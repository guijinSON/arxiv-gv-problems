"""Verified planar-function equivalence generator for arXiv:2605.26263.

The native objects are quadratic functions on GF(p^3).  A planted candidate is
obtained from Theorem 3.3 of the paper by invertible input/output scalings.
Every decoy is made non-planar by choosing a derivative direction and kernel
first and changing one coefficient to force that collision.  Thus generation
never solves an instance in order to learn its answer.
"""

from __future__ import annotations

import copy
import functools
import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:                 # pragma: no cover - stdlib implementation below
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "quadratic Dembowski-Ostrom polynomials over GF(p^3)",
        "q-linearized derivative maps",
        "multiplicative finite-field equivalence certificate",
    ],
    "verification_operations": [
        "exact arithmetic in GF(p^3)",
        "five polynomial-coefficient identity comparisons",
        "Dickson determinant factor identity over GF(p)",
        "finite-field nonzero comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "A multiplicative change of variable preserves a low-degree relation "
        "among the five coefficients; without finding that relation one tests "
        "derivative maps throughout GF(p^3)."
    ),
    "hardness_basis": (
        "Track B: Proposition 2.1's homogeneous Dickson-matrix test enumerates "
        "p^2+p+1 projective derivative directions, O(m p^2) for m candidates; "
        "at shipping p=307, m=6 it measured 96,008 directions, at least "
        "5,664,472 scalar additions/multiplications, and about 0.51 s, "
        "while the coefficient-invariant and one-projector Hilbert-90 change "
        "of variables take at most 180 exact finite-field operations without "
        "a CAS across the shipping ladder."
    ),
    "max_answer_tokens": 10,
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
        "A JSON object {index,v,r}: index selects one displayed polynomial; "
        "v is one nonzero GF(p^3) element as three base-p coordinates; r is "
        "a base-field integer distinct from 0 and 1 with "
        "3r^2-3r+1 nonzero."
    ),
    "bounds": {
        "index": "0 <= index < number of candidates",
        "v_coordinates": 3,
        "coordinate_range": "0,...,p-1",
        "r_range": "0,...,p-1 subject to the displayed exclusions",
        "max_atomic_elements": 5,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 5, "candidates": 4},
    "easy": {"n": 149, "candidates": 6},
    "medium": {"n": 211, "candidates": 6},
    "hard": {"n": 307, "candidates": 6},
}
SHIPPING_DIFFICULTY: str = "hard"

STRUCTURAL_HINT: str = (
    "The five coefficients retain a multiplicative-change invariant that is "
    "cubic and homogeneous in adjacent coefficient pairs."
)
PLACEBO_HINT: str = (
    "The five coefficients should be handled in their displayed order with "
    "all finite-field reductions performed exactly."
)

# Replaced after the script-owned three oracle arms have run.
G9_EVIDENCE: dict = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

