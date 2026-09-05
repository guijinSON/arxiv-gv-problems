"""Rejected equitable total-colouring prototype for arXiv:2503.20055.

The paper's Definitions 1 and 8 define total and equitable total colourings.
Section 1 records that deciding whether a bipartite cubic graph has an
equitable four-total-colouring is NP-complete.  This module inverse-generates
such colourings: it samples balanced vertex colour classes, builds four
edge-colour matchings around them, forgets all hidden colours, and retains the
colour word as a witness.

Generation is deterministic in ``(n, seed, params)``, uses only the standard
library, performs no file I/O, and prints nothing at import time.
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
from collections import Counter, deque
from typing import Any


TRACK = "A"

_PAPER_CITATION = (
    "Section 1, Definitions 1 and 8; the same section cites the NP-completeness "
    "of deciding equitable four-total-colourability for bipartite cubic graphs"
)

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "connected simple bipartite cubic graph",
        "equitable total four-colouring word",
    ],
    "verification_operations": [
        "exact integer colour comparison on adjacent vertices",
        "exact integer colour comparison on incident vertex-edge pairs",
        "exact integer colour comparison on adjacent edges",
        "integer colour-class cardinality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Use each vertex together with its three incident edges as an all-four-"
        "colours constraint; without sustained propagation across overlapping "
        "constraints one must backtrack through the hidden balanced colouring."
    ),
    "hardness_basis": (
        "Track A: Section 1 states NP-completeness for equitable four-total-"
        "colouring of bipartite cubic graphs; shipping uses 102 vertices with "
        "four hidden vertex classes of sizes 24/26 and colour-safe switching, "
        "where the measured equitable DSATUR/DPLL baseline exhausts its stated "
        "node budget and wall-clock cost in G5 on the generated distribution."
    ),
    "max_answer_tokens": 257,
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
    "demo": {"n": 8, "switch_rounds": 0},
    "easy": {"n": 54, "switch_rounds": 2},
    "medium": {"n": 78, "switch_rounds": 4},
    "hard": {"n": 102, "switch_rounds": 8},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "At every vertex, that vertex and its three incident edges use all four "
    "colours exactly once."
)
PLACEBO_HINT = (
    "At every stage, the vertex numbers and displayed edge indices should be "
    "tracked with consistent care."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One word of 5n/2 symbols from {1,2,3,4}, with equitable symbol counts; "
        "the V0 symbol is 1 and its three incident-edge symbols, in increasing "
        "other-endpoint order, are 2,3,4."
    ),
    "bounds": {
        "alphabet_size": 4,
        "word_length": "5n/2",
        "max_supported_n": 400,
        "fixed_global_symmetry_symbols": 4,
        "colour_count_difference": 1,
    },
}

NOTES = r"""
Step 0 and exact paper grounding.  Definition 1 in Section 1 says that a total
colouring assigns colours to both vertices and edges, with distinct colours on
adjacent or incident elements.  Definition 8 says equitable means that every
two colour-class cardinalities differ by at most one.  The introduction states
that deciding whether a cubic graph has four total colours is NP-hard even when
the graph is bipartite, and that the result persists for equitable total
colourings.  The cited Dantas et al. result is the sharper NP-completeness
statement for equitable four-total-colouring of bipartite cubic graphs.

What produces the certificate.  The answer is sampled before the public graph.
Each side of a hidden bipartition receives the same four near-equal vertex-
colour class sizes.  For edge colour j, a perfect matching joins all vertices
whose vertex colour is not j, always across the bipartition and never between
equal vertex colours.  Thus every vertex is incident with the three colours
other than its own.  Colour-safe endpoint switches mix each matching.  The
hidden colours are then forgotten and vertices and edges are independently
relabelled.  The generator never colours the graph it emits.

What makes cases easy.  The paper's Theorem 1 is a direct Kempe-style swap once
a maximal colour-alternating path is supplied; it is not used as a Track A
hardness claim.  Theorem 2 lifts a colouring through a supplied covering map,
and Theorem 3 gives explicit efficient total colourings of Q3 and the prisms
C_(4j) square K2.  The explicit symmetric graphs and supplied alternating
paths in Sections 2--4 are therefore avoided.  General five-total-colourability
of subcubic graphs is also not the question here: the palette is fixed at four.

Distributional caution.  Worst-case NP-completeness alone says nothing about
this planted distribution.  The module therefore includes construction-aware
spectral clustering, per-element statistics, balanced greedy colouring,
balanced min-conflicts, and exact equitable DSATUR/DPLL.  The hidden classes
have unequal sizes at every non-demo preset, avoiding the exact equitable-
partition eigenspace created by four equal classes.  Plants and decoys are not
separate populations: every public edge comes from the same switched matching
process.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_NODE_CAP = 2_000_000
_DPLL_PANEL_BUDGET = 1_000_000
_DPLL_BASELINE_BUDGET = 1_000_000
_ATTACK_SEEDS = tuple(range(3100, 3108))
_G4_SAMPLES = 200_000

# Replaced only after script-owned hardening runs.  A zero-attempt state is not
# hardness evidence and deliberately keeps G9 failing until those runs exist.
_ORACLE_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


