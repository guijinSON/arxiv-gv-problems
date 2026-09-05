"""Verified generator based on Theorem 2.2 of arXiv:2005.08095.

The paper reduces Maximum Clique to General d-Position by adjoining H_t.
Here G is a compact, k-partite graph over a prime field.  Every colour-pair
relation is the union of three affine maps with a shared slope.  A planted
system of hidden coordinate gauges and translations is sampled before the
graph is built, so a transversal clique is known without solving the generated
instance.

The family is Track B.  Lexicographic CSP search must scan most field values,
while a short multiplicative-then-additive cocycle calculation removes hidden
coordinate gauges and turns the exceptional affine relation into the answer.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "the paper's graph G' obtained by joining H_t to a compact k-partite graph G",
        "a prescribed-size general d-position set represented by its G-vertices",
    ],
    "verification_operations": [
        "exact modular affine evaluation",
        "exact graph adjacency lookup",
        "exact clique and cardinality checks",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 2, Proposition 2.1 and Theorem 2.2: construct H_t and join "
        "A union B union {v_1} to G, giving gp_d(G')=gp_d(H_t)+omega(G)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The ordinary pair slopes obey a multiplicative cocycle and their rescaled "
        "intercepts obey an additive cocycle; without both invariants, lexicographic "
        "clique search scans most of the field."
    ),
    "hardness_basis": (
        "Track B: complete lexicographic multicoloured-clique backtracking costs "
        "O(p*k^2*r^(k-1)) in the worst case (linear in p for fixed shipping k=20, "
        "r=3) and at p=500009 averages 7,190,380 exact operations, 140,973 field "
        "values, and 0.99 seconds over eight audit seeds; the distribution-specific "
        "cocycle algorithm is O(k^2*r^2+k*log(p)) and uses at most 274 exact "
        "operations, but a no-tool solver must first discover its two invariants."
    ),
    "max_answer_tokens": 41,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 17, "classes": 4, "degree": 3},
    "easy": {"n": 200003, "classes": 20, "degree": 3},
    "medium": {"n": 500009, "classes": 20, "degree": 3},
    "hard": {"n": 1000003, "classes": 20, "degree": 3},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "The ordinary pair slopes form a multiplicative cocycle whose rescaled intercept "
    "sets contain an additive cocycle."
)
PLACEBO_HINT = (
    "The listed pair relations require careful bookkeeping of the modular labels, "
    "class order, and answer slots."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list containing exactly one displayed integer vertex label from each "
        "colour class, in class order; class Ci contains labels i*p through (i+1)*p-1."
    ),
    "bounds": {
        "length": "number of colour classes",
        "entry_min": 0,
        "entry_max": "p times number of colour classes minus 1",
        "one_per_colour": True,
        "candidate_count": "p^(number of colour classes)",
    },
}

NOTES = (
    "Section 1, equation (1), fixes the forbidden configuration as three selected "
    "vertices on a common geodesic of length at most d. Section 2, Proposition 2.1 "
    "gives gp_t(H_t)=4t, and Theorem 2.2 supplies the exact H_t join used here. "
    "Propositions 3.1 and 3.3 make paths and cycles easy, while Section 6 notes "
    "polynomial algorithms for gp_2 and ordinary general position on trees; those "
    "regimes were avoided. The certificate-producing reference method here is a "
    "lexicographic CSP scan, not a hidden oracle. Its mechanical cost and the compact "
        "slope/twisted-intercept cocycle route are both measured. Independent field-"
        "coordinate gauges hide the formerly obvious slope-1 pattern. Equal pair-degrees defeat degree "
    "outliers; high exceptional roots defeat zero-first greedy search; random restarts "
    "and the common-coordinate ansatz are tested separately."
)


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_GUESS_SAMPLES = 200_000

# Filled from the required harness runs.  Service failures are not model attempts.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3, "service_errors": 0},
    "hinted": {"solved": 0, "attempts": 3, "service_errors": 0},
    "placebo": {"solved": 0, "attempts": 3, "service_errors": 0},
    "hinted_verdict": "hardened",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_prime(value):
    if not _is_int(value) or value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime(value):
    candidate = max(3, int(value) | 1)
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _validate_params(n, classes, degree, seed):
    if not _is_prime(n) or n < 17:
        raise ValueError("n must be a prime integer at least 17")
    if not _is_int(classes) or classes < 4:
        raise ValueError("classes must be an integer at least 4")
    if degree != 3:
        raise ValueError("this family requires degree=3")
    if not _is_int(seed):
        raise ValueError("seed must be an integer")


def _sample_with_required(required, p, rng):
    values = {required % p}
    while len(values) < 3:
        values.add(rng.randrange(p))
    result = sorted(values)
    rng.shuffle(result)
    return result


def _relation_map(inst):
    cached = inst.get("_relation_cache") if isinstance(inst, dict) else None
    if isinstance(cached, dict):
        return cached
    try:
        p = inst["modulus"]
        k = inst["color_count"]
        result = {}
        for rec in inst["relations"]:
            i, j = rec["left"], rec["right"]
            slope = rec["slope"]
            intercepts = rec["intercepts"]
            if not (0 <= i < j < k) or (i, j) in result:
                return None
            if not _is_int(slope) or not 1 <= slope < p:
                return None
            if (
                not isinstance(intercepts, list)
                or len(intercepts) != 3
                or len(set(intercepts)) != 3
                or any(not _is_int(b) or not 0 <= b < p for b in intercepts)
            ):
                return None
            result[(i, j)] = (slope, tuple(intercepts))
        if len(result) != k * (k - 1) // 2:
            return None
        inst["_relation_cache"] = result
        return result
    except (KeyError, TypeError, ValueError):
        return None


def _directed_slope(relations, p, i, j):
    """Slope of the public affine relation directed from colour i to j."""
    if i < j:
        return relations[(i, j)][0]
    return pow(relations[(j, i)][0], -1, p)


def _gauge_setup(inst, count_operations=False):
    """Find the exceptional edge from the public slope cocycle.

    The four triangles on colours 0,1,2,3 have exactly two slope-cocycle
    failures; their common edge is the exceptional relation.  Only public
    relation data is used.
    """
    relations = _relation_map(inst)
    if relations is None:
        return None, 0
    p, k = inst["modulus"], inst["color_count"]
    if k < 4:
        return None, 0
    operations = 0
    bad_triangles = []
    for a, b, c in itertools.combinations(range(4), 3):
        operations += 1
        if (_directed_slope(relations, p, b, c)
                * _directed_slope(relations, p, a, b)) % p != \
                _directed_slope(relations, p, a, c):
            bad_triangles.append({a, b, c})
    if len(bad_triangles) != 2:
        return None, operations
    common = bad_triangles[0] & bad_triangles[1]
    if len(common) != 2:
        return None, operations
    special = tuple(sorted(common))

    context = {
        "relations": relations,
        "p": p,
        "k": k,
        "special": special,
    }
    return context, operations if count_operations else 0


def _directed_relation(context, i, j):
    """Public affine relation x_j=a*x_i+b in the requested orientation."""
    relations, p = context["relations"], context["p"]
    if i < j:
        return relations[(i, j)]
    slope, intercepts = relations[(j, i)]
    inverse = pow(slope, -1, p)
    return inverse, tuple((-inverse * value) % p for value in intercepts)


def _inverse_operation_count(value, modulus):
    """Euclidean divisions needed for a modular inverse (not counted as one op)."""
    count = 0
    a, b = modulus, value % modulus
    while b:
        a, b = b, a % b
        count += 1
    return count


def _recover_structure(inst, count_operations=False):
    """Recover the unique twisted additive cocycle in public coordinates."""
    context, operations = _gauge_setup(inst, count_operations=True)
    if context is None:
        return None, None, operations
    p, k = context["p"], context["k"]
    left, right = context["special"]
    anchors = [i for i in range(k) if i not in (left, right)]
    if len(anchors) < 2:
        return None, None, operations
    c, d = anchors[:2]

    a_ac, b_ac = _directed_relation(context, left, c)
    a_cd, b_cd = _directed_relation(context, c, d)
    a_ad, b_ad = _directed_relation(context, left, d)
    operations += 1
    if a_ad != a_cd * a_ac % p:
        return None, None, operations

    anchor_solutions = []
    ad_set = set(b_ad)
    for x in b_ac:
        for y in b_cd:
            operations += 2
            composed = (a_cd * x + y) % p
            if composed in ad_set:
                anchor_solutions.append((x, y, composed))
    if len(anchor_solutions) != 1:
        return None, None, operations
    t_c, _, t_d = anchor_solutions[0]
    translations = {left: 0, c: t_c, d: t_d}

    for vertex in range(k):
        if vertex in (left, right, c, d):
            continue
        _, b_lv = _directed_relation(context, left, vertex)
        a_cv, b_cv = _directed_relation(context, c, vertex)
        a_dv, b_dv = _directed_relation(context, d, vertex)
        c_term = a_cv * t_c % p
        d_term = a_dv * t_d % p
        operations += 2
        choices = []
        for x in b_lv:
            operations += 2
            if (x - c_term) % p in b_cv and (x - d_term) % p in b_dv:
                choices.append(x)
        if len(choices) != 1:
            return None, None, operations
        translations[vertex] = choices[0]

    a_cr, b_cr = _directed_relation(context, c, right)
    a_rd, b_rd = _directed_relation(context, right, d)
    target = (t_d - (a_rd * a_cr % p) * t_c) % p
    operations += 3
    bridge = []
    for x in b_cr:
        for y in b_rd:
            operations += 2
            if (a_rd * x + y) % p == target:
                bridge.append((x, y))
    if len(bridge) != 1:
        return None, None, operations
    translations[right] = (a_cr * t_c + bridge[0][0]) % p
    operations += 2
    if len(translations) != k:
        return None, None, operations

    gauges = {left: 1}
    for vertex in range(k):
        if vertex in (left, right):
            continue
        gauges[vertex] = _directed_slope(context["relations"], p, left, vertex)
    gauges[right] = a_cr * gauges[c] % p
    operations += 1
    context["gauges"] = gauges
    result = [translations[i] for i in range(k)]
    return result, context, operations if count_operations else 0


def _recover_shifts(inst, count_operations=False):
    shifts, _, operations = _recover_structure(inst, count_operations)
    return shifts, operations


def _compact_route(inst):
    """The intended Track B route, implemented for measurement and audit."""
    shifts, context, operations = _recover_structure(inst, count_operations=True)
    if shifts is None or context is None:
        return None, operations
    p, k = inst["modulus"], inst["color_count"]
    left, right = context["special"]
    slope, intercepts = _directed_relation(context, left, right)
    # x_i = g_i*z+t_i.  The exceptional relation fixes z.
    b = intercepts[0]
    numerator = (slope * shifts[left] + b - shifts[right]) % p
    denominator = (context["gauges"][right]
                   - slope * context["gauges"][left]) % p
    operations += 4
    z = numerator * pow(denominator, -1, p) % p
    operations += 1 + _inverse_operation_count(denominator, p)
    residues = [
        (context["gauges"][i] * z + shifts[i]) % p
        for i in range(k)
    ]
    operations += 2 * k
    answer = [i * p + residues[i] for i in range(k)]
    operations += 2 * k
    return answer, operations


def make_instance(n, seed=0, **params):
    """Inverse-generate a Theorem 2.2 General d-Position instance."""
    classes = params.pop("classes", 20)
    degree = params.pop("degree", 3)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, classes, degree, seed)
    p = n
    rng = random.Random(seed)

    while True:
        shifts = [0] + [rng.randrange(p) for _ in range(classes - 1)]
        if shifts[1] == 0:
            continue
        gauges = [1] + [rng.randrange(1, p) for _ in range(classes - 1)]
        relations = []
        relation_cache = {}
        for left in range(classes):
            for right in range(left + 1, classes):
                if (left, right) == (0, 2):
                    continue
                required = (shifts[right] - shifts[left]) % p
                base_intercepts = _sample_with_required(required, p, rng)
                slope = gauges[right] * pow(gauges[left], -1, p) % p
                intercepts = [
                    gauges[right] * value % p for value in base_intercepts
                ]
                rec = {
                    "left": left,
                    "right": right,
                    "slope": slope,
                    "intercepts": intercepts,
                }
                relations.append(rec)
                relation_cache[(left, right)] = (slope, tuple(intercepts))

        roots = rng.sample(range(p), 3)
        base_slope = 2
        base_special_intercepts = sorted(
            {(shifts[2] + (1 - base_slope) * root) % p for root in roots}
        )
        if len(base_special_intercepts) != 3:
            continue
        slope = base_slope * gauges[2] * pow(gauges[0], -1, p) % p
        special_intercepts = [
            gauges[2] * value % p for value in base_special_intercepts
        ]
        special = {
            "left": 0,
            "right": 2,
            "slope": slope,
            "intercepts": special_intercepts,
        }
        relations.append(special)
        relations.sort(key=lambda rec: (rec["left"], rec["right"]))

        t = p * classes
        inst = {
            "paper": "arXiv:2005.08095",
            "family": "Section 2 H_t reduction with affine-cocycle clique graph",
            "recipe": "theorem-2.2-Ht-affine-cocycle-v1",
            "n": p,
            "modulus": p,
            "color_count": classes,
            "cross_degree": degree,
            "G_order_t": t,
            "d": t,
            "Ht_order": 6 * t - 3,
            "Gprime_order": 7 * t - 3,
            "fixed_Ht_certificate_size": 4 * t,
            "target_size": 4 * t + classes,
            "relations": relations,
        }
        inst["_relation_cache"] = {
            (rec["left"], rec["right"]):
            (rec["slope"], tuple(rec["intercepts"]))
            for rec in relations
        }
        recovered, _ = _recover_shifts(inst)
        if recovered != [
            gauges[i] * (value - shifts[0]) % p
            for i, value in enumerate(shifts)
        ]:
            continue
        planted_z = roots[0]
        residues = [
            gauges[i] * (planted_z + value) % p
            for i, value in enumerate(shifts)
        ]
        inst["answer"] = [i * p + residues[i] for i in range(classes)]
        return inst


def _decode_answer(inst, answer):
    p = inst["modulus"]
    return [label - i * p for i, label in enumerate(answer)]


def _edge(relations, p, i, x, j, y):
    if i < j:
        slope, intercepts = relations[(i, j)]
        return (y - slope * x) % p in intercepts
    slope, intercepts = relations[(j, i)]
    return (x - slope * y) % p in intercepts


def verify(inst, answer):
    """Check any valid compact target-size witness; never read inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if any(not _is_int(value) for value in answer):
        return False, "every representative must be an integer vertex label"
    if len(set(answer)) != len(answer):
        return False, "representative vertex labels must be distinct"
    try:
        p, k, t = inst["modulus"], inst["color_count"], inst["G_order_t"]
        if (
            inst.get("recipe") != "theorem-2.2-Ht-affine-cocycle-v1"
            or not _is_prime(p)
            or t != p * k
            or inst["n"] != p
            or inst["d"] != t
            or inst["cross_degree"] != 3
            or inst["fixed_Ht_certificate_size"] != 4 * t
            or inst["target_size"] != 4 * t + k
            or inst["Ht_order"] != 6 * t - 3
            or inst["Gprime_order"] != 7 * t - 3
        ):
            return False, "malformed Theorem 2.2 construction parameters"
    except (KeyError, TypeError):
        return False, "malformed instance"
    if len(answer) != k:
        return False, f"wrong length: expected {k} representatives, got {len(answer)}"
    for i, label in enumerate(answer):
        if not i * p <= label < (i + 1) * p:
            if not 0 <= label < k * p:
                return False, f"unknown vertex label {label}"
            owner = label // p
            return False, (
                f"slot {i + 1} requires colour {i + 1}, but label {label} "
                f"belongs to colour {owner + 1}"
            )
    relations = _relation_map(inst)
    if relations is None:
        return False, "malformed relation data"
    residues = _decode_answer(inst, answer)
    for i in range(k):
        for j in range(i + 1, k):
            if not _edge(relations, p, i, residues[i], j, residues[j]):
                return False, (
                    f"labels {answer[i]} and {answer[j]} are incompatible "
                    f"for colours {i + 1} and {j + 1}"
                )
    # A union B together with the submitted G-vertices is literally a clique.
    # Hence no selected third vertex lies on a shortest path between two others.
    return True, "ok"


