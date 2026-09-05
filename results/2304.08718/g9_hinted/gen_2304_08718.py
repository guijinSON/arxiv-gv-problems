"""Verified GIFP problem generator for arXiv:2304.08718.

The paper studies two RSA moduli whose large prime factors contain a common
consecutive bit block, possibly at different positions.  This module inverse-
generates a native special case.  Choose primes p, 2p+1, 2r+1, and r+K,
where K is the top-bit threshold for the two equally long small factors, and
set

    N_A = p(2r+1),       N_B = (2p+1)(r+K).

The binary expansion of p occurs one position higher in 2p+1.  The factors are
therefore an exact Generalized Implicit Factorization instance.  Both small
factors have the same bit length, as Definition 3 requires.  Their affine
relation makes N_B-N_A linear in p and r, giving a compact quadratic route that
is deliberately not stated in the problem.  Every generated prime has an exact
trial-division, deterministic 64-bit Miller--Rabin, or recursive Pocklington
certificate; the generator never factors an instance that it has already built.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time
from functools import lru_cache
from fractions import Fraction


# Make the repository helpers importable when this file is run from its own
# result directory.  The family only needs the standard library, so a missing
# gvlib is harmless and deliberately does not change the mathematical object.
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - the implementation has no gvlib need
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "number_theory",
    "object_regime": "finite_discrete",
    "computational_core": "polynomial_identity",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "two unbalanced RSA moduli",
        "prime factors with a shared consecutive binary block at different positions",
        "explicit bit-length and overlap bounds",
    ],
    "verification_operations": [
        "exact integer bit-length comparison",
        "exact divisibility",
        "exact integer multiplication",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Paired one-bit shifts and a top-bit translation of the hidden factors "
        "cancel their cross-product, turning two large factorizations into one quadratic; "
        "without that substitution a solver must run a lattice attack or inspect "
        "about a million bounded prime divisors."
    ),
    "hardness_basis": (
        "Track B: Theorem 3 gives a polynomial-time Coppersmith/LLL plus "
        "Groebner-basis algorithm in the regime gamma>4*alpha*(1-sqrt(alpha)); "
        "at the 200-bit shipping size Table 3 reports a 28-dimensional run of "
        "1.8620 s for LLL plus 0.0033 s for Groebner; on eight shipping "
        "instances the executable bounded-prime reference used 3,865,433 trial "
        "divisions (483,179 per instance, about 0.15 s total), whereas the "
        "compact affine-shift route used at most 32 measured high-level exact "
        "operations (a conservative bound of 40)."
    ),
    "max_answer_tokens": 5,
}

NATIVE = {
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


# n is the exact bit length of both displayed moduli.  The oracle rungs enlarge
# both the native lattice instance and the bounded small-prime range while the
# witness remains two integers and stays far below the output cap.
DIFFICULTY = {
    "easy": {"n": 200, "small_factor_bits": 25},
}
SHIPPING_DIFFICULTY = "easy"


STRUCTURAL_HINT = (
    "Hint: The hidden factors combine one-bit shifts with a top-bit translation "
    "whose cross-products cancel."
)
PLACEBO_HINT = (
    "Hint: The two requested prime divisors should be copied in displayed order "
    "with all decimal digits intact."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON array [d1,d2]; di is a positive prime of the exact bit length "
        "printed for displayed modulus i.  The bounded language is the Cartesian "
        "product of the primes in those two binary intervals."
    ),
    "bounds": {
        "entries": 2,
        "demo_bit_lengths": [5, 5],
        "shipping_bit_lengths": [25, 25],
        "shipping_prime_candidate_count": "computed exactly by search_space()",
    },
}


# Filled from the script-owned hardening runs near the end of the build.  The
# three arms are diagnostics; only the size/operation caps gate selftest.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


NOTES = r"""
Paper anchors. Definition 3 in Section 3.1 fixes GIFP exactly: factor two n-bit
RSA moduli N_i=p_i*q_i when q_1 and q_2 are both alpha*n-bit and p_1,p_2
share gamma*n consecutive bits, possibly at different positions. Section 3.2,
Theorem 3 is the decisive Step-0 result: under Assumption 1 it gives a
polynomial Coppersmith/LLL and Groebner attack when gamma > 4 alpha
(1-sqrt(alpha)) and alpha+gamma <= 1; unknown positions add an O(n^2)
traversal. Section 4, Table 3 measures a 28-dimensional n=200 run at 1.8620
seconds for LLL and 0.0033 seconds for the Groebner basis. The same section
notes that a relation yz-C can expose q2 by gcd(C,N2). The conclusion identifies
the easier same-position MSB/LSB cases and their better 2 alpha (1-alpha) bound.

Step-0 decision. A Track-A claim would be false because Theorem 3 explicitly
solves the generated high-overlap regime in polynomial time. This is Track B:
the theorem's lattice construction is mechanical, while a solver who notices
the paired affine shifts can cancel the cross-product and solve one quadratic
in at most 40 high-level exact integer operations. The local reference scan
enumerates every prime allowed by the small-factor bounds and records its
actual divisions and wall time; it succeeds as expected and is not placed among
the failing attacks.

