#!/usr/bin/env python3
"""Verified integer-triangle generator for arXiv:2512.15237.

The paper identifies triangles with a prescribed circumradius-to-exradius
ratio with suitable rational points on an elliptic curve.  This module uses
the reverse direction for generation: it samples the integer sides first and
then computes the ratio exactly.  It never searches for a triangle it built.

Importing this module performs no file I/O and prints nothing.
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
from fractions import Fraction


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:                 # pragma: no cover - stdlib fallback is complete
    exact_matrices = rationals = None


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "number_theory",
    "object_regime": "integer_lattice",
    "computational_core": "polynomial_identity",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "integer side-length triangle with one distinguished side",
        "reduced rational circumradius-to-exradius ratio",
        "paper's associated elliptic curve over Q",
    ],
    "verification_operations": [
        "integer range, parity, distinctness, and triangle-inequality checks",
        "exact integer products",
        "exact rational equality by cross multiplication",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "The semiperimeter substitution turns the radius identity into the "
        "paper's quartic and then its elliptic curve; without that change of "
        "variables, recovery is an unstructured three-variable Diophantine search."
    ),
    "hardness_basis": (
        "Track A: Theorems 2 and 3 identify recovery with finding a suitable "
        "non-torsion rational point on E_N; shipping uses generic ratios from "
        "three distinct random odd 256-bit sides, explicitly excluding the "
        "N=m^2+/-1 families solved by Theorem 4, and the measured bounded-height "
        "elliptic-point search and construction-aware attacks fail on 8/8 seeds."
    ),
    "max_answer_tokens": 60,
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
    "demo": {"n": 4, "lower_eighths": 4},
    "easy": {"n": 256, "lower_eighths": 7},
    "medium": {"n": 320, "lower_eighths": 6},
    "hard": {"n": 384, "lower_eighths": 4},
}
SHIPPING_DIFFICULTY = "easy"


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON array of exactly three pairwise-distinct odd integers.  The "
        "positions are the displayed f/g/h role order; every entry lies in the "
        "instance's inclusive interval [L,U].  The entries must form a strict "
        "triangle and have the displayed exact ratio."
    ),
    "bounds": {
        "array_length": 3,
        "entry_interval": "inclusive [inst['lower'], inst['upper']]",
        "parity": "odd",
        "distinct": True,
        "role_order": "inst['answer_order']",
    },
}


STRUCTURAL_HINT = (
    "The semiperimeter deficiencies place the ratio equation on the paper's "
    "quartic and hence on its birational elliptic curve."
)
PLACEBO_HINT = (
    "Keep the three displayed side roles and all inclusive integer bounds "
    "straight while checking the exact ratio."
)


# Replaced after the script-owned three-arm runs.  These values are diagnostics;
# only the size/effort caps gate G9.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


NOTES = r"""
Section 1, equations (2)--(3), fixes the exact native object and the identity
used by verify: for the excircle tangent to the distinguished side h,
R/r = 2fgh / ((f+g+h)(f-g-h)(g-h-f)).  Section 2 derives the quartic C_N and
its birational elliptic curve E_N.  Theorems 2 and 3 say that a rational
triangle exists exactly when E_N has an admissible rational non-torsion point.

The Step-0 easy-regime check is essential here.  Theorem 4 gives closed-form
triangles whenever N=m^2+1 or N=m^2-1; those ratios are rejected during
generation.  The torsion discussion in Section 3 shows that torsion points do
not produce triangles and lists rank-zero examples.  The paper does not prove
complexity-theoretic hardness.  TRACK A is therefore a distributional claim
for generic high-height inverse-generated ratios, supported by the measured
attacks, not an NP-hardness claim.

Generation samples three distinct odd n-bit side lengths from exactly the same
bounded language used by random_candidate, computes N by the displayed
identity, and keeps only ratios outside the paper's explicit square families.
The attack panel checks boundary/magnitude landmarks, exact coordinate descent,
structure-aware random restarts, small-factor grouping of the ratio numerator,
and the paper-induced bounded-height rational-point search on E_N.  The
generator obtains no witness from any of them.  Larger n and a wider interval
grow the candidate space while the certificate remains three integers.

