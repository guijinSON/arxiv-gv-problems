"""Candidate generator for the consistency problem for modular lattices.

Paper: C. Herrmann, Y. Tsukamoto, M. Ziegler, "On the consistency problem for
modular lattices and related structures", arXiv:1607.03315 (math.LO).

Native objects.  Section 3 ("Frames") is the paper's central tool: Lemma 5
(\\lab{fex}) builds a von Neumann 4-frame  abar = (a_1..a_4, a_ij, a_bot, a_top)
of the subspace lattice L(V), V = V_1^4, and shows

  (iii)(a) G(L,abar) = { g : g+a_1 = g+a_2 = a_1+a_2, g cap a_1 = g cap a_2 = a_bot }
           is a group under a fixed LATTICE TERM t(x,y,zbar);
  (iii)(b) Gamma_abar(f) = { v - eps(f v) } is an isomorphism GL(a_1) -> G(L,abar);
  (iii)(c) the generated subgroup acts fixed point free iff
           a_12 cap g_1 cap ... cap g_k = a_bot.

This module ships exactly those objects: subspaces of F_q^{4d} handed to the
solver as basis matrices, a conjunction of lattice equations built only from
meet and join, and a witness that is a tuple of subspaces.  Verification is
exact linear algebra over F_q (RREF, Zassenhaus intersection) -- no floats.

Generation is inverse: f_1, f_2 in GL(d,q) are sampled FIRST, the witnesses are
g_i = Gamma_abar(f_i), and the published constants are C_1 = t(g_1,g_2,abar),
C_2 = t(g_2,g_1,abar).  make_instance never searches.

STATUS: REJECTED on H.  See REJECTED.md.  The module is retained as evidence
per the contract ("If you built a module, KEEP it").
"""

from __future__ import annotations

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
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover
    exact_matrices = rationals = None


TRACK = "B"          # claimed at build time; the measurement in REJECTED.md
                     # shows the Track B gap does not exist.

# ----------------------------------------------------------------- op counter
class Ops:
    __slots__ = ("n",)

    def __init__(self):
        self.n = 0

OPS = Ops()


# ------------------------------------------------------- F_q linear algebra --
def rref(rows, q, count=False):
    m = [list(r) for r in rows]
    if not m:
        return ()
    n = len(m[0])
    piv = 0
    for c in range(n):
        r = None
        for i in range(piv, len(m)):
            if m[i][c] % q:
                r = i
                break
        if r is None:
            continue
        m[piv], m[r] = m[r], m[piv]
        iv = pow(m[piv][c], q - 2, q)
        m[piv] = [(x * iv) % q for x in m[piv]]
        if count:
            OPS.n += n
        for i in range(len(m)):
            if i != piv and m[i][c] % q:
                f = m[i][c] % q
                m[i] = [(m[i][j] - f * m[piv][j]) % q for j in range(n)]
                if count:
                    OPS.n += n
        piv += 1
        if piv == len(m):
            break
    return tuple(tuple(x % q for x in r) for r in m[:piv])


def join(A, B, q, count=False):
    return rref(list(A) + list(B), q, count)


def meet(A, B, q, count=False):
    if not A or not B:
        return ()
    n = len(A[0])
    block = [list(r) + list(r) for r in A] + [list(r) + [0] * n for r in B]
    R = rref(block, q, count)
    out = [r[n:] for r in R if all(x % q == 0 for x in r[:n])]
    return rref(out, q, count)


def full(n, q):
    return tuple(tuple(1 if j == i else 0 for j in range(n)) for i in range(n))


def mat_mul(A, B, q, count=False):
    n, k, m = len(A), len(B), len(B[0])
    C = [[0] * m for _ in range(n)]
    for i in range(n):
        for t in range(k):
            a = A[i][t] % q
            if a:
                Bt = B[t]
                Ci = C[i]
                for j in range(m):
                    Ci[j] = (Ci[j] + a * Bt[j]) % q
        if count:
            OPS.n += k * m
    return [tuple(r) for r in C]


def mat_inv(A, q, count=False):
    n = len(A)
    m = [list(A[i]) + [1 if j == i else 0 for j in range(n)] for i in range(n)]
    R = rref(m, q, count)
    if len(R) != n:
        return None
    for i in range(n):
        for j in range(n):
            if R[i][j] != (1 if i == j else 0):
                return None
    return [tuple(R[i][n:]) for i in range(n)]


