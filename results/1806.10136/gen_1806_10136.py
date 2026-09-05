"""Verified problem generator for arXiv:1806.10136.

The paper studies representations by

    floor(x^2/a) + floor(y^2/b) + floor(z^2/c).

This module stays in those native integer objects.  It inverse-generates a
representation by composing the paper's square-factor identity (1.2) with an
integer orthogonal image of the classical Pythagorean triple.  Verification is
only exact integer squaring, floor division, range checks, and equality.

Generation never searches for a representation of an already-built target.
The target and its certificate are assembled together from exact identities.
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


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - the implementation is stdlib-only
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE = {
    "native_domain": "number_theory",
    "object_regime": "integer_lattice",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "ternary floor-quadratic form",
        "positive integer denominators with a common squarefree core",
        "interval-bounded nonnegative integer representation",
    ],
    "verification_operations": [
        "exact integer comparison",
        "exact integer squaring",
        "Euclidean floor division",
        "exact integer addition and equality",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "A common-squarefree change of variables turns the three coordinates "
        "into an integer orthogonal image of a Pythagorean triple; without it "
        "one must scan floor-square pair sums."
    ),
    "hardness_basis": (
        "Track B: equation (1.2) permits an O(U^2), O(1)-space monotone "
        "pair-sum search after square-factor normalization; across eight "
        "shipping medium instances it used 8,362,194 counted exact operations "
        "(under one second total in repeated runs on this host, maximum "
        "2,413,021 for one instance), while the "
        "compact orthogonal-identity route used at most 112 operations."
    ),
    "max_answer_tokens": 7,
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

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list [x1,x2,x3] of exactly three pairwise-distinct, "
        "nonnegative integers.  Coordinate xi lies in the displayed inclusive "
        "interval [Li,Bi] and is tied to denominator ai in the same position."
    ),
    "bounds": {
        "length": 3,
        "entry_type": "integer",
        "minimum": "the corresponding displayed inclusive lower bound Li",
        "maximum": "the corresponding displayed inclusive bound Bi",
        "pairwise_distinct": True,
        "maximum_atomic_elements": 3,
    },
}

DIFFICULTY = {
    "demo": {"n": 2, "core_bits": 3},
    "easy": {"n": 28, "core_bits": 6},
    "medium": {"n": 40, "core_bits": 7},
    "hard": {"n": 56, "core_bits": 8},
}

SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "The common-squarefree substitution hides an integer orthogonal image of "
    "a Pythagorean triple among the three coordinates."
)
PLACEBO_HINT = (
    "The coordinate order and inclusive upper bounds deserve careful attention "
    "when checking the three terms."
)

# Filled from three independent script-owned harden.py runs after the shipping
# rung is known.  These fields are diagnostic; only the size/effort caps gate G9.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "too_easy",
}

NOTES = r"""
Section 1 fixes the exact object: F_{a,b,c}(x,y,z) is the sum of the
three displayed floors, with x,y,z integral.  Equation (1.2) is the key exact
transformation: if a=s(a)t^2, then floor((tx)^2/a)=floor(x^2/s(a)).
Section 2 rewrites the same representation as one by a shifted lattice coset.
Theorem 1.1 proves F_m almost universal for every m>=3; Corollary 1.1 carries
this through square factors when the three denominators have the same
squarefree part.  The proof uses Eisenstein/local-density lower bounds and
Duke's cusp-form estimate, so its phrase "sufficiently large" is non-effective
here: it proves existence but is not an executable witness-producing algorithm.

That observation rules out an honest Track-A claim for this constructed
distribution.  Track B is explicit.  The mechanical reference first takes the
common core m=gcd(a,b,c), uses (1.2) to search the embedded variables, tabulates
floor(u^2/m), and runs a monotone two-pointer two-sum scan for every first
coordinate.  Its O(U^2) comparisons are measured at the shipping preset.  The
compact route instead recognizes a scaled integer orthogonal transform of
(t^2-1,2t,t^2+1); its squared norm is 18(t^2+1)^2.  A common small residue
supplies the linear correction in the target.

