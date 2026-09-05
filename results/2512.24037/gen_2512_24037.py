"""Verified generator for a symmetry-hidden Kidney Exchange cycle cover.

The object is exactly Definition 1 of arXiv:2512.24037: a loopless directed
compatibility graph. There are no altruists, paths are disabled, the cycle
bound is three, and the target is every vertex.

Instances are inverse-generated. A fixed-point-free order-three permutation is
sampled first; its orbits are the certificate. Every noise arc is added as a
full orbit of the same permutation, and regular permutation layers make all
vertices have identical in- and out-degree. The certificate is known before
any attack is run. Only the Python standard library is used.
"""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
import hashlib
import json
import math
import os
import random
import re
import time
from typing import Any


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "A fixed modular offset between each consecutive pair of numbered blocks "
    "defines an order-three symmetry of the compatibility arcs."
)
PLACEBO_HINT: str = (
    "Careful bookkeeping within each consecutive numbered block helps avoid "
    "mistakes while reading the directed compatibility arcs."
)

# Filled with the measured external-harness results after all three arms run.
G9_ARM_RESULTS: dict[str, dict[str, int]] = {
    "bare": {"solved": 2, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": ["directed kidney-compatibility graph", "directed 3-cycles"],
    "verification_operations": [
        "integer range and disjointness checks",
        "exact directed-edge membership",
        "full vertex-coverage comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "The desired cycles are the orbits of a hidden order-three modular "
        "block shift; without recognizing it, the legal cycles form a large "
        "exact-cover search."
    ),
    "hardness_basis": (
        "Track B: the distribution-specific offset decoder is O(|A|+n) after "
        "tallying inter-block displacements (about 4,000 integer/index "
        "operations and under 0.02 s at the shipping preset), whereas the "
        "compact symmetry route uses under 300 modular operations; the generic "
        "class remains the length-3 perfect-cycle-cover problem proved "
        "NP-complete by Abraham--Blum--Sandholm Theorem 1 and cited in Section 1.2."
    ),
    "max_answer_tokens": 225,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "Canonical JSON partitions of vertices 0,...,3*n-1 into exactly n "
        "unlabelled triples: each triple has three distinct increasing "
        "integers, triples are lexicographically sorted, and every vertex "
        "occurs exactly once."
    ),
    "bounds": {
        "n_triples": "n",
        "triple_size": 3,
        "vertex_min": 0,
        "vertex_max": "3*n - 1",
        "vertex_count": "3*n",
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 3, "degree": 1, "screen_nodes": 0},
    "easy": {"n": 72, "degree": 12, "screen_nodes": 50_000},
    "medium": {"n": 76, "degree": 12, "screen_nodes": 100_000},
    "hard": {"n": 81, "degree": 12, "screen_nodes": 200_000},
}
SHIPPING_DIFFICULTY = "easy"

NOTES = r"""
STEP 0 paper audit. Section 2, Definition 1 fixes the native object and all
conventions: the graph is directed and loopless; path and cycle lengths count
edges; altruists are not patients; and t counts covered non-altruistic
vertices. This family uses B=empty, lp=0, lc=3, and t=|V|.

The easy result is Theorem 1 in Section 3: color coding plus subset DP decides
Kidney Exchange in deterministic O*((4e)^t) time. Accordingly t=3n grows with
the instance. Section 1.1 also records FPT for combined treewidth and length;
these regular random lifts do not hold structural width fixed. Section 1.2
cites Abraham--Blum--Sandholm Theorem 1, which proves that perfect directed
cycle cover with maximum length L>=3 is NP-complete. A bound of two would be
matching.

The paper's new Section 6 claim is not used. Its construction sets t=|V| even
though Definition 1 excludes altruists from t, repeatedly equates path length
with vertex count despite the edge-count convention, and derives B'=31B before
calling B' constant. Relying on that claim would be unsafe.

Generation route. Choose offsets r0,r1 first. They define sigma on three blocks
by (0,i)->(1,i+r0), (1,i)->(2,i+r1), and
(2,i)->(0,i-r0-r1), modulo n. Sigma has order three and no fixed vertex, so its
n orbits are directed triangles and are the answer. Noise arcs are added only
in complete sigma-orbits through random regular permutation layers. Every
vertex has identical in/out degree. A bounded Algorithm-X screen discards only
the easy tail; it never supplies the certificate.

Track B honesty. An efficient decoder exists for this distribution: tally the
modular offsets of arcs from block 0 to 1 and block 1 to 2. The planted offsets
occur n times and reconstruct every orbit. The reference implementation reports
its O(|A|+n) time and operation count. The compact route intersects the few
outgoing offset sets of several vertices and advances each orbit twice. Generic
low-degree, lexicographic, randomized-greedy, zero-offset, and bounded
Algorithm-X attacks are all measured.
"""


