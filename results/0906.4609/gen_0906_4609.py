"""Verified generator for critical maximum independent sets.

The source is arXiv:0906.4609, especially Proposition 1.3 and Theorem 2.7.
Each instance supplies a graph and a matching that misses one vertex.  The
certificate is an independent set containing that vertex and one endpoint of
every matching edge.  The equality |I| + |M| = |V| proves at once that I and M
are maximum and that the graph is Konig--Egervary.  Theorem 2.7 identifies I as
a critical independent set.

Generation samples the independent-set orientation first and adds only edges
that preserve it.  It never solves the graph it has just made.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time


TRACK = "B"


PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite simple graph",
        "matching with one exposed vertex",
        "critical maximum independent set",
    ],
    "verification_operations": [
        "exact edge membership",
        "matching endpoint distinctness",
        "exact neighborhood cardinality",
        "integer cardinality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Use equality in the matching bound to orient every matching edge from "
        "the exposed vertex's alternating-reachability class; without that "
        "invariant one must solve the full independent-transversal instance."
    ),
    "hardness_basis": (
        "Track B: the supplied near-perfect matching reduces the search to 2-SAT, "
        "solvable by implication-graph SCCs in O(|V|+|E|); at shipping n=96, "
        "seed 271828, this took 5,373 implication/DFS arc operations and 0.000904 "
        "seconds, while the planted alternating closure uses 96 forced "
        "matching-edge orientations."
    ),
    "max_answer_tokens": 97,
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
        "A JSON list representing an independent set of the required size. "
        "Because the displayed matching has one exposed vertex, a "
        "structure-aware candidate contains that exposed vertex and exactly "
        "one endpoint of each matching edge."
    ),
    "bounds": {
        "length": "number of matching edges plus one",
        "entries": "distinct vertex labels in 0..|V|-1",
        "required_exposed_vertices": 1,
        "choices_per_matching_edge": 2,
        "candidate_count": "2^|M|",
    },
}


DIFFICULTY = {
    "demo": {"n": 6, "block_size": 3, "cross_percent": 70, "internal_percent": 15},
    "easy": {"n": 96, "block_size": 16, "cross_percent": 50, "internal_percent": 15},
    "medium": {"n": 112, "block_size": 14, "cross_percent": 50, "internal_percent": 15},
    "hard": {"n": 128, "block_size": 16, "cross_percent": 50, "internal_percent": 15},
}

SHIPPING_DIFFICULTY = "easy"


STRUCTURAL_HINT = (
    "Equality in the matching bound makes the exposed vertex's alternating-reachability "
    "class a forced orientation of the matching edges."
)
PLACEBO_HINT = (
    "The vertex and adjacency lists use exact zero-based labels, making careful "
    "bookkeeping across the matching edges important."
)


# Filled only from transcripts produced by scripts/harden.py.  The three arms
# are diagnostics under the current protocol; only the local size/effort caps
# in G9(c) gate shipment.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 1, "attempts": 3},
    "hinted": {"solved": None, "attempts": 3},
    "placebo": {"solved": None, "attempts": 3},
    "hinted_verdict": "pending",
}


NOTES = r"""
Section 1 fixes the exact objects: a finite undirected loopless simple graph,
independent sets, matchings, critical difference, and Konig--Egervary equality.
Proposition 1.3 supplies the construction certificate: a maximum independent
set at least as large as the complementary side, together with a matching that
saturates that side.  Theorem 2.7 is the paper's main characterization: in a
Konig--Egervary graph every maximum independent set is critical.

The easy-result triage is decisive.  Page 2 explicitly says that a critical
independent set is polynomial-time computable, and the displayed matching makes
this particular search an even simpler 2-SAT instance: equality forces the
exposed vertex and one endpoint per matching edge.  Thus Track A would be false.
Track B is honest about the linear-time SCC reference algorithm.

Generation samples a hidden orientation of every matching pair, makes those
oriented vertices independent, and inserts dense same-distribution constraint
blocks plus a sparse chain between them.  The exposed vertex seeds the planted
orientation.  Cross edges and matching edges are sampled only after the witness
exists; edges inside the complementary side make the graph non-bipartite without
damaging the witness.  Relabelling erases construction positions.

