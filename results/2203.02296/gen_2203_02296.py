"""Verified generator for paired prime/cube/power-of-two representations.

This is a bounded symmetric subfamily of equation (1.7) in Xin Chen,
arXiv:2203.02296.  Instances are made by inverse generation.  The module never
solves a target in order to obtain its planted certificate.
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


# Make the repository helpers importable when harden.py runs from this folder.
# This family only needs the standard library, so the fallback is complete.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - supported fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "number_theory",
    "object_regime": "integer_lattice",
    "computational_core": "other",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "pair of positive odd integer targets",
        "primes in symmetric three-term arithmetic progressions",
        "power-of-two exponent with an exact multiplicity",
    ],
    "verification_operations": [
        "deterministic integer primality testing",
        "exact integer cubing and exponentiation",
        "exact substitution into both Diophantine equations",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "After removing the shared high power of two, both residues have the "
        "same hidden linear prime factor; without seeing that invariant one "
        "must scan the bounded prime parameter."
    ),
    "hardness_basis": (
        "Track B: the definition-driven bounded divisor scan is O(n) exact "
        "arithmetic and at shipping n=6,000,000 averaged 1,687,770 exact "
        "operations and 1.09 seconds in the latest eight-seed run, while the "
        "common-factor route takes at most 76 exact operations."
    ),
    "max_answer_tokens": 6,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "One JSON array [q,j1,j2,e] of four base-10 integers.  q is prime in "
        "the printed inclusive q interval; j1 and j2 are ordered choices from "
        "the printed consecutive index set (repetition forbidden), each "
        "derived q-a and q+a is prime, and the two printed algebraic cofactors "
        "are coprime; e is in the printed inclusive exponent interval.  The "
        "array is an exact symbolic expansion of the ten prime variables and "
        "k identical powers 2^e."
    ),
    "bounds": {
        "answer_integers": 4,
        "q_interval": "[q_min,q_max] inclusive",
        "offset_indices": "j_start through j_start+offset_count-1",
        "indices_ordered": True,
        "index_repetition_allowed": False,
        "cofactor_gcd": 1,
        "exponent_slots_max_shipping": 256,
        "power_multiplicity_shipping": 231,
    },
}

DIFFICULTY: dict = {
    "demo": {
        "n": 50, "offset_count": 8, "offset_scale": 16,
        "k": 5, "power_slots": 8,
    },
    "easy": {
        "n": 10_000, "offset_count": 24, "offset_scale": 48,
        "k": 231, "power_slots": 64,
    },
    "medium": {
        "n": 200_000, "offset_count": 40, "offset_scale": 80,
        "k": 231, "power_slots": 128,
    },
    "hard": {
        "n": 6_000_000, "offset_count": 64, "offset_scale": 128,
        "k": 231, "power_slots": 256,
    },
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The two residues modulo 2^B share the linear prime as a common factor."
)
PLACEBO_HINT = (
    "The two equations and their inclusive bounds reward especially careful checking."
)

# Filled from script-owned runs after hardening.  Zero-attempt entries are
# honest placeholders during local gate development, not oracle evidence.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

NOTES = r"""
Paper triage.  Section 1, equation (1.7), fixes the simultaneous object: each
odd target is one prime plus four prime cubes plus the SAME k powers of two.
Theorem 1.1 proves existence for k=231 and sufficiently large comparable odd
targets.  Section 2 defines the prime ranges and the common power sum used by
the circle method, and Section 3 obtains only the nonconstructive inequality
R(N1,N2)>0.  The paper gives neither an effective size threshold nor an
algorithm that outputs a representation.  Its theorem therefore does not
produce this module's certificates, and it supplies no distributional hardness
claim.  Those facts rule out pretending that Theorem 1.1 supports Track A.

Construction.  Pick two distinct, ordered symmetric prime progressions whose
displayed cofactors are coprime, together with one exponent e, then set
N_i=q+2(q-a_i)^3+2(q+a_i)^3+k*2^e.  This is literally (1.7), allowing repeated
prime variables and repeated exponents as the paper does.  The certificate
[q,j1,j2,e] expands each row to the linear prime q, two copies of q-a_i, two
copies of q+a_i, and k copies of 2^e.  Targets are computed only after these
objects have been sampled.  Thus generation is inverse construction, not a
search on the emitted targets.

