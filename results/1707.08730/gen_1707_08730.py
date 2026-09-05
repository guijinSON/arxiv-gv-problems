"""Verified fixed-cardinality subset-sum generator for arXiv:1707.08730."""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import os
import random
import re
import statistics
import time


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "Modulo 997, the six desired weights occupy one common residue class."
)
PLACEBO_HINT: str = (
    "Across the list, the six desired weights require careful exact arithmetic."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite list of positive integers",
        "integer target",
        "fixed-cardinality subset",
    ],
    "verification_operations": [
        "index range and distinctness checks",
        "exact integer addition",
        "exact integer equality",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize that the six selected weights share a hidden residue class; "
        "without that invariant, generic meet-in-the-middle 6SUM enumerates triples."
    ),
    "hardness_basis": (
        "Track B: standard meet-in-the-middle 6SUM is Theta(n^3) time and memory "
        "and measured 2,040,862 operations/0.527 seconds at shipping n=150; an O(B*n) "
        "construction-aware scan through moduli 7..1000 measured 101,305 operations/"
        "0.0037 seconds, while recognizing modulus 997 cuts the route to 158 operations, "
        "but a no-tool solver must discover it and reduce 150 66-bit integers."
    ),
    "max_answer_tokens": 7,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"]
    + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 12, "k": 6, "modulus": 997, "quotient_bits": 5},
    "easy": {"n": 150, "k": 6, "modulus": 997, "quotient_bits": 56},
    "medium": {"n": 210, "k": 6, "modulus": 997, "quotient_bits": 72},
    "hard": {"n": 270, "k": 6, "modulus": 997, "quotient_bits": 88},
}
SHIPPING_DIFFICULTY: str = "easy"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A strictly increasing list of exactly six distinct 0-based indices, "
        "each between 0 and n-1 inclusive."
    ),
    "bounds": {
        "atomic_elements": 6,
        "index_lower_bound": 0,
        "index_upper_bound": "n-1",
    },
}

NOTES: str = (
    "Section I fixes subset-sum as selecting integer elements whose sum equals W, "
    "and Section III represents the selected subset by the computational-basis "
    "index paired with its sum. Section I also explicitly gives exhaustive search "
    "and O(nW) dynamic programming and quotes a quantum-walk cost polynomial in n "
    "when the subset size is fixed; consequently a six-element family cannot make "
    "an honest Track A claim. Sections III-IV give only a conditional quantum "
    "heuristic under Assumptions 1 and 2, not a classically checkable shortcut. "
    "The generator inverse-plants one uniformly selected six-item residue bucket; "
    "every planted and decoy bucket is sampled identically. Generic 6SUM is solved "
    "by the disclosed triple meet-in-the-middle reference algorithm, and an exhaustive "
    "small-modulus scan records the faster construction-aware mechanical route. "
    "Magnitude outliers, descending greedy selection, random restarts, and a visible-"
    "decimal-suffix ansatz are measured separately and fail at the shipping preset."
)


