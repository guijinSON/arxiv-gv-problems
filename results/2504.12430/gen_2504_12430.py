"""Verified witness generator for arXiv:2504.12430.

The generated task is proper (6:2)-fractional coloring of a graph, viewed as a
2-uniform hypergraph.  A color is a 2-subset of {0,1,2,3,4,5}; adjacent vertices
must receive disjoint subsets.  Generation plants a balanced coloring first and
then samples a connected 5-regular graph whose edges are all proper under it.

Only the Python standard library is used.  Generation is deterministic for
``(n, seed)`` and uses a private ``random.Random`` instance.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import random
import re
from collections import deque


# ``n`` is the number of vertices planted with each of the fifteen possible
# 2-subsets, so the public graph has 15*n vertices.  Degree five is the useful
# sparse/hard window found by the local-solver sweep.
DIFFICULTY = {
    "standard": {"n": 18, "degree": 5},
    "hard": {"n": 24, "degree": 5},
    "extreme": {"n": 30, "degree": 5},
}

SHIPPING_DIFFICULTY = "standard"

NOTES = r"""
Paper reading notes.  Section 1 of Akhmejanova--Longbrake fixes the definition:
every vertex receives exactly b distinct colors from [a], and an edge is proper
exactly when no one color belongs to every vertex on that edge.  The same
section explicitly says that on 2-element edges this is the usual (a:b) graph
multicoloring.  Thus, for (a,b)=(6,2), the fifteen possible vertex colors are
the 2-subsets of a six-element set and allowed adjacent pairs are disjoint.
This is precisely graph homomorphism to the Kneser graph KG(6,2).

The target paper is extremal combinatorics, not a computational-complexity
paper.  Its Theorem 1 is a sparse-edge sufficient condition for colorability in
the different regime 2 <= b <= a-2 and a <= uniformity/(2 ln uniformity), and
its proof gives a randomized recoloring construction.  Theorem 3 gives another
reserve-color construction when a/b grows.  This generator deliberately uses
2-uniform edges and does not claim either theorem as a hardness theorem.
Computational hardness instead follows from the Hell--Nesetril H-coloring
dichotomy: homomorphism to a fixed loopless non-bipartite graph is NP-complete.
KG(6,2) is loopless and non-bipartite.  The nearby (4:2) choice would be easy:
KG(4,2) is three disjoint edges, so feasibility is just bipartiteness.

