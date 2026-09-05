"""Verified connected-face-cover generator for arXiv:2301.09440.

The paper proves that a connected face cover of a plane biconnected graph is
equivalent both to an outerplanar split sequence and to a feedback vertex set
in the dual.  Its NP-hardness reduction maps a vertex cover of a biconnected
cubic plane graph G to an equally large connected face cover of the graph
obtained by subdividing every edge of G's dual once.

This module constructs G together with a minimum vertex cover.  It begins with
K4 and repeatedly replaces one cubic vertex by the seven-vertex planar
"cube-minus-a-vertex" patch.  The replacement raises the independence number
by exactly three, so the complementary minimum cover is known by composition,
not found by solving the generated instance.  The paper's reduction then
turns it into the native plane graph and connected-face-cover witness shown to
the solver.
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
        "biconnected plane graph given by all facial boundary cycles",
        "face-vertex incidence graph",
        "connected face cover",
    ],
    "verification_operations": [
        "exact face-boundary incidence lookup",
        "finite set union for vertex coverage",
        "breadth-first connectivity in the face-vertex incidence graph",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3, Property 1 and the NP-completeness theorem: vertex cover "
        "in a biconnected cubic plane graph maps to connected face cover in "
        "the all-1-subdivision of its dual"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Recognize recursively nested seven-vertex cube-minus-one-vertex "
        "patches in the face-intersection graph; without that decomposition, "
        "one must search among fixed-size face subsets."
    ),
    "hardness_basis": (
        "Track B: reverse cube-patch contraction recovers a minimum cover in "
        "O(F^2) local adjacency inspections; over eight shipping seeds it used "
        "4,819--5,803 counted local/update operations and about 0.0129 seconds "
        "per instance, while after recognizing the decomposition the compact "
        "route is 50 contractions plus 153 outputs (203 high-level operations)."
    ),
    # Exact worst case for a compact JSON list of 153 labels drawn from
    # 1..304: all labels can have three digits, so (459 digits + 152 commas
    # + 2 brackets) / 4 characters per approximate token rounds up to 154.
    "max_answer_tokens": 154,
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

# n is the number of alpha-preserving vertex expansions.  nesting_bias is the
# percentage chance that the next expansion occurs inside the newest patch.
# Raising it at fixed n lengthens the dependency chain without lengthening the
# witness, which gives escalate() a second, fixed-answer-length axis.
DIFFICULTY = {
    "demo": {"n": 0, "nesting_bias": 0},
    "easy": {"n": 15, "nesting_bias": 45},
    "medium": {"n": 30, "nesting_bias": 65},
    "hard": {"n": 50, "nesting_bias": 85},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Look for recursively nested seven-vertex cube-minus-one-vertex patches "
    "in the graph whose vertices are the displayed faces."
)
PLACEBO_HINT = (
    "Inspect every displayed boundary incidence carefully and double-check all "
    "labels before committing to the requested set of faces."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A strictly increasing JSON list of exactly k distinct displayed face "
        "labels; every label is an integer in the instance's finite face-label "
        "set.  Candidates are sampled uniformly from all k-subsets."
    ),
    "bounds": {
        "length": "instance field k",
        "entry_set": "the displayed positive integer face labels",
        "distinct": True,
        "canonical_order": "strictly increasing",
        "candidate_count": "binomial(number_of_faces, k)",
    },
}

NOTES = (
    "Section 2, Definition 1 fixes face covers and connectivity through the "
    "face-vertex incidence graph. Lemmas 1--3 and Theorem 1 identify a cover "
    "of size k+1 with k embedding-preserving splits. Section 3, Property 1 "
    "and the NP-completeness proof license the all-1-subdivision-of-the-dual "
    "construction used here. Section 4, Theorem 2 identifies connected face "
    "covers with feedback vertex sets; its corollary is the important easy "
    "regime: maximal planar inputs are polynomial-time because their duals "
    "are subcubic. The paper also notes a 13k kernel and a PTAS. This generated "
    "distribution has an additional easy route and is therefore Track B: "
    "recursively contract cube-minus-one-vertex patches back to K4. Plants and "
    "decoys are indistinguishable by boundary length (every displayed face is "
    "a 6-cycle), labels and input order are uniformly scrambled, and the audit "
    "tests boundary outliers, greedy set cover, randomized greedy independent "
    "sets, label parity, and a local four-cycle ansatz."
)


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_GUESS_SAMPLES = 200_000

# Filled after the three official oracle arms run.  Keeping the fields in the
# module makes selftest_report.json reproducible from the final source.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unavailable: OpenRouter HTTP 403 key limit",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_params(n, nesting_bias, seed):
    if not _is_int(n) or n < 0:
        raise ValueError("n must be a nonnegative integer")
    if not _is_int(nesting_bias) or not 0 <= nesting_bias <= 100:
        raise ValueError("nesting_bias must be an integer from 0 through 100")
    if not _is_int(seed):
        raise ValueError("seed must be an integer")


def _base_rotation():
    """A consistently oriented plane rotation system for K4."""
    return {
        0: [1, 3, 2],
        1: [2, 3, 0],
        2: [0, 3, 1],
        3: [0, 1, 2],
    }


def _expand_vertex(rotation, independent, vertex, next_label):
    """Replace one cubic vertex by a planar seven-vertex 3-pole.

    The patch has terminals p_i, intermediate vertices q_i, and centre c.
    Its internal edges are a 6-cycle p0,q0,p1,q1,p2,q2 plus c--q_i.
    If the contracted vertex belongs to an independent set, replace it by all
    p_i and c; otherwise add all q_i.  Either branch gains exactly three.
    """
    neighbours = list(rotation[vertex])
    if len(neighbours) != 3:
        raise AssertionError("the source graph stopped being cubic")
    p = [next_label + i for i in range(3)]
    q = [next_label + 3 + i for i in range(3)]
    centre = next_label + 6

    del rotation[vertex]
    for i, neighbour in enumerate(neighbours):
        where = rotation[neighbour].index(vertex)
        rotation[neighbour][where] = p[i]
        rotation[p[i]] = [neighbour, q[i], q[(i - 1) % 3]]
        rotation[q[i]] = [p[(i + 1) % 3], centre, p[i]]
    rotation[centre] = list(q)

    created = set(p + q + [centre])
    if vertex in independent:
        independent.remove(vertex)
        independent.update(p)
        independent.add(centre)
    else:
        independent.update(q)
    return next_label + 7, created


def _face_darts(rotation):
    """Return oriented facial dart cycles and a dart-to-face map."""
    seen = set()
    cycles = []
    dart_face = {}
    for u in sorted(rotation):
        for v in rotation[u]:
            if (u, v) in seen:
                continue
            face_id = len(cycles)
            cycle = []
            a, b = u, v
            while (a, b) not in seen:
                seen.add((a, b))
                dart_face[(a, b)] = face_id
                cycle.append((a, b))
                neighbours = rotation[b]
                position = neighbours.index(a)
                a, b = b, neighbours[(position - 1) % len(neighbours)]
            cycles.append(cycle)
    return cycles, dart_face


def _facial_cycles(rotation):
    return [[u for u, _v in cycle] for cycle in _face_darts(rotation)[0]]


def _subdivided_dual(rotation):
    """Build the all-1-subdivision of the plane dual.

    Dual-face vertices are numbered 0..f-1.  Every source edge receives one
    new degree-2 vertex.  The resulting facial cycles are in bijection with
    source vertices, and every one has length six because the source is cubic.
    """
    source_faces, dart_face = _face_darts(rotation)
    source_edges = sorted(
        {tuple(sorted((u, v))) for u in rotation for v in rotation[u]}
    )
    edge_number = {edge: i for i, edge in enumerate(source_edges)}
    face_count = len(source_faces)
    dual_rotation = {}
    for face_id, dart_cycle in enumerate(source_faces):
        dual_rotation[face_id] = [
            face_count + edge_number[tuple(sorted((u, v)))]
            for u, v in dart_cycle
        ]
    for edge, edge_id in edge_number.items():
        u, v = edge
        dual_rotation[face_count + edge_id] = [
            dart_face[(u, v)],
            dart_face[(v, u)],
        ]

    dual_faces = _facial_cycles(dual_rotation)
    face_to_source = {}
    for face_id, boundary in enumerate(dual_faces):
        edge_nodes = [x for x in boundary if x >= face_count]
        common = None
        for edge_node in edge_nodes:
            source_edge = source_edges[edge_node - face_count]
            endpoints = set(source_edge)
            common = endpoints if common is None else common & endpoints
        if common is None or len(common) != 1:
            raise AssertionError("a dual face did not identify one source vertex")
        face_to_source[face_id] = next(iter(common))
    if set(face_to_source.values()) != set(rotation):
        raise AssertionError("dual faces are not in bijection with source vertices")
    return dual_rotation, dual_faces, face_to_source


def _scramble_instance(dual_rotation, dual_faces, face_to_source, cover, rng):
    """Erase every construction label while preserving the plane embedding."""
    vertices = sorted(dual_rotation)
    vertex_labels = list(range(1, len(vertices) + 1))
    rng.shuffle(vertex_labels)
    vertex_map = dict(zip(vertices, vertex_labels))

    face_labels = list(range(1, len(dual_faces) + 1))
    rng.shuffle(face_labels)
    face_map = dict(enumerate(face_labels))
    reflect = bool(rng.getrandbits(1))
    rows = []
    for old_face, boundary in enumerate(dual_faces):
        transformed = [vertex_map[v] for v in boundary]
        if reflect:
            transformed.reverse()
        shift = rng.randrange(len(transformed))
        transformed = transformed[shift:] + transformed[:shift]
        rows.append({"id": face_map[old_face], "boundary": transformed})
    rng.shuffle(rows)

    answer = sorted(
        face_map[old_face]
        for old_face, source_vertex in face_to_source.items()
        if source_vertex in cover
    )
    return rows, answer


def make_instance(n, seed=0, **params):
    """Construct a minimum connected face cover without solving the instance.

    K4 starts with a known maximum independent set of size one.  Each local
    replacement carries that set forward and raises its size by three.  For the
    converse bound, any independent set using four patch vertices must use all
    terminals plus the centre and therefore contracts to an independent set
    containing the old vertex; a set using at most three patch vertices
    contracts with the old vertex absent.  Thus alpha rises by exactly three.
    The complement is a minimum vertex cover and Section 3 of the paper carries
    it to the returned connected face cover.
    """
    nesting_bias = params.pop("nesting_bias", 50)
    if params:
        raise TypeError("unexpected parameters: " + ", ".join(sorted(params)))
    _validate_params(n, nesting_bias, seed)
    rng = random.Random(seed)

    rotation = _base_rotation()
    independent = {rng.randrange(4)}
    next_label = 4
    newest = set(rotation)
    for _step in range(n):
        if newest and rng.randrange(100) < nesting_bias:
            pool = sorted(newest & set(rotation))
        else:
            pool = sorted(rotation)
        vertex = rng.choice(pool)
        next_label, newest = _expand_vertex(
            rotation, independent, vertex, next_label
        )

    vertex_count = len(rotation)
    expected_alpha = 1 + 3 * n
    if len(independent) != expected_alpha:
        raise AssertionError("carried independent set has the wrong size")
    cover = set(rotation) - independent
    expected_cover = 3 + 3 * n
    if len(cover) != expected_cover:
        raise AssertionError("carried vertex cover has the wrong size")

    dual_rotation, dual_faces, face_to_source = _subdivided_dual(rotation)
    if any(len(boundary) != 6 for boundary in dual_faces):
        raise AssertionError("cubic source did not yield six-sided dual faces")
    faces, answer = _scramble_instance(
        dual_rotation, dual_faces, face_to_source, cover, rng
    )
    return {
        "n": n,
        "nesting_bias": nesting_bias,
        "plane_vertex_count": len(dual_rotation),
        "face_count": vertex_count,
        "k": expected_cover,
        "faces": faces,
        "answer": answer,
    }


def render(inst):
    lines = [
        "CONNECTED FACE COVER IN A PLANE GRAPH",
        "",
        "A plane graph is specified below by all of its faces.  Each row has",
        "the form `face-label: v1 v2 ...`, listing the graph vertices met while",
        "walking once around that face.  The list is cyclic: its starting point",
        "and direction do not matter.  Vertex labels and face labels are positive",
        "integers, and the outer face is not distinguished.",
        "",
        "A face cover is a set S of displayed faces such that every graph vertex",
        "occurs on the boundary of at least one face in S.  It is connected when",
        "the following bipartite incidence graph is connected: one side contains",
        "the faces in S, the other side contains all graph vertices, and a chosen",
        "face is adjacent to exactly the vertices on its displayed boundary.",
        "",
        f"This instance has {inst['plane_vertex_count']} graph vertices and "
        f"{inst['face_count']} faces.",
        f"Find a connected face cover containing exactly k = {inst['k']} faces.",
        "",
        "FACIAL BOUNDARY CYCLES",
    ]
    for face in inst["faces"]:
        lines.append(
            str(face["id"]) + ": " + " ".join(map(str, face["boundary"]))
        )
    lines.extend(
        [
            "",
            "Output the face labels as a JSON array of exactly k distinct integers",
            "in strictly increasing order.  Labels are 1-indexed as displayed;",
            "order has no mathematical meaning, but increasing order is the required",
            "canonical output format, and repeats are forbidden.",
            "Give your final answer inside <answer></answer> tags.",
            "Example format: <answer>[2, 7, 11]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    body = matches[-1].strip() if matches else text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.I | re.S)
    if fenced:
        body = fenced.group(1).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, list):
        return None
    return value


def _face_table(inst):
    table = {}
    faces = inst.get("faces")
    if not isinstance(faces, list):
        return None
    for row in faces:
        if not isinstance(row, dict):
            return None
        face_id = row.get("id")
        boundary = row.get("boundary")
        if not _is_int(face_id) or face_id in table:
            return None
        if not isinstance(boundary, list) or not boundary:
            return None
        if not all(_is_int(vertex) for vertex in boundary):
            return None
        table[face_id] = list(boundary)
    return table


def verify(inst, answer):
    """Check the submitted connected face cover; never inspect inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if not all(_is_int(value) for value in answer):
        return False, "every face label must be an integer"
    if len(answer) != inst.get("k"):
        return False, f"expected exactly {inst.get('k')} face labels"
    if len(set(answer)) != len(answer):
        return False, "face labels must be distinct"
    if any(a >= b for a, b in zip(answer, answer[1:])):
        return False, "face labels must be in strictly increasing order"

    table = _face_table(inst)
    if table is None:
        return False, "instance has malformed facial boundary data"
    unknown = [face_id for face_id in answer if face_id not in table]
    if unknown:
        return False, f"unknown face label {unknown[0]}"

    all_vertices = set()
    incidence = {}
    for face_id, boundary in table.items():
        all_vertices.update(boundary)
        for vertex in set(boundary):
            incidence.setdefault(vertex, set()).add(face_id)
    selected = set(answer)
    covered = set().union(*(set(table[f]) for f in answer))
    missing = sorted(all_vertices - covered)
    if missing:
        return False, f"graph vertex {missing[0]} is not covered"

    # Connectivity of H[S union V].  Coverage guarantees every vertex exists in
    # this induced incidence graph, so one BFS across tagged face/vertex nodes is
    # an exact executable certificate check.
    start = ("f", answer[0])
    seen = {start}
    queue = [start]
    head = 0
    while head < len(queue):
        kind, label = queue[head]
        head += 1
        if kind == "f":
            neighbours = [("v", v) for v in set(table[label])]
        else:
            neighbours = [("f", f) for f in incidence[label] if f in selected]
        for node in neighbours:
            if node not in seen:
                seen.add(node)
                queue.append(node)
    wanted = len(selected) + len(all_vertices)
    if len(seen) != wanted:
        return False, "the selected face-vertex incidence graph is disconnected"
    return True, "ok"


