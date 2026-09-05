"""Verified Track-B generators for arXiv:2212.13149.

The paper studies X A X = B X B and X B X = A X A over R or C.
Proposition 6.5(ii), specialized to b=-a and alpha=0, supplies the
2-by-2 solution

    A0 = [[a,1],[0,a]], B0 = [[-a,1],[0,-a]],
    X0 = [[0,-1],[a^2,0]].

Direct sums of these blocks are transported by the simultaneous-similarity
invariance in Theorem 3.1.  The certificate is carried through that transform;
``make_instance`` never solves the equations it emits.
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


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - documented fallback
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "rational coefficient matrices in a Yang-Baxter-type system",
        "rational solution matrix",
    ],
    "verification_operations": [
        "exact rational matrix multiplication",
        "exact rational matrix comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Separating A and B into their half-sum and half-difference reveals "
        "a square-zero operator and a scaled involution whose transpose closes "
        "the two cubic identities."
    ),
    "hardness_basis": (
        "Track B: exact rational Jordan-chain elimination is an O(n^3) "
        "reference algorithm and averaged 12,022 exact operations and 0.0082 "
        "seconds over eight shipping instances; the half-sum/half-difference "
        "transpose route takes at most 219 exact arithmetic operations and must "
        "be recognized without tools."
    ),
    "max_answer_tokens": 391,
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

_HEIGHT_BOUND = 10 ** 15
_DENOMINATOR_BOUND = 1_000_000

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A nonzero n-by-n rational matrix.  Each entry is encoded as "
        "[numerator,denominator], with denominator in [1,1000000] and numerator "
        "in [-10^15,10^15].  Equivalent unreduced encodings are allowed."
    ),
    "bounds": {
        "rows": "n",
        "columns": "n",
        "numerator_abs": _HEIGHT_BOUND,
        "denominator_min": 1,
        "denominator_max": _DENOMINATOR_BOUND,
        "nonzero": True,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 2, "q_digits": 1},
    "easy": {"n": 6, "q_digits": 2},
    "medium": {"n": 8, "q_digits": 2},
    "hard": {"n": 10, "q_digits": 2},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT: str = (
    "Hint: The half-sum and half-difference isolate a square-zero part and a scaled involution."
)
PLACEBO_HINT: str = (
    "Hint: Keep every rational entry exact and check the two displayed equations in order."
)

# Replaced with harness-owned measurements after the bare/hinted/placebo runs.
_G9_EVIDENCE = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "pending",
}

NOTES = r"""
Definition and source. Section 1, equation (1), defines the system XAX=BXB and
XBX=AXA over real or complex square matrices. Section 6 treats 2-by-2 Jordan
coefficients. Proposition 6.5(ii), with b=-a and alpha=0, gives the exact block
used here. Theorem 3.1 says simultaneous similarity carries the full solution
set, so a direct sum of known blocks can be hidden by an exact rational
orthogonal basis change while its solution is carried along.

Step-0 discrimination and easy regimes. The certificate is not Track-A hard.
The paper itself uses Groebner bases in Section 6 and explicitly classifies the
2-by-2 regimes; on this promised distribution, exact rational Jordan-chain
elimination is polynomial time. The zero matrix is always a solution, so the
problem explicitly requires a nonzero witness. Cases A=B and the displayed
Jordan basis are also immediate and are not generated. The honest claim is
Track B: elimination is mechanical but too long by hand, while a solver that
notices the sum/difference structure can use a short exact transpose identity.

Generation. Before randomization, each 2-by-2 block is a Proposition 6.5(ii)
solution. ``make_instance`` forms a direct sum, samples a rational Householder
matrix P with P inverse equal to P transpose, and returns PAP^T, PBP^T, and the
carried PX P^T. It does not call the reference solver.

