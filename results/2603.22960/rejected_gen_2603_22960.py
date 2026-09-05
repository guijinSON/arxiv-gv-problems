"""Retained, rejected Track-B experiment for arXiv:2603.22960.

The task uses the affine-hyperplane designs in Section 3 of Chen--Hua--Li--Wu.
For each succinct design record, the solver returns the positive intersection
number of two distinct intersecting blocks.  Section 2, Lemma 2.4 supplies that
number by an exact residual-design identity.  Instances are constructed from
prime fields; no generated instance is searched for its answer.

This draft is intentionally not shippable.  The audit in REJECTED.md found the
direct affine identity c = k*k/v, which solves all 32 shipping records in 64
exact operations.  The earlier all-block-pairs baseline was not the standard
algorithm for the promised input distribution, so the family fails H.
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
from typing import Any


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "affine hyperplane block designs over prime fields",
        "BIBD parameter records",
        "positive block-intersection polynomial",
    ],
    "verification_operations": [
        "exact integer multiplication",
        "exact integer divisibility",
        "exact polynomial coefficient comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "At a fixed point, the incident blocks against the remaining points form "
        "a residual 2-design, so one double count replaces explicit block-pair "
        "intersection scans."
    ),
    "hardness_basis": (
        "Track B: Section 2, Lemma 2.3 gives an O(m) exact parameter algorithm "
        "using 6m=192 integer operations for m=32 shipping records (measured "
        "wall-clock is refreshed in selftest_report.json); even the smallest "
        "allowed shipping design has 16,777,214 blocks, so a definition-level "
        "all-pairs incidence scan starts above 140 trillion block pairs, while "
        "the compact residual-design route stays within 192 operations once its "
        "decomposition is recognized."
    ),
    "max_answer_tokens": 420,
}

NATIVE: dict = {
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

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A dense polynomial P(x)=sum_j c_j*x^j with one term for every displayed "
        "record j.  JSON terms are [[[c_j,1],[j]],...].  Every denominator is 1 "
        "and every numerator is an integer in 1..k_j-1, where k_j is that "
        "record's block size.  Terms occur in increasing exponent order."
    ),
    "bounds": {
        "terms": "number of displayed records",
        "variables": 1,
        "degree": "record_count-1",
        "coefficient_denominator": 1,
        "coefficient_numerator": "1..k_j-1 for term j",
        "atomic_elements": "3*record_count",
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 4, "count": 4, "q_max": 3, "dimension_span": 2},
    "easy": {"n": 12, "count": 24, "q_max": 7, "dimension_span": 6},
    "medium": {"n": 20, "count": 28, "q_max": 11, "dimension_span": 7},
    "hard": {"n": 30, "count": 32, "q_max": 13, "dimension_span": 8},
}

SHIPPING_DIFFICULTY: str = "hard"

STRUCTURAL_HINT: str = (
    "Fixing a point turns its incident blocks and all other points into a "
    "residual 2-design with inherited constant degrees."
)
PLACEBO_HINT: str = (
    "Keeping the record indices aligned with the requested coefficients avoids "
    "small but consequential transcription mistakes."
)

# Populated after the three isolated harden.py runs.  These are diagnostics only;
# selftest deliberately records zero attempts until real transcripts exist.
G9_RESULTS: dict = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}

NOTES: str = (
    "Section 1 fixes the exact simple, non-trivial BIBD and local "
    "2-homogeneity definitions.  Section 3, Example AG(2) constructs "
    "AG_{d-1}(d,q) and proves that ASL_d(q) is locally 2-transitive, so every "
    "sampled prime-field record is certified by construction.  Section 2, "
    "Lemma 2.3 is the answer identity: for a non-symmetric locally "
    "2-homogeneous design the two block intersections are 0 and "
    "c=(k-1)(lambda-1)/(r-1)+1.  Theorem 1.1 and Section 3 also make clear that "
    "these infinite families are explicit, so this is Track B rather than a "
    "false Track-A claim.  Records are sampled without replacement and shuffled. "
    "The adversary panel rejects the line-design constant, the symmetric-design "
    "intersection, a gcd guess, a square-root dimension guess, and uniform random "
    "restart; the successful Lemma 2.3 formula is reported separately as the "
    "reference algorithm."
)


_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31)


def _require_int(name: str, value: object, low: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < low:
        raise ValueError(f"{name} must be an integer at least {low}")
    return value


def _record(q: int, d: int) -> dict[str, int]:
    """Parameters of AG_{d-1}(d,q), Section 3, Example AG(2)."""
    v = q**d
    k = q ** (d - 1)
    return {
        "v": v,
        "b": q * (v - 1) // (q - 1),
        "r": (v - 1) // (q - 1),
        "k": k,
        "lambda": (k - 1) // (q - 1),
    }


def _intersection_from_record(record: dict[str, int]) -> int:
    """Lemma 2.3's positive block-intersection number."""
    numerator = (record["k"] - 1) * (record["lambda"] - 1)
    denominator = record["r"] - 1
    quotient, remainder = divmod(numerator, denominator)
    if remainder:
        raise ValueError("record violates the residual-design divisibility")
    return quotient + 1


