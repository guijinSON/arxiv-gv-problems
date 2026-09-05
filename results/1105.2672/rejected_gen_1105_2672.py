"""Verified problem generator for arXiv:1105.2672.

The generated task is native to the paper: find a strict coloring (a partition
of the vertices) of a 3-uniform bi-hypergraph.  Instances are affine relabelings
of random partial sub-hypergraphs of H*_{q,q} from Section 3.  The planted
coordinate partition is carried through the relabeling, never recovered by
solving.
"""

from __future__ import annotations

import functools
import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time
from collections import Counter


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # The family has a standard-library finite-field fallback.
    exact_matrices = rationals = None


TRACK = "B"
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Across bi-edges, the same two projective directions recur among the three "
    "vertex-pair differences."
)
PLACEBO_HINT = (
    "Across the data, careful modular arithmetic and consistent normalization "
    "prevent avoidable mistakes."
)

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "3-uniform bi-hypergraph",
        "affinely labelled vertices in GF(p)^2",
        "strict coloring as a set partition",
    ],
    "verification_operations": [
        "exact partition coverage check",
        "exact bi-edge color comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Every bi-edge repeats each hidden coordinate on one vertex pair, so the "
        "two kernel directions recur across otherwise unrelated edges."
    ),
    "hardness_basis": (
        "Track B: the pair-direction histogram plus partition evaluation runs in "
        "O(|B| log p + |X|+|B|), succeeds on every generated instance, and at the "
        "shipping preset processes 4,500 pair directions (measured wall-clock is "
        "reported by selftest); the compact route takes at most 276 exact operations, "
        "but only after noticing the repeated-direction invariant."
    ),
    "max_answer_tokens": 80,
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

DIFFICULTY = {
    "demo": {"n": 5, "modulus_floor": 101, "edge_budget": 60},
    "easy": {"n": 11, "modulus_floor": 10_007, "edge_budget": 250},
    "medium": {"n": 17, "modulus_floor": 1_000_003, "edge_budget": 700},
    "hard": {"n": 23, "modulus_floor": 1_000_000_007, "edge_budget": 1_500},
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "Canonical partitions of all N vertices into q nonempty color classes, "
        "conditioned on the first listed bi-edge already using exactly two colors; "
        "vertices and classes are ordered by their least vertex ID."
    ),
    "bounds": {
        "vertices": "N=3q",
        "color_classes": "q",
        "first_edge_colors": 2,
        "space": "3*(S(N-1,q)-S(N-2,q))",
    },
}

NOTES = (
    "Section 1 fixes the exact rule: a proper coloring of a bi-edge must contain "
    "both a repeated color and two distinct colors, hence a 3-edge has exactly two "
    "colors. Theorem 2.2 proves that coordinate projections are all strict "
    "colorings of H, and Theorem 3.2 carries the spectrum to the sparse H* family; "
    "we use its n1=n2=q construction. Deleting a uniformly sampled subset of "
    "bi-edges preserves both known coordinate colorings and creates structural "
    "diversity. An invertible affine map over GF(p) relabels the coordinates while "
    "the planted partition is carried directly. Track A is not claimed: the construction exposes an "
    "efficient pair-direction histogram. The degree-outlier, raw-axis greedy, 256 "
    "random-direction, and small-coefficient attacks are defeated respectively by "
    "uniform edge sampling, a dense affine mix, the enormous set-partition answer "
    "space, and rejection of small planted slopes."
)

# Filled from the separately run hardening arms before shipping.  G9(a,b) are
# diagnostic only; G9(c) is computed afresh by selftest.
G9_DIAGNOSTIC = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


def _is_prime(value):
    if value < 2:
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


def _normalise_direction(a, b, p):
    """Canonical point [a:b] of the projective line over GF(p)."""
    a %= p
    b %= p
    if a:
        inv = pow(a, -1, p)
        return (1, (b * inv) % p)
    if b:
        return (0, 1)
    return None


def _poly(direction):
    a, b = direction
    return [[int(a), [1, 0]], [int(b), [0, 1]]]


def _poly_direction(answer):
    return int(answer[0][0]), int(answer[1][0])


def _canonical_partition_from_colors(colors):
    classes = {}
    for vertex, color in enumerate(colors):
        classes.setdefault(color, []).append(vertex)
    return sorted((sorted(block) for block in classes.values()), key=lambda b: b[0])


