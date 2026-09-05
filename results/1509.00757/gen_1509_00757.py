"""Verified generator for radial plane-diameter completions.

The source problem is BBFPDC from arXiv:1509.00757.  The paper's hardness
proof uses non-triangular variable faces whose two useful diagonals encode a
Boolean choice, and long distance witnesses force all choices and clauses.
This module keeps those native objects but uses a deliberately transparent
outerplanar chain rather than reproducing the paper's large NP-hardness
reduction.

An instance has marked pentagonal faces sharing a root.  A witness adds one
radial diagonal in every face.  Symmetric terminal paths force a choice in
every face; two more terminal paths between each consecutive pair force the
same hidden orientation.  The planted phase is sampled before the graph is
labelled, so generation never searches for a completion.  Verification does
not trust the construction: it validates every chord and recomputes the
diameter of the completed graph with exact unweighted BFS.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import random
import re
import time
from collections import deque


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "plane graph with marked pentagonal faces",
        "radial face diagonals",
        "unweighted graph diameter",
    ],
    "verification_operations": [
        "cyclic face-boundary incidence",
        "one-chord-per-face planarity check",
        "exact unweighted breadth-first search",
        "integer diameter comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Pairs of equal-radius terminal paths couple neighboring pentagonal "
        "faces, so their two radial choices propagate as one hidden global "
        "orientation; without recognizing that invariant one must test an "
        "exponential space of face choices."
    ),
    "hardness_basis": (
        "Track B: the paper's Theorem 2 gives BBFPDC an "
        "O(N^3)+2^{2^{O((kd) log d)}} alpha(q)^2 N FPT algorithm, and this "
        "restricted distribution has an O(N(N+E)) exact constraint-extraction "
        "plus BFS algorithm; at shipping n=32 the latter averages 858,334 "
        "edge/constraint operations and 0.444 seconds over eight seeds, while "
        "the compact orientation-propagation route uses 63 exact choices."
    ),
    "max_answer_tokens": 96,
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
    "demo": {"n": 3, "decoys": 0, "tail_length": 1},
    "easy": {"n": 32, "decoys": 16, "tail_length": 3},
    "medium": {"n": 40, "decoys": 40, "tail_length": 3},
    "hard": {"n": 48, "decoys": 96, "tail_length": 3},
}
SHIPPING_DIFFICULTY = "easy"


STRUCTURAL_HINT = (
    "Equal-radius terminal paths encode a common orientation shared by "
    "neighboring pentagonal faces."
)
PLACEBO_HINT = (
    "Careful bookkeeping of vertex labels and face order is important for "
    "this completion problem."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list in displayed face order containing exactly one canonical "
        "undirected radial diagonal [smaller_endpoint,larger_endpoint] for each "
        "of the n marked pentagons.  Each face has exactly two such choices."
    ),
    "bounds": {
        "length": "n",
        "entries_per_edge": 2,
        "choices_per_face": 2,
        "candidate_count": "2^n",
    },
}


NOTES = (
    "Section 1 fixes BBFPDC: a completion is a plane spanning supergraph, q "
    "bounds all new edges, k bounds new edges in each original face, and d "
    "bounds ordinary unweighted diameter.  Theorem 1's BFPDC reduction, in "
    "particular Steps (iii*)-(iv*) and the proof following Figure 7, supplies "
    "the two useful diagonals of each degree-five variable face and uses mast "
    "poles to force a satisfying choice.  Lemmas 6 and 7 explain why the "
    "distance sentinels do not create shortcuts.  The easy regime that rules "
    "out a Track A claim is Theorem 2 (called Theorem 1 in the introduction): "
    "BBFPDC is solvable in O(N^3)+2^{2^{O((kd) log d)}} alpha(q)^2 N steps, "
    "hence is polynomial for fixed k and d; here k=1 and d is fixed by the "
    "tail length.  The generator samples a phase first and composes symmetric "
    "distance identities along a plane chain.  Random relabelling, independent "
    "face rotations/reflections, shuffled input order, and same-radius decoy "
    "sentinels defeat label, boundary-position, degree, frequency, and restart "
    "attacks without changing the native graph certificate."
)


# Filled after the three script-owned oracle runs.  Zero attempts is an honest
# unrun state; selftest records it but only the answer/operation caps are gated.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


def _plain_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _edge(u, v):
    return [u, v] if u < v else [v, u]


def _validate_params(n, decoys, tail_length):
    for name, value in (("n", n), ("decoys", decoys), ("tail_length", tail_length)):
        if not _plain_int(value):
            raise ValueError(f"{name} must be an integer")
    if n < 3:
        raise ValueError("n must be at least 3")
    if decoys < 0:
        raise ValueError("decoys must be nonnegative")
    if tail_length < 1:
        raise ValueError("tail_length must be positive")


def make_instance(n, seed=0, **params):
    """Inverse-generate a certified radial BBFPDC completion.

    The global orientation (the answer) is sampled before any labels, edges,
    face rotations, or decoys.  Everything subsequently added is symmetric in
    the two orientations, so the sampled chords have the promised diameter by
    construction; no completion search occurs here.
    """
    decoys = params.pop("decoys", 0)
    tail_length = params.pop("tail_length", 3)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, decoys, tail_length)
    if not _plain_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)

    # G: sample the certificate's global phase first.
    planted_phase = rng.randrange(2)

    next_vertex = 1

    def new_vertex():
        nonlocal next_vertex
        value = next_vertex
        next_vertex += 1
        return value

    root = 0
    edges = set()
    physical_faces = []
    for _ in range(n):
        a, u, v, b = (new_vertex() for _j in range(4))
        boundary = [root, a, u, v, b]
        for j in range(5):
            edges.add(tuple(_edge(boundary[j], boundary[(j + 1) % 5])))
        physical_faces.append({"boundary": boundary, "u": u, "v": v})

    sentinel_specs = []

    def add_sentinel(neighbors):
        sentinel_root = new_vertex()
        for endpoint in neighbors:
            edges.add(tuple(_edge(sentinel_root, endpoint)))
        path = [sentinel_root]
        previous = sentinel_root
        for _ in range(tail_length):
            vertex = new_vertex()
            edges.add(tuple(_edge(previous, vertex)))
            path.append(vertex)
            previous = vertex
        sentinel_specs.append(
            {
                "root": sentinel_root,
                "pole": previous,
                "path": path,
                "neighbors": list(neighbors),
            }
        )

    # One symmetric terminal per face forces some radial choice in that face.
    for face in physical_faces:
        add_sentinel([face["u"], face["v"]])

    # Two clauses per adjacent pair force the same physical orientation:
    # (u_i or v_j) and (v_i or u_j).
    for i in range(n - 1):
        left, right = physical_faces[i], physical_faces[i + 1]
        add_sentinel([left["u"], right["v"]])
        add_sentinel([left["v"], right["u"]])

    # Decoys are sampled from the exact same symmetric sentinel gadget.  They
    # add crowding but no orientation information because both neighbors lie in
    # one face, whose witness already chooses exactly one of them.
    for _ in range(decoys):
        face = physical_faces[rng.randrange(n)]
        add_sentinel([face["u"], face["v"]])

    # The root pole is longer by two.  With a satisfying completion every
    # sentinel root is exactly at most distance 2 from root, making d tight;
    # an unsatisfied sentinel is at distance 3 and violates d by one.
    root_path = [root]
    previous = root
    for _ in range(tail_length + 2):
        vertex = new_vertex()
        edges.add(tuple(_edge(previous, vertex)))
        root_path.append(vertex)
        previous = vertex
    diameter_bound = 2 * tail_length + 4

    vertex_count = next_vertex
    relabel = list(range(vertex_count))
    rng.shuffle(relabel)

    def mv(vertex):
        return relabel[vertex]

    mapped_edges = [_edge(mv(u), mv(v)) for u, v in edges]
    rng.shuffle(mapped_edges)

    # Rotate and reflect every cyclic boundary independently.  The embedding is
    # unchanged, but there is no globally meaningful "third boundary vertex".
    face_answer_pairs = []
    for face in physical_faces:
        boundary = [mv(v) for v in face["boundary"]]
        if rng.randrange(2):
            boundary.reverse()
        shift = rng.randrange(5)
        boundary = boundary[shift:] + boundary[:shift]
        chosen = face["u"] if planted_phase == 0 else face["v"]
        face_answer_pairs.append(({"boundary": boundary}, _edge(mv(root), mv(chosen))))
    rng.shuffle(face_answer_pairs)
    faces = [pair[0] for pair in face_answer_pairs]
    answer = [pair[1] for pair in face_answer_pairs]

    sentinels = []
    for spec in sentinel_specs:
        sentinels.append(
            {
                "root": mv(spec["root"]),
                "pole": mv(spec["pole"]),
                "path": [mv(v) for v in spec["path"]],
                "neighbors": [mv(v) for v in spec["neighbors"]],
            }
        )
    rng.shuffle(sentinels)

    return {
        "family": "radial bounded-budget plane diameter completion",
        "n": n,
        "decoys": decoys,
        "tail_length": tail_length,
        "vertex_count": vertex_count,
        "root": mv(root),
        "root_path": [mv(v) for v in root_path],
        "diameter_bound": diameter_bound,
        "edge_budget": n,
        "per_face_budget": 1,
        "edges": mapped_edges,
        "faces": faces,
        "sentinels": sentinels,
        "answer": answer,
    }


def _radial_options(inst, face):
    boundary = face.get("boundary") if isinstance(face, dict) else None
    if not isinstance(boundary, list) or len(boundary) != 5:
        raise ValueError("marked face must have a five-vertex boundary")
    root = inst["root"]
    if boundary.count(root) != 1 or len(set(boundary)) != 5:
        raise ValueError("marked face boundary is malformed")
    pos = boundary.index(root)
    endpoints = [boundary[(pos + 2) % 5], boundary[(pos - 2) % 5]]
    return sorted((_edge(root, endpoint) for endpoint in endpoints), key=lambda e: e[1] if e[0] == root else e[0])


def render(inst):
    edge_lines = []
    for start in range(0, len(inst["edges"]), 8):
        group = inst["edges"][start : start + 8]
        edge_lines.append("  " + "  ".join(f"{u}-{v}" for u, v in group))
    face_lines = [
        f"  F{i + 1}: [" + ", ".join(str(v) for v in face["boundary"]) + "]"
        for i, face in enumerate(inst["faces"])
    ]
    statement = f"""Find a radial bounded-budget plane diameter completion.

