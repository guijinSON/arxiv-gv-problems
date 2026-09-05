"""Verified generator for two-2-list colorings of plane graphs.

The native problem is Theorem 1.3 of Postle--Thomas, arXiv:1402.1813:
two vertices of the outer cycle have lists of size two, the other outer
vertices have lists of size at least three, and interior vertices have lists
of size at least five.  A witness is an ordinary proper list-coloring.

Instances are inverse-generated without solving them.  A fixed colored
icosahedron is subdivided into triangular barycentric grids, one face is made
the outer face, and the coloring is carried through subdivision by a parity
identity.  Vertex names and colors are then scrambled and decoy list entries
are sampled.  The renderer exposes several scrambled base-key candidates, so a
solver who discovers the parity invariant has a compact exact route.  The verifier does
not rely on that route: it checks only the submitted colors, displayed lists,
and displayed edges.
"""

from __future__ import annotations

import functools
import hashlib
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
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "plane graph with a specified outer cycle",
        "vertex list-assignment",
        "proper list-coloring",
    ],
    "verification_operations": [
        "integer list membership",
        "exact inequality on every edge",
        "cycle and answer-shape checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Barycentric coefficient parity transports a proper base labeling consistently "
        "across all refined triangular faces; without recognizing it, a solver "
        "must carry out a full list-coloring search on the scrambled graph."
    ),
    "hardness_basis": (
        "Track B: the Thomassen-style constructive proof gives an O(N^2) algorithm, "
        "and executable MRV forward-checking follows the same zero-backtrack quadratic "
        "scan on the N=246 candidate in about 0.012 seconds but uses about 151,131 exact "
        "list tests and 246 decisions; selecting the "
        "one list-compatible displayed base key takes about 25 membership probes, "
        "and applying parity is O(N) with 114 XOR operations, so the "
        "former trace "
        "is not executable by hand while the latter is compact once recognized."
    ),
    "max_answer_tokens": 124,
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
    "demo": {"n": 1},
    "easy": {"n": 3},
    "medium": {"n": 4},
    "hard": {"n": 5},
}
# Retained candidate preset.  The script-owned verdict is cap_bound, so this
# module is parked and is not a shipped family under the current 256-atom cap.
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The parity pattern of the barycentric weights is consistent across the "
    "two refined faces incident with every base edge."
)
PLACEBO_HINT = (
    "The ordering of the vertex records is arbitrary, so track the displayed "
    "indices and list boundaries with care."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list containing exactly one integer color per displayed vertex; "
        "entry v is sampled uniformly from the explicitly displayed list L(v)."
    ),
    "bounds": {
        "length": "N = 10*n^2 + 2 - (n-1)(n-2)/2",
        "per_vertex_choices": "2 on two outer vertices, 3 on all other outer "
        "vertices, and 5 on every interior vertex",
        "maximum_shipping_atoms": 246,
        "colors": [0, 1, 2, 3, 4, 5, 6, 7],
    },
}

NOTES = (
    "Section 1 defines an L-coloring as a proper coloring choosing a color from "
    "each vertex list.  Theorem 1.3 fixes the exact regime used here: arbitrary "
    "two vertices of the outer cycle have 2-lists, every other outer vertex has "
    "a list of size at least three, and every interior vertex has a list of size "
    "at least five.  Theorem 1.2 identifies an easier adjacent-precolored-edge "
    "regime; Section 2, especially Lemma 2.3, supplies the extension machinery, "
    "and Theorem 3.1 is the stronger form proved in Section 3.  The paper proves "
    "existence, not a hard distribution, so Track A is not claimed; later work by "
    "Postle records that Thomassen-style proofs naturally yield quadratic-time "
    "coloring algorithms.  The answer "
    "is carried from a fixed icosahedral coloring by a subdivision identity, then "
    "vertex and color names are randomized; eight scrambled base-key candidates are "
    "displayed so the parity route is self-contained without revealing which one fits. "
    "Draws whose list-frequency, first-key, two deterministic greedy, or 256-restart "
    "random-greedy attacks solve them are "
    "discarded without changing or discovering the already-known witness.  The final "
    "bare oracle run solved the 246-vertex maximum-writable preset on two of three "
    "attempts; frequency six needs 352 answer atoms.  The family is therefore parked "
    "as cap_bound, not rejected and not shipped."
)

# Script-owned oracle evidence for the final retained variant.  Bare hardening
# failed at the maximum writable rung, so the G9 hint/placebo arms were not run.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 2, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run_bare_cap_bound",
}


# Icosahedron: north pole 0, upper pentagon 1..5, lower pentagon 6..10,
# south pole 11.  Every edge belongs to exactly two of these 20 faces.
def _u(i):
    return 1 + (i % 5)


def _l(i):
    return 6 + (i % 5)


_BASE_FACES = tuple(
    face
    for i in range(5)
    for face in (
        (0, _u(i), _u(i + 1)),
        (_u(i), _u(i + 1), _l(i)),
        (_u(i), _l(i), _l(i - 1)),
        (11, _l(i), _l(i + 1)),
    )
)

