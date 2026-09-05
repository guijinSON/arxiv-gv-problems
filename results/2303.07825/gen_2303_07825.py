"""Verified problem generator for arXiv:2303.07825.

The paper's Section 6 treats arbitrary binary quadratic Diophantine
equations by reducing them to generalized Pell equations.  This module runs
that construction backwards: it starts from a certified Pell solution, hides
the Pell conic by an affine unimodular coordinate change, and supplies an
integer box containing the transported solution.  Generation never searches
the emitted box.
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


# Keep the repository helpers importable when this file is run from its result
# directory.  The family only needs Python's exact integers, so gvlib is an
# optional compatibility import rather than a dependency.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import rationals  # noqa: F401
except ImportError:  # pragma: no cover - the generator remains stdlib-only
    rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "number_theory",
    "object_regime": "integer_lattice",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "binary quadratic Diophantine equation over the integers",
        "inclusive integer bounding box",
    ],
    "verification_operations": [
        "inclusive integer-bound comparison",
        "exact integer substitution into a quadratic polynomial",
        "exact equality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "An affine unimodular change of variables hides a Pell conic; without "
        "recognizing that form, the bounded exact route scans a large interval."
    ),
    "hardness_basis": (
        "Track B: exact O(W) discriminant scanning averages 103400 iterations, "
        "1344225 counted exact operations, and 0.06-0.43 seconds across unloaded "
        "and shared-runner measurements at shipping n=250007, while recognizing and "
        "exploiting the affine Pell form takes at most 189 exact operations across "
        "10000 measured seeds."
    ),
    "max_answer_tokens": 6,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

# n is the number of allowed integers in each coordinate interval.  Increasing
# n grows the search rectangle while the answer remains a pair of integers.
DIFFICULTY: dict = {
    "demo": {"n": 9},
    "easy": {"n": 2_003},
    "medium": {"n": 25_003},
    "hard": {"n": 250_007},
}
SHIPPING_DIFFICULTY: str = "hard"

STRUCTURAL_HINT: str = (
    "Look for an affine unimodular coordinate system in which the quadratic "
    "becomes a Pell conic."
)
PLACEBO_HINT: str = (
    "Look for careful integer bookkeeping that respects both inclusive "
    "coordinate intervals throughout."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON list [x,y] of exactly two integers, with x and y drawn uniformly "
        "from their instance-supplied inclusive intervals."
    ),
    "bounds": {
        "coordinates": 2,
        "interval_width_each": "n",
        "max_coordinate_bits": 1024,
        "candidate_count": "n^2",
    },
}

NOTES: str = (
    "Section 2.1 fixes a solution as a substitution, and Sections 2.4 and 2.6 "
    "fix normal-form output and constraints. Section 6, Theorem 6.4 in the "
    "published numbering (the source label quad_eqn_thm), treats arbitrary "
    "two-variable quadratic equations and explains Lagrange reduction to a "
    "generalized Pell equation; its Pell lemma gives the recurrence used here. "
    "The easy regimes explicitly identified there--nonpositive Pell parameter "
    "or a square parameter--are excluded. Plants are placed uniformly within "
    "their boxes. Interval landmarks, residual greedy rounding, random restart, "
    "and a small-coordinate square-root ansatz all fail in the adversary panel. "
    "A full exact discriminant scan is disclosed as the successful Track-B "
    "reference algorithm."
)

# Filled from the script-owned hardening runs.  These are diagnostics only;
# since 2026-09-05, G9 gates the size and intended-route caps, not oracle success.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0, "errors": 4,
             "error_reason": "OpenRouter HTTP 403 total key limit"},
    "hinted": {"solved": 0, "attempts": 0, "errors": 4,
               "error_reason": "OpenRouter HTTP 403 total key limit"},
    "placebo": {"solved": 0, "attempts": 0, "errors": 4,
                "error_reason": "OpenRouter HTTP 403 total key limit"},
    "hinted_verdict": "unrun_api_quota",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_n(n):
    if not _is_int(n) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if n > 10 ** 300:
        raise ValueError("n exceeds the declared 1024-bit certificate language")


def _expand_pell(a, b, c, d, e, f, pell_d):
    """Coefficients of (a*x+b*y+e)^2-D(c*x+d*y+f)^2-1."""
    return [
        a * a - pell_d * c * c,
        2 * (a * b - pell_d * c * d),
        b * b - pell_d * d * d,
        2 * (a * e - pell_d * c * f),
        2 * (b * e - pell_d * d * f),
        e * e - pell_d * f * f - 1,
    ]


def _poly_value(coefficients, x, y):
    xx, xy, yy, lx, ly, const = coefficients
    return xx * x * x + xy * x * y + yy * y * y + lx * x + ly * y + const


def make_instance(n: int, seed: int = 0, **params: object) -> dict:
    """Transport a recurrence-certified Pell solution into an integer box."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_n(n)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)

    # D=m^2-1 is positive and nonsquare.  (m,1) is its fundamental positive
    # Pell solution: if a smaller v existed, it would have v=0.
    m = rng.randint(3, 11)
    pell_d = m * m - 1
    shear_abs = rng.randint(1, m - 2)
    shear = shear_abs if rng.getrandbits(1) else -shear_abs
    second_abs = rng.randint(1, m - 2)
    second_shear = second_abs if rng.getrandbits(1) else -second_abs
    swapped = bool(rng.getrandbits(1))
    shift_u = rng.randint(-n, n)
    shift_v = rng.randint(-n, n)

    # Generate (u,v) by the exact recurrence from the paper's Pell lemma.
    # The generous gap makes the n-by-n box isolate this recurrence level, yet
    # no search for a solution to the emitted quadratic is performed.
    pell_u, pell_v, pell_step = 1, 0, 0
    while True:
        base_x = pell_u - shift_u - shear * (pell_v - shift_v)
        base_y = (-second_shear * (pell_u - shift_u)
                  + (1 + shear * second_shear) * (pell_v - shift_v))
        if min(abs(base_x), abs(base_y)) > 40 * n:
            break
        pell_u, pell_v = (
            m * pell_u + pell_d * pell_v,
            pell_u + m * pell_v,
        )
        pell_step += 1

    # Two integral shears give the determinant-one matrix
    # [[1+p*q,p],[q,1]].  An optional variable swap keeps determinant +/-1,
    # hence the transform maps Z^2 bijectively to Z^2.
    base_x = pell_u - shift_u - shear * (pell_v - shift_v)
    base_y = (-second_shear * (pell_u - shift_u)
              + (1 + shear * second_shear) * (pell_v - shift_v))
    if not swapped:
        answer_x, answer_y = base_x, base_y
        a, b = 1 + shear * second_shear, shear
        c, d = second_shear, 1
    else:
        answer_x, answer_y = base_y, base_x
        a, b = shear, 1 + shear * second_shear
        c, d = 1, second_shear

    # Keep the two coordinate intervals disjoint.  This changes only the affine
    # origin and guarantees that the G2 coordinate-swap corruption is genuine.
    while abs(answer_x - answer_y) <= 2 * n:
        # Changing shift_u changes base_x-base_y by
        # -5*n*(1+second_shear), except that this vanishes when the second
        # shear is -1.  In precisely that case, changing shift_v changes the
        # difference by 5*n*(shear + 1 + shear*second_shear) = 5*n.
        # Thus the chosen update always moves the difference by at least 5*n,
        # so one pass takes it from <=2*n to >=3*n.
        if second_shear != -1:
            shift_u += 5 * n
        else:
            shift_v += 5 * n
        base_x = pell_u - shift_u - shear * (pell_v - shift_v)
        base_y = (-second_shear * (pell_u - shift_u)
                  + (1 + shear * second_shear) * (pell_v - shift_v))
        if not swapped:
            answer_x, answer_y = base_x, base_y
        else:
            answer_x, answer_y = base_y, base_x

    coefficients = _expand_pell(a, b, c, d, shift_u, shift_v, pell_d)
    before_x = rng.randrange(n)
    before_y = rng.randrange(n)
    bounds = [
        [answer_x - before_x, answer_x - before_x + n - 1],
        [answer_y - before_y, answer_y - before_y + n - 1],
    ]
    answer = [answer_x, answer_y]
    if _poly_value(coefficients, answer_x, answer_y) != 0:
        raise AssertionError("internal Pell transport failed")
    return {
        "paper": "arXiv:2303.07825",
        "n": n,
        "coefficients": coefficients,
        "bounds": bounds,
        "answer": answer,
        "route_step_bound": pell_step,
    }


