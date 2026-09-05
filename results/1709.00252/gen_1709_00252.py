"""Verified generators for unsigned square edge-matching puzzles.

The native problem is the feasibility version of the MILP in Section 2.1 of
Salassa et al., arXiv:1709.00252.  Instances are inverse-generated: first make
a completely matched board, then independently rotate and permute its tiles.
The verifier never consults that planted placement.
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
from collections import Counter, defaultdict


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "square tiles with four colored edges",
        "rotatable n by n edge-matching board",
    ],
    "verification_operations": [
        "permutation check",
        "quarter-turn rotation",
        "exact edge-color comparison",
        "exact gray-border comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Use gray-border types and the rarest compatible edge continuations to "
        "propagate placements before branching over the remaining tiles."
    ),
    "hardness_basis": (
        "Track A: Section 1 invokes Demaine--Demaine Theorem 3 (NP-complete "
        "unsigned unit-square edge matching on a square board with all tiles "
        "used and a growing palette); shipping uses the full 12x12 placement-"
        "and-rotation regime with 10 non-gray colors, where the measured CSP/"
        "DPLL-style attack exhausts 5,000,000 nodes on every audited seed."
    ),
    "max_answer_tokens": 138,
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

CERTIFICATE_LANGUAGE = {
    "description": (
        "A row-major list of exactly n^2 oriented-tile codes.  Code 4*t+r "
        "uses 0-indexed tile t exactly once with clockwise rotation r in "
        "{0,1,2,3}; candidates already respect each tile's gray-border type."
    ),
    "bounds": {
        "n_min": 2,
        "shipping_n": 12,
        "answer_length_at_shipping": 144,
        "tile_id_max_at_shipping": 143,
        "code_max_at_shipping": 575,
        "rotation_count": 4,
    },
}

DIFFICULTY = {
    "demo": {"n": 2, "colors": 3, "dpll_nodes": 2_000},
    "easy": {"n": 12, "colors": 10, "dpll_nodes": 5_000_000},
    "medium": {"n": 13, "colors": 10, "dpll_nodes": 5_000_000},
    "hard": {"n": 14, "colors": 11, "dpll_nodes": 5_000_000},
}

SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "A cell's feasible-domain size is governed by its gray-edge type and the "
    "frequency of its compatible color continuations."
)
PLACEBO_HINT = (
    "A proposed board is easiest to audit with careful bookkeeping of tile "
    "numbers and clockwise quarter-turn codes."
)

# Filled from the three independent harden.py runs after the module is final.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3, "errors": 0},
    "hinted": {"solved": 0, "attempts": 3, "errors": 0},
    "placebo": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted_verdict": "hardened",
}

NOTES = """\
Definition: Section 2.1, especially constraints (2)-(11), fixes one use of each
tile, one tile per cell, clockwise rotations, exact equality on adjacent colors,
and color 0 on the outer frame.  Section 2.2 gives the equivalent assignment-
conflict clique model, but this generator retains the native tiles.

Easy regimes avoided: Section 2.3 reports complete solutions through 6x6 by
both CPLEX and a max-clique heuristic, but not at 7x7 and 8x8 in the larger runs.
Section 3 identifies easy decompositions: border optimization is effectively
one-dimensional, and fixed non-adjacent tile reassignment is bipartite matching
solvable by the Hungarian algorithm.  Shipping is therefore a full 12x12
placement-and-rotation CSP, not one of those subproblems.

Certificate production: inverse generation samples the internal grid-edge colors,
writes each on both incident planted tiles, puts color 0 only on the outer frame,
then rotates and permutes all tiles.  Shipping uses iid colors; the first escalation
instead shuffles a balanced color multiset to remove frequency outliers without
lengthening the answer.  No generated instance is solved to obtain its answer.
Construction takes O(n^2) work because it retains the hidden sampled board; it is
not an algorithm for recovering a board from the shuffled instance.  The measured
recovery baseline instead exhausts 5,000,000 branches, and no polynomial recovery
method is known, so this is a Track-A claim rather than a concealed Track-B algorithm.