# A fixed proper four-coloring of the base icosahedron, checked in selftest.
_BASE_COLORING = (0, 1, 2, 1, 2, 3, 3, 0, 3, 0, 2, 1)
# Split every one of the four proper base color classes across a high bit.  The
# low two bits still prove adjacent labels differ, while the eight labels make
# five-element interior lists genuine constraints instead of the full palette.
_BASE_LABELING = tuple(
    color | (4 * high)
    for color, high in zip(
        _BASE_COLORING,
        (0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0),
    )
)
_PALETTE = tuple(range(8))


def _affine_permutations():
    """All affine bijections of the three-bit XOR label space."""
    maps = []
    for a in range(1, 8):
        for b in range(1, 8):
            if b == a:
                continue
            for c in range(1, 8):
                if c in (a, b, a ^ b):
                    continue
                for offset in range(8):
                    image = []
                    for value in range(8):
                        mapped = offset
                        if value & 1:
                            mapped ^= a
                        if value & 2:
                            mapped ^= b
                        if value & 4:
                            mapped ^= c
                        image.append(mapped)
                    maps.append(tuple(image))
    return tuple(maps)


_AFFINE_PERMUTATIONS = _affine_permutations()


def _point_key(face, weights):
    """Canonical sparse barycentric coordinates, independent of face order."""
    return tuple((v, w) for v, w in sorted(zip(face, weights)) if w)


@functools.lru_cache(maxsize=None)
def _mesh(frequency):
    """Return immutable (points, edges, outer_cycle) for a refined disk."""
    if isinstance(frequency, bool) or not isinstance(frequency, int) or frequency < 1:
        raise ValueError("n must be a positive integer subdivision frequency")

    points = set()
    edges = set()
    for face in _BASE_FACES:
        local = {}
        for a in range(frequency + 1):
            for b in range(frequency - a + 1):
                c = frequency - a - b
                key = _point_key(face, (a, b, c))
                local[(a, b, c)] = key
                points.add(key)

        # Two lattice points are adjacent exactly when one unit of barycentric
        # weight moves between two base corners.
        for weights, key in local.items():
            for give in range(3):
                if weights[give] == 0:
                    continue
                for take in range(3):
                    if take == give:
                        continue
                    other = list(weights)
                    other[give] -= 1
                    other[take] += 1
                    other = tuple(other)
                    if other in local:
                        edges.add(tuple(sorted((key, local[other]))))

    # Treat the interior of base face (0,1,2) as the unbounded face.  Its
    # subdivided boundary remains and has length 3*frequency.
    outside_vertices = {0, 1, 2}
    removed = {
        point
        for point in points
        if len(point) == 3 and {v for v, _ in point} == outside_vertices
    }
    points.difference_update(removed)
    edges = {
        edge
        for edge in edges
        if edge[0] not in removed and edge[1] not in removed
    }

    outer = []
    for a, b in ((0, 1), (1, 2), (2, 0)):
        for step in range(frequency):
            outer.append(
                tuple(
                    (v, w)
                    for v, w in sorted(
                        ((a, frequency - step), (b, step))
                    )
                    if w
                )
            )

    ordered_points = tuple(sorted(points))
    ordered_edges = tuple(sorted(edges))
    return ordered_points, ordered_edges, tuple(outer)


def _raw_color(point):
    """Carry the base labeling through subdivision by XOR parity."""
    color = 0
    for base_vertex, weight in point:
        if weight & 1:
            color ^= _BASE_LABELING[base_vertex]
    return color


def _parity_decode(tags, base_key, zero_key, frequency):
    """Expand the displayed base key by the barycentric parity identity."""
    decoded = []
    for tag in tags:
        value = zero_key if frequency % 2 == 0 else 0
        first = frequency % 2 == 1
        for base_vertex, weight in tag:
            if weight & 1:
                if first:
                    value = base_key[base_vertex]
                    first = False
                else:
                    value ^= base_key[base_vertex]
        decoded.append(value)
    return decoded


def _adjacency(n_vertices, edges):
    adj = [set() for _ in range(n_vertices)]
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    return adj


def _valid_coloring_data(lists, edges, candidate):
    if not isinstance(candidate, list) or len(candidate) != len(lists):
        return False
    if any(
        isinstance(c, bool) or not isinstance(c, int) or c not in lists[v]
        for v, c in enumerate(candidate)
    ):
        return False
    return all(candidate[a] != candidate[b] for a, b in edges)


def _greedy_candidate(lists, edges, order, rng=None):
    adj = _adjacency(len(lists), edges)
    candidate = [-1] * len(lists)
    for vertex in order:
        available = [
            color
            for color in lists[vertex]
            if all(candidate[w] != color for w in adj[vertex])
        ]
        if not available:
            return None
        candidate[vertex] = rng.choice(available) if rng is not None else available[0]
    return candidate


def _attack_outlier(lists, edges):
    frequency = {color: 0 for color in _PALETTE}
    for choices in lists:
        for color in choices:
            frequency[color] += 1
    candidate = [min(choices, key=lambda c: (frequency[c], c)) for choices in lists]
    return candidate if _valid_coloring_data(lists, edges, candidate) else None