def _canonical_answer(rows: Any) -> list[list[int]]:
    return sorted(sorted(int(v) for v in row) for row in rows)


def _sigma(v: int, n: int, r0: int, r1: int) -> int:
    """The hidden fixed-point-free order-three permutation."""
    block, i = divmod(v, n)
    if block == 0:
        return n + (i + r0) % n
    if block == 1:
        return 2 * n + (i + r1) % n
    return (i - r0 - r1) % n


def _legal_cycles_from_edges(
    vertex_count: int, edges: Any
) -> list[tuple[int, int, int]]:
    outgoing = [set() for _ in range(vertex_count)]
    for u, v in edges:
        outgoing[u].add(v)
    cycles: set[tuple[int, int, int]] = set()
    for a in range(vertex_count):
        for b in outgoing[a]:
            for c in outgoing[b]:
                if c != a and a in outgoing[c]:
                    cycles.add(tuple(sorted((a, b, c))))
    return sorted(cycles)


def _algorithm_x_edges(
    vertex_count: int, edges: Any, node_limit: int
) -> tuple[list[list[int]] | None, int, bool]:
    """Minimum-column Algorithm X with bitset row deletion.

    Returns (cover, visited_nodes, exhausted). A missing cover with exhausted
    false means that the explicit node budget was reached.
    """
    rows = _legal_cycles_from_edges(vertex_count, edges)
    by_vertex = [0] * vertex_count
    row_masks: list[int] = []
    for row_id, row in enumerate(rows):
        mask = 0
        for v in row:
            mask |= 1 << v
            by_vertex[v] |= 1 << row_id
        row_masks.append(mask)
    conflicts = []
    for row in rows:
        bad = 0
        for v in row:
            bad |= by_vertex[v]
        conflicts.append(bad)
    full = (1 << vertex_count) - 1
    nodes = 0
    cutoff = False

    def visit(covered: int, active: int) -> list[int] | None:
        nonlocal nodes, cutoff
        nodes += 1
        if nodes > node_limit:
            cutoff = True
            return None
        if covered == full:
            return []
        remaining = full ^ covered
        options: int | None = None
        while remaining:
            bit = remaining & -remaining
            remaining -= bit
            vertex = bit.bit_length() - 1
            available = by_vertex[vertex] & active
            if not available:
                return None
            if options is None or available.bit_count() < options.bit_count():
                options = available
        assert options is not None
        while options:
            bit = options & -options
            options -= bit
            row_id = bit.bit_length() - 1
            suffix = visit(
                covered | row_masks[row_id], active & ~conflicts[row_id]
            )
            if suffix is not None:
                return [row_id] + suffix
            if cutoff:
                return None
        return None

    picked = visit(0, (1 << len(rows)) - 1)
    if picked is None:
        return None, nodes, not cutoff
    return _canonical_answer(rows[row_id] for row_id in picked), nodes, True


