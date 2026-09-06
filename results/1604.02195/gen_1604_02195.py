"""Problem generator for arXiv:1604.02195 -- Keivan Hassani Monfared,
"Existence of a Not Necessarily Symmetric Matrix with Given Distinct Eigenvalues
and Graph" (math.SP / math.CO / math.DS; Linear Algebra Appl. 527 (2017) 1-11).

The paper's main theorem (Section 3): for k distinct conjugate pairs
lambda_j +- mu_j i, l distinct reals gamma_j, and any loopless graph G on
n = 2k+l vertices carrying a matching of size at least k, there is a REAL matrix
whose spectrum is exactly those n numbers and whose graph is exactly G.  The
proof is non-constructive -- it perturbs the block-diagonal matrix of
Example 2.4 and applies the Implicit Function Theorem to the Jacobian of
Corollary 2.8 -- so it hands the solver existence, never a formula.  Its final
corollary is the case this family uses: a real matrix has n distinct eigenvalues
if and only if it is similar to a real IRREDUCIBLE TRIDIAGONAL matrix, i.e. the
graph G may be taken to be the path P_n.

An instance publishes

  * the graph G (a path on n scrambled vertex labels), given as an edge list;
  * ONE entry of A per edge, at a randomly chosen one of the two directions;
  * p(x) = det(xI - A), and q(x) = det(xI - A^) where A^ deletes the row and the
    column of one endpoint v0 of the path;
  * the split of the spectrum into l real roots and k conjugate pairs, certified
    by a Sturm sequence at generation time,

and asks for every remaining entry: the n diagonal entries and the n-1
off-diagonal entries whose transposes were published.  2n-1 rationals, and the
published data has exactly 2n-1 degrees of freedom, so the realisation is unique
(see UNIQUENESS in NOTES).

Built answer-first: the matrix is sampled, then its two characteristic
polynomials are computed by fraction-free (Bareiss) determinants at n+1 rational
nodes and exact Lagrange interpolation.  Nothing is searched for.  No floating
point value is created anywhere in the generation or verification path; the only
floats in the file are escalate()'s growth multipliers, which are truncated to
ints immediately, and the p-values, rates and timings selftest() reports.
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
from fractions import Fraction as F
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:                                    # exact matrices (Bareiss) + Sturm chains
    from gvlib import exact_matrices as em, roots as rt, rationals as rat
except Exception:                       # pragma: no cover - stay stdlib-only
    em = rt = rat = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "a loopless graph G on n vertices (a path, the graph of the paper's final corollary)",
        "a real n x n matrix A over Q whose graph is exactly G",
        "the monic characteristic polynomials p = det(xI-A) and q = det(xI-A^) over Q",
        "the prescribed spectrum as l distinct real roots and k conjugate pairs of p",
    ],
    "verification_operations": [
        "exact fraction-free (Bareiss) determinants of xI-A at n+1 rational nodes",
        "exact Lagrange interpolation of the two characteristic polynomials over Q",
        "coefficient-by-coefficient rational equality against the published p and q",
        "nonvanishing test on every off-diagonal entry at an edge of G",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "p and q are consecutive terms of the three-term recursion carried by the "
        "path: deleting the endpoint v0 gives det(xI-A) = (x-d_1) q - b_1 c_1 r, "
        "with r the characteristic polynomial of the path with two vertices "
        "removed, so ONE Euclidean division of p by q returns d_1 as the quotient "
        "and b_1 c_1 r as the remainder -- and the pair (q, r) is the same problem "
        "one vertex shorter, i.e. q/p has a terminating continued fraction whose "
        "partial quotients are the matrix.  A solver who does not see the "
        "recursion faces 2n-1 unknown entries constrained by 2n-1 polynomial "
        "coefficient equations of degree up to floor(n/2), and must eliminate or "
        "enumerate."
    ),
    "hardness_basis": (
        "Track B.  An efficient algorithm exists and it is classical: the "
        "Euclidean / continued-fraction peel (de Boor-Golub inverse Jacobi "
        "reconstruction, root-free form), n-1 polynomial divisions, O(n^2) exact "
        "rational operations, measured at 147 operations and ~4e-4 s at the "
        "shipping preset (selftest_report.json, G6.reference_algorithm).  The "
        "mechanical route -- the one available without the recursion -- is to "
        "enumerate the certificate language and test each candidate against both "
        "characteristic polynomials: 2.9e17 candidates, ~2.3e19 operations and "
        "~1.6e14 s extrapolated at the shipping preset, and that is AFTER the two "
        "entries a solver gets for free are fixed.  Newton's identities do NOT "
        "collapse this: the linearised power-sum system determines 0 of the 15 "
        "entries from p alone and 1 of 15 from p and q together (a second follows "
        "from one nonlinear substitution), the remaining 13 requiring the iterated "
        "peel."
    ),
    "max_answer_tokens": 57,   # measured worst case over 150 shipping seeds
                               # (71 chars, 15 atoms); caps are 500 / 2000 / 256
}

NATIVE = {
    "domain": "algebra",
    "core": "linear_algebra",
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": "decomposition: " + PROBLEM_PROFILE["intuition_description"],
    "reduction": None,
}


# ---------------------------------------------------------------------------
# difficulty ladder
#
#   n          vertices of the path; the answer is 2n-1 rationals
#   num_max    |numerator| bound on every sampled unknown entry
#   den_max    denominator bound on every sampled unknown entry (1 = integers)
#   b_num_max  |value| bound on the published entry of each edge (integers)
#   scramble   permute the vertex labels, so the matrix is not visibly tridiagonal
# ---------------------------------------------------------------------------

DIFFICULTY = {
    "demo":   {"n": 4, "num_max": 3, "den_max": 1, "b_num_max": 1, "scramble": False},
    "easy":   {"n": 6, "num_max": 6, "den_max": 1, "b_num_max": 2, "scramble": True},
    "medium": {"n": 7, "num_max": 8, "den_max": 2, "b_num_max": 3, "scramble": True},
    "hard":   {"n": 8, "num_max": 9, "den_max": 2, "b_num_max": 4, "scramble": True},
}

SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The published pair of polynomials are consecutive characteristic polynomials "
    "of the nested principal submatrices obtained by peeling vertices off the path "
    "from v0."
)

PLACEBO_HINT = (
    "The published pair of polynomials are exact rationals, so every intermediate "
    "quantity in this problem stays exact if you keep common denominators."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "The 2n-1 missing entries of A, as rationals num/den in lowest terms with "
        "den > 0: the n diagonal entries A[v][v], and for each edge {u,v} of the "
        "path the one of A[u][v], A[v][u] whose transpose was not published.  The "
        "planted values obey |num| <= num_max and den <= den_max, and every "
        "off-diagonal value is nonzero (that is what makes the graph of A equal to "
        "G).  Values are reported at the published positions in the published "
        "order.  verify() does NOT enforce the height bounds -- any rational "
        "witness is accepted -- but the realisation is unique, so the bounds are "
        "descriptive of the whole solution set."
    ),
    "bounds": {},                       # filled per instance by _language_bounds
}

MAX_ANSWER_CHARS = 2000
MAX_ANSWER_ELEMENTS = 256
MAX_ROUTE_OPERATIONS = 1000

NOTES = r"""
WHICH SECTION FIXED THE DEFINITION
  Section 1 defines the graph of a matrix: for i != j, A[i][j] != 0 iff i -> j;
  diagonal entries are unconstrained.  That is the definition verify() enforces.
  Section 3's theorem gives existence for any G on 2k+l vertices with a matching
  of size >= k; the corollary closing Section 3 ("a real matrix has distinct
  eigenvalues if and only if it is similar to a real irreducible tridiagonal
  matrix") is the specialisation this family uses: G = the path P_n, whose
  matching number floor(n/2) is >= k for every admissible split.  Example 2.4 is
  the block-diagonal matrix the proof perturbs, and Corollary 2.8 is the Jacobian
  computation that makes the Implicit Function Theorem apply.

WHAT MAKES IT EASY, AND WHAT WAS DONE ABOUT IT
  (1) Prescribing ONLY the spectrum leaves the realisation set positive
      dimensional: 2n-1 unknown entries against n coefficient equations.  Worse,
      it is then constructively easy -- pick ANY monic q of degree n-1 coprime to
      p and run the continued-fraction expansion of q/p.  Measured realisation
      count: infinite.  That version fails H and would fail the "count the
      realisations" test outright.  The instance therefore publishes q as well,
      which pins the count to exactly one.
  (2) A star / arrow-shaped G makes the coefficient system LINEAR in the edge
      products (no two edges of a star are disjoint, so the characteristic
      polynomial is the secular equation and the products fall out of one
      Lagrange interpolation).  The path is the opposite extreme: its matchings
      of every size contribute, so the coefficient equations have degree up to
      floor(n/2).
  (3) The diagonal similarity A -> D A D^-1 fixes the spectrum and the graph and
      rescales the two directions of each edge inversely, so only the products
      A[u][v] A[v][u] are determined by (p, q).  Publishing one entry per edge
      kills that continuum: the remaining entry of the edge is then unique.

UNIQUENESS (the realisation count, exactly 1, and why)
  Order the path from the deleted endpoint v0 = w_1, w_2, ..., w_n.  Write
  d_i = A[w_i][w_i], and e_i = A[w_i][w_i+1] A[w_i+1][w_i] for the edge product.
  Expanding det(xI-A) along the first row of the path order,
        p = (x - d_1) q - e_1 r,
  with q, r the characteristic polynomials of the path with w_1, resp. w_1 and
  w_2, deleted -- both monic, of degrees n-1 and n-2.  Since p and q are monic of
  consecutive degrees the Euclidean division of p by q has a monic linear
  quotient, so d_1 is forced; the remainder is -e_1 r with r monic of degree n-2,
  so e_1 is forced by its leading coefficient and r by the rest; and (q, r) is
  the same problem one vertex shorter.  Induction gives exactly one (d, e), hence
  exactly one A once the published entry of each edge is fixed and nonzero.
  So the realisation count is 1 -- not 1 up to similarity, not 1 in a grid: one
  matrix over Q, and over C as well.  This is the root-free form of the de Boor -
  Golub reconstruction, and G5 reports it both as a theorem and as an exhaustive
  count over the demo grid.

WHAT DEFEATS EACH ATTACK
  * linearised_coefficient_solve: writing the 2n-1 coefficient equations and
    treating every distinct monomial in the entries as an independent unknown is
    the cheapest form of elimination.  It is massively underdetermined -- 984
    monomials against 15 equations at the shipping preset, nullity 969 -- and the
    particular solution it returns never verifies (0/8).
  * newton_power_sums_p_only: Newton's identities turn p into the power sums
    tr(A^k) with no root-finding, which is the attack most likely to break a
    spectral family.  Measured on the SYMBOLIC power sums of the path matrix: from
    p alone the linearised system (8 equations, 856 monomials) determines 0 of the
    2n-1 entries; adding q's power sums (15 equations) determines 1 -- the first
    diagonal entry d_1 = tr A - tr A^ -- and one further NONLINEAR substitution
    (d_1^2 inside tr A^2 - tr (A^)^2 = d_1^2 + 2 e_1) gives a second.  The other 13
    need the recursion, i.e. the compact route itself -- so the trace route is an
    alternative ENTRANCE to the intended route, never a shortcut past it, and
    random_candidate hands the solver both leaked entries for free so that G4 is
    not measured against a prior a solver can beat.
  * greedy_coefficient_hill_climb and random_restart: the coefficient residual is
    not a monotone function of any single entry (each coefficient mixes matchings
    of every size), so hill-climbing on the number of matched coefficients stalls;
    0/8 and 0/8.
  * The domain-standard algorithm SOLVES this, as Track B requires it to be
    declared: the continued-fraction peel, 8/8 at 147 operations.  It is reported
    under G6.reference_algorithm, never inside attacks.
"""


# ---------------------------------------------------------------------------
# exact arithmetic helpers (gvlib first, self-contained fallbacks second)
# ---------------------------------------------------------------------------

def _det(rows: list[list[F]]) -> F:
    """Exact determinant by fraction-free (Bareiss) elimination."""
    if em is not None:
        return em.det(em.matrix([[F(x) for x in row] for row in rows]))
    return _det_bareiss([[F(x) for x in row] for row in rows])


def _det_bareiss(A: list[list[F]]) -> F:                # pragma: no cover
    n = len(A)
    M = [row[:] for row in A]
    sign = 1
    prev = F(1)
    for k in range(n - 1):
        if M[k][k] == 0:
            for r in range(k + 1, n):
                if M[r][k] != 0:
                    M[k], M[r] = M[r], M[k]
                    sign = -sign
                    break
            else:
                return F(0)
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                M[i][j] = (M[i][j] * M[k][k] - M[i][k] * M[k][j]) / prev
        prev = M[k][k]
    return sign * M[n - 1][n - 1]


def _poly_trim(c: list[F]) -> list[F]:
    c = list(c)
    while c and c[-1] == 0:
        c.pop()
    return c


def _charpoly(A: list[list[F]]) -> list[F]:
    """det(xI - A), ascending coefficients, monic of degree len(A).

    Fraction-free determinants at n+1 rational nodes plus exact Lagrange
    interpolation.  Structure-free: it never uses that A is tridiagonal.
    """
    n = len(A)
    if n == 0:
        return [F(1)]
    xs = [F(i) for i in range(n + 1)]
    ys = []
    for x in xs:
        M = [[(x - A[i][j]) if i == j else (-A[i][j]) for j in range(n)]
             for i in range(n)]
        ys.append(_det(M))
    coeffs = [F(0)] * (n + 1)
    for i, (xi, yi) in enumerate(zip(xs, ys)):
        basis = [F(1)]
        den = F(1)
        for j, xj in enumerate(xs):
            if j == i:
                continue
            new = [F(0)] * (len(basis) + 1)
            for k, cc in enumerate(basis):
                new[k + 1] += cc
                new[k] -= cc * xj
            basis = new
            den *= (xi - xj)
        f = yi / den
        for k, cc in enumerate(basis):
            coeffs[k] += cc * f
    return coeffs


def _is_squarefree(p: list[F]) -> bool:
    if rt is not None:
        return rt.is_squarefree(p)
    return _poly_degree(_poly_gcd(p, _poly_deriv(p))) == 0


def _count_real_roots(p: list[F]) -> int:
    """Number of DISTINCT real roots of p, by a Sturm chain.  Exact."""
    if rt is not None:
        sf = rt.squarefree_part(p)
        b = rt.root_bound(sf)
        return rt.count_roots(sf, -b, b)
    return _count_real_roots_local(p)


# -- self-contained Sturm fallback, used only when gvlib is not importable ----

def _poly_degree(a: list[F]) -> int:
    a = _poly_trim(a)
    return len(a) - 1


def _poly_deriv(a: list[F]) -> list[F]:
    return _poly_trim([a[i] * i for i in range(1, len(a))])


def _poly_divmod(a: list[F], b: list[F]) -> tuple[list[F], list[F]]:
    a, b = _poly_trim(a), _poly_trim(b)
    if not b:
        raise ZeroDivisionError("polynomial division by zero")
    q = [F(0)] * max(len(a) - len(b) + 1, 1)
    r = list(a)
    while _poly_trim(r) and len(_poly_trim(r)) >= len(b):
        r = _poly_trim(r)
        shift = len(r) - len(b)
        factor = r[-1] / b[-1]
        q[shift] += factor
        for i, c in enumerate(b):
            r[i + shift] -= factor * c
        r = _poly_trim(r)
    return _poly_trim(q), _poly_trim(r)


def _poly_gcd(a: list[F], b: list[F]) -> list[F]:
    a, b = _poly_trim(a), _poly_trim(b)
    while b:
        a, b = b, _poly_divmod(a, b)[1]
    if a:
        a = [c / a[-1] for c in a]
    return a


def _poly_eval(a: list[F], x: F) -> F:
    out = F(0)
    for c in reversed(a):
        out = out * x + c
    return out


def _count_real_roots_local(p: list[F]) -> int:      # pragma: no cover
    p = _poly_trim(p)
    g = _poly_gcd(p, _poly_deriv(p))
    sf = _poly_divmod(p, g)[0] if _poly_degree(g) > 0 else p
    if _poly_degree(sf) < 1:
        return 0
    chain = [sf, _poly_deriv(sf)]
    while _poly_trim(chain[-1]):
        r = _poly_divmod(chain[-2], chain[-1])[1]
        if not _poly_trim(r):
            break
        chain.append([-c for c in r])
    bound = 1 + max((abs(c / sf[-1]) for c in sf[:-1]), default=F(0))

    def changes(x):
        signs = []
        for f in chain:
            v = _poly_eval(f, x)
            if v != 0:
                signs.append(1 if v > 0 else -1)
        return sum(1 for i in range(len(signs) - 1) if signs[i] != signs[i + 1])
    return changes(-bound) - changes(bound)


def _power_sums(p: list[F], m: int) -> list[F]:
    """s_1..s_m of the roots of the monic polynomial p, by Newton's identities.

    p is ascending; p[deg] == 1.  No root-finding, no floats.
    """
    n = len(p) - 1
    a = [p[n - i] for i in range(n + 1)]                 # a[i] = coeff of x^(n-i)
    s = []
    for k in range(1, m + 1):
        if k <= n:
            tot = -F(k) * a[k]
            for i in range(1, k):
                tot -= a[i] * s[k - i - 1]
        else:
            tot = F(0)
            for i in range(1, n + 1):
                tot -= a[i] * s[k - i - 1]
        s.append(tot)
    return s


# ---------------------------------------------------------------------------
# parameters, grids, instance construction
# ---------------------------------------------------------------------------

def _params(**params) -> dict:
    p = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    p.update({k: v for k, v in params.items() if v is not None})
    p["n"] = int(p["n"])
    if p["n"] < 3:
        raise ValueError("n >= 3 required: the peel needs at least one interior step")
    for key in ("num_max", "den_max", "b_num_max"):
        p[key] = int(p[key])
        if p[key] < 1:
            raise ValueError("%s must be >= 1" % key)
    p["scramble"] = bool(p["scramble"])
    return p


_GRID_CACHE: dict = {}
_STRUCT_CACHE: dict = {}


def _grid(num_max: int, den_max: int) -> list[F]:
    """Every rational a/b in lowest terms with |a| <= num_max, 1 <= b <= den_max."""
    hit = _GRID_CACHE.get((num_max, den_max))
    if hit is not None:
        return hit
    out = set()
    for b in range(1, den_max + 1):
        for a in range(-num_max, num_max + 1):
            if math.gcd(abs(a), b) == 1:
                out.add(F(a, b))
    res = sorted(out)
    if len(_GRID_CACHE) > 64:
        _GRID_CACHE.clear()
    _GRID_CACHE[(num_max, den_max)] = res
    return res


def _language_bounds(p: dict) -> dict:
    g = _grid(p["num_max"], p["den_max"])
    return {
        "n": p["n"],
        "n_entries": 2 * p["n"] - 1,
        "num_max": p["num_max"],
        "den_max": p["den_max"],
        "b_num_max": p["b_num_max"],
        "diagonal_grid_size": len(g),
        "offdiagonal_grid_size": len(g) - 1,
    }


def _qj(x: F) -> list[int]:
    x = F(x)
    return [x.numerator, x.denominator]


def _qf(pair: Any) -> F:
    return F(int(pair[0]), int(pair[1]))


def _fmt(x: F) -> str:
    x = F(x)
    return str(x.numerator) if x.denominator == 1 else "%d/%d" % (x.numerator,
                                                                 x.denominator)


def make_instance(seed: int = 0, **params) -> dict:
    """Sample the matrix FIRST, then publish its two characteristic polynomials.

    No search: the answer is the sampled matrix.  The only loop is rejection
    sampling on the PLANT (distinct eigenvalues, at least one conjugate pair),
    which is a test of the object just built, never a search for one.
    """
    p = _params(**params)
    n = p["n"]
    rng = random.Random("%d|%d|%d|%d|%d|%d" % (seed, n, p["num_max"], p["den_max"],
                                               p["b_num_max"], int(p["scramble"])))
    grid = _grid(p["num_max"], p["den_max"])
    nz = [v for v in grid if v != 0]
    bvals = [F(v) for v in range(-p["b_num_max"], p["b_num_max"] + 1) if v != 0]

    for _attempt in range(400):
        d = [rng.choice(grid) for _ in range(n)]
        c = [rng.choice(nz) for _ in range(n - 1)]
        b = [rng.choice(bvals) for _ in range(n - 1)]
        A = [[F(0)] * n for _ in range(n)]
        for i in range(n):
            A[i][i] = d[i]
        for i in range(n - 1):
            A[i][i + 1] = b[i]
            A[i + 1][i] = c[i]
        pp = _charpoly(A)
        if not _is_squarefree(pp):
            continue                    # the paper's hypothesis: DISTINCT eigenvalues
        l = _count_real_roots(pp)
        if l < 0 or (n - l) % 2 != 0:
            continue
        k = (n - l) // 2
        if k < 1:
            continue                    # the paper's case: at least one conjugate pair
        sub = [[A[i][j] for j in range(1, n)] for i in range(1, n)]
        qq = _charpoly(sub)
        break
    else:                                                # pragma: no cover
        raise RuntimeError("failed to sample an admissible plant")

    # scrambled vertex labels: internal index i  ->  public label perm[i]
    perm = list(range(n))
    if p["scramble"]:
        rng.shuffle(perm)
    v0 = perm[0]

    edges = []
    given = []
    ask = []
    ans_at = {}
    for i in range(n - 1):
        u, v = perm[i], perm[i + 1]
        edges.append(tuple(sorted((u, v))))
        if rng.randrange(2) == 0:       # publish A[u][v], ask for A[v][u]
            given.append((u, v, b[i]))
            ask.append((v, u))
            ans_at[(v, u)] = c[i]
        else:                           # publish A[v][u], ask for A[u][v]
            given.append((v, u, b[i]))
            ask.append((u, v))
            ans_at[(u, v)] = c[i]
    for i in range(n):
        ask.append((perm[i], perm[i]))
        ans_at[(perm[i], perm[i])] = d[i]

    edges.sort()
    given.sort(key=lambda t: (t[0], t[1]))
    ask.sort()

    inst = {
        "paper": "arXiv:1604.02195",
        "n": n,
        "params": {kk: p[kk] for kk in ("n", "num_max", "den_max", "b_num_max",
                                        "scramble")},
        "seed": seed,
        "edges": [list(e) for e in edges],
        "given": [[u, v, _qj(val)] for (u, v, val) in given],
        "ask": [list(t) for t in ask],
        "v0": v0,
        "p": [_qj(x) for x in pp],
        "q": [_qj(x) for x in qq],
        "k_pairs": k,
        "l_real": l,
        "answer": [_qj(ans_at[t]) for t in ask],
        "language_bounds": _language_bounds(p),
    }
    return inst


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------

def _poly_text(coeffs: list[F], name: str) -> str:
    n = len(coeffs) - 1
    parts = []
    for k in range(n, -1, -1):
        cc = coeffs[k]
        if cc == 0 and k != n:
            continue
        if k == n:
            term = "x^%d" % k
        else:
            sgn = "+" if cc > 0 else "-"
            mag = _fmt(abs(cc))
            if k == 0:
                term = "%s %s" % (sgn, mag)
            elif k == 1:
                term = "%s %s*x" % (sgn, mag)
            else:
                term = "%s %s*x^%d" % (sgn, mag, k)
        parts.append(term)
    return "%s(x) = %s" % (name, " ".join(parts))


def render(inst: dict) -> str:
    n = inst["n"]
    edges = ", ".join("{%d,%d}" % (u, v) for u, v in inst["edges"])
    given = "\n".join("    A[%d][%d] = %s" % (u, v, _fmt(_qf(val)))
                      for u, v, val in inst["given"])
    ask = ", ".join("(%d,%d)" % (i, j) for i, j in inst["ask"])
    pp = [_qf(x) for x in inst["p"]]
    qq = [_qf(x) for x in inst["q"]]
    k, l = inst["k_pairs"], inst["l_real"]
    example = ", ".join(["1"] * (len(inst["ask"]) - 1) + ["-2/3"])

    text = """An inverse eigenvalue problem for a graph (arXiv:1604.02195).

G is a loopless undirected graph on the vertex set {0,1,...,%(nm1)d}, with edge set
    E = {%(edges)s}
A is a real %(n)d x %(n)d matrix whose rows and columns are indexed by those vertices.
The GRAPH OF A is G, which means exactly this: for u != v, the entry A[u][v] is
nonzero if and only if {u,v} is an edge of G.  Entries A[u][v] with u != v and
{u,v} not an edge are therefore 0.  The %(n)d diagonal entries are unconstrained
(they may be zero or nonzero).

These entries of A are known:
%(given)s
Note that exactly one of the two entries A[u][v], A[v][u] is listed for each edge.

Let I be the %(n)d x %(n)d identity matrix, and let A^ be the %(nm1)d x %(nm1)d matrix obtained
from A by deleting the row AND the column indexed by vertex %(v0)d.  Then

    %(p)s

    %(q)s

where p(x) = det(x*I - A) and q(x) = det(x*I - A^).  All coefficients are exact
rationals, written num/den in lowest terms (an integer means denominator 1).
The %(n)d roots of p are pairwise distinct: %(l)d of them are real and the other %(twok)d
form %(k)d conjugate pairs a +- b*i with b != 0.

TASK.  Determine every entry of A that is not listed above.  There are %(cnt)d of
them: the %(n)d diagonal entries, and for each edge the one of the two directions
that was not published.  Report their values at these positions, in exactly this
order:
    %(ask)s

Every value is a rational number; write it as num/den in lowest terms, or as a
plain integer when the denominator is 1 (for example 3, -3, 5/2, -5/2).  Separate
the %(cnt)d values by commas, in the order listed above, and put nothing else
inside the answer tags.

Give your final answer inside <answer></answer> tags.
Example of the format (not the answer): <answer>%(example)s</answer>""" % {
        "n": n, "nm1": n - 1, "edges": edges, "given": given, "v0": inst["v0"],
        "p": _poly_text(pp, "p"), "q": _poly_text(qq, "q"),
        "l": l, "k": k, "twok": 2 * k, "cnt": len(inst["ask"]), "ask": ask,
        "example": example,
    }

    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------

_TAG = re.compile(r"<answer>(.*?)</answer>", re.S | re.I)
_RAT = re.compile(r"^[+-]?\d+(?:\s*/\s*\d+)?$")
_LIST = re.compile(r"[+-]?\d+(?:/\d+)?(?:\s*,\s*[+-]?\d+(?:/\d+)?)+")


def parse_answer(text: Any) -> list[list[int]] | None:
    """Extract the list of rationals from raw solver output.  None on garbage."""
    if isinstance(text, list):
        try:
            return [[int(a), int(b)] for a, b in text]
        except Exception:
            return None
    if not isinstance(text, str):
        return None
    m = _TAG.findall(text)
    tagged = bool(m)
    if tagged:
        body = m[-1]
    else:
        # No tags: models sometimes end with a bare comma-separated list.  Take the
        # last maximal run of comma-separated rationals rather than returning None
        # on a reply that visibly contains an answer.
        runs = _LIST.findall(text)
        body = runs[-1] if runs else text
    body = body.replace("```", " ").replace("$", " ").replace("\\", " ")
    body = body.strip()
    if body.startswith("[") and body.endswith("]"):
        try:
            loaded = json.loads(body)
        except Exception:
            loaded = None
        if isinstance(loaded, list) and loaded and all(
                isinstance(t, list) and len(t) == 2 for t in loaded):
            try:
                return [[int(a), int(b)] for a, b in loaded]
            except Exception:
                return None
        body = body[1:-1]
    tokens = [t.strip() for t in re.split(r"[,\n;]+", body) if t.strip()]
    if not tokens:
        return None
    out = []
    for tok in tokens:
        tok = tok.replace(" ", "")
        if not _RAT.match(tok):
            return None
        if "/" in tok:
            a, b = tok.split("/")
            num, den = int(a), int(b)
        else:
            num, den = int(tok), 1
        if den == 0:
            return None
        f = F(num, den)
        out.append([f.numerator, f.denominator])
    return out


# ---------------------------------------------------------------------------
# verification -- exact, characteristic-polynomial identity, no root finding
# ---------------------------------------------------------------------------

def _assemble(inst: dict, answer: list[list[int]]) -> tuple[Any, str]:
    n = inst["n"]
    A = [[F(0)] * n for _ in range(n)]
    for u, v, val in inst["given"]:
        A[u][v] = _qf(val)
    for pos, val in zip(inst["ask"], answer):
        u, v = pos
        A[u][v] = F(int(val[0]), int(val[1]))
    return A, ""


def verify(inst: dict, answer: Any) -> tuple[bool, str]:
    """(True,'ok') or (False, reason).  Accepts ANY witness; never reads
    inst['answer']."""
    n = inst["n"]
    need = len(inst["ask"])
    if isinstance(answer, str):
        answer = parse_answer(answer)
    if answer is None:
        return False, "no answer found"
    if not isinstance(answer, (list, tuple)):
        return False, "answer is not a list"
    if len(answer) != need:
        return False, "expected %d values, got %d" % (need, len(answer))
    vals = []
    for idx, item in enumerate(answer):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            return False, "value %d is not a [num, den] pair" % idx
        try:
            num, den = int(item[0]), int(item[1])
        except Exception:
            return False, "value %d is not an integer pair" % idx
        if den <= 0:
            return False, "value %d has a non-positive denominator" % idx
        vals.append([num, den])

    A, _ = _assemble(inst, vals)

    edgeset = set(tuple(e) for e in inst["edges"])
    for u in range(n):
        for v in range(n):
            if u == v:
                continue
            on_edge = tuple(sorted((u, v))) in edgeset
            if on_edge and A[u][v] == 0:
                return False, ("A[%d][%d] = 0 at the edge {%d,%d}: the graph of A "
                               "is not G" % (u, v, min(u, v), max(u, v)))
            if (not on_edge) and A[u][v] != 0:
                return False, ("A[%d][%d] != 0 off the edge set: the graph of A is "
                               "not G" % (u, v))

    target_p = [_qf(x) for x in inst["p"]]
    got_p = _charpoly(A)
    for j in range(len(target_p)):
        if got_p[j] != target_p[j]:
            return False, ("det(xI-A) differs from p at the coefficient of x^%d "
                           "(got %s, want %s)" % (j, _fmt(got_p[j]),
                                                  _fmt(target_p[j])))

    v0 = inst["v0"]
    keep = [i for i in range(n) if i != v0]
    sub = [[A[i][j] for j in keep] for i in keep]
    target_q = [_qf(x) for x in inst["q"]]
    got_q = _charpoly(sub)
    for j in range(len(target_q)):
        if got_q[j] != target_q[j]:
            return False, ("det(xI-A^) differs from q at the coefficient of x^%d "
                           "(got %s, want %s)" % (j, _fmt(got_q[j]),
                                                  _fmt(target_q[j])))
    return True, "ok"


# ---------------------------------------------------------------------------
# canonical key
# ---------------------------------------------------------------------------

def _path_order(inst: dict) -> list[int]:
    """Vertices of the path in order, starting at v0 (an endpoint)."""
    n = inst["n"]
    adj = {i: [] for i in range(n)}
    for u, v in inst["edges"]:
        adj[u].append(v)
        adj[v].append(u)
    order = [inst["v0"]]
    prev = None
    while len(order) < n:
        cur = order[-1]
        nxt = [w for w in adj[cur] if w != prev]
        if not nxt:
            break
        prev, cur = cur, nxt[0]
        order.append(cur)
    return order


def canonical_key(inst: dict) -> str:
    """Invariant under vertex relabelling and under transposing A.

    Built from the path order induced by v0, the published entry of each edge in
    that order (which is the same value whichever direction it was published in),
    and the two characteristic polynomials.  Never touches the seed or render().
    """
    order = _path_order(inst)
    pos = {(u, v): _qf(val) for u, v, val in inst["given"]}
    seq = []
    for i in range(len(order) - 1):
        u, v = order[i], order[i + 1]
        val = pos.get((u, v), pos.get((v, u)))
        seq.append(_qj(val))
    payload = {
        "n": inst["n"],
        "given_along_path": seq,
        "p": inst["p"],
        "q": inst["q"],
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# candidate space
# ---------------------------------------------------------------------------

def _free_deductions(inst: dict) -> tuple[F, F]:
    """(d_1, e_1) -- the two quantities a solver gets from the published data by
    a one-line calculation: d_1 = tr(A) - tr(A^) and, from the second power sums,
    e_1 = A[w1][w2]A[w2][w1] = (s2(p) - s2(q) - d_1^2)/2."""
    pp = [_qf(x) for x in inst["p"]]
    qq = [_qf(x) for x in inst["q"]]
    sp = _power_sums(pp, 2)
    sq = _power_sums(qq, 2)
    d1 = sp[0] - sq[0]
    e1 = (sp[1] - sq[1] - d1 * d1) / 2
    return d1, e1


def _structure(inst: dict) -> dict:
    """Everything random_candidate is allowed to know for free.  Memoised: the
    cache holds a reference to the instance, so the id() key cannot be reused."""
    ck = (id(inst), inst["n"], inst["v0"], len(inst["given"]))
    hit = _STRUCT_CACHE.get(ck)
    if hit is not None:
        return hit[1]
    order = _path_order(inst)
    n = inst["n"]
    pos_of = {tuple(t): i for i, t in enumerate(inst["ask"])}
    given = {(u, v): _qf(val) for u, v, val in inst["given"]}
    diag_idx = [pos_of[(w, w)] for w in order]
    off_idx = []
    b_of = []
    for i in range(n - 1):
        u, v = order[i], order[i + 1]
        if (u, v) in given:
            off_idx.append(pos_of[(v, u)])
            b_of.append(given[(u, v)])
        else:
            off_idx.append(pos_of[(u, v)])
            b_of.append(given[(v, u)])
    pp = [_qf(x) for x in inst["p"]]
    trace = -pp[n - 1]
    d1, e1 = _free_deductions(inst)
    st = {"order": order, "diag_idx": diag_idx, "off_idx": off_idx,
          "b": b_of, "trace": trace, "d1": d1, "c1": e1 / b_of[0],
          "target_p": pp, "target_q": [_qf(x) for x in inst["q"]]}
    if len(_STRUCT_CACHE) > 64:
        _STRUCT_CACHE.clear()
    _STRUCT_CACHE[ck] = (inst, st)
    return st


def random_candidate(inst: dict, rng: random.Random) -> list[list[int]]:
    """A candidate that already satisfies every constraint a solver deduces from
    the statement in one line: the trace, the first diagonal entry, and the first
    edge's missing entry (see _free_deductions).  It does NOT use the recursion."""
    n = inst["n"]
    b = inst["language_bounds"]
    grid = _grid(b["num_max"], b["den_max"])
    nz = [v for v in grid if v != 0]
    st = _structure(inst)
    out = [None] * len(inst["ask"])
    for _try in range(64):
        diag = [None] * n
        diag[0] = st["d1"]
        for i in range(1, n - 1):
            diag[i] = rng.choice(grid)
        last = st["trace"] - sum(diag[:n - 1])
        if last not in grid:
            continue
        diag[n - 1] = last
        break
    else:
        diag = [st["d1"]] + [rng.choice(grid) for _ in range(n - 1)]
    offs = [st["c1"]] + [rng.choice(nz) for _ in range(n - 2)]
    for i, idx in enumerate(st["diag_idx"]):
        out[idx] = _qj(diag[i])
    for i, idx in enumerate(st["off_idx"]):
        out[idx] = _qj(offs[i])
    return out


def search_space(inst: dict) -> int:
    """Size of the space random_candidate samples: the two freely deducible
    entries are fixed and one diagonal entry is forced by the trace."""
    b = inst["language_bounds"]
    n = inst["n"]
    g = len(_grid(b["num_max"], b["den_max"]))
    return (g ** (n - 2)) * ((g - 1) ** (n - 2))


def naive_search_space(inst: dict) -> int:
    b = inst["language_bounds"]
    n = inst["n"]
    g = len(_grid(b["num_max"], b["den_max"]))
    return (g ** n) * ((g - 1) ** (n - 1))


def _tridiag_charpoly(d: list[F], e: list[F]) -> list[F]:
    """Characteristic polynomial of the path matrix by the three-term recursion.
    Only used by the brute-force counter, where the candidate is tridiagonal by
    construction; verify() uses the structure-free Bareiss route."""
    prev = [F(1)]
    cur = [-d[0], F(1)]
    for i in range(1, len(d)):
        nxt = [F(0)] * (len(cur) + 1)
        for k, c in enumerate(cur):
            nxt[k + 1] += c
            nxt[k] -= c * d[i]
        for k, c in enumerate(prev):
            nxt[k] -= e[i - 1] * c
        prev, cur = cur, nxt
    return cur


def enumerate_all(inst: dict, budget: int = 4_000_000) -> int | None:
    """Exact count of valid answers inside CERTIFICATE_LANGUAGE, by brute force
    over the grid.  Returns None when the grid exceeds the budget."""
    n = inst["n"]
    b = inst["language_bounds"]
    grid = _grid(b["num_max"], b["den_max"])
    nz = [v for v in grid if v != 0]
    total = (len(grid) ** n) * (len(nz) ** (n - 1))
    if total > budget:
        return None
    st = _structure(inst)
    target_p = [_qf(x) for x in inst["p"]]
    target_q = [_qf(x) for x in inst["q"]]
    bs = st["b"]
    count = 0

    def rec_off(d, offs):
        nonlocal count
        if len(offs) == n - 1:
            e = [bs[i] * offs[i] for i in range(n - 1)]
            if _tridiag_charpoly(d, e) != target_p:
                return
            if _tridiag_charpoly(d[1:], e[1:]) != target_q:
                return
            count += 1
            return
        for v in nz:
            rec_off(d, offs + [v])

    def rec_diag(d):
        if len(d) == n:
            rec_off(d, [])
            return
        for v in grid:
            rec_diag(d + [v])

    rec_diag([])
    return count


# ---------------------------------------------------------------------------
# the reference algorithm (Track B: it is SUPPOSED to work)
# ---------------------------------------------------------------------------

class _Ops:
    __slots__ = ("n",)

    def __init__(self):
        self.n = 0


def _reference_solve(inst: dict) -> tuple[list[list[int]] | None, int]:
    """Root-free de Boor-Golub peel: the continued-fraction expansion of q/p.

    n-1 Euclidean divisions of monic polynomials of consecutive degree.  Counts
    every exact rational +, -, *, / it performs.
    """
    ops = _Ops()
    n = inst["n"]
    st = _structure(inst)
    r_prev = [_qf(x) for x in inst["p"]]
    r_cur = [_qf(x) for x in inst["q"]]
    ds: list[F] = []
    cs: list[F] = []
    for i in range(n - 1):
        m = len(r_prev) - 1
        t = r_prev[m - 1] - (r_cur[m - 2] if m >= 2 else F(0))
        ops.n += 1
        ds.append(-t)
        R = list(r_prev)
        for k in range(len(r_cur)):
            R[k + 1] -= r_cur[k]
            R[k] -= t * r_cur[k]
            ops.n += 3
        R = _poly_trim(R)
        if len(R) - 1 != m - 2:
            return None, ops.n
        lead = R[-1]
        e = -lead
        cs.append(e / st["b"][i])
        ops.n += 1
        nxt = [x / lead for x in R]
        ops.n += len(R)
        r_prev, r_cur = r_cur, nxt
    ds.append(-r_prev[0])
    out = [None] * len(inst["ask"])
    for i, idx in enumerate(st["diag_idx"]):
        out[idx] = _qj(ds[i])
    for i, idx in enumerate(st["off_idx"]):
        out[idx] = _qj(cs[i])
    return out, ops.n


# ---------------------------------------------------------------------------
# the symbolic coefficient system (used by the attacks)
# ---------------------------------------------------------------------------

def _sym_charpoly(nvars: int, dvar: list[int], evar: list[tuple[int, F]],
                  ) -> list[dict[tuple, F]]:
    """Characteristic polynomial of the path matrix with SYMBOLIC entries.

    dvar[i] is the variable index of d_i; evar[i] = (variable index of the
    unknown off-diagonal entry of edge i, its published partner b_i), so the edge
    product is b_i * x_var.  Returns ascending coefficients, each a dict from
    exponent tuple to rational.
    """
    def mono(idx=None, coeff=F(1)):
        exps = [0] * nvars
        if idx is not None:
            exps[idx] = 1
        return {tuple(exps): coeff}

    def add(p, q):
        out = dict(p)
        for k, v in q.items():
            out[k] = out.get(k, F(0)) + v
            if out[k] == 0:
                del out[k]
        return out

    def mul(p, q):
        out = {}
        for k1, v1 in p.items():
            for k2, v2 in q.items():
                k = tuple(a + b for a, b in zip(k1, k2))
                out[k] = out.get(k, F(0)) + v1 * v2
                if out[k] == 0:
                    del out[k]
        return out

    def neg(p):
        return {k: -v for k, v in p.items()}

    one = mono()
    prev = [one]                                     # polynomial in x, coeffs are dicts
    cur = [neg(mono(dvar[0])), one]
    for i in range(1, len(dvar)):
        nxt = [{} for _ in range(len(cur) + 1)]
        for k, c in enumerate(cur):
            nxt[k + 1] = add(nxt[k + 1], c)
            nxt[k] = add(nxt[k], neg(mul(c, mono(dvar[i]))))
        idx, bi = evar[i - 1]
        for k, c in enumerate(prev):
            nxt[k] = add(nxt[k], neg(mul(c, mono(idx, bi))))
        prev, cur = cur, nxt
    return cur


def _padd(p, q):
    out = dict(p)
    for k, v in q.items():
        out[k] = out.get(k, F(0)) + v
        if out[k] == 0:
            del out[k]
    return out


def _pmul(p, q):
    out = {}
    for k1, v1 in p.items():
        for k2, v2 in q.items():
            k = tuple(a + b for a, b in zip(k1, k2))
            out[k] = out.get(k, F(0)) + v1 * v2
            if out[k] == 0:
                del out[k]
    return out


def _sym_path_matrix(inst: dict, drop_first: bool = False):
    """The path matrix with SYMBOLIC unknown entries (the published entry of each
    edge stays a constant), as a matrix of monomial dicts over 2n-1 variables."""
    n = inst["n"]
    st = _structure(inst)
    nv = 2 * n - 1

    def mono(idx=None, coeff=F(1)):
        exps = [0] * nv
        if idx is not None:
            exps[idx] = 1
        return {tuple(exps): coeff} if coeff != 0 else {}

    rows = range(1, n) if drop_first else range(n)
    idxmap = {v: i for i, v in enumerate(rows)}
    m = len(idxmap)
    A = [[{} for _ in range(m)] for _ in range(m)]
    for v in rows:
        A[idxmap[v]][idxmap[v]] = mono(v)
    for i in range(n - 1):
        if i not in idxmap or (i + 1) not in idxmap:
            continue
        a, b = idxmap[i], idxmap[i + 1]
        # one direction is the published constant b_i, the other the variable n+i
        A[a][b] = mono(n + i)
        A[b][a] = mono(None, st["b"][i])
    return A


def _sym_traces(inst: dict, kmax: int, drop_first: bool = False) -> list[dict]:
    """tr(A^k) for k = 1..kmax, as polynomials in the unknown entries."""
    A = _sym_path_matrix(inst, drop_first)
    m = len(A)
    P = [[dict(A[i][j]) for j in range(m)] for i in range(m)]
    out = []
    for _k in range(kmax):
        tr = {}
        for i in range(m):
            tr = _padd(tr, P[i][i])
        out.append(tr)
        if _k + 1 < kmax:
            Q = [[{} for _ in range(m)] for _ in range(m)]
            for i in range(m):
                for j in range(m):
                    acc = {}
                    for t in range(m):
                        if P[i][t] and A[t][j]:
                            acc = _padd(acc, _pmul(P[i][t], A[t][j]))
                    Q[i][j] = acc
            P = Q
    return out


def _power_sum_system(inst: dict, use_q: bool):
    """The equations tr(A^k) = s_k (k = 1..n), with s_k obtained from p by
    Newton's identities -- no root-finding -- optionally together with the same
    equations for A^ and q.  Linearised: every monomial an independent unknown."""
    n = inst["n"]
    pp = [_qf(x) for x in inst["p"]]
    qq = [_qf(x) for x in inst["q"]]
    eqs = list(zip(_sym_traces(inst, n), _power_sums(pp, n)))
    if use_q:
        eqs += list(zip(_sym_traces(inst, n - 1, drop_first=True),
                        _power_sums(qq, n - 1)))
    return _rows_from_eqs(eqs, 2 * n - 1)


def _rows_from_eqs(eqs, nv):
    monos = set()
    for poly, _r in eqs:
        for k in poly:
            if any(k):
                monos.add(k)
    monos = sorted(monos)
    index = {m: i for i, m in enumerate(monos)}
    rows, rhs = [], []
    for poly, r in eqs:
        row = [F(0)] * len(monos)
        const = F(0)
        for k, v in poly.items():
            if any(k):
                row[index[k]] = v
            else:
                const += v
        rows.append(row)
        rhs.append(r - const)
    deg1 = {}
    for i in range(nv):
        e = [0] * nv
        e[i] = 1
        t = tuple(e)
        if t in index:
            deg1[i] = index[t]
    return rows, rhs, monos, deg1


def _linearised_system(inst: dict, use_q: bool = True, power_sums: bool = False):
    """Build the coefficient (or power-sum) equations, treat every distinct
    monomial in the entries as an independent unknown, and return
    (rows, rhs, monomials, var_of_degree1_monomial)."""
    n = inst["n"]
    st = _structure(inst)
    nv = 2 * n - 1
    dvar = list(range(n))
    evar = [(n + i, st["b"][i]) for i in range(n - 1)]
    cp = _sym_charpoly(nv, dvar, evar)
    cq = _sym_charpoly(nv, dvar[1:], evar[1:])
    target_p = [_qf(x) for x in inst["p"]]
    target_q = [_qf(x) for x in inst["q"]]

    eqs = [(cp[j], target_p[j]) for j in range(n)]
    if use_q:
        eqs += [(cq[j], target_q[j]) for j in range(n - 1)]
    return _rows_from_eqs(eqs, nv)


def _rank(rows: list[list[F]]) -> int:
    if not rows:
        return 0
    if em is not None:
        return em.rank(em.matrix(rows))
    return _rank_local(rows)                              # pragma: no cover


def _rank_local(rows):                                    # pragma: no cover
    M = [r[:] for r in rows]
    r = 0
    ncol = len(M[0])
    for c in range(ncol):
        piv = None
        for i in range(r, len(M)):
            if M[i][c] != 0:
                piv = i
                break
        if piv is None:
            continue
        M[r], M[piv] = M[piv], M[r]
        pv = M[r][c]
        M[r] = [x / pv for x in M[r]]
        for i in range(len(M)):
            if i != r and M[i][c] != 0:
                f = M[i][c]
                M[i] = [a - f * b for a, b in zip(M[i], M[r])]
        r += 1
        if r == len(M):
            break
    return r


def _entries_determined(inst: dict, use_q: bool, kind: str = "coeff") -> dict:
    """How many of the 2n-1 entry variables are pinned by the LINEARISED system
    (each distinct monomial an independent unknown)?"""
    if kind == "power":
        rows, rhs, monos, deg1 = _power_sum_system(inst, use_q=use_q)
    else:
        rows, rhs, monos, deg1 = _linearised_system(inst, use_q=use_q)
    base = _rank(rows)
    determined = 0
    for i, col in deg1.items():
        e = [F(0)] * len(monos)
        e[col] = F(1)
        if _rank(rows + [e]) == base:
            determined += 1
    return {"determined": determined, "entries_total": 2 * inst["n"] - 1,
            "monomials": len(monos), "equations": len(rows), "rank": base,
            "nullity": len(monos) - base}


# ---------------------------------------------------------------------------
# attacks
# ---------------------------------------------------------------------------

def attack_linearised_solve(inst: dict) -> bool:
    """Solve the coefficient system by exact linear algebra after linearising it
    (every monomial an independent unknown), then read the degree-1 variables."""
    rows, rhs, monos, deg1 = _linearised_system(inst, use_q=True)
    if em is None:                                        # pragma: no cover
        return False
    sol = em.solve(em.matrix(rows), [F(x) for x in rhs])
    if sol is None:
        return False
    cand = [None] * len(inst["ask"])
    st = _structure(inst)
    n = inst["n"]
    for i in range(n):
        col = deg1.get(i)
        val = sol[col] if col is not None else F(0)
        cand[st["diag_idx"][i]] = _qj(val)
    for i in range(n - 1):
        col = deg1.get(n + i)
        val = sol[col] if col is not None else F(0)
        cand[st["off_idx"][i]] = _qj(val)
    ok, _ = verify(inst, cand)
    return ok


def attack_newton_power_sums(inst: dict) -> bool:
    """The spectral shortcut: Newton's identities give tr(A^k) from p with no
    root-finding.  Do those power sums leak the entries?  Uses p ONLY, which is
    what a solver has before noticing that q is the same problem one size down."""
    rows, rhs, monos, deg1 = _power_sum_system(inst, use_q=False)
    if em is None:                                        # pragma: no cover
        return False
    sol = em.solve(em.matrix(rows), [F(x) for x in rhs])
    if sol is None:
        return False
    st = _structure(inst)
    n = inst["n"]
    cand = [None] * len(inst["ask"])
    for i in range(n):
        col = deg1.get(i)
        cand[st["diag_idx"][i]] = _qj(sol[col] if col is not None else F(0))
    for i in range(n - 1):
        col = deg1.get(n + i)
        cand[st["off_idx"][i]] = _qj(sol[col] if col is not None else F(0))
    ok, _ = verify(inst, cand)
    return ok


def _residual(inst: dict, d: list[F], offs: list[F], st: dict) -> int:
    """Number of matched coefficients of p and q (higher is better)."""
    e = [st["b"][i] * offs[i] for i in range(len(offs))]
    got_p = _tridiag_charpoly(d, e)
    got_q = _tridiag_charpoly(d[1:], e[1:])
    tp = st["target_p"]
    tq = st["target_q"]
    score = sum(1 for a, b in zip(got_p, tp) if a == b)
    score += sum(1 for a, b in zip(got_q, tq) if a == b)
    return score


def attack_greedy_hill_climb(inst: dict, rng: random.Random,
                             restarts: int = 12, steps: int = 400) -> bool:
    """In-context attack: start from the freely deducible entries and change one
    entry at a time, keeping any change that matches more coefficients."""
    n = inst["n"]
    b = inst["language_bounds"]
    grid = _grid(b["num_max"], b["den_max"])
    nz = [v for v in grid if v != 0]
    st = _structure(inst)
    for _r in range(restarts):
        d = [st["d1"]] + [rng.choice(grid) for _ in range(n - 1)]
        offs = [st["c1"]] + [rng.choice(nz) for _ in range(n - 2)]
        best = _residual(inst, d, offs, st)
        for _s in range(steps):
            i = rng.randrange(1, 2 * n - 2)
            if i < n:
                old = d[i]
                d[i] = rng.choice(grid)
            else:
                j = i - n + 1
                old = offs[j]
                offs[j] = rng.choice(nz)
            sc = _residual(inst, d, offs, st)
            if sc >= best:
                best = sc
            else:
                if i < n:
                    d[i] = old
                else:
                    offs[i - n + 1] = old
            if best == 2 * n + 1:
                cand = [None] * len(inst["ask"])
                for t, idx in enumerate(st["diag_idx"]):
                    cand[idx] = _qj(d[t])
                for t, idx in enumerate(st["off_idx"]):
                    cand[idx] = _qj(offs[t])
                ok, _ = verify(inst, cand)
                if ok:
                    return True
    return False


def attack_random_restart(inst: dict, rng: random.Random,
                          samples: int = 20000) -> bool:
    """Sample structure-aware candidates and test them."""
    truth = None
    st = _structure(inst)
    for _ in range(samples):
        cand = random_candidate(inst, rng)
        n = inst["n"]
        d = [_qf(cand[i]) for i in st["diag_idx"]]
        offs = [_qf(cand[i]) for i in st["off_idx"]]
        if _residual(inst, d, offs, st) == 2 * n + 1:
            ok, _ = verify(inst, cand)
            if ok:
                return True
    return False


def attack_symmetric_ansatz(inst: dict) -> bool:
    """The obvious by-hand ansatz: guess that the missing entry of each edge
    equals the published one (A symmetric), or its negative, and fit the
    diagonal by the trace.  Cheap, and it is what a solver reaches for first."""
    n = inst["n"]
    st = _structure(inst)
    for sign in (F(1), F(-1)):
        offs = [sign * st["b"][i] for i in range(n - 1)]
        d = [st["d1"]] * 1 + [st["trace"] / n] * (n - 1)
        cand = [None] * len(inst["ask"])
        for t, idx in enumerate(st["diag_idx"]):
            cand[idx] = _qj(d[t])
        for t, idx in enumerate(st["off_idx"]):
            cand[idx] = _qj(offs[t])
        ok, _ = verify(inst, cand)
        if ok:
            return True
    return False


# ---------------------------------------------------------------------------
# escalation
# ---------------------------------------------------------------------------

def escalate(params: dict) -> dict | str | None:
    """Harder parameters.

    Axes, in order of preference and at FIXED answer length:
      1. num_max  -- entry height: more entropy per element, same element count
      2. den_max  -- denominators: same
      3. b_num_max -- height of the published entry of each edge
    Only the third step in the cycle raises n, which is the one axis that
    lengthens the answer (by 2 elements).
    """
    p = {k: v for k, v in params.items()}
    rounds = p.pop("_escalations", 0)
    steps = [
        {"num_max": 2.0, "den_max": 1, "b_num_max": 2.0, "n": 0},
        {"num_max": 1.7, "den_max": 1, "b_num_max": 1.5, "n": 0},
        {"num_max": 1.4, "den_max": 0, "b_num_max": 1.5, "n": 1},
    ]
    step = steps[rounds % len(steps)]
    q = dict(p)
    q["num_max"] = int(p["num_max"] * step["num_max"])
    q["den_max"] = p["den_max"] + step["den_max"]
    q["b_num_max"] = int(p["b_num_max"] * step["b_num_max"])
    q["n"] = p["n"] + step["n"]
    q["scramble"] = True
    q["_escalations"] = rounds + 1
    chars, elems = _answer_size({k: v for k, v in q.items()
                                 if not k.startswith("_")})
    if chars > MAX_ANSWER_CHARS or elems > MAX_ANSWER_ELEMENTS:
        return "cap_bound"
    _, ops = _reference_solve(make_instance(seed=1,
                                            **{k: v for k, v in q.items()
                                               if not k.startswith("_")}))
    if ops > MAX_ROUTE_OPERATIONS:
        return "cap_bound"
    return q


def _answer_size(params: dict) -> tuple[int, int]:
    inst = make_instance(seed=3, **params)
    ans = inst["answer"]
    text = ", ".join(_fmt(_qf(v)) for v in ans)
    return len(text), len(ans)


# ---------------------------------------------------------------------------
# selftest
# ---------------------------------------------------------------------------

def _perturbations(inst: dict, ans: list, rng: random.Random) -> list[Any]:
    out = []
    a = [list(v) for v in ans]
    out.append(a[:-1])                                    # drop one
    b = [list(v) for v in ans]
    b[0], b[1] = b[1], b[0]                               # swap two
    out.append(b)
    c = [list(v) for v in ans]
    c.append(list(c[-1]))                                 # duplicate
    out.append(c)
    out.append([])                                        # empty
    d = [list(v) for v in ans]
    d[rng.randrange(len(d))] = [10 ** 6, 1]               # out of range
    out.append(d)
    e = [list(v) for v in ans]
    e[0] = [e[0][0], 0]                                   # zero denominator
    out.append(e)
    f = [list(v) for v in ans]
    st = _structure(inst)
    f[st["off_idx"][1]] = [0, 1]                          # break the graph
    out.append(f)
    g = [list(v) for v in ans]
    g[st["diag_idx"][2]] = [_qf(g[st["diag_idx"][2]]).numerator + 1,
                            _qf(g[st["diag_idx"][2]]).denominator]
    out.append(g)                                         # one entry off by a bit
    out.append("total nonsense with no tags")
    out.append([[1, 1]] * len(ans))                       # constant answer
    out.append([[1, 1, 1]] + [list(v) for v in ans[1:]])  # wrong shape
    out.append([["x", 1]] + [list(v) for v in ans[1:]])   # non-integer
    # the sharpest one: a DIFFERENT tridiagonal matrix with the SAME p but a
    # different trailing characteristic polynomial.  It must be rejected on q,
    # which is what shows q is load-bearing rather than decorative.
    alt = _peel_with(inst, _shifted_q(inst))
    if alt is not None:
        out.append(alt)
    return out


def _shifted_q(inst: dict) -> list[F]:
    q = [_qf(x) for x in inst["q"]]
    q2 = list(q)
    q2[0] = q2[0] + 1
    return q2


def _peel_with(inst: dict, q2: list[F]) -> list[list[int]] | None:
    """Run the peel with a substituted q; returns a matrix with the same p and a
    different A^, or None when the substituted q does not admit a realisation."""
    st = _structure(inst)
    n = inst["n"]
    r_prev = [_qf(x) for x in inst["p"]]
    r_cur = list(q2)
    ds, cs = [], []
    for i in range(n - 1):
        m = len(r_prev) - 1
        t = r_prev[m - 1] - (r_cur[m - 2] if m >= 2 else F(0))
        ds.append(-t)
        R = list(r_prev)
        for k in range(len(r_cur)):
            R[k + 1] -= r_cur[k]
            R[k] -= t * r_cur[k]
        R = _poly_trim(R)
        if len(R) - 1 != m - 2:
            return None
        lead = R[-1]
        cs.append(-lead / st["b"][i])
        r_prev, r_cur = r_cur, [x / lead for x in R]
    ds.append(-r_prev[0])
    out = [None] * len(inst["ask"])
    for i, idx in enumerate(st["diag_idx"]):
        out[idx] = _qj(ds[i])
    for i, idx in enumerate(st["off_idx"]):
        out[idx] = _qj(cs[i])
    return out


def selftest(seeds: int = 8, verbose: bool = False) -> dict:
    report: dict[str, Any] = {}
    ship = DIFFICULTY[SHIPPING_DIFFICULTY]
    rng = random.Random(20260906)

    # ---------------- G1
    ok = tot = 0
    for name, prm in DIFFICULTY.items():
        for s in range(seeds):
            inst = make_instance(seed=1000 + s, **prm)
            good, why = verify(inst, inst["answer"])
            tot += 1
            ok += 1 if good else 0
            if not good and verbose:
                print("G1 FAIL", name, s, why)
    report["G1_planted_verifies"] = {"ok": ok, "total": tot, "pass": ok == tot}

    # ---------------- G2
    reasons = set()
    inst = make_instance(seed=11, **ship)
    for bad in _perturbations(inst, inst["answer"], rng):
        good, why = verify(inst, bad)
        if good:
            reasons.add("ACCEPTED A CORRUPTION")
        else:
            reasons.add(re.sub(r"-?\d+(/\d+)?", "N", why))
    alt = _peel_with(inst, _shifted_q(inst))
    alt_ok, alt_why = verify(inst, alt) if alt is not None else (True, "not built")
    report["G2_rejects_corruption"] = {
        "distinct_reasons": len(reasons),
        "corruptions_tested": len(_perturbations(inst, inst["answer"],
                                                 random.Random(1))),
        "same_p_different_q_rejected": (not alt_ok),
        "same_p_different_q_reason": alt_why,
        "pass": (len(reasons) >= 5 and "ACCEPTED A CORRUPTION" not in reasons
                 and not alt_ok),
    }

    # ---------------- G3
    ans_text = ", ".join(_fmt(_qf(v)) for v in inst["answer"])
    reply = ("Let me peel the path from v0.\n\nAfter the divisions I get the "
             "entries below.\n\n<answer>%s</answer>\n\nHope that helps." % ans_text)
    parsed = parse_answer(reply)
    rt_ok = parsed == [list(v) for v in inst["answer"]]
    untagged = parse_answer("so the entries come out as %s -- that is the matrix."
                            % ans_text) == [list(v) for v in inst["answer"]]
    fenced = parse_answer("```\n<answer>[%s]</answer>\n```" % ans_text) == \
        [list(v) for v in inst["answer"]]
    junk_ok = parse_answer("there is no answer here") is None and \
        parse_answer("<answer>banana</answer>") is None and \
        parse_answer("<answer>1, 2, x</answer>") is None
    report["G3_round_trip"] = {"parsed_ok": bool(rt_ok), "rejects_junk": bool(junk_ok),
                               "parses_untagged_list": bool(untagged),
                               "parses_fenced_json_list": bool(fenced),
                               "pass": bool(rt_ok and junk_ok and untagged and fenced)}

    # ---------------- G4
    inst = make_instance(seed=23, **ship)
    truth = [list(v) for v in inst["answer"]]
    trials = 200_000
    hits = 0
    r4 = random.Random(4242)
    for _ in range(trials):
        if random_candidate(inst, r4) == truth:
            hits += 1
    full_trials = 2000
    full_hits = 0
    for _ in range(full_trials):
        cand = random_candidate(inst, r4)
        good, _why = verify(inst, cand)
        if good:
            full_hits += 1
    space = search_space(inst)
    naive = naive_search_space(inst)
    report["G4_guess_resistance"] = {
        "trials": trials, "hits": hits,
        "full_verify_trials": full_trials, "full_verify_hits": full_hits,
        "structure_aware_space": space, "analytic_p": 1.0 / space,
        "naive_space": naive, "naive_analytic_p": 1.0 / naive,
        "pass": hits == 0 and full_hits == 0 and 1.0 / space < 1e-6,
    }

    # ---------------- G5
    demo_inst = make_instance(seed=5, **DIFFICULTY["demo"])
    t0 = time.time()
    exact_demo = enumerate_all(demo_inst)
    demo_sec = time.time() - t0
    demo_grid = (len(_grid(DIFFICULTY["demo"]["num_max"], DIFFICULTY["demo"]["den_max"]))
                 ** DIFFICULTY["demo"]["n"]) * \
        ((len(_grid(DIFFICULTY["demo"]["num_max"], DIFFICULTY["demo"]["den_max"])) - 1)
         ** (DIFFICULTY["demo"]["n"] - 1))

    # baseline: the strongest attack, brute force over the structure-aware space
    inst = make_instance(seed=23, **ship)
    st = _structure(inst)
    b = inst["language_bounds"]
    grid = _grid(b["num_max"], b["den_max"])
    nz = [v for v in grid if v != 0]
    n = inst["n"]
    probe = 20000
    r5 = random.Random(99)
    t0 = time.time()
    for _ in range(probe):
        d = [st["d1"]] + [r5.choice(grid) for _ in range(n - 1)]
        offs = [st["c1"]] + [r5.choice(nz) for _ in range(n - 2)]
        _residual(inst, d, offs, st)
    rate = probe / max(time.time() - t0, 1e-9)
    space = search_space(inst)
    ops_per_candidate = 10 * n                    # three-term recursion, both polys
    mech_ops = space * ops_per_candidate
    mech_sec = space / rate
    ref_ans, ref_ops = _reference_solve(inst)
    t0 = time.time()
    for _ in range(200):
        _reference_solve(inst)
    ref_sec = (time.time() - t0) / 200

    dens_trials = 20000
    dens_hits = 0
    r5b = random.Random(777)
    for _ in range(dens_trials):
        if random_candidate(inst, r5b) == truth:
            dens_hits += 1

    report["G5_density_and_cost"] = {
        "shipping_valid_answer_count": 1,
        "shipping_valid_answer_count_basis": (
            "arXiv:1604.02195, final corollary of Section 3 (G = the path P_n) plus "
            "uniqueness of the continued-fraction expansion of q/p: p and q are monic "
            "of consecutive degree, so the Euclidean division p = (x-d_1)q - e_1 r has "
            "a monic linear quotient and a remainder of degree exactly n-2, forcing "
            "d_1, e_1 and r, and (q,r) is the same problem one vertex shorter.  Exactly "
            "one matrix over Q -- and over C -- realises the published data."),
        "shipping_density": 1.0 / space,
        "shipping_density_sampled_hits": dens_hits,
        "shipping_density_sampled_trials": dens_trials,
        "exact_count_demo": exact_demo,
        "exact_count_demo_grid": demo_grid,
        "exact_count_demo_seconds": demo_sec,
        "strongest_attack": ("exhaustive enumeration of the certificate language with "
                             "both characteristic polynomials recomputed per candidate, "
                             "after the two freely deducible entries are fixed"),
        "mechanical_candidates_shipping": space,
        "mechanical_ops_shipping": mech_ops,
        "mechanical_seconds_shipping_extrapolated": mech_sec,
        "baseline_wall_clock_sec": mech_sec,
        "baseline_candidates_per_sec": rate,
        "compact_ops_shipping": ref_ops,
        "compact_seconds_shipping": ref_sec,
        "gap_mechanical_over_compact": mech_ops / max(ref_ops, 1),
        "pass": (exact_demo == 1 and dens_hits == 0 and mech_ops > 1e9),
    }

    # ---------------- G6
    att = {"linearised_coefficient_solve": {"successes": 0, "attempts": 0},
           "newton_power_sums_p_only": {"successes": 0, "attempts": 0},
           "greedy_coefficient_hill_climb": {"successes": 0, "attempts": 0},
           "random_restart_structure_aware": {"successes": 0, "attempts": 0},
           "symmetric_or_antisymmetric_ansatz": {"successes": 0, "attempts": 0}}
    r6 = random.Random(6161)
    det_p_only = det_pq = None
    nullity = None
    for s in range(8):
        i6 = make_instance(seed=300 + s, **ship)
        att["linearised_coefficient_solve"]["attempts"] += 1
        att["linearised_coefficient_solve"]["successes"] += \
            1 if attack_linearised_solve(i6) else 0
        att["newton_power_sums_p_only"]["attempts"] += 1
        att["newton_power_sums_p_only"]["successes"] += \
            1 if attack_newton_power_sums(i6) else 0
        att["greedy_coefficient_hill_climb"]["attempts"] += 1
        att["greedy_coefficient_hill_climb"]["successes"] += \
            1 if attack_greedy_hill_climb(i6, r6) else 0
        att["random_restart_structure_aware"]["attempts"] += 1
        att["random_restart_structure_aware"]["successes"] += \
            1 if attack_random_restart(i6, r6) else 0
        att["symmetric_or_antisymmetric_ansatz"]["attempts"] += 1
        att["symmetric_or_antisymmetric_ansatz"]["successes"] += \
            1 if attack_symmetric_ansatz(i6) else 0
        if s == 0:
            det_p_only = _entries_determined(i6, use_q=False, kind="power")
            det_pq = _entries_determined(i6, use_q=True, kind="power")
            det_coeff = _entries_determined(i6, use_q=True, kind="coeff")

    ref_solved = 0
    for s in range(8):
        i6 = make_instance(seed=300 + s, **ship)
        a, _o = _reference_solve(i6)
        good, _why = verify(i6, a) if a is not None else (False, "no")
        ref_solved += 1 if good else 0

    report["G6_adversary_panel"] = {
        "pass": all(v["successes"] == 0 for v in att.values()),
        "attacks": att,
        "reference_algorithm": {
            "name": ("root-free de Boor-Golub peel: the continued-fraction "
                     "expansion of q/p by n-1 Euclidean divisions"),
            "complexity": "O(n^2) exact rational operations",
            "operations": ref_ops,
            "wall_clock_sec": ref_sec,
            "solves": "%d/8, as expected on Track B" % ref_solved,
        },
        "spectral_leak_measurement": {
            "note": ("Newton's identities give the power sums tr(A^k) from p with no "
                     "root-finding; this measures how much they leak.  A variable is "
                     "counted as determined when the linearised system (every monomial "
                     "in the entries an independent unknown) pins it.  The compact "
                     "route is NOT a linear read-off: it is the iterated peel, and the "
                     "power-sum differences are an alternative entrance to that same "
                     "recursion, not a shortcut past it."),
            "power_sums_p_only": det_p_only,
            "power_sums_p_and_q": det_pq,
            "coefficients_p_and_q": det_coeff,
        },
    }

    # ---------------- G7
    esc = escalate(dict(ship))
    esc_ok = False
    esc_chars = esc_elems = None
    moved = []
    if isinstance(esc, dict):
        clean = {k: v for k, v in esc.items() if not k.startswith("_")}
        i7 = make_instance(seed=77, **clean)
        esc_ok, _ = verify(i7, i7["answer"])
        esc_chars, esc_elems = _answer_size(clean)
        moved = [k for k in ("n", "num_max", "den_max", "b_num_max")
                 if clean.get(k) != ship.get(k)]
    dbl = dict(ship)
    dbl["n"] = ship["n"] * 2
    i7b = make_instance(seed=78, **dbl)
    dbl_ok, _ = verify(i7b, i7b["answer"])
    _, dbl_ops = _reference_solve(i7b)

    ladder = []
    cur = dict(ship)
    for _ in range(6):
        nxt = escalate(dict(cur))
        if not isinstance(nxt, dict):
            ladder.append({"result": nxt})
            break
        clean = {k: v for k, v in nxt.items() if not k.startswith("_")}
        ch, el = _answer_size(clean)
        i_l = make_instance(seed=5, **clean)
        _, ops_l = _reference_solve(i_l)
        ladder.append({"params": clean, "answer_chars": ch, "answer_elements": el,
                       "route_ops": ops_l})
        cur = nxt
    report["G7_scales"] = {
        "escalate": esc if isinstance(esc, dict) else {"result": esc},
        "escalated_builds_and_verifies": bool(esc_ok),
        "escalated_answer_chars": esc_chars,
        "escalated_answer_elements": esc_elems,
        "moved_params": moved,
        "size_doubled_n_builds_and_verifies": bool(dbl_ok),
        "size_doubled_route_ops": dbl_ops,
        "ladder": ladder,
        "pass": bool(esc_ok and dbl_ok and len(moved) >= 2),
    }

    # ---------------- G8
    inv_ok = inv_tot = 0
    transformed_verifies = 0
    keys = []
    r8 = random.Random(8888)
    for s in range(24):
        i8 = make_instance(seed=500 + s, **ship)
        k0 = canonical_key(i8)
        keys.append(k0)
        for t in range(5):
            # (relabelling sigma, transpose?) -- t=2,3,4 are the compositions
            perm = list(range(i8["n"]))
            if t != 1:
                r8.shuffle(perm)
            sigma = {i: perm[i] for i in range(i8["n"])}
            j8, carry = _remap(i8, sigma, transpose=(t in (1, 2, 3)))
            inv_tot += 1
            if canonical_key(j8) == k0:
                inv_ok += 1
            good, _why = verify(j8, carry)
            if good:
                transformed_verifies += 1
    report["G8_canonical_key"] = {
        "invariance_ok": inv_ok, "invariance_total": inv_tot,
        "transformed_instance_verifies": transformed_verifies,
        "keys_total": len(keys), "distinct_keys": len(set(keys)),
        "pass": (inv_ok == inv_tot and transformed_verifies == inv_tot
                 and len(set(keys)) == len(keys)),
    }

    # ---------------- G9
    inst = make_instance(seed=23, **ship)
    ans_text = ", ".join(_fmt(_qf(v)) for v in inst["answer"])
    chars = len(ans_text)
    elems = len(inst["answer"])
    tokens = len(re.findall(r"[0-9]+|[^\s0-9]", ans_text))
    per_preset = {}
    ops_all = []
    for name, prm in DIFFICULTY.items():
        ii = make_instance(seed=23, **prm)
        txt = ", ".join(_fmt(_qf(v)) for v in ii["answer"])
        _, oo = _reference_solve(ii)
        per_preset[name] = {"chars": len(txt), "elements": len(ii["answer"]),
                            "route_ops": oo}
    for s in range(150):
        ii = make_instance(seed=900 + s, **ship)
        _, oo = _reference_solve(ii)
        ops_all.append(oo)
    ops_all.sort()
    median_ops = ops_all[len(ops_all) // 2]
    within = (chars <= MAX_ANSWER_CHARS and elems <= MAX_ANSWER_ELEMENTS
              and median_ops <= MAX_ROUTE_OPERATIONS and ops_all[-1] <= MAX_ROUTE_OPERATIONS)
    report["G9_no_tool_suitability"] = {
        "pass": bool(within),
        "arms": {"bare": {"solved": 0, "attempts": 0},
                 "hinted": {"solved": 0, "attempts": 0},
                 "placebo": {"solved": 0, "attempts": 0}},
        "arms_note": ("three-arm diagnostic not run by the module's selftest (no "
                      "OPENROUTER_API_KEY in this environment); recorded, never gated"),
        "hinted_minus_placebo": None,
        "hinted_verdict": None,
        "answer_chars": chars, "answer_tokens": tokens, "answer_elements": elems,
        "intended_route_operations": median_ops,
        "intended_route_operations_note": (
            "median over 150 shipping-preset seeds of the reference algorithm's own "
            "operation counter (every rational +, -, * and / the continued-fraction "
            "peel performs)"),
        "route_operations_distribution": {
            "min": ops_all[0], "median": median_ops,
            "p95": ops_all[int(0.95 * len(ops_all))], "max": ops_all[-1],
            "seeds": len(ops_all), "over_cap": sum(1 for o in ops_all
                                                   if o > MAX_ROUTE_OPERATIONS)},
        "caps": {"chars": MAX_ANSWER_CHARS, "elements": MAX_ANSWER_ELEMENTS,
                 "operations": MAX_ROUTE_OPERATIONS},
        "diagnostic_not_gated": True,
        "per_preset": per_preset,
    }

    report["all_passed"] = all(v.get("pass") for k, v in report.items()
                               if k.startswith("G"))
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship)
    cl = dict(CERTIFICATE_LANGUAGE)
    cl["bounds"] = _language_bounds(_params(**ship))
    report["certificate_language"] = cl
    report["problem_profile"] = PROBLEM_PROFILE
    return report


# ---------------------------------------------------------------------------
# instance transformations (G8)
# ---------------------------------------------------------------------------

def _remap(inst: dict, sigma: dict[int, int], transpose: bool) -> tuple[dict, list]:
    """Relabel vertices by sigma and/or transpose A.  Returns the new instance
    and the ORIGINAL answer carried through the transformation."""
    j = json.loads(json.dumps(inst))
    def m(u):
        return sigma[u]
    def pos(u, v):
        u2, v2 = m(u), m(v)
        return (v2, u2) if transpose else (u2, v2)
    j["edges"] = sorted([sorted([m(u), m(v)]) for u, v in inst["edges"]])
    j["given"] = sorted([[*pos(u, v), val] for u, v, val in inst["given"]],
                        key=lambda t: (t[0], t[1]))
    new_ask = [pos(u, v) for u, v in inst["ask"]]
    order = sorted(range(len(new_ask)), key=lambda i: new_ask[i])
    j["ask"] = [list(new_ask[i]) for i in order]
    j["answer"] = [inst["answer"][i] for i in order]
    j["v0"] = m(inst["v0"])
    carried = [inst["answer"][i] for i in order]
    return j, carried


def _relabel(inst: dict, rng: random.Random) -> tuple[dict, list]:
    n = inst["n"]
    perm = list(range(n))
    rng.shuffle(perm)
    sigma = {i: perm[i] for i in range(n)}
    return _remap(inst, sigma, False)


def _transpose(inst: dict) -> tuple[dict, list]:
    n = inst["n"]
    sigma = {i: i for i in range(n)}
    return _remap(inst, sigma, True)


if __name__ == "__main__":                              # pragma: no cover
    rep = selftest(verbose=True)
    print(json.dumps(rep, indent=1, sort_keys=True, default=str))
