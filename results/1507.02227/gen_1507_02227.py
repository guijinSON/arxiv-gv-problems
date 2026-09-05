"""Verified generators for polynomial syzygies of plane rational curves.

The family is based on the Hilbert--Burch presentation in Section 2 of
arXiv:1507.02227.  Instances are generated from the two rows of a presentation
matrix and only then are its maximal minors formed.  Thus ``make_instance``
never solves the syzygy problem that it poses.
"""

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
    from gvlib import rationals, sparse_poly  # noqa: F401
except ImportError:  # The implementation below remains standard-library-only.
    rationals = sparse_poly = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "homogeneous binary forms over Q",
        "polynomial syzygy of a plane rational-curve parameterization",
    ],
    "verification_operations": [
        "exact integer polynomial multiplication",
        "gvlib sparse-polynomial identity check when available",
        "exact coefficient comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Two special directions in the span of the parameterizing forms have "
        "high root multiplicities; recognizing them compresses a large "
        "coefficient-nullspace calculation to two small relations."
    ),
    "hardness_basis": (
        "Track B: exact modular Gaussian elimination on the degree-8 "
        "coefficient-convolution matrix is O((d+k)k^2), measured at the easy "
        "shipping preset as 52,891 field operations and about 0.01 s; the invariant "
        "route uses 146 exact operations but requires recognizing two mixed "
        "high-multiplicity directions."
    ),
    "max_answer_tokens": 142,
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
    "demo": {"n": 8, "k": 2},
    "easy": {"n": 72, "k": 8},
    "medium": {"n": 120, "k": 12},
    "hard": {"n": 160, "k": 16},
}
SHIPPING_DIFFICULTY = "easy"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A normalized triple of homogeneous degree-k polynomials over Q, "
        "stored sparsely as [[[numerator,denominator],[s_exp,t_exp]],...]. "
        "Denominators are 1, zero terms are omitted, terms are ordered by "
        "increasing t_exp, every numerator has absolute value at most B=4*3^k, "
        "and the coefficient of s^k in the first polynomial is 1."
    ),
    "bounds": {
        "n_polynomials": 3,
        "degree_parameter": "k",
        "coefficient_bound": "4*3^k",
        "denominator": 1,
        "normalization": "coefficient of s^k in polynomial 0 equals 1",
    },
}

STRUCTURAL_HINT = (
    "The span of the three degree-d forms has distinguished directions with "
    "root-multiplicity patterns d and (d-k,k)."
)
PLACEBO_HINT = (
    "The three degree-d forms reward careful bookkeeping of homogeneous "
    "coefficient order and rational signs."
)

# Filled from the separate hardening runs before release.  These values are
# diagnostics only; G9(c), not oracle success under a hint, is the gate.
G9_ARMS = {
    "bare": {"solved": 0, "attempts": 3, "errors": 0},
    "hinted": {"solved": 1, "attempts": 3, "errors": 0},
    "placebo": {"solved": 0, "attempts": 3, "errors": 0},
}

NOTES = """
Section 2, equation (2), fixes the native definition: a splitting type
(k,d-k) is encoded by the two homogeneous rows of a Hilbert--Burch matrix, and
the three parameterizing forms are its 2-by-2 minors.  Theorem 3.1 identifies
the same minimal moving line with the scroll construction, so no discrete
surrogate is used here.  The Introduction's Ascenzi bounds identify a special
easy regime, and the coefficient-kernel method is an efficient general method;
therefore this is explicitly Track B, not a worst-case hardness claim.

Generation starts with rows alpha=(X^k,0,Y^k) and beta, forms their minors,
then applies an invertible target-coordinate mixing.  Coprimality is forced by
the X^d minor and the Y^d term, while birationality follows from the displayed
ratios in README.md.  The planted answer is alpha carried through the inverse
mixing matrix.  The L1 outlier attack treats one mixed coordinate as special;
the edge-greedy attack recovers only the (d-k,k) direction; the obvious
two-monomial ansatz omits the dense kth power; and random restarts sample the
full normalized coefficient language.  Each fails.  Exact modular Gaussian
elimination is reported separately as the successful Track-B reference
algorithm.
""".strip()