def _attack_label_greedy(lists, edges):
    candidate = _greedy_candidate(lists, edges, range(len(lists)))
    return candidate if candidate is not None and _valid_coloring_data(lists, edges, candidate) else None


def _attack_degree_greedy(lists, edges):
    adj = _adjacency(len(lists), edges)
    order = sorted(range(len(lists)), key=lambda v: (-len(adj[v]), v))
    candidate = _greedy_candidate(lists, edges, order)
    return candidate if candidate is not None and _valid_coloring_data(lists, edges, candidate) else None


def _attack_random_greedy(lists, edges, attack_seed, restarts=16):
    n_vertices = len(lists)
    rng = random.Random(attack_seed)
    steps = 0
    for _ in range(restarts):
        order = list(range(n_vertices))
        rng.shuffle(order)
        candidate = _greedy_candidate(lists, edges, order, rng)
        steps += n_vertices
        if candidate is not None and _valid_coloring_data(lists, edges, candidate):
            return candidate, steps
    return None, steps


def _restart_seed(lists, edges):
    """Public deterministic seed for the reproducible restart attack."""
    payload = json.dumps([lists, edges], separators=(",", ":"))
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:8], "big")


def _attack_obvious_parity(tags, lists, edges):
    # An in-context but wrong ansatz: use each visible base vertex number as its
    # three-bit key and try every XOR translation.  The displayed base key is not
    # the base-vertex numbering.
    raw = []
    for tag in tags:
        value = 0
        for base_vertex, weight in tag:
            if weight & 1:
                value ^= base_vertex % 8
        raw.append(value)
    for offset in range(8):
        candidate = [value ^ offset for value in raw]
        if _valid_coloring_data(lists, edges, candidate):
            return candidate
    return None


def _attack_first_base_key(tags, key_candidates, frequency, lists, edges):
    first = key_candidates[0]
    candidate = _parity_decode(tags, first["base"], first["zero"], frequency)
    return candidate if _valid_coloring_data(lists, edges, candidate) else None


def _candidate_is_panel_easy(tags, key_candidates, frequency, lists, edges):
    """Reject draws solved by the cheap no-tool panel, never to find an answer."""
    if _attack_first_base_key(
        tags, key_candidates, frequency, lists, edges
    ) is not None:
        return True
    if _attack_outlier(lists, edges) is not None:
        return True
    if _attack_label_greedy(lists, edges) is not None:
        return True
    if _attack_degree_greedy(lists, edges) is not None:
        return True
    if _attack_obvious_parity(tags, lists, edges) is not None:
        return True
    if len(lists) >= 200:
        found, _ = _attack_random_greedy(
            lists, edges, _restart_seed(lists, edges), restarts=256
        )
        return found is not None
    return False


def make_instance(n, seed=0, **params):
    """Inverse-generate a theorem-regime plane list-coloring instance.

    The exact coloring is formed before the lists.  Cheap-attack filtering can
    discard a draw, but no search result is ever used as the certificate.
    """
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer subdivision frequency")

    points, base_edges, base_outer = _mesh(n)
    rng = random.Random(seed)
    for attempt in range(10_000):
        color_permutation = rng.choice(_AFFINE_PERMUTATIONS)
        candidate_permutations = [color_permutation]
        while len(candidate_permutations) < 8:
            decoy = rng.choice(_AFFINE_PERMUTATIONS)
            if decoy not in candidate_permutations:
                candidate_permutations.append(decoy)
        rng.shuffle(candidate_permutations)
        if candidate_permutations[0] == color_permutation:
            candidate_permutations[0], candidate_permutations[-1] = (
                candidate_permutations[-1],
                candidate_permutations[0],
            )
        key_candidates = [
            {
                "base": [permutation[color] for color in _BASE_LABELING],
                "zero": permutation[0],
            }
            for permutation in candidate_permutations
        ]
        point_order = list(range(len(points)))
        rng.shuffle(point_order)
        point_to_vertex = {
            point: point_order[index] for index, point in enumerate(points)
        }

        answer = [None] * len(points)
        tags = [None] * len(points)
        for point in points:
            vertex = point_to_vertex[point]
            answer[vertex] = color_permutation[_raw_color(point)]
            tags[vertex] = [[base, weight] for base, weight in point]

        edges = sorted(
            tuple(sorted((point_to_vertex[a], point_to_vertex[b])))
            for a, b in base_edges
        )
        outer = [point_to_vertex[point] for point in base_outer]
        special = {outer[0], outer[n + 1]}

        lists = []
        outer_set = set(outer)
        adj = _adjacency(len(points), edges)
        for vertex in range(len(points)):
            size = 2 if vertex in special else (3 if vertex in outer_set else 5)
            # Neighbor colors are the most credible decoys: they have the same
            # marginal source as planted colors and create local conflicts instead
            # of advertising the witness through unusually isolated list entries.
            decoys = list({answer[w] for w in adj[vertex]})
            rng.shuffle(decoys)
            remaining = [
                color
                for color in _PALETTE
                if color != answer[vertex] and color not in decoys
            ]
            rng.shuffle(remaining)
            decoys.extend(remaining)
            lists.append(sorted([answer[vertex]] + decoys[: size - 1]))

        valid_key_candidates = sum(
            _valid_coloring_data(
                lists,
                edges,
                _parity_decode(tags, key["base"], key["zero"], n),
            )
            for key in key_candidates
        )
        if valid_key_candidates != 1:
            continue
        if n >= 3 and _candidate_is_panel_easy(
            tags, key_candidates, n, lists, edges
        ):
            continue

        return {
            "family": "two 2-lists on a plane graph",
            "subdivision_frequency": n,
            "vertex_count": len(points),
            "edge_count": len(edges),
            "key_candidates": key_candidates,
            "tags": tags,
            "edges": [list(edge) for edge in edges],
            "outer_cycle": outer,
            "special_vertices": sorted(special),
            "lists": lists,
            "answer": answer,
        }
    raise RuntimeError("could not draw an instance defeating the cheap attack panel")