def _validate_params(n: int, switch_rounds: int) -> None:
    if (isinstance(n, bool) or not isinstance(n, int) or n < 8
            or n % 2 or n > 400):
        raise ValueError("n must be an even integer in 8..400")
    if (isinstance(switch_rounds, bool) or not isinstance(switch_rounds, int)
            or not 0 <= switch_rounds <= 64):
        raise ValueError("switch_rounds must be an integer in 0..64")


def _balanced_side_sizes(side_size: int, rng: random.Random) -> list[int]:
    """Near-equal positive sizes, randomly assigned to the four colours."""
    q, r = divmod(side_size, 4)
    if q == 0:
        raise ValueError("each bipartition side must contain at least 4 vertices")
    sizes = [q + (i < r) for i in range(4)]
    rng.shuffle(sizes)
    return sizes


def _canon_edge(u: int, v: int) -> tuple[int, int]:
    return (u, v) if u < v else (v, u)


def _sample_colour_matching(
    edge_colour: int,
    left_classes: list[list[int]],
    right_classes: list[list[int]],
    forbidden: set[tuple[int, int]],
    rng: random.Random,
) -> list[tuple[int, int, int]]:
    """Sample one colour layer, retrying only its multiset derangement."""
    colours = [c for c in range(4) if c != edge_colour]
    base_left = [(c, vertex) for c in colours for vertex in left_classes[c]]
    for _attempt in range(20_000):
        left = base_left[:]
        rng.shuffle(left)
        pools = {c: right_classes[c][:] for c in colours}
        for pool in pools.values():
            rng.shuffle(pool)
        layer: list[tuple[int, int, int]] = []
        possible = True
        for left_colour, u in left:
            eligible = []
            for right_colour in colours:
                if right_colour == left_colour or not pools[right_colour]:
                    continue
                v = pools[right_colour][-1]
                if _canon_edge(u, v) not in forbidden:
                    eligible.append(right_colour)
            if not eligible:
                possible = False
                break
            # Preserve future Hall slack by consuming a largest eligible pool.
            largest = max(len(pools[c]) for c in eligible)
            choices = [c for c in eligible if len(pools[c]) == largest]
            right_colour = rng.choice(choices)
            v = pools[right_colour].pop()
            layer.append((u, v, edge_colour))
        if possible:
            return layer
    raise RuntimeError("could not sample a simple colour matching")


def _connected(n: int, edges: list[tuple[int, int, int]]) -> bool:
    adjacency = [[] for _ in range(n)]
    for u, v, _colour in edges:
        adjacency[u].append(v)
        adjacency[v].append(u)
    seen = {0}
    stack = [0]
    while stack:
        u = stack.pop()
        for v in adjacency[u]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return len(seen) == n


def _switch_layers(
    edges: list[tuple[int, int, int]],
    vertex_colours: list[int],
    side_size: int,
    switch_rounds: int,
    rng: random.Random,
) -> None:
    """Mix a known colouring by colour-safe bipartite 2-switches."""
    by_colour = {
        colour: [i for i, edge in enumerate(edges) if edge[2] == colour]
        for colour in range(4)
    }
    occupied = {_canon_edge(u, v) for u, v, _colour in edges}
    target = switch_rounds * len(edges)
    made = 0
    attempts = 0
    while made < target and attempts < max(10_000, 200 * target):
        attempts += 1
        colour = rng.randrange(4)
        if len(by_colour[colour]) < 2:
            continue
        i, j = rng.sample(by_colour[colour], 2)
        u, v, _ = edges[i]
        x, y, _ = edges[j]
        # Stored construction endpoints are left then right before relabelling.
        if not (u < side_size <= v and x < side_size <= y):
            raise AssertionError("switch layer lost its bipartition orientation")
        if len({u, v, x, y}) < 4:
            continue
        new1 = _canon_edge(u, y)
        new2 = _canon_edge(x, v)
        old1 = _canon_edge(u, v)
        old2 = _canon_edge(x, y)
        if new1 in occupied or new2 in occupied:
            continue
        if vertex_colours[u] in (colour, vertex_colours[y]):
            continue
        if vertex_colours[x] in (colour, vertex_colours[v]):
            continue
        occupied.remove(old1)
        occupied.remove(old2)
        occupied.add(new1)
        occupied.add(new2)
        edges[i] = (u, y, colour)
        edges[j] = (x, v, colour)
        made += 1
    if made < target:
        raise RuntimeError("could not complete requested colour-safe switches")


