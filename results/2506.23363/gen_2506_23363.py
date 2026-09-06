"""Verified inverse generator for Critical Node Cut (arXiv:2506.23363).

The instances use the x=0 specialization identified in the paper: deleting a
set with zero remaining connected pairs is exactly deleting a vertex cover.
The graph is a shuffled standard SAT-to-Vertex-Cover construction for a
balanced, planted NAE-3-SAT formula.  Only the graph is exposed to solvers.

This module is deterministic for ``(n, seed, params)``, uses only the Python
standard library, performs no file I/O, and has no import-time side effects.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re
from collections import Counter


DIFFICULTY = {
    # n is the number of Boolean variables.  Each constraint becomes a pair of
    # complementary 3-clauses, and then two clause triangles in the CNC graph.
    # The budget, treewidth proxies, and structured search exponent all grow
    # linearly with n; the mean constraint degree stays in the empirically hard
    # planted region instead of making density a giveaway.
    # A readable worked-example/calibration rung.  It is intentionally not a
    # shipping candidate and is expected to fall to both attacks and oracles.
    "demo": {"n": 3, "constraint_degree": 1},
    "easy": {"n": 66, "constraint_degree": 8},
    "medium": {"n": 90, "constraint_degree": 8},
    "hard": {"n": 114, "constraint_degree": 8},
}

SHIPPING_DIFFICULTY = "easy"


NOTES = r"""
Paper basis.  Section 2 (Preliminaries) defines Critical Node Cut on a simple
undirected graph G: find at most k vertices whose deletion leaves at most x
unordered connected vertex pairs, where pairs(G)=sum_C binom(|C|,2).  The
Introduction explicitly observes that x=0 is Vertex Cover, so the family here
is an exact special case of the paper's problem.  Section 3, Theorem
CNC:fes, proves the stronger general problem W[1]-hard for the combined
parameter k+feedback-edge-number+maximum-degree+pathwidth.  The Introduction
also recalls the tight ETH n^{o(k)} lower bound for CNC.  For x=0 the usual
NP-completeness of Vertex Cover supplies the direct worst-case hardness.

Easy regimes avoided.  The Introduction records polynomial algorithms on
trees, an n^{O(treewidth)} dynamic program, FPT algorithms for x+treewidth and
vertex-cover number, and W[1]-hardness by k.  Section 4 gives FPT algorithms for
max-leaf number, vertex integrity, and modular-width and an XP algorithm for
clique-width; Section 5 gives an FPT approximation scheme by treewidth.  Here k
is linear in graph size, x+treewidth is not bounded because the random
incidence core has growing width, and the graphs have growing max-leaf number,
integrity, modular-width, and clique-width proxies.  Exact x=0 also makes an
approximation to the pair objective irrelevant: a witness must cover every
edge.

Inverse generation.  The abstract answer is sampled first: one truth choice
per variable and one omitted (true) literal vertex in each future clause
triangle.  Only afterward are a random bounded-degree 3-uniform constraint
hypergraph and literal signs built around that witness.  Every NAE constraint
is emitted with its complementary clause.  Consequently each variable's two
literal vertices have exactly equal degree and are exchanged by a global graph
automorphism; positive and negative literal frequencies are exactly balanced.
Clause vertices all have the same degree.  A final uniform vertex relabelling
and edge shuffle remove construction order.

Attacks.  The outlier attack ranks vertices by degree and two-hop degree
statistics, then makes the locally best clause choice.  Complement pairing
removes its per-element signal.  The greedy attack repeatedly deletes the
vertex incident to most currently uncovered edges.  The random-restart attack
uses multiple random gadget-respecting assignments plus strict-improvement
single-variable hill climbing and locally optimal clause omissions.  selftest
requires all three to solve zero of eight shipping-level seeds.  An earlier
n=60 candidate was rejected after the hill climber solved seed 5 (one of eight
panel seeds); increasing the core to n=66 made the same attack fail 8/8 while
preserving constraint density and all plant/decoy symmetries.  Stronger
WalkSAT variants, spectral recovery, and complete SAT/Vertex-Cover solvers are
explicitly outside this cheap panel and remain caveats rather than claimed
defeats.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"```(?:json|text)?\s*(.*?)\s*```", re.I | re.S)
_ENUMERATION_CAP = 250_000