Inverse generation samples the complete public witness before any input edge.
It uses every one of the fifteen 2-subsets equally often, then pairs five stubs
per vertex only across disjoint planted subsets.  Every public vertex has degree
five; vertices within and outside any planted class use the same stub-pairing
distribution, input labels are randomly permuted by the planted assignment,
and edges are shuffled.  There is no separate, statistically different decoy
edge population.  The adversary panel tests a per-vertex position/local-cycle
ranking, deterministic left-to-right greedy coloring, and 512 randomized
forward-checking restarts, plus a bounded arc-consistency/backtracking solver.
A sweep rejected degree four because that exact solver finished quickly; at
degree six and above propagation begins exposing the planted partition.  The
degree-five regime is the deliberately narrow hard window.  A degree-five
n=12 draft was also removed after the bounded exact attack solved one of eight
test seeds; the named ladder begins at n=18.  Exact graph
isomorphism canonicalization is not
claimed: canonical_key uses the strongest cheap invariant used here, a sorted
multiset of rooted BFS layer/edge profiles, and the README records that caveat.
"""


PALETTE = tuple(range(6))
DOMAIN = tuple(itertools.combinations(PALETTE, 2))
DOMAIN_INDEX = {pair: index for index, pair in enumerate(DOMAIN)}
TARGET_ADJ = tuple(
    tuple(
        j
        for j, other in enumerate(DOMAIN)
        if not set(pair).intersection(other)
    )
    for pair in DOMAIN
)
TARGET_ADJ_SETS = tuple(frozenset(row) for row in TARGET_ADJ)
TARGET_ADJ_MASKS = tuple(sum(1 << color for color in row) for row in TARGET_ADJ)
TARGET_EDGES = tuple(
    (i, j)
    for i in range(len(DOMAIN))
    for j in TARGET_ADJ[i]
    if i < j
)


def _norm_edge(u: int, v: int) -> tuple[int, int]:
    return (u, v) if u < v else (v, u)


def _adjacency(vertex_count: int, edges: list | tuple) -> list[list[int]]:
    adjacency = [[] for _ in range(vertex_count)]
    for raw_u, raw_v in edges:
        u, v = int(raw_u), int(raw_v)
        adjacency[u].append(v)
        adjacency[v].append(u)
    for row in adjacency:
        row.sort()
    return adjacency


def _connected(adjacency: list[list[int]]) -> bool:
    if not adjacency:
        return True
    seen = {0}
    queue = deque([0])
    while queue:
        vertex = queue.popleft()
        for neighbor in adjacency[vertex]:
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return len(seen) == len(adjacency)


def _pair_simple_bucket(
    left: list[int], right: list[int], rng: random.Random
) -> list[tuple[int, int]] | None:
    """Randomly pair two stub buckets without repeating a public edge."""

    for _ in range(2_000):
        shuffled = right[:]
        rng.shuffle(shuffled)
        edges = [_norm_edge(u, v) for u, v in zip(left, shuffled)]
        if len(set(edges)) == len(edges):
            return edges
    return None


def _sample_regular_graph(
    class_vertices: list[list[int]], degree: int, rng: random.Random
) -> tuple[list[tuple[int, int]], list[list[int]]]:
    """Pair equal-degree stubs across KG(6,2)-compatible classes.

    Aggregate traffic is equal on the six target edges incident to each target
    color, but an individual vertex's five stubs are randomly distributed among
    those target neighbors.  This keeps public degree identical without leaving
    the exact local-cover signature that one edge per target neighbor would.
    """

    q = len(class_vertices[0])
    vertex_count = len(DOMAIN) * q
    bucket_size = degree * q // len(TARGET_ADJ[0])
    expected_edges = degree * vertex_count // 2

    for _attempt in range(5_000):
        buckets: dict[tuple[int, int], list[int]] = {}
        for color_index, vertices in enumerate(class_vertices):
            stubs = [vertex for vertex in vertices for _ in range(degree)]
            rng.shuffle(stubs)
            neighbors = list(TARGET_ADJ[color_index])
            rng.shuffle(neighbors)
            for offset, neighbor_color in enumerate(neighbors):
                buckets[(color_index, neighbor_color)] = stubs[
                    offset * bucket_size : (offset + 1) * bucket_size
                ]

        edges: list[tuple[int, int]] = []
        failed = False
        for left_color, right_color in TARGET_EDGES:
            left = buckets[(left_color, right_color)][:]
            right = buckets[(right_color, left_color)][:]
            rng.shuffle(left)
            rng.shuffle(right)
            paired = _pair_simple_bucket(left, right, rng)
            if paired is None:
                failed = True
                break
            edges.extend(paired)

        if failed or len(edges) != expected_edges or len(set(edges)) != expected_edges:
            continue
        adjacency = _adjacency(vertex_count, edges)
        if any(len(row) != degree for row in adjacency):
            continue
        if not _connected(adjacency):
            continue
        rng.shuffle(edges)
        return edges, adjacency

    raise RuntimeError("could not sample a connected simple regular planted graph")


def make_instance(n: int, seed: int = 0, degree: int = 5, **params) -> dict:
    """Sample a fractional coloring first, then build a graph around it.

    ``n`` is the number of public vertices carrying each of the fifteen possible
    two-color sets.  Hence the graph has exactly ``15*n`` vertices.  Increasing
    ``n`` grows a constant-degree fixed-target CSP rather than making it dense.

    The shipping family uses degree 5 and requires ``n`` divisible by 6 so equal
    target-edge traffic is integral.  Degree 6 is accepted for the tiny n=1
    enumeration fixture used by ``selftest``.
    """

    if params:
        unknown = ", ".join(sorted(map(str, params)))
        raise TypeError(f"unknown make_instance parameter(s): {unknown}")
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    if n < 1:
        raise ValueError("n must be at least 1")
    if isinstance(degree, bool) or not isinstance(degree, int):
        raise TypeError("degree must be an integer")
    if degree < 1:
        raise ValueError("degree must be positive")
    if degree * n % len(TARGET_ADJ[0]):
        raise ValueError(
            f"degree*n must be divisible by {len(TARGET_ADJ[0])} for balanced generation"
        )
    if degree > len(TARGET_ADJ[0]) * n:
        raise ValueError("degree exceeds the number of compatible public vertices")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")

    rng = random.Random(seed)
    vertex_count = len(DOMAIN) * n

    # G: the complete public witness is sampled before a single problem edge.
    planted_indices = [index for index in range(len(DOMAIN)) for _ in range(n)]
    rng.shuffle(planted_indices)
    answer = [
        [vertex, DOMAIN[color_index][0], DOMAIN[color_index][1]]
        for vertex, color_index in enumerate(planted_indices)
    ]

    class_vertices = [
        [vertex for vertex, assigned in enumerate(planted_indices) if assigned == color_index]
        for color_index in range(len(DOMAIN))
    ]
    edges, adjacency = _sample_regular_graph(class_vertices, degree, rng)

    return {
        "paper": "arXiv:2504.12430",
        "family": "proper (6:2)-fractional coloring of a 2-uniform hypergraph",
        "n": n,
        "seed": seed,
        "a": 6,
        "b": 2,
        "vertex_count": vertex_count,
        "edge_count": len(edges),
        "degree": degree,
        "edges": edges,
        "adjacency": adjacency,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Return the complete standalone problem statement."""

    vertex_count = inst["vertex_count"]
    edge_lines = [f"{u} {v}" for u, v in inst["edges"]]
    return "\n".join(
        [
            "Proper (6:2)-fractional coloring of a graph",
            "",
            "A graph is a set of vertices together with undirected edges.  Here it",
            "is also viewed as a 2-uniform hypergraph: every edge has exactly two",
            "distinct endpoints.  There are no loops and no repeated edges.",
            "",
            "Assign every vertex exactly two DISTINCT colors chosen from",
            "{0,1,2,3,4,5}.  An edge is properly fractionally colored exactly when",
            "no color is assigned to both endpoints.  Equivalently, the two",
            "2-element color sets at the endpoints must be disjoint.  Every listed",
            "edge must satisfy this rule.",
            "",
            f"Vertices are the integers 0 through {vertex_count - 1}, inclusive",
            "(0-indexed).  Every vertex must appear exactly once in the answer.",
            "The order of vertex records and the order of the two colors within a",
            "record do not matter.  Different vertices may receive the same pair.",
            "Only the edges listed below impose constraints; nonedges impose none.",
            "",
            f"Edges ({inst['edge_count']} total), one pair of endpoints per line:",
            *edge_lines,
            "",
            "Give your final answer inside <answer></answer> tags as one JSON array.",
            "It must contain exactly one [vertex,color1,color2] record per vertex.",
            "Both colors in a record must be integers in 0..5 and must be distinct.",
            "Example format: <answer>[[0,0,1],[1,2,3]]</answer>",
            "Output nothing else inside the tags.",
        ]
    )