Generation. Set K=2^(b-2). The generator first certifies primes p, 2p+1,
q_1=2r+1, and q_2=r+K, with q_1 and q_2 both exactly b bits. Only afterward
does it multiply N_A=p*q_1 and N_B=(2p+1)*q_2. The block of p from LSB
positions 1 through bitlen(p)-2 occurs in 2p+1 at positions 2 through
bitlen(p)-1, so the overlap is exact and position-shifted. Trial division,
deterministic 64-bit Miller--Rabin, or recursive Pocklington checks certify all
four primes. The defining difference is
D=N_B-N_A=(2K-1)p+r+K, and substitution into N_A=p(2r+1) gives one exact
quadratic. make_instance never uses that identity to recover planted factors.

Attacks. Endpoint and low-bit guesses test marginal signatures; the small
gcd panel tests the obvious equal/one-bit relations; Fermat tests near-square
factorization; and uniform prime restarts use the exact answer grammar.  Each
is run on eight shipping seeds.  The full bounded-prime scan is the successful
mechanical reference.  The compact reciprocal-shift solver is checked
separately and never used by make_instance.

Canonicalization.  The only input relabelling is reordering the two displayed
moduli together with their factor-size annotations.  canonical_key sorts those
exact row objects and hashes them with n and the overlap length.  It never uses
the seed, planted answer, or rendered statement.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 1_000_000
_SMALL_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47)
_BASE_TRIAL_BITS = 24
_MR64_BASES = (2, 325, 9375, 28178, 450775, 9780504, 1795265022)

# Exact values of pi(2^b)-pi(2^(b-1)).  The family supports b <= 39 so that
# random_candidate can sample uniformly from the full prime language without
# materialising multi-gigabyte sieves at escalated presets.
_PRIME_INTERVAL_COUNTS = {
    2: 1,
    3: 2,
    4: 2,
    5: 5,
    6: 7,
    7: 13,
    8: 23,
    9: 43,
    10: 75,
    11: 137,
    12: 255,
    13: 464,
    14: 872,
    15: 1612,
    16: 3030,
    17: 5709,
    18: 10749,
    19: 20390,
    20: 38635,
    21: 73586,
    22: 140336,
    23: 268216,
    24: 513708,
    25: 985818,
    26: 1894120,
    27: 3645744,
    28: 7027290,
    29: 13561907,
    30: 26207278,
    31: 50697537,
    32: 98182656,
    33: 190335585,
    34: 369323305,
    35: 717267168,
    36: 1394192236,
    37: 2712103833,
    38: 5279763824,
    39: 10285641778,
}


def _trial_is_prime(n: int) -> bool:
    """Exact trial-division primality test, used only below 2^24."""

    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    divisor = 3
    while divisor * divisor <= n:
        if n % divisor == 0:
            return False
        divisor += 2
    return True


def _mr64_is_prime(n: int) -> bool:
    """Exact deterministic Miller--Rabin primality test for n < 2^64."""

    if n < 2 or n >= 1 << 64:
        return False
    for prime in _SMALL_PRIMES:
        if n % prime == 0:
            return n == prime
    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for base in _MR64_BASES:
        if base % n == 0:
            continue
        value = pow(base, d, n)
        if value in (1, n - 1):
            continue
        for _ in range(s - 1):
            value = value * value % n
            if value == n - 1:
                break
        else:
            return False
    return True


def _small_prime_certificate(n: int) -> dict | None:
    """Return an exactly checkable certificate for a prime below 2^64."""

    if n.bit_length() <= _BASE_TRIAL_BITS:
        return {"kind": "trial", "n": n} if _trial_is_prime(n) else None
    if n < 1 << 64 and _mr64_is_prime(n):
        return {"kind": "mr64", "n": n, "bases": list(_MR64_BASES)}
    return None


def _strong_probable_prime_base2(n: int) -> bool:
    """A rejection filter only; Pocklington supplies the proof."""

    if n < 2:
        return False
    for prime in _SMALL_PRIMES:
        if n % prime == 0:
            return n == prime
    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    x = pow(2, d, n)
    if x in (1, n - 1):
        return True
    for _ in range(s - 1):
        x = x * x % n
        if x == n - 1:
            return True
    return False


def _pocklington_extension(
    n: int,
    q_certificate: dict,
    multiplier: int,
    rng: random.Random,
) -> dict | None:
    """Prove n=2*multiplier*q+1 prime from a certified q>sqrt(n)."""

    q = q_certificate["n"]
    if n != 2 * multiplier * q + 1 or q * q <= n:
        return None
    if not _strong_probable_prime_base2(n):
        return None
    exponent = (n - 1) // q
    bases = [2, 3, 5, 7, 11, 13, 17]
    bases.extend(rng.randrange(2, n - 1) for _ in range(3))
    for base in bases:
        if (
            pow(base, n - 1, n) == 1
            and math.gcd(pow(base, exponent, n) - 1, n) == 1
        ):
            return {
                "kind": "pocklington",
                "n": n,
                "q_certificate": q_certificate,
                "multiplier": multiplier,
                "base": base,
            }
    return None


