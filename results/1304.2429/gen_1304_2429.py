"""Verified problem generator for arXiv:1304.2429.

The paper defines an H-factor and studies packings of edge-disjoint tree
factors.  Its most basic tree, K_2, is a perfect matching.  This module builds
a bipartite graph over F_p as a union of affine perfect matchings

    x -> a*x + b  (mod p),

all with one hidden slope and independently sampled intercepts.  Any requested
subset of the affine layers is an exact packing certificate.  Generation knows
the layers by construction and never solves the emitted graph.
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
from collections import Counter


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "graph",
    "certificate_form": "polynomial",
    "native_objects": [
        "bipartite graph with both vertex classes identified with F_p",
        "edge-disjoint K_2-factors (perfect matchings)",
        "degree-one permutation polynomials over F_p",
    ],
    "verification_operations": [
        "exact finite-field affine evaluation",
        "edge-membership comparison",
        "exact vertex-coverage and edge-disjointness checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The sum of the right-neighbor residues is an affine function of the "
        "left residue whose first difference reveals the common slope; without "
        "that invariant, one must pair two full neighbor rows and verify the "
        "resulting affine candidates across the graph."
    ),
    "hardness_basis": (
        "Track B: the exact reference enumerator tests all affine maps determined "
        "by the neighborhoods of 0 and 1 in O(d^2 p) finite-field operations; "
        "at shipping p=509,d=80 it averaged 256,030 exact operations and 0.0161 "
        "seconds over eight seeds, while the neighbor-sum invariant uses at most "
        "186 exact operations."
    ),
    "max_answer_tokens": 14,
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

CERTIFICATE_LANGUAGE = {
    "description": (
        "An unordered list of exactly k distinct affine polynomials "
        "f_i(x)=a*x+b_i over F_p, encoded as decimal coefficient pairs [a,b_i]. "
        "Here 1<=a<p and 0<=b_i<p. Pairwise edge-disjointness over a prime field "
        "forces all k maps to have one common slope, so random candidates already "
        "enforce that freely deducible constraint and use distinct intercepts."
    ),
    "bounds": {
        "number_of_polynomials": "instance value k",
        "degree": 1,
        "coefficient_field": "F_p for the displayed prime p",
        "slope_range": "1..p-1",
        "intercept_range": "0..p-1",
        "distinct_intercepts": True,
        "order_matters": False,
    },
}

DIFFICULTY = {
    "demo": {"n": 7, "layers": 3, "required": 2},
    "easy": {"n": 127, "layers": 20, "required": 4},
    "medium": {"n": 251, "layers": 45, "required": 5},
    "hard": {"n": 509, "layers": 80, "required": 6},
}

SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Across left vertices, the sum of all right-neighbor residues has a constant "
    "finite-field first difference."
)
PLACEBO_HINT = (
    "Across the adjacency rows, careful modular arithmetic and consistent "
    "coefficient formatting are important."
)

# Filled after the script-owned runs.  These are diagnostics, not hardness gates.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 1, "attempts": 3},
    "hinted_verdict": "too_easy",
}

NOTES = (
    "Section 1 fixes the exact object: for t dividing n, an H-factor consists "
    "of vertex-disjoint copies of H covering every vertex, and the paper states "
    "explicitly that a K_2-factor is a perfect matching. The proof of Theorem 1 "
    "in Section 3 builds T-factors by choosing one perfect matching on every "
    "super-edge of the T blow-up; Lemma 3.4 is the source of those matchings. "
    "Theorems 1-3 are asymptotic existence results, not computational-hardness "
    "results, so Track A would be unsupported. The easy algorithm here enumerates "
    "affine maps determined by images of 0 and 1 and checks them exactly. Track B "
    "instead tests recognition of the neighbor-sum invariant. Every generated "
    "layer is an equally valid affine perfect matching; there is no special "
    "planted layer. Uniform degrees defeat degree outliers, the complete field "
    "makes raw edge differences uniform, modular wrap defeats sorted-row and "
    "ordinary-average guesses, and random restarts sample the exact common-slope "
    "certificate language."
)


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
    candidate = max(2, int(value))
    if candidate > 2 and candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 1 if candidate == 2 else 2
    return candidate


def _validate_parameters(n, layers, required):
    if not _is_prime(n) or n < 7:
        raise ValueError("n must be a prime at least 7")
    if not _is_int(layers) or not 2 <= layers < n:
        raise ValueError("layers must be an integer in [2,n)")
    if not _is_int(required) or not 2 <= required <= layers:
        raise ValueError("required must be an integer in [2,layers]")


def _adjacency_from(a, intercepts, p):
    return {
        x: {(a * x + b) % p for b in intercepts}
        for x in range(p)
    }


def _ordinary_average_guess(adjacency, degree, p):
    row0 = adjacency[0]
    row1 = adjacency[1]
    return ((sum(row1) - sum(row0)) // degree) % p


def _rank_pair_guess(adjacency, p):
    row0, row1 = sorted(adjacency[0]), sorted(adjacency[1])
    differences = [(right - left) % p for left, right in zip(row0, row1)]
    counts = Counter(differences)
    return min(differences, key=lambda value: (-counts[value], value))


def make_instance(n, seed=0, layers=8, required=4, **params):
    """Inverse-generate an affine packing and retain a symbolic certificate."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, layers, required)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)

    # Avoid the translation slope a=1 because it is the most obvious ansatz.
    # Reject only two cheap construction signatures, never on the result of a
    # solver: ordinary integer averaging and sorted-row pairing must not reveal a.
    for _ in range(10_000):
        slope = rng.randrange(2, n)
        intercepts = sorted(rng.sample(range(n), layers))
        adjacency = _adjacency_from(slope, intercepts, n)
        if (_ordinary_average_guess(adjacency, layers, n) != slope
                and _rank_pair_guess(adjacency, n) != slope):
            break
    else:
        raise RuntimeError("could not suppress elementary construction signatures")

    rows = [[x, sorted(neighbors)] for x, neighbors in adjacency.items()]
    rng.shuffle(rows)
    for row in rows:
        rng.shuffle(row[1])

    chosen = sorted(intercepts)[:required]
    answer = [[slope, intercept] for intercept in chosen]
    return {
        "paper": "arXiv:1304.2429",
        "family": "affine packing of K_2-factors",
        "p": n,
        "layers": layers,
        "required": required,
        "adjacency": rows,
        "answer": answer,
    }


