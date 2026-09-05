#!/usr/bin/env python3
"""Verified octahedral-packing instances from arXiv:2506.10471.

The paper recursively inserts octahedral triangulations into triangular faces.
We sample the insertion tree first, retain its vertex-disjoint core octahedra,
and optionally add face-stacked degree-four distractor centers with degree-three
satellites.  Thus the answer is carried through construction; generation never
searches the graph.
"""

from __future__ import annotations

import copy
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
except ImportError:                 # not present: stay standard-library-only
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "plane triangulation given by its graph",
        "vertex-disjoint induced octahedron subgraphs",
    ],
    "verification_operations": [
        "set disjointness",
        "integer range checking",
        "exact induced-edge lookup",
        "induced degree comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Recognize the tree of overlapping octahedra: leaf core blocks have "
        "private vertices, whereas every interface octahedron overlaps its two "
        "neighboring core blocks."
    ),
    "hardness_basis": (
        "Track B: enumerate induced K_{2,2,2} subgraphs through nonedge common "
        "neighborhoods in O(N^2 Delta^4), then run Algorithm X on the generated "
        "overlap-tree exact cover; at shipping n=40 this took 146,204 counted "
        "operations and 0.038 seconds, while the compact leaf-forcing route uses "
        "79 block eliminations."
    ),
    "max_answer_tokens": 251,
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


# n is the number of planted, pairwise-disjoint octahedron blocks.  Each decoy
# unit is a degree-four face-stacking center plus its degree-three satellite.
# Centers pass the freely visible degree test but lie in no octahedron, enlarging
# the honest candidate haystack without lengthening the answer.
DIFFICULTY = {
    "demo": {"n": 2, "decoys": 0},
    "easy": {"n": 30, "decoys": 60},
    "medium": {"n": 35, "decoys": 100},
    "hard": {"n": 40, "decoys": 144},
}
SHIPPING_DIFFICULTY = "hard"


STRUCTURAL_HINT = (
    "The overlap graph of the induced octahedra has leaf core blocks containing "
    "vertices that belong to no competing octahedron."
)
PLACEBO_HINT = (
    "The edge list is undirected, so careful bookkeeping of repeated endpoints "
    "and block boundaries helps avoid clerical mistakes."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "An unordered JSON list of exactly b unordered six-element lists of "
        "distinct vertex labels in 0..N-1; the b blocks are pairwise disjoint."
    ),
    "bounds": {
        "blocks": "inst['target_blocks']",
        "vertices_per_block": 6,
        "eligible_vertices": "all graph vertices of total degree at least 4",
        "vertex_min": 0,
        "vertex_max": "inst['vertex_count'] - 1",
        "repetition": "forbidden globally",
        "max_atomic_elements_at_shipping": 240,
    },
}


NOTES = (
    "Section 2 fixes the paper's native objects: finite simple plane graphs, "
    "induced subgraphs, and the octahedron used throughout the constructions. "
    "Section 8, especially the construction before Observation 16 and "
    "Observation 17, gives the recursive face insertion and the vertex-disjoint "
    "octahedral decomposition. The generator samples a finite pruning of that "
    "insertion tree and carries the core blocks through a vertex relabelling. "
    "Each face-stacked distractor consists of a degree-four center and a "
    "degree-three satellite; this preserves planarity and triangulation and "
    "changes no planted induced octahedron. The certificate is not "
    "obtained by running the reference solver. The paper supplies no hardness "
    "theorem for finding the decomposition. Accordingly this is Track B: a "
    "common-neighborhood enumerator followed by Algorithm X solves every "
    "instance. The compact route is the paper's recursive decomposition: "
    "interface octahedra overlap two core blocks and leaf core blocks expose "
    "private vertices. Degree grouping, first-fit packing, maximum-degree "
    "packing, and randomized no-backtracking packing are tested as attacks; "
    "the exact minimum-column search is reported separately as the successful "
    "reference algorithm."
)