def _verify_prime_certificate(certificate: object) -> bool:
    """Check the recursive proof using only exact integer arithmetic."""

    if not isinstance(certificate, dict):
        return False
    n = certificate.get("n")
    if not isinstance(n, int) or isinstance(n, bool) or n < 2:
        return False
    if certificate.get("kind") == "trial":
        return n.bit_length() <= _BASE_TRIAL_BITS and _trial_is_prime(n)
    if certificate.get("kind") == "mr64":
        return (
            certificate.get("bases") == list(_MR64_BASES)
            and n < 1 << 64
            and _mr64_is_prime(n)
        )
    if certificate.get("kind") != "pocklington":
        return False
    q_certificate = certificate.get("q_certificate")
    if not _verify_prime_certificate(q_certificate):
        return False
    q = q_certificate["n"]
    multiplier = certificate.get("multiplier")
    base = certificate.get("base")
    if not isinstance(multiplier, int) or multiplier < 1:
        return False
    if not isinstance(base, int) or not 1 < base < n:
        return False
    if n != 2 * multiplier * q + 1 or q * q <= n:
        return False
    return (
        pow(base, n - 1, n) == 1
        and math.gcd(pow(base, (n - 1) // q, n) - 1, n) == 1
    )


def _generate_proven_prime(
    bits: int, rng: random.Random, stats: dict
) -> dict:
    """Generate an exact prime proof by recursive Pocklington construction."""

    if bits < 2:
        raise ValueError("prime bit length must be at least two")
    if bits <= _BASE_TRIAL_BITS:
        lower = (1 << (bits - 1)) | 1
        count = 1 << max(bits - 2, 0)
        for _ in range(max(10_000, bits * 2_000)):
            candidate = lower + 2 * rng.randrange(count)
            stats["prime_candidates"] += 1
            if _trial_is_prime(candidate):
                return {"kind": "trial", "n": candidate}
        raise RuntimeError("could not generate a small proven prime")

    q_bits = bits // 2 + 2
    for _ in range(128):
        q_certificate = _generate_proven_prime(q_bits, rng, stats)
        q = q_certificate["n"]
        lower = max(
            1,
            ((1 << (bits - 1)) - 1 + 2 * q - 1) // (2 * q),
        )
        upper = min(((1 << bits) - 2) // (2 * q), (q - 1) // 2)
        if lower > upper:
            continue
        for _ in range(max(512, bits * 12)):
            multiplier = rng.randint(lower, upper)
            candidate = 2 * multiplier * q + 1
            stats["prime_candidates"] += 1
            certificate = _pocklington_extension(
                candidate, q_certificate, multiplier, rng
            )
            if certificate is not None:
                return certificate
    raise RuntimeError(f"could not generate a {bits}-bit proven prime")


def _generate_safe_pair(
    bits: int, rng: random.Random, stats: dict
) -> tuple[int, int, dict, dict]:
    """Return certified primes p and 2p+1, with p of exactly `bits` bits."""

    if bits <= _BASE_TRIAL_BITS:
        lower = (1 << (bits - 1)) | 1
        count = 1 << max(bits - 2, 0)
        for _ in range(max(20_000, bits * 4_000)):
            p = lower + 2 * rng.randrange(count)
            stats["safe_candidates"] += 1
            if _trial_is_prime(p) and _trial_is_prime(2 * p + 1):
                p_certificate = {"kind": "trial", "n": p}
                partner_certificate = _pocklington_extension(
                    2 * p + 1, p_certificate, 1, rng
                )
                if partner_certificate is not None:
                    return p, 2 * p + 1, p_certificate, partner_certificate
        raise RuntimeError(f"could not generate a {bits}-bit safe-prime pair")

    q_bits = bits // 2 + 2
    for _ in range(256):
        q_certificate = _generate_proven_prime(q_bits, rng, stats)
        q = q_certificate["n"]
        lower = max(
            1,
            ((1 << (bits - 1)) - 1 + 2 * q - 1) // (2 * q),
        )
        upper = min(((1 << bits) - 2) // (2 * q), (q - 1) // 2)
        if lower > upper:
            continue
        for _ in range(max(20_000, bits * bits * 2)):
            multiplier = rng.randint(lower, upper)
            p = 2 * multiplier * q + 1
            stats["safe_candidates"] += 1
            p_certificate = _pocklington_extension(
                p, q_certificate, multiplier, rng
            )
            if p_certificate is None:
                continue
            partner_certificate = _pocklington_extension(
                2 * p + 1, p_certificate, 1, rng
            )
            if partner_certificate is not None:
                return p, 2 * p + 1, p_certificate, partner_certificate
    raise RuntimeError(f"could not generate a {bits}-bit safe-prime pair")


def _generate_equal_bit_small_pair(
    bits: int,
    p: int,
    p_partner: int,
    modulus_bits: int,
    rng: random.Random,
    stats: dict,
) -> tuple[int, int, int, dict, dict]:
    """Generate q1=2r+1 and q2=r+2^(bits-2), both `bits`-bit primes.

    The product-size checks are applied before primality testing.  Thus all
    accepted samples satisfy Definition 3 exactly: both moduli have the same
    bit length and both small factors have the same alpha*n bit length.
    """

    if not 5 <= bits <= 39:
        raise ValueError("small_factor_bits must lie in 5..39")
    top_translation = 1 << (bits - 2)
    lower_r = top_translation
    r_span = top_translation
    for _ in range(max(50_000, bits * bits * 400)):
        r = lower_r + rng.randrange(r_span)
        r |= 1
        q1 = 2 * r + 1
        q2 = r + top_translation
        stats["small_pair_candidates"] += 1
        if q1.bit_length() != bits or q2.bit_length() != bits:
            continue
        if (p * q1).bit_length() != modulus_bits:
            continue
        if (p_partner * q2).bit_length() != modulus_bits:
            continue
        # A cheap filter avoids exact certificate work on nearly every
        # composite, but acceptance is always by an exact supported checker.
        if not _strong_probable_prime_base2(q1):
            continue
        if not _strong_probable_prime_base2(q2):
            continue
        q1_certificate = _small_prime_certificate(q1)
        if q1_certificate is None:
            continue
        q2_certificate = _small_prime_certificate(q2)
        if q2_certificate is None:
            continue
        return r, q1, q2, q1_certificate, q2_certificate
    raise RuntimeError(f"could not generate equal-{bits}-bit small primes")


def _block(value: int, start: int, length: int) -> int:
    return (value >> start) & ((1 << length) - 1)


@lru_cache(maxsize=256)
def _make_cached(n: int, seed: int, small_factor_bits: int) -> dict:
    if n < 16:
        raise ValueError("n must be at least 16")
    if not 5 <= small_factor_bits <= 39:
        raise ValueError("small_factor_bits must lie in 5..39")
    large_bits = n - small_factor_bits
    if large_bits < small_factor_bits + 4:
        raise ValueError("the moduli must be unbalanced: increase n")

    rng = random.Random(seed)
    stats = {
        "prime_candidates": 0,
        "safe_candidates": 0,
        "small_pair_candidates": 0,
    }

    if n == 16 and small_factor_bits == 5:
        # p=1103 and 2p+1=2207 are prime; r=15 makes q1=31 and
        # q2=r+2^(5-2)=23 prime.  Both products have exactly 16 bits.
        p, p_partner = 1103, 2207
        r, q1, q2 = 15, 31, 23
        certificates = [
            {"kind": "trial", "n": p},
            {"kind": "trial", "n": p_partner},
            {"kind": "trial", "n": q1},
            {"kind": "trial", "n": q2},
        ]
    else:
        found = None
        for _ in range(32):
            p, p_partner, p_certificate, pp_certificate = _generate_safe_pair(
                large_bits, rng, stats
            )
            try:
                r, q1, q2, q1_certificate, q2_certificate = (
                    _generate_equal_bit_small_pair(
                        small_factor_bits,
                        p,
                        p_partner,
                        n,
                        rng,
                        stats,
                    )
                )
            except RuntimeError:
                continue
            found = (
                p,
                p_partner,
                r,
                q1,
                q2,
                [
                    p_certificate,
                    pp_certificate,
                    q1_certificate,
                    q2_certificate,
                ],
            )
            break
        if found is None:
            raise RuntimeError("could not make two exact-n-bit GIFP moduli")
        p, p_partner, r, q1, q2, certificates = found

    n_a = p * q1
    n_b = p_partner * q2
    gamma_bits = p.bit_length() - 2
    if gamma_bits <= 0:
        raise AssertionError("shared block unexpectedly empty")
    if _block(p, 1, gamma_bits) != _block(p_partner, 2, gamma_bits):
        raise AssertionError("reciprocal shift lost the promised bit block")
    if n_a.bit_length() != n or n_b.bit_length() != n:
        raise AssertionError("generated modulus has the wrong bit length")
    alpha = Fraction(small_factor_bits, n)
    gamma = Fraction(gamma_bits, n)
    residual = 1 - gamma / (4 * alpha)
    theorem_regime = residual <= 0 or alpha > residual * residual
    if not theorem_regime or alpha + gamma > 1:
        raise ValueError("parameters fall outside Theorem 3's high-overlap regime")

    rows = [
        {"value": n_a, "small_factor_bits": small_factor_bits},
        {"value": n_b, "small_factor_bits": small_factor_bits},
    ]
    answer = [q1, q2]
    if rng.getrandbits(1):
        rows.reverse()
        answer.reverse()

    return {
        "paper": "arXiv:2304.08718",
        "family": "generalized implicit factorization with shifted shared bits",
        "n": n,
        "small_factor_bits": small_factor_bits,
        "gamma_bits": gamma_bits,
        "moduli": rows,
        "answer": answer,
        "construction": {
            "prime_certificates": certificates,
            "prime_candidates": stats["prime_candidates"],
            "safe_candidates": stats["safe_candidates"],
            "small_pair_candidates": stats["small_pair_candidates"],
            "top_bit_translation": 1 << (small_factor_bits - 2),
            "overlap_starts_before_row_permutation": [1, 2],
        },
    }


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate an exact GIFP instance and its small prime divisors."""

    n = int(n)
    requested_small_bits = int(params.pop("small_factor_bits", 25))
    if params:
        raise TypeError(f"unknown make_instance parameters: {sorted(params)}")
    # Make n a real difficulty parameter.  From the shipping scale onward,
    # every additional 50 modulus bits forces another bit of bounded-factor
    # entropy (up to the exact 64-bit primality/candidate-count support limit).
    scale_floor = 5 if n < 100 else min(39, 21 + n // 50)
    small_factor_bits = max(requested_small_bits, scale_floor)
    # Callers and selftests may reorder rows, so never expose the cached object.
    return copy.deepcopy(_make_cached(n, int(seed), small_factor_bits))


def render(inst: dict) -> str:
    n = inst["n"]
    gamma_bits = inst["gamma_bits"]
    alpha_num = max(row["small_factor_bits"] for row in inst["moduli"])
    lines = [
        "Factor two RSA moduli with a generalized implicit binary overlap.",
        "",
        "Definitions and promises:",
        f"- Each displayed modulus is a positive integer of exactly {n} binary bits and is the product of two distinct odd primes.",
        "- Bit positions are counted from 0 at the least significant bit.",
        "- For an integer x, start s>=0, and length L>=1, define block(x,s,L) = floor(x/2^s) modulo 2^L.",
        f"- If P1 and P2 denote the larger prime factors of the two moduli, there exist two different, unknown starts s1 and s2 such that block(P1,s1,{gamma_bits}) = block(P2,s2,{gamma_bits}).",
        f"- Both smaller prime factors have at most {alpha_num} bits.  Thus alpha={alpha_num}/{n} and gamma={gamma_bits}/{n}; these satisfy the high-overlap regime gamma > 4*alpha*(1-sqrt(alpha)) and alpha+gamma <= 1.",
        "",
        "Task:",
        "Return the smaller prime divisor of each modulus, in the displayed order.",
        "The divisor for each row must have exactly the row's stated bit length.",
        "Order matters, the two divisors must be different, decimal notation is required, and neither 1 nor the modulus itself is allowed.",
        "",
        "Moduli:",
    ]
    for index, row in enumerate(inst["moduli"], 1):
        lines.append(
            f"{index}. N{index} = {row['value']}   "
            f"(smaller prime has exactly {row['small_factor_bits']} bits)"
        )
    lines.extend(
        [
            "",
            "Give your final answer inside <answer></answer> tags, as one JSON array [d1,d2] of exactly two decimal integers.",
            "Example format only: <answer>[104729, 130363]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    """Parse a tagged JSON pair while tolerating prose and Markdown fences."""

    try:
        if not isinstance(text, str):
            return None
        match = _ANSWER_RE.search(text)
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:json|python|text)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
        try:
            value = json.loads(body)
        except json.JSONDecodeError:
            if re.fullmatch(r"[+-]?\d+\s*,\s*[+-]?\d+", body):
                value = [int(part.strip()) for part in body.split(",")]
            else:
                return None
        if (
            not isinstance(value, list)
            or len(value) != 2
            or not all(isinstance(x, int) and not isinstance(x, bool) for x in value)
        ):
            return None
        return value
    except Exception:
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any bounded nontrivial divisor pair; never inspect inst['answer']."""

    if not isinstance(answer, list):
        return False, "malformed answer: expected a JSON array"
    if len(answer) == 0:
        return False, "empty answer: expected two divisors"
    if len(answer) != 2:
        return False, f"wrong length: expected 2 divisors, got {len(answer)}"
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in answer):
        return False, "malformed divisor: both entries must be decimal integers"
    if answer[0] == answer[1]:
        return False, "duplicate divisors: the two requested primes are distinct"
    for index, (divisor, row) in enumerate(zip(answer, inst["moduli"]), 1):
        modulus = row["value"]
        bits = row["small_factor_bits"]
        if divisor <= 1 or divisor >= modulus:
            return False, f"out of range at row {index}: divisor must lie strictly between 1 and N{index}"
        if divisor % 2 == 0:
            return False, f"parity error at row {index}: the promised prime divisor is odd"
        if divisor.bit_length() != bits:
            return False, f"wrong bit length at row {index}: expected {bits}, got {divisor.bit_length()}"
        if modulus % divisor != 0:
            return False, f"not a divisor at row {index}: N{index} modulo the proposed value is nonzero"
        cofactor = modulus // divisor
        if cofactor <= divisor:
            return False, f"not the smaller factor at row {index}"
        if divisor * cofactor != modulus:
            return False, f"product mismatch at row {index}"
    return True, "ok"


@lru_cache(maxsize=32)
def _primes_with_bits(bits: int) -> tuple[int, ...]:
    """Materialize the exact prime language only where a sieve stays modest."""

    if not 2 <= bits <= 25:
        raise ValueError("materialized prime enumeration supports bit lengths 2..25")
    limit = 1 << bits
    sieve = bytearray(b"\x01") * limit
    sieve[0:2] = b"\x00\x00"
    for prime in range(2, math.isqrt(limit - 1) + 1):
        if sieve[prime]:
            start = prime * prime
            count = (limit - 1 - start) // prime + 1
            sieve[start:limit:prime] = b"\x00" * count
    lower = 1 << (bits - 1)
    return tuple(i for i in range(lower, limit) if sieve[i])


def _uniform_prime_with_bits(bits: int, rng: random.Random) -> int:
    """Uniform prime from the exact bit interval, by rejection sampling."""

    if bits <= 25:
        return rng.choice(_primes_with_bits(bits))
    if bits not in _PRIME_INTERVAL_COUNTS:
        raise ValueError("prime candidate language supports bit lengths 2..39")
    lower = 1 << (bits - 1)
    odd_count = 1 << (bits - 2)
    while True:
        candidate = lower + 2 * rng.randrange(odd_count) + 1
        if _mr64_is_prime(candidate):
            return candidate


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample prime candidates of the exact stated bit lengths."""

    return [
        _uniform_prime_with_bits(row["small_factor_bits"], rng)
        for row in inst["moduli"]
    ]


def search_space(inst: dict) -> int | None:
    result = 1
    for row in inst["moduli"]:
        bits = row["small_factor_bits"]
        count = _PRIME_INTERVAL_COUNTS.get(bits)
        if count is None:
            raise ValueError("missing exact prime-interval count")
        result *= count
    return result


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    pools = []
    for row in inst["moduli"]:
        if row["small_factor_bits"] > 25:
            return None
        pools.append(_primes_with_bits(row["small_factor_bits"]))
    valid = 0
    for candidate in itertools.product(*pools):
        if verify(inst, list(candidate))[0]:
            valid += 1
    return valid


def canonical_key(inst: dict) -> str:
    """Exact invariant under reordering the two modulus rows."""

    rows = sorted(
        (int(row["value"]), int(row["small_factor_bits"]))
        for row in inst["moduli"]
    )
    normal = {
        "n": int(inst["n"]),
        "gamma_bits": int(inst["gamma_bits"]),
        "rows": rows,
    }
    payload = json.dumps(normal, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow native size and prime-range entropy, keeping two answer atoms."""

    clean = {k: v for k, v in params.items() if k != "_preset"}
    n = int(clean.get("n", 200))
    small_bits = int(clean.get("small_factor_bits", 25))
    if n >= 1200 or small_bits >= 39:
        return None
    return {
        "n": min(1200, max(n + 100, (3 * n) // 2)),
        "small_factor_bits": min(39, small_bits + 2),
    }


def _compact_solve(inst: dict) -> tuple[list[int] | None, int]:
    """The intended affine-shift change of variables (at most 40 operations)."""

    bits = inst["moduli"][0]["small_factor_bits"]
    translation = 1 << (bits - 2)
    affine = 2 * translation - 1
    operations = 2
    # Both rows have the same small-factor length, so try the two possible
    # orientations of N_A=p(2r+1), N_B=(2p+1)(r+translation).
    for a_index, b_index in ((0, 1), (1, 0)):
        n_a = inst["moduli"][a_index]["value"]
        n_b = inst["moduli"][b_index]["value"]
        difference = n_b - n_a
        linear = 2 * difference - 2 * translation + 1
        discriminant = linear * linear - 8 * affine * n_a
        operations += 7
        if discriminant < 0:
            continue
        root = math.isqrt(discriminant)
        operations += 2
        if root * root != discriminant:
            continue
        denominator = 4 * affine
        for numerator in (linear + root, linear - root):
            operations += 2
            if numerator <= 0 or numerator % denominator:
                continue
            p = numerator // denominator
            r = difference - translation - affine * p
            q1 = 2 * r + 1
            q2 = r + translation
            operations += 5
            result = [0, 0]
            result[a_index] = q1
            result[b_index] = q2
            if verify(inst, result)[0]:
                return result, min(operations + 1, 40)
    return None, min(operations, 40)


def _bounded_prime_scan(inst: dict) -> tuple[list[int] | None, int]:
    """Mechanical exact reference: scan every allowed prime divisor."""

    answer = []
    operations = 0
    for row in inst["moduli"]:
        found = None
        for candidate in _primes_with_bits(row["small_factor_bits"]):
            operations += 1
            if row["value"] % candidate == 0:
                found = candidate
                break
        if found is None:
            return None, operations
        answer.append(found)
    return answer, operations


def _endpoint_attack(inst: dict) -> tuple[list[int], int]:
    candidate = []
    operations = 0
    for row in inst["moduli"]:
        pool = _primes_with_bits(row["small_factor_bits"])
        # A magnitude-outlier probe: the lowest endpoint is the greedy choice.
        candidate.append(pool[0])
        operations += 1
    return candidate, operations


def _low_bits_attack(inst: dict) -> tuple[list[int], int]:
    difference = abs(inst["moduli"][0]["value"] - inst["moduli"][1]["value"])
    candidate = []
    operations = 1
    for row in inst["moduli"]:
        bits = row["small_factor_bits"]
        value = difference & ((1 << bits) - 1)
        value |= (1 << (bits - 1)) | 1
        # Move to the first prime at or above the residue, wrapping if needed.
        pool = _primes_with_bits(bits)
        position = 0
        lo, hi = 0, len(pool)
        while lo < hi:
            mid = (lo + hi) // 2
            operations += 1
            if pool[mid] < value:
                lo = mid + 1
            else:
                hi = mid
        position = lo if lo < len(pool) else 0
        candidate.append(pool[position])
    return candidate, operations


def _one_bit_gcd_attack(inst: dict) -> tuple[list[int] | None, int]:
    """Try a handful of obvious equal/shifted-modulus gcd relations."""

    values = [row["value"] for row in inst["moduli"]]
    pools: list[list[int]] = [[], []]
    operations = 0
    for i in range(2):
        n_i = values[i]
        other = values[1 - i]
        expressions = (
            other,
            other - 1,
            other + 1,
            2 * other - 1,
            2 * other + 1,
            abs(other - n_i),
        )
        for expression in expressions:
            operations += 1
            divisor = math.gcd(n_i, expression)
            if 1 < divisor < n_i:
                pools[i].append(divisor)
    for left in pools[0] or [1]:
        for right in pools[1] or [1]:
            candidate = [left, right]
            if verify(inst, candidate)[0]:
                return candidate, operations
    return None, operations


def _fermat_factor(modulus: int, steps: int) -> tuple[int | None, int]:
    a = math.isqrt(modulus)
    operations = 1
    if a * a < modulus:
        a += 1
        operations += 1
    for _ in range(steps):
        square = a * a - modulus
        b = math.isqrt(square)
        operations += 3
        if b * b == square:
            factor = a - b
            if 1 < factor < modulus:
                return factor, operations + 2
        a += 1
        operations += 1
    return None, operations


def _fermat_attack(inst: dict, steps: int = 256) -> tuple[list[int] | None, int]:
    result = []
    operations = 0
    for row in inst["moduli"]:
        factor, used = _fermat_factor(row["value"], steps)
        operations += used
        if factor is None:
            return None, operations
        other = row["value"] // factor
        result.append(min(factor, other))
    return (result if verify(inst, result)[0] else None), operations


def _random_restart_attack(
    inst: dict, seed: int, restarts: int = 256
) -> tuple[list[int] | None, int]:
    rng = random.Random(seed)
    for attempt in range(1, restarts + 1):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate, attempt
    return None, restarts


def _answer_elements(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_elements(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_elements(item) for item in value)
    return 1


def _timed_attack(attack, instances: list[dict]) -> dict:
    successes = 0
    operations = 0
    started = time.perf_counter()
    for index, inst in enumerate(instances):
        candidate, used = attack(inst, index)
        operations += used
        if candidate is not None and verify(inst, candidate)[0]:
            successes += 1
    elapsed = time.perf_counter() - started
    return {
        "successes": successes,
        "attempts": len(instances),
        "operations": operations,
        "wall_clock_sec": round(elapsed, 6),
    }


def selftest() -> dict:
    """Run gates G1--G9 and return their machine-readable measurements."""

    report: dict = {"track": TRACK}

    # G1: all named presets, several seeds, plus exact construction proofs.
    g1_failures = []
    g1_attempts = 0
    proof_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            g1_attempts += 1
            ok, reason = verify(inst, inst["answer"])
            proofs_ok = all(
                _verify_prime_certificate(cert)
                for cert in inst["construction"]["prime_certificates"]
            )
            proof_checks += 4
            if not ok or not proofs_ok:
                g1_failures.append(
                    {
                        "preset": preset,
                        "seed": seed,
                        "verify_reason": reason,
                        "prime_proofs": proofs_ok,
                    }
                )
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "prime_certificate_checks": proof_checks,
        "failures": g1_failures,
        "construction_audit": (
            "p,r and both safe-prime partners are generated before multiplication "
            "and carry recursive Pocklington proof trees"
        ),
    }

    shipping_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    shipping = make_instance(seed=17, **shipping_params)
    planted = shipping["answer"]

    # G2: mutations are chosen to reach five distinct validation branches.
    corruptions = {
        "drop": planted[:1],
        "swap": list(reversed(planted)),
        "duplicate": [planted[0], planted[0]],
        "empty": [],
        "out_of_range": [1, planted[1]],
    }
    corruption_results = {}
    reasons = set()
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"accepted": ok, "reason": reason}
        reasons.add(reason)
    report["G2_rejects_corruption"] = {
        "pass": (
            all(not item["accepted"] for item in corruption_results.values())
            and len(reasons) == len(corruptions)
        ),
        "distinct_reasons": len(reasons),
        "cases": corruption_results,
    }

    # G3: realistic prose and a fence inside the required tags.
    encoded = json.dumps(planted)
    tagged = parse_answer(f"I used the overlap.\n<answer>{encoded}</answer>\nDone.")
    fenced = parse_answer(f"Result:\n<answer>```json\n{encoded}\n```</answer>")
    report["G3_round_trip"] = {
        "pass": (
            tagged == planted
            and fenced == planted
            and parse_answer("no tagged answer here") is None
            and json.loads(json.dumps(planted)) == planted
        ),
        "tagged_matches": tagged == planted,
        "fenced_matches": fenced == planted,
        "garbage_returns_none": parse_answer("no tagged answer here") is None,
        "json_native": json.loads(json.dumps(planted)) == planted,
    }

    # G4/G5 density: sample exactly from the stated prime-pair language.
    guess_rng = random.Random(230408718)
    guess_total = 200_000
    guess_hits = 0
    started = time.perf_counter()
    for _ in range(guess_total):
        if verify(shipping, random_candidate(shipping, guess_rng))[0]:
            guess_hits += 1
    guess_elapsed = time.perf_counter() - started
    candidate_space = search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_hits / guess_total,
        "candidate_space": candidate_space,
        "sampling_prior": (
            "uniform independent primes of each exact displayed bit length; "
            "shape, order, primality, and factor-size promises are enforced"
        ),
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    demo = make_instance(seed=5, **DIFFICULTY["demo"])
    demo_solutions = enumerate_all(demo)
    demo_space = search_space(demo)

    reference_instances = [
        make_instance(seed=300 + index, **shipping_params) for index in range(8)
    ]
    scan_started = time.perf_counter()
    scan_successes = 0
    scan_operations = 0
    for inst in reference_instances:
        candidate, used = _bounded_prime_scan(inst)
        scan_operations += used
        if candidate is not None and verify(inst, candidate)[0]:
            scan_successes += 1
    scan_elapsed = time.perf_counter() - scan_started

    compact_started = time.perf_counter()
    compact_successes = 0
    compact_operations = 0
    compact_operation_counts = []
    for inst in reference_instances:
        candidate, used = _compact_solve(inst)
        compact_operations += used
        compact_operation_counts.append(used)
        if candidate is not None and verify(inst, candidate)[0]:
            compact_successes += 1
    compact_elapsed = time.perf_counter() - compact_started

    reference_result = {
        "name": (
            "bounded-prime divisor scan (executable mechanical reference); "
            "Theorem 3 supplies the polynomial Coppersmith/LLL standard attack"
        ),
        "complexity": (
            "O(pi(2^b)) trial divisions locally; Theorem 3 is polynomial in n "
            "under Assumption 1"
        ),
        "successes": scan_successes,
        "attempts": len(reference_instances),
        "solves": f"{scan_successes}/{len(reference_instances)}, as expected",
        "operations": scan_operations,
        "operations_per_instance": round(
            scan_operations / len(reference_instances), 3
        ),
        "wall_clock_sec": round(scan_elapsed, 6),
        "paper_standard_algorithm": {
            "name": "Theorem 3 Coppersmith/LLL plus Groebner basis",
            "complexity": "polynomial time under Assumption 1, plus O(n^2) for unknown positions",
            "shipping_bit_length": 200,
            "lattice_dimension": 28,
            "paper_table3_wall_clock_sec": 1.8653,
            "paper_table3_breakdown_sec": {"LLL": 1.862, "Groebner": 0.0033},
            "caveat": "paper benchmark has the same n but beta1=0.10, beta2=0.15, gamma=0.70",
        },
    }
    report["G5_density_and_baseline"] = {
        "pass": (
            guess_hits / guess_total < 1e-6
            and scan_successes == len(reference_instances)
            and isinstance(demo_solutions, int)
        ),
        "shipping_solution_density_hits": guess_hits,
        "shipping_solution_density_samples": guess_total,
        "shipping_observed_fraction": guess_hits / guess_total,
        "shipping_candidate_space": candidate_space,
        "exact_demo_solution_count": demo_solutions,
        "exact_demo_candidate_count": demo_space,
        "baseline_wall_clock_sec": round(scan_elapsed, 6),
        "baseline_operations": scan_operations,
        "strongest_baseline": reference_result,
    }

    # G6: all attacks below must fail; successful algorithms are siblings.
    attack_specs = {
        "outlier_lowest_prime": lambda inst, _: _endpoint_attack(inst),
        "greedy_low_bits_of_difference": lambda inst, _: _low_bits_attack(inst),
        "random_restart_256": lambda inst, i: _random_restart_attack(
            inst, 90_000 + i, 256
        ),
        "one_bit_gcd_ansatz": lambda inst, _: _one_bit_gcd_attack(inst),
        "fermat_near_square_256": lambda inst, _: _fermat_attack(inst, 256),
    }
    attack_results = {
        name: _timed_attack(attack, reference_instances)
        for name, attack in attack_specs.items()
    }
    all_attacks_failed = all(
        result["successes"] == 0 for result in attack_results.values()
    )
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed,
        "attacks": attack_results,
        "reference_algorithm": reference_result,
        "compact_route": {
            "name": "one-bit-shift/top-bit-translation quadratic identity",
            "successes": compact_successes,
            "attempts": len(reference_instances),
            "operations": compact_operations,
            "operations_per_instance_average": round(
                compact_operations / len(reference_instances), 3
            ),
            "operations_per_instance_max": max(compact_operation_counts),
            "intended_route_bound": 40,
            "wall_clock_sec": round(compact_elapsed, 6),
        },
    }

    # G7: double native size and enlarge coefficient entropy, not witness arity.
    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=98765, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (
            doubled_ok
            and doubled["n"] == 2 * shipping["n"]
            and len(doubled["answer"]) == len(shipping["answer"])
        ),
        "base_n": shipping["n"],
        "doubled_n": doubled["n"],
        "small_factor_bits_before": shipping_params["small_factor_bits"],
        "small_factor_bits_after": doubled["small_factor_bits"],
        "answer_entries_before": len(shipping["answer"]),
        "answer_entries_after": len(doubled["answer"]),
        "doubled_verify_reason": doubled_reason,
        "next_escalation": escalate(shipping_params),
    }

    # G8: reverse the rows and carry the witness through the same relabelling.
    invariant_successes = 0
    carried_successes = 0
    unrelated_keys = []
    examples = []
    for seed in range(20):
        original = make_instance(seed=10_000 + seed, **shipping_params)
        transformed = copy.deepcopy(original)
        transformed["moduli"].reverse()
        carried_answer = list(reversed(original["answer"]))
        transformed["answer"] = carried_answer
        invariant = canonical_key(original) == canonical_key(transformed)
        carried_ok, carried_reason = verify(transformed, carried_answer)
        invariant_successes += int(invariant)
        carried_successes += int(carried_ok)
        unrelated_keys.append(canonical_key(original))
        if seed < 3:
            examples.append(
                {
                    "seed": 10_000 + seed,
                    "key_invariant": invariant,
                    "carried_verify": carried_ok,
                    "carried_reason": carried_reason,
                }
            )
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": (
            invariant_successes == 20
            and carried_successes == 20
            and distinct_keys == 20
        ),
        "invariance": {
            "successes": invariant_successes,
            "attempts": 20,
            "transformations": "reordering the two modulus rows",
        },
        "carried_witness_verifies": {
            "successes": carried_successes,
            "attempts": 20,
        },
        "unrelated_distinct_keys": distinct_keys,
        "unrelated_attempts": 20,
        "examples": examples,
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_elements = _answer_elements(shipping["answer"])
    answer_tokens = math.ceil(answer_chars / 4)
    arms = {
        name: dict(G9_ORACLE_RESULTS.get(name, {"solved": 0, "attempts": 0}))
        for name in ("bare", "hinted", "placebo")
    }
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else 0.0
    )
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else 0.0
    )
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000 and answer_elements <= 256 and 40 <= 300,
        "arms": arms,
        "arms_recorded_not_gated": True,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS.get("hinted_verdict", "not_run"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": 40,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_gates_pass"] = all(gate.get("pass") for gate in gates)
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping_params
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
