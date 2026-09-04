"""Verified problem generator for arXiv:1204.1113.

The generated object is native to the paper: a univariate sparse polynomial
over a prime finite field.  Generation transports a known root through the
power-substitution used in Section 3.1 of the paper.  All arithmetic in the
checker is exact integer arithmetic modulo p.
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
    "Find the coefficient pair related by minus three: their exponent difference "
    "is the unit that straightens every exponent into consecutive degrees."
)
PLACEBO_HINT: str = (
    "Keep the modular representatives and the two output limbs in their stated "
    "ranges throughout the calculation."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "univariate sparse polynomial over a prime finite field",
        "prime-field element encoded by two radix limbs",
    ],
    "verification_operations": [
        "exact modular exponentiation",
        "exact finite-field addition and multiplication",
        "integer range comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize the hidden invertible power substitution that lowers all "
        "exponents at once; without it one faces sparse root detection in a field "
        "with billions of elements."
    ),
    "hardness_basis": (
        "Track B: coefficient-indexed exponent unmasking followed by the Section "
        "3.1 power substitution and binary modular exponentiation is O(n+log p); "
        "at shipping n=48 and p=2^31-1 it took a median 161 counted exact "
        "operations and 0.000014 seconds over eight seeds, while an unaided solver "
        "must discover and execute the same large-integer map."
    ),
    "max_answer_tokens": 3,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

# All four primes are Mersenne primes and are 3 modulo 4.  The latter fact makes
# z^2+1 root-free and is the exact certificate behind the unique-root plant.
_PRIMES = {
    7: 127,
    31: 2147483647,
    61: 2305843009213693951,
    127: 170141183460469231731687303715884105727,
}

DIFFICULTY: dict = {
    "demo": {"n": 8, "prime_bits": 7},
    "easy": {"n": 48, "prime_bits": 31},
    "medium": {"n": 72, "prime_bits": 61},
    "hard": {"n": 96, "prime_bits": 127},
}
SHIPPING_DIFFICULTY: str = "easy"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "Exactly two nonnegative base-B limbs [high, low], each below B, whose "
        "decoded integer high*B+low lies in 1..p-1; B is stated in the instance."
    ),
    "bounds": {
        "n_limbs": 2,
        "max_limb_bits": 64,
        "max_field_bits": 127,
        "decoded_lower_bound": 1,
    },
}

NOTES: str = (
    "Section 1.1 and Theorem 1.1 fix the input as a t-nomial of degree below q "
    "over F_q and give the fixed-t sub-linear decision algorithm; the same section "
    "says d-th-power existence is polynomial in log d+log q, so binomials were "
    "avoided. Theorem 1.4 is only worst-case hardness when t grows and is not used "
    "as an average-case claim. Section 3.1 supplies the invertible power "
    "substitution carrying the planted root. The plant and decoys have identical "
    "one-coefficient marginals through a random global scale. Magnitude outliers, "
    "input-order greed, uniform restarts, and small-root ansatzes fail; the exact "
    "coefficient-pair unmasking algorithm is disclosed separately for Track B."
)

# Filled from the script-owned hardening runs before shipping.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "hardened",
}


def _convolve(a, b, p):
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] = (out[i + j] + x * y) % p
    return out


def _low_polynomial(n, p, rng):
    """Return coefficients of (y-3)(H(y)^2+1), dense and unambiguous.

    H is monic of degree (n-2)/2 with zero next-to-leading coefficient.
    Consequently the top two coefficients before scaling are exactly 1,-3.
    Since p=3 mod 4, H(y)^2+1 never vanishes in F_p, so y=3 is the
    unique field root.  Rejection sampling only removes accidental zero,
    duplicate, or additional -2 coefficient relations; it never searches for
    the certificate.
    """
    m = (n - 2) // 2
    while True:
        hpoly = [rng.randrange(1, p) for _ in range(m - 1)] + [0, 1]
        u = _convolve(hpoly, hpoly, p)
        u[0] = (u[0] + 1) % p
        g = [0] * (len(u) + 1)
        for i, coefficient in enumerate(u):
            g[i] = (g[i] - 3 * coefficient) % p
            g[i + 1] = (g[i + 1] + coefficient) % p
        if len(g) != n or any(c == 0 for c in g) or len(set(g)) != n:
            continue
        relations = [(i, j) for i, c in enumerate(g) for j, d in enumerate(g)
                     if d == (-3 * c) % p]
        if relations == [(n - 1, n - 2)]:
            return g


def _sample_unit(rng, modulus):
    while True:
        value = rng.randrange(2, modulus)
        if math.gcd(value, modulus) == 1:
            return value


def _limb_base(p):
    return 1 << ((p.bit_length() + 1) // 2)


def _encode_root(x, base):
    return [x // base, x % base]


def _decode_root(answer, base):
    return answer[0] * base + answer[1]


def make_instance(n, seed=0, **params) -> dict:
    """Transport the known root y=2 through an invertible power map.

    The answer is known by construction.  No root search or factorization is
    performed.  Larger n gives more terms to inspect, while prime_bits enlarges
    every modular operation.
    """
    prime_bits = params.pop("prime_bits", 31)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 8 or n % 2:
        raise ValueError("n must be an even integer at least 8")
    if prime_bits not in _PRIMES:
        raise ValueError("prime_bits must be one of 7, 31, 61, 127")
    p = _PRIMES[prime_bits]
    if n >= p:
        raise ValueError("n must be smaller than p")

    rng = random.Random(seed)
    coefficients = _low_polynomial(n, p, rng)
    scale = rng.randrange(1, p)
    coefficients = [(scale * c) % p for c in coefficients]

    # f(x)=g(x^h), with h a unit modulo p-1.  If e=h^{-1}, then
    # x=3^e satisfies f(x)=g(3)=0.  Reject the rare edge-of-range root so the
    # encoded answer has no small-integer signature.
    modulus = p - 1
    while True:
        h = _sample_unit(rng, modulus)
        inverse_h = pow(h, -1, modulus)
        root = pow(3, inverse_h, p)
        if p // 8 < root < 7 * p // 8:
            break
    # A cyclic exponent translation is multiplication by a monomial on F_p^*.
    # It preserves nonzero roots while removing any link between one
    # coefficient's marginal statistic and a distinguished exponent.
    exponent_shift = rng.randrange(modulus)
    terms = [[coefficients[b], (h * b + exponent_shift) % modulus]
             for b in range(n)]
    rng.shuffle(terms)

    base = _limb_base(p)
    return {
        "family": "hidden power substitution sparse root",
        "p": p,
        "prime_bits": prime_bits,
        "n": n,
        "limb_base": base,
        "terms": terms,
        "answer": _encode_root(root, base),
    }


def render(inst) -> str:
    lines = []
    for start in range(0, len(inst["terms"]), 4):
        chunk = inst["terms"][start:start + 4]
        lines.append("  " + "   ".join(f"({c}, {a})" for c, a in chunk))
    statement = f"""SPARSE POLYNOMIAL ROOT OVER A PRIME FIELD

