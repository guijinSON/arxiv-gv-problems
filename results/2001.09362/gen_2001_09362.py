"""Inverse generator for an S-packing coloring search family.

The graph is given compactly.  Its vertices are q anchors and q^2 cells.  The
anchors form a clique, every row and every column of cells forms a clique, and
a clue cell is joined to all anchors except the one named by its clue.  For the
sequence S=(1,...,1), an S-packing coloring is exactly a proper q-coloring.
After normalising the anchor colors, its cell colors are precisely a completion
of the partial Latin square in ``clues``.

Only the Python standard library is used.  Importing this module has no side
effects.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections import Counter


DIFFICULTY = {
    "demo": {
        "n": 5,
        "clue_density": 0.52,
        "filter_nodes": 0,
        "attack_filter": False,
    },
    "easy": {
        "n": 20,
        "clue_density": 0.4,
        "filter_nodes": 100000,
        "attack_filter": True,
    },
    "medium": {
        "n": 22,
        "clue_density": 0.40,
        "filter_nodes": 100_000,
        "attack_filter": True,
    },
    "hard": {
        "n": 26,
        "clue_density": 0.40,
        "filter_nodes": 150_000,
        "attack_filter": True,
    },
}

SHIPPING_DIFFICULTY = "medium"

NOTES = r"""
Paper basis: Section 1 of Holub--Jakovac--Klavzar, “S-packing chromatic
vertex-critical graphs” (arXiv:2001.09362), gives the exact distance definition
and explicitly observes that S=(1,1,...) is ordinary proper vertex coloring.
We use that specialization, represented by a compact rook-graph plus anchor
clique.  Proposition 2.2 identifies the two-color/bipartite easy regime; the
complete low-color critical classifications in Theorems 3.1 and 4.1 and the
caterpillar bound in Proposition 5.2 are therefore not used as search regimes.
The cited complexity literature also separates the NP-complete three-color
regime from polynomial cases.  Independently, partial Latin-square completion
is NP-complete (Colbourn, Discrete Applied Mathematics 8 (1984), 25--30).

Generation samples a randomized completed Latin square and a permutation of
the output colors first, then samples clues from that completion.  The hard
presets retain only public instances on which a bounded deterministic MRV
completion search exhausts its node budget.  Clue positions are uniform; there
is no separate decoy distribution.  A final random row/column/symbol relabeling
and optional transpose hide row-construction order.  The adversary panel tests
cyclic/positional formulas, deterministic greedy completion, and row-preserving
min-conflicts restarts.  Hard-preset generation rejects a clue set if any of
those succeeds.

