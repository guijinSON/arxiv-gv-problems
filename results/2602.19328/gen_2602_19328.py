"""Verified generator for arXiv:2602.19328.

The family is the weighted, restricted edge-insertion construction in Section
4.1 / Theorem 4(ii), instantiated with a planted affine exact cover.  Generation
never solves the instance: a complete affine line is sampled first and the graph
is built around it.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time


# Keep the repository helper library importable when this module is run from its
# own results directory.  This certificate needs only integer arithmetic, so the
# standard-library fallback is complete.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import rationals  # noqa: F401
except ImportError:  # pragma: no cover - the module remains dependency-free
    rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "positively weighted graph encoded by vertex classes and exact edge rules",
        "distinguished graph edge",
        "set of weighted edge insertions",
    ],
    "verification_operations": [
        "set-union recomputation of covered graph-neighbor classes",
        "exact integer evaluation of the Ollivier-Ricci curvature numerator",
        "strict sign comparison",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 4.1, proof of Theorem 4(ii): the maximum-coverage instance is "
        "mapped to a weighted restricted-insertion curvature instance"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "The useful set-neighbor insertions form a parallel class of affine "
        "triples; without recognizing that symmetry one faces a large exact-cover search."
    ),
    "hardness_basis": (
        "Track B: although Theorem 4(ii) places weighted restricted insertion "
        "with weights {1,2,3} and b=1 in an NP-complete regime, this affine "
        "subdistribution has an O(n+q^3) exhaustive affine-line scan; at the "
        "shipping medium preset (q=73,n=1400) it averaged 4,229 hash probes "
        "(7,250 maximum) and 0.0011 s per instance on this machine, while a solver that spots the "
        "parallel-line symmetry needs at most 2q=146 modular arithmetic steps."
    ),
    "max_answer_tokens": 296,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object with exactly q distinct unit-weight edges [\"T\",\"Si\",1], "
        "where 0 <= i < n; edge order is immaterial."
    ),
    "bounds": {
        "n_insertions": "q",
        "left_endpoint": "T",
        "right_endpoint_index": "0..n-1",
        "edge_weight": 1,
        "distinct": True,
    },
}

DIFFICULTY = {
    "demo": {"n": 11, "q": 5},
    "easy": {"n": 900, "q": 59},
    "medium": {"n": 1400, "q": 73},
    "hard": {"n": 1800, "q": 83},
}

SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "The useful incidence triples lie on a single affine line in the (x,y) plane over the displayed prime field."
)
PLACEBO_HINT = (
    "The useful insertion list rewards careful attention to the vertex labels and the displayed prime field throughout."
)

# Filled with the harness measurements after the three isolated oracle runs.
G9_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 2, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
}

NOTES = (
    "Section 2.2 fixes the restricted insertion and negative-to-positive sign "
    "conventions. Section 4.1 and Theorem 4(ii) fix the hard weighted regime: "
    "weights are 1, 2, or 3 and b=1; its proof supplies the maximum-coverage "
    "graph construction used here. Theorems 5, 6, and 11 are the easy regime "
    "to avoid: their polynomial algorithms apply to unweighted restricted insertion, not this "
    "weighted family. The certificate is generated before the graph by choosing "
    "an affine line y=ax+b whose q triples exactly cover the three coordinate "
    "classes. Replication by q+4 is the proof's gap-amplification idea and makes "
    "positive curvature equivalent to exact cover. Plants and decoys have the "
    "same single-triple marginal distribution. Degree-outlier, greedy coverage, "
    "256 random restarts, and the obvious slope-one ansatz are tested and fail; "
    "the complete affine-line scan is disclosed as the successful Track B "
    "reference algorithm."
)


_ANSWER_TAG_RE = re.compile(r"<answer>(.*?)</answer>", re.IGNORECASE | re.DOTALL)
_SET_NAME_RE = re.compile(r"^S(0|[1-9][0-9]*)$")


def _is_prime(value: int) -> bool:
    if not isinstance(value, int) or isinstance(value, bool) or value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    limit = math.isqrt(value)
    for divisor in range(3, limit + 1, 2):
        if value % divisor == 0:
            return False
    return True


def _answer_from_indices(indices) -> dict:
    return {
        "insertions": [["T", "S%d" % i, 1] for i in sorted(indices)]
    }


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate an affine exact cover, then apply the paper's reduction."""
    q = params.pop("q", None)
    if params:
        raise TypeError("unknown parameters: %s" % sorted(params))
    if not isinstance(n, int) or isinstance(n, bool):
        raise ValueError("n must be an integer")
    if not _is_prime(q) or q < 5:
        raise ValueError("q must be an odd prime at least 5")
    if not (q <= n <= q * q):
        raise ValueError("n must satisfy q <= n <= q^2")

    rng = random.Random(seed)

    # Excluding 0 and -1 makes x, y, and z=x+y all permutations along the
    # line.  Excluding slope 1 leaves it as a genuine failing by-hand ansatz.
    slopes = [a for a in range(q) if a not in (0, 1, q - 1)]
    planted_slope = rng.choice(slopes)
    planted_intercept = rng.randrange(q)
    triples = [
        [x, (planted_slope * x + planted_intercept) % q]
        for x in range(q)
    ]
    planted_points = {tuple(pair) for pair in triples}

    # Averaged over the random affine line, both a planted point and a decoy
    # have the uniform single-point marginal on F_q^2.  Only their joint
    # correlation differs, which is exactly the intended hidden structure.
    seen = set(planted_points)
    while len(triples) < n:
        pair = (rng.randrange(q), rng.randrange(q))
        if pair not in seen:
            seen.add(pair)
            triples.append([pair[0], pair[1]])

    tagged = [(pair, tuple(pair) in planted_points) for pair in triples]
    rng.shuffle(tagged)
    triples = [list(pair) for pair, _ in tagged]
    planted_indices = [i for i, (_, planted) in enumerate(tagged) if planted]

    replication = q + 4
    base_elements = 3 * q
    element_vertices = replication * base_elements
    sink_vertices = 2 * element_vertices + 2 * n - 2
    delta = 3 * (element_vertices + n)

    inst = {
        "family": "weighted_restricted_insertion_affine_cover",
        "n": n,
        "q": q,
        "triples": triples,
        "replication": replication,
        "base_elements": base_elements,
        "element_vertices": element_vertices,
        "sink_vertices": sink_vertices,
        "delta": delta,
        "answer": _answer_from_indices(planted_indices),
    }
    return inst