def _normalize_colours(
    n: int, edges: list[list[int]], vertex_colours: list[int], edge_colours: list[int]
) -> str:
    """Fix the four global colour names using V0 and its incident edges."""
    incident = []
    for index, (u, v) in enumerate(edges):
        if u == 0 or v == 0:
            other = v if u == 0 else u
            incident.append((other, index))
    if len(incident) != 3:
        raise AssertionError("V0 is not cubic")
    incident.sort()
    old_order = [vertex_colours[0]] + [edge_colours[i] for _v, i in incident]
    if sorted(old_order) != [0, 1, 2, 3]:
        raise AssertionError("anchor clique does not use all four colours")
    rename = {old: str(new + 1) for new, old in enumerate(old_order)}
    return "".join(rename[c] for c in vertex_colours + edge_colours)


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Inverse-generate a promised equitable four-total-colouring."""
    switch_rounds = params.pop("switch_rounds", 0)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    _validate_params(n, switch_rounds)
    rng = random.Random(seed)
    side_size = n // 2
    side_colour_sizes = _balanced_side_sizes(side_size, rng)

    vertex_colours: list[int] = []
    left_classes: list[list[int]] = []
    right_classes: list[list[int]] = []
    next_vertex = 0
    for side in range(2):
        classes = []
        for colour, size in enumerate(side_colour_sizes):
            row = list(range(next_vertex, next_vertex + size))
            next_vertex += size
            classes.append(row)
            vertex_colours.extend([colour] * size)
        if side == 0:
            left_classes = classes
        else:
            right_classes = classes

    for _graph_attempt in range(2_000):
        hidden_edges: list[tuple[int, int, int]] = []
        occupied: set[tuple[int, int]] = set()
        try:
            for edge_colour in range(4):
                layer = _sample_colour_matching(
                    edge_colour, left_classes, right_classes, occupied, rng
                )
                hidden_edges.extend(layer)
                occupied.update(_canon_edge(u, v) for u, v, _ in layer)
        except RuntimeError:
            continue
        if _connected(n, hidden_edges):
            break
    else:
        raise RuntimeError("could not generate a connected simple cubic graph")

    _switch_layers(
        hidden_edges, vertex_colours, side_size, switch_rounds, rng
    )
    if not _connected(n, hidden_edges):
        raise AssertionError("a colour-safe switch disconnected the graph")

    permutation = list(range(n))
    rng.shuffle(permutation)
    public_vertex_colours = [0] * n
    for old, new in enumerate(permutation):
        public_vertex_colours[new] = vertex_colours[old]
    public_records = []
    for u, v, colour in hidden_edges:
        a, b = permutation[u], permutation[v]
        public_records.append(([a, b], colour))
    rng.shuffle(public_records)
    public_edges = [row for row, _colour in public_records]
    public_edge_colours = [colour for _row, colour in public_records]
    answer = _normalize_colours(
        n, public_edges, public_vertex_colours, public_edge_colours
    )

    return {
        "family": "equitable four-total-colouring of a bipartite cubic graph",
        "n": n,
        "m": len(public_edges),
        "colours": 4,
        "switch_rounds": switch_rounds,
        "edges": public_edges,
        "answer": answer,
    }


def _anchor_positions(inst: dict) -> list[int]:
    n = inst["n"]
    incident = []
    for index, row in enumerate(inst["edges"]):
        if not isinstance(row, list) or len(row) != 2:
            continue
        u, v = row
        if u == 0 or v == 0:
            incident.append((v if u == 0 else u, n + index))
    incident.sort()
    return [0] + [position for _other, position in incident]


def render(inst: dict) -> str:
    """Render a self-contained exact witness problem."""
    n = inst["n"]
    m = inst["m"]
    rows = "\n".join(
        f"E{i}: V{u} V{v}" for i, (u, v) in enumerate(inst["edges"])
    )
    anchors = _anchor_positions(inst)
    other_endpoints = []
    for position in anchors[1:]:
        u, v = inst["edges"][position - n]
        other_endpoints.append(v if u == 0 else u)
    statement = f"""Equitable four-total-colouring

The graph below is a connected simple bipartite cubic graph: it has vertices
V0,...,V{n - 1}; every vertex has exactly three incident edges; and its {m}
undirected edges are E0,...,E{m - 1}.  An edge's two endpoint orders are
interchangeable.

A total colouring assigns one of the symbols 1,2,3,4 to every vertex and every
edge.  It is valid exactly when all three conditions hold:
1. adjacent vertices have different symbols;
2. an edge differs from both of its endpoint vertices; and
3. any two edges sharing an endpoint have different symbols.

It is equitable when the four symbol counts over vertices and edges together
differ pairwise by at most one.  Find any equitable valid total colouring.

Edges:
{rows}

Encode the colouring as one word of exactly {n + m} symbols.  Positions
0 through {n - 1} colour V0 through V{n - 1}; positions {n} through
{n + m - 1} colour E0 through E{m - 1}.  No separators are allowed.  To fix
irrelevant global colour names, position 0 must be 1.  V0's incident edges,
ordered by increasing other endpoint V{other_endpoints[0]}, V{other_endpoints[1]},
V{other_endpoints[2]}, must have symbols 2, 3, 4 respectively.

