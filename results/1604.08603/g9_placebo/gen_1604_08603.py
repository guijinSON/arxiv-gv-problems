"""Generator for cubic {K_1,3, P_4}-edge-decomposition instances.

The family comes from Bulteau et al., "Decomposing Cubic Graphs into
Connected Subgraphs of Size Three" (arXiv:1604.08603), specifically the
NP-complete regime in Theorem 2.  Only the Python standard library is used.
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


TRACK = "A"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": ["labelled simple connected cubic graph", "edge IDs"],
    "verification_operations": [
        "exact integer edge-cover accounting",
        "endpoint-incidence degree counting",
        "three-edge graph-shape comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Bridge constraints and local edge-incidence degrees propagate forced "
        "three-edge pieces; without them the solver faces exact-cover branching."
    ),
    "hardness_basis": (
        "Track A: Theorem 2 proves NP-completeness for simple connected cubic "
        "{K1,3,P4}-decomposition; in the shipping n=48 non-bipartite, "
        "no-perfect-matching regime, minimum-column Algorithm X hit its "
        "200,000-node cap on each of 8/8 measured seeds without a solution."
    ),
    # A compact JSON answer has 153 scalar edge IDs and 409 conservative lexical
    # tokens (numbers and punctuation are each counted as one token).
    "max_answer_tokens": 409,
}


NATIVE: dict = {
    "domain": "combinatorics",
    "core": "exact_cover",
    "objects": ["labelled simple connected cubic graph", "edge IDs"],
    "intuition": (
        "constraint propagation: Bridge constraints and local edge-incidence "
        "degrees propagate forced three-edge pieces; without them the solver "
        "faces exact-cover branching."
    ),
    "reduction": None,
}

DIFFICULTY: dict = {
    "hard": {"n": 48, "claw_fraction": 0.50, "marked_fraction": 0.25},
}

SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "For an instance with m labelled edges, a certificate is an unordered "
        "partition of edge IDs 1..m into exactly m/3 unordered triples. At the "
        "shipping preset m=153, so every certificate has 51 triples of arity 3."
    ),
    "bounds": {
        "shipping_edge_ids": 153,
        "shipping_groups": 51,
        "group_size": 3,
        "edge_id_min": 1,
        "edge_id_max": 153,
    },
}


STRUCTURAL_HINT = (
    "Every bridge must be the middle edge of a three-edge path in any valid decomposition."
)

PLACEBO_HINT = (
    "Careful tracking of edge identifiers helps avoid mistakes in any valid decomposition."
)

# These external measurements are replaced with the final transcript counts after
# running the three hardening arms.  They are data, not inputs to generation or
# verification, and are kept here so selftest() remains deterministic and does no IO.
G9_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}
G9_HINTED_VERDICT = "not_run_openrouter_quota_exhausted"

NOTES = r"""
Section 1 and Table 1 fix the exact problem: the input is a simple connected
cubic graph and the witness partitions every edge into three-edge subgraphs.
We use exactly K_{1,3} (a claw) and P_4 (a four-vertex path).  Theorem 2 in
Section 4 proves this regime NP-complete.  The other six choices of allowed
shapes are polynomial-time or impossible.  In particular, Proposition 2 says
that a cubic graph has a P_4-only decomposition exactly when it has a perfect
matching, and Proposition 3 makes bipartite graphs trivial via claws.

The answer is sampled first as a random mixture of claws and paths whose vertex
incidences are paired uniformly subject to simplicity and connectedness.  We
then use the co-fish attachment from Section 4, Lemma 3, on all three edges of
several planted claws.  The local replacement has an explicit ten-piece
decomposition.  Its bridge forces the attachment vertex to match into the
five-vertex co-fish core in every perfect matching.  Since all three edges at a
selected old vertex are attached this way, that vertex cannot be matched;
therefore every emitted graph has no perfect matching and cannot fall into the
easy P_4-only regime.  Co-fish triangles also make it non-bipartite.

Edges and vertices are independently relabelled after construction.  Plants
and unmodified pieces use the same random incidence distribution.  The outlier
attack targets co-fish-adjacent vertices; greedy and random-restart attacks use
the exact-cover matrix; the domain attack is Algorithm X with the minimum-column
heuristic.  The canonical key ignores labels and edge order and hashes a strong
multiset of rooted colour-refinement quotients.  It is an invariant, not a
complete graph-isomorphism canonical form; this limitation is documented.

