"""Verified problem generator for arXiv:1911.05032.

The generated problem is the r=2 case of Diverse 3-Hitting Set.  A witness is
an ordered pair of complementary hitting sets.  Generation samples triples
that cross a planted quadratic-character bipartition and closes them under a
multiplicative action, so the witness is known without solving the instance.
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
from collections import Counter


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # This finite-set family needs only exact Python integers.
    exact_matrices = rationals = None


TRACK: str = "B"

STRUCTURAL_HINT = (
    "Look for the two multiplicative orbits distinguished by the quadratic "
    "character of the displayed nonzero coordinates."
)
PLACEBO_HINT = (
    "Keep track of the two requested sets and check every displayed triple "
    "against both sets carefully."
)


PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite universe",
        "3-element constraint family",
        "two hitting sets",
    ],
    "verification_operations": [
        "exact set intersection",
        "exact cardinality comparison",
        "exact symmetric-difference count",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Recognize that multiplicative closure splits the displayed coordinates "
        "by quadratic character; without that symmetry one must mechanically "
        "2-color a large NAE-3-SAT instance."
    ),
    "hardness_basis": (
        "Track B: Section 3 and Theorem 1 give the r^2*d^(k*r)*|U|^O(1) "
        "enumerate-and-augment algorithm, while the implemented exact DPLL "
        "reference route is O(2^|U|*|F|) in the worst case and at the initial "
        "shipping preset (p=149, 40 orbits) solved 8/8 using a measured mean "
        "of 160,162 literal/cardinality inspections in about 0.015 seconds; the "
        "compact route needs 222 modular-square/membership operations once "
        "the quadratic-character symmetry is recognized."
    ),
    "max_answer_tokens": 123,
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


DIFFICULTY = {
    "demo": {"n": 7, "orbit_count": 2},
    "easy": {"n": 83, "orbit_count": 24},
    "medium": {"n": 127, "orbit_count": 32},
    "hard": {"n": 149, "orbit_count": 40},
}
SHIPPING_DIFFICULTY = "hard"


CERTIFICATE_LANGUAGE = {
    "description": (
        "An ordered JSON pair [S1,S2].  Each Si contains exactly k distinct "
        "universe IDs, S1 and S2 are disjoint, and together they contain every "
        "one of the 2k IDs.  Thus a candidate is a uniformly sampled balanced "
        "ordered bipartition; order inside either set is immaterial."
    ),
    "bounds": {
        "number_of_sets": 2,
        "set_size": "k=(p-1)/2",
        "universe_size": "2k=p-1",
        "distinct_elements": True,
        "partition_required": True,
        "max_shipping_atomic_elements": 148,
    },
}


NOTES = """\
Definition: Section 1 defines a hitting set and the Diverse X template, including
the size-at-most-k rule and Hamming diversity.  With r=2, the sum and minimum
pairwise diversity measures coincide.  We set t=2k=|U|, so any feasible pair is
necessarily a balanced complementary pair; each member must hit every displayed
triple.  This is exactly the paper's native Diverse 3-Hitting Set object, not a
graph or finite-field surrogate.  The coordinates only expose an automorphism of
the set system and do not change what verify checks.

What makes it easy: Lemma 1 enumerates at most d^k minimal hitting sets, Section 3
augments every r-tuple by flow, and Theorem 1 obtains
r^2 d^(kr) |U|^O(1).  Section 6 also gives a separate FPT algorithm for minimum
pairwise distance.  Those results rule out an honest Track A claim.  At our
growing k the bound is enormous, but NAE unit-propagation DPLL solves the planted
distribution mechanically; it is reported as the Track B reference algorithm.

