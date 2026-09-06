"""REJECTED FAMILY -- retained as evidence, do not ship.  See REJECTED.md.

Fails H on both tracks: the compact route (constraint propagation on the forced row
multisets) IS an in-context attack and solves 40/40 shipping instances in a median of
35 backtracking nodes; a zero-search padding heuristic solves 23/40.  G and V hold.

Least common standard multiples of standard bideterminants in A_gen^bd.

Source: arXiv:2510.11212, Grochow & Natarajan, "Groebner Bases Native to
Term-ordered Commutative Algebras, with Application to the Hodge Algebra of
Minors".  Section 7 (bideterminants):
  - Defn 7.6  (defn:order-bitab)  the pseudo-ASL term order on standard bitableaux
  - Thm  7.12 (thm:leading-bd)    LT(f*g) = [sort(R_f+R_g) | sort(C_f+C_g)]
  - Lem  7.22 (lem:lt-div-bd)     g/f = [R_g minus R_f | C_g minus C_f]  (closed form)
  - Defn 5.10 (defn:lcms)         LCM_sm = division-minimal common multiples
  - Thm  7.19 / Alg 7.1           the LCM algorithm, whose two subroutines the
                                  authors describe (conclusion.tex:25) as "naive
                                  exhaustive searches over combinatorial spaces
                                  that are easily seen to have exponential size"

Everything here is exact integer / multiset combinatorics.  No floats.
"""
import os, sys, json, re
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    from gvlib import rationals            # noqa: F401  (not needed: pure integers)
except ImportError:
    rationals = None

import random as _random

TRACK = "B"

# ===================================================================== primitives
def shape(bt):
    return tuple(len(S) for S, T in bt)

def _sorted_cols(bt):
    return tuple(sorted(bt, key=lambda c: (-len(c[0]), c[0], c[1])))

def is_normal(bt):
    return all(tuple(sorted(set(S))) == tuple(S) and tuple(sorted(set(T))) == tuple(T)
               for S, T in bt)

def is_standard(bt):
    """Both tableaux semi-standard: columns strictly increasing, rows non-decreasing,
    column heights non-increasing (Section 7.1)."""
    if not bt: return True
    if not is_normal(bt): return False
    h = shape(bt)
    if any(h[i] < h[i + 1] for i in range(len(h) - 1)): return False
    for j in range(len(bt) - 1):
        (S1, T1), (S2, T2) = bt[j], bt[j + 1]
        for i in range(len(S2)):
            if S1[i] > S2[i] or T1[i] > T2[i]: return False
    return True

def in_box(bt, m, n):
    return all(all(1 <= s <= m for s in S) and all(1 <= t <= n for t in T) for S, T in bt)

def rows_of(bt, which):
    cols = _sorted_cols(bt)
    h = [len(S) for S, T in cols]
    nrows = h[0] if h else 0
    out = [[] for _ in range(nrows)]
    for S, T in cols:
        seq = S if which == 0 else T
        for i, v in enumerate(seq): out[i].append(v)
    return [tuple(sorted(r)) for r in out]

def merge_sort_bitab(bt):
    """Theorem 7.12(II): the leading standard bitableau of a product."""
    cols = _sorted_cols(bt)
    lam = [len(S) for S, T in cols]
    nrows = lam[0] if lam else 0
    R = [[] for _ in range(nrows)]; C = [[] for _ in range(nrows)]
    for S, T in cols:
        for i, (s, t) in enumerate(zip(S, T)):
            R[i].append(s); C[i].append(t)
    for i in range(nrows): R[i].sort(); C[i].sort()
    out = []
    for j in range(len(cols)):
        out.append((tuple(R[i][j] for i in range(lam[j])),
                    tuple(C[i][j] for i in range(lam[j]))))
    return _sorted_cols(tuple(out))

def _msub(a, b):
    la = list(a)
    for x in b:
        if x in la: la.remove(x)
        else: return None
    return tuple(sorted(la))