Track choice and easy route.  The symmetric identity
2(q-a)^3+2(q+a)^3=4q^3+12qa^2 makes each low residue equal to
q(4q^2+12a^2+1).  Plants are conditioned so the two displayed cofactors are
coprime, hence the gcd of the residues is q.  Exact division and an integer
square root recover each a, the public floor formula recovers each j, and the
remaining quotient recovers e.  A definition-driven scan over every allowed q
also solves all instances in O(n), so this is explicitly Track B.  The paper
does not discuss this deliberately restricted easy regime; it is introduced
to create a no-tool compression problem while staying in the native integer
equations.

Attacks.  Plants and random candidates use the same hierarchical prior: q is
uniform over eligible primes, the ordered coprime offset pair is uniform for
that q, and e is uniform in its interval.  The midpoint/outlier choice, a
cube-root approximation that ignores the unknown offset coefficient, 256
restarts, and a 64-candidate by-hand divisor window are run on eight shipping
seeds and must all fail.  The complete linear divisor scan is the Track B
reference algorithm and is reported separately because it is expected to
succeed.
""".strip()


_MR_BASES_64 = (2, 325, 9375, 28178, 450775, 9780504, 1795265022)
_SMALL_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
_PRIME_CACHE: dict[int, bool] = {}
_GROUP_CACHE: dict[tuple[int, int, int, int], tuple] = {}


def _is_prime(value: int) -> bool:
    """Deterministic Miller--Rabin for the unsigned 64-bit range."""
    cached = _PRIME_CACHE.get(value)
    if cached is not None:
        return cached
    if value < 2:
        return False
    for p in _SMALL_PRIMES:
        if value % p == 0:
            result = value == p
            if len(_PRIME_CACHE) < 500_000:
                _PRIME_CACHE[value] = result
            return result
    d, s = value - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    result = True
    for base in _MR_BASES_64:
        if base % value == 0:
            continue
        x = pow(base, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            result = False
            break
    if len(_PRIME_CACHE) < 500_000:
        _PRIME_CACHE[value] = result
    return result


def _validate_params(n: int, offset_count: int, offset_scale: int,
                     k: int, power_slots: int) -> None:
    vals = (n, offset_count, offset_scale, k, power_slots)
    if any(isinstance(x, bool) or not isinstance(x, int) for x in vals):
        raise ValueError("all parameters must be integers")
    if n < 50:
        raise ValueError("n must be at least 50")
    if offset_count < 2 or offset_scale <= offset_count:
        raise ValueError("need 2 <= offset_count < offset_scale")
    if k < 1 or power_slots < 2:
        raise ValueError("k must be positive and power_slots at least 2")
    j_start = offset_scale // 3
    if j_start + offset_count - 1 >= offset_scale:
        raise ValueError("the offset index interval must stay below offset_scale")
    qmax = 2 * n - 1
    amax = _offset(qmax, j_start + offset_count - 1, offset_scale)
    if qmax + amax >= 2**64:
        raise ValueError("prime candidates must remain below 2^64")


def _offset(q: int, j: int, scale: int) -> int:
    """The public even offset a_j(q)."""
    return 2 * ((j * q) // (2 * scale))


def _allowed_js_values(offset_count: int, offset_scale: int) -> range:
    start = offset_scale // 3
    return range(start, start + offset_count)


def _valid_js_trial(q: int, offset_count: int,
                    offset_scale: int) -> list[int]:
    js = []
    for j in _allowed_js_values(offset_count, offset_scale):
        a = _offset(q, j, offset_scale)
        if 0 < a < q and _is_prime(q - a) and _is_prime(q + a):
            js.append(j)
    return js


def _cofactor(q: int, a: int) -> int:
    return 4 * q * q + 12 * a * a + 1


def _row_low(q: int, j: int, scale: int) -> int:
    a = _offset(q, j, scale)
    return q * _cofactor(q, a)


def make_instance(n: int, seed: int = 0, offset_count: int = 64,
                  offset_scale: int = 128, k: int = 231,
                  power_slots: int = 256, **params) -> dict:
    """Inverse-generate a certified pair of native integer equations."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, offset_count, offset_scale, k, power_slots)
    rng = random.Random(seed)
    q_min, q_max = n, 2 * n - 1

    for _ in range(200_000):
        q = rng.randint(q_min, q_max)
        if not _is_prime(q):
            continue
        js = _valid_js_trial(q, offset_count, offset_scale)
        if len(js) < 2:
            continue
        pairs = []
        for j1 in js:
            a1 = _offset(q, j1, offset_scale)
            f1 = _cofactor(q, a1)
            for j2 in js:
                if j1 == j2:
                    continue
                a2 = _offset(q, j2, offset_scale)
                if math.gcd(f1, _cofactor(q, a2)) == 1:
                    pairs.append((j1, j2))
        if pairs:
            j1, j2 = rng.choice(pairs)
            break
    else:                                      # pragma: no cover - defensive
        raise RuntimeError("could not sample two certified prime progressions")

    low1 = _row_low(q, j1, offset_scale)
    low2 = _row_low(q, j2, offset_scale)
    low_bits = max(low1, low2).bit_length()
    e = low_bits + rng.randrange(power_slots)
    shared = k * (1 << e)
    inst = {
        "family": "paired_symmetric_prime_cubes_and_powers_of_two",
        "n": n,
        "q_min": q_min,
        "q_max": q_max,
        "offset_count": offset_count,
        "offset_scale": offset_scale,
        "j_start": offset_scale // 3,
        "k": k,
        "power_slots": power_slots,
        "low_bits": low_bits,
        "e_min": low_bits,
        "e_max": low_bits + power_slots - 1,
        "N1": low1 + shared,
        "N2": low2 + shared,
    }
    inst["answer"] = [q, j1, j2, e]
    return inst


