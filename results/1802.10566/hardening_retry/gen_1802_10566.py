"""Verified problem generator for arXiv:1802.10566.

The family uses the paper's Section 4.2 reduction for the H_{2,k} demand
graphs.  A cyclic compatibility instance supplies a multicolored clique by
construction.  The reduction turns that clique into an exact-cost
Shallow-Light Steiner Network subgraph, represented here by the same compact
choice blueprint used in the proof.  The generated instance is never solved
to obtain its planted certificate.
"""

from __future__ import annotations

import hashlib
import heapq
import itertools
import json
import math
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - the module is stdlib-only either way
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "compactly encoded weighted Shallow-Light Steiner Network graph",
        "two-root complete-bipartite demand graph H_{2,k}",
        "subgraph blueprint selecting one paper vertex gadget per color",
    ],
    "verification_operations": [
        "modular compatibility comparison",
        "exact integer edge-cost summation",
        "exact Dijkstra shortest paths on the expanded certificate subgraph",
        "distance-bound comparison for every demand pair",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 4.2.3, Case H_{2,k}, Lemmas 4.10-4.11 and Theorem 4.4 "
        "(Multicolored Clique to unit-length/unit-cost SLSN)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The allowed pair offsets contain one additive gauge that is globally "
        "consistent around every triangle; without recognizing that gauge, the "
        "solver faces the full compatibility search."
    ),
    "hardness_basis": (
        "Track B: sparse path consistency on the explicit difference relations "
        "is polynomial, O(k^3*d^2); the shipping selftest records its measured "
        "support tests and wall time, while the additive-gauge route uses at "
        "most 282 exact modular membership operations."
    ),
    "max_answer_tokens": 120,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 4, "modulus": 11, "offsets_per_pair": 2},
    "easy": {"n": 24, "modulus": 97, "offsets_per_pair": 2},
    "medium": {"n": 40, "modulus": 193, "offsets_per_pair": 2},
    "hard": {"n": 58, "modulus": 389, "offsets_per_pair": 2},
}
SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "An ordered tuple of exactly k global candidate-vertex IDs.  Position i "
        "must lie in [i*m,(i+1)*m), so it selects one of the m vertex gadgets in "
        "color group i; repetitions of a global ID are forbidden.  Global "
        "translation is normalized by requiring the group-0 ID to be 0."
    ),
    "bounds": {
        "tuple_length": "k",
        "choices_per_position": "m",
        "global_id_min": 0,
        "global_id_max": "k*m-1",
    },
}

STRUCTURAL_HINT = (
    "The distinguished offsets form one additive gauge that is consistent around "
    "every triangle of color groups."
)
PLACEBO_HINT = (
    "Careful bookkeeping of group order and zero-based identifiers helps avoid "
    "small transcription errors."
)

# Filled from the three isolated harden.py runs.  The arms are diagnostic; only
# the measured size/effort caps determine G9.pass.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "pending",
}

NOTES = """\
Definition 1.1 fixes the native task: choose a minimum-cost subgraph in which
every demand pair has a path of length at most L.  Theorem 2.2 makes a constant
number of demands polynomial-time solvable in n^{O(p^4)}, and Theorem 2.3 gives
an FPT algorithm for star demands; this family avoids both regimes by using the
growing two-root complete-bipartite demand graphs H_{2,k}.  Theorem 2.4 is the
paper's W[1]-hardness dichotomy, while Section 4.2.3 and Lemmas 4.10-4.11
supply the H_{2,k} construction used here.

The certificate is produced before the instance: random group gauges are
sampled, their consistent pair offsets are inserted, and identically
distributed random offsets are added as decoys.  Rejection sampling discards a
decoy draw if it creates a second globally triangle-consistent gauge, but it
never searches for the planted answer.  The paper's clique-to-SLSN proof then
gives the exact subgraph blueprint.  Degree outliers are impossible because
every candidate has exactly d neighbours in every other group.  The equal-label,
smallest-offset, sequential-greedy, diagonal, and random-restart attacks are
checked on eight shipping seeds.  Sparse path consistency is a successful
polynomial reference algorithm and is reported separately because this is
Track B.  A discarded ladder with 12 groups and four offsets was solved at
every modulus through 521; the final ladder grows demand groups instead.

The displayed weighted edges are the paper's degree-two-path compression: an
edge of length/cost w denotes the w-hop unit-length/unit-cost path used in the
proof.  Expanding or contracting those internally unique paths preserves both
the cost and all terminal distances.
"""


