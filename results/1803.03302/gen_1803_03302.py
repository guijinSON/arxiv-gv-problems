"""Verified Track-B generator for arXiv:1803.03302.

The paper turns a voxelized square-panel surface into its face-adjacency graph
and asks for a Hamiltonian cycle (a one-strip mesh stripification).  This
module grows a genuine voxel polycube one cube at a time.  A Hamiltonian cycle
of its exposed square faces is carried through every attachment by replacing
the covered face with a Hamiltonian path through the five newly exposed faces.
No generated instance is solved in order to obtain its stored certificate.
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
try:  # The family is integer/combinatorial and does not require these helpers.
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - standard-library-only fallback
    exact_matrices = rationals = None


TRACK = "B"

# Direction order is part of the exact panel encoding.
DIRS = (
    (1, 0, 0), (-1, 0, 0),
    (0, 1, 0), (0, -1, 0),
    (0, 0, 1), (0, 0, -1),
)
DIR_NAMES = ("+x", "-x", "+y", "-y", "+z", "-z")
OPPOSITE = (1, 0, 3, 2, 5, 4)


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _face_corners(face):
    """Four integer corners of (cube_x,cube_y,cube_z,direction)."""
    x, y, z, d = face
    if d == 0:
        return ((x + 1, y, z), (x + 1, y + 1, z),
                (x + 1, y + 1, z + 1), (x + 1, y, z + 1))
    if d == 1:
        return ((x, y, z), (x, y, z + 1),
                (x, y + 1, z + 1), (x, y + 1, z))
    if d == 2:
        return ((x, y + 1, z), (x, y + 1, z + 1),
                (x + 1, y + 1, z + 1), (x + 1, y + 1, z))
    if d == 3:
        return ((x, y, z), (x + 1, y, z),
                (x + 1, y, z + 1), (x, y, z + 1))
    if d == 4:
        return ((x, y, z + 1), (x + 1, y, z + 1),
                (x + 1, y + 1, z + 1), (x, y + 1, z + 1))
    return ((x, y, z), (x, y + 1, z),
            (x + 1, y + 1, z), (x + 1, y, z))


def _surface(cubes):
    occupied = set(cubes)
    faces = set()
    for x, y, z in cubes:
        for d, delta in enumerate(DIRS):
            if (x + delta[0], y + delta[1], z + delta[2]) not in occupied:
                faces.add((x, y, z, d))
    return faces


def _surface_adjacency(faces):
    faces = set(faces)
    edge_faces = {}
    for face in faces:
        corners = _face_corners(face)
        for i in range(4):
            edge = tuple(sorted((corners[i], corners[(i + 1) % 4])))
            edge_faces.setdefault(edge, []).append(face)
    if any(len(pair) != 2 for pair in edge_faces.values()):
        raise ValueError("voxel boundary is not a closed two-manifold")
    adjacency = {face: set() for face in faces}
    for pair in edge_faces.values():
        a, b = pair
        adjacency[a].add(b)
        adjacency[b].add(a)
    if any(len(neighbors) != 4 for neighbors in adjacency.values()):
        raise ValueError("every square panel must have four edge-neighbors")
    return adjacency


def _patch_path(new_faces, entry, exit_, adjacency, rng):
    middle = sorted(set(new_faces) - {entry, exit_})
    paths = []
    for order in itertools.permutations(middle):
        path = (entry,) + order + (exit_,)
        if all(path[i + 1] in adjacency[path[i]]
               for i in range(len(path) - 1)):
            paths.append(path)
    if not paths:
        raise AssertionError("the five-face attachment patch did not splice")
    return list(paths[rng.randrange(len(paths))])


def _build_native(cube_count, rng):
    """Grow a monotone voxel chain and carry a face Hamiltonian cycle."""
    cubes = [(0, 0, 0)]
    # A cube's face graph is an octahedron; consecutive entries are never
    # opposite faces, including the last-to-first pair.
    cycle = [(0, 0, 0, d) for d in (0, 2, 1, 4, 3, 5)]
    steps = []
    for _ in range(cube_count - 1):
        d = rng.choice((0, 2))  # monotone +x/+y keeps the cube adjacency a path
        old_cube = cubes[-1]
        new_cube = _add(old_cube, DIRS[d])
        old_faces = _surface(cubes)
        glue = old_cube + (d,)
        if glue not in old_faces:
            raise AssertionError("chain attachment face is not exposed")
        index = cycle.index(glue)
        before = cycle[index - 1]
        after = cycle[(index + 1) % len(cycle)]

        cubes.append(new_cube)
        steps.append(d)
        new_surface = _surface(cubes)
        adjacency = _surface_adjacency(new_surface)
        patch = [new_cube + (side,) for side in range(6)
                 if side != OPPOSITE[d]]
        entries = [face for face in patch if before in adjacency[face]]
        exits = [face for face in patch if after in adjacency[face]]
        if len(entries) != 1 or len(exits) != 1 or entries[0] == exits[0]:
            raise AssertionError("attachment ports are not the expected side faces")
        replacement = _patch_path(
            patch, entries[0], exits[0], adjacency, rng
        )
        cycle[index:index + 1] = replacement

    faces = _surface(cubes)
    adjacency = _surface_adjacency(faces)
    if len(cycle) != len(faces) or set(cycle) != faces:
        raise AssertionError("carried cycle does not cover the final surface")
    if not all(cycle[(i + 1) % len(cycle)] in adjacency[cycle[i]]
               for i in range(len(cycle))):
        raise AssertionError("carried cycle contains a non-hinge transition")
    return cubes, steps, faces, adjacency, cycle


def make_instance(n, seed=0, **params):
    """Construct a voxel-chain surface and its cycle by local certificate splices."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError("n must be a positive integer cube count")
    rng = random.Random(seed)
    cubes, steps, faces, adjacency, cycle = _build_native(n, rng)

    ordered_faces = sorted(faces)
    labels = list(range(len(ordered_faces)))
    rng.shuffle(labels)
    face_to_label = dict(zip(ordered_faces, labels))
    panels = [None] * len(ordered_faces)
    for face in ordered_faces:
        label = face_to_label[face]
        panels[label] = {
            "cube": [face[0], face[1], face[2]],
            "normal": DIR_NAMES[face[3]],
            "neighbors": sorted(face_to_label[v] for v in adjacency[face]),
        }
    answer = [face_to_label[face] for face in cycle]
    # Normalise rotation and reversal, which changes no undirected cycle.
    pivot = answer.index(0)
    answer = answer[pivot:] + answer[:pivot]
    if answer[-1] < answer[1]:
        answer = [answer[0]] + list(reversed(answer[1:]))
    return {
        "cube_count": n,
        "panel_count": len(panels),
        "cubes": [list(cube) for cube in cubes],
        "panels": panels,
        "answer": answer,
    }


