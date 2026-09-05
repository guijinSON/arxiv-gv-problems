"""Verified Hamiltonian-cycle instances in K_{1,4}-free split graphs.

The native graph class and Hamiltonian witness come from Cai, Guo, Lai and
Zhou, "Tight spectral conditions for the Hamiltonicity of K_{1,r}-free split
graphs" (arXiv:2604.14763).  Instances are inverse-generated from a cubic
Hamiltonian core.  A general, construction-oblivious route uses Edmonds'
maximum-matching algorithm; a short no-tool route detects a repeated modular
edge difference.
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
from collections import Counter


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "K_{1,4}-free split graph",
        "explicit clique/independent-set split partition",
        "Hamiltonian cycle",
    ],
    "verification_operations": [
        "vertex-set equality",
        "exact graph-edge lookup",
        "cyclic adjacency check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "A spanning cycle in the cubic cross-incidence core is the unique large "
        "multiplicity class of modular endpoint differences; without noticing "
        "it, one must compute a perfect matching and splice the complementary cycles."
    ),
    "hardness_basis": (
        "Track B: the construction-oblivious reference route runs Edmonds' blossom "
        "maximum matching in O(n^3), then orients the complementary 2-factor; at "
        "shipping n=94 it averaged 14,690 primitive operations and 0.00064 s over "
        "eight measured instances, whereas the modular-difference route uses at "
        "most 3n=282 exact integer operations and only adjacency lookups thereafter."
    ),
    "max_answer_tokens": 473,
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
    "demo": {"n": 4},
    "easy": {"n": 22},
    "medium": {"n": 46},
    "hard": {"n": 94},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Hint: Compare the modular differences between the two nonhub neighbors "
    "of every clique vertex."
)
PLACEBO_HINT = (
    "Hint: Check the vertex identifiers carefully when reading each listed "
    "cross-neighborhood."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A cyclic ordering of every graph vertex exactly once, beginning with a "
        "clique vertex and with no two independent-set vertices consecutive; "
        "entries are integer vertex IDs in [0,N-1]."
    ),
    "bounds": {
        "cycle_length": "N = 5n/2 + 1",
        "clique_vertices": "3n/2",
        "independent_vertices": "n+1",
        "maximum_shipping_length": 236,
        "maximum_vertex_id": 235,
    },
}

# Filled from the script-owned oracle runs after hardening.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

NOTES = r"""
Definition and theorem. Section 1 of arXiv:2604.14763 defines a split graph
G=(K,I), K_{1,r}-freeness, and Hamiltonian cycles. Theorem 1.2 states that every
3-connected K_{1,4}-free split graph is Hamiltonian; Section 4 explicitly uses
that result when it observes that minimum independent-set degree at least three
makes the graph 3-connected. The paper's new Theorem 1.4 is a sharp spectral
sufficient condition, not a search algorithm, and its proof classifies a
maximum-spectral-radius non-Hamiltonian counterexample through Perron-vector
edge moves and equitable quotient matrices.

Step-0 decision. Track A is unavailable. The paper cites Renjith--Sadagopan,
whose Section 2, Theorem 2.2 gives a polynomial-time Hamiltonian-cycle algorithm
for K_{1,4}-free split graphs; their Section 3 places K_{1,5}-free split graphs
on the NP-complete side of the dichotomy. This module therefore declares Track
B. On this generated subclass, deleting the universal independent vertex turns
the cross-incidence data into a cubic graph F. Any perfect matching M of F
leaves a 2-factor. Orient its cycles, assign every complementary edge to its
head, make one five-vertex path around every edge of M, and join the paths with
clique edges, placing the universal vertex in one join. Edmonds' blossom
algorithm finds M in O(n^3); selftest measures the actual work.

Generation. For even n, choose a unit a modulo n and plant the circulant cycle
{x,x+a}. Add a perfect matching whose individual edges obey the same unit-
difference rule and avoid the planted edges. Make one clique vertex for every
core edge; connect it to the two endpoints and to one universal independent
vertex. Every clique vertex therefore has exactly three independent neighbors,
all sharing the universal vertex, so an induced K_{1,4} is impossible. Every
ordinary independent vertex has degree three, the universal vertex has all
clique vertices as neighbors, and deleting any two vertices leaves the graph
connected. The graph is thus 3-connected and Theorem 1.2 applies. The planted
cycle and matching directly compose into the emitted Hamiltonian cycle; no
generated instance is solved to obtain its answer. Vertex IDs, edge rows, and
neighbor order are shuffled after the witness is known.

