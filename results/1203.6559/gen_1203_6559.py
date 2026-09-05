"""Verified problem generator for arXiv:1203.6559.

The generated problem is the group-pairing formulation of Mahjong Solitaire with
peeking from Section 3 of Michiel de Bondt's paper.  Every board consists only of
isolated vertical stacks, so a tile is playable exactly when it is currently on
top of its stack.
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
from collections import deque


TRACK: str = "A"
SHIPPING_DIFFICULTY: str = "easy"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "isolated stacks of Mahjong tiles",
        "three-way pairings of four-copy tile groups",
    ],
    "verification_operations": [
        "pair contraction",
        "directed stack-precedence construction",
        "topological acyclicity check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Reject a partial choice when contracting its proposed matches closes a "
        "directed precedence cycle; without that invariant the ternary pairing "
        "tree must be searched mechanically."
    ),
    "hardness_basis": (
        "Theorem 3 proves NP-completeness already for isolated height-three "
        "stacks; the shipping distribution uses 192 four-copy groups in "
        "isolated height-eight stacks, outside the height-at-most-two easy "
        "regime of Theorems 5 and 7, and its measured Section-3-style pairing "
        "search cost is reported at G5."
    ),
    "max_answer_tokens": 97,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 6, "height": 4},
    "easy": {"n": 192, "height": 8},
    "medium": {"n": 216, "height": 8},
    "hard": {"n": 240, "height": 8},
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A length-n JSON vector over {0,1,2}; entry g selects one of the three "
        "perfect pairings of the four tiles in group g, ordered by tile ID."
    ),
    "bounds": {"length": "n", "alphabet_size": 3},
}

STRUCTURAL_HINT: str = (
    "A partial pairing is impossible as soon as its contracted stack-precedence "
    "edges contain a directed cycle."
)
PLACEBO_HINT: str = (
    "A careful solution should keep the tile identifiers and group indices "
    "consistently distinguished."
)

NOTES: str = """
Section 2 fixes the native rules and Theorem 3 fixes the hard regime: Mahjong
Solitaire with peeking remains NP-complete even for isolated stacks of the forms
aab and abb.  Theorems 5 and 7 identify the fatal easy case: initial boards made
only of isolated stacks of heights one and two are always solvable, with blocked
cycles giving the residual characterization.  This generator therefore uses
height 4 only for the hand-scale demo and height 8 for evaluated presets.

Section 3 observes that four copies of a group have three possible pairings and
searches those pairings recursively.  The certificate here is exactly that
paper-native object.  Contracting the two tiles of each proposed match turns the
top-to-bottom order of every isolated stack into directed precedence edges.  The
pairing is playable iff this finite directed graph is acyclic, so verification is
an executable exact check rather than an appeal to the NP-completeness theorem.