def parse_answer(text: str) -> object | None:
    """Parse the last tagged JSON witness, tolerating prose and Markdown fences."""

    try:
        if not isinstance(text, str):
            return None
        matches = re.findall(
            r"<answer\b[^>]*>(.*?)</answer\s*>",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not matches:
            return None
        body = matches[-1].strip()
        body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body).strip()
        value = json.loads(body)
        if not isinstance(value, list):
            return None
        for record in value:
            if (
                not isinstance(record, list)
                or len(record) != 3
                or not all(isinstance(item, int) and not isinstance(item, bool) for item in record)
            ):
                return None
        return value
    except Exception:
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Accept any proper (6:2)-coloring; never inspect the planted answer."""

    vertex_count = inst["vertex_count"]
    if not isinstance(answer, list):
        return False, "malformed: expected a JSON array of vertex records"
    if not answer:
        return False, f"empty answer: expected {vertex_count} vertex records"
    if len(answer) != vertex_count:
        return False, f"wrong record count: expected {vertex_count}, got {len(answer)}"

    assigned: list[frozenset[int] | None] = [None] * vertex_count
    for position, record in enumerate(answer):
        if (
            not isinstance(record, (list, tuple))
            or len(record) != 3
            or not all(isinstance(item, int) and not isinstance(item, bool) for item in record)
        ):
            return False, f"malformed record at answer position {position}"
        vertex, first, second = record
        if vertex < 0 or vertex >= vertex_count:
            return False, f"vertex out of range: {vertex} is not in 0..{vertex_count - 1}"
        if assigned[vertex] is not None:
            return False, f"duplicate vertex record: vertex {vertex} appears more than once"
        if first < 0 or first >= 6 or second < 0 or second >= 6:
            bad = first if first < 0 or first >= 6 else second
            return False, f"color out of range: {bad} is not in 0..5"
        if first == second:
            return False, f"repeated color at vertex {vertex}: the two colors must be distinct"
        assigned[vertex] = frozenset((first, second))

    missing = next((vertex for vertex, colors in enumerate(assigned) if colors is None), None)
    if missing is not None:
        return False, f"missing vertex record: vertex {missing} was not assigned"

    for edge_index, (u, v) in enumerate(inst["edges"]):
        common = assigned[u].intersection(assigned[v])  # type: ignore[union-attr]
        if common:
            shown = ",".join(map(str, sorted(common)))
            return False, f"edge conflict at edge {edge_index} ({u},{v}): shared color(s) {shown}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from all locally well-formed fractional colorings.

    Each record names one vertex exactly once and already contains two distinct,
    in-range colors.  Only the nontrivial edge-disjointness constraints remain.
    """

    records = []
    for vertex in range(inst["vertex_count"]):
        first, second = DOMAIN[rng.randrange(len(DOMAIN))]
        records.append([vertex, first, second])
    return records


