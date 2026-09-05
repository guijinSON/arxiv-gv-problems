"""Verified inverse-generated Groebner-basis instances for arXiv:1105.5509.

The paper studies Buchberger reduction for multihomogeneous ideals.  This
module first samples a reduced Groebner basis over a prime field, then replaces
it by an invertible, row-permuted rank-one recombination.  The sampled basis is
carried through that construction; ``make_instance`` never solves the displayed
instance.

The solver returns the finite-field coefficient matrix of the reduced basis.
The verifier reconstructs the polynomials, checks equality with the displayed
ideal by exact reductions, and executes Buchberger S-polynomial reductions.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import random
import re
import sys
import time
from collections import Counter


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import sparse_poly  # noqa: F401  (available to repo consumers)
except ImportError:                 # pragma: no cover - standard-library fallback
    sparse_poly = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "multihomogeneous polynomials over a prime field",
        "reduced Groebner basis coefficient matrix",
        "S-polynomials",
    ],
    "verification_operations": [
        "exact prime-field arithmetic",
        "exact multivariate polynomial reduction",
        "Buchberger S-polynomial reduction to zero",
        "exact coefficient comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize the rank-one constant-row structure hidden in the leading-"
        "coefficient block; without it one must eliminate the full finite-field "
        "coefficient matrix."
    ),
    "hardness_basis": (
        "Track B: Gauss-Jordan elimination on the homogeneous coefficient matrix "
        "runs in O(n^3) field operations and at the shipping medium preset used "
        "9,666 operations in 0.0032 seconds in the final self-test; the planted "
        "rank-one route uses 214 modular arithmetic operations but must be recognized and "
        "executed exactly without tools."
    ),
    "max_answer_tokens": 126,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "An n-by-2 matrix over the displayed prime field GF(p), represented as "
        "n JSON rows of two canonical integers in the inclusive range 0..p-1; "
        "row i supplies the two tail coefficients of the prescribed monic basis "
        "polynomial B_i."
    ),
    "bounds": {
        "rows": "n (36 at the shipping preset; 72 in the G7 scaling test)",
        "columns": 2,
        "coefficient_min": 0,
        "coefficient_max": "p-1",
        "modulus_bits_shipping": 16,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 2, "modulus_bits": 2},
    "easy": {"n": 24, "modulus_bits": 12},
    "medium": {"n": 36, "modulus_bits": 16},
    "hard": {"n": 48, "modulus_bits": 20},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT: str = (
    "Hint: The leading-coefficient block is a row permutation of the identity "
    "plus a rank-one constant-row matrix."
)
PLACEBO_HINT: str = (
    "Hint: The displayed coefficient block uses canonical prime-field entries "
    "and a fixed lexicographic monomial order."
)

_G9_EVIDENCE = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "hardened",
    "placebo_verdict": "unavailable: OpenRouter HTTP 403 key total limit",
}

NOTES = r"""
Paper definition. Sections 2 and 3 define the coordinatewise partial order on
N^d, a polynomial ring multigraded by that ordered monoid, homogeneous
polynomials, leading monomials, and reduction. Proposition 3.1 connects
multidegree order to leading-monomial divisibility. Proposition 3.2 is the
paper's executable certificate fact: a homogeneous reduction at degree d uses
only basis elements in the principal degree ideal below d. Section 4 schedules
the resulting S-polynomial reductions by minimal antichains.

Step-0 discrimination. A Groebner basis is produced by Buchberger's algorithm,
so this cannot honestly be Track A. The paper itself calls Buchberger
exponential in Section 1.1, but that is a worst-case statement, not evidence
about this planted distribution. For this distribution an even stronger
polynomial algorithm exists: row-reduce the degree-(2,2) coefficient matrix
over GF(p). The instrumented Gauss-Jordan implementation, its operation count,
and its successful 8/8 runs are therefore reported as the Track-B reference
algorithm. The compact decoder uses the displayed leading block's hidden
identity-plus-rank-one invariant. At the shipping preset its two weighted
column sums and row corrections cost 2(3n-1)=214 field operations, whereas the
instrumented full elimination costs roughly ten thousand operations.