def _sample_regular_lift(
    n: int, rng: random.Random, degree: int
) -> tuple[list[tuple[int, int]], list[list[int]], int, int, int]:
    r0 = rng.randrange(1, n)
    r1 = rng.randrange(1, n)
    while (r0 + r1) % n == 0:
        r0 = rng.randrange(1, n)
        r1 = rng.randrange(1, n)
    orbits = []
    for i in range(n):
        a = i
        b = _sigma(a, n, r0, r1)
        c = _sigma(b, n, r0, r1)
        if _sigma(c, n, r0, r1) != a:
            raise AssertionError("sigma does not have order three")
        orbits.append([a, b, c])
    rng.shuffle(orbits)
    edges: set[tuple[int, int]] = set()
    for orbit in orbits:
        edges.update((orbit[p], orbit[(p + 1) % 3]) for p in range(3))

    layers = 1
    tries = 0
    while layers < degree and tries < 250_000:
        tries += 1
        permutation = list(range(n))
        rng.shuffle(permutation)
        if any(permutation[i] == i for i in range(n)):
            continue
        phase = [rng.randrange(3) for _ in range(n)]
        proposed: list[tuple[int, int]] = []
        acceptable = True
        for i, j in enumerate(permutation):
            for p in range(3):
                arc = (orbits[i][p], orbits[j][(p + phase[i]) % 3])
                if arc in edges or (arc[1], arc[0]) in edges:
                    acceptable = False
                    break
                proposed.append(arc)
            if not acceptable:
                break
        if acceptable:
            edges.update(proposed)
            layers += 1
    if layers != degree:
        raise ValueError("could not realize the requested regular degree")
    return sorted(edges), _canonical_answer(orbits), r0, r1, tries


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Build a deterministic inverse-generated Kidney Exchange instance."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    degree = int(params.pop("degree", 12))
    screen_nodes = int(params.pop("screen_nodes", 0))
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if degree < 1 or degree >= n:
        raise ValueError("degree must satisfy 1 <= degree < n")
    if screen_nodes < 0:
        raise ValueError("screen_nodes must be nonnegative")
    rng = random.Random(seed)
    for build_round in range(48):
        try:
            edges, answer, _r0, _r1, lift_tries = _sample_regular_lift(
                n, rng, degree
            )
        except ValueError:
            continue
        found = None
        screen_visited = 0
        if screen_nodes:
            found, screen_visited, _ = _algorithm_x_edges(3 * n, edges, screen_nodes)
            if found is not None:
                continue
        inst = {
            "family": "order_three_kidney_cycle_cover",
            "n": n,
            "vertex_count": 3 * n,
            "edges": [list(edge) for edge in edges],
            "altruists": [],
            "path_limit": 0,
            "cycle_limit": 3,
            "target": 3 * n,
            "regular_degree": degree,
            "screen_nodes": screen_nodes,
            "screen_visited": screen_visited,
            "build_round": build_round,
            "lift_tries": lift_tries,
            "answer": answer,
        }
        if not verify(inst, answer)[0]:
            raise AssertionError("constructed orbit cover did not verify")
        decoded, _, _ = _reference_decode(inst)
        if decoded is None:
            continue
        return inst
    raise RuntimeError("could not sample an instance passing the bounded screen")