def _graph_description(inst) -> str:
    q = inst["q"]
    n = inst["n"]
    r = inst["replication"]
    ne = inst["element_vertices"]
    ns = inst["sink_vertices"]
    lines = [
        "  S%d: (%d,%d,%d)" % (i, x, y, (x + y) % q)
        for i, (x, y) in enumerate(inst["triples"])
    ]
    return "\n".join([
        "The prime is q=%d; all coordinate arithmetic below is modulo q." % q,
        "Vertices are U,V,T; set vertices S0,...,S%d; element-copy vertices "
        "EX[x,r], EY[y,r], EZ[z,r] for 0<=x,y,z<q and 0<=r<%d; and sink "
        "vertices D0,...,D%d." % (n - 1, r, ns - 1),
        "The undirected weighted edges are exactly these:",
        "  {U,V} has weight 2 and {U,T} has weight 3.",
        "  V is joined with weight 3 to every set vertex and every element-copy vertex.",
        "  V is joined with weight 1 to every sink vertex.",
        "  Every two distinct set vertices are joined with weight 1.",
        "  If Si has triple (x,y,z), Si is joined with weight 1 to EX[x,r], "
        "EY[y,r], and EZ[z,r] for every 0<=r<%d." % r,
        "There are no other edges. Thus there are %d element-copy vertices and %d sinks." % (ne, ns),
        "The set-vertex triples are:",
        *lines,
    ])


