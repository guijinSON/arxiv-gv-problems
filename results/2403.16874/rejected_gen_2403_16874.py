"""Generator for arXiv:2403.16874 -- Cohn, de Laat, Leijenhorst,
"Optimality of spherical codes via exact semidefinite programming bounds".

FAMILY (as built and measured; see REJECTED.md for the verdict):
  Exact rational dual certificate for the Delsarte two-point linear programming
  bound on spherical codes.  The solver is handed the ambient dimension n, a
  rational cosine s = cos(theta), a degree cap d and a claimed cardinality bound
  B, and must produce the Gegenbauer coefficient vector (f_0=1, f_1, ..., f_d) of
  a polynomial f with
      (i)   f_k >= 0 for k = 1..d,
      (ii)  f(t) <= 0 for every real t in [-1, s],
      (iii) f(1) <= B,
  which by Delsarte/Goethals/Seidel proves |C| <= f(1)/f_0 = f(1) <= B for every
  spherical code C in S^{n-1} with maximal inner product at most s.  This is the
  two-point bound of the paper's Appendix A (Section "Two-point bounds"), the
  k=2 case of the k-point bounds described in Section 1, and it is the exact
  analogue of the three-point dual certificate of Section 3, equation
  (eq:codebound), at k=2 instead of k=3.

  The planting is inverse generation via complementary slackness (Section 3, the
  paragraph after (eq:upperbound)): the certificate is BUILT as
      f(t) = c * (t+1)^e * (t-s) * prod_i (t - a_i)^2,
  which is <= 0 on [-1,s] by inspection, normalised so that f_0 = 1, and kept
  only when every Gegenbauer coefficient f_k (k>=1) is >= 0.  No LP is ever
  solved inside make_instance.

NOTES
  - Section 3 (eq:codebound) fixed the exact definition of the k-point bound and
    the objective 1 + <F_0, J>.
  - Section 2 ("Rounding procedure") is what told me the certificate is the
    output of an SDP solver plus a rounding heuristic: the paper's entire
    technical contribution is converting floating-point solver output into an
    exact solution.
  - Appendix A ("Two-point bounds", Tables LPbounds/LPbounds2) is the two-point
    specialisation this module implements.
  - What made it EASY: the optimum of the bound is a function of (n, d, s)
    alone.  A generator can plant a FEASIBLE certificate but not an OPTIMAL one,
    so the published bound B is always strictly loose, and the feasible set that
    verify() accepts is full-dimensional.  See REJECTED.md for the measured gap.

Standard library + gvlib only.  Exact rational arithmetic throughout; no float
appears anywhere in verify().
"""

import os
import sys
import time
from fractions import Fraction as F
from random import Random

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for _cand in (_REPO_ROOT, os.environ.get("GV_REPO_ROOT", "")):
    if _cand and _cand not in sys.path:
        sys.path.insert(0, _cand)
try:
    from gvlib import roots as rt
    from gvlib import rationals as rat
except ImportError:  # stay standard-library-only
    rt = rat = None

TRACK = "B"

SHIPPING_DIFFICULTY = "hard"

DIFFICULTY = {
    "demo":   dict(dim=8,  n_roots=1, use_minus_one=True,  den_max=4,  height_bits=24),
    "easy":   dict(dim=16, n_roots=2, use_minus_one=True,  den_max=6,  height_bits=48),
    "medium": dict(dim=24, n_roots=3, use_minus_one=True,  den_max=10, height_bits=96),
    "hard":   dict(dim=48, n_roots=4, use_minus_one=True,  den_max=14, height_bits=160),
}

STRUCTURAL_HINT = (
    "A polynomial that is non-positive on the whole interval and vanishes at "
    "interior points must vanish there to even order."
)
PLACEBO_HINT = (
    "A polynomial of this degree has many coefficients, so keep the bookkeeping "
    "of the indices straight as you work."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A Delsarte dual certificate written as the Gegenbauer coefficient vector "
        "(f_1, ..., f_d) of f(t) = 1 + sum_{k=1}^{d} f_k P_k^n(t), with f_0 = 1 "
        "fixed.  Each f_k is a non-negative rational num/den with |num| and den "
        "below 2^height_bits.  Order matters: entry k is the coefficient of "
        "P_k^n."
    ),
    "bounds": {"degree": None, "coeff_bits": None, "n_elements": None},
}