Attack defenses: planted and non-planted-looking edges do not exist as separate
populations--all internal edges are iid.  Input order and stored orientation are
independently randomized.  Border-type outlier ordering, rarity-greedy filling,
structure-aware random restarts, and a bounded chronological CSP/DPLL search are
measured on eight shipping seeds.  The Track-A distribution claim rests on that
measured panel as well as the paper's problem-class result; worst-case
NP-completeness alone would not establish average hardness for this generator.
"""


def _rotate(sides: list[int] | tuple[int, int, int, int], k: int) -> list[int]:
    """Rotate [top,right,bottom,left] clockwise by k quarter-turns."""
    k %= 4
    a = list(sides)
    if k == 0:
        return a
    return a[-k:] + a[:-k]


def _outward_sides(n: int, pos: int) -> frozenset[int]:
    r, c = divmod(pos, n)
    out = set()
    if r == 0:
        out.add(0)
    if c == n - 1:
        out.add(1)
    if r == n - 1:
        out.add(2)
    if c == 0:
        out.add(3)
    return frozenset(out)


def _zero_sides(sides: list[int]) -> frozenset[int]:
    return frozenset(i for i, value in enumerate(sides) if value == 0)


def _valid_rotations_for_position(sides: list[int], outward: frozenset[int]) -> list[int]:
    return [k for k in range(4) if _zero_sides(_rotate(sides, k)) == outward]


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a satisfiable native edge-matching instance."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    colors = params.get("colors", max(3, round(0.8 * n)))
    if isinstance(colors, bool) or not isinstance(colors, int) or colors < 2:
        raise ValueError("colors must be an integer at least 2")
    dpll_nodes = params.get("dpll_nodes", 100_000)
    if not isinstance(dpll_nodes, int) or isinstance(dpll_nodes, bool) or dpll_nodes < 1:
        raise ValueError("dpll_nodes must be a positive integer")
    balanced = params.get("balanced", False)
    if not isinstance(balanced, bool):
        raise ValueError("balanced must be a boolean")

    rng = random.Random(seed)
    if balanced:
        edge_colors = [1 + (i % colors) for i in range(2 * n * (n - 1))]
        rng.shuffle(edge_colors)
        cursor = 0
        horizontal = []
        for _ in range(n - 1):
            horizontal.append(edge_colors[cursor:cursor + n])
            cursor += n
        vertical = []
        for _ in range(n):
            vertical.append(edge_colors[cursor:cursor + n - 1])
            cursor += n - 1
    else:
        horizontal = [
            [rng.randint(1, colors) for _ in range(n)] for _ in range(n - 1)
        ]
        vertical = [
            [rng.randint(1, colors) for _ in range(n - 1)] for _ in range(n)
        ]

    planted_tiles: list[list[int]] = []
    for r in range(n):
        for c in range(n):
            planted_tiles.append([
                0 if r == 0 else horizontal[r - 1][c],
                0 if c == n - 1 else vertical[r][c],
                0 if r == n - 1 else horizontal[r][c],
                0 if c == 0 else vertical[r][c - 1],
            ])

    stored: list[list[int]] = []
    unscramble: list[int] = []
    for tile in planted_tiles:
        turn = rng.randrange(4)
        stored.append(_rotate(tile, turn))
        unscramble.append((-turn) % 4)

    old_ids = list(range(n * n))
    rng.shuffle(old_ids)
    tiles = [stored[old] for old in old_ids]
    new_id = {old: new for new, old in enumerate(old_ids)}
    answer = [4 * new_id[old] + unscramble[old] for old in range(n * n)]

    return {
        "n": n,
        "colors": colors,
        "balanced": balanced,
        "tiles": tiles,
        "dpll_nodes": dpll_nodes,
        "answer": answer,
    }


def render(inst: dict) -> str:
    n = inst["n"]
    lines = [
        "EDGE-MATCHING PUZZLE",
        "",
        f"Arrange the {n*n} listed square tiles on a {n} by {n} board.",
        "Each tile must be used exactly once and may be rotated, but not flipped.",
        "A tile is listed as [top,right,bottom,left] in its stored orientation.",
        "Rotation r=0,1,2,3 means r clockwise quarter-turns from that orientation.",
        "Every pair of touching edges must have exactly the same integer color.",
        "Color 0 is gray. An edge is 0 if and only if it faces outside the board:",
        "all outer edges are 0 and no internal touching edge is 0.",
        "Rows, columns, and tile IDs are 0-indexed.",
        "",
        "Tiles:",
    ]
    lines.extend(f"{i}: {json.dumps(tile, separators=(',', ':'))}"
                 for i, tile in enumerate(inst["tiles"]))
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    lines.extend([
        "",
        f"Return one JSON list of exactly {n*n} integers in row-major cell order.",
        "At each cell, integer code 4*t+r means tile ID t with rotation r.",
        "Thus the first code is row 0, column 0; order matters and repeats are forbidden.",
        "Give your final answer inside <answer></answer> tags, as that JSON list.",
        "Format-only example: <answer>[13, 6, 8, 3]</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text) -> object | None:
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\b[^>]*>(.*?)</answer>", text,
                      flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    body = match.group(1).strip()
    body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    if any(isinstance(x, bool) or not isinstance(x, int) for x in value):
        return None
    return value


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Check a witness directly; deliberately never reads inst['answer']."""
    n = inst["n"]
    count = n * n
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer list is empty"
    if len(answer) != count:
        return False, f"expected {count} oriented-tile codes, got {len(answer)}"
    board: list[list[int]] = []
    used: set[int] = set()
    for pos, code in enumerate(answer):
        if isinstance(code, bool) or not isinstance(code, int):
            return False, "every oriented-tile code must be an integer"
        if code < 0 or code >= 4 * count:
            return False, f"oriented-tile code outside inclusive range 0..{4*count-1}"
        tile_id, turn = divmod(code, 4)
        if tile_id in used:
            return False, "a tile ID is duplicated and another tile is missing"
        used.add(tile_id)
        sides = _rotate(inst["tiles"][tile_id], turn)
        outward = _outward_sides(n, pos)
        if _zero_sides(sides) != outward:
            r, c = divmod(pos, n)
            return False, f"gray-border rule fails at row {r}, column {c}"
        r, c = divmod(pos, n)
        if c and board[pos - 1][1] != sides[3]:
            return False, f"horizontal edge mismatch after row {r}, column {c-1}"
        if r and board[pos - n][2] != sides[0]:
            return False, f"vertical edge mismatch after row {r-1}, column {c}"
        board.append(sides)
    return True, "ok"


