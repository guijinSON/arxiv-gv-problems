"""Verified generator for arXiv:2511.13531.

The task uses the exact GF(2) anticommutation matrix in Theorem 8 / Appendix
A.3.  Instances are cyclic convolution operators with a polynomial divisor
chosen before the public mask is assembled, so a nonzero kernel certificate is
known by construction rather than found by solving the finished instance.
"""

from __future__ import annotations

import hashlib
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
except ImportError:  # The module remains standard-library-only.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "Pauli anticommutation matrix over GF(2)",
        "GF(2) kernel vector",
    ],
    "verification_operations": [
        "exact cyclic matrix-vector multiplication over GF(2)",
        "bitwise nonzero and dimension checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "The cyclic connection mask is an XOR-sum of translated copies of a "
        "short reciprocal factor; without recognizing that factor, one must "
        "perform exact finite-field elimination or a polynomial gcd."
    ),
    "hardness_basis": (
        "Track B: the standard circulant-matrix algorithm computes a polynomial "
        "gcd over GF(2) in O(n^2) coefficient operations (or Gaussian elimination "
        "in O(n^3)); at shipping n=510 it averages about 47,700 coefficient XORs "
        "and 0.00023 s here, "
        "while the reciprocal-mask route uses at most 300 exact operations."
    ),
    "max_answer_tokens": 44,
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
    "demo": {"n": 14, "degree": 3, "blocks": 0},
    "easy": {"n": 126, "degree": 6, "blocks": 2},
    "medium": {"n": 254, "degree": 7, "blocks": 3},
    "hard": {"n": 510, "degree": 8, "blocks": 4},
}
SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "One nonzero vector in GF(2)^n, encoded as a fixed-width little-bit-order "
        "hexadecimal string inside a three-field JSON object; all 2^n-1 nonzero "
        "vectors are candidates."
    ),
    "bounds": {
        "vectors": 1,
        "alphabet_size": 2,
        "shipping_dimension": 510,
        "json_scalar_fields": 3,
    },
}

STRUCTURAL_HINT = (
    "The connection mask is an XOR-superposition of translated copies of one "
    "short self-reciprocal polynomial."
)
PLACEBO_HINT = (
    "Keep careful track of the bit order and wraparound convention while checking "
    "each stated parity condition."
)

# Replaced with measured oracle results after the three harness runs.
G9_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

NOTES = (
    "Section II fixes the frustration pattern as the anticommutation relation of "
    "Pauli strings. Section IX.2, Theorem 8, proved in Appendix A.3, states that "
    "minimum Pauli-string length is rank_GF(2)(A)/2 and that the standard "
    "realization attains it. This identifies the easy mechanical route—exact "
    "rank elimination—so the family is Track B, not Track A. The generator first "
    "chooses a reciprocal factor q of x^n+1, sets h=(x^n+1)/q, and only then "
    "assembles a symmetric zero-diagonal mask from translated copies of q. "
    "Regularity defeats degree outliers; an antipodal offset defeats all-ones; "
    "random translated blocks defeat fixed short patterns; greedy syndrome "
    "descent and half-repeat restarts are measured explicitly."
)


# A primitive binary polynomial for each rung. Its reciprocal product is
# self-reciprocal and divides x^(2^degree-1)+1.
_PRIMITIVE = {
    3: 0b1011,       # x^3 + x + 1
    6: 0b1000011,    # fallback only; all factors are enumerated below
    7: 0b10000011,   # x^7 + x + 1
    8: 0x11D,        # x^8 + x^4 + x^3 + x^2 + 1
}


def _poly_degree(p: int) -> int:
    return p.bit_length() - 1


def _poly_mul(a: int, b: int) -> int:
    out = 0
    while b:
        if b & 1:
            out ^= a
        a <<= 1
        b >>= 1
    return out


def _poly_divmod(a: int, b: int) -> tuple[int, int]:
    if b <= 0:
        raise ZeroDivisionError("zero polynomial")
    quotient = 0
    db = _poly_degree(b)
    while a and _poly_degree(a) >= db:
        shift = _poly_degree(a) - db
        quotient ^= 1 << shift
        a ^= b << shift
    return quotient, a


def _poly_divmod_cost(a: int, b: int) -> tuple[int, int, int, int]:
    if b <= 0:
        raise ZeroDivisionError("zero polynomial")
    quotient = 0
    steps = 0
    coefficient_xors = 0
    db = _poly_degree(b)
    weight = b.bit_count()
    while a and _poly_degree(a) >= db:
        shift = _poly_degree(a) - db
        quotient ^= 1 << shift
        a ^= b << shift
        steps += 1
        coefficient_xors += weight
    return quotient, a, steps, coefficient_xors