canonical_key is a hash of a typed incidence-graph Weisfeiler--Lehman
invariant, not of the seed, render output, planted completion, or input order.
It is invariant under row/column/symbol permutations, row-column transpose,
and clue reordering.  This is a strong cheap invariant, not a complete
isomorphism canonizer; rare non-isomorphic collisions remain possible.
""".strip()


_ANSWER_RE = re.compile(r"<answer>\s*(.*?)\s*</answer>", re.IGNORECASE | re.DOTALL)
_INT_LIST_RE = re.compile(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*")


def _clue_dict(inst: dict) -> dict[tuple[int, int], int]:
    """Return clues as a mapping, rejecting duplicate positions consistently."""
    result: dict[tuple[int, int], int] = {}
    for item in inst.get("clues", []):
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            continue
        r, c, s = item
        result[(r, c)] = s
    return result


def _random_latin_square(q: int, rng: random.Random) -> list[list[int]]:
    """Construct a varied Latin square via random perfect matchings, row by row."""
    square: list[list[int]] = []
    used_in_column = [set() for _ in range(q)]

    for _ in range(q):
        columns = list(range(q))
        rng.shuffle(columns)
        preferences = {
            c: rng.sample(
                [s for s in range(q) if s not in used_in_column[c]],
                q - len(used_in_column[c]),
            )
            for c in columns
        }
        symbol_to_column: dict[int, int] = {}

        def augment(column: int, seen: set[int]) -> bool:
            for symbol in preferences[column]:
                if symbol in seen:
                    continue
                seen.add(symbol)
                previous = symbol_to_column.get(symbol)
                if previous is None or augment(previous, seen):
                    symbol_to_column[symbol] = column
                    return True
            return False

        for column in columns:
            if not augment(column, set()):
                raise RuntimeError("internal Latin-square matching failure")

        row = [-1] * q
        for symbol, column in symbol_to_column.items():
            row[column] = symbol
            used_in_column[column].add(symbol)
        square.append(row)

    # Remove the temporal signature of the row-by-row construction.
    row_order = list(range(q))
    column_order = list(range(q))
    symbol_order = list(range(q))
    rng.shuffle(row_order)
    rng.shuffle(column_order)
    rng.shuffle(symbol_order)
    transformed = [
        [symbol_order[square[row_order[r]][column_order[c]]] for c in range(q)]
        for r in range(q)
    ]
    if rng.randrange(2):
        transformed = [[transformed[c][r] for c in range(q)] for r in range(q)]
    return transformed


def _completion_state(inst: dict):
    """Build domains for a normalized partial Latin square, or return None."""
    q = inst.get("n")
    if type(q) is not int or q < 1:
        return None
    rows = [set(range(q)) for _ in range(q)]
    columns = [set(range(q)) for _ in range(q)]
    open_cells = {(r, c) for r in range(q) for c in range(q)}
    for (r, c), symbol in _clue_dict(inst).items():
        if not (type(r) is type(c) is type(symbol) is int):
            return None
        if not (0 <= r < q and 0 <= c < q and 0 <= symbol < q):
            return None
        if symbol not in rows[r] or symbol not in columns[c]:
            return None
        rows[r].remove(symbol)
        columns[c].remove(symbol)
        open_cells.discard((r, c))
    return rows, columns, open_cells


def _bounded_completion_search(inst: dict, cap: int) -> tuple[bool, int]:
    """Deterministic MRV search.  False with nodes>cap means budget exhaustion."""
    state = _completion_state(inst)
    if state is None:
        return False, 0
    rows, columns, open_cells = state
    nodes = 0

    def visit() -> bool:
        nonlocal nodes
        nodes += 1
        if nodes > cap:
            return False
        if not open_cells:
            return True
        cell = min(
            open_cells,
            key=lambda rc: (len(rows[rc[0]] & columns[rc[1]]), rc[0], rc[1]),
        )
        r, c = cell
        domain = rows[r] & columns[c]
        if not domain:
            return False
        open_cells.remove(cell)
        for symbol in sorted(domain):
            rows[r].remove(symbol)
            columns[c].remove(symbol)
            if visit():
                return True
            rows[r].add(symbol)
            columns[c].add(symbol)
            if nodes > cap:
                break
        open_cells.add(cell)
        return False

    return visit(), nodes


def _symbols_to_answer(q: int, grid: list[list[int]]) -> list[int]:
    return list(range(1, q + 1)) + [grid[r][c] + 1 for r in range(q) for c in range(q)]


def _greedy_grid(inst: dict, mrv: bool) -> list[list[int]] | None:
    state = _completion_state(inst)
    if state is None:
        return None
    q = inst["n"]
    rows, columns, open_cells = state
    grid = [[-1] * q for _ in range(q)]
    for (r, c), symbol in _clue_dict(inst).items():
        grid[r][c] = symbol

    while open_cells:
        if mrv:
            r, c = min(
                open_cells,
                key=lambda rc: (len(rows[rc[0]] & columns[rc[1]]), rc[0], rc[1]),
            )
        else:
            r, c = min(open_cells)
        domain = rows[r] & columns[c]
        if not domain:
            return None
        symbol = min(domain)
        grid[r][c] = symbol
        rows[r].remove(symbol)
        columns[c].remove(symbol)
        open_cells.remove((r, c))
    return grid


def _attack_outlier(inst: dict) -> bool:
    """Try conspicuous position/magnitude formulas, including cyclic isotopes."""
    q = inst["n"]
    for sign in (1, -1):
        for shift in range(q):
            grid = [[(r + sign * c + shift) % q for c in range(q)] for r in range(q)]
            ok, _ = verify(inst, _symbols_to_answer(q, grid))
            if ok:
                return True
    return False


def _attack_greedy(inst: dict) -> bool:
    """Try row-major and MRV greedy completion without backtracking."""
    q = inst["n"]
    for mrv in (False, True):
        grid = _greedy_grid(inst, mrv)
        if grid is not None and verify(inst, _symbols_to_answer(q, grid))[0]:
            return True
    return False


def _random_restart_answer(inst: dict, restarts: int = 4, step_factor: int = 15):
    """Mild row-preserving min-conflicts; returns a witness or None."""
    q = inst["n"]
    clues = _clue_dict(inst)
    fixed_by_row = [set() for _ in range(q)]
    fixed_symbols = [set() for _ in range(q)]
    for (r, c), symbol in clues.items():
        fixed_by_row[r].add(c)
        fixed_symbols[r].add(symbol)

    seed_material = (canonical_key(inst) + ":random-restart").encode("ascii")
    rng = random.Random(int.from_bytes(hashlib.sha256(seed_material).digest()[:8], "big"))

    def penalty(count: int) -> int:
        return max(0, count - 1)

    for _ in range(restarts):
        grid = [[-1] * q for _ in range(q)]
        for (r, c), symbol in clues.items():
            grid[r][c] = symbol
        for r in range(q):
            free_symbols = [s for s in range(q) if s not in fixed_symbols[r]]
            rng.shuffle(free_symbols)
            for c, symbol in zip(
                [c for c in range(q) if c not in fixed_by_row[r]], free_symbols
            ):
                grid[r][c] = symbol

        counts = [[0] * q for _ in range(q)]
        for r in range(q):
            for c in range(q):
                counts[c][grid[r][c]] += 1
        conflicts = sum(penalty(x) for column in counts for x in column)

        for _step in range(step_factor * q * q):
            if conflicts == 0:
                return _symbols_to_answer(q, grid)
            bad_columns = [c for c in range(q) if any(x > 1 for x in counts[c])]
            c1 = rng.choice(bad_columns)
            movable_rows = [r for r in range(q) if c1 not in fixed_by_row[r]]
            if not movable_rows:
                continue
            duplicate_rows = [r for r in movable_rows if counts[c1][grid[r][c1]] > 1]
            r = rng.choice(duplicate_rows or movable_rows)
            other_columns = [c for c in range(q) if c != c1 and c not in fixed_by_row[r]]
            if not other_columns:
                continue
            sample = rng.sample(other_columns, min(8, len(other_columns)))
            scored: list[tuple[int, int]] = []
            a = grid[r][c1]
            for c2 in sample:
                b = grid[r][c2]
                delta = 0
                delta += penalty(counts[c1][a] - 1) - penalty(counts[c1][a])
                delta += penalty(counts[c1][b] + 1) - penalty(counts[c1][b])
                delta += penalty(counts[c2][b] - 1) - penalty(counts[c2][b])
                delta += penalty(counts[c2][a] + 1) - penalty(counts[c2][a])
                scored.append((delta, c2))
            best_delta = min(delta for delta, _ in scored)
            choices = [c for delta, c in scored if delta == best_delta]
            c2 = rng.choice(choices if rng.random() >= 0.04 else sample)
            b = grid[r][c2]
            actual_delta = 0
            actual_delta += penalty(counts[c1][a] - 1) - penalty(counts[c1][a])
            actual_delta += penalty(counts[c1][b] + 1) - penalty(counts[c1][b])
            actual_delta += penalty(counts[c2][b] - 1) - penalty(counts[c2][b])
            actual_delta += penalty(counts[c2][a] + 1) - penalty(counts[c2][a])
            counts[c1][a] -= 1
            counts[c1][b] += 1
            counts[c2][b] -= 1
            counts[c2][a] += 1
            grid[r][c1], grid[r][c2] = b, a
            conflicts += actual_delta
    return None


def _attack_random_restart(inst: dict) -> bool:
    answer = _random_restart_answer(inst)
    return answer is not None and verify(inst, answer)[0]


def make_instance(
    n: int,
    seed: int = 0,
    clue_density: float = 0.40,
    filter_nodes: int = 0,
    attack_filter: bool = False,
) -> dict:
    """Sample a coloring first, then reveal a hard partial instance around it.

    ``n`` is the Latin-square order q.  The implicit graph has q^2+q vertices
    and q colors, so increasing n enlarges both the witness and its domains.
    """
    if type(n) is not int or n < 3:
        raise ValueError("n must be an integer at least 3")
    if not (0.05 <= clue_density <= 0.90):
        raise ValueError("clue_density must be between 0.05 and 0.90")
    if type(seed) is not int:
        raise TypeError("seed must be an integer")
    if type(filter_nodes) is not int or filter_nodes < 0:
        raise ValueError("filter_nodes must be a nonnegative integer")

    rng = random.Random(seed)

    # G: the complete witness is sampled before any clue positions.
    latin = _random_latin_square(n, rng)
    anchor_colors = list(range(1, n + 1))
    rng.shuffle(anchor_colors)
    answer = anchor_colors + [
        anchor_colors[latin[r][c]] for r in range(n) for c in range(n)
    ]

    clue_count = max(1, min(n * n - 1, round(clue_density * n * n)))
    all_cells = [(r, c) for r in range(n) for c in range(n)]

    # Recursion depth, rather than mathematical ease, becomes the limiting
    # factor for doubled stress instances.  Above this size the growing q is
    # itself the hardness escalation and filtering is skipped.
    effective_filter = filter_nodes if n * n - clue_count <= 750 else 0
    effective_attacks = attack_filter and n <= 30

    observed_nodes = 0
    for attempt in range(1, 81):
        chosen = rng.sample(all_cells, clue_count)
        clues = [(r, c, latin[r][c]) for r, c in chosen]
        rng.shuffle(clues)
        public = {"n": n, "clues": clues}

        if effective_filter:
            solved, observed_nodes = _bounded_completion_search(public, effective_filter)
            if solved or observed_nodes <= effective_filter:
                continue
        if effective_attacks and (
            _attack_outlier(public)
            or _attack_greedy(public)
            or _attack_random_restart(public)
        ):
            continue

        return {
            "n": n,
            "clues": clues,
            "answer": answer,
            "clue_density": clue_density,
            "filter_nodes": filter_nodes,
            "filter_observed_nodes": observed_nodes,
            "generation_attempts": attempt,
        }
    raise RuntimeError("could not sample an attack-resistant clue set in 80 attempts")


def render(inst: dict) -> str:
    """Render a complete, self-contained statement for the solver."""
    q = inst["n"]
    clues = sorted(_clue_dict(inst).items())
    clue_lines = "\n".join(f"  ({r},{c}) = {s}" for (r, c), s in clues)
    total = q + q * q
    return f"""S-packing coloring of a compactly defined graph