def _category_positions(n: int) -> dict[int, list[int]]:
    groups = {0: [], 1: [], 2: []}
    for pos in range(n * n):
        groups[len(_outward_sides(n, pos))].append(pos)
    return groups


def _category_tiles(inst: dict) -> dict[int, list[int]]:
    groups = {0: [], 1: [], 2: []}
    for tile_id, tile in enumerate(inst["tiles"]):
        groups[len(_zero_sides(tile))].append(tile_id)
    return groups


def _candidate_data(inst: dict):
    cached = inst.get("_candidate_data")
    if cached is not None:
        return cached
    n = inst["n"]
    pos_groups = _category_positions(n)
    tile_groups = _category_tiles(inst)
    outward_by_pos = [_outward_sides(n, pos) for pos in range(n * n)]
    turns = [[None] * (n * n) for _ in inst["tiles"]]
    for tile_id, tile in enumerate(inst["tiles"]):
        zero_count = len(_zero_sides(tile))
        for pos, outward in enumerate(outward_by_pos):
            if len(outward) == zero_count:
                turns[tile_id][pos] = _valid_rotations_for_position(tile, outward)
    cached = (pos_groups, tile_groups, turns)
    inst["_candidate_data"] = cached
    return cached


def random_candidate(inst: dict, rng) -> object:
    """Uniformly sample the statement-visible border-respecting language."""
    n = inst["n"]
    pos_groups, tile_groups, turns = _candidate_data(inst)
    answer = [0] * (n * n)
    for zeros in (0, 1, 2):
        positions = pos_groups[zeros]
        ids = list(tile_groups[zeros])
        rng.shuffle(ids)
        for pos, tile_id in zip(positions, ids):
            rotations = turns[tile_id][pos]
            # Border types have a forced turn.  Inner tiles have no gray edge,
            # so all four codes are legal and two random bits are exactly uniform.
            turn = rng.getrandbits(2) if zeros == 0 else rotations[0]
            answer[pos] = 4 * tile_id + turn
    return answer