def _poly_gcd(a: int, b: int) -> int:
    while b:
        _, remainder = _poly_divmod(a, b)
        a, b = b, remainder
    return a


def _poly_gcd_cost(a: int, b: int) -> tuple[int, int, int]:
    word_steps = 0
    coefficient_xors = 0
    while b:
        _, remainder, steps, xors = _poly_divmod_cost(a, b)
        word_steps += steps
        coefficient_xors += xors
        a, b = b, remainder
    return a, word_steps, coefficient_xors


def _reciprocal(p: int, degree: int) -> int:
    out = 0
    for i in range(degree + 1):
        if (p >> i) & 1:
            out |= 1 << (degree - i)
    return out


def _poly_mod_mul(a: int, b: int, modulus: int) -> int:
    return _poly_divmod(_poly_mul(a, b), modulus)[1]


def _is_irreducible(p: int, degree: int) -> bool:
    """Rabin's GF(2) irreducibility test at these tiny degrees."""
    x = 0b10
    power = x
    for _ in range(1, degree // 2 + 1):
        power = _poly_mod_mul(power, power, p)
        if _poly_gcd(power ^ x, p) != 1:
            return False
    power = x
    for _ in range(degree):
        power = _poly_mod_mul(power, power, p)
    return power == x


def _reciprocal_factors(degree: int) -> list[int]:
    """Products p*p* for non-self-reciprocal irreducibles of given degree."""
    if degree not in _PRIMITIVE:
        raise ValueError("degree must be one of 3, 6, 7, 8")
    irreducibles = []
    for low in range(1, 1 << degree, 2):
        p = (1 << degree) | low
        if _is_irreducible(p, degree):
            irreducibles.append(p)
    seen = set()
    factors = []
    for p in irreducibles:
        if p in seen:
            continue
        reciprocal = _reciprocal(p, degree)
        seen.update((p, reciprocal))
        if reciprocal == p:
            continue
        factors.append(_poly_mul(p, reciprocal))
    if not factors:
        raise AssertionError("no reciprocal factor pairs found")
    return sorted(set(factors))


def _connection_mask(inst: dict) -> int:
    mask = 0
    for offset in inst["connection_offsets"]:
        mask |= 1 << offset
    return mask


def _hex_width(n: int) -> int:
    return (n + 3) // 4


def _answer_object(n: int, vector: int) -> dict:
    return {
        "encoding": "hex-lsb0",
        "n": n,
        "vector": "0x" + format(vector, f"0{_hex_width(n)}x"),
    }


def _select_shifts(n: int, degree: int, blocks: int,
                   rng: random.Random) -> list[int]:
    half = n // 2
    q_degree = 2 * degree
    upper = half - 3 * degree - 1
    if blocks == 0:
        return []
    candidates = list(range(1, upper + 1))
    rng.shuffle(candidates)
    selected: list[int] = []
    separation = q_degree + 2
    for shift in candidates:
        if all(abs(shift - old) >= separation for old in selected):
            selected.append(shift)
            if len(selected) == blocks:
                return sorted(selected)
    raise ValueError("too many translated blocks for n and degree")


def make_instance(n: int, seed: int = 0, degree: int = 8,
                  blocks: int = 8, **params) -> dict:
    """Build an exact cyclic operator with a known kernel certificate."""
    del params
    if isinstance(n, bool) or not isinstance(n, int) or n < 6:
        raise ValueError("n must be an integer at least 6")
    if n % 2:
        raise ValueError("n must be even")
    if isinstance(blocks, bool) or not isinstance(blocks, int) or blocks < 0:
        raise ValueError("blocks must be a nonnegative integer")
    period = (1 << degree) - 1
    if n % period:
        raise ValueError("n must be a multiple of 2^degree-1")

    rng = random.Random(seed)
    factors = _reciprocal_factors(degree)
    q = factors[rng.randrange(len(factors))]
    modulus = (1 << n) | 1
    h, remainder = _poly_divmod(modulus, q)
    if remainder:
        raise AssertionError("internal primitive factor does not divide modulus")

    half = n // 2
    mask = q << (half - degree)
    shifts = _select_shifts(n, degree, blocks, rng)
    q_degree = 2 * degree
    for shift in shifts:
        mask ^= q << shift
        mask ^= q << (n - shift - q_degree)

    if mask & 1:
        raise AssertionError("connection mask has a forbidden diagonal term")
    if not all(((mask >> k) & 1) == ((mask >> (n - k)) & 1)
               for k in range(1, n)):
        raise AssertionError("connection mask is not symmetric")
    if not ((mask >> half) & 1):
        raise AssertionError("antipodal connection was lost")

    offsets = [k for k in range(1, n) if (mask >> k) & 1]
    return {
        "family": "cyclic_pauli_anticommutation_kernel_v1",
        "n": n,
        "connection_offsets": offsets,
        "answer": _answer_object(n, h),
    }


def render(inst: dict) -> str:
    n = inst["n"]
    width = _hex_width(n)
    offsets = ", ".join(str(x) for x in inst["connection_offsets"])
    mode = os.environ.get("GV_HINT_MODE")
    hint = ""
    if mode == "structural":
        hint = "\n\nStructural hint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        hint = "\n\nHint: " + PLACEBO_HINT
    example_vector = "0x" + "0" * (width - 1) + "1"
    return f"""Pauli anticommutation dependency over GF(2)

Work over the two-element field GF(2), where addition is XOR. There are {n}
row/column coordinates numbered 0 through {n - 1}. Define a symmetric binary
matrix A with zero diagonal by

    A[i,j] = 1 exactly when (j-i) modulo {n} belongs to D,

where

    D = [{offsets}].

Find any nonzero vector v in GF(2)^{n} such that A v = 0. Equivalently, for
every i from 0 through {n - 1}, the XOR of v[(i+d) modulo {n}] over all d in D
must be zero.

Encode v as one hexadecimal integer with exactly {width} lowercase hex digits
after 0x. Bit i (the coefficient of 2^i, with bit 0 least significant) is v[i].
The vector must be nonzero; the {4 * width - n} unused high bit(s), if any, must
be zero. Return a JSON object with exactly "encoding", "n", and "vector".{hint}

Give your final answer inside <answer></answer> tags, as the exact JSON object.
Example: <answer>{{"encoding":"hex-lsb0","n":{n},"vector":"{example_vector}"}}</answer>
Output nothing else inside the tags."""


def parse_answer(text: str):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body)
    try:
        return json.loads(body)
    except (TypeError, ValueError):
        return None


