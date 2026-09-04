"""Verified SSB factor-recovery generator for arXiv:2201.13153.

The instances use the paper's native objects: balanced semiprimes and exact
congruences modulo a prime escrow key.  The factors are sampled first, so the
certificate is known by inverse generation.  The checker only performs exact
integer operations and never reads the planted answer.
"""

from __future__ import annotations

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
    "Reduce N times the inverse of k modulo T to recover a factor residue by "
    "a square root, then use C to lift it through the quotient-sum quadratic."
)
PLACEBO_HINT: str = (
    "Keep every intermediate integer in its stated range and check each row "
    "carefully before committing to the final list."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "number_theory",
    "object_regime": "finite_discrete",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "balanced semiprimes",
        "prime escrow modulus",
        "multiplicative congruence between hidden prime factors",
    ],
    "verification_operations": [
        "exact integer range comparison",
        "exact divisibility",
        "exact integer multiplication",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Turn the modular correlation between the two factors into a square "
        "root for their residues, then lift those residues using the stated "
        "sum of quotient coefficients; without that change of variables one "
        "faces several unrelated balanced factorizations."
    ),
    "hardness_basis": (
        "Track B: the Section 4.2 SSB recovery specialized to the supplied k "
        "and quotient sum C uses O(n log T) exact arithmetic; selftest measures "
        "its shipping-preset wall-clock and operation count, while executing "
        "the modular square roots and lifts exactly is not realistic by hand."
    ),
    "max_answer_tokens": 16,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "easy": {"n": 3, "factor_bits": 24, "c": 5},
}
SHIPPING_DIFFICULTY: str = "easy"

_WHEEL_PRIMES = (2, 3, 5, 7, 11, 13)
_WHEEL = math.prod(_WHEEL_PRIMES)


def _build_wheel_prefix() -> tuple[int, ...]:
    count = 0
    prefix = []
    for value in range(_WHEEL):
        count += math.gcd(value, _WHEEL) == 1
        prefix.append(count)
    return tuple(prefix)


_WHEEL_PREFIX = _build_wheel_prefix()

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON list of exactly n decimal integers.  Entry i is an alpha-bit "
        "candidate for the smaller factor of row i and is coprime to "
        "2*3*5*7*11*13.  The finite language contains every candidate a basic "
        "small-prime sieve leaves."
    ),
    "bounds": {
        "min_entries": 1,
        "max_entries": 32,
        "max_factor_bits": 62,
        "wheel": _WHEEL,
    },
}

NOTES: str = (
    "Section 4.1 fixes SSB's exact condition H0, p congruent to k*q modulo a "
    "large prime T, and its inverse prime-generation route. Section 4.2 gives "
    "the executable recovery: obtain q squared modulo T, take its square roots, "
    "and solve for the high-level quotient coefficients. Section 4.3 is the "
    "STEP 0 disqualifier for Track A: recovery is O(K*(alpha+c)^3*2^(2c)) and "
    "O(alpha^4) in the recommended regime. This Track B subfamily supplies k "
    "and C=floor(p/T)+floor(q/T), removing the paper's two short exhaustive "
    "loops but retaining its modular-square-root and lifting identities. Each "
    "preset composes independent SSB rows. Factors are sampled before N is "
    "formed, and all primality decisions are deterministic below 2^64. The "
    "generator rejects close factors so bounded Fermat search fails; small-prime "
    "trial division, nearest-square, no-wrap, residue-as-factor, and random "
    "candidate attacks are measured separately from the successful Track B "
    "reference algorithm."
)

# Filled after the script-owned hardening runs.  Until then G9 intentionally
# fails: an unevaluated oracle claim must never look like evidence.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "pending",
}