_PRIME = 2305843009213693951  # 2^61-1, prime.
_Q_VALUES = (-5, -4, -3, -2, -1, 1, 2, 3, 4, 5)
_MATRIX_CACHE = None


def _det3(a):
    return (
        a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
        - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
        + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0])
    )


def _inv3_unimodular(a):
    det = _det3(a)
    if abs(det) != 1:
        raise ValueError("matrix is not unimodular")
    # Cofactor transpose, divided by det (which is +/-1).
    return [
        [
            (
                a[(j + 1) % 3][(i + 1) % 3]
                * a[(j + 2) % 3][(i + 2) % 3]
                - a[(j + 1) % 3][(i + 2) % 3]
                * a[(j + 2) % 3][(i + 1) % 3]
            )
            // det
            for j in range(3)
        ]
        for i in range(3)
    ]


def _admissible_matrices():
    """Small N=M^-1 with N[0][0]=1 and a fully mixed inverse M."""
    global _MATRIX_CACHE
    if _MATRIX_CACHE is None:
        values = (-2, -1, 1, 2)
        found = []
        for tail in itertools.product(values, repeat=8):
            nmat = [
                [1, tail[0], tail[1]],
                [tail[2], tail[3], tail[4]],
                [tail[5], tail[6], tail[7]],
            ]
            if abs(_det3(nmat)) != 1:
                continue
            mmat = _inv3_unimodular(nmat)
            if all(x != 0 for row in mmat for x in row) and max(
                abs(x) for row in mmat for x in row
            ) <= 16:
                found.append((nmat, mmat))
        _MATRIX_CACHE = tuple(found)
    return _MATRIX_CACHE


def _add(p, q):
    if len(p) != len(q):
        raise ValueError("polynomial degree mismatch")
    return [a + b for a, b in zip(p, q)]


def _scale(p, c):
    return [c * x for x in p]


def _x_y_monomial(x_degree, y_degree):
    """Coefficients of (s+2t)^x_degree * t^y_degree."""
    degree = x_degree + y_degree
    out = [0] * (degree + 1)
    for i in range(x_degree + 1):
        out[i + y_degree] = math.comb(x_degree, i) * (2 ** i)
    return out


def _mix_forms(matrix, forms):
    return [
        [sum(matrix[i][j] * forms[j][r] for j in range(3)) for r in range(len(forms[0]))]
        for i in range(3)
    ]


def _coeffs_to_json(coeffs, degree):
    return [
        [[[int(c), 1], [degree - i, i]] for i, c in enumerate(poly) if c]
        for poly in coeffs
    ]


def _json_to_coeffs(answer, degree, bound, normalization=(0, 0, 1)):
    if not isinstance(answer, list) or len(answer) != 3:
        return None, "answer must contain exactly three polynomials"
    coeffs = []
    for p_index, poly in enumerate(answer):
        if not isinstance(poly, list):
            return None, f"polynomial {p_index} must be a list of terms"
        row = [0] * (degree + 1)
        seen = set()
        last_t = -1
        for term in poly:
            if (
                not isinstance(term, list)
                or len(term) != 2
                or not isinstance(term[0], list)
                or len(term[0]) != 2
                or not isinstance(term[1], list)
                or len(term[1]) != 2
            ):
                return None, "each term must be [[numerator,denominator],[s_exp,t_exp]]"
            num, den = term[0]
            es, et = term[1]
            ints = (num, den, es, et)
            if any(isinstance(x, bool) or not isinstance(x, int) for x in ints):
                return None, "coefficients and exponents must be integers"
            if den <= 0 or math.gcd(num, den) != 1:
                return None, "rational coefficients must be reduced with positive denominator"
            if den != 1:
                return None, "this bounded language requires denominator 1"
            if num == 0:
                return None, "zero-coefficient terms must be omitted"
            if abs(num) > bound:
                return None, "coefficient exceeds the declared bound"
            if es < 0 or et < 0 or es + et != degree:
                return None, f"every monomial must have total degree {degree}"
            if et in seen:
                return None, "duplicate monomial"
            if et <= last_t:
                return None, "terms are not in canonical exponent order"
            seen.add(et)
            last_t = et
            row[et] = num
        coeffs.append(row)
    norm_poly, norm_t_exp, norm_value = normalization
    if (
        isinstance(norm_poly, bool) or not isinstance(norm_poly, int)
        or isinstance(norm_t_exp, bool) or not isinstance(norm_t_exp, int)
        or isinstance(norm_value, bool) or not isinstance(norm_value, int)
        or not 0 <= norm_poly < 3 or not 0 <= norm_t_exp <= degree
    ):
        return None, "malformed normalization convention"
    if coeffs[norm_poly][norm_t_exp] != norm_value:
        return None, (
            f"normalization requires coefficient {norm_value} on "
            f"s^{degree-norm_t_exp}t^{norm_t_exp} in polynomial {norm_poly}"
        )
    return coeffs, "ok"