def _parse_instance(inst):
    if not isinstance(inst, dict):
        return None, "instance is not a dictionary"
    p, layers, required = inst.get("p"), inst.get("layers"), inst.get("required")
    try:
        _validate_parameters(p, layers, required)
    except ValueError as exc:
        return None, "invalid instance parameters: " + str(exc)
    rows = inst.get("adjacency")
    if not isinstance(rows, list) or len(rows) != p:
        return None, "instance must contain one adjacency row per left residue"
    adjacency = {}
    for row in rows:
        if not (isinstance(row, list) and len(row) == 2 and _is_int(row[0])
                and isinstance(row[1], list)):
            return None, "malformed adjacency row"
        x, neighbors = row
        if not 0 <= x < p or x in adjacency:
            return None, "duplicate or out-of-range left residue"
        if len(neighbors) != layers:
            return None, "an adjacency row has the wrong degree"
        if any(not _is_int(y) or not 0 <= y < p for y in neighbors):
            return None, "right residue is outside F_p"
        if len(set(neighbors)) != layers:
            return None, "an adjacency row repeats a right neighbor"
        adjacency[x] = set(neighbors)
    if set(adjacency) != set(range(p)):
        return None, "left residues do not cover F_p"
    right_degrees = [0] * p
    for neighbors in adjacency.values():
        for y in neighbors:
            right_degrees[y] += 1
    if any(degree != layers for degree in right_degrees):
        return None, "the bipartite graph is not regular on the right"
    return {"p": p, "layers": layers, "required": required,
            "adjacency": adjacency}, None


