"""Planted MinRank instances outside the superdetermined (easy) band.

Source paper: arXiv:2208.01442, Magali Bardet and Manon Bertin,
"Improvement of algebraic attacks for solving superdetermined MinRank
instances" (cs.CR / cs.IT / cs.SC).

See NOTES at the bottom of the header block for what each section of the
paper fixed.
"""

import hashlib
import itertools
import json
import os
import random
import re
import sys
import time
from math import comb, log2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:                                    # optional, repo-root helper library
    from gvlib import exact_matrices, rationals   # noqa: F401
except ImportError:                     # not present: stay standard-library-only
    exact_matrices = rationals = None


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "matrices M_0, M_1, ..., M_k over the prime field F_q",
        "the linear pencil M_x = M_0 + sum_i x_i M_i",
        "the coefficient vector x in F_q^k",
    ],
    "verification_operations": [
        "exact F_q linear combination of k+1 matrices",
        "Gaussian elimination over F_q (no floats anywhere)",
        "integer comparison of the resulting rank against the target r",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "duality",
    "intuition_description": (
        "rank(M_x) <= r is not a condition one can test coordinate by coordinate; "
        "the only handle is the dual object, the (n-r)-dimensional right kernel of "
        "M_x, each of whose vectors turns the rank condition into m equations that "
        "are linear in x -- a solver without that view is left enumerating q^k "
        "vectors and computing a rank for each."
    ),
    "hardness_basis": (
        "Track A: MinRank is NP-complete (Buss-Frandsen-Shallit, cited as [BFS99] in "
        "Section 1 of arXiv:2208.01442), and the shipped distribution is the standard "
        "planted one. The parameter regime is chosen to sit strictly OUTSIDE the "
        "superdetermined band that Section 4 of the paper shows is easy: Support-Minors "
        "linearisation solves at bidegree b=1 exactly when m*C(n,r+1) >= K*C(n,r), i.e. "
        "m(n-r) >= K(r+1); at the shipping preset that reads 70 >= 164, false by a "
        "factor 2.34, and the b=1 Macaulay matrix is 2100 x 4920, short of the 4919 "
        "independent equations linearisation needs by 2819. The Bardet et al. counting "
        "formula first turns positive at b=5, where the Macaulay matrix is "
        "150,381,330 x 146,611,080 (2.2e16 dense entries; 2^62.6 field operations and "
        "~200 GB even by sparse Wiedemann). Solutions are unique: k=40 < (m-r)(n-r)=49, "
        "so the expected number of spurious solutions is 2^-71.7."
    ),
    "max_answer_tokens": 96,
}

NATIVE = {
    "domain": "algebra",
    "core": "linear_algebra",
    "objects": [
        "matrices M_0, M_1, ..., M_k over the prime field F_q",
        "the linear pencil M_x = M_0 + sum_i x_i M_i",
        "the coefficient vector x in F_q^k",
    ],
    "intuition": (
        "duality: rank(M_x) <= r is not a condition one can test coordinate by "
        "coordinate; the only handle is the dual object, the (n-r)-dimensional right "
        "kernel of M_x, each of whose vectors turns the rank condition into m equations "
        "that are linear in x -- a solver without that view is left enumerating q^k "
        "vectors and computing a rank for each."
    ),
    "reduction": None,
}

# q, rows (=m), cols (=n), r (target rank), k (number of unknowns)
DIFFICULTY = {
    "demo":   {"q": 5,   "rows": 3,  "cols": 3,  "r": 1, "k": 2},
    "easy":   {"q": 13,  "rows": 6,  "cols": 6,  "r": 2, "k": 8},
    "medium": {"q": 61,  "rows": 8,  "cols": 8,  "r": 3, "k": 20},
    "hard":   {"q": 251, "rows": 10, "cols": 10, "r": 3, "k": 40},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "A matrix has rank at most r exactly when its right kernel has dimension at "
    "least n-r, and every single kernel vector is an equation that is linear in "
    "the unknowns."
)

PLACEBO_HINT = (
    "The matrices are listed one after another in row-major order, so it is worth "
    "keeping the row and column indices straight while assembling the combination."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "The answer is the coefficient vector x = (x_1, ..., x_k) in F_q^k, written "
        "as k integers in the range 0..q-1 in index order. Nothing else is accepted: "
        "no shorter vector, no entry outside the range, no reordering."
    ),
    "bounds": {"k": 40, "q": 251, "entries_are_field_elements": True},
}

NOTES = """
What each part of arXiv:2208.01442 fixed.

* Problem 1 (Section 1) fixes the definition: given matrices over F_q and a target
  rank r, find field coefficients x, not all zero, with rank(sum x_i M_i) <= r.  The
  paper works with the homogeneous form and K matrices; this module ships the affine
  form M_0 + sum_{i=1..k} x_i M_i, which is the homogeneous problem with K = k+1
  matrices under the normalisation x_0 = 1 (the form used by the NIST MinRank
  signature submissions).  Section 1 also records the NP-completeness citation [BFS99].

* Section 4 ("Complexity of solving superdetermined systems") is what told me what
  makes this problem EASY, and it is the single most important page for this family.
  It gives the linearisation criterion for the (SM) system -- solvable as soon as
  m*C(n,r+1) >= K*C(n,r), equivalently m(n-r) >= K(r+1).  Everything the paper improves
  lives inside
  that band -- superdetermined instances, defined in Section 4 as K < r*m.  So the
  paper's own subject matter is the easy side, and a generator that plants inside it
  is broken.  The shipping preset is placed strictly on the other side of that
  inequality and the margin is measured (G5/G6).

* Section 4 also gives the b=2 counts (m*C(n,r+1)*K - C(n,r+2)*C(m+1,2) equations in
  C(n,r)*C(K+1,2) monomials), which pins down the general Bardet et al. degree-b
  counting formula used by sm_counts(); the module reports the first bidegree at which
  linearisation could work and the size of that Macaulay matrix.

* Section 4's remark on the hybrid approach -- exhaustively searching a columns of the
  kernel matrix C at a cost of q^{a*r} field operations -- is implemented as
  attack_kernel_guess, the Goubin-Courtois kernel attack; its per-trial cost is
  measured and extrapolated.

* The modelings in Section 1 (KS, Minors, SM-C, SM-c_T) and Proposition 1 fix what the
  domain-standard attack is; attack_support_minors builds the (SM) Macaulay matrix at
  bidegree b over F_q and eliminates it exactly.  It is calibrated: it SOLVES the demo
  preset at b=1 and the easy preset at b=2, and fails at the shipping preset, which is
  what makes its failure evidence rather than an untested claim.

How each attack was defeated.

* Statistical / outlier attacks cannot work here, and this is provable rather than
  empirical: with M_1..M_k drawn i.i.d. uniform, x drawn uniform and the planted
  rank-r matrix R drawn uniform over rank-exactly-r matrices, the posterior of x given
  the whole instance is exactly uniform over {z : rank(M_z) = r}.  The instance carries
  no information about x beyond its own solution set.  attack_gram_normal_equations is
  the concrete probe: over the reals the least-squares estimate -G^{-1} b would recover
  x, and over F_q it returns a uniformly random vector because <R, M_j> is uniform.

* Greedy / hill-climbing dies because the rank landscape is flat: over F_q almost every
  x gives rank min(m,n), and single-coordinate moves essentially never lower it.

* The domain attack is defeated by the parameter regime, not by anything clever in the
  planting: the b=1 Macaulay matrix is 2100 x 4920 and cannot have rank 4919.
"""


# --------------------------------------------------------------------------
# exact arithmetic over F_q  (integers mod a prime; no floats anywhere)
# --------------------------------------------------------------------------

def _is_prime(m):
    if m < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if m % p == 0:
            return m == p
    d, s = m - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        x = pow(a, d, m)
        if x in (1, m - 1):
            continue
        for _ in range(s - 1):
            x = x * x % m
            if x == m - 1:
                break
        else:
            return False
    return True


_INV_CACHE = {}


def _inv_table(q):
    """Multiplicative inverses in F_q, cached (q is small enough to tabulate)."""
    t = _INV_CACHE.get(q)
    if t is None:
        if q > 1 << 22:
            return None
        t = [0] * q
        for v in range(1, q):
            t[v] = pow(v, q - 2, q)
        _INV_CACHE[q] = t
    return t