Attacks. Dense Householder mixing removes coordinate-position and sparse-entry
outliers. The greedy attack chooses among the obvious sum, difference, and
transpose candidates by the first residual; the small linear-combination
restart searches commuting ansatzes; the in-context transpose attack notices
the right shape but uses the unsquared scale. All are tested on eight shipping
seeds. The exact Jordan-chain solver is expected to succeed and is reported
separately, as Track B requires.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ZERO = Fraction(0)
_ONE = Fraction(1)


def _identity(n):
    return [[_ONE if i == j else _ZERO for j in range(n)] for i in range(n)]


def _transpose(a):
    return [list(row) for row in zip(*a)]


def _add(a, b):
    return [[x + y for x, y in zip(ra, rb)] for ra, rb in zip(a, b)]


def _sub(a, b):
    return [[x - y for x, y in zip(ra, rb)] for ra, rb in zip(a, b)]


def _scale(a, c):
    c = Fraction(c)
    return [[c * x for x in row] for row in a]


def _matmul(a, b):
    bt = _transpose(b)
    return [[sum((x * y for x, y in zip(row, col)), _ZERO) for col in bt]
            for row in a]


def _triple_entry(left, middle, right, i, j):
    """One entry of left*middle*right, used for cheap exact rejection."""
    n = len(left)
    return sum((left[i][k] * middle[k][ell] * right[ell][j]
                for k in range(n) for ell in range(n)), _ZERO)


def _to_json_matrix(a):
    if rationals is not None:
        return [[rationals.to_json(x) for x in row] for row in a]
    return [[[x.numerator, x.denominator] for x in row] for row in a]


def _from_json_matrix(value, n, bound, label="matrix", denominator_bound=None):
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a JSON array of rows")
    if not value:
        raise ValueError(f"{label} is empty")
    if len(value) != n:
        raise ValueError(f"wrong row count: expected {n}, got {len(value)}")
    out = []
    for i, row in enumerate(value):
        if not isinstance(row, list):
            raise ValueError(f"row {i} is not a JSON array")
        if len(row) != n:
            raise ValueError(f"wrong column count in row {i}: expected {n}, got {len(row)}")
        decoded = []
        for j, pair in enumerate(row):
            if not isinstance(pair, list) or len(pair) != 2:
                raise ValueError(f"entry ({i},{j}) is not [numerator,denominator]")
            num, den = pair
            if (isinstance(num, bool) or isinstance(den, bool)
                    or not isinstance(num, int) or not isinstance(den, int)):
                raise ValueError(f"entry ({i},{j}) does not contain two integers")
            if den < 1:
                raise ValueError(f"entry ({i},{j}) has a nonpositive denominator")
            den_bound = bound if denominator_bound is None else denominator_bound
            if abs(num) > bound or den > den_bound:
                raise OverflowError(f"entry ({i},{j}) is outside the inclusive height bound")
            decoded.append(Fraction(num, den))
        out.append(decoded)
    return out


def _householder(n, rng):
    """A dense exact rational orthogonal involution."""
    while True:
        v = [rng.choice((-3, -2, -1, 1, 2, 3)) for _ in range(n)]
        s = sum(x * x for x in v)
        p = [[Fraction(int(i == j)) - Fraction(2 * v[i] * v[j], s)
              for j in range(n)] for i in range(n)]
        # Reject the rare choices that preserve too much visible sparsity.
        if all(p[i][j] != 0 for i in range(n) for j in range(n)):
            return p