def render(inst):
    data, error = _parse_instance(inst)
    if error is not None:
        raise ValueError(error)
    p, required = data["p"], data["required"]
    lines = [
        "AFFINE PACKING OF TREE FACTORS",
        "",
        "A K2-factor of a graph is a perfect matching: a set of edges in which "
        "every vertex occurs exactly once. A packing is a collection of factors "
        "whose edge sets are pairwise disjoint.",
        "",
        f"Both sides L and R of the following bipartite graph are the finite field "
        f"F_{p}, represented by the integers 0 through {p - 1}. All arithmetic "
        f"below is modulo the prime p={p}. An adjacency row 'x: y1 y2 ...' lists "
        "exactly the right residues y for which (x,y) is an edge. Row order and "
        "neighbor order carry no meaning.",
        "",
        f"Find exactly k={required} degree-one polynomials f_i(x)=a_i*x+b_i "
        f"over F_{p} such that each set {{(x,f_i(x)): x in F_{p}}} is a K2-factor "
        "of the displayed graph and the k factors are pairwise edge-disjoint. "
        "Every a_i must be nonzero. Coefficients are the canonical decimal "
        f"representatives 0,...,{p - 1}. The order of the k polynomials does not "
        "matter, but repeats are forbidden.",
        "",
        "Adjacency rows:",
    ]
    for x, neighbors in inst["adjacency"]:
        lines.append(f"{x}: " + " ".join(str(y) for y in neighbors))
    example = [[1, index] for index in range(required)]
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as a JSON list of "
        f"exactly {required} coefficient pairs [a,b].",
        "Example of the required syntax only: <answer>"
        + json.dumps(example, separators=(",", ":")) + "</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Extract one JSON answer block, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\b[^>]*>(.*?)</answer>", text,
                      flags=re.IGNORECASE | re.DOTALL)
    if match is None:
        return None
    body = match.group(1).strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body,
                         flags=re.IGNORECASE | re.DOTALL)
    if fence is not None:
        body = fence.group(1).strip()
    try:
        answer = json.loads(body)
    except (TypeError, ValueError):
        return None
    return answer if isinstance(answer, list) else None


def _validate_answer_shape(data, answer):
    if not isinstance(answer, list):
        return None, "answer must be a JSON list"
    if not answer:
        return None, "answer is empty"
    if len(answer) != data["required"]:
        return None, f"answer must contain exactly {data['required']} affine maps"
    maps = []
    for pair in answer:
        if not (isinstance(pair, list) and len(pair) == 2
                and all(_is_int(value) for value in pair)):
            return None, "each affine map must be a two-integer list [a,b]"
        a, b = pair
        if not (0 <= a < data["p"] and 0 <= b < data["p"]):
            return None, "a coefficient is outside the displayed field range"
        if a == 0:
            return None, "a slope is zero, so the map is not a permutation"
        maps.append((a, b))
    if len(set(maps)) != len(maps):
        return None, "duplicate affine maps are not allowed"
    slopes = {a for a, _ in maps}
    if len(slopes) != 1:
        return None, "different slopes intersect, so the proposed factors are not edge-disjoint"
    return maps, None


def _verify_data(data, answer):
    """Verify against already validated instance data (used by measurements)."""
    maps, error = _validate_answer_shape(data, answer)
    if error is not None:
        return False, error
    p, adjacency = data["p"], data["adjacency"]
    used_edges = set()
    for map_index, (a, b) in enumerate(maps):
        seen_right = set()
        for x in range(p):
            y = (a * x + b) % p
            if y not in adjacency[x]:
                return False, f"affine map {map_index} uses the absent edge ({x},{y})"
            if y in seen_right:
                return False, f"affine map {map_index} does not cover right vertices once"
            if (x, y) in used_edges:
                return False, f"affine map {map_index} reuses an edge"
            seen_right.add(y)
            used_edges.add((x, y))
        if len(seen_right) != p:
            return False, f"affine map {map_index} is not a K2-factor"
    return True, "ok"


def verify(inst, answer):
    """Check any valid affine factor packing; never consult inst['answer']."""
    data, error = _parse_instance(inst)
    if error is not None:
        return False, error
    return _verify_data(data, answer)


def _random_candidate_data(data, rng):
    slope = rng.randrange(1, data["p"])
    intercepts = sorted(rng.sample(range(data["p"]), data["required"]))
    return [[slope, intercept] for intercept in intercepts]