def _is_prime(value: int) -> bool:
    """Deterministic Miller--Rabin for unsigned 64-bit integers."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value % prime == 0:
            return value == prime
    if value >= 1 << 64:
        raise ValueError("exact primality routine is limited to values below 2^64")
    d = value - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    # This seven-base set is deterministic for n < 2^64.
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        a = base % value
        if a == 0:
            continue
        x = pow(a, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _random_prime(bits: int, rng: random.Random, residue4: int | None = None) -> int:
    if not 5 <= bits <= 62:
        raise ValueError("prime bit length must be between 5 and 62")
    low, high = 1 << (bits - 1), 1 << bits
    for _ in range(200000):
        candidate = rng.randrange(low, high) | 1
        if residue4 is not None:
            candidate += (residue4 - candidate) % 4
            if candidate >= high:
                continue
        if _is_prime(candidate):
            return candidate
    raise RuntimeError("deterministic prime sampling budget exhausted")


def _ceil_sqrt(value: int) -> int:
    root = math.isqrt(value)
    return root if root * root == value else root + 1


def _make_row(bits: int, c: int, T: int, rng: random.Random,
              used_primes: set[int]) -> tuple[dict, int]:
    low, high = 1 << (bits - 1), 1 << bits
    max_k = min(max(5, bits), T - 1)
    for _ in range(20000):
        q = _random_prime(bits, rng)
        if q in used_primes or q == T:
            continue
        k = rng.randrange(2, max_k + 1)
        b = (k * (q % T)) % T
        pi_low = max(0, (low - b + T - 1) // T)
        pi_high = (high - 1 - b) // T
        quotients = list(range(pi_low, pi_high + 1))
        rng.shuffle(quotients)
        for pi in quotients:
            p = pi * T + b
            if p == q or p in used_primes or not _is_prime(p):
                continue
            # Fermat's method starts at ceil(sqrt(N)) and succeeds at (p+q)/2.
            N = p * q
            fermat_steps = (p + q) // 2 - _ceil_sqrt(N)
            if bits >= 20 and fermat_steps <= 20000:
                continue
            row = {
                "N": N,
                "k": k,
                "C": pi + q // T,
            }
            return row, min(p, q)
    raise RuntimeError("could not construct a separated SSB prime pair")


def make_instance(n, seed=0, **params) -> dict:
    """Build n independent SSB rows, retaining the planted factors."""
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 32:
        raise ValueError("n must be an integer in 1..32")
    factor_bits = params.get("factor_bits", 29)
    c = params.get("c", 5)
    if (isinstance(factor_bits, bool) or not isinstance(factor_bits, int)
            or not 8 <= factor_bits <= 62):
        raise ValueError("factor_bits must be an integer in 8..62")
    if isinstance(c, bool) or not isinstance(c, int) or not 3 <= c <= factor_bits - 5:
        raise ValueError("c must be an integer in 3..factor_bits-5")

    rng = random.Random(seed)
    T = _random_prime(factor_bits - c, rng, residue4=3)
    rows = []
    answer = []
    used_primes: set[int] = set()
    for _ in range(n):
        row, smaller = _make_row(factor_bits, c, T, rng, used_primes)
        cofactor = row["N"] // smaller
        used_primes.update((smaller, cofactor))
        rows.append(row)
        answer.append(smaller)
    return {
        "n": n,
        "factor_bits": factor_bits,
        "c": c,
        "T": T,
        "rows": rows,
        "answer": answer,
    }


def render(inst) -> str:
    rows = "\n".join(
        f"{i}: N={row['N']}  k={row['k']}  C={row['C']}"
        for i, row in enumerate(inst["rows"], 1)
    )
    examples = ",".join(str(101 + 2 * i) for i in range(inst["n"]))
    statement = f"""SSB factor recovery (arXiv:2201.13153)

There are {inst['n']} independent rows.  In every row, N is the product p*q
of two distinct prime integers p and q, each having exactly alpha={inst['factor_bits']}
bits (so 2^(alpha-1) <= p,q < 2^alpha).  The common escrow modulus
T={inst['T']} is prime and T modulo 4 equals 3.

For each row the displayed nonzero integer k and integer C satisfy, for one
ordering of its hidden factors,

    p = k*q (mod T),
    C = floor(p/T) + floor(q/T).

Here x = y (mod T) means T divides x-y, and floor is ordinary integer floor.
Find the SMALLER prime factor of N in every row.  Row numbering is 1-based;
your output entries must follow that order.  No repeats are intended, and each
entry must be a decimal integer with exactly alpha bits.

Rows:
{rows}

Give your final answer inside <answer></answer> tags as one JSON list of exactly
{inst['n']} decimal integers, with no quotes and no expressions.
Example format: <answer>[{examples}]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer>\s*(.*?)\s*</answer>", text, re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    return value


def verify(inst, answer) -> tuple[bool, str]:
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer list is empty"
    wanted = len(inst["rows"])
    if len(answer) < wanted:
        return False, f"too few factor entries: expected {wanted}"
    if len(answer) > wanted:
        return False, f"too many factor entries: expected {wanted}"
    low, high = 1 << (inst["factor_bits"] - 1), 1 << inst["factor_bits"]
    for i, (row, candidate) in enumerate(zip(inst["rows"], answer), 1):
        if isinstance(candidate, bool) or not isinstance(candidate, int):
            return False, f"entry {i} is not an integer"
        if not low <= candidate < high:
            return False, f"entry {i} lies outside the alpha-bit factor range"
        if row["N"] % candidate:
            return False, f"entry {i} is not a divisor of N in row {i}"
        other = row["N"] // candidate
        if candidate >= other:
            return False, f"entry {i} is not the smaller factor"
        if candidate * other != row["N"]:
            return False, f"entry {i} fails the exact product check"
    return True, "ok"


