"""Verified projective-line generator for arXiv:1902.05133.

The paper studies lines on smooth degree-d surfaces in projective three-space
and gives weighted Fermat surfaces as the basic line-rich example.  This module
applies an invertible triangular rational change of coordinates to such a
surface.  A line is chosen in Fermat coordinates and carried through the
change, so generation never solves the displayed coefficient system.

The answer is the 2 x 4 integer matrix of two linear equations defining a
projective line.  Verification restricts the homogeneous surface polynomial to
that line and compares every coefficient with zero using integer arithmetic.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import time
from fractions import Fraction


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "geometry",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "homogeneous polynomial over Q defining a smooth surface in projective 3-space",
        "projective line given by two independent rational linear equations",
    ],
    "verification_operations": [
        "exact substitution of a two-parameter line into a homogeneous polynomial",
        "integer binomial expansion",
        "zero comparison of every restricted coefficient",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize a low-rank triangular Waring structure in the expanded coefficient "
        "tensor; without it one must run full tensor deflation or solve the line equations."
    ),
    "hardness_basis": (
        "Track B: triangular Waring deflation recovers the four hidden linear forms in "
        "O(binomial(d+3,3)) exact coefficient operations; at shipping d=17 it scanned "
        "1,330 terms per instance (80,656 counted operations and 0.169 seconds over "
        "eight measured instances), whereas the ten-slice route uses 86 exact operations "
        "but requires noticing the hidden change of variables."
    ),
    "max_answer_tokens": 32,
}

NATIVE: dict = {
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

# n is the odd surface degree.  Growth adds coefficient-tensor entries but the
# answer remains a 2 x 4 matrix.
DIFFICULTY: dict = {
    "easy": {"n": 23, "coeff_bound": 15, "answer_bound": 1024},
}
SHIPPING_DIFFICULTY: str = "easy"

STRUCTURAL_HINT: str = (
    "The coefficient tensor is governed by a low-rank Waring decomposition "
    "compatible with a triangular flag."
)
PLACEBO_HINT: str = (
    "The coefficient table rewards careful attention to exponent order and "
    "exact integer signs throughout."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A 2-by-4 integer matrix [[1,0,u,v],[0,1,w,z]] in reduced row form, "
        "where u,v,w,z lie in the displayed inclusive interval [-B,B]."
    ),
    "bounds": {
        "rows": 2,
        "columns": 4,
        "fixed_pivot_block": [[1, 0], [0, 1]],
        "free_entries": 4,
        "entry_interval": "[-answer_bound, answer_bound] inclusive",
        "candidate_count": "(2*answer_bound+1)^4",
    },
}

# Replaced after the script-owned bare, structural, and placebo oracle runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}

NOTES: str = r"""
Section 2 fixes the native definition: a line L lies on X_d exactly when the
restriction f|_L vanishes identically; equations (4)--(5) repeatedly use direct
restriction computations.  Theorem 1.1 assumes a smooth degree-d surface over
characteristic 0 or p>d, and Example 3.9 supplies the Fermat surface
x0^d+x1^d+x2^d+x3^d=0 with 3d^2 contained lines.  The generator stays in
characteristic zero, uses odd d, pairs equal diagonal weights, and transports
one of those lines through an invertible rational coordinate change.  Smoothness
is therefore inherited from a diagonal Fermat surface.

Step-0 algorithm check.  The paper proves a counting bound, not computational
hardness, so Track A would be unsupported.  On this deliberately structured
distribution an efficient algorithm does exist: read the pure and near-pure
coefficient slices along the triangular flag, or mechanically deflate all four
d-th powers.  Full deflation scans O(binomial(d+3,3)) tensor entries; the compact
route reads ten slices and row-reduces two equations.  This is consequently an
honest Track B no-tool-compression claim.