def _adjacency_from_instance(inst):
    panels = inst.get("panels")
    if not isinstance(panels, list):
        return None, "panels must be a list"
    count = inst.get("panel_count")
    if count != len(panels):
        return None, "panel count does not match the panel list"
    adjacency = []
    face_to_label = {}
    name_to_direction = {name: i for i, name in enumerate(DIR_NAMES)}
    for i, panel in enumerate(panels):
        if not isinstance(panel, dict) or not isinstance(panel.get("neighbors"), list):
            return None, f"panel {i} is malformed"
        cube = panel.get("cube")
        normal = panel.get("normal")
        if (not isinstance(cube, list) or len(cube) != 3
                or any(not isinstance(x, int) or isinstance(x, bool) for x in cube)
                or normal not in name_to_direction):
            return None, f"panel {i} has malformed exact geometry"
        face = (cube[0], cube[1], cube[2], name_to_direction[normal])
        if face in face_to_label:
            return None, f"panels {face_to_label[face]} and {i} duplicate one square"
        face_to_label[face] = i
        row = panel["neighbors"]
        if len(row) != 4 or len(set(row)) != 4:
            return None, f"panel {i} does not have four distinct neighbors"
        if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 or v >= count
               for v in row):
            return None, f"panel {i} has an invalid neighbor"
        adjacency.append(set(row))
    for u, row in enumerate(adjacency):
        for v in row:
            if u not in adjacency[v]:
                return None, f"hinge {u}-{v} is not symmetric"
    cubes = inst.get("cubes")
    if (not isinstance(cubes, list)
            or any(not isinstance(c, list) or len(c) != 3
                   or any(not isinstance(x, int) or isinstance(x, bool) for x in c)
                   for c in cubes)):
        return None, "cube list is malformed"
    cube_tuples = [tuple(c) for c in cubes]
    if len(set(cube_tuples)) != len(cube_tuples):
        return None, "cube list contains a duplicate voxel"
    true_faces = _surface(cube_tuples)
    if set(face_to_label) != true_faces:
        return None, "panel geometry is not exactly the exposed voxel surface"
    try:
        geometric = _surface_adjacency(true_faces)
    except ValueError as exc:
        return None, str(exc)
    for face, label in face_to_label.items():
        expected = {face_to_label[other] for other in geometric[face]}
        if adjacency[label] != expected:
            return None, f"panel {label} neighbor list disagrees with shared edges"
    return adjacency, "ok"