Generation is inverse: choose a random coordinate-to-ID permutation, take the
nonzero quadratic residues and nonresidues as the two answer sets, sample every
base triple from the same uniform nonmonochromatic distribution, and include its
full multiplicative orbit.  Every generated triple therefore meets both planted
sets.  Full orbit closure equalizes all one-vertex incidence degrees.  The attack
panel checks degree outliers, an online greedy coloring, 256 uniform balanced
restarts, the obvious coordinate interval, and ID parity.  None is the compact
quadratic-character route.
"""


_G9_ARMS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 2, "attempts": 3},
    "placebo": {"solved": 3, "attempts": 3},
}


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    factor = 3
    while factor * factor <= value:
        if value % factor == 0:
            return False
        factor += 2
    return True


def _next_odd_prime(value: int) -> int:
    candidate = max(3, value)
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _quadratic_residues(p: int) -> set[int]:
    return {x * x % p for x in range(1, (p + 1) // 2)}


def _coordinate_orbit(triple: tuple[int, int, int], p: int) -> set[tuple[int, int, int]]:
    return {
        tuple(sorted((a * triple[0] % p, a * triple[1] % p, a * triple[2] % p)))
        for a in range(1, p)
    }


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a native Diverse 3-Hitting Set instance."""
    orbit_count = params.pop("orbit_count", None)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if isinstance(orbit_count, bool) or not isinstance(orbit_count, int) or orbit_count < 1:
        raise ValueError("orbit_count must be a positive integer")

    p = _next_odd_prime(n)
    coordinates = list(range(1, p))
    k = (p - 1) // 2
    residues = _quadratic_residues(p)
    rng = random.Random(seed)

    # Coordinate q names the element coordinate_to_id[q-1].  Random names make
    # answers vary between seeds without changing the set-system distribution.
    coordinate_to_id = list(range(1, p))
    rng.shuffle(coordinate_to_id)

    coordinate_edges: set[tuple[int, int, int]] = set()
    accepted_orbits = 0
    attempts = 0
    max_attempts = max(10_000, orbit_count * 1_000)
    while accepted_orbits < orbit_count and attempts < max_attempts:
        attempts += 1
        triple = tuple(sorted(rng.sample(coordinates, 3)))
        residue_count = sum(x in residues for x in triple)
        if residue_count in (0, 3):
            continue
        orbit = _coordinate_orbit(triple, p)
        if orbit.issubset(coordinate_edges):
            continue
        coordinate_edges.update(orbit)
        accepted_orbits += 1
    if accepted_orbits != orbit_count:
        raise ValueError("orbit_count exceeds the available distinct mixed orbits")

    def element_id(coordinate: int) -> int:
        return coordinate_to_id[coordinate - 1]

    constraints = [
        sorted(element_id(x) for x in triple) for triple in coordinate_edges
    ]
    rng.shuffle(constraints)
    first = sorted(element_id(x) for x in residues)
    second = sorted(set(range(1, p)) - set(first))

    return {
        "p": p,
        "universe": list(range(1, p)),
        "coordinate_to_id": coordinate_to_id,
        "constraints": constraints,
        "d": 3,
        "r": 2,
        "k": k,
        "diversity_target": p - 1,
        "orbit_count": orbit_count,
        "answer": [first, second],
    }


