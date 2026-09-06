"""Verified generator for McNie / Niederreiter syndrome decoding over F_q.

Paper: Kim, Kim, Galvez, Kim, Lee, "McNie: A code-based public-key
cryptosystem", arXiv:1812.05008 (cs.CR).

Native object.  Section 3.1 (the boxed Key generation / Encryption /
Decryption) defines McNie for "a parity check matrix H in F_{q^m}^{(n-k) x n}
of an r-error-correcting code with an efficient decoding algorithm", and
Section 4.2 ("Security reduction") proves that attacking the ciphertext
c1 = m G' + e is exactly an instance of the (Rank) Syndrome Decoding problem
with parameters (n, l, r): given a parity-check matrix and a syndrome, find an
error vector of bounded weight.  This module ships that problem in the Hamming
metric (m = 1, i.e. a prime field F_q), which is the metric the abstract names
("its security is reduced to the hard problem of syndrome decoding") and the
one for which information-set decoding is the domain-standard attack.  The
rank-metric instantiation of Sections 2-3.3 is *not* what ships here; see the
README caveats.

Generation is inverse: the error vector is sampled FIRST (support then nonzero
values), the parity-check matrix is sampled independently and uniformly, and
the published syndrome is s = H e^T.  make_instance never searches.

Verification is one exact matrix-vector product over F_q plus a weight count.
Below the unique-decoding radius the planted e is, with the probability
recorded in PROBLEM_PROFILE, the only vector of weight <= w with that
syndrome, so verify() is a decision procedure and not merely a soundness test.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time
from math import comb

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:  # present in the repository; this finite-field family does not need it
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - graceful standard-library fallback
    exact_matrices = rationals = None


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "parity-check matrix H = [I_u | A] over the prime field F_q",
        "syndrome vector s in F_q^u",
        "bounded-Hamming-weight error vector e in F_q^n, given by its support",
    ],
    "verification_operations": [
        "exact modular matrix-vector product H e^T over F_q",
        "componentwise equality with the published syndrome",
        "Hamming weight count against the published bound w",
        "range and distinctness checks on the reported support",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "duality",
    "intuition_description": (
        "The systematic block I_u makes the first u coordinates of e a linear "
        "function of the last k, so the free unknowns are only e restricted to "
        "the information set; a solver without that observation searches the "
        "whole weight-w sphere in F_q^n instead of the much smaller set of "
        "low-weight patterns on k coordinates."
    ),
    "hardness_basis": (
        "Track A: coset weights / syndrome decoding of a random linear code is "
        "NP-complete (Berlekamp, McEliece, van Tilborg 1978), and McNie's own "
        "security reduction (Section 4.2 of arXiv:1812.05008) is to exactly "
        "this problem; the shipped distribution is the standard hard one - "
        "uniform H and a uniform weight-w error with w = 17 strictly below the "
        "unique-decoding radius of a random [210,168] code over F_31 - where "
        "the best known attack is information-set decoding.  Measured at the "
        "shipping preset: Prange needs 1.705e13 expected iterations "
        "(2^44.0), Lee-Brickell with p=1 reduces that by 110.8x at 23x the "
        "per-iteration cost, and both were run and failed."
    ),
    "max_answer_tokens": 96,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}


# q  prime field size, n code length, k code dimension (u = n - k parity
# checks), w Hamming weight of the planted error.  The named ladder holds w
# well below the unique-decoding radius of a random [n,k]_q code while raising
# n and the field.  escalate() then grows n and q with w FIXED, so the answer
# stays 2w atoms forever.
DIFFICULTY = {
    "demo":   {"q": 7,  "n": 10,  "k": 5,   "w": 2},
    "easy":   {"q": 13, "n": 60,  "k": 45,  "w": 6},
    "medium": {"q": 31, "n": 150, "k": 120, "w": 12},
    "hard":   {"q": 31, "n": 210, "k": 168, "w": 17},
}

SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The left block of the parity-check matrix is the identity, so the first "
    "u coordinates of the error are already determined by the last k."
)
PLACEBO_HINT = (
    "The rows of the displayed matrix are listed top to bottom, so keeping the "
    "index bookkeeping straight matters throughout this computation."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A strictly increasing list of at most w indices in {0,...,n-1}, each "
        "paired with a value in {1,...,q-1}; this is the support "
        "representation of a vector e in F_q^n of Hamming weight at most w.  "
        "The language has sum_{j=0}^{w} C(n,j)(q-1)^j members."
    ),
    "bounds": {
        "max_support_size": "w",
        "index_range": "0..n-1",
        "value_range": "1..q-1",
        "atoms": "2w (at most 34 at the shipping preset)",
    },
}

NOTES = (
    "Section 3.1 (boxed Key generation) fixes the object: a parity-check "
    "matrix H over F_{q^m} of an r-error-correcting code, an error e of weight "
    "at most r, and the published data from which e must be recovered.  "
    "Section 4.2 (Security reduction) is the theorem that licenses the family: "
    "attacking c1 = m G' + e IS a syndrome-decoding instance with parameters "
    "(n, l, r).  Section 4.3.1 names the domain-standard attack "
    "('Combinatorial attacks ... apply the Information Set Decoding') and is "
    "why Prange and Lee-Brickell are the mandatory adversaries here.  What "
    "makes the problem EASY, and had to be avoided: (i) any algebraic "
    "structure in H - Goppa, GRS, Reed-Solomon, Gabidulin, LRPC - is broken by "
    "structural attacks (Sections 4.3.3-4.3.5 catalogue Overbeck, "
    "Lau-Tan, Hauteville-Tillich), so H here is uniformly random with no "
    "hidden structure at all and no trapdoor is published; (ii) Remark 2 and "
    "Section 4.3.2 (Gaborit's attack) show that publishing c2 = m F leaks "
    "n-k linear equations on the message and collapses the effective "
    "dimension, so the c2 half of the McNie ciphertext is deliberately NOT "
    "part of the instance; (iii) w above the unique-decoding radius would "
    "admit many solutions, so w is held below it and the expected number of "
    "spurious solutions is computed exactly.  Attacks defeated: Prange ISD, "
    "Lee-Brickell ISD (p=1), plain support enumeration, unconstrained "
    "Gaussian elimination, column-statistic outlier ranking, greedy syndrome "
    "peeling, and randomised restarts with a weight heuristic."
)


# --------------------------------------------------------------------------
# prime field helpers (exact integer arithmetic modulo a prime; no floats)
# --------------------------------------------------------------------------

def _is_prime(m: int) -> bool:
    if m < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if m % p == 0:
            return m == p
    d, r = m - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        x = pow(a, d, m)
        if x in (1, m - 1):
            continue
        for _ in range(r - 1):
            x = x * x % m
            if x == m - 1:
                break
        else:
            return False
    return True


def _next_prime(m: int) -> int:
    c = max(2, m + 1)
    while not _is_prime(c):
        c += 1
    return c


def _solve_square(cols, rhs, q):
    """Solve M y = rhs where M has the given columns, over F_q.

    ``cols`` is a list of u column vectors (each a list of u ints).  Returns
    the solution list, or None when M is singular.  Pure integer arithmetic.
    """
    u = len(rhs)
    # augmented rows
    rows = [[cols[j][i] % q for j in range(u)] + [rhs[i] % q] for i in range(u)]
    piv_row = 0
    for c in range(u):
        p = None
        for r in range(piv_row, u):
            if rows[r][c]:
                p = r
                break
        if p is None:
            return None
        rows[piv_row], rows[p] = rows[p], rows[piv_row]
        pr = rows[piv_row]
        inv = pow(pr[c], q - 2, q)
        if inv != 1:
            rows[piv_row] = pr = [v * inv % q for v in pr]
        for r in range(u):
            if r != piv_row and rows[r][c]:
                f = rows[r][c]
                rr = rows[r]
                rows[r] = [(a - f * b) % q for a, b in zip(rr, pr)]
        piv_row += 1
    return [rows[i][u] for i in range(u)]


def _invert_square(cols, q):
    """Inverse of the matrix with the given columns, as a list of rows."""
    u = len(cols)
    rows = [[cols[j][i] % q for j in range(u)] + [1 if j == i else 0
                                                  for j in range(u)]
            for i in range(u)]
    piv = 0
    for c in range(u):
        p = None
        for r in range(piv, u):
            if rows[r][c]:
                p = r
                break
        if p is None:
            return None
        rows[piv], rows[p] = rows[p], rows[piv]
        pr = rows[piv]
        inv = pow(pr[c], q - 2, q)
        if inv != 1:
            rows[piv] = pr = [v * inv % q for v in pr]
        for r in range(u):
            if r != piv and rows[r][c]:
                f = rows[r][c]
                rr = rows[r]
                rows[r] = [(a - f * b) % q for a, b in zip(rr, pr)]
        piv += 1
    return [row[u:] for row in rows]


def _rref(rows, ncols, q):
    """Reduced row echelon form of ``rows`` over F_q; returns (rows, pivots)."""
    mat = [list(r) for r in rows]
    piv = 0
    pivots = []
    for c in range(ncols):
        p = None
        for r in range(piv, len(mat)):
            if mat[r][c] % q:
                p = r
                break
        if p is None:
            continue
        mat[piv], mat[p] = mat[p], mat[piv]
        inv = pow(mat[piv][c] % q, q - 2, q)
        mat[piv] = [v * inv % q for v in mat[piv]]
        pr = mat[piv]
        for r in range(len(mat)):
            if r != piv and mat[r][c] % q:
                f = mat[r][c] % q
                mat[r] = [(a - f * b) % q for a, b in zip(mat[r], pr)]
        pivots.append(c)
        piv += 1
        if piv == len(mat):
            break
    return mat, pivots


# --------------------------------------------------------------------------
# instance construction (G: plant first, derive the public data afterwards)
# --------------------------------------------------------------------------

def make_instance(n=None, seed=0, **params):
    """Build one McNie/Niederreiter syndrome-decoding instance.

    Accepts the preset keys as keyword arguments, e.g.
    ``make_instance(seed=3, **DIFFICULTY["hard"])``.
    """
    if n is None:
        n = params.get("n")
    if n is None:
        raise ValueError("code length n is required")
    q = int(params.get("q", 31))
    k = int(params.get("k", n // 2))
    w = int(params.get("w", 2))
    n = int(n)
    u = n - k
    if not _is_prime(q):
        raise ValueError("q must be prime (this family works over F_p)")
    if not (0 < k < n):
        raise ValueError("need 0 < k < n")
    if not (0 < w <= u // 2):
        raise ValueError("need 0 < w <= (n-k)/2 for unique decoding")

    rng = random.Random(("mcnie-1812.05008", q, n, k, w, seed).__repr__())

    # ---- 1. the certificate is sampled FIRST ----------------------------
    support = sorted(rng.sample(range(n), w))
    values = [rng.randrange(1, q) for _ in range(w)]
    answer = [[int(p), int(v)] for p, v in zip(support, values)]

    # ---- 2. the public parity-check matrix, sampled independently -------
    #        H = [ I_u | A ], A uniform over F_q^{u x k}
    A = [[rng.randrange(q) for _ in range(k)] for _ in range(u)]

    # ---- 3. the syndrome is DERIVED from the plant ----------------------
    #        s = H e^T, computed sparsely from the support (w*u operations)
    s = [0] * u
    for p, v in answer:
        if p < u:
            s[p] += v
        else:
            j = p - u
            for i in range(u):
                s[i] += A[i][j] * v
    s = [x % q for x in s]

    # exact expected number of OTHER weight-<=w vectors with this syndrome
    tot = sum(comb(n, j) * (q - 1) ** j for j in range(w + 1)) - 1
    spurious_num, spurious_den = tot, q ** u

    return {
        "family": "mcnie_syndrome_decoding",
        "paper": "arXiv:1812.05008",
        "q": q, "n": n, "k": k, "u": u, "w": w,
        "seed": seed,
        "A": A,
        "s": s,
        "answer": answer,
        "expected_spurious_solutions": [spurious_num, spurious_den],
    }


# --------------------------------------------------------------------------
# statement
# --------------------------------------------------------------------------

def _fmt_matrix(A):
    return "\n".join(" ".join(str(v) for v in row) for row in A)


def render(inst) -> str:
    q, n, k, u, w = inst["q"], inst["n"], inst["k"], inst["u"], inst["w"]
    lines = []
    lines.append(
        "Syndrome decoding over a finite field.\n"
        "\n"
        f"Work in the prime field F_q with q = {q}: the elements are the "
        f"integers 0, 1, ..., {q - 1} and all arithmetic (+, -, *) is done "
        f"modulo {q}.\n"
    )
    lines.append(
        f"Let n = {n}, k = {k} and u = n - k = {u}.\n"
        f"You are given a parity-check matrix H of size {u} x {n} over F_q in "
        "systematic form\n"
        "\n"
        f"    H = [ I_{u} | A ]\n"
        "\n"
        f"where I_{u} is the {u} x {u} identity matrix and A is the "
        f"{u} x {k} matrix printed below.  A is listed one row per line, rows "
        f"0 to {u - 1} from top to bottom, entries separated by single spaces, "
        f"columns 0 to {k - 1} from left to right.  Column j of A is column "
        f"{u} + j of H, so H has columns indexed 0 to {n - 1}.\n"
    )
    lines.append("A =")
    lines.append(_fmt_matrix(inst["A"]))
    lines.append("")
    lines.append(
        f"You are also given a syndrome vector s = (s_0, ..., s_{{{u - 1}}}) "
        "in F_q^u:\n"
    )
    lines.append("s = " + " ".join(str(v) for v in inst["s"]))
    lines.append("")
    lines.append(
        f"TASK.  Find a vector e = (e_0, e_1, ..., e_{{{n - 1}}}) with every "
        "e_t in F_q such that BOTH of the following hold.\n"
        "\n"
        "  (1)  H e^T = s.  Written out, for every i = 0, 1, ..., "
        f"{u - 1}:\n"
        "\n"
        f"           e_i  +  sum_{{j=0}}^{{{k - 1}}} A[i][j] * e_{{{u}+j}}   "
        f"==   s_i   (mod {q})\n"
        "\n"
        f"  (2)  the Hamming weight of e is at most w = {w}; that is, the "
        f"number of indices t in 0..{n - 1} with e_t != 0 is at most {w}.\n"
    )
    lines.append(
        "Such a vector exists.  Any e satisfying (1) and (2) is accepted; "
        "with overwhelming probability it is unique.\n"
    )
    lines.append(
        "ANSWER FORMAT.  Report e by its support only: for each index t with "
        "e_t != 0, give the pair t:e_t.  Indices are 0-based, must be "
        f"strictly increasing, must lie in 0..{n - 1}, must not repeat, and "
        f"each value must lie in 1..{q - 1}.  Coordinates you do not list are "
        "taken to be 0.\n"
        "\n"
        "Give your final answer inside <answer></answer> tags as a "
        'comma-separated list of "index:value" pairs sorted by increasing '
        "index.\n"
        "Example: <answer>3:17, 45:2, 199:30</answer>\n"
        "Output nothing else inside the tags."
    )
    text = "\n".join(lines)

    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


# --------------------------------------------------------------------------
# parsing
# --------------------------------------------------------------------------

_PAIR = re.compile(r"(-?\d+)\s*[:=]\s*(-?\d+)")
_BRACKET_PAIR = re.compile(r"[\[(]\s*(-?\d+)\s*,\s*(-?\d+)\s*[\])]")


def parse_answer(text):
    if text is None:
        return None
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer>(.*?)</answer>", text, re.S | re.I)
    body = blocks[-1] if blocks else text
    body = body.replace("```", " ")
    # a JSON list of pairs is also accepted
    stripped = body.strip()
    if stripped.startswith("["):
        try:
            data = json.loads(stripped)
            out = []
            for item in data:
                if (isinstance(item, (list, tuple)) and len(item) == 2
                        and all(isinstance(x, int) for x in item)):
                    out.append([int(item[0]), int(item[1])])
                else:
                    return None
            return out if out else None
        except Exception:
            pass
    pairs = _PAIR.findall(body)
    if not pairs:
        # tolerate "(3, 17), (45, 2)" / "[3, 17] [45, 2]" bracketed pairs
        pairs = _BRACKET_PAIR.findall(body)
    if not pairs:
        return None
    try:
        return [[int(a), int(b)] for a, b in pairs]
    except Exception:
        return None


# --------------------------------------------------------------------------
# verification (exact, over F_q; never reads inst["answer"])
# --------------------------------------------------------------------------

def verify(inst, answer):
    q, n, k, u, w = inst["q"], inst["n"], inst["k"], inst["u"], inst["w"]
    if answer is None:
        return False, "no answer"
    if not isinstance(answer, (list, tuple)):
        return False, "answer is not a list of index:value pairs"
    if len(answer) > w:
        return False, f"support size {len(answer)} exceeds the weight bound {w}"
    seen = set()
    pairs = []
    for item in answer:
        if not (isinstance(item, (list, tuple)) and len(item) == 2):
            return False, "an entry is not an index:value pair"
        p, v = item
        if not isinstance(p, int) or isinstance(p, bool):
            return False, "an index is not an integer"
        if not isinstance(v, int) or isinstance(v, bool):
            return False, "a value is not an integer"
        if not (0 <= p < n):
            return False, f"index {p} out of range 0..{n - 1}"
        if not (1 <= v <= q - 1):
            return False, f"value {v} out of range 1..{q - 1}"
        if p in seen:
            return False, f"index {p} repeated"
        seen.add(p)
        pairs.append((p, v))
    if len(pairs) > w:
        return False, f"Hamming weight {len(pairs)} exceeds the bound {w}"
    # exact syndrome recomputation, sparsely: w * u modular multiply-adds
    s = inst["s"]
    acc = [0] * u
    if "H" in inst:                                   # general (twisted) form
        H = inst["H"]
        for p, v in pairs:
            for i in range(u):
                acc[i] += H[i][p] * v
    else:                                             # systematic H = [I | A]
        A = inst["A"]
        for p, v in pairs:
            if p < u:
                acc[p] += v
            else:
                j = p - u
                for i in range(u):
                    acc[i] += A[i][j] * v
    for i in range(u):
        if acc[i] % q != s[i] % q:
            return False, f"syndrome mismatch in row {i}"
    return True, "ok"


# --------------------------------------------------------------------------
# candidate space
# --------------------------------------------------------------------------

def random_candidate(inst, rng):
    """Uniform over the declared certificate language: a weight-w support with
    nonzero values.  Every constraint the statement makes free (index range,
    distinctness, sorted order, value range, support size) is already
    enforced."""
    q, n, w = inst["q"], inst["n"], inst["w"]
    sup = sorted(rng.sample(range(n), w))
    return [[p, rng.randrange(1, q)] for p in sup]


def search_space(inst):
    q, n, w = inst["q"], inst["n"], inst["w"]
    return sum(comb(n, j) * (q - 1) ** j for j in range(w + 1))


def information_set_space(inst):
    """The sharper space a solver who sees the systematic block searches:
    low-weight patterns on the k information coordinates only."""
    q, k, w = inst["q"], inst["k"], inst["w"]
    return sum(comb(k, j) * (q - 1) ** j for j in range(w + 1))


def enumerate_all(inst, budget=4_000_000):
    """Exact number of weight-<=w solutions, or None when the enumeration is
    over budget.  Uses the systematic block: e_L is determined by e_R."""
    q, n, k, u, w = inst["q"], inst["n"], inst["k"], inst["u"], inst["w"]
    work = sum(comb(k, j) * (q - 1) ** j for j in range(w + 1))
    if work > budget:
        return None
    A, s = inst["A"], inst["s"]
    count = 0
    for j in range(w + 1):
        for sup in itertools.combinations(range(k), j):
            for vals in itertools.product(range(1, q), repeat=j):
                acc = list(s)
                for c, v in zip(sup, vals):
                    for i in range(u):
                        acc[i] -= A[i][c] * v
                left = [x % q for x in acc]
                if sum(1 for x in left if x) + j <= w:
                    count += 1
    return count


# --------------------------------------------------------------------------
# canonical key
# --------------------------------------------------------------------------

def canonical_key(inst) -> str:
    """Invariant under (a) any change of parity-check basis H -> U H, s -> U s
    with U invertible, and (b) any permutation of the k information
    coordinates.  Column permutations that mix the parity block with the
    information block are NOT quotiented out: that is code equivalence, which
    is exactly the hard problem this family is built on."""
    q, n, k, u = inst["q"], inst["n"], inst["k"], inst["u"]
    H = _H(inst)
    # form [H | s] and put it in RREF, which kills the left U-action
    aug = [list(H[i]) + [inst["s"][i]] for i in range(u)]
    red, pivots = _rref(aug, n + 1, q)
    # pivot columns are 0..u-1 for a systematic instance; read off A' and s'
    body = [[red[i][u + j] % q for j in range(k)] for i in range(u)]
    tail = [red[i][n] % q for i in range(u)]
    cols = sorted(tuple(body[i][j] for i in range(u)) for j in range(k))
    payload = json.dumps(
        {"f": "mcnie_sd", "q": q, "n": n, "k": k, "w": inst["w"],
         "A": cols, "s": tail},
        separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


# --------------------------------------------------------------------------
# escalation: grow the haystack, not the needle
# --------------------------------------------------------------------------

def escalate(params):
    """Harder parameters at FIXED answer length.

    Two dials move together and the error weight w never does:
      * n doubles while u = n - k stays fixed, so the code rate rises and the
        Prange iteration count C(n,w)/C(u,w) grows by roughly 2^w;
      * q jumps to the next prime above 4q, which raises the entropy of every
        answer value, multiplies the certificate language by 4^w, and widens
        the unique-decoding margin so the answer stays unique.
    The answer is always w index:value pairs = 2w atoms, independent of both.
    """
    p = dict(params)
    q, n, k, w = int(p["q"]), int(p["n"]), int(p["k"]), int(p["w"])
    u = n - k
    new_n = 2 * n
    new_q = _next_prime(4 * q)
    new_k = new_n - u
    # uniqueness must survive: E[#other weight<=w vectors] < 2^-20
    tot = sum(comb(new_n, j) * (new_q - 1) ** j for j in range(w + 1)) - 1
    if tot * (1 << 20) >= new_q ** u:
        return "cap_bound"
    return {"q": new_q, "n": new_n, "k": new_k, "w": w}


# --------------------------------------------------------------------------
# adversaries
# --------------------------------------------------------------------------

def _H(inst):
    """The full u x n parity-check matrix as a list of rows.

    Instances published by make_instance are systematic, so H = [I_u | A] is
    rebuilt on demand; a twisted instance (used by the G8 invariance check)
    may carry an explicit non-systematic "H"."""
    if "H" in inst:
        return inst["H"]
    u, k = inst["u"], inst["k"]
    A = inst["A"]
    return [[1 if j == i else 0 for j in range(u)] + list(A[i])
            for i in range(u)]


def _columns(inst):
    q, n, u = inst["q"], inst["n"], inst["u"]
    H = _H(inst)
    return [[H[i][t] % q for i in range(u)] for t in range(n)]


def attack_prange(inst, rng, max_iters=None, time_budget=None):
    """Prange information-set decoding (Prange 1962), the domain-standard
    attack named in Section 4.3.1 of the paper.  Returns
    (answer or None, iterations, seconds)."""
    q, n, u, w = inst["q"], inst["n"], inst["u"], inst["w"]
    cols = _columns(inst)
    s = inst["s"]
    idx = list(range(n))
    t0 = time.time()
    it = 0
    while True:
        if max_iters is not None and it >= max_iters:
            break
        if time_budget is not None and time.time() - t0 > time_budget:
            break
        it += 1
        J = rng.sample(idx, u)
        y = _solve_square([cols[t] for t in J], s, q)
        if y is None:
            continue
        if sum(1 for v in y if v) <= w:
            ans = sorted([J[i], y[i] % q] for i in range(u) if y[i] % q)
            return ans, it, time.time() - t0
    return None, it, time.time() - t0


def attack_lee_brickell(inst, rng, p=1, max_iters=None, time_budget=None):
    """Lee-Brickell ISD with parameter p: allow p error positions inside the
    information set.  Implemented for p in {0,1}."""
    q, n, u, w = inst["q"], inst["n"], inst["u"], inst["w"]
    cols = _columns(inst)
    s = inst["s"]
    idx = list(range(n))
    t0 = time.time()
    it = 0
    while True:
        if max_iters is not None and it >= max_iters:
            break
        if time_budget is not None and time.time() - t0 > time_budget:
            break
        it += 1
        J = rng.sample(idx, u)
        Jset = set(J)
        inv = _invert_square([cols[t] for t in J], q)
        if inv is None:
            continue
        y0 = [sum(inv[i][t] * s[t] for t in range(u)) % q for i in range(u)]
        if sum(1 for v in y0 if v) <= w:
            ans = sorted([J[i], y0[i]] for i in range(u) if y0[i])
            return ans, it, time.time() - t0
        if p == 0:
            continue
        for c in idx:
            if c in Jset:
                continue
            col = cols[c]
            uc = [sum(inv[i][t] * col[t] for t in range(u)) % q
                  for i in range(u)]
            for v in range(1, q):
                cand = [(y0[i] - v * uc[i]) % q for i in range(u)]
                if sum(1 for x in cand if x) <= w - 1:
                    ans = sorted([[J[i], cand[i]] for i in range(u)
                                  if cand[i]] + [[c, v]])
                    return ans, it, time.time() - t0
    return None, it, time.time() - t0


def attack_bruteforce_supports(inst, budget=2_000_000):
    """Plain enumeration of low-weight patterns on the information set."""
    q, n, k, u, w = inst["q"], inst["n"], inst["k"], inst["u"], inst["w"]
    A, s = inst["A"], inst["s"]
    t0 = time.time()
    tried = 0
    for j in range(w + 1):
        for sup in itertools.combinations(range(k), j):
            for vals in itertools.product(range(1, q), repeat=j):
                tried += 1
                if tried > budget:
                    return None, tried, time.time() - t0
                acc = list(s)
                for c, v in zip(sup, vals):
                    Acol = [A[i][c] for i in range(u)]
                    for i in range(u):
                        acc[i] -= Acol[i] * v
                left = [x % q for x in acc]
                if sum(1 for x in left if x) + j <= w:
                    ans = sorted([[i, left[i]] for i in range(u) if left[i]]
                                 + [[u + c, v] for c, v in zip(sup, vals)])
                    return ans, tried, time.time() - t0
    return None, tried, time.time() - t0


def attack_gaussian_baseline(inst):
    """Unconstrained linear algebra: solve H e^T = s ignoring the weight
    bound.  The systematic form gives the solution with e_R = 0 immediately.
    Returns (answer or None, weight_found, seconds)."""
    q, u, w = inst["q"], inst["u"], inst["w"]
    t0 = time.time()
    e_left = [v % q for v in inst["s"]]
    wt = sum(1 for v in e_left if v)
    ans = sorted([i, e_left[i]] for i in range(u) if e_left[i])
    ok = wt <= w
    return (ans if ok else None), wt, time.time() - t0


def attack_column_outlier(inst):
    """Outlier probe: rank coordinates by how well their column correlates
    with the syndrome, then take the w best as the support and solve for the
    values on that support."""
    q, n, u, w = inst["q"], inst["n"], inst["u"], inst["w"]
    cols = _columns(inst)
    s = inst["s"]
    score = []
    for t in range(n):
        c = cols[t]
        # residual weight after the best single-scalar cancellation
        best = u + 1
        for v in range(1, q):
            wt = sum(1 for i in range(u) if (s[i] - v * c[i]) % q)
            if wt < best:
                best = wt
        score.append((best, t))
    score.sort()
    sup = sorted(t for _, t in score[:w])
    # solve the over-determined system H[:, sup] x = s exactly on that support
    vals = _solve_restricted(inst, sup)
    if vals is None:
        return None
    return sorted([sup[i], vals[i]] for i in range(len(sup)) if vals[i])


def _solve_restricted(inst, sup):
    """Solve H[:, sup] x = s exactly (u equations, |sup| unknowns) or None."""
    q, u = inst["q"], inst["u"]
    cols = _columns(inst)
    m = len(sup)
    rows = [[cols[sup[j]][i] % q for j in range(m)] + [inst["s"][i] % q]
            for i in range(u)]
    red, pivots = _rref(rows, m + 1, q)
    if m in pivots:
        return None  # inconsistent
    x = [0] * m
    for r, c in enumerate(pivots):
        x[c] = red[r][m] % q
    # confirm
    for i in range(u):
        acc = sum(cols[sup[j]][i] * x[j] for j in range(m)) % q
        if acc != inst["s"][i] % q:
            return None
    return x


def attack_greedy_peel(inst, rng, restarts=1):
    """Greedy syndrome peeling: repeatedly pick the (column, value) pair that
    reduces the syndrome weight the most, up to w times."""
    q, n, u, w = inst["q"], inst["n"], inst["u"], inst["w"]
    cols = _columns(inst)
    for _ in range(restarts):
        resid = list(inst["s"])
        chosen = {}
        for _step in range(w):
            best = None
            order = list(range(n))
            rng.shuffle(order)
            for t in order:
                if t in chosen:
                    continue
                c = cols[t]
                for v in range(1, q):
                    wt = sum(1 for i in range(u) if (resid[i] - v * c[i]) % q)
                    if best is None or wt < best[0]:
                        best = (wt, t, v)
            if best is None:
                break
            wt, t, v = best
            chosen[t] = v
            c = cols[t]
            resid = [(resid[i] - v * c[i]) % q for i in range(u)]
            if wt == 0:
                break
        if all(x == 0 for x in resid) and len(chosen) <= w:
            return sorted([t, v] for t, v in chosen.items())
    return None


def attack_random_restart(inst, rng, restarts=256):
    """Sample a random support, solve the restricted linear system exactly,
    accept when it is consistent."""
    q, n, w = inst["q"], inst["n"], inst["w"]
    for _ in range(restarts):
        sup = sorted(rng.sample(range(n), w))
        vals = _solve_restricted(inst, sup)
        if vals is not None:
            ans = sorted([sup[i], vals[i]] for i in range(w) if vals[i])
            ok, _ = verify(inst, ans)
            if ok:
                return ans
    return None


# --------------------------------------------------------------------------
# analytic attack costs
# --------------------------------------------------------------------------

def prange_expected_iterations(inst):
    n, u, w = inst["n"], inst["u"], inst["w"]
    return comb(n, w) / comb(u, w)


def lee_brickell_gain(inst, p=1):
    """Iteration-count reduction factor of Lee-Brickell(p=1) over Prange."""
    k, u, w = inst["k"], inst["u"], inst["w"]
    if w < 1 or u - w + 1 <= 0:
        return 1.0
    return 1.0 + k * comb(u, w - 1) / comb(u, w)


# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------

def _corruptions(inst, ans, rng):
    q, n, w = inst["q"], inst["n"], inst["w"]
    out = []
    if ans:
        drop = [list(p) for p in ans[1:]]
        out.append(("drop_one", drop))
        swapped = [list(p) for p in ans]
        swapped[0][1] = 1 + (swapped[0][1] % (q - 1))
        out.append(("perturb_value", swapped))
        moved = [list(p) for p in ans]
        used = {p for p, _ in ans}
        cand = next(t for t in range(n) if t not in used)
        moved[0][0] = cand
        out.append(("move_index", sorted(moved)))
        dup = [list(p) for p in ans] + [list(ans[0])]
        out.append(("duplicate_index", dup))
        oor = [list(p) for p in ans]
        oor[0][0] = n + 5
        out.append(("index_out_of_range", oor))
        badv = [list(p) for p in ans]
        badv[0][1] = 0
        out.append(("value_zero", badv))
    out.append(("empty", []))
    return out


def selftest(verbose=True, heavy=True):
    t_start = time.time()
    report = {"module": "gen_1812_05008", "track": TRACK,
              "shipping_difficulty": SHIPPING_DIFFICULTY}
    rng = random.Random(20260906)

    # ---------------- G1 ------------------------------------------------
    g1_total = g1_ok = 0
    per_preset = {}
    for name, params in DIFFICULTY.items():
        cnt = 0
        for sd in range(6):
            inst = make_instance(seed=sd, **params)
            ok, why = verify(inst, inst["answer"])
            g1_total += 1
            if ok:
                g1_ok += 1
                cnt += 1
            else:
                per_preset.setdefault("failures", []).append((name, sd, why))
        per_preset[name] = f"{cnt}/6"
    report["G1_planted_verifies"] = {
        "pass": g1_ok == g1_total, "ok": g1_ok, "total": g1_total,
        "per_preset": per_preset,
    }

    # ---------------- G2 ------------------------------------------------
    reasons = {}
    g2_bad = 0
    for name, params in DIFFICULTY.items():
        inst = make_instance(seed=101, **params)
        for label, bad in _corruptions(inst, inst["answer"], rng):
            ok, why = verify(inst, bad)
            if ok:
                g2_bad += 1
            reasons.setdefault(label, set()).add(why.split(" in row")[0])
    report["G2_rejects_corruption"] = {
        "pass": g2_bad == 0,
        "accepted_corruptions": g2_bad,
        "distinct_reasons": sorted({r for v in reasons.values() for r in v}),
    }

    # ---------------- G3 ------------------------------------------------
    inst = make_instance(seed=7, **DIFFICULTY["medium"])
    ans = inst["answer"]
    body = ", ".join(f"{p}:{v}" for p, v in ans)
    prose = ("Let me set up the information set and eliminate.\n\n"
             "```\nsome scratch work\n```\n"
             f"So the error vector has support of size {len(ans)}.\n"
             f"<answer>{body}</answer>\nThat should be it.")
    got = parse_answer(prose)
    rt_ok = got == ans and verify(inst, got)[0]
    junk_ok = parse_answer("I could not determine the error vector.") is None
    json_form = parse_answer("<answer>" + json.dumps(ans) + "</answer>") == ans
    report["G3_round_trip"] = {
        "pass": bool(rt_ok and junk_ok and json_form),
        "prose_round_trip": bool(rt_ok), "garbage_returns_none": bool(junk_ok),
        "json_form_accepted": bool(json_form),
    }

    # ---------------- G4 ------------------------------------------------
    ship = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=11, **ship)
    trials = 200_000
    hits = 0
    grng = random.Random(4242)
    for _ in range(trials):
        cand = random_candidate(inst, grng)
        if verify(inst, cand)[0]:
            hits += 1
    space = search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": hits == 0,
        "hits": hits, "trials": trials,
        "structure_aware_space": str(space),
        "structure_aware_space_log2": round(math.log2(space), 2),
        "information_set_space_log2": round(
            math.log2(information_set_space(inst)), 2),
        "analytic_p_guess": f"~1/{space}",
    }

    # ---------------- G5 ------------------------------------------------
    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    num, den = inst["expected_spurious_solutions"]
    exp_sp_log2 = math.log2(num) - math.log2(den) if num else float("-inf")
    prange_iters = prange_expected_iterations(inst)
    prng = random.Random(9001)
    _, pit, psec = attack_prange(inst, prng, time_budget=25.0 if heavy else 2.0)
    sec_per_iter = psec / max(pit, 1)
    report["G5_density_and_baseline"] = {
        "shipping_preset": SHIPPING_DIFFICULTY,
        "shipping_params": ship,
        "exact_solution_count_demo": demo_count,
        "expected_spurious_solutions_log2_shipping": round(exp_sp_log2, 2),
        "sampled_density_shipping": f"{hits}/{trials}",
        "baseline_attack": "Prange information-set decoding",
        "prange_expected_iterations": prange_iters,
        "prange_expected_iterations_log2": round(math.log2(prange_iters), 2),
        "prange_measured_iterations": pit,
        "prange_measured_seconds": round(psec, 3),
        "prange_seconds_per_iteration": sec_per_iter,
        "prange_projected_seconds": prange_iters * sec_per_iter,
        "prange_projected_years": prange_iters * sec_per_iter / 31_557_600,
    }

    # ---------------- G6 ------------------------------------------------
    attacks = {}
    seeds = list(range(8))
    arng = random.Random(777)

    def _run(name, fn):
        succ = 0
        t0 = time.time()
        for sd in seeds:
            i2 = make_instance(seed=1000 + sd, **ship)
            got = fn(i2, arng)
            if got is not None and verify(i2, got)[0]:
                succ += 1
        attacks[name] = {"successes": succ, "attempts": len(seeds),
                         "seconds": round(time.time() - t0, 3)}

    _run("outlier_column_correlation", lambda i, r: attack_column_outlier(i))
    _run("greedy_syndrome_peeling",
         lambda i, r: attack_greedy_peel(i, r, restarts=1))
    _run("random_restart_256",
         lambda i, r: attack_random_restart(i, r, restarts=256))
    _run("gaussian_elimination_baseline",
         lambda i, r: attack_gaussian_baseline(i)[0])
    isd_budget = 20.0 if heavy else 2.0
    _run("prange_isd",
         lambda i, r: attack_prange(i, r, time_budget=isd_budget)[0])
    _run("lee_brickell_isd_p1",
         lambda i, r: attack_lee_brickell(i, r, p=1, time_budget=isd_budget)[0])
    _run("bruteforce_supports",
         lambda i, r: attack_bruteforce_supports(i, budget=200_000)[0])
    report["G6_adversary_panel"] = {
        "pass": all(a["successes"] == 0 for a in attacks.values()),
        "attacks": attacks,
    }

    # ---------------- G7 ------------------------------------------------
    bigger = escalate(ship)
    g7 = {"escalated_params": bigger}
    if isinstance(bigger, dict):
        bi = make_instance(seed=5, **bigger)
        ok, why = verify(bi, bi["answer"])
        g7["escalated_verifies"] = bool(ok)
        g7["escalated_prange_log2"] = round(
            math.log2(prange_expected_iterations(bi)), 2)
        g7["shipping_prange_log2"] = round(math.log2(prange_iters), 2)
        g7["answer_atoms_shipping"] = 2 * ship["w"]
        g7["answer_atoms_escalated"] = 2 * bigger["w"]
        g7["harder"] = (g7["escalated_prange_log2"]
                        > g7["shipping_prange_log2"])
        g7["answer_length_fixed"] = (g7["answer_atoms_shipping"]
                                     == g7["answer_atoms_escalated"])
        g7["pass"] = bool(ok and g7["harder"] and g7["answer_length_fixed"])
    else:
        g7["pass"] = False
    # difficulty is monotone along the named ladder too
    ladder = []
    for name, params in DIFFICULTY.items():
        i3 = make_instance(seed=1, **params)
        ladder.append((name, round(math.log2(
            prange_expected_iterations(i3)), 2)))
    g7["ladder_prange_log2"] = ladder
    g7["ladder_monotone"] = all(ladder[i][1] < ladder[i + 1][1]
                                for i in range(len(ladder) - 1))
    g7["pass"] = bool(g7["pass"] and g7["ladder_monotone"])
    report["G7_scales"] = g7

    # ---------------- G8 ------------------------------------------------
    inv_ok = inv_tot = 0
    real_ok = 0
    krng = random.Random(31337)
    small = DIFFICULTY["easy"]
    real_tot = 0
    for sd in range(20):
        base = make_instance(seed=sd, **small)
        key0 = canonical_key(base)
        q, u, k, n = base["q"], base["u"], base["k"], base["n"]
        H0 = _H(base)

        def twist_basis(H, s):
            """H -> U H, s -> U s for a random invertible U over F_q.  The
            published matrix is genuinely non-systematic afterwards."""
            while True:
                U = [[krng.randrange(q) for _ in range(u)] for _ in range(u)]
                if _rref([r[:] for r in U], u, q)[1] == list(range(u)):
                    break
            H2 = [[sum(U[i][t] * H[t][c] for t in range(u)) % q
                   for c in range(n)] for i in range(u)]
            s2 = [sum(U[i][t] * s[t] for t in range(u)) % q for i in range(u)]
            return H2, s2

        def perm_info(H, perm):
            """Relabel the k information coordinates."""
            return [[H[i][c] if c < u else H[i][u + perm[c - u]]
                     for c in range(n)] for i in range(u)]

        perm = list(range(k))
        krng.shuffle(perm)
        inv_perm = [0] * k
        for j, pj in enumerate(perm):
            inv_perm[pj] = j
        moved = sorted([p if p < u else u + inv_perm[p - u], v]
                       for p, v in base["answer"])

        # (a) change of parity-check basis alone
        H2, s2 = twist_basis(H0, base["s"])
        t1 = dict(base); t1["H"] = H2; t1["s"] = s2
        # (b) information-coordinate relabelling alone
        t2 = dict(base); t2["H"] = perm_info(H0, perm)
        # (c) the two composed, in both orders
        t3 = dict(base); t3["H"] = perm_info(H2, perm); t3["s"] = s2
        H4, s4 = twist_basis(perm_info(H0, perm), base["s"])
        t4 = dict(base); t4["H"] = H4; t4["s"] = s4

        for tw, ans in ((t1, base["answer"]), (t2, moved),
                        (t3, moved), (t4, moved)):
            inv_tot += 1
            if canonical_key(tw) == key0:
                inv_ok += 1
            real_tot += 1
            ok_t, _ = verify(tw, ans)
            if ok_t:
                real_ok += 1

    keys = {canonical_key(make_instance(seed=500 + sd, **small))
            for sd in range(20)}
    report["G8_canonical_key"] = {
        "pass": (inv_ok == inv_tot and len(keys) == 20
                 and real_ok == real_tot),
        "invariance_ok": inv_ok, "invariance_total": inv_tot,
        "invariances_tested": [
            "H -> U H, s -> U s (change of parity-check basis)",
            "relabelling of the k information coordinates",
            "both composed, in both orders",
        ],
        "transformation_is_real_ok": real_ok,
        "transformation_checks": real_tot,
        "distinct_keys": len(keys), "distinct_seeds": 20,
    }

    # ---------------- G9(c) ---------------------------------------------
    ship_inst = make_instance(seed=13, **ship)
    ans = ship_inst["answer"]
    serial = ", ".join(f"{p}:{v}" for p, v in ans)
    chars = len(serial)
    atoms = 2 * len(ans)
    tokens = max(1, round(chars / 4))
    verify_ops = len(ans) * (ship["n"] - ship["k"])
    report["G9_no_tool_suitability"] = {
        "pass": chars <= 2000 and atoms <= 256,
        "arms": {"bare": None, "hinted": None, "placebo": None},
        "arms_note": "three-arm oracle diagnostic not run: no OPENROUTER_API_KEY "
                     "in this environment",
        "answer_chars": chars, "answer_tokens": tokens,
        "answer_elements": atoms,
        "answer_json_chars": len(json.dumps(ans)),
        "verification_operations": verify_ops,
        "intended_route_operations": None,
        "intended_route_note": (
            "Track A: there is no compact solving route.  The recorded number "
            "is the cost of CHECKING a proposed answer (w*u modular "
            "multiply-adds); the cost of FINDING one is the Prange figure in "
            "G5."),
        "render_chars": len(render(ship_inst)),
    }

    # ---------------- JSON-nativeness -----------------------------------
    report["json_native_answer"] = (
        json.loads(json.dumps(ship_inst["answer"])) == ship_inst["answer"])

    gates = [report["G1_planted_verifies"]["pass"],
             report["G2_rejects_corruption"]["pass"],
             report["G3_round_trip"]["pass"],
             report["G4_guess_resistance"]["pass"],
             report["G6_adversary_panel"]["pass"],
             report["G7_scales"]["pass"],
             report["G8_canonical_key"]["pass"],
             report["G9_no_tool_suitability"]["pass"],
             report["json_native_answer"]]
    report["all_gates_pass"] = all(gates)
    report["elapsed_sec"] = round(time.time() - t_start, 2)
    if verbose:
        print(json.dumps(report, indent=2, default=str))
    return report


if __name__ == "__main__":
    selftest()
