"""Exact rational scalars, as a thin layer over ``fractions.Fraction``.

There is deliberately no arithmetic here: ``Fraction`` already adds, multiplies
and compares exactly.  What this module owns is the *boundary* -- coercion,
validation and the JSON-native encoding -- which is where verifiers actually go
wrong: a solver hands back ``"0.333"``, something calls ``float()`` on it, and a
grader that was supposed to be exact silently starts rounding.

JSON-native form of a rational is the two-element list ``[num, den]``; see
``gvlib/README.md``.  Floats are rejected everywhere, loudly.
"""

import re
from fractions import Fraction

__all__ = [
    "Q",
    "to_json",
    "from_json",
    "vector_to_json",
    "vector_from_json",
    "parse_rational",
    "bit_size",
    "within_bits",
]

# One exact rational literal: "7", "-7", "3/4", "-3 / 4".  No exponent notation.
_FRACTION_RE = re.compile(r"^([+-]?[0-9]+)(?:\s*/\s*([+-]?[0-9]+))?$")
# One exact decimal literal: "1.25", "-.5", "3.".  Read as a ratio of integers.
_DECIMAL_RE = re.compile(r"^([+-]?)([0-9]*)\.([0-9]*)$")


def _is_plain_int(x):
    """True for a genuine Python int.  ``bool`` is excluded on purpose."""
    return isinstance(x, int) and not isinstance(x, bool)


def Q(value):
    """Return `value` as an exact ``Fraction``.

    Accepts an ``int``, a ``Fraction``, an exact literal string ("7", "-3/4",
    "1.25"), or a two-element ``[num, den]`` sequence of ints.  Guarantees the
    result equals the input exactly -- no rounding happens anywhere.

    Raises ``TypeError`` on a ``float``, a ``bool`` or any other type, and
    ``ValueError`` on a malformed literal or a zero denominator.  Rejecting
    ``float`` is the point: ``Q(0.1)`` would otherwise be
    3602879701896397/36028797018963968 and every downstream equality would be
    subtly wrong.
    """
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool):
        raise TypeError("bool is not a rational; pass an int")
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, float):
        raise TypeError(
            "float is not exact; pass an int, a literal string, or [num, den]"
        )
    if isinstance(value, str):
        parsed = parse_rational(value)
        if parsed is None:
            raise ValueError("not an exact rational literal: %r" % (value,))
        return parsed
    if isinstance(value, (list, tuple)):
        return from_json(value)
    raise TypeError("cannot interpret %s as a rational" % (type(value).__name__,))


def to_json(value):
    """Encode a rational as the JSON-native ``[num, den]``.

    Guarantees: exactly two Python ints, in lowest terms, ``den > 0``, and
    ``from_json(to_json(q)) == Q(q)``.  The result contains only ints, so
    ``json.dumps`` accepts it and no float ever enters the serialisation.
    """
    q = Q(value)
    return [q.numerator, q.denominator]


def from_json(pair):
    """Decode the JSON-native ``[num, den]`` into a ``Fraction``.

    Strict on purpose, because this is what reads solver output: `pair` must be
    a list or tuple of exactly two genuine ints (``bool`` rejected, ``float``
    rejected, nested lists rejected) and ``den`` must be non-zero.  Guarantees a
    ``Fraction`` equal to ``num/den`` in lowest terms with a positive
    denominator.  Raises ``TypeError``/``ValueError`` otherwise; it never
    returns an approximation.
    """
    if not isinstance(pair, (list, tuple)):
        raise TypeError("rational must be a [num, den] list, got %s"
                        % (type(pair).__name__,))
    if len(pair) != 2:
        raise ValueError("rational must have exactly 2 entries, got %d" % (len(pair),))
    num, den = pair
    if not _is_plain_int(num) or not _is_plain_int(den):
        raise TypeError("rational entries must be ints, got %r" % (pair,))
    if den == 0:
        raise ValueError("zero denominator in %r" % (pair,))
    return Fraction(num, den)


def vector_to_json(values):
    """Encode a sequence of rationals as a list of ``[num, den]`` pairs.

    Guarantees a list of the same length whose entries each satisfy the
    ``to_json`` contract.  A vector is therefore a list of 2-lists, never a flat
    list -- that is what keeps "a rational" and "a vector" distinguishable.
    """
    return [to_json(v) for v in values]


def vector_from_json(items):
    """Decode a list of ``[num, den]`` pairs into a list of ``Fraction``.

    Raises ``TypeError``/``ValueError`` if `items` is not a list/tuple or if any
    entry fails ``from_json``.  Guarantees a list of the same length.
    """
    if not isinstance(items, (list, tuple)):
        raise TypeError("expected a list of [num, den] pairs, got %s"
                        % (type(items).__name__,))
    return [from_json(x) for x in items]


def parse_rational(text):
    """Parse one exact rational literal out of `text`, or return ``None``.

    Accepts "7", "-7", "3/4", "-3 / 4", "1.25", "-.5", with surrounding
    whitespace.  Rejects everything else -- exponent notation ("1e5"), bare
    words, empty strings, "1/0" -- by returning ``None``.

    Guarantees: never raises, never uses ``float``.  "1.25" is read as 125/100,
    not as the nearest binary double.  Intended for ``parse_answer``, where
    malformed model output must produce ``None`` rather than an exception.
    """
    if not isinstance(text, str):
        return None
    s = text.strip()
    m = _FRACTION_RE.match(s)
    if m:
        num = int(m.group(1))
        den = 1 if m.group(2) is None else int(m.group(2))
        if den == 0:
            return None
        return Fraction(num, den)
    m = _DECIMAL_RE.match(s)
    if m:
        sign, whole, frac = m.group(1), m.group(2), m.group(3)
        if not whole and not frac:
            return None
        digits = (whole or "0") + frac
        value = Fraction(int(digits), 10 ** len(frac))
        return -value if sign == "-" else value
    return None


def bit_size(value):
    """Bit length of the larger of |numerator| and denominator.

    Guarantees a non-negative int; ``bit_size(0) == 1`` because 0/1 has
    denominator 1.  Use it to enforce the ``coeff_bits`` bound a family declares
    in ``CERTIFICATE_LANGUAGE``: an unenforced bound makes ``search_space`` a
    fiction.
    """
    q = Q(value)
    return max(abs(q.numerator).bit_length(), q.denominator.bit_length(), 1)


def within_bits(value, bits):
    """True iff ``bit_size(value) <= bits``.

    Guarantees a plain bool and no side effects.  `bits` must be a positive int.
    """
    if not _is_plain_int(bits) or bits <= 0:
        raise ValueError("bits must be a positive int, got %r" % (bits,))
    return bit_size(value) <= bits
