"""Exact VT-syndrome deletion-decoding problem generator for arXiv:2501.13534.

The family uses the paper's Section 2.3 binary constant-weight/set-code
construction.  It is deterministic in (n, seed, params), uses only the standard
library (gvlib is detected but not needed), performs no file I/O, and prints
nothing at import time.
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
from functools import lru_cache


# Make the repository's optional exact-arithmetic helpers importable when this
# file is run from its result directory.  This family needs only integer modular
# arithmetic, so it remains standard-library-only if gvlib is absent.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - supported dependency-free fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "VT power-syndrome vector over F_p",
        "support of a binary constant-weight codeword",
        "surviving support after asymmetric 1-to-0 errors",
    ],
    "verification_operations": [
        "exact finite-field power sums",
        "support containment and cardinality",
        "integer range and distinctness checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "recognize the deleted support as an affine image of a centered template, "
        "whereas a generic decoder reconstructs and factors its locator polynomial"
    ),
    "hardness_basis": (
        "Track B: Newton identities plus Cantor-Zassenhaus factorization has expected "
        "polynomial complexity in t and log(p) (the Section 2.3 decoder is linear in "
        "q up to polylogarithmic factors); at the medium shipping preset the bundled "
        "schoolbook factorizer takes a measured median 437032 exact operations and "
        "about 0.04 seconds, versus 232 exact operations for affine-moment normalization"
    ),
    "max_answer_tokens": 97,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": " +
        PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "A strictly increasing list of exactly t distinct integers in F_p^*, "
        "disjoint from the displayed survivors, whose first power sum is the "
        "displayed residual first syndrome; t <= 64 and p < 2^61"
    ),
    "bounds": {
        "max_symbols": 64,
        "field_modulus_bits": 61,
        "strictly_increasing": True,
        "distinct": True,
        "first_power_sum_fixed": True,
    },
}

DIFFICULTY = {
    "demo": {"n": 43, "t": 4, "survivors": 2},
    "easy": {"n": 5_000, "t": 48, "survivors": 2},
    "medium": {"n": 50_000, "t": 48, "survivors": 2},
    "hard": {"n": 200_000, "t": 48, "survivors": 2},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "The deleted symbols form an affine image over F_p of the centered odd-step "
    "template {-(t-1), -(t-3), ..., t-3, t-1}."
)
PLACEBO_HINT = (
    "Careful use of all the displayed modular power sums can help control arithmetic "
    "errors in the proposed support list."
)

# Filled from the three script-owned hardening runs.  Keeping these measurements
# as data lets selftest remain free of network and file I/O.
G9_EVIDENCE = {
    # Two medium bare calls completed and failed before the account quota was
    # exhausted.  API-error redraws are correctly excluded from the attempt count.
    "bare": {"solved": 0, "attempts": 2},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}

NOTES = r"""
Definition and certificate source.  Section 2.1, Definitions 1--2 identify a
length-w set code with a w-subset of the alphabet and define correction of t
deletions.  Sections 2.2--2.3 turn the support into a binary constant-weight
word and Definition 3 assigns its first t power sums modulo a prime p>q.
Definition 4 fixes a syndrome class, and the paragraph immediately after it
states that this class corrects t asymmetric 1-to-0 errors.  Verification here
is exactly membership in that class plus containment of the displayed survivor
support; no graph or finite-field surrogate replaces the paper's objects.

Step-0 algorithm test.  The same Section 2.3 explicitly says the cited decoder
has complexity linear in q and t up to polylogarithmic factors.  More generally,
Newton identities construct the degree-t error-locator polynomial and a standard
finite-field factorization algorithm recovers its roots in expected polynomial
time.  Thus Track A would be false.  This module declares Track B and measures a
schoolbook Newton/Cantor--Zassenhaus implementation as its reference algorithm.

Generation.  The deleted support is sampled first as c+uD in F_p, where D is
the centered odd-step template and c,u are random nonzero field elements.  Two
uniform survivors are added, and the complete support's syndrome is computed.
The paper's power-sum argument guarantees uniqueness.  Individual planted and
surviving symbols have the same essentially uniform field distribution; the
signal is relational, not a magnitude or position marker.

Easy regimes and attacks.  A generic decoder is efficient with tools, and t=1
would reveal the deletion from one subtraction, so neither is presented as
structural hardness.  The shipping instances keep t=48 and enlarge q while the
answer stays fixed.  Magnitude, survivor-neighbour, unit-scale affine, and 256
structure-aware random-restart probes are required to fail.  The reference
factorization succeeds, as Track B requires.  The affine insight reduces the
instance to its first two residual moments; modular square-root extraction and
template expansion stay below the no-tool operation cap.
""".strip()


# ---------------------------------------------------------------------------
# Basic finite-field construction

def _is_prime(value: int) -> bool:
    """Deterministic Miller--Rabin for the supported (<2^64) range."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value % prime == 0:
            return value == prime
    d = value - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
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
            return False
    return True


