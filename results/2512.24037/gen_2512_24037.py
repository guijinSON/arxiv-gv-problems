"""Verified generator for a hard, cycle-only Kidney Exchange family.

The family is the perfect directed-triangle-packing special case of Definition 1
in arXiv:2512.24037.  There are no altruists, paths are disabled, every allowed
cycle has at most three edges, and the target is every vertex.  The graph is
oriented (it never contains both u->v and v->u), so a feasible cover necessarily
consists of directed 3-cycles.

Only the Python standard library is used.  Importing this module has no side
effects and performs no I/O.
"""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
import hashlib
import json
import math
import random
import re
import time
from typing import Any


NATIVE: dict = {
    "domain": "combinatorics",
    "core": "exact_cover",
    "objects": ["directed compatibility graph (adjacency list)"],
    "intuition": "recognize perfect directed-triangle packing as exact cover",
    "reduction": None,
}

# This is a parameterized finite language: for each instance, n and hence all
# array and integer bounds are fixed.  Canonicalization gives one serialization
# per unlabeled partition, exactly matching random_candidate and search_space.
CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "Canonical JSON partitions of the vertices 0,...,3*n-1 into exactly n "
        "unlabeled triples: every triple contains three distinct integers in "
        "increasing order, the triples are lexicographically sorted, and every "
        "vertex appears exactly once."
    ),
    "bounds": {
        "n_triples": "n",
        "triple_size": 3,
        "vertex_min": 0,
        "vertex_max": "3*n - 1",
        "vertex_count": "3*n",
    },
}


# ``example`` is intentionally transparent and is only for the README.  The
# hardening harness is expected to solve it and advance to ``hard``.
DIFFICULTY: dict = {
    "example": {"n": 3, "decoy_ratio": 0.0, "screen_nodes": 0},
    "hard": {"n": 60, "decoy_ratio": 2.0, "screen_nodes": 50_000},
}
SHIPPING_DIFFICULTY = "hard"

NOTES = r"""
Paper reading.  Section 2, Definition 1 fixes the exact object: a loopless
directed compatibility graph, an altruist set B, edge-count bounds lp and lc,
and a target t counting covered non-altruistic vertices.  This module uses
B=empty, lp=0, lc=3, and t=|V|.  Section 1.2 states that Kidney Exchange stays
NP-hard with short cycles or chains; Section 5 separately establishes hardness
without altruists.  Thus the witness here is a collection of vertex-disjoint
legal cycles, not a claimed optimum or a no-instance.

Easy regimes avoided.  Section 3 gives an O*((4e)^t) deterministic FPT
algorithm, so t=3n grows with n.  Section 1.1/5 notes FPT for the combined
treewidth and length parameters; the random compatibility graphs here do not
hold treewidth fixed.  Cycles of length at most two would collapse to ordinary
matching, so the cap is three.  Approximation results in Section 1.2 do not
certify a perfect cover.

Construction and attacks.  A uniformly random partition of all vertices and a
uniform cyclic orientation are sampled first.  Those planted arcs are inserted,
then uniformly sampled 3-cycles are inserted as noise; reverse arcs are rejected
so 2-cycles never arise.  Every vertex belongs to exactly one planted cycle, and
plant and noise cycles use the same triple/orientation distribution.  Random
relabeling is inherent in the initial partition.  The decoy ratio is kept near
the observed hard phase of planted exact cover.  Shipping instances are rejected
and regenerated if deterministic Algorithm X finds any cover within 50,000
search nodes.  The self-test also runs a degree/outlier greedy rule, a
left-to-right greedy rule, 256 randomized greedy restarts, and Algorithm X.

Paper caveat.  Section 6 appears internally inconsistent with Definition 1: it
sets t to |V| although altruists are not patients counted by t, and uses a path
bound one larger than the edge-count convention.  Its claim that positive-
integer Fixed-Size-3-Partition is NP-hard for a literally fixed target is also
not used here.  This generator relies on the short-cycle hardness summarized in
Section 1.2, not on that construction.
"""