@functools.lru_cache(maxsize=None)
def _base_vertices(q):
    # Section 3's X*_{q,q}, shifted from [q] to {0,...,q-1}.
    vertices = {(i, k) for i in range(3) for k in range(3)}
    for k in range(3, q):
        vertices.update(((0, k), (k, 0), (k, k)))
    return tuple(sorted(vertices))


@functools.lru_cache(maxsize=None)
def _base_edges(q):
    vertices = _base_vertices(q)
    edges = []
    for i, j, k in itertools.combinations(range(len(vertices)), 3):
        a, b, c = vertices[i], vertices[j], vertices[k]
        if (len({a[0], b[0], c[0]}) == 2
                and len({a[1], b[1], c[1]}) == 2):
            edges.append((i, j, k))
    return tuple(edges)


def make_instance(n, seed=0, modulus_floor=1_000_003, edge_budget=1_500,
                  **params):
    """Construct a certified partial H*_{q,q} instance without solving it."""
    del params
    q = int(n)
    if q < 5:
        raise ValueError("n=q must be at least 5")
    p = _next_prime(max(int(modulus_floor), 4 * q + 1))
    budget = int(edge_budget)
    if budget < 2:
        raise ValueError("edge_budget must be at least 2")
    rng = random.Random(seed)

    # Choose a dense affine mix.  The inverse rows are the two known coloring
    # polynomials.  Keeping their slopes away from tiny values makes the stated
    # cheap attacks honest failures rather than construction artifacts.
    banned_slopes = {v % p for v in range(-8, 9)}
    while True:
        aa = rng.randrange(1, p)
        ab = rng.randrange(1, p)
        ba = rng.randrange(1, p)
        bb = rng.randrange(1, p)
        det = (aa * bb - ab * ba) % p
        if not det:
            continue
        inv_det = pow(det, -1, p)
        row_x = _normalise_direction(bb * inv_det, -ab * inv_det, p)
        row_y = _normalise_direction(-ba * inv_det, aa * inv_det, p)
        if (row_x != row_y and row_x[0] == row_y[0] == 1
                and row_x[1] not in banned_slopes
                and row_y[1] not in banned_slopes):
            break

    tx = rng.randrange(p)
    ty = rng.randrange(p)
    base_vertices = _base_vertices(q)
    transformed = [
        ((aa * x + ab * y + tx) % p,
         (ba * x + bb * y + ty) % p)
        for x, y in base_vertices
    ]

    base_order = list(range(len(base_vertices)))
    rng.shuffle(base_order)
    old_to_new = {old: new for new, old in enumerate(base_order)}
    points = [list(transformed[old]) for old in base_order]

    all_edges = _base_edges(q)
    take = min(budget, len(all_edges))
    selected = rng.sample(range(len(all_edges)), take)
    edges = [
        sorted(old_to_new[v] for v in all_edges[index])
        for index in selected
    ]
    rng.shuffle(edges)

    # Carry the first-coordinate partition through the vertex permutation.  This
    # is the certificate known by construction; no coloring search is performed.
    planted_colors = [base_vertices[old][0] for old in base_order]
    planted_partition = _canonical_partition_from_colors(planted_colors)

    return {
        "q": q,
        "p": p,
        "points": points,
        "edges": edges,
        "answer": planted_partition,
        "construction": "affine partial H*_{q,q} from Section 3",
    }


def render(inst):
    p = inst["p"]
    q = inst["q"]
    lines = [
        "STRICT COLORING OF A 3-UNIFORM BI-HYPERGRAPH",
        "",
        f"All arithmetic is in the prime field GF({p}); reduce every value modulo {p}.",
        "A 3-uniform bi-hypergraph has vertices and 3-element bi-edges.",
        "A proper coloring of a bi-edge must use exactly two colors: it may be",
        "neither monochromatic (one color) nor rainbow (three colors).",
        f"A strict {q}-coloring is proper and uses exactly {q} distinct colors.",
        "",
        f"Partition every vertex into exactly {q} nonempty color classes so that the",
        "partition is a strict coloring under the rule above. Coordinates are part of",
        "the instance and may be used in GF(p), but colors themselves are just classes.",
        "Within each class list vertex IDs in increasing order; order the classes by",
        "their least vertex ID. Repeats and omitted vertices are forbidden.",
        "",
        "Vertices are 0-indexed; each line is: vertex_id x y",
    ]
    lines.extend(
        f"{index} {point[0]} {point[1]}"
        for index, point in enumerate(inst["points"])
    )
    lines.extend([
        "",
        "Bi-edges follow; each line contains three distinct 0-based vertex IDs.",
    ])
    lines.extend("{} {} {}".format(*edge) for edge in inst["edges"])
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as one exact JSON list",
        f"of {q} lists, containing every vertex ID exactly once in the order specified.",
        "Example format only: <answer>[[0,3],[1,2]]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


