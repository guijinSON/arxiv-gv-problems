"""Pentagon-Equation table completion, arXiv:2004.04028 (Colazzo-Jespers-Kubat).

A set-theoretic solution of the Pentagon Equation (PE) on a finite set S is a map
s: S x S -> S x S, written s(x,y) = (x.y, theta_x(y)), with

    s_23 s_13 s_12 = s_12 s_23        on S^3,

equivalently (paper, Section 1) the three identities

    (P1)  (x.y).z            = x.(y.z)
    (P2)  theta_x(y) . theta_{x.y}(z) = theta_x(y.z)
    (P3)  theta_{theta_x(y)} theta_{x.y} = theta_y .

This module plants a genuine PE solution, blanks `holes` cells of the two
displayed tables and asks the solver to restore them.  Verification is exact and
purely combinatorial: rebuild s and compare s_23 s_13 s_12 against s_12 s_23 on
all |S|^3 triples.

VERDICT: this family is REJECTED on H.  See REJECTED.md.  Pure unit propagation
over (P1)-(P3) -- no backtracking at all -- restores every blanked cell on every
preset measured, including 70% of both tables blanked at |S| = 24.  The module is
retained as evidence, per the contract.
"""

from __future__ import annotations

import json
import os
import random
import re
import sys
import time
from typing import Any

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
try:  # pragma: no cover - the family needs only integer arithmetic
    from gvlib import exact_matrices, rationals
except ImportError:
    exact_matrices = rationals = None


TRACK = "B"

STRUCTURAL_HINT = (
    "Every theta-row is a relabelled copy of the map y -> y*x^{-1} of a group "
    "torsor carried on the idempotents of S."
)
PLACEBO_HINT = (
    "Every entry of the two displayed tables is an element of S, so keep the row "
    "and column indices carefully apart while reading them."
)

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "set-theoretic map s: S x S -> S x S",
        "semigroup multiplication table of S",
        "the family of maps theta_x: S -> S",
    ],
    "verification_operations": [
        "table lookup",
        "composition of s_12, s_13, s_23 on S^3",
        "exact tuple equality over all |S|^3 triples",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Identity (P3) turns each unknown cell into an index that selects a whole "
        "theta-row, so one known column pins the cell; a solver without that "
        "observation searches |S|^holes completions."
    ),
    "hardness_basis": (
        "Track B FAILS as measured.  The reference algorithm is unit propagation "
        "over (P1)-(P3): at the largest preset (|S| = 40, 100 holes) it restores "
        "100/100 cells with 0 backtracks in 0.47 s; the compact route (recognise "
        "the group torsor, then one lookup per hole) costs ~3 operations per hole. "
        "Mechanical 2|S| = 80 operations per hole against compact 3 per hole is a "
        "factor of 27, not a factor of 10^5, so there is no gap to test."
    ),
    "max_answer_tokens": 160,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": " + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

# params: m,q,r build the left-zero factor E (|E| = m*q + r); g is the group factor
# |G|; holes is the number of blanked cells.  |S| = (m*q + r) * g.
DIFFICULTY = {
    "demo":   {"n": 6,  "m": 3, "q": 1, "r": 0, "g": 2, "holes": 5},
    "easy":   {"n": 12, "m": 4, "q": 1, "r": 0, "g": 3, "holes": 24},
    "medium": {"n": 24, "m": 3, "q": 2, "r": 0, "g": 4, "holes": 60},
    "hard":   {"n": 40, "m": 4, "q": 2, "r": 0, "g": 5, "holes": 100},
}
SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of `holes` integers in 0..|S|-1, one per blanked cell, in the "
        "order the blanked cells are listed in the statement (multiplication table "
        "first, then the theta table, each in row-major order)."
    ),
    "bounds": {"entries": "holes", "min_value": 0, "max_value": "|S| - 1"},
}

