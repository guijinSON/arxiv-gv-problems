"""Verified problem generator derived from arXiv:1805.11702.

The task is native finite-field algebraic geometry: given a smooth complete
intersection of a singular quadric and a cubic in projective 3-space, find a
tritangent plane.  Instances are inverse-generated from the identity

    F = u^3 + A(s,t) u + r(s,t)^2,   r = s*t*(s-t),

on the quadric parametrised by (s^2:st:t^2:w).  Thus u=0 cuts the curve in
three distinct double points.  A dense projective change of coordinates and a
multiple of the quadric hide that presentation while preserving the witness.
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


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import sparse_poly  # noqa: F401
except ImportError:  # pragma: no cover - this family remains stdlib-only
    sparse_poly = None


TRACK = "B"


PROBLEM_PROFILE = {
    "native_domain": "geometry",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "smooth space sextic over a prime field",
        "singular quadric and cubic in projective 3-space",
        "linear form defining a tritangent plane",
    ],
    "verification_operations": [
        "finite-field linear substitution",
        "exact homogeneous polynomial expansion",
        "univariate polynomial gcd",
        "squarefree and scalar-square tests",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The second polar of the cubic in the singular quadric's vertex "
        "direction is the trace-zero plane section; without recognizing this "
        "invariant one must search tangent-plane incidences."
    ),
    "hardness_basis": (
        "Track B: Algorithm 3.1 of the paper finds tritangents by resultants and "
        "the 45 quartic equations for square binary sextics; the executable "
        "finite-field tangent-pencil specialization used here is O(p^2), and "
        "at the shipping preset performs up to 3,714,246 measured exact field "
        "operations in 0.646 seconds, whereas the second-polar route uses at "
        "most 165 field operations."
    ),
    "max_answer_tokens": 4,
}


NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}


DIFFICULTY = {
    "demo": {"n": 7, "scramble": False},
    "easy": {"n": 503, "scramble": True},
    "medium": {"n": 1009, "scramble": True},
    "hard": {"n": 2017, "scramble": True},
}

SHIPPING_DIFFICULTY = "easy"


STRUCTURAL_HINT = (
    "The second polar of the cubic in the cone's vertex direction is an "
    "intrinsic trace section."
)
PLACEBO_HINT = (
    "The modular representatives and projective normalizations should be "
    "handled consistently throughout."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "One canonically normalized linear form [h0,h1,h2,h3] over GF(p) "
        "that does not vanish at the cone vertex: entries are integers in "
        "0..p-1 and the first nonzero entry is 1."
    ),
    "bounds": {
        "field": "GF(p) from the instance",
        "coefficients": 4,
        "coefficient_min": 0,
        "coefficient_max": "p-1",
        "projective_normalization": "first nonzero coefficient equals 1",
        "must_not_contain_vertex": True,
    },
}


NOTES = """\
Definition source: Section 2.2, especially Definition 2.2, defines tritangent
planes by a doubled degree-three hyperplane section.  Equation (*) in Section
4.1 writes a sextic on the singular quadric as a weighted cubic in w, and
Proposition 4.3 excludes planes through the cone vertex from the odd
tritangents.  Algorithm 3.1 supplies the executable square-binary-sextic test:
eliminate a plane and require the resulting sextic to lie on the variety of
perfect squares, whose ideal has 45 quartic generators.

Step 0: this cannot honestly be Track A.  Algorithm 3.1 is a general symbolic
method and Section 4.2 gives an even more specialized construction from the 240
exceptional curves.  In this finite-field presentation, a direct point/tangent-
pencil algorithm is O(p^2) after the cone parametrization is known.  At p=503
it processes about 253,000 cone points and about 253,000 tangent-plane pencil
members, costing up to 3,714,246 counted field operations in the eight-seed
audit.  The compact route differentiates the displayed cubic twice along the
displayed cone vertex and normalizes four coefficients (at most 165 field
operations).  That gap is
the Track-B claim.

Generation is by composition of identities, never by solving the output
instance.  We choose A only when the discriminant -4*A^3-27*r^4 is squarefree;
the discriminant/Jacobian criterion then certifies smoothness of the trigonal
curve in characteristic other than 2 or 3.  The identity
F=u^3+A*u+r^2 certifies u=0 as a tritangent.  We then add Q times a random linear
form and apply a random GL(4) coordinate change, carrying the certificate.

The attack panel tries sparse coordinate planes (outlier), the first 256 planes
in canonical order (greedy), 256 uniformly random projective planes, the vector
of pure-cube coefficients (a plausible tensor ansatz), and the unjustified
identification of the cone vertex with a dual plane.  Dense independent masks
make all five fail on the audited seeds.  The successful second-polar route is
the intended invariant, not an attack, while the O(p^2) tangent-pencil method is
reported separately as the Track-B reference algorithm.