def _lazy_random_candidate_hit(inst: dict, rng) -> bool:
    """Test the same uniform prior without drawing an irrelevant failed suffix.

    Sequential removal from each category pool is exactly a uniform random
    permutation.  Once a sampled prefix has a mismatched edge, every completion
    is invalid, so materializing its remaining independent choices cannot alter
    the hit count.  A rare complete candidate is passed through public verify().
    """
    n = inst["n"]
    _, tile_groups, turns = _candidate_data(inst)
    pools = {zeros: list(ids) for zeros, ids in tile_groups.items()}
    board: list[list[int]] = []
    answer: list[int] = []
    for pos in range(n * n):
        outward = _outward_sides(n, pos)
        zeros = len(outward)
        pool = pools[zeros]
        pick = rng.randrange(len(pool))
        tile_id = pool[pick]
        pool[pick] = pool[-1]
        pool.pop()
        turn = rng.getrandbits(2) if zeros == 0 else turns[tile_id][pos][0]
        sides = _rotate(inst["tiles"][tile_id], turn)
        r, c = divmod(pos, n)
        if c and board[pos - 1][1] != sides[3]:
            return False
        if r and board[pos - n][2] != sides[0]:
            return False
        board.append(sides)
        answer.append(4 * tile_id + turn)
    return verify(inst, answer)[0]


def search_space(inst: dict) -> int:
    n = inst["n"]
    inner = (n - 2) ** 2
    edge = 4 * (n - 2)
    # Corner and non-corner border permutations have forced orientations;
    # each inner tile has four stored-orientation codes.
    return math.factorial(4) * math.factorial(edge) * math.factorial(inner) * 4 ** inner


def enumerate_all(inst: dict) -> int | None:
    if search_space(inst) > 100_000:
        return None
    n = inst["n"]
    pos_groups = _category_positions(n)
    tile_groups = _category_tiles(inst)
    answer = [0] * (n * n)
    valid = 0

    def fill_group(group_index: int) -> None:
        nonlocal valid
        if group_index == 3:
            valid += int(verify(inst, answer)[0])
            return
        zeros = (2, 1, 0)[group_index]
        positions = pos_groups[zeros]
        for ids in itertools.permutations(tile_groups[zeros]):
            rotation_lists = [
                _valid_rotations_for_position(inst["tiles"][tile_id],
                                              _outward_sides(n, pos))
                for pos, tile_id in zip(positions, ids)
            ]
            for turns in itertools.product(*rotation_lists):
                for pos, tile_id, turn in zip(positions, ids, turns):
                    answer[pos] = 4 * tile_id + turn
                fill_group(group_index + 1)

    fill_group(0)
    return valid


def _color_partition(tiles: list[list[int]], rounds: int = 12) -> dict[int, int]:
    """Relabel colors by a rotation-aware refinement invariant."""
    colors = sorted({x for tile in tiles for x in tile})
    counts = Counter(x for tile in tiles for x in tile)
    labels = {c: (0 if c == 0 else counts[c]) for c in colors}
    # Compress the initial values canonically while keeping gray distinguished.
    vals = sorted(set(labels[c] for c in colors if c != 0))
    value_class = {v: i + 1 for i, v in enumerate(vals)}
    labels = {c: (0 if c == 0 else value_class[labels[c]]) for c in colors}
    for _ in range(rounds):
        signatures = {}
        for color in colors:
            if color == 0:
                signatures[color] = ("gray",)
                continue
            contexts = []
            for tile in tiles:
                for i, x in enumerate(tile):
                    if x == color:
                        contexts.append(tuple(labels[tile[(i + d) % 4]]
                                              for d in (1, 2, 3)))
            signatures[color] = (labels[color], tuple(sorted(contexts)))
        nonzero_sigs = sorted({signatures[c] for c in colors if c != 0})
        sig_class = {sig: i + 1 for i, sig in enumerate(nonzero_sigs)}
        new_labels = {
            c: (0 if c == 0 else sig_class[signatures[c]]) for c in colors
        }
        if new_labels == labels:
            break
        labels = new_labels
    return labels


def _reflected_sides(sides: list[int] | tuple[int, ...]) -> list[int]:
    """Reflect [top,right,bottom,left] across the board's vertical axis."""
    return [sides[0], sides[3], sides[2], sides[1]]


def _canonical_wire(n: int, tiles: list[list[int]]) -> str:
    labels = _color_partition(tiles)
    normalized = []
    for tile in tiles:
        relabeled = [labels[x] for x in tile]
        rotations = [tuple(_rotate(relabeled, k)) for k in range(4)]
        normalized.append(min(rotations))
    payload = [n, sorted(normalized)]
    return json.dumps(payload, separators=(",", ":"), sort_keys=False)


