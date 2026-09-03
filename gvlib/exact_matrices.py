"""Exact rational matrices.

A matrix is a list of rows, each a list of ``Fraction``; a vector is a flat list
of ``Fraction``.  Every result is exact -- no float is produced or accepted
anywhere in this module, so an eigenvalue-free PSD test is available to a
``verify()`` that must be reproducible bit for bit.

The determinant uses fraction-free Bareiss elimination on an integer rescaling
of the matrix, which keeps intermediate entries as minors instead of letting
rational numerators and denominators blow up.  Rank, ``solve`` and ``nullspace``
share one reduced-row-echelon routine over Q.

On semidefiniteness, read the docstrings of ``is_psd`` and
``leading_principal_minors`` together: all leading principal minors positive is
a correct test for positive *definiteness* and is NOT a correct test for
positive *semi*definiteness.  ``is_psd`` uses LDL^T, which is.
"""

import math
from fractions import Fraction

from .rationals import Q, from_json as _rat_from_json, to_json as _rat_to_json

__all__ = [
    "matrix",
    "shape",
    "identity",
    "add",
    "sub",
    "scale",
    "matmul",
    "matvec",
    "transpose",
    "det",
    "rank",
    "solve",
    "nullspace",
    "gram",
    "is_symmetric",
    "ldl",
    "is_psd",
    "is_positive_definite",
    "leading_principal_minors",
    "ldl_to_squares",
    "to_json",
    "from_json",
]

_ZERO = Fraction(0)
_ONE = Fraction(1)


def matrix(rows):
    """Validate `rows` and return a fresh matrix of ``Fraction``.

    Guarantees: non-empty, rectangular, at least one column, every entry coerced
    by ``rationals.Q`` (so a float entry raises ``TypeError`` instead of
    poisoning the arithmetic), and the input is not aliased or mutated.  Raises
    ``TypeError``/``ValueError`` otherwise.  Every other function here assumes
    its arguments already satisfy this.
    """
    if not isinstance(rows, (list, tuple)) or len(rows) == 0:
        raise ValueError("matrix must be a non-empty list of rows")
    out = []
    width = None
    for r in rows:
        if not isinstance(r, (list, tuple)):
            raise TypeError("each row must be a list, got %s" % (type(r).__name__,))
        if width is None:
            width = len(r)
            if width == 0:
                raise ValueError("matrix must have at least one column")
        elif len(r) != width:
            raise ValueError("ragged matrix: rows of length %d and %d"
                             % (width, len(r)))
        out.append([Q(x) for x in r])
    return out


def shape(A):
    """``(rows, cols)`` of `A`.  Guarantees both are positive ints."""
    return (len(A), len(A[0]))