def _shape_sub(la, lb):
    l = list(la)
    for x in lb:
        if x in l: l.remove(x)
        else: return None
    return tuple(sorted(l, reverse=True))

def _from_rows(lam, Rr, Cr):
    lam = tuple(sorted(lam, reverse=True)); p = len(lam)
    nrows = lam[0] if p else 0
    conj = [sum(1 for x in lam if x >= i + 1) for i in range(nrows)]
    for i in range(nrows):
        if i >= len(Rr) or i >= len(Cr): return None
        if len(Rr[i]) != conj[i] or len(Cr[i]) != conj[i]: return None
    for i in range(nrows, max(len(Rr), len(Cr))):
        if (i < len(Rr) and Rr[i]) or (i < len(Cr) and Cr[i]): return None
    return tuple((tuple(Rr[i][j] for i in range(lam[j])),
                  tuple(Cr[i][j] for i in range(lam[j]))) for j in range(p))

def quotient(f, g):
    """Lemma 7.22: the unique standard h with LT(f*h)=g, else None."""
    lam = _shape_sub(shape(g), shape(f))
    if lam is None: return None
    Rf, Cf = rows_of(f, 0), rows_of(f, 1)
    Rg, Cg = rows_of(g, 0), rows_of(g, 1)
    Rh, Ch = [], []
    for i in range(len(Rg)):
        a = _msub(Rg[i], Rf[i] if i < len(Rf) else ())
        b = _msub(Cg[i], Cf[i] if i < len(Cf) else ())
        if a is None or b is None: return None
        Rh.append(a); Ch.append(b)
    h = _from_rows(lam, Rh, Ch)
    if h is None or not is_standard(h): return None
    return h

def lt_divides(f, g):
    """f |_gen g, checked by RECOMPUTING the leading term (Thm 7.12) -- one division."""
    if not f: return True
    h = quotient(f, g)
    if h is None: return False
    return merge_sort_bitab(tuple(f) + tuple(h)) == _sorted_cols(g)

# ------------------------------------------------------------- leastness (Defn 5.10)
def _one_column_smaller_divisors(L):
    """Every standard L' with L' |_gen L and one fewer column.
    Divisibility is graded by column count -- if L'|L then #cols(L') < #cols(L), and
    L = LT(L' * h) factors one column of h at a time -- so checking this layer is
    necessary and sufficient for division-minimality within the divisors of L."""
    RL, CL = rows_of(L, 0), rows_of(L, 1)
    out = set()
    for h in set(shape(L)):
        lam = _shape_sub(shape(L), (h,))
        def rec(i, Rr, Cr):
            if i == h:
                Rr2 = Rr + [RL[k] for k in range(h, len(RL))]
                Cr2 = Cr + [CL[k] for k in range(h, len(CL))]
                Lp = _from_rows(lam, Rr2, Cr2)
                if Lp is not None and is_standard(Lp) and lt_divides(Lp, L):
                    out.add(_sorted_cols(Lp))
                return
            for rv in sorted(set(RL[i])):
                rr = _msub(RL[i], (rv,))
                for cv in sorted(set(CL[i])):
                    rec(i + 1, Rr + [rr], Cr + [_msub(CL[i], (cv,))])
        rec(0, [], [])
    return out

def is_lcm(f, g, L):
    """L is a LEAST common standard multiple of f and g relative to A_gen^bd."""
    if not is_standard(L): return False, "not a standard bitableau"
    if not lt_divides(f, L): return False, "f does not lt-divide the answer"
    if not lt_divides(g, L): return False, "g does not lt-divide the answer"
    for Lp in _one_column_smaller_divisors(L):
        if lt_divides(f, Lp) and lt_divides(g, Lp):
            return False, "not least: a proper standard divisor is also a common multiple"
    return True, "ok"