Give your final answer inside <answer></answer> tags, as that exact colour word.
Syntax-only example (not instance data): <answer>123414322341</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the last tagged colour word, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    for body in reversed(_ANSWER_RE.findall(text)):
        body = body.strip()
        if body.startswith("```") and body.endswith("```"):
            lines = body.splitlines()
            if len(lines) >= 3:
                body = "\n".join(lines[1:-1]).strip()
        if len(body) >= 2 and body[0] == body[-1] == '"':
            try:
                body = json.loads(body)
            except (TypeError, ValueError):
                continue
        if isinstance(body, str) and body and all(c in "1234" for c in body):
            return body
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any normalized equitable total colouring; never read the plant."""
    if not isinstance(answer, str):
        return False, "answer must be one colour word"
    if not answer:
        return False, "colour word must not be empty"
    n = inst.get("n")
    edges = inst.get("edges")
    if (isinstance(n, bool) or not isinstance(n, int) or n < 1
            or not isinstance(edges, list)):
        return False, "malformed instance"
    expected = n + len(edges)
    if len(answer) != expected:
        return False, (
            f"colour word has {len(answer)} symbols; exactly {expected} are required"
        )
    if any(c not in "1234" for c in answer):
        return False, "every symbol must be one of 1, 2, 3, or 4"
    anchors = _anchor_positions(inst)
    if len(anchors) != 4:
        return False, "malformed V0 incidence list"
    for expected_symbol, position in zip("1234", anchors):
        if answer[position] != expected_symbol:
            return False, (
                f"normalization position {position} must be {expected_symbol}"
            )
    counts = Counter(answer)
    if max(counts.values()) - min(counts.values()) > 1:
        return False, "the four colour-class sizes are not equitable"

    seen: set[tuple[int, int]] = set()
    incident: list[list[int]] = [[] for _ in range(n)]
    for index, row in enumerate(edges):
        if (not isinstance(row, list) or len(row) != 2
                or any(isinstance(v, bool) or not isinstance(v, int) for v in row)):
            return False, f"malformed edge E{index}"
        u, v = row
        if not (0 <= u < n and 0 <= v < n) or u == v:
            return False, f"malformed endpoints at E{index}"
        edge = _canon_edge(u, v)
        if edge in seen:
            return False, f"duplicate public edge at E{index}"
        seen.add(edge)
        edge_symbol = answer[n + index]
        if answer[u] == answer[v]:
            return False, f"adjacent vertices V{u} and V{v} share a colour"
        if edge_symbol == answer[u] or edge_symbol == answer[v]:
            return False, f"edge E{index} shares a colour with an endpoint"
        incident[u].append(index)
        incident[v].append(index)
    for vertex, row in enumerate(incident):
        symbols = [answer[n + index] for index in row]
        if len(symbols) != 3:
            return False, f"malformed degree at V{vertex}"
        if len(set(symbols)) != 3:
            return False, f"two edges incident with V{vertex} share a colour"
    return True, "ok"


def _target_counts(total: int, high_colours: tuple[int, ...]) -> list[int]:
    q, _r = divmod(total, 4)
    high = set(high_colours)
    return [q + int(c in high) for c in range(4)]


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample normalized words with the required equitable counts."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    total = inst["n"] + len(inst["edges"])
    _q, r = divmod(total, 4)
    high = tuple(sorted(rng.sample(range(4), r)))
    counts = _target_counts(total, high)
    anchors = _anchor_positions(inst)
    word = [""] * total
    for colour, position in enumerate(anchors):
        word[position] = str(colour + 1)
        counts[colour] -= 1
    free_symbols = [str(colour + 1) for colour, count in enumerate(counts)
                    for _ in range(count)]
    rng.shuffle(free_symbols)
    iterator = iter(free_symbols)
    for position in range(total):
        if not word[position]:
            word[position] = next(iterator)
    return "".join(word)


def search_space(inst: dict) -> int | None:
    """Exact size of the structure-aware normalized equitable word language."""
    total = inst["n"] + len(inst["edges"])
    q, r = divmod(total, 4)
    remaining = [q] * r + [q - 1] * (4 - r)
    numerator = math.factorial(total - 4) * math.comb(4, r)
    denominator = math.prod(math.factorial(value) for value in remaining)
    return numerator // denominator


def _total_adjacency(inst: dict) -> list[set[int]]:
    n = inst["n"]
    edges = inst["edges"]
    adjacency = [set() for _ in range(n + len(edges))]
    incident = [[] for _ in range(n)]
    for index, (u, v) in enumerate(edges):
        e = n + index
        adjacency[u].add(v)
        adjacency[v].add(u)
        adjacency[u].add(e)
        adjacency[e].add(u)
        adjacency[v].add(e)
        adjacency[e].add(v)
        incident[u].append(e)
        incident[v].append(e)
    for row in incident:
        for i, u in enumerate(row):
            for v in row[:i]:
                adjacency[u].add(v)
                adjacency[v].add(u)
    return adjacency


def _equitable_dpll(
    inst: dict, node_budget: int | None, count_all: bool = False
) -> tuple[str | int | None, int]:
    """Exact balanced DSATUR with capacity pruning and optional counting."""
    adjacency = _total_adjacency(inst)
    total = len(adjacency)
    anchors = _anchor_positions(inst)
    colours = [-1] * total
    masks = [0] * total
    used = [0] * 4
    for colour, vertex in enumerate(anchors):
        colours[vertex] = colour
        used[colour] += 1
    for vertex in anchors:
        bit = 1 << colours[vertex]
        for neighbor in adjacency[vertex]:
            if colours[neighbor] < 0:
                masks[neighbor] |= bit
    low, rem = divmod(total, 4)
    high = low + bool(rem)
    nodes = 0
    solutions = 0
    found: list[int] | None = None

    def capacities_possible(left: int) -> bool:
        if any(value > high for value in used):
            return False
        deficits = sum(max(0, low - value) for value in used)
        return deficits <= left

    def search(left: int) -> bool:
        nonlocal nodes, solutions, found
        nodes += 1
        if node_budget is not None and nodes > node_budget:
            return True
        if left == 0:
            if max(used) - min(used) <= 1:
                solutions += 1
                if not count_all:
                    found = colours[:]
                    return True
            return False
        vertex = max(
            (u for u in range(total) if colours[u] < 0),
            key=lambda u: (masks[u].bit_count(), len(adjacency[u]), -used[0], -u),
        )
        available = (~masks[vertex]) & 15
        order = sorted(range(4), key=lambda c: (used[c], c))
        for colour in order:
            bit = 1 << colour
            if not available & bit or used[colour] >= high:
                continue
            colours[vertex] = colour
            used[colour] += 1
            changed: list[tuple[int, int]] = []
            impossible = False
            for neighbor in adjacency[vertex]:
                if colours[neighbor] < 0:
                    old = masks[neighbor]
                    new = old | bit
                    if new != old:
                        masks[neighbor] = new
                        changed.append((neighbor, old))
                        if new == 15:
                            impossible = True
            stop = False
            if not impossible and capacities_possible(left - 1):
                stop = search(left - 1)
            for neighbor, old in changed:
                masks[neighbor] = old
            used[colour] -= 1
            colours[vertex] = -1
            if stop and (found is not None or
                         (node_budget is not None and nodes > node_budget)):
                return True
        return False

    search(total - 4)
    if count_all:
        if node_budget is not None and nodes > node_budget:
            return None, nodes
        return solutions, nodes
    if found is None:
        return None, nodes
    word = "".join(str(c + 1) for c in found)
    return word, nodes


def enumerate_all(inst: dict) -> int | None:
    """Exactly count normalized valid witnesses when bounded DPLL finishes."""
    count, _nodes = _equitable_dpll(
        inst, _ENUMERATION_NODE_CAP, count_all=True
    )
    return count if isinstance(count, int) else None


def _graph_adjacency(inst: dict) -> list[set[int]]:
    adjacency = [set() for _ in range(inst["n"])]
    for u, v in inst["edges"]:
        adjacency[u].add(v)
        adjacency[v].add(u)
    return adjacency


def _structural_signature(inst: dict) -> list[Any]:
    """Strong exact isomorphism invariant for generated cubic graphs."""
    adjacency = _graph_adjacency(inst)
    n = len(adjacency)
    vertex_rows = []
    for start in range(n):
        distances = [-1] * n
        distances[start] = 0
        queue = deque([start])
        while queue:
            u = queue.popleft()
            for v in adjacency[u]:
                if distances[v] < 0:
                    distances[v] = distances[u] + 1
                    queue.append(v)
        distance_hist = tuple(sorted(Counter(distances).items()))
        closed = []
        vector = {start: 1}
        for length in range(1, 9):
            nxt: dict[int, int] = {}
            for u, value in vector.items():
                for v in adjacency[u]:
                    nxt[v] = nxt.get(v, 0) + value
            vector = nxt
            if length >= 3:
                closed.append(vector.get(start, 0))
        common = sorted(
            Counter(len(adjacency[start] & adjacency[v])
                    for v in range(n) if v != start).items()
        )
        vertex_rows.append((distance_hist, tuple(closed), tuple(common)))
    return [n, len(inst["edges"]), sorted(vertex_rows)]


def canonical_key(inst: dict) -> str:
    """Hash graph invariants only, ignoring labels, edge order, and the plant."""
    payload = json.dumps(_structural_signature(inst), separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Increase colour-safe mixing at fixed witness length before the cap."""
    if not isinstance(params, dict):
        return None
    n = params.get("n")
    rounds = params.get("switch_rounds", 0)
    if (isinstance(n, bool) or not isinstance(n, int)
            or isinstance(rounds, bool) or not isinstance(rounds, int)):
        return None
    if rounds < 64:
        out = dict(params)
        out["switch_rounds"] = min(64, rounds + 8)
        return out
    return "cap_bound"