def canonical_key(inst: dict) -> str:
    """Invariant under representation changes and square-board reflections."""
    direct = _canonical_wire(inst["n"], inst["tiles"])
    reflected = _canonical_wire(
        inst["n"], [_reflected_sides(tile) for tile in inst["tiles"]]
    )
    wire = min(direct, reflected)
    return hashlib.sha256(wire.encode("ascii")).hexdigest()


def escalate(params) -> dict | str | None:
    p = dict(params)
    n = int(p["n"])
    # First remove the per-color frequency signal while keeping the 196-code
    # answer fixed.  Only then grow the board toward the 256-atom cap.
    if not p.get("balanced", False):
        p["balanced"] = True
        return p
    if n < 16:
        p["n"] = n + 1
        p["colors"] = max(3, round(0.8 * (n + 1)))
        return p
    return "cap_bound"


def _rarity_answer(inst: dict) -> list[int]:
    """Outlier probe: align border types and rank tiles by rare colors."""
    n = inst["n"]
    freq = Counter(x for tile in inst["tiles"] for x in tile if x)
    positions = _category_positions(n)
    tiles = _category_tiles(inst)
    answer = [0] * (n * n)
    for zeros in (2, 1, 0):
        ranked_tiles = sorted(
            tiles[zeros],
            key=lambda t: (sum(freq[x] for x in inst["tiles"][t] if x), t),
        )
        for pos, tile_id in zip(positions[zeros], ranked_tiles):
            rotations = _valid_rotations_for_position(
                inst["tiles"][tile_id], _outward_sides(n, pos)
            )
            turn = min(rotations, key=lambda k: tuple(_rotate(inst["tiles"][tile_id], k)))
            answer[pos] = 4 * tile_id + turn
    return answer


def _oriented_options(inst: dict) -> dict[tuple[int, int], list[tuple[int, int, tuple[int, ...]]]]:
    by_top_left: dict[tuple[int, int], list[tuple[int, int, tuple[int, ...]]]] = defaultdict(list)
    for tile_id, tile in enumerate(inst["tiles"]):
        seen = set()
        for turn in range(4):
            sides = tuple(_rotate(tile, turn))
            if sides in seen:
                continue
            seen.add(sides)
            by_top_left[(sides[0], sides[3])].append((tile_id, turn, sides))
    return by_top_left


def _greedy_answer(inst: dict) -> list[int] | None:
    """One-pass rarity greedy with no backtracking."""
    n = inst["n"]
    by_tl = _oriented_options(inst)
    used = set()
    board: list[tuple[int, ...]] = []
    answer = []
    freq = Counter(x for tile in inst["tiles"] for x in tile if x)
    for pos in range(n * n):
        r, c = divmod(pos, n)
        top = 0 if r == 0 else board[pos - n][2]
        left = 0 if c == 0 else board[pos - 1][1]
        candidates = []
        for tile_id, turn, sides in by_tl.get((top, left), []):
            if tile_id in used:
                continue
            if (sides[1] == 0) != (c == n - 1):
                continue
            if (sides[2] == 0) != (r == n - 1):
                continue
            score = freq.get(sides[1], 0) + freq.get(sides[2], 0)
            candidates.append((score, tile_id, turn, sides))
        if not candidates:
            return None
        _, tile_id, turn, sides = min(candidates)
        used.add(tile_id)
        board.append(sides)
        answer.append(4 * tile_id + turn)
    return answer


def _random_greedy_answer(inst: dict, rng: random.Random) -> list[int] | None:
    """Randomized restart that enforces every edge exposed so far."""
    n = inst["n"]
    by_tl = _oriented_options(inst)
    used = set()
    board: list[tuple[int, ...]] = []
    answer = []
    for pos in range(n * n):
        r, c = divmod(pos, n)
        top = 0 if r == 0 else board[pos - n][2]
        left = 0 if c == 0 else board[pos - 1][1]
        candidates = []
        for tile_id, turn, sides in by_tl.get((top, left), []):
            if tile_id in used:
                continue
            if (sides[1] == 0) != (c == n - 1):
                continue
            if (sides[2] == 0) != (r == n - 1):
                continue
            candidates.append((tile_id, turn, sides))
        if not candidates:
            return None
        tile_id, turn, sides = rng.choice(candidates)
        used.add(tile_id)
        board.append(sides)
        answer.append(4 * tile_id + turn)
    return answer