def render(inst: dict) -> str:
    j_last = inst["j_start"] + inst["offset_count"] - 1
    text = "\n".join([
        "PAIRED PRIME-CUBE REPRESENTATION",
        "",
        "All quantities are ordinary nonnegative integers and every interval "
        "below is inclusive.  Repeated prime terms and repeated powers of two "
        "are allowed.",
        "",
        f"N1 = {inst['N1']}",
        f"N2 = {inst['N2']}",
        f"k = {inst['k']}",
        f"B = {inst['low_bits']}",
        f"q_min = {inst['q_min']}",
        f"q_max = {inst['q_max']}",
        f"j_start = {inst['j_start']}",
        f"j_last = {j_last}",
        f"offset_scale = {inst['offset_scale']}",
        f"e_min = {inst['e_min']}",
        f"e_max = {inst['e_max']}",
        "",
        "Find four integers q, j1, j2, e.  They must obey",
        "  q_min <= q <= q_max,",
        "  j_start <= j1,j2 <= j_last (order matters; j1 and j2 must differ),",
        "  e_min <= e <= e_max.",
        "For i=1,2 define exactly",
        "  a_i = 2 * floor(j_i*q / (2*offset_scale)).",
        "The three integers q-a_i, q, q+a_i must all be prime for each i.",
        "Also define c_i = 4*q^2 + 12*a_i^2 + 1; gcd(c_1,c_2) must equal 1.",
        "They must give the two exact identities",
        "  N1 = q + 2*(q-a_1)^3 + 2*(q+a_1)^3 + k*2^e,",
        "  N2 = q + 2*(q-a_2)^3 + 2*(q+a_2)^3 + k*2^e.",
        "Thus each row is one prime, four cubes of primes, and the same k "
        "powers of two: the four cube primes are two copies each of q-a_i "
        "and q+a_i, and all k power exponents equal e.",
        "",
        "Give your final answer inside <answer></answer> tags as the JSON array "
        "[q,j1,j2,e], using base-10 integers.",
        f"Example format: <answer>[{inst['q_min']},{inst['j_start']},"
        f"{inst['j_start'] + 1},{inst['e_min']}]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    if not blocks:
        return None
    body = blocks[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        lines = body.splitlines()
        if len(lines) >= 2:
            lines = lines[1:-1]
            body = "\n".join(lines).strip()
    try:
        return json.loads(body)
    except (TypeError, ValueError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list):
        return False, "answer must be one JSON array"
    if len(answer) < 4:
        return False, f"answer has too few entries: expected 4, got {len(answer)}"
    if len(answer) > 4:
        return False, f"answer has too many entries: expected 4, got {len(answer)}"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "all four answer entries must be integers"
    q, j1, j2, e = answer
    if not (inst["q_min"] <= q <= inst["q_max"]):
        return False, "q is outside the inclusive q interval"
    j_last = inst["j_start"] + inst["offset_count"] - 1
    if not (inst["j_start"] <= j1 <= j_last):
        return False, "j1 is outside the inclusive index interval"
    if not (inst["j_start"] <= j2 <= j_last):
        return False, "j2 is outside the inclusive index interval"
    if j1 == j2:
        return False, "j1 and j2 must be distinct"
    if not (inst["e_min"] <= e <= inst["e_max"]):
        return False, "e is outside the inclusive exponent interval"
    if not _is_prime(q):
        return False, "q is not prime"
    js = (j1, j2)
    for row, j in enumerate(js, 1):
        a = _offset(q, j, inst["offset_scale"])
        if not (0 < a < q):
            return False, f"row {row} has a nonpositive prime q-a"
        if not _is_prime(q - a):
            return False, f"row {row} lower symmetric term q-a is not prime"
        if not _is_prime(q + a):
            return False, f"row {row} upper symmetric term q+a is not prime"
    a1 = _offset(q, j1, inst["offset_scale"])
    a2 = _offset(q, j2, inst["offset_scale"])
    if math.gcd(_cofactor(q, a1), _cofactor(q, a2)) != 1:
        return False, "the two algebraic cofactors are not coprime"
    shared = inst["k"] * (1 << e)
    expected1 = _row_low(q, j1, inst["offset_scale"]) + shared
    if expected1 != inst["N1"]:
        return False, "first exact integer identity does not hold"
    expected2 = _row_low(q, j2, inst["offset_scale"]) + shared
    if expected2 != inst["N2"]:
        return False, "second exact integer identity does not hold"
    return True, "ok"


def _sieve(limit: int) -> bytearray:
    flags = bytearray(b"\x01") * (limit + 1)
    flags[0:2] = b"\x00\x00"
    for p in range(2, math.isqrt(limit) + 1):
        if flags[p]:
            start = p * p
            flags[start:limit + 1:p] = b"\x00" * (
                (limit - start) // p + 1
            )
    return flags


def _candidate_index(inst: dict) -> tuple[
        list[tuple[int, tuple[tuple[int, int], ...]]], int]:
    key = (inst["n"], inst["offset_count"], inst["offset_scale"],
           inst["j_start"])
    cached = _GROUP_CACHE.get(key)
    if cached is not None:
        return cached
    qmax = inst["q_max"]
    jlast = inst["j_start"] + inst["offset_count"] - 1
    limit = qmax + _offset(qmax, jlast, inst["offset_scale"])
    prime = _sieve(limit)
    groups: list[tuple[int, tuple[int, ...]]] = []
    total = 0
    for q in range(inst["q_min"], qmax + 1):
        if not prime[q]:
            continue
        valid = []
        for j in range(inst["j_start"], jlast + 1):
            a = _offset(q, j, inst["offset_scale"])
            if 0 < a < q and prime[q - a] and prime[q + a]:
                valid.append(j)
        pairs = []
        for j1 in valid:
            a1 = _offset(q, j1, inst["offset_scale"])
            c1 = _cofactor(q, a1)
            for j2 in valid:
                if j1 == j2:
                    continue
                a2 = _offset(q, j2, inst["offset_scale"])
                if math.gcd(c1, _cofactor(q, a2)) == 1:
                    pairs.append((j1, j2))
        if pairs:
            packed = tuple(pairs)
            groups.append((q, packed))
            total += len(packed)
    result = (groups, total)
    _GROUP_CACHE[key] = result
    return result


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample the plant's hierarchy over admissible [q,j1,j2,e] words."""
    groups, pair_count = _candidate_index(inst)
    if pair_count == 0:                              # pragma: no cover
        raise RuntimeError("certificate language is unexpectedly empty")
    q, pairs = rng.choice(groups)
    j1, j2 = rng.choice(pairs)
    e = rng.randint(inst["e_min"], inst["e_max"])
    return [q, j1, j2, e]


def search_space(inst: dict) -> int:
    """Exact cardinality of the bounded, prime-filtered certificate language."""
    _, pair_count = _candidate_index(inst)
    return pair_count * inst["power_slots"]


def enumerate_all(inst: dict) -> int | None:
    """Count exact answers when the complete bounded language is at most 200k."""
    size = search_space(inst)
    if size > 200_000:
        return None
    groups, _ = _candidate_index(inst)
    count = 0
    for q, pairs in groups:
        for j1, j2 in pairs:
            for e in range(inst["e_min"], inst["e_max"] + 1):
                if verify(inst, [q, j1, j2, e])[0]:
                    count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Exact normal form for exchanging the two identically defined rows."""
    payload = {
        "family": inst["family"],
        "n": inst["n"],
        "q_interval": [inst["q_min"], inst["q_max"]],
        "offset": [inst["j_start"], inst["offset_count"],
                   inst["offset_scale"]],
        "power": [inst["k"], inst["e_min"], inst["e_max"]],
        "low_bits": inst["low_bits"],
        "targets": sorted([inst["N1"], inst["N2"]]),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow two haystack axes while the four-integer answer stays fixed."""
    out = {k: v for k, v in params.items() if k != "_preset"}
    out["n"] = int(out.get("n", DIFFICULTY["hard"]["n"])) * 4
    out["power_slots"] = int(out.get("power_slots", 256)) * 2
    qmax = 2 * out["n"] - 1
    jstart = int(out.get("offset_scale", 128)) // 3
    jlast = jstart + int(out.get("offset_count", 64)) - 1
    amax = _offset(qmax, jlast, int(out.get("offset_scale", 128)))
    if qmax + amax >= 2**64:
        # This is the exact-primality implementation boundary, not the answer
        # format cap, so calling it cap_bound would misdiagnose the family.
        return None
    return out


def _swap_rows(inst: dict) -> tuple[dict, list[int]]:
    out = {key: value for key, value in inst.items() if key != "answer"}
    out["N1"], out["N2"] = inst["N2"], inst["N1"]
    q, j1, j2, e = inst["answer"]
    carried = [q, j2, j1, e]
    out["answer"] = carried
    return out, carried


def _recover_e(inst: dict) -> int | None:
    mask = (1 << inst["low_bits"]) - 1
    low = inst["N1"] & mask
    rest = inst["N1"] - low
    if rest <= 0 or rest % inst["k"]:
        return None
    power = rest // inst["k"]
    if power & (power - 1):
        return None
    e = power.bit_length() - 1
    return e if inst["e_min"] <= e <= inst["e_max"] else None


def _j_from_offset(inst: dict, q: int, a: int) -> int | None:
    # floor(j*q/(2s))=a/2.  The ceiling below identifies the only possible j;
    # adjacent checks cover the exact boundary case.
    h, scale = a // 2, inst["offset_scale"]
    guess = (2 * scale * h + q - 1) // q
    for j in (guess - 1, guess, guess + 1):
        if (inst["j_start"] <= j
                < inst["j_start"] + inst["offset_count"]
                and _offset(q, j, scale) == a):
            return j
    return None


def _decode_at_q(inst: dict, q: int, low1: int, low2: int,
                 e: int | None) -> list[int] | None:
    if e is None or low1 % q or low2 % q:
        return None
    js = []
    for low in (low1, low2):
        t = low // q - 4 * q * q - 1
        if t <= 0 or t % 12:
            return None
        square = t // 12
        a = math.isqrt(square)
        if a * a != square or a % 2:
            return None
        j = _j_from_offset(inst, q, a)
        if j is None:
            return None
        js.append(j)
    ans = [q, js[0], js[1], e]
    return ans if verify(inst, ans)[0] else None


def _reference_algorithm(inst: dict) -> dict:
    """Track B baseline: scan q, deriving the remaining three entries exactly."""
    modulus = 1 << inst["low_bits"]
    low1, low2 = inst["N1"] % modulus, inst["N2"] % modulus
    e = _recover_e(inst)
    q = inst["q_min"] | 1
    q_trials = 0
    operations = 5
    t0 = time.perf_counter()
    answer = None
    while q <= inst["q_max"]:
        q_trials += 1
        operations += 1
        if low1 % q == 0:
            operations += 1
            if low2 % q == 0:
                candidate = _decode_at_q(inst, q, low1, low2, e)
                operations += 20
                if candidate is not None:
                    answer = candidate
                    break
        q += 2
    elapsed = time.perf_counter() - t0
    return {
        "ok": answer is not None and verify(inst, answer)[0],
        "answer": answer,
        "wall_clock_sec": elapsed,
        "operations": operations,
        "q_trials": q_trials,
    }


def _nearest_valid_group(inst: dict, q0: int, limit: int = 20_000
                         ) -> tuple[int, list[int]] | None:
    q0 = min(inst["q_max"], max(inst["q_min"], q0))
    for distance in range(limit + 1):
        candidates = (q0,) if distance == 0 else (q0 - distance, q0 + distance)
        for q in candidates:
            if not (inst["q_min"] <= q <= inst["q_max"]):
                continue
            if _is_prime(q):
                js = _valid_js_trial(q, inst["offset_count"],
                                     inst["offset_scale"])
                if js:
                    return q, js
    return None


def _best_indices_for_q(inst: dict, q: int, js: list[int]) -> list[int]:
    """Choose the locally closest legal row parameter for each target."""
    modulus = 1 << inst["low_bits"]
    lows = [inst["N1"] % modulus, inst["N2"] % modulus]
    return [min(js, key=lambda j: abs(
        _row_low(q, j, inst["offset_scale"]) - low
    )) for low in lows]


def _attack_midpoint(inst: dict) -> object:
    """Treat the centre of the public q interval as a positional outlier."""
    found = _nearest_valid_group(inst, (inst["q_min"] + inst["q_max"]) // 2)
    if found is None:
        return None
    q, js = found
    chosen = _best_indices_for_q(inst, q, js)
    return [q, chosen[0], chosen[1], _recover_e(inst)]


def _iroot3(value: int) -> int:
    lo, hi = 0, 1 << ((value.bit_length() + 2) // 3 + 1)
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if mid * mid * mid <= value:
            lo = mid
        else:
            hi = mid
    return lo


def _attack_greedy_cuberoot(inst: dict) -> object:
    modulus = 1 << inst["low_bits"]
    lows = [inst["N1"] % modulus, inst["N2"] % modulus]
    mid_j = inst["j_start"] + (inst["offset_count"] - 1) // 2
    ratio_num = mid_j
    ratio_den = inst["offset_scale"]
    # Substitute the middle allowed a/q ratio into 4+12(a/q)^2.
    coeff_num = 4 * ratio_den * ratio_den + 12 * ratio_num * ratio_num
    estimates = [_iroot3(low * ratio_den * ratio_den // coeff_num)
                 for low in lows]
    found = _nearest_valid_group(inst, sum(estimates) // 2)
    if found is None:
        return None
    q, js = found
    chosen = _best_indices_for_q(inst, q, js)
    return [q, chosen[0], chosen[1], _recover_e(inst)]


def _attack_random_restart(inst: dict, seed: int, restarts: int = 256) -> bool:
    rng = random.Random(seed ^ 0x220302296)
    for _ in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _attack_bounded_divisor_scan(inst: dict, budget: int = 64) -> bool:
    modulus = 1 << inst["low_bits"]
    low1, low2 = inst["N1"] % modulus, inst["N2"] % modulus
    e = _recover_e(inst)
    q = inst["q_min"] | 1
    for _ in range(budget):
        ans = _decode_at_q(inst, q, low1, low2, e)
        if ans is not None:
            return True
        q += 2
    return False


def _gcd_divisions(a: int, b: int) -> int:
    steps = 0
    while b:
        a, b = b, a % b
        steps += 1
    return steps


def _intended_route_operations(inst: dict) -> int:
    modulus = 1 << inst["low_bits"]
    low1, low2 = inst["N1"] % modulus, inst["N2"] % modulus
    # Two residues, Euclid, two exact cofactor/square recoveries, two inverse
    # floor evaluations, and extraction/checking of the power-of-two quotient.
    return 2 + _gcd_divisions(low1, low2) + 2 * 10 + 8


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    wire = json.dumps(answer, separators=(",", ":"))
    return len(wire), math.ceil(len(wire) / 4), len(answer)


def selftest() -> dict:
    report: dict = {}

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": why})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **ship_params)
    original = list(inst["answer"])
    corruptions = {
        "drop_one": verify(inst, original[:-1]),
        "swap_two": verify(inst, [original[1], original[0],
                                   original[2], original[3]]),
        "duplicate_one": verify(inst, original + [original[-1]]),
        "empty": verify(inst, []),
        "out_of_range": verify(inst, original[:3] + [inst["e_max"] + 1]),
    }
    reasons = [why for ok, why in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not ok for ok, _ in corruptions.values())
                and len(set(reasons)) == len(reasons),
        "cases": {name: {"rejected": not result[0], "reason": result[1]}
                  for name, result in corruptions.items()},
        "distinct_reasons": len(set(reasons)),
    }

    wire = json.dumps(original, separators=(",", ":"))
    parsed = parse_answer(
        "I used the common-factor invariant.\n```text\n<answer>\n"
        + wire + "\n</answer>\n```\nBoth substitutions are exact."
    )
    report["G3_round_trip"] = {
        "pass": parsed == original,
        "surrounding_prose_and_markdown_fence": True,
        "json_round_trip": parsed == original,
    }

    guess_rng = random.Random(0x220302296)
    guess_total = 200_000
    hits = 0
    t0 = time.perf_counter()
    for _ in range(guess_total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    guess_seconds = time.perf_counter() - t0
    space = search_space(inst)
    groups, _ = _candidate_index(inst)
    planted_pairs = next(pairs for q, pairs in groups
                         if q == inst["answer"][0])
    planted_hit_denominator = (
        len(groups) * len(planted_pairs) * inst["power_slots"]
    )
    report["G4_guess_resistance"] = {
        "pass": hits / guess_total < 1e-6
                and 1 / planted_hit_denominator < 1e-6,
        "hits": hits,
        "total": guess_total,
        "empirical_probability": hits / guess_total,
        "candidate_space": space,
        "exact_planted_witness_hit_probability": 1 / planted_hit_denominator,
        "exact_planted_witness_hit_denominator": planted_hit_denominator,
        "prior": (
            "q uniform over eligible primes; ordered distinct coprime offset "
            "pair uniform conditional on q; exponent uniform in its interval"
        ),
        "sampling_wall_seconds": guess_seconds,
    }

    baseline = _reference_algorithm(inst)
    attack_t0 = time.perf_counter()
    baseline_attack_success = _attack_random_restart(inst, 0xB45E, 256)
    baseline_attack_seconds = time.perf_counter() - attack_t0
    divisor_t0 = time.perf_counter()
    divisor_attack_success = _attack_bounded_divisor_scan(inst, 64)
    divisor_attack_seconds = time.perf_counter() - divisor_t0
    demo_inst = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    report["G5_density_and_baseline"] = {
        "pass": baseline["ok"] and hits / guess_total < 1e-6
                and demo_count is not None and not baseline_attack_success
                and not divisor_attack_success,
        "shipping_observed_valid_fraction": hits / guess_total,
        "shipping_density_sample_count": guess_total,
        "shipping_valid_hits": hits,
        "strongest_failing_attack_wall_seconds": baseline_attack_seconds,
        "strongest_failing_attack_name": "structure-aware random restart",
        "strongest_failing_attack_restarts": 256,
        "strongest_failing_attack_success_count": int(baseline_attack_success),
        "in_context_divisor_scan_wall_seconds": divisor_attack_seconds,
        "in_context_divisor_scan_iterations": 64,
        "in_context_divisor_scan_success_count": int(divisor_attack_success),
        "reference_wall_seconds": baseline["wall_clock_sec"],
        "reference_operation_count": baseline["operations"],
        "reference_q_trials": baseline["q_trials"],
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo_inst),
        "shipping_candidate_space": space,
        "enumerate_all_shipping": None,
    }

    attack_successes = {
        "outlier_midpoint_parameter": 0,
        "greedy_middle_coefficient_cuberoot": 0,
        "random_restart_256_structure_aware": 0,
        "in_context_bounded_divisor_scan_64": 0,
    }
    reference_runs = []
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **ship_params)
        if verify(trial, _attack_midpoint(trial))[0]:
            attack_successes["outlier_midpoint_parameter"] += 1
        if verify(trial, _attack_greedy_cuberoot(trial))[0]:
            attack_successes["greedy_middle_coefficient_cuberoot"] += 1
        if _attack_random_restart(trial, seed):
            attack_successes["random_restart_256_structure_aware"] += 1
        if _attack_bounded_divisor_scan(trial, 64):
            attack_successes["in_context_bounded_divisor_scan_64"] += 1
        reference_runs.append(_reference_algorithm(trial))
    ref_ok = sum(int(run["ok"]) for run in reference_runs)
    all_failed = all(count == 0 for count in attack_successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_ok == 8,
        "attacks": {
            name: {"successes": count, "attempts": 8}
            for name, count in attack_successes.items()
        },
        "reference_algorithm": {
            "name": "definition-driven linear scan of the bounded q interval",
            "complexity": "O(n) exact integer divisions; O(1) memory",
            "wall_clock_sec": sum(r["wall_clock_sec"] for r in reference_runs),
            "mean_wall_clock_sec": (
                sum(r["wall_clock_sec"] for r in reference_runs) / 8
            ),
            "operations": sum(r["operations"] for r in reference_runs),
            "mean_operations": sum(r["operations"] for r in reference_runs) // 8,
            "mean_q_trials": sum(r["q_trials"] for r in reference_runs) // 8,
            "solves": f"{ref_ok}/8, as expected",
        },
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled_params["power_slots"] *= 2
    doubled = make_instance(seed=77, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_params["n"] > ship_params["n"]
                and doubled_params["power_slots"] > ship_params["power_slots"],
        "base_n": ship_params["n"],
        "doubled_n": doubled_params["n"],
        "base_power_slots": ship_params["power_slots"],
        "doubled_power_slots": doubled_params["power_slots"],
        "answer_elements_unchanged": len(doubled["answer"]),
        "doubled_verify": doubled_why,
        "reference_q_haystack_ratio": 2,
        "exponent_haystack_ratio": 2,
    }

    invariance_checks = 0
    witness_checks = 0
    key_params = {
        "n": 10_000, "offset_count": 24, "offset_scale": 48,
        "k": 17, "power_slots": 64,
    }
    for seed in range(20):
        base = make_instance(seed=seed, **key_params)
        swapped, carried = _swap_rows(base)
        invariance_checks += int(canonical_key(swapped) == canonical_key(base))
        witness_checks += int(verify(swapped, carried)[0])
        composed, carried2 = _swap_rows(swapped)
        invariance_checks += int(canonical_key(composed) == canonical_key(base))
        witness_checks += int(verify(composed, carried2)[0])
    keys = {canonical_key(make_instance(seed=seed, **key_params))
            for seed in range(1000, 1020)}
    report["G8_canonical_key"] = {
        "pass": invariance_checks == 40 and witness_checks == 40
                and len(keys) == 20,
        "invariance_checks": invariance_checks,
        "transformed_witness_checks": witness_checks,
        "unrelated_distinct": len(keys),
        "unrelated_attempts": 20,
        "transformations": (
            "exchange of the two identically defined target equations, and "
            "that exchange composed with itself"
        ),
    }

    size_and_ops = []
    for seed in range(256):
        measured = make_instance(seed=1000 + seed, **ship_params)
        size_and_ops.append((*_answer_metrics(measured["answer"]),
                             _intended_route_operations(measured)))
    chars = max(x[0] for x in size_and_ops)
    tokens = max(x[1] for x in size_and_ops)
    elements = max(x[2] for x in size_and_ops)
    intended_ops = max(x[3] for x in size_and_ops)
    ev = G9_EVIDENCE
    hinted_attempts = ev["hinted"]["attempts"]
    placebo_attempts = ev["placebo"]["attempts"]
    hinted_rate = (ev["hinted"]["solved"] / hinted_attempts
                   if hinted_attempts else 0.0)
    placebo_rate = (ev["placebo"]["solved"] / placebo_attempts
                    if placebo_attempts else 0.0)
    within_caps = chars <= 2000 and elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {
            "bare": dict(ev["bare"]),
            "hinted": dict(ev["hinted"]),
            "placebo": dict(ev["placebo"]),
        },
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": ev["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "answer_size_sample_count": len(size_and_ops),
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship_params)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