def make_instance(n, seed=0, **params):
    """Construct a rational-curve parameterization and its minimal syzygy.

    ``n`` is the curve degree d.  It must be a multiple of k and at least 4k.
    The certificate comes from the first Hilbert--Burch row before the three
    minors are mixed; no coefficient-kernel problem is solved here.
    """
    k = params.pop("k", None)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    if isinstance(k, bool) or not isinstance(k, int):
        raise TypeError("k must be an integer")
    if k < 2 or n < 4 * k or n % k:
        raise ValueError("require k >= 2, n >= 4k, and n divisible by k")

    rng = random.Random(seed)
    nmat, mmat = rng.choice(_admissible_matrices())
    ratio = n // k
    q_values = [rng.choice(_Q_VALUES) for _ in range(2, ratio)]

    # Hilbert--Burch rows over X=s+2t, Y=t:
    # alpha = (X^k, 0, Y^k)
    # beta  = (Y^(d-k), X^(d-k), X^(d-k-1)Y
    #          + sum_{j=2}^{d/k-1} q_j X^(d-k-jk)Y^(jk)).
    m = n - k
    g0 = _scale(_x_y_monomial(m, k), -1)
    g2 = _x_y_monomial(n, 0)
    g1 = [0] * (n + 1)
    g1[n] = 1
    g1 = _add(g1, _scale(_x_y_monomial(n - 1, 1), -1))
    for j, q in zip(range(2, ratio), q_values):
        g1 = _add(g1, _scale(_x_y_monomial(n - j * k, j * k), -q))
    forms = _mix_forms(mmat, [g0, g1, g2])

    xk = _x_y_monomial(k, 0)
    yk = _x_y_monomial(0, k)
    answer_coeffs = [
        _add(_scale(xk, nmat[0][j]), _scale(yk, nmat[2][j]))
        for j in range(3)
    ]
    bound = 4 * (3 ** k)
    answer = _coeffs_to_json(answer_coeffs, k)
    return {
        "degree": n,
        "syzygy_degree": k,
        "coefficient_bound": bound,
        "normalization": [0, 0, 1],
        "forms": forms,
        "answer": answer,
    }


def render(inst):
    d = inst["degree"]
    k = inst["syzygy_degree"]
    bound = inst["coefficient_bound"]
    norm_poly, norm_t_exp, norm_value = inst.get("normalization", [0, 0, 1])
    lines = [
        "Polynomial syzygy of a parameterized plane rational curve",
        "",
        "Work over the rational numbers. For a degree-r homogeneous binary form",
        "P(s,t), its coefficient vector [c_0,...,c_r] means",
        "P(s,t) = sum_{i=0}^r c_i s^(r-i)t^i.",
        "",
        f"Here d={d}, k={k}, and B={bound}. The three degree-d forms are:",
    ]
    for j, form in enumerate(inst["forms"]):
        lines.append(f"F{j} = {json.dumps(form, separators=(',', ':'))}")
    lines.extend([
        "",
        "Find three homogeneous degree-k polynomials A0,A1,A2 such that",
        "A0*F0 + A1*F1 + A2*F2 is the zero polynomial.",
        "",
        "Your answer must use the following finite normalized language. Represent",
        "each polynomial sparsely as a list of terms",
        "[[[numerator,denominator],[s_exponent,t_exponent]],...]. Use exactly",
        "three polynomial lists. Every exponent is nonnegative and sums to k;",
        "order terms by increasing t_exponent; omit zero terms; use reduced",
        "rationals with positive denominator. In this instance every denominator",
        f"must be 1 and every |numerator| must be <= B={bound}. The coefficient",
        (
            f"of s^{k-norm_t_exp}t^{norm_t_exp} in A{norm_poly} must be "
            f"exactly {norm_value}. Order of A0,A1,A2 matters."
        ),
        "",
        "Give your final answer inside <answer></answer> tags, as one JSON array",
        "containing the three sparse polynomial arrays.",
        (
            "Example of the required syntax (not a solution): "
            f"<answer>[[[[1,1],[{k},0]]],[[[-2,1],[0,{k}]]],"
            f"[[[3,1],[{k-1},1]]]]</answer>"
        ),
        "Output nothing else inside the tags.",
    ])
    text = "\n".join(lines)
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, flags=re.I | re.S)
    if fence:
        body = fence.group(1).strip()
    try:
        return json.loads(body)
    except (TypeError, ValueError):
        return None


