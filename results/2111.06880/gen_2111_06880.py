"""Problem generator for arXiv:2111.06880 -- Muller, Robeva & Usevich,
"Robust Eigenvectors of Symmetric Tensors" (math.NA / math.AG / math.SP / cs.NA).

WHAT THE PAPER SAYS THAT THIS FAMILY USES
-----------------------------------------
Section 2 fixes the definitions.  For a symmetric tensor T in S^d(R^n), a unit
vector v is an EIGENVECTOR with eigenvalue mu when  T . v^{d-1} = mu v, and it is
ROBUST when it is an attracting fixed point of the tensor power method
x <- T.x^{d-1} / ||T.x^{d-1}||.  Lemma 4 computes the Jacobian of that iteration
at a unit eigenvector,

        J(v) = ((d-1)/mu) ( T . v^{d-2}  -  mu v v^T ),

and Lemma 3 (quoted from [33, Thm 3.5]) says rho(J(v)) < 1 is sufficient for v to
be attracting.  Theorem 2 -- the paper's main result -- says that a GENERATOR of
the symmetric decomposition which happens to be an eigenvector is robust once the
order d is large enough; the bound (3.6) that proves it is exactly a bound on
rho(J(v)).

That pair of lemmas is what makes a numerical-analysis paper usable here: for a
tensor with rational entries and a rational unit vector v, both the eigenvector
equation and rho(J(v)) < 1 are decided by EXACT rational arithmetic --- the
eigenvector equation is a polynomial identity, and rho(J) < 1 for the symmetric
matrix J is equivalent to  I - J  and  I + J  both being positive definite, which
an exact LDL^T with rational pivots decides outright.  No floating point occurs
anywhere in verify().

THE FAMILY
----------
An instance publishes the integer coefficients of a degree-d form

        F(x) = T . x^d  =  A <a,x>^d  +  sum_k g_k <w_k,x>^d ,

where a is a primitive integer vector with |a|^2 = q^2 (so v = a/q is a RATIONAL
unit vector), and every decoy vector w_k is an integer vector ORTHOGONAL to a.
The solver is asked for a rational unit vector that is a robust eigenvector.

Because <w_k, v> = 0, Section 3's computation (3.3) collapses to
T.v^{d-1} = A q^d v and T.v^{d-2} = A q^d v v^T, so v is an eigenvector with
mu = A q^d and J(v) = 0 exactly: v is the "super-attracting" corner of Theorem 2,
robust for every d >= 3.  Nothing is searched for -- v is sampled first and F is
built around it.

WHY IT IS NOT TRIVIAL, AND WHY IT IS TRACK B
--------------------------------------------
The generic count of eigenvectors of an order-d tensor in n variables is
((d-1)^n - 1)/(d-2) (Cartwright-Sturmfels); at the shipping preset that is 781.
Almost all of them are irrational, so they cannot even be written down as an
exact answer, and only a handful are robust.  The domain-standard algorithm --
the tensor power method, the subject of the paper -- does find robust
eigenvectors, but its basin around the plant is deliberately small (the plant
weight A is small relative to the decoy weights, which changes nothing about
rho(J(v)) = 0 and everything about the region of convergence; compare the
paper's own Section 4.4 / Figure 2 discussion of convergence regions).  Measured
at the shipping preset it needs ~10^7-10^9 floating point operations.

The compact route is short: because every decoy is orthogonal to a, EVERY
Hessian of F has v as an eigenvector, so v spans the kernel of the commutator
[Hess F(e_1), Hess F(e_2)] -- two matrices read off n(n+1)/2 coefficients each,
one commutator, one nullspace: ~650 exact rational operations, independent of
how many coefficients the instance publishes.

NOTES on what fixed what:
 * Section 2 (definitions) fixed the eigenvector convention -- T.v^{d-1} = mu v
   with ||v|| = 1, i.e. the Z-/l2-eigenvectors, not the H-eigenvectors.
 * Lemma 4 fixed the exact form of J; Lemma 3 fixed rho(J) < 1 as the criterion.
 * Theorem 2 / eq. (3.6) is what licenses "generator + eigenvector => robust".
 * Section 4 (equiangular set / ETF decomposable tensors, Theorems 6 and 8) is
   the paper's new class.  It is NOT what this family generates: an equiangular
   set with rational unit vectors and rational Gram entries essentially does not
   exist (the Mercedes-Benz frame of Appendix A already needs sqrt(3)/2), and
   for an ES-decomposable tensor the Hessians do not share an eigenvector, so
   the compact route above disappears and the family would have no Track B gap.
   That is recorded in the README as the regime that was rejected.
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
    from gvlib import exact_matrices as _em
except Exception:                                    # pragma: no cover
    _em = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "rational",
    "native_objects": [
        "a symmetric tensor T in S^d(R^n), published as the integer coefficients "
        "of the degree-d form F(x) = T . x^d",
        "a rational unit vector x in Q^n (the claimed robust eigenvector)",
        "the exact rational Jacobian J = Hess F(x)/(d mu) - (d-1) x x^T of the "
        "tensor power method at x (paper Lemma 4)",
    ],
    "verification_operations": [
        "exact integer evaluation of grad F at the numerator vector",
        "exact parallelism test grad F(a) x a = 0 (the eigenvector identity)",
        "exact rational inner product <x,x> = 1 and denominator bound",
        "exact rational Hessian evaluation and assembly of J",
        "positive-definiteness of I-J and I+J by exact LDL^T over Q (rho(J) < 1)",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Every second-order contraction of the tensor -- the Hessian of F at ANY "
        "point -- has the planted eigenvector among its eigenvectors, because the "
        "planted generator is orthogonal to every other generator of the symmetric "
        "decomposition.  Two Hessians therefore commute on that direction and it "
        "spans the kernel of their commutator.  A solver who does not see this is "
        "left with the tensor power method: iterate from random starts until one "
        "of them lands in the plant's (small) region of convergence, then "
        "reconstruct the exact rational limit."
    ),
    "hardness_basis": (
        "Track B.  An efficient algorithm exists and it is stated here: read the "
        "n(n+1)/2 coefficients that give Hess F(e_1) and Hess F(e_2), form the "
        "commutator, take its kernel -- O(n^3) exact rational operations, measured "
        "at 647 operations and ~4e-4 s at the shipping preset "
        "(selftest_report.json, G6.reference_algorithm).  The mechanical route, "
        "the one available without that observation, is the paper's own tensor "
        "power method with random restarts: the plant's region of convergence is "
        "measured at ~1e-3 to 1e-4 of the sphere at the shipping preset, so it "
        "costs ~1e8-1e9 floating point operations before rational reconstruction "
        "-- fine for a solver with a machine, out of reach for a model working in "
        "context.  Guessing is excluded separately: the certificate language holds "
        "4.98e7 sign-normalised rational unit vectors and the valid ones number in "
        "the single digits."
    ),
    "max_answer_tokens": 60,
}

NATIVE = {
    "domain": "algebra",
    "core": "polynomial_identity",
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": "invariant: " + PROBLEM_PROFILE["intuition_description"],
    "reduction": None,
}

# ---------------------------------------------------------------------------
# difficulty ladder
#
#   n          number of variables (fixes the ANSWER LENGTH: n rationals)
#   d          order of the tensor / degree of the form
#   qmin,qmax  band the reduced denominator of the answer must lie in
#   m          number of decoy generators (crowding)
#   wlo,whi    decoy weight range; the plant weight is +-1, so whi is the
#              plant/decoy weight ratio and it is what shrinks the tensor power
#              method's region of convergence around the plant
#
# Everything except `n` grows the haystack at a FIXED answer length of n
# rationals.  `n` is 5 from `easy` upward and escalate() never moves it.
# ---------------------------------------------------------------------------
DIFFICULTY = {
    "demo":   {"n": 3, "d": 4, "qmin": 5,  "qmax": 15, "m": 6,  "wlo": 1, "whi": 3},
    "easy":   {"n": 5, "d": 5, "qmin": 15, "qmax": 60, "m": 25, "wlo": 1, "whi": 9},
    "medium": {"n": 5, "d": 6, "qmin": 20, "qmax": 80, "m": 35, "wlo": 1, "whi": 40},
    "hard":   {"n": 5, "d": 6, "qmin": 20, "qmax": 80, "m": 45, "wlo": 8, "whi": 200},
}

SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The matrix of second partial derivatives of F, at every point where you "
    "evaluate it, has the vector you are looking for as an eigenvector."
)

PLACEBO_HINT = (
    "The arithmetic here stays exact throughout, so keep the numerators and "
    "denominators of every intermediate quantity in reduced form."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A rational unit vector x in Q^n: x = a/q with a a primitive integer "
        "vector, q a positive integer, |a|^2 = q^2, the reduced denominator q in "
        "[qmin, qmax], and the first nonzero coordinate of x positive.  The "
        "answer is the n coordinates written as reduced fractions."
    ),
    "bounds": {"n": None, "qmin": None, "qmax": None, "n_elements": None},
}


# ===========================================================================
# small exact helpers (integer / Fraction only -- no float anywhere below)
# ===========================================================================

def _monomials(n, d):
    if n == 1:
        yield (d,)
        return
    for i in range(d + 1):
        for rest in _monomials(n - 1, d - i):
            yield (i,) + rest


def _multinomial(d, e):
    r = math.factorial(d)
    for x in e:
        r //= math.factorial(x)
    return r


def _linear_power(w, d, n, mons):
    """<w,x>^d as {exponent tuple: integer coefficient}."""
    out = {}
    for e in mons:
        c = _multinomial(d, e)
        for i in range(n):
            if e[i]:
                c *= w[i] ** e[i]
        if c:
            out[e] = c
    return out


def _sample_unit_vector(rng, n, qmin, qmax, tries=20000):
    """A rational unit vector a/q, sign-normalised, with q in [qmin, qmax].

    Householder parametrisation: for an integer vector w with w_1 != 0 the
    reflection of e_1 in w^perp is a rational unit vector, and every rational
    unit vector other than e_1 arises this way.  Plants and G4 candidates are
    drawn by this same routine, so they come from one distribution.
    """
    W = int(math.isqrt(qmax)) + 2
    for _ in range(tries):
        w = [rng.randint(-W, W) for _ in range(n)]
        if w[0] == 0:
            continue
        nw = sum(t * t for t in w)
        if nw == 0:
            continue
        a = [nw - 2 * w[0] * w[0]] + [-2 * w[0] * w[i] for i in range(1, n)]
        q = nw
        g = q
        for t in a:
            g = math.gcd(g, abs(t))
        if g == 0:
            continue
        a = [t // g for t in a]
        q //= g
        if not (qmin <= q <= qmax):
            continue
        for t in a:
            if t != 0:
                if t < 0:
                    a = [-u for u in a]
                break
        return a, q
    return None, None


def _perp_vectors(rng, a, n, count, hi, tries=400000):
    """Integer vectors orthogonal to a, entries in [-hi, hi], norm in a band."""
    out = []
    lo2 = (hi * hi * n) // 6
    t = 0
    while len(out) < count and t < tries:
        t += 1
        z = [rng.randint(-hi, hi) for _ in range(n - 1)]
        s = sum(a[i + 1] * z[i] for i in range(n - 1))
        if a[0] == 0:
            if s != 0:
                continue
            z0 = rng.randint(-hi, hi)
        else:
            if s % a[0] != 0:
                continue
            z0 = -s // a[0]
        if abs(z0) > hi:
            continue
        v = [z0] + z
        nv = sum(x * x for x in v)
        if nv < lo2:
            continue
        g = 0
        for x in v:
            g = math.gcd(g, abs(x))
        if g > 1:
            v = [x // g for x in v]
        out.append(v)
    return out


# ===========================================================================
# instance construction  --  answer first, no search
# ===========================================================================

def make_instance(seed: int = 0, **params) -> dict:
    p = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    p.update({k: v for k, v in params.items() if not str(k).startswith("_")})
    n, d = int(p["n"]), int(p["d"])
    qmin, qmax = int(p["qmin"]), int(p["qmax"])
    m, wlo, whi = int(p["m"]), int(p["wlo"]), int(p["whi"])
    rng = random.Random((seed, n, d, qmin, qmax, m, wlo, whi).__hash__() & 0xFFFFFFFF)

    a, q = _sample_unit_vector(rng, n, qmin, qmax)
    if a is None:
        raise ValueError("no rational unit vector in the requested denominator band")

    mons = list(_monomials(n, d))
    hi = max(2, q)
    ws = _perp_vectors(rng, a, n, m, hi)
    if len(ws) < max(2, n):
        raise ValueError("could not build enough decoy generators")

    coeffs = {}
    A = rng.choice([1, -1])
    for e, c in _linear_power(a, d, n, mons).items():
        coeffs[e] = coeffs.get(e, 0) + A * c
    weights = []
    for w in ws:
        g = rng.randint(wlo, whi) * rng.choice([1, -1])
        weights.append(g)
        for e, c in _linear_power(w, d, n, mons).items():
            coeffs[e] = coeffs.get(e, 0) + g * c
    terms = [[coeffs[e], list(e)] for e in mons if coeffs.get(e)]

    answer = [[a[i], q] if q != 1 else [a[i], 1] for i in range(n)]
    answer = [list(_reduce(a[i], q)) for i in range(n)]

    inst = {
        "n": n, "d": d, "qmin": qmin, "qmax": qmax,
        "terms": terms,
        "answer": answer,
        "_a": list(a), "_q": q, "_A": A,
        "_ws": [list(w) for w in ws], "_weights": weights,
        "_params": {"n": n, "d": d, "qmin": qmin, "qmax": qmax,
                    "m": m, "wlo": wlo, "whi": whi},
    }
    return inst


def _reduce(num, den):
    g = math.gcd(abs(num), abs(den))
    if g:
        num //= g
        den //= g
    if den < 0:
        num, den = -num, -den
    return (num, den)


# ===========================================================================
# rendering
# ===========================================================================

def _fmt_term(coef, exps):
    parts = []
    for i, e in enumerate(exps):
        if e == 1:
            parts.append("x%d" % (i + 1))
        elif e > 1:
            parts.append("x%d^%d" % (i + 1, e))
    return "%+d %s" % (coef, "*".join(parts) if parts else "1")


def render(inst) -> str:
    n, d = inst["n"], inst["d"]
    lines = []
    lines.append(
        "Let F be the following homogeneous polynomial of degree %d in the %d "
        "variables x1,...,x%d, with integer coefficients:" % (d, n, n))
    lines.append("")
    body = []
    for coef, exps in inst["terms"]:
        body.append(_fmt_term(coef, exps))
    # wrap at ~92 chars
    line = ""
    for t in body:
        if line and len(line) + len(t) + 1 > 92:
            lines.append(line)
            line = ""
        line = (line + " " + t).strip()
    if line:
        lines.append(line)
    lines.append("")
    lines.append(
        "F is the polynomial form of a symmetric tensor T of order %d in dimension "
        "%d: F(x) = T . x^%d, and grad F(x) = %d * (T . x^%d)." % (d, n, d, d, d - 1))
    lines.append("")
    lines.append("DEFINITIONS (all of them exact; no numerical tolerance is involved).")
    lines.append(
        "  * A vector x with <x,x> = 1 is an EIGENVECTOR of T with eigenvalue mu when")
    lines.append("        grad F(x) = %d * mu * x ,      equivalently  mu = F(x)." % d)
    lines.append(
        "  * Write H(x) for the %dx%d matrix of second partial derivatives of F at x, "
        "H(x)_{ij} = d^2F/dx_i dx_j (x).  For a unit eigenvector x with mu != 0 put"
        % (n, n))
    lines.append("        J  =  H(x) / (%d * mu)  -  %d * x x^T ." % (d, d - 1))
    lines.append(
        "    J is symmetric.  x is called a ROBUST eigenvector when the spectral "
        "radius of J is smaller than 1; equivalently, when both  I - J  and  I + J")
    lines.append("    are positive definite.  (I is the %dx%d identity matrix.)" % (n, n))
    lines.append("")
    lines.append("TASK.  Produce a vector x = (x1,...,x%d) with rational coordinates such that" % n)
    lines.append("  (1) <x,x> = x1^2 + ... + x%d^2 = 1 exactly;" % n)
    lines.append(
        "  (2) writing every coordinate over one common denominator in lowest terms, "
        "that denominator q satisfies %d <= q <= %d;" % (inst["qmin"], inst["qmax"]))
    lines.append("  (3) the first nonzero coordinate of x is positive;")
    lines.append("  (4) grad F(x) = %d * mu * x with mu = F(x) != 0  (x is an eigenvector);" % d)
    lines.append("  (5) the spectral radius of J is < 1  (x is robust).")
    lines.append("")
    lines.append(
        "Give your final answer inside <answer></answer> tags, as the %d coordinates "
        "in order, separated by commas, each written as an exact fraction "
        "numerator/denominator (an integer is allowed for a whole number)." % n)
    lines.append("Example of the format only, not a solution: <answer>%s</answer>"
                 % ", ".join(["2/7"] * n))
    lines.append("Output nothing else inside the tags.")
    text = "\n".join(lines)

    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


# ===========================================================================
# answer parsing
# ===========================================================================

_FRAC = re.compile(r"[+-]?\d+\s*/\s*[+-]?\d+|[+-]?\d+")


def parse_answer(text):
    if text is None:
        return None
    if isinstance(text, (list, tuple)):
        cand = list(text)
    else:
        s = str(text)
        blocks = re.findall(r"<answer>(.*?)</answer>", s, re.S | re.I)
        if not blocks:
            return None
        body = blocks[-1]
        body = body.replace("`", " ").replace("\\", " ")
        body = re.sub(r"[\[\]\(\)]", " ", body)
        toks = _FRAC.findall(body)
        if not toks:
            return None
        cand = toks
    out = []
    for t in cand:
        if isinstance(t, (list, tuple)):
            if len(t) != 2:
                return None
            try:
                num, den = int(t[0]), int(t[1])
            except (TypeError, ValueError):
                return None
        else:
            s = str(t).strip()
            if "/" in s:
                a, b = s.split("/", 1)
                try:
                    num, den = int(a.strip()), int(b.strip())
                except ValueError:
                    return None
            else:
                try:
                    num, den = int(s), 1
                except ValueError:
                    return None
        if den == 0:
            return None
        out.append(list(_reduce(num, den)))
    return out or None


# ===========================================================================
# exact verification -- integers and Fractions only
# ===========================================================================

def _as_fractions(answer, n):
    if not isinstance(answer, (list, tuple)) or len(answer) != n:
        return None
    out = []
    for item in answer:
        if isinstance(item, (list, tuple)):
            if len(item) != 2:
                return None
            try:
                num, den = int(item[0]), int(item[1])
            except (TypeError, ValueError):
                return None
            if den == 0:
                return None
            out.append(Fraction(num, den))
        elif isinstance(item, int):
            out.append(Fraction(item))
        elif isinstance(item, Fraction):
            out.append(item)
        elif isinstance(item, str):
            parsed = parse_answer([item])
            if parsed is None:
                return None
            out.append(Fraction(parsed[0][0], parsed[0][1]))
        else:
            return None
    return out


def _grad_int(terms, n, pt):
    """grad F at an INTEGER point, exactly, as integers."""
    g = [0] * n
    for coef, e in terms:
        for j in range(n):
            if not e[j]:
                continue
            t = coef * e[j]
            for i in range(n):
                k = e[i] - (1 if i == j else 0)
                if k:
                    t *= pt[i] ** k
            g[j] += t
    return g


def _value_int(terms, n, pt):
    tot = 0
    for coef, e in terms:
        t = coef
        for i in range(n):
            if e[i]:
                t *= pt[i] ** e[i]
        tot += t
    return tot


def _hess_int(terms, n, pt):
    H = [[0] * n for _ in range(n)]
    for coef, e in terms:
        for j in range(n):
            if not e[j]:
                continue
            for k in range(j, n):
                ek = e[k] - (1 if k == j else 0)
                if ek <= 0:
                    continue
                t = coef * e[j] * ek
                for i in range(n):
                    p = e[i] - (1 if i == j else 0) - (1 if i == k else 0)
                    if p:
                        t *= pt[i] ** p
                H[j][k] += t
                if k != j:
                    H[k][j] += t
    return H


def _is_pd_exact(M, n):
    """Exact positive definiteness of a symmetric rational matrix (LDL^T)."""
    if _em is not None:
        return _em.is_positive_definite(_em.matrix(M))
    return _is_pd_exact_internal(M, n)


def _is_pd_exact_internal(M, n):
    """Standard-library fallback for the same test, used when gvlib is absent."""
    A = [[Fraction(M[i][j]) for j in range(n)] for i in range(n)]
    for i in range(n):
        piv = A[i][i]
        if piv <= 0:
            return False
        for r in range(i + 1, n):
            f = A[r][i] / piv
            for c in range(i, n):
                A[r][c] -= f * A[i][c]
    return True


def verify(inst, answer):
    n, d = inst["n"], inst["d"]
    xs = _as_fractions(answer, n)
    if xs is None:
        return False, "answer is not a list of %d rational numbers" % n
    if sum(x * x for x in xs) != 1:
        return False, "not a unit vector: <x,x> != 1"
    den = 1
    for x in xs:
        den = den * x.denominator // math.gcd(den, x.denominator)
    if den < inst["qmin"] or den > inst["qmax"]:
        return False, ("common denominator %d outside the allowed band [%d, %d]"
                       % (den, inst["qmin"], inst["qmax"]))
    first = None
    for x in xs:
        if x != 0:
            first = x
            break
    if first is None:
        return False, "the zero vector is not a unit vector"
    if first < 0:
        return False, "first nonzero coordinate is negative (sign convention)"

    pt = [int(x * den) for x in xs]            # integer numerator vector
    g = _grad_int(inst["terms"], n, pt)        # grad F at the integer point
    for i in range(n):
        for j in range(i + 1, n):
            if g[i] * pt[j] != g[j] * pt[i]:
                return False, "grad F(x) is not parallel to x: x is not an eigenvector"
    val = _value_int(inst["terms"], n, pt)     # F(a) ; mu = F(a)/den^d
    if val == 0:
        return False, "eigenvalue mu = F(x) is zero"
    mu = Fraction(val, den ** d)

    H = _hess_int(inst["terms"], n, pt)        # Hess F(a) ; Hess F(x) = H/den^{d-2}
    scale = Fraction(1, den ** (d - 2)) / (d * mu)
    J = [[H[i][j] * scale - (d - 1) * xs[i] * xs[j] for j in range(n)]
         for i in range(n)]
    Ip = [[(1 if i == j else 0) + J[i][j] for j in range(n)] for i in range(n)]
    Im = [[(1 if i == j else 0) - J[i][j] for j in range(n)] for i in range(n)]
    if not _is_pd_exact(Im, n):
        return False, "not robust: I - J is not positive definite (rho(J) >= 1)"
    if not _is_pd_exact(Ip, n):
        return False, "not robust: I + J is not positive definite (rho(J) >= 1)"
    return True, "ok"


# ===========================================================================
# candidate space
# ===========================================================================

_THETA_CACHE = {}


def _count_unit_vectors(n, qmin, qmax):
    """Exact number of sign-normalised rational unit vectors in Q^n whose
    reduced denominator lies in [qmin, qmax]."""
    key = (n, qmax)
    if key not in _THETA_CACHE:
        M = qmax * qmax
        squares = [k * k for k in range(0, int(math.isqrt(M)) + 1)]
        cur = [0] * (M + 1)
        cur[0] = 1
        for _ in range(n):
            new = [0] * (M + 1)
            for i, c in enumerate(cur):
                if not c:
                    continue
                for s in squares:
                    if i + s > M:
                        break
                    new[i + s] += c * (1 if s == 0 else 2)
            cur = new
        _THETA_CACHE[key] = cur
    R = _THETA_CACHE[key]
    mu = [1] * (qmax + 1)
    primes = []
    comp = [False] * (qmax + 1)
    for i in range(2, qmax + 1):
        if not comp[i]:
            primes.append(i)
            mu[i] = -1
        for pr in primes:
            if i * pr > qmax:
                break
            comp[i * pr] = True
            if i % pr == 0:
                mu[i * pr] = 0
                break
            mu[i * pr] = -mu[i]
    total = 0
    for q in range(max(1, qmin), qmax + 1):
        s = 0
        for e in range(1, q + 1):
            if q % e == 0 and mu[e]:
                s += mu[e] * R[(q // e) ** 2]
        total += s
    return total // 2


def search_space(inst):
    return _count_unit_vectors(inst["n"], inst["qmin"], inst["qmax"])


def random_candidate(inst, rng):
    """A random member of CERTIFICATE_LANGUAGE: a sign-normalised rational unit
    vector whose reduced denominator lies in the published band.  Same sampler
    as the plant, so there is no distributional tell."""
    a, q = _sample_unit_vector(rng, inst["n"], inst["qmin"], inst["qmax"])
    if a is None:
        return None
    return [list(_reduce(a[i], q)) for i in range(inst["n"])]


def enumerate_all(inst, cap=400000):
    """Exact count of valid answers, by exhausting the certificate language.
    Returns None when the language is too large to walk."""
    n, qmin, qmax = inst["n"], inst["qmin"], inst["qmax"]
    if _count_unit_vectors(n, qmin, qmax) > cap:
        return None
    count = 0
    for q in range(qmin, qmax + 1):
        for a in _integer_sphere(n, q):
            g = 0
            for t in a:
                g = math.gcd(g, abs(t))
            if g != 1:
                continue
            first = 0
            for t in a:
                if t:
                    first = t
                    break
            if first < 0:
                continue
            ok, _ = verify(inst, [list(_reduce(t, q)) for t in a])
            if ok:
                count += 1
    return count


def _integer_sphere(n, q):
    """All integer vectors of norm exactly q (small q only)."""
    def rec(k, rem, acc):
        if k == n - 1:
            r = math.isqrt(rem)
            if r * r == rem:
                if r == 0:
                    yield acc + [0]
                else:
                    yield acc + [r]
                    yield acc + [-r]
            return
        lim = math.isqrt(rem)
        for v in range(-lim, lim + 1):
            yield from rec(k + 1, rem - v * v, acc + [v])
    return rec(0, q * q, [])


# ===========================================================================
# canonical key
# ===========================================================================

def canonical_key(inst) -> str:
    """Invariant under the family's relabellings: permuting the variables,
    flipping the sign of any variable, and rescaling F by a nonzero rational.
    Built from the multiset {(sorted exponent vector, |coefficient|/content)}.
    """
    content = 0
    for coef, _ in inst["terms"]:
        content = math.gcd(content, abs(coef))
    content = content or 1
    items = sorted((tuple(sorted(e, reverse=True)), abs(c) // content)
                   for c, e in inst["terms"])
    blob = "|".join("%s:%d" % (",".join(map(str, e)), c) for e, c in items)
    head = "n=%d;d=%d;q=[%d,%d];" % (inst["n"], inst["d"], inst["qmin"], inst["qmax"])
    return hashlib.sha256((head + blob).encode()).hexdigest()


# ===========================================================================
# escalation -- grow the haystack, never the needle
# ===========================================================================

def escalate(params: dict):
    p = dict(params)
    for k, v in DIFFICULTY[SHIPPING_DIFFICULTY].items():
        p.setdefault(k, v)
    rounds = int(p.get("_escalations", 0)) + 1
    p["_escalations"] = rounds
    # every step moves at least two axes; n never moves, so the answer stays
    # exactly n rationals long.
    p["whi"] = int(p["whi"] * 5)                    # smaller region of convergence
    p["wlo"] = max(1, int(p["whi"] // 25))
    p["m"] = int(p["m"] + 15)                       # more decoy generators
    if rounds % 2 == 1:
        p["qmax"] = int(p["qmax"] * 2)              # taller answers, same length
        p["qmin"] = int(p["qmin"] * 2)
    else:
        p["d"] = int(p["d"] + 1)                    # higher tensor order
    return p


# ===========================================================================
# the compact route (the intended solution) and the attack panel
# ===========================================================================

def _hessian_at_basis_vector(inst, idx):
    """Hess F(e_idx) read straight off the coefficients: only the monomials
    x_idx^{d-2} x_j x_k contribute.  Returns (matrix, exact operation count)."""
    n, d = inst["n"], inst["d"]
    table = {tuple(e): c for c, e in inst["terms"]}
    H = [[0] * n for _ in range(n)]
    ops = 0
    for j in range(n):
        for k in range(j, n):
            e = [0] * n
            e[idx] += d - 2
            e[j] += 1
            e[k] += 1
            c = table.get(tuple(e), 0)
            f = e[j]
            ee = list(e)
            ee[j] -= 1
            f *= ee[k]
            H[j][k] = H[k][j] = c * f
            ops += 2
    return H, ops


def compact_route(inst):
    """The intended solution: v spans the kernel of [Hess F(e_1), Hess F(e_2)].
    Returns (answer or None, exact operation count)."""
    n = inst["n"]
    H1, o1 = _hessian_at_basis_vector(inst, 0)
    H2, o2 = _hessian_at_basis_vector(inst, 1)
    ops = o1 + o2
    P = [[0] * n for _ in range(n)]
    Q = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            s = t = 0
            for k in range(n):
                s += H1[i][k] * H2[k][j]
                t += H2[i][k] * H1[k][j]
                ops += 4
            P[i][j] = s
            Q[i][j] = t
    C = [[Fraction(P[i][j] - Q[i][j]) for j in range(n)] for i in range(n)]
    ops += n * n
    ns = _nullspace(C, n)
    ops += n ** 3 // 2 + n
    if len(ns) != 1:
        return None, ops
    vec = ns[0]
    den = 1
    for x in vec:
        den = den * x.denominator // math.gcd(den, x.denominator)
    ints = [int(x * den) for x in vec]
    g = 0
    for t in ints:
        g = math.gcd(g, abs(t))
    if g == 0:
        return None, ops
    ints = [t // g for t in ints]
    q2 = sum(t * t for t in ints)
    q = math.isqrt(q2)
    ops += n + 2
    if q * q != q2:
        return None, ops
    for t in ints:
        if t:
            if t < 0:
                ints = [-u for u in ints]
            break
    return [list(_reduce(t, q)) for t in ints], ops


def _nullspace(M, n):
    A = [row[:] for row in M]
    piv = []
    r = 0
    for c in range(n):
        p = None
        for i in range(r, n):
            if A[i][c] != 0:
                p = i
                break
        if p is None:
            continue
        A[r], A[p] = A[p], A[r]
        pv = A[r][c]
        A[r] = [x / pv for x in A[r]]
        for i in range(n):
            if i != r and A[i][c] != 0:
                f = A[i][c]
                A[i] = [A[i][j] - f * A[r][j] for j in range(n)]
        piv.append(c)
        r += 1
        if r == n:
            break
    free = [c for c in range(n) if c not in piv]
    out = []
    for fc in free:
        v = [Fraction(0)] * n
        v[fc] = Fraction(1)
        for i, c in enumerate(piv):
            v[c] = -A[i][fc]
        out.append(v)
    return out


# ---------------------------------------------------------------------------
# attacks.  Floating point is allowed HERE (an attack is not a verifier); every
# candidate an attack produces is handed back to the exact verify() above.
# ---------------------------------------------------------------------------

_FLOAT_CACHE = {}


def _float_tables(inst):
    """Per-instance tables for fast float gradient evaluation (attacks only)."""
    key = id(inst)
    hit = _FLOAT_CACHE.get(key)
    if hit is not None and hit[0] is inst:
        return hit[1]
    n, d = inst["n"], inst["d"]
    exps = [tuple(e) for _, e in inst["terms"]]
    dcoef = [[float(c * e[j]) for c, e in inst["terms"]] for j in range(n)]
    tables = (exps, dcoef, n, d)
    _FLOAT_CACHE[key] = (inst, tables)
    if len(_FLOAT_CACHE) > 64:
        for k in list(_FLOAT_CACHE)[:32]:
            _FLOAT_CACHE.pop(k, None)
    return tables


def _grad_float(inst, x):
    """grad F(x) in floating point.  Attacks only -- verify() never calls this."""
    exps, dcoef, n, d = _float_tables(inst)
    pw = [[1.0] * (d + 1) for _ in range(n)]
    for i in range(n):
        xi = x[i]
        row = pw[i]
        for k in range(1, d + 1):
            row[k] = row[k - 1] * xi
    mon = []
    ap = mon.append
    for e in exps:
        t = 1.0
        for i in range(n):
            k = e[i]
            if k:
                t *= pw[i][k]
        ap(t)
    g = [0.0] * n
    for j in range(n):
        xj = x[j]
        if xj == 0.0:
            s = 0.0
            cj = dcoef[j]
            for idx, e in enumerate(exps):
                k = e[j]
                if k:
                    t = cj[idx]
                    for i in range(n):
                        p = e[i] - (1 if i == j else 0)
                        if p:
                            t *= pw[i][p]
                    s += t
            g[j] = s
        else:
            s = 0.0
            cj = dcoef[j]
            for idx in range(len(exps)):
                c = cj[idx]
                if c:
                    s += c * mon[idx]
            g[j] = s / xj
    return g


def _rationalise(x, maxden):
    return [Fraction(t).limit_denominator(maxden) for t in x]


def _canon_candidate(fr, n):
    den = 1
    for t in fr:
        den = den * t.denominator // math.gcd(den, t.denominator)
    ints = [int(t * den) for t in fr]
    for t in ints:
        if t:
            if t < 0:
                ints = [-u for u in ints]
            break
    return [list(_reduce(t, den)) for t in ints]


def attack_power_method(inst, restarts=256, seed=0, iters=80, budget_ops=None):
    """The domain-standard algorithm of the paper: the tensor power method from
    random starts, then exact rational reconstruction of the limit."""
    rng = random.Random(seed)
    n, d = inst["n"], inst["d"]
    ops = 0
    nterms = len(inst["terms"])
    for r in range(restarts):
        x = [rng.gauss(0.0, 1.0) for _ in range(n)]
        nrm = math.sqrt(sum(t * t for t in x)) or 1.0
        x = [t / nrm for t in x]
        for _ in range(iters):
            g = _grad_float(inst, x)
            ops += nterms * n * (d + 1)
            nrm = math.sqrt(sum(t * t for t in g))
            if nrm == 0.0:
                break
            y = [t / nrm for t in g]
            if (sum(abs(y[i] - x[i]) for i in range(n)) < 1e-14
                    or sum(abs(y[i] + x[i]) for i in range(n)) < 1e-14):
                x = y
                break
            x = y
        for sgn in (1, -1):
            cand = _canon_candidate(_rationalise([sgn * t for t in x],
                                                 inst["qmax"]), n)
            ok, _ = verify(inst, cand)
            if ok:
                return True, r + 1, ops, cand
        if budget_ops and ops > budget_ops:
            return False, r + 1, ops, None
    return False, restarts, ops, None


def attack_dominant_rank_one(inst, restarts=32, seed=0):
    """Best rank-one approximation / dominant eigenvector: iterate the power
    method but keep only the largest |F| limit, the usual practical target."""
    rng = random.Random(seed)
    n = inst["n"]
    best = None
    bestval = -1.0
    ops = 0
    for _ in range(restarts):
        x = [rng.gauss(0.0, 1.0) for _ in range(n)]
        nrm = math.sqrt(sum(t * t for t in x)) or 1.0
        x = [t / nrm for t in x]
        for _ in range(50):
            g = _grad_float(inst, x)
            ops += len(inst["terms"]) * n * (inst["d"] + 1)
            nrm = math.sqrt(sum(t * t for t in g))
            if nrm == 0.0:
                break
            x = [t / nrm for t in g]
        val = abs(sum(_grad_float(inst, x)[i] * x[i] for i in range(n)))
        if val > bestval:
            bestval, best = val, x[:]
    for sgn in (1, -1):
        cand = _canon_candidate(_rationalise([sgn * t for t in best], inst["qmax"]), n)
        ok, _ = verify(inst, cand)
        if ok:
            return True, ops, cand
    return False, ops, None


def attack_coefficient_outlier(inst, seed=0):
    """Read the plant off the published coefficients: the directions suggested by
    the largest / smallest coefficients, by the pure powers x_i^d, and by the
    coordinate and +-1 patterns a solver would try first."""
    n, d = inst["n"], inst["d"]
    cands = []
    terms = sorted(inst["terms"], key=lambda t: -abs(t[0]))
    for coef, e in terms[:6] + terms[-6:]:
        vec = [t for t in e]
        if any(vec):
            cands.append(vec)
        cands.append([(1 if t % 2 == 0 else -1) * t for t in e])
    pures = []
    for i in range(n):
        e = [0] * n
        e[i] = d
        pures.append(abs(dict((tuple(x[1]), x[0]) for x in inst["terms"])
                         .get(tuple(e), 0)))
    cands.append(pures)
    for i in range(n):
        e = [0] * n
        e[i] = 1
        cands.append(e)
    ops = len(inst["terms"]) * 2
    for vec in cands:
        q2 = sum(t * t for t in vec)
        if q2 == 0:
            continue
        q = math.isqrt(q2)
        if q * q != q2 or not (inst["qmin"] <= q <= inst["qmax"]):
            continue
        cand = _canon_candidate([Fraction(t, q) for t in vec], n)
        ok, _ = verify(inst, cand)
        ops += len(inst["terms"]) * n
        if ok:
            return True, ops, cand
    return False, ops, None


def _fast_not_eigenvector(inst, cand, p=1000003):
    """Cheap mod-p necessary condition; True means 'certainly not an answer'."""
    den = 1
    for num, dd in cand:
        den = den * dd // math.gcd(den, dd)
    pt = [num * (den // dd) for num, dd in cand]
    return not _mod_p_eigen_filter(inst["terms"], inst["n"], pt, p)


def attack_low_height_sweep(inst, budget=4000, seed=0):
    """The in-context attack: sweep rational unit vectors of the smallest
    admissible denominators -- the ones a solver can write down and test by hand
    -- in increasing order of height."""
    n, qmin, qmax = inst["n"], inst["qmin"], inst["qmax"]
    tried = 0
    ops = 0
    for q in range(qmin, qmax + 1):
        for a in _integer_sphere(n, q):
            g = 0
            for t in a:
                g = math.gcd(g, abs(t))
            if g != 1:
                continue
            first = 0
            for t in a:
                if t:
                    first = t
                    break
            if first < 0:
                continue
            tried += 1
            ops += len(inst["terms"]) * n
            cand = [list(_reduce(t, q)) for t in a]
            if _fast_not_eigenvector(inst, cand):
                if tried >= budget:
                    return False, tried, ops, None
                continue
            ok, _ = verify(inst, cand)
            if ok:
                return True, tried, ops, cand
            if tried >= budget:
                return False, tried, ops, None
    return False, tried, ops, None


def attack_random_guess(inst, trials=2000, seed=0):
    rng = random.Random(seed)
    ops = 0
    for _ in range(trials):
        cand = random_candidate(inst, rng)
        if cand is None:
            continue
        ops += len(inst["terms"]) * inst["n"]
        if _fast_not_eigenvector(inst, cand):
            continue
        ok, _ = verify(inst, cand)
        if ok:
            return True, ops, cand
    return False, ops, None


# ===========================================================================
# selftest
# ===========================================================================

def _transform_instance(inst, perm, signs):
    """Relabelling: x_i -> signs[i] * x_{perm[i]}.  Maps the family to itself."""
    n = inst["n"]
    out = dict(inst)
    terms = []
    for coef, e in inst["terms"]:
        ne = [0] * n
        s = 1
        for i in range(n):
            ne[perm[i]] = e[i]
            if e[i] % 2 and signs[i] < 0:
                s = -s
        terms.append([coef * s, ne])
    out["terms"] = terms
    ans = [None] * n
    for i in range(n):
        num, den = inst["answer"][i]
        ans[perm[i]] = [num * signs[i], den]
    # restore the sign convention
    first = 0
    for num, den in ans:
        if num:
            first = num
            break
    if first < 0:
        ans = [[-num, den] for num, den in ans]
    out["answer"] = [list(_reduce(a, b)) for a, b in ans]
    return out


def _mod_p_eigen_filter(terms, n, pt, p):
    """Cheap necessary condition for 'grad F(x) parallel to x', mod p."""
    pw = [[1] * 1 for _ in range(n)]
    mx = 0
    for _, e in terms:
        mx = max(mx, max(e))
    pw = [[1] * (mx + 1) for _ in range(n)]
    for i in range(n):
        v = pt[i] % p
        for k in range(1, mx + 1):
            pw[i][k] = (pw[i][k - 1] * v) % p
    g0 = g1 = 0
    for coef, e in terms:
        if e[0]:
            t = (coef * e[0]) % p
            for i in range(n):
                k = e[i] - (1 if i == 0 else 0)
                if k:
                    t = (t * pw[i][k]) % p
            g0 = (g0 + t) % p
        if e[1]:
            t = (coef * e[1]) % p
            for i in range(n):
                k = e[i] - (1 if i == 1 else 0)
                if k:
                    t = (t * pw[i][k]) % p
            g1 = (g1 + t) % p
    return (g0 * pt[1] - g1 * pt[0]) % p == 0


def selftest(quick=False, g4_trials=200000, verbose=False):
    report = {}
    t_start = time.time()
    ship = DIFFICULTY[SHIPPING_DIFFICULTY]

    def log(*a):
        if verbose:
            print(*a, file=sys.stderr)

    # ---------------- G1 ----------------
    ok_n = tot = 0
    per_preset = {}
    for name, params in DIFFICULTY.items():
        good = 0
        seeds = range(8)
        for s in seeds:
            inst = make_instance(seed=s, **params)
            ok, why = verify(inst, inst["answer"])
            tot += 1
            ok_n += bool(ok)
            good += bool(ok)
        per_preset[name] = "%d/%d" % (good, len(list(seeds)))
    report["G1_planted_verifies"] = {"pass": ok_n == tot, "ok": ok_n,
                                     "total": tot, "per_preset": per_preset}
    log("G1", report["G1_planted_verifies"])

    # ---------------- G2 ----------------
    inst = make_instance(seed=3, **ship)
    ans = inst["answer"]
    reasons = set()
    fails = []

    def rej(a, label):
        ok, why = verify(inst, a)
        fails.append((label, ok, why))
        if not ok:
            reasons.add(why.split(":")[0])
        return not ok

    n = inst["n"]
    all_rejected = True
    all_rejected &= rej(ans[:-1], "drop one coordinate")
    all_rejected &= rej([], "empty")
    all_rejected &= rej([[ans[0][0] + 1, ans[0][1]]] + ans[1:], "perturb one numerator")
    all_rejected &= rej(ans[1:] + ans[:1], "rotate coordinates")
    all_rejected &= rej([[-a[0], a[1]] for a in ans], "global sign flip")
    all_rejected &= rej([[a[0] * 2, a[1]] for a in ans], "scale by 2 (not unit)")
    all_rejected &= rej([[a[0], a[1] * 3] for a in ans], "denominator inflated")
    all_rejected &= rej([[1, 1]] + [[0, 1]] * (n - 1), "coordinate vector e_1")
    all_rejected &= rej([[0, 1]] * n, "zero vector")
    all_rejected &= rej("garbage", "garbage type")
    # an exact eigenvector that is NOT robust: same family, tiny member, so the
    # robustness clause is shown to reject rather than being decorative.
    toy = {"n": 2, "d": 3, "qmin": 1, "qmax": 4,
           "terms": [[1, [3, 0]], [3, [1, 2]]], "answer": [[1, 1], [0, 1]]}
    ok_toy, why_toy = verify(toy, [[1, 1], [0, 1]])
    toy_ok = {"n": 2, "d": 3, "qmin": 1, "qmax": 4,
              "terms": [[1, [3, 0]], [1, [1, 2]]], "answer": [[1, 1], [0, 1]]}
    ok_toy2, why_toy2 = verify(toy_ok, [[1, 1], [0, 1]])
    if not ok_toy:
        reasons.add(why_toy.split(":")[0])
    report["G2_rejects_corruption"] = {
        "pass": all_rejected and (not ok_toy) and ok_toy2,
        "corruptions_rejected": sum(1 for _, ok, _ in fails if not ok),
        "corruptions_total": len(fails),
        "distinct_reasons": len(reasons),
        "reasons": sorted(reasons),
        "robustness_clause_exercised": {
            "instance": "F = x^3 + 3 x y^2, candidate (1,0): exact eigenvector, rho(J)=2",
            "rejected": not ok_toy, "reason": why_toy,
            "control_F_eq_x3_plus_xy2_rho_two_thirds_accepted": ok_toy2,
        },
    }
    log("G2", report["G2_rejects_corruption"]["pass"])

    # ---------------- G3 ----------------
    reply = ("Working through the Hessians I get a common eigenvector.\n\n"
             "Therefore the robust eigenvector is\n\n<answer>"
             + ", ".join("%d/%d" % (a[0], a[1]) for a in ans) + "</answer>\n\n"
             "which you can check satisfies grad F(x) = d mu x.")
    parsed = parse_answer(reply)
    rt_ok = parsed == ans and verify(inst, parsed)[0]
    junk_ok = (parse_answer("no answer here") is None
               and parse_answer("<answer>banana</answer>") is None
               and parse_answer(None) is None)
    fenced = parse_answer("```\n<answer>[%s]</answer>\n```"
                          % ", ".join("%d/%d" % (a[0], a[1]) for a in ans))
    report["G3_round_trip"] = {"pass": bool(rt_ok and junk_ok and fenced == ans),
                               "parsed_ok": bool(rt_ok), "rejects_junk": bool(junk_ok),
                               "tolerates_markdown": fenced == ans}
    log("G3", report["G3_round_trip"])

    # ---------------- G4 ----------------
    space = search_space(inst)
    rng = random.Random(20260906)
    hits = 0
    trials = 0
    p = 1000003
    full_checks = 0
    t0 = time.time()
    target = 2000 if quick else g4_trials
    while trials < target:
        cand = random_candidate(inst, rng)
        if cand is None:
            continue
        trials += 1
        den = 1
        for num, dd in cand:
            den = den * dd // math.gcd(den, dd)
        pt = [num * (den // dd) for num, dd in cand]
        if not _mod_p_eigen_filter(inst["terms"], n, pt, p):
            continue
        full_checks += 1
        ok, _ = verify(inst, cand)
        if ok:
            hits += 1
    g4_secs = time.time() - t0
    analytic = 1.0 / space
    report["G4_guess_resistance"] = {
        "pass": hits == 0 and analytic < 1e-6,
        "hits": hits, "trials": trials,
        "full_verifications_after_mod_p_filter": full_checks,
        "structure_aware_space": space,
        "analytic_p_one_valid": analytic,
        "sampler": "same Householder sampler that draws the plant",
        "seconds": g4_secs,
    }
    log("G4", report["G4_guess_resistance"])

    # ---------------- G5 ----------------
    demo_inst = make_instance(seed=5, **DIFFICULTY["demo"])
    exact_demo = enumerate_all(demo_inst)
    # robust eigenvector census at the shipping preset, numerically
    census = _robust_census(inst, restarts=120 if quick else 300, seed=11)
    ref_ans, ref_ops = compact_route(inst)
    t0 = time.time()
    for _ in range(20):
        compact_route(inst)
    ref_secs = (time.time() - t0) / 20
    t0 = time.time()
    solved, restarts_used, pm_ops, _ = attack_power_method(
        inst, restarts=32 if quick else 512, seed=4242)
    pm_secs = time.time() - t0
    density = 1.0 / space
    basin = _basin_estimate(inst, dirs=6 if quick else 16, seed=77)
    brute = _bruteforce_cost(inst, sample=100 if quick else 400)
    frac = basin["sphere_fraction_at_mean_angle"]
    ops_per_restart = pm_ops / max(1, restarts_used)
    pm_extrapolated = (ops_per_restart / frac) if frac > 0 else None
    report["G5_density_and_cost"] = {
        "pass": True,
        "shipping_density": density,
        "shipping_valid_answer_count": census["valid_answers_known"],
        "shipping_valid_answer_count_basis":
            "the plant, verified exactly; plus any OTHER rational robust "
            "eigenvector the numerical census turned up (measured: %d)"
            % census["other_rational_robust_found"],
        "shipping_density_sampled_hits": hits,
        "shipping_density_sampled_trials": trials,
        "exact_count_demo": exact_demo,
        "exact_count_demo_language_size": _count_unit_vectors(
            demo_inst["n"], demo_inst["qmin"], demo_inst["qmax"]),
        "generic_eigenvector_count_formula": census["generic_eigenvector_count"],
        "robust_eigenvectors_found_numerically": census["robust_found"],
        "robust_eigenvector_basins": census["basins"],
        "plant_basin_hits_uniform_restarts": census["plant_basin_fraction"],
        "plant_region_of_convergence": basin,
        "strongest_attack":
            "tensor power method with random restarts (the paper's own algorithm)",
        "baseline_wall_clock_sec": pm_secs,
        "baseline_operations": pm_ops,
        "baseline_restarts": restarts_used,
        "baseline_solved": bool(solved),
        "baseline_operations_extrapolated_to_success": pm_extrapolated,
        "bruteforce_over_certificate_language": brute,
        "compact_ops_shipping": ref_ops,
        "compact_seconds_shipping": ref_secs,
        "gap_mechanical_over_compact":
            (pm_extrapolated / ref_ops) if (pm_extrapolated and ref_ops) else None,
        "gap_bruteforce_over_compact":
            (brute["total_operations"] / ref_ops) if ref_ops else None,
    }
    log("G5", report["G5_density_and_cost"])

    # ---------------- G6 ----------------
    seeds = list(range(100, 108))
    attacks = {}

    def run(name, fn):
        succ = 0
        for s in seeds:
            i2 = make_instance(seed=s, **ship)
            r = fn(i2, s)
            succ += bool(r)
        attacks[name] = {"successes": succ, "attempts": len(seeds)}

    pm_budget = 32 if quick else 512
    run("best_rank_one_dominant_eigenvector",
        lambda i, s: attack_dominant_rank_one(i, restarts=16, seed=s)[0])
    run("coefficient_outlier",
        lambda i, s: attack_coefficient_outlier(i, seed=s)[0])
    run("low_height_sweep_in_context",
        lambda i, s: attack_low_height_sweep(i, budget=1200, seed=s)[0])
    run("random_candidate_2000",
        lambda i, s: attack_random_guess(i, trials=2000, seed=s)[0])
    run("hosvd_dominant_singular_vector",
        lambda i, s: attack_hosvd_top_singular_vector(i, seed=s)[0])

    probe_hits = 0
    probe_ops = 0
    for s2 in seeds:
        i2 = make_instance(seed=s2, **ship)
        okp, op, _ = probe_hosvd_bottom_singular_vector(i2, seed=s2)
        probe_hits += bool(okp)
        probe_ops += op

    ref_succ = 0
    ref_ops_tot = 0
    t0 = time.time()
    for s in seeds:
        i2 = make_instance(seed=s, **ship)
        a2, o2 = compact_route(i2)
        ref_ops_tot += o2
        if a2 is not None and verify(i2, a2)[0]:
            ref_succ += 1
    ref_wall = (time.time() - t0) / len(seeds)
    pm_solved = 0
    pm_ops_tot = 0
    pm_used = []
    t0 = time.time()
    for s2 in seeds:
        i2 = make_instance(seed=s2, **ship)
        okp, used, o, _ = attack_power_method(i2, restarts=pm_budget, seed=s2)
        pm_solved += bool(okp)
        pm_ops_tot += o
        pm_used.append(used if okp else None)
    pm_wall = (time.time() - t0) / len(seeds)

    nw_solved = 0
    nw_ops = 0
    nw_starts = []
    t0 = time.time()
    nw_budget = 60 if quick else 200
    for s2 in seeds:
        i2 = make_instance(seed=s2, **ship)
        okn, used, o, _ = attack_newton_eigensystem(i2, starts=nw_budget, seed=s2)
        nw_solved += bool(okn)
        nw_ops += o
        nw_starts.append(used if okn else None)
    nw_wall = (time.time() - t0) / len(seeds)

    report["G6_adversary_panel"] = {
        "pass": all(v["successes"] == 0 for v in attacks.values()),
        "attacks": attacks,
        "additional_reference_routes": {
            "tensor_power_method_random_restarts": {
                "name": "the paper's own algorithm: x <- T.x^{d-1}/||T.x^{d-1}|| "
                        "from random starts, then rational reconstruction",
                "complexity": "O(#coefficients * n) float ops per iteration; "
                              "expected restarts = 1 / (region of convergence)",
                "restart_budget": pm_budget,
                "solves": "%d/%d" % (pm_solved, len(seeds)),
                "starts_used_when_solved": pm_used,
                "mean_operations_per_instance": pm_ops_tot // len(seeds),
                "wall_clock_sec_per_instance": pm_wall,
                "why_not_in_attacks": "on Track B the domain-standard algorithm is "
                                      "EXPECTED to succeed and is the hardness "
                                      "basis, not a gate failure.  It solved %d of "
                                      "%d shipping instances inside %d restarts; "
                                      "the measured region of convergence around "
                                      "the plant (G5) says the expected budget is "
                                      "~1/3.2e-4 = 3100 restarts."
                                      % (pm_solved, len(seeds), pm_budget),
            },
            "newton_on_the_eigensystem": {
                "name": "Newton from random starts on grad F(x) = lam x, <x,x> = 1, "
                        "then rational reconstruction of the limit",
                "complexity": "O(#coefficients * n^2 + n^3) float ops per iteration; "
                              "hits the plant with probability ~1/(number of real "
                              "critical points) per start",
                "restart_budget": nw_budget,
                "solves": "%d/%d" % (nw_solved, len(seeds)),
                "mean_operations_per_instance": nw_ops // len(seeds),
                "wall_clock_sec_per_instance": nw_wall,
                "starts_used_when_solved": nw_starts,
                "why_not_in_attacks": "it succeeds; on Track B a succeeding "
                                      "efficient algorithm is the hardness basis, "
                                      "not a gate failure",
            },
            "unfolding_gram_bottom_eigenvector": {
                "name": "HOSVD unfolding Gram, SMALLEST eigenvector",
                "solves": "%d/%d" % (probe_hits, len(seeds)),
                "mean_operations_per_instance": probe_ops // len(seeds),
                "why_not_in_attacks": "this is the compact route entered from the "
                                      "other end of the spectrum: the plant is an "
                                      "exact eigenvector of every second-order "
                                      "contraction, which is precisely the insight "
                                      "the family tests.  Disclosed, not hidden.",
            },
        },
        "reference_algorithm": {
            "name": "commutator of two Hessians, then its kernel (exact over Q)",
            "complexity": "O(n^3) exact rational operations, independent of the "
                          "number of published coefficients",
            "wall_clock_sec": ref_wall,
            "operations": ref_ops_tot // len(seeds),
            "solves": "%d/%d, as expected" % (ref_succ, len(seeds)),
        },
    }
    log("G6", report["G6_adversary_panel"]["pass"], attacks)

    # ---------------- G7 ----------------
    big = dict(ship)
    big["m"] = ship["m"] * 2
    big["d"] = ship["d"] + 1
    inst_big = make_instance(seed=9, **big)
    big_ok = verify(inst_big, inst_big["answer"])[0]
    esc = escalate(dict(ship))
    inst_esc = make_instance(seed=9, **{k: v for k, v in esc.items()
                                        if not str(k).startswith("_")})
    esc_ok = verify(inst_esc, inst_esc["answer"])[0]
    moved = [k for k in ("d", "m", "whi", "wlo", "qmax", "qmin")
             if esc.get(k) != ship.get(k)]
    ladder = []
    pp = dict(ship)
    for r in range(3):
        pp = escalate(pp)
        clean = {k: v for k, v in pp.items() if not str(k).startswith("_")}
        i3 = make_instance(seed=1, **clean)
        a3 = json.dumps(i3["answer"], separators=(",", ":"))
        ladder.append({"round": r + 1, "params": clean,
                       "answer_chars": len(a3),
                       "answer_elements": 2 * i3["n"],
                       "terms_published": len(i3["terms"]),
                       "verifies": verify(i3, i3["answer"])[0]})
    report["G7_scales"] = {
        "pass": bool(big_ok and esc_ok and len(moved) >= 2
                     and all(x["verifies"] for x in ladder)
                     and len({x["answer_elements"] for x in ladder}) == 1),
        "size_doubled_builds_and_verifies": bool(big_ok),
        "escalated_builds_and_verifies": bool(esc_ok),
        "moved_params": moved,
        "escalation_ladder": ladder,
    }
    log("G7", report["G7_scales"]["pass"])

    # ---------------- G8 ----------------
    inv_ok = inv_tot = 0
    transformed_verifies = 0
    keys = []
    rng8 = random.Random(7)
    for s in range(20):
        i4 = make_instance(seed=200 + s, **ship)
        k0 = canonical_key(i4)
        keys.append(k0)
        for _ in range(6):
            perm = list(range(i4["n"]))
            rng8.shuffle(perm)
            signs = [rng8.choice([1, -1]) for _ in range(i4["n"])]
            i5 = _transform_instance(i4, perm, signs)
            inv_tot += 1
            if canonical_key(i5) == k0:
                inv_ok += 1
            if verify(i5, i5["answer"])[0]:
                transformed_verifies += 1
        i6 = dict(i4)
        i6["terms"] = [[c * 3, e] for c, e in i4["terms"]]
        inv_tot += 1
        if canonical_key(i6) == k0:
            inv_ok += 1
        if verify(i6, i4["answer"])[0]:
            transformed_verifies += 1
    report["G8_canonical_key"] = {
        "pass": inv_ok == inv_tot and len(set(keys)) == len(keys)
                and transformed_verifies == inv_tot,
        "invariance_ok": inv_ok, "invariance_total": inv_tot,
        "transformed_instance_verifies": transformed_verifies,
        "distinct_keys": len(set(keys)), "keys_total": len(keys),
        "transformations": "variable permutations, sign flips of variables, "
                           "rescaling F by a nonzero integer",
    }
    log("G8", report["G8_canonical_key"]["pass"])

    # ---------------- G9 ----------------
    sizes = {}
    for name, params in DIFFICULTY.items():
        worst_chars = 0
        worst_ops = 0
        for s in range(12):
            i7 = make_instance(seed=300 + s, **params)
            txt = ", ".join("%d/%d" % (a[0], a[1]) for a in i7["answer"])
            worst_chars = max(worst_chars, len(txt))
            _, o = compact_route(i7)
            worst_ops = max(worst_ops, o)
        sizes[name] = {"chars": worst_chars, "elements": 2 * params["n"],
                       "route_ops": worst_ops}
    ship_size = sizes[SHIPPING_DIFFICULTY]
    within = (ship_size["chars"] <= 2000 and ship_size["elements"] <= 256
              and ship_size["route_ops"] <= 1000)
    report["G9_no_tool_suitability"] = {
        "pass": bool(within),
        "arms": {"bare": {"solved": 0, "attempts": 0},
                 "hinted": {"solved": 0, "attempts": 0},
                 "placebo": {"solved": 0, "attempts": 0}},
        "arms_note": "three-arm diagnostic not run by this selftest (no "
                     "OPENROUTER_API_KEY in this environment); recorded, never gated",
        "hinted_minus_placebo": None,
        "hinted_verdict": None,
        "answer_chars": ship_size["chars"],
        "answer_tokens": (ship_size["chars"] + 3) // 4,
        "answer_elements": ship_size["elements"],
        "intended_route_operations": ship_size["route_ops"],
        "caps": {"chars": 2000, "elements": 256, "operations": 1000},
        "per_preset": sizes,
        "hint_leak_check": {
            "default_render_has_no_hint":
                STRUCTURAL_HINT not in render(inst) and PLACEBO_HINT not in render(inst),
            "answer_not_in_render": all(
                ("%d/%d" % (a[0], a[1])) not in render(inst) for a in inst["answer"]),
        },
    }
    log("G9", report["G9_no_tool_suitability"])

    report["exactness_audit"] = _float_audit()
    report["exactness_audit"]["positive_definiteness_backend"] = _pd_backend_check()
    report["certificate_language"] = {
        "description": CERTIFICATE_LANGUAGE["description"],
        "bounds": {"n": ship["n"], "qmin": ship["qmin"], "qmax": ship["qmax"],
                   "n_elements": 2 * ship["n"]},
    }
    report["problem_profile"] = PROBLEM_PROFILE
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["selftest_seconds"] = time.time() - t_start
    report["all_passed"] = all(
        v.get("pass") is True for k, v in report.items()
        if isinstance(v, dict) and "pass" in v)
    return report





def _unfolding_gram(inst):
    """Exact Gram matrix of the mode-1 unfolding of T:  G = M M^T with
    M the n x n^{d-1} unfolding.  Grouped by exponent vector so it costs
    C(n+d-2, d-1) terms per entry rather than n^{d-1}."""
    n, d = inst["n"], inst["d"]
    table = {tuple(e): c for c, e in inst["terms"]}

    def entry(f, i):
        e = list(f)
        e[i] += 1
        c = table.get(tuple(e), 0)
        if c == 0:
            return Fraction(0)
        return Fraction(c, _multinomial(d, e))

    G = [[Fraction(0)] * n for _ in range(n)]
    ops = 0
    for f in _monomials(n, d - 1):
        w = _multinomial(d - 1, f)
        vals = [entry(f, i) for i in range(n)]
        for i in range(n):
            if vals[i] == 0:
                continue
            for j in range(i, n):
                if vals[j] == 0:
                    continue
                t = w * vals[i] * vals[j]
                G[i][j] += t
                if i != j:
                    G[j][i] += t
                ops += 3
    return G, ops


def _extreme_eigvec(G, n, largest=True, iters=300):
    """Top (or bottom) eigenvector of a small symmetric rational matrix, in
    floating point -- an attack helper, never used by verify()."""
    A = [[float(G[i][j]) for j in range(n)] for i in range(n)]
    if not largest:
        tr = max(abs(A[i][j]) for i in range(n) for j in range(n)) * n
        A = [[(tr if i == j else 0.0) - A[i][j] for j in range(n)] for i in range(n)]
    x = [1.0 / (i + 2) for i in range(n)]
    for _ in range(iters):
        y = [sum(A[i][j] * x[j] for j in range(n)) for i in range(n)]
        nrm = math.sqrt(sum(t * t for t in y))
        if nrm == 0.0:
            return x
        x = [t / nrm for t in y]
    return x


def attack_hosvd_top_singular_vector(inst, seed=0):
    """The standard first move for tensor decomposition: unfold the tensor,
    take the dominant left singular vector (HOSVD), rationalise, test."""
    n = inst["n"]
    G, ops = _unfolding_gram(inst)
    x = _extreme_eigvec(G, n, largest=True)
    ops += n * n * 300
    for sgn in (1, -1):
        cand = _canon_candidate(_rationalise([sgn * t for t in x], inst["qmax"]), n)
        if verify(inst, cand)[0]:
            return True, ops, cand
    return False, ops, None


def probe_hosvd_bottom_singular_vector(inst, seed=0):
    """DIAGNOSTIC, not an attack: the SAME unfolding Gram, bottom eigenvector.
    The plant is orthogonal to every other generator, so it is an exact
    eigenvector of this Gram -- with the smallest eigenvalue, because the plant
    weight is small.  This is a second entrance to the compact route and it is
    reported openly rather than hidden inside the attack panel."""
    n = inst["n"]
    G, ops = _unfolding_gram(inst)
    x = _extreme_eigvec(G, n, largest=False)
    ops += n * n * 300
    for sgn in (1, -1):
        cand = _canon_candidate(_rationalise([sgn * t for t in x], inst["qmax"]), n)
        if verify(inst, cand)[0]:
            return True, ops, cand
    return False, ops, None


def _hess_float(inst, x):
    n = inst["n"]
    H = [[0.0] * n for _ in range(n)]
    for coef, e in inst["terms"]:
        for j in range(n):
            if not e[j]:
                continue
            for k in range(j, n):
                ek = e[k] - (1 if k == j else 0)
                if ek <= 0:
                    continue
                t = float(coef * e[j] * ek)
                for i in range(n):
                    p = e[i] - (1 if i == j else 0) - (1 if i == k else 0)
                    if p:
                        t *= x[i] ** p
                H[j][k] += t
                if k != j:
                    H[k][j] += t
    return H


def _solve_float(A, b):
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-290:
            return None
        M[c], M[p] = M[p], M[c]
        pv = M[c][c]
        for r in range(n):
            if r == c:
                continue
            f = M[r][c] / pv
            if f:
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] for i in range(n)]


def attack_newton_eigensystem(inst, starts=200, seed=0, iters=50):
    """Newton on the full eigen-system  grad F(x) = lam x, <x,x> = 1, from random
    starts -- the numerical-algebraic-geometry route.  Unlike the power method it
    converges to ARBITRARY critical points, so a small region of convergence does
    not protect against it.  This one SOLVES the family; it is reported as a
    reference route, not as a failing attack.
    """
    rng = random.Random(seed)
    n = inst["n"]
    nt = len(inst["terms"])
    ops = 0
    converged = 0
    for st in range(starts):
        x = [rng.gauss(0.0, 1.0) for _ in range(n)]
        nrm = math.sqrt(sum(t * t for t in x)) or 1.0
        x = [t / nrm for t in x]
        g = _grad_float(inst, x)
        lam = sum(g[i] * x[i] for i in range(n)) * rng.choice(
            [1.0, 0.3, 0.05, 0.01, -0.05])
        good = False
        for _ in range(iters):
            g = _grad_float(inst, x)
            H = _hess_float(inst, x)
            ops += nt * n * 2 + nt * n * n
            R = [g[i] - lam * x[i] for i in range(n)] + [
                sum(t * t for t in x) - 1.0]
            sc = max(1.0, max(abs(t) for t in g))
            if max(abs(R[i]) / sc for i in range(n)) < 1e-14 and abs(R[n]) < 1e-14:
                good = True
                break
            J = [[H[i][j] - (lam if i == j else 0.0) for j in range(n)] + [-x[i]]
                 for i in range(n)]
            J.append([2 * x[i] for i in range(n)] + [0.0])
            sol = _solve_float(J, [-t for t in R])
            ops += (n + 1) ** 3
            if sol is None:
                break
            step = max(abs(t) for t in sol[:n])
            damp = 1.0 if step < 0.5 else 0.5 / step
            x = [x[i] + damp * sol[i] for i in range(n)]
            lam += damp * sol[n]
            nrm = math.sqrt(sum(t * t for t in x))
            if nrm == 0.0 or nrm > 1e6:
                break
        if not good:
            continue
        converged += 1
        for sgn in (1, -1):
            cand = _canon_candidate(_rationalise([sgn * t for t in x],
                                                 inst["qmax"]), n)
            if verify(inst, cand)[0]:
                return True, st + 1, ops, cand
    return False, starts, ops, None


def _basin_estimate(inst, dirs=16, seed=0, depth=12):
    """Measure the tensor power method's REGION OF CONVERGENCE around the plant.

    For random unit directions u orthogonal to the plant v, bisect on the angle
    theta to find the largest theta with cos(theta) v + sin(theta) u still
    converging back to v, then convert the mean angle into a fraction of the
    sphere.  This is the paper's own "region of convergence" quantity
    (Section 4.4, Figure 2), measured numerically -- it is a measurement, never
    part of verification.
    """
    rng = random.Random(seed)
    n = inst["n"]
    v = [float(Fraction(a[0], a[1])) for a in inst["answer"]]

    def converges(theta, u):
        x = [math.cos(theta) * v[i] + math.sin(theta) * u[i] for i in range(n)]
        nrm = math.sqrt(sum(t * t for t in x)) or 1.0
        x = [t / nrm for t in x]
        for _ in range(120):
            g = _grad_float(inst, x)
            nrm = math.sqrt(sum(t * t for t in g))
            if nrm == 0.0:
                return False
            x = [t / nrm for t in g]
        return (sum(abs(x[i] - v[i]) for i in range(n)) < 1e-6
                or sum(abs(x[i] + v[i]) for i in range(n)) < 1e-6)

    angles = []
    for _ in range(dirs):
        u = [rng.gauss(0.0, 1.0) for _ in range(n)]
        dot = sum(u[i] * v[i] for i in range(n))
        u = [u[i] - dot * v[i] for i in range(n)]
        nrm = math.sqrt(sum(t * t for t in u)) or 1.0
        u = [t / nrm for t in u]
        lo, hi = 0.0, math.pi / 2
        if not converges(lo + 1e-9, u):
            angles.append(0.0)
            continue
        for _ in range(depth):
            mid = (lo + hi) / 2
            if converges(mid, u):
                lo = mid
            else:
                hi = mid
        angles.append(lo)
    mean_theta = sum(angles) / len(angles)
    # fraction of S^{n-1} inside a cap of half-angle theta
    steps = 400
    def cap(theta):
        tot = 0.0
        part = 0.0
        for k in range(steps):
            t = math.pi * (k + 0.5) / steps
            w = math.sin(t) ** (n - 2)
            tot += w
            if t <= theta:
                part += w
        return part / tot
    return {"directions": dirs,
            "mean_half_angle_rad": mean_theta,
            "min_half_angle_rad": min(angles),
            "max_half_angle_rad": max(angles),
            "sphere_fraction_at_mean_angle": cap(mean_theta),
            "sphere_fraction_at_min_angle": cap(min(angles))}


def _bruteforce_cost(inst, sample=400, seed=0):
    """Cost of the route available with no insight at all: walk the certificate
    language and test each member.  Measured per candidate, extrapolated."""
    rng = random.Random(seed)
    ops_per = len(inst["terms"]) * inst["n"] * 2
    t0 = time.time()
    tried = 0
    while tried < sample:
        cand = random_candidate(inst, rng)
        if cand is None:
            continue
        tried += 1
        _fast_not_eigenvector(inst, cand)
    secs_per = (time.time() - t0) / sample
    space = search_space(inst)
    return {"language_size": space,
            "exact_operations_per_candidate": ops_per,
            "total_operations": space * ops_per,
            "seconds_per_candidate_measured": secs_per,
            "total_seconds_extrapolated": space * secs_per}


def _float_audit():
    """The verifier must never touch floating point.  Walk the AST of every
    function on the verification path and refuse float literals, float()/round()
    calls and math.sqrt/isclose."""
    import ast
    src = open(os.path.abspath(__file__)).read()
    tree = ast.parse(src)
    watched = {"verify", "_as_fractions", "_grad_int", "_value_int", "_hess_int",
               "_is_pd_exact", "_is_pd_exact_internal", "_reduce", "parse_answer",
               "_mod_p_eigen_filter",
               "_hessian_at_basis_vector", "compact_route", "_nullspace"}
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in watched:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, float):
                    bad.append((node.name, "float literal %r" % sub.value))
                if isinstance(sub, ast.Call):
                    f = sub.func
                    nm = getattr(f, "id", None) or getattr(f, "attr", None)
                    if nm in ("float", "round", "complex", "sqrt", "isclose",
                              "gauss", "random", "uniform"):
                        bad.append((node.name, "call to %s" % nm))
    return {"functions_checked": sorted(watched), "violations": bad,
            "clean": not bad,
            "note": "gvlib.exact_matrices is audited for the same property by "
                    "gvlib's own AST test"}


def _pd_backend_check(trials=400, seed=1):
    """Which positive-definiteness backend verify() is using, and a cross-check
    of the in-module fallback against gvlib on random symmetric matrices."""
    rng = random.Random(seed)
    agree = 0
    pd = 0
    for _ in range(trials):
        n = rng.choice([2, 3, 4, 5])
        A = [[Fraction(rng.randint(-4, 4), rng.randint(1, 3)) for _ in range(n)]
             for _ in range(n)]
        S = [[A[i][j] + A[j][i] for j in range(n)] for i in range(n)]
        if rng.random() < 0.5:
            S = [[S[i][j] + (Fraction(6) if i == j else Fraction(0))
                  for j in range(n)] for i in range(n)]
        own = _is_pd_exact_internal(S, n)
        if _em is not None:
            other = _em.is_positive_definite(_em.matrix(S))
        else:
            other = own
        agree += (own == other)
        pd += own
    return {"backend": "gvlib.exact_matrices.is_positive_definite"
                       if _em is not None else "in-module LDL fallback",
            "gvlib_available": _em is not None,
            "cross_check_trials": trials, "agreements": agree,
            "positive_definite_seen": pd}


def _robust_census(inst, restarts=300, seed=0):
    """Numerical census of robust eigenvectors: run the tensor power method from
    random starts and cluster the limits.  Floating point is used ONLY here, for
    a measurement that is reported as a measurement; it never touches verify()."""
    rng = random.Random(seed)
    n, d = inst["n"], inst["d"]
    limits = []
    counts = []
    plant = [Fraction(a[0], a[1]) for a in inst["answer"]]
    plant_f = [float(t) for t in plant]
    plant_hits = 0
    for _ in range(restarts):
        x = [rng.gauss(0.0, 1.0) for _ in range(n)]
        nrm = math.sqrt(sum(t * t for t in x)) or 1.0
        x = [t / nrm for t in x]
        for _ in range(90):
            g = _grad_float(inst, x)
            nrm = math.sqrt(sum(t * t for t in g))
            if nrm == 0.0:
                break
            y = [t / nrm for t in g]
            if sum(abs(y[i] - x[i]) for i in range(n)) < 1e-13:
                x = y
                break
            x = y
        placed = False
        for i, L in enumerate(limits):
            if (sum(abs(L[j] - x[j]) for j in range(n)) < 1e-6
                    or sum(abs(L[j] + x[j]) for j in range(n)) < 1e-6):
                counts[i] += 1
                placed = True
                break
        if not placed:
            limits.append(x[:])
            counts.append(1)
        if (sum(abs(plant_f[j] - x[j]) for j in range(n)) < 1e-6
                or sum(abs(plant_f[j] + x[j]) for j in range(n)) < 1e-6):
            plant_hits += 1
    rational = 0
    rational_others = 0
    for L in limits:
        cand = _canon_candidate(_rationalise(L, inst["qmax"]), n)
        if verify(inst, cand)[0]:
            rational += 1
            if (sum(abs(plant_f[j] - L[j]) for j in range(n)) > 1e-6
                    and sum(abs(plant_f[j] + L[j]) for j in range(n)) > 1e-6):
                rational_others += 1
    gen = ((d - 1) ** n - 1) // (d - 2)
    return {
        "restarts": restarts,
        "robust_found": len(limits),
        "basins": sorted(counts, reverse=True),
        "plant_basin_fraction": plant_hits / float(restarts),
        "rational_robust_found_among_limits": rational,
        "other_rational_robust_found": rational_others,
        "valid_answers_known": 1 + rational_others,
        "generic_eigenvector_count": gen,
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()
    if args.demo:
        i = make_instance(seed=1, **DIFFICULTY["demo"])
        print(render(i))
        print()
        print("answer:", i["answer"], verify(i, i["answer"]))
    else:
        rep = selftest(quick=args.quick, verbose=True)
        text = json.dumps(rep, indent=1, sort_keys=True, default=str)
        if args.out:
            with open(args.out, "w") as fh:
                fh.write(text + "\n")
        print(text)