def _answer_for_records(records: list[dict[str, int]]) -> list[list[Any]]:
    return [
        [[_intersection_from_record(record), 1], [j]]
        for j, record in enumerate(records)
    ]


def make_instance(
    n: int,
    seed: int = 0,
    count: int = 24,
    q_max: int = 7,
    dimension_span: int = 6,
    **params: Any,
) -> dict:
    """Construct certified affine-hyperplane records without solving them."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    n = _require_int("n", n, 3)
    count = _require_int("count", count, 1)
    q_max = _require_int("q_max", q_max, 2)
    dimension_span = _require_int("dimension_span", dimension_span, 1)

    primes = [q for q in _PRIMES if q <= q_max]
    if not primes:
        raise ValueError("q_max leaves no supported prime field")
    d_min = max(3, n - dimension_span + 1)
    choices = [(q, d) for q in primes for d in range(d_min, n + 1)]
    if count > len(choices):
        raise ValueError("count exceeds the distinct (prime, dimension) records")

    rng = random.Random(seed)
    selected = rng.sample(choices, count)
    rng.shuffle(selected)
    records = [_record(q, d) for q, d in selected]

    # Unique prime powers q^(d-2) make coefficient-swap corruptions unambiguous.
    certificates = [_intersection_from_record(record) for record in records]
    if len(set(certificates)) != len(certificates):
        raise AssertionError("construction unexpectedly produced duplicate certificates")

    return {
        "family": "affine_hyperplane_positive_intersections",
        "n": n,
        "record_count": count,
        "q_max": q_max,
        "dimension_span": dimension_span,
        "records": records,
        "answer": _answer_for_records(records),
    }


def render(inst: dict) -> str:
    records = inst["records"]
    lines = [
        "AFFINE-HYPERPLANE INTERSECTION POLYNOMIAL",
        "",
        "A 2-(v,k,lambda) block design consists of v points and b distinct",
        "blocks.  Every block contains exactly k points, every point belongs to",
        "exactly r blocks, and every pair of distinct points belongs to exactly",
        "lambda common blocks.",
        "",
        "The records below come from affine hyperplane designs.  For a hidden",
        "prime q and integer d>=3, the points are the vectors in F_q^d and the",
        "blocks are all affine hyperplanes {x : a dot x = t}, with nonzero a",
        "identified up to nonzero scalar multiplication.  Such a design is simple,",
        "non-trivial, non-symmetric, and locally 2-homogeneous: its affine special",
        "linear automorphism group fixes any point or block and is 2-homogeneous",
        "on the incident blocks or points, respectively.",
        "",
        "Two distinct affine hyperplanes are either disjoint or have the same",
        "positive number of common points.  For record j, call that positive",
        "intersection number c_j.  Determine the exact dense polynomial",
        "P(x)=sum_{j=0}^{m-1} c_j*x^j.  Record indices are 0-based.",
        "",
        "Each row is: j | v | b | r | k | lambda",
    ]
    for j, record in enumerate(records):
        lines.append(
            f"{j} | {record['v']} | {record['b']} | {record['r']} | "
            f"{record['k']} | {record['lambda']}"
        )
    lines.extend(
        [
            "",
            f"Output exactly {len(records)} coefficients in exponent order.",
            "Write every exact rational as num/den; here every denominator must be 1.",
            "Give your final answer inside <answer></answer> tags, as a comma-separated",
            "coefficient list c_0/1,c_1/1,...,c_(m-1)/1.",
            "Example: <answer>3/1,9/1,27/1</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].replace("`", "").strip()
    if not body:
        return None
    pieces = [piece.strip() for piece in body.split(",")]
    if not pieces or any(not piece for piece in pieces):
        return None
    answer: list[list[Any]] = []
    for j, piece in enumerate(pieces):
        match = re.fullmatch(r"([+-]?\d+)\s*/\s*([+-]?\d+)", piece)
        if match is None:
            return None
        numerator = int(match.group(1))
        denominator = int(match.group(2))
        if denominator == 0:
            return None
        if denominator < 0:
            numerator, denominator = -numerator, -denominator
        divisor = math.gcd(abs(numerator), denominator)
        answer.append([[numerator // divisor, denominator // divisor], [j]])
    return answer


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    records = inst["records"]
    if not isinstance(answer, list):
        return False, "answer must be a polynomial term list"
    if not answer:
        return False, "answer polynomial must not be empty"
    if len(answer) != len(records):
        return False, f"polynomial must contain exactly {len(records)} terms"

    for j, (term, record) in enumerate(zip(answer, records)):
        if not isinstance(term, list) or len(term) != 2:
            return False, f"term {j} must be [coefficient, exponent]"
        coefficient, exponent = term
        if exponent != [j]:
            return False, f"term {j} exponent must equal its 0-based position"
        if not isinstance(coefficient, list) or len(coefficient) != 2:
            return False, f"term {j} coefficient must be [numerator, denominator]"
        numerator, denominator = coefficient
        if (
            isinstance(numerator, bool)
            or isinstance(denominator, bool)
            or not isinstance(numerator, int)
            or not isinstance(denominator, int)
        ):
            return False, f"term {j} rational entries must be integers"
        if denominator != 1:
            return False, f"term {j} coefficient denominator must be 1"
        if numerator < 1 or numerator >= record["k"]:
            return False, f"term {j} numerator is outside 1..k_j-1"
        expected = _intersection_from_record(record)
        if numerator != expected:
            return False, f"term {j} is not the positive block-intersection number"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniform over the bounded, structure-aware coefficient language."""
    return [
        [[rng.randint(1, record["k"] - 1), 1], [j]]
        for j, record in enumerate(inst["records"])
    ]