def _rank(mat, q):
    """Exact rank over F_q of a list-of-lists matrix.  Gaussian elimination."""
    rows = [row[:] for row in mat]
    nr = len(rows)
    nc = len(rows[0]) if nr else 0
    piv = 0
    for col in range(nc):
        sel = -1
        for i in range(piv, nr):
            if rows[i][col]:
                sel = i
                break
        if sel < 0:
            continue
        rows[piv], rows[sel] = rows[sel], rows[piv]
        tab = _inv_table(q)
        pv = rows[piv][col]
        inv = tab[pv] if tab else pow(pv, q - 2, q)
        pr = rows[piv]
        if inv != 1:
            rows[piv] = pr = [v * inv % q for v in pr]
        for i in range(piv + 1, nr):
            f = rows[i][col]
            if f:
                ri = rows[i]
                rows[i] = [(a - f * b) % q for a, b in zip(ri, pr)]
        piv += 1
        if piv == nr:
            break
    return piv


def _rank_ops(rows, cols, r):
    """Field operations a rank check costs: the elimination reaches at most
    r+1 pivots before it can stop, each costing (rows-1)*cols multiply-adds."""
    return (r + 1) * rows * cols


def _rref(rows_in, ncols, q):
    """Reduced row echelon form; returns (rows, pivot_columns)."""
    rows = [row[:] for row in rows_in]
    piv_cols = []
    piv = 0
    for col in range(ncols):
        sel = -1
        for i in range(piv, len(rows)):
            if rows[i][col]:
                sel = i
                break
        if sel < 0:
            continue
        rows[piv], rows[sel] = rows[sel], rows[piv]
        tab = _inv_table(q)
        pv = rows[piv][col]
        inv = tab[pv] if tab else pow(pv, q - 2, q)
        if inv != 1:
            rows[piv] = [v * inv % q for v in rows[piv]]
        pr = rows[piv]
        for i in range(len(rows)):
            if i != piv and rows[i][col]:
                f = rows[i][col]
                rows[i] = [(a - f * b) % q for a, b in zip(rows[i], pr)]
        piv_cols.append(col)
        piv += 1
        if piv == len(rows):
            break
    return rows[:piv], piv_cols


def _solve_linear(rowsA, rhs, nvars, q):
    """Solve A z = rhs over F_q.  Returns (particular, nullspace_basis) or None."""
    aug = [rowsA[i][:] + [rhs[i]] for i in range(len(rowsA))]
    red, piv_cols = _rref(aug, nvars + 1, q)
    if nvars in piv_cols:                     # 0 = 1  -> inconsistent
        return None
    part = [0] * nvars
    for i, c in enumerate(piv_cols):
        part[c] = red[i][nvars]
    free = [c for c in range(nvars) if c not in piv_cols]
    basis = []
    for f in free:
        v = [0] * nvars
        v[f] = 1
        for i, c in enumerate(piv_cols):
            v[c] = (-red[i][f]) % q
        basis.append(v)
    return part, basis


def _n_rank_le(rows, cols, r, q):
    """Exact number of rows x cols matrices over F_q of rank <= r."""
    tot = 0
    for j in range(r + 1):
        gauss = 1
        for i in range(j):
            gauss = gauss * (q ** rows - q ** i) // (q ** j - q ** i)
        prod = 1
        for i in range(j):
            prod *= (q ** cols - q ** i)
        tot += gauss * prod
    return tot


# --------------------------------------------------------------------------
# instance construction  --  the answer is sampled FIRST, never searched for
# --------------------------------------------------------------------------

def _params(n=None, **params):
    p = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    p.update({k: v for k, v in params.items() if k in ("q", "rows", "cols", "r", "k")})
    if n is not None and not params:
        names = list(DIFFICULTY)
        p = dict(DIFFICULTY[names[min(int(n), len(names) - 1)]])
    return p


def make_instance(n=None, seed=0, **params):
    p = _params(n, **params)
    q, rows, cols, r, k = p["q"], p["rows"], p["cols"], p["r"], p["k"]
    if not _is_prime(q):
        raise ValueError("q must be prime, got %r" % (q,))
    if r >= min(rows, cols):
        raise ValueError("target rank must be below min(m, n)")
    rng = random.Random(("2208.01442", q, rows, cols, r, k, seed).__repr__())

    # 1. the ANSWER first: a uniform coefficient vector.
    x = [rng.randrange(q) for _ in range(k)]

    # 2. k uniform matrices.
    mats = [[[rng.randrange(q) for _ in range(cols)] for _ in range(rows)]
            for _ in range(k)]

    # 3. a uniform matrix of rank EXACTLY r, as A*B with A, B of full rank r.
    while True:
        A = [[rng.randrange(q) for _ in range(r)] for _ in range(rows)]
        if _rank(A, q) == r:
            break
    while True:
        B = [[rng.randrange(q) for _ in range(cols)] for _ in range(r)]
        if _rank(B, q) == r:
            break
    R = [[sum(A[i][t] * B[t][j] for t in range(r)) % q for j in range(cols)]
         for i in range(rows)]

    # 4. close the identity:  M_0 = R - sum x_i M_i,  so M_x = R by construction.
    M0 = [[(R[i][j] - sum(x[t] * mats[t][i][j] for t in range(k))) % q
           for j in range(cols)] for i in range(rows)]

    inst = {
        "family": "minrank_planted",
        "q": q, "rows": rows, "cols": cols, "r": r, "k": k,
        "mats": [M0] + mats,
        "answer": x,
    }
    return inst


def _flat(inst):
    """Row-major flattening of the k+1 matrices, cached on the instance."""
    f = inst.get("_flat")
    if f is None or len(f) != inst["k"] + 1:
        f = [[v for row in M for v in row] for M in inst["mats"]]
        inst["_flat"] = f
    return f


def _combine(inst, x):
    """M(x) = M_0 + sum_i x_i M_i over F_q, exactly."""
    q, rows, cols, k = inst["q"], inst["rows"], inst["cols"], inst["k"]
    flat = _flat(inst)
    acc = flat[0][:]
    for t in range(k):
        xt = x[t]
        if xt:
            acc = [a + xt * b for a, b in zip(acc, flat[t + 1])]
    return [[acc[i * cols + j] % q for j in range(cols)] for i in range(rows)]


# --------------------------------------------------------------------------
# output contract
# --------------------------------------------------------------------------

def _fmt_matrix(M, indent="  "):
    w = max(len(str(v)) for row in M for v in row)
    return "\n".join(indent + " ".join(str(v).rjust(w) for v in row) for row in M)


def render(inst):
    q, rows, cols, r, k = (inst["q"], inst["rows"], inst["cols"],
                           inst["r"], inst["k"])
    L = []
    L.append("MinRank over a finite field.")
    L.append("")
    L.append("Work in the prime field F_q with q = %d; its elements are the integers"
             % q)
    L.append("0, 1, ..., %d and all arithmetic below is modulo %d." % (q - 1, q))
    L.append("")
    L.append("You are given %d matrices M_0, M_1, ..., M_%d, each with m = %d rows"
             % (k + 1, k, rows))
    L.append("and n = %d columns, with entries in F_%d." % (cols, q))
    L.append("")
    L.append("For a vector x = (x_1, ..., x_%d) in F_%d^%d write" % (k, q, k))
    L.append("")
    if k <= 3:
        terms = " + ".join("x_%d*M_%d" % (i, i) for i in range(1, k + 1))
    else:
        terms = "x_1*M_1 + x_2*M_2 + ... + x_%d*M_%d" % (k, k)
    L.append("    M(x) = M_0 + " + terms)
    L.append("")
    L.append("where the sum is entrywise modulo %d." % q)
    L.append("")
    L.append("TASK.  Find one vector x in F_%d^%d such that" % (q, k))
    L.append("")
    L.append("    rank(M(x)) <= %d" % r)
    L.append("")
    L.append("where the rank is the rank over F_%d, i.e. the largest number of" % q)
    L.append("linearly independent rows of M(x) when the entries are treated as")
    L.append("elements of F_%d (NOT the rank over the rationals or the reals)." % q)
    L.append("Equivalently: every (%d x %d) minor of M(x) must vanish modulo %d."
             % (r + 1, r + 1, q))
    L.append("")
    L.append("Such an x exists.  Every entry x_i is an integer with 0 <= x_i <= %d;"
             % (q - 1))
    L.append("entries may repeat and any of them may be 0.  Order matters: x_i is the")
    L.append("coefficient of M_i.  You must give all %d entries." % k)
    L.append("")
    L.append("THE MATRICES.  Each matrix is printed as %d rows of %d entries,"
             % (rows, cols))
    L.append("separated by spaces, in row order.")
    for idx, M in enumerate(inst["mats"]):
        L.append("")
        L.append("M_%d =" % idx)
        L.append(_fmt_matrix(M))
    L.append("")
    L.append("OUTPUT.")
    L.append("Give your final answer inside <answer></answer> tags, as the %d"
             % k)
    L.append("integers x_1, ..., x_%d separated by commas, in this order." % k)
    L.append("Example: <answer>%s</answer>"
             % ", ".join(str((3 * i + 1) % q) for i in range(1, k + 1)))
    L.append("Output nothing else inside the tags.")
    text = "\n".join(L)

    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHINT. " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHINT. " + PLACEBO_HINT
    return text