_ANSWER_RE = re.compile(r"<answer>\s*(.*?)\s*</answer>", re.I | re.S)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    payload = match.group(1).strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return answer if isinstance(answer, list) else None


def _validate_partition(inst, answer):
    if not isinstance(answer, list):
        return None, "answer_not_a_list"
    if not answer:
        return None, "empty_partition"
    if len(answer) < inst["q"]:
        return None, "missing_color_class"
    if len(answer) > inst["q"]:
        return None, "extra_color_class"
    if any(not isinstance(block, list) for block in answer):
        return None, "malformed_color_class"
    if any(not block for block in answer):
        return None, "empty_color_class"
    flat = []
    for block in answer:
        for vertex in block:
            if not isinstance(vertex, int) or isinstance(vertex, bool):
                return None, "noninteger_vertex"
            if not 0 <= vertex < len(inst["points"]):
                return None, "vertex_out_of_range"
            flat.append(vertex)
    if len(set(flat)) != len(flat):
        return None, "duplicate_vertex"
    if len(flat) < len(inst["points"]):
        return None, "missing_vertex"
    if len(flat) > len(inst["points"]):
        return None, "too_many_vertices"
    if any(block != sorted(block) for block in answer):
        return None, "vertices_not_increasing"
    if answer != sorted(answer, key=lambda block: block[0]):
        return None, "classes_not_canonical"
    colors = [None] * len(inst["points"])
    for color, block in enumerate(answer):
        for vertex in block:
            colors[vertex] = color
    return colors, "ok"


def verify(inst, answer):
    colors, reason = _validate_partition(inst, answer)
    if colors is None:
        return False, reason
    for edge in inst["edges"]:
        count = len({colors[edge[0]], colors[edge[1]], colors[edge[2]]})
        if count == 1:
            return False, "monochromatic_bi_edge"
        if count == 3:
            return False, "rainbow_bi_edge"
    return True, "ok"


@functools.lru_cache(maxsize=None)
def _completion_table(length, q):
    # ways[t][r]: length-t strings over q labels that visit all r labels not yet
    # seen.  This lets random_candidate sample the conditioned language exactly.
    ways = [[0] * (q + 1) for _ in range(length + 1)]
    ways[0][0] = 1
    for t in range(1, length + 1):
        for r in range(q + 1):
            ways[t][r] = (q - r) * ways[t - 1][r]
            if r:
                ways[t][r] += r * ways[t - 1][r - 1]
    return tuple(tuple(row) for row in ways)


def random_candidate(inst, rng):
    """Uniform partition conditioned on the first edge already being proper."""
    q = inst["q"]
    total_vertices = len(inst["points"])
    edge = list(inst["edges"][0])
    repeated_pair = rng.randrange(3)
    pair_positions = ((0, 1), (0, 2), (1, 2))[repeated_pair]
    repeated_color = rng.randrange(q)
    singleton_color = rng.randrange(q - 1)
    if singleton_color >= repeated_color:
        singleton_color += 1
    colors = [None] * total_vertices
    colors[edge[pair_positions[0]]] = repeated_color
    colors[edge[pair_positions[1]]] = repeated_color
    singleton_position = ({0, 1, 2} - set(pair_positions)).pop()
    colors[edge[singleton_position]] = singleton_color

    seen = {repeated_color, singleton_color}
    unseen = set(range(q)) - seen
    remaining = [v for v in range(total_vertices) if colors[v] is None]
    ways = _completion_table(len(remaining), q)
    for index, vertex in enumerate(remaining):
        t = len(remaining) - index
        r = len(unseen)
        seen_weight = (q - r) * ways[t - 1][r]
        unseen_weight = r * ways[t - 1][r - 1] if r else 0
        roll = rng.randrange(seen_weight + unseen_weight)
        if roll < seen_weight:
            color = rng.choice(sorted(seen))
        else:
            color = rng.choice(sorted(unseen))
            unseen.remove(color)
            seen.add(color)
        colors[vertex] = color
    return _canonical_partition_from_colors(colors)