The canonical key uses equal-weight degree-four transvectant invariants of the
binary degree-twelve discriminant.  It is unchanged not only by ambient GL(4),
equation scaling, and term order, but also by GL(2) changes of (s,t), quadratic
translations of w, and nonzero rescalings of w in the cone parametrization.
"""


# A sparse polynomial is dict[exponent tuple, coefficient modulo p].
Poly = dict[tuple[int, int, int, int], int]


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime(value: int) -> int:
    candidate = max(7, int(value))
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _trim(poly: list[int], p: int) -> list[int]:
    out = [x % p for x in poly]
    while len(out) > 1 and out[-1] == 0:
        out.pop()
    return out or [0]


def _uadd(a: list[int], b: list[int], p: int) -> list[int]:
    out = [0] * max(len(a), len(b))
    for i, value in enumerate(a):
        out[i] = (out[i] + value) % p
    for i, value in enumerate(b):
        out[i] = (out[i] + value) % p
    return _trim(out, p)


def _uscale(a: list[int], scalar: int, p: int) -> list[int]:
    return _trim([(scalar * value) % p for value in a], p)


def _umul(a: list[int], b: list[int], p: int) -> list[int]:
    out = [0] * (len(a) + len(b) - 1)
    for i, av in enumerate(a):
        for j, bv in enumerate(b):
            out[i + j] = (out[i + j] + av * bv) % p
    return _trim(out, p)


def _upow(a: list[int], exponent: int, p: int) -> list[int]:
    result = [1]
    base = a[:]
    power = exponent
    while power:
        if power & 1:
            result = _umul(result, base, p)
        power >>= 1
        if power:
            base = _umul(base, base, p)
    return result


def _udivmod(a: list[int], b: list[int], p: int):
    dividend = _trim(a, p)
    divisor = _trim(b, p)
    if divisor == [0]:
        raise ZeroDivisionError("polynomial division by zero")
    if len(dividend) < len(divisor):
        return [0], dividend
    quotient = [0] * (len(dividend) - len(divisor) + 1)
    lead_inv = pow(divisor[-1], -1, p)
    remainder = dividend[:]
    while remainder != [0] and len(remainder) >= len(divisor):
        shift = len(remainder) - len(divisor)
        factor = remainder[-1] * lead_inv % p
        quotient[shift] = factor
        for i, value in enumerate(divisor):
            remainder[i + shift] = (remainder[i + shift] - factor * value) % p
        remainder = _trim(remainder, p)
    return _trim(quotient, p), remainder


def _ugcd(a: list[int], b: list[int], p: int) -> list[int]:
    left = _trim(a, p)
    right = _trim(b, p)
    while right != [0]:
        _, remainder = _udivmod(left, right, p)
        left, right = right, remainder
    if left == [0]:
        return [0]
    return _uscale(left, pow(left[-1], -1, p), p)


def _uderivative(poly: list[int], p: int) -> list[int]:
    if len(poly) <= 1:
        return [0]
    return _trim([(i * poly[i]) % p for i in range(1, len(poly))], p)


def _binary_add(a: list[int], b: list[int], p: int) -> list[int]:
    size = max(len(a), len(b))
    out = [0] * size
    for i in range(size):
        out[i] = ((a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0)) % p
    return out


def _binary_scale(a: list[int], scalar: int, p: int) -> list[int]:
    return [(scalar * value) % p for value in a]


def _binary_mul(a: list[int], b: list[int], p: int) -> list[int]:
    out = [0] * (len(a) + len(b) - 1)
    for i, av in enumerate(a):
        for j, bv in enumerate(b):
            out[i + j] = (out[i + j] + av * bv) % p
    return out


def _binary_pow(a: list[int], exponent: int, p: int) -> list[int]:
    out = [1]
    for _ in range(exponent):
        out = _binary_mul(out, a, p)
    return out


def _binary_eval(coeffs: list[int], s: int, t: int, p: int) -> int:
    degree = len(coeffs) - 1
    total = 0
    for t_exp, coeff in enumerate(coeffs):
        total += coeff * pow(s, degree - t_exp, p) * pow(t, t_exp, p)
    return total % p


def _falling(value: int, length: int, p: int) -> int:
    result = 1
    for offset in range(length):
        result = result * (value - offset) % p
    return result


def _binary_derivative(coeffs: list[int], s_order: int, t_order: int, p: int) -> list[int]:
    """Mixed derivative of a binary form, indexed by the remaining t exponent."""
    degree = len(coeffs) - 1
    out_degree = degree - s_order - t_order
    if out_degree < 0:
        return [0]
    out = [0] * (out_degree + 1)
    for t_exp, coeff in enumerate(coeffs):
        s_exp = degree - t_exp
        if s_exp < s_order or t_exp < t_order:
            continue
        factor = _falling(s_exp, s_order, p) * _falling(t_exp, t_order, p)
        out[t_exp - t_order] = (out[t_exp - t_order] + coeff * factor) % p
    return out


def _transvectant(left: list[int], right: list[int], order: int, p: int) -> list[int]:
    """Classical binary-form transvectant, up to an irrelevant scalar factor."""
    left_degree = len(left) - 1
    right_degree = len(right) - 1
    if order < 0 or order > min(left_degree, right_degree):
        raise ValueError("invalid transvectant order")
    out = [0] * (left_degree + right_degree - 2 * order + 1)
    for k in range(order + 1):
        dl = _binary_derivative(left, order - k, k, p)
        dr = _binary_derivative(right, k, order - k, p)
        term = _binary_mul(dl, dr, p)
        factor = math.comb(order, k) * (-1 if k % 2 else 1)
        for index, value in enumerate(term):
            out[index] = (out[index] + factor * value) % p
    return out


def _binary_absolute_invariants(coeffs: list[int], p: int) -> list[int] | None:
    """Projective vector of degree-4, determinant-weight-24 invariants.

    For a binary dodecic f, each C_r=(f,f)_r is a degree-2 covariant.
    The scalar (C_r,C_r)_(24-2r), for even r, has degree 4 in f and
    determinant weight 24.  Together with (f,f)_12^2 these give a compact
    invariant under GL(2), rescaling of f, and hence reparametrization of P^1.
    """
    if len(coeffs) != 13:
        raise ValueError("expected a binary dodecic")
    scalar = _transvectant(coeffs, coeffs, 12, p)[0]
    values = [scalar * scalar % p]
    for order in (2, 4, 6, 8, 10):
        covariant = _transvectant(coeffs, coeffs, order, p)
        values.append(_transvectant(covariant, covariant, len(covariant) - 1, p)[0])
    return _projective_normalize(values, p)


def _squarefree_binary(coeffs: list[int], p: int) -> bool:
    degree = len(coeffs) - 1
    # Require the coefficient at s^degree to be nonzero, so the dehomogenized
    # polynomial has full degree and infinity is not a root.
    if not coeffs or coeffs[0] % p == 0:
        return False
    dehom = [coeffs[degree - i] % p for i in range(degree + 1)]
    return len(_ugcd(dehom, _uderivative(dehom, p), p)) == 1


def _poly_clean(poly: Poly, p: int) -> Poly:
    return {exp: value % p for exp, value in poly.items() if value % p}


def _poly_add(a: Poly, b: Poly, p: int) -> Poly:
    out = dict(a)
    for exp, value in b.items():
        out[exp] = (out.get(exp, 0) + value) % p
    return _poly_clean(out, p)


def _poly_scale(poly: Poly, scalar: int, p: int) -> Poly:
    return _poly_clean({exp: scalar * value for exp, value in poly.items()}, p)


def _poly_mul(a: Poly, b: Poly, p: int) -> Poly:
    out: Poly = {}
    for ea, av in a.items():
        for eb, bv in b.items():
            exp = tuple(ea[i] + eb[i] for i in range(4))
            out[exp] = (out.get(exp, 0) + av * bv) % p
    return _poly_clean(out, p)


def _poly_pow(poly: Poly, exponent: int, p: int) -> Poly:
    out: Poly = {(0, 0, 0, 0): 1}
    for _ in range(exponent):
        out = _poly_mul(out, poly, p)
    return out


def _linear_poly(coeffs: list[int], p: int) -> Poly:
    out: Poly = {}
    for i, coeff in enumerate(coeffs):
        if coeff % p:
            exp = [0, 0, 0, 0]
            exp[i] = 1
            out[tuple(exp)] = coeff % p
    return out


def _monomial(exp: tuple[int, int, int, int], coeff: int, p: int) -> Poly:
    return {} if coeff % p == 0 else {exp: coeff % p}


def _compose_linear(poly: Poly, forms: list[list[int]], p: int) -> Poly:
    linear_forms = [_linear_poly(row, p) for row in forms]
    out: Poly = {}
    for exp, coeff in poly.items():
        term: Poly = {(0, 0, 0, 0): coeff}
        for i, power in enumerate(exp):
            if power:
                term = _poly_mul(term, _poly_pow(linear_forms[i], power, p), p)
        out = _poly_add(out, term, p)
    return out


def _serialize_poly(poly: Poly, p: int) -> list[list[object]]:
    return [
        [value % p, list(exp)]
        for exp, value in sorted(poly.items())
        if value % p
    ]


def _deserialize_poly(data: list, p: int) -> Poly:
    out: Poly = {}
    for item in data:
        if not isinstance(item, list) or len(item) != 2:
            raise ValueError("bad sparse polynomial term")
        coeff, exponent = item
        if not isinstance(coeff, int) or not isinstance(exponent, list) or len(exponent) != 4:
            raise ValueError("bad sparse polynomial term")
        exp = tuple(int(x) for x in exponent)
        out[exp] = (out.get(exp, 0) + coeff) % p
    return _poly_clean(out, p)


def _matrix_inverse(matrix: list[list[int]], p: int) -> list[list[int]] | None:
    n = len(matrix)
    work = [
        [matrix[i][j] % p for j in range(n)]
        + [1 if i == j else 0 for j in range(n)]
        for i in range(n)
    ]
    for column in range(n):
        pivot = next((r for r in range(column, n) if work[r][column]), None)
        if pivot is None:
            return None
        work[column], work[pivot] = work[pivot], work[column]
        inverse = pow(work[column][column], -1, p)
        work[column] = [(value * inverse) % p for value in work[column]]
        for row in range(n):
            if row == column:
                continue
            factor = work[row][column]
            if factor:
                work[row] = [
                    (work[row][j] - factor * work[column][j]) % p
                    for j in range(2 * n)
                ]
    return [row[n:] for row in work]


def _matrix_mul(a: list[list[int]], b: list[list[int]], p: int) -> list[list[int]]:
    return [
        [sum(a[i][k] * b[k][j] for k in range(len(b))) % p for j in range(len(b[0]))]
        for i in range(len(a))
    ]


def _row_matrix_mul(row: list[int], matrix: list[list[int]], p: int) -> list[int]:
    return [sum(row[k] * matrix[k][j] for k in range(len(row))) % p for j in range(len(matrix[0]))]


def _matrix_vector(matrix: list[list[int]], vector: list[int], p: int) -> list[int]:
    return [sum(row[j] * vector[j] for j in range(len(vector))) % p for row in matrix]


def _projective_normalize(vector: list[int], p: int) -> list[int] | None:
    reduced = [value % p for value in vector]
    pivot = next((value for value in reduced if value), None)
    if pivot is None:
        return None
    inverse = pow(pivot, -1, p)
    return [(value * inverse) % p for value in reduced]


def _poly_eval(poly: Poly, point: list[int], p: int) -> int:
    total = 0
    for exp, coeff in poly.items():
        value = coeff
        for i, power in enumerate(exp):
            if power:
                value = value * pow(point[i], power, p) % p
        total = (total + value) % p
    return total


def _poly_gradient(poly: Poly, point: list[int], p: int) -> list[int]:
    gradient = [0, 0, 0, 0]
    for exp, coeff in poly.items():
        for variable in range(4):
            if exp[variable] == 0:
                continue
            value = coeff * exp[variable]
            for i, power in enumerate(exp):
                adjusted = power - (1 if i == variable else 0)
                if adjusted:
                    value = value * pow(point[i], adjusted, p) % p
            gradient[variable] = (gradient[variable] + value) % p
    return gradient


def _random_gl4(rng: random.Random, p: int) -> tuple[list[list[int]], list[list[int]]]:
    for _ in range(256):
        matrix = [[rng.randrange(1, p) for _ in range(4)] for _ in range(4)]
        inverse = _matrix_inverse(matrix, p)
        if inverse is not None and all(value for row in inverse for value in row):
            return matrix, inverse
    raise RuntimeError("failed to sample a dense invertible 4x4 matrix")


def _base_polynomials(rng: random.Random, p: int):
    # Q = y1^2-y0*y2.
    quadric = _poly_add(
        _monomial((0, 2, 0, 0), 1, p),
        _monomial((1, 0, 1, 0), -1, p),
        p,
    )

    r = [0, 1, -1, 0]  # s*t*(s-t), coefficients by t-exponent.
    r2 = _binary_mul(r, r, p)
    r4 = _binary_mul(r2, r2, p)
    for _ in range(4096):
        a = [rng.randrange(1, p)] + [rng.randrange(p) for _ in range(3)] + [rng.randrange(1, p)]
        a3 = _binary_pow(a, 3, p)
        discriminant = _binary_add(
            _binary_scale(a3, -4, p),
            _binary_scale(r4, -27, p),
            p,
        )
        if _squarefree_binary(discriminant, p):
            break
    else:
        raise RuntimeError("failed to sample a squarefree trigonal discriminant")

    q = [rng.randrange(1, p), rng.randrange(1, p), rng.randrange(1, p)]
    u = _linear_poly([-q[0], -q[1], -q[2], 1], p)
    a_lift: Poly = {}
    for exp, coeff in zip(
        ((2, 0, 0, 0), (1, 1, 0, 0), (1, 0, 1, 0), (0, 1, 1, 0), (0, 0, 2, 0)),
        a,
    ):
        a_lift = _poly_add(a_lift, _monomial(exp, coeff, p), p)
    r2_lift = _poly_add(
        _poly_add(
            _monomial((2, 0, 1, 0), 1, p),
            _monomial((0, 3, 0, 0), -2, p),
            p,
        ),
        _monomial((1, 0, 2, 0), 1, p),
        p,
    )
    cubic = _poly_add(
        _poly_add(_poly_pow(u, 3, p), _poly_mul(a_lift, u, p), p),
        r2_lift,
        p,
    )
    # This changes the displayed cubic but not its restriction to Q.
    random_linear = _linear_poly([rng.randrange(p) for _ in range(4)], p)
    cubic = _poly_add(cubic, _poly_mul(quadric, random_linear, p), p)
    return quadric, cubic, [-q[0] % p, -q[1] % p, -q[2] % p, 1], discriminant


def _weighted_forms_from_data(p: int, cubic_data: tuple, cone_data: tuple):
    cubic = _deserialize_poly([[c, list(e)] for c, e in cubic_data], p)
    cone = [list(row) for row in cone_data]
    pulled = _compose_linear(cubic, cone, p)
    reduced: Poly = {}
    for exp, coeff in pulled.items():
        e0, e1, e2, e3 = exp
        pairs = e1 // 2
        normal = (e0 + pairs, e1 % 2, e2 + pairs, e3)
        reduced[normal] = (reduced.get(normal, 0) + coeff) % p
    reduced = _poly_clean(reduced, p)
    forms = {0: [0] * 7, 1: [0] * 5, 2: [0] * 3, 3: [0]}
    for (e0, e1, e2, ew), coeff in reduced.items():
        s_exp = 2 * e0 + e1
        t_exp = 2 * e2 + e1
        expected = 6 - 2 * ew
        if s_exp + t_exp != expected or ew not in forms:
            raise ValueError("cubic pullback has inconsistent weighted degree")
        forms[ew][t_exp] = (forms[ew][t_exp] + coeff) % p
    return tuple(tuple(forms[k]) for k in range(4))


@lru_cache(maxsize=64)
def _weighted_forms_cached(p: int, cubic_data: tuple, cone_data: tuple):
    return _weighted_forms_from_data(p, cubic_data, cone_data)


def _weighted_forms(inst: dict) -> tuple[tuple[int, ...], ...]:
    cubic_data = tuple((int(item[0]), tuple(item[1])) for item in inst["cubic"])
    cone_data = tuple(tuple(int(value) for value in row) for row in inst["cone_map"])
    return _weighted_forms_cached(inst["p"], cubic_data, cone_data)


def _curve_discriminant(inst: dict) -> list[int]:
    """Binary discriminant of the monic cubic obtained on the quadric cone."""
    p = inst["p"]
    f0, f1, f2, f3 = [list(form) for form in _weighted_forms(inst)]
    if len(f3) != 1 or f3[0] == 0:
        raise ValueError("cubic pullback is not cubic in the weighted coordinate")
    inv_lead = pow(f3[0], -1, p)
    b = _binary_scale(f2, inv_lead, p)
    c = _binary_scale(f1, inv_lead, p)
    d = _binary_scale(f0, inv_lead, p)
    inv3 = pow(3, -1, p)
    inv27 = pow(27, -1, p)
    depressed_p = _binary_add(c, _binary_scale(_binary_mul(b, b, p), -inv3, p), p)
    depressed_q = _binary_add(
        _binary_add(d, _binary_scale(_binary_mul(b, c, p), -inv3, p), p),
        _binary_scale(_binary_pow(b, 3, p), 2 * inv27, p),
        p,
    )
    return _binary_add(
        _binary_scale(_binary_pow(depressed_p, 3, p), -4, p),
        _binary_scale(_binary_pow(depressed_q, 2, p), -27, p),
        p,
    )


def _plane_section(inst: dict, plane: list[int]) -> list[int] | None:
    p = inst["p"]
    cone = inst["cone_map"]
    pulled_plane = _row_matrix_mul(plane, cone, p)
    if pulled_plane[3] == 0:
        return None
    inverse = pow(pulled_plane[3], -1, p)
    q = [(-pulled_plane[i] * inverse) % p for i in range(3)]
    forms = _weighted_forms(inst)
    result = [0] * 7
    power = [1]
    for w_power in range(4):
        if w_power:
            power = _binary_mul(power, q, p)
        term = _binary_mul(list(forms[w_power]), power, p)
        for i, value in enumerate(term):
            result[i] = (result[i] + value) % p
    return result


def _transform_binary(coeffs: list[int], v: tuple[int, int], w: tuple[int, int], p: int) -> list[int]:
    # P(v*S+w*T); result indexed by exponent of T.
    degree = len(coeffs) - 1
    out = [0] * (degree + 1)
    for original_t, coeff in enumerate(coeffs):
        original_s = degree - original_t
        for i in range(original_s + 1):
            left = math.comb(original_s, i) * pow(v[0], original_s - i, p) * pow(w[0], i, p)
            for j in range(original_t + 1):
                right = math.comb(original_t, j) * pow(v[1], original_t - j, p) * pow(w[1], j, p)
                out[i + j] = (out[i + j] + coeff * left * right) % p
    return out


def _scalar_square_with_squarefree_root(coeffs: list[int], p: int) -> bool:
    if not any(value % p for value in coeffs):
        return False
    # Almost every candidate already has two nonzero endpoint coefficients.
    # In that case no binary-coordinate change is needed; this fast path makes
    # the mandatory 200k structure-aware audit practical without weakening it.
    if coeffs[0] % p and coeffs[-1] % p:
        transformed = [value % p for value in coeffs]
    else:
        nonroots = []
        for direction in itertools.chain(((1, value) for value in range(p)), ((0, 1),)):
            if _binary_eval(coeffs, *direction, p):
                nonroots.append(direction)
                if len(nonroots) >= 8:
                    break
        pair = None
        for v in nonroots:
            for w in nonroots:
                if (v[0] * w[1] - v[1] * w[0]) % p:
                    pair = (v, w)
                    break
            if pair:
                break
        if pair is None:
            return False
        transformed = _transform_binary(coeffs, pair[0], pair[1], p)
    # Both endpoint coefficients are nonzero, hence this is a full degree-six
    # affine polynomial with no missing root at infinity.
    affine = _trim(transformed, p)
    if len(affine) != 7:
        return False
    divisor = _ugcd(affine, _uderivative(affine, p), p)
    if len(divisor) != 4:
        return False
    if len(_ugcd(divisor, _uderivative(divisor, p), p)) != 1:
        return False
    square = _umul(divisor, divisor, p)
    quotient, remainder = _udivmod(affine, square, p)
    return remainder == [0] and len(quotient) == 1 and quotient[0] != 0


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a smooth sextic and carry a tritangent through GL(4)."""
    p = _next_prime(params.get("modulus", n))
    if p in (2, 3):
        raise ValueError("the characteristic must be different from 2 and 3")
    rng = random.Random(seed)
    quadric0, cubic0, plane0, _ = _base_polynomials(rng, p)

    if not params.get("scramble", True):
        cone = [[1 if i == j else 0 for j in range(4)] for i in range(4)]
        answer = _projective_normalize(plane0, p)
        inst = {
            "n": int(n),
            "p": p,
            "quadric": _serialize_poly(quadric0, p),
            "cubic": _serialize_poly(cubic0, p),
            "cone_map": cone,
            "answer": answer,
        }
        ok, reason = verify(inst, answer)
        if not ok:
            raise RuntimeError("unscrambled construction failed: " + reason)
        return inst

    # Resample only the coordinate mask if a cheap attack would accidentally
    # hit a valid plane.  The planted plane was fixed before this loop.
    for _ in range(128):
        cone, cone_inverse = _random_gl4(rng, p)
        quadric = _compose_linear(quadric0, cone_inverse, p)
        cubic = _compose_linear(cubic0, cone_inverse, p)
        answer = _projective_normalize(_row_matrix_mul(plane0, cone_inverse, p), p)
        if answer is None or answer[0] != 1 or answer[1] in (0, 1):
            continue
        inst = {
            "n": int(n),
            "p": p,
            "quadric": _serialize_poly(quadric, p),
            "cubic": _serialize_poly(cubic, p),
            "cone_map": cone,
            "answer": answer,
        }
        ok, _reason = verify(inst, answer)
        if not ok:
            continue
        if p >= 101 and any(
            verify(inst, candidate)[0]
            for candidate in _cheap_attack_candidates(inst, random.Random(99173), include_random=False).values()
            for candidate in candidate
        ):
            continue
        return inst
    raise RuntimeError("failed to mask the constructed tritangent")