def render(inst: dict) -> str:
    vertex_count = inst["vertex_count"]
    n = inst["n"]
    outgoing = [[] for _ in range(vertex_count)]
    for u, v in inst["edges"]:
        outgoing[u].append(v)
    adjacency = "\n".join(
        f"{u}: " + (" ".join(map(str, sorted(outgoing[u]))) if outgoing[u] else "-")
        for u in range(vertex_count)
    )
    statement = f"""Kidney exchange -- perfect directed 3-cycle cover

There are {vertex_count} patient-donor pairs, numbered 0 through {vertex_count - 1},
and no altruistic donors. A directed arc u -> v means that u's donor is
compatible with v's patient. A directed cycle is a list of distinct vertices
whose consecutive arcs, including the last-to-first arc, all exist. Cycle
length is its number of arcs. Chains are disabled, and a legal exchange is a
directed cycle of at most 3 arcs.

The graph is loopless and oriented: it never contains both u -> v and v -> u.
Consequently it has no legal 1- or 2-cycles, so every legal exchange is a
directed 3-cycle. For a sorted triple [a,b,c], this means either a->b, b->c,
c->a all exist, or a->c, c->b, b->a all exist.

Find exactly {n} pairwise vertex-disjoint legal cycles covering all
{vertex_count} vertices. Thus every patient is served exactly once. Vertices
0..{n - 1}, {n}..{2 * n - 1}, and {2 * n}..{3 * n - 1} form three consecutive
numbered blocks; the blocks impose no additional feasibility rule. Vertex
numbering is 0-based. Within each triple, list distinct vertices in increasing
order. Sort the triples lexicographically. Repetitions are forbidden and order
otherwise has no meaning.

The adjacency list below gives every arc. A dash would mean no outgoing arcs;
no unlisted arc exists.

{adjacency}

Give your final answer inside <answer></answer> tags, as one JSON array
containing exactly {n} three-integer arrays in the canonical order specified
above.
Example format: <answer>[[0, 4, 8], [1, 5, 6]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    for raw in reversed(blocks):
        body = raw.strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, flags=re.I | re.S)
        if fenced:
            body = fenced.group(1).strip()
        try:
            value = json.loads(body)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(value, list) or not all(isinstance(row, list) for row in value):
            continue
        if not all(
            isinstance(v, int) and not isinstance(v, bool)
            for row in value
            for v in row
        ):
            continue
        return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any perfect legal cycle cover without reading inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    expected = inst["n"]
    if len(answer) != expected:
        return False, f"expected {expected} cycles, got {len(answer)}"
    vertex_count = inst["vertex_count"]
    edge_set = {tuple(edge) for edge in inst["edges"]}
    seen: set[int] = set()
    for index, row in enumerate(answer):
        if not isinstance(row, list):
            return False, f"cycle {index} is not a JSON array"
        if len(row) != 3:
            return False, f"cycle {index} has {len(row)} vertices; expected 3"
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in row):
            return False, f"cycle {index} contains a non-integer vertex"
        if len(set(row)) != 3:
            return False, f"cycle {index} repeats a vertex"
        for v in row:
            if not 0 <= v < vertex_count:
                return False, f"vertex {v} is outside 0..{vertex_count - 1}"
        overlap = seen.intersection(row)
        if overlap:
            return False, f"vertex {min(overlap)} appears in more than one cycle"
        seen.update(row)
        a, b, c = sorted(row)
        clockwise = {(a, b), (b, c), (c, a)}
        counterclockwise = {(a, c), (c, b), (b, a)}
        if not (clockwise <= edge_set or counterclockwise <= edge_set):
            return False, f"cycle {index} is not a directed 3-cycle"
    if len(seen) != vertex_count:
        missing = min(set(range(vertex_count)) - seen)
        return False, f"vertex {missing} is not covered"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    vertices = list(range(inst["vertex_count"]))
    rng.shuffle(vertices)
    return _canonical_answer(vertices[i : i + 3] for i in range(0, len(vertices), 3))


def search_space(inst: dict) -> int | None:
    n = inst["n"]
    return math.factorial(3 * n) // (math.factorial(3) ** n * math.factorial(n))


def enumerate_all(inst: dict) -> int | None:
    if search_space(inst) > 2_000_000:
        return None
    vertex_count = inst["vertex_count"]
    rows = _legal_cycles_from_edges(vertex_count, inst["edges"])
    by_vertex = [[] for _ in range(vertex_count)]
    masks = []
    for row_id, row in enumerate(rows):
        mask = sum(1 << v for v in row)
        masks.append(mask)
        for v in row:
            by_vertex[v].append(row_id)
    full = (1 << vertex_count) - 1
    calls = 0

    @lru_cache(maxsize=None)
    def count(covered: int) -> int:
        nonlocal calls
        calls += 1
        if calls > 2_000_000:
            raise OverflowError
        if covered == full:
            return 1
        bit = (full ^ covered) & -(full ^ covered)
        vertex = bit.bit_length() - 1
        return sum(
            count(covered | masks[row_id])
            for row_id in by_vertex[vertex]
            if not (masks[row_id] & covered)
        )

    try:
        return count(0)
    except OverflowError:
        return None


def _reference_decode(inst: dict) -> tuple[list[list[int]] | None, int, int]:
    """Recover the two repeated block offsets in O(|A|+n)."""
    n = inst["n"]
    counters = [Counter(), Counter(), Counter()]
    relevant = 0
    for u, v in inst["edges"]:
        source_block, source_index = divmod(u, n)
        target_block, target_index = divmod(v, n)
        if target_block == (source_block + 1) % 3:
            counters[source_block][(target_index - source_index) % n] += 1
            relevant += 1
    best = []
    ties = 0
    for counter in counters:
        if not counter:
            return None, 4 * relevant, ties
        peak = max(counter.values())
        winners = [offset for offset, count in counter.items() if count == peak]
        ties += len(winners)
        if len(winners) != 1:
            return None, 4 * relevant, ties
        best.append(winners[0])
    if sum(best) % n:
        return None, 4 * relevant, ties
    r0, r1, _ = best
    answer = _canonical_answer(
        [i, n + (i + r0) % n, 2 * n + (i + r0 + r1) % n]
        for i in range(n)
    )
    operations = 4 * relevant + 2 * n
    if not verify(inst, answer)[0]:
        return None, operations, ties
    return answer, operations, ties


def _compact_route_metrics(inst: dict) -> dict[str, int | bool]:
    n = inst["n"]
    outgoing = [[] for _ in range(3 * n)]
    for u, v in inst["edges"]:
        outgoing[u].append(v)
    operations = 0
    inspected = 0
    offsets = []
    for block in (0, 1):
        common: set[int] | None = None
        for index in range(n):
            candidates = {
                (v % n - index) % n
                for v in outgoing[block * n + index]
                if v // n == block + 1
            }
            operations += len(candidates)
            inspected += 1
            common = candidates if common is None else common.intersection(candidates)
            if len(common) == 1:
                break
        if common is None or len(common) != 1:
            return {"success": False, "operations": operations, "vertices_inspected": inspected}
        offsets.append(next(iter(common)))
    operations += 2 * n
    return {
        "success": True,
        "operations": operations,
        "vertices_inspected": inspected,
        "r0": offsets[0],
        "r1": offsets[1],
    }


def _wl_code(vertex_count: int, edges: list[tuple[int, int]]) -> str:
    """Relabelling-invariant refinement seeded by triangle support."""
    incoming = [set() for _ in range(vertex_count)]
    outgoing = [set() for _ in range(vertex_count)]
    for u, v in edges:
        outgoing[u].add(v)
        incoming[v].add(u)
    support = {(u, v): len(outgoing[v] & incoming[u]) for u, v in edges}
    cycles = _legal_cycles_from_edges(vertex_count, edges)
    cycle_count = [0] * vertex_count
    for row in cycles:
        for v in row:
            cycle_count[v] += 1
    signatures = [
        (
            len(incoming[v]),
            len(outgoing[v]),
            cycle_count[v],
            tuple(sorted(support[(v, w)] for w in outgoing[v])),
            tuple(sorted(support[(u, v)] for u in incoming[v])),
        )
        for v in range(vertex_count)
    ]
    palette = {signature: i for i, signature in enumerate(sorted(set(signatures)))}
    colors = [palette[signature] for signature in signatures]
    for _ in range(vertex_count):
        refined_signatures = [
            (
                colors[v],
                tuple(sorted(colors[u] for u in incoming[v])),
                tuple(sorted(colors[w] for w in outgoing[v])),
            )
            for v in range(vertex_count)
        ]
        palette = {
            signature: i for i, signature in enumerate(sorted(set(refined_signatures)))
        }
        refined = [palette[signature] for signature in refined_signatures]
        if refined == colors:
            break
        colors = refined
    colored_edges = sorted((colors[u], colors[v]) for u, v in edges)
    colored_cycles = sorted(tuple(sorted(colors[v] for v in row)) for row in cycles)
    return json.dumps(
        [vertex_count, sorted(Counter(colors).items()), colored_edges, colored_cycles],
        separators=(",", ":"),
    )


def canonical_key(inst: dict) -> str:
    vertex_count = inst["vertex_count"]
    edges = [tuple(edge) for edge in inst["edges"]]
    forward = _wl_code(vertex_count, edges)
    backward = _wl_code(vertex_count, [(v, u) for u, v in edges])
    structural = json.dumps(
        [inst["cycle_limit"], inst["path_limit"], inst["target"], min(forward, backward)],
        separators=(",", ":"),
    )
    return hashlib.sha256(structural.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    current = dict(params)
    degree = int(current.get("degree", 12))
    n = int(current.get("n", 81))
    if degree < 14:
        current["degree"] = degree + 1
        current["screen_nodes"] = max(200_000, 2 * int(current.get("screen_nodes", 0)))
        return current
    if n < 84:
        current["n"] = 84
        current["screen_nodes"] = max(800_000, int(current.get("screen_nodes", 0)))
        return current
    return "cap_bound"


def _outlier_attack(inst: dict) -> list[list[int]] | None:
    vertex_count = inst["vertex_count"]
    degree = [0] * vertex_count
    for u, v in inst["edges"]:
        degree[u] += 1
        degree[v] += 1
    rows = _legal_cycles_from_edges(vertex_count, inst["edges"])
    rows.sort(key=lambda row: (sum(degree[v] for v in row), row))
    used: set[int] = set()
    chosen = []
    for row in rows:
        if not used.intersection(row):
            chosen.append(row)
            used.update(row)
    return _canonical_answer(chosen) if len(used) == vertex_count else None


def _greedy_attack(inst: dict) -> list[list[int]] | None:
    vertex_count = inst["vertex_count"]
    rows = _legal_cycles_from_edges(vertex_count, inst["edges"])
    by_vertex = [[] for _ in range(vertex_count)]
    for row in rows:
        for v in row:
            by_vertex[v].append(row)
    uncovered = set(range(vertex_count))
    chosen = []
    while uncovered:
        vertex = min(uncovered)
        options = [row for row in by_vertex[vertex] if set(row) <= uncovered]
        if not options:
            return None
        row = min(options)
        chosen.append(row)
        uncovered.difference_update(row)
    return _canonical_answer(chosen)


def _random_restart_attack(inst: dict, restarts: int = 256) -> list[list[int]] | None:
    vertex_count = inst["vertex_count"]
    rows = _legal_cycles_from_edges(vertex_count, inst["edges"])
    by_vertex = [[] for _ in range(vertex_count)]
    for row in rows:
        for v in row:
            by_vertex[v].append(row)
    attack_seed = int(hashlib.sha256(json.dumps(inst["edges"]).encode()).hexdigest()[:16], 16)
    rng = random.Random(attack_seed)
    for _ in range(restarts):
        uncovered = set(range(vertex_count))
        chosen = []
        while uncovered:
            best_options = None
            for v in sorted(uncovered):
                options = [row for row in by_vertex[v] if set(row) <= uncovered]
                if not options:
                    best_options = []
                    break
                if best_options is None or len(options) < len(best_options):
                    best_options = options
            if not best_options:
                break
            row = rng.choice(best_options)
            chosen.append(row)
            uncovered.difference_update(row)
        if not uncovered:
            return _canonical_answer(chosen)
    return None


def _zero_offset_attack(inst: dict) -> list[list[int]]:
    n = inst["n"]
    return [[i, n + i, 2 * n + i] for i in range(n)]


def _relabel_instance(
    inst: dict, permutation: list[int], reverse_arcs: bool = False
) -> dict:
    transformed = dict(inst)
    if reverse_arcs:
        transformed["edges"] = [
            [permutation[v], permutation[u]] for u, v in reversed(inst["edges"])
        ]
    else:
        transformed["edges"] = [
            [permutation[u], permutation[v]] for u, v in reversed(inst["edges"])
        ]
    transformed["answer"] = _canonical_answer(
        [permutation[v] for v in row] for row in inst["answer"]
    )
    return transformed


def _answer_atoms(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest() -> dict:
    report: dict[str, Any] = {}
    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2, 3):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {"pass": not failures, "checks": checks, "failures": failures}

    inst = make_instance(seed=101, **DIFFICULTY[SHIPPING_DIFFICULTY])
    base = json.loads(json.dumps(inst["answer"]))
    corruptions: dict[str, Any] = {}
    dropped = json.loads(json.dumps(base)); dropped[0].pop(); corruptions["drop_one"] = dropped
    swapped = None
    for left in range(len(base)):
        for right in range(left + 1, len(base)):
            for i in range(3):
                for j in range(3):
                    trial = json.loads(json.dumps(base))
                    trial[left][i], trial[right][j] = trial[right][j], trial[left][i]
                    trial = _canonical_answer(trial)
                    ok, why = verify(inst, trial)
                    if not ok and "not a directed 3-cycle" in why:
                        swapped = trial; break
                if swapped is not None: break
            if swapped is not None: break
        if swapped is not None: break
    if swapped is None:
        raise AssertionError("could not create a rejected membership swap")
    corruptions["swap_one"] = swapped
    duplicated = json.loads(json.dumps(base)); duplicated[0][2] = duplicated[0][1]
    corruptions["duplicate"] = duplicated
    corruptions["empty"] = []
    outside = json.loads(json.dumps(base)); outside[-1][-1] = inst["vertex_count"]
    corruptions["out_of_range"] = outside
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    distinct_reasons = len({case["reason"] for case in cases.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values()) and distinct_reasons == 5,
        "cases": cases,
        "distinct_reasons": distinct_reasons,
    }

    payload = json.dumps(inst["answer"])
    response = f"I checked the arcs.\n```json\n<answer>\n{payload}\n</answer>\n```\nDone."
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and parse_answer("garbage") is None,
        "realistic_response_parsed": parsed == inst["answer"],
        "garbage_returns_none": parse_answer("garbage") is None,
        "json_native": json.loads(json.dumps(inst["answer"])) == inst["answer"],
    }

    guess_inst = make_instance(seed=2024, **DIFFICULTY[SHIPPING_DIFFICULTY])
    guess_rng = random.Random(0x251224037)
    total = 200_000
    hits = sum(
        verify(guess_inst, random_candidate(guess_inst, guess_rng))[0]
        for _ in range(total)
    )
    probability = hits / total
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": total,
        "measured_probability": probability,
        "prior": "uniform partition of all vertices into unlabelled triples",
        "candidate_space": search_space(guess_inst),
    }

    shipping_space = search_space(guess_inst)
    exact_count = enumerate_all(guess_inst)
    if exact_count is None:
        density_method = "uniform random_candidate sampling checked by verify"
        valid_answers, sample_size, density = hits, total, probability
    else:
        density_method = "exact enumerate_all count"
        valid_answers, sample_size = exact_count, shipping_space
        density = exact_count / shipping_space
    started = time.perf_counter()
    decoded, reference_operations, decoder_ties = _reference_decode(guess_inst)
    reference_seconds = time.perf_counter() - started
    reference_solved = decoded is not None and verify(guess_inst, decoded)[0]
    attack_limit = int(DIFFICULTY[SHIPPING_DIFFICULTY]["screen_nodes"])
    started = time.perf_counter()
    attack_answer, attack_nodes, attack_exhausted = _algorithm_x_edges(
        guess_inst["vertex_count"], guess_inst["edges"], attack_limit
    )
    attack_seconds = time.perf_counter() - started
    attack_solved = attack_answer is not None and verify(guess_inst, attack_answer)[0]
    report["G5_shipping_difficulty"] = {
        "pass": density < 1e-6 and reference_solved and not attack_solved,
        "shipping_preset": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
        "shipping_instance_seed": 2024,
        "valid_answers_sampled": valid_answers,
        "density_sample_size": sample_size,
        "observed_valid_fraction": density,
        "exact_solution_count": exact_count,
        "density_method": density_method,
        "candidate_space": shipping_space,
        "baseline_nodes": attack_nodes,
        "baseline_wall_seconds": attack_seconds,
        "baseline_solved": attack_solved,
        "baseline_search_exhausted": attack_exhausted,
        "reference_operations": reference_operations,
        "reference_wall_seconds": reference_seconds,
        "reference_solved": reference_solved,
        "decoder_peak_ties_total": decoder_ties,
    }

    names = (
        "outlier_low_degree",
        "greedy_left_to_right",
        "random_restart_256",
        "zero_offset_block_ansatz",
        f"algorithm_x_{attack_limit}",
    )
    outcomes = {name: {"successes": 0, "attempts": 8} for name in names}
    algorithm_nodes = []
    reference_successes = 0
    reference_ops = []
    reference_time = 0.0
    for seed in range(3000, 3008):
        attack_inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        guesses = {
            "outlier_low_degree": _outlier_attack(attack_inst),
            "greedy_left_to_right": _greedy_attack(attack_inst),
            "random_restart_256": _random_restart_attack(attack_inst, 256),
            "zero_offset_block_ansatz": _zero_offset_attack(attack_inst),
        }
        exact, nodes, _ = _algorithm_x_edges(
            attack_inst["vertex_count"], attack_inst["edges"], attack_limit
        )
        guesses[f"algorithm_x_{attack_limit}"] = exact
        algorithm_nodes.append(nodes)
        for name, candidate in guesses.items():
            if candidate is not None and verify(attack_inst, candidate)[0]:
                outcomes[name]["successes"] += 1
        started = time.perf_counter()
        reference, operations, _ = _reference_decode(attack_inst)
        reference_time += time.perf_counter() - started
        reference_ops.append(operations)
        if reference is not None and verify(attack_inst, reference)[0]:
            reference_successes += 1
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in outcomes.values())
        and reference_successes == 8,
        "attacks": outcomes,
        "algorithm_x_nodes": algorithm_nodes,
        "reference_algorithm": {
            "name": "inter-block modular-offset frequency decoder",
            "complexity": "O(|A| + n) integer/index operations",
            "wall_clock_sec": reference_time,
            "operations": sum(reference_ops),
            "per_instance_operations": reference_ops,
            "solves": f"{reference_successes}/8, as expected on Track B",
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled_params["screen_nodes"] = 0
    doubled = make_instance(seed=707, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["vertex_count"] == 2 * guess_inst["vertex_count"],
        "base_n": guess_inst["n"],
        "doubled_n": doubled["n"],
        "doubled_vertices": doubled["vertex_count"],
        "doubled_edges": len(doubled["edges"]),
        "verify_reason": doubled_reason,
    }

    keys = []
    key_failures = []
    invariance_checks = 0
    carried_checks = 0
    for seed in range(20):
        key_inst = make_instance(n=24, seed=8000 + seed, degree=6, screen_nodes=0)
        key = canonical_key(key_inst)
        keys.append(key)
        rng = random.Random(9000 + seed)
        permutation = list(range(key_inst["vertex_count"])); rng.shuffle(permutation)
        variants = [
            _relabel_instance(key_inst, permutation, False),
            _relabel_instance(key_inst, list(range(key_inst["vertex_count"])), True),
            _relabel_instance(key_inst, permutation, True),
        ]
        reordered = dict(key_inst); reordered["edges"] = list(reversed(key_inst["edges"]))
        variants.append(reordered)
        for variant in variants:
            invariance_checks += 1
            if canonical_key(variant) != key:
                key_failures.append({"seed": seed, "kind": "key changed"})
            ok, reason = verify(variant, variant["answer"])
            carried_checks += 1
            if not ok:
                key_failures.append({"seed": seed, "kind": "map invalid", "reason": reason})
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_keys": 20,
        "distinct_unrelated_keys": distinct,
        "failures": key_failures,
        "transformations": [
            "arbitrary vertex relabelling plus reversed edge-list order",
            "global reversal of every arc",
            "composition of relabelling, input reordering, and arc reversal",
            "edge-list reordering alone",
        ],
        "method": "triangle-support-seeded directed color refinement, converse-normalized",
    }

    answer_blob = json.dumps(guess_inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(guess_inst["answer"])
    compact = _compact_route_metrics(guess_inst)
    intended_operations = int(compact["operations"])
    arms = json.loads(json.dumps(G9_ARM_RESULTS))
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000 and answer_elements <= 256
        and intended_operations <= 300 and bool(compact["success"]),
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": (
            "not_run_cap_bound"
            if arms["hinted"]["attempts"] == 0
            else ("too_easy" if arms["hinted"]["solved"] else "hardened")
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "compact_vertices_inspected": compact["vertices_inspected"],
        "caps": {"chars": 2000, "tokens": 500, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["problem_profile"] = {**PROBLEM_PROFILE, "max_answer_tokens": answer_tokens}
    report["native"] = NATIVE
    report["certificate_language"] = CERTIFICATE_LANGUAGE
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = DIFFICULTY[SHIPPING_DIFFICULTY]
    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