_TAG = re.compile(r"<answer>(.*?)</answer>", re.S | re.I)
_INT = re.compile(r"-?\d+")


def parse_answer(text):
    if text is None:
        return None
    if isinstance(text, (list, tuple)):
        try:
            return [int(v) for v in text]
        except (TypeError, ValueError):
            return None
    if not isinstance(text, str):
        return None
    blocks = _TAG.findall(text)
    body = blocks[-1] if blocks else text
    body = body.replace("```json", " ").replace("```", " ")
    body = body.replace("[", " ").replace("]", " ")
    nums = _INT.findall(body)
    if not nums:
        return None
    try:
        return [int(v) for v in nums]
    except ValueError:
        return None


def verify(inst, answer):
    """(True, 'ok') or (False, reason).  Never reads inst['answer']."""
    q, rows, cols, r, k = (inst["q"], inst["rows"], inst["cols"],
                           inst["r"], inst["k"])
    if answer is None:
        return False, "no answer parsed"
    if isinstance(answer, tuple):
        answer = list(answer)
    if not isinstance(answer, list):
        return False, "answer is not a list of %d field elements" % k
    if len(answer) != k:
        return False, "answer has %d entries, expected %d" % (len(answer), k)
    for i, v in enumerate(answer):
        if isinstance(v, bool) or not isinstance(v, int):
            return False, "entry %d is not an integer" % (i + 1)
        if not (0 <= v < q):
            return False, "entry %d = %d is outside 0..%d" % (i + 1, v, q - 1)
    Mx = _combine(inst, answer)
    rk = _rank(Mx, q)
    if rk > r:
        return False, "rank(M(x)) = %d, which exceeds the target %d" % (rk, r)
    return True, "ok"


# --------------------------------------------------------------------------
# certificate language, density, canonical form
# --------------------------------------------------------------------------

def random_candidate(inst, rng):
    """Uniform over CERTIFICATE_LANGUAGE.  The statement gives a solver no
    deducible constraint on x beyond 'k entries, each in 0..q-1', so the
    structure-aware space and the naive space coincide here."""
    return [rng.randrange(inst["q"]) for _ in range(inst["k"])]


def search_space(inst):
    return inst["q"] ** inst["k"]


def enumerate_all(inst, budget=4_000_000):
    """Exact number of valid answers, or None when the space is too large."""
    q, k = inst["q"], inst["k"]
    if q ** k > budget:
        return None
    cnt = 0
    for x in itertools.product(range(q), repeat=k):
        if _rank(_combine(inst, list(x)), q) <= inst["r"]:
            cnt += 1
    return cnt


def expected_solution_count(inst):
    """Exact expectation of the number of valid answers for this construction.

    Conditioned on the planted x*, for any z != x* the matrix M(z) equals
    R + sum_i (z_i - x*_i) M_i with M_1..M_k i.i.d. uniform, hence is exactly
    uniform on F_q^{m x n}.  So E[#solutions] = 1 + (q^k - 1) * P(rank <= r).
    """
    q, rows, cols, r, k = (inst["q"], inst["rows"], inst["cols"],
                           inst["r"], inst["k"])
    num = _n_rank_le(rows, cols, r, q)
    den = q ** (rows * cols)
    spurious = (q ** k - 1) * num / den
    return 1.0 + spurious, spurious