def _cycle_arcs(triple: tuple[int, int, int], flip: int) -> tuple[tuple[int, int], ...]:
    """Return one of the two cyclic orientations of an unordered triple."""
    a, b, c = sorted(triple)
    if flip:
        b, c = c, b
    return ((a, b), (b, c), (c, a))


def _legal_cycles_from_edges(vertex_count: int, edges: Any) -> list[tuple[int, int, int]]:
    """Enumerate unordered vertex triples inducing a directed 3-cycle."""
    out = [set() for _ in range(vertex_count)]
    for u, v in edges:
        out[u].add(v)
    cycles: set[tuple[int, int, int]] = set()
    for a in range(vertex_count):
        for b in out[a]:
            for c in out[b]:
                if c != a and a in out[c]:
                    cycles.add(tuple(sorted((a, b, c))))
    return sorted(cycles)


def _canonical_answer(rows: Any) -> list[list[int]]:
    return sorted([sorted(map(int, row)) for row in rows])


def _algorithm_x_edges(
    vertex_count: int, edges: Any, node_limit: int
) -> tuple[list[list[int]] | None, int, bool]:
    """Exact-cover search with the standard minimum-column Algorithm X rule.

    The return value is (cover_or_None, visited_nodes, exhausted_search).  A None
    cover with exhausted_search=False means the explicit node budget was hit.
    """
    rows = _legal_cycles_from_edges(vertex_count, edges)
    by_vertex: list[list[int]] = [[] for _ in range(vertex_count)]
    row_masks: list[int] = []
    for row_id, row in enumerate(rows):
        mask = 0
        for v in row:
            mask |= 1 << v
            by_vertex[v].append(row_id)
        row_masks.append(mask)

    full = (1 << vertex_count) - 1
    nodes = 0
    cutoff = False

    def visit(covered: int) -> list[int] | None:
        nonlocal nodes, cutoff
        nodes += 1
        if nodes > node_limit:
            cutoff = True
            return None
        if covered == full:
            return []

        remaining = full ^ covered
        best: list[int] | None = None
        while remaining:
            bit = remaining & -remaining
            remaining -= bit
            v = bit.bit_length() - 1
            options = [r for r in by_vertex[v] if not (row_masks[r] & covered)]
            if not options:
                return None
            if best is None or len(options) < len(best):
                best = options

        assert best is not None
        for row_id in best:
            suffix = visit(covered | row_masks[row_id])
            if suffix is not None:
                return [row_id] + suffix
            if cutoff:
                return None
        return None

    picked = visit(0)
    if picked is None:
        return None, nodes, not cutoff
    return _canonical_answer(rows[r] for r in picked), nodes, True


