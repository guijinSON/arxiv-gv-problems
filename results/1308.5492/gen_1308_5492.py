"""Verified generator for arXiv:1308.5492, Four squares of primes and powers of 2.

The paper's equation (1.1) represents an even integer by four prime squares and
46 powers of two.  This module fixes and displays the 46 exponents, then asks
for the four distinct prime bases in a displayed interval.  Instances are
inverse-generated from a hidden four-term prime arithmetic progression; the
verifier accepts every increasing prime quadruple that satisfies the equation.

Only exact integer arithmetic is used.  Importing this file performs no I/O and
has no observable side effects.
"""

from __future__ import annotations

import bisect
import hashlib
import json
import math
import os
import random
import re
import sys
import time
from typing import Any


# Make the repository helper library available when harden.py is launched from
# this result directory.  This family needs only integers, so gvlib is optional.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - the standard-library path is complete
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "number_theory",
    "object_regime": "finite_discrete",
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "even integer",
        "four distinct prime bases in an integer interval",
        "46 powers of two",
    ],
    "verification_operations": [
        "deterministic integer primality testing",
        "exact integer squaring",
        "exact powers-of-two summation",
        "integer equality and interval comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Centering the four hidden prime bases exposes an arithmetic progression "
        "and turns their square subtotal into one square plus five times a square; "
        "without that change of variables one searches prime-pair sums."
    ),
    "hardness_basis": (
        "Track B, in the k=46 regime of equation (1.1) and Theorem 1.1: a "
        "segmented sieve followed by meet-in-the-middle four-sum costs "
        "O(n log log U + m^2) for m interval primes and, at the shipping preset, "
        "averaged 0.38 million prime-pair visits (1.55 million counted exact "
        "operations) and 0.154 seconds in the final recorded shipping run; the "
        "centered-progression route tests at most 28 wheel multiples in 164 exact "
        "operations, still requiring the solver to discover the progression identity."
    ),
    "max_answer_tokens": 10,
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

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON-native list [p0,p1,p2,p3] of exactly four distinct primes, "
        "strictly increasing, each in the displayed inclusive interval, and "
        "whose sum lies in the necessary integer range obtained from the "
        "displayed square subtotal and interval."
    ),
    "bounds": {
        "prime_count": 4,
        "distinct": True,
        "ordering": "strictly increasing",
        "minimum": "instance lower bound",
        "maximum": "instance upper bound",
        "sum": "necessary bounds derived from the square equation",
    },
}

DIFFICULTY = {
    "demo": {
        "n": 650,
        "prime_floor": 10,
        "min_gap_slot": 1,
        "gap_slots": 1,
        "power_max": 8,
    },
    "easy": {
        "n": 9_000,
        "prime_floor": 1_000_000,
        "min_gap_slot": 9,
        "gap_slots": 14,
        "power_max": 22,
    },
    "medium": {
        "n": 18_000,
        "prime_floor": 5_000_000,
        "min_gap_slot": 13,
        "gap_slots": 24,
        "power_max": 32,
    },
    "hard": {
        "n": 32_000,
        "prime_floor": 10_000_000,
        "min_gap_slot": 25,
        "gap_slots": 48,
        "power_max": 40,
    },
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "The four prime bases form an arithmetic progression whose common "
    "difference is a positive multiple of 210."
)
PLACEBO_HINT = (
    "Careful attention to the inclusive interval and exact square subtotal "
    "helps prevent transcription errors."
)

# Filled from the script-owned transcripts after the three oracle arms run.
G9_MEASUREMENTS = {
    "bare": {"solved": 0, "attempts": 2},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "oracle_unreachable_http_403_key_limit",
}