def make_instance(n, seed=0, **params) -> dict:
    """Carry explicit Proposition-6.5 blocks through an exact similarity."""
    q_digits = params.pop("q_digits", 2)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 2 or n % 2:
        raise ValueError("n must be an even integer at least 2")
    if isinstance(q_digits, bool) or not isinstance(q_digits, int) or not 1 <= q_digits <= 6:
        raise ValueError("q_digits must be an integer in [1,6]")

    rng = random.Random(seed)
    lo = 2 if q_digits == 1 else 10 ** (q_digits - 1)
    hi = 9 if q_digits == 1 else 10 ** q_digits - 1
    q = rng.randint(lo, hi)
    blocks = n // 2
    signs = [rng.choice((-1, 1)) for _ in range(blocks)]
    if blocks >= 2:
        signs[0], signs[1] = -1, 1
        rng.shuffle(signs)

    d0 = [[_ZERO for _ in range(n)] for _ in range(n)]
    n0 = [[_ZERO for _ in range(n)] for _ in range(n)]
    x0 = [[_ZERO for _ in range(n)] for _ in range(n)]
    for k, sign in enumerate(signs):
        i = 2 * k
        a = sign * q
        d0[i][i] = d0[i + 1][i + 1] = Fraction(a)
        n0[i][i + 1] = _ONE
        x0[i][i + 1] = -_ONE
        x0[i + 1][i] = Fraction(q * q)

    a0 = _add(d0, n0)
    b0 = _sub(n0, d0)
    p = _householder(n, rng)
    # P=P^T=P^{-1}.  The answer is transported, never recovered.
    a = _matmul(_matmul(p, a0), p)
    b = _matmul(_matmul(p, b0), p)
    x = _matmul(_matmul(p, x0), p)
    answer = _to_json_matrix(x)
    largest_num = max(abs(v.numerator) for row in x for v in row)
    largest_den = max(v.denominator for row in x for v in row)
    if largest_num > _HEIGHT_BOUND or largest_den > _DENOMINATOR_BOUND:
        raise ValueError("constructed certificate exceeds declared rational height")
    return {
        "family": "orthogonally transported Yang-Baxter matrix system",
        "n": n,
        "q_digits": q_digits,
        "numerator_height_bound": _HEIGHT_BOUND,
        "denominator_bound": _DENOMINATOR_BOUND,
        "A": _to_json_matrix(a),
        "B": _to_json_matrix(b),
        "answer": answer,
    }


def _format_rational(pair):
    num, den = pair
    return str(num) if den == 1 else f"{num}/{den}"


def _format_matrix(matrix):
    return "\n".join(" ".join(_format_rational(x) for x in row) for row in matrix)


def render(inst) -> str:
    hint = ""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        hint = "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        hint = "\n\n" + PLACEBO_HINT
    n = inst["n"]
    return f"""Nonzero solution of a Yang--Baxter matrix system

All matrices below are {n} by {n} matrices over the rational numbers.  Matrix
multiplication is the ordinary row-by-column product.  Find any nonzero
rational matrix X satisfying both exact identities

    X A X = B X B
    X B X = A X A.

The zero matrix is forbidden.  No sign, symmetry, rank, or invertibility
condition is imposed.  Every answer entry must have numerator absolute value
at most {inst['numerator_height_bound']} and positive denominator at most
{inst['denominator_bound']}; endpoints are inclusive.  Equivalent
unreduced fractions are accepted.

Matrix A (each row is one line; p/q means the exact rational p divided by q):
{_format_matrix(inst['A'])}

Matrix B:
{_format_matrix(inst['B'])}

Rows and columns use 0-based positions, though the output contains no indices.
Return exactly {n} rows of {n} entries in matrix order.  Encode each rational
entry as the JSON pair [numerator,denominator], even when the denominator is 1.

Give your final answer inside <answer></answer> tags as one JSON array of rows.
Example format only: <answer>[[[0,1],[1,2]],[[3,1],[-4,5]]]</answer>
Output nothing else inside the tags.{hint}"""


def parse_answer(text) -> object | None:
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json|python)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
    try:
        obj = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return obj if isinstance(obj, list) else None