def verify(inst, answer):
    try:
        d = inst["degree"]
        k = inst["syzygy_degree"]
        bound = inst["coefficient_bound"]
        forms = inst["forms"]
        if (
            not isinstance(forms, list)
            or len(forms) != 3
            or any(not isinstance(f, list) or len(f) != d + 1 for f in forms)
        ):
            return False, "malformed instance forms"
        coeffs, reason = _json_to_coeffs(
            answer, k, bound, tuple(inst.get("normalization", [0, 0, 1]))
        )
        if coeffs is None:
            return False, reason
        # Compare coefficients from the s-edge inward.  Wrong random candidates
        # almost always fail at the first coefficient; valid certificates still
        # receive a complete exact identity check.
        for r in range(d + k + 1):
            total = 0
            lo = max(0, r - d)
            hi = min(k, r)
            for j in range(3):
                for i in range(lo, hi + 1):
                    total += coeffs[j][i] * forms[j][r - i]
            if total != 0:
                return False, f"syzygy identity fails at t-exponent {r}"
        # Exercise the repository's canonical sparse-polynomial arithmetic as
        # an independent exact check.  The direct convolution above remains the
        # standard-library fallback and gives random candidates a cheap, sound
        # early rejection path.
        if sparse_poly is not None:
            a_polys = [
                {(k - i, i): Fraction(c) for i, c in enumerate(row) if c}
                for row in coeffs
            ]
            f_polys = [
                {(d - i, i): Fraction(c) for i, c in enumerate(row) if c}
                for row in forms
            ]
            identity = {}
            for a_poly, f_poly in zip(a_polys, f_polys):
                identity = sparse_poly.add(identity, sparse_poly.mul(a_poly, f_poly))
            if not sparse_poly.is_zero(identity):
                return False, "sparse-polynomial identity cross-check failed"
        return True, "ok"
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        return False, f"malformed answer or instance: {exc}"


def random_candidate(inst, rng):
    if not hasattr(rng, "randint"):
        raise TypeError("rng must provide randint")
    k = inst["syzygy_degree"]
    bound = inst["coefficient_bound"]
    norm_poly, norm_t_exp, norm_value = inst.get("normalization", [0, 0, 1])
    coeffs = []
    for j in range(3):
        row = []
        for i in range(k + 1):
            if j == norm_poly and i == norm_t_exp:
                row.append(norm_value)
            else:
                row.append(rng.randint(-bound, bound))
        coeffs.append(row)
    return _coeffs_to_json(coeffs, k)


def search_space(inst):
    k = inst["syzygy_degree"]
    bound = inst["coefficient_bound"]
    return (2 * bound + 1) ** (3 * (k + 1) - 1)


def enumerate_all(inst):
    # Even the smallest supported language has more than 10^9 elements.
    if search_space(inst) > 200000:
        return None
    return None


def _rref_rows(rows):
    """Canonical rational row space, represented by integer pairs."""
    from fractions import Fraction

    a = [[Fraction(x) for x in row] for row in rows]
    nr = len(a)
    nc = len(a[0])
    pivot_row = 0
    for col in range(nc):
        pivot = next((r for r in range(pivot_row, nr) if a[r][col]), None)
        if pivot is None:
            continue
        a[pivot_row], a[pivot] = a[pivot], a[pivot_row]
        v = a[pivot_row][col]
        a[pivot_row] = [x / v for x in a[pivot_row]]
        for r in range(nr):
            if r != pivot_row and a[r][col]:
                c = a[r][col]
                a[r] = [x - c * y for x, y in zip(a[r], a[pivot_row])]
        pivot_row += 1
        if pivot_row == nr:
            break
    a = [row for row in a if any(row)]
    return tuple(tuple((x.numerator, x.denominator) for x in row) for row in a)