def _signed_term(coefficient, monomial, first=False):
    if coefficient == 0:
        return ""
    sign = "-" if coefficient < 0 else "+"
    magnitude = abs(coefficient)
    body = str(magnitude) if not monomial else (
        monomial if magnitude == 1 else f"{magnitude}*{monomial}"
    )
    if first:
        return ("-" if coefficient < 0 else "") + body
    return f" {sign} {body}"


def _format_polynomial(coefficients):
    monomials = ("x^2", "x*y", "y^2", "x", "y", "")
    pieces = []
    for coefficient, monomial in zip(coefficients, monomials):
        if coefficient:
            pieces.append(_signed_term(coefficient, monomial, not pieces))
    return "".join(pieces) if pieces else "0"


def render(inst: dict) -> str:
    """Render a complete exact bounded Diophantine problem."""
    x_bounds, y_bounds = inst["bounds"]
    statement = f"""Find one integer solution of this bounded binary quadratic Diophantine equation.

An integer solution is an ordered pair (x,y) of ordinary base-10 integers for which the displayed polynomial is exactly zero. Multiplication is written with *, and x^2 means x*x.

Equation:
  {_format_polynomial(inst['coefficients'])} = 0

Inclusive bounds:
  {x_bounds[0]} <= x <= {x_bounds[1]}
  {y_bounds[0]} <= y <= {y_bounds[1]}

Both interval endpoints are included. The order matters: the first coordinate is x and the second is y. There are no floating-point approximations.

Give your final answer inside <answer></answer> tags as a JSON list of exactly two base-10 integers [x,y].
Example: <answer>[3,-17]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract a two-integer JSON list from a tagged model response."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    if not matches:
        return None
    payload = matches[-1].strip()
    fence = re.fullmatch(r"```(?:json|text)?\s*(.*?)\s*```", payload,
                         flags=re.IGNORECASE | re.DOTALL)
    if fence:
        payload = fence.group(1).strip()
    try:
        value = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if (not isinstance(value, list) or len(value) != 2
            or not all(_is_int(item) for item in value)):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check bounds and exact substitution; never consult inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) == 1:
        return False, "answer has one coordinate; exactly two are required"
    if len(answer) != 2:
        return False, f"answer has {len(answer)} coordinates; exactly two are required"
    if not all(_is_int(item) for item in answer):
        return False, "both coordinates must be base-10 integers"
    x, y = answer
    (x_lo, x_hi), (y_lo, y_hi) = inst["bounds"]
    if not x_lo <= x <= x_hi:
        return False, f"x={x} is outside the inclusive interval [{x_lo},{x_hi}]"
    if not y_lo <= y <= y_hi:
        return False, f"y={y} is outside the inclusive interval [{y_lo},{y_hi}]"
    residual = _poly_value(inst["coefficients"], x, y)
    if residual != 0:
        return False, f"exact substitution at ({x},{y}) gives {residual}, not 0"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the stated integer rectangle."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    return [rng.randint(*inst["bounds"][0]), rng.randint(*inst["bounds"][1])]


def search_space(inst: dict) -> int | None:
    """The exact cardinality of the instance's bounded certificate language."""
    (x_lo, x_hi), (y_lo, y_hi) = inst["bounds"]
    return (x_hi - x_lo + 1) * (y_hi - y_lo + 1)