def _validate_parameters(n: int, degree: int) -> tuple[int, int]:
    if isinstance(n, bool) or not isinstance(n, int) or n < 3 or n % 3:
        raise ValueError("n must be an integer at least 3 and divisible by 3")
    if isinstance(degree, bool) or not isinstance(degree, int):
        raise ValueError("constraint_degree must be an integer")
    if degree < 1 or degree == 2:
        raise ValueError("constraint_degree must be 1 or at least 3")
    if degree > n - 2:
        raise ValueError("constraint_degree must be at most n-2")
    return n, degree


def _degree_sequence(n: int, mean_degree: int, rng: random.Random) -> list[int]:
    """A varied sequence of sum n*mean_degree, bounded away from degree 2.

    Variation makes cheap isomorphism invariants useful without distinguishing
    the two literal vertices belonging to any one variable: both receive the
    same occurrence degree later.
    """

    degrees = [mean_degree] * n
    if mean_degree < 5:
        return degrees
    low, high = mean_degree - 3, mean_degree + 3
    for _ in range(4 * n):
        a = rng.randrange(n)
        b = rng.randrange(n - 1)
        if b >= a:
            b += 1
        if degrees[a] < high and degrees[b] > low:
            degrees[a] += 1
            degrees[b] -= 1
    return degrees