def canonical_key(inst):
    """The problem is the AFFINE SPACE L = M_0 + span(M_1..M_k) inside
    F_q^{m x n}: re-choosing the generators (S in GL_k) or translating the
    origin (M_0 -> M_0 + sum t_i M_i) gives literally the same problem with a
    relabelled answer.  The key is the reduced row echelon form of the linear
    part together with the canonical representative of M_0 modulo it, which is
    a COMPLETE invariant for that group.  See the README caveat for the part
    this key does NOT capture (GL_m x GL_n equivalence of matrix codes)."""
    q, rows, cols, r, k = (inst["q"], inst["rows"], inst["cols"],
                           inst["r"], inst["k"])
    flat = [[M[i][j] for i in range(rows) for j in range(cols)]
            for M in inst["mats"][1:]]
    basis, piv_cols = _rref(flat, rows * cols, q)
    m0 = [inst["mats"][0][i][j] for i in range(rows) for j in range(cols)]
    for row, c in zip(basis, piv_cols):       # reduce M_0 modulo span(M_1..M_k)
        f = m0[c]
        if f:
            m0 = [(a - f * b) % q for a, b in zip(m0, row)]
    payload = json.dumps({"q": q, "m": rows, "n": cols, "r": r, "k": k,
                          "basis": basis, "m0": m0}, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def relabel(inst, rng):
    """Apply a random element of the declared symmetry group: a change of
    generators S in GL_k and a translation t in F_q^k.  Returns the relabelled
    instance and the map carrying an answer of the original to an answer of it."""
    q, rows, cols, k = inst["q"], inst["rows"], inst["cols"], inst["k"]
    while True:
        S = [[rng.randrange(q) for _ in range(k)] for _ in range(k)]
        if _rank(S, q) == k:
            break
    t = [rng.randrange(q) for _ in range(k)]
    old = inst["mats"]
    # new M_j = sum_i S[i][j] * M_i     (j = 1..k)
    newmats = []
    for j in range(k):
        newmats.append([[sum(S[i][j] * old[i + 1][a][b] for i in range(k)) % q
                         for b in range(cols)] for a in range(rows)])
    newM0 = [[(old[0][a][b] + sum(t[i] * old[i + 1][a][b] for i in range(k))) % q
              for b in range(cols)] for a in range(rows)]
    out = dict(inst)
    out["mats"] = [newM0] + newmats
    out.pop("_flat", None)
    # M_0' + sum y_j M_j' = M_0 + sum_i (t_i + sum_j S[i][j] y_j) M_i,
    # so y must solve  S y = x - t.
    sol = _solve_linear([[S[i][j] for j in range(k)] for i in range(k)],
                        [(inst["answer"][i] - t[i]) % q for i in range(k)], k, q)
    out["answer"] = sol[0]
    return out


# --------------------------------------------------------------------------
# packed exact linear algebra over F_q, used by the Support-Minors attack
# --------------------------------------------------------------------------

from array import array


def _pack_ctx(ncols, q, nrows):
    W = 32
    while (nrows * (q - 1) ** 2 + q) >= (1 << W):
        W *= 2
    tc = {8: "B", 16: "H", 32: "I", 64: "Q"}[W]
    BLK = max(1, 4096 // (W // 8))
    return {"W": W, "tc": tc, "mask": (1 << W) - 1, "BLK": BLK,
            "nb": (ncols + BLK - 1) // BLK, "ncols": ncols, "q": q}


def _pack_sparse(ctx, d):
    W, BLK = ctx["W"], ctx["BLK"]
    blocks = [0] * ctx["nb"]
    for c, v in d.items():
        if v:
            blocks[c // BLK] += v << (W * (c % BLK))
    return blocks


def _normalize_blocks(ctx, blocks):
    W, tc, BLK, nb, q, ncols = (ctx["W"], ctx["tc"], ctx["BLK"], ctx["nb"],
                                ctx["q"], ctx["ncols"])
    step = W // 8
    out, ent = [], []
    for bi in range(nb):
        width = min(BLK, ncols - bi * BLK)
        a = array(tc)
        a.frombytes(blocks[bi].to_bytes(width * step, "little"))
        vals = [v % q for v in a]
        ent.append(vals)
        out.append(int.from_bytes(array(tc, vals).tobytes(), "little"))
    return out, ent


def _echelon(ctx, sparse_rows, time_budget=None, keep_rows=False):
    """Row echelon form over F_q of a sparse matrix.  Returns a dict with the
    rank, the pivot data, the number of field operations and the wall clock."""
    W, BLK, nb, mask, q, ncols = (ctx["W"], ctx["BLK"], ctx["nb"], ctx["mask"],
                                  ctx["q"], ctx["ncols"])
    t0 = time.time()
    pivots = []
    ops = 0
    timed_out = False
    for sr in sparse_rows:
        row = _pack_sparse(ctx, sr)
        for (pc, prow, fb, _e) in pivots:
            a = ((row[pc // BLK] >> (W * (pc % BLK))) & mask) % q
            ops += 1
            if a:
                f = q - a
                for i in range(fb, nb):
                    if prow[i]:
                        row[i] += f * prow[i]
                ops += (nb - fb) * BLK
        norm, ent = _normalize_blocks(ctx, row)
        lead = -1
        for bi in range(nb):
            for j, v in enumerate(ent[bi]):
                if v:
                    lead = bi * BLK + j
                    break
            if lead >= 0:
                break
        if lead < 0:
            continue
        pv = ent[lead // BLK][lead % BLK]
        tab = _inv_table(q)
        inv = tab[pv] if tab else pow(pv, q - 2, q)
        if inv != 1:
            flat = [v * inv % q for bi in range(nb) for v in ent[bi]]
            norm = _pack_sparse(ctx, {c: v for c, v in enumerate(flat) if v})
            ent = [[flat[bi * BLK + j] for j in range(min(BLK, ncols - bi * BLK))]
                   for bi in range(nb)]
        flat_ent = None
        if keep_rows:
            flat_ent = [v for bi in range(nb) for v in ent[bi]][:ncols]
        pivots.append((lead, norm, lead // BLK, flat_ent))
        if time_budget is not None and time.time() - t0 > time_budget:
            timed_out = True
            break
    return {"rank": len(pivots), "pivots": pivots, "ops": ops,
            "seconds": time.time() - t0, "timed_out": timed_out}


# --------------------------------------------------------------------------
# the domain-standard attack: the paper's Support-Minors modeling (SM)
# --------------------------------------------------------------------------

def sm_counts(rows, cols, r, k, b):
    """Independent equations and monomials of the (SM) system at bidegree (b, r),
    with K = k+1 linear variables.  The b=1 and b=2 cases are displayed in
    Section 4 of arXiv:2208.01442; the general alternating sum is the
    Bardet et al. (Asiacrypt 2020) formula the section builds on."""
    K = k + 1
    neq = 0
    for i in range(1, b + 1):
        if r + i > cols:
            break
        neq += ((-1) ** (i + 1) * comb(cols, r + i) * comb(rows + i - 1, i)
                * comb(K + b - i - 1, b - i))
    nmon = comb(cols, r) * comb(K + b - 1, b)
    return neq, nmon


def sm_first_solvable_b(rows, cols, r, k, bmax=24):
    """Smallest bidegree at which linearisation of (SM) can determine x, with
    the size of that Macaulay matrix.  None if there is none up to bmax."""
    for b in range(1, bmax + 1):
        neq, nmon = sm_counts(rows, cols, r, k, b)
        if neq > 0 and neq >= nmon - 1:
            return b, neq, nmon
    return None


def _mons_upto(k, d):
    out = []
    for deg in range(d + 1):
        out.extend(itertools.combinations_with_replacement(range(1, k + 1), deg))
    return out


def _sm_system(inst, b):
    """Build the (SM) Macaulay matrix at bidegree b as sparse rows."""
    q, rows, cols, r, k = (inst["q"], inst["rows"], inst["cols"],
                           inst["r"], inst["k"])
    mats = inst["mats"]
    supports = list(itertools.combinations(range(cols), r))
    sup_idx = {S: i for i, S in enumerate(supports)}
    mons = _mons_upto(k, b)
    mon_idx = {m: i for i, m in enumerate(mons)}
    nsup = len(supports)
    ncols_mat = len(mons) * nsup

    def col_of(mon, S):
        return mon_idx[mon] * nsup + sup_idx[S]

    betas = _mons_upto(k, b - 1)
    srows = []
    for l in range(rows):
        for T in itertools.combinations(range(cols), r + 1):
            subsets = [(j, t, tuple(u for u in T if u != t))
                       for j, t in enumerate(T)]
            for beta in betas:
                d = {}
                for j, t, S in subsets:
                    sgn = -1 if (j & 1) else 1
                    v = sgn * mats[0][l][t]
                    if v % q:
                        c = col_of(beta, S)
                        d[c] = (d.get(c, 0) + v) % q
                    for i in range(1, k + 1):
                        e = mats[i][l][t]
                        if not e:
                            continue
                        mon = tuple(sorted(beta + (i,)))
                        c = col_of(mon, S)
                        d[c] = (d.get(c, 0) + sgn * e) % q
                d = {c: v for c, v in d.items() if v}
                if d:
                    srows.append(d)
    return srows, ncols_mat, mons, supports, mon_idx, sup_idx


def attack_support_minors(inst, b=1, run_elimination=True, time_budget=None):
    """The paper's Support-Minors modeling solved by linearisation.

    Returns a dict; `solved` is True only when a vector that VERIFIES was
    recovered.  When the equation count cannot reach n_mon - 1 the linearised
    system is rank deficient by construction and the attack reports that -- this
    is exactly the criterion of Section 4 ("solvable whenever
    m*C(n,r+1) >= K*C(n,r)"), and it is what an attacker reads off before
    building anything.
    """
    q, rows, cols, r, k = (inst["q"], inst["rows"], inst["cols"],
                           inst["r"], inst["k"])
    neq, nmon = sm_counts(rows, cols, r, k, b)
    out = {"b": b, "n_eq_formula": neq, "n_mon_formula": nmon,
           "solved": False, "x": None, "rank": None, "seconds": 0.0,
           "ops": 0, "eliminated": False}
    if neq < nmon - 1:
        out["reason"] = ("underdetermined: at b=%d the (SM) Macaulay matrix has at "
                         "most %d independent equations against %d monomials, so its "
                         "rank cannot reach the %d needed to determine x "
                         "(deficit %d)" % (b, neq, nmon, nmon - 1, nmon - 1 - neq))
        if not run_elimination:
            return out
    t0 = time.time()
    srows, ncols_mat, mons, supports, mon_idx, sup_idx = _sm_system(inst, b)
    ctx = _pack_ctx(ncols_mat, q, len(srows))
    res = _echelon(ctx, srows, time_budget=time_budget,
                   keep_rows=(neq >= nmon - 1))
    out["eliminated"] = True
    out["rank"] = res["rank"]
    out["ops"] = res["ops"]
    out["seconds"] = time.time() - t0
    out["timed_out"] = res["timed_out"]
    out["matrix_shape"] = [len(srows), ncols_mat]
    if res["timed_out"] or res["rank"] < ncols_mat - 1:
        out.setdefault("reason",
                       "measured rank %d < %d, kernel dimension %d > 1: "
                       "linearisation does not determine x"
                       % (res["rank"], ncols_mat - 1, ncols_mat - res["rank"]))
        return out
    # one-dimensional kernel: back-substitute
    piv_cols = [p[0] for p in res["pivots"]]
    pivset = set(piv_cols)
    free = [c for c in range(ncols_mat) if c not in pivset]
    if len(free) != 1:
        out["reason"] = "kernel dimension %d != 1" % len(free)
        return out
    v = [0] * ncols_mat
    v[free[0]] = 1
    for (pc, _n, _fb, ent) in reversed(res["pivots"]):
        s = 0
        for c in range(pc + 1, ncols_mat):
            if ent[c] and v[c]:
                s += ent[c] * v[c]
        v[pc] = (-s) % q
    nsup = len(supports)
    x = None
    for si in range(nsup):
        den = v[mon_idx[()] * nsup + si]
        if den:
            tab = _inv_table(q)
            inv = tab[den] if tab else pow(den, q - 2, q)
            x = [v[mon_idx[(i,)] * nsup + si] * inv % q for i in range(1, k + 1)]
            break
    if x is None:
        out["reason"] = "kernel vector has c_S = 0 for every support S"
        return out
    ok, why = verify(inst, x)
    out["solved"] = ok
    out["x"] = x if ok else None
    out["reason"] = "ok" if ok else "recovered vector fails: " + why
    return out


# --------------------------------------------------------------------------
# the other domain attack: Goubin-Courtois kernel guessing (= the hybrid of
# Section 4, "exhaustive search on some columns of C, at the cost of q^{ar}")
# --------------------------------------------------------------------------

def kernel_attack_success_prob(q, cols, r, a):
    """Exact probability that a uniformly random a-dimensional subspace of
    F_q^n lies inside a fixed (n-r)-dimensional subspace."""
    num, den = 1, 1
    for i in range(a):
        num *= (q ** (cols - r) - q ** i)
        den *= (q ** cols - q ** i)
    return num / den


def attack_kernel_guess(inst, rng, trials=200, time_budget=None):
    """Guess an a-dimensional subspace of the right kernel of M(x); each guess
    turns the rank condition into m*a linear equations in x."""
    q, rows, cols, r, k = (inst["q"], inst["rows"], inst["cols"],
                           inst["r"], inst["k"])
    a = max(1, -(-k // rows))
    a = min(a, cols - r)
    t0 = time.time()
    done = 0
    solved = None
    for _ in range(trials):
        V = [[rng.randrange(q) for _ in range(a)] for _ in range(cols)]
        A, rhs = [], []
        for j in range(a):
            for l in range(rows):
                A.append([sum(inst["mats"][i + 1][l][c] * V[c][j]
                              for c in range(cols)) % q for i in range(k)])
                rhs.append((-sum(inst["mats"][0][l][c] * V[c][j]
                                 for c in range(cols))) % q)
        sol = _solve_linear(A, rhs, k, q)
        done += 1
        if sol is not None:
            part, basis = sol
            cands = [part]
            for bvec in basis[:2]:
                cands.append([(p + bv) % q for p, bv in zip(part, bvec)])
            for cand in cands:
                if verify(inst, cand)[0]:
                    solved = cand
                    break
        if solved is not None:
            break
        if time_budget is not None and time.time() - t0 > time_budget:
            break
    secs = time.time() - t0
    p = kernel_attack_success_prob(q, cols, r, a)
    return {"solved": solved is not None, "x": solved, "trials": done,
            "seconds": secs, "a": a, "success_prob": p,
            "expected_trials": (1.0 / p) if p > 0 else float("inf"),
            "sec_per_trial": secs / max(done, 1),
            "projected_seconds": (secs / max(done, 1)) * (1.0 / p) if p > 0 else float("inf")}


# --------------------------------------------------------------------------
# generic probes
# --------------------------------------------------------------------------

def attack_bruteforce(inst, budget=200_000, time_budget=None, rng=None):
    """Exhaustive search over F_q^k in odometer order (or random order)."""
    q, k = inst["q"], inst["k"]
    t0 = time.time()
    total = q ** k
    tried = 0
    solved = None
    if rng is None:
        it = itertools.product(range(q), repeat=k)
        for tup in it:
            tried += 1
            if _rank(_combine(inst, list(tup)), q) <= inst["r"]:
                solved = list(tup)
                break
            if tried >= budget:
                break
            if time_budget is not None and (tried & 1023) == 0 and time.time() - t0 > time_budget:
                break
    else:
        while tried < budget:
            cand = [rng.randrange(q) for _ in range(k)]
            tried += 1
            if _rank(_combine(inst, cand), q) <= inst["r"]:
                solved = cand
                break
            if time_budget is not None and (tried & 1023) == 0 and time.time() - t0 > time_budget:
                break
    secs = time.time() - t0
    return {"solved": solved is not None, "x": solved, "tried": tried,
            "space": total, "seconds": secs,
            "sec_per_candidate": secs / max(tried, 1),
            "ops_per_candidate": inst["k"] * inst["rows"] * inst["cols"]
                                 + _rank_ops(inst["rows"], inst["cols"], inst["r"]),
            "projected_seconds": (secs / max(tried, 1)) * total}


def attack_gram_normal_equations(inst):
    """The planting-signature probe.  M_0 = R - sum x_i M_i, so with
    b_j = <M_0, M_j> and G_ij = <M_i, M_j> we have G x = <R, M> - b.  Over the
    reals dropping the unknown <R, M_j> term is the least-squares estimate of x
    and it works; over F_q every <R, M_j> is uniform, so it does not."""
    q, rows, cols, k = inst["q"], inst["rows"], inst["cols"], inst["k"]
    mats = inst["mats"]

    def ip(A, B):
        return sum(A[i][j] * B[i][j] for i in range(rows) for j in range(cols)) % q

    G = [[ip(mats[i + 1], mats[j + 1]) for j in range(k)] for i in range(k)]
    b = [(-ip(mats[0], mats[j + 1])) % q for j in range(k)]
    sol = _solve_linear(G, b, k, q)
    if sol is None:
        return {"solved": False, "x": None, "reason": "Gram system inconsistent"}
    cand = sol[0]
    ok, why = verify(inst, cand)
    return {"solved": ok, "x": cand if ok else None, "reason": "ok" if ok else why}


def attack_greedy_hillclimb(inst, rng, restarts=8, sweeps=6):
    """Coordinate descent on rank(M(x))."""
    q, k, r = inst["q"], inst["k"], inst["r"]
    best = None
    evals = 0
    for _ in range(restarts):
        x = [rng.randrange(q) for _ in range(k)]
        cur = _rank(_combine(inst, x), q)
        evals += 1
        for _ in range(sweeps):
            improved = False
            for i in range(k):
                old = x[i]
                bv, bs = old, cur
                for v in range(q):
                    if v == old:
                        continue
                    x[i] = v
                    s = _rank(_combine(inst, x), q)
                    evals += 1
                    if s < bs:
                        bs, bv = s, v
                x[i] = bv
                if bs < cur:
                    cur, improved = bs, True
            if not improved:
                break
        if best is None or cur < best[0]:
            best = (cur, list(x))
        if cur <= r:
            return {"solved": True, "x": list(x), "best_rank": cur, "evals": evals}
    return {"solved": False, "x": None, "best_rank": best[0], "evals": evals}


def attack_random_restart(inst, rng, samples=20000, time_budget=None):
    """Uniform sampling with a rank-based acceptance heuristic."""
    q, k, r = inst["q"], inst["k"], inst["r"]
    t0 = time.time()
    best = min(inst["rows"], inst["cols"]) + 1
    n = 0
    for _ in range(samples):
        x = [rng.randrange(q) for _ in range(k)]
        s = _rank(_combine(inst, x), q)
        n += 1
        if s < best:
            best = s
        if s <= r:
            return {"solved": True, "x": x, "samples": n, "best_rank": s,
                    "seconds": time.time() - t0}
        if time_budget is not None and (n & 255) == 0 and time.time() - t0 > time_budget:
            break
    return {"solved": False, "x": None, "samples": n, "best_rank": best,
            "seconds": time.time() - t0}


def attack_low_rank_column_span(inst, rng, trials=400):
    """Sparse-support probe: the plant would be cheap to find if it happened to be
    supported on one or two coordinates, which is what an in-context solver would
    try first.  Tries every 1-sparse x (all k*q of them) and then `trials` random
    2-sparse ones."""
    q, k = inst["q"], inst["k"]
    for i in range(k):
        for v in range(q):
            x = [0] * k
            x[i] = v
            if verify(inst, x)[0]:
                return {"solved": True, "x": x}
    for _ in range(trials):
        i, j = rng.randrange(k), rng.randrange(k)
        x = [0] * k
        x[i] = rng.randrange(q)
        x[j] = rng.randrange(q)
        if verify(inst, x)[0]:
            return {"solved": True, "x": x}
    return {"solved": False, "x": None,
            "tried": k * q + trials}


# --------------------------------------------------------------------------
# a cost model for the published attacks, used by escalate() and G7
# --------------------------------------------------------------------------

def _sm_solve_log2(rows, cols, r, K, bmax=24):
    """log2 of the field operations sparse (Wiedemann) linear algebra needs on
    the (SM) Macaulay matrix at the first bidegree where it can determine x."""
    if K < 1 or cols <= r:
        return None
    for b in range(1, bmax + 1):
        neq = 0
        for i in range(1, b + 1):
            if r + i > cols:
                break
            neq += ((-1) ** (i + 1) * comb(cols, r + i) * comb(rows + i - 1, i)
                    * comb(K + b - i - 1, b - i))
        nmon = comb(cols, r) * comb(K + b - 1, b)
        if neq <= 0:
            continue
        if neq >= nmon - 1:
            nnz = neq * (r + 1) * K
            return b, log2(2.0 * nmon * nnz), neq, nmon
    return None


def best_known_attack(q, rows, cols, r, k):
    """Cheapest published route at these parameters, in log2(field operations).
    Covers: plain Support-Minors linearisation; the Section 4 hybrid that guesses
    a columns of the kernel matrix C at cost q^{a r} (a = n-r fully linearises,
    which is the Goubin-Courtois kernel attack); the hybrid that guesses a of the
    x_i at cost q^a; and exhaustive search."""
    K = k + 1
    cands = []
    s = _sm_solve_log2(rows, cols, r, K)
    if s:
        cands.append(("support_minors_b%d" % s[0], s[1], s[2], s[3]))
    for a in range(1, cols - r + 1):
        Kp = K - rows * a
        guess = -log2(kernel_attack_success_prob(q, cols, r, a))
        if Kp < 2:
            cands.append(("kernel_attack_a%d" % a, guess + 3 * log2(max(K, 2)), 0, 0))
            break
        s = _sm_solve_log2(rows, cols - a, r, Kp)
        if s:
            cands.append(("hybrid_kernel_a%d_b%d" % (a, s[0]), guess + s[1], s[2], s[3]))
    for a in range(1, k):
        if a * log2(q) > 400:
            break
        s = _sm_solve_log2(rows, cols, r, K - a)
        if s:
            cands.append(("hybrid_guessx_a%d_b%d" % (a, s[0]),
                          a * log2(q) + s[1], s[2], s[3]))
    cands.append(("exhaustive_search", k * log2(q) + log2(_rank_ops(rows, cols, r)), 0, 0))
    cands.sort(key=lambda t: t[1])
    name, cost, neq, nmon = cands[0]
    return {"name": name, "log2_ops": cost, "n_eq": neq, "n_mon": nmon,
            "all": [(n, round(c, 2)) for n, c, _, _ in cands[:6]]}


_ESC_PRIMES = [5, 13, 31, 61, 127, 251, 509, 1021, 2039, 4093, 8191, 16381,
               32749, 65521, 131071, 262139, 524287, 1048573]

_MAX_RENDER_ENTRIES = 40_000
_UNIQUENESS_MARGIN = 5


def escalate(params):
    """Strictly harder parameters at a FIXED answer length.

    k -- the number of field elements in the answer -- never moves.  What moves
    is the field size q, the matrix dimensions m and n, and the target rank r,
    at least two of them at once.  Raising m and n alone would be a mistake and
    the search below rejects it: it makes the (SM) system MORE overdetermined and
    walks the instance back into the easy band of Section 4."""
    p = dict(params)
    q, rows, cols, r, k = p["q"], p["rows"], p["cols"], p["r"], p["k"]
    cur = best_known_attack(q, rows, cols, r, k)["log2_ops"]
    qi = _ESC_PRIMES.index(q) if q in _ESC_PRIMES else 0
    best = None
    for qj in range(qi, min(qi + 3, len(_ESC_PRIMES))):
        q2 = _ESC_PRIMES[qj]
        for rows2 in range(rows, rows + 6):
            for cols2 in range(cols, cols + 6):
                for r2 in range(r, r + 4):
                    moved = ((q2 > q) + (rows2 > rows) + (cols2 > cols) + (r2 > r))
                    if moved < 2:
                        continue
                    if r2 >= min(rows2, cols2):
                        continue
                    if (rows2 - r2) * (cols2 - r2) - k < _UNIQUENESS_MARGIN:
                        continue
                    if (k + 1) * rows2 * cols2 > _MAX_RENDER_ENTRIES:
                        continue
                    if k * (len(str(q2 - 1)) + 2) > 2000:
                        continue
                    c = best_known_attack(q2, rows2, cols2, r2, k)["log2_ops"]
                    if c < cur + 2.0:
                        continue
                    key = (-round(min(c, cur + 25.0), 3),
                           (k + 1) * rows2 * cols2, -q2)
                    if best is None or key < best[0]:
                        best = (key, {"q": q2, "rows": rows2, "cols": cols2,
                                      "r": r2, "k": k})
    if best is None:
        return "cap_bound"
    return best[1]


def _rank_le(mat, q, r):
    """Fast exact test rank(mat) <= r: stop as soon as r+1 pivots appear."""
    rows = [row[:] for row in mat]
    nr, nc = len(rows), len(rows[0])
    piv = 0
    for col in range(nc):
        sel = -1
        for i in range(piv, nr):
            if rows[i][col]:
                sel = i
                break
        if sel < 0:
            continue
        rows[piv], rows[sel] = rows[sel], rows[piv]
        tab = _inv_table(q)
        pv = rows[piv][col]
        inv = tab[pv] if tab else pow(pv, q - 2, q)
        pr = rows[piv]
        if inv != 1:
            rows[piv] = pr = [v * inv % q for v in pr]
        for i in range(piv + 1, nr):
            f = rows[i][col]
            if f:
                rows[i] = [(a - f * b) % q for a, b in zip(rows[i], pr)]
        piv += 1
        if piv > r:
            return False
        if piv == nr:
            break
    return True


def _is_solution(inst, x):
    return _rank_le(_combine(inst, x), inst["q"], inst["r"])


# --------------------------------------------------------------------------
# selftest: gates G1..G9
# --------------------------------------------------------------------------

CALIBRATION_PRESETS = {
    # small enough that enumerate_all() terminates, so the analytic estimator
    # of the solution count can be checked against an exact count.
    "cal_many":   {"q": 5, "rows": 4, "cols": 4, "r": 2, "k": 6},   # k > (m-r)(n-r)
    "cal_unique": {"q": 5, "rows": 5, "cols": 5, "r": 2, "k": 6},   # k < (m-r)(n-r)
}


def _answer_size(inst):
    ans = inst["answer"]
    txt = ", ".join(str(v) for v in ans)
    tokens = max(len(ans) + len(ans) - 1, -(-len(txt) // 3))
    return {"chars": len(txt), "elements": len(ans), "tokens": tokens,
            "json_chars": len(json.dumps(ans))}


def _corruptions(inst, rng):
    ans = inst["answer"]
    q, k = inst["q"], inst["k"]
    out = []
    out.append(("drop one entry", ans[:-1]))
    out.append(("duplicate one entry", ans + [ans[0]]))
    a = ans[:]
    i, j = 0, k - 1
    if a[i] != a[j]:
        a[i], a[j] = a[j], a[i]
        out.append(("swap two entries", a))
    b = ans[:]
    b[rng.randrange(k)] = (b[0] + 1 + rng.randrange(q - 1)) % q
    out.append(("perturb one entry", b))
    c = ans[:]
    c[0] = q
    out.append(("entry out of range (=q)", c))
    d = ans[:]
    d[min(1, k - 1)] = -1
    out.append(("negative entry", d))
    out.append(("empty", []))
    e = ans[:]
    e[min(2, k - 1)] = "3"
    out.append(("non-integer entry", e))
    out.append(("None", None))
    out.append(("all zeros", [0] * k))
    return out


def selftest(verbose=True, heavy=True):
    t_start = time.time()
    rep = {}
    log = (lambda *a: print(*a)) if verbose else (lambda *a: None)
    ship = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    q, rows, cols, r, k = (ship["q"], ship["rows"], ship["cols"],
                           ship["r"], ship["k"])
    n_seeds = 8 if heavy else 3

    # ---------------- G1 ----------------
    per, ok_tot, tot = {}, 0, 0
    n_g1 = 20
    det_ok = True
    for name, p in DIFFICULTY.items():
        good = 0
        for s in range(n_g1):
            inst = make_instance(seed=1000 + s, **p)
            ok, _ = verify(inst, inst["answer"])
            rt = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            good += bool(ok and rt)
        per[name] = "%d/%d" % (good, n_g1)
        ok_tot += good
        tot += n_g1
        i1 = make_instance(seed=4242, **p)
        i2 = make_instance(seed=4242, **p)
        if (i1["mats"] != i2["mats"] or i1["answer"] != i2["answer"]
                or canonical_key(i1) != canonical_key(i2)):
            det_ok = False
    rep["G1_planted_verifies"] = {"ok": ok_tot, "total": tot, "per_preset": per,
                                  "seeds_per_preset": n_g1,
                                  "deterministic": det_ok,
                                  "pass": ok_tot == tot and det_ok}
    log("G1", rep["G1_planted_verifies"])

    # ---------------- G2 ----------------
    rng = random.Random(11)
    reasons, accepted = set(), 0
    for p in (DIFFICULTY["demo"], ship):
        for s in range(4):
            inst = make_instance(seed=2000 + s, **p)
            for _label, bad in _corruptions(inst, rng):
                ok, why = verify(inst, bad)
                if ok:
                    accepted += 1
                else:
                    reasons.add(why)
            ok, why = verify(inst, parse_answer("no answer here"))
            if ok:
                accepted += 1
            else:
                reasons.add(why)
    rep["G2_rejects_corruption"] = {"accepted_corruptions": accepted,
                                    "distinct_reasons": sorted(reasons),
                                    "pass": accepted == 0 and len(reasons) >= 5}
    log("G2", rep["G2_rejects_corruption"]["pass"], accepted,
        len(rep["G2_rejects_corruption"]["distinct_reasons"]), "reasons")

    # ---------------- G3 ----------------
    inst = make_instance(seed=7, **ship)
    a = inst["answer"]
    prose = ("Let me set this up.  The rank condition gives a bilinear system, and "
             "after some work I get\n\n```\nx = (%s)\n```\n\nSo my final answer is\n"
             "<answer>%s</answer>\nHope that helps!"
             % (", ".join(map(str, a)), ", ".join(map(str, a))))
    rt1 = parse_answer(prose) == a
    jsonish = "Answer: <answer>%s</answer>" % json.dumps(a)
    rt2 = parse_answer(jsonish) == a
    spaced = "<answer>\n  %s\n</answer>" % "  ".join(map(str, a))
    rt3 = parse_answer(spaced) == a
    junk = parse_answer("I could not solve this one.") is None
    junk2 = parse_answer(None) is None
    ver = verify(inst, parse_answer(prose))[0]
    # the statement must not contain the answer, in any of the three hint modes
    leak = False
    for mode in (None, "structural", "placebo"):
        if mode is None:
            os.environ.pop("GV_HINT_MODE", None)
        else:
            os.environ["GV_HINT_MODE"] = mode
        for s in range(6):
            i3 = make_instance(seed=900 + s, **ship)
            txt = render(i3)
            joined = ", ".join(map(str, i3["answer"]))
            if joined in txt or " ".join(map(str, i3["answer"])) in txt:
                leak = True
            if mode == "structural" and STRUCTURAL_HINT not in txt:
                leak = True
            if mode is None and ("HINT." in txt):
                leak = True
    os.environ.pop("GV_HINT_MODE", None)
    rep["G3_round_trip"] = {"prose_round_trip": rt1, "json_form_accepted": rt2,
                            "whitespace_form_accepted": rt3,
                            "garbage_returns_none": bool(junk and junk2),
                            "verifies_after_parse": ver,
                            "render_leaks_answer": leak,
                            "hint_modes_behave": not leak,
                            "pass": all([rt1, rt2, rt3, junk, junk2, ver, not leak])}
    log("G3", rep["G3_round_trip"]["pass"])

    # ---------------- G4 ----------------
    trials = 200_000
    rng = random.Random(4242)
    inst = make_instance(seed=17, **ship)
    hits = 0
    agree = True
    t0 = time.time()
    for i in range(trials):
        cand = random_candidate(inst, rng)
        good = _is_solution(inst, cand)
        if i < 2000 and good != verify(inst, cand)[0]:
            agree = False
        if good:
            hits += 1
    space = search_space(inst)
    rep["G4_guess_resistance"] = {
        "trials": trials, "hits": hits,
        "fast_check_agrees_with_verify": agree,
        "structure_aware_space": str(space),
        "structure_aware_space_log2": round(log2(space), 2),
        "analytic_p_guess": "~%.3e" % (expected_solution_count(inst)[0] / space),
        "analytic_p_guess_log2": round(log2(expected_solution_count(inst)[0]) - log2(space), 2),
        "note": ("the statement leaves a solver no deducible constraint on x beyond "
                 "'k entries, each in 0..q-1', so the structure-aware space and the "
                 "naive space coincide"),
        "seconds": round(time.time() - t0, 1),
        "pass": hits == 0 and agree and (expected_solution_count(inst)[0] / space) < 1e-6}
    log("G4", rep["G4_guess_resistance"]["hits"], "/", trials,
        "%.1fs" % rep["G4_guess_resistance"]["seconds"])

    # ---------------- G5 ----------------
    g5 = {}
    # (i) exact enumeration where feasible, as a CALIBRATION of the estimator
    calib = {}
    for cname, cp in CALIBRATION_PRESETS.items():
        counts, preds = [], []
        for s in range(20):
            ci = make_instance(seed=5000 + s, **cp)
            counts.append(enumerate_all(ci, budget=200_000))
            preds.append(expected_solution_count(ci)[0])
        calib[cname] = {"params": cp, "seeds": len(counts),
                        "mean_exact_count": sum(counts) / len(counts),
                        "predicted_count": preds[0],
                        "min_exact": min(counts), "max_exact": max(counts)}
    demo_counts = [enumerate_all(make_instance(seed=6000 + s, **DIFFICULTY["demo"]))
                   for s in range(20)]
    g5["exact_solution_count_demo_mean"] = sum(demo_counts) / len(demo_counts)
    g5["exact_solution_count_demo_predicted"] = expected_solution_count(
        make_instance(seed=6000, **DIFFICULTY["demo"]))[0]
    g5["estimator_calibration"] = calib
    # (ii) density at the SHIPPING preset
    exp_tot, exp_sp = expected_solution_count(inst)
    g5["expected_solution_count_shipping"] = exp_tot
    g5["expected_spurious_solutions_shipping"] = exp_sp
    g5["expected_spurious_solutions_log2_shipping"] = round(log2(exp_sp), 2)
    g5["sampled_density_shipping"] = "%d/%d" % (hits, trials)
    g5["sampled_density_shipping_hits"] = hits
    g5["valid_answer_count_shipping"] = exp_tot
    g5["uniqueness_condition"] = ("k = %d < (m-r)(n-r) = %d"
                                  % (k, (rows - r) * (cols - r)))
    # (iii) baseline cost of the strongest attack, measured at shipping
    sm = attack_support_minors(inst, b=1, run_elimination=True)
    g5["baseline_attack"] = "Support-Minors linearisation (arXiv:2208.01442, Sec. 4)"
    g5["baseline_wall_clock_sec"] = round(sm["seconds"], 2)
    g5["baseline_cost_ops"] = sm["ops"]
    g5["support_minors_b1_shape"] = sm["matrix_shape"]
    g5["support_minors_b1_measured_rank"] = sm["rank"]
    g5["support_minors_b1_rank_needed"] = sm["matrix_shape"][1] - 1
    g5["support_minors_b1_deficit"] = sm["matrix_shape"][1] - 1 - sm["rank"]
    fb = sm_first_solvable_b(rows, cols, r, k)
    g5["support_minors_first_solvable_b"] = fb[0]
    g5["support_minors_first_solvable_shape"] = [fb[1], fb[2]]
    g5["support_minors_counts_by_b"] = {
        str(b): list(sm_counts(rows, cols, r, k, b)) for b in range(1, fb[0] + 1)}
    bk = best_known_attack(q, rows, cols, r, k)
    g5["best_known_attack"] = bk["name"]
    g5["best_known_attack_log2_ops"] = round(bk["log2_ops"], 2)
    g5["best_known_attack_ranking"] = bk["all"]
    rngk = random.Random(99)
    kr = attack_kernel_guess(inst, rngk, trials=120, time_budget=25)
    g5["kernel_attack_a"] = kr["a"]
    g5["kernel_attack_success_prob"] = kr["success_prob"]
    g5["kernel_attack_expected_trials"] = kr["expected_trials"]
    g5["kernel_attack_sec_per_trial"] = kr["sec_per_trial"]
    g5["kernel_attack_projected_seconds"] = kr["projected_seconds"]
    g5["kernel_attack_projected_years"] = kr["projected_seconds"] / 31_557_600.0
    g5["pass"] = (exp_sp < 1e-3 and hits == 0 and sm["solved"] is False
                  and bk["log2_ops"] > 55)
    rep["G5_density_and_baseline"] = g5
    log("G5 exp_spurious=2^%.1f  SM b=1 rank %d/%d  best known 2^%.1f"
        % (g5["expected_spurious_solutions_log2_shipping"],
           sm["rank"], sm["matrix_shape"][1] - 1, bk["log2_ops"]))

    # ---------------- G6 ----------------
    attacks = {}

    def _run(name, fn, n=n_seeds):
        succ, secs = 0, 0.0
        agg = {}
        for s in range(n):
            i2 = make_instance(seed=30000 + s, **ship)
            t0 = time.time()
            res = fn(i2, random.Random(777 + s))
            secs += time.time() - t0
            if res.get("solved"):
                succ += 1
            for kk in ("rank", "best_rank", "trials", "tried", "samples", "evals"):
                v = res.get(kk)
                if isinstance(v, (int, float)):
                    agg.setdefault(kk, []).append(v)
        attacks[name] = {"successes": succ, "attempts": n,
                         "seconds": round(secs, 3)}
        for kk, vals in agg.items():
            attacks[name]["total_" + kk] = sum(vals)
            attacks[name]["worst_" + kk] = min(vals)
        log("   attack %-34s %d/%d  %.1fs" % (name, succ, n, secs))

    sm_state = {"n": 0, "ranks": [], "secs": 0.0, "ops": 0}
    sm_full = 3 if heavy else 1

    def _sm_panel(i, rg):
        full = sm_state["n"] < sm_full
        sm_state["n"] += 1
        res = attack_support_minors(i, b=1, run_elimination=full)
        if full and res.get("rank") is not None:
            sm_state["ranks"].append(res["rank"])
            sm_state["secs"] += res["seconds"]
            sm_state["ops"] += res["ops"]
        return res

    _run("support_minors_linearisation_b1", _sm_panel)
    attacks["support_minors_linearisation_b1"].update({
        "full_eliminations_run": len(sm_state["ranks"]),
        "measured_ranks": sm_state["ranks"],
        "rank_needed": comb(cols, r) * (k + 1) - 1,
        "elimination_seconds": round(sm_state["secs"], 1),
        "elimination_field_ops": sm_state["ops"],
        "note": ("the remaining seeds are decided by the Section 4 criterion itself: "
                 "with only %d equations against %d monomials the linearised system "
                 "cannot have the rank that determines x, which is what an attacker "
                 "reads off before building the matrix"
                 % (rows * comb(cols, r + 1), comb(cols, r) * (k + 1)))})
    _run("kernel_attack_goubin_courtois",
         lambda i, rg: attack_kernel_guess(i, rg, trials=150, time_budget=15))
    _run("gram_normal_equations_outlier",
         lambda i, rg: attack_gram_normal_equations(i))
    _run("greedy_coordinate_descent",
         lambda i, rg: attack_greedy_hillclimb(i, rg, restarts=2, sweeps=2))
    _run("random_restart_20000",
         lambda i, rg: attack_random_restart(i, rg, samples=20000, time_budget=20))
    _run("exhaustive_search_budget_20000",
         lambda i, rg: attack_bruteforce(i, budget=20000, time_budget=20, rng=rg))
    _run("sparse_support_probe",
         lambda i, rg: attack_low_rank_column_span(i, rg, trials=2000))

    # calibration: the same two domain attacks SOLVE the easier rungs
    cal = {}
    dsm = [attack_support_minors(make_instance(seed=s, **DIFFICULTY["demo"]), b=1)["solved"]
           for s in range(6)]
    esm = [attack_support_minors(make_instance(seed=s, **DIFFICULTY["easy"]),
                                 b=2)["solved"] for s in range(4)]
    ker = [attack_kernel_guess(make_instance(seed=s, **DIFFICULTY["easy"]),
                               random.Random(s), trials=400_000,
                               time_budget=60)["solved"] for s in range(3)]
    cal["support_minors_b1_on_demo"] = "%d/%d solved" % (sum(dsm), len(dsm))
    cal["support_minors_b2_on_easy"] = "%d/%d solved" % (sum(esm), len(esm))
    cal["kernel_attack_on_easy"] = "%d/%d solved" % (sum(ker), len(ker))
    cal["note"] = ("the two domain attacks are calibrated: the SAME code solves the "
                   "lower rungs of the ladder, so their failure at the shipping "
                   "preset is a measurement and not an untested claim")
    rep["G6_adversary_panel"] = {
        "pass": all(v["successes"] == 0 for v in attacks.values()),
        "attacks": attacks, "calibration": cal}
    log("G6", rep["G6_adversary_panel"]["pass"], cal)

    # ---------------- G7 ----------------
    ladder = [(nm, round(best_known_attack(p["q"], p["rows"], p["cols"], p["r"],
                                           p["k"])["log2_ops"], 2))
              for nm, p in DIFFICULTY.items()]
    monotone = all(ladder[i][1] < ladder[i + 1][1] for i in range(len(ladder) - 1))
    esc = escalate(ship)
    g7 = {"ladder_best_attack_log2": ladder, "ladder_monotone": monotone}
    if isinstance(esc, dict):
        ei = make_instance(seed=1, **esc)
        ok, _ = verify(ei, ei["answer"])
        elog = round(best_known_attack(esc["q"], esc["rows"], esc["cols"],
                                       esc["r"], esc["k"])["log2_ops"], 2)
        g7.update({
            "escalated_params": esc, "escalated_verifies": ok,
            "escalated_best_attack_log2": elog,
            "harder": elog > ladder[-1][1],
            "answer_elements_shipping": k,
            "answer_elements_escalated": esc["k"],
            "answer_length_fixed": esc["k"] == k,
            "escalation_axes": ["q", "m (rows)", "n (cols)", "r (target rank)"],
            "escalation_chain": [],
        })
        p2 = dict(ship)
        for _ in range(4):
            nx = escalate(p2)
            if not isinstance(nx, dict):
                g7["escalation_chain"].append(nx)
                break
            c = round(best_known_attack(nx["q"], nx["rows"], nx["cols"], nx["r"],
                                        nx["k"])["log2_ops"], 2)
            g7["escalation_chain"].append(
                {"params": nx, "best_attack_log2": c, "answer_elements": nx["k"]})
            p2 = nx
        g7["pass"] = bool(monotone and ok and g7["harder"] and g7["answer_length_fixed"])
    else:
        g7.update({"escalated_params": esc, "pass": False})
    rep["G7_scales"] = g7
    log("G7", g7["pass"], ladder, "->", g7.get("escalated_best_attack_log2"))

    # ---------------- G8 ----------------
    inv_ok = inv_tot = 0
    real_ok = real_tot = 0
    keys = []
    for s in range(20):
        i0 = make_instance(seed=8000 + s, **DIFFICULTY["medium"])
        k0 = canonical_key(i0)
        keys.append(k0)
        rg = random.Random(400 + s)
        cur = i0
        for step in range(4):                 # single maps and their composites
            cur = relabel(cur, rg)
            inv_tot += 1
            if canonical_key(cur) == k0:
                inv_ok += 1
            real_tot += 1
            if verify(cur, cur["answer"])[0]:
                real_ok += 1
    rep["G8_canonical_key"] = {
        "invariances_tested": [
            "change of generators M_j -> sum_i S[i][j] M_i for S in GL_k(F_q)",
            "translation of the origin M_0 -> M_0 + sum_i t_i M_i",
            "the two composed, four deep, in random order",
        ],
        "invariance_ok": inv_ok, "invariance_total": inv_tot,
        "transformation_is_real_ok": real_ok, "transformation_checks": real_tot,
        "distinct_keys": len(set(keys)), "distinct_seeds": len(keys),
        "not_captured": ("GL_m x GL_n equivalence M_i -> A M_i B, which is the "
                         "Matrix Code Equivalence problem and is believed hard "
                         "(it is the security assumption of the NIST candidate "
                         "MEDS); see the README caveats"),
        "pass": (inv_ok == inv_tot and real_ok == real_tot
                 and len(set(keys)) == len(keys))}
    log("G8", rep["G8_canonical_key"]["pass"], inv_ok, "/", inv_tot,
        "distinct", len(set(keys)))

    # ---------------- G9 ----------------
    inst = make_instance(seed=17, **ship)
    sz = _answer_size(inst)
    verif_ops = k * rows * cols + _rank_ops(rows, cols, r)
    within = sz["chars"] <= 2000 and sz["elements"] <= 256
    rep["G9_no_tool_suitability"] = {
        "arms": {"bare": None, "hinted": None, "placebo": None},
        "arms_note": ("three-arm oracle diagnostic not run: no OPENROUTER_API_KEY in "
                      "this environment.  STEP 4 is run by the caller."),
        "hinted_minus_placebo": None,
        "hinted_verdict": None,
        "answer_chars": sz["chars"], "answer_json_chars": sz["json_chars"],
        "answer_tokens": sz["tokens"], "answer_elements": sz["elements"],
        "render_chars": len(render(inst)),
        "intended_route_operations": None,
        "intended_route_note": (
            "Track A: there is no compact solving route, so the >=1000-operation cap "
            "on the intended route has no Track A referent.  The recorded number is "
            "the cost of CHECKING a proposed answer -- %d field operations: %d "
            "multiply-adds to form M(x) plus at most %d for the elimination that "
            "decides rank(M(x)) <= %d.  The cost of FINDING one is the "
            "best_known_attack figure in G5." % (verif_ops, k * rows * cols,
                                                 _rank_ops(rows, cols, r), r)),
        "verification_operations": verif_ops,
        "within_answer_caps": within,
        "pass": within}
    log("G9", rep["G9_no_tool_suitability"]["pass"], sz)

    gates = [v for kk, v in rep.items() if kk.startswith("G")]
    rep["all_gates_pass"] = all(bool(g["pass"]) for g in gates)
    rep["all_passed"] = rep["all_gates_pass"]
    rep["module"] = "gen_2208_01442"
    rep["track"] = TRACK
    rep["shipping_difficulty"] = SHIPPING_DIFFICULTY
    rep["shipping_params"] = ship
    rep["problem_profile"] = PROBLEM_PROFILE
    rep["certificate_language"] = CERTIFICATE_LANGUAGE
    rep["json_native_answer"] = True
    rep["elapsed_sec"] = round(time.time() - t_start, 1)
    return rep


def _json_safe(o):
    """Strict-JSON-safe: no Infinity/NaN, no huge ints left as ints."""
    if isinstance(o, dict):
        return {k: _json_safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_json_safe(v) for v in o]
    if isinstance(o, float):
        if o != o or o in (float("inf"), float("-inf")):
            return str(o)
        return o
    if isinstance(o, int) and not isinstance(o, bool) and abs(o) > 2 ** 53:
        return str(o)
    return o


if __name__ == "__main__":
    out = selftest(verbose=True, heavy=("--fast" not in sys.argv))
    with open("selftest_report.json", "w") as fh:
        json.dump(_json_safe(out), fh, indent=1, sort_keys=True, default=str,
                  allow_nan=False)
    print("\nall_gates_pass =", out["all_gates_pass"], " elapsed", out["elapsed_sec"], "s")
