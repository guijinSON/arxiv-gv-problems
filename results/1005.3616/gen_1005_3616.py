"""Verified generator for conflict-free hypergraph colouring.

The native definition is Definition 1.1 of Smorodinsky's survey
"Conflict-Free Coloring and its Applications" (arXiv:1005.3616): every
hyperedge must contain a colour used by exactly one of its vertices.

This module inverse-generates balanced planted 3-colourings of 4-uniform
hypergraphs.  The answer is sampled first.  Every displayed edge is then
sampled from the same colour-multiplicity mixture, and is admitted only when
the planted colouring is conflict-free on it.  The mixture makes same-colour
and different-colour pairs have equal expected co-incidence, removing the
ordinary pair-spectral signature of naive planting.  Generation never searches
for a colouring of the instance it emits.
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


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:  # Available in the repository; this finite family does not require it.
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - graceful standard-library fallback
    exact_matrices = rationals = None


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "4-uniform hypergraph",
        "three-colour vertex colouring",
        "hyperedge colour multiplicities",
    ],
    "verification_operations": [
        "integer range and surjectivity checks",
        "exact colour-frequency count in every hyperedge",
        "equality comparison with one",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 4, Non-Geometric Hypergraphs, explicitly studies arbitrary "
        "finite hypergraphs; this selects that native branch of the survey "
        "rather than reducing a geometric object."
    ),
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Useful information appears in higher-order intersections of "
        "hyperedges because the planting equalizes all pair co-incidence "
        "rates in expectation; without exploiting those intersections a "
        "solver must search the three-colour constraint system."
    ),
    "hardness_basis": (
        "Track A: Theorem 2 of Nakajima--Verwimp--Wrochna--Zivny "
        "(arXiv:2501.12062) proves NP-hardness of finding an l-conflict-free "
        "colouring of a promised k-conflict-free r-uniform hypergraph for "
        "r=4 and 3<=k<=l; here k=l=3, n=120, m/n=3, with a balanced "
        "pair-neutral planted distribution, and the shipping measurements "
        "show 0/8 successes for 2,500-node DPLL (20,008 nodes, 48,055,606 "
        "counted operations, 23.263541 seconds total) and all "
        "construction-aware attacks (worst-case hardness alone is not claimed "
        "as distributional evidence)."
    ),
    "max_answer_tokens": 61,
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


# ``n`` is the number of vertices and ``m`` the number of four-vertex edges.
# The non-demo presets increase both the ground set and crowding.  Once the
# named ladder is exhausted, escalate() raises m while keeping the 240-entry
# answer fixed.
DIFFICULTY = {
    "demo": {"n": 9, "m": 12},
    "easy": {"n": 120, "m": 360},
    "medium": {"n": 180, "m": 558},
    "hard": {"n": 240, "m": 768},
}

SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Look for information in intersections of several hyperedges, since "
    "single-vertex and pair co-incidence statistics are neutralized."
)
PLACEBO_HINT = (
    "Look for accuracy across all displayed hyperedges, since careful vertex "
    "indexing and consistent checking are important throughout."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly n entries from {0,1,2}, using every value at "
        "least once; entry v is the colour of vertex v.  The bounded language "
        "has 3^n - 3*2^n + 3 members."
    ),
    "bounds": {
        "length": "n",
        "alphabet": [0, 1, 2],
        "all_colours_used": True,
        "candidate_count": "3^n - 3*2^n + 3",
        "shipping_max_atoms": 120,
    },
}

NOTES = (
    "Section 1.1 and Definition 1.1 fix the native object and exact condition: "
    "a colour must occur exactly once in every hyperedge.  The same section "
    "warns that 3-uniform CF-colouring collapses to ordinary non-monochromatic "
    "colouring, so this family uses rank four.  Section 5 says optimal CF "
    "colouring of even congruent-disc hypergraphs is NP-hard, but also gives "
    "an O(n log n) construction of a non-optimal O(log n)-colouring; that "
    "result cannot justify Track A for arbitrary planted instances.  A later "
    "complete promise-CSP classification, Theorem 2 of arXiv:2501.12062, "
    "places promised 3-CF-colouring of 4-uniform hypergraphs in the NP-hard "
    "regime and identifies the exceptional easy case k=2: Gaussian elimination "
    "over GF(2).  The generator therefore samples three balanced colour classes "
    "first, draws every edge from one pair-neutral valid-edge mixture, and "
    "rejects the vanishingly rare candidate whose binary parity system is "
    "consistent.  Degree sorting, input periodicity, one-pass greedy, "
    "min-conflicts restarts, pair-spectral clustering, the binary GF(2) route, "
    "and bounded DPLL are all tested.  The failed 3-uniform prototype was "
    "discarded because WalkSAT recovered witnesses on most trials."
)


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"^\s*```(?:json|python)?\s*(.*?)\s*```\s*$", re.I | re.S)
_GUESS_SAMPLES = 200_000
_DPLL_NODE_CAP = 2_500

# Filled from the script-owned oracle runs after hardening.  Zero attempts mean
# "not run", never "the oracle failed".
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_params(n, m, seed):
    if not _is_int(n) or n < 9 or n % 3:
        raise ValueError("n must be an integer at least 9 and divisible by 3")
    if not _is_int(m) or m < n or m > math.comb(n, 4):
        raise ValueError("m must be an integer from n through binomial(n,4)")
    if not _is_int(seed):
        raise ValueError("seed must be an integer")


def _edge_type(edge, colouring):
    counts = [0, 0, 0]
    for vertex in edge:
        counts[colouring[vertex]] += 1
    return tuple(sorted(counts, reverse=True))


def _connected_and_nonisolated(n, edges):
    neighbors = [set() for _ in range(n)]
    for edge in edges:
        for vertex in edge:
            neighbors[vertex].update(other for other in edge if other != vertex)
    if any(not row for row in neighbors):
        return False
    seen = {0}
    stack = [0]
    while stack:
        vertex = stack.pop()
        for other in neighbors[vertex]:
            if other not in seen:
                seen.add(other)
                stack.append(other)
    return len(seen) == n


def _binary_parity_solution(n, edges, counts=None):
    """Solve xor_{v in edge} x_v = 1; return None if inconsistent.

    On a four-vertex edge, a two-colouring is conflict-free exactly when one
    colour has odd multiplicity, which is precisely this affine GF(2) system.
    Rows are Python integer bitsets, so no non-standard dependency is needed.
    """
    basis = {}
    rhs_basis = {}
    for edge in edges:
        mask = 0
        for vertex in edge:
            mask ^= 1 << vertex
        rhs = 1
        while mask:
            pivot = mask.bit_length() - 1
            if counts is not None:
                counts["xor_steps"] += 1
            if pivot not in basis:
                basis[pivot] = mask
                rhs_basis[pivot] = rhs
                break
            mask ^= basis[pivot]
            rhs ^= rhs_basis[pivot]
        if not mask and rhs:
            return None
    answer = [0] * n
    for pivot in sorted(basis):
        row = basis[pivot] & ~(1 << pivot)
        parity = 0
        while row:
            bit = row & -row
            parity ^= answer[bit.bit_length() - 1]
            row ^= bit
            if counts is not None:
                counts["back_substitutions"] += 1
        answer[pivot] = rhs_basis[pivot] ^ parity
    return answer


def _sample_edges(n, m, colouring, rng):
    """Sample one pair-neutral valid-edge set from the planted colouring."""
    class_size = n // 3
    # Exact finite-n weight making the expected co-incidence of a fixed pair
    # the same whether its planted colours agree or differ.  Type (3,1,0)
    # receives weight 1 and type (2,1,1) receives weight numerator/denominator.
    numerator = 2 * (class_size + 1) * (class_size - 2)
    denominator = class_size * (3 * class_size - 5)
    edges = set()
    draws = 0
    draw_cap = max(100_000, 500 * m)
    while len(edges) < m and draws < draw_cap:
        edge = tuple(sorted(rng.sample(range(n), 4)))
        draws += 1
        if edge in edges:
            continue
        kind = _edge_type(edge, colouring)
        if kind == (3, 1, 0):
            edges.add(edge)
        elif kind == (2, 1, 1) and rng.randrange(denominator) < numerator:
            edges.add(edge)
    if len(edges) != m:
        raise RuntimeError("edge rejection sampler exceeded its deterministic cap")
    return sorted(edges), draws, [numerator, denominator]


def make_instance(n, seed=0, m=None, **params):
    """Inverse-generate a promised 3-CF-colourable 4-uniform hypergraph.

    The colouring is sampled before a single edge exists.  Edges are accepted
    only according to their colour multiplicity under that already-held
    witness.  Screening the easy binary special case never searches for the
    planted three-colouring.
    """
    if params:
        raise ValueError(f"unknown parameters: {', '.join(sorted(params))}")
    if m is None:
        m = 3 * n
    _validate_params(n, m, seed)
    rng = random.Random(seed)

    answer = [colour for colour in range(3) for _ in range(n // 3)]
    rng.shuffle(answer)

    edges = None
    total_draws = 0
    acceptance_weight = None
    for attempt in range(1, 65):
        trial, draws, acceptance_weight = _sample_edges(n, m, answer, rng)
        total_draws += draws
        if not _connected_and_nonisolated(n, trial):
            continue
        # Exclude the polynomial k=2 exception.  At shipping density this test
        # is almost always inconsistent on the first attempt.
        if _binary_parity_solution(n, trial) is not None:
            continue
        edges = trial
        break
    if edges is None:
        raise RuntimeError("could not obtain a connected non-binary instance")

    return {
        "paper": "arXiv:1005.3616",
        "family": "pair-neutral planted 3-CF-colouring",
        "n": n,
        "m": m,
        "colour_count": 3,
        "edge_size": 4,
        "edges": [list(edge) for edge in edges],
        "pair_neutral_weight_211": acceptance_weight,
        "generation_attempts": attempt,
        "edge_draws": total_draws,
        "answer": answer,
    }


def render(inst):
    """Render a self-contained native hypergraph-colouring problem."""
    lines = [
        "Find a conflict-free 3-colouring of the displayed 4-uniform hypergraph.",
        "",
        "Definitions.",
        f"The vertices are the integers 0 through {inst['n'] - 1}, inclusive.",
        "A colouring assigns one of the labelled colours 0, 1, or 2 to every",
        "vertex.  It is conflict-free when every hyperedge contains at least",
        "one colour that occurs on exactly one vertex of that hyperedge.",
        "For example, edge colours (0,0,0,1) and (0,0,1,2) are valid, while",
        "(0,0,0,0) and (0,0,1,1) are invalid.  Hyperedges are unordered sets",
        "of four distinct vertices; their displayed order has no meaning.",
        "",
        "Use all three colours at least once.  It is guaranteed that this",
        "instance has no conflict-free colouring using only two colours.",
        f"There are exactly {inst['n']} output entries: entry v is the colour",
        "of vertex v.  Vertex numbering is 0-based, repetitions of colours are",
        "allowed, and the order of output entries is therefore significant.",
        "",
        f"Hyperedges ({inst['m']} rows, in the format edge-ID: four vertices):",
    ]
    for edge_id, edge in enumerate(inst["edges"]):
        lines.append(f"{edge_id}: {' '.join(str(vertex) for vertex in edge)}")
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as one JSON list",
        f"of exactly {inst['n']} integers, each 0, 1, or 2.",
        "Example format: <answer>[0, 1, 2, 0]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Extract the first tagged JSON or comma-separated integer list."""
    try:
        if not isinstance(text, str):
            return None
        match = _ANSWER_RE.search(text)
        if not match:
            return None
        body = match.group(1).strip()
        fenced = _FENCE_RE.match(body)
        if fenced:
            body = fenced.group(1).strip()
        try:
            value = json.loads(body)
        except (json.JSONDecodeError, TypeError):
            stripped = body.strip().strip("[]")
            if not stripped:
                return []
            pieces = [piece for piece in re.split(r"[\s,]+", stripped) if piece]
            if any(re.fullmatch(r"[-+]?\d+", piece) is None for piece in pieces):
                return None
            value = [int(piece) for piece in pieces]
        if not isinstance(value, list):
            return None
        if any(not _is_int(item) for item in value):
            return None
        return value
    except Exception:  # malformed model output must never escape the parser
        return None