def _simple_hypergraph(degrees: list[int], rng: random.Random) -> list[tuple[int, int, int]]:
    """Realize a degree sequence as a simple 3-uniform hypergraph by rejection."""

    stubs = [v for v, degree in enumerate(degrees) for _ in range(degree)]
    if len(stubs) % 3:
        raise AssertionError("the constraint degree sum must be divisible by three")
    for _ in range(20_000):
        rng.shuffle(stubs)
        triples = [tuple(sorted(stubs[i:i + 3])) for i in range(0, len(stubs), 3)]
        if all(len(set(triple)) == 3 for triple in triples) and len(set(triples)) == len(triples):
            return triples
    raise RuntimeError("could not realize a simple constraint hypergraph")


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Sample a deletion witness first, then construct a CNC instance around it.

    ``n`` counts hidden Boolean variables.  ``constraint_degree`` is the mean
    number of NAE constraints incident with a variable.  It is kept constant
    across a difficulty ladder, so doubling n doubles the random constraint
    core and increases the generic exponential search exponent.
    """

    degree = params.pop("constraint_degree", 8)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    n, degree = _validate_parameters(n, degree)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    constraint_count = n * degree // 3

    # G: sample the complete abstract witness before any graph data.  An
    # omission pair (a,b) says to leave position a out of the first clause
    # triangle and position b out of its complementary triangle.  a != b lets
    # us choose a truth pattern in which both omitted literals are true.
    planted_assignment = [rng.getrandbits(1) for _ in range(n)]
    omission_pairs: list[tuple[int, int]] = []
    for _ in range(constraint_count):
        a = rng.randrange(3)
        b = rng.randrange(2)
        if b >= a:
            b += 1
        omission_pairs.append((a, b))

    # Everything below is problem construction conditioned on that witness.
    variable_degrees = _degree_sequence(n, degree, rng)
    constraints = _simple_hypergraph(variable_degrees, rng)
    if len(constraints) != constraint_count:
        raise AssertionError("internal constraint count mismatch")

    # Old vertex numbers are zero-based and never exposed.  Variable vertex
    # 2*i+b represents literal x_i when b=1 and not-x_i when b=0.
    edges: list[tuple[int, int]] = []
    answer_old: list[int] = []
    variable_edges_old: list[tuple[int, int]] = []
    clause_triangles_old: list[tuple[int, int, int]] = []
    for i, bit in enumerate(planted_assignment):
        pair = (2 * i, 2 * i + 1)
        variable_edges_old.append(pair)
        edges.append(pair)
        answer_old.append(2 * i + bit)

    next_vertex = 2 * n
    for variables, (omit_first, omit_second) in zip(constraints, omission_pairs):
        remaining_position = 3 - omit_first - omit_second
        truth = [0, 0, 0]
        truth[omit_first] = 1
        truth[omit_second] = 0
        truth[remaining_position] = rng.getrandbits(1)
        first_literals = tuple(
            planted_assignment[var] if truth[pos] else 1 - planted_assignment[var]
            for pos, var in enumerate(variables)
        )

        for complement, omitted in ((False, omit_first), (True, omit_second)):
            triangle = (next_vertex, next_vertex + 1, next_vertex + 2)
            next_vertex += 3
            clause_triangles_old.append(triangle)
            edges.extend(((triangle[0], triangle[1]),
                          (triangle[0], triangle[2]),
                          (triangle[1], triangle[2])))
            for pos, (clause_vertex, var) in enumerate(zip(triangle, variables)):
                literal_bit = first_literals[pos] ^ int(complement)
                edges.append((clause_vertex, 2 * var + literal_bit))
                if pos != omitted:
                    answer_old.append(clause_vertex)

    vertex_count = next_vertex
    budget = n + 4 * constraint_count
    if len(answer_old) != budget:
        raise AssertionError("internal witness size mismatch")

    # Hide construction order with a uniform global relabelling to 1..N.
    labels = list(range(1, vertex_count + 1))
    rng.shuffle(labels)
    relabelled_edges = [tuple(sorted((labels[u], labels[v]))) for u, v in edges]
    rng.shuffle(relabelled_edges)
    answer = [labels[v] for v in answer_old]
    rng.shuffle(answer)
    variable_edges = [tuple(sorted((labels[u], labels[v]))) for u, v in variable_edges_old]
    clause_triangles = [tuple(sorted(labels[v] for v in triangle))
                        for triangle in clause_triangles_old]

    return {
        "family": "Critical Node Cut (x=0 / Vertex Cover)",
        "n": n,
        "constraint_degree": degree,
        "constraint_count": constraint_count,
        "vertex_count": vertex_count,
        "edges": [list(edge) for edge in relabelled_edges],
        "k": budget,
        "x": 0,
        # These blocks are exactly recoverable from degrees and triangle
        # components; keeping them avoids repeating that linear-time work in
        # the 200k-sample G4 test.  They contain no planted choices.
        "_variable_edges": [list(edge) for edge in variable_edges],
        "_clause_triangles": [list(triangle) for triangle in clause_triangles],
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Return the complete standalone problem statement seen by a solver."""

    edge_lines = "\n".join(f"{u} {v}" for u, v in inst["edges"])
    return f"""CRITICAL NODE CUT — EXACT ZERO-PAIR WITNESS

You are given a simple undirected graph.  Vertices are the integers 1 through
{inst['vertex_count']}, inclusive.  Each row in the edge list is one unordered
edge {{u,v}}; there are no loops or duplicate edges.

For a deletion set S, remove every vertex in S and every incident edge.  Two
distinct remaining vertices form a connected pair when an undirected path
joins them in the remaining graph.  If the remaining connected components
have sizes c_1,c_2,..., the number of unordered connected pairs is
sum_i c_i*(c_i-1)/2.

Find exactly {inst['k']} distinct vertices whose deletion leaves at most
{inst['x']} connected pairs.  Because the bound is zero, equivalently every
listed edge must have at least one endpoint in your deletion set.  Order does
not matter.  Repeated vertices are forbidden, and no vertex outside the
inclusive range 1..{inst['vertex_count']} is allowed.

VERTEX_COUNT {inst['vertex_count']}
EDGE_COUNT {len(inst['edges'])}
DELETE_EXACTLY {inst['k']}
CONNECTED_PAIR_BOUND {inst['x']}
EDGES
{edge_lines}
END_EDGES

Give your final answer inside <answer></answer> tags, as a comma-separated list
of exactly {inst['k']} distinct vertex integers.
Syntax example only, for a hypothetical instance asking for three vertices:
<answer>3, 17, 42</answer>
Output nothing else inside the tags."""


def _parse_integer_list(body: str) -> list[int] | None:
    body = body.strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    if body.startswith("[") and body.endswith("]"):
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            return None
        if isinstance(value, list) and all(
            isinstance(v, int) and not isinstance(v, bool) for v in value
        ):
            return value
        return None
    if not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", body):
        return None
    try:
        return [int(piece.strip()) for piece in body.split(",")]
    except ValueError:
        return None