def _dpll_attack(inst: dict, node_budget: int | None = None) -> dict:
    """Chronological exact CSP search with unit domains and forward checking."""
    n = inst["n"]
    total = n * n
    budget = int(node_budget if node_budget is not None else inst["dpll_nodes"])
    by_tl = _oriented_options(inst)
    freq = Counter(x for tile in inst["tiles"] for x in tile if x)
    for options in by_tl.values():
        options.sort(key=lambda x: (freq.get(x[2][1], 0) + freq.get(x[2][2], 0),
                                    x[0], x[1]))
    board: list[tuple[int, ...] | None] = [None] * total
    answer = [0] * total
    used = [False] * total
    nodes = 0
    backtracks = 0
    exhausted = False
    t0 = time.perf_counter()

    def compatible_options(pos: int):
        r, c = divmod(pos, n)
        top = 0 if r == 0 else board[pos - n][2]  # type: ignore[index]
        left = 0 if c == 0 else board[pos - 1][1]  # type: ignore[index]
        for tile_id, turn, sides in by_tl.get((top, left), []):
            if used[tile_id]:
                continue
            if (sides[1] == 0) != (c == n - 1):
                continue
            if (sides[2] == 0) != (r == n - 1):
                continue
            yield tile_id, turn, sides

    def dfs(pos: int) -> bool:
        nonlocal nodes, backtracks, exhausted
        if pos == total:
            return True
        for tile_id, turn, sides in compatible_options(pos):
            if nodes >= budget:
                exhausted = True
                return False
            nodes += 1
            used[tile_id] = True
            board[pos] = sides
            answer[pos] = 4 * tile_id + turn
            # Forward-check the next chronological domain.  A singleton is
            # naturally unit-propagated by the next recursive call.
            viable = pos + 1 == total or any(compatible_options(pos + 1))
            if viable and dfs(pos + 1):
                return True
            used[tile_id] = False
            board[pos] = None
            backtracks += 1
            if exhausted:
                return False
        return False

    solved = dfs(0)
    elapsed = time.perf_counter() - t0
    candidate = list(answer) if solved else None
    verified = bool(candidate is not None and verify(inst, candidate)[0])
    return {
        "success": verified,
        "answer": candidate if verified else None,
        "nodes": nodes,
        "backtracks": backtracks,
        "budget": budget,
        "budget_exhausted": exhausted,
        "wall_clock_sec": elapsed,
    }


def _transformed_instance(inst: dict, seed: int) -> tuple[dict, list[int]]:
    """Compose tile reordering, representation rotation, and color relabeling."""
    rng = random.Random(seed)
    count = inst["n"] ** 2
    old_order = list(range(count))
    rng.shuffle(old_order)
    old_to_new = {old: new for new, old in enumerate(old_order)}
    turns = [rng.randrange(4) for _ in range(count)]
    color_order = list(range(1, inst["colors"] + 1))
    rng.shuffle(color_order)
    color_map = {0: 0, **{old: color_order[old - 1]
                          for old in range(1, inst["colors"] + 1)}}
    new_tiles = []
    for new, old in enumerate(old_order):
        rotated = _rotate(inst["tiles"][old], turns[new])
        new_tiles.append([color_map[x] for x in rotated])
    carried = []
    for code in inst["answer"]:
        old, rotation = divmod(code, 4)
        new = old_to_new[old]
        carried.append(4 * new + ((rotation - turns[new]) % 4))
    changed = {k: v for k, v in inst.items()
               if k not in ("tiles", "answer") and not k.startswith("_")}
    changed["tiles"] = new_tiles
    changed["answer"] = carried
    return changed, carried


def _reflected_instance(inst: dict) -> tuple[dict, list[int]]:
    """Reflect the board coordinate system and carry a witness through it."""
    n = inst["n"]
    changed = {k: v for k, v in inst.items()
               if k not in ("tiles", "answer") and not k.startswith("_")}
    changed["tiles"] = [_reflected_sides(tile) for tile in inst["tiles"]]
    carried = [0] * (n * n)
    for pos, code in enumerate(inst["answer"]):
        r, c = divmod(pos, n)
        tile_id, rotation = divmod(code, 4)
        destination = r * n + (n - 1 - c)
        carried[destination] = 4 * tile_id + ((-rotation) % 4)
    changed["answer"] = carried
    return changed, carried


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    wire = json.dumps(answer, separators=(",", ":"))
    return len(wire), math.ceil(len(wire) / 4), len(answer)  # one code per cell