def verify(inst, answer):
    """Check any valid witness exactly, without consulting inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a list"
    if not answer:
        return False, "answer is empty"
    n = inst["n"]
    if len(answer) < n:
        return False, f"too few vertex colours: expected {n}, received {len(answer)}"
    if len(answer) > n:
        return False, f"too many vertex colours: expected {n}, received {len(answer)}"
    for vertex, colour in enumerate(answer):
        if not _is_int(colour):
            return False, f"colour at vertex {vertex} is not an integer"
        if colour not in (0, 1, 2):
            return False, f"colour at vertex {vertex} is outside 0..2"
    if set(answer) != {0, 1, 2}:
        return False, "all three labelled colours must occur at least once"
    for edge_id, edge in enumerate(inst["edges"]):
        counts = [0, 0, 0]
        for vertex in edge:
            counts[answer[vertex]] += 1
        if 1 not in counts:
            return False, (
                f"hyperedge {edge_id} has no uniquely occurring colour "
                f"(multiplicities {counts})"
            )
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from the stated surjective length-n ternary strings."""
    while True:
        candidate = [rng.randrange(3) for _ in range(inst["n"])]
        if set(candidate) == {0, 1, 2}:
            return candidate


def search_space(inst):
    n = inst["n"]
    return 3 ** n - 3 * (2 ** n) + 3