There are q = {q} available color labels: the integers 1 through {q}.
Use the S-packing sequence S = ({', '.join(['1'] * q)}).  An S-packing
coloring assigns one color label to every vertex, and two distinct vertices
with the same label must have graph distance strictly greater than 1.  Thus,
for this S, adjacent vertices must have different labels (ordinary proper
vertex coloring).

The undirected graph has these vertices:
  * anchors A[0], ..., A[{q - 1}];
  * cells C[r,c] for 0 <= r < {q} and 0 <= c < {q}.
All indices are 0-based.  Its edges are exactly the following; there are no
others:
  1. Every two distinct anchors are adjacent.
  2. Two distinct cells are adjacent exactly when they share a row or share a
     column: C[r,c]--C[r,d] for c != d, and C[r,c]--C[t,c] for r != t.
  3. For every clue (r,c)=s below, C[r,c] is adjacent to every anchor A[t]
     with t != s, and is not adjacent to A[s].

Clues (each s is an anchor INDEX, not an output color label):
{clue_lines}

Find any proper coloring of all vertices.  The anchor clique necessarily uses
all {q} output labels, and a clue (r,c)=s consequently forces C[r,c] to have
the same output label as A[s].  Output labels may be globally permuted; any
valid coloring is accepted.

Your answer must contain exactly {total} comma-separated base-10 integers, in
this order: A[0] through A[{q - 1}], then all cells in row-major order
C[0,0], C[0,1], ..., C[{q - 1},{q - 1}].  Order matters.  Every integer must
be in the inclusive range 1..{q}; repeats are allowed unless an edge forbids
them.

