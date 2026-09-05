"""Verified affine-frame generators for arXiv:1204.4298.

The paper's Example 2 is a path whose vertices have been blown up to cliques:
consecutive clique layers are joined completely.  Boundary i receives colour i
and all within-layer edges receive colour 1.  A path through the layers is
rainbow, while the two end layers are at distance L-1, so the colouring is
optimal and attains rc(G)=2*alpha(G)-1.

This module applies a random invertible affine change of coordinates over F_p
and asks for that compact coordinate frame.  Expanding the frame gives the
paper's layer partition and its edge colouring.  Generation knows the frame
before it builds or relabels the graph; it never recovers a frame from an
already-built instance.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # This family needs only elementary arithmetic modulo p.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "graph",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "a simple graph whose vertices have coordinate labels in F_p^2",
        "an affine coordinate frame encoding an optimal rainbow edge-colouring",
    ],
    "verification_operations": [
        "exact modular determinant and affine-coordinate inversion",
        "exact reconstruction of clique layers and graph adjacency",
        "exact expansion of the paper's boundary-colour rule",
        "diameter and rainbow-path comparison on the layer quotient",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Closed-neighborhood twin classes are parallel affine progressions whose "
        "quotient is a path; without changing to those coordinates, a solver must "
        "recover the twin partition and affine frame mechanically."
    ),
    "hardness_basis": (
        "Track B: closed-neighborhood twin refinement followed by exact affine-"
        "frame recovery runs in O(N^2+L^2+w^3+NLw^2), averaging 36,271 counted "
        "operations and 0.0027 seconds at shipping n=32 over eight gate seeds; the "
        "paper's colouring is then linear in the edges, whereas the compact route "
        "uses at most 204 modular arithmetic operations after recognizing the "
        "affine path of twin classes."
    ),
    "max_answer_tokens": 17,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (PROBLEM_PROFILE["intuition_type"] + ": " +
                  PROBLEM_PROFILE["intuition_description"]),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 4, "width_min": 2, "width_max": 3, "p": 7},
    "easy": {"n": 10, "width_min": 2, "width_max": 4, "p": 101},
    "medium": {"n": 20, "width_min": 3, "width_max": 6, "p": 257},
    "hard": {"n": 32, "width_min": 4, "width_max": 7, "p": 1009},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Closed-neighborhood twin classes are parallel affine progressions whose "
    "quotient graph is a path."
)
PLACEBO_HINT = (
    "Consistent bookkeeping for modular coordinate pairs and vertex indices "
    "is important throughout the problem."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON affine frame over F_p: an origin and two ordered, linearly "
        "independent vectors named layer_step and slot_step; every coordinate "
        "is an integer in 0..p-1."
    ),
    "bounds": {
        "field": "F_p from the instance",
        "vectors": 3,
        "coordinates_per_vector": 2,
        "coordinate_min": 0,
        "coordinate_max": "p-1",
        "step_vectors_linearly_independent": True,
    },
}

NOTES = (
    "The Introduction fixes the exact notions used here: graphs are finite, "
    "simple and undirected; a rainbow path has pairwise differently coloured "
    "edges; rc(G) is the minimum number of colours making every vertex pair "
    "rainbow connected; and alpha(G) is the maximum independent-set size. "
    "Example 2 supplies the actual object: 2t clique layers, complete joins only "
    "between consecutive layers, boundary i coloured i, and within-layer edges "
    "coloured 1. Its proof gives rc(G)=diam(G)=2t-1=2 alpha(G)-1. The same "
    "one-line path and independence arguments allow arbitrary nonempty layer "
    "sizes, which this generator uses for structural diversity. Theorem 1 and "
    "its Procedures 1 and 2 are constructive, so this is deliberately Track B, "
    "not a false Track-A claim: an efficient certificate-producing algorithm "
    "exists. The reference algorithm groups equal closed neighborhoods, orders "
    "the quotient path, and tests endpoint affine progressions. Plants and "
    "decoys are not separate graph elements: every vertex is generated by the "
    "same affine frame. Random affine labels defeat coordinate-axis and fixed-"
    "origin guesses; variable layer widths defeat a global slot reversal; the "
    "frequency attack learns at most a projective direction, not its scale or "
    "origin; random frames and lexicographic local frames fail exact expansion."
)


# Filled after the script-owned oracle runs.  G9(a,b) are diagnostics; only the
# answer-size and intended-operation caps determine the G9 pass flag.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unrun",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_prime(p):
    if not _is_int(p) or p < 2:
        return False
    if p % 2 == 0:
        return p == 2
    divisor = 3
    while divisor * divisor <= p:
        if p % divisor == 0:
            return False
        divisor += 2
    return True


def _validate_parameters(n, width_min, width_max, p):
    if not _is_int(n) or n < 4 or n % 2:
        raise ValueError("n must be an even integer at least 4")
    if (not _is_int(width_min) or not _is_int(width_max)
            or width_min < 2 or width_max < width_min):
        raise ValueError("width_min and width_max must be integers with 2 <= min <= max")
    if not _is_prime(p):
        raise ValueError("p must be prime")
    if p <= max(n, width_max):
        raise ValueError("p must exceed both n and width_max")


def _add(a, b, p):
    return ((a[0] + b[0]) % p, (a[1] + b[1]) % p)


def _sub(a, b, p):
    return ((a[0] - b[0]) % p, (a[1] - b[1]) % p)


def _scale(k, a, p):
    return ((k * a[0]) % p, (k * a[1]) % p)


def _point(origin, layer_step, slot_step, layer, slot, p):
    return _add(origin,
                _add(_scale(layer, layer_step, p),
                     _scale(slot, slot_step, p), p), p)


def _det(a, b, p):
    return (a[0] * b[1] - a[1] * b[0]) % p


def _draw_nonzero_vector(p, rng):
    while True:
        vector = (rng.randrange(p), rng.randrange(p))
        if vector != (0, 0):
            return vector


def _draw_frame(p, rng):
    origin = (rng.randrange(p), rng.randrange(p))
    layer_step = _draw_nonzero_vector(p, rng)
    while True:
        slot_step = (rng.randrange(p), rng.randrange(p))
        if _det(layer_step, slot_step, p):
            return origin, layer_step, slot_step


def make_instance(n, seed=0, width_min=2, width_max=5, p=257, **params):
    """Transform a known layered extremal graph through a sampled affine frame."""
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_parameters(n, width_min, width_max, p)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)

    # Example 2 fixes its first two layer sizes at 2.  Later layers are allowed
    # independent sizes: its rainbow-path and alpha arguments use only that every
    # layer is a nonempty clique, not equality of their sizes.
    widths = [2, 2] + [rng.randint(width_min, width_max) for _ in range(n - 2)]

    # G: the inverse affine map (the answer) is sampled before any graph data.
    origin, layer_step, slot_step = _draw_frame(p, rng)
    records = []
    for layer, width in enumerate(widths):
        for slot in range(width):
            records.append((layer, slot,
                            _point(origin, layer_step, slot_step,
                                   layer, slot, p)))
    rng.shuffle(records)
    vertices = [[point[0], point[1]] for _layer, _slot, point in records]
    coordinates = [(layer, slot) for layer, slot, _point_value in records]

    edges = []
    for u in range(len(vertices)):
        layer_u, _slot_u = coordinates[u]
        for v in range(u + 1, len(vertices)):
            layer_v, _slot_v = coordinates[v]
            if layer_u == layer_v or abs(layer_u - layer_v) == 1:
                edges.append([u, v])
    rng.shuffle(edges)

    answer = {
        "origin": list(origin),
        "layer_step": list(layer_step),
        "slot_step": list(slot_step),
    }
    return {
        "p": p,
        "layers": n,
        "width_min": width_min,
        "width_max": width_max,
        "vertices": vertices,
        "edges": edges,
        "answer": answer,
    }


def _adjacency(inst):
    count = len(inst["vertices"])
    adjacency = [set() for _ in range(count)]
    for edge in inst["edges"]:
        if (not isinstance(edge, (list, tuple)) or len(edge) != 2
                or not all(_is_int(x) for x in edge)):
            raise ValueError("malformed edge in instance")
        u, v = edge
        if not (0 <= u < v < count):
            raise ValueError("instance edges must be canonical distinct pairs")
        adjacency[u].add(v)
        adjacency[v].add(u)
    return adjacency


def render(inst):
    """Render a complete standalone graph problem and its exact JSON contract."""
    adjacency = _adjacency(inst)
    rows = []
    for vertex, point in enumerate(inst["vertices"]):
        closed = sorted(adjacency[vertex] | {vertex})
        rows.append(
            f"{vertex:>3}  ({point[0]},{point[1]})  " +
            " ".join(map(str, closed))
        )
    table = "\n".join(rows)
    statement = f"""Recover a compact optimal rainbow-colouring certificate