NOTES = r"""
Definition.  Equation (1.1) in the Introduction is
N=p1^2+p2^2+p3^2+p4^2+2^nu1+...+2^nuk, and Theorem 1.1 sets k=46;
neither statement requires distinct primes or states exponent bounds.  The
Section 2 count R_k uses ordered primes in the narrow box B and 4<=nu<=L,
allowing repeats.  Section 5 first chooses two exponents in {1,2,3} to fix the
class modulo 8, then proves the remaining k=44 representation with exponents
from Section 2.  This module keeps the native integer, prime-square, and
power-of-two objects, but supplies all 46 exponents and requires four distinct
prime bases.  Those are explicit bounded specializations guaranteed by inverse
generation, not by Theorem 1.1 and not by a graph or finite-field reduction.

Step 0 and the easy boundary.  Theorem 1.1 is existential: the proof in Section
5 compares major- and minor-arc estimates and gives no recovery algorithm or
effective threshold for "sufficiently large".  The paper contains no
computational recovery theorem or tractable special-case result, so it cannot
justify a Track-A hardness claim for this inverse-generated distribution.  For
this supplied-exponent specialization, a specialist can enumerate the primes
in the interval and solve the remaining four-sum by hashing prime-square pairs
in O(m^2) time and memory.  That successful external standard algorithm is
reported openly, making this Track B.

Construction and compact route.  The generator samples p and d first, with
d=210s, and retains p,p+d,p+2d,p+3d only when all four are prime.  It samples
the exponent multiset and interval placement from independent RNG streams,
then forms N by exact addition.  Thus the certificate is known by inverse
generation, never recovered from the completed instance.  If the progression
is noticed, its prime-square subtotal T obeys
T=(2p+3d)^2+5d^2.  The displayed interval limits d to at most 50 positive
multiples of 210 at the largest named preset, and at most 28 at the medium
shipping preset.  Maintaining 5d^2 by a first-difference recurrence gives the
measured 164-operation intended route at shipping size.

Attacks.  Independent RNG streams prevent the power list and padding from
encoding the plant.  The panel tries interval quartiles, a nearest-residual
greedy rule, consecutive-prime windows near sqrt(T/4), 512 random legal
quadruples, and the first eight hand-scale 210-step progression guesses.  The
full meet-in-the-middle algorithm is intentionally outside attacks and appears
as Track B's successful reference_algorithm.

Guess prior.  Writing each prime as lower+x makes the square equation imply an
integer interval for sum(x), containing 97 values at the measured shipping
seed.  Both random_candidate and search_space condition on this freely
deducible constraint; sampling from all interval-prime quadruples would
exaggerate the search space.  A discarded 10^10-scale draft made this interval
a singleton and thereby gave away a much shorter moment calculation.
""".strip()


_MR_BASES_64 = (2, 325, 9375, 28178, 450775, 9780504, 1795265022)
_SMALL_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
_WHEEL = 210
_WHEEL_RESIDUES = tuple(r for r in range(1, _WHEEL) if math.gcd(r, _WHEEL) == 1)