def render(inst) -> str:
    q = inst["q"]
    n = inst["n"]
    delta = inst["delta"]
    # A complete, parseable format example avoids teaching the solver to emit
    # ellipses.  It illustrates syntax only and is not claimed to solve the
    # displayed instance.
    example_edges = [["T", "S%d" % i, 1] for i in range(q)]

    statement = f"""Critical-edge intervention in a weighted graph

For a vertex A, its closed neighborhood consists of A and every adjacent vertex.
Put the uniform probability distribution on each closed neighborhood. For two
adjacent vertices A,B, the earth mover distance EMD(A,B) is the minimum, over all
nonnegative shipments from A's closed neighborhood to B's closed neighborhood,
of the sum of (shipped mass)*(weighted shortest-path distance), with every source
sending its full mass and every destination receiving its full mass. The
Ollivier-Ricci curvature of edge {{A,B}} is

    Ric(A,B) = 1 - EMD(A,B)/dist(A,B).

{_graph_description(inst)}

The distinguished edge is {{U,V}}. Its initial curvature is exactly
(2-{delta})/{delta}, which is negative.

Choose exactly {q} DISTINCT set vertices. For every chosen Si, insert the new
undirected edge {{T,Si}} with weight 1; no other insertion is permitted. The
closed neighborhoods of U and V therefore do not change. Your inserted edges
must make Ric(U,V) strictly positive (zero is not accepted).

Exact checking identity: if c is the number of distinct base labels among
X_x, Y_y, and Z_z occurring in the chosen triples, then the post-insertion
curvature is

    (({q}+4)*c + {q}+4 - {inst['element_vertices']}) / (6*({inst['element_vertices']}+{n})).

This identity is an exact rational equality, not a floating-point approximation.
Indices are 0-based; edge order does not matter; repeats are forbidden.

Give your final answer inside <answer></answer> tags as one JSON object with key
"insertions" and exactly {q} entries ["T","Si",1].
Example shape: <answer>{{"insertions": {json.dumps(example_edges, separators=(',', ':'))}}}</answer>
Output nothing else inside the tags."""

    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    if not isinstance(text, str):
        return None
    matches = _ANSWER_TAG_RE.findall(text)
    bodies = list(reversed(matches))
    if not bodies:
        fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
        bodies = list(reversed(fenced))
    for body in bodies:
        cleaned = body.strip()
        fence = re.fullmatch(r"```(?:json)?\s*(.*?)```", cleaned, re.IGNORECASE | re.DOTALL)
        if fence:
            cleaned = fence.group(1).strip()
        try:
            return json.loads(cleaned)
        except (TypeError, ValueError):
            continue
    return None


def _decode_indices(inst, answer):
    if not isinstance(answer, dict) or set(answer) != {"insertions"}:
        return None, "answer must be one JSON object with only the key 'insertions'"
    edges = answer["insertions"]
    if not isinstance(edges, list):
        return None, "insertions must be a JSON list"
    if not edges:
        return None, "insertion list is empty"
    if len(edges) != inst["q"]:
        return None, "expected exactly %d insertions, received %d" % (inst["q"], len(edges))

    indices = []
    for edge in edges:
        if not isinstance(edge, (list, tuple)) or len(edge) != 3:
            return None, "every insertion must be a three-item weighted edge"
        left, right, weight = edge
        if left != "T":
            return None, "every insertion must have T as its first endpoint"
        if weight != 1 or isinstance(weight, bool):
            return None, "every inserted edge must have integer weight 1"
        if not isinstance(right, str):
            return None, "each second endpoint must be a set-vertex name Si"
        match = _SET_NAME_RE.fullmatch(right)
        if not match:
            return None, "only set vertices Si are legal second endpoints"
        index = int(match.group(1))
        if index >= inst["n"]:
            return None, "unknown set vertex %s" % right
        indices.append(index)
    if len(set(indices)) != len(indices):
        return None, "duplicate insertion edge"
    return indices, "ok"


