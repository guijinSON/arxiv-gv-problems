"""Sparse multivariate polynomials over Q.

A polynomial is a plain ``dict`` mapping an exponent tuple to a ``Fraction``::

    3*x0^2*x1 - 2   ->   {(2, 1): Fraction(3), (0, 0): Fraction(-2)}

Invariants of a *normalised* polynomial (everything this module returns):

  * every key is a tuple of non-negative ints, all of the same length -- the
    arity, i.e. the number of variables;
  * every value is a non-zero ``Fraction``;
  * the zero polynomial is ``{}``, and its arity is unknown (``None``).

Plain dicts rather than a class, so a generated module can write one as a
literal, ship it through JSON, and read it in a diff without learning an API.

Naming note: the exponentiation helper is ``power`` and evaluation is
``evaluate``.  Calling them ``pow`` and ``eval`` would shadow two builtins
inside every module that does ``from gvlib.sparse_poly import *``, and one of
those builtins is ``eval``.
"""

from fractions import Fraction

from .rationals import Q, from_json as _rat_from_json, to_json as _rat_to_json

__all__ = [
    "normalize",
    "arity",
    "const",
    "var",
    "add",
    "sub",
    "scale",
    "mul",
    "power",
    "evaluate",
    "compose",
    "equal",
    "is_zero",
    "degree",
    "terms",
    "to_string",
    "to_json",
    "from_json",
    "to_univariate",
    "from_univariate",
    "gram_form",
]

_ZERO = Fraction(0)


def _check_exponents(key, nvars):
    """Return `key` as a validated exponent tuple of length `nvars` (or any
    length if `nvars` is None).  Internal."""
    if not isinstance(key, (tuple, list)):
        raise TypeError("exponent key must be a tuple/list, got %s"
                        % (type(key).__name__,))
    exps = tuple(key)
    for e in exps:
        if isinstance(e, bool) or not isinstance(e, int):
            raise TypeError("exponents must be ints, got %r" % (key,))
        if e < 0:
            raise ValueError("exponents must be non-negative, got %r" % (key,))
    if nvars is not None and len(exps) != nvars:
        raise ValueError("expected %d variables, got %r" % (nvars, key))
    return exps


def normalize(poly, nvars=None):
    """Validate `poly` and return a fresh normalised copy.

    Coerces every coefficient with ``rationals.Q``, converts exponent lists to
    tuples, drops zero coefficients, and checks that all keys have the same
    length (which must equal `nvars` if given).  Guarantees the returned dict
    satisfies the module invariants, and that the input is not mutated.

    Raises ``TypeError``/``ValueError`` on anything malformed.  This is the only
    function that should ever be handed untrusted input; every other function
    here assumes normalised arguments.
    """
    if not isinstance(poly, dict):
        raise TypeError("polynomial must be a dict, got %s" % (type(poly).__name__,))
    width = nvars
    acc = {}
    for key, coeff in poly.items():
        exps = _check_exponents(key, width)
        if width is None:
            width = len(exps)
        acc[exps] = acc.get(exps, _ZERO) + Q(coeff)
    return {e: c for e, c in acc.items() if c != 0}


def arity(poly):
    """Number of variables of `poly`, or ``None`` for the zero polynomial.

    Guarantees: for a normalised polynomial every key has this length.
    """
    for key in poly:
        return len(key)
    return None


def _common_arity(p, q):
    """Shared arity of two normalised polynomials, treating {} as arity-agnostic.
    Raises ValueError on a genuine mismatch.  Internal."""
    a, b = arity(p), arity(q)
    if a is None:
        return b
    if b is None:
        return a
    if a != b:
        raise ValueError("arity mismatch: %d vs %d" % (a, b))
    return a


def const(value, nvars):
    """The constant polynomial `value` in `nvars` variables.

    Guarantees ``{}`` when `value` is zero, else a single term with exponent
    tuple ``(0,)*nvars``.  `nvars` must be a positive int.
    """
    if isinstance(nvars, bool) or not isinstance(nvars, int) or nvars < 1:
        raise ValueError("nvars must be a positive int, got %r" % (nvars,))
    c = Q(value)
    return {} if c == 0 else {(0,) * nvars: c}


def var(index, nvars):
    """The polynomial x_index in `nvars` variables (0-based `index`).

    Guarantees a single term with coefficient 1.  Raises ``ValueError`` if
    `index` is out of range.
    """
    if isinstance(nvars, bool) or not isinstance(nvars, int) or nvars < 1:
        raise ValueError("nvars must be a positive int, got %r" % (nvars,))
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < nvars:
        raise ValueError("index %r out of range for %d variables" % (index, nvars))
    exps = [0] * nvars
    exps[index] = 1
    return {tuple(exps): Fraction(1)}