Generation chooses one of three small square-factor patterns, randomly orders
it, and randomly assigns the three identity components to the displayed
positions.  The small factors avoid the dense large-denominator regime noted
in Section 1, while the random order removes a fixed positional marker.  The
displayed coordinate intervals force every term to contribute between about
1/30 and 9/10 of the target, excluding the trivial one-term easy regime.
The attack panel tests the largest-denominator outlier, a residual-filling
greedy rule, uniform structure-aware restarts, and the tempting but wrong
zero-residue orthogonal ansatz.  The successful two-pointer reference search is
reported separately, as Track B requires.
""".strip()


_SCALE_PATTERNS = ((1, 1, 1), (1, 1, 2), (1, 2, 3))
_MR_BASES_64 = (2, 325, 9375, 28178, 450775, 9780504, 1795265022)
_SMALL_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)


def _is_prime(value: int) -> bool:
    if isinstance(value, bool) or not isinstance(value, int) or value < 2:
        return False
    for prime in _SMALL_PRIMES:
        if value % prime == 0:
            return value == prime
    odd = value - 1
    twos = 0
    while odd % 2 == 0:
        odd //= 2
        twos += 1
    bases = _MR_BASES_64 if value < (1 << 64) else _SMALL_PRIMES
    for base in bases:
        if base % value == 0:
            continue
        witness = pow(base, odd, value)
        if witness in (1, value - 1):
            continue
        for _ in range(twos - 1):
            witness = witness * witness % value
            if witness == value - 1:
                break
        else:
            return False
    return True


def _sample_prime(bits: int, rng: random.Random) -> int:
    if bits < 3:
        raise ValueError("core_bits must be at least 3")
    low = 1 << (bits - 1)
    high = 1 << bits
    for _ in range(10_000):
        candidate = rng.randrange(low, high) | 1
        if _is_prime(candidate):
            return candidate
    for candidate in range(low | 1, high, 2):
        if _is_prime(candidate):
            return candidate
    raise RuntimeError("prime interval unexpectedly empty")


def _identity_components(t: int) -> tuple[int, int, int]:
    """Signed rows of a 3-times-orthogonal image of a Pythagorean triple."""
    return (
        -(t * t + 4 * t + 3),
        -(4 * t * t - 2 * t),
        -(t * t + 4 * t - 3),
    )


def _closed_target(m: int, t: int, residue: int) -> int:
    # If s ranges over _identity_components(t), then
    #   sum(s^2) = 18(t^2+1)^2,  sum(s) = -6t(t+1).
    # residue^2 < m on every generated instance.
    return 18 * m * (t * t + 1) ** 2 - 12 * residue * t * (t + 1)


def _ceil_sqrt(value: int) -> int:
    root = math.isqrt(value)
    return root + (root * root < value)


def _coordinate_interval(denominator: int, target: int) -> tuple[int, int]:
    # Keep all three summands material.  The planted transformed identity has
    # asymptotic contribution ratios 1/18, 16/18, 1/18.
    low_term = target // 30
    high_term = 9 * target // 10
    lower = _ceil_sqrt(denominator * low_term)
    upper = math.isqrt(denominator * (high_term + 1) - 1)
    return lower, upper


def make_instance(n: int, seed: int = 0, core_bits: int = 6, **params) -> dict:
    """Inverse-generate one exact floor-quadratic representation."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    if isinstance(core_bits, bool) or not isinstance(core_bits, int) or core_bits < 3:
        raise ValueError("core_bits must be an integer at least 3")

    rng = random.Random(seed)
    if n == 2 and core_bits == 3:
        # A stable hand-scale illustration; the seed still changes the harmless
        # term order and component assignment.
        m = 5
        t = 2
        residue = 1
    else:
        m = _sample_prime(core_bits, rng)
        t = n + rng.randrange(2 * n)
        residue = rng.randrange(1, math.isqrt(m - 1) + 1)
        residue *= rng.choice((-1, 1))

    scales = list(rng.choice(_SCALE_PATTERNS))
    rng.shuffle(scales)
    denominators = [m * scale * scale for scale in scales]
    signed = _identity_components(t)
    base_coordinates = [abs(m * value + residue) for value in signed]

    valid_assignments = []
    for perm in itertools.permutations(base_coordinates):
        candidate = [scale * value for scale, value in zip(scales, perm)]
        if len(set(candidate)) == 3:
            valid_assignments.append(candidate)
    if not valid_assignments:
        raise RuntimeError("identity assignment did not produce distinct coordinates")
    answer = list(rng.choice(valid_assignments))

    target = _closed_target(m, t, residue)
    assembled = sum(
        coordinate * coordinate // denominator
        for coordinate, denominator in zip(answer, denominators)
    )
    if assembled != target:
        raise AssertionError("internal identity assembly failed")

    intervals = [_coordinate_interval(denominator, target) for denominator in denominators]
    lower_bounds = [interval[0] for interval in intervals]
    bounds = [interval[1] for interval in intervals]
    if not all(lower <= value <= upper for lower, value, upper in
               zip(lower_bounds, answer, bounds)):
        raise AssertionError("planted coordinate escaped its contribution interval")
    return {
        "n": n,
        "core_bits": core_bits,
        "denominators": denominators,
        "target": target,
        "lower_bounds": lower_bounds,
        "bounds": bounds,
        "answer": answer,
    }