def render(inst) -> str:
    """Render a complete statement with an exact JSON answer contract."""
    p = inst["p"]
    k = inst["k"]
    lines = [
        "Diverse 3-Hitting Set",
        "",
        "The universe consists of the integer element IDs "
        + json.dumps(inst["universe"], separators=(",", ":"))
        + ".",
        "A hitting set is a set of element IDs having nonempty intersection "
        "with every constraint triple listed below.",
        "For sets A and B, their Hamming distance is the number of IDs in "
        "exactly one of A and B (the size of their symmetric difference).",
        "",
        f"Find exactly two hitting sets S1 and S2.  Each must contain exactly {k} "
        f"distinct IDs, and their Hamming distance must be at least {p - 1}.",
        "Equivalently here, they must be disjoint and together contain the whole "
        "universe.  The order of the two sets and the order of IDs inside a set "
        "do not matter; repeated IDs are forbidden.",
        "",
        f"For reference, the nonzero coordinates are 1 through {p - 1} modulo "
        f"the prime p={p}.  Coordinate q names the element ID in position q of "
        "this coordinate-to-ID list:",
        json.dumps(inst["coordinate_to_id"], separators=(",", ":")),
        "Coordinates are auxiliary labels only: validity is determined solely "
        "by the universe, triples, sizes, and Hamming distance above.",
        "",
        f"Constraint triples ({len(inst['constraints'])} total):",
    ]
    lines.extend(json.dumps(edge, separators=(",", ":")) for edge in inst["constraints"])

    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])

    lines.extend(
        [
            "",
            "Give your final answer inside <answer></answer> tags as one JSON "
            "array [S1,S2] containing two arrays of integer IDs.",
            "Syntax example only (not an answer to this instance): "
            "<answer>[[1,4],[2,3]]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    return "\n".join(lines)


def parse_answer(text) -> object | None:
    """Extract one JSON array from tagged or prose-surrounded model output."""
    if not isinstance(text, str):
        return None
    tagged = re.search(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    candidates = [tagged.group(1)] if tagged else []
    candidates.append(text)
    decoder = json.JSONDecoder()
    for candidate in candidates:
        cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", candidate, flags=re.I | re.S)
        try:
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, list) else None
        except (TypeError, ValueError):
            pass
        for match in re.finditer(r"\[", cleaned):
            try:
                parsed, _end = decoder.raw_decode(cleaned[match.start() :])
            except ValueError:
                continue
            if isinstance(parsed, list):
                return parsed
    return None


def verify(inst, answer) -> tuple[bool, str]:
    """Check any valid diverse pair; the planted answer is never consulted."""
    if not isinstance(answer, list) or len(answer) != 2:
        return False, "answer must be a JSON array containing exactly two sets"
    universe_list = inst.get("universe")
    if not isinstance(universe_list, list):
        return False, "instance has a malformed universe"
    universe = set(universe_list)
    k = inst.get("k")
    normalized = []
    for index, values in enumerate(answer, start=1):
        if not isinstance(values, list):
            return False, f"set {index} must be a JSON array"
        if any(isinstance(x, bool) or not isinstance(x, int) for x in values):
            return False, f"set {index} contains a non-integer element ID"
        if len(set(values)) != len(values):
            return False, f"set {index} contains duplicate element IDs"
        unknown = sorted(set(values) - universe)
        if unknown:
            return False, f"set {index} contains an out-of-universe ID: {unknown[0]}"
        if len(values) != k:
            return False, f"set {index} must contain exactly {k} distinct IDs"
        normalized.append(set(values))

    first, second = normalized
    if first & second:
        return False, "the two sets overlap, so their Hamming distance is too small"
    if first | second != universe:
        return False, "the two sets do not partition the universe"
    distance = len(first ^ second)
    if distance < inst.get("diversity_target", 0):
        return False, "the Hamming-distance target is not met"
    for edge_index, edge in enumerate(inst.get("constraints", []), start=1):
        edge_set = set(edge)
        if not first & edge_set:
            return False, f"set 1 does not hit constraint {edge_index}"
        if not second & edge_set:
            return False, f"set 2 does not hit constraint {edge_index}"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Sample uniformly from balanced ordered bipartitions, the stated structure."""
    universe = list(inst["universe"])
    first = sorted(rng.sample(universe, inst["k"]))
    first_set = set(first)
    second = [x for x in universe if x not in first_set]
    return [first, second]


def search_space(inst) -> int | None:
    """Count balanced ordered bipartitions (the second side is determined)."""
    return math.comb(len(inst["universe"]), inst["k"])


def enumerate_all(inst) -> int | None:
    """Count all valid ordered witnesses when at most 200,000 candidates exist."""
    space = search_space(inst)
    if space is None or space > 200_000:
        return None
    universe = list(inst["universe"])
    total = 0
    for choice in itertools.combinations(universe, inst["k"]):
        first = list(choice)
        first_set = set(first)
        candidate = [first, [x for x in universe if x not in first_set]]
        total += int(verify(inst, candidate)[0])
    return total


def canonical_key(inst) -> str:
    """A strong cheap hypergraph invariant, independent of IDs and input order."""
    universe = list(inst["universe"])
    position = {value: index for index, value in enumerate(universe)}
    size = len(universe)
    degree = [0] * size
    codegree = [[0] * size for _ in range(size)]
    edge_sizes = Counter()
    for edge in inst["constraints"]:
        indices = sorted(position[x] for x in set(edge))
        edge_sizes[len(indices)] += 1
        for i in indices:
            degree[i] += 1
        for offset, i in enumerate(indices):
            for j in indices[offset + 1 :]:
                codegree[i][j] += 1
                codegree[j][i] += 1
    link_signatures = sorted(
        (degree[i], tuple(sorted(codegree[i][j] for j in range(size) if j != i)))
        for i in range(size)
    )
    pair_codegrees = sorted(
        codegree[i][j] for i in range(size) for j in range(i + 1, size)
    )
    invariant = {
        "n": size,
        "k": inst["k"],
        "r": inst["r"],
        "t": inst["diversity_target"],
        "edge_sizes": sorted(edge_sizes.items()),
        "links": link_signatures,
        "pairs": pair_codegrees,
    }
    blob = json.dumps(invariant, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()


def escalate(params) -> dict | str | None:
    """Increase mechanical crowding first, then modulus while the caps permit."""
    current = dict(params)
    current.pop("_preset", None)
    n = int(current["n"])
    orbit_count = int(current["orbit_count"])
    if orbit_count < 40:
        current["orbit_count"] = min(40, orbit_count + 8)
        return current
    p = _next_odd_prime(n)
    for target in (149, 173, 197):
        if p < target:
            current["n"] = target
            return current
    return "cap_bound"


def _candidate_from_first(inst: dict, first_values) -> list[list[int]]:
    first = sorted(set(first_values))
    first_set = set(first)
    return [first, [x for x in inst["universe"] if x not in first_set]]


def _outlier_candidate(inst: dict) -> list[list[int]]:
    degree = Counter()
    for edge in inst["constraints"]:
        degree.update(edge)
    ordered = sorted(inst["universe"], key=lambda x: (-degree[x], x))
    return _candidate_from_first(inst, ordered[: inst["k"]])


def _greedy_candidate(inst: dict) -> list[list[int]]:
    incident = {x: [] for x in inst["universe"]}
    for edge in inst["constraints"]:
        for value in edge:
            incident[value].append(edge)
    assigned: dict[int, int] = {}
    counts = [0, 0]
    for value in sorted(inst["universe"]):
        choices = []
        for color in (0, 1):
            if counts[color] >= inst["k"]:
                continue
            newly_monochromatic = 0
            for edge in incident[value]:
                other = [x for x in edge if x != value]
                if all(x in assigned and assigned[x] == color for x in other):
                    newly_monochromatic += 1
            choices.append((newly_monochromatic, counts[color], color))
        color = min(choices)[2]
        assigned[value] = color
        counts[color] += 1
    return _candidate_from_first(inst, [x for x, color in assigned.items() if color == 0])


def _attack_candidates(inst: dict) -> dict[str, object]:
    coordinate_map = inst["coordinate_to_id"]
    k = inst["k"]
    return {
        "outlier_incidence_degree": _outlier_candidate(inst),
        "greedy_online_balance": _greedy_candidate(inst),
        "coordinate_interval_ansatz": _candidate_from_first(inst, coordinate_map[:k]),
        "id_parity_ansatz": _candidate_from_first(
            inst, [x for x in inst["universe"] if x % 2 == 1]
        ),
    }


def _reference_dpll(inst: dict, node_limit: int = 1_000_000):
    """Exact balanced NAE-3-SAT DPLL; return (answer, metrics)."""
    universe = list(inst["universe"])
    position = {value: index for index, value in enumerate(universe)}
    edges = [tuple(position[x] for x in edge) for edge in inst["constraints"]]
    size = len(universe)
    k = inst["k"]
    degree = [0] * size
    for edge in edges:
        for index in edge:
            degree[index] += 1
    operations = 0
    nodes = 0
    limit_hit = False

    def propagate(colors: list[int]) -> bool:
        nonlocal operations
        while True:
            changed = False
            ones = sum(value == 1 for value in colors)
            zeros = sum(value == 0 for value in colors)
            operations += size
            undecided = size - ones - zeros
            if ones > k or zeros > k or ones + undecided < k or zeros + undecided < k:
                return False
            if ones == k:
                for index, value in enumerate(colors):
                    if value < 0:
                        colors[index] = 0
                        changed = True
            elif zeros == k:
                for index, value in enumerate(colors):
                    if value < 0:
                        colors[index] = 1
                        changed = True
            for edge in edges:
                assigned = []
                unassigned = -1
                for index in edge:
                    operations += 1
                    if colors[index] < 0:
                        unassigned = index
                    else:
                        assigned.append(colors[index])
                if len(assigned) == 3 and assigned[0] == assigned[1] == assigned[2]:
                    return False
                if (
                    len(assigned) == 2
                    and assigned[0] == assigned[1]
                    and colors[unassigned] < 0
                ):
                    colors[unassigned] = 1 - assigned[0]
                    changed = True
            if not changed:
                return True

    def recurse(colors: list[int]):
        nonlocal nodes, limit_hit
        nodes += 1
        if nodes > node_limit:
            limit_hit = True
            return None
        if not propagate(colors):
            return None
        if all(value >= 0 for value in colors):
            return colors if sum(colors) == k else None
        index = max(
            (i for i, value in enumerate(colors) if value < 0),
            key=lambda i: (degree[i], -i),
        )
        for color in (0, 1):
            branch = list(colors)
            branch[index] = color
            result = recurse(branch)
            if result is not None:
                return result
        return None

    initial = [-1] * size
    initial[0] = 0  # Break the global color-complement symmetry.
    colors = recurse(initial)
    if colors is None:
        answer = None
    else:
        first = [universe[i] for i, color in enumerate(colors) if color == 0]
        answer = _candidate_from_first(inst, first)
    return answer, {
        "nodes": nodes,
        "operations": operations,
        "limit_hit": limit_hit,
    }


def _atomic_elements(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atomic_elements(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atomic_elements(item) for item in value)
    return 1


def _relabel(inst: dict, permutation: dict[int, int], reverse_edges: bool = False) -> dict:
    moved = dict(inst)
    moved["universe"] = [permutation[x] for x in inst["universe"]]
    moved["coordinate_to_id"] = [permutation[x] for x in inst["coordinate_to_id"]]
    edges = [[permutation[x] for x in edge] for edge in inst["constraints"]]
    if reverse_edges:
        edges.reverse()
    moved["constraints"] = edges
    moved["answer"] = [[permutation[x] for x in side] for side in inst["answer"]]
    return moved


def selftest() -> dict:
    report = {
        "paper": "1911.05032",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    g1_failures = []
    g1_checks = 0
    for preset, parameters in DIFFICULTY.items():
        for seed in (0, 1, 17, 65537):
            inst = make_instance(seed=seed, **parameters)
            ok, reason = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            try:
                if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                    g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
            except (TypeError, ValueError) as exc:
                g1_failures.append(f"{preset}/{seed}: JSON failure {exc}")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=20260905, **DIFFICULTY[SHIPPING_DIFFICULTY])
    first, second = shipping["answer"]
    swapped = None
    for left in first:
        for right in second:
            candidate = [
                [right if x == left else x for x in first],
                [left if x == right else x for x in second],
            ]
            if not verify(shipping, candidate)[0]:
                swapped = candidate
                break
        if swapped is not None:
            break
    corruptions = {
        "empty": [],
        "drop_one": [first[:-1], second],
        "swap_across_sets": swapped if swapped is not None else [second, first],
        "duplicate": [[first[0], first[0], *first[2:]], second],
        "out_of_range": [[*first[:-1], max(shipping["universe"]) + 1], second],
    }
    corruption_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "The multiplicative coloring gives the following pair.\n```json\n<answer>"
        + json.dumps(shipping["answer"])
        + "</answer>\n```\nThat is my final answer."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"]
        and verify(shipping, parsed)[0]
        and parse_answer("no certificate here") is None,
        "realistic_response_parsed": parsed is not None,
        "equals_planted": parsed == shipping["answer"],
        "garbage_returns_none": parse_answer("no certificate here") is None,
    }

    guess_rng = random.Random(0x191105032)
    sample_total = 200_000
    sample_hits = 0
    for _ in range(sample_total):
        sample_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    empirical = sample_hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": empirical < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "empirical_probability": empirical,
        "candidate_space": search_space(shipping),
        "prior": "uniform over balanced ordered bipartitions; complement, sizes, and diversity are enforced",
    }

    attack_names = list(_attack_candidates(shipping)) + ["random_restart_256"]
    attack_stats = {name: {"successes": 0, "attempts": 0} for name in attack_names}
    reference_successes = 0
    reference_elapsed = 0.0
    reference_operations = 0
    reference_nodes = 0
    reference_instances = []
    for seed in range(19110, 19118):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, candidate in _attack_candidates(inst).items():
            attack_stats[name]["attempts"] += 1
            attack_stats[name]["successes"] += int(verify(inst, candidate)[0])

        restart_rng = random.Random(seed ^ 0xA55A5AA5)
        restart_solved = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, restart_rng))[0]:
                restart_solved = True
                break
        attack_stats["random_restart_256"]["attempts"] += 1
        attack_stats["random_restart_256"]["successes"] += int(restart_solved)

        started = time.perf_counter()
        answer, metrics = _reference_dpll(inst)
        elapsed = time.perf_counter() - started
        solved = answer is not None and verify(inst, answer)[0]
        reference_successes += int(solved)
        reference_elapsed += elapsed
        reference_operations += metrics["operations"]
        reference_nodes += metrics["nodes"]
        reference_instances.append(
            {
                "seed": seed,
                "constraints": len(inst["constraints"]),
                "nodes": metrics["nodes"],
                "operations": metrics["operations"],
                "wall_clock_sec": round(elapsed, 6),
                "solved": solved,
            }
        )

    all_attacks_failed = all(item["successes"] == 0 for item in attack_stats.values())
    reference = {
        "name": "balanced NAE-3-SAT DPLL with unit and cardinality propagation",
        "complexity": "O(2^|U| * |F|) worst-case exact; paper Theorem 1 gives r^2*d^(k*r)*|U|^O(1)",
        "wall_clock_sec": round(reference_elapsed, 6),
        "mean_wall_clock_sec": round(reference_elapsed / 8, 6),
        "operations": reference_operations,
        "mean_operations": reference_operations // 8,
        "nodes": reference_nodes,
        "mean_nodes": reference_nodes / 8,
        "solves": f"{reference_successes}/8, as expected",
        "instances": reference_instances,
    }
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    report["G5_density_and_baseline"] = {
        "pass": sample_total >= 200_000 and reference_successes == 8,
        "shipping_sampled_solution_hits": sample_hits,
        "shipping_sampled_solution_total": sample_total,
        "shipping_sampled_solution_fraction": empirical,
        "strongest_attack_wall_sec": round(reference_elapsed, 6),
        "strongest_attack_operations": reference_operations,
        "strongest_attack_nodes": reference_nodes,
        "strongest_attack_solved_instances": reference_successes,
        "demo_exact_valid_certificate_count": enumerate_all(demo),
        "demo_candidate_space": search_space(demo),
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed,
        "attacks": attack_stats,
        "reference_algorithm": reference,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    doubled_params = {
        "n": shipping_params["n"] * 2,
        "orbit_count": shipping_params["orbit_count"],
    }
    doubled = make_instance(seed=314159, **doubled_params)
    base = make_instance(seed=314159, **shipping_params)
    report["G7_scales"] = {
        "pass": verify(doubled, doubled["answer"])[0]
        and len(doubled["universe"]) > len(base["universe"])
        and search_space(doubled) > search_space(base),
        "base_n_parameter": shipping_params["n"],
        "base_universe_size": len(base["universe"]),
        "doubled_n_parameter": doubled_params["n"],
        "doubled_universe_size": len(doubled["universe"]),
        "base_candidate_space": search_space(base),
        "doubled_candidate_space": search_space(doubled),
        "doubled_planted_verifies": verify(doubled, doubled["answer"])[0],
    }

    invariance_checks = 0
    carried_checks = 0
    keys = set()
    g8_ok = True
    for offset in range(20):
        inst = make_instance(
            seed=90000 + offset, **DIFFICULTY[SHIPPING_DIFFICULTY]
        )
        key = canonical_key(inst)
        keys.add(key)
        rng = random.Random(70000 + offset)
        shuffled = list(inst["universe"])
        rng.shuffle(shuffled)
        permutation = dict(zip(inst["universe"], shuffled))
        identity = {x: x for x in inst["universe"]}
        variants = [
            _relabel(inst, identity, reverse_edges=True),
            _relabel(inst, permutation, reverse_edges=False),
            _relabel(inst, permutation, reverse_edges=True),
        ]
        for variant in variants:
            invariance_checks += 1
            if canonical_key(variant) != key:
                g8_ok = False
            carried_checks += 1
            if not verify(variant, variant["answer"])[0]:
                g8_ok = False
    report["G8_canonical_key"] = {
        "pass": g8_ok and len(keys) == 20,
        "invariance_checks": invariance_checks,
        "carried_certificate_checks": carried_checks,
        "unrelated_distinct_keys": len(keys),
        "unrelated_instances": 20,
        "symmetries_tested": [
            "constraint-list reversal",
            "arbitrary universe relabelling",
            "composition of relabelling and reversal",
        ],
        "key_scope": "multiset of vertex link signatures and pair codegrees; not a complete isomorphism canonical form",
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_elements = _atomic_elements(shipping["answer"])
    answer_tokens = math.ceil(answer_chars / 4)
    intended_operations = 3 * len(shipping["universe"]) // 2
    hinted = _G9_ARMS["hinted"]
    placebo = _G9_ARMS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300,
        "arms": _G9_ARMS,
        "diagnostic_complete": all(arm["attempts"] >= 3 for arm in _G9_ARMS.values()),
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": (
            "hardened"
            if hinted["attempts"] >= 3 and hinted["solved"] == 0
            else "too_easy"
            if hinted["attempts"] >= 3
            else "diagnostic_pending"
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gate_values = [
        value
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict) and "pass" in value
    ]
    report["all_passed"] = all(value["pass"] for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
