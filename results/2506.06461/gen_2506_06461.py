"""Problem generator for arXiv:2506.06461.

    Oleg Ogandzhanyants, Sergey Sadov, Margo Kondratieva,
    "Constructing strong starters of orders 3p: triplication with SAT solver"
    (math.CO).

The paper's central object (Section 1) is a *strong starter* in Z_n, n odd:
a partition of Z_n \\ {0} into (n-1)/2 pairs {a_i, b_i} such that the
differences +-(a_i - b_i) comprise all of Z_n \\ {0} and the sums a_i + b_i are
distinct and nonzero.  The paper's method reduces the construction of one of
these to a "Sudoku-type problem mod 3" and hands that to the SAT solver z3.

This family hands the solver a strong starter of Z_n with k of its pairs
removed and asks for them back.  Verification is the paper's own definition,
done in exact modular arithmetic.  Generation is answer-first: the starter is
assembled from a classical multiplicative construction whose strong-starter
property is a two-line proof, and the removed pairs -- the answer -- are known
before the instance exists.  No search of any kind runs in make_instance.

Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import time
from typing import Any


TRACK = "B"

# ---------------------------------------------------------------------------
# Presets.  `n` is the modulus (odd, coprime with 3 -- the paper's regime for a
# base starter -- and not a Fermat prime).  `k` is the number of removed pairs
# and IS the answer length in atoms; it stays fixed as the ladder climbs.
# `n_clustered` is how many of the k removed pairs are taken from whole orbits
# of the hidden multiplier subgroup (crowding dial).  `show_differences` prints
# the -- fully redundant -- list of missing differences.
# ---------------------------------------------------------------------------
DIFFICULTY = {
    "demo": {"n": 31, "k": 4, "n_clustered": 0, "show_differences": True},
    "easy": {"n": 1601, "k": 149, "n_clustered": 0, "show_differences": True},
    "medium": {"n": 1409, "k": 149, "n_clustered": 0, "show_differences": True},
    "hard": {"n": 1259, "k": 149, "n_clustered": 0, "show_differences": True},
}

SHIPPING_DIFFICULTY = "hard"

# Floor for escalation: k pairs cannot be removed from a starter that has fewer
# than k pairs, and the crowding formula needs some slack above 2k.
_N_FLOOR_SLACK = 60

NOTES = r"""
WHICH SECTION FIXED THE DEFINITION.  Section 1 of arXiv:2506.06461: a starter
in an abelian group G of odd order n is a partition of G* = G\{0} into
k = (n-1)/2 pairs {a_i,b_i} whose differences {+-(a_i-b_i)} comprise G*; it is
STRONG when the sums \hat S = {a_i+b_i} satisfy 0 not in \hat S and
|\hat S| = k.  verify() is that definition, executed on Z_n with exact integer
arithmetic and nothing else.

WHY THE FAMILY IS NOT THE PAPER'S SUDOKU.  The paper's contribution is
triplication: from a strong starter T of order p coprime with 3 and a key t it
builds an extension table Sigma_p (Section 3) and a constraint problem mod 3
(Section 6) whose solution yields a strong starter of order 3p
(Theorem "Solution of Sudoku yields a strong starter").  That Sudoku CANNOT be
generated answer-first: its solution is exactly what the paper hands to z3, the
existence of strong starters of order 3p > 1000 is open (Horton's conjecture,
Section 1), and the paper's own timings show z3 needing 17,961 s at p = 499
(file time_101-499.txt of the arXiv source).  A generator that had to solve the
Sudoku would be a generator that solves its own instances, which rule G
forbids.  So the family is built one level down, on the paper's base object --
a strong starter of order n coprime with 3, which is exactly what triplication
consumes as input -- posed as a completion problem, the same shape of
constraint-satisfaction problem the paper solves with z3.

WHAT PRODUCES THE CERTIFICATE (the STEP-0 question).  Not a theorem of the
paper: the planted starter is the classical multiplicative one.  Let u have odd
multiplicative order m > 1 in Z_n^*, so H = <u> does not contain -1; let A be a
union of one coset from each pair {C, -C} of H-cosets (a half system, so
A |_| -A = Z_n^*), and let c = -u^{-1}.  Then cA = -A, so {{x, cx} : x in A}
partitions Z_n^*; the differences are +-x(1-c) = (1-c)(A |_| -A) = Z_n^*, all
distinct; the sums are x(1+c), distinct and nonzero because 1+c = 1-u^{-1} is a
unit.  Two lines, no search, 2^{(n-1)/(2m)} choices of A per (n, u).  The
existence of u requires n-1 to have an odd factor > 1 (n not a Fermat prime)
and, notably, FAILS for 3 | n -- an odd-order u is 1 mod 3, so 1+c = 0 mod 3 --
which is why this construction stops exactly where Horton's conjecture starts.

WHAT MAKES IT EASY, and what is avoided.  (a) Removing too few pairs: the
candidate pairs per missing difference class scale as 2*k*f^2 with
f = 2k/(n-1), so a sparse instance is solved by unit propagation alone
(measured: n = 4003, k = 99 gives 1.4 skew-aware candidates per class and the
exact-cover attack finishes in 99 nodes; n = 2003, k = 99 gives 3.1 and it
finishes in 99 nodes; n = 1259, k = 99 gives 5.7 and 1285 nodes).  The ladder
therefore raises k and moves n DOWN, and every shipped preset sits above 11
skew-aware candidates per class.  (b) The planted starter is skew (its sum set contains exactly one of
{s,-s} for every s), which is a real signature of the construction: an attacker
who assumes it prunes the admissible sums from ~n/2 values to 2k, i.e. the
candidates per class from 44 to 17.  That attack is in the panel and it fails
at every shipped preset, but it is the reason the ladder sits at a deleted
fraction f = 2k/(n-1) of 0.19 and above rather than lower.  (c) n divisible by 3 is
impossible for the construction and is rejected by make_instance.