def _covered_base_count(inst, indices) -> int:
    q = inst["q"]
    xs, ys, zs = set(), set(), set()
    for index in indices:
        x, y = inst["triples"][index]
        xs.add(x)
        ys.add(y)
        zs.add((x + y) % q)
    return len(xs) + len(ys) + len(zs)


def verify(inst, answer) -> tuple[bool, str]:
    indices, reason = _decode_indices(inst, answer)
    if indices is None:
        return False, reason
    covered = _covered_base_count(inst, indices)
    numerator = (
        inst["replication"] * covered
        + inst["q"] + 4
        - inst["element_vertices"]
    )
    denominator = 6 * (inst["element_vertices"] + inst["n"])
    if numerator <= 0:
        return False, (
            "curvature is not positive: numerator %d over denominator %d; "
            "the triples cover %d of %d base labels"
            % (numerator, denominator, covered, inst["base_elements"])
        )
    return True, "ok"


def random_candidate(inst, rng) -> object:
    if not hasattr(rng, "sample"):
        raise TypeError("rng must provide sample()")
    return _answer_from_indices(rng.sample(range(inst["n"]), inst["q"]))


def search_space(inst) -> int | None:
    return math.comb(inst["n"], inst["q"])


def enumerate_all(inst) -> int | None:
    space = search_space(inst)
    if space is None or space > 100_000:
        return None
    total = 0
    for indices in itertools.combinations(range(inst["n"]), inst["q"]):
        if verify(inst, _answer_from_indices(indices))[0]:
            total += 1
    return total