def verify(inst, answer) -> tuple[bool, str]:
    """Verify any bounded nonzero rational solution; never read inst['answer']."""
    n = inst["n"]
    try:
        x = _from_json_matrix(
            answer, n, inst["numerator_height_bound"], "answer",
            inst["denominator_bound"])
    except OverflowError as exc:
        return False, str(exc)
    except (TypeError, ValueError, ZeroDivisionError) as exc:
        return False, str(exc)
    if not any(value for row in x for value in row):
        return False, "the zero matrix is forbidden"
    try:
        a = _from_json_matrix(inst["A"], n, _HEIGHT_BOUND, "A", _DENOMINATOR_BOUND)
        b = _from_json_matrix(inst["B"], n, _HEIGHT_BOUND, "B", _DENOMINATOR_BOUND)
    except (TypeError, ValueError, OverflowError, ZeroDivisionError) as exc:
        return False, "malformed instance: " + str(exc)

    for i in range(n):
        for j in range(n):
            if _triple_entry(x, a, x, i, j) != _triple_entry(b, x, b, i, j):
                return False, f"first identity fails at ({i},{j})"
    for i in range(n):
        for j in range(n):
            if _triple_entry(x, b, x, i, j) != _triple_entry(a, x, a, i, j):
                return False, f"second identity fails at ({i},{j})"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniformly sample the declared bounded nonzero rational encodings."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    n = inst["n"]
    h = inst["numerator_height_bound"]
    d = inst["denominator_bound"]
    while True:
        out = [[[rng.randint(-h, h), rng.randint(1, d)] for _ in range(n)]
               for _ in range(n)]
        if any(pair[0] for row in out for pair in row):
            return out


def search_space(inst) -> int | None:
    n = inst["n"]
    h = inst["numerator_height_bound"]
    d = inst["denominator_bound"]
    encodings_per_entry = (2 * h + 1) * d
    # Exclude matrices whose every numerator is zero (denominators still vary).
    return encodings_per_entry ** (n * n) - d ** (n * n)


def enumerate_all(inst) -> int | None:
    # Even the 2-by-2 bounded language is intentionally enormous.
    return None


def _matrix_mod(json_matrix, prime, inverses):
    return [[(num % prime) * inverses[den] % prime for num, den in row]
            for row in json_matrix]


def _first_identity_possible_mod(candidate, a_mod, b_mod, prime, inverses):
    """Necessary modular filter; a rejection here is an exact rejection over Q."""
    x = _matrix_mod(candidate, prime, inverses)
    n = len(x)
    left = right = 0
    for k in range(n):
        for ell in range(n):
            left += x[0][k] * a_mod[k][ell] * x[ell][0]
            right += b_mod[0][k] * x[k][ell] * b_mod[ell][0]
    return (left - right) % prime == 0


def _invariant_parameters(inst):
    n = inst["n"]
    a = _from_json_matrix(inst["A"], n, _HEIGHT_BOUND, "A")
    b = _from_json_matrix(inst["B"], n, _HEIGHT_BOUND, "B")
    d = _scale(_sub(a, b), Fraction(1, 2))
    d2 = _matmul(d, d)
    q2 = d2[0][0]
    if q2.denominator != 1 or q2 <= 0 or any(
        d2[i][j] != (q2 if i == j else 0)
        for i in range(n) for j in range(n)
    ):
        raise ValueError("instance is outside the promised scaled-involution family")
    q = math.isqrt(q2.numerator)
    if q * q != q2.numerator:
        raise ValueError("scaled-involution square is not an integer square")
    tr = sum((d[i][i] for i in range(n)), _ZERO)
    diff = tr / (2 * q)
    if diff.denominator != 1:
        raise ValueError("invalid signed-block multiplicity")
    blocks = n // 2
    plus = (blocks + diff.numerator) // 2
    return q, tuple(sorted((plus, blocks - plus)))


def canonical_key(inst) -> str:
    """Complete invariant on this promised family, modulo basis and A/B swap."""
    q, multiplicities = _invariant_parameters(inst)
    raw = json.dumps([inst["n"], q, multiplicities], separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params) -> dict | str | None:
    n = params.get("n")
    digits = params.get("q_digits", 2)
    if isinstance(n, bool) or not isinstance(n, int):
        return None
    if digits < 5:
        return {"n": n, "q_digits": digits + 1}
    return "cap_bound"