NOTES: str = r"""
Definition and Step 0.  The Introduction defines planarity by requiring every
nonzero derivative f(X+a)-f(X) to permute GF(q^3).  Proposition 2.1 turns each
test into a 3 by 3 Dickson determinant.  Lemma 2.2 gives the executable
nonvanishing test a^3+b^3+c^3-3abc != 0 for a q-linearized polynomial.
Theorem 3.3 is the exact two-parameter family used here: with E=1 and D=r,
g_r(X)=X^2+2(1-r)X^(p+1)+2rX^(p^2+1)+(1-r)X^(2p)+rX^(2p^2)
is planar exactly when 3r^2-3r+1 is nonzero.  Direct substitution into
Proposition 2.1 factors every derivative determinant as
16(z+y)(z+x)omega(y+x), where
omega=3r^2-3r+1 and (x,y,z)=(a,a^p,a^(p^2)).
The paper's proof displays scalar 4 instead of 16: its Corollary 2.6 system
sets each parenthesized coefficient to twice the product coefficient, while
Proposition 2.1 has another outer factor 2.  The missing nonzero factor 4 does
not affect planarity, but this checker uses the exact coefficient identity.

Track decision.  Track A would be false: on this generated distribution the
coefficient invariant followed by a three-dimensional Hilbert-90 solve is an
O(m log p) recovery algorithm.  This is Track B.  The domain-standard mechanical
reference follows Proposition 2.1 and quotients scalar multiples, testing
p^2+p+1 projective derivative matrices for a planar candidate.  The compact
route instead notices the invariant
c1^2*c4+c2^2*c3=4*c0*c3*c4, recovers the twist from t=2*c3/c1, and uses the
three-term Hilbert-90 projector.  The measured mechanical cost is written by
selftest into G5 and G6; the compact route is capped at 180 field operations.

Construction.  For random nonzero lambda,v and admissible r, put
t=v^(p-1), s=t^(p+1), and use coefficients
[lambda, 2lambda(1-r)t, 2lambda*r*s,
 lambda(1-r)t^2, lambda*r*s^2].  This is u*g_r(vX), u=lambda/v^2,
so the planted certificate is known before the instance exists.  A decoy starts
from an independent draw of the same object.  The generator then samples
nonzero derivative direction a and proposed kernel h and changes one coefficient
by the unique delta that makes D_a(h)=0.  That collision is the decoy's
construction certificate; no planarity search is performed.

Attack handling.  Candidate order is shuffled, the planted row is kept away
from the first position and from the smallest coordinate-energy outlier, and
v is never a base-field scalar.  The panel tests that energy outlier, the first
row, 256 uniformly sampled well-formed certificates, and the obvious v in GF(p)
ansatz.  The reference Dickson enumeration is intentionally separate because a
Track B reference is expected to solve.  Candidate reordering, simultaneous
Frobenius conjugation, and independent nonzero input/output scalings of every
row are the exact representational symmetries exercised by canonical_key and
G8.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 200_000


# Field elements are tuples (a0,a1,a2), representing a0+a1*T+a2*T^2.
FE = tuple[int, int, int]
MOD = tuple[int, int, int]


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_odd_prime(value: int) -> int:
    value = max(3, int(value))
    if value % 2 == 0:
        value += 1
    while not _is_prime(value):
        value += 2
    return value


def _find_irreducible_cubic(p: int) -> MOD:
    """Return m0,m1,m2 for a monic cubic with no root in GF(p)."""
    for m2 in range(min(p, 5)):
        for m1 in range(1, p):
            for m0 in range(1, p):
                if all((x * x * x + m2 * x * x + m1 * x + m0) % p
                       for x in range(p)):
                    return (m0, m1, m2)
    raise ValueError("could not find an irreducible cubic")


def _fe(value: object, p: int) -> FE | None:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    if any(isinstance(x, bool) or not isinstance(x, int) or not 0 <= x < p
           for x in value):
        return None
    return (int(value[0]), int(value[1]), int(value[2]))


def _zero() -> FE:
    return (0, 0, 0)


def _one() -> FE:
    return (1, 0, 0)


def _base(value: int, p: int) -> FE:
    return (value % p, 0, 0)


def _add(a: FE, b: FE, p: int) -> FE:
    return ((a[0] + b[0]) % p, (a[1] + b[1]) % p,
            (a[2] + b[2]) % p)


def _sub(a: FE, b: FE, p: int) -> FE:
    return ((a[0] - b[0]) % p, (a[1] - b[1]) % p,
            (a[2] - b[2]) % p)


def _neg(a: FE, p: int) -> FE:
    return ((-a[0]) % p, (-a[1]) % p, (-a[2]) % p)


def _scale(a: FE, scalar: int, p: int) -> FE:
    scalar %= p
    return (a[0] * scalar % p, a[1] * scalar % p,
            a[2] * scalar % p)


def _mul(a: FE, b: FE, p: int, modulus: MOD) -> FE:
    values = [0] * 5
    for i in range(3):
        for j in range(3):
            values[i + j] = (values[i + j] + a[i] * b[j]) % p
    for degree in (4, 3):
        coefficient = values[degree] % p
        if coefficient:
            for j in range(3):
                values[degree - 3 + j] = (
                    values[degree - 3 + j] - coefficient * modulus[j]
                ) % p
    return (values[0] % p, values[1] % p, values[2] % p)


def _pow(a: FE, exponent: int, p: int, modulus: MOD) -> FE:
    if exponent < 0:
        return _pow(_inv(a, p, modulus), -exponent, p, modulus)
    result = _one()
    base = a
    while exponent:
        if exponent & 1:
            result = _mul(result, base, p, modulus)
        base = _mul(base, base, p, modulus)
        exponent >>= 1
    return result


def _inv(a: FE, p: int, modulus: MOD) -> FE:
    if a == _zero():
        raise ZeroDivisionError("zero has no inverse")
    return _pow(a, p ** 3 - 2, p, modulus)


def _div(a: FE, b: FE, p: int, modulus: MOD) -> FE:
    return _mul(a, _inv(b, p, modulus), p, modulus)


def _frob(a: FE, p: int, modulus: MOD, power: int = 1) -> FE:
    return _pow(a, p ** (power % 3), p, modulus)


def _rand_fe(rng: random.Random, p: int, nonzero: bool = False) -> FE:
    while True:
        value = (rng.randrange(p), rng.randrange(p), rng.randrange(p))
        if not nonzero or value != _zero():
            return value


@functools.lru_cache(maxsize=128)
def _good_r_values(p: int) -> tuple[int, ...]:
    return tuple(r for r in range(p) if r not in (0, 1)
                 and (3 * r * r - 3 * r + 1) % p != 0)


def _valid_coefficients(rng: random.Random, p: int,
                        modulus: MOD) -> tuple[list[FE], FE, int]:
    choices = _good_r_values(p)
    if not choices:
        raise ValueError("field has no admissible theorem parameter")
    r = rng.choice(choices)
    while True:
        v = _rand_fe(rng, p, nonzero=True)
        # Exclude the obvious identity/base-field ansatz and make corruption
        # swaps meaningful in G2.  Requiring the first Hilbert-90 projector to
        # be nonzero gives the compact route a measured one-projector bound.
        t = _pow(v, p - 1, p, modulus)
        if (v[1:] != (0, 0) and len(set(v)) >= 2
                and _hilbert90_solution(t, p, modulus) is not None):
            break
    lam = _rand_fe(rng, p, nonzero=True)
    # Since t=v^(p-1), t^(p+1)=t*t^p.  This is the compact relation a
    # no-tool solver can use instead of a second generic exponentiation.
    s = _mul(t, _frob(t, p, modulus), p, modulus)
    one_minus_r = (1 - r) % p
    coefficients = [
        lam,
        _scale(_mul(lam, t, p, modulus), 2 * one_minus_r, p),
        _scale(_mul(lam, s, p, modulus), 2 * r, p),
        _scale(_mul(lam, _mul(t, t, p, modulus), p, modulus),
               one_minus_r, p),
        _scale(_mul(lam, _mul(s, s, p, modulus), p, modulus), r, p),
    ]
    return coefficients, v, r


def _derivative_terms(a: FE, h: FE, p: int, modulus: MOD) -> list[FE]:
    aq = _frob(a, p, modulus)
    aqq = _frob(aq, p, modulus)
    hq = _frob(h, p, modulus)
    hqq = _frob(hq, p, modulus)
    return [
        _scale(_mul(a, h, p, modulus), 2, p),
        _add(_mul(a, hq, p, modulus), _mul(aq, h, p, modulus), p),
        _add(_mul(a, hqq, p, modulus), _mul(aqq, h, p, modulus), p),
        _scale(_mul(aq, hq, p, modulus), 2, p),
        _scale(_mul(aqq, hqq, p, modulus), 2, p),
    ]


def _derivative_value(coefficients: list[FE], a: FE, h: FE,
                      p: int, modulus: MOD) -> FE:
    result = _zero()
    for coefficient, term in zip(
            coefficients, _derivative_terms(a, h, p, modulus)):
        result = _add(result, _mul(coefficient, term, p, modulus), p)
    return result


def _coefficient_invariant(coefficients: list[FE], p: int,
                           modulus: MOD) -> FE:
    c0, c1, c2, c3, c4 = coefficients
    left_a = _mul(_mul(c1, c1, p, modulus), c4, p, modulus)
    left_b = _mul(_mul(c2, c2, p, modulus), c3, p, modulus)
    right = _scale(_mul(_mul(c0, c3, p, modulus), c4, p, modulus),
                   4, p)
    return _sub(_add(left_a, left_b, p), right, p)


@functools.lru_cache(maxsize=4096)
def _coefficient_invariant_cached(coefficients: tuple[FE, ...], p: int,
                                  modulus: MOD) -> FE:
    return _coefficient_invariant(list(coefficients), p, modulus)


def _make_decoy(coefficients: list[FE], rng: random.Random, p: int,
                 modulus: MOD) -> list[FE]:
    """Plant a derivative collision by solving for one coefficient change."""
    for _ in range(200):
        a = _rand_fe(rng, p, nonzero=True)
        h = _rand_fe(rng, p, nonzero=True)
        current = _derivative_value(coefficients, a, h, p, modulus)
        if current == _zero():       # cannot happen for a sound planted base
            continue
        terms = _derivative_terms(a, h, p, modulus)
        order = list(range(5))
        rng.shuffle(order)
        for index in order:
            if terms[index] == _zero():
                continue
            delta = _div(_neg(current, p), terms[index], p, modulus)
            if delta == _zero():
                continue
            changed = list(coefficients)
            changed[index] = _add(changed[index], delta, p)
            if _zero() in changed:
                continue
            if _coefficient_invariant(changed, p, modulus) == _zero():
                continue
            if _derivative_value(changed, a, h, p, modulus) != _zero():
                raise AssertionError("collision construction failed")
            return changed
    raise RuntimeError("could not construct a separated non-planar decoy")


def _energy(coefficients: list[FE], p: int) -> int:
    return sum(min(x, p - x) for coefficient in coefficients
               for x in coefficient)


def make_instance(n: int, seed: int = 0, candidates: int = 24,
                  **params: object) -> dict:
    """Build one inverse-generated planar-certificate haystack."""
    del params
    p = _next_odd_prime(n)
    if candidates < 2:
        raise ValueError("candidates must be at least 2")
    if candidates > 128:
        raise ValueError("candidates must be at most 128")
    modulus = _find_irreducible_cubic(p)
    rng = random.Random(seed)

    # Regenerate only to defeat a declared per-row outlier probe; this does not
    # search for the answer, which remains the independently sampled theorem row.
    for _attempt in range(100):
        rows: list[list[FE]] = []
        planted_coefficients, planted_v, planted_r = _valid_coefficients(
            rng, p, modulus)
        rows.append(planted_coefficients)
        for _ in range(candidates - 1):
            base, _v, _r = _valid_coefficients(rng, p, modulus)
            rows.append(_make_decoy(base, rng, p, modulus))
        ordering = list(range(candidates))
        rng.shuffle(ordering)
        rows = [rows[i] for i in ordering]
        planted_index = ordering.index(0)
        if planted_index == 0:
            rows[0], rows[1] = rows[1], rows[0]
            planted_index = 1
        energies = [_energy(row, p) for row in rows]
        if planted_index != min(range(candidates), key=lambda i: (energies[i], i)):
            break
    else:
        raise RuntimeError("could not separate the planted row from outlier probe")

    answer = {
        "index": planted_index,
        "v": list(planted_v),
        "r": planted_r,
    }
    return {
        "p": p,
        "modulus": [modulus[0], modulus[1], modulus[2], 1],
        "candidates": [[list(value) for value in row] for row in rows],
        "answer": answer,
    }


def _fmt_fe(value: list[int] | FE) -> str:
    return "[" + ",".join(str(x) for x in value) + "]"


def render(inst: dict) -> str:
    """Render a complete finite-field equivalence-certificate problem."""
    p = inst["p"]
    m0, m1, m2, _ = inst["modulus"]
    lines = []
    for index, row in enumerate(inst["candidates"]):
        lines.append(f"{index}: " + " ".join(_fmt_fe(value) for value in row))
    statement = f"""Planar-polynomial equivalence certificate over GF({p}^3)

