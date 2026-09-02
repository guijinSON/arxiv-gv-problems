"""Inverse generator for the Grand Tour puzzle from arXiv:2508.11570.

The public instance is an even square grid plus a perfect matching of forced
grid edges.  A witness is a Hamiltonian cycle containing every forced edge.
Only the Python standard library is used, and generation is deterministic in
``(n, seed)``.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from typing import Iterable


DIFFICULTY = {
    "standard": {"n": 11},
    "hard": {"n": 15},
    "extreme": {"n": 20},
}
SHIPPING_DIFFICULTY = "standard"

NOTES = r"""
Family and definition.  Section 2.1 of Kiatchaipipat and Ruangwises,
"NP-Completeness Proofs of Puzzles using the T-Metacell Framework"
(arXiv:2508.11570v2), defines Grand Tour as finding one loop through every
graph vertex exactly once while including every edge marked as mandatory.  The
paper also states in Section 1.2 that all traversal is orthogonal.  This module
therefore uses the full orthogonal grid graph and asks for the loop as a cyclic
ordering of all row-major vertex IDs.

Hard and easy regimes.  Section 2.1 proves Grand Tour NP-complete with an
arbitrarily small forced/unforced-edge proportion and ASP-complete using a 5x5
asymmetric forced-edge T-metacell in which every vertex has at least one forced
edge.  It also identifies the opposite extreme: forcing both cycle incidences
at every vertex induces the Hamiltonian cycle and cannot implement the
metacell.  We stay between those extremes by publishing exactly one forced
edge at every vertex (a perfect matching).  The paper gives no polynomial,
closed-form, FPT, or approximation algorithm for this regime.  ASP-completeness
also says that finding another witness remains NP-complete even when witnesses
are supplied.

Inverse generation and attacks.  The answer is sampled first as the boundary
cycle obtained by merging 2x2 cycles along a uniformly sampled coarse-grid
spanning tree.  A random alternating half becomes the forced perfect matching;
all grid edges remain available, so planted and non-planted available edges
have identical public representation.  The self-test directly attacks the
remaining construction signature with (1) the original 2x2 block completion,
(2) a deterministic least-freedom/left-to-right greedy walk through forced
pairs, (3) randomized least-freedom restarts, and (4) randomized complementary
perfect matchings followed by greedy 2x2 flips that merge cycles.  The last
attack solved 4/8 instances at the discarded n=8 setting, causing that preset
to be rejected; the shipped size is accepted only if all attacks fail across at
least eight seeds.