NOTES = """
Definition fixed by Section 1 of arXiv:2004.04028: s(x,y) = (x.y, theta_x(y)) is a
PE solution iff (P1) associativity, (P2), (P3) hold.  Products of solutions are
solutions (Section 1, after Definition 1.4), which is the planting route used here.

The plant is  (E, s_E) x (G, s_G)  where
  * E is a LEFT ZERO semigroup (i.j = i), on which (P1),(P2) hold automatically and
    the PE reduces to the single identity  theta_{theta_i(j)} theta_i = theta_j.
    Writing i o j = theta_i(j) that identity reads (i o j) o (i o k) = j o k.
    We plant the torsor solution  i o j = phi(j) . phi(i)^{-1}  of a group T
    (optionally composed with an idempotent retraction, r > 0), which is the
    generic bijective solution: an easy argument shows every bijective solution on
    a left zero semigroup has this form, matching the paper's Lemma 2.5.
  * G is a cyclic group carrying the UNIQUE bijective PE solution s_G(a,b)=(ab,b)
    of Proposition 3.1 (Kashaev-Sergeev).

What makes it easy - the two results that killed the family:
  * Theorem 5.6 / Corollary 5.8 classify all INVOLUTIVE solutions up to isomorphism
    by the three cardinalities |X|, |A|, |G|; on a set of size 2^n(2m+1) there are
    exactly binom(n+2,2) of them.  Any involutive branch of this family is a lookup.
  * Identity (P3) is an "element constraint": the unknown value of theta_x(y) is
    itself the ROW INDEX of the equation it appears in, so one known column of
    theta already reduces its domain to a singleton.  Measured: unit propagation
    alone, zero backtracks, restores every hole at every preset.
"""


# ----------------------------------------------------------------------------
# planting
# ----------------------------------------------------------------------------
def _left_zero_solution(rng: random.Random, m: int, q: int, r: int) -> list[list[int]]:
    """theta table of a PE solution on a left zero semigroup of size m*q + r.

    Base: E0 = T x Z with |T| = m (cyclic), |Z| = q, and
        theta_{(a,z)}(b,w) = (c_z * a^{-1} * b, w).
    Then r extra points are attached through an idempotent retraction pi onto E0,
    which keeps (i o j) o (i o k) = j o k (a retraction of a solution is one).
    """
    base = m * q
    c = [rng.randrange(m) for _ in range(q)]
    idx = lambda a, z: a * q + z
    tab0 = [[0] * base for _ in range(base)]
    for a in range(m):
        for z in range(q):
            for b in range(m):
                for w in range(q):
                    tab0[idx(a, z)][idx(b, w)] = idx((c[z] - a + b) % m, w)
    n = base + r
    if r:
        pi = list(range(base)) + [rng.randrange(base) for _ in range(r)]
        return [[tab0[pi[x]][pi[y]] for y in range(n)] for x in range(n)]
    return tab0


def _plant(rng: random.Random, m: int, q: int, r: int, g: int):
    """Product of the left-zero solution above with the unique group solution on Z_g."""
    e = m * q + r
    n = e * g
    theta_e = _left_zero_solution(rng, m, q, r)
    idx = lambda i, a: i * g + a
    mul = [[0] * n for _ in range(n)]
    th = [[0] * n for _ in range(n)]
    for i in range(e):
        for a in range(g):
            for j in range(e):
                for b in range(g):
                    mul[idx(i, a)][idx(j, b)] = idx(i, (a + b) % g)
                    th[idx(i, a)][idx(j, b)] = idx(theta_e[i][j], b)
    perm = list(range(n))
    rng.shuffle(perm)
    m2 = [[0] * n for _ in range(n)]
    t2 = [[0] * n for _ in range(n)]
    for x in range(n):
        for y in range(n):
            m2[perm[x]][perm[y]] = perm[mul[x][y]]
            t2[perm[x]][perm[y]] = perm[th[x][y]]
    return m2, t2