def _roots_for_x_counted(coefficients, x):
    """Return integral y roots and an exact-arithmetic operation count."""
    xx, xy, yy, lx, ly, const = coefficients
    linear = xy * x + ly
    fixed = xx * x * x + lx * x + const
    operations = 7  # two affine terms: four products and three additions
    if yy == 0:
        if linear == 0:
            return (None if fixed == 0 else []), operations
        numerator = -fixed
        operations += 1  # remainder
        if numerator % linear:
            return [], operations
        operations += 1  # quotient
        return [numerator // linear], operations
    discriminant = linear * linear - 4 * yy * fixed
    operations += 4
    if discriminant < 0:
        return [], operations
    root = math.isqrt(discriminant)
    operations += 2  # isqrt and square
    if root * root != discriminant:
        return [], operations
    denominator = 2 * yy
    operations += 1
    answers = []
    for numerator in (-linear + root, -linear - root):
        operations += 2  # addition/subtraction and remainder
        if numerator % denominator == 0:
            operations += 1
            value = numerator // denominator
            if value not in answers:
                answers.append(value)
    return answers, operations


def _roots_for_x(coefficients, x):
    """All integral y roots for fixed x, using the exact discriminant."""
    roots, _ = _roots_for_x_counted(coefficients, x)
    return roots


def _discriminant_scan(inst, stop_first=True):
    """Successful generic Track-B reference algorithm."""
    (x_lo, x_hi), (y_lo, y_hi) = inst["bounds"]
    solutions = []
    iterations = operations = 0
    for x in range(x_lo, x_hi + 1):
        iterations += 1
        roots, root_operations = _roots_for_x_counted(
            inst["coefficients"], x
        )
        operations += root_operations
        if roots is None:
            # This branch cannot occur in generated instances; a linear identity
            # would make every bounded y a root.
            roots = range(y_lo, y_hi + 1)
        for y in roots:
            if y_lo <= y <= y_hi:
                candidate = [x, y]
                operations += 13  # exact substitution into six terms
                if verify(inst, candidate)[0]:
                    solutions.append(candidate)
                    if stop_first:
                        return solutions, {"iterations": iterations,
                                           "scalar_operations": operations}
    return solutions, {"iterations": iterations, "scalar_operations": operations}


def enumerate_all(inst: dict) -> int | None:
    """Count all bounded answers when the exact scan is safely capped."""
    width = inst["bounds"][0][1] - inst["bounds"][0][0] + 1
    if width > 300_000:
        return None
    solutions, _ = _discriminant_scan(inst, stop_first=False)
    return len(solutions)


def _substitute_polynomial(coefficients, a, b, e, c, d, f):
    """Substitute old x=a*u+b*v+e, old y=c*u+d*v+f."""
    xx, xy, yy, lx, ly, const = coefficients
    return [
        xx * a * a + xy * a * c + yy * c * c,
        2 * xx * a * b + xy * (a * d + b * c) + 2 * yy * c * d,
        xx * b * b + xy * b * d + yy * d * d,
        2 * xx * a * e + xy * (a * f + c * e) + 2 * yy * c * f + lx * a + ly * c,
        2 * xx * b * e + xy * (b * f + d * e) + 2 * yy * d * f + lx * b + ly * d,
        xx * e * e + xy * e * f + yy * f * f + lx * e + ly * f + const,
    ]


def _primitive_coefficients(coefficients):
    divisor = 0
    for value in coefficients:
        divisor = math.gcd(divisor, abs(value))
    divisor = divisor or 1
    primitive = [value // divisor for value in coefficients]
    first = next((value for value in primitive if value), 1)
    if first < 0:
        primitive = [-value for value in primitive]
    return primitive


def canonical_key(inst: dict) -> str:
    """Normalize translations, axis reflections/swaps, order, sign, and gcd."""
    (x_lo, x_hi), (y_lo, y_hi) = inst["bounds"]
    width_x, width_y = x_hi - x_lo, y_hi - y_lo
    normalized = _substitute_polynomial(
        inst["coefficients"], 1, 0, x_lo, 0, 1, y_lo
    )
    forms = []
    for swap in (False, True):
        for flip_x in (False, True):
            for flip_y in (False, True):
                sx, sy = (-1 if flip_x else 1), (-1 if flip_y else 1)
                ex, ey = (width_x if flip_x else 0), (width_y if flip_y else 0)
                if not swap:
                    coeff = _substitute_polynomial(
                        normalized, sx, 0, ex, 0, sy, ey
                    )
                    widths = [width_x, width_y]
                else:
                    # old p=sx*v+ex, old q=sy*u+ey
                    coeff = _substitute_polynomial(
                        normalized, 0, sx, ex, sy, 0, ey
                    )
                    widths = [width_y, width_x]
                forms.append(json.dumps(
                    [widths, _primitive_coefficients(coeff)],
                    separators=(",", ":"),
                ))
    payload = min(forms).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _relabel_instance(inst, swap, flip_x, flip_y, shift_x, shift_y):
    """Apply new=(signed permutation)*old+shift and carry the witness."""
    sx, sy = (-1 if flip_x else 1), (-1 if flip_y else 1)
    (x_lo, x_hi), (y_lo, y_hi) = inst["bounds"]
    old_x, old_y = inst["answer"]
    if not swap:
        # old x=sx*(u-shift_x), old y=sy*(v-shift_y)
        substitution = (sx, 0, -sx * shift_x, 0, sy, -sy * shift_y)
        new_x = sx * old_x + shift_x
        new_y = sy * old_y + shift_y
        bx = sorted((sx * x_lo + shift_x, sx * x_hi + shift_x))
        by = sorted((sy * y_lo + shift_y, sy * y_hi + shift_y))
    else:
        # u=sx*old_y+shift_x, v=sy*old_x+shift_y
        substitution = (0, sy, -sy * shift_y, sx, 0, -sx * shift_x)
        new_x = sx * old_y + shift_x
        new_y = sy * old_x + shift_y
        bx = sorted((sx * y_lo + shift_x, sx * y_hi + shift_x))
        by = sorted((sy * x_lo + shift_y, sy * x_hi + shift_y))
    transformed = dict(inst)
    transformed["coefficients"] = _substitute_polynomial(
        inst["coefficients"], *substitution
    )
    transformed["bounds"] = [bx, by]
    transformed["answer"] = [new_x, new_y]
    return transformed


def _recover_pell_form_counted(inst):
    """Recover the two-shear Pell form and conservatively count arithmetic.

    The count charges each integer addition, subtraction, multiplication,
    quotient, remainder, and ``isqrt`` as one exact operation.  Comparisons,
    sign changes, coefficient permutations, and bound checks are free.  Some
    short-circuited checks are charged anyway, so this is an upper bound for
    the executed recovery path rather than an optimistic source-line count.
    """
    original = inst["coefficients"]
    operations = 0
    for orientation in ("direct", "swap"):
        if orientation == "direct":
            coefficients = original
        else:
            # Q(v,u): renaming axes only permutes coefficients.
            xx0, xy0, yy0, lx0, ly0, const0 = original
            coefficients = [yy0, xy0, xx0, ly0, lx0, const0]
        xx, xy, yy, lx, ly, const = coefficients
        discriminant = xy * xy - 4 * xx * yy
        operations += 6  # four arithmetic ops and two conservative remainders
        if discriminant <= 0 or discriminant % 4 or xy % 2:
            continue
        pell_d = discriminant // 4
        m = math.isqrt(pell_d + 1)
        operations += 4  # quotient, addition, isqrt, square
        if m * m != pell_d + 1:
            continue
        shear_square = yy + pell_d
        operations += 1
        if shear_square <= 0:
            continue
        shear_root = math.isqrt(shear_square)
        operations += 2  # isqrt and square
        if shear_root * shear_root != shear_square:
            continue
        half_xy = xy // 2
        operations += 1
        for shear in (shear_root, -shear_root):
            shear_numerator = half_xy - shear
            operations += 2  # subtraction and conservative remainder
            if yy == 0 or shear_numerator % yy:
                continue
            second_shear = shear_numerator // yy
            a = 1 + shear * second_shear
            operations += 3  # quotient, multiplication, addition

            # Validate only the three homogeneous coefficients.  Calling the
            # six-coefficient expander here would do irrelevant arithmetic on
            # zero affine shifts and would not be the compact by-hand route.
            rebuilt_homogeneous = [
                a * a - pell_d * second_shear * second_shear,
                2 * (a * shear - pell_d * second_shear),
                shear * shear - pell_d,
            ]
            operations += 12
            if rebuilt_homogeneous != coefficients[:3]:
                continue
            operations += 2  # two conservative parity remainders
            if lx % 2 or ly % 2:
                continue
            half_x, half_y = lx // 2, ly // 2
            operations += 2
            shift_u = half_x - second_shear * half_y
            numerator = shear * half_x - a * half_y
            operations += 7  # three products/two differences, remainder, quotient
            if numerator % pell_d:
                continue
            shift_v = numerator // pell_d

            # The homogeneous terms already match.  Checking the two linear
            # terms and the constant costs fourteen further exact operations.
            rebuilt_affine = [
                2 * (a * shift_u
                     - pell_d * second_shear * shift_v),
                2 * (shear * shift_u - pell_d * shift_v),
                shift_u * shift_u - pell_d * shift_v * shift_v - 1,
            ]
            operations += 14
            if rebuilt_affine == coefficients[3:]:
                return ((orientation, shear, second_shear,
                         shift_u, shift_v, pell_d), operations)
    return None, operations


def _recover_pell_form(inst):
    """Recover the two-shear affine Pell coordinates exactly."""
    recovered, _ = _recover_pell_form_counted(inst)
    return recovered


def _linear_range(a, b, const, x_bounds, y_bounds):
    values = [a * x + b * y + const
              for x in x_bounds for y in y_bounds]
    return min(values), max(values)


def _compact_pell_solver(inst):
    """Public-data-only compact solver used to measure intended route effort."""
    recovered, operations = _recover_pell_form_counted(inst)
    if recovered is None:
        return None, {"exact_operations": operations, "recurrence_steps": 0}
    orientation, shear, second_shear, shift_u, shift_v, pell_d = recovered
    m = math.isqrt(pell_d + 1)
    operations += 4  # two additions, isqrt, square
    if m * m != pell_d + 1:
        return None, {"exact_operations": operations, "recurrence_steps": 0}
    if orientation == "direct":
        x_bounds, y_bounds = inst["bounds"]
    else:
        y_bounds, x_bounds = inst["bounds"]
    a = 1 + shear * second_shear
    operations += 2
    u_range = _linear_range(a, shear, shift_u, x_bounds, y_bounds)
    v_range = _linear_range(second_shear, 1, shift_v, x_bounds, y_bounds)
    operations += 32  # four affine corner evaluations for each range
    sign_us = (1,) if u_range[0] > 0 else ((-1,) if u_range[1] < 0 else (1, -1))
    sign_vs = (1,) if v_range[0] > 0 else ((-1,) if v_range[1] < 0 else (1, -1))
    operations += 12
    pell_u, pell_v = 1, 0
    for step in range(0, 128):
        for sign_u in sign_us:
            for sign_v in sign_vs:
                target_u = sign_u * pell_u
                target_v = sign_v * pell_v
                # The affine image of the box is contained in these two exact
                # coordinate ranges.  Range rejection is comparison-only and
                # avoids doing an inverse transform for impossible sign/level
                # combinations.
                if not (u_range[0] <= target_u <= u_range[1]
                        and v_range[0] <= target_v <= v_range[1]):
                    continue
                delta_u = target_u - shift_u
                delta_v = target_v - shift_v
                visible_x = delta_u - shear * delta_v
                visible_y = (-second_shear * delta_u + a * delta_v)
                operations += 7
                candidate = ([visible_x, visible_y] if orientation == "direct"
                             else [visible_y, visible_x])
                # A recurrence point already satisfies the Pell equation.  The
                # inverse image therefore satisfies the displayed quadratic;
                # only the four bound comparisons are needed while iterating.
                in_bounds = all(
                    lo <= value <= hi
                    for value, (lo, hi) in zip(candidate, inst["bounds"])
                )
                if in_bounds:
                    operations += 13  # final exact polynomial substitution
                    if not verify(inst, candidate)[0]:
                        continue
                    return candidate, {
                        "exact_operations": operations,
                        "recurrence_steps": step,
                    }
        pell_u, pell_v = (
            m * pell_u + pell_d * pell_v,
            pell_u + m * pell_v,
        )
        operations += 5
    return None, {"exact_operations": operations, "recurrence_steps": 128}


def _attack_interval_landmark(inst):
    return [
        (inst["bounds"][0][0] + inst["bounds"][0][1]) // 2,
        (inst["bounds"][1][0] + inst["bounds"][1][1]) // 2,
    ]


def _attack_residual_greedy(inst):
    """Coarse x grid plus nearest quadratic-vertex rounding."""
    (x_lo, x_hi), (y_lo, y_hi) = inst["bounds"]
    _, xy, yy, _, ly, _ = inst["coefficients"]
    best = None
    for index in range(33):
        x = x_lo + (x_hi - x_lo) * index // 32
        if yy:
            centre = -(xy * x + ly) // (2 * yy)
        else:
            centre = (y_lo + y_hi) // 2
        for y in (y_lo, y_hi, max(y_lo, min(y_hi, centre - 1)),
                  max(y_lo, min(y_hi, centre)),
                  max(y_lo, min(y_hi, centre + 1))):
            score = abs(_poly_value(inst["coefficients"], x, y))
            row = (score, x, y)
            if best is None or row < best:
                best = row
    return [best[1], best[2]]


def _attack_random_restart(inst, rng, restarts=8192):
    best = None
    for _ in range(restarts):
        x, y = random_candidate(inst, rng)
        score = abs(_poly_value(inst["coefficients"], x, y))
        row = (score, x, y)
        if best is None or row < best:
            best = row
    return [best[1], best[2]]


def _attack_small_coordinate_ansatz(inst):
    """Try obvious landmarks and exact square roots only at those x values."""
    x_lo, x_hi = inst["bounds"][0]
    points = {x_lo, x_hi, (x_lo + x_hi) // 2}
    for value in (-2, -1, 0, 1, 2):
        if x_lo <= value <= x_hi:
            points.add(value)
    candidates = []
    y_lo, y_hi = inst["bounds"][1]
    for x in sorted(points):
        roots = _roots_for_x(inst["coefficients"], x) or []
        for y in roots:
            if y_lo <= y <= y_hi:
                candidates.append([x, y])
    if candidates:
        return candidates[0]
    return [min(points), y_lo]


def escalate(params: dict) -> dict | str | None:
    """Grow both interval widths while keeping a two-integer witness."""
    if not isinstance(params, dict) or set(params) != {"n"}:
        return None
    n = params["n"]
    _validate_n(n)
    # The immediate 4x rung above the named hard preset has a measured
    # worst-case compact route above G9's 300-operation limit.  A 16x jump
    # changes the recurrence alignment and stays within the cap (199 ops over
    # 10,000 seeds); one further 4x rung stays within it (202 ops).  The next
    # rung reaches 370, so the no-tool effort cap, not mathematical hardness,
    # ends this fixed-two-integer ladder there.
    if n >= 16_000_511:
        return "cap_bound"
    if n < 1_000_000:
        return {"n": 16 * n + 15}
    return {"n": 4 * n + 3}


def _json_answer_size(answer):
    compact = json.dumps(answer, separators=(",", ":"))
    return len(compact), (len(compact) + 3) // 4


def selftest() -> dict:
    report = {
        "paper": "arXiv:2303.07825",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures = []
    attempts = 0
    for preset, parameters in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **parameters)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
    }

    shipping = make_instance(seed=230307825, **DIFFICULTY[SHIPPING_DIFFICULTY])
    x, y = shipping["answer"]
    corruptions = {
        "drop_one": [x],
        "swap_coordinates": [y, x],
        "duplicate_one": [x, x, y],
        "empty": [],
        "out_of_range": [shipping["bounds"][0][1] + 1, y],
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    distinct_reasons = len({row["reason"] for row in corruption_results.values()})
    report["G2_rejects_corruption"] = {
        "pass": (all(row["rejected"] for row in corruption_results.values())
                 and distinct_reasons == len(corruption_results)),
        "cases": corruption_results,
        "distinct_reasons": distinct_reasons,
    }

    realistic = (
        "The exact substitution cancels.\n<answer>\n```json\n"
        + json.dumps(shipping["answer"], separators=(",", ":"))
        + "\n```\n</answer>\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and parse_answer("no answer here") is None,
        "parsed": parsed,
    }

    guess_rng = random.Random(0x230307825)
    guess_total = 200_000
    guess_hits = 0
    started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_elapsed = time.perf_counter() - started
    observed_density = guess_hits / guess_total
    exact_count = enumerate_all(shipping)
    exact_density = (exact_count / search_space(shipping)
                     if exact_count is not None else None)
    report["G4_guess_resistance"] = {
        "pass": (exact_density < 1e-6 if exact_density is not None
                 else observed_density < 1e-6),
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": observed_density,
        "exact_probability": exact_density,
        "probability_basis": ("exact enumeration of the shipping rectangle"
                              if exact_density is not None
                              else "structure-aware Monte Carlo at shipping"),
        "structure_aware_space": search_space(shipping),
        "sampling_rule": "uniform over both stated inclusive integer intervals",
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attack_functions = {
        "interval_midpoint_outlier": lambda inst, rng: _attack_interval_landmark(inst),
        "coarse_residual_greedy": lambda inst, rng: _attack_residual_greedy(inst),
        "random_restart_8192": lambda inst, rng: _attack_random_restart(inst, rng, 8192),
        "small_coordinate_square_root_ansatz": (
            lambda inst, rng: _attack_small_coordinate_ansatz(inst)
        ),
    }
    attack_results = {name: {"successes": 0, "attempts": 0}
                      for name in attack_functions}
    attack_elapsed = {name: 0.0 for name in attack_functions}
    attack_seeds = list(range(8100, 8108))
    reference_successes = compact_successes = 0
    reference_elapsed = 0.0
    reference_iterations = []
    reference_operations = []
    compact_operations = []
    compact_steps = []
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for offset, (name, function) in enumerate(attack_functions.items()):
            rng = random.Random(seed * 1009 + offset)
            start = time.perf_counter()
            candidate = function(inst, rng)
            attack_elapsed[name] += time.perf_counter() - start
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])
            attack_results[name]["attempts"] += 1

        start = time.perf_counter()
        found, stats = _discriminant_scan(inst, stop_first=True)
        reference_elapsed += time.perf_counter() - start
        reference_iterations.append(stats["iterations"])
        reference_operations.append(stats["scalar_operations"])
        if found:
            reference_successes += int(verify(inst, found[0])[0])

        compact, compact_stats = _compact_pell_solver(inst)
        compact_operations.append(compact_stats["exact_operations"])
        compact_steps.append(compact_stats["recurrence_steps"])
        if compact is not None:
            compact_successes += int(verify(inst, compact)[0])

    for name, elapsed in attack_elapsed.items():
        attack_results[name]["wall_clock_sec_total_8"] = round(elapsed, 6)
    all_failed = all(row["successes"] == 0 for row in attack_results.values())
    reference = {
        "name": "exact discriminant scan over the x interval",
        "complexity": "O(W) exact iterations and O(W log^2 C) bit operations",
        "wall_clock_sec_total_8": round(reference_elapsed, 6),
        "wall_clock_sec_mean": round(reference_elapsed / len(attack_seeds), 6),
        "iterations_mean": sum(reference_iterations) // len(reference_iterations),
        "iterations_min": min(reference_iterations),
        "iterations_max": max(reference_iterations),
        "operations_mean": sum(reference_operations) // len(reference_operations),
        "operations_min": min(reference_operations),
        "operations_max": max(reference_operations),
        "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
    }
    intended_operations = max(compact_operations)
    report["G6_adversary_panel"] = {
        "pass": (all_failed and reference_successes == compact_successes
                 == len(attack_seeds)),
        "attacks": attack_results,
        "reference_algorithm": reference,
        "compact_route": {
            "name": "recover affine two-shear Pell coordinates and iterate the Pell recurrence",
            "worst_case_exact_operations": intended_operations,
            "recurrence_steps_max": max(compact_steps),
            "count_model": (
                "integer additions/products/quotients/remainders/isqrt in form "
                "recovery and box transport, five recurrence operations per "
                "level, seven inverse-coordinate operations per sign choice, "
                "and the final exact substitution"
            ),
            "solves": f"{compact_successes}/{len(attack_seeds)}, as expected",
        },
    }

    strongest = max(attack_elapsed, key=attack_elapsed.get)
    report["G5_density_and_baseline_cost"] = {
        "pass": (exact_density is not None and exact_density < 1e-6 and all_failed),
        "exact_valid_answers_at_shipping": exact_count,
        "exact_density_at_shipping": exact_density,
        "sampled_density_at_shipping": observed_density,
        "density_hits": guess_hits,
        "density_samples": guess_total,
        "candidate_space": search_space(shipping),
        "strongest_failing_attack": strongest,
        "attack_wall_clock_sec_total_8": round(attack_elapsed[strongest], 6),
        "attack_candidate_evaluations_total_8": 8192 * len(attack_seeds),
        "reference_algorithm_iterations_mean": reference["iterations_mean"],
        "reference_algorithm_operations_mean": reference["operations_mean"],
        "reference_algorithm_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
        "demo_exact_valid_answers": enumerate_all(
            make_instance(seed=3, **DIFFICULTY["demo"])
        ),
    }

    doubled_params = {"n": 2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"]}
    larger = make_instance(seed=707, **doubled_params)
    larger_ok, larger_reason = verify(larger, larger["answer"])
    report["G7_scales"] = {
        "pass": larger_ok and search_space(larger) > search_space(shipping),
        "shipping_n": shipping["n"],
        "doubled_n": larger["n"],
        "shipping_candidate_space": search_space(shipping),
        "doubled_candidate_space": search_space(larger),
        "verify_reason": larger_reason,
    }

    invariance_checks = carried_checks = 0
    key_failures = []
    transformations = [
        (False, False, False, 17, -23, 1),
        (False, True, True, -31, 29, -1),
        (True, False, True, 41, 37, 3),
        (True, True, False, -43, -47, -3),
    ]
    for seed in range(20):
        inst = make_instance(seed=9000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        for variant, transformation in enumerate(transformations):
            transformed = _relabel_instance(inst, *transformation[:5])
            scale = transformation[5]
            transformed["coefficients"] = [
                scale * value for value in transformed["coefficients"]
            ]
            invariance_checks += 1
            if canonical_key(transformed) != key:
                key_failures.append({"seed": seed, "variant": variant,
                                     "reason": "canonical key changed"})
            carried_checks += 1
            ok, reason = verify(transformed, transformed["answer"])
            if not ok:
                key_failures.append({"seed": seed, "variant": variant,
                                     "reason": "carried witness failed: " + reason})
    unrelated = [
        canonical_key(make_instance(seed=20_000 + seed,
                                    **DIFFICULTY[SHIPPING_DIFFICULTY]))
        for seed in range(20)
    ]
    distinct_keys = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "invariance_failures": key_failures,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "symmetries_tested": [
            "integer translations of both coordinate origins",
            "independent axis reflections",
            "x/y variable renaming",
            "compositions of translations, reflections, and variable renaming",
            "global equation gcd/sign normalization",
        ],
    }

    # Measure the output and compact-route caps over a broad shipping sample,
    # rather than letting one convenient representative stand in for a worst
    # case.  The seed language is unbounded, so this is explicitly a measured
    # maximum, not a proof over every possible Python integer seed.
    size_sample_seeds = 10_000
    measured_answer_sizes = []
    measured_route_operations = []
    size_sample_failures = []
    for seed in range(size_sample_seeds):
        sample = make_instance(
            seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY]
        )
        measured_answer_sizes.append(_json_answer_size(sample["answer"]))
        candidate, stats = _compact_pell_solver(sample)
        measured_route_operations.append(stats["exact_operations"])
        if candidate is None or not verify(sample, candidate)[0]:
            size_sample_failures.append(seed)
    answer_chars = max(row[0] for row in measured_answer_sizes)
    answer_tokens = max(row[1] for row in measured_answer_sizes)
    intended_operations = max(measured_route_operations)
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = (arms["hinted"]["solved"] / hinted_attempts
                   if hinted_attempts else None)
    placebo_rate = (arms["placebo"]["solved"] / placebo_attempts
                    if placebo_attempts else None)
    hint_delta = (hinted_rate - placebo_rate
                  if hinted_rate is not None and placebo_rate is not None
                  else None)
    within_caps = (answer_chars <= 2000 and len(shipping["answer"]) <= 256
                   and intended_operations <= 300 and not size_sample_failures)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hint_delta,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": len(shipping["answer"]),
        "intended_route_operations": intended_operations,
        "shipping_seeds_measured": size_sample_seeds,
        "compact_route_failures": size_sample_failures,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gate_values = [value for key, value in report.items() if key.startswith("G")]
    report["pass"] = all(gate.get("pass") is True for gate in gate_values)
    report["all_passed"] = report["pass"]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
