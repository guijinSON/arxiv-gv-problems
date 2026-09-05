"""Native finite-geometry witness generator for arXiv:2512.24689.

The paper constructs three disjoint F_q-linear blocking sets from subspaces of
F_{q^h}^3.  This module uses q=2 and asks for an explicit nonzero vector in the
intersection of each displayed subspace with a displayed projective line.
Generation is by composition of identities: the unique binary dependence among
1, a, ..., a^h is the defining polynomial of a, and the bases are assembled so
that this dependence is the requested intersection vector.  The generator never
solves a generated instance.
"""

from __future__ import annotations

import functools
import hashlib
import itertools
import json
import os
import random
import re
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - supported fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "geometry",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "polynomial",
    "native_objects": [
        "three F_2-linear subspaces of GF(2^n)^3",
        "their induced Redei-type blocking sets in PG(2,2^n)",
        "three projective lines and binary coordinate polynomials",
    ],
    "verification_operations": [
        "carryless polynomial reduction over GF(2)",
        "exact finite-field linear combination",
        "exact projective line incidence",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The line evaluations of the displayed basis rows form a cyclically "
        "shifted, scaled power basis, so their sole binary dependence is the "
        "field's defining polynomial; without recognizing it one performs "
        "dense binary elimination."
    ),
    "hardness_basis": (
        "Track B: Gaussian nullspace elimination solves the certificate in "
        "O(n^3) bit operations; the final self-test records its measured "
        "shipping-preset wall time and operation count, while the compact "
        "power-basis route takes at most n+5 exact field operations and must "
        "be recognized from the projective incidence data without tools."
    ),
    "max_answer_tokens": 15,
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
        "One nonzero binary polynomial C(T)=c_0+c_1*T+...+c_n*T^n, "
        "encoded by the exactly n+1 coefficient characters c_0...c_n."
    ),
    "bounds": {
        "polynomials": 1,
        "coefficient_field": "GF(2)",
        "max_degree": "n",
        "coefficient_characters": "n+1",
        "zero_polynomial_excluded": True,
    },
}

DIFFICULTY: dict = {"easy": {"n": 61}}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The displayed line-evaluation columns are scaled cyclic orderings of one "
    "power basis."
)
PLACEBO_HINT = (
    "The displayed hexadecimal columns reward careful bookkeeping across all "
    "indexed rows."
)

# Script-owned oracle evidence is copied here after STEP 4 and the two G9 runs.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

NOTES = r"""
STEP 0.  Definition 2.2 fixes Redei-type blocking sets.  Example 2.4 and the
Grassmann-dimension argument immediately before it identify the paper's native
objects: an (h+1)-dimensional F_q-subspace U of F_(q^h)^3 induces a blocking set,
and a nonzero vector of U in a line's two-dimensional vector subspace is an
executable incidence witness.  Lemma 3.2 gives the coordinate form used here.

Theorem 4.1 gives exact sufficient conditions for L, phi(L), and phi^2(L) to be
pairwise disjoint, where phi(X:Y:Z)=(Z:X:Y).  For q=2, beta=1, h>=4, and the
functional f(1)=f(alpha^2)=1, f(alpha)=0, with its last coefficient chosen from
1/(alpha+1), the two conditions reduce to two direct bit checks.  Thus these
three subspaces induce the paper's 3-fold blocking set.  The easy h=2 Baer case
and the small-characteristic line-union constructions of Section 2.1 are not
used.

The discriminating certificate question rules out Track A: from any displayed
basis and line, a specialist forms an n by (n+1) binary incidence matrix and
finds its nullspace by Gaussian elimination in O(n^3) bit operations.  This is
the Track B reference algorithm and is deliberately reported as successful,
not placed among the failing attacks.

Generation is composition of identities, not post-hoc solving.  A contact point
and tangent line are sampled first.  The basis is then lifted from a scaled,
cyclic ordering of 1,alpha,...,alpha^n.  The identity m(alpha)=0 supplies its
known coordinate polynomial, and one kernel-vector adjustment makes the lifts a
basis with exactly that dependence.  A random projectivity finally scrambles
all coordinates while carrying every certificate with it.

The outlier attack selects one unusually small row, the greedy attack repeatedly
reduces the Hamming weight of a partial syndrome, random restart samples legal
nonzero coefficient polynomials, and the no-tool ansatz copies the unshifted
modulus coefficients.  Nonzero syndromes defeat the unit-vector probe; shifts
are chosen to defeat the direct-copy ansatz; the remaining two are checked on
every adversary seed.
""".strip()


# ---------------------------------------------------------------------------
# Binary polynomials and GF(2^n)