# ----------------------------------------------------------------------------
# exact pentagon check  (the V side)
# ----------------------------------------------------------------------------
def _pentagon(mul, th, n) -> tuple[bool, str]:
    """s_23 s_13 s_12 == s_12 s_23 on all n^3 triples, done by composing the maps."""
    s = lambda x, y: (mul[x][y], th[x][y])

    def s12(t):
        a, b = s(t[0], t[1]); return (a, b, t[2])

    def s23(t):
        a, b = s(t[1], t[2]); return (t[0], a, b)

    def s13(t):
        a, b = s(t[0], t[2]); return (a, t[1], b)

    for x in range(n):
        for y in range(n):
            for z in range(n):
                t = (x, y, z)
                if s23(s13(s12(t))) != s12(s23(t)):
                    return False, f"pentagon fails at ({x},{y},{z})"
    return True, "ok"


# ----------------------------------------------------------------------------
# the generator
# ----------------------------------------------------------------------------
def make_instance(n: int, seed: int = 0, **params: Any) -> dict[str, Any]:
    rng = random.Random((seed << 12) ^ (n * 1_000_003) ^ 0x2004_04028)
    m = int(params.get("m", 4)); q = int(params.get("q", 1))
    r = int(params.get("r", 0)); g = int(params.get("g", 3))
    holes = int(params.get("holes", 24))
    mul, th = _plant(rng, m, q, r, g)
    size = (m * q + r) * g
    if n and n != size:
        raise ValueError(f"n={n} inconsistent with (m,q,r,g) giving |S|={size}")
    ok, why = _pentagon(mul, th, size)
    if not ok:  # pragma: no cover - construction is theorem-backed
        raise AssertionError("planted object is not a PE solution: " + why)

    cells = [("M", x, y) for x in range(size) for y in range(size)]
    cells += [("T", x, y) for x in range(size) for y in range(size)]
    rng.shuffle(cells)
    blanks = cells[:holes]
    blanks.sort(key=lambda c: (0 if c[0] == "M" else 1, c[1], c[2]))

    shown_m = [row[:] for row in mul]
    shown_t = [row[:] for row in th]
    answer = []
    for w, x, y in blanks:
        tab = shown_m if w == "M" else shown_t
        answer.append(tab[x][y])
        tab[x][y] = None

    return {
        "size": size, "m": m, "q": q, "r": r, "g": g, "holes": holes,
        "mul": shown_m, "theta": shown_t,
        "blanks": [[w, x, y] for (w, x, y) in blanks],
        "answer": answer,
    }


# ----------------------------------------------------------------------------
# statement
# ----------------------------------------------------------------------------
def _fmt(tab):
    return "\n".join(
        " ".join("?" if v is None else str(v) for v in row) for row in tab
    )


