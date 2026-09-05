"""Verified factor-certificate generator for arXiv:1307.1833.

Hein's Theorem III.4.2 identifies the real points of a special osculating
Schubert instance with real monic factorizations f'(t)=A(t)B(t).  This module
stays in that paper-licensed polynomial model.  It samples the factors first
through the identity

    X^4 + (2-c^2)X^2Y^2 + Y^4
      = (X^2-cXY+Y^2)(X^2+cXY+Y^2),

then integrates exactly to obtain the osculation-divisor polynomial f.  A
witness is one monic factor in an exact residue-block polynomial encoding.
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
import statistics
import sys
import time
from fractions import Fraction


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:  # Optional helpers; this module deliberately remains stdlib-only.
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - graceful standalone fallback
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "real osculation-divisor polynomial f(t) over Q",
        "monic real factor of the derivative f'(t) in residue-block form",
        "paper-licensed polynomial model of the special osculating Schubert problem (omega, box^(N-1))",
    ],
    "verification_operations": [
        "exact rational differentiation",
        "exact integer polynomial division",
        "exact coefficient comparison",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section III.4, Theorem III.4.2: real points of the special "
        "osculating Schubert instance are exactly monic real factorizations "
        "f'(t)=A(t)B(t) of the prescribed degrees"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Three exponent-residue blocks of the derivative are two fourth "
        "powers and a scaled product square, exposing a hidden difference "
        "of squares in quadratic forms."
    ),
    "hardness_basis": (
        "Track B: exact Q[t] factorization is polynomial-time via LLL; the "
        "measured Berlekamp factorization over F_97 plus centered lifting, "
        "O(D^3+2^r D^2), took a median 11,049,990 field operations and "
        "about 0.7 s at shipping derivative degree 144 over eight seeds, while "
        "recognizing the hidden three-block quadratic-form identity leaves "
        "a 241-operation compact route."
    ),
    "max_answer_tokens": 26,
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

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "One monic integer polynomial factor in three residue blocks: a JSON "
        "object {stride:m, blocks:[C0,C1,C2]} represents "
        "sum(C_r[j]*t^(m*j+r)). Blocks have instance-fixed lengths, every "
        "coefficient has absolute value at most H, C0 has nonzero constant "
        "coefficient and leading coefficient 1, and zero coefficients are "
        "written explicitly."
    ),
    "bounds": {
        "degree": "instance field factor_degree",
        "stride": "instance field residue_stride",
        "block_lengths": "instance field block_lengths",
        "coefficient_height": "instance field component_bound",
        "leading_coefficient": 1,
        "constant_term_required": True,
        "residues": [0, 1, 2],
    },
}

DIFFICULTY: dict = {
    "easy": {
        "n": 72,
        "residue_modulus": 9,
        "compressed_degree": 4,
        "coeff_bound": 2,
        "identity_scale_max": 3,
    },
}

SHIPPING_DIFFICULTY: str = "easy"

STRUCTURAL_HINT: str = (
    "The derivative's three residue blocks are two fourth powers and a scaled product square forming a difference of quadratic-form squares."
)
PLACEBO_HINT: str = (
    "The polynomial's several coefficient blocks reward careful attention to signs, degrees, exact arithmetic, and consistent block indexing."
)

# Patched from the three script-owned runs after hardening.  These are
# diagnostics; only the answer/operation caps determine G9's pass value.
G9_EVIDENCE = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "unavailable_http_403_key_limit",
}

NOTES: str = r"""
Section II.3 fixes a Schubert variety by the incidence inequalities
dim(H intersect F_{alpha_i}) >= i, and Section II.6 fixes osculating flags by
successive derivatives of a rational normal curve.  Section III.4 then fixes
the family used here: omega=(2,...,k,N), one omega condition at infinity, and
N-1 hypersurface conditions at the roots of a squarefree real polynomial f.
Theorem III.4.2 is the decisive statement: its real Schubert points are in
bijection with monic real factorizations f'=AB of degrees N-k-1 and k-1.

The same theorem is also the STEP-0 warning.  In this licensed coordinate
family a witness is produced by exact univariate factorization, not by a hard
general Schubert solver.  Exact Q[t] factorization has polynomial-time LLL
algorithms, while this module's measured executable reference is the classical
Berlekamp modular factorization and degree-balanced lift.  The family is
therefore Track B, never Track A.

Generation composes identities and never solves its output.  It samples dense
small-coefficient polynomials q,r and c, sets X=q(t^m), Y=t*r(t^m), plants the
two factors X^2-cXY+Y^2 and X^2+cXY+Y^2, forms their product, and integrates.
Modular gcd tests only certify that f has distinct roots and that the reference
prime is good; they do not discover the stored factor.  Raising m grows the
ambient degree and generic factorization cost while the three answer-block
lengths stay fixed.

The magnitude attack projects large derivative coefficients into answer
blocks.  The greedy residue attack mistakes the fourth-power blocks themselves
for factor blocks.  Random restarts sample the exact declared block language.
The symmetric/alternating ansatz tests an obvious by-hand quadratic-form guess.
All four are checked over eight shipping seeds.  The successful compact audit,
reported separately, identifies the three residue convolutions, takes exact
fourth roots, and assembles one quadratic-form factor; it is the intended
insight, not a failed adversary.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_GUESS_SAMPLES = 200_000
_SELFTEST_SEEDS = tuple(range(8))


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _trim(poly):
    out = list(poly)
    while len(out) > 1 and out[-1] == 0:
        out.pop()
    return out or [0]


def _sparse_to_dense(terms, degree=None):
    if not terms:
        return [0] if degree is None else [0] * (degree + 1)
    top = max(term[1] for term in terms) if degree is None else degree
    out = [0] * (top + 1)
    for coefficient, exponent in terms:
        out[exponent] += coefficient
    return _trim(out) if degree is None else out


def _dense_to_sparse(poly):
    return [[coefficient, exponent] for exponent, coefficient in
            reversed(list(enumerate(poly))) if coefficient]