# Replaced after the corresponding scripts/harden.py runs have produced transcripts.
# The three arms are diagnostics under the current contract; only the size and
# intended-route limits gate G9.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 2, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "too_easy_at_shipping",
}


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


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a k-subset sum by planting one exchangeable residue bucket."""
    k = params.pop("k", 6)
    modulus = params.pop("modulus", 997)
    quotient_bits = params.pop("quotient_bits", 56)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    integers = (n, k, modulus, quotient_bits)
    if any(isinstance(x, bool) or not isinstance(x, int) for x in integers):
        raise TypeError("n, k, modulus, and quotient_bits must be integers")
    if k < 2 or k % 2:
        raise ValueError("k must be an even integer at least 2")
    if n < 2 * k or n % k:
        raise ValueError("n must be a multiple of k and at least 2k")
    if not _is_prime(modulus) or modulus <= n // k or modulus <= k:
        raise ValueError("modulus must be prime and exceed both k and n/k")
    if quotient_bits < 5:
        raise ValueError("quotient_bits must be at least 5")

    rng = random.Random(seed)
    bucket_count = n // k
    residues = rng.sample(range(modulus), bucket_count)
    planted_bucket = rng.randrange(bucket_count)
    low = 1 << (quotient_bits - 1)
    high = 1 << quotient_bits

    tagged_weights = []
    for bucket, residue in enumerate(residues):
        # Sampling without replacement makes the input a set even within a bucket.
        quotients = set()
        while len(quotients) < k:
            quotients.add(rng.randrange(low, high))
        for quotient in sorted(quotients):
            tagged_weights.append((modulus * quotient + residue, bucket))
    rng.shuffle(tagged_weights)

    weights = [weight for weight, _ in tagged_weights]
    answer = sorted(
        index
        for index, (_, bucket) in enumerate(tagged_weights)
        if bucket == planted_bucket
    )
    target = sum(weights[index] for index in answer)
    return {
        "family": "exact fixed-cardinality subset sum",
        "n": n,
        "k": k,
        "weights": weights,
        "target": target,
        "answer": answer,
    }


def _answer_text(answer) -> str:
    return ", ".join(str(value) for value in answer)


def render(inst) -> str:
    entries = [f"{index}:{weight}" for index, weight in enumerate(inst["weights"])]
    lines = ["  " + "  ".join(entries[start : start + 5]) for start in range(0, len(entries), 5)]
    statement = f"""EXACT {inst['k']}-ELEMENT SUBSET SUM

You are given {inst['n']} positive integers called weights and the positive integer
target T={inst['target']}. Find exactly {inst['k']} distinct weights whose sum is
exactly T. A weight is selected by its 0-based index shown before the colon.

Return exactly {inst['k']} distinct indices in strictly increasing order. Indices
range from 0 through {inst['n'] - 1}, inclusive; repeated indices are forbidden and
the order of addition does not matter. All arithmetic is ordinary exact integer
arithmetic, with no modular interpretation in the definition of a valid answer.

Weights (index:value):
{chr(10).join(lines)}

Give your final answer inside <answer></answer> tags, as exactly {inst['k']}
comma-separated base-10 indices with no brackets.
Example format: <answer>{', '.join(str(i) for i in range(inst['k']))}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    try:
        matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", str(text), re.I | re.S)
        if not matches:
            return None
        body = matches[-1].strip()
        for fence in ("~~~", chr(96) * 3):
            if body.startswith(fence) and body.endswith(fence):
                body = re.sub("^" + re.escape(fence) + r"[^\n]*\n?", "", body)
                body = re.sub(r"\n?" + re.escape(fence) + "$", "", body).strip()
        if body.startswith("[") and body.endswith("]"):
            body = body[1:-1].strip()
        if not body:
            return []
        pieces = [piece.strip() for piece in body.split(",")]
        if any(not re.fullmatch(r"[+-]?\d+", piece) for piece in pieces):
            return None
        return [int(piece) for piece in pieces]
    except Exception:
        return None


