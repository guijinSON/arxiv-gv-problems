"""Verified Dota Underlords team generators for arXiv:2007.05020.

The paper's Theorem 1 identifies the equal-power, size-two-alliance case with
fixed-cardinality densest subgraph.  Here every nonconflicting hero pair is
one such alliance.  A maximum-power team is therefore an exact-size
independent set in the sparse conflict graph printed in the instance.

Generation is inverse: two public multiplicative cosets in GF(p) are chosen
first, then a regular conflict graph is sampled around their union.  The
public tag gives a short exact decoder, so this is explicitly Track B rather
than an average-case hardness claim about a planted distribution.
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
except ImportError:  # pragma: no cover - optional for this finite family
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "heroes with equal integer base power",
        "two-hero alliances specified by the complement of a conflict graph",
        "bounded-cardinality team",
    ],
    "verification_operations": [
        "integer label and cardinality checks",
        "exact conflict-edge incidence checks",
        "integer team-power recomputation",
        "strict integer threshold comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Translate hero labels by the public field center and enumerate the two "
        "named exponent cosets; without that invariant one must find a large "
        "independent set in a regular conflict graph."
    ),
    "hardness_basis": (
        "Track B: translated exponent-coset decoding is O(n), takes at most "
        "207 exact modular operations and under 0.001 s at shipping n=336; "
        "the measured 256-restart graph heuristic instead exhausts all restarts."
    ),
    "max_answer_tokens": 113,
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


# p=n+1 is prime, and the certified team has size 2n/7.  The hard rung
# remains below both G9's 256-element and 300-operation caps.
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
    "Keep the hero labels and the listed conflict pairs aligned while checking "
    "the required team size and power."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A comma-separated set of exactly 2n/7 distinct hero labels; order is "
        "immaterial, every label is in 0..p-1 except the omitted center, and no "
        "listed conflict pair may lie wholly inside the set."
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
STEP 0. Section 3.2 and system (2) fix the native object: choose at most m
heroes; each chosen hero contributes its base power, and an alliance threshold
can add a bonus to its chosen members. Theorem 2 says a proposed team is
checked in O(ntq) time by counting active alliances and evaluating that exact
objective.

Section 4.1, Theorem 1 fixes the family used here. With equal hero power,
alliances of size two, activation only when both members are present, and
equal member bonuses, team power is an affine function of the number of
alliance edges induced by the team. This module uses that case directly. Every
unordered hero pair except a displayed sparse conflict pair is a two-hero
alliance; the complement notation only compresses the alliance list. A k-hero
team has the maximum possible power k^2 exactly when it contains no conflict.

The easy regimes were decisive. Section 3.1 explicitly solves the no-alliance
case by sorting hero powers. Section 4.4, Theorems 4--6, supplies a polynomial
reduction to maximum edge-weighted clique when maximum alliance size q is
bounded, and Section 5 solves the real data with integer programming. Worst-
case NP-completeness in Theorem 3 says nothing about this inverse-generated
distribution. The public finite-field decoder therefore forces TRACK B: its
O(n) modular algorithm produces the certificate in at most 207 measured exact
operations at the shipping preset, and is reported as the successful reference
algorithm rather than hidden in a Track A claim.

Generation never solves the output instance. It chooses a random translation
and two of seven multiplicative exponent classes first. Their union is the
answer. It then realizes a simple regular conflict graph with no edges inside
that union: all planted vertices send their stubs across the cut, cross-degrees
on the other side are balanced, and the remaining degree sequence is realized
and randomized by degree-preserving switches. Vertex degree is identical
everywhere and edge order is shuffled.

The attack panel probes triangle/four-cycle outliers, deterministic residual-
degree greedy, 256 randomized greedy restarts, a smallest-eigenvector spectral
ordering, and obvious raw-label ansatzes. The successful coset decoder is
separate. canonical_key uses exact graph invariants and is invariant under
arbitrary hero relabelling, edge reordering, and endpoint reversal; it is not a
complete graph-isomorphism canonizer, so collisions remain theoretically
possible.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 250_000


def _popcount(value: int) -> int:
    # Keep compatibility with the Python version used by the repository
    # harness, which predates int.bit_count().
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
    team_size = 2 * n // 7
    outside_size = n - team_size
    if type(degree) is not int or not (3 <= degree < outside_size):
        raise ValueError("degree must be an integer in [3, n-2n/7)")
    if degree * (n - 2 * team_size) % 2:
        raise ValueError("residual outside degree sum must be even")


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
    """Realize a simple degree sequence and erase construction order by switches."""

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
    """Decode the certified team from public metadata and count modular ops."""

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
    outside = [v for v in vertices if v not in independent]
    cross_total = degree * len(independent)
    cross_floor, cross_extra = divmod(cross_total, len(outside))
    if cross_floor < 1 or cross_floor + int(bool(cross_extra)) >= degree:
        raise ValueError("parameters do not admit balanced cross degrees")

    independent_list = sorted(independent)
    for _attempt in range(20_000):
        outside_order = outside[:]
        rng.shuffle(outside_order)
        cross_degree = {v: cross_floor for v in outside}
        for v in outside_order[:cross_extra]:
            cross_degree[v] += 1
        capacity = dict(cross_degree)
        cross_pairs: list[tuple[int, int]] = []
        inside_order = independent_list[:]
        rng.shuffle(inside_order)
        good = True
        for w in inside_order:
            chosen: set[int] = set()
            for _ in range(degree):
                candidates = [
                    v for v in outside if capacity[v] > 0 and v not in chosen
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

        residual = {v: degree - cross_degree[v] for v in outside}
        internal = _randomized_havel_hakimi(outside, residual, rng)
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
    raise RuntimeError("could not realize the regular conflict graph")


def make_instance(
    n: int,
    seed: int = 0,
    *,
    degree: int,
    **params: Any,
) -> dict:
    """Choose a certified team first, then build its Underlords instance."""

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
    planted = set(answer)
    team_size = 2 * n // 7
    if len(planted) != team_size or center in planted:
        raise AssertionError("coset decoder produced the wrong team")
    conflicts = _sample_regular_around_independent(
        vertices, planted, degree, rng
    )
    alliance_count = math.comb(n, 2) - len(conflicts)
    maximum_power = team_size * team_size
    return {
        "family": "equal-power two-hero-alliance Underlords team",
        "n": n,
        "prime": prime,
        "center": center,
        "primitive_root": primitive_root,
        "coset_offsets": offsets,
        "field_tag_valid": True,
        "conflict_degree": degree,
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
        "alliance_count": alliance_count,
        "team_limit": team_size,
        "team_size": team_size,
        "base_power": 1,
        "member_bonus": 1,
        "power_threshold": maximum_power - 1,
        "maximum_power": maximum_power,
        "decoder_operations": decoder_operations,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Return the complete standalone problem and its exact output grammar."""

    conflicts = sorted(tuple(sorted(edge)) for edge in inst["conflicts"])
    conflict_text = "\n".join(f"{u} {v}" for u, v in conflicts)
    offsets = ", ".join(map(str, inst["coset_offsets"]))
    example = ", ".join(map(str, range(inst["team_size"])))
    statement = f"""DOTA UNDERLORDS — MAXIMUM-POWER TEAM WITNESS

There are {inst['n']} heroes. Their labels are all integers from 0 through
{inst['prime'] - 1}, inclusive, except the omitted label {inst['center']}.
Choose a team containing at most {inst['team_limit']} distinct heroes.

Every hero has base power 1. Every unordered pair of distinct heroes is a
two-hero alliance except the {inst['conflict_count']} conflict pairs listed
below. An alliance is active exactly when both of its heroes are on the team.
Each active alliance gives bonus power 1 to each of its two members, hence 2
total bonus power. There are no other alliances or bonuses.

For a team T, its exact total power is therefore

    |T| + 2 * (number of unordered nonconflict pairs contained in T).

Find a team whose total power is strictly greater than
{inst['power_threshold']}. Since |T| is at most {inst['team_limit']}, this is
equivalent to giving exactly {inst['team_size']} heroes with no listed
conflict pair between two chosen heroes. The maximum attainable power is
{inst['maximum_power']}.

The instance also carries this public finite-field tag for a possible compact
route (all arithmetic in the tag is modulo the prime p):

    prime p = {inst['prime']}
    center b = {inst['center']}
    primitive root g modulo p = {inst['primitive_root']}
    exponent-class offsets modulo 7 = {offsets}

The tag does not relax the witness conditions: grading uses only the chosen
team, the conflict list, and the power formula above.

CONFLICT PAIRS (one unordered pair u v per row)
{conflict_text}

Order of chosen heroes is irrelevant. Repeats are forbidden. Every output
label must be an integer in the inclusive range 0..{inst['prime'] - 1}, and
the omitted label {inst['center']} is forbidden.

Give your final answer inside <answer></answer> tags, as a comma-separated list
of exactly {inst['team_size']} distinct integer hero labels.
Example: <answer>{example}</answer>
The example shows syntax only and is not necessarily a valid team.
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


def _normalized_conflicts(inst: dict) -> list[tuple[int, int]]:
    return sorted(tuple(sorted(edge)) for edge in inst["conflicts"])


def _team_power(inst: dict, team: set[int]) -> int:
    conflicts_inside = sum(
        1 for u, v in _normalized_conflicts(inst) if u in team and v in team
    )
    active_alliances = math.comb(len(team), 2) - conflicts_inside
    return inst["base_power"] * len(team) + 2 * inst["member_bonus"] * active_alliances


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid team exactly; never inspect inst['answer']."""

    if not isinstance(answer, list):
        return False, "answer must be a list of hero labels"
    if not answer:
        return False, "answer is empty"
    if any(type(v) is not int for v in answer):
        return False, "every hero label must be an integer"
    if len(answer) != inst["team_size"]:
        return False, f"expected exactly {inst['team_size']} hero labels"
    if len(set(answer)) != len(answer):
        return False, "hero labels must be distinct"
    allowed = set(_vertices(inst))
    if any(v not in allowed for v in answer):
        return False, (
            f"a label is outside 0..{inst['prime'] - 1} or equals omitted "
            f"label {inst['center']}"
        )
    team = set(answer)
    for u, v in _normalized_conflicts(inst):
        if u in team and v in team:
            return False, f"conflict pair {u}-{v} lies inside the proposed team"
    power = _team_power(inst, team)
    if power <= inst["power_threshold"]:
        return False, (
            f"team power {power} is not strictly greater than "
            f"{inst['power_threshold']}"
        )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the exact-size distinct-label space stated to solvers."""

    return sorted(rng.sample(_vertices(inst), inst["team_size"]))


def search_space(inst: dict) -> int | None:
    return math.comb(inst["n"], inst["team_size"])


def enumerate_all(inst: dict) -> int | None:
    """Count all valid teams only when exact enumeration is safely bounded."""

    if search_space(inst) > _ENUMERATION_CAP:
        return None
    conflicts = _normalized_conflicts(inst)
    count = 0
    for candidate in itertools.combinations(_vertices(inst), inst["team_size"]):
        chosen = set(candidate)
        if all(u not in chosen or v not in chosen for u, v in conflicts):
            count += 1
    return count


def _adjacency_bits(inst: dict) -> tuple[list[int], list[int], dict[int, int]]:
    labels = _vertices(inst)
    position = {label: index for index, label in enumerate(labels)}
    adjacency = [0] * len(labels)
    for u, v in _normalized_conflicts(inst):
        ui, vi = position[u], position[v]
        adjacency[ui] |= 1 << vi
        adjacency[vi] |= 1 << ui
    return adjacency, labels, position


def _graph_invariant_payload(inst: dict) -> dict:
    """Strong cheap invariants independent of labels and conflict-row order."""

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
                next_frontier |= adjacency[low.bit_length() - 1]
                bits ^= low
            next_frontier &= ~seen
            seen |= next_frontier
            frontier = next_frontier
            distance += 1
        if _popcount(seen) != n:
            distances[-1] = distances.get(-1, 0) + n - _popcount(seen)
    return {
        "n": n,
        "m": inst["conflict_count"],
        "target": inst["team_size"],
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
    return all(
        u not in chosen or v not in chosen
        for u, v in _normalized_conflicts(inst)
    )


def _attack_outlier_local_motif(inst: dict) -> list[int] | None:
    """Rank vertices by local triangles/four-cycles in both directions."""

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
    target = inst["team_size"]
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
    if len(candidate) < inst["team_size"]:
        return None
    candidate = sorted(candidate[: inst["team_size"]])
    return candidate if _independent(inst, candidate) else None


def _attack_random_restarts(
    inst: dict, seed: int, restarts: int = 256
) -> tuple[list[int] | None, int]:
    rng = random.Random(seed ^ 0xD07A2007)
    target = inst["team_size"]
    for attempt in range(1, restarts + 1):
        candidate = _greedy_independent(inst, rng)
        if len(candidate) >= target:
            candidate = sorted(candidate[:target])
            if _independent(inst, candidate):
                return candidate, attempt
    return None, restarts


def _attack_spectral(inst: dict) -> list[int] | None:
    """A standard-library smallest-adjacency-eigenvector heuristic."""

    adjacency, labels, _position = _adjacency_bits(inst)
    n = len(labels)
    vector = [math.sin((i + 1) * 1.61803398875) for i in range(n)]
    mean = sum(vector) / n
    vector = [value - mean for value in vector]
    for _ in range(120):
        nxt = [0.0] * n
        for v in range(n):
            total = float(inst["conflict_degree"]) * vector[v]
            bits = adjacency[v]
            while bits:
                low = bits & -bits
                total -= vector[low.bit_length() - 1]
                bits ^= low
            nxt[v] = total
        norm = math.sqrt(sum(value * value for value in nxt)) or 1.0
        vector = [value / norm for value in nxt]

    target = inst["team_size"]
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
    """Cheap by-hand guesses using order, parity, and unpowered residues."""

    labels = _vertices(inst)
    target = inst["team_size"]
    offsets = set(inst["coset_offsets"])
    centered = sorted(
        labels, key=lambda v: ((v - inst["center"]) % inst["prime"])
    )
    candidates = [
        sorted(labels)[:target],
        sorted(labels)[-target:],
        sorted(labels, key=lambda v: (v % 2, v))[:target],
        sorted(labels, key=lambda v: (v % 7 not in offsets, v))[:target],
        sorted(centered[:target]),
    ]
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
    transformed["conflicts"] = [
        [permutation[u], permutation[v]] for u, v in inst["conflicts"]
    ]
    transformed["answer"] = sorted(permutation[v] for v in inst["answer"])
    transformed["field_tag_valid"] = False
    return transformed


# Updated only from transcripts produced by scripts/harden.py in isolated dirs.
G9_AUDIT = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "pending",
}


def selftest() -> dict:
    """Run and measure G1--G9; return a wholly JSON-native report."""

    report: dict[str, Any] = {
        "paper": "2007.05020",
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
            for edge in shipping["conflicts"]
        )
    )
    corruptions: dict[str, object] = {
        "drop_one": planted[:-1],
        "swap_one": planted[1:] + [replacement],
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
        "The field classes give this team.\n```text\n<answer>\n"
        + ", ".join(map(str, planted))
        + "\n</answer>\n```\nIts recomputed power reaches the strict bound."
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
        reordered["conflicts"] = [
            edge[::-1] for edge in reversed(inst["conflicts"])
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
            "arbitrary hero relabelling with carried witness",
            "conflict-row reorder plus endpoint reversal",
            "their composition",
        ],
        "failures": g8_failures,
    }

    longest = sorted(_vertices(shipping), reverse=True)[: shipping["team_size"]]
    serialized = json.dumps(sorted(longest), separators=(",", ":"))
    answer_chars = len(serialized)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = shipping["team_size"]
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
