"""Verified Track-B generator derived from arXiv:2107.03097.

Vukusic proves that, for N >= 3, the binary cubic

    Q_N(X,Y) = X(X-F_N Y)(X-2^N Y) - Y^3

takes the values +/-1 only at eight explicitly listed lattice points.  This
module carries Q_N and one of those points through an SL(2,Z) coordinate
change.  A public positive lattice box contains exactly that carried point.
Generation knows the point from the change of variables and never searches
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
from fractions import Fraction
from functools import lru_cache


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import rationals  # noqa: F401
except ImportError:  # pragma: no cover - exact integers suffice off-repo
    rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "number_theory",
    "object_regime": "integer_lattice",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "irreducible homogeneous binary cubic form over Z",
        "bounded rectangle in the integer lattice",
    ],
    "verification_operations": [
        "inclusive integer-bound comparison",
        "integer gcd",
        "exact binary-cubic substitution",
        "exact comparison with +1 and -1",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "A unimodular coordinate change crowds all three projective roots near "
        "one primitive rational direction; without recognizing that direction, "
        "the dependency-free exact baseline scans the bounded lattice box."
    ),
    "hardness_basis": (
        "Track B: bounded exact finite-difference scanning is O(W^2) and averages "
        "2,151,529 lattice evaluations, 8,637,629 exact operations, and about "
        "2.05 seconds on the final measured run at the shipping preset, while Vieta's root "
        "centroid followed by continued-fraction "
        "rational reconstruction uses fewer than 160 exact operations; the paper's "
        "Sections 3-4 also give effective PARI/GP and continued-fraction methods, "
        "so no Track-A claim is made."
    ),
    "max_answer_tokens": 4,
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


DIFFICULTY: dict = {
    "demo": {
        "n": 4,
        "paper_n": 4,
        "offset_scale": 1,
        "shear_scale": 1,
        "scramble": True,
    },
    "easy": {
        "n": 2_049,
        "paper_n": 220,
        "offset_scale": 8,
        "shear_scale": 4,
        "scramble": True,
    },
    "medium": {
        "n": 4_097,
        "paper_n": 260,
        "offset_scale": 12,
        "shear_scale": 6,
        "scramble": True,
    },
    "hard": {
        "n": 8_193,
        "paper_n": 300,
        "offset_scale": 16,
        "shear_scale": 8,
        "scramble": True,
    },
}

SHIPPING_DIFFICULTY: str = "easy"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON list [x,y] of exactly two coprime base-10 integers.  Each "
        "coordinate lies in its displayed inclusive interval; order matters."
    ),
    "bounds": {
        "coordinates": 2,
        "coordinate_intervals": "instance supplied and inclusive",
        "coprime": True,
        "ordered": True,
        "maximum_coordinate_decimal_digits": 998,
    },
}

STRUCTURAL_HINT: str = (
    "The three real projective roots are crowded by one unimodular coordinate "
    "change around a primitive rational direction."
)
PLACEBO_HINT: str = (
    "The four exact coefficients and both inclusive coordinate bounds reward "
    "careful integer bookkeeping throughout."
)


# Replaced after the script-owned hardening runs.  These are diagnostics; G9(c)
# (answer and intended-route caps) is the only gating part of G9.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 2, "errors": 4},
        "hinted": {"solved": 0, "attempts": 0, "errors": 4},
        "placebo": {"solved": 0, "attempts": 0, "errors": 4},
    },
    "hinted_verdict": "unreachable_after_bare_arm_exhausted_key_limit",
}


NOTES: str = r"""
Theorem 1 fixes the exact family and completely classifies it: for every
integer N>=3, Q_N(X,Y)=+/-1 has only +(or -) of (1,0), (0,1),
(F_N,1), and (2^N,1).  Lemma 6 separately proves that the |Y|<=1
solutions are exactly those trivial points.  Thus the unmodified problem
fails H immediately: (1,0) costs no search.  Section 3 says PARI/GP solves
N<=28 in a couple of minutes; Section 4 uses Baker-Davenport reduction and
continued fractions for 29<=N<=1000 (about one hour for all 972 parameters),
and Section 6 finishes the remaining range with LLL.  Those algorithms and
the explicit classification rule out Track A.