def _answer_to_json(terms):
    """Encode internal integer [coefficient,exponent] terms canonically."""

    return [[[coefficient, 1], [exponent]] for coefficient, exponent in terms]


def _block_answer_to_dense(answer, degree):
    """Expand {stride, blocks} into an integer coefficient vector."""

    stride = answer["stride"]
    dense = [0] * (degree + 1)
    for residue, block in enumerate(answer["blocks"]):
        for index, coefficient in enumerate(block):
            exponent = stride * index + residue
            if exponent <= degree:
                dense[exponent] = coefficient
    return _trim(dense)


def _dense_to_block_answer(inst, dense):
    """Compress a factor if it uses exactly residues 0, 1, 2."""

    stride = inst["residue_stride"]
    blocks = [[0] * length for length in inst["block_lengths"]]
    for exponent, coefficient in enumerate(_trim(dense)):
        if not coefficient:
            continue
        residue = exponent % stride
        if residue > 2:
            return None
        index = (exponent - residue) // stride
        if index >= len(blocks[residue]):
            return None
        blocks[residue][index] = coefficient
    return {"stride": stride, "blocks": blocks}


def _dense_mul(left, right):
    out = [0] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        if not a:
            continue
        for j, b in enumerate(right):
            if b:
                out[i + j] += a * b
    return _trim(out)


def _dense_divmod_monic(dividend, divisor):
    """Exact integer long division by a monic integer polynomial."""

    dividend = _trim(dividend)
    divisor = _trim(divisor)
    if divisor == [0] or divisor[-1] != 1:
        return None, dividend
    if len(dividend) < len(divisor):
        return [0], dividend
    work = list(dividend)
    quotient = [0] * (len(dividend) - len(divisor) + 1)
    ddegree = len(divisor) - 1
    for shift in range(len(quotient) - 1, -1, -1):
        coefficient = work[ddegree + shift]
        quotient[shift] = coefficient
        if coefficient:
            for j, value in enumerate(divisor):
                work[j + shift] -= coefficient * value
    return _trim(quotient), _trim(work)


def _mod_trim(poly, prime):
    return _trim([int(value) % prime for value in poly])


def _mod_divmod(dividend, divisor, prime, stats=None):
    work = _mod_trim(dividend, prime)
    divisor = _mod_trim(divisor, prime)
    if divisor == [0]:
        raise ZeroDivisionError("polynomial division by zero")
    if len(work) < len(divisor):
        return [0], work
    quotient = [0] * (len(work) - len(divisor) + 1)
    inverse = pow(divisor[-1], -1, prime)
    while work != [0] and len(work) >= len(divisor):
        shift = len(work) - len(divisor)
        coefficient = work[-1] * inverse % prime
        quotient[shift] = coefficient
        for j, value in enumerate(divisor):
            work[j + shift] = (work[j + shift] - coefficient * value) % prime
            if stats is not None:
                stats["field_operations"] += 2
        work = _trim(work)
    return _mod_trim(quotient, prime), _mod_trim(work, prime)


def _mod_gcd(left, right, prime, stats=None):
    left, right = _mod_trim(left, prime), _mod_trim(right, prime)
    while right != [0]:
        _, remainder = _mod_divmod(left, right, prime, stats)
        left, right = right, remainder
        if stats is not None:
            stats["gcd_steps"] += 1
    if left == [0]:
        return [0]
    inverse = pow(left[-1], -1, prime)
    if stats is not None:
        stats["field_operations"] += len(left)
    return _mod_trim([value * inverse for value in left], prime)


def _mod_mul(left, right, modulus_poly, prime, stats=None):
    product = [0] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        if not a:
            continue
        for j, b in enumerate(right):
            if b:
                product[i + j] = (product[i + j] + a * b) % prime
                if stats is not None:
                    stats["field_operations"] += 2
    _, remainder = _mod_divmod(product, modulus_poly, prime, stats)
    return remainder


def _mod_pow(base, exponent, modulus_poly, prime, stats=None):
    result = [1]
    base = _mod_divmod(base, modulus_poly, prime, stats)[1]
    while exponent:
        if exponent & 1:
            result = _mod_mul(result, base, modulus_poly, prime, stats)
        exponent >>= 1
        if exponent:
            base = _mod_mul(base, base, modulus_poly, prime, stats)
    return result


def _nullspace_mod(matrix, prime, stats):
    if not matrix:
        return []
    rows = [list(map(lambda x: x % prime, row)) for row in matrix]
    nrows, ncols = len(rows), len(rows[0])
    pivot_columns = []
    pivot_row = 0
    for column in range(ncols):
        selected = next((r for r in range(pivot_row, nrows)
                         if rows[r][column] % prime), None)
        if selected is None:
            continue
        rows[pivot_row], rows[selected] = rows[selected], rows[pivot_row]
        inverse = pow(rows[pivot_row][column], -1, prime)
        for j in range(column, ncols):
            rows[pivot_row][j] = rows[pivot_row][j] * inverse % prime
            stats["field_operations"] += 1
        for r in range(nrows):
            if r == pivot_row or rows[r][column] == 0:
                continue
            multiplier = rows[r][column]
            for j in range(column, ncols):
                rows[r][j] = (rows[r][j] - multiplier * rows[pivot_row][j]) % prime
                stats["field_operations"] += 2
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == nrows:
            break
    free_columns = [c for c in range(ncols) if c not in set(pivot_columns)]
    basis = []
    for free in free_columns:
        vector = [0] * ncols
        vector[free] = 1
        for row_index, pivot in enumerate(pivot_columns):
            vector[pivot] = (-rows[row_index][free]) % prime
        basis.append(vector)
    return basis


def _berlekamp_basis(poly, prime, stats):
    poly = _mod_trim(poly, prime)
    degree = len(poly) - 1
    if degree <= 0:
        return []
    xpoly = [0, 1]
    x_to_p = _mod_pow(xpoly, prime, poly, prime, stats)
    columns = [[1]]
    current = [1]
    for _ in range(1, degree):
        current = _mod_mul(current, x_to_p, poly, prime, stats)
        columns.append(current)
    matrix = []
    for row in range(degree):
        values = []
        for column in range(degree):
            value = columns[column][row] if row < len(columns[column]) else 0
            if row == column:
                value -= 1
            values.append(value % prime)
        matrix.append(values)
    return _nullspace_mod(matrix, prime, stats)