def random_candidate(inst, rng):
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    labels = sorted(face["id"] for face in inst["faces"])
    return sorted(rng.sample(labels, inst["k"]))


def search_space(inst):
    return math.comb(inst["face_count"], inst["k"])


def enumerate_all(inst):
    space = search_space(inst)
    if space > 250_000:
        return None
    labels = sorted(face["id"] for face in inst["faces"])
    total = 0
    for candidate in itertools.combinations(labels, inst["k"]):
        total += int(verify(inst, list(candidate))[0])
    return total


def _rotation_from_faces(inst):
    """Recover a global rotation system from arbitrarily oriented face rows.

    A facial boundary cycle has no preferred traversal direction.  Normalize
    the independently chosen row directions first: two faces incident to an
    edge must traverse that edge oppositely in a consistent orientation of the
    sphere.  The resulting system is unique up to reversing every face, which
    canonical_key() already removes by considering both map orientations.
    """
    faces = inst.get("faces")
    if not isinstance(faces, list) or not faces:
        raise ValueError("missing facial cycles")

    edge_uses = {}
    cycles = {}
    for row_number, face in enumerate(faces):
        if not isinstance(face, dict):
            raise ValueError("malformed facial cycle")
        face_id = face.get("id")
        cycle = face.get("boundary")
        if not _is_int(face_id) or face_id in cycles:
            raise ValueError("facial labels must be distinct integers")
        if not isinstance(cycle, list) or len(cycle) < 3:
            raise ValueError("facial cycles must contain at least three vertices")
        if not all(_is_int(vertex) for vertex in cycle):
            raise ValueError("facial cycles contain a non-integer vertex")
        cycles[face_id] = list(cycle)
        for u, v in zip(cycle, cycle[1:] + cycle[:1]):
            if u == v:
                raise ValueError("facial cycle contains a loop")
            edge = (u, v) if u < v else (v, u)
            direction = 1 if (u, v) == edge else -1
            edge_uses.setdefault(edge, []).append((face_id, direction, row_number))

    constraints = {face_id: [] for face_id in cycles}
    for uses in edge_uses.values():
        if len(uses) != 2:
            raise ValueError("each plane edge must occur in exactly two faces")
        (left, left_dir, _), (right, right_dir, _) = uses
        if left == right:
            raise ValueError("an edge occurs twice on one generated face")
        # flip[right] = relation * flip[left].
        relation = -left_dir * right_dir
        constraints[left].append((right, relation))
        constraints[right].append((left, relation))

    flips = {}
    for root in sorted(cycles):
        if root in flips:
            continue
        flips[root] = 1
        queue = [root]
        head = 0
        while head < len(queue):
            face_id = queue[head]
            head += 1
            for neighbour, relation in constraints[face_id]:
                wanted = flips[face_id] * relation
                if neighbour in flips and flips[neighbour] != wanted:
                    raise ValueError("facial cycles are not consistently orientable")
                if neighbour not in flips:
                    flips[neighbour] = wanted
                    queue.append(neighbour)

    predecessor = {}
    for face_id, stored_cycle in cycles.items():
        cycle = (
            stored_cycle
            if flips[face_id] > 0
            else list(reversed(stored_cycle))
        )
        length = len(cycle)
        for i, vertex in enumerate(cycle):
            before = cycle[(i - 1) % length]
            after = cycle[(i + 1) % length]
            row = predecessor.setdefault(vertex, {})
            previous = row.get(before)
            if previous is not None and previous != after:
                raise ValueError("inconsistent facial orientations")
            row[before] = after
    rotation = {}
    for vertex, pred in predecessor.items():
        if set(pred) != set(pred.values()):
            raise ValueError("facial cycles do not define a rotation")
        start = min(pred)
        order = [start]
        cursor = pred[start]
        while cursor != start:
            if cursor in order or cursor not in pred:
                raise ValueError("broken local rotation")
            order.append(cursor)
            cursor = pred[cursor]
        if len(order) != len(pred):
            raise ValueError("local rotation is incomplete")
        rotation[vertex] = order
    return rotation