def rand_gl(d, q, rng):
    while True:
        A = [tuple(rng.randrange(q) for _ in range(d)) for _ in range(d)]
        if mat_inv(A, q) is not None:
            return A


# ------------------------------------------------------ frames (Lemma fex) --
def build_frame(d, q, P=None):
    N = 4 * d
    a = {}
    for i in range(1, 5):
        a[i] = rref([tuple(1 if j == (i - 1) * d + r else 0 for j in range(N))
                     for r in range(d)], q)
    for j in range(2, 5):
        rows = []
        for r in range(d):
            v = [0] * N
            v[r] = 1
            v[(j - 1) * d + r] = (-1) % q
            rows.append(tuple(v))
        a[(1, j)] = rref(rows, q)
    for k in range(2, 5):
        for j in range(k + 1, 5):
            a[(k, j)] = meet(join(a[k], a[j], q), join(a[(1, k)], a[(1, j)], q), q)
    if P is not None:
        for key in list(a):
            a[key] = rref(mat_mul([list(r) for r in a[key]], P, q), q)
    return a


def gamma(f, d, q, P=None):
    N = 4 * d
    rows = []
    for r in range(d):
        v = [0] * N
        v[r] = 1
        for s in range(d):
            v[d + s] = (-f[s][r]) % q
        rows.append(tuple(v))
    S = rref(rows, q)
    if P is not None:
        S = rref(mat_mul([list(x) for x in S], P, q), q)
    return S


def term_t(x, y, a, q, count=False):
    """The paper's group-multiplication lattice term, Lemma fex(iii)(a)."""
    z1, z2, z3 = a[1], a[2], a[3]
    z12, z23 = a[(1, 2)], a[(2, 3)]
    u = meet(join(x, z23, q, count), join(z1, z3, q, count), q, count)
    u = meet(join(u, z12, q, count), join(z2, z3, q, count), q, count)
    u = meet(join(y, u, q, count), join(z1, z3, q, count), q, count)
    u = meet(join(u, z23, q, count), join(z1, z2, q, count), q, count)
    return u


# ------------------------------------------------------------------ profile --
PROBLEM_PROFILE = {
    "native_domain": "logic",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "von Neumann 4-frame of L(F_q^{4d}) given as 10 basis matrices",
        "conjunction of lattice equations in meet and join",
        "subspaces of F_q^{4d} given by basis matrices",
    ],
    "verification_operations": [
        "exact RREF over F_q",
        "subspace join (row-space sum) and Zassenhaus intersection",
        "canonical-form equality of subspaces",
        "rank/dimension comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "reduction recognition",
    "intuition_description": (
        "The four frame equations force every admissible subspace to be the "
        "graph of an invertible d x d matrix over the frame's own basis, so "
        "the lattice system collapses to matrix equations in GL(d,q); a "
        "solver without that observation searches the Grassmannian of "
        "d-subspaces of F_q^{4d}."
    ),
    "hardness_basis": (
        "MEASURED AND REJECTED.  The paper proves only unsolvability "
        "(Theorem 5c, Lemma 5(iv), from Theorem 3 = Adyan/Rabin/"
        "Bridson-Wilton); it fixes no finite parameter regime.  At every size "
        "whose witness fits the answer cap the domain-standard attack "
        "(frame-coordinatisation + Sylvester solve) succeeds; see REJECTED.md "
        "for the two numbers."
    ),
    "max_answer_tokens": 260,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (PROBLEM_PROFILE["intuition_type"] + ": "
                  + PROBLEM_PROFILE["intuition_description"]),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo":   {"d": 1, "q": 5},
    "easy":   {"d": 2, "q": 5},
    "medium": {"d": 2, "q": 11},
    "hard":   {"d": 3, "q": 7},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Each unknown meets the first two frame elements trivially and joins with "
    "either to their common join."
)
PLACEBO_HINT = (
    "The subspaces below are listed as row bases, so keeping the row and "
    "column bookkeeping straight matters throughout."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "Two d x 4d matrices over F_q, each in reduced row echelon form of "
        "rank d, listing a basis of a d-dimensional subspace of F_q^{4d} that "
        "is a complement of both a_1 and a_2 inside a_1 + a_2.  The set of "
        "subspaces satisfying those frame conditions is in bijection with "
        "GL(d,q), so the language has |GL(d,q)|^2 members."
    ),
    "bounds": {"unknowns": 2, "rows": "d", "cols": "4d", "entry_range": "0..q-1"},
}