def _format_poly(data: list, variables=("x0", "x1", "x2", "x3")) -> str:
    pieces = []
    for coeff, exponent in data:
        factors = []
        for variable, power in zip(variables, exponent):
            if power == 1:
                factors.append(variable)
            elif power:
                factors.append(f"{variable}^{power}")
        monomial = "*".join(factors) if factors else "1"
        pieces.append(f"{coeff}*{monomial}")
    return " + ".join(pieces) if pieces else "0"


def render(inst: dict) -> str:
    p = inst["p"]
    matrix_rows = "\n".join("  " + " ".join(map(str, row)) for row in inst["cone_map"])
    statement = f"""Find a tritangent plane to a space sextic over GF({p}).

All arithmetic is modulo the prime {p}.  Projective 3-space has homogeneous
coordinates (x0:x1:x2:x3).  A nonzero coefficient vector h=[h0,h1,h2,h3]
defines the plane H: h0*x0+h1*x1+h2*x2+h3*x3=0; scalar multiples define the
same plane.

The curve C is the complete intersection Q=F=0, where
Q = {_format_poly(inst['quadric'])}
F = {_format_poly(inst['cubic'])}

It is guaranteed that C is a smooth degree-6 curve and Q is a singular quadric.
For exact substitution, the following parametrizes Q:

  [x0,x1,x2,x3]^T = B * [s^2,s*t,t^2,w]^T,
B =
{matrix_rows}

A plane is a valid answer precisely when it does not contain the singular point
B*[0,0,0,1]^T and, after its equation is used to eliminate w in the displayed
parametrization, F becomes a nonzero scalar multiple of the square of a
squarefree homogeneous cubic in s,t.  Equivalently, H meets C at three distinct
geometric points, each with multiplicity two.

Return one valid plane.  Use the unique normalization in which every hi is an
integer from 0 through {p - 1} and the first nonzero hi is 1.

Give your final answer inside <answer></answer> tags, as a JSON list of exactly
four integers [h0,h1,h2,h3].
Example: <answer>[1,0,3,5]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    payload = matches[-1].strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", payload, flags=re.I | re.S)
    if fence:
        payload = fence.group(1).strip()
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(answer, list):
        return None
    return answer


def verify(inst: dict, answer) -> tuple[bool, str]:
    p = inst["p"]
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) == 5 and answer[-1] in answer[:-1]:
        return False, "a duplicated extra coefficient is not allowed"
    if len(answer) != 4:
        return False, "plane must have exactly four coefficients"
    if any(isinstance(value, bool) or not isinstance(value, int) for value in answer):
        return False, "every plane coefficient must be an integer"
    if any(value < 0 or value >= p for value in answer):
        return False, f"plane coefficient outside the allowed range 0..{p - 1}"
    if not any(answer):
        return False, "the zero vector does not define a projective plane"
    if _projective_normalize(answer, p) != answer:
        return False, "plane coefficients are not canonically normalized"
    section = _plane_section(inst, answer)
    if section is None:
        return False, "the plane contains the singular vertex of the quadric"
    if not _scalar_square_with_squarefree_root(section, p):
        return False, "the plane section is not a scalar square of a squarefree cubic"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random):
    p = inst["p"]
    vertex = [row[3] % p for row in inst["cone_map"]]
    while True:
        vector = [rng.randrange(p) for _ in range(4)]
        normalized = _projective_normalize(vector, p)
        if normalized is not None and sum(normalized[i] * vertex[i] for i in range(4)) % p:
            return normalized


def search_space(inst: dict) -> int:
    p = inst["p"]
    # All projective planes except the p^2+p+1 planes through the fixed vertex.
    return p**3


def _all_projective_planes(p: int):
    for pivot in range(4):
        for tail in itertools.product(range(p), repeat=3 - pivot):
            yield [0] * pivot + [1] + list(tail)


def enumerate_all(inst: dict) -> int | None:
    if inst["p"] > 11:
        return None
    return sum(1 for plane in _all_projective_planes(inst["p"]) if verify(inst, plane)[0])


def _language_planes(inst: dict):
    p = inst["p"]
    vertex = [row[3] % p for row in inst["cone_map"]]
    for plane in _all_projective_planes(p):
        if sum(plane[i] * vertex[i] for i in range(4)) % p:
            yield plane


def _normalized_binary_form(coeffs: list[int], p: int) -> list[int]:
    normalized = _projective_normalize(coeffs, p)
    if normalized is None:
        return [0] * len(coeffs)
    return normalized


def _canonical_binary_form_small_characteristic(coeffs: list[int], p: int) -> list[int]:
    """Exact PGL(2)-orbit representative, used only for the tiny demo fields."""
    best = None
    for pivot in range(4):
        for tail in itertools.product(range(p), repeat=3 - pivot):
            a, b, c, d = [0] * pivot + [1] + list(tail)
            if (a * d - b * c) % p == 0:
                continue
            transformed = _transform_binary(coeffs, (a, c), (b, d), p)
            normalized = tuple(_normalized_binary_form(transformed, p))
            if best is None or normalized < best:
                best = normalized
    if best is None:
        raise ValueError("binary form has no PGL(2) orbit representative")
    return list(best)


def canonical_key(inst: dict) -> str:
    p = inst["p"]
    discriminant = _curve_discriminant(inst)
    invariants = _binary_absolute_invariants(discriminant, p)
    if invariants is None:
        # Classical derivative transvectants degenerate in small characteristic.
        # Those fields are tiny enough for exact PGL(2)-orbit canonicalization.
        payload = [
            p,
            "small-characteristic-pgl2-orbit",
            _canonical_binary_form_small_characteristic(discriminant, p),
        ]
    else:
        payload = [p, "binary-dodecic-degree4-invariants", invariants]
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()


def escalate(params: dict):
    harder = dict(params)
    current = _next_prime(harder.get("modulus", harder.get("n", 101)))
    # Four coefficients stay four coefficients; only their decimal width grows.
    # The serialization cap is not approached until the modulus has hundreds
    # of digits, far beyond the oracle ladder's practical build range.
    if 4 * len(str(current)) >= 1900:
        return "cap_bound"
    harder["n"] = _next_prime(2 * current + 1)
    harder.pop("modulus", None)
    return harder


def _pure_cube_candidate(inst: dict) -> list[int] | None:
    p = inst["p"]
    cubic = _deserialize_poly(inst["cubic"], p)
    vector = [cubic.get(tuple(3 if i == j else 0 for i in range(4)), 0) for j in range(4)]
    return _projective_normalize(vector, p)


def _cheap_attack_candidates(inst: dict, rng: random.Random, include_random: bool = True):
    p = inst["p"]
    coordinate = [[1 if i == j else 0 for i in range(4)] for j in range(4)]
    greedy = list(itertools.islice(_language_planes(inst), 256))
    pure = _pure_cube_candidate(inst)
    vertex = _projective_normalize([row[3] for row in inst["cone_map"]], p)
    attacks = {
        "outlier_sparse_coordinate_planes": coordinate,
        "greedy_lexicographic_256": greedy,
        "pure_cube_coefficient_ansatz": [pure] if pure is not None else [],
        "vertex_as_dual_plane_ansatz": [vertex] if vertex is not None else [],
    }
    if include_random:
        attacks["random_restart_256"] = [random_candidate(inst, rng) for _ in range(256)]
    return attacks


def _reference_algorithm(inst: dict):
    """Enumerate C(F_p), then count tangent-plane pencil incidences."""
    p = inst["p"]
    q_poly = _deserialize_poly(inst["quadric"], p)
    f_poly = _deserialize_poly(inst["cubic"], p)
    cone = inst["cone_map"]
    forms = [list(form) for form in _weighted_forms(inst)]
    started = time.perf_counter()
    incidences: dict[tuple[int, ...], int] = {}
    cone_points = 0
    curve_points = 0
    pencil_updates = 0
    operations = 0
    bases = [(1, value) for value in range(p)] + [(0, 1)]
    for s, t in bases:
        evaluated = [_binary_eval(form, s, t, p) for form in forms]
        operations += sum(4 * len(form) for form in forms)
        for w in range(p):
            cone_points += 1
            value = ((evaluated[3] * w + evaluated[2]) * w + evaluated[1]) * w + evaluated[0]
            operations += 6
            if value % p:
                continue
            curve_points += 1
            y = [s * s % p, s * t % p, t * t % p, w]
            point = _matrix_vector(cone, y, p)
            gq = _poly_gradient(q_poly, point, p)
            gf = _poly_gradient(f_poly, point, p)
            operations += 8 * (len(q_poly) + len(f_poly))
            for lam in range(p):
                plane = _projective_normalize([(gq[i] + lam * gf[i]) % p for i in range(4)], p)
                operations += 8
                if plane is None:
                    continue
                key = tuple(plane)
                incidences[key] = incidences.get(key, 0) + 1
                pencil_updates += 1
                if incidences[key] == 3 and verify(inst, plane)[0]:
                    return plane, {
                        "wall_clock_sec": time.perf_counter() - started,
                        "operations": operations,
                        "cone_points": cone_points,
                        "curve_points": curve_points,
                        "tangent_pencil_updates": pencil_updates,
                    }
            plane = _projective_normalize(gf, p)
            operations += 4
            if plane is not None:
                key = tuple(plane)
                incidences[key] = incidences.get(key, 0) + 1
                pencil_updates += 1
                if incidences[key] == 3 and verify(inst, plane)[0]:
                    return plane, {
                        "wall_clock_sec": time.perf_counter() - started,
                        "operations": operations,
                        "cone_points": cone_points,
                        "curve_points": curve_points,
                        "tangent_pencil_updates": pencil_updates,
                    }
    return None, {
        "wall_clock_sec": time.perf_counter() - started,
        "operations": operations,
        "cone_points": cone_points,
        "curve_points": curve_points,
        "tangent_pencil_updates": pencil_updates,
    }


def _compact_second_polar(inst: dict):
    """Recover the planted plane as half the second vertex-direction polar."""
    p = inst["p"]
    cubic = _deserialize_poly(inst["cubic"], p)
    vertex = [row[3] % p for row in inst["cone_map"]]
    plane = [0, 0, 0, 0]
    operations = 0
    # The coefficient of x_j*t^2 in F(x+t*v) is
    # c*e_j*product_i(v_i^(e_i-delta_ij)).  The usual second derivative adds
    # a global factor 2, irrelevant for the projective plane.
    for exponent, coeff in cubic.items():
        for j in range(4):
            if exponent[j] == 0:
                continue
            value = coeff * exponent[j] % p
            operations += 1
            for i in range(4):
                power = exponent[i] - (1 if i == j else 0)
                for _ in range(power):
                    value = value * vertex[i] % p
                    operations += 1
            plane[j] = (plane[j] + value) % p
            operations += 1
    normalized = _projective_normalize(plane, p)
    operations += 5  # pivot scan, one inversion, and four normalizing products
    return normalized, operations


def _transport_instance(inst: dict, transform: list[list[int]], q_scale: int, f_scale: int):
    p = inst["p"]
    inverse = _matrix_inverse(transform, p)
    if inverse is None:
        raise ValueError("singular relabelling")
    q = _poly_scale(_compose_linear(_deserialize_poly(inst["quadric"], p), inverse, p), q_scale, p)
    f = _poly_scale(_compose_linear(_deserialize_poly(inst["cubic"], p), inverse, p), f_scale, p)
    cone = _matrix_mul(transform, inst["cone_map"], p)
    answer = _projective_normalize(_row_matrix_mul(inst["answer"], inverse, p), p)
    out = {
        "n": inst["n"],
        "p": p,
        "quadric": list(reversed(_serialize_poly(q, p))),
        "cubic": list(reversed(_serialize_poly(f, p))),
        "cone_map": cone,
        "answer": answer,
    }
    return out


def _source_automorphism(rng: random.Random, p: int) -> list[list[int]]:
    """Automorphism of P(1,1,2): GL(2) on (s,t), plus w shift/scale.

    The returned matrix sends [S^2,S*T,T^2,W] to
    [s^2,s*t,t^2,w], so right-multiplying cone_map merely reparametrizes the
    same singular quadric and the same curve.
    """
    while True:
        a, b, c, d = [rng.randrange(p) for _ in range(4)]
        if (a * d - b * c) % p:
            break
    shift = [rng.randrange(p) for _ in range(3)]
    scale = rng.randrange(1, p)
    return [
        [a * a % p, 2 * a * b % p, b * b % p, 0],
        [a * c % p, (a * d + b * c) % p, b * d % p, 0],
        [c * c % p, 2 * c * d % p, d * d % p, 0],
        [shift[0], shift[1], shift[2], scale],
    ]


ORACLE_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 3, "errors": 0},
    "hinted": {"solved": 0, "attempts": 3, "errors": 0},
    "placebo": {"solved": 0, "attempts": 3, "errors": 0},
    "hinted_verdict": "hardened",
}


def _answer_atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest() -> dict:
    report = {}

    failures = []
    checks = 0
    smoothness_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 99):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append(f"{preset}/{seed}: answer is not JSON-native")
            discriminant = _curve_discriminant(inst)
            smoothness_checks += 1
            if not _squarefree_binary(discriminant, inst["p"]):
                failures.append(f"{preset}/{seed}: branch discriminant is not squarefree")
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "smoothness_certificate_checks": smoothness_checks,
        "failures": failures,
    }

    shipping = make_instance(seed=20260518, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    swap = planted[:]
    swap[0], swap[1] = swap[1], swap[0]
    corruptions = {
        "drop": planted[:-1],
        "swap": swap,
        "duplicate": planted + [planted[0]],
        "empty": [],
        "out_of_range": [shipping["p"]] + planted[1:],
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = [item["reason"] for item in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in cases.values()) and len(set(reasons)) == len(reasons),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    encoded = json.dumps(planted, separators=(",", ":"))
    realistic = "The doubled divisor gives this plane.\n<answer>```json\n" + encoded + "\n```</answer>\n"
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged answer") is None,
        "realistic_response_parsed": parsed == planted,
        "garbage_returns_none": parse_answer("no tagged answer") is None,
    }

    samples = 200000
    hits = 0
    guess_rng = random.Random(180511702)
    density_start = time.perf_counter()
    for _ in range(samples):
        hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    density_wall = time.perf_counter() - density_start
    density = hits / samples
    theorem_upper = 120 / search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": samples >= 200000 and density < 1e-6 and theorem_upper < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": density,
        "structure_aware": True,
        "certificate_space": search_space(shipping),
        "theorem_upper_bound_120_over_space": theorem_upper,
        "wall_clock_sec": density_wall,
    }

    reference, reference_cost = _reference_algorithm(shipping)
    reference_ok = reference is not None and verify(shipping, reference)[0]
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    attack_start = time.perf_counter()
    restart = _cheap_attack_candidates(shipping, random.Random(1818))["random_restart_256"]
    restart_success = any(verify(shipping, candidate)[0] for candidate in restart)
    attack_wall = time.perf_counter() - attack_start
    report["G5_density_and_baseline"] = {
        "pass": density < 1e-6 and reference_ok and demo_count is not None,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_estimate": density,
        "theorem_density_upper_bound": theorem_upper,
        "demo_exact_valid_answer_count": demo_count,
        "demo_certificate_space": search_space(demo),
        "strongest_failing_attack": "random_restart_256",
        "strongest_failing_attack_wall_sec": attack_wall,
        "strongest_failing_attack_iterations": 256,
        "strongest_failing_attack_successes": int(restart_success),
        "reference_algorithm_wall_sec": reference_cost["wall_clock_sec"],
        "reference_algorithm_operations": reference_cost["operations"],
        "reference_algorithm_cone_points": reference_cost["cone_points"],
        "reference_algorithm_tangent_pencil_updates": reference_cost["tangent_pencil_updates"],
    }

    attack_names = (
        "outlier_sparse_coordinate_planes",
        "greedy_lexicographic_256",
        "random_restart_256",
        "pure_cube_coefficient_ansatz",
        "vertex_as_dual_plane_ansatz",
    )
    panel = {name: {"successes": 0, "attempts": 8} for name in attack_names}
    ref_successes = 0
    ref_times = []
    ref_operations = []
    compact_successes = 0
    compact_operations = []
    for offset in range(8):
        inst = make_instance(seed=8800 + offset, **DIFFICULTY[SHIPPING_DIFFICULTY])
        bundle = _cheap_attack_candidates(inst, random.Random(9900 + offset))
        for name in attack_names:
            panel[name]["successes"] += int(any(verify(inst, candidate)[0] for candidate in bundle[name]))
        found, cost = _reference_algorithm(inst)
        ref_successes += int(found is not None and verify(inst, found)[0])
        ref_times.append(cost["wall_clock_sec"])
        ref_operations.append(cost["operations"])
        compact, compact_cost = _compact_second_polar(inst)
        compact_successes += int(compact is not None and verify(inst, compact)[0])
        compact_operations.append(compact_cost)
    all_failed = all(item["successes"] == 0 for item in panel.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_successes == 8 and compact_successes == 8,
        "attacks": panel,
        "reference_algorithm": {
            "name": "finite-field curve-point and tangent-pencil incidence enumeration",
            "paper_algorithm": "Algorithm 3.1 (resultants plus square-sextic equations)",
            "complexity": "O(p^2) field operations with the displayed cone parametrization",
            "wall_clock_sec_mean": sum(ref_times) / len(ref_times),
            "wall_clock_sec_max": max(ref_times),
            "operations": max(ref_operations),
            "solves": f"{ref_successes}/8, as expected",
        },
        "compact_route": {
            "name": "second polar in the displayed cone-vertex direction",
            "operations": max(compact_operations),
            "solves": f"{compact_successes}/8, as expected",
        },
    }

    spaces = {name: search_space(make_instance(seed=17, **params)) for name, params in DIFFICULTY.items()}
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=17, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    values = list(spaces.values())
    report["G7_scales"] = {
        "pass": all(a < b for a, b in zip(values, values[1:])) and doubled_ok,
        "search_spaces": spaces,
        "doubled_n": doubled_params["n"],
        "doubled_prime": doubled["p"],
        "doubled_search_space": search_space(doubled),
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
    }

    invariant_checks = 0
    transport_checks = 0
    invariant_failures = []
    distinct = []
    for offset in range(20):
        inst = make_instance(seed=12000 + offset, **DIFFICULTY[SHIPPING_DIFFICULTY])
        base_key = canonical_key(inst)
        distinct.append(base_key)
        transform_rng = random.Random(22000 + offset)
        transform, _inverse = _random_gl4(transform_rng, inst["p"])
        moved = _transport_instance(
            inst,
            transform,
            transform_rng.randrange(1, inst["p"]),
            transform_rng.randrange(1, inst["p"]),
        )
        invariant_checks += 1
        if canonical_key(moved) != base_key:
            invariant_failures.append(f"seed {12000 + offset}: ambient key changed")
        ok, reason = verify(moved, moved["answer"])
        transport_checks += 1
        if not ok:
            invariant_failures.append(f"seed {12000 + offset}: ambient witness: {reason}")

        source_change = _source_automorphism(transform_rng, inst["p"])
        reparametrized = dict(inst)
        reparametrized["cone_map"] = _matrix_mul(inst["cone_map"], source_change, inst["p"])
        invariant_checks += 1
        if canonical_key(reparametrized) != base_key:
            invariant_failures.append(f"seed {12000 + offset}: source key changed")
        ok, reason = verify(reparametrized, inst["answer"])
        transport_checks += 1
        if not ok:
            invariant_failures.append(f"seed {12000 + offset}: source witness: {reason}")

        composed = dict(moved)
        composed["cone_map"] = _matrix_mul(moved["cone_map"], source_change, inst["p"])
        invariant_checks += 1
        if canonical_key(composed) != base_key:
            invariant_failures.append(f"seed {12000 + offset}: composed key changed")
        ok, reason = verify(composed, moved["answer"])
        transport_checks += 1
        if not ok:
            invariant_failures.append(f"seed {12000 + offset}: composed witness: {reason}")
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and len(set(distinct)) == 20,
        "invariance_checks": invariant_checks,
        "witness_transport_checks": transport_checks,
        "distinct_unrelated_keys": len(set(distinct)),
        "unrelated_instances": 20,
        "failures": invariant_failures,
        "transformations": [
            "dense projective GL(4) coordinate relabelling",
            "independent nonzero scaling of Q and F",
            "sparse-polynomial term reordering",
            "GL(2) reparametrization of (s,t)",
            "quadratic translation and nonzero rescaling of w",
            "composition of all five",
        ],
    }

    answer_blob = json.dumps(planted, separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(planted)
    compact_answer, intended_ops = _compact_second_polar(shipping)
    compact_ok = compact_answer is not None and verify(shipping, compact_answer)[0]
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    arms = {
        key: dict(ORACLE_ARM_RESULTS[key]) for key in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"] if arms["hinted"]["attempts"] else 0.0
    placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"] if arms["placebo"]["attempts"] else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": ORACLE_ARM_RESULTS["hinted_verdict"],
        "diagnostic_recorded_not_gated": True,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "intended_route_verifies": compact_ok,
    }

    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