STEP 0 track decision: the certificate for an arbitrary instance is produced by
exact-cover search, whose worst-case cost is exponential; the paper gives no
polynomial algorithm for the {K_{1,3},P_4} regime.  The planted certificate is
instead known by inverse generation and the co-fish identity.  The bridge lemma
is useful propagation but does not collapse the random base exact cover to a
short formula, so this is Track A rather than Track B.
"""


def _norm_edge(u: int, v: int) -> tuple[int, int]:
    return (u, v) if u < v else (v, u)


def _connected(n: int, edges: list[tuple[int, int]]) -> bool:
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    seen = {0}
    todo = [0]
    while todo:
        u = todo.pop()
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                todo.append(v)
    return len(seen) == n


def _base_graph(
    n: int, claw_fraction: float, rng: random.Random
) -> tuple[list[tuple[int, int]], list[list[tuple[int, int]]], list[int]]:
    """Sample piece roles first, then identify role stubs into cubic vertices."""
    piece_count = n // 2
    claw_count = min(piece_count - 1, max(1, int(round(piece_count * claw_fraction))))
    kinds = ["C"] * claw_count + ["P"] * (piece_count - claw_count)
    rng.shuffle(kinds)

    # Tokens name incidence roles.  A C centre consumes degree 3, a P internal
    # role consumes degree 2, and all U roles consume degree 1.
    units: list[tuple[str, int, int]] = []
    doubles: list[tuple[str, int, int]] = []
    centres: list[tuple[str, int, int]] = []
    for p, kind in enumerate(kinds):
        if kind == "C":
            centres.append(("C", p, 0))
            units.extend(("U", p, j) for j in range(1, 4))
        else:
            units.extend((("U", p, 0), ("U", p, 3)))
            doubles.extend((("D", p, 1), ("D", p, 2)))

    for _ in range(20_000):
        us = units[:]
        ds = doubles[:]
        rng.shuffle(us)
        rng.shuffle(ds)
        paired = us[: len(ds)]
        left = us[len(ds) :]
        if any(u[1] == d[1] for u, d in zip(paired, ds)):
            continue
        triples = [left[i : i + 3] for i in range(0, len(left), 3)]
        if any(len({x[1] for x in group}) != 3 for group in triples):
            continue

        role_vertex: dict[tuple[str, int, int], int] = {}
        next_vertex = 0
        for role in centres:
            role_vertex[role] = next_vertex
            next_vertex += 1
        for d, u in zip(ds, paired):
            role_vertex[d] = next_vertex
            role_vertex[u] = next_vertex
            next_vertex += 1
        for group in triples:
            for u in group:
                role_vertex[u] = next_vertex
            next_vertex += 1
        if next_vertex != n:
            raise AssertionError("incidence accounting error")

        pieces: list[list[tuple[int, int]]] = []
        edges: list[tuple[int, int]] = []
        claw_piece_indices: list[int] = []
        for p, kind in enumerate(kinds):
            if kind == "C":
                c = role_vertex[("C", p, 0)]
                verts = [role_vertex[("U", p, j)] for j in range(1, 4)]
                part = [_norm_edge(c, v) for v in verts]
                claw_piece_indices.append(p)
            else:
                verts = [
                    role_vertex[("U", p, 0)],
                    role_vertex[("D", p, 1)],
                    role_vertex[("D", p, 2)],
                    role_vertex[("U", p, 3)],
                ]
                part = [_norm_edge(verts[j], verts[j + 1]) for j in range(3)]
            pieces.append(part)
            edges.extend(part)

        if len(set(edges)) != len(edges):
            continue
        degree = Counter(x for e in edges for x in e)
        if len(degree) != n or any(degree[v] != 3 for v in range(n)):
            continue
        if not _connected(n, edges):
            continue
        return edges, pieces, claw_piece_indices
    raise RuntimeError("could not sample a connected simple cubic base graph")


def _attach_cofishes(
    n: int,
    pieces: list[list[tuple[int, int]]],
    selected: set[int],
) -> tuple[int, list[tuple[int, int]], list[list[tuple[int, int]]]]:
    """Replace selected planted claws by the explicit Lemma 3 local cover."""
    out_pieces: list[list[tuple[int, int]]] = []
    all_edges: list[tuple[int, int]] = []
    next_vertex = n

    for piece_index, part in enumerate(pieces):
        if piece_index not in selected:
            out_pieces.append(part[:])
            all_edges.extend(part)
            continue

        deg = Counter(x for edge in part for x in edge)
        centre = next(v for v, d in deg.items() if d == 3)
        centre_edges: list[tuple[int, int]] = []
        for old_u, old_v in part:
            leaf = old_v if old_u == centre else old_u
            f, a, b, c, d, x = range(next_vertex, next_vertex + 6)
            next_vertex += 6
            local = [
                _norm_edge(centre, f),
                _norm_edge(f, leaf),
                _norm_edge(f, a),
                _norm_edge(a, b),
                _norm_edge(b, c),
                _norm_edge(c, d),
                _norm_edge(d, a),
                _norm_edge(b, x),
                _norm_edge(d, x),
                _norm_edge(c, x),
            ]
            all_edges.extend(local)
            centre_edges.append(local[0])
            # leaf-f-a-b, b-c-d-a, and the claw centred at x.
            out_pieces.append([local[1], local[2], local[3]])
            out_pieces.append([local[4], local[5], local[6]])
            out_pieces.append([local[7], local[8], local[9]])
        out_pieces.append(centre_edges)
    return next_vertex, all_edges, out_pieces


def make_instance(
    n: int,
    seed: int = 0,
    claw_fraction: float = 0.50,
    marked_fraction: float = 0.25,
) -> dict:
    """Sample a decomposition first and construct its cubic graph around it.

    ``n`` is the even number of vertices in the random base graph, before the
    co-fish gadgets are attached.  Larger ``n`` adds independently coupled
    pieces and increases the exact-cover search problem.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 8 or n % 2:
        raise ValueError("n must be an even integer at least 8")
    if not (0.10 <= float(claw_fraction) <= 0.90):
        raise ValueError("claw_fraction must be between 0.10 and 0.90")
    if not (0.0 <= float(marked_fraction) <= 1.0):
        raise ValueError("marked_fraction must be between 0 and 1")

    rng = random.Random(seed)
    base_edges, base_pieces, claw_indices = _base_graph(n, claw_fraction, rng)
    del base_edges  # the pieces are the authoritative pre-attachment partition
    marked_count = 0
    if marked_fraction > 0:
        marked_count = max(1, int(round(len(claw_indices) * marked_fraction)))
    marked_count = min(marked_count, len(claw_indices))
    chosen = set(rng.sample(claw_indices, marked_count))
    vertex_count, edges, answer_edges = _attach_cofishes(n, base_pieces, chosen)

    # Erase construction order: relabel vertices, shuffle the edge table, and
    # shuffle both pieces and the three IDs inside each piece.
    vertex_perm = list(range(vertex_count))
    rng.shuffle(vertex_perm)
    relabelled = [_norm_edge(vertex_perm[u], vertex_perm[v]) for u, v in edges]
    order = list(range(len(relabelled)))
    rng.shuffle(order)
    edge_id = {relabelled[old]: new + 1 for new, old in enumerate(order)}
    final_edges = [relabelled[old] for old in order]
    answer = []
    for part in answer_edges:
        ids = [edge_id[_norm_edge(vertex_perm[u], vertex_perm[v])] for u, v in part]
        rng.shuffle(ids)
        answer.append(ids)
    rng.shuffle(answer)

    inst = {
        "vertex_count": vertex_count,
        "edges": [[u + 1, v + 1] for u, v in final_edges],
        "answer": answer,
        "base_n": n,
        "allowed": ["K1,3", "P4"],
    }
    return inst