def _next_prime_3mod4(minimum: int) -> int:
    candidate = max(7, minimum)
    candidate += (3 - candidate) % 4
    while not _is_prime(candidate):
        candidate += 4
    return candidate


def _template(t: int) -> list[int]:
    return [-(t - 1) + 2 * i for i in range(t)]


def _power_sums(values, t: int, p: int) -> list[int]:
    sums = [0] * t
    for value in values:
        power = 1
        for k in range(t):
            power = power * value % p
            sums[k] = (sums[k] + power) % p
    return sums


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Plant an affine deleted support, then compute its VT syndrome exactly."""
    t = params.pop("t", 48)
    survivor_count = params.pop("survivors", 2)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    for name, value in (("n", n), ("t", t), ("survivors", survivor_count),
                        ("seed", seed)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if n < 11 or n >= 2**61:
        raise ValueError("n must satisfy 11 <= n < 2^61")
    if t < 4 or t > 64 or t % 2:
        raise ValueError("t must be an even integer from 4 through 64")
    if survivor_count < 1 or survivor_count > 4:
        raise ValueError("survivors must be an integer from 1 through 4")

    # Alphabet positions are 1,...,q and the syndrome field is F_p with p>q,
    # exactly as in Definition 3.  Choosing q=p-1 also gives a multiplicative
    # relabelling symmetry used by canonical_key.
    p = _next_prime_3mod4(n + 1)
    q = p - 1
    if q <= t + survivor_count or p <= 2 * t + 1:
        raise ValueError("ambient alphabet is too small for these parameters")

    rng = random.Random(seed)
    pattern = _template(t)
    while True:
        center = rng.randrange(1, p)
        scale = rng.randrange(2, p - 1)
        if scale in (1, p - 1):
            continue
        deleted = [(center + scale * d) % p for d in pattern]
        if 0 not in deleted and len(set(deleted)) == t:
            break
    deleted_set = set(deleted)

    survivors_list = []
    while len(survivors_list) < survivor_count:
        value = rng.randrange(1, p)
        if value not in deleted_set and value not in survivors_list:
            survivors_list.append(value)
    rng.shuffle(survivors_list)

    answer = sorted(deleted)
    support = answer + survivors_list
    syndrome = _power_sums(support, t, p)
    return {
        "requested_n": n,
        "p": p,
        "q": q,
        "word_weight": t + survivor_count,
        "deletions": t,
        "survivors": survivors_list,
        "syndrome": syndrome,
        "answer": answer,
    }


# ---------------------------------------------------------------------------
# Statement, parser, and exact verifier

def render(inst: dict) -> str:
    """Render the complete native set-code decoding problem."""
    p = inst["p"]
    q = inst["q"]
    t = inst["deletions"]
    weight = inst["word_weight"]
    lines = [
        "VT POWER-SYNDROME DELETION DECODING",
        "",
        f"Work in the prime field F_p with p = {p}; every congruence below is modulo p.",
        f"The alphabet positions are the ordinary integers 1 through q = {q}, inclusive.",
        "A support is a set of distinct alphabet positions.  It represents the 1-positions",
        "of a binary constant-weight word; a deletion changes a 1 to 0.",
        "",
        f"The original support had exactly {weight} positions.  Exactly t = {t} positions",
        "were deleted.  The surviving positions are:",
        "SURVIVORS " + " ".join(map(str, inst["survivors"])),
        "",
        "For k=1,...,t, the k-th VT syndrome is the sum of x^k over every x in",
        "the original support, reduced to the unique integer in 0,...,p-1.",
        "The syndrome vector (entries listed in order k=1,...,t) is:",
        "SYNDROME " + " ".join(map(str, inst["syndrome"])),
        "",
        f"Recover the set of exactly {t} deleted positions.  Your positions must be",
        f"distinct integers in 1,...,{q}, disjoint from SURVIVORS, and written in",
        "strictly increasing order.  A candidate is correct exactly when adjoining it",
        "to SURVIVORS reproduces every displayed syndrome entry.",
        "",
        "Give your final answer inside <answer></answer> tags as a comma-separated",
        f"list of exactly {t} decimal integers, with no brackets.",
        "Example for a four-position answer: <answer>1, 4, 9, 16</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"```(?:json|text)?\s*(.*?)\s*```", re.I | re.S)


def _parse_int_list(body: str):
    body = body.strip()
    if body.startswith("[") and body.endswith("]"):
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            return None
        if (isinstance(value, list) and
                all(isinstance(v, int) and not isinstance(v, bool) for v in value)):
            return value
        return None
    if not body or not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", body):
        return None
    try:
        return [int(part.strip()) for part in body.split(",")]
    except ValueError:
        return None


def parse_answer(text: str) -> object | None:
    """Extract the advertised integer list from tags, fences, or nearby prose."""
    if not isinstance(text, str):
        return None
    bodies = list(reversed(_ANSWER_RE.findall(text)))
    bodies.extend(reversed(_FENCE_RE.findall(text)))
    for body in bodies:
        parsed = _parse_int_list(body)
        if parsed is not None:
            return parsed
    # Tolerate a bare JSON list embedded in a final sentence.
    decoder = json.JSONDecoder()
    for start in (i for i, char in enumerate(text) if char == "["):
        try:
            value, _ = decoder.raw_decode(text[start:])
        except (TypeError, ValueError):
            continue
        if (isinstance(value, list) and
                all(isinstance(v, int) and not isinstance(v, bool) for v in value)):
            return value
    return None


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Check any deleted support by exact substitution; never inspect inst['answer']."""
    t = inst["deletions"]
    p = inst["p"]
    q = inst["q"]
    if not isinstance(answer, list):
        return False, "answer must be a list of integer positions"
    if not answer:
        return False, "answer is empty"
    if len(answer) != t:
        return False, f"expected exactly {t} deleted positions"
    if any(isinstance(value, bool) or not isinstance(value, int) for value in answer):
        return False, "every position must be an integer"
    if len(set(answer)) != len(answer):
        return False, "deleted positions must be distinct"
    if answer != sorted(answer):
        return False, "deleted positions must be in strictly increasing order"
    if any(value < 1 or value > q for value in answer):
        return False, f"a position is outside the inclusive alphabet range 1..{q}"
    survivor_set = set(inst["survivors"])
    if any(value in survivor_set for value in answer):
        return False, "a deleted position is also listed as a survivor"

    # Compare one power at a time.  This is still exact substitution into every
    # displayed identity for a correct witness, while letting the 200,000-sample
    # density audit reject a random candidate at its first bad power instead of
    # needlessly evaluating all t powers.
    values = list(answer) + inst["survivors"]
    powers = [1] * len(values)
    for k, wanted in enumerate(inst["syndrome"], 1):
        actual = 0
        for index, value in enumerate(values):
            powers[index] = powers[index] * value % p
            actual = (actual + powers[index]) % p
        if actual != wanted:
            return False, f"VT syndrome mismatch at power k={k}"
    return True, "ok"


