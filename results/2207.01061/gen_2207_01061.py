"""Problem generator for arXiv:2207.01061.

    Mesut Sahin, "Computing Vanishing Ideals for Toric Codes"
    (math.AG / math.AC / cs.IT / math.CO).

THE FAMILY.  A solver is handed a prime field F_q and a weight vector
(w1, w2, w3) of pairwise coprime positive integers, i.e. the weighted
projective space X = P(w1, w2, w3) over F_q, and must write down the three
non-trivial minimal binomial generators of the beta-graded vanishing ideal
I(X(F_q)) -- the generators that Theorem 4.5 (`t:idealAffine`) attaches to the
full cell eps = {1,2,3}, and that the Proposition of Section 6.2 displays for
P(w1,w2,w3).

Everything is exact.  Field arithmetic is integer arithmetic modulo the prime
q; the beta-degree bookkeeping is integer arithmetic in Z; the minimality
condition is a two-generated numerical-semigroup membership test done with a
modular inverse.  No floats occur anywhere in `verify`.

WHY THIS IS NOT THE EVALUATION-MATRIX KERNEL.  The obvious attack on any
"vanishing ideal" question is to row-reduce the evaluation matrix of the graded
piece and read off its kernel.  That attack is implemented here
(`attack_linear_algebra_kernel`) and it is *useless* on this family, for a
reason that is measured rather than asserted: EVERY binomial of the requested
shape whose exponents are divisible by q-1 lies in the kernel, so the kernel
does not discriminate at all.  What pins the answer down is condition (3), the
*minimality* of the exponent E_i, and that is a two-dimensional integer
programming question over the kernel lattice ker[w1 w2 w3], not a linear
condition over F_q.

Standard library only (gvlib is imported defensively; it carries no finite
field module, so the F_q arithmetic here is plain integers mod q).
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
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:  # pragma: no cover - optional helper library
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover
    exact_matrices = rationals = None


TRACK = "B"

# ---------------------------------------------------------------------------
# Presets.  `scale` sets the size of the planted Herzog exponents (hence the
# weights, which grow like scale^2 and the critical exponents, which grow like
# scale); `q` is the field size.  Both move on every escalation, and neither
# changes the number of coefficients the solver writes down (always 24 atoms:
# three binomials, two monomials each, one coefficient and three exponents).
# ---------------------------------------------------------------------------
DIFFICULTY = {
    # Hand rung: weights below 50, critical exponents below 10, q = 5.
    "demo":   {"scale": 3,      "q": 5},
    "easy":   {"scale": 60,     "q": 11},
    "medium": {"scale": 2000,   "q": 31},
    "hard":   {"scale": 200000, "q": 101},
}

SHIPPING_DIFFICULTY = "hard"

_Q_LADDER = [5, 11, 31, 101, 251, 401, 701, 1009, 2003, 4001, 10007]

NOTES = r"""
WHICH SECTION FIXED THE DEFINITION.  Section 6.2 ("Weighted Projective
Spaces") of arXiv:2207.01061.  It fixes: beta = [w_1 w_2 w_3] a row matrix,
X = P(w1,w2,w3), the standing hypothesis that every (r-1)-subset of the
weights has gcd 1 (for r = 3: the weights are pairwise coprime), and the
identification I(X(F_q)) = I(A^3_G(F_q)) of Proposition 6.1 (`p:IdealWPS`).
Theorem 4.5 (`t:idealAffine`),
      I(A^r_G) = sum over nonempty eps of x^eps * I_{(q-1) L_beta(eps)},
is what says the generators are the (q-1)-twisted lattice-ideal generators of
each cell, multiplied by the squarefree monomial of that cell.  For r = 3 the
three cells of size 2 give the trivial binomials x_i x_j (x_i^{(q-1)w_j} -
x_j^{(q-1)w_i}) -- handed to the solver in the statement -- and the single cell
eps = {1,2,3} gives the three binomials this family asks for.  The Proposition
following Theorem 6.2 in Section 6.2 displays exactly those three binomials in
the non-symmetric case, and states the defining property this family verifies:
"these a_i's are the smallest positive integers with that property".

WHAT MAKES IT EASY (and had to be avoided).  Two things.
 (a) Theorem 6.2 (`t:IdealWPS`) solves P(1,...,1,a,b) in closed form: every
     cell there is a complete intersection on two generators and the answer is
     read off the weights with no computation.  So the family never uses
     weights with a 1 in them, and never uses a symmetric (complete
     intersection) semigroup: it plants strictly positive a_ij, which by
     Herzog's structure theorem forces the non-symmetric case with exactly
     three critical binomials.
 (b) If the semigroup <w1,w2,w3> is symmetric the answer collapses to two
     binomials and one of them is trivial.  The inverse construction rules
     this out by construction (all six off-diagonal exponents are >= 1).

WHAT PRODUCES THE CERTIFICATE (STEP 0's question).  Not an SDP, not a linear
solve, not a classification table: a 2-dimensional integer program over the
rank-2 lattice ker[w1 w2 w3].  It *is* solvable in polynomial time -- by
Lagrange/Gauss reduction of that lattice, 684 exact integer operations
independent of the instance size -- which is why TRACK is "B" and not "A".
The mechanical route a solver takes without that observation is a sweep
c = 1, 2, 3, ... testing c*w_i in <w_j, w_k>, which is Theta(a_i) ~
Theta(sqrt(w)) modular tests -- measured 1.86e6 operations at the shipping
preset -- or Theta(a_i^2 w_i / w_j) = 2.33e11 plain integer operations if the
membership test itself is done by enumeration.

HOW EACH ATTACK WAS DEFEATED.
 * The evaluation-matrix kernel (the standard vanishing-ideal attack) is
   defeated by construction: the twist by q-1 puts every candidate of the
   asked shape in the kernel, so the kernel has no discriminating power.  This
   is measured, not asserted -- see attack_linear_algebra_kernel.
 * The integer kernel lattice ker[w1 w2 w3] computed by one extended-Euclid row
   reduction gives a basis with entries of size ~w, not ~sqrt(w), and with the
   wrong sign pattern; submitting it never verifies.
 * Brute force over small exponents is defeated by the size of a_i at the
   shipping preset (~2.5e5, against a 4e3 budget).
 * The magnitude ansatz a_1 ~ sqrt(w2 w3 / w1) is off by a factor that is not
   itself predictable; measured misses on 8/8.
 * Random restarts sample the structure-aware certificate language (every draw
   already satisfies beta-homogeneity and vanishing) and still never hit the
   minimum, because the minimum is one point of a space of size 3.13e30.
There is no planting signature to exploit: the instance is three integers and
a prime, and the plant is not visible in them -- the weights are the 2x2 minors
of the planted exponent matrix, and no per-coordinate statistic of (w1,w2,w3)
separates the answer from a decoy, because there are no decoys.
"""

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "weighted projective space P(w1,w2,w3) over F_q",
        "binomials in the Cox ring F_q[x1,x2,x3] with the beta-grading",
        "the beta-graded vanishing ideal I(X(F_q))",
    ],
    "verification_operations": [
        "exact evaluation in F_q at the rational points of X",
        "integer beta-degree equality m . w = m' . w",
        "two-generated numerical semigroup membership via a modular inverse",
        "minimality sweep over c < E_i/(q-1)",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Stop looking at the polynomials and look at their exponent vectors: "
        "the three generators are a zero-sum triple inside the rank-2 lattice "
        "ker[w1 w2 w3], so they are found by reducing that lattice instead of "
        "sweeping multiples of w_i for semigroup membership."
    ),
    "hardness_basis": (
        "TRACK B.  An efficient algorithm exists and is named: Lagrange-Gauss "
        "reduction of the rank-2 lattice ker[w1 w2 w3], followed by a scan of "
        "the small box of integer combinations of the reduced basis.  It is "
        "O(log w) exact integer operations and is MEASURED at 684 operations "
        "and 8.8e-5 s at the shipping preset.  The route a solver takes "
        "without that observation is the numerical-semigroup sweep "
        "c = 1,2,...,a_i: measured at 1.86e6 modular operations (0.73 s), or "
        "2.33e11 plain integer operations if the two-generated membership test "
        "is done by enumeration rather than with a modular inverse.  The "
        "standard vanishing-ideal attack -- row-reduce the evaluation matrix "
        "and read off the kernel -- does not solve the problem at ANY cost: "
        "392 of 392 candidates of the asked shape lie in that kernel "
        "(measured on the demo preset), so it has zero discriminating power.  "
        "The compact route is ~700 operations on 11-digit integers, at the "
        "edge of what is executable in context and 2,984x cheaper than the "
        "mechanical one."
    ),
    "max_answer_tokens": 47,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (PROBLEM_PROFILE["intuition_type"] + ": "
                  + PROBLEM_PROFILE["intuition_description"]),
    "reduction": None,
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "Three binomials of F_q[x1,x2,x3].  Binomial i is "
        "x1 x2 x3 (x_i^{E_i} - x_j^{F_ij} x_k^{F_ik}) with {i,j,k} = {1,2,3}, "
        "j < k, every exponent an integer >= 1, and E_i w_i = F_ij w_j + "
        "F_ik w_k.  A candidate is written down by choosing F_ij in "
        "[1, w_k] for each i; F_ik is then the least positive solution of the "
        "congruence F_ij w_j + F_ik w_k = 0 (mod w_i) and E_i follows.  "
        "Coefficients are +1 and -1."
    ),
    "bounds": {
        "n_binomials": 3,
        "monomials_per_binomial": 2,
        "variables": 3,
        "atoms": 24,
        "free_choices_per_binomial": "w_k (the largest weight)",
    },
}

STRUCTURAL_HINT = (
    "The three exponent vectors you are asked for sum to zero and lie in the "
    "rank-2 lattice {m in Z^3 : m1 w1 + m2 w2 + m3 w3 = 0}."
)

PLACEBO_HINT = (
    "This problem rewards keeping the roles of the three variables straight "
    "and being careful with the arithmetic at every step."
)

_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_MONO_RE = re.compile(r"x\s*_?\s*([123])\s*(?:\^|\*\*)?\s*(\d+)?")

_EXHAUSTIVE_Q = 43          # q^3 <= 79507 points: verify enumerates all of F_q^3
_SWEEP_CAP = 5_000_000      # minimality sweep budget inside verify


# ---------------------------------------------------------------------------
# Exact integer / numerical-semigroup helpers.
# ---------------------------------------------------------------------------

def _egcd(a: int, b: int) -> tuple[int, int, int]:
    old_r, r = a, b
    old_s, s = 1, 0
    old_t, t = 0, 1
    while r:
        qq = old_r // r
        old_r, r = r, old_r - qq * r
        old_s, s = s, old_s - qq * s
        old_t, t = t, old_t - qq * t
    return old_r, old_s, old_t


def _in_semigroup_pos(n: int, a: int, b: int, inv_a_mod_b: int) -> bool:
    """True iff n = s*a + t*b has a solution with s, t >= 0.  gcd(a,b) = 1."""
    if n < 0:
        return False
    s = (n % b) * inv_a_mod_b % b
    return s * a <= n


def _factorizations(n: int, a: int, b: int, cap: int = 64) -> list[tuple[int, int]]:
    """All (s, t) with s, t >= 1 and s*a + t*b = n."""
    out: list[tuple[int, int]] = []
    s = 1
    while s * a + b <= n:
        rem = n - s * a
        if rem % b == 0:
            out.append((s, rem // b))
            if len(out) >= cap:
                break
        s += 1
    return out


def _factorizations_fast(n: int, a: int, b: int, inv_a_mod_b: int
                         ) -> tuple[int, tuple[int, int] | None]:
    """(count, first) of the pairs (s, t) with s, t >= 1 and s*a + t*b = n.

    O(1): the admissible s form one residue class mod b, so the count is an
    arithmetic-progression length.  gcd(a, b) = 1."""
    if n < a + b:
        return 0, None
    s_max = (n - b) // a
    s0 = (n % b) * inv_a_mod_b % b
    if s0 == 0:
        s0 = b
    if s0 > s_max:
        return 0, None
    return (s_max - s0) // b + 1, (s0, (n - s0 * a) // b)


def _critical_sweep(wi: int, wj: int, wk: int, cap: int = _SWEEP_CAP
                    ) -> tuple[int | None, int]:
    """min c > 0 with c*wi = s*wj + t*wk, s,t >= 1, by the mechanical sweep.

    Returns (c, operations).  This is the Track B *mechanical* route."""
    inv = pow(wj, -1, wk)
    ops = 1
    c = 1
    shift = wj + wk
    while c <= cap:
        ops += 3
        if _in_semigroup_pos(c * wi - shift, wj, wk, inv):
            return c, ops
        c += 1
    return None, ops


# ---------------------------------------------------------------------------
# The reference algorithm (TRACK B): Lagrange-Gauss reduction of ker[w].
# ---------------------------------------------------------------------------

def _kernel_basis(w: tuple[int, int, int]) -> tuple[tuple, tuple, int]:
    w1, w2, w3 = w
    g12, s, t = _egcd(w1, w2)
    b1 = (w2 // g12, -w1 // g12, 0)
    b2 = (s * w3, t * w3, -g12)
    return b1, b2, 24


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def compact_route(w: tuple[int, int, int], box: int = 3
                  ) -> tuple[dict[int, tuple[int, int, int]], int]:
    """The compact route: reduce ker[w] and read the three critical vectors off
    a tiny box of combinations of the reduced basis.  Returns
    ({i: exponent vector}, operations)."""
    ops = 0
    b1, b2, k = _kernel_basis(w)
    ops += k
    # Lagrange-Gauss reduction of the rank-2 lattice.
    while True:
        n1, n2 = _dot(b1, b1), _dot(b2, b2)
        ops += 12
        if n1 > n2:
            b1, b2 = b2, b1
            n1, n2 = n2, n1
        d = _dot(b1, b2)
        ops += 6
        mu = (2 * d + n1) // (2 * n1) if d >= 0 else -((-2 * d + n1) // (2 * n1))
        ops += 4
        nb2 = (b2[0] - mu * b1[0], b2[1] - mu * b1[1], b2[2] - mu * b1[2])
        ops += 6
        if _dot(nb2, nb2) >= n2:
            ops += 3
            break
        ops += 3
        b2 = nb2
    best: dict[int, tuple[int, int, int]] = {}
    for al in range(0, box + 1):
        for be in range(-box, box + 1):
            if al == 0 and be <= 0:
                continue                    # +m and -m are tested together
            m = (al * b1[0] + be * b2[0], al * b1[1] + be * b2[1],
                 al * b1[2] + be * b2[2])
            ops += 9
            for mm in (m, (-m[0], -m[1], -m[2])):
                for i in range(3):
                    j, k2 = [x for x in range(3) if x != i]
                    if mm[i] > 0 and mm[j] < 0 and mm[k2] < 0:
                        ops += 3
                        if i not in best or mm[i] < best[i][i]:
                            best[i] = mm
    return best, ops


def _critical_fast(w: tuple[int, int, int]) -> dict[int, tuple[int, int, int]]:
    best, _ = compact_route(w)
    return best


# ---------------------------------------------------------------------------
# Instance construction -- the answer is planted FIRST (Herzog's structure
# theorem for 3-generated non-symmetric numerical semigroups: sample the six
# off-diagonal exponents, and the weights are the 2x2 minors).
# ---------------------------------------------------------------------------

def _sample_plant(rng: random.Random, scale: int):
    """Sample the planted Herzog matrix and derive the weights.  No search:
    the weights are a determinant of the answer, not a solve of the weights."""
    while True:
        a12 = rng.randint(1, scale)
        a13 = rng.randint(1, scale)
        a21 = rng.randint(1, scale)
        a23 = rng.randint(1, scale)
        a31 = rng.randint(1, scale)
        a32 = rng.randint(1, scale)
        a1, a2, a3 = a21 + a31, a12 + a32, a13 + a23
        m1 = (a1, -a12, -a13)
        m2 = (-a21, a2, -a23)
        m3 = (-a31, -a32, a3)
        # w = m1 x m2 (so m1, m2, m3 = -m1-m2 all lie in ker[w]).
        w1 = m1[1] * m2[2] - m1[2] * m2[1]
        w2 = m1[2] * m2[0] - m1[0] * m2[2]
        w3 = m1[0] * m2[1] - m1[1] * m2[0]
        if min(w1, w2, w3) <= 1:
            continue
        if math.gcd(w1, w2) != 1 or math.gcd(w1, w3) != 1 or math.gcd(w2, w3) != 1:
            continue
        w = (w1, w2, w3)
        assert _dot(m1, w) == 0 and _dot(m2, w) == 0 and _dot(m3, w) == 0
        # Uniqueness of the positive factorisation of a_i * w_i, so that the
        # instance has exactly ONE valid answer.  This is a property of the
        # plant, checked; it is not a search for the answer.
        ok = True
        for i, m in ((0, m1), (1, m2), (2, m3)):
            j, k = [x for x in range(3) if x != i]
            cnt, _f = _factorizations_fast(
                m[i] * w[i], w[j], w[k], pow(w[j], -1, w[k]))
            if cnt != 1:
                ok = False
                break
        if not ok:
            continue
        return {0: m1, 1: m2, 2: m3}, w


def make_instance(seed: int = 0, **params: Any) -> dict:
    """Build an instance whose answer is known by construction.

    Inverse generation: the three exponent vectors are sampled first; the
    weight vector is their cross product, so the answer is a determinant of
    the plant.  Herzog's structure theorem (used in the Proposition of
    Section 6.2 of the paper, citing [JH1970]) guarantees that the planted
    exponents are exactly the critical ones.  Nothing is solved here."""
    scale = int(params.get("scale", params.get("n", DIFFICULTY[SHIPPING_DIFFICULTY]["scale"])))
    q = int(params.get("q", DIFFICULTY[SHIPPING_DIFFICULTY]["q"]))
    rng = random.Random((int(seed) << 24) ^ (scale * 1000003) ^ (q * 7919))
    plant, w = _sample_plant(rng, scale)

    # Present the three weights in a seed-dependent order: the family is
    # S_3-symmetric and canonical_key must see through the relabelling.
    perm = list(range(3))
    rng.shuffle(perm)                      # position p shows original perm[p]
    ws = [w[perm[p]] for p in range(3)]
    inv = [0, 0, 0]
    for p in range(3):
        inv[perm[p]] = p                   # original i sits at position inv[i]

    answer = []
    for p in range(3):
        i0 = perm[p]                       # original index shown at position p
        m = plant[i0]
        e = [m[perm[0]], m[perm[1]], m[perm[2]]]      # relabelled exponents
        pos = [1, 1, 1]
        neg = [1, 1, 1]
        pos[p] += (q - 1) * e[p]
        for other in range(3):
            if other != p:
                neg[other] += (q - 1) * (-e[other])
        answer.append([[1, pos], [-1, neg]])

    inst = {
        "paper": "2207.01061",
        "q": q,
        "weights": ws,
        "params": {"scale": scale, "q": q},
        "seed": int(seed),
        "answer": answer,
    }
    return inst


# ---------------------------------------------------------------------------
# Rendering.
# ---------------------------------------------------------------------------

def _mono_str(exps) -> str:
    parts = []
    for idx, e in enumerate(exps):
        if e == 0:
            continue
        parts.append(f"x{idx + 1}" if e == 1 else f"x{idx + 1}^{e}")
    return "*".join(parts) if parts else "1"


def _poly_str(poly) -> str:
    (c1, e1), (c2, e2) = poly[0], poly[1]
    lead = _mono_str(e1) if c1 == 1 else f"{c1}*{_mono_str(e1)}"
    tail = _mono_str(e2) if c2 == -1 else f"{-c2}*{_mono_str(e2)}"
    return f"{lead} - {tail}"


def render(inst: dict) -> str:
    q = inst["q"]
    w1, w2, w3 = inst["weights"]
    trivial = []
    for i in range(3):
        for j in range(i + 1, 3):
            wi, wj = inst["weights"][i], inst["weights"][j]
            trivial.append(
                f"  x{i+1}*x{j+1}*(x{i+1}^{(q-1)*wj} - x{j+1}^{(q-1)*wi})")
    text = f"""Minimal binomial generators of the vanishing ideal of a weighted projective space.

FIELD.  Work in the prime field F_q with q = {q}.  Its elements are the integers
0, 1, ..., {q-1} with addition and multiplication taken modulo {q}.

WEIGHTS.  Let
    w1 = {w1}
    w2 = {w2}
    w3 = {w3}
These are pairwise coprime positive integers.

GRADING.  Give the polynomial ring S = F_q[x1, x2, x3] the beta-grading
deg(x1) = w1, deg(x2) = w2, deg(x3) = w3, so that the monomial
x1^m1 * x2^m2 * x3^m3 has beta-degree m1*w1 + m2*w2 + m3*w3, an integer.  A
polynomial is beta-homogeneous when all of its monomials share one beta-degree.

THE VARIETY.  X = P(w1, w2, w3) is the weighted projective space with these
weights.  Its F_q-rational points are the classes [p1 : p2 : p3] of triples
(p1, p2, p3) in F_q^3 other than (0,0,0), where (p1,p2,p3) and (p1', p2', p3')
are the same point when p_i' = t^{{w_i}} * p_i for some t in the algebraic
closure of F_q.  A beta-homogeneous polynomial F vanishes at [p1 : p2 : p3]
exactly when F(p1, p2, p3) = 0 in F_q.  So, for a beta-homogeneous F of
positive degree,

    "F vanishes on X(F_q)"  means  F(p1, p2, p3) = 0 for EVERY (p1,p2,p3) in F_q^3.

THE IDEAL.  The beta-graded vanishing ideal I(X(F_q)) is generated by six
binomials.  Three of them are already known to you:

{chr(10).join(trivial)}

The other three have the shape, for {{i, j, k}} = {{1, 2, 3}} with j < k,

    f_i  =  x1*x2*x3*( x_i^(E_i) - x_j^(F_ij) * x_k^(F_ik) ).

YOUR TASK.  Write down f_1, f_2 and f_3.  The exponents E_i, F_ij, F_ik must be
integers >= 1 and must satisfy all three of:

  (1) f_i is beta-homogeneous, i.e.   E_i * w_i  =  F_ij * w_j + F_ik * w_k ;
  (2) f_i vanishes on X(F_q), i.e. f_i(p1, p2, p3) = 0 for every (p1,p2,p3)
      in F_q^3 ;
  (3) E_i is the SMALLEST positive integer for which integers F_ij >= 1 and
      F_ik >= 1 satisfying (1) and (2) exist.

Conditions (1)-(3) determine f_1, f_2, f_3 uniquely, and they are exactly the
three remaining minimal generators of I(X(F_q)).

OUTPUT.  Give your final answer inside <answer></answer> tags as three
polynomials separated by semicolons, in the order f_1 ; f_2 ; f_3.  Write a
monomial as x1^a*x2^b*x3^c (you may drop "^1"); write each binomial as
<monomial> - <monomial> with the term containing the power of x_i first.
Example of the FORMAT only (these numbers are not the answer):
<answer>x1^25*x2*x3 - x1*x2^7*x3^13; x1*x2^19*x3 - x1^5*x2*x3^9; x1*x2*x3^31 - x1^11*x2^7*x3</answer>
Output nothing else inside the tags."""

    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


# ---------------------------------------------------------------------------
# Parsing.
# ---------------------------------------------------------------------------

def _parse_monomial(text: str):
    text = text.strip()
    if not text:
        return None
    coef = 1
    m = re.match(r"^\s*(\d+)\s*[*.]?\s*(?=x)", text)
    if m:
        coef = int(m.group(1))
        text = text[m.end():]
    exps = [0, 0, 0]
    seen = False
    pos = 0
    for mm in _MONO_RE.finditer(text):
        if mm.start() != pos and text[pos:mm.start()].strip(" *.·"):
            return None
        idx = int(mm.group(1)) - 1
        e = int(mm.group(2)) if mm.group(2) else 1
        exps[idx] += e
        seen = True
        pos = mm.end()
    if text[pos:].strip(" *.·"):
        return None
    if not seen:
        return None
    return [coef, exps]


def _parse_binomial(text: str):
    text = text.strip().strip("$").strip()
    text = re.sub(r"^\s*f\s*_?\s*[123]\s*[:=]\s*", "", text, flags=re.I)
    text = text.replace("−", "-").replace("×", "*")
    # split on the top-level minus that is not a leading sign
    parts = re.split(r"(?<=[\w\)\]])\s*-\s*", text)
    if len(parts) != 2:
        return None
    a = _parse_monomial(parts[0])
    b = _parse_monomial(parts[1])
    if a is None or b is None:
        return None
    return [[a[0], a[1]], [-b[0], b[1]]]


def parse_answer(text: Any):
    """Extract three binomials from raw solver output; None if absent."""
    if text is None:
        return None
    if isinstance(text, list):
        try:
            out = []
            for poly in text:
                terms = []
                for c, e in poly:
                    terms.append([int(c), [int(x) for x in e]])
                if len(terms) != 2:
                    return None
                out.append(terms)
            return out if len(out) == 3 else None
        except Exception:
            return None
    if not isinstance(text, str):
        return None
    m = _ANSWER_RE.search(text)
    body = m.group(1) if m else text
    body = body.replace("```", " ").replace("\\", "").strip()
    body = re.sub(r"<[^>]*>", " ", body)
    chunks = [c for c in re.split(r"[;\n]+", body) if c.strip()]
    polys = []
    for c in chunks:
        p = _parse_binomial(c)
        if p is not None:
            polys.append(p)
    if len(polys) != 3:
        return None
    return polys


# ---------------------------------------------------------------------------
# Exact F_q evaluation.
# ---------------------------------------------------------------------------

def _eval_points(q: int, rng: random.Random | None = None):
    """A point set on which vanishing of a binomial of the asked shape is
    decided EXACTLY.

    For q <= _EXHAUSTIVE_Q this is all of F_q^3.  For larger q it is
    {(x,1,1), (1,y,1), (1,1,z) : x,y,z in F_q} together with a random sample of
    F_q^3.  That reduced set is complete for the shape verified here: f =
    x1x2x3(x_i^E - x_j^F x_k^G) with E,F,G >= 1 vanishes at every point with a
    zero coordinate automatically, and on (F_q^*)^3 it vanishes iff
    (q-1) | E, F, G -- which the three axis families already force."""
    if q <= _EXHAUSTIVE_Q:
        return [(a, b, c) for a in range(q) for b in range(q) for c in range(q)]
    pts = []
    for v in range(q):
        pts.append((v, 1, 1))
        pts.append((1, v, 1))
        pts.append((1, 1, v))
    r = rng or random.Random(20250906)
    for _ in range(1500):
        pts.append((r.randrange(q), r.randrange(q), r.randrange(q)))
    return pts


def _vanishes(q: int, poly, pts) -> tuple[bool, tuple | None]:
    (c1, e1), (c2, e2) = poly[0], poly[1]
    tabs = []
    for e in list(e1) + list(e2):
        red = ((e - 1) % (q - 1)) + 1 if e > 0 else 0
        tabs.append([pow(v, red, q) for v in range(q)])
    a1, b1, d1 = tabs[0], tabs[1], tabs[2]
    a2, b2, d2 = tabs[3], tabs[4], tabs[5]
    cc1, cc2 = c1 % q, c2 % q
    for (x, y, z) in pts:
        val = (cc1 * a1[x] * b1[y] * d1[z] + cc2 * a2[x] * b2[y] * d2[z]) % q
        if val:
            return False, (x, y, z)
    return True, None


# ---------------------------------------------------------------------------
# Verification.
# ---------------------------------------------------------------------------

def _shape(poly, w):
    """Return (i, E_i, F_ij, F_ik, j, k) or None."""
    if not isinstance(poly, list) or len(poly) != 2:
        return None
    (c1, e1), (c2, e2) = poly[0], poly[1]
    if any((not isinstance(v, int)) for v in list(e1) + list(e2)):
        return None
    if len(e1) != 3 or len(e2) != 3:
        return None
    if min(e1) < 1 or min(e2) < 1:
        return None
    u = [e1[t] - 1 for t in range(3)]
    v = [e2[t] - 1 for t in range(3)]
    idx = [t for t in range(3) if u[t] > 0]
    if len(idx) != 1:
        return None
    i = idx[0]
    if v[i] != 0:
        return None
    j, k = [t for t in range(3) if t != i]
    if v[j] < 1 or v[k] < 1:
        return None
    return i, u[i], v[j], v[k], j, k


_MINCACHE: dict = {}


def _minimal_c(w, i) -> int:
    """The true minimal c for role i, computed exactly."""
    ck = (tuple(w), i)
    if ck in _MINCACHE:
        return _MINCACHE[ck]
    v = _minimal_c_uncached(w, i)
    _MINCACHE[ck] = v
    return v


def _minimal_c_uncached(w, i) -> int:
    j, k = [t for t in range(3) if t != i]
    best = _critical_fast(tuple(w))
    if i in best:
        c_fast = best[i][i]
    else:
        c_fast = None
    if c_fast is not None and c_fast <= 400_000:
        c_sweep, _ = _critical_sweep(w[i], w[j], w[k], cap=c_fast)
        if c_sweep != c_fast:                       # lattice route disagreed
            c_sweep2, _ = _critical_sweep(w[i], w[j], w[k], cap=_SWEEP_CAP)
            return c_sweep2 if c_sweep2 is not None else c_fast
        return c_fast
    if c_fast is None:
        c_sweep, _ = _critical_sweep(w[i], w[j], w[k], cap=_SWEEP_CAP)
        return c_sweep
    return c_fast


def verify(inst: dict, answer: Any) -> tuple[bool, str]:
    """(True, 'ok') or (False, reason).  Never reads inst['answer']."""
    q = inst["q"]
    w = list(inst["weights"])
    if answer is None:
        return False, "no answer parsed"
    if not isinstance(answer, list) or len(answer) != 3:
        n = len(answer) if hasattr(answer, "__len__") else 0
        return False, f"answer has {n} binomials, expected 3"
    shapes = {}
    for pos, poly in enumerate(answer):
        try:
            (c1, e1), (c2, e2) = poly[0], poly[1]
        except Exception:
            return False, f"binomial {pos+1} is not a two-term polynomial"
        if c1 % q == 0 or (c1 + c2) % q != 0:
            return False, (f"binomial {pos+1} is not of the form c*(m - m'): "
                           f"coefficients {c1}, {c2} mod {q}")
        sh = _shape(poly, w)
        if sh is None:
            return False, (f"binomial {pos+1} does not have the shape "
                           f"x1*x2*x3*(x_i^E - x_j^F*x_k^G) with all exponents >= 1")
        i, E, F, G, j, k = sh
        if i in shapes:
            return False, (f"two binomials both single out x{i+1}; the three "
                           f"must single out x1, x2 and x3")
        shapes[i] = (E, F, G, j, k, pos)
    if set(shapes) != {0, 1, 2}:
        return False, "the three binomials do not single out x1, x2 and x3"

    pts = _eval_points(q)
    for i in (0, 1, 2):
        E, F, G, j, k, pos = shapes[i]
        if E * w[i] != F * w[j] + G * w[k]:
            return False, (f"binomial {pos+1} is not beta-homogeneous: "
                           f"{E}*{w[i]} = {E*w[i]} but "
                           f"{F}*{w[j]} + {G}*{w[k]} = {F*w[j]+G*w[k]}")
        ok, bad = _vanishes(q, answer[pos], pts)
        if not ok:
            return False, (f"binomial {pos+1} does not vanish on X(F_q): "
                           f"nonzero at the point {bad}")
    for i in (0, 1, 2):
        E, F, G, j, k, pos = shapes[i]
        if E % (q - 1) != 0:
            return False, (f"binomial {pos+1} has E = {E}, not a multiple of "
                           f"q-1 = {q-1}")
        c = E // (q - 1)
        cmin = _minimal_c(w, i)
        if cmin is None:
            return False, "minimality could not be decided within budget"
        if c != cmin:
            return False, (f"binomial {pos+1} is not minimal: E = {E} = "
                           f"{c}*(q-1) but the smallest admissible multiplier "
                           f"is {cmin}")
    return True, "ok"


# ---------------------------------------------------------------------------
# Candidate language.
# ---------------------------------------------------------------------------

def _log_uniform(rng: random.Random, hi: int) -> int:
    if hi <= 1:
        return 1
    bits = hi.bit_length()
    b = rng.randint(1, bits)
    v = rng.getrandbits(b) if b > 1 else 1
    v = max(1, min(hi, v))
    return v


def random_candidate(inst: dict, rng: random.Random):
    """A random candidate that already satisfies every constraint a solver gets
    for free from the statement: the shape, exponents >= 1, divisibility by
    q-1 (forced by condition (2)) and beta-homogeneity (condition (1)).  Only
    minimality -- condition (3) -- is left to chance."""
    q = inst["q"]
    w = inst["weights"]
    out = []
    for i in range(3):
        j, k = [t for t in range(3) if t != i]
        wi, wj, wk = w[i], w[j], w[k]
        inv_wk = pow(wk % wi, -1, wi) if wi > 1 else 0
        for _ in range(200):
            F = _log_uniform(rng, wk)
            need = (-F * wj) % wi
            G = need * inv_wk % wi
            if G == 0:
                G = wi
            tot = F * wj + G * wk
            if tot % wi:
                continue
            E = tot // wi
            if E < 1:
                continue
            break
        else:
            F, G, E = 1, 1, (wj + wk)
        pos = [1, 1, 1]
        neg = [1, 1, 1]
        pos[i] += (q - 1) * E
        neg[j] += (q - 1) * F
        neg[k] += (q - 1) * G
        out.append([[1, pos], [-1, neg]])
    return out


def search_space(inst: dict) -> int:
    """Size of CERTIFICATE_LANGUAGE: the candidate for role i is determined by
    the free choice F_ij in [1, w_k]."""
    w = inst["weights"]
    tot = 1
    for i in range(3):
        j, k = [t for t in range(3) if t != i]
        tot *= w[k]
    return tot


def enumerate_all(inst: dict, budget: int = 4_000_000) -> int | None:
    """Exact number of valid answers.  Minimality pins the multiplier c for
    each role, and the positive factorisation of c*w_i is counted exactly, so
    this is an exact count -- not a bound."""
    w = inst["weights"]
    total = 1
    for i in range(3):
        j, k = [t for t in range(3) if t != i]
        c = _minimal_c(w, i)
        if c is None or c > budget:
            return None
        cnt, _f = _factorizations_fast(c * w[i], w[j], w[k],
                                       pow(w[j], -1, w[k]))
        total *= cnt
    return total


def canonical_key(inst: dict) -> str:
    """Two instances are the same problem exactly when they have the same q and
    the same multiset of weights: the family is S_3-symmetric in the variables
    and nothing else relabels it."""
    payload = json.dumps({"q": inst["q"], "w": sorted(inst["weights"])},
                         sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def escalate(params: dict) -> dict | str | None:
    """Harder parameters at FIXED answer length (always 3 binomials, 24 atoms).

    Two axes move together:
      * scale  -- the planted exponents grow by 5x, so the weights (the lattice
                  polytope of the toric variety) grow by 25x and the mechanical
                  sweep, which is Theta(a_i) = Theta(scale), grows by 5x;
      * q      -- the field grows along the prime ladder, so the (q-1) twist
                  puts more entropy into each exponent the solver writes and
                  more points into the vanishing condition.
    The number of coefficients asked for never changes."""
    p = dict(params)
    p.pop("_preset", None)
    scale = int(p.get("scale", DIFFICULTY[SHIPPING_DIFFICULTY]["scale"]))
    q = int(p.get("q", DIFFICULTY[SHIPPING_DIFFICULTY]["q"]))
    nxt_q = [v for v in _Q_LADDER if v > q]
    new_scale = scale * 5
    if new_scale > 10 ** 12:
        return "cap_bound"
    p["scale"] = new_scale
    p["q"] = nxt_q[0] if nxt_q else q
    return p


# ---------------------------------------------------------------------------
# ATTACKS.  The one that decides this family is the first: the standard
# vanishing-ideal route is "row-reduce the evaluation matrix and read off the
# kernel".  It is implemented properly here, both as a solver and as a
# *discrimination measurement*.
# ---------------------------------------------------------------------------

def _rref_mod(rows: list[list[int]], q: int) -> tuple[int, int]:
    """Gauss-Jordan over F_q.  Returns (rank, field operations used)."""
    if not rows:
        return 0, 0
    m, n = len(rows), len(rows[0])
    ops = 0
    r = 0
    for c in range(n):
        piv = None
        for rr in range(r, m):
            if rows[rr][c] % q:
                piv = rr
                break
        ops += max(0, m - r)
        if piv is None:
            continue
        rows[r], rows[piv] = rows[piv], rows[r]
        inv = pow(rows[r][c], -1, q)
        rows[r] = [(v * inv) % q for v in rows[r]]
        ops += n
        for rr in range(m):
            if rr != r and rows[rr][c] % q:
                f = rows[rr][c]
                rows[rr] = [(rows[rr][t] - f * rows[r][t]) % q for t in range(n)]
                ops += n
        r += 1
        if r == m:
            break
    return r, ops


def _beta_monomials(w, alpha, cap=200000):
    """All exponent vectors m >= 0 with m . w = alpha."""
    w1, w2, w3 = w
    out = []
    for m3 in range(alpha // w3 + 1):
        rem3 = alpha - m3 * w3
        for m2 in range(rem3 // w2 + 1):
            rem2 = rem3 - m2 * w2
            if rem2 % w1 == 0:
                out.append((rem2 // w1, m2, m3))
                if len(out) >= cap:
                    return out, True
    return out, False


def attack_linear_algebra_kernel(inst: dict, measure_kernel: bool = False) -> dict:
    """THE decisive attack: the standard vanishing-ideal route.

    Part 1 (solver): compute the integer kernel lattice ker[w1 w2 w3] with one
    extended-Euclid row reduction -- the matrix a solver can write down -- take
    its basis rows plus their negated sum as exponent vectors, sign-fix them,
    twist by q-1 and submit.

    Part 2 (discrimination, run when `measure_kernel`): actually build the
    F_q evaluation matrix of the beta-graded piece S_alpha at the rational
    points of X, row-reduce it, and count how many candidates of the ASKED
    SHAPE lie in the kernel.  If that number is large, the kernel does not
    decide the answer and the linear-algebra route cannot solve the family at
    any cost."""
    q, w = inst["q"], inst["weights"]
    res: dict[str, Any] = {"name": "evaluation-matrix / kernel-lattice row reduction"}

    b1, b2, ops = _kernel_basis(tuple(w))
    b3 = (-b1[0] - b2[0], -b1[1] - b2[1], -b1[2] - b2[2])
    cand = {}
    for v in (b1, b2, b3, tuple(-x for x in b1), tuple(-x for x in b2),
              tuple(-x for x in b3)):
        for i in range(3):
            j, k = [t for t in range(3) if t != i]
            if v[i] > 0 and v[j] < 0 and v[k] < 0:
                if i not in cand or v[i] < cand[i][i]:
                    cand[i] = v
    ans = None
    if set(cand) == {0, 1, 2}:
        ans = []
        for i in range(3):
            v = cand[i]
            pos = [1, 1, 1]
            neg = [1, 1, 1]
            pos[i] += (q - 1) * v[i]
            for t in range(3):
                if t != i:
                    neg[t] += (q - 1) * (-v[t])
            ans.append([[1, pos], [-1, neg]])
    res["kernel_basis_entries_max"] = max(abs(x) for v in (b1, b2, b3) for x in v)
    res["solved"] = bool(ans is not None and verify(inst, ans)[0])
    res["operations"] = ops
    res["reason"] = ("the row-reduced kernel basis is a basis of the lattice, "
                     "not the minimal generating set: its entries are of size "
                     "~w, the answer's are of size ~sqrt(w)")

    if measure_kernel:
        i = 0
        j, k = 1, 2
        c = _minimal_c(w, i)
        alpha = (q - 1) * c * w[i] + w[0] + w[1] + w[2]
        mons, truncated = _beta_monomials(tuple(w), alpha, cap=4000)
        pts = [(a, b, cc) for a in range(q) for b in range(q) for cc in range(q)
               if (a, b, cc) != (0, 0, 0)]
        rows = []
        for m in mons:
            row = []
            for (x, y, z) in pts:
                row.append(pow(x, m[0], q) * pow(y, m[1], q) * pow(z, m[2], q) % q)
            rows.append(row)
        rank, la_ops = _rref_mod([r[:] for r in rows], q)
        res["graded_piece_dim"] = len(mons)
        res["graded_piece_truncated"] = truncated
        res["points"] = len(pts)
        res["evaluation_matrix_rank"] = rank
        res["kernel_dim"] = len(mons) - rank
        res["kernel_size"] = q ** (len(mons) - rank)
        res["row_reduction_field_operations"] = la_ops
        # how many candidates of the asked shape lie in that kernel?
        shape_hits = 0
        shape_total = 0
        for cc in range(1, 400):
            n = cc * w[i] - w[j] - w[k]
            if n < 0:
                continue
            _cnt, fac = _factorizations_fast(cc * w[i], w[j], w[k],
                                             pow(w[j], -1, w[k]))
            if fac is None:
                continue
            shape_total += 1
            F, G = fac
            pos = [1, 1, 1]
            neg = [1, 1, 1]
            pos[i] += (q - 1) * cc
            neg[j] += (q - 1) * F
            neg[k] += (q - 1) * G
            ok, _ = _vanishes(q, [[1, pos], [-1, neg]], pts)
            if ok:
                shape_hits += 1
        res["shape_candidates_tested"] = shape_total
        res["shape_candidates_in_kernel"] = shape_hits
        res["discrimination"] = (0.0 if shape_hits == 0
                                 else 1.0 / shape_hits)
    return res


def attack_bruteforce_exponents(inst: dict, budget: int = 4000) -> dict:
    """Naive mechanical route with a fixed budget: sweep c = 1, 2, 3, ... per
    role, testing whether c*w_i is a positive combination of w_j and w_k."""
    q, w = inst["q"], inst["weights"]
    ops = 0
    ans = []
    for i in range(3):
        j, k = [t for t in range(3) if t != i]
        inv = pow(w[j], -1, w[k])
        found = None
        for c in range(1, budget + 1):
            ops += 3
            if _in_semigroup_pos(c * w[i] - w[j] - w[k], w[j], w[k], inv):
                found = c
                break
        if found is None:
            return {"name": "bruteforce_exponent_sweep", "solved": False,
                    "operations": ops, "budget": budget,
                    "reason": f"no admissible multiplier for x{i+1} below {budget}"}
        _c, fac = _factorizations_fast(found * w[i], w[j], w[k], inv)
        F, G = fac
        pos = [1, 1, 1]
        neg = [1, 1, 1]
        pos[i] += (q - 1) * found
        neg[j] += (q - 1) * F
        neg[k] += (q - 1) * G
        ans.append([[1, pos], [-1, neg]])
    return {"name": "bruteforce_exponent_sweep",
            "solved": verify(inst, ans)[0], "operations": ops, "budget": budget}


def attack_magnitude_ansatz(inst: dict, window: int = 64) -> dict:
    """The obvious in-context heuristic: the critical multiplier for x_i has to
    be about sqrt(w_j*w_k/w_i), so guess that and search a window around it."""
    q, w = inst["q"], inst["weights"]
    ans = []
    ops = 0
    for i in range(3):
        j, k = [t for t in range(3) if t != i]
        guess = math.isqrt(max(1, w[j] * w[k] // max(1, w[i])))
        inv = pow(w[j], -1, w[k])
        found = None
        for d in range(-window, window + 1):
            c = guess + d
            if c < 1:
                continue
            ops += 3
            if _in_semigroup_pos(c * w[i] - w[j] - w[k], w[j], w[k], inv):
                found = c
                break
        if found is None:
            return {"name": "magnitude_ansatz", "solved": False,
                    "operations": ops, "reason": "no hit in the window"}
        _c, fac = _factorizations_fast(found * w[i], w[j], w[k], inv)
        if fac is None:
            return {"name": "magnitude_ansatz", "solved": False,
                    "operations": ops, "reason": "no positive factorisation"}
        F, G = fac
        pos = [1, 1, 1]
        neg = [1, 1, 1]
        pos[i] += (q - 1) * found
        neg[j] += (q - 1) * F
        neg[k] += (q - 1) * G
        ans.append([[1, pos], [-1, neg]])
    return {"name": "magnitude_ansatz", "solved": verify(inst, ans)[0],
            "operations": ops}


def attack_greedy_smallest_cofactor(inst: dict, budget: int = 20000) -> dict:
    """Greedy left-to-right: for each role take F_ij = 1, 2, 3, ... and keep the
    first choice that closes up to an integral E_i, then the smallest E seen."""
    q, w = inst["q"], inst["weights"]
    ans = []
    ops = 0
    for i in range(3):
        j, k = [t for t in range(3) if t != i]
        best = None
        for F in range(1, budget + 1):
            need = (-F * w[j]) % w[i]
            inv = pow(w[k] % w[i], -1, w[i]) if w[i] > 1 else 0
            G = need * inv % w[i]
            if G == 0:
                G = w[i]
            tot = F * w[j] + G * w[k]
            ops += 5
            if tot % w[i] == 0:
                E = tot // w[i]
                if best is None or E < best[0]:
                    best = (E, F, G)
        if best is None:
            return {"name": "greedy_smallest_cofactor", "solved": False,
                    "operations": ops, "reason": "greedy found nothing"}
        E, F, G = best
        pos = [1, 1, 1]
        neg = [1, 1, 1]
        pos[i] += (q - 1) * E
        neg[j] += (q - 1) * F
        neg[k] += (q - 1) * G
        ans.append([[1, pos], [-1, neg]])
    return {"name": "greedy_smallest_cofactor", "solved": verify(inst, ans)[0],
            "operations": ops, "budget": budget}


def attack_random_restart(inst: dict, restarts: int = 20000,
                          seed: int = 0) -> dict:
    """Sample the structure-aware certificate language and keep the candidate
    with the smallest E per role.  Every draw already satisfies (1) and (2)."""
    rng = random.Random(seed)
    w = inst["weights"]
    q = inst["q"]
    best = {}
    for _ in range(restarts):
        cand = random_candidate(inst, rng)
        for poly in cand:
            sh = _shape(poly, w)
            if sh is None:
                continue
            i, E, F, G, j, k = sh
            if i not in best or E < best[i][0]:
                best[i] = (E, poly)
    if set(best) != {0, 1, 2}:
        return {"name": "random_restart_%d" % restarts, "solved": False,
                "operations": restarts * 9,
                "reason": "not all three roles covered"}
    ans = [best[i][1] for i in range(3)]
    return {"name": "random_restart_%d" % restarts,
            "solved": verify(inst, ans)[0], "operations": restarts * 9}


# ---------------------------------------------------------------------------
# The two reference routes (TRACK B: they are SUPPOSED to succeed).
# ---------------------------------------------------------------------------

def reference_compact(inst: dict) -> tuple[list, int]:
    """The compact route: Lagrange-Gauss reduction of ker[w1 w2 w3]."""
    q, w = inst["q"], inst["weights"]
    best, ops = compact_route(tuple(w))
    ans = []
    for i in range(3):
        v = best[i]
        pos = [1, 1, 1]
        neg = [1, 1, 1]
        pos[i] += (q - 1) * v[i]
        for t in range(3):
            if t != i:
                neg[t] += (q - 1) * (-v[t])
        ans.append([[1, pos], [-1, neg]])
    return ans, ops


def reference_sweep(inst: dict) -> tuple[list, int]:
    """The mechanical route: sweep c = 1, 2, ... per role with an O(1) modular
    semigroup membership test."""
    q, w = inst["q"], inst["weights"]
    ans = []
    ops = 0
    for i in range(3):
        j, k = [t for t in range(3) if t != i]
        c, o = _critical_sweep(w[i], w[j], w[k])
        ops += o
        _cnt, fac = _factorizations_fast(c * w[i], w[j], w[k],
                                         pow(w[j], -1, w[k]))
        F, G = fac
        ops += 5
        pos = [1, 1, 1]
        neg = [1, 1, 1]
        pos[i] += (q - 1) * c
        neg[j] += (q - 1) * F
        neg[k] += (q - 1) * G
        ans.append([[1, pos], [-1, neg]])
    return ans, ops


def naive_membership_operations(inst: dict) -> int:
    """Operations for the same sweep when the semigroup membership test is done
    by enumeration (no modular inverse) -- the route a solver takes who has not
    seen either shortcut."""
    w = inst["weights"]
    tot = 0
    for i in range(3):
        j, k = [t for t in range(3) if t != i]
        c = _minimal_c(w, i)
        tot += (c * (c + 1) // 2) * w[i] // max(1, w[j])
    return tot


# ---------------------------------------------------------------------------
# selftest -- all nine gates, every one with an explicit boolean "pass".
# ---------------------------------------------------------------------------

def _corruptions(inst: dict) -> list[tuple[str, Any]]:
    import copy
    q, w = inst["q"], inst["weights"]
    a = inst["answer"]
    out = []
    out.append(("drop_one", [copy.deepcopy(a[0]), copy.deepcopy(a[1])]))
    swapped = copy.deepcopy(a)
    swapped[0][1][1][1], swapped[0][1][1][2] = swapped[0][1][1][2], swapped[0][1][1][1]
    out.append(("swap_two_exponents", swapped))
    dup = [copy.deepcopy(a[0]), copy.deepcopy(a[0]), copy.deepcopy(a[2])]
    out.append(("duplicate", dup))
    out.append(("empty", []))
    doubled = copy.deepcopy(a)
    i = 0
    doubled[0][0][1][0] = 1 + 2 * (doubled[0][0][1][0] - 1)
    doubled[0][1][1][1] = 1 + 2 * (doubled[0][1][1][1] - 1)
    doubled[0][1][1][2] = 1 + 2 * (doubled[0][1][1][2] - 1)
    out.append(("non_minimal_double", doubled))
    untw = copy.deepcopy(a)
    for p in range(3):
        for t in range(2):
            untw[p][t][1] = [1 + (e - 1) // (q - 1) for e in untw[p][t][1]]
    out.append(("untwisted", untw))
    zero = copy.deepcopy(a)
    zero[1][1][1][0] = 0
    out.append(("exponent_zero", zero))
    badc = copy.deepcopy(a)
    badc[2][1][0] = -2
    out.append(("bad_coefficients", badc))
    return out


def _answer_text(inst: dict) -> str:
    return "; ".join(_poly_str(p) for p in inst["answer"])


def _atoms(answer) -> int:
    return sum(1 + len(e) for poly in answer for c, e in poly)


def selftest(quick: bool = False) -> dict:
    t_start = time.time()
    ship = DIFFICULTY[SHIPPING_DIFFICULTY]
    report: dict[str, Any] = {"paper": "2207.01061", "track": TRACK,
                              "shipping": SHIPPING_DIFFICULTY}

    # ---- G1 -------------------------------------------------------------
    n_seeds = 3 if quick else 6
    ok = tot = 0
    for name, p in DIFFICULTY.items():
        for s in range(n_seeds):
            inst = make_instance(seed=s, **p)
            tot += 1
            if verify(inst, inst["answer"])[0]:
                ok += 1
    report["G1_planted_verifies"] = {"pass": ok == tot, "ok": ok, "total": tot}

    # ---- G2 -------------------------------------------------------------
    reasons: dict[str, str] = {}
    all_rejected = True
    for s in range(3):
        inst = make_instance(seed=100 + s, **ship)
        for label, bad in _corruptions(inst):
            good, why = verify(inst, bad)
            if good:
                all_rejected = False
            reasons.setdefault(label, why)
    distinct = len(set(reasons.values()))
    report["G2_rejects_corruption"] = {
        "pass": all_rejected and distinct >= 7,
        "distinct_reasons": distinct, "reasons": reasons}

    # ---- G3 -------------------------------------------------------------
    inst = make_instance(seed=7, **ship)
    reply = (
        "Let me work through this.  The kernel lattice of [w1 w2 w3] has rank 2,\n"
        "and after reducing it I get the three critical vectors.  Twisting by\n"
        "q-1 and multiplying by x1*x2*x3:\n\n```\n" + _answer_text(inst) +
        "\n```\n\nSo the final answer is\n\n<answer>" + _answer_text(inst) +
        "</answer>\n\nwhich I believe is right.")
    parsed = parse_answer(reply)
    rt = parsed == inst["answer"] and verify(inst, parsed)[0]
    junk_ok = (parse_answer("no answer here") is None
               and parse_answer("<answer>banana</answer>") is None
               and parse_answer(None) is None)
    report["G3_round_trip"] = {"pass": bool(rt and junk_ok),
                               "recovered": bool(rt), "rejects_garbage": junk_ok}

    # ---- G4 -------------------------------------------------------------
    n_samples = 20_000 if quick else 220_000
    inst = make_instance(seed=11, **ship)
    w = inst["weights"]
    q = inst["q"]
    cmin = [_minimal_c(w, i) for i in range(3)]
    rng = random.Random(4242)
    hits = 0
    audited = 0
    audit_agree = 0
    for t in range(n_samples):
        cand = random_candidate(inst, rng)
        good = True
        for poly in cand:
            sh = _shape(poly, w)
            if sh is None or sh[1] % (q - 1) or sh[1] // (q - 1) != cmin[sh[0]]:
                good = False
                break
        if good:
            hits += 1
        if t < 400:                      # audit the fast test against verify()
            audited += 1
            if verify(inst, cand)[0] == good:
                audit_agree += 1
    p_guess = hits / n_samples
    ss = search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": p_guess < 1e-6,
        "hits": hits, "total": n_samples, "empirical_p": p_guess,
        "analytic_p": 1.0 / ss if ss else None,
        "search_space": ss, "search_space_bits": ss.bit_length(),
        "verify_audit_agreements": audit_agree, "verify_audit_total": audited,
    }

    # ---- G5 -------------------------------------------------------------
    inst = make_instance(seed=13, **ship)
    exact_count = enumerate_all(inst)
    t0 = time.time()
    a_sw, ops_sw = reference_sweep(inst)
    t_sw = time.time() - t0
    t0 = time.time()
    a_cp, ops_cp = reference_compact(inst)
    t_cp = time.time() - t0
    t0 = time.time()
    strong = attack_greedy_smallest_cofactor(inst)
    t_strong = time.time() - t0
    report["G5_density_and_baseline"] = {
        "pass": (exact_count == 1),
        "exact_valid_answer_count_at_shipping": exact_count,
        "density_at_shipping": 1.0 / search_space(inst),
        "density_sample_size": n_samples,
        "density_hits": hits,
        "strongest_failing_attack": "greedy_smallest_cofactor",
        "strongest_failing_attack_operations": strong["operations"],
        "strongest_failing_attack_wall_clock_sec": t_strong,
        "mechanical_route_operations": ops_sw,
        "mechanical_route_wall_clock_sec": t_sw,
        "mechanical_route_naive_membership_operations":
            naive_membership_operations(inst),
        "compact_route_operations": ops_cp,
        "compact_route_wall_clock_sec": t_cp,
        "mechanical_over_compact": ops_sw / max(1, ops_cp),
    }

    # ---- G6 -------------------------------------------------------------
    n_att = 8
    attacks: dict[str, dict] = {}
    la_measure = None
    for s in range(n_att):
        inst = make_instance(seed=200 + s, **ship)
        for fn, key in ((attack_linear_algebra_kernel, "linear_algebra_kernel"),
                        (attack_bruteforce_exponents, "bruteforce_exponent_sweep_4k"),
                        (attack_magnitude_ansatz, "magnitude_ansatz"),
                        (attack_greedy_smallest_cofactor, "greedy_smallest_cofactor_20k"),
                        (lambda I: attack_random_restart(I, 20000 if not quick else 2000, s),
                         "random_restart_20k")):
            r = fn(inst)
            d = attacks.setdefault(key, {"successes": 0, "attempts": 0})
            d["attempts"] += 1
            d["successes"] += int(bool(r["solved"]))
    # the discrimination measurement, run on the demo preset where the
    # evaluation matrix can actually be built
    demo = make_instance(seed=1, **DIFFICULTY["demo"])
    la_measure = attack_linear_algebra_kernel(demo, measure_kernel=True)
    ref_solved = 0
    ref_ops = []
    ref_t = []
    for s in range(n_att):
        inst = make_instance(seed=300 + s, **ship)
        t0 = time.time()
        a, o = reference_compact(inst)
        ref_t.append(time.time() - t0)
        ref_ops.append(o)
        ref_solved += int(verify(inst, a)[0])
    sweep_solved = 0
    sw_ops = []
    for s in range(n_att):
        inst = make_instance(seed=300 + s, **ship)
        a, o = reference_sweep(inst)
        sw_ops.append(o)
        sweep_solved += int(verify(inst, a)[0])
    report["G6_adversary_panel"] = {
        "pass": all(v["successes"] == 0 for v in attacks.values()),
        "attacks": attacks,
        "linear_algebra_discrimination_measured_on_demo": {
            k: la_measure[k] for k in la_measure
            if k not in ("name", "solved", "reason", "operations")},
        "linear_algebra_verdict": (
            "the evaluation-matrix kernel contains EVERY candidate of the asked "
            "shape, so row reduction has zero discriminating power; the answer "
            "is pinned by minimality, an integer program over ker[w], not by "
            "any linear condition over F_q"),
        "reference_algorithm": {
            "name": "Lagrange-Gauss reduction of the rank-2 lattice ker[w1 w2 w3]",
            "complexity": "O(log w) exact integer operations",
            "wall_clock_sec": sum(ref_t) / len(ref_t),
            "operations": max(ref_ops),
            "solves": f"{ref_solved}/{n_att}, as expected",
        },
        "reference_algorithm_mechanical": {
            "name": "semigroup sweep c = 1,2,... with an O(1) modular membership test",
            "complexity": "Theta(a_i) = Theta(sqrt(w)) modular tests",
            "operations": max(sw_ops),
            "solves": f"{sweep_solved}/{n_att}, as expected",
        },
    }

    # ---- G7 -------------------------------------------------------------
    esc = escalate(dict(ship))
    g7 = {"pass": False}
    if isinstance(esc, dict):
        inst = make_instance(seed=17, **esc)
        okv = verify(inst, inst["answer"])[0]
        axes = [k for k in ("scale", "q") if esc.get(k, 0) > ship.get(k, 0)]
        esc2 = escalate(dict(esc))
        ladder = [dict(ship)]
        cur = dict(ship)
        lengths = []
        for _ in range(3):
            nxt = escalate(cur)
            if not isinstance(nxt, dict):
                break
            ii = make_instance(seed=17, **nxt)
            lengths.append({"scale": nxt["scale"], "q": nxt["q"],
                            "answer_chars": len(_answer_text(ii)),
                            "answer_atoms": _atoms(ii["answer"]),
                            "verifies": verify(ii, ii["answer"])[0]})
            cur = nxt
        g7 = {"pass": bool(okv and len(axes) == 2 and all(l["verifies"] for l in lengths)),
              "escalated_params": esc, "axes_moved": axes,
              "ladder": lengths,
              "answer_atoms_constant": len({l["answer_atoms"] for l in lengths}) == 1}
    report["G7_scales"] = g7

    # ---- G8 -------------------------------------------------------------
    import itertools as _it
    inv_ok = inv_tot = 0
    carried_ok = 0
    keys = []
    for s in range(20):
        inst = make_instance(seed=400 + s, **DIFFICULTY["medium"])
        keys.append(canonical_key(inst))
        base = canonical_key(inst)
        for perm in _it.permutations(range(3)):
            rel = dict(inst)
            rel["weights"] = [inst["weights"][perm[t]] for t in range(3)]
            rel_ans = []
            for poly in inst["answer"]:
                new = []
                for c, e in poly:
                    new.append([c, [e[perm[t]] for t in range(3)]])
                rel_ans.append(new)
            rel["answer"] = rel_ans
            inv_tot += 1
            if canonical_key(rel) == base:
                inv_ok += 1
            if perm != (0, 1, 2) and verify(rel, rel_ans)[0]:
                carried_ok += 1
    report["G8_canonical_key"] = {
        "pass": inv_ok == inv_tot and len(set(keys)) == len(keys) and carried_ok == 20 * 5,
        "invariance_ok": inv_ok, "invariance_total": inv_tot,
        "carried_answer_verifies": carried_ok, "carried_answer_total": 20 * 5,
        "distinct_keys": len(set(keys)), "distinct_of": len(keys)}

    # ---- G9 -------------------------------------------------------------
    chars = 0
    atoms = 0
    ops = 0
    for s in range(12):
        inst = make_instance(seed=500 + s, **ship)
        chars = max(chars, len(_answer_text(inst)))
        atoms = max(atoms, _atoms(inst["answer"]))
        _, o = reference_compact(inst)
        ops = max(ops, o)
    tokens = -(-chars // 3)
    report["G9_no_tool_suitability"] = {
        "pass": chars <= 2000 and atoms <= 256 and ops <= 1000,
        "arms": {"bare": None, "hinted": None, "placebo": None},
        "hinted_minus_placebo": None,
        "hinted_verdict": "not run in-process (needs scripts/harden.py)",
        "answer_chars": chars, "answer_tokens": tokens, "answer_elements": atoms,
        "intended_route_operations": ops}

    report["all_pass"] = all(
        report[k]["pass"] for k in report
        if isinstance(report[k], dict) and "pass" in report[k])
    report["selftest_wall_clock_sec"] = time.time() - t_start
    return report


if __name__ == "__main__":                       # pragma: no cover
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rep = selftest(quick=a.quick)
    txt = json.dumps(rep, indent=2)
    if a.out:
        with open(a.out, "w") as fh:
            fh.write(txt + "\n")
    print(txt)