Compact route and attacks. Marginally, planted and matching core edges both
have unit modular difference, and every ordinary core vertex has degree three;
there is no per-element degree or parity outlier. Collectively, the n planted
edges share one modular difference, while a matching contributes at most n/2
copies of any difference. That frequency invariant exposes the 2-factor in at
most 3n integer operations. The adversary panel tests degree-outlier matching,
lowest-label greedy matching, 256 random nonbacktracking cycle walks, and the
plausible but wrong smallest-difference ansatz. The full blossom reference is
reported separately because Track B expects it to succeed.

Easy regimes. The cited dichotomy's polynomial K_{1,4}-free side is the reason
this is not Track A. The paper's claw-free case is easier still: Theorem 1.1
says Hamiltonicity is equivalent to 2-connectivity, and the large claw-free
split graphs in its proof have disjoint independent neighborhoods. The module
uses the K_{1,4}-free boundary, keeps n growing, and avoids the fixed-|I| cases
handled explicitly at the start of the proof of Theorem 1.4.

Canonicalization. The instance is an annotated graph: ordinary independent
vertices carry residues modulo n. Vertex IDs and input order are irrelevant,
and a global affine change x -> ux+t of all residues is a family symmetry. The
key recovers the high-multiplicity core cycle, represents the remaining perfect
matching as a chord diagram, and minimizes that representation over every
rotation and reflection. Hence it is invariant under ID renaming, row order,
neighbor order, and affine residue changes. Residue annotations distinguish the
intended cycle; the key does not claim to solve unannotated cubic graph
isomorphism.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 600_000