def _berlekamp_factor_squarefree(poly, prime, stats):
    """Classical Berlekamp factorization of a monic squarefree polynomial."""

    poly = _mod_trim(poly, prime)
    if len(poly) <= 2:
        return [poly]
    basis = _berlekamp_basis(poly, prime, stats)
    if len(basis) <= 1:
        return [poly]
    factors = [poly]
    for vector in basis[1:]:
        for value in range(prime):
            next_factors = []
            for factor in factors:
                if len(factor) <= 2:
                    next_factors.append(factor)
                    continue
                reduced = _mod_divmod(vector, factor, prime, stats)[1]
                if not reduced:
                    reduced = [0]
                reduced = list(reduced)
                reduced[0] = (reduced[0] - value) % prime
                divisor = _mod_gcd(factor, reduced, prime, stats)
                if 1 < len(divisor) < len(factor):
                    quotient, remainder = _mod_divmod(factor, divisor, prime, stats)
                    if remainder != [0]:
                        raise AssertionError("Berlekamp split did not divide")
                    next_factors.extend([divisor, quotient])
                else:
                    next_factors.append(factor)
            factors = next_factors
            if len(factors) == len(basis):
                break
        if len(factors) == len(basis):
            break
    # Defensive recursion makes the routine robust if a basis vector happened
    # not to finish a component because of a representation degeneracy.
    if len(factors) == 1:
        return [poly]
    result = []
    for factor in factors:
        sub_basis = _berlekamp_basis(factor, prime, stats)
        if len(sub_basis) <= 1:
            result.append(factor)
        else:
            result.extend(_berlekamp_factor_squarefree(factor, prime, stats))
    return result


def _validate_params(
    n, seed, residue_modulus, compressed_degree, coeff_bound,
    identity_scale_max,
):
    values = (
        n, seed, residue_modulus, compressed_degree, coeff_bound,
        identity_scale_max,
    )
    if any(not _is_int(value) for value in values):
        raise ValueError("all parameters must be integers")
    if residue_modulus < 5:
        raise ValueError("residue_modulus must be at least 5")
    if compressed_degree < 1:
        raise ValueError("compressed_degree must be positive")
    if n != 2 * residue_modulus * compressed_degree:
        raise ValueError("n must equal 2*residue_modulus*compressed_degree")
    if coeff_bound < 1:
        raise ValueError("coeff_bound must be positive")
    if identity_scale_max < 3:
        raise ValueError("identity_scale_max must be at least 3")


def _differentiate_f_terms(f_terms):
    derivative = {}
    for rational, exponent in f_terms:
        if exponent == 0:
            continue
        numerator, denominator = rational
        value = Fraction(numerator, denominator) * exponent
        if value.denominator != 1:
            raise ValueError("instance derivative is not integral")
        derivative[exponent - 1] = derivative.get(exponent - 1, 0) + value.numerator
    return [[coefficient, exponent] for exponent, coefficient in
            sorted(derivative.items(), reverse=True) if coefficient]


def _poly_derivative_mod(poly, prime):
    if len(poly) <= 1:
        return [0]
    return _mod_trim([index * poly[index] for index in range(1, len(poly))], prime)


def _integrate_to_terms(g_dense, constant):
    terms = []
    for exponent in range(len(g_dense) - 1, -1, -1):
        coefficient = g_dense[exponent]
        if coefficient:
            value = Fraction(coefficient, exponent + 1)
            terms.append([[value.numerator, value.denominator], exponent + 1])
    terms.append([[constant, 1], 0])
    return terms


def _f_mod_prime(f_terms, prime):
    degree = max(exponent for _, exponent in f_terms)
    dense = [0] * (degree + 1)
    for rational, exponent in f_terms:
        numerator, denominator = rational
        dense[exponent] = numerator * pow(denominator, -1, prime) % prime
    return _mod_trim(dense, prime)


def _next_prime(lower_bound):
    candidate = max(3, lower_bound | 1)
    while True:
        limit = math.isqrt(candidate)
        if all(candidate % divisor for divisor in range(3, limit + 1, 2)):
            return candidate
        candidate += 2