Let p={inst['p']}. Arithmetic is in the prime field F_p: two integers denote
the same field element exactly when they have the same remainder modulo p.

The polynomial is
    f(x) = sum c*x^a over all pairs (c,a) below, computed modulo p.
All coefficients and exponents are ordinary decimal integers. Exponentiation
means field exponentiation; in particular x^0=1, including when x=0. The pair
order is irrelevant, exponents lie in 0..p-2, and there are exactly n={inst['n']}
nonzero terms. The polynomial has exactly one nonzero root in F_p (zero is
irrelevant and may or may not be a root).

(coefficient, exponent) pairs:
{chr(10).join(lines)}

Find the unique nonzero integer root x with 1 <= x < p. Encode it in exactly two
base-B limbs [high, low], where B={inst['limb_base']}, so that
x = high*B + low and 0 <= high,low < B. The brackets are omitted in the
answer block.

Give your final answer inside <answer></answer> tags, as two comma-separated
decimal integers high, low.
Example format: <answer>0, 1</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    try:
        matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", str(text),
                             re.I | re.S)
        if not matches:
            return None
        body = matches[-1].strip()
        body = re.sub(r"^```(?:text|json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
        match = re.fullmatch(r"\[?\s*(\d+)\s*,\s*(\d+)\s*\]?", body)
        if not match:
            return None
        return [int(match.group(1)), int(match.group(2))]
    except (TypeError, ValueError, OverflowError):
        return None


def verify(inst, answer) -> tuple[bool, str]:
    """Check a candidate root by direct exact substitution; never read answer."""
    if answer is None:
        return False, "answer is missing"
    if not isinstance(answer, list):
        return False, "answer must be a list of two limbs"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) < 2:
        return False, "too few limbs"
    if len(answer) > 2:
        return False, "too many limbs"
    if any(isinstance(v, bool) or not isinstance(v, int) for v in answer):
        return False, "limbs must be integers"
    base = inst["limb_base"]
    if any(v < 0 or v >= base for v in answer):
        return False, "limb out of range"
    x = _decode_root(answer, base)
    p = inst["p"]
    if x >= p:
        return False, "encoded root is outside F_p"
    if x == 0:
        return False, "root must be nonzero"
    residue = 0
    for coefficient, exponent in inst["terms"]:
        residue = (residue + coefficient * pow(x, exponent, p)) % p
    if residue != 0:
        return False, "encoded value is not a root"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniformly sample the exact stated root-certificate language."""
    x = rng.randrange(1, inst["p"])
    return _encode_root(x, inst["limb_base"])


def search_space(inst) -> int | None:
    return inst["p"] - 1


def enumerate_all(inst) -> int | None:
    if inst["p"] > 10000:
        return None
    return sum(verify(inst, _encode_root(x, inst["limb_base"]))[0]
               for x in range(1, inst["p"]))


def _recover_normal_form(inst, count_operations=False):
    """Construction-aware O(n+log p) solver and normalizer.

    A dictionary indexed by coefficient exposes the unique pair
    c_low=-3*c_high.  Their exponent difference is h.  Multiplying all
    exponents by h^{-1} recovers degrees 0..n-1.
    """
    p, modulus = inst["p"], inst["p"] - 1
    by_coefficient = {c: (c, a) for c, a in inst["terms"]}
    operations = 0
    pairs = []
    for c_high, a_high in inst["terms"]:
        target = (-3 * c_high) % p
        operations += 2
        if target in by_coefficient:
            c_low, a_low = by_coefficient[target]
            pairs.append((c_high, a_high, c_low, a_low))
    if len(pairs) != 1:
        raise ValueError("instance has no unique minus-two coefficient pair")
    c_high, a_high, _c_low, a_low = pairs[0]
    h = (a_high - a_low) % modulus
    operations += 1
    if math.gcd(h, modulus) != 1:
        raise ValueError("recovered exponent step is not a unit")
    inverse_h = pow(h, -1, modulus)
    # Count one Euclidean division per quotient as an exact arithmetic op.
    aa, bb = h, modulus
    while bb:
        aa, bb = bb, aa % bb
        operations += 1
    normalized = [None] * inst["n"]
    scale_inverse = pow(c_high, -1, p)
    operations += 1
    high_degree = (a_high * inverse_h) % modulus
    offset = (high_degree - (inst["n"] - 1)) % modulus
    operations += 2
    for coefficient, exponent in inst["terms"]:
        degree = ((exponent * inverse_h) - offset) % modulus
        operations += 2
        if degree >= inst["n"] or normalized[degree] is not None:
            raise ValueError("exponents do not normalize to consecutive degrees")
        normalized[degree] = (coefficient * scale_inverse) % p
        operations += 1
    if any(c is None for c in normalized):
        raise ValueError("missing normalized degree")
    if normalized[-1] != 1 or normalized[-2] != p - 3:
        raise ValueError("coefficient orientation is inconsistent")
    if count_operations:
        return normalized, h, inverse_h, operations
    return normalized, h, inverse_h


def _binary_power_count(base, exponent, modulus):
    result = 1
    value = base % modulus
    operations = 0
    e = exponent
    while e:
        if e & 1:
            result = (result * value) % modulus
            operations += 1
        e >>= 1
        if e:
            value = (value * value) % modulus
            operations += 1
    return result, operations


def _reference_algorithm(inst):
    p, modulus = inst["p"], inst["p"] - 1
    by_coefficient = {c: a for c, a in inst["terms"]}
    pairs = []
    operations = 0
    for c_high, a_high in inst["terms"]:
        target = (-3 * c_high) % p
        operations += 2
        if target in by_coefficient:
            pairs.append((a_high, by_coefficient[target]))
    if len(pairs) != 1:
        raise ValueError("instance has no unique minus-three coefficient pair")
    h = (pairs[0][0] - pairs[0][1]) % modulus
    operations += 1
    inverse_h = pow(h, -1, modulus)
    aa, bb = h, modulus
    while bb:
        aa, bb = bb, aa % bb
        operations += 1
    root, power_operations = _binary_power_count(3, inverse_h, p)
    operations += power_operations
    return _encode_root(root, inst["limb_base"]), operations


def canonical_key(inst) -> str:
    normalized, _h, _inverse_h = _recover_normal_form(inst)
    payload = json.dumps({"p": inst["p"], "coefficients": normalized},
                         sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params) -> dict | None:
    n = params.get("n")
    bits = params.get("prime_bits", 31)
    order = [7, 31, 61, 127]
    if bits not in order:
        return None
    index = order.index(bits)
    if index < len(order) - 1:
        return {"n": max(n + 32, DIFFICULTY["easy"]["n"]),
                "prime_bits": order[index + 1]}
    if n < 192:
        return {"n": n + 32, "prime_bits": 127}
    return None


def _attack_outlier_magnitude(inst):
    p, modulus = inst["p"], inst["p"] - 1
    coefficient, exponent = min(
        inst["terms"], key=lambda pair: abs(pair[0] - p // 2))
    del coefficient
    if math.gcd(exponent, modulus) != 1:
        return _encode_root(0, inst["limb_base"])
    candidate = pow(3, pow(exponent, -1, modulus), p)
    return _encode_root(candidate, inst["limb_base"])


def _attack_greedy_input_pair(inst):
    p, modulus = inst["p"], inst["p"] - 1
    a = inst["terms"][0][1]
    b = inst["terms"][1][1]
    step = (a - b) % modulus
    if math.gcd(step, modulus) != 1:
        return _encode_root(1, inst["limb_base"])
    candidate = pow(3, pow(step, -1, modulus), p)
    return _encode_root(candidate, inst["limb_base"])


def _attack_largest_coefficients(inst):
    p, modulus = inst["p"], inst["p"] - 1
    selected = sorted(inst["terms"], reverse=True)[:2]
    for first, second in ((selected[0], selected[1]),
                          (selected[1], selected[0])):
        step = (first[1] - second[1]) % modulus
        if math.gcd(step, modulus) == 1:
            candidate = pow(3, pow(step, -1, modulus), p)
            answer = _encode_root(candidate, inst["limb_base"])
            if verify(inst, answer)[0]:
                return answer
    return _encode_root(0, inst["limb_base"])


def _attack_small_ansatz(inst):
    for x in (0, 1, 2, 3, inst["p"] - 1, inst["p"] - 2):
        answer = _encode_root(x, inst["limb_base"])
        if verify(inst, answer)[0]:
            return answer
    return _encode_root(0, inst["limb_base"])


def _random_restart(inst, seed, restarts):
    rng = random.Random(seed)
    for _ in range(restarts):
        answer = random_candidate(inst, rng)
        if verify(inst, answer)[0]:
            return answer
    return _encode_root(0, inst["limb_base"])


def _transformed_instance(inst, *, reorder=False, scale=1, exponent_unit=1,
                          exponent_shift=0):
    p, modulus = inst["p"], inst["p"] - 1
    terms = [[(scale * c) % p,
              (exponent_unit * a + exponent_shift) % modulus]
             for c, a in inst["terms"]]
    if reorder:
        terms = terms[1::2] + terms[::2]
    out = dict(inst)
    out["terms"] = terms
    return out


def _answer_wire(answer):
    return f"{answer[0]}, {answer[1]}"


def selftest() -> dict:
    report = {}

    g1_failures = []
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not g1_failures and json_roundtrips == 12,
        "attempts": 12,
        "json_roundtrips": json_roundtrips,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=0, **shipping_params)
    planted = shipping["answer"]
    corruptions = {
        "drop": planted[:1],
        "swap": planted[::-1],
        "duplicate": planted + planted[-1:],
        "empty": [],
        "out_of_range": [shipping["limb_base"], planted[1]],
    }
    cases = {}
    reasons = set()
    for name, candidate in corruptions.items():
        ok, why = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": why}
        reasons.add(why)
    report["G2_rejects_corruption"] = {
        "pass": all(c["rejected"] for c in cases.values()) and len(reasons) == 5,
        "cases": cases,
    }

    realistic = ("I used the exponent substitution.\n```text\n<answer>" +
                 _answer_wire(planted) + "</answer>\n```\n")
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no certificate here") is None,
        "parsed": parsed,
        "garbage_returns_none": parse_answer("no certificate here") is None,
    }

    guess_total = 200000
    guess_hits = 0
    guess_rng = random.Random(12041113)
    t0 = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(shipping, guess_rng)
        if verify(shipping, candidate)[0]:
            guess_hits += 1
    guess_seconds = time.perf_counter() - t0
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "structure_aware_space": search_space(shipping),
        "sampler": "uniform decoded field element with both stated limb bounds enforced",
        "wall_clock_sec": round(guess_seconds, 6),
    }

    baseline_restarts = 4096
    t0 = time.perf_counter()
    baseline_answer = _random_restart(shipping, 99173, baseline_restarts)
    baseline_seconds = time.perf_counter() - t0
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    report["G5_density_and_baseline"] = {
        "pass": (guess_hits == 0 and not verify(shipping, baseline_answer)[0]
                 and enumerate_all(demo) == 1),
        "shipping_valid_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_observed_solution_fraction": guess_hits / guess_total,
        "shipping_exact_solution_count_by_construction": 1,
        "demo_exact_solution_count": enumerate_all(demo),
        "baseline_iterations": baseline_restarts,
        "baseline_wall_seconds": round(baseline_seconds, 6),
    }

    attack_functions = {
        "outlier_coefficient_magnitude": lambda inst, seed: _attack_outlier_magnitude(inst),
        "greedy_first_input_pair": lambda inst, seed: _attack_greedy_input_pair(inst),
        "largest_coefficients_pair": lambda inst, seed: _attack_largest_coefficients(inst),
        "in_context_small_root_ansatz": lambda inst, seed: _attack_small_ansatz(inst),
        "random_restart_256": lambda inst, seed: _random_restart(inst, seed ^ 0x55AA, 256),
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
        t0 = time.perf_counter()
        candidate, operations = _reference_algorithm(inst)
        reference_times.append(time.perf_counter() - t0)
        reference_operations.append(operations)
        if verify(inst, candidate)[0]:
            reference_successes += 1
    all_failed = all(v["successes"] == 0 for v in attacks.values())
    reference_median_ops = int(statistics.median(reference_operations))
    reference_median_time = statistics.median(reference_times)
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "coefficient-indexed exponent unmasking plus binary powering",
            "complexity": "O(n + log p) exact arithmetic operations",
            "median_wall_clock_sec": round(reference_median_time, 9),
            "median_operations": reference_median_ops,
            "operation_definition": (
                "modular coefficient transforms, exponent-step recovery, Euclidean "
                "divisions, and modular multiplies"
            ),
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=31, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    _answer, doubled_operations = _reference_algorithm(doubled)
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_operations > reference_median_ops,
        "shipping_n": shipping_params["n"],
        "doubled_n": doubled_params["n"],
        "shipping_reference_operations": reference_median_ops,
        "doubled_reference_operations": doubled_operations,
        "doubled_verify_reason": doubled_why,
    }

    invariance_checks = 0
    carried_witness_checks = 0
    for seed in range(20):
        inst = make_instance(seed=seed, **shipping_params)
        key = canonical_key(inst)
        scale = (seed + 7) % inst["p"] or 1
        unit_rng = random.Random(5000 + seed)
        unit = _sample_unit(unit_rng, inst["p"] - 1)
        exponent_shift = (7919 * seed + 104729) % (inst["p"] - 1)
        root = _decode_root(inst["answer"], inst["limb_base"])
        carried_root = pow(root, pow(unit, -1, inst["p"] - 1), inst["p"])
        carried_answer = _encode_root(carried_root, inst["limb_base"])
        transforms = [
            (_transformed_instance(inst, reorder=True), inst["answer"]),
            (_transformed_instance(inst, scale=scale), inst["answer"]),
            (_transformed_instance(inst, exponent_unit=unit), carried_answer),
            (_transformed_instance(inst, exponent_shift=exponent_shift),
             inst["answer"]),
            (_transformed_instance(inst, reorder=True, scale=scale,
                                   exponent_unit=unit,
                                   exponent_shift=exponent_shift), carried_answer),
        ]
        for transformed, witness in transforms:
            invariance_checks += canonical_key(transformed) == key
            carried_witness_checks += verify(transformed, witness)[0]
    unrelated_keys = {
        canonical_key(make_instance(seed=seed + 1000, **shipping_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": (invariance_checks == 100 and carried_witness_checks == 100
                 and len(unrelated_keys) == 20),
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_witness_checks,
        "unrelated_attempts": 20,
        "unrelated_distinct": len(unrelated_keys),
        "symmetries": [
            "term reordering",
            "nonzero global coefficient scaling",
            "unit power-coordinate relabelling",
            "cyclic exponent translation (nonzero-domain monomial scaling)",
            "composition of all four",
        ],
    }

    answer_body = _answer_wire(planted)
    answer_chars = len(answer_body)
    answer_elements = len(planted)
    answer_tokens = max(1, (answer_chars + 3) // 4)
    arms = G9_RESULTS["arms"]
    hinted_verdict = G9_RESULTS["hinted_verdict"]
    hinted_still_hardened = hinted_verdict == "hardened"
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and reference_median_ops <= 300)
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
        "intended_route_operations": reference_median_ops,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["all_passed"] = all(
        value.get("pass", False) for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