def selftest() -> dict:
    report: dict = {}

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **ship_params)
    original = list(inst["answer"])
    swapped = list(original)
    swapped[0], swapped[-1] = swapped[-1], swapped[0]
    duplicated = list(original)
    duplicated[1] = duplicated[0]
    corruptions = {
        "drop_one": verify(inst, original[:-1]),
        "swap_two": verify(inst, swapped),
        "duplicate_one": verify(inst, duplicated),
        "empty": verify(inst, []),
        "out_of_range": verify(inst, original[:-1] + [4 * inst["n"] ** 2]),
    }
    reasons = [reason for ok, reason in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not ok for ok, _ in corruptions.values())
                and len(set(reasons)) == len(reasons),
        "cases": {name: {"rejected": not result[0], "reason": result[1]}
                  for name, result in corruptions.items()},
        "distinct_reasons": len(set(reasons)),
    }

    wire = json.dumps(original, separators=(",", ":"))
    parsed = parse_answer(
        "I propagated the constrained boundary first.\n```json\n"
        f"<answer>{wire}</answer>\n```\nThe edge checks are exact."
    )
    report["G3_round_trip"] = {
        "pass": parsed == original,
        "surrounding_prose_and_markdown_fence": True,
        "json_round_trip": parsed == original,
    }

    guess_rng = random.Random(0x170900252)
    guess_total = 200_000
    hits = 0
    t0 = time.perf_counter()
    for _ in range(guess_total):
        hits += int(_lazy_random_candidate_hit(inst, guess_rng))
    guess_seconds = time.perf_counter() - t0
    space = search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": hits / guess_total < 1e-6,
        "hits": hits,
        "total": guess_total,
        "empirical_probability": hits / guess_total,
        "candidate_space": space,
        "candidate_space_log10": math.log10(space),
        "prior": (
            "uniform over permutations within corner, non-corner border, and "
            "interior tile classes, with every border-gray orientation forced "
            "and every inner rotation uniform"
        ),
        "sampling_method": (
            "exact lazy form of random_candidate: category permutations are "
            "drawn uniformly without replacement, but a suffix is not "
            "materialized after its prefix already proves the board invalid"
        ),
        "sampling_wall_seconds": guess_seconds,
    }

    baseline = _dpll_attack(inst)
    demo_inst = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    report["G5_density_and_baseline"] = {
        "pass": hits / guess_total < 1e-6 and demo_count is not None
                and not baseline["success"] and baseline["budget_exhausted"],
        "shipping_observed_valid_fraction": hits / guess_total,
        "shipping_density_sample_count": guess_total,
        "shipping_valid_hits": hits,
        "shipping_candidate_space": space,
        "enumerate_all_shipping": None,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo_inst),
        "strongest_attack": "chronological CSP/DPLL with forward checking",
        "strongest_attack_wall_seconds": baseline["wall_clock_sec"],
        "strongest_attack_nodes": baseline["nodes"],
        "strongest_attack_backtracks": baseline["backtracks"],
        "strongest_attack_budget": baseline["budget"],
        "strongest_attack_budget_exhausted": baseline["budget_exhausted"],
        "strongest_attack_success": baseline["success"],
    }

    successes = {
        "outlier_border_type_and_color_rarity": 0,
        "greedy_rarest_continuation_no_backtracking": 0,
        "random_greedy_restart_256": 0,
        "csp_dpll_forward_checking": 0,
    }
    dpll_runs = []
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **ship_params)
        successes["outlier_border_type_and_color_rarity"] += int(
            verify(trial, _rarity_answer(trial))[0]
        )
        greedy = _greedy_answer(trial)
        successes["greedy_rarest_continuation_no_backtracking"] += int(
            greedy is not None and verify(trial, greedy)[0]
        )
        rng = random.Random(seed ^ 0xA11CE)
        restart_hit = False
        for _ in range(256):
            restarted = _random_greedy_answer(trial, rng)
            if restarted is not None and verify(trial, restarted)[0]:
                restart_hit = True
                break
        successes["random_greedy_restart_256"] += int(restart_hit)
        run = _dpll_attack(trial)
        dpll_runs.append(run)
        successes["csp_dpll_forward_checking"] += int(run["success"])
    all_failed = (all(value == 0 for value in successes.values())
                  and sum(int(x["budget_exhausted"]) for x in dpll_runs) == 8)
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": {
            name: {"successes": count, "attempts": 8}
            for name, count in successes.items()
        },
        "standard_algorithm": {
            "name": "chronological CSP/DPLL with unit domains and forward checking",
            "complexity": "exponential worst case; O(n^2) storage",
            "total_wall_clock_sec": sum(x["wall_clock_sec"] for x in dpll_runs),
            "total_nodes": sum(x["nodes"] for x in dpll_runs),
            "total_backtracks": sum(x["backtracks"] for x in dpll_runs),
            "per_seed_node_budget": ship_params["dpll_nodes"],
            "budget_exhaustions": sum(int(x["budget_exhausted"]) for x in dpll_runs),
        },
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled_params["colors"] *= 2
    doubled = make_instance(seed=77, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    fixed_escalation = escalate(ship_params)
    fixed_length_ok = (
        isinstance(fixed_escalation, dict)
        and fixed_escalation.get("n") == ship_params["n"]
        and fixed_escalation.get("balanced") is True
        and len(make_instance(seed=77, **fixed_escalation)["answer"])
        == len(inst["answer"])
    )
    report["G7_scales"] = {
        "pass": (doubled_ok and doubled_params["n"] == 2 * ship_params["n"]
                 and fixed_length_ok),
        "base_n": ship_params["n"],
        "doubled_n": doubled_params["n"],
        "base_candidate_log10": math.log10(space),
        "doubled_candidate_log10": math.log10(search_space(doubled)),
        "doubled_verify": doubled_reason,
        "first_escalation_fixed_answer_length": fixed_length_ok,
        "first_escalation": fixed_escalation,
    }

    invariance_checks = 0
    witness_checks = 0
    for seed in range(20):
        base = make_instance(n=7, colors=7, dpll_nodes=100, seed=seed)
        mirrored, mirrored_answer = _reflected_instance(base)
        invariance_checks += int(canonical_key(base) == canonical_key(mirrored))
        witness_checks += int(verify(mirrored, mirrored_answer)[0])
        changed, carried = _transformed_instance(base, seed ^ 0xC0110)
        invariance_checks += int(canonical_key(base) == canonical_key(changed))
        witness_checks += int(verify(changed, carried)[0])
        changed2, carried2 = _transformed_instance(mirrored, seed ^ 0xB04AD)
        invariance_checks += int(canonical_key(base) == canonical_key(changed2))
        witness_checks += int(verify(changed2, carried2)[0])
    keys = {
        canonical_key(make_instance(n=7, colors=7, dpll_nodes=100, seed=seed))
        for seed in range(1000, 1020)
    }
    report["G8_canonical_key"] = {
        "pass": invariance_checks == 60 and witness_checks == 60 and len(keys) == 20,
        "invariance_checks": invariance_checks,
        "invariance_attempts": 60,
        "transformed_witness_checks": witness_checks,
        "transformed_witness_attempts": 60,
        "unrelated_distinct": len(keys),
        "unrelated_attempts": 20,
        "transformations": (
            "square-board reflection, input-tile permutation, independent "
            "stored-orientation rotation, global nonzero-color relabeling, "
            "and their composition"
        ),
        "method": (
            "rotation-aware color refinement plus the lexicographically lesser "
            "of the two global chiral normal forms"
        ),
    }

    metrics = [_answer_metrics(make_instance(seed=1000 + seed, **ship_params)["answer"])
               for seed in range(256)]
    chars = max(x[0] for x in metrics)
    tokens = max(x[1] for x in metrics)
    elements = max(x[2] for x in metrics)
    intended_ops = ship_params["n"] ** 2
    ev = G9_EVIDENCE
    hinted_attempts = ev["hinted"]["attempts"]
    placebo_attempts = ev["placebo"]["attempts"]
    hinted_rate = ev["hinted"]["solved"] / hinted_attempts if hinted_attempts else None
    placebo_rate = ev["placebo"]["solved"] / placebo_attempts if placebo_attempts else None
    within_caps = chars <= 2000 and elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {
            "bare": dict(ev["bare"]),
            "hinted": dict(ev["hinted"]),
            "placebo": dict(ev["placebo"]),
        },
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None
        ),
        "hinted_verdict": ev["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "answer_size_sample_count": len(metrics),
        "intended_route_operations": intended_ops,
        "intended_route_operation_definition": (
            "one oriented-tile placement per board cell after the combinatorial "
            "search has identified a complete compatible continuation; this is "
            "the certificate-assembly work left after the searched-for insight"
        ),
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship_params)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
