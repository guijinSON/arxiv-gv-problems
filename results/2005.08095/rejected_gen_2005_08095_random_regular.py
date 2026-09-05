"""Verified generator for the General d-Position reduction of arXiv:2005.08095.

Section 2, Proposition 2.1 and Theorem 2.2, transform Maximum Clique into
General d-Position by adjoining the graph H_t.  This module inverse-generates a
hidden multicoloured clique, applies that exact transformation at d=t, and asks
for a compact description of a prescribed-size general d-position set.

The generator samples the answer before it constructs any compatibility graph.
The verifier expands the compact answer through the paper's construction and
checks the resulting clique, hence the geodesic condition, exactly.
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


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "the paper's graph G' obtained by joining H_t to a coloured graph G",
        "prescribed-size general d-position set represented by its non-H_t vertices",
    ],
    "verification_operations": [
        "exact graph adjacency lookup",
        "exact clique check",
        "exact cardinality accounting in the H_t extension",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 2, Proposition 2.1 and Theorem 2.2: construct H_t and join "
        "A union B union {v_1} to G, giving gp_d(G')=gp_d(H_t)+omega(G)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "reduction recognition",
    "intuition_description": (
        "Recognize that the fixed A union B part of H_t turns the requested "
        "general-position extension into one representative per colour forming "
        "a clique; without that recognition one faces geodesics in a 7t-3 vertex graph."
    ),
    "hardness_basis": (
        "Track A: Theorem 2.2 proves NP-completeness through the exact Maximum "
        "Clique reduction used here; the shipping regime has d=t, 22 colour "
        "classes of size 32, and 23-regular colour-pair graphs at the planted "
        "first-moment threshold, where no efficient recovery method is known "
        "for this planted distribution and exact MRV clique search exhausts "
        "500,000 nodes on all eight audit seeds (measured wall-clock is in G5)."
    ),
    "max_answer_tokens": 23,
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
    "demo": {"n": 3, "classes": 3, "degree": 2},
    "easy": {"n": 32, "classes": 22, "degree": 23},
    "medium": {"n": 40, "classes": 24, "degree": 29},
    "hard": {"n": 48, "classes": 24, "degree": 34},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The A-union-B extension in the paper's H_t reduction preserves exactly "
    "the clique compatibility relation among the selected G-vertices."
)
PLACEBO_HINT = (
    "The named vertex classes and matrix conventions reward careful attention "
    "to every label and index."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly one displayed integer vertex label from each "
        "colour class, in class order; labels are distinct and no label repeats."
    ),
    "bounds": {
        "length": "number of colour classes",
        "entry_min": 1,
        "entry_max": "n times number of colour classes",
        "one_per_colour": True,
        "candidate_count": "n^(number of colour classes)",
    },
}

NOTES = (
    "Section 1, equation (1), fixes the exact forbidden configuration: three "
    "selected vertices on a common geodesic of length at most d. Section 2, "
    "Proposition 2.1 defines H_t and gives gp_t(H_t)=4t; Theorem 2.2 supplies "
    "the identity gp_d(G')=gp_d(H_t)+omega(G) used by the generator. Paths and "
    "cycles were avoided because Propositions 3.1 and 3.3 give their answers "
    "explicitly. Section 6 also records polynomial algorithms for gp_2 on trees "
    "and for ordinary general position on trees. The answer is sampled before "
    "every pair graph. Pair graphs are regular, so degree does not reveal the "
    "plant; many degree-preserving two-switches hide the initial coordinates. "
    "The audit separately tests triangle participation, greedy propagation, "
    "random restarts, a centred spectral method, and exact MRV search."
)


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_EXACT_NODE_BUDGET = 500_000
_GUESS_SAMPLES = 200_000

# Updated from the three independent harness runs after hardening.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0, "service_errors": 4},
    "hinted": {"solved": 0, "attempts": 0, "service_errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "service_errors": 4},
    "hinted_verdict": "unreachable",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_params(n, classes, degree, seed):
    if not _is_int(n) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if not _is_int(classes) or classes < 3:
        raise ValueError("classes must be an integer at least 3")
    if not _is_int(degree) or not 1 <= degree < n:
        raise ValueError("degree must be an integer with 1 <= degree < n")
    if not _is_int(seed):
        raise ValueError("seed must be an integer")


def _regular_pair(n, degree, plant_left, plant_right, rng):
    """Return a switched regular bipartite graph containing the planted edge."""
    missing_degree = n - degree
    left_at = [plant_left] + [x for x in range(n) if x != plant_left]
    right_at = [plant_right] + [y for y in range(n) if y != plant_right]
    left_tail = left_at[1:]
    right_tail = right_at[1:]
    rng.shuffle(left_tail)
    rng.shuffle(right_tail)
    left_at = [plant_left] + left_tail
    right_at = [plant_right] + right_tail
    left_coordinate = {vertex: coordinate for coordinate, vertex in enumerate(left_at)}

    # The missing-edge graph is regular.  Excluding shift zero ensures that the
    # planted pair starts as an edge of the compatibility graph.
    shifts = rng.sample(range(1, n), missing_degree)
    missing = [set() for _ in range(n)]
    for x in range(n):
        coordinate = left_coordinate[x]
        missing[x] = {right_at[(coordinate + shift) % n] for shift in shifts}
    assert plant_right not in missing[plant_left]

    # Degree-preserving switches mix the graph while retaining only the planted
    # edge condition.  Plants and decoys therefore have identical pair-degrees.
    for _ in range(3 * n * max(1, missing_degree)):
        a = rng.randrange(n)
        b = rng.randrange(n - 1)
        if b >= a:
            b += 1
        only_a = missing[a] - missing[b]
        only_b = missing[b] - missing[a]
        if a == plant_left:
            only_b.discard(plant_right)
        if b == plant_left:
            only_a.discard(plant_right)
        if not only_a or not only_b:
            continue
        y = rng.choice(sorted(only_a))
        z = rng.choice(sorted(only_b))
        missing[a].remove(y)
        missing[b].remove(z)
        missing[a].add(z)
        missing[b].add(y)

    assert all(len(row) == missing_degree for row in missing)
    column_degrees = [0] * n
    for row in missing:
        for y in row:
            column_degrees[y] += 1
    assert all(value == missing_degree for value in column_degrees)
    assert plant_right not in missing[plant_left]
    return [
        "".join("0" if y in row else "1" for y in range(n))
        for row in missing
    ]


def make_instance(n, seed=0, **params):
    """Inverse-generate a Theorem 2.2 General d-Position instance.

    One local representative per colour is sampled first.  Each regular
    colour-pair graph is then conditioned to contain the corresponding planted
    edge.  H_t and G' are represented by the paper's exact symbolic recipe; no
    clique or general-position set is solved for during generation.
    """
    classes = params.pop("classes", 22)
    degree = params.pop(
        "degree", max(1, min(n - 1, round(n ** (1.0 - 2.0 / (classes - 1)))))
    )
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, classes, degree, seed)
    rng = random.Random(seed)

    planted_local = [rng.randrange(n) for _ in range(classes)]
    labels = list(range(1, n * classes + 1))
    rng.shuffle(labels)
    colours = []
    cursor = 0
    for _ in range(classes):
        block = labels[cursor:cursor + n]
        cursor += n
        rng.shuffle(block)
        colours.append(block)

    compatibility = []
    for left in range(classes):
        for right in range(left + 1, classes):
            compatibility.append({
                "left": left,
                "right": right,
                "rows": _regular_pair(
                    n,
                    degree,
                    planted_local[left],
                    planted_local[right],
                    rng,
                ),
            })

    answer = [colours[i][planted_local[i]] for i in range(classes)]
    t = n * classes
    inst = {
        "paper": "arXiv:2005.08095",
        "family": "Section 2 H_t reduction from Maximum Clique",
        "recipe": "theorem-2.2-Ht-join-v1",
        "n": n,
        "color_count": classes,
        "cross_degree": degree,
        "G_order_t": t,
        "d": t,
        "Ht_order": 6 * t - 3,
        "Gprime_order": 7 * t - 3,
        "fixed_Ht_certificate_size": 4 * t,
        "target_size": 4 * t + classes,
        "colors": colours,
        "compatibility": compatibility,
        "answer": answer,
    }
    inst["_compat_cache"] = {
        (rec["left"], rec["right"]): rec["rows"] for rec in compatibility
    }
    owner = {}
    local = {}
    for colour, block in enumerate(colours):
        for position, label in enumerate(block):
            owner[label] = colour
            local[label] = position
    inst["_local_cache"] = (owner, local)
    return inst


def _compat_map(inst):
    cached = inst.get("_compat_cache") if isinstance(inst, dict) else None
    if isinstance(cached, dict):
        return cached
    try:
        k = inst["color_count"]
        n = inst["n"]
        result = {}
        for rec in inst["compatibility"]:
            i, j, rows = rec["left"], rec["right"], rec["rows"]
            if not (0 <= i < j < k) or len(rows) != n:
                return None
            if any(
                not isinstance(row, str)
                or len(row) != n
                or set(row) - {"0", "1"}
                for row in rows
            ):
                return None
            result[(i, j)] = rows
        if len(result) != k * (k - 1) // 2:
            return None
        inst["_compat_cache"] = result
        return result
    except (KeyError, TypeError, ValueError):
        return None


def _local_maps(inst):
    cached = inst.get("_local_cache") if isinstance(inst, dict) else None
    if isinstance(cached, tuple) and len(cached) == 2:
        return cached
    try:
        colours = inst["colors"]
        k, n = inst["color_count"], inst["n"]
        if len(colours) != k or any(len(block) != n for block in colours):
            return None
        owner = {}
        local = {}
        for colour, block in enumerate(colours):
            for position, label in enumerate(block):
                if not _is_int(label) or label in owner:
                    return None
                owner[label] = colour
                local[label] = position
        inst["_local_cache"] = (owner, local)
        return owner, local
    except (KeyError, TypeError):
        return None


def _compatible(cmap, local, i, u, j, v):
    if i > j:
        i, j, u, v = j, i, v, u
    return cmap[(i, j)][local[u]][local[v]] == "1"


def verify(inst, answer):
    """Check any valid compact target-size witness; never read ``inst['answer']``."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if any(not _is_int(value) for value in answer):
        return False, "every representative must be an integer vertex label"

    try:
        k, n = inst["color_count"], inst["n"]
        t = inst["G_order_t"]
        if (
            inst.get("recipe") != "theorem-2.2-Ht-join-v1"
            or t != n * k
            or inst["d"] != t
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
    if len(set(answer)) != len(answer):
        return False, "representative labels must be distinct"
    maps = _local_maps(inst)
    cmap = _compat_map(inst)
    if maps is None or cmap is None:
        return False, "malformed instance data"
    owner, local = maps
    for i, label in enumerate(answer):
        if label not in owner:
            return False, f"unknown vertex label {label}"
        if owner[label] != i:
            return False, (
                f"slot {i + 1} requires colour {i + 1}, but label {label} "
                f"belongs to colour {owner[label] + 1}"
            )

    # A union B is a K_{4t}, and Theorem 2.2 joins all of it to every G vertex.
    # Thus its union with the submitted vertices is a clique exactly when the
    # submitted G vertices are a clique.  A clique contains no geodesic triple.
    for i in range(k):
        for j in range(i + 1, k):
            if not _compatible(cmap, local, i, answer[i], j, answer[j]):
                return False, (
                    f"labels {answer[i]} and {answer[j]} are incompatible "
                    f"for colours {i + 1} and {j + 1}"
                )
    # The target asks only for feasibility at this displayed size.  The checker
    # therefore needs no non-executable optimality claim: completeness of the
    # expanded induced graph directly proves the geodesic condition.
    return True, "ok"


def render(inst):
    k, n, t = inst["color_count"], inst["n"], inst["G_order_t"]
    example = [block[0] for block in inst["colors"]]
    lines = [
        "Find a prescribed-size general d-position set in a graph given by a compact recipe.",
        "",
        "Definitions.",
        "For vertices x,y, dist(x,y) is the minimum number of edges on an x-y path.",
        "A geodesic is a path whose length equals that distance. A set S is in",
        "general d-position when no three distinct vertices of S occur on one",
        "geodesic of length at most d.",
        "",
        f"There are k={k} colour classes C1,...,C{k}, each containing n={n}",
        f"vertices. Their disjoint union is a graph G of order t={t}. There are no",
        "edges inside a colour class. Between each pair of classes, edges are given",
        "by the compatibility matrices below.",
        "",
        "The full graph G' is the following Section 2 construction.",
        f"1. Make H_t. Its sets A={{a1,...,a{2*t}}} and B={{b1,...,b{2*t}}}",
        f"   together induce a complete graph K_{4*t}.",
        f"2. Add the path v1-v2-...-v{t-1}. Join every vertex of B to v1.",
        f"3. For every i from 2 through {t-1}, add u_i adjacent to v_i and v_(i-1).",
        "   There are no other H_t edges.",
        "4. Take the disjoint union of H_t and G, then join every G vertex to every",
        "   vertex of A, every vertex of B, and v1. Add no other cross edges.",
        f"The resulting G' has {inst['Gprime_order']} vertices. Here d=t={t}.",
        "",
        f"Your compact answer must give exactly one vertex label from each C_i, in",
        f"the order C1,...,C{k}. The checker expands it to S=A union B union your",
        f"{k} submitted vertices and checks the graph conditions. The required",
        f"expanded-set size is exactly {inst['target_size']}.",
        "Do not output the A or B vertices themselves.",
        "",
        "Matrix convention.",
        "For PAIR Ci Cj with i<j, rows follow the printed order of Ci and bit",
        "positions follow the printed order of Cj. Bit 1 means an edge; bit 0 means",
        "no edge. Positions in this explanation are 1-based. Slash-separated bit",
        "strings are consecutive rows. Decimal labels are arbitrary identifiers.",
        "",
        "Colour classes (in answer-slot order):",
    ]
    for i, block in enumerate(inst["colors"], 1):
        lines.append(f"  C{i}: " + " ".join(map(str, block)))
    lines.extend(["", "Compatibility matrices:"])
    for rec in inst["compatibility"]:
        i, j = rec["left"] + 1, rec["right"] + 1
        lines.append(f"  PAIR C{i} C{j}: " + "/".join(rec["rows"]))
    lines.extend([
        "",
        f"Output exactly {k} distinct decimal labels as a JSON list. Entry i must",
        "belong to Ci. Order is significant, repeats are forbidden, and all displayed",
        "bounds are inclusive.",
        "",
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
    """Uniformly sample after enforcing arity and one vertex per colour."""
    return [rng.choice(block) for block in inst["colors"]]


def search_space(inst):
    try:
        return inst["n"] ** inst["color_count"]
    except (KeyError, TypeError, ValueError):
        return None


def enumerate_all(inst):
    space = search_space(inst)
    if space is None or space > 1_000_000:
        return None
    return sum(
        int(verify(inst, list(candidate))[0])
        for candidate in itertools.product(*inst["colors"])
    )


def _intersection_spectrum(masks):
    return sorted(
        (masks[i] & masks[j]).bit_count()
        for i in range(len(masks))
        for j in range(i + 1, len(masks))
    )


def _pair_signature(rows):
    n = len(rows)
    row_masks = [int(row, 2) for row in rows]
    col_masks = []
    for j in range(n):
        mask = 0
        for i, row in enumerate(rows):
            if row[j] == "1":
                mask |= 1 << i
        col_masks.append(mask)
    a = _intersection_spectrum(row_masks)
    b = _intersection_spectrum(col_masks)
    if b < a:
        a, b = b, a
    four_cycles = sum(x * (x - 1) // 2 for x in a)
    return [four_cycles, a, b]


def canonical_key(inst):
    """Strong cheap invariant under colour, row, column, and label relabelling.

    Exact canonicalisation contains coloured graph isomorphism.  The sorted pair
    signatures use both row- and column-common-neighbour spectra and exact
    four-cycle counts.  They are invariant but can theoretically collide on
    nonisomorphic adversarial graphs; the README records that caveat.
    """
    cmap = _compat_map(inst)
    if cmap is None:
        return "general-d-position-Ht:malformed"
    signatures = sorted(_pair_signature(rows) for rows in cmap.values())
    payload = [inst["color_count"], inst["n"], inst["cross_degree"], signatures]
    digest = hashlib.sha256(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return "general-d-position-Ht-v1:" + digest


def escalate(params):
    """Grow the colour classes while keeping the answer length fixed."""
    if not isinstance(params, dict) or "n" not in params:
        return None
    n = int(params["n"])
    classes = int(params.get("classes", 22))
    new_n = n + 8
    return {
        "n": new_n,
        "classes": classes,
        "degree": max(
            1,
            min(new_n - 1, round(new_n ** (1.0 - 2.0 / (classes - 1)))),
        ),
    }


# ---------------------------------------------------------------------------
# Construction-aware attacks.  Each uses only rendered instance data.


def _adjacency_masks(inst):
    cached = inst.get("_mask_cache") if isinstance(inst, dict) else None
    if isinstance(cached, list):
        return cached
    cmap = _compat_map(inst)
    if cmap is None:
        return None
    k, n = inst["color_count"], inst["n"]
    masks = [[[0] * k for _ in range(n)] for _ in range(k)]
    for (i, j), rows in cmap.items():
        for x, bits in enumerate(rows):
            masks[i][x][j] = int(bits[::-1], 2)
        for y in range(n):
            reverse = 0
            for x, bits in enumerate(rows):
                if bits[y] == "1":
                    reverse |= 1 << x
            masks[j][y][i] = reverse
    inst["_mask_cache"] = masks
    return masks


def _local_answer(inst, local_values):
    if local_values is None:
        return None
    return [inst["colors"][i][x] for i, x in enumerate(local_values)]


def _attack_outlier(inst):
    """Choose maximum triangle participation independently in each colour."""
    masks = _adjacency_masks(inst)
    if masks is None:
        return None
    k, n = inst["color_count"], inst["n"]
    chosen = []
    for i in range(k):
        scores = []
        for x in range(n):
            score = 0
            for j in range(k):
                if j == i:
                    continue
                bits = masks[i][x][j]
                while bits:
                    low = bits & -bits
                    y = low.bit_length() - 1
                    bits -= low
                    for h in range(j + 1, k):
                        if h != i:
                            score += (
                                masks[i][x][h] & masks[j][y][h]
                            ).bit_count()
            scores.append((score, -inst["colors"][i][x], x))
        chosen.append(max(scores)[2])
    return _local_answer(inst, chosen)


def _greedy_once(inst, masks, rng=None):
    k, n = inst["color_count"], inst["n"]
    domains = [(1 << n) - 1 for _ in range(k)]
    assigned = [-1] * k
    for _ in range(k):
        colour = min(
            (i for i in range(k) if assigned[i] < 0),
            key=lambda i: (domains[i].bit_count(), i),
        )
        bits = domains[colour]
        if not bits:
            return None
        candidates = []
        while bits:
            low = bits & -bits
            value = low.bit_length() - 1
            bits -= low
            score = sum(
                (domains[j] & masks[colour][value][j]).bit_count()
                for j in range(k)
                if assigned[j] < 0 and j != colour
            )
            candidates.append((score, value))
        best_score = max(score for score, _ in candidates)
        best = [value for score, value in candidates if score == best_score]
        value = rng.choice(best) if rng is not None else min(best)
        assigned[colour] = value
        for j in range(k):
            if assigned[j] < 0:
                domains[j] &= masks[colour][value][j]
    return _local_answer(inst, assigned)


def _attack_greedy(inst):
    masks = _adjacency_masks(inst)
    return None if masks is None else _greedy_once(inst, masks)


def _attack_random_restart(inst, rng, restarts=64):
    masks = _adjacency_masks(inst)
    if masks is None:
        return None
    for _ in range(restarts):
        candidate = _greedy_once(inst, masks, rng)
        if candidate is not None and verify(inst, candidate)[0]:
            return candidate
    return None


def _attack_spectral(inst, iterations=14):
    """Centred power iteration on the multipartite compatibility graph."""
    masks = _adjacency_masks(inst)
    if masks is None:
        return None
    k, n, degree = inst["color_count"], inst["n"], inst["cross_degree"]
    rng = random.Random(0x200508095)
    vector = [
        [rng.randrange(-1000, 1001) / 1000.0 for _ in range(n)]
        for _ in range(k)
    ]
    for _ in range(iterations):
        sums = [sum(block) for block in vector]
        nxt = [[0.0] * n for _ in range(k)]
        for i in range(k):
            for x in range(n):
                value = 0.0
                for j in range(k):
                    if i == j:
                        continue
                    bits = masks[i][x][j]
                    neighbour_sum = 0.0
                    while bits:
                        low = bits & -bits
                        y = low.bit_length() - 1
                        bits -= low
                        neighbour_sum += vector[j][y]
                    value += neighbour_sum - (degree / n) * sums[j]
                nxt[i][x] = value
        norm = math.sqrt(sum(v * v for block in nxt for v in block)) or 1.0
        vector = [[v / norm for v in block] for block in nxt]
    for sign in (1.0, -1.0):
        local_values = [
            max(range(n), key=lambda x: (sign * vector[i][x], -x))
            for i in range(k)
        ]
        candidate = _local_answer(inst, local_values)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _attack_exact(inst, node_budget=_EXACT_NODE_BUDGET):
    """Exact MRV clique search with forward checking and measured counters."""
    masks = _adjacency_masks(inst)
    if masks is None:
        return None, {"nodes": 0, "updates": 0, "exhausted": False}
    k, n = inst["color_count"], inst["n"]
    domains = [(1 << n) - 1 for _ in range(k)]
    assigned = [-1] * k
    nodes = 0
    updates = 0
    exhausted = False

    def dfs(depth):
        nonlocal nodes, updates, exhausted
        nodes += 1
        if nodes > node_budget:
            exhausted = True
            return None
        if depth == k:
            return assigned[:]
        colour = min(
            (i for i in range(k) if assigned[i] < 0),
            key=lambda i: (domains[i].bit_count(), i),
        )
        bits = domains[colour]
        while bits and not exhausted:
            low = bits & -bits
            value = low.bit_length() - 1
            bits -= low
            assigned[colour] = value
            changes = []
            feasible = True
            for j in range(k):
                if assigned[j] >= 0:
                    continue
                new_domain = domains[j] & masks[colour][value][j]
                updates += 1
                if new_domain != domains[j]:
                    changes.append((j, domains[j]))
                    domains[j] = new_domain
                if not new_domain:
                    feasible = False
                    break
            if feasible:
                found = dfs(depth + 1)
                if found is not None:
                    return found
            for j, old_domain in reversed(changes):
                domains[j] = old_domain
            assigned[colour] = -1
        return None

    found = dfs(0)
    return _local_answer(inst, found), {
        "nodes": nodes,
        "updates": updates,
        "exhausted": exhausted,
    }


def _relabel_instance(inst, rng):
    """Permute colours, vertices, and labels, carrying the planted witness."""
    k, n = inst["color_count"], inst["n"]
    old_cmap = _compat_map(inst)
    maps = _local_maps(inst)
    if old_cmap is None or maps is None:
        raise ValueError("malformed instance")
    old_owner, _ = maps

    colour_order = list(range(k))
    rng.shuffle(colour_order)
    old_positions_for_new = []
    label_map = {}
    all_new_labels = list(range(10_000_001, 10_000_001 + k * n))
    rng.shuffle(all_new_labels)
    cursor = 0
    new_colours = []
    for old_i in colour_order:
        order = list(range(n))
        rng.shuffle(order)
        old_positions_for_new.append(order)
        block = []
        for old_pos in order:
            old_label = inst["colors"][old_i][old_pos]
            new_label = all_new_labels[cursor]
            cursor += 1
            label_map[old_label] = new_label
            block.append(new_label)
        new_colours.append(block)

    new_compatibility = []
    for a in range(k):
        old_a = colour_order[a]
        for b in range(a + 1, k):
            old_b = colour_order[b]
            rows = []
            for old_x in old_positions_for_new[a]:
                bits = []
                for old_y in old_positions_for_new[b]:
                    if old_a < old_b:
                        bit = old_cmap[(old_a, old_b)][old_x][old_y]
                    else:
                        bit = old_cmap[(old_b, old_a)][old_y][old_x]
                    bits.append(bit)
                rows.append("".join(bits))
            new_compatibility.append({"left": a, "right": b, "rows": rows})

    old_answer_by_colour = {old_owner[label]: label for label in inst["answer"]}
    new_answer = [label_map[old_answer_by_colour[old_i]] for old_i in colour_order]
    transformed = {
        key: value
        for key, value in inst.items()
        if key not in {"colors", "compatibility", "answer"}
        and not key.startswith("_")
    }
    transformed["colors"] = new_colours
    transformed["compatibility"] = new_compatibility
    transformed["answer"] = new_answer
    return transformed


def _corruptions(inst):
    answer = list(inst["answer"])
    corrupt = {
        "empty": [],
        "drop_one": answer[:-1],
        "duplicate": [answer[1]] + answer[1:],
        "out_of_range": [max(max(block) for block in inst["colors"]) + 1] + answer[1:],
        "swap_slots": answer[1:2] + answer[0:1] + answer[2:],
    }
    replacement = None
    for slot, block in enumerate(inst["colors"]):
        for label in block:
            if label == answer[slot]:
                continue
            candidate = answer[:]
            candidate[slot] = label
            if not verify(inst, candidate)[0]:
                replacement = candidate
                break
        if replacement is not None:
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
                    "preset": preset,
                    "seed": seed,
                    "reason": "answer is not JSON-native",
                })
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checked": checks,
        "failures": failures,
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
        "The H_t extension reduces the remaining choice to G.\n\n"
        "<answer>```json\n"
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
    guess_hits = 0
    for _ in range(_GUESS_SAMPLES):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
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
        "outlier_triangle_participation": {"successes": 0, "attempts": 8},
        "greedy_max_future_compatibility": {"successes": 0, "attempts": 8},
        "random_restart_64": {"successes": 0, "attempts": 8},
        "spectral_centered_power_iteration": {"successes": 0, "attempts": 8},
        "standard_exact_clique_mrv_500k": {"successes": 0, "attempts": 8},
    }
    exact_nodes = []
    exact_updates = []
    exact_walls = []
    exact_exhaustions = 0
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **shipping_params)
        candidates = {
            "outlier_triangle_participation": _attack_outlier(inst),
            "greedy_max_future_compatibility": _attack_greedy(inst),
            "random_restart_64": _attack_random_restart(
                inst, random.Random(seed ^ 0xD905), 64
            ),
            "spectral_centered_power_iteration": _attack_spectral(inst),
        }
        start = time.perf_counter()
        exact_candidate, counters = _attack_exact(inst)
        exact_walls.append(time.perf_counter() - start)
        exact_nodes.append(counters["nodes"])
        exact_updates.append(counters["updates"])
        exact_exhaustions += int(counters["exhausted"])
        candidates["standard_exact_clique_mrv_500k"] = exact_candidate
        for name, candidate in candidates.items():
            if candidate is not None and verify(inst, candidate)[0]:
                attack_results[name]["successes"] += 1

    all_attacks_failed = all(item["successes"] == 0 for item in attack_results.values())
    report["G5_density_and_baseline"] = {
        "pass": guess_hits / _GUESS_SAMPLES < 1e-6 and exact_exhaustions == 8,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": _GUESS_SAMPLES,
        "shipping_solution_fraction_estimate": guess_hits / _GUESS_SAMPLES,
        "baseline_wall_clock_sec_mean": sum(exact_walls) / len(exact_walls),
        "baseline_wall_clock_sec_max": max(exact_walls),
        "baseline_nodes_mean": sum(exact_nodes) / len(exact_nodes),
        "baseline_nodes_max": max(exact_nodes),
        "baseline_compatibility_updates_mean": sum(exact_updates) / len(exact_updates),
        "baseline_budget_exhaustions": exact_exhaustions,
        "demo_exact_valid_answers": enumerate_all(
            make_instance(seed=5, **DIFFICULTY["demo"])
        ),
        "demo_candidate_space": search_space(
            make_instance(seed=5, **DIFFICULTY["demo"])
        ),
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed,
        "attacks": attack_results,
        "seeds": attack_seeds,
        "standard_algorithm": (
            "exact multicoloured-clique/CSP search with MRV and forward checking"
        ),
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled_params["degree"] = round(
        doubled_params["n"]
        ** (1.0 - 2.0 / (doubled_params["classes"] - 1))
    )
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
    for seed in range(20):
        inst = make_instance(seed=20_000 + seed, **shipping_params)
        key = canonical_key(inst)
        unrelated_keys.append(key)
        for turn in range(2):
            transformed = _relabel_instance(
                inst, random.Random(30_000 + 17 * seed + turn)
            )
            invariant_checks += 1
            if canonical_key(transformed) != key:
                key_failures.append({"seed": seed, "turn": turn, "kind": "key"})
            ok, why = verify(transformed, transformed["answer"])
            witness_checks += 1
            if not ok:
                key_failures.append({
                    "seed": seed,
                    "turn": turn,
                    "kind": "witness",
                    "reason": why,
                })
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "real_transformation_witness_checks": witness_checks,
        "unrelated_instances": 20,
        "unrelated_distinct_keys": distinct,
        "failures": key_failures,
        "invariant": (
            "sorted row/column common-neighbour spectra and exact four-cycle "
            "counts for every colour-pair graph"
        ),
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(shipping["answer"])
    intended_ops = shipping["color_count"] * (shipping["color_count"] - 1) // 2
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else None
    )
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else None
    )
    hinted_minus_placebo = (
        hinted_rate - placebo_rate
        if hinted_rate is not None and placebo_rate is not None
        else None
    )
    within_caps = (
        answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
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