def verify(inst, answer):
    """Check any normalised Hamiltonian cycle; never consult inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    count = inst.get("panel_count")
    if not isinstance(count, int):
        return False, "instance panel count is malformed"
    if len(answer) == 0:
        return False, "cycle must not be empty"
    if len(answer) < count:
        return False, "cycle omits one or more panels"
    if len(answer) > count:
        return False, "cycle repeats or adds panels"
    if any(not isinstance(v, int) or isinstance(v, bool) for v in answer):
        return False, "every panel id must be an integer"
    if any(v < 0 or v >= count for v in answer):
        return False, "panel id is out of range"
    if len(set(answer)) != count:
        return False, "a panel id is duplicated"
    if answer[0] != 0:
        return False, "normalised cycle must start with panel 0"
    if answer[1] > answer[-1]:
        return False, "normalised cycle must use the smaller neighbor second"
    adjacency, reason = _adjacency_from_instance(inst)
    if adjacency is None:
        return False, reason
    for i, u in enumerate(answer):
        v = answer[(i + 1) % count]
        if v not in adjacency[u]:
            return False, f"panels {u} and {v} do not share a hinge"
    return True, "ok"


PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "voxel polycube surface with exact integer square-panel coordinates",
        "dual face-adjacency graph of the square-panel surface",
        "Hamiltonian panel cycle",
    ],
    "verification_operations": [
        "exact integer reconstruction of exposed voxel faces",
        "exact shared-edge comparison",
        "permutation and graph-cycle checks",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Mesh Stripification, Section (B), page 9: a one-strip quadrilateral "
        "mesh is represented as a Hamiltonian cycle of its face-adjacency graph."
    ),
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Recognize that the voxel solid is an attachment chain and splice the "
        "five newly exposed faces in place of each covered face; without this "
        "decomposition one must run a general Hamiltonian-cycle method."
    ),
    "hardness_basis": (
        "Track B: the paper uses the Concorde TSP solver and reports almost-linear "
        "empirical growth, while the disclosed standard 2-factor/merge reference "
        "algorithm runs in O(R*F^3) time; at the 254-panel hard preset it measured "
        "an upper-median 7,506,977 primitive operations and 0.898 seconds over eight "
        "seeds (maximum 166,296,780 operations and 21.635 seconds), whereas recognizing "
        "the attachment decomposition leaves 186 local splice decisions."
    ),
    "max_answer_tokens": 227,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 1},
    "easy": {"n": 47},
    "medium": {"n": 55},
    "hard": {"n": 63},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The voxel centers form an attachment chain whose covered face is replaced "
    "by a five-face surface patch."
)
PLACEBO_HINT = (
    "Careful bookkeeping of panel labels and hinge endpoints helps avoid "
    "transcription mistakes in the final cycle."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON permutation of all F panel ids, normalised to start with 0 and "
        "to place the smaller of panel 0's two cycle-neighbors second; ids are "
        "the integers 0 through F-1 with no repeats."
    ),
    "bounds": {
        "shape": "normalised permutation",
        "panel_ids": "0..F-1",
        "max_atomic_elements_at_shipping": 254,
    },
}

NOTES = (
    "Section (A), page 5 fixes the native objects as exposed unit square faces "
    "of a voxelization, each with four edge-neighbors. Section (B), page 9 "
    "licenses the dual-graph Hamiltonian-cycle formulation and supplies the "
    "STEP-0 easy result: Taubin's triangulated-quad construction is linear and "
    "the authors' Concorde runs grow almost linearly, so Track A is unavailable. "
    "Theorem 1 directly stacks every strip into one or two piles, which makes "
    "stacking itself unsuitable for Track A; Theorem 2 gives O(n) feasibility "
    "checking but no cheap optimality certificate. The generator therefore uses "
    "a Track-B transformation-of-a-known-instance: attaching one cube removes "
    "one surface face and adds a five-face wheel patch that has a spanning path "
    "between either pair of attachment ports. Panel labels are uniformly "
    "shuffled, every panel has degree four, and all cubes/panels come from the "
    "same construction. Geometric sorting, smallest-label greedy traversal, "
    "random self-avoiding walks, and a fixed local-face ansatz are measured in "
    "G6; the paper-cited 2-factor-and-merge approach is disclosed separately as "
    "the successful Track-B reference algorithm."
)

# Filled after the three isolated harden.py runs. These are diagnostics; only
# the answer and intended-route caps gate G9.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


def render(inst):
    """Render a self-contained square-panel Hamiltonian-strip problem."""
    lines = [
        "Voxel-surface one-strip problem",
        "",
        "A voxel is the closed unit cube [x,x+1] x [y,y+1] x [z,z+1] "
        "with integer origin (x,y,z). The voxel solid below is the union of "
        "the listed voxels. A panel is one exposed unit-square face of that "
        "solid. Two panels share a hinge exactly when their squares share one "
        "complete unit edge. The supplied neighbor lists record those hinges; "
        "each panel has exactly four distinct neighbors.",
        "",
        "Find one Hamiltonian panel cycle: a cyclic ordering that contains every "
        "panel id exactly once and whose consecutive panels, including the last "
        "and first, share a hinge. Panel ids are 0-based. Order is cyclic and "
        "reversal ordinarily does not matter, so normalise the answer by putting "
        "panel 0 first and putting the smaller of its two cycle-neighbors second.",
        "",
        "A panel row is: id | owning voxel origin | outward normal | four neighbors.",
        "The order of voxel rows, panel rows, and neighbor ids carries no meaning.",
        "",
        "Voxels (integer origins):",
        " ".join("(%d,%d,%d)" % tuple(cube) for cube in inst["cubes"]),
        "",
        f"Panels ({inst['panel_count']} total):",
    ]
    for panel_id, panel in enumerate(inst["panels"]):
        cube = panel["cube"]
        neighbors = ",".join(str(v) for v in panel["neighbors"])
        lines.append(
            f"{panel_id} | ({cube[0]},{cube[1]},{cube[2]}) | "
            f"{panel['normal']} | {neighbors}"
        )
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags, as one JSON "
        f"list of exactly {inst['panel_count']} integers satisfying the "
        "normalisation above.",
        "Example format: <answer>[0,3,17,2]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


_ANSWER_RE = re.compile(r"<answer>(.*?)</answer>", re.IGNORECASE | re.DOTALL)


def parse_answer(text):
    """Parse a tagged JSON integer list, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if (not isinstance(value, list)
            or any(not isinstance(v, int) or isinstance(v, bool) for v in value)):
        return None
    return value


