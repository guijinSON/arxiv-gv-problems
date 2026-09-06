"""Constant-dimension subspace codes: extending a lifted MRD code by a spread plane.

Paper: arXiv:1905.11021, A. Cossidente, F. Pavese, "Subspace code constructions"
(math.CO / cs.IT).  The paper improves the lower bound on A_q(9,4;3), the maximum
number of planes of PG(8,q) mutually intersecting in at most one point, and (Sec. 3)
constructs (6,(q^3-1)(q^2+q+1),4;3)_q orbit codes of planes of PG(5,q).

The family built here lives in the paper's PG(5,q) setting and in the lifted-MRD
code of size q^6 that the paper's introduction cites as the standard lower bound
A_q(6,4;3) >= q^{(n-k)(k-delta+1)} = q^6 (Silva-Kschischang-Koetter).

Objects.  L = GF(q^3) over K = GF(q).  For b,c in L the set
    W(b,c) = { (y, b*y + c*y^q) : y in L }  <  L x L = K^6
is a plane of PG(5,q); the q^6 planes W(b,c) are the lifting of the Gabidulin MRD
code {b*x + c*x^q} and pairwise meet in at most one point.  The sub-family
    U(a) = W(a,0) = { (y, a*y) : y in L }
is the Desarguesian spread: q^3 pairwise disjoint planes.

Task.  Given m planes W(b_i,c_i) with c_i != 0, find a in L with
dim_K(U(a) ∩ W(b_i,c_i)) = 1 for every i -- a spread plane meeting every given
codeword, i.e. a codeword that may be adjoined to the given code while every
pairwise intersection is a single point.

Why it is generatable.  Plant a first.  U(a) meets W(b,c) exactly when the
q-linearised polynomial (a-b)y - c*y^q has a nonzero root, i.e. when
N(a-b) = N(c) with N the norm of L over K.  So sample c, then sample z uniformly
from the norm fibre N^{-1}(N(c)), and set b = a - z.  No search.

Why it is hard without the insight (TRACK B).  Nothing in the statement mentions
norms.  A solver who does not see the norm criterion is left enumerating a in L
(q^3 candidates, each needing a 6x6 rank computation over K).  A solver who does
see it gets a linear system: N(x-b) expands as

  N(a-b) = N(a) - 3[b0*P(a) + r*b2*Q(a) + r*b1*R(a)]
                + 3[P(b)*a0 + r*R(b)*a1 + r*Q(b)*a2] - N(b)

with P(x)=x0^2-r*x1*x2, Q(x)=r*x2^2-x0*x1, R(x)=x1^2-x0*x2 (the coordinates of
x^{q+1}), so every constraint is K-LINEAR in the seven unknowns
(N(a), P(a), Q(a), R(a), a0, a1, a2) and a falls out of one small solve.

NOTES
-----
* Section 1 (Introduction) fixed the definition: an (n,M,2d;k)_q constant-dimension
  code is a set of (k-1)-spaces of PG(n-1,q) pairwise meeting in at most a
  (k-d-1)-space; for k=3, d=2 that is "planes pairwise meeting in at most a point".
  It also cites [SKK] for A_q(n,2d;k) >= q^{(n-k)(k-d+1)}, the lifted-MRD bound whose
  k=3,n=6 case is the code used here.
* Section 2 / Constructions 2.1-2.3 build the PG(5,q) families the PG(8,q) bound is
  assembled from; Section 3 constructs orbit codes of planes of PG(5,q) under a group
  of order (q^3-1)(q^2+q+1) -- the Singer structure of L* that also drives the norm
  criterion used here.
* What makes it EASY, and had to be steered around: (i) with m <= 3 given planes the
  answer can be written down with no arithmetic at all -- pick any three independent
  y_i and solve y_i*X = y_i*B_i, so m must exceed 3 by a margin; (ii) rank-ONE
  perturbations (the first design tried) are broken outright: see `attack_colspace`
  below and REJECTED-variant notes in the README, column spaces of the published
  differences intersect in the planted rank-1 factor and give a in O(k^3);
  (iii) the number of constraints must reach 7 or the linearisation is
  underdetermined, but must not be so large that the instance is redundant.
"""