# ---------------------------------------------------------------------------
# Candidate language and exact counting

def _residual_first(inst: dict) -> int:
    return (inst["syndrome"][0] - sum(inst["survivors"])) % inst["p"]


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the obvious first-syndrome-constrained answer language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    p = inst["p"]
    t = inst["deletions"]
    forbidden = set(inst["survivors"])
    target = _residual_first(inst)
    # Choosing an ordered (t-1)-tuple and deriving its last member gives every
    # valid unordered t-set exactly t! preimages, so rejection preserves uniformity.
    while True:
        prefix = []
        used = set(forbidden)
        while len(prefix) < t - 1:
            value = rng.randrange(1, p)
            if value not in used:
                used.add(value)
                prefix.append(value)
        last = (target - sum(prefix)) % p
        if last != 0 and last not in used:
            return sorted(prefix + [last])


def _count_language(inst: dict) -> int:
    """Count t-subsets of F_p excluding 0/survivors with prescribed sum."""
    p = inst["p"]
    t = inst["deletions"]
    forbidden = tuple([0] + sorted(set(inst["survivors"])))
    target = _residual_first(inst)

    @lru_cache(maxsize=None)
    def count(j: int, size: int, total: int) -> int:
        if size < 0 or size > p - j:
            return 0
        total %= p
        if size == 0:
            return int(total == 0)
        if j == 0:
            # Translation by c sends a size-k subset's sum to sum+k*c.
            # Since 0<k<p, the p sum classes of F_p are equinumerous.
            return math.comb(p, size) // p
        f = forbidden[j - 1]
        # Subsets avoiding f = all previously-allowed subsets minus those
        # containing f; remove f from the latter.
        return count(j - 1, size, total) - count(j, size - 1, total - f)

    return count(len(forbidden), t, target)


