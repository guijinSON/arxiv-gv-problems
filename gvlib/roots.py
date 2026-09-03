"""Sturm sequences and exact real-root isolation over Q.

A univariate polynomial here is a *dense ascending* coefficient list of
rationals: ``[-1, 0, 3]`` is ``3*x^2 - 1``, and the zero polynomial is ``[]``.
``gvlib.sparse_poly.to_univariate`` / ``from_univariate`` convert to and from
the sparse form.

What this buys a family: a real algebraic number can be *named exactly* by a
squarefree polynomial plus an isolating interval with rational endpoints, and a
solver's claimed root can then be checked with integer arithmetic alone.  That
is a continuous-flavoured answer with a finite, exact certificate -- which is
the whole point of shipping this module rather than reaching for floats.

Everything is exact.  Nothing here converges to an answer; the bisection loops
terminate because the roots of a squarefree polynomial are simple and separated,
and every comparison is a comparison of rationals.
"""

from fractions import Fraction

from .rationals import Q

__all__ = [
    "normalize",
    "degree",
    "evaluate",
    "derivative",
    "divmod_poly",
    "gcd_poly",
    "squarefree_part",
    "is_squarefree",
    "sturm_sequence",
    "sign_changes",
    "count_roots",
    "root_bound",
    "isolate_roots",
    "refine",
]

_ZERO = Fraction(0)
_ONE = Fraction(1)


def normalize(coeffs):
    """Validate `coeffs` and return a fresh dense ascending list of ``Fraction``
    with trailing zeros stripped.

    Guarantees: the zero polynomial becomes ``[]``, and a non-zero result has a
    non-zero last entry (its leading coefficient).  Coefficients go through
    ``rationals.Q``, so a float raises ``TypeError``.  Every other function here
    assumes normalised input.
    """
    if not isinstance(coeffs, (list, tuple)):
        raise TypeError("polynomial must be a list of coefficients, got %s"
                        % (type(coeffs).__name__,))
    out = [Q(c) for c in coeffs]
    while out and out[-1] == 0:
        out.pop()
    return out


def degree(p):
    """Degree of `p`; ``-1`` for the zero polynomial.

    The ``-1`` convention makes ``degree(gcd_poly(p, derivative(p))) == 0`` the
    exact statement of squarefreeness for a non-zero p.
    """
    return len(p) - 1


def evaluate(p, x):
    """Value of `p` at the rational `x`, by Horner's rule, as a ``Fraction``.

    Guarantees exactness: `x` is coerced with ``rationals.Q``, so passing a
    float raises rather than silently making the answer approximate.
    """
    v = Q(x)
    acc = _ZERO
    for c in reversed(p):
        acc = acc * v + c
    return acc


def derivative(p):
    """Formal derivative of `p`, in the same representation.

    Guarantees ``[]`` for constants and for the zero polynomial.
    """
    return normalize([p[i] * i for i in range(1, len(p))])


def divmod_poly(a, b):
    """Exact quotient and remainder: ``(q, r)`` with ``a == q*b + r`` and
    ``degree(r) < degree(b)``.

    Guarantees exact rational arithmetic and normalised outputs.  Raises
    ``ZeroDivisionError`` if `b` is the zero polynomial.
    """
    a = normalize(a)
    b = normalize(b)
    if not b:
        raise ZeroDivisionError("division by the zero polynomial")
    r = list(a)
    db = degree(b)
    lead = b[-1]
    q = [_ZERO] * max(0, len(a) - db)
    for k in range(len(r) - 1, db - 1, -1):
        if r[k] == 0:
            continue
        f = r[k] / lead
        q[k - db] = f
        for i in range(db + 1):
            r[k - db + i] -= f * b[i]
    return normalize(q), normalize(r)


def gcd_poly(a, b):
    """Monic greatest common divisor of `a` and `b` over Q.

    Guarantees: the result is monic (leading coefficient 1) unless both inputs
    are zero, in which case it is ``[]``; it divides both inputs exactly; and it
    is the gcd of largest degree.
    """
    x, y = normalize(a), normalize(b)
    while y:
        _, r = divmod_poly(x, y)
        x, y = y, r
    if not x:
        return []
    lead = x[-1]
    return [c / lead for c in x]