from __future__ import annotations

import random
from typing import Optional

# --------------------------------------------------------------------------
# declarations
# --------------------------------------------------------------------------

TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "geometry",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "planes of PG(5,q) as 3-dimensional GF(q)-subspaces of GF(q^3) x GF(q^3)",
        "q-linearised polynomials over GF(q^3)",
    ],
    "verification_operations": [
        "exact GF(q) Gaussian elimination on a 6x6 matrix",
        "subspace intersection dimension via rank",
        "GF(q^3) arithmetic modulo t^3 - r",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Two lifted planes meet exactly when the difference of their constant "
        "coefficients has the same GF(q)-norm as the Frobenius coefficient, and the "
        "norm form linearises in the coordinates of x^{q+1}; a solver without this "
        "must enumerate GF(q^3) and run a 6x6 rank computation per candidate."
    ),
    "hardness_basis": (
        "TRACK B.  The efficient algorithm exists and is named: expand N(a-b_i)=N(c_i) "
        "in the GF(q)-unknowns (N(a),P(a),Q(a),R(a),a0,a1,a2), translate so b_1=0, and "
        "solve one 6x6 linear system -- O(m + k^3) field operations, MEASURED at 343 "
        "GF(q) operations and 3.0e-4 s, recovering the planted a on 30/30 shipping "
        "instances.  The mechanical route for a solver who does not see the norm "
        "criterion is enumeration of GF(q^3): MEASURED 1,835,595 candidates/s and 11.0 "
        "field ops per candidate, so q^3 = 1.03e9 candidates = 1.13e10 field operations "
        "and 9.3 minutes at the shipping preset q=1009, m=7.  The intermediate route "
        "(norm criterion seen, linearisation not) walks the q^2+q+1 norm fibre: MEASURED "
        "656,974 candidates, 7.24e6 ops, 2.03 s.  None of the three is executable in "
        "context without tools, but only the first is short enough to write down."
    ),
    "max_answer_tokens": 16,
}

NATIVE: dict = {
    "domain": "geometry",
    "core": "linear_algebra",
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": " +
        PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": None,
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "One element a of GF(q^3), written as three integers a0,a1,a2 in [0,q) "
        "meaning a0 + a1*t + a2*t^2 modulo t^3 - r."
    ),
    "bounds": {"field_elements": 1, "coordinates": 3, "coordinate_range": "q"},
}

# each preset: q must be a prime = 1 (mod 3) and > 3;  m = number of given planes
DIFFICULTY: dict = {
    "demo":   {"q": 13,   "m": 8},
    "easy":   {"q": 127,  "m": 8},
    "medium": {"q": 307,  "m": 8},
    "hard":   {"q": 1009, "m": 7},
}

SHIPPING_DIFFICULTY: str = "hard"

STRUCTURAL_HINT: str = (
    "Whether U(a) meets W(b,c) depends on a - b only through its norm to GF(q)."
)

PLACEBO_HINT: str = (
    "Keeping the coefficient triples lined up carefully is what this problem rewards."
)

# --------------------------------------------------------------------------
# GF(q) and GF(q^3) = GF(q)[t]/(t^3 - r)
# --------------------------------------------------------------------------


def _is_prime(v: int) -> bool:
    if v < 2:
        return False
    if v % 2 == 0:
        return v == 2
    d = 3
    while d * d <= v:
        if v % d == 0:
            return False
        d += 2
    return True


def _next_good_prime(v: int) -> int:
    """Smallest prime > v congruent to 1 mod 3 (so t^3 - r can be irreducible)."""
    c = v + 1
    while True:
        if c % 3 == 1 and _is_prime(c):
            return c
        c += 1