Post-build rejection audit.  This prototype is retained because its local G1--G8
measurements are useful, but it must not ship.  The elliptic-curve substitution
does not itself recover the planted high-height point, so the intended route is
not the 18 operations needed to verify an already-known triangle.  Even the
bounded height-128 search performs 96,666 candidate-point trials across eight
shipping seeds without finding a witness.  That is already above the G9(c)
300-operation cap and supplies no compact post-insight route.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _normalise(n: int, lower_eighths: int) -> tuple[int, int, int]:
    if type(n) is not int or type(lower_eighths) is not int:
        raise TypeError("n and lower_eighths must be integers")
    if n < 4:
        raise ValueError("n must be at least 4")
    if not 4 <= lower_eighths <= 7:
        raise ValueError("lower_eighths must be between 4 and 7 inclusive")
    lower = lower_eighths * (1 << (n - 3))
    upper = (1 << n) - 1
    first = lower if lower & 1 else lower + 1
    if first + 4 > upper:
        raise ValueError("interval must contain at least three odd integers")
    return n, lower, upper


def _first_odd(lower: int) -> int:
    return lower if lower & 1 else lower + 1


def _odd_count(lower: int, upper: int) -> int:
    first = _first_odd(lower)
    if first > upper:
        return 0
    return (upper - first) // 2 + 1


def _draw_odd(rng: random.Random, lower: int, upper: int) -> int:
    first = _first_odd(lower)
    return first + 2 * rng.randrange(_odd_count(lower, upper))


def _ratio_for_sides(f: int, g: int, h: int) -> tuple[int, int]:
    numerator = 2 * f * g * h
    denominator = (f + g + h) * (f - g - h) * (g - h - f)
    if denominator <= 0:
        raise ValueError("not a strict positive-side triangle")
    common = math.gcd(numerator, denominator)
    return numerator // common, denominator // common


def _fraction_is_square(value: Fraction) -> bool:
    if value < 0:
        return False
    rn = math.isqrt(value.numerator)
    rd = math.isqrt(value.denominator)
    return rn * rn == value.numerator and rd * rd == value.denominator