The generator therefore uses the allowed structure-preserving-transformation
route.  It chooses a primitive positive vector v, completes it to an SL(2,Z)
matrix A, and replaces the second column by w+k*v.  It publishes
Q_N(A^{-1}(x,y)) and a box containing v but none of w, F_N*v+w, 2^N*v+w or
their negatives.  Theorem 1 then proves that v is the unique valid point in
the box.  The checker does not appeal to that theorem: it checks shape,
bounds, gcd, and exact substitution only.

This is honestly Track B.  A finite-difference grid scan succeeds on every
instance and is measured separately.  The compact public-data solver uses
Vieta: -c1/(3*c0) is the mean of the three roots of
c0*t^3+c1*t^2+c2*t+c3.  The large column shear crowds those roots tightly
around v[0]/v[1], whose continued-fraction reconstruction recovers v in fewer
than 160 counted exact operations.  Box landmarks, bounded residual descent,
structure-aware random restarts, and a two-decimal by-hand centroid ansatz are
tested as failing attacks.  Sampling the planted primitive point uniformly in
the same public box removes endpoint and midpoint outliers; the 2049-by-2049
box makes 8192 unbiased restarts too sparse; the high shear creates misleading
local residual slopes; and recovering the direction needs much more than a
two-decimal centroid.  The exact compact solver is disclosed under
compact_route, not misreported as a failed attack.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 100_000
_ATTACK_SEEDS = 8
_G4_SAMPLES = 200_000
_COMPACT_STRESS_SEEDS = 10_000


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_parameters(n, paper_n, offset_scale, shear_scale, scramble):
    for name, value, lower in (
        ("n", n, 4),
        ("paper_n", paper_n, 3),
        ("offset_scale", offset_scale, 1),
        ("shear_scale", shear_scale, 1),
    ):
        if not _is_int(value) or value < lower:
            raise ValueError(f"{name} must be an integer >= {lower}")
    coordinate_upper = (offset_scale + 3) * n
    if (coordinate_upper.bit_length() > 3_315
            or len(str(coordinate_upper)) > 998):
        raise ValueError("coordinate bounds exceed the 2,000-character answer cap")
    if paper_n > 2_000:
        raise ValueError("paper_n is capped at 2000 to keep the rendered form writable")
    if not isinstance(scramble, bool):
        raise ValueError("scramble must be Boolean")


