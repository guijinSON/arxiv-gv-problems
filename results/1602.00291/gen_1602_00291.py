"""Verified edge-metric-basis generator for arXiv:1602.00291.

The paper's Theorem 7 proves that C_(4r) square C_(4t) has edge metric
dimension three and constructs a basis.  This module samples an anchored
torus and a layered affine relabelling first, carries the theorem's basis
through that relabelling, and asks for any valid anchored basis.  The verifier
does not trust the planted answer: it decodes a candidate and compares the
exact distance triples of every edge.
"""

from __future__ import annotations

from array import array
from functools import lru_cache
import itertools
import json
import math
import os
import random
import re
import sys
import time


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # pragma: no cover - this family is stdlib-only
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "succinctly encoded Cartesian torus graph C_(4r) square C_(4t)",
        "three-vertex edge metric basis containing a designated anchor",
    ],
    "verification_operations": [
        "exact modular decoding of vertex labels",
        "exact cyclic graph distance",
        "pairwise comparison of integer edge-distance triples",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "A half-cycle antipodal pair in one torus factor leaves only reflection "
        "ambiguities, and one simultaneous quarter-cycle offset breaks them; "
        "without that symmetry a solver scans candidate landmark triples."
    ),
    "hardness_basis": (
        "Track B: Section 3.1's set-cover formulation gives a mechanical "
        "distance-signature scan; at the measured shipping instance N=10,000, "
        "the O(N^2) symmetry-reduced implementation used here performed "
        "102,500,000 exact distance evaluations in 16--24 seconds across "
        "repeated self-tests (23.71 seconds in the saved report), whereas "
        "Theorem 7's "
        "half/quarter-cycle construction uses at most 168 exact arithmetic "
        "operations after the symmetry is seen."
    ),
    "max_answer_tokens": 6,
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


# n controls the quarter-cycle lengths.  The three-entry witness stays fixed
# while the candidate-pair haystack and the mechanical O(N^2) scan grow.
DIFFICULTY = {
    "demo": {"n": 1, "span": 1, "axis_gap": 0, "encoding_layers": 1},
    "easy": {"n": 24, "span": 16, "axis_gap": 3, "encoding_layers": 7},
    "medium": {"n": 36, "span": 20, "axis_gap": 4, "encoding_layers": 8},
    "hard": {"n": 54, "span": 24, "axis_gap": 5, "encoding_layers": 9},
}
SHIPPING_DIFFICULTY = "easy"


STRUCTURAL_HINT = (
    "A resolving triple on this 4r-by-4t torus is governed by a half-cycle "
    "antipode in one factor and simultaneous quarter-cycle offsets."
)
PLACEBO_HINT = (
    "A submitted triple on this finitely labelled torus should follow every "
    "modular convention and appear in strictly increasing numeric order."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "A strictly increasing list of exactly three distinct vertex labels in "
        "0..N-1, one of which is the designated anchor A.  Order carries no "
        "mathematical meaning; sorting is the unique serialization."
    ),
    "bounds": {
        "atomic_elements": 3,
        "entry_min": 0,
        "entry_max": "N-1",
        "distinct": True,
        "must_contain_anchor": True,
        "candidate_count": "binomial(N-1, 2)",
    },
}


# Filled after the script-owned hardening runs.  These arms are diagnostics;
# since 2026-09-05 only the answer-size and intended-operation caps gate G9.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 2, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "too_easy",
}