Let F=GF({p})[T]/(T^3+{m2}T^2+{m1}T+{m0}).  A field element
a0+a1*T+a2*T^2 is written [a0,a1,a2], with every coordinate reduced to
0,...,{p - 1}.  All additions, products, powers, and divisions below are in F.

Each numbered row contains five field elements c0 c1 c2 c3 c4 and represents
the function

  f(X)=c0*X^2+c1*X^({p}+1)+c2*X^({p*p}+1)
       +c3*X^(2*{p})+c4*X^(2*{p*p})  on F.

A function is planar when, for every nonzero a in F, the map
X -> f(X+a)-f(X) is a permutation of F.  Exactly one displayed row has the
following certificate.  Find its 0-based index, a nonzero v in F, and an
integer r in GF({p}) such that r is neither 0 nor 1,

  omega = 3*r^2-3*r+1  is nonzero modulo {p},

and, with t=v^({p}-1) and s=t^({p}+1), its coefficients satisfy exactly

  c1 = 2*c0*(1-r)*t
  c2 = 2*c0*r*s
  c3 = c0*(1-r)*t^2
  c4 = c0*r*s^2.

These equalities exhibit f(X)=u*g_r(vX), where u=c0/v^2 is nonzero and

  g_r(X)=X^2+2(1-r)X^({p}+1)+2rX^({p*p}+1)
         +(1-r)X^(2*{p})+rX^(2*{p*p}).