def _one_graph(
    n: int, rng: random.Random, decoy_ratio: float
) -> tuple[list[tuple[int, int]], list[list[int]]]:
    """Sample the witness first, then add identically distributed cycle noise."""
    vertex_count = 3 * n
    order = list(range(vertex_count))
    rng.shuffle(order)

    # This is the answer-first step.  It is complete before any decoy is drawn.
    planted = [tuple(order[3 * i : 3 * i + 3]) for i in range(n)]
    edges: set[tuple[int, int]] = set()
    deliberately_added: set[tuple[int, int, int]] = set()

    def insert_cycle(triple: tuple[int, int, int]) -> bool:
        key = tuple(sorted(triple))
        if key in deliberately_added:
            return False
        choices = [0, 1]
        rng.shuffle(choices)
        for flip in choices:
            arcs = _cycle_arcs(key, flip)
            if any((v, u) in edges for u, v in arcs):
                continue
            if not any(arc not in edges for arc in arcs):
                continue
            edges.update(arcs)
            deliberately_added.add(key)
            return True
        return False

    for triple in planted:
        # Planted triples are disjoint, so no reverse-arc conflict is possible.
        if not insert_cycle(triple):
            raise AssertionError("disjoint planted cycle was unexpectedly rejected")

    wanted = int(round(decoy_ratio * vertex_count))
    accepted = 0
    tries = 0
    max_tries = max(10_000, 200 * max(1, wanted))
    while accepted < wanted and tries < max_tries:
        tries += 1
        triple = tuple(rng.sample(range(vertex_count), 3))
        if insert_cycle(triple):
            accepted += 1
    if accepted != wanted:
        raise ValueError("decoy density is too high for an oriented graph")

    return sorted(edges), _canonical_answer(planted)


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Make a planted perfect directed-3-cycle-packing instance.

    ``n`` is the number of cycles in a witness, so the graph has ``3*n``
    vertices and target ``t=3*n``.  Larger n at fixed decoy ratio increases the
    exact-cover core.  Generation is deterministic for (n, seed, params).
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer")
    decoy_ratio = float(params.pop("decoy_ratio", 2.0))
    screen_nodes = int(params.pop("screen_nodes", 0))
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if not math.isfinite(decoy_ratio) or decoy_ratio < 0:
        raise ValueError("decoy_ratio must be finite and nonnegative")
    if screen_nodes < 0:
        raise ValueError("screen_nodes must be nonnegative")

    rng = random.Random(seed)
    max_rounds = 64
    for build_round in range(max_rounds):
        edges, answer = _one_graph(n, rng, decoy_ratio)
        # Tiny examples should remain instant and readable.  At useful sizes,
        # screen away the easy tail of the planted distribution.
        if screen_nodes and n >= 50:
            found, _, _ = _algorithm_x_edges(3 * n, edges, screen_nodes)
            if found is not None and build_round + 1 < max_rounds:
                continue
        return {
            "family": "perfect_directed_triangle_kidney_exchange",
            "n": n,
            "vertex_count": 3 * n,
            "edges": [list(e) for e in edges],
            "altruists": [],
            "path_limit": 0,
            "cycle_limit": 3,
            "target": 3 * n,
            "decoy_ratio": decoy_ratio,
            "screen_nodes": screen_nodes,
            "screen_passed": not screen_nodes or n < 50 or found is None,
            "build_round": build_round,
            "answer": answer,
        }
    raise RuntimeError("could not sample an instance that passed the hardness screen")


def render(inst: dict) -> str:
    """Render the complete, self-contained problem seen by a solver."""
    vertex_count = inst["vertex_count"]
    out = [[] for _ in range(vertex_count)]
    for u, v in inst["edges"]:
        out[u].append(v)
    adjacency = "\n".join(
        f"{u}: " + (" ".join(map(str, sorted(out[u]))) if out[u] else "-")
        for u in range(vertex_count)
    )
    return f"""Kidney exchange — perfect directed 3-cycle packing

There are {vertex_count} patient-donor pairs, numbered 0 through {vertex_count - 1}.
There are no altruistic donors, so paths/chains are not allowed.  A directed edge
u -> v means that u's donor is compatible with v's patient.  The graph has no
self-loops and never contains both u -> v and v -> u.

A legal exchange is a directed cycle with at most 3 edges.  Because this graph is
oriented as stated above, it has no 1- or 2-edge cycles; every legal exchange is
therefore a directed 3-cycle on three distinct vertices.  For a sorted triple
[a,b,c], it is a directed 3-cycle exactly when either the edges a->b, b->c, c->a
all exist or the edges a->c, c->b, b->a all exist.

Find exactly {inst['n']} pairwise vertex-disjoint directed 3-cycles.  They must
cover all {vertex_count} vertices, so every patient receives a kidney.  A vertex
may appear in exactly one triple.  Vertex numbering is 0-based.  Within each
triple list the three vertex numbers in strictly increasing order; sort the list
of triples lexicographically.  No repeats are allowed, and order otherwise has
no meaning.

The adjacency list below gives every directed edge.  A dash means no outgoing
edges.  No edges other than those listed exist.

{adjacency}

Give your final answer inside <answer></answer> tags, as one JSON array containing
exactly {inst['n']} three-integer arrays in the canonical sorted order just
specified.
Example format: <answer>[[0, 1, 2], [3, 4, 5]]</answer>
Output nothing else inside the tags."""