Work over the finite field F_{inst['p']}; all additions, subtractions and
multiplications of coordinate pairs are componentwise modulo {inst['p']}.
The input is a finite simple undirected graph on vertices 0 through
{len(inst['vertices']) - 1}, inclusive.  Each vertex has a distinct coordinate
label (x,y) in F_{inst['p']}^2.  The table gives the vertex index, its coordinate,
and its CLOSED neighborhood (the vertex itself plus all its neighbors).  Thus
two distinct indices u,v are adjacent exactly when v occurs in u's row.

The graph is promised to have {inst['layers']} nonempty clique layers.  In one
of the two possible layer orientations, layers 0 and 1 have width 2 and every
later width is in the inclusive range {inst['width_min']}..{inst['width_max']}.
Vertices in the same layer are all adjacent, consecutive layers are joined by
all possible edges, and there are no other edges.

Your answer is an affine frame O,A,B in F_{inst['p']}^2.  It must decode every
displayed coordinate uniquely as

    coordinate = O + i*A + j*B  (mod {inst['p']}),

where i is its 0-based layer number.  Within every decoded layer i, the slot
numbers j must be exactly 0,1,...,width(i)-1 with no gap or repeat.  Reversing
the layer orientation is allowed if it obeys the same graph and endpoint-width
promise.  A and B must be linearly independent over F_{inst['p']}.