For completeness, the exact certificate check uses the derivative determinant
factorization 16*(z+y)*(z+x)*omega*(y+x), where
(x,y,z)=(a,a^{p},a^{p*p}); after removing nonzero scalar factors, the three
two-term q-linearized factors have nonzero Dickson determinants 2, 2, and
2*omega^3 modulo {p}.

Rows (c0 c1 c2 c3 c4):
{chr(10).join(lines)}

Give your final answer inside <answer></answer> tags as one JSON object with
exactly the keys index, v, and r.  The field element v must be its three
coordinate integers.  Example syntax:
<answer>{{"index":3,"v":[1,2,4],"r":2}}</answer>
Output nothing else inside the tags.
"""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\nHint: " + STRUCTURAL_HINT + "\n"
    elif mode == "placebo":
        statement += "\nHint: " + PLACEBO_HINT + "\n"
    return statement


def parse_answer(text: str) -> object | None:
    """Parse the final tagged JSON certificate, tolerating surrounding prose."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    payload = matches[-1].strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(answer, dict):
        return None
    return answer


def _base_factor_identity(r: int, p: int) -> bool:
    """Execute the coefficient identity used in Theorem 3.3's proof."""
    e, d = 1, r % p
    a, b, c = 2 * (e - d), 2 * d, e - d
    cube = (-2 * a * a * d + 2 * a * b * e - 2 * b * b * c) % p
    beta = (2 * a * a * c - 2 * a * b * d - 4 * a * c * d
            + 4 * a * e * e + 2 * b * b * e - 4 * b * c * e
            + 4 * b * d * d) % p
    gamma = (2 * a * a * e - 2 * a * b * c + 4 * a * c * c
             - 4 * a * d * e + 2 * b * b * d - 4 * b * c * d
             + 4 * b * e * e) % p
    mixed = (2 * a ** 3 + 2 * b ** 3 + 8 * c ** 3
             - 24 * c * d * e + 8 * d ** 3 + 8 * e ** 3) % p
    omega = (3 * r * r - 3 * r + 1) % p
    factor_determinants = (2 % p, 2 % p, 2 * pow(omega, 3, p) % p)
    return (cube == 0 and beta == 16 * omega % p
            and gamma == 16 * omega % p and mixed == 32 * omega % p
            and all(factor_determinants))


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid equivalence witness without consulting inst['answer']."""
    if not isinstance(answer, dict) or not answer:
        return False, "answer must be a nonempty JSON object"
    if set(answer) != {"index", "v", "r"}:
        return False, "answer must contain exactly the keys index, v, and r"
    p = inst["p"]
    modulus = tuple(inst["modulus"][:3])
    index = answer["index"]
    if isinstance(index, bool) or not isinstance(index, int):
        return False, "index must be an integer"
    if not 0 <= index < len(inst["candidates"]):
        return False, "index is outside the displayed row range"
    if not isinstance(answer["v"], (list, tuple)):
        return False, "v must be a coordinate list"
    if len(answer["v"]) < 3:
        return False, "v is missing a coordinate"
    if len(answer["v"]) > 3:
        return False, "v has a duplicate or extra coordinate"
    v = _fe(answer["v"], p)
    if v is None:
        return False, "v coordinates must be integers in the base-field range"
    if v == _zero():
        return False, "v must be nonzero"
    r = answer["r"]
    if isinstance(r, bool) or not isinstance(r, int) or not 0 <= r < p:
        return False, "r must be a base-field integer in range"
    if r in (0, 1):
        return False, "r must be distinct from 0 and 1"
    omega = (3 * r * r - 3 * r + 1) % p
    if omega == 0:
        return False, "the theorem parameter omega is zero"
    coefficients = [tuple(value) for value in inst["candidates"][index]]
    if _coefficient_invariant_cached(tuple(coefficients), p, modulus) != _zero():
        return False, "selected row fails the multiplicative coefficient invariant"
    t = _pow(v, p - 1, p, modulus)
    s = _mul(t, _frob(t, p, modulus), p, modulus)
    c0, c1, c2, c3, c4 = coefficients
    expected = [
        _scale(_mul(c0, t, p, modulus), 2 * (1 - r), p),
        _scale(_mul(c0, s, p, modulus), 2 * r, p),
        _scale(_mul(c0, _mul(t, t, p, modulus), p, modulus),
               1 - r, p),
        _scale(_mul(c0, _mul(s, s, p, modulus), p, modulus), r, p),
    ]
    for offset, (actual, wanted) in enumerate(zip((c1, c2, c3, c4), expected), 1):
        if actual != wanted:
            return False, f"coefficient c{offset} violates its equivalence identity"
    if c0 == _zero():
        return False, "output scaling c0/v^2 must be nonzero"
    if not _base_factor_identity(r, p):
        return False, "Dickson determinant factor certificate failed"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from all statement-compliant certificate triples."""
    p = inst["p"]
    while True:
        v = [rng.randrange(p), rng.randrange(p), rng.randrange(p)]
        if any(v):
            break
    return {
        "index": rng.randrange(len(inst["candidates"])),
        "v": v,
        "r": rng.choice(_good_r_values(p)),
    }