def _is_prime(value: int) -> bool:
    """Deterministic Miller-Rabin for the 64-bit escalation range."""
    if value < 2:
        return False
    small_primes = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small_primes:
        if value % prime == 0:
            return value == prime
    exponent = value - 1
    power_of_two = 0
    while exponent % 2 == 0:
        power_of_two += 1
        exponent //= 2
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        witness = pow(base, exponent, value)
        if witness in (1, value - 1):
            continue
        for _ in range(power_of_two - 1):
            witness = witness * witness % value
            if witness == value - 1:
                break
        else:
            return False
    return True


def _next_prime(value: int) -> int:
    candidate = max(2, int(value))
    if candidate > 2 and candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 1 if candidate == 2 else 2
    return candidate


def _relation_map(inst: dict) -> dict[tuple[int, int], tuple[int, ...]]:
    return {
        (int(row[0]), int(row[1])): tuple(int(x) for x in row[2])
        for row in inst["relations"]
    }


def _offsets(relations, i: int, j: int, modulus: int) -> tuple[int, ...]:
    """Allowed values of x_j-x_i, for either orientation."""
    if i < j:
        return tuple(relations[i, j])
    return tuple((-x) % modulus for x in relations[j, i])


def _locals_from_answer(inst: dict, answer: list[int]) -> list[int]:
    modulus = inst["modulus"]
    return [answer[i] - i * modulus for i in range(inst["k"])]


def _compatible_locals(inst: dict, values: list[int]) -> bool:
    k = inst["k"]
    modulus = inst["modulus"]
    if len(values) != k:
        return False
    relations = _relation_map(inst)
    return all(
        (values[j] - values[i]) % modulus in relations[i, j]
        for i in range(k) for j in range(i + 1, k)
    )


def _compact_survivors(relations, k: int, modulus: int):
    """Triangle-supported offsets, exploiting the cyclic encoding."""
    survivors = {}
    for i in range(k):
        for j in range(i + 1, k):
            keep = []
            for delta in relations[i, j]:
                supported_everywhere = True
                for h in range(k):
                    if h == i or h == j:
                        continue
                    right = set(_offsets(relations, h, j, modulus))
                    if not any(
                        (delta - left) % modulus in right
                        for left in _offsets(relations, i, h, modulus)
                    ):
                        supported_everywhere = False
                        break
                if supported_everywhere:
                    keep.append(delta)
            survivors[i, j] = keep
    return survivors


def _anchor_decode_from_relations(relations, k: int, modulus: int):
    """The intended bounded route; return (local solutions, modular tests)."""
    solutions = []
    operations = 0
    for first in relations[0, 1]:
        values = [0, first]
        viable = True
        for i in range(2, k):
            choices = []
            allowed_from_one = set(relations[1, i])
            for value in relations[0, i]:
                operations += 1
                if (value - first) % modulus in allowed_from_one:
                    choices.append(value)
            if len(choices) != 1:
                viable = False
                break
            values.append(choices[0])
        if viable:
            if all(
                (values[j] - values[i]) % modulus in relations[i, j]
                for i in range(k) for j in range(i + 1, k)
            ):
                solutions.append(values)
    return solutions, operations


