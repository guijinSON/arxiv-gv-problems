"""Verified generator from arXiv:0709.1499, Section 2 and Proposition 2.1.

The paper gives the infinitesimal automorphism R of an upper-unitriangular
bilinear-form matrix M(a,b,c), over any commutative ring, and proves that the
generator is carried through an integral change of basis by conjugation.  This
module substitutes monomials in Z[x], hides M behind a unimodular basis, and
asks for the correspondingly conjugated polynomial generator.

Generation composes displayed identities and a structure-preserving change of
basis.  It never solves the generated coefficient-matching system.
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


TRACK = "B"


PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "3 by 3 bilinear-form matrix over Z[x]",
        "polynomial infinitesimal automorphism matrix",
    ],
    "verification_operations": [
        "exact sparse-polynomial multiplication over Z",
        "exact polynomial coefficient comparison",
        "matrix transpose and multiplication",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize the constant coefficient of the bilinear form as P^T P, "
        "undo that unimodular basis, and use the universal three-parameter identity; "
        "without the basis change one faces a large coefficient-matching system."
    ),
    "hardness_basis": (
        "Track B: generic coefficient matching can be performed exactly by "
        "evaluation, 9-variable modular elimination, and interpolation in "
        "O(D*9^3+9D^2) field operations for output degree D=3n; at shipping "
        "n=60, seed 800, it used 1,047,704 counted operations and 0.060 seconds, "
        "whereas recognizing the hidden constant-term Gram factor and the universal "
        "Section 2 identity used 259 exact coefficient operations on the reporting seed."
    ),
    "max_answer_tokens": 325,
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
        "A 3 by 3 matrix of sparse univariate polynomials over Z.  Every term is "
        "[coefficient, [exponent]], total degree is at most D=3n, coefficients "
        "have absolute value at most H, the total support has exactly K terms, "
        "and entry (2,2) is the fixed normalization polynomial q(x) supplied "
        "with the instance."
    ),
    "bounds": {
        "matrix_rows": 3,
        "matrix_columns": 3,
        "variables": 1,
        "max_degree": "D=3n",
        "coefficient_height": "instance value H",
        "total_nonzero_terms": "instance value K",
        "fixed_normalization_entry": "X[1][1]=q(x)",
    },
}


DIFFICULTY = {
    "demo": {"n": 0, "input_coeff_bound": 2, "basis_bound": 1},
    "easy": {"n": 60, "input_coeff_bound": 5, "basis_bound": 3},
    "medium": {"n": 120, "input_coeff_bound": 7, "basis_bound": 5},
    "hard": {"n": 200, "input_coeff_bound": 9, "basis_bound": 7},
}

SHIPPING_DIFFICULTY = "easy"


STRUCTURAL_HINT = (
    "The constant coefficient of the displayed bilinear form is a Gram matrix "
    "of an upper-unitriangular integral basis."
)
PLACEBO_HINT = (
    "The nine output entries use exact integer coefficients, so careful attention "
    "to matrix indices and polynomial signs is worthwhile."
)


G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 1, "attempts": 3},
    "hinted_verdict": "too_easy",
}


NOTES = r"""
The exact definition comes from Section 2: M(a,b,c) is upper unitriangular,
R is the nonzero solution of R^t M + M R = 0, and the text explicitly says a,
b,c may lie in any commutative ring.  The displayed R formula immediately
after Proposition 2.1 is the construction identity.  Proposition 2.1(b) gives
the change-of-basis law used to hide M: B=P^t M P has generator X=P^{-1}RP.

The Step 0 easy-result is in the same paragraph: R is unique up to a scalar and
is displayed explicitly.  Independently, a generic solver obtains it through a
linear coefficient system.  Track A would therefore be false.  Track B compares
exact evaluation/elimination/interpolation with spotting B(0)=P^tP, undoing P,
using the identity over abstract a,b,c, and conjugating the result back.

The source was withdrawn in version 7.  This family does not use its withdrawn
headline claim that the dominant Markoff number determines a triple.  It uses
only the Section 2 polynomial identity, rechecked from scratch by verify() on
every generated instance.  The correct parts were later incorporated into
arXiv:1208.4032, as the withdrawal notice says.

Generation draws the hidden a,b,c as nonconstant monomials from the same
distribution and draws P as an upper-unitriangular integer matrix.  Degree n
enlarges the coefficient-matching basis while the certificate remains sparse.
Conjugation by P spreads the true support across entries, defeating both the
high-degree outlier and low-degree greedy patterns; random restart samples the
exact bounded language rather than a naive superset; and the finite-cosquare
attack is rejected because that automorphism is not the normalized infinitesimal
generator.  Each failed on eight shipping seeds.  The generic reference
algorithm is reported separately because it is expected to solve on Track B.