def add(p, q):
    """Sum of two normalised polynomials.

    Guarantees a normalised result with cancellation applied (terms that cancel
    are removed, so ``add(p, scale(p, -1)) == {}``).  Raises ``ValueError`` on
    an arity mismatch.
    """
    _common_arity(p, q)
    out = dict(p)
    for e, c in q.items():
        total = out.get(e, _ZERO) + c
        if total == 0:
            out.pop(e, None)
        else:
            out[e] = total
    return out


def sub(p, q):
    """Difference ``p - q`` of two normalised polynomials.

    Guarantees a normalised result; ``is_zero(sub(p, p))`` is always True.
    """
    return add(p, scale(q, -1))


def scale(p, factor):
    """`p` multiplied by the rational scalar `factor`.

    Guarantees ``{}`` when `factor` is zero, and a normalised result otherwise.
    """
    c = Q(factor)
    if c == 0:
        return {}
    return {e: v * c for e, v in p.items()}


def mul(p, q):
    """Product of two normalised polynomials.

    Guarantees a normalised result with like terms collected and cancellation
    applied.  Raises ``ValueError`` on an arity mismatch.  Cost is O(|p|*|q|)
    exact rational multiplications; there is no FFT and none is wanted -- the
    certificates here are small and the arithmetic must stay auditable.
    """
    _common_arity(p, q)
    out = {}
    for ep, cp in p.items():
        for eq, cq in q.items():
            e = tuple(a + b for a, b in zip(ep, eq))
            total = out.get(e, _ZERO) + cp * cq
            if total == 0:
                out.pop(e, None)
            else:
                out[e] = total
    return out


def power(p, k):
    """`p` raised to the non-negative integer power `k`.

    Guarantees an exact normalised result, computed by binary exponentiation.
    ``power(p, 0)`` is the constant 1 in `p`'s arity, so it raises
    ``ValueError`` for ``power({}, 0)`` where the arity is unknown.
    """
    if isinstance(k, bool) or not isinstance(k, int) or k < 0:
        raise ValueError("exponent must be a non-negative int, got %r" % (k,))
    n = arity(p)
    if k == 0:
        if n is None:
            raise ValueError("power({}, 0) is ambiguous: arity unknown")
        return const(1, n)
    result = None
    base = p
    e = k
    while e:
        if e & 1:
            result = base if result is None else mul(result, base)
        e >>= 1
        if e:
            base = mul(base, base)
    return result


def evaluate(p, point):
    """Value of `p` at `point`, a sequence of rationals, as a ``Fraction``.

    Guarantees an exact value: every coordinate goes through ``rationals.Q``, so
    a float coordinate raises ``TypeError`` rather than silently making the
    result approximate.  ``evaluate({}, point)`` is 0.  Raises ``ValueError`` if
    ``len(point)`` disagrees with the arity.
    """
    n = arity(p)
    coords = [Q(x) for x in point]
    if n is not None and len(coords) != n:
        raise ValueError("expected %d coordinates, got %d" % (n, len(coords)))
    total = _ZERO
    for exps, coeff in p.items():
        term = coeff
        for x, e in zip(coords, exps):
            if e:
                term *= x ** e
        total += term
    return total


def compose(p, subs):
    """Substitute polynomials for the variables of `p`.

    `subs` is a sequence of ``arity(p)`` normalised polynomials, all of the same
    arity m; the result is a polynomial in m variables.  Guarantees exactness
    and agreement with evaluation: ``evaluate(compose(p, subs), pt)`` equals
    ``evaluate(p, [evaluate(s, pt) for s in subs])`` for every rational point.

    Raises ``ValueError`` if the number of substitutions is wrong, if they have
    mixed arity, or if every substitution is the zero polynomial (whose arity is
    unknown, leaving m undetermined).
    """
    n = arity(p)
    if n is None:
        return {}
    if len(subs) != n:
        raise ValueError("expected %d substitutions, got %d" % (n, len(subs)))
    inner = None
    for s in subs:
        a = arity(s)
        if a is not None:
            if inner is not None and a != inner:
                raise ValueError("substitutions have mixed arity")
            inner = a
    if inner is None:
        raise ValueError("cannot infer arity: every substitution is zero")
    max_exp = [0] * n
    for exps in p:
        for i, e in enumerate(exps):
            if e > max_exp[i]:
                max_exp[i] = e
    powers = []
    for i in range(n):
        seq = [const(1, inner)]
        for _ in range(max_exp[i]):
            seq.append(mul(seq[-1], subs[i]))
        powers.append(seq)
    out = {}
    for exps, coeff in p.items():
        term = const(coeff, inner)
        for i, e in enumerate(exps):
            if e:
                term = mul(term, powers[i][e])
        out = add(out, term)
    return out