def parse_answer(text: str) -> object | None:
    """Extract a tagged integer list, tolerating prose and Markdown fences."""

    if not isinstance(text, str):
        return None
    bodies = list(reversed(_ANSWER_RE.findall(text)))
    bodies.extend(reversed(_FENCE_RE.findall(text)))
    for body in bodies:
        parsed = _parse_integer_list(body)
        if parsed is not None:
            return parsed
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid CNC deletion witness; never consult ``inst['answer']``."""

    if not isinstance(answer, list):
        return False, "answer must be a list of vertex integers"
    if not answer:
        return False, "answer is empty"
    if any(not isinstance(v, int) or isinstance(v, bool) for v in answer):
        return False, "every vertex must be an integer"
    if len(answer) != inst["k"]:
        return False, f"expected exactly {inst['k']} vertices, got {len(answer)}"
    if len(set(answer)) != len(answer):
        return False, "answer contains a duplicate vertex"
    vertex_count = inst["vertex_count"]
    for vertex in answer:
        if vertex < 1 or vertex > vertex_count:
            return False, f"vertex {vertex} is outside the inclusive range 1..{vertex_count}"

    deleted = set(answer)
    if inst["x"] == 0:
        for u, v in inst["edges"]:
            if u not in deleted and v not in deleted:
                return False, f"connected-pair bound exceeded: uncovered edge {u} {v} remains"
        return True, "ok"

    # The family currently ships x=0, but this exact component computation
    # keeps the checker faithful if a future preset uses a positive bound.
    adjacency = [[] for _ in range(vertex_count + 1)]
    for u, v in inst["edges"]:
        if u not in deleted and v not in deleted:
            adjacency[u].append(v)
            adjacency[v].append(u)
    seen = set(deleted)
    pairs = 0
    for start in range(1, vertex_count + 1):
        if start in seen:
            continue
        seen.add(start)
        stack = [start]
        size = 0
        while stack:
            vertex = stack.pop()
            size += 1
            for neighbor in adjacency[vertex]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        pairs += size * (size - 1) // 2
    if pairs > inst["x"]:
        return False, f"connected-pair bound exceeded: got {pairs}, limit {inst['x']}"
    return True, "ok"


def _blocks(inst: dict) -> tuple[list[tuple[int, int]], list[tuple[int, int, int]]]:
    return ([tuple(block) for block in inst["_variable_edges"]],
            [tuple(block) for block in inst["_clause_triangles"]])


def _recover_blocks_from_graph(inst: dict) -> tuple[list[tuple[int, int]],
                                                    list[tuple[int, int, int]]]:
    """Recover every forced local block using only the solver-visible graph."""

    adjacency = _graph_data(inst)
    clause_vertices = {v for v in range(1, inst["vertex_count"] + 1)
                       if len(adjacency[v]) == 3}
    variable_vertices = set(range(1, inst["vertex_count"] + 1)) - clause_vertices
    variable_edges = sorted(
        tuple(sorted((u, v)))
        for u, v in inst["edges"]
        if u in variable_vertices and v in variable_vertices
    )

    unseen = set(clause_vertices)
    triangles: list[tuple[int, int, int]] = []
    while unseen:
        start = min(unseen)
        component = set()
        stack = [start]
        unseen.remove(start)
        while stack:
            vertex = stack.pop()
            component.add(vertex)
            for neighbor in adjacency[vertex] & clause_vertices:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
        if len(component) != 3:
            raise ValueError("visible degree-3 subgraph is not partitioned into triangles")
        triangle = tuple(sorted(component))
        if any(v not in adjacency[u] for u, v in itertools.combinations(triangle, 2)):
            raise ValueError("visible clause component is not a triangle")
        triangles.append(triangle)
    return variable_edges, sorted(triangles)


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the obvious gadget-respecting candidate space.

    Every variable edge is covered with exactly one endpoint and every clause
    triangle with exactly two vertices.  Those disjoint local lower bounds sum
    to k, so any size-k solution has exactly this shape.  Only the occurrence
    edges remain to test.  The sampling is independent of the planted answer.
    """

    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    variable_edges, clause_triangles = _blocks(inst)
    candidate: list[int] = []
    for u, v in variable_edges:
        candidate.append((u, v)[rng.getrandbits(1)])
    for triangle in clause_triangles:
        omitted = rng.randrange(3)
        candidate.extend(vertex for pos, vertex in enumerate(triangle) if pos != omitted)
    return candidate


def search_space(inst: dict) -> int | None:
    """Naive space of unordered, distinct, exactly-k deletion sets."""

    return math.comb(inst["vertex_count"], inst["k"])