def make_instance(
    n,
    seed=0,
    residue_modulus=9,
    compressed_degree=4,
    coeff_bound=2,
    identity_scale_max=3,
    **params,
):
    """Compose a certified quadratic-form factorization, then integrate.

    q, r, and c are sampled before the instance.  With X=q(t^m) and
    Y=t*r(t^m), the factors X^2-cXY+Y^2 and X^2+cXY+Y^2 are planted by an
    exact identity.  Modular tests certify distinct osculation roots and a good
    reference-factorization prime; neither test discovers a factor.
    """

    _validate_params(
        n, seed, residue_modulus, compressed_degree, coeff_bound,
        identity_scale_max,
    )
    rng = random.Random(seed)
    m, ell = residue_modulus, compressed_degree
    source_values = [value for value in range(-coeff_bound, coeff_bound + 1)
                     if value]
    component_bound = max(
        (ell + 1) * coeff_bound * coeff_bound,
        identity_scale_max * ell * coeff_bound * coeff_bound,
    )
    reference_prime = _next_prime(2 * component_bound + 1)
    while n % reference_prime == 0:
        reference_prime = _next_prime(reference_prime + 2)
    attempts = 0
    while True:
        attempts += 1
        if attempts > 10_000:
            raise RuntimeError("could not obtain a squarefree planted instance")
        q = [rng.choice(source_values) for _ in range(ell)] + [1]
        r = [rng.choice(source_values) for _ in range(ell - 1)] + [1]
        scale = rng.randrange(3, identity_scale_max + 1)
        half_degree = n // 2
        q_dense = [0] * (half_degree + 1)
        r_dense = [0] * (half_degree + 1)
        for index, coefficient in enumerate(q):
            q_dense[m * index] = coefficient
        for index, coefficient in enumerate(r):
            r_dense[m * index + 1] = coefficient
        q2_dense = _dense_mul(q_dense, q_dense)
        r2_dense = _dense_mul(r_dense, r_dense)
        cross_dense = _dense_mul(q_dense, r_dense)
        factor_a = [0] * (n + 1)
        factor_b = [0] * (n + 1)
        for index, coefficient in enumerate(q2_dense):
            factor_a[index] += coefficient
            factor_b[index] += coefficient
        for index, coefficient in enumerate(cross_dense):
            factor_a[index] -= scale * coefficient
            factor_b[index] += scale * coefficient
        for index, coefficient in enumerate(r2_dense):
            factor_a[index] += coefficient
            factor_b[index] += coefficient
        factor_a, factor_b = _trim(factor_a), _trim(factor_b)
        g_dense = _dense_mul(factor_a, factor_b)
        g_mod = _mod_trim(g_dense, reference_prime)
        if _mod_gcd(
            g_mod, _poly_derivative_mod(g_mod, reference_prime),
            reference_prime,
        ) != [1]:
            continue
        # Any constant outside the finite set of critical values makes f and
        # f' coprime.  Coprimality modulo a prime larger than every denominator
        # proves coprimality over Q and hence distinct complex roots.
        squarefree_prime = _next_prime(2 * n + 3)
        for _ in range(64):
            constant = rng.randrange(-10_000, 10_001)
            f_terms = _integrate_to_terms(g_dense, constant)
            f_mod = _f_mod_prime(f_terms, squarefree_prime)
            derivative_mod = _poly_derivative_mod(f_mod, squarefree_prime)
            if _mod_gcd(f_mod, derivative_mod, squarefree_prime) == [1]:
                answer = {
                    "stride": m,
                    "blocks": [
                        _dense_mul(q, q),
                        [-scale * value for value in _dense_mul(q, r)],
                        _dense_mul(r, r),
                    ],
                }
                g_evaluations = {}
                for point in (1, -1, 2, 3):
                    g_evaluations[str(point)] = sum(
                        coefficient * pow(point, exponent)
                        for exponent, coefficient in enumerate(g_dense)
                        if coefficient
                    )
                schubert_n = 2 * n + 2
                return {
                    "factor_degree": n,
                    "residue_stride": m,
                    "compressed_degree_hidden": ell,
                    "source_coefficient_bound_hidden": coeff_bound,
                    "identity_scale_max_hidden": identity_scale_max,
                    "identity_scale_hidden": scale,
                    "component_bound": component_bound,
                    "block_lengths": [2 * ell + 1, 2 * ell, 2 * ell - 1],
                    "reference_prime": reference_prime,
                    "f_terms": f_terms,
                    "g_evaluations": g_evaluations,
                    "g_mod2_bits": sum(
                        (coefficient & 1) << exponent
                        for exponent, coefficient in enumerate(g_dense)
                        if coefficient & 1
                    ),
                    "schubert": {
                        "ambient_dimension": schubert_n,
                        "plane_dimension": n + 1,
                        "omega": "(2,3,...,k,N)",
                        "finite_osculation_count": schubert_n - 1,
                    },
                    "construction_attempts": attempts,
                    "answer": answer,
                }
        # Resample q and r if the chosen constants were exceptionally unlucky.


def _format_rational(rational):
    numerator, denominator = rational
    return str(numerator) if denominator == 1 else f"{numerator}/{denominator}"


def _format_polynomial_terms(terms, rational_coefficients=False):
    rendered = []
    for coefficient, exponent in terms:
        text = _format_rational(coefficient) if rational_coefficients else str(coefficient)
        rendered.append(f"[{text}, {exponent}]")
    return "[" + ", ".join(rendered) + "]"