def _count_wheel_candidates(bits: int) -> int:
    low, high = 1 << (bits - 1), 1 << bits

    def through(x: int) -> int:
        if x < 0:
            return 0
        cycles, remainder = divmod(x + 1, _WHEEL)
        return cycles * _WHEEL_PREFIX[-1] + (
            _WHEEL_PREFIX[remainder - 1] if remainder else 0
        )

    return through(high - 1) - through(low - 1)


def random_candidate(inst, rng) -> object:
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    low, high = 1 << (inst["factor_bits"] - 1), 1 << inst["factor_bits"]
    answer = []
    for _ in inst["rows"]:
        while True:
            candidate = rng.randrange(low, high)
            if math.gcd(candidate, _WHEEL) == 1:
                answer.append(candidate)
                break
    return answer


def search_space(inst) -> int | None:
    return _count_wheel_candidates(inst["factor_bits"]) ** len(inst["rows"])


def enumerate_all(inst) -> int | None:
    size = search_space(inst)
    if size is None or size > 200000:
        return None
    low, high = 1 << (inst["factor_bits"] - 1), 1 << inst["factor_bits"]
    candidates = [x for x in range(low, high) if math.gcd(x, _WHEEL) == 1]
    count = 0
    for answer in itertools.product(candidates, repeat=len(inst["rows"])):
        if verify(inst, list(answer))[0]:
            count += 1
    return count


def _canonical_row(T: int, row: dict) -> tuple[int, int, int]:
    k = row["k"] % T
    inverse = pow(k, -1, T)
    return row["N"], row["C"], min(k, inverse)