def _rref(rows, counter):
    r = [[Fraction(x) for x in row] for row in rows]
    m, n = len(r), len(r[0])
    pivots = []
    row = 0
    for col in range(n):
        if row == m:
            break
        pivot = next((i for i in range(row, m) if r[i][col]), None)
        if pivot is None:
            continue
        r[row], r[pivot] = r[pivot], r[row]
        pv = r[row][col]
        for j in range(col, n):
            r[row][j] /= pv
            counter[0] += 1
        for i in range(m):
            if i == row or not r[i][col]:
                continue
            factor = r[i][col]
            for j in range(col, n):
                r[i][j] -= factor * r[row][j]
                counter[0] += 2
        pivots.append(col)
        row += 1
    return r, pivots


def _nullspace(matrix, counter):
    r, pivots = _rref(matrix, counter)
    cols = len(matrix[0])
    free = [j for j in range(cols) if j not in pivots]
    basis = []
    for f in free:
        v = [_ZERO] * cols
        v[f] = _ONE
        for i, p in enumerate(pivots):
            v[p] = -r[i][f]
            counter[0] += 1
        basis.append(v)
    return basis


def _independent_column_indices(columns, wanted, counter):
    selected = []
    rank = 0
    for j in range(len(columns)):
        trial = selected + [j]
        # Column rank equals row rank of the transposed selected matrix.
        rows = [[columns[c][i] for c in trial] for i in range(len(columns[0]))]
        _, pivots = _rref(rows, counter)
        if len(pivots) > rank:
            selected.append(j)
            rank += 1
            if rank == wanted:
                break
    return selected


def _inverse(matrix, counter):
    n = len(matrix)
    aug = [row[:] + eye for row, eye in zip(matrix, _identity(n))]
    r, pivots = _rref(aug, counter)
    if pivots[:n] != list(range(n)):
        raise ValueError("singular chain basis")
    return [row[n:] for row in r]


def _matmul_counted(a, b, counter):
    bt = _transpose(b)
    out = []
    for row in a:
        new = []
        for col in bt:
            total = _ZERO
            for x, y in zip(row, col):
                total += x * y
                counter[0] += 2
            new.append(total)
        out.append(new)
    return out