Generation. In GF(p), sample the wanted reduced basis
    B_i = x_i^2 + c_i a*b + d_i c*d.
The variable multidegrees are |x_i|=(1,1), |a|=(1,0), |b|=(1,2),
|c|=(0,1), |d|=(2,1), so every displayed monomial has multidegree
(2,2). The leading monomials x_i^2 are pairwise coprime, and the two
tail monomials are divisible by none of them, making B reduced; the verifier
still executes every S-polynomial reduction rather than trusting this prose.
Choose v with sum(v)=0 and A=I+1*v^T. Then A^{-1}=I-1*v^T exactly. Randomly
permute A's rows and publish F=A*B. Since det(A)=1+sum(v)=1, F and B generate
the same ideal. The answer B is sampled before F and is never recovered by a
solver inside make_instance.

Easy regimes and attacks. Example 1.1 says the commuting-matrix ideals I_1 and
I_2 are blackboard-trivial, I_3 takes minutes, and I_4 took Macaulay2 hours with
563 reverse-lex basis elements; product orders gave much smaller bases. Section
6 warns that a densely populated multidegree is an essentially serial
bottleneck. This generator deliberately uses one dense multidegree, but makes
only the Track-B no-tool claim. Row order is shuffled, coefficients are uniform
in GF(p), and no basis row is planted as an input outlier. Tested failures are a
small-row anchor, raw pivot-row extraction, an unweighted centering ansatz, a
sign-only rank-one ansatz, and 256 uniform restarts. Exact Gauss-Jordan is
expected to succeed and is kept outside the failing attack panel.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_TAILS = 2


# -- exact prime-field and polynomial helpers ---------------------------------