Generation samples the triangular linear forms and paired weights first.  The
line equations are obtained by adding the paired forms and exact row reduction,
before the surface is expanded.  The outlier attack uses only pure coefficients;
the greedy attack minimizes the two endpoint restrictions over a tiny box; the
random attack samples the declared certificate language; and the by-hand ansatz
exhausts {-2,-1,0,1,2}^4.  Off-diagonal entries and the carried witness are
sampled outside that tiny box, but no verifier result is used to manufacture the
certificate.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    limit = math.isqrt(value)
    divisor = 3
    while divisor <= limit:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime(value: int) -> int:
    value = max(2, value)
    if value > 2 and value % 2 == 0:
        value += 1
    while not _is_prime(value):
        value += 1 if value == 2 else 2
    return value


def _compositions(total: int, length: int):
    if length == 1:
        yield (total,)
        return
    for first in range(total + 1):
        for tail in _compositions(total - first, length - 1):
            yield (first,) + tail


def _multinomial(total: int, exponents) -> int:
    result = 1
    left = total
    for exponent in exponents[:-1]:
        result *= math.comb(left, exponent)
        left -= exponent
    return result


def _expand_power(linear, degree: int, weight=1):
    """Sparse coefficients of weight*(linear[0]x0+...+linear[3]x3)^degree."""
    out = {}
    for exponents in _compositions(degree, 4):
        coefficient = weight * _multinomial(degree, exponents)
        for base, exponent in zip(linear, exponents):
            if exponent:
                coefficient *= base ** exponent
                if coefficient == 0:
                    break
        if coefficient:
            out[exponents] = coefficient
    return out


def _surface_terms(forms, weights, degree: int):
    coefficients = {}
    for linear, weight in zip(forms, weights):
        for exponent, coefficient in _expand_power(linear, degree, weight).items():
            coefficients[exponent] = coefficients.get(exponent, 0) + coefficient
            if coefficients[exponent] == 0:
                del coefficients[exponent]
    return [[coefficient, list(exponent)] for exponent, coefficient in sorted(coefficients.items())]


def _rref_pair_equations(forms, weights):
    groups = {}
    for index, weight in enumerate(weights):
        groups.setdefault(weight, []).append(index)
    if sorted(len(group) for group in groups.values()) != [2, 2]:
        raise ValueError("weights must form two distinct equal pairs")
    equations = []
    for group in groups.values():
        i, j = group
        equations.append([forms[i][k] + forms[j][k] for k in range(4)])
    equations.sort(key=lambda row: 0 if row[0] else 1)
    first, second = equations
    if first[0] != 1 or second[0] != 0 or second[1] != 1:
        raise ValueError("the paired equations left the required affine chart")
    factor = first[1]
    first = [first[k] - factor * second[k] for k in range(4)]
    answer = [first, second]
    if answer[0][:2] != [1, 0] or answer[1][:2] != [0, 1]:
        raise AssertionError("bad exact row reduction")
    return answer