def _validate_n(n: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 4 or n > 510:
        raise ValueError("n must be an integer from 4 through 510")


def _poly_rem(value: int, modulus: int) -> int:
    md = modulus.bit_length() - 1
    while value and value.bit_length() - 1 >= md:
        value ^= modulus << (value.bit_length() - 1 - md)
    return value


def _poly_gcd(a: int, b: int) -> int:
    while b:
        a, b = b, _poly_rem(a, b)
    return a


def _poly_divmod(a: int, b: int) -> tuple[int, int]:
    q = 0
    bd = b.bit_length() - 1
    while a and a.bit_length() - 1 >= bd:
        shift = a.bit_length() - 1 - bd
        q ^= 1 << shift
        a ^= b << shift
    return q, a


def _gf_mul(a: int, b: int, modulus: int, n: int) -> int:
    if a.bit_length() < b.bit_length():
        a, b = b, a
    result = 0
    top = 1 << n
    while b:
        if b & 1:
            result ^= a
        b >>= 1
        a <<= 1
        if a & top:
            a ^= modulus
    return result & (top - 1)


def _gf_square(a: int, modulus: int, n: int) -> int:
    return _gf_mul(a, a, modulus, n)


def _gf_pow(a: int, exponent: int, modulus: int, n: int) -> int:
    result = 1
    while exponent:
        if exponent & 1:
            result = _gf_mul(result, a, modulus, n)
        a = _gf_square(a, modulus, n)
        exponent >>= 1
    return result


def _gf_inv(a: int, modulus: int, n: int) -> int:
    if not a:
        raise ZeroDivisionError("zero has no inverse")
    return _gf_pow(a, (1 << n) - 2, modulus, n)


def _prime_divisors(value: int) -> list[int]:
    out = []
    d = 2
    while d * d <= value:
        if value % d == 0:
            out.append(d)
            while value % d == 0:
                value //= d
        d += 1
    if value > 1:
        out.append(value)
    return out


def _is_irreducible(modulus: int, n: int) -> bool:
    if modulus.bit_length() != n + 1 or not (modulus & 1):
        return False
    x = 2
    value = x
    for _ in range(n):
        value = _gf_square(value, modulus, n)
    if value != x:
        return False
    for prime in _prime_divisors(n):
        value = x
        for _ in range(n // prime):
            value = _gf_square(value, modulus, n)
        if _poly_gcd(value ^ x, modulus) != 1:
            return False
    return True


@functools.lru_cache(maxsize=None)
def _modulus(n: int) -> int:
    """A deterministic, nonsparse irreducible binary polynomial of degree n."""
    _validate_n(n)
    rng = random.Random(0x251224689 ^ (n << 17))
    top = 1 << n
    while True:
        candidate = top | 1 | (rng.getrandbits(n - 1) << 1)
        weight = candidate.bit_count()
        if 3 <= weight <= n - 1 and _is_irreducible(candidate, n):
            return candidate


def _functional_t(modulus: int, n: int) -> int:
    """Choose f(alpha^(n-1)) so Theorem 4.1 holds when q=2."""
    # Irreducibility and n>1 imply m(1)=1.  Therefore
    # 1/(alpha+1) = (m(alpha)+m(1))/(alpha+1).
    quotient, remainder = _poly_divmod(modulus ^ 1, 0b11)
    if remainder or ((quotient >> (n - 1)) & 1) != 1:
        raise AssertionError("unexpected synthetic-division identity")
    return 1 ^ (quotient & 1) ^ ((quotient >> 2) & 1)


def _f(value: int, n: int, t: int) -> int:
    return ((value & 1) ^ ((value >> 2) & 1)
            ^ (t & ((value >> (n - 1)) & 1)))


def _dot(line: list[int], point: tuple[int, int, int] | list[int],
         modulus: int, n: int) -> int:
    return (_gf_mul(line[0], point[0], modulus, n)
            ^ _gf_mul(line[1], point[1], modulus, n)
            ^ _gf_mul(line[2], point[2], modulus, n))


def _combine(rows: list[list[int]] | list[tuple[int, int, int]], mask: int
             ) -> tuple[int, int, int]:
    x = y = z = 0
    index = 0
    while mask:
        if mask & 1:
            row = rows[index]
            x ^= row[0]
            y ^= row[1]
            z ^= row[2]
        mask >>= 1
        index += 1
    return x, y, z


def _rank_bits(values: list[int]) -> int:
    pivots: dict[int, int] = {}
    for value in values:
        while value:
            pivot = value.bit_length() - 1
            if pivot in pivots:
                value ^= pivots[pivot]
            else:
                pivots[pivot] = value
                break
    return len(pivots)


def _linear_basis_with_reps(columns: list[int], n: int
                            ) -> list[tuple[int, int] | None]:
    pivots: list[tuple[int, int] | None] = [None] * n
    for index, original in enumerate(columns):
        value = original
        rep = 1 << index
        while value:
            pivot = value.bit_length() - 1
            entry = pivots[pivot]
            if entry is None:
                pivots[pivot] = (value, rep)
                break
            value ^= entry[0]
            rep ^= entry[1]
    if any(entry is None for entry in pivots):
        raise ValueError("linear map is not onto")
    return pivots


def _preimage(target: int, pivots: list[tuple[int, int] | None]) -> int:
    rep = 0
    value = target
    while value:
        pivot = value.bit_length() - 1
        entry = pivots[pivot]
        if entry is None:
            raise ValueError("target outside image")
        value ^= entry[0]
        rep ^= entry[1]
    return rep


# ---------------------------------------------------------------------------
# The paper's three subspaces and projective transformations


def _base_subspace(modulus: int, n: int) -> list[tuple[int, int, int]]:
    t = _functional_t(modulus, n)
    rows = []
    for j in range(n):
        value = 1 << j
        rows.append((value, _f(value, n, t), 0))
    rows.append((0, 2, 1))       # (0, alpha, beta), beta=1
    return rows


def _rotate(point: tuple[int, int, int], amount: int
            ) -> tuple[int, int, int]:
    amount %= 3
    if amount == 0:
        return point
    if amount == 1:
        return point[2], point[0], point[1]
    return point[1], point[2], point[0]


def _mat_vec(matrix: list[list[int]], vector: tuple[int, int, int],
             modulus: int, n: int) -> tuple[int, int, int]:
    return tuple(
        _gf_mul(row[0], vector[0], modulus, n)
        ^ _gf_mul(row[1], vector[1], modulus, n)
        ^ _gf_mul(row[2], vector[2], modulus, n)
        for row in matrix
    )  # type: ignore[return-value]


def _mat_inv(matrix: list[list[int]], modulus: int, n: int) -> list[list[int]]:
    rows = [list(row) + [1 if i == j else 0 for j in range(3)]
            for i, row in enumerate(matrix)]
    for col in range(3):
        pivot = next((r for r in range(col, 3) if rows[r][col]), None)
        if pivot is None:
            raise ValueError("singular matrix")
        rows[col], rows[pivot] = rows[pivot], rows[col]
        inv = _gf_inv(rows[col][col], modulus, n)
        rows[col] = [_gf_mul(v, inv, modulus, n) for v in rows[col]]
        for r in range(3):
            if r != col and rows[r][col]:
                factor = rows[r][col]
                rows[r] = [a ^ _gf_mul(factor, b, modulus, n)
                           for a, b in zip(rows[r], rows[col])]
    return [row[3:] for row in rows]


def _random_gl3(rng: random.Random, modulus: int, n: int) -> tuple[list[list[int]], list[list[int]]]:
    while True:
        matrix = [[rng.getrandbits(n) for _ in range(3)] for _ in range(3)]
        try:
            return matrix, _mat_inv(matrix, modulus, n)
        except ValueError:
            pass


def _line_transform(line: list[int], inverse: list[list[int]],
                    modulus: int, n: int) -> list[int]:
    return [
        _gf_mul(line[0], inverse[0][j], modulus, n)
        ^ _gf_mul(line[1], inverse[1][j], modulus, n)
        ^ _gf_mul(line[2], inverse[2][j], modulus, n)
        for j in range(3)
    ]


def _projective_norm(point: tuple[int, int, int] | list[int],
                     modulus: int, n: int) -> tuple[int, int, int]:
    pivot = next((v for v in point if v), None)
    if pivot is None:
        raise ValueError("zero projective vector")
    inv = _gf_inv(pivot, modulus, n)
    return tuple(_gf_mul(v, inv, modulus, n) for v in point)  # type: ignore[return-value]


def _sample_line_through(point: tuple[int, int, int], base_rows: list[tuple[int, int, int]],
                         previous_points: list[tuple[int, int, int]], rng: random.Random,
                         modulus: int, n: int) -> tuple[list[int], list[int]]:
    pivot = next(i for i, value in enumerate(point) if value)
    inv = _gf_inv(point[pivot], modulus, n)
    # A weight-one point has about half of its incident lines tangent.  A
    # higher-weight representative has none; cap this inner trial so the outer
    # constructor can discard such a point instead of spending 10,000 draws.
    for _ in range(128):
        line = [rng.getrandbits(n) for _ in range(3)]
        subtotal = 0
        for i in range(3):
            if i != pivot:
                subtotal ^= _gf_mul(line[i], point[i], modulus, n)
        line[pivot] = _gf_mul(subtotal, inv, modulus, n)
        if not any(line):
            continue
        if any(_dot(line, old, modulus, n) == 0 for old in previous_points):
            continue
        syndromes = [_dot(line, row, modulus, n) for row in base_rows]
        if _rank_bits(syndromes) == n:
            return line, syndromes
    raise RuntimeError("could not sample a tangent line")


def _noncollinear(points: list[tuple[int, int, int]], modulus: int, n: int) -> bool:
    if len(points) < 3:
        return True
    a, b, c = points[-3:]
    det = (
        _gf_mul(a[0], _gf_mul(b[1], c[2], modulus, n)
                ^ _gf_mul(b[2], c[1], modulus, n), modulus, n)
        ^ _gf_mul(a[1], _gf_mul(b[0], c[2], modulus, n)
                  ^ _gf_mul(b[2], c[0], modulus, n), modulus, n)
        ^ _gf_mul(a[2], _gf_mul(b[0], c[1], modulus, n)
                  ^ _gf_mul(b[1], c[0], modulus, n), modulus, n)
    )
    return det != 0


def _mask_to_word(mask: int, width: int) -> str:
    return "".join("1" if (mask >> j) & 1 else "0" for j in range(width))


def _word_to_mask(word: str) -> int:
    mask = 0
    for j, char in enumerate(word):
        if char == "1":
            mask |= 1 << j
    return mask


def _greedy_word(syndromes: list[int]) -> str:
    remaining = set(range(len(syndromes)))
    first = min(remaining, key=lambda j: (syndromes[j].bit_count(), j))
    chosen = 1 << first
    value = syndromes[first]
    remaining.remove(first)
    while remaining and value:
        best = min(remaining,
                   key=lambda j: ((value ^ syndromes[j]).bit_count(), j))
        new_value = value ^ syndromes[best]
        if new_value.bit_count() >= value.bit_count():
            break
        chosen |= 1 << best
        value = new_value
        remaining.remove(best)
    return _mask_to_word(chosen, len(syndromes))


def _make_panel(component: int, relation_mask: int, targets: list[int],
                canonical_rows: list[tuple[int, int, int]],
                previous_points: list[tuple[int, int, int]],
                previous_lines: list[list[int]], rng: random.Random,
                modulus: int, n: int) -> tuple[dict, tuple[int, int, int], list[int]]:
    width = n + 1
    component_rows = [_rotate(row, component) for row in canonical_rows]
    for _ in range(10000):
        vector_mask = rng.randrange(1, 1 << width)
        point = _combine(component_rows, vector_mask)
        point_norm = _projective_norm(point, modulus, n)
        if any(point_norm == _projective_norm(old, modulus, n)
               for old in previous_points):
            continue
        if any(_dot(old_line, point, modulus, n) == 0
               for old_line in previous_lines):
            continue
        if len(previous_points) == 2 and not _noncollinear(
                previous_points + [point], modulus, n):
            continue
        try:
            line, source_syndromes = _sample_line_through(
                point, component_rows, previous_points, rng, modulus, n)
        except RuntimeError:
            continue
        pivots = _linear_basis_with_reps(source_syndromes, n)
        lifts = []
        for target in targets:
            lift = _preimage(target, pivots)
            if rng.getrandbits(1):
                lift ^= vector_mask
            lifts.append(lift)
        combination = 0
        for j in range(width):
            if (relation_mask >> j) & 1:
                combination ^= lifts[j]
        if combination not in (0, vector_mask):
            raise AssertionError("lifted relation escaped the tangent kernel")
        if combination == 0:
            adjust = next(j for j in range(width)
                          if (relation_mask >> j) & 1)
            lifts[adjust] ^= vector_mask
        basis = [list(_combine(component_rows, lift)) for lift in lifts]
        if _rank_bits(lifts) != width:
            raise AssertionError("constructed rows are not a basis")
        syndromes = [_dot(line, row, modulus, n) for row in basis]
        if syndromes != targets:
            raise AssertionError("lift did not preserve requested syndrome")
        if _greedy_word(syndromes) == _mask_to_word(relation_mask, width):
            continue
        return ({
            "component": component,
            "line": line,
            "basis": basis,
            "syndromes": syndromes,
        }, point, line)
    raise RuntimeError("could not construct a resistant query panel")


def _theorem_conditions(modulus: int, n: int) -> bool:
    """Direct exact check of Theorem 4.1 for q=2, alpha=x, beta=1."""
    t = _functional_t(modulus, n)
    alpha = 2
    if _f(alpha, n, t) == 1:
        return False
    for k in (0, 1):
        inv = _gf_inv(alpha ^ k, modulus, n)
        rhs = (1
               ^ (_f(inv, n, t) ^ k) * _f(alpha, n, t)
               ^ k * _f(inv, n, t) * _f(1, n, t))
        if k == rhs:
            return False
    return True


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Construct a certified three-panel projective-incidence instance."""
    if params:
        unknown = ", ".join(sorted(params))
        raise TypeError(f"unknown parameters: {unknown}")
    _validate_n(n)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    modulus = _modulus(n)
    if not _theorem_conditions(modulus, n):
        raise AssertionError("paper construction conditions failed")
    width = n + 1
    modulus_mask = modulus & ((1 << width) - 1)
    modulus_word = _mask_to_word(modulus_mask, width)

    # A nonzero cyclic shift defeats the direct-copy ansatz while retaining the
    # paper's m(alpha)=0 relation.
    shifts = list(range(1, width))
    rng.shuffle(shifts)
    shift = next(s for s in shifts
                 if modulus_word[s:] + modulus_word[:s] != modulus_word)
    exponent_order = [(j + shift) % width for j in range(width)]
    relation_mask = 0
    for position, exponent in enumerate(exponent_order):
        if (modulus >> exponent) & 1:
            relation_mask |= 1 << position
    answer_word = _mask_to_word(relation_mask, width)

    powers = [1]
    for _ in range(n):
        powers.append(_gf_mul(powers[-1], 2, modulus, n))

    canonical_rows = _base_subspace(modulus, n)
    panels = []
    points: list[tuple[int, int, int]] = []
    lines: list[list[int]] = []
    for component in range(3):
        # Independent nonzero scales make per-row magnitude heuristics useless,
        # but do not change the binary dependence.
        while True:
            scale = rng.randrange(1, 1 << n)
            targets = [_gf_mul(scale, powers[e], modulus, n)
                       for e in exponent_order]
            if _greedy_word(targets) != answer_word:
                break
        panel, point, line = _make_panel(
            component, relation_mask, targets, canonical_rows,
            points, lines, rng, modulus, n)
        panels.append(panel)
        points.append(point)
        lines.append(line)

    matrix, inverse = _random_gl3(rng, modulus, n)
    for panel in panels:
        panel["basis"] = [list(_mat_vec(matrix, tuple(row), modulus, n))
                          for row in panel["basis"]]
        panel["line"] = _line_transform(panel["line"], inverse, modulus, n)
        recomputed = [_dot(panel["line"], row, modulus, n)
                      for row in panel["basis"]]
        if recomputed != panel["syndromes"]:
            raise AssertionError("projectivity failed to preserve incidence")

    return {
        "n": n,
        "field_modulus": modulus,
        "field_modulus_word": modulus_word,
        "alpha": 2,
        "panels": panels,
        "answer": {"coefficients": answer_word},
    }


# ---------------------------------------------------------------------------
# Statement, parser, verifier, and candidate language


def _hex(value: int, n: int) -> str:
    return "0x" + format(value, f"0{(n + 3) // 4}x")


def _modulus_expression(modulus: int, n: int) -> str:
    terms = []
    for exponent in range(n, -1, -1):
        if not ((modulus >> exponent) & 1):
            continue
        if exponent == 0:
            terms.append("1")
        elif exponent == 1:
            terms.append("X")
        else:
            terms.append(f"X^{exponent}")
    return " + ".join(terms)


def render(inst: dict) -> str:
    n = inst["n"]
    width = n + 1
    lines = [
        "PROJECTIVE SUBSPACE--LINE INTERSECTION CERTIFICATE",
        "",
        f"Let F = GF(2)[X]/(m(X)), where m(X) = {_modulus_expression(inst['field_modulus'], n)}.",
        f"Its bit-polynomial integer is {_hex(inst['field_modulus'], n + 1)} and deg(m)={n}.",
        "A hexadecimal field element encodes the coefficients of 1,X,...,X^(n-1) in its bits.",
        "Field addition is bitwise XOR.  Field multiplication is carryless polynomial multiplication",
        "followed by reduction modulo m(X).  All arithmetic below is exact in F.",
        "",
        "A projective point of PG(2,F) is a nonzero triple (x,y,z), up to multiplication",
        "by a nonzero field element.  A line [a,b,c] contains it exactly when",
        "a*x + b*y + c*z = 0 in F.",
        "",
        "Each panel gives an F_2-basis b_0,...,b_n of one of three (n+1)-dimensional",
        "F_2-subspaces U of F^3.  Such a U induces the linear blocking set",
        "L_U = {<u>_F : u in U and u != 0}.  The three underlying blocking sets are",
        "pairwise disjoint Redei-type sets from the construction; together they form",
        "a 3-fold blocking set.  The row S is an audit value equal to the exact line",
        "evaluation a*x+b*y+c*z of that row.",
        "",
        f"Find one nonzero binary coordinate polynomial C(T)=c_0+...+c_{n}T^{n}.",
        f"Use the SAME {width} coefficients in all three panels.  For every panel,",
        "the vector sum c_0*b_0 XOR ... XOR c_n*b_n must be nonzero and lie on",
        "that panel's line.  Coefficients are in GF(2), and row indexing is 0-based.",
        "",
    ]
    for pindex, panel in enumerate(inst["panels"]):
        lines.append(f"PANEL {pindex} (blocking-set component {panel['component']}):")
        lines.append("line = [" + ", ".join(_hex(v, n) for v in panel["line"]) + "]")
        lines.append("row : X-coordinate  Y-coordinate  Z-coordinate  | S")
        for index, (row, syndrome) in enumerate(zip(panel["basis"], panel["syndromes"])):
            lines.append(
                f"{index:>3} : {_hex(row[0], n)} {_hex(row[1], n)} "
                f"{_hex(row[2], n)} | {_hex(syndrome, n)}")
        lines.append("")
    lines.extend([
        "Encode C by the coefficient word c_0c_1...c_n (constant coefficient first).",
        f"It must contain exactly {width} characters, each 0 or 1, and may not be all zero.",
        "Give your final answer inside <answer></answer> tags as a JSON object with",
        'exactly the key "coefficients".  Example: <answer>{"coefficients":"10100"}</answer>',
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    candidates = []
    tagged = re.search(r"<answer>\s*(.*?)\s*</answer>", text,
                       flags=re.IGNORECASE | re.DOTALL)
    if tagged:
        candidates.append(tagged.group(1))
    candidates.extend(re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text,
                                 flags=re.IGNORECASE | re.DOTALL))
    # Last-resort balanced-object scan for prose without the required tags.
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            value, _ = decoder.raw_decode(text[match.start():])
            if isinstance(value, dict):
                candidates.append(json.dumps(value))
        except (ValueError, json.JSONDecodeError):
            pass
    for candidate in candidates:
        candidate = candidate.strip()
        if candidate.startswith("```") and candidate.endswith("```"):
            candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate,
                               flags=re.IGNORECASE)
        try:
            value = json.loads(candidate)
        except (TypeError, ValueError):
            continue
        if (isinstance(value, dict) and set(value) == {"coefficients"}
                and isinstance(value["coefficients"], str)):
            return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if "coefficients" not in answer:
        return False, "answer is missing the coefficients field"
    if set(answer) != {"coefficients"}:
        return False, "answer has an unexpected field"
    word = answer["coefficients"]
    if not isinstance(word, str):
        return False, "coefficients must be a string"
    if word == "":
        return False, "coefficient word is empty"
    width = inst["n"] + 1
    if len(word) < width:
        return False, "coefficient word is too short"
    if len(word) > width:
        return False, "coefficient word is too long"
    if any(char not in "01" for char in word):
        return False, "coefficient word contains a nonbinary character"
    if "1" not in word:
        return False, "coefficient polynomial is zero"
    mask = _word_to_mask(word)
    modulus = inst["field_modulus"]
    n = inst["n"]
    for pindex, panel in enumerate(inst["panels"]):
        point = _combine(panel["basis"], mask)
        if point == (0, 0, 0):
            return False, f"panel {pindex} combination is the zero vector"
        if _dot(panel["line"], point, modulus, n) != 0:
            return False, f"panel {pindex} combination is not on its line"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    width = inst["n"] + 1
    mask = rng.randrange(1, 1 << width)
    return {"coefficients": _mask_to_word(mask, width)}


def search_space(inst: dict) -> int:
    return (1 << (inst["n"] + 1)) - 1


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space > 1_000_000:
        return None
    width = inst["n"] + 1
    count = 0
    for mask in range(1, 1 << width):
        ok, _ = verify(inst, {"coefficients": _mask_to_word(mask, width)})
        count += int(ok)
    return count


# ---------------------------------------------------------------------------
# Reference algorithm, attacks, and structural canonical key


def _null_word(syndromes: list[int], n: int,
               counter: dict | None = None) -> str:
    width = n + 1
    rows = []
    for bit in range(n):
        row = 0
        for col, value in enumerate(syndromes):
            if (value >> bit) & 1:
                row |= 1 << col
            if counter is not None:
                counter["bit_operations"] += 1
        rows.append(row)
    rank = 0
    pivots = []
    for col in range(width):
        pivot = next((r for r in range(rank, n) if (rows[r] >> col) & 1), None)
        if counter is not None:
            counter["bit_operations"] += max(1, n - rank)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for r in range(n):
            if r != rank and ((rows[r] >> col) & 1):
                rows[r] ^= rows[rank]
                if counter is not None:
                    counter["bit_operations"] += width
        pivots.append(col)
        rank += 1
        if rank == n:
            break
    free = [col for col in range(width) if col not in set(pivots)]
    if rank != n or len(free) != 1:
        raise ValueError("expected a one-dimensional binary nullspace")
    mask = 1 << free[0]
    for row_index, pivot_col in enumerate(pivots):
        if (rows[row_index] >> free[0]) & 1:
            mask |= 1 << pivot_col
    return _mask_to_word(mask, width)


def _reference_algorithm(inst: dict) -> tuple[dict, dict]:
    counter = {"bit_operations": 0}
    # The statement requires a common word; one dense nullspace solve suffices.
    word = _null_word(inst["panels"][0]["syndromes"], inst["n"], counter)
    answer = {"coefficients": word}
    ok, reason = verify(inst, answer)
    return answer, {
        "bit_operations": counter["bit_operations"],
        "verified": ok,
        "reason": reason,
    }


def _attack_answers(inst: dict, seed: int) -> dict[str, dict]:
    width = inst["n"] + 1
    first = inst["panels"][0]["syndromes"]
    outlier = min(range(width), key=lambda j: (first[j].bit_count(), j))
    modulus_word = inst["field_modulus_word"]
    rng = random.Random((seed << 32) ^ inst["field_modulus"] ^ 0xA77AC)
    random_hit = None
    for _ in range(256):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            random_hit = candidate
            break
    return {
        "outlier_low_hamming_row": {
            "coefficients": _mask_to_word(1 << outlier, width)},
        "greedy_xor_descent": {"coefficients": _greedy_word(first)},
        "random_restart_256": (random_hit or random_candidate(inst, rng)),
        "unshifted_modulus_copy": {"coefficients": modulus_word},
    }


def _contact_point(inst: dict, panel: dict) -> tuple[int, int, int]:
    word = _null_word(panel["syndromes"], inst["n"])
    return _combine(panel["basis"], _word_to_mask(word))


def canonical_key(inst: dict) -> str:
    """A projective/Frobenius invariant of the three marked tangent flags."""
    n = inst["n"]
    modulus = inst["field_modulus"]
    panels = inst["panels"]
    if len(panels) != 3:
        raise ValueError("canonical key expects exactly three panels")
    points = [_contact_point(inst, panel) for panel in panels]
    lines = [panel["line"] for panel in panels]
    cross = [[_dot(lines[i], points[j], modulus, n) for j in range(3)]
             for i in range(3)]
    if any(cross[i][i] != 0 for i in range(3)):
        raise ValueError("marked flag is not incident")
    if any(cross[i][j] == 0 for i in range(3) for j in range(3) if i != j):
        raise ValueError("unexpected cross-incidence")
    numerator = _gf_mul(
        _gf_mul(cross[0][1], cross[1][2], modulus, n),
        cross[2][0], modulus, n)
    denominator = _gf_mul(
        _gf_mul(cross[0][2], cross[2][1], modulus, n),
        cross[1][0], modulus, n)
    rho = _gf_mul(numerator, _gf_inv(denominator, modulus, n), modulus, n)
    orbit = []
    value = rho
    for _ in range(n):
        orbit.append(value)
        orbit.append(_gf_inv(value, modulus, n))
        value = _gf_square(value, modulus, n)
    canonical = min(orbit)
    payload = f"flag-cycle-v1:{n}:{modulus:x}:{canonical:x}".encode()
    return hashlib.sha256(payload).hexdigest()


def _g8_transform(inst: dict, seed: int) -> dict:
    rng = random.Random(seed ^ 0xC8A0)
    n = inst["n"]
    modulus = inst["field_modulus"]
    width = n + 1
    answer_word = inst["answer"]["coefficients"]
    panels = []
    for panel in inst["panels"]:
        panels.append({
            "component": panel["component"],
            "line": list(panel["line"]),
            "basis": [list(row) for row in panel["basis"]],
            "syndromes": list(panel["syndromes"]),
        })

    # A simultaneous row swap and elementary shear are genuine changes of the
    # common F_2 coordinate basis; carry the coefficient polynomial through.
    a, b = rng.sample(range(width), 2)
    chars = list(answer_word)
    chars[a], chars[b] = chars[b], chars[a]
    for panel in panels:
        panel["basis"][a], panel["basis"][b] = panel["basis"][b], panel["basis"][a]
        panel["syndromes"][a], panel["syndromes"][b] = panel["syndromes"][b], panel["syndromes"][a]
    a, b = rng.sample(range(width), 2)
    old_a = chars[a]
    chars[b] = str(int(chars[b]) ^ int(old_a))
    for panel in panels:
        panel["basis"][a] = [x ^ y for x, y in zip(panel["basis"][a], panel["basis"][b])]
        panel["syndromes"][a] ^= panel["syndromes"][b]

    matrix, inverse = _random_gl3(rng, modulus, n)
    frobenius_power = rng.randrange(n)
    for panel in panels:
        panel["basis"] = [list(_mat_vec(matrix, tuple(row), modulus, n))
                          for row in panel["basis"]]
        panel["line"] = _line_transform(panel["line"], inverse, modulus, n)
        for _ in range(frobenius_power):
            panel["basis"] = [[_gf_square(v, modulus, n) for v in row]
                              for row in panel["basis"]]
            panel["line"] = [_gf_square(v, modulus, n) for v in panel["line"]]
            panel["syndromes"] = [_gf_square(v, modulus, n)
                                  for v in panel["syndromes"]]
    order = list(range(3))
    rng.shuffle(order)
    panels = [panels[i] for i in order]
    return {
        "n": n,
        "field_modulus": modulus,
        "field_modulus_word": inst["field_modulus_word"],
        "alpha": inst["alpha"],
        "panels": panels,
        "answer": {"coefficients": "".join(chars)},
    }


def escalate(params: dict) -> dict | str | None:
    n = params.get("n")
    if isinstance(n, bool) or not isinstance(n, int):
        return None
    if n < 61:
        return {"n": 61}
    if n < 127:
        return {"n": 127}
    if n < 191:
        return {"n": 191}
    if n < 255:
        return {"n": 255}
    return "cap_bound"


# ---------------------------------------------------------------------------
# Mandatory gates


def _answer_metrics(answer: dict) -> tuple[int, int, int]:
    blob = json.dumps(answer, separators=(",", ":"))
    atoms = len(answer["coefficients"])
    # A conservative no-tokenizer upper bound; four characters per token is
    # optimistic for bit strings, so count eight bit characters per token plus
    # the small JSON wrapper token by token.
    tokens = (atoms + 7) // 8 + 7
    return len(blob), tokens, atoms


def selftest() -> dict:
    report: dict = {
        "paper": "2512.24689",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    # G1: every preset, multiple seeds, exact JSON round-trip.
    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in range(3):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            g1_attempts += 1
            if not ok or not json_ok:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": reason, "json": json_ok})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "verified": g1_attempts - len(g1_failures),
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=90210, **shipping)
    word = inst["answer"]["coefficients"]
    differing = next(i for i in range(len(word)) if word[i] != word[(i + 1) % len(word)])
    swapped = list(word)
    j = (differing + 1) % len(word)
    swapped[differing], swapped[j] = swapped[j], swapped[differing]
    corruptions = {
        "drop_one": {},
        "swap_two": {"coefficients": "".join(swapped)},
        "duplicate_one": {"coefficients": word + word[-1]},
        "empty": {"coefficients": ""},
        "out_of_range": {"coefficients": "2" + word[1:]},
    }
    g2_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        g2_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in g2_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": (all(entry["rejected"] for entry in g2_results.values())
                 and len(set(reasons)) == len(reasons)),
        "cases": g2_results,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = ("I used the shared null relation.\n```json\n<answer>"
                 + json.dumps(inst["answer"]) + "</answer>\n```\n")
    parsed = parse_answer(realistic)
    garbage = parse_answer("No certificate was found; {broken json].")
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and garbage is None,
        "realistic_response_parsed": parsed == inst["answer"],
        "garbage_returns_none": garbage is None,
    }

    # G4 and the shipping density part of G5 use the exact declared prior.
    sample_total = 200_000
    sample_rng = random.Random(0x6402512)
    hits = 0
    t0 = time.perf_counter()
    for _ in range(sample_total):
        hits += int(verify(inst, random_candidate(inst, sample_rng))[0])
    sample_seconds = time.perf_counter() - t0
    report["G4_guess_resistance"] = {
        "pass": hits / sample_total < 1e-6,
        "hits": hits,
        "total": sample_total,
        "observed_probability": hits / sample_total,
        "candidate_space": search_space(inst),
        "sampling_prior": "uniform nonzero binary coefficient polynomials",
    }

    demo_inst = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    reference_runs = []
    reference_times = []
    reference_ops = []
    shipping_instances = []
    for seed in range(8):
        current = make_instance(seed=seed + 1000, **shipping)
        shipping_instances.append(current)
        start = time.perf_counter()
        candidate, stats = _reference_algorithm(current)
        elapsed = time.perf_counter() - start
        reference_times.append(elapsed)
        reference_ops.append(stats["bit_operations"])
        reference_runs.append(bool(stats["verified"] and verify(current, candidate)[0]))

    # G6 attacks, all evaluated on the same eight shipping instances.
    attack_names = [
        "outlier_low_hamming_row", "greedy_xor_descent",
        "random_restart_256", "unshifted_modulus_copy",
    ]
    attack_counts = {name: 0 for name in attack_names}
    attack_start = time.perf_counter()
    for seed, current in enumerate(shipping_instances):
        for name, candidate in _attack_answers(current, seed).items():
            attack_counts[name] += int(verify(current, candidate)[0])
    attack_elapsed = time.perf_counter() - attack_start
    attacks = {name: {"successes": attack_counts[name], "attempts": 8}
               for name in attack_names}
    all_failed = all(entry["successes"] == 0 for entry in attacks.values())

    mean_reference = sum(reference_times) / len(reference_times)
    mean_ops = sum(reference_ops) / len(reference_ops)
    report["G5_density_and_baseline"] = {
        "pass": (demo_count == 1 and hits / sample_total < 1e-6
                 and all(reference_runs)),
        "shipping_sample_hits": hits,
        "shipping_sample_total": sample_total,
        "shipping_sampled_density": hits / sample_total,
        "shipping_exact_valid_answers_from_rank": 1,
        "shipping_exact_density": 1 / search_space(inst),
        "demo_exact_valid_answers": demo_count,
        "demo_candidate_space": search_space(demo_inst),
        "reference_mean_wall_sec": mean_reference,
        "reference_mean_bit_operations": mean_ops,
        "strongest_failing_attack_wall_sec_8_instances": attack_elapsed,
        "guess_sampling_wall_sec": sample_seconds,
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "binary Gaussian nullspace elimination",
            "complexity": "O(n^3) bit operations",
            "wall_clock_sec_mean": mean_reference,
            "operations_mean": mean_ops,
            "attempts": 8,
            "successes": sum(reference_runs),
            "solves": f"{sum(reference_runs)}/8, as expected",
        },
    }

    doubled_n = min(510, 2 * shipping["n"])
    doubled = make_instance(n=doubled_n, seed=314159)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_n > shipping["n"],
        "shipping_n": shipping["n"],
        "doubled_n": doubled_n,
        "doubled_verified": doubled_ok,
        "reason": doubled_reason,
    }

    invariant = carried = 0
    original_keys = []
    transformed_keys = []
    distinct_keys = []
    for seed in range(20):
        original = make_instance(seed=20_000 + seed, **shipping)
        transformed = _g8_transform(original, 30_000 + seed)
        key_a = canonical_key(original)
        key_b = canonical_key(transformed)
        original_keys.append(key_a)
        transformed_keys.append(key_b)
        invariant += int(key_a == key_b)
        carried += int(verify(transformed, transformed["answer"])[0])
        distinct_keys.append(key_a)
    report["G8_canonical_key"] = {
        "pass": invariant == 20 and carried == 20 and len(set(distinct_keys)) == 20,
        "invariant_composed_relabellings": invariant,
        "invariance_attempts": 20,
        "carried_witness_verifies": carried,
        "carried_witness_attempts": 20,
        "unrelated_distinct": len(set(distinct_keys)),
        "unrelated_attempts": 20,
        "transformations": [
            "simultaneous basis row swap and shear",
            "projective GL(3,F) coordinate change",
            "field Frobenius automorphism",
            "panel reordering",
        ],
    }

    chars, tokens, atoms = _answer_metrics(inst["answer"])
    intended_ops = inst["n"] + 5
    arms = G9_EVIDENCE
    hinted = arms.get("hinted", {"solved": 0, "attempts": 0})
    placebo = arms.get("placebo", {"solved": 0, "attempts": 0})
    hp = ((hinted.get("solved", 0) / hinted.get("attempts", 1))
          if hinted.get("attempts", 0) else None)
    pp = ((placebo.get("solved", 0) / placebo.get("attempts", 1))
          if placebo.get("attempts", 0) else None)
    report["G9_no_tool_suitability"] = {
        "pass": chars <= 2000 and atoms <= 256 and intended_ops <= 300,
        "arms": {
            "bare": arms.get("bare", {"solved": 0, "attempts": 0}),
            "hinted": hinted,
            "placebo": placebo,
        },
        "hinted_minus_placebo": (hp - pp if hp is not None and pp is not None else None),
        "hinted_verdict": arms.get("hinted_verdict", "not_run"),
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": atoms,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items()
             if key.startswith("G") and key[1:2].isdigit()]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