# ===================================================================== generation
def _random_standard_bitab(rng, lam, m, n, tries=4000):
    """Uniform-ish random standard bitableau of shape lam over [m]x[n] (rejection)."""
    for _ in range(tries):
        colsS, colsT, ok = [], [], True
        prevS = prevT = None
        for h in lam:
            for _ in range(400):
                S = tuple(sorted(rng.sample(range(1, m + 1), h)))
                T = tuple(sorted(rng.sample(range(1, n + 1), h)))
                if prevS is None or (all(prevS[i] <= S[i] for i in range(h)) and
                                     all(prevT[i] <= T[i] for i in range(h))):
                    break
            else:
                ok = False; break
            colsS.append(S); colsT.append(T); prevS, prevT = S, T
        if not ok: continue
        bt = tuple(zip(colsS, colsT))
        if is_standard(bt): return bt
    return None

DIFFICULTY = {
    "demo":   dict(m=4, n=4, heights=(2, 1),          overlap=0),
    "easy":   dict(m=5, n=5, heights=(3, 2, 1),       overlap=1),
    "medium": dict(m=6, n=6, heights=(4, 3, 2, 1),    overlap=2),
    "hard":   dict(m=7, n=7, heights=(5, 4, 3, 2, 1), overlap=2),
}
SHIPPING_DIFFICULTY = "hard"

def make_instance(n_size=0, seed=0, m=6, n=6, heights=(4, 3, 2, 1), overlap=2, **kw):
    """Plant the LCM L FIRST (Theorem 7.12 + Lemma 7.22 guarantee leastness because
    the column heights of L are pairwise distinct), then cut f and g out of it."""
    rng = _random.Random((seed, m, n, heights, overlap).__hash__() & 0xFFFFFFFF)
    lam = tuple(sorted(heights, reverse=True))
    assert len(set(lam)) == len(lam), "planting needs pairwise-distinct column heights"
    for _ in range(500):
        L = _random_standard_bitab(rng, lam, m, n)
        if L is None: continue
        p = len(L)
        if p < 2: continue
        idx = list(range(p)); rng.shuffle(idx)
        cut = rng.randint(1, p - 1)
        A, Bs = set(idx[:cut]), set(idx[cut:])
        for _ in range(overlap):                      # crowding: shared columns
            if len(A) < p - 1 and Bs - A:
                A.add(rng.choice(sorted(Bs - A)))
            elif len(Bs) < p - 1 and A - Bs:
                Bs.add(rng.choice(sorted(A - Bs)))
        if len(A) >= p or len(Bs) >= p: continue
        if A | Bs != set(idx): continue
        f = _sorted_cols(tuple(L[i] for i in sorted(A)))
        g = _sorted_cols(tuple(L[i] for i in sorted(Bs)))
        if not (is_standard(f) and is_standard(g)): continue
        ok, _r = is_lcm(f, g, L)
        if not ok: continue
        return {"m": m, "n": n, "f": [[list(S), list(T)] for S, T in f],
                "g": [[list(S), list(T)] for S, T in g],
                "answer": [[list(S), list(T)] for S, T in L],
                "params": {"m": m, "n": n, "heights": list(lam), "overlap": overlap},
                "seed": seed}
    raise RuntimeError("generation failed")

def _bt(obj):
    try:
        return _sorted_cols(tuple((tuple(int(x) for x in c[0]), tuple(int(x) for x in c[1]))
                                  for c in obj))
    except Exception:
        return None

def verify(inst, answer):
    L = _bt(answer)
    if L is None: return False, "malformed answer"
    if any(len(S) != len(T) or not S for S, T in L): return False, "a minor is empty or has |S| != |T|"
    if not in_box(L, inst["m"], inst["n"]): return False, "an index is outside the matrix"
    f, g = _bt(inst["f"]), _bt(inst["g"])
    return is_lcm(f, g, L)

# ===================================================================== presentation
def _fmt(bt):
    return " * ".join("(" + ",".join(map(str, S)) + " | " + ",".join(map(str, T)) + ")"
                      for S, T in bt)

STRUCTURAL_HINT = ("Row i of each tableau of a common multiple must contain the "
                   "multiplicity-wise maximum of row i of f and row i of g.")