def render(inst):
    p, k, t = inst["modulus"], inst["color_count"], inst["G_order_t"]
    example = [i * p for i in range(k)]
    lines = [
        "Find a prescribed-size general d-position set in a compactly specified graph.",
        "",
        "Definitions.",
        "For vertices x,y, dist(x,y) is the minimum number of edges on an x-y path.",
        "A geodesic is a path whose length equals that distance. A set S is in",
        "general d-position when no three distinct vertices of S occur on one",
        "geodesic of length at most d.",
        "",
        f"Let p={p}, a prime. Arithmetic below is modulo p, with residues 0,...,{p-1}.",
        f"The graph G has k={k} colour classes C1,...,C{k}. Class Ci (with i",
        f"1-based) contains the p integer vertex labels (i-1)*p through i*p-1.",
        "The residue coordinate of a label in Ci is label-(i-1)*p.",
        "There are no edges inside a colour class.",
        "",
        "For each line PAIR Ci Cj: a ; b1,b2,b3, where i<j, a vertex with",
        "residue x in Ci is adjacent to a vertex with residue y in Cj exactly when",
        "y = a*x+b modulo p for at least one listed b. All three b values are",
        "included, and there are no other G-edges.",
        "",
        "Pair relations:",
    ]
    for rec in inst["relations"]:
        intercepts = ",".join(map(str, rec["intercepts"]))
        lines.append(
            f"  PAIR C{rec['left'] + 1} C{rec['right'] + 1}: "
            f"{rec['slope']} ; {intercepts}"
        )
    lines.extend([
        "",
        "The full graph G' is the following Section 2 construction.",
        f"1. Make H_t for t={t}. Its sets A={{a1,...,a{2*t}}} and",
        f"   B={{b1,...,b{2*t}}} together induce a complete graph K_{4*t}.",
        f"2. Add the path v1-v2-...-v{t-1}, and join every B vertex to v1.",
        f"3. For i=2,...,{t-1}, add u_i adjacent to v_i and v_(i-1).",
        "   These are all H_t edges.",
        "4. Join every G vertex to every vertex of A, every vertex of B, and v1.",
        "   Add no other cross edges.",
        f"Thus G' has {inst['Gprime_order']} vertices, and d=t={t}.",
        "",
        f"Submit exactly one G-vertex label from each C_i, in C1,...,C{k} order.",
        f"The checker expands the answer to S=A union B union those {k} vertices.",
        f"The required expanded size is exactly {inst['target_size']}. Do not list",
        "the A or B vertices. Order is significant; bounds are inclusive.",
        "",
        f"Output exactly {k} distinct decimal labels as a JSON list.",
        "Give your final answer inside <answer></answer> tags, as that JSON list.",
        f"Example syntax only: <answer>{json.dumps(example, separators=(',', ':'))}</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Parse a tagged JSON integer list, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.I | re.S)
    if fenced:
        body = fenced.group(1).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list) or any(not _is_int(x) for x in value):
        return None
    return value


def random_candidate(inst, rng):
    """Uniformly sample after enforcing length and one vertex per colour."""
    p, k = inst["modulus"], inst["color_count"]
    return [i * p + rng.randrange(p) for i in range(k)]


def search_space(inst):
    try:
        return inst["modulus"] ** inst["color_count"]
    except (KeyError, TypeError, ValueError):
        return None


def enumerate_all(inst):
    space = search_space(inst)
    if space is None or space > 1_000_000:
        return None
    p, k = inst["modulus"], inst["color_count"]
    return sum(
        int(verify(inst, [i * p + values[i] for i in range(k)])[0])
        for values in itertools.product(range(p), repeat=k)
    )


def _affine_set_signature(values, p):
    """Canonical image of a finite field set under x -> a*x+b, a != 0."""
    normal_forms = []
    for zero in values:
        for one in values:
            if one == zero:
                continue
            inverse = pow((one - zero) % p, -1, p)
            normal_forms.append(tuple(sorted(
                ((value - zero) * inverse) % p for value in values
            )))
    return min(normal_forms)


def canonical_key(inst):
    """Strong cheap invariant under colour and affine-coordinate relabelling."""
    relations = _relation_map(inst)
    if relations is None:
        return "general-d-position-affine-cocycle:malformed"
    p = inst["modulus"]
    signatures = sorted(
        _affine_set_signature(intercepts, p)
        for _, intercepts in relations.values()
    )
    payload = [p, inst["color_count"], inst["cross_degree"], signatures]
    digest = hashlib.sha256(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return "general-d-position-affine-cocycle-v1:" + digest


def escalate(params):
    """Grow the field while keeping the witness length fixed."""
    if not isinstance(params, dict) or "n" not in params:
        return None
    classes = int(params.get("classes", 20))
    # The witness has fixed cardinality, but its decimal labels eventually hit
    # the character cap.  Detect that true format limit before doing a costly
    # prime search at fantastically large field sizes.
    upper = 2 * int(params["n"]) + 2
    next_answer_chars = 2 + max(0, classes - 1) + sum(
        len(str((i + 1) * upper - 1)) for i in range(classes)
    )
    if next_answer_chars > 2000:
        return "cap_bound"
    return {
        "n": _next_prime(2 * int(params["n"]) + 1),
        "classes": classes,
        "degree": 3,
    }


def _neighbours(relations, p, i, x, j):
    if i < j:
        slope, intercepts = relations[(i, j)]
        return [(slope * x + b) % p for b in intercepts]
    slope, intercepts = relations[(j, i)]
    inverse = pow(slope, -1, p)
    return [(inverse * (x - b)) % p for b in intercepts]


def _greedy_from_x0(inst, x0):
    relations = _relation_map(inst)
    p, k = inst["modulus"], inst["color_count"]
    values = [x0]
    for colour in range(1, k):
        candidates = sorted(set(_neighbours(relations, p, 0, x0, colour)))
        feasible = [
            value for value in candidates
            if all(_edge(relations, p, j, values[j], colour, value)
                   for j in range(colour))
        ]
        if not feasible:
            return None
        values.append(feasible[0])
    return [i * p + values[i] for i in range(k)]


def _reference_scan(inst):
    """Complete lexicographic CSP backtracking with forward compatibility checks."""
    relations = _relation_map(inst)
    p, k = inst["modulus"], inst["color_count"]
    counters = {"field_values": 0, "edge_checks": 0, "modular_operations": 0}

    def extend(values):
        colour = len(values)
        if colour == k:
            return list(values)
        candidates = _neighbours(relations, p, 0, values[0], colour)
        counters["modular_operations"] += 2 * len(candidates)
        for value in candidates:
            good = True
            for earlier in range(1, colour):
                counters["edge_checks"] += 1
                counters["modular_operations"] += 2
                if not _edge(
                    relations, p, earlier, values[earlier], colour, value
                ):
                    good = False
                    break
            if not good:
                continue
            values.append(value)
            result = extend(values)
            if result is not None:
                return result
            values.pop()
        return None

    for x0 in range(p):
        counters["field_values"] += 1
        values = extend([x0])
        if values is not None:
            answer = [i * p + values[i] for i in range(k)]
            if verify(inst, answer)[0]:
                counters["operations"] = (
                    counters["edge_checks"] + counters["modular_operations"]
                )
                return answer, counters
    counters["operations"] = counters["edge_checks"] + counters["modular_operations"]
    return None, counters


def _attack_outlier_degree(inst):
    # Every vertex has degree three into every other colour, so all scores tie.
    p, k = inst["modulus"], inst["color_count"]
    return [i * p for i in range(k)]


def _attack_greedy(inst):
    return _greedy_from_x0(inst, 0)


def _attack_random_restart(inst, rng, restarts=64):
    p = inst["modulus"]
    for _ in range(restarts):
        candidate = _greedy_from_x0(inst, rng.randrange(p))
        if candidate is not None and verify(inst, candidate)[0]:
            return candidate
    return None


def _attack_common_coordinate(inst):
    p, k = inst["modulus"], inst["color_count"]
    residue = p // 2
    return [i * p + residue for i in range(k)]


def _transform_instance(inst, rng, colour_permutation=True,
                        affine_coordinates=True, reorder_records=True):
    """Apply genuine graph relabellings and carry the witness."""
    p, k = inst["modulus"], inst["color_count"]
    scales = [rng.randrange(1, p) if affine_coordinates else 1 for _ in range(k)]
    offsets = [rng.randrange(p) if affine_coordinates else 0 for _ in range(k)]
    order = list(range(k))
    if colour_permutation:
        rng.shuffle(order)
    old_to_new = {old: new for new, old in enumerate(order)}
    new_relations = []
    for rec in inst["relations"]:
        old_i, old_j = rec["left"], rec["right"]
        new_i, new_j = old_to_new[old_i], old_to_new[old_j]
        slope = (
            scales[old_j]
            * rec["slope"]
            * pow(scales[old_i], -1, p)
        ) % p
        intercepts = [
            (scales[old_j] * b + offsets[old_j] - slope * offsets[old_i]) % p
            for b in rec["intercepts"]
        ]
        if new_i < new_j:
            left, right = new_i, new_j
        else:
            left, right = new_j, new_i
            inverse = pow(slope, -1, p)
            intercepts = [(-inverse * b) % p for b in intercepts]
            slope = inverse
        new_relations.append({
            "left": left,
            "right": right,
            "slope": slope,
            "intercepts": intercepts,
        })
    if reorder_records:
        for rec in new_relations:
            rng.shuffle(rec["intercepts"])
        rng.shuffle(new_relations)
    transformed = {
        key: value for key, value in inst.items()
        if key not in {"relations", "answer"} and not key.startswith("_")
    }
    transformed["relations"] = new_relations
    old_residues = _decode_answer(inst, inst["answer"])
    transformed["answer"] = [
        new_i * p + (
            scales[old_i] * old_residues[old_i] + offsets[old_i]
        ) % p
        for new_i, old_i in enumerate(order)
    ]
    return transformed


def _corruptions(inst):
    answer = list(inst["answer"])
    p, k = inst["modulus"], inst["color_count"]
    corrupt = {
        "empty": [],
        "drop_one": answer[:-1],
        "duplicate": [answer[1]] + answer[1:],
        "out_of_range": [k * p + 1] + answer[1:],
        "swap_slots": answer[1:2] + answer[0:1] + answer[2:],
    }
    replacement = None
    for residue in range(p):
        label = residue
        if label == answer[0]:
            continue
        candidate = answer[:]
        candidate[0] = label
        if not verify(inst, candidate)[0]:
            replacement = candidate
            break
    corrupt["incompatible_replacement"] = replacement
    return corrupt


def selftest():
    report = {}

    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": why})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({
                    "preset": preset, "seed": seed,
                    "reason": "answer is not JSON-native",
                })
    report["G1_planted_verifies"] = {
        "pass": not failures, "checked": checks, "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=314159, **shipping_params)

    corruption_results = {}
    reasons = []
    for name, candidate in _corruptions(shipping).items():
        if candidate is None:
            corruption_results[name] = {"rejected": False, "reason": "not constructed"}
            continue
        ok, why = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": why}
        if not ok:
            reasons.append(why)
    report["G2_rejects_corruption"] = {
        "pass": (
            all(item["rejected"] for item in corruption_results.values())
            and len(set(reasons)) == len(reasons)
        ),
        "distinct_reasons": len(set(reasons)),
        "cases": corruption_results,
    }

    response = (
        "The affine cocycle fixes the transversal.\n\n<answer>```json\n"
        + json.dumps(shipping["answer"])
        + "\n```</answer>\n"
    )
    parsed = parse_answer(response)
    parsed_ok, parsed_why = verify(shipping, parsed)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and parsed_ok,
        "verify_reason": parsed_why,
    }

    guess_rng = random.Random(271828)
    guess_hits = sum(
        int(verify(shipping, random_candidate(shipping, guess_rng))[0])
        for _ in range(_GUESS_SAMPLES)
    )
    report["G4_guess_resistance"] = {
        "pass": guess_hits / _GUESS_SAMPLES < 1e-6,
        "hits": guess_hits,
        "total": _GUESS_SAMPLES,
        "measured_probability": guess_hits / _GUESS_SAMPLES,
        "candidate_space": search_space(shipping),
        "sampler": "uniform one-listed-vertex-per-colour assignments",
    }

    attack_seeds = list(range(800, 808))
    attack_results = {
        "outlier_equal_degree_tie": {"successes": 0, "attempts": 8},
        "greedy_zero_first": {"successes": 0, "attempts": 8},
        "random_restart_64": {"successes": 0, "attempts": 8},
        "common_coordinate_ansatz": {"successes": 0, "attempts": 8},
    }
    reference_successes = 0
    reference_walls = []
    reference_operations = []
    reference_field_values = []
    compact_operations = []
    compact_successes = 0
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **shipping_params)
        candidates = {
            "outlier_equal_degree_tie": _attack_outlier_degree(inst),
            "greedy_zero_first": _attack_greedy(inst),
            "random_restart_64": _attack_random_restart(
                inst, random.Random(seed ^ 0xD905), 64
            ),
            "common_coordinate_ansatz": _attack_common_coordinate(inst),
        }
        for name, candidate in candidates.items():
            if candidate is not None and verify(inst, candidate)[0]:
                attack_results[name]["successes"] += 1

        start = time.perf_counter()
        reference_answer, counters = _reference_scan(inst)
        reference_walls.append(time.perf_counter() - start)
        reference_operations.append(counters["operations"])
        reference_field_values.append(counters["field_values"])
        reference_successes += int(
            reference_answer is not None and verify(inst, reference_answer)[0]
        )
        compact_answer, operations = _compact_route(inst)
        compact_operations.append(operations)
        compact_successes += int(
            compact_answer is not None and verify(inst, compact_answer)[0]
        )

    report["G5_density_and_baseline"] = {
        "pass": (
            guess_hits / _GUESS_SAMPLES < 1e-6
            and reference_successes == 8
            and compact_successes == 8
        ),
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": _GUESS_SAMPLES,
        "shipping_solution_fraction_estimate": guess_hits / _GUESS_SAMPLES,
        "shipping_known_valid_answers_by_construction": 3,
        "shipping_candidate_space": search_space(shipping),
        "reference_wall_clock_sec_mean": sum(reference_walls) / 8,
        "reference_wall_clock_sec_max": max(reference_walls),
        "reference_operations_mean": sum(reference_operations) / 8,
        "reference_operations_max": max(reference_operations),
        "reference_field_values_mean": sum(reference_field_values) / 8,
        "compact_route_operations_max": max(compact_operations),
        "demo_exact_valid_answers": enumerate_all(
            make_instance(seed=5, **DIFFICULTY["demo"])
        ),
        "demo_candidate_space": search_space(
            make_instance(seed=5, **DIFFICULTY["demo"])
        ),
    }
    all_attacks_failed = all(item["successes"] == 0 for item in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8,
        "attacks": attack_results,
        "seeds": attack_seeds,
        "reference_algorithm": {
            "name": "complete lexicographic multicoloured-clique CSP backtracking",
            "complexity": (
                "O(p*k^2*r^(k-1)) worst case; O(p) in the scaling variable "
                "for fixed shipping k=20 and r=3"
            ),
            "wall_clock_sec_mean": sum(reference_walls) / 8,
            "operations_mean": sum(reference_operations) / 8,
            "field_values_mean": sum(reference_field_values) / 8,
            "solves": f"{reference_successes}/8, as expected",
        },
        "compact_route": {
            "name": "slope cocycle, twisted intercept cocycle, and one affine equation",
            "operations_max": max(compact_operations),
            "solves": f"{compact_successes}/8",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] = _next_prime(2 * shipping_params["n"] + 1)
    start = time.perf_counter()
    doubled = make_instance(seed=1234, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(shipping),
        "base_n": shipping["n"],
        "doubled_n": doubled["n"],
        "answer_length_base": len(shipping["answer"]),
        "answer_length_doubled": len(doubled["answer"]),
        "base_candidate_space": search_space(shipping),
        "doubled_candidate_space": search_space(doubled),
        "doubled_build_sec": doubled_build,
        "verify_reason": doubled_why,
    }

    invariant_checks = 0
    witness_checks = 0
    key_failures = []
    unrelated_keys = []
    transform_modes = [
        (False, True, False, "independent_affine_coordinates"),
        (True, False, False, "colour_permutation"),
        (False, False, True, "record_reordering"),
        (True, True, True, "composition"),
    ]
    for seed in range(20):
        inst = make_instance(seed=20_000 + seed, **shipping_params)
        key = canonical_key(inst)
        unrelated_keys.append(key)
        for colour_perm, affine_coordinates, reorder, name in transform_modes:
            transformed = _transform_instance(
                inst,
                random.Random(30_000 + 17 * seed + len(name)),
                colour_permutation=colour_perm,
                affine_coordinates=affine_coordinates,
                reorder_records=reorder,
            )
            invariant_checks += 1
            if canonical_key(transformed) != key:
                key_failures.append({"seed": seed, "transform": name, "kind": "key"})
            ok, why = verify(transformed, transformed["answer"])
            witness_checks += 1
            if not ok:
                key_failures.append({
                    "seed": seed, "transform": name, "kind": "witness", "reason": why,
                })
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "real_transformation_witness_checks": witness_checks,
        "unrelated_instances": 20,
        "unrelated_distinct_keys": distinct,
        "failures": key_failures,
        "transformations": [mode[3] for mode in transform_modes],
        "invariant": "affine-normalised intercept-set signatures",
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(shipping["answer"])
    compact_answer, intended_ops = _compact_route(shipping)
    compact_ok = compact_answer is not None and verify(shipping, compact_answer)[0]
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else None
    )
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else None
    )
    hinted_minus_placebo = (
        hinted_rate - placebo_rate
        if hinted_rate is not None and placebo_rate is not None else None
    )
    within_caps = (
        answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps and compact_ok,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "intended_route_verifies": compact_ok,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "caps_pass": within_caps,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping_params
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