# Filled from script-owned hardening runs after the ladder settles.  These arms
# are diagnostic; G9(c)'s answer/operation caps are the only gating part.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unavailable_http_403_key_limit",
}


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"^\s*```(?:json|text)?\s*(.*?)\s*```\s*$", re.I | re.S)
_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8
_ENUMERATION_NODE_CAP = 200_000


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate(n, decoys):
    if not _is_int(n) or not 1 <= n <= 256:
        raise ValueError("n must be an integer in 1..256")
    if not _is_int(decoys) or decoys < 0:
        raise ValueError("decoys must be a nonnegative integer")
    if decoys > 12 * n - 4:
        raise ValueError("decoys cannot exceed the number of original faces")


def _edge(u, v):
    return (u, v) if u < v else (v, u)


def _bits_from_edges(vertex_count, edges):
    bits = [0] * vertex_count
    for u, v in edges:
        bits[u] |= 1 << v
        bits[v] |= 1 << u
    return bits


def _eligible_from_bits(bits):
    return [v for v, neighbors in enumerate(bits) if neighbors.bit_count() >= 4]


def _octahedron_faces(vertices):
    """The eight facial triangles of K_{2,2,2} in the paper's labelling."""
    a, b, c, d, e, f = vertices
    return [
        (a, b, c), (a, b, f), (a, e, c), (a, e, f),
        (d, b, c), (d, b, f), (d, e, c), (d, e, f),
    ]


def _child_slots(vertices):
    """The three inner faces af e, fb d, and ed c used in Section 8."""
    a, b, c, d, e, f = vertices
    return [(a, f, e), (f, b, d), (e, d, c)]


def _add_core(edges, blocks):
    start = 6 * len(blocks)
    vertices = list(range(start, start + 6))
    blocks.append(vertices)
    opposite = {_edge(vertices[0], vertices[3]),
                _edge(vertices[1], vertices[4]),
                _edge(vertices[2], vertices[5])}
    for u, v in itertools.combinations(vertices, 2):
        if _edge(u, v) not in opposite:
            edges.add(_edge(u, v))
    return vertices


def _interface_faces(parent_face, child_outer):
    """Six annular faces after two opposite triangles form an octahedron."""
    result = []
    for bits in itertools.product((0, 1), repeat=3):
        if bits in ((0, 0, 0), (1, 1, 1)):
            continue
        result.append(tuple(
            child_outer[i] if bits[i] else parent_face[i] for i in range(3)
        ))
    return result