def search_space(inst: dict) -> int | None:
    """Number of semantic assignments after shape/range/distinctness are enforced."""

    return len(DOMAIN) ** inst["vertex_count"]


def enumerate_all(inst: dict) -> int | None:
    """Count every valid coloring exactly for tiny graphs, with a work cap."""

    vertex_count = inst["vertex_count"]
    if vertex_count > 15:
        return None
    adjacency = inst.get("adjacency") or _adjacency(vertex_count, inst["edges"])
    assignment = [-1] * vertex_count
    visits = 0
    cap = 2_000_000

    def available(vertex: int) -> list[int]:
        return [
            color
            for color in range(len(DOMAIN))
            if all(
                assignment[neighbor] < 0
                or assignment[neighbor] in TARGET_ADJ_SETS[color]
                for neighbor in adjacency[vertex]
            )
        ]

    def dfs(assigned_count: int) -> int:
        nonlocal visits
        visits += 1
        if visits > cap:
            raise OverflowError
        if assigned_count == vertex_count:
            return 1

        best_vertex = -1
        best_options: list[int] | None = None
        best_assigned_neighbors = -1
        for vertex in range(vertex_count):
            if assignment[vertex] >= 0:
                continue
            options = available(vertex)
            if not options:
                return 0
            assigned_neighbors = sum(assignment[w] >= 0 for w in adjacency[vertex])
            if (
                best_options is None
                or len(options) < len(best_options)
                or (
                    len(options) == len(best_options)
                    and assigned_neighbors > best_assigned_neighbors
                )
            ):
                best_vertex = vertex
                best_options = options
                best_assigned_neighbors = assigned_neighbors

        total = 0
        assert best_options is not None
        for color in best_options:
            assignment[best_vertex] = color
            total += dfs(assigned_count + 1)
            assignment[best_vertex] = -1
        return total

    try:
        return dfs(0)
    except OverflowError:
        return None


def _root_profile(
    vertex_count: int,
    edges: list[tuple[int, int]],
    adjacency: list[list[int]],
    root: int,
) -> tuple:
    distances = [-1] * vertex_count
    distances[root] = 0
    queue = deque([root])
    while queue:
        vertex = queue.popleft()
        for neighbor in adjacency[vertex]:
            if distances[neighbor] < 0:
                distances[neighbor] = distances[vertex] + 1
                queue.append(neighbor)

    profile = []
    for level in range(max(distances) + 1):
        vertices_here = sum(distance == level for distance in distances)
        within = 0
        forward = 0
        for u, v in edges:
            du, dv = distances[u], distances[v]
            if du == level and dv == level:
                within += 1
            elif (du == level and dv == level + 1) or (dv == level and du == level + 1):
                forward += 1
        profile.append((vertices_here, within, forward))
    return tuple(profile)