HOW EACH ATTACK WAS DEFEATED.  There is no plant/decoy asymmetry to exploit:
every pair the solver must find is drawn from the same multiplicative family as
the ones it is shown, and the removed pairs are a uniformly random subset.  The
candidate pair for a missing difference is not distinguishable from its
near-misses by any local statistic -- both endpoints are orphans, the sum is an
admissible sum -- which is what the outlier and greedy probes measure.  The
difficulty comes from crowding: at the shipping preset each of the 149 missing
difference classes admits about 44 candidate pairs, and (exact counts at the
sizes where enumeration terminates: 1 completion at n=31 k=4, 4 at n=211 k=20,
4 at n=997 k=49) essentially only one combination of them is a partition with
distinct sums.
""".strip()

STRUCTURAL_HINT = (
    "Every pair of the starter, given or missing, has the form {x, c*x} mod n "
    "for one and the same c."
)

PLACEBO_HINT = (
    "Keep careful track of which reduction is applied where: differences are "
    "taken up to sign while sums are not, and mixing the two is the usual "
    "source of error here."
)

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "the cyclic group Z_n, n odd and coprime with 3",
        "a partial strong starter: unordered pairs {a,b} of Z_n \\ {0}",
        "the difference multiset +-(a-b) and the sum set a+b modulo n",
    ],
    "verification_operations": [
        "exact integer arithmetic modulo n",
        "set partition check of Z_n \\ {0}",
        "difference-cover check (+-(a-b) comprise Z_n \\ {0})",
        "distinctness and nonzeroness of the pair sums",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "The whole starter is a single orbit of multiplication by one hidden "
        "unit c: every displayed pair is {x, c*x} mod n, so c is one modular "
        "division away and the missing pair with difference d is "
        "{d/(1-c), c*d/(1-c)} up to sign; a solver who does not see that must "
        "solve an exact cover of the 2k orphaned elements by pairs with "
        "prescribed differences and pairwise distinct sums."
    ),
    "hardness_basis": (
        "TRACK B.  An efficient algorithm exists and is named: read the ratio "
        "c = b*a^{-1} mod n off any one displayed pair (both orientations of "
        "that pair describe the same starter, so at most two values of c are "
        "tried), then emit x_j = +- d_j*(1-c)^{-1} for each missing difference "
        "class d_j, settling the sign by which of the two candidate pairs is "
        "still fully orphaned.  Measured at the shipping preset (n=1259, "
        "k=149): 504 exact modular operations worst case over 8 seeds, "
        "3.4e-4 s, 8/8 correct.  A second polynomial route needs no displayed "
        "pair at all: sweep the sum/difference ratio (1+c)/(1-c) over Z_n^*, "
        "a median of 2.5e4 modular multiplications (9.4e4 worst seen).  The mechanical alternative -- "
        "the constraint search this paper itself delegates to z3 -- is an "
        "exact cover of the 298 orphaned residues by 149 pairs with "
        "prescribed difference classes and pairwise distinct sums, 44 "
        "candidate pairs per class: Algorithm X with most-constrained-element "
        "ordering, forward checking and randomised restarts fails after "
        "1,429,720 nodes / 240 s at the shipping preset (and on 8/8 seeds at "
        "a 60 s budget, ~340,000 nodes each), and Dinitz-Stinson hill "
        "climbing -- the method the "
        "paper used to build its own base starters -- fails after 2,000,000 "
        "iterations on every one of 8 seeds.  The compact route is 504 "
        "operations; the mechanical one is not executable in context at all."
    ),
    "max_answer_tokens": 230,
}

NATIVE = {
    "domain": "combinatorics",
    "core": "csp_sat",
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": None,
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "k integers y_1..y_k with 1 <= y_j <= n-1, where y_j names the pair "
        "{y_j, (y_j - d_j) mod n} restoring the j-th missing difference class "
        "d_j (the classes sorted ascending, each written as its "
        "representative in [1,(n-1)/2]).  A solver who has read the statement "
        "restricts y_j to the orphaned elements whose partner at distance d_j "
        "is also orphaned and whose pair sum is still admissible."
    ),
    "bounds": {"k": 149, "n": 1259, "elements_per_slot": "n-1 naive; "
               "~24 after the constraints the statement makes explicit"},
}

_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_INT_RE = re.compile(r"-?\d+")
_LABEL_RE = re.compile(r"[A-Za-z_][A-Za-z_0-9]*\s*\*?\s*[:=]+")


# ---------------------------------------------------------------------------
# Small number theory (exact integers only)
# ---------------------------------------------------------------------------

def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def _smallest_odd_prime_factor(e: int) -> int | None:
    d = 3
    while d * d <= e:
        if e % d == 0:
            return d
        d += 2
    return e if e > 1 else None


def _odd_order_unit(n: int, rng: random.Random) -> tuple[int, int]:
    """A unit u of odd multiplicative order m > 1 (so -1 is not in <u>)."""
    e = n - 1
    s = 0
    while e % 2 == 0:
        e //= 2
        s += 1
    q = _smallest_odd_prime_factor(e)
    if q is None:
        raise ValueError("n-1 is a power of 2 (Fermat prime): no odd-order unit")
    for _ in range(2000):
        a = rng.randrange(2, n - 1)
        u = pow(a, (n - 1) // q, n)
        if u != 1:
            return u, q
    raise ValueError("failed to find a unit of order %d mod %d" % (q, n))


# ---------------------------------------------------------------------------
# The planted strong starter -- built, never searched for.
# ---------------------------------------------------------------------------

def _build_starter(n: int, rng: random.Random):
    """{{x, c x} : x in A}: a strong starter of Z_n.  See NOTES."""
    u, m = _odd_order_unit(n, rng)
    c = (-pow(u, -1, n)) % n
    seen = bytearray(n)
    orbits: list[list[int]] = []
    where: dict[int, int] = {}
    for x in range(1, n):
        if seen[x]:
            continue
        orb = []
        y = x
        while not seen[y]:
            seen[y] = 1
            orb.append(y)
            y = y * u % n
        for z in orb:
            where[z] = len(orbits)
        orbits.append(orb)
    groups: list[list[int]] = []          # one chosen orbit per +- class
    done = set()
    for i, orb in enumerate(orbits):
        if i in done:
            continue
        j = where[(-orb[0]) % n]
        if j == i:
            raise ArithmeticError("-1 fell inside <u>; u has even order")
        done.add(i)
        done.add(j)
        groups.append(orbits[i] if rng.random() < 0.5 else orbits[j])
    pairs = []
    orbit_of_pair = []
    for gi, g in enumerate(groups):
        for x in g:
            pairs.append((x, x * c % n))
            orbit_of_pair.append(gi)
    return pairs, orbit_of_pair, c, u, m


def _check_strong_starter(n: int, pairs) -> tuple[bool, str]:
    """The paper's Section-1 definition, executed."""
    if len(pairs) != (n - 1) // 2:
        return False, ("pairing has %d pairs, a starter of Z_%d needs %d"
                       % (len(pairs), n, (n - 1) // 2))
    seen = set()
    diffs = set()
    sums = set()
    for a, b in pairs:
        for z in (a, b):
            if z % n == 0:
                return False, "0 appears in a pair, but pairs partition Z_n\\{0}"
            if z in seen:
                return False, "element %d is used by more than one pair" % z
            seen.add(z)
        d = (a - b) % n
        if d == 0:
            return False, "pair {%d,%d} has difference 0" % (a, b)
        if d in diffs:
            return False, "difference +-%d is realised by two pairs" % min(d, n - d)
        diffs.add(d)
        diffs.add((-d) % n)
        s = (a + b) % n
        if s == 0:
            return False, "pair {%d,%d} has sum 0 mod %d" % (a, b, n)
        if s in sums:
            return False, "sum %d is realised by two pairs" % s
        sums.add(s)
    if len(seen) != n - 1:
        return False, "pairs do not cover Z_%d\\{0}" % n
    if len(diffs) != n - 1:
        return False, "differences do not comprise Z_%d\\{0}" % n
    return True, "ok"


# ---------------------------------------------------------------------------
# make_instance -- answer first, then the instance around it.
# ---------------------------------------------------------------------------

def make_instance(seed: int = 0, **params: Any) -> dict:
    p = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    p.update({k: v for k, v in params.items() if v is not None})
    n = int(p["n"])
    k = int(p["k"])
    n_clustered = int(p.get("n_clustered", 0))
    show_differences = bool(p.get("show_differences", True))

    if n % 2 == 0:
        raise ValueError("n must be odd")
    if n % 3 == 0:
        raise ValueError("n must be coprime with 3 (the paper's base regime, "
                         "and the multiplicative construction fails for 3|n)")
    if not _is_prime(n):
        raise ValueError("this generator ships prime moduli only")
    if not (1 <= k <= (n - 1) // 2):
        raise ValueError("k must be between 1 and (n-1)/2")

    rng = random.Random(("2506.06461", n, k, n_clustered,
                         show_differences, seed).__repr__())

    pairs, orbit_of_pair, c, u, m = _build_starter(n, rng)
    ok, why = _check_strong_starter(n, pairs)
    if not ok:                       # unreachable; the construction is a proof
        raise ArithmeticError("planted starter is not strong: " + why)

    # --- the answer: which pairs to remove, chosen before anything else ----
    idx = list(range(len(pairs)))
    rng.shuffle(idx)
    if n_clustered <= 0:
        removed = idx[:k]
    else:
        by_orbit: dict[int, list[int]] = {}
        for i in idx:
            by_orbit.setdefault(orbit_of_pair[i], []).append(i)
        groups = list(by_orbit.values())
        rng.shuffle(groups)
        removed = []
        for g in groups:
            if len(removed) >= min(n_clustered, k):
                break
            for i in g:
                if len(removed) < k:
                    removed.append(i)
        rest = [i for i in idx if i not in set(removed)]
        removed.extend(rest[:k - len(removed)])
    rem = set(removed)
    gone = [pairs[i] for i in removed]
    kept = [pairs[i] for i in range(len(pairs)) if i not in rem]

    # missing difference classes, ascending, each as its rep in [1,(n-1)/2]
    dcls = sorted(min((a - b) % n, (b - a) % n) for a, b in gone)
    # the answer: for class d_j, the endpoint y with y - (partner) = d_j
    answer = []
    by_d = {}
    for a, b in gone:
        d = min((a - b) % n, (b - a) % n)
        by_d[d] = a if (a - b) % n == d else b
    for d in dcls:
        answer.append(by_d[d])

    shown = [tuple(sorted(pr)) for pr in kept]
    rng.shuffle(shown)

    return {
        "paper": "2506.06461",
        "n": n,
        "given_pairs": [list(pr) for pr in shown],
        "show_differences": show_differences,
        "params": {"n": n, "k": k, "n_clustered": n_clustered,
                   "show_differences": show_differences},
        "answer": answer,
    }


# ---------------------------------------------------------------------------
# Derived quantities -- computed from the instance, never from inst["answer"].
# ---------------------------------------------------------------------------

_DERIVE_CACHE: dict = {}
_CAND_CACHE: dict = {}


def _derive(inst: dict):
    key = id(inst)
    hit = _DERIVE_CACHE.get(key)
    if hit is not None and hit[0] is inst:
        return hit[1]
    res = _derive_uncached(inst)
    if len(_DERIVE_CACHE) > 512:
        _DERIVE_CACHE.clear()
    _DERIVE_CACHE[key] = (inst, res)
    return res


def _derive_uncached(inst: dict):
    n = inst["n"]
    given = [tuple(pr) for pr in inst["given_pairs"]]
    used = set()
    for a, b in given:
        used.add(a)
        used.add(b)
    orphans = set(x for x in range(1, n) if x not in used)
    gdiff = set()
    for a, b in given:
        d = (a - b) % n
        gdiff.add(d)
        gdiff.add((-d) % n)
    dcls = sorted(d for d in range(1, n // 2 + 1) if d not in gdiff)
    gsum = set((a + b) % n for a, b in given)
    return n, given, orphans, dcls, gsum


def _candidates(inst: dict, skew: bool = False):
    """The pairs a solver may legally use, per missing difference class."""
    key = (id(inst), skew)
    hit = _CAND_CACHE.get(key)
    if hit is not None and hit[0] is inst:
        return hit[1]
    res = _candidates_uncached(inst, skew)
    if len(_CAND_CACHE) > 512:
        _CAND_CACHE.clear()
    _CAND_CACHE[key] = (inst, res)
    return res


def _candidates_uncached(inst: dict, skew: bool = False):
    n, given, orphans, dcls, gsum = _derive(inst)
    if skew:
        allowed = set(s for s in range(1, n)
                      if s not in gsum and (n - s) not in gsum)
    else:
        allowed = set(s for s in range(1, n) if s not in gsum)
    out = []
    for d in dcls:
        cs = []
        for y in orphans:
            z = (y - d) % n
            if z in orphans:
                s = (y + z) % n
                if s in allowed:
                    cs.append(y)
        out.append(cs)
    return dcls, out, orphans, gsum


# ---------------------------------------------------------------------------
# Statement
# ---------------------------------------------------------------------------

def render(inst: dict) -> str:
    n, given, orphans, dcls, gsum = _derive(inst)
    k = len(dcls)
    lines = []
    lines.append("STRONG STARTERS IN Z_%d." % n)
    lines.append(
        "Work in Z_%d, the integers modulo %d. A STRONG STARTER of Z_%d is a "
        "set of %d unordered pairs {a,b} of nonzero residues such that:"
        % (n, n, n, (n - 1) // 2))
    lines.append("")
    lines.append("  (S1) every nonzero residue 1,2,...,%d occurs in exactly "
                 "one pair;" % (n - 1))
    lines.append("  (S2) the %d values (a-b) mod %d and (b-a) mod %d, taken "
                 "over all pairs, are pairwise distinct -- equivalently they "
                 "are exactly the %d nonzero residues, each once;"
                 % (n - 1, n, n, n - 1))
    lines.append("  (S3) the %d values (a+b) mod %d are pairwise distinct and "
                 "none of them is 0." % ((n - 1) // 2, n))
    lines.append("")
    lines.append(
        "For a pair {a,b} call min((a-b) mod %d, (b-a) mod %d) its DIFFERENCE "
        "CLASS; by (S2) the %d pairs of a starter have the %d difference "
        "classes 1,2,...,%d, one each."
        % (n, n, (n - 1) // 2, (n - 1) // 2, (n - 1) // 2))
    lines.append("")
    lines.append("THE INSTANCE.")
    lines.append(
        "A strong starter S of Z_%d exists but %d of its %d pairs have been "
        "removed. The remaining %d pairs are:"
        % (n, k, (n - 1) // 2, len(given)))
    lines.append("")
    body = "  " + "  ".join("{%d,%d}" % (a, b)
                            for a, b in sorted(tuple(sorted(pr))
                                               for pr in given))
    # wrap at ~92 columns
    wrapped = []
    cur = " "
    for tok in body.split():
        if len(cur) + len(tok) + 1 > 92:
            wrapped.append(cur)
            cur = " "
        cur += " " + tok
    wrapped.append(cur)
    lines.extend(wrapped)
    lines.append("")
    lines.append(
        "The %d residues that do not occur above are exactly the %d elements "
        "of the %d removed pairs." % (len(orphans), len(orphans), k))
    lines.append("")
    lines.append(
        "Let d_1 < d_2 < ... < d_%d be the %d difference classes NOT realised "
        "by the pairs listed above, in increasing order." % (k, k))
    if inst.get("show_differences", True):
        lines.append("They are:")
        cur = " "
        wrapped = []
        for tok in [str(d) for d in dcls]:
            if len(cur) + len(tok) + 2 > 92:
                wrapped.append(cur)
                cur = " "
            cur += " " + tok
        wrapped.append(cur)
        lines.extend(wrapped)
    else:
        lines.append("(You have to work them out from the pairs above.)")
    lines.append("")
    lines.append("TASK.")
    lines.append(
        "Restore the %d removed pairs, that is, find %d pairs which together "
        "with the %d pairs above satisfy (S1), (S2) and (S3)."
        % (k, k, len(given)))
    lines.append(
        "The removed pair whose difference class is d_j is {y_j, "
        "(y_j - d_j) mod %d} for a unique residue y_j; report the y_j."
        % n)
    lines.append("")
    lines.append("OUTPUT.")
    lines.append(
        "Give your final answer inside <answer></answer> tags, as %d "
        "comma-separated integers y_1, y_2, ..., y_%d in that order (y_j goes "
        "with d_j, the j-th smallest missing difference class). Each y_j must "
        "satisfy 1 <= y_j <= %d." % (k, k, n - 1))
    ex = ", ".join(str(i + 1) for i in range(min(k, 4)))
    if k > 4:
        ex += ", ..."
    lines.append("Example format: <answer>%s</answer>" % ex)
    lines.append("Output nothing else inside the tags.")

    text = "\n".join(lines)
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


# ---------------------------------------------------------------------------
# Parsing and verification
# ---------------------------------------------------------------------------

def parse_answer(text: Any) -> Any:
    if not isinstance(text, str):
        return None
    blocks = _ANSWER_RE.findall(text)
    body = blocks[-1] if blocks else text
    body = body.replace("```", " ")
    body = _LABEL_RE.sub(" ", body)
    if not blocks:
        stripped = body.strip()
        if not stripped or not re.fullmatch(r"[\s,;\[\]\-0-9]+", stripped):
            return None
    nums = _INT_RE.findall(body)
    if not nums:
        return None
    try:
        return [int(t) for t in nums]
    except ValueError:
        return None


def verify(inst: dict, answer: Any) -> tuple[bool, str]:
    """The paper's definition, recomputed from scratch.  Never reads
    inst["answer"]; any valid completion is accepted."""
    n, given, orphans, dcls, gsum = _derive(inst)
    k = len(dcls)
    if not isinstance(answer, (list, tuple)):
        return False, "answer is not a list of integers"
    answer = list(answer)
    if len(answer) != k:
        return False, ("answer has %d entries, expected %d (one per missing "
                       "difference class)" % (len(answer), k))
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in answer):
        return False, "answer contains a non-integer entry"
    for j, y in enumerate(answer, 1):
        if not (1 <= y <= n - 1):
            return False, ("y%d = %d is outside [1, %d]" % (j, y, n - 1))
    new = []
    for j, (d, y) in enumerate(zip(dcls, answer), 1):
        z = (y - d) % n
        if z == 0:
            return False, ("pair %d would be {%d,0}, but 0 is not a member of "
                           "any pair" % (j, y))
        new.append((y, z))
    # (S1): the new pairs must partition exactly the orphaned residues
    seen = set()
    for j, (y, z) in enumerate(new, 1):
        for w in (y, z):
            if w not in orphans:
                return False, ("pair %d uses residue %d, which already occurs "
                               "in one of the given pairs" % (j, w))
            if w in seen:
                return False, ("residue %d is used by two of your pairs" % w)
            seen.add(w)
    if len(seen) != len(orphans):
        return False, ("your pairs cover %d of the %d missing residues"
                       % (len(seen), len(orphans)))
    ok, why = _check_strong_starter(n, list(given) + new)
    if not ok:
        return False, why
    return True, "ok"


# ---------------------------------------------------------------------------
# Space accounting
# ---------------------------------------------------------------------------

def random_candidate(inst: dict, rng: random.Random) -> list[int]:
    """Structure-aware: every constraint a solver reads off the statement for a
    single slot is already applied -- both endpoints orphaned, difference class
    correct, pair sum not already used and nonzero.  Only the joint constraints
    (disjointness across slots, distinctness of sums) are left to chance."""
    dcls, cands, orphans, gsum = _candidates(inst, skew=False)
    out = []
    for cs in cands:
        if not cs:
            out.append(rng.randrange(1, inst["n"]))
        else:
            out.append(cs[rng.randrange(len(cs))])
    return out


def search_space(inst: dict) -> int:
    dcls, cands, orphans, gsum = _candidates(inst, skew=False)
    total = 1
    for cs in cands:
        total *= max(1, len(cs))
    return total


def enumerate_all(inst: dict, cap: int = 20000,
                  time_budget: float = 30.0) -> int | None:
    """Exact number of valid completions; None if the count would exceed `cap`
    or the budget."""
    n, given, orphans, dcls, gsum = _derive(inst)
    dcls, cands, orphans, gsum = _candidates(inst, skew=False)
    k = len(dcls)
    flat = []
    by_el: dict[int, list[int]] = {}
    for i, cs in enumerate(cands):
        d = dcls[i]
        for y in cs:
            z = (y - d) % n
            idx = len(flat)
            flat.append((i, y, z, (y + z) % n))
            by_el.setdefault(y, []).append(idx)
            by_el.setdefault(z, []).append(idx)
    alive = [True] * len(flat)
    done_el = {e: False for e in orphans}
    els = sorted(orphans)
    t0 = time.time()
    state = {"cnt": 0}

    def rec():
        if state["cnt"] > cap or time.time() - t0 > time_budget:
            raise TimeoutError
        best, bl = None, None
        for e in els:
            if done_el[e]:
                continue
            opts = [i for i in by_el.get(e, ()) if alive[i]]
            if bl is None or len(opts) < len(bl):
                best, bl = e, opts
                if not opts:
                    return
        if best is None:
            state["cnt"] += 1
            return
        for idx in bl:
            i, y, z, s = flat[idx]
            trail = []
            for j in range(len(flat)):
                if not alive[j]:
                    continue
                ci, cy, cz, cs = flat[j]
                if ci == i or cy in (y, z) or cz in (y, z) or cs == s:
                    alive[j] = False
                    trail.append(j)
            done_el[y] = done_el[z] = True
            rec()
            for j in trail:
                alive[j] = True
            done_el[y] = done_el[z] = False

    try:
        rec()
    except TimeoutError:
        return None
    return state["cnt"]


def canonical_key(inst: dict) -> str:
    """Invariant under the maps that preserve the problem: reordering the pair
    list, swapping a pair's two entries, and the group automorphism
    x -> v*x (v a unit), which carries strong starters to strong starters.
    Canonical form: the lexicographic minimum, over v, of the pair
    (sorted orphan set, sorted given-sum set) scaled by v.  The minimum has 1 in
    the scaled orphan set, so v ranges over the inverses of the orphans only.
    """
    n, given, orphans, dcls, gsum = _derive(inst)
    orph = sorted(orphans)
    sums = sorted(gsum)
    best = None
    for e in orph:
        v = pow(e, -1, n)
        a = tuple(sorted((v * x) % n for x in orph))
        b = tuple(sorted((v * x) % n for x in sums))
        cand = (a, b)
        if best is None or cand < best:
            best = cand
    blob = repr((n, len(given), best))
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


def escalate(params: dict) -> dict | str | None:
    """Strictly harder parameters at FIXED answer length (k never moves).

    Two dials move together, and neither adds a single character to the answer:
      * n DOWN -- the removed pairs stay k, so the deleted fraction
        f = 2k/(n-1) rises and the number of candidate pairs per missing
        difference class, which scales as 2*k*f^2, rises with it: more
        near-misses per real pair, a bigger haystack, the same needle;
      * n_clustered UP -- the removed pairs are drawn from whole orbits of the
        hidden multiplier subgroup, which raises the candidate density another
        8-15% at fixed (n, k) by making the orphan set difference-rich.
    `show_differences` is switched off on the way (a redundant clue: the
    missing classes are computable from the given pairs), which is a third
    parameter and never changes the answer.
    """
    p = dict(params)
    n = int(p["n"])
    k = int(p["k"])
    floor = 2 * k + _N_FLOOR_SLACK
    nxt = None
    m = int(n * 0.82)
    while m > floor:
        if m % 2 and m % 3 and _is_prime(m):
            e = m - 1
            while e % 2 == 0:
                e //= 2
            if _smallest_odd_prime_factor(e):
                nxt = m
                break
        m -= 1
    if nxt is None:
        return "cap_bound"
    p["n"] = nxt
    p["n_clustered"] = min(k, int(p.get("n_clustered", 0)) + max(1, k // 2))
    p["show_differences"] = False
    return p


# ---------------------------------------------------------------------------
# The compact route -- Track B's reference algorithm.
# ---------------------------------------------------------------------------

def _reconstruct_from_c(inst: dict, c: int) -> tuple[list[int] | None, int]:
    """Given the hidden multiplier c, write down the removed pairs.

    Every pair of the starter is {x, c x}, so the pair whose difference class
    is d has x (1-c) = +- d: the reported endpoint is either d*(1-c)^{-1} or
    -c*d*(1-c)^{-1}.  Whichever of the two has both of its elements still
    orphaned (and a still-unused sum) is the right one; the handful of classes
    where both survive are settled by propagating the elements already claimed.
    Returns (answer, exact modular operations used).
    """
    n, given, orphans, dcls, gsum = _derive(inst)
    ops = 0
    inv_cost = 2 * max(1, n.bit_length())
    if (1 - c) % n == 0:
        return None, ops
    try:
        w = pow((1 - c) % n, -1, n)
    except ValueError:
        return None, ops
    ops += inv_cost + 1
    cands: list[list[int]] = []
    for d in dcls:
        y1 = (d * w) % n
        ops += 1
        y2 = (-c * y1) % n
        ops += 1
        opts = []
        for y in (y1, y2):
            z = (y - d) % n
            if y in orphans and z in orphans:
                sm = (y + z) % n
                ops += 1
                if sm != 0 and sm not in gsum:
                    opts.append(y)
        if not opts:
            return None, ops
        cands.append(opts)
    k = len(dcls)
    assign: list[Any] = [None] * k
    claimed: set[int] = set()
    changed = True
    while changed:
        changed = False
        for j, d in enumerate(dcls):
            if assign[j] is not None:
                continue
            live = [y for y in cands[j]
                    if y not in claimed and (y - d) % n not in claimed]
            if not live:
                return None, ops
            cands[j] = live
            if len(live) == 1:
                assign[j] = live[0]
                claimed.add(live[0])
                claimed.add((live[0] - d) % n)
                changed = True
    left = [j for j in range(k) if assign[j] is None]
    if left:
        # a few classes where both signs are still open: settle them by a
        # depth-limited search over at most 2 choices each
        def rec(t, claimed_local, used_sums):
            if t == len(left):
                return True
            j = left[t]
            d = dcls[j]
            for y in cands[j]:
                z = (y - d) % n
                sm = (y + z) % n
                if y in claimed_local or z in claimed_local or sm in used_sums:
                    continue
                assign[j] = y
                if rec(t + 1, claimed_local | {y, z}, used_sums | {sm}):
                    return True
                assign[j] = None
            return False
        base_sums = set(gsum)
        for j in range(k):
            if assign[j] is not None:
                y = assign[j]
                base_sums.add((y + (y - dcls[j]) % n) % n)
        if not rec(0, set(claimed), base_sums):
            return None, ops
    return list(assign), ops


def reference_solve(inst: dict) -> tuple[list[int] | None, int]:
    """The compact route.  Read the hidden multiplier off one displayed pair --
    both orientations of that pair describe the same starter, so at most two
    values of c have to be tried -- then write the answer down."""
    n, given, orphans, dcls, gsum = _derive(inst)
    inv_cost = 2 * max(1, n.bit_length())
    a, b = given[0]
    total = 0
    for c in ((b * pow(a, -1, n)) % n, (a * pow(b, -1, n)) % n):
        total += inv_cost + 1
        out, ops = _reconstruct_from_c(inst, c)
        total += ops
        if out is not None:
            return out, total
    return None, total


def multiplier_sweep(inst: dict, budget: int = 4_000_000):
    """The polynomial fallback that does not look at a displayed pair at all:
    sweep the sum/difference ratio lam = (1+c)/(1-c) over Z_n^* and keep the
    lam that carries every missing difference class onto an admissible sum."""
    n, given, orphans, dcls, gsum = _derive(inst)
    ops = 0
    allowed = set(s for s in range(1, n) if s not in gsum)
    for lam in range(2, n):
        if (lam + 1) % n == 0:
            continue
        good = True
        for d in dcls:
            s = (lam * d) % n
            ops += 1
            if s not in allowed and (n - s) not in allowed:
                good = False
                break
        if ops > budget:
            return None, ops
        if not good:
            continue
        c = ((lam - 1) * pow(lam + 1, -1, n)) % n
        out, o = _reconstruct_from_c(inst, c)
        ops += o
        if out is not None and verify(inst, out)[0]:
            return out, ops
    return None, ops


# ---------------------------------------------------------------------------
# Adversary panel
# ---------------------------------------------------------------------------

class _Restart(Exception):
    pass


def attack_exact_cover(inst: dict, skew: bool = False,
                       node_budget: int = 2_000_000, time_budget: float = 60.0,
                       restarts: int = 20, restart_nodes: int = 100_000,
                       rng: random.Random | None = None):
    """Algorithm X: branch on the most constrained uncovered element, with
    forward checking on elements, difference classes and sums, and randomised
    restarts.  `skew` additionally exploits the fact that the planted starter
    is skew (its sum set holds exactly one of {s,-s}) -- a construction-aware
    pruning that shrinks the admissible sums from ~n/2 values to 2k."""
    rng = rng or random.Random(0)
    n, given, orphans, dcls, gsum = _derive(inst)
    _, cands, _, _ = _candidates(inst, skew=skew)
    k = len(dcls)
    flat = []
    by_el: dict[int, list[int]] = {}
    by_cls: list[list[int]] = [[] for _ in range(k)]
    for i, cs in enumerate(cands):
        d = dcls[i]
        for y in cs:
            z = (y - d) % n
            idx = len(flat)
            flat.append((i, y, z, (y + z) % n))
            by_cls[i].append(idx)
            by_el.setdefault(y, []).append(idx)
            by_el.setdefault(z, []).append(idx)
    els = sorted(orphans)
    state = {"nodes": 0}
    t0 = time.time()

    def run_once():
        alive = [True] * len(flat)
        done_el = {e: False for e in els}
        done_cls = [False] * k
        sol = [None] * k
        start = state["nodes"]

        def rec():
            if (state["nodes"] > node_budget
                    or time.time() - t0 > time_budget):
                raise TimeoutError
            if state["nodes"] - start > restart_nodes:
                raise _Restart
            best, bl = None, None
            for e in els:
                if done_el[e]:
                    continue
                opts = [i for i in by_el.get(e, ()) if alive[i]]
                if bl is None or len(opts) < len(bl):
                    best, bl = e, opts
                    if not opts:
                        return False
            if best is None:
                return all(done_cls)
            for i in range(k):
                if not done_cls[i] and not any(alive[j] for j in by_cls[i]):
                    return False
            opts = bl[:]
            rng.shuffle(opts)
            for idx in opts:
                state["nodes"] += 1
                i, y, z, s = flat[idx]
                key = min(s, n - s) if skew else s
                trail = []
                for j in range(len(flat)):
                    if not alive[j]:
                        continue
                    ci, cy, cz, cs = flat[j]
                    ck = min(cs, n - cs) if skew else cs
                    if ci == i or cy in (y, z) or cz in (y, z) or ck == key:
                        alive[j] = False
                        trail.append(j)
                done_el[y] = done_el[z] = True
                done_cls[i] = True
                sol[i] = y
                if rec():
                    return True
                for j in trail:
                    alive[j] = True
                done_el[y] = done_el[z] = False
                done_cls[i] = False
            return False

        return rec(), sol

    for _ in range(restarts):
        try:
            ok, sol = run_once()
            if ok:
                return sol, state["nodes"], time.time() - t0
        except _Restart:
            continue
        except TimeoutError:
            break
    return None, state["nodes"], time.time() - t0


def attack_hill_climbing(inst: dict, iters: int = 2_000_000,
                         time_budget: float = 60.0,
                         rng: random.Random | None = None, skew: bool = False):
    """Dinitz-Stinson hill climbing -- the standard construction method for
    starters, and the one this paper used to build its own base starters.
    Repeatedly pick an unfilled difference class, place a random admissible
    pair for it, and evict whatever it collides with."""
    rng = rng or random.Random(0)
    n, given, orphans, dcls, gsum = _derive(inst)
    _, cands, _, _ = _candidates(inst, skew=skew)
    k = len(dcls)
    assign: list[Any] = [None] * k
    el_owner: dict[int, int] = {}
    sum_owner: dict[int, int] = {}
    unfilled = set(range(k))
    t0 = time.time()
    it = 0

    def evict(j):
        y, z, s = assign[j]
        assign[j] = None
        unfilled.add(j)
        el_owner.pop(y, None)
        el_owner.pop(z, None)
        sum_owner.pop(min(s, n - s) if skew else s, None)

    while unfilled and it < iters:
        it += 1
        if it % 4096 == 0 and time.time() - t0 > time_budget:
            break
        i = rng.choice(tuple(unfilled))
        cs = cands[i]
        if not cs:
            return None, it, time.time() - t0
        y = cs[rng.randrange(len(cs))]
        z = (y - dcls[i]) % n
        s = (y + z) % n
        key = min(s, n - s) if skew else s
        for e in (y, z):
            j = el_owner.get(e)
            if j is not None:
                evict(j)
        j = sum_owner.get(key)
        if j is not None:
            evict(j)
        assign[i] = (y, z, s)
        unfilled.discard(i)
        el_owner[y] = i
        el_owner[z] = i
        sum_owner[key] = i
    if unfilled:
        return None, it, time.time() - t0
    return [assign[i][0] for i in range(k)], it, time.time() - t0


def attack_greedy(inst: dict, rng: random.Random | None = None):
    """In-context greedy: walk the missing classes in increasing order and take
    the first admissible pair each time (no backtracking).  This is the route a
    solver takes when no structure has been spotted."""
    n, given, orphans, dcls, gsum = _derive(inst)
    _, cands, _, _ = _candidates(inst, skew=False)
    used_el = set()
    used_sum = set(gsum)
    out = []
    for i, d in enumerate(dcls):
        pick = None
        for y in cands[i]:
            z = (y - d) % n
            s = (y + z) % n
            if y in used_el or z in used_el or s in used_sum:
                continue
            pick = y
            break
        if pick is None:
            return None
        z = (pick - d) % n
        used_el.add(pick)
        used_el.add(z)
        used_sum.add((pick + z) % n)
        out.append(pick)
    return out


def attack_min_sum(inst: dict, rng: random.Random | None = None):
    """Outlier probe: is the planted pair the one with the extreme statistic?
    For every class take the admissible candidate with the smallest pair sum."""
    n, given, orphans, dcls, gsum = _derive(inst)
    _, cands, _, _ = _candidates(inst, skew=False)
    out = []
    for i, d in enumerate(dcls):
        if not cands[i]:
            return None
        best = min(cands[i], key=lambda y: ((y + (y - d) % n) % n, y))
        out.append(best)
    return out


def attack_constant_shift(inst: dict, rng: random.Random | None = None):
    """In-context ansatz: assume the starter is additive, {x, x+e} for a fixed
    e, which is the first structure a reader guesses.  (It cannot be right: an
    additive starter has all differences equal.)  Best-effort version: fit e to
    the given pairs, then use it."""
    n, given, orphans, dcls, gsum = _derive(inst)
    from collections import Counter
    cnt = Counter()
    for a, b in given:
        cnt[(a - b) % n] += 1
        cnt[(b - a) % n] += 1
    e = cnt.most_common(1)[0][0]
    out = []
    for d in dcls:
        y = (e + d) % n
        out.append(y if 1 <= y <= n - 1 else 1)
    return out


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def _atoms(answer) -> int:
    return len(answer)


def _serialise(answer) -> str:
    return ", ".join(str(v) for v in answer)


def selftest(quick: bool = False) -> dict:
    t_start = time.time()
    report: dict[str, Any] = {"paper": "2506.06461", "track": TRACK,
                              "shipping": SHIPPING_DIFFICULTY}
    ship = DIFFICULTY[SHIPPING_DIFFICULTY]

    # ---- G1 -------------------------------------------------------------
    ok = tot = 0
    fails = []
    for name, params in DIFFICULTY.items():
        seeds = range(6) if not quick else range(2)
        for s in seeds:
            inst = make_instance(seed=s, **params)
            good, why = verify(inst, inst["answer"])
            tot += 1
            if good:
                ok += 1
            else:
                fails.append((name, s, why))
    report["G1_planted_verifies"] = {"pass": ok == tot, "ok": ok, "total": tot,
                                     "failures": fails[:5]}

    # ---- G2 -------------------------------------------------------------
    inst = make_instance(seed=1, **ship)
    a0 = list(inst["answer"])
    reasons = {}
    corrupt = {
        "drop_one": a0[:-1],
        "empty": [],
        "swap_two": a0[1:2] + a0[0:1] + a0[2:],
        "duplicate": [a0[0]] + a0[1:-1] + [a0[0]],
        "out_of_range": [inst["n"] + 5] + a0[1:],
        "zero_entry": [0] + a0[1:],
        "non_orphan": [inst["given_pairs"][0][0]] + a0[1:],
        "shifted": [(v + 1) % inst["n"] or 1 for v in a0],
    }
    all_rejected = True
    for name, cand in corrupt.items():
        good, why = verify(inst, cand)
        if good:
            all_rejected = False
            reasons[name] = "ACCEPTED (bug)"
        else:
            reasons[name] = why
    report["G2_rejects_corruption"] = {
        "pass": all_rejected and len(set(reasons.values())) >= 5,
        "distinct_reasons": len(set(reasons.values())),
        "reasons": reasons,
    }

    # ---- G3 -------------------------------------------------------------
    reply = ("Let me work through the constraints.\n\nAfter propagating the "
             "difference classes I get the completion below.\n\n"
             "<answer>%s</answer>\n\nwhich satisfies (S1)-(S3)."
             % _serialise(a0))
    got = parse_answer(reply)
    rt = got == a0 and verify(inst, got)[0]
    report["G3_round_trip"] = {"pass": bool(rt), "recovered": got == a0,
                               "verifies": bool(got is not None
                                                and verify(inst, got)[0]),
                               "garbage_is_none":
                                   parse_answer("no answer here at all")
                                   is None}

    # ---- G4 -------------------------------------------------------------
    rng = random.Random(20260906)
    N = 200_000 if not quick else 5_000
    hits = 0
    for _ in range(N):
        cand = random_candidate(inst, rng)
        if verify(inst, cand)[0]:
            hits += 1
    ss = search_space(inst)
    inst_easy = make_instance(seed=2, **DIFFICULTY["easy"])
    N2 = 200_000 if not quick else 5_000
    hits2 = 0
    for _ in range(N2):
        if verify(inst_easy, random_candidate(inst_easy, rng))[0]:
            hits2 += 1
    report["G4_guess_resistance"] = {
        "pass": hits == 0 and hits2 == 0,
        "hits": hits, "total": N,
        "hits_easy_preset": hits2, "total_easy_preset": N2,
        "empirical_p": hits / N,
        "empirical_p_upper_95pct": 3.0 / N,
        "analytic_p_upper": 1.0 / ss if ss else None,
        "search_space": ss,
        "search_space_bits": ss.bit_length(),
    }

    # ---- G5 -------------------------------------------------------------
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    exact_demo = enumerate_all(demo, cap=100000, time_budget=30)
    small = make_instance(seed=0, **{"n": 211, "k": 20, "n_clustered": 0,
                                     "show_differences": True})
    exact_small = enumerate_all(small, cap=50000, time_budget=45)
    exact_ship = enumerate_all(inst, cap=200, time_budget=20 if quick else 60)
    tb = 20.0 if quick else 240.0
    nb = 200_000 if quick else 2_000_000
    sol_x, nodes_x, sec_x = attack_exact_cover(
        inst, skew=False, node_budget=nb, time_budget=tb, restarts=20,
        restart_nodes=100_000, rng=random.Random(4242))
    ref, ref_ops = reference_solve(inst)
    t0 = time.time()
    ref2, _ = reference_solve(inst)
    ref_sec = time.time() - t0
    ref_ok = ref is not None and verify(inst, ref)[0]
    report["G5_density_and_baseline"] = {
        "pass": bool(sol_x is None and ref_ok),
        "exact_solution_count_demo": exact_demo,
        "exact_solution_count_n211_k20": exact_small,
        "exact_solution_count_at_shipping": exact_ship,
        "density_at_shipping": hits / N,
        "density_sample_size": N,
        "density_hits": hits,
        "strongest_attack": "exact_cover_algorithm_X_mrv",
        "strongest_attack_nodes": nodes_x,
        "strongest_attack_sec": sec_x,
        "strongest_attack_solved": sol_x is not None,
        "reference_algorithm_operations": ref_ops,
        "reference_algorithm_sec": ref_sec,
        "reference_algorithm_correct": bool(ref_ok),
    }

    # ---- G6 -------------------------------------------------------------
    seeds = list(range(8 if not quick else 3))
    attacks: dict[str, dict] = {}
    per_attack_cost: dict[str, Any] = {}

    def record(name, fn):
        succ = 0
        cost = []
        for s in seeds:
            iw = make_instance(seed=100 + s, **ship)
            res = fn(iw, random.Random(7 * s + 1))
            sol = res[0] if isinstance(res, tuple) else res
            if isinstance(res, tuple) and len(res) == 3:
                cost.append((res[1], round(res[2], 2)))
            if sol is not None and verify(iw, sol)[0]:
                succ += 1
        attacks[name] = {"successes": succ, "attempts": len(seeds)}
        if cost:
            per_attack_cost[name] = cost

    nb6 = 100_000 if quick else 500_000
    tb6 = 10.0 if quick else 60.0
    record("exact_cover_algorithm_X_mrv",
           lambda i, r: attack_exact_cover(i, skew=False, node_budget=nb6,
                                           time_budget=tb6, restarts=10,
                                           restart_nodes=50_000, rng=r))
    record("exact_cover_skew_signature",
           lambda i, r: attack_exact_cover(i, skew=True, node_budget=nb6,
                                           time_budget=tb6, restarts=10,
                                           restart_nodes=50_000, rng=r))
    record("dinitz_stinson_hill_climbing",
           lambda i, r: attack_hill_climbing(i, iters=2_000_000,
                                             time_budget=tb6, rng=r))
    record("greedy_smallest_difference_first", lambda i, r: attack_greedy(i, r))
    record("outlier_min_pair_sum", lambda i, r: attack_min_sum(i, r))
    record("constant_shift_ansatz", lambda i, r: attack_constant_shift(i, r))

    ref_succ = 0
    ref_ops_all = []
    ref_secs = []
    for s in seeds:
        iw = make_instance(seed=100 + s, **ship)
        t0 = time.time()
        sol, o = reference_solve(iw)
        ref_secs.append(time.time() - t0)
        ref_ops_all.append(o)
        if sol is not None and verify(iw, sol)[0]:
            ref_succ += 1
    sw_succ = 0
    sw_ops = []
    for s in seeds[:3]:
        iw = make_instance(seed=100 + s, **ship)
        sol, o = multiplier_sweep(iw)
        sw_ops.append(o)
        if sol is not None and verify(iw, sol)[0]:
            sw_succ += 1

    report["G6_adversary_panel"] = {
        "pass": all(v["successes"] == 0 for v in attacks.values()),
        "attacks": attacks,
        "attack_cost": per_attack_cost,
        "reference_algorithm": {
            "name": "recover the hidden multiplier c from one displayed pair, "
                    "then x_j = +- d_j * (1-c)^{-1}",
            "complexity": "O(k) modular multiplications after 2 inversions",
            "wall_clock_sec": sum(ref_secs) / len(ref_secs),
            "operations": max(ref_ops_all),
            "solves": "%d/%d, as expected" % (ref_succ, len(seeds)),
        },
        "reference_algorithm_fallback": {
            "name": "sweep the sum/difference ratio (1+c)/(1-c) over Z_n^*",
            "complexity": "O(n) trials, O(k) each in the worst case",
            "operations_median": sorted(sw_ops)[len(sw_ops) // 2],
            "solves": "%d/%d" % (sw_succ, len(seeds[:3])),
        },
    }

    # ---- G7 -------------------------------------------------------------
    esc = escalate(dict(ship))
    esc_ok = False
    esc_info: Any = esc
    esc_cd = None
    if isinstance(esc, dict):
        i2 = make_instance(seed=5, **esc)
        esc_ok = verify(i2, i2["answer"])[0]
        _, cd2, _, _ = _candidates(i2, skew=False)
        esc_cd = sum(len(x) for x in cd2) / len(cd2)
        esc_info = {"params": esc, "answer_atoms": len(i2["answer"]),
                    "candidates_per_class": round(esc_cd, 2)}
    _, cd1, _, _ = _candidates(inst, skew=False)
    ship_cd = sum(len(x) for x in cd1) / len(cd1)
    ladder = []
    for nm in ("easy", "medium", "hard"):
        ii = make_instance(seed=3, **DIFFICULTY[nm])
        _, cc, _, _ = _candidates(ii, skew=False)
        _, cs, _, _ = _candidates(ii, skew=True)
        sol, nd, sc = attack_exact_cover(
            ii, skew=True, node_budget=100_000 if not quick else 20_000,
            time_budget=30.0 if not quick else 8.0, restarts=6,
            restart_nodes=25_000, rng=random.Random(9))
        ladder.append({"preset": nm, "n": DIFFICULTY[nm]["n"],
                       "k": DIFFICULTY[nm]["k"],
                       "answer_atoms": len(ii["answer"]),
                       "candidates_per_class": round(
                           sum(len(x) for x in cc) / len(cc), 2),
                       "candidates_per_class_skew_aware": round(
                           sum(len(x) for x in cs) / len(cs), 2),
                       "skew_exact_cover_solved": sol is not None,
                       "skew_exact_cover_nodes": nd})
    report["G7_scales"] = {
        "pass": bool(esc_ok and esc_cd is not None and esc_cd > ship_cd),
        "escalated": esc_info,
        "shipping_candidates_per_class": round(ship_cd, 2),
        "ladder": ladder,
    }

    # ---- G8 -------------------------------------------------------------
    inv_ok = inv_tot = 0
    carried_ok = 0
    keys = []
    for s in range(20):
        i0 = make_instance(seed=300 + s, **DIFFICULTY["easy"])
        k0 = canonical_key(i0)
        keys.append(k0)
        n0 = i0["n"]
        for v in (2, 3, pow(5, 1, n0), n0 - 1):
            if v % n0 == 0:
                continue
            i1 = {**i0,
                  "given_pairs": [[(v * a) % n0, (v * b) % n0]
                                  for a, b in i0["given_pairs"]]}
            # reorder + swap inside pairs as well
            rr = random.Random(s)
            gp = [[b, a] if rr.random() < 0.5 else [a, b]
                  for a, b in i1["given_pairs"]]
            rr.shuffle(gp)
            i1["given_pairs"] = gp
            inv_tot += 1
            if canonical_key(i1) == k0:
                inv_ok += 1
            # the transformation is real: carry the answer through it
            _, _, _, d0, _ = _derive(i0)
            _, _, orph1, d1, _ = _derive(i1)
            pairs0 = [(y, (y - d) % n0) for y, d in zip(i0["answer"], d0)]
            pairs1 = [((v * a) % n0, (v * b) % n0) for a, b in pairs0]
            byd = {}
            for a, b in pairs1:
                dd = min((a - b) % n0, (b - a) % n0)
                byd[dd] = a if (a - b) % n0 == dd else b
            ans1 = [byd[d] for d in d1] if set(byd) == set(d1) else None
            if ans1 is not None and verify(i1, ans1)[0]:
                carried_ok += 1
    report["G8_canonical_key"] = {
        "pass": bool(inv_ok == inv_tot and carried_ok == inv_tot
                     and len(set(keys)) == len(keys)),
        "invariance_ok": inv_ok, "invariance_total": inv_tot,
        "carried_answer_verifies": carried_ok,
        "distinct_keys": len(set(keys)), "distinct_of": len(keys),
    }

    # ---- G9 -------------------------------------------------------------
    ser = _serialise(a0)
    chars = len(ser)
    atoms = _atoms(a0)
    tokens = int(round(chars / 3.4))
    _, route_ops = reference_solve(inst)
    within = chars <= 2000 and atoms <= 256 and route_ops <= 1000
    report["G9_no_tool_suitability"] = {
        "pass": bool(within),
        "arms": {"bare": None, "hinted": None, "placebo": None},
        "hinted_minus_placebo": None,
        "hinted_verdict": "not run in-process (needs scripts/harden.py)",
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": atoms,
        "intended_route_operations": route_ops,
        "caps": {"chars": 2000, "elements": 256, "route_operations": 1000},
    }

    report["all_pass"] = all(
        report[g]["pass"] for g in report if g.startswith("G"))
    report["selftest_wall_clock_sec"] = time.time() - t_start
    return report


if __name__ == "__main__":
    import sys
    r = selftest(quick="--quick" in sys.argv)
    print(json.dumps(r, indent=2, default=str))