def random_candidate(inst, rng):
    """Sample uniformly from common-slope, distinct-intercept certificates."""
    data, error = _parse_instance(inst)
    if error is not None:
        raise ValueError(error)
    return _random_candidate_data(data, rng)


def search_space(inst):
    data, error = _parse_instance(inst)
    if error is not None:
        raise ValueError(error)
    return (data["p"] - 1) * math.comb(data["p"], data["required"])


def enumerate_all(inst):
    data, error = _parse_instance(inst)
    if error is not None:
        raise ValueError(error)
    if search_space(inst) > 200_000:
        return None
    count = 0
    for slope in range(1, data["p"]):
        for intercepts in itertools.combinations(range(data["p"]), data["required"]):
            answer = [[slope, intercept] for intercept in intercepts]
            count += int(verify(inst, answer)[0])
    return count


def _recover_structure(inst):
    data, error = _parse_instance(inst)
    if error is not None:
        raise ValueError(error)
    p, degree, adjacency = data["p"], data["layers"], data["adjacency"]
    slope = ((sum(adjacency[1]) - sum(adjacency[0])) * pow(degree, -1, p)) % p
    intercepts = sorted(adjacency[0])
    expected = _adjacency_from(slope, intercepts, p)
    if any(adjacency[x] != expected[x] for x in range(p)):
        raise ValueError("instance is not a union of common-slope affine factors")
    return data, slope, intercepts


def canonical_key(inst):
    """Canonicalize row order and all affine relabellings of the two field axes."""
    data, _slope, intercepts = _recover_structure(inst)
    p = data["p"]
    normal_forms = []
    for first in intercepts:
        for second in intercepts:
            if first == second:
                continue
            inverse = pow((second - first) % p, -1, p)
            normal_forms.append(tuple(sorted(((b - first) * inverse) % p
                                             for b in intercepts)))
    normalized = min(normal_forms)
    payload = {
        "p": p,
        "layers": data["layers"],
        "required": data["required"],
        "intercept_affine_class": normalized,
    }
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return "affine-k2-packing-v1:" + hashlib.sha256(blob.encode()).hexdigest()