def _simple_local_attacks(k: int, modulus: int, relations):
    equal = [0] * k
    diagonal = [i % modulus for i in range(k)]
    anchor_first = [0] + [min(relations[0, i]) for i in range(1, k)]
    greedy = [0]
    for i in range(1, k):
        choice = next((
            value for value in range(modulus)
            if all(
                (value - greedy[j]) % modulus in relations[j, i]
                for j in range(i)
            )
        ), None)
        if choice is None:
            greedy = []
            break
        greedy.append(choice)
    return {
        "outlier_uniform_degree_tiebreak": equal,
        "greedy_smallest_compatible": greedy,
        "in_context_first_anchor_offset": anchor_first,
        "obvious_diagonal_ansatz": diagonal,
    }


def _locals_compatible_raw(values, k: int, modulus: int, relations) -> bool:
    return len(values) == k and all(
        (values[j] - values[i]) % modulus in relations[i, j]
        for i in range(k) for j in range(i + 1, k)
    )


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a clique, then apply the paper's H_{2,k} reduction."""
    k = int(n)
    modulus = int(params.get("modulus", _next_prime(8 * k + 1)))
    width = int(params.get("offsets_per_pair", 4))
    if k < 3 or k > 128:
        raise ValueError("n (the number of color groups) must be in 3..128")
    if not _is_prime(modulus) or modulus < 2 * width + 1:
        raise ValueError("modulus must be prime and at least 2*d+1")
    if width < 2 or width > 8:
        raise ValueError("offsets_per_pair must be in 2..8")

    rng = random.Random(seed)
    for generation_attempt in range(1, 5001):
        gauges = [rng.randrange(modulus) for _ in range(k)]
        relations = {}
        for i in range(k):
            for j in range(i + 1, k):
                planted = (gauges[j] - gauges[i]) % modulus
                values = {planted}
                while len(values) < width:
                    values.add(rng.randrange(modulus))
                displayed = list(values)
                rng.shuffle(displayed)
                relations[i, j] = tuple(displayed)

        normalized = [(value - gauges[0]) % modulus for value in gauges]
        decoded, _ = _anchor_decode_from_relations(
            relations, k, modulus
        )
        if decoded != [normalized]:
            continue

        survivors = _compact_survivors(relations, k, modulus)
        if any(
            survivors[i, j] != [(gauges[j] - gauges[i]) % modulus]
            for i in range(k) for j in range(i + 1, k)
        ):
            continue

        attacks = _simple_local_attacks(k, modulus, relations)
        if any(
            _locals_compatible_raw(candidate, k, modulus, relations)
            for candidate in attacks.values()
        ):
            continue
        break
    else:  # pragma: no cover - parameters above make this astronomically unlikely
        raise RuntimeError("could not draw decoys satisfying the family invariants")

    displayed_relations = [
        [i, j, list(relations[i, j])]
        for i in range(k) for j in range(i + 1, k)
    ]
    rng.shuffle(displayed_relations)
    answer = [i * modulus + normalized[i] for i in range(k)]
    return {
        "paper": "arXiv:1802.10566",
        "construction": "Section 4.2 H_{2,k} weighted path compression",
        "k": k,
        "modulus": modulus,
        "offsets_per_pair": width,
        "relations": displayed_relations,
        "distance_bound": 7,
        "cost_bound": 7 * k * k - 5 * k,
        "demand_count": 2 * k * (k - 1),
        "generation_attempts": generation_attempt,
        "answer": answer,
    }


def _vertex_name(vertex) -> str:
    return ":".join(str(x) for x in vertex)


def _edge_key(left, right):
    return tuple(sorted((left, right), key=_vertex_name))