def search_space(inst: dict) -> int:
    p = inst["p"]
    return len(inst["candidates"]) * (p ** 3 - 1) * len(_good_r_values(p))


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    count = 0
    p = inst["p"]
    for index in range(len(inst["candidates"])):
        for coords in itertools.product(range(p), repeat=3):
            if coords == _zero():
                continue
            for r in _good_r_values(p):
                count += int(verify(inst, {
                    "index": index, "v": list(coords), "r": r,
                })[0])
    return count


def _row_scale_invariants(row: list[list[int]], p: int,
                          modulus: MOD) -> list[FE]:
    """Three invariants of arbitrary nonzero input/output scalings."""
    c0, c1, c2, c3, c4 = (tuple(value) for value in row)
    if _zero() in (c0, c1, c2, c3, c4):
        raise ValueError("canonical scaling invariants require nonzero coefficients")
    first = _div(_mul(c1, c1, p, modulus),
                 _mul(c0, c3, p, modulus), p, modulus)
    second = _div(_mul(c2, c2, p, modulus),
                  _mul(c0, c4, p, modulus), p, modulus)
    third = _div(_mul(_frob(c0, p, modulus), c2, p, modulus),
                 _mul(_frob(c1, p, modulus), c1, p, modulus), p, modulus)
    return [first, second, third]


def _canonical_payload(inst: dict, frobenius_power: int) -> str:
    p = inst["p"]
    modulus = tuple(inst["modulus"][:3])
    rows = []
    for row in inst["candidates"]:
        invariants = _row_scale_invariants(row, p, modulus)
        rows.append([list(_frob(value, p, modulus, frobenius_power))
                     for value in invariants])
    rows.sort(key=lambda row: json.dumps(row, separators=(",", ":")))
    return json.dumps({
        "p": p,
        "modulus": inst["modulus"],
        "rows": rows,
        "certificate": "multiplicative-Theorem-3.3-equivalence",
    }, sort_keys=True, separators=(",", ":"))


def canonical_key(inst: dict) -> str:
    """Quotient row order, Frobenius, and global input/output scalings."""
    payload = min(_canonical_payload(inst, power) for power in range(3))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _pow_multiplication_count(exponent: int) -> int:
    """Exact _mul calls made by the binary powering routine."""
    return exponent.bit_length() + exponent.bit_count()


def _compact_route_operation_bound(p: int, candidates: int) -> int:
    """Field-operation bound for full invariant scan plus planted recovery."""
    inverse = _pow_multiplication_count(p ** 3 - 2)
    frobenius = _pow_multiplication_count(p)
    # Nine operations per cubic invariant.  Recovering r and t uses two
    # inversions and six further operations.  The norm-one Hilbert-90
    # projector uses three Frobenius maps, four products, and two additions.
    return 9 * candidates + 2 * inverse + 3 * frobenius + 12