def _validate_n(n: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 4 or n % 2:
        raise ValueError("n must be an even integer at least 4")


def _canonical_difference(a: int, b: int, modulus: int) -> int:
    d = (a - b) % modulus
    return min(d, (-d) % modulus)


def _sample_matching(
    n: int, step_difference: int, rng: random.Random
) -> list[tuple[int, int]]:
    """Sample a parity-crossing perfect matching with unit differences.

    At n=4 the two diagonals are the unique completion of the four-cycle and
    are used only by the hand-scale demo.  For larger n, a shuffled bijection
    from evens to odds is rejected unless every edge has unit difference and
    is not a planted cycle edge.  For the shipping ladder the acceptance
    probability is bounded away from zero.  The deterministic affine fallback
    keeps make_instance total for less friendly even sizes.
    """
    if n == 4:
        return [(0, 2), (1, 3)]
    evens = list(range(0, n, 2))
    odds = list(range(1, n, 2))
    for _ in range(20_000):
        shuffled = odds[:]
        rng.shuffle(shuffled)
        pairs = list(zip(evens, shuffled))
        if all(
            math.gcd(abs(u - v), n) == 1
            and _canonical_difference(u, v, n) != step_difference
            for u, v in pairs
        ):
            return pairs

    alternatives = [
        d
        for d in range(1, n)
        if math.gcd(d, n) == 1
        and _canonical_difference(0, d, n) != step_difference
    ]
    if not alternatives:
        raise ValueError("n has no unit-difference matching disjoint from the cycle")
    offset = rng.choice(alternatives)
    return [(u, (u + offset) % n) for u in evens]


def _compose_cycle(
    n: int,
    step: int,
    cycle_edge_id: dict[frozenset[int], int],
    matching: list[tuple[int, int]],
    matching_edge_id: dict[frozenset[int], int],
    hub: int,
    rng: random.Random,
) -> list[int]:
    incoming = {
        v: cycle_edge_id[frozenset(((v - step) % n, v))] for v in range(n)
    }
    pairs = matching[:]
    rng.shuffle(pairs)
    answer: list[int] = []
    for u, v in pairs:
        if rng.randrange(2):
            u, v = v, u
        answer.extend(
            [incoming[u], u, matching_edge_id[frozenset((u, v))], v, incoming[v]]
        )
    answer.append(hub)
    return answer


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a Hamiltonian K_{1,4}-free split graph."""
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_n(n)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)

    if n == 4:
        step = 1
    else:
        # Uniform over unit steps: before the global repetition is considered,
        # a planted core edge has the same unit-difference marginal as a decoy.
        units = [a for a in range(1, n) if math.gcd(a, n) == 1]
        step = rng.choice(units)
    step_difference = _canonical_difference(0, step, n)

    cycle_edges = [frozenset((x, (x + step) % n)) for x in range(n)]
    matching = _sample_matching(n, step_difference, rng)
    matching_edges = [frozenset(edge) for edge in matching]
    if len(set(cycle_edges)) != n or set(cycle_edges) & set(matching_edges):
        raise AssertionError("core edge construction is not simple")

    clique_size = 3 * n // 2
    total_vertices = clique_size + n + 1
    base_hub = n
    base_clique = list(range(n + 1, total_vertices))
    rng.shuffle(base_clique)

    records: list[tuple[str, frozenset[int]]] = [
        ("cycle", edge) for edge in cycle_edges
    ] + [("matching", edge) for edge in matching_edges]
    rng.shuffle(records)
    edge_id: dict[frozenset[int], int] = {}
    cycle_edge_id: dict[frozenset[int], int] = {}
    matching_edge_id: dict[frozenset[int], int] = {}
    cross: list[list[object]] = []
    for clique_vertex, (kind, edge) in zip(base_clique, records):
        u, v = tuple(edge)
        edge_id[edge] = clique_vertex
        (cycle_edge_id if kind == "cycle" else matching_edge_id)[edge] = clique_vertex
        neighbors = [base_hub, u, v]
        rng.shuffle(neighbors)
        cross.append([clique_vertex, neighbors])

    base_answer = _compose_cycle(
        n,
        step,
        cycle_edge_id,
        matching,
        matching_edge_id,
        base_hub,
        rng,
    )

    # Relabel only after the certificate has been composed.
    labels = list(range(total_vertices))
    rng.shuffle(labels)
    relabel = {old: labels[old] for old in range(total_vertices)}
    independent = [relabel[v] for v in range(n + 1)]
    clique = [relabel[v] for v in range(n + 1, total_vertices)]
    residue_labels = [[relabel[v], v] for v in range(n)]
    cross_relabeled = [
        [relabel[int(k)], [relabel[int(v)] for v in neighbors]]
        for k, neighbors in cross
    ]
    rng.shuffle(independent)
    rng.shuffle(clique)
    rng.shuffle(residue_labels)
    rng.shuffle(cross_relabeled)
    for _, neighbors in cross_relabeled:
        rng.shuffle(neighbors)
    answer = [relabel[v] for v in base_answer]

    return {
        "family": "k14_free_split_hamilton_cycle",
        "n": n,
        "vertex_count": total_vertices,
        "clique": clique,
        "independent": independent,
        "hub": relabel[base_hub],
        "residue_labels": residue_labels,
        "cross_neighborhoods": cross_relabeled,
        "answer": answer,
    }


def _format_answer(answer: list[int]) -> str:
    return ", ".join(str(v) for v in answer)


def render(inst: dict) -> str:
    n = inst["n"]
    residue_rows = sorted(inst["residue_labels"], key=lambda row: row[1])
    cross_rows = list(inst["cross_neighborhoods"])
    lines = [
        "Hamiltonian cycle in a K_{1,4}-free split graph",
        "",
        "A finite simple graph is split when its vertices are partitioned into a",
        "clique K (every two distinct vertices of K are adjacent) and an independent",
        "set I (no two vertices of I are adjacent). It is K_{1,4}-free when no five",
        "vertices induce a four-leaf star. A Hamiltonian cycle is a cyclic ordering",
        "of all vertices in which every consecutive pair, including last-to-first,",
        "is an edge.",
        "",
        f"This graph has N={inst['vertex_count']} vertices, with IDs 0 through "
        f"{inst['vertex_count'] - 1}.",
        f"The residue modulus is n={n}. The universal independent vertex is "
        f"h={inst['hub']}.",
        "The other independent vertices are listed as vertex:residue:",
        "  " + " ".join(f"{vertex}:{residue}" for vertex, residue in residue_rows),
        "Clique vertices K:",
        "  " + " ".join(str(v) for v in inst["clique"]),
        "",
        "All clique-clique edges are present. There are no independent-independent",
        "edges. The remaining edges are exactly the following cross-neighborhoods;",
        "a row `k: a b c` says clique vertex k is adjacent to independent vertices",
        "a, b, and c:",
    ]
    lines.extend(
        f"  {k}: " + " ".join(str(v) for v in neighbors)
        for k, neighbors in cross_rows
    )
    lines.extend(
        [
            "",
            f"Output exactly {inst['vertex_count']} distinct integer vertex IDs in",
            "cyclic order, separated by commas. The first ID must be a clique vertex",
            "(this fixes the bounded answer language); either direction is allowed.",
            "Every graph vertex must occur once, with no repetitions.",
            "",
            "Give your final answer inside <answer></answer> tags, as a comma-separated",
            "list of integer vertex IDs.",
            "Example: <answer>7, 2, 9, 4</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if match is None:
        return None
    body = match.group(1).strip()
    if not body:
        return []
    body = re.sub(r"^```(?:json|text)?\s*|\s*```$", "", body, flags=re.I | re.S)
    try:
        if body.lstrip().startswith("["):
            value = json.loads(body)
            if (
                isinstance(value, list)
                and all(isinstance(x, int) and not isinstance(x, bool) for x in value)
            ):
                return value
            return None
        pieces = [piece.strip() for piece in body.split(",")]
        if not pieces or any(not re.fullmatch(r"[-+]?\d+", p) for p in pieces):
            return None
        return [int(piece) for piece in pieces]
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _instance_sets(inst: dict) -> tuple[set[int], set[int], dict[int, set[int]]]:
    clique = set(inst["clique"])
    independent = set(inst["independent"])
    cross = {int(k): set(neighbors) for k, neighbors in inst["cross_neighborhoods"]}
    return clique, independent, cross


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Verify any Hamiltonian cycle in the supplied split graph exactly."""
    if not isinstance(answer, list):
        return False, "answer must be a list of integer vertex IDs"
    if not answer:
        return False, "answer is empty"
    if len(answer) != inst["vertex_count"]:
        return False, "cycle has wrong length"
    if any(isinstance(v, bool) or not isinstance(v, int) for v in answer):
        return False, "cycle entries must be integers"
    clique, independent, cross = _instance_sets(inst)
    vertices = clique | independent
    if any(v not in vertices for v in answer):
        return False, "cycle contains an unknown vertex"
    if len(set(answer)) != len(answer):
        return False, "cycle repeats a vertex"
    if answer[0] not in clique:
        return False, "cycle must start with a clique vertex"

    def adjacent(u: int, v: int) -> bool:
        if u == v:
            return False
        if u in clique and v in clique:
            return True
        if u in clique and v in independent:
            return v in cross.get(u, set())
        if v in clique and u in independent:
            return u in cross.get(v, set())
        return False

    for u, v in zip(answer, answer[1:] + answer[:1]):
        if not adjacent(u, v):
            return False, f"cycle uses a non-edge {u}-{v}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the statement-aware bounded cycle language."""
    clique = list(inst["clique"])
    independent = list(inst["independent"])
    rng.shuffle(clique)
    rng.shuffle(independent)
    gaps = set(rng.sample(range(len(clique)), len(independent)))
    result: list[int] = []
    cursor = 0
    for index, vertex in enumerate(clique):
        result.append(vertex)
        if index in gaps:
            result.append(independent[cursor])
            cursor += 1
    return result


def search_space(inst: dict) -> int | None:
    k = len(inst["clique"])
    i = len(inst["independent"])
    return math.factorial(k) * math.comb(k, i) * math.factorial(i)


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the bounded language only when it contains at most 600k words."""
    size = search_space(inst)
    if size is None or size > _ENUMERATION_CAP:
        return None
    clique = tuple(inst["clique"])
    independent = tuple(inst["independent"])
    hits = 0
    for kp in itertools.permutations(clique):
        for gaps_tuple in itertools.combinations(range(len(clique)), len(independent)):
            gaps = set(gaps_tuple)
            for ip in itertools.permutations(independent):
                candidate: list[int] = []
                cursor = 0
                for index, vertex in enumerate(kp):
                    candidate.append(vertex)
                    if index in gaps:
                        candidate.append(ip[cursor])
                        cursor += 1
                if verify(inst, candidate)[0]:
                    hits += 1
    return hits


def _core(inst: dict) -> tuple[list[int], list[tuple[int, int, int]], dict[int, int]]:
    hub = inst["hub"]
    residue = {int(v): int(r) for v, r in inst["residue_labels"]}
    ordinary = sorted(residue, key=residue.get)
    edges: list[tuple[int, int, int]] = []
    for k, neighbors in inst["cross_neighborhoods"]:
        ends = [v for v in neighbors if v != hub]
        if len(ends) != 2 or any(v not in residue for v in ends):
            raise ValueError("malformed cubic cross-incidence core")
        edges.append((int(k), int(ends[0]), int(ends[1])))
    return ordinary, edges, residue


def _cycle_from_matching(
    inst: dict, matching_pairs: list[tuple[int, int]]
) -> list[int] | None:
    """Turn a perfect matching of the cubic core into a split Hamilton cycle."""
    ordinary, edges, residue = _core(inst)
    edge_id = {frozenset((u, v)): k for k, u, v in edges}
    if len(edge_id) != len(edges):
        return None
    matched_edges = {frozenset(pair) for pair in matching_pairs}
    if len(matched_edges) * 2 != len(ordinary):
        return None
    covered = set().union(*matched_edges) if matched_edges else set()
    if covered != set(ordinary) or any(edge not in edge_id for edge in matched_edges):
        return None

    complement = [edge for edge in edge_id if edge not in matched_edges]
    adj: dict[int, list[int]] = {v: [] for v in ordinary}
    for edge in complement:
        u, v = tuple(edge)
        adj[u].append(v)
        adj[v].append(u)
    if any(len(adj[v]) != 2 for v in ordinary):
        return None

    incoming: dict[int, int] = {}
    unseen = set(ordinary)
    while unseen:
        start = min(unseen, key=residue.get)
        previous: int | None = None
        current = start
        order = [start]
        while True:
            choices = [v for v in adj[current] if v != previous]
            if not choices:
                return None
            nxt = min(choices, key=residue.get)
            if nxt == start:
                incoming[start] = edge_id[frozenset((current, start))]
                break
            if nxt in order:
                return None
            incoming[nxt] = edge_id[frozenset((current, nxt))]
            order.append(nxt)
            previous, current = current, nxt
        unseen.difference_update(order)

    answer: list[int] = []
    pairs = sorted(
        (tuple(edge) for edge in matched_edges),
        key=lambda pair: min(residue[pair[0]], residue[pair[1]]),
    )
    for u, v in pairs:
        if residue[u] > residue[v]:
            u, v = v, u
        answer.extend([incoming[u], u, edge_id[frozenset((u, v))], v, incoming[v]])
    answer.append(inst["hub"])
    return answer


def _blossom_perfect_matching(
    vertices: list[int], edge_pairs: list[tuple[int, int]]
) -> tuple[list[tuple[int, int]] | None, int]:
    """Edmonds' unweighted blossom algorithm, O(V^3), with an operation count."""
    index = {v: i for i, v in enumerate(vertices)}
    graph = [[] for _ in vertices]
    for u, v in edge_pairs:
        a, b = index[u], index[v]
        if b not in graph[a]:
            graph[a].append(b)
            graph[b].append(a)
    # Count integer/index/edge primitive operations, including the linear array
    # initialization that a literal execution performs on every augmentation.
    count = [2 * len(edge_pairs)]
    size = len(vertices)
    match = [-1] * size
    parent = [-1] * size
    base = list(range(size))
    used = [False] * size
    blossom = [False] * size

    def lca(a: int, b: int) -> int:
        seen = [False] * size
        while True:
            a = base[a]
            seen[a] = True
            count[0] += 1
            if match[a] == -1:
                break
            a = parent[match[a]]
        while True:
            b = base[b]
            count[0] += 1
            if seen[b]:
                return b
            b = parent[match[b]]

    def mark_path(v: int, root: int, child: int) -> None:
        while base[v] != root:
            blossom[base[v]] = blossom[base[match[v]]] = True
            parent[v] = child
            child = match[v]
            v = parent[match[v]]
            count[0] += 1

    def find_path(root: int) -> int:
        nonlocal parent, base, used, blossom
        used = [False] * size
        parent = [-1] * size
        base = list(range(size))
        count[0] += 3 * size
        queue = [root]
        used[root] = True
        head = 0
        while head < len(queue):
            v = queue[head]
            head += 1
            for u in graph[v]:
                count[0] += 1
                if base[v] == base[u] or match[v] == u:
                    continue
                if u == root or (match[u] != -1 and parent[match[u]] != -1):
                    curbase = lca(v, u)
                    blossom = [False] * size
                    count[0] += size
                    mark_path(v, curbase, u)
                    mark_path(u, curbase, v)
                    for i in range(size):
                        count[0] += 1
                        if blossom[base[i]]:
                            base[i] = curbase
                            if not used[i]:
                                used[i] = True
                                queue.append(i)
                elif parent[u] == -1:
                    parent[u] = v
                    if match[u] == -1:
                        return u
                    u = match[u]
                    used[u] = True
                    queue.append(u)
        return -1

    for root in range(size):
        if match[root] != -1:
            continue
        endpoint = find_path(root)
        if endpoint == -1:
            continue
        while endpoint != -1:
            previous = parent[endpoint]
            nxt = match[previous] if previous != -1 else -1
            match[endpoint] = previous
            if previous != -1:
                match[previous] = endpoint
            endpoint = nxt
            count[0] += 1

    if any(v == -1 for v in match):
        return None, count[0]
    result = [
        (vertices[i], vertices[match[i]]) for i in range(size) if i < match[i]
    ]
    count[0] += size
    return result, count[0]


def _reference_solve(inst: dict) -> tuple[list[int] | None, int]:
    ordinary, edges, _ = _core(inst)
    matching, operations = _blossom_perfect_matching(
        ordinary, [(u, v) for _, u, v in edges]
    )
    if matching is None:
        return None, operations
    candidate = _cycle_from_matching(inst, matching)
    # Core extraction, complement construction/orientation, and path splicing.
    operations += 4 * len(edges) + 3 * len(ordinary)
    return candidate, operations


def _greedy_matching(inst: dict, edge_order: str) -> list[int] | None:
    ordinary, edges, residue = _core(inst)
    degree = Counter()
    for _, u, v in edges:
        degree[u] += 1
        degree[v] += 1
    if edge_order == "outlier":
        ordered = sorted(
            edges,
            key=lambda row: (
                -(abs(degree[row[1]] - degree[row[2]])),
                row[0],
            ),
        )
    else:
        ordered = sorted(
            edges,
            key=lambda row: (
                min(residue[row[1]], residue[row[2]]),
                max(residue[row[1]], residue[row[2]]),
            ),
        )
    used: set[int] = set()
    matching: list[tuple[int, int]] = []
    for _, u, v in ordered:
        if u not in used and v not in used:
            used.update((u, v))
            matching.append((u, v))
    if len(used) != len(ordinary):
        return None
    return _cycle_from_matching(inst, matching)


def _random_cycle_walk(
    inst: dict, rng: random.Random, restarts: int = 256
) -> tuple[list[int] | None, int]:
    ordinary, edges, _ = _core(inst)
    adj = {v: [] for v in ordinary}
    all_edges = {frozenset((u, v)) for _, u, v in edges}
    for edge in all_edges:
        u, v = tuple(edge)
        adj[u].append(v)
        adj[v].append(u)
    nodes = 0
    for _ in range(restarts):
        start = rng.choice(ordinary)
        path = [start]
        seen = {start}
        while len(path) < len(ordinary):
            choices = [v for v in adj[path[-1]] if v not in seen]
            nodes += len(adj[path[-1]])
            if not choices:
                break
            nxt = rng.choice(choices)
            path.append(nxt)
            seen.add(nxt)
        if len(path) == len(ordinary) and frozenset((path[-1], start)) in all_edges:
            cycle_edges = {
                frozenset((u, v)) for u, v in zip(path, path[1:] + path[:1])
            }
            matching = [tuple(edge) for edge in all_edges - cycle_edges]
            candidate = _cycle_from_matching(inst, matching)
            if candidate is not None:
                return candidate, nodes
    return None, nodes


def _smallest_difference_ansatz(inst: dict) -> list[int] | None:
    ordinary, edges, residue = _core(inst)
    modulus = inst["n"]
    grouped: dict[int, list[tuple[int, int]]] = {}
    for _, u, v in edges:
        d = _canonical_difference(residue[u], residue[v], modulus)
        grouped.setdefault(d, []).append((u, v))
    guessed_cycle = grouped[min(grouped)]
    if len(guessed_cycle) != len(ordinary):
        return None
    degree = Counter(v for edge in guessed_cycle for v in edge)
    if any(degree[v] != 2 for v in ordinary):
        return None
    cycle_set = {frozenset(edge) for edge in guessed_cycle}
    matching = [
        (u, v) for _, u, v in edges if frozenset((u, v)) not in cycle_set
    ]
    return _cycle_from_matching(inst, matching)


def canonical_key(inst: dict) -> str:
    """Canonical chord diagram of the annotated cubic incidence core."""
    ordinary, edges, residue = _core(inst)
    modulus = inst["n"]
    counts = Counter(
        _canonical_difference(residue[u], residue[v], modulus) for _, u, v in edges
    )
    top = max(counts.values())
    modes = [d for d, count in counts.items() if count == top]
    if len(modes) != 1:
        raise ValueError("instance has no unique repeated-difference cycle")
    mode = modes[0]
    cycle_edges = [
        frozenset((u, v))
        for _, u, v in edges
        if _canonical_difference(residue[u], residue[v], modulus) == mode
    ]
    if len(cycle_edges) != len(ordinary):
        raise ValueError("recovered cycle has wrong size")
    cycle_set = set(cycle_edges)
    adj = {v: [] for v in ordinary}
    for edge in cycle_edges:
        u, v = tuple(edge)
        adj[u].append(v)
        adj[v].append(u)
    if any(len(adj[v]) != 2 for v in ordinary):
        raise ValueError("recovered high-multiplicity class is not a cycle")
    chords = [frozenset((u, v)) for _, u, v in edges if frozenset((u, v)) not in cycle_set]

    encodings: list[tuple[tuple[int, int], ...]] = []
    for start in ordinary:
        for first in adj[start]:
            order = [start, first]
            previous, current = start, first
            while len(order) < len(ordinary):
                nxts = [v for v in adj[current] if v != previous]
                if len(nxts) != 1 or nxts[0] == start:
                    break
                previous, current = current, nxts[0]
                order.append(current)
            if len(order) != len(ordinary) or start not in adj[order[-1]]:
                continue
            position = {v: i for i, v in enumerate(order)}
            encoding = tuple(
                sorted(
                    tuple(sorted((position[u], position[v])))
                    for u, v in (tuple(edge) for edge in chords)
                )
            )
            encodings.append(encoding)
    if not encodings:
        raise ValueError("could not canonically traverse recovered cycle")
    payload = json.dumps(
        {"n": modulus, "chords": min(encodings)}, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    n = params.get("n")
    if not isinstance(n, int):
        return None
    for candidate in (22, 46, 94):
        if candidate > n:
            return {"n": candidate}
    return "cap_bound"


def _relabel_instance(
    inst: dict, rng: random.Random
) -> tuple[dict, list[int]]:
    vertices = list(range(inst["vertex_count"]))
    shuffled = vertices[:]
    rng.shuffle(shuffled)
    mapping = dict(zip(vertices, shuffled))
    transformed = dict(inst)
    transformed["clique"] = [mapping[v] for v in reversed(inst["clique"])]
    transformed["independent"] = [mapping[v] for v in reversed(inst["independent"])]
    transformed["hub"] = mapping[inst["hub"]]
    transformed["residue_labels"] = [
        [mapping[v], r] for v, r in reversed(inst["residue_labels"])
    ]
    transformed["cross_neighborhoods"] = [
        [mapping[k], [mapping[v] for v in reversed(neighbors)]]
        for k, neighbors in reversed(inst["cross_neighborhoods"])
    ]
    carried = [mapping[v] for v in inst["answer"]]
    transformed["answer"] = carried
    return transformed, carried


def _affine_residues(inst: dict, rng: random.Random) -> dict:
    modulus = inst["n"]
    units = [u for u in range(1, modulus) if math.gcd(u, modulus) == 1]
    multiplier = rng.choice(units)
    shift = rng.randrange(modulus)
    transformed = dict(inst)
    transformed["residue_labels"] = [
        [vertex, (multiplier * residue + shift) % modulus]
        for vertex, residue in reversed(inst["residue_labels"])
    ]
    transformed["clique"] = list(reversed(inst["clique"]))
    transformed["independent"] = list(reversed(inst["independent"]))
    transformed["cross_neighborhoods"] = [
        [k, list(reversed(neighbors))]
        for k, neighbors in reversed(inst["cross_neighborhoods"])
    ]
    return transformed


def _find_nonedge_swap(inst: dict, answer: list[int]) -> list[int]:
    independent = set(inst["independent"])
    positions = [i for i, v in enumerate(answer) if v in independent]
    for a_index, b_index in itertools.combinations(positions, 2):
        candidate = answer[:]
        candidate[a_index], candidate[b_index] = candidate[b_index], candidate[a_index]
        ok, reason = verify(inst, candidate)
        if not ok and reason.startswith("cycle uses a non-edge"):
            return candidate
    raise AssertionError("could not construct swapped non-edge corruption")


def selftest() -> dict:
    report: dict[str, object] = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    g1_attempts = 0
    g1_failures: list[str] = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 19):
            inst = make_instance(seed=seed, **params)
            g1_attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    corruptions: dict[str, list[int]] = {
        "drop_one": planted[:-1],
        "swap_two": _find_nonedge_swap(shipping, planted),
        "duplicate": planted[:-1] + [planted[0]],
        "empty": [],
        "out_of_range": planted[:-1] + [shipping["vertex_count"]],
    }
    corruption_reasons = {
        name: verify(shipping, candidate)[1] for name, candidate in corruptions.items()
    }
    g2_pass = (
        all(not verify(shipping, candidate)[0] for candidate in corruptions.values())
        and len(set(corruption_reasons.values())) == len(corruption_reasons)
    )
    report["G2_rejects_corruption"] = {
        "pass": g2_pass,
        "reasons": corruption_reasons,
    }

    realistic = (
        "I used the split partition and checked the wraparound edge.\n"
        "```text\n<answer>"
        + _format_answer(planted)
        + "</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and verify(shipping, parsed)[0],
        "parsed_length": len(parsed) if isinstance(parsed, list) else None,
        "garbage_returns_none": parse_answer("no tagged answer here") is None,
    }

    guess_rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_elapsed = time.perf_counter() - guess_start
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "candidate_space": search_space(shipping),
        "prior": "uniform over clique-first permutations with no consecutive I vertices",
    }

    attack_seeds = list(range(800, 808))
    attacks = {
        "outlier_degree_matching": {"successes": 0, "attempts": 0},
        "greedy_lowest_label_matching": {"successes": 0, "attempts": 0},
        "random_cycle_walk_256": {"successes": 0, "attempts": 0, "nodes": 0},
        "smallest_modular_difference_ansatz": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_operations = 0
    strongest_nodes = 0
    strongest_elapsed = 0.0
    reference_elapsed = 0.0
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_degree_matching": _greedy_matching(inst, "outlier"),
            "greedy_lowest_label_matching": _greedy_matching(inst, "label"),
            "smallest_modular_difference_ansatz": _smallest_difference_ansatz(inst),
        }
        walk_start = time.perf_counter()
        walk_candidate, nodes = _random_cycle_walk(inst, random.Random(seed ^ 0xA5A5))
        strongest_elapsed += time.perf_counter() - walk_start
        candidates["random_cycle_walk_256"] = walk_candidate
        strongest_nodes += nodes
        attacks["random_cycle_walk_256"]["nodes"] += nodes
        for name, candidate in candidates.items():
            attacks[name]["attempts"] += 1
            if candidate is not None and verify(inst, candidate)[0]:
                attacks[name]["successes"] += 1

        reference_start = time.perf_counter()
        reference_candidate, operations = _reference_solve(inst)
        reference_elapsed += time.perf_counter() - reference_start
        reference_operations += operations
        if reference_candidate is not None and verify(inst, reference_candidate)[0]:
            reference_successes += 1
    all_failed = all(entry["successes"] == 0 for entry in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and len(attacks) >= 4,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Edmonds blossom maximum matching plus complementary-cycle splicing",
            "complexity": "O(n^3) worst-case for matching; O(n) splicing",
            "wall_clock_sec": reference_elapsed,
            "operations": reference_operations,
            "average_operations": reference_operations / len(attack_seeds),
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    exact_demo_solutions = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": (
            guess_hits / guess_total < 1e-6
            and all_failed
            and reference_successes == len(attack_seeds)
        ),
        "shipping_density": {
            "hits": guess_hits,
            "samples": guess_total,
            "observed_fraction": guess_hits / guess_total,
        },
        "demo_exact_valid_answers": exact_demo_solutions,
        "demo_candidate_space": search_space(demo),
        "strongest_failing_attack": {
            "name": "256 random nonbacktracking cycle walks",
            "wall_clock_sec_panel": strongest_elapsed,
            "nodes_panel": strongest_nodes,
            "attempts": len(attack_seeds),
            "successes": attacks["random_cycle_walk_256"]["successes"],
        },
        "reference_operations_panel": reference_operations,
        "guess_sampling_wall_clock_sec": guess_elapsed,
    }

    doubled = make_instance(
        n=2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"], seed=2026
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    sizes = [make_instance(seed=5, **params)["vertex_count"] for params in DIFFICULTY.values()]
    report["G7_scales"] = {
        "pass": doubled_ok and sizes == sorted(sizes) and len(set(sizes)) == len(sizes),
        "preset_vertex_counts": sizes,
        "doubled_n": doubled["n"],
        "doubled_vertex_count": doubled["vertex_count"],
        "doubled_verify_reason": doubled_reason,
    }

    invariant_checks = 0
    carried_checks = 0
    invariant_failures: list[int] = []
    for seed in range(20):
        inst = make_instance(seed=1000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        transformed, carried = _relabel_instance(inst, random.Random(7000 + seed))
        transformed = _affine_residues(transformed, random.Random(9000 + seed))
        invariant_checks += 1
        if canonical_key(transformed) != key:
            invariant_failures.append(seed)
        carried_checks += 1
        if not verify(transformed, carried)[0]:
            invariant_failures.append(seed)
    unrelated_keys = [
        canonical_key(
            make_instance(seed=2000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        )
        for seed in range(20)
    ]
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and len(set(unrelated_keys)) == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated": len(set(unrelated_keys)),
        "unrelated_attempts": 20,
        "failures": invariant_failures,
        "transformations": [
            "arbitrary vertex-ID permutation",
            "clique/independent/cross-row reordering",
            "cross-neighborhood reordering",
            "affine residue change x -> ux+t",
            "all transformations composed",
        ],
    }

    serialized_answer = json.dumps(planted)
    answer_chars = len(serialized_answer)
    # Conservative lexical count: every integer and punctuation mark counts as
    # one token.  This is reproducible without adding a tokenizer dependency.
    answer_tokens = len(re.findall(r"\d+|[^\w\s]", serialized_answer))
    answer_elements = len(planted)
    intended_operations = 3 * shipping["n"]
    within_caps = (
        answer_chars <= 2000
        and answer_tokens <= 500
        and answer_elements <= 256
        and intended_operations <= 300
    )
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else 0.0
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps_only_gate": True,
    }

    report["pass"] = all(
        bool(value.get("pass"))
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