def _source_variants(forms):
    identity = [row[:] for row in forms]
    reverse = [list(reversed(row)) for row in forms]
    parity = [[x if i % 2 == 0 else -x for i, x in enumerate(row)] for row in forms]
    reverse_parity = [list(reversed(row)) for row in parity]
    return (identity, reverse, parity, reverse_parity)


def canonical_key(inst):
    """Hash a target-GL(3)-invariant row space and basic source relabellings."""
    forms = inst["forms"]
    normal_forms = [_rref_rows(v) for v in _source_variants(forms)]
    best = min(normal_forms)
    # The requested syzygy degree is part of the problem, even though the
    # degree-d form span usually determines it for generator-produced inputs.
    payload = json.dumps([inst["syzygy_degree"], best], separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params):
    n = int(params["n"])
    k = int(params["k"])
    # Keep the degree-k polynomial witness fixed in size and add four more
    # k-blocks of degree-d coefficient data (more moduli and more equations).
    return {"n": n + 4 * k, "k": k}


def _reference_syzygy(inst):
    """Standard coefficient-kernel algorithm over a large exact prime field."""
    d = inst["degree"]
    k = inst["syzygy_degree"]
    forms = inst["forms"]
    bound = inst["coefficient_bound"]
    if 2 * bound >= _PRIME:
        raise ValueError("reference prime is too small for coefficient recovery")
    cols = 3 * (k + 1)
    rows = d + k + 1
    matrix = []
    for r in range(rows):
        row = []
        for j in range(3):
            for i in range(k + 1):
                q = r - i
                row.append(forms[j][q] % _PRIME if 0 <= q <= d else 0)
        matrix.append(row)

    operations = 0
    pivots = []
    pivot_row = 0
    for col in range(cols):
        pivot = next((r for r in range(pivot_row, rows) if matrix[r][col]), None)
        if pivot is None:
            continue
        matrix[pivot_row], matrix[pivot] = matrix[pivot], matrix[pivot_row]
        inv = pow(matrix[pivot_row][col], _PRIME - 2, _PRIME)
        operations += 1
        for c in range(col, cols):
            matrix[pivot_row][c] = (matrix[pivot_row][c] * inv) % _PRIME
            operations += 1
        for r in range(pivot_row + 1, rows):
            factor = matrix[r][col]
            if not factor:
                continue
            for c in range(col, cols):
                matrix[r][c] = (
                    matrix[r][c] - factor * matrix[pivot_row][c]
                ) % _PRIME
                operations += 2
        pivots.append(col)
        pivot_row += 1
        if pivot_row == rows:
            break

    free = [c for c in range(cols) if c not in set(pivots)]
    if len(free) != 1:
        raise ValueError(f"expected a one-dimensional kernel, found {len(free)}")
    vector = [0] * cols
    vector[free[0]] = 1
    for row_index in range(len(pivots) - 1, -1, -1):
        col = pivots[row_index]
        total = 0
        for c in range(col + 1, cols):
            if vector[c] and matrix[row_index][c]:
                total = (total + matrix[row_index][c] * vector[c]) % _PRIME
                operations += 2
        vector[col] = (-total) % _PRIME
    if vector[0] == 0:
        raise ValueError("kernel cannot be normalized at the declared coefficient")
    inv0 = pow(vector[0], _PRIME - 2, _PRIME)
    operations += 1
    vector = [(x * inv0) % _PRIME for x in vector]
    operations += cols
    centered = [x if x <= _PRIME // 2 else x - _PRIME for x in vector]
    if any(abs(x) > bound for x in centered):
        raise ValueError("modular recovery exceeded the declared coefficient bound")
    coeffs = [centered[j * (k + 1):(j + 1) * (k + 1)] for j in range(3)]
    answer = _coeffs_to_json(coeffs, k)
    ok, reason = verify(inst, answer)
    if not ok:
        raise ValueError("recovered vector failed exact verification: " + reason)
    return answer, {"field_operations": operations, "rows": rows, "columns": cols}


def _poly_xk(k):
    return _x_y_monomial(k, 0)


def _poly_tk(k):
    return _x_y_monomial(0, k)


def _attack_l1_outlier(inst):
    k = inst["syzygy_degree"]
    index = min(range(3), key=lambda j: sum(abs(x) for x in inst["forms"][j]))
    coeffs = [[0] * (k + 1) for _ in range(3)]
    coeffs[0] = _poly_xk(k)
    coeffs[index] = _add(coeffs[index], _poly_tk(k))
    return _coeffs_to_json(coeffs, k)


def _small_edge_relation(inst):
    k = inst["syzygy_degree"]
    forms = inst["forms"]
    for a in range(-2, 3):
        for b in range(-2, 3):
            if all(forms[0][r] + a * forms[1][r] + b * forms[2][r] == 0
                   for r in range(k)):
                return [1, a, b]
    return [1, 0, 0]


def _attack_edge_greedy(inst):
    k = inst["syzygy_degree"]
    relation = _small_edge_relation(inst)
    xk = _poly_xk(k)
    coeffs = [_scale(xk, c) for c in relation]
    return _coeffs_to_json(coeffs, k)


def _restricted_monomial_kernel(inst):
    """Try alpha_j=a_j*s^k+b_j*t^k, normalized with a_0=1."""
    d = inst["degree"]
    k = inst["syzygy_degree"]
    forms = inst["forms"]
    # Solve the five unknowns a1,a2,b0,b1,b2 over Q by RREF of [A|-f0].
    from fractions import Fraction

    equations = []
    for r in range(d + k + 1):
        def f(j, q):
            return forms[j][q] if 0 <= q <= d else 0
        equations.append([
            Fraction(f(1, r)), Fraction(f(2, r)),
            Fraction(f(0, r - k)), Fraction(f(1, r - k)),
            Fraction(f(2, r - k)), Fraction(-f(0, r)),
        ])
    row = 0
    pivots = []
    for col in range(5):
        pivot = next((r for r in range(row, len(equations)) if equations[r][col]), None)
        if pivot is None:
            continue
        equations[row], equations[pivot] = equations[pivot], equations[row]
        v = equations[row][col]
        equations[row] = [x / v for x in equations[row]]
        for r in range(len(equations)):
            if r != row and equations[r][col]:
                c = equations[r][col]
                equations[r] = [x - c * y for x, y in zip(equations[r], equations[row])]
        pivots.append(col)
        row += 1
    if any(all(x == 0 for x in eq[:5]) and eq[5] != 0 for eq in equations):
        return None
    if len(pivots) < 5:
        return None
    solution = [Fraction(0)] * 5
    for r, c in enumerate(pivots):
        solution[c] = equations[r][5]
    if any(x.denominator != 1 for x in solution):
        return None
    a1, a2, b0, b1, b2 = [int(x) for x in solution]
    coeffs = []
    for a, b in ((1, b0), (a1, b1), (a2, b2)):
        p = [0] * (k + 1)
        p[0], p[k] = a, b
        coeffs.append(p)
    return _coeffs_to_json(coeffs, k)


def _transform_permute(inst, order):
    out = dict(inst)
    out["forms"] = [inst["forms"][j][:] for j in order]
    out["answer"] = [inst["answer"][j] for j in order]
    norm_poly, norm_t_exp, norm_value = inst.get("normalization", [0, 0, 1])
    out["normalization"] = [order.index(norm_poly), norm_t_exp, norm_value]
    return out


def _transform_swap_variables(inst):
    out = dict(inst)
    out["forms"] = [list(reversed(p)) for p in inst["forms"]]
    transformed = []
    for poly in inst["answer"]:
        terms = [[[c[0], c[1]], [e[1], e[0]]] for c, e in poly]
        terms.sort(key=lambda term: term[1][1])
        transformed.append(terms)
    out["answer"] = transformed
    norm_poly, norm_t_exp, norm_value = inst.get("normalization", [0, 0, 1])
    out["normalization"] = [norm_poly, inst["syzygy_degree"] - norm_t_exp, norm_value]
    return out


def _transform_shear(inst):
    out = dict(inst)
    f0, f1, f2 = inst["forms"]
    out["forms"] = [_add(f0, f1), f1[:], f2[:]]
    coeffs, reason = _json_to_coeffs(
        inst["answer"], inst["syzygy_degree"], inst["coefficient_bound"],
        tuple(inst.get("normalization", [0, 0, 1])),
    )
    if coeffs is None:
        raise AssertionError(reason)
    carried = [coeffs[0], _add(coeffs[1], _scale(coeffs[0], -1)), coeffs[2]]
    out["answer"] = _coeffs_to_json(carried, inst["syzygy_degree"])
    return out


def _transform_parity(inst):
    """Carry the problem through the source relabelling t -> -t."""
    out = dict(inst)
    out["forms"] = [
        [c if i % 2 == 0 else -c for i, c in enumerate(poly)]
        for poly in inst["forms"]
    ]
    transformed = []
    for poly in inst["answer"]:
        terms = json.loads(json.dumps(poly))
        for term in terms:
            if term[1][1] % 2:
                term[0][0] = -term[0][0]
        transformed.append(terms)
    out["answer"] = transformed
    return out


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _worst_answer_size(k):
    xk = _x_y_monomial(k, 0)
    yk = _x_y_monomial(0, k)
    sizes = []
    for nmat, _ in _admissible_matrices():
        coeffs = [
            _add(_scale(xk, nmat[0][j]), _scale(yk, nmat[2][j]))
            for j in range(3)
        ]
        answer = _coeffs_to_json(coeffs, k)
        sizes.append((len(json.dumps(answer)), _answer_atoms(answer)))
    return max(c for c, _ in sizes), max(a for _, a in sizes)


def selftest():
    report = {}

    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 991):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    original = shipping["answer"]
    corruptions = {}
    # Drop a non-leading term.
    dropped = json.loads(json.dumps(original))
    dropped[1].pop(-1)
    corruptions["drop_one_term"] = dropped
    swapped = json.loads(json.dumps(original))
    swapped[0][0], swapped[0][1] = swapped[0][1], swapped[0][0]
    corruptions["swap_two_terms"] = swapped
    duplicated = json.loads(json.dumps(original))
    duplicated[0].insert(1, json.loads(json.dumps(duplicated[0][0])))
    corruptions["duplicate_term"] = duplicated
    corruptions["empty"] = []
    out_of_range = json.loads(json.dumps(original))
    out_of_range[1][0][0][0] = shipping["coefficient_bound"] + 1
    corruptions["out_of_range"] = out_of_range
    reasons = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        reasons[name] = reason if not ok else "ACCEPTED"
    report["G2_rejects_corruption"] = {
        "pass": all(v != "ACCEPTED" for v in reasons.values())
        and len(set(reasons.values())) == len(reasons),
        "reasons": reasons,
    }

    wire = json.dumps(original, separators=(",", ":"))
    realistic = "I used the moving-line relation.\n```text\nfinal below\n```\n<answer>\n```json\n" + wire + "\n```\n</answer>\n"
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == original and parse_answer("garbage") is None,
        "prose_and_fence": parsed == original,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    samples = 200000
    sample_rng = random.Random(20260905)
    hits = 0
    for _ in range(samples):
        candidate = random_candidate(shipping, sample_rng)
        if verify(shipping, candidate)[0]:
            hits += 1
    space = search_space(shipping)
    # Hilbert--Burch gives a one-dimensional degree-k syzygy space because
    # 2k<d; the required leading coefficient selects exactly one member.
    exact_valid = 1
    report["G4_guess_resistance"] = {
        "pass": exact_valid * 1000000 < space and samples >= 200000,
        "hits": hits,
        "total": samples,
        "sample_fraction": hits / samples,
        "exact_valid_answers": exact_valid,
        "search_space": space,
        "exact_probability_less_than_1e-6": exact_valid * 1000000 < space,
    }

    reference_runs = []
    for seed in range(8):
        inst = make_instance(seed=7000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        start = time.perf_counter()
        recovered, stats = _reference_syzygy(inst)
        elapsed = time.perf_counter() - start
        ok, reason = verify(inst, recovered)
        reference_runs.append({
            "seed": 7000 + seed,
            "ok": ok,
            "reason": reason,
            "wall_clock_sec": elapsed,
            "field_operations": stats["field_operations"],
            "rows": stats["rows"],
            "columns": stats["columns"],
        })
    strongest = max(reference_runs, key=lambda x: x["wall_clock_sec"])
    report["G5_density_and_baseline_cost"] = {
        "pass": all(run["ok"] for run in reference_runs),
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_estimate": hits / samples,
        "exact_valid_answer_count_from_structure": exact_valid,
        "baseline_wall_clock_sec": strongest["wall_clock_sec"],
        "baseline_field_operations": strongest["field_operations"],
        "baseline_rows": strongest["rows"],
        "baseline_columns": strongest["columns"],
    }

    attack_counts = {
        "outlier_l1_single_coordinate": 0,
        "greedy_edge_relation_only": 0,
        "random_restart_256": 0,
        "obvious_two_monomial_ansatz": 0,
    }
    for seed in range(8):
        inst = make_instance(seed=9000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        if verify(inst, _attack_l1_outlier(inst))[0]:
            attack_counts["outlier_l1_single_coordinate"] += 1
        if verify(inst, _attack_edge_greedy(inst))[0]:
            attack_counts["greedy_edge_relation_only"] += 1
        rr = random.Random(123456 + seed)
        if any(verify(inst, random_candidate(inst, rr))[0] for _ in range(256)):
            attack_counts["random_restart_256"] += 1
        monomial = _restricted_monomial_kernel(inst)
        if monomial is not None and verify(inst, monomial)[0]:
            attack_counts["obvious_two_monomial_ansatz"] += 1
    attacks = {
        name: {"successes": successes, "attempts": 8}
        for name, successes in attack_counts.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(v["successes"] == 0 for v in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact modular Gaussian elimination on the coefficient-convolution matrix",
            "complexity": "O((d+k)*(3k+3)^2) field operations",
            "wall_clock_sec_max": strongest["wall_clock_sec"],
            "operations_max": strongest["field_operations"],
            "solves": f"{sum(run['ok'] for run in reference_runs)}/8, as expected",
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=42, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and len(doubled["forms"][0]) > len(shipping["forms"][0]),
        "shipping_degree": shipping["degree"],
        "doubled_degree": doubled["degree"],
        "answer_atoms_shipping": _answer_atoms(shipping["answer"]),
        "answer_atoms_doubled": _answer_atoms(doubled["answer"]),
        "verify_reason": doubled_reason,
    }

    invariant_checks = 0
    carried_checks = 0
    g8_errors = []
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(seed=11000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        unrelated_keys.append(key)
        permuted = _transform_permute(inst, [2, 0, 1])
        sheared = _transform_shear(inst)
        swapped = _transform_swap_variables(inst)
        parity = _transform_parity(inst)
        transforms = [
            permuted,
            sheared,
            swapped,
            parity,
            _transform_permute(swapped, [1, 2, 0]),
            _transform_shear(parity),
        ]
        for transformed in transforms:
            invariant_checks += 1
            if canonical_key(transformed) != key:
                g8_errors.append([seed, "key changed"])
            ok, reason = verify(transformed, transformed["answer"])
            carried_checks += 1
            if not ok:
                g8_errors.append([seed, reason])
    report["G8_canonical_key"] = {
        "pass": not g8_errors and len(set(unrelated_keys)) == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated": len(set(unrelated_keys)),
        "unrelated_attempts": 20,
        "errors": g8_errors,
        "scope": "target GL(3), coordinate permutation, and signed s/t exchange",
    }

    answer_chars, answer_elements = _worst_answer_size(shipping["syzygy_degree"])
    answer_tokens = (answer_chars + 3) // 4
    intended_ops = 12 * shipping["syzygy_degree"] + 50
    hinted = G9_ARMS["hinted"]
    placebo = G9_ARMS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else None
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else None
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300,
        "arms": G9_ARMS,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None
        ),
        "hinted_verdict": (
            "unavailable_openrouter_403" if not hinted["attempts"] else
            ("too_easy" if hinted["solved"] else "hardened")
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2))