def enumerate_all(inst: dict) -> int | None:
    """Count all valid witnesses by bounded brute force over forced blocks."""

    variable_edges, clause_triangles = _blocks(inst)
    structured_space = (2 ** len(variable_edges)) * (3 ** len(clause_triangles))
    if structured_space > _ENUMERATION_CAP:
        return None
    choices: list[tuple[tuple[int, ...], ...]] = []
    for u, v in variable_edges:
        choices.append(((u,), (v,)))
    for a, b, c in clause_triangles:
        choices.append(((a, b), (a, c), (b, c)))
    count = 0
    for picked in itertools.product(*choices):
        candidate = [vertex for part in picked for vertex in part]
        if verify(inst, candidate)[0]:
            count += 1
    return count


def _canonical_wl_certificate(inst: dict) -> list:
    """A strong cheap isomorphism invariant based on color refinement."""

    vertex_count = inst["vertex_count"]
    adjacency = [[] for _ in range(vertex_count)]
    normalized_edges: list[tuple[int, int]] = []
    for raw_u, raw_v in inst["edges"]:
        u, v = raw_u - 1, raw_v - 1
        if u > v:
            u, v = v, u
        normalized_edges.append((u, v))
        adjacency[u].append(v)
        adjacency[v].append(u)

    adjacency_sets = [set(neighbors) for neighbors in adjacency]
    triangle_counts = []
    for vertex in range(vertex_count):
        neighbors = sorted(adjacency[vertex])
        edge_count = sum(
            1
            for i, u in enumerate(neighbors)
            for v in neighbors[i + 1:]
            if v in adjacency_sets[u]
        )
        triangle_counts.append(edge_count)

    initial = [(len(adjacency[v]), triangle_counts[v]) for v in range(vertex_count)]
    palette = {signature: color for color, signature in enumerate(sorted(set(initial)))}
    colors = [palette[signature] for signature in initial]
    for _ in range(16):
        signatures = []
        for vertex in range(vertex_count):
            neighbor_colors = tuple(sorted(Counter(colors[w] for w in adjacency[vertex]).items()))
            signatures.append((colors[vertex], neighbor_colors))
        palette = {signature: color for color, signature in enumerate(sorted(set(signatures)))}
        new_colors = [palette[signature] for signature in signatures]
        old_count = len(set(colors))
        colors = new_colors
        if len(palette) == old_count:
            break

    color_histogram = sorted(Counter(colors).items())
    edge_color_histogram: Counter[tuple[int, int]] = Counter()
    for u, v in normalized_edges:
        a, b = colors[u], colors[v]
        if a > b:
            a, b = b, a
        edge_color_histogram[(a, b)] += 1
    return [
        vertex_count,
        len(normalized_edges),
        inst["k"],
        inst["x"],
        color_histogram,
        sorted((a, b, count) for (a, b), count in edge_color_histogram.items()),
    ]