Give your final answer inside <answer></answer> tags, as one comma-separated
list.  Syntax example: <answer>1, 2, 3</answer> (your actual list must contain
exactly {total} integers).  Output nothing else inside the tags."""


def parse_answer(text: str) -> object | None:
    """Extract the first well-formed tagged comma-separated integer list."""
    if not isinstance(text, str):
        return None
    for match in _ANSWER_RE.finditer(text):
        body = match.group(1).strip()
        if not body or _INT_LIST_RE.fullmatch(body) is None:
            continue
        try:
            return [int(piece.strip()) for piece in body.split(",")]
        except (TypeError, ValueError):
            continue
    return None


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Check any witness using only public instance data; never read the plant."""
    q = inst.get("n")
    if not isinstance(answer, list):
        return False, "answer must be a list"
    if not answer:
        return False, "answer is empty"
    expected = q + q * q
    if len(answer) < expected:
        return False, f"too few colors: expected {expected}, got {len(answer)}"
    if len(answer) > expected:
        return False, f"too many colors: expected {expected}, got {len(answer)}"
    for vertex, color in enumerate(answer):
        if type(color) is not int or not 1 <= color <= q:
            return False, f"color at vertex {vertex} is outside the inclusive range 1..{q}"

    anchors = answer[:q]
    if len(set(anchors)) != q:
        return False, "anchor colors are not all distinct"
    cells = [answer[q + r * q : q + (r + 1) * q] for r in range(q)]
    for r, row in enumerate(cells):
        repeated = next((color for color, count in Counter(row).items() if count > 1), None)
        if repeated is not None:
            return False, f"row {r} repeats color {repeated}"
    for c in range(q):
        column = [cells[r][c] for r in range(q)]
        repeated = next((color for color, count in Counter(column).items() if count > 1), None)
        if repeated is not None:
            return False, f"column {c} repeats color {repeated}"
    for (r, c), symbol in sorted(_clue_dict(inst).items()):
        if cells[r][c] != anchors[symbol]:
            return False, f"clue ({r},{c})={symbol} is violated"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample after enforcing anchor symmetry, every clue, and every row clique.

    The only remaining test is whether independently completed row permutations
    also satisfy every column clique.  This is substantially more informed than
    uniform noise over q^(q^2+q), and it does not inspect the planted answer.
    """
    q = inst["n"]
    clues = _clue_dict(inst)
    candidate = list(range(1, q + 1))
    for r in range(q):
        row = [-1] * q
        used = set()
        for c in range(q):
            if (r, c) in clues:
                symbol = clues[(r, c)]
                row[c] = symbol + 1
                used.add(symbol)
        remaining = [symbol for symbol in range(q) if symbol not in used]
        rng.shuffle(remaining)
        it = iter(remaining)
        for c in range(q):
            if row[c] < 0:
                row[c] = next(it) + 1
        candidate.extend(row)
    return candidate


def search_space(inst: dict) -> int | None:
    """Return the naive labeled-coloring space q^(q^2+q)."""
    q = inst.get("n")
    if type(q) is not int or q < 1:
        return None
    return q ** (q * q + q)


def _structure_aware_space(inst: dict) -> int:
    q = inst["n"]
    clues = _clue_dict(inst)
    result = 1
    for r in range(q):
        fixed = sum((r, c) in clues for c in range(q))
        result *= math.factorial(q - fixed)
    return result


def enumerate_all(inst: dict) -> int | None:
    """Count all labeled witnesses for q<=6, with a hard two-million-node cap."""
    q = inst.get("n")
    if type(q) is not int or q > 6 or q < 1:
        return None
    state = _completion_state(inst)
    if state is None:
        return 0
    rows, columns, open_cells = state
    nodes = 0
    aborted = False

    def count() -> int:
        nonlocal nodes, aborted
        nodes += 1
        if nodes > 2_000_000:
            aborted = True
            return 0
        if not open_cells:
            return 1
        cell = min(
            open_cells,
            key=lambda rc: (len(rows[rc[0]] & columns[rc[1]]), rc[0], rc[1]),
        )
        r, c = cell
        domain = rows[r] & columns[c]
        if not domain:
            return 0
        open_cells.remove(cell)
        total = 0
        for symbol in sorted(domain):
            rows[r].remove(symbol)
            columns[c].remove(symbol)
            total += count()
            rows[r].add(symbol)
            columns[c].add(symbol)
            if aborted:
                break
        open_cells.add(cell)
        return total

    normalized = count()
    return None if aborted else normalized * math.factorial(q)


def canonical_key(inst: dict) -> str:
    """Hash a typed incidence-graph invariant of the public partial square."""
    q = inst["n"]
    clues = sorted((r, c, s) for (r, c), s in _clue_dict(inst).items())
    # Node blocks: rows, columns, symbols, then one node per clue.  Rows and
    # columns deliberately share an initial type so transpose is a symmetry.
    base = 3 * q
    total_nodes = base + len(clues)
    adjacency = [set() for _ in range(total_nodes)]
    edges = []
    for i, (r, c, s) in enumerate(clues):
        node = base + i
        for endpoint in (r, q + c, 2 * q + s):
            adjacency[node].add(endpoint)
            adjacency[endpoint].add(node)
            edges.append((endpoint, node))
    colors = [0] * (2 * q) + [1] * q + [2] * len(clues)
    history = []
    for _ in range(min(total_nodes + 1, 32)):
        signatures = [
            (colors[v], tuple(sorted(colors[w] for w in adjacency[v])))
            for v in range(total_nodes)
        ]
        classes = {signature: i for i, signature in enumerate(sorted(set(signatures)))}
        colors = [classes[signature] for signature in signatures]
        hist = sorted(Counter(colors).items())
        edge_hist = sorted(
            Counter(tuple(sorted((colors[u], colors[v]))) for u, v in edges).items()
        )
        history.append((hist, edge_hist))

    # If refinement becomes discrete this records the complete incidence graph;
    # otherwise it remains a strong (but explicitly incomplete) invariant.
    final_edges = sorted(tuple(sorted((colors[u], colors[v]))) for u, v in edges)
    payload = {
        "family": "partial-latin-as-S1-coloring",
        "q": q,
        "clue_count": len(clues),
        "history": history,
        "final_edges": final_edges,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase Latin order and the public-search rejection budget."""
    q = int(params.get("n", 0))
    if q >= 34:
        return None
    harder = dict(params)
    harder["n"] = q + 4
    harder["filter_nodes"] = min(400_000, max(20_000, int(params.get("filter_nodes", 0)) * 2))
    harder["attack_filter"] = True
    return harder