def render(inst: dict) -> str:
    denominators = inst["denominators"]
    lower_bounds = inst["lower_bounds"]
    bounds = inst["bounds"]
    lines = [
        "Find a bounded representation by a ternary floor-quadratic form.",
        "",
        "For a real number q, floor(q) is the greatest integer not exceeding q.",
        "Find three pairwise-distinct nonnegative integers x1, x2, x3 such that",
        "",
        f"  floor(x1^2/{denominators[0]}) + floor(x2^2/{denominators[1]}) "
        f"+ floor(x3^2/{denominators[2]}) = {inst['target']}.",
        "",
        "The coordinates are indexed from 1 and tied to the denominators in the",
        "displayed order; coordinate order therefore matters.  Repeats are forbidden.",
        "All bounds are inclusive:",
        f"  {lower_bounds[0]} <= x1 <= {bounds[0]}",
        f"  {lower_bounds[1]} <= x2 <= {bounds[1]}",
        f"  {lower_bounds[2]} <= x3 <= {bounds[2]}",
        "Only exact integer arithmetic is intended; decimal approximations are not accepted.",
        "",
        "Give your final answer inside <answer></answer> tags, as a JSON list",
        "[x1,x2,x3] containing exactly three base-10 integers.",
        "Example: <answer>[12,34,56]</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(("", "Hint: " + STRUCTURAL_HINT))
    elif mode == "placebo":
        lines.extend(("", "Hint: " + PLACEBO_HINT))
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer>\s*(.*?)\s*</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        answer = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(answer, list):
        return None
    return answer


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) != 3:
        return False, "answer must contain exactly three coordinates"
    if any(isinstance(value, bool) or not isinstance(value, int) for value in answer):
        return False, "every coordinate must be an integer"
    if len(set(answer)) != 3:
        return False, "the three coordinates must be pairwise distinct"
    if any(value < lower or value > upper for value, lower, upper in
           zip(answer, inst["lower_bounds"], inst["bounds"])):
        return False, "a coordinate lies outside its inclusive bound"
    value = sum(
        coordinate * coordinate // denominator
        for coordinate, denominator in zip(answer, inst["denominators"])
    )
    if value != inst["target"]:
        return False, "the exact floor sum does not equal the target"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniform over all shape-, bound-, and distinctness-valid triples."""
    lower_bounds = inst["lower_bounds"]
    bounds = inst["bounds"]
    while True:
        candidate = [rng.randrange(lower, upper + 1)
                     for lower, upper in zip(lower_bounds, bounds)]
        if len(set(candidate)) == 3:
            return candidate


def search_space(inst: dict) -> int | None:
    lowers = inst["lower_bounds"]
    uppers = inst["bounds"]
    sizes = [upper - lower + 1 for lower, upper in zip(lowers, uppers)]
    total = math.prod(sizes)
    pair_equal = 0
    for i, j, k in ((0, 1, 2), (0, 2, 1), (1, 2, 0)):
        overlap = max(0, min(uppers[i], uppers[j]) - max(lowers[i], lowers[j]) + 1)
        pair_equal += overlap * sizes[k]
    all_equal = max(0, min(uppers) - max(lowers) + 1)
    return total - pair_equal + 2 * all_equal


def enumerate_all(inst: dict) -> int | None:
    """Count all valid witnesses exactly when a two-coordinate scan is small."""
    lowers = inst["lower_bounds"]
    bounds = inst["bounds"]
    order = sorted(range(3), key=lambda index: bounds[index] - lowers[index])
    i, j, k = order
    work = (bounds[i] - lowers[i] + 1) * (bounds[j] - lowers[j] + 1)
    if work > 2_000_000:
        return None
    target = inst["target"]
    denominators = inst["denominators"]
    third_counts: dict[int, list[int]] = {}
    for z in range(lowers[k], bounds[k] + 1):
        value = z * z // denominators[k]
        third_counts.setdefault(value, []).append(z)
    count = 0
    for x in range(lowers[i], bounds[i] + 1):
        vx = x * x // denominators[i]
        for y in range(lowers[j], bounds[j] + 1):
            if x == y:
                continue
            need = target - vx - y * y // denominators[j]
            for z in third_counts.get(need, ()):
                if z != x and z != y:
                    count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Canonical under every permutation of the three summands."""
    payload = {
        "terms": sorted(zip(inst["denominators"], inst["lower_bounds"], inst["bounds"])),
        "target": inst["target"],
        "pairwise_distinct": True,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow numeric crowding first, then the normalized pair-sum haystack."""
    harder = {key: value for key, value in params.items() if key != "_preset"}
    bits = int(harder.get("core_bits", 6))
    n = int(harder.get("n", 28))
    if bits < 14:
        harder["core_bits"] = bits + 1
        return harder
    next_n = (3 * n + 1) // 2
    # m < 2^bits, t < 3n, every identity component is below a small
    # constant times t^2, and the largest square multiplier is 3.  Convert a
    # conservative bit bound to decimal digits using log10(2) < 30103/100000.
    coordinate_bits = bits + 2 * (3 * next_n).bit_length() + 6
    coordinate_digits = (coordinate_bits * 30103 + 99_999) // 100_000
    serialized_upper = 3 * coordinate_digits + 4  # brackets and two commas
    if serialized_upper > 2_000:
        return "cap_bound"
    harder["n"] = next_n
    harder["core_bits"] = bits
    return harder


def _gcd_with_operations(values: list[int]) -> tuple[int, int]:
    result = 0
    operations = 0
    for value in values:
        a, b = result, value
        while b:
            a, b = b, a % b
            operations += 1
        result = abs(a)
    return result, operations


def _normalization(inst: dict) -> tuple[int, list[int], int] | None:
    m, operations = _gcd_with_operations(inst["denominators"])
    scales = []
    for denominator in inst["denominators"]:
        if denominator % m:
            return None
        quotient = denominator // m
        scale = math.isqrt(quotient)
        operations += 3
        if scale * scale != quotient:
            return None
        scales.append(scale)
    return m, scales, operations


def _compact_solve(inst: dict) -> tuple[list[int] | None, int]:
    normalized = _normalization(inst)
    if normalized is None:
        return None, 0
    m, scales, operations = normalized
    target = inst["target"]
    coarse = max(1, target // (18 * m))
    approx_t = math.isqrt(math.isqrt(coarse))
    operations += 5
    recovered = None
    for t in range(max(2, approx_t - 5), approx_t + 7):
        leading = 18 * m * (t * t + 1) ** 2
        divisor = 12 * t * (t + 1)
        difference = leading - target
        operations += 11
        if difference != 0 and difference % divisor == 0:
            residue = difference // divisor
            operations += 3
            if residue != 0 and residue * residue < m \
                    and _closed_target(m, t, residue) == target:
                recovered = (t, residue)
            break
    if recovered is None:
        return None, operations
    t, residue = recovered
    base = [abs(m * value + residue) for value in _identity_components(t)]
    operations += 18
    for perm in itertools.permutations(base):
        answer = [scale * value for scale, value in zip(scales, perm)]
        operations += 6
        if verify(inst, answer)[0]:
            return answer, operations
    return None, operations


def _reference_solve(inst: dict) -> tuple[list[int] | None, int, int]:
    """Equation-(1.2) normalization plus monotone floor-square 3SUM."""
    normalized = _normalization(inst)
    if normalized is None:
        return None, 0, 0
    m, scales, operations = normalized
    target = inst["target"]
    low_term = target // 30
    high_term = 9 * target // 10
    lower = _ceil_sqrt(m * low_term)
    upper = math.isqrt(m * (high_term + 1) - 1)
    operations += 8
    comparisons = 0
    for first in range(lower, upper + 1):
        left = first
        right = upper
        remaining = target - first * first // m
        operations += 3
        while left <= right:
            current = left * left // m + right * right // m
            comparisons += 1
            operations += 5
            if current == remaining:
                base = (first, left, right)
                for perm in set(itertools.permutations(base)):
                    answer = [scale * value for scale, value in zip(scales, perm)]
                    operations += 6
                    if verify(inst, answer)[0]:
                        return answer, operations, comparisons
                left += 1
            elif current < remaining:
                left += 1
            else:
                right -= 1
    return None, operations, comparisons


def _nearest_coordinate(
    denominator: int, desired_term: int, lower: int, upper: int
) -> int:
    guess = min(upper, max(lower, math.isqrt(max(0, denominator * desired_term))))
    choices = range(max(lower, guess - 2), min(upper, guess + 2) + 1)
    return min(
        choices,
        key=lambda value: (abs(value * value // denominator - desired_term), value),
    )


def _attack_largest_denominator(inst: dict) -> list[int]:
    index = max(range(3), key=lambda i: inst["denominators"][i])
    answer = list(inst["lower_bounds"])
    answer[index] = _nearest_coordinate(
        inst["denominators"][index],
        inst["target"],
        inst["lower_bounds"][index],
        inst["bounds"][index],
    )
    for position in range(3):
        while answer.count(answer[position]) > 1 and answer[position] < inst["bounds"][position]:
            answer[position] += 1
    return answer


def _attack_greedy(inst: dict) -> list[int]:
    answer: list[int | None] = [None, None, None]
    remaining = inst["target"]
    order = sorted(range(3), key=lambda i: -inst["denominators"][i])
    minimum_terms = [
        lower * lower // denominator
        for lower, denominator in zip(inst["lower_bounds"], inst["denominators"])
    ]
    maximum_terms = [
        upper * upper // denominator
        for upper, denominator in zip(inst["bounds"], inst["denominators"])
    ]
    for rank, index in enumerate(order):
        reserve = sum(minimum_terms[later] for later in order[rank + 1:])
        desired = max(minimum_terms[index], min(maximum_terms[index], remaining - reserve))
        value = _nearest_coordinate(
            inst["denominators"][index],
            desired,
            inst["lower_bounds"][index],
            inst["bounds"][index],
        )
        while value in answer and value > inst["lower_bounds"][index]:
            value -= 1
        answer[index] = value
        remaining -= value * value // inst["denominators"][index]
    if len(set(answer)) < 3:
        for index in range(3):
            while answer.count(answer[index]) > 1 and answer[index] < inst["bounds"][index]:
                answer[index] += 1
    return [int(value) for value in answer]


def _attack_zero_residue_identity(inst: dict) -> list[int] | None:
    normalized = _normalization(inst)
    if normalized is None:
        return None
    m, scales, _ = normalized
    coarse = max(1, inst["target"] // (18 * m))
    t = max(2, math.isqrt(math.isqrt(coarse)))
    base = [m * abs(value) for value in _identity_components(t)]
    for perm in itertools.permutations(base):
        answer = [scale * value for scale, value in zip(scales, perm)]
        if len(set(answer)) == 3 and all(
            lower <= value <= upper
            for value, lower, upper in
            zip(answer, inst["lower_bounds"], inst["bounds"])
        ):
            return answer
    return None


def _permute_instance(inst: dict, permutation: tuple[int, int, int]) -> dict:
    changed = dict(inst)
    for key in ("denominators", "lower_bounds", "bounds", "answer"):
        changed[key] = [inst[key][index] for index in permutation]
    return changed


def _answer_atoms(answer: object) -> int:
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    return 1


def _find_equation_corruption(inst: dict, answer: list[int]) -> list[int]:
    for index, value in enumerate(answer):
        digits = list(str(value))
        for i in range(len(digits)):
            for j in range(i + 1, len(digits)):
                if digits[i] == digits[j] or (i == 0 and digits[j] == "0"):
                    continue
                changed_digits = list(digits)
                changed_digits[i], changed_digits[j] = changed_digits[j], changed_digits[i]
                changed = list(answer)
                changed[index] = int("".join(changed_digits))
                ok, reason = verify(inst, changed)
                if not ok and reason == "the exact floor sum does not equal the target":
                    return changed
    for index, value in enumerate(answer):
        for delta in (-1, 1):
            changed = list(answer)
            changed[index] = value + delta
            ok, reason = verify(inst, changed)
            if not ok and reason == "the exact floor sum does not equal the target":
                return changed
    raise AssertionError("could not build an equation-only corruption")


def selftest() -> dict:
    report: dict = {}

    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            try:
                round_trip = json.loads(json.dumps(inst["answer"]))
            except TypeError as exc:
                failures.append({"preset": preset, "seed": seed, "reason": str(exc)})
            else:
                if round_trip != inst["answer"]:
                    failures.append({"preset": preset, "seed": seed,
                                     "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "failures": failures,
        "construction": (
            "inverse generation from equation (1.2) and an exact integer "
            "orthogonal image of a Pythagorean triple"
        ),
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=271828, **shipping_params)
    answer = inst["answer"]
    duplicate = list(answer)
    duplicate[1] = duplicate[0]
    out_of_range = list(answer)
    out_of_range[2] = inst["bounds"][2] + 1
    corruptions = {
        "drop_one": answer[:-1],
        "swap_two_digits": _find_equation_corruption(inst, answer),
        "duplicate": duplicate,
        "empty": None,
        "out_of_range": out_of_range,
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [item["reason"] for item in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "corruptions": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The common core gives the transformed identity.\n```text\n"
        + "<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nThe exact floors check."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer,
        "parsed_equals_answer": parsed == answer,
        "surrounding_prose_and_markdown": True,
    }

    trials = 200_000
    guess_rng = random.Random(0x180610136)
    hits = 0
    guess_started = time.perf_counter()
    for _ in range(trials):
        hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - guess_started
    guess_rate = hits / trials
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": hits,
        "total": trials,
        "observed_probability": guess_rate,
        "candidate_space": search_space(inst),
        "prior": (
            "uniform over triples already satisfying the displayed integer, "
            "bound, and pairwise-distinct constraints"
        ),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count_started = time.perf_counter()
    demo_count = enumerate_all(demo)
    demo_count_seconds = time.perf_counter() - demo_count_started

    restart_started = time.perf_counter()
    restart_rng = random.Random(424242)
    restart_iterations = 256
    restart_success = False
    for _ in range(restart_iterations):
        if verify(inst, random_candidate(inst, restart_rng))[0]:
            restart_success = True
            break
    restart_seconds = time.perf_counter() - restart_started

    reference_started = time.perf_counter()
    reference_answer, reference_operations, reference_comparisons = _reference_solve(inst)
    reference_seconds = time.perf_counter() - reference_started
    reference_ok = reference_answer is not None and verify(inst, reference_answer)[0]
    report["G5_density_and_baseline_cost"] = {
        "pass": demo_count is not None and reference_ok and not restart_success,
        "shipping_seed": 271828,
        "shipping_density_hits": hits,
        "shipping_density_samples": trials,
        "shipping_sampled_solution_fraction": guess_rate,
        "shipping_exact_solution_count": None,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "demo_count_wall_clock_sec": round(demo_count_seconds, 6),
        "strongest_failing_attack": "256 structure-aware uniform restarts",
        "baseline_iterations": restart_iterations,
        "baseline_success": restart_success,
        "baseline_wall_clock_sec": round(restart_seconds, 6),
        "reference_pair_comparisons": reference_comparisons,
        "reference_operation_count": reference_operations,
        "reference_wall_clock_sec": round(reference_seconds, 6),
    }

    attack_names = (
        "largest_denominator_outlier",
        "greedy_residual_largest_first",
        "uniform_random_restart_256",
        "in_context_zero_residue_orthogonal_ansatz",
    )
    attacks = {
        name: {"successes": 0, "attempts": 8, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    reference_successes = 0
    reference_operations_all = []
    reference_comparisons_all = []
    reference_times = []
    compact_successes = 0
    compact_operations = []
    compact_times = []
    for seed in range(10_000, 10_008):
        current = make_instance(seed=seed, **shipping_params)
        candidate_attacks = {
            "largest_denominator_outlier": _attack_largest_denominator(current),
            "greedy_residual_largest_first": _attack_greedy(current),
            "in_context_zero_residue_orthogonal_ansatz": (
                _attack_zero_residue_identity(current)
            ),
        }

        rr_started = time.perf_counter()
        rr_rng = random.Random(seed ^ 0xBAD5EED)
        rr_answer = None
        for _ in range(256):
            trial = random_candidate(current, rr_rng)
            if verify(current, trial)[0]:
                rr_answer = trial
                break
        attacks["uniform_random_restart_256"]["wall_clock_sec"] += (
            time.perf_counter() - rr_started
        )
        candidate_attacks["uniform_random_restart_256"] = rr_answer

        for name, candidate in candidate_attacks.items():
            started = time.perf_counter()
            solved = candidate is not None and verify(current, candidate)[0]
            attacks[name]["successes"] += int(solved)
            if name != "uniform_random_restart_256":
                attacks[name]["wall_clock_sec"] += time.perf_counter() - started

        started = time.perf_counter()
        ref_answer, ref_ops, ref_comparisons = _reference_solve(current)
        reference_times.append(time.perf_counter() - started)
        reference_operations_all.append(ref_ops)
        reference_comparisons_all.append(ref_comparisons)
        reference_successes += int(
            ref_answer is not None and verify(current, ref_answer)[0]
        )

        started = time.perf_counter()
        compact_answer, compact_ops = _compact_solve(current)
        compact_times.append(time.perf_counter() - started)
        compact_operations.append(compact_ops)
        compact_successes += int(
            compact_answer is not None and verify(current, compact_answer)[0]
        )

    for result in attacks.values():
        result["wall_clock_sec"] = round(result["wall_clock_sec"], 6)
    all_attacks_failed = all(result["successes"] == 0 for result in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "square-factor normalization plus monotone two-pointer 3SUM",
            "paper_basis": "equation (1.2) and Corollary 1.1",
            "complexity": (
                "O(U^2) exact pair comparisons and O(1) auxiliary memory, where "
                "U=floor(sqrt(m(N+1)-1))"
            ),
            "wall_clock_sec": round(sum(reference_times), 6),
            "operations": sum(reference_operations_all),
            "operation_unit": "exact integer arithmetic/comparison steps across eight instances",
            "pair_comparisons": sum(reference_comparisons_all),
            "per_instance_operations": reference_operations_all,
            "per_instance_pair_comparisons": reference_comparisons_all,
            "solves": f"{reference_successes}/8, as expected",
        },
        "intended_compact_route": {
            "name": "common-core extraction and orthogonal Pythagorean identity",
            "wall_clock_sec": round(sum(compact_times), 6),
            "operations": compact_operations,
            "operations_max": max(compact_operations),
            "solves": f"{compact_successes}/8",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and doubled["target"] > inst["target"]
        and search_space(doubled) > search_space(inst),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "shipping_target": inst["target"],
        "doubled_target": doubled["target"],
        "shipping_candidate_space": search_space(inst),
        "doubled_candidate_space": search_space(doubled),
        "doubled_verify_reason": doubled_reason,
    }

    key_failures = []
    invariance_checks = 0
    real_transform_checks = 0
    unrelated_keys = []
    transformations = ((1, 0, 2), (1, 2, 0), (2, 0, 1))
    for seed in range(20):
        original = make_instance(seed=50_000 + seed, **shipping_params)
        key = canonical_key(original)
        unrelated_keys.append(key)
        for index, permutation in enumerate(transformations):
            changed = _permute_instance(original, permutation)
            invariance_checks += 1
            if canonical_key(changed) != key:
                key_failures.append({"seed": seed, "variant": index,
                                     "reason": "key changed under term permutation"})
            real_transform_checks += 1
            if not verify(changed, changed["answer"])[0]:
                key_failures.append({"seed": seed, "variant": index,
                                     "reason": "carried answer failed"})
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "real_transformation_checks": real_transform_checks,
        "distinct_unrelated_keys": distinct_keys,
        "unrelated_attempts": 20,
        "transformations": [
            "swap the first two summands",
            "cycle the last two summands",
            "composition giving a three-cycle",
        ],
        "failures": key_failures,
        "caveat": "canonical only for summand permutations, the full evident instance symmetry",
    }

    encoded = json.dumps(answer, separators=(",", ":"))
    answer_chars = len(encoded)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(answer)
    arms = {name: dict(G9_EVIDENCE[name]) for name in ("bare", "hinted", "placebo")}
    hinted_minus_placebo = None
    if all(arms[name]["attempts"] for name in arms):
        hinted_minus_placebo = (
            arms["hinted"]["solved"] / arms["hinted"]["attempts"]
            - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        )
    representative_compact, representative_ops = _compact_solve(inst)
    intended_operations = max(compact_operations + [representative_ops])
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "within_caps": within_caps,
        "representative_compact_solution_verified": (
            representative_compact is not None
            and verify(inst, representative_compact)[0]
        ),
    }

    measured_max_tokens = 0
    measured_max_chars = 0
    for seed in range(64):
        current = make_instance(seed=70_000 + seed, **shipping_params)
        blob = json.dumps(current["answer"], separators=(",", ":"))
        measured_max_chars = max(measured_max_chars, len(blob))
        measured_max_tokens = max(measured_max_tokens, math.ceil(len(blob) / 4))
    report["profile_measurements"] = {
        "shipping_answer_chars_max_over_64_seeds": measured_max_chars,
        "shipping_answer_tokens_max_over_64_seeds": measured_max_tokens,
        "declared_max_answer_tokens": PROBLEM_PROFILE["max_answer_tokens"],
    }
    if measured_max_tokens > PROBLEM_PROFILE["max_answer_tokens"]:
        report["G9_no_tool_suitability"]["pass"] = False
        report["G9_no_tool_suitability"]["profile_bound_failure"] = True

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