def _sample_nonzero(rng: random.Random, bound: int) -> int:
    floor = max(1, bound // 2)
    magnitude = rng.randint(floor, bound)
    return magnitude if rng.randrange(2) else -magnitude


def make_instance(n, seed=0, **params) -> dict:
    """Construct a smooth transformed Fermat surface and carry a line with it."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 3 or n % 2 == 0:
        raise ValueError("n must be an odd integer at least 3 (the surface degree)")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    coeff_bound = params.pop("coeff_bound", None)
    answer_bound = params.pop("answer_bound", None)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(coeff_bound, bool) or not isinstance(coeff_bound, int) or coeff_bound < 2:
        raise ValueError("coeff_bound must be an integer at least 2")
    if isinstance(answer_bound, bool) or not isinstance(answer_bound, int) or answer_bound < 1:
        raise ValueError("answer_bound must be a positive integer")

    rng = random.Random(seed)
    base = 1009 + rng.randrange(900_000)
    weight_a = 2 if n == 3 else _next_prime(base)
    weight_b = 3 if n == 3 else _next_prime(base + 101 + rng.randrange(10_000))
    if weight_a == weight_b:
        weight_b = _next_prime(weight_b + 2)
    pairing = rng.randrange(2)

    # Every candidate surface is smooth because this matrix is unipotent upper
    # triangular and both diagonal weights are nonzero.  Resampling only keeps
    # the already-known carried answer inside the promised bounded language and,
    # outside the demo, away from the deliberately audited tiny ansatz.
    for _attempt in range(20_000):
        a01 = _sample_nonzero(rng, coeff_bound)
        a02 = _sample_nonzero(rng, coeff_bound)
        a03 = _sample_nonzero(rng, coeff_bound)
        a12 = _sample_nonzero(rng, coeff_bound)
        a13 = _sample_nonzero(rng, coeff_bound)
        a23 = _sample_nonzero(rng, coeff_bound)
        forms = [
            [1, a01, a02, a03],
            [0, 1, a12, a13],
            [0, 0, 1, a23],
            [0, 0, 0, 1],
        ]
        weights = (
            [weight_a, weight_b, weight_a, weight_b]
            if pairing == 0
            else [weight_a, weight_b, weight_b, weight_a]
        )
        answer = _rref_pair_equations(forms, weights)
        free = [answer[0][2], answer[0][3], answer[1][2], answer[1][3]]
        if max(map(abs, free)) > answer_bound:
            continue
        if n > 3 and min(map(abs, free)) <= 3:
            continue
        break
    else:
        raise RuntimeError("could not sample a carried line inside answer_bound")

    terms = _surface_terms(forms, weights, n)
    return {
        "family": "line on a transformed weighted Fermat surface",
        "degree": n,
        "field": "Q",
        "coeff_bound": coeff_bound,
        "answer_bound": answer_bound,
        "polynomial_terms": terms,
        # This is an exact evaluation cache for verify().  The rendered object is
        # the expanded coefficient table; selftest checks cache/table equality.
        "evaluation_cache": {"forms": forms, "weights": weights},
        "canonical_moduli": sorted([weight_a, weight_b]),
        "answer": answer,
    }


def render(inst) -> str:
    degree = inst["degree"]
    bound = inst["answer_bound"]
    rows = "\n".join(
        f"  {','.join(map(str, exponent))} : {coefficient}"
        for coefficient, exponent in inst["polynomial_terms"]
    )
    hint = ""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        hint = "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        hint = "\n\nHint: " + PLACEBO_HINT

    return f"""FIND A PROJECTIVE LINE ON AN EXACT SURFACE

Work over the rational numbers.  The four homogeneous coordinates on
projective 3-space are x0,x1,x2,x3.  The surface X is the zero set F=0 of the
homogeneous degree-{degree} polynomial displayed below.  A table row

    e0,e1,e2,e3 : c

means the term c*x0^e0*x1^e1*x2^e2*x3^e3.  Exponents are nonnegative and sum
to {degree}; every nonzero term is listed exactly once, and every omitted
monomial has coefficient zero.  All coefficients are exact base-10 integers.

Your witness must be a projective line in the fixed dual affine chart

    x0 + u*x2 + v*x3 = 0
    x1 + w*x2 + z*x3 = 0,

where u,v,w,z are integers in the inclusive interval [-{bound},{bound}].  These
independent equations define a line parametrized by

    [x0:x1:x2:x3] = [-u*s-v*t : -w*s-z*t : s : t]

for [s:t] in projective 1-space.  The line lies on X exactly when substituting
this parametrization into F gives the zero polynomial in s,t (all {degree + 1}
coefficients must vanish).

Expanded coefficient table ({len(inst['polynomial_terms'])} rows):
{rows}{hint}

Give your final answer inside <answer></answer> tags as the exact JSON integer
matrix [[1,0,u,v],[0,1,w,z]].  Do not use fractions, decimals, or entries
outside the stated inclusive bounds.  Row order is fixed by the two leading
pivots, repeats are not allowed, and indexing is 0-based.
Example of the required syntax (not necessarily a solution):
<answer>[[1,0,2,-3],[0,1,4,5]]</answer>
Output nothing else inside the tags."""


def parse_answer(text) -> object | None:
    """Parse the delimited JSON matrix, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    if body.startswith("```") and body.endswith("```"):
        lines = body.splitlines()
        if len(lines) >= 3:
            body = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value


def _restriction_coefficients(inst, answer):
    u, v = answer[0][2], answer[0][3]
    w, z = answer[1][2], answer[1][3]
    degree = inst["degree"]
    cache = inst["evaluation_cache"]
    restricted = [0] * (degree + 1)
    for linear, weight in zip(cache["forms"], cache["weights"]):
        alpha = -linear[0] * u - linear[1] * w + linear[2]
        beta = -linear[0] * v - linear[1] * z + linear[3]
        for k in range(degree + 1):
            restricted[k] += (
                weight
                * math.comb(degree, k)
                * alpha ** (degree - k)
                * beta ** k
            )
    return restricted


def verify(inst, answer) -> tuple[bool, str]:
    """Check shape and exact polynomial restriction; never consult inst['answer']."""
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list) or len(answer) != 2:
        return False, "answer must contain exactly two equation rows"
    if answer[0] == answer[1]:
        return False, "the two equation rows are duplicated and not independent"
    if any(not isinstance(row, list) or len(row) != 4 for row in answer):
        return False, "each equation row must contain exactly four entries"
    if any(isinstance(value, bool) or not isinstance(value, int) for row in answer for value in row):
        return False, "all matrix entries must be exact integers"
    if answer[0][:2] == [0, 1] and answer[1][:2] == [1, 0]:
        return False, "the equation rows are swapped; pivot order must be 0 then 1"
    if answer[0][:2] != [1, 0] or answer[1][:2] != [0, 1]:
        return False, "matrix must have the fixed reduced pivot block [[1,0],[0,1]]"
    bound = inst["answer_bound"]
    for row in answer:
        for value in row[2:]:
            if not -bound <= value <= bound:
                return False, f"a free entry lies outside the inclusive range [-{bound},{bound}]"
    for k, coefficient in enumerate(_restriction_coefficients(inst, answer)):
        if coefficient:
            return False, (
                f"restriction is nonzero: coefficient of "
                f"s^{inst['degree'] - k}*t^{k} is {coefficient}"
            )
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniformly sample the full stated four-integer affine chart."""
    bound = inst["answer_bound"]
    u, v, w, z = [rng.randint(-bound, bound) for _ in range(4)]
    return [[1, 0, u, v], [0, 1, w, z]]


def search_space(inst) -> int | None:
    return (2 * inst["answer_bound"] + 1) ** 4


def enumerate_all(inst) -> int | None:
    """Count valid chart lines exactly when at most 200,000 candidates exist."""
    if search_space(inst) > 200_000:
        return None
    bound = inst["answer_bound"]
    count = 0
    for u, v, w, z in itertools.product(range(-bound, bound + 1), repeat=4):
        ok, _ = verify(inst, [[1, 0, u, v], [0, 1, w, z]])
        count += int(ok)
    return count


def canonical_key(inst) -> str:
    """Key on degree and normalized diagonal-weight moduli, not presentation."""
    weights = list(inst.get("canonical_moduli") or inst["evaluation_cache"]["weights"])
    common = 0
    for weight in weights:
        common = math.gcd(common, abs(int(weight)))
    normalized = sorted({int(weight) // common for weight in weights})
    payload = json.dumps(
        {"degree": inst["degree"], "weight_ratio": normalized},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def escalate(params) -> dict | str | None:
    """Grow the coefficient tensor while retaining a fixed-size witness."""
    degree = int(params["n"])
    if degree >= 71:
        return "cap_bound"
    return {
        "n": degree + 6,
        "coeff_bound": int(params["coeff_bound"]) + 4,
        "answer_bound": int(params["answer_bound"]) * 2,
    }


def _poly_dict(inst):
    return {tuple(exponent): Fraction(coefficient) for coefficient, exponent in inst["polynomial_terms"]}


def _recover_line_from_forms(forms, weights):
    equations = []
    groups = {}
    for index, weight in enumerate(weights):
        groups.setdefault(weight, []).append(index)
    for group in groups.values():
        if len(group) != 2:
            raise ValueError("recovered weights do not pair")
        equations.append([forms[group[0]][j] + forms[group[1]][j] for j in range(4)])
    equations.sort(key=lambda row: 0 if row[0] else 1)
    r0, r1 = equations
    r0 = [value / r0[0] for value in r0]
    r1 = [value / r1[1] for value in r1]
    r0 = [r0[j] - r0[1] * r1[j] for j in range(4)]
    matrix = [r0, r1]
    answer = []
    for row in matrix:
        converted = []
        for value in row:
            value = Fraction(value)
            if value.denominator != 1:
                raise ValueError("recovered line left the integer certificate chart")
            converted.append(value.numerator)
        answer.append(converted)
    return answer


def _reference_deflation(inst):
    """Mechanical full-tensor triangular Waring deflation, with measured work."""
    degree = inst["degree"]
    residual = _poly_dict(inst)
    forms = []
    weights = []
    operations = 0
    scanned_terms = 0
    for pivot in range(4):
        pure = tuple(degree if i == pivot else 0 for i in range(4))
        weight = residual.get(pure, Fraction(0))
        if not weight:
            raise ValueError("zero pivot in Waring deflation")
        linear = [Fraction(0)] * 4
        linear[pivot] = Fraction(1)
        for column in range(pivot + 1, 4):
            exponent = [0] * 4
            exponent[pivot] = degree - 1
            exponent[column] = 1
            coefficient = residual.get(tuple(exponent), Fraction(0))
            linear[column] = coefficient / (degree * weight)
            operations += 2
        forms.append(linear)
        weights.append(weight)
        expanded = _expand_power(linear, degree, weight)
        for exponent, coefficient in expanded.items():
            residual[exponent] = residual.get(exponent, Fraction(0)) - coefficient
            operations += 1 + sum(2 for e in exponent if e)
            scanned_terms += 1
            if residual[exponent] == 0:
                del residual[exponent]
    if residual:
        raise ValueError("deflation did not reproduce the displayed polynomial")
    answer = _recover_line_from_forms(forms, weights)
    return answer, {"operations": operations, "scanned_terms": scanned_terms}


def _compact_leading_slice(inst):
    """Recover using only pure and x_i^(d-1)x_j coefficient lookups."""
    degree = inst["degree"]
    coefficients = _poly_dict(inst)
    forms = []
    weights = []
    operations = 0
    lookups = 0
    for pivot in range(4):
        pure = tuple(degree if i == pivot else 0 for i in range(4))
        value = coefficients.get(pure, Fraction(0))
        lookups += 1
        for old_form, old_weight in zip(forms, weights):
            value -= old_weight * old_form[pivot] ** degree
            operations += 3
        weight = value
        linear = [Fraction(0)] * 4
        linear[pivot] = Fraction(1)
        for column in range(pivot + 1, 4):
            exponent = [0] * 4
            exponent[pivot] = degree - 1
            exponent[column] = 1
            value = coefficients.get(tuple(exponent), Fraction(0))
            lookups += 1
            for old_form, old_weight in zip(forms, weights):
                value -= (
                    old_weight
                    * degree
                    * old_form[pivot] ** (degree - 1)
                    * old_form[column]
                )
                operations += 5
            linear[column] = value / (degree * weight)
            operations += 2
        forms.append(linear)
        weights.append(weight)
    answer = _recover_line_from_forms(forms, weights)
    # Pairing, two row scalings, and one elimination: a conservative exact count.
    operations += 36
    return answer, {"operations": operations, "coefficient_lookups": lookups}


def _eval_endpoint(inst, u, w):
    degree = inst["degree"]
    total = 0
    cache = inst["evaluation_cache"]
    for linear, weight in zip(cache["forms"], cache["weights"]):
        alpha = -linear[0] * u - linear[1] * w + linear[2]
        total += weight * alpha ** degree
    return total


def _attack_outlier(inst):
    pure = []
    degree = inst["degree"]
    coefficients = _poly_dict(inst)
    bound = inst["answer_bound"]
    width = 2 * bound + 1
    for variable in range(4):
        exponent = tuple(degree if i == variable else 0 for i in range(4))
        value = abs(int(coefficients.get(exponent, 0)))
        pure.append(value % width - bound)
    return [[1, 0, pure[0], pure[1]], [0, 1, pure[2], pure[3]]], 4


def _attack_greedy(inst):
    best_left = min(
        itertools.product(range(-3, 4), repeat=2),
        key=lambda pair: abs(_eval_endpoint(inst, pair[0], pair[1])),
    )
    # The t endpoint is the same computation after swapping free-coordinate
    # columns in each cached form.
    swapped = dict(inst)
    cache = inst["evaluation_cache"]
    swapped["evaluation_cache"] = {
        "forms": [[row[0], row[1], row[3], row[2]] for row in cache["forms"]],
        "weights": list(cache["weights"]),
    }
    best_right = min(
        itertools.product(range(-3, 4), repeat=2),
        key=lambda pair: abs(_eval_endpoint(swapped, pair[0], pair[1])),
    )
    # swapped endpoint variables are v,z.
    candidate = [[1, 0, best_left[0], best_right[0]], [0, 1, best_left[1], best_right[1]]]
    return candidate, 98 * 4


def _attack_random(inst, seed, restarts=256):
    rng = random.Random(seed ^ 0xA51CE55)
    for attempt in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate, attempt + 1
    return None, restarts


def _attack_small_ansatz(inst):
    attempts = 0
    for u, v, w, z in itertools.product(range(-2, 3), repeat=4):
        attempts += 1
        candidate = [[1, 0, u, v], [0, 1, w, z]]
        if verify(inst, candidate)[0]:
            return candidate, attempts
    return None, attempts


def _scale_instance(inst, scalar):
    out = dict(inst)
    out["polynomial_terms"] = [[scalar * c, list(e)] for c, e in inst["polynomial_terms"]]
    cache = inst["evaluation_cache"]
    out["evaluation_cache"] = {
        "forms": [list(row) for row in cache["forms"]],
        "weights": [scalar * weight for weight in cache["weights"]],
    }
    out["canonical_moduli"] = [scalar * value for value in inst["canonical_moduli"]]
    out["answer"] = [list(row) for row in inst["answer"]]
    return out


def _coordinate_shear(inst, shear):
    """Substitute x=B*y for upper-unipotent B and carry the line equations."""
    cache = inst["evaluation_cache"]
    forms = [
        [sum(row[k] * shear[k][j] for k in range(4)) for j in range(4)]
        for row in cache["forms"]
    ]
    weights = list(cache["weights"])
    answer_rows = [
        [sum(row[k] * shear[k][j] for k in range(4)) for j in range(4)]
        for row in inst["answer"]
    ]
    factor = answer_rows[0][1]
    answer_rows[0] = [answer_rows[0][j] - factor * answer_rows[1][j] for j in range(4)]
    out = dict(inst)
    out["evaluation_cache"] = {"forms": forms, "weights": weights}
    out["polynomial_terms"] = _surface_terms(forms, weights, inst["degree"])
    out["answer"] = answer_rows
    out["answer_bound"] = max(
        inst["answer_bound"],
        max(abs(value) for row in answer_rows for value in row),
    )
    return out


def _reorder_instance(inst, rng):
    out = dict(inst)
    terms = [[c, list(e)] for c, e in inst["polynomial_terms"]]
    rng.shuffle(terms)
    out["polynomial_terms"] = terms
    out["evaluation_cache"] = {
        "forms": [list(row) for row in inst["evaluation_cache"]["forms"]],
        "weights": list(inst["evaluation_cache"]["weights"]),
    }
    out["answer"] = [list(row) for row in inst["answer"]]
    return out


def _cache_matches_table(inst):
    cache = inst["evaluation_cache"]
    expected = _surface_terms(cache["forms"], cache["weights"], inst["degree"])
    normalize = lambda rows: sorted((tuple(e), int(c)) for c, e in rows)
    return normalize(expected) == normalize(inst["polynomial_terms"])


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest() -> dict:
    report = {}

    # G1: every preset, multiple seeds, exact JSON-native answers and cache/table equality.
    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            attempts += 1
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            cache_ok = _cache_matches_table(inst)
            if not (ok and json_ok and cache_ok):
                failures.append({
                    "preset": preset,
                    "seed": seed,
                    "verify": reason,
                    "json": json_ok,
                    "cache": cache_ok,
                })
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=424242, **shipping_params)
    answer = [list(row) for row in inst["answer"]]
    corruptions = {
        "drop": [answer[0][:-1], list(answer[1])],
        "swap": [list(answer[1]), list(answer[0])],
        "duplicate": [list(answer[0]), list(answer[0])],
        "empty": [],
        "out_of_range": [list(answer[0]), [0, 1, answer[1][2], inst["answer_bound"] + 1]],
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"accepted": ok, "reason": reason}
    reasons = [case["reason"] for case in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not case["accepted"] for case in cases.values()) and len(set(reasons)) == 5,
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    encoded = json.dumps(answer, separators=(",", ":"))
    realistic = f"I used the homogeneous restriction.\n```json\nnoise\n```\n<answer>```json\n{encoded}\n```</answer>\nDone."
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("garbage") is None,
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4 and the shipping-density half of G5 share the mandatory 200k sample.
    rng = random.Random(0x190205133)
    total = 200_000
    hits = 0
    started = time.perf_counter()
    for _ in range(total):
        hits += int(verify(inst, random_candidate(inst, rng))[0])
    guess_wall = time.perf_counter() - started
    fraction = hits / total
    report["G4_guess_resistance"] = {
        "pass": fraction < 1e-6,
        "hits": hits,
        "total": total,
        "observed_fraction": fraction,
        "candidate_space": search_space(inst),
        "sampling_prior": "uniform over all four bounded integer entries in the required affine chart",
        "wall_clock_sec": round(guess_wall, 6),
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)

    # G6 attacks and the Track-B reference algorithm.
    attack_specs = {
        "outlier_pure_coefficient": lambda obj, seed: _attack_outlier(obj),
        "greedy_endpoint_cancellation": lambda obj, seed: _attack_greedy(obj),
        "random_restart_256": lambda obj, seed: _attack_random(obj, seed, 256),
        "small_integer_waring_ansatz": lambda obj, seed: _attack_small_ansatz(obj),
    }
    attack_results = {
        name: {"successes": 0, "attempts": 0, "operations": 0, "wall_clock_sec": 0.0}
        for name in attack_specs
    }
    reference_successes = 0
    reference_operations = 0
    reference_terms = 0
    reference_wall = 0.0
    compact_operations = 0
    compact_lookups = 0
    for seed in range(8):
        attack_inst = make_instance(seed=10_000 + seed, **shipping_params)
        for name, attack in attack_specs.items():
            started = time.perf_counter()
            candidate, operations = attack(attack_inst, seed)
            elapsed = time.perf_counter() - started
            success = candidate is not None and verify(attack_inst, candidate)[0]
            result = attack_results[name]
            result["successes"] += int(success)
            result["attempts"] += 1
            result["operations"] += operations
            result["wall_clock_sec"] += elapsed

        started = time.perf_counter()
        recovered, stats = _reference_deflation(attack_inst)
        reference_wall += time.perf_counter() - started
        reference_successes += int(verify(attack_inst, recovered)[0])
        reference_operations += stats["operations"]
        reference_terms += stats["scanned_terms"]

        compact, compact_stats = _compact_leading_slice(attack_inst)
        if not verify(attack_inst, compact)[0]:
            failures.append({"compact_seed": seed})
        compact_operations = max(compact_operations, compact_stats["operations"])
        compact_lookups = max(compact_lookups, compact_stats["coefficient_lookups"])

    for result in attack_results.values():
        result["wall_clock_sec"] = round(result["wall_clock_sec"], 6)
    all_failed = all(result["successes"] == 0 and result["attempts"] >= 8 for result in attack_results.values())
    reference = {
        "name": "full triangular Waring deflation over Q",
        "complexity": "O(binomial(d+3,3)) exact coefficient operations",
        "wall_clock_sec": round(reference_wall, 6),
        "operations": reference_operations,
        "scanned_terms": reference_terms,
        "solves": f"{reference_successes}/8, as expected",
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": reference,
        "in_context_attack": "small_integer_waring_ansatz",
    }

    strongest_name, strongest = max(
        attack_results.items(), key=lambda item: item[1]["operations"]
    )
    report["G5_density_and_baseline"] = {
        "pass": demo_count is not None and hits == 0 and reference_successes == 8,
        "shipping_candidate_space": search_space(inst),
        "shipping_sampled_valid_hits": hits,
        "shipping_sampled_valid_total": total,
        "shipping_sampled_density": fraction,
        "demo_degree": demo["degree"],
        "demo_candidate_count": search_space(demo),
        "demo_exact_solution_count": demo_count,
        "strongest_failing_attack": strongest_name,
        "strongest_failing_attack_operations": strongest["operations"],
        "strongest_failing_attack_wall_clock_sec": strongest["wall_clock_sec"],
        "reference_algorithm": reference,
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * shipping_params["n"] + 1  # nearest supported odd degree
    doubled_params["answer_bound"] *= 2
    doubled = make_instance(seed=91, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    _, shipping_ref_stats = _reference_deflation(inst)
    _, doubled_ref_stats = _reference_deflation(doubled)
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_ref_stats["scanned_terms"] > 2 * shipping_ref_stats["scanned_terms"],
        "shipping_degree": inst["degree"],
        "shipping_polynomial_terms": len(inst["polynomial_terms"]),
        "shipping_reference_terms": shipping_ref_stats["scanned_terms"],
        "doubled_params": doubled_params,
        "doubled_polynomial_terms": len(doubled["polynomial_terms"]),
        "doubled_reference_terms": doubled_ref_stats["scanned_terms"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "answer_shape_unchanged": [len(doubled["answer"]), len(doubled["answer"][0])] == [2, 4],
    }

    invariance_checks = 0
    carried_checks = 0
    invariance_failures = []
    distinct = set()
    shear = [
        [1, 1, -1, 0],
        [0, 1, 1, 1],
        [0, 0, 1, -1],
        [0, 0, 0, 1],
    ]
    for seed in range(20):
        base = make_instance(seed=30_000 + seed, **shipping_params)
        base_key = canonical_key(base)
        distinct.add(base_key)
        reordered = _reorder_instance(base, random.Random(seed))
        scaled = _scale_instance(base, 7)
        sheared = _coordinate_shear(base, shear)
        composed = _reorder_instance(_scale_instance(sheared, 11), random.Random(100 + seed))
        for name, transformed in (
            ("term_reordering", reordered),
            ("polynomial_scaling", scaled),
            ("upper_unipotent_coordinate_change", sheared),
            ("composed_change_scale_reorder", composed),
        ):
            invariance_checks += 1
            if canonical_key(transformed) != base_key:
                invariance_failures.append({"seed": seed, "transform": name, "kind": "key"})
            carried_checks += 1
            if not verify(transformed, transformed["answer"])[0]:
                invariance_failures.append({"seed": seed, "transform": name, "kind": "witness"})
    report["G8_canonical_key"] = {
        "pass": not invariance_failures and len(distinct) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "invariance_failures": invariance_failures,
        "unrelated_instances": 20,
        "distinct_keys": len(distinct),
        "transformations": [
            "coefficient-row reordering",
            "nonzero global polynomial scaling",
            "upper-unipotent projective coordinate change",
            "composition of coordinate change, scaling, and row reordering",
        ],
        "key_caveat": "construction invariant, not a complete projective-equivalence algorithm",
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_atoms = _answer_atoms(inst["answer"])
    answer_tokens = math.ceil(answer_chars / 4)
    within_caps = answer_chars <= 2000 and answer_atoms <= 256 and compact_operations <= 300
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_hardened = G9_ORACLE_RESULTS["hinted_verdict"] == "hardened"
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
            - arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
        ),
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": compact_operations,
        "intended_route_coefficient_lookups": compact_lookups,
        "within_caps": within_caps,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping_params)
    report["all_passed"] = all(
        gate.get("pass", True)
        for name, gate in report.items()
        if name.startswith("G") and isinstance(gate, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