This frame symbolically defines the paper's edge-colouring: every edge within
a layer gets colour 1, and every edge between layers i and i+1 gets colour i+1.
The frame is valid only if this expansion is an optimal rainbow colouring.  A
path is rainbow when all its edge colours are pairwise distinct; a graph is
rainbow connected when every two vertices have a rainbow path.  Optimal means
that no rainbow colouring uses fewer colours.

vertex  coordinate  closed-neighborhood
{table}

Give your final answer inside <answer></answer> tags as exactly one JSON object
with three length-2 integer arrays named `origin`, `layer_step`, and `slot_step`.
Every entry must lie in 0..{inst['p'] - 1}; order inside each pair is (x,y).
Example syntax: <answer>{{"origin":[0,0],"layer_step":[1,0],"slot_step":[0,1]}}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>",
                        re.IGNORECASE | re.DOTALL)


def parse_answer(text):
    """Extract the last tagged JSON frame, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        lines = body.splitlines()
        if len(lines) >= 2:
            body = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    if set(value) != {"origin", "layer_step", "slot_step"}:
        return None
    for name in ("origin", "layer_step", "slot_step"):
        vector = value[name]
        if (not isinstance(vector, list) or len(vector) != 2
                or not all(_is_int(x) for x in vector)):
            return None
    return value


def _validated_frame(inst, answer):
    """Return (O,A,B) or a stable, corruption-specific error string."""
    if not isinstance(answer, dict):
        return None, "answer must be a JSON object"
    if not answer:
        return None, "answer object is empty"
    required = {"origin", "layer_step", "slot_step"}
    if set(answer) != required:
        return None, "answer must contain exactly origin, layer_step, and slot_step"
    for name in ("origin", "layer_step", "slot_step"):
        vector = answer[name]
        if not isinstance(vector, (list, tuple)) or len(vector) != 2:
            return None, f"{name} must be a length-2 coordinate pair"
        if not all(_is_int(value) for value in vector):
            return None, f"{name} coordinates must be integers"
    p = inst["p"]
    if any(value < 0 or value >= p for name in required for value in answer[name]):
        return None, f"a frame coordinate is outside the inclusive range 0..{p - 1}"
    origin = tuple(answer["origin"])
    layer_step = tuple(answer["layer_step"])
    slot_step = tuple(answer["slot_step"])
    if not _det(layer_step, slot_step, p):
        return None, "layer_step and slot_step are linearly dependent"
    return (origin, layer_step, slot_step), None


def _decode_layout(inst, frame):
    """Decode all vertices and return (coordinates,widths) or an error."""
    origin, layer_step, slot_step = frame
    p = inst["p"]
    determinant = _det(layer_step, slot_step, p)
    inverse_det = pow(determinant, p - 2, p)
    decoded = []
    seen = set()
    slots = [[] for _ in range(inst["layers"])]
    for point_value in inst["vertices"]:
        point = tuple(point_value)
        difference = _sub(point, origin, p)
        layer = ((difference[0] * slot_step[1] -
                  difference[1] * slot_step[0]) * inverse_det) % p
        slot = ((layer_step[0] * difference[1] -
                 layer_step[1] * difference[0]) * inverse_det) % p
        if layer >= inst["layers"]:
            return None, "a vertex decodes outside the permitted layer range"
        if slot >= inst["width_max"]:
            return None, "a vertex decodes outside the permitted slot range"
        if (layer, slot) in seen:
            return None, "two vertices decode to the same layer and slot"
        seen.add((layer, slot))
        slots[layer].append(slot)
        decoded.append((layer, slot))
    if any(not row for row in slots):
        return None, "at least one decoded layer is empty"
    widths = []
    for row in slots:
        ordered = sorted(row)
        if ordered != list(range(len(ordered))):
            return None, "decoded slot numbers are not consecutive from zero"
        widths.append(len(ordered))
    normal = (widths[0:2] == [2, 2] and
              all(inst["width_min"] <= width <= inst["width_max"]
                  for width in widths[2:]))
    reversed_normal = (widths[-2:] == [2, 2] and
                       all(inst["width_min"] <= width <= inst["width_max"]
                           for width in widths[:-2]))
    if not (normal or reversed_normal):
        return None, "decoded layer widths violate the endpoint-width promise"
    return (decoded, widths), None


def verify(inst, answer):
    """Verify any affine frame and its induced optimal colouring exactly."""
    frame, error = _validated_frame(inst, answer)
    if error:
        return False, error
    layout, error = _decode_layout(inst, frame)
    if error:
        return False, error
    decoded, widths = layout

    try:
        actual_edges = {tuple(edge) for edge in inst["edges"]}
    except TypeError:
        return False, "the instance edge list is malformed"
    expected_edges = set()
    for u in range(len(decoded)):
        for v in range(u + 1, len(decoded)):
            layer_u, _slot_u = decoded[u]
            layer_v, _slot_v = decoded[v]
            if layer_u == layer_v or abs(layer_u - layer_v) == 1:
                expected_edges.add((u, v))
    if actual_edges != expected_edges:
        return False, "the decoded layers do not reconstruct the input graph"

    # Execute the rainbow and optimality identities on the decoded quotient.
    # Between layers a<b, one crossing edge from each boundary has colours
    # a+1,...,b, all distinct. Same/adjacent-layer pairs have a direct edge.
    layers = inst["layers"]
    for a in range(layers):
        for b in range(a + 1, layers):
            colours = list(range(a + 1, b + 1))
            if len(colours) != len(set(colours)):
                return False, "the induced boundary path is not rainbow"
    used_colours = layers - 1
    diameter_lower_bound = layers - 1
    if used_colours != diameter_lower_bound:
        return False, "the induced colouring does not meet the diameter lower bound"
    if len(widths) != layers:
        return False, "internal layer count mismatch"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from all ordered affine frames over the displayed field."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    origin, layer_step, slot_step = _draw_frame(inst["p"], rng)
    return {
        "origin": list(origin),
        "layer_step": list(layer_step),
        "slot_step": list(slot_step),
    }


def search_space(inst):
    """Count all origins and ordered independent step-vector pairs exactly."""
    p = inst["p"]
    return p * p * (p * p - 1) * (p * p - p)


def enumerate_all(inst):
    """Count valid frames exactly only when the declared language is small."""
    if search_space(inst) > 200_000:
        return None
    p = inst["p"]
    total = 0
    for ox in range(p):
        for oy in range(p):
            for ax in range(p):
                for ay in range(p):
                    if (ax, ay) == (0, 0):
                        continue
                    for bx in range(p):
                        for by in range(p):
                            if not _det((ax, ay), (bx, by), p):
                                continue
                            candidate = {
                                "origin": [ox, oy],
                                "layer_step": [ax, ay],
                                "slot_step": [bx, by],
                            }
                            total += int(verify(inst, candidate)[0])
    return total


def _twin_path(inst):
    """Return true-twin classes in one path orientation, or None."""
    adjacency = _adjacency(inst)
    groups = {}
    for vertex in range(len(adjacency)):
        signature = tuple(sorted(adjacency[vertex] | {vertex}))
        groups.setdefault(signature, []).append(vertex)
    classes = list(groups.values())
    class_of = {}
    for index, group in enumerate(classes):
        for vertex in group:
            class_of[vertex] = index
    quotient = [set() for _ in classes]
    for u, v in inst["edges"]:
        left, right = class_of[u], class_of[v]
        if left != right:
            quotient[left].add(right)
            quotient[right].add(left)
    endpoints = [index for index, row in enumerate(quotient) if len(row) == 1]
    if len(classes) != inst["layers"] or len(endpoints) != 2:
        return None
    order = []
    previous = None
    current = min(endpoints)
    while True:
        order.append(current)
        following = [x for x in quotient[current] if x != previous]
        if not following:
            break
        if len(following) != 1:
            return None
        previous, current = current, following[0]
    if len(order) != len(classes):
        return None
    return [classes[index] for index in order]


def canonical_key(inst):
    """Canonicalize index/order/affine relabellings by the twin-path widths."""
    path = _twin_path(inst)
    if path is None:
        # Strong fallback for malformed out-of-family instances; generated inputs
        # never take it.  It excludes seed and input ordering.
        adjacency = _adjacency(inst)
        degrees = sorted(len(row) for row in adjacency)
        payload = [inst["p"], len(adjacency), len(inst["edges"]), degrees]
    else:
        widths = [len(group) for group in path]
        canonical_widths = min(widths, list(reversed(widths)))
        payload = [inst["p"], canonical_widths]
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":")).encode()
    ).hexdigest()


def escalate(params):
    """Grow useful fixed-answer axes until the compact-route cap is reached."""
    n = params["n"]
    width_min = params.get("width_min", 2)
    width_max = params.get("width_max", 5)
    p = params.get("p", 257)
    primes = [1009, 2003, 4001]
    next_p = next((prime for prime in primes if prime > p), p)
    if n < 48:
        return {
            "n": min(48, n + 8),
            "width_min": min(8, width_min + 1),
            "width_max": min(11, width_max + 1),
            "p": next_p,
        }
    # At n=48 the declared compact route costs 284 exact operations.  The next
    # meaningful layer/crowding step would cost at least 324, beyond G9(c)'s 300-
    # operation ceiling.  A larger modulus alone changes digit work but not the
    # structural search; using it to defeat a no-tool solver would be a calculator
    # test, not a harder instance of the intended insight.
    return None


def _candidate_from_frame(origin, layer_step, slot_step):
    return {
        "origin": list(origin),
        "layer_step": list(layer_step),
        "slot_step": list(slot_step),
    }


def _frame_for_order(inst, groups, operation_box=None):
    """Recover a frame by exhaustive endpoint-progression tests."""
    p = inst["p"]
    point_groups = [[tuple(inst["vertices"][v]) for v in group]
                    for group in groups]

    def count(amount=1):
        if operation_box is not None:
            operation_box[0] += amount

    first = point_groups[0]
    for origin in first:
        for neighbor in first:
            count(2)
            slot_step = _sub(neighbor, origin, p)
            if slot_step == (0, 0):
                continue
            expected_first = {
                _add(origin, _scale(slot, slot_step, p), p)
                for slot in range(len(first))
            }
            count(4 * len(first))
            if expected_first != set(first):
                continue
            second = point_groups[1]
            for point_value in second:
                for slot in range(len(second)):
                    count(6)
                    layer_step = _sub(
                        point_value,
                        _add(origin, _scale(slot, slot_step, p), p), p)
                    if not _det(layer_step, slot_step, p):
                        continue
                    matches = True
                    for layer, points in enumerate(point_groups):
                        expected = {
                            _point(origin, layer_step, slot_step,
                                   layer, j, p)
                            for j in range(len(points))
                        }
                        count(8 * len(points))
                        if expected != set(points):
                            matches = False
                            break
                    if matches:
                        return _candidate_from_frame(origin, layer_step, slot_step)
    return None


def _reference_algorithm(inst):
    """Mechanical twin refinement, quotient ordering, and affine progression search."""
    started = time.perf_counter()
    operation_box = [0]
    adjacency = _adjacency(inst)
    vertex_count = len(adjacency)
    operation_box[0] += 2 * len(inst["edges"])
    groups = {}
    for vertex in range(vertex_count):
        signature = []
        for other in range(vertex_count):
            operation_box[0] += 1
            if other == vertex or other in adjacency[vertex]:
                signature.append(other)
        groups.setdefault(tuple(signature), []).append(vertex)
    classes = list(groups.values())
    class_of = {}
    for index, group in enumerate(classes):
        for vertex in group:
            class_of[vertex] = index
            operation_box[0] += 1
    quotient = [set() for _ in classes]
    for u, v in inst["edges"]:
        operation_box[0] += 1
        left, right = class_of[u], class_of[v]
        if left != right:
            quotient[left].add(right)
            quotient[right].add(left)
    endpoints = [index for index, row in enumerate(quotient) if len(row) == 1]
    if len(endpoints) != 2:
        return None, {"operations": operation_box[0],
                      "wall_clock_sec": time.perf_counter() - started}
    order = []
    previous, current = None, endpoints[0]
    while True:
        order.append(current)
        operation_box[0] += len(quotient[current]) + 1
        following = [x for x in quotient[current] if x != previous]
        if not following:
            break
        previous, current = current, following[0]
    ordered_groups = [classes[index] for index in order]
    for candidate_order in (ordered_groups, list(reversed(ordered_groups))):
        candidate = _frame_for_order(inst, candidate_order, operation_box)
        if candidate is not None and verify(inst, candidate)[0]:
            return candidate, {
                "operations": operation_box[0],
                "wall_clock_sec": time.perf_counter() - started,
                "vertices": vertex_count,
                "edges": len(inst["edges"]),
                "twin_classes": len(classes),
            }
    return None, {
        "operations": operation_box[0],
        "wall_clock_sec": time.perf_counter() - started,
        "vertices": vertex_count,
        "edges": len(inst["edges"]),
        "twin_classes": len(classes),
    }


def _axis_attack(inst):
    point = min(map(tuple, inst["vertices"]))
    return _candidate_from_frame(point, (1, 0), (0, 1))


def _degree_extrema_attack(inst):
    adjacency = _adjacency(inst)
    ordered = sorted(range(len(adjacency)),
                     key=lambda vertex: (len(adjacency[vertex]), vertex))
    origin = tuple(inst["vertices"][ordered[0]])
    layer_step = _sub(tuple(inst["vertices"][ordered[1]]), origin, inst["p"])
    slot_step = None
    for vertex in ordered[2:]:
        difference = _sub(tuple(inst["vertices"][vertex]), origin, inst["p"])
        if _det(layer_step, difference, inst["p"]):
            slot_step = difference
            break
    if slot_step is None or layer_step == (0, 0):
        return _axis_attack(inst)
    return _candidate_from_frame(origin, layer_step, slot_step)


def _lexicographic_local_attack(inst):
    adjacency = _adjacency(inst)
    origin_vertex = min(range(len(inst["vertices"])),
                        key=lambda v: tuple(inst["vertices"][v]))
    origin = tuple(inst["vertices"][origin_vertex])
    differences = [
        _sub(tuple(inst["vertices"][v]), origin, inst["p"])
        for v in sorted(adjacency[origin_vertex])
    ]
    differences.sort()
    for layer_step in differences:
        for slot_step in differences:
            if _det(layer_step, slot_step, inst["p"]):
                return _candidate_from_frame(origin, layer_step, slot_step)
    return _axis_attack(inst)


def _projective(vector, p):
    if vector == (0, 0):
        return vector
    if vector[0]:
        inverse = pow(vector[0], p - 2, p)
    else:
        inverse = pow(vector[1], p - 2, p)
    return _scale(inverse, vector, p)


def _frequency_direction_attack(inst):
    p = inst["p"]
    counts = {}
    for u, v in inst["edges"]:
        difference = _sub(tuple(inst["vertices"][v]),
                          tuple(inst["vertices"][u]), p)
        direction = _projective(difference, p)
        counts[direction] = counts.get(direction, 0) + 1
    directions = sorted(counts, key=lambda d: (-counts[d], d))
    slot_step = directions[0] if directions else (0, 1)
    layer_step = next((d for d in directions
                       if _det(d, slot_step, p)), (1, 0))
    origin = min(map(tuple, inst["vertices"]))
    return _candidate_from_frame(origin, layer_step, slot_step)


def _visible_endpoint_attack(inst):
    """Exploit the degree-3 endpoint class exposed by the rendered table.

    At the shipping parameters the first two layers have width two and all
    other layers have width at least four.  The two vertices in layer zero are
    therefore the unique degree-3 vertices.  Their coordinate difference is
    the slot step (up to orientation), and their two common neighbors are the
    next layer.  Trying the two orientations and two slot alignments is enough.
    """
    adjacency = _adjacency(inst)
    endpoints = [vertex for vertex, row in enumerate(adjacency) if len(row) == 3]
    if len(endpoints) != 2:
        return _axis_attack(inst)
    common = sorted(adjacency[endpoints[0]] & adjacency[endpoints[1]])
    if len(common) != 2:
        return _axis_attack(inst)
    p = inst["p"]
    for zero_index in range(2):
        origin = tuple(inst["vertices"][endpoints[zero_index]])
        other = tuple(inst["vertices"][endpoints[1 - zero_index]])
        slot_step = _sub(other, origin, p)
        for next_vertex in common:
            next_point = tuple(inst["vertices"][next_vertex])
            for next_slot in range(2):
                layer_step = _sub(
                    next_point, _add(origin,
                                     _scale(next_slot, slot_step, p), p), p)
                candidate = _candidate_from_frame(origin, layer_step, slot_step)
                if verify(inst, candidate)[0]:
                    return candidate
    return candidate


def _random_restart_attack(inst, rng, attempts=256):
    candidate = None
    for _ in range(attempts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return candidate


def _index_permuted(inst, seed):
    rng = random.Random(seed)
    count = len(inst["vertices"])
    old_at_new = list(range(count))
    rng.shuffle(old_at_new)
    new_of_old = [0] * count
    for new, old in enumerate(old_at_new):
        new_of_old[old] = new
    transformed = {key: value for key, value in inst.items()
                   if key not in ("vertices", "edges", "answer")}
    transformed["vertices"] = [list(inst["vertices"][old]) for old in old_at_new]
    transformed["edges"] = [
        sorted((new_of_old[u], new_of_old[v])) for u, v in inst["edges"]
    ]
    rng.shuffle(transformed["edges"])
    transformed["answer"] = json.loads(json.dumps(inst["answer"]))
    return transformed


def _affine_relabelled(inst, seed):
    rng = random.Random(seed)
    p = inst["p"]
    translation, column_a, column_b = _draw_frame(p, rng)

    def transform(vector, translate=False):
        point = _add(_scale(vector[0], column_a, p),
                     _scale(vector[1], column_b, p), p)
        return _add(point, translation, p) if translate else point

    transformed = {key: value for key, value in inst.items()
                   if key not in ("vertices", "answer")}
    transformed["vertices"] = [list(transform(tuple(point), True))
                               for point in inst["vertices"]]
    answer = inst["answer"]
    transformed["answer"] = {
        "origin": list(transform(tuple(answer["origin"]), True)),
        "layer_step": list(transform(tuple(answer["layer_step"]))),
        "slot_step": list(transform(tuple(answer["slot_step"]))),
    }
    return transformed


def _reverse_frame(inst, answer):
    p = inst["p"]
    origin = tuple(answer["origin"])
    layer_step = tuple(answer["layer_step"])
    reversed_origin = _add(origin,
                           _scale(inst["layers"] - 1, layer_step, p), p)
    return {
        "origin": list(reversed_origin),
        "layer_step": list(_scale(-1, layer_step, p)),
        "slot_step": list(answer["slot_step"]),
    }


def _json_answer_size(answer):
    compact = json.dumps(answer, separators=(",", ":"))
    atoms = sum(len(answer[name]) for name in
                ("origin", "layer_step", "slot_step"))
    return len(compact), (len(compact) + 3) // 4, atoms


def selftest():
    """Run all nine required gates and return their measured evidence."""
    report = {
        "paper": "arXiv:1204.4298",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures = []
    attempts = 0
    for preset, parameters in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **parameters)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures}

    shipping = make_instance(seed=12044298,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    corruptions = {
        "empty_answer": {},
        "drop_one_coordinate": {
            "origin": planted["origin"][:-1],
            "layer_step": planted["layer_step"][:],
            "slot_step": planted["slot_step"][:],
        },
        "swap_step_roles": {
            "origin": planted["origin"][:],
            "layer_step": planted["slot_step"][:],
            "slot_step": planted["layer_step"][:],
        },
        "duplicate_steps": {
            "origin": planted["origin"][:],
            "layer_step": planted["layer_step"][:],
            "slot_step": planted["layer_step"][:],
        },
        "out_of_range": {
            "origin": [shipping["p"], planted["origin"][1]],
            "layer_step": planted["layer_step"][:],
            "slot_step": planted["slot_step"][:],
        },
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = {entry["reason"] for entry in corruption_results.values()}
    report["G2_rejects_corruption"] = {
        "pass": (all(entry["rejected"] for entry in corruption_results.values())
                 and len(reasons) == len(corruption_results)),
        "cases": corruption_results,
        "distinct_reasons": len(reasons),
    }

    payload = json.dumps(planted, separators=(",", ":"))
    realistic = ("The repeated closed neighborhoods determine the frame.\n"
                 "<answer>\n```json\n" + payload +
                 "\n```\n</answer>\nAll arithmetic is modulo p.")
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": (parsed == planted and parse_answer("no tagged answer") is None
                 and parse_answer("<answer>{bad}</answer>") is None),
        "json_chars": len(payload),
    }

    guess_rng = random.Random(0x12044298)
    guess_total = 200_000
    guess_hits = 0
    guess_started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping,
                                 random_candidate(shipping, guess_rng))[0])
    guess_elapsed = time.perf_counter() - guess_started
    density = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": density,
        "structure_aware_space": search_space(shipping),
        "sampling_rule": (
            "uniform over all origins and all ordered linearly independent "
            "step-vector pairs over F_p; shape, bounds and independence are "
            "enforced before verification"
        ),
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attack_functions = {
        "coordinate_axes": lambda inst, rng: _axis_attack(inst),
        "degree_extrema_frame": lambda inst, rng: _degree_extrema_attack(inst),
        "lexicographic_local_frame": lambda inst, rng: _lexicographic_local_attack(inst),
        "projective_direction_frequency": (
            lambda inst, rng: _frequency_direction_attack(inst)),
        "visible_degree3_twin_endpoint": (
            lambda inst, rng: _visible_endpoint_attack(inst)),
        "random_restart_256": (
            lambda inst, rng: _random_restart_attack(inst, rng, 256)),
    }
    attack_results = {name: {"successes": 0, "attempts": 0}
                      for name in attack_functions}
    attack_elapsed = {name: 0.0 for name in attack_functions}
    reference_successes = 0
    reference_elapsed = 0.0
    reference_operations = []
    reference_sizes = []
    attack_seeds = list(range(42980, 42988))
    for seed in attack_seeds:
        inst = make_instance(seed=seed,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
        for offset, (name, function) in enumerate(attack_functions.items()):
            rng = random.Random(seed * 1009 + offset)
            started = time.perf_counter()
            candidate = function(inst, rng)
            attack_elapsed[name] += time.perf_counter() - started
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])
            attack_results[name]["attempts"] += 1
        candidate, stats = _reference_algorithm(inst)
        reference_elapsed += stats["wall_clock_sec"]
        reference_operations.append(stats["operations"])
        reference_sizes.append((stats.get("vertices"), stats.get("edges")))
        reference_successes += int(candidate is not None and
                                   verify(inst, candidate)[0])
    for name in attack_results:
        attack_results[name]["wall_clock_sec_total_8"] = round(
            attack_elapsed[name], 6)
    all_failed = all(row["successes"] == 0 for row in attack_results.values())
    reference = {
        "name": (
            "closed-neighborhood twin refinement, quotient-path ordering, and "
            "exact affine-progression recovery"
        ),
        "complexity": "O(N^2 + L^2 + w^3 + NLw^2) exact",
        "wall_clock_sec_total_8": round(reference_elapsed, 6),
        "wall_clock_sec_mean": round(reference_elapsed / len(attack_seeds), 8),
        "operations_mean": sum(reference_operations) // len(reference_operations),
        "operations_min": min(reference_operations),
        "operations_max": max(reference_operations),
        "shipping_vertex_edge_sizes": reference_sizes,
        "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
    }
    intended_operations = (4 * shipping["layers"] +
                           8 * shipping["width_max"] + 20)
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == len(attack_seeds),
        "attacks": attack_results,
        "reference_algorithm": reference,
        "compact_route": {
            "name": "affine twin-path coordinate change",
            "worst_case_exact_operations": intended_operations,
            "count_model": (
                "two vector differences, orientation/scale checks in the two "
                "endpoint classes, and four modular checks per quotient layer"
            ),
        },
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    enumeration_started = time.perf_counter()
    demo_count = enumerate_all(demo)
    enumeration_elapsed = time.perf_counter() - enumeration_started
    strongest = max(attack_elapsed, key=attack_elapsed.get)
    report["G5_density_and_baseline_cost"] = {
        "pass": (density < 1e-6 and all_failed and demo_count is not None
                 and reference_successes == len(attack_seeds)),
        "sampled_density_at_shipping": density,
        "density_hits": guess_hits,
        "density_samples": guess_total,
        "candidate_space_at_shipping": search_space(shipping),
        "exact_demo_valid_answers": demo_count,
        "exact_demo_candidate_space": search_space(demo),
        "exact_demo_enumeration_wall_clock_sec": round(enumeration_elapsed, 6),
        "strongest_failing_attack": strongest,
        "baseline_wall_clock_sec_total_8": round(attack_elapsed[strongest], 6),
        "baseline_attempts_or_iterations": (
            8 * 256 if strongest == "random_restart_256" else 8),
        "reference_algorithm_operations_mean": reference["operations_mean"],
        "reference_algorithm_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
    }

    parameters = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    parameters["n"] *= 2
    doubled = make_instance(seed=991, **parameters)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (doubled_ok and doubled["layers"] == 2 * shipping["layers"]
                 and len(doubled["vertices"]) > len(shipping["vertices"])),
        "original_layers": shipping["layers"],
        "doubled_layers": doubled["layers"],
        "original_vertices": len(shipping["vertices"]),
        "doubled_vertices": len(doubled["vertices"]),
        "fixed_answer_elements": 6,
        "verify_reason": doubled_reason,
    }

    key_failures = []
    invariant_checks = 0
    carried_checks = 0
    for seed in range(20):
        inst = make_instance(seed=seed,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
        original_key = canonical_key(inst)
        transforms = {
            "vertex_index_and_edge_order": _index_permuted(inst, 50000 + seed),
            "affine_coordinate_relabelling": _affine_relabelled(inst, 60000 + seed),
        }
        transforms["composed_relabelling"] = _index_permuted(
            transforms["affine_coordinate_relabelling"], 70000 + seed)
        for name, transformed in transforms.items():
            if canonical_key(transformed) != original_key:
                key_failures.append({"seed": seed, "kind": "invariance",
                                     "transformation": name})
            else:
                invariant_checks += 1
            ok, reason = verify(transformed, transformed["answer"])
            if not ok:
                key_failures.append({"seed": seed, "kind": "carried_witness",
                                     "transformation": name, "reason": reason})
            else:
                carried_checks += 1
        reversed_answer = _reverse_frame(inst, inst["answer"])
        ok, reason = verify(inst, reversed_answer)
        if not ok:
            key_failures.append({"seed": seed, "kind": "layer_reversal_witness",
                                 "reason": reason})
        else:
            carried_checks += 1
    unrelated_keys = [
        canonical_key(make_instance(seed=90000 + seed,
                                    **DIFFICULTY[SHIPPING_DIFFICULTY]))
        for seed in range(20)
    ]
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct_count == 20,
        "invariant_relabellings": invariant_checks,
        "carried_witnesses_valid": carried_checks,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "vertex index permutation and edge reordering",
            "invertible affine coordinate relabelling over F_p",
            "their composition",
            "layer-path reversal (alternate witness)",
        ],
        "failures": key_failures,
    }

    shipping_sizes = [
        _json_answer_size(make_instance(
            seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])["answer"])
        for seed in range(256)
    ]
    answer_chars, answer_tokens, answer_elements = max(shipping_sizes)
    arms = {name: dict(G9_ORACLE_RESULTS.get(
        name, {"solved": 0, "attempts": 0}))
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    within_caps = (answer_chars <= 2000 and answer_elements <= 256 and
                   intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS.get("hinted_verdict", "unrun"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {
            "answer_chars": 2000,
            "answer_elements": 256,
            "intended_route_operations": 300,
        },
    }

    report["pass"] = all(
        value.get("pass", False) for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
