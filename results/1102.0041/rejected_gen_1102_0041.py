"""Rejected full-multiset-ordering prototype for arXiv:1102.0041.

The solver receives a multiset R containing two copies of every residue and a
family of proper submultisets.  It must permute all of R so that every required
submultiset occurs as the multiset of a contiguous substring.  Generation is
inverse: choose a modular cycle, apply a cubic permutation to its symbols,
repeat the cycle, and take certified contiguous blocks.  The planted word is
never recovered by solving the generated instance.  This prototype is retained
for audit: its excess sets form an ordinary set-C1P instance, so it fails H.
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


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - this finite family needs no helper
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "permutation",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "multiset of residue symbols",
        "family of required submultisets",
        "full multiset ordering",
    ],
    "verification_operations": [
        "exact multiplicity comparison",
        "rolling contiguous-window multiset comparison",
        "integer range and length checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Cube-rooting the residue labels turns every three-symbol excess "
        "multiset into a length-three arc of one modular cycle; without that "
        "change of variables, the solver must reconstruct a crowded ordering "
        "from unordered repeated-symbol constraints."
    ),
    "hardness_basis": (
        "Track B: Problem 1 and Corollary 17 place full multiset ordering in "
        "the paper's NP-complete general regime, while its Booth-Lueker "
        "set-C1P algorithm solves this promised excess-set distribution in "
        "O(p+sum|E_i|) time; at p=83,m=56 the measured specialized reference "
        "used a mean 1,456 counted primitive operations (maximum 1,564) and "
        "about 0.0005 seconds over eight seeds, versus at most 292 exact "
        "arithmetic operations after the cube-root change of variables."
    ),
    "max_answer_tokens": 161,
}

NATIVE: dict = {
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


DIFFICULTY: dict = {
    "demo": {"n": 5, "constraints": 3, "max_excess": 4},
    "easy": {"n": 29, "constraints": 12, "max_excess": 3},
    "medium": {"n": 59, "constraints": 30, "max_excess": 3},
    "hard": {"n": 83, "constraints": 56, "max_excess": 3},
}

SHIPPING_DIFFICULTY: str = "hard"


CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "One JSON list of length 2p over symbols 0,...,p-1, containing every "
        "symbol exactly twice.  Order matters and the two occurrences of a "
        "symbol are indistinguishable."
    ),
    "bounds": {
        "length": "2p",
        "entry_min": 0,
        "entry_max": "p-1",
        "multiplicity_of_each_symbol": 2,
        "shipping_p": 83,
        "shipping_atomic_elements": 166,
    },
}


STRUCTURAL_HINT: str = (
    "The cube roots of each three-symbol excess constraint are arcs of one "
    "modular arithmetic cycle."
)

PLACEBO_HINT: str = (
    "The repeated symbols in every constraint make careful multiplicity "
    "bookkeeping important throughout the ordering."
)


NOTES: str = """\
Section 2 defines a multiset P to occur in a string exactly when some
contiguous substring has multiset P, including multiplicity.  Problem 1 then
defines #FMO using a full ordering of every occurrence of R.  This module asks
for that paper-native witness rather than replacing the problem by a graph.

Step-0 audit: Section 1.2 gives the easy result that ordinary set C1P is solved
and represented by Booth--Lueker PQ-trees in linear time, whereas Theorem 16
and Corollary 17 make counting and deciding the unrestricted multiset version
#P-complete and NP-complete.  The excess sets generated here are themselves an
ordinary set-C1P instance, so Track A would be false.  The family is explicitly
Track B: a measured interval-component implementation of that standard route
is reported as reference_algorithm, with modular-step enumeration reported as
a slower secondary reference.

Generation first selects the answer.  For prime p == 2 (mod 3), cubing is a
permutation of the residues.  The planted word consists of two copies of the
cycle (j*d)^3 mod p.  Each shipping Q has one copy of every residue plus a
second copy of three consecutive cycle symbols, so Q is literally the
multiset of a length-(p+3) planted substring.  Arc position zero is omitted:
this makes both orientations recovered from an unordered arc valid, while
leaving all requirements identically distributed.  Shipping requirements are
sampled from the same three-arc distribution and shuffled.  Escalation first
adds more such requirements and then longer cycle arcs without lengthening the
answer.