def enumerate_all(inst):
    """Count valid surjective colourings exactly when the language is small."""
    if search_space(inst) > 1_000_000:
        return None
    count = 0
    for candidate in itertools.product(range(3), repeat=inst["n"]):
        if set(candidate) == {0, 1, 2}:
            count += int(verify(inst, list(candidate))[0])
    return count


def _wl_digest(kind, old, neighbor_colours):
    payload = json.dumps(
        [kind, old, sorted(neighbor_colours)],
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_key(inst):
    """A strong cheap incidence invariant, not a full isomorphism canonizer."""
    n = inst["n"]
    edges = [tuple(edge) for edge in inst["edges"]]
    incident = [[] for _ in range(n)]
    for edge_id, edge in enumerate(edges):
        for vertex in edge:
            incident[vertex].append(edge_id)
    vertex_colours = [f"V:{len(incident[v])}" for v in range(n)]
    edge_colours = ["E:4"] * len(edges)
    for _ in range(6):
        new_vertices = [
            _wl_digest("V", vertex_colours[v],
                       [edge_colours[e] for e in incident[v]])
            for v in range(n)
        ]
        new_edges = [
            _wl_digest("E", edge_colours[e],
                       [vertex_colours[v] for v in edge])
            for e, edge in enumerate(edges)
        ]
        vertex_colours, edge_colours = new_vertices, new_edges

    pair_codegrees = {}
    for edge in edges:
        for u, v in itertools.combinations(edge, 2):
            pair = (u, v) if u < v else (v, u)
            pair_codegrees[pair] = pair_codegrees.get(pair, 0) + 1
    intersection_histogram = [0] * 5
    edge_sets = [set(edge) for edge in edges]
    for i in range(len(edges)):
        for j in range(i):
            intersection_histogram[len(edge_sets[i] & edge_sets[j])] += 1
    payload = {
        "n": n,
        "m": len(edges),
        "vertex_refinement": sorted(vertex_colours),
        "edge_refinement": sorted(edge_colours),
        "pair_codegrees": sorted(pair_codegrees.values()),
        "edge_intersections": intersection_histogram,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _incidence(inst):
    incident = [[] for _ in range(inst["n"])]
    for edge_id, edge in enumerate(inst["edges"]):
        for vertex in edge:
            incident[vertex].append(edge_id)
    return incident


def _ensure_surjective(candidate):
    candidate = list(candidate)
    missing = [colour for colour in range(3) if colour not in candidate]
    for colour, vertex in zip(missing, range(len(candidate))):
        candidate[vertex] = colour
    return candidate


def _attack_degree_tertiles(inst):
    incident = _incidence(inst)
    order = sorted(range(inst["n"]), key=lambda v: (len(incident[v]), v))
    answer = [0] * inst["n"]
    for rank, vertex in enumerate(order):
        answer[vertex] = min(2, 3 * rank // inst["n"])
    return answer


def _attack_input_period(inst):
    return [vertex % 3 for vertex in range(inst["n"])]


def _greedy_candidate(inst, rng, random_order=False):
    n = inst["n"]
    edges = inst["edges"]
    incident = _incidence(inst)
    order = list(range(n))
    if random_order:
        rng.shuffle(order)
    else:
        order.sort(key=lambda v: (-len(incident[v]), v))
    answer = [-1] * n
    operations = 0
    for position, vertex in enumerate(order):
        colour_order = list(range(3))
        if random_order:
            rng.shuffle(colour_order)
        else:
            preferred = position % 3
            colour_order = [preferred] + [c for c in range(3) if c != preferred]
        scored = []
        for colour in colour_order:
            answer[vertex] = colour
            bad = 0
            for edge_id in incident[vertex]:
                operations += 1
                edge = edges[edge_id]
                if all(answer[v] >= 0 for v in edge):
                    counts = [0, 0, 0]
                    for v in edge:
                        counts[answer[v]] += 1
                    bad += int(1 not in counts)
            scored.append((bad, colour_order.index(colour), colour))
        answer[vertex] = min(scored)[2]
    return _ensure_surjective(answer), operations


def _attack_random_greedy(inst, rng, restarts=64):
    operations = 0
    last = None
    for _ in range(restarts):
        last, used = _greedy_candidate(inst, rng, True)
        operations += used
        if verify(inst, last)[0]:
            return last, True, operations
    return last, False, operations


def _edge_bad(answer, edge):
    counts = [0, 0, 0]
    for vertex in edge:
        counts[answer[vertex]] += 1
    return 1 not in counts


def _attack_min_conflicts(inst, rng, restarts=16, steps=1500):
    """WalkSAT-style random restarts with min-conflict recolouring."""
    n = inst["n"]
    edges = inst["edges"]
    incident = _incidence(inst)
    operations = 0
    last = None
    for _ in range(restarts):
        answer = [rng.randrange(3) for _ in range(n)]
        answer = _ensure_surjective(answer)
        bad = {i for i, edge in enumerate(edges) if _edge_bad(answer, edge)}
        operations += len(edges)
        for _step in range(steps):
            if not bad:
                return answer, True, operations
            edge_id = rng.choice(tuple(bad))
            edge = edges[edge_id]
            choices = []
            if rng.randrange(5) == 0:
                vertex = rng.choice(edge)
                choices = [(vertex, colour) for colour in range(3)
                           if colour != answer[vertex]]
            else:
                for vertex in edge:
                    old = answer[vertex]
                    before = sum(i in bad for i in incident[vertex])
                    for colour in range(3):
                        if colour == old:
                            continue
                        answer[vertex] = colour
                        after = 0
                        for other_edge in incident[vertex]:
                            operations += 1
                            after += int(_edge_bad(answer, edges[other_edge]))
                        choices.append((after - before, vertex, colour))
                    answer[vertex] = old
                best = min(choice[0] for choice in choices)
                choices = [(vertex, colour) for score, vertex, colour in choices
                           if score == best]
            vertex, colour = rng.choice(choices)
            answer[vertex] = colour
            for other_edge in incident[vertex]:
                operations += 1
                if _edge_bad(answer, edges[other_edge]):
                    bad.add(other_edge)
                else:
                    bad.discard(other_edge)
        last = _ensure_surjective(answer)
    return last, False, operations


def _orthogonalize(vector, bases):
    vector = list(vector)
    mean = sum(vector) / len(vector)
    vector = [value - mean for value in vector]
    for base in bases:
        dot = sum(x * y for x, y in zip(vector, base))
        vector = [x - dot * y for x, y in zip(vector, base)]
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return [0.0] * len(vector)
    return [value / norm for value in vector]


def _attack_pair_spectral(inst):
    """Two-vector spectral clustering of the pair co-incidence matrix."""
    n = inst["n"]
    rng = random.Random(0x10053616)
    bases = []
    for _component in range(2):
        vector = _orthogonalize(
            [rng.uniform(-1.0, 1.0) for _ in range(n)], bases
        )
        for _ in range(80):
            nxt = [6.0 * value for value in vector]
            for edge in inst["edges"]:
                total = sum(vector[v] for v in edge)
                for vertex in edge:
                    nxt[vertex] += total - vector[vertex]
            vector = _orthogonalize(nxt, bases)
        bases.append(vector)
    points = list(zip(bases[0], bases[1]))
    first = min(range(n), key=lambda v: points[v][0])
    second = max(range(n), key=lambda v: points[v][0])
    third = max(range(n), key=lambda v: points[v][1])
    centers = [points[first], points[second], points[third]]
    labels = [0] * n
    for _ in range(24):
        labels = [
            min(range(3), key=lambda c: (
                (point[0] - centers[c][0]) ** 2
                + (point[1] - centers[c][1]) ** 2,
                c,
            ))
            for point in points
        ]
        new_centers = []
        for colour in range(3):
            members = [points[v] for v in range(n) if labels[v] == colour]
            if not members:
                new_centers.append(centers[colour])
            else:
                new_centers.append((
                    sum(point[0] for point in members) / len(members),
                    sum(point[1] for point in members) / len(members),
                ))
        centers = new_centers
    return _ensure_surjective(labels)


def _dpll_solve(inst, node_cap=_DPLL_NODE_CAP):
    """Bounded DPLL with colour symmetry breaking and domain propagation."""
    n = inst["n"]
    edges = inst["edges"]
    incident = _incidence(inst)
    counts = {
        "nodes": 0,
        "edge_checks": 0,
        "domain_tests": 0,
        "forced_assignments": 0,
        "branches": 0,
        "capped": False,
    }

    def domain(vertex, assignment):
        allowed = {0, 1, 2}
        for edge_id in incident[vertex]:
            edge = edges[edge_id]
            if sum(assignment[v] < 0 for v in edge) != 1:
                continue
            for colour in tuple(allowed):
                local = [0, 0, 0]
                for v in edge:
                    local[colour if v == vertex else assignment[v]] += 1
                counts["domain_tests"] += 1
                if 1 not in local:
                    allowed.discard(colour)
        return allowed

    def recurse(assignment):
        counts["nodes"] += 1
        if counts["nodes"] > node_cap:
            counts["capped"] = True
            return None

        # Repeated singleton-domain propagation.
        while True:
            forced = None
            best = None
            best_domain = None
            best_key = None
            for vertex in range(n):
                if assignment[vertex] >= 0:
                    continue
                allowed = domain(vertex, assignment)
                if not allowed:
                    return None
                if len(allowed) == 1:
                    forced = (vertex, next(iter(allowed)))
                    break
                frontier = [0, 0, 0, 0]
                for edge_id in incident[vertex]:
                    assigned = sum(assignment[v] >= 0 for v in edges[edge_id])
                    counts["edge_checks"] += 1
                    frontier[assigned] += 1
                key = (-len(allowed), frontier[3], frontier[2],
                       len(incident[vertex]), -vertex)
                if best_key is None or key > best_key:
                    best_key = key
                    best = vertex
                    best_domain = allowed
            if forced is None:
                break
            assignment[forced[0]] = forced[1]
            counts["forced_assignments"] += 1

        if best is None:
            return assignment

        used = {colour for colour in assignment if colour >= 0}
        max_new = min(2, (max(used) + 1) if used else 0)
        choices = [colour for colour in range(max_new + 1)
                   if colour in best_domain]
        for colour in choices:
            counts["branches"] += 1
            child = list(assignment)
            child[best] = colour
            result = recurse(child)
            if result is not None:
                return result
            if counts["capped"]:
                return None
        return None

    answer = recurse([-1] * n)
    return answer, counts


def _relabel_instance(inst, rng):
    """Compose vertex relabelling, edge reordering, and within-edge ordering."""
    n = inst["n"]
    new_to_old = list(range(n))
    rng.shuffle(new_to_old)
    old_to_new = {old: new for new, old in enumerate(new_to_old)}
    edges = []
    for old_edge in inst["edges"]:
        new_edge = [old_to_new[vertex] for vertex in old_edge]
        rng.shuffle(new_edge)
        edges.append(new_edge)
    rng.shuffle(edges)
    transformed = {
        key: value for key, value in inst.items()
        if key not in ("edges", "answer")
    }
    transformed["edges"] = edges
    transformed["answer"] = [inst["answer"][old] for old in new_to_old]
    return transformed


def _find_bad_swap(inst):
    planted = inst["answer"]
    # Search only for a corruption to test the checker, never to generate the
    # held certificate.
    for i in range(inst["n"]):
        for j in range(i):
            if planted[i] == planted[j]:
                continue
            trial = list(planted)
            trial[i], trial[j] = trial[j], trial[i]
            ok, reason = verify(inst, trial)
            if not ok and reason.startswith("hyperedge"):
                return trial
    raise AssertionError("could not find a rejecting colour swap")


def escalate(params):
    """Tighten crowding at fixed answer length, then report the atom cap."""
    params = {key: value for key, value in dict(params).items()
              if not key.startswith("_")}
    n = params["n"]
    m = params.get("m", 3 * n)
    if m < 5 * n:
        params["m"] = min(5 * n, m + max(1, n // 4))
        return params
    # The fixed-length density axis has been exhausted.  More vertices would
    # take the 240-atom hard answer over the published 256-atom ceiling.
    return "cap_bound"


def selftest():
    """Run all mandatory local gates and return JSON-native measurements."""
    report = {
        "paper": "1005.3616",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    g1_failures = []
    g1_attempts = 0
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 7, 29):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            g1_attempts += 1
            json_roundtrips += int(json_ok)
            if not ok or not json_ok:
                g1_failures.append([preset, seed, reason, json_ok])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "json_native_roundtrips": json_roundtrips,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=10053616, **shipping_params)
    planted = shipping["answer"]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": _find_bad_swap(shipping),
        "duplicate_one": planted + [planted[-1]],
        "empty": [],
        "out_of_range": [3] + planted[1:],
    }
    corruption_cases = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_cases[name] = {"accepted": bool(ok), "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": (
            all(not result["accepted"] for result in corruption_cases.values())
            and len(set(reasons)) == len(reasons)
        ),
        "cases": corruption_cases,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "I checked the edge multiplicities.\n\n<answer>\n```json\n"
        + json.dumps(planted)
        + "\n```\n</answer>\nThe list is in vertex order."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and verify(shipping, parsed)[0],
        "parsed": parsed is not None,
        "roundtrip_equal": parsed == planted,
    }

    guess_rng = random.Random(0x10053616)
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(_GUESS_SAMPLES):
        guess_hits += int(verify(
            shipping, random_candidate(shipping, guess_rng)
        )[0])
    guess_wall = time.perf_counter() - guess_start
    guess_fraction = guess_hits / _GUESS_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": _GUESS_SAMPLES >= 200_000 and guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": _GUESS_SAMPLES,
        "observed_fraction": guess_fraction,
        "structure_aware_space": search_space(shipping),
        "prior": "uniform over surjective length-n ternary strings",
        "wall_clock_sec": round(guess_wall, 6),
    }

    attack_names = [
        "outlier_degree_tertiles",
        "input_period_012",
        "greedy_most_incident",
        "random_greedy_restart_64",
        "min_conflicts_restart_16x1500",
        "pair_spectral_two_vector",
        "binary_parity_gaussian",
        "dpll_domain_propagation_2500",
    ]
    attacks = {
        name: {
            "successes": 0,
            "attempts": 0,
            "wall_clock_sec": 0.0,
        }
        for name in attack_names
    }
    attack_operations = {
        "greedy_most_incident": 0,
        "random_greedy_restart_64": 0,
        "min_conflicts_restart_16x1500": 0,
        "binary_parity_gaussian": 0,
        "dpll_domain_propagation_2500": 0,
    }
    dpll_totals = {
        "nodes": 0,
        "edge_checks": 0,
        "domain_tests": 0,
        "forced_assignments": 0,
        "branches": 0,
        "capped_attempts": 0,
    }
    for seed in range(8):
        inst = make_instance(seed=50_000 + seed, **shipping_params)
        rng = random.Random(60_000 + seed)

        timed_candidates = {}
        start = time.perf_counter()
        timed_candidates["outlier_degree_tertiles"] = _attack_degree_tertiles(inst)
        attacks["outlier_degree_tertiles"]["wall_clock_sec"] += (
            time.perf_counter() - start
        )

        start = time.perf_counter()
        timed_candidates["input_period_012"] = _attack_input_period(inst)
        attacks["input_period_012"]["wall_clock_sec"] += time.perf_counter() - start

        start = time.perf_counter()
        greedy, operations = _greedy_candidate(inst, rng, False)
        attacks["greedy_most_incident"]["wall_clock_sec"] += (
            time.perf_counter() - start
        )
        attack_operations["greedy_most_incident"] += operations
        timed_candidates["greedy_most_incident"] = greedy

        start = time.perf_counter()
        restarted, _won, operations = _attack_random_greedy(inst, rng, 64)
        attacks["random_greedy_restart_64"]["wall_clock_sec"] += (
            time.perf_counter() - start
        )
        attack_operations["random_greedy_restart_64"] += operations
        timed_candidates["random_greedy_restart_64"] = restarted

        start = time.perf_counter()
        min_conflicts, _won, operations = _attack_min_conflicts(
            inst, rng, 16, 1500
        )
        attacks["min_conflicts_restart_16x1500"]["wall_clock_sec"] += (
            time.perf_counter() - start
        )
        attack_operations["min_conflicts_restart_16x1500"] += operations
        timed_candidates["min_conflicts_restart_16x1500"] = min_conflicts

        start = time.perf_counter()
        timed_candidates["pair_spectral_two_vector"] = _attack_pair_spectral(inst)
        attacks["pair_spectral_two_vector"]["wall_clock_sec"] += (
            time.perf_counter() - start
        )

        parity_counts = {"xor_steps": 0, "back_substitutions": 0}
        start = time.perf_counter()
        binary = _binary_parity_solution(inst["n"], inst["edges"], parity_counts)
        attacks["binary_parity_gaussian"]["wall_clock_sec"] += (
            time.perf_counter() - start
        )
        attack_operations["binary_parity_gaussian"] += sum(parity_counts.values())
        timed_candidates["binary_parity_gaussian"] = binary

        start = time.perf_counter()
        dpll, dpll_counts = _dpll_solve(inst, _DPLL_NODE_CAP)
        attacks["dpll_domain_propagation_2500"]["wall_clock_sec"] += (
            time.perf_counter() - start
        )
        for field in ("nodes", "edge_checks", "domain_tests",
                      "forced_assignments", "branches"):
            dpll_totals[field] += dpll_counts[field]
        dpll_totals["capped_attempts"] += int(dpll_counts["capped"])
        dpll_ops = (
            dpll_counts["edge_checks"] + dpll_counts["domain_tests"]
            + dpll_counts["forced_assignments"] + dpll_counts["branches"]
        )
        attack_operations["dpll_domain_propagation_2500"] += dpll_ops
        timed_candidates["dpll_domain_propagation_2500"] = dpll

        for name, candidate in timed_candidates.items():
            won = candidate is not None and verify(inst, candidate)[0]
            attacks[name]["successes"] += int(won)
            attacks[name]["attempts"] += 1

    for name, result in attacks.items():
        result["wall_clock_sec"] = round(result["wall_clock_sec"], 6)
        if name in attack_operations:
            result["operations"] = attack_operations[name]
    attacks["dpll_domain_propagation_2500"].update(dpll_totals)
    all_attacks_failed = all(
        result["successes"] == 0 and result["attempts"] >= 8
        for result in attacks.values()
    )
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed,
        "attacks": attacks,
        "standard_algorithm": "bounded DPLL with domain/unit propagation",
        "construction_attack": "two-vector pair-co-incidence spectral clustering",
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_start = time.perf_counter()
    demo_count = enumerate_all(demo)
    demo_wall = time.perf_counter() - demo_start
    baseline = attacks["dpll_domain_propagation_2500"]
    report["G5_density_and_baseline_cost"] = {
        "pass": (
            guess_fraction < 1e-6
            and demo_count is not None
            and baseline["successes"] == 0
            and baseline["capped_attempts"] == 8
        ),
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": _GUESS_SAMPLES,
        "shipping_sampled_density": guess_fraction,
        "shipping_candidate_space": search_space(shipping),
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "demo_count_wall_sec": round(demo_wall, 6),
        "strongest_attack": "bounded DPLL with domain/unit propagation",
        "baseline_node_cap_each": _DPLL_NODE_CAP,
        "baseline_nodes_total": baseline["nodes"],
        "baseline_operations_total": baseline["operations"],
        "baseline_wall_sec_total": baseline["wall_clock_sec"],
    }

    doubled_params = {
        "n": 2 * shipping["n"],
        "m": 2 * shipping["m"],
    }
    start = time.perf_counter()
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": bool(doubled_ok),
        "base_n": shipping["n"],
        "base_m": shipping["m"],
        "doubled_n": doubled["n"],
        "doubled_m": doubled["m"],
        "build_wall_sec": round(doubled_build, 6),
        "verify_reason": doubled_reason,
    }

    invariant_checks = 0
    carried_checks = 0
    distinct_keys = []
    g8_failures = []
    g8_params = DIFFICULTY["easy"]
    for seed in range(20):
        inst = make_instance(seed=70_000 + seed, **g8_params)
        transformed = _relabel_instance(inst, random.Random(80_000 + seed))
        invariant_checks += 1
        if canonical_key(inst) != canonical_key(transformed):
            g8_failures.append([seed, "key changed under composed relabelling"])
        carried_checks += 1
        if not verify(transformed, transformed["answer"])[0]:
            g8_failures.append([seed, "carried colouring did not verify"])
        distinct_keys.append(canonical_key(inst))
    distinct_count = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": (
            not g8_failures
            and invariant_checks >= 20
            and carried_checks >= 20
            and distinct_count == 20
        ),
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct_count,
        "failures": g8_failures,
        "key_kind": "six-round incidence WL plus exact intersection histograms",
    }

    answer_blob = json.dumps(planted, separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(planted)
    intended_operations = shipping["n"]
    arms = {
        arm: {
            "solved": int(G9_ORACLE_RESULTS[arm]["solved"]),
            "attempts": int(G9_ORACLE_RESULTS[arm]["attempts"]),
        }
        for arm in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else None
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else None
    )
    hint_delta = (
        hinted_rate - placebo_rate
        if hinted_rate is not None and placebo_rate is not None else None
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hint_delta,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