def search_space(inst: dict) -> int | None:
    """Exact size of the first-syndrome-constrained certificate language."""
    return _count_language(inst)


def enumerate_all(inst: dict) -> int | None:
    """Brute-force valid witnesses when the derived-last enumeration is small."""
    p = inst["p"]
    t = inst["deletions"]
    forbidden = {0, *inst["survivors"]}
    allowed_count = p - len(forbidden)
    work = math.comb(allowed_count, t - 1)
    if work > 300_000:
        return None
    allowed = [value for value in range(1, p) if value not in forbidden]
    target = _residual_first(inst)
    valid = 0
    for prefix in itertools.combinations(allowed, t - 1):
        last = (target - sum(prefix)) % p
        # Count each full set only when the derived member is its largest.
        if last in forbidden or last <= prefix[-1]:
            continue
        candidate = list(prefix) + [last]
        if verify(inst, candidate)[0]:
            valid += 1
    return valid


# ---------------------------------------------------------------------------
# Generic finite-field reference decoder (Newton + Cantor--Zassenhaus)

def _poly_trim(poly, p):
    out = [value % p for value in poly]
    while len(out) > 1 and out[-1] == 0:
        out.pop()
    return out


def _poly_divmod(a, b, p, counter):
    a = _poly_trim(a, p)
    b = _poly_trim(b, p)
    if b == [0]:
        raise ZeroDivisionError("polynomial division by zero")
    if len(a) < len(b):
        return [0], a
    quotient = [0] * (len(a) - len(b) + 1)
    inv = pow(b[-1], -1, p)
    while len(a) >= len(b) and a != [0]:
        shift = len(a) - len(b)
        factor = a[-1] * inv % p
        counter["operations"] += 1
        quotient[shift] = factor
        for j, coefficient in enumerate(b):
            a[shift + j] = (a[shift + j] - factor * coefficient) % p
            counter["operations"] += 2
        a = _poly_trim(a, p)
    return _poly_trim(quotient, p), a


def _poly_monic(poly, p, counter):
    poly = _poly_trim(poly, p)
    inv = pow(poly[-1], -1, p)
    counter["operations"] += len(poly)
    return [(value * inv) % p for value in poly]


def _poly_gcd(a, b, p, counter):
    a = _poly_trim(a, p)
    b = _poly_trim(b, p)
    while b != [0]:
        _, remainder = _poly_divmod(a, b, p, counter)
        a, b = b, remainder
    return _poly_monic(a, p, counter)


def _poly_mulmod(a, b, modulus, p, counter):
    raw = [0] * (len(a) + len(b) - 1)
    for i, avalue in enumerate(a):
        if avalue:
            for j, bvalue in enumerate(b):
                raw[i + j] = (raw[i + j] + avalue * bvalue) % p
                counter["operations"] += 2
    _, remainder = _poly_divmod(raw, modulus, p, counter)
    return remainder


def _poly_powmod(base, exponent, modulus, p, counter):
    result = [1]
    base = _poly_trim(base, p)
    while exponent:
        if exponent & 1:
            result = _poly_mulmod(result, base, modulus, p, counter)
        exponent >>= 1
        if exponent:
            base = _poly_mulmod(base, base, modulus, p, counter)
    return result


def _locator_from_instance(inst: dict, counter) -> list[int]:
    p = inst["p"]
    t = inst["deletions"]
    survivor_sums = _power_sums(inst["survivors"], t, p)
    counter["operations"] += 2 * t * len(inst["survivors"])
    powers = [(a - b) % p for a, b in zip(inst["syndrome"], survivor_sums)]
    counter["operations"] += t
    elementary = [1]
    for k in range(1, t + 1):
        total = 0
        for i in range(1, k + 1):
            term = elementary[k - i] * powers[i - 1]
            total = (total + term if i % 2 else total - term) % p
            counter["operations"] += 2
        elementary.append(total * pow(k, -1, p) % p)
        counter["operations"] += 1
    # Product (z-r): ascending coefficients (-1)^(t-j)e_(t-j).
    return [(((-1) ** (t - j)) * elementary[t - j]) % p
            for j in range(t + 1)]