def _parse_vector(inst: dict, answer) -> tuple[int | None, str]:
    if not isinstance(answer, dict):
        return None, "answer must be a JSON object"
    if not answer:
        return None, "answer object is empty"
    if set(answer) != {"encoding", "n", "vector"}:
        return None, "answer must have exactly encoding, n, and vector fields"
    if answer["encoding"] != "hex-lsb0":
        return None, "encoding must be 'hex-lsb0'"
    if isinstance(answer["n"], bool) or not isinstance(answer["n"], int) \
            or answer["n"] != inst["n"]:
        return None, "declared vector length does not match instance n"
    vector = answer["vector"]
    if not isinstance(vector, str) or not vector.startswith("0x"):
        return None, "vector must be a hexadecimal string beginning with 0x"
    digits = vector[2:]
    if len(digits) != _hex_width(inst["n"]):
        return None, "hex vector has wrong fixed width"
    if not re.fullmatch(r"[0-9a-f]+", digits):
        return None, "hex vector contains a non-lowercase-hexadecimal digit"
    bits = int(digits, 16)
    if bits >> inst["n"]:
        return None, "unused high bits must be zero"
    if bits == 0:
        return None, "vector must be nonzero"
    return bits, "ok"


def _rotate_right(mask: int, shift: int, n: int) -> int:
    shift %= n
    if shift == 0:
        return mask
    low = mask & ((1 << shift) - 1)
    return (mask >> shift) | (low << (n - shift))


def _kernel_syndrome(inst: dict, vector: int) -> int:
    syndrome = 0
    n = inst["n"]
    for offset in inst["connection_offsets"]:
        syndrome ^= _rotate_right(vector, offset, n)
    return syndrome


def verify(inst: dict, answer) -> tuple[bool, str]:
    bits, reason = _parse_vector(inst, answer)
    if bits is None:
        return False, reason
    if _kernel_syndrome(inst, bits) != 0:
        return False, "vector is not in the GF(2) kernel of the stated matrix"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random):
    n = inst["n"]
    return _answer_object(n, rng.randrange(1, 1 << n))


