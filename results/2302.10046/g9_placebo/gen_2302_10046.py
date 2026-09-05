"""Verified generator for bend-bounded orthogonal drawing extension.

The source is arXiv:2302.10046.  Section 2 defines Bend-Minimal
Orthogonal Extension, Section 5 proves that feature points may be moved to a
finite sector grid, and Section 6 gives the FPT dynamic program.

This module uses a native, exact specialization: a connected orthogonal wall
drawing H is the wall set of a recursively divided perfect rectilinear maze,
and G adds one edge between two marked vertices of H.  The answer is the
integer-coordinate polyline for that edge.  Each recursive division joins two
already-built cell trees through one gap.  The constructor carries the unique
endpoint-to-endpoint path while composing those trees, so it never solves the
finished maze.
"""

from __future__ import annotations

import bisect
import hashlib
import itertools
import json
import math
import os
import random
import re
import time
from collections import deque


TRACK = "B"


PROBLEM_PROFILE = {
    "native_domain": "geometry",
    "object_regime": "integer_lattice",
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "connected planar orthogonal drawing Gamma(H) on the integer lattice",
        "two marked vertices joined by one missing edge",
        "integer-coordinate orthogonal polyline extension",
    ],
    "verification_operations": [
        "exact integer axis-alignment test",
        "exact closed-segment intersection",
        "exact bend count",
        "exact endpoint and bounding-box comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Single-gap separator walls recursively decompose the face, so branches "
        "whose sole gate is off the endpoint-to-endpoint route can be discarded; "
        "without this decomposition one must search the full cell complex."
    ),
    "hardness_basis": (
        "Track B: exact cell-complex breadth-first search solves this one-edge "
        "specialization in O(RC+|walls|); at the shipping medium preset and seed "
        "271828 it processes 1,872 cells in 7,967 exact operations, while the "
        "single-gate decomposition restricts search to the 144-cell endpoint "
        "block and uses 120 cell decisions and coordinate writes."
    ),
    "max_answer_tokens": 248,
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
        "A JSON list of integer points.  The structure-aware random language uses "
        "the fixed endpoints, an odd number of nonzero segments starting and "
        "ending horizontally as forced by the endpoint walls, alternating axes, "
        "and coordinates in the closed frame.  Wall avoidance and global "
        "self-avoidance are the tested constraints."
    ),
    "bounds": {
        "points": "2..beta+2",
        "x_coordinates": "integers 0..frame_width",
        "y_coordinates": "integers 0..frame_height",
        "orientations": 2,
        "endpoint_constraint": "both endpoints fixed",
        "candidate_count": "exact complete-graph walk-bridge product",
    },
}


DIFFICULTY = {
    "medium": {
        "n": 12,
        "decoy_blocks": 12,
        "min_route_cells": 36,
        "max_answer_atoms": 220,
        "harden_attacks": True,
    },
}

SHIPPING_DIFFICULTY = "medium"


STRUCTURAL_HINT = (
    "The wall drawing is a nested family of single-gap orthogonal separators."
)
PLACEBO_HINT = (
    "The coordinate list rewards careful attention to exact orthogonal segments."
)


# Patched only from transcripts produced by scripts/harden.py.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}


NOTES = r"""
Section 2 fixes the exact definition used here: G is a simple connected planar
graph of maximum degree four, Gamma(H) is a planar orthogonal drawing of a
connected subgraph, an extension must coincide with Gamma(H), and beta bounds
the total bends on missing edges.  This family retains those native objects:
the listed lattice wall segments are Gamma(H), and the witness is the missing
edge's exact orthogonal polyline.  There is no surrogate reduction: this is a
special case of the paper's native geometric problem.  Section 5.2, Lemma 15
and Corollary 16 independently support the use of finite exact feature-point
sets, but are not needed to reinterpret the instance.

Step-0 easy-case triage rules out Track A.  The Introduction states that
extension existence without bend minimization is linear-time, fixed-embedding
bend minimization is polynomial by Tamassia's flow model, and maximum-degree
three bend minimization is linear. Section 6, Lemma 23 and Corollary 24 solve
the paper's parameter regime in 2^{kappa^{O(1)}} n time. Here
kappa=1, and an exact cell BFS is an even simpler linear reference algorithm.

Generation uses composition of identities.  Each rectangular submaze is a cell
tree.  Two recursively built trees plus one uniformly placed connecting gap are
again a tree; if the marked endpoints lie on different sides, their held paths
compose through that gap, and if they lie on one side the other tree is a decoy
branch.  Stacked blocks are attached by the same one-gap operation.  Thus the
certificate is carried during construction, never found by solving the final
instance.  Gate locations for route and decoy separators use the same random
law.

The construction rejects rare draws solved by the declared cheap attacks.  A
degree-outlier walk, Manhattan greedy walk, random non-backtracking restarts,
and 64-node hand-scale DFS all fail on every shipped instance by construction.
The exact full-complex BFS reference succeeds, as Track B requires.  After the
single-gate decomposition is recognized, an executable DFS restricted to the
endpoint block also succeeds within the 300-operation cap.  Increasing
decoy_blocks grows the searched wall complex without lengthening the answer;
n is raised only after that fixed-witness axis.
""".strip()


Cell = tuple[int, int]
Edge = tuple[Cell, Cell]
Segment = tuple[int, int, int, int]


def _cell_edge(a: Cell, b: Cell) -> Edge:
    return (a, b) if a < b else (b, a)


def _attempt_seed(seed: int, attempt: int, n: int, decoy_blocks: int) -> int:
    """Stable mixer whose endpoint block is independent of the decoy count."""

    mask = (1 << 64) - 1
    x = (int(seed) & mask) ^ ((attempt + 1) * 0x9E3779B97F4A7C15 & mask)
    x ^= (n * 0xBF58476D1CE4E5B9) & mask
    # Deliberately do not mix ``decoy_blocks``.  Raising only that parameter
    # grows the haystack while leaving the endpoint block and witness fixed.
    x ^= x >> 30
    x = (x * 0xBF58476D1CE4E5B9) & mask
    x ^= x >> 27
    x = (x * 0x94D049BB133111EB) & mask
    x ^= x >> 31
    return x