def _blueprint_edges(inst: dict, values: list[int]):
    """Expand representatives to the weighted proof subgraph."""
    k = inst["k"]
    relations = _relation_map(inst)
    edges = {}

    def add(left, right, weight):
        key = _edge_key(left, right)
        old = edges.get(key)
        if old is not None and old != weight:
            raise ValueError("inconsistent duplicate edge weight")
        edges[key] = weight

    r1 = ("R1",)
    r2 = ("R2",)
    for i in range(k):
        for j in range(i + 1, k):
            a, b = values[i], values[j]
            if (b - a) % inst["modulus"] not in relations[i, j]:
                return None
            zij = ("Z", i, j)
            ze = ("ZE", i, a, j, b)
            xi = ("X", i, a, j)
            xj = ("X", j, b, i)
            add(r1, zij, 1)
            add(zij, ze, 1)
            add(ze, xi, 1)
            add(ze, xj, 1)

    for i in range(k):
        a = values[i]
        yi = ("Y", i)
        yv = ("YV", i, a)
        add(r2, yi, 1)
        add(yi, yv, 1)
        for j in range(k):
            if i == j:
                continue
            xij = ("X", i, a, j)
            lij = ("L", i, j)
            add(yv, xij, 1)
            add(xij, lij, 4)
    return edges


def _shortest_distance(adjacency, source, target):
    queue = [(0, _vertex_name(source), source)]
    distances = {source: 0}
    while queue:
        distance, _, vertex = heapq.heappop(queue)
        if distance != distances[vertex]:
            continue
        if vertex == target:
            return distance
        for neighbour, weight in adjacency.get(vertex, ()):
            new_distance = distance + weight
            if new_distance < distances.get(neighbour, 10**30):
                distances[neighbour] = new_distance
                heapq.heappush(
                    queue, (new_distance, _vertex_name(neighbour), neighbour)
                )
    return None