def escalate(params):
    n = params.get("n")
    layers = params.get("layers")
    required = params.get("required")
    if not all(_is_int(value) for value in (n, layers, required)):
        return None
    harder_n = _next_prime((3 * n) // 2)
    harder_layers = min(harder_n - 1, layers + max(8, layers // 5))
    return {"n": harder_n, "layers": harder_layers, "required": required}


def _compact_shortcut(inst):
    data, slope, intercepts = _recover_structure(inst)
    return [[slope, b] for b in intercepts[:data["required"]]]


def _reference_enumerator(inst):
    """Enumerate affine maps from N(0)xN(1), with counted exact operations."""
    data, error = _parse_instance(inst)
    if error is not None:
        raise ValueError(error)
    p, adjacency = data["p"], data["adjacency"]
    operations = 0
    valid = set()
    for b in sorted(adjacency[0]):
        for y1 in sorted(adjacency[1]):
            slope = (y1 - b) % p
            operations += 2
            if slope == 0:
                continue
            good = True
            for x in range(p):
                y = (slope * x + b) % p
                operations += 4  # multiply, add, reduce, membership test
                if y not in adjacency[x]:
                    good = False
                    break
            if good:
                valid.add((slope, b))
    by_slope = {}
    for slope, b in valid:
        by_slope.setdefault(slope, []).append(b)
    for slope in sorted(by_slope):
        bs = sorted(by_slope[slope])
        if len(bs) >= data["required"]:
            return [[slope, b] for b in bs[:data["required"]]], operations, len(valid)
    return None, operations, len(valid)


def _candidate_with_slope(data, slope, intercepts=None):
    if intercepts is None:
        intercepts = sorted(data["adjacency"][0])[:data["required"]]
    values = list(dict.fromkeys(int(v) % data["p"] for v in intercepts))
    for value in range(data["p"]):
        if len(values) >= data["required"]:
            break
        if value not in values:
            values.append(value)
    return [[slope % data["p"], b] for b in values[:data["required"]]]


def _attack_edge_difference_outlier(inst):
    data, error = _parse_instance(inst)
    if error is not None:
        raise ValueError(error)
    p = data["p"]
    frequencies = Counter((y - x) % p for x, ys in data["adjacency"].items() for y in ys)
    intercepts = [value for value, _count in sorted(frequencies.items(),
                                                    key=lambda item: (-item[1], item[0]))]
    return _candidate_with_slope(data, 1, intercepts)


def _attack_sorted_row_greedy(inst):
    data, error = _parse_instance(inst)
    if error is not None:
        raise ValueError(error)
    slope = _rank_pair_guess(data["adjacency"], data["p"])
    return _candidate_with_slope(data, slope)


def _attack_ordinary_average(inst):
    data, error = _parse_instance(inst)
    if error is not None:
        raise ValueError(error)
    slope = _ordinary_average_guess(data["adjacency"], data["layers"], data["p"])
    return _candidate_with_slope(data, slope)


def _attack_single_edge_translation(inst):
    data, error = _parse_instance(inst)
    if error is not None:
        raise ValueError(error)
    x = min(data["adjacency"])
    y = min(data["adjacency"][x])
    intercepts = [((neighbor - x) % data["p"]) for neighbor in sorted(data["adjacency"][x])]
    return _candidate_with_slope(data, 1, intercepts)


def _transform_instance(inst, rng, swap_sides=False):
    data, error = _parse_instance(inst)
    if error is not None:
        raise ValueError(error)
    p = data["p"]
    u, w = rng.randrange(1, p), rng.randrange(1, p)
    v, z = rng.randrange(p), rng.randrange(p)
    transformed = {}
    for x, neighbors in data["adjacency"].items():
        nx = (u * x + v) % p
        transformed[nx] = {(w * y + z) % p for y in neighbors}
    maps = []
    u_inv = pow(u, -1, p)
    for a, b in inst["answer"]:
        na = (w * a * u_inv) % p
        nb = (w * b + z - na * v) % p
        maps.append([na, nb])
    if swap_sides:
        inverse_graph = {x: set() for x in range(p)}
        for x, neighbors in transformed.items():
            for y in neighbors:
                inverse_graph[y].add(x)
        transformed = inverse_graph
        inverted = []
        for a, b in maps:
            a_inv = pow(a, -1, p)
            inverted.append([a_inv, (-a_inv * b) % p])
        maps = inverted
    rows = [[x, list(neighbors)] for x, neighbors in transformed.items()]
    rng.shuffle(rows)
    for row in rows:
        rng.shuffle(row[1])
    return {
        "paper": inst["paper"], "family": inst["family"], "p": p,
        "layers": data["layers"], "required": data["required"],
        "adjacency": rows, "answer": maps,
    }


def _count_atoms(obj):
    if isinstance(obj, dict):
        return sum(_count_atoms(value) for value in obj.values())
    if isinstance(obj, list):
        return sum(_count_atoms(value) for value in obj)
    return 1


def _answer_size(answer):
    blob = json.dumps(answer, separators=(",", ":"))
    return len(blob), (len(blob) + 3) // 4, _count_atoms(answer)


def _intended_operations(inst):
    # Two degree-d sums, a subtraction, inverse/multiply/reduction, selecting k
    # intercepts, and a conservative allowance for Euclid and bookkeeping.
    return 2 * inst["layers"] + inst["required"] + 20


def selftest():
    report = {
        "paper": "arXiv:1304.2429",
        "family": "affine packing of K_2-factors",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1: all presets, several independent instances, and JSON-native answers.
    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures,
        "generation_route": "inverse generation of equally valid affine factors",
    }

    shipping = make_instance(seed=13042429, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]

    # G2: five materially distinct corruptions and five distinct diagnostics.
    drop = json.loads(json.dumps(planted[:-1]))
    swap = json.loads(json.dumps(planted))
    swap[0][0], swap[0][1] = swap[0][1], swap[0][0]
    if swap[0][0] == 0 or swap[0][0] == planted[0][0]:
        swap[0][0] = (planted[0][0] + 1) % shipping["p"] or 1
    duplicate = json.loads(json.dumps(planted))
    duplicate[1] = list(duplicate[0])
    out_of_range = json.loads(json.dumps(planted))
    out_of_range[0][1] = shipping["p"]
    corruptions = {
        "drop_one_map": drop,
        "swap_coefficients": swap,
        "duplicate_map": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = {entry["reason"] for entry in cases.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in cases.values())
                and len(reasons) == len(cases),
        "attempts": len(cases), "distinct_reasons": len(reasons), "cases": cases,
    }

    # G3: tagged JSON inside a realistic fenced response.
    realistic = ("The common finite-field slope is consistent across the rows.\n"
                 "```json\n<answer>\n"
                 + json.dumps(planted, separators=(",", ":"))
                 + "\n</answer>\n```\nEach polynomial was checked on all residues.")
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged answer") is None,
        "parsed_equals_answer": parsed == planted,
        "surrounding_prose_and_fence": True,
    }

    # G4: sample exactly the structure-aware common-slope language.
    guess_rng = random.Random(0x13042429)
    guess_total = 200_000
    guess_hits = 0
    shipping_data, shipping_error = _parse_instance(shipping)
    if shipping_error is not None:
        raise AssertionError(shipping_error)
    started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(_verify_data(
            shipping_data, _random_candidate_data(shipping_data, guess_rng))[0])
    guess_elapsed = time.perf_counter() - started
    exact_valid = math.comb(shipping["layers"], shipping["required"])
    exact_space = search_space(shipping)
    exact_density = exact_valid / exact_space
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6 and exact_density < 1e-6,
        "hits": guess_hits, "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "exact_valid_certificates": exact_valid,
        "structure_aware_space": exact_space,
        "exact_probability": exact_density,
        "sampling_rule": "uniform common nonzero slope and uniform k-subset of distinct intercepts",
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    # G5/G6: cheap attacks must fail; the disclosed Track-B reference must solve.
    attack_functions = {
        "edge_difference_outlier": _attack_edge_difference_outlier,
        "greedy_sorted_row_pairing": _attack_sorted_row_greedy,
        "random_restart_256": None,
        "in_context_ordinary_average": _attack_ordinary_average,
        "single_edge_translation_ansatz": _attack_single_edge_translation,
    }
    attacks = {name: {"successes": 0, "attempts": 0, "wall_clock_sec": 0.0}
               for name in attack_functions}
    reference_times, reference_operations, reference_valid_maps = [], [], []
    reference_successes = compact_successes = 0
    attack_seeds = list(range(8100, 8108))
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        data, error = _parse_instance(inst)
        if error is not None:
            raise AssertionError(error)
        for offset, (name, function) in enumerate(attack_functions.items()):
            t0 = time.perf_counter()
            if function is None:
                rng = random.Random(seed * 1009 + offset)
                success = any(_verify_data(data, _random_candidate_data(data, rng))[0]
                              for _ in range(256))
            else:
                success = _verify_data(data, function(inst))[0]
            attacks[name]["wall_clock_sec"] += time.perf_counter() - t0
            attacks[name]["attempts"] += 1
            attacks[name]["successes"] += int(success)
        t0 = time.perf_counter()
        candidate, operations, valid_maps = _reference_enumerator(inst)
        reference_times.append(time.perf_counter() - t0)
        reference_operations.append(operations)
        reference_valid_maps.append(valid_maps)
        reference_successes += int(candidate is not None and verify(inst, candidate)[0])
        compact_successes += int(verify(inst, _compact_shortcut(inst))[0])
    for result in attacks.values():
        result["wall_clock_sec"] = round(result["wall_clock_sec"], 6)
    work_per_attempt = {
        "edge_difference_outlier": shipping["p"] * shipping["layers"],
        "greedy_sorted_row_pairing": 2 * shipping["layers"],
        "random_restart_256": 256,
        "in_context_ordinary_average": 2 * shipping["layers"],
        "single_edge_translation_ansatz": shipping["layers"],
    }
    for name, result in attacks.items():
        result["work_units_total_8"] = work_per_attempt[name] * len(attack_seeds)
    all_attacks_failed = all(row["successes"] == 0 and row["attempts"] >= 8
                             for row in attacks.values())
    reference = {
        "name": "enumerate affine maps from N(0) x N(1), then verify on F_p",
        "complexity": "O(d^2 p) exact finite-field operations",
        "operations_mean": sum(reference_operations) // len(reference_operations),
        "operations_min": min(reference_operations),
        "operations_max": max(reference_operations),
        "wall_clock_sec_mean": round(sum(reference_times) / len(reference_times), 8),
        "wall_clock_sec_total_8": round(sum(reference_times), 6),
        "valid_maps_per_instance": reference_valid_maps,
        "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed
                and reference_successes == compact_successes == len(attack_seeds),
        "attacks": attacks,
        "reference_algorithm": reference,
        "compact_route": {
            "name": "finite-field first difference of neighbor sums",
            "worst_case_exact_operations": _intended_operations(shipping),
            "solves": f"{compact_successes}/{len(attack_seeds)}, as expected",
        },
    }
    strongest = max(attacks, key=lambda name: attacks[name]["wall_clock_sec"])
    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    report["G5_density_and_baseline_cost"] = {
        "pass": exact_density < 1e-6 and all_attacks_failed
                and reference_successes == len(attack_seeds),
        "exact_valid_answers_at_shipping": exact_valid,
        "exact_density_at_shipping": exact_density,
        "sampled_density_at_shipping": guess_hits / guess_total,
        "density_hits": guess_hits, "density_samples": guess_total,
        "candidate_space_at_shipping": exact_space,
        "strongest_failing_attack": strongest,
        "baseline_wall_clock_sec_total_8": attacks[strongest]["wall_clock_sec"],
        "baseline_work_units_total_8": attacks[strongest]["work_units_total_8"],
        "reference_operations_mean": reference["operations_mean"],
        "reference_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
        "demo_exact_valid_answers": enumerate_all(demo),
        "demo_candidate_space": search_space(demo),
    }

    # G7: double the field size while holding the certificate length fixed.
    doubled_n = _next_prime(2 * shipping["p"])
    doubled = make_instance(n=doubled_n, layers=shipping["layers"],
                            required=shipping["required"], seed=707)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(shipping)
                and len(doubled["answer"]) == len(shipping["answer"]),
        "shipping_n": shipping["p"], "doubled_n": doubled_n,
        "shipping_edges": shipping["p"] * shipping["layers"],
        "doubled_edges": doubled_n * shipping["layers"],
        "shipping_answer_maps": len(shipping["answer"]),
        "doubled_answer_maps": len(doubled["answer"]),
        "verify_reason": doubled_reason,
    }

    # G8: row/neighbor reorderings, affine coordinate relabellings, side swap,
    # and compositions of all of them; every carried certificate is rechecked.
    invariance_checks = carried_checks = 0
    g8_failures = []
    original_keys = []
    for seed in range(20):
        inst = make_instance(seed=9000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        original_keys.append(key)
        for variant, swap_sides in enumerate((False, True)):
            transformed = _transform_instance(
                inst, random.Random(12000 + 10 * seed + variant), swap_sides)
            invariance_checks += 1
            if canonical_key(transformed) != key:
                g8_failures.append({"seed": seed, "variant": variant,
                                    "reason": "canonical key changed"})
            carried_checks += 1
            ok, reason = verify(transformed, transformed["answer"])
            if not ok:
                g8_failures.append({"seed": seed, "variant": variant,
                                    "reason": "carried certificate failed: " + reason})
    distinct_keys = len(set(original_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20, "distinct_keys": distinct_keys,
        "failures": g8_failures,
        "symmetries_tested": [
            "adjacency-row and neighbor reordering",
            "independent affine relabellings of left and right F_p coordinates",
            "swapping the bipartition sides",
            "composition of all preceding maps",
        ],
    }

    # G9: oracle arms are script-owned diagnostics; only exact size/effort caps gate.
    chars, tokens, atoms = _answer_size(shipping["answer"])
    intended_operations = _intended_operations(shipping)
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = chars <= 2000 and atoms <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars, "answer_tokens": tokens,
        "answer_elements": atoms,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["pass"] = all(gate.get("pass") is True for gate in gates)
    report["all_passed"] = report["pass"]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