def equal(p, q):
    """True iff `p` and `q` are the same polynomial.

    Guarantees a plain bool with no exception on an arity mismatch: polynomials
    in different numbers of variables are simply not equal (except that the zero
    polynomial equals the zero polynomial).  Both arguments are normalised
    first, so ``equal({(0,): 0}, {})`` is True.
    """
    return normalize(p) == normalize(q)


def is_zero(p):
    """True iff `p` is the zero polynomial.

    Normalises first, so a dict carrying explicit zero coefficients still counts
    as zero.  This is the intended shape of an exact identity check in
    ``verify``: ``is_zero(sub(claimed, expected))``.
    """
    return not normalize(p)


def degree(p, var_index=None):
    """Total degree of `p`, or its degree in variable `var_index`.

    Guarantees ``-1`` for the zero polynomial (so that ``degree(p) < d`` reads
    correctly for every d >= 0), and a non-negative int otherwise.  Raises
    ``ValueError`` if `var_index` is out of range.
    """
    if not p:
        return -1
    if var_index is None:
        return max(sum(e) for e in p)
    n = arity(p)
    if isinstance(var_index, bool) or not isinstance(var_index, int) \
            or not 0 <= var_index < n:
        raise ValueError("variable index %r out of range for arity %d"
                         % (var_index, n))
    return max(e[var_index] for e in p)


def _sort_key(exps):
    """Graded lexicographic order key.  Internal."""
    return (sum(exps), exps)


def terms(p):
    """Terms of `p` as a list of ``(exponent tuple, Fraction)``, ascending in
    graded lexicographic order.

    Guarantees a deterministic order that does not depend on dict insertion
    order -- which is what makes a rendered statement or a canonical key stable
    across runs.
    """
    return [(e, p[e]) for e in sorted(p, key=_sort_key)]


def to_string(p, names=None):
    """Render `p` as a human-readable string, e.g. ``"3/4*x0^2*x1 - 2"``.

    Terms are ordered by graded lexicographic degree, highest first; the zero
    polynomial renders as ``"0"``.  `names` overrides the default ``x0, x1, ...``
    and must have one entry per variable.

    Guarantees determinism.  There is no parser for this format on purpose: if a
    solver must return a polynomial, ship the JSON form (see ``to_json``) so the
    output contract has exactly one shape to grade.
    """
    if not p:
        return "0"
    n = arity(p)
    if names is None:
        names = ["x%d" % i for i in range(n)]
    elif len(names) != n:
        raise ValueError("expected %d names, got %d" % (n, len(names)))
    pieces = []
    for exps, coeff in reversed(terms(p)):
        factors = []
        for i, e in enumerate(exps):
            if e == 1:
                factors.append(str(names[i]))
            elif e > 1:
                factors.append("%s^%d" % (names[i], e))
        mag = abs(coeff)
        if factors and mag == 1:
            body = "*".join(factors)
        elif factors:
            body = str(mag) + "*" + "*".join(factors)
        else:
            body = str(mag)
        sign = "-" if coeff < 0 else "+"
        pieces.append((sign, body))
    head_sign, head_body = pieces[0]
    out = ("-" + head_body) if head_sign == "-" else head_body
    for sign, body in pieces[1:]:
        out += " %s %s" % (sign, body)
    return out


def to_json(p):
    """Encode `p` in the JSON-native form.

    Returns ``{"nvars": n, "terms": [[[e0, ..., e_{n-1}], [num, den]], ...]}``
    with terms in ascending graded lexicographic order and ``nvars`` equal to 0
    only for the zero polynomial.  Guarantees ints-and-lists only (``json.dumps``
    accepts it directly) and a round trip: ``equal(from_json(to_json(p)), p)``.
    """
    n = arity(p)
    return {
        "nvars": 0 if n is None else n,
        "terms": [[list(e), _rat_to_json(c)] for e, c in terms(p)],
    }