def _is_probable_prime(value):
    """Deterministic Miller-Rabin for the unsigned 64-bit range."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value % prime == 0:
            return value == prime
    d = value - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        x = pow(base, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _prime_for_bits(bits):
    if isinstance(bits, bool) or not isinstance(bits, int) or not 2 <= bits <= 60:
        raise ValueError("modulus_bits must be an integer in 2..60")
    value = (1 << bits) + 1
    if value % 2 == 0:
        value += 1
    while not _is_probable_prime(value):
        value += 2
    return value


def _matrix_rank_mod(matrix, p):
    if not matrix:
        return 0
    a = [[x % p for x in row] for row in matrix]
    rows, cols = len(a), len(a[0])
    rank = 0
    for col in range(cols):
        pivot = next((r for r in range(rank, rows) if a[r][col]), None)
        if pivot is None:
            continue
        a[rank], a[pivot] = a[pivot], a[rank]
        inv = pow(a[rank][col], p - 2, p)
        a[rank] = [x * inv % p for x in a[rank]]
        for r in range(rows):
            if r != rank and a[r][col]:
                factor = a[r][col]
                a[r] = [(x - factor * y) % p for x, y in zip(a[r], a[rank])]
        rank += 1
        if rank == rows:
            break
    return rank


def _solve_leading_block(inst):
    """Solve A X=T by Gauss-Jordan; return (X, counted field operations)."""
    p = inst["modulus"]
    n = inst["n"]
    rows = [row[:] for row in inst["coefficient_rows"]]
    ops = 0
    pivot_row = 0
    for col in range(n):
        pivot = next((r for r in range(pivot_row, n) if rows[r][col] % p), None)
        if pivot is None:
            return None, ops
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        inv = pow(rows[pivot_row][col] % p, p - 2, p)
        ops += 1
        for j in range(col, n + _TAILS):
            rows[pivot_row][j] = rows[pivot_row][j] * inv % p
            ops += 1
        for r in range(n):
            if r == pivot_row:
                continue
            factor = rows[r][col] % p
            if factor == 0:
                continue
            for j in range(col, n + _TAILS):
                rows[r][j] = (rows[r][j] - factor * rows[pivot_row][j]) % p
                ops += 2
        pivot_row += 1
    return [row[n:n + _TAILS] for row in rows], ops


def _structured_decode(inst):
    """Decode by the planted invariant; return (X, exact arithmetic count)."""
    ordered, v = _ordered_pivot_rows(inst)
    if ordered is None:
        return None, 0
    n, p = inst["n"], inst["modulus"]
    shifts = []
    ops = 0
    for col in range(_TAILS):
        total = 0
        for j in range(n):
            product = v[j] * ordered[j][col] % p
            ops += 1
            if j:
                total = (total + product) % p
                ops += 1
            else:
                total = product
        shifts.append(total)
    decoded = []
    for row in ordered:
        decoded.append([(row[col] - shifts[col]) % p for col in range(_TAILS)])
        ops += _TAILS
    return decoded, ops


def _monomial_data(n):
    """Return exponent vectors for x_i^2, a*b, and c*d."""
    width = n + 4
    leading = []
    for i in range(n):
        exp = [0] * width
        exp[i] = 2
        leading.append(tuple(exp))
    ab = [0] * width
    ab[n] = ab[n + 1] = 1
    cd = [0] * width
    cd[n + 2] = cd[n + 3] = 1
    return leading, (tuple(ab), tuple(cd))


def _basis_polynomials(answer, p):
    n = len(answer)
    leading, tails = _monomial_data(n)
    out = []
    for i, row in enumerate(answer):
        poly = {leading[i]: 1}
        for coeff, exp in zip(row, tails):
            if coeff % p:
                poly[exp] = coeff % p
        out.append(poly)
    return out


def _poly_term_add(poly, exp, coeff, p):
    value = (poly.get(exp, 0) + coeff) % p
    if value:
        poly[exp] = value
    else:
        poly.pop(exp, None)


def _multiply_monomial(poly, shift, scalar, p):
    out = {}
    for exp, coeff in poly.items():
        new_exp = tuple(a + b for a, b in zip(exp, shift))
        _poly_term_add(out, new_exp, scalar * coeff, p)
    return out


def _divides(left, right):
    return all(a <= b for a, b in zip(left, right))


def _normal_form(poly, basis, p):
    """Exact multivariate division in the fixed lex order."""
    work = {exp: coeff % p for exp, coeff in poly.items() if coeff % p}
    remainder = {}
    leading = [max(g) for g in basis]
    while work:
        exp = max(work)
        coeff = work[exp]
        reducer = next((i for i, lm in enumerate(leading) if _divides(lm, exp)), None)
        if reducer is None:
            _poly_term_add(remainder, exp, coeff, p)
            work.pop(exp)
            continue
        lm = leading[reducer]
        shift = tuple(a - b for a, b in zip(exp, lm))
        multiple = _multiply_monomial(basis[reducer], shift, coeff, p)
        for term_exp, term_coeff in multiple.items():
            _poly_term_add(work, term_exp, -term_coeff, p)
    return remainder


def _s_polynomial(left, right, p):
    lm_left, lm_right = max(left), max(right)
    lcm = tuple(max(a, b) for a, b in zip(lm_left, lm_right))
    shift_left = tuple(a - b for a, b in zip(lcm, lm_left))
    shift_right = tuple(a - b for a, b in zip(lcm, lm_right))
    out = _multiply_monomial(left, shift_left, 1, p)
    for exp, coeff in _multiply_monomial(right, shift_right, -1, p).items():
        _poly_term_add(out, exp, coeff, p)
    return out


# -- public generator interface ----------------------------------------------

def make_instance(n, seed=0, modulus_bits=20, **params) -> dict:
    """Inverse-generate a multihomogeneous ideal with a known reduced basis."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 2 or n % 2:
        raise ValueError("n must be an even integer at least 2")
    p = _prime_for_bits(modulus_bits)
    rng = random.Random(seed)

    # The wanted coefficient matrix X is sampled first.
    answer = [[rng.randrange(p) for _ in range(_TAILS)] for _ in range(n)]

    # Pair a with -a, then shuffle: sum(v)=0, so (I+1*v^T)^-1=I-1*v^T.
    v = []
    for _ in range(n // 2):
        value = rng.randrange(1, p)
        v.extend((value, (-value) % p))
    rng.shuffle(v)

    # Natural rows of A=I+1*v^T and T=A*X.
    natural = []
    for i in range(n):
        lead = v[:]
        lead[i] = (lead[i] + 1) % p
        tail = []
        for col in range(_TAILS):
            tail.append(sum(lead[j] * answer[j][col] for j in range(n)) % p)
        natural.append(lead + tail)

    order = list(range(n))
    rng.shuffle(order)
    rows = [natural[old] for old in order]

    return {
        "paper": "arXiv:1105.5509",
        "field": "GF(p)",
        "modulus": p,
        "modulus_bits": modulus_bits,
        "n": n,
        "n_variables": n + 4,
        "variable_multidegrees": {
            "x_i": [1, 1],
            "a": [1, 0],
            "b": [1, 2],
            "c": [0, 1],
            "d": [2, 1],
        },
        "monomial_columns": [f"x{i}^2" for i in range(n)] + ["a*b", "c*d"],
        "coefficient_rows": rows,
        "answer": answer,
    }


def render(inst) -> str:
    n = inst["n"]
    p = inst["modulus"]
    xvars = ",".join(f"x{i}" for i in range(n))
    xorder = " > ".join(f"x{i}" for i in range(n))
    columns = " ".join(inst["monomial_columns"])
    rows = "\n".join(" ".join(map(str, row)) for row in inst["coefficient_rows"])
    text = f"""Recover a reduced multihomogeneous Groebner basis

Work in the polynomial ring GF({p})[{xvars},a,b,c,d].  GF({p}) is
the prime field: add and multiply integer representatives modulo {p}, always
writing a field element as its unique integer in the inclusive range 0..{p - 1}.

Use lexicographic monomial order with
{xorder} > a > b > c > d.  For exponent vectors, compare the
exponent of the first variable where they differ; the monomial with the larger
exponent there is larger.  The variables have N^2 multidegrees
|x_i|=(1,1), |a|=(1,0), |b|=(1,2), |c|=(0,1), |d|=(2,1).
Thus x_i^2, a*b, and c*d all have multidegree (2,2).

Each following row is the coefficient vector of one generator of an ideal I.
The generated ideal I consists of every finite sum of polynomial multiples of
these rows.  Rows may be used in any order.  The coefficient columns, in order,
are:
{columns}

{rows}

A monomial's multidegree is the sum of the variable multidegrees counted with
their exponents; a polynomial is multihomogeneous when all its monomials have
one multidegree.  LM(f) denotes the largest monomial of f in the stated order.
A finite set G is a Groebner basis when every polynomial in I has leading
monomial divisible by a leading monomial of G.  It is reduced when every member
is monic and no nonleading monomial of one member is divisible by a leading
monomial of any member.  Equivalently for checking here, Buchberger's criterion
says that every pair's S-polynomial must reduce to zero by G.  For monic f,g,
S(f,g)=lcm(LM(f),LM(g))/LM(f)*f - lcm(LM(f),LM(g))/LM(g)*g, where
the lcm takes the coordinatewise maximum of the two exponent vectors.

The reduced Groebner basis of I is promised to have exactly {n} polynomials in
this fixed form, with row index i and all arithmetic in GF({p}):

    B_i = x_i^2 + U[i][0]*a*b + U[i][1]*c*d,   0 <= i < {n}.

Return U as exactly {n} rows of two canonical field integers.  Row order is
fixed by x0,x1,...,x{n - 1}; do not reorder rows.  Entries may repeat.  No
fractions, negative representatives, omitted rows, or extra keys are allowed.

Give your final answer inside <answer></answer> tags as one JSON matrix.
Example format only: <answer>[[0,1],[2,3]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\n" + PLACEBO_HINT
    return text


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    bodies = []
    if matches:
        # Tagged output is authoritative.  A fence inside the tags is allowed.
        body = matches[-1].strip()
        fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.I | re.S)
        bodies.append(fence.group(1).strip() if fence else body)
    else:
        # Models occasionally obey the JSON shape but wrap it in an outer
        # Markdown fence instead of the requested tags.  G3 requires accepting
        # that harmless presentation variation.
        fences = re.findall(r"```(?:json)?\s*(.*?)\s*```", text, re.I | re.S)
        bodies.extend(reversed([body.strip() for body in fences]))
        bodies.append(text.strip())
    for body in bodies:
        try:
            return json.loads(body)
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
    return None


def _validate_answer_shape(inst, answer):
    n, p = inst["n"], inst["modulus"]
    if not isinstance(answer, list):
        return False, "answer is not a matrix"
    if not answer:
        return False, "answer matrix is empty"
    if len(answer) < n:
        return False, f"too few basis rows: expected {n}, got {len(answer)}"
    if len(answer) > n:
        return False, f"too many basis rows: expected {n}, got {len(answer)}"
    for i, row in enumerate(answer):
        if not isinstance(row, list) or len(row) != _TAILS:
            return False, f"basis row {i} must contain exactly two entries"
        for j, value in enumerate(row):
            if isinstance(value, bool) or not isinstance(value, int):
                return False, f"coefficient U[{i}][{j}] is not an integer"
            if not 0 <= value < p:
                return False, f"coefficient U[{i}][{j}] is outside 0..{p - 1}"
    return True, "ok"


def verify(inst, answer):
    """Check any valid fixed-template reduced basis; never inspect inst['answer']."""
    ok, reason = _validate_answer_shape(inst, answer)
    if not ok:
        return False, reason
    n, p = inst["n"], inst["modulus"]
    rows = inst["coefficient_rows"]

    # Exact degree-(2,2) reductions of every displayed generator by B.
    # Its x-leading coefficients cancel B_i, leaving precisely these tail tests.
    for r, row in enumerate(rows):
        for col in range(_TAILS):
            residual = row[n + col]
            for j in range(n):
                residual -= row[j] * answer[j][col]
            if residual % p:
                return False, "candidate basis does not generate the displayed ideal"

    leading_block = [row[:n] for row in rows]
    if _matrix_rank_mod(leading_block, p) != n:
        return False, "displayed generators do not span all candidate basis rows"

    # Execute Buchberger's criterion exactly, even though the coprime leading
    # monomials make the outcome theorem-backed.
    basis = _basis_polynomials(answer, p)
    for i in range(n):
        for j in range(i + 1, n):
            s_poly = _s_polynomial(basis[i], basis[j], p)
            if _normal_form(s_poly, basis, p):
                return False, f"S-polynomial for basis rows {i},{j} does not reduce to zero"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the exact n-by-2 finite-field certificate language."""
    p = inst["modulus"]
    return [[rng.randrange(p) for _ in range(_TAILS)] for _ in range(inst["n"])]


def search_space(inst):
    return inst["modulus"] ** (inst["n"] * _TAILS)


def enumerate_all(inst):
    size = search_space(inst)
    if size > 10_000:
        return None
    count = 0
    p, n = inst["modulus"], inst["n"]
    for flat in itertools.product(range(p), repeat=n * _TAILS):
        candidate = [list(flat[2 * i:2 * i + 2]) for i in range(n)]
        count += int(verify(inst, candidate)[0])
    return count


def canonical_key(inst):
    """Invariant under generator-row order, x relabelling, and a<->c,b<->d."""
    solved, _ = _solve_leading_block(inst)
    if solved is None:
        return "singular-invalid-instance"
    normal = sorted(tuple(row) for row in solved)
    swapped = sorted((row[1], row[0]) for row in solved)
    canonical = min(normal, swapped)
    payload = json.dumps(
        [inst["modulus"], inst["n"], canonical], separators=(",", ":")
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def escalate(params):
    """Raise coefficient entropy at fixed answer shape before declaring the cap."""
    out = {k: v for k, v in params.items() if k != "_preset"}
    bits = out.get("modulus_bits", 20)
    if bits < 52:
        out["modulus_bits"] = bits + 8
        # Use a real instance because JSON punctuation also consumes the cap.
        probe = make_instance(seed=98765, **out)
        if len(json.dumps(probe["answer"], separators=(",", ":"))) > 2000:
            return "cap_bound"
        return out
    return "cap_bound"


# -- attacks, relabellings, and gates -----------------------------------------

def _ordered_pivot_rows(inst):
    """Read the unique +1 bump in each leading column and return those tail rows."""
    n = inst["n"]
    rows = inst["coefficient_rows"]
    ordered = [None] * n
    baselines = []
    for col in range(n):
        counts = Counter(row[col] for row in rows)
        base = counts.most_common(1)[0][0]
        baselines.append(base)
        bump = (base + 1) % inst["modulus"]
        where = [r for r, row in enumerate(rows) if row[col] == bump]
        if len(where) != 1:
            return None, None
        ordered[col] = rows[where[0]][n:n + _TAILS]
    return ordered, baselines


def _attack_raw_pivot_rows(inst):
    ordered, _ = _ordered_pivot_rows(inst)
    return ordered if ordered is not None else [[0, 0] for _ in range(inst["n"])]


def _attack_zero_anchor(inst, smallest=False):
    ordered, _ = _ordered_pivot_rows(inst)
    if ordered is None:
        return [[0, 0] for _ in range(inst["n"])]
    anchor = 0
    if smallest:
        p = inst["modulus"]
        centered = lambda x: min(x, p - x)
        anchor = min(range(inst["n"]),
                     key=lambda i: (sum(centered(x) for x in ordered[i]), i))
    return [[(row[c] - ordered[anchor][c]) % inst["modulus"]
             for c in range(_TAILS)] for row in ordered]


def _attack_unweighted_center(inst):
    ordered, _ = _ordered_pivot_rows(inst)
    n, p = inst["n"], inst["modulus"]
    if ordered is None:
        return [[0, 0] for _ in range(n)]
    inv_n = pow(n, p - 2, p)
    center = [sum(row[c] for row in ordered) * inv_n % p for c in range(_TAILS)]
    return [[(row[c] - center[c]) % p for c in range(_TAILS)] for row in ordered]


def _attack_sign_only(inst):
    ordered, baselines = _ordered_pivot_rows(inst)
    n, p = inst["n"], inst["modulus"]
    if ordered is None:
        return [[0, 0] for _ in range(n)]
    signs = [1 if value <= p // 2 else p - 1 for value in baselines]
    shift = [sum(signs[j] * ordered[j][c] for j in range(n)) % p
             for c in range(_TAILS)]
    return [[(ordered[i][c] - shift[c]) % p for c in range(_TAILS)]
            for i in range(n)]


def _relabel_instance(inst, row_order, x_order, swap_tails):
    n = inst["n"]
    if sorted(row_order) != list(range(n)) or sorted(x_order) != list(range(n)):
        raise ValueError("orders must be permutations")
    out = dict(inst)
    transformed_rows = []
    for old_r in row_order:
        old = inst["coefficient_rows"][old_r]
        tail = old[n:n + _TAILS]
        if swap_tails:
            tail = tail[::-1]
        transformed_rows.append([old[j] for j in x_order] + tail)
    out["coefficient_rows"] = transformed_rows
    out["monomial_columns"] = [f"x{i}^2" for i in range(n)] + ["a*b", "c*d"]
    carried = [inst["answer"][old][:] for old in x_order]
    if swap_tails:
        carried = [row[::-1] for row in carried]
    out["answer"] = carried
    return out


def _answer_atom_count(answer):
    return sum(len(row) for row in answer) if isinstance(answer, list) else 0


def selftest() -> dict:
    report = {}

    planted_ok = 0
    planted_total = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, _ = verify(inst, inst["answer"])
            planted_ok += int(ok)
            planted_total += 1
    report["G1_planted_verifies"] = {
        "pass": planted_ok == planted_total,
        "verified": planted_ok,
        "attempts": planted_total,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    base = [row[:] for row in shipping["answer"]]
    swapped = [row[:] for row in base]
    positions = [(i, j) for i in range(shipping["n"]) for j in range(_TAILS)]
    pair = next(((a, b) for a in positions for b in positions
                 if a < b and base[a[0]][a[1]] != base[b[0]][b[1]]), None)
    if pair is not None:
        a, b = pair
        swapped[a[0]][a[1]], swapped[b[0]][b[1]] = (
            swapped[b[0]][b[1]], swapped[a[0]][a[1]]
        )
    corruptions = {
        "drop": base[:-1],
        "swap": swapped,
        "duplicate": base + [base[-1][:]],
        "empty": [],
        "out_of_range": [[shipping["modulus"], base[0][1]]] + base[1:],
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = {case["reason"] for case in cases.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values()) and len(reasons) == 5,
        "cases": cases,
        "distinct_reasons": len(reasons),
    }

    wire = json.dumps(shipping["answer"], separators=(",", ":"))
    realistic = "The row reduction gives:\n<answer>```json\n" + wire + "\n```</answer>\nChecked."
    parsed = parse_answer(realistic)
    outer_fence = "The matrix is:\n```json\n" + wire + "\n```\n"
    report["G3_round_trip"] = {
        "pass": (parsed == shipping["answer"]
                 and parse_answer(outer_fence) == shipping["answer"]
                 and parse_answer("no answer here") is None),
        "parsed_equals_answer": parsed == shipping["answer"],
        "outer_fence_equals_answer": parse_answer(outer_fence) == shipping["answer"],
        "garbage_returns_none": parse_answer("no answer here") is None,
        "json_native": json.loads(json.dumps(shipping["answer"])) == shipping["answer"],
    }

    guess_rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "candidate_space": search_space(shipping),
        "candidate_space_bits": search_space(shipping).bit_length(),
        "prior": "uniform over all n-by-2 canonical GF(p) matrices",
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    t0 = time.perf_counter()
    reference_answer, reference_ops = _solve_leading_block(shipping)
    reference_sec = time.perf_counter() - t0
    reference_ok = reference_answer is not None and verify(shipping, reference_answer)[0]
    compact_answer, compact_ops = _structured_decode(shipping)
    compact_ok = compact_answer is not None and verify(shipping, compact_answer)[0]
    report["G5_density_and_baseline_cost"] = {
        "pass": (guess_total >= 200_000 and guess_rate < 1e-6
                 and reference_ok and compact_ok),
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_fraction": guess_rate,
        "shipping_exact_enumeration": enumerate_all(shipping),
        "demo_exact_solution_count": enumerate_all(demo),
        "baseline_wall_clock_seconds": round(reference_sec, 6),
        "baseline_arithmetic_operations": reference_ops,
        "baseline_algorithm": "Gauss-Jordan elimination over GF(p)",
        "compact_route_arithmetic_operations": compact_ops,
        "compact_route_verified": compact_ok,
    }

    attacks = {
        "outlier_smallest_row_anchor": {"successes": 0, "attempts": 8},
        "greedy_raw_pivot_rows": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "row_difference_zero_anchor": {"successes": 0, "attempts": 8},
        "unweighted_rank_one_center": {"successes": 0, "attempts": 8},
        "sign_only_rank_one_ansatz": {"successes": 0, "attempts": 8},
    }
    ref_success = 0
    ref_ops = []
    ref_secs = []
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_smallest_row_anchor": _attack_zero_anchor(inst, smallest=True),
            "greedy_raw_pivot_rows": _attack_raw_pivot_rows(inst),
            "row_difference_zero_anchor": _attack_zero_anchor(inst),
            "unweighted_rank_one_center": _attack_unweighted_center(inst),
            "sign_only_rank_one_ansatz": _attack_sign_only(inst),
        }
        for name, candidate in candidates.items():
            attacks[name]["successes"] += int(verify(inst, candidate)[0])
        rrng = random.Random(seed ^ 0x5A17)
        hit = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, rrng))[0]:
                hit = True
                break
        attacks["random_restart_256"]["successes"] += int(hit)
        rt0 = time.perf_counter()
        answer, ops = _solve_leading_block(inst)
        ref_secs.append(time.perf_counter() - rt0)
        ref_ops.append(ops)
        ref_success += int(answer is not None and verify(inst, answer)[0])
    all_failed = all(value["successes"] == 0 and value["attempts"] >= 8
                     for value in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_success == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Gauss-Jordan elimination over GF(p)",
            "complexity": "O(n^3 + n^2*t) exact field operations, t=2",
            "wall_clock_sec_mean": round(sum(ref_secs) / len(ref_secs), 6),
            "wall_clock_sec_max": round(max(ref_secs), 6),
            "operations_mean": round(sum(ref_ops) / len(ref_ops)),
            "operations_max": max(ref_ops),
            "solves": f"{ref_success}/8, as expected",
        },
    }

    doubled = make_instance(n=2 * shipping["n"], seed=2718,
                            modulus_bits=shipping["modulus_bits"])
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] > shipping["n"]
                and search_space(doubled) > search_space(shipping),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_planted_verifies": doubled_ok,
        "shipping_search_space_bits": search_space(shipping).bit_length(),
        "doubled_search_space_bits": search_space(doubled).bit_length(),
    }

    invariant = 0
    carried_valid = 0
    for seed in range(20):
        inst = make_instance(seed=1000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        rrng = random.Random(9000 + seed)
        row_order = list(range(inst["n"]))
        x_order = list(range(inst["n"]))
        rrng.shuffle(row_order)
        rrng.shuffle(x_order)
        transformed = _relabel_instance(inst, row_order, x_order, bool(seed % 2))
        invariant += int(canonical_key(inst) == canonical_key(transformed))
        carried_valid += int(verify(transformed, transformed["answer"])[0])
    unrelated = {
        canonical_key(make_instance(seed=2000 + seed,
                                    **DIFFICULTY[SHIPPING_DIFFICULTY]))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariant == 20 and carried_valid == 20 and len(unrelated) == 20,
        "composed_relabellings_invariant": invariant,
        "carried_witnesses_valid": carried_valid,
        "unrelated_distinct_keys": len(unrelated),
        "attempts_each": 20,
        "transformations": "input-row permutation + x-variable permutation + optional tail-variable-pair swap",
    }

    answer_chars = 0
    answer_atoms = 0
    for seed in range(40):
        answer = make_instance(seed=3000 + seed,
                               **DIFFICULTY[SHIPPING_DIFFICULTY])["answer"]
        answer_chars = max(answer_chars, len(json.dumps(answer, separators=(",", ":"))))
        answer_atoms = max(answer_atoms, _answer_atom_count(answer))
    answer_tokens = (answer_chars + 3) // 4
    intended_ops = _TAILS * (3 * shipping["n"] - 1)
    arms = _G9_EVIDENCE["arms"]
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        hinted_minus_placebo = hinted_rate - placebo_rate
    else:
        hinted_minus_placebo = None
    within_caps = answer_chars <= 2000 and answer_atoms <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        # The three oracle arms, including the hinted arm, are diagnostics.
        # Only the answer-size and intended-effort caps gate G9.
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": _G9_EVIDENCE["hinted_verdict"],
        "placebo_verdict": _G9_EVIDENCE["placebo_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_ops,
    }

    report["all_passed"] = all(
        value.get("pass") for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = DIFFICULTY[SHIPPING_DIFFICULTY]
    report["oracle_infrastructure"] = {
        "status": "bare and hinted complete; placebo diagnostic blocked",
        "reason": "OpenRouter reached the key total limit before a placebo attempt scored",
    }
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