def _transform_instance(
    inst: dict,
    vertex_permutation: list[int],
    edge_order: list[int] | None = None,
    reverse_alternate: bool = False,
) -> dict:
    """Carry a witness through vertex relabelling and edge reordering."""
    n = inst["n"]
    m = len(inst["edges"])
    if sorted(vertex_permutation) != list(range(n)):
        raise ValueError("vertex_permutation is not a permutation")
    if edge_order is None:
        edge_order = list(range(m))
    if sorted(edge_order) != list(range(m)):
        raise ValueError("edge_order is not a permutation")
    old_word = inst["answer"]
    old_vertex = [int(c) - 1 for c in old_word[:n]]
    old_edge = [int(c) - 1 for c in old_word[n:]]
    new_vertex = [0] * n
    for old, new in enumerate(vertex_permutation):
        new_vertex[new] = old_vertex[old]
    new_edges = []
    new_edge_colours = []
    for new_index, old_index in enumerate(edge_order):
        u, v = inst["edges"][old_index]
        row = [vertex_permutation[u], vertex_permutation[v]]
        if reverse_alternate and new_index % 2:
            row.reverse()
        new_edges.append(row)
        new_edge_colours.append(old_edge[old_index])
    answer = _normalize_colours(n, new_edges, new_vertex, new_edge_colours)
    return {
        "family": inst["family"],
        "n": n,
        "m": m,
        "colours": 4,
        "switch_rounds": inst["switch_rounds"],
        "edges": new_edges,
        "answer": answer,
    }