NOTES = r"""
Paper grounding. Section 1 defines the distance from a vertex v to an edge xy
as min(d(v,x),d(v,y)), and defines an edge metric generator by uniqueness of
all resulting edge-distance vectors. Section 2, Theorem 7 (labelled
torus-4r-4t in the source) proves edim(C_(4r) square C_(4t))=3 and constructs
the basis {(0,0),(0,2t),(r,t)}. The proof's first two landmarks leave only
reflection symmetries, and the simultaneous quarter offsets of the third
break them. Translation gives the anchored version used here.

Step-0 decision. Theorem 12 proves EDIM NP-complete by reduction from 3-SAT,
but worst-case hardness says nothing about this generated distribution.
Moreover, the paper gives linear-time construction on trees and explicit
formulae for paths, cycles, complete and complete bipartite graphs, grids,
wheels, fans, these tori, and an explicit upper-bound construction for
hypercubes. This torus family is therefore Track B, never Track A. The
mechanical reference follows Section 3.1: compute which edge pairs each
vertex distinguishes and greedily refine the unresolved signature classes.
Vertex transitivity fixes the required anchor and torus reflections reduce
the second-landmark scan to one quadrant. It remains quadratic in the number
of vertices and is measured at the shipping preset. The compact route instead
uses Theorem 7's half/quarter-cycle coordinates and composes the displayed
affine label layers.

Generation. Sample the cycle lengths, anchor coordinate, factor-order
presentation, and every bijective affine label layer before forming the
answer. Translate the theorem's three coordinates to the anchor and carry
them through the sampled encoding. No candidate set is searched during
make_instance.

Attacks. All vertices have degree four, so a degree/outlier choice has no
signal. Farthest-first chooses a diagonally antipodal and hence reflection-
symmetric triple. The obvious two-axis-antipodes ansatz has the same defect.
Uniform anchored random restarts are tested against the actual bounded
certificate language. The successful set-cover signature scan is reported
separately as the Track-B reference algorithm.

Canonicalization. Public affine relabelling, swapping the two Cartesian
factors, reflecting or translating either cycle, and refactoring the affine
encoding do not change the anchored graph's isomorphism type. The key is the
unordered pair of cycle lengths. The self-test explicitly checks public
relabeling, factor swap, and their composition with carried witnesses. This
is complete for the generated family because a Cartesian product of two
cycles in the shipping regime is determined by its two factor lengths.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 5_000
_SHIPPING_SEED = 160_200_291


def _validate_params(n, span, axis_gap, encoding_layers):
    values = (n, span, axis_gap, encoding_layers)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise ValueError("n, span, axis_gap, and encoding_layers must be integers")
    if n < 1:
        raise ValueError("n must be positive")
    if not 1 <= span <= 128:
        raise ValueError("span must lie in 1..128")
    if axis_gap < 0:
        raise ValueError("axis_gap must be nonnegative")
    if not 1 <= encoding_layers <= 24:
        raise ValueError("encoding_layers must lie in 1..24")
    if n + axis_gap > 4096:
        raise ValueError("cycle quarter-lengths are capped at 4096")


def _random_unit(rng, modulus):
    while True:
        value = rng.randrange(2, modulus)
        if math.gcd(value, modulus) == 1:
            return value


def _affine_constants(layers, modulus):
    multiplier = 1
    shift = 0
    for a, b in layers:
        multiplier = a * multiplier % modulus
        shift = (a * shift + b) % modulus
    return multiplier, shift


def _refresh_derived(inst):
    multiplier, shift = _affine_constants(inst["encoding_layers"], inst["N"])
    inst["decode_multiplier"] = pow(multiplier, -1, inst["N"])
    inst["decode_shift"] = shift
    return inst


def _encode(inst, x, y):
    L, M, modulus = inst["L"], inst["M"], inst["N"]
    x %= L
    y %= M
    value = y * L + x if inst["transpose_before_flattening"] else x * M + y
    for a, b in inst["encoding_layers"]:
        value = (a * value + b) % modulus
    return value


def _decode(inst, label):
    base = (
        inst["decode_multiplier"] * (label - inst["decode_shift"])
    ) % inst["N"]
    if inst["transpose_before_flattening"]:
        y, x = divmod(base, inst["L"])
    else:
        x, y = divmod(base, inst["M"])
    return x, y


def make_instance(n, seed=0, **params):
    """Construct an encoded anchored torus and carry Theorem 7's basis."""
    span = params.pop("span", 4)
    axis_gap = params.pop("axis_gap", 4)
    encoding_layers = params.pop("encoding_layers", 7)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, span, axis_gap, encoding_layers)
    rng = random.Random(seed)

    r = n + rng.randrange(span)
    # Nearby factors keep the resolving-basis density uniformly small while
    # span supplies many genuinely non-isomorphic tori for corpus diversity.
    t = r + rng.randrange(axis_gap + 1)
    L, M = 4 * r, 4 * t
    modulus = L * M
    transpose = bool(rng.randrange(2))
    layers = []
    for _ in range(encoding_layers):
        layers.append([_random_unit(rng, modulus), rng.randrange(modulus)])

    inst = {
        "paper": "arXiv:1602.00291",
        "family": "anchored encoded C_(4r) square C_(4t)",
        "r": r,
        "t": t,
        "L": L,
        "M": M,
        "N": modulus,
        "transpose_before_flattening": transpose,
        "encoding_layers": layers,
    }
    _refresh_derived(inst)
    anchor_x = rng.randrange(L)
    anchor_y = rng.randrange(M)
    anchor = _encode(inst, anchor_x, anchor_y)
    theorem_coordinates = [
        (anchor_x, anchor_y),
        (anchor_x, anchor_y + M // 2),
        (anchor_x + L // 4, anchor_y + M // 4),
    ]
    inst["anchor"] = anchor
    inst["answer"] = sorted(_encode(inst, x, y) for x, y in theorem_coordinates)
    return inst


def _encoding_lines(inst):
    first = (
        "q := y*L + x"
        if inst["transpose_before_flattening"]
        else "q := x*M + y"
    )
    lines = ["  " + first]
    for index, (a, b) in enumerate(inst["encoding_layers"], 1):
        lines.append(f"  layer {index}: q := ({a}*q + {b}) mod N")
    lines.append("  enc(x,y) is the final q.")
    return "\n".join(lines)


def render(inst):
    """Render the complete native graph problem and exact output contract."""
    statement = f"""Find an anchored edge metric basis of an encoded Cartesian torus.

Let L={inst['L']}, M={inst['M']}, and N=L*M={inst['N']}. Coordinates are pairs
(x,y) with 0 <= x < L and 0 <= y < M. Addition to x is modulo L and
addition to y is modulo M.

Each coordinate has a public vertex label enc(x,y) in 0,...,N-1. Compute it
by the following exact rules, in the displayed order:
{_encoding_lines(inst)}
Every displayed multiplier is coprime to N, so enc is a bijection.

The undirected graph has vertex labels 0,...,N-1. For every coordinate (x,y)
it has the two edges
  {{enc(x,y), enc(x+1 mod L,y)}}
  {{enc(x,y), enc(x,y+1 mod M)}}.
These are all its edges; duplicate endpoint order does not create new edges.

For vertices u,v, d(u,v) is the number of edges in a shortest graph path.
For a vertex s and an edge e={{u,v}}, define d(s,e)=min(d(s,u),d(s,v)).
A set S of vertices is an edge metric generator when all distinct edges e
have distinct ordered triples (d(s,e) for s in S), using S in increasing
numeric-label order. In this graph no two-vertex set is an edge metric
generator, so a three-vertex generator is an edge metric basis.

Return exactly three distinct vertex labels forming an edge metric basis and
including the designated anchor A={inst['anchor']}. The three labels must be
written in strictly increasing numeric order; order otherwise has no meaning.

Give your final answer inside <answer></answer> tags as three comma-separated
base-10 integers.
Example: <answer>3, 17, 42</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Extract a three-integer answer from tags, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    try:
        if body.startswith("["):
            value = json.loads(body)
            if not isinstance(value, list):
                return None
            if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
                return None
            return value
        if not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", body):
            return None
        return [int(piece.strip()) for piece in body.split(",")]
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _cyclic_distance(left, right, length):
    delta = abs(left - right)
    return min(delta, length - delta)


@lru_cache(maxsize=32)
def _axis_tables(length):
    """All vertex and forward-edge distances on one cycle length."""
    vertex = []
    forward_edge = []
    for landmark in range(length):
        distances = tuple(
            _cyclic_distance(position, landmark, length)
            for position in range(length)
        )
        vertex.append(distances)
        forward_edge.append(
            tuple(
                min(distances[position], distances[(position + 1) % length])
                for position in range(length)
            )
        )
    return tuple(vertex), tuple(forward_edge)


def _landmark_arrays(L, M, coordinate):
    a, b = coordinate
    x_vertex, x_edge = _axis_tables(L)
    y_vertex, y_edge = _axis_tables(M)
    return x_vertex[a], y_vertex[b], x_edge[a], y_edge[b]


def _first_collision(inst, labels):
    L, M = inst["L"], inst["M"]
    tables = [_landmark_arrays(L, M, _decode(inst, label)) for label in labels]
    first_table, second_table, third_table = tables
    seen = {}
    for x in range(L):
        for y in range(M):
            horizontal = (
                first_table[2][x] + first_table[1][y],
                second_table[2][x] + second_table[1][y],
                third_table[2][x] + third_table[1][y],
            )
            edge = ("H", x, y)
            if horizontal in seen:
                return seen[horizontal], edge, horizontal
            seen[horizontal] = edge
            vertical = (
                first_table[0][x] + first_table[3][y],
                second_table[0][x] + second_table[3][y],
                third_table[0][x] + third_table[3][y],
            )
            edge = ("V", x, y)
            if vertical in seen:
                return seen[vertical], edge, vertical
            seen[vertical] = edge
    return None


def verify(inst, answer):
    """Check shape and every exact edge-distance triple; never read answer key."""
    if not isinstance(answer, list):
        return False, "answer must be a list of three integer labels"
    if not answer:
        return False, "answer is empty"
    if len(answer) != 3:
        return False, "expected exactly three labels"
    if any(isinstance(label, bool) or not isinstance(label, int) for label in answer):
        return False, "every label must be an integer"
    if len(set(answer)) != 3:
        return False, "the three labels must be distinct"
    if answer != sorted(answer):
        return False, "labels must be in strictly increasing order"
    if any(label < 0 or label >= inst["N"] for label in answer):
        return False, "a label lies outside 0..N-1"
    if inst["anchor"] not in answer:
        return False, "the designated anchor is missing"
    collision = _first_collision(inst, answer)
    if collision is not None:
        first, second, signature = collision
        return False, (
            f"edges {first} and {second} share distance triple {signature}"
        )
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from all anchored, sorted, distinct triples."""
    anchor = inst["anchor"]
    ranks = rng.sample(range(inst["N"] - 1), 2)
    labels = [rank if rank < anchor else rank + 1 for rank in ranks]
    labels.append(anchor)
    return sorted(labels)


def search_space(inst):
    return math.comb(inst["N"] - 1, 2)


def enumerate_all(inst):
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    anchor = inst["anchor"]
    others = [label for label in range(inst["N"]) if label != anchor]
    count = 0
    for pair in itertools.combinations(others, 2):
        count += int(verify(inst, sorted([anchor, pair[0], pair[1]]))[0])
    return count


def canonical_key(inst):
    """Canonical key for the anchored torus, ignoring every public relabelling."""
    return json.dumps(
        {"anchored_cartesian_cycle_lengths": sorted([inst["L"], inst["M"]])},
        sort_keys=True,
        separators=(",", ":"),
    )


def escalate(params):
    if not isinstance(params, dict) or "n" not in params:
        return None
    harder = dict(params)
    harder.pop("_preset", None)
    harder["n"] = max(params["n"] + 1, (3 * params["n"]) // 2)
    harder["span"] = min(128, max(2, params.get("span", 4) + 1))
    harder["axis_gap"] = params.get("axis_gap", 4) + 1
    harder["encoding_layers"] = min(24, params.get("encoding_layers", 7) + 1)
    if harder["n"] + harder["axis_gap"] > 4096:
        return None
    return harder


def _edge_vector(L, M, coordinate):
    dx, dy, horizontal_x, vertical_y = _landmark_arrays(L, M, coordinate)
    result = array("H")
    for x in range(L):
        for y in range(M):
            result.append(horizontal_x[x] + dy[y])
            result.append(dx[x] + vertical_y[y])
    return result


def _pair_ambiguity(first, second, stride):
    counts = {}
    ambiguity = 0
    for left, right in zip(first, second):
        key = left * stride + right
        previous = counts.get(key, 0)
        ambiguity += previous
        counts[key] = previous + 1
    return ambiguity


def _reference_signature_greedy(inst):
    """Mechanical Section-3.1-style refinement of edge signature classes."""
    started = time.perf_counter()
    L, M = inst["L"], inst["M"]
    anchor_coordinate = _decode(inst, inst["anchor"])
    ax, ay = anchor_coordinate
    stride = L // 2 + M // 2 + 1
    first_vector = _edge_vector(L, M, anchor_coordinate)
    distance_evaluations = len(first_vector)
    second_candidates = 0
    best_score = None
    best_coordinate = None
    best_vector = None

    # Reflections about the anchor make one quadrant a complete orbit list.
    for dx in range(L // 2 + 1):
        for dy in range(M // 2 + 1):
            if dx == 0 and dy == 0:
                continue
            coordinate = ((ax + dx) % L, (ay + dy) % M)
            vector = _edge_vector(L, M, coordinate)
            distance_evaluations += len(vector)
            second_candidates += 1
            score = _pair_ambiguity(first_vector, vector, stride)
            if best_score is None or score < best_score:
                best_score = score
                best_coordinate = coordinate
                best_vector = vector

    pair_keys = array(
        "I", (left * stride + right for left, right in zip(first_vector, best_vector))
    )
    third_candidates = 0
    answer = None
    for dx in range(L):
        for dy in range(M):
            coordinate = ((ax + dx) % L, (ay + dy) % M)
            if coordinate in (anchor_coordinate, best_coordinate):
                continue
            vector = _edge_vector(L, M, coordinate)
            distance_evaluations += len(vector)
            third_candidates += 1
            signatures = set()
            resolves = True
            for pair_key, distance in zip(pair_keys, vector):
                key = pair_key * stride + distance
                if key in signatures:
                    resolves = False
                    break
                signatures.add(key)
            if resolves:
                answer = sorted(
                    [
                        inst["anchor"],
                        _encode(inst, *best_coordinate),
                        _encode(inst, *coordinate),
                    ]
                )
                break
        if answer is not None:
            break

    elapsed = time.perf_counter() - started
    verified = answer is not None and verify(inst, answer)[0]
    return {
        "name": "orbit-reduced greedy edge-signature/set-cover scan",
        "complexity": "O(N^2) exact distance evaluations and O(N) memory",
        "wall_clock_sec": round(elapsed, 6),
        "operations": distance_evaluations,
        "distance_evaluations": distance_evaluations,
        "second_candidates": second_candidates,
        "third_candidates": third_candidates,
        "solves": "1/1" if verified else "0/1",
        "verified": verified,
    }


def _torus_distance(L, M, first, second):
    return _cyclic_distance(first[0], second[0], L) + _cyclic_distance(
        first[1], second[1], M
    )


def _attack_panel(instances):
    names = [
        "outlier_degree_tie_break",
        "greedy_farthest_first",
        "random_restart_256",
        "obvious_two_axis_antipodes",
    ]
    results = {
        name: {"successes": 0, "attempts": len(instances), "wall_clock_sec": 0.0}
        for name in names
    }
    for index, inst in enumerate(instances):
        started = time.perf_counter()
        labels = [label for label in range(inst["N"]) if label != inst["anchor"]][:2]
        candidate = sorted([inst["anchor"], *labels])
        results[names[0]]["successes"] += int(verify(inst, candidate)[0])
        results[names[0]]["wall_clock_sec"] += time.perf_counter() - started

        started = time.perf_counter()
        anchor_coordinate = _decode(inst, inst["anchor"])
        coordinates = [
            (x, y) for x in range(inst["L"]) for y in range(inst["M"])
        ]
        second = max(
            coordinates,
            key=lambda point: (
                _torus_distance(inst["L"], inst["M"], anchor_coordinate, point),
                -_encode(inst, *point),
            ),
        )
        third = max(
            (point for point in coordinates if point not in (anchor_coordinate, second)),
            key=lambda point: (
                min(
                    _torus_distance(inst["L"], inst["M"], anchor_coordinate, point),
                    _torus_distance(inst["L"], inst["M"], second, point),
                ),
                -_encode(inst, *point),
            ),
        )
        candidate = sorted(_encode(inst, *point) for point in (anchor_coordinate, second, third))
        results[names[1]]["successes"] += int(verify(inst, candidate)[0])
        results[names[1]]["wall_clock_sec"] += time.perf_counter() - started

        started = time.perf_counter()
        restart_rng = random.Random(700_000 + index)
        solved = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, restart_rng))[0]:
                solved = True
                break
        results[names[2]]["successes"] += int(solved)
        results[names[2]]["wall_clock_sec"] += time.perf_counter() - started

        started = time.perf_counter()
        ax, ay = anchor_coordinate
        obvious = [
            anchor_coordinate,
            ((ax + inst["L"] // 2) % inst["L"], ay),
            (ax, (ay + inst["M"] // 2) % inst["M"]),
        ]
        candidate = sorted(_encode(inst, *point) for point in obvious)
        results[names[3]]["successes"] += int(verify(inst, candidate)[0])
        results[names[3]]["wall_clock_sec"] += time.perf_counter() - started

    for result in results.values():
        result["wall_clock_sec"] = round(result["wall_clock_sec"], 6)
    results[names[0]]["statistic"] = "all vertices have the same degree 4"
    results[names[2]]["restarts_per_instance"] = 256
    return results


def _public_relabel(inst, multiplier, shift):
    if math.gcd(multiplier, inst["N"]) != 1:
        raise ValueError("public relabelling multiplier must be a unit modulo N")
    changed = dict(inst)
    changed["encoding_layers"] = [list(layer) for layer in inst["encoding_layers"]]
    changed["encoding_layers"].append([multiplier % inst["N"], shift % inst["N"]])
    changed["anchor"] = (multiplier * inst["anchor"] + shift) % inst["N"]
    changed["answer"] = sorted(
        (multiplier * label + shift) % inst["N"] for label in inst["answer"]
    )
    return _refresh_derived(changed)


def _swap_factors(inst):
    changed = dict(inst)
    changed["L"], changed["M"] = inst["M"], inst["L"]
    changed["r"], changed["t"] = inst["t"], inst["r"]
    changed["transpose_before_flattening"] = not inst["transpose_before_flattening"]
    changed["encoding_layers"] = [list(layer) for layer in inst["encoding_layers"]]
    return changed


def _coordinate_symmetry(inst, reflect_x, reflect_y, shift_x, shift_y):
    """Carry the anchor and witness through a torus translation/reflection."""
    changed = dict(inst)

    def move(label):
        x, y = _decode(inst, label)
        if reflect_x:
            x = -x
        if reflect_y:
            y = -y
        return _encode(
            inst,
            (x + shift_x) % inst["L"],
            (y + shift_y) % inst["M"],
        )

    changed["anchor"] = move(inst["anchor"])
    changed["answer"] = sorted(move(label) for label in inst["answer"])
    return changed


def _answer_atoms(answer):
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest():
    report = {
        "paper": "1602.00291",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_seed": _SHIPPING_SEED,
    }

    planted_cases = []
    all_planted = True
    json_native = True
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            all_planted &= ok
            json_native &= json.loads(json.dumps(inst["answer"])) == inst["answer"]
            planted_cases.append(
                {"preset": preset, "seed": seed, "ok": ok, "reason": reason}
            )
    report["G1_planted_verifies"] = {
        "pass": all_planted and json_native,
        "cases": planted_cases,
        "json_native": json_native,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=_SHIPPING_SEED, **shipping_params)
    answer = shipping["answer"]
    swapped = list(answer)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = list(answer)
    duplicated[2] = duplicated[1]
    out_of_range = list(answer)
    out_of_range[-1] = shipping["N"]
    corruptions = {
        "drop_one": answer[:-1],
        "swap_two": swapped,
        "duplicate_one": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    corruption_cases = {}
    corruption_reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_cases[name] = {"rejected": not ok, "reason": reason}
        corruption_reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": (
            all(case["rejected"] for case in corruption_cases.values())
            and len(set(corruption_reasons)) == len(corruption_reasons)
        ),
        "distinct_reasons": len(set(corruption_reasons)),
        "cases": corruption_cases,
    }

    realistic = (
        "I used the torus symmetries and decoded the anchor.\n```text\n<answer>"
        + ", ".join(map(str, answer))
        + "</answer>\n```\nThe labels are sorted."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("no tagged answer here") is None,
        "parsed_equals_answer": parsed == answer,
        "garbage_returns_none": parse_answer("no tagged answer here") is None,
    }

    guess_rng = random.Random(4_160_200_291)
    sample_total = 200_000
    sample_hits = 0
    guess_started = time.perf_counter()
    for _ in range(sample_total):
        sample_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_elapsed = time.perf_counter() - guess_started
    sample_fraction = sample_hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": sample_fraction < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "fraction": sample_fraction,
        "candidate_space": search_space(shipping),
        "candidate_space_bits": search_space(shipping).bit_length() - 1,
        "structure_aware_prior": (
            "uniform sorted triples already constrained to contain the anchor"
        ),
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_started = time.perf_counter()
    demo_count = enumerate_all(demo)
    demo_elapsed = time.perf_counter() - demo_started
    attack_instances = [
        make_instance(seed=810_000 + seed, **shipping_params) for seed in range(8)
    ]
    attacks = _attack_panel(attack_instances)
    reference = _reference_signature_greedy(shipping)
    strongest_name = max(attacks, key=lambda name: attacks[name]["wall_clock_sec"])
    report["G5_density_and_baseline_cost"] = {
        "pass": demo_count is not None and reference["verified"],
        "shipping_sample_hits": sample_hits,
        "shipping_sample_total": sample_total,
        "shipping_solution_density": sample_fraction,
        "shipping_candidate_space": search_space(shipping),
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "demo_count_wall_clock_sec": round(demo_elapsed, 6),
        "strongest_failing_attack": strongest_name,
        "baseline_attack_iterations": attacks[strongest_name]["attempts"],
        "baseline_attack_wall_clock_sec": attacks[strongest_name]["wall_clock_sec"],
        "reference_operations": reference["operations"],
        "reference_wall_clock_sec": reference["wall_clock_sec"],
    }

    all_failed = all(result["successes"] == 0 for result in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and len(attacks) >= 4 and reference["verified"],
        "attacks": attacks,
        "reference_algorithm": reference,
        "paper_standard_method": (
            "Section 3.1 reduces edge metric dimension to set cover over pairs of edges"
        ),
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    scale_started = time.perf_counter()
    doubled = make_instance(seed=2026, **doubled_params)
    doubled_build = time.perf_counter() - scale_started
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(shipping),
        "shipping_vertices": shipping["N"],
        "doubled_vertices": doubled["N"],
        "shipping_candidate_space": search_space(shipping),
        "doubled_candidate_space": search_space(doubled),
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_reason,
    }

    invariant = 0
    carried = 0
    unrelated_keys = []
    selected = []
    diversity_params = {"n": 1, "span": 20, "axis_gap": 21, "encoding_layers": 2}
    for seed in range(1000):
        inst = make_instance(seed=910_000 + seed, **diversity_params)
        key = canonical_key(inst)
        if key in unrelated_keys:
            continue
        unrelated_keys.append(key)
        selected.append(inst)
        if len(selected) == 20:
            break
    for index, inst in enumerate(selected):
        key = canonical_key(inst)
        relabel_rng = random.Random(920_000 + index)
        multiplier = _random_unit(relabel_rng, inst["N"])
        shift = relabel_rng.randrange(inst["N"])
        relabelled = _public_relabel(inst, multiplier, shift)
        swapped_factors = _swap_factors(inst)
        coordinate_moved = _coordinate_symmetry(
            inst,
            reflect_x=bool(index & 1),
            reflect_y=bool(index & 2),
            shift_x=(3 * index + 1) % inst["L"],
            shift_y=(5 * index + 2) % inst["M"],
        )
        composed = _public_relabel(coordinate_moved, multiplier, shift)
        factor_and_label = _public_relabel(swapped_factors, multiplier, shift)
        for transformed in (
            relabelled,
            swapped_factors,
            coordinate_moved,
            composed,
            factor_and_label,
        ):
            invariant += int(canonical_key(transformed) == key)
            carried += int(verify(transformed, transformed["answer"])[0])
    report["G8_canonical_key"] = {
        "pass": (
            len(selected) == 20
            and invariant == 100
            and carried == 100
            and len(set(unrelated_keys)) == 20
        ),
        "invariant_relabellings": invariant,
        "real_transformations_verified": carried,
        "unrelated_attempts": len(selected),
        "unrelated_distinct_keys": len(set(unrelated_keys)),
        "transformations": [
            "bijective affine relabelling of every public vertex label",
            "swap of the two Cartesian cycle factors",
            "translation and independent reflection of the cycle coordinates",
            "composition of coordinate symmetry with public affine relabelling",
            "composition of factor swap with public affine relabelling",
        ],
        "key_scope": "complete on the generated anchored two-cycle torus family",
    }

    answer_chars = len(json.dumps(shipping["answer"]))
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    intended_operations = 18 * len(shipping["encoding_layers"]) + 42
    arms = {
        name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else 0.0
    )
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000 and answer_elements <= 256 and intended_operations <= 300,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