def render(inst):
    degree = inst["factor_degree"]
    schubert = inst["schubert"]
    stride = inst["residue_stride"]
    lengths = inst["block_lengths"]
    bound = inst["component_bound"]
    statement = f"""Exact factor certificate for a real osculating Schubert instance

Let Q[t] be the ring of one-variable polynomials with rational coefficients.
In the displayed sparse term list, each pair [a/b,e] means the exact term
(a/b)*t^e (with an integer shown instead of a/1); unlisted coefficients are
zero and every displayed denominator is positive.

The geometric source is a conjugation-stable osculating instance in the complex
Grassmannian Gr(k,C^N), whose points are k-dimensional complex linear subspaces
of C^N, with N={schubert['ambient_dimension']} and k={schubert['plane_dimension']}.
Its conditions are omega=(2,3,...,k,N) at infinity and the standard codimension-one
Schubert incidence condition at each of the {schubert['finite_osculation_count']}
distinct complex roots of the following real squarefree polynomial f(t)
("squarefree" means that no complex root is repeated):

f terms (coefficient, exponent), descending by exponent:
{_format_polynomial_terms(inst['f_terms'], rational_coefficients=True)}

For this special family, the paper proves that its real points (the k-planes
defined over R) are in bijection with factorizations f'(t)=A(t)B(t) in which A
and B are monic real polynomials of degree {degree}; "monic" means leading
coefficient 1.  Thus a complete concrete certificate is one such factor A(t).
No knowledge of Grassmannians is needed: return A in the bounded exact language
below, and the checker differentiates f and performs exact polynomial division.
Numeric approximations and lists of roots are not accepted.

Encode A by three coefficient blocks.  The JSON object
{{"stride":m,"blocks":[C0,C1,C2]}} represents the ordinary polynomial
  A(t) = sum over r=0,1,2 and j>=0 of C_r[j] * t^(m*j+r).
All block arrays are in increasing j order and include zero coefficients.

Your answer must have exactly the two keys "stride" and "blocks".  The stride
must be the integer {stride}.  C0, C1, C2 must have lengths {lengths[0]},
{lengths[1]}, {lengths[2]}, respectively.  Every entry must be an integer in
the inclusive range [-{bound},{bound}].  The final entry of C0 must be 1,
the first entry of C0 must be nonzero, and no other nonzero pattern is assumed.
These rules make A monic of degree exactly {degree}; order is the displayed
C0,C1,C2 residue order and repetitions within a coefficient array are allowed.

Give your final answer inside <answer></answer> tags, as that JSON object.
Example: <answer>{{"stride":5,"blocks":[[1,2,1],[-2,-2],[1]]}}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    payload = match.group(1).strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(answer, dict):
        return None
    return answer


def _validate_answer_shape(inst, answer):
    if not isinstance(answer, dict) or set(answer) != {"stride", "blocks"}:
        return False, "answer must contain exactly the keys stride and blocks"
    if not _is_int(answer["stride"]):
        return False, "stride must be an integer"
    if answer["stride"] != inst["residue_stride"]:
        return False, "stride does not match the required value"
    blocks = answer["blocks"]
    if not isinstance(blocks, list) or len(blocks) != 3:
        return False, "blocks must be a list of exactly three coefficient arrays"
    for index, (block, length) in enumerate(zip(blocks, inst["block_lengths"])):
        if not isinstance(block, list) or len(block) != length:
            return False, f"block {index} must have exactly {length} coefficients"
        if not all(_is_int(value) for value in block):
            return False, "every block coefficient must be an integer"
    bound = inst["component_bound"]
    if any(abs(value) > bound for block in blocks for value in block):
        return False, "coefficient exceeds the declared inclusive height bound"
    if blocks[0][-1] != 1:
        return False, "residue-zero block must have leading coefficient 1"
    if blocks[0][0] == 0:
        return False, "factor must contain a nonzero constant coefficient"
    return True, blocks


def verify(inst, answer):
    valid, detail = _validate_answer_shape(inst, answer)
    if not valid:
        return False, detail
    blocks = detail
    divisor = _block_answer_to_dense(
        {"stride": answer["stride"], "blocks": blocks},
        inst["factor_degree"],
    )
    # Cheap exact necessary conditions keep G4's 200k structure-aware samples
    # inexpensive.  Divisibility in Z[t] implies divisibility after evaluation
    # at every integer point.
    for point in (1, -1, 2, 3):
        candidate_value = sum(
            coefficient * pow(point, exponent)
            for exponent, coefficient in enumerate(divisor)
        )
        target_value = inst["g_evaluations"][str(point)]
        if candidate_value == 0:
            if target_value != 0:
                return False, f"evaluation divisibility fails at t={point}"
            continue
        if target_value % candidate_value:
            return False, f"evaluation divisibility fails at t={point}"
    # Surviving the four integer evaluations is rare.  Before the more costly
    # integer long division, apply one further exact necessary check in F_2[t].
    divisor_bits = 0
    for exponent, coefficient in enumerate(divisor):
        if coefficient & 1:
            divisor_bits |= 1 << exponent
    remainder_bits = inst["g_mod2_bits"]
    divisor_degree = divisor_bits.bit_length() - 1
    while remainder_bits and remainder_bits.bit_length() - 1 >= divisor_degree:
        remainder_bits ^= divisor_bits << (
            remainder_bits.bit_length() - 1 - divisor_degree
        )
    if remainder_bits:
        return False, "mod-2 polynomial remainder is nonzero"
    try:
        derivative_terms = _differentiate_f_terms(inst["f_terms"])
    except (ArithmeticError, TypeError, ValueError):
        return False, "instance polynomial has a malformed derivative"
    degree = inst["factor_degree"]
    derivative = _sparse_to_dense(derivative_terms, 2 * degree)
    quotient, remainder = _dense_divmod_monic(derivative, divisor)
    if quotient is None or remainder != [0]:
        return False, "proposed polynomial does not divide f'(t) exactly"
    if len(quotient) - 1 != degree or quotient[-1] != 1:
        return False, "exact cofactor is not monic of the required degree"
    return True, "ok"


def random_candidate(inst, rng):
    bound = inst["component_bound"]
    blocks = [
        [rng.randrange(-bound, bound + 1) for _ in range(length)]
        for length in inst["block_lengths"]
    ]
    blocks[0][0] = rng.choice(tuple(range(-bound, 0)) + tuple(range(1, bound + 1)))
    blocks[0][-1] = 1
    return {"stride": inst["residue_stride"], "blocks": blocks}


def search_space(inst):
    lengths = inst["block_lengths"]
    bound = inst["component_bound"]
    free = (lengths[0] - 2) + lengths[1] + lengths[2]
    return (2 * bound) * (2 * bound + 1) ** free


def enumerate_all(inst):
    space = search_space(inst)
    if space > 250_000:
        return None
    lengths = inst["block_lengths"]
    bound = inst["component_bound"]
    values = range(-bound, bound + 1)
    nonzero = tuple(range(-bound, 0)) + tuple(range(1, bound + 1))
    free = (lengths[0] - 2) + lengths[1] + lengths[2]
    valid = 0
    for constant in nonzero:
        for entries in itertools.product(values, repeat=free):
            cursor = 0
            middle_count = lengths[0] - 2
            block0 = [constant]
            block0.extend(entries[cursor:cursor + middle_count])
            cursor += middle_count
            block0.append(1)
            block1 = list(entries[cursor:cursor + lengths[1]])
            cursor += lengths[1]
            block2 = list(entries[cursor:cursor + lengths[2]])
            answer = {
                "stride": inst["residue_stride"],
                "blocks": [block0, block1, block2],
            }
            if verify(inst, answer)[0]:
                valid += 1
    return valid


def _derivative_dense(inst):
    terms = _differentiate_f_terms(inst["f_terms"])
    return _sparse_to_dense(terms, 2 * inst["factor_degree"])


def _exact_monic_square_root(square):
    square = _trim(square)
    degree = len(square) - 1
    if degree < 0 or degree % 2 or square[-1] != 1:
        return None, 0
    root_degree = degree // 2
    root = [0] * (root_degree + 1)
    root[root_degree] = 1
    operations = 0
    for exponent in range(root_degree - 1, -1, -1):
        target_degree = root_degree + exponent
        known = 0
        for i in range(exponent + 1, root_degree + 1):
            j = target_degree - i
            if exponent < j <= root_degree:
                known += root[i] * root[j]
                operations += 2
        remainder = square[target_degree] - known
        operations += 1
        if remainder % 2:
            return None, operations
        root[exponent] = remainder // 2
        operations += 1
    if _dense_mul(root, root) != square:
        return None, operations
    return root, operations


def _compact_quadratic_form_route(inst):
    derivative_terms = _differentiate_f_terms(inst["f_terms"])
    derivative_ops = len(derivative_terms)
    term_map = {exponent: coefficient for coefficient, exponent in derivative_terms}
    above_four = sorted(exponent for exponent in term_map if exponent > 4)
    if not above_four:
        return None, {"operations": derivative_ops, "reason": "no exponent gap"}
    modulus = above_four[0]
    if modulus < 5:
        return None, {"operations": derivative_ops, "reason": "invalid residue modulus"}
    q_fourth_map, middle_map, r_fourth_map = {}, {}, {}
    for exponent, coefficient in term_map.items():
        residue = exponent % modulus
        if residue == 0:
            q_fourth_map[exponent // modulus] = coefficient
        elif residue == 2:
            middle_map[(exponent - 2) // modulus] = coefficient
        elif residue == 4:
            r_fourth_map[(exponent - 4) // modulus] = coefficient
        else:
            return None, {"operations": derivative_ops, "reason": "unexpected residue class"}
    q_fourth = [0] * (max(q_fourth_map) + 1)
    middle = [0] * (max(middle_map) + 1)
    r_fourth = [0] * (max(r_fourth_map) + 1)
    for exponent, coefficient in q_fourth_map.items():
        q_fourth[exponent] = coefficient
    for exponent, coefficient in middle_map.items():
        middle[exponent] = coefficient
    for exponent, coefficient in r_fourth_map.items():
        r_fourth[exponent] = coefficient
    q_square, q2_ops = _exact_monic_square_root(q_fourth)
    q, q_ops = _exact_monic_square_root(q_square) if q_square is not None else (None, 0)
    r_square, r2_ops = _exact_monic_square_root(r_fourth)
    r, r_ops = _exact_monic_square_root(r_square) if r_square is not None else (None, 0)
    operations = derivative_ops + q2_ops + q_ops + r2_ops + r_ops
    if q is None or r is None:
        return None, {"operations": operations, "reason": "outer blocks are not fourth powers"}
    scale_square = 2 - middle[-1]
    scale = math.isqrt(scale_square) if scale_square >= 0 else -1
    operations += 2
    if scale < 3 or scale * scale != scale_square:
        return None, {"operations": operations, "reason": "middle scale is not integral"}
    cross = _dense_mul(q, r)
    operations += 2 * len(q) * len(r)
    middle_block = [-scale * coefficient for coefficient in cross]
    operations += len(middle_block)
    answer = {
        "stride": modulus,
        "blocks": [q_square, middle_block, r_square],
    }
    return answer, {
        "operations": operations,
        "inferred_modulus": modulus,
        "inferred_scale": scale,
        "q_fourth_root_operations": q2_ops + q_ops,
        "r_fourth_root_operations": r2_ops + r_ops,
    }


def _reference_berlekamp_factor(inst):
    """Generic modular factorization, blind to the quadratic-form identity."""

    started = time.perf_counter()
    derivative = _derivative_dense(inst)
    prime = inst["reference_prime"]
    stats = {
        "field_operations": 0,
        "gcd_steps": 0,
        "subset_nodes": 0,
        "modular_factor_count": 0,
    }
    modular = _mod_trim(derivative, prime)
    derivative_mod = _poly_derivative_mod(modular, prime)
    if _mod_gcd(modular, derivative_mod, prime, stats) != [1]:
        stats["wall_clock_sec"] = time.perf_counter() - started
        return None, stats
    factors = _berlekamp_factor_squarefree(modular, prime, stats)
    factors.sort(key=lambda poly: (len(poly), poly))
    stats["modular_factor_count"] = len(factors)
    target = inst["factor_degree"]
    suffix_degree = [0] * (len(factors) + 1)
    for index in range(len(factors) - 1, -1, -1):
        suffix_degree[index] = suffix_degree[index + 1] + len(factors[index]) - 1
    answer = None

    def visit(index, degree, chosen):
        nonlocal answer
        stats["subset_nodes"] += 1
        if answer is not None or degree > target:
            return
        if degree + suffix_degree[index] < target:
            return
        if index == len(factors):
            if degree != target:
                return
            candidate_mod = [1]
            for factor_index in chosen:
                candidate_mod = _mod_mul(
                    candidate_mod, factors[factor_index], modular, prime, stats
                )
            centered = [value if value <= prime // 2 else value - prime
                        for value in candidate_mod]
            centered += [0] * (target + 1 - len(centered))
            candidate = _dense_to_block_answer(inst, centered)
            if candidate is not None and verify(inst, candidate)[0]:
                answer = candidate
            return
        factor_degree = len(factors[index]) - 1
        visit(index + 1, degree + factor_degree, chosen + [index])
        visit(index + 1, degree, chosen)

    visit(0, 0, [])
    stats["wall_clock_sec"] = time.perf_counter() - started
    return answer, stats


def _ansatz_candidate(inst, rule):
    bound = inst["component_bound"]
    blocks = []
    for residue, length in enumerate(inst["block_lengths"]):
        block = []
        for index in range(length):
            value = int(rule(residue, index))
            block.append(max(-bound, min(bound, value)))
        blocks.append(block)
    if blocks[0][0] == 0:
        blocks[0][0] = 1
    blocks[0][-1] = 1
    return {"stride": inst["residue_stride"], "blocks": blocks}


def _attack_magnitude_outlier(inst):
    g = _derivative_dense(inst)
    stride = inst["residue_stride"]
    return _ansatz_candidate(
        inst,
        lambda residue, index: (
            1 if g[min(len(g) - 1, stride * index + 2 * residue)] >= 0 else -1
        ),
    )


def _attack_greedy_residue_projection(inst):
    g = _derivative_dense(inst)
    stride = inst["residue_stride"]
    return _ansatz_candidate(
        inst,
        lambda residue, index: (
            g[stride * index + 2 * residue]
            if stride * index + 2 * residue < len(g) else 0
        ),
    )


def _attack_random_restart(inst, rng, restarts=256):
    last = None
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last
    return last


def _attack_symmetric_alternating_ansatz(inst):
    lengths = inst["block_lengths"]
    return _ansatz_candidate(
        inst,
        lambda residue, index: (
            -1 if (index + residue) % 2 else 1
        ) * (1 if index <= (lengths[residue] - 1) // 2
             else 1),
    )


def _sign_transform(inst):
    out = copy.deepcopy(inst)
    transformed_f = []
    for rational, exponent in inst["f_terms"]:
        numerator, denominator = rational
        transformed_f.append([
            [numerator * (-1 if exponent % 2 == 0 else 1), denominator], exponent
        ])
    out["f_terms"] = transformed_f
    degree = inst["factor_degree"]
    stride = inst["residue_stride"]
    transformed_blocks = []
    for residue, block in enumerate(inst["answer"]["blocks"]):
        transformed_blocks.append([
            coefficient * (-1 if (degree + stride * index + residue) % 2 else 1)
            for index, coefficient in enumerate(block)
        ])
    out["answer"] = {"stride": stride, "blocks": transformed_blocks}
    derivative = _derivative_dense(out)
    out["g_evaluations"] = {
        str(point): sum(coefficient * pow(point, exponent)
                        for exponent, coefficient in enumerate(derivative)
                        if coefficient)
        for point in (1, -1, 2, 3)
    }
    out["g_mod2_bits"] = sum(
        (coefficient & 1) << exponent
        for exponent, coefficient in enumerate(derivative)
        if coefficient & 1
    )
    return out


def canonical_key(inst):
    # The Schubert instance is determined by the roots of f, not by f' alone.
    # In particular, two vertical translates have the same derivative but
    # generally different osculation points.  Normalize exact rational terms,
    # including the constant, and quotient only by the represented projective
    # reflection t -> -t.  Because deg(f) is odd and its leading coefficient is
    # fixed, the normalized reflected polynomial is -f(-t).
    exact = {}
    for rational, exponent in inst["f_terms"]:
        value = Fraction(rational[0], rational[1])
        exact[exponent] = exact.get(exponent, Fraction(0)) + value

    def encoded(reflected):
        terms = []
        for exponent, value in exact.items():
            if reflected and exponent % 2 == 0:
                value = -value
            if value:
                terms.append((exponent, value.numerator, value.denominator))
        return tuple(sorted(terms, reverse=True))

    normal = min(encoded(False), encoded(True))
    payload = {
        "factor_degree": inst["factor_degree"],
        "residue_stride": inst["residue_stride"],
        "block_lengths": inst["block_lengths"],
        "component_bound": inst["component_bound"],
        "f_normal_form": normal,
    }
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params):
    return None


def _atomic_elements(value):
    if isinstance(value, dict):
        return sum(_atomic_elements(item) for item in value.values())
    if isinstance(value, list):
        return sum(_atomic_elements(item) for item in value)
    return 1


def selftest():
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    failures = []
    attempts = 0
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not failures and json_roundtrips == attempts,
        "attempts": attempts,
        "json_roundtrips": json_roundtrips,
        "failures": failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=90210, **ship_params)
    answer = inst["answer"]
    dropped = copy.deepcopy(answer)
    dropped["blocks"][0].pop()
    swapped = copy.deepcopy(answer)
    swapped["blocks"][0][-1], swapped["blocks"][0][-2] = (
        swapped["blocks"][0][-2], swapped["blocks"][0][-1]
    )
    duplicated = copy.deepcopy(answer)
    duplicated["blocks"][1] = duplicated["blocks"][0][:]
    out_of_range = copy.deepcopy(answer)
    out_of_range["blocks"][0][0] = inst["component_bound"] + 1
    corruptions = {
        "drop": dropped,
        "swap": swapped,
        "duplicate": duplicated,
        "empty": {},
        "out_of_range": out_of_range,
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
    }

    realistic = (
        "The residue classes suggest a difference of squares.\n\n"
        "```json\n<answer>" + json.dumps(answer) + "</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("no tagged answer") is None,
        "parsed_blocks": len(parsed.get("blocks", [])) if isinstance(parsed, dict) else None,
        "garbage_returns_none": parse_answer("no tagged answer") is None,
    }

    guess_rng = random.Random(0x13071833)
    hits = 0
    started = time.perf_counter()
    for _ in range(_GUESS_SAMPLES):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    guess_seconds = time.perf_counter() - started
    report["G4_guess_resistance"] = {
        "pass": hits / _GUESS_SAMPLES < 1e-6,
        "hits": hits,
        "total": _GUESS_SAMPLES,
        "observed_probability": hits / _GUESS_SAMPLES,
        "structure_aware_space": search_space(inst),
        "sample_seconds": round(guess_seconds, 6),
        "sampler": (
            "uniform over the fixed three-block monic polynomial language, "
            "including zero coefficients and a nonzero constant term"
        ),
    }

    attacks = {
        "outlier_largest_derivative_coefficients": {"successes": 0, "attempts": 0},
        "greedy_residue_projection": {"successes": 0, "attempts": 0},
        "random_restart_256_structure_aware": {"successes": 0, "attempts": 0},
        "in_context_symmetric_alternating_ansatz": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_times = []
    reference_operations = []
    reference_nodes = []
    reference_factor_counts = []
    compact_successes = 0
    compact_operations = []
    for seed in range(3100, 3108):
        attacked = make_instance(seed=seed, **ship_params)
        candidates = {
            "outlier_largest_derivative_coefficients": _attack_magnitude_outlier(attacked),
            "greedy_residue_projection": _attack_greedy_residue_projection(attacked),
            "random_restart_256_structure_aware": _attack_random_restart(
                attacked, random.Random(seed ^ 0x5A5A), 256
            ),
            "in_context_symmetric_alternating_ansatz": _attack_symmetric_alternating_ansatz(attacked),
        }
        for name, candidate in candidates.items():
            attacks[name]["attempts"] += 1
            if verify(attacked, candidate)[0]:
                attacks[name]["successes"] += 1
        reference, stats = _reference_berlekamp_factor(attacked)
        reference_times.append(stats["wall_clock_sec"])
        reference_operations.append(stats["field_operations"])
        reference_nodes.append(stats["subset_nodes"])
        reference_factor_counts.append(stats["modular_factor_count"])
        if reference is not None and verify(attacked, reference)[0]:
            reference_successes += 1
        compact, compact_stats = _compact_quadratic_form_route(attacked)
        compact_operations.append(compact_stats["operations"])
        if compact is not None and verify(attacked, compact)[0]:
            compact_successes += 1
    all_failed = all(entry["successes"] == 0 for entry in attacks.values())
    median_reference_time = statistics.median(reference_times)
    median_reference_operations = int(statistics.median(reference_operations))
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Berlekamp factorization over the recorded good prime plus centered lift",
            "complexity": (
                "classical O(D^3) modular linear algebra plus O(2^r D^2) "
                "worst-case grouping for r modular factors; polynomial-time "
                "LLL factorization over Q is also known"
            ),
            "median_wall_clock_sec": round(median_reference_time, 6),
            "median_operations": median_reference_operations,
            "median_subset_nodes": int(statistics.median(reference_nodes)),
            "median_modular_factors": int(statistics.median(reference_factor_counts)),
            "operation_definition": (
                "each modular multiply, add/subtract, scale, or pivot update "
                "counts as one field operation"
            ),
            "solves": f"{reference_successes}/8, as expected",
        },
        "compact_route": {
            "name": "three residue blocks and a quadratic-form difference of squares",
            "median_operations": int(statistics.median(compact_operations)),
            "solves": f"{compact_successes}/8",
        },
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    strongest_candidate = _attack_greedy_residue_projection(inst)
    baseline_started = time.perf_counter()
    baseline_ok = verify(inst, strongest_candidate)[0]
    baseline_seconds = time.perf_counter() - baseline_started
    report["G5_density_and_baseline"] = {
        "pass": hits / _GUESS_SAMPLES < 1e-6
        and demo_count is not None
        and reference_successes == 8,
        "shipping_valid_hits": hits,
        "shipping_density_samples": _GUESS_SAMPLES,
        "shipping_observed_solution_fraction": hits / _GUESS_SAMPLES,
        "shipping_space_size": search_space(inst),
        "demo_exact_solution_count": demo_count,
        "demo_space_size": search_space(demo),
        "baseline_name": "greedy residue projection",
        "baseline_wall_seconds": round(baseline_seconds, 6),
        "baseline_solved": baseline_ok,
        "strongest_reference_name": (
            "Berlekamp factorization over the recorded good prime plus centered lift"
        ),
        "strongest_reference_median_wall_seconds": round(median_reference_time, 6),
        "strongest_reference_median_operations": median_reference_operations,
        "strongest_reference_solved": reference_successes == 8,
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled_params["residue_modulus"] *= 2
    doubled = make_instance(seed=77, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["factor_degree"] == 2 * inst["factor_degree"]
        and doubled["block_lengths"] == inst["block_lengths"],
        "shipping_n": inst["factor_degree"],
        "doubled_n": doubled["factor_degree"],
        "answer_shape_unchanged": doubled["block_lengths"] == inst["block_lengths"],
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = 0
    carried_checks = 0
    constant_sensitivity_checks = 0
    distinct_keys = []
    for offset in range(20):
        original = make_instance(seed=7000 + offset, **ship_params)
        key = canonical_key(original)
        distinct_keys.append(key)
        reordered = copy.deepcopy(original)
        random.Random(8000 + offset).shuffle(reordered["f_terms"])
        signed = _sign_transform(original)
        signed_reordered = _sign_transform(reordered)
        for variant in (reordered, signed, signed_reordered):
            invariance_checks += 1
            if canonical_key(variant) == key and verify(variant, variant["answer"])[0]:
                carried_checks += 1
        translated = copy.deepcopy(original)
        for term in translated["f_terms"]:
            if term[1] == 0:
                term[0][0] += term[0][1]
                break
        if (_derivative_dense(translated) == _derivative_dense(original)
                and canonical_key(translated) != key):
            constant_sensitivity_checks += 1
    report["G8_canonical_key"] = {
        "pass": invariance_checks == 60
        and carried_checks == 60
        and constant_sensitivity_checks == 20
        and len(set(distinct_keys)) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "same_derivative_different_constant_distinguished": constant_sensitivity_checks,
        "unrelated_distinct": len(set(distinct_keys)),
        "unrelated_attempts": 20,
        "symmetries": [
            "arbitrary reordering of the sparse input term list",
            "the real projective coordinate reflection t -> -t",
            "input reordering composed with t -> -t",
        ],
    }

    compact_answer, compact_stats = _compact_quadratic_form_route(inst)
    serialized = json.dumps(answer, separators=(",", ":"))
    answer_chars = len(serialized)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _atomic_elements(answer)
    arms = copy.deepcopy(G9_EVIDENCE["arms"])
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else None
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else None
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and compact_stats["operations"] <= 300
        and compact_answer is not None
        and verify(inst, compact_answer)[0]
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None
        ),
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact_stats["operations"],
        "intended_route_verifies": (
            compact_answer is not None and verify(inst, compact_answer)[0]
        ),
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track_B_mechanical_cost"] = {
        "reference_median_wall_clock_sec": round(median_reference_time, 6),
        "reference_median_field_operations": median_reference_operations,
        "compact_route_operations": compact_stats["operations"],
    }
    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if re.match(r"G\d", key)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