The degree/outlier attack sees overlapping endpoint-degree distributions; the
static greedy encounters blocks before their forcing bridge; one-hop propagation
stops after only the first block; and random matching orientations have one
valid point among 2^|M|.  All are measured on eight shipping seeds.  The standard
2-SAT SCC algorithm is expected to solve and is reported separately.
""".strip()


def _edge(u, v):
    if u == v:
        raise ValueError("loops are not allowed")
    return (u, v) if u < v else (v, u)


def _adjacency(inst):
    adjacency = [[] for _ in range(inst["n_vertices"])]
    for u, v in inst["edges"]:
        adjacency[u].append(v)
        adjacency[v].append(u)
    for row in adjacency:
        row.sort()
    return adjacency


def _matching_maps(inst):
    mate = {}
    for u, v in inst["matching"]:
        mate[u] = v
        mate[v] = u
    exposed = [v for v in range(inst["n_vertices"]) if v not in mate]
    return mate, exposed


def make_instance(n, seed=0, **params):
    """Inverse-generate a non-bipartite Konig--Egervary graph.

    ``n`` is the number of matching pairs.  The answer, including the sole
    exposed vertex, is sampled before any nonmatching edge is created.
    """

    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    block_size = params.pop("block_size", max(2, min(16, n)))
    cross_percent = params.pop("cross_percent", 80)
    internal_percent = params.pop("internal_percent", 15)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(block_size, bool) or not isinstance(block_size, int):
        raise ValueError("block_size must be an integer")
    if block_size < 2 or n % block_size:
        raise ValueError("block_size must divide n and be at least 2")
    if not (1 <= cross_percent <= 100):
        raise ValueError("cross_percent must be in 1..100")
    if not (0 <= internal_percent <= 100):
        raise ValueError("internal_percent must be in 0..100")

    rng = random.Random(seed)
    unmatched = 0
    first_side = list(range(1, n + 1))
    second_side = list(range(n + 1, 2 * n + 1))

    # Choose the certificate orientation first.  Swapping pair endpoints makes
    # the planted endpoint locally unbiased before graph edges are sampled.
    planted = [unmatched]
    complement = []
    pairs = []
    for i in range(n):
        a, b = first_side[i], second_side[i]
        if rng.getrandbits(1):
            a, b = b, a
        planted.append(a)
        complement.append(b)
        pairs.append((a, b))

    edges = set()
    for a, b in pairs:
        edges.add(_edge(a, b))

    blocks = [list(range(start, start + block_size)) for start in range(0, n, block_size)]

    # Dense implication blocks.  The directed interpretation is only for the
    # construction: an undirected edge joins a planted endpoint in pair i to a
    # complementary endpoint in pair j.  A cycle makes every block one forcing
    # class even if the random part is unlucky.
    for block in blocks:
        for offset, i in enumerate(block):
            j = block[(offset + 1) % len(block)]
            edges.add(_edge(planted[i + 1], complement[j]))
        for i in block:
            for j in block:
                if rng.randrange(100) < cross_percent:
                    edges.add(_edge(planted[i + 1], complement[j]))

        # Guaranteed triangle on the complementary side makes the instances
        # genuinely non-bipartite while leaving the planted set untouched.
        j0, j1 = block[0], block[1]
        edges.add(_edge(complement[j0], complement[j1]))
        edges.add(_edge(planted[j0 + 1], complement[j1]))
        for left_pos in range(len(block)):
            for right_pos in range(left_pos + 1, len(block)):
                if rng.randrange(100) < internal_percent:
                    edges.add(_edge(complement[block[left_pos]], complement[block[right_pos]]))

    # The exposed vertex fixes the polarity of the first block.  One bridge per
    # adjacent block carries that polarity through the whole instance.
    edges.add(_edge(unmatched, complement[blocks[0][0]]))
    for block_index in range(len(blocks) - 1):
        source = blocks[block_index][-1]
        target = blocks[block_index + 1][0]
        edges.add(_edge(planted[source + 1], complement[target]))

    # Random vertex relabelling destroys all construction positions.  It is a
    # structure-preserving transformation and carries both certificates.
    vertex_count = 2 * n + 1
    permutation = list(range(vertex_count))
    rng.shuffle(permutation)
    relabelled_edges = sorted({_edge(permutation[u], permutation[v]) for u, v in edges})
    relabelled_matching = [
        [permutation[u], permutation[v]] for u, v in pairs
    ]
    rng.shuffle(relabelled_matching)
    answer = sorted(permutation[v] for v in planted)

    return {
        "n_vertices": vertex_count,
        "edges": [[u, v] for u, v in relabelled_edges],
        "matching": relabelled_matching,
        "target_size": n + 1,
        "critical_difference": 1,
        "block_size": block_size,
        "cross_percent": cross_percent,
        "internal_percent": internal_percent,
        "answer": answer,
    }


def render(inst):
    adjacency = _adjacency(inst)
    lines = [
        "Find a critical maximum independent set in a finite graph.",
        "",
        "The graph is finite, undirected, loopless, and has no repeated edges.  Its",
        f"vertices are the integers 0 through {inst['n_vertices'] - 1}, inclusive.  A set",
        "is independent when no displayed graph edge has both endpoints in the set.",
        "For a vertex set S, its open neighborhood N(S) consists of vertices outside S",
        "adjacent to at least one vertex of S.  Its difference is |S|-|N(S)|.  A",
        "critical independent set maximizes this difference among all independent sets.",
        "",
        "A matching is a collection of edges with no shared endpoint.  The matching",
        "displayed below leaves exactly one graph vertex exposed (not in any matching",
        "edge).  Any independent set contains at most one endpoint from each matching",
        "edge.  Consequently an independent set of the required size below is maximum,",
        "and equality in this matching bound certifies that its difference is 1 and is",
        "the largest possible.  Thus no unexecutable theorem is needed by the checker.",
        "",
        f"Required set size: {inst['target_size']}",
        "",
        "Matching edges (unordered pairs; the line order and endpoint order carry no meaning):",
    ]
    packed = []
    for u, v in inst["matching"]:
        packed.append(f"({u},{v})")
    width = 8
    for start in range(0, len(packed), width):
        lines.append("  " + " ".join(packed[start:start + width]))
    lines.extend([
        "",
        "Complete adjacency list (each undirected edge therefore appears in both rows):",
    ])
    for vertex, neighbors in enumerate(adjacency):
        lines.append(f"  {vertex}: " + " ".join(map(str, neighbors)))
    lines.extend([
        "",
        f"Return exactly {inst['target_size']} distinct vertex labels in increasing order.",
        "Order is fixed only to make grading unambiguous; repeats and omitted vertices are",
        "not allowed.  Use a JSON list of decimal integers, with no ellipsis.",
        "",
        "Give your final answer inside <answer></answer> tags, as the JSON list just specified.",
        "Example: <answer>[0,2,5]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    try:
        tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
        if tagged:
            payload = tagged[-1].strip()
        else:
            fenced = re.findall(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text, re.I)
            if fenced:
                payload = fenced[-1]
            else:
                lists = re.findall(r"\[[\s\d,\-+]*\]", text)
                if not lists:
                    return None
                payload = lists[-1]
        value = json.loads(payload)
        if not isinstance(value, list):
            return None
        if any(isinstance(v, bool) or not isinstance(v, int) for v in value):
            return None
        return value
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _validate_instance(inst):
    try:
        vertex_count = inst["n_vertices"]
        edges = inst["edges"]
        matching = inst["matching"]
        target = inst["target_size"]
    except (KeyError, TypeError):
        return False, "malformed instance"
    if isinstance(vertex_count, bool) or not isinstance(vertex_count, int) or vertex_count < 1:
        return False, "malformed vertex count"
    edge_set = set()
    for item in edges:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            return False, "malformed graph edge"
        u, v = item
        if any(isinstance(x, bool) or not isinstance(x, int) for x in (u, v)):
            return False, "noninteger graph endpoint"
        if not (0 <= u < vertex_count and 0 <= v < vertex_count) or u >= v:
            return False, "graph edge is out of range, reversed, or a loop"
        if (u, v) in edge_set:
            return False, "repeated graph edge"
        edge_set.add((u, v))
    covered = set()
    for item in matching:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            return False, "malformed matching edge"
        u, v = item
        if any(isinstance(x, bool) or not isinstance(x, int) for x in (u, v)):
            return False, "noninteger matching endpoint"
        if not (0 <= u < vertex_count and 0 <= v < vertex_count):
            return False, "matching endpoint out of range"
        if u == v or u in covered or v in covered:
            return False, "matching edges share an endpoint"
        if _edge(u, v) not in edge_set:
            return False, "matching pair is not a graph edge"
        covered.update((u, v))
    if vertex_count - len(covered) != 1:
        return False, "matching must expose exactly one vertex"
    if target != len(matching) + 1 or target + len(matching) != vertex_count:
        return False, "target does not meet the matching equality"
    return True, "ok"


def verify(inst, answer):
    valid, reason = _validate_instance(inst)
    if not valid:
        return False, reason
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if any(isinstance(v, bool) or not isinstance(v, int) for v in answer):
        return False, "every answer entry must be an integer"
    if len(set(answer)) != len(answer):
        return False, "answer contains a duplicate vertex"
    if any(v < 0 or v >= inst["n_vertices"] for v in answer):
        return False, "answer contains an out-of-range vertex"
    if answer != sorted(answer):
        return False, "answer vertices must be in increasing order"
    if len(answer) != inst["target_size"]:
        return False, f"wrong length: expected {inst['target_size']} vertices"
    chosen = set(answer)
    for u, v in inst["edges"]:
        if u in chosen and v in chosen:
            return False, f"not independent: graph edge ({u},{v}) is internal"
    neighborhood = set()
    for u, v in inst["edges"]:
        if u in chosen and v not in chosen:
            neighborhood.add(v)
        elif v in chosen and u not in chosen:
            neighborhood.add(u)
    difference = len(chosen) - len(neighborhood)
    if difference != inst["critical_difference"]:
        return False, f"wrong difference: got {difference}"
    return True, "ok"


def random_candidate(inst, rng):
    mate, exposed = _matching_maps(inst)
    if len(exposed) != 1:
        return []
    answer = list(exposed)
    for u, v in inst["matching"]:
        answer.append((u, v)[rng.getrandbits(1)])
    return sorted(answer)


def search_space(inst):
    return 1 << len(inst["matching"])


def _candidate_valid_fast(inst, answer, edge_set=None):
    if len(answer) != inst["target_size"] or len(set(answer)) != len(answer):
        return False
    chosen = set(answer)
    if edge_set is None:
        edge_set = inst["edges"]
    return not any(u in chosen and v in chosen for u, v in edge_set)


def enumerate_all(inst):
    pair_count = len(inst["matching"])
    if pair_count > 22:
        return None
    _, exposed = _matching_maps(inst)
    if len(exposed) != 1:
        return 0
    edges = inst["edges"]
    valid = 0
    for mask in range(1 << pair_count):
        candidate = list(exposed)
        for index, pair in enumerate(inst["matching"]):
            candidate.append(pair[(mask >> index) & 1])
        if _candidate_valid_fast(inst, candidate, edges):
            valid += 1
    return valid


def canonical_key(inst):
    """Typed 1-WL fingerprint of the graph with its displayed matching marked."""

    vertex_count = inst["n_vertices"]
    graph_neighbors = [set() for _ in range(vertex_count)]
    for u, v in inst["edges"]:
        graph_neighbors[u].add(v)
        graph_neighbors[v].add(u)
    matching_neighbors = [set() for _ in range(vertex_count)]
    matching_set = set()
    for u, v in inst["matching"]:
        matching_neighbors[u].add(v)
        matching_neighbors[v].add(u)
        matching_set.add(_edge(u, v))

    signatures = [
        (len(matching_neighbors[v]), len(graph_neighbors[v]))
        for v in range(vertex_count)
    ]

    def compress(items):
        ordered = sorted(set(items))
        table = {item: index for index, item in enumerate(ordered)}
        return [table[item] for item in items]

    colors = compress(signatures)
    for _ in range(vertex_count):
        refined = []
        for v in range(vertex_count):
            marked = sorted(colors[w] for w in matching_neighbors[v])
            ordinary = sorted(
                colors[w]
                for w in graph_neighbors[v]
                if _edge(v, w) not in matching_set
            )
            refined.append((colors[v], tuple(marked), tuple(ordinary)))
        new_colors = compress(refined)
        if new_colors == colors:
            break
        colors = new_colors

    vertex_profiles = []
    for v in range(vertex_count):
        vertex_profiles.append([
            colors[v],
            sorted(colors[w] for w in matching_neighbors[v]),
            sorted(
                colors[w]
                for w in graph_neighbors[v]
                if _edge(v, w) not in matching_set
            ),
        ])
    payload = {
        "n": vertex_count,
        "m": len(inst["edges"]),
        "matching": len(inst["matching"]),
        "target": inst["target_size"],
        "profiles": sorted(vertex_profiles, key=lambda x: json.dumps(x, separators=(",", ":"))),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def escalate(params):
    current = dict(params)
    n = int(current.get("n", 96))
    block_size = int(current.get("block_size", 12))
    cross = int(current.get("cross_percent", 80))
    internal = int(current.get("internal_percent", 15))
    if cross < 90:
        current["cross_percent"] = min(90, cross + 5)
        return current
    if internal < 25:
        current["internal_percent"] = min(25, internal + 5)
        return current
    # A larger number of blocks grows the matching-orientation haystack.  The
    # explicit answer remains within 256 atoms through n=248.
    if n + block_size <= 248:
        current["n"] = n + block_size
        return current
    return "cap_bound"


def _compact_closure(inst):
    """Construction-aware alternating closure, with inspected-entry count."""

    adjacency = _adjacency(inst)
    mate, exposed = _matching_maps(inst)
    if len(exposed) != 1:
        return None, 0
    selected = set(exposed)
    oriented = set()
    for vertex in selected:
        oriented.add(vertex)
    queue = list(exposed)
    scans = 0
    head = 0
    while head < len(queue) and len(selected) < inst["target_size"]:
        vertex = queue[head]
        head += 1
        for neighbor in adjacency[vertex]:
            scans += 1
            if neighbor in selected:
                return None, scans
            if neighbor not in mate:
                continue
            chosen = mate[neighbor]
            pair_key = min(neighbor, chosen)
            if pair_key in oriented:
                if neighbor in selected:
                    return None, scans
                continue
            oriented.add(pair_key)
            selected.add(chosen)
            queue.append(chosen)
            if len(selected) == inst["target_size"]:
                break
    candidate = sorted(selected)
    if len(candidate) != inst["target_size"]:
        return None, scans
    return candidate, scans


def _solve_2sat(inst):
    """Reference independent-transversal solver using implication SCCs."""

    pairs = [tuple(pair) for pair in inst["matching"]]
    endpoint = {}
    for index, (u, v) in enumerate(pairs):
        endpoint[u] = (index, 0)
        endpoint[v] = (index, 1)
    exposed = [v for v in range(inst["n_vertices"]) if v not in endpoint]
    size = 2 * len(pairs)
    graph = [[] for _ in range(size)]
    reverse = [[] for _ in range(size)]
    implication_arcs = 0

    def node(variable, value):
        return 2 * variable + value

    def add_arc(source, target):
        nonlocal implication_arcs
        graph[source].append(target)
        reverse[target].append(source)
        implication_arcs += 1

    for u, v in inst["edges"]:
        left = endpoint.get(u)
        right = endpoint.get(v)
        if left is None and right is None:
            return None, {"implication_arcs": implication_arcs, "dfs_arc_scans": 0}
        if left is None:
            variable, value = right
            add_arc(node(variable, value), node(variable, 1 - value))
        elif right is None:
            variable, value = left
            add_arc(node(variable, value), node(variable, 1 - value))
        else:
            lv, lb = left
            rv, rb = right
            if lv == rv:
                continue
            add_arc(node(lv, lb), node(rv, 1 - rb))
            add_arc(node(rv, rb), node(lv, 1 - lb))

    seen = [False] * size
    order = []
    scans = 0

    def dfs1(start):
        nonlocal scans
        stack = [(start, 0)]
        seen[start] = True
        while stack:
            vertex, index = stack[-1]
            if index < len(graph[vertex]):
                neighbor = graph[vertex][index]
                stack[-1] = (vertex, index + 1)
                scans += 1
                if not seen[neighbor]:
                    seen[neighbor] = True
                    stack.append((neighbor, 0))
            else:
                order.append(vertex)
                stack.pop()

    for vertex in range(size):
        if not seen[vertex]:
            dfs1(vertex)

    component = [-1] * size

    def dfs2(start, label):
        nonlocal scans
        stack = [start]
        component[start] = label
        while stack:
            vertex = stack.pop()
            for neighbor in reverse[vertex]:
                scans += 1
                if component[neighbor] == -1:
                    component[neighbor] = label
                    stack.append(neighbor)

    label = 0
    for vertex in reversed(order):
        if component[vertex] == -1:
            dfs2(vertex, label)
            label += 1
    for variable in range(len(pairs)):
        if component[node(variable, 0)] == component[node(variable, 1)]:
            return None, {"implication_arcs": implication_arcs, "dfs_arc_scans": scans}

    candidate = list(exposed)
    for variable, pair in enumerate(pairs):
        value = 1 if component[node(variable, 1)] > component[node(variable, 0)] else 0
        candidate.append(pair[value])
    candidate.sort()
    if not _candidate_valid_fast(inst, candidate):
        # Component numbering conventions differ between equivalent SCC passes;
        # the opposite convention is tested exactly rather than trusted.
        candidate = list(exposed)
        for variable, pair in enumerate(pairs):
            value = 0 if component[node(variable, 1)] > component[node(variable, 0)] else 1
            candidate.append(pair[value])
        candidate.sort()
    return candidate, {"implication_arcs": implication_arcs, "dfs_arc_scans": scans}


def _attack_outlier(inst):
    adjacency = _adjacency(inst)
    _, exposed = _matching_maps(inst)
    candidate = list(exposed)
    for u, v in inst["matching"]:
        candidate.append(min((u, v), key=lambda x: (len(adjacency[x]), x)))
    return sorted(candidate)


def _attack_greedy(inst):
    adjacency = [set(row) for row in _adjacency(inst)]
    _, exposed = _matching_maps(inst)
    selected = set(exposed)
    for u, v in inst["matching"]:
        choices = [x for x in (u, v) if not (adjacency[x] & selected)]
        if choices:
            chosen = min(choices, key=lambda x: (len(adjacency[x]), x))
        else:
            chosen = min((u, v), key=lambda x: (len(adjacency[x]), x))
        selected.add(chosen)
    return sorted(selected)


def _attack_one_hop(inst):
    adjacency = _adjacency(inst)
    mate, exposed = _matching_maps(inst)
    selected = set(exposed)
    forced_pairs = set()
    for vertex in exposed:
        for neighbor in adjacency[vertex]:
            if neighbor in mate:
                chosen = mate[neighbor]
                selected.add(chosen)
                forced_pairs.add(frozenset((neighbor, chosen)))
    for u, v in inst["matching"]:
        if frozenset((u, v)) not in forced_pairs:
            selected.add(min((u, v), key=lambda x: (len(adjacency[x]), x)))
    return sorted(selected)


def _relabeled(
    inst,
    permutation,
    reorder_edges=False,
    reorder_matching=False,
    swap_matching_endpoints=False,
    seed=0,
):
    rng = random.Random(seed)
    result = {
        key: value
        for key, value in inst.items()
        if key not in {"edges", "matching", "answer"}
    }
    edges = [[*_edge(permutation[u], permutation[v])] for u, v in inst["edges"]]
    matching = [[permutation[u], permutation[v]] for u, v in inst["matching"]]
    if swap_matching_endpoints:
        matching = [[v, u] for u, v in matching]
    if reorder_edges:
        rng.shuffle(edges)
    else:
        edges.sort()
    if reorder_matching:
        rng.shuffle(matching)
    result["edges"] = edges
    result["matching"] = matching
    result["answer"] = sorted(permutation[v] for v in inst["answer"])
    return result


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest():
    report = {}

    # G1: all presets, multiple independent seeds, plus JSON-native answers.
    failures = []
    checks = 0
    for preset, kwargs in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **kwargs)
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok or json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=271828, **shipping)
    answer = inst["answer"]

    # G2: five semantically different corruptions and five different reasons.
    corruptions = {
        "drop_one": answer[:-1],
        "duplicate": sorted(answer[:-1] + [answer[0]]),
        "empty": [],
        "out_of_range": sorted(answer[1:] + [inst["n_vertices"]]),
    }
    selected = set(answer)
    flip = list(answer)
    for u, v in inst["matching"]:
        if u in selected:
            flip.remove(u)
            flip.append(v)
            break
        if v in selected:
            flip.remove(v)
            flip.append(u)
            break
    corruptions["flip_one_matching_choice"] = sorted(flip)
    corruption_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        if not ok:
            reasons.append(reason.split(":", 1)[0])
    report["G2_rejects_corruption"] = {
        "pass": all(x["rejected"] for x in corruption_results.values()) and len(set(reasons)) == 5,
        "attempts": len(corruption_results),
        "distinct_reasons": len(set(reasons)),
        "cases": corruption_results,
    }

    # G3: prose, a markdown fence, and the required tags.
    response = (
        "I used the matching bound and checked the neighborhood.\n```text\n"
        + "<answer>"
        + json.dumps(answer)
        + "</answer>\n```\nThe set has the requested size."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer,
        "parsed_equals_answer": parsed == answer,
        "surrounding_prose_and_fence": True,
    }

    # G4 and shipping density: sample the exact matching-orientation language.
    trials = 200_000
    rng = random.Random(0x904609)
    hits = 0
    started = time.perf_counter()
    for _ in range(trials):
        candidate = random_candidate(inst, rng)
        if _candidate_valid_fast(inst, candidate):
            hits += 1
    guess_seconds = time.perf_counter() - started
    report["G4_guess_resistance"] = {
        "pass": hits / trials < 1e-6,
        "hits": hits,
        "total": trials,
        "observed_probability": hits / trials,
        "candidate_space": search_space(inst),
        "candidate_space_bits": len(inst["matching"]),
        "prior": "uniform independent orientation of every displayed matching edge",
        "wall_clock_sec": round(guess_seconds, 6),
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    reference_started = time.perf_counter()
    reference_answer, reference_counts = _solve_2sat(inst)
    reference_seconds = time.perf_counter() - reference_started
    reference_ok = reference_answer is not None and verify(inst, reference_answer)[0]
    baseline_rng = random.Random(424242)
    baseline_started = time.perf_counter()
    baseline_checks = 0
    baseline_success = False
    for _ in range(256):
        baseline_checks += 1
        if _candidate_valid_fast(inst, random_candidate(inst, baseline_rng)):
            baseline_success = True
            break
    baseline_seconds = time.perf_counter() - baseline_started
    reference_operations = (
        reference_counts["implication_arcs"] + reference_counts["dfs_arc_scans"]
    )
    report["G5_density_and_baseline_cost"] = {
        "pass": demo_count is not None and reference_ok,
        "shipping_seed": 271828,
        "shipping_sample_hits": hits,
        "shipping_sample_total": trials,
        "shipping_solution_density": hits / trials,
        "shipping_exact_density": f"1/2^{len(inst['matching'])} (uniqueness follows from the forced block chain)",
        "demo_exact_valid_answers": demo_count,
        "demo_candidate_space": search_space(demo),
        "strongest_failing_attack": "256 uniform matching-orientation restarts",
        "baseline_candidate_checks": baseline_checks,
        "baseline_success": baseline_success,
        "baseline_wall_clock_sec": round(baseline_seconds, 6),
        "reference_wall_clock_sec": round(reference_seconds, 6),
        "reference_operation_count": reference_operations,
    }

    # G6: Track B keeps tool-free failures separate from the successful SCC solver.
    attacks = {
        "outlier_lower_degree": {"successes": 0, "attempts": 8},
        "greedy_matching_order": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "in_context_one_hop_from_exposed": {"successes": 0, "attempts": 8},
    }
    ref_operations = []
    ref_times = []
    compact_operations = []
    compact_successes = 0
    reference_successes = 0
    attack_started = {name: time.perf_counter() for name in attacks}
    attack_elapsed = {name: 0.0 for name in attacks}
    for seed in range(10_000, 10_008):
        current = make_instance(seed=seed, **shipping)
        candidates = {}
        start = time.perf_counter()
        candidates["outlier_lower_degree"] = _attack_outlier(current)
        attack_elapsed["outlier_lower_degree"] += time.perf_counter() - start
        start = time.perf_counter()
        candidates["greedy_matching_order"] = _attack_greedy(current)
        attack_elapsed["greedy_matching_order"] += time.perf_counter() - start
        start = time.perf_counter()
        candidates["in_context_one_hop_from_exposed"] = _attack_one_hop(current)
        attack_elapsed["in_context_one_hop_from_exposed"] += time.perf_counter() - start
        start = time.perf_counter()
        rr_rng = random.Random(seed ^ 0xA5A5A5)
        rr_candidate = None
        for _ in range(256):
            attempt = random_candidate(current, rr_rng)
            if _candidate_valid_fast(current, attempt):
                rr_candidate = attempt
                break
        candidates["random_restart_256"] = rr_candidate
        attack_elapsed["random_restart_256"] += time.perf_counter() - start
        for name, candidate in candidates.items():
            if candidate is not None and verify(current, candidate)[0]:
                attacks[name]["successes"] += 1

        start = time.perf_counter()
        ref_answer, counts = _solve_2sat(current)
        ref_times.append(time.perf_counter() - start)
        ref_operations.append(counts["implication_arcs"] + counts["dfs_arc_scans"])
        if ref_answer is not None and verify(current, ref_answer)[0]:
            reference_successes += 1
        compact_answer, compact_scans = _compact_closure(current)
        compact_operations.append(compact_scans)
        if compact_answer is not None and verify(current, compact_answer)[0]:
            compact_successes += 1
    for name in attacks:
        attacks[name]["wall_clock_sec"] = round(attack_elapsed[name], 6)
    all_failed = all(item["successes"] == 0 and item["attempts"] >= 8 for item in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "2-SAT implication graph solved by Kosaraju SCCs",
            "complexity": "O(|V|+|E|)",
            "solves": f"{reference_successes}/8, as expected",
            "wall_clock_sec": round(sum(ref_times), 6),
            "operations": sum(ref_operations),
            "operation_unit": "implication-arc constructions and DFS arc scans across eight shipping instances",
            "per_instance_operations": ref_operations,
        },
        "intended_compact_route": {
            "name": "alternating closure from the exposed vertex",
            "solves": f"{compact_successes}/8",
            "forced_orientation_operations": shipping["n"],
            "neighbor_entries_examined_max": max(compact_operations),
            "neighbor_entries_examined": compact_operations,
        },
    }

    # G7: double n while keeping the block size and construction distribution.
    doubled = dict(shipping)
    doubled["n"] = 2 * shipping["n"]
    doubled_inst = make_instance(seed=314159, **doubled)
    doubled_ok, doubled_reason = verify(doubled_inst, doubled_inst["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled_inst) > search_space(inst),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "candidate_space_bits_shipping": len(inst["matching"]),
        "candidate_space_bits_doubled": len(doubled_inst["matching"]),
        "doubled_verify_reason": doubled_reason,
    }

    # G8: arbitrary vertex relabelling, both input-order symmetries, and all
    # nonempty compositions are checked on twenty independent graphs.
    invariance = 0
    real_transformations = 0
    key_failures = []
    for seed in range(20):
        base = make_instance(seed=50_000 + seed, **DIFFICULTY["demo"])
        base_key = canonical_key(base)
        rng = random.Random(60_000 + seed)
        permutation = list(range(base["n_vertices"]))
        rng.shuffle(permutation)
        for use_vertex in (False, True):
            for reorder_edges in (False, True):
                for reorder_matching in (False, True):
                    for swap_matching_endpoints in (False, True):
                        if not (
                            use_vertex
                            or reorder_edges
                            or reorder_matching
                            or swap_matching_endpoints
                        ):
                            continue
                        mapping = permutation if use_vertex else list(range(base["n_vertices"]))
                        transformed = _relabeled(
                            base,
                            mapping,
                            reorder_edges=reorder_edges,
                            reorder_matching=reorder_matching,
                            swap_matching_endpoints=swap_matching_endpoints,
                            seed=70_000 + seed,
                        )
                        invariance += 1
                        if canonical_key(transformed) != base_key:
                            key_failures.append({
                                "seed": seed,
                                "transform": [
                                    use_vertex,
                                    reorder_edges,
                                    reorder_matching,
                                    swap_matching_endpoints,
                                ],
                            })
                        carried = transformed["answer"] if use_vertex else base["answer"]
                        if verify(transformed, carried)[0]:
                            real_transformations += 1
    diversity_params = {
        "n": 18,
        "block_size": 3,
        "cross_percent": 70,
        "internal_percent": 15,
    }
    unrelated = [canonical_key(make_instance(seed=80_000 + seed, **diversity_params)) for seed in range(20)]
    report["G8_canonical_key"] = {
        "pass": not key_failures and real_transformations == invariance and len(set(unrelated)) == 20,
        "invariance_checks": invariance,
        "real_transformations_verified": real_transformations,
        "unrelated_attempts": 20,
        "unrelated_distinct_keys": len(set(unrelated)),
        "failures": key_failures,
        "caveat": "typed 1-WL fingerprint, not a complete canonical-labelling algorithm",
    }

    # G9(a,b) are script-owned diagnostics; only (c) is a gate.
    answer_blob = json.dumps(answer, separators=(",", ":"))
    worst_answer = list(range(inst["n_vertices"] - inst["target_size"], inst["n_vertices"]))
    worst_blob = json.dumps(worst_answer, separators=(",", ":"))
    compact_answer, compact_neighbor_scans = _compact_closure(inst)
    compact_ops = len(inst["matching"])
    arms = {
        name: {
            "solved": G9_ORACLE_RESULTS[name]["solved"],
            "attempts": G9_ORACLE_RESULTS[name]["attempts"],
        }
        for name in ("bare", "hinted", "placebo")
    }
    hinted = arms["hinted"]["solved"]
    placebo = arms["placebo"]["solved"]
    hinted_minus_placebo = None
    if isinstance(hinted, int) and isinstance(placebo, int):
        hinted_minus_placebo = hinted / arms["hinted"]["attempts"] - placebo / arms["placebo"]["attempts"]
    within_caps = len(answer_blob) <= 2000 and _answer_atoms(answer) <= 256 and compact_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps and compact_answer is not None,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": len(answer_blob),
        "answer_tokens": math.ceil(len(answer_blob) / 4),
        "answer_elements": _answer_atoms(answer),
        "worst_case_answer_chars": len(worst_blob),
        "worst_case_answer_tokens": math.ceil(len(worst_blob) / 4),
        "intended_route_operations": compact_ops,
        "intended_route_neighbor_entries_read": compact_neighbor_scans,
        "within_caps": within_caps,
    }

    report["paper"] = "arXiv:0906.4609"
    report["family"] = "matching-certified critical maximum independent set"
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