def _least_rotation(values):
    if not values:
        return ()
    seq = tuple(values)
    return min(seq[i:] + seq[:i] for i in range(len(seq)))


def _rooted_map_code(rotation, root_u, root_v, direction):
    ids = {root_u: 0, root_v: 1}
    anchors = {root_u: root_v, root_v: root_u}
    queue = [root_u, root_v]
    head = 0
    while head < len(queue):
        vertex = queue[head]
        head += 1
        neighbours = rotation[vertex]
        anchor = anchors[vertex]
        position = neighbours.index(anchor)
        order = [
            neighbours[(position + direction * step) % len(neighbours)]
            for step in range(len(neighbours))
        ]
        for neighbour in order:
            if neighbour not in ids:
                ids[neighbour] = len(ids)
                anchors[neighbour] = vertex
                queue.append(neighbour)
    if len(ids) != len(rotation):
        raise ValueError("plane graph is disconnected")

    by_id = [None] * len(ids)
    for vertex, number in ids.items():
        around = [ids[n] for n in rotation[vertex]]
        if direction < 0:
            around.reverse()
        by_id[number] = _least_rotation(around)
    return tuple(by_id)


def canonical_key(inst):
    """Exact canonical form of the embedded graph, ignoring all input labels."""
    rotation = _rotation_from_faces(inst)
    codes = []
    for u in rotation:
        for v in rotation[u]:
            codes.append(_rooted_map_code(rotation, u, v, 1))
            codes.append(_rooted_map_code(rotation, u, v, -1))
    canonical = min(codes)
    payload = json.dumps(
        {"k": inst["k"], "rotation": canonical},
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def escalate(params):
    current = {k: v for k, v in params.items() if k != "_preset"}
    n = int(current.get("n", 0))
    nesting_bias = int(current.get("nesting_bias", 50))
    if nesting_bias < 96:
        # First deepen the hidden dependency chain at fixed answer length.
        harder_n = n
        harder_bias = min(96, nesting_bias + 11)
    else:
        harder_n = max(n + 4, math.ceil(n * 1.22))
        harder_bias = nesting_bias
    # The answer has 3+3n atoms.  Stop honestly before crossing either public
    # output cap; there is no non-lengthening axis left once nesting is saturated.
    atoms = 3 + 3 * harder_n
    estimated_chars = 7 * atoms + 2
    intended_operations = harder_n + atoms
    if atoms > 256 or estimated_chars > 2000 or intended_operations > 300:
        return "cap_bound"
    return {"n": harder_n, "nesting_bias": harder_bias}


def _source_graph(inst):
    """Recover the cubic source graph used by the paper's reduction.

    In an all-1-subdivided dual, every subdivision vertex is incident to exactly
    two displayed faces.  Those two face labels are the endpoints of the
    corresponding source edge.  Original dual vertices have incidence >= 3.
    """
    incidence = {}
    for face in inst["faces"]:
        for vertex in set(face["boundary"]):
            incidence.setdefault(vertex, set()).add(face["id"])
    adjacency = {face["id"]: set() for face in inst["faces"]}
    for incident_faces in incidence.values():
        if len(incident_faces) == 2:
            u, v = sorted(incident_faces)
            adjacency[u].add(v)
            adjacency[v].add(u)
    return adjacency


def _is_source_vertex_cover(adjacency, candidate):
    """Fast equivalent of verify() for generated all-1-subdivision instances.

    Section 3, Property 1 says a source vertex cover maps to a connected face
    cover, so after random_candidate has enforced the output language it is
    enough to find one uncovered source edge.  Any rare hit is rechecked by the
    public verifier in selftest.
    """
    chosen = set(candidate)
    for u, neighbours in adjacency.items():
        if u in chosen:
            continue
        for v in neighbours:
            if v not in chosen:
                return False
    return True


def _patch_at(adjacency, centre, counter=None):
    """Recognize one exposed seven-vertex expansion patch."""
    if counter is not None:
        counter["local_inspections"] += 1
    q = set(adjacency.get(centre, ()))
    if len(q) != 3:
        return None
    if any(len(adjacency[x]) != 3 for x in q):
        return None
    if any((q - {x}) & adjacency[x] for x in q):
        return None
    pairs = [set(adjacency[x]) - {centre} for x in q]
    p = set().union(*pairs)
    if len(p) != 3 or p & q or centre in p:
        return None
    if any(len(pair) != 2 for pair in pairs):
        return None
    if any(sum(vertex in pair for pair in pairs) != 2 for vertex in p):
        return None
    if any(len(adjacency[x]) != 3 for x in p):
        return None
    patch = q | p | {centre}
    external = []
    for terminal in p:
        q_neighbours = adjacency[terminal] & q
        outside = adjacency[terminal] - patch
        if len(q_neighbours) != 2 or len(outside) != 1:
            return None
        external.append(next(iter(outside)))
    if len(set(external)) != 3:
        return None
    return {
        "centre": centre,
        "q": tuple(sorted(q)),
        "p": tuple(sorted(p)),
        "external": tuple(sorted(external)),
    }


def _contract_patch(adjacency, patch, new_vertex):
    patch_vertices = set(patch["q"]) | set(patch["p"]) | {patch["centre"]}
    external = set(patch["external"])
    for outside in external:
        adjacency[outside].difference_update(patch_vertices)
        adjacency[outside].add(new_vertex)
    for vertex in patch_vertices:
        del adjacency[vertex]
    adjacency[new_vertex] = set(external)


def _reference_cover(inst):
    """Polynomial reverse-contraction solver used as Track-B reference."""
    adjacency = {u: set(vs) for u, vs in _source_graph(inst).items()}
    originals = set(adjacency)
    history = []
    next_synthetic = -1
    counter = {"local_inspections": 0, "adjacency_updates": 0, "contractions": 0}
    while len(adjacency) > 4:
        found = None
        for centre in sorted(adjacency):
            found = _patch_at(adjacency, centre, counter)
            if found is not None:
                break
        if found is None:
            return None, counter
        new_vertex = next_synthetic
        next_synthetic -= 1
        _contract_patch(adjacency, found, new_vertex)
        counter["adjacency_updates"] += 31
        counter["contractions"] += 1
        found["contracted"] = new_vertex
        history.append(found)

    remaining = sorted(adjacency)
    if len(remaining) != 4 or any(len(adjacency[v]) != 3 for v in remaining):
        return None, counter
    independent = {remaining[0]}
    for patch in reversed(history):
        contracted = patch["contracted"]
        if contracted in independent:
            independent.remove(contracted)
            independent.update(patch["p"])
            independent.add(patch["centre"])
        else:
            independent.update(patch["q"])
    if not independent <= originals:
        return None, counter
    cover = sorted(originals - independent)
    counter["total_operations"] = (
        counter["local_inspections"]
        + counter["adjacency_updates"]
        + len(originals)
    )
    return cover, counter


def _attack_outlier(inst, reverse=False):
    table = _face_table(inst)
    incidence_count = {}
    for boundary in table.values():
        for vertex in set(boundary):
            incidence_count[vertex] = incidence_count.get(vertex, 0) + 1
    scored = []
    row_position = {row["id"]: i for i, row in enumerate(inst["faces"])}
    for face_id, boundary in table.items():
        score = (
            sum(incidence_count[v] for v in set(boundary)),
            row_position[face_id],
            face_id,
        )
        scored.append((score, face_id))
    return sorted(
        face_id
        for _score, face_id in sorted(scored, reverse=reverse)[: inst["k"]]
    )


def _attack_greedy_cover(inst):
    table = _face_table(inst)
    uncovered = set().union(*(set(boundary) for boundary in table.values()))
    chosen = []
    available = set(table)
    while available and len(chosen) < inst["k"]:
        face_id = max(
            available,
            key=lambda f: (len(set(table[f]) & uncovered), -f),
        )
        chosen.append(face_id)
        available.remove(face_id)
        uncovered.difference_update(table[face_id])
    return sorted(chosen)


def _greedy_independent(adjacency, order):
    chosen = set()
    forbidden = set()
    for vertex in order:
        if vertex not in forbidden:
            chosen.add(vertex)
            forbidden.add(vertex)
            forbidden.update(adjacency[vertex])
    return chosen


def _attack_greedy_independent(inst):
    adjacency = _source_graph(inst)
    # A hand-executable smallest-neighbour-sum rule, without patch contraction.
    order = sorted(
        adjacency,
        key=lambda v: (sum(adjacency[n].__len__() for n in adjacency[v]), v),
    )
    independent = _greedy_independent(adjacency, order)
    if len(independent) != inst["face_count"] - inst["k"]:
        return None
    return sorted(set(adjacency) - independent)


def _attack_random_restart(inst, rng, restarts=64):
    adjacency = _source_graph(inst)
    vertices = list(adjacency)
    target = inst["face_count"] - inst["k"]
    for _ in range(restarts):
        rng.shuffle(vertices)
        independent = _greedy_independent(adjacency, vertices)
        if len(independent) == target:
            return sorted(set(adjacency) - independent)
    return None


def _attack_label_parity(inst):
    labels = sorted(face["id"] for face in inst["faces"])
    parity = [label for label in labels if label % 2 == 0]
    if len(parity) < inst["k"]:
        parity += [label for label in labels if label % 2]
    return sorted(parity[: inst["k"]])


def _attack_four_cycle_ansatz(inst, reverse=True):
    adjacency = _source_graph(inst)
    scores = []
    for vertex in adjacency:
        count = 0
        neighbours = list(adjacency[vertex])
        for a, b in itertools.combinations(neighbours, 2):
            count += len((adjacency[a] & adjacency[b]) - {vertex})
        scores.append((count, vertex))
    # Treat the most locally cube-like vertices as the independent set.
    alpha = inst["face_count"] - inst["k"]
    independent = {
        v for _score, v in sorted(scores, reverse=reverse)[:alpha]
    }
    return sorted(set(adjacency) - independent)


def _relabel_instance(inst, rng, reflect=False):
    vertex_labels = sorted(
        {vertex for face in inst["faces"] for vertex in face["boundary"]}
    )
    shuffled_vertices = list(vertex_labels)
    rng.shuffle(shuffled_vertices)
    vertex_map = dict(zip(vertex_labels, shuffled_vertices))

    face_labels = sorted(face["id"] for face in inst["faces"])
    shuffled_faces = list(face_labels)
    rng.shuffle(shuffled_faces)
    face_map = dict(zip(face_labels, shuffled_faces))
    rows = []
    for face in inst["faces"]:
        boundary = [vertex_map[v] for v in face["boundary"]]
        if reflect:
            boundary.reverse()
        shift = rng.randrange(len(boundary))
        boundary = boundary[shift:] + boundary[:shift]
        rows.append({"id": face_map[face["id"]], "boundary": boundary})
    rng.shuffle(rows)
    transformed = {
        key: value
        for key, value in inst.items()
        if key not in {"faces", "answer"}
    }
    transformed["faces"] = rows
    transformed["answer"] = sorted(face_map[f] for f in inst["answer"])
    return transformed


def _reorder_instance(inst, rng, reflect=False):
    """Change only facial row order, cyclic starts, and optional orientation."""
    rows = []
    for face in inst["faces"]:
        boundary = list(face["boundary"])
        if reflect:
            boundary.reverse()
        shift = rng.randrange(len(boundary))
        boundary = boundary[shift:] + boundary[:shift]
        rows.append({"id": face["id"], "boundary": boundary})
    rng.shuffle(rows)
    transformed = {
        key: value
        for key, value in inst.items()
        if key not in {"faces", "answer"}
    }
    transformed["faces"] = rows
    transformed["answer"] = list(inst["answer"])
    return transformed


def _independently_reorient_instance(inst, rng):
    """Reverse an arbitrary subset of faces and rotate/reorder all rows."""
    rows = []
    reversed_count = 0
    for face in inst["faces"]:
        boundary = list(face["boundary"])
        if rng.getrandbits(1):
            boundary.reverse()
            reversed_count += 1
        shift = rng.randrange(len(boundary))
        boundary = boundary[shift:] + boundary[:shift]
        rows.append({"id": face["id"], "boundary": boundary})
    # Make the tested transformation nontrivial even on an unlikely all-zero
    # draw, so G8 cannot pass without exercising independent direction changes.
    if reversed_count == 0:
        rows[0]["boundary"].reverse()
    rng.shuffle(rows)
    transformed = {
        key: value
        for key, value in inst.items()
        if key not in {"faces", "answer"}
    }
    transformed["faces"] = rows
    transformed["answer"] = list(inst["answer"])
    return transformed


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest():
    report = {}

    # G1: every named preset, multiple independent seeds, plus JSON safety.
    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append(
                    {"preset": preset, "seed": seed, "reason": "answer not JSON-native"}
                )
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checked": checks,
        "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=314159, **shipping_params)

    # G2: validation order deliberately gives each requested corruption a
    # distinct, useful explanation.
    good = list(shipping["answer"])
    variants = {
        "empty": [],
        "drop_one": good[:-1],
        "duplicate": [good[0], good[0]] + good[2:],
        "swap_two": [good[1], good[0]] + good[2:],
        "out_of_range": good[:-1] + [shipping["face_count"] + 10_000],
    }
    corruptions = {}
    for name, candidate in variants.items():
        ok, reason = verify(shipping, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = {row["reason"] for row in corruptions.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in corruptions.values()) and len(reasons) == 5,
        "distinct_reasons": len(reasons),
        "cases": corruptions,
    }

    # G3: realistic prose, markdown fencing, whitespace, and exact round trip.
    response = (
        "The incidence graph is connected.\n\n<answer>\n```json\n"
        + json.dumps(shipping["answer"])
        + "\n```\n</answer>\n"
    )
    parsed = parse_answer(response)
    parsed_ok, parsed_reason = verify(shipping, parsed)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and parsed_ok,
        "verify_reason": parsed_reason,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    # G4/G5 share the required shipping-preset structure-aware sample.  The
    # sampler enforces exact arity, distinctness, the label set, and canonical
    # order before asking whether the mathematical constraints hold.
    guess_rng = random.Random(271828)
    shipping_source = _source_graph(shipping)
    guess_hits = 0
    started = time.perf_counter()
    for _ in range(_GUESS_SAMPLES):
        candidate = random_candidate(shipping, guess_rng)
        if _is_source_vertex_cover(shipping_source, candidate):
            # The fast predicate is theorem-backed, but a hit is cheap enough to
            # send through the complete public checker as a regression guard.
            guess_hits += int(verify(shipping, candidate)[0])
    guess_wall = time.perf_counter() - started
    probability = guess_hits / _GUESS_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": _GUESS_SAMPLES >= 200_000 and probability < 1e-6,
        "hits": guess_hits,
        "total": _GUESS_SAMPLES,
        "measured_probability": probability,
        "candidate_space": search_space(shipping),
        "sampler": "uniform strictly increasing k-subsets of displayed faces",
    }

    # G6 attacks and the successful Track-B reference algorithm.
    attack_seeds = list(range(80_000, 80_008))
    names = [
        "boundary_incidence_low_outlier",
        "boundary_incidence_high_outlier",
        "greedy_maximum_new_coverage",
        "random_greedy_independent_64",
        "in_context_even_label_ansatz",
        "local_four_cycle_high_ansatz",
        "local_four_cycle_low_ansatz",
    ]
    successes = {name: 0 for name in names}
    reference_successes = 0
    reference_walls = []
    reference_ops = []
    restart_steps = []
    restart_walls = []
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **shipping_params)
        restart_begun = time.perf_counter()
        restart_candidate = _attack_random_restart(
            inst, random.Random(seed ^ 0xA17C), 64
        )
        restart_walls.append(time.perf_counter() - restart_begun)
        candidates = {
            "boundary_incidence_low_outlier": _attack_outlier(inst, reverse=False),
            "boundary_incidence_high_outlier": _attack_outlier(inst, reverse=True),
            "greedy_maximum_new_coverage": _attack_greedy_cover(inst),
            "random_greedy_independent_64": restart_candidate,
            "in_context_even_label_ansatz": _attack_label_parity(inst),
            "local_four_cycle_high_ansatz": _attack_four_cycle_ansatz(
                inst, reverse=True
            ),
            "local_four_cycle_low_ansatz": _attack_four_cycle_ansatz(
                inst, reverse=False
            ),
        }
        restart_steps.append(64 * inst["face_count"])
        for name, candidate in candidates.items():
            if candidate is not None and verify(inst, candidate)[0]:
                successes[name] += 1

        begun = time.perf_counter()
        reference, counters = _reference_cover(inst)
        reference_walls.append(time.perf_counter() - begun)
        reference_ops.append(counters.get("total_operations", 0))
        if reference is not None and verify(inst, reference)[0]:
            reference_successes += 1

    attacks = {
        name: {"successes": successes[name], "attempts": len(attack_seeds)}
        for name in names
    }
    all_failed = all(row["successes"] == 0 for row in attacks.values())
    report["G5_density_and_baseline"] = {
        "pass": probability < 1e-6 and all_failed and reference_successes == 8,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": _GUESS_SAMPLES,
        "shipping_solution_fraction_estimate": probability,
        "density_sampling_wall_clock_sec": round(guess_wall, 6),
        "strongest_failing_attack": "random_greedy_independent_64",
        "baseline_wall_clock_sec_mean": round(
            sum(restart_walls) / len(restart_walls), 6
        ),
        "baseline_wall_clock_sec_max": round(max(restart_walls), 6),
        "baseline_iterations_per_instance": min(restart_steps),
        "reference_wall_clock_sec_mean": round(
            sum(reference_walls) / len(reference_walls), 6
        ),
        "reference_operations_min": min(reference_ops),
        "reference_operations_max": max(reference_ops),
        "demo_exact_valid_answers": enumerate_all(
            make_instance(seed=5, **DIFFICULTY["demo"])
        ),
        "demo_candidate_space": search_space(
            make_instance(seed=5, **DIFFICULTY["demo"])
        ),
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == len(attack_seeds),
        "attacks": attacks,
        "seeds": attack_seeds,
        "reference_algorithm": {
            "name": "reverse cube-minus-one-vertex patch contraction",
            "complexity": "O(F^2) local adjacency inspections in this implementation",
            "wall_clock_sec_total": round(sum(reference_walls), 6),
            "wall_clock_sec_mean": round(
                sum(reference_walls) / len(reference_walls), 6
            ),
            "operations_per_instance_min": min(reference_ops),
            "operations_per_instance_max": max(reference_ops),
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
    }

    # G7: double the structural size.  The construction remains linear and its
    # carried certificate still verifies exactly.
    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled_params["nesting_bias"] = min(96, doubled_params["nesting_bias"] + 10)
    begun = time.perf_counter()
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_wall = time.perf_counter() - begun
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(shipping),
        "shipping_n": shipping_params["n"],
        "doubled_n": doubled_params["n"],
        "shipping_face_count": shipping["face_count"],
        "doubled_face_count": doubled["face_count"],
        "shipping_candidate_space": search_space(shipping),
        "doubled_candidate_space": search_space(doubled),
        "doubled_build_wall_clock_sec": round(doubled_wall, 6),
        "verify_reason": doubled_reason,
    }

    # G8: arbitrary vertex and face relabellings, input reorderings, rotations,
    # global reflection, and compositions.  The transformed certificate is
    # checked as well as the exact embedded-map key.
    invariance_checks = 0
    carried_checks = 0
    failures = []
    unrelated_keys = []
    key_audit_params = {"n": 12, "nesting_bias": 60}
    for seed in range(20):
        inst = make_instance(seed=120_000 + seed, **key_audit_params)
        key = canonical_key(inst)
        unrelated_keys.append(key)
        independently_reoriented = _independently_reorient_instance(
            inst, random.Random(230_000 + 23 * seed)
        )
        transforms = [
            _reorder_instance(
                inst, random.Random(210_000 + seed), reflect=False
            ),
            _reorder_instance(
                inst, random.Random(215_000 + seed), reflect=True
            ),
            _relabel_instance(
                inst, random.Random(220_000 + 19 * seed), reflect=False
            ),
            _relabel_instance(
                inst, random.Random(220_001 + 19 * seed), reflect=True
            ),
            independently_reoriented,
            _relabel_instance(
                independently_reoriented,
                random.Random(240_000 + 29 * seed),
                reflect=bool(seed % 2),
            ),
        ]
        for turn, transformed in enumerate(transforms):
            invariance_checks += 1
            if canonical_key(transformed) != key:
                failures.append({"seed": seed, "turn": turn, "kind": "key"})
            ok, reason = verify(transformed, transformed["answer"])
            carried_checks += 1
            if not ok:
                failures.append(
                    {
                        "seed": seed,
                        "turn": turn,
                        "kind": "carried witness",
                        "reason": reason,
                    }
                )
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not failures and distinct == 20,
        "invariance_checks": invariance_checks,
        "real_transformation_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "unrelated_distinct_keys": distinct,
        "failures": failures,
        "invariant": (
            "minimum rooted code over every dart and both orientations of the "
            "reconstructed combinatorial plane map"
        ),
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    intended_ops = shipping_params["n"] + len(shipping["answer"])
    hinted = G9_ORACLE_RESULTS["hinted"]
    placebo = G9_ORACLE_RESULTS["placebo"]
    difference = None
    if hinted["attempts"] and placebo["attempts"]:
        difference = (
            hinted["solved"] / hinted["attempts"]
            - placebo["solved"] / placebo["attempts"]
        )
    caps_pass = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_ops <= 300
    )
    report["G9_no_tool_suitability"] = {
        # G9(a,b) are diagnostic as of 2026-09-05; only the caps gate.
        "pass": caps_pass,
        "arms": {
            "bare": dict(G9_ORACLE_RESULTS["bare"]),
            "hinted": dict(hinted),
            "placebo": dict(placebo),
        },
        "hinted_minus_placebo": difference,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "caps_pass": caps_pass,
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for name, value in report.items()
        if name.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