def _gl_order(d, q):
    n = 1
    for i in range(d):
        n *= (q ** d - q ** i)
    return n


def _gauss_binom(n, k, q):
    num = 1
    den = 1
    for i in range(k):
        num *= (q ** (n - i) - 1)
        den *= (q ** (k - i) - 1)
    return num // den


# ---------------------------------------------------------- make_instance ---
def make_instance(n=None, seed=0, d=3, q=7, **kw):
    rng = random.Random(seed)
    N = 4 * d
    while True:
        P = [tuple(rng.randrange(q) for _ in range(N)) for _ in range(N)]
        if mat_inv(P, q) is not None:
            break
    a = build_frame(d, q, P)
    while True:
        f1 = rand_gl(d, q, rng)
        f2 = rand_gl(d, q, rng)
        g1 = gamma(f1, d, q, P)
        g2 = gamma(f2, d, q, P)
        # Lemma fex(iii)(c): fixed-point-free  <=>  a_12 cap g_1 cap g_2 = 0
        if meet(meet(a[(1, 2)], g1, q), g2, q) == ():
            break
    C1 = term_t(g1, g2, a, q)
    C2 = term_t(g2, g1, a, q)
    frame = {}
    for k, v in a.items():
        key = "a%d" % k if isinstance(k, int) else "a%d%d" % k
        frame[key] = [list(r) for r in v]
    return {
        "id": "1607.03315",
        "q": q, "d": d, "N": N,
        "frame": frame,
        "C1": [list(r) for r in C1],
        "C2": [list(r) for r in C2],
        "answer": [[list(r) for r in g1], [list(r) for r in g2]],
    }


# ------------------------------------------------------------------ render --
def _mat_str(M):
    return "; ".join(" ".join(str(x) for x in row) for row in M)


def render(inst):
    q, d, N = inst["q"], inst["d"], inst["N"]
    L = []
    L.append("Work in the lattice L of all linear subspaces of the vector "
             "space V = F_%d^%d over the field F_%d = {0,...,%d} with "
             "arithmetic mod %d." % (q, N, q, q - 1, q))
    L.append("")
    L.append("For subspaces A, B of V write A + B for their sum (the join) "
             "and A & B for their intersection (the meet).  0 denotes the "
             "zero subspace and V the whole space.")
    L.append("")
    L.append("A subspace is written as a matrix: each row is a basis vector, "
             "entries separated by spaces, rows separated by ';'.  Two "
             "matrices denote the same subspace exactly when their row spaces "
             "agree.")
    L.append("")
    L.append("The following ten subspaces are given (they form a von Neumann "
             "4-frame of L):")
    for k in ["a1", "a2", "a3", "a4", "a12", "a13", "a14", "a23", "a24", "a34"]:
        L.append("  %-4s = %s" % (k, _mat_str(inst["frame"][k])))
    L.append("")
    L.append("Two further subspaces are given:")
    L.append("  C1   = %s" % _mat_str(inst["C1"]))
    L.append("  C2   = %s" % _mat_str(inst["C2"]))
    L.append("")
    L.append("Define, for subspaces X and Y of V, the lattice term")
    L.append("  t(X,Y) = ( ( ( Y + ( ( ( X + a23 ) & ( a1 + a3 ) ) + a12 ) "
             "& ( a2 + a3 ) ) & ( a1 + a3 ) ) + a23 ) & ( a1 + a2 ).")
    L.append("")
    L.append("Find subspaces X1 and X2 of V satisfying ALL of the following "
             "equations simultaneously:")
    L.append("  (1)  X1 + a1 = a1 + a2      and  X1 + a2 = a1 + a2")
    L.append("  (2)  X1 & a1 = 0            and  X1 & a2 = 0")
    L.append("  (3)  X2 + a1 = a1 + a2      and  X2 + a2 = a1 + a2")
    L.append("  (4)  X2 & a1 = 0            and  X2 & a2 = 0")
    L.append("  (5)  t(X1,X2) = C1")
    L.append("  (6)  t(X2,X1) = C2")
    L.append("  (7)  a12 & X1 & X2 = 0")
    L.append("")
    L.append("Equations (1)-(4) force dim X1 = dim X2 = %d.  Any pair of "
             "subspaces satisfying (1)-(7) is accepted; the pair need not be "
             "the one used to build the instance." % d)
    L.append("")
    L.append("Give your final answer inside <answer></answer> tags as JSON: a "
             "list of two matrices, each a list of %d rows of %d integers in "
             "0..%d, the rows being a basis of X1 and of X2 respectively."
             % (d, N, q - 1))
    L.append("Example format: <answer>[[[1,0,...],[0,1,...]],"
             "[[1,0,...],[0,1,...]]]</answer>")
    L.append("Output nothing else inside the tags.")
    s = "\n".join(L)
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        s += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        s += "\n\nHint: " + PLACEBO_HINT
    return s