def _canonicalize_candidate(inst: dict, colours: list[int]) -> str:
    anchors = _anchor_positions(inst)
    old_order = [colours[position] for position in anchors]
    if sorted(old_order) == [0, 1, 2, 3]:
        rename = {old: new for new, old in enumerate(old_order)}
        colours = [rename[c] for c in colours]
    return "".join(str(c + 1) for c in colours)


def _rank_statistic_attack(inst: dict) -> str:
    """Per-element local-statistic ranking followed by balanced colour blocks."""
    adjacency = _total_adjacency(inst)
    total = len(adjacency)
    triangles = [
        sum(v in adjacency[w] for i, v in enumerate(sorted(adjacency[u]))
            for w in sorted(adjacency[u])[i + 1:])
        for u in range(total)
    ]
    order = sorted(
        range(total),
        key=lambda u: (u >= inst["n"], triangles[u],
                       sum(triangles[v] for v in adjacency[u]), u),
    )
    q, r = divmod(total, 4)
    counts = [q + (c < r) for c in range(4)]
    colours = [0] * total
    cursor = 0
    for colour, count in enumerate(counts):
        for u in order[cursor:cursor + count]:
            colours[u] = colour
        cursor += count
    return _canonicalize_candidate(inst, colours)


def _greedy_balanced_attack(inst: dict) -> str:
    """Capacity-aware DSATUR without backtracking."""
    adjacency = _total_adjacency(inst)
    total = len(adjacency)
    colours = [-1] * total
    masks = [0] * total
    used = [0] * 4
    anchors = _anchor_positions(inst)
    for colour, u in enumerate(anchors):
        colours[u] = colour
        used[colour] = 1
    for u in anchors:
        for v in adjacency[u]:
            if colours[v] < 0:
                masks[v] |= 1 << colours[u]
    high = (total + 3) // 4
    for _ in range(total - 4):
        u = max((v for v in range(total) if colours[v] < 0),
                key=lambda v: (masks[v].bit_count(), len(adjacency[v]), -v))
        available = [c for c in range(4)
                     if not masks[u] & (1 << c) and used[c] < high]
        if not available:
            available = [c for c in range(4) if used[c] < high] or [0]
        colour = min(available, key=lambda c: (used[c], c))
        colours[u] = colour
        used[colour] += 1
        for v in adjacency[u]:
            if colours[v] < 0:
                masks[v] |= 1 << colour
    return "".join(str(c + 1) for c in colours)


def _min_conflicts_attack(
    inst: dict, rng: random.Random, restarts: int = 8, steps: int = 20_000
) -> tuple[str, int]:
    """Balanced swap-based local repair, preserving all language constraints."""
    adjacency = _total_adjacency(inst)
    anchors = set(_anchor_positions(inst))
    movable = [u for u in range(len(adjacency)) if u not in anchors]
    operations = 0
    last = random_candidate(inst, rng)
    for _restart in range(restarts):
        word = random_candidate(inst, rng)
        colours = [int(c) - 1 for c in word]
        conflicts = [sum(colours[u] == colours[v] for v in adjacency[u])
                     for u in range(len(adjacency))]
        operations += sum(len(row) for row in adjacency)
        bad = {u for u in movable if conflicts[u]}
        for _step in range(steps):
            if not bad:
                candidate = "".join(str(c + 1) for c in colours)
                return candidate, operations
            u = rng.choice(tuple(bad))
            partners = [v for v in movable if colours[v] != colours[u]]
            if not partners:
                break
            sample = rng.sample(partners, min(24, len(partners)))
            old_local = conflicts[u]
            best_score = None
            best = []
            for v in sample:
                before = old_local + conflicts[v]
                after_u = sum(colours[v] == colours[w] for w in adjacency[u])
                after_v = sum(colours[u] == colours[w] for w in adjacency[v])
                score = after_u + after_v - before
                operations += len(adjacency[u]) + len(adjacency[v])
                if best_score is None or score < best_score:
                    best_score, best = score, [v]
                elif score == best_score:
                    best.append(v)
            v = rng.choice(best)
            old_u, old_v = colours[u], colours[v]
            if best_score is not None and best_score >= 0 and rng.randrange(20):
                continue
            touched = {u, v} | adjacency[u] | adjacency[v]
            colours[u], colours[v] = old_v, old_u
            for x in touched:
                conflicts[x] = sum(colours[x] == colours[y] for y in adjacency[x])
                operations += len(adjacency[x])
                if x in anchors:
                    continue
                if conflicts[x]:
                    bad.add(x)
                else:
                    bad.discard(x)
        last = "".join(str(c + 1) for c in colours)
    return last, operations