Generation is inverse: sample two removal events per group, place the two tiles
of each event at the same hidden time in distinct stacks, then erase the times,
rename everything, and retain only the board and pairing certificate.  The
per-group support distribution is identical for planted and alternative pairs.
The depth outlier attack, a repair hill-climber seeded by that leaky statistic,
exposed-pair greedy play, random restarts, and a capped version of the paper's
group-pairing recursion are all rerun by selftest().  The depth statistic predicts
individual planted entries substantially better than chance, so it is reported
even though it does not by itself furnish a valid witness; n=144 was rejected
because the repair attack converted the leak into valid witnesses on 3/8 seeds.
""".strip()


_PAIRINGS = (
    ((0, 1), (2, 3)),
    ((0, 2), (1, 3)),
    ((0, 3), (1, 2)),
)


def _validate_parameters(n: int, height: int) -> tuple[int, int]:
    if isinstance(n, bool) or not isinstance(n, int) or n < 4:
        raise ValueError("n must be an integer at least 4")
    if isinstance(height, bool) or not isinstance(height, int):
        raise ValueError("height must be an integer")
    if height < 4 or height % 4:
        raise ValueError("height must be a positive multiple of 4, at least 4")
    if (4 * n) % height:
        raise ValueError("height must divide 4*n")
    n_stacks = (4 * n) // height
    if n_stacks < 4:
        raise ValueError("at least four stacks are required")
    if n % n_stacks:
        raise ValueError("this balanced construction requires n divisible by 4*n/height")
    return n_stacks, height // 4


def make_instance(n: int, seed: int = 0, height: int = 8, **params) -> dict:
    """Inverse-generate a board and a known legal group pairing.

    Hidden pair events are sampled before the board.  Sorting every stack by the
    event times makes the sampled pairs a legal removal schedule by construction;
    no solver is called.
    """
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    n_stacks, block_size = _validate_parameters(n, height)
    rng = random.Random(seed)

    # Groups in one block have the same four supporting stacks.  Stack names,
    # group names, the planted matching, event order, and tile IDs are all
    # independently randomized.  This balanced incidence guarantees that each
    # stack has exactly `height` tiles and each group visits four distinct stacks.
    group_order = list(range(n))
    stack_order = list(range(n_stacks))
    rng.shuffle(group_order)
    rng.shuffle(stack_order)
    support = [[0] * 4 for _ in range(n)]
    for position, group in enumerate(group_order):
        base = position // block_size
        for occurrence in range(4):
            support[group][occurrence] = stack_order[(base + occurrence) % n_stacks]

    planted_code = [rng.randrange(3) for _ in range(n)]
    events = [(group, event) for group in range(n) for event in range(2)]
    rng.shuffle(events)
    event_time = {event: i for i, event in enumerate(events)}

    records: list[list[tuple[int, int, int]]] = [[] for _ in range(n_stacks)]
    planted_old_pairs: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    old_group: list[int] = []
    for group in range(n):
        code = planted_code[group]
        for event, (left, right) in enumerate(_PAIRINGS[code]):
            left_id = len(old_group)
            old_group.append(group)
            right_id = len(old_group)
            old_group.append(group)
            when = event_time[group, event]
            records[support[group][left]].append((when, left_id, group))
            records[support[group][right]].append((when, right_id, group))
            planted_old_pairs[group].append((left_id, right_id))

    for stack in records:
        stack.sort(key=lambda item: item[0])
        if len(stack) != height:
            raise AssertionError("internal balancing error")

    # Tile identifiers carry no time information.
    new_id_of = list(range(4 * n))
    rng.shuffle(new_id_of)
    stacks = [
        [new_id_of[old_id] for _when, old_id, _group in stack]
        for stack in records
    ]
    rng.shuffle(stacks)
    tile_groups = [0] * (4 * n)
    for old_id, group in enumerate(old_group):
        tile_groups[new_id_of[old_id]] = group

    answer: list[int] = []
    for group in range(n):
        tiles = sorted(i for i, value in enumerate(tile_groups) if value == group)
        target = {
            frozenset((new_id_of[a], new_id_of[b]))
            for a, b in planted_old_pairs[group]
        }
        code = next(
            code
            for code, pairing in enumerate(_PAIRINGS)
            if {frozenset((tiles[a], tiles[b])) for a, b in pairing} == target
        )
        answer.append(code)

    return {
        "n": n,
        "height": height,
        "stacks": stacks,
        "tile_groups": tile_groups,
        "answer": answer,
    }


def _group_tiles(inst: dict) -> list[list[int]]:
    n = inst.get("n")
    groups = [[] for _ in range(n)]
    for tile, group in enumerate(inst.get("tile_groups", [])):
        if isinstance(group, bool) or not isinstance(group, int) or not 0 <= group < n:
            raise ValueError("invalid tile group")
        groups[group].append(tile)
    if any(len(group) != 4 for group in groups):
        raise ValueError("every group must contain exactly four tiles")
    for group in groups:
        group.sort()
    return groups


def _pair_sets_for_code(tiles: list[int], code: int) -> set[frozenset[int]]:
    return {frozenset((tiles[a], tiles[b])) for a, b in _PAIRINGS[code]}


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Accept every pairing whose exact precedence graph is acyclic."""
    n = inst.get("n")
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) < n:
        return False, f"too few entries: expected {n}, got {len(answer)}"
    if len(answer) > n:
        return False, f"too many entries: expected {n}, got {len(answer)}"
    for group, code in enumerate(answer):
        if isinstance(code, bool) or not isinstance(code, int):
            return False, f"entry {group} is not an integer"
        if not 0 <= code <= 2:
            return False, f"entry {group} is outside 0..2"

    try:
        groups = _group_tiles(inst)
    except (TypeError, ValueError) as exc:
        return False, f"invalid instance: {exc}"

    tile_count = 4 * n
    tile_stack = [-1] * tile_count
    seen_tiles: set[int] = set()
    for stack_index, stack in enumerate(inst.get("stacks", [])):
        for tile in stack:
            if (
                isinstance(tile, bool)
                or not isinstance(tile, int)
                or not 0 <= tile < tile_count
                or tile in seen_tiles
            ):
                return False, "invalid instance: tile IDs must occur exactly once"
            seen_tiles.add(tile)
            tile_stack[tile] = stack_index
    if len(seen_tiles) != tile_count:
        return False, "invalid instance: tile IDs must occur exactly once"

    pair_node = [-1] * tile_count
    node = 0
    for group, code in enumerate(answer):
        tiles = groups[group]
        for left, right in _PAIRINGS[code]:
            a, b = tiles[left], tiles[right]
            if tile_stack[a] == tile_stack[b]:
                return False, f"group {group} pairs two tiles in the same stack"
            pair_node[a] = pair_node[b] = node
            node += 1

    adjacency = [set() for _ in range(2 * n)]
    indegree = [0] * (2 * n)
    for stack in inst["stacks"]:
        for upper, lower in zip(stack, stack[1:]):
            source, target = pair_node[upper], pair_node[lower]
            if source == target:
                return False, "a proposed pair is vertically self-blocking"
            if target not in adjacency[source]:
                adjacency[source].add(target)
                indegree[target] += 1

    queue = [node for node, degree in enumerate(indegree) if degree == 0]
    for source in queue:
        for target in adjacency[source]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if len(queue) != 2 * n:
        residue = [i for i, degree in enumerate(indegree) if degree > 0]
        signature = hashlib.sha256(
            json.dumps(answer, separators=(",", ":")).encode("ascii")
        ).hexdigest()[:8]
        return False, (
            "chosen pairings create a directed precedence cycle "
            f"(residual nodes {residue[:6]}, candidate {signature})"
        )
    return True, "ok"