def _is_prime(value: int) -> bool:
    """Deterministic Miller-Rabin for every unsigned 64-bit integer."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 2:
        return False
    for prime in _SMALL_PRIMES:
        if value % prime == 0:
            return value == prime
    if value >= 1 << 64:
        # Current presets never enter this branch.  Trial division is exact and
        # keeps verify honest if a caller supplies a larger candidate.
        limit = math.isqrt(value)
        divisor = 41
        while divisor <= limit:
            if value % divisor == 0:
                return False
            divisor += 2
        return True
    odd_part = value - 1
    twos = 0
    while odd_part % 2 == 0:
        twos += 1
        odd_part //= 2
    for base in _MR_BASES_64:
        if base % value == 0:
            continue
        x = pow(base, odd_part, value)
        if x in (1, value - 1):
            continue
        for _ in range(twos - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _base_primes(limit: int) -> list[int]:
    if limit < 2:
        return []
    marks = bytearray(b"\x01") * (limit + 1)
    marks[0:2] = b"\x00\x00"
    for p in range(2, math.isqrt(limit) + 1):
        if marks[p]:
            start = p * p
            marks[start:limit + 1:p] = b"\x00" * (((limit - start) // p) + 1)
    return [p for p in range(2, limit + 1) if marks[p]]


def _primes_in_interval(lower: int, upper: int) -> list[int]:
    """Exact segmented sieve for the interval used by every supported preset."""
    if upper < lower or upper < 2:
        return []
    lower = max(lower, 2)
    root = math.isqrt(upper)
    # A root this large would make the segmented pre-sieve counterproductive.
    # The supported presets and their one-step scaling tests stay below it.
    if root > 2_000_000:
        return [v for v in range(lower, upper + 1) if _is_prime(v)]
    segment = bytearray(b"\x01") * (upper - lower + 1)
    for prime in _base_primes(root):
        start = max(prime * prime, ((lower + prime - 1) // prime) * prime)
        if start <= upper:
            segment[start - lower:upper - lower + 1:prime] = (
                b"\x00" * (((upper - start) // prime) + 1)
            )
    return [lower + i for i, flag in enumerate(segment) if flag]


def _validate_params(
    n: int,
    prime_floor: int,
    min_gap_slot: int,
    gap_slots: int,
    power_max: int,
) -> None:
    values = (n, prime_floor, min_gap_slot, gap_slots, power_max)
    if any(isinstance(v, bool) or not isinstance(v, int) for v in values):
        raise ValueError("all parameters must be integers")
    if n < 650:
        raise ValueError("n must be at least 650")
    if prime_floor < 2:
        raise ValueError("prime_floor must be at least 2")
    if not 1 <= min_gap_slot <= gap_slots:
        raise ValueError("gap slots must satisfy 1 <= min_gap_slot <= gap_slots")
    if 3 * _WHEEL * gap_slots > n:
        raise ValueError("n is too small to contain the planted progression")
    if power_max < 4:
        raise ValueError("power_max must be at least 4")


def _demo_progression(index: int) -> tuple[int, int]:
    """Return the indexed small four-prime progression of common gap 210."""
    wanted = index % 32
    found = 0
    for start in range(2, 2_000_000):
        if all(_is_prime(start + k * _WHEEL) for k in range(4)):
            if found == wanted:
                return start, _WHEEL
            found += 1
    raise RuntimeError("could not construct demo prime progression")


def _sample_progression(
    seed: int,
    prime_floor: int,
    min_gap_slot: int,
    gap_slots: int,
) -> tuple[int, int]:
    if prime_floor == 10 and min_gap_slot == gap_slots == 1:
        return _demo_progression(seed)
    rng = random.Random(seed ^ 0x6A09E667F3BCC909)
    gap = _WHEEL * rng.randint(min_gap_slot, gap_slots)
    q0 = max(1, (prime_floor + _WHEEL - 1) // _WHEEL)
    q_span = max(1_000, q0)
    for _ in range(200_000):
        q = q0 + rng.randrange(q_span)
        start = _WHEEL * q + rng.choice(_WHEEL_RESIDUES)
        if start + 3 * gap >= 1 << 63:
            continue
        if all(_is_prime(start + k * gap) for k in range(4)):
            return start, gap
    raise RuntimeError("could not sample a four-prime arithmetic progression")


def make_instance(
    n: int,
    seed: int = 0,
    prime_floor: int = 10_000_000_000,
    min_gap_slot: int = 25,
    gap_slots: int = 48,
    power_max: int = 40,
    **params: Any,
) -> dict:
    """Inverse-generate a certified instance of the paper's equation (1.1)."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, prime_floor, min_gap_slot, gap_slots, power_max)

    start, gap = _sample_progression(seed, prime_floor, min_gap_slot, gap_slots)
    answer = [start + k * gap for k in range(4)]

    exponent_rng = random.Random(seed ^ 0xBB67AE8584CAA73B)
    exponents = [exponent_rng.randint(4, power_max) for _ in range(46)]
    exponent_rng.shuffle(exponents)
    power_total = sum(1 << exponent for exponent in exponents)

    placement_rng = random.Random(seed ^ 0x3C6EF372FE94F82B)
    span = 3 * gap
    # Scale one fixed random fraction of the spare width.  Thus increasing n at
    # fixed seed nests the old interval inside the new one instead of redrawing
    # an unrelated placement, which makes the difficulty axis genuinely
    # monotone while leaving the plant position statistically uniform.
    spare = n - span
    left_padding = placement_rng.getrandbits(64) * spare // (1 << 64)
    lower = start - left_padding
    if lower < 2:
        lower = 2
    upper = lower + n
    if answer[-1] > upper:
        lower = answer[-1] - n
        upper = answer[-1]

    prime_square_target = sum(p * p for p in answer)
    target = prime_square_target + power_total
    prime_pool = _primes_in_interval(lower, upper)
    if not all(p in prime_pool for p in answer):
        raise AssertionError("construction lost a planted prime")

    return {
        "n": n,
        "target": target,
        "prime_square_target": prime_square_target,
        "power_exponents": exponents,
        "power_total": power_total,
        "prime_lower": lower,
        "prime_upper": upper,
        "prime_count": len(prime_pool),
        "answer": answer,
        # Derived solely from the displayed interval; used by local measurements.
        "_prime_pool": prime_pool,
    }