def search_space(inst: dict) -> int | None:
    return math.prod(record["k"] - 1 for record in inst["records"])


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 100_000:
        return None
    ranges = [range(1, record["k"]) for record in inst["records"]]
    expected = tuple(_intersection_from_record(record) for record in inst["records"])
    return sum(tuple(candidate) == expected for candidate in itertools.product(*ranges))


def canonical_key(inst: dict) -> str:
    canonical = sorted(
        (
            record["v"],
            record["b"],
            record["r"],
            record["k"],
            record["lambda"],
        )
        for record in inst["records"]
    )
    payload = json.dumps(canonical, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    clean = {key: value for key, value in params.items() if key != "_preset"}
    n = int(clean.get("n", 3))
    count = int(clean.get("count", 24))
    q_max = int(clean.get("q_max", 7))
    next_n = n + 6
    # Fixed term count: only the ambient dimensions and coefficient entropy grow.
    max_digits = len(str(q_max ** (next_n - 2)))
    conservative_chars = count * (max_digits + 22) + 2
    if 3 * count > 256 or 6 * count > 300 or conservative_chars > 2000:
        return "cap_bound"
    harder = dict(clean)
    harder["n"] = next_n
    return harder


def _candidate_from_values(inst: dict, values: list[int]) -> list[list[Any]]:
    return [[ [int(value), 1], [j]] for j, value in enumerate(values)]


def _attack_candidates(inst: dict) -> dict[str, list[list[Any]]]:
    records = inst["records"]
    return {
        "outlier_constant_one": _candidate_from_values(inst, [1 for _ in records]),
        "greedy_copy_lambda": _candidate_from_values(
            inst, [record["lambda"] for record in records]
        ),
        "by_hand_gcd_k_lambda": _candidate_from_values(
            inst, [math.gcd(record["k"], record["lambda"]) for record in records]
        ),
        "by_hand_square_root_k": _candidate_from_values(
            inst, [math.isqrt(record["k"]) for record in records]
        ),
    }


def _reference_algorithm(inst: dict) -> list[list[Any]]:
    return _answer_for_records(inst["records"])


def _atom_count(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atom_count(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atom_count(item) for item in value)
    return 1


def _corruptions(answer: list[list[Any]]) -> dict[str, object]:
    dropped = json.loads(json.dumps(answer))
    dropped.pop()

    swapped = json.loads(json.dumps(answer))
    swapped[0][0], swapped[1][0] = swapped[1][0], swapped[0][0]

    duplicated = json.loads(json.dumps(answer))
    duplicated[-1][1] = list(duplicated[0][1])

    out_of_range = json.loads(json.dumps(answer))
    out_of_range[0][0][0] = 0

    return {
        "drop_one_term": dropped,
        "swap_two_coefficients": swapped,
        "duplicate_exponent": duplicated,
        "empty": [],
        "out_of_range_coefficient": out_of_range,
    }


def selftest() -> dict:
    report: dict[str, Any] = {
        "paper": "2603.22960",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    # G1: construction, exact verification, and JSON-native answers.
    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2, 17, 991):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            json_native = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            checks += 1
            if not ok or not json_native:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "failures": failures,
    }

    shipping = make_instance(seed=20260905, **DIFFICULTY[SHIPPING_DIFFICULTY])

    corruption_results = {}
    corruption_reasons = []
    for name, bad in _corruptions(shipping["answer"]).items():
        ok, reason = verify(shipping, bad)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        corruption_reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": (
            all(item["rejected"] for item in corruption_results.values())
            and len(set(corruption_reasons)) == len(corruption_reasons)
        ),
        "cases": corruption_results,
        "distinct_reasons": len(set(corruption_reasons)),
    }

    coefficients = ", ".join(
        f"{term[0][0]}/{term[0][1]}" for term in shipping["answer"]
    )
    realistic = (
        "The residual design gives the coefficients.\n```text\n"
        f"<answer>\n{coefficients}\n</answer>\n```\n"
        "The exponents are their displayed positions."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and parse_answer("garbage") is None,
        "realistic_response": parsed == shipping["answer"],
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4/G5: sample exactly from CERTIFICATE_LANGUAGE at the shipping preset.
    samples = 200_000
    hits = 0
    guess_rng = random.Random(260322960)
    density_start = time.perf_counter()
    for _ in range(samples):
        candidate = random_candidate(shipping, guess_rng)
        hits += int(verify(shipping, candidate)[0])
    density_wall = time.perf_counter() - density_start
    space = search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "structure_aware_space": space,
        "exact_unique_witness_probability": f"1/{space}",
        "sampler": "independent uniform c_j in the stated integer range 1..k_j-1",
    }

    # G6: four failing no-tool attacks plus a failing random restart.  The exact
    # Lemma 2.3 algorithm is expected to succeed and is therefore a sibling field.
    attack_names = list(_attack_candidates(shipping)) + ["random_restart_256"]
    attacks = {name: {"successes": 0, "attempts": 0} for name in attack_names}
    reference_solves = 0
    reference_repetitions = 2000
    reference_wall = 0.0
    random_restart_wall = 0.0
    random_restart_iterations = 0
    for seed in range(8100, 8108):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, candidate in _attack_candidates(inst).items():
            ok, _ = verify(inst, candidate)
            attacks[name]["successes"] += int(ok)
            attacks[name]["attempts"] += 1

        restart_rng = random.Random(seed ^ 0x260322960)
        start = time.perf_counter()
        solved = False
        for restart in range(256):
            ok, _ = verify(inst, random_candidate(inst, restart_rng))
            if ok:
                solved = True
                break
        random_restart_wall += time.perf_counter() - start
        random_restart_iterations += restart + 1
        attacks["random_restart_256"]["successes"] += int(solved)
        attacks["random_restart_256"]["attempts"] += 1

        start = time.perf_counter()
        for _ in range(reference_repetitions):
            reference = _reference_algorithm(inst)
        reference_wall += time.perf_counter() - start
        reference_solves += int(verify(inst, reference)[0])

    all_failed = all(
        item["successes"] == 0 and item["attempts"] >= 8
        for item in attacks.values()
    )
    reference_mean = reference_wall / (8 * reference_repetitions)
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Lemma 2.3 residual-design parameter identity",
            "complexity": "O(m) exact integer arithmetic for m records",
            "wall_clock_sec_total_benchmark": reference_wall,
            "timing_repetitions_per_instance": reference_repetitions,
            "wall_clock_sec_mean": reference_mean,
            "operations_per_shipping_instance": 6 * shipping["record_count"],
            "solves": f"{reference_solves}/8, as expected",
        },
    }

    block_pairs = sum(
        record["b"] * (record["b"] - 1) // 2 for record in shipping["records"]
    )
    report["G5_density_and_baseline_cost"] = {
        "pass": hits / samples < 1e-6 and all_failed and reference_solves == 8,
        "shipping_density": {
            "hits": hits,
            "total": samples,
            "observed_fraction": hits / samples,
            "exact_fraction_from_uniqueness": f"1/{space}",
            "sampling_wall_clock_sec": density_wall,
        },
        "strongest_failing_attack": {
            "name": "uniform random restart in the bounded coefficient language",
            "wall_clock_sec_total_8": random_restart_wall,
            "iterations": random_restart_iterations,
            "successes": attacks["random_restart_256"]["successes"],
        },
        "reference_baseline": {
            "name": "Lemma 2.3 exact parameter algorithm",
            "wall_clock_sec_mean": reference_mean,
            "operations": 6 * shipping["record_count"],
        },
        "definition_level_mechanical_route": {
            "algorithm": "enumerate unordered block pairs and count common points",
            "smallest_blocks_in_one_shipping_record": min(
                record["b"] for record in shipping["records"]
            ),
            "unordered_block_pairs_across_shipping_records": block_pairs,
            "pair_visits_lower_bound": block_pairs,
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=777, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > space,
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_space": space,
        "doubled_space": search_space(doubled),
        "answer_terms_unchanged": doubled["record_count"] == shipping["record_count"],
        "doubled_build_sec": doubled_build,
        "verify_reason": doubled_reason,
    }

    invariance_checks = 0
    preservation_checks = 0
    g8_failures = []
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(seed=9000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        original_key = canonical_key(inst)
        unrelated_keys.append(original_key)
        rng = random.Random(seed ^ 0xA661)
        random_order = list(range(inst["record_count"]))
        rng.shuffle(random_order)
        reverse_order = list(reversed(range(inst["record_count"])))
        for label, order in (("record_permutation", random_order), ("composition", reverse_order)):
            transformed = dict(inst)
            transformed["records"] = [inst["records"][index] for index in order]
            transformed["answer"] = _answer_for_records(transformed["records"])
            invariance_checks += 1
            preservation_checks += 1
            if canonical_key(transformed) != original_key:
                g8_failures.append({"seed": seed, "map": label, "failure": "key changed"})
            if not verify(transformed, transformed["answer"])[0]:
                g8_failures.append(
                    {"seed": seed, "map": label, "failure": "relabelled answer failed"}
                )
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariance_checks,
        "problem_preservation_checks": preservation_checks,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "failures": g8_failures,
        "canonicalization": "sort the five-parameter design records",
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_atoms = _atom_count(shipping["answer"])
    answer_tokens = (answer_chars + 3) // 4
    hinted_attempts = G9_RESULTS["hinted"]["attempts"]
    placebo_attempts = G9_RESULTS["placebo"]["attempts"]
    hinted_rate = (
        G9_RESULTS["hinted"]["solved"] / hinted_attempts if hinted_attempts else None
    )
    placebo_rate = (
        G9_RESULTS["placebo"]["solved"] / placebo_attempts if placebo_attempts else None
    )
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000 and answer_atoms <= 256 and 6 * shipping["record_count"] <= 300,
        "arms": G9_RESULTS,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": "diagnostic recorded" if hinted_attempts else "pending isolated run",
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "token_measure": "ceil(minified JSON characters / 4)",
        "answer_elements": answer_atoms,
        "intended_route_operations": 6 * shipping["record_count"],
    }

    gate_passes = [
        value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_passed"] = all(gate_passes)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