def parse_answer(text: str) -> object | None:
    """Extract the last well-formed tagged JSON array; never raise on garbage."""
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
        if not isinstance(value, list):
            continue
        if not all(isinstance(row, list) for row in value):
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
    """Check any perfect cycle cover without consulting the planted answer.

    The renderer requests canonical ordering for a clean wire format, but the
    checker deliberately normalizes row and cycle order so every semantically
    valid witness is accepted.
    """
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    expected = inst["n"]
    if len(answer) != expected:
        return False, f"expected {expected} cycles, got {len(answer)}"

    vertex_count = inst["vertex_count"]
    seen: set[int] = set()
    edge_set = {tuple(e) for e in inst["edges"]}
    for i, row in enumerate(answer):
        if not isinstance(row, list):
            return False, f"cycle {i} is not a JSON array"
        if len(row) != 3:
            return False, f"cycle {i} has {len(row)} vertices; expected 3"
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in row):
            return False, f"cycle {i} contains a non-integer vertex"
        if len(set(row)) != 3:
            return False, f"cycle {i} repeats a vertex"
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
            return False, f"cycle {i} is not a directed 3-cycle"

    if len(seen) != vertex_count:
        missing = min(set(range(vertex_count)) - seen)
        return False, f"vertex {missing} is not covered"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample a partition into triples, the structure-aware prior.

    Arity, full coverage, disjointness, and canonical ordering are built in.  It
    does not use the planted answer or favor any legal graph edge.
    """
    vertices = list(range(inst["vertex_count"]))
    rng.shuffle(vertices)
    return _canonical_answer(
        vertices[i : i + 3] for i in range(0, len(vertices), 3)
    )


def search_space(inst: dict) -> int | None:
    """Number of unordered partitions of 3n labelled vertices into n triples."""
    n = inst["n"]
    return math.factorial(3 * n) // (math.factorial(3) ** n * math.factorial(n))


def enumerate_all(inst: dict) -> int | None:
    """Count every valid cover exactly when the explicit state space is small."""
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
    cap = 2_000_000

    @lru_cache(maxsize=None)
    def count(covered: int) -> int:
        nonlocal calls
        calls += 1
        if calls > cap:
            raise OverflowError
        if covered == full:
            return 1
        remaining = full ^ covered
        bit = remaining & -remaining
        v = bit.bit_length() - 1
        return sum(count(covered | masks[r]) for r in by_vertex[v] if not (masks[r] & covered))

    try:
        return count(0)
    except OverflowError:
        return None


def _wl_code(vertex_count: int, edges: list[tuple[int, int]]) -> str:
    """A deterministic directed 1-WL structural code (not a seed/render hash)."""
    incoming = [[] for _ in range(vertex_count)]
    outgoing = [[] for _ in range(vertex_count)]
    for u, v in edges:
        outgoing[u].append(v)
        incoming[v].append(u)
    colors = [0] * vertex_count
    for _ in range(vertex_count):
        signatures = [
            (
                colors[v],
                tuple(sorted(colors[u] for u in incoming[v])),
                tuple(sorted(colors[w] for w in outgoing[v])),
            )
            for v in range(vertex_count)
        ]
        palette = {sig: i for i, sig in enumerate(sorted(set(signatures)))}
        refined = [palette[sig] for sig in signatures]
        old_classes = len(set(colors))
        colors = refined
        if len(set(colors)) == old_classes:
            break
    counts = sorted(Counter(colors).items())
    colored_edges = sorted((colors[u], colors[v]) for u, v in edges)
    return json.dumps([vertex_count, counts, colored_edges], separators=(",", ":"))


def canonical_key(inst: dict) -> str:
    """Invariant under vertex relabeling, edge order, and global arc reversal.

    Directed graph isomorphism is not known to have a cheap complete canonical
    form.  This uses stable directed color refinement; on these irregular random
    graphs it almost always individualizes all vertices.  The minimum of the
    graph and converse-graph codes handles the answer-preserving global reversal.
    """
    vertex_count = inst["vertex_count"]
    edges = [tuple(e) for e in inst["edges"]]
    forward = _wl_code(vertex_count, edges)
    backward = _wl_code(vertex_count, [(v, u) for u, v in edges])
    structural = json.dumps(
        [inst["cycle_limit"], inst["path_limit"], inst["target"], min(forward, backward)],
        separators=(",", ":"),
    )
    return hashlib.sha256(structural.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | None:
    """Keep the critical decoy density and enlarge the exact-cover core."""
    current = int(params.get("n", 60))
    if current >= 120:
        return None
    nxt = dict(params)
    nxt["n"] = min(120, current + 20)
    nxt.setdefault("decoy_ratio", 2.0)
    nxt.setdefault("screen_nodes", 50_000)
    return nxt


def _outlier_attack(inst: dict) -> list[list[int]] | None:
    """Prefer cycles whose vertices have the lowest aggregate directed degree."""
    vertex_count = inst["vertex_count"]
    degree = [0] * vertex_count
    for u, v in inst["edges"]:
        degree[u] += 1
        degree[v] += 1
    cycles = _legal_cycles_from_edges(vertex_count, inst["edges"])
    cycles.sort(key=lambda row: (sum(degree[v] for v in row), row))
    used: set[int] = set()
    chosen = []
    for row in cycles:
        if not used.intersection(row):
            chosen.append(row)
            used.update(row)
    if len(used) != vertex_count:
        return None
    return _canonical_answer(chosen)


def _greedy_attack(inst: dict) -> list[list[int]] | None:
    """Cover the smallest uncovered vertex with its lexicographically first row."""
    vertex_count = inst["vertex_count"]
    rows = _legal_cycles_from_edges(vertex_count, inst["edges"])
    by_vertex = [[] for _ in range(vertex_count)]
    for row in rows:
        for v in row:
            by_vertex[v].append(row)
    uncovered = set(range(vertex_count))
    chosen = []
    while uncovered:
        v = min(uncovered)
        options = [row for row in by_vertex[v] if set(row) <= uncovered]
        if not options:
            return None
        row = min(options)
        chosen.append(row)
        uncovered.difference_update(row)
    return _canonical_answer(chosen)


def _random_restart_attack(inst: dict, restarts: int = 256) -> list[list[int]] | None:
    """Randomized no-backtracking exact-cover greed with an MRV column rule."""
    vertex_count = inst["vertex_count"]
    rows = _legal_cycles_from_edges(vertex_count, inst["edges"])
    by_vertex = [[] for _ in range(vertex_count)]
    for row in rows:
        for v in row:
            by_vertex[v].append(row)
    # Derive attack randomness only from public instance data, never the plant.
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


def _relabel_instance(inst: dict, permutation: list[int], reverse_arcs: bool = False) -> dict:
    """Relabel a test instance and carry its witness through the same bijection."""
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


def selftest() -> dict:
    """Run gates G1--G8 and return their measured, JSON-serializable report."""
    report: dict[str, Any] = {}

    # G1: every named preset and several independent seeds.
    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2, 3):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    # G2: five specified corruptions reach five distinct rejection paths.
    inst = make_instance(seed=101, **DIFFICULTY[SHIPPING_DIFFICULTY])
    base = json.loads(json.dumps(inst["answer"]))
    corruptions = {}
    dropped = json.loads(json.dumps(base))
    dropped[0].pop()
    corruptions["drop_one"] = dropped
    # Exchange one vertex between two cycles.  Purely reordering a cycle must be
    # accepted, so find a genuine one-for-one membership swap that breaks an arc.
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
                        swapped = trial
                        break
                if swapped is not None:
                    break
            if swapped is not None:
                break
        if swapped is not None:
            break
    if swapped is None:
        raise AssertionError("could not construct a rejected membership swap")
    corruptions["swap_one"] = swapped
    duplicated = json.loads(json.dumps(base))
    duplicated[0][2] = duplicated[0][1]
    corruptions["duplicate"] = duplicated
    corruptions["empty"] = []
    outside = json.loads(json.dumps(base))
    outside[-1][-1] = inst["vertex_count"]
    corruptions["out_of_range"] = outside
    reasons = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        reasons[name] = {"rejected": not ok, "reason": why}
    reason_texts = [v["reason"] for v in reasons.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in reasons.values()) and len(set(reason_texts)) == 5,
        "cases": reasons,
        "distinct_reasons": len(set(reason_texts)),
    }

    # G3: realistic prose, a Markdown fence, and whitespace around the tag.
    payload = json.dumps(inst["answer"])
    response = f"I checked every arc.\n```json\n<answer>\n{payload}\n</answer>\n```\nDone."
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and parse_answer("garbage") is None,
        "realistic_response_parsed": parsed == inst["answer"],
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4: uniform over partitions into triples, not arbitrary integer arrays.
    guess_inst = make_instance(seed=2024, **DIFFICULTY[SHIPPING_DIFFICULTY])
    guess_rng = random.Random(0x251224037)
    total = 200_000
    hits = 0
    for _ in range(total):
        candidate = random_candidate(guess_inst, guess_rng)
        if verify(guess_inst, candidate)[0]:
            hits += 1
    measured = hits / total
    report["G4_guess_resistance"] = {
        "pass": measured < 1e-6,
        "hits": hits,
        "total": total,
        "measured_probability": measured,
        "prior": "uniform random partition of all vertices into unlabeled triples",
        "naive_search_space": search_space(guess_inst),
    }

    # G5: density and strongest-baseline cost on the instance that ships.  The
    # G4 candidates already form a uniform sample from the declared language,
    # so reuse that run rather than silently changing the instance or prior.
    baseline_limit = 50_000
    baseline_started = time.perf_counter()
    baseline_answer, baseline_nodes, baseline_exhausted = _algorithm_x_edges(
        guess_inst["vertex_count"], guess_inst["edges"], baseline_limit
    )
    baseline_seconds = time.perf_counter() - baseline_started

    # Keep the earlier exact small-instance count only as a labelled additional
    # measurement.  It is not substituted for the shipping-preset density.
    sparse_inst = make_instance(n=5, seed=505, decoy_ratio=2.0, screen_nodes=0)
    solution_count = enumerate_all(sparse_inst)
    space = search_space(sparse_inst)
    fraction = None if solution_count is None else solution_count / space
    report["G5_shipping_difficulty"] = {
        "pass": (
            measured < 0.001
            and total > 0
            and baseline_nodes > 0
            and baseline_seconds >= 0.0
            and solution_count is not None
            and fraction is not None
            and fraction < 0.001
        ),
        "preset": SHIPPING_DIFFICULTY,
        "params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
        "seed": 2024,
        "n": guess_inst["n"],
        "density": {
            "method": "uniform samples from CERTIFICATE_LANGUAGE, checked by verify",
            "valid_samples": hits,
            "sample_size": total,
            "observed_fraction": measured,
            "candidate_space": search_space(guess_inst),
            "pass_threshold": 0.001,
        },
        "baseline_cost": {
            "attack": "Algorithm X with minimum-column branching",
            "node_limit": baseline_limit,
            "nodes": baseline_nodes,
            "wall_seconds": baseline_seconds,
            "found_valid_witness": (
                baseline_answer is not None
                and verify(guess_inst, baseline_answer)[0]
            ),
            "search_exhausted": baseline_exhausted,
        },
        "additional_small_exact_count": {
            "n": 5,
            "seed": 505,
            "valid_answers": solution_count,
            "candidate_space": space,
            "fraction": fraction,
        },
    }

    # G6: construction-aware generic probes plus the standard exact-cover attack.
    attack_names = (
        "outlier_low_degree",
        "greedy_left_to_right",
        "random_restart_256",
        "algorithm_x_50000",
    )
    outcomes = {name: {"successes": 0, "attempts": 8} for name in attack_names}
    algorithm_nodes = []
    for seed in range(3000, 3008):
        attack_inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        guesses = {
            "outlier_low_degree": _outlier_attack(attack_inst),
            "greedy_left_to_right": _greedy_attack(attack_inst),
            "random_restart_256": _random_restart_attack(attack_inst, 256),
        }
        exact, nodes, _ = _algorithm_x_edges(
            attack_inst["vertex_count"], attack_inst["edges"], 50_000
        )
        guesses["algorithm_x_50000"] = exact
        algorithm_nodes.append(nodes)
        for name, candidate in guesses.items():
            if candidate is not None and verify(attack_inst, candidate)[0]:
                outcomes[name]["successes"] += 1
    all_failed = all(v["successes"] == 0 for v in outcomes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": outcomes,
        "algorithm_x_nodes": algorithm_nodes,
        "domain_attack": "Algorithm X with minimum-column branching",
    }

    # G7: the generator and planted check survive a doubled exact-cover core.
    shipping_n = DIFFICULTY[SHIPPING_DIFFICULTY]["n"]
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] = 2 * shipping_n
    doubled = make_instance(seed=707, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["vertex_count"] == 2 * guess_inst["vertex_count"],
        "base_n": shipping_n,
        "doubled_n": doubled_params["n"],
        "doubled_vertices": doubled["vertex_count"],
        "doubled_edges": len(doubled["edges"]),
        "verify_reason": doubled_why,
    }

    # G8: vertex bijections, arc-list reorderings, reversal, and compositions.
    invariant_checks = 0
    carried_witness_checks = 0
    invariant_failures = []
    keys = []
    for seed in range(20):
        key_inst = make_instance(n=16, seed=8000 + seed, decoy_ratio=2.0, screen_nodes=0)
        original_key = canonical_key(key_inst)
        keys.append(original_key)
        relabel_rng = random.Random(9000 + seed)
        permutation = list(range(key_inst["vertex_count"]))
        relabel_rng.shuffle(permutation)
        variants = [
            _relabel_instance(key_inst, permutation, False),
            _relabel_instance(key_inst, list(range(key_inst["vertex_count"])), True),
            _relabel_instance(key_inst, permutation, True),
        ]
        reordered = dict(key_inst)
        reordered["edges"] = list(reversed(key_inst["edges"]))
        variants.append(reordered)
        for variant in variants:
            invariant_checks += 1
            if canonical_key(variant) != original_key:
                invariant_failures.append(seed)
            ok, _ = verify(variant, variant["answer"])
            carried_witness_checks += 1
            if not ok:
                invariant_failures.append(seed)
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_witness_checks,
        "unrelated_keys": 20,
        "distinct_unrelated_keys": distinct,
        "failures": invariant_failures,
        "transformations": [
            "arbitrary vertex relabeling plus reversed edge-list order",
            "global reversal of every arc",
            "composition of relabeling, reordering, and arc reversal",
            "edge-list reordering alone",
        ],
        "method": "directed 1-WL refinement, normalized with the converse graph",
    }

    gate_values = [v for k, v in report.items() if k.startswith("G")]
    report["all_passed"] = all(v.get("pass") is True for v in gate_values)
    report["native"] = NATIVE
    report["certificate_language"] = CERTIFICATE_LANGUAGE
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = DIFFICULTY[SHIPPING_DIFFICULTY]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