def canonical_key(inst: dict) -> str:
    """Return a strong relabeling-invariant fingerprint of the public graph.

    This is not claimed to be an exact graph-isomorphism canonical form.  It is
    the sorted multiset of rooted BFS layer profiles, including edge counts
    within and between consecutive layers.  It ignores seed, planted witness,
    input edge order/orientation, public vertex names, and palette names.
    """

    vertex_count = inst["vertex_count"]
    edges = sorted({_norm_edge(int(u), int(v)) for u, v in inst["edges"]})
    adjacency = _adjacency(vertex_count, edges)
    profiles = sorted(
        _root_profile(vertex_count, edges, adjacency, root)
        for root in range(vertex_count)
    )
    payload = json.dumps(
        [vertex_count, len(edges), profiles], separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | None:
    """Grow the same constant-degree CSP; return None past the practical window."""

    n = params.get("n")
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        return None
    degree = params.get("degree", 5)
    if isinstance(degree, bool) or not isinstance(degree, int):
        return None
    if n >= 36:
        return None
    return {"n": n + 6, "degree": degree}


def _records_from_indices(indices: list[int]) -> list[list[int]]:
    return [
        [vertex, DOMAIN[color][0], DOMAIN[color][1]]
        for vertex, color in enumerate(indices)
    ]


def _attack_outlier_rank(inst: dict) -> list[list[int]]:
    """Guess classes from public position and cheap per-vertex graph statistics."""

    adjacency = inst["adjacency"]
    vertex_count = inst["vertex_count"]
    scores = []
    for vertex in range(vertex_count):
        # All degrees are equal; cycle/common-neighbor and position information
        # are the remaining obvious per-element signatures.
        neighbor_set = set(adjacency[vertex])
        two_step = sum(
            1
            for u in adjacency[vertex]
            for w in adjacency[u]
            if w != vertex and w in neighbor_set
        )
        common_neighbor_mass = sum(
            len(set(adjacency[u]).intersection(adjacency[v]))
            for u, v in itertools.combinations(adjacency[vertex], 2)
        )
        scores.append(
            (
                len(adjacency[vertex]),
                two_step,
                common_neighbor_mass,
                sum(adjacency[vertex]),
                vertex,
            )
        )
    order = sorted(range(vertex_count), key=lambda vertex: scores[vertex])
    assigned = [0] * vertex_count
    for rank, vertex in enumerate(order):
        assigned[vertex] = rank % len(DOMAIN)
    return _records_from_indices(assigned)


def _attack_left_to_right_greedy(inst: dict) -> list[list[int]]:
    """Use the first target color compatible with already colored neighbors."""

    assignment = [-1] * inst["vertex_count"]
    for vertex in range(inst["vertex_count"]):
        options = [
            color
            for color in range(len(DOMAIN))
            if all(
                assignment[neighbor] < 0
                or assignment[neighbor] in TARGET_ADJ_SETS[color]
                for neighbor in inst["adjacency"][vertex]
            )
        ]
        assignment[vertex] = options[0] if options else 0
    return _records_from_indices(assignment)


def _attack_random_restart(
    inst: dict, rng: random.Random, restarts: int = 512
) -> list[list[int]] | None:
    """Randomized saturation-order greedy search with one-step look-ahead."""

    adjacency = inst["adjacency"]
    vertex_count = inst["vertex_count"]
    for _ in range(restarts):
        assignment = [-1] * vertex_count
        remaining = set(range(vertex_count))
        failed = False
        while remaining:
            saturation = {
                vertex: sum(assignment[w] >= 0 for w in adjacency[vertex])
                for vertex in remaining
            }
            best = max(saturation.values())
            choices = [vertex for vertex in remaining if saturation[vertex] == best]
            vertex = choices[rng.randrange(len(choices))]
            options = [
                color
                for color in range(len(DOMAIN))
                if all(
                    assignment[neighbor] < 0
                    or assignment[neighbor] in TARGET_ADJ_SETS[color]
                    for neighbor in adjacency[vertex]
                )
            ]
            if not options:
                failed = True
                break

            # Prefer choices leaving the most colors for unassigned neighbors,
            # but randomize ties.  There is no backtracking or local repair.
            option_scores = []
            for color in options:
                score = 0
                for neighbor in adjacency[vertex]:
                    if assignment[neighbor] >= 0:
                        continue
                    score += sum(
                        all(
                            assignment[w] < 0
                            or candidate in TARGET_ADJ_SETS[assignment[w]]
                            for w in adjacency[neighbor]
                            if w != vertex
                        )
                        and candidate in TARGET_ADJ_SETS[color]
                        for candidate in range(len(DOMAIN))
                    )
                option_scores.append(score)
            best_score = max(option_scores)
            best_options = [
                color for color, score in zip(options, option_scores) if score == best_score
            ]
            assignment[vertex] = best_options[rng.randrange(len(best_options))]
            remaining.remove(vertex)
        if not failed:
            candidate = _records_from_indices(assignment)
            if verify(inst, candidate)[0]:
                return candidate
    return None


def _attack_bounded_ac3(
    inst: dict, node_limit: int = 2_000
) -> list[list[int]] | None:
    """Try a real CSP attack: arc consistency plus MRV backtracking.

    KG(6,2) is vertex-transitive, so post-composing a solution with a palette
    permutation lets the attack fix public vertex 0 to target color 0 without
    loss of generality.  The strict node cap keeps this an adversary-panel probe
    rather than an unbounded oracle hidden inside ``selftest``.
    """

    vertex_count = inst["vertex_count"]
    all_colors = (1 << len(DOMAIN)) - 1
    domains = [all_colors] * vertex_count
    domains[0] = 1
    nodes = 0

    def revise(left_domain: int, right_domain: int) -> int:
        kept = 0
        remaining = left_domain
        while remaining:
            bit = remaining & -remaining
            remaining -= bit
            color = bit.bit_length() - 1
            if TARGET_ADJ_MASKS[color] & right_domain:
                kept |= bit
        return kept

    def propagate(state: list[int]) -> bool:
        changed = True
        while changed:
            changed = False
            for u, v in inst["edges"]:
                new_u = revise(state[u], state[v])
                if not new_u:
                    return False
                new_v = revise(state[v], new_u)
                if not new_v:
                    return False
                if new_u != state[u]:
                    state[u] = new_u
                    changed = True
                if new_v != state[v]:
                    state[v] = new_v
                    changed = True
        return True

    def dfs(state: list[int]) -> list[int] | None:
        nonlocal nodes
        nodes += 1
        if nodes > node_limit or not propagate(state):
            return None
        vertex = -1
        option_count = len(DOMAIN) + 1
        for candidate, domain in enumerate(state):
            count = domain.bit_count()
            if 1 < count < option_count:
                vertex = candidate
                option_count = count
        if vertex < 0:
            return [domain.bit_length() - 1 for domain in state]

        remaining = state[vertex]
        while remaining and nodes <= node_limit:
            bit = remaining & -remaining
            remaining -= bit
            child = state[:]
            child[vertex] = bit
            result = dfs(child)
            if result is not None:
                return result
        return None

    result = dfs(domains)
    return None if result is None else _records_from_indices(result)


def _corruptions(inst: dict) -> dict[str, object]:
    answer = [record[:] for record in inst["answer"]]

    swapped = None
    for first in range(inst["vertex_count"]):
        for second in range(first + 1, inst["vertex_count"]):
            candidate = [record[:] for record in answer]
            candidate[first][1:], candidate[second][1:] = (
                candidate[second][1:],
                candidate[first][1:],
            )
            if not verify(inst, candidate)[0]:
                swapped = candidate
                break
        if swapped is not None:
            break
    if swapped is None:
        raise RuntimeError("could not construct a rejected swap corruption")

    duplicate = [record[:] for record in answer]
    duplicate[-1][0] = duplicate[0][0]
    out_of_range = [record[:] for record in answer]
    out_of_range[0][1] = 6
    return {
        "drop_one": answer[:-1],
        "swap_two_color_sets": swapped,
        "duplicate_vertex": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }


def _relabel_instance(inst: dict, permutation: list[int]) -> dict:
    transformed = dict(inst)
    transformed["edges"] = [
        (permutation[u], permutation[v]) for u, v in inst["edges"]
    ]
    transformed["adjacency"] = _adjacency(inst["vertex_count"], transformed["edges"])
    transformed["answer"] = sorted(
        [[permutation[vertex], first, second] for vertex, first, second in inst["answer"]]
    )
    return transformed


def _reorder_instance(inst: dict, rng: random.Random) -> dict:
    transformed = dict(inst)
    edges = list(inst["edges"])
    rng.shuffle(edges)
    transformed["edges"] = [
        (v, u) if rng.randrange(2) else (u, v) for u, v in edges
    ]
    transformed["adjacency"] = _adjacency(inst["vertex_count"], transformed["edges"])
    return transformed


def _permute_palette_answer(answer: list[list[int]], permutation: list[int]) -> list[list[int]]:
    return [
        [vertex, permutation[first], permutation[second]]
        for vertex, first, second in answer
    ]


def selftest() -> dict:
    """Run all mandatory gates and return their machine-readable measurements."""

    report: dict[str, object] = {}

    # G1: every named preset and several seeds, plus determinism.
    g1_rows = {}
    g1_ok = True
    deterministic = True
    for preset, params in DIFFICULTY.items():
        rows = []
        for seed in (0, 1, 2, 3):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            same = inst == make_instance(seed=seed, **params)
            rows.append({"seed": seed, "ok": ok, "reason": reason, "deterministic": same})
            g1_ok = g1_ok and ok
            deterministic = deterministic and same
        g1_rows[preset] = rows
    report["G1_planted_verifies"] = {
        "pass": g1_ok and deterministic,
        "verified": sum(row["ok"] for rows in g1_rows.values() for row in rows),
        "total": sum(len(rows) for rows in g1_rows.values()),
        "deterministic_checks_passed": sum(
            row["deterministic"] for rows in g1_rows.values() for row in rows
        ),
        "by_preset": g1_rows,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=12_345, **shipping)

    # G2: all five requested corruption types, with distinct diagnostics.
    corruption_rows = {}
    reasons = []
    for name, candidate in _corruptions(inst).items():
        ok, reason = verify(inst, candidate)
        corruption_rows[name] = {"accepted": ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(not row["accepted"] for row in corruption_rows.values())
        and len(set(reasons)) == len(reasons),
        "rejected": sum(not row["accepted"] for row in corruption_rows.values()),
        "total": len(corruption_rows),
        "distinct_reasons": len(set(reasons)),
        "cases": corruption_rows,
    }

    # G3: prose outside the tags and a Markdown JSON fence inside them.
    realistic = (
        "I found a proper fractional coloring.\n\n<answer>\n```json\n"
        + json.dumps(inst["answer"])
        + "\n```\n</answer>\nThe records may be checked edge by edge."
    )
    parsed = parse_answer(realistic)
    garbage_cases = ["", "no tags here", "<answer>not json</answer>", "<answer>{}</answer>"]
    garbage_rejected = sum(parse_answer(text) is None for text in garbage_cases)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and garbage_rejected == len(garbage_cases),
        "parsed_records": len(parsed) if isinstance(parsed, list) else None,
        "garbage_rejected": garbage_rejected,
        "garbage_total": len(garbage_cases),
        "prose_and_fence": True,
    }

    # G4: candidates already obey record shape, full vertex coverage, range, and
    # two-distinct-colors.  This is the solver-aware 10^|V| prior, not raw JSON.
    guess_rng = random.Random(99_991)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            guess_hits += 1
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "p_hat": guess_rate,
        "threshold": 1e-6,
        "prior": "independent uniform choice among the fifteen valid 2-subsets at every named vertex",
        "structure_enforced": [
            "exactly one record per vertex",
            "two distinct colors per record",
            "all colors in 0..5",
        ],
        "semantic_search_space": search_space(inst),
    }

    # G5: n=1, degree=6 produces a relabeled KG(6,2).  The exact enumerator
    # counts all endomorphisms of the target, not only the planted one.
    sparse_rows = []
    sparse_ok = True
    for seed in (3, 7, 11):
        small = make_instance(n=1, degree=6, seed=seed)
        answers = enumerate_all(small)
        space = search_space(small)
        ratio = None if answers is None or space is None else answers / space
        sparse_rows.append(
            {
                "seed": seed,
                "vertices": small["vertex_count"],
                "valid_answers": answers,
                "search_space": space,
                "ratio": ratio,
            }
        )
        sparse_ok = sparse_ok and ratio is not None and ratio < 1e-6
    report["G5_sparse"] = {
        "pass": sparse_ok,
        "instances": sparse_rows,
        "threshold": 1e-6,
    }

    # G6: attacks know the target and public graph but never inspect the plant.
    attack_seeds = list(range(800, 808))
    attack_instances = {
        seed: make_instance(seed=seed, **shipping) for seed in attack_seeds
    }
    attacks = {
        "per_vertex_outlier_rank": lambda item, rng: _attack_outlier_rank(item),
        "left_to_right_greedy": lambda item, rng: _attack_left_to_right_greedy(item),
        "randomized_forward_greedy_512": lambda item, rng: _attack_random_restart(
            item, rng, 512
        ),
        "bounded_ac3_mrv_2000_nodes": lambda item, rng: _attack_bounded_ac3(
            item, 2_000
        ),
    }
    attack_rows = {}
    for name, attack in attacks.items():
        solved_seeds = []
        for seed, attack_inst in attack_instances.items():
            candidate = attack(attack_inst, random.Random(500_000 + seed))
            if candidate is not None and verify(attack_inst, candidate)[0]:
                solved_seeds.append(seed)
        attack_rows[name] = {
            "solved": len(solved_seeds),
            "total": len(attack_seeds),
            "solved_seeds": solved_seeds,
        }
    report["G6_adversary_panel"] = {
        "pass": all(row["solved"] == 0 for row in attack_rows.values()),
        "shipping_params": dict(shipping),
        "seeds": attack_seeds,
        "attacks": attack_rows,
    }

    # G7: doubling n doubles the graph while the hard-window degree is fixed.
    doubled = make_instance(n=shipping["n"] * 2, degree=shipping["degree"], seed=54_321)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["vertex_count"] == 2 * inst["vertex_count"]
        and doubled["edge_count"] == 2 * inst["edge_count"]
        and doubled["degree"] == shipping["degree"],
        "base_n": shipping["n"],
        "base_vertices": inst["vertex_count"],
        "doubled_n": doubled["n"],
        "doubled_vertices": doubled["vertex_count"],
        "doubled_edges": doubled["edge_count"],
        "degree": doubled["degree"],
        "search_space_growth_factor": len(DOMAIN) ** inst["vertex_count"],
        "verify_ok": doubled_ok,
        "verify_reason": doubled_reason,
    }

    # G8: edge reorder/orientation, vertex renaming, their composition, and the
    # five-color palette symmetry.  Carried witnesses prove the maps are real.
    invariance_checks = 0
    invariance_passed = 0
    carried_checks = 0
    carried_passed = 0
    answer_independence_checks = 0
    answer_independence_passed = 0
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(seed=20_000 + seed, **shipping)
        base_key = canonical_key(base)
        unrelated_keys.append(base_key)
        transform_rng = random.Random(70_000 + seed)
        vertex_permutation = list(range(base["vertex_count"]))
        transform_rng.shuffle(vertex_permutation)
        palette_permutation = list(PALETTE)
        transform_rng.shuffle(palette_permutation)

        reordered = _reorder_instance(base, transform_rng)
        relabeled = _relabel_instance(base, vertex_permutation)
        composed = _reorder_instance(relabeled, transform_rng)
        for transformed in (reordered, relabeled, composed):
            invariance_checks += 1
            if canonical_key(transformed) == base_key:
                invariance_passed += 1
            carried_checks += 1
            if verify(transformed, transformed["answer"])[0]:
                carried_passed += 1

        palette_answer = _permute_palette_answer(base["answer"], palette_permutation)
        carried_checks += 1
        if verify(base, palette_answer)[0]:
            carried_passed += 1

        no_answer = dict(base)
        no_answer["answer"] = []
        answer_independence_checks += 1
        if canonical_key(no_answer) == base_key:
            answer_independence_passed += 1

    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariance_passed == invariance_checks
        and carried_passed == carried_checks
        and answer_independence_passed == answer_independence_checks
        and distinct == len(unrelated_keys),
        "invariance_checks_passed": invariance_passed,
        "invariance_checks_total": invariance_checks,
        "carried_answer_checks_passed": carried_passed,
        "carried_answer_checks_total": carried_checks,
        "answer_independence_checks_passed": answer_independence_passed,
        "answer_independence_checks_total": answer_independence_checks,
        "distinct_unrelated_keys": distinct,
        "unrelated_instances": len(unrelated_keys),
        "transformations": [
            "edge reorder and endpoint reversal",
            "arbitrary vertex relabeling",
            "vertex relabeling composed with edge reordering",
            "global permutation of the six palette colors (witness symmetry)",
        ],
        "key_kind": "rooted BFS layer/edge-profile multiset (strong invariant, not exact GI canonicalization)",
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
