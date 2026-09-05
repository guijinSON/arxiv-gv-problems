"""Verified inverse-polynomial generator for arXiv:2409.18758.

The construction is the odd-characteristic, ``a = 1`` specialization of
Theorem 3.1.  Parameters satisfying the theorem are sampled first, the public
permutation polynomial is expanded, and its inverse coefficient table is
expanded from the theorem's displayed formula.  Generation never solves the
emitted interpolation problem.
"""

from __future__ import annotations

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
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - supported fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "the quadratic finite field GF(p^2) in the basis {1,i}",
        "a permutation polynomial over GF(p^2)",
        "a sparse compositional-inverse polynomial over GF(p^2)",
    ],
    "verification_operations": [
        "exact arithmetic in GF(p^2)",
        "binomial expansion of powers of x^p+x",
        "exact coefficient comparison for the local inverse identity",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "The nonlinear exponent clusters are binomial expansions in the "
        "fibre coordinate x^p+x; without recognizing that coordinate, a "
        "solver must recover the inverse coefficients by interpolation."
    ),
    "hardness_basis": (
        "Track B: exact restricted-support interpolation followed by Gaussian "
        "elimination is polynomial in the displayed basis size and recovered "
        "each p=131071 shipping inverse in about 130000 field operations and "
        "0.05 seconds, whereas Theorem 3.1 compresses the same calculation to "
        "about 120 exact operations once the x^p+x blocks are seen."
    ),
    "max_answer_tokens": 178,
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
        "A JSON polynomial coefficient table with exactly the displayed, "
        "strictly increasing exponent list; every coefficient is [r,s] for "
        "r+s*i in GF(p^2), with 0 <= r,s < p."
    ),
    "bounds": {
        "terms": "5 in demo and 33 in every hardened preset",
        "coefficient_coordinates": "integers in [0,p-1]",
        "exponents": "the 5 or 33 values printed in the instance",
        "largest_supported_prime": 2305843009213693951,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 3, "term_count": 1},
    "easy": {"n": 127, "term_count": 5},
    "medium": {"n": 8191, "term_count": 5},
    "hard": {"n": 131071, "term_count": 5},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The nonlinear exponent clusters are coefficient patterns of powers of "
    "the fibre map x^p+x."
)
PLACEBO_HINT = (
    "The listed coefficients should be handled consistently in the stated "
    "finite-field basis."
)

# Replaced with script-owned measurements after the three hardening runs.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 2, "attempts": 3},
    "hinted_verdict": "too_easy",
}

NOTES = r"""
Definition and triage.  Section 1 defines a permutation polynomial and its
unique compositional inverse modulo x^(q)-x.  Section 2, Lemma 2.2 is the local
inverse criterion.  Section 3, Theorem 3.1 is decisive: for
f(x)=u*x^q+v*x+g(x^q+a*x) over GF(q^2), it gives both exact hypotheses and an
explicit inverse.  Thus an undisclosed Track-A claim would be false.  Theorem
3.3 and Remark 3.4 also give the adjugate/Dickson-matrix route for linearized
polynomials, another explicitly easy regime avoided here.

Construction.  Take q=p, p=3 mod 4, represent GF(p^2)=GF(p)[i]/(i^2+1), and
specialize Theorem 3.1(ii) to a=1 and b_1=0.  Sample u=(u0,s) and v=(v0,s)
with u0-v0 and u0+v0 nonzero.  For each selected exponent k>=2 sample
b_k=(0,t_k), so b_k^p+b_k=0.  Consequently c=u+v^p=u0+v0 is nonzero and all
of Theorem 3.1(ii)'s hypotheses hold.  Expand the public f and, independently,
expand
  (v-u)^(-1) [x-g(c^(-1)(x^p+x))-u*c^(-1)(x^p+x)].
This is theorem-backed inverse generation, not interpolation or search.

Attacks.  There are no separately distributed plant and decoy terms: every
coefficient block comes from the same sampled local form, and conjugation/sign
orbits therefore reveal no planted outlier.  Composition is not coefficientwise,
which defeats the greedy reciprocal table; the fixed-support language has
p^(66) candidates at shipping, which defeats uniform restarts; and every sampled
b_k is nonzero, so the tempting inverse of the linearized part cannot also invert
the nonlinear summand.  The successful generic restricted-support interpolation
algorithm is disclosed separately, as Track B requires.
""".strip()