def canonical_key(inst) -> str:
    payload = {
        "factor_bits": inst["factor_bits"],
        "T": inst["T"],
        "rows": sorted(_canonical_row(inst["T"], row) for row in inst["rows"]),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


def escalate(params) -> dict | None:
    n = params.get("n")
    bits = params.get("factor_bits", 29)
    c = params.get("c", 5)
    if not isinstance(n, int) or n >= 6:
        return None
    return {"n": n + 1, "factor_bits": bits, "c": c}


def _inverse_with_count(a: int, modulus: int) -> tuple[int, int]:
    old_r, r = a, modulus
    old_s, s = 1, 0
    operations = 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        operations += 3
    if old_r != 1:
        raise ValueError("noninvertible multiplier")
    return old_s % modulus, operations + 1


def _power_with_count(base: int, exponent: int, modulus: int) -> tuple[int, int]:
    result = 1
    value = base % modulus
    operations = 1
    while exponent:
        if exponent & 1:
            result = result * value % modulus
            operations += 1
        exponent >>= 1
        if exponent:
            value = value * value % modulus
            operations += 1
    return result, operations


def _recover_row(T: int, row: dict) -> tuple[int, int]:
    inverse, operations = _inverse_with_count(row["k"] % T, T)
    square = row["N"] * inverse % T
    operations += 1
    root, power_operations = _power_with_count(square, (T + 1) // 4, T)
    operations += power_operations
    for a in (root, (-root) % T):
        b = row["k"] * a % T
        operations += 1
        residue_product = a * b
        operations += 1
        if (row["N"] - residue_product) % T:
            operations += 1
            continue
        delta = (row["N"] - residue_product) // T
        coefficient = b - a - row["C"] * T
        constant = delta - b * row["C"]
        discriminant = coefficient * coefficient - 4 * T * constant
        operations += 7
        if discriminant < 0:
            continue
        sqrt_discriminant = math.isqrt(discriminant)
        operations += 1
        if sqrt_discriminant * sqrt_discriminant != discriminant:
            operations += 1
            continue
        for sign in (sqrt_discriminant, -sqrt_discriminant):
            numerator = -coefficient + sign
            denominator = 2 * T
            operations += 2
            if numerator % denominator:
                operations += 1
                continue
            pi = numerator // denominator
            nu = row["C"] - pi
            p = pi * T + b
            q = nu * T + a
            operations += 5
            if p > 1 and q > 1 and p * q == row["N"]:
                operations += 1
                return min(p, q), operations
            operations += 1
    raise ValueError("SSB recovery found no factor")


def _reference_algorithm(inst) -> tuple[list[int], int]:
    answer = []
    operations = 0
    for row in inst["rows"]:
        factor, row_operations = _recover_row(inst["T"], row)
        answer.append(factor)
        operations += row_operations
    return answer, operations


def _fallback_candidate(inst) -> list[int]:
    low = 1 << (inst["factor_bits"] - 1)
    return [low + 1 + 2 * i for i in range(len(inst["rows"]))]


def _attack_nearest_square(inst, _seed) -> list[int]:
    return [math.isqrt(row["N"]) for row in inst["rows"]]


def _attack_no_wrap(inst, _seed) -> list[int]:
    answer = []
    for row in inst["rows"]:
        candidate = math.isqrt(row["N"] // max(1, row["k"]))
        answer.append(max(1 << (inst["factor_bits"] - 1), candidate))
    return answer


def _attack_residue_as_factor(inst, _seed) -> list[int]:
    low = 1 << (inst["factor_bits"] - 1)
    return [low + (row["N"] % inst["T"]) for row in inst["rows"]]


def _attack_small_trial_division(inst, _seed, limit=10000) -> list[int]:
    output = []
    low = 1 << (inst["factor_bits"] - 1)
    for row in inst["rows"]:
        found = None
        divisor = 3
        while divisor <= limit:
            if row["N"] % divisor == 0:
                found = divisor
                break
            divisor += 2
        output.append(found if found is not None else low + 1)
    return output


def _fermat_factor(value: int, iterations: int) -> tuple[int | None, int]:
    a = _ceil_sqrt(value)
    for node in range(1, iterations + 1):
        b2 = a * a - value
        b = math.isqrt(b2)
        if b * b == b2:
            factor = a - b
            if 1 < factor < value and value % factor == 0:
                return min(factor, value // factor), node
        a += 1
    return None, iterations


def _attack_fermat(inst, _seed, iterations=512) -> list[int]:
    low = 1 << (inst["factor_bits"] - 1)
    output = []
    for row in inst["rows"]:
        factor, _nodes = _fermat_factor(row["N"], iterations)
        output.append(factor if factor is not None else low + 1)
    return output


def _attack_random_restart(inst, seed, restarts=256) -> list[int]:
    rng = random.Random(seed ^ 0x220113153)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return _fallback_candidate(inst)


def _transform(inst, *, reorder=False, invert=False) -> tuple[dict, list[int]]:
    rows = [dict(row) for row in inst["rows"]]
    answer = list(inst["answer"])
    if invert:
        for row in rows:
            row["k"] = pow(row["k"], -1, inst["T"])
    if reorder:
        order = list(range(len(rows) - 1, -1, -1))
        rows = [rows[i] for i in order]
        answer = [answer[i] for i in order]
    transformed = dict(inst)
    transformed["rows"] = rows
    # This is only for the carried-witness test; verify never consults it.
    transformed["answer"] = answer
    return transformed, answer


def selftest() -> dict:
    report: dict = {}

    failures = []
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            if not ok:
                failures.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not failures and json_roundtrips == 12,
        "attempts": 12,
        "json_roundtrips": json_roundtrips,
        "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=0, **shipping_params)
    planted = shipping["answer"]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": [planted[1], planted[0]] + planted[2:],
        "duplicate_one": planted + [planted[-1]],
        "empty": [],
        "out_of_range": [1] + planted[1:],
    }
    corruption_cases = {}
    reasons = set()
    for name, candidate in corruptions.items():
        ok, why = verify(shipping, candidate)
        corruption_cases[name] = {"rejected": not ok, "reason": why}
        reasons.add(why)
    report["G2_rejects_corruption"] = {
        "pass": (all(case["rejected"] for case in corruption_cases.values())
                 and len(reasons) == len(corruption_cases)),
        "cases": corruption_cases,
        "distinct_reasons": len(reasons),
    }

    realistic = (
        "I used the congruence and checked each product.\n```json\n"
        f"<answer>{json.dumps(planted)}</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": (parsed == planted and parse_answer("no tagged answer") is None),
        "parsed": parsed,
        "garbage_returns_none": parse_answer("no tagged answer") is None,
    }

    guess_total = 200000
    guess_hits = 0
    guess_rng = random.Random(220113153)
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        if verify(shipping, random_candidate(shipping, guess_rng))[0]:
            guess_hits += 1
    guess_seconds = time.perf_counter() - guess_start
    observed = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": observed,
        "structure_aware_space": search_space(shipping),
        "sampler": (
            "uniform alpha-bit integers independently per row after exact "
            "small-prime wheel sieving"
        ),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    baseline_nodes = 4096
    baseline_start = time.perf_counter()
    baseline_answer = _attack_fermat(shipping, 0, baseline_nodes)
    baseline_seconds = time.perf_counter() - baseline_start
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    report["G5_density_and_baseline"] = {
        "pass": (guess_hits == 0 and not verify(shipping, baseline_answer)[0]
                 and enumerate_all(demo) == 1),
        "shipping_valid_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_observed_solution_fraction": observed,
        "shipping_exact_solution_count_by_construction": 1,
        "demo_exact_solution_count": enumerate_all(demo),
        "strongest_failing_attack": "bounded Fermat factorization",
        "baseline_nodes_per_row": baseline_nodes,
        "baseline_total_nodes": baseline_nodes * shipping["n"],
        "baseline_wall_seconds": round(baseline_seconds, 6),
    }

    attack_functions = {
        "outlier_nearest_square": _attack_nearest_square,
        "greedy_no_modular_wrap": _attack_no_wrap,
        "residue_as_factor_ansatz": _attack_residue_as_factor,
        "in_context_fermat_512": lambda inst, seed: _attack_fermat(inst, seed, 512),
        "small_prime_trial_division_10000": _attack_small_trial_division,
        "random_restart_256": _attack_random_restart,
    }
    attacks = {name: {"successes": 0, "attempts": 8}
               for name in attack_functions}
    reference_times = []
    reference_operations = []
    reference_successes = 0
    for seed in range(80, 88):
        inst = make_instance(seed=seed, **shipping_params)
        for name, attack in attack_functions.items():
            if verify(inst, attack(inst, seed))[0]:
                attacks[name]["successes"] += 1
        started = time.perf_counter()
        answer, operations = _reference_algorithm(inst)
        reference_times.append(time.perf_counter() - started)
        reference_operations.append(operations)
        if verify(inst, answer)[0]:
            reference_successes += 1
    median_time = statistics.median(reference_times)
    median_operations = int(statistics.median(reference_operations))
    max_operations = max(reference_operations)
    all_failed = all(result["successes"] == 0 for result in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "SSB modular-square-root and quotient-sum lifting",
            "complexity": "O(n log T) exact arithmetic for T congruent to 3 mod 4",
            "median_wall_clock_sec": round(median_time, 9),
            "median_operations": median_operations,
            "max_operations_over_8": max_operations,
            "operation_definition": (
                "Euclidean divisions/updates, modular multiplies or squares, "
                "quadratic arithmetic, and exact integer-square-root calls"
            ),
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=31, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    _doubled_answer, doubled_operations = _reference_algorithm(doubled)
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_operations > median_operations,
        "shipping_n": shipping_params["n"],
        "doubled_n": doubled_params["n"],
        "shipping_reference_operations": median_operations,
        "doubled_reference_operations": doubled_operations,
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = 0
    carried_witness_checks = 0
    for seed in range(20):
        inst = make_instance(seed=seed, **shipping_params)
        key = canonical_key(inst)
        for options in (
            {"reorder": True},
            {"invert": True},
            {"reorder": True, "invert": True},
        ):
            transformed, carried = _transform(inst, **options)
            invariance_checks += canonical_key(transformed) == key
            carried_witness_checks += verify(transformed, carried)[0]
    unrelated_keys = {
        canonical_key(make_instance(seed=1000 + seed, **shipping_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": (invariance_checks == 60 and carried_witness_checks == 60
                 and len(unrelated_keys) == 20),
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_witness_checks,
        "unrelated_attempts": 20,
        "unrelated_distinct": len(unrelated_keys),
        "symmetries": [
            "row reordering",
            "swapping factor roles by replacing k with its inverse modulo T",
            "composition of row reordering and factor-role swap",
        ],
    }

    answer_body = json.dumps(planted, separators=(",", ":"))
    answer_chars = len(answer_body)
    answer_tokens = max(1, (answer_chars + 3) // 4)
    answer_elements = len(planted)
    arms = G9_RESULTS["arms"]
    hinted_verdict = G9_RESULTS["hinted_verdict"]
    hinted_still_hardened = hinted_verdict == "hardened"
    intended_operations = max(max_operations, _reference_algorithm(shipping)[1])
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_operations <= 300)
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    report["G9_no_tool_suitability"] = {
        "pass": hinted_still_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": hinted_verdict,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["all_passed"] = all(
        result.get("pass", False)
        for name, result in report.items()
        if name.startswith("G") and name[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