def render(inst: dict) -> str:
    exponents = ", ".join(str(v) for v in inst["power_exponents"])
    text = f"""Four prime squares and 46 powers of two

An integer is prime if it is greater than 1 and its only positive divisors are
1 and itself.  Find exactly four pairwise distinct prime integers
p0 < p1 < p2 < p3, each in the inclusive interval
[{inst['prime_lower']}, {inst['prime_upper']}], such that

  p0^2 + p1^2 + p2^2 + p3^2 + sum(2^e for e in E) = N.

The fixed list E contains exactly 46 exponents; repeated exponents are allowed:
  E = [{exponents}]

Instance checksums (ordinary base-10 integers):
  sum(2^e for e in E) = {inst['power_total']}
  N = {inst['target']}
  required prime-square subtotal = N - sum(2^e for e in E)
                                 = {inst['prime_square_target']}

The order of E has no significance.  The four output primes must be written in
strictly increasing order; no repeats and no values outside the inclusive
interval are allowed.  Any quadruple satisfying all these conditions is valid.

Give your final answer inside <answer></answer> tags as four comma-separated
base-10 integers.
Example: <answer>101, 151, 197, 251</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def parse_answer(text: Any) -> object | None:
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    payloads = list(reversed(tagged))
    if not payloads:
        fenced = re.findall(r"```(?:json|text)?\s*(.*?)```", text,
                            flags=re.IGNORECASE | re.DOTALL)
        payloads.extend(reversed(fenced))
        payloads.append(text)
    for payload in payloads:
        cleaned = payload.strip()
        try:
            if cleaned.startswith("[") and cleaned.endswith("]"):
                value = json.loads(cleaned)
                if (isinstance(value, list) and len(value) == 4
                        and all(isinstance(v, int) and not isinstance(v, bool)
                                for v in value)):
                    return value
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
        if re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+){3}", cleaned):
            try:
                return [int(part.strip()) for part in cleaned.split(",")]
            except ValueError:
                pass
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid witness using only instance data and exact arithmetic."""
    if not isinstance(answer, list):
        return False, "answer must be a list of four integers"
    if len(answer) != 4:
        return False, f"expected exactly 4 primes, got {len(answer)}"
    if any(isinstance(v, bool) or not isinstance(v, int) for v in answer):
        return False, "all four entries must be base-10 integers"
    if len(set(answer)) != 4:
        return False, "the four primes must be pairwise distinct"
    if any(answer[i] >= answer[i + 1] for i in range(3)):
        return False, "the four primes must be in strictly increasing order"
    lower = int(inst["prime_lower"])
    upper = int(inst["prime_upper"])
    for index, value in enumerate(answer):
        if value < lower or value > upper:
            return False, f"entry {index} is outside the inclusive prime interval"
    for index, value in enumerate(answer):
        if not _is_prime(value):
            return False, f"entry {index} is not prime"
    exponents = inst.get("power_exponents")
    if not (isinstance(exponents, list) and len(exponents) == 46
            and all(isinstance(e, int) and not isinstance(e, bool) and e >= 0
                    for e in exponents)):
        return False, "instance has a malformed exponent list"
    power_total = sum(1 << e for e in exponents)
    if power_total != inst.get("power_total"):
        return False, "instance power checksum is inconsistent"
    prime_total = sum(value * value for value in answer)
    if prime_total + power_total != inst.get("target"):
        return False, "the four prime squares and 46 powers do not sum to N"
    return True, "ok"


