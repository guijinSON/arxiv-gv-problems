"""Verified problem generator for arXiv:2506.17521.

The generated problem is Structural Optimal Jacobian Accumulation in the
paper's vertex-elimination model. Section 3, Theorem 1 maps a Vertex Cover
instance to a computational DAG and gives a four-phase elimination sequence
for every cover. We generate the complement of a cover first, as a hidden
independent set, then carry that witness through the theorem's construction.

This is an honest Track B family. A public finite-field tag gives an O(n)
decoder for the planted independent set, while a solver that misses the tag
faces a regular planted Independent Set instance and, beyond it, an ordering
problem on twice as many internal DAG vertices. The checker never trusts the
tag: it verifies independence, expands the cover macro, builds the native DAG,
and replays every elimination exactly.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time
from typing import Any


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - optional for this finite graph family
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "regular graph on translated nonzero elements of GF(p)",
        "directed acyclic computational graph under vertex elimination",
        "independent-set macro for a total elimination sequence",
    ],
    "verification_operations": [
        "exact graph incidence checks",
        "exact directed-arc insertion and deletion",
        "integer in-degree times out-degree",
        "integer Markowitz-cost summation",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3, Theorem 1 (linear reduction from Vertex Cover to "
        "Structural Optimal Jacobian Accumulation)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Translate by the public field center and enumerate the two named "
        "exponent cosets; without that invariant one must recover a large "
        "independent set or search elimination orders."
    ),
    "hardness_basis": (
        "Track B: the public exponent-coset decoder is O(n), uses at most "
        "207 exact modular operations and under 0.001 s at shipping n=336, "
        "whereas statement-blind search is the paper's exponential ordering "
        "problem and the measured 256-restart graph heuristic fails."
    ),
    "max_answer_tokens": 97,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}


# n is the source-graph order and p=n+1 is prime. The planted independent set
# has size 2n/7. The hard rung stays within both G9 output/operation caps.
DIFFICULTY = {
    "demo": {"n": 28, "degree": 4},
    "easy": {"n": 112, "degree": 8},
    "medium": {"n": 196, "degree": 10},
    "hard": {"n": 336, "degree": 10},
}

SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Subtract the displayed center modulo p, then enumerate the two named "
    "exponent cosets by repeated multiplication by g^7."
)
PLACEBO_HINT = (
    "Keep the displayed labels and the four named elimination phases aligned "
    "while assembling the requested witness."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A comma-separated set of exactly 2n/7 distinct source-graph labels; "
        "order is immaterial, each label is an integer in 0..p-1 other than "
        "the omitted center, and no source edge may have both endpoints in "
        "the set. The checker complements it to a cover and deterministically "
        "expands the paper's four-phase total elimination sequence."
    ),
    "bounds": {
        "elements": "2n/7",
        "minimum_label": 0,
        "maximum_label": "p-1",
        "excluded_label": "center",
        "distinct": True,
        "order_matters": False,
        "maximum_shipping_elements": 96,
    },
}

NOTES = r"""
STEP 0. Section 1 fixes the native operation: eliminating an internal DAG
vertex deletes it and inserts every missing arc from an old in-neighbor to an
old out-neighbor; the Markowitz cost is indegree times outdegree immediately
before deletion. A witness for Structural Optimal Jacobian Accumulation is a
permutation of all internal vertices whose total cost is within the bound.

Section 3, Theorem 1 is the construction used here. It replaces every source
graph vertex v by v.1,...,v.5, with v.2 and v.3 internal, and its forward proof
turns any cover C into four phases: C.2, (V-C).3, (V-C).2, C.3. The module
asks for V-C as a compact macro, expands it, constructs the actual DAG, and
replays the eliminations. This is a paper-licensed representation, not a
convenience graph standing in for an unrelated continuous problem.

The discriminating certificate question forces Track B. Section 5,
Proposition 4 supplies an O(2^N N^4) exact algorithm for general instances,
but this generated distribution also has a much faster public decoder: after
subtracting the center in GF(p), its planted independent set is the union of
two named exponent classes modulo seven. Repeated multiplication by g^7
enumerates it in O(n) exact arithmetic. The reference algorithm reports that
success and its measured cost; it is intentionally not disguised as Track A.

Generation is inverse and performs no search for its witness. The two cosets
are chosen first. A regular graph is then sampled around them: every planted
vertex sends all stubs across the cut, cover-side cross-degrees are balanced,
and the residual cover-side degree sequence is realized and randomized by
degree-preserving switches. All public vertices have the same degree and the
labels are translated by a random center. The theorem carries the known cover
into the elimination macro.