def make_instance(n, seed=0, decoys=0, **params):
    """Construct a pruned Section-8 insertion tree and retain its core blocks."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    _validate(n, decoys)
    rng = random.Random(seed)

    edges = set()
    blocks = []
    root = _add_core(edges, blocks)
    faces = {tuple(sorted(face)) for face in _octahedron_faces(root)}

    # The root of G'_k permits all four alternating faces; every descendant is
    # a G_j and permits the three inner faces.  Random pruning gives many
    # non-isomorphic members while staying inside the paper's insertion scheme.
    available = [(0, tuple(root[:3]))]
    available.extend((0, face) for face in _child_slots(root))
    for _ in range(n - 1):
        slot_index = rng.randrange(len(available))
        _parent_index, parent_face = available.pop(slot_index)
        child = _add_core(edges, blocks)
        child_index = len(blocks) - 1
        child_outer = tuple(child[:3])

        # Two opposite triangles, with matched nonedges, induce an octahedron.
        for x, opposite_child in zip(parent_face, child_outer):
            for y in child_outer:
                if y != opposite_child:
                    edges.add(_edge(x, y))

        parent_key = tuple(sorted(parent_face))
        if parent_key not in faces:
            raise AssertionError("construction attempted to fill a non-face")
        faces.remove(parent_key)
        for face in _octahedron_faces(child):
            if set(face) != set(child_outer):
                faces.add(tuple(sorted(face)))
        for face in _interface_faces(parent_face, child_outer):
            faces.add(tuple(sorted(face)))
        available.extend((child_index, face) for face in _child_slots(child))

    # Stack twice into each chosen original face.  The center x ends with total
    # degree four, so it survives the free degree filter.  Its fourth neighbor y
    # has total degree three, so x cannot lie in an induced octahedron (an
    # octahedron containing x would have to contain all four of x's neighbors).
    original_faces = sorted(faces)
    rng.shuffle(original_faces)
    for decoy_index, face in enumerate(original_faces[:decoys]):
        center = 6 * n + 2 * decoy_index
        satellite = center + 1
        faces.remove(tuple(sorted(face)))
        for u in face:
            edges.add(_edge(center, u))
        center_faces = []
        for u, v in itertools.combinations(face, 2):
            new_face = tuple(sorted((center, u, v)))
            center_faces.append(new_face)
            faces.add(new_face)
        satellite_face = rng.choice(center_faces)
        faces.remove(satellite_face)
        for u in satellite_face:
            edges.add(_edge(satellite, u))
        for u, v in itertools.combinations(satellite_face, 2):
            faces.add(tuple(sorted((satellite, u, v))))

    vertex_count = 6 * n + 2 * decoys
    if vertex_count and max(max(edge) for edge in edges) != vertex_count - 1:
        raise AssertionError("non-contiguous construction labels")
    if len(edges) != 3 * vertex_count - 6:
        raise AssertionError("constructed graph is not a triangulation")

    # A final uniformly random relabelling destroys construction-order leakage.
    permutation = list(range(vertex_count))
    rng.shuffle(permutation)
    public_edges = sorted(_edge(permutation[u], permutation[v]) for u, v in edges)
    answer = sorted(
        (sorted(permutation[v] for v in block) for block in blocks),
        key=lambda block: tuple(block),
    )
    adjacency_bits = _bits_from_edges(vertex_count, public_edges)
    return {
        "vertex_count": vertex_count,
        "target_blocks": n,
        "edges": [list(edge) for edge in public_edges],
        # JSON-native verifier acceleration, exactly derivable from edges.
        "adjacency_bits": adjacency_bits,
        "eligible_vertices": _eligible_from_bits(adjacency_bits),
        "answer": answer,
    }


def render(inst):
    """Render the entire induced-octahedron packing task."""
    n_vertices = inst["vertex_count"]
    target = inst["target_blocks"]
    edge_text = " ".join(f"{u}-{v}" for u, v in inst["edges"])
    statement = f"""Induced octahedron packing in a plane triangulation

The graph is finite, simple, and undirected.  Its vertices are the integers
0 through {n_vertices - 1}.  An edge u-v is the same as v-u, and the complete
edge list is given below.  The graph is guaranteed to be a planar graph in
which every face is a triangle; no drawing or embedding is needed.

An induced octahedron is a set of exactly six distinct vertices whose induced
subgraph is K_(2,2,2).  Equivalently, among those six vertices every vertex has
exactly four neighbors (so exactly 12 of their 15 unordered pairs are edges).

Find exactly {target} induced octahedra that are pairwise vertex-disjoint.
Order does not matter, either among the {target} blocks or within a block.
No vertex may be repeated within or between blocks; vertices not listed in the
answer are allowed.

N = {n_vertices}
b = {target}
Edges ({len(inst['edges'])}):
{edge_text}