def render(inst: dict) -> str:
    """Render a complete, standalone statement and its exact output contract."""
    lines = [
        "CUBIC GRAPH EDGE DECOMPOSITION",
        "",
        "The input is a simple undirected graph. Vertices are the integers",
        f"1 through {inst['vertex_count']}. Edges are numbered 1 through {len(inst['edges'])}",
        "in the table below. Each table row has the form `edge_id: endpoint endpoint`.",
        "",
        "Partition every edge into groups of exactly three. Each group must be",
        "one of these (the chosen three edges need not be an induced subgraph):",
        "  * K1,3 (claw): three edges sharing one centre and having three distinct leaves;",
        "  * P4 (path): a simple path of three edges on four distinct vertices.",
        "",
        "Every edge ID must occur exactly once. Groups and IDs within a group may",
        "be in any order. Repetitions are forbidden. Vertex and edge IDs are 1-indexed.",
        "",
        "EDGES",
    ]
    lines.extend(f"{i}: {u} {v}" for i, (u, v) in enumerate(inst["edges"], 1))
    lines.extend(
        [
            "",
            f"Your answer must be a JSON array of exactly {len(inst['edges']) // 3} arrays,",
            "each inner array containing exactly three integer edge IDs.",
            "Give your final answer inside <answer></answer> tags, in that JSON format.",
            "Example: <answer>[[1,2,3],[4,5,6]]</answer>",
            "The example only illustrates syntax and is not an answer to this instance.",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Extract the last well-formed tagged JSON decomposition, without raising."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    for body in reversed(matches):
        body = body.strip()
        if body.startswith("```") and body.endswith("```"):
            body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
            body = re.sub(r"\s*```$", "", body)
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            continue
        if not isinstance(value, list):
            continue
        if not all(isinstance(p, list) for p in value):
            continue
        if not all(all(isinstance(e, int) and not isinstance(e, bool) for e in p) for p in value):
            continue
        return value
    return None


def _piece_kind(edge_table: list[list[int]], ids: list[int]) -> str | None:
    degree: Counter[int] = Counter()
    vertices = set()
    for edge_id in ids:
        u, v = edge_table[edge_id - 1]
        degree[u] += 1
        degree[v] += 1
        vertices.add(u)
        vertices.add(v)
    if len(vertices) != 4:
        return None
    ds = sorted(degree.values())
    if ds == [1, 1, 1, 3]:
        return "K1,3"
    if ds == [1, 1, 2, 2]:
        return "P4"
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid edge partition; the planted answer is never consulted."""
    edge_count = len(inst["edges"])
    needed = edge_count // 3
    if not isinstance(answer, list):
        return False, "answer_not_array"
    if len(answer) != needed:
        return False, f"piece_count: expected {needed}, got {len(answer)}"
    for i, part in enumerate(answer):
        if not isinstance(part, list):
            return False, f"piece_not_array: group {i + 1}"
        if len(part) != 3:
            return False, f"piece_arity: group {i + 1} has {len(part)} IDs"
        if any(not isinstance(e, int) or isinstance(e, bool) for e in part):
            return False, f"edge_not_integer: group {i + 1}"
        if any(e < 1 or e > edge_count for e in part):
            return False, f"edge_range: group {i + 1}"
    flat = [e for part in answer for e in part]
    if len(set(flat)) != len(flat):
        return False, "duplicate_edge"
    missing = set(range(1, edge_count + 1)) - set(flat)
    if missing:
        return False, f"missing_edge: {min(missing)}"
    for i, part in enumerate(answer):
        if _piece_kind(inst["edges"], part) is None:
            return False, f"invalid_shape: group {i + 1}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample an edge partition into unordered triples.

    This incorporates the statement-obvious arity, piece count, no-repetition,
    and exact-coverage constraints.  It does not condition on connected shape,
    which is precisely the nontrivial constraint being guessed.
    """
    ids = list(range(1, len(inst["edges"]) + 1))
    rng.shuffle(ids)
    return [ids[i : i + 3] for i in range(0, len(ids), 3)]


def search_space(inst: dict) -> int | None:
    """Number of partitions of all labelled edges into unordered triples."""
    m = len(inst["edges"])
    p = m // 3
    return math.factorial(m) // (math.factorial(3) ** p * math.factorial(p))


def _valid_pieces(inst: dict) -> list[tuple[int, int, int]]:
    """Enumerate all claw and P4 candidates as triples of zero-based edge IDs."""
    edges = [(u - 1, v - 1) for u, v in inst["edges"]]
    n = inst["vertex_count"]
    incident: list[list[int]] = [[] for _ in range(n)]
    other: list[dict[int, int]] = [dict() for _ in range(n)]
    for e, (u, v) in enumerate(edges):
        incident[u].append(e)
        incident[v].append(e)
        other[u][e] = v
        other[v][e] = u
    out: set[tuple[int, int, int]] = set()
    for es in incident:
        if len(es) >= 3:
            for part in itertools.combinations(es, 3):
                out.add(tuple(sorted(part)))
    # Choose a middle edge and one continuing edge at each endpoint.
    for middle, (u, v) in enumerate(edges):
        for left in incident[u]:
            if left == middle:
                continue
            a = other[u][left]
            for right in incident[v]:
                if right == middle:
                    continue
                b = other[v][right]
                if len({a, u, v, b}) == 4:
                    out.add(tuple(sorted((left, middle, right))))
    return sorted(out)


def _exact_cover(
    inst: dict,
    *,
    node_limit: int,
    rng: random.Random | None = None,
    count_all: bool = False,
) -> tuple[list[list[int]] | None, int, int, bool]:
    """Algorithm X; return (solution, count, nodes, exhausted)."""
    pieces = _valid_pieces(inst)
    m = len(inst["edges"])
    by_edge: list[list[int]] = [[] for _ in range(m)]
    for row, part in enumerate(pieces):
        for e in part:
            by_edge[e].append(row)
    used = [False] * m
    chosen: list[int] = []
    first_solution: list[list[int]] | None = None
    count = 0
    nodes = 0
    exhausted = True

    def visit() -> bool:
        nonlocal first_solution, count, nodes, exhausted
        if nodes >= node_limit:
            exhausted = False
            return True
        nodes += 1
        if len(chosen) * 3 == m:
            count += 1
            if first_solution is None:
                first_solution = [[e + 1 for e in pieces[r]] for r in chosen]
            return not count_all
        best_options: list[int] | None = None
        for edge in range(m):
            if used[edge]:
                continue
            options = [
                row for row in by_edge[edge]
                if not any(used[e] for e in pieces[row])
            ]
            if not options:
                return False
            if best_options is None or len(options) < len(best_options):
                best_options = options
                if len(options) == 1:
                    break
        assert best_options is not None
        if rng is not None:
            best_options = best_options[:]
            rng.shuffle(best_options)
        for row in best_options:
            part = pieces[row]
            for e in part:
                used[e] = True
            chosen.append(row)
            stop = visit()
            chosen.pop()
            for e in part:
                used[e] = False
            if stop:
                return True
        return False

    visit()
    return first_solution, count, nodes, exhausted


def enumerate_all(inst: dict) -> int | None:
    """Count all decompositions only for small instances, with a hard work cap."""
    if len(inst["edges"]) > 24:
        return None
    _, count, _, exhausted = _exact_cover(inst, node_limit=2_000_000, count_all=True)
    return count if exhausted else None


def _root_signature(adj: list[list[int]], root: int) -> tuple:
    """Invariant rooted 1-WL quotient, used as a strong cheap GI invariant."""
    n = len(adj)
    colors = [0] * n
    colors[root] = 1
    history = []
    for _ in range(n):
        descriptions = [(colors[v], tuple(sorted(colors[w] for w in adj[v]))) for v in range(n)]
        palette = {value: i for i, value in enumerate(sorted(set(descriptions)))}
        new_colors = [palette[value] for value in descriptions]
        sizes = tuple(sorted(Counter(new_colors).values()))
        history.append((new_colors[root], sizes))
        if new_colors == colors:
            colors = new_colors
            break
        colors = new_colors
    classes = max(colors) + 1
    class_sizes = tuple(Counter(colors)[i] for i in range(classes))
    quotient = [[0] * classes for _ in range(classes)]
    for u in range(n):
        for v in adj[u]:
            quotient[colors[u]][colors[v]] += 1
    return (tuple(history), class_sizes, tuple(tuple(row) for row in quotient))


def canonical_key(inst: dict) -> str:
    """Label/order-invariant rooted-colour-refinement key for the graph."""
    n = inst["vertex_count"]
    adj = [[] for _ in range(n)]
    for a, b in inst["edges"]:
        u, v = a - 1, b - 1
        adj[u].append(v)
        adj[v].append(u)
    signatures = sorted(_root_signature(adj, root) for root in range(n))
    payload = repr((n, len(inst["edges"]), signatures)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Increase crowding at fixed witness length, then grow to the token cap."""
    if "n" not in params:
        return None
    n = int(params["n"])
    marked_fraction = float(params.get("marked_fraction", 0.25))
    # n=48 with three marked claws has 153 edges.  n=30 with four marked
    # claws also has 153 edges, but one more crowded co-fish choice: Algorithm X
    # still failed 8/8 capped runs and took 109.3 s rather than 47.2 s total.
    if n >= 48 and marked_fraction <= 0.25:
        out = dict(params)
        out["n"] = 30
        out["claw_fraction"] = 0.50
        out["marked_fraction"] = 0.50
        return out
    # Once crowding is raised, use the remaining answer budget to enlarge the
    # random core while keeping four anchors: 180 IDs, 481 conservative tokens.
    if n == 30 and marked_fraction >= 0.49:
        out = dict(params)
        out["n"] = 48
        out["claw_fraction"] = 0.50
        out["marked_fraction"] = 0.34
        return out
    # Another group would exceed the conservative 500-token answer cap.
    return "cap_bound"


def _greedy_attack(inst: dict, mode: str, rng: random.Random | None = None) -> list[list[int]] | None:
    pieces = _valid_pieces(inst)
    m = len(inst["edges"])
    by_edge = [[] for _ in range(m)]
    for row, part in enumerate(pieces):
        for e in part:
            by_edge[e].append(row)
    used = [False] * m
    chosen: list[int] = []
    while len(chosen) * 3 < m:
        choices = []
        for e in range(m):
            if used[e]:
                continue
            opts = [r for r in by_edge[e] if not any(used[x] for x in pieces[r])]
            if not opts:
                return None
            choices.append((len(opts), e, opts))
        _, _, opts = min(choices, key=lambda x: (x[0], x[1]))
        if mode == "random":
            assert rng is not None
            row = rng.choice(opts)
        else:
            # Prefer the row whose other edges are currently most constrained.
            def score(r: int) -> tuple[int, tuple[int, int, int]]:
                freedom = 0
                for x in pieces[r]:
                    freedom += sum(
                        1 for rr in by_edge[x]
                        if not any(used[y] for y in pieces[rr])
                    )
                return freedom, pieces[r]
            row = min(opts, key=score)
        for e in pieces[row]:
            used[e] = True
        chosen.append(row)
    return [[e + 1 for e in pieces[r]] for r in chosen]


def _outlier_attack(inst: dict) -> list[list[int]] | None:
    """Pick claws at vertices incident with the most graph bridges, then greedily fill."""
    n = inst["vertex_count"]
    edges = [(a - 1, b - 1) for a, b in inst["edges"]]
    adj: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    for eid, (u, v) in enumerate(edges):
        adj[u].append((v, eid))
        adj[v].append((u, eid))
    tin = [-1] * n
    low = [0] * n
    bridges: set[int] = set()
    clock = 0

    def dfs(u: int, parent_edge: int) -> None:
        nonlocal clock
        tin[u] = low[u] = clock
        clock += 1
        for v, eid in adj[u]:
            if eid == parent_edge:
                continue
            if tin[v] >= 0:
                low[u] = min(low[u], tin[v])
            else:
                dfs(v, eid)
                low[u] = min(low[u], low[v])
                if low[v] > tin[u]:
                    bridges.add(eid)

    dfs(0, -1)
    # The co-fish-adjacent old centres are distance two from three bridges.
    scores = []
    for u in range(n):
        score = sum(1 for v, _ in adj[u] for _, e2 in adj[v] if e2 in bridges)
        scores.append((score, u))
    forced_edges: set[int] = set()
    for score, u in scores:
        if score >= 3:
            forced_edges.update(e for _, e in adj[u])
    pieces = _valid_pieces(inst)
    chosen = [i for i, p in enumerate(pieces) if set(p) == forced_edges] if len(forced_edges) == 3 else []
    # Usually there are multiple suspicious centres; committing all of them is
    # intentionally an aggressive construction-aware heuristic.
    if len(forced_edges) > 3:
        chosen = []
        for score, u in scores:
            if score >= 3:
                target = tuple(sorted(e for _, e in adj[u]))
                try:
                    chosen.append(pieces.index(target))
                except ValueError:
                    return None
    used: set[int] = set()
    answer: list[list[int]] = []
    for row in chosen:
        if used.intersection(pieces[row]):
            return None
        used.update(pieces[row])
        answer.append([e + 1 for e in pieces[row]])
    # Finish without backtracking by minimum-column greedy.
    by_edge = [[] for _ in edges]
    for row, part in enumerate(pieces):
        for e in part:
            by_edge[e].append(row)
    while len(used) < len(edges):
        best = None
        for e in range(len(edges)):
            if e in used:
                continue
            opts = [r for r in by_edge[e] if not used.intersection(pieces[r])]
            if not opts:
                return None
            item = (len(opts), e, opts)
            if best is None or item[:2] < best[:2]:
                best = item
        assert best is not None
        row = min(best[2], key=lambda r: pieces[r])
        used.update(pieces[row])
        answer.append([e + 1 for e in pieces[row]])
    return answer


def _transformed_instance(inst: dict, vertex_perm: list[int], edge_order: list[int]) -> tuple[dict, list[list[int]]]:
    """Relabel vertices/reorder edges and carry the planted answer through."""
    old_edges = inst["edges"]
    new_edges_unordered = [
        [vertex_perm[u - 1] + 1, vertex_perm[v - 1] + 1] for u, v in old_edges
    ]
    new_edges = [new_edges_unordered[i] for i in edge_order]
    old_to_new = {old: new + 1 for new, old in enumerate(edge_order)}
    answer = [[old_to_new[e - 1] for e in part] for part in inst["answer"]]
    out = dict(inst)
    out["edges"] = new_edges
    out["answer"] = answer
    return out, answer


def _answer_atom_count(value: object) -> int:
    if isinstance(value, list):
        return sum(_answer_atom_count(item) for item in value)
    if isinstance(value, dict):
        return sum(_answer_atom_count(item) for item in value.values())
    return 1


def _conservative_json_tokens(value: object) -> int:
    """Count every number and punctuation mark as a token (an upper estimate)."""
    payload = json.dumps(value, separators=(",", ":"))
    return len(re.findall(r"-?\d+|[^\s]", payload))


def selftest() -> dict:
    """Run the mandatory G1--G9 gates and return JSON-serialisable evidence."""
    report: dict = {}

    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, why])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "verified": g1_attempts - len(g1_failures),
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    inst = make_instance(seed=91, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = [p[:] for p in inst["answer"]]
    corruptions: dict[str, object] = {}
    drop = [p[:] for p in planted]
    drop[0] = drop[0][:-1]
    corruptions["drop_one"] = drop
    duplicate = [p[:] for p in planted]
    duplicate[0][1] = duplicate[0][0]
    corruptions["duplicate"] = duplicate
    corruptions["empty"] = []
    out_of_range = [p[:] for p in planted]
    out_of_range[0][0] = len(inst["edges"]) + 1
    corruptions["out_of_range"] = out_of_range
    swapped = None
    for i in range(len(planted)):
        for j in range(i + 1, len(planted)):
            for a in range(3):
                for b in range(3):
                    trial = [p[:] for p in planted]
                    trial[i][a], trial[j][b] = trial[j][b], trial[i][a]
                    ok, why = verify(inst, trial)
                    if not ok and why.startswith("invalid_shape"):
                        swapped = trial
                        break
                if swapped is not None:
                    break
            if swapped is not None:
                break
        if swapped is not None:
            break
    corruptions["swap_between_groups"] = swapped
    g2_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        g2_results[name] = {"rejected": not ok, "reason": why}
        reasons.append(why.split(":", 1)[0])
    report["G2_rejects_corruption"] = {
        "pass": swapped is not None and all(x["rejected"] for x in g2_results.values()) and len(set(reasons)) == len(reasons),
        "cases": g2_results,
        "distinct_reasons": len(set(reasons)),
    }

    response = "I checked every edge.\n```json\n<answer>\n" + json.dumps(planted) + "\n</answer>\n```\nDone."
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "realistic_response_parsed": parsed is not None,
        "equal_to_witness": parsed == planted,
    }

    guess_rng = random.Random(20260428)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            guess_hits += 1
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "measured_probability": guess_hits / guess_total,
        "sampler": "uniform edge partitions into unordered triples; exact coverage, arity, and no repetition pre-enforced",
        "naive_search_space": search_space(inst),
    }

    # Keep the old exact small-instance count only as supplementary context.
    # The mandatory G5 density and baseline cost below both use shipping inputs.
    small = make_instance(n=12, seed=7, claw_fraction=0.5, marked_fraction=0.0)
    exact_count = enumerate_all(small)
    small_space = search_space(small)
    small_fraction = None if exact_count is None else exact_count / small_space

    attack_names = [
        "outlier_cofish_neighbourhood",
        "greedy_min_column",
        "random_restart_256",
        "algorithm_x_200k_nodes",
    ]
    attack_success = {name: 0 for name in attack_names}
    attack_attempts = {name: 0 for name in attack_names}
    attack_nodes = []
    for seed in range(100, 108):
        target = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates: dict[str, object | None] = {
            "outlier_cofish_neighbourhood": _outlier_attack(target),
            "greedy_min_column": _greedy_attack(target, "greedy"),
        }
        rr_answer = None
        rr_rng = random.Random(900_000 + seed)
        for _ in range(256):
            rr_answer = _greedy_attack(target, "random", rr_rng)
            if rr_answer is not None and verify(target, rr_answer)[0]:
                break
        candidates["random_restart_256"] = rr_answer
        attack_started = time.perf_counter()
        exact_answer, _, nodes, exhausted = _exact_cover(target, node_limit=200_000)
        attack_wall_seconds = time.perf_counter() - attack_started
        attack_nodes.append(
            {
                "seed": seed,
                "nodes": nodes,
                "exhausted": exhausted,
                "wall_seconds": attack_wall_seconds,
            }
        )
        candidates["algorithm_x_200k_nodes"] = exact_answer
        for name in attack_names:
            attack_attempts[name] += 1
            candidate = candidates[name]
            if candidate is not None and verify(target, candidate)[0]:
                attack_success[name] += 1
    attacks = {
        name: {"successes": attack_success[name], "attempts": attack_attempts[name]}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(row["successes"] == 0 for row in attacks.values()),
        "attacks": attacks,
        "domain_attack": "Algorithm X exact-cover search with minimum-column branching",
        "algorithm_x_runs": attack_nodes,
    }

    density_fraction = guess_hits / guess_total
    density_upper_95 = -math.expm1(math.log(0.05) / guess_total) if guess_hits == 0 else None
    baseline_total_nodes = sum(run["nodes"] for run in attack_nodes)
    baseline_wall_seconds = sum(run["wall_seconds"] for run in attack_nodes)
    baseline_success_count = attack_success["algorithm_x_200k_nodes"]
    baseline_succeeded = baseline_success_count > 0
    report["G5_sparse"] = {
        "pass": (
            density_upper_95 is not None
            and density_upper_95 < 1e-4
            and all(run["nodes"] == 200_000 for run in attack_nodes)
            and not baseline_succeeded
        ),
        "shipping_preset": SHIPPING_DIFFICULTY,
        # Direct numeric summaries keep the G5 evidence mechanically visible;
        # the nested records below retain the measurement protocol and runs.
        "shipping_observed_valid_fraction": density_fraction,
        "shipping_density_sample_count": guess_total,
        "baseline_wall_seconds": baseline_wall_seconds,
        "baseline_total_nodes": baseline_total_nodes,
        "baseline_success_count": baseline_success_count,
        "density": {
            "base_n": DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
            "instance_seed": 91,
            "instance_edges": len(inst["edges"]),
            "sampler_seed": 20260428,
            "hits": guess_hits,
            "sample_size": guess_total,
            "observed_fraction": density_fraction,
            "one_sided_95_percent_upper_bound": density_upper_95,
            "candidate_space": search_space(inst),
            "sampler": "random_candidate: uniform unordered triple partitions",
        },
        "baseline_cost": {
            "attack": "Algorithm X exact cover with minimum-column branching",
            "shipping_runs": len(attack_nodes),
            "node_limit_per_run": 200_000,
            "total_nodes": baseline_total_nodes,
            "wall_seconds": baseline_wall_seconds,
            "successful_runs": baseline_success_count,
            "succeeded": baseline_succeeded,
            "runs": attack_nodes,
        },
        "supplementary_exact_count": {
            "base_n": 12,
            "instance_seed": 7,
            "instance_edges": len(small["edges"]),
            "valid_answers": exact_count,
            "candidate_space": small_space,
            "solution_fraction": small_fraction,
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    normal = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    report["G7_scales"] = {
        "pass": doubled_ok and len(doubled["edges"]) > len(normal["edges"]),
        "base_n": DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        "doubled_n": doubled_params["n"],
        "base_edges": len(normal["edges"]),
        "doubled_edges": len(doubled["edges"]),
        "doubled_verify": doubled_why,
    }

    invariance_checks = 0
    real_transform_checks = 0
    invariant_failures = []
    keys = []
    for seed in range(20):
        sample = make_instance(n=20, seed=10_000 + seed, claw_fraction=0.5, marked_fraction=0.2)
        key = canonical_key(sample)
        keys.append(key)
        trng = random.Random(70_000 + seed)
        vperm = list(range(sample["vertex_count"]))
        eorder = list(range(len(sample["edges"])))
        trng.shuffle(vperm)
        trng.shuffle(eorder)
        variants = [
            _transformed_instance(sample, vperm, list(range(len(eorder)))),
            _transformed_instance(sample, list(range(len(vperm))), eorder),
            _transformed_instance(sample, vperm, eorder),
        ]
        for changed, carried_answer in variants:
            invariance_checks += 1
            if canonical_key(changed) != key:
                invariant_failures.append(seed)
            ok, _ = verify(changed, carried_answer)
            real_transform_checks += 1
            if not ok:
                invariant_failures.append(f"verify-{seed}")
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and distinct == 20,
        "invariance_checks": invariance_checks,
        "real_transform_verify_checks": real_transform_checks,
        "distinct_unrelated": distinct,
        "unrelated_attempts": 20,
        "failures": invariant_failures,
        "transformations": ["vertex permutation", "edge-row permutation", "their composition"],
        "key_kind": "multiset of rooted colour-refinement quotients (strong invariant, not complete GI)",
    }

    size_samples = [
        make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])["answer"]
        for seed in range(32)
    ]
    answer_chars = max(len(json.dumps(a, separators=(",", ":"))) for a in size_samples)
    answer_tokens = max(_conservative_json_tokens(a) for a in size_samples)
    answer_elements = max(_answer_atom_count(a) for a in size_samples)
    intended_route_operations = len(inst["edges"])
    hinted_attempts = G9_ARM_RESULTS["hinted"]["attempts"]
    placebo_attempts = G9_ARM_RESULTS["placebo"]["attempts"]
    hinted_minus_placebo = None
    if hinted_attempts and placebo_attempts:
        hinted_minus_placebo = (
            G9_ARM_RESULTS["hinted"]["solved"] / hinted_attempts
            - G9_ARM_RESULTS["placebo"]["solved"] / placebo_attempts
        )
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_route_operations <= 300
        and answer_tokens <= 500
    )
    report["G9_no_tool_suitability"] = {
        "pass": G9_HINTED_VERDICT == "hardened" and within_caps,
        "arms": G9_ARM_RESULTS,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_HINTED_VERDICT,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_route_operations,
        "operation_definition": "one exact edge-placement/accounting operation per edge after structural choices",
        "caps": {"chars": 2_000, "tokens": 500, "atomic_elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