The adversary panel tests local-motif outliers, minimum-residual-degree greedy,
256 randomized greedy restarts, a smallest-eigenvector spectral heuristic, and
several obvious label ansatzes. The successful algebraic decoder is reported
separately as Track B's reference algorithm. canonical_key uses exact graph
invariants (common-neighbor histograms, rooted local signatures, and distance
histograms); it is invariant under arbitrary vertex relabelling but is not a
complete graph-isomorphism canonizer, so collisions remain theoretically
possible.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 250_000


def _popcount(value: int) -> int:
    return bin(value).count("1")


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _prime_factors(value: int) -> list[int]:
    factors: list[int] = []
    divisor = 2
    while divisor * divisor <= value:
        if value % divisor == 0:
            factors.append(divisor)
            while value % divisor == 0:
                value //= divisor
        divisor += 1
    if value > 1:
        factors.append(value)
    return factors


def _primitive_root(prime: int) -> int:
    factors = _prime_factors(prime - 1)
    for candidate in range(2, prime):
        if all(
            pow(candidate, (prime - 1) // factor, prime) != 1
            for factor in factors
        ):
            return candidate
    raise ValueError("prime has no primitive root")


def _validate_parameters(n: int, degree: int) -> None:
    if type(n) is not int or n < 28 or n > 896 or n % 7:
        raise ValueError("n must be a multiple of 7 in [28, 896]")
    if not _is_prime(n + 1):
        raise ValueError("n+1 must be prime")
    independent_size = 2 * n // 7
    cover_size = n - independent_size
    if type(degree) is not int or not (3 <= degree < cover_size):
        raise ValueError("degree must be an integer in [3, cover_size)")
    if degree * (n - 2 * independent_size) % 2:
        raise ValueError("residual cover degree sum must be even")


def _weighted_choice(
    rng: random.Random, candidates: list[int], weights: list[int]
) -> int:
    point = rng.randrange(sum(weights))
    for candidate, weight in zip(candidates, weights):
        if point < weight:
            return candidate
        point -= weight
    raise AssertionError("weighted choice fell through")


def _randomized_havel_hakimi(
    vertices: list[int], degrees: dict[int, int], rng: random.Random
) -> set[tuple[int, int]] | None:
    """Realize a simple degree sequence and erase ordering via 2-switches."""

    remaining = dict(degrees)
    edges: set[tuple[int, int]] = set()
    while True:
        positive = [v for v in vertices if remaining[v] > 0]
        if not positive:
            break
        maximum = max(remaining[v] for v in positive)
        tied = [v for v in positive if remaining[v] == maximum]
        u = rng.choice(tied)
        need = remaining[u]
        candidates = [
            v
            for v in positive
            if v != u and tuple(sorted((u, v))) not in edges
        ]
        if len(candidates) < need:
            return None
        rng.shuffle(candidates)
        candidates.sort(key=lambda v: remaining[v], reverse=True)
        chosen = candidates[:need]
        remaining[u] = 0
        for v in chosen:
            if remaining[v] <= 0:
                return None
            remaining[v] -= 1
            edges.add(tuple(sorted((u, v))))
    if any(remaining.values()):
        return None

    edge_list = list(edges)
    for _ in range(max(100, 30 * len(edge_list))):
        i, j = rng.sample(range(len(edge_list)), 2)
        a, b = edge_list[i]
        c, d = edge_list[j]
        if rng.randrange(2):
            c, d = d, c
        if len({a, b, c, d}) < 4:
            continue
        old1, old2 = tuple(sorted((a, b))), tuple(sorted((c, d)))
        new1, new2 = tuple(sorted((a, d))), tuple(sorted((c, b)))
        if new1 == new2 or new1 in edges or new2 in edges:
            continue
        edges.remove(old1)
        edges.remove(old2)
        edges.add(new1)
        edges.add(new2)
        edge_list[i], edge_list[j] = new1, new2
    return edges


def _decode_cosets(
    prime: int,
    center: int,
    primitive_root: int,
    offsets: list[int],
) -> tuple[list[int], int]:
    """Decode the planted set without reading answer; return witness and ops."""

    operations = 0

    def counted_pow(base: int, exponent: int) -> int:
        nonlocal operations
        result = 1
        factor = base % prime
        while exponent:
            if exponent & 1:
                result = (result * factor) % prime
                operations += 1
            exponent >>= 1
            if exponent:
                factor = (factor * factor) % prime
                operations += 1
        return result

    step = counted_pow(primitive_root, 7)
    class_size = (prime - 1) // 7
    values: set[int] = set()
    for offset in offsets:
        current = counted_pow(primitive_root, offset)
        for _ in range(class_size):
            values.add((center + current) % prime)
            operations += 1
            current = (current * step) % prime
            operations += 1
    return sorted(values), operations


def _sample_regular_around_independent(
    vertices: list[int],
    independent: set[int],
    degree: int,
    rng: random.Random,
) -> list[list[int]]:
    cover = [v for v in vertices if v not in independent]
    cross_total = degree * len(independent)
    cross_floor, cross_extra = divmod(cross_total, len(cover))
    if cross_floor < 1 or cross_floor + int(bool(cross_extra)) >= degree:
        raise ValueError("parameters do not admit balanced cross degrees")

    independent_list = sorted(independent)
    for _attempt in range(20_000):
        cover_order = cover[:]
        rng.shuffle(cover_order)
        cross_degree = {v: cross_floor for v in cover}
        for v in cover_order[:cross_extra]:
            cross_degree[v] += 1
        capacity = dict(cross_degree)
        cross_pairs: list[tuple[int, int]] = []
        w_order = independent_list[:]
        rng.shuffle(w_order)
        good = True
        for w in w_order:
            chosen: set[int] = set()
            for _ in range(degree):
                candidates = [
                    v for v in cover if capacity[v] > 0 and v not in chosen
                ]
                if not candidates:
                    good = False
                    break
                v = _weighted_choice(
                    rng, candidates, [capacity[x] for x in candidates]
                )
                chosen.add(v)
                capacity[v] -= 1
                cross_pairs.append(tuple(sorted((w, v))))
            if not good:
                break
        if not good or any(capacity.values()):
            continue

        residual = {v: degree - cross_degree[v] for v in cover}
        internal = _randomized_havel_hakimi(cover, residual, rng)
        if internal is None:
            continue
        edges = set(cross_pairs) | internal
        counts = {v: 0 for v in vertices}
        for u, v in edges:
            counts[u] += 1
            counts[v] += 1
        if any(counts[v] != degree for v in vertices):
            continue
        edge_rows = [list(edge) for edge in edges]
        rng.shuffle(edge_rows)
        return edge_rows
    raise RuntimeError("could not realize the regular planted graph")


def make_instance(
    n: int,
    seed: int = 0,
    *,
    degree: int,
    **params: Any,
) -> dict:
    """Inverse-generate a certified SOJA instance; never solve the instance."""

    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_parameters(n, degree)
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    prime = n + 1
    center = rng.randrange(prime)
    primitive_root = _primitive_root(prime)
    offsets = sorted(rng.sample(range(7), 2))
    answer, decoder_operations = _decode_cosets(
        prime, center, primitive_root, offsets
    )
    vertices = [v for v in range(prime) if v != center]
    independent = set(answer)
    if len(independent) != 2 * n // 7 or center in independent:
        raise AssertionError("coset decoder produced the wrong shape")
    edges = _sample_regular_around_independent(
        vertices, independent, degree, rng
    )
    edge_count = len(edges)
    cover_size = n - len(answer)
    threshold = 6 * edge_count + 4 * n + cover_size
    return {
        "family": "Structural Optimal Jacobian Accumulation via Theorem 1",
        "n": n,
        "prime": prime,
        "center": center,
        "primitive_root": primitive_root,
        "coset_offsets": offsets,
        "field_tag_valid": True,
        "degree": degree,
        "source_edges": edges,
        "source_edge_count": edge_count,
        "independent_size": len(answer),
        "cover_size": cover_size,
        "dag_vertex_count": 5 * n,
        "dag_internal_count": 2 * n,
        "cost_threshold": threshold,
        "decoder_operations": decoder_operations,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a complete problem statement with an exact answer grammar."""

    edges = sorted(tuple(sorted(edge)) for edge in inst["source_edges"])
    edge_text = "\n".join(f"{u} {v}" for u, v in edges)
    offsets = ", ".join(map(str, inst["coset_offsets"]))
    example = ", ".join(map(str, range(inst["independent_size"])))
    statement = f"""STRUCTURAL OPTIMAL JACOBIAN ACCUMULATION — INDEPENDENT-SET MACRO

The source graph G has {inst['n']} vertices. Its vertex labels are all integers
from 0 through {inst['prime'] - 1}, except the omitted label
{inst['center']}. Each row "u v" below is one undirected edge {{u,v}}; there
are no loops or repeated edges. The graph is {inst['degree']}-regular.

The instance also carries a public finite-field tag:

    prime p = {inst['prime']}
    center b = {inst['center']}
    primitive root g modulo p = {inst['primitive_root']}
    exponent-class offsets modulo 7 = {offsets}

These numbers are public metadata for a possible compact route. They do not
relax the witness conditions below: the checker validates the graph witness
and the complete DAG elimination directly.

The directed acyclic computational graph D is defined from G as follows. For
each source label v create v.1,v.2,v.3,v.4,v.5. Vertices v.2 and v.3 are
internal; v.1,v.4,v.5 are terminals. Add these six arcs for every v:

    v.1->v.2, v.2->v.3, v.2->v.4,
    v.2->v.5, v.3->v.4, v.3->v.5.

For every source edge {{u,v}}, add four arcs:

    u.1->v.3, u.2->v.3, v.1->u.3, v.2->u.3.

Eliminating an internal vertex x deletes x and its incident arcs, then adds
every missing arc a->c for which a was an in-neighbor and c was an
out-neighbor of x immediately before deletion. Its cost is its in-degree
times its out-degree at that moment. A total sequence eliminates each of the
{2 * inst['n']} internal vertices exactly once. The required total cost is at
most {inst['cost_threshold']}.

Give exactly {inst['independent_size']} distinct source labels forming an
independent set W of G: no listed edge may have both endpoints in W. Order is
irrelevant, labels are integers in the inclusive range 0..{inst['prime'] - 1},
the omitted center {inst['center']} is forbidden, and repeats are forbidden.
The checker sets C=V(G)-W, sorts every phase by numerical source label, and
expands W to the following concrete total elimination sequence:

    phase 1: v.2 for v in C;
    phase 2: v.3 for v in W;
    phase 3: v.2 for v in W;
    phase 4: v.3 for v in C.

It then constructs D and replays all {2 * inst['n']} eliminations exactly.

SOURCE EDGES (one row: u v)
{edge_text}

Give your final answer inside <answer></answer> tags, as a comma-separated list
of exactly {inst['independent_size']} distinct integer source labels.
Example: <answer>{example}</answer>
The example shows syntax only and is not necessarily an independent set.
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the last tagged integer list, tolerating prose and fences."""

    if not isinstance(text, str):
        return None
    for raw in reversed(_ANSWER_RE.findall(text)):
        body = raw.strip()
        fence = re.fullmatch(r"```(?:json|text)?\s*(.*?)\s*```", body, re.I | re.S)
        if fence:
            body = fence.group(1).strip()
        if body.startswith("[") and body.endswith("]"):
            try:
                value = json.loads(body)
            except (TypeError, ValueError):
                continue
            if isinstance(value, list) and all(type(x) is int for x in value):
                return value
            continue
        if not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", body):
            continue
        try:
            return [int(piece.strip()) for piece in body.split(",")]
        except ValueError:
            continue
    return None


def _vertices(inst: dict) -> list[int]:
    return [v for v in range(inst["prime"]) if v != inst["center"]]


def _normalized_edges(inst: dict) -> list[tuple[int, int]]:
    return sorted(tuple(sorted(edge)) for edge in inst["source_edges"])


def _compile_sequence(inst: dict, independent: set[int]) -> list[int]:
    labels = _vertices(inst)
    position = {label: index for index, label in enumerate(labels)}
    cover = [v for v in labels if v not in independent]
    outside = sorted(independent)

    def dag_index(label: int, local: int) -> int:
        return 5 * position[label] + (local - 1)

    return (
        [dag_index(v, 2) for v in cover]
        + [dag_index(v, 3) for v in outside]
        + [dag_index(v, 2) for v in outside]
        + [dag_index(v, 3) for v in cover]
    )


def _build_dag(inst: dict) -> tuple[list[int], list[int]]:
    labels = _vertices(inst)
    position = {label: index for index, label in enumerate(labels)}
    total = 5 * inst["n"]
    incoming = [0] * total
    outgoing = [0] * total

    def index(label: int, local: int) -> int:
        return 5 * position[label] + (local - 1)

    def add(u: int, v: int) -> None:
        outgoing[u] |= 1 << v
        incoming[v] |= 1 << u

    for label in labels:
        v1, v2, v3, v4, v5 = (index(label, j) for j in range(1, 6))
        add(v1, v2)
        add(v2, v3)
        add(v2, v4)
        add(v2, v5)
        add(v3, v4)
        add(v3, v5)
    for u, v in _normalized_edges(inst):
        add(index(u, 1), index(v, 3))
        add(index(u, 2), index(v, 3))
        add(index(v, 1), index(u, 3))
        add(index(v, 2), index(u, 3))
    return incoming, outgoing


def _replay_cost(inst: dict, sequence: list[int]) -> tuple[int, str]:
    incoming, outgoing = _build_dag(inst)
    total_vertices = len(incoming)
    active = (1 << total_vertices) - 1
    total_cost = 0
    for step, vertex in enumerate(sequence):
        if vertex < 0 or vertex >= total_vertices or not ((active >> vertex) & 1):
            return total_cost, f"compiled sequence repeats a vertex at step {step}"
        predecessors = incoming[vertex] & active
        successors = outgoing[vertex] & active
        total_cost += _popcount(predecessors) * _popcount(successors)

        bits = predecessors
        while bits:
            low = bits & -bits
            pred = low.bit_length() - 1
            new_successors = successors & ~outgoing[pred]
            outgoing[pred] |= successors
            qbits = new_successors
            while qbits:
                qlow = qbits & -qbits
                succ = qlow.bit_length() - 1
                incoming[succ] |= 1 << pred
                qbits ^= qlow
            outgoing[pred] &= ~(1 << vertex)
            bits ^= low
        bits = successors
        while bits:
            low = bits & -bits
            succ = low.bit_length() - 1
            incoming[succ] &= ~(1 << vertex)
            bits ^= low
        incoming[vertex] = 0
        outgoing[vertex] = 0
        active &= ~(1 << vertex)
    return total_cost, "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Validate a candidate without reading inst['answer']."""

    if not isinstance(answer, list):
        return False, "answer must be a list of source labels"
    if not answer:
        return False, "answer is empty"
    if any(type(v) is not int for v in answer):
        return False, "every source label must be an integer"
    if len(answer) != inst["independent_size"]:
        return False, f"expected exactly {inst['independent_size']} source labels"
    if len(set(answer)) != len(answer):
        return False, "source labels must be distinct"
    allowed = set(_vertices(inst))
    if any(v not in allowed for v in answer):
        return False, (
            f"a label is outside 0..{inst['prime'] - 1} or equals omitted "
            f"center {inst['center']}"
        )
    independent = set(answer)
    for u, v in _normalized_edges(inst):
        if u in independent and v in independent:
            return False, f"source edge {u}-{v} lies inside the proposed independent set"

    sequence = _compile_sequence(inst, independent)
    if len(sequence) != inst["dag_internal_count"] or len(set(sequence)) != len(sequence):
        return False, "macro did not compile to every internal vertex exactly once"
    cost, replay_reason = _replay_cost(inst, sequence)
    if replay_reason != "ok":
        return False, replay_reason
    if cost > inst["cost_threshold"]:
        return False, (
            f"compiled elimination cost {cost} exceeds threshold "
            f"{inst['cost_threshold']}"
        )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the exact-size subset a statement-aware solver searches."""

    return sorted(rng.sample(_vertices(inst), inst["independent_size"]))


def search_space(inst: dict) -> int | None:
    return math.comb(inst["n"], inst["independent_size"])


def enumerate_all(inst: dict) -> int | None:
    """Brute-force exact count only when the declared space is safely small."""

    if search_space(inst) > _ENUMERATION_CAP:
        return None
    edges = _normalized_edges(inst)
    count = 0
    for candidate in itertools.combinations(_vertices(inst), inst["independent_size"]):
        chosen = set(candidate)
        if all(u not in chosen or v not in chosen for u, v in edges):
            count += 1
    return count


def _adjacency_bits(inst: dict) -> tuple[list[int], list[int], dict[int, int]]:
    labels = _vertices(inst)
    position = {label: index for index, label in enumerate(labels)}
    adjacency = [0] * len(labels)
    for u, v in _normalized_edges(inst):
        ui, vi = position[u], position[v]
        adjacency[ui] |= 1 << vi
        adjacency[vi] |= 1 << ui
    return adjacency, labels, position


def _graph_invariant_payload(inst: dict) -> dict:
    """Strong cheap invariants, independent of all vertex labels and edge order."""

    adjacency, _labels, _position = _adjacency_bits(inst)
    n = len(adjacency)
    edge_common: dict[int, int] = {}
    nonedge_common: dict[int, int] = {}
    rooted: list[tuple[int, int, tuple[int, ...]]] = []
    for v in range(n):
        neighbor_common: list[int] = []
        triangle_twice = 0
        bits = adjacency[v]
        while bits:
            low = bits & -bits
            w = low.bit_length() - 1
            common = _popcount(adjacency[v] & adjacency[w])
            neighbor_common.append(common)
            triangle_twice += common
            if v < w:
                edge_common[common] = edge_common.get(common, 0) + 1
            bits ^= low
        rooted.append(
            (_popcount(adjacency[v]), triangle_twice // 2, tuple(sorted(neighbor_common)))
        )
    for v in range(n):
        for w in range(v + 1, n):
            if (adjacency[v] >> w) & 1:
                continue
            common = _popcount(adjacency[v] & adjacency[w])
            nonedge_common[common] = nonedge_common.get(common, 0) + 1

    distances: dict[int, int] = {}
    for start in range(n):
        seen = 1 << start
        frontier = seen
        distance = 0
        while frontier:
            if distance:
                distances[distance] = distances.get(distance, 0) + _popcount(frontier)
            next_frontier = 0
            bits = frontier
            while bits:
                low = bits & -bits
                vertex = low.bit_length() - 1
                next_frontier |= adjacency[vertex]
                bits ^= low
            next_frontier &= ~seen
            seen |= next_frontier
            frontier = next_frontier
            distance += 1
        if _popcount(seen) != n:
            distances[-1] = distances.get(-1, 0) + n - _popcount(seen)
    return {
        "n": n,
        "m": inst["source_edge_count"],
        "target": inst["independent_size"],
        "degree_sequence": sorted(_popcount(row) for row in adjacency),
        "rooted_local_signatures": sorted(rooted),
        "edge_common_neighbor_histogram": sorted(edge_common.items()),
        "nonedge_common_neighbor_histogram": sorted(nonedge_common.items()),
        "ordered_pair_distance_histogram": sorted(distances.items()),
    }


def canonical_key(inst: dict) -> str:
    payload = _graph_invariant_payload(inst)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | None:
    n = params.get("n")
    degree = params.get("degree")
    if type(n) is not int or type(degree) is not int:
        return None
    lower = n + 84
    for candidate in range(lower + (-lower % 7), 897, 7):
        if _is_prime(candidate + 1):
            return {"n": candidate, "degree": degree}
    return None


def _independent(inst: dict, candidate: list[int]) -> bool:
    if len(candidate) != len(set(candidate)):
        return False
    chosen = set(candidate)
    return all(u not in chosen or v not in chosen for u, v in _normalized_edges(inst))


def _attack_outlier_local_motif(inst: dict) -> list[int] | None:
    """Rank by triangles/four-cycles in both directions."""

    adjacency, labels, _position = _adjacency_bits(inst)
    scored: list[tuple[tuple[int, int], int]] = []
    for v, row in enumerate(adjacency):
        triangle_twice = 0
        four_score = 0
        bits = row
        neighbors: list[int] = []
        while bits:
            low = bits & -bits
            w = low.bit_length() - 1
            neighbors.append(w)
            triangle_twice += _popcount(row & adjacency[w])
            bits ^= low
        for a, b in itertools.combinations(neighbors, 2):
            four_score += max(0, _popcount(adjacency[a] & adjacency[b]) - 1)
        scored.append(((triangle_twice // 2, four_score), labels[v]))
    target = inst["independent_size"]
    for reverse in (False, True):
        candidate = sorted(
            label for _score, label in sorted(scored, reverse=reverse)[:target]
        )
        if _independent(inst, candidate):
            return candidate
    return None


def _greedy_independent(
    inst: dict, rng: random.Random | None = None
) -> list[int]:
    adjacency, labels, _position = _adjacency_bits(inst)
    available = (1 << len(labels)) - 1
    selected: list[int] = []
    while available:
        candidates: list[tuple[float, float, int]] = []
        bits = available
        while bits:
            low = bits & -bits
            vertex = low.bit_length() - 1
            residual_degree = _popcount(adjacency[vertex] & available)
            tie = rng.random() if rng is not None else float(labels[vertex])
            candidates.append((float(residual_degree), tie, vertex))
            bits ^= low
        _degree, _tie, vertex = min(candidates)
        selected.append(labels[vertex])
        available &= ~(1 << vertex)
        available &= ~adjacency[vertex]
    return selected


def _attack_greedy(inst: dict) -> list[int] | None:
    candidate = _greedy_independent(inst)
    if len(candidate) < inst["independent_size"]:
        return None
    candidate = sorted(candidate[: inst["independent_size"]])
    return candidate if _independent(inst, candidate) else None


def _attack_random_restarts(
    inst: dict, seed: int, restarts: int = 256
) -> tuple[list[int] | None, int]:
    rng = random.Random(seed ^ 0x51A7C0DE)
    target = inst["independent_size"]
    for attempt in range(1, restarts + 1):
        candidate = _greedy_independent(inst, rng)
        if len(candidate) >= target:
            candidate = sorted(candidate[:target])
            if _independent(inst, candidate):
                return candidate, attempt
    return None, restarts


def _attack_spectral(inst: dict) -> list[int] | None:
    """Smallest-adjacency-eigenvector power iteration, standard-library only."""

    adjacency, labels, _position = _adjacency_bits(inst)
    n = len(labels)
    vector = [math.sin((i + 1) * 1.61803398875) for i in range(n)]
    mean = sum(vector) / n
    vector = [value - mean for value in vector]
    for _ in range(120):
        nxt = [0.0] * n
        for v in range(n):
            total = float(inst["degree"]) * vector[v]
            bits = adjacency[v]
            while bits:
                low = bits & -bits
                total -= vector[low.bit_length() - 1]
                bits ^= low
            nxt[v] = total
        norm = math.sqrt(sum(value * value for value in nxt)) or 1.0
        vector = [value / norm for value in nxt]

    target = inst["independent_size"]
    for reverse in (False, True):
        order = sorted(range(n), key=lambda v: vector[v], reverse=reverse)
        extreme = sorted(labels[v] for v in order[:target])
        if _independent(inst, extreme):
            return extreme
        chosen_indices = 0
        greedy: list[int] = []
        for v in order:
            if not (adjacency[v] & chosen_indices):
                greedy.append(labels[v])
                chosen_indices |= 1 << v
                if len(greedy) == target:
                    return sorted(greedy)
    return None


def _attack_obvious_label_ansatz(inst: dict) -> list[int] | None:
    """Cheap by-hand guesses using visible order, parity, and raw residues."""

    labels = _vertices(inst)
    target = inst["independent_size"]
    candidates: list[list[int]] = []
    candidates.append(sorted(labels)[:target])
    candidates.append(sorted(labels)[-target:])
    candidates.append(sorted(labels, key=lambda v: (v % 2, v))[:target])
    offsets = set(inst["coset_offsets"])
    candidates.append(
        sorted(labels, key=lambda v: (v % 7 not in offsets, v))[:target]
    )
    centered = sorted(
        labels, key=lambda v: ((v - inst["center"]) % inst["prime"])
    )
    candidates.append(sorted(centered[:target]))
    for candidate in candidates:
        if _independent(inst, candidate):
            return candidate
    return None


def _reference_decoder(inst: dict) -> tuple[list[int], int]:
    return _decode_cosets(
        inst["prime"],
        inst["center"],
        inst["primitive_root"],
        list(inst["coset_offsets"]),
    )


def _relabel_instance(inst: dict, permutation: dict[int, int]) -> dict:
    transformed = dict(inst)
    transformed["source_edges"] = [
        [permutation[u], permutation[v]] for u, v in inst["source_edges"]
    ]
    transformed["answer"] = sorted(permutation[v] for v in inst["answer"])
    transformed["field_tag_valid"] = False
    return transformed


# Patched only from isolated harden.py transcripts. Pending deliberately keeps
# G9(b), and therefore all_passed, false.
G9_AUDIT = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "pending",
}


def selftest() -> dict:
    """Run and measure G1--G9; return a JSON-native report."""

    report: dict[str, Any] = {
        "paper": "2506.17521",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    g1_failures: list[str] = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            try:
                if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                    g1_failures.append(f"{preset}/{seed}: JSON round-trip changed answer")
            except (TypeError, ValueError) as exc:
                g1_failures.append(f"{preset}/{seed}: JSON failure {exc}")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=101, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    planted_set = set(planted)
    removed = planted[0]
    replacement = next(
        v
        for v in _vertices(shipping)
        if v not in planted_set
        and any(
            v in edge
            and removed not in edge
            and (edge[0] in planted_set or edge[1] in planted_set)
            for edge in shipping["source_edges"]
        )
    )
    swapped = planted[1:] + [replacement]
    corruptions: dict[str, object] = {
        "drop_one": planted[:-1],
        "swap_one": swapped,
        "duplicate": planted[:-1] + [planted[0]],
        "empty": [],
        "out_of_range": planted[:-1] + [shipping["prime"]],
    }
    reasons: dict[str, str] = {}
    all_rejected = True
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        all_rejected &= not ok
        reasons[name] = reason
    report["G2_rejects_corruption"] = {
        "pass": all_rejected and len(set(reasons.values())) == len(reasons),
        "rejected": sum(reason != "ok" for reason in reasons.values()),
        "distinct_reasons": len(set(reasons.values())),
        "reasons": reasons,
    }

    realistic = (
        "The field classes give this set.\n```text\n<answer>\n"
        + ", ".join(map(str, planted))
        + "\n</answer>\n```\nThe cover macro then has four phases."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged witness") is None,
        "realistic_response_parsed": parsed == planted,
        "garbage_returns_none": parse_answer("no tagged witness") is None,
    }

    adjacency, _labels, position = _adjacency_bits(shipping)
    guess_rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    guess_started = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(shipping, guess_rng)
        mask = 0
        for label in candidate:
            mask |= 1 << position[label]
        valid = True
        for label in candidate:
            if adjacency[position[label]] & mask:
                valid = False
                break
        guess_hits += int(valid)
    guess_elapsed = time.perf_counter() - guess_started
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_hits / guess_total,
        "structure_aware_space": search_space(shipping),
        "candidate_prior": "uniform over all exact-2n/7 subsets of public labels",
        "elapsed_sec": round(guess_elapsed, 6),
    }

    baseline_started = time.perf_counter()
    baseline_answer, baseline_restarts = _attack_random_restarts(shipping, 101, 256)
    baseline_wall = time.perf_counter() - baseline_started
    baseline_success = (
        baseline_answer is not None and verify(shipping, baseline_answer)[0]
    )
    reference_started = time.perf_counter()
    reference_answer, reference_operations = _reference_decoder(shipping)
    reference_wall = time.perf_counter() - reference_started
    reference_success = verify(shipping, reference_answer)[0]
    report["G5_density_and_baseline"] = {
        "pass": guess_hits / guess_total < 1e-6 and not baseline_success and reference_success,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_sampled_solution_fraction": guess_hits / guess_total,
        "shipping_exact_solution_count": None,
        "baseline_name": "256 randomized minimum-residual-degree greedy restarts",
        "baseline_wall_clock_sec": round(baseline_wall, 6),
        "baseline_restarts": baseline_restarts,
        "baseline_success": baseline_success,
        "reference_wall_clock_sec": round(reference_wall, 6),
        "reference_operations": reference_operations,
        "reference_success": reference_success,
    }

    attack_names = [
        "outlier_local_motif",
        "greedy_min_residual_degree",
        "random_restart_256",
        "spectral_smallest_eigenvector",
        "by_hand_label_ansatz",
    ]
    successes = {name: 0 for name in attack_names}
    attempts = 8
    random_restart_seconds = 0.0
    random_restarts_used = 0
    reference_seconds = 0.0
    reference_operations_seen: list[int] = []
    reference_successes = 0
    for seed in range(200, 200 + attempts):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates: dict[str, list[int] | None] = {
            "outlier_local_motif": _attack_outlier_local_motif(inst),
            "greedy_min_residual_degree": _attack_greedy(inst),
            "spectral_smallest_eigenvector": _attack_spectral(inst),
            "by_hand_label_ansatz": _attack_obvious_label_ansatz(inst),
        }
        started = time.perf_counter()
        random_answer, restarts_used = _attack_random_restarts(inst, seed, 256)
        random_restart_seconds += time.perf_counter() - started
        random_restarts_used += restarts_used
        candidates["random_restart_256"] = random_answer
        for name, candidate in candidates.items():
            if candidate is not None and verify(inst, candidate)[0]:
                successes[name] += 1

        started = time.perf_counter()
        decoded, operations = _reference_decoder(inst)
        reference_seconds += time.perf_counter() - started
        reference_operations_seen.append(operations)
        if verify(inst, decoded)[0]:
            reference_successes += 1
    attacks = {
        name: {"successes": successes[name], "attempts": attempts}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": (
            all(item["successes"] == 0 for item in attacks.values())
            and reference_successes == attempts
        ),
        "attacks": attacks,
        "random_restart_mean_wall_clock_sec": round(
            random_restart_seconds / attempts, 6
        ),
        "random_restart_total_restarts": random_restarts_used,
        "reference_algorithm": {
            "name": "translated exponent-coset decoder",
            "complexity": "O(n) exact modular arithmetic",
            "mean_wall_clock_sec": round(reference_seconds / attempts, 6),
            "operations": max(reference_operations_seen),
            "solves": f"{reference_successes}/{attempts}, as expected",
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=303, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * shipping["n"],
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_candidate_space": search_space(shipping),
        "doubled_candidate_space": search_space(doubled),
        "doubled_verification": doubled_reason,
    }

    invariance_checks = 0
    preserving_checks = 0
    g8_failures: list[str] = []
    unrelated_keys: list[str] = []
    for seed in range(20):
        inst = make_instance(seed=1000 + seed, **DIFFICULTY["easy"])
        key = canonical_key(inst)
        unrelated_keys.append(key)
        rng = random.Random(0xCA11 + seed)
        old_labels = _vertices(inst)
        new_labels = old_labels[:]
        rng.shuffle(new_labels)
        permutation = dict(zip(old_labels, new_labels))
        relabelled = _relabel_instance(inst, permutation)
        reordered = dict(inst)
        reordered["source_edges"] = [
            edge[::-1] for edge in reversed(inst["source_edges"])
        ]
        composed = _relabel_instance(reordered, permutation)
        for index, variant in enumerate((relabelled, reordered, composed)):
            invariance_checks += 1
            if canonical_key(variant) != key:
                g8_failures.append(f"seed {seed} variant {index}: key changed")
            preserving_checks += 1
            ok, reason = verify(variant, variant["answer"])
            if not ok:
                g8_failures.append(f"seed {seed} variant {index}: {reason}")
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_count == 20,
        "invariance_checks": invariance_checks,
        "preserving_witness_checks": preserving_checks,
        "distinct_unrelated_keys": distinct_count,
        "unrelated_instances": 20,
        "transformations": [
            "arbitrary source-vertex relabelling with carried witness",
            "edge-row reorder plus endpoint reversal",
            "their composition",
        ],
        "failures": g8_failures,
    }

    longest = sorted(_vertices(shipping), reverse=True)[: shipping["independent_size"]]
    serialized = json.dumps(sorted(longest), separators=(",", ":"))
    answer_chars = len(serialized)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = shipping["independent_size"]
    intended_operations = shipping["decoder_operations"]
    arms = G9_AUDIT["arms"]
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
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": G9_AUDIT["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_AUDIT["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