# ------------------------------------------------------------ parse_answer --
def parse_answer(text):
    if not isinstance(text, str):
        return None
    m = re.findall(r"<answer>(.*?)</answer>", text, re.S | re.I)
    body = m[-1] if m else text
    body = body.replace("```json", " ").replace("```", " ").strip()
    try:
        v = json.loads(body)
        if (isinstance(v, list) and len(v) == 2
                and all(isinstance(M, list) and M and
                        all(isinstance(r, list) and
                            all(isinstance(x, int) for x in r) for r in M)
                        for M in v)):
            return [[list(r) for r in M] for M in v]
    except Exception:
        pass
    nums = re.findall(r"-?\d+", body)
    if not nums:
        return None
    return None


# ----------------------------------------------------------------- verify ---
def verify(inst, answer):
    q, d, N = inst["q"], inst["d"], inst["N"]
    if not isinstance(answer, list) or len(answer) != 2:
        return False, "answer must be a list of two matrices"
    subs = []
    for idx, M in enumerate(answer):
        if not isinstance(M, list) or len(M) == 0:
            return False, "X%d is not a non-empty matrix" % (idx + 1)
        for r in M:
            if not isinstance(r, list) or len(r) != N:
                return False, "X%d has a row of length != %d" % (idx + 1, N)
            for x in r:
                if not isinstance(x, int) or x < 0 or x >= q:
                    return False, ("X%d has entry %r outside 0..%d"
                                   % (idx + 1, x, q - 1))
        S = rref(M, q)
        if len(S) != d:
            return False, ("X%d has dimension %d, expected %d"
                           % (idx + 1, len(S), d))
        subs.append(S)
    a = {}
    for k in ["a1", "a2", "a3", "a4", "a12", "a13", "a14", "a23", "a24", "a34"]:
        v = rref(inst["frame"][k], q)
        a[int(k[1:]) if len(k) == 2 else (int(k[1]), int(k[2]))] = v
    X1, X2 = subs
    a12join = join(a[1], a[2], q)
    for idx, X in enumerate(subs):
        if join(X, a[1], q) != a12join:
            return False, "X%d + a1 != a1 + a2" % (idx + 1)
        if join(X, a[2], q) != a12join:
            return False, "X%d + a2 != a1 + a2" % (idx + 1)
        if meet(X, a[1], q) != ():
            return False, "X%d & a1 != 0" % (idx + 1)
        if meet(X, a[2], q) != ():
            return False, "X%d & a2 != 0" % (idx + 1)
    if term_t(X1, X2, a, q) != rref(inst["C1"], q):
        return False, "t(X1,X2) != C1"
    if term_t(X2, X1, a, q) != rref(inst["C2"], q):
        return False, "t(X2,X1) != C2"
    if meet(meet(a[(1, 2)], X1, q), X2, q) != ():
        return False, "a12 & X1 & X2 != 0 (assignment is trivial)"
    return True, "ok"