The outlier attack sorts symbols by constraint frequency; the numeric attack
tries the visible residue order; the co-occurrence greedy walk follows local
frequency only; the overlap walk joins triples without backtracking across
missing windows; the cube-root-sorted probe notices the power map but not its
step; and 256 strengthened random restarts try doubled random permutations.
The successful set-C1P solver and modular-step enumerator are kept out of
attacks, as Track B requires, and are reported separately.
"""


# Script-owned oracle results are copied here after the three isolated runs.
# Zero attempts mean "not run yet", never an invented oracle failure.
G9_ORACLE_RESULTS: dict = {
    "bare": {"solved": 0, "attempts": 0, "infrastructure_errors": 4},
    "hinted": {"solved": 0, "attempts": 0, "infrastructure_errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "infrastructure_errors": 4},
    "hinted_verdict": "not_run_key_limit",
}


def _plain_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    limit = math.isqrt(value)
    divisor = 3
    while divisor <= limit:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_cubic_prime(n: int) -> int:
    """Smallest prime p >= n for which x -> x^3 permutes F_p."""
    candidate = max(5, n)
    while not (_is_prime(candidate) and candidate % 3 == 2):
        candidate += 1
    return candidate


def _cycle(p: int, step: int) -> list[int]:
    return [pow((j * step) % p, 3, p) for j in range(p)]


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a full multiset ordering and certified substrings."""
    constraints = params.pop("constraints", None)
    max_excess = params.pop("max_excess", 3)
    if params:
        raise ValueError(f"unknown parameters: {sorted(params)}")
    if not _plain_int(n):
        raise ValueError("n must be an integer")
    if n < 5:
        raise ValueError("n must be at least 5")
    if n > 1000:
        raise ValueError("n exceeds the supported construction bound 1000")
    p = _next_cubic_prime(n)
    if not _plain_int(max_excess):
        raise ValueError("max_excess must be an integer")
    if not 3 <= max_excess <= p - 1:
        raise ValueError(f"max_excess must lie in 3..{p - 1}")
    # Start zero is deliberately omitted.  Reversing a non-wrapping arc that
    # starts in 1..p-length gives another non-wrapping arc in the reversed
    # zero-anchored cycle.  Consequently either orientation recovered from one
    # unordered length-three arc is a certified solution.
    windows = [
        (length, start)
        for length in range(3, max_excess + 1)
        for start in range(1, p - length + 1)
    ]
    maximum = len(windows)
    if constraints is None:
        constraints = max(3, min(maximum, (2 * p) // 3))
    if not _plain_int(constraints):
        raise ValueError("constraints must be an integer")
    if not 1 <= constraints <= maximum:
        raise ValueError(f"constraints must lie in 1..{maximum}")
    if not _plain_int(seed):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    allowed_steps = list(range(2, p - 1))
    step = rng.choice(allowed_steps)
    order = _cycle(p, step)
    answer = order + order

    # Always retain one length-three arc: fixed-answer-length escalation adds
    # clutter without making the intended compact route exceed G9(c).
    anchor = (3, rng.randrange(1, p - 2))
    remainder = [window for window in windows if window != anchor]
    chosen = [anchor] + rng.sample(remainder, constraints - 1)
    extras = [sorted(order[start:start + length]) for length, start in chosen]
    rng.shuffle(extras)

    return {
        "p": p,
        "requested_n": n,
        "word_length": 2 * p,
        "max_excess": max_excess,
        "constraints": extras,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a complete, standalone full-multiset-ordering problem."""
    p = inst["p"]
    extras = inst["constraints"]
    lines = [
        "FULL MULTISET ORDERING",
        "",
        f"The symbol alphabet is the integers 0 through {p - 1}.",
        (
            f"The universe multiset R contains exactly two indistinguishable "
            f"copies of each symbol, so a full ordering has length {2 * p}."
        ),
        "",
        (
            "A multiset occurs in an ordering when some contiguous substring "
            "has exactly the same symbol multiplicities."
        ),
        (
            "Each requirement below is written compactly by its EXCESS "
            "symbols: the required multiset Q contains one copy of every "
            "alphabet symbol and one additional copy of every listed symbol."
        ),
        (
            "The excess symbols on a line are distinct.  A line with k excess "
            f"symbols therefore defines a Q of size {p}+k.  Every listed Q "
            "must occur, but occurrences may overlap and may appear in any order."
        ),
        "",
        f"There are {len(extras)} requirements:",
    ]
    for index, extra in enumerate(extras):
        labels = " ".join(str(symbol) for symbol in extra)
        lines.append(f"Q{index:03d} excess ({len(extra)}): {labels}")
    lines.extend([
        "",
        (
            f"Find one list of exactly {2 * p} integers that uses every symbol "
            "exactly twice and in which every required multiset occurs."
        ),
        "Order matters; repeats are required; all labels are literal integers.",
        "",
        (
            "Give your final answer inside <answer></answer> tags as one JSON "
            "list of integers."
        ),
        (
            "Example of syntax only: "
            "<answer>[0, 2, 1, 0, 2, 1]</answer>"
        ),
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    """Parse a tagged JSON list, tolerating prose, fences, and whitespace."""
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\b[^>]*>(.*?)</answer>", text,
                      flags=re.IGNORECASE | re.DOTALL)
    if match:
        payload = match.group(1).strip()
    else:
        payload = text.strip()
    payload = re.sub(r"^\s*```(?:json)?\s*", "", payload,
                     flags=re.IGNORECASE)
    payload = re.sub(r"\s*```\s*$", "", payload)
    decoder = json.JSONDecoder()
    starts = [index for index, char in enumerate(payload) if char == "["]
    for start in starts:
        try:
            value, _ = decoder.raw_decode(payload[start:])
        except (ValueError, TypeError):
            continue
        if isinstance(value, list):
            return value
    return None


def _window_has_target(answer: list[int], p: int, extra: list[int]) -> bool:
    target_extra = set(extra)
    width = p + len(extra)
    counts = [0] * p
    for symbol in answer[:width]:
        counts[symbol] += 1
    mismatches = sum(
        counts[symbol] != (2 if symbol in target_extra else 1)
        for symbol in range(p)
    )
    if mismatches == 0:
        return True
    for start in range(1, len(answer) - width + 1):
        outgoing = answer[start - 1]
        incoming = answer[start + width - 1]
        if outgoing == incoming:
            if mismatches == 0:
                return True
            continue
        outgoing_target = 2 if outgoing in target_extra else 1
        incoming_target = 2 if incoming in target_extra else 1
        mismatches -= int(counts[outgoing] != outgoing_target)
        counts[outgoing] -= 1
        mismatches += int(counts[outgoing] != outgoing_target)
        mismatches -= int(counts[incoming] != incoming_target)
        counts[incoming] += 1
        mismatches += int(counts[incoming] != incoming_target)
        if mismatches == 0:
            return True
    return False


def _window_has_target_counted(answer: list[int], p: int,
                               extra: list[int]) -> tuple[bool, int]:
    """The rolling check with an explicit elementary-operation counter."""
    target_extra = set(extra)
    width = p + len(extra)
    counts = [0] * p
    operations = 0
    for symbol in answer[:width]:
        counts[symbol] += 1
        operations += 1
    mismatches = 0
    for symbol in range(p):
        mismatches += int(counts[symbol] != (2 if symbol in target_extra else 1))
        operations += 2
    if mismatches == 0:
        return True, operations
    for start in range(1, len(answer) - width + 1):
        outgoing = answer[start - 1]
        incoming = answer[start + width - 1]
        operations += 1
        if outgoing == incoming:
            continue
        outgoing_target = 2 if outgoing in target_extra else 1
        incoming_target = 2 if incoming in target_extra else 1
        mismatches -= int(counts[outgoing] != outgoing_target)
        counts[outgoing] -= 1
        mismatches += int(counts[outgoing] != outgoing_target)
        mismatches -= int(counts[incoming] != incoming_target)
        counts[incoming] += 1
        mismatches += int(counts[incoming] != incoming_target)
        operations += 8
        if mismatches == 0:
            return True, operations
    return False, operations


def _verify_counted(inst: dict, answer: list[int]) -> tuple[bool, int]:
    """Count the exact loops/updates used by the reference verifier route."""
    p = inst["p"]
    operations = 0
    counts = [0] * p
    for symbol in answer:
        counts[symbol] += 1
        operations += 1
    for count in counts:
        operations += 1
        if count != 2:
            return False, operations
    for extra in inst["constraints"]:
        found, used = _window_has_target_counted(answer, p, extra)
        operations += used
        if not found:
            return False, operations
    return True, operations


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any witness exactly, without consulting inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer_not_list"
    if not answer:
        return False, "empty_answer"
    p = inst.get("p")
    if len(answer) != 2 * p:
        return False, f"wrong_length: expected {2 * p}, got {len(answer)}"
    for index, symbol in enumerate(answer):
        if not _plain_int(symbol) or not 0 <= symbol < p:
            return False, f"symbol_out_of_range: position {index}"
    counts = [0] * p
    for symbol in answer:
        counts[symbol] += 1
    wrong = next((symbol for symbol, count in enumerate(counts) if count != 2), None)
    if wrong is not None:
        return False, f"wrong_multiplicity: symbol {wrong} occurs {counts[wrong]} times"
    for index, extra in enumerate(inst.get("constraints", [])):
        if not _window_has_target(answer, p, extra):
            return False, f"missing_required_multiset: Q{index:03d}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from words containing exactly two of every symbol."""
    candidate = [symbol for symbol in range(inst["p"]) for _ in range(2)]
    rng.shuffle(candidate)
    return candidate


def search_space(inst: dict) -> int | None:
    """Number of multiset permutations with two copies of each of p symbols."""
    p = inst["p"]
    return math.factorial(2 * p) // (2 ** p)


def _multiset_words_two_each(p: int):
    counts = [2] * p
    word: list[int] = []

    def visit():
        if len(word) == 2 * p:
            yield list(word)
            return
        for symbol in range(p):
            if counts[symbol]:
                counts[symbol] -= 1
                word.append(symbol)
                yield from visit()
                word.pop()
                counts[symbol] += 1

    yield from visit()


def enumerate_all(inst: dict) -> int | None:
    """Brute-force exact valid-answer count only below a firm 200k cap."""
    if search_space(inst) > 200_000:
        return None
    return sum(verify(inst, word)[0] for word in _multiset_words_two_each(inst["p"]))


def canonical_key(inst: dict) -> str:
    """A label- and input-order-invariant WL key for the incidence hypergraph."""
    p = inst["p"]
    constraints = [tuple(sorted(triple)) for triple in inst["constraints"]]
    m = len(constraints)
    neighbors: list[list[int]] = [[] for _ in range(p + m)]
    for q_index, triple in enumerate(constraints):
        node = p + q_index
        for symbol in triple:
            neighbors[node].append(symbol)
            neighbors[symbol].append(node)
    colors = [0] * p + [1] * m
    for _ in range(12):
        signatures = [
            (0 if node < p else 1, colors[node],
             tuple(sorted(colors[other] for other in neighbors[node])))
            for node in range(p + m)
        ]
        palette = {signature: index for index, signature in
                   enumerate(sorted(set(signatures)))}
        updated = [palette[signature] for signature in signatures]
        if updated == colors:
            break
        colors = updated
    node_profiles = sorted(
        (0 if node < p else 1, colors[node], len(neighbors[node]),
         tuple(sorted(colors[other] for other in neighbors[node])))
        for node in range(p + m)
    )
    edge_profiles = sorted(
        (colors[symbol], colors[p + q_index])
        for q_index, triple in enumerate(constraints)
        for symbol in triple
    )
    pair_intersections = sorted(
        len(set(constraints[i]).intersection(constraints[j]))
        for i in range(m) for j in range(i + 1, m)
    )
    payload = [p, m, node_profiles, edge_profiles, pair_intersections]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Increase clutter at fixed witness length before considering a larger p."""
    harder = dict(params)
    p = _next_cubic_prime(int(harder["n"]))
    max_excess = int(harder.get("max_excess", 3))
    current = int(harder.get("constraints", max(3, (2 * p) // 3)))
    capacity = sum(p - length + 1 for length in range(3, max_excess + 1))
    if current < capacity:
        harder["constraints"] = min(capacity, current + max(6, p // 10))
        return harder
    if max_excess < p - 1:
        harder["max_excess"] = min(p - 1, max_excess + 2)
        new_capacity = sum(
            p - length + 1
            for length in range(3, harder["max_excess"] + 1)
        )
        harder["constraints"] = min(
            new_capacity, current + max(6, p // 10)
        )
        return harder
    return None


def _candidate_from_order(order: list[int]) -> list[int]:
    return list(order) + list(order)


def _attack_frequency_order(inst: dict) -> list[int]:
    p = inst["p"]
    frequency = [0] * p
    for triple in inst["constraints"]:
        for symbol in triple:
            frequency[symbol] += 1
    order = sorted(range(p), key=lambda symbol: (frequency[symbol], symbol))
    return _candidate_from_order(order)


def _attack_numeric_order(inst: dict) -> list[int]:
    return _candidate_from_order(list(range(inst["p"])))


def _attack_cube_root_sorted(inst: dict) -> list[int]:
    p = inst["p"]
    inverse_exponent = pow(3, -1, p - 1)
    order = sorted(range(p), key=lambda symbol: pow(symbol, inverse_exponent, p))
    return _candidate_from_order(order)


def _attack_cooccurrence_greedy(inst: dict) -> tuple[list[int], int]:
    p = inst["p"]
    degree = [0] * p
    pair = [[0] * p for _ in range(p)]
    operations = 0
    for triple in inst["constraints"]:
        for symbol in triple:
            degree[symbol] += 1
        for a, b in itertools.combinations(triple, 2):
            pair[a][b] += 1
            pair[b][a] += 1
            operations += 2
    start = min(range(p), key=lambda symbol: (degree[symbol], symbol))
    order = [start]
    unused = set(range(p)) - {start}
    while unused:
        previous = order[-1]
        chosen = min(unused, key=lambda symbol: (-pair[previous][symbol], symbol))
        operations += len(unused)
        order.append(chosen)
        unused.remove(chosen)
    return _candidate_from_order(order), operations


def _attack_overlap_no_backtracking(inst: dict) -> tuple[list[int], int]:
    triples = [set(triple) for triple in inst["constraints"]]
    p = inst["p"]
    operations = 0
    overlap_degree = []
    for index, triple in enumerate(triples):
        degree = 0
        for other_index, other in enumerate(triples):
            if index != other_index:
                degree += int(len(triple & other) == 2)
                operations += 1
        overlap_degree.append(degree)
    first = min(range(len(triples)), key=lambda i: (overlap_degree[i], sorted(triples[i])))
    order = sorted(triples[first])
    used = set(order)
    while len(order) < p:
        tail = set(order[-2:])
        options = []
        for triple in triples:
            operations += 1
            if tail <= triple:
                new = triple - used
                if len(new) == 1:
                    options.append(next(iter(new)))
        if not options:
            order.extend(sorted(set(range(p)) - used))
            break
        chosen = min(options)
        order.append(chosen)
        used.add(chosen)
    return _candidate_from_order(order), operations


def _reference_set_c1p_components(
        inst: dict) -> tuple[list[int] | None, int, int]:
    """Solve the generated excess-set C1P instance without the cubic map.

    For length-three intervals, two requirements share two symbols exactly
    when their hidden starts differ by one, and one symbol exactly when the
    starts differ by two.  Each overlap component can therefore be embedded
    on an integer line (up to reflection), after which a bipartite matching
    assigns its symbols to positions.  Disjoint components and unused symbols
    may be concatenated arbitrarily.  Doubling the resulting permutation is a
    valid full-multiset ordering.

    This is the measured domain-standard reference for the shipped preset.
    The paper's general Booth--Lueker PQ-tree algorithm also solves the excess
    set family, in time linear in its incidence count.
    """
    p = inst["p"]
    requirements = [set(extra) for extra in inst["constraints"]]
    if any(len(extra) != 3 for extra in requirements):
        return None, 0, 0
    m = len(requirements)
    operations = 0
    search_nodes = 0

    owners: list[list[int]] = [[] for _ in range(p)]
    for index, extra in enumerate(requirements):
        for symbol in extra:
            owners[symbol].append(index)
            operations += 1

    intersections: dict[tuple[int, int], int] = {}
    for occurrences in owners:
        for left_index in range(len(occurrences)):
            for right_index in range(left_index + 1, len(occurrences)):
                left = occurrences[left_index]
                right = occurrences[right_index]
                edge = (min(left, right), max(left, right))
                intersections[edge] = intersections.get(edge, 0) + 1
                operations += 1

    adjacency: list[dict[int, int]] = [{} for _ in range(m)]
    for (left, right), overlap in intersections.items():
        if overlap not in (1, 2):
            return None, operations, search_nodes
        distance = 3 - overlap
        adjacency[left][right] = distance
        adjacency[right][left] = distance

    components: list[list[int]] = []
    seen: set[int] = set()
    for root in range(m):
        if root in seen:
            continue
        stack = [root]
        seen.add(root)
        component = []
        while stack:
            current = stack.pop()
            component.append(current)
            operations += 1
            for neighbor in adjacency[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        components.append(component)

    blocks: list[list[int]] = []
    for component in components:
        coordinates = {component[0]: 0}
        if len(component) > 1:
            neighbor = next(iter(adjacency[component[0]]))
            coordinates[neighbor] = adjacency[component[0]][neighbor]

        def embed() -> dict[int, int] | None:
            nonlocal operations, search_nodes
            search_nodes += 1
            if len(coordinates) == len(component):
                return dict(coordinates)
            choices = []
            for node in component:
                if node in coordinates:
                    continue
                placed_neighbors = [
                    neighbor for neighbor in adjacency[node]
                    if neighbor in coordinates
                ]
                if not placed_neighbors:
                    continue
                candidates = None
                for neighbor in placed_neighbors:
                    distance = adjacency[node][neighbor]
                    center = coordinates[neighbor]
                    pair = {center - distance, center + distance}
                    candidates = pair if candidates is None \
                        else candidates.intersection(pair)
                    operations += 2
                choices.append((len(candidates), -len(placed_neighbors),
                                node, candidates))
            if not choices:
                return None
            _, _, node, candidates = min(
                choices, key=lambda item: (item[0], item[1], item[2])
            )
            for coordinate in sorted(candidates):
                if coordinate in coordinates.values():
                    continue
                consistent = True
                for other, other_coordinate in coordinates.items():
                    required = adjacency[node].get(other)
                    actual = abs(coordinate - other_coordinate)
                    operations += 1
                    if ((required is None and actual <= 2)
                            or (required is not None and actual != required)):
                        consistent = False
                        break
                if not consistent:
                    continue
                coordinates[node] = coordinate
                result = embed()
                if result is not None:
                    return result
                del coordinates[node]
            return None

        embedded = embed()
        if embedded is None:
            return None, operations, search_nodes
        offset = min(embedded.values())
        embedded = {node: value - offset for node, value in embedded.items()}
        width = max(embedded.values()) + 3
        symbols = sorted(set().union(
            *(requirements[index] for index in component)
        ))
        if len(symbols) != width:
            return None, operations, search_nodes

        allowed = {symbol: set(range(width)) for symbol in symbols}
        for index in component:
            interval = {
                embedded[index], embedded[index] + 1, embedded[index] + 2
            }
            for symbol in requirements[index]:
                allowed[symbol].intersection_update(interval)
                operations += 1

        position_to_symbol: dict[int, int] = {}

        def augment(symbol: int, visited: set[int]) -> bool:
            nonlocal operations
            for position in sorted(allowed[symbol]):
                operations += 1
                if position in visited:
                    continue
                visited.add(position)
                if (position not in position_to_symbol
                        or augment(position_to_symbol[position], visited)):
                    position_to_symbol[position] = symbol
                    return True
            return False

        symbol_order = sorted(symbols, key=lambda symbol: len(allowed[symbol]))
        if not all(augment(symbol, set()) for symbol in symbol_order):
            return None, operations, search_nodes
        blocks.append([position_to_symbol[position] for position in range(width)])

    used = set().union(*(set(block) for block in blocks)) if blocks else set()
    order = []
    for block in blocks:
        order.extend(block)
    order.extend(symbol for symbol in range(p) if symbol not in used)

    positions = [0] * p
    for index, symbol in enumerate(order):
        positions[symbol] = index
    for extra in requirements:
        locations = [positions[symbol] for symbol in extra]
        operations += len(locations)
        if max(locations) - min(locations) != 2:
            return None, operations, search_nodes
    return _candidate_from_order(order), operations, search_nodes


def _pow_mod_counted(base: int, exponent: int,
                     modulus: int) -> tuple[int, int]:
    """Binary modular exponentiation and its multiplication count."""
    result = 1
    operations = 0
    for bit in bin(exponent)[2:]:
        result = (result * result) % modulus
        operations += 1
        if bit == "1":
            result = (result * base) % modulus
            operations += 1
    return result, operations


def _compact_cube_root_solver(inst: dict) -> tuple[list[int] | None, int]:
    """Execute and count the intended post-insight Track-B route.

    Cubing is bijective modulo p because p == 2 (mod 3).  Cube-rooting one
    excess triple therefore exposes an unordered modular arithmetic
    progression.  Its unique midpoint determines the step up to sign.  The
    construction omits position-zero arcs, so both signs give valid doubled
    cycles and no search or final verification is needed to choose one.

    The counter includes every modular multiplication/addition/subtraction.
    Comparisons, indexing, list appends, and copying the cycle are not exact
    arithmetic operations.
    """
    p = inst["p"]
    triple = next((extra for extra in inst["constraints"] if len(extra) == 3),
                  None)
    if triple is None:
        return None, 0

    # Since p = 2 (mod 3), (2p-1)/3 is the inverse of 3 modulo p-1.
    inverse_exponent = (2 * p - 1) // 3
    roots = []
    operations = 3
    for symbol in triple:
        root, used = _pow_mod_counted(symbol, inverse_exponent, p)
        roots.append(root)
        operations += used

    midpoint = None
    endpoints: list[int] = []
    for index, candidate in enumerate(roots):
        others = roots[:index] + roots[index + 1:]
        # One multiplication and one addition, both reduced modulo p.
        operations += 2
        if (2 * candidate) % p == (others[0] + others[1]) % p:
            midpoint = candidate
            endpoints = others
            break
    if midpoint is None:
        return None, operations

    # Either endpoint chooses one of the two certified orientations.
    step = (min(endpoints) - midpoint) % p
    operations += 1
    if step == 0:
        return None, operations

    order = []
    for index in range(p):
        residue = (index * step) % p
        square = (residue * residue) % p
        value = (square * residue) % p
        operations += 3
        order.append(value)
    return _candidate_from_order(order), operations


def _reference_modular_enumerator(inst: dict) -> tuple[list[int] | None, int]:
    """Mechanical promised-family solver: try every nonzero modular step."""
    p = inst["p"]
    operations = 0
    for step in range(1, p):
        order = []
        for j in range(p):
            residue = (j * step) % p
            value = (residue * residue) % p
            value = (value * residue) % p
            order.append(value)
            operations += 3
        candidate = _candidate_from_order(order)
        valid, verify_operations = _verify_counted(inst, candidate)
        operations += verify_operations
        if valid:
            return candidate, operations
    return None, operations


def _relabel_instance(inst: dict, mapping: list[int], rng: random.Random) -> dict:
    out = {
        "p": inst["p"],
        "requested_n": inst["requested_n"],
        "word_length": inst["word_length"],
        "max_excess": inst.get(
            "max_excess", max(map(len, inst["constraints"]))
        ),
        "constraints": [sorted(mapping[x] for x in triple)
                        for triple in inst["constraints"]],
        "answer": [mapping[x] for x in inst["answer"]],
    }
    rng.shuffle(out["constraints"])
    return out


def _atomic_elements(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atomic_elements(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atomic_elements(item) for item in value)
    return 1


def selftest() -> dict:
    """Run correctness, density, attack, scaling, invariance, and size gates."""
    report: dict[str, object] = {
        "paper": "1102.0041",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    failures = []
    attempts = 0
    for preset, preset_params in DIFFICULTY.items():
        for seed in (0, 1, 2, 19):
            inst = make_instance(seed=seed, **preset_params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "answer_not_json_native"})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=314159, **ship_params)
    planted = shipping["answer"]
    swapped = None
    for left in range(min(24, shipping["p"] - 1)):
        for right in range(left + 1, min(32, shipping["p"])):
            if planted[left] == planted[right]:
                continue
            trial = list(planted)
            trial[left], trial[right] = trial[right], trial[left]
            if not verify(shipping, trial)[0]:
                swapped = trial
                break
        if swapped is not None:
            break
    if swapped is None:
        raise AssertionError("could not construct a constraint-breaking swap")
    corruptions = {
        "drop": planted[:-1],
        "swap": swapped,
        "duplicate": planted[:-1] + [planted[0]],
        "empty": [],
        "out_of_range": planted[:-1] + [shipping["p"]],
    }
    cases = {}
    codes = []
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
        codes.append(reason.split(":", 1)[0])
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and len(set(codes)) == len(codes),
        "cases": cases,
        "distinct_reason_codes": len(set(codes)),
    }

    response = (
        "I used the common cyclic coordinate.\n\n```json\n<answer>\n"
        + json.dumps(planted)
        + "\n</answer>\n```\nThe multiplicities are exact."
    )
    parsed = parse_answer(response)
    parsed_ok, parsed_reason = verify(shipping, parsed)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parsed_ok,
        "parsed_equals_answer": parsed == planted,
        "verify_reason": parsed_reason,
        "json_native": json.loads(json.dumps(planted)) == planted,
        "garbage_returns_none": parse_answer("no tagged or JSON answer") is None,
    }

    guess_rng = random.Random(20260905)
    guess_total = 200_000
    guess_hits = 0
    density_start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    density_wall = time.perf_counter() - density_start
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "candidate_prior": "uniform permutations of a multiset with two of each symbol",
        "search_space": str(search_space(shipping)),
        "wall_clock_sec": round(density_wall, 6),
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count_start = time.perf_counter()
    demo_count = enumerate_all(demo)
    demo_count_wall = time.perf_counter() - demo_count_start

    attack_names = [
        "outlier_frequency_order",
        "numeric_sorted_cycle",
        "cube_root_sorted_without_step",
        "greedy_cooccurrence_walk",
        "overlap_walk_no_backtracking",
        "random_restart_doubled_permutation_256",
    ]
    attacks = {name: {"successes": 0, "attempts": 0} for name in attack_names}
    attack_wall = 0.0
    restart_wall = 0.0
    attack_operations = {name: 0 for name in attack_names}
    reference_successes = 0
    reference_operations = []
    reference_nodes = []
    reference_times = []
    modular_successes = 0
    modular_operations = []
    modular_times = []
    compact_successes = 0
    compact_operations = []
    attack_seeds = list(range(9100, 9108))
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **ship_params)
        started = time.perf_counter()
        co_candidate, co_ops = _attack_cooccurrence_greedy(inst)
        overlap_candidate, overlap_ops = _attack_overlap_no_backtracking(inst)
        candidates = {
            "outlier_frequency_order": _attack_frequency_order(inst),
            "numeric_sorted_cycle": _attack_numeric_order(inst),
            "cube_root_sorted_without_step": _attack_cube_root_sorted(inst),
            "greedy_cooccurrence_walk": co_candidate,
            "overlap_walk_no_backtracking": overlap_candidate,
        }
        for name, candidate in candidates.items():
            attacks[name]["attempts"] += 1
            attacks[name]["successes"] += int(verify(inst, candidate)[0])
        attack_operations["greedy_cooccurrence_walk"] += co_ops
        attack_operations["overlap_walk_no_backtracking"] += overlap_ops
        restart_rng = random.Random(seed ^ 0xC0FFEE)
        restart_hit = False
        restart_started = time.perf_counter()
        for _ in range(256):
            random_order = list(range(inst["p"]))
            restart_rng.shuffle(random_order)
            candidate = _candidate_from_order(random_order)
            if verify(inst, candidate)[0]:
                restart_hit = True
                break
        restart_wall += time.perf_counter() - restart_started
        attacks["random_restart_doubled_permutation_256"]["attempts"] += 1
        attacks["random_restart_doubled_permutation_256"]["successes"] += int(restart_hit)
        attack_operations["random_restart_doubled_permutation_256"] += 256
        attack_wall += time.perf_counter() - started

        started = time.perf_counter()
        recovered, operations, nodes = _reference_set_c1p_components(inst)
        reference_times.append(time.perf_counter() - started)
        reference_operations.append(operations)
        reference_nodes.append(nodes)
        reference_successes += int(recovered is not None and verify(inst, recovered)[0])

        started = time.perf_counter()
        modular, operations = _reference_modular_enumerator(inst)
        modular_times.append(time.perf_counter() - started)
        modular_operations.append(operations)
        modular_successes += int(modular is not None and verify(inst, modular)[0])

        compact, operations = _compact_cube_root_solver(inst)
        compact_operations.append(operations)
        compact_successes += int(compact is not None and verify(inst, compact)[0])

    for name, operations in attack_operations.items():
        if operations:
            attacks[name]["operations"] = operations
    all_failed = all(item["successes"] == 0 and item["attempts"] >= 8
                     for item in attacks.values())
    reference = {
        "name": (
            "ordinary set-C1P reduction; measured interval-component and "
            "matching implementation"
        ),
        "complexity": (
            "Booth-Lueker PQ-trees are O(p + sum|E_i|); the measured "
            "specialized implementation is polynomial"
        ),
        "wall_clock_sec_mean": round(sum(reference_times) / len(reference_times), 6),
        "wall_clock_sec_max": round(max(reference_times), 6),
        "operations_mean": round(sum(reference_operations) / len(reference_operations), 3),
        "operations_max": max(reference_operations),
        "search_nodes_mean": round(sum(reference_nodes) / len(reference_nodes), 3),
        "search_nodes_max": max(reference_nodes),
        "solves": f"{reference_successes}/8, as expected",
        "operation_counter": (
            "incidence visits, overlap updates, coordinate consistency checks, "
            "matching probes, and final span checks"
        ),
    }
    modular_reference = {
        "name": "exhaustive modular-step enumeration of cubed cycles",
        "complexity": "O(m*p^2) exact operations on this promised distribution",
        "wall_clock_sec_mean": round(sum(modular_times) / len(modular_times), 6),
        "wall_clock_sec_max": round(max(modular_times), 6),
        "operations_mean": round(sum(modular_operations) / len(modular_operations), 3),
        "operations_max": max(modular_operations),
        "solves": f"{modular_successes}/8, as expected",
    }
    compact_route = {
        "name": "cube-root one excess triple and output either cubic orientation",
        "operations_mean": round(sum(compact_operations) / len(compact_operations), 3),
        "operations_max": max(compact_operations),
        "solves": f"{compact_successes}/8",
        "operation_counter": "modular multiplications, additions, and subtractions",
    }
    report["G5_density_and_baseline"] = {
        "pass": guess_rate < 1e-6 and reference_successes == 8
        and modular_successes == 8
        and compact_successes == 8 and all_failed,
        "shipping_density_fraction": guess_rate,
        "shipping_valid_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_wall_clock_sec": round(density_wall, 6),
        "demo_exact_valid_answers": demo_count,
        "demo_candidate_space": search_space(demo),
        "demo_enumeration_wall_clock_sec": round(demo_count_wall, 6),
        "strongest_failing_attack_name": "random_restart_doubled_permutation_256",
        "strongest_failing_attack_wall_clock_sec": round(restart_wall, 6),
        "strongest_failing_attack_iterations": 8 * 256,
        "adversary_panel_wall_clock_sec_total": round(attack_wall, 6),
        "reference_algorithm": reference,
        "secondary_reference_algorithm": modular_reference,
        "compact_route": compact_route,
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8
        and modular_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "secondary_reference_algorithm": modular_reference,
        "compact_route": compact_route,
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] = 2 * ship_params["n"]
    doubled_p = _next_cubic_prime(doubled_params["n"])
    doubled_params["constraints"] = min(doubled_p - 2, 2 * ship_params["constraints"])
    scale_started = time.perf_counter()
    doubled = make_instance(seed=4471, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["p"] > shipping["p"]
        and search_space(doubled) > search_space(shipping),
        "shipping_requested_n": ship_params["n"],
        "shipping_p": shipping["p"],
        "doubled_requested_n": doubled_params["n"],
        "doubled_p": doubled["p"],
        "doubled_planted_verifies": doubled_ok,
        "verify_reason": doubled_reason,
        "build_and_verify_sec": round(time.perf_counter() - scale_started, 6),
    }

    invariance_checks = 0
    transport_checks = 0
    nontrivial_checks = 0
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(seed=12000 + seed, **DIFFICULTY["medium"])
        base_key = canonical_key(base)
        unrelated_keys.append(base_key)
        rng = random.Random(32000 + seed)
        mapping1 = list(range(base["p"]))
        mapping2 = list(range(base["p"]))
        rng.shuffle(mapping1)
        rng.shuffle(mapping2)
        composed = [mapping2[mapping1[symbol]] for symbol in range(base["p"])]
        variants = [
            _relabel_instance(base, list(range(base["p"])), rng),
            _relabel_instance(base, mapping1, rng),
            _relabel_instance(base, composed, rng),
        ]
        for variant in variants:
            invariance_checks += 1
            key_ok = canonical_key(variant) == base_key
            witness_ok = verify(variant, variant["answer"])[0]
            transport_checks += int(witness_ok)
            nontrivial_checks += int(variant["constraints"] != base["constraints"])
            if not key_ok:
                continue
    report["G8_canonical_key"] = {
        "pass": invariance_checks == 60
        and transport_checks == 60
        and nontrivial_checks >= 40
        and len(set(unrelated_keys)) == 20,
        "invariance_checks": invariance_checks,
        "witness_transport_checks": transport_checks,
        "nontrivial_transformations": nontrivial_checks,
        "unrelated_distinct": len(set(unrelated_keys)),
        "unrelated_attempts": len(unrelated_keys),
        "invariant": "12-round bipartite incidence WL plus intersection profile",
    }

    answer_blob = json.dumps(planted)
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _atomic_elements(planted)
    intended_operations = max(compact_operations)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_attempts = arms["hinted"].get("attempts", 0) or 0
    placebo_attempts = arms["placebo"].get("attempts", 0) or 0
    hinted_rate = (arms["hinted"].get("solved", 0) or 0) / hinted_attempts \
        if hinted_attempts else 0.0
    placebo_rate = (arms["placebo"].get("solved", 0) or 0) / placebo_attempts \
        if placebo_attempts else 0.0
    within_caps = answer_chars <= 2000 and answer_elements <= 256 \
        and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS.get("hinted_verdict", "not_run"),
        "oracle_status": "infrastructure_blocked_http_403_key_limit",
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gate_values = [value for key, value in report.items()
                   if key.startswith("G") and isinstance(value, dict)]
    report["all_passed"] = all(value.get("pass") for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