def canonical_key(inst: dict) -> str:
    """Return a relabelling- and edge-order-invariant structural key.

    Exact graph canonization is not known to be polynomial-time.  This uses
    stabilized Weisfeiler-Leman color refinement, enriched by triangle counts
    and color-pair edge counts.  It can collide on adversarial non-isomorphic
    graphs; the README records that limitation.  It never uses the seed,
    answer, input order, or rendered text.
    """

    payload = json.dumps(_canonical_wl_certificate(inst), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase the random constraint core while preserving its hard density."""

    if not isinstance(params, dict):
        return None
    n = params.get("n")
    degree = params.get("constraint_degree", 8)
    if not isinstance(n, int) or n >= 150:
        return None
    return {"n": n + 18, "constraint_degree": degree}


def _graph_data(inst: dict):
    vertex_count = inst["vertex_count"]
    adjacency = [set() for _ in range(vertex_count + 1)]
    for u, v in inst["edges"]:
        adjacency[u].add(v)
        adjacency[v].add(u)
    return adjacency


def _candidate_from_variable_choices(inst: dict, selected_variables: set[int],
                                     rng: random.Random | None = None) -> list[int]:
    """Finish a variable choice with locally best clause omissions."""

    _, triangles = _blocks(inst)
    adjacency = _graph_data(inst)
    candidate = list(selected_variables)
    for triangle in triangles:
        triangle_set = set(triangle)
        satisfiers = []
        for vertex in triangle:
            external = next(neighbor for neighbor in adjacency[vertex]
                            if neighbor not in triangle_set)
            if external in selected_variables:
                satisfiers.append(vertex)
        if satisfiers:
            omitted = rng.choice(satisfiers) if rng is not None else min(satisfiers)
        else:
            omitted = rng.choice(triangle) if rng is not None else min(triangle)
        candidate.extend(vertex for vertex in triangle if vertex != omitted)
    return candidate


def _outlier_attack(inst: dict) -> list[int]:
    """Choose each element using only cheap per-vertex structural statistics."""

    adjacency = _graph_data(inst)
    degrees = [len(neighbors) for neighbors in adjacency]

    def score(vertex: int):
        neighbor_degrees = [degrees[w] for w in adjacency[vertex]]
        return (degrees[vertex], sum(neighbor_degrees),
                sum(value * value for value in neighbor_degrees), -vertex)

    variable_edges, _ = _blocks(inst)
    selected = {max(edge, key=score) for edge in variable_edges}
    return _candidate_from_variable_choices(inst, selected)


def _greedy_attack(inst: dict) -> list[int]:
    """Repeatedly delete the vertex covering most currently uncovered edges."""

    vertex_count = inst["vertex_count"]
    selected: set[int] = set()
    edges = [tuple(edge) for edge in inst["edges"]]
    while len(selected) < inst["k"]:
        scores = [0] * (vertex_count + 1)
        uncovered = 0
        for u, v in edges:
            if u not in selected and v not in selected:
                scores[u] += 1
                scores[v] += 1
                uncovered += 1
        if not uncovered:
            fill = next(vertex for vertex in range(1, vertex_count + 1)
                        if vertex not in selected)
            selected.add(fill)
            continue
        best = max((scores[vertex], -vertex, vertex)
                   for vertex in range(1, vertex_count + 1)
                   if vertex not in selected)[2]
        selected.add(best)
    return sorted(selected)


def _random_restart_attack(inst: dict, attack_seed: int, restarts: int = 16) -> list[int]:
    """Random assignments plus strict-improvement one-variable hill climbing."""

    rng = random.Random(attack_seed)
    variable_edges, triangles = _blocks(inst)
    adjacency = _graph_data(inst)
    node_to_variable = {}
    for index, edge in enumerate(variable_edges):
        for vertex in edge:
            node_to_variable[vertex] = index

    external_by_clause: list[tuple[int, int, int]] = []
    incident_clauses = [set() for _ in variable_edges]
    for clause_index, triangle in enumerate(triangles):
        triangle_set = set(triangle)
        externals = tuple(next(neighbor for neighbor in adjacency[vertex]
                               if neighbor not in triangle_set)
                          for vertex in triangle)
        external_by_clause.append(externals)
        for external in externals:
            incident_clauses[node_to_variable[external]].add(clause_index)

    best_selected: set[int] | None = None
    best_score = len(triangles) + 1
    for _ in range(restarts):
        selected = {edge[rng.getrandbits(1)] for edge in variable_edges}

        def unsatisfied(clause_index: int) -> bool:
            return not any(vertex in selected for vertex in external_by_clause[clause_index])

        flags = [unsatisfied(i) for i in range(len(triangles))]
        score = sum(flags)
        if score < best_score:
            best_score, best_selected = score, set(selected)
        for _step in range(4 * len(variable_edges)):
            improving: list[tuple[int, int]] = []
            next_score = score
            for variable, (u, v) in enumerate(variable_edges):
                old, new = (u, v) if u in selected else (v, u)
                selected.remove(old)
                selected.add(new)
                trial = score
                for clause_index in incident_clauses[variable]:
                    trial += int(unsatisfied(clause_index)) - int(flags[clause_index])
                selected.remove(new)
                selected.add(old)
                if trial < next_score:
                    next_score = trial
                    improving = [(variable, trial)]
                elif trial == next_score and trial < score:
                    improving.append((variable, trial))
            if not improving:
                break
            variable, score = rng.choice(improving)
            u, v = variable_edges[variable]
            old, new = (u, v) if u in selected else (v, u)
            selected.remove(old)
            selected.add(new)
            for clause_index in incident_clauses[variable]:
                flags[clause_index] = unsatisfied(clause_index)
            if score < best_score:
                best_score, best_selected = score, set(selected)
            if score == 0:
                return _candidate_from_variable_choices(inst, selected, rng)
    if best_selected is None:
        best_selected = {edge[0] for edge in variable_edges}
    return _candidate_from_variable_choices(inst, best_selected, rng)


def _transformed_instance(inst: dict, permutation: list[int], reverse_edges: bool) -> dict:
    """Relabel a graph and carry all vertex-valued data through the map."""

    if sorted(permutation) != list(range(1, inst["vertex_count"] + 1)):
        raise ValueError("permutation must contain every new label exactly once")

    def mapped(vertex: int) -> int:
        return permutation[vertex - 1]

    transformed = dict(inst)
    transformed["edges"] = [list(sorted((mapped(u), mapped(v)))) for u, v in inst["edges"]]
    if reverse_edges:
        transformed["edges"].reverse()
    transformed["answer"] = [mapped(vertex) for vertex in inst["answer"]]
    transformed["_variable_edges"] = [list(sorted((mapped(u), mapped(v))))
                                       for u, v in inst["_variable_edges"]]
    transformed["_clause_triangles"] = [list(sorted(mapped(v) for v in triangle))
                                         for triangle in inst["_clause_triangles"]]
    return transformed


def selftest() -> dict:
    """Run and report all mandatory G1--G8 gates."""

    report: dict[str, object] = {}

    # G1: all presets, several unrelated seeds.
    g1_checks = 0
    g1_failures = []
    for preset, preset_params in DIFFICULTY.items():
        for seed in (0, 1, 2, 17):
            instance = make_instance(seed=seed, **preset_params)
            ok, reason = verify(instance, instance["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=12345, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = list(shipping["answer"])

    # G2: five distinct corruptions with five distinct diagnostics.
    variable_edges, _ = _blocks(shipping)
    planted_set = set(planted)
    chosen_variable = next(v for edge in variable_edges for v in edge if v in planted_set)
    its_pair = next(edge for edge in variable_edges if chosen_variable in edge)
    mate = its_pair[0] if its_pair[1] == chosen_variable else its_pair[1]
    replacement = next(v for v in range(1, shipping["vertex_count"] + 1)
                       if v not in planted_set and v != mate)
    swapped = list(planted)
    swapped[swapped.index(chosen_variable)] = replacement
    duplicate = list(planted)
    duplicate[-1] = duplicate[0]
    out_of_range = list(planted)
    out_of_range[-1] = shipping["vertex_count"] + 1
    corruptions = {
        "drop_one": planted[:-1],
        "swap_one": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": (all(entry["rejected"] for entry in corruption_results.values())
                 and len(set(reasons)) == len(reasons)),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: model-style prose and a fenced tagged answer round-trip exactly.
    body = ", ".join(map(str, planted))
    response = ("I checked every remaining component.\n\n```text\n"
                f"<answer>\n{body}\n</answer>\n```\n")
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_length": len(parsed) if isinstance(parsed, list) else None,
        "expected_length": len(planted),
    }

    # G4: actual structure-aware Monte Carlo, not the naive binomial space.
    guess_instance = make_instance(seed=20250623, **DIFFICULTY[SHIPPING_DIFFICULTY])
    cached_variables, cached_triangles = _blocks(guess_instance)
    recovered_variables, recovered_triangles = _recover_blocks_from_graph(guess_instance)
    blocks_recovered = (sorted(cached_variables) == recovered_variables
                        and sorted(cached_triangles) == recovered_triangles)
    guess_rng = random.Random(0x250623363)
    total = 200_000
    hits = 0
    for _ in range(total):
        if verify(guess_instance, random_candidate(guess_instance, guess_rng))[0]:
            hits += 1
    measured = hits / total
    structured_space = ((2 ** guess_instance["n"])
                        * (3 ** len(guess_instance["_clause_triangles"])))
    report["G4_guess_resistance"] = {
        "pass": measured < 1e-6 and blocks_recovered,
        "hits": hits,
        "total": total,
        "measured_probability": measured,
        "analytical_upper_bound": (2 / 9) ** guess_instance["constraint_count"],
        "prior": "uniform over one endpoint per variable edge and two vertices per clause triangle",
        "blocks_recovered_from_visible_graph": blocks_recovered,
        "structure_aware_space": structured_space,
        "naive_space": search_space(guess_instance),
    }

    # G5: a small instance is fully enumerable; report its exact density in
    # the naive exactly-k subset space.
    small = make_instance(n=6, seed=314159, constraint_degree=1)
    valid_count = enumerate_all(small)
    naive_space = search_space(small)
    fraction = None if valid_count is None else valid_count / naive_space
    report["G5_sparse"] = {
        "pass": valid_count is not None and 0 < valid_count and fraction < 1e-3,
        "instance": {"n": 6, "constraint_degree": 1, "seed": 314159},
        "valid_answers": valid_count,
        "naive_candidates": naive_space,
        "solution_fraction": fraction,
    }

    # G6: three construction-aware cheap attacks, eight fresh seeds each.
    attack_results = {
        "outlier_degree_two_hop": {"solved": 0, "attempts": 8},
        "greedy_max_uncovered_degree": {"solved": 0, "attempts": 8},
        "random_restart_hill_climb": {"solved": 0, "attempts": 8},
    }
    for seed in range(8):
        instance = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_degree_two_hop": _outlier_attack(instance),
            "greedy_max_uncovered_degree": _greedy_attack(instance),
            "random_restart_hill_climb": _random_restart_attack(
                instance, attack_seed=0xC0FFEE + seed
            ),
        }
        for name, candidate in candidates.items():
            if verify(instance, candidate)[0]:
                attack_results[name]["solved"] += 1
    for result in attack_results.values():
        result["failed"] = result["attempts"] - result["solved"]
    report["G6_adversary_panel"] = {
        "pass": all(result["solved"] == 0 for result in attack_results.values()),
        "shipping_preset": SHIPPING_DIFFICULTY,
        "seeds": list(range(8)),
        "attacks": attack_results,
    }

    # G7: double n at constant density, verify the plant and growth in both
    # graph size and the shape-correct search space.
    base_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    base = make_instance(seed=2718, **base_params)
    doubled_params = dict(base_params, n=2 * base_params["n"])
    doubled = make_instance(seed=2718, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (doubled_ok and doubled["vertex_count"] > base["vertex_count"]
                 and search_space(doubled) > search_space(base)),
        "base_n": base_params["n"],
        "doubled_n": doubled_params["n"],
        "base_vertices": base["vertex_count"],
        "doubled_vertices": doubled["vertex_count"],
        "base_search_bits": search_space(base).bit_length(),
        "doubled_search_bits": search_space(doubled).bit_length(),
        "doubled_planted_reason": doubled_reason,
    }

    # G8: arbitrary vertex permutations, input reorderings, and their
    # composition.  Carrying the answer through proves each map is real.
    invariance_checks = 0
    transformed_witness_checks = 0
    g8_failures = []
    unrelated_keys = []
    for seed in range(20):
        instance = make_instance(seed=10_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        original_key = canonical_key(instance)
        unrelated_keys.append(original_key)
        identity = list(range(1, instance["vertex_count"] + 1))
        reordered = _transformed_instance(instance, identity, reverse_edges=True)
        perm = list(identity)
        random.Random(90_000 + seed).shuffle(perm)
        relabelled = _transformed_instance(instance, perm, reverse_edges=False)
        composed = _transformed_instance(instance, perm, reverse_edges=True)
        for name, transformed in (("edge_order", reordered),
                                  ("vertex_relabel", relabelled),
                                  ("composition", composed)):
            invariance_checks += 1
            if canonical_key(transformed) != original_key:
                g8_failures.append({"seed": seed, "transform": name,
                                    "failure": "key changed"})
        witness_ok, witness_reason = verify(relabelled, relabelled["answer"])
        transformed_witness_checks += 1
        if not witness_ok:
            g8_failures.append({"seed": seed, "transform": "vertex_relabel",
                                "failure": witness_reason})
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_keys == len(unrelated_keys),
        "invariance_checks": invariance_checks,
        "transformed_witness_checks": transformed_witness_checks,
        "distinct_unrelated": distinct_keys,
        "unrelated_total": len(unrelated_keys),
        "failures": g8_failures,
        "invariant": "triangle-enriched stabilized WL color/edge histogram",
    }

    gate_values = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(isinstance(value, dict) and value.get("pass")
                                  for value in gate_values)
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