# ---------------------------------------------------- candidates / spaces ---
def random_candidate(inst, rng):
    """Structure-aware: sample a pair of subspaces already satisfying (1)-(4).

    A solver who reads (1)-(4) knows each X must be a d-dimensional complement
    of both a_1 and a_2 inside a_1 + a_2; those are exactly the images of
    GL(d,q) under Gamma.  We sample uniformly from that set, expressed in the
    instance's own scrambled basis, so no structural work is left free.
    """
    q, d = inst["q"], inst["d"]
    a = {}
    for k in ["a1", "a2"]:
        a[k] = rref(inst["frame"][k], q)
    b1 = list(a["a1"])
    b2 = list(a["a2"])
    out = []
    for _ in range(2):
        f = rand_gl(d, q, rng)
        rows = []
        for r in range(d):
            v = [0] * inst["N"]
            for c in range(inst["N"]):
                s = b1[r][c]
                for t2 in range(d):
                    s = (s - f[t2][r] * b2[t2][c]) % q
                v[c] = s
            rows.append(v)
        out.append([list(x) for x in rref(rows, q)])
    return out


def search_space(inst):
    return _gl_order(inst["d"], inst["q"]) ** 2


def enumerate_all(inst, cap=4_000_000):
    """Exact count of valid answers, over the structure-aware domain."""
    q, d = inst["q"], inst["d"]
    if _gl_order(d, q) ** 2 > cap:
        return None
    dom = _domain(inst)
    cnt = 0
    for X1 in dom:
        for X2 in dom:
            ok, _ = verify(inst, [[list(r) for r in X1], [list(r) for r in X2]])
            if ok:
                cnt += 1
    return cnt


def _all_gl(d, q):
    out = []
    for entries in itertools.product(range(q), repeat=d * d):
        M = [tuple(entries[i * d:(i + 1) * d]) for i in range(d)]
        if mat_inv(M, q) is not None:
            out.append(M)
    return out


def _domain(inst):
    """All subspaces satisfying frame conditions (1)-(2): the Gamma images."""
    q, d = inst["q"], inst["d"]
    b1 = list(rref(inst["frame"]["a1"], q))
    b2 = list(rref(inst["frame"]["a2"], q))
    N = inst["N"]
    out = []
    for f in _all_gl(d, q):
        rows = []
        for r in range(d):
            v = [0] * N
            for c in range(N):
                s = b1[r][c]
                for t2 in range(d):
                    s = (s - f[t2][r] * b2[t2][c]) % q
                v[c] = s
            rows.append(v)
        out.append(rref(rows, q))
    return out


def canonical_key(inst):
    """Basis-independent invariant: the conjugacy-class data of the planted
    pair read through the frame, computed from the PUBLISHED data only."""
    q, d = inst["q"], inst["d"]
    a = {}
    for k in ["a1", "a2", "a3", "a4", "a12", "a13", "a14", "a23", "a24", "a34"]:
        a[int(k[1:]) if len(k) == 2 else (int(k[1]), int(k[2]))] = \
            rref(inst["frame"][k], q)
    M1 = _read_matrix(inst["C1"], a, q, d)
    M2 = _read_matrix(inst["C2"], a, q, d)
    feats = []
    for M in (M1, M2):
        feats.append(tuple(_charpoly(M, q)))
        feats.append(_mat_order(M, q))
    P = mat_mul(M1, M2, q)
    feats.append(tuple(_charpoly(P, q)))
    feats.append(_mat_order(P, q))
    return "1607.03315|q=%d|d=%d|%s" % (q, d, "|".join(map(str, feats)))


def _charpoly(M, q):
    d = len(M)
    # Leverrier-Faddeev over F_q needs division by k; use expansion by
    # det(xI - M) via Hessenberg-free Bareiss on a small d instead.
    coeffs = []
    for k in range(d + 1):
        s = 0
        for S in itertools.combinations(range(d), k):
            sub = [[M[i][j] for j in S] for i in S]
            s = (s + _det(sub, q)) % q
        coeffs.append(s % q)
    return coeffs


def _det(M, q):
    n = len(M)
    if n == 0:
        return 1
    m = [list(r) for r in M]
    det = 1
    for c in range(n):
        p = None
        for i in range(c, n):
            if m[i][c] % q:
                p = i
                break
        if p is None:
            return 0
        if p != c:
            m[c], m[p] = m[p], m[c]
            det = (-det) % q
        det = (det * m[c][c]) % q
        iv = pow(m[c][c], q - 2, q)
        m[c] = [(x * iv) % q for x in m[c]]
        for i in range(c + 1, n):
            f = m[i][c] % q
            if f:
                m[i] = [(m[i][j] - f * m[c][j]) % q for j in range(n)]
    return det % q


