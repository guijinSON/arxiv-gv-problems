"""Planted balanced number partitioning -- arXiv:2501.16517.

    Neekon Vafa, Vinod Vaikuntanathan,
    "Symmetric Perceptrons, Number Partitioning and Lattices" (arXiv:2501.16517).

NOTES
-----
WHICH SECTION FIXED THE DEFINITION.
  Definition 2.19 ("Number Partitioning Problem", Section 2.6 `Symmetric
  Perceptrons and Number Partitioning`): given a ~ N(0, I_m), output
  x in {-1,1}^m with |a^T x| <= kappa(m) * sqrt(m).  We ship the classical
  integer form of exactly that predicate at kappa = 0: a in Z^m, find
  x in {-1,1}^m with a^T x = 0.  The integer form is the one Karmarkar-Karp
  (cited by the paper as the best known algorithm) and Garey-Johnson (cited for
  worst-case NP-completeness) work in, and it is forced on us anyway: exact
  verification of a^T x = 0 needs exact arithmetic.

WHICH RESULT TOLD US WHAT MAKES IT EASY -- and where the window is.
  Section 1, paragraph "Number Partitioning (or Number Balancing)":

      "An application of the pigeonhole principle shows that solutions exist,
       both in the worst case and on average ..., for kappa_stat(m) = 2^{-m}."

  That single line locates the whole regime.  Rescale the paper's a_i ~ N(0,1)
  to b-bit integers, a_i ~ U{1..2^b}: the smallest achievable |a^T x| over all
  2^m sign vectors is about 2^b * kappa_stat(m) * sqrt(m) = 2^{b-m} * sqrt(m).
  The integer discrepancy is an integer, so

      b < m  ->  ~2^{m-b} perfect partitions exist by accident.  ABUNDANCE:
                 verify() accepts anything, and the family is broken.
      b > m  ->  whp NO perfect partition exists at random, so a PLANTED one is
                 essentially unique.  This is the regime we ship (measured
                 exactly by meet-in-the-middle: see selftest G5).

  The other easy end is the lattice one, and it is the reason b must not be
  pushed far above m.  A perfect partition of a is a +-1 vector in the
  orthogonal lattice a^perp, and the Lagarias-Odlyzko / Coster-Joux-LaMacchia-
  Odlyzko-Schnorr low-density subset-sum attack recovers it once the density
  m/b drops below ~0.94, i.e. once b > ~1.06 m -- IF one has an exact SVP
  oracle.  What is actually runnable is LLL, whose Hermite factor costs another
  factor delta^m, and we MEASURED where that bites (see README table): at
  b/m = 1.08 exact LLL on the CJLOSS lattice recovers the plant for m <= 40 and
  never for m >= 48 (0/8 at m = 48, 56, 64, 80, 96, 112, 128, 144); at m = 64 it
  needs b >= 2m before it works again.

  So the usable window is  m < b < (LLL boundary),  and it WIDENS with m:
  at m = 144 we sit at b = 156 while LLL would need b of order 10^2 x larger.

WHAT DEFEATED EACH ATTACK.
  * LLL/CJLOSS -- the shipping dimension.  m = 144 puts the lattice at rank 144,
    where LLL's approximation factor swamps the 2^{b/m} gap.  Measured 0/8.
  * meet-in-the-middle (Horowitz-Sahni) -- the shipping m.  2^{m/2} = 2^{72}.
  * Karmarkar-Karp differencing -- b.  KK reaches discrepancy 2^{-O(log^2 m)}
    relative to the largest element, i.e. residue ~ 2^{b - O(log^2 m)}, which is
    astronomically far from 0 whenever b ~ m.  This is the paper's own
    statistical-computational gap, and it is why b ~ m and not b ~ log^2 m.
  * local search / random restart -- the overlap gap property of Gamarnik and
    Kizildag (cited in Section 1), which says stable algorithms fail below
    kappa* = 2^{-omega(sqrt(m log m))}; we are at kappa = 0.
  * outlier statistics -- the construction.  Both sides are drawn from the same
    uniform law and the planted partition is balanced (|S| = m/2), so no
    per-element statistic separates the two blocks.  One coordinate is solved
    for rather than sampled; its conditional density is flat to within
    exp(-6/m) (4% at m = 144) and its index is uniform over all m.
"""

import hashlib
import math
import os
import random

# ---------------------------------------------------------------------------
# gvlib is not needed here: every object in this family is an integer and every
# operation in verify() is exact integer arithmetic.  Kept standard-library only.
# ---------------------------------------------------------------------------

TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "integer_lattice",
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "the weight vector a in Z^m (the paper's a ~ N(0,I_m), discretised to "
        "b-bit integers so that a^T x = 0 is exactly checkable)",
        "the sign vector x in {-1,1}^m of Definition 2.19",
        "the orthogonal lattice a^perp = {y in Z^m : a^T y = 0}, which is where "
        "the paper's lattice connection lives and where the LLL attack runs",
    ],
    "verification_operations": [
        "exact big-integer summation of m/2 weights",
        "exact big-integer equality of the two block sums",
        "cardinality check |S| = m/2 and index-range/distinctness checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "discretisation",
    "reduction": {"kind": "discretisation", "citation": "arXiv:2501.16517 abstract and Section 1: \"The number partitioning problem (NPP_kappa) corresponds to the special case of setting n=1.\" NPP is therefore the paper's own object, not an analogue. The one deviation is the entry distribution: the paper draws a ~ N(0,1)^m, while this family draws b-bit integers uniformly. That discretisation is required for exact verification (a^T x = 0 must be decidable without floating point) and it preserves the paper's statistical criterion, which is stated in terms of kappa_stat(m) = 2^-m and rescales to the perfect-partition transition at b ~ m; the shipping preset sits at b/m = 1.083, just above it.", "deviation": "Gaussian entries -> uniform b-bit integers", "preserved": "the m-vs-b phase transition and the uniqueness of the planted balanced partition"},
    "reduction_source": "paper_central",
    "intuition_type": "search pruning",
    "intuition_description": (
        "Every valid answer has the same block sum, T = (sum a_i)/2, fixed "
        "before any search begins, so the task is a fixed-target, fixed-"
        "cardinality subset sum rather than an optimisation; a solver who does "
        "not exploit that target has to sift C(m, m/2) sign patterns, and a "
        "solver who does still has no better handle than meet-in-the-middle at "
        "2^{m/2} or lattice reduction on a rank-(m+1) lattice."
    ),
    "hardness_basis": (
        "Track A.  Corollary 5.4 (`sivp-to-npp`; informal Theorem 1.3) proves "
        "NPP_kappa is hard for polynomial-time algorithms at "
        "kappa(m) = 2^{-log^{3+eps} m} assuming subexponential hardness of "
        "approximating SIVP/GapCRP/GDD (Assumption 2.14).  This family sits at "
        "kappa = 0, far inside that range, and at bit-ratio b/m = 1.083 -- just "
        "above the paper's own statistical threshold kappa_stat(m) = 2^{-m} "
        "(Section 1, 'Number Partitioning (or Number Balancing)'), where "
        "perfect partitions stop existing at random so the planted one is "
        "essentially unique (measured: exactly 2 valid answers, S and its "
        "complement, on every instance counted).  The domain-standard attack "
        "for this class -- LLL on the Coster-Joux-LaMacchia-Odlyzko-Schnorr "
        "partition lattice -- is measured to fail 0/8 at the shipping preset "
        "(m = 144, rank-144 lattice, 11 s and 3.3e7 exact integer operations "
        "per instance), and to succeed at this bit-ratio only for m <= 40.  "
        "Meet-in-the-middle (Horowitz-Sahni) costs 2^{m/2} = 2^{72} and the "
        "best known subset-sum algorithm (Becker-Coron-Joux, 2^{0.291 m}) "
        "costs 2^{41.9}."
    ),
    "max_answer_tokens": 144,
}

NATIVE = {
    "domain": "combinatorics",
    "core": "subset_sum",
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (PROBLEM_PROFILE["intuition_type"] + ": "
                  + PROBLEM_PROFILE["intuition_description"]),
    "reduction": PROBLEM_PROFILE["reduction"],
}

# --- the ladder -----------------------------------------------------------
# b = m + max(6, ceil(m/12)) throughout:  strictly above the paper's
# kappa_stat = 2^{-m} threshold (so the plant is unique) and far below the
# measured LLL boundary (so the lattice attack has nothing to grip).
DIFFICULTY = {
    "demo":   {"m": 8,   "b": 14},
    "easy":   {"m": 80,  "b": 87},
    "medium": {"m": 112, "b": 122},
    "hard":   {"m": 144, "b": 156},
}
SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A strictly increasing list of exactly m/2 distinct integers drawn from "
        "{0, 1, ..., m-1}: the 0-based indices of the weights placed in the "
        "first block.  Nothing else is admissible -- no repeats, no index "
        "outside the range, no other length."
    ),
    "bounds": {
        "n_elements": "m/2",
        "index_range": "0 .. m-1",
        "distinct": True,
        "ordered": True,
    },
}

STRUCTURAL_HINT = (
    "Both blocks must sum to the same value, so every valid answer hits one "
    "target that is fixed before any search: half of the total."
)
PLACEBO_HINT = (
    "This problem rewards keeping careful track of which index belongs to "
    "which number while you work, especially near the end."
)


# ---------------------------------------------------------------------------
# G -- generation.  The partition is sampled FIRST; the weights are then chosen
# to realise it.  make_instance never searches.
# ---------------------------------------------------------------------------