def verify(inst, answer) -> tuple[bool, str]:
    if answer is None:
        return False, "answer is absent"
    if not isinstance(answer, list):
        return False, "answer must be a list of indices"
    if not answer:
        return False, "answer is empty"
    k = inst["k"]
    if len(answer) < k:
        return False, f"answer has fewer than {k} indices"
    if len(answer) > k:
        return False, f"answer has more than {k} indices"
    if any(isinstance(index, bool) or not isinstance(index, int) for index in answer):
        return False, "every index must be an integer"
    if len(set(answer)) != len(answer):
        return False, "indices must be distinct"
    if any(answer[i] >= answer[i + 1] for i in range(len(answer) - 1)):
        return False, "indices must be strictly increasing"
    if answer[0] < 0 or answer[-1] >= inst["n"]:
        return False, "an index is outside the allowed range"
    total = sum(inst["weights"][index] for index in answer)
    if total != inst["target"]:
        return False, "selected weights do not sum to the target"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniformly sample the stated fixed-cardinality certificate language."""
    return sorted(rng.sample(range(inst["n"]), inst["k"]))


def search_space(inst) -> int | None:
    return math.comb(inst["n"], inst["k"])


def enumerate_all(inst) -> int | None:
    if search_space(inst) > 1_000_000:
        return None
    count = 0
    weights = inst["weights"]
    target = inst["target"]
    for candidate in itertools.combinations(range(inst["n"]), inst["k"]):
        if sum(weights[index] for index in candidate) == target:
            count += 1
    return count


def _normal_form(inst):
    """Normalize reorderings and every integral affine/reflection symmetry."""
    weights = inst["weights"]
    k = inst["k"]
    low = min(weights)
    high = max(weights)

    forward_weights = [weight - low for weight in weights]
    forward_target = inst["target"] - k * low
    reflected_weights = [high - weight for weight in weights]
    reflected_target = k * high - inst["target"]

    scale = 0
    for value in forward_weights + [forward_target]:
        scale = math.gcd(scale, abs(value))
    if scale == 0:
        scale = 1

    forward = (
        forward_target // scale,
        tuple(sorted(value // scale for value in forward_weights)),
    )
    reflected = (
        reflected_target // scale,
        tuple(sorted(value // scale for value in reflected_weights)),
    )
    return min(forward, reflected)


def canonical_key(inst) -> str:
    normalized_target, normalized_weights = _normal_form(inst)
    payload = [
        "fixed-cardinality-subset-sum",
        inst["n"],
        inst["k"],
        normalized_target,
        list(normalized_weights),
    ]
    raw = json.dumps(payload, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def escalate(params) -> dict | str | None:
    out = dict(params)
    n = int(out["n"])
    k = int(out.get("k", 6))
    quotient_bits = int(out.get("quotient_bits", 56))
    if n < 270:
        out["n"] = min(270, n + 60)
        if out["n"] % k:
            out["n"] += k - out["n"] % k
    else:
        # The witness remains six indices; only the coefficient entropy grows.
        out["quotient_bits"] = quotient_bits + 32
    return out


def _compact_residue_solver(inst, modulus: int):
    """Construction-aware route, disclosed for Track B measurement."""
    inverse_k = pow(inst["k"], -1, modulus)
    wanted = (inst["target"] % modulus) * inverse_k % modulus
    candidate = [
        index for index, weight in enumerate(inst["weights"]) if weight % modulus == wanted
    ]
    candidate.sort()
    operations = inst["n"] + inst["k"] + 2
    return candidate, {
        "operations": operations,
        "operation_definition": (
            "n+1 modular reductions, one modular inverse, one multiplication, "
            "and k-1 exact additions for final checking"
        ),
    }


def _discover_residue_solver(inst, max_modulus=1000):
    """Construction-aware mechanical attack: try every invertible small modulus."""
    operations = 0
    moduli_tried = 0
    k = inst["k"]
    for modulus in range(k + 1, max_modulus + 1):
        operations += 1  # gcd test
        if math.gcd(k, modulus) != 1:
            continue
        moduli_tried += 1
        wanted = (inst["target"] % modulus) * pow(k, -1, modulus) % modulus
        operations += 3  # target reduction, inverse, multiply-and-reduce
        candidate = []
        for index, weight in enumerate(inst["weights"]):
            operations += 2  # remainder and comparison
            if weight % modulus == wanted:
                candidate.append(index)
        if len(candidate) == k:
            operations += k + 1  # exact additions and target comparison
            candidate.sort()
            if verify(inst, candidate)[0]:
                return candidate, {
                    "operations": operations,
                    "moduli_tried": moduli_tried,
                    "found_modulus": modulus,
                }
    return None, {
        "operations": operations,
        "moduli_tried": moduli_tried,
        "found_modulus": None,
    }


def _store_sum(table, total, indices):
    previous = table.get(total)
    if previous is None:
        table[total] = indices
    elif isinstance(previous, tuple):
        table[total] = [previous, indices]
    else:
        previous.append(indices)


def _sum_entries(value):
    if value is None:
        return ()
    if isinstance(value, tuple):
        return (value,)
    return value


def _reference_meet_in_middle(inst):
    """Complete meet-in-the-middle for even k, specialized to the shipping k=6."""
    k = inst["k"]
    if k % 2:
        return None, {"operations": 0, "half_subsets": 0}
    half = k // 2
    weights = inst["weights"]
    table = {}
    operations = 0
    half_subsets = 0
    for indices in itertools.combinations(range(inst["n"]), half):
        total = sum(weights[index] for index in indices)
        operations += half - 1
        _store_sum(table, total, indices)
        operations += 1
        half_subsets += 1
    for indices in itertools.combinations(range(inst["n"]), half):
        total = sum(weights[index] for index in indices)
        complement = inst["target"] - total
        operations += half
        for other in _sum_entries(table.get(complement)):
            operations += 1
            if set(indices).isdisjoint(other):
                candidate = sorted(indices + other)
                if verify(inst, candidate)[0]:
                    return candidate, {
                        "operations": operations,
                        "half_subsets": half_subsets,
                        "stored_sums": len(table),
                    }
    return None, {
        "operations": operations,
        "half_subsets": half_subsets,
        "stored_sums": len(table),
    }


def _attack_magnitude_outlier(inst):
    k = inst["k"]
    indices = sorted(
        range(inst["n"]), key=lambda index: abs(k * inst["weights"][index] - inst["target"])
    )[:k]
    return sorted(indices)


def _attack_descending_greedy(inst):
    chosen = []
    remaining = inst["target"]
    ordered = sorted(range(inst["n"]), key=lambda i: inst["weights"][i], reverse=True)
    for index in ordered:
        if len(chosen) == inst["k"]:
            break
        if inst["weights"][index] <= remaining:
            chosen.append(index)
            remaining -= inst["weights"][index]
    if len(chosen) < inst["k"]:
        for index in ordered:
            if index not in chosen:
                chosen.append(index)
                if len(chosen) == inst["k"]:
                    break
    return sorted(chosen)


def _attack_random_restart(inst, rng, restarts=4096):
    last = random_candidate(inst, rng)
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last
    return last


def _attack_visible_suffix(inst):
    """By-hand ansatz: mistake an ordinary decimal suffix for the hidden class."""
    buckets = {digit: [] for digit in range(10)}
    for index, weight in enumerate(inst["weights"]):
        buckets[weight % 10].append(index)
    usable = [indices for indices in buckets.values() if len(indices) >= inst["k"]]
    if not usable:
        return list(range(inst["k"]))
    best = min(
        usable,
        key=lambda indices: abs(
            sum(inst["weights"][index] for index in indices[: inst["k"]]) - inst["target"]
        ),
    )
    return sorted(best[: inst["k"]])


def _transform_instance(inst, permutation=None, scale=1, shift=0, reflect=False):
    out = copy.deepcopy(inst)
    n = inst["n"]
    if permutation is None:
        permutation = list(range(n))
    weights = inst["weights"]
    target = inst["target"]
    if reflect:
        center = min(weights) + max(weights) + 1
        weights = [center - weight for weight in weights]
        target = inst["k"] * center - target
    out["weights"] = [scale * weights[old] + shift for old in permutation]
    out["target"] = scale * target + inst["k"] * shift
    planted = set(inst["answer"])
    out["answer"] = sorted(new for new, old in enumerate(permutation) if old in planted)
    return out


def _answer_size(answer):
    encoded = json.dumps(answer, separators=(",", ":"))
    return {
        "chars": len(encoded),
        "tokens": math.ceil(len(encoded) / 4),
        "elements": len(answer),
    }


def selftest():
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    g1_attempts = 0
    g1_failures = []
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            instance = make_instance(seed=seed, **params)
            ok, reason = verify(instance, instance["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, reason])
            if json.loads(json.dumps(instance["answer"])) == instance["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not g1_failures and json_roundtrips == g1_attempts,
        "attempts": g1_attempts,
        "json_roundtrips": json_roundtrips,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=90210, **ship_params)
    answer = inst["answer"]
    duplicate = answer[:]
    duplicate[-1] = duplicate[0]
    out_of_range = answer[:]
    out_of_range[-1] = inst["n"]
    replacement = next(index for index in range(inst["n"]) if index not in set(answer))
    swapped = sorted([replacement] + answer[1:])
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
    }

    realistic = (
        "I checked the six selected values with exact arithmetic.\n\n"
        "```text\n<answer>" + _answer_text(answer) + "</answer>\n```"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("there is no tagged answer") is None,
        "parsed": parsed,
        "garbage_returns_none": parse_answer("there is no tagged answer") is None,
    }

    samples = 200_000
    guess_rng = random.Random(0x170708730)
    hits = 0
    for _ in range(samples):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "structure_aware_space": search_space(inst),
        "sampler": "uniform over all increasing six-subsets; shape, size, distinctness, and order are enforced",
    }

    baseline_start = time.perf_counter()
    baseline_answer, baseline_stats = _reference_meet_in_middle(inst)
    baseline_wall = time.perf_counter() - baseline_start
    discovery_start = time.perf_counter()
    discovery_answer, discovery_stats = _discover_residue_solver(inst)
    discovery_wall = time.perf_counter() - discovery_start
    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": hits / samples < 1e-6
        and demo_count is not None
        and baseline_answer is not None
        and verify(inst, baseline_answer)[0]
        and discovery_answer is not None
        and verify(inst, discovery_answer)[0],
        "shipping_valid_hits": hits,
        "shipping_density_samples": samples,
        "shipping_observed_solution_fraction": hits / samples,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_wall_seconds": round(baseline_wall, 6),
        "baseline_operations": baseline_stats["operations"],
        "baseline_half_subsets": baseline_stats["half_subsets"],
        "strongest_attack": "construction-aware exhaustive modulus scan through 1000",
        "strongest_attack_wall_seconds": round(discovery_wall, 6),
        "strongest_attack_operations": discovery_stats["operations"],
        "strongest_attack_found_modulus": discovery_stats["found_modulus"],
    }

    attack_results = {
        "outlier_closest_to_target_mean": {"successes": 0, "attempts": 0},
        "greedy_largest_not_exceeding_residual": {"successes": 0, "attempts": 0},
        "random_restart_4096_six_subsets": {"successes": 0, "attempts": 0},
        "in_context_equal_decimal_suffix": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_times = []
    reference_operations = []
    reference_half_subsets = []
    discovery_successes = 0
    discovery_times = []
    discovery_operations = []
    discovery_moduli = []
    compact_successes = 0
    compact_times = []
    compact_operations = []
    for seed in range(3100, 3108):
        attacked = make_instance(seed=seed, **ship_params)
        candidates = {
            "outlier_closest_to_target_mean": _attack_magnitude_outlier(attacked),
            "greedy_largest_not_exceeding_residual": _attack_descending_greedy(attacked),
            "random_restart_4096_six_subsets": _attack_random_restart(
                attacked, random.Random(seed ^ 0xA5A5), restarts=4096
            ),
            "in_context_equal_decimal_suffix": _attack_visible_suffix(attacked),
        }
        for name, candidate in candidates.items():
            attack_results[name]["attempts"] += 1
            if verify(attacked, candidate)[0]:
                attack_results[name]["successes"] += 1

        start = time.perf_counter()
        reference_answer, stats = _reference_meet_in_middle(attacked)
        reference_times.append(time.perf_counter() - start)
        reference_operations.append(stats["operations"])
        reference_half_subsets.append(stats["half_subsets"])
        if reference_answer is not None and verify(attacked, reference_answer)[0]:
            reference_successes += 1

        start = time.perf_counter()
        discovery_answer, discovery_stats = _discover_residue_solver(attacked)
        discovery_times.append(time.perf_counter() - start)
        discovery_operations.append(discovery_stats["operations"])
        discovery_moduli.append(discovery_stats["found_modulus"])
        if discovery_answer is not None and verify(attacked, discovery_answer)[0]:
            discovery_successes += 1

        start = time.perf_counter()
        compact_answer, compact_stats = _compact_residue_solver(
            attacked, ship_params["modulus"]
        )
        compact_times.append(time.perf_counter() - start)
        compact_operations.append(compact_stats["operations"])
        if verify(attacked, compact_answer)[0]:
            compact_successes += 1

    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed
        and reference_successes == 8
        and discovery_successes == 8
        and compact_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "exact meet-in-the-middle 6SUM using two triple-sum passes",
            "complexity": "Theta(n^3) exact additions, hash operations, and memory for fixed k=6",
            "median_wall_clock_sec": round(statistics.median(reference_times), 6),
            "operations": int(statistics.median(reference_operations)),
            "median_operations": int(statistics.median(reference_operations)),
            "median_half_subsets": int(statistics.median(reference_half_subsets)),
            "operation_definition": "integer additions/subtractions, hash insertions/lookups, and collision checks",
            "solves": f"{reference_successes}/8, as expected",
        },
        "construction_aware_reference": {
            "name": "exhaustive invertible-modulus scan through 1000",
            "complexity": "O(B*n) modular reductions and comparisons for bound B=1000",
            "median_wall_clock_sec": round(statistics.median(discovery_times), 6),
            "operations": int(statistics.median(discovery_operations)),
            "operation_definition": (
                "gcd tests plus target/weight remainders, comparisons, modular inverses, "
                "and exact verification"
            ),
            "found_moduli": discovery_moduli,
            "solves": f"{discovery_successes}/8, as expected",
        },
        "compact_route": {
            "name": "common residue-class invariant modulo 997",
            "complexity": "Theta(n) modular reductions after recognizing the invariant",
            "median_wall_clock_sec": round(statistics.median(compact_times), 8),
            "operations": int(statistics.median(compact_operations)),
            "operation_definition": (
                "n+1 modular reductions, one inverse, one multiplication, and k-1 exact additions"
            ),
            "solves": f"{compact_successes}/8, as expected",
        },
    }

    doubled_n = 2 * ship_params["n"]
    doubled = make_instance(
        n=doubled_n,
        k=ship_params["k"],
        modulus=ship_params["modulus"],
        quotient_bits=ship_params["quotient_bits"],
        seed=77,
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] > inst["n"]
        and search_space(doubled) > search_space(inst),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "shipping_search_space": search_space(inst),
        "doubled_search_space": search_space(doubled),
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = 0
    witness_checks = 0
    invariant_failures = []
    distinct_keys = []
    for seed in range(20):
        original = make_instance(seed=7000 + seed, **ship_params)
        original_key = canonical_key(original)
        distinct_keys.append(original_key)
        rng = random.Random(8000 + seed)
        permutation = list(range(original["n"]))
        rng.shuffle(permutation)
        variants = [
            _transform_instance(original, permutation=permutation),
            _transform_instance(original, scale=7, shift=12345),
            _transform_instance(original, reflect=True),
            _transform_instance(
                original,
                permutation=list(reversed(permutation)),
                scale=5,
                shift=6789,
                reflect=True,
            ),
        ]
        for variant in variants:
            invariance_checks += 1
            if canonical_key(variant) != original_key:
                invariant_failures.append([seed, "key changed"])
            witness_checks += 1
            if not verify(variant, variant["answer"])[0]:
                invariant_failures.append([seed, "carried witness failed"])
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and len(set(distinct_keys)) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": witness_checks,
        "distinct_unrelated_keys": len(set(distinct_keys)),
        "unrelated_instances": 20,
        "failures": invariant_failures,
        "symmetries": "input reorderings, positive integral affine maps, reflections, and their compositions",
        "key_basis": "normalized sorted weights and target modulo affine/reflection symmetry; never seed or rendering",
    }

    # Exact worst-case serialization within the shipping certificate language:
    # the six largest legal indices maximize the decimal width.
    size = _answer_size(list(range(inst["n"] - inst["k"], inst["n"])))
    arms = copy.deepcopy(G9_RESULTS["arms"])
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else None
    placebo_rate = (
        arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else None
    )
    intended_operations = ship_params["n"] + ship_params["k"] + 2
    within_caps = (
        size["chars"] <= 2000
        and size["elements"] <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": size["chars"],
        "answer_tokens": size["tokens"],
        "answer_elements": size["elements"],
        "intended_route_operations": intended_operations,
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