# ---------------------------------------------------------------------------
# Exact arithmetic in GF(p^2) = GF(p)[i]/(i^2+1), p == 3 (mod 4)


class _Counter:
    __slots__ = ("adds", "multiplies", "inversions", "euclid_divisions")

    def __init__(self) -> None:
        self.adds = 0
        self.multiplies = 0
        self.inversions = 0
        self.euclid_divisions = 0

    @property
    def operations(self) -> int:
        return self.adds + self.multiplies + self.euclid_divisions


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small:
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        s += 1
        d //= 2
    # Deterministic for every n < 2^64.
    for a in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if a % n == 0:
            continue
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def _validate_params(n: int, term_count: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer prime")
    if not _is_prime(n) or n % 4 != 3:
        raise ValueError("n must be a prime congruent to 3 modulo 4")
    if isinstance(term_count, bool) or not isinstance(term_count, int):
        raise ValueError("term_count must be an integer")
    if not 1 <= term_count <= len(_POWER_POOL):
        raise ValueError("term_count is outside the supported range")
    if _POWER_POOL[term_count - 1] >= n:
        raise ValueError("every nonlinear power must be below n")


def _mod_inv(a: int, p: int, counter: _Counter | None = None) -> int:
    a %= p
    if a == 0:
        raise ZeroDivisionError("zero has no inverse")
    old_r, r = p, a
    old_s, s = 0, 1
    while r:
        q = old_r // r
        if counter is not None:
            counter.euclid_divisions += 1
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
    return old_s % p


def _fadd(a: tuple[int, int], b: tuple[int, int], p: int,
          counter: _Counter | None = None) -> tuple[int, int]:
    if counter is not None:
        counter.adds += 1
    return ((a[0] + b[0]) % p, (a[1] + b[1]) % p)


def _fneg(a: tuple[int, int], p: int) -> tuple[int, int]:
    return ((-a[0]) % p, (-a[1]) % p)


def _fsub(a: tuple[int, int], b: tuple[int, int], p: int,
          counter: _Counter | None = None) -> tuple[int, int]:
    return _fadd(a, _fneg(b, p), p, counter)


def _fmul(a: tuple[int, int], b: tuple[int, int], p: int,
          counter: _Counter | None = None) -> tuple[int, int]:
    if counter is not None:
        counter.multiplies += 1
    return ((a[0] * b[0] - a[1] * b[1]) % p,
            (a[0] * b[1] + a[1] * b[0]) % p)


def _fscale(a: tuple[int, int], scalar: int, p: int,
            counter: _Counter | None = None) -> tuple[int, int]:
    return _fmul(a, (scalar % p, 0), p, counter)


def _fconj(a: tuple[int, int], p: int) -> tuple[int, int]:
    return (a[0], (-a[1]) % p)


def _finv(a: tuple[int, int], p: int,
          counter: _Counter | None = None) -> tuple[int, int]:
    if a == (0, 0):
        raise ZeroDivisionError("zero has no inverse")
    if counter is not None:
        counter.inversions += 1
    norm = (a[0] * a[0] + a[1] * a[1]) % p
    z = _mod_inv(norm, p, counter)
    return (a[0] * z % p, -a[1] * z % p)


def _fpow(a: tuple[int, int], exponent: int, p: int,
          counter: _Counter | None = None) -> tuple[int, int]:
    result = (1, 0)
    base = a
    while exponent:
        if exponent & 1:
            result = _fmul(result, base, p, counter)
        exponent >>= 1
        if exponent:
            base = _fmul(base, base, p, counter)
    return result


def _as_pair(value: object) -> tuple[int, int] | None:
    if (not isinstance(value, list) or len(value) != 2
            or any(isinstance(x, bool) or not isinstance(x, int)
                   for x in value)):
        return None
    return (value[0], value[1])


def _pair_json(value: tuple[int, int]) -> list[int]:
    return [value[0], value[1]]


_POWER_POOL = (2, 3, 5, 7, 9, 11, 13, 15)


def _powers(term_count: int) -> tuple[int, ...]:
    return _POWER_POOL[:term_count]


def _basis(p: int, powers: tuple[int, ...]) -> list[int]:
    degrees = {1, p}
    for k in powers:
        for j in range(k + 1):
            degrees.add(k + j * (p - 1))
    return sorted(degrees)


def _expanded_polynomial(p: int, u: tuple[int, int], v: tuple[int, int],
                         bs: dict[int, tuple[int, int]],
                         counter: _Counter | None = None
                         ) -> dict[int, tuple[int, int]]:
    out = {1: v, p: u}
    for k, b in bs.items():
        for j in range(k + 1):
            degree = k + j * (p - 1)
            out[degree] = _fscale(b, math.comb(k, j), p, counter)
    return out


def _inverse_from_local(p: int, u: tuple[int, int], v: tuple[int, int],
                        bs: dict[int, tuple[int, int]],
                        counter: _Counter | None = None
                        ) -> dict[int, tuple[int, int]]:
    """Expand the inverse displayed in Theorem 3.1(ii), with a=1."""
    one = (1, 0)
    c = _fadd(u, _fconj(v, p), p, counter)
    A = _finv(_fsub(v, u, p, counter), p, counter)
    C = _finv(c, p, counter)
    uC = _fmul(u, C, p, counter)
    out = {
        1: _fmul(A, _fsub(one, uC, p, counter), p, counter),
        p: _fmul(A, _fneg(uC, p), p, counter),
    }
    for k, b in bs.items():
        factor = _fmul(A, _fneg(_fmul(b, _fpow(C, k, p, counter),
                                      p, counter), p), p, counter)
        for j in range(k + 1):
            degree = k + j * (p - 1)
            out[degree] = _fscale(factor, math.comb(k, j), p, counter)
    return out


def _table(poly: dict[int, tuple[int, int]]) -> list[list[object]]:
    return [[_pair_json(poly[e]), [e]] for e in sorted(poly)]


def _public_terms(inst: dict) -> list[list[object]]:
    return sorted(inst["polynomial"], key=lambda term: term[1][0])


def _term_map(inst: dict) -> tuple[dict[int, tuple[int, int]] | None, str]:
    terms = inst.get("polynomial")
    if not isinstance(terms, list):
        return None, "instance polynomial is malformed"
    out: dict[int, tuple[int, int]] = {}
    for term in terms:
        if (not isinstance(term, list) or len(term) != 2
                or not isinstance(term[1], list) or len(term[1]) != 1
                or isinstance(term[1][0], bool)
                or not isinstance(term[1][0], int)):
            return None, "instance polynomial term is malformed"
        coeff = _as_pair(term[0])
        if coeff is None:
            return None, "instance coefficient is malformed"
        degree = term[1][0]
        if degree in out:
            return None, "instance has a duplicate exponent"
        out[degree] = coeff
    return out, "ok"


def _derive_expected(inst: dict,
                     counter: _Counter | None = None
                     ) -> tuple[dict[int, tuple[int, int]] | None, str]:
    p = inst.get("p")
    powers_obj = inst.get("nonlinear_powers")
    if (isinstance(p, bool) or not isinstance(p, int)
            or not isinstance(powers_obj, list)
            or any(isinstance(k, bool) or not isinstance(k, int)
                   for k in powers_obj)):
        return None, "instance parameters are malformed"
    powers = tuple(powers_obj)
    public, why = _term_map(inst)
    if public is None:
        return None, why
    wanted = _basis(p, powers)
    if sorted(public) != wanted:
        return None, "instance support does not match its displayed basis"
    u, v = public[p], public[1]
    if u[1] != v[1]:
        return None, "instance linear coefficients violate the local form"
    if u[0] == v[0] or (u[0] + v[0]) % p == 0:
        return None, "instance local scalars are singular"
    bs: dict[int, tuple[int, int]] = {}
    for k in powers:
        b = public[k]
        if b[0] != 0 or b[1] == 0:
            return None, "instance nonlinear coefficient is not trace-zero"
        bs[k] = b
        for j in range(k + 1):
            degree = k + j * (p - 1)
            expected = _fscale(b, math.comb(k, j), p, counter)
            if public[degree] != expected:
                return None, "instance nonlinear block is not a power of x^p+x"
    return _inverse_from_local(p, u, v, bs, counter), "ok"


def _sample_outside(rng: random.Random, p: int,
                    excluded: set[int]) -> int:
    """Uniformly sample [0,p) minus a small set without allocating O(p)."""
    blocked = sorted({x % p for x in excluded})
    value = rng.randrange(p - len(blocked))
    for forbidden in blocked:
        if value >= forbidden:
            value += 1
    return value


def make_instance(n: int, seed: int = 0, term_count: int = 5,
                  **params) -> dict:
    """Construct a certified Theorem-3.1 inverse-polynomial instance."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, term_count)
    p = n
    rng = random.Random(seed)
    u0 = rng.randrange(p)
    v0 = _sample_outside(rng, p, {u0, (-u0) % p})
    shared_imag = rng.randrange(p)
    u = (u0, shared_imag)
    v = (v0, shared_imag)
    bs = {k: (0, rng.randrange(1, p)) for k in _powers(term_count)}

    public = _expanded_polynomial(p, u, v, bs)
    inverse = _inverse_from_local(p, u, v, bs)
    inst = {
        "p": p,
        "field_modulus": "i^2+1",
        "nonlinear_powers": list(_powers(term_count)),
        "polynomial": _table(public),
        "answer": _table(inverse),
    }
    expected, why = _derive_expected(inst)
    if expected != inverse:
        raise AssertionError("Theorem 3.1 construction failed: " + why)
    return inst


# ---------------------------------------------------------------------------
# Problem contract


def _format_terms(terms: list[list[object]]) -> str:
    return "\n".join(
        f"    exponent {term[1][0]:>8}: [{term[0][0]}, {term[0][1]}]"
        for term in sorted(terms, key=lambda t: t[1][0])
    )


def render(inst: dict) -> str:
    p = inst["p"]
    basis = [term[1][0] for term in _public_terms(inst)]
    statement = f"""Recover a compositional inverse over a quadratic finite field

Let F = GF({p}^2) = GF({p})[i]/(i^2+1).  The prime {p} is 3 modulo 4, so
i^2+1 is irreducible.  Encode r+s*i as the pair [r,s], where both coordinates
are the unique integers from 0 through {p - 1}.  Pair addition and
multiplication are

    [r,s]+[t,w] = [(r+t) mod {p}, (s+w) mod {p}],
    [r,s]*[t,w] = [(r*t-s*w) mod {p}, (r*w+s*t) mod {p}].

For a polynomial P(x) over F, composition is reduced modulo x^({p*p})-x;
thus two reduced polynomials represent the same function exactly when their
coefficients agree.  A permutation polynomial is one whose function F -> F is
bijective, and its compositional inverse H is the unique reduced polynomial
satisfying both H(P(x))=x and P(H(x))=x as functions on F.

The following promised permutation polynomial P(x) is given by its complete
coefficient table on a fixed basis (a listed coefficient may be [0,0]).  Each
row means ``coefficient [r,s] times x^exponent``:

{_format_terms(inst['polynomial'])}

Its inverse is promised to have coefficients only on this ordered basis:

    {basis}

Return the COMPLETE coefficient table of H on that basis, including a row when
its coefficient is [0,0].  The table must be a JSON list in increasing exponent
order.  A row is [[r,s],[e]], meaning coefficient r+s*i at exponent e.  There
must be exactly {len(basis)} rows, with no repeated exponent; order matters and
all coordinate bounds are inclusive.  Any table defining the compositional
inverse is accepted.

"""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "Hint: " + STRUCTURAL_HINT + "\n\n"
    elif mode == "placebo":
        statement += "Hint: " + PLACEBO_HINT + "\n\n"
    statement += (
        "Give your final answer inside <answer></answer> tags as the JSON "
        "coefficient table.\n"
        "Example: <answer>[[[1,0],[1]],[[2,1],[3]]]</answer>\n"
        "Output nothing else inside the tags."
    )
    return statement


def _parsed_table(value: object) -> list[list[object]] | None:
    if not isinstance(value, list) or not value:
        return None
    last = -1
    for term in value:
        if (not isinstance(term, list) or len(term) != 2
                or _as_pair(term[0]) is None
                or not isinstance(term[1], list) or len(term[1]) != 1
                or isinstance(term[1][0], bool)
                or not isinstance(term[1][0], int)
                or term[1][0] < 0 or term[1][0] <= last):
            return None
        last = term[1][0]
    return value


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON polynomial table from model prose."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\s*>(.*?)</answer\s*>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    if not blocks:
        return None
    body = blocks[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    return _parsed_table(value)


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any inverse table by exact local-identity coefficient expansion."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) == 0:
        return False, "answer is empty"
    basis = [term[1][0] for term in _public_terms(inst)]
    if len(answer) != len(basis):
        return False, f"answer must contain exactly {len(basis)} terms"

    degrees = []
    coefficients = []
    for term in answer:
        if not isinstance(term, list) or len(term) != 2:
            return False, "each term must be [coefficient,[exponent]]"
        coeff = _as_pair(term[0])
        if coeff is None:
            return False, "each coefficient must be a pair of integers"
        exp = term[1]
        if (not isinstance(exp, list) or len(exp) != 1
                or isinstance(exp[0], bool) or not isinstance(exp[0], int)):
            return False, "each exponent must be a one-integer list"
        coefficients.append(coeff)
        degrees.append(exp[0])
    if len(set(degrees)) != len(degrees):
        return False, "answer contains a duplicate exponent"
    if degrees != sorted(degrees):
        return False, "terms must be in strictly increasing exponent order"
    if degrees != basis:
        return False, "answer exponents do not equal the displayed basis"
    p = inst["p"]
    if any(not (0 <= r < p and 0 <= s < p) for r, s in coefficients):
        return False, "a coefficient coordinate is out of range"

    expected, why = _derive_expected(inst)
    if expected is None:
        return False, why
    for degree, coefficient in zip(degrees, coefficients):
        if coefficient != expected[degree]:
            return False, f"inverse coefficient mismatch at exponent {degree}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the fixed-support language printed in the statement."""
    p = inst["p"]
    return [
        [[rng.randrange(p), rng.randrange(p)], [term[1][0]]]
        for term in _public_terms(inst)
    ]


def search_space(inst: dict) -> int | None:
    return inst["p"] ** (2 * len(inst["polynomial"]))


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the declared language only below a strict 100k cap."""
    size = search_space(inst)
    if size > 100_000:
        return None
    p = inst["p"]
    basis = [term[1][0] for term in _public_terms(inst)]
    count = 0
    for encoded in itertools.product(range(p * p), repeat=len(basis)):
        candidate = [
            [[z % p, z // p], [degree]]
            for z, degree in zip(encoded, basis)
        ]
        count += int(verify(inst, candidate)[0])
    return count


def _conjugated_terms(terms: list[list[object]], p: int
                      ) -> list[list[object]]:
    return [
        [[term[0][0], (-term[0][1]) % p], [term[1][0]]]
        for term in terms
    ]


def canonical_key(inst: dict) -> str:
    """Normalize term order and the nontrivial GF(p^2)/GF(p) automorphism."""
    p = inst["p"]
    terms = _public_terms(inst)
    conjugate = sorted(_conjugated_terms(terms, p), key=lambda t: t[1][0])
    base = [p, list(inst["nonlinear_powers"]), terms]
    moved = [p, list(inst["nonlinear_powers"]), conjugate]
    a = json.dumps(base, separators=(",", ":"))
    b = json.dumps(moved, separators=(",", ":"))
    return min(a, b)


_ESCALATION_PRIMES = (
    3, 43, 127, 8191, 131071, 524287, 2147483647,
    2305843009213693951,
)


def escalate(params: dict) -> dict | str | None:
    """Grow field size at fixed 33-term answer length; stop at the char cap."""
    n = params.get("n")
    term_count = params.get("term_count", 5)
    for prime in _ESCALATION_PRIMES:
        if prime > n:
            return {"n": prime, "term_count": term_count}
    return "cap_bound"


# ---------------------------------------------------------------------------
# Generic reference solver and construction-aware attacks


def _eval_table(terms: list[list[object]], x: tuple[int, int], p: int,
                counter: _Counter | None = None) -> tuple[int, int]:
    total = (0, 0)
    for term in terms:
        coeff = (term[0][0], term[0][1])
        power = _fpow(x, term[1][0], p, counter)
        total = _fadd(total, _fmul(coeff, power, p, counter), p, counter)
    return total


def _reference_interpolation(inst: dict) -> dict:
    """Solve for all inverse coefficients by evaluation and exact RREF."""
    p = inst["p"]
    basis = [term[1][0] for term in _public_terms(inst)]
    m = len(basis)
    pivots: dict[int, list[tuple[int, int]]] = {}
    counter = _Counter()
    start = time.perf_counter()
    rows_examined = 0
    q = p * p
    step = 2 * p + 1             # coprime to p^2
    offset = p + 1
    for t in range(q):
        code = (offset + step * t) % q
        x = (code % p, code // p)
        y = _eval_table(inst["polynomial"], x, p, counter)
        row = [_fpow(y, degree, p, counter) for degree in basis] + [x]
        rows_examined += 1
        for col in sorted(pivots):
            factor = row[col]
            if factor != (0, 0):
                pivot_row = pivots[col]
                row = [
                    _fsub(value, _fmul(factor, pivot_value, p, counter),
                          p, counter)
                    for value, pivot_value in zip(row, pivot_row)
                ]
        pivot = next((j for j in range(m) if row[j] != (0, 0)), None)
        if pivot is None:
            if row[-1] != (0, 0):
                return {"ok": False, "reason": "interpolation system inconsistent"}
            continue
        inv = _finv(row[pivot], p, counter)
        row = [_fmul(inv, value, p, counter) for value in row]
        for old_col, old_row in list(pivots.items()):
            factor = old_row[pivot]
            if factor != (0, 0):
                pivots[old_col] = [
                    _fsub(value, _fmul(factor, new_value, p, counter),
                          p, counter)
                    for value, new_value in zip(old_row, row)
                ]
        pivots[pivot] = row
        if len(pivots) == m:
            break
    if len(pivots) != m:
        return {"ok": False, "reason": "interpolation did not reach full rank"}
    solution = [(0, 0)] * m
    for col, row in pivots.items():
        solution[col] = row[-1]
    answer = [[_pair_json(c), [e]] for c, e in zip(solution, basis)]
    elapsed = time.perf_counter() - start
    ok, reason = verify(inst, answer)
    return {
        "ok": ok,
        "reason": reason,
        "answer": answer,
        "wall_clock_sec": elapsed,
        "operations": counter.operations,
        "field_additions": counter.adds,
        "field_multiplications": counter.multiplies,
        "field_inversions": counter.inversions,
        "euclid_divisions": counter.euclid_divisions,
        "rows_examined": rows_examined,
    }


def _blank_candidate(inst: dict) -> list[list[object]]:
    return [[[0, 0], [term[1][0]]] for term in _public_terms(inst)]


def _attack_outlier_orbit_representative(inst: dict) -> bool:
    p = inst["p"]
    candidate = []
    for term in _public_terms(inst):
        c = (term[0][0], term[0][1])
        orbit = {c, _fneg(c, p), _fconj(c, p),
                 _fneg(_fconj(c, p), p), (0, 0), (1, 0)}
        chosen = min(orbit, key=lambda z: (z[0] + z[1], z[0], z[1]))
        candidate.append([_pair_json(chosen), [term[1][0]]])
    return verify(inst, candidate)[0]


def _attack_greedy_coefficientwise_inverse(inst: dict) -> bool:
    p = inst["p"]
    candidate = []
    for term in _public_terms(inst):
        c = (term[0][0], term[0][1])
        d = (0, 0) if c == (0, 0) else _finv(c, p)
        candidate.append([_pair_json(d), [term[1][0]]])
    return verify(inst, candidate)[0]


def _attack_random_restart(inst: dict, seed: int,
                           restarts: int = 256) -> bool:
    rng = random.Random(seed ^ 0x240918758)
    for _ in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _attack_linear_part_only(inst: dict) -> bool:
    """Invert u*x^p+v*x and pretend the nonlinear part is absent."""
    p = inst["p"]
    public, _ = _term_map(inst)
    assert public is not None
    u, v = public[p], public[1]
    denominator = _fsub(_fmul(v, _fconj(v, p), p),
                        _fmul(u, _fconj(u, p), p), p)
    inv_d = _finv(denominator, p)
    d1 = _fmul(_fconj(v, p), inv_d, p)
    dp = _fmul(_fneg(u, p), inv_d, p)
    candidate = _blank_candidate(inst)
    locations = {term[1][0]: term for term in candidate}
    locations[1][0] = _pair_json(d1)
    locations[p][0] = _pair_json(dp)
    return verify(inst, candidate)[0]


def _conjugate_instance(inst: dict) -> tuple[dict, list[list[object]]]:
    p = inst["p"]
    moved = {k: v for k, v in inst.items() if k not in ("polynomial", "answer")}
    moved["polynomial"] = _conjugated_terms(inst["polynomial"], p)
    carried = _conjugated_terms(inst["answer"], p)
    moved["answer"] = carried
    return moved, carried


def _reorder_instance(inst: dict) -> tuple[dict, list[list[object]]]:
    moved = {k: v for k, v in inst.items() if k not in ("polynomial", "answer")}
    moved["polynomial"] = list(reversed(inst["polynomial"]))
    carried = json.loads(json.dumps(inst["answer"]))
    moved["answer"] = carried
    return moved, carried


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))

    def atoms(value: object) -> int:
        if isinstance(value, dict):
            return sum(atoms(v) for v in value.values())
        if isinstance(value, list):
            return sum(atoms(v) for v in value)
        return 1

    # Approximate common BPE tokenization conservatively enough for this compact
    # numeric JSON: four characters per token, rounded upward.
    return len(encoded), math.ceil(len(encoded) / 4), atoms(answer)


def selftest() -> dict:
    """Run every mandatory gate and return a JSON-native measurement dict."""
    report: dict = {}

    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2026):
            trial = make_instance(seed=seed, **params)
            ok, why = verify(trial, trial["answer"])
            json_ok = json.loads(json.dumps(trial["answer"])) == trial["answer"]
            g1_checks += 1
            if not (ok and json_ok):
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": why, "json_native": json_ok})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **ship_params)
    planted = inst["answer"]
    drop = json.loads(json.dumps(planted[:-1]))
    swapped = json.loads(json.dumps(planted))
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicate = json.loads(json.dumps(planted))
    duplicate[1][1][0] = duplicate[0][1][0]
    out_of_range = json.loads(json.dumps(planted))
    out_of_range[0][0][0] = inst["p"]
    corruptions = {
        "drop_one": drop,
        "swap_two": swapped,
        "duplicate_exponent": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    rejection_reasons = {}
    all_rejected = True
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        all_rejected &= not ok
        rejection_reasons[name] = why
    distinct = len(set(rejection_reasons.values()))
    report["G2_rejects_corruption"] = {
        "pass": all_rejected and distinct == len(corruptions),
        "rejections": rejection_reasons,
        "distinct_reasons": distinct,
    }

    realistic = (
        "The local coordinate gives the following exact table.\n\n"
        "```json\ncoefficient computation omitted\n```\n"
        f"<answer>\n{json.dumps(planted)}\n</answer>\n"
        "All residues are in the required range."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": (parsed == planted and verify(inst, parsed)[0]
                 and parse_answer("garbage") is None),
        "parsed_matches": parsed == planted,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    guess_rng = random.Random(0x240918758)
    guess_total = 200_000
    hits = 0
    sample_start = time.perf_counter()
    for _ in range(guess_total):
        hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    sampling_seconds = time.perf_counter() - sample_start
    density = hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6,
        "hits": hits,
        "total": guess_total,
        "empirical_probability": density,
        "prior": (
            "uniform over every GF(p^2) coefficient on the exact fixed support "
            "printed in the statement"
        ),
        "candidate_space": search_space(inst),
        "sampling_wall_seconds": sampling_seconds,
    }

    baseline_start = time.perf_counter()
    baseline_success = _attack_random_restart(inst, 0xB451, restarts=4096)
    baseline_seconds = time.perf_counter() - baseline_start
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    one_reference = _reference_interpolation(inst)
    report["G5_density_and_baseline"] = {
        "pass": (density < 1e-6 and not baseline_success
                 and demo_count == 1 and one_reference.get("ok") is True),
        "shipping_observed_valid_fraction": density,
        "shipping_density_sample_count": guess_total,
        "shipping_valid_hits": hits,
        "shipping_candidate_space": search_space(inst),
        "unique_inverse_count": 1,
        "baseline_wall_seconds": baseline_seconds,
        "baseline_iterations": 4096,
        "baseline_successes": int(baseline_success),
        "reference_wall_seconds": one_reference.get("wall_clock_sec", 0.0),
        "reference_operation_count": one_reference.get("operations", 0),
        "reference_rows_examined": one_reference.get("rows_examined", 0),
        "demo_exact_solution_count": demo_count,
        "enumerate_all_shipping": None,
    }

    attack_names = {
        "outlier_extreme_orbit_representative": 0,
        "greedy_coefficientwise_inverse": 0,
        "random_restart_256_structure_aware": 0,
        "linearized_part_only_ansatz": 0,
    }
    reference_runs = []
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **ship_params)
        attack_names["outlier_extreme_orbit_representative"] += int(
            _attack_outlier_orbit_representative(trial))
        attack_names["greedy_coefficientwise_inverse"] += int(
            _attack_greedy_coefficientwise_inverse(trial))
        attack_names["random_restart_256_structure_aware"] += int(
            _attack_random_restart(trial, seed))
        attack_names["linearized_part_only_ansatz"] += int(
            _attack_linear_part_only(trial))
        reference_runs.append(_reference_interpolation(trial))
    all_attacks_failed = all(value == 0 for value in attack_names.values())
    reference_ok = sum(int(run.get("ok") is True) for run in reference_runs)
    reference_wall = sum(run.get("wall_clock_sec", 0.0) for run in reference_runs)
    reference_ops = sum(run.get("operations", 0) for run in reference_runs)
    reference_rows = sum(run.get("rows_examined", 0) for run in reference_runs)
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_ok == 8,
        "attacks": {
            name: {"successes": successes, "attempts": 8}
            for name, successes in attack_names.items()
        },
        "reference_algorithm": {
            "name": "restricted-support evaluation/interpolation with exact RREF",
            "complexity": (
                "O(m^3 + r*m*log(p*m)) GF(p^2) operations after r rows, "
                "with r<=p^2; m=33 at shipping"
            ),
            "wall_clock_sec": reference_wall,
            "mean_wall_clock_sec": reference_wall / 8,
            "operations": reference_ops,
            "mean_operations": reference_ops // 8,
            "rows_examined": reference_rows,
            "mean_rows_examined": reference_rows / 8,
            "solves": f"{reference_ok}/8, as expected",
        },
    }

    doubled_prime = next(p for p in _ESCALATION_PRIMES
                         if p > 2 * ship_params["n"])
    doubled = make_instance(n=doubled_prime,
                            term_count=ship_params["term_count"], seed=77)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_prime > 2 * ship_params["n"],
        "base_n": ship_params["n"],
        "doubled_valid_n": doubled_prime,
        "doubled_verify": doubled_why,
        "answer_terms_unchanged": (
            len(doubled["answer"]) == len(inst["answer"]))
    }

    invariance = 0
    carried_checks = 0
    attempts = 0
    for seed in range(20):
        trial = make_instance(seed=seed + 700, **ship_params)
        reordered, same_answer = _reorder_instance(trial)
        conjugated, conjugate_answer = _conjugate_instance(trial)
        composed, composed_answer = _reorder_instance(conjugated)
        for moved, carried in ((reordered, same_answer),
                               (conjugated, conjugate_answer),
                               (composed, composed_answer)):
            attempts += 1
            invariance += int(canonical_key(moved) == canonical_key(trial))
            carried_checks += int(verify(moved, carried)[0])
    unrelated = {
        canonical_key(make_instance(seed=seed + 9000, **ship_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": (invariance == attempts and carried_checks == attempts
                 and len(unrelated) == 20),
        "invariance_checks": invariance,
        "invariance_attempts": attempts,
        "transformed_witness_checks": carried_checks,
        "unrelated_distinct": len(unrelated),
        "unrelated_attempts": 20,
        "transformations": (
            "input term reordering, GF(p^2)/GF(p) conjugation, and their "
            "composition"
        ),
    }

    chars, tokens, elements = _answer_metrics(inst["answer"])
    route_counter = _Counter()
    expected, route_why = _derive_expected(inst, route_counter)
    route_ok = expected is not None and route_why == "ok"
    within_caps = (chars <= 2000 and tokens <= 500 and elements <= 256
                   and route_counter.operations <= 300)
    evidence = G9_EVIDENCE
    h_attempts = evidence["hinted"]["attempts"]
    p_attempts = evidence["placebo"]["attempts"]
    h_rate = evidence["hinted"]["solved"] / h_attempts if h_attempts else 0.0
    p_rate = evidence["placebo"]["solved"] / p_attempts if p_attempts else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": within_caps and route_ok,
        "arms": {
            "bare": dict(evidence["bare"]),
            "hinted": dict(evidence["hinted"]),
            "placebo": dict(evidence["placebo"]),
        },
        "hinted_minus_placebo": h_rate - p_rate,
        "hinted_verdict": evidence["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": route_counter.operations,
        "caps": {"chars": 2000, "tokens": 500,
                 "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship_params)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