def search_space(inst: dict) -> int:
    return (1 << inst["n"]) - 1


def enumerate_all(inst: dict):
    if search_space(inst) > 20000:
        return None
    return sum(_kernel_syndrome(inst, bits) == 0
               for bits in range(1, 1 << inst["n"]))


def _unit_multipliers(n: int) -> list[int]:
    return [u for u in range(1, n) if math.gcd(u, n) == 1]


def canonical_key(inst: dict) -> str:
    n = inst["n"]
    offsets = inst["connection_offsets"]
    candidates = []
    for unit in _unit_multipliers(n):
        value = 0
        for d in offsets:
            value |= 1 << ((unit * d) % n)
        candidates.append(value)
    payload = f"{n}:{min(candidates):x}".encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def escalate(params: dict):
    p = {k: v for k, v in params.items() if k != "_preset"}
    next_n = int(p["n"]) * 2
    next_blocks = int(p.get("blocks", 0)) + 4
    if _hex_width(next_n) + 90 > 2000:
        return "cap_bound"
    p["n"] = next_n
    p["blocks"] = next_blocks
    return p


def _carried_answer(answer: dict, n: int, unit: int, shift: int) -> dict:
    old = int(answer["vector"][2:], 16)
    new = 0
    for coordinate in range(n):
        if (old >> coordinate) & 1:
            new_coordinate = (unit * coordinate + shift) % n
            new |= 1 << new_coordinate
    return _answer_object(n, new)


def _affine_transform(inst: dict, unit: int, shift: int) -> tuple[dict, dict]:
    n = inst["n"]
    carried = _carried_answer(inst["answer"], n, unit, shift)
    transformed = {
        "family": inst["family"],
        "n": n,
        "connection_offsets": sorted(
            {(unit * d) % n for d in inst["connection_offsets"]}
        ),
        "answer": carried,
    }
    return transformed, carried


def _candidate_ok(inst: dict, bits: int | None) -> bool:
    return bool(bits) and _kernel_syndrome(inst, bits) == 0


def _attack_outlier_degree(inst: dict, rng: random.Random):
    del rng
    # Every coordinate has equal row weight, so a degree-only support is all ones.
    return (1 << inst["n"]) - 1, 1


def _attack_random_restart(inst: dict, rng: random.Random, restarts: int = 256):
    for attempt in range(1, restarts + 1):
        bits = rng.randrange(1, 1 << inst["n"])
        if _candidate_ok(inst, bits):
            return bits, attempt
    return None, restarts