def canonical_key(inst) -> str:
    """Strong cheap hypergraph invariant, independent of vertex/set labels.

    Full 3-uniform hypergraph isomorphism is not attempted.  The invariant keeps
    the degree multiset and, for every hyperedge, the unordered degrees of its
    three incident base vertices.  It is invariant under arbitrary base-vertex
    and set relabellings and is much stronger than a seed/render hash.
    """
    q = inst["q"]
    dx = [0] * q
    dy = [0] * q
    dz = [0] * q
    for x, y in inst["triples"]:
        dx[x] += 1
        dy[y] += 1
        dz[(x + y) % q] += 1
    edge_signatures = sorted(
        sorted((dx[x], dy[y], dz[(x + y) % q]))
        for x, y in inst["triples"]
    )
    payload = {
        "q": q,
        "n": inst["n"],
        "replication": inst["replication"],
        "degrees": sorted(dx + dy + dz),
        "edge_degree_signatures": edge_signatures,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def escalate(params) -> dict | str | None:
    p = {k: v for k, v in params.items() if k != "_preset"}
    n = int(p["n"])
    q = int(p["q"])
    if n < q * q:
        # More decoys at fixed q: the answer stays exactly 3q atoms.
        p["n"] = min(q * q, max(n + 1, (3 * n + 1) // 2))
        return p
    # q=83 already uses 249 of the 256 atomic-element allowance.  The next
    # supported prime would exceed the cap, so this is genuinely cap-bound.
    if q >= 83:
        return "cap_bound"
    for candidate in range(q + 2, 84):
        if _is_prime(candidate):
            p["q"] = candidate
            p["n"] = min(candidate * candidate, max(n, 4 * candidate))
            return p
    return "cap_bound"


# ---- attacks and exact Track-B reference algorithm -----------------------

def _attack_outlier_frequency(inst):
    q = inst["q"]
    dx = [0] * q
    dy = [0] * q
    dz = [0] * q
    for x, y in inst["triples"]:
        dx[x] += 1
        dy[y] += 1
        dz[(x + y) % q] += 1
    target = 3 * inst["n"] / q
    ranked = sorted(
        range(inst["n"]),
        key=lambda i: (
            abs(
                dx[inst["triples"][i][0]]
                + dy[inst["triples"][i][1]]
                + dz[sum(inst["triples"][i]) % q]
                - target
            ),
            i,
        ),
    )
    return _answer_from_indices(ranked[:q]), inst["n"]


def _attack_greedy_new_coordinates(inst):
    q = inst["q"]
    used_x, used_y, used_z = set(), set(), set()
    remaining = set(range(inst["n"]))
    chosen = []
    scans = 0
    for _ in range(q):
        best = None
        best_score = -1
        for i in remaining:
            x, y = inst["triples"][i]
            z = (x + y) % q
            score = int(x not in used_x) + int(y not in used_y) + int(z not in used_z)
            scans += 1
            if score > best_score or (score == best_score and (best is None or i < best)):
                best, best_score = i, score
        chosen.append(best)
        remaining.remove(best)
        x, y = inst["triples"][best]
        used_x.add(x)
        used_y.add(y)
        used_z.add((x + y) % q)
    return _answer_from_indices(chosen), scans


def _attack_random_restart(inst, rng, restarts=256):
    q = inst["q"]
    best = []
    scans = 0
    base_order = list(range(inst["n"]))
    for _ in range(restarts):
        order = base_order[:]
        rng.shuffle(order)
        used_x, used_y, used_z = set(), set(), set()
        chosen = []
        for i in order:
            scans += 1
            x, y = inst["triples"][i]
            z = (x + y) % q
            if x in used_x or y in used_y or z in used_z:
                continue
            chosen.append(i)
            used_x.add(x)
            used_y.add(y)
            used_z.add(z)
            if len(chosen) == q:
                return _answer_from_indices(chosen), scans
        if len(chosen) > len(best):
            best = chosen
    filler = [i for i in range(inst["n"]) if i not in set(best)]
    return _answer_from_indices(best + filler[:q - len(best)]), scans


def _attack_slope_one_ansatz(inst):
    q = inst["q"]
    lookup = {tuple(pair): i for i, pair in enumerate(inst["triples"])}
    probes = 0
    for intercept in range(q):
        line = []
        for x in range(q):
            probes += 1
            index = lookup.get((x, (x + intercept) % q))
            if index is None:
                break
            line.append(index)
        if len(line) == q:
            return _answer_from_indices(line), probes
    return _answer_from_indices(range(q)), probes


def _reference_affine_scan(inst):
    """Successful O(n+q^3) algorithm disclosed by the Track B claim."""
    q = inst["q"]
    lookup = {tuple(pair): i for i, pair in enumerate(inst["triples"])}
    probes = 0
    for slope in range(q):
        if slope in (0, q - 1):
            continue
        for intercept in range(q):
            line = []
            for x in range(q):
                probes += 1
                index = lookup.get((x, (slope * x + intercept) % q))
                if index is None:
                    break
                line.append(index)
            if len(line) == q:
                return _answer_from_indices(line), probes
    return None, probes


def _relabel_instance(inst, order, unit, tx, ty, swap_xy=False):
    """Apply a genuine graph relabelling and carry the certificate through it."""
    q = inst["q"]
    transformed = []
    for old_index in order:
        x, y = inst["triples"][old_index]
        x2 = (unit * x + tx) % q
        y2 = (unit * y + ty) % q
        if swap_xy:
            x2, y2 = y2, x2
        transformed.append([x2, y2])
    old_to_new = {old: new for new, old in enumerate(order)}
    planted, why = _decode_indices(inst, inst["answer"])
    if planted is None:
        raise AssertionError(why)
    result = {k: v for k, v in inst.items() if k not in ("triples", "answer")}
    result["triples"] = transformed
    result["answer"] = _answer_from_indices(old_to_new[i] for i in planted)
    return result


def _answer_measurements(answer):
    blob = json.dumps(answer, separators=(",", ":"))

    def atoms(value):
        if isinstance(value, dict):
            return sum(atoms(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return sum(atoms(v) for v in value)
        return 1

    return len(blob), (len(blob) + 3) // 4, atoms(answer)


def selftest() -> dict:
    report = {
        "paper": "2602.19328",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: all rungs, three independent seeds each.
    checked = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 90210):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            checked += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed, "reason": "answer not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "instances_checked": checked,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=271828, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = json.loads(json.dumps(shipping["answer"]))
    edges = planted["insertions"]
    corruptions = {
        "drop_one": {"insertions": edges[:-1]},
        "illegal_endpoint": {"insertions": edges[:-1] + [["U", edges[-1][1], 1]]},
        "duplicate": {"insertions": edges[:-1] + [edges[0]]},
        "empty": {"insertions": []},
        "out_of_range": {"insertions": edges[:-1] + [["T", "S%d" % shipping["n"], 1]]},
    }
    g2_results = {name: verify(shipping, answer) for name, answer in corruptions.items()}
    g2_reasons = [why for ok, why in g2_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not ok for ok, _ in g2_results.values()) and len(set(g2_reasons)) == len(g2_reasons),
        "cases": {name: {"accepted": ok, "reason": why} for name, (ok, why) in g2_results.items()},
        "distinct_reasons": len(set(g2_reasons)),
    }

    response = (
        "I used the repeated incidence pattern.\n```json\n<answer>\n"
        + json.dumps(shipping["answer"])
        + "\n</answer>\n```\n"
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and verify(shipping, parsed)[0],
        "model_style_response_parsed": parsed is not None,
        "round_trip_equal": parsed == shipping["answer"],
    }

    # G4/G5 shipping density measurement from the actual bounded language.
    guess_rng = random.Random(314159265)
    guess_total = 200_000
    guess_hits = 0
    density_start = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(shipping, guess_rng)
        if verify(shipping, candidate)[0]:
            guess_hits += 1
    density_seconds = time.perf_counter() - density_start
    guess_probability = guess_hits / guess_total
    # Every valid selection contains each X-coordinate exactly once, so even in
    # the complete q-by-q candidate grid there are at most q! valid selections.
    # Restricting to the displayed n candidates can only reduce that count.
    analytical_upper_bound = math.factorial(shipping["q"]) / search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": analytical_upper_bound < 1e-6 and guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "analytical_probability_upper_bound": analytical_upper_bound,
        "upper_bound_basis": "at most q! exact covers, since every valid selection uses each X-coordinate once",
        "candidate_space": search_space(shipping),
        "sampling_prior": "uniform q-subsets of the n legal set-neighbor insertions",
        "wall_clock_sec": round(density_seconds, 6),
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)

    attack_names = (
        "outlier_coordinate_frequency",
        "greedy_max_new_coordinates",
        "random_restart_256_disjoint",
        "by_hand_slope_one_ansatz",
    )
    attack_stats = {
        name: {"successes": 0, "attempts": 0, "operations": 0, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    ref_successes = 0
    ref_attempts = 0
    ref_probes = 0
    ref_max_probes = 0
    ref_seconds = 0.0
    for seed in range(8):
        inst = make_instance(seed=7000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        calls = (
            (attack_names[0], lambda: _attack_outlier_frequency(inst)),
            (attack_names[1], lambda: _attack_greedy_new_coordinates(inst)),
            (attack_names[2], lambda: _attack_random_restart(inst, random.Random(81000 + seed), 256)),
            (attack_names[3], lambda: _attack_slope_one_ansatz(inst)),
        )
        for name, call in calls:
            started = time.perf_counter()
            candidate, operations = call()
            elapsed = time.perf_counter() - started
            success = verify(inst, candidate)[0]
            attack_stats[name]["attempts"] += 1
            attack_stats[name]["successes"] += int(success)
            attack_stats[name]["operations"] += operations
            attack_stats[name]["wall_clock_sec"] += elapsed

        started = time.perf_counter()
        candidate, probes = _reference_affine_scan(inst)
        ref_seconds += time.perf_counter() - started
        ref_attempts += 1
        ref_probes += probes
        ref_max_probes = max(ref_max_probes, probes)
        ref_successes += int(candidate is not None and verify(inst, candidate)[0])

    for values in attack_stats.values():
        values["wall_clock_sec"] = round(values["wall_clock_sec"], 6)
    all_attacks_failed = all(values["successes"] == 0 for values in attack_stats.values())
    report["G5_density_and_baseline"] = {
        "pass": guess_hits == 0 and ref_successes == ref_attempts,
        "shipping_valid_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_observed_solution_fraction": guess_probability,
        "shipping_analytical_solution_fraction_upper_bound": analytical_upper_bound,
        "demo_exact_valid_answers": demo_count,
        "demo_candidate_space": search_space(demo),
        "strongest_failing_attack": "random_restart_256_disjoint",
        "strongest_attack_wall_clock_sec_8_seeds": round(
            attack_stats["random_restart_256_disjoint"]["wall_clock_sec"], 6
        ),
        "strongest_attack_candidate_scans_8_seeds": attack_stats["random_restart_256_disjoint"]["operations"],
        "reference_wall_clock_sec_8_seeds": round(ref_seconds, 6),
        "reference_membership_probes_8_seeds": ref_probes,
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and ref_successes == ref_attempts,
        "attacks": attack_stats,
        "reference_algorithm": {
            "name": "exhaustive affine-line scan with hash membership",
            "complexity": "O(n + q^3) time and O(n) space",
            "wall_clock_sec": round(ref_seconds, 6),
            "operations": ref_probes,
            "max_operations_one_instance": ref_max_probes,
            "solves": "%d/%d, as expected" % (ref_successes, ref_attempts),
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=1618033, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(shipping),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_space_bits": search_space(shipping).bit_length(),
        "doubled_space_bits": search_space(doubled).bit_length(),
        "doubled_verify_reason": doubled_why,
    }

    invariant_checks = 0
    preserved_witnesses = 0
    original_keys = []
    for seed in range(20):
        inst = make_instance(n=110, q=23, seed=12000 + seed)
        original_key = canonical_key(inst)
        original_keys.append(original_key)
        rrng = random.Random(13000 + seed)
        order = list(range(inst["n"]))
        rrng.shuffle(order)
        transformed = _relabel_instance(
            inst,
            order,
            unit=rrng.randrange(1, inst["q"]),
            tx=rrng.randrange(inst["q"]),
            ty=rrng.randrange(inst["q"]),
            swap_xy=bool(seed & 1),
        )
        invariant_checks += 1
        invariant_checks += int(canonical_key(transformed) == original_key)
        preserved_witnesses += int(verify(transformed, transformed["answer"])[0])
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 40 and preserved_witnesses == 20 and len(set(original_keys)) == 20,
        "relabelled_instances": 20,
        "key_equalities": invariant_checks - 20,
        "witnesses_preserved": preserved_witnesses,
        "unrelated_distinct_keys": len(set(original_keys)),
        "unrelated_instances": 20,
        "transformations": "set reorder + affine coordinate relabel + optional X/Y swap, composed",
    }

    # Measure the longest serialisation permitted at this shipping preset, not
    # merely the particular planted indices drawn above.
    worst_case_answer = _answer_from_indices(
        range(shipping["n"] - shipping["q"], shipping["n"])
    )
    answer_chars, answer_tokens, answer_elements = _answer_measurements(worst_case_answer)
    hinted = G9_ARM_RESULTS["hinted"]
    placebo = G9_ARM_RESULTS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    intended_ops = 2 * shipping["q"]
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": G9_ARM_RESULTS,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": "too_easy" if hinted["solved"] else "hardened",
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "arms_recorded_not_gated": True,
    }

    gate_values = [v for k, v in report.items() if k.startswith("G") and isinstance(v, dict)]
    report["all_passed"] = all(v.get("pass") is True for v in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