The instance is a finite simple undirected plane graph G.  Its vertices are the
integers 0 through {inst['vertex_count'] - 1}.  An edge u-v is unweighted and
may be traversed in either direction.  The distance between two vertices is the
fewest edges in a path, and the diameter is the maximum distance over all
vertex pairs.

The embedding has {inst['n']} marked pentagonal faces F1,...,F{inst['n']}.
Each displayed boundary is cyclic: its last vertex is also adjacent to its
first, and rotating or reversing the list describes the same face.  All marked
faces have the same distinguished root vertex R={inst['root']}.  In a marked
pentagon, the two boundary vertices that are two boundary steps from R are the
radial endpoints; joining R to either one is a radial diagonal.

Add exactly one radial diagonal inside every marked face and no other edge.
Thus exactly q={inst['edge_budget']} edges are added in total and at most
k={inst['per_face_budget']} edge is added in each marked face.  Since the face
interiors are disjoint, these additions preserve the supplied plane embedding.
Your completed graph must have diameter at most d={inst['diameter_bound']}.

Existing edges of G (each appears once, in arbitrary order):
{chr(10).join(edge_lines)}

Marked pentagonal face boundaries, in required answer order:
{chr(10).join(face_lines)}

For each face F1 through F{inst['n']}, output its chosen undirected edge as
[u,v] with u<v.  The outer list must follow the displayed face order and contain
exactly {inst['n']} pairs.  Vertex labels are 0-based and repetitions within an
edge are forbidden.