def render(inst: dict) -> str:
    lines = [
        "MAHJONG GROUP-PAIRING PROBLEM (peeking allowed)",
        "",
        "The board consists only of isolated vertical stacks.  In each listed",
        "stack the first tile is the top tile.  A tile is playable exactly when",
        "all tiles before it in that stack have been removed.  A move removes two",
        "playable tiles from the same group.  Every group has exactly four tiles.",
        "",
        "Choose in advance how the four tiles of every group will be split into",
        "two removal pairs.  For group Gg, sort its tile IDs increasingly as",
        "a<b<c<d.  Output 0 for (a,b),(c,d); 1 for (a,c),(b,d); or 2 for",
        "(a,d),(b,c).  The chosen pairs must admit an order that removes the whole",
        "board under the move and playability rules above.",
        "",
        f"There are {inst['n']} groups G0..G{inst['n'] - 1}, "
        f"{len(inst['stacks'])} stacks, and {4 * inst['n']} distinct tiles.",
        "A tile is written T<id>:G<group>.",
        "",
        "STACKS (top -> bottom):",
    ]
    tile_groups = inst["tile_groups"]
    for index, stack in enumerate(inst["stacks"]):
        body = " ".join(f"T{tile}:G{tile_groups[tile]}" for tile in stack)
        lines.append(f"S{index}: {body}")
    lines.extend(
        [
            "",
            f"Give exactly {inst['n']} integers, in group order G0..G{inst['n'] - 1}.",
            "Give your final answer inside <answer></answer> tags, as one JSON",
            "array whose entries are 0, 1, or 2.",
            "Example: <answer>[0,1,2,0]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str):
    if not isinstance(text, str):
        return None
    tagged = re.search(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    candidates = [tagged.group(1)] if tagged else [text]
    for candidate in candidates:
        cleaned = re.sub(r"^\s*```(?:json)?\s*", "", candidate, flags=re.I)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
        starts = [match.start() for match in re.finditer(r"\[", cleaned)]
        if not starts and cleaned.strip():
            starts = [0]
        for start in starts:
            try:
                value, _end = json.JSONDecoder().raw_decode(cleaned[start:].lstrip())
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
            if isinstance(value, list):
                return value
    return None


def random_candidate(inst: dict, rng: random.Random):
    return [rng.randrange(3) for _ in range(inst["n"])]


def search_space(inst: dict) -> int:
    return 3 ** inst["n"]


def enumerate_all(inst: dict):
    space = search_space(inst)
    if space > 100_000:
        return None
    count = 0
    for answer in itertools.product(range(3), repeat=inst["n"]):
        count += int(verify(inst, list(answer))[0])
    return count


def _structural_sequences(inst: dict) -> list[list[int]]:
    return [[inst["tile_groups"][tile] for tile in stack] for stack in inst["stacks"]]


def canonical_key(inst: dict) -> str:
    """A label-invariant ordered-incidence refinement key.

    Exact isomorphism of these ordered hypergraphs is not known to be cheap.  The
    refinement is invariant under stack, group, and tile renaming and is extremely
    discriminating on this distribution; README.md records that it is not a
    complete canonical labelling algorithm.
    """
    sequences = _structural_sequences(inst)
    n = inst["n"]
    color = [0] * n
    for _round in range(2 * n + 1):
        occurrences = [[] for _ in range(n)]
        for sequence in sequences:
            context = tuple(color[group] for group in sequence)
            for position, group in enumerate(sequence):
                occurrences[group].append((position, context))
        signatures = [tuple(sorted(items)) for items in occurrences]
        palette = {signature: i for i, signature in enumerate(sorted(set(signatures)))}
        new_color = [palette[signature] for signature in signatures]
        if new_color == color:
            break
        color = new_color
    normal = sorted(tuple(color[group] for group in sequence) for sequence in sequences)
    payload = json.dumps(
        {"n": n, "height": inst["height"], "stacks": normal},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict):
    n = int(params["n"])
    height = int(params.get("height", 8))
    if n < 240:
        return {"n": min(240, n + 32), "height": height}
    return "cap_bound"


def _encode_pairs(inst: dict, removed_pairs: list[tuple[int, int]]):
    groups = _group_tiles(inst)
    by_group: list[set[frozenset[int]]] = [set() for _ in range(inst["n"])]
    for left, right in removed_pairs:
        group = inst["tile_groups"][left]
        if inst["tile_groups"][right] != group:
            return None
        by_group[group].add(frozenset((left, right)))
    answer = []
    for group, tiles in enumerate(groups):
        if len(by_group[group]) != 2:
            return None
        code = next(
            (code for code in range(3) if _pair_sets_for_code(tiles, code) == by_group[group]),
            None,
        )
        if code is None:
            return None
        answer.append(code)
    return answer


def _play_greedily(inst: dict, rng: random.Random | None = None, mode: str = "lex"):
    positions = [0] * len(inst["stacks"])
    removed: list[tuple[int, int]] = []
    for _step in range(2 * inst["n"]):
        exposed: dict[int, list[int]] = {}
        for stack_index, stack in enumerate(inst["stacks"]):
            position = positions[stack_index]
            if position < len(stack):
                tile = stack[position]
                exposed.setdefault(inst["tile_groups"][tile], []).append(stack_index)
        choices = [(group, stacks) for group, stacks in exposed.items() if len(stacks) >= 2]
        if not choices:
            return None
        if mode == "crowded":
            group, available = max(choices, key=lambda item: (len(item[1]), -item[0]))
        elif mode == "random":
            assert rng is not None
            group, available = rng.choice(choices)
        else:
            group, available = min(choices, key=lambda item: item[0])
        if mode == "random":
            left_stack, right_stack = rng.sample(available, 2)
        else:
            left_stack, right_stack = available[:2]
        left = inst["stacks"][left_stack][positions[left_stack]]
        right = inst["stacks"][right_stack][positions[right_stack]]
        removed.append((left, right))
        positions[left_stack] += 1
        positions[right_stack] += 1
    return _encode_pairs(inst, removed)


def _depth_outlier_answer(inst: dict):
    location = {}
    for stack, tiles in enumerate(inst["stacks"]):
        for depth, tile in enumerate(tiles):
            location[tile] = (stack, depth)
    answer = []
    for tiles in _group_tiles(inst):
        scores = []
        for code, pairing in enumerate(_PAIRINGS):
            score = sum(abs(location[tiles[a]][1] - location[tiles[b]][1]) for a, b in pairing)
            scores.append((score, code))
        answer.append(min(scores)[1])
    return answer


def _partial_acyclic(inst: dict, assignment: dict[int, int]) -> bool:
    groups = _group_tiles(inst)
    pair_node = {}
    node = 0
    for group, code in assignment.items():
        for left, right in _PAIRINGS[code]:
            pair_node[groups[group][left]] = node
            pair_node[groups[group][right]] = node
            node += 1
    adjacency = [set() for _ in range(node)]
    indegree = [0] * node
    for stack in inst["stacks"]:
        for upper, lower in zip(stack, stack[1:]):
            if upper not in pair_node or lower not in pair_node:
                continue
            source, target = pair_node[upper], pair_node[lower]
            if source == target:
                return False
            if target not in adjacency[source]:
                adjacency[source].add(target)
                indegree[target] += 1
    queue = [i for i, degree in enumerate(indegree) if degree == 0]
    for source in queue:
        for target in adjacency[source]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    return len(queue) == node


def _paper_pruning_scan(inst: dict, assignment: dict[int, int]) -> bool:
    """The relaxed cleaning scan from Section 3, implemented event-first."""
    n = inst["n"]
    groups = _group_tiles(inst)
    mate: dict[int, int] = {}
    for group, code in assignment.items():
        for left, right in _PAIRINGS[code]:
            a, b = groups[group][left], groups[group][right]
            mate[a] = b
            mate[b] = a

    positions = [0] * len(inst["stacks"])
    exposed: list[set[int]] = [set() for _ in range(n)]
    started = [False] * n
    removed = 0
    queue = deque()
    queued = [False] * n

    def schedule(group: int):
        if not queued[group]:
            queued[group] = True
            queue.append(group)

    def expose_top(stack_index: int):
        position = positions[stack_index]
        stack = inst["stacks"][stack_index]
        if position < len(stack):
            tile = stack[position]
            group = inst["tile_groups"][tile]
            exposed[group].add(tile)
            schedule(group)

    tile_stack = [-1] * (4 * n)
    for stack_index, stack in enumerate(inst["stacks"]):
        for tile in stack:
            tile_stack[tile] = stack_index
        expose_top(stack_index)

    def remove_tile(tile: int):
        nonlocal removed
        group = inst["tile_groups"][tile]
        exposed[group].remove(tile)
        stack_index = tile_stack[tile]
        positions[stack_index] += 1
        removed += 1
        expose_top(stack_index)

    while queue:
        group = queue.popleft()
        queued[group] = False
        if group in assignment:
            # A fixed group may only be removed in its two proposed pairs.
            while True:
                playable = next(
                    (
                        tile
                        for tile in sorted(exposed[group])
                        if mate.get(tile) in exposed[group]
                    ),
                    None,
                )
                if playable is None:
                    break
                partner = mate[playable]
                remove_tile(playable)
                remove_tile(partner)
        elif started[group]:
            # After the relaxed first pair, the third and fourth tiles are free
            # to be played individually.
            while exposed[group]:
                remove_tile(min(exposed[group]))
        elif len(exposed[group]) >= 2:
            first, second = sorted(exposed[group])[:2]
            started[group] = True
            remove_tile(first)
            remove_tile(second)
            while exposed[group]:
                remove_tile(min(exposed[group]))
    return removed == 4 * n


def _pairing_dfs(inst: dict, node_cap: int = 256):
    # The recursion, pruning scan, and critical-group selection are the three
    # central ingredients of Section 3.  We inspect the 16 shallowest remaining
    # groups for criticality at each node, a bounded implementation of the
    # paper's heuristic that keeps the audit reproducible.
    depths = [[] for _ in range(inst["n"])]
    for stack in inst["stacks"]:
        for depth, tile in enumerate(stack):
            depths[inst["tile_groups"][tile]].append(depth)
    order = sorted(range(inst["n"]), key=lambda g: (sum(depths[g]), g))
    assignment: dict[int, int] = {}
    nodes = 0

    def visit(index: int):
        nonlocal nodes
        if nodes >= node_cap:
            return None
        nodes += 1
        if index == len(order):
            candidate = [assignment[g] for g in range(inst["n"])]
            return candidate if verify(inst, candidate)[0] else False
        remaining = [group for group in order if group not in assignment]
        best_group = remaining[0]
        best_allowed = None
        for candidate_group in remaining[:16]:
            allowed = []
            for code in range(3):
                assignment[candidate_group] = code
                if _partial_acyclic(inst, assignment) and _paper_pruning_scan(inst, assignment):
                    allowed.append(code)
                del assignment[candidate_group]
            if best_allowed is None or len(allowed) < len(best_allowed):
                best_group, best_allowed = candidate_group, allowed
            if not allowed:
                return False
        group = best_group
        for code in best_allowed or []:
            assignment[group] = code
            result = visit(index + 1)
            if result is not False and result is not None:
                return result
            if result is None and nodes >= node_cap:
                del assignment[group]
                return None
            del assignment[group]
        return False

    started = time.perf_counter()
    result = visit(0)
    return result, nodes, time.perf_counter() - started


def _carry_answer_after_tile_relabel(inst: dict, new_tile_of: list[int]):
    old_groups = _group_tiles(inst)
    carried = []
    for group, code in enumerate(inst["answer"]):
        old_pairs = _pair_sets_for_code(old_groups[group], code)
        target = {frozenset(new_tile_of[tile] for tile in pair) for pair in old_pairs}
        new_tiles = sorted(new_tile_of[tile] for tile in old_groups[group])
        carried.append(
            next(
                new_code
                for new_code in range(3)
                if _pair_sets_for_code(new_tiles, new_code) == target
            )
        )
    return carried


def _relabel_instance(
    inst: dict,
    seed: int,
    *,
    relabel_tiles: bool = True,
    relabel_groups: bool = True,
    reorder_stacks: bool = True,
):
    rng = random.Random(seed)
    n = inst["n"]
    tile_map = list(range(4 * n))
    group_map = list(range(n))
    if relabel_tiles:
        rng.shuffle(tile_map)
    if relabel_groups:
        rng.shuffle(group_map)
    carried_before_group = _carry_answer_after_tile_relabel(inst, tile_map)
    stacks = [[tile_map[tile] for tile in stack] for stack in inst["stacks"]]
    if reorder_stacks:
        rng.shuffle(stacks)
    tile_groups = [0] * (4 * n)
    for old_tile, old_group in enumerate(inst["tile_groups"]):
        tile_groups[tile_map[old_tile]] = group_map[old_group]
    answer = [0] * n
    for old_group, code in enumerate(carried_before_group):
        answer[group_map[old_group]] = code
    return {
        "n": n,
        "height": inst["height"],
        "stacks": stacks,
        "tile_groups": tile_groups,
        "answer": answer,
    }


def _cycle_score(inst: dict, answer: list[int]) -> int:
    """How many contracted pair nodes Kahn's algorithm can eliminate."""
    n = inst["n"]
    groups = _group_tiles(inst)
    pair_node = [-1] * (4 * n)
    node = 0
    for group, code in enumerate(answer):
        for left, right in _PAIRINGS[code]:
            pair_node[groups[group][left]] = node
            pair_node[groups[group][right]] = node
            node += 1
    adjacency = [set() for _ in range(2 * n)]
    indegree = [0] * (2 * n)
    for stack in inst["stacks"]:
        for upper, lower in zip(stack, stack[1:]):
            source, target = pair_node[upper], pair_node[lower]
            if source == target:
                return -1
            if target not in adjacency[source]:
                adjacency[source].add(target)
                indegree[target] += 1
    queue = [i for i, degree in enumerate(indegree) if degree == 0]
    for source in queue:
        for target in adjacency[source]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    return len(queue)


def _depth_repair_hillclimb(inst: dict, seed: int, steps: int = 3000):
    """Repair the construction's strongest visible statistical clue."""
    rng = random.Random(seed)
    answer = _depth_outlier_answer(inst)
    score = _cycle_score(inst, answer)
    evaluations = 1
    for iteration in range(steps):
        if score == 2 * inst["n"]:
            return answer, evaluations, iteration
        group = rng.randrange(inst["n"])
        old_code = answer[group]
        alternatives = [code for code in range(3) if code != old_code]
        rng.shuffle(alternatives)
        best_score, best_code = score, old_code
        for code in alternatives:
            answer[group] = code
            candidate_score = _cycle_score(inst, answer)
            evaluations += 1
            if candidate_score > best_score:
                best_score, best_code = candidate_score, code
        answer[group] = best_code
        score = best_score
        # Rare plateau moves make this a real repair attack rather than pure
        # coordinate ascent, while retaining a deterministic operation budget.
        if best_code == old_code and rng.random() < 0.03:
            answer[group] = rng.choice(alternatives)
            score = _cycle_score(inst, answer)
            evaluations += 1
    if score == 2 * inst["n"]:
        return answer, evaluations, steps
    return None, evaluations, steps


def _find_invalid_swap(inst: dict):
    planted = inst["answer"]
    for left in range(len(planted)):
        for right in range(left + 1, len(planted)):
            if planted[left] == planted[right]:
                continue
            candidate = planted[:]
            candidate[left], candidate[right] = candidate[right], candidate[left]
            ok, reason = verify(inst, candidate)
            if not ok:
                return candidate, reason
    return None, "no invalid coordinate swap found"


def selftest() -> dict:
    report: dict = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    g1_failures = []
    g1_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            g1_checks += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed, "reason": "answer not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    corruptions = {
        "drop": planted[:-1],
        "duplicate": planted + [planted[-1]],
        "empty": [],
        "out_of_range": [3] + planted[1:],
    }
    swapped, swap_note = _find_invalid_swap(shipping)
    if swapped is not None:
        corruptions["swap"] = swapped
    corruption_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": (
            len(corruptions) == 5
            and all(item["rejected"] for item in corruption_results.values())
            and len(set(reasons)) == len(reasons)
        ),
        "results": corruption_results,
        "swap_note": swap_note,
    }

    response = (
        "I used the precedence-cycle test.\n```json\n<answer>"
        + json.dumps(planted, separators=(",", ":"))
        + "</answer>\n```\nThe array is in group order."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("garbage without an array") is None,
        "parsed_matches": parsed == planted,
    }

    guess_total = 200_000
    guess_hits = 0
    guess_rng = random.Random(0x12036559)
    started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_seconds = time.perf_counter() - started
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "wall_clock_sec": round(guess_seconds, 6),
        "candidate_space": str(search_space(shipping)),
        "sampling_prior": "uniform over all three locally legal pairings per group",
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)

    attack_seeds = list(range(100, 108))
    attack_counts = {
        "outlier_minimum_depth_gap": 0,
        "depth_outlier_repair_hillclimb_3000": 0,
        "greedy_exposed_lexicographic": 0,
        "random_restart_32": 0,
        "paper_group_pairing_dfs_256": 0,
    }
    dfs_nodes = 0
    dfs_seconds = 0.0
    repair_evaluations = 0
    repair_seconds = 0.0
    outlier_entry_matches = 0
    outlier_entry_total = 0
    restart_attempts = 0
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidate = _depth_outlier_answer(inst)
        attack_counts["outlier_minimum_depth_gap"] += int(verify(inst, candidate)[0])
        outlier_entry_matches += sum(
            proposed == planted
            for proposed, planted in zip(candidate, inst["answer"])
        )
        outlier_entry_total += inst["n"]

        repair_started = time.perf_counter()
        candidate, evaluations, _iterations = _depth_repair_hillclimb(
            inst, seed=seed, steps=3000
        )
        repair_seconds += time.perf_counter() - repair_started
        repair_evaluations += evaluations
        attack_counts["depth_outlier_repair_hillclimb_3000"] += int(
            candidate is not None and verify(inst, candidate)[0]
        )

        candidate = _play_greedily(inst, mode="lex")
        attack_counts["greedy_exposed_lexicographic"] += int(
            candidate is not None and verify(inst, candidate)[0]
        )

        restart_success = False
        for restart in range(32):
            restart_attempts += 1
            rng = random.Random((seed + 1) * 1_000_003 + restart)
            candidate = _play_greedily(inst, rng=rng, mode="random")
            if candidate is not None and verify(inst, candidate)[0]:
                restart_success = True
                break
        attack_counts["random_restart_32"] += int(restart_success)

        candidate, nodes, seconds = _pairing_dfs(inst, node_cap=256)
        dfs_nodes += nodes
        dfs_seconds += seconds
        attack_counts["paper_group_pairing_dfs_256"] += int(
            candidate is not None and candidate is not False and verify(inst, candidate)[0]
        )

    attacks = {
        name: {"successes": successes, "attempts": len(attack_seeds)}
        for name, successes in attack_counts.items()
    }
    report["G5_density_and_baseline_cost"] = {
        "pass": True,
        "shipping_density_hits": guess_hits,
        "shipping_density_total": guess_total,
        "strongest_attack_wall_clock_sec": round(repair_seconds, 6),
        "strongest_attack_operations": repair_evaluations,
        "shipping_density": {
            "hits": guess_hits,
            "total": guess_total,
            "observed_fraction": guess_rate,
        },
        "demo_exact_valid_answers": demo_count,
        "demo_candidate_space": search_space(demo),
        "strongest_attack": {
            "name": "depth-outlier-seeded cycle-score repair hill-climber",
            "wall_clock_sec": round(repair_seconds, 6),
            "operations": repair_evaluations,
            "iteration_cap_per_seed": 3000,
            "seeds": len(attack_seeds),
        },
        "paper_pairing_search_cost": {
            "wall_clock_sec": round(dfs_seconds, 6),
            "nodes": dfs_nodes,
            "node_cap_per_seed": 256,
        },
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in attacks.values()),
        "attacks": attacks,
        "random_restart_trials_executed": restart_attempts,
        "outlier_entry_accuracy": outlier_entry_matches / outlier_entry_total,
        "outlier_entries": {
            "matches": outlier_entry_matches,
            "total": outlier_entry_total,
        },
        "standard_algorithm_note": (
            "The paper_group_pairing attack is the paper's natural ternary group-pairing "
            "recursion with exact cycle pruning and a critical-group proxy."
        ),
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    started = time.perf_counter()
    doubled = make_instance(seed=11, **doubled_params)
    doubled_build_seconds = time.perf_counter() - started
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    spaces = [search_space(make_instance(seed=0, **params)) for params in DIFFICULTY.values()]
    report["G7_scales"] = {
        "pass": doubled_ok and all(a < b for a, b in zip(spaces, spaces[1:])),
        "search_spaces_strictly_increase": all(a < b for a, b in zip(spaces, spaces[1:])),
        "doubled_n": doubled_params["n"],
        "doubled_build_sec": round(doubled_build_seconds, 6),
        "doubled_verifies": doubled_ok,
        "reason": doubled_reason,
    }

    invariant_checks = 0
    transformed_verify_checks = 0
    unrelated_keys = []
    transformation_modes = [
        (True, False, False, "tile renaming"),
        (False, True, False, "group renaming"),
        (False, False, True, "stack permutation"),
        (True, True, False, "tile+group"),
        (True, False, True, "tile+stack"),
        (False, True, True, "group+stack"),
        (True, True, True, "tile+group+stack"),
    ]
    invariant_failure = None
    for seed in range(20):
        base = make_instance(n=48, height=8, seed=seed)
        for mode_index, (tiles, groups, stacks, label) in enumerate(transformation_modes):
            transformed = _relabel_instance(
                base,
                seed + 9000 + 100 * mode_index,
                relabel_tiles=tiles,
                relabel_groups=groups,
                reorder_stacks=stacks,
            )
            invariant_checks += 1
            if canonical_key(base) != canonical_key(transformed):
                invariant_failure = {"seed": seed, "transformation": label}
                break
            transformed_verify_checks += int(verify(transformed, transformed["answer"])[0])
        if invariant_failure:
            break
        unrelated_keys.append(canonical_key(base))
    expected_invariance = 20 * len(transformation_modes)
    invariant_ok = invariant_checks == expected_invariance
    report["G8_canonical_key"] = {
        "pass": (
            invariant_ok
            and transformed_verify_checks == expected_invariance
            and len(unrelated_keys) == 20
            and len(set(unrelated_keys)) == 20
        ),
        "invariance_checks": invariant_checks,
        "transformed_answer_verifies": transformed_verify_checks,
        "unrelated_instances": len(unrelated_keys),
        "distinct_keys": len(set(unrelated_keys)),
        "transformations": [mode[3] for mode in transformation_modes],
        "invariance_failure": invariant_failure,
    }

    compact_answer = json.dumps(planted, separators=(",", ":"))
    answer_chars = len(compact_answer)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(planted)
    intended_operations = len(planted)
    report["G9_no_tool_suitability"] = {
        "pass": (
            answer_chars <= 2000
            and answer_elements <= 256
            and intended_operations <= 300
        ),
        "arms": {
            "bare": {"solved": 0, "attempts": 3},
            "hinted": {"solved": 0, "attempts": 3},
            "placebo": {"solved": 0, "attempts": 3},
        },
        "arms_note": "measured by harden.py; see the three transcript files",
        "hinted_minus_placebo": 0.0,
        "hinted_verdict": "hardened",
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    report["pass"] = all(
        gate.get("pass", False)
        for name, gate in report.items()
        if name.startswith("G") and isinstance(gate, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