def _field(q: int) -> dict:
    """r = least non-cube in GF(q)*, w = a primitive cube root of unity."""
    if not (_is_prime(q) and q > 3 and q % 3 == 1):
        raise ValueError("q must be a prime > 3 with q = 1 (mod 3)")
    cubes = {pow(x, 3, q) for x in range(q)}
    r = next(x for x in range(2, q) if x not in cubes)
    w = pow(r, (q - 1) // 3, q)
    return {"q": q, "r": r, "w": w}


def _add(x, y, q):
    return ((x[0] + y[0]) % q, (x[1] + y[1]) % q, (x[2] + y[2]) % q)


def _sub(x, y, q):
    return ((x[0] - y[0]) % q, (x[1] - y[1]) % q, (x[2] - y[2]) % q)


def _mul(x, y, q, r):
    x0, x1, x2 = x
    y0, y1, y2 = y
    return ((x0 * y0 + r * (x1 * y2 + x2 * y1)) % q,
            (x0 * y1 + x1 * y0 + r * x2 * y2) % q,
            (x0 * y2 + x1 * y1 + x2 * y0) % q)


def _scal(lam, x, q):
    return (lam * x[0] % q, lam * x[1] % q, lam * x[2] % q)


def _frob(x, q, w):
    """x -> x^q, which on t^3 = r is the coordinate twist by omega."""
    return (x[0], x[1] * w % q, x[2] * w * w % q)


def _norm(x, q, r):
    """N_{L/K}(x) = x0^3 + r*x1^3 + r^2*x2^3 - 3*r*x0*x1*x2."""
    x0, x1, x2 = x
    return (x0 * x0 * x0 + r * x1 * x1 * x1 + r * r * x2 * x2 * x2
            - 3 * r * x0 * x1 * x2) % q


def _pqr(x, q, r):
    """Coordinates of x^{q+1} up to the fixed omega twists: the quadratic invariants."""
    x0, x1, x2 = x
    return ((x0 * x0 - r * x1 * x2) % q,
            (r * x2 * x2 - x0 * x1) % q,
            (x1 * x1 - x0 * x2) % q)


def _inv(x, q, r, w):
    """x^{-1} = x^{q} * x^{q^2} / N(x)."""
    n = _norm(x, q, r)
    if n == 0:
        raise ZeroDivisionError("zero element of GF(q^3)")
    xq = _frob(x, q, w)
    xq2 = _frob(xq, q, w)
    num = _mul(xq, xq2, q, r)
    return _scal(pow(n, q - 2, q), num, q)


# --------------------------------------------------------------------------
# planes of PG(5,q) and exact subspace intersection
# --------------------------------------------------------------------------


def _plane_rows(b, c, q, r, w) -> list:
    """3x6 generator matrix over GF(q) of W(b,c) = {(y, b*y + c*y^q)}."""
    rows = []
    for j in range(3):
        e = [0, 0, 0]
        e[j] = 1
        e = tuple(e)
        img = _add(_mul(b, e, q, r), _mul(c, _frob(e, q, w), q, r), q)
        rows.append(list(e) + list(img))
    return rows


def _rank(rows, q) -> int:
    mat = [list(row) for row in rows]
    nrow, ncol = len(mat), len(mat[0])
    rk = 0
    for col in range(ncol):
        piv = None
        for i in range(rk, nrow):
            if mat[i][col] % q:
                piv = i
                break
        if piv is None:
            continue
        mat[rk], mat[piv] = mat[piv], mat[rk]
        inv = pow(mat[rk][col], q - 2, q)
        mat[rk] = [v * inv % q for v in mat[rk]]
        for i in range(nrow):
            if i != rk and mat[i][col] % q:
                f = mat[i][col]
                mat[i] = [(mat[i][j] - f * mat[rk][j]) % q for j in range(ncol)]
        rk += 1
        if rk == nrow:
            break
    return rk


def _meet_dim(rows_a, rows_b, q) -> int:
    return 3 + 3 - _rank(rows_a + rows_b, q)


# --------------------------------------------------------------------------
# uniform sampling from a norm fibre  (inverse generation -- no search)
# --------------------------------------------------------------------------


def _cube_root_table(q: int) -> dict:
    tab: dict = {}
    for x in range(1, q):
        tab.setdefault(pow(x, 3, q), []).append(x)
    return tab


def _sample_norm_fibre(target: int, rng, F, cbrt) -> tuple:
    """Uniform element z of GF(q^3) with N(z) = target != 0.

    Pick a uniform nonzero z0, then rescale: N(lam*z0) = lam^3*N(z0), so lam must be
    a cube root of target/N(z0).  Exactly a third of the directions admit one and
    each admits three, so the accepted z is uniform on the fibre.
    """
    q, r = F["q"], F["r"]
    while True:
        z0 = (rng.randrange(q), rng.randrange(q), rng.randrange(q))
        if z0 == (0, 0, 0):
            continue
        n0 = _norm(z0, q, r)
        need = target * pow(n0, q - 2, q) % q
        roots = cbrt.get(need)
        if not roots:
            continue
        return _scal(rng.choice(roots), z0, q)


def _enumerate_norm_fibre(target: int, F, cbrt) -> list:
    """All q^2+q+1 elements z with N(z) = target != 0, via projective directions."""
    q, r = F["q"], F["r"]
    out = []
    reps = [(1, y, z) for y in range(q) for z in range(q)]
    reps += [(0, 1, z) for z in range(q)]
    reps.append((0, 0, 1))
    for z0 in reps:
        n0 = _norm(z0, q, r)
        need = target * pow(n0, q - 2, q) % q
        for lam in cbrt.get(need, ()):
            out.append(_scal(lam, z0, q))
    return out


# --------------------------------------------------------------------------
# instance construction
# --------------------------------------------------------------------------


def _linearisation_rank(planes, F) -> int:
    """Rank of the 7-unknown linear system the compact route solves."""
    q, r = F["q"], F["r"]
    rows = []
    for (b, _c) in planes:
        Pb, Qb, Rb = _pqr(b, q, r)
        rows.append([1, (-3 * b[0]) % q, (-3 * r * b[2]) % q, (-3 * r * b[1]) % q,
                     3 * Pb % q, 3 * r * Rb % q, 3 * r * Qb % q])
    return _rank(rows, q)


def make_instance(seed: int = 0, *, q: int = 1009, m: int = 7,
                  n: Optional[int] = None, **_) -> dict:
    """Plant a, then build m planes that a meets.  Never searches for a.

    `n`, when given, selects q from a ladder instead (house-harness compatibility);
    larger n is strictly harder.
    """
    if n is not None:
        q = _next_good_prime(max(12, 12 * (2 ** int(n))))
    F = _field(q)
    r, w = F["r"], F["w"]
    rng = random.Random("1905.11021|%d|%d|%d" % (int(seed), q, m))
    cbrt = _cube_root_table(q)

    for _attempt in range(200):
        a = (rng.randrange(q), rng.randrange(q), rng.randrange(q))
        planes = []
        seen = set()
        guard = 0
        while len(planes) < m and guard < 400 * m:
            guard += 1
            c = (rng.randrange(q), rng.randrange(q), rng.randrange(q))
            if c == (0, 0, 0):
                continue
            z = _sample_norm_fibre(_norm(c, q, r), rng, F, cbrt)
            b = _sub(a, z, q)
            if (b, c) in seen:
                continue
            seen.add((b, c))
            planes.append((b, c))
        if len(planes) < m:
            continue
        # Well-formedness only -- the answer is already fixed, nothing is searched
        # for here.  The published planes must carry as much linear information as
        # m planes can: rank min(m,7) in the 7-unknown system.  (At m = 7 that makes
        # the compact route determined; at m = 6 it is deliberately one short, which
        # is what the last rung of escalate() trades on.)
        if _linearisation_rank(planes, F) < min(m, 7):
            continue
        order = list(range(m))
        rng.shuffle(order)
        planes = [planes[i] for i in order]
        return {
            "q": q, "r": r, "omega": w, "m": m,
            "planes": [[list(b), list(c)] for (b, c) in planes],
            "answer": list(a),
        }
    raise RuntimeError("instance construction failed")


# --------------------------------------------------------------------------
# statement
# --------------------------------------------------------------------------


def _fmt(x) -> str:
    return "(%d,%d,%d)" % (x[0], x[1], x[2])


def render(inst: dict) -> str:
    import os
    q, r, m = inst["q"], inst["r"], inst["m"]
    lines = []
    A = lines.append
    A("Work over the finite field K = GF(%d) (the integers modulo %d) and its cubic"
      % (q, q))
    A("extension L = GF(%d^3), realised as L = K[t]/(t^3 - %d)." % (q, r))
    A("An element of L is written as a triple (x0,x1,x2) standing for")
    A("x0 + x1*t + x2*t^2; all arithmetic is modulo t^3 - %d and modulo %d."
      % (r, q))
    A("(t^3 - %d is irreducible over K, so L really is a field.)" % r)
    A("")
    A("Let V = L x L, a 6-dimensional vector space over K; the 3-dimensional")
    A("K-subspaces of V are the planes of PG(5,%d)." % q)
    A("Write y -> y^%d for the Frobenius map of L over K." % q)
    A("")
    A("For b, c in L put")
    A("    W(b,c) = { (y, b*y + c*y^%d) : y in L }," % q)
    A("and for a in L put")
    A("    U(a)   = { (y, a*y) : y in L }.")
    A("Each of these is a 3-dimensional K-subspace of V, i.e. a plane of PG(5,%d)."
      % q)
    A("")
    A("You are given the following %d planes W(b_i, c_i), each printed as the pair"
      % m)
    A("b_i then c_i:")
    A("")
    for i, (b, c) in enumerate(inst["planes"], 1):
        A("  i=%2d   b=%s   c=%s" % (i, _fmt(b), _fmt(c)))
    A("")
    A("TASK.  Find a in L such that U(a) meets every one of the %d given planes:" % m)
    A("for each i the intersection U(a) ∩ W(b_i,c_i) must have K-dimension exactly 1,")
    A("that is, the two planes must share exactly one point of PG(5,%d)." % q)
    A("At least one such a exists.")
    A("")
    A("Conventions, so that nothing is ambiguous:")
    A("  * coordinates are integers reduced into the range 0..%d;" % (q - 1))
    A("  * dimension means dimension over K = GF(%d), not over L;" % q)
    A("  * the order in which the planes are listed is irrelevant;")
    A("  * every given c_i is nonzero, so no given plane is of the form U(.);")
    A("  * a = (0,0,0) is allowed as an answer if it happens to work.")
    A("")
    A("Give your final answer inside <answer></answer> tags, as the three")
    A("coordinates of a separated by commas, in the order a0,a1,a2.")
    A("Example: <answer>17,0,42</answer>")
    A("Output nothing else inside the tags.")
    text = "\n".join(lines)
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


# --------------------------------------------------------------------------
# parsing and verification
# --------------------------------------------------------------------------


def parse_answer(text) -> Optional[list]:
    if text is None:
        return None
    if isinstance(text, (list, tuple)):
        vals = list(text)
        if len(vals) == 3 and all(isinstance(v, int) for v in vals):
            return [int(v) for v in vals]
        return None
    if not isinstance(text, str):
        return None
    lo = text.rfind("<answer>")
    if lo == -1:
        return None
    hi = text.find("</answer>", lo)
    body = text[lo + 8: hi if hi != -1 else len(text)]
    body = body.replace("`", " ").replace("(", " ").replace(")", " ")
    body = body.replace("[", " ").replace("]", " ").replace(",", " ")
    body = body.replace(";", " ").replace("\n", " ")
    toks = body.split()
    vals = []
    for tok in toks:
        tok = tok.strip()
        try:
            vals.append(int(tok))
        except ValueError:
            return None
    if len(vals) != 3:
        return None
    return vals


def verify(inst: dict, answer) -> tuple:
    """Exact, native check: build the planes over GF(q) and intersect them."""
    q, r, w = inst["q"], inst["r"], inst["omega"]
    if isinstance(answer, str):
        answer = parse_answer(answer)
    if answer is None:
        return (False, "no answer parsed")
    if isinstance(answer, tuple):
        answer = list(answer)
    if not isinstance(answer, list) or len(answer) != 3:
        return (False, "answer must be exactly 3 coordinates")
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in answer):
        return (False, "coordinates must be integers")
    if any(v < 0 or v >= q for v in answer):
        return (False, "coordinate outside the range 0..%d" % (q - 1))
    a = (answer[0], answer[1], answer[2])
    ua = _plane_rows(a, (0, 0, 0), q, r, w)
    if _rank(ua, q) != 3:
        return (False, "U(a) is not a plane")
    for i, (b, c) in enumerate(inst["planes"], 1):
        b = tuple(b)
        c = tuple(c)
        d = _meet_dim(ua, _plane_rows(b, c, q, r, w), q)
        if d != 1:
            return (False,
                    "plane %d meets U(a) in dimension %d, not 1" % (i, d))
    return (True, "ok")