def from_json(obj, nvars=None):
    """Decode a polynomial from JSON-native form.

    Accepts either the canonical dict produced by ``to_json`` or a bare list of
    ``[exponents, [num, den]]`` terms -- tolerant in, canonical out, which is
    what a ``parse_answer`` boundary wants.  Repeated exponent tuples are summed
    rather than silently overwriting each other.

    Guarantees a normalised polynomial, or ``TypeError``/``ValueError`` on
    malformed input; it never returns a partially-decoded object.  Pass `nvars`
    to require a specific arity (recommended in ``verify``: it turns a
    wrong-shape answer into a clean rejection instead of an exception later).
    """
    if isinstance(obj, dict):
        if "terms" not in obj:
            raise ValueError("polynomial JSON needs a 'terms' key")
        declared = obj.get("nvars")
        if declared is not None:
            if isinstance(declared, bool) or not isinstance(declared, int):
                raise TypeError("nvars must be an int, got %r" % (declared,))
            if nvars is not None and declared != 0 and declared != nvars:
                raise ValueError("declared nvars %d != required %d" % (declared, nvars))
            if nvars is None and declared != 0:
                nvars = declared
        raw_terms = obj["terms"]
    else:
        raw_terms = obj
    if not isinstance(raw_terms, (list, tuple)):
        raise TypeError("terms must be a list, got %s" % (type(raw_terms).__name__,))
    acc = {}
    width = nvars
    for item in raw_terms:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("each term must be [exponents, [num, den]], got %r"
                             % (item,))
        exps = _check_exponents(item[0], width)
        if width is None:
            width = len(exps)
        acc[exps] = acc.get(exps, _ZERO) + _rat_from_json(item[1])
    return {e: c for e, c in acc.items() if c != 0}


def to_univariate(p):
    """Dense ascending coefficient list of a one-variable polynomial.

    ``{(2,): 3, (0,): -1}`` becomes ``[-1, 0, 3]``.  Guarantees a list of
    ``Fraction`` with no trailing zero (``[]`` for the zero polynomial), which
    is exactly the representation ``gvlib.roots`` consumes.  Raises
    ``ValueError`` if `p` has more than one variable.
    """
    n = arity(p)
    if n is None:
        return []
    if n != 1:
        raise ValueError("expected a univariate polynomial, got arity %d" % (n,))
    d = degree(p)
    coeffs = [_ZERO] * (d + 1)
    for (e,), c in p.items():
        coeffs[e] = c
    return coeffs


def from_univariate(coeffs):
    """Build a one-variable polynomial from a dense ascending coefficient list.

    Inverse of ``to_univariate``: ``from_univariate([-1, 0, 3])`` is
    ``{(0,): -1, (2,): 3}``.  Guarantees a normalised polynomial; coefficients
    go through ``rationals.Q``.
    """
    out = {}
    for e, c in enumerate(coeffs):
        q = Q(c)
        if q != 0:
            out[(e,)] = q
    return out


def gram_form(matrix, basis):
    """The polynomial ``sum_{i,j} G[i][j] * m_i * m_j`` for a Gram matrix G.

    `matrix` is a square nested sequence of rationals and `basis` is a list of
    exponent tuples, one per row: ``m_i`` is the monomial with exponents
    ``basis[i]``.  Guarantees the exact expansion, with like terms collected.
    `matrix` need not be symmetric -- an asymmetric entry contributes through
    both ``G[i][j]`` and ``G[j][i]``, exactly as in ``v^T G v``.

    This is the bridge that makes an SOS / Gram certificate checkable in three
    lines: expand the claimed Gram form, subtract the target polynomial, and
    assert ``is_zero``.  Pair it with ``exact_matrices.is_psd``.
    """
    k = len(basis)
    if k == 0:
        raise ValueError("basis must be non-empty")
    if len(matrix) != k:
        raise ValueError("matrix has %d rows but basis has %d monomials"
                         % (len(matrix), k))
    exps = [_check_exponents(b, None) for b in basis]
    width = len(exps[0])
    for e in exps:
        if len(e) != width:
            raise ValueError("basis monomials have mixed arity")
    out = {}
    for i, row in enumerate(matrix):
        if len(row) != k:
            raise ValueError("matrix row %d has length %d, expected %d"
                             % (i, len(row), k))
        for j, entry in enumerate(row):
            c = Q(entry)
            if c == 0:
                continue
            e = tuple(a + b for a, b in zip(exps[i], exps[j]))
            total = out.get(e, _ZERO) + c
            if total == 0:
                out.pop(e, None)
            else:
                out[e] = total
    return out