def _mat_order(M, q):
    d = len(M)
    I = [tuple(1 if i == j else 0 for j in range(d)) for i in range(d)]
    A = [tuple(r) for r in M]
    k = 1
    while A != I and k < 4 * q ** d:
        A = mat_mul(A, M, q)
        k += 1
    return k


def _read_raw(S, a, q, d, count=False):
    """Coordinates of S in the frame basis (b1|b2): the matrix M with
    S = { (x, -x M) } in those coordinates.  Lemma fex(iii)(b) executed in
    the instance's own scrambled basis."""
    b1 = list(a[1])
    b2 = list(a[2])
    S = rref(S, q, count)
    if len(S) != d:
        return None
    N = len(b1[0])
    basis = b1 + b2
    Mt = [[basis[i][c] for i in range(2 * d)] for c in range(N)]
    coeffs = []
    for r in range(d):
        sol = _solve(Mt, [S[r][c] for c in range(N)], q, count)
        if sol is None:
            return None
        coeffs.append(sol)
    A = [tuple(coeffs[r][:d]) for r in range(d)]
    B = [tuple((-coeffs[r][d + i]) % q for i in range(d)) for r in range(d)]
    Ai = mat_inv(A, q, count)
    if Ai is None:
        return None
    return mat_mul(Ai, B, q, count)


def _read_matrix(S, a, q, d, count=False):
    """The group element of G(L,abar) that S represents, normalised so that
    a_12 (the identity of the group, Lemma fex(iii)(a)) reads as I."""
    J = _read_raw(a[(1, 2)], a, q, d, count)
    if J is None:
        return None
    Ji = mat_inv(J, q, count)
    if Ji is None:
        return None
    M = _read_raw(S, a, q, d, count)
    if M is None:
        return None
    return mat_mul(M, Ji, q, count)


def _write_matrix(F, a, q, d, count=False):
    """Inverse of _read_matrix: the subspace of G(L,abar) with that value."""
    J = _read_raw(a[(1, 2)], a, q, d, count)
    M = mat_mul(F, J, q, count)
    b1 = list(a[1])
    b2 = list(a[2])
    N = len(b1[0])
    rows = []
    for r in range(d):
        v = [0] * N
        for c in range(N):
            sv = b1[r][c]
            for t in range(d):
                sv = (sv - M[r][t] * b2[t][c]) % q
            v[c] = sv
        rows.append(v)
        if count:
            OPS.n += d * N
    return rref(rows, q, count)


def _solve(M, rhs, q, count=False):
    rows = len(M)
    cols = len(M[0])
    aug = [list(M[i]) + [rhs[i]] for i in range(rows)]
    R = rref(aug, q, count)
    sol = [0] * cols
    for r in R:
        piv = None
        for j in range(cols):
            if r[j] % q:
                piv = j
                break
        if piv is None:
            if r[cols] % q:
                return None
            continue
        sol[piv] = r[cols] % q
    return sol


# ------------------------------------------------------------- escalate -----
def escalate(params):
    """Two axes at FIXED answer length: raise q (entropy per atom) and raise
    the field again while d stays put, so the witness stays 2*d*4d integers.
    d is deliberately NOT raised: that would lengthen the answer."""
    q = params["q"]
    d = params["d"]
    nxt = {5: 11, 7: 13, 11: 23, 13: 29, 23: 47, 29: 59, 47: 97, 59: 101,
           97: 197, 101: 211}
    if q in nxt:
        return {"d": d, "q": nxt[q]}
    return "cap_bound"


NOTES = """
Definition fixed by: Section 2 (consistency problem), Section 3 Lemma 5
(\\lab{fex}) -- frame axioms, G(L,abar), the term t, Gamma, and the
fixed-point-free criterion (iii)(c).

What makes it easy: the paragraph immediately after Corollary 7
(\\lab{five}) -- the consistency problem for L(F^d_F) is solvable if and
only if there is a recursive dimension bound delta(n).  All of the paper's
hardness is unboundedness of the dimension; at any FIXED d the problem is
finite-dimensional linear algebra.

Attacks: the domain-standard attack is frame coordinatisation
(Lemma fex(iii)(b)) followed by a Sylvester solve; it succeeds on every
instance.  See REJECTED.md for the measured numbers.
"""