Give your final answer inside <answer></answer> tags as a JSON array of exactly
{target} arrays, each containing exactly six integer vertex labels.
Example format: <answer>[[0,1,2,3,4,5],[6,7,8,9,10,11]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Extract the first JSON array in the answer tags (or a bare response)."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    body = match.group(1).strip() if match else text.strip()
    fence = _FENCE_RE.match(body)
    if fence:
        body = fence.group(1).strip()
    decoder = json.JSONDecoder()
    starts = [0] if body.startswith("[") else []
    starts.extend(i for i, char in enumerate(body) if char == "[" and i != 0)
    for start in starts:
        try:
            value, _ = decoder.raw_decode(body[start:])
        except (ValueError, TypeError):
            continue
        if isinstance(value, list):
            return value
    return None


def _edge_set(inst):
    return {_edge(u, v) for u, v in inst["edges"]}


def _is_octahedron(block, edges):
    if len(block) != 6 or len(set(block)) != 6:
        return False
    return all(
        sum(_edge(u, v) in edges for v in block if v != u) == 4
        for u in block
    )


def _is_octahedron_bits(block, adjacency_bits):
    if len(block) != 6 or len(set(block)) != 6:
        return False
    mask = sum(1 << v for v in block)
    return all((adjacency_bits[u] & mask).bit_count() == 4 for u in block)


def verify(inst, answer):
    """Verify only the submitted packing; never consult inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer_not_list"
    if not answer:
        return False, "answer_empty"
    if len(answer) != inst["target_blocks"]:
        return False, "block_count"
    seen = set()
    normalized = []
    for block in answer:
        if not isinstance(block, list):
            return False, "block_not_list"
        if len(block) != 6:
            return False, "block_size"
        if any(not _is_int(v) for v in block):
            return False, "vertex_not_integer"
        if any(v < 0 or v >= inst["vertex_count"] for v in block):
            return False, "vertex_range"
        if len(set(block)) != 6 or any(v in seen for v in block):
            return False, "duplicate_vertex"
        seen.update(block)
        normalized.append(tuple(block))
    adjacency_bits = inst.get("adjacency_bits")
    if not isinstance(adjacency_bits, list) or len(adjacency_bits) != inst["vertex_count"]:
        adjacency_bits = _bits_from_edges(inst["vertex_count"], inst["edges"])
    if any(not _is_octahedron_bits(block, adjacency_bits) for block in normalized):
        return False, "not_induced_octahedron"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly after the freely-deducible total-degree filter."""
    count = 6 * inst["target_blocks"]
    eligible = inst.get("eligible_vertices")
    if not isinstance(eligible, list):
        eligible = _eligible_from_bits(inst["adjacency_bits"])
    sequence = rng.sample(eligible, count)
    blocks = [sorted(sequence[i:i + 6]) for i in range(0, count, 6)]
    rng.shuffle(blocks)
    return blocks


def search_space(inst):
    """Number of unordered b-packings of unordered six-sets from N vertices."""
    eligible = inst.get("eligible_vertices")
    total = (len(eligible) if isinstance(eligible, list)
             else len(_eligible_from_bits(inst["adjacency_bits"])))
    blocks = inst["target_blocks"]
    used = 6 * blocks
    if used > total:
        return 0
    return math.factorial(total) // (
        math.factorial(total - used)
        * (math.factorial(6) ** blocks)
        * math.factorial(blocks)
    )


def _adjacency(inst):
    adjacency = [set() for _ in range(inst["vertex_count"])]
    for u, v in inst["edges"]:
        adjacency[u].add(v)
        adjacency[v].add(u)
    return adjacency


def _candidate_octahedra(inst, stats=None):
    """Enumerate induced K_(2,2,2)s via an opposite nonedge pair."""
    adjacency = _adjacency(inst)
    found = set()
    pair_checks = 0
    intersections = 0
    four_sets = 0
    edges = _edge_set(inst)
    eligible = [v for v, neighbors in enumerate(adjacency) if len(neighbors) >= 4]
    for position, u in enumerate(eligible):
        for v in eligible[position + 1:]:
            pair_checks += 1
            if v in adjacency[u]:
                continue
            intersections += 1
            common = sorted(
                w for w in adjacency[u].intersection(adjacency[v])
                if len(adjacency[w]) >= 4
            )
            for rest in itertools.combinations(common, 4):
                four_sets += 1
                candidate = tuple(sorted((u, v) + rest))
                if candidate not in found and _is_octahedron(candidate, edges):
                    found.add(candidate)
    if stats is not None:
        stats.update({
            "pair_checks": pair_checks,
            "common_neighborhood_intersections": intersections,
            "candidate_4sets_tested": four_sets,
            "octahedra_found": len(found),
        })
    return sorted(found)