PLACEBO_HINT = ("This problem rewards keeping the row and the column tableau "
                "carefully separated while you work.")

def render(inst):
    m, n = inst["m"], inst["n"]
    f, g = _bt(inst["f"]), _bt(inst["g"])
    s = f"""Let X be a generic {m} x {n} matrix of distinct indeterminates x_(i,j).

A MINOR is written (r_1,...,r_k | c_1,...,c_k): the determinant of the submatrix on
rows r_1<...<r_k and columns c_1<...<c_k.  A BIDETERMINANT is a product of minors,
written as a BITABLEAU: list its minors as columns, in non-increasing order of size.
Writing the row indices of the j-th minor down column j gives the row tableau R, and
the column indices give the column tableau C.

A bitableau is STANDARD if, in BOTH R and C, every column is strictly increasing
downwards and every row is non-decreasing left to right (so the minor sizes are
non-increasing left to right).

PRODUCT RULE.  For standard bitableaux u and v, the product of their bideterminants
has a unique largest standard bitableau in its straightening, namely
    LT(u*v) = merge the columns of u and v, then SORT EACH ROW of the merged R into
              ascending order, and independently SORT EACH ROW of the merged C.
DIVISIBILITY.  u divides w when there is a standard bitableau h with LT(u*h) = w.
COMMON MULTIPLE.  w is a common multiple of f and g when f divides w and g divides w.
LEAST.  A common multiple w is LEAST when no common multiple w' other than w itself
divides w.

INSTANCE.
  f = {_fmt(f)}
  g = {_fmt(g)}

TASK.  Give one least common standard multiple of f and g.  All indices must lie in
1..{m} (rows) and 1..{n} (columns).  There may be more than one correct answer; any
one of them is accepted.

Write the answer as its list of minors, one per pair of parentheses, separated by "*",
each as (rows|cols) with indices comma-separated and increasing, minors listed in
non-increasing order of size.

Give your final answer inside <answer></answer> tags.
Example: <answer>(1,2,3|1,2,3) * (2,4|1,3) * (3|2)</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural": s += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":  s += "\n\nHint: " + PLACEBO_HINT
    return s

def parse_answer(text):
    if not isinstance(text, str): return None
    mm = re.findall(r"<answer>(.*?)</answer>", text, re.S)
    body = mm[-1] if mm else text
    cols = []
    for a, b in re.findall(r"\(\s*([0-9,\s]+?)\s*\|\s*([0-9,\s]+?)\s*\)", body):
        try:
            S = [int(x) for x in re.split(r"[,\s]+", a.strip()) if x]
            T = [int(x) for x in re.split(r"[,\s]+", b.strip()) if x]
        except ValueError:
            return None
        if not S or not T: return None
        cols.append([S, T])
    return cols or None

# ===================================================================== gate helpers
CERTIFICATE_LANGUAGE = {
    "description": "A standard bitableau over [m]x[n]: an ordered list of minors "
                   "(S_j|T_j) with |S_j|=|T_j| non-increasing in j, each S_j a strictly "
                   "increasing subset of [m] and T_j of [n], such that both the row and "
                   "the column tableau are semi-standard.",
    "bounds": {"m": None, "n": None, "max_columns": None, "max_height": None},
}

def search_space(inst):
    from math import comb
    m, n = inst["m"], inst["n"]
    p = len(_bt(inst["answer"])); hmax = min(m, n)
    return sum(comb(m, h) * comb(n, h) for h in range(1, hmax + 1)) ** p

def random_candidate(inst, rng):
    """Structure-aware: the shape is forced (Lemma 7.22 -- it must contain the multiset
    union of shape(f) and shape(g)), so sample only the entries."""
    m, n = inst["m"], inst["n"]
    lam = sorted(shape(_bt(inst["answer"])), reverse=True)
    for _ in range(200):
        bt = tuple((tuple(sorted(rng.sample(range(1, m + 1), h))),
                    tuple(sorted(rng.sample(range(1, n + 1), h)))) for h in lam)
        if is_standard(bt): return [[list(S), list(T)] for S, T in bt]
    return [[list(S), list(T)] for S, T in _bt(inst["f"])]

def canonical_key(inst):
    f, g = _bt(inst["f"]), _bt(inst["g"])
    a, b = sorted([f, g])
    return json.dumps([inst["m"], inst["n"], a, b], sort_keys=True)

def escalate(params):
    p = dict(params)
    h = tuple(p.get("heights", (4, 3, 2, 1)))
    p["m"] = p.get("m", 6) + 1
    p["n"] = p.get("n", 6) + 1
    p["overlap"] = min(p.get("overlap", 2) + 1, len(h) - 2) if len(h) > 3 else p.get("overlap", 1)
    p["heights"] = tuple(range(len(h) + 1, 0, -1))
    if p["m"] > 12: return "cap_bound"
    return p

NOTES = """\
Definition fixed by:  Section 7.1 of arXiv:2510.11212 (bitableaux, standard bitableaux,
  the partial order on minors Defn 7.3) and Defn 5.10 (defn:lcms) for "least common
  standard multiple"; the product rule is Theorem 7.12(II) (thm:leading-bd) and the
  closed-form quotient is Lemma 7.22 (lem:lt-div-bd).