def escalate(params: dict) -> dict | str | None:
    """Increase the field/haystack while the five-atom witness stays fixed."""
    harder = dict(params)
    current = int(harder.get("n", 101))
    harder["n"] = _next_odd_prime(max(current + 2, (3 * current) // 2))
    harder["candidates"] = int(harder.get("candidates", 6))
    if _compact_route_operation_bound(
            int(harder["n"]), int(harder["candidates"])) > 300:
        return "cap_bound"
    return harder


def _hilbert90_solution(t: FE, p: int, modulus: MOD) -> FE | None:
    """Solve v^p=t*v with the fixed one-vector Hilbert-90 projector."""
    if t == _zero():
        return None
    tp = _frob(t, p, modulus)
    tpp = _frob(tp, p, modulus)
    if _mul(_mul(t, tp, p, modulus), tpp, p, modulus) != _one():
        return None
    # Norm(t)=1 gives t^-1=t^p*t^(p^2) and (t*t^p)^-1=t^(p^2).
    # The Hilbert-90 projector at w=1 therefore has only three terms.
    tinv = _mul(tp, tpp, p, modulus)
    v = _add(_one(), _add(tinv, tpp, p), p)
    if v != _zero() and _frob(v, p, modulus) == _mul(t, v, p, modulus):
        return v
    return None


def _recover_from_index(inst: dict, index: int) -> dict | None:
    """The compact structural route, used only to complete selected attacks."""
    p = inst["p"]
    modulus = tuple(inst["modulus"][:3])
    coefficients = [tuple(value) for value in inst["candidates"][index]]
    if _coefficient_invariant_cached(tuple(coefficients), p, modulus) != _zero():
        return None
    c0, c1, c2, c3, c4 = coefficients
    if _zero() in (c0, c1, c2, c3, c4):
        return None
    r_fe = _div(_mul(c2, c2, p, modulus),
                _scale(_mul(c0, c4, p, modulus), 4, p), p, modulus)
    if r_fe[1:] != (0, 0):
        return None
    r = r_fe[0]
    if r not in _good_r_values(p):
        return None
    t = _div(_scale(c3, 2, p), c1, p, modulus)
    v = _hilbert90_solution(t, p, modulus)
    if v is None:
        return None
    answer = {"index": index, "v": list(v), "r": r}
    return answer if verify(inst, answer)[0] else None


def _det3(matrix: list[list[int]], p: int) -> int:
    return (
        matrix[0][0] * (matrix[1][1] * matrix[2][2]
                        - matrix[1][2] * matrix[2][1])
        - matrix[0][1] * (matrix[1][0] * matrix[2][2]
                          - matrix[1][2] * matrix[2][0])
        + matrix[0][2] * (matrix[1][0] * matrix[2][1]
                          - matrix[1][1] * matrix[2][0])
    ) % p


def _derivative_basis_matrices(row: list[list[int]], p: int,
                               modulus: MOD) -> list[list[list[int]]]:
    coefficients = [tuple(value) for value in row]
    basis = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    matrices = []
    for a in basis:
        columns = [_derivative_value(coefficients, a, h, p, modulus)
                   for h in basis]
        matrices.append([[columns[col][line] for col in range(3)]
                         for line in range(3)])
    return matrices


def _has_singular_derivative(row: list[list[int]], p: int, modulus: MOD,
                             counter: dict[str, int]) -> bool:
    basis_matrices = _derivative_basis_matrices(row, p, modulus)
    counter["derivative_basis_builds"] += 1
    # The determinant is a homogeneous cubic in a.  These are exactly the
    # normalized representatives of P^2(GF(p)): (1,b,c), (0,1,c), (0,0,1).
    projective = itertools.chain(
        ((1, b, c) for b in range(p) for c in range(p)),
        ((0, 1, c) for c in range(p)),
        ((0, 0, 1),),
    )
    for coords in projective:
        matrix = [[sum(coords[k] * basis_matrices[k][i][j]
                       for k in range(3)) % p
                   for j in range(3)] for i in range(3)]
        counter["directions_tested"] += 1
        # Nine three-term linear combinations cost 45 scalar multiplies/adds;
        # the expanded 3-by-3 determinant costs another 14.  Reductions and
        # one-time setup are omitted, making this a reproducible lower bound.
        counter["scalar_operations"] += 59
        if _det3(matrix, p) == 0:
            return True
    return False


def _reference_algorithm(inst: dict) -> dict:
    """Literal Proposition 2.1 derivative/Dickson enumeration."""
    p = inst["p"]
    modulus = tuple(inst["modulus"][:3])
    counter = {
        "derivative_basis_builds": 0,
        "directions_tested": 0,
        "scalar_operations": 0,
    }
    start = time.perf_counter()
    planar_indices = []
    for index, row in enumerate(inst["candidates"]):
        if not _has_singular_derivative(row, p, modulus, counter):
            planar_indices.append(index)
    answer = None
    if len(planar_indices) == 1:
        answer = _recover_from_index(inst, planar_indices[0])
    wall = time.perf_counter() - start
    ok, reason = verify(inst, answer) if answer is not None else (
        False, f"found {len(planar_indices)} planar rows")
    return {
        "ok": ok,
        "reason": reason,
        "answer": answer,
        "planar_indices": planar_indices,
        "wall_clock_sec": wall,
        "counter": counter,
    }


def _attack_outlier_energy(inst: dict) -> bool:
    p = inst["p"]
    index = min(range(len(inst["candidates"])),
                key=lambda i: (_energy([tuple(v) for v in inst["candidates"][i]], p), i))
    answer = _recover_from_index(inst, index)
    return answer is not None and verify(inst, answer)[0]


def _attack_greedy_first(inst: dict) -> bool:
    answer = _recover_from_index(inst, 0)
    return answer is not None and verify(inst, answer)[0]


def _attack_random_restart(inst: dict, seed: int, restarts: int = 256) -> bool:
    rng = random.Random(seed ^ 0x260526263)
    for _ in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _attack_base_field_twist(inst: dict) -> bool:
    p = inst["p"]
    for index in range(len(inst["candidates"])):
        for scalar in (1, 2, p - 1):
            if scalar == 0:
                continue
            for r in _good_r_values(p):
                answer = {"index": index, "v": [scalar % p, 0, 0], "r": r}
                if verify(inst, answer)[0]:
                    return True
    return False


def _permute_candidates(inst: dict, permutation: list[int]) -> dict:
    moved = copy.deepcopy(inst)
    moved["candidates"] = [copy.deepcopy(inst["candidates"][i])
                           for i in permutation]
    old_index = inst["answer"]["index"]
    moved["answer"]["index"] = permutation.index(old_index)
    return moved


def _frobenius_instance(inst: dict, power: int = 1) -> dict:
    moved = copy.deepcopy(inst)
    p = inst["p"]
    modulus = tuple(inst["modulus"][:3])
    moved["candidates"] = [
        [list(_frob(tuple(value), p, modulus, power)) for value in row]
        for row in inst["candidates"]
    ]
    moved["answer"]["v"] = list(_frob(tuple(inst["answer"]["v"]),
                                            p, modulus, power))
    return moved


def _multiplicative_instance(inst: dict, output_scale: FE,
                             input_scale: FE) -> dict:
    """Carry witnesses through f(X) -> output_scale*f(input_scale*X)."""
    moved = copy.deepcopy(inst)
    p = inst["p"]
    modulus = tuple(inst["modulus"][:3])
    if output_scale == _zero() or input_scale == _zero():
        raise ValueError("multiplicative relabelling scalars must be nonzero")
    exponents = (2, p + 1, p * p + 1, 2 * p, 2 * p * p)
    factors = [_mul(output_scale, _pow(input_scale, exponent, p, modulus),
                    p, modulus) for exponent in exponents]
    moved["candidates"] = [
        [list(_mul(tuple(value), factors[index], p, modulus))
         for index, value in enumerate(row)]
        for row in inst["candidates"]
    ]
    moved["answer"]["v"] = list(_mul(tuple(inst["answer"]["v"]),
                                           input_scale, p, modulus))
    return moved


def _independent_multiplicative_instance(
        inst: dict, scales: list[tuple[FE, FE]]) -> dict:
    """Scale each candidate independently and carry the selected witness."""
    if len(scales) != len(inst["candidates"]):
        raise ValueError("one input/output scale pair is required per row")
    moved = copy.deepcopy(inst)
    p = inst["p"]
    modulus = tuple(inst["modulus"][:3])
    exponents = (2, p + 1, p * p + 1, 2 * p, 2 * p * p)
    for row_index, (output_scale, input_scale) in enumerate(scales):
        if output_scale == _zero() or input_scale == _zero():
            raise ValueError("multiplicative relabelling scalars must be nonzero")
        factors = [
            _mul(output_scale, _pow(input_scale, exponent, p, modulus),
                 p, modulus)
            for exponent in exponents
        ]
        moved["candidates"][row_index] = [
            list(_mul(tuple(value), factor, p, modulus))
            for value, factor in zip(inst["candidates"][row_index], factors)
        ]
        if row_index == inst["answer"]["index"]:
            moved["answer"]["v"] = list(_mul(
                tuple(inst["answer"]["v"]), input_scale, p, modulus))
    return moved


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))

    def atoms(value: object) -> int:
        if isinstance(value, dict):
            return sum(atoms(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return sum(atoms(v) for v in value)
        return 1

    return len(encoded), (len(encoded) + 3) // 4, atoms(answer)


def selftest() -> dict:
    """Run all correctness, resistance, scale, canonicality, and size gates."""
    report: dict = {}

    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2026):
            trial = make_instance(seed=seed, **params)
            ok, reason = verify(trial, trial["answer"])
            json_native = json.loads(json.dumps(trial["answer"])) == trial["answer"]
            checks += 1
            if not (ok and json_native):
                failures.append({"preset": preset, "seed": seed,
                                 "reason": reason, "json_native": json_native})
    report["G1_planted_verifies"] = {
        "pass": not failures, "checks": checks, "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping_params)
    answer = copy.deepcopy(inst["answer"])
    swapped_answer = None
    for i, j in ((0, 1), (0, 2), (1, 2)):
        candidate = copy.deepcopy(answer)
        candidate["v"][i], candidate["v"][j] = (
            candidate["v"][j], candidate["v"][i])
        if not verify(inst, candidate)[0]:
            swapped_answer = candidate
            break
    if swapped_answer is None:
        swapped_answer = copy.deepcopy(answer)
        swapped_answer["v"] = swapped_answer["v"][::-1]
    corruptions = {
        "drop_one": {**answer, "v": answer["v"][:-1]},
        "swap_one": swapped_answer,
        "duplicate_one": {**answer, "v": answer["v"] + [answer["v"][-1]]},
        "empty": {},
        "out_of_range": {**answer, "index": len(inst["candidates"])},
    }
    rejections = {}
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        rejections[name] = {"rejected": not ok, "reason": reason}
    reasons = [row["reason"] for row in rejections.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in rejections.values())
                and len(set(reasons)) == len(reasons),
        "rejections": rejections,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "The invariant singles out one row; my exact certificate is below.\n"
        "```text\nintermediate arithmetic omitted\n```\n"
        f"<answer>\n{json.dumps(answer)}\n</answer>\n"
        "All coordinates are reduced modulo p."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0]
                and parse_answer("garbage") is None,
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    rng = random.Random(0x260526263)
    total = 200_000
    hits = 0
    sample_start = time.perf_counter()
    for _ in range(total):
        hits += int(verify(inst, random_candidate(inst, rng))[0])
    sample_wall = time.perf_counter() - sample_start
    valid_r = len(_good_r_values(inst["p"]))
    exact_valid = inst["p"] - 1
    exact_density = exact_valid / search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": hits / total < 1e-6 and exact_density < 1e-6,
        "hits": hits,
        "total": total,
        "observed_probability": hits / total,
        "exact_valid_certificates": exact_valid,
        "certificate_space": search_space(inst),
        "exact_density": exact_density,
        "structure_aware_prior": (
            f"uniform row, nonzero v, and one of {valid_r} admissible r values"
        ),
        "wall_clock_sec": round(sample_wall, 6),
    }

    demo = make_instance(seed=2718, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    reference = _reference_algorithm(inst)
    report["G5_density_and_baseline"] = {
        "pass": (demo_count is not None and reference["ok"]
                 and exact_density < 1e-6),
        "shipping_density_exact": exact_density,
        "shipping_valid_count_exact": exact_valid,
        "shipping_certificate_space": search_space(inst),
        "shipping_sample_hits": hits,
        "shipping_sample_total": total,
        "demo_valid_count_enumerated": demo_count,
        "demo_certificate_space": search_space(demo),
        "strongest_attack": "Proposition 2.1 exhaustive Dickson enumeration",
        "baseline_wall_clock_sec": round(reference["wall_clock_sec"], 6),
        "baseline_directions_tested": reference["counter"]["directions_tested"],
        "baseline_scalar_operations": reference["counter"]["scalar_operations"],
    }

    attack_seeds = list(range(8))
    attack_results = {
        "outlier_coordinate_energy": {"successes": 0, "attempts": 0},
        "greedy_first_candidate": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
        "base_field_twist_ansatz": {"successes": 0, "attempts": 0},
    }
    for seed in attack_seeds:
        trial = make_instance(seed=seed + 9000, **shipping_params)
        outcomes = {
            "outlier_coordinate_energy": _attack_outlier_energy(trial),
            "greedy_first_candidate": _attack_greedy_first(trial),
            "random_restart_256": _attack_random_restart(trial, seed),
            "base_field_twist_ansatz": _attack_base_field_twist(trial),
        }
        for name, success in outcomes.items():
            attack_results[name]["successes"] += int(success)
            attack_results[name]["attempts"] += 1
    all_failed = all(row["successes"] == 0 and row["attempts"] >= 8
                     for row in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference["ok"],
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "Proposition 2.1 exhaustive Dickson determinant test",
            "complexity": "O(m*p^2) projective 3-by-3 determinant tests",
            "wall_clock_sec": round(reference["wall_clock_sec"], 6),
            "operations": reference["counter"]["scalar_operations"],
            "directions_tested": reference["counter"]["directions_tested"],
            "solves": "1/1, as expected on Track B",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * int(doubled_params["n"])
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["p"] > inst["p"]
                and search_space(doubled) > search_space(inst),
        "shipping_p": inst["p"],
        "doubled_p": doubled["p"],
        "shipping_space": search_space(inst),
        "doubled_space": search_space(doubled),
        "doubled_verify_reason": doubled_reason,
    }

    invariant_checks = 0
    carried_checks = 0
    keys = []
    canonical_failures = []
    for seed in range(20):
        trial = make_instance(seed=seed + 12000, **shipping_params)
        key = canonical_key(trial)
        keys.append(key)
        permutation = list(reversed(range(len(trial["candidates"]))))
        reordered = _permute_candidates(trial, permutation)
        conjugated = _frobenius_instance(trial, 1)
        relabel_rng = random.Random(seed ^ 0xC4A0C1)
        output_scale = _rand_fe(relabel_rng, trial["p"], nonzero=True)
        input_scale = _rand_fe(relabel_rng, trial["p"], nonzero=True)
        scaled = _multiplicative_instance(trial, output_scale, input_scale)
        independent_scales = [
            (_rand_fe(relabel_rng, trial["p"], nonzero=True),
             _rand_fe(relabel_rng, trial["p"], nonzero=True))
            for _ in trial["candidates"]
        ]
        independently_scaled = _independent_multiplicative_instance(
            trial, independent_scales)
        composed = _multiplicative_instance(
            _independent_multiplicative_instance(
                _frobenius_instance(reordered, 2), independent_scales),
            output_scale, input_scale)
        for name, moved in (("reorder", reordered),
                            ("frobenius", conjugated),
                            ("input_output_scaling", scaled),
                            ("independent_row_scaling", independently_scaled),
                            ("composed", composed)):
            invariant_checks += 1
            if canonical_key(moved) != key:
                canonical_failures.append({"seed": seed, "map": name,
                                           "failure": "key changed"})
            ok, why = verify(moved, moved["answer"])
            carried_checks += 1
            if not ok:
                canonical_failures.append({"seed": seed, "map": name,
                                           "failure": why})
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not canonical_failures and distinct == len(keys),
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": len(keys),
        "distinct_keys": distinct,
        "failures": canonical_failures,
        "symmetries": ["candidate reordering", "global Frobenius",
                       "independent nonzero input/output scaling per row",
                       "their composition"],
    }

    chars, tokens, elements = _answer_metrics(inst["answer"])
    intended_ops = _compact_route_operation_bound(
        inst["p"], len(inst["candidates"]))
    arms = copy.deepcopy(G9_EVIDENCE)
    hinted = arms.get("hinted", {"solved": 0, "attempts": 0})
    placebo = arms.get("placebo", {"solved": 0, "attempts": 0})
    hinted_rate = (hinted["solved"] / hinted["attempts"]
                   if hinted["attempts"] else None)
    placebo_rate = (placebo["solved"] / placebo["attempts"]
                    if placebo["attempts"] else None)
    within_caps = chars <= 2000 and elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {name: arms.get(name, {"solved": 0, "attempts": 0})
                 for name in ("bare", "hinted", "placebo")},
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None
        ),
        "hinted_verdict": arms.get("hinted_verdict", "not_run"),
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "diagnostic_not_gated": True,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping_params
    report["certificate_language"] = CERTIFICATE_LANGUAGE
    report["problem_profile"] = PROBLEM_PROFILE
    gate_rows = [value for key, value in report.items()
                 if key.startswith("G") and key[1:2].isdigit()]
    report["all_passed"] = all(row.get("pass") for row in gate_rows)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