def _fib(index):
    """Exact fast doubling Fibonacci number."""
    def pair(k):
        if k == 0:
            return 0, 1
        a, b = pair(k // 2)
        c = a * ((b << 1) - a)
        d = a * a + b * b
        if k & 1:
            return d, c + d
        return c, d
    return pair(index)[0]


def _extended_gcd(a, b):
    old_r, r = a, b
    old_s, s = 1, 0
    old_t, t = 0, 1
    while r:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
        old_t, t = t, old_t - q * t
    return old_r, old_s, old_t


def _poly_mul(left, right):
    """Multiply homogeneous binary forms stored by increasing y exponent."""
    out = [0] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            out[i + j] += a * b
    return out


def _cube_linear(linear):
    return _poly_mul(_poly_mul(linear, linear), linear)


def _transform_form(fibonacci, power, matrix):
    """Coefficients of Q_N(A^-1(x,y)); matrix=(a,b,c,d), det A=1."""
    a, b, c, d = matrix
    if a * d - b * c != 1:
        raise ValueError("coordinate matrix is not in SL(2,Z)")
    old_x = [d, -b]
    old_y = [-c, a]
    x_minus_fy = [old_x[i] - fibonacci * old_y[i] for i in range(2)]
    x_minus_py = [old_x[i] - power * old_y[i] for i in range(2)]
    product = _poly_mul(_poly_mul(old_x, x_minus_fy), x_minus_py)
    y_cube = _cube_linear(old_y)
    return [u - v for u, v in zip(product, y_cube)]


def _form_value(coefficients, x, y):
    c0, c1, c2, c3 = coefficients
    return c0 * x * x * x + c1 * x * x * y + c2 * x * y * y + c3 * y * y * y


def make_instance(n, seed=0, paper_n=220, offset_scale=8,
                  shear_scale=4, scramble=True, **params):
    """Carry a theorem-listed Thue solution through a known SL(2,Z) map."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, paper_n, offset_scale, shear_scale, scramble)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    fibonacci = _fib(paper_n)
    power = 1 << paper_n

    if not scramble:
        # The demo exposes the paper's own form.  At N=4 the positive box
        # [1,4]^2 contains only (F_4,1)=(3,1).
        coefficients = [1, -(fibonacci + power), fibonacci * power, -1]
        bounds = [[1, n], [1, n]]
        answer = [fibonacci, 1]
        if not (1 <= answer[0] <= n and 1 <= answer[1] <= n):
            raise ValueError("unscrambled demo box does not contain (F_N,1)")
        matrix = (1, 0, 0, 1)
    else:
        # First select the box.  Conditional on primitivity, the planted point
        # is uniform in the box; it is not tied to a midpoint or endpoint.
        lower = rng.randint(offset_scale * n, (offset_scale + 2) * n)
        upper = lower + n - 1
        while True:
            a = rng.randint(lower, upper)
            c = rng.randint(lower, upper)
            if a != c and math.gcd(a, c) == 1:
                break

        # If a*d0-b0*c=1, every completion is (b0+k*a,d0+k*c).
        gcd_value, d0, bezout_c = _extended_gcd(a, c)
        if gcd_value != 1:
            raise AssertionError("sampled vector unexpectedly nonprimitive")
        b0 = -bezout_c
        k_lo = shear_scale * upper
        k = rng.randint(k_lo, k_lo + 2 * upper)
        b = b0 + k * a
        d = d0 + k * c
        matrix = (a, b, c, d)
        coefficients = _transform_form(fibonacci, power, matrix)
        bounds = [[lower, upper], [lower, upper]]
        answer = [a, c]

        # These are construction checks, not a search for the witness.
        if min(b, d) <= upper:
            raise AssertionError("second transported trivial solution entered the box")
        if abs(_form_value(coefficients, c, a)) == 1:
            raise AssertionError("coordinate swap accidentally produced a solution")

    if abs(_form_value(coefficients, *answer)) != 1:
        raise AssertionError("transported theorem solution failed exact substitution")
    if any(not value for value in coefficients):
        raise AssertionError("degenerate displayed coefficient")

    inst = {
        "paper": "arXiv:2107.03097",
        "paper_parameter": paper_n,
        "coefficients": coefficients,
        "bounds": bounds,
        "answer": answer,
    }
    return inst


def _signed_term(coefficient, monomial, first=False):
    if coefficient == 0:
        return ""
    magnitude = abs(coefficient)
    body = monomial if magnitude == 1 else f"{magnitude}*{monomial}"
    if not monomial:
        body = str(magnitude)
    if first:
        return ("-" if coefficient < 0 else "") + body
    return (" - " if coefficient < 0 else " + ") + body


def _format_form(coefficients):
    monomials = ("x^3", "x^2*y", "x*y^2", "y^3")
    pieces = []
    for coefficient, monomial in zip(coefficients, monomials):
        if coefficient:
            pieces.append(_signed_term(coefficient, monomial, not pieces))
    return "".join(pieces) if pieces else "0"


def render(inst):
    """Render a complete, exact bounded Thue-equation problem."""
    (x_lo, x_hi), (y_lo, y_hi) = inst["bounds"]
    statement = f"""Find one primitive integer solution of this bounded binary cubic equation.

A primitive integer solution is an ordered pair (x,y) of ordinary base-10 integers with gcd(|x|,|y|)=1.  It must satisfy the displayed equation exactly; either right-hand sign is allowed.  Multiplication is written with *, and powers have their usual integer meaning.

Equation:
  {_format_form(inst['coefficients'])} = +1 or -1

Inclusive coordinate bounds:
  {x_lo} <= x <= {x_hi}
  {y_lo} <= y <= {y_hi}

Both endpoints are included.  The order matters: the first coordinate is x and the second is y.  No floating-point approximation is accepted.

Give your final answer inside <answer></answer> tags as a JSON list of exactly two base-10 integers [x,y].
Example: <answer>[3,-17]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Extract the last tagged two-integer JSON answer; return None on garbage."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    payload = matches[-1].strip()
    fence = re.fullmatch(r"```(?:json|text)?\s*(.*?)\s*```", payload,
                         flags=re.I | re.S)
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


def verify(inst, answer):
    """Check only the public bounds and exact cubic identity."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) == 1:
        return False, "answer has one coordinate; exactly two are required"
    if len(answer) != 2:
        return False, f"answer has {len(answer)} coordinates; exactly two are required"
    if not all(_is_int(value) for value in answer):
        return False, "both coordinates must be base-10 integers"
    x, y = answer
    (x_lo, x_hi), (y_lo, y_hi) = inst["bounds"]
    if not x_lo <= x <= x_hi:
        return False, f"x={x} is outside the inclusive interval [{x_lo},{x_hi}]"
    if not y_lo <= y <= y_hi:
        return False, f"y={y} is outside the inclusive interval [{y_lo},{y_hi}]"
    divisor = math.gcd(abs(x), abs(y))
    if divisor != 1:
        return False, f"coordinates are not primitive: gcd(|x|,|y|)={divisor}"
    value = _form_value(inst["coefficients"], x, y)
    if value not in (-1, 1):
        return False, f"exact substitution gives {value}, not +1 or -1"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from the stated primitive lattice points."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    (x_lo, x_hi), (y_lo, y_hi) = inst["bounds"]
    while True:
        candidate = [rng.randint(x_lo, x_hi), rng.randint(y_lo, y_hi)]
        if math.gcd(abs(candidate[0]), abs(candidate[1])) == 1:
            return candidate


@lru_cache(maxsize=64)
def _mobius_up_to(limit):
    mu = [0] * (limit + 1)
    composite = [False] * (limit + 1)
    primes = []
    if limit >= 1:
        mu[1] = 1
    for value in range(2, limit + 1):
        if not composite[value]:
            primes.append(value)
            mu[value] = -1
        for prime in primes:
            product = value * prime
            if product > limit:
                break
            composite[product] = True
            if value % prime == 0:
                mu[product] = 0
                break
            mu[product] = -mu[value]
    return tuple(mu)


def _coprime_rectangle_count(bounds):
    (x_lo, x_hi), (y_lo, y_hi) = bounds
    if min(x_lo, y_lo) <= 0:
        raise ValueError("candidate counting expects positive generated bounds")
    limit = min(x_hi, y_hi)
    mu = _mobius_up_to(limit)
    total = 0
    for divisor in range(1, limit + 1):
        if mu[divisor]:
            count_x = x_hi // divisor - (x_lo - 1) // divisor
            count_y = y_hi // divisor - (y_lo - 1) // divisor
            total += mu[divisor] * count_x * count_y
    return total


def search_space(inst):
    """Exact number of primitive ordered pairs in the displayed rectangle."""
    return _coprime_rectangle_count(tuple(tuple(row) for row in inst["bounds"]))


def _grid_scan(inst, stop_first=True):
    """Exact O(W^2) reference scan using cubic forward differences in y."""
    (x_lo, x_hi), (y_lo, y_hi) = inst["bounds"]
    c0, c1, c2, c3 = inst["coefficients"]
    solutions = []
    evaluations = operations = x_rows = 0
    for x in range(x_lo, x_hi + 1):
        x_rows += 1
        x2 = x * x
        x3 = x2 * x
        cubic = c3
        quadratic = c2 * x
        linear = c1 * x2
        constant = c0 * x3
        y = y_lo
        y2 = y * y
        y3 = y2 * y
        value = cubic * y3 + quadratic * y2 + linear * y + constant
        delta1 = (cubic * (3 * y2 + 3 * y + 1)
                  + quadratic * (2 * y + 1) + linear)
        delta2 = cubic * (6 * y + 6) + 2 * quadratic
        delta3 = 6 * cubic
        operations += 30
        while y <= y_hi:
            evaluations += 1
            operations += 1
            if value in (-1, 1):
                candidate = [x, y]
                if verify(inst, candidate)[0]:
                    solutions.append(candidate)
                    if stop_first:
                        return solutions, {
                            "lattice_evaluations": evaluations,
                            "exact_operations": operations,
                            "x_rows": x_rows,
                        }
            value += delta1
            delta1 += delta2
            delta2 += delta3
            operations += 3
            y += 1
    return solutions, {
        "lattice_evaluations": evaluations,
        "exact_operations": operations,
        "x_rows": x_rows,
    }


def enumerate_all(inst):
    """Brute-force exact valid-answer count for small rectangles only."""
    (x_lo, x_hi), (y_lo, y_hi) = inst["bounds"]
    area = (x_hi - x_lo + 1) * (y_hi - y_lo + 1)
    if area > _ENUMERATION_CAP:
        return None
    solutions, _ = _grid_scan(inst, stop_first=False)
    return len(solutions)


def _limit_denominator_counted(value, max_denominator):
    """Fraction.limit_denominator with an explicit arithmetic-operation count."""
    if value.denominator <= max_denominator:
        return value, 1, 0
    numerator, denominator = value.numerator, value.denominator
    p0, q0, p1, q1 = 0, 1, 1, 0
    operations = 0
    steps = 0
    while True:
        steps += 1
        quotient = numerator // denominator
        q2 = q0 + quotient * q1
        operations += 3
        if q2 > max_denominator:
            break
        p0, q0, p1, q1 = p1, q1, p0 + quotient * p1, q2
        numerator, denominator = denominator, numerator - quotient * denominator
        operations += 4
    k = (max_denominator - q0) // q1
    bound1 = Fraction(p0 + k * p1, q0 + k * q1)
    bound2 = Fraction(p1, q1)
    operations += 7
    if abs(bound2 - value) <= abs(bound1 - value):
        return bound2, operations + 5, steps
    return bound1, operations + 5, steps


def _compact_centroid_solver(inst):
    """Recover the crowded primitive root direction from public coefficients."""
    c0, c1, _, _ = inst["coefficients"]
    if c0 == 0:
        return None, {"exact_operations": 1, "continued_fraction_steps": 0}
    mean_root = Fraction(-c1, 3 * c0)
    max_denominator = max(abs(endpoint) for row in inst["bounds"] for endpoint in row)
    reconstructed, operations, steps = _limit_denominator_counted(
        mean_root, max_denominator
    )
    candidate = [reconstructed.numerator, reconstructed.denominator]
    # Conservatively count centroid setup, endpoint comparisons, candidate
    # extraction, bounds/gcd checks, and the final cubic substitution too.
    operations += 24
    if verify(inst, candidate)[0]:
        return candidate, {
            "exact_operations": operations,
            "continued_fraction_steps": steps,
        }
    return None, {
        "exact_operations": operations,
        "continued_fraction_steps": steps,
    }


def _primitive_near(inst, x, y):
    (x_lo, x_hi), (y_lo, y_hi) = inst["bounds"]
    x = min(x_hi, max(x_lo, x))
    y = min(y_hi, max(y_lo, y))
    for radius in range(0, 64):
        offsets = ((radius, 0), (-radius, 0), (0, radius), (0, -radius))
        for dx, dy in offsets:
            xx, yy = x + dx, y + dy
            if (x_lo <= xx <= x_hi and y_lo <= yy <= y_hi
                    and math.gcd(abs(xx), abs(yy)) == 1):
                return [xx, yy]
    return random_candidate(inst, random.Random(x * 1000003 + y))


def _attack_box_landmarks(inst):
    """Outlier probe: choose the lowest residual among nine box landmarks."""
    (x_lo, x_hi), (y_lo, y_hi) = inst["bounds"]
    xs = (x_lo, (x_lo + x_hi) // 2, x_hi)
    ys = (y_lo, (y_lo + y_hi) // 2, y_hi)
    candidates = {
        tuple(_primitive_near(inst, x, y)) for x in xs for y in ys
    }
    return list(min(candidates, key=lambda z: abs(abs(
        _form_value(inst["coefficients"], z[0], z[1])) - 1)))


def _attack_residual_descent(inst):
    """Greedy in-context coordinate descent from the box centre."""
    (x_lo, x_hi), (y_lo, y_hi) = inst["bounds"]
    current = _primitive_near(inst, (x_lo + x_hi) // 2, (y_lo + y_hi) // 2)
    for _ in range(48):
        options = [current]
        x, y = current
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                       (1, 1), (1, -1), (-1, 1), (-1, -1)):
            xx, yy = x + dx, y + dy
            if (x_lo <= xx <= x_hi and y_lo <= yy <= y_hi
                    and math.gcd(abs(xx), abs(yy)) == 1):
                options.append([xx, yy])
        best = min(options, key=lambda z: abs(abs(
            _form_value(inst["coefficients"], z[0], z[1])) - 1))
        if best == current:
            break
        current = best
    return current


def _attack_random_restart(inst, rng, restarts=8_192):
    best = None
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        score = abs(abs(_form_value(inst["coefficients"], *candidate)) - 1)
        row = (score, candidate)
        if best is None or row < best:
            best = row
        if score == 0:
            break
    return best[1]


def _attack_two_decimal_centroid(inst):
    """A by-hand ansatz using only two decimal places of Vieta's centroid."""
    c0, c1, _, _ = inst["coefficients"]
    mean_root = Fraction(-c1, 3 * c0)
    scaled = mean_root * 100
    rounded = (scaled.numerator + scaled.denominator // 2) // scaled.denominator
    coarse = Fraction(rounded, 100)
    (_, _), (y_lo, y_hi) = inst["bounds"]
    y = (y_lo + y_hi) // 2
    x_fraction = coarse * y
    x = (x_fraction.numerator + x_fraction.denominator // 2) // x_fraction.denominator
    return _primitive_near(inst, x, y)


def _sign_normalized_coefficients(coefficients):
    # A common divisor other than one would change the equation |Q|=1, so it
    # is not a relabelling symmetry.  Generated solvable forms are primitive
    # automatically; only the harmless global sign is normalized here.
    out = list(coefficients)
    first = next((value for value in out if value), 1)
    return [-value for value in out] if first < 0 else out


def _relabel_instance(inst, swap=False, flip_x=False, flip_y=False):
    """Signed coordinate renaming, carrying the witness and both intervals."""
    sx = -1 if flip_x else 1
    sy = -1 if flip_y else 1
    coefficients = inst["coefficients"]
    transformed = [0] * 4
    if not swap:
        for index, coefficient in enumerate(coefficients):
            transformed[index] = coefficient * sx ** (3 - index) * sy ** index
        x_bounds = sorted(sx * endpoint for endpoint in inst["bounds"][0])
        y_bounds = sorted(sy * endpoint for endpoint in inst["bounds"][1])
        answer = [sx * inst["answer"][0], sy * inst["answer"][1]]
    else:
        for index, coefficient in enumerate(coefficients):
            transformed[3 - index] = (
                coefficient * sy ** (3 - index) * sx ** index
            )
        x_bounds = sorted(sx * endpoint for endpoint in inst["bounds"][1])
        y_bounds = sorted(sy * endpoint for endpoint in inst["bounds"][0])
        answer = [sx * inst["answer"][1], sy * inst["answer"][0]]
    out = dict(inst)
    out["coefficients"] = transformed
    out["bounds"] = [x_bounds, y_bounds]
    out["answer"] = answer
    return out


def canonical_key(inst):
    """Orbit key under x/y renaming, axis signs, and global form sign."""
    forms = []
    for swap in (False, True):
        for flip_x in (False, True):
            for flip_y in (False, True):
                relabelled = _relabel_instance(inst, swap, flip_x, flip_y)
                forms.append(json.dumps([
                    relabelled["bounds"],
                    _sign_normalized_coefficients(relabelled["coefficients"]),
                ], separators=(",", ":")))
    return hashlib.sha256(min(forms).encode("ascii")).hexdigest()


def escalate(params):
    """Grow the box and coefficient separation while keeping a two-atom answer."""
    expected = {"n", "paper_n", "offset_scale", "shear_scale", "scramble"}
    if not isinstance(params, dict) or set(params) != expected:
        return None
    if not params["scramble"]:
        return dict(DIFFICULTY["easy"])
    harder = {
        "n": 2 * params["n"] - 1,
        "paper_n": min(params["paper_n"] + 40, 2_000),
        "offset_scale": params["offset_scale"] + 4,
        "shear_scale": params["shear_scale"] + 2,
        "scramble": True,
    }
    coordinate_upper = (harder["offset_scale"] + 3) * harder["n"]
    if (coordinate_upper.bit_length() > 3_315
            or len(str(coordinate_upper)) > 998):
        return "cap_bound"
    return harder


def _answer_size(answer):
    encoded = json.dumps(answer, separators=(",", ":"))
    return len(encoded), (len(encoded) + 3) // 4


def selftest():
    report = {
        "paper": "arXiv:2107.03097",
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

    shipping = make_instance(seed=210703097, **DIFFICULTY[SHIPPING_DIFFICULTY])
    x, y = shipping["answer"]
    corruptions = {
        "drop_one": [x],
        "swap_coordinates": [y, x],
        "duplicate_one": [x, x],
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
        "The primitive pair gives exact value +1.\n<answer>\n```json\n"
        + json.dumps(shipping["answer"], separators=(",", ":"))
        + "\n```\n</answer>\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and parse_answer("garbage") is None,
        "parsed": parsed,
    }

    guess_rng = random.Random(0x210703097)
    guess_hits = 0
    started = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        guess_hits += int(verify(
            shipping, random_candidate(shipping, guess_rng)
        )[0])
    guess_elapsed = time.perf_counter() - started
    observed_probability = guess_hits / _G4_SAMPLES
    candidate_space = search_space(shipping)
    theorem_density = 1 / candidate_space
    report["G4_guess_resistance"] = {
        "pass": observed_probability < 1e-6 and theorem_density < 1e-6,
        "hits": guess_hits,
        "total": _G4_SAMPLES,
        "observed_probability": observed_probability,
        "structure_aware_space": candidate_space,
        "sampling_rule": "uniform over primitive pairs in the displayed box",
        "theorem_certified_unique_answer_density": theorem_density,
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attack_functions = {
        "box_landmark_outlier": lambda inst, rng: _attack_box_landmarks(inst),
        "local_residual_greedy_48": lambda inst, rng: _attack_residual_descent(inst),
        "random_restart_8192": lambda inst, rng: _attack_random_restart(inst, rng),
        "two_decimal_centroid_ansatz": (
            lambda inst, rng: _attack_two_decimal_centroid(inst)
        ),
    }
    attack_results = {name: {"successes": 0, "attempts": 0}
                      for name in attack_functions}
    attack_elapsed = {name: 0 for name in attack_functions}
    reference_successes = compact_successes = 0
    reference_elapsed = 0
    reference_evaluations = []
    reference_operations = []
    compact_operations = []
    compact_steps = []
    for seed in range(8100, 8100 + _ATTACK_SEEDS):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for offset, (name, function) in enumerate(attack_functions.items()):
            rng = random.Random(seed * 1009 + offset)
            start = time.perf_counter()
            candidate = function(inst, rng)
            attack_elapsed[name] += time.perf_counter() - start
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])
            attack_results[name]["attempts"] += 1

        start = time.perf_counter()
        found, stats = _grid_scan(inst, stop_first=True)
        reference_elapsed += time.perf_counter() - start
        reference_evaluations.append(stats["lattice_evaluations"])
        reference_operations.append(stats["exact_operations"])
        if found:
            reference_successes += int(verify(inst, found[0])[0])

        compact, compact_stats = _compact_centroid_solver(inst)
        compact_operations.append(compact_stats["exact_operations"])
        compact_steps.append(compact_stats["continued_fraction_steps"])
        if compact is not None:
            compact_successes += int(verify(inst, compact)[0])

    # G9(c) asks for a measured worst case, not merely the eight adversary
    # seeds.  Stress the compact route over a much broader deterministic sample.
    compact_stress_successes = 0
    for seed in range(_COMPACT_STRESS_SEEDS):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        compact, compact_stats = _compact_centroid_solver(inst)
        compact_operations.append(compact_stats["exact_operations"])
        compact_steps.append(compact_stats["continued_fraction_steps"])
        if compact is not None:
            compact_stress_successes += int(verify(inst, compact)[0])

    for name, elapsed in attack_elapsed.items():
        attack_results[name]["wall_clock_sec_total_8"] = round(elapsed, 6)
    all_failed = all(row["successes"] == 0 for row in attack_results.values())
    reference = {
        "name": "complete bounded exact finite-difference lattice scan",
        "complexity": "O(W^2) exact additions for a W-by-W box",
        "wall_clock_sec_total_8": round(reference_elapsed, 6),
        "wall_clock_sec_mean": round(reference_elapsed / _ATTACK_SEEDS, 6),
        "lattice_evaluations_mean": sum(reference_evaluations) // _ATTACK_SEEDS,
        "lattice_evaluations_min": min(reference_evaluations),
        "lattice_evaluations_max": max(reference_evaluations),
        "operations_mean": sum(reference_operations) // _ATTACK_SEEDS,
        "operations_min": min(reference_operations),
        "operations_max": max(reference_operations),
        "solves": f"{reference_successes}/{_ATTACK_SEEDS}, as expected",
        "scope": "complete reference algorithm for the emitted bounded problem",
        "paper_domain_standard_context": (
            "Sections 3-4 use PARI/GP Thue solving and Baker-Davenport/"
            "continued-fraction reduction; Section 6 uses LLL.  Those external "
            "systems are not dependencies of this module and were not rerun."
        ),
    }
    intended_operations = max(compact_operations)
    report["G6_adversary_panel"] = {
        "pass": (all_failed and reference_successes == compact_successes
                 == _ATTACK_SEEDS
                 and compact_stress_successes == _COMPACT_STRESS_SEEDS),
        "attacks": attack_results,
        "reference_algorithm": reference,
        "compact_route": {
            "name": "Vieta root centroid plus continued-fraction reconstruction",
            "complexity": "O(log C) exact Euclidean divisions for coefficient height C",
            "worst_case_exact_operations": intended_operations,
            "continued_fraction_steps_max": max(compact_steps),
            "count_model": (
                "integer division/multiplication/addition in continued fractions, "
                "plus conservative fixed charges for rational setup, endpoint "
                "comparisons, gcd, bounds, and exact cubic verification"
            ),
            "solves": f"{compact_successes}/{_ATTACK_SEEDS}, as expected",
            "distribution_stress_solves": (
                f"{compact_stress_successes}/{_COMPACT_STRESS_SEEDS}"
            ),
        },
    }

    strongest = max(attack_elapsed, key=attack_elapsed.get)
    report["G5_density_and_baseline_cost"] = {
        "pass": theorem_density < 1e-6 and all_failed,
        "exact_valid_answers_at_shipping_by_Theorem_1": 1,
        "exact_density_at_shipping_by_Theorem_1": theorem_density,
        "sampled_density_at_shipping": observed_probability,
        "density_hits": guess_hits,
        "density_samples": _G4_SAMPLES,
        "candidate_space": candidate_space,
        "strongest_failing_attack": strongest,
        "attack_wall_clock_sec_total_8": round(attack_elapsed[strongest], 6),
        "attack_candidate_evaluations_total_8": 8_192 * _ATTACK_SEEDS,
        "reference_algorithm_lattice_evaluations_mean": (
            reference["lattice_evaluations_mean"]
        ),
        "reference_algorithm_operations_mean": reference["operations_mean"],
        "reference_algorithm_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
        "demo_exact_valid_answers": enumerate_all(
            make_instance(seed=3, **DIFFICULTY["demo"])
        ),
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled_params["paper_n"] += 20
    larger = make_instance(seed=707, **doubled_params)
    larger_ok, larger_reason = verify(larger, larger["answer"])
    report["G7_scales"] = {
        "pass": larger_ok and search_space(larger) > candidate_space,
        "shipping_n": DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        "doubled_n": doubled_params["n"],
        "shipping_candidate_space": candidate_space,
        "doubled_candidate_space": search_space(larger),
        "verify_reason": larger_reason,
    }

    invariance_checks = carried_checks = 0
    key_failures = []
    # The full presentation-symmetry group: optional x/y exchange, independent
    # signs on both coordinates, and optional global negation of the form.
    # These 16 cases include every composition of the generators named above.
    transformations = [
        (swap, flip_x, flip_y, negate)
        for swap in (False, True)
        for flip_x in (False, True)
        for flip_y in (False, True)
        for negate in (False, True)
    ]
    for seed in range(20):
        inst = make_instance(seed=9000 + seed,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        for variant, transformation in enumerate(transformations):
            swap, flip_x, flip_y, negate = transformation
            transformed = _relabel_instance(inst, swap, flip_x, flip_y)
            if negate:
                transformed["coefficients"] = [
                    -value for value in transformed["coefficients"]
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
            "x/y variable renaming",
            "independent coordinate sign changes",
            "compositions of renaming and sign changes",
            "global cubic coefficient sign normalization",
        ],
    }

    answer_chars, answer_tokens = _answer_size(shipping["answer"])
    arms = {name: dict(G9_RESULTS["arms"][name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (answer_chars <= 2_000 and len(shipping["answer"]) <= 256
                   and intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": len(shipping["answer"]),
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["pass"] = all(gate.get("pass") is True for gate in gates)
    report["all_passed"] = report["pass"]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
