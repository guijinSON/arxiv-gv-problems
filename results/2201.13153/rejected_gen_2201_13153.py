"""Native SSB factor-recovery generator for arXiv:2201.13153.

Prime factors are sampled first; only the semiprime N, escrow prime T, and
coefficient bound K are posed. Verification is exact and never reads the plant.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import statistics
import time

TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "The least-significant digit of N in base T has a deliberately small "
    "square-free part."
)
PLACEBO_HINT: str = (
    "The exact integer ranges in the statement are useful consistency checks."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "number_theory",
    "object_regime": "finite_discrete",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "balanced semiprime",
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
    "intuition_type": "decomposition",
    "intuition_description": (
        "A carry-free base-T expansion exposes product and weighted-sum identities "
        "for the hidden quotient coefficients; without recognizing it, Section "
        "4.2 searches k and the lift range."
    ),
    "hardness_basis": (
        "Track B: Cesati Section 4.2 recovers factors in "
        "O(K*(alpha+c)^3*2^(2c)) bit operations (Section 4.3); the shipping "
        "preset's faithful scan cost is measured in selftest_report.json, while "
        "the carry-free decomposition uses fewer than 80 exact operations."
    ),
    "max_answer_tokens": 6,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

# n is the SSB coefficient bound K. The answer remains one integer as K grows.
DIFFICULTY: dict = {
    "demo": {"n": 11, "factor_bits": 13, "c": 3, "residue_bound": 9},
    "easy": {"n": 509, "factor_bits": 61, "c": 7, "residue_bound": 100_000},
    "medium": {"n": 997, "factor_bits": 61, "c": 7, "residue_bound": 200_000},
    "hard": {"n": 1995, "factor_bits": 61, "c": 8, "residue_bound": 400_000},
}
SHIPPING_DIFFICULTY: str = "easy"

_WHEEL_PRIMES = (2, 3, 5, 7, 11, 13)
_WHEEL = math.prod(_WHEEL_PRIMES)


def _make_wheel_prefix() -> tuple[int, ...]:
    count, out = 0, []
    for value in range(_WHEEL):
        count += math.gcd(value, _WHEEL) == 1
        out.append(count)
    return tuple(out)


_WHEEL_PREFIX = _make_wheel_prefix()

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON list containing exactly one alpha-bit decimal integer coprime "
        "to 2*3*5*7*11*13, representing the smaller nontrivial factor."
    ),
    "bounds": {"entries": 1, "max_factor_bits": 62, "small_prime_wheel": _WHEEL},
}

NOTES: str = (
    "Section 4.1 fixes SSB condition H0: for a prime escrow key T, p is "
    "congruent to k*q modulo T for some 1<k<=K; Figure 1 gives inverse prime "
    "generation. Sections 4.2.1--4.2.3 give the executable recovery: search k, "
    "take modular square roots, search quotient coefficients, and check the "
    "product. Section 4.3 makes Track A dishonest: this costs "
    "O(K*(alpha+c)^3*2^(2c)), is polynomial in the recommended regime, and "
    "Table 1 measures RSA-size runs. Here q=nu*T+a and p=pi*T+k*a, with no "
    "carries in N's first three base-T digits. The residue a uses only 3,5,7 "
    "while k is a larger prime, making the constant digit's square-free part "
    "the compact invariant. Factors and T are sampled before N is formed, and "
    "deterministic Miller--Rabin below 2^64 makes generation exact. Separated "
    "factors and a large k defeat bounded Fermat and the by-hand small-k route; "
    "trial division, digit guessing, Pollard rho, and random restarts are measured."
)

# Filled from the script-owned hardening transcripts before the final selftest.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "pending",
}


def _is_prime(value: int) -> bool:
    """Deterministic Miller--Rabin for values below 2^64."""
    if value < 2:
        return False
    for prime in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if value % prime == 0:
            return value == prime
    if value >= 1 << 64:
        raise ValueError("exact primality is limited to values below 2^64")
    d, s = value - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        a = base % value
        if not a:
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
    low, high = 1 << (bits - 1), 1 << bits
    for _ in range(250_000):
        candidate = rng.randrange(low, high) | 1
        if residue4 is not None:
            candidate += (residue4 - candidate) % 4
            if candidate >= high:
                continue
        if _is_prime(candidate):
            return candidate
    raise RuntimeError("prime sampling budget exhausted")


def _smooth_residues(bound: int) -> list[int]:
    values = set()
    p3 = 1
    while p3 <= bound:
        p5 = p3
        while p5 <= bound:
            p7 = p5
            while p7 <= bound:
                if p7 >= 3:
                    values.add(p7)
                p7 *= 7
            p5 *= 5
        p3 *= 3
    return sorted(values)


def _even_values(low: int, high: int) -> list[int]:
    return list(range(low + (low & 1), high + 1, 2))


def _quotient_range(bits: int, T: int, residue: int) -> tuple[int, int]:
    low, high = 1 << (bits - 1), 1 << bits
    return ((low - residue + T - 1) // T, (high - 1 - residue) // T)


def _construct(bits: int, c: int, K: int, residue_bound: int,
               rng: random.Random) -> dict:
    floor = 5 if K < 37 else max(37, K // 2)
    k_values = [k for k in range(floor, K + 1) if _is_prime(k)]
    smooth = _smooth_residues(residue_bound)
    if not k_values or not smooth:
        raise ValueError("parameters leave no usable coefficient or residue")
    for _ in range(256):
        T = _random_prime(bits - c, rng, residue4=3)
        ks, residues = list(k_values), list(smooth)
        rng.shuffle(ks)
        rng.shuffle(residues)
        for a in residues:
            for k in ks:
                D = k * a * a
                if D >= T:
                    continue
                qlo, qhi = _quotient_range(bits, T, a)
                nus = _even_values(qlo, qhi)
                rng.shuffle(nus)
                q_nu = next(((nu * T + a, nu) for nu in nus
                             if _is_prime(nu * T + a)), None)
                if q_nu is None:
                    continue
                q, nu = q_nu
                b = k * a
                plo, phi = _quotient_range(bits, T, b)
                pis = _even_values(plo, phi)
                rng.shuffle(pis)
                for pi in pis:
                    p = pi * T + b
                    if p == q or not _is_prime(p):
                        continue
                    B = a * (pi + k * nu)
                    if B >= T:
                        continue
                    N = p * q
                    high, D2 = divmod(N, T)
                    A, B2 = divmod(high, T)
                    if (A, B2, D2) != (pi * nu, B, D):
                        continue
                    if bits >= 30:
                        steps = (p + q) // 2 - math.isqrt(N)
                        if steps <= 100_000:
                            continue
                    return {"N": N, "T": T, "base_digits": [A, B, D],
                            "answer": [min(p, q)]}
    raise RuntimeError("could not construct a carry-free SSB semiprime")


def make_instance(n, seed=0, **params) -> dict:
    """Build an inverse-generated SSB instance; n is coefficient bound K."""
    if isinstance(n, bool) or not isinstance(n, int) or not 5 <= n <= 20_000:
        raise ValueError("n must be an integer in 5..20000")
    bits = params.get("factor_bits", 61)
    c = params.get("c", 6)
    bound = params.get("residue_bound", 50_000)
    if isinstance(bits, bool) or not isinstance(bits, int) or not 8 <= bits <= 62:
        raise ValueError("factor_bits must be an integer in 8..62")
    if isinstance(c, bool) or not isinstance(c, int) or not 3 <= c <= bits - 5:
        raise ValueError("c must be an integer in 3..factor_bits-5")
    if isinstance(bound, bool) or not isinstance(bound, int) or not 3 <= bound <= 2_000_000:
        raise ValueError("residue_bound must be an integer in 3..2000000")
    core = _construct(bits, c, n, bound, random.Random(seed))
    return {"n": n, "factor_bits": bits, "c": c,
            "residue_bound": bound, **core}


def render(inst) -> str:
    statement = f"""Single Semiprime Backdoor factor recovery (arXiv:2201.13153)

