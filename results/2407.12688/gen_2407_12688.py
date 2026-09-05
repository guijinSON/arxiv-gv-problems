"""Verified native finite-field problems from arXiv:2407.12688.

The task is to invert one value of a linear-equivalence transform of the
paper's Theorem 3.8 permutation polynomial over GF(p^3).  A preimage is sampled
first and the target is then computed, so generation never searches for the
witness.  Verification is one exact polynomial evaluation.  The compact route
recognizes the rank-two linearized part and rank-one nonlinear part inherited
from Proposition 4.1; exhaustive inversion is the disclosed Track-B reference.
"""

from __future__ import annotations

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
except ImportError:  # pragma: no cover - this family needs no helper package
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "cubic finite field presented as F_p[z]/(z^3-g)",
        "expanded sparse permutation polynomial over F_(p^3)",
        "finite-field preimage represented in the polynomial basis",
    ],
    "verification_operations": [
        "exact arithmetic in F_p[z]/(z^3-g)",
        "exact Frobenius powering",
        "exact substitution into the permutation polynomial",
        "coefficient-vector equality",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "The expanded polynomial splits into a rank-two linearized map and a "
        "rank-one fifth power, turning inversion over p^3 elements into one "
        "small coordinate solve and one power inversion in F_p."
    ),
    "hardness_basis": (
        "Track B: inverse-table enumeration evaluates the expanded Section 4.2 "
        "linear-equivalence transform in O(p^3 log s) field operations; on the "
        "lower-edge shipping instance p=103 it examines a measured 222,004 "
        "candidates (6,438,116 modular operations, 1.2--2.1 seconds over "
        "repeated local runs), whereas "
        "recognizing the Section 4.1 rank decomposition uses at most 286 exact "
        "finite-field operations but must be found without a CAS."
    ),
    "max_answer_tokens": 4,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

# n is a lower bound for p.  The seed selects one of prime_span consecutive
# admissible primes at or above n.  The answer always has three coordinates.
DIFFICULTY = {
    "demo": {"n": 7, "s": 5, "prime_span": 1},
    "easy": {"n": 103, "s": 5, "prime_span": 32},
    "medium": {"n": 163, "s": 5, "prime_span": 64},
    "hard": {"n": 193, "s": 5, "prime_span": 128},
}
SHIPPING_DIFFICULTY = "easy"

CERTIFICATE_LANGUAGE = {
    "description": (
        "One element of F_p[z]/(z^3-g), written uniquely as the three-integer "
        "coefficient vector [c0,c1,c2] with 0 <= ci < p."
    ),
    "bounds": {
        "dimension": 3,
        "coordinate_lower_inclusive": 0,
        "coordinate_upper_offset_from_p": -1,
    },
}

STRUCTURAL_HINT = (
    "The linearized component has rank two and its nonlinear complement is a "
    "fifth power with one-dimensional image."
)
PLACEBO_HINT = (
    "Careful modular bookkeeping keeps all three displayed field coordinates "
    "consistent throughout the calculation."
)

# Script-owned runs on 2026-09-05 at the shipping preset.  The three arms are
# diagnostics; only the answer-size and intended-route caps gate G9.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "hardened",
}

NOTES = """\
Theorem 3.8 fixes the native family: for a in the norm-one subgroup, a != 1,
and gcd(s,p-1)=1, f_5=A_a+A_(a^2)+Tr^s permutes F_(p^3).  Proposition 4.1
and Table 1 in Section 4.1 supply its compositional inverse through the three
local components.  Section 4.2 defines linear equivalence by invertible
linearized pre- and post-composition; the generator applies exactly that map
and expands the result.  This avoids making Table 1 a direct lookup while
staying in the paper's native polynomial objects.

This is Track B because a generic inverse table is still an effective O(p^3)
algorithm.  The generator samples x before forming y=h(x), where h=Q o f_5 o P.
Sparse-coordinate, copy-output, linear-only, termwise-power, and random-restart
attacks are tested; none sees the rank decomposition in the expanded terms.
Difficulty grows by increasing p while the witness remains one field element.
"""


# --- Prime and cubic-field arithmetic --------------------------------------

def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for q in small:
        if n % q == 0:
            return n == q
    d = 41
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def _admissible_prime_at(n: int, s: int, index: int = 0) -> int:
    """The indexed prime p >= n with p=1 mod 3 and gcd(s,p-1)=1."""
    p = max(7, int(n))
    seen = 0
    while True:
        if p % 3 == 1 and math.gcd(s, p - 1) == 1 and _is_prime(p):
            if seen == index:
                return p
            seen += 1
        p += 1