def _explicit_or_extra_torsion_regime(p: int, q: int) -> bool:
    value = Fraction(p, q)
    # Theorem 4's two formula families, plus the extra-2-torsion case from
    # Proposition 1.  The latter is not known to solve recovery, but excluding
    # it keeps the shipping regime squarely generic.
    return (
        _fraction_is_square(value + 1)
        or _fraction_is_square(value - 1)
        or _fraction_is_square(value * (value + 2))
    )


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a certified ratio instance from sampled side lengths."""

    lower_eighths = params.pop("lower_eighths", 4)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    n, lower, upper = _normalise(n, int(lower_eighths))
    rng = random.Random(seed)

    for _ in range(10000):
        sides = []
        while len(sides) < 3:
            candidate = _draw_odd(rng, lower, upper)
            if candidate not in sides:
                sides.append(candidate)
        f, g, h = sides
        p, q = _ratio_for_sides(f, g, h)
        if _explicit_or_extra_torsion_regime(p, q):
            continue
        order = ["f", "g", "h"]
        if rng.randrange(2):
            order[0], order[1] = order[1], order[0]
        values = {"f": f, "g": g, "h": h}
        answer = [values[name] for name in order]
        return {
            "paper": "arXiv:2512.15237v1",
            "family": "bounded integer triangle from an exact R/r_h ratio",
            "n": n,
            "lower_eighths": lower_eighths,
            "lower": lower,
            "upper": upper,
            "ratio": [p, q],
            "answer_order": order,
            "seed": seed,
            "answer": answer,
        }
    raise RuntimeError("could not sample a generic ratio after 10000 attempts")


def render(inst: dict) -> str:
    """Render a self-contained exact Diophantine search problem."""

    p, q = inst["ratio"]
    order = ", ".join(inst["answer_order"])
    lines = [
        "INTEGER TRIANGLE WITH A PRESCRIBED CIRCUMRADIUS/EXRADIUS RATIO",
        "",
        "A strict integer triangle is three positive integer side lengths f,g,h",
        "satisfying f+g>h, f+h>g, and g+h>f.  The side h is distinguished:",
        "r_h denotes the radius of the excircle tangent to side h, while R denotes",
        "the circumcircle radius.  For such a triangle the exact identity is",
        "",
        "  R/r_h = 2*f*g*h / ((f+g+h)*(f-g-h)*(g-h-f)).",
        "",
        "Both negative factors in the denominator make this value positive.",
        "The roles f and g are interchangeable; the distinguished role h is not.",
        "All bounds below are inclusive.",
        "",
        f"Target reduced rational ratio N = {p}/{q}.",
        f"Every side must be an odd integer in [{inst['lower']}, {inst['upper']}].",
        "The three side lengths must be pairwise distinct.",
        "Find any strict integer triangle satisfying these conditions and R/r_h=N",
        "exactly.  Decimal approximations are not accepted.",
        "",
        f"Give the three integers in this position order: [{order}].",
        "Give your final answer inside <answer></answer> tags as one JSON array",
        "of exactly three decimal integers, with no labels inside the array.",
        "Example of the required syntax only: <answer>[9,11,13]</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Extract the tagged JSON triple, tolerating prose and Markdown fences."""

    try:
        if not isinstance(text, str):
            return None
        match = _ANSWER_RE.search(text)
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:json|text|txt)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
        value = json.loads(body)
        if not isinstance(value, list):
            return None
        if any(type(item) is not int for item in value):
            return None
        return value
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Check any valid bounded triangle without consulting the planted answer."""

    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) != 3:
        return False, "answer must contain exactly three sides"
    if any(type(value) is not int for value in answer):
        return False, "every side must be a decimal integer"
    lower, upper = inst["lower"], inst["upper"]
    if any(value < lower or value > upper for value in answer):
        return False, "a side lies outside the inclusive interval"
    if any(value % 2 == 0 for value in answer):
        return False, "every side must be odd"
    if len(set(answer)) != 3:
        return False, "the three side lengths must be pairwise distinct"

    by_role = dict(zip(inst["answer_order"], answer))
    f, g, h = by_role["f"], by_role["g"], by_role["h"]
    if not (f + g > h and f + h > g and g + h > f):
        return False, "the side lengths violate a strict triangle inequality"

    p, q = inst["ratio"]
    left = 2 * q * f * g * h
    right = p * (f + g + h) * (f - g - h) * (g - h - f)
    if left != right:
        return False, "the exact circumradius/exradius ratio is not the target"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the stated shape/parity/distinctness-aware language."""

    chosen = []
    while len(chosen) < 3:
        value = _draw_odd(rng, inst["lower"], inst["upper"])
        if value not in chosen:
            chosen.append(value)
    return chosen


def search_space(inst: dict) -> int:
    """Exact size of the ordered distinct-odd-triple certificate language."""

    count = _odd_count(inst["lower"], inst["upper"])
    return count * (count - 1) * (count - 2)


def enumerate_all(inst: dict) -> int | None:
    """Count exact witnesses when the declared language is at most 100,000."""

    if search_space(inst) > 100000:
        return None
    values = range(_first_odd(inst["lower"]), inst["upper"] + 1, 2)
    total = 0
    for candidate in itertools.permutations(values, 3):
        if verify(inst, list(candidate))[0]:
            total += 1
    return total