# --------------------------------------------------------------------------
# house-style accessories
# --------------------------------------------------------------------------


def random_candidate(inst: dict, rng: random.Random) -> list:
    """A structure-aware guess: every constraint a solver can read off the
    statement is already satisfied (an element of L in range) -- there is no
    further freely-deducible constraint on a."""
    q = inst["q"]
    return [rng.randrange(q), rng.randrange(q), rng.randrange(q)]


def search_space(inst: dict) -> int:
    return inst["q"] ** 3


def enumerate_all(inst: dict, cap: int = 4000) -> Optional[int]:
    """Exact number of valid a.  Uses the norm fibre of the first constraint when
    q^3 is too large to walk, which is still exact (every solution lies in it)."""
    q, r, w = inst["q"], inst["r"], inst["omega"]
    planes = [(tuple(b), tuple(c)) for b, c in inst["planes"]]
    if q ** 3 <= 2_000_000:
        count = 0
        for a0 in range(q):
            for a1 in range(q):
                for a2 in range(q):
                    a = (a0, a1, a2)
                    ok = True
                    for (b, c) in planes:
                        if _norm(_sub(a, b, q), q, r) != _norm(c, q, r):
                            ok = False
                            break
                    if ok:
                        count += 1
        return count
    if q > cap:
        return None
    cbrt = _cube_root_table(q)
    b1, c1 = planes[0]
    target = _norm(c1, q, r)
    count = 0
    for z in _enumerate_norm_fibre(target, {"q": q, "r": r}, cbrt):
        a = _add(b1, z, q)
        ok = True
        for (b, c) in planes[1:]:
            if _norm(_sub(a, b, q), q, r) != _norm(c, q, r):
                ok = False
                break
        if ok:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Invariant under the symmetries that preserve the problem:
    translation of every b_i by a common s (with a -> a+s), the collineations
    (y,z)->(y, lam*z) and (y,z)->(mu*y, z), the Frobenius, and reordering the
    planes.  (N(b_i - b_j)/N(c_k))^2 is fixed by all of them -- the square is what
    makes it independent of which way round the pair is taken, since N(-d) = -N(d)
    in odd characteristic."""
    import hashlib
    q, r = inst["q"], inst["r"]
    planes = [(tuple(b), tuple(c)) for b, c in inst["planes"]]
    ncs = [_norm(c, q, r) for (_b, c) in planes]
    vals = []
    for i in range(len(planes)):
        for j in range(i + 1, len(planes)):
            nd = _norm(_sub(planes[i][0], planes[j][0], q), q, r)
            for nc in ncs:
                ratio = nd * pow(nc, q - 2, q) % q
                vals.append(ratio * ratio % q)
    vals.sort()
    payload = "%d|%d|%d|%s" % (q, r, len(planes), ",".join(map(str, vals)))
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def escalate(params: dict) -> object:
    """Harder parameters at FIXED answer length (always three GF(q) coordinates).

    Two axes, both leaving the answer three atoms long:
      * q -- the ambient field, so the haystack q^3 grows while the needle does not;
      * m -- the number of published planes, decreasing: fewer clues, and below
        seven the linearisation is no longer determined and the compact route has
        to be finished with the quadratic relations.
    """
    q = int(params.get("q", 1009))
    m = int(params.get("m", 7))
    if q >= 10 ** 7:
        return "cap_bound"
    new_q = _next_good_prime(int(q * 3.2))
    new_m = m - 1 if m > 6 else 6
    if new_m == m and new_q == q:
        return None
    return {"q": new_q, "m": new_m}


# --------------------------------------------------------------------------
# the compact route -- the thing the family claims to test.  Kept in the module
# so that its cost is measured against the shipped instances, not a sketch.
# --------------------------------------------------------------------------


def _solve_linear(rows, rhs, q):
    ncol = len(rows[0])
    aug = [list(row) + [rhs[i]] for i, row in enumerate(rows)]
    piv = []
    rk = 0
    for c in range(ncol):
        p = None
        for i in range(rk, len(aug)):
            if aug[i][c] % q:
                p = i
                break
        if p is None:
            continue
        aug[rk], aug[p] = aug[p], aug[rk]
        inv = pow(aug[rk][c], q - 2, q)
        aug[rk] = [v * inv % q for v in aug[rk]]
        for i in range(len(aug)):
            if i != rk and aug[i][c] % q:
                f = aug[i][c]
                aug[i] = [(aug[i][j] - f * aug[rk][j]) % q for j in range(ncol + 1)]
        piv.append(c)
        rk += 1
    if rk < ncol:
        return None
    out = [0] * ncol
    for i, c in enumerate(piv):
        out[c] = aug[i][ncol]
    return out


def compact_route(inst: dict) -> tuple:
    """Translate so b_1 = 0, then solve the 6x6 linearisation.  Returns (a, ops).

    ops counts every GF(q) multiplication, division, addition and subtraction.
    """
    q, r = inst["q"], inst["r"]
    cons = [(tuple(b), _norm(tuple(c), q, r)) for b, c in inst["planes"]]
    b1, c1 = cons[0]
    rows, rhs, ops = [], [], 0
    for (b, c) in cons[1:7]:
        d = _sub(b, b1, q)
        ops += 3
        Pd, Qd, Rd = _pqr(d, q, r)
        ops += 8
        Nd = (d[0] * Pd + r * d[2] * Qd + r * d[1] * Rd) % q
        ops += 6
        rows.append([d[0], d[2], d[1], Pd, Rd, Qd])   # constants folded into unknowns
        rhs.append((c + Nd - c1) % q)
        ops += 2
    if len(rows) < 6:
        return None, ops
    ops += 85 * 2 + 15 + 15 * 2 + 6                   # elimination + back substitution
    sol = _solve_linear(rows, rhs, q)
    if sol is None:
        return None, ops
    i3 = pow(3, q - 2, q)
    ir = pow(r, q - 2, q)
    a = _add((sol[3] * i3 % q, sol[4] * i3 % q * ir % q, sol[5] * i3 % q * ir % q),
             b1, q)
    ops += 8
    return a, ops


def mechanical_route(inst: dict, budget: Optional[int] = None) -> tuple:
    """Enumerate GF(q^3) with no insight at all.  Returns (a, candidates, ops)."""
    q, r = inst["q"], inst["r"]
    cons = [(tuple(b), _norm(tuple(c), q, r)) for b, c in inst["planes"]]
    ops = 0
    tried = 0
    for a0 in range(q):
        for a1 in range(q):
            for a2 in range(q):
                a = (a0, a1, a2)
                tried += 1
                good = True
                for (b, c) in cons:
                    ops += 11
                    if _norm(_sub(a, b, q), q, r) != c:
                        good = False
                        break
                if good:
                    return a, tried, ops
                if budget and tried >= budget:
                    return None, tried, ops
    return None, tried, ops


# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------


def selftest(seeds: int = 20, full: bool = False) -> dict:
    """Every gate with the number that shows it.  `full=True` adds the slow
    exact-density and exhaustive-search measurements."""
    import time
    report: dict = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}
    ship = DIFFICULTY[SHIPPING_DIFFICULTY]

    # G1 -------------------------------------------------------------------
    g1 = {}
    total = good = 0
    for name, p in DIFFICULTY.items():
        n_ok = 0
        for s in range(seeds):
            inst = make_instance(seed=s, **p)
            n_ok += verify(inst, inst["answer"])[0]
        g1[name] = {"ok": n_ok, "attempts": seeds}
        total += seeds
        good += n_ok
    report["G1_planted_verifies"] = {"pass": good == total, "per_preset": g1,
                                     "ok": good, "attempts": total}

    # G2 -------------------------------------------------------------------
    inst = make_instance(seed=5, **ship)
    a = inst["answer"]
    q = inst["q"]
    corruptions = {
        "perturb_one": [(a[0] + 1) % q, a[1], a[2]],
        "swap_two": [a[1], a[0], a[2]],
        "drop_one": [a[0], a[1]],
        "empty": [],
        "out_of_range": [a[0], a[1], q + 3],
        "negative": [-1, a[1], a[2]],
        "non_integer": [a[0], a[1], "x"],
    }
    g2 = {k: verify(inst, v)[1] for k, v in corruptions.items()}
    report["G2_rejects_corruption"] = {
        "pass": all(not verify(inst, v)[0] for v in corruptions.values()),
        "distinct_reasons": len(set(g2.values())), "reasons": g2}

    # G3 -------------------------------------------------------------------
    reply = ("Working in GF(%d^3) I linearise the norm conditions and get\n"
             "a = %d + %d t + %d t^2.\n\n<answer>%d, %d, %d</answer>\nDone."
             % (q, a[0], a[1], a[2], a[0], a[1], a[2]))
    report["G3_round_trip"] = {
        "pass": parse_answer(reply) == a and parse_answer("junk") is None,
        "parsed": parse_answer(reply)}

    # G4 -------------------------------------------------------------------
    rng = random.Random(4)
    hits = 0
    samples = 200_000
    cons = [(tuple(b), _norm(tuple(c), q, ship["q"] and inst["r"]))
            for b, c in inst["planes"]]
    r = inst["r"]
    for _ in range(samples):
        cand = tuple(random_candidate(inst, rng))
        if all(_norm(_sub(cand, b, q), q, r) == c for b, c in cons):
            hits += 1
    exact = enumerate_all(inst)
    report["G4_guess_resistance"] = {
        "pass": (exact / q ** 3) < 1e-6, "hits": hits, "samples": samples,
        "exact_valid_answers": exact, "search_space": q ** 3,
        "p_guess": exact / q ** 3}

    # G5 -------------------------------------------------------------------
    t0 = time.time()
    got, ops = compact_route(inst)
    dt = time.time() - t0
    _, tried, mops = mechanical_route(inst, budget=200_000)
    report["G5_density_and_baseline"] = {
        "exact_solution_count_at_shipping_preset": exact,
        "density": exact / q ** 3,
        "compact_route_ops": ops, "compact_route_sec": dt,
        "compact_route_correct": got == tuple(a),
        "mechanical_ops_per_candidate": mops / tried,
        "mechanical_candidates_full_sweep": q ** 3,
        "mechanical_ops_full_sweep": int(q ** 3 * mops / tried)}

    # G7 -------------------------------------------------------------------
    scale = {}
    for n in range(5):
        i2 = make_instance(seed=1, n=n, m=8)
        scale["n=%d" % n] = {"q": i2["q"], "space": i2["q"] ** 3,
                             "verifies": verify(i2, i2["answer"])[0]}
    report["G7_scales"] = {"pass": all(v["verifies"] for v in scale.values()),
                           "ladder": scale}

    # G9(c) ----------------------------------------------------------------
    rendered = "%d,%d,%d" % tuple(a)
    report["G9_no_tool_suitability"] = {
        "answer_chars": len(rendered), "answer_elements": len(a),
        "answer_tokens": 16, "intended_route_operations": ops,
        "within_answer_cap": len(rendered) <= 2000 and len(a) <= 256,
        "within_route_cap_300": ops <= 300,
        "note": ("the answer caps hold with three orders of magnitude to spare; the "
                 "intended-route cap of 300 does NOT hold -- the measured route is "
                 "%d GF(q) operations.  See the README caveat." % ops)}
    return report