def identity(n):
    """The n-by-n identity matrix.  `n` must be a positive int."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive int, got %r" % (n,))
    return [[_ONE if i == j else _ZERO for j in range(n)] for i in range(n)]


def add(A, B):
    """Entrywise sum.  Raises ``ValueError`` unless the shapes agree."""
    if shape(A) != shape(B):
        raise ValueError("shape mismatch: %r vs %r" % (shape(A), shape(B)))
    return [[a + b for a, b in zip(ra, rb)] for ra, rb in zip(A, B)]


def sub(A, B):
    """Entrywise difference ``A - B``.  Raises ``ValueError`` on a shape
    mismatch.  ``sub(A, A)`` is the exact zero matrix."""
    if shape(A) != shape(B):
        raise ValueError("shape mismatch: %r vs %r" % (shape(A), shape(B)))
    return [[a - b for a, b in zip(ra, rb)] for ra, rb in zip(A, B)]


def scale(A, factor):
    """`A` multiplied entrywise by the rational scalar `factor`."""
    c = Q(factor)
    return [[c * x for x in row] for row in A]


def transpose(A):
    """Transpose of `A`.  Guarantees ``shape(transpose(A)) == (n, m)`` for an
    m-by-n `A`, and ``transpose(transpose(A)) == A``."""
    m, n = shape(A)
    return [[A[i][j] for i in range(m)] for j in range(n)]


def matmul(A, B):
    """Exact matrix product ``A @ B``.

    Raises ``ValueError`` unless ``cols(A) == rows(B)``.  Guarantees exact
    rational entries; cost is the schoolbook O(m*n*p).
    """
    m, n = shape(A)
    n2, p = shape(B)
    if n != n2:
        raise ValueError("cannot multiply %r by %r" % (shape(A), shape(B)))
    Bt = transpose(B)
    return [[sum((a * b for a, b in zip(row, col)), _ZERO) for col in Bt]
            for row in A]


def matvec(A, v):
    """Exact product ``A @ v`` for a vector `v`, returned as a flat list.

    Raises ``ValueError`` unless ``len(v) == cols(A)``.
    """
    m, n = shape(A)
    if len(v) != n:
        raise ValueError("expected a vector of length %d, got %d" % (n, len(v)))
    w = [Q(x) for x in v]
    return [sum((a * b for a, b in zip(row, w)), _ZERO) for row in A]


def _integerize(A):
    """Return ``(B, factor)`` where B is an integer matrix with
    ``B[i][j] == A[i][j] * L_i`` and ``factor == prod(L_i)``, L_i the lcm of the
    denominators in row i.  Hence ``det(A) == det(B) / factor``.  Internal."""
    B = []
    factor = 1
    for row in A:
        L = 1
        for x in row:
            L = math.lcm(L, x.denominator)
        # L is a multiple of every denominator in the row, so this is exact
        # integer arithmetic -- no Fraction-to-int conversion is involved.
        B.append([x.numerator * (L // x.denominator) for x in row])
        factor *= L
    return B, factor


def _bareiss(B):
    """Fraction-free Bareiss elimination on a square integer matrix.

    Returns the integer determinant.  Every division in the loop is exact by the
    Bareiss identity (each entry is a minor of the permuted matrix), so ``//``
    never truncates.  Internal.
    """
    n = len(B)
    M = [row[:] for row in B]
    sign = 1
    prev = 1
    for k in range(n - 1):
        if M[k][k] == 0:
            pivot = None
            for r in range(k + 1, n):
                if M[r][k] != 0:
                    pivot = r
                    break
            if pivot is None:
                return 0
            M[k], M[pivot] = M[pivot], M[k]
            sign = -sign
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                M[i][j] = (M[i][j] * M[k][k] - M[i][k] * M[k][j]) // prev
            M[i][k] = 0
        prev = M[k][k]
    return sign * M[n - 1][n - 1]


def det(A):
    """Exact determinant of a square matrix, as a ``Fraction``.

    Computed by fraction-free Bareiss elimination on an integer rescaling of
    `A`, with row swaps when a pivot vanishes.  Guarantees an exact value --
    ``det(A) == 0`` iff `A` is singular, with no tolerance and no rounding --
    and raises ``ValueError`` if `A` is not square.
    """
    m, n = shape(A)
    if m != n:
        raise ValueError("determinant needs a square matrix, got %r" % (shape(A),))
    B, factor = _integerize(A)
    return Fraction(_bareiss(B), factor)


def _rref(A):
    """Reduced row echelon form over Q.

    Returns ``(R, pivots)`` with `R` a fresh matrix and `pivots` the list of
    pivot column indices in increasing order.  Internal.
    """
    R = [row[:] for row in A]
    m, n = shape(R)
    pivots = []
    r = 0
    for c in range(n):
        if r >= m:
            break
        pivot = None
        for i in range(r, m):
            if R[i][c] != 0:
                pivot = i
                break
        if pivot is None:
            continue
        R[r], R[pivot] = R[pivot], R[r]
        pv = R[r][c]
        R[r] = [x / pv for x in R[r]]
        for i in range(m):
            if i != r and R[i][c] != 0:
                f = R[i][c]
                R[i] = [a - f * b for a, b in zip(R[i], R[r])]
        pivots.append(c)
        r += 1
    return R, pivots


def rank(A):
    """Exact rank of `A`.

    Guarantees the true rank over Q (no numerical threshold anywhere): for a
    square `A`, ``rank(A) == n`` iff ``det(A) != 0``, and
    ``rank(A) == rank(transpose(A))``.
    """
    _, pivots = _rref(A)
    return len(pivots)


def solve(A, b):
    """One exact solution of ``A x = b``, or ``None`` if there is none.

    Guarantees: when a solution is returned, ``matvec(A, x) == b`` exactly.
    When the system is underdetermined the free variables are set to 0, so this
    is *a* particular solution, not the general one -- combine it with
    ``nullspace(A)`` for the rest.  Raises ``ValueError`` if ``len(b)`` does not
    match the number of rows.
    """
    m, n = shape(A)
    if len(b) != m:
        raise ValueError("expected a right-hand side of length %d, got %d"
                         % (m, len(b)))
    rhs = [Q(x) for x in b]
    aug = [A[i][:] + [rhs[i]] for i in range(m)]
    R, pivots = _rref(aug)
    if n in pivots:
        return None  # a pivot in the augmented column: 0 == 1
    x = [_ZERO] * n
    for r, c in enumerate(pivots):
        x[c] = R[r][n]
    return x


def nullspace(A):
    """A basis of ``{x : A x = 0}``.

    Guarantees: each returned vector is non-zero and satisfies ``A x == 0``
    exactly, the vectors are linearly independent, and the basis has exactly
    ``cols(A) - rank(A)`` elements (so an empty list means the kernel is
    trivial).
    """
    m, n = shape(A)
    R, pivots = _rref(A)
    free = [c for c in range(n) if c not in pivots]
    basis = []
    for f in free:
        v = [_ZERO] * n
        v[f] = _ONE
        for r, c in enumerate(pivots):
            v[c] = -R[r][f]
        basis.append(v)
    return basis


def gram(vectors):
    """Gram matrix ``G[i][j] = <v_i, v_j>`` of a list of rational vectors.

    Guarantees: `G` is symmetric, ``is_psd(G)`` is always True, and
    ``rank(G)`` equals the rank of the vector family.  Raises
    ``ValueError`` unless the vectors are non-empty and of equal length.
    """
    V = matrix(vectors)
    return matmul(V, transpose(V))


def is_symmetric(A):
    """True iff `A` is square and ``A[i][j] == A[j][i]`` exactly for all i, j.

    Never raises: a non-square matrix simply returns False.
    """
    m, n = shape(A)
    if m != n:
        return False
    for i in range(m):
        for j in range(i + 1, n):
            if A[i][j] != A[j][i]:
                return False
    return True


def ldl(A):
    """Exact LDL^T factorisation of a symmetric matrix, without pivoting.

    Returns ``(L, D)`` with `L` unit lower triangular and `D` a list of
    diagonal entries such that ``A == L @ diag(D) @ L^T`` exactly, or ``None``
    if symmetric elimination hits a zero pivot whose column below is not zero
    (no unpivoted factorisation exists in that case -- and, as ``is_psd``
    relies on, such a matrix is never positive semidefinite).

    Raises ``ValueError`` if `A` is not square or not symmetric.
    """
    n, m = shape(A)
    if n != m:
        raise ValueError("LDL needs a square matrix, got %r" % (shape(A),))
    if not is_symmetric(A):
        raise ValueError("LDL needs a symmetric matrix")
    S = [row[:] for row in A]
    L = identity(n)
    D = []
    for k in range(n):
        d = S[k][k]
        if d == 0:
            for i in range(k + 1, n):
                if S[i][k] != 0:
                    return None
            D.append(_ZERO)
            continue
        D.append(d)
        for i in range(k + 1, n):
            L[i][k] = S[i][k] / d
        for i in range(k + 1, n):
            f = L[i][k]
            if f == 0:
                continue
            for j in range(k + 1, n):
                S[i][j] -= f * S[k][j]
        for i in range(k + 1, n):
            S[i][k] = _ZERO
    return L, D


def is_psd(A):
    """True iff `A` is symmetric and positive semidefinite, decided exactly.

    Symmetry is treated as part of the definition, so a non-symmetric or
    non-square argument returns False rather than raising -- ``verify()`` can
    call this on whatever a solver produced without a guard.

    The decision is LDL^T with the zero-pivot rule: `A` is PSD iff symmetric
    elimination completes with every pivot >= 0.  It is exact and complete, and
    it needs no eigenvalues.  Do NOT substitute "all leading principal minors
    >= 0" for this -- that test is wrong for PSD; see
    ``leading_principal_minors``.
    """
    if not is_symmetric(A):
        return False
    factored = ldl(A)
    if factored is None:
        return False
    _, D = factored
    return all(d >= 0 for d in D)


def is_positive_definite(A):
    """True iff `A` is symmetric and positive definite, decided exactly.

    Equivalent to Sylvester's criterion (all leading principal minors > 0) but
    computed from LDL^T, whose pivots are the successive ratios of those minors.
    A non-symmetric or non-square argument returns False rather than raising.
    """
    if not is_symmetric(A):
        return False
    factored = ldl(A)
    if factored is None:
        return False
    _, D = factored
    return all(d > 0 for d in D)


def leading_principal_minors(A):
    """The n leading principal minors of a square `A`, smallest first.

    Entry k is ``det(A[:k+1][:k+1])``.  Guarantees exact values.

    Read this warning before using it as a test.  All minors > 0 is equivalent
    to positive definiteness for a symmetric `A` (Sylvester's criterion), and
    all minors >= 0 is NOT equivalent to positive semidefiniteness: the matrix
    ``[[0, 0], [0, -1]]`` has leading principal minors 0 and 0, both >= 0, and
    is not PSD.  Deciding PSD needs *every* principal minor, not just the
    leading ones -- which is exponential; use ``is_psd``, which is not.
    """
    n, m = shape(A)
    if n != m:
        raise ValueError("leading principal minors need a square matrix")
    return [det([row[:k + 1] for row in A[:k + 1]]) for k in range(n)]


def ldl_to_squares(L, D):
    """Turn an LDL^T factorisation into a weighted sum of squares.

    Returns a list of ``(weight, linear_form)`` pairs, dropping zero weights,
    such that for every rational vector x::

        x^T A x  ==  sum(w * (sum(c_i * x_i))**2 for w, c in result)

    where ``c`` is the k-th column of `L`.  Guarantees exactness and, when `A`
    is PSD, that every returned weight is a positive rational.

    The weights stay outside the squares because a rational PSD matrix need not
    admit a decomposition with rational square roots: ``sum w_k * l_k^2`` with
    ``w_k`` in Q_{>=0} is the honest exact certificate, and it is exactly what a
    verifier can check with ``sparse_poly``.
    """
    n = len(D)
    out = []
    for k in range(n):
        w = D[k]
        if w == 0:
            continue
        out.append((w, [L[i][k] for i in range(n)]))
    return out


def to_json(A):
    """Encode a matrix as nested lists of ``[num, den]`` pairs.

    Guarantees ints-and-lists only, so ``json.dumps`` accepts it and no float
    can enter the serialisation.  ``from_json(to_json(A)) == A``.
    """
    return [[_rat_to_json(x) for x in row] for row in A]


def from_json(obj, rows=None, cols=None):
    """Decode a matrix from nested lists of ``[num, den]`` pairs.

    Strict: raises ``TypeError``/``ValueError`` on a ragged, empty or malformed
    input, and -- when `rows`/`cols` are given -- on a shape mismatch.  Pass the
    expected shape when reading solver output so a wrong-shape answer becomes a
    clean rejection rather than an exception three calls later.
    """
    if not isinstance(obj, (list, tuple)) or len(obj) == 0:
        raise ValueError("matrix JSON must be a non-empty list of rows")
    out = []
    width = None
    for r in obj:
        if not isinstance(r, (list, tuple)):
            raise TypeError("each row must be a list, got %s" % (type(r).__name__,))
        row = [_rat_from_json(x) for x in r]
        if width is None:
            width = len(row)
            if width == 0:
                raise ValueError("matrix must have at least one column")
        elif len(row) != width:
            raise ValueError("ragged matrix JSON")
        out.append(row)
    if rows is not None and len(out) != rows:
        raise ValueError("expected %d rows, got %d" % (rows, len(out)))
    if cols is not None and width != cols:
        raise ValueError("expected %d columns, got %d" % (cols, width))
    return out