def _transform_instance(
    inst: dict,
    row_map: list[int],
    column_map: list[int],
    symbol_map: list[int],
    transpose: bool,
) -> tuple[dict, list[int]]:
    """Relabel a public instance and carry its witness through the relabeling."""
    q = inst["n"]
    transformed_clues = []
    for (r, c), symbol in _clue_dict(inst).items():
        if transpose:
            nr, nc = column_map[c], row_map[r]
        else:
            nr, nc = row_map[r], column_map[c]
        transformed_clues.append((nr, nc, symbol_map[symbol]))
    transformed_clues.reverse()

    old = inst["answer"]
    old_anchors = old[:q]
    old_cells = [old[q + r * q : q + (r + 1) * q] for r in range(q)]
    new_anchors = [-1] * q
    new_cells = [[-1] * q for _ in range(q)]
    for symbol in range(q):
        new_anchors[symbol_map[symbol]] = old_anchors[symbol]
    for r in range(q):
        for c in range(q):
            if transpose:
                nr, nc = column_map[c], row_map[r]
            else:
                nr, nc = row_map[r], column_map[c]
            new_cells[nr][nc] = old_cells[r][c]
    carried = new_anchors + [new_cells[r][c] for r in range(q) for c in range(q)]
    transformed = dict(inst)
    transformed["clues"] = transformed_clues
    transformed["answer"] = carried
    return transformed, carried