What told me it is easy:  Theorem 7.12(II) and Lemma 7.22 make BOTH divisibility and
  the quotient closed-form multiset operations, so the only real freedom in a least
  common multiple is the padding of each row beyond the multiplicity-wise union
  re_i = R(R_f,i) u R(R_g,i).  Row i's required content and length are both forced, R
  and C decouple, and the completion is a semi-standard-tableau completion that
  constraint propagation finishes in a few dozen nodes.  Measured: 40/40 solved,
  median 34 backtracking nodes at the shipping preset.
Planting:  the column heights of the planted L are pairwise DISTINCT, so the multiset
  union of shape(f) and shape(g) equals shape(L); every common multiple therefore has
  at least |shape(L)| columns, so no proper divisor of L is a common multiple and L is
  least by construction (Lemma 7.22).  No search anywhere in make_instance.
Attack defence attempted:  raising m,n, raising the number of shared columns
  (crowding), and lengthening the shape.  None of it worked -- see REJECTED.md.
Paper bug found:  Theorem 7.19's completeness argument claims every least common
  standard multiple has exactly P = max_i max(rd_i, cd_i) columns.  False: f = (2|1),
  g = (2,3|1,2) has P = 1 and no common multiple with 1 column at all.  Consequence for
  this project: "least" has no cheap certificate, so verify() has to enumerate the
  one-column-smaller divisors of the answer.
"""

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_discrete",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": ["standard bitableaux over [m]x[n]",
                       "bideterminants (products of minors) of a generic matrix"],
    "verification_operations": ["multiset subtraction on tableau rows",
                                "multiset subtraction on column heights",
                                "recomputation of LT(f*h) by merge-and-sort (Thm 7.12)",
                                "semi-standardness comparisons",
                                "enumeration of the one-column-smaller divisors"],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Row i of every common multiple must contain the multiplicity-wise union of "
        "row i of f and row i of g, and the shape must contain the multiset union of "
        "the two shapes; a solver who does not see this must search standard bitableaux."),
    "hardness_basis": (
        "REJECTED.  Track B was the only candidate and it fails: the compact route IS "
        "an in-context attack.  Constraint propagation over the forced row multisets "
        "solves 40/40 shipping instances in a median of 34 backtracking nodes "
        "(~5e2 exact operations, 0.14 s), and a zero-search padding heuristic solves "
        "6/8.  The paper's own Algorithm 7.1 enumerates ~7e6 standard bitableaux at the "
        "same preset, but that gap is not testable because the short side is trivially "
        "reachable by hand."),
    "max_answer_tokens": 40,
}
NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": " + PROBLEM_PROFILE["intuition_description"],
    "reduction": None,
}