def _reference_algorithm(inst):
    """Exact Jordan-chain construction independent of the planted witness."""
    n = inst["n"]
    counter = [0]
    a = _from_json_matrix(inst["A"], n, _HEIGHT_BOUND, "A")
    b = _from_json_matrix(inst["B"], n, _HEIGHT_BOUND, "B")
    d = _scale(_sub(a, b), Fraction(1, 2))
    nil = _scale(_add(a, b), Fraction(1, 2))
    counter[0] += 2 * n * n
    d2 = _matmul_counted(d, d, counter)
    q2 = d2[0][0]
    q = math.isqrt(q2.numerator)
    if q2.denominator != 1 or q * q != q2.numerator:
        return None, counter[0]

    chains = []
    for eigenvalue in (Fraction(q), Fraction(-q)):
        shifted = [[d[i][j] - (eigenvalue if i == j else 0)
                    for j in range(n)] for i in range(n)]
        counter[0] += n
        wbasis = _nullspace(shifted, counter)
        if not wbasis:
            continue
        images = []
        for f in wbasis:
            image = []
            for row in nil:
                image.append(sum((x * y for x, y in zip(row, f)), _ZERO))
                counter[0] += 2 * n
            images.append(image)
        wanted = len(wbasis) // 2
        chosen = _independent_column_indices(images, wanted, counter)
        if len(chosen) != wanted:
            return None, counter[0]
        for idx in chosen:
            chains.append((images[idx], wbasis[idx]))

    if len(chains) != n // 2:
        return None, counter[0]
    columns = []
    for e, f in chains:
        columns.extend((e, f))
    qmat = [[columns[j][i] for j in range(n)] for i in range(n)]
    qinv = _inverse(qmat, counter)
    x0 = [[_ZERO for _ in range(n)] for _ in range(n)]
    for k in range(n // 2):
        i = 2 * k
        x0[i][i + 1] = -_ONE
        x0[i + 1][i] = q2
    answer = _matmul_counted(_matmul_counted(qmat, x0, counter), qinv, counter)
    return _to_json_matrix(answer), counter[0]


def _sum_difference(inst):
    n = inst["n"]
    a = _from_json_matrix(inst["A"], n, _HEIGHT_BOUND, "A")
    b = _from_json_matrix(inst["B"], n, _HEIGHT_BOUND, "B")
    return _scale(_add(a, b), Fraction(1, 2)), _scale(_sub(a, b), Fraction(1, 2))


def _residual_score(inst, candidate):
    ok, _ = verify(inst, candidate)
    if ok:
        return 0
    try:
        n = inst["n"]
        x = _from_json_matrix(candidate, n, _HEIGHT_BOUND)
        a = _from_json_matrix(inst["A"], n, _HEIGHT_BOUND, "A")
        b = _from_json_matrix(inst["B"], n, _HEIGHT_BOUND, "B")
        left = _matmul(_matmul(x, a), x)
        right = _matmul(_matmul(b, x), b)
        return sum(abs(z.numerator) for row in _sub(left, right) for z in row)
    except Exception:
        return 10 ** 100


def _attack_outlier(inst):
    n = inst["n"]
    a = _from_json_matrix(inst["A"], n, _HEIGHT_BOUND, "A")
    b = _from_json_matrix(inst["B"], n, _HEIGHT_BOUND, "B")
    i, j = max(((i, j) for i in range(n) for j in range(n)),
               key=lambda ij: abs(a[ij[0]][ij[1]]) + abs(b[ij[0]][ij[1]]))
    x = [[_ZERO for _ in range(n)] for _ in range(n)]
    x[i][j] = _ONE
    return _to_json_matrix(x)


def _attack_greedy(inst):
    nil, d = _sum_difference(inst)
    options = [nil, d, _transpose(nil), _sub(_transpose(nil), nil)]
    candidates = [_to_json_matrix(x) for x in options]
    return min(candidates, key=lambda x: _residual_score(inst, x))


def _attack_wrong_scale_transpose(inst):
    nil, d = _sum_difference(inst)
    d2 = _matmul(d, d)
    q = math.isqrt(d2[0][0].numerator)
    return _to_json_matrix(_add(_scale(_transpose(nil), q), _scale(nil, -1)))


def _attack_linear_combo(inst, rng, attempts=256):
    n = inst["n"]
    a = _from_json_matrix(inst["A"], n, _HEIGHT_BOUND, "A")
    b = _from_json_matrix(inst["B"], n, _HEIGHT_BOUND, "B")
    best = None
    best_score = None
    for _ in range(attempts):
        u, v = rng.randint(-8, 8), rng.randint(-8, 8)
        if u == v == 0:
            u = 1
        candidate = _to_json_matrix(_add(_scale(a, u), _scale(b, v)))
        score = _residual_score(inst, candidate)
        if score == 0:
            return candidate
        if best is None or score < best_score:
            best, best_score = candidate, score
    return best


def _relabel_instance(inst, order, swap_ab=False):
    n = inst["n"]
    if sorted(order) != list(range(n)):
        raise ValueError("order is not a permutation")
    out = dict(inst)
    def relabel(matrix):
        return [[matrix[order[i]][order[j]] for j in range(n)] for i in range(n)]
    aa, bb = relabel(inst["A"]), relabel(inst["B"])
    out["A"], out["B"] = (bb, aa) if swap_ab else (aa, bb)
    out["answer"] = relabel(inst["answer"])
    return out


def _basis_transform_instance(inst):
    """Apply a fixed non-permutation rational orthogonal basis change."""
    n = inst["n"]
    q = _identity(n)
    q[0][0], q[0][1] = Fraction(3, 5), Fraction(-4, 5)
    q[1][0], q[1][1] = Fraction(4, 5), Fraction(3, 5)
    qt = _transpose(q)
    out = dict(inst)
    for key in ("A", "B", "answer"):
        matrix = _from_json_matrix(
            inst[key], n, _HEIGHT_BOUND, key, _DENOMINATOR_BOUND)
        out[key] = _to_json_matrix(_matmul(_matmul(q, matrix), qt))
    return out


def _answer_atoms(answer):
    return 2 * sum(len(row) for row in answer) if isinstance(answer, list) else 0


def selftest() -> dict:
    report = {}

    planted = total = 0
    for params in DIFFICULTY.values():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            planted += int(verify(inst, inst["answer"])[0])
            total += 1
    report["G1_planted_verifies"] = {
        "pass": planted == total, "verified": planted, "attempts": total,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    base = json.loads(json.dumps(shipping["answer"]))
    swapped = json.loads(json.dumps(base))
    found = False
    for i in range(shipping["n"]):
        for j in range(shipping["n"] - 1):
            if swapped[i][j] != swapped[i][j + 1]:
                swapped[i][j], swapped[i][j + 1] = swapped[i][j + 1], swapped[i][j]
                found = True
                break
        if found:
            break
    duplicate = json.loads(json.dumps(base))
    duplicate[0].append(duplicate[0][-1])
    out_of_range = json.loads(json.dumps(base))
    out_of_range[0][0] = [_HEIGHT_BOUND + 1, 1]
    corruptions = {
        "drop": base[:-1],
        "swap": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, why = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": why}
    reasons = {value["reason"] for value in cases.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in cases.values()) and len(reasons) == 5,
        "cases": cases,
        "distinct_reasons": len(reasons),
    }

    wire = json.dumps(shipping["answer"], separators=(",", ":"))
    realistic = f"I used exact arithmetic.\n<answer>```json\n{wire}\n```</answer>\nDone."
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"],
        "parsed_equals_answer": parsed == shipping["answer"],
        "json_native": json.loads(json.dumps(shipping["answer"])) == shipping["answer"],
    }

    guess_rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    modular_survivors = 0
    prime = 1_000_003
    inverses = [0] * (shipping["denominator_bound"] + 1)
    inverses[1] = 1
    for d in range(2, len(inverses)):
        inverses[d] = (prime - (prime // d) * inverses[prime % d] % prime) % prime
    a_mod = _matrix_mod(shipping["A"], prime, inverses)
    b_mod = _matrix_mod(shipping["B"], prime, inverses)
    for _ in range(guess_total):
        candidate = random_candidate(shipping, guess_rng)
        if _first_identity_possible_mod(candidate, a_mod, b_mod, prime, inverses):
            modular_survivors += 1
            guess_hits += int(verify(shipping, candidate)[0])
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "exact_modular_filter_survivors": modular_survivors,
        "candidate_space": search_space(shipping),
        "prior": "uniform bounded nonzero rational encodings of the required matrix shape",
    }

    t0 = time.perf_counter()
    reference, ref_ops = _reference_algorithm(shipping)
    ref_sec = time.perf_counter() - t0
    ref_ok = reference is not None and verify(shipping, reference)[0]
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_total >= 200_000 and guess_rate < 1e-6 and ref_ok,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_fraction": guess_rate,
        "shipping_exact_enumeration": enumerate_all(shipping),
        "baseline_wall_clock_seconds": round(ref_sec, 6),
        "baseline_arithmetic_operations": ref_ops,
        "baseline_algorithm": "exact rational Jordan-chain elimination",
    }

    attacks = {
        "outlier_largest_coefficient": {"successes": 0, "attempts": 8},
        "greedy_smallest_first_residual": {"successes": 0, "attempts": 8},
        "random_restart_linear_combo_256": {"successes": 0, "attempts": 8},
        "unscaled_transpose_ansatz": {"successes": 0, "attempts": 8},
    }
    ref_success = 0
    ref_operations = []
    ref_seconds = []
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_largest_coefficient": _attack_outlier(inst),
            "greedy_smallest_first_residual": _attack_greedy(inst),
            "random_restart_linear_combo_256": _attack_linear_combo(
                inst, random.Random(seed ^ 0x5A17)),
            "unscaled_transpose_ansatz": _attack_wrong_scale_transpose(inst),
        }
        for name, candidate in candidates.items():
            attacks[name]["successes"] += int(verify(inst, candidate)[0])
        rt0 = time.perf_counter()
        candidate, operations = _reference_algorithm(inst)
        ref_seconds.append(time.perf_counter() - rt0)
        ref_operations.append(operations)
        ref_success += int(candidate is not None and verify(inst, candidate)[0])
    all_failed = all(v["successes"] == 0 and v["attempts"] >= 8
                     for v in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_success == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact rational Jordan-chain elimination",
            "complexity": "O(n^3) exact arithmetic on this promised distribution",
            "wall_clock_sec_mean": round(sum(ref_seconds) / len(ref_seconds), 6),
            "wall_clock_sec_max": round(max(ref_seconds), 6),
            "operations_mean": round(sum(ref_operations) / len(ref_operations)),
            "operations_max": max(ref_operations),
            "solves": f"{ref_success}/8, as expected",
        },
    }

    doubled = make_instance(n=2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
                            q_digits=DIFFICULTY[SHIPPING_DIFFICULTY]["q_digits"],
                            seed=2718)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] > shipping["n"]
                and search_space(doubled) > search_space(shipping),
        "shipping_dimension": shipping["n"],
        "doubled_dimension": doubled["n"],
        "doubled_planted_verifies": doubled_ok,
        "shipping_search_space_bits": search_space(shipping).bit_length(),
        "doubled_search_space_bits": search_space(doubled).bit_length(),
    }

    invariant = carried = 0
    for seed in range(20):
        inst = make_instance(seed=1000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        rrng = random.Random(9000 + seed)
        first = list(range(inst["n"]))
        second = list(range(inst["n"]))
        rrng.shuffle(first)
        rrng.shuffle(second)
        composed = [first[second[i]] for i in range(inst["n"])]
        transformed = _basis_transform_instance(
            _relabel_instance(inst, composed, swap_ab=bool(seed % 2)))
        invariant += int(canonical_key(inst) == canonical_key(transformed))
        carried += int(verify(transformed, transformed["answer"])[0])
    unrelated_seeds = list(range(3000, 3020))
    unrelated_keys = {
        canonical_key(make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY]))
        for seed in unrelated_seeds
    }
    report["G8_canonical_key"] = {
        "pass": invariant == 20 and carried == 20 and len(unrelated_keys) == 20,
        "composed_relabellings_invariant": invariant,
        "carried_witnesses_valid": carried,
        "unrelated_distinct_keys": len(unrelated_keys),
        "attempts_each": 20,
        "unrelated_seeds": unrelated_seeds,
    }

    answer_chars = answer_atoms = 0
    answer_lengths = []
    for seed in range(40):
        answer = make_instance(seed=3000 + seed,
                               **DIFFICULTY[SHIPPING_DIFFICULTY])["answer"]
        encoded = json.dumps(answer, separators=(",", ":"))
        answer_lengths.append(len(encoded))
        answer_chars = max(answer_chars, len(encoded))
        answer_atoms = max(answer_atoms, _answer_atoms(answer))
    answer_tokens = max((length + 3) // 4 for length in answer_lengths)
    n = shipping["n"]
    # One row dot product obtains q^2; each X_ij uses one multiply/subtract.
    intended_ops = (2 * n - 1) + 2 * n * n
    arms = _G9_EVIDENCE["arms"]
    hinted_minus_placebo = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
    )
    within_caps = answer_chars <= 2000 and answer_atoms <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": _G9_EVIDENCE["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": _G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_ops,
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        value.get("pass") for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = DIFFICULTY[SHIPPING_DIFFICULTY]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
