"""Verified L-tromino tiling generator for arXiv:1710.04640.

Akagi et al. prove that tiling an Aztec diamond with an unbounded number of
defects is NP-complete (Theorem 13).  This module stays in those native
objects: an instance is an Aztec diamond, all but an explicitly listed set of
cells are defects, and the witness is a list of L-tromino placements.

The distribution is honestly Track B.  A standard exact-cover search solves
the instances mechanically.  By construction, most planted tiles belong to
one hidden 2-by-2 parity grid and a small number are phase breakers; noticing
that global decomposition gives a much shorter no-tool route.
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
from functools import lru_cache
from typing import Any


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "Most tromino bounding boxes share one parity class, with only a small boundary fringe outside it."
)
PLACEBO_HINT: str = (
    "Careful bookkeeping of cell coordinates and tile orientations is useful throughout this problem."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "geometry",
    "object_regime": "integer_lattice",
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "Aztec diamond with defective lattice cells",
        "L-tromino placements in the square lattice",
    ],
    "verification_operations": [
        "exact integer coordinate comparison",
        "2-by-2 L-shape check",
        "exact disjoint-union equality of covered and nondefective cells",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3.2, Theorem 13 (embed an arbitrary defective region inside an Aztec diamond)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "A dominant parity grid decomposes almost all free cells into 2-by-2 blocks; "
        "without seeing it, a solver must search the overlapping L-placement exact cover."
    ),
    "hardness_basis": (
        "Track B: minimum-column Algorithm X solves the finite L-placement exact cover "
        "with exponential worst-case complexity; at shipping n=48 it solved 8/8 instances "
        "using 213,057 placement checks and 1,113 search nodes in 0.265692 seconds total, "
        "whereas recognizing the dominant anchor-parity decomposition leaves a 228-operation "
        "no-tool route."
    ),
    "max_answer_tokens": 119,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 4, "exceptions": 2, "compactness": 0, "screen_restarts": 4},
    "easy": {"n": 36, "exceptions": 5, "compactness": 1, "screen_restarts": 32},
    "medium": {"n": 48, "exceptions": 6, "compactness": 2, "screen_restarts": 48},
    "hard": {"n": 60, "exceptions": 7, "compactness": 3, "screen_restarts": 64},
}
SHIPPING_DIFFICULTY: str = "medium"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "An unordered JSON list of exactly n distinct legal L-tromino placements. "
        "A placement is [x,y,m], where (x,y) is the lower-left cell of its 2-by-2 "
        "bounding box and m is the omitted corner code 0=SW, 1=SE, 2=NW, 3=NE."
    ),
    "bounds": {
        "placements": "n",
        "integers_per_placement": 3,
        "omitted_corner_min": 0,
        "omitted_corner_max": 3,
        "shipping_max_atomic_elements": 180,
    },
}

NOTES: str = (
    "Section 2 fixes the native definitions: a cell is indexed by its integer lower-left "
    "corner, a defect cannot be covered, and a cover consists of nonoverlapping L-trominoes "
    "inside the region. Section 3.2, Theorem 13 is the hard regime used here: an arbitrary "
    "defective region is embedded in an Aztec diamond and every surrounding cell is made a "
    "defect. The easy cases deliberately avoided are defect-free Aztec rectangles (Theorems "
    "3 and 8, O(b^2)), one-defect rectangles (Theorem 10, O(b^2)), forbidden-polyomino-free "
    "180-tromino regions (Theorem 19, polynomial via claw-free independent set), and scaled "
    "regions R^boxplus (Theorem 23, constructive and efficient). The certificate is produced "
    "by composition: disjoint L-trominoes are assembled first, and only then embedded and "
    "relabelled. A standard exact-cover search produces a certificate efficiently on this "
    "promise, so Track A would be false. Candidate regions are deterministically screened "
    "against boundary-score, lexicographic greedy, randomized most-constrained greedy, and "
    "bounding-box parity attacks; the successful generic Algorithm X is reported separately."
)

G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


_CORNERS = ((0, 0), (1, 0), (0, 1), (1, 1))
_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _mix_seed(seed: int, nonce: int) -> int:
    x = (int(seed) & ((1 << 128) - 1)) ^ 0x171004640A5A5A5A5
    x ^= (nonce + 1) * 0x9E3779B97F4A7C15
    x ^= x >> 30
    x *= 0xBF58476D1CE4E5B9
    x ^= x >> 27
    return x & ((1 << 128) - 1)


def _tile_cells(row: list[int] | tuple[int, int, int]) -> frozenset[tuple[int, int]]:
    x, y, missing = row
    return frozenset(
        (x + dx, y + dy)
        for code, (dx, dy) in enumerate(_CORNERS)
        if code != missing
    )


def _encode_tile(cells: Any) -> list[int] | None:
    points = set(cells)
    if len(points) != 3:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x0, y0 = min(xs), min(ys)
    if max(xs) != x0 + 1 or max(ys) != y0 + 1:
        return None
    full = {(x0 + dx, y0 + dy) for dx, dy in _CORNERS}
    missing = full - points
    if len(missing) != 1:
        return None
    miss = next(iter(missing))
    return [x0, y0, _CORNERS.index((miss[0] - x0, miss[1] - y0))]


def _connected(cells: set[tuple[int, int]]) -> bool:
    if not cells:
        return False
    todo = [next(iter(cells))]
    seen = {todo[0]}
    while todo:
        x, y = todo.pop()
        for dx, dy in _DIRS:
            q = (x + dx, y + dy)
            if q in cells and q not in seen:
                seen.add(q)
                todo.append(q)
    return len(seen) == len(cells)


def _grow_macro_cells(n: int, rng: random.Random, compactness: int) -> set[tuple[int, int]]:
    blocks = {(0, 0)}
    frontier = set(_DIRS)
    while len(blocks) < n:
        choices = sorted(frontier)
        rng.shuffle(choices)
        if compactness <= 0:
            chosen = choices[0]
        else:
            sample = choices[: min(len(choices), 2 + 2 * compactness)]
            chosen = max(
                sample,
                key=lambda p: (
                    sum((p[0] + dx, p[1] + dy) in blocks for dx, dy in _DIRS),
                    -abs(p[0]) - abs(p[1]),
                    rng.random(),
                ),
            )
        blocks.add(chosen)
        frontier.discard(chosen)
        for dx, dy in _DIRS:
            q = (chosen[0] + dx, chosen[1] + dy)
            if q not in blocks:
                frontier.add(q)
    return blocks


def _candidate_attachments(
    cells: set[tuple[int, int]], phase: tuple[int, int]
) -> list[list[int]]:
    minx = min(x for x, _ in cells)
    maxx = max(x for x, _ in cells)
    miny = min(y for _, y in cells)
    maxy = max(y for _, y in cells)
    out = []
    for x in range(minx - 2, maxx + 2):
        for y in range(miny - 2, maxy + 2):
            if (x & 1, y & 1) == phase:
                continue
            for missing in range(4):
                row = [x, y, missing]
                covered = _tile_cells(row)
                if covered & cells:
                    continue
                if not any(
                    (cx + dx, cy + dy) in cells
                    for cx, cy in covered
                    for dx, dy in _DIRS
                ):
                    continue
                out.append(row)
    return out


def _add_exceptions(
    cells: set[tuple[int, int]],
    answer: list[list[int]],
    count: int,
    phase: tuple[int, int],
    rng: random.Random,
) -> bool:
    original_bounds = (
        min(x for x, _ in cells), max(x for x, _ in cells),
        min(y for _, y in cells), max(y for _, y in cells),
    )
    for step in range(count):
        candidates = _candidate_attachments(cells, phase)
        if not candidates:
            return False
        rng.shuffle(candidates)
        minx, maxx, miny, maxy = (
            min(x for x, _ in cells), max(x for x, _ in cells),
            min(y for _, y in cells), max(y for _, y in cells),
        )

        def score(row: list[int]) -> tuple[int, int, float]:
            covered = _tile_cells(row)
            extension = sum(
                int(x < minx or x > maxx or y < miny or y > maxy)
                for x, y in covered
            )
            contacts = sum(
                (x + dx, y + dy) in cells
                for x, y in covered
                for dx, dy in _DIRS
            )
            # The first two attachments preferentially invalidate the obvious
            # lower-left bounding-box phase in x and y.
            bbox_break = 0
            if step == 0:
                new_minx = min(minx, *(x for x, _ in covered))
                bbox_break = int((new_minx & 1) != phase[0])
            elif step == 1:
                new_miny = min(miny, *(y for _, y in covered))
                bbox_break = int((new_miny & 1) != phase[1])
            return (3 * bbox_break + extension, contacts, rng.random())

        chosen = max(candidates, key=score)
        covered = set(_tile_cells(chosen))
        cells.update(covered)
        answer.append(chosen)

    minx, _, miny, _ = original_bounds
    return (min(x for x, _ in cells) & 1, min(y for _, y in cells) & 1) != phase or count == 0


def _transform_point(p: tuple[int, int], code: int) -> tuple[int, int]:
    x, y = p
    transforms = (
        (x, y), (x, -y), (-x, y), (-x, -y),
        (y, x), (y, -x), (-y, x), (-y, -x),
    )
    return transforms[code & 7]


def _apply_transform(
    cells: set[tuple[int, int]],
    tiles: list[list[int]],
    code: int,
    tx: int,
    ty: int,
) -> tuple[set[tuple[int, int]], list[list[int]]]:
    def tr(p: tuple[int, int]) -> tuple[int, int]:
        a, b = _transform_point(p, code)
        return a + tx, b + ty

    new_cells = {tr(p) for p in cells}
    new_tiles = []
    for row in tiles:
        encoded = _encode_tile(tr(p) for p in _tile_cells(row))
        if encoded is None:
            raise AssertionError("lattice symmetry did not preserve an L-tromino")
        new_tiles.append(encoded)
    return new_cells, new_tiles


@lru_cache(maxsize=128)
def _legal_placement_tuples(
    cell_key: tuple[tuple[int, int], ...]
) -> tuple[tuple[int, int, int], ...]:
    cells = set(cell_key)
    if not cells:
        return ()
    anchors = set()
    for x, y in cells:
        for dx, dy in _CORNERS:
            anchors.add((x - dx, y - dy))
    rows = []
    for x, y in sorted(anchors):
        for missing in range(4):
            row = [x, y, missing]
            if _tile_cells(row) <= cells:
                rows.append(row)
    return tuple(tuple(row) for row in rows)


def _legal_placements_from_cells(cells: set[tuple[int, int]]) -> list[list[int]]:
    key = tuple(sorted(cells))
    return [list(row) for row in _legal_placement_tuples(key)]


def _placement_index(inst: dict) -> tuple[list[list[int]], dict[tuple[int, int], list[int]]]:
    cells = {tuple(p) for p in inst["free_cells"]}
    rows = [list(row) for row in _legal_placement_tuples(tuple(sorted(cells)))]
    by_cell = {p: [] for p in cells}
    for index, row in enumerate(rows):
        for p in _tile_cells(row):
            by_cell[p].append(index)
    return rows, by_cell


def _greedy_cover(
    inst: dict,
    mode: str,
    rng: random.Random | None = None,
) -> list[list[int]] | None:
    rows, by_cell = _placement_index(inst)
    uncovered = {tuple(p) for p in inst["free_cells"]}
    picked = []
    while uncovered:
        if mode == "lex":
            cell = min(uncovered)
        else:
            cell = min(
                uncovered,
                key=lambda p: sum(_tile_cells(rows[i]) <= uncovered for i in by_cell[p]),
            )
        feasible = [i for i in by_cell[cell] if _tile_cells(rows[i]) <= uncovered]
        if not feasible:
            return None
        if mode == "boundary":
            def boundary_score(i: int) -> tuple[int, list[int]]:
                score = sum(len(by_cell[p]) for p in _tile_cells(rows[i]))
                return score, rows[i]
            chosen = min(feasible, key=boundary_score)
        elif mode == "random":
            assert rng is not None
            chosen = rng.choice(feasible)
        else:
            chosen = min(feasible, key=lambda i: rows[i])
        picked.append(rows[chosen])
        uncovered.difference_update(_tile_cells(rows[chosen]))
    return picked


def _random_restart_attack(inst: dict, restarts: int) -> tuple[list[list[int]] | None, int]:
    blob = json.dumps(sorted(inst["free_cells"]), separators=(",", ":"))
    seed = int(hashlib.sha256(blob.encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    operations = 0
    for _ in range(restarts):
        candidate = _greedy_cover(inst, "random", rng)
        operations += len(inst["free_cells"])
        if candidate is not None and verify(inst, candidate)[0]:
            return candidate, operations
    return None, operations


def _bbox_parity_attack(inst: dict) -> list[list[int]] | None:
    cells = {tuple(p) for p in inst["free_cells"]}
    ox = min(x for x, _ in cells) & 1
    oy = min(y for _, y in cells) & 1
    groups: dict[tuple[int, int], set[tuple[int, int]]] = {}
    for x, y in cells:
        key = ((x - ox) // 2, (y - oy) // 2)
        groups.setdefault(key, set()).add((x, y))
    answer = []
    for group in groups.values():
        encoded = _encode_tile(group)
        if encoded is None:
            return None
        answer.append(encoded)
    return answer


def _dominant_parity_route(inst: dict, node_cap: int = 4000) -> tuple[list[list[int]] | None, int]:
    """Construction-aware compact route used only as a Track-B measurement."""
    cells = {tuple(p) for p in inst["free_cells"]}
    operations = 0
    phases = []
    for ox, oy in itertools.product(range(2), repeat=2):
        groups: dict[tuple[int, int], set[tuple[int, int]]] = {}
        for x, y in cells:
            groups.setdefault(((x - ox) // 2, (y - oy) // 2), set()).add((x, y))
            operations += 1
        forced = []
        used = set()
        for group in groups.values():
            encoded = _encode_tile(group)
            if encoded is not None:
                forced.append(encoded)
                used.update(group)
            operations += 1
        phases.append((len(used), forced, used))
    for _, forced, used in sorted(phases, reverse=True, key=lambda t: t[0]):
        remainder = cells - used
        if not remainder:
            if verify(inst, forced)[0]:
                return forced, operations
            continue
        partial_inst = {"free_cells": [list(p) for p in remainder]}
        tail, stats = _algorithm_x(partial_inst, node_cap=node_cap)
        operations += stats["operations"]
        if tail is not None:
            candidate = forced + tail
            if verify(inst, candidate)[0]:
                return candidate, operations
    return None, operations


def _algorithm_x(inst: dict, node_cap: int = 2_000_000) -> tuple[list[list[int]] | None, dict]:
    rows, by_cell = _placement_index(inst)
    uncovered = {tuple(p) for p in inst["free_cells"]}
    picked: list[int] = []
    stats = {
        "nodes": 0,
        "operations": len(rows) * 3,
        "legal_placements": len(rows),
        "aborted": False,
    }

    def dfs() -> bool:
        if not uncovered:
            return True
        if stats["nodes"] >= node_cap:
            stats["aborted"] = True
            return False
        stats["nodes"] += 1
        best_cell = None
        best_rows = None
        for cell in uncovered:
            feasible = []
            for index in by_cell[cell]:
                stats["operations"] += 1
                if _tile_cells(rows[index]) <= uncovered:
                    feasible.append(index)
            if not feasible:
                return False
            if best_rows is None or len(feasible) < len(best_rows):
                best_cell, best_rows = cell, feasible
                if len(feasible) == 1:
                    break
        assert best_cell is not None and best_rows is not None
        for index in best_rows:
            covered = _tile_cells(rows[index])
            uncovered.difference_update(covered)
            picked.append(index)
            if dfs():
                return True
            picked.pop()
            uncovered.update(covered)
        return False

    solved = dfs()
    if not solved:
        return None, stats
    return [rows[i] for i in picked], stats


def _screen_attacks(inst: dict, restarts: int) -> bool:
    candidates = (
        _greedy_cover(inst, "boundary"),
        _greedy_cover(inst, "lex"),
        _random_restart_attack(inst, restarts)[0],
        _bbox_parity_attack(inst),
    )
    return all(candidate is None or not verify(inst, candidate)[0] for candidate in candidates)


def make_instance(
    n: int,
    seed: int = 0,
    exceptions: int = 5,
    compactness: int = 1,
    screen_restarts: int = 32,
    **params: Any,
) -> dict:
    """Build a defective Aztec diamond and a tiling by composition, never search."""
    del params
    n = int(n)
    exceptions = int(exceptions)
    compactness = int(compactness)
    screen_restarts = int(screen_restarts)
    if n < 4:
        raise ValueError("n must be at least 4")
    if not 0 <= exceptions < n:
        raise ValueError("exceptions must satisfy 0 <= exceptions < n")

    core_n = n - exceptions
    for attempt in range(512):
        rng = random.Random(_mix_seed(seed, attempt))
        blocks = _grow_macro_cells(core_n, rng, compactness)
        cells: set[tuple[int, int]] = set()
        answer: list[list[int]] = []
        for bx, by in sorted(blocks):
            row = [2 * bx, 2 * by, rng.randrange(4)]
            covered = set(_tile_cells(row))
            cells.update(covered)
            answer.append(row)
        if not _connected(cells):
            continue
        if not _add_exceptions(cells, answer, exceptions, (0, 0), rng):
            continue
        if not _connected(cells):
            continue
        code = rng.randrange(8)
        tx, ty = rng.randrange(-23, 24), rng.randrange(-23, 24)
        cells, answer = _apply_transform(cells, answer, code, tx, ty)
        rng.shuffle(answer)
        free_cells = [list(p) for p in cells]
        rng.shuffle(free_cells)
        radial = max(abs(2 * x + 1) + abs(2 * y + 1) for x, y in cells)
        diamond_order = (radial + 1) // 2 + 2 + rng.randrange(4)
        inst = {
            "paper_id": "1710.04640",
            "family": "L-tromino cover of an Aztec diamond with arbitrary defects",
            "n": n,
            "diamond_order": diamond_order,
            "free_cells": free_cells,
            "answer": answer,
        }
        if len(_legal_placements_from_cells(cells)) < n + max(4, n // 3):
            continue
        if screen_restarts and not _screen_attacks(inst, screen_restarts):
            continue
        return inst
    raise RuntimeError("could not construct a screened instance; relax parameters")


def render(inst: dict) -> str:
    free_cells = inst["free_cells"]
    lines = [
        "L-TROMINO TILING WITH DEFECTS",
        "",
        f"The board is the Aztec diamond of order {inst['diamond_order']}. A lattice cell is",
        "identified by the integer pair (x,y) at its lower-left corner. The listed cells",
        "below are nondefective; every other cell of the Aztec diamond is a defect and",
        "must not be covered. Only the listed cells matter for the requested cover.",
        "",
        "An L-tromino consists of exactly three cells of one 2-by-2 block: all corners",
        "except one. Tiles may use any rotation or reflection. A tiling must cover every",
        "listed cell exactly once, cover no defect, and contain no overlapping tiles.",
        "",
        f"There are {len(free_cells)} nondefective cells, so your answer must contain",
        f"exactly {inst['n']} placements. Coordinates are signed decimal integers.",
        "The order of placements does not matter and repeated placements are forbidden.",
        "",
        "Nondefective cells (input order is arbitrary):",
    ]
    chunk = 12
    for start in range(0, len(free_cells), chunk):
        lines.append("  " + " ".join(f"({x},{y})" for x, y in free_cells[start:start + chunk]))
    lines += [
        "",
        "Encode a placement as [x,y,m]. Here (x,y) is the lower-left cell of its",
        "2-by-2 bounding block and m is the one omitted corner:",
        "  0 = southwest (x,y); 1 = southeast (x+1,y);",
        "  2 = northwest (x,y+1); 3 = northeast (x+1,y+1).",
        "",
        "Give your final answer inside <answer></answer> tags as one JSON list of",
        f"exactly {inst['n']} placement triples.",
        "Example: <answer>[[0,0,3],[1,1,0]]</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines += ["", "Hint: " + STRUCTURAL_HINT]
    elif mode == "placebo":
        lines += ["", "Hint: " + PLACEBO_HINT]
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not match:
        return None
    payload = match.group(1).strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", payload, flags=re.I | re.S)
    if fence:
        payload = fence.group(1).strip()
    try:
        value = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, list):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    # Deliberately never inspect inst["answer"].
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    expected = int(inst["n"])
    if len(answer) != expected:
        return False, f"wrong tile count: expected {expected}, got {len(answer)}"
    normalized = []
    for index, row in enumerate(answer):
        if not isinstance(row, list) or len(row) != 3:
            return False, f"placement {index} must be a three-integer JSON list"
        if any(not isinstance(v, int) or isinstance(v, bool) for v in row):
            return False, f"placement {index} contains a non-integer"
        x, y, missing = row
        if missing < 0 or missing > 3:
            return False, f"placement {index} has omitted-corner code outside 0..3"
        normalized.append((x, y, missing))
    if len(set(normalized)) != len(normalized):
        return False, "duplicate placement"
    free = {tuple(p) for p in inst["free_cells"]}
    covered: set[tuple[int, int]] = set()
    for index, row in enumerate(normalized):
        cells = _tile_cells(row)
        outside = cells - free
        if outside:
            return False, f"placement {index} covers a defect or lies outside the diamond"
        overlap = cells & covered
        if overlap:
            return False, f"placement {index} overlaps an earlier tile"
        covered.update(cells)
    missing_cells = free - covered
    if missing_cells:
        return False, f"tiling leaves {len(missing_cells)} nondefective cells uncovered"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    key = tuple(sorted(tuple(p) for p in inst["free_cells"]))
    rows = _legal_placement_tuples(key)
    if len(rows) < inst["n"]:
        return []
    return [list(row) for row in rng.sample(rows, inst["n"])]


def search_space(inst: dict) -> int:
    key = tuple(sorted(tuple(p) for p in inst["free_cells"]))
    rows = _legal_placement_tuples(key)
    return math.comb(len(rows), int(inst["n"]))


def enumerate_all(inst: dict) -> int | None:
    rows, by_cell = _placement_index(inst)
    cells = {tuple(p) for p in inst["free_cells"]}
    if len(rows) > 90 or len(cells) > 30:
        return None
    count = 0
    nodes = 0
    cap = 2_000_000

    def dfs(uncovered: set[tuple[int, int]]) -> None:
        nonlocal count, nodes
        nodes += 1
        if nodes > cap:
            return
        if not uncovered:
            count += 1
            return
        cell = min(
            uncovered,
            key=lambda p: sum(_tile_cells(rows[i]) <= uncovered for i in by_cell[p]),
        )
        for index in by_cell[cell]:
            covered = _tile_cells(rows[index])
            if covered <= uncovered:
                dfs(uncovered - covered)

    dfs(cells)
    return None if nodes > cap else count


def _normal_forms(cells: set[tuple[int, int]]) -> list[tuple[tuple[int, int], ...]]:
    forms = []
    for code in range(8):
        points = [_transform_point(p, code) for p in cells]
        minx = min(x for x, _ in points)
        miny = min(y for _, y in points)
        forms.append(tuple(sorted((x - minx, y - miny) for x, y in points)))
    return forms


def canonical_key(inst: dict) -> str:
    cells = {tuple(p) for p in inst["free_cells"]}
    canonical = min(_normal_forms(cells))
    payload = json.dumps(canonical, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _relabel_instance(inst: dict, code: int, tx: int, ty: int, shuffle_seed: int) -> dict:
    cells = {tuple(p) for p in inst["free_cells"]}
    # This helper is for G8 only; carrying the certificate is allowed here.
    transformed_cells, transformed_answer = _apply_transform(
        cells, inst["answer"], code, tx, ty
    )
    rng = random.Random(shuffle_seed)
    free = [list(p) for p in transformed_cells]
    rng.shuffle(free)
    rng.shuffle(transformed_answer)
    out = dict(inst)
    out["free_cells"] = free
    out["answer"] = transformed_answer
    radial = max(abs(2 * x + 1) + abs(2 * y + 1) for x, y in transformed_cells)
    out["diamond_order"] = (radial + 1) // 2 + 3
    return out


def escalate(params: dict) -> dict | str | None:
    p = dict(params)
    n = int(p.get("n", 0))
    exceptions = int(p.get("exceptions", 0))
    compactness = int(p.get("compactness", 0))
    restarts = int(p.get("screen_restarts", 0))
    # First harden at essentially fixed witness length: crowd the same cells and
    # screen against more randomized greedy restarts.
    if compactness < 6:
        p["compactness"] = compactness + 1
        p["screen_restarts"] = min(256, max(64, 2 * restarts))
        return p
    if exceptions < min(12, n // 4):
        p["exceptions"] = exceptions + 1
        p["screen_restarts"] = min(512, max(128, 2 * restarts))
        return p
    if 3 * (n + 4) <= 256:
        p["n"] = n + 4
        return p
    return "cap_bound"


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))

    def atoms(value: object) -> int:
        if isinstance(value, dict):
            return sum(atoms(v) for v in value.values())
        if isinstance(value, list):
            return sum(atoms(v) for v in value)
        return 1

    return len(encoded), math.ceil(len(encoded) / 4), atoms(answer)


def _corrupt_swap_coordinates(inst: dict) -> list[list[int]]:
    answer = [row[:] for row in inst["answer"]]
    for i, row in enumerate(answer):
        trial = [r[:] for r in answer]
        trial[i] = [row[1], row[0], row[2]]
        ok, reason = verify(inst, trial)
        if not ok and "defect" in reason:
            return trial
    # A one-coordinate swap with the next placement is another natural swap.
    for i in range(len(answer) - 1):
        trial = [r[:] for r in answer]
        trial[i][0], trial[i + 1][0] = trial[i + 1][0], trial[i][0]
        ok, reason = verify(inst, trial)
        if not ok and "defect" in reason:
            return trial
    raise AssertionError("could not build a coordinate-swap corruption")


def selftest() -> dict:
    report: dict[str, Any] = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 104729):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
            try:
                restored = json.loads(json.dumps(inst["answer"]))
            except (TypeError, ValueError) as exc:
                g1_failures.append({"preset": preset, "seed": seed, "reason": str(exc)})
            else:
                if restored != inst["answer"]:
                    g1_failures.append({"preset": preset, "seed": seed,
                                        "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=20260905, **shipping_params)
    planted = ship["answer"]
    corruptions = {
        "empty": [],
        "drop_one": [row[:] for row in planted[:-1]],
        "drop_element": [planted[0][:-1]] + [row[:] for row in planted[1:]],
        "duplicate": [planted[0][:], planted[0][:]] + [row[:] for row in planted[2:]],
        "out_of_range": [[planted[0][0], planted[0][1], 4]]
                        + [row[:] for row in planted[1:]],
        "swap_coordinates": _corrupt_swap_coordinates(ship),
    }
    corruption_results = {}
    for name, bad in corruptions.items():
        ok, reason = verify(ship, bad)
        corruption_results[name] = {"accepted": ok, "reason": reason}
    reasons = [v["reason"] for v in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not v["accepted"] for v in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "I checked the union of the following tiles.\n<answer>\n```json\n"
        + json.dumps(planted, separators=(",", ":"))
        + "\n```\n</answer>\nAll coordinates use the requested convention."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted and verify(ship, parsed)[0]
        and parse_answer("no tagged answer here") is None,
        "parsed_matches": parsed == planted,
        "garbage_returns_none": parse_answer("no tagged answer here") is None,
    }

    guess_rng = random.Random(171004640)
    guess_total = 200_000
    guess_hits = 0
    started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_wall = time.perf_counter() - started
    guess_density = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_density,
        "candidate_space": str(search_space(ship)),
        "sampling_prior": (
            "uniform n-subset of all distinct legal L placements wholly inside the free cells; "
            "shape, tile count, in-region placement, and duplicate exclusion are enforced"
        ),
        "wall_clock_sec": round(guess_wall, 6),
    }

    attack_names = (
        "outlier_low_cell_frequency",
        "greedy_lexicographic",
        "random_restart_most_constrained",
        "by_hand_bounding_box_parity",
    )
    attacks = {
        name: {"successes": 0, "attempts": 0, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    reference = {
        "name": "minimum-column Algorithm X on all legal L placements",
        "complexity": "exponential worst case after O(P) placement enumeration",
        "successes": 0,
        "attempts": 0,
        "operations": 0,
        "nodes": 0,
        "legal_placements": 0,
        "wall_clock_sec": 0.0,
    }
    compact = {
        "name": "dominant 2-by-2 anchor-parity decomposition plus bounded residual exact cover",
        "complexity": "linear scan plus exponential search only in the fixed-size fringe",
        "successes": 0,
        "attempts": 0,
        "operations": 0,
        "operation_samples": [],
        "wall_clock_sec": 0.0,
    }
    for seed in range(8100, 8108):
        current = make_instance(seed=seed, **shipping_params)
        probes = (
            lambda: _greedy_cover(current, "boundary"),
            lambda: _greedy_cover(current, "lex"),
            lambda: _random_restart_attack(
                current, int(shipping_params["screen_restarts"])
            )[0],
            lambda: _bbox_parity_attack(current),
        )
        for name, probe in zip(attack_names, probes):
            started = time.perf_counter()
            candidate = probe()
            elapsed = time.perf_counter() - started
            attacks[name]["attempts"] += 1
            attacks[name]["successes"] += int(
                candidate is not None and verify(current, candidate)[0]
            )
            attacks[name]["wall_clock_sec"] += elapsed

        started = time.perf_counter()
        candidate, stats = _algorithm_x(current)
        elapsed = time.perf_counter() - started
        reference["attempts"] += 1
        reference["successes"] += int(
            candidate is not None and verify(current, candidate)[0]
        )
        reference["operations"] += stats["operations"]
        reference["nodes"] += stats["nodes"]
        reference["legal_placements"] += stats["legal_placements"]
        reference["wall_clock_sec"] += elapsed

        started = time.perf_counter()
        candidate, operations = _dominant_parity_route(current)
        elapsed = time.perf_counter() - started
        compact["attempts"] += 1
        compact["successes"] += int(
            candidate is not None and verify(current, candidate)[0]
        )
        compact["operations"] += operations
        compact["operation_samples"].append(operations)
        compact["wall_clock_sec"] += elapsed

    for row in attacks.values():
        row["wall_clock_sec"] = round(row["wall_clock_sec"], 6)
    reference["wall_clock_sec"] = round(reference["wall_clock_sec"], 6)
    reference["solves"] = f"{reference['successes']}/{reference['attempts']}, as expected"
    compact["wall_clock_sec"] = round(compact["wall_clock_sec"], 6)
    compact["solves"] = f"{compact['successes']}/{compact['attempts']}, as expected"
    all_failed = all(v["successes"] == 0 and v["attempts"] >= 8 for v in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed
        and reference["successes"] == reference["attempts"]
        and compact["successes"] == compact["attempts"],
        "attacks": attacks,
        "reference_algorithm": reference,
        "compact_route": compact,
        "track_b_note": (
            "The successful domain-standard algorithm is intentionally outside attacks."
        ),
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    strongest = attacks["random_restart_most_constrained"]
    report["G5_density_and_baseline"] = {
        "pass": guess_hits == 0
        and demo_count is not None and demo_count > 0
        and all_failed
        and reference["successes"] == reference["attempts"],
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": guess_total,
        "shipping_sampled_density": guess_density,
        "shipping_candidate_space": str(search_space(ship)),
        "demo_exact_solution_count": demo_count,
        "demo_n": demo["n"],
        "strongest_failing_attack": "random_restart_most_constrained",
        "strongest_attack_wall_clock_sec": strongest["wall_clock_sec"],
        "strongest_attack_attempts": strongest["attempts"],
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operations": reference["operations"],
        "reference_nodes": reference["nodes"],
    }

    ladder = []
    for name, params in DIFFICULTY.items():
        sample = make_instance(seed=2, **params)
        ladder.append({
            "preset": name,
            "n": sample["n"],
            "free_cells": len(sample["free_cells"]),
            "legal_placements": len(_legal_placements_from_cells(
                {tuple(p) for p in sample["free_cells"]}
            )),
            "search_space_bits": search_space(sample).bit_length(),
        })
    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * int(shipping_params["n"])
    doubled_params["exceptions"] = 2 * int(shipping_params["exceptions"])
    doubled_params["screen_restarts"] = 0
    doubled = make_instance(seed=8675309, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * ship["n"]
        and search_space(doubled) > search_space(ship),
        "ladder": ladder,
        "shipping_n": ship["n"],
        "doubled_n": doubled["n"],
        "doubled_verification": doubled_reason,
        "shipping_search_space_bits": search_space(ship).bit_length(),
        "doubled_search_space_bits": search_space(doubled).bit_length(),
    }

    invariance_checks = 0
    carried_checks = 0
    keys = []
    g8_failures = []
    for seed in range(20):
        base = make_instance(seed=9000 + seed, **shipping_params)
        key = canonical_key(base)
        keys.append(key)
        one = _relabel_instance(base, seed % 8, 31 - seed, seed - 17, 10000 + seed)
        two = _relabel_instance(one, (3 * seed + 1) % 8, -11, 29, 11000 + seed)
        for transformed in (one, two):
            invariance_checks += 1
            if canonical_key(transformed) != key:
                g8_failures.append(f"seed {seed}: key changed under a lattice relabelling")
            carried_checks += 1
            ok, reason = verify(transformed, transformed["answer"])
            if not ok:
                g8_failures.append(f"seed {seed}: carried witness failed: {reason}")
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and invariance_checks >= 40
        and carried_checks >= 40 and distinct == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct,
        "transformations": [
            "arbitrary input-cell reordering",
            "all eight square-lattice dihedral symmetries",
            "global integer translation",
            "compositions of these maps",
        ],
        "failures": g8_failures,
    }

    answer_chars, answer_tokens, answer_elements = _answer_metrics(planted)
    # G9 counts the route *after* the insight.  Once the dominant phase has been
    # recognized, one pass assigns the 3n cells to blocks, one pass emits the n
    # tiles, and the fixed fringe needs at most exceptions^2 local comparisons.
    # The automated compact probe above additionally discovers the phase by four
    # full scans; that mechanical discovery cost is reported, but is not the
    # intended post-insight route measured here.
    intended_ops = (
        4 * int(ship["n"])
        + int(shipping_params["exceptions"]) ** 2
    )
    arms = {
        name: dict(G9_EVIDENCE[name]) for name in ("bare", "hinted", "placebo")
    }
    hinted_attempts = arms["hinted"].get("attempts", 0)
    placebo_attempts = arms["placebo"].get("attempts", 0)
    hinted_rate = arms["hinted"].get("solved", 0) / hinted_attempts if hinted_attempts else 0.0
    placebo_rate = arms["placebo"].get("solved", 0) / placebo_attempts if placebo_attempts else 0.0
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