def _attack_short_patterns(inst: dict, rng: random.Random):
    del rng
    n = inst["n"]
    candidates = [1, (1 << n) - 1, (1 << (n // 2)) - 1,
                  _connection_mask(inst)]
    for period in range(2, min(16, n) + 1):
        for residue in range(period):
            bits = 0
            for i in range(residue, n, period):
                bits |= 1 << i
            candidates.append(bits)
    tested = 0
    seen = set()
    for bits in candidates:
        bits &= (1 << n) - 1
        if not bits or bits in seen:
            continue
        seen.add(bits)
        tested += 1
        if _candidate_ok(inst, bits):
            return bits, tested
    return None, tested


def _attack_half_repeat(inst: dict, rng: random.Random, restarts: int = 4096):
    n = inst["n"]
    half = n // 2
    for attempt in range(1, restarts + 1):
        lower = rng.randrange(1, 1 << half)
        bits = lower | (lower << half)
        if _candidate_ok(inst, bits):
            return bits, attempt
    return None, restarts


def _attack_greedy_descent(inst: dict, rng: random.Random,
                           restarts: int = 3, max_steps: int = 32):
    n = inst["n"]
    base = _connection_mask(inst)
    columns = [_rotate_right(base, j, n) for j in range(n)]
    evaluations = 0
    for _ in range(restarts):
        bits = rng.randrange(1, 1 << n)
        syndrome = _kernel_syndrome(inst, bits)
        for _step in range(max_steps):
            if syndrome == 0:
                if bits:
                    return bits, evaluations
                break
            current = syndrome.bit_count()
            best_weight = current
            best_j = None
            for j, column in enumerate(columns):
                weight = (syndrome ^ column).bit_count()
                evaluations += 1
                if weight < best_weight:
                    best_weight = weight
                    best_j = j
            if best_j is None:
                break
            bits ^= 1 << best_j
            syndrome ^= columns[best_j]
    return None, evaluations


def _reference_algorithm(inst: dict):
    """Exact circulant method: polynomial gcd followed by an annihilator."""
    n = inst["n"]
    a = _connection_mask(inst)
    modulus = (1 << n) | 1
    t0 = time.perf_counter()
    gcd_poly, word_steps, coefficient_xors = _poly_gcd_cost(a, modulus)
    vector, remainder = _poly_divmod(modulus, gcd_poly)
    elapsed = time.perf_counter() - t0
    if remainder:
        raise AssertionError("gcd did not divide modulus")
    return vector, elapsed, word_steps, coefficient_xors


def _answer_atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _sample_guess_rate(inst: dict, samples: int, seed: int):
    rng = random.Random(seed)
    hits = 0
    for _ in range(samples):
        candidate = random_candidate(inst, rng)
        bits = int(candidate["vector"][2:], 16)
        if _candidate_ok(inst, bits):
            hits += 1
    return hits


def selftest() -> dict:
    report = {}

    preset_checks = 0
    json_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 101):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError(f"G1 {preset}/{seed}: {why}")
            preset_checks += 1
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                raise AssertionError("answer is not JSON-native")
            json_checks += 1
    report["G1_planted_verifies"] = {
        "pass": True,
        "preset_seed_checks": preset_checks,
        "json_native_checks": json_checks,
    }

    ship = make_instance(seed=20250905, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = ship["answer"]
    corruptions = {
        "drop_one_field": {"encoding": planted["encoding"], "n": planted["n"]},
        "swap_one_label": {**planted, "encoding": "lsb0-hex"},
        "duplicate_vector": {**planted, "vector": [planted["vector"], planted["vector"]]},
        "empty": {},
        "out_of_range_length": {**planted, "n": planted["n"] + 1},
    }
    reasons = {}
    for name, candidate in corruptions.items():
        ok, why = verify(ship, candidate)
        if ok:
            raise AssertionError(f"G2 accepted {name}")
        reasons[name] = why
    planted_bits = int(planted["vector"][2:], 16)
    flipped = _answer_object(ship["n"], planted_bits ^ 1)
    ok, why = verify(ship, flipped)
    if ok:
        raise AssertionError("G2 accepted a flipped certificate")
    reasons["flipped_bit"] = why
    report["G2_rejects_corruption"] = {
        "pass": len(set(reasons.values())) == len(reasons),
        "corruptions_rejected": len(reasons),
        "distinct_reasons": len(set(reasons.values())),
        "reasons": reasons,
    }

    response = (
        "I used cyclic parity.\n```text\n<answer>"
        + json.dumps(planted, separators=(",", ":"))
        + "</answer>\n```\nThat is my final result."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted and verify(ship, parsed)[0],
        "realistic_response_parsed": parsed == planted,
    }

    samples = 200_000
    t0 = time.perf_counter()
    hits = _sample_guess_rate(ship, samples, 884422)
    guess_seconds = time.perf_counter() - t0
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "sampling_wall_seconds": round(guess_seconds, 6),
        "candidate_space_bits": ship["n"],
    }

    mask = _connection_mask(ship)
    modulus = (1 << ship["n"]) | 1
    nullity = _poly_degree(_poly_gcd(mask, modulus))
    exact_valid = (1 << nullity) - 1
    exact_space = search_space(ship)
    attack_rng = random.Random(314159)
    t0 = time.perf_counter()
    _, greedy_evaluations = _attack_greedy_descent(ship, attack_rng)
    baseline_seconds = time.perf_counter() - t0
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": hits / samples < 1e-6 and baseline_seconds >= 0.0,
        "shipping_sample_hits": hits,
        "shipping_sample_total": samples,
        "shipping_sample_density": hits / samples,
        "shipping_exact_nullity": nullity,
        "shipping_exact_valid_count": exact_valid,
        "shipping_exact_density": exact_valid / exact_space,
        "demo_exact_valid_count": demo_count,
        "baseline_wall_seconds": round(baseline_seconds, 6),
        "baseline_iterations": greedy_evaluations,
    }

    attacks = {
        "outlier_equal_degree": _attack_outlier_degree,
        "greedy_syndrome_descent": _attack_greedy_descent,
        "random_restart_256": _attack_random_restart,
        "short_period_ansatz": _attack_short_patterns,
        "half_repeat_random_4096": _attack_half_repeat,
    }
    attack_report = {}
    for name, attack in attacks.items():
        successes = 0
        total_work = 0
        t0 = time.perf_counter()
        for seed in range(8):
            inst = make_instance(seed=7000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
            candidate, work = attack(inst, random.Random(90000 + seed))
            total_work += work
            if candidate is not None and _candidate_ok(inst, candidate):
                successes += 1
        attack_report[name] = {
            "successes": successes,
            "attempts": 8,
            "total_work": total_work,
            "wall_seconds": round(time.perf_counter() - t0, 6),
        }

    reference_successes = 0
    reference_seconds = 0.0
    reference_word_steps = 0
    reference_coefficient_xors = 0
    for seed in range(8):
        inst = make_instance(seed=8100 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        vector, elapsed, steps, xors = _reference_algorithm(inst)
        reference_seconds += elapsed
        reference_word_steps += steps
        reference_coefficient_xors += xors
        if _candidate_ok(inst, vector):
            reference_successes += 1
    all_failed = all(item["successes"] == 0 for item in attack_report.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and len(attack_report) >= 4 and reference_successes == 8,
        "attacks": attack_report,
        "reference_algorithm": {
            "name": "Euclidean polynomial gcd for a circulant GF(2) matrix",
            "complexity": "O(n^2) GF(2) coefficient operations",
            "wall_clock_sec": round(reference_seconds, 6),
            "mean_wall_clock_sec": round(reference_seconds / 8, 6),
            "word_xor_steps": reference_word_steps,
            "coefficient_xors": reference_coefficient_xors,
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled_params["blocks"] += 4
    doubled = make_instance(seed=12345, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(ship),
        "shipping_n": ship["n"],
        "doubled_n": doubled["n"],
        "candidate_space_exponent_increase": doubled["n"] - ship["n"],
        "doubled_verify_reason": doubled_why,
    }

    invariance_checks = 0
    carried_checks = 0
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(seed=12000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        base_key = canonical_key(inst)
        unrelated_keys.append(base_key)

        reordered = dict(inst)
        reordered["connection_offsets"] = list(reversed(inst["connection_offsets"]))
        if canonical_key(reordered) != base_key:
            raise AssertionError("canonical key depends on offset order")
        invariance_checks += 1

        units = _unit_multipliers(inst["n"])
        unit = units[(17 * seed + 3) % len(units)]
        shift = (29 * seed + 11) % inst["n"]
        for u, s in ((unit, 0), (1, shift), (unit, shift)):
            transformed, carried = _affine_transform(inst, u, s)
            if canonical_key(transformed) != base_key:
                raise AssertionError("canonical key is not affine invariant")
            invariance_checks += 1
            ok, why = verify(transformed, carried)
            if not ok:
                raise AssertionError(f"affine map did not preserve problem: {why}")
            carried_checks += 1
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariance_checks == 80 and carried_checks == 60 and distinct == 20,
        "invariance_checks": invariance_checks,
        "real_transformation_checks": carried_checks,
        "unrelated_distinct_keys": distinct,
        "unrelated_attempts": 20,
    }

    answer_blob = json.dumps(ship["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(ship["answer"])
    degree = DIFFICULTY[SHIPPING_DIFFICULTY]["degree"]
    planted_vector = int(ship["answer"]["vector"][2:], 16)
    q, factor_remainder = _poly_divmod((1 << ship["n"]) | 1, planted_vector)
    if factor_remainder:
        raise AssertionError("planted vector does not expose its construction factor")
    half_modulus = (1 << ((1 << degree) - 1)) | 1
    quotient, remainder = _poly_divmod(half_modulus, q)
    if remainder:
        raise AssertionError("compact-route factor arithmetic failed")
    route_operations = (len(ship["connection_offsets"]) + (2 * degree + 1)
                        + quotient.bit_count() + 1)
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and route_operations <= 300)
    arms = {
        key: dict(G9_RESULTS[key]) for key in ("bare", "hinted", "placebo")
    }
    hinted_attempts = arms["hinted"]["attempts"]
    hinted_still_hardened = (
        G9_RESULTS["hinted_verdict"] == "hardened"
        and hinted_attempts > 0
        and arms["hinted"]["solved"] == 0
    )
    hinted_rate = (arms["hinted"]["solved"] / hinted_attempts
                   if hinted_attempts else 0.0)
    placebo_attempts = arms["placebo"]["attempts"]
    placebo_rate = (arms["placebo"]["solved"] / placebo_attempts
                    if placebo_attempts else 0.0)
    report["G9_no_tool_suitability"] = {
        "pass": hinted_still_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": route_operations,
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