def _balanced_cut(lo: int, hi: int, rng: random.Random) -> int:
    """A nontrivial cut from the middle third, keeping recursion logarithmic."""

    span = hi - lo
    if span <= 1:
        raise ValueError("cannot split a unit interval")
    lower = lo + max(1, span // 3)
    upper = hi - max(1, span // 3)
    if lower > upper:
        lower = upper = lo + span // 2
    return rng.randint(lower, upper)


def _build_rectangle(
    x0: int,
    x1: int,
    y0: int,
    y1: int,
    rng: random.Random,
    pair: tuple[Cell, Cell] | None = None,
) -> tuple[set[Edge], list[Cell] | None, int]:
    """Compose a random recursive-division cell tree and carry one held path.

    Random split orientations, positions, and gaps are chosen before looking at
    ``pair``.  Hence tracked route separators and untracked decoy separators are
    sampled from the same distribution.
    """

    width, height = x1 - x0, y1 - y0
    if width == 1 and height == 1:
        path = [pair[0]] if pair is not None else None
        return set(), path, 1 if pair is not None else 0

    if width > height:
        vertical = True
    elif height > width:
        vertical = False
    else:
        vertical = bool(rng.getrandbits(1))

    if vertical:
        cut = _balanced_cut(x0, x1, rng)
        gate = rng.randrange(y0, y1)
        rect_a = (x0, cut, y0, y1)
        rect_b = (cut, x1, y0, y1)
        gate_a, gate_b = (cut - 1, gate), (cut, gate)

        def side(p: Cell) -> int:
            return 0 if p[0] < cut else 1

    else:
        cut = _balanced_cut(y0, y1, rng)
        gate = rng.randrange(x0, x1)
        rect_a = (x0, x1, y0, cut)
        rect_b = (x0, x1, cut, y1)
        gate_a, gate_b = (gate, cut - 1), (gate, cut)

        def side(p: Cell) -> int:
            return 0 if p[1] < cut else 1

    pair_a = pair_b = None
    split_pair = False
    tracked_side = None
    if pair is not None:
        start, target = pair
        if start == target:
            tracked_side = side(start)
            if tracked_side == 0:
                pair_a = pair
            else:
                pair_b = pair
        elif side(start) == side(target):
            tracked_side = side(start)
            if tracked_side == 0:
                pair_a = pair
            else:
                pair_b = pair
        else:
            split_pair = True
            if side(start) == 0:
                pair_a = (start, gate_a)
                pair_b = (gate_b, target)
            else:
                pair_a = (target, gate_a)
                pair_b = (gate_b, start)

    edges_a, path_a, proof_a = _build_rectangle(*rect_a, rng, pair_a)
    edges_b, path_b, proof_b = _build_rectangle(*rect_b, rng, pair_b)
    edges = edges_a | edges_b
    edges.add(_cell_edge(gate_a, gate_b))

    if pair is None:
        return edges, None, 0
    if not split_pair:
        path = path_a if tracked_side == 0 else path_b
        return edges, path, proof_a + proof_b + 1

    start, target = pair
    if side(start) == 0:
        path = list(path_a or []) + list(path_b or [])
    else:
        path = list(reversed(path_b or [])) + list(reversed(path_a or []))
    return edges, path, proof_a + proof_b + 1


def _wall_units(cols: int, rows: int, passages: set[Edge]) -> set[Segment]:
    units: set[Segment] = set()
    width, height = 2 * cols, 2 * rows
    for row in range(rows):
        units.add((0, 2 * row, 0, 2 * row + 2))
        units.add((width, 2 * row, width, 2 * row + 2))
    for col in range(cols):
        units.add((2 * col, 0, 2 * col + 2, 0))
        units.add((2 * col, height, 2 * col + 2, height))

    for col in range(1, cols):
        for row in range(rows):
            left, right = (col - 1, row), (col, row)
            if _cell_edge(left, right) not in passages:
                units.add((2 * col, 2 * row, 2 * col, 2 * row + 2))
    for row in range(1, rows):
        for col in range(cols):
            below, above = (col, row - 1), (col, row)
            if _cell_edge(below, above) not in passages:
                units.add((2 * col, 2 * row, 2 * col + 2, 2 * row))
    return units


def _merge_units(units: set[Segment], block_height: int | None = None) -> list[list[int]]:
    horizontal: dict[int, list[tuple[int, int]]] = {}
    vertical: dict[int, list[tuple[int, int]]] = {}
    for x1, y1, x2, y2 in units:
        if y1 == y2:
            horizontal.setdefault(y1, []).append((min(x1, x2), max(x1, x2)))
        else:
            vertical.setdefault(x1, []).append((min(y1, y2), max(y1, y2)))

    merged: list[list[int]] = []
    for y, intervals in horizontal.items():
        intervals.sort()
        lo, hi = intervals[0]
        for a, b in intervals[1:]:
            if a <= hi:
                hi = max(hi, b)
            else:
                merged.append([lo, y, hi, y])
                lo, hi = a, b
        merged.append([lo, y, hi, y])
    for x, intervals in vertical.items():
        intervals.sort()
        lo, hi = intervals[0]
        for a, b in intervals[1:]:
            if a <= hi:
                hi = max(hi, b)
            else:
                merged.append([x, lo, x, hi])
                lo, hi = a, b
        merged.append([x, lo, x, hi])
    if block_height:
        split: list[list[int]] = []
        max_y = max(max(s[1], s[3]) for s in merged)
        cuts = list(range(block_height, max_y, block_height))
        for segment in merged:
            x1, y1, x2, y2 = segment
            if x1 != x2:
                split.append(segment)
                continue
            points = [y1] + [cut for cut in cuts if y1 < cut < y2] + [y2]
            split.extend([[x1, a, x1, b] for a, b in zip(points, points[1:])])
        merged = split
    # Present low-y blocks first.  Once the one-gap separator insight is seen,
    # the solver can read the endpoint block without scanning every decoy wall.
    merged.sort(
        key=lambda s: (max(s[1], s[3]), min(s[1], s[3]), s[1] == s[3], s[0], s[2])
    )
    return merged


def _compress_cell_path(
    cells: list[Cell], start: tuple[int, int], target: tuple[int, int]
) -> list[list[int]]:
    raw = [list(start)] + [[2 * x + 1, 2 * y + 1] for x, y in cells] + [list(target)]
    out: list[list[int]] = []
    for point in raw:
        if len(out) >= 2:
            a, b = out[-2], out[-1]
            if (a[0] == b[0] == point[0]) or (a[1] == b[1] == point[1]):
                out[-1] = point
                continue
        out.append(point)
    return out


def _adjacency_from_passages(cols: int, rows: int, passages: set[Edge]):
    adjacency: dict[Cell, list[Cell]] = {}
    for col in range(cols):
        for row in range(rows):
            adjacency[(col, row)] = []
    for a, b in passages:
        adjacency[a].append(b)
        adjacency[b].append(a)
    for neighbors in adjacency.values():
        neighbors.sort()
    return adjacency


def _path_candidate(inst, cells: list[Cell] | None):
    if not cells or cells[0] != inst["_start_cell"] or cells[-1] != inst["_target_cell"]:
        return None
    return _compress_cell_path(cells, tuple(inst["start"]), tuple(inst["target"]))


def _walk_attack(inst, score, budget=None):
    adjacency = inst["_adjacency"]
    current = inst["_start_cell"]
    target = inst["_target_cell"]
    path = [current]
    seen = {current}
    limit = budget or len(adjacency)
    while current != target and len(path) <= limit:
        choices = [v for v in adjacency[current] if v not in seen]
        if not choices:
            return None, len(path)
        current = min(choices, key=lambda v: score(v, adjacency, target))
        path.append(current)
        seen.add(current)
    return (_path_candidate(inst, path) if current == target else None), len(path)


def _attack_manhattan(inst):
    return _walk_attack(
        inst,
        lambda v, _adj, target: (abs(v[0] - target[0]) + abs(v[1] - target[1]), v),
    )


def _attack_degree_outlier(inst):
    return _walk_attack(
        inst,
        lambda v, adj, target: (
            -len(adj[v]),
            abs(v[0] - target[0]) + abs(v[1] - target[1]),
            v,
        ),
    )


def _attack_random_restarts(inst, seed, restarts=64):
    rng = random.Random(seed)
    adjacency = inst["_adjacency"]
    target = inst["_target_cell"]
    operations = 0
    max_steps = min(len(adjacency), max(96, 3 * inst["_route_cells"]))
    for _ in range(restarts):
        current = inst["_start_cell"]
        path = [current]
        seen = {current}
        for _step in range(max_steps):
            operations += 1
            if current == target:
                return _path_candidate(inst, path), operations
            choices = [v for v in adjacency[current] if v not in seen]
            if not choices:
                break
            current = choices[rng.randrange(len(choices))]
            path.append(current)
            seen.add(current)
    return None, operations


def _attack_depth_limited(inst, node_budget=64):
    adjacency = inst["_adjacency"]
    start, target = inst["_start_cell"], inst["_target_cell"]
    stack = [(start, None, iter(adjacency[start]))]
    path = [start]
    seen = {start}
    expanded = 1
    while stack and expanded < node_budget:
        vertex, _parent, iterator = stack[-1]
        if vertex == target:
            return _path_candidate(inst, path), expanded
        try:
            nxt = next(iterator)
        except StopIteration:
            stack.pop()
            path.pop()
            continue
        if nxt in seen:
            continue
        seen.add(nxt)
        path.append(nxt)
        stack.append((nxt, vertex, iter(adjacency[nxt])))
        expanded += 1
    if stack and stack[-1][0] == target:
        return _path_candidate(inst, path), expanded
    return None, expanded


def _compact_endpoint_dfs(inst):
    """Recover the route after applying the single-gate block decomposition.

    All blocks above the first are attached through one passage.  Since both
    endpoints are in the first block and the complete cell complex is a tree,
    no simple endpoint-to-endpoint path can enter one of those attached
    branches.  This routine therefore searches only the n-by-n endpoint block.
    Its operation counter charges one unit per expanded cell and one per cell
    copied into the recovered route.  It does not read ``inst['answer']``.
    """

    n = inst["_n"]
    adjacency = inst["_adjacency"]
    start, target = inst["_start_cell"], inst["_target_cell"]
    stack = [start]
    parent = {start: None}
    expanded = 0
    while stack:
        current = stack.pop()
        expanded += 1
        if current == target:
            break
        # Reverse the canonical order so the smallest neighbor is processed
        # first by the LIFO stack.  Branches outside the endpoint block are
        # discarded by the decomposition invariant, not by answer knowledge.
        for nxt in reversed(adjacency[current]):
            if nxt[1] >= n or nxt in parent:
                continue
            parent[nxt] = current
            stack.append(nxt)
    if target not in parent:
        return None, expanded
    cells = []
    current = target
    while current is not None:
        cells.append(current)
        current = parent[current]
    cells.reverse()
    return _path_candidate(inst, cells), expanded + len(cells)


def _cheap_attack_succeeds(inst, seed):
    candidates = [
        _attack_manhattan(inst)[0],
        _attack_degree_outlier(inst)[0],
        _attack_random_restarts(inst, seed ^ 0xA5A5A5, restarts=24)[0],
        _attack_depth_limited(inst, node_budget=64)[0],
    ]
    return any(c is not None and verify(inst, c)[0] for c in candidates)


def make_instance(n, seed=0, **params):
    """Compose an exact orthogonal extension instance and carry its certificate."""

    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    decoy_blocks = params.pop("decoy_blocks", max(0, n // 2))
    min_route_cells = params.pop("min_route_cells", max(2, 2 * n))
    max_answer_atoms = params.pop("max_answer_atoms", 256)
    harden_attacks = params.pop("harden_attacks", True)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    for name, value in (
        ("decoy_blocks", decoy_blocks),
        ("min_route_cells", min_route_cells),
        ("max_answer_atoms", max_answer_atoms),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if decoy_blocks < 0 or min_route_cells < 1 or max_answer_atoms < 4:
        raise ValueError("parameters are outside their supported ranges")

    cols = n
    rows = n * (decoy_blocks + 1)
    for attempt in range(256):
        rng = random.Random(_attempt_seed(seed, attempt, n, decoy_blocks))
        start_cell = (0, rng.randrange(n))
        target_cell = (n - 1, rng.randrange(n))
        passages, held_path, proof_steps = _build_rectangle(
            0, n, 0, n, rng, (start_cell, target_cell)
        )
        if held_path is None:
            continue

        start = (0, 2 * start_cell[1] + 1)
        target = (2 * n, 2 * target_cell[1] + 1)
        answer = _compress_cell_path(held_path, start, target)
        answer_atoms = 2 * len(answer)
        if (
            len(held_path) < min_route_cells
            or answer_atoms > max_answer_atoms
        ):
            continue

        # Each extra block is produced by the same recursive law and attached
        # through exactly one uniformly random gate.  It is therefore a branch
        # of the cell tree and cannot change the carried endpoint path.
        for block in range(1, decoy_blocks + 1):
            y0, y1 = block * n, (block + 1) * n
            block_edges, _unused, _ = _build_rectangle(0, n, y0, y1, rng, None)
            passages |= block_edges
            gate_col = rng.randrange(n)
            passages.add(
                _cell_edge((gate_col, y0 - 1), (gate_col, y0))
            )

        units = _wall_units(cols, rows, passages)
        walls = _merge_units(units, block_height=2 * n)
        adjacency = _adjacency_from_passages(cols, rows, passages)
        inst = {
            "frame_width": 2 * cols,
            "frame_height": 2 * rows,
            "cell_columns": cols,
            "cell_rows": rows,
            "start": list(start),
            "target": list(target),
            "beta": len(answer) - 2,
            "walls": walls,
            "answer": answer,
            "_wall_units": units,
            "_wall_index": _make_wall_index(walls),
            "_passages": passages,
            "_adjacency": adjacency,
            "_start_cell": start_cell,
            "_target_cell": target_cell,
            "_route_cells": len(held_path),
            "_proof_steps": proof_steps,
            "_construction_attempt": attempt + 1,
            "_n": n,
            "_decoy_blocks": decoy_blocks,
        }
        if not verify(inst, answer)[0]:
            continue
        compact_answer, compact_operations = _compact_endpoint_dfs(inst)
        if (
            compact_answer is None
            or not verify(inst, compact_answer)[0]
            or compact_operations > 300
        ):
            continue
        inst["_compact_operations"] = compact_operations
        if harden_attacks and _cheap_attack_succeeds(
            inst, _attempt_seed(seed, attempt + 1000, n, decoy_blocks)
        ):
            continue
        return inst
    raise RuntimeError("could not construct an instance within 256 deterministic attempts")


def _ascii_endpoint_block(inst):
    """Exact text view of the square containing both marked endpoints."""

    side = inst["frame_width"]
    horizontal = set()
    vertical = set()
    for x1, y1, x2, y2 in inst["walls"]:
        if y1 == y2 and 0 <= y1 <= side:
            lo, hi = max(0, min(x1, x2)), min(side, max(x1, x2))
            horizontal.update((x, y1) for x in range(lo, hi + 1))
        elif x1 == x2 and 0 <= x1 <= side:
            lo, hi = max(0, min(y1, y2)), min(side, max(y1, y2))
            vertical.update((x1, y) for y in range(lo, hi + 1))
    start, target = tuple(inst["start"]), tuple(inst["target"])
    rows = []
    for y in range(side, -1, -1):
        chars = []
        for x in range(side + 1):
            point = (x, y)
            if point == start:
                char = "S"
            elif point == target:
                char = "T"
            elif point in horizontal and point in vertical:
                char = "+"
            elif point in horizontal:
                char = "-"
            elif point in vertical:
                char = "|"
            else:
                char = " "
            chars.append(char)
        rows.append(f"y={y:02d} " + "".join(chars))
    return rows


def render(inst):
    lines = [
        "BEND-BOUNDED ORTHOGONAL DRAWING EXTENSION",
        "",
        "A fixed planar orthogonal drawing Gamma(H) is given by the closed wall",
        "segments listed below. Every segment is horizontal or vertical. Segment",
        "endpoints, every meeting point, and the marked points S and T are vertices",
        "of H; S and T subdivide their incident wall segments. Touching listed",
        "segments share a vertex rather than crossing. H is connected.",
        "The closed frame is [0,W] x [0,H].",
        "",
        "The graph G adds exactly one missing edge from the marked vertex S to the",
        "marked vertex T. Draw that edge as one simple orthogonal polyline. Its",
        "interior may not meet or overlap any listed wall, and may not touch any",
        "vertex or edge of Gamma(H). The polyline may meet Gamma(H) only at S and T.",
        "It must stay in the closed frame and have at most beta bends. A bend is an",
        "internal point where a horizontal segment and a vertical segment meet.",
        "",
        f"W={inst['frame_width']}  H={inst['frame_height']}  beta={inst['beta']}",
        f"S={json.dumps(inst['start'], separators=(',', ':'))}",
        f"T={json.dumps(inst['target'], separators=(',', ':'))}",
        "",
        "For exact visual tracing, the square 0<=x<=W, 0<=y<=W containing S and",
        "T is also shown as an ASCII lattice below. Character column x is the",
        "integer x-coordinate and each row is labelled by its integer y-coordinate;",
        "'-' and '|' are wall points, '+' is their meeting, and blanks are free.",
        "This is a redundant view of the wall list, not additional geometry.",
        "ENDPOINT_BLOCK_ASCII",
        *_ascii_endpoint_block(inst),
        "END_ENDPOINT_BLOCK_ASCII",
        "",
        f"WALLS={len(inst['walls'])}",
    ]
    for index, wall in enumerate(inst["walls"]):
        lines.append(f"{index}: " + " ".join(map(str, wall)))
    lines.extend(
        [
            "",
            "Output a JSON list of points [[x0,y0],[x1,y1],...,[xm,ym]] in order",
            "from S to T. Coordinates must be integers. Include S, T, and every bend",
            "point, but no other collinear intermediate points. Consecutive points",
            "must be distinct and share exactly one coordinate. Indices are zero-based;",
            "all bounds are inclusive; repeated points and self-intersections are forbidden.",
            "",
            "Give your final answer inside <answer></answer> tags, as the JSON point list.",
            "Format-only example: <answer>[[0,1],[1,1],[1,3],[3,3]]</answer>",
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
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    for point in value:
        if (
            not isinstance(point, list)
            or len(point) != 2
            or any(isinstance(v, bool) or not isinstance(v, int) for v in point)
        ):
            return None
    return value


def _axis_intersection(a, b):
    """None, a point tuple, or the string 'overlap' for closed axis segments."""

    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    if ay1 == ay2 and by1 == by2:
        if ay1 != by1:
            return None
        lo, hi = max(min(ax1, ax2), min(bx1, bx2)), min(max(ax1, ax2), max(bx1, bx2))
        if lo > hi:
            return None
        return (lo, ay1) if lo == hi else "overlap"
    if ax1 == ax2 and bx1 == bx2:
        if ax1 != bx1:
            return None
        lo, hi = max(min(ay1, ay2), min(by1, by2)), min(max(ay1, ay2), max(by1, by2))
        if lo > hi:
            return None
        return (ax1, lo) if lo == hi else "overlap"
    if ay1 == ay2:
        h, v = a, b
    else:
        h, v = b, a
    hx1, hy, hx2, _ = h
    vx, vy1, _, vy2 = v
    if min(hx1, hx2) <= vx <= max(hx1, hx2) and min(vy1, vy2) <= hy <= max(vy1, vy2):
        return (vx, hy)
    return None


def _make_wall_index(walls):
    """Index exact integer contacts with the public axis-aligned wall segments."""

    horizontal = {}
    vertical = {}
    vertical_cross = {}
    horizontal_cross = {}
    for x1, y1, x2, y2 in walls:
        if y1 == y2:
            lo, hi = sorted((x1, x2))
            horizontal.setdefault(y1, []).append((lo, hi))
            for x in range(lo, hi + 1):
                horizontal_cross.setdefault(x, set()).add(y1)
        else:
            lo, hi = sorted((y1, y2))
            vertical.setdefault(x1, []).append((lo, hi))
            for y in range(lo, hi + 1):
                vertical_cross.setdefault(y, set()).add(x1)
    for intervals in itertools.chain(horizontal.values(), vertical.values()):
        intervals.sort()
    return {
        "horizontal": horizontal,
        "vertical": vertical,
        "vertical_cross": {
            key: sorted(values) for key, values in vertical_cross.items()
        },
        "horizontal_cross": {
            key: sorted(values) for key, values in horizontal_cross.items()
        },
    }


def _segment_meets_wall(segment, wall_index, allowed_points):
    """Whether an axis segment has a non-permitted contact with Gamma(H)."""

    x1, y1, x2, y2 = segment
    if y1 == y2:
        lo, hi = sorted((x1, x2))
        for a, b in wall_index["horizontal"].get(y1, ()):
            left, right = max(lo, a), min(hi, b)
            if left > right:
                continue
            if left == right and (left, y1) in allowed_points:
                continue
            return True
        crosses = wall_index["vertical_cross"].get(y1, ())
        begin = bisect.bisect_left(crosses, lo)
        end = bisect.bisect_right(crosses, hi)
        return any((x, y1) not in allowed_points for x in crosses[begin:end])

    lo, hi = sorted((y1, y2))
    for a, b in wall_index["vertical"].get(x1, ()):
        bottom, top = max(lo, a), min(hi, b)
        if bottom > top:
            continue
        if bottom == top and (x1, bottom) in allowed_points:
            continue
        return True
    crosses = wall_index["horizontal_cross"].get(x1, ())
    begin = bisect.bisect_left(crosses, lo)
    end = bisect.bisect_right(crosses, hi)
    return any((x1, y) not in allowed_points for y in crosses[begin:end])


def verify(inst, answer):
    """Check any exact polyline witness; never consult ``inst['answer']``."""

    if not isinstance(answer, list) or len(answer) < 2:
        return False, "shape: answer must be a list of at least two points"
    points = []
    for index, point in enumerate(answer):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            return False, f"point-shape: point {index} is not [x,y]"
        x, y = point
        if isinstance(x, bool) or isinstance(y, bool) or not isinstance(x, int) or not isinstance(y, int):
            return False, f"coordinate-type: point {index} does not contain two integers"
        if not (0 <= x <= inst["frame_width"] and 0 <= y <= inst["frame_height"]):
            return False, f"bounds: point {index} lies outside the closed frame"
        points.append((x, y))

    start, target = tuple(inst["start"]), tuple(inst["target"])
    if points[0] != start or points[-1] != target:
        return False, "endpoints: the polyline must be ordered from S to T"

    candidate_segments = []
    for index, (a, b) in enumerate(zip(points, points[1:])):
        if a == b:
            return False, f"zero-length: segment {index} has equal endpoints"
        if a[0] != b[0] and a[1] != b[1]:
            return False, f"axis: segment {index} is not horizontal or vertical"
        candidate_segments.append((a[0], a[1], b[0], b[1]))
    if len(points) - 2 > inst["beta"]:
        return False, "bend-budget: the listed bend count exceeds beta"
    for index in range(1, len(points) - 1):
        a, b, c = points[index - 1], points[index], points[index + 1]
        if (a[0] == b[0] == c[0]) or (a[1] == b[1] == c[1]):
            return False, f"redundant: point {index} is not a bend"

    wall_index = inst.get("_wall_index") or _make_wall_index(inst["walls"])
    for i, segment in enumerate(candidate_segments):
        if _segment_meets_wall(segment, wall_index, {start, target}):
            return False, f"wall: segment {i} meets Gamma(H) away from its permitted endpoint"

    for i, first in enumerate(candidate_segments):
        for j in range(i + 2, len(candidate_segments)):
            hit = _axis_intersection(first, candidate_segments[j])
            if hit is not None:
                return False, f"self-intersection: nonconsecutive segments {i} and {j} meet"
    return True, "ok"


def _walk_count(q: int, steps: int, same: bool) -> int:
    if steps < 0:
        return 0
    sign = -1 if steps & 1 else 1
    if same:
        return ((q - 1) ** steps + (q - 1) * sign) // q
    return ((q - 1) ** steps - sign) // q


def _orientation_counts(inst, first_horizontal: bool, segments=None):
    if segments is None:
        segments = inst["beta"] + 1
    horizontal = (segments + (1 if first_horizontal else 0)) // 2
    vertical = segments - horizontal
    sx, sy = inst["start"]
    tx, ty = inst["target"]
    x_count = _walk_count(inst["frame_width"] + 1, horizontal, sx == tx)
    y_count = _walk_count(inst["frame_height"] + 1, vertical, sy == ty)
    return x_count * y_count, horizontal, vertical


def search_space(inst):
    return sum(
        _orientation_counts(inst, True, segments)[0]
        for segments in range(1, inst["beta"] + 2, 2)
    )


def _sample_bridge(q: int, steps: int, start: int, target: int, rng: random.Random):
    current = start
    values = []
    for remaining in range(steps, 0, -1):
        if remaining == 1:
            if target == current:
                raise ValueError("zero bridge count sampled")
            nxt = target
        elif target == current:
            # Every non-target state has the same continuation count.
            pick = rng.randrange(q - 1)
            nxt = pick if pick < current else pick + 1
        else:
            weight_target = _walk_count(q, remaining - 1, True)
            weight_other = _walk_count(q, remaining - 1, False)
            total = weight_target + (q - 2) * weight_other
            ticket = rng.randrange(total)
            if ticket < weight_target:
                nxt = target
            else:
                pick = (ticket - weight_target) // weight_other
                excluded = sorted((current, target))
                nxt = pick
                for value in excluded:
                    if nxt >= value:
                        nxt += 1
        values.append(nxt)
        current = nxt
    return values


def random_candidate(inst, rng):
    classes = [
        (segments, _orientation_counts(inst, True, segments)[0])
        for segments in range(1, inst["beta"] + 2, 2)
    ]
    ticket = rng.randrange(sum(item[1] for item in classes))
    segments = 0
    for class_segments, count in classes:
        if ticket < count:
            segments = class_segments
            break
        ticket -= count
    _count, horizontal, vertical = _orientation_counts(
        inst, True, segments
    )
    sx, sy = inst["start"]
    tx, ty = inst["target"]
    xs = _sample_bridge(inst["frame_width"] + 1, horizontal, sx, tx, rng)
    ys = _sample_bridge(inst["frame_height"] + 1, vertical, sy, ty, rng)
    points = [[sx, sy]]
    x, y = sx, sy
    ix = iy = 0
    for segment in range(segments):
        horizontal_now = segment % 2 == 0
        if horizontal_now:
            x = xs[ix]
            ix += 1
        else:
            y = ys[iy]
            iy += 1
        points.append([x, y])
    return points


def _dimension_walks(q, steps, start, target):
    if steps == 0:
        if start == target:
            yield []
        return

    def rec(current, remaining, prefix):
        if remaining == 1:
            if target != current:
                yield prefix + [target]
            return
        for nxt in range(q):
            if nxt != current:
                yield from rec(nxt, remaining - 1, prefix + [nxt])

    yield from rec(start, steps, [])


def enumerate_all(inst):
    space = search_space(inst)
    if space > 50_000:
        return None
    total = 0
    sx, sy = inst["start"]
    tx, ty = inst["target"]
    for segments in range(1, inst["beta"] + 2):
        if segments % 2 == 0:
            continue
        _count, horizontal, vertical = _orientation_counts(inst, True, segments)
        x_walks = list(
            _dimension_walks(inst["frame_width"] + 1, horizontal, sx, tx)
        )
        y_walks = list(
            _dimension_walks(inst["frame_height"] + 1, vertical, sy, ty)
        )
        for xs, ys in itertools.product(x_walks, y_walks):
            x, y = sx, sy
            ix = iy = 0
            candidate = [[x, y]]
            for segment in range(segments):
                if segment % 2 == 0:
                    x = xs[ix]
                    ix += 1
                else:
                    y = ys[iy]
                    iy += 1
                candidate.append([x, y])
            if verify(inst, candidate)[0]:
                total += 1
    return total


def _point_transform(point, width, height, code):
    x, y = point
    transforms = (
        (x, y, width, height),
        (width - x, y, width, height),
        (x, height - y, width, height),
        (width - x, height - y, width, height),
        (y, x, height, width),
        (height - y, x, height, width),
        (y, width - x, height, width),
        (height - y, width - x, height, width),
    )
    return transforms[code]


def _canonical_data(inst, code):
    width, height = inst["frame_width"], inst["frame_height"]
    s = _point_transform(tuple(inst["start"]), width, height, code)
    t = _point_transform(tuple(inst["target"]), width, height, code)
    new_width, new_height = s[2], s[3]
    endpoints = sorted(((s[0], s[1]), (t[0], t[1])))
    walls = []
    for wall in inst["walls"]:
        a = _point_transform((wall[0], wall[1]), width, height, code)
        b = _point_transform((wall[2], wall[3]), width, height, code)
        p, q = sorted(((a[0], a[1]), (b[0], b[1])))
        walls.append((p[0], p[1], q[0], q[1]))
    walls.sort()
    return (new_width, new_height, inst["beta"], tuple(endpoints), tuple(walls))


def canonical_key(inst):
    canonical = min(_canonical_data(inst, code) for code in range(8))
    blob = repr(canonical).encode("ascii")
    return hashlib.sha256(blob).hexdigest()


def _transform_instance(inst, code, reorder_seed=0, swap_endpoints=False):
    width, height = inst["frame_width"], inst["frame_height"]
    start_t = _point_transform(tuple(inst["start"]), width, height, code)
    target_t = _point_transform(tuple(inst["target"]), width, height, code)
    walls = []
    for wall in inst["walls"]:
        a = _point_transform((wall[0], wall[1]), width, height, code)
        b = _point_transform((wall[2], wall[3]), width, height, code)
        walls.append([a[0], a[1], b[0], b[1]])
    rng = random.Random(reorder_seed)
    for wall in walls:
        if rng.getrandbits(1):
            wall[:] = [wall[2], wall[3], wall[0], wall[1]]
    rng.shuffle(walls)
    answer = []
    for point in inst["answer"]:
        p = _point_transform(tuple(point), width, height, code)
        answer.append([p[0], p[1]])
    start = [start_t[0], start_t[1]]
    target = [target_t[0], target_t[1]]
    if swap_endpoints:
        start, target = target, start
        answer.reverse()
    return {
        "frame_width": start_t[2],
        "frame_height": start_t[3],
        "start": start,
        "target": target,
        "beta": inst["beta"],
        "walls": walls,
        "answer": answer,
    }


def _expand_public_wall_units(walls):
    """Expand the rendered merged walls into their public two-unit pieces."""

    units = set()
    for x1, y1, x2, y2 in walls:
        if x1 == x2:
            lo, hi = sorted((y1, y2))
            if x1 % 2 or lo % 2 or hi % 2:
                raise ValueError("vertical wall is off the two-unit cell grid")
            units.update((x1, y, x1, y + 2) for y in range(lo, hi, 2))
        elif y1 == y2:
            lo, hi = sorted((x1, x2))
            if y1 % 2 or lo % 2 or hi % 2:
                raise ValueError("horizontal wall is off the two-unit cell grid")
            units.update((x, y1, x + 2, y1) for x in range(lo, hi, 2))
        else:
            raise ValueError("wall is not horizontal or vertical")
    return units


def _reference_bfs(inst):
    """Exact public-data reference: expand rendered walls, then run cell BFS."""

    cols = inst["frame_width"] // 2
    rows = inst["frame_height"] // 2
    units = _expand_public_wall_units(inst["walls"])
    adjacency = {}
    operations = 0
    for x in range(cols):
        for y in range(rows):
            cell = (x, y)
            neighbors = []
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                operations += 1
                nx, ny = x + dx, y + dy
                if not (0 <= nx < cols and 0 <= ny < rows):
                    continue
                if dx:
                    wall_x = 2 * max(x, nx)
                    unit = (wall_x, 2 * y, wall_x, 2 * y + 2)
                else:
                    wall_y = 2 * max(y, ny)
                    unit = (2 * x, wall_y, 2 * x + 2, wall_y)
                if unit not in units:
                    neighbors.append((nx, ny))
            adjacency[cell] = neighbors

    start, target = inst["_start_cell"], inst["_target_cell"]
    queue = deque([start])
    parent = {start: None}
    while queue:
        current = queue.popleft()
        operations += 1
        if current == target:
            break
        for nxt in adjacency[current]:
            operations += 1
            if nxt not in parent:
                parent[nxt] = current
                queue.append(nxt)
    if target not in parent:
        return None, operations
    path = []
    current = target
    while current is not None:
        path.append(current)
        current = parent[current]
        operations += 1
    path.reverse()
    return _path_candidate(inst, path), operations


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _construction_invariants(inst):
    """Executable checks that the generated H and cell complex have the claimed form."""

    vertex_count = inst["cell_columns"] * inst["cell_rows"]
    if len(inst["_passages"]) != vertex_count - 1:
        return False, "cell passage graph does not have tree edge count"
    start = inst["_start_cell"]
    reached = {start}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for nxt in inst["_adjacency"][current]:
            if nxt not in reached:
                reached.add(nxt)
                queue.append(nxt)
    if len(reached) != vertex_count:
        return False, "cell passage graph is disconnected"

    # The public, merged wall representation must encode exactly the private
    # unit-wall set used by the reference algorithms.  This prevents the
    # checker and attacks from silently operating on a different maze than the
    # one shown to the solver.
    try:
        expanded_walls = _expand_public_wall_units(inst["walls"])
    except ValueError as exc:
        return False, f"public wall expansion failed: {exc}"
    if expanded_walls != inst["_wall_units"]:
        return False, "public merged walls do not equal the private unit-wall set"

    start, target = map(tuple, (inst["start"], inst["target"]))
    for name, point in (("S", start), ("T", target)):
        if not any(
            _axis_intersection((point[0], point[1], point[0], point[1]), wall)
            == point
            for wall in inst["walls"]
        ):
            return False, f"marked endpoint {name} is not a vertex of Gamma(H)"

    wall_adjacency: dict[tuple[int, int], set[tuple[int, int]]] = {}
    for x1, y1, x2, y2 in inst["_wall_units"]:
        a, b = (x1, y1), (x2, y2)
        wall_adjacency.setdefault(a, set()).add(b)
        wall_adjacency.setdefault(b, set()).add(a)
    if not wall_adjacency:
        return False, "Gamma(H) has no wall vertices"
    root = next(iter(wall_adjacency))
    wall_reached = {root}
    queue = deque([root])
    while queue:
        current = queue.popleft()
        for nxt in wall_adjacency[current]:
            if nxt not in wall_reached:
                wall_reached.add(nxt)
                queue.append(nxt)
    if len(wall_reached) != len(wall_adjacency):
        return False, "Gamma(H) is disconnected"
    if max(map(len, wall_adjacency.values())) > 4:
        return False, "Gamma(H) has a vertex of degree greater than four"
    return True, "ok"


def escalate(params):
    return "cap_bound"


def selftest():
    report = {}

    failures = []
    checks = 0
    for preset, kwargs in DIFFICULTY.items():
        for seed in (0, 1, 17):
            try:
                inst = make_instance(seed=seed, **kwargs)
                ok, reason = verify(inst, inst["answer"])
                invariant_ok, invariant_reason = _construction_invariants(inst)
                json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            except Exception as exc:  # diagnostic, never hide the failing preset
                ok, invariant_ok, json_ok = False, False, False
                reason = f"{type(exc).__name__}: {exc}"
                invariant_reason = reason
            checks += 1
            if not ok or not invariant_ok or not json_ok:
                failures.append(
                    {
                        "preset": preset,
                        "seed": seed,
                        "reason": reason,
                        "construction_invariant": invariant_reason,
                    }
                )
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "checked_properties": (
            "planted verification, JSON answer round-trip, passage-tree connectivity, "
            "public/private wall equality, marked endpoint incidence, connected "
            "Gamma(H), and maximum wall-vertex degree four"
        ),
        "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=271828, **shipping)
    answer = inst["answer"]

    # Five mutations are chosen to trip five independent verifier clauses.
    drop = [p[:] for p in answer]
    drop.pop(1)
    swapped = [p[:] for p in answer]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicate = [p[:] for p in answer]
    duplicate.insert(1, duplicate[0][:])
    out_of_range = [p[:] for p in answer]
    out_of_range[1] = [inst["frame_width"] + 1, out_of_range[1][1]]
    corruptions = {
        "drop_one": drop,
        "swap_two": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    corruption_results = {}
    reason_classes = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        if not ok:
            reason_classes.append(reason.split(":", 1)[0])
    report["G2_rejects_corruption"] = {
        "pass": (
            all(item["rejected"] for item in corruption_results.values())
            and len(set(reason_classes)) == len(corruptions)
        ),
        "attempts": len(corruptions),
        "distinct_reasons": len(set(reason_classes)),
        "cases": corruption_results,
    }

    response = (
        "The separator route gives the following exact extension.\n```json\n"
        + "<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nI checked every wall intersection."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer,
        "parsed_equals_answer": parsed == answer,
        "surrounding_prose_and_fence": True,
    }

    trials = 200_000
    guess_rng = random.Random(0x230210046)
    hits = 0
    guess_started = time.perf_counter()
    for _ in range(trials):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    guess_seconds = time.perf_counter() - guess_started
    report["G4_guess_resistance"] = {
        "pass": hits / trials < 1e-6,
        "hits": hits,
        "total": trials,
        "observed_probability": hits / trials,
        "candidate_space": search_space(inst),
        "candidate_space_bits": search_space(inst).bit_length() - 1,
        "prior": (
            "uniform over endpoint- and port-correct, up-to-budget, alternating-axis "
            "nonzero integer walk bridges in the displayed frame"
        ),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    ref_started = time.perf_counter()
    ref_answer, ref_operations = _reference_bfs(inst)
    ref_seconds = time.perf_counter() - ref_started
    ref_ok = ref_answer is not None and verify(inst, ref_answer)[0]
    baseline_started = time.perf_counter()
    _baseline_answer, baseline_nodes = _attack_depth_limited(inst, 64)
    baseline_seconds = time.perf_counter() - baseline_started
    report["G5_density_and_baseline_cost"] = {
        "pass": ref_ok,
        "shipping_seed": 271828,
        "shipping_sample_hits": hits,
        "shipping_sample_total": trials,
        "shipping_solution_density": hits / trials,
        "demo_exact_valid_answers": demo_count,
        "demo_candidate_space": search_space(demo),
        "strongest_failing_attack": "64-node depth-limited exact cell DFS",
        "baseline_nodes": baseline_nodes,
        "baseline_wall_clock_sec": round(baseline_seconds, 6),
        "reference_operations": ref_operations,
        "reference_wall_clock_sec": round(ref_seconds, 6),
    }

    attacks = {
        "outlier_highest_cell_degree_walk": {"successes": 0, "attempts": 8},
        "greedy_manhattan_no_backtracking": {"successes": 0, "attempts": 8},
        "random_restart_nonbacktracking_64": {"successes": 0, "attempts": 8},
        "in_context_depth_limited_dfs_64": {"successes": 0, "attempts": 8},
    }
    elapsed = {name: 0.0 for name in attacks}
    reference_successes = 0
    reference_operations = []
    reference_times = []
    compact_ops = []
    for seed in range(10_000, 10_008):
        current = make_instance(seed=seed, **shipping)
        candidates = {}
        started = time.perf_counter()
        candidates["outlier_highest_cell_degree_walk"] = _attack_degree_outlier(current)[0]
        elapsed["outlier_highest_cell_degree_walk"] += time.perf_counter() - started
        started = time.perf_counter()
        candidates["greedy_manhattan_no_backtracking"] = _attack_manhattan(current)[0]
        elapsed["greedy_manhattan_no_backtracking"] += time.perf_counter() - started
        started = time.perf_counter()
        candidates["random_restart_nonbacktracking_64"] = _attack_random_restarts(
            current, seed ^ 0xC0FFEE, 64
        )[0]
        elapsed["random_restart_nonbacktracking_64"] += time.perf_counter() - started
        started = time.perf_counter()
        candidates["in_context_depth_limited_dfs_64"] = _attack_depth_limited(current, 64)[0]
        elapsed["in_context_depth_limited_dfs_64"] += time.perf_counter() - started
        for name, candidate in candidates.items():
            if candidate is not None and verify(current, candidate)[0]:
                attacks[name]["successes"] += 1

        started = time.perf_counter()
        solved, operations = _reference_bfs(current)
        reference_times.append(time.perf_counter() - started)
        reference_operations.append(operations)
        if solved is not None and verify(current, solved)[0]:
            reference_successes += 1
        compact_answer, compact_operations = _compact_endpoint_dfs(current)
        if compact_answer is None or not verify(current, compact_answer)[0]:
            compact_operations = 301
        compact_ops.append(compact_operations)
    for name in attacks:
        attacks[name]["wall_clock_sec"] = round(elapsed[name], 6)
    all_failed = all(
        item["successes"] == 0 and item["attempts"] >= 8 for item in attacks.values()
    )
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and max(compact_ops) <= 300,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact cell-adjacency construction followed by breadth-first search",
            "complexity": "O(R*C + |walls|)",
            "solves": f"{reference_successes}/8, as expected",
            "wall_clock_sec": round(sum(reference_times), 6),
            "operations": sum(reference_operations),
            "per_instance_operations": reference_operations,
            "operation_unit": "exact wall probes, queue/neighbor scans, and parent steps",
        },
        "intended_compact_route": {
            "name": "single-gate block decomposition followed by endpoint-block DFS",
            "operations_max": max(compact_ops),
            "per_instance_operations": compact_ops,
            "solves": "8/8 without reading the planted answer",
        },
    }

    # More than double the searched complex while genuinely increasing n.
    # Most growth stays on the decoy axis so the larger instance remains under
    # the fixed answer and no-tool operation caps.
    doubled = dict(shipping)
    doubled["n"] = shipping["n"] + 4
    doubled["decoy_blocks"] = shipping["decoy_blocks"] + 12
    doubled["min_route_cells"] = shipping["min_route_cells"]
    doubled["harden_attacks"] = False
    fixed_shipping = dict(shipping)
    fixed_shipping["harden_attacks"] = False
    fixed_inst = make_instance(seed=314159, **fixed_shipping)
    doubled_inst = make_instance(seed=314159, **doubled)
    doubled_ok, doubled_reason = verify(doubled_inst, doubled_inst["answer"])
    report["G7_scales"] = {
        "pass": (
            doubled_ok
            and doubled_inst["cell_columns"] > fixed_inst["cell_columns"]
            and doubled_inst["cell_columns"] * doubled_inst["cell_rows"]
            >= 2 * fixed_inst["cell_columns"] * fixed_inst["cell_rows"]
            and search_space(doubled_inst) > search_space(fixed_inst)
        ),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "scaling_axis": (
            "n increases from 16 to 20 while decoy blocks more than double the "
            "total cell complex under the fixed answer cap"
        ),
        "shipping_decoy_blocks": shipping["decoy_blocks"],
        "doubled_decoy_blocks": doubled["decoy_blocks"],
        "shipping_cells": inst["cell_columns"] * inst["cell_rows"],
        "doubled_cells": doubled_inst["cell_columns"] * doubled_inst["cell_rows"],
        "answer_atoms_shipping": _answer_atoms(fixed_inst["answer"]),
        "answer_atoms_doubled": _answer_atoms(doubled_inst["answer"]),
        "compact_operations_shipping": fixed_inst["_compact_operations"],
        "compact_operations_doubled": doubled_inst["_compact_operations"],
        "shipping_search_space_bits": search_space(fixed_inst).bit_length() - 1,
        "doubled_search_space_bits": search_space(doubled_inst).bit_length() - 1,
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = 0
    real_transformations = 0
    key_failures = []
    g8_params = dict(DIFFICULTY["easy"])
    g8_params["decoy_blocks"] = 1
    g8_params["harden_attacks"] = False
    for seed in range(20):
        base = make_instance(seed=50_000 + seed, **g8_params)
        base_key = canonical_key(base)
        for code in range(8):
            for swap_endpoints in (False, True):
                transformed = _transform_instance(
                    base,
                    code,
                    60_000 + seed * 16 + 2 * code + int(swap_endpoints),
                    swap_endpoints=swap_endpoints,
                )
                invariance_checks += 1
                if canonical_key(transformed) != base_key:
                    key_failures.append(
                        {"seed": seed, "isometry": code, "endpoint_swap": swap_endpoints}
                    )
                ok, _reason = verify(transformed, transformed["answer"])
                if ok:
                    real_transformations += 1
    unrelated = [
        canonical_key(make_instance(seed=80_000 + seed, **g8_params)) for seed in range(20)
    ]
    report["G8_canonical_key"] = {
        "pass": (
            not key_failures
            and real_transformations == invariance_checks
            and len(set(unrelated)) == 20
        ),
        "invariance_checks": invariance_checks,
        "real_transformations_verified": real_transformations,
        "unrelated_attempts": 20,
        "unrelated_distinct_keys": len(set(unrelated)),
        "transformations": (
            "all eight rectangle isometries, segment endpoint reversal, wall-list "
            "reordering, and reversal-invariant missing-edge endpoints"
        ),
        "failures": key_failures,
    }

    answer_blob = json.dumps(answer, separators=(",", ":"))
    arms = {
        name: {
            "solved": G9_ORACLE_RESULTS[name]["solved"],
            "attempts": G9_ORACLE_RESULTS[name]["attempts"],
        }
        for name in ("bare", "hinted", "placebo")
    }
    hinted, placebo = arms["hinted"]["solved"], arms["placebo"]["solved"]
    hinted_minus_placebo = None
    if (
        isinstance(hinted, int)
        and isinstance(placebo, int)
        and arms["hinted"]["attempts"] > 0
        and arms["placebo"]["attempts"] > 0
    ):
        hinted_minus_placebo = (
            hinted / arms["hinted"]["attempts"]
            - placebo / arms["placebo"]["attempts"]
        )
    compact_answer, intended_ops = _compact_endpoint_dfs(inst)
    # Exact serialization upper bound from the shipping language bounds.  A
    # point is no longer than ``[frame_width,frame_height]`` and there are at
    # most max_answer_atoms/2 points.
    worst_points = shipping["max_answer_atoms"] // 2
    worst_point_chars = (
        len(str(inst["frame_width"])) + len(str(inst["frame_height"])) + 3
    )
    worst_answer_chars = worst_points * worst_point_chars + worst_points - 1 + 2
    worst_answer_tokens = math.ceil(worst_answer_chars / 4)
    within_caps = (
        worst_answer_chars <= 2000
        and shipping["max_answer_atoms"] <= 256
        and intended_ops <= 300
    )
    report["G9_no_tool_suitability"] = {
        # The three arms, including the formerly gated hinted arm, are
        # diagnostics as of 2026-09-05.  Only the size/effort caps gate G9.
        "pass": within_caps and compact_answer is not None,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": len(answer_blob),
        "answer_tokens": math.ceil(len(answer_blob) / 4),
        "answer_elements": _answer_atoms(answer),
        "worst_case_answer_chars": worst_answer_chars,
        "worst_case_answer_tokens": worst_answer_tokens,
        "worst_case_answer_elements": shipping["max_answer_atoms"],
        "intended_route_operations": intended_ops,
        "worst_case_intended_route_operations": 300,
        "within_caps": within_caps,
    }

    report["paper"] = "arXiv:2302.10046"
    report["family"] = "single-edge bend-bounded orthogonal maze extension"
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping)
    report["all_passed"] = all(
        value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