def random_candidate(inst, rng):
    """Uniformly sample the stated normalised-permutation language."""
    count = inst["panel_count"]
    tail = list(range(1, count))
    rng.shuffle(tail)
    candidate = [0] + tail
    if candidate[1] > candidate[-1]:
        candidate = [0] + list(reversed(candidate[1:]))
    return candidate


def search_space(inst):
    count = inst["panel_count"]
    if count <= 2:
        return 1
    return math.factorial(count - 1) // 2


def enumerate_all(inst):
    """Count normalised valid cycles exactly only below a fixed work cap."""
    count = inst["panel_count"]
    space = search_space(inst)
    if space > 500_000:
        return None
    hits = 0
    for tail in itertools.permutations(range(1, count)):
        if tail[0] > tail[-1]:
            continue
        hits += int(verify(inst, [0] + list(tail))[0])
    return hits


def _canonical_cubes(cubes):
    """Canonical voxel set under translations and all 48 cube symmetries."""
    points = [tuple(c) for c in cubes]
    forms = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((-1, 1), repeat=3):
            transformed = []
            for point in points:
                # Transform doubled cell centers, then recover cell origins.
                center = [2 * point[i] + 1 for i in range(3)]
                out = [signs[j] * center[perm[j]] for j in range(3)]
                transformed.append(tuple((value - 1) // 2 for value in out))
            mins = tuple(min(p[j] for p in transformed) for j in range(3))
            forms.append(tuple(sorted(
                tuple(p[j] - mins[j] for j in range(3))
                for p in transformed
            )))
    return min(forms)


def canonical_key(inst):
    canonical = _canonical_cubes(inst["cubes"])
    blob = json.dumps(canonical, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params):
    """The witness visits every panel, so the next size exceeds the atom cap."""
    n = int(params.get("n", 0))
    if 4 * n + 2 >= 254:
        return "cap_bound"
    harder = max(n + 4, math.ceil(n * 1.18))
    if 4 * harder + 2 > 256:
        return "cap_bound"
    return {"n": harder}


def _normalise_cycle(cycle):
    if not cycle or 0 not in cycle:
        return cycle
    pivot = cycle.index(0)
    cycle = cycle[pivot:] + cycle[:pivot]
    if len(cycle) > 2 and cycle[1] > cycle[-1]:
        cycle = [cycle[0]] + list(reversed(cycle[1:]))
    return cycle


def _cycles_from_selected(panel_count, selected, operation_box=None):
    chosen = [[] for _ in range(panel_count)]
    for u, v in selected:
        chosen[u].append(v)
        chosen[v].append(u)
    if any(len(row) != 2 for row in chosen):
        return None
    seen = set()
    cycles = []
    for start in range(panel_count):
        if start in seen:
            continue
        cycle = []
        previous = -1
        current = start
        while current not in seen:
            seen.add(current)
            cycle.append(current)
            a, b = chosen[current]
            nxt = a if a != previous else b
            previous, current = current, nxt
            if operation_box is not None:
                operation_box[0] += 1
        if current != start:
            return None
        cycles.append(cycle)
    return cycles


def _reference_two_factor_merge(inst, rng, max_restarts=256):
    """Paper-cited 2-factor extraction followed by exact cycle merging.

    A randomized Euler tour of a 4-regular graph, colored alternately, gives two
    2-factors.  We try both and merge distinct cycles by valid two-edge swaps.
    The method is generic: it uses only the supplied adjacency, not voxel order.
    """
    adjacency = [set(panel["neighbors"]) for panel in inst["panels"]]
    count = len(adjacency)
    graph_edges = {
        (u, v) for u in range(count) for v in adjacency[u] if u < v
    }
    operations = [0]
    start_time = time.perf_counter()
    for restart in range(1, max_restarts + 1):
        unused = [list(row) for row in adjacency]
        for row in unused:
            rng.shuffle(row)
        used = set()
        stack = [0]
        euler_vertices = []
        while stack:
            u = stack[-1]
            while unused[u]:
                v = unused[u][-1]
                edge = (min(u, v), max(u, v))
                operations[0] += 1
                if edge not in used:
                    break
                unused[u].pop()
            if unused[u]:
                v = unused[u].pop()
                used.add((min(u, v), max(u, v)))
                stack.append(v)
            else:
                euler_vertices.append(stack.pop())
            operations[0] += 1
        if len(used) != 2 * count:
            raise AssertionError("4-regular reference graph has wrong edge count")
        euler_edges = [
            (min(euler_vertices[i], euler_vertices[i + 1]),
             max(euler_vertices[i], euler_vertices[i + 1]))
            for i in range(len(euler_vertices) - 1)
        ]

        for parity in (0, 1):
            selected = set(euler_edges[parity::2])
            cycles = _cycles_from_selected(count, selected, operations)
            if cycles is None:
                raise AssertionError("alternating Euler edges are not a 2-factor")
            while len(cycles) > 1:
                component = {
                    vertex: index
                    for index, cycle in enumerate(cycles)
                    for vertex in cycle
                }
                merged = False
                chosen_edges = list(selected)
                for i, (a, b) in enumerate(chosen_edges):
                    for c, d in chosen_edges[i + 1:]:
                        operations[0] += 1
                        if component[a] == component[c]:
                            continue
                        options = (
                            ((a, c), (b, d)),
                            ((a, d), (b, c)),
                        )
                        for first, second in options:
                            x = (min(first), max(first))
                            y = (min(second), max(second))
                            operations[0] += 2
                            if x in graph_edges and y in graph_edges:
                                selected.remove((min(a, b), max(a, b)))
                                selected.remove((min(c, d), max(c, d)))
                                selected.add(x)
                                selected.add(y)
                                merged = True
                                break
                        if merged:
                            break
                    if merged:
                        break
                if not merged:
                    break
                cycles = _cycles_from_selected(count, selected, operations)
                if cycles is None:
                    raise AssertionError("a merge broke the 2-factor")
            if len(cycles) == 1:
                cycle = _normalise_cycle(cycles[0])
                return cycle, {
                    "restarts": restart,
                    "operations": operations[0],
                    "wall_clock_sec": time.perf_counter() - start_time,
                }
    return None, {
        "restarts": max_restarts,
        "operations": operations[0],
        "wall_clock_sec": time.perf_counter() - start_time,
    }


def _complete_candidate(path, count):
    used = set(path)
    path = list(path) + [v for v in range(count) if v not in used]
    return _normalise_cycle(path)


def _greedy_walk(inst, random_source=None):
    adjacency = [set(panel["neighbors"]) for panel in inst["panels"]]
    count = len(adjacency)
    path = [0]
    used = {0}
    while len(path) < count:
        candidates = [v for v in adjacency[path[-1]] if v not in used]
        if not candidates:
            break
        if random_source is None:
            candidates.sort(key=lambda v: (
                sum(w not in used for w in adjacency[v]), v
            ))
            nxt = candidates[0]
        else:
            # Mild structure-aware bias: prefer vertices with few exits, but
            # randomize ties as a restart heuristic would.
            best = min(sum(w not in used for w in adjacency[v])
                       for v in candidates)
            tied = [v for v in candidates
                    if sum(w not in used for w in adjacency[v]) == best]
            nxt = random_source.choice(tied)
        path.append(nxt)
        used.add(nxt)
    return _complete_candidate(path, count)


def _geometric_sort_candidate(inst):
    normal_rank = {name: i for i, name in enumerate(DIR_NAMES)}
    order = sorted(range(inst["panel_count"]), key=lambda label: (
        sum(inst["panels"][label]["cube"]),
        normal_rank[inst["panels"][label]["normal"]],
        tuple(inst["panels"][label]["cube"]),
        label,
    ))
    return _normalise_cycle(order)


def _fixed_local_face_candidate(inst):
    # The visually tempting rule: visit voxels by x+y and exposed normals in a
    # fixed cyclic order. It ignores which two ports a five-face splice uses.
    preferred = {d: i for i, d in enumerate(("+x", "+y", "-x", "+z", "-y", "-z"))}
    order = sorted(range(inst["panel_count"]), key=lambda label: (
        sum(inst["panels"][label]["cube"]),
        preferred[inst["panels"][label]["normal"]],
        label,
    ))
    return _normalise_cycle(order)


def _attack_candidates(inst, seed):
    random_walks = []
    rng = random.Random(seed ^ 0x180303302)
    for _ in range(256):
        random_walks.append(_greedy_walk(inst, rng))
    # A pair-of-smallest-neighbors 2-factor is another plausible paper-and-pencil
    # ansatz. If it is not one cycle, turn it into a shape-valid permutation so
    # verify supplies the exact failure reason.
    count = inst["panel_count"]
    chosen = set()
    for u, panel in enumerate(inst["panels"]):
        for v in sorted(panel["neighbors"])[:2]:
            chosen.add((min(u, v), max(u, v)))
    cycles = _cycles_from_selected(count, chosen)
    if cycles is not None and len(cycles) == 1:
        pairing = _normalise_cycle(cycles[0])
    else:
        pairing = _complete_candidate([0], count)
    return {
        "outlier_geometric_sort": [_geometric_sort_candidate(inst)],
        "greedy_fewest_exits": [_greedy_walk(inst)],
        "random_restart_256_walks": random_walks,
        "in_context_fixed_face_order": [_fixed_local_face_candidate(inst)],
        "smallest_neighbor_pairing": [pairing],
    }


def _signed_permutation_transform(inst, permutation, signs, translation, relabel, seed):
    """Apply a true mesh symmetry and a panel relabeling, carrying the cycle."""
    vector_to_direction = {vector: i for i, vector in enumerate(DIRS)}

    def transform_cube(cube):
        center = [2 * cube[i] + 1 for i in range(3)]
        out = [signs[j] * center[permutation[j]] for j in range(3)]
        return [(out[j] - 1) // 2 + translation[j] for j in range(3)]

    def transform_normal(name):
        old = DIRS[DIR_NAMES.index(name)]
        out = tuple(signs[j] * old[permutation[j]] for j in range(3))
        return DIR_NAMES[vector_to_direction[out]]

    count = inst["panel_count"]
    if relabel is None:
        relabel = list(range(count))
    panels = [None] * count
    for old, panel in enumerate(inst["panels"]):
        new = relabel[old]
        panels[new] = {
            "cube": transform_cube(panel["cube"]),
            "normal": transform_normal(panel["normal"]),
            "neighbors": sorted(relabel[v] for v in panel["neighbors"]),
        }
    cubes = [transform_cube(cube) for cube in inst["cubes"]]
    random.Random(seed).shuffle(cubes)
    answer = _normalise_cycle([relabel[v] for v in inst["answer"]])
    return {
        "cube_count": inst["cube_count"],
        "panel_count": count,
        "cubes": cubes,
        "panels": panels,
        "answer": answer,
    }


def _answer_size(answer):
    text = json.dumps(answer, separators=(",", ":"))
    return {
        "answer_chars": len(text),
        "answer_tokens": math.ceil(len(text) / 4),
        "answer_elements": len(answer),
    }


def _compact_shelling_solution(inst):
    """Recover a cycle from the monotone attachment decomposition, not the plant."""
    cubes = sorted((tuple(c) for c in inst["cubes"]), key=lambda c: (sum(c), c))
    if not cubes:
        return None, 0
    first = cubes[0]
    cycle = [first + (d,) for d in (0, 2, 1, 4, 3, 5)]
    prefix = [first]
    chooser = random.Random(0)
    for new_cube in cubes[1:]:
        old_cube = prefix[-1]
        delta = tuple(new_cube[j] - old_cube[j] for j in range(3))
        if delta not in DIRS:
            return None, 3 * (len(prefix) - 1)
        direction = DIRS.index(delta)
        glue = old_cube + (direction,)
        if glue not in cycle:
            return None, 3 * (len(prefix) - 1)
        index = cycle.index(glue)
        before = cycle[index - 1]
        after = cycle[(index + 1) % len(cycle)]
        prefix.append(new_cube)
        adjacency = _surface_adjacency(_surface(prefix))
        patch = [new_cube + (side,) for side in range(6)
                 if side != OPPOSITE[direction]]
        entries = [face for face in patch if before in adjacency[face]]
        exits = [face for face in patch if after in adjacency[face]]
        if len(entries) != 1 or len(exits) != 1:
            return None, 3 * (len(prefix) - 1)
        cycle[index:index + 1] = _patch_path(
            patch, entries[0], exits[0], adjacency, chooser
        )
    face_to_label = {}
    for label, panel in enumerate(inst["panels"]):
        try:
            direction = DIR_NAMES.index(panel["normal"])
            face = tuple(panel["cube"]) + (direction,)
        except (KeyError, TypeError, ValueError):
            return None, 3 * max(0, len(cubes) - 1)
        face_to_label[face] = label
    if any(face not in face_to_label for face in cycle):
        return None, 3 * max(0, len(cubes) - 1)
    return _normalise_cycle([face_to_label[face] for face in cycle]), 3 * max(0, len(cubes) - 1)


def _fast_cycle_ok(adjacency, candidate):
    count = len(adjacency)
    return (
        isinstance(candidate, list)
        and len(candidate) == count
        and candidate[0] == 0
        and candidate[1] < candidate[-1]
        and len(set(candidate)) == count
        and all(0 <= v < count for v in candidate)
        and all(candidate[(i + 1) % count] in adjacency[candidate[i]]
                for i in range(count))
    )


def selftest():
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    g1_failures = []
    attempts = 0
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 29):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                g1_failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not g1_failures and json_roundtrips == attempts,
        "attempts": attempts,
        "json_roundtrips": json_roundtrips,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=190, **shipping_params)
    answer = inst["answer"]
    swapped = None
    for i in range(2, len(answer) - 2):
        for j in range(i + 1, min(len(answer) - 1, i + 12)):
            candidate = list(answer)
            candidate[i], candidate[j] = candidate[j], candidate[i]
            ok, reason = verify(inst, candidate)
            if not ok and reason.startswith("panels "):
                swapped = candidate
                break
        if swapped is not None:
            break
    if swapped is None:
        raise AssertionError("could not make a non-edge swap corruption")
    duplicated = list(answer)
    duplicated[2] = duplicated[1]
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": answer[:-1] + [inst["panel_count"]],
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [result["reason"] for result in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(result["rejected"] for result in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The cyclic ordering closes at panel 0.\n\n```text\n<answer>\n"
        + json.dumps(answer, separators=(",", ":"))
        + "\n</answer>\n```\nAll ids are zero-based."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0]
        and parse_answer("there is no tagged answer") is None,
        "parsed_equals_answer": parsed == answer,
        "garbage_returns_none": parse_answer("there is no tagged answer") is None,
    }

    adjacency = [set(panel["neighbors"]) for panel in inst["panels"]]
    guess_rng = random.Random(0x180303302)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(_fast_cycle_ok(
            adjacency, random_candidate(inst, guess_rng)
        ))
    guess_seconds = time.perf_counter() - guess_start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_fraction,
        "structure_aware_space_bits": search_space(inst).bit_length(),
        "sampler": (
            "uniform over permutations after enforcing all stated shape, range, "
            "distinctness, rotation, and reversal-normalisation constraints"
        ),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    exact_demo_count = enumerate_all(demo)
    baseline_start = time.perf_counter()
    baseline_answer, baseline_stats = _reference_two_factor_merge(
        inst, random.Random(0xBADA551), max_restarts=256
    )
    baseline_wall = time.perf_counter() - baseline_start
    baseline_ok = baseline_answer is not None and verify(inst, baseline_answer)[0]
    report["G5_density_and_baseline"] = {
        "pass": isinstance(guess_fraction, float) and baseline_ok
        and exact_demo_count is not None,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_solution_fraction_estimate": guess_fraction,
        "shipping_candidate_space_bits": search_space(inst).bit_length(),
        "demo_exact_valid_answers": exact_demo_count,
        "demo_candidate_space": search_space(demo),
        "baseline_attack": "randomized Euler 2-factor extraction plus two-edge cycle merging",
        "baseline_wall_clock_sec": round(baseline_wall, 6),
        "baseline_operations": baseline_stats["operations"],
        "baseline_restarts": baseline_stats["restarts"],
        "baseline_success": baseline_ok,
    }

    attack_names = (
        "outlier_geometric_sort",
        "greedy_fewest_exits",
        "random_restart_256_walks",
        "in_context_fixed_face_order",
        "smallest_neighbor_pairing",
    )
    attack_results = {
        name: {"successes": 0, "attempts": 0, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    reference_successes = 0
    reference_operations = []
    reference_restarts = []
    reference_seconds = []
    compact_successes = 0
    compact_operations = []
    compact_seconds = []
    for seed in range(4100, 4108):
        trial = make_instance(seed=seed, **shipping_params)
        trial_adjacency = [set(panel["neighbors"]) for panel in trial["panels"]]
        candidates = _attack_candidates(trial, seed)
        for name in attack_names:
            start = time.perf_counter()
            success = any(_fast_cycle_ok(trial_adjacency, candidate)
                          for candidate in candidates[name])
            attack_results[name]["wall_clock_sec"] += time.perf_counter() - start
            attack_results[name]["attempts"] += 1
            attack_results[name]["successes"] += int(success)

        start = time.perf_counter()
        recovered, stats = _reference_two_factor_merge(
            trial, random.Random(seed ^ 0x2FAC70), max_restarts=256
        )
        reference_seconds.append(time.perf_counter() - start)
        reference_operations.append(stats["operations"])
        reference_restarts.append(stats["restarts"])
        reference_successes += int(
            recovered is not None and verify(trial, recovered)[0]
        )

        start = time.perf_counter()
        compact, operations = _compact_shelling_solution(trial)
        compact_seconds.append(time.perf_counter() - start)
        compact_operations.append(operations)
        compact_successes += int(
            compact is not None and verify(trial, compact)[0]
        )
    for result in attack_results.values():
        result["wall_clock_sec"] = round(result["wall_clock_sec"], 6)
    all_attacks_failed = all(
        result["successes"] == 0 for result in attack_results.values()
    )
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8
        and compact_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "randomized Euler 2-factor extraction plus two-edge cycle merging",
            "complexity": "O(R*F^3) worst-case for R Euler-tour restarts",
            "wall_clock_sec_median": round(sorted(reference_seconds)[4], 6),
            "wall_clock_sec_max": round(max(reference_seconds), 6),
            "operations_median": sorted(reference_operations)[4],
            "operations_max": max(reference_operations),
            "restarts_median": sorted(reference_restarts)[4],
            "restarts_max": max(reference_restarts),
            "solves": f"{reference_successes}/8, as expected",
        },
        "compact_route": {
            "name": "attachment-chain five-face splicing",
            "wall_clock_sec_median": round(sorted(compact_seconds)[4], 6),
            "operations": max(compact_operations),
            "solves": f"{compact_successes}/8",
        },
    }

    named_panel_counts = [
        make_instance(seed=0, **params)["panel_count"]
        for params in DIFFICULTY.values()
    ]
    doubled_params = {"n": 2 * shipping_params["n"]}
    doubled = make_instance(seed=71, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": all(a < b for a, b in zip(
            named_panel_counts, named_panel_counts[1:]
        )) and doubled_ok and escalate(shipping_params) == "cap_bound",
        "named_panel_counts": named_panel_counts,
        "doubled_params": doubled_params,
        "doubled_panel_count": doubled["panel_count"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "escalate_result": escalate(shipping_params),
    }

    invariance_checks = 0
    carried_checks = 0
    invariance_failures = []
    keys = []
    for seed in range(20):
        original = make_instance(seed=seed, **shipping_params)
        key = canonical_key(original)
        keys.append(key)
        rng = random.Random(seed ^ 0xC4A1)
        permutation = list(range(3))
        rng.shuffle(permutation)
        signs = [rng.choice((-1, 1)) for _ in range(3)]
        translation = [rng.randrange(-20, 21) for _ in range(3)]
        relabel = list(range(original["panel_count"]))
        rng.shuffle(relabel)
        transformed = _signed_permutation_transform(
            original, permutation, signs, translation, relabel, seed ^ 0x5151
        )
        invariance_checks += 1
        if canonical_key(transformed) != key:
            invariance_failures.append([seed, "key changed"])
        ok, reason = verify(transformed, transformed["answer"])
        carried_checks += 1
        if not ok:
            invariance_failures.append([seed, reason])
    report["G8_canonical_key"] = {
        "pass": not invariance_failures and len(set(keys)) == len(keys),
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated_keys": len(set(keys)),
        "unrelated_instances": len(keys),
        "transformations": (
            "composed panel relabeling, cube-row reordering, translation, "
            "coordinate permutation, and coordinate reflection"
        ),
        "failures": invariance_failures,
    }

    size = _answer_size(answer)
    bare = G9_ORACLE_RESULTS["bare"]
    hinted = G9_ORACLE_RESULTS["hinted"]
    placebo = G9_ORACLE_RESULTS["placebo"]
    hinted_rate = (hinted["solved"] / hinted["attempts"]
                   if hinted["attempts"] else 0.0)
    placebo_rate = (placebo["solved"] / placebo["attempts"]
                    if placebo["attempts"] else 0.0)
    intended_operations = 3 * (inst["cube_count"] - 1)
    within_caps = (
        size["answer_chars"] <= 2000
        and size["answer_elements"] <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {
            "bare": dict(bare),
            "hinted": dict(hinted),
            "placebo": dict(placebo),
        },
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        **size,
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