def squarefree_part(p):
    """The monic squarefree part ``p / gcd(p, p')``.

    Guarantees: same distinct real roots as `p`, each now simple; monic; ``[]``
    for the zero polynomial.  Sturm's theorem needs a squarefree argument, and
    this is how to get one.
    """
    q = normalize(p)
    if not q:
        return []
    g = gcd_poly(q, derivative(q))
    if degree(g) <= 0:
        lead = q[-1]
        return [c / lead for c in q]
    part, _ = divmod_poly(q, g)
    lead = part[-1]
    return [c / lead for c in part]


def is_squarefree(p):
    """True iff `p` is non-constant and has no repeated factor over Q.

    Decided exactly as ``degree(gcd(p, p')) == 0``.  Constants and the zero
    polynomial return False, because "the roots of a constant" is not a question
    this module answers.
    """
    q = normalize(p)
    if degree(q) < 1:
        return False
    return degree(gcd_poly(q, derivative(q))) == 0


def _scale_positive(p):
    """Divide `p` by the absolute value of its leading coefficient.

    Multiplying any member of a Sturm chain by a positive rational leaves every
    sign, and therefore every sign-change count, unchanged -- it only keeps the
    coefficients from growing.  Internal.
    """
    if not p:
        return p
    m = abs(p[-1])
    return [c / m for c in p]


def sturm_sequence(p):
    """The canonical Sturm chain of `p`: ``p0 = p``, ``p1 = p'``,
    ``p_{k+1} = -rem(p_{k-1}, p_k)``, stopping at the last non-zero term.

    Each element is rescaled by a positive rational, which does not change any
    sign and keeps the coefficients small.  Guarantees a non-empty list whose
    first element is `p` rescaled, for any non-constant `p`; raises
    ``ValueError`` for a constant or zero `p`.
    """
    q = normalize(p)
    if degree(q) < 1:
        raise ValueError("Sturm chain needs a non-constant polynomial")
    seq = [_scale_positive(q), _scale_positive(derivative(q))]
    while degree(seq[-1]) > 0:
        _, r = divmod_poly(seq[-2], seq[-1])
        if not r:
            break
        seq.append(_scale_positive([-c for c in r]))
    return seq


def sign_changes(seq, x):
    """Number of sign changes in the values of `seq` at the rational `x`,
    skipping zeros.

    Guarantees a non-negative int and exact evaluation.  This is the V(x) of
    Sturm's theorem.
    """
    last = 0
    count = 0
    for p in seq:
        v = evaluate(p, x)
        if v == 0:
            continue
        s = 1 if v > 0 else -1
        if last != 0 and s != last:
            count += 1
        last = s
    return count


def count_roots(p, a, b, seq=None):
    """Number of distinct real roots of `p` in the open interval ``(a, b)``.

    `p` must be squarefree (``is_squarefree``) and must not vanish at either
    endpoint; `a` must be less than `b`.  Guarantees the exact count by Sturm's
    theorem, ``V(a) - V(b)``, with no numerical tolerance anywhere.  Raises
    ``ValueError`` if the preconditions fail -- in particular an endpoint that
    is itself a root is refused rather than silently miscounted.

    Pass `seq` (from ``sturm_sequence``) to reuse a chain across many queries.
    """
    lo, hi = Q(a), Q(b)
    if lo >= hi:
        raise ValueError("need a < b, got %s and %s" % (lo, hi))
    q = normalize(p)
    if not is_squarefree(q):
        raise ValueError("count_roots needs a squarefree polynomial; "
                         "use squarefree_part first")
    if evaluate(q, lo) == 0 or evaluate(q, hi) == 0:
        raise ValueError("an endpoint is a root; move it")
    chain = sturm_sequence(q) if seq is None else seq
    return sign_changes(chain, lo) - sign_changes(chain, hi)


def root_bound(p):
    """A positive rational `B` with every real root of `p` strictly inside
    ``(-B, B)``.

    Cauchy's bound, ``1 + max|a_i| / |a_n|``.  Guarantees ``B > 0``,
    ``evaluate(p, B) != 0`` and ``evaluate(p, -B) != 0``, so it is always a legal
    starting interval for ``isolate_roots``.  Raises ``ValueError`` for a
    constant or zero `p`.
    """
    q = normalize(p)
    if degree(q) < 1:
        raise ValueError("root bound needs a non-constant polynomial")
    lead = abs(q[-1])
    return _ONE + max(abs(c) for c in q[:-1]) / lead