Give your final answer inside <answer></answer> tags, as a JSON list of pairs.
Example: <answer>[[3,17],[5,42],[8,19]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse a tagged JSON witness, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    bodies = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    candidates = list(reversed(bodies))
    if not candidates:
        candidates = [text]
    decoder = json.JSONDecoder()
    for body in candidates:
        cleaned = body.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        starts = [0] if cleaned.startswith("[") else [i for i, ch in enumerate(cleaned) if ch == "["]
        for start in starts:
            try:
                value, _end = decoder.raw_decode(cleaned[start:])
            except (ValueError, TypeError):
                continue
            if isinstance(value, list):
                return value
    return None


def _adjacency(inst, extra_edges=()):
    count = inst["vertex_count"]
    adjacency = [[] for _ in range(count)]
    for edge in itertools.chain(inst["edges"], extra_edges):
        u, v = edge
        adjacency[u].append(v)
        adjacency[v].append(u)
    return adjacency


def _bfs(adjacency, source):
    distances = [-1] * len(adjacency)
    distances[source] = 0
    queue = deque([source])
    edge_scans = 0
    while queue:
        vertex = queue.popleft()
        for neighbor in adjacency[vertex]:
            edge_scans += 1
            if distances[neighbor] < 0:
                distances[neighbor] = distances[vertex] + 1
                queue.append(neighbor)
    return distances, edge_scans


def _diameter(inst, extra_edges):
    adjacency = _adjacency(inst, extra_edges)
    maximum = 0
    operations = 0
    for source in range(len(adjacency)):
        distances, scans = _bfs(adjacency, source)
        operations += scans
        if -1 in distances:
            return None, operations
        maximum = max(maximum, max(distances))
    return maximum, operations


def _shape_and_edges(inst, answer):
    if not isinstance(answer, list):
        return False, "answer must be a JSON list", None
    if not answer:
        return False, "answer is empty", None
    if len(answer) != inst["n"]:
        return False, f"wrong number of face diagonals: expected {inst['n']}", None
    seen = set()
    existing = {tuple(edge) for edge in inst["edges"]}
    accepted = []
    for index, item in enumerate(answer):
        if not isinstance(item, list) or len(item) != 2 or not all(_plain_int(v) for v in item):
            return False, f"entry {index + 1} must be a pair of integer labels", None
        u, v = item
        if not (0 <= u < inst["vertex_count"] and 0 <= v < inst["vertex_count"]):
            return False, f"entry {index + 1} has an out-of-range vertex", None
        if u >= v:
            return False, f"entry {index + 1} is not in canonical u<v order", None
        edge = (u, v)
        if edge in seen:
            return False, f"entry {index + 1} duplicates an earlier edge", None
        seen.add(edge)
        if edge in existing:
            return False, f"entry {index + 1} is already an edge of G", None
        try:
            options = {tuple(option) for option in _radial_options(inst, inst["faces"][index])}
        except (KeyError, TypeError, ValueError) as exc:
            return False, f"malformed instance face: {exc}", None
        if edge not in options:
            return False, f"entry {index + 1} is not a radial diagonal of F{index + 1}", None
        accepted.append([u, v])
    return True, "ok", accepted


def _selected_endpoints(inst, edges):
    root = inst["root"]
    return {v if u == root else u for u, v in edges}


def _quick_sentinel_check(inst, edges):
    """Executable necessary condition used before the all-pairs BFS.

    Every listed sentinel has a path of tail_length from its root and is joined
    to exactly its two listed radial endpoints.  With the longer root path, its
    pole is within d of the root pole only if at least one neighbor is selected.
    This is checked directly from instance records; passing candidates are still
    subjected to full BFS below.
    """
    selected = _selected_endpoints(inst, edges)
    for sentinel in inst["sentinels"]:
        if not any(endpoint in selected for endpoint in sentinel["neighbors"]):
            return False, sentinel["pole"]
    return True, None


def verify(inst, answer):
    """Accept any valid radial completion, never consulting the planted answer."""
    ok, reason, edges = _shape_and_edges(inst, answer)
    if not ok:
        return False, reason
    sentinel_ok, pole = _quick_sentinel_check(inst, edges)
    if not sentinel_ok:
        return False, f"diameter exceeds d at sentinel pole {pole}"
    diameter, _operations = _diameter(inst, edges)
    if diameter is None:
        return False, "completed graph is disconnected"
    if diameter > inst["diameter_bound"]:
        return False, f"completed graph has diameter {diameter}, exceeding d={inst['diameter_bound']}"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from the structure-aware two-choice-per-face language."""
    if not hasattr(rng, "randrange"):
        raise TypeError("rng must provide randrange")
    return [_radial_options(inst, face)[rng.randrange(2)] for face in inst["faces"]]


def search_space(inst):
    return 1 << inst["n"]


def enumerate_all(inst):
    """Brute-force the declared language only while the work is safely capped."""
    if inst["n"] > 18:
        return None
    options = [_radial_options(inst, face) for face in inst["faces"]]
    total = 0
    for bits in itertools.product((0, 1), repeat=inst["n"]):
        candidate = [options[i][bits[i]] for i in range(inst["n"])]
        if _quick_sentinel_check(inst, candidate)[0]:
            ok, _reason = verify(inst, candidate)
            total += int(ok)
    return total


def _constraint_structure(inst):
    endpoint_face = {}
    for face_index, face in enumerate(inst["faces"]):
        for option in _radial_options(inst, face):
            endpoint = option[1] if option[0] == inst["root"] else option[0]
            endpoint_face[endpoint] = face_index
    colors = [0] * inst["n"]
    tree_edges = set()
    clauses = []
    option_index = {}
    for face_index, face in enumerate(inst["faces"]):
        for bit, option in enumerate(_radial_options(inst, face)):
            endpoint = option[1] if option[0] == inst["root"] else option[0]
            option_index[endpoint] = (face_index, bit)
    for sentinel in inst["sentinels"]:
        try:
            literals = [option_index[v] for v in sentinel["neighbors"]]
        except (KeyError, TypeError):
            continue
        faces = {literal[0] for literal in literals}
        if len(faces) == 1:
            colors[next(iter(faces))] += 1
        elif len(faces) == 2:
            i, j = sorted(faces)
            tree_edges.add((i, j))
            clauses.append((literals[0], literals[1]))
    return colors, tree_edges, clauses


def _rooted_tree_code(vertex, parent, adjacency, colors):
    children = [
        _rooted_tree_code(neighbor, vertex, adjacency, colors)
        for neighbor in adjacency[vertex]
        if neighbor != parent
    ]
    children.sort()
    return f"{colors[vertex]}(" + "".join(children) + ")"


def _colored_tree_code(colors, edges):
    n = len(colors)
    adjacency = [[] for _ in range(n)]
    for u, v in edges:
        adjacency[u].append(v)
        adjacency[v].append(u)
    if n == 1:
        return f"{colors[0]}()"
    if len(edges) != n - 1 or any(not row for row in adjacency):
        # Strong deterministic fallback for malformed/non-tree instances.  It is
        # still label-invariant but intentionally does not pretend to solve GI.
        degrees_and_colors = sorted((len(adjacency[i]), colors[i]) for i in range(n))
        return "fallback:" + json.dumps(degrees_and_colors, separators=(",", ":"))
    degree = [len(row) for row in adjacency]
    leaves = deque(i for i, value in enumerate(degree) if value <= 1)
    remaining = n
    while remaining > 2:
        layer = len(leaves)
        remaining -= layer
        for _ in range(layer):
            leaf = leaves.popleft()
            degree[leaf] = 0
            for neighbor in adjacency[leaf]:
                if degree[neighbor] > 0:
                    degree[neighbor] -= 1
                    if degree[neighbor] == 1:
                        leaves.append(neighbor)
    centers = list(leaves)
    codes = [_rooted_tree_code(center, -1, adjacency, colors) for center in centers]
    return min(codes)


def canonical_key(inst):
    """Canonicalize the colored constraint tree, not labels or rendering order."""
    colors, edges, _clauses = _constraint_structure(inst)
    tree_code = _colored_tree_code(colors, edges)
    payload = {
        "n": inst["n"],
        "tail_length": inst["tail_length"],
        "root_tail_edges": len(inst["root_path"]) - 1,
        "colored_constraint_tree": tree_code,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params):
    """Grow symmetric decoy crowding while keeping the certificate length fixed."""
    current = dict(params)
    current.pop("_preset", None)
    n = current.get("n")
    decoys = current.get("decoys", 0)
    tail_length = current.get("tail_length", 3)
    if not all(_plain_int(v) for v in (n, decoys, tail_length)):
        return None
    return {
        "n": n,
        "decoys": decoys + max(n, decoys // 2, 1),
        "tail_length": tail_length + (1 if decoys >= 8 * n else 0),
    }


def _candidate_from_bits(inst, bits):
    return [_radial_options(inst, face)[bits[i]] for i, face in enumerate(inst["faces"])]


def _attack_degree_outlier(inst):
    adjacency = _adjacency(inst)
    bits = []
    for face in inst["faces"]:
        options = _radial_options(inst, face)
        endpoints = [edge[1] if edge[0] == inst["root"] else edge[0] for edge in options]
        scores = [len(adjacency[v]) for v in endpoints]
        bits.append(0 if scores[0] >= scores[1] else 1)
    return _candidate_from_bits(inst, bits)


def _attack_greedy_frequency(inst):
    frequency = [0] * inst["vertex_count"]
    for sentinel in inst["sentinels"]:
        for endpoint in sentinel["neighbors"]:
            frequency[endpoint] += 1
    bits = []
    for face in inst["faces"]:
        options = _radial_options(inst, face)
        endpoints = [edge[1] if edge[0] == inst["root"] else edge[0] for edge in options]
        scores = [frequency[v] for v in endpoints]
        bits.append(0 if scores[0] > scores[1] else 1)
    return _candidate_from_bits(inst, bits)


def _attack_clockwise_ansatz(inst):
    answer = []
    root = inst["root"]
    for face in inst["faces"]:
        boundary = face["boundary"]
        pos = boundary.index(root)
        answer.append(_edge(root, boundary[(pos + 2) % 5]))
    return answer


def _attack_random_restart(inst, seed, restarts=256):
    rng = random.Random(seed)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if _quick_sentinel_check(inst, candidate)[0]:
            ok, _reason = verify(inst, candidate)
            if ok:
                return candidate
    return None


def _reference_solve(inst):
    """Mechanical exact solver: extract binary clauses and propagate the tree."""
    started = time.perf_counter()
    _colors, tree_edges, clauses = _constraint_structure(inst)
    operations = len(inst["sentinels"]) * 2
    grouped = {}
    for left, right in clauses:
        pair = tuple(sorted((left[0], right[0])))
        grouped.setdefault(pair, []).append((left, right))
        operations += 1

    constraint_adjacency = [[] for _ in range(inst["n"])]
    for (i, j), pair_clauses in grouped.items():
        allowed = []
        for vi in (0, 1):
            for vj in (0, 1):
                good = True
                for (fi, oi), (fj, oj) in pair_clauses:
                    values = {i: vi, j: vj}
                    operations += 2
                    if values[fi] != oi and values[fj] != oj:
                        good = False
                        break
                if good:
                    allowed.append((vi, vj))
        if len(allowed) != 2:
            raise ValueError("reference extraction did not find a binary relation")
        mapping_i_to_j = {vi: vj for vi, vj in allowed}
        mapping_j_to_i = {vj: vi for vi, vj in allowed}
        constraint_adjacency[i].append((j, mapping_i_to_j))
        constraint_adjacency[j].append((i, mapping_j_to_i))

    bits = [None] * inst["n"]
    bits[0] = 0
    queue = deque([0])
    while queue:
        vertex = queue.popleft()
        for neighbor, mapping in constraint_adjacency[vertex]:
            operations += 1
            wanted = mapping[bits[vertex]]
            if bits[neighbor] is None:
                bits[neighbor] = wanted
                queue.append(neighbor)
            elif bits[neighbor] != wanted:
                raise ValueError("extracted constraints are inconsistent")
    if any(bit is None for bit in bits):
        raise ValueError("extracted constraint graph is disconnected")
    answer = _candidate_from_bits(inst, bits)
    diameter, bfs_operations = _diameter(inst, answer)
    operations += bfs_operations
    if diameter is None or diameter > inst["diameter_bound"]:
        # The other global phase is the only alternative for this symmetric
        # family; trying it is still a constant part of the reference method.
        bits = [1 - bit for bit in bits]
        answer = _candidate_from_bits(inst, bits)
        diameter, bfs_operations = _diameter(inst, answer)
        operations += bfs_operations
    elapsed = time.perf_counter() - started
    return answer, operations, elapsed


def _transform_instance(inst, rng, relabel=True, reorder=True, boundary_symmetry=True):
    transformed = json.loads(json.dumps(inst))
    count = inst["vertex_count"]
    permutation = list(range(count))
    if relabel:
        rng.shuffle(permutation)

    def mv(vertex):
        return permutation[vertex]

    transformed["root"] = mv(inst["root"])
    transformed["root_path"] = [mv(v) for v in inst["root_path"]]
    transformed["edges"] = [_edge(mv(u), mv(v)) for u, v in inst["edges"]]
    transformed["sentinels"] = [
        {
            "root": mv(s["root"]),
            "pole": mv(s["pole"]),
            "path": [mv(v) for v in s["path"]],
            "neighbors": [mv(v) for v in s["neighbors"]],
        }
        for s in inst["sentinels"]
    ]
    faces = []
    answers = []
    for face, edge in zip(inst["faces"], inst["answer"]):
        boundary = [mv(v) for v in face["boundary"]]
        if boundary_symmetry:
            if rng.randrange(2):
                boundary.reverse()
            shift = rng.randrange(5)
            boundary = boundary[shift:] + boundary[:shift]
        faces.append({"boundary": boundary})
        answers.append(_edge(mv(edge[0]), mv(edge[1])))
    if reorder:
        order = list(range(len(faces)))
        rng.shuffle(order)
        faces = [faces[i] for i in order]
        answers = [answers[i] for i in order]
        rng.shuffle(transformed["edges"])
        rng.shuffle(transformed["sentinels"])
    transformed["faces"] = faces
    transformed["answer"] = answers
    return transformed


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest():
    report = {}
    presets = list(DIFFICULTY.items())

    g1_checks = 0
    g1_failures = []
    for preset, params in presets:
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **shipping_params)
    corruption_results = {}
    corruptions = {}
    corruptions["empty"] = []
    corruptions["drop_one"] = inst["answer"][:-1]
    swapped = json.loads(json.dumps(inst["answer"]))
    swapped[0] = list(reversed(swapped[0]))
    corruptions["swap_endpoints"] = swapped
    duplicated = json.loads(json.dumps(inst["answer"]))
    duplicated[1] = list(duplicated[0])
    corruptions["duplicate"] = duplicated
    out_of_range = json.loads(json.dumps(inst["answer"]))
    out_of_range[0] = [0, inst["vertex_count"]]
    corruptions["out_of_range"] = out_of_range
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    g2_pass = all(row["rejected"] for row in corruption_results.values()) and len(set(reasons)) == len(reasons)
    report["G2_rejects_corruption"] = {
        "pass": g2_pass,
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    encoded_answer = json.dumps(inst["answer"], separators=(",", ":"))
    model_style = f"I traced the face constraints.\n```json\n<answer>{encoded_answer}</answer>\n```"
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and parse_answer("not an answer") is None,
        "model_style_round_trip": parsed == inst["answer"],
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    guess_total = 200_000
    guess_hits = 0
    guess_rng = random.Random(99173)
    guess_started = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        if _quick_sentinel_check(inst, candidate)[0]:
            ok, _reason = verify(inst, candidate)
            guess_hits += int(ok)
    guess_elapsed = time.perf_counter() - guess_started
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "declared_space": search_space(inst),
        "sampler": "uniform independent choice between the two radial diagonals in every face",
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    demo_inst = make_instance(seed=11, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    baseline_started = time.perf_counter()
    baseline_attempts = 0
    baseline_successes = 0
    for seed in range(8):
        attack_inst = make_instance(seed=7000 + seed, **shipping_params)
        candidate = _attack_random_restart(attack_inst, 9000 + seed, 256)
        baseline_attempts += 256
        baseline_successes += int(candidate is not None)
    baseline_elapsed = time.perf_counter() - baseline_started
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_probability < 1e-6 and demo_count == 2,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_sampled_density": guess_probability,
        "shipping_exact_valid_answers_by_structure": 2,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo_inst),
        "strongest_failing_attack_wall_sec": round(baseline_elapsed, 6),
        "strongest_failing_attack_restarts": baseline_attempts,
        "strongest_failing_attack_seed_successes": baseline_successes,
    }

    attack_functions = {
        "outlier_endpoint_degree": lambda x, s: _attack_degree_outlier(x),
        "greedy_sentinel_frequency": lambda x, s: _attack_greedy_frequency(x),
        "random_restart_256": lambda x, s: _attack_random_restart(x, 12000 + s, 256),
        "in_context_clockwise_ansatz": lambda x, s: _attack_clockwise_ansatz(x),
    }
    attack_results = {name: {"successes": 0, "attempts": 8} for name in attack_functions}
    for seed in range(8):
        attack_inst = make_instance(seed=13000 + seed, **shipping_params)
        for name, attack in attack_functions.items():
            candidate = attack(attack_inst, seed)
            if candidate is not None:
                ok, _reason = verify(attack_inst, candidate)
                attack_results[name]["successes"] += int(ok)

    reference_operations = []
    reference_times = []
    reference_successes = 0
    for seed in range(8):
        reference_inst = make_instance(seed=15000 + seed, **shipping_params)
        candidate, operations, elapsed = _reference_solve(reference_inst)
        ok, _reason = verify(reference_inst, candidate)
        reference_successes += int(ok)
        reference_operations.append(operations)
        reference_times.append(elapsed)
    reference = {
        "name": "binary sentinel-clause extraction, tree propagation, and all-pairs BFS verification",
        "complexity": "O(N(N+E)) exact, dominated by unweighted all-pairs BFS",
        "wall_clock_sec_mean": round(sum(reference_times) / len(reference_times), 6),
        "wall_clock_sec_max": round(max(reference_times), 6),
        "operations_mean": round(sum(reference_operations) / len(reference_operations)),
        "operations_max": max(reference_operations),
        "solves": f"{reference_successes}/8, as expected",
    }
    report["G6_adversary_panel"] = {
        "pass": all(row["successes"] == 0 for row in attack_results.values()) and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": reference,
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=2468, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    escalated = escalate(shipping_params)
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst) and isinstance(escalated, dict) and escalated["decoys"] > shipping_params["decoys"],
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "shipping_space_bits": inst["n"],
        "doubled_space_bits": doubled["n"],
        "doubled_verify_reason": doubled_reason,
        "fixed_answer_length_escalation": escalated,
    }

    invariance_checks = 0
    preserving_checks = 0
    distinct_keys = []
    g8_failures = []
    for seed in range(20):
        original = make_instance(seed=20000 + seed, **shipping_params)
        key = canonical_key(original)
        distinct_keys.append(key)
        transforms = (
            _transform_instance(original, random.Random(30000 + seed), True, False, False),
            _transform_instance(original, random.Random(40000 + seed), False, True, True),
            _transform_instance(original, random.Random(50000 + seed), True, True, True),
        )
        for transformed in transforms:
            invariance_checks += 1
            if canonical_key(transformed) != key:
                g8_failures.append(f"seed {seed}: key changed")
            ok, reason = verify(transformed, transformed["answer"])
            preserving_checks += 1
            if not ok:
                g8_failures.append(f"seed {seed}: transformed witness failed: {reason}")
    distinct_count = len(set(distinct_keys))
    if distinct_count != len(distinct_keys):
        g8_failures.append("unrelated seeds collided")
    report["G8_canonical_key"] = {
        "pass": not g8_failures,
        "invariance_checks": invariance_checks,
        "witness_preserving_transform_checks": preserving_checks,
        "distinct_unrelated_keys": distinct_count,
        "unrelated_instances": len(distinct_keys),
        "transformations": ["arbitrary vertex relabelling", "input/face reordering plus dihedral boundary symmetry", "composition of all transformations"],
        "failures": g8_failures,
    }

    measured_answer_chars = []
    for size_seed in range(500):
        size_inst = make_instance(seed=size_seed, **shipping_params)
        measured_answer_chars.append(
            len(json.dumps(size_inst["answer"]))
        )
    answer_chars = max(measured_answer_chars)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(inst["answer"])
    intended_operations = 2 * inst["n"] - 1
    arms = {
        key: {"solved": value["solved"], "attempts": value["attempts"]}
        for key, value in G9_ORACLE_RESULTS.items()
        if key in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "answer_size_seeds_measured": len(measured_answer_chars),
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["profile"] = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": shipping_params,
        "certificate_language": CERTIFICATE_LANGUAGE,
        "reference_algorithm": reference,
    }
    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