def render(inst: dict[str, Any]) -> str:
    n = inst["size"]
    blist = ", ".join(
        f"{w}[{x}][{y}]" for (w, x, y) in (tuple(b) for b in inst["blanks"])
    )
    txt = f"""Let S = {{0, 1, ..., {n-1}}}.

A map s : S x S -> S x S is written s(x, y) = ( M[x][y] , T[x][y] ), where M and T
are {n} x {n} tables of elements of S.  Write x.y for M[x][y] and theta_x(y) for T[x][y].

Define three maps from S^3 to S^3:
  s_12(x,y,z) = ( M[x][y], T[x][y], z )
  s_23(x,y,z) = ( x, M[y][z], T[y][z] )
  s_13(x,y,z) = ( M[x][z], y, T[x][z] )
The pair (S, s) is a SET-THEORETIC SOLUTION OF THE PENTAGON EQUATION when

        s_23( s_13( s_12(x,y,z) ) )  =  s_12( s_23(x,y,z) )

holds for every triple (x, y, z) in S^3.  (Equivalently: (x.y).z = x.(y.z),
theta_x(y) . theta_{{x.y}}(z) = theta_x(y.z), and
theta_{{theta_x(y)}}( theta_{{x.y}}(z) ) = theta_y(z), for all x, y, z in S.)

Below are the tables M and T of one such solution, with {inst['holes']} entries erased
and shown as "?".  Rows are indexed by the first argument, columns by the second;
both are 0-indexed, and row i is printed on line i.

M (multiplication table, {n} rows of {n} entries):
{_fmt(inst['mul'])}

T (theta table, {n} rows of {n} entries):
{_fmt(inst['theta'])}

The erased cells, in order, are:
{blist}

TASK.  Replace every "?" by an element of S so that the completed pair (M, T) is a
set-theoretic solution of the Pentagon Equation on S.  Any completion that
satisfies the equation for all {n}^3 triples is accepted.

Give your final answer inside <answer></answer> tags, as the {inst['holes']} restored values
in exactly the order the erased cells are listed above, separated by commas.
Example: <answer>3, 17, 42</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        txt += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        txt += "\n\nHint: " + PLACEBO_HINT
    return txt


# ----------------------------------------------------------------------------
# parsing / verification
# ----------------------------------------------------------------------------
def parse_answer(text: object):
    if not isinstance(text, str):
        return None
    m = re.findall(r"<answer>(.*?)</answer>", text, re.S | re.I)
    body = m[-1] if m else text
    body = body.replace("```", " ")
    nums = re.findall(r"-?\d+", body)
    if not nums:
        return None
    try:
        return [int(v) for v in nums]
    except ValueError:  # pragma: no cover
        return None


def verify(inst: dict[str, Any], answer: object) -> tuple[bool, str]:
    n = inst["size"]
    blanks = [tuple(b) for b in inst["blanks"]]
    if isinstance(answer, tuple):
        answer = list(answer)
    if not isinstance(answer, list):
        return False, "answer is not a list"
    if len(answer) != len(blanks):
        return False, f"expected {len(blanks)} values, got {len(answer)}"
    vals = []
    for v in answer:
        if isinstance(v, bool) or not isinstance(v, int):
            return False, "answer contains a non-integer entry"
        if not (0 <= v < n):
            return False, f"entry {v} outside 0..{n-1}"
        vals.append(v)
    mul = [row[:] for row in inst["mul"]]
    th = [row[:] for row in inst["theta"]]
    for (w, x, y), v in zip(blanks, vals):
        tab = mul if w == "M" else th
        if tab[x][y] is not None:
            return False, f"cell {w}[{x}][{y}] was not blank"
        tab[x][y] = v
    for tab, name in ((mul, "M"), (th, "T")):
        for x in range(n):
            for y in range(n):
                if tab[x][y] is None:
                    return False, f"cell {name}[{x}][{y}] still unfilled"
    return _pentagon(mul, th, n)


# ----------------------------------------------------------------------------
# G4 / G5 helpers
# ----------------------------------------------------------------------------
def random_candidate(inst: dict[str, Any], rng: random.Random):
    """Structure-aware: a solver reading the statement knows only the shape --
    `holes` elements of S.  (P1)-(P3) are exactly what it has to work out.)"""
    n = inst["size"]
    return [rng.randrange(n) for _ in range(inst["holes"])]


def search_space(inst: dict[str, Any]) -> int:
    return inst["size"] ** inst["holes"]


def enumerate_all(inst: dict[str, Any], cap: int = 5000, node_cap: int = 400_000):
    """Exact count of valid completions, or None when the cap is hit."""
    n = inst["size"]
    blanks = [tuple(b) for b in inst["blanks"]]
    mul = [row[:] for row in inst["mul"]]
    th = [row[:] for row in inst["theta"]]
    tabs = {"M": mul, "T": th}
    nodes = [0]
    count = [0]

    def local_ok():
        def gv(t, a, b):
            if a is None or b is None:
                return None
            return t[a][b]
        for x in range(n):
            for y in range(n):
                xy = mul[x][y]; txy = th[x][y]
                for z in range(n):
                    yz = mul[y][z]
                    l = gv(mul, xy, z); r = gv(mul, x, yz)
                    if l is not None and r is not None and l != r:
                        return False
                    l = gv(mul, txy, gv(th, xy, z)); r = gv(th, x, yz)
                    if l is not None and r is not None and l != r:
                        return False
                    l = gv(th, txy, gv(th, xy, z)); r = gv(th, y, z)
                    if l is not None and r is not None and l != r:
                        return False
        return True

    def rec(i):
        nodes[0] += 1
        if nodes[0] > node_cap or count[0] >= cap:
            raise TimeoutError
        if i == len(blanks):
            if _pentagon(mul, th, n)[0]:
                count[0] += 1
            return
        w, x, y = blanks[i]
        tab = tabs[w]
        for v in range(n):
            tab[x][y] = v
            if local_ok():
                rec(i + 1)
            tab[x][y] = None

    try:
        rec(0)
    except TimeoutError:
        return None
    return count[0]


def canonical_key(inst: dict[str, Any]) -> str:
    """Invariant under relabelling S by any permutation, and under reordering the
    blank list.  Colour-refinement on the two tables, then a sorted digest."""
    n = inst["size"]
    mul = inst["mul"]; th = inst["theta"]
    col = [0] * n
    for _ in range(n + 2):
        sig = []
        for x in range(n):
            rowm = tuple(sorted((-1 if mul[x][y] is None else col[mul[x][y]]) for y in range(n)))
            colm = tuple(sorted((-1 if mul[y][x] is None else col[mul[y][x]]) for y in range(n)))
            rowt = tuple(sorted((-1 if th[x][y] is None else col[th[x][y]]) for y in range(n)))
            colt = tuple(sorted((-1 if th[y][x] is None else col[th[y][x]]) for y in range(n)))
            nb = sum(1 for y in range(n) if mul[x][y] is None) + \
                 sum(1 for y in range(n) if th[x][y] is None)
            nbc = sum(1 for y in range(n) if mul[y][x] is None) + \
                  sum(1 for y in range(n) if th[y][x] is None)
            sig.append((col[x], nb, nbc, rowm, colm, rowt, colt))
        order = sorted(set(sig))
        newcol = [order.index(sig[x]) for x in range(n)]
        if newcol == col:
            break
        col = newcol
    multiset = sorted(
        (col[x], col[y],
         -1 if mul[x][y] is None else col[mul[x][y]],
         -1 if th[x][y] is None else col[th[x][y]])
        for x in range(n) for y in range(n)
    )
    payload = json.dumps([n, inst["holes"], sorted(col), multiset], separators=(",", ":"))
    import hashlib
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def escalate(params: dict[str, Any]) -> dict[str, Any] | str | None:
    """Grow the ground set at FIXED answer length.

    Honest note: this axis was measured and it makes the family EASIER, not
    harder -- at fixed `holes` a larger |S| means a lower hole density and unit
    propagation still closes every cell with zero backtracks (|S| = 40, holes =
    100: 0 backtracks, 0.47 s).  The dial is implemented as the contract asks;
    the family is nevertheless rejected on H.  See REJECTED.md.
    """
    p = dict(params)
    m = int(p.get("m", 4)); q = int(p.get("q", 1)); g = int(p.get("g", 3))
    # two dials move: the group factor and the torsor factor of the ground set.
    if g < 11:
        g = g + 2
    m = m + 1
    p["m"] = m; p["g"] = g
    p["n"] = (m * q + int(p.get("r", 0))) * g
    if p["n"] > 96:
        return "cap_bound"
    return p


def selftest() -> dict[str, Any]:  # pragma: no cover - measurement driver lives outside
    import measure  # noqa: F401
    return measure.run()