def isolate_roots(p, lo=None, hi=None):
    """Isolating intervals for the distinct real roots of a squarefree `p`.

    Returns a list of ``(a, b)`` pairs of ``Fraction``, sorted and
    non-overlapping, such that ``a < b``, exactly one root of `p` lies strictly
    inside each, and neither endpoint is a root.  Two adjacent intervals may
    share an endpoint (``x^2-2`` gives ``(-3,0)`` and ``(0,3)``); since the
    shared point is never a root, the open intervals are still disjoint.  A
    rational root is isolated like any other, by an interval around it; use
    ``refine`` to pin it down exactly.

    Guarantees: the number of intervals equals the number of distinct real roots
    in the search range, which is ``(lo, hi)`` if given and ``(-B, B)`` from
    ``root_bound`` otherwise.  `p` must be squarefree and must not vanish at
    `lo` or `hi`; otherwise ``ValueError``.  Termination is guaranteed because
    the roots of a squarefree polynomial are simple, hence separated by a
    positive rational distance.
    """
    q = normalize(p)
    if not is_squarefree(q):
        raise ValueError("isolate_roots needs a squarefree polynomial; "
                         "use squarefree_part first")
    if lo is None or hi is None:
        B = root_bound(q)
        lo = -B if lo is None else Q(lo)
        hi = B if hi is None else Q(hi)
    else:
        lo, hi = Q(lo), Q(hi)
    if lo >= hi:
        raise ValueError("need lo < hi, got %s and %s" % (lo, hi))
    chain = sturm_sequence(q)
    for x in (lo, hi):
        if evaluate(q, x) == 0:
            raise ValueError("an endpoint is a root; move it")
    total = sign_changes(chain, lo) - sign_changes(chain, hi)
    out = []
    stack = [(lo, hi, total)]
    guard = 0
    limit = 64 * (degree(q) + 1) ** 2 + 1024
    while stack:
        guard += 1
        if guard > limit:
            raise RuntimeError("root isolation failed to terminate")
        a, b, c = stack.pop()
        if c == 0:
            continue
        if c == 1:
            out.append((a, b))
            continue
        mid = (a + b) / 2
        steps = 0
        while evaluate(q, mid) == 0:
            # The midpoint is itself a root: shift it toward `a`.  Only finitely
            # many points are roots, so this stops, and the root at the old
            # midpoint stays strictly inside the right-hand sub-interval.
            mid = (a + mid) / 2
            steps += 1
            if steps > degree(q) + 1:
                raise RuntimeError("could not find a non-root midpoint")
        left = sign_changes(chain, a) - sign_changes(chain, mid)
        stack.append((a, mid, left))
        stack.append((mid, b, c - left))
    out.sort()
    return out


def refine(p, interval, width):
    """Shrink an isolating interval to width at most `width`, exactly.

    Bisects with rational midpoints, keeping the half that still contains the
    root.  Guarantees: the returned ``(a, b)`` still isolates the same root,
    ``b - a <= width``, and if the root is exactly rational the result may be
    the degenerate ``(r, r)`` with ``evaluate(p, r) == 0``.  Sign comparisons
    are exact, so the endpoints are certified bounds and not estimates.

    `width` must be a positive rational; `interval` must come from
    ``isolate_roots`` (or otherwise bracket exactly one simple root with
    non-zero, opposite-sign endpoints).
    """
    q = normalize(p)
    a, b = Q(interval[0]), Q(interval[1])
    w = Q(width)
    if w <= 0:
        raise ValueError("width must be positive, got %s" % (w,))
    if a == b:
        if evaluate(q, a) != 0:
            raise ValueError("degenerate interval that is not a root")
        return (a, a)
    if a > b:
        raise ValueError("need a <= b, got %s and %s" % (a, b))
    fa, fb = evaluate(q, a), evaluate(q, b)
    if fa == 0:
        return (a, a)
    if fb == 0:
        return (b, b)
    if (fa > 0) == (fb > 0):
        raise ValueError("endpoints do not bracket a sign change")
    while b - a > w:
        mid = (a + b) / 2
        fm = evaluate(q, mid)
        if fm == 0:
            return (mid, mid)
        if (fm > 0) == (fa > 0):
            a, fa = mid, fm
        else:
            b, fb = mid, fm
    return (a, b)