The first implementation exposed M(a,b,c) directly.  The oracle pool recovered
its displayed formula at every tested degree from n=40 through n=505, showing
that exponent growth was not a hardness axis.  The hidden unimodular basis is
the substantive revised family, not a seed or coefficient retuning.
""".strip()


# Internal sparse polynomials are dictionaries exponent -> integer coefficient.


def _clean(p):
    return {int(e): int(c) for e, c in p.items() if c}


def _p_add(*polys):
    out = {}
    for p in polys:
        for e, c in p.items():
            out[e] = out.get(e, 0) + c
            if out[e] == 0:
                del out[e]
    return out


def _p_scale(p, k):
    return _clean({e: k * c for e, c in p.items()})


def _p_mul(p, q):
    out = {}
    for e, a in p.items():
        for f, b in q.items():
            out[e + f] = out.get(e + f, 0) + a * b
    return _clean(out)


def _p_eval(p, x, modulus=None):
    if modulus is None:
        return sum(c * pow(x, e) for e, c in p.items())
    return sum((c % modulus) * pow(x, e, modulus) for e, c in p.items()) % modulus


def _p_to_input(p):
    return [[c, e] for e, c in sorted(p.items())]


def _p_from_input(obj):
    if not isinstance(obj, list):
        raise ValueError("input polynomial is not a list")
    out = {}
    for term in obj:
        if not (isinstance(term, list) and len(term) == 2):
            raise ValueError("bad input polynomial term")
        c, e = term
        if isinstance(c, bool) or not isinstance(c, int):
            raise ValueError("bad input coefficient")
        if isinstance(e, bool) or not isinstance(e, int) or e < 0 or e in out:
            raise ValueError("bad input exponent")
        if not c:
            raise ValueError("zero input coefficient")
        out[e] = c
    return out


def _p_to_answer(p):
    return [[[c, 1], [e]] for e, c in sorted(p.items())]


def _matrix_to_answer(mat):
    return [[_p_to_answer(mat[i][j]) for j in range(3)] for i in range(3)]


def _formula_R(a, b, c):
    """The polynomial matrix displayed in Section 2 of the paper."""

    a2 = _p_mul(a, a)
    b2 = _p_mul(b, b)
    c2 = _p_mul(c, c)
    ab = _p_mul(a, b)
    ac = _p_mul(a, c)
    bc = _p_mul(b, c)
    abc = _p_mul(ab, c)
    ac2 = _p_mul(a, c2)
    a2c = _p_mul(a2, c)
    return [
        [
            _p_add(a2, b2, _p_scale(abc, -1)),
            _p_add(_p_scale(a, 2), bc, _p_scale(ac2, -1)),
            _p_add(_p_scale(b, 2), _p_scale(ac, -1)),
        ],
        [
            _p_add(bc, _p_scale(a, -2)),
            _p_add(c2, _p_scale(a2, -1)),
            _p_add(_p_scale(c, 2), _p_scale(ab, -1)),
        ],
        [
            _p_add(ac, _p_scale(b, -2)),
            _p_add(_p_scale(c, -2), _p_scale(ab, -1), a2c),
            _p_add(abc, _p_scale(b2, -1), _p_scale(c2, -1)),
        ],
    ]


def _mat_transpose(A):
    return [[A[j][i] for j in range(3)] for i in range(3)]


def _mat_mul(A, B):
    return [
        [
            _p_add(*(_p_mul(A[i][k], B[k][j]) for k in range(3)))
            for j in range(3)
        ]
        for i in range(3)
    ]


def _mat_add(A, B):
    return [[_p_add(A[i][j], B[i][j]) for j in range(3)] for i in range(3)]


def _M(a, b, c):
    z, o = {}, {0: 1}
    return [[o, a, b], [z, o, c], [z, z, o]]


def _support(mat):
    return sum(len(mat[i][j]) for i in range(3) for j in range(3))


def _height(mat):
    return max(abs(c) for row in mat for p in row for c in p.values())


def _matrix_to_input(mat):
    return [[_p_to_input(mat[i][j]) for j in range(3)] for i in range(3)]


def _matrix_from_input(obj):
    if not (isinstance(obj, list) and len(obj) == 3):
        raise ValueError("input matrix is not 3 by 3")
    out = []
    for row in obj:
        if not (isinstance(row, list) and len(row) == 3):
            raise ValueError("input matrix is not 3 by 3")
        out.append([_p_from_input(poly) for poly in row])
    return out


def _constant_matrix(values):
    return [
        [({0: int(values[i][j])} if values[i][j] else {}) for j in range(3)]
        for i in range(3)
    ]


def _upper_basis(p, q, r):
    return _constant_matrix([[1, p, q], [0, 1, r], [0, 0, 1]])


def _upper_basis_inverse(p, q, r):
    return _constant_matrix([[1, -p, p * r - q], [0, 1, -r], [0, 0, 1]])


def _assemble_instance(n, input_coeff_bound, basis_bound, form, normalization, answer_mat):
    answer = _matrix_to_answer(answer_mat)
    degree_bound = 0 if n == 0 else 3 * n
    return {
        "n": n,
        "input_coeff_bound": input_coeff_bound,
        "basis_bound": basis_bound,
        "degree_bound": degree_bound,
        "coefficient_bound": _height(answer_mat),
        "support_size": _support(answer_mat),
        "form": _matrix_to_input(form),
        "normalization": _p_to_input(normalization),
        "answer": answer,
    }


_REFERENCE_PRIME = 2305843009213693951  # 2^61-1


def make_instance(n, seed=0, **params):
    """Construct by substitution followed by a unimodular change of basis."""

    input_coeff_bound = params.pop("input_coeff_bound", 9)
    basis_bound = params.pop("basis_bound", 7)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise ValueError("n must be a nonnegative integer")
    if (
        isinstance(input_coeff_bound, bool)
        or not isinstance(input_coeff_bound, int)
        or input_coeff_bound < 1
    ):
        raise ValueError("input_coeff_bound must be a positive integer")
    if (
        isinstance(basis_bound, bool)
        or not isinstance(basis_bound, int)
        or basis_bound < 1
    ):
        raise ValueError("basis_bound must be a positive integer")

    if n == 0:
        # A hand-scale instance with a 3,584-candidate bounded language.
        a, b, c = {0: 1}, {}, {}
        M = _M(a, b, c)
        R = _formula_R(a, b, c)
        return _assemble_instance(n, input_coeff_bound, basis_bound, M, R[1][1], R)

    if n < 6:
        raise ValueError("positive n must be at least 6")

    rng = random.Random(seed)

    nonzero_basis_values = [i for i in range(-basis_bound, basis_bound + 1) if i]
    nonzero_input_values = [
        i for i in range(-input_coeff_bound, input_coeff_bound + 1) if i
    ]

    # Conditioning on one uniformly chosen label attaining degree n keeps a,b,c
    # exchangeable.  Distinct degrees suppress accidental support collisions.
    for _ in range(1000):
        degrees = rng.sample(range(max(1, n // 2), n), 2) + [n]
        rng.shuffle(degrees)
        a, b, c = (
            {degree: rng.choice(nonzero_input_values)} for degree in degrees
        )
        p, q, r = (rng.choice(nonzero_basis_values) for _ in range(3))
        P = _upper_basis(p, q, r)
        Pinv = _upper_basis_inverse(p, q, r)
        M = _M(a, b, c)
        R = _formula_R(a, b, c)
        form = _mat_mul(_mat_mul(_mat_transpose(P), M), P)
        answer_mat = _mat_mul(_mat_mul(Pinv, R), P)
        normalization = answer_mat[1][1]
        if not normalization:
            continue
        if _support(answer_mat) > 82:
            continue
        if not all(
            _p_eval(normalization, x, _REFERENCE_PRIME) != 0
            for x in range(1, 3 * n + 2)
        ):
            continue
        inst = _assemble_instance(
            n,
            input_coeff_bound,
            basis_bound,
            form,
            normalization,
            answer_mat,
        )
        if len(json.dumps(inst["answer"])) <= 2000:
            return inst
    else:
        raise RuntimeError("could not draw a bounded nondegenerate transformed instance")


def _format_poly_input(obj):
    p = _p_from_input(obj)
    if not p:
        return "0"
    chunks = []
    for e in sorted(p, reverse=True):
        c = p[e]
        mag = abs(c)
        if e == 0:
            atom = str(mag)
        elif e == 1:
            atom = "x" if mag == 1 else f"{mag}*x"
        else:
            atom = f"x^{e}" if mag == 1 else f"{mag}*x^{e}"
        if not chunks:
            chunks.append(("-" if c < 0 else "") + atom)
        else:
            chunks.append((" - " if c < 0 else " + ") + atom)
    return "".join(chunks)


def render(inst):
    """Render the complete solver-facing problem statement."""

    B = inst["form"]
    text = f"""Polynomial infinitesimal automorphism problem