Let alpha={inst['factor_bits']}. The displayed integer N is the product p*q of
two distinct primes, each with exactly alpha bits; hence
2^(alpha-1) <= p,q < 2^alpha. The displayed T is prime. The SSB promise holds:
for one ordering of p and q, some integer k with 2 <= k <= K obeys
p = k*q (mod T), meaning T divides p-k*q.

N = {inst['N']}
T = {inst['T']}
K = {inst['n']}

Find the smaller nontrivial factor of N. Your answer is a JSON list containing
exactly one base-10 integer. The list order is fixed and repetitions are forbidden.

Give your final answer inside <answer></answer> tags as that one-element JSON list.
Example: <answer>[123457]</answer>
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
    body = re.sub(r"^```(?:json|text)?\s*", "", matches[-1].strip(), flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        answer = json.loads(body)
    except (TypeError, ValueError):
        return None
    return answer if isinstance(answer, list) else None


def verify(inst, answer) -> tuple[bool, str]:
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer list is empty"
    if len(answer) != 1:
        return False, "answer must contain exactly one factor"
    factor = answer[0]
    if isinstance(factor, bool) or not isinstance(factor, int):
        return False, "the factor is not an integer"
    low, high = 1 << (inst["factor_bits"] - 1), 1 << inst["factor_bits"]
    if not low <= factor < high:
        return False, "the factor lies outside the required alpha-bit range"
    if inst["N"] % factor:
        return False, "the candidate is not a divisor of N"
    cofactor = inst["N"] // factor
    if factor >= cofactor:
        return False, "the candidate divisor is not the smaller factor"
    if factor * cofactor != inst["N"]:
        return False, "the exact product check failed"
    return True, "ok"


def _count_wheel_candidates(bits: int) -> int:
    low, high = 1 << (bits - 1), 1 << bits
    def through(x: int) -> int:
        if x < 0:
            return 0
        cycles, rem = divmod(x + 1, _WHEEL)
        return cycles * _WHEEL_PREFIX[-1] + (_WHEEL_PREFIX[rem - 1] if rem else 0)
    return through(high - 1) - through(low - 1)


def random_candidate(inst, rng) -> object:
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    low, high = 1 << (inst["factor_bits"] - 1), 1 << inst["factor_bits"]
    while True:
        value = rng.randrange(low, high)
        if math.gcd(value, _WHEEL) == 1:
            return [value]


def search_space(inst) -> int | None:
    return _count_wheel_candidates(inst["factor_bits"])


def enumerate_all(inst) -> int | None:
    if search_space(inst) > 200_000:
        return None
    low, high = 1 << (inst["factor_bits"] - 1), 1 << inst["factor_bits"]
    return sum(verify(inst, [x])[0] for x in range(low, high)
               if math.gcd(x, _WHEEL) == 1)


def canonical_key(inst) -> str:
    data = (inst["factor_bits"], inst["N"], inst["T"], inst["n"])
    return hashlib.sha256(repr(data).encode("ascii")).hexdigest()


def escalate(params) -> dict | str | None:
    K = params.get("n")
    if not isinstance(K, int) or K >= 20_000:
        return None
    bits, c = params.get("factor_bits", 61), params.get("c", 7)
    return {"n": min(20_000, 2 * K + 1), "factor_bits": bits,
            "c": min(bits - 5, c + (K >= 2000)),
            "residue_bound": min(2_000_000, params.get("residue_bound", 100_000) * 2)}


def _paper_recover(inst) -> tuple[list[int], dict]:
    """Section 4.2's k/high-coefficient scan, instrumented."""
    N, T, K = inst["N"], inst["T"], inst["n"]
    upper_C = -(-N // (T * T))
    iterations = powers = 0
    for k in range(2, K + 1):
        z = N * pow(k, -1, T) % T
        powers += 1
        if pow(z, (T - 1) // 2, T) != 1:
            powers += 1
            continue
        root = pow(z, (T + 1) // 4, T)
        powers += 2
        for a in (root, (-root) % T):
            b = k * a % T
            delta = (N - a * b) // T
            for C in range(upper_C + 1):
                iterations += 1
                coefficient = b - a - C * T
                constant = delta - b * C
                disc = coefficient * coefficient - 4 * T * constant
                if disc < 0:
                    continue
                square = math.isqrt(disc)
                if square * square != disc:
                    continue
                denominator = 2 * T
                for signed in (square, -square):
                    numerator = -coefficient + signed
                    if numerator % denominator:
                        continue
                    pi, nu = numerator // denominator, C - numerator // denominator
                    p, q = pi * T + b, nu * T + a
                    if p > 1 and q > 1 and p * q == N:
                        return [min(p, q)], {
                            "coefficient_iterations": iterations,
                            "modular_power_calls": powers,
                            "counted_operations": iterations * 8 + powers,
                            "upper_C": upper_C,
                        }
    raise ValueError("Section 4.2 recovery found no factor")


def _compact_recover(inst) -> tuple[list[int], int]:
    N, T, K = inst["N"], inst["T"], inst["n"]
    high, D = divmod(N, T)
    A, B = divmod(high, T)
    operations, remainder, a = 2, D, 1
    for prime in (3, 5, 7):
        exponent = 0
        while remainder % prime == 0:
            remainder //= prime
            exponent += 1
            operations += 2
        operations += 1
        if exponent % 2:
            raise ValueError("constant digit lacks the planted square shape")
        a *= prime ** (exponent // 2)
        operations += 1
    k = remainder
    if not (2 <= k <= K and _is_prime(k) and D == k * a * a):
        raise ValueError("constant digit has no admissible square-free part")
    operations += 4
    if B % a:
        raise ValueError("middle digit is incompatible with the residue")
    S = B // a
    disc = S * S - 4 * k * A
    root = math.isqrt(disc)
    operations += 6
    if root * root != disc:
        raise ValueError("quotient discriminant is not square")
    for signed in (root, -root):
        numerator, denominator = S + signed, 2 * k
        operations += 2
        if numerator % denominator:
            operations += 1
            continue
        nu = numerator // denominator
        if not nu or A % nu:
            operations += 2
            continue
        pi = A // nu
        p, q = pi * T + k * a, nu * T + a
        operations += 7
        if p * q == N:
            return [min(p, q)], operations + 1
        operations += 1
    raise ValueError("carry-free recovery found no factor")


def _fallback(inst) -> list[int]:
    return [(1 << (inst["factor_bits"] - 1)) + 1]


def _attack_digit(inst, _seed) -> list[int]:
    _, digit = divmod(inst["N"], inst["T"])
    low = 1 << (inst["factor_bits"] - 1)
    return [digit if digit >= low else low + digit]


def _fermat(value: int, budget: int) -> tuple[int | None, int]:
    x = math.isqrt(value)
    x += x * x < value
    for node in range(1, budget + 1):
        square = x * x - value
        root = math.isqrt(square)
        if root * root == square:
            factor = x - root
            if 1 < factor < value and value % factor == 0:
                return min(factor, value // factor), node
        x += 1
    return None, budget


def _attack_fermat(inst, _seed, budget=4096) -> list[int]:
    factor, _ = _fermat(inst["N"], budget)
    return [factor] if factor else _fallback(inst)


def _attack_trial(inst, _seed, limit=10_000) -> list[int]:
    for divisor in range(3, limit + 1, 2):
        if inst["N"] % divisor == 0:
            return [divisor]
    return _fallback(inst)


def _attack_small_k(inst, _seed, limit=31) -> list[int]:
    N, T = inst["N"], inst["T"]
    high, D = divmod(N, T)
    A, B = divmod(high, T)
    for k in range(2, min(limit, inst["n"]) + 1):
        if D % k:
            continue
        a = math.isqrt(D // k)
        if not a or a * a != D // k or B % a:
            continue
        S, disc = B // a, (B // a) ** 2 - 4 * k * A
        if disc < 0:
            continue
        root = math.isqrt(disc)
        if root * root != disc:
            continue
        for signed in (root, -root):
            den = 2 * k
            if (S + signed) % den:
                continue
            nu = (S + signed) // den
            if nu and A % nu == 0:
                p, q = (A // nu) * T + k * a, nu * T + a
                if p * q == N:
                    return [min(p, q)]
    return _fallback(inst)


def _pollard_rho(value: int, seed: int, restarts=8,
                 steps=4096) -> tuple[int | None, int]:
    rng, used = random.Random(seed ^ 0x220113153), 0
    for _ in range(restarts):
        x = rng.randrange(2, value - 1)
        y, constant = x, rng.randrange(1, value - 1)
        for _ in range(steps):
            x = (x * x + constant) % value
            y = (y * y + constant) % value
            y = (y * y + constant) % value
            divisor = math.gcd(abs(x - y), value)
            used += 1
            if 1 < divisor < value:
                return min(divisor, value // divisor), used
            if divisor == value:
                break
    return None, used


def _attack_rho(inst, seed) -> list[int]:
    factor, _ = _pollard_rho(inst["N"], seed)
    return [factor] if factor else _fallback(inst)


def _attack_restart(inst, seed, attempts=256) -> list[int]:
    rng = random.Random(seed ^ 0x515342)
    for _ in range(attempts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return _fallback(inst)


def _factor_label_swap(inst: dict) -> tuple[dict, list[int]]:
    return dict(inst), list(inst["answer"])


def selftest() -> dict:
    report, failures, json_checks = {}, [], 0
    for preset, preset_params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **preset_params)
            ok, why = verify(inst, inst["answer"])
            if not ok:
                failures.append(f"{preset}/{seed}: {why}")
            json_checks += json.loads(json.dumps(inst["answer"])) == inst["answer"]
    report["G1_planted_verifies"] = {
        "pass": not failures and json_checks == 12, "attempts": 12,
        "json_roundtrips": json_checks, "failures": failures}

    params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=0, **params)
    factor = shipping["answer"][0]
    corruptions = {
        "drop_container": factor,
        "swap_to_larger_factor": [shipping["N"] // factor],
        "duplicate_factor": [factor, factor], "empty": [], "out_of_range": [1]}
    cases, reasons = {}, set()
    for name, candidate in corruptions.items():
        ok, why = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": why}
        reasons.add(why)
    report["G2_rejects_corruption"] = {
        "pass": all(x["rejected"] for x in cases.values()) and len(reasons) == 5,
        "cases": cases, "distinct_reasons": len(reasons)}

    response = f"Reasoning here.\n```json\n<answer>{json.dumps(shipping['answer'])}</answer>\n```"
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and parse_answer("garbage") is None,
        "parsed": parsed, "garbage_returns_none": parse_answer("garbage") is None}

    total, hits, rng = 200_000, 0, random.Random(220113153)
    started = time.perf_counter()
    for _ in range(total):
        hits += verify(shipping, random_candidate(shipping, rng))[0]
    guess_seconds = time.perf_counter() - started
    report["G4_guess_resistance"] = {
        "pass": hits / total < 1e-6, "hits": hits, "total": total,
        "observed_probability": hits / total,
        "structure_aware_space": search_space(shipping),
        "sampler": "uniform alpha-bit integers surviving the small-prime wheel",
        "wall_clock_sec": round(guess_seconds, 6)}

    started = time.perf_counter()
    rho_factor, rho_iterations = _pollard_rho(shipping["N"], 0)
    rho_seconds = time.perf_counter() - started
    demo_count = enumerate_all(make_instance(seed=0, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline"] = {
        "pass": hits == 0 and rho_factor is None and demo_count == 1,
        "shipping_valid_hits": hits, "shipping_density_samples": total,
        "shipping_observed_solution_fraction": hits / total,
        "shipping_exact_valid_answers": 1, "demo_exact_solution_count": demo_count,
        "strongest_failing_attack": "Pollard rho with deterministic restart budget",
        "baseline_iterations": rho_iterations, "baseline_restarts": 8,
        "baseline_wall_seconds": round(rho_seconds, 6)}

    attack_fns = {
        "outlier_base_digit_as_factor": _attack_digit,
        "greedy_fermat_4096": _attack_fermat,
        "random_restart_256": _attack_restart,
        "in_context_small_k_through_31": _attack_small_k,
        "small_prime_trial_division_10000": _attack_trial,
        "pollard_rho_8x4096": _attack_rho}
    attacks = {name: {"successes": 0, "attempts": 8} for name in attack_fns}
    ref_times, ref_iters, ref_ops, compact_ops = [], [], [], []
    reference_successes = 0
    for seed in range(80, 88):
        inst = make_instance(seed=seed, **params)
        for name, attack in attack_fns.items():
            attacks[name]["successes"] += verify(inst, attack(inst, seed))[0]
        started = time.perf_counter()
        ref_answer, stats = _paper_recover(inst)
        ref_times.append(time.perf_counter() - started)
        ref_iters.append(stats["coefficient_iterations"])
        ref_ops.append(stats["counted_operations"])
        reference_successes += verify(inst, ref_answer)[0]
        compact_answer, operations = _compact_recover(inst)
        compact_ops.append(operations)
        if not verify(inst, compact_answer)[0]:
            failures.append(f"compact/{seed}")
    all_failed = all(x["successes"] == 0 for x in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and not any(
            x.startswith("compact/") for x in failures),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Cesati Section 4.2 SSB recovery scan",
            "complexity": "O(K*(alpha+c)^3*2^(2c)) bit operations",
            "median_wall_clock_sec": round(statistics.median(ref_times), 6),
            "max_wall_clock_sec": round(max(ref_times), 6),
            "median_coefficient_iterations": int(statistics.median(ref_iters)),
            "max_coefficient_iterations": max(ref_iters),
            "median_counted_operations": int(statistics.median(ref_ops)),
            "solves": f"{reference_successes}/8, as expected"},
        "compact_route": {
            "name": "carry-free base-T decomposition",
            "median_operations": int(statistics.median(compact_ops)),
            "max_operations": max(compact_ops)}}

    doubled_params = dict(params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=31, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_params["n"] > params["n"],
        "shipping_K": params["n"], "doubled_K": doubled_params["n"],
        "answer_elements_before": 1, "answer_elements_after": 1,
        "doubled_verify_reason": doubled_why}

    invariance = carried = 0
    for seed in range(20):
        inst = make_instance(seed=seed, **params)
        transformed, witness = _factor_label_swap(inst)
        invariance += canonical_key(transformed) == canonical_key(inst)
        carried += verify(transformed, witness)[0]
    distinct = len({canonical_key(make_instance(seed=1000 + seed, **params))
                    for seed in range(20)})
    report["G8_canonical_key"] = {
        "pass": invariance == carried == distinct == 20,
        "symmetry": "swap the two hidden factor labels",
        "invariance_checks": invariance, "carried_witness_checks": carried,
        "distinct_unrelated_keys": distinct}

    blob = json.dumps(shipping["answer"], separators=(",", ":"))
    _, intended_ops = _compact_recover(shipping)
    arms, verdict = G9_RESULTS["arms"], G9_RESULTS["hinted_verdict"]
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = len(blob) <= 2000 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": verdict == "hardened" and within_caps, "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": verdict, "answer_chars": len(blob),
        "answer_tokens": max(1, math.ceil(len(blob) / 4)),
        "answer_elements": 1, "intended_route_operations": intended_ops,
        "within_caps": within_caps}

    report["all_passed"] = all(v.get("pass", False) for k, v in report.items()
                                  if k.startswith("G"))
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