def render(inst):
    key_lines = [
        f"  {index}: zero={key['zero']} | "
        + " ".join(str(c) for c in key["base"])
        for index, key in enumerate(inst["key_candidates"])
    ]
    vertex_lines = []
    for vertex, (tag, choices) in enumerate(zip(inst["tags"], inst["lists"])):
        tag_text = " ".join(f"{base}^{weight}" for base, weight in tag)
        list_text = ",".join(str(color) for color in choices)
        vertex_lines.append(f"  {vertex}: {tag_text} | {list_text}")
    edge_lines = []
    row = []
    for a, b in inst["edges"]:
        row.append(f"{a}-{b}")
        if len(row) == 14:
            edge_lines.append("  " + " ".join(row))
            row = []
    if row:
        edge_lines.append("  " + " ".join(row))

    n_vertices = inst["vertex_count"]
    statement = f"""Find a proper list-coloring of a plane graph.

A list-coloring assigns one integer color to every vertex.  It is proper when
(i) the color of vertex v belongs to its displayed list L(v), and (ii) the two
endpoints of every displayed edge have different colors.

This graph has vertices 0 through {n_vertices - 1}.  Vertex numbers are arbitrary
and answer order is significant.  The outer face is bounded by the simple cycle
shown below, in cyclic order.  The two marked special vertices have lists of
exactly two colors; all other outer-cycle vertices have lists of exactly three;
every vertex not on the outer cycle has a list of exactly five.

Each vertex also has a barycentric tag.  A term b^w assigns positive integer
weight w to base vertex b; weights in one tag sum to the subdivision frequency
{inst['subdivision_frequency']}.  Shared edge points have the same tag from either
incident triangular face.  Tags are part of the plane triangulation data, not
extra permitted colors.  Each auxiliary key candidate assigns three-bit labels
(written as integers 0 through 7) to base vertices 0 through 11 and has a zero
label.  The candidates are construction data, not additional coloring constraints,
and their row order has no mathematical significance.

Key candidates have format "row: zero=z | labels for base vertices 0,1,...,11":
{chr(10).join(key_lines)}

Outer cycle ({len(inst['outer_cycle'])} vertices):
  {' '.join(str(v) for v in inst['outer_cycle'])}
Special two-list vertices:
  {' '.join(str(v) for v in inst['special_vertices'])}

Vertex records have the format "v: barycentric-tag | comma-separated L(v)":
{chr(10).join(vertex_lines)}

Edges ({inst['edge_count']} unordered pairs, with no loops or repeats):
{chr(10).join(edge_lines)}

Return exactly {n_vertices} integers, one for each vertex in increasing vertex
order 0,1,...,{n_vertices - 1}.  Repeated colors are allowed on nonadjacent
vertices.  Use a JSON list; no vertex or list entry may be omitted.

Give your final answer inside <answer></answer> tags, as that JSON list.
Example: <answer>{json.dumps([0] * n_vertices, separators=(',', ':'))}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse the last tagged JSON list, tolerating prose and markdown fences."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    if not blocks:
        return None
    body = blocks[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        answer = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(answer, list):
        return None
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return None
    return answer


def verify(inst, answer):
    """Check any submitted list-coloring exactly; never consult inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    n_vertices = inst["vertex_count"]
    if len(answer) != n_vertices:
        return False, f"wrong length: expected {n_vertices}, got {len(answer)}"
    for vertex, color in enumerate(answer):
        if isinstance(color, bool) or not isinstance(color, int):
            return False, f"non-integer color at vertex {vertex}"
        if color < 0 or color >= len(_PALETTE):
            return False, f"color outside the stated range at vertex {vertex}"
        if color not in inst["lists"][vertex]:
            return False, f"color not in L({vertex})"
    for a, b in inst["edges"]:
        if answer[a] == answer[b]:
            return False, f"edge conflict on {a}-{b}"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from the exact product of displayed vertex lists."""
    return [rng.choice(choices) for choices in inst["lists"]]


def search_space(inst):
    size = 1
    for choices in inst["lists"]:
        size *= len(choices)
    return size


def _count_solutions(inst, node_cap=2_000_000):
    lists = inst["lists"]
    adj = _adjacency(len(lists), inst["edges"])
    colors = [-1] * len(lists)
    nodes = 0

    def visit(remaining):
        nonlocal nodes
        if remaining == 0:
            return 1
        best = None
        best_available = None
        best_key = None
        for vertex in range(len(lists)):
            if colors[vertex] >= 0:
                continue
            used = {colors[w] for w in adj[vertex] if colors[w] >= 0}
            available = [c for c in lists[vertex] if c not in used]
            if not available:
                return 0
            key = (len(available), -len(used), -len(adj[vertex]), vertex)
            if best_key is None or key < best_key:
                best, best_available, best_key = vertex, available, key
        total = 0
        for color in best_available:
            nodes += 1
            if nodes > node_cap:
                raise OverflowError
            colors[best] = color
            total += visit(remaining - 1)
            colors[best] = -1
        return total

    try:
        return visit(len(lists)), nodes
    except OverflowError:
        return None, nodes


def enumerate_all(inst):
    if inst["subdivision_frequency"] > 1:
        return None
    count, _ = _count_solutions(inst)
    return count


def _reference_dpll(inst):
    """MRV/forward-checking CSP reference, with exact operation counters."""
    lists = inst["lists"]
    adj = _adjacency(len(lists), inst["edges"])
    colors = [-1] * len(lists)
    decisions = 0
    list_tests = 0
    backtracks = 0

    def visit(remaining):
        nonlocal decisions, list_tests, backtracks
        if remaining == 0:
            return True
        best = None
        best_available = None
        best_key = None
        for vertex in range(len(lists)):
            if colors[vertex] >= 0:
                continue
            used = {colors[w] for w in adj[vertex] if colors[w] >= 0}
            available = []
            for color in lists[vertex]:
                list_tests += 1
                if color not in used:
                    available.append(color)
            if not available:
                return False
            key = (len(available), -len(used), -len(adj[vertex]), vertex)
            if best_key is None or key < best_key:
                best, best_available, best_key = vertex, available, key
        for color in best_available:
            decisions += 1
            colors[best] = color
            if visit(remaining - 1):
                return True
            colors[best] = -1
            backtracks += 1
        return False

    started = time.perf_counter()
    solved = visit(len(lists))
    elapsed = time.perf_counter() - started
    return (colors if solved else None), {
        "decisions": decisions,
        "list_tests": list_tests,
        "backtracks": backtracks,
        "wall_clock_sec": elapsed,
    }


def canonical_key(inst):
    """Return a relabeling-invariant local-structure fingerprint.

    Exact colored-graph canonization is intentionally not attempted.  The
    sorted vertex and edge signature multisets are invariant under *every*
    vertex relabeling (including base-frame automorphisms), and minimization
    over affine color maps removes the construction's color-name symmetry.
    """
    adjacency = _adjacency(inst["vertex_count"], inst["edges"])
    outer = set(inst["outer_cycle"])
    special = set(inst["special_vertices"])
    best = None
    for perm_tuple in _AFFINE_PERMUTATIONS:
        vertex_signatures = tuple(
            (
                int(vertex in outer),
                int(vertex in special),
                len(adjacency[vertex]),
                tuple(sorted(perm_tuple[color] for color in inst["lists"][vertex])),
            )
            for vertex in range(inst["vertex_count"])
        )
        vertex_counts = tuple(sorted(Counter(vertex_signatures).items()))
        edge_counts = tuple(sorted(Counter(
            tuple(sorted((vertex_signatures[a], vertex_signatures[b])))
            for a, b in inst["edges"]
        ).items()))
        form = (vertex_counts, edge_counts)
        if best is None or form < best:
            best = form
    payload = (inst["subdivision_frequency"], best)
    blob = repr(payload)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _relabel_instance(inst, permutation, reverse_outer=False, rotate=0, color_map=None):
    """Test helper: carry a real isomorphism and its witness."""
    n_vertices = inst["vertex_count"]
    if color_map is None:
        color_map = {c: c for c in _PALETTE}
    tags = [None] * n_vertices
    lists = [None] * n_vertices
    answer = [None] * n_vertices
    for old, new in enumerate(permutation):
        tags[new] = [list(pair) for pair in inst["tags"][old]]
        lists[new] = sorted(color_map[c] for c in inst["lists"][old])
        answer[new] = color_map[inst["answer"][old]]
    edges = [
        list(sorted((permutation[a], permutation[b]))) for a, b in inst["edges"]
    ]
    edges.reverse()
    outer = [permutation[v] for v in inst["outer_cycle"]]
    if reverse_outer:
        outer.reverse()
    if outer:
        rotate %= len(outer)
        outer = outer[rotate:] + outer[:rotate]
    special = sorted(permutation[v] for v in inst["special_vertices"])
    return {
        **{k: v for k, v in inst.items() if k not in {
            "key_candidates", "tags", "lists", "answer", "edges",
            "outer_cycle", "special_vertices"
        }},
        "key_candidates": [
            {
                "base": [color_map[c] for c in key["base"]],
                "zero": color_map[key["zero"]],
            }
            for key in reversed(inst["key_candidates"])
        ],
        "tags": tags,
        "lists": lists,
        "answer": answer,
        "edges": edges,
        "outer_cycle": outer,
        "special_vertices": special,
    }


def _relabel_base_frame(inst, base_permutation):
    """Rename the twelve auxiliary barycentric base symbols consistently."""
    tags = [
        [[base_permutation[base], weight] for base, weight in tag]
        for tag in inst["tags"]
    ]
    tags = [sorted(tag) for tag in tags]
    key_candidates = []
    for key in inst["key_candidates"]:
        relabeled = [None] * 12
        for old_base, new_base in enumerate(base_permutation):
            relabeled[new_base] = key["base"][old_base]
        key_candidates.append({"base": relabeled, "zero": key["zero"]})
    return {
        **inst,
        "tags": tags,
        "key_candidates": key_candidates,
        "answer": list(inst["answer"]),
    }


def escalate(params):
    frequency = int(params.get("n", 1))
    if frequency < 5:
        harder = dict(params)
        harder["n"] = frequency + 1
        return harder
    # Frequency six has 352 answer atoms, so the required native coloring no
    # longer fits the 256-atom output cap.  No honest fixed-length axis remains.
    return "cap_bound"


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _intended_operations(inst):
    # Count exact arithmetic only.  Reading a visibly odd/even small exponent and
    # copying a color into the answer are not arithmetic operations.  At odd
    # frequency, r odd-key labels take r-1 XORs.  At even frequency the affine
    # zero key starts the accumulator, so r labels take r XORs.
    operations = 0
    for tag in inst["tags"]:
        odd = sum(weight & 1 for _, weight in tag)
        operations += (
            odd
            if inst["subdivision_frequency"] % 2 == 0
            else max(0, odd - 1)
        )
    return operations


def _predict_from_key(tag, key, frequency):
    """Return one key prediction and its exact XOR count."""
    value = key["zero"] if frequency % 2 == 0 else 0
    first = frequency % 2 == 1
    operations = 0
    for base_vertex, weight in tag:
        if not (weight & 1):
            continue
        if first:
            value = key["base"][base_vertex]
            first = False
        else:
            value ^= key["base"][base_vertex]
            operations += 1
    return value, operations


def _compact_decode(inst):
    """Select the compatible displayed key by cheap probes, then expand it."""
    frequency = inst["subdivision_frequency"]
    active = list(range(len(inst["key_candidates"])))
    membership_tests = 0
    selection_xors = 0
    # Probe zero-XOR tags first.  At the odd shipping frequency, most mesh
    # vertices inherit one base-key label directly, which separates decoy keys
    # without expanding eight complete colorings.
    order = sorted(
        range(inst["vertex_count"]),
        key=lambda vertex: (
            _predict_from_key(
                inst["tags"][vertex], inst["key_candidates"][0], frequency
            )[1],
            vertex,
        ),
    )
    for vertex in order:
        survivors = []
        for index in active:
            predicted, operations = _predict_from_key(
                inst["tags"][vertex], inst["key_candidates"][index], frequency
            )
            membership_tests += 1
            selection_xors += operations
            if predicted in inst["lists"][vertex]:
                survivors.append(index)
        active = survivors
        if len(active) <= 1:
            break
    if len(active) != 1:
        return None, {
            "membership_tests": membership_tests,
            "selection_xors": selection_xors,
            "final_xors": 0,
        }
    key = inst["key_candidates"][active[0]]
    answer = _parity_decode(inst["tags"], key["base"], key["zero"], frequency)
    return answer, {
        "membership_tests": membership_tests,
        "selection_xors": selection_xors,
        "final_xors": _intended_operations(inst),
    }


def selftest():
    report = {}

    # Fixed base and mesh identities are part of the construction proof.
    base_edges = {
        tuple(sorted((a, b)))
        for face in _BASE_FACES
        for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0]))
    }
    base_ok = (
        len(_BASE_FACES) == 20
        and len(base_edges) == 30
        and all(_BASE_COLORING[a] != _BASE_COLORING[b] for a, b in base_edges)
        and all(_BASE_LABELING[a] != _BASE_LABELING[b] for a, b in base_edges)
        and len(_AFFINE_PERMUTATIONS) == 1344
    )
    planted_attempts = 0
    planted_successes = 0
    decoder_successes = 0
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            planted_attempts += 1
            planted_successes += int(verify(inst, inst["answer"])[0])
            decoded, _ = _compact_decode(inst)
            decoder_successes += int(
                decoded == inst["answer"] and verify(inst, decoded)[0]
            )
            json_roundtrips += int(json.loads(json.dumps(inst["answer"])) == inst["answer"])
    report["G1_planted_verifies"] = {
        "pass": base_ok
        and planted_successes == planted_attempts
        and decoder_successes == planted_attempts
        and json_roundtrips == planted_attempts,
        "base_identity_checked": base_ok,
        "successes": planted_successes,
        "displayed_decoder_successes": decoder_successes,
        "attempts": planted_attempts,
        "json_roundtrips": json_roundtrips,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping_params)
    answer = list(inst["answer"])
    corruptions = {}
    corruptions["empty"] = verify(inst, [])[1]
    corruptions["drop_one"] = verify(inst, answer[:-1])[1]
    outside = list(answer)
    outside[0] = len(_PALETTE)
    corruptions["out_of_range"] = verify(inst, outside)[1]

    duplicate = None
    for a, b in inst["edges"]:
        if answer[a] in inst["lists"][b]:
            duplicate = list(answer)
            duplicate[b] = answer[a]
            break
    corruptions["duplicate_on_edge"] = verify(inst, duplicate)[1]

    swapped = None
    for i in inst["outer_cycle"]:
        for j in inst["outer_cycle"]:
            if i != j and (answer[j] not in inst["lists"][i] or answer[i] not in inst["lists"][j]):
                swapped = list(answer)
                swapped[i], swapped[j] = swapped[j], swapped[i]
                break
        if swapped is not None:
            break
    corruptions["swap_two"] = verify(inst, swapped)[1]
    distinct_reasons = len(set(corruptions.values()))
    report["G2_rejects_corruption"] = {
        "pass": all(reason != "ok" for reason in corruptions.values()) and distinct_reasons == 5,
        "reasons": corruptions,
        "distinct_reasons": distinct_reasons,
    }

    model_reply = (
        "I used the outer-face constraints first.\n\n```json\n"
        f"<answer>{json.dumps(answer)}</answer>\n```\n"
        "The edge check is exact."
    )
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_length": len(parsed) if parsed is not None else None,
    }

    guess_rng = random.Random(20260904)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "candidate_space": search_space(inst),
        "candidate_space_bits": search_space(inst).bit_length() - 1,
        "sampler": "independent uniform choice from each displayed L(v)",
    }

    baseline_started = time.perf_counter()
    baseline_candidate, baseline_steps = _attack_random_greedy(
        inst["lists"], inst["edges"],
        _restart_seed(inst["lists"], inst["edges"]), restarts=256
    )
    baseline_elapsed = time.perf_counter() - baseline_started
    reference_candidate, reference_stats = _reference_dpll(inst)
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count, demo_nodes = _count_solutions(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_probability < 1e-6 and baseline_candidate is None and demo_count is not None,
        "shipping_density_hits": guess_hits,
        "shipping_density_total": guess_total,
        "shipping_density_estimate": guess_probability,
        "strongest_failing_attack_wall_clock_sec": baseline_elapsed,
        "strongest_failing_attack_steps": baseline_steps,
        "strongest_failing_attack_restarts": 256,
        "reference_algorithm_solved": int(
            reference_candidate is not None and verify(inst, reference_candidate)[0]
        ),
        "reference_algorithm_wall_clock_sec": reference_stats["wall_clock_sec"],
        "reference_algorithm_list_tests": reference_stats["list_tests"],
        "reference_algorithm_decisions": reference_stats["decisions"],
        "demo_exact_solution_count": demo_count,
        "demo_enumeration_nodes": demo_nodes,
    }

    attack_names = (
        "outlier_rarest_list_color",
        "greedy_label_order",
        "greedy_high_degree_first",
        "random_greedy_256_restarts",
        "first_displayed_base_key",
        "obvious_barycentric_vertex_key_ansatz",
    )
    attack_successes = {name: 0 for name in attack_names}
    reference_solves = 0
    reference_decisions = 0
    reference_tests = 0
    reference_backtracks = 0
    reference_seconds = 0.0
    decoder_solves = 0
    decoder_membership_tests = 0
    decoder_selection_xors = 0
    panel_attempts = 8
    for seed in range(1000, 1000 + panel_attempts):
        panel_inst = make_instance(seed=seed, **shipping_params)
        lists, edges = panel_inst["lists"], panel_inst["edges"]
        attack_successes[attack_names[0]] += int(_attack_outlier(lists, edges) is not None)
        attack_successes[attack_names[1]] += int(_attack_label_greedy(lists, edges) is not None)
        attack_successes[attack_names[2]] += int(_attack_degree_greedy(lists, edges) is not None)
        random_found, _ = _attack_random_greedy(
            lists, edges, _restart_seed(lists, edges), restarts=256
        )
        attack_successes[attack_names[3]] += int(random_found is not None)
        attack_successes[attack_names[4]] += int(
            _attack_first_base_key(
                panel_inst["tags"], panel_inst["key_candidates"],
                panel_inst["subdivision_frequency"], lists, edges,
            ) is not None
        )
        attack_successes[attack_names[5]] += int(
            _attack_obvious_parity(panel_inst["tags"], lists, edges) is not None
        )
        reference_answer, stats = _reference_dpll(panel_inst)
        reference_solves += int(reference_answer is not None and verify(panel_inst, reference_answer)[0])
        reference_decisions += stats["decisions"]
        reference_tests += stats["list_tests"]
        reference_backtracks += stats["backtracks"]
        reference_seconds += stats["wall_clock_sec"]
        decoded, decoder_stats = _compact_decode(panel_inst)
        decoder_solves += int(verify(panel_inst, decoded)[0])
        decoder_membership_tests += decoder_stats["membership_tests"]
        decoder_selection_xors += decoder_stats["selection_xors"]

    attacks = {
        name: {"successes": attack_successes[name], "attempts": panel_attempts}
        for name in attack_names
    }
    all_failed = all(result["successes"] == 0 for result in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed
        and reference_solves == panel_attempts
        and decoder_solves == panel_attempts,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "MRV forward-checking executable proxy for the proof-guided construction",
            "complexity": (
                "O(5^N) worst case for this implementation; O(N^2) on the measured "
                "zero-backtrack scan, matching the natural Thomassen-style bound"
            ),
            "wall_clock_sec": reference_seconds / panel_attempts,
            "operations": round(reference_tests / panel_attempts),
            "decisions": round(reference_decisions / panel_attempts),
            "backtracks": round(reference_backtracks / panel_attempts),
            "solves": f"{reference_solves}/{panel_attempts}, as expected",
        },
        "efficient_distribution_decoder": {
            "name": "compatible-key selection plus barycentric-parity transport",
            "complexity": "O(N), since every tag has at most three terms",
            "operations": _intended_operations(inst)
            + round(decoder_selection_xors / panel_attempts),
            "membership_tests": round(decoder_membership_tests / panel_attempts),
            "selection_xors": round(decoder_selection_xors / panel_attempts),
            "solves": f"{decoder_solves}/{panel_attempts}, as expected",
        },
    }

    doubled = make_instance(n=shipping_params["n"] * 2, seed=424242)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["vertex_count"] > inst["vertex_count"] * 2,
        "shipping_vertices": inst["vertex_count"],
        "doubled_vertices": doubled["vertex_count"],
        "shipping_space_bits": search_space(inst).bit_length() - 1,
        "doubled_space_bits": search_space(doubled).bit_length() - 1,
    }

    invariant_checks = 0
    carried_witness_checks = 0
    distinct_keys = set()
    for seed in range(20):
        original = make_instance(seed=20_000 + seed, **shipping_params)
        original_key = canonical_key(original)
        distinct_keys.add(original_key)
        transform_rng = random.Random(90_000 + seed)
        permutation = list(range(original["vertex_count"]))
        transform_rng.shuffle(permutation)
        color_map = dict(enumerate(transform_rng.choice(_AFFINE_PERMUTATIONS)))
        for reverse, rotate, cmap in (
            (False, 0, None),
            (True, seed + 1, None),
            (False, seed * 2 + 1, color_map),
            (True, seed * 3 + 2, color_map),
        ):
            transformed = _relabel_instance(
                original, permutation, reverse_outer=reverse, rotate=rotate, color_map=cmap
            )
            invariant_checks += int(canonical_key(transformed) == original_key)
            carried_witness_checks += int(verify(transformed, transformed["answer"])[0])
        base_permutation = list(range(12))
        transform_rng.shuffle(base_permutation)
        reframed = _relabel_base_frame(original, base_permutation)
        invariant_checks += int(canonical_key(reframed) == original_key)
        carried_witness_checks += int(verify(reframed, reframed["answer"])[0])
    total_invariance = 20 * 5
    report["G8_canonical_key"] = {
        "pass": invariant_checks == total_invariance
        and carried_witness_checks == total_invariance
        and len(distinct_keys) == 20,
        "invariant_relabellings": invariant_checks,
        "invariance_attempts": total_invariance,
        "carried_witnesses_valid": carried_witness_checks,
        "carried_witness_attempts": total_invariance,
        "distinct_unrelated_keys": len(distinct_keys),
        "distinctness_attempts": 20,
        "symmetries_tested": [
            "arbitrary vertex renumbering",
            "edge-list reversal",
            "key-candidate row reversal",
            "outer-cycle rotation and reversal",
            "global affine color permutation",
            "auxiliary barycentric base-frame renaming",
            "compositions of the above",
        ],
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    _, compact_stats = _compact_decode(inst)
    intended_ops = compact_stats["selection_xors"] + compact_stats["final_xors"]
    hinted = G9_ORACLE_RESULTS["hinted"]
    placebo = G9_ORACLE_RESULTS["placebo"]
    hinted_still_hardened = G9_ORACLE_RESULTS["hinted_verdict"] == "hardened"
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    arms = {
        arm: dict(G9_ORACLE_RESULTS[arm]) for arm in ("bare", "hinted", "placebo")
    }
    report["G9_no_tool_suitability"] = {
        "pass": hinted_still_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted["solved"] / max(1, hinted["attempts"])
            - placebo["solved"] / max(1, placebo["attempts"])
        ),
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "intended_route_membership_tests": compact_stats["membership_tests"],
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping_params)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    report["disposition"] = (
        "cap_bound: retained and parked, not rejected and not shipped"
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