def _necessary_prime_sum_bounds(inst: dict) -> tuple[int, int]:
    """Cheap sum bounds that a solver gets for free from the statement.

    Write every candidate as p_i = lower + x_i with 0 <= x_i <= n.  If
    S=sum(x_i), then the displayed square target satisfies

        target - 4*lower^2 = 2*lower*S + sum(x_i^2).

    Bounding the last term between 0 and 4*n^2 gives the interval below.
    At the shipping preset it is far narrower than the naive range of four
    interval primes, so ignoring it would substantially overstate guess
    resistance.
    """
    lower = int(inst["prime_lower"])
    width = int(inst["prime_upper"]) - lower
    residual = int(inst["prime_square_target"]) - 4 * lower * lower
    denominator = 2 * lower
    offset_low = -((-(residual - 4 * width * width)) // denominator)
    offset_high = residual // denominator
    offset_low = max(0, offset_low)
    offset_high = min(4 * width, offset_high)
    return 4 * lower + offset_low, 4 * lower + offset_high


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the structure-aware bounded certificate language.

    Choose a feasible total uniformly, choose three interval primes uniformly,
    and accept exactly when the complementary fourth value is another distinct
    interval prime.  Every legal quadruple has exactly four possible omitted
    entries, so conditioning on acceptance is uniform and does not favour the
    planted answer.
    """
    pool = inst.get("_prime_pool")
    if not isinstance(pool, list):
        pool = _primes_in_interval(inst["prime_lower"], inst["prime_upper"])
    total_low, total_high = _necessary_prime_sum_bounds(inst)
    while True:
        chosen = rng.sample(pool, 3)
        wanted = rng.randint(total_low, total_high) - sum(chosen)
        position = bisect.bisect_left(pool, wanted)
        if (position < len(pool) and pool[position] == wanted
                and wanted not in chosen):
            return sorted(chosen + [wanted])


def _count_sum_language(inst: dict) -> int:
    """Count increasing prime quadruples satisfying the free sum bounds.

    For a<b<c<d, maintain a Fenwick tree of pair sums p_a+p_b with b<c and
    query the complementary sum interval for p_c+p_d.  This counts every
    quadruple once in O(m^2 log n) time and O(n) memory.
    """
    pool = inst.get("_prime_pool")
    if not isinstance(pool, list):
        pool = _primes_in_interval(inst["prime_lower"], inst["prime_upper"])
    if len(pool) < 4:
        return 0
    lower = int(inst["prime_lower"])
    width = int(inst["prime_upper"]) - lower
    total_low, total_high = _necessary_prime_sum_bounds(inst)
    bit = [0] * (2 * width + 3)

    def update(offset: int) -> None:
        index = offset + 1
        while index < len(bit):
            bit[index] += 1
            index += index & -index

    def prefix(offset: int) -> int:
        if offset < 0:
            return 0
        index = min(offset + 1, len(bit) - 1)
        result = 0
        while index:
            result += bit[index]
            index -= index & -index
        return result

    count = 0
    pair_origin = 2 * lower
    for c in range(2, len(pool) - 1):
        b = c - 1
        for a in range(b):
            update(pool[a] + pool[b] - pair_origin)
        for d in range(c + 1, len(pool)):
            second = pool[c] + pool[d]
            wanted_low = total_low - second - pair_origin
            wanted_high = total_high - second - pair_origin
            count += prefix(wanted_high) - prefix(wanted_low - 1)
    return count


def search_space(inst: dict) -> int | None:
    cached = inst.get("_structure_aware_space")
    if isinstance(cached, int) and not isinstance(cached, bool):
        return cached
    count = _count_sum_language(inst)
    inst["_structure_aware_space"] = count
    return count


def _fast_valid(inst: dict, candidate: list[int]) -> bool:
    return sum(value * value for value in candidate) == inst["prime_square_target"]


def _pair_table_count(inst: dict) -> int:
    """Count exact increasing solutions; caller caps the candidate count."""
    primes = inst["_prime_pool"]
    target = inst["prime_square_target"]
    groups: dict[int, list[tuple[int, int]]] = {}
    for j in range(1, len(primes)):
        square_j = primes[j] * primes[j]
        for i in range(j):
            total = primes[i] * primes[i] + square_j
            groups.setdefault(total, []).append((i, j))
    partitions = 0
    for total, pairs in groups.items():
        complement = target - total
        other = groups.get(complement)
        if other is None or total > complement:
            continue
        if total < complement:
            for a, b in pairs:
                for c, d in other:
                    if len({a, b, c, d}) == 4:
                        partitions += 1
        else:
            for left in range(len(pairs)):
                a, b = pairs[left]
                for right in range(left + 1, len(pairs)):
                    c, d = pairs[right]
                    if len({a, b, c, d}) == 4:
                        partitions += 1
    if partitions % 3:
        raise AssertionError("four-sum partition count was not divisible by three")
    return partitions // 3


def enumerate_all(inst: dict) -> int | None:
    if int(inst.get("prime_count", 10**9)) > 2_100:
        return None
    return _pair_table_count(inst)


def canonical_key(inst: dict) -> str:
    normal_form = {
        "target": int(inst["target"]),
        "prime_interval": [int(inst["prime_lower"]), int(inst["prime_upper"])],
        "power_exponents": sorted(int(e) for e in inst["power_exponents"]),
    }
    blob = json.dumps(normal_form, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    current = {k: v for k, v in params.items() if k != "_preset"}
    n = int(current.get("n", 0))
    if n < 33_000:
        current["n"] = 33_000
        # Move the plant to the end of the still-sub-300-operation AP scan while
        # widening the interval slightly; the four-number answer stays fixed.
        current["min_gap_slot"] = 43
        current["gap_slots"] = 52
        return current
    # Larger intervals push the compact AP scan beyond the 300-operation cap.
    # Raising only the integer magnitude shrinks the prime pool and is not a
    # monotone hardness axis, so no honest further escalation is available.
    return None


def _nearest_distinct(primes: list[int], targets: list[int]) -> list[int]:
    chosen: list[int] = []
    for target in targets:
        index = bisect.bisect_left(primes, target)
        options = []
        for j in range(max(0, index - 3), min(len(primes), index + 4)):
            if primes[j] not in chosen:
                options.append(primes[j])
        if not options:
            options = [p for p in primes if p not in chosen]
        chosen.append(min(options, key=lambda p: (abs(p - target), p)))
    return sorted(chosen)


def _attack_candidates(inst: dict, restart_seed: int) -> dict[str, list[int] | None]:
    primes = inst["_prime_pool"]
    lower, upper = inst["prime_lower"], inst["prime_upper"]
    width = upper - lower
    attacks: dict[str, list[int] | None] = {}

    quartiles = [lower + width * k // 5 for k in range(1, 5)]
    attacks["outlier_interval_quartiles"] = _nearest_distinct(primes, quartiles)

    remaining = inst["prime_square_target"]
    available = list(primes)
    greedy: list[int] = []
    for slots_left in range(4, 0, -1):
        target = math.isqrt(max(0, remaining // slots_left))
        pick = _nearest_distinct(available, [target])[0]
        greedy.append(pick)
        available.remove(pick)
        remaining -= pick * pick
    attacks["greedy_equal_residual"] = sorted(greedy)

    center = math.isqrt(inst["prime_square_target"] // 4)
    center_index = bisect.bisect_left(primes, center)
    consecutive_hit = None
    for start in range(max(0, center_index - 40),
                       min(len(primes) - 3, center_index + 41)):
        candidate = primes[start:start + 4]
        if _fast_valid(inst, candidate):
            consecutive_hit = candidate
            break
    attacks["consecutive_prime_windows_80"] = consecutive_hit

    by_hand_hit = None
    target = inst["prime_square_target"]
    for slot in range(1, 9):
        gap = _WHEEL * slot
        radicand = target - 5 * gap * gap
        if radicand < 0:
            continue
        centered = math.isqrt(radicand)
        if centered * centered != radicand or (centered - 3 * gap) % 2:
            continue
        start = (centered - 3 * gap) // 2
        candidate = [start + k * gap for k in range(4)]
        if verify(inst, candidate)[0]:
            by_hand_hit = candidate
            break
    attacks["by_hand_ap_first_8_wheel_steps"] = by_hand_hit

    rng = random.Random(restart_seed)
    random_hit = None
    for _ in range(512):
        candidate = random_candidate(inst, rng)
        if _fast_valid(inst, candidate):
            random_hit = candidate
            break
    attacks["random_restart_512"] = random_hit
    return attacks


def _reference_four_sum(inst: dict) -> tuple[list[int] | None, dict[str, int]]:
    """Segmented-sieve + incremental pair hash, independent of the plant."""
    # Reconstruct the prime pool from exactly the data shown to the solver; do
    # not let the baseline benefit from make_instance's private measurement cache.
    primes = _primes_in_interval(inst["prime_lower"], inst["prime_upper"])
    count = len(primes)
    squares = [p * p for p in primes]
    target = inst["prime_square_target"]
    table: dict[int, int | list[int]] = {}
    sieve_candidates = inst["prime_upper"] - inst["prime_lower"] + 1
    operations = sieve_candidates + count
    pair_visits = 0
    for j in range(1, count):
        square_j = squares[j]
        for i in range(j):
            total = squares[i] + square_j
            complement = target - total
            pair_visits += 1
            operations += 3
            previous = table.get(complement)
            if previous is not None:
                codes = previous if isinstance(previous, list) else [previous]
                for code in codes:
                    a, b = divmod(code, count)
                    operations += 1
                    if len({a, b, i, j}) == 4:
                        answer = sorted((primes[a], primes[b], primes[i], primes[j]))
                        if verify(inst, answer)[0]:
                            return answer, {
                                "operations": operations,
                                "pair_visits": pair_visits,
                                "stored_pair_sums": len(table),
                                "sieve_candidates": sieve_candidates,
                            }
            code = i * count + j
            old = table.get(total)
            if old is None:
                table[total] = code
            elif isinstance(old, list):
                if len(old) < 4:
                    old.append(code)
            else:
                table[total] = [old, code]
            operations += 1
    return None, {
        "operations": operations,
        "pair_visits": pair_visits,
        "stored_pair_sums": len(table),
        "sieve_candidates": sieve_candidates,
    }


def _atom_count(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_atom_count(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atom_count(v) for v in value)
    return 1


def selftest() -> dict:
    """Run all local gates and return a fully JSON-native measured report."""
    report: dict[str, Any] = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    g1_failures: list[str] = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=314159, **ship_params)
    planted = list(ship["answer"])
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": [planted[1], planted[0], planted[2], planted[3]],
        "duplicate_one": [planted[0], planted[1], planted[2], planted[2]],
        "empty": [],
        "out_of_range": [ship["prime_lower"] - 1, planted[1], planted[2], planted[3]],
    }
    cases = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, why = verify(ship, candidate)
        cases[name] = {"rejected": not ok, "reason": why}
        reasons.append(why)
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in cases.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "cases": cases,
    }

    answer_text = ", ".join(str(v) for v in planted)
    model_style = (
        "The exact check succeeds.\n```text\n"
        f"<answer>{answer_text}</answer>\n```\n"
        "Those are the four requested primes."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("unrelated prose") is None,
        "parsed": parsed,
    }

    samples = 250_000
    sample_rng = random.Random(8675309)
    hits = 0
    for _ in range(samples):
        candidate = random_candidate(ship, sample_rng)
        if _fast_valid(ship, candidate):
            hits += 1
            if not verify(ship, candidate)[0]:
                raise AssertionError("fast density check disagrees with verify")
    density = hits / samples
    structured_space = search_space(ship)
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": density,
        "candidate_space": structured_space,
        "sampler": (
            "uniform increasing 4-subsets of actual interval primes, conditioned "
            "on the necessary prime-sum bounds implied by the square subtotal"
        ),
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    shipping_count = enumerate_all(ship)
    exact_shipping_fraction = (
        shipping_count / structured_space
        if shipping_count is not None and structured_space else None
    )

    attack_names = [
        "outlier_interval_quartiles",
        "greedy_equal_residual",
        "consecutive_prime_windows_80",
        "by_hand_ap_first_8_wheel_steps",
        "random_restart_512",
    ]
    attack_results = {
        name: {"successes": 0, "attempts": 8} for name in attack_names
    }
    reference_successes = 0
    reference_times: list[float] = []
    reference_operations: list[int] = []
    reference_pair_visits: list[int] = []
    reference_sieve_candidates: list[int] = []
    for seed in range(8):
        inst = make_instance(seed=12_000 + seed, **ship_params)
        for name, candidate in _attack_candidates(inst, 700_000 + seed).items():
            if candidate is not None and verify(inst, candidate)[0]:
                attack_results[name]["successes"] += 1
        started = time.perf_counter()
        reference_answer, counts = _reference_four_sum(inst)
        elapsed = time.perf_counter() - started
        reference_times.append(elapsed)
        reference_operations.append(counts["operations"])
        reference_pair_visits.append(counts["pair_visits"])
        reference_sieve_candidates.append(counts["sieve_candidates"])
        reference_successes += int(
            reference_answer is not None and verify(inst, reference_answer)[0]
        )

    reference = {
        "name": "segmented sieve plus meet-in-the-middle prime-square four-sum",
        "complexity": "O(n log log U + m^2) time and O(m^2) memory",
        "wall_clock_sec_mean": sum(reference_times) / len(reference_times),
        "wall_clock_sec_max": max(reference_times),
        "operations_mean": sum(reference_operations) / len(reference_operations),
        "operations_max": max(reference_operations),
        "pair_visits_mean": sum(reference_pair_visits) / len(reference_pair_visits),
        "pair_visits_max": max(reference_pair_visits),
        "sieve_candidates_mean": (
            sum(reference_sieve_candidates) / len(reference_sieve_candidates)
        ),
        "sieve_candidates_max": max(reference_sieve_candidates),
        "solves": f"{reference_successes}/8, as expected",
    }
    all_attacks_failed = all(
        result["successes"] == 0 and result["attempts"] >= 8
        for result in attack_results.values()
    )
    report["G5_density_and_baseline"] = {
        "pass": demo_count is not None and shipping_count is not None
        and exact_shipping_fraction is not None
        and exact_shipping_fraction < 1e-6
        and reference_successes == 8,
        "shipping_density_hits": hits,
        "shipping_density_total": samples,
        "shipping_observed_fraction": density,
        "shipping_valid_solution_count": shipping_count,
        "shipping_structure_aware_space": structured_space,
        "shipping_exact_solution_fraction": exact_shipping_fraction,
        "shipping_prime_count": ship["prime_count"],
        "demo_valid_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "baseline_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
        "baseline_wall_clock_sec_max": reference["wall_clock_sec_max"],
        "baseline_operations_mean": reference["operations_mean"],
        "baseline_operations_max": reference["operations_max"],
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": reference,
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] = 2 * int(doubled_params["n"])
    # Hold the random choices fixed so this tests the n-axis rather than two
    # unrelated draws.  make_instance nests the original interval at fixed seed.
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(ship),
        "shipping_n": ship["n"],
        "doubled_n": doubled["n"],
        "shipping_space": search_space(ship),
        "doubled_space": search_space(doubled),
        "doubled_verify_reason": doubled_reason,
        "answer_elements_shipping": _atom_count(ship["answer"]),
        "answer_elements_doubled": _atom_count(doubled["answer"]),
    }

    invariant_checks = 0
    real_transform_checks = 0
    composed_checks = 0
    unrelated_keys = []
    g8_failures = []
    for seed in range(20):
        inst = make_instance(seed=20_000 + seed, **DIFFICULTY["medium"])
        key = canonical_key(inst)
        unrelated_keys.append(key)
        once = dict(inst)
        once["power_exponents"] = list(inst["power_exponents"])
        random.Random(30_000 + seed).shuffle(once["power_exponents"])
        twice = dict(once)
        twice["power_exponents"] = list(reversed(once["power_exponents"]))
        if canonical_key(once) == key:
            invariant_checks += 1
        else:
            g8_failures.append(f"power reordering changed key at seed {seed}")
        if verify(once, inst["answer"])[0]:
            real_transform_checks += 1
        else:
            g8_failures.append(f"reordered instance rejected answer at seed {seed}")
        if canonical_key(twice) == key and verify(twice, inst["answer"])[0]:
            composed_checks += 1
        else:
            g8_failures.append(f"composed reordering failed at seed {seed}")
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "real_transformation_checks": real_transform_checks,
        "composed_transformation_checks": composed_checks,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "transformations": [
            "arbitrary reordering of the 46 fixed summands",
            "reversal composed with that reordering",
        ],
        "failures": g8_failures,
    }

    answer_blob = json.dumps(ship["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    arms = {
        name: {
            "solved": int(G9_MEASUREMENTS[name]["solved"]),
            "attempts": int(G9_MEASUREMENTS[name]["attempts"]),
        }
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else 0.0
    )
    intended_operations = 164
    within_caps = (
        answer_chars <= 2_000
        and _atom_count(ship["answer"]) <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        # The three oracle arms, including the formerly gated hinted arm, are
        # diagnostics as of 2026-09-05.  Only the answer/effort caps still gate.
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": _atom_count(ship["answer"]),
        "intended_route_operations": intended_operations,
    }

    gates = [key for key in report if key.startswith("G")]
    report["all_passed"] = all(bool(report[key].get("pass")) for key in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