def default_b(m: int) -> int:
    """The bit-length that puts an m-item instance inside the window."""
    return m + max(6, -(-m // 12))


def make_instance(seed: int = 0, **params) -> dict:
    """Plant a balanced perfect partition, then build weights that realise it.

    Route: INVERSE GENERATION.  We draw the answer (a uniformly random balanced
    half S of the index set), then draw m-1 weights i.i.d. uniform on
    {1..2^b} and *solve* for the single remaining weight so that the two blocks
    balance exactly.  If that weight falls outside {1..2^b} the whole draw is
    discarded and retried, so the accepted law is exactly "i.i.d. uniform
    weights conditioned on S being a perfect balanced partition", with the
    solved-for coordinate uniformly placed among all m positions.
    """
    m = int(params.get("m", DIFFICULTY[SHIPPING_DIFFICULTY]["m"]))
    if m % 2:
        raise ValueError("m must be even (the partition is balanced)")
    b = int(params.get("b", default_b(m)))
    rng = random.Random(f"2501.16517|{seed}|{m}|{b}")
    U = 1 << b

    idx = list(range(m))
    rng.shuffle(idx)
    plus = set(idx[: m // 2])                 # <- the answer, sampled FIRST
    sign = [1 if i in plus else -1 for i in range(m)]

    tries = 0
    while True:
        tries += 1
        c = rng.randrange(m)                  # the solved-for coordinate
        w = [0] * m
        acc = 0
        for i in range(m):
            if i == c:
                continue
            w[i] = rng.randrange(1, U + 1)
            acc += w[i] * sign[i]
        wc = -acc * sign[c]                   # sign[c]^2 == 1
        if 1 <= wc <= U:
            w[c] = wc
            break

    # publish the weights in sorted order; the answer is re-expressed as the
    # indices of the planted block in that order.
    order = sorted(range(m), key=lambda i: (w[i], i))
    a = [w[i] for i in order]
    answer = sorted(pos for pos, i in enumerate(order) if sign[i] == 1)

    assert sum(a[i] for i in answer) * 2 == sum(a)
    return {
        "id": "2501.16517",
        "m": m,
        "b": b,
        "a": a,
        "half_total": sum(a) // 2,
        "answer": answer,
        "_rejections": tries - 1,
    }


# ---------------------------------------------------------------------------
# the output contract
# ---------------------------------------------------------------------------

def render(inst) -> str:
    m, a = inst["m"], inst["a"]
    k = m // 2
    lines = []
    lines.append(
        "NUMBER PARTITIONING.\n"
        f"\nYou are given {m} positive integers a[0], a[1], ..., a[{m - 1}] "
        "(0-based indexing).\n"
        f"They are listed below, one per line, in nondecreasing order.\n"
    )
    width = len(str(m - 1))
    for i, v in enumerate(a):
        lines.append(f"a[{str(i).rjust(width)}] = {v}")
    lines.append(
        "\nTASK.  Find a set S of indices with BOTH of the following "
        "properties:\n"
        f"  (1)  S contains exactly {k} indices, all distinct, each in the "
        f"range 0 .. {m - 1};\n"
        "  (2)  the numbers whose index is in S have exactly the same total as "
        "the numbers\n"
        "       whose index is not in S:\n"
        "\n           sum of a[i] over i in S   =   sum of a[i] over i not in "
        "S.\n"
        "\nAt least one such S exists.  The equality in (2) is exact integer "
        "equality --\n"
        "not approximate, not up to rounding.  Any S with both properties is "
        "accepted\n"
        "(in particular the complement of a valid S is also valid).\n"
    )
    hint = os.environ.get("GV_HINT_MODE")
    if hint == "structural":
        lines.append("\n" + STRUCTURAL_HINT + "\n")
    elif hint == "placebo":
        lines.append("\n" + PLACEBO_HINT + "\n")
    lines.append(
        "\nOUTPUT.\n"
        f"Give your final answer inside <answer></answer> tags, as the {k} "
        "indices of S,\n"
        "in increasing order, separated by commas.\n"
        "Example (for a 6-number instance needing 3 indices): "
        "<answer>0, 2, 5</answer>\n"
        "Output nothing else inside the tags."
    )
    return "\n".join(lines)


def parse_answer(text):
    """Pull a list of indices out of raw model output.  None on garbage."""
    if text is None:
        return None
    if isinstance(text, (list, tuple)):
        try:
            return sorted(int(v) for v in text)
        except (TypeError, ValueError):
            return None
    if not isinstance(text, str):
        return None
    s = text
    lo = s.rfind("<answer>")
    if lo != -1:
        hi = s.find("</answer>", lo)
        s = s[lo + 8: hi if hi != -1 else len(s)]
    else:
        # tolerate a fenced block or a bare trailing list
        if "```" in s:
            parts = s.split("```")
            if len(parts) >= 3:
                s = parts[-2]
        s = s.strip().splitlines()[-1] if s.strip() else ""
    s = s.replace("`", " ").replace("[", " ").replace("]", " ")
    s = s.replace("{", " ").replace("}", " ").replace(",", " ")
    s = s.replace(";", " ").replace("\n", " ").replace("\t", " ")
    out = []
    for tok in s.split():
        tok = tok.strip(".")
        if not tok:
            continue
        try:
            out.append(int(tok))
        except ValueError:
            return None
    if not out:
        return None
    return sorted(out)


def verify(inst, answer):
    """(True,'ok') or (False, reason).  Never reads inst['answer']."""
    m, a = inst["m"], inst["a"]
    k = m // 2
    if answer is None:
        return False, "no_answer"
    if isinstance(answer, (str, bytes, dict, set)):
        return False, "answer_not_a_list"
    if not isinstance(answer, (list, tuple)):
        return False, "answer_not_a_list"
    if len(answer) == 0:
        return False, "empty_answer"
    for v in answer:
        if isinstance(v, bool) or not isinstance(v, int):
            return False, "non_integer_entry"
    if len(answer) < k:
        return False, f"too_few_indices ({len(answer)} < {k})"
    if len(answer) > k:
        return False, f"too_many_indices ({len(answer)} > {k})"
    if any(v < 0 for v in answer):
        return False, "index_negative"
    if any(v >= m for v in answer):
        return False, "index_out_of_range_high"
    s = set(answer)
    if len(s) != len(answer):
        return False, "duplicate_index"
    lhs = 0
    for i in s:
        lhs += a[i]
    rhs = 0
    for i in range(m):
        if i not in s:
            rhs += a[i]
    if lhs != rhs:
        return False, f"sums_differ (difference {lhs - rhs})"
    return True, "ok"


# ---------------------------------------------------------------------------
# counting / candidate sampling
# ---------------------------------------------------------------------------

def random_candidate(inst, rng):
    """A uniformly random candidate that already satisfies everything a solver
    reads off the statement: exactly m/2 distinct indices in range."""
    m = inst["m"]
    return sorted(rng.sample(range(m), m // 2))


def search_space(inst):
    m = inst["m"]
    return math.comb(m, m // 2)


def enumerate_all(inst, cap_half=1 << 21):
    """EXACT number of valid answers, by meet-in-the-middle.  None if too big.

    Counts sets S, so the planted block and its complement count as two.
    """
    m, a = inst["m"], inst["a"]
    h = m // 2
    if (1 << h) > cap_half:
        return None
    left = {}
    A, B = a[:h], a[h:]
    for mask in range(1 << h):
        s = 0
        pc = 0
        for i in range(h):
            if (mask >> i) & 1:
                s += A[i]
                pc += 1
            else:
                s -= A[i]
        key = (pc, s)
        left[key] = left.get(key, 0) + 1
    tot = 0
    for mask in range(1 << h):
        s = 0
        pc = 0
        for i in range(h):
            if (mask >> i) & 1:
                s += B[i]
                pc += 1
            else:
                s -= B[i]
        tot += left.get((m // 2 - pc, -s), 0)
    return tot


def expected_valid_count(m: int, b: int) -> float:
    """Calibrated estimate of the number of valid answers (sets S).

    A uniformly random balanced sign vector has a^T x with mean 0 and standard
    deviation ~ 2^b sqrt(m/12); a^T x always has the parity of sum(a) (even
    here), so P(a^T x = 0) ~ 2 / (sqrt(2 pi) 2^b sqrt(m/12)).  Multiplying by
    C(m, m/2) ~ 2^m sqrt(2/(pi m)) gives

        E[# balanced solutions] ~ 2^{m-b} * 2.205 / m .

    Calibrated against exact meet-in-the-middle counts for m = 16..40: see the
    table in the README.  The two planted answers (S and its complement) are
    always present, so the estimate returned is 2 + that.
    """
    sd = (2.0 ** b) * math.sqrt(m / 12.0)
    log_choose = m * math.log(2) - 0.5 * math.log(math.pi * m / 2)
    log_p = math.log(2.0) - 0.5 * math.log(2 * math.pi) - math.log(sd)
    return 2.0 + math.exp(log_choose + log_p)


def canonical_key(inst) -> str:
    """Invariant under (i) permutation of the published weights and (ii) the
    affine maps a -> lambda*a + c (lambda > 0 integer, c integer), which
    preserve the valid-answer set exactly because every answer is balanced:
    sum_i (lambda a_i + c) x_i = lambda sum_i a_i x_i for sum_i x_i = 0.
    """
    a = sorted(inst["a"])
    lo = a[0]
    diffs = [v - lo for v in a]
    g = 0
    for d in diffs:
        g = math.gcd(g, d)
    if g:
        diffs = [d // g for d in diffs]
    payload = f"{inst['m']}|" + ",".join(str(d) for d in diffs)
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def escalate(params):
    """Harder parameters.  Two axes move together, by design:

      m -- the ground set, so the haystack C(m, m/2) and the rank of the
           lattice the domain attack has to reduce both grow;
      b -- the weight bit-length, which must track m to keep the planted
           partition unique (the paper's kappa_stat = 2^{-m} line).

    The ANSWER stays one bit per item -- m/2 indices -- so the certificate
    never leaves the cap: m = 256 is 128 atoms and 466 characters.
    """
    m = int(params.get("m", DIFFICULTY[SHIPPING_DIFFICULTY]["m"]))
    if m >= 256:                  # 256 items == 256 answer bits == the cap
        return "cap_bound"
    nxt = min(m + 32, 256)
    return {"m": nxt, "b": default_b(nxt)}


# ===========================================================================
# H -- the adversary panel.  Everything below is an ATTACK, not part of the
# family.  All exact integer arithmetic; no floats anywhere that matter.
# ===========================================================================

# --- (a) the domain-standard attack: LLL on the CJLOSS partition lattice ----

_gram_det = []


def _integral_lll(basis, delta_num=99, delta_den=100, op_budget=None):
    """Exact all-integer LLL (de Weger / Cohen, Algorithm 2.6.7).

    No floats, no Fractions: the Gram-Schmidt data is carried as the integer
    determinants d[i] and the integers lambda[i][j] = d[j] * mu[i][j].
    Returns (reduced_basis, operations, completed).  The Gram determinant of
    the lattice (an invariant of the basis) is stashed on the returned list as
    the attribute-free convention below: it is d[n] after initialisation.
    """
    b = [list(map(int, row)) for row in basis]
    n = len(b)
    _gram_det.clear()
    if n == 0:
        return b, 0, True
    ops = [0]

    def dot(u, v):
        ops[0] += len(u)
        return sum(x * y for x, y in zip(u, v))

    d = [0] * (n + 1)
    d[0] = 1
    lam = [[0] * (n + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, i + 1):
            u = dot(b[i - 1], b[j - 1])
            for kk in range(1, j):
                u = (d[kk] * u - lam[i][kk] * lam[j][kk]) // d[kk - 1]
                ops[0] += 3
            if j < i:
                lam[i][j] = u
            else:
                d[i] = u
        if d[i] == 0:
            raise ValueError("lattice basis is not full rank")
    _gram_det.append(d[n])

    def red(k, l):
        if 2 * abs(lam[k][l]) <= d[l]:
            return
        q = (2 * lam[k][l] + d[l]) // (2 * d[l])
        bk, bl = b[k - 1], b[l - 1]
        for t in range(len(bk)):
            bk[t] -= q * bl[t]
        ops[0] += len(bk)
        lam[k][l] -= q * d[l]
        for i in range(1, l):
            lam[k][i] -= q * lam[l][i]
        ops[0] += l

    k = 2
    while k <= n:
        red(k, k - 1)
        if (delta_den * (d[k] * d[k - 2] + lam[k][k - 1] ** 2)
                >= delta_num * d[k - 1] ** 2):
            for l in range(k - 2, 0, -1):
                red(k, l)
            k += 1
        else:
            b[k - 1], b[k - 2] = b[k - 2], b[k - 1]
            for j in range(1, k - 1):
                lam[k][j], lam[k - 1][j] = lam[k - 1][j], lam[k][j]
            lm = lam[k][k - 1]
            B = (d[k - 2] * d[k] + lm * lm) // d[k - 1]
            for i in range(k + 1, n + 1):
                t = lam[i][k]
                lam[i][k] = (d[k] * lam[i][k - 1] - lm * t) // d[k - 1]
                lam[i][k - 1] = (B * t + lm * lam[i][k]) // d[k]
                ops[0] += 8
            d[k - 1] = B
            ops[0] += 6
            k = max(2, k - 1)
        ops[0] += 6
        if op_budget is not None and ops[0] > op_budget:
            return b, ops[0], False
    return b, ops[0], True


def _cjloss_basis(a, perm=None):
    """The Coster-Joux-LaMacchia-Odlyzko-Schnorr lattice for BALANCED perfect
    partitioning, in doubled-integer form.  Rank m inside Z^{m+2}.

        b_i  =  (2 e_i | 2 N a_i | 2 N)          i = 0 .. m-2
        b_*  =  (1 ... 1 | 2 N T | N m)          T = (sum a)/2

    A 0/1 indicator x of a valid block gives sum_i x_i b_i - b_* = (2x - 1, 0, 0),
    a +-1 vector of norm sqrt(m): the CJLOSS half-integer trick, which is what
    buys the density threshold 0.9408 instead of Lagarias-Odlyzko's 0.6463.
    Row b_{m-1} is deliberately omitted -- because T = (sum a)/2 exactly, it is
    the rational combination 2 b_* - sum_{i<m-1} b_i and including it would make
    the basis rank-deficient (and add the junk vector (0..0,2,0,0) if patched
    with an extra coordinate).  The Z-span is unchanged.
    N = 2m forces the two heavy coordinates of any vector shorter than N to
    vanish, i.e. forces both the sum and the cardinality constraint.
    """
    m = len(a)
    T = sum(a) // 2
    N = 2 * m
    order = perm if perm is not None else list(range(m))
    rows = []
    for i in order[:m - 1]:
        r = [0] * (m + 2)
        r[i] = 2
        r[m] = 2 * N * a[i]
        r[m + 1] = 2 * N
        rows.append(r)
    rows.append([1] * m + [2 * N * T, N * m])
    return rows


def usvp_gap(inst):
    """The unique-SVP gap of the CJLOSS lattice at these parameters.

    lambda_1 of a random lattice of rank r and determinant D is, by the Gaussian
    heuristic, sqrt(r/(2 pi e)) D^{1/r}.  The planted vector has norm sqrt(m).  Their ratio is the gap ANY lattice-reduction algorithm must
    beat: recovering a unique shortest vector needs a root-Hermite factor
    delta_0 with delta_0^r <= gap.  Returns (gap, required_delta0, log2_det).
    """
    a, m = inst["a"], inst["m"]
    rows = _cjloss_basis(a)
    # det Gram, computed exactly by the same integral Gram-Schmidt LLL uses
    _integral_lll(rows, op_budget=1)
    det_gram = _gram_det[0]
    r = m
    log2_D = 0.5 * (math.log(det_gram, 2))
    log2_lam1 = 0.5 * math.log(r / (2 * math.pi * math.e), 2) + log2_D / r
    log2_target = 0.5 * math.log(r, 2)
    gap = 2.0 ** (log2_lam1 - log2_target)
    delta0 = 2.0 ** ((log2_lam1 - log2_target) / r) if gap > 0 else None
    return gap, delta0, log2_D


def attack_lattice_lll(inst, rng=None, restarts=1, op_budget=None):
    """LLL on the CJLOSS partition lattice.  Returns (answer|None, stats)."""
    a, m = inst["a"], inst["m"]
    ops_total = 0
    for t in range(restarts):
        perm = list(range(m))
        if t:
            rng.shuffle(perm)
        rows = _cjloss_basis(a, perm)
        red, ops, done = _integral_lll(rows, op_budget=op_budget)
        ops_total += ops
        det_gram = _gram_det[0] if _gram_det else None
        shortest2 = min(sum(v * v for v in r2) for r2 in red)
        for r in red:
            if r[m] or r[m + 1]:
                continue
            head = r[:m]
            for sgn in (1, -1):
                v = [sgn * t2 for t2 in head]
                if all(t2 in (1, -1) for t2 in v):
                    S = sorted(i for i in range(m) if v[i] == 1)
                    if len(S) == m // 2 and \
                            sum(a[i] for i in S) * 2 == sum(a):
                        return S, _lll_stats(ops_total, m, det_gram, shortest2)
    return None, _lll_stats(ops_total, m, det_gram, shortest2)


def _lll_stats(ops, m, det_gram, shortest2):
    r = m
    st = {"ops": ops, "rank": r}
    if det_gram:
        log2D = 0.5 * math.log(det_gram, 2)
        log2_b1 = 0.5 * math.log(shortest2, 2)
        log2_target = 0.5 * math.log(r, 2)
        st["log2_lattice_determinant"] = log2D
        st["lll_shortest_over_planted_norm"] = 2.0 ** (log2_b1 - log2_target)
        st["lll_achieved_root_hermite_delta0"] = \
            2.0 ** ((log2_b1 - log2D / r) / r)
        # bit-length b at which LLL WOULD find the plant at this m, from the
        # measured delta0:  need  log2 D / r - 0.5 log2(2 pi e) >= r log2 delta0
        d0 = math.log(st["lll_achieved_root_hermite_delta0"], 2)
        need_log2D = r * (r * d0 + 0.5 * math.log(2 * math.pi * math.e, 2))
        st["b_at_which_lll_would_succeed"] = (need_log2D - 10.0) / 2.0
    return st


# --- (b) meet-in-the-middle / Horowitz-Sahni --------------------------------

def attack_meet_in_the_middle(inst, rng=None, half_budget=1 << 15):
    """Horowitz-Sahni: enumerate signed sums of each half and match.

    Exact and complete when 2^{m/2} <= half_budget; otherwise it enumerates
    half_budget masks per side (a random sub-box) and reports what fraction of
    the 2^{m/2} x 2^{m/2} product it covered.
    """
    a, m = inst["a"], inst["m"]
    h = m // 2
    full = (1 << h) <= half_budget
    n_masks = (1 << h) if full else half_budget
    A, B = a[:h], a[h:]

    def block(vals, masks):
        out = {}
        for mask in masks:
            s = 0
            pc = 0
            for i in range(h):
                if (mask >> i) & 1:
                    s += vals[i]
                    pc += 1
                else:
                    s -= vals[i]
            out.setdefault((pc, s), mask)
        return out

    if full:
        masksA = range(1 << h)
        masksB = range(1 << h)
    else:
        rng = rng or random.Random(0)
        masksA = [rng.randrange(1 << h) for _ in range(n_masks)]
        masksB = [rng.randrange(1 << h) for _ in range(n_masks)]
    left = block(A, masksA)
    for mask in masksB:
        s = 0
        pc = 0
        for i in range(h):
            if (mask >> i) & 1:
                s += B[i]
                pc += 1
            else:
                s -= B[i]
        hit = left.get((m // 2 - pc, -s))
        if hit is not None:
            S = sorted([i for i in range(h) if (hit >> i) & 1]
                       + [h + i for i in range(h) if (mask >> i) & 1])
            return S, {"ops": 2 * n_masks * h, "complete": full,
                       "coverage": (n_masks / float(1 << h)) ** 2}
    return None, {"ops": 2 * n_masks * h, "complete": full,
                  "coverage": (n_masks / float(1 << h)) ** 2 if h < 200 else 0.0}


# --- (c) Karmarkar-Karp differencing (the paper's own algorithm) ------------

def attack_karmarkar_karp(inst, rng=None):
    """Largest-differencing method, with the block reconstruction.

    Returns (answer|None, stats) -- stats carry the achieved residue, which is
    the number the paper's kappa_comp(m) = 2^{-O(log^2 m)} is about.
    """
    import heapq
    a, m = inst["a"], inst["m"]
    # heap of (-value, node) where node is a pair-tree of index sets
    heap = [(-a[i], i) for i in range(m)]
    heapq.heapify(heap)
    tree = {}
    nxt = m
    while len(heap) > 1:
        v1, n1 = heapq.heappop(heap)
        v2, n2 = heapq.heappop(heap)
        diff = (-v1) - (-v2)
        tree[nxt] = (n1, n2)
        heapq.heappush(heap, (-diff, nxt))
        nxt += 1
    residue = -heap[0][0]
    root = heap[0][1]
    # colour the tree: children of a differenced node go to opposite blocks
    colour = {root: 1}
    stack = [root]
    while stack:
        node = stack.pop()
        if node in tree:
            n1, n2 = tree[node]
            colour[n1] = colour[node]
            colour[n2] = -colour[node]
            stack.extend((n1, n2))
    S = sorted(i for i in range(m) if colour.get(i, 1) == 1)
    ok = (residue == 0 and len(S) == m // 2
          and sum(a[i] for i in S) * 2 == sum(a))
    return (S if ok else None), {"residue": residue,
                                 "residue_bits": residue.bit_length(),
                                 "block_size": len(S)}


# --- (d) random restart + local search --------------------------------------

def attack_local_search(inst, rng, restarts=32, sweeps=30):
    """Random balanced start, then best-improvement 1-swaps on |discrepancy|."""
    a, m = inst["a"], inst["m"]
    k = m // 2
    best = None
    steps = 0
    for _ in range(restarts):
        S = set(rng.sample(range(m), k))
        out = [i for i in range(m) if i not in S]
        S = list(S)
        disc = sum(a[i] for i in S) - sum(a[i] for i in out)
        for _ in range(sweeps):
            improved = False
            for ii in range(k):
                for jj in range(k):
                    steps += 1
                    nd = disc - 2 * a[S[ii]] + 2 * a[out[jj]]
                    if abs(nd) < abs(disc):
                        S[ii], out[jj] = out[jj], S[ii]
                        disc = nd
                        improved = True
                        break
                if improved:
                    break
            if not improved:
                break
            if disc == 0:
                break
        if best is None or abs(disc) < best:
            best = abs(disc)
        if disc == 0:
            return sorted(S), {"steps": steps, "best_abs_discrepancy": 0}
    return None, {"steps": steps, "best_abs_discrepancy": best}


# --- (e) per-element outlier / greedy statistics ----------------------------

_STATS = ("largest_half", "smallest_half", "alternate_by_rank", "odd_even",
          "mod3_bucket", "greedy_pair_up", "top_bit_set", "prefix_half")


def attack_outlier_statistics(inst, rng=None):
    """Can the planted block be read off a per-element statistic?"""
    a, m = inst["a"], inst["m"]
    k = m // 2
    order = sorted(range(m), key=lambda i: a[i])
    cands = {
        "largest_half": sorted(order[k:]),
        "smallest_half": sorted(order[:k]),
        "alternate_by_rank": sorted(order[0::2]),
        "odd_even": sorted(sorted(range(m), key=lambda i: (a[i] & 1, a[i]))[:k]),
        "mod3_bucket": sorted(sorted(range(m), key=lambda i: (a[i] % 3, i))[:k]),
        "greedy_pair_up": sorted(order[0::2]),
        "top_bit_set": sorted(sorted(range(m),
                                     key=lambda i: (-(a[i].bit_length()), i))[:k]),
        "prefix_half": list(range(k)),
    }
    for name, S in cands.items():
        if len(set(S)) == k and sum(a[i] for i in S) * 2 == sum(a):
            return S, {"which": name}
    return None, {"which": None}


ATTACKS = {
    "lattice_lll_cjloss": attack_lattice_lll,
    "meet_in_the_middle_horowitz_sahni": attack_meet_in_the_middle,
    "karmarkar_karp_differencing": attack_karmarkar_karp,
    "random_restart_local_search": attack_local_search,
    "outlier_statistics": attack_outlier_statistics,
}


# ===========================================================================
# selftest
# ===========================================================================

def _answer_text(ans):
    return ", ".join(str(v) for v in ans)


def selftest(verbose=False, g6_seeds=8, g4_trials=200000):
    import time
    rep = {}
    ship = DIFFICULTY[SHIPPING_DIFFICULTY]
    m, b = ship["m"], ship["b"]

    def say(*x):
        if verbose:
            print(*x, flush=True)

    # ---- G1 -----------------------------------------------------------
    ok = 0
    tot = 0
    for name, p in DIFFICULTY.items():
        for sd in range(8):
            inst = make_instance(seed=1000 + sd, **p)
            tot += 1
            good, why = verify(inst, inst["answer"])
            if good:
                ok += 1
            else:
                say("G1 FAIL", name, sd, why)
    rep["G1_planted_verifies"] = {"ok": ok, "total": tot, "pass": ok == tot}
    say("G1", ok, "/", tot)

    # ---- G2 -----------------------------------------------------------
    reasons = set()
    all_rejected = True
    for sd in range(6):
        inst = make_instance(seed=50 + sd, **ship)
        A = list(inst["answer"])
        k = len(A)
        bad = [
            None,
            "not a list at all",
            [],
            A[:-1],
            A + [A[0]],
            [A[0]] * k,
            [-1] + A[1:],
            [m] + A[1:],
            [float(A[0])] + A[1:],
            sorted([v for v in A if v != A[0]]
                   + [next(i for i in range(m) if i not in set(A))]),
        ]
        for cand in bad:
            good, why = verify(inst, cand)
            if good:
                all_rejected = False
                say("G2 accepted a corruption:", cand)
            else:
                reasons.add(why.split(" (")[0])
    rep["G2_rejects_corruption"] = {"distinct_reasons": len(reasons),
                                    "reasons": sorted(reasons),
                                    "pass": all_rejected and len(reasons) >= 8}
    say("G2 reasons", sorted(reasons))

    # ---- G3 -----------------------------------------------------------
    inst = make_instance(seed=7, **ship)
    A = inst["answer"]
    prose = (
        "Let me think about this.  The total is even, so each block must sum "
        "to half of it.\n"
        "After a fair amount of searching I believe the following works.\n\n"
        "```\nnot the answer\n```\n\n"
        f"So the answer is:\n\n<answer>{_answer_text(A)}</answer>\n\n"
        "I hope that is right."
    )
    rt = parse_answer(prose)
    g3a = (rt == A)
    g3b = (parse_answer("I could not solve it.") is None)
    g3c = (parse_answer("<answer>alpha beta</answer>") is None)
    g3d = (parse_answer(f"<answer>[{_answer_text(A)}]</answer>") == A)
    rep["G3_round_trip"] = {"pass": bool(g3a and g3b and g3c and g3d),
                            "round_trip": g3a, "garbage_is_none": g3b and g3c,
                            "bracket_form": g3d}
    say("G3", rep["G3_round_trip"])

    # ---- G4 -----------------------------------------------------------
    rng = random.Random(4242)
    inst = make_instance(seed=11, **ship)
    hits = 0
    for _ in range(g4_trials):
        cand = random_candidate(inst, rng)
        if sum(inst["a"][i] for i in cand) * 2 == sum(inst["a"]):
            hits += 1
    space = search_space(inst)
    analytic = expected_valid_count(m, b) / space
    rep["G4_guess_resistance"] = {
        "hits": hits, "trials": g4_trials,
        "search_space": space,
        "analytic_p": analytic,
        "pass": hits == 0 and analytic < 1e-6,
    }
    say("G4", hits, "/", g4_trials, "p =", analytic)

    # ---- G5 -----------------------------------------------------------
    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_exact = enumerate_all(demo)
    calib = []
    for mm in (16, 20, 24, 28):
        for bb in (mm - 5, mm, default_b(mm)):
            c = [enumerate_all(make_instance(seed=q, m=mm, b=bb))
                 for q in range(3)]
            calib.append({"m": mm, "b": bb, "b_over_m": round(bb / mm, 3),
                          "exact_counts": c,
                          "calibrated_estimate": expected_valid_count(mm, bb)})
    inst = make_instance(seed=21, **ship)
    t0 = time.time()
    sol, st = attack_lattice_lll(inst)
    lll_sec = time.time() - t0
    gap, delta0, log2D = usvp_gap(inst)
    mitm_ops = 2.0 ** (m / 2) * (m / 2)
    bcj_ops = 2.0 ** (0.291 * m)
    rep["G5_density_and_cost"] = {
        "shipping_m": m, "shipping_b": b,
        "shipping_valid_answer_count": expected_valid_count(m, b),
        "shipping_valid_count_is_estimate": True,
        "shipping_analytic_density": expected_valid_count(m, b) / space,
        "exact_valid_count_demo": demo_exact,
        "exact_count_calibration": calib,
        "strongest_attack": "LLL on the CJLOSS partition lattice (rank m)",
        "baseline_wall_clock_sec": lll_sec,
        "baseline_operations": st["ops"],
        "baseline_solved": sol is not None,
        "usvp_gap_lambda1GH_over_target": gap,
        "usvp_required_root_hermite_delta0": delta0,
        "cjloss_lattice_log2_determinant": log2D,
        "cjloss_lattice_rank": m,
        "meet_in_the_middle_ops_shipping": mitm_ops,
        "best_known_subset_sum_ops_shipping_bcj": bcj_ops,
        "bruteforce_ops_shipping": float(space),
        "pass": bool(sol is None and demo_exact is not None
                     and expected_valid_count(m, b) < 3.0),
    }
    say("G5", lll_sec, "s  demo_count", demo_exact)

    # ---- G6 -----------------------------------------------------------
    attacks = {}
    rng = random.Random(6060)
    for name, fn in ATTACKS.items():
        succ = 0
        extra = []
        for sd in range(g6_seeds):
            inst = make_instance(seed=6000 + sd, **ship)
            if name == "lattice_lll_cjloss":
                got, st = fn(inst, rng, restarts=1)
            else:
                got, st = fn(inst, rng)
            if got is not None and verify(inst, got)[0]:
                succ += 1
            extra.append(st)
        attacks[name] = {"successes": succ, "attempts": g6_seeds,
                         "detail": extra[0]}
    # sanity: the attacks are not no-ops.  MITM and LLL must SOLVE small cases.
    tiny = make_instance(seed=5, m=16, b=default_b(16))
    mitm_ok = attack_meet_in_the_middle(tiny)[0] is not None
    lll_ok = attack_lattice_lll(tiny, random.Random(1))[0] is not None
    # outlier diagnostics: is the planted block visible per element?
    hitcount = {s: 0 for s in ("in_top_half", "in_bottom_half", "odd_valued")}
    trials = 24
    for sd in range(trials):
        inst = make_instance(seed=8000 + sd, **ship)
        A = set(inst["answer"])
        a = inst["a"]
        order = sorted(range(m), key=lambda i: a[i])
        hitcount["in_top_half"] += len(A & set(order[m // 2:]))
        hitcount["in_bottom_half"] += len(A & set(order[:m // 2]))
        hitcount["odd_valued"] += sum(1 for i in A if a[i] & 1)
    rep["G6_adversary_panel"] = {
        "attacks": attacks,
        "pass": all(v["successes"] == 0 for v in attacks.values()),
        "attack_sanity_on_small_instances": {
            "meet_in_the_middle_solves_m16": mitm_ok,
            "lll_solves_m16": lll_ok,
        },
        "outlier_diagnostics": {
            "trials": trials,
            "chance_baseline_per_trial": m / 4.0,
            "mean_hits": {k2: v / trials for k2, v in hitcount.items()},
        },
    }
    say("G6", {k2: v["successes"] for k2, v in attacks.items()})

    # ---- G7 -----------------------------------------------------------
    esc = escalate(dict(ship))
    ladder = []
    p = dict(ship)
    for _ in range(4):
        nxt = escalate(p)
        if not isinstance(nxt, dict):
            ladder.append({"escalate": nxt})
            break
        i2 = make_instance(seed=1, **nxt)
        good, _ = verify(i2, i2["answer"])
        ladder.append({"m": nxt["m"], "b": nxt["b"],
                       "answer_atoms": len(i2["answer"]),
                       "answer_chars": len(_answer_text(i2["answer"])),
                       "answer_bits_equivalent": nxt["m"],
                       "verifies": good})
        p = nxt
    i2 = make_instance(seed=1, **esc) if isinstance(esc, dict) else None
    rep["G7_scales"] = {
        "escalate": esc,
        "moved_params": ["m", "b"],
        "escalated_builds_and_verifies": bool(i2 and verify(i2, i2["answer"])[0]),
        "escalated_answer_chars": len(_answer_text(i2["answer"])) if i2 else None,
        "ladder": ladder,
        "pass": bool(i2 and verify(i2, i2["answer"])[0]
                     and esc["m"] > m and esc["b"] > b),
    }
    say("G7", rep["G7_scales"]["escalate"])

    # ---- G8 -----------------------------------------------------------
    rng = random.Random(88)
    inv = 0
    inv_tot = 0
    carried = 0
    keys = []
    for sd in range(24):
        inst = make_instance(seed=300 + sd, **DIFFICULTY["easy"])
        k0 = canonical_key(inst)
        keys.append(k0)
        mm = inst["m"]
        perm = list(range(mm))
        rng.shuffle(perm)
        lam = rng.randrange(1, 7)
        c = rng.randrange(-3, 20)
        variants = [
            {"m": mm, "a": [inst["a"][perm[i]] for i in range(mm)]},
            {"m": mm, "a": [lam * v for v in inst["a"]]},
            {"m": mm, "a": [v + c for v in inst["a"]]},
            {"m": mm, "a": [lam * inst["a"][perm[i]] + c for i in range(mm)]},
        ]
        for v in variants:
            inv_tot += 1
            if canonical_key(v) == k0:
                inv += 1
        # the transformation is REAL: affine variants keep the same answers
        aff = {"m": mm, "a": [lam * v + c for v in inst["a"]],
               "answer": inst["answer"]}
        if verify(aff, inst["answer"])[0]:
            carried += 1
        # and the permuted instance verifies against the carried answer
        inv_perm = [0] * mm
        for i, pi in enumerate(perm):
            inv_perm[pi] = i
        pv = {"m": mm, "a": [inst["a"][perm[i]] for i in range(mm)]}
        moved = sorted(inv_perm[i] for i in inst["answer"])
        if verify(pv, moved)[0]:
            carried += 1
    rep["G8_canonical_key"] = {
        "invariance_ok": inv, "invariance_checks": inv_tot,
        "answer_carried_through_transform": carried,
        "distinct_keys": len(set(keys)), "instances": len(keys),
        "pass": inv == inv_tot and len(set(keys)) == len(keys)
                and carried == 2 * len(keys),
    }
    say("G8", rep["G8_canonical_key"])

    # ---- G9 -----------------------------------------------------------
    inst = make_instance(seed=99, **ship)
    txt = _answer_text(inst["answer"])
    route_ops = (m - 1) + (m // 2)      # form T = (sum a)/2, then one block sum
    caps = {"chars": 2000, "elements": 256, "operations": 1000}
    within = (len(txt) <= caps["chars"] and len(inst["answer"]) <= caps["elements"]
              and route_ops <= caps["operations"])
    rep["G9_no_tool_suitability"] = {
        "answer_chars": len(txt),
        "answer_elements": len(inst["answer"]),
        "answer_tokens": len(inst["answer"]) + txt.count(",") + 1,
        "answer_bits_equivalent": m,
        "intended_route_operations": route_ops,
        "intended_route_operations_note":
            "Track A: there is no compact route past the search.  The number "
            "reported is the exact-arithmetic cost of the route a solver takes "
            "ONCE it holds the certificate -- form T = (sum a)/2 with m-1 "
            "big-integer additions, then add the m/2 chosen weights and compare. "
            "The search that produces the certificate is the hard part and is "
            "measured in G5/G6.",
        "caps": caps,
        "within_caps": within,
        "arms": {"bare": {"solved": 0, "attempts": 0},
                 "hinted": {"solved": 0, "attempts": 0},
                 "placebo": {"solved": 0, "attempts": 0}},
        "arms_note": "three-arm diagnostic not run by the module selftest; "
                     "STEP 4 runs the bare arm (llm_loop_transcript.jsonl).",
        "diagnostic_not_gated": True,
        "hinted_minus_placebo": None,
        "hinted_verdict": None,
        "pass": bool(within),
    }
    say("G9", rep["G9_no_tool_suitability"]["answer_chars"], "chars",
        route_ops, "ops")

    rep["all_passed"] = all(v.get("pass") for k, v in rep.items()
                            if k.startswith("G"))
    rep["track"] = TRACK
    rep["shipping_difficulty"] = SHIPPING_DIFFICULTY
    rep["shipping_params"] = dict(ship)
    rep["certificate_language"] = CERTIFICATE_LANGUAGE
    rep["problem_profile"] = PROBLEM_PROFILE
    return rep


if __name__ == "__main__":
    import json
    import sys
    if "--demo" in sys.argv:
        i = make_instance(seed=3, **DIFFICULTY["demo"])
        print(render(i))
        print("\nplanted answer:", i["answer"], verify(i, i["answer"]))
        print("valid answers (exhaustive):", enumerate_all(i))
    else:
        r = selftest(verbose=True)
        print(json.dumps(r, indent=1, sort_keys=True, default=str))