def _factor_linear_roots(poly, p, rng, counter):
    poly = _poly_monic(poly, p, counter)
    degree = len(poly) - 1
    if degree == 0:
        return []
    if degree == 1:
        counter["operations"] += 2
        return [(-poly[0] * pow(poly[1], -1, p)) % p]
    for _ in range(128):
        counter["iterations"] += 1
        probe = [rng.randrange(p) for _ in range(degree)]
        direct = _poly_gcd(poly, probe, p, counter)
        ddeg = len(direct) - 1
        if 0 < ddeg < degree:
            other, remainder = _poly_divmod(poly, direct, p, counter)
            if remainder != [0]:
                raise AssertionError("internal polynomial division failure")
            return (_factor_linear_roots(direct, p, rng, counter) +
                    _factor_linear_roots(other, p, rng, counter))
        half = _poly_powmod(probe, (p - 1) // 2, poly, p, counter)
        half[0] = (half[0] - 1) % p
        factor = _poly_gcd(poly, half, p, counter)
        fdeg = len(factor) - 1
        if 0 < fdeg < degree:
            other, remainder = _poly_divmod(poly, factor, p, counter)
            if remainder != [0]:
                raise AssertionError("internal polynomial division failure")
            return (_factor_linear_roots(factor, p, rng, counter) +
                    _factor_linear_roots(other, p, rng, counter))
    raise RuntimeError("Cantor-Zassenhaus split budget exhausted")


def _reference_decode(inst: dict, seed: int = 0):
    counter = {"operations": 0, "iterations": 0}
    locator = _locator_from_instance(inst, counter)
    roots = sorted(_factor_linear_roots(locator, inst["p"],
                                        random.Random(seed), counter))
    return roots, counter


def _inverse_counted(value: int, p: int, counter) -> int:
    """Extended-Euclidean inverse with an explicit arithmetic-operation count."""
    old_r, r = value % p, p
    old_s, s = 1, 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        counter["operations"] += 5  # division and two multiply/subtract updates
    if old_r != 1:
        raise ZeroDivisionError("noninvertible field element")
    return old_s % p


def _pow_counted(base: int, exponent: int, p: int, counter) -> int:
    result = 1
    base %= p
    while exponent:
        if exponent & 1:
            result = result * base % p
            counter["operations"] += 1
        exponent >>= 1
        if exponent:
            base = base * base % p
            counter["operations"] += 1
    return result


def _compact_decode(inst: dict):
    """Decode this generated distribution through its affine moment invariant."""
    p = inst["p"]
    t = inst["deletions"]
    counter = {"operations": 0}
    first = inst["syndrome"][0]
    second = inst["syndrome"][1]
    for value in inst["survivors"]:
        first = (first - value) % p
        second = (second - value * value) % p
        counter["operations"] += 3
    inv_t = _inverse_counted(t, p, counter)
    center = first * inv_t % p
    counter["operations"] += 1
    centered_second = (second - t * center * center) % p
    counter["operations"] += 3
    # For D={-(t-1),-(t-3),...,t-1}, sum(d^2)=t(t^2-1)/3.
    d2 = t * (t * t - 1) % p
    d2 = d2 * _inverse_counted(3, p, counter) % p
    counter["operations"] += 4
    scale_squared = centered_second * _inverse_counted(d2, p, counter) % p
    counter["operations"] += 1
    # make_instance chooses p == 3 (mod 4), so this exponent is a square root.
    scale = _pow_counted(scale_squared, (p + 1) // 4, p, counter)
    if scale * scale % p != scale_squared:
        raise ArithmeticError("affine second moment is not a square")
    counter["operations"] += 1
    roots = []
    for value in _template(t):
        roots.append((center + scale * value) % p)
        counter["operations"] += 2
    return sorted(roots), counter


# ---------------------------------------------------------------------------
# Cheap attacks, affine symmetry, and canonical key

def _complete_from_order(inst: dict, ordered_values) -> list[int]:
    t = inst["deletions"]
    p = inst["p"]
    forbidden = {0, *inst["survivors"]}
    target = _residual_first(inst)
    chosen = []
    used = set(forbidden)
    for value in ordered_values:
        value %= p
        if value in used:
            continue
        if len(chosen) < t - 2:
            chosen.append(value)
            used.add(value)
            continue
        last = (target - sum(chosen) - value) % p
        if last not in used and last not in (0, value):
            return sorted(chosen + [value, last])
    return random_candidate(inst, random.Random(0xC0DEC))


def _attack_outlier_magnitude(inst: dict):
    p = inst["p"]
    order = itertools.chain.from_iterable((lo, p - lo) for lo in range(1, p // 2 + 1))
    return _complete_from_order(inst, order)


def _attack_greedy_near_survivor(inst: dict):
    p = inst["p"]
    anchor = inst["survivors"][0]
    order = (value for distance in range(p)
             for value in ((anchor - distance) % p, (anchor + distance) % p))
    return _complete_from_order(inst, order)


def _attack_unit_scale_ansatz(inst: dict):
    p = inst["p"]
    t = inst["deletions"]
    center = _residual_first(inst) * pow(t, -1, p) % p
    candidate = sorted({(center + d) % p for d in _template(t)})
    if (len(candidate) == t and 0 not in candidate and
            not set(candidate).intersection(inst["survivors"])):
        return candidate
    return _complete_from_order(inst, range(1, p))


def _scale_instance(inst: dict, multiplier: int, reverse_survivors=False) -> dict:
    p = inst["p"]
    multiplier %= p
    if multiplier == 0:
        raise ValueError("multiplier must be nonzero modulo p")
    out = dict(inst)
    survivors_list = [(multiplier * value) % p for value in inst["survivors"]]
    if reverse_survivors:
        survivors_list.reverse()
    out["survivors"] = survivors_list
    power = 1
    scaled_syndrome = []
    for value in inst["syndrome"]:
        power = power * multiplier % p
        scaled_syndrome.append(value * power % p)
    out["syndrome"] = scaled_syndrome
    if "answer" in inst:
        out["answer"] = sorted(multiplier * value % p for value in inst["answer"])
    return out


def canonical_key(inst: dict) -> str:
    """Normalize survivor order and every multiplicative field relabelling."""
    p = inst["p"]
    survivors_list = list(inst["survivors"])
    if not survivors_list:
        raise ValueError("canonical_key requires at least one survivor")
    forms = []
    for base in survivors_list:
        scale = pow(base, -1, p)
        normalized_survivors = tuple(sorted(value * scale % p
                                            for value in survivors_list))
        normalized_syndrome = []
        power = 1
        for value in inst["syndrome"]:
            power = power * scale % p
            normalized_syndrome.append(value * power % p)
        forms.append((normalized_survivors, tuple(normalized_syndrome)))
    canonical = min(forms)
    payload = json.dumps({
        "p": p,
        "t": inst["deletions"],
        "weight": inst["word_weight"],
        "survivors": canonical[0],
        "syndrome": canonical[1],
    }, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Enlarge the field first; only later use still-bounded fixed-shape dials."""
    out = dict(params)
    ambient = int(out.get("n", 200_000))
    survivor_count = int(out.get("survivors", 2))
    t = int(out.get("t", 48))
    if survivor_count > 1:
        out["survivors"] = survivor_count - 1
        out["n"] = ambient * 2
        out["t"] = t
        return out
    if ambient < 2**57:
        out["n"] = ambient * 4
        out["survivors"] = survivor_count
        out["t"] = t
        return out
    if t < 64:
        out["t"] = min(64, t + 8)
        out["n"] = ambient
        out["survivors"] = survivor_count
        return out
    return "cap_bound"


# ---------------------------------------------------------------------------
# Mandatory gates

def _answer_token_estimate(answer) -> int:
    # Count punctuation and decimal runs in the exact JSON wire representation.
    return len(re.findall(r"-?\d+|[\[\],]", json.dumps(answer)))


def _intended_route_operations(inst: dict) -> int:
    _, counter = _compact_decode(inst)
    return counter["operations"]


def selftest() -> dict:
    """Run gates G1--G9 and return a fully JSON-native measurement report."""
    report = {}

    # G1: every preset and several seeds.
    g1_failures = []
    g1_total = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(3):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_total += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "verified": g1_total,
        "failures": g1_failures,
        "construction": "inverse generation of an affine support before syndromes",
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=9173, **ship_params)
    planted = list(inst["answer"])

    # G2: route five corruptions to five distinct diagnostics.
    swapped = list(planted)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = list(planted)
    duplicated[1] = duplicated[0]
    outside = list(planted)
    outside[-1] = inst["p"]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_one": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": outside,
    }
    g2_cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        g2_cases[name] = {"rejected": not ok, "reason": reason}
    g2_reasons = [item["reason"] for item in g2_cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in g2_cases.values()) and
                len(set(g2_reasons)) == len(g2_reasons),
        "cases": g2_cases,
        "distinct_reasons": len(set(g2_reasons)),
    }

    # G3: tagged comma format and a common fenced-JSON deviation.
    comma = ", ".join(map(str, planted))
    response = ("The power sums check out.\n```text\n<answer>" + comma +
                "</answer>\n```\nThat is my final support.")
    fenced_json = "Here is the support:\n```json\n" + json.dumps(planted) + "\n```"
    parsed = parse_answer(response)
    parsed_json = parse_answer(fenced_json)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parsed_json == planted,
        "tagged_comma_parsed": parsed == planted,
        "fenced_json_parsed": parsed_json == planted,
    }

    # G4/G5 density: every sample already has correct shape, range,
    # distinctness, survivor exclusion, ordering, and first power sum.
    guess_rng = random.Random(0x250113534)
    sample_total = 200_000
    hits = 0
    for _ in range(sample_total):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            hits += 1
    probability = hits / sample_total
    language_size = search_space(inst)
    exact_probability = 1.0 / language_size
    report["G4_guess_resistance"] = {
        "pass": (sample_total >= 200_000 and hits == 0 and
                 exact_probability < 1e-6),
        "hits": hits,
        "total": sample_total,
        "measured_probability": probability,
        "exact_probability": exact_probability,
        "exact_valid_answers": 1,
        "uniqueness_basis": "Definition 4: correction of t asymmetric 1-to-0 errors",
        "search_space": language_size,
        "prior": "uniform t-subsets satisfying every shape rule and the first syndrome",
    }

    # The strongest available algorithm is expected to solve on Track B.
    baseline_start = time.perf_counter()
    decoded, baseline_counter = _reference_decode(inst, seed=12345)
    baseline_wall = time.perf_counter() - baseline_start
    baseline_ok = verify(inst, decoded)[0]
    compact, compact_counter = _compact_decode(inst)
    compact_ok = verify(inst, compact)[0]
    demo = make_instance(seed=5, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": (exact_probability < 1e-6 and baseline_ok and compact_ok and
                 demo_count is not None),
        "shipping_density_hits": hits,
        "shipping_density_total": sample_total,
        "shipping_density_estimate": probability,
        "shipping_density_exact": exact_probability,
        "shipping_valid_answers": 1,
        "shipping_solution_count_basis": (
            "Definition 4's t-asymmetric-error correction property; sampled density "
            "is reported because shipping enumeration is capped"
        ),
        "demo_exact_solution_count": demo_count,
        "baseline_wall_seconds": round(baseline_wall, 6),
        "baseline_operations": baseline_counter["operations"],
        "baseline_factor_splits": baseline_counter["iterations"],
        "baseline_verified": baseline_ok,
        "baseline_algorithm": "Newton identities plus Cantor-Zassenhaus factorization",
        "compact_route_operations": compact_counter["operations"],
        "compact_route_verified": compact_ok,
    }

    # G6: four no-tool/cheap attacks must fail; reference factorization succeeds.
    attack_names = (
        "outlier_alternating_extremes",
        "greedy_nearest_survivor",
        "random_restart_256",
        "by_hand_unit_scale_ansatz",
    )
    successes = {name: 0 for name in attack_names}
    ref_successes = 0
    ref_times = []
    ref_operations = []
    ref_splits = []
    for offset in range(8):
        attack_inst = make_instance(seed=20_000 + offset, **ship_params)
        candidates = {
            "outlier_alternating_extremes": _attack_outlier_magnitude(attack_inst),
            "greedy_nearest_survivor": _attack_greedy_near_survivor(attack_inst),
            "by_hand_unit_scale_ansatz": _attack_unit_scale_ansatz(attack_inst),
        }
        restart_rng = random.Random(30_000 + offset)
        restart_hit = False
        for _ in range(256):
            if verify(attack_inst, random_candidate(attack_inst, restart_rng))[0]:
                restart_hit = True
                break
        successes["random_restart_256"] += int(restart_hit)
        for name, candidate in candidates.items():
            successes[name] += int(verify(attack_inst, candidate)[0])

        start = time.perf_counter()
        roots, count = _reference_decode(attack_inst, seed=40_000 + offset)
        ref_times.append(time.perf_counter() - start)
        ref_operations.append(count["operations"])
        ref_splits.append(count["iterations"])
        ref_successes += int(verify(attack_inst, roots)[0])

    attack_report = {
        name: {"successes": successes[name], "attempts": 8}
        for name in attack_names
    }
    sorted_times = sorted(ref_times)
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in attack_report.values()) and
                ref_successes == 8,
        "attacks": attack_report,
        "reference_algorithm": {
            "name": "Newton identities plus Cantor-Zassenhaus finite-field factorization",
            "complexity": "expected polynomial in t and log(p); schoolbook polynomial arithmetic",
            "wall_clock_sec_median": round((sorted_times[3] + sorted_times[4]) / 2, 6),
            "operations_median": sorted(ref_operations)[len(ref_operations) // 2],
            "factor_splits_median": sorted(ref_splits)[len(ref_splits) // 2],
            "solves": f"{ref_successes}/8, as expected on Track B",
        },
    }

    # G7: double the ambient alphabet without lengthening the answer.
    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["q"] > inst["q"] and
                len(doubled["answer"]) == len(inst["answer"]),
        "base_alphabet": inst["q"],
        "doubled_alphabet": doubled["q"],
        "base_answer_elements": len(inst["answer"]),
        "doubled_answer_elements": len(doubled["answer"]),
        "verify_reason": doubled_reason,
    }

    # G8: survivor reorder, multiplicative alphabet relabelling, and composition.
    invariance_checks = 0
    witness_checks = 0
    g8_failures = []
    unrelated = []
    for offset in range(20):
        original = make_instance(seed=80_000 + offset, **ship_params)
        key = canonical_key(original)
        unrelated.append(key)

        reordered = dict(original)
        reordered["survivors"] = list(reversed(original["survivors"]))
        invariance_checks += 1
        witness_checks += 1
        if canonical_key(reordered) != key:
            g8_failures.append({"seed": offset, "transform": "survivor reorder"})
        if not verify(reordered, original["answer"])[0]:
            g8_failures.append({"seed": offset, "transform": "reorder witness"})

        relabel_rng = random.Random(90_000 + offset)
        multiplier = relabel_rng.randrange(1, original["p"])
        scaled = _scale_instance(original, multiplier)
        invariance_checks += 1
        witness_checks += 1
        if canonical_key(scaled) != key:
            g8_failures.append({"seed": offset, "transform": "field scaling"})
        if not verify(scaled, scaled["answer"])[0]:
            g8_failures.append({"seed": offset, "transform": "scaled witness"})

        composed = _scale_instance(original, multiplier, reverse_survivors=True)
        invariance_checks += 1
        witness_checks += 1
        if canonical_key(composed) != key:
            g8_failures.append({"seed": offset, "transform": "scaling plus reorder"})
        if not verify(composed, composed["answer"])[0]:
            g8_failures.append({"seed": offset, "transform": "composed witness"})

    distinct = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariance_checks,
        "witness_preservation_checks": witness_checks,
        "unrelated_distinct": distinct,
        "unrelated_total": 20,
        "failures": g8_failures,
        "method": "normalize by each survivor and minimize over multiplicative scalings",
    }

    # G9(a) measurements are injected only after script-owned runs.  Parts (b,c)
    # determine pass; the three-arm comparison itself is deliberately diagnostic.
    # Measure a reproducible seed panel, then include the elementary theoretical
    # character bound (all t entries have as many digits as q).  The latter makes
    # the cap check independent of whether this particular panel happens to draw
    # a small field element.
    size_panel = [make_instance(seed=910_000 + offset, **ship_params)["answer"]
                  for offset in range(256)]
    measured_answer_chars = max(
        len(json.dumps(answer, separators=(",", ":"))) for answer in size_panel)
    theoretical_answer_chars = 2 + (len(inst["answer"]) - 1) + \
        len(inst["answer"]) * len(str(inst["q"]))
    answer_chars = max(measured_answer_chars, theoretical_answer_chars)
    answer_tokens = max(_answer_token_estimate(answer) for answer in size_panel)
    answer_elements = max(len(answer) for answer in size_panel)
    route_ops = _intended_route_operations(inst)
    hinted = G9_EVIDENCE["hinted"]
    placebo = G9_EVIDENCE["placebo"]
    hinted_rate = (hinted["solved"] / hinted["attempts"]
                   if hinted["attempts"] else 0.0)
    placebo_rate = (placebo["solved"] / placebo["attempts"]
                    if placebo["attempts"] else 0.0)
    hinted_hardened = (G9_EVIDENCE["hinted_verdict"] == "hardened" and
                       hinted["attempts"] >= 3)
    within_caps = (answer_chars <= 2_000 and answer_elements <= 256 and
                   route_ops <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": {
            "bare": dict(G9_EVIDENCE["bare"]),
            "hinted": dict(hinted),
            "placebo": dict(placebo),
        },
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_chars_measured_256_seeds": measured_answer_chars,
        "answer_chars_theoretical_bound": theoretical_answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": route_ops,
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship_params)
    return report


__all__ = [
    "TRACK", "PROBLEM_PROFILE", "NATIVE", "CERTIFICATE_LANGUAGE", "DIFFICULTY",
    "SHIPPING_DIFFICULTY", "STRUCTURAL_HINT", "PLACEBO_HINT", "NOTES",
    "make_instance", "render", "parse_answer", "verify", "random_candidate",
    "search_space", "enumerate_all", "canonical_key", "escalate", "selftest",
]