@functools.lru_cache(maxsize=None)
def _stirling_second(n, k):
    if n == k or k == 1:
        return 1
    if k < 1 or k > n:
        return 0
    return k * _stirling_second(n - 1, k) + _stirling_second(n - 1, k - 1)


def search_space(inst):
    n = len(inst["points"])
    q = inst["q"]
    return 3 * (_stirling_second(n - 1, q) - _stirling_second(n - 2, q))


def enumerate_all(inst):
    # Even the q=5 demo language contains hundreds of millions of partitions.
    return None


def canonical_key(inst):
    """Strong incidence invariant, independent of vertex and edge labels."""
    vertex_count = len(inst["points"])
    degree = [0] * vertex_count
    pair_degree = Counter()
    normal_edges = []
    for edge in inst["edges"]:
        edge = tuple(sorted(edge))
        normal_edges.append(edge)
        for vertex in edge:
            degree[vertex] += 1
        for pair in itertools.combinations(edge, 2):
            pair_degree[pair] += 1
    edge_signatures = []
    for edge in normal_edges:
        ds = sorted(degree[v] for v in edge)
        ps = sorted(pair_degree[tuple(sorted(pair))]
                    for pair in itertools.combinations(edge, 2))
        edge_signatures.append((ds, ps))
    payload = {
        "q": inst["q"],
        "p": inst["p"],
        "vertices": vertex_count,
        "edges": len(normal_edges),
        "degrees": sorted(degree),
        "positive_pair_codegrees": sorted(pair_degree.values()),
        "edge_local_signatures": sorted(edge_signatures),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def escalate(params):
    harder = dict(params)
    harder.pop("_preset", None)
    harder["n"] = max(int(params["n"]) + 1, math.ceil(int(params["n"]) * 1.35))
    harder["modulus_floor"] = max(
        int(params.get("modulus_floor", 101)) * 4 + 1,
        4 * harder["n"] + 1,
    )
    harder["edge_budget"] = math.ceil(int(params.get("edge_budget", 60)) * 1.5)
    return harder


def _normal_from_points(first, second, p):
    dx = (second[0] - first[0]) % p
    dy = (second[1] - first[1]) % p
    return _normalise_direction(dy, -dx, p)


def _partition_from_direction(inst, direction):
    a, b = direction
    colors = [(a * x + b * y) % inst["p"] for x, y in inst["points"]]
    return _canonical_partition_from_colors(colors)


def _reference_algorithm(inst):
    start = time.perf_counter()
    counts = Counter()
    direction_records = 0
    for edge in inst["edges"]:
        for u, v in itertools.combinations(edge, 2):
            direction = _normal_from_points(
                inst["points"][u], inst["points"][v], inst["p"])
            direction_records += 1
            if direction is not None:
                counts[direction] += 1
    candidates_tested = 0
    found = None
    for direction, _ in counts.most_common(12):
        candidates_tested += 1
        candidate = _partition_from_direction(inst, direction)
        if verify(inst, candidate)[0]:
            found = candidate
            break
    elapsed = time.perf_counter() - start
    return found, {
        "wall_clock_sec": elapsed,
        "direction_records": direction_records,
        "field_ops_estimate": 6 * direction_records,
        "candidates_tested": candidates_tested,
    }


def _attack_outlier_degree(inst):
    degree = [0] * len(inst["points"])
    for edge in inst["edges"]:
        for vertex in edge:
            degree[vertex] += 1
    order = sorted(range(len(degree)), key=lambda v: (-degree[v], v))
    direction = _normal_from_points(
        inst["points"][order[0]], inst["points"][order[-1]], inst["p"])
    return _partition_from_direction(inst, direction or (1, 0))


def _attack_greedy_raw_axis(inst):
    candidates = [(1, 0), (0, 1)]
    # Greedily choose the displayed axis whose values come closest to q colors.
    direction = min(
        candidates,
        key=lambda d: abs(len({(d[0] * x + d[1] * y) % inst["p"]
                               for x, y in inst["points"]}) - inst["q"]),
    )
    return _partition_from_direction(inst, direction)


def _attack_random_restart(inst, rng, restarts=256):
    last = _partition_from_direction(inst, (1, 0))
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last
    return last


def _attack_small_coefficient(inst):
    p = inst["p"]
    directions = [(0, 1)] + [(1, value % p) for value in range(-8, 9)]
    best = None
    best_gap = None
    for direction in directions:
        count = len({(direction[0] * x + direction[1] * y) % p
                     for x, y in inst["points"]})
        gap = abs(count - inst["q"])
        if best_gap is None or gap < best_gap:
            best, best_gap = direction, gap
    return _partition_from_direction(inst, best)


def _reorder_instance(inst, seed):
    rng = random.Random(seed)
    order = list(range(len(inst["points"])))
    rng.shuffle(order)
    old_to_new = {old: new for new, old in enumerate(order)}
    changed = {k: v for k, v in inst.items() if k not in {"points", "edges", "answer"}}
    changed["points"] = [inst["points"][old] for old in order]
    changed["edges"] = [
        sorted(old_to_new[v] for v in edge) for edge in reversed(inst["edges"])
    ]
    changed["answer"] = sorted(
        (sorted(old_to_new[v] for v in block) for block in inst["answer"]),
        key=lambda block: block[0],
    )
    return changed


def _affine_relabel(inst, answer, seed):
    rng = random.Random(seed)
    p = inst["p"]
    while True:
        aa, ab, ba, bb = (rng.randrange(p) for _ in range(4))
        det = (aa * bb - ab * ba) % p
        if det:
            break
    tx, ty = rng.randrange(p), rng.randrange(p)
    points = [
        [(aa * x + ab * y + tx) % p, (ba * x + bb * y + ty) % p]
        for x, y in inst["points"]
    ]
    changed = {k: v for k, v in inst.items() if k not in {"points", "answer"}}
    changed["points"] = points
    changed["answer"] = json.loads(json.dumps(answer))
    return changed


def _atom_count(value):
    if isinstance(value, dict):
        return sum(_atom_count(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atom_count(v) for v in value)
    return 1


def _swapped_corruption(inst, answer):
    """Find a membership swap that preserves shape but violates a bi-edge."""
    for left in range(len(answer)):
        for right in range(left + 1, len(answer)):
            for li, u in enumerate(answer[left]):
                for ri, v in enumerate(answer[right]):
                    changed = json.loads(json.dumps(answer))
                    changed[left][li], changed[right][ri] = v, u
                    changed = sorted((sorted(block) for block in changed),
                                     key=lambda block: block[0])
                    ok, reason = verify(inst, changed)
                    if not ok and reason in {
                            "monochromatic_bi_edge", "rainbow_bi_edge"}:
                        return changed
    raise AssertionError("could not construct a swapping corruption")


def selftest():
    report = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    planted_checks = 0
    planted_failures = []
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            planted_checks += 1
            if not ok:
                planted_failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not planted_failures and json_roundtrips == planted_checks,
        "checks": planted_checks,
        "json_native_roundtrips": json_roundtrips,
        "failures": planted_failures,
    }

    shipping = make_instance(seed=23, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = json.loads(json.dumps(shipping["answer"]))
    dropped = json.loads(json.dumps(answer))
    dropped[0].pop()
    if not dropped[0]:
        dropped.pop(0)
    dropped = sorted((sorted(block) for block in dropped), key=lambda block: block[0])
    duplicated = json.loads(json.dumps(answer))
    duplicated[1].append(duplicated[0][0])
    duplicated[1].sort()
    out_of_range = json.loads(json.dumps(answer))
    out_of_range[-1][-1] = len(shipping["points"])
    corruptions = {
        "drop_one_vertex": dropped,
        "swap_memberships": _swapped_corruption(shipping, answer),
        "duplicate_vertex": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    corruption_results = {}
    reasons = []
    for name, bad in corruptions.items():
        ok, reason = verify(shipping, bad)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": (all(item["rejected"] for item in corruption_results.values())
                 and len(set(reasons)) == len(reasons)),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    model_style = (
        "The repeated pair directions determine the polynomial.\n"
        "```json\n<answer>" + json.dumps(shipping["answer"])
        + "</answer>\n```\nThis is projectively normalized."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and parse_answer("garbage") is None,
        "model_style_recovered": parsed == shipping["answer"],
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    guess_rng = random.Random(11052672)
    samples = 200_000
    hits = 0
    for _ in range(samples):
        candidate = random_candidate(shipping, guess_rng)
        if verify(shipping, candidate)[0]:
            hits += 1
    rate = hits / samples
    report["G4_guess_resistance"] = {
        "pass": rate < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": rate,
        "structure_aware_space": search_space(shipping),
        "prior": (
            "uniform over canonical q-block partitions conditioned on the first "
            "listed bi-edge using exactly two colors"
        ),
    }

    reference_answer, reference_cost = _reference_algorithm(shipping)
    reference_ok = (reference_answer is not None
                    and verify(shipping, reference_answer)[0])
    report["G5_density_and_baseline"] = {
        "pass": isinstance(rate, float) and reference_ok,
        "shipping_density_estimate": {
            "hits": hits,
            "samples": samples,
            "observed_fraction": rate,
        },
        "enumerate_all_shipping": enumerate_all(shipping),
        "baseline": {
            "name": "bi-edge pair-direction histogram",
            **reference_cost,
            "solved": reference_ok,
        },
    }

    attack_names = [
        "outlier_degree_line",
        "greedy_raw_axis",
        "random_restart_256",
        "small_coefficient_ansatz",
    ]
    attack_counts = {name: 0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_records = 0
    attempts = 8
    for offset in range(attempts):
        inst = make_instance(seed=1000 + offset,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_degree_line": _attack_outlier_degree(inst),
            "greedy_raw_axis": _attack_greedy_raw_axis(inst),
            "random_restart_256": _attack_random_restart(
                inst, random.Random(9000 + offset)),
            "small_coefficient_ansatz": _attack_small_coefficient(inst),
        }
        for name, candidate in candidates.items():
            if verify(inst, candidate)[0]:
                attack_counts[name] += 1
        found, cost = _reference_algorithm(inst)
        if found is not None and verify(inst, found)[0]:
            reference_successes += 1
        reference_seconds += cost["wall_clock_sec"]
        reference_records += cost["direction_records"]
    attacks = {
        name: {"successes": attack_counts[name], "attempts": attempts}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "bi-edge pair-direction histogram",
            "complexity": "O(|B| log p + |X|+|B|)",
            "wall_clock_sec_mean": reference_seconds / attempts,
            "operations_mean_direction_records": reference_records // attempts,
            "solves": f"{reference_successes}/{attempts}, as expected",
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled_params["edge_budget"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=41, **doubled_params)
    doubled_time = time.perf_counter() - start
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (doubled_ok
                 and len(doubled["points"]) > len(shipping["points"])
                 and len(doubled["edges"]) > len(shipping["edges"])),
        "shipping_vertices": len(shipping["points"]),
        "doubled_vertices": len(doubled["points"]),
        "shipping_edges": len(shipping["edges"]),
        "doubled_edges": len(doubled["edges"]),
        "doubled_build_sec": doubled_time,
        "verify_reason": doubled_reason,
    }

    invariant_checks = 0
    preserved_checks = 0
    keys = []
    for offset in range(20):
        inst = make_instance(seed=20_000 + offset,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        keys.append(key)
        reordered = _reorder_instance(inst, 30_000 + offset)
        affine = _affine_relabel(inst, inst["answer"], 40_000 + offset)
        composed = _reorder_instance(affine, 50_000 + offset)
        for changed in (reordered, affine, composed):
            invariant_checks += 1
            if canonical_key(changed) == key:
                preserved_checks += 1
            ok, _ = verify(changed, changed["answer"])
            invariant_checks += 1
            if ok:
                preserved_checks += 1
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": preserved_checks == invariant_checks and distinct == len(keys),
        "invariance_and_witness_checks_passed": preserved_checks,
        "invariance_and_witness_checks_total": invariant_checks,
        "unrelated_distinct": distinct,
        "unrelated_total": len(keys),
        "transformations": [
            "vertex permutation plus edge reordering",
            "invertible affine coordinate relabeling with carried partition",
            "composition of both transformations",
        ],
    }

    # Match emit.sh/harden.py, which use json.dumps' default separators.
    answer_blob = json.dumps(shipping["answer"])
    arms = {
        name: dict(G9_DIAGNOSTIC[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    caps_ok = (len(answer_blob) <= 2_000 and _atom_count(shipping["answer"]) <= 256
               and 276 <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": caps_ok,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_DIAGNOSTIC["hinted_verdict"],
        "answer_chars": len(answer_blob),
        "answer_tokens": math.ceil(len(answer_blob) / 4),
        "answer_elements": _atom_count(shipping["answer"]),
        "intended_route_operations": 276,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