Canonicalization.  Coordinates are semantic: arbitrary vertex renumbering is
not a family symmetry because IDs are defined by the row-major coordinate
formula.  The cheap exact symmetries are reordering/reorienting the forced-edge
input plus all eight rotations/reflections of the square.  canonical_key takes
the lexicographically least forced-edge set under that full dihedral group.
""".strip()


def _edge(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _vid(r: int, c: int, side: int) -> int:
    return r * side + c


def _coarse_neighbors(v: int, n: int) -> list[int]:
    r, c = divmod(v, n)
    out = []
    if r:
        out.append(v - n)
    if c:
        out.append(v - 1)
    if c + 1 < n:
        out.append(v + 1)
    if r + 1 < n:
        out.append(v + n)
    return out


def _wilson_tree(n: int, rng: random.Random) -> list[tuple[int, int]]:
    """Sample a uniform spanning tree of the n by n coarse grid."""
    total = n * n
    root = rng.randrange(total)
    in_tree = {root}
    order = [v for v in range(total) if v != root]
    rng.shuffle(order)
    tree = []
    for start in order:
        if start in in_tree:
            continue
        path = [start]
        positions = {start: 0}
        cur = start
        while cur not in in_tree:
            nxt = rng.choice(_coarse_neighbors(cur, n))
            if nxt in positions:
                cut = positions[nxt]
                for old in path[cut + 1 :]:
                    positions.pop(old, None)
                path = path[: cut + 1]
            else:
                positions[nxt] = len(path)
                path.append(nxt)
            cur = nxt
        for a, b in zip(path, path[1:]):
            tree.append(_edge(a, b))
            in_tree.add(a)
        in_tree.add(path[-1])
    if len(tree) != total - 1:
        raise AssertionError("Wilson sampler did not produce a spanning tree")
    return tree


def _tree_boundary_cycle(n: int, rng: random.Random) -> set[tuple[int, int]]:
    """Merge n^2 disjoint 2x2 cycles along a random coarse spanning tree."""
    side = 2 * n
    cycle: set[tuple[int, int]] = set()
    for br in range(n):
        for bc in range(n):
            a = _vid(2 * br, 2 * bc, side)
            b = a + 1
            c = a + side
            d = c + 1
            cycle.update((_edge(a, b), _edge(b, d), _edge(c, d), _edge(a, c)))

    for x, y in _wilson_tree(n, rng):
        xr, xc = divmod(x, n)
        yr, yc = divmod(y, n)
        if xr == yr:
            if xc > yc:
                xr, xc, yr, yc = yr, yc, xr, xc
            left_top = _vid(2 * xr, 2 * xc + 1, side)
            right_top = _vid(2 * yr, 2 * yc, side)
            old = (_edge(left_top, left_top + side),
                   _edge(right_top, right_top + side))
            new = (_edge(left_top, right_top),
                   _edge(left_top + side, right_top + side))
        else:
            if xr > yr:
                xr, xc, yr, yc = yr, yc, xr, xc
            top_left = _vid(2 * xr + 1, 2 * xc, side)
            bottom_left = _vid(2 * yr, 2 * yc, side)
            old = (_edge(top_left, top_left + 1),
                   _edge(bottom_left, bottom_left + 1))
            new = (_edge(top_left, bottom_left),
                   _edge(top_left + 1, bottom_left + 1))
        cycle.remove(old[0])
        cycle.remove(old[1])
        cycle.add(new[0])
        cycle.add(new[1])
    return cycle


def _cycle_adjacency(edges: Iterable[tuple[int, int]], total: int) -> list[list[int]]:
    adj = [[] for _ in range(total)]
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    return adj


def _is_single_cycle(edges: set[tuple[int, int]], total: int) -> bool:
    if len(edges) != total:
        return False
    adj = _cycle_adjacency(edges, total)
    if any(len(ns) != 2 for ns in adj):
        return False
    seen = {0}
    stack = [0]
    while stack:
        stack.extend(v for v in adj[stack.pop()] if v not in seen and not seen.add(v))
    return len(seen) == total


def _cycle_order(edges: set[tuple[int, int]], total: int) -> list[int]:
    adj = _cycle_adjacency(edges, total)
    if any(len(ns) != 2 for ns in adj):
        raise AssertionError("not a 2-regular graph")
    order = [0]
    prev = -1
    cur = 0
    nxt = min(adj[0])
    while nxt != 0:
        order.append(nxt)
        prev, cur = cur, nxt
        a, b = adj[cur]
        nxt = b if a == prev else a
        if len(order) > total:
            raise AssertionError("cycle traversal did not close")
    if len(order) != total:
        raise AssertionError("cycle has more than one component")
    return order


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Plant a Grand Tour first, then expose one alternating matching.

    ``n`` is half the grid side, so an instance has ``4*n*n`` vertices.  Larger
    n strictly enlarges both the witness and the structural candidate space.
    """
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    rng = random.Random(seed)
    side = 2 * n
    total = side * side
    cycle = _tree_boundary_cycle(n, rng)
    answer = _cycle_order(cycle, total)
    offset = rng.randrange(2)
    forced = []
    for i in range(offset, total, 2):
        forced.append(_edge(answer[i], answer[(i + 1) % total]))
    forced.sort()
    return {
        "family": "Grand Tour",
        "n": n,
        "height": side,
        "width": side,
        "forced": forced,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render all rules and instance data needed by a solver."""
    height = inst["height"]
    width = inst["width"]
    total = height * width
    forced = " ".join(f"{a}-{b}" for a, b in inst["forced"])
    return f"""Grand Tour witness problem

The graph is a {height}-row by {width}-column rectangular grid of {total} vertices.
Rows are 0 through {height - 1}, columns are 0 through {width - 1}, and the vertex
at (row r, column c) has ID r*{width}+c.  Thus IDs are 0 through {total - 1}.
Two vertices have an available undirected edge exactly when their grid cells share
a side: their coordinates differ by 1 in exactly one coordinate and agree in the
other.  Diagonal and wraparound edges do not exist.

Find one simple closed loop that visits every vertex exactly once and uses every
forced edge below.  A forced edge a-b is undirected.  The forced edges are:
{forced}

Represent the loop by exactly {total} comma-separated vertex IDs v0,...,v{total - 1}
in cyclic order.  Every ID must occur exactly once.  Consecutive IDs must share an
available edge, including v{total - 1} back to v0.  The starting vertex and direction
are arbitrary; do not repeat v0 at the end.

Give your final answer inside <answer></answer> tags, as comma-separated integers.
Example: <answer>0, 1, 5, 4</answer>
Output nothing else inside the tags."""


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL)
_INT_LIST_RE = re.compile(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*")


def parse_answer(text: str) -> object | None:
    """Extract the last well-formed tagged comma-separated integer list."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if not body or _INT_LIST_RE.fullmatch(body) is None:
        return None
    try:
        return [int(piece.strip()) for piece in body.split(",")]
    except (TypeError, ValueError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid Grand Tour cycle without consulting the planted answer."""
    if not isinstance(answer, list):
        return False, "answer must be a list of vertex IDs"
    if not answer:
        return False, "answer is empty"
    total = inst["height"] * inst["width"]
    if len(answer) != total:
        return False, f"wrong length: expected {total} vertex IDs, got {len(answer)}"
    for i, v in enumerate(answer):
        if isinstance(v, bool) or not isinstance(v, int):
            return False, f"vertex at position {i} is not an integer"
        if not 0 <= v < total:
            return False, f"vertex {v} at position {i} is out of range 0..{total - 1}"
    if len(set(answer)) != total:
        return False, "a vertex ID is repeated"

    width = inst["width"]
    used = set()
    for i, a in enumerate(answer):
        b = answer[(i + 1) % total]
        ar, ac = divmod(a, width)
        br, bc = divmod(b, width)
        if abs(ar - br) + abs(ac - bc) != 1:
            return False, f"step {i}: {a}-{b} is not an orthogonal grid edge"
        used.add(_edge(a, b))
    missing = sorted({_edge(a, b) for a, b in inst["forced"]} - used)
    if missing:
        a, b = missing[0]
        return False, f"forced edge {a}-{b} is missing"
    return True, "ok"


def _sample_complement(inst: dict, rng: random.Random) -> set[tuple[int, int]]:
    """Randomized augmenting-path perfect matching, using public data only."""
    side = inst["width"]
    total = side * side
    forced = {_edge(a, b) for a, b in inst["forced"]}
    black = [v for v in range(total) if sum(divmod(v, side)) % 2 == 0]
    rng.shuffle(black)
    options = [[] for _ in range(total)]
    for v in black:
        r, c = divmod(v, side)
        row = options[v]
        for nr, nc in ((r - 1, c), (r, c - 1), (r, c + 1), (r + 1, c)):
            if 0 <= nr < side and 0 <= nc < side:
                u = _vid(nr, nc, side)
                if _edge(u, v) not in forced:
                    row.append(u)
        rng.shuffle(row)

    white_match = [-1] * total
    seen = [0] * total
    stamp = 0

    def augment(v: int) -> bool:
        for u in options[v]:
            if seen[u] == stamp:
                continue
            seen[u] = stamp
            if white_match[u] < 0 or augment(white_match[u]):
                white_match[u] = v
                return True
        return False

    for v in black:
        stamp += 1
        if not augment(v):
            # A complementary matching is guaranteed by the planted cycle, so
            # reaching this branch would be an implementation error, not a
            # reason to bias the sample toward the stored plant.
            raise AssertionError("augmenting matcher failed on a satisfiable instance")

    complement = set()
    for u, v in enumerate(white_match):
        if v >= 0:
            complement.add(_edge(u, v))
    return complement


def _matching_candidate(inst: dict, complement: set[tuple[int, int]],
                        rng: random.Random) -> list[int]:
    """Serialize one or more alternating cycles, breaking only complement edges."""
    total = inst["height"] * inst["width"]
    forced_partner = [-1] * total
    complement_partner = [-1] * total
    for a, b in inst["forced"]:
        forced_partner[a] = b
        forced_partner[b] = a
    for a, b in complement:
        complement_partner[a] = b
        complement_partner[b] = a

    # Traverse every alternating component with its non-forced closing edge at
    # the boundary.  Concatenation preserves all forced edges in the list.
    unseen = set(range(total))
    components = []
    while unseen:
        start = min(unseen)
        order = [start]
        prev = start
        cur = forced_partner[start]
        while cur != start:
            order.append(cur)
            unseen.discard(cur)
            nxt = complement_partner[cur] if forced_partner[cur] == prev else forced_partner[cur]
            prev, cur = cur, nxt
        unseen.discard(start)
        components.append(order)
    rng.shuffle(components)
    return [v for component in components for v in component]


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample a locally valid 2-factor and leave only connectivity unresolved.

    A randomized augmenting-path algorithm finds a perfect matching of allowed
    *non-forced* grid edges.  Together with the forced perfect matching this
    gives degree exactly two at every vertex and uses only available edges.  If
    it has several cycles, their orders are concatenated while breaking only
    non-forced closing edges, so shape, uniqueness, every forced edge, and all
    local degree/adjacency deductions are already enforced.  The candidate is
    valid exactly when that random 2-factor happens to be one cycle.
    """
    return _matching_candidate(inst, _sample_complement(inst, rng), rng)


def search_space(inst: dict) -> int | None:
    """Number of structural cycles modulo rotation and reversal.

    With m forced pairs this is (m-1)! * 2^(m-1).  It is already narrower than
    the naive permutation space because every obvious forced-pair constraint is
    built in.
    """
    m = len(inst["forced"])
    if m < 2:
        return None
    return math.factorial(m - 1) * (1 << (m - 1))


class _EnumerationCap(Exception):
    pass


def enumerate_all(inst: dict) -> int | None:
    """Count solution cycles exactly for small grids; abort above a hard cap."""
    total = inst["height"] * inst["width"]
    if total > 36:
        return None
    side = inst["width"]
    forced = {_edge(a, b) for a, b in inst["forced"]}
    forced_partner = {}
    for a, b in forced:
        forced_partner[a] = b
        forced_partner[b] = a
    options = [[] for _ in range(total)]
    for v in range(total):
        r, c = divmod(v, side)
        for nr, nc in ((r - 1, c), (r, c - 1), (r, c + 1), (r + 1, c)):
            if 0 <= nr < side and 0 <= nc < side:
                u = _vid(nr, nc, side)
                if _edge(u, v) not in forced:
                    options[v].append(u)

    unmatched = set(range(total))
    chosen: list[tuple[int, int]] = []
    count = 0
    nodes = 0
    cap = 2_000_000

    def connected_cycle() -> bool:
        union = forced | set(chosen)
        return _is_single_cycle(union, total)

    def rec() -> None:
        nonlocal count, nodes
        nodes += 1
        if nodes > cap:
            raise _EnumerationCap
        if not unmatched:
            if connected_cycle():
                count += 1
            return
        v = min(unmatched, key=lambda x: sum(u in unmatched for u in options[x]))
        unmatched.remove(v)
        for u in options[v]:
            if u in unmatched:
                unmatched.remove(u)
                chosen.append(_edge(u, v))
                rec()
                chosen.pop()
                unmatched.add(u)
        unmatched.add(v)

    try:
        rec()
    except _EnumerationCap:
        return None
    return count


def _transform_vertex(v: int, side: int, sym: int) -> int:
    r, c = divmod(v, side)
    if sym == 0:
        nr, nc = r, c
    elif sym == 1:
        nr, nc = c, side - 1 - r
    elif sym == 2:
        nr, nc = side - 1 - r, side - 1 - c
    elif sym == 3:
        nr, nc = side - 1 - c, r
    elif sym == 4:
        nr, nc = r, side - 1 - c
    elif sym == 5:
        nr, nc = side - 1 - r, c
    elif sym == 6:
        nr, nc = c, r
    elif sym == 7:
        nr, nc = side - 1 - c, side - 1 - r
    else:
        raise ValueError("symmetry index must be 0..7")
    return _vid(nr, nc, side)


def _transformed_instance(inst: dict, sym: int, reverse_input: bool = False) -> dict:
    side = inst["width"]
    out = dict(inst)
    out["forced"] = [
        _edge(_transform_vertex(a, side, sym), _transform_vertex(b, side, sym))
        for a, b in inst["forced"]
    ]
    if reverse_input:
        out["forced"] = [(b, a) for a, b in reversed(out["forced"])]
    out["answer"] = [_transform_vertex(v, side, sym) for v in inst["answer"]]
    return out


def canonical_key(inst: dict) -> str:
    """Exact D4-invariant key for the coordinate-semantic square-grid instance."""
    side = inst["width"]
    forms = []
    for sym in range(8):
        edges = sorted(
            _edge(_transform_vertex(a, side, sym), _transform_vertex(b, side, sym))
            for a, b in inst["forced"]
        )
        forms.append(json.dumps([side, edges], separators=(",", ":")))
    canonical = min(forms)
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase the grid side safely; inverse planting prevents unsatisfiability."""
    if "n" not in params:
        return None
    out = dict(params)
    out["n"] = int(out["n"]) + max(3, int(out["n"]) // 3)
    return out


def _pairs_and_orientations(inst: dict):
    pairs = [tuple(x) for x in inst["forced"]]
    for i, (a, b) in enumerate(pairs):
        yield i, a, b
        yield i, b, a


def _pair_walk_attack(inst: dict, randomized: bool, rng: random.Random | None = None,
                      restarts: int = 1) -> list[int]:
    """Cheap Warnsdorff-style walk on contracted forced pairs."""
    pairs = [tuple(x) for x in inst["forced"]]
    side = inst["width"]
    total = side * side
    pair_of = {}
    for i, (a, b) in enumerate(pairs):
        pair_of[a] = i
        pair_of[b] = i

    def neighbors(v: int):
        r, c = divmod(v, side)
        for nr, nc in ((r - 1, c), (r, c - 1), (r, c + 1), (r + 1, c)):
            if 0 <= nr < side and 0 <= nc < side:
                u = _vid(nr, nc, side)
                if pair_of[u] != pair_of[v]:
                    yield u

    def onward(exit_v: int, used: set[int]) -> int:
        return sum(pair_of[u] not in used for u in neighbors(exit_v))

    for attempt in range(restarts):
        if randomized and rng is not None:
            start_pair = rng.randrange(len(pairs))
            flip = rng.randrange(2)
        else:
            start_pair = 0
            flip = 0
        x, y = pairs[start_pair]
        if flip:
            x, y = y, x
        path = [x, y]
        used = {start_pair}
        current = y
        while len(used) < len(pairs):
            candidates = []
            for entry in neighbors(current):
                p = pair_of[entry]
                if p in used:
                    continue
                a, b = pairs[p]
                exit_v = b if entry == a else a
                candidates.append((onward(exit_v, used | {p}), p, entry, exit_v))
            if not candidates:
                break
            candidates.sort()
            if randomized and rng is not None:
                best = candidates[0][0]
                pool = [x for x in candidates if x[0] <= best + 1]
                _, p, entry, exit_v = rng.choice(pool)
            else:
                _, p, entry, exit_v = candidates[0]
            path.extend((entry, exit_v))
            used.add(p)
            current = exit_v
        if len(path) == total:
            ok, _ = verify(inst, path)
            if ok:
                return path
    return path if 'path' in locals() else []


def _coarse_block_attack(inst: dict) -> list[int]:
    """Guess the unmixed 2x2 construction's complementary matching."""
    side = inst["width"]
    total = side * side
    forced = {_edge(a, b) for a, b in inst["forced"]}
    chosen = set()
    matched = set()
    preferred = []
    fallback = []
    for r in range(side):
        for c in range(side):
            v = _vid(r, c, side)
            if c + 1 < side:
                e = _edge(v, v + 1)
                (preferred if r % 2 == 0 else fallback).append(e)
            if r + 1 < side:
                e = _edge(v, v + side)
                (preferred if c % 2 == 0 else fallback).append(e)
    for a, b in preferred + fallback:
        if (a, b) not in forced and a not in matched and b not in matched:
            chosen.add((a, b))
            matched.update((a, b))
    union = forced | chosen
    if len(matched) == total and _is_single_cycle(union, total):
        return _cycle_order(union, total)
    return list(range(total))


def _component_count(edges: set[tuple[int, int]], total: int) -> int:
    adj = _cycle_adjacency(edges, total)
    seen = set()
    count = 0
    for start in range(total):
        if start in seen:
            continue
        count += 1
        seen.add(start)
        stack = [start]
        while stack:
            for v in adj[stack.pop()]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
    return count


def _cycle_merge_attack(inst: dict, rng: random.Random,
                        restarts: int = 64) -> list[int]:
    """Greedily flip complementary domino pairs when a flip merges cycles."""
    side = inst["width"]
    total = side * side
    forced = {_edge(a, b) for a, b in inst["forced"]}
    last = set()
    for _ in range(restarts):
        complement = _sample_complement(inst, rng)
        cycles = _component_count(forced | complement, total)
        while cycles > 1:
            squares = [(r, c) for r in range(side - 1) for c in range(side - 1)]
            rng.shuffle(squares)
            improved = False
            for r, c in squares:
                a = _vid(r, c, side)
                b = a + 1
                d = a + side
                e = d + 1
                horizontal = {_edge(a, b), _edge(d, e)}
                vertical = {_edge(a, d), _edge(b, e)}
                if horizontal <= complement and not (vertical & forced):
                    old, new = horizontal, vertical
                elif vertical <= complement and not (horizontal & forced):
                    old, new = vertical, horizontal
                else:
                    continue
                trial = (complement - old) | new
                new_cycles = _component_count(forced | trial, total)
                if new_cycles < cycles:
                    complement = trial
                    cycles = new_cycles
                    improved = True
                    break
            if not improved:
                break
        if cycles == 1:
            return _cycle_order(forced | complement, total)
        last = complement
    return _matching_candidate(inst, last, rng)


def selftest() -> dict:
    """Run and measure gates G1--G8; raise AssertionError on any failure."""
    report = {}

    checked = 0
    for name, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            assert ok, (name, seed, why)
            checked += 1
    report["G1_planted_verifies"] = {"pass": True, "instances": checked}

    ship = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260831, **ship)
    planted = inst["answer"]
    corruptions = {
        "empty": [],
        "drop_one": planted[:-1],
        "duplicate": [planted[0], planted[0]] + planted[2:],
        "out_of_range": [inst["height"] * inst["width"]] + planted[1:],
    }
    swapped = None
    for i in range(1, min(len(planted), 20)):
        trial = planted[:]
        trial[i], trial[(i + 1) % len(trial)] = trial[(i + 1) % len(trial)], trial[i]
        ok, why = verify(inst, trial)
        if not ok and "not an orthogonal grid edge" in why:
            swapped = trial
            break
    assert swapped is not None
    corruptions["swap_adjacent"] = swapped
    reasons = {}
    for label, bad in corruptions.items():
        ok, why = verify(inst, bad)
        assert not ok
        reasons[label] = why
    assert len(set(reasons.values())) == len(reasons), reasons
    report["G2_rejects_corruption"] = {"pass": True, "reasons": reasons}

    response = "Here is the completed tour.\n```text\n<answer>" + ", ".join(
        map(str, planted)) + "</answer>\n```\nI checked the closing edge."
    parsed = parse_answer(response)
    assert parsed == planted
    assert parse_answer("garbage without tags") is None
    assert parse_answer("<answer>1, nope, 3</answer>") is None
    report["G3_round_trip"] = {"pass": True, "vertices": len(planted)}

    guess_inst = make_instance(seed=8675309, **ship)
    guess_rng = random.Random(13579)
    total_guesses = 200_000
    hits = 0
    for _ in range(total_guesses):
        candidate = random_candidate(guess_inst, guess_rng)
        if verify(guess_inst, candidate)[0]:
            hits += 1
    probability = hits / total_guesses
    assert probability < 1e-6, (hits, total_guesses)
    report["G4_guess_resistance"] = {
        "pass": True,
        "hits": hits,
        "total": total_guesses,
        "empirical_probability": probability,
        "prior": "randomized augmenting-path complementary grid matchings; only global connectivity is unenforced",
        "structural_search_space": search_space(guess_inst),
    }

    sparse_rows = []
    for seed in (2, 3, 5):
        small = make_instance(n=2, seed=seed)
        solutions = enumerate_all(small)
        space = search_space(small)
        assert solutions is not None and solutions >= 1
        fraction = solutions / space
        assert fraction < 0.001, (seed, solutions, space, fraction)
        sparse_rows.append({"seed": seed, "solutions": solutions,
                            "space": space, "fraction": fraction})
    report["G5_sparse"] = {"pass": True, "instances": sparse_rows}

    attack_seeds = list(range(3100, 3108))
    attack_results = {
        "coarse_2x2_signature": {"solved": 0, "trials": len(attack_seeds)},
        "deterministic_least_freedom_greedy": {"solved": 0, "trials": len(attack_seeds)},
        "randomized_least_freedom_512_restarts": {"solved": 0, "trials": len(attack_seeds)},
        "perfect_matching_cycle_merge_64_restarts": {"solved": 0, "trials": len(attack_seeds)},
    }
    for seed in attack_seeds:
        target = make_instance(seed=seed, **ship)
        if verify(target, _coarse_block_attack(target))[0]:
            attack_results["coarse_2x2_signature"]["solved"] += 1
        if verify(target, _pair_walk_attack(target, False))[0]:
            attack_results["deterministic_least_freedom_greedy"]["solved"] += 1
        rrng = random.Random(seed ^ 0x5A17)
        if verify(target, _pair_walk_attack(target, True, rrng, 512))[0]:
            attack_results["randomized_least_freedom_512_restarts"]["solved"] += 1
        mrng = random.Random(seed * 1000 + 97)
        if verify(target, _cycle_merge_attack(target, mrng, 64))[0]:
            attack_results["perfect_matching_cycle_merge_64_restarts"]["solved"] += 1
    assert all(row["solved"] == 0 for row in attack_results.values()), attack_results
    report["G6_adversary_panel"] = {"pass": True, "attacks": attack_results}

    doubled_params = dict(ship)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=424242, **doubled_params)
    ok, why = verify(doubled, doubled["answer"])
    assert ok, why
    assert len(doubled["answer"]) > len(inst["answer"])
    assert search_space(doubled) > search_space(inst)
    report["G7_scales"] = {
        "pass": True,
        "base_vertices": len(inst["answer"]),
        "doubled_n_vertices": len(doubled["answer"]),
        "planted_verifies": True,
    }

    invariant_checks = 0
    real_transform_checks = 0
    keys = []
    for seed in range(20):
        base = make_instance(n=5, seed=9000 + seed)
        key = canonical_key(base)
        keys.append(key)
        for sym in range(8):
            transformed = _transformed_instance(base, sym, reverse_input=(sym % 2 == 1))
            assert canonical_key(transformed) == key
            invariant_checks += 1
            ok, why = verify(transformed, transformed["answer"])
            assert ok, (seed, sym, why)
            real_transform_checks += 1
    distinct = len(set(keys))
    assert distinct == len(keys)
    report["G8_canonical_key"] = {
        "pass": True,
        "invariance_checks": invariant_checks,
        "real_transform_checks": real_transform_checks,
        "distinct_unrelated": distinct,
        "unrelated_total": len(keys),
        "symmetries": "8 square dihedral maps, composed with input reversal",
    }

    report["all_passed"] = all(
        isinstance(v, dict) and v.get("pass")
        for k, v in report.items() if k.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2))