def _algorithm_x(inst, candidates=None, stats=None):
    """Minimum-column exact cover of all vertices occurring in candidates."""
    if candidates is None:
        candidates = _candidate_octahedra(inst, stats)
    universe = set().union(*(set(block) for block in candidates)) if candidates else set()
    target = inst["target_blocks"]
    if len(universe) != 6 * target:
        return None
    by_vertex = {v: [] for v in universe}
    for index, block in enumerate(candidates):
        for v in block:
            by_vertex[v].append(index)
    nodes = 0
    backtracks = 0

    def visit(uncovered, chosen):
        nonlocal nodes, backtracks
        nodes += 1
        if not uncovered:
            return list(chosen) if len(chosen) == target else None
        if len(chosen) >= target:
            backtracks += 1
            return None
        options_by_vertex = []
        for vertex in uncovered:
            options = [
                index for index in by_vertex[vertex]
                if set(candidates[index]).issubset(uncovered)
            ]
            if not options:
                backtracks += 1
                return None
            options_by_vertex.append((len(options), vertex, options))
        _, _, options = min(options_by_vertex)
        for index in options:
            block_set = set(candidates[index])
            result = visit(uncovered - block_set, chosen + [index])
            if result is not None:
                return result
        backtracks += 1
        return None

    solution_indices = visit(frozenset(universe), [])
    if stats is not None:
        stats.update({"search_nodes": nodes, "backtracks": backtracks})
    if solution_indices is None:
        return None
    return sorted((list(candidates[i]) for i in solution_indices), key=tuple)


def enumerate_all(inst):
    """Count valid packings by capped exact-cover/backtracking enumeration."""
    candidates = _candidate_octahedra(inst)
    target = inst["target_blocks"]
    universe = set().union(*(set(block) for block in candidates)) if candidates else set()
    nodes = 0

    # In the generated family exactly 6b vertices occur in any candidate, so a
    # b-packing is precisely an exact cover.  The fallback below also handles a
    # small non-generated instance whose candidate universe is larger.
    if len(universe) == 6 * target:
        by_vertex = {v: [] for v in universe}
        for index, block in enumerate(candidates):
            for v in block:
                by_vertex[v].append(index)

        def exact_visit(uncovered, selected):
            nonlocal nodes
            nodes += 1
            if nodes > _ENUMERATION_NODE_CAP:
                raise OverflowError
            if not uncovered:
                return int(selected == target)
            if selected >= target:
                return 0
            columns = []
            for vertex in uncovered:
                options = [
                    index for index in by_vertex[vertex]
                    if set(candidates[index]).issubset(uncovered)
                ]
                if not options:
                    return 0
                columns.append((len(options), vertex, options))
            _, _, options = min(columns)
            return sum(exact_visit(
                uncovered - set(candidates[index]), selected + 1
            ) for index in options)

        try:
            return exact_visit(frozenset(universe), 0)
        except OverflowError:
            return None

    if len(candidates) > 20:
        return None
    count = 0

    def packing_visit(start, selected, used):
        nonlocal count, nodes
        nodes += 1
        if nodes > _ENUMERATION_NODE_CAP:
            raise OverflowError
        if selected == target:
            count += 1
            return
        needed = target - selected
        if len(candidates) - start < needed:
            return
        for i in range(start, len(candidates)):
            block = set(candidates[i])
            if not block.intersection(used):
                packing_visit(i + 1, selected + 1, used | block)

    try:
        packing_visit(0, 0, set())
    except OverflowError:
        return None
    return count


def _tree_code_from_solution(inst, solution):
    """AHU code of the quotient tree of the disjoint core octahedra."""
    blocks = [set(block) for block in solution]
    adjacency = [set() for _ in blocks]
    edges = _edge_set(inst)
    for i in range(len(blocks)):
        for j in range(i + 1, len(blocks)):
            if any(_edge(u, v) in edges for u in blocks[i] for v in blocks[j]):
                adjacency[i].add(j)
                adjacency[j].add(i)

    if len(blocks) == 1:
        return "()"
    degrees = [len(x) for x in adjacency]
    leaves = [i for i, degree in enumerate(degrees) if degree <= 1]
    remaining = len(blocks)
    while remaining > 2:
        next_leaves = []
        remaining -= len(leaves)
        for leaf in leaves:
            degrees[leaf] = 0
            for neighbor in adjacency[leaf]:
                if degrees[neighbor] > 0:
                    degrees[neighbor] -= 1
                    if degrees[neighbor] == 1:
                        next_leaves.append(neighbor)
        leaves = next_leaves
    centers = leaves

    def rooted(vertex, parent):
        children = sorted(rooted(x, vertex) for x in adjacency[vertex] if x != parent)
        return "(" + "".join(children) + ")"

    return min(rooted(center, -1) for center in centers)