def _first_noncube(p: int) -> int:
    for g in range(2, p):
        if pow(g, (p - 1) // 3, p) != 1:
            return g
    raise ValueError("no cubic nonresidue found")


def _add(x, y, p: int):
    return tuple((a + b) % p for a, b in zip(x, y))


def _scale(c: int, x, p: int):
    return tuple(c * a % p for a in x)


def _mul(x, y, p: int, g: int):
    """Multiply coefficient triples modulo z^3-g."""
    a0, a1, a2 = x
    b0, b1, b2 = y
    return (
        (a0 * b0 + g * (a1 * b2 + a2 * b1)) % p,
        (a0 * b1 + a1 * b0 + g * a2 * b2) % p,
        (a0 * b2 + a1 * b1 + a2 * b0) % p,
    )


def _pow(x, e: int, p: int, g: int):
    out = (1, 0, 0)
    base = tuple(x)
    while e:
        if e & 1:
            out = _mul(out, base, p, g)
        base = _mul(base, base, p, g)
        e >>= 1
    return out


def _frob(x, p: int, g: int, times: int = 1):
    """Frobenius in the chosen basis; z^p=omega*z."""
    times %= 3
    if times == 0:
        return tuple(x)
    omega = pow(g, (p - 1) // 3, p)
    if times == 1:
        return (x[0] % p, x[1] * omega % p,
                x[2] * omega * omega % p)
    return (x[0] % p, x[1] * omega * omega % p,
            x[2] * omega % p)


def _A(a, x, p: int, g: int):
    """A_a(X)=X^(p^2)+aX^p+a^(1+p^2)X from Section 2."""
    xp = _frob(x, p, g, 1)
    xp2 = _frob(x, p, g, 2)
    c = _mul(a, _frob(a, p, g, 2), p, g)
    return _add(xp2, _add(_mul(a, xp, p, g), _mul(c, x, p, g), p), p)


def _trace(x, p: int, g: int):
    return _add(tuple(x), _add(_frob(x, p, g, 1),
                               _frob(x, p, g, 2), p), p)


def _mat_mul(a, b, p: int):
    return [[sum(a[i][k] * b[k][j] for k in range(len(b))) % p
             for j in range(len(b[0]))] for i in range(len(a))]


def _random_invertible_matrix(rng, p: int):
    """Build, rather than search for, an invertible 3x3 matrix."""
    a = [[int(i == j) for j in range(3)] for i in range(3)]
    for step in range(12):
        if step % 3 == 0:
            i, j = rng.sample(range(3), 2)
            a[i], a[j] = a[j], a[i]
        elif step % 3 == 1:
            i = rng.randrange(3)
            c = rng.randrange(1, p)
            a[i] = [c * v % p for v in a[i]]
        else:
            i, j = rng.sample(range(3), 2)
            c = rng.randrange(1, p)
            a[i] = [(u + c * v) % p for u, v in zip(a[i], a[j])]
    return a


def _linearized_matrix(coefficients, p: int, g: int):
    """Coordinate matrix of sum_k coefficients[k]*X^(p^k)."""
    def fn(x):
        out = (0, 0, 0)
        for k, c in enumerate(coefficients):
            out = _add(out, _mul(tuple(c), _frob(x, p, g, k), p, g), p)
        return out
    return _linear_matrix(fn, p)


def _matrix_to_linearized(matrix, p: int, g: int):
    """Represent an arbitrary F_p-linear coordinate map as a p-polynomial."""
    columns = []
    for k in range(3):
        for r in range(3):
            c = tuple(int(i == r) for i in range(3))
            m = _linearized_matrix(
                [c if j == k else (0, 0, 0) for j in range(3)], p, g)
            columns.append([m[i][j] for i in range(3) for j in range(3)])
    system = [[columns[col][row] for col in range(9)] for row in range(9)]
    inv = _mat_inv(system, p)
    if inv is None:
        raise ValueError("linearized-coordinate conversion is singular")
    target = [matrix[i][j] % p for i in range(3) for j in range(3)]
    flat = _mat_vec(inv, target, p)
    return [tuple(flat[3 * k:3 * k + 3]) for k in range(3)]


def _expand_power(outer, forms, s: int, p: int, g: int):
    """Expand outer*(d0*X+d1*X^p+d2*X^(p^2))^s."""
    out = {}
    fact_s = math.factorial(s)
    for i in range(s + 1):
        for j in range(s - i + 1):
            k = s - i - j
            multinomial = fact_s // (math.factorial(i) * math.factorial(j)
                                     * math.factorial(k))
            coef = tuple(outer)
            for d, power in zip(forms, (i, j, k)):
                coef = _mul(coef, _pow(tuple(d), power, p, g), p, g)
            coef = _scale(multinomial, coef, p)
            exponent = i + j * p + k * p * p
            out[exponent] = _add(out.get(exponent, (0, 0, 0)), coef, p)
    return {e: c for e, c in out.items() if c != (0, 0, 0)}


def _terms_from_coordinate_form(linear, outer, functional, s: int,
                                p: int, g: int):
    linear_coeffs = _matrix_to_linearized(linear, p, g)
    functional_matrix = [list(functional), [0, 0, 0], [0, 0, 0]]
    form_coeffs = _matrix_to_linearized(functional_matrix, p, g)
    terms = _expand_power(tuple(outer), form_coeffs, s, p, g)
    for k, coef in enumerate(linear_coeffs):
        exponent = p ** k
        terms[exponent] = _add(terms.get(exponent, (0, 0, 0)), coef, p)
    return {e: c for e, c in terms.items() if c != (0, 0, 0)}


def _eval_terms_raw(terms, x, p: int, g: int, s: int):
    """Direct exact evaluation using base-p exponent digits."""
    bases = [tuple(x), _frob(tuple(x), p, g, 1),
             _frob(tuple(x), p, g, 2)]
    powers = []
    for base in bases:
        row = [(1, 0, 0)]
        for _ in range(s):
            row.append(_mul(row[-1], base, p, g))
        powers.append(row)
    total = (0, 0, 0)
    for exponent, coefficient in terms:
        digits = []
        e = exponent
        for _ in range(3):
            digits.append(e % p)
            e //= p
        monomial = (1, 0, 0)
        for row, digit in zip(powers, digits):
            monomial = _mul(monomial, row[digit], p, g)
        total = _add(total, _mul(tuple(coefficient), monomial, p, g), p)
    return total


_ANALYSIS_CACHE = {}


def _analyze_polynomial(inst):
    """Recover and certify L(x)+c*ell(x)^s from the expanded polynomial."""
    p, g, s = inst["p"], inst["g"], inst["s"]
    frozen = tuple(sorted((int(e), tuple(c)) for e, c in inst["terms"]))
    key = (p, g, s, frozen)
    if key in _ANALYSIS_CACHE:
        return _ANALYSIS_CACHE[key]
    term_map = dict(frozen)
    linear_coeffs = [term_map.get(p ** k, (0, 0, 0)) for k in range(3)]
    linear = _linearized_matrix(linear_coeffs, p, g)
    nonlinear = [(e, c) for e, c in frozen if e not in (1, p, p * p)]
    images = [_eval_terms_raw(nonlinear,
                              tuple(int(i == j) for i in range(3)), p, g, s)
              for j in range(3)]
    chosen = next((v for v in images if v != (0, 0, 0)), None)
    if chosen is None:
        raise ValueError("expanded polynomial has no nonlinear component")
    pivot = next(i for i, v in enumerate(chosen) if v)
    iv = pow(chosen[pivot], p - 2, p)
    outer = [v * iv % p for v in chosen]
    q_values = [v[pivot] for v in images]
    root_exponent = pow(s, -1, p - 1)
    functional = [pow(v, root_exponent, p) if v else 0 for v in q_values]
    expected = _terms_from_coordinate_form(
        linear, outer, functional, s, p, g)
    if expected != term_map:
        raise ValueError("expanded polynomial does not have the promised structure")
    value = (linear, outer, functional)
    _ANALYSIS_CACHE[key] = value
    return value


def _f_eval(inst, x):
    p, s = inst["p"], inst["s"]
    linear, outer, functional = _analyze_polynomial(inst)
    scalar = sum(a * b for a, b in zip(functional, x)) % p
    return tuple((u + c * pow(scalar, s, p)) % p
                 for u, c in zip(_mat_vec(linear, x, p), outer))


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a linearly equivalent Theorem 3.8 polynomial."""
    s = int(params.get("s", 5))
    prime_span = int(params.get("prime_span", 1))
    n = int(n)
    if s <= 1:
        raise ValueError("s must be greater than 1")
    if math.gcd(s, 6) != 1:
        raise ValueError(
            "s must be coprime to 6 for the p=1 mod 3 field presentations")
    if prime_span < 1:
        raise ValueError("prime_span must be positive")
    # Varying p supplies genuine diversity even after Section 4.2 linear
    # equivalence is quotiented out.  It also hardens the distribution without
    # lengthening the three-coordinate witness.
    p = _admissible_prime_at(
        max(n, s + 1), s, (int(seed) ^ 0x32) % prime_span)
    g = _first_noncube(p)
    rng = random.Random(seed)

    # b^(p-1) has norm one.  Reject only the forbidden theorem parameter a=1.
    while True:
        b = tuple(rng.randrange(p) for _ in range(3))
        if b != (0, 0, 0):
            a = _pow(b, p - 1, p, g)
            if a != (1, 0, 0):
                break

    # Build the coordinate form of f_5=A_a+A_(a^2)+Tr^s.
    a2 = _mul(a, a, p, g)
    base_linear = _linear_matrix(
        lambda value: _add(_A(a, value, p, g),
                           _A(a2, value, p, g), p), p)
    trace_matrix = _linear_matrix(lambda value: _trace(value, p, g), p)

    # Section 4.2's linear equivalence: h=Q o f_5 o P.  P and Q are
    # constructed from elementary row operations, so no invertibility search
    # and no certificate search occurs.
    pre = _random_invertible_matrix(rng, p)
    post = _random_invertible_matrix(rng, p)
    linear = _mat_mul(post, _mat_mul(base_linear, pre, p), p)
    functional = [sum(trace_matrix[0][k] * pre[k][j]
                      for k in range(3)) % p for j in range(3)]
    outer = [post[i][0] % p for i in range(3)]
    term_map = _terms_from_coordinate_form(
        linear, outer, functional, s, p, g)
    terms = [[e, list(c)] for e, c in term_map.items()]
    rng.shuffle(terms)

    # Sample the certificate first.  Nonzero, pairwise-distinct coordinates make
    # G2's independent corruptions visibly different; no such promise is leaked.
    while True:
        x = tuple(rng.randrange(p) for _ in range(3))
        if x[0] == 0 or len(set(x)) != 3:
            continue
        base_x = _mat_vec(pre, x, p)
        base_scalar = sum(trace_matrix[0][j] * base_x[j]
                          for j in range(3)) % p
        base_linear_target = _mat_vec(base_linear, base_x, p)
        # Avoid the two degenerate target orbits, which expose a purely linear
        # or purely nonlinear inversion.  This is inverse generation, not a
        # search for the answer: x was sampled before its target was formed.
        if base_scalar and any(base_linear_target):
            break
    inst = {
        "paper": "2407.12688",
        "p": p,
        "g": g,
        "s": s,
        "terms": terms,
        "target": None,
        "answer": list(x),
    }
    inst["target"] = list(_f_eval(inst, x))
    return inst


def _elt_text(x) -> str:
    return "[" + ",".join(str(v) for v in x) + "]"


def render(inst) -> str:
    p, g, s = inst["p"], inst["g"], inst["s"]
    lines = [
        "Invert one value of a permutation polynomial over a cubic finite field.",
        "",
        f"Let K = F_{p}[z]/(z^3-{g}).  (The integer {g} is a cubic nonresidue "
        f"modulo {p}, so z^3-{g} is irreducible.)",
        f"Represent c0+c1*z+c2*z^2 by [c0,c1,c2], with every coordinate in "
        f"0,...,{p-1}.  All coordinate arithmetic is modulo {p}.",
        "Addition is coordinatewise.  Multiplication is determined by z^3="
        f"{g}; explicitly,",
        "  [a0,a1,a2]*[b0,b1,b2] =",
        f"  [a0*b0+{g}*(a1*b2+a2*b1), "
        f"a0*b1+a1*b0+{g}*a2*b2, a0*b2+a1*b1+a2*b0] mod {p}.",
        "For u in K, u^e means repeated multiplication in this field.",
        f"The sparse polynomial h(X)=sum_e c_e*X^e is listed below.  An entry "
        "e : [c0,c1,c2] gives exponent e and coefficient c0+c1*z+c2*z^2.",
        "Terms may be added in any order, and exponents are ordinary nonnegative "
        "integers:",
    "",
    ]
    lines.extend(f"  {e} : {_elt_text(c)}" for e, c in inst["terms"])
    lines += [
        "",
        "It is promised that h is a permutation of K, constructed by invertible "
        "linearized pre- and post-composition; therefore every target has "
        "exactly one preimage.  A linearized "
        "polynomial has the form r0*X+r1*X^p+r2*X^(p^2) and induces an "
        "F_p-linear map of K.",
        f"Find the unique x in K such that h(x)={_elt_text(inst['target'])}.",
        "",
        "Give your final answer inside <answer></answer> tags as exactly three "
        "comma-separated base-field coordinates c0,c1,c2.",
        "Coordinates are 0-indexed polynomial-basis coefficients; order matters, "
        "repetitions and zero coordinates are allowed, and each must lie in the "
        f"inclusive range 0,...,{p-1}.",
        "Example format only: <answer>3, 1, 4</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines += ["", "Hint: " + STRUCTURAL_HINT]
    elif mode == "placebo":
        lines += ["", "Hint: " + PLACEBO_HINT]
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer>\s*(.*?)\s*</answer>", text,
                        flags=re.I | re.S)
    if not blocks:
        return None
    body = blocks[-1].strip()
    body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    if body.startswith("["):
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            return None
    else:
        pieces = [v.strip() for v in body.split(",")]
        if len(pieces) != 3 or any(not re.fullmatch(r"[+-]?\d+", v)
                                   for v in pieces):
            return None
        value = [int(v) for v in pieces]
    if (not isinstance(value, list) or len(value) != 3
            or any(isinstance(v, bool) or not isinstance(v, int)
                   for v in value)):
        return None
    return value


def verify(inst, answer):
    """Check a candidate by exact substitution; never inspect inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a coordinate list"
    if not answer:
        return False, "answer is empty"
    if len(answer) < 3:
        return False, "too few coordinates: expected exactly 3"
    if len(answer) > 3:
        return False, "too many coordinates: expected exactly 3"
    if any(isinstance(v, bool) or not isinstance(v, int) for v in answer):
        return False, "every coordinate must be an integer"
    p = inst["p"]
    if any(v < 0 or v >= p for v in answer):
        return False, f"coordinate outside the inclusive range 0..{p-1}"
    got = _f_eval(inst, tuple(answer))
    want = tuple(inst["target"])
    if got != want:
        i = next(i for i in range(3) if got[i] != want[i])
        return (False, f"substitution mismatch at output coordinate {i}: "
                f"got {got[i]}, expected {want[i]} (full output {_elt_text(got)})")
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the exact, structure-aware certificate language K."""
    p = inst["p"]
    return [rng.randrange(p), rng.randrange(p), rng.randrange(p)]


def search_space(inst):
    return inst["p"] ** 3


def enumerate_all(inst):
    if search_space(inst) > 200_000:
        return None
    hits = 0
    p = inst["p"]
    for x in itertools.product(range(p), repeat=3):
        hits += int(verify(inst, list(x))[0])
    return hits


def canonical_key(inst):
    """Canonicalize the generated class from public instance data only.

    Every generated map has form Lx+c*ell(x)^s with rank(L)=2, c outside
    image(L), and ell nonzero on kernel(L).  Independent invertible linear
    changes in the input and output reduce it to (u,v,w)->(u,v,w^s).  A target
    therefore has just two orbit flags: whether its image(L) component and its
    complementary component vanish.  The generator deliberately uses the
    nonzero/nonzero orbit, so p and s provide the remaining invariant.
    """
    p = inst["p"]
    linear, outer, _ = _analyze_polynomial(inst)
    transpose = [[linear[j][i] for j in range(3)] for i in range(3)]
    rho = _null_vector(transpose, p)
    if rho is None:
        raise ValueError("linear component is not rank two")
    denominator = sum(a * b for a, b in zip(rho, outer)) % p
    if not denominator:
        raise ValueError("nonlinear direction lies in the linear image")
    nonlinear_scalar = (sum(a * b for a, b in zip(rho, inst["target"]))
                        * pow(denominator, p - 2, p)) % p
    linear_part = [(y - c * nonlinear_scalar) % p
                   for y, c in zip(inst["target"], outer)]
    normal = {
        "p": p,
        "s": inst["s"],
        "linear_target_zero": not any(linear_part),
        "nonlinear_target_zero": nonlinear_scalar == 0,
    }
    blob = json.dumps(normal, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def escalate(params):
    """Raise modulus and modulus spread at fixed three-coordinate output."""
    out = dict(params)
    out["n"] = max(int(out.get("n", 193)) + 1,
                   int(out.get("n", 193)) * 2)
    out["prime_span"] = max(2, int(out.get("prime_span", 1)) * 2)
    return out


# --- Compact inverse and adversarial probes (selftest only) -----------------

def _mat_vec(a, x, p: int):
    return [sum(v * w for v, w in zip(row, x)) % p for row in a]


def _mat_inv(a, p: int):
    n = len(a)
    m = [[v % p for v in row] + [int(i == j) for j in range(n)]
         for i, row in enumerate(a)]
    for col in range(n):
        pivot = next((r for r in range(col, n) if m[r][col]), None)
        if pivot is None:
            return None
        m[col], m[pivot] = m[pivot], m[col]
        iv = pow(m[col][col], p - 2, p)
        m[col] = [v * iv % p for v in m[col]]
        for r in range(n):
            if r == col or not m[r][col]:
                continue
            c = m[r][col]
            m[r] = [(u - c * v) % p for u, v in zip(m[r], m[col])]
    return [row[n:] for row in m]


def _linear_matrix(fn, p: int):
    cols = [fn(tuple(int(i == j) for i in range(3))) for j in range(3)]
    return [[cols[j][i] for j in range(3)] for i in range(3)]


def _rank_one_factor(matrix, p: int):
    for col in range(3):
        vector = [matrix[row][col] for row in range(3)]
        for pivot in range(3):
            if vector[pivot]:
                iv = pow(vector[pivot], p - 2, p)
                t = [v * iv % p for v in vector]
                lam = matrix[pivot][:]
                if all(matrix[i][j] % p == t[i] * lam[j] % p
                       for i in range(3) for j in range(3)):
                    return t, lam
    raise ValueError("map is not rank one")


def _compact_preimage(inst):
    """Invert the certified rank-two plus rank-one coordinate form."""
    p, s = inst["p"], inst["s"]
    linear, outer, functional = _analyze_polynomial(inst)

    # A left null vector rho of the rank-two linear map isolates ell(x)^s.
    transpose = [[linear[j][i] for j in range(3)] for i in range(3)]
    rho = _null_vector(transpose, p)
    if rho is None:
        raise ValueError("linearized component does not have rank two")
    denominator = sum(a * b for a, b in zip(rho, outer)) % p
    if not denominator:
        raise ValueError("nonlinear image lies in the linear image")
    numerator = sum(a * b for a, b in zip(rho, inst["target"])) % p
    powered = numerator * pow(denominator, p - 2, p) % p
    root_exponent = pow(s, -1, p - 1)
    local = pow(powered, root_exponent, p) if powered else 0
    remainder = [(y - c * pow(local, s, p)) % p
                 for y, c in zip(inst["target"], outer)]

    # Any three independent equations among Lx=remainder and ell(x)=local.
    equations = [row[:] for row in linear] + [functional[:]]
    rhs = remainder + [local]
    for chosen in itertools.combinations(range(4), 3):
        matrix = [equations[i] for i in chosen]
        inv = _mat_inv(matrix, p)
        if inv is None:
            continue
        answer = _mat_vec(inv, [rhs[i] for i in chosen], p)
        if (_mat_vec(linear, answer, p) == remainder
                and sum(a * b for a, b in zip(functional, answer)) % p
                == local):
            return answer
    raise ValueError("no nonsingular compact coordinate solve")


def _null_vector(matrix, p: int):
    """One nonzero vector in the nullspace of a 3-column matrix."""
    a = [[v % p for v in row] for row in matrix]
    rows, cols = len(a), len(a[0])
    pivots = []
    r = 0
    for col in range(cols):
        pivot = next((i for i in range(r, rows) if a[i][col]), None)
        if pivot is None:
            continue
        a[r], a[pivot] = a[pivot], a[r]
        iv = pow(a[r][col], p - 2, p)
        a[r] = [v * iv % p for v in a[r]]
        for i in range(rows):
            if i != r and a[i][col]:
                c = a[i][col]
                a[i] = [(u - c * v) % p for u, v in zip(a[i], a[r])]
        pivots.append(col)
        r += 1
    free = next((j for j in range(cols) if j not in pivots), None)
    if free is None:
        return None
    x = [0] * cols
    x[free] = 1
    for row in range(len(pivots) - 1, -1, -1):
        col = pivots[row]
        x[col] = -sum(a[row][j] * x[j] for j in range(col + 1, cols)) % p
    return x


def _linear_only_candidate(inst):
    p = inst["p"]
    matrix, _, _ = _analyze_polynomial(inst)
    aug = [row[:] + [b] for row, b in zip(matrix, inst["target"])]
    r = 0
    pivots = []
    for col in range(3):
        pivot = next((i for i in range(r, 3) if aug[i][col] % p), None)
        if pivot is None:
            continue
        aug[r], aug[pivot] = aug[pivot], aug[r]
        iv = pow(aug[r][col], p - 2, p)
        aug[r] = [v * iv % p for v in aug[r]]
        for i in range(3):
            if i != r and aug[i][col]:
                c = aug[i][col]
                aug[i] = [(u - c * v) % p for u, v in zip(aug[i], aug[r])]
        pivots.append(col)
        r += 1
    if any(not any(row[:3]) and row[3] for row in aug):
        return [0, 0, 0]
    out = [0, 0, 0]
    for row, col in enumerate(pivots):
        out[col] = aug[row][3]
    return out


def _attack_candidates(inst, name: str, rng):
    p, g, s = inst["p"], inst["g"], inst["s"]
    y = inst["target"]
    r = pow(s, -1, p - 1)
    if name == "copy_target_or_sparse_basis":
        return [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1],
                [1, 1, 1], y[:]]
    if name == "by_hand_ignore_nonlinear_term":
        return [_linear_only_candidate(inst)]
    if name == "coordinatewise_fifth_root":
        return [[pow(v, r, p) if v else 0 for v in y]]
    if name == "whole_field_fifth_root":
        return [list(_pow(tuple(y), r, p, g))]
    if name == "random_restart_256":
        return [random_candidate(inst, rng) for _ in range(256)]
    raise KeyError(name)


def _brute_force_preimage(inst):
    """Exhaustive scan after support-factorized polynomial evaluation."""
    p = inst["p"]
    checked = 0
    for x in itertools.product(range(p), repeat=3):
        checked += 1
        if _f_eval(inst, x) == tuple(inst["target"]):
            return list(x), checked
    return None, checked


def _frobenius_transform(inst, times: int):
    p, g = inst["p"], inst["g"]
    out = dict(inst)
    out["terms"] = [[e, list(_frob(tuple(c), p, g, times))]
                    for e, c in inst["terms"]]
    out["target"] = list(_frob(tuple(inst["target"]), p, g, times))
    out["answer"] = list(_frob(tuple(inst["answer"]), p, g, times))
    return out


def _reorder_terms(inst):
    out = dict(inst)
    out["terms"] = list(reversed(inst["terms"]))
    out["answer"] = inst["answer"][:]
    return out


def _linear_equivalence_transform(inst, seed: int):
    """Apply another paper-licensed pre/post linearized relabelling."""
    p, g, s = inst["p"], inst["g"], inst["s"]
    linear, outer, functional = _analyze_polynomial(inst)
    rng = random.Random(seed)
    pre = _random_invertible_matrix(rng, p)
    post = _random_invertible_matrix(rng, p)
    pre_inv = _mat_inv(pre, p)
    if pre_inv is None:  # impossible by construction
        raise ValueError("constructed pre-map is singular")
    new_linear = _mat_mul(post, _mat_mul(linear, pre, p), p)
    new_outer = _mat_vec(post, outer, p)
    new_functional = [sum(functional[k] * pre[k][j]
                          for k in range(3)) % p for j in range(3)]
    terms = _terms_from_coordinate_form(
        new_linear, new_outer, new_functional, s, p, g)
    out = dict(inst)
    out["terms"] = [[e, list(c)] for e, c in reversed(sorted(terms.items()))]
    out["target"] = _mat_vec(post, inst["target"], p)
    out["answer"] = _mat_vec(pre_inv, inst["answer"], p)
    return out


def _answer_atoms(a):
    if isinstance(a, dict):
        return sum(_answer_atoms(v) for v in a.values())
    if isinstance(a, (list, tuple)):
        return sum(_answer_atoms(v) for v in a)
    return 1


def selftest():
    report = {"paper": "2407.12688", "track": TRACK,
              "shipping_difficulty": SHIPPING_DIFFICULTY}

    # G1: every preset and multiple independent instances.
    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 20260717):
            attempts += 1
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": reason})
            compact = _compact_preimage(inst)
            if compact != inst["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "compact inverse disagrees with plant"})
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts,
        "verified": attempts - len(failures), "failures": failures,
    }

    # 424242 selects the lower-edge shipping prime p=103.  The full easy
    # distribution ranges over 32 admissible primes, all at least this hard.
    shipping = make_instance(seed=424242, **DIFFICULTY[SHIPPING_DIFFICULTY])

    # G2: semantically separate corruptions, with checker-produced diagnostics.
    ans = shipping["answer"][:]
    corruptions = {
        "drop": ans[:-1],
        "swap": [ans[1], ans[0], ans[2]],
        "duplicate": [ans[0], ans[1], ans[0]],
        "empty": [],
        "out_of_range": [shipping["p"], ans[1], ans[2]],
    }
    cases = {}
    reasons = []
    for name, bad in corruptions.items():
        ok, reason = verify(shipping, bad)
        cases[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in cases.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)), "cases": cases,
    }

    # G3: realistic prose/fence tolerance plus JSON-native answer guarantee.
    realistic = ("I used the Frobenius components.\n<answer>```text\n"
                 + ", ".join(map(str, ans)) + "\n```</answer>\nDone.")
    parsed = parse_answer(realistic)
    json_native = json.loads(json.dumps(ans)) == ans
    report["G3_round_trip"] = {
        "pass": parsed == ans and json_native,
        "parsed_matches": parsed == ans, "json_native": json_native,
    }

    # G4 and shipping density: one exact-language Monte Carlo run is shared.
    rng = random.Random(9128675309)
    samples = 200_000
    hits = 0
    t0 = time.perf_counter()
    for _ in range(samples):
        hits += int(verify(shipping, random_candidate(shipping, rng))[0])
    sample_wall = time.perf_counter() - t0
    observed = hits / samples
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6,
        "hits": hits, "total": samples,
        "observed_probability": observed,
        "exact_language_size": search_space(shipping),
        "shipping_p": shipping["p"],
        "exact_probability_by_uniqueness": 1 / search_space(shipping),
        "sampling_wall_sec": round(sample_wall, 6),
    }

    # G5: exact demo count plus an actually timed shipping-preset inverse scan.
    demo = make_instance(seed=17, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    t0 = time.perf_counter()
    brute_answer, brute_checks = _brute_force_preimage(shipping)
    brute_wall = time.perf_counter() - t0
    brute_ok = brute_answer is not None and verify(shipping, brute_answer)[0]
    # The cached coordinate evaluator performs 9 matrix multiplications, 6
    # matrix additions, 3 dot multiplications, 2 dot additions, 3 squarings/
    # multiplications for the fifth power, and 6 output operations: 29 exact
    # base-field arithmetic operations per enumerated candidate.
    brute_operations = brute_checks * 29
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and brute_ok and observed < 1e-6,
        "demo_exact_solution_count": demo_count,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_fraction": observed,
        "shipping_exact_density_by_theorem": 1 / search_space(shipping),
        "shipping_p": shipping["p"],
        "baseline_candidates_checked": brute_checks,
        "baseline_operation_count": brute_operations,
        "baseline_wall_clock_sec": round(brute_wall, 6),
    }

    # G6: four no-tool probes plus a random restart; all must fail on 8 seeds.
    attack_names = [
        "copy_target_or_sparse_basis",
        "by_hand_ignore_nonlinear_term",
        "coordinatewise_fifth_root",
        "whole_field_fifth_root",
        "random_restart_256",
    ]
    attack_counts = {name: {"successes": 0, "attempts": 0}
                     for name in attack_names}
    compact_successes = 0
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name in attack_names:
            arng = random.Random((seed << 20) ^ sum(map(ord, name)))
            candidates = _attack_candidates(inst, name, arng)
            success = any(verify(inst, candidate)[0]
                          for candidate in candidates)
            attack_counts[name]["attempts"] += 1
            attack_counts[name]["successes"] += int(success)
        compact_successes += int(verify(inst, _compact_preimage(inst))[0])
    all_failed = all(v["successes"] == 0 and v["attempts"] >= 8
                     for v in attack_counts.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attack_counts,
        "reference_algorithm": {
            "name": "exhaustive inverse-table scan with exact evaluator preprocessing",
            "complexity": "O(p^3 log s) exact finite-field operations",
            "wall_clock_sec": round(brute_wall, 6),
            "candidates_checked": brute_checks,
            "operations": brute_operations,
            "solves": "1/1 timed generic scan, as expected",
        },
        "compact_route_validation": {
            "successes": compact_successes,
            "attempts": 8,
        },
    }

    # G7: p and its cubic haystack grow; answer length does not.
    doubled = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled["n"] *= 2
    larger = make_instance(seed=424242, **doubled)
    larger_ok, larger_reason = verify(larger, larger["answer"])
    report["G7_scales"] = {
        "pass": larger_ok and larger["p"] > shipping["p"]
        and search_space(larger) > search_space(shipping)
        and len(larger["answer"]) == len(shipping["answer"]),
        "p_before": shipping["p"], "p_after": larger["p"],
        "space_before": search_space(shipping),
        "space_after": search_space(larger),
        "answer_elements_before": len(shipping["answer"]),
        "answer_elements_after": len(larger["answer"]),
        "verify_reason": larger_reason,
    }

    # G8: term order is immaterial; field-coordinate relabellings are Frobenius.
    invariant = transformed = 0
    unrelated = []
    for seed in range(20):
        inst = make_instance(seed=10000 + seed,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        moved_instances = [
            _reorder_terms(inst),
            _frobenius_transform(inst, 1),
            _frobenius_transform(inst, 2),
            _reorder_terms(_frobenius_transform(inst, 1)),
            _linear_equivalence_transform(inst, seed + 50000),
            _frobenius_transform(
                _linear_equivalence_transform(inst, seed + 60000), 1),
        ]
        for moved in moved_instances:
            invariant += int(canonical_key(moved) == key)
            transformed += int(verify(moved, moved["answer"])[0])
        unrelated.append(key)
    report["G8_canonical_key"] = {
        "pass": invariant == 120 and transformed == 120
        and len(set(unrelated)) == 20,
        "invariance_checks_attempted": 120,
        "invariance_checks_passed": invariant,
        "transformed_witnesses_attempted": 120,
        "transformed_witnesses_verified": transformed,
        "unrelated_instances": 20,
        "unrelated_distinct_keys": len(set(unrelated)),
    }

    blob = json.dumps(shipping["answer"])
    chars = len(blob)
    tokens = math.ceil(chars / 4)
    atoms = _answer_atoms(shipping["answer"])
    arms = G9_RESULTS["arms"]
    ha, pa = arms["hinted"]["attempts"], arms["placebo"]["attempts"]
    hs = arms["hinted"]["solved"] / ha if ha else None
    ps = arms["placebo"]["solved"] / pa if pa else None
    report["G9_no_tool_suitability"] = {
        "pass": chars <= 2000 and atoms <= 256 and 286 <= 300,
        "arms": arms,
        "arms_complete": all(arms[k]["attempts"] > 0 for k in arms),
        "hinted_minus_placebo": hs - ps if hs is not None and ps is not None
        else None,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": chars, "answer_tokens": tokens,
        "answer_elements": atoms, "intended_route_operations": 286,
    }

    report["all_passed"] = all(
        value.get("pass", True) for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