def canonical_key(inst: dict) -> str:
    """Key on the reduced ratio and bounds, ignoring seed and f/g presentation."""

    p, q = inst["ratio"]
    common = math.gcd(p, q)
    structural = {
        "ratio": [p // common, q // common],
        "lower": inst["lower"],
        "upper": inst["upper"],
        "parity": "odd",
        "distinct": True,
        "distinguished_role": "h",
    }
    payload = json.dumps(structural, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Raise coefficient entropy and widen the interval at fixed three atoms."""

    n = int(params.get("n", 96))
    lower_eighths = int(params.get("lower_eighths", 7))
    new_n = n + 32
    new_lower = max(4, lower_eighths - 1)
    # Compact JSON has three maximal decimal integers, two commas and brackets.
    worst_chars = 3 * len(str((1 << new_n) - 1)) + 4
    if worst_chars > 2000:
        return "cap_bound"
    return {"n": new_n, "lower_eighths": new_lower}


# ---------------------------------------------------------------------------
# Construction-aware and domain-standard attacks used by the mandatory gates.


def _ordered_candidate(inst: dict, f: int, g: int, h: int) -> list[int]:
    values = {"f": f, "g": g, "h": h}
    return [values[name] for name in inst["answer_order"]]


def _landmarks(inst: dict) -> list[int]:
    lower, upper = inst["lower"], inst["upper"]
    raw = [
        lower,
        lower + (upper - lower) // 4,
        (lower + upper) // 2,
        upper - (upper - lower) // 4,
        upper,
    ]
    out = []
    for value in raw:
        value = max(lower, min(upper, value))
        if value % 2 == 0:
            value = value + 1 if value < upper else value - 1
        if value not in out:
            out.append(value)
    return out


def _attack_outlier_landmarks(inst: dict):
    """Try all boundary/quartile/midpoint magnitude outliers."""

    nodes = 0
    for values in itertools.permutations(_landmarks(inst), 3):
        nodes += 1
        candidate = _ordered_candidate(inst, *values)
        if verify(inst, candidate)[0]:
            return candidate, nodes
    return None, nodes


def _cross_residual(inst: dict, canonical: list[int]) -> int:
    f, g, h = canonical
    p, q = inst["ratio"]
    return abs(
        2 * q * f * g * h
        - p * (f + g + h) * (f - g - h) * (g - h - f)
    )


def _clamp_odd(value: int, lower: int, upper: int) -> int:
    value = max(lower, min(upper, value))
    if value % 2 == 0:
        if value < upper:
            value += 1
        else:
            value -= 1
    return value


def _attack_greedy_coordinate(inst: dict, restarts: int = 12):
    """Exact residual descent from deterministic random and central starts."""

    p, q = inst["ratio"]
    rng = random.Random((p ^ (q << 1) ^ 0xC001D00D) & ((1 << 256) - 1))
    lower, upper = inst["lower"], inst["upper"]
    nodes = 0
    for restart in range(restarts):
        if restart == 0:
            current = _landmarks(inst)[1:4]
        else:
            current = []
            while len(current) < 3:
                value = _draw_odd(rng, lower, upper)
                if value not in current:
                    current.append(value)
        current = list(current)
        best = _cross_residual(inst, current)
        step = max(2, ((upper - lower) // 4) // 2 * 2)
        while step >= 2:
            improved = False
            for index in range(3):
                for direction in (-1, 1):
                    trial = list(current)
                    trial[index] = _clamp_odd(
                        trial[index] + direction * step, lower, upper
                    )
                    if len(set(trial)) != 3:
                        continue
                    nodes += 1
                    score = _cross_residual(inst, trial)
                    if score < best:
                        current, best = trial, score
                        improved = True
                        candidate = _ordered_candidate(inst, *current)
                        if verify(inst, candidate)[0]:
                            return candidate, nodes
            if not improved:
                step //= 2
                if step % 2:
                    step -= 1
        candidate = _ordered_candidate(inst, *current)
        if verify(inst, candidate)[0]:
            return candidate, nodes
    return None, nodes


def _small_primes(limit: int) -> list[int]:
    sieve = bytearray(b"\x01") * (limit + 1)
    sieve[:2] = b"\x00\x00"
    for value in range(2, math.isqrt(limit) + 1):
        if sieve[value]:
            sieve[value * value:limit + 1:value] = b"\x00" * (
                (limit - value * value) // value + 1
            )
    return [value for value in range(2, limit + 1) if sieve[value]]


def _attack_factor_partition(inst: dict, shuffle_attempts: int = 128):
    """Strip small factors from N's numerator and greedily group side-sized chunks."""

    residue = inst["ratio"][0]
    factors = []
    divisions = 0
    for prime in _small_primes(10000):
        while residue % prime == 0:
            factors.append(prime)
            residue //= prime
            divisions += 1
        divisions += 1
    if residue > 1:
        factors.append(residue)
    p, q = inst["ratio"]
    rng = random.Random(p ^ q ^ 0xFAC70)
    nodes = 0
    variants = [sorted(factors, reverse=True)]
    for _ in range(shuffle_attempts):
        variant = list(factors)
        rng.shuffle(variant)
        variants.append(variant)
    for variant in variants:
        bins = [1, 1, 1]
        for factor in variant:
            index = min(range(3), key=lambda i: bins[i])
            bins[index] *= factor
        for triple in itertools.permutations(bins):
            nodes += 1
            candidate = _ordered_candidate(inst, *triple)
            if verify(inst, candidate)[0]:
                return candidate, nodes, divisions
    return None, nodes, divisions


def _attack_random_restart(inst: dict, restarts: int = 2048):
    p, q = inst["ratio"]
    rng = random.Random(p ^ (q << 1) ^ 0x51A7E)
    for node in range(1, restarts + 1):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate, node
    return None, restarts


def _sqrt_fraction(value: Fraction) -> Fraction | None:
    if value < 0:
        return None
    a = math.isqrt(value.numerator)
    b = math.isqrt(value.denominator)
    if a * a == value.numerator and b * b == value.denominator:
        return Fraction(a, b)
    return None


def _ceil_fraction(value: Fraction) -> int:
    return -((-value.numerator) // value.denominator)


def _point_to_candidate(inst: dict, u: Fraction, v: Fraction):
    """Apply equations (5)--(6) and Theorem 2 to an elliptic-curve point."""

    N = Fraction(*inst["ratio"])
    denominator = (u - 1) * (u + 4 * N - 1)
    if denominator == 0:
        return None
    x = -4 * N * (v + 2 * N * u) / denominator
    if not 0 < x < 1:
        return None
    y_den = (u - 1) ** 2 * (4 * N + u - 1) ** 2
    y = -4 * N * (4 * N + u * u - 1) * (
        8 * N * N * u + 4 * N * u + 4 * N * v - 4 * N
        + u * u - 2 * u + 1
    ) / y_den
    root_b = abs(y)
    a1 = -x * x - 2 * (2 * N - 1) * x + 4 * N
    a2 = -x * x + 2 * (2 * N + 1) * x - 4 * N
    sides = [
        (a1 - root_b) / (2 * x),
        x,
        (a2 + root_b) / (2 * x),
    ]
    if any(value <= 0 for value in sides):
        return None
    scale = math.lcm(*(value.denominator for value in sides))
    integers = [int(value * scale) for value in sides]
    common = math.gcd(math.gcd(integers[0], integers[1]), integers[2])
    integers = [value // common for value in integers]
    if any(value % 2 == 0 for value in integers):
        return None
    lower, upper = inst["lower"], inst["upper"]
    k_low = max(_ceil_fraction(Fraction(lower, value)) for value in integers)
    k_high = min(upper // value for value in integers)
    if k_low % 2 == 0:
        k_low += 1
    if k_low > k_high:
        return None
    f, g, h = [value * k_low for value in integers]
    candidate = _ordered_candidate(inst, f, g, h)
    return candidate if verify(inst, candidate)[0] else None


def _attack_elliptic_height(inst: dict, height: int = 128):
    """Standard small-projective-height search on the paper's E_N."""

    N = Fraction(*inst["ratio"])
    nodes = 0
    for denominator in range(1, height + 1):
        for numerator in range(-height, height + 1):
            if math.gcd(abs(numerator), denominator) != 1:
                continue
            u = Fraction(numerator, denominator)
            if not (1 - 4 * N < u < 0 or u > 1):
                continue
            nodes += 1
            rhs = (
                u ** 3
                + 2 * (2 * N * N + 2 * N - 1) * u * u
                - (4 * N - 1) * u
            )
            root = _sqrt_fraction(rhs)
            if root is None:
                continue
            for v in (root, -root):
                candidate = _point_to_candidate(inst, u, v)
                if candidate is not None:
                    return candidate, nodes
    return None, nodes


def _presentation_swap(inst: dict) -> dict:
    changed = dict(inst)
    old_order = list(inst["answer_order"])
    new_order = list(old_order)
    new_order[0], new_order[1] = new_order[1], new_order[0]
    values = dict(zip(old_order, inst["answer"]))
    changed["answer_order"] = new_order
    changed["answer"] = [values[name] for name in new_order]
    return changed


def _mathematical_fg_swap(inst: dict) -> dict:
    changed = dict(inst)
    values = dict(zip(inst["answer_order"], inst["answer"]))
    values["f"], values["g"] = values["g"], values["f"]
    changed["answer"] = [values[name] for name in inst["answer_order"]]
    return changed


def _answer_atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest() -> dict:
    """Run mandatory gates and return their measurements as JSON-native data."""

    report = {}

    # G1: every preset, multiple independent seeds, plus JSON-native answers.
    g1_failures = []
    checked = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            checked += 1
            ok, why = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append(f"{preset}/seed={seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/seed={seed}: answer not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "instances_checked": checked,
        "failures": g1_failures,
    }

    ship_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    shipping = make_instance(seed=4242, **ship_params)
    answer = list(shipping["answer"])

    # G2: five corruption classes with five distinct diagnostics.
    corruptions = {
        "drop_one": answer[:-1],
        "empty": [],
        "duplicate": [answer[0], answer[0], answer[2]],
        "out_of_range": [shipping["lower"] - 1, answer[1], answer[2]],
    }
    by_role = dict(zip(shipping["answer_order"], answer))
    by_role["f"], by_role["h"] = by_role["h"], by_role["f"]
    corruptions["swap_distinguished"] = [
        by_role[name] for name in shipping["answer_order"]
    ]
    reasons = {}
    for name, candidate in corruptions.items():
        ok, why = verify(shipping, candidate)
        reasons[name] = {"rejected": not ok, "reason": why}
    distinct_reasons = len({item["reason"] for item in reasons.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in reasons.values())
        and distinct_reasons == len(reasons),
        "cases": reasons,
        "distinct_reasons": distinct_reasons,
    }

    # G3: tagged answer with prose and a fenced payload.
    realistic = (
        "I used the exact radius identity and checked all three inequalities.\n"
        "<answer>\n```json\n" + json.dumps(answer) + "\n```\n</answer>\n"
        "The array follows the requested displayed role order."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(shipping, parsed)[0],
        "parsed_equals_planted": parsed == answer,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    # G4/G5 shipping-preset structure-aware density measurement.
    guesses = 200000
    guess_rng = random.Random(0x251215237)
    hits = 0
    started = time.perf_counter()
    for _ in range(guesses):
        hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_seconds = time.perf_counter() - started
    report["G4_guess_resistance"] = {
        "pass": hits / guesses < 1e-6,
        "hits": hits,
        "total": guesses,
        "observed_probability": hits / guesses,
        "sampler": "uniform ordered distinct odd triples in the stated interval",
        "candidate_space": search_space(shipping),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    # G6 attacks, all executed on the shipping preset across eight seeds.
    attack_names = [
        "outlier_boundary_landmarks",
        "greedy_exact_residual_descent",
        "random_restart_2048",
        "small_factor_partition",
        "elliptic_rational_height_128",
    ]
    attack_data = {
        name: {"successes": 0, "attempts": 8, "nodes": 0, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    attack_instances = [
        make_instance(seed=9000 + seed, **ship_params) for seed in range(8)
    ]
    for inst in attack_instances:
        begun = time.perf_counter()
        found, nodes = _attack_outlier_landmarks(inst)
        attack_data[attack_names[0]]["wall_clock_sec"] += time.perf_counter() - begun
        attack_data[attack_names[0]]["nodes"] += nodes
        attack_data[attack_names[0]]["successes"] += int(found is not None)

        begun = time.perf_counter()
        found, nodes = _attack_greedy_coordinate(inst)
        attack_data[attack_names[1]]["wall_clock_sec"] += time.perf_counter() - begun
        attack_data[attack_names[1]]["nodes"] += nodes
        attack_data[attack_names[1]]["successes"] += int(found is not None)

        begun = time.perf_counter()
        found, nodes = _attack_random_restart(inst)
        attack_data[attack_names[2]]["wall_clock_sec"] += time.perf_counter() - begun
        attack_data[attack_names[2]]["nodes"] += nodes
        attack_data[attack_names[2]]["successes"] += int(found is not None)

        begun = time.perf_counter()
        found, nodes, divisions = _attack_factor_partition(inst)
        attack_data[attack_names[3]]["wall_clock_sec"] += time.perf_counter() - begun
        attack_data[attack_names[3]]["nodes"] += nodes
        attack_data[attack_names[3]]["trial_divisions"] = (
            attack_data[attack_names[3]].get("trial_divisions", 0) + divisions
        )
        attack_data[attack_names[3]]["successes"] += int(found is not None)

        begun = time.perf_counter()
        found, nodes = _attack_elliptic_height(inst)
        attack_data[attack_names[4]]["wall_clock_sec"] += time.perf_counter() - begun
        attack_data[attack_names[4]]["nodes"] += nodes
        attack_data[attack_names[4]]["successes"] += int(found is not None)

    for data in attack_data.values():
        data["wall_clock_sec"] = round(data["wall_clock_sec"], 6)
    all_failed = all(data["successes"] == 0 for data in attack_data.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and len(attack_data) >= 4,
        "attacks": attack_data,
        "domain_standard_attack": "elliptic_rational_height_128",
        "note": (
            "The domain attack enumerates reduced rational u-coordinates of "
            "projective height at most 128 on the paper's E_N and applies its "
            "birational reconstruction exactly."
        ),
    }

    demo = make_instance(seed=13, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    baseline = attack_data["elliptic_rational_height_128"]
    report["G5_density_and_baseline"] = {
        "pass": isinstance(demo_count, int) and guesses >= 200000
        and baseline["nodes"] > 0,
        "shipping_density_hits": hits,
        "shipping_density_samples": guesses,
        "shipping_observed_fraction": hits / guesses,
        "shipping_candidate_space": search_space(shipping),
        "demo_n": demo["n"],
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "strongest_attack": "elliptic_rational_height_128",
        "baseline_total_nodes_8_seeds": baseline["nodes"],
        "baseline_wall_clock_sec_8_seeds": baseline["wall_clock_sec"],
        "baseline_successes_8_seeds": baseline["successes"],
    }

    # G7: named spaces strictly increase; doubling n still builds and verifies.
    named_spaces = [
        search_space(make_instance(seed=77, **params))
        for params in DIFFICULTY.values()
    ]
    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled_started = time.perf_counter()
    doubled = make_instance(seed=88, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    doubled_seconds = time.perf_counter() - doubled_started
    report["G7_scales"] = {
        "pass": doubled_ok and all(
            left < right for left, right in zip(named_spaces, named_spaces[1:])
        ),
        "named_candidate_spaces": named_spaces,
        "shipping_n": ship_params["n"],
        "doubled_n": doubled_params["n"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "doubled_build_and_verify_sec": round(doubled_seconds, 6),
        "answer_atomic_elements_fixed": 3,
    }

    # G8: f/g mathematical symmetry, presentation relabelling, and composition.
    invariance_checks = 0
    carried_checks = 0
    g8_failures = []
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(seed=20000 + seed, **ship_params)
        key = canonical_key(inst)
        unrelated_keys.append(key)
        transformed = [
            _presentation_swap(inst),
            _mathematical_fg_swap(inst),
            _presentation_swap(_mathematical_fg_swap(inst)),
        ]
        for changed in transformed:
            invariance_checks += 1
            if canonical_key(changed) != key:
                g8_failures.append(f"seed {seed}: canonical key changed")
            carried_checks += 1
            ok, why = verify(changed, changed["answer"])
            if not ok:
                g8_failures.append(f"seed {seed}: carried witness failed: {why}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "real_transformation_verify_checks": carried_checks,
        "distinct_unrelated_keys": distinct_keys,
        "unrelated_instances": 20,
        "symmetries": [
            "swap the symmetric mathematical roles f and g",
            "swap their displayed output positions",
            "compose both swaps",
        ],
        "key_kind": "reduced target ratio plus bounded certificate language",
        "failures": g8_failures,
    }

    # G9 diagnostics and the only active gate: exact output/operation caps.
    measured_answers = [inst["answer"] for inst in attack_instances] + [answer]
    blobs = [json.dumps(value, separators=(",", ":")) for value in measured_answers]
    answer_chars = max(map(len, blobs))
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = max(_answer_atoms(value) for value in measured_answers)
    # A previous draft incorrectly counted only witness verification here.  The
    # intended route after the elliptic-curve insight still has to find a rational
    # point.  The tested height-128 route already visits this many points without
    # succeeding, so this is a conservative lower bound, not a claimed solution.
    _, intended_operations = _attack_elliptic_height(shipping)
    arms = {name: dict(G9_EVIDENCE[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "rejection_reason": (
            "the elliptic-curve insight leaves an unbounded rational-point search; "
            "the measured operation count is only a failed-search lower bound"
        ),
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = ship_params
    report["certificate_language"] = CERTIFICATE_LANGUAGE
    report["problem_profile"] = PROBLEM_PROFILE
    report["all_passed"] = all(
        value.get("pass", False) for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
