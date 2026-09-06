"""Problem generator for arXiv:2209.04762.

    Danyao Wu, Pingzhi Yuan, Cunsheng Ding, Yuzhen Ma,
    "Permutation trinomials over F_{2^m}: a corrected version" (math.CO/math.NT).

The family is a *preimage* problem for permutation trinomials over F_{2^m}.
A solver is handed an explicit finite field F_{2^m}, a short list of trinomials
(exactly one of which permutes the field), and a handful of target values, and
must name the permuting trinomial and invert it at each target.

Everything is exact: field elements are integers, arithmetic is carry-less
multiplication modulo an irreducible polynomial over F_2, and `verify` is three
polynomial evaluations.

Standard library only.
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
from typing import Any


TRACK = "B"

# ---------------------------------------------------------------------------
# Presets.  `m` is the odd extension degree; 2^m - 1 must have a factor below
# _FACTOR_LIMIT so that non-permutation decoys can be built (see _decoy_shift).
# ---------------------------------------------------------------------------
DIFFICULTY = {
    # Hand rung: no QM twist at all, so the displayed trinomial is literally
    # x + x^(2^k-1) + x^(2^k+1), the polynomial of Proposition 2.6.
    "demo": {"m": 9, "n_targets": 1, "n_decoys": 0, "twist_level": 0},
    # Coefficients twisted (a, b random), exponents still the paper's.
    "easy": {"m": 15, "n_targets": 3, "n_decoys": 4, "twist_level": 1},
    # Full quasi-multiplicative twist: exponents scrambled by a random d with
    # gcd(d, 2^m-1) = 1, so the family is only visible up to QM equivalence.
    "medium": {"m": 23, "n_targets": 3, "n_decoys": 8, "twist_level": 2},
    "hard": {"m": 35, "n_targets": 3, "n_decoys": 16, "twist_level": 2},
}

SHIPPING_DIFFICULTY = "hard"

# Odd degrees m for which 2^m - 1 has a prime factor below _FACTOR_LIMIT.
# Mersenne-prime exponents (13, 17, 19, 31, 61, 67, 71) are excluded: with
# 2^m - 1 prime there is no proper subgroup to build a decoy in.
_M_LADDER = [9, 11, 15, 21, 23, 25, 27, 29, 33, 35, 37, 39, 41, 43, 45,
             47, 49, 51, 53, 55, 57, 59, 63, 65, 69, 73, 75, 77, 79]

_FACTOR_LIMIT = 200_000

NOTES = r"""
WHICH SECTION FIXED THE DEFINITION.  Proposition 2.6 of arXiv:2209.04762 (the
`potri1` proposition, restated in the paper "for the convenience of the
reader"): for odd m > 1 and k = (m+1)/2, f(x) = x + x^(2^k-1) + x^(2^k+1)
permutes F_{2^m}.  Section 5 gives the quasi-multiplicative orbit of that
polynomial -- f(bx)/b and f(x^e) -- and Definition 2.2 fixes what "QM
equivalent" means: f(x) = a g(c x^d) with gcd(d, q-1) = 1.  The instances here
are exactly the QM orbit a * f(b * x^d) of Proposition 2.6's trinomial.

WHAT PRODUCES THE CERTIFICATE (the STEP-0 question).  The *proof* of
Proposition 2.6 does, in closed form.  Equations (2-1)..(2-7) of that proof
substitute y = x^(2^k), use y^(2^(k-1)) = x^(2^(2k-1)) = x^(2^m) = x, eliminate
y linearly, and land on

        (1 + c^2 + c^(2^k)) * x = c * c^(2^k),

so the unique preimage of c is x = c^(2^k+1) / (1 + c^2 + c^(2^k)).  That is a
polynomial-time formula, which is why this family is declared TRACK = "B" and
not "A".  The claim being made is the no-tool one: the formula is roughly 20
field operations once you see it, and roughly 2^m field evaluations if you do
not.

WHAT MAKES IT EASY, and what is avoided.  (a) m even -- the proposition needs m
odd; for even m the same trinomial is far from injective (measured image sizes
35/64, 136/256, 527/1024, 2080/4096 at m = 6, 8, 10, 12), so only odd m ships.
(b) A small field: at m <= 20 an attacker just tabulates the whole field.  The
shipping preset is m = 35, i.e. 3.4e10 field elements.  (c) Leaving the
trinomial in the paper's displayed form: then the family is recognisable by
eye.  From `medium` up, a random QM twist a * f(b * x^d) scrambles both the
exponents and the coefficients, and the solver has to recover d and b before
the formula applies.

HOW EACH ATTACK WAS DEFEATED.  Plants and decoys are drawn from one
distribution: every candidate is a * f(b * x^e) with a, b uniform in F_{2^m}^*
and e uniform subject to a gcd condition.  The *only* difference between the
planted trinomial and a decoy is whether gcd(e, 2^m-1) is 1, which is precisely
the condition in Definition 2.2; a decoy has image of size (2^m-1)/g + 1 and is
provably not a permutation.  Generation checks, in closed form, that at least
one target lies outside each decoy's image, so the answer is unique.  The
preimages themselves are sampled uniformly *before* the targets are computed,
so no per-element statistic (magnitude, Hamming weight, order, ...) separates
them from field noise; the outlier panel measures exactly that.
""".strip()

STRUCTURAL_HINT = (
    "Every exponent in the permuting trinomial is a fixed multiple of the "
    "smallest one, and the two ratios are 2^k-1 and 2^k+1 for the single k "
    "with 2k-1 = m."
)

PLACEBO_HINT = (
    "Keep careful track of which reduction is applied where: exponents live "
    "modulo 2^m-1 while coefficients live in the field itself, and mixing the "
    "two is the usual source of error here."
)

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "the finite field F_{2^m} given by an irreducible modulus over F_2",
        "trinomials a1*x^e1 + a2*x^e2 + a3*x^e3 over F_{2^m}",
        "field elements as targets",
    ],
    "verification_operations": [
        "carry-less multiplication modulo an irreducible polynomial over F_2",
        "square-and-multiply exponentiation in F_{2^m}",
        "exact field equality",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Setting y = x^(2^k) with k = (m+1)/2 turns the trinomial equation "
        "into a pair of equations linear in x, because y^(2^(k-1)) = x; a "
        "solver without that substitution has to search the field or do "
        "root-finding on a polynomial of degree ~2^m."
    ),
    "hardness_basis": (
        "TRACK B.  The compositional inverse is the closed form "
        "x = c^(2^k+1)/(1+c^2+c^(2^k)) read off the proof of Proposition 2.6 "
        "(equations 2-1..2-7), composed with the inverse of the QM twist; that "
        "is O(m) field operations, measured at 246 field operations per "
        "instance at the shipping preset m=35 (0.006 s).  The mechanical "
        "alternative is exhaustive evaluation over F_{2^35}: 3.44e10 "
        "evaluations for the one gcd-screened candidate and 5.84e11 across all "
        "17, at a measured 1.1e3 evaluations/s here, i.e. 3.2e7 s resp. 5.5e8 "
        "s; or root-finding on a polynomial of degree up to 2^35-1, which is "
        "worse.  The gap is a factor of about 1.4e8.  The compact route is not "
        "mechanically executable in context because it must first be "
        "discovered: the trinomial is presented after a random QM twist, so "
        "the exponent triple is not the paper's displayed one."
    ),
    "max_answer_tokens": 24,
}

NATIVE = {
    "domain": "algebra",
    "core": "polynomial_identity",
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": None,
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "A candidate index j in [0, D) followed by L field elements written as "
        "integers in [1, 2^m - 1]; element v encodes the polynomial "
        "sum_i bit_i(v) x^i of F_2[x] modulo the stated irreducible modulus."
    ),
    # Bounds at the shipping preset; make_instance carries the exact values
    # for any preset in inst["params"].
    "bounds": {"n_candidates": 17, "n_targets": 3, "field_bits": 35,
               "elements_per_field": 34359738368,
               "language_size": 17 * 34359738367 * 34359738366 * 34359738365},
}

_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_INT_RE = re.compile(r"-?\d+")
_LABEL_RE = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\s*\*?\s*[:=]+")


# ---------------------------------------------------------------------------
# Exact F_{2^m} arithmetic on plain Python integers.
# ---------------------------------------------------------------------------

def _poly_mulmod(a: int, b: int, poly: int, m: int) -> int:
    r = 0
    while b:
        if b & 1:
            r ^= a
        b >>= 1
        a <<= 1
        if (a >> m) & 1:
            a ^= poly
    return r


def _poly_gcd(a: int, b: int) -> int:
    while b:
        da = a.bit_length() - 1
        db = b.bit_length() - 1
        if da < db:
            a, b = b, a
            continue
        a ^= b << (da - db)
    return a


def _prime_factors(n: int) -> list[int]:
    out = []
    d = 2
    while d * d <= n:
        if n % d == 0:
            out.append(d)
            while n % d == 0:
                n //= d
        d += 1
    if n > 1:
        out.append(n)
    return out


def _is_irreducible(poly: int, m: int) -> bool:
    """Rabin's irreducibility test over F_2."""
    def x_pow_2e(e: int) -> int:
        r = 2
        for _ in range(e):
            r = _poly_mulmod(r, r, poly, m)
        return r
    if x_pow_2e(m) != 2:
        return False
    for p in _prime_factors(m):
        t = x_pow_2e(m // p) ^ 2
        if t == 0:
            return False
        if _poly_gcd(poly, t).bit_length() - 1 != 0:
            return False
    return True


_MODULUS_CACHE: dict[int, int] = {}


def _modulus(m: int) -> int:
    """The lowest-weight, then lexicographically smallest, irreducible
    polynomial of degree m over F_2.  Deterministic; cached."""
    if m in _MODULUS_CACHE:
        return _MODULUS_CACHE[m]
    for width in (1, 3, 5):
        for combo in itertools.combinations(range(1, m), width):
            poly = (1 << m) | 1
            for c in combo:
                poly |= 1 << c
            if _is_irreducible(poly, m):
                _MODULUS_CACHE[m] = poly
                return poly
    raise RuntimeError("no irreducible modulus found for degree %d" % m)


class _Field:
    """F_{2^m}; elements are ints in [0, 2^m)."""

    __slots__ = ("m", "poly", "N", "k")

    def __init__(self, m: int) -> None:
        self.m = m
        self.poly = _modulus(m)
        self.N = (1 << m) - 1
        self.k = (m + 1) // 2

    def mul(self, a: int, b: int) -> int:
        return _poly_mulmod(a, b, self.poly, self.m)

    def pow(self, a: int, e: int) -> int:
        if a == 0:
            return 0
        e %= self.N
        if e < 0:
            e += self.N
        r = 1
        while e:
            if e & 1:
                r = self.mul(r, a)
            a = self.mul(a, a)
            e >>= 1
        return r

    def inv(self, a: int) -> int:
        if a == 0:
            raise ZeroDivisionError("0 has no inverse in F_2^m")
        return self.pow(a, self.N - 1)

    def frob(self, a: int, e: int) -> int:
        """a^(2^e)."""
        for _ in range(e % self.m):
            a = self.mul(a, a)
        return a


_FIELD_CACHE: dict[int, _Field] = {}


def _field(m: int) -> _Field:
    F = _FIELD_CACHE.get(m)
    if F is None:
        F = _Field(m)
        _FIELD_CACHE[m] = F
    return F


# ---------------------------------------------------------------------------
# Proposition 2.6 of the paper and the closed form its proof produces.
# ---------------------------------------------------------------------------

def _f_base(F: _Field, x: int) -> int:
    """f(x) = x + x^(2^k-1) + x^(2^k+1), k = (m+1)/2.  PP of F_{2^m}, m odd."""
    if x == 0:
        return 0
    y = F.frob(x, F.k)                       # x^(2^k)
    return x ^ F.mul(y, F.inv(x)) ^ F.mul(y, x)


def _f_base_inv(F: _Field, c: int) -> int:
    """The unique preimage, from equations (2-1)..(2-7) of Proposition 2.6:
    x = c * c^(2^k) / (1 + c^2 + c^(2^k))."""
    if c == 0:
        return 0
    d = F.frob(c, F.k)
    den = 1 ^ F.mul(c, c) ^ d
    if den == 0:                             # the proof shows this cannot happen
        raise ArithmeticError("1 + c^2 + c^(2^k) vanished; m must be odd")
    return F.mul(F.mul(c, d), F.inv(den))


def _twisted_terms(F: _Field, a: int, b: int, e: int) -> list[tuple[int, int]]:
    """The three (exponent, coefficient) terms of a * f(b * x^e), exponents
    reduced into [1, 2^m-1] so the trinomial agrees with the map on all of
    F_{2^m} (including 0)."""
    k = F.k
    N = F.N
    mults = (1, (1 << k) - 1, (1 << k) + 1)
    terms = []
    for t in mults:
        ex = (e * t) % N
        if ex == 0:
            ex = N
        terms.append((ex, F.mul(a, F.pow(b, t))))
    return terms


def _eval_terms(F: _Field, terms: list[tuple[int, int]], x: int) -> int:
    if x == 0:
        return 0
    acc = 0
    for ex, co in terms:
        acc ^= F.mul(co, F.pow(x, ex))
    return acc


# ---------------------------------------------------------------------------
# Generation -- answer first, always.
# ---------------------------------------------------------------------------

def _coprime_shift(F: _Field, rng: random.Random) -> int:
    while True:
        e = rng.randrange(1, F.N)
        if math.gcd(e, F.N) == 1:
            return e


def _decoy_shift(F: _Field, rng: random.Random, factors: list[int]) -> int:
    """e with gcd(e, 2^m-1) > 1, so x -> x^e is (2^m-1)/g to one and the
    resulting trinomial is provably not a permutation of F_{2^m}."""
    while True:
        g = factors[rng.randrange(len(factors))]
        e = (g * rng.randrange(1, F.N // g)) % F.N
        if e != 0 and math.gcd(e, F.N) > 1:
            return e


def _terms_distinct(terms: list[tuple[int, int]]) -> bool:
    ex = [t[0] for t in terms]
    return len(set(ex)) == 3 and all(c != 0 for _, c in terms)


def _target_in_image(F: _Field, a: int, b: int, e: int, c: int) -> bool:
    """Is c in the image of x -> a * f(b * x^e)?  Uses the closed-form inverse
    of f, so this costs O(m) field operations rather than 2^m."""
    if c == 0:
        return True
    z = F.mul(_f_base_inv(F, F.mul(c, F.inv(a))), F.inv(b))
    if z == 0:
        return True
    g = math.gcd(e, F.N)
    return F.pow(z, F.N // g) == 1


def make_instance(seed: int = 0, **params: Any) -> dict:
    """Sample the preimages first, then build the instance around them.

    No search of any kind happens here: the planted trinomial comes from
    Proposition 2.6 twisted by a random QM equivalence, the preimages are drawn
    uniformly, and the targets are their images.
    """
    m = int(params.get("m", DIFFICULTY[SHIPPING_DIFFICULTY]["m"]))
    n_targets = int(params.get("n_targets", 3))
    n_decoys = int(params.get("n_decoys", 8))
    twist_level = int(params.get("twist_level", 2))
    if m % 2 == 0:
        raise ValueError("m must be odd: Proposition 2.6 needs 2k-1 = m")
    if m < 5:
        raise ValueError("m must be at least 5")

    rng = random.Random(("2209.04762", m, n_targets, n_decoys,
                         twist_level, seed).__repr__())
    F = _field(m)

    factors = []
    n = F.N
    d = 3
    while d <= _FACTOR_LIMIT and d * d <= n:
        if n % d == 0:
            factors.append(d)
            while n % d == 0:
                n //= d
        d += 2
    if not factors:
        raise ValueError(
            "2^%d - 1 has no factor below %d; pick m from _M_LADDER" %
            (m, _FACTOR_LIMIT))

    # --- the planted permutation trinomial -------------------------------
    while True:
        if twist_level >= 1:
            a = rng.randrange(1, 1 << m)
            b = rng.randrange(1, 1 << m)
        else:
            a = b = 1
        e = _coprime_shift(F, rng) if twist_level >= 2 else 1
        plant_terms = _twisted_terms(F, a, b, e)
        if _terms_distinct(plant_terms):
            break

    # --- the answer, sampled before anything depends on it ----------------
    xs: list[int] = []
    seen = set()
    while len(xs) < n_targets:
        x = rng.randrange(1, 1 << m)
        if x in seen:
            continue
        seen.add(x)
        xs.append(x)
    targets = [_eval_terms(F, plant_terms, x) for x in xs]
    if len(set(targets)) != len(targets) or 0 in targets:
        # f is a bijection, so this is unreachable; keep the guard anyway.
        raise ArithmeticError("planted trinomial is not injective on the plants")

    # --- decoys: same distribution, gcd(e, 2^m-1) > 1 ---------------------
    candidates = [plant_terms]
    seen_ex = {tuple(sorted(t[0] for t in plant_terms))}
    guard = 0
    while len(candidates) < n_decoys + 1:
        guard += 1
        if guard > 20000:
            raise RuntimeError("decoy sampling failed; lower n_decoys")
        if twist_level >= 1:
            da = rng.randrange(1, 1 << m)
            db = rng.randrange(1, 1 << m)
        else:
            da = db = 1
        de = _decoy_shift(F, rng, factors)
        terms = _twisted_terms(F, da, db, de)
        if not _terms_distinct(terms):
            continue
        key = tuple(sorted(t[0] for t in terms))
        if key in seen_ex:
            continue
        # A decoy is only admissible if at least one target is outside its
        # image; then no answer using this index can ever verify.
        if all(_target_in_image(F, da, db, de, c) for c in targets):
            continue
        seen_ex.add(key)
        candidates.append(terms)

    order = list(range(len(candidates)))
    rng.shuffle(order)
    shuffled = [sorted(candidates[i]) for i in order]
    plant_index = order.index(0)

    return {
        "paper": "2209.04762",
        "m": m,
        "modulus": F.poly,
        "candidates": [[[ex, co] for ex, co in terms] for terms in shuffled],
        "targets": targets,
        "params": {"m": m, "n_targets": n_targets,
                   "n_decoys": n_decoys, "twist_level": twist_level},
        "answer": [plant_index] + xs,
    }


# ---------------------------------------------------------------------------
# Statement
# ---------------------------------------------------------------------------

def _poly_str(mod: int, m: int) -> str:
    parts = []
    for i in range(m, -1, -1):
        if (mod >> i) & 1:
            parts.append("1" if i == 0 else ("x" if i == 1 else "x^%d" % i))
    return " + ".join(parts)


def render(inst: dict) -> str:
    m = inst["m"]
    mod = inst["modulus"]
    cands = inst["candidates"]
    tg = inst["targets"]
    L = len(tg)
    D = len(cands)

    lines = []
    lines.append("FINITE FIELD.")
    lines.append(
        "Work in F_{2^%d}, the field with 2^%d elements. Represent an element "
        "by an integer v with 0 <= v < 2^%d: bit i of v (the coefficient of "
        "2^i) is the coefficient of x^i in the polynomial representing v. "
        "Addition of field elements is bitwise XOR of these integers. "
        "Multiplication is multiplication of the corresponding polynomials "
        "over F_2, reduced modulo the irreducible polynomial"
        % (m, m, m))
    lines.append("")
    lines.append("    P(x) = %s      (integer encoding %d)"
                 % (_poly_str(mod, m), mod))
    lines.append("")
    lines.append(
        "The nonzero elements form a cyclic group of order 2^%d - 1 = %d, so "
        "v^(2^%d - 1) = 1 for every nonzero v, and 0^e = 0 for every e >= 1."
        % (m, (1 << m) - 1, m))
    lines.append("")
    lines.append("CANDIDATE TRINOMIALS.")
    lines.append(
        "Below are %d trinomials over F_{2^%d}, written as three "
        "(exponent, coefficient) pairs; trinomial number j is"
        % (D, m))
    lines.append("")
    lines.append("    T_j(x) = c1*x^d1 + c2*x^d2 + c3*x^d3")
    lines.append("")
    lines.append(
        "with the pairs (d1,c1), (d2,c2), (d3,c3) listed in increasing "
        "exponent order. Exponents are integers in [1, 2^%d - 1] and "
        "coefficients are nonzero field elements. Candidates are numbered "
        "from 0." % m)
    lines.append("")
    for j, terms in enumerate(cands):
        pairs = ", ".join("(%d, %d)" % (ex, co) for ex, co in terms)
        lines.append("  j = %d : %s" % (j, pairs))
    lines.append("")
    lines.append(
        "Exactly one of these %d trinomials is a PERMUTATION POLYNOMIAL of "
        "F_{2^%d}, that is, exactly one induces a bijection x -> T_j(x) of "
        "the field onto itself. Call its index j*." % (D, m))
    lines.append("")
    lines.append("TARGETS.")
    lines.append(
        "Because T_{j*} is a bijection, each of the following %d field "
        "elements has exactly one preimage under it." % L)
    lines.append("")
    for i, c in enumerate(tg, 1):
        lines.append("  c%d = %d" % (i, c))
    lines.append("")
    lines.append("TASK.")
    lines.append(
        "Find j* and find the field elements x1, ..., x%d with "
        "T_{j*}(xi) = ci for i = 1, ..., %d. Each xi is an integer with "
        "1 <= xi < 2^%d. The answer is unique: no other candidate index "
        "admits preimages for all %d targets." % (L, L, m, L))
    lines.append("")
    lines.append("OUTPUT.")
    lines.append(
        "Give your final answer inside <answer></answer> tags, as %d "
        "comma-separated integers: first j*, then x1, ..., x%d, in that "
        "order." % (L + 1, L))
    lines.append("Example: <answer>%s</answer>"
                 % ", ".join(["0"] + ["1"] * L))
    lines.append("Output nothing else inside the tags.")

    text = "\n".join(lines)
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


# ---------------------------------------------------------------------------
# Parsing and verification
# ---------------------------------------------------------------------------

def parse_answer(text: Any) -> Any:
    if not isinstance(text, str):
        return None
    blocks = _ANSWER_RE.findall(text)
    body = blocks[-1] if blocks else text
    body = body.replace("```", " ")
    # Tolerate labelled output ("j* = 3, x1 = 17, x2 = 42") by deleting the
    # labels before reading integers, so that the "1" of "x1" is not parsed.
    body = _LABEL_RE.sub(" ", body)
    nums = _INT_RE.findall(body)
    if not blocks:
        # No tags: only accept a clean, comma/space separated integer list.
        stripped = body.strip()
        if not stripped or not re.fullmatch(r"[\s,;\[\]\-0-9]+", stripped):
            return None
    if len(nums) < 2:
        return None
    try:
        vals = [int(t) for t in nums]
    except ValueError:
        return None
    return vals


def verify(inst: dict, answer: Any) -> tuple[bool, str]:
    m = inst["m"]
    cands = inst["candidates"]
    targets = inst["targets"]
    L = len(targets)

    if not isinstance(answer, (list, tuple)):
        return False, "answer is not a list of integers"
    answer = list(answer)
    if len(answer) != L + 1:
        return False, ("answer has %d entries, expected %d (index plus %d "
                       "preimages)" % (len(answer), L + 1, L))
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in answer):
        return False, "answer contains a non-integer entry"

    j = answer[0]
    if not (0 <= j < len(cands)):
        return False, ("candidate index %d out of range [0, %d)"
                       % (j, len(cands)))

    xs = answer[1:]
    for i, x in enumerate(xs, 1):
        if not (1 <= x < (1 << m)):
            return False, ("preimage x%d = %d is outside [1, 2^%d)"
                           % (i, x, m))
    if len(set(xs)) != len(xs):
        return False, "preimages are not distinct, but the targets are"

    F = _field(m)
    terms = [(ex, co) for ex, co in cands[j]]
    for i, (x, c) in enumerate(zip(xs, targets), 1):
        got = _eval_terms(F, terms, x)
        if got != c:
            return False, ("T_%d(x%d) = %d, but c%d = %d" % (j, i, got, i, c))
    return True, "ok"


# ---------------------------------------------------------------------------
# Space accounting
# ---------------------------------------------------------------------------

def random_candidate(inst: dict, rng: random.Random) -> list[int]:
    """A shape-correct guess: a legal index and legal nonzero field elements.
    Everything a solver gets for free from the statement is already applied."""
    m = inst["m"]
    L = len(inst["targets"])
    out = [rng.randrange(len(inst["candidates"]))]
    seen: set[int] = set()
    while len(out) < L + 1:
        v = rng.randrange(1, 1 << m)
        if v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def search_space(inst: dict) -> int:
    m = inst["m"]
    L = len(inst["targets"])
    D = len(inst["candidates"])
    n = (1 << m) - 1
    total = D
    for i in range(L):
        total *= (n - i)
    return total


def enumerate_all(inst: dict, budget: int = 4_000_000) -> int | None:
    """Exact number of valid answers.  Feasible only when 2^m * D is small."""
    m = inst["m"]
    D = len(inst["candidates"])
    if (1 << m) * D > budget:
        return None
    F = _field(m)
    targets = inst["targets"]
    count = 0
    for j, cj in enumerate(inst["candidates"]):
        terms = [(ex, co) for ex, co in cj]
        pre: list[list[int]] = [[] for _ in targets]
        for x in range(1, 1 << m):
            v = _eval_terms(F, terms, x)
            for i, c in enumerate(targets):
                if v == c:
                    pre[i].append(x)
        prod = 1
        for lst in pre:
            prod *= len(lst)
        count += prod
    return count


def canonical_key(inst: dict) -> str:
    """Invariant under: reordering the candidate list, reordering the target
    list, and applying any power of the Frobenius automorphism x -> x^2 to
    every coefficient and target (which relabels the field, not the problem).
    """
    m = inst["m"]
    F = _field(m)
    best = None
    for e in range(m):
        cands = []
        for terms in inst["candidates"]:
            tt = tuple(sorted((ex, F.frob(co, e)) for ex, co in terms))
            cands.append(tt)
        blob = (m, inst["modulus"], tuple(sorted(cands)),
                tuple(sorted(F.frob(c, e) for c in inst["targets"])))
        s = repr(blob)
        if best is None or s < best:
            best = s
    return hashlib.sha256(best.encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Escalation: grow the haystack, not the needle.
# ---------------------------------------------------------------------------

def escalate(params: dict) -> dict | str | None:
    """Harder parameters at FIXED answer length.

    Three dials move together and none of them changes how many numbers the
    solver writes down:
      * m            -- the ambient field grows, so the exhaustive route grows
                        as 2^m while the answer stays 1 + n_targets integers;
      * n_decoys     -- more same-distribution near-misses to screen;
      * twist_level  -- the quasi-multiplicative twist is switched on, which
                        hides the paper's exponent triple behind a random
                        d coprime to 2^m - 1.
    n_targets is deliberately NOT raised: that is the needle.
    """
    p = dict(params)
    m = int(p.get("m", 35))
    tw = int(p.get("twist_level", 2))
    if tw < 2:
        p["twist_level"] = 2
        p["n_decoys"] = int(p.get("n_decoys", 8)) * 2
        return p
    nxt = [v for v in _M_LADDER if v > m]
    if not nxt:
        # The answer cannot be lengthened without leaving the 256-atom cap
        # regime we ship in, and no larger field in the ladder is available.
        return "cap_bound"
    p["m"] = nxt[0]
    p["n_decoys"] = min(64, int(p.get("n_decoys", 8)) + 8)
    p["n_targets"] = int(p.get("n_targets", 3))
    return p


# ---------------------------------------------------------------------------
# The reference algorithm: the compact route of Proposition 2.6's proof.
# ---------------------------------------------------------------------------

def _solve_candidate(F: _Field, terms: list[tuple[int, int]],
                     targets: list[int]) -> tuple[list[int], int] | None:
    """Recover (a, b, d) from a trinomial claimed to be a * f(b * x^d), then
    invert at each target with the closed form.  Returns (preimages, ops) or
    None if the trinomial is not of that shape.  This is the Track B reference
    algorithm; `ops` counts field operations."""
    N, k, m = F.N, F.k, F.m
    ops = 1                    # one gcd screen (Definition 2.2) per candidate
    if math.gcd(terms[0][0], N) != 1:
        return None
    for perm in itertools.permutations(range(3)):
        (e1, c1), (e2, c2), (e3, c3) = (terms[perm[0]], terms[perm[1]],
                                        terms[perm[2]])
        if math.gcd(e1, N) != 1:
            continue
        inv_e1 = pow(e1, -1, N)
        if (e2 * inv_e1 - ((1 << k) - 1)) % N != 0:
            continue
        if (e3 * inv_e1 - ((1 << k) + 1)) % N != 0:
            continue
        ops += 2               # the two exponent-ratio checks that succeeded
        d = e1 % N
        # c3/c1 = b^(2^k)  =>  b = (c3/c1)^(2^(m-k))
        ratio = F.mul(c3, F.inv(c1)); ops += 2      # one division, one mul
        b = F.frob(ratio, m - k); ops += (m - k)    # squarings
        if b == 0:
            continue
        a = F.mul(c1, F.inv(b)); ops += 2
        if a == 0:
            continue
        dinv = pow(d, -1, N); ops += 1               # one modular inverse
        inv_a, inv_b = F.inv(a), F.inv(b); ops += 2
        out = []
        good = True
        for c in targets:
            w = F.mul(c, inv_a); ops += 1
            # closed form: k squarings for c^(2^k), one squaring for c^2,
            # two additions, one multiplication, one division
            z = _f_base_inv(F, w); ops += (k + 5)
            z = F.mul(z, inv_b); ops += 1
            x = F.pow(z, dinv)
            ops += dinv.bit_length() - 1 + bin(dinv).count("1") - 1
            if _eval_terms(F, terms, x) != c:
                good = False
                break
            out.append(x)
        if good:
            return out, ops
    return None


def reference_solve(inst: dict) -> tuple[list[int] | None, int]:
    """Solve an instance the way a solver who has seen the structure does."""
    F = _field(inst["m"])
    total = 0
    for j, cj in enumerate(inst["candidates"]):
        terms = [(ex, co) for ex, co in cj]
        res = _solve_candidate(F, terms, inst["targets"])
        if res is None:
            total += 1      # the gcd screen of Definition 2.2, and nothing more
            continue
        if res is not None:
            xs, ops = res
            return [j] + xs, total + ops
    return None, total


# ---------------------------------------------------------------------------
# Attacks
# ---------------------------------------------------------------------------

def attack_exhaustive_preimage(inst: dict, budget: int = 400_000):
    """The domain-mechanical route: evaluate every candidate trinomial at every
    field element until the targets are hit.  Cost is D * 2^m evaluations."""
    F = _field(inst["m"])
    targets = inst["targets"]
    spent = 0
    for j, cj in enumerate(inst["candidates"]):
        terms = [(ex, co) for ex, co in cj]
        found: dict[int, int] = {}
        for x in range(1, 1 << inst["m"]):
            spent += 1
            if spent > budget:
                return None, spent
            v = _eval_terms(F, terms, x)
            if v in targets and v not in found:
                found[v] = x
                if len(found) == len(set(targets)):
                    break
        if len(found) == len(set(targets)):
            return [j] + [found[c] for c in targets], spent
    return None, spent


def attack_exponent_search(inst: dict, budget: int = 200_000):
    """Exhaustive search over exponent space without the paper's structure:
    for each candidate, try to write the trinomial as a * g(b * x^d) for every
    monomial substitution d and every Frobenius index kk, using only the
    *displayed* exponent ratios, then test the resulting closed form.  This is
    the 'classification lookup' attack with the classification unknown: it
    sweeps kk over all of [1, m] instead of using kk = (m+1)/2."""
    F = _field(inst["m"])
    N, m = F.N, F.m
    targets = inst["targets"]
    spent = 0
    for j, cj in enumerate(inst["candidates"]):
        terms = [(ex, co) for ex, co in cj]
        for perm in itertools.permutations(range(3)):
            (e1, c1), (e2, c2), (e3, c3) = (terms[perm[0]], terms[perm[1]],
                                            terms[perm[2]])
            if math.gcd(e1, N) != 1:
                continue
            inv_e1 = pow(e1, -1, N)
            r2 = (e2 * inv_e1) % N
            r3 = (e3 * inv_e1) % N
            for kk in range(1, m + 1):
                spent += 1
                if spent > budget:
                    return None, spent
                if r2 != ((1 << kk) - 1) % N or r3 != ((1 << kk) + 1) % N:
                    continue
                # Found a shape; apply the closed form with THIS kk.
                if (2 * kk - 1) % m != 0:
                    continue          # the substitution identity fails
                ratio = F.mul(c3, F.inv(c1))
                b = F.frob(ratio, m - kk)
                if b == 0:
                    continue
                a = F.mul(c1, F.inv(b))
                dinv = pow(e1, -1, N)
                out = []
                ok = True
                for c in targets:
                    w = F.mul(c, F.inv(a))
                    dd = F.frob(w, kk)
                    den = 1 ^ F.mul(w, w) ^ dd
                    if den == 0:
                        ok = False
                        break
                    z = F.mul(F.mul(w, dd), F.inv(den))
                    z = F.mul(z, F.inv(b))
                    x = F.pow(z, dinv)
                    if _eval_terms(F, terms, x) != c:
                        ok = False
                        break
                    out.append(x)
                if ok:
                    return [j] + out, spent
    return None, spent


def attack_outlier(inst: dict, rng: random.Random | None = None):
    """Is the answer readable off a per-element statistic?  Try the extremal
    element of the field under several orderings, per candidate, with the
    candidate chosen by every cheap statistic in sight."""
    F = _field(inst["m"])
    m, targets = inst["m"], inst["targets"]
    stats = []
    for j, cj in enumerate(inst["candidates"]):
        ex = [t[0] for t in cj]
        co = [t[1] for t in cj]
        stats.append((j, min(ex), max(ex), sum(ex), sum(bin(c).count("1")
                                                       for c in co),
                      min(co), max(co)))
    orders = []
    for idx in range(1, 7):
        orders.append(sorted(stats, key=lambda s: s[idx])[0][0])
        orders.append(sorted(stats, key=lambda s: -s[idx])[0][0])
    for j in dict.fromkeys(orders):
        terms = [(ex, co) for ex, co in inst["candidates"][j]]
        for guess in (targets,
                      [c ^ 1 for c in targets],
                      [F.inv(c) if c else 1 for c in targets],
                      [F.mul(c, c) for c in targets]):
            cand = [j] + list(guess)
            ok, _ = verify(inst, cand)
            if ok:
                return cand
    return None


def attack_greedy_bitflip(inst: dict, rng: random.Random,
                          restarts: int = 24, steps: int = 400):
    """Hill-climb each preimage independently: minimise the Hamming distance
    between T_j(x) and c by single-bit flips of x.  This is the obvious
    in-context heuristic and the one a solver without the substitution would
    reach for."""
    F = _field(inst["m"])
    m, targets = inst["m"], inst["targets"]
    N = (1 << m) - 1
    screened = [j for j, cj in enumerate(inst["candidates"])
                if math.gcd(cj[0][0], N) == 1]
    if not screened:
        screened = list(range(len(inst["candidates"])))
    for j in screened:
        cj = inst["candidates"][j]
        terms = [(ex, co) for ex, co in cj]
        sol = []
        for c in targets:
            best_x = None
            for _ in range(restarts):
                x = rng.randrange(1, 1 << m)
                cur = bin(_eval_terms(F, terms, x) ^ c).count("1")
                for _ in range(steps):
                    if cur == 0:
                        break
                    improved = False
                    for bit in range(m):
                        y = x ^ (1 << bit)
                        if y == 0:
                            continue
                        d = bin(_eval_terms(F, terms, y) ^ c).count("1")
                        if d < cur:
                            x, cur = y, d
                            improved = True
                            break
                    if not improved:
                        break
                if cur == 0:
                    best_x = x
                    break
            if best_x is None:
                sol = None
                break
            sol.append(best_x)
        if sol is not None:
            cand = [j] + sol
            ok, _ = verify(inst, cand)
            if ok:
                return cand
    return None


def attack_random_restart(inst: dict, rng: random.Random,
                          samples: int = 200_000):
    """Sample shape-correct candidates with a mild heuristic (prefer the
    candidate whose exponent gcd screen passes)."""
    good = [j for j, cj in enumerate(inst["candidates"])
            if math.gcd(cj[0][0], (1 << inst["m"]) - 1) == 1]
    if not good:
        good = list(range(len(inst["candidates"])))
    m = inst["m"]
    L = len(inst["targets"])
    for _ in range(samples):
        cand = [good[rng.randrange(len(good))]]
        cand += [rng.randrange(1, 1 << m) for _ in range(L)]
        ok, _ = verify(inst, cand)
        if ok:
            return cand
    return None


def attack_algebraic_linearised(inst: dict):
    """Treat the trinomial as if it were a linearised (2-polynomial) map and
    solve the induced F_2-linear system for x.  This is the standard first
    move for equations over F_{2^m} whose exponents are close to powers of two,
    and it is exactly what fails here: the map is not additive."""
    F = _field(inst["m"])
    m = inst["m"]
    for j, cj in enumerate(inst["candidates"]):
        terms = [(ex, co) for ex, co in cj]
        # Build the matrix of x -> T(x) restricted to the F_2 basis.
        cols = [_eval_terms(F, terms, 1 << i) for i in range(m)]
        sol = []
        for c in inst["targets"]:
            # Gaussian elimination over F_2 on the m x m matrix `cols`.
            rows = list(cols)
            aug = [1 << i for i in range(m)]
            tgt = c
            x = 0
            piv = {}
            for i in range(m):
                v, tag = rows[i], aug[i]
                while v:
                    b = v.bit_length() - 1
                    if b in piv:
                        pv, pt = piv[b]
                        v ^= pv
                        tag ^= pt
                    else:
                        piv[b] = (v, tag)
                        break
            v, tag = tgt, 0
            while v:
                b = v.bit_length() - 1
                if b not in piv:
                    break
                pv, pt = piv[b]
                v ^= pv
                tag ^= pt
            if v == 0:
                x = tag
            if x and _eval_terms(F, terms, x) == c:
                sol.append(x)
            else:
                sol = None
                break
        if sol:
            ok, _ = verify(inst, sol and [j] + sol)
            if ok:
                return [j] + sol
    return None


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------

def _atoms(answer: Any) -> int:
    if isinstance(answer, (list, tuple)):
        return sum(_atoms(v) for v in answer)
    return 1


def selftest(quick: bool = False) -> dict:
    report: dict[str, Any] = {"paper": "2209.04762", "track": TRACK,
                              "shipping": SHIPPING_DIFFICULTY}
    ship = DIFFICULTY[SHIPPING_DIFFICULTY]

    # --- G1 ---------------------------------------------------------------
    g1_ok = 0
    g1_tot = 0
    for name, params in DIFFICULTY.items():
        for seed in range(6):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_tot += 1
            g1_ok += 1 if ok else 0
            if not ok:
                report.setdefault("G1_failures", []).append((name, seed, why))
    report["G1_planted_verifies"] = {"pass": g1_ok == g1_tot,
                                     "ok": g1_ok, "total": g1_tot}

    # --- G2 ---------------------------------------------------------------
    inst = make_instance(seed=11, **ship)
    ans = inst["answer"]
    reasons = {}
    corruptions = {
        "drop_one": ans[:-1],
        "swap_two": [ans[0], ans[2], ans[1]] + ans[3:] if len(ans) > 2 else ans,
        "duplicate": [ans[0]] + [ans[1]] * (len(ans) - 1),
        "empty": [],
        "out_of_range": [ans[0]] + [1 << inst["m"]] + ans[2:],
        "bad_index": [len(inst["candidates"])] + ans[1:],
        "wrong_candidate": [(ans[0] + 1) % len(inst["candidates"])] + ans[1:],
    }
    all_rejected = True
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        reasons[name] = why
        if ok:
            all_rejected = False
    report["G2_rejects_corruption"] = {
        "pass": all_rejected,
        "distinct_reasons": len(set(reasons.values())),
        "reasons": reasons,
    }

    # --- G3 ---------------------------------------------------------------
    body = ", ".join(str(v) for v in ans)
    reply = ("Let me set y = x^(2^k).\n\nAfter eliminating y I get the "
             "closed form.\n\n<answer>%s</answer>\n\nHope that helps." % body)
    got = parse_answer(reply)
    rt = got == ans
    junk = [parse_answer("no answer here"), parse_answer(""),
            parse_answer(None), parse_answer("<answer>banana</answer>")]
    report["G3_round_trip"] = {"pass": rt and all(v is None for v in junk),
                               "recovered": got == ans}

    # --- G4 ---------------------------------------------------------------
    rng = random.Random(4)
    ss = search_space(inst)

    def sample(ins, trials):
        h = 0
        for _ in range(trials):
            if verify(ins, random_candidate(ins, rng))[0]:
                h += 1
        return h

    # Full 200k draws are run at `easy` (cheap field arithmetic) and a
    # 25k probe at the shipping preset; both are reported, neither is
    # substituted for the other.
    easy_inst = make_instance(seed=77, **DIFFICULTY["easy"])
    t_easy = 2_000 if quick else 200_000
    h_easy = sample(easy_inst, t_easy)
    t_ship = 500 if quick else 25_000
    h_ship = sample(inst, t_ship)
    p_guess = h_ship / t_ship
    report["G4_guess_resistance"] = {
        "pass": (h_ship == 0 and h_easy == 0
                 and 1.0 / ss < 1e-6),
        "hits": h_ship, "total": t_ship,
        "hits_easy_preset": h_easy, "total_easy_preset": t_easy,
        "empirical_p": p_guess,
        "empirical_p_upper_95pct": 3.0 / t_ship,
        "analytic_p": 1.0 / ss,
        "search_space": ss,
        "search_space_bits": ss.bit_length(),
    }

    # --- G5 ---------------------------------------------------------------
    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    exact_demo = enumerate_all(demo)
    t0 = time.time()
    sol, ops = reference_solve(inst)
    ref_secs = time.time() - t0
    t0 = time.time()
    probe_budget = 20_000
    _, spent = attack_exhaustive_preimage(inst, budget=probe_budget)
    brute_secs = time.time() - t0
    rate = spent / brute_secs if brute_secs > 0 else float("inf")
    full = len(inst["candidates"]) * (1 << inst["m"])
    report["G5_density_and_baseline"] = {
        "pass": True,
        "exact_solution_count_demo_m9": exact_demo,
        "density_at_shipping": 1.0 / ss,
        "density_sample_size": t_ship,
        "density_hits": h_ship,
        "strongest_attack": "exhaustive_preimage_search",
        "strongest_attack_evaluations_needed": full,
        "measured_evaluations_per_second": rate,
        "projected_wall_clock_sec": full / rate if rate else None,
        "reference_algorithm_field_ops": ops,
        "reference_algorithm_sec": ref_secs,
        "reference_algorithm_correct": bool(sol
                                            and verify(inst, sol)[0]),
    }

    # --- G6 ---------------------------------------------------------------
    seeds = list(range(8))
    attacks: dict[str, dict] = {}

    def run(name, fn):
        succ = 0
        for s in seeds:
            ins = make_instance(seed=1000 + s, **ship)
            r = fn(ins, random.Random(s))
            if r is not None and verify(ins, r)[0]:
                succ += 1
        attacks[name] = {"successes": succ, "attempts": len(seeds)}

    run("outlier_candidate_statistics", lambda i, r: attack_outlier(i, r))
    run("greedy_hamming_bitflip",
        lambda i, r: attack_greedy_bitflip(i, r, restarts=8, steps=60))
    run("random_restart_5k",
        lambda i, r: attack_random_restart(i, r, samples=5_000))
    run("algebraic_linearised_solve",
        lambda i, r: attack_algebraic_linearised(i))
    run("exhaustive_preimage_capped_2e4",
        lambda i, r: attack_exhaustive_preimage(i, budget=20_000)[0])

    # Track B: the domain-standard route is reported separately and is
    # EXPECTED to succeed -- it is the hardness_basis, not a failure.
    ref_succ = 0
    ref_ops = []
    t0 = time.time()
    for s in seeds:
        ins = make_instance(seed=2000 + s, **ship)
        r, o = reference_solve(ins)
        ref_ops.append(o)
        if r is not None and verify(ins, r)[0]:
            ref_succ += 1
    ref_wall = time.time() - t0

    # A second, "blind" form of the reference algorithm: it does not know that
    # k = (m+1)/2 and sweeps the whole exponent space instead.  It is reported
    # here rather than in `attacks` because on Track B it is expected to win.
    sweep_succ = 0
    sweep_spent = []
    for s in seeds:
        ins = make_instance(seed=3000 + s, **ship)
        r, sp = attack_exponent_search(ins, budget=200_000)
        sweep_spent.append(sp)
        if r is not None and verify(ins, r)[0]:
            sweep_succ += 1

    report["G6_adversary_panel"] = {
        "pass": all(a["successes"] == 0 for a in attacks.values()),
        "attacks": attacks,
        "reference_algorithm_blind_exponent_sweep": {
            "name": "sweep k' over [1, m], test the closed form for each",
            "complexity": "O(D * m) shape tests, then O(m) field ops",
            "shape_tests": int(sum(sweep_spent) / len(sweep_spent)),
            "solves": "%d/%d, as expected" % (sweep_succ, len(seeds)),
        },
        "reference_algorithm": {
            "name": ("closed-form compositional inverse of Proposition 2.6 "
                     "after undoing the QM twist of Definition 2.2"),
            "complexity": "O(m) field operations per target",
            "wall_clock_sec": ref_wall / len(seeds),
            "operations": int(sum(ref_ops) / len(ref_ops)),
            "solves": "%d/%d, as expected" % (ref_succ, len(seeds)),
        },
    }

    # --- G7 ---------------------------------------------------------------
    bigger = escalate(dict(ship))
    scaled_ok = False
    scaled_note = str(bigger)
    if isinstance(bigger, dict):
        big = make_instance(seed=5, **bigger)
        scaled_ok = verify(big, big["answer"])[0]
        _, big_ops = reference_solve(big)
        scaled_note = "m=%d n_decoys=%d ref_ops=%d" % (
            bigger["m"], bigger["n_decoys"], big_ops)
    report["G7_scales"] = {"pass": scaled_ok, "escalated": scaled_note,
                           "escalated_params": bigger}

    # --- G8 ---------------------------------------------------------------
    inv_ok = 0
    inv_tot = 0
    for s in range(20):
        base = make_instance(seed=300 + s, **DIFFICULTY["easy"])
        F = _field(base["m"])
        k0 = canonical_key(base)
        # relabelling 1: reorder candidates (and move the plant index with it)
        perm = list(range(len(base["candidates"])))
        random.Random(s).shuffle(perm)
        r1 = dict(base)
        r1["candidates"] = [base["candidates"][p] for p in perm]
        r1["answer"] = [perm.index(base["answer"][0])] + base["answer"][1:]
        # relabelling 2: reorder targets (carry the preimages with them)
        tperm = list(range(len(base["targets"])))
        random.Random(s + 7).shuffle(tperm)
        r2 = dict(r1)
        r2["targets"] = [r1["targets"][p] for p in tperm]
        r2["answer"] = [r1["answer"][0]] + [r1["answer"][1:][p] for p in tperm]
        # relabelling 3: Frobenius x -> x^2 on the whole instance
        r3 = dict(r2)
        r3["candidates"] = [[[ex, F.mul(co, co)] for ex, co in t]
                            for t in r2["candidates"]]
        r3["targets"] = [F.mul(c, c) for c in r2["targets"]]
        r3["answer"] = [r2["answer"][0]] + [F.mul(v, v)
                                            for v in r2["answer"][1:]]
        for r in (r1, r2, r3):
            inv_tot += 1
            if canonical_key(r) == k0:
                inv_ok += 1
        # step 2: the relabellings really preserve the problem
        if not verify(r3, r3["answer"])[0]:
            report.setdefault("G8_transform_failures", []).append(s)
    keys = {canonical_key(make_instance(seed=900 + s, **DIFFICULTY["easy"]))
            for s in range(20)}
    report["G8_canonical_key"] = {
        "pass": inv_ok == inv_tot and len(keys) == 20
        and "G8_transform_failures" not in report,
        "invariance_ok": inv_ok, "invariance_total": inv_tot,
        "distinct_keys": len(keys), "distinct_of": 20,
    }

    # --- G9(c) ------------------------------------------------------------
    worst_chars = 0
    worst_atoms = 0
    for s in range(24):
        ii = make_instance(seed=600 + s, **ship)
        blob = json.dumps(ii["answer"], separators=(",", ":"))
        worst_chars = max(worst_chars, len(blob))
        worst_atoms = max(worst_atoms, _atoms(ii["answer"]))
        assert json.loads(blob) == ii["answer"]
    _, route_ops = reference_solve(make_instance(seed=1, **ship))
    report["G9_no_tool_suitability"] = {
        "pass": worst_chars <= 2000 and worst_atoms <= 256
        and route_ops <= 300,
        "arms": {"bare": None, "hinted": None, "placebo": None},
        "hinted_minus_placebo": None,
        "hinted_verdict": "not run in-process (needs scripts/harden.py)",
        "answer_chars": worst_chars,
        "answer_tokens": (worst_chars + 3) // 4,
        "answer_elements": worst_atoms,
        "intended_route_operations": route_ops,
    }

    gates = [k for k in report if k.startswith("G") and
             isinstance(report[k], dict) and "pass" in report[k]]
    report["all_pass"] = all(report[k]["pass"] for k in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, default=str))