def _spectral_partition_attack(
    inst: dict, rng: random.Random, iterations: int = 100
) -> tuple[str, int]:
    """Four-vector orthogonal iteration and clustering on the total graph."""
    adjacency = _total_adjacency(inst)
    total = len(adjacency)
    vectors = [[rng.uniform(-1.0, 1.0) for _ in range(total)] for _ in range(4)]
    operations = 0

    def orthonormalize(rows: list[list[float]]) -> list[list[float]]:
        out = []
        for row in rows:
            mean = sum(row) / len(row)
            row = [x - mean for x in row]
            for previous in out:
                dot = sum(x * y for x, y in zip(row, previous))
                row = [x - dot * y for x, y in zip(row, previous)]
            norm = math.sqrt(sum(x * x for x in row)) or 1.0
            out.append([x / norm for x in row])
        return out

    vectors = orthonormalize(vectors)
    # Apply (6I-A), whose leading directions are low-adjacency eigenvectors.
    for _ in range(iterations):
        updated = []
        for vector in vectors:
            updated.append([
                6.0 * vector[u] - sum(vector[v] for v in adjacency[u])
                for u in range(total)
            ])
            operations += sum(len(row) + 1 for row in adjacency)
        vectors = orthonormalize(updated)
    points = [tuple(vector[u] for vector in vectors) for u in range(total)]
    centers = [points[min(range(total), key=lambda u: (points[u], u))]]
    while len(centers) < 4:
        u = max(range(total), key=lambda x: min(
            sum((points[x][j] - center[j]) ** 2 for j in range(4))
            for center in centers
        ))
        centers.append(points[u])
    labels = [0] * total
    for _ in range(30):
        labels = [min(range(4), key=lambda c: (
            sum((point[j] - centers[c][j]) ** 2 for j in range(4)), c
        )) for point in points]
        new_centers = []
        for colour in range(4):
            cluster = [points[u] for u in range(total) if labels[u] == colour]
            if cluster:
                new_centers.append(tuple(
                    sum(point[j] for point in cluster) / len(cluster)
                    for j in range(4)
                ))
            else:
                new_centers.append(centers[colour])
        if new_centers == centers:
            break
        centers = new_centers
    return _canonicalize_candidate(inst, labels), operations