def verify(inst, answer) -> tuple[bool, str]:
    """Verify a compact blueprint without consulting inst['answer']."""
    if not isinstance(answer, list):
        return False, "certificate must be a list of vertex ids"
    if not answer:
        return False, "certificate is empty"
    k = inst.get("k")
    modulus = inst.get("modulus")
    if len(answer) != k:
        return False, "wrong representative count"
    if any(isinstance(value, bool) or not isinstance(value, int) for value in answer):
        return False, "representatives must be integers"
    if any(value < 0 or value >= k * modulus for value in answer):
        return False, "representative out of range"
    if len(set(answer)) != k:
        return False, "duplicate global representative"
    if any(value // modulus != i for i, value in enumerate(answer)):
        return False, "representatives are not in group order"
    if answer[0] != 0:
        return False, "group-0 representative must be normalized to id 0"

    values = _locals_from_answer(inst, answer)
    edges = _blueprint_edges(inst, values)
    if edges is None:
        return False, "chosen candidates are not pairwise compatible"

    cost = sum(edges.values())
    if cost != inst.get("cost_bound"):
        return False, "expanded blueprint has the wrong exact cost"

    adjacency = {}
    for (left, right), weight in edges.items():
        adjacency.setdefault(left, []).append((right, weight))
        adjacency.setdefault(right, []).append((left, weight))
    bound = inst.get("distance_bound")
    distances = {}
    for root in (("R1",), ("R2",)):
        queue = [(0, _vertex_name(root), root)]
        root_distances = {root: 0}
        while queue:
            distance, _, vertex = heapq.heappop(queue)
            if distance != root_distances[vertex]:
                continue
            for neighbour, weight in adjacency.get(vertex, ()):
                new_distance = distance + weight
                if new_distance < root_distances.get(neighbour, 10**30):
                    root_distances[neighbour] = new_distance
                    heapq.heappush(
                        queue,
                        (new_distance, _vertex_name(neighbour), neighbour),
                    )
        distances[root] = root_distances
    for i in range(k):
        for j in range(k):
            if i == j:
                continue
            terminal = ("L", i, j)
            for root in (("R1",), ("R2",)):
                distance = distances[root].get(terminal)
                if distance is None:
                    return False, f"a {root[0]} demand is disconnected"
                if distance > bound:
                    return False, f"a {root[0]} demand exceeds the distance bound"
    return True, "ok"


def render(inst) -> str:
    """Render the complete compact SLSN instance and answer contract."""
    k = inst["k"]
    modulus = inst["modulus"]
    rows = "\n".join(
        f"  D[{i},{j}] = {{{', '.join(map(str, values))}}}"
        for i, j, values in inst["relations"]
    )
    statement = f"""Shallow-Light Steiner Network subgraph blueprint

All indices and residues below are zero-based.  Arithmetic in the D table is
modulo m={modulus}.  There are k={k} color groups.  Group i has candidate
vertices V(i,a), one for every residue 0 <= a < m.  Its global vertex ID is
i*m+a.  For i<j, V(i,a) and V(j,b) are compatible exactly when
(b-a) mod m belongs to D[i,j].  The complete table is:

{rows}

This table compactly defines the following UNDIRECTED weighted graph from
Section 4.2 of the paper.  Every displayed edge has both length and cost equal
to its weight; an edge of weight w is shorthand for an internally unique
w-hop unit-length/unit-cost path.

Vertices:
  roots R1,R2;
  Z(i,j) for i<j;
  ZE(i,a,j,b) for every compatible i<j pair;
  Y(i) and YV(i,a);
  X(i,a,j) and terminal L(i,j) for every ordered i!=j.

Edges (and no others):
  R1--Z(i,j) [1];
  Z(i,j)--ZE(i,a,j,b) [1] for compatible pairs;
  ZE(i,a,j,b)--X(i,a,j) [1] and --X(j,b,i) [1];
  R2--Y(i) [1], Y(i)--YV(i,a) [1];
  YV(i,a)--X(i,a,j) [1] for i!=j;
  X(i,a,j)--L(i,j) [4].

There are {inst['demand_count']} demands: for every ordered pair i!=j, both
{{R1,L(i,j)}} and {{R2,L(i,j)}} must be connected in the chosen subgraph by a
path of length at most {inst['distance_bound']}.  The subgraph's total edge
cost must be exactly {inst['cost_bound']}.

Your certificate is a compact subgraph blueprint.  Choose exactly one V(i,a_i)
from every group, in increasing group order.  Because adding one residue to all
a_i changes no compatibility, normalize this symmetry by choosing V(0,0), whose
global ID is 0.  The checker expands the canonical
paper subgraph: for each i<j it uses ZE(i,a_i,j,a_j) and its four incident proof
edges, and for each ordered i!=j it uses the R2/Y/YV chain and the edge to
L(i,j).  Thus a certificate is valid only if every chosen pair is compatible,
the expanded union has exact cost {inst['cost_bound']}, and all demands meet the
closed (inclusive) length bound.  Different valid blueprints are accepted.

Give your final answer inside <answer></answer> tags, as {k} comma-separated
global vertex IDs in increasing group order, with no brackets.
Example format: <answer>{', '.join(str(i * modulus) for i in range(k))}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse the delimited comma-separated tuple; never raise on garbage."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json|text)?\s*|\s*```$", "", body, flags=re.I | re.S)
    try:
        if body.startswith("["):
            value = json.loads(body)
            if (
                isinstance(value, list)
                and all(isinstance(x, int) and not isinstance(x, bool) for x in value)
            ):
                return value
            return None
        if not re.fullmatch(r"-?\d+(?:\s*,\s*-?\d+)*", body):
            return None
        return [int(part.strip()) for part in body.split(",")]
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


def random_candidate(inst, rng) -> object:
    """Sample after enforcing the explicit global-translation normalization."""
    modulus = inst["modulus"]
    return [0] + [
        i * modulus + rng.randrange(modulus) for i in range(1, inst["k"])
    ]


def search_space(inst) -> int | None:
    return inst["modulus"] ** (inst["k"] - 1)


def enumerate_all(inst) -> int | None:
    """Brute-force the bounded blueprint language only when it is small."""
    if search_space(inst) > 250_000:
        return None
    count = 0
    k, modulus = inst["k"], inst["modulus"]
    for tail in itertools.product(range(modulus), repeat=k - 1):
        count += int(_compatible_locals(inst, [0, *tail]))
    return count


def _cycle_signature(inst: dict):
    """A cheap affine/class-relabel invariant of the compatibility object."""
    k, modulus = inst["k"], inst["modulus"]
    relations = _relation_map(inst)
    triangles = []
    for i in range(k):
        for j in range(i + 1, k):
            for h in range(j + 1, k):
                histogram = {}
                for left in relations[i, j]:
                    for right in relations[j, h]:
                        for direct in relations[i, h]:
                            residue = (left + right - direct) % modulus
                            histogram[residue] = histogram.get(residue, 0) + 1
                nonzero = [
                    count for residue, count in histogram.items() if residue != 0
                ]
                triangles.append((
                    histogram.get(0, 0),
                    modulus - 1 - len(nonzero),
                    tuple(sorted(nonzero)),
                ))
    triangles.sort()
    return [k, modulus, inst["offsets_per_pair"], triangles]


def canonical_key(inst) -> str:
    payload = json.dumps(_cycle_signature(inst), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _transformed(inst: dict, rng: random.Random, *, compose: bool = True):
    """Apply class permutation and cyclic affine candidate relabellings."""
    k, modulus = inst["k"], inst["modulus"]
    old_relations = _relation_map(inst)
    permutation = list(range(k))
    if compose:
        rng.shuffle(permutation)
    translations = [rng.randrange(modulus) for _ in range(k)]
    multiplier = rng.randrange(1, modulus)
    new_relations = []
    for i in range(k):
        for j in range(i + 1, k):
            old_offsets = _offsets(
                old_relations, permutation[i], permutation[j], modulus
            )
            values = [
                (multiplier * value + translations[j] - translations[i]) % modulus
                for value in old_offsets
            ]
            rng.shuffle(values)
            new_relations.append([i, j, values])
    rng.shuffle(new_relations)

    old_values = _locals_from_answer(inst, inst["answer"])
    new_values = [
        (multiplier * old_values[permutation[i]] + translations[i]) % modulus
        for i in range(k)
    ]
    origin = new_values[0]
    new_values = [(value - origin) % modulus for value in new_values]
    out = dict(inst)
    out["relations"] = new_relations
    out["answer"] = [i * modulus + new_values[i] for i in range(k)]
    return out


def escalate(params) -> dict | str | None:
    """Grow demand groups at fixed certificate encoding until G9's route cap."""
    harder = dict(params)
    width = int(harder.get("offsets_per_pair", 2))
    next_k = int(harder.get("n", 58)) + 2
    if width * width * (next_k - 2) + next_k > 300:
        return "cap_bound"
    harder["n"] = next_k
    harder["modulus"] = _next_prime(int(harder.get("modulus", 389)) + 100)
    harder["offsets_per_pair"] = width
    return harder


def _reference_algorithm(inst: dict):
    """Mechanical path consistency over every compact relation and triangle."""
    start = time.perf_counter()
    k, modulus = inst["k"], inst["modulus"]
    relations = _relation_map(inst)
    retained = {}
    operations = 0
    for i in range(k):
        for j in range(i + 1, k):
            pair_survivors = []
            for delta in relations[i, j]:
                supported_everywhere = True
                for h in range(k):
                    if h == i or h == j:
                        continue
                    right_offsets = set(_offsets(relations, h, j, modulus))
                    support = False
                    for left_offset in _offsets(relations, i, h, modulus):
                        operations += 1
                        if (delta - left_offset) % modulus in right_offsets:
                            support = True
                            break
                    if not support:
                        supported_everywhere = False
                        break
                if supported_everywhere:
                    pair_survivors.append(delta)
            retained[i, j] = pair_survivors

    values = [0]
    for j in range(1, k):
        choices = retained[0, j]
        if len(choices) != 1:
            return None, time.perf_counter() - start, operations
        values.append(choices[0])
    answer = [i * modulus + values[i] for i in range(k)]
    return answer, time.perf_counter() - start, operations


def _globalize(inst: dict, values: list[int]) -> list[int]:
    return [i * inst["modulus"] + value for i, value in enumerate(values)]


def _attack_candidates(inst: dict, rng: random.Random):
    relations = _relation_map(inst)
    local = _simple_local_attacks(
        inst["k"], inst["modulus"], relations
    )
    attacks = {
        name: [_globalize(inst, values)] if len(values) == inst["k"] else [[]]
        for name, values in local.items()
    }
    attacks["random_restart_256"] = [
        random_candidate(inst, rng) for _ in range(256)
    ]
    return attacks


def _answer_token_measure(answer) -> int:
    blob = json.dumps(answer, separators=(",", ":"))
    return len(re.findall(r"-?\d+|[\[\],]", blob))


def selftest() -> dict:
    report = {
        "paper": "1802.10566",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    verified = 0
    failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            verified += int(ok)
            if not ok:
                failures.append(f"{preset}/{seed}: {reason}")
    report["G1_planted_verifies"] = {
        "pass": verified == 12,
        "verified": verified,
        "attempts": 12,
        "failures": failures,
    }

    ship = make_instance(seed=3, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = ship["answer"]
    swapped = planted[:]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    corruptions = {
        "drop": planted[:-1],
        "swap": swapped,
        "duplicate": [planted[0], planted[0]] + planted[2:],
        "empty": [],
        "out_of_range": [-1] + planted[1:],
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(ship, candidate)
        rejected[name] = {"rejected": not ok, "reason": reason}
    reasons = {row["reason"] for row in rejected.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in rejected.values()) and len(reasons) == 5,
        "cases": rejected,
        "distinct_reasons": len(reasons),
    }

    response = (
        "I used the compatibility invariant.\n```text\n<answer>"
        + ", ".join(map(str, planted))
        + "</answer>\n```\n"
    )
    parsed = parse_answer(response)
    json_native = json.loads(json.dumps(planted)) == planted
    report["G3_round_trip"] = {
        "pass": parsed == planted and json_native,
        "parsed_matches": parsed == planted,
        "json_native": json_native,
    }

    density_inst = make_instance(seed=11, **DIFFICULTY[SHIPPING_DIFFICULTY])
    density_rng = random.Random(0x180210566)
    density_relations = _relation_map(density_inst)
    samples = 200_000
    hits = 0
    density_start = time.perf_counter()
    for _ in range(samples):
        candidate = random_candidate(density_inst, density_rng)
        local_values = _locals_from_answer(density_inst, candidate)
        hits += int(_locals_compatible_raw(
            local_values,
            density_inst["k"],
            density_inst["modulus"],
            density_relations,
        ))
    density_wall = time.perf_counter() - density_start
    probability = hits / samples
    report["G4_guess_resistance"] = {
        "pass": samples >= 200_000 and probability < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": probability,
        "structure_aware": True,
        "language_size": search_space(density_inst),
        "sampling_wall_sec": round(density_wall, 6),
    }

    attack_successes = {}
    reference_successes = 0
    reference_times = []
    reference_operations = []
    for seed in range(8):
        inst = make_instance(seed=100 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, candidates in _attack_candidates(
            inst, random.Random(9000 + seed)
        ).items():
            solved = any(verify(inst, candidate)[0] for candidate in candidates)
            attack_successes[name] = attack_successes.get(name, 0) + int(solved)
        reference_answer, wall, operations = _reference_algorithm(inst)
        reference_ok = (
            reference_answer is not None and verify(inst, reference_answer)[0]
        )
        reference_successes += int(reference_ok)
        reference_times.append(wall)
        reference_operations.append(operations)

    attack_report = {
        name: {"successes": successes, "attempts": 8}
        for name, successes in attack_successes.items()
    }
    all_attacks_failed = len(attack_report) >= 4 and all(
        row["successes"] == 0 for row in attack_report.values()
    )
    reference_report = {
        "name": "path consistency on all compact difference relations",
        "complexity": "O(k^3*d^2) modular candidate-support tests",
        "wall_clock_sec_mean": round(sum(reference_times) / 8, 6),
        "wall_clock_sec_max": round(max(reference_times), 6),
        "operations_mean": round(sum(reference_operations) / 8),
        "operations_min": min(reference_operations),
        "operations_max": max(reference_operations),
        "solves": f"{reference_successes}/8, as expected",
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8,
        "attacks": attack_report,
        "reference_algorithm": reference_report,
    }

    report["G5_density_and_baseline"] = {
        "pass": probability < 1e-6 and reference_successes == 8,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_observed_solution_fraction": probability,
        "construction_proved_exact_solution_count": density_inst["modulus"],
        "shipping_exact_language_size": search_space(density_inst),
        "reference_wall_clock_sec_mean": reference_report["wall_clock_sec_mean"],
        "reference_candidate_support_tests_mean": reference_report["operations_mean"],
        "demo_exact_solution_count_seed0": enumerate_all(
            make_instance(seed=0, **DIFFICULTY["demo"])
        ),
    }

    doubled_params = {
        "n": 2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        "modulus": _next_prime(
            2 * DIFFICULTY[SHIPPING_DIFFICULTY]["modulus"]
        ),
        "offsets_per_pair": DIFFICULTY[SHIPPING_DIFFICULTY]["offsets_per_pair"],
    }
    doubled = make_instance(seed=23, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (
            doubled_ok
            and search_space(doubled) > search_space(ship)
            and doubled["demand_count"] > ship["demand_count"]
        ),
        "shipping_n": ship["k"],
        "doubled_n": doubled["k"],
        "shipping_search_space_bits": search_space(ship).bit_length(),
        "doubled_search_space_bits": search_space(doubled).bit_length(),
        "shipping_demands": ship["demand_count"],
        "doubled_demands": doubled["demand_count"],
        "doubled_verify_reason": doubled_reason,
    }

    invariance_passed = 0
    carried_passed = 0
    failures = []
    for seed in range(20):
        inst = make_instance(seed=700 + seed, **DIFFICULTY["easy"])
        key = canonical_key(inst)
        variants = [
            _transformed(inst, random.Random(1000 + 10 * seed + offset))
            for offset in range(5)
        ]
        for variant in variants:
            same = canonical_key(variant) == key
            valid = verify(variant, variant["answer"])[0]
            invariance_passed += int(same)
            carried_passed += int(valid)
            if not same or not valid:
                failures.append({"seed": seed, "same_key": same, "valid": valid})
    unrelated_keys = {
        canonical_key(make_instance(seed=2000 + seed, **DIFFICULTY["easy"]))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": (
            invariance_passed == 100
            and carried_passed == 100
            and len(unrelated_keys) == 20
        ),
        "invariance_passed": invariance_passed,
        "invariance_attempts": 100,
        "carried_answer_verifies": carried_passed,
        "carried_answer_attempts": 100,
        "distinct_unrelated_keys": len(unrelated_keys),
        "distinctness_attempts": 20,
        "failures": failures,
    }

    answer_blob = json.dumps(planted, separators=(",", ":"))
    answer_tokens = _answer_token_measure(planted)
    answer_elements = len(planted)
    intended_operations = (
        ship["offsets_per_pair"] ** 2 * (ship["k"] - 2) + ship["k"]
    )
    arms = json.loads(json.dumps(G9_RESULTS["arms"]))
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else 0.0
    )
    within_caps = (
        len(answer_blob) <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": len(answer_blob),
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [
        value for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    ]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