Work in the univariate polynomial ring Z[x].  The following matrix B(x)
represents a bilinear form (rows are displayed from top to bottom):

  B[0] = [{_format_poly_input(B[0][0])}, {_format_poly_input(B[0][1])}, {_format_poly_input(B[0][2])}]
  B[1] = [{_format_poly_input(B[1][0])}, {_format_poly_input(B[1][1])}, {_format_poly_input(B[1][2])}]
  B[2] = [{_format_poly_input(B[2][0])}, {_format_poly_input(B[2][1])}, {_format_poly_input(B[2][2])}]

Find a 3 by 3 matrix X(x) of polynomials with integer coefficients such that

  transpose(X(x))*B(x) + B(x)*X(x) = the zero matrix,

and with the normalization

  X[1][1] = {_format_poly_input(inst['normalization'])}.

Matrix indices are zero-based, so X[1][1] is the central entry.  The answer must
have total degree at most D={inst['degree_bound']}, exactly K={inst['support_size']}
nonzero monomial terms across all nine entries, and every coefficient must have
absolute value at most H={inst['coefficient_bound']}.  A zero coefficient must
be omitted.  Terms may be listed in any order, but an exponent may occur at
most once in an entry.

Give your final answer inside <answer></answer> tags as JSON for a 3 by 3
matrix.  Encode each polynomial as a list of terms ["num/den", [exponent]];
coefficients here are integers, so den must be 1.  For example, 2*x^3-5 is
[["2/1",[3]],["-5/1",[0]]], and the zero polynomial is [].
Output nothing else inside the tags.
"""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\nHint: " + STRUCTURAL_HINT + "\n"
    elif mode == "placebo":
        text += "\nHint: " + PLACEBO_HINT + "\n"
    return text


def _answer_text(answer):
    external = []
    for row in answer:
        out_row = []
        for poly in row:
            out_row.append([[f"{term[0][0]}/{term[0][1]}", term[1]] for term in poly])
        external.append(out_row)
    return json.dumps(external, separators=(",", ":"))


def parse_answer(text):
    """Parse the tagged JSON answer, tolerating prose and Markdown fences."""

    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    payload = matches[-1].strip()
    payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
    payload = re.sub(r"\s*```$", "", payload)
    try:
        raw = json.loads(payload)
        if not (isinstance(raw, list) and len(raw) == 3):
            return None
        answer = []
        for row in raw:
            if not (isinstance(row, list) and len(row) == 3):
                return None
            out_row = []
            for poly in row:
                if not isinstance(poly, list):
                    return None
                out_poly = []
                for term in poly:
                    if not (isinstance(term, list) and len(term) == 2):
                        return None
                    coefficient, exponent = term
                    if isinstance(coefficient, str):
                        m = re.fullmatch(r"([+-]?\d+)\s*/\s*([+-]?\d+)", coefficient)
                        if not m:
                            return None
                        coefficient = [int(m.group(1)), int(m.group(2))]
                    elif (
                        isinstance(coefficient, list)
                        and len(coefficient) == 2
                        and all(isinstance(v, int) and not isinstance(v, bool) for v in coefficient)
                    ):
                        coefficient = list(coefficient)
                    else:
                        return None
                    if not (
                        isinstance(exponent, list)
                        and len(exponent) == 1
                        and isinstance(exponent[0], int)
                        and not isinstance(exponent[0], bool)
                    ):
                        return None
                    out_poly.append([coefficient, list(exponent)])
                out_row.append(out_poly)
            answer.append(out_row)
        return answer
    except (ValueError, TypeError, OverflowError):
        return None


def _validated_answer(inst, answer):
    if not (isinstance(answer, list) and len(answer) == 3):
        return None, "answer must be a 3-by-3 matrix"
    mat = []
    support = 0
    for row in answer:
        if not (isinstance(row, list) and len(row) == 3):
            return None, "answer must be a 3-by-3 matrix"
        out_row = []
        for poly in row:
            if not isinstance(poly, list):
                return None, "each matrix entry must be a polynomial term list"
            out = {}
            for term in poly:
                if not (isinstance(term, list) and len(term) == 2):
                    return None, "malformed polynomial term"
                coefficient, exponent = term
                if not (
                    isinstance(coefficient, list)
                    and len(coefficient) == 2
                    and all(isinstance(v, int) and not isinstance(v, bool) for v in coefficient)
                ):
                    return None, "coefficient must be a rational pair [num,den]"
                num, den = coefficient
                if den == 0:
                    return None, "coefficient denominator is zero"
                if den != 1:
                    return None, "coefficients must be integers (denominator 1)"
                if num == 0:
                    return None, "zero coefficient terms must be omitted"
                if abs(num) > inst["coefficient_bound"]:
                    return None, "coefficient exceeds the declared height bound"
                if not (
                    isinstance(exponent, list)
                    and len(exponent) == 1
                    and isinstance(exponent[0], int)
                    and not isinstance(exponent[0], bool)
                ):
                    return None, "monomial exponent must be a one-integer list"
                e = exponent[0]
                if e < 0 or e > inst["degree_bound"]:
                    return None, "monomial exponent is outside 0..D"
                if e in out:
                    return None, "polynomial contains a duplicate exponent"
                out[e] = num
                support += 1
            out_row.append(out)
        mat.append(out_row)
    if support != inst["support_size"]:
        return None, f"wrong support size: expected {inst['support_size']} nonzero terms"
    return mat, "ok"


def _numeric_matrix(mat, x, modulus):
    return [[_p_eval(mat[i][j], x, modulus) for j in range(3)] for i in range(3)]


def _numeric_residual_zero(M, R, modulus):
    for i in range(3):
        for j in range(3):
            total = 0
            for k in range(3):
                total += R[k][i] * M[k][j] + M[i][k] * R[k][j]
            if total % modulus:
                return False
    return True


def verify(inst, answer):
    """Check any bounded witness exactly, without consulting inst['answer']."""

    R, reason = _validated_answer(inst, answer)
    if R is None:
        return False, reason
    try:
        form = _matrix_from_input(inst["form"])
        normalization = _p_from_input(inst["normalization"])
    except (KeyError, TypeError, ValueError) as exc:
        return False, "malformed instance data: " + str(exc)
    if R[1][1] != normalization:
        return False, "central entry does not equal the supplied normalization q(x)"

    # Two very cheap necessary evaluations reject essentially every random
    # candidate before exact expansion.  Passing them never causes acceptance.
    for x, prime in ((1, 1000003), (-1, 1000033)):
        Mn = _numeric_matrix(form, x, prime)
        Rn = _numeric_matrix(R, x, prime)
        if not _numeric_residual_zero(Mn, Rn, prime):
            return False, "matrix identity fails at an exact modular evaluation"

    residual = _mat_add(_mat_mul(_mat_transpose(R), form), _mat_mul(form, R))
    if any(residual[i][j] for i in range(3) for j in range(3)):
        return False, "polynomial matrix identity is not zero"
    return True, "ok"


def _monomial_count(D):
    return D + 1


def _fixed_support(inst):
    return len(_p_from_input(inst["normalization"]))


def search_space(inst):
    """Exact size of the structure-aware bounded certificate language."""

    D = inst["degree_bound"]
    free_positions = 8 * _monomial_count(D)
    free_terms = inst["support_size"] - _fixed_support(inst)
    H = inst["coefficient_bound"]
    if free_terms < 0 or free_terms > free_positions:
        return 0
    return math.comb(free_positions, free_terms) * pow(2 * H, free_terms)


def _free_entries():
    return [(i, j) for i in range(3) for j in range(3) if (i, j) != (1, 1)]


def random_candidate(inst, rng):
    """Uniformly sample after enforcing shape, bounds, support and normalization."""

    D = inst["degree_bound"]
    H = inst["coefficient_bound"]
    entries = _free_entries()
    total_positions = len(entries) * (D + 1)
    remaining = inst["support_size"] - _fixed_support(inst)
    positions = rng.sample(range(total_positions), remaining)
    mat = [[{} for _ in range(3)] for _ in range(3)]
    mat[1][1] = _p_from_input(inst["normalization"])
    for pos in positions:
        entry_index, exponent = divmod(pos, D + 1)
        i, j = entries[entry_index]
        raw = rng.randrange(2 * H)
        coefficient = raw + 1 if raw < H else -(raw - H + 1)
        mat[i][j][exponent] = coefficient
    return _matrix_to_answer(mat)


def enumerate_all(inst):
    """Brute-force the exact bounded language only when it is genuinely small."""

    space = search_space(inst)
    if space > 100000:
        return None
    D = inst["degree_bound"]
    H = inst["coefficient_bound"]
    entries = _free_entries()
    positions = list(range(len(entries) * (D + 1)))
    remaining = inst["support_size"] - _fixed_support(inst)
    values = list(range(-H, 0)) + list(range(1, H + 1))
    norm = _p_from_input(inst["normalization"])
    valid = 0
    for support in itertools.combinations(positions, remaining):
        for coefficients in itertools.product(values, repeat=remaining):
            mat = [[{} for _ in range(3)] for _ in range(3)]
            mat[1][1] = dict(norm)
            for pos, coefficient in zip(support, coefficients):
                entry_index, exponent = divmod(pos, D + 1)
                i, j = entries[entry_index]
                mat[i][j][exponent] = coefficient
            if verify(inst, _matrix_to_answer(mat))[0]:
                valid += 1
    return valid


def _poly_tuple(p):
    return tuple(sorted(p.items()))


def _key_variants(a, b, c):
    variants = []
    for x_sign in (1, -1):
        ax = {e: v * (x_sign if e % 2 else 1) for e, v in a.items()}
        bx = {e: v * (x_sign if e % 2 else 1) for e, v in b.items()}
        cx = {e: v * (x_sign if e % 2 else 1) for e, v in c.items()}
        for sa, sb, sc in ((1, 1, 1), (-1, -1, 1), (-1, 1, -1), (1, -1, -1)):
            signed = (_p_scale(ax, sa), _p_scale(bx, sb), _p_scale(cx, sc))
            variants.append(tuple(_poly_tuple(p) for p in signed))
            variants.append(tuple(_poly_tuple(p) for p in (signed[2], signed[1], signed[0])))
    return variants


def _recover_hidden_basis(form):
    """Recover P from form(0)=P^T P for upper-unitriangular P."""

    constant = [[form[i][j].get(0, 0) for j in range(3)] for i in range(3)]
    if constant[0][0] != 1:
        raise ValueError("constant Gram matrix has unexpected leading entry")
    p = constant[0][1]
    q = constant[0][2]
    r = constant[1][2] - p * q
    P = _upper_basis(p, q, r)
    gram = _mat_mul(_mat_transpose(P), P)
    expected = _constant_matrix(constant)
    if gram != expected:
        raise ValueError("constant coefficient is not the required Gram matrix")
    return P, _upper_basis_inverse(p, q, r), (p, q, r)


def _underlying_parameters(inst):
    form = _matrix_from_input(inst["form"])
    if inst.get("n") == 0:
        return form[0][1], form[0][2], form[1][2]
    _, Pinv, _ = _recover_hidden_basis(form)
    M = _mat_mul(_mat_mul(_mat_transpose(Pinv), form), Pinv)
    one = {0: 1}
    if [M[i][i] for i in range(3)] != [one, one, one]:
        raise ValueError("recovered form is not unitriangular")
    if any(M[i][j] for i in range(3) for j in range(i)):
        raise ValueError("recovered form is not unitriangular")
    return M[0][1], M[0][2], M[1][2]


def canonical_key(inst):
    """Strip the hidden basis, then canonicalize x sign and a/c reversal."""

    a, b, c = _underlying_parameters(inst)
    canonical = min(_key_variants(a, b, c))
    payload = repr(canonical).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def escalate(params):
    """Grow degree and the hidden-basis range while certificate support stays fixed."""

    out = dict(params)
    n = out.get("n")
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        return None
    out["n"] = max(n + 1, (3 * n) // 2)
    out["basis_bound"] = min(31, int(out.get("basis_bound", 7)) + 2)
    return out


# --- Reference algorithm and audit attacks ---------------------------------


def _numeric_system(M, normalization, prime, counter):
    rows = []
    for i in range(3):
        for j in range(3):
            row = [0] * 10
            for k in range(3):
                row[3 * k + i] = (row[3 * k + i] + M[k][j]) % prime
                row[3 * k + j] = (row[3 * k + j] + M[i][k]) % prime
                counter[0] += 2
            rows.append(row)
    row = [0] * 10
    row[4] = 1
    row[9] = normalization % prime
    rows.append(row)

    pivot_row = 0
    pivot_for = {}
    for col in range(9):
        pivot = next((r for r in range(pivot_row, len(rows)) if rows[r][col]), None)
        if pivot is None:
            continue
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        inv = pow(rows[pivot_row][col], prime - 2, prime)
        counter[0] += 2 * prime.bit_length()
        for j in range(col, 10):
            rows[pivot_row][j] = rows[pivot_row][j] * inv % prime
            counter[0] += 1
        for r in range(len(rows)):
            if r == pivot_row or not rows[r][col]:
                continue
            factor = rows[r][col]
            for j in range(col, 10):
                rows[r][j] = (rows[r][j] - factor * rows[pivot_row][j]) % prime
                counter[0] += 2
        pivot_for[col] = pivot_row
        pivot_row += 1
    if len(pivot_for) != 9:
        raise ArithmeticError("pointwise system is singular")
    for row in rows:
        if not any(row[:9]) and row[9]:
            raise ArithmeticError("pointwise system is inconsistent")
    return [rows[pivot_for[col]][9] for col in range(9)]


def _interpolate_consecutive(value_columns, prime, counter):
    """Interpolate values at x=1,2,...,D+1 in the Newton basis."""
    D = len(value_columns[0]) - 1
    inverses = [0, 1]
    for k in range(2, D + 1):
        inverses.append(pow(k, prime - 2, prime))
        counter[0] += 2 * prime.bit_length()
    newton = []
    for values in value_columns:
        dd = list(values)
        coeffs = [dd[0]]
        for order in range(1, D + 1):
            inv = inverses[order]
            for i in range(D - order + 1):
                dd[i] = (dd[i + 1] - dd[i]) * inv % prime
                counter[0] += 2
            coeffs.append(dd[0])
        newton.append(coeffs)

    results = [[0] * (D + 1) for _ in range(9)]
    basis = [1]
    for k in range(D + 1):
        for entry in range(9):
            coefficient = newton[entry][k]
            for j, value in enumerate(basis):
                results[entry][j] = (results[entry][j] + coefficient * value) % prime
                counter[0] += 2
        if k < D:
            new_basis = [0] * (len(basis) + 1)
            for j, value in enumerate(basis):
                new_basis[j + 1] = (new_basis[j + 1] + value) % prime
                new_basis[j] = (new_basis[j] - (k + 1) * value) % prime
                counter[0] += 3
            basis = new_basis
    return results


def _reference_solve(inst):
    """Generic exact evaluation/elimination/interpolation, not the planted formula."""

    prime = _REFERENCE_PRIME
    if 2 * inst["coefficient_bound"] >= prime:
        raise ArithmeticError("reference prime is too small for coefficient lifting")
    form = _matrix_from_input(inst["form"])
    norm = _p_from_input(inst["normalization"])
    D = inst["degree_bound"]
    counter = [0]
    columns = [[] for _ in range(9)]
    for x in range(1, D + 2):
        values_at_x = _numeric_matrix(form, x, prime)
        nv = _p_eval(norm, x, prime)
        counter[0] += sum(
            2 * max(1, e.bit_length())
            for p in [poly for row in form for poly in row] + [norm]
            for e in p
        )
        values = _numeric_system(values_at_x, nv, prime, counter)
        for i, value in enumerate(values):
            columns[i].append(value)
    dense = _interpolate_consecutive(columns, prime, counter)
    mat = [[{} for _ in range(3)] for _ in range(3)]
    for index, coeffs in enumerate(dense):
        p = {}
        for exponent, coefficient in enumerate(coeffs):
            if coefficient > prime // 2:
                coefficient -= prime
            if coefficient:
                p[exponent] = coefficient
        mat[index // 3][index % 3] = p
    return _matrix_to_answer(mat), counter[0]


def _candidate_from_positions(inst, high):
    D, H = inst["degree_bound"], inst["coefficient_bound"]
    entries = _free_entries()
    remaining = inst["support_size"] - _fixed_support(inst)
    positions = range(len(entries) * (D + 1) - 1, -1, -1) if high else range(len(entries) * (D + 1))
    chosen = list(itertools.islice(positions, remaining))
    mat = [[{} for _ in range(3)] for _ in range(3)]
    norm = _p_from_input(inst["normalization"])
    mat[1][1] = norm
    lead_sign = 1 if sum(norm.values()) >= 0 else -1
    coefficient = max(-H, min(H, lead_sign))
    for pos in chosen:
        entry_index, exponent = divmod(pos, D + 1)
        i, j = entries[entry_index]
        mat[i][j][exponent] = coefficient
    return _matrix_to_answer(mat)


def _finite_automorphism_attack(inst):
    M = _matrix_from_input(inst["form"])
    Minv = [[{} for _ in range(3)] for _ in range(3)]
    for i in range(3):
        for j in range(3):
            rows = [r for r in range(3) if r != i]
            cols = [c for c in range(3) if c != j]
            minor = _p_add(
                _p_mul(M[rows[0]][cols[0]], M[rows[1]][cols[1]]),
                _p_scale(_p_mul(M[rows[0]][cols[1]], M[rows[1]][cols[0]]), -1),
            )
            Minv[j][i] = _p_scale(minor, -1 if (i + j) % 2 else 1)
    H = _mat_mul(Minv, _mat_transpose(M))
    S = [[_p_add(H[i][j], ({0: -1} if i == j else {})) for j in range(3)] for i in range(3)]
    return _matrix_to_answer(S)


def _transform_poly_x(p, sign):
    return {e: c * (sign if e % 2 else 1) for e, c in p.items()}


def _transform_for_g8(inst, x_sign, basis_change, swap, reverse_terms=False):
    form = _matrix_from_input(inst["form"])
    X, reason = _validated_answer(inst, inst["answer"])
    if X is None:
        raise AssertionError(reason)
    P, Pinv, _ = _recover_hidden_basis(form)
    M = _mat_mul(_mat_mul(_mat_transpose(Pinv), form), Pinv)
    R = _mat_mul(_mat_mul(P, X), Pinv)
    M = [[_transform_poly_x(M[i][j], x_sign) for j in range(3)] for i in range(3)]
    R = [[_transform_poly_x(R[i][j], x_sign) for j in range(3)] for i in range(3)]
    if swap:
        M = [[M[2 - j][2 - i] for j in range(3)] for i in range(3)]
        R = [[_p_scale(R[2 - i][2 - j], -1) for j in range(3)] for i in range(3)]
    U = _upper_basis(*basis_change)
    P2 = _mat_mul(P, U)
    p2 = P2[0][1].get(0, 0)
    q2 = P2[0][2].get(0, 0)
    r2 = P2[1][2].get(0, 0)
    P2inv = _upper_basis_inverse(p2, q2, r2)
    form2 = _mat_mul(_mat_mul(_mat_transpose(P2), M), P2)
    X2 = _mat_mul(_mat_mul(P2inv, R), P2)
    out = _assemble_instance(
        inst["n"],
        inst["input_coeff_bound"],
        inst["basis_bound"],
        form2,
        X2[1][1],
        X2,
    )
    if reverse_terms:
        out["form"] = [
            [list(reversed(poly)) for poly in row] for row in out["form"]
        ]
        out["normalization"] = list(reversed(out["normalization"]))
        out["answer"] = [[list(reversed(poly)) for poly in row] for row in out["answer"]]
    return out


def _formula_operation_count_polys(a, b, c):
    """Count coefficient arithmetic in the universal sparse formula."""

    # Nine products used with common-subexpression elimination.
    product_pairs = [(a, a), (b, b), (c, c), (a, b), (a, c), (b, c)]
    products = [_p_mul(p, q) for p, q in product_pairs]
    a2, b2, c2, ab, ac, bc = products
    product_pairs += [(ab, c), (a, c2), (a2, c)]
    multiplications = sum(len(p) * len(q) for p, q in product_pairs)
    # Scaling and summing the displayed entries, counted conservatively once per
    # input term touched.  This is an operation count, not a wall-time claim.
    additions_and_scales = (
        len(a2) + len(b2) + len(_p_mul(ab, c))
        + 2 * len(a) + len(bc) + len(_p_mul(a, c2))
        + 2 * len(b) + len(ac)
        + len(bc) + 2 * len(a)
        + len(c2) + len(a2)
        + 2 * len(c) + len(ab)
        + len(ac) + 2 * len(b)
        + 2 * len(c) + len(ab) + len(_p_mul(a2, c))
        + len(_p_mul(ab, c)) + len(b2) + len(c2)
    )
    return multiplications + additions_and_scales


def _p_mul_count(p, q):
    out = {}
    operations = 0
    for e, a in p.items():
        for f, b in q.items():
            operations += 1
            if e + f in out:
                operations += 1
            out[e + f] = out.get(e + f, 0) + a * b
    return _clean(out), operations


def _mat_mul_count(A, B):
    out = [[{} for _ in range(3)] for _ in range(3)]
    operations = 0
    for i in range(3):
        for j in range(3):
            pieces = []
            for k in range(3):
                product, used = _p_mul_count(A[i][k], B[k][j])
                operations += used
                pieces.append(product)
            total = {}
            for piece in pieces:
                for exponent, coefficient in piece.items():
                    if exponent in total:
                        operations += 1
                    total[exponent] = total.get(exponent, 0) + coefficient
            out[i][j] = _clean(total)
    return out, operations


def _compact_solve(inst):
    """Execute the intended constant-Gram change of variables exactly."""

    form = _matrix_from_input(inst["form"])
    if inst.get("n") == 0:
        R = _formula_R(form[0][1], form[0][2], form[1][2])
        return _matrix_to_answer(R), _formula_operation_count_polys(
            form[0][1], form[0][2], form[1][2]
        )
    P, Pinv, (p, q, r) = _recover_hidden_basis(form)
    left, op1 = _mat_mul_count(_mat_transpose(Pinv), form)
    M, op2 = _mat_mul_count(left, Pinv)
    a, b, c = M[0][1], M[0][2], M[1][2]
    R = _formula_R(a, b, c)
    left, op3 = _mat_mul_count(Pinv, R)
    X, op4 = _mat_mul_count(left, P)
    # p*q, subtraction for r, p*r, and subtraction for P^{-1}.
    scalar_operations = 4
    operations = (
        scalar_operations
        + op1
        + op2
        + _formula_operation_count_polys(a, b, c)
        + op3
        + op4
    )
    return _matrix_to_answer(X), operations


def _count_atoms(obj):
    if isinstance(obj, dict):
        return sum(_count_atoms(v) for v in obj.values())
    if isinstance(obj, list):
        return sum(_count_atoms(v) for v in obj)
    return 1


def selftest():
    report = {
        "paper": "arXiv:0709.1499",
        "family": "polynomial infinitesimal automorphism matrix",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1
    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 1729):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok or json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {"pass": not failures, "checks": checks, "failures": failures}

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])

    # G2
    corruptions = {}
    drop = json.loads(json.dumps(shipping["answer"]))
    target = next((p for i, row in enumerate(drop) for j, p in enumerate(row) if (i, j) != (1, 1) and p), None)
    target.pop()
    candidates = {"drop_one": drop}
    swap = json.loads(json.dumps(shipping["answer"]))
    swap[1][1], swap[0][0] = swap[0][0], swap[1][1]
    candidates["swap_entries"] = swap
    duplicate = json.loads(json.dumps(shipping["answer"]))
    poly = next(p for row in duplicate for p in row if p)
    poly.append(json.loads(json.dumps(poly[0])))
    candidates["duplicate_term"] = duplicate
    candidates["empty"] = []
    out_of_range = json.loads(json.dumps(shipping["answer"]))
    term = next(t for row in out_of_range for p in row for t in p)
    term[0][0] = shipping["coefficient_bound"] + 1
    candidates["out_of_range"] = out_of_range
    for name, candidate in candidates.items():
        ok, reason = verify(shipping, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = {v["reason"] for v in corruptions.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in corruptions.values()) and len(reasons) == len(corruptions),
        "attempts": len(corruptions),
        "distinct_reasons": len(reasons),
        "cases": corruptions,
    }

    # G3
    realistic = "Here is the matrix.\n```json\n<answer>\n" + _answer_text(shipping["answer"]) + "\n</answer>\n```\nDone."
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"],
        "parsed_equals_answer": parsed == shipping["answer"],
        "surrounding_prose_and_fence": True,
    }

    # G4
    guess_rng = random.Random(8675309)
    total = 200000
    hits = 0
    t0 = time.perf_counter()
    for _ in range(total):
        if verify(shipping, random_candidate(shipping, guess_rng))[0]:
            hits += 1
    guess_time = time.perf_counter() - t0
    report["G4_guess_resistance"] = {
        "pass": hits / total < 1e-6,
        "hits": hits,
        "total": total,
        "observed_probability": hits / total,
        "candidate_space": search_space(shipping),
        "candidate_space_bits": search_space(shipping).bit_length() - 1,
        "prior": "uniform K-support bounded coefficients after fixing the stated central entry",
        "wall_clock_sec": round(guess_time, 6),
    }

    # G5 and G6 share the measured reference runs.
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    attack_seeds = list(range(800, 808))
    attacks = {
        "outlier_high_degree_support": {"successes": 0, "attempts": 0, "wall_clock_sec": 0.0},
        "greedy_low_degree_support": {"successes": 0, "attempts": 0, "wall_clock_sec": 0.0},
        "random_restart_256": {"successes": 0, "attempts": 0, "wall_clock_sec": 0.0},
        "in_context_finite_automorphism": {"successes": 0, "attempts": 0, "wall_clock_sec": 0.0},
    }
    reference_ops = []
    reference_times = []
    reference_success = 0
    random_checks = 0
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        attack_candidates = {
            "outlier_high_degree_support": [_candidate_from_positions(inst, True)],
            "greedy_low_degree_support": [_candidate_from_positions(inst, False)],
            "random_restart_256": [random_candidate(inst, random.Random(seed * 1009 + i)) for i in range(256)],
            "in_context_finite_automorphism": [_finite_automorphism_attack(inst)],
        }
        for name, options in attack_candidates.items():
            start = time.perf_counter()
            success = any(verify(inst, candidate)[0] for candidate in options)
            attacks[name]["wall_clock_sec"] += time.perf_counter() - start
            attacks[name]["attempts"] += 1
            attacks[name]["successes"] += int(success)
            if name == "random_restart_256":
                random_checks += len(options)
        start = time.perf_counter()
        recovered, operations = _reference_solve(inst)
        reference_times.append(time.perf_counter() - start)
        reference_ops.append(operations)
        reference_success += int(verify(inst, recovered)[0])
    for result in attacks.values():
        result["wall_clock_sec"] = round(result["wall_clock_sec"], 6)

    report["G5_density_and_baseline_cost"] = {
        "pass": demo_count == 1 and reference_success == len(attack_seeds),
        "shipping_sample_hits": hits,
        "shipping_sample_total": total,
        "shipping_solution_density": hits / total,
        "demo_candidate_space": search_space(demo),
        "demo_exact_valid_answers": demo_count,
        "demo_exact_density": demo_count / search_space(demo),
        "strongest_failing_attack": "random_restart_256",
        "baseline_candidate_checks": random_checks,
        "baseline_wall_clock_sec": attacks["random_restart_256"]["wall_clock_sec"],
        "reference_operation_count_shipping_seed_800": reference_ops[0],
        "reference_wall_clock_sec_shipping_seed_800": round(reference_times[0], 6),
    }
    report["G6_adversary_panel"] = {
        "pass": all(v["successes"] == 0 and v["attempts"] >= 8 for v in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "modular evaluation, 9-variable Gaussian elimination, and Newton interpolation",
            "complexity": "O(D*9^3 + 9D^2) finite-field operations, D=3n",
            "operations": sum(reference_ops),
            "per_instance_operations": reference_ops,
            "wall_clock_sec": round(sum(reference_times), 6),
            "per_instance_wall_clock_sec": [round(v, 6) for v in reference_times],
            "solves": f"{reference_success}/{len(attack_seeds)}, as expected",
        },
    }

    # G7
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(shipping),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_candidate_space_bits": search_space(shipping).bit_length() - 1,
        "doubled_candidate_space_bits": search_space(doubled).bit_length() - 1,
        "doubled_verify_reason": doubled_reason,
    }

    # G8
    invariance_checks = 0
    real_checks = 0
    g8_failures = []
    distinct_keys = []
    basis_changes = ((0, 0, 0), (1, 0, 0), (0, -1, 1), (1, -1, 1))
    for seed in range(20):
        inst = make_instance(seed=10000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        original_key = canonical_key(inst)
        distinct_keys.append(original_key)
        for x_sign in (1, -1):
            for basis_change in basis_changes:
                for swap_flag in (False, True):
                    for reverse_terms in (False, True):
                        transformed = _transform_for_g8(
                            inst, x_sign, basis_change, swap_flag, reverse_terms
                        )
                        invariance_checks += 1
                        if canonical_key(transformed) != original_key:
                            g8_failures.append({"seed": seed, "kind": "key_changed"})
                        ok, reason = verify(transformed, transformed["answer"])
                        real_checks += 1
                        if not ok:
                            g8_failures.append({"seed": seed, "kind": "not_real", "reason": reason})
    unrelated_distinct = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and unrelated_distinct == 20,
        "invariance_checks": invariance_checks,
        "real_transformations_verified": real_checks,
        "unrelated_attempts": 20,
        "unrelated_distinct_keys": unrelated_distinct,
        "failures": g8_failures,
        "symmetries": "term order, x sign, upper-unitriangular basis changes, and a/c transpose reversal",
    }

    # G9(c); oracle arms are filled from script-owned transcripts after those runs.
    size_samples = [
        make_instance(seed=s, **DIFFICULTY[SHIPPING_DIFFICULTY])["answer"]
        for s in range(50)
    ]
    char_sizes = [len(json.dumps(a)) for a in size_samples]
    atom_sizes = [_count_atoms(a) for a in size_samples]
    answer_chars = len(json.dumps(shipping["answer"]))
    answer_atoms = _count_atoms(shipping["answer"])
    answer_tokens = math.ceil(answer_chars / 4)
    compact_answer, compact_ops = _compact_solve(shipping)
    compact_ok, compact_reason = verify(shipping, compact_answer)
    arms = {
        key: {"solved": value["solved"], "attempts": value["attempts"]}
        for key, value in G9_ORACLE_RESULTS.items()
        if key in ("bare", "hinted", "placebo")
    }
    hinted = arms["hinted"]["solved"]
    placebo = arms["placebo"]["solved"]
    difference = None
    if isinstance(hinted, int) and isinstance(placebo, int) and arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        difference = hinted / arms["hinted"]["attempts"] - placebo / arms["placebo"]["attempts"]
    within_caps = (
        max(char_sizes) <= 2000
        and max(atom_sizes) <= 256
        and compact_ops <= 300
        and compact_ok
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": difference,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": compact_ops,
        "intended_route_verify_reason": compact_reason,
        "worst_case_answer_chars": max(char_sizes),
        "worst_case_answer_tokens": math.ceil(max(char_sizes) / 4),
        "worst_case_answer_elements": max(atom_sizes),
        "within_caps": within_caps,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [v for k, v in report.items() if k.startswith("G") and k[1:2].isdigit()]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