def _wl_descriptor(inst):
    """A strong cheap invariant for the face-stacking decorations."""
    adjacency = _adjacency(inst)
    colors = [len(neighbors) for neighbors in adjacency]
    for _ in range(inst["vertex_count"]):
        signatures = [
            (colors[v], tuple(sorted(colors[u] for u in adjacency[v])))
            for v in range(inst["vertex_count"])
        ]
        palette = {signature: i for i, signature in enumerate(sorted(set(signatures)))}
        new_colors = [palette[signature] for signature in signatures]
        if new_colors == colors:
            break
        colors = new_colors
    vertex_histogram = sorted(Counter(colors).items())
    edge_histogram = sorted(Counter(
        tuple(sorted((colors[u], colors[v]))) for u, v in inst["edges"]
    ).items())
    return [vertex_histogram, edge_histogram]


def canonical_key(inst):
    """Relabelling-invariant quotient-tree plus color-refinement fingerprint."""
    solution = _algorithm_x(inst)
    if solution is None:
        raise ValueError("instance has no recoverable octahedral exact cover")
    descriptor = {
        "tree": _tree_code_from_solution(inst, solution),
        "wl": _wl_descriptor(inst),
    }
    payload = json.dumps(descriptor, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def escalate(params):
    """First add fixed-answer decoys; only then approach the 256-atom cap."""
    current = dict(params)
    n = current.get("n")
    decoys = current.get("decoys", 0)
    if not _is_int(n) or not _is_int(decoys):
        return None
    face_cap = 12 * n - 4
    if decoys < face_cap:
        current["decoys"] = min(face_cap, decoys + max(n, decoys // 2, 1))
        return current
    if n < 42:
        current["n"] = min(42, n + 2)
        current["decoys"] = min(current["decoys"], 12 * current["n"] - 4)
        return current
    return "cap_bound"


def _degree_grouping(inst):
    adjacency = _adjacency(inst)
    needed = 6 * inst["target_blocks"]
    order = sorted(range(inst["vertex_count"]),
                   key=lambda v: (-len(adjacency[v]), v))[:needed]
    return [sorted(order[i:i + 6]) for i in range(0, needed, 6)]


def _greedy_candidates(inst, candidates, mode, rng=None):
    adjacency = _adjacency(inst)
    used = set()
    chosen = []
    while len(chosen) < inst["target_blocks"]:
        available = [block for block in candidates if not used.intersection(block)]
        if not available:
            return None
        if mode == "first":
            block = min(available)
        elif mode == "degree":
            block = max(available, key=lambda candidate: (
                sum(len(adjacency[v]) for v in candidate),
                tuple(-v for v in candidate),
            ))
        elif mode == "random":
            block = rng.choice(available)
        else:
            raise ValueError("unknown greedy mode")
        chosen.append(list(block))
        used.update(block)
    return chosen


def _attack_results(inst, seed):
    candidates = _candidate_octahedra(inst)
    attacks = {}
    candidates_to_try = {
        "outlier_degree_grouping": _degree_grouping(inst),
        "greedy_first_fit": _greedy_candidates(inst, candidates, "first"),
        "greedy_max_total_degree": _greedy_candidates(inst, candidates, "degree"),
    }
    for name, answer in candidates_to_try.items():
        attacks[name] = bool(answer is not None and verify(inst, answer)[0])

    rng = random.Random(91_000 + seed)
    random_success = False
    for _ in range(256):
        answer = _greedy_candidates(inst, candidates, "random", rng)
        if answer is not None and verify(inst, answer)[0]:
            random_success = True
            break
    attacks["random_restart_256"] = random_success
    return attacks


def _relabel(inst, rng):
    transformed = copy.deepcopy(inst)
    permutation = list(range(inst["vertex_count"]))
    rng.shuffle(permutation)
    transformed["edges"] = [
        list(_edge(permutation[u], permutation[v])) for u, v in inst["edges"]
    ]
    rng.shuffle(transformed["edges"])
    transformed["adjacency_bits"] = _bits_from_edges(
        inst["vertex_count"], transformed["edges"]
    )
    transformed["eligible_vertices"] = _eligible_from_bits(
        transformed["adjacency_bits"]
    )
    transformed["answer"] = [
        [permutation[v] for v in block] for block in inst["answer"]
    ]
    for block in transformed["answer"]:
        rng.shuffle(block)
    rng.shuffle(transformed["answer"])
    return transformed


def _answer_atoms(answer):
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest():
    """Run G1--G9 and return all measured evidence as a JSON-native dict."""
    report = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1: every construction route and public preset verifies.
    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer_not_json_native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=20_260_905, **shipping_params)

    # G2: five semantically different corruptions must reach five reasons.
    corruptions = {}
    dropped = copy.deepcopy(shipping["answer"])
    dropped[0] = dropped[0][:-1]
    corruptions["drop_element"] = dropped

    swapped = None
    for i in range(len(shipping["answer"])):
        for j in range(i + 1, len(shipping["answer"])):
            trial = copy.deepcopy(shipping["answer"])
            trial[i][0], trial[j][0] = trial[j][0], trial[i][0]
            if verify(shipping, trial)[1] == "not_induced_octahedron":
                swapped = trial
                break
        if swapped is not None:
            break
    if swapped is None:
        swapped = copy.deepcopy(shipping["answer"])
        swapped[0][0], swapped[1][0] = swapped[1][0], swapped[0][0]
    corruptions["swap_between_blocks"] = swapped

    duplicated = copy.deepcopy(shipping["answer"])
    duplicated[0][1] = duplicated[0][0]
    corruptions["duplicate"] = duplicated
    corruptions["empty"] = []
    out_of_range = copy.deepcopy(shipping["answer"])
    out_of_range[0][0] = shipping["vertex_count"]
    corruptions["out_of_range"] = out_of_range
    reasons = {name: verify(shipping, answer)[1]
               for name, answer in corruptions.items()}
    report["G2_rejects_corruption"] = {
        "pass": all(reason != "ok" for reason in reasons.values())
                and len(set(reasons.values())) == len(reasons),
        "reasons": reasons,
    }

    # G3: realistic prose and a markdown fence around the tagged JSON.
    response = (
        "I used the recursive decomposition.\n\n<answer>\n```json\n"
        + json.dumps(shipping["answer"])
        + "\n```\n</answer>\n"
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and verify(shipping, parsed)[0],
        "parsed_matches": parsed == shipping["answer"],
    }

    # G4/G5 density at the actual shipping preset.
    guess_rng = random.Random(44_044)
    hits = 0
    density_start = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    density_wall = time.perf_counter() - density_start
    probability = hits / _G4_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": _G4_SAMPLES,
        "observed_probability": probability,
        "candidate_space": search_space(shipping),
        "sampler": "uniform disjoint unordered six-set packings",
        "eligible_vertices_after_degree_filter": len(shipping["eligible_vertices"]),
        "wall_clock_sec": round(density_wall, 6),
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    shipping_count = enumerate_all(shipping)
    reference_stats = {}
    reference_start = time.perf_counter()
    reference_answer = _algorithm_x(shipping, stats=reference_stats)
    reference_wall = time.perf_counter() - reference_start
    reference_ok = bool(reference_answer and verify(shipping, reference_answer)[0])
    reference_operations = sum(reference_stats.get(key, 0) for key in (
        "pair_checks", "common_neighborhood_intersections",
        "candidate_4sets_tested", "search_nodes"
    ))

    attack_clock_start = time.perf_counter()
    strongest_attack = _attack_results(shipping, 20_260_905)["random_restart_256"]
    attack_wall = time.perf_counter() - attack_clock_start
    report["G5_density_and_baseline"] = {
        "pass": hits == 0 and demo_count is not None
                and shipping_count is not None and reference_ok,
        "shipping_density_hits": hits,
        "shipping_density_samples": _G4_SAMPLES,
        "shipping_density_fraction": probability,
        "shipping_exact_valid_answer_count": shipping_count,
        "shipping_exact_density_log10": (
            math.log10(shipping_count) - math.log10(search_space(shipping))
            if shipping_count else None
        ),
        "demo_exact_valid_answer_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "reference_wall_clock_sec": round(reference_wall, 6),
        "reference_operations": reference_operations,
        "reference_search_nodes": reference_stats.get("search_nodes", 0),
        "strongest_failing_attack_wall_clock_sec": round(attack_wall, 6),
        "strongest_failing_attack_iterations": 256,
        "strongest_failing_attack_succeeded": strongest_attack,
    }

    # G6: attacks fail; the successful exact algorithm is deliberately separate.
    attack_names = (
        "outlier_degree_grouping",
        "greedy_first_fit",
        "greedy_max_total_degree",
        "random_restart_256",
    )
    attack_totals = {name: 0 for name in attack_names}
    panel_start = time.perf_counter()
    for seed in range(_ATTACK_SEEDS):
        inst = make_instance(seed=71_000 + seed, **shipping_params)
        for name, succeeded in _attack_results(inst, seed).items():
            attack_totals[name] += int(succeeded)
    panel_wall = time.perf_counter() - panel_start
    attacks = {
        name: {"successes": attack_totals[name], "attempts": _ATTACK_SEEDS}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in attacks.values())
                and reference_ok,
        "attacks": attacks,
        "panel_wall_clock_sec": round(panel_wall, 6),
        "reference_algorithm": {
            "name": "nonedge common-neighborhood enumeration plus Algorithm X",
            "complexity": (
                "O(N^2 Delta^4) enumeration and forced linear search on the "
                "generated overlap-tree exact covers"
            ),
            "wall_clock_sec": round(reference_wall, 6),
            "operations": reference_operations,
            "pair_checks": reference_stats.get("pair_checks", 0),
            "common_neighborhood_intersections": reference_stats.get(
                "common_neighborhood_intersections", 0
            ),
            "candidate_4sets_tested": reference_stats.get("candidate_4sets_tested", 0),
            "search_nodes": reference_stats.get("search_nodes", 0),
            "solves": "1/1 measured shipping instance; construction audit 8/8 below",
        },
    }

    reference_audit = 0
    for seed in range(8):
        inst = make_instance(seed=88_000 + seed, **shipping_params)
        answer = _algorithm_x(inst)
        reference_audit += int(answer is not None and verify(inst, answer)[0])
    report["G6_adversary_panel"]["reference_algorithm"]["audit_successes"] = reference_audit
    report["G6_adversary_panel"]["reference_algorithm"]["audit_attempts"] = 8
    report["G6_adversary_panel"]["pass"] &= reference_audit == 8

    # G7: double the main size parameter and the fixed-ratio decoy count.
    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled_params["decoys"] *= 2
    doubled_start = time.perf_counter()
    doubled = make_instance(seed=7_007, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
                and doubled["vertex_count"] > shipping["vertex_count"],
        "shipping_vertices": shipping["vertex_count"],
        "doubled_vertices": doubled["vertex_count"],
        "doubled_build_and_verify_sec": round(time.perf_counter() - doubled_start, 6),
        "verify_reason": doubled_reason,
    }

    # G8: relabel vertices, reorder edges, and compose those transformations.
    invariant = 0
    carried = 0
    keys = []
    g8_params = {
        "n": min(shipping_params["n"], 16),
        "decoys": min(shipping_params["decoys"], 32),
    }
    for seed in range(20):
        inst = make_instance(seed=99_000 + seed, **g8_params)
        key = canonical_key(inst)
        keys.append(key)
        transformed = _relabel(inst, random.Random(123_000 + seed))
        invariant += int(canonical_key(transformed) == key)
        carried += int(verify(transformed, transformed["answer"])[0])
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": invariant == 20 and carried == 20 and distinct == 20,
        "relabel_and_reorder_invariant": invariant,
        "transformations_tested": 20,
        "carried_witnesses_verified": carried,
        "unrelated_distinct_keys": distinct,
        "unrelated_instances": 20,
        "invariant": "octahedron-quotient tree plus 1-WL decorated-graph fingerprint",
    }

    # G9: script-owned arms are recorded; only the caps gate.
    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    intended_operations = 2 * shipping["target_blocks"] - 1
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    within_caps = answer_chars <= 2000 and answer_elements <= 256 \
        and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items()
             if key.startswith("G") and key[1:2].isdigit()]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