def _answer_atoms(answer: object) -> int:
    if isinstance(answer, str):
        return len(answer)
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest() -> dict:
    """Run G1--G9 and return machine-readable measured evidence."""
    report: dict[str, Any] = {}

    checked = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 99):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            assert ok, (preset, seed, reason)
            assert json.loads(json.dumps(inst["answer"])) == inst["answer"]
            checked += 1
    report["G1_planted_verifies"] = {
        "pass": True,
        "instances": checked,
        "generation_route": "inverse generation by four switched matchings",
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **shipping)
    answer = inst["answer"]
    corruptions = {
        "empty": "",
        "drop_one": answer[:-1],
        "duplicate_one": answer + answer[-1],
        "swap_normalizers": answer[1] + answer[0] + answer[2:],
        "out_of_range": answer[:-1] + "5",
    }
    reasons = {}
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        assert not ok, (name, bad)
        reasons[name] = reason
    assert len(set(reasons.values())) == len(reasons), reasons
    report["G2_rejects_corruption"] = {"pass": True, "reasons": reasons}

    response = (
        "I propagated the incident constraints and checked the class sizes.\n"
        "```text\n<answer>" + answer + "</answer>\n```\n"
        "The word uses the stated vertex-then-edge order."
    )
    assert parse_answer(response) == answer
    assert parse_answer("no tagged answer") is None
    assert parse_answer("<answer>123x</answer>") is None
    report["G3_round_trip"] = {
        "pass": True,
        "answer_elements": len(answer),
        "json_native": True,
    }

    guess_inst = make_instance(seed=8675309, **shipping)
    guess_rng = random.Random(13579)
    guess_hits = sum(
        verify(guess_inst, random_candidate(guess_inst, guess_rng))[0]
        for _ in range(_G4_SAMPLES)
    )
    guess_probability = guess_hits / _G4_SAMPLES
    assert guess_probability < 1e-6, (guess_hits, _G4_SAMPLES)
    report["G4_guess_resistance"] = {
        "pass": True,
        "hits": guess_hits,
        "total": _G4_SAMPLES,
        "empirical_probability": guess_probability,
        "structure_aware_space": search_space(guess_inst),
        "prior": "uniform normalized words with exact equitable class sizes",
    }

    demo = make_instance(seed=31415, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    assert isinstance(demo_count, int) and demo_count >= 1, demo_count
    density_inst = make_instance(seed=112358, **shipping)
    density_rng = random.Random(24680)
    density_hits = sum(
        verify(density_inst, random_candidate(density_inst, density_rng))[0]
        for _ in range(_G4_SAMPLES)
    )
    baseline_inst = make_instance(seed=424242, **shipping)
    started = time.perf_counter()
    baseline_answer, baseline_nodes = _equitable_dpll(
        baseline_inst, _DPLL_BASELINE_BUDGET
    )
    baseline_seconds = time.perf_counter() - started
    baseline_solved = (
        isinstance(baseline_answer, str)
        and verify(baseline_inst, baseline_answer)[0]
    )
    assert not baseline_solved, (baseline_nodes, baseline_seconds)
    report["G5_density_and_baseline"] = {
        "pass": True,
        "shipping_density_hits": density_hits,
        "shipping_density_samples": _G4_SAMPLES,
        "shipping_density_estimate": density_hits / _G4_SAMPLES,
        "demo_exact_solution_count": demo_count,
        "demo_n": demo["n"],
        "baseline_wall_seconds": round(baseline_seconds, 6),
        "baseline_nodes": baseline_nodes,
        "baseline_node_budget": _DPLL_BASELINE_BUDGET,
        "baseline_solved": baseline_solved,
    }

    attack_names = [
        "per_element_local_statistic",
        "greedy_balanced_dsatur",
        "random_restart_balanced_min_conflicts",
        "construction_aware_low_spectrum",
        "exact_equitable_dsatur_dpll_1m",
    ]
    attacks = {name: {"successes": 0, "attempts": len(_ATTACK_SEEDS)}
               for name in attack_names}
    costs = {name: 0 for name in attack_names}
    for seed in _ATTACK_SEEDS:
        current = make_instance(seed=seed, **shipping)
        candidates: dict[str, str | None] = {}
        candidates[attack_names[0]] = _rank_statistic_attack(current)
        candidates[attack_names[1]] = _greedy_balanced_attack(current)
        candidate, operations = _min_conflicts_attack(
            current, random.Random(seed ^ 0xA5A5A5A5)
        )
        candidates[attack_names[2]] = candidate
        costs[attack_names[2]] += operations
        candidate, operations = _spectral_partition_attack(
            current, random.Random(seed ^ 0x5A5A5A5A)
        )
        candidates[attack_names[3]] = candidate
        costs[attack_names[3]] += operations
        candidate, nodes = _equitable_dpll(current, _DPLL_PANEL_BUDGET)
        candidates[attack_names[4]] = candidate if isinstance(candidate, str) else None
        costs[attack_names[4]] += nodes
        for name, candidate in candidates.items():
            if candidate is not None and verify(current, candidate)[0]:
                attacks[name]["successes"] += 1
    for name in attack_names:
        attacks[name]["operations_or_nodes"] = costs[name]
    all_failed = all(row["successes"] == 0 for row in attacks.values())
    assert all_failed, attacks
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attacks,
        "domain_standard_attack": "exact_equitable_dsatur_dpll_1m",
        "construction_aware_attack": "construction_aware_low_spectrum",
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=777, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    assert doubled_ok, doubled_reason
    escalated = escalate(shipping)
    assert isinstance(escalated, dict) and escalated != shipping
    report["G7_scales"] = {
        "pass": True,
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_edges": len(doubled["edges"]),
        "escalated_params": escalated,
    }

    invariant_trials = 0
    carried_trials = 0
    unrelated_keys = []
    for seed in range(20):
        small = make_instance(n=30, switch_rounds=2, seed=5000 + seed)
        key = canonical_key(small)
        unrelated_keys.append(key)
        rng = random.Random(9000 + seed)
        vertex_permutation = list(range(small["n"]))
        rng.shuffle(vertex_permutation)
        edge_order = list(range(len(small["edges"])))
        rng.shuffle(edge_order)
        transformed = _transform_instance(
            small, vertex_permutation, edge_order, reverse_alternate=True
        )
        assert canonical_key(transformed) == key
        invariant_trials += 1
        ok, reason = verify(transformed, transformed["answer"])
        assert ok, reason
        carried_trials += 1
        second_permutation = list(range(small["n"]))
        rng.shuffle(second_permutation)
        composed = _transform_instance(transformed, second_permutation)
        assert canonical_key(composed) == key
        invariant_trials += 1
        ok, reason = verify(composed, composed["answer"])
        assert ok, reason
        carried_trials += 1
    distinct = len(set(unrelated_keys))
    assert distinct == len(unrelated_keys), unrelated_keys
    report["G8_canonical_key"] = {
        "pass": True,
        "invariant_relabelings": invariant_trials,
        "valid_carried_witnesses": carried_trials,
        "distinct_unrelated": distinct,
        "unrelated_attempts": len(unrelated_keys),
        "key_kind": "distance/closed-walk/common-neighbor graph invariant",
    }

    answer_chars = len(json.dumps(inst["answer"]))
    answer_elements = _answer_atoms(inst["answer"])
    answer_tokens = answer_elements + 2
    intended_operations = answer_elements
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    arms = {key: dict(_ORACLE_EVIDENCE[key])
            for key in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    hinted_hardened = _ORACLE_EVIDENCE["hinted_verdict"] == "hardened"
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _ORACLE_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