def selftest() -> dict:
    """Run G1--G8 and return a JSON-serializable measurement report."""
    report: dict[str, object] = {}

    # G1: every preset, three seeds each.
    g1_cases = 0
    g1_failures = []
    preset_instances = {}
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_cases += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
            if seed == 0:
                preset_instances[preset] = inst
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "cases": g1_cases,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = preset_instances.get(SHIPPING_DIFFICULTY) or make_instance(seed=0, **shipping_params)

    # G2: five requested corruptions, each landing on a distinct diagnostic.
    answer = list(inst["answer"])
    corruptions = {
        "drop_one": answer[:-1],
        "duplicate_one": answer + [answer[-1]],
        "empty": [],
        "out_of_range": [0] + answer[1:],
    }
    swapped = list(answer)
    q = inst["n"]
    swapped[q], swapped[q + 1] = swapped[q + 1], swapped[q]
    corruptions["swap_two"] = swapped
    g2_reasons = {name: verify(inst, bad)[1] for name, bad in corruptions.items()}
    g2_rejected = all(not verify(inst, bad)[0] for bad in corruptions.values())
    report["G2_rejects_corruption"] = {
        "pass": g2_rejected and len(set(g2_reasons.values())) == len(g2_reasons),
        "reasons": g2_reasons,
        "distinct_reasons": len(set(g2_reasons.values())),
    }

    # G3: realistic prose and a Markdown fence surrounding the tagged answer.
    encoded = ", ".join(map(str, answer))
    response = f"I checked the row and column constraints.\n```text\n<answer>{encoded}</answer>\n```\n"
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("garbage") is None,
        "parsed_length": len(parsed) if isinstance(parsed, list) else None,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4: the sampler already fixes anchor symmetry, clues, and all row cliques.
    guess_rng = random.Random(0x200109362)
    hits = 0
    trials = 200_000
    for _ in range(trials):
        candidate = random_candidate(inst, guess_rng)
        hits += int(verify(inst, candidate)[0])
    report["G4_guess_resistance"] = {
        "pass": hits / trials < 1e-6,
        "hits": hits,
        "total": trials,
        "empirical_probability": hits / trials,
        "sampler": "anchor-normalized, clue-respecting independent row permutations",
        "structure_aware_space_decimal_digits": len(str(_structure_aware_space(inst))),
        "naive_space_decimal_digits": len(str(search_space(inst))),
    }

    # G5: exact enumeration on a deliberately small generated member.
    tiny = make_instance(
        n=4, seed=314159, clue_density=0.50, filter_nodes=0, attack_filter=False
    )
    exact = enumerate_all(tiny)
    naive = search_space(tiny)
    fraction = None if exact is None or naive is None else exact / naive
    report["G5_sparse"] = {
        "pass": exact is not None and fraction is not None and fraction < 1e-6,
        "q": tiny["n"],
        "valid_answers": exact,
        "naive_space": naive,
        "solution_fraction": fraction,
        "structure_aware_space": _structure_aware_space(tiny),
    }

    # G6: all attacks must fail, not merely have a low success rate.
    attacks = {
        "outlier_position_magnitude": _attack_outlier,
        "greedy_row_major_or_mrv": _attack_greedy,
        "random_restart_min_conflicts": _attack_random_restart,
    }
    attack_results = {}
    for name, attack in attacks.items():
        successes = 0
        for seed in range(8):
            sample = make_instance(seed=10_000 + seed, **shipping_params)
            successes += int(attack(sample))
        attack_results[name] = {"successes": successes, "attempts": 8, "pass": successes == 0}
    report["G6_adversary_panel"] = {
        "pass": all(item["pass"] for item in attack_results.values()),
        "attacks": attack_results,
    }

    # G7: doubling q roughly quadruples vertices and grows the reduced space.
    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * shipping_params["n"]
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    base_digits = len(str(_structure_aware_space(inst)))
    doubled_digits = len(str(_structure_aware_space(doubled)))
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_digits > base_digits,
        "base_q": inst["n"],
        "doubled_q": doubled["n"],
        "base_graph_vertices": inst["n"] ** 2 + inst["n"],
        "doubled_graph_vertices": doubled["n"] ** 2 + doubled["n"],
        "base_structure_space_decimal_digits": base_digits,
        "doubled_structure_space_decimal_digits": doubled_digits,
        "verify_reason": doubled_reason,
    }

    # G8: 20 seeds, composed row/column/symbol permutations, transpose, clue
    # reordering, and output-color permutation.  Also check unrelated keys.
    invariance_checks = 0
    transformed_verify_checks = 0
    g8_failures = []
    unrelated_keys = []
    for seed in range(20):
        sample = make_instance(
            n=7, seed=50_000 + seed, clue_density=0.40,
            filter_nodes=0, attack_filter=False,
        )
        key = canonical_key(sample)
        reordered = dict(sample)
        reordered["clues"] = list(reversed(sample["clues"]))
        invariance_checks += 1
        if canonical_key(reordered) != key:
            g8_failures.append({"seed": seed, "transform": "clue_reorder"})
        if not verify(reordered, sample["answer"])[0]:
            g8_failures.append({"seed": seed, "transform": "reorder_not_real"})
        transformed_verify_checks += 1

        trng = random.Random(90_000 + seed)
        row_map = list(range(7))
        column_map = list(range(7))
        symbol_map = list(range(7))
        palette_map = list(range(7))
        trng.shuffle(row_map)
        trng.shuffle(column_map)
        trng.shuffle(symbol_map)
        trng.shuffle(palette_map)
        transformed, carried = _transform_instance(
            sample, row_map, column_map, symbol_map, transpose=bool(seed % 2)
        )
        carried = [palette_map[color - 1] + 1 for color in carried]
        invariance_checks += 1
        if canonical_key(transformed) != key:
            g8_failures.append({"seed": seed, "transform": "composed_relabel"})
        if not verify(transformed, carried)[0]:
            g8_failures.append({"seed": seed, "transform": "relabel_not_real"})
        transformed_verify_checks += 1
        unrelated_keys.append(key)

    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariance_checks,
        "transformed_witness_verify_checks": transformed_verify_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct,
        "failures": g8_failures,
        "invariant": "typed incidence-graph WL refinement; incomplete for isomorphism",
    }

    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