PROBLEM_PROFILE = {
    "native_domain": "optimization",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "rational",
    "native_objects": [
        "Gegenbauer polynomials P_k^n over Q",
        "a univariate polynomial f non-positive on [-1, cos theta]",
        "the Delsarte dual vector (f_0, ..., f_d) of a spherical-code LP bound",
    ],
    "verification_operations": [
        "exact rational evaluation of the Gegenbauer three-term recurrence",
        "exact rational sign comparison of the coefficients f_k",
        "Sturm-sequence real root isolation of f on [-1, s]",
        "exact rational sample-point sign test for non-positivity",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "duality",
    "intuition_description": (
        "Complementary slackness forces the dual polynomial to touch zero to even "
        "order at every inner product the code realises, so the certificate is a "
        "product of squares times one sign-carrying factor; a solver who does not "
        "see that must solve the semi-infinite linear program directly."
    ),
    "hardness_basis": (
        "REJECTED -- see REJECTED.md.  The bound proved by the certificate is a "
        "function of (n, d, s) alone, so the generator can plant only a feasible "
        "certificate, never a tight one, and the accepted set is full-dimensional."
    ),
    "max_answer_tokens": None,
}

NATIVE = {
    "domain": "optimization",
    "core": "linear_algebra",
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": " + PROBLEM_PROFILE["intuition_description"],
    "reduction": None,
}


# --------------------------------------------------------------------------
# exact univariate polynomial helpers (ascending coefficient lists over Q)
# --------------------------------------------------------------------------

def _polymul(a, b):
    r = [F(0)] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                r[i + j] += x * y
    return r


def _polyeval(p, x):
    r = F(0)
    for c in reversed(p):
        r = r * x + c
    return r


def gegenbauer(n, d):
    """P_0..P_d, Gegenbauer with parameter n/2-1, normalised P_k^n(1) = 1.

    Ascending rational coefficient lists.  Recurrence (Delsarte-Goethals-Seidel):
        (k + n - 2) P_{k+1}(t) = (2k + n - 2) t P_k(t) - k P_{k-1}(t).
    """
    P = [[F(1)]]
    if d >= 1:
        P.append([F(0), F(1)])
    for k in range(1, d):
        a = F(2 * k + n - 2, k + n - 2)
        b = F(k, k + n - 2)
        nxt = [F(0)] * (k + 2)
        for i, c in enumerate(P[k]):
            nxt[i + 1] += a * c
        for i, c in enumerate(P[k - 1]):
            nxt[i] -= b * c
        P.append(nxt)
    return P[: d + 1]


def _to_gegenbauer(f, P):
    """Monomial coefficients -> Gegenbauer coefficients (triangular back-substitution)."""
    f = list(f)
    out = [F(0)] * len(f)
    for k in range(len(f) - 1, -1, -1):
        c = f[k] / P[k][k]
        out[k] = c
        if c:
            for i, x in enumerate(P[k]):
                f[i] -= c * x
    return out


def _from_gegenbauer(g, P):
    out = [F(0)] * len(g)
    for k, c in enumerate(g):
        if c:
            for i, x in enumerate(P[k]):
                out[i] += c * x
    return out


def _squarefree_odd_part(p):
    """Product of the squarefree factors of p of ODD multiplicity (Yun).

    Exactly the factor whose roots are the points where p changes sign.  The
    result is squarefree, so Sturm counting applies to it directly.
    """
    p = rt.normalize(list(p))
    dp = rt.derivative(p)
    c = rt.gcd_poly(p, dp)
    w = rt.divmod_poly(p, c)[0]
    y = rt.divmod_poly(dp, c)[0]
    z = rt.normalize([y[i] - (rt.derivative(w)[i] if i < len(rt.derivative(w)) else F(0))
                      for i in range(max(len(y), len(rt.derivative(w))))])
    odd = [F(1)]
    i = 1
    while rt.degree(w) > 0:
        g = rt.gcd_poly(w, z)
        if i % 2 == 1 and rt.degree(g) > 0:
            odd = _polymul(odd, g)
        w = rt.divmod_poly(w, g)[0]
        y = rt.divmod_poly(z, g)[0]
        dw = rt.derivative(w)
        z = rt.normalize([(y[j] if j < len(y) else F(0)) - (dw[j] if j < len(dw) else F(0))
                          for j in range(max(len(y), len(dw), 1))])
        i += 1
        if i > 200:
            break
    return rt.normalize(odd)


def _deflate(p, r):
    """Divide out every factor (t - r) from p."""
    while rt.degree(p) > 0 and _polyeval(p, r) == 0:
        q, rem = rt.divmod_poly(p, [-r, F(1)])
        p = rt.normalize(q)
    return p


def _nonpositive_on(f, lo, hi):
    """Exact: is f(t) <= 0 for every real t in [lo, hi]?

    f changes sign exactly at its odd-multiplicity roots.  If the odd part has
    no root strictly inside (lo, hi), f has one sign there apart from isolated
    even-order zeros, so one interior non-root sample plus the two endpoints
    decides it.  Every comparison is a comparison of rationals; no floats.
    """
    if rt is None:
        raise RuntimeError("gvlib is required for exact verification")
    p = rt.normalize(list(f))
    if rt.degree(p) < 0:
        return True, "ok"
    if rt.degree(p) == 0:
        return (p[0] <= 0), ("ok" if p[0] <= 0 else "f is the positive constant %s" % (p[0],))
    if _polyeval(p, lo) > 0:
        return False, "f(%s) = %s > 0 at the left endpoint" % (lo, _polyeval(p, lo))
    if _polyeval(p, hi) > 0:
        return False, "f(%s) = %s > 0 at the right endpoint" % (hi, _polyeval(p, hi))
    odd = _squarefree_odd_part(p)
    odd = _deflate(_deflate(odd, lo), hi)
    if rt.degree(odd) > 0:
        cnt = rt.count_roots(odd, lo, hi)
        if cnt != 0:
            return False, "f changes sign %d time(s) strictly inside [-1, s]" % cnt
    probe = None
    d = rt.degree(p)
    for j in range(1, 2 * d + 4):
        x = lo + (hi - lo) * F(j, 2 * d + 4)
        if _polyeval(p, x) != 0:
            probe = x
            break
    if probe is None:
        return True, "ok"
    val = _polyeval(p, probe)
    if val > 0:
        return False, "f(%s) = %s > 0 inside the interval" % (probe, val)
    return True, "ok"


# --------------------------------------------------------------------------
# generation -- the certificate is planted first, never searched for
# --------------------------------------------------------------------------

def _sample_rational(rng, den_max, lo, hi):
    for _ in range(400):
        dn = rng.randint(2, den_max)
        num = rng.randint(-dn * 1 + 1, dn - 1)
        v = F(num, dn)
        if lo < v < hi:
            return v
    return None


def make_instance(seed=0, dim=16, n_roots=2, use_minus_one=True, den_max=6,
                  height_bits=48, **_ignored):
    """Plant the Delsarte dual certificate, then publish the instance around it.

    The certificate f(t) = (t+1)^e (t-s) prod_i (t-a_i)^2 is non-positive on
    [-1, s] BY CONSTRUCTION (each squared factor is >= 0 and (t-s) <= 0 there),
    so no search happens here: we only re-draw the root positions until the
    Gegenbauer coefficients happen to be non-negative, which is an O(d^2)
    property of the drawn roots, not of any instance.
    """
    rng = Random("2403.16874|%d|%d|%d|%d" % (seed, dim, n_roots, den_max))
    e = 1 if use_minus_one else 0
    for _attempt in range(4000):
        s = _sample_rational(rng, den_max, F(0), F(1))
        if s is None:
            continue
        aa = set()
        guard = 0
        while len(aa) < n_roots and guard < 200:
            guard += 1
            a = _sample_rational(rng, den_max, F(-1), s)
            if a is not None:
                aa.add(a)
        if len(aa) != n_roots:
            continue
        aa = sorted(aa)
        f = [F(1), F(1)] if e else [F(1)]
        for a in aa:
            f = _polymul(f, _polymul([-a, F(1)], [-a, F(1)]))
        f = _polymul(f, [-s, F(1)])
        d = len(f) - 1
        P = gegenbauer(dim, d)
        g = _to_gegenbauer(f, P)
        if g[0] <= 0:
            continue
        g = [x / g[0] for x in g]
        if not all(x >= 0 for x in g[1:]):
            continue
        if rat is not None and not all(rat.within_bits(x, height_bits) for x in g):
            continue
        bound = sum(g)                      # f(1) = sum_k f_k since P_k(1) = 1
        answer = [[x.numerator, x.denominator] for x in g[1:]]
        return {
            "dim": dim,
            "s": [s.numerator, s.denominator],
            "degree": d,
            "bound": [bound.numerator, bound.denominator],
            "n_roots": n_roots,
            "den_max": den_max,
            "height_bits": height_bits,
            "answer": answer,
            "_planted_roots": [[a.numerator, a.denominator] for a in aa],
        }
    raise RuntimeError("planting failed for %r" % ((seed, dim, n_roots, den_max),))


# --------------------------------------------------------------------------
# presentation
# --------------------------------------------------------------------------

def render(inst):
    n = inst["dim"]
    s = F(*inst["s"])
    d = inst["degree"]
    B = F(*inst["bound"])
    lines = []
    lines.append("Spherical codes and the Delsarte linear programming bound.")
    lines.append("")
    lines.append("Work on the unit sphere S^(n-1) in R^n with n = %d." % n)
    lines.append("Let P_0^n, P_1^n, P_2^n, ... be the Gegenbauer (ultraspherical) polynomials")
    lines.append("for dimension n, normalised by P_k^n(1) = 1 and generated by")
    lines.append("    P_0^n(t) = 1,   P_1^n(t) = t,")
    lines.append("    (k + n - 2) P_{k+1}^n(t) = (2k + n - 2) t P_k^n(t) - k P_{k-1}^n(t).")
    lines.append("All arithmetic below is exact arithmetic over the rational numbers.")
    lines.append("")
    lines.append("Let s = %s/%s." % (s.numerator, s.denominator))
    lines.append("A spherical code with maximal inner product at most s is a finite set C of")
    lines.append("unit vectors in R^n with <x,y> <= s for all distinct x, y in C.")
    lines.append("")
    lines.append("Delsarte's bound says: if f(t) = sum_{k=0}^{%d} f_k P_k^n(t) satisfies" % d)
    lines.append("    (i)   f_k >= 0 for every k = 1, ..., %d," % d)
    lines.append("    (ii)  f(t) <= 0 for EVERY real t in the closed interval [-1, s],")
    lines.append("    (iii) f_0 > 0,")
    lines.append("then every such code C obeys |C| <= f(1)/f_0.")
    lines.append("")
    lines.append("TASK.  Normalise f_0 = 1.  Produce rational numbers f_1, ..., f_%d such that" % d)
    lines.append("conditions (i) and (ii) hold for f(t) = 1 + sum_{k=1}^{%d} f_k P_k^n(t), and" % d)
    lines.append("such that the resulting bound satisfies")
    lines.append("    f(1) = 1 + f_1 + ... + f_%d  <=  %s/%s." % (d, B.numerator, B.denominator))
    lines.append("(Condition (ii) is a condition on the whole interval, not on sample points.)")
    lines.append("")
    lines.append("Give your final answer inside <answer></answer> tags, as the %d rationals" % d)
    lines.append("f_1, ..., f_%d in this order, comma separated, each written as num/den" % d)
    lines.append("(an integer on its own is allowed; write 0 as 0).")
    lines.append("Example for degree 3: <answer>1/2, 0, 7/4</answer>")
    lines.append("Output nothing else inside the tags.")
    out = "\n".join(lines)
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        out += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        out += "\n\nHint: " + PLACEBO_HINT
    return out


def parse_answer(text):
    if text is None:
        return None
    if not isinstance(text, str):
        try:
            return [[int(a), int(b)] for a, b in text]
        except Exception:
            return None
    body = text
    if "<answer>" in text and "</answer>" in text:
        body = text.split("<answer>", 1)[1].split("</answer>", 1)[0]
    body = body.replace("```", " ").replace("\n", " ").replace("[", " ").replace("]", " ")
    parts = [p.strip() for p in body.split(",")]
    parts = [p for p in parts if p]
    if not parts:
        return None
    out = []
    for p in parts:
        p = p.strip().strip("$").replace(" ", "")
        if rat is not None:
            v = rat.parse_rational(p)
        else:
            try:
                v = F(p)
            except Exception:
                v = None
        if v is None:
            return None
        out.append([v.numerator, v.denominator])
    return out


def verify(inst, answer):
    """Exact.  Accepts ANY valid Delsarte dual certificate, not only the plant."""
    n = inst["dim"]
    s = F(*inst["s"])
    d = inst["degree"]
    B = F(*inst["bound"])
    if not isinstance(answer, (list, tuple)):
        return False, "answer is not a list"
    if len(answer) != d:
        return False, "expected %d coefficients f_1..f_%d, got %d" % (d, d, len(answer))
    coeffs = []
    for item in answer:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            try:
                num, den = int(item[0]), int(item[1])
            except Exception:
                return False, "coefficient entry is not a rational [num, den]"
            if den == 0:
                return False, "coefficient has zero denominator"
            coeffs.append(F(num, den))
        elif isinstance(item, int):
            coeffs.append(F(item))
        else:
            return False, "coefficient entry is not a rational [num, den]"
    for k, c in enumerate(coeffs, start=1):
        if c < 0:
            return False, "f_%d = %s is negative, violating condition (i)" % (k, c)
    hb = inst.get("height_bits")
    if hb and rat is not None:
        for k, c in enumerate(coeffs, start=1):
            if not rat.within_bits(c, hb):
                return False, "f_%d exceeds the declared height bound of %d bits" % (k, hb)
    g = [F(1)] + coeffs
    total = sum(g)
    if total > B:
        return False, "f(1) = %s exceeds the published bound %s" % (total, B)
    P = gegenbauer(n, d)
    f = _from_gegenbauer(g, P)
    ok, why = _nonpositive_on(f, F(-1), s)
    if not ok:
        return False, "condition (ii) fails: " + why
    return True, "ok"


# --------------------------------------------------------------------------
# gate instrumentation
# --------------------------------------------------------------------------

def random_candidate(inst, rng):
    """Structure-aware: sample the SAME construction the plant uses -- a product
    of squares times (t+1)(t-s) -- with roots from the same grid, normalised so
    f_0 = 1.  This is exactly what an in-context solver who has seen the
    complementary-slackness ansatz would write down."""
    n = inst["dim"]
    s = F(*inst["s"])
    den_max = inst["den_max"]
    m = inst["n_roots"]
    d = inst["degree"]
    for _ in range(60):
        aa = set()
        guard = 0
        while len(aa) < m and guard < 200:
            guard += 1
            a = _sample_rational(rng, den_max, F(-1), s)
            if a is not None:
                aa.add(a)
        if len(aa) != m:
            continue
        f = [F(1), F(1)]
        for a in sorted(aa):
            f = _polymul(f, _polymul([-a, F(1)], [-a, F(1)]))
        f = _polymul(f, [-s, F(1)])
        if len(f) - 1 != d:
            continue
        P = gegenbauer(n, d)
        g = _to_gegenbauer(f, P)
        if g[0] == 0:
            continue
        g = [x / g[0] for x in g]
        return [[x.numerator, x.denominator] for x in g[1:]]
    return [[0, 1]] * d


def search_space(inst):
    return None      # a cone of rationals; genuinely uncountable, G5 uses density


def enumerate_all(inst):
    return None      # the accepted set is a full-dimensional cone: uncountable


def canonical_key(inst):
    s = F(*inst["s"])
    B = F(*inst["bound"])
    parts = ["n=%d" % inst["dim"], "d=%d" % inst["degree"],
             "s=%d/%d" % (s.numerator, s.denominator),
             "B=%d/%d" % (B.numerator, B.denominator)]
    return "|".join(parts)


def escalate(params):
    p = dict(params)
    moved = 0
    if p.get("den_max", 6) < 40:
        p["den_max"] = p["den_max"] + 6
        moved += 1
    if p.get("dim", 16) < 4096:
        p["dim"] = p["dim"] * 2
        moved += 1
    p["height_bits"] = p.get("height_bits", 48) * 2
    moved += 1
    if moved < 2:
        return "cap_bound"
    return p


# --------------------------------------------------------------------------
# the reference algorithm: the exact rational LP that the domain reaches for
# --------------------------------------------------------------------------

class _Ops(object):
    __slots__ = ("n",)

    def __init__(self):
        self.n = 0


def _simplex(A, b, c, ops, iter_cap=100000):
    """min c.x  s.t.  A x = b (b >= 0), x >= 0.  Exact two-phase, Bland's rule."""
    m, nv = len(A), len(A[0])
    T = [list(A[i]) + [F(1) if j == i else F(0) for j in range(m)] + [b[i]] for i in range(m)]
    basis = list(range(nv, nv + m))
    N = nv + m
    obj = [F(0)] * (N + 1)
    for i in range(m):
        for j in range(N + 1):
            obj[j] -= T[i][j]
    ops.n += m * (N + 1)
    for i in range(m):
        obj[nv + i] = F(0)

    def pivot(objv, r, cidx):
        p = T[r][cidx]
        T[r] = [x / p for x in T[r]]
        ops.n += len(T[r])
        for i in range(m):
            if i != r and T[i][cidx]:
                fct = T[i][cidx]
                T[i] = [T[i][j] - fct * T[r][j] for j in range(N + 1)]
                ops.n += 2 * (N + 1)
        if objv[cidx]:
            fct = objv[cidx]
            for j in range(N + 1):
                objv[j] -= fct * T[r][j]
            ops.n += 2 * (N + 1)
        basis[r] = cidx

    def run(objv, ncols):
        it = 0
        while True:
            it += 1
            if it > iter_cap:
                return False
            cidx = -1
            for j in range(ncols):
                if objv[j] < 0:
                    cidx = j
                    break
            if cidx < 0:
                return True
            r = -1
            best = None
            for i in range(m):
                if T[i][cidx] > 0:
                    ratio = T[i][-1] / T[i][cidx]
                    ops.n += 1
                    if best is None or ratio < best or (ratio == best and basis[i] < basis[r]):
                        best, r = ratio, i
            if r < 0:
                return True
            pivot(objv, r, cidx)

    if not run(obj, N):
        return None
    if obj[-1] != 0:
        return None
    for i in range(m):
        if basis[i] >= nv:
            for j in range(nv):
                if T[i][j] != 0:
                    pivot(obj, i, j)
                    break
    obj2 = [F(0)] * (N + 1)
    for j in range(nv):
        obj2[j] = c[j]
    for i in range(m):
        if basis[i] < nv and obj2[basis[i]]:
            fct = obj2[basis[i]]
            for j in range(N + 1):
                obj2[j] -= fct * T[i][j]
            ops.n += 2 * (N + 1)
    if not run(obj2, nv):
        return None
    x = [F(0)] * nv
    for i in range(m):
        if basis[i] < nv:
            x[basis[i]] = T[i][-1]
    return x


def reference_algorithm(inst, grid=40, rounds=6):
    """The domain-standard attack: solve the Delsarte LP exactly over Q by
    discretising [-1, s] and adding violated cutting planes until the continuous
    constraint holds.  Returns (answer_or_None, operations, seconds)."""
    n, d = inst["dim"], inst["degree"]
    s = F(*inst["s"])
    B = F(*inst["bound"])
    P = gegenbauer(n, d)
    ts = [F(-1) + (s + F(1)) * F(j, grid) for j in range(grid + 1)]
    ops = _Ops()
    t0 = time.time()
    ans = None
    for _rnd in range(rounds):
        rows, bb = [], []
        for t in ts:
            rows.append([-_polyeval(P[k], t) for k in range(1, d + 1)])
            bb.append(F(1))
            ops.n += d
        m = len(rows)
        A = [rows[i] + [F(-1) if j == i else F(0) for j in range(m)] for i in range(m)]
        c = [F(1)] * d + [F(0)] * m
        x = _simplex(A, bb, c, ops)
        if x is None:
            break
        cand = [[x[k].numerator, x[k].denominator] for k in range(d)]
        ok, why = verify(inst, cand)
        if ok:
            ans = cand
            break
        f = _from_gegenbauer([F(1)] + [x[k] for k in range(d)], P)
        bad = None
        for j in range(4 * grid + 1):
            t = F(-1) + (s + F(1)) * F(j, 4 * grid)
            if _polyeval(f, t) > 0:
                bad = t
                break
        if bad is None:
            break
        ts = sorted(set(ts + [bad]))
    return ans, ops.n, time.time() - t0


def compact_route(inst):
    """The route the family claims to test: complementary slackness fixes the
    shape f = c (t+1)(t-s) prod (t-a_i)^2, so given the root positions the
    certificate is one expansion plus one triangular basis change.  Counted in
    exact rational operations."""
    n, d = inst["dim"], inst["degree"]
    s = F(*inst["s"])
    aa = [F(*p) for p in inst["_planted_roots"]]
    ops = 0
    f = [F(1), F(1)]
    for a in aa:
        q = _polymul([-a, F(1)], [-a, F(1)])
        ops += 4
        nf = _polymul(f, q)
        ops += len(f) * len(q)
        f = nf
    nf = _polymul(f, [-s, F(1)])
    ops += 2 * len(f)
    f = nf
    P = gegenbauer(n, d)
    ops += 3 * d
    g = list(f)
    out = [F(0)] * len(g)
    for k in range(len(g) - 1, -1, -1):
        cc = g[k] / P[k][k]
        ops += 1
        out[k] = cc
        if cc:
            for i, x in enumerate(P[k]):
                g[i] -= cc * x
                ops += 2
    scale = out[0]
    out = [x / scale for x in out]
    ops += len(out)
    return [[x.numerator, x.denominator] for x in out[1:]], ops


def in_context_sweep(inst, grid=12):
    """The attack a solver can actually run in context, without tools: assume all
    the double roots coincide, f = (t+1)(t-s)(t-a)^{2m}, and sweep the single
    rational parameter a over a coarse grid.  Returns (answer_or_None, ops)."""
    n, d, m = inst["dim"], inst["degree"], inst["n_roots"]
    s = F(*inst["s"])
    ops = 0
    for j in range(1, grid):
        a = F(-1) + (s + F(1)) * F(j, grid)
        f = [F(1), F(1)]
        for _ in range(m):
            f = _polymul(f, _polymul([-a, F(1)], [-a, F(1)]))
            ops += 3 * len(f)
        f = _polymul(f, [-s, F(1)])
        ops += 2 * len(f)
        P = gegenbauer(n, d)
        ops += 3 * d
        g = _to_gegenbauer(f, P)
        ops += d * d
        if g[0] <= 0:
            continue
        g = [x / g[0] for x in g]
        ops += len(g)
        cand = [[x.numerator, x.denominator] for x in g[1:]]
        ok, _why = verify(inst, cand)
        if ok:
            return cand, ops
    return None, ops


def selftest(seeds=8):
    """Reproduces the measurements the rejection rests on.  See REJECTED.md."""
    import random as _random
    rep = {"track": TRACK, "verdict": "REJECTED (H, on both tracks)"}
    g1 = {"ok": 0, "total": 0}
    caps = {}
    for name, p in DIFFICULTY.items():
        ch, at = [], []
        for sd in range(seeds):
            inst = make_instance(seed=1000 + sd, **p)
            ok, _ = verify(inst, inst["answer"])
            g1["ok"] += bool(ok)
            g1["total"] += 1
            ch.append(len(",".join("%d/%d" % (a, b) for a, b in inst["answer"])))
            at.append(2 * len(inst["answer"]))
        caps[name] = {"answer_chars_max": max(ch), "answer_atoms": max(at)}
    rep["G1_planted_verifies"] = dict(g1, **{"pass": g1["ok"] == g1["total"]})
    rep["answer_caps"] = caps
    dens, sweep, route = {}, {}, {}
    for name in ("easy", "medium", "hard"):
        p = DIFFICULTY[name]
        hits = tot = 0
        for sd in range(seeds):
            inst = make_instance(seed=100 + sd, **p)
            rng = _random.Random(9000 + sd)
            for _ in range(100):
                ok, _ = verify(inst, random_candidate(inst, rng))
                hits += bool(ok)
                tot += 1
        dens[name] = {"hits": hits, "trials": tot, "density": hits / float(tot)}
        sv = 0
        ops = []
        for sd in range(seeds):
            inst = make_instance(seed=200 + sd, **p)
            a, o = in_context_sweep(inst)
            sv += a is not None
            ops.append(o)
        sweep[name] = {"successes": sv, "attempts": seeds,
                       "median_ops": sorted(ops)[len(ops) // 2]}
        ro = []
        for sd in range(seeds):
            inst = make_instance(seed=500 + sd, **p)
            _a, o = compact_route(inst)
            ro.append(o)
        route[name] = sorted(ro)[len(ro) // 2]
    rep["G4_guess_resistance"] = {"structure_aware": dens,
                                  "pass": all(d["density"] < 1e-6 for d in dens.values())}
    rep["in_context_sweep_attack"] = sweep
    rep["compact_route_operations"] = route
    return rep
