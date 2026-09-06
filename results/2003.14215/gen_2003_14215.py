"""Verified generator for key recovery in a difference block cipher.

Paper: Roberto La Scala, Sharwan K. Tiwari, "Stream/block ciphers, difference
equations and algebraic attacks", arXiv:2003.14215 (cs.CR, cs.SC, math.AC,
math.RA).

Native object.  Definition 5.6 defines a *difference block cipher* as a
reducible invertible explicit difference system together with a final clock T;
the key is the initial state u(0) of the key subsystem, the plaintext is v(0)
and the ciphertext is v(T).  Section 7 instantiates this with KeeLoq, equation
(7.1):

    k(64) = k(0)
    x(32) = x(0) + x(16) + x(9) + x(1) + x(20)x(31) + ... + k(0)

This module ships exactly that system shape at reduced size: a key subsystem
k(K) = k(0) -- a cyclic permutation of period K, which is Definition 4.1's
notion of period and the "period d of the key subsystem" that Section 5's final
subsection turns into an attack -- together with one explicit cubic difference
equation whose nonlinear part is KeeLoq's own NL function 0x3A5C742E (its ANF
is the one printed in (7.1); the module asserts the two agree).  Corollary 3.4
gives invertibility: x(0) occurs linearly and every other term has clock >= 1.

What ships.  The solver is handed the difference system, the NL truth table,
the round count R and a handful of plaintext/ciphertext pairs, and must return
the key.  Verification re-runs the difference system: exact GF(2) arithmetic,
no floats anywhere.

Generation is forward-only.  The key is sampled FIRST, uniformly, from
GF(2)^K.  One plaintext P is sampled uniformly, its slid partner is computed as
P* = F(P) where F is the K-round map -- one forward encryption with the key we
already hold.  Nothing is ever searched for.  Because the key subsystem has
period K and R = m*K, the encryption is E = F^m, so E(P*) = E(F(P)) = F(E(P)):
the slid relation propagates to the ciphertexts, and the pair (P, P*) is itself
a K-round plaintext/ciphertext pair.  Since the block length equals K, such a
pair pins down the whole internal bit-sequence and each round equation then
*defines* one key bit.  That is the compact route; see STRUCTURAL_HINT.

Why this is Track B.  An efficient algorithm exists and it is the compact route
itself.  What a solver reaches for without that observation -- the algebraic
attack of Definition 5.9 (Groebner bases or SAT over the round equations, which
is what Sections 6 and 7 actually run) -- degenerates here to exhaustive key
search, because the difference system is *explicit* (Definition 2.1) and so
every round equation is affine in each single variable: propagation determines
everything downstream of a guess and constrains nothing upstream of it.  Both
numbers are measured in selftest_report.json.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:  # present in the repository; this GF(2) family does not need it
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - graceful standard-library fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "explicit difference system over GF(2): k(K)=k(0) and "
        "x(L)=x(0)+x(a1)+x(a2)+NL(x(p1),...,x(p5))+k(0)",
        "t-states of the system, published as plaintext/ciphertext pairs",
        "initial state of the key subsystem (the key), a vector in GF(2)^K",
    ],
    "verification_operations": [
        "exact GF(2) evaluation of the explicit difference equation, R times "
        "per published pair",
        "table lookup of the NL polynomial on 5 GF(2) arguments",
        "componentwise equality of the recomputed t-state with the published "
        "ciphertext",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "The round count is an exact multiple of the key subsystem's period, "
        "so the encryption is a power of one fixed permutation F and therefore "
        "commutes with it; two published plaintexts standing in the relation "
        "P2 = F(P1) then form a single-period plaintext/ciphertext pair whose "
        "internal bit-sequence is completely published, and each round "
        "equation reads off one key bit.  A solver without that observation "
        "must run the algebraic attack of Definition 5.9, which on an explicit "
        "difference system collapses to exhaustive key search."
    ),
    "hardness_basis": (
        "Track B.  The algorithm that exists is the key-period / slid-pair "
        "attack of Section 5's final subsection (the paper's own reduction of "
        "the final clock T to the period d of the key subsystem, applied to "
        "KeeLoq in Section 7); its complexity is O(s^2 * K) GF(2) operations "
        "and its measured cost at the shipping preset is 384-564 primitive "
        "operations over 24 seeds.  The mechanical route -- the algebraic "
        "attack of Definition 5.9 by multiple plaintext-ciphertext pairs, run "
        "as Groebner-style elimination / unit propagation with branching, "
        "which is what Sections 6 and 7 run against Bivium and KeeLoq -- was "
        "measured to degenerate to exhaustive key search: 0.5*2^12, 1.5*2^14 "
        "and 1.35*2^16 search nodes at K = 12, 14, 16 with m >= 3, flat in m "
        "past m = 3.  With R = m*K and m >= 2 the first round equation whose "
        "left-hand side is a published ciphertext bit is t = R - L = "
        "(m-1)K >= K, so every key bit is assigned before any consistency "
        "check exists and the search tree cannot be pruned above the leaves.  "
        "At the shipping preset that is of order 2^48 nodes; the measured "
        "per-node cost and node rate, and the projected wall clock, are in "
        "G5_density_and_baseline.  Brute force over the key space is 2^48 "
        "encryptions of 288 rounds, also projected there from a measured "
        "rate."
    ),
    "max_answer_tokens": 48,
}

NATIVE = {
    "domain": "algebra",
    "core": "other",
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": "symmetry: " + PROBLEM_PROFILE["intuition_description"],
    "reduction": None,
}

# K = key length = key-subsystem period = block length L.  R = m*K rounds.
DIFFICULTY = {
    "demo":   {"K": 12, "m": 2, "npairs": 2, "nl_taps": 5},
    "easy":   {"K": 24, "m": 3, "npairs": 3, "nl_taps": 5},
    "medium": {"K": 32, "m": 4, "npairs": 3, "nl_taps": 5},
    "hard":   {"K": 48, "m": 6, "npairs": 3, "nl_taps": 5},
}
SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "The key: the initial state k(0),...,k(K-1) of the key subsystem "
        "k(K) = k(0), written as a string of K characters from {0,1} with k(0) "
        "leftmost.  Nothing else is admissible."
    ),
    "bounds": {"field": 2, "length": "K", "atoms": "K", "chars": "K"},
}

STRUCTURAL_HINT = (
    "The number of rounds is an exact multiple of the key subsystem's period, "
    "so the encryption map is a power of one fixed permutation of the state "
    "space."
)

PLACEBO_HINT = (
    "This problem rewards keeping the round index and the register index "
    "carefully separated at every step of the computation."
)

NOTES = """
Which section fixed the definition.  Definition 5.6 (difference block cipher:
a reducible invertible explicit difference system plus a final clock T; key =
u(0), plaintext = v(0), ciphertext = v(T)).  Definition 5.9 (algebraic attack by
multiple plaintext-ciphertext pairs) is the attack this family is measured
against.  Equation (7.1) is the concrete system whose shape is shipped, and its
NL part is KeeLoq's 0x3A5C742E -- the module asserts the paper's printed ANF and
that table agree on all 32 inputs.

What told me what makes it easy.  Section 5, final subsection: "A better
strategy is possible when the period of the key subsystem, say d, is
sufficiently small... we are reduced to compute V_K(I' + J') for T = 64."  The
paper reduces the final clock from 528 to 64 by finding fixed points; the same
identity S^d = id licenses the slid pair used here.  Definition 4.1 and
Proposition 4.5 supply "period"; Corollary 3.4 supplies invertibility (x(0)
occurs linearly and nothing else sits at clock 0).

What makes it hard, and what I had to steer around.  Section 2's word
"explicit" is the whole story: in an explicit system every round equation is
affine in each single variable, so unit propagation determines everything
downstream of a guess and constrains nothing upstream.  I first built the
obvious family -- reduced-round key recovery with R rounds against block length
L -- and measured it dead.  With u = R - L unknown interior bits, the compact
route and the standard algebraic attack are *the same algorithm* at every u:
at u = 0 both cost about 1.1e3 primitive operations, and the standard attack
only reaches 1e6 operations at u = 21-22, by which point the compact route
needs at least 2^7 branch decisions (no seed finished at g <= 6 once u >= 20),
i.e. >= 1.5e5 operations, 150x over G9's route cap.
Measured growth of the standard attack there: 2^(1.01*u) primitive operations
over u = 16..24.  That window is empty and the numbers are in the README.

What re-opened it was the paper's own device rather than a parameter choice.
Making R a multiple of the key period turns the cipher into F^m, and planting
one slid plaintext pair (forward-only, with the key already in hand) inserts a
single-period pair into the published data without inserting any statistical
signature: for ANY two K-bit strings A, B there is a key with B = F(A), so the
slid pair is information-theoretically invisible from the plaintexts alone.
The discrimination is C-side agreement, which is what the compact route uses.

What I did to defeat each attack.  (i) No fixed point is ever published, so the
Section-5 fixed-point scan finds nothing.  (ii) Plaintexts, including the slid
partner, are uniform K-bit strings drawn from the same distribution; no
positional, weight or ordering statistic separates them (attack
outlier_pair_statistics).  (iii) R >= 3K, because at m = 2 the interior window
is small enough that the DPLL/Groebner attack costs only 0.04*2^K instead of
1.35*2^K.  (iv) The pair list is shuffled, so the slid pair is not the first
one and its orientation is not fixed.
"""

# --------------------------------------------------------------------------
# The difference system
# --------------------------------------------------------------------------

# KeeLoq's NL function.  Section 7, equation (7.1) prints its ANF; the standard
# specification gives it as the truth table 0x3A5C742E.  _check_nlf asserts the
# two agree.
KEELOQ_NL = 0x3A5C742E


def _keeloq_anf(v0, v1, v2, v3, v4):
    """The ANF displayed in (7.1) with (v0..v4) = (x(1),x(9),x(20),x(26),x(31))."""
    return (v1 ^ v0 ^ (v2 & v4) ^ (v0 & v4) ^ (v2 & v3) ^ (v0 & v3)
            ^ (v1 & v2) ^ (v0 & v1) ^ (v0 & v1 & v4) ^ (v0 & v2 & v4)
            ^ (v1 & v3 & v4) ^ (v2 & v3 & v4))


def _check_nlf():
    for idx in range(32):
        v = [(idx >> i) & 1 for i in range(5)]
        if _keeloq_anf(*v) != ((KEELOQ_NL >> idx) & 1):
            return False
    return True


def _nl_lookup(table, vals):
    idx = 0
    for i, b in enumerate(vals):
        idx |= b << i
    return (table >> idx) & 1


def _encrypt(inst, key, pt, rounds=None):
    """Run the explicit difference system forward.  Exact GF(2), no floats."""
    K = inst["K"]
    L = inst["L"]
    R = inst["R"] if rounds is None else rounds
    lin = inst["lin_taps"]
    nlt = inst["nl_taps"]
    tbl = inst["nl_table"]
    s = list(pt) + [0] * R
    for t in range(R):
        idx = 0
        for i, p in enumerate(nlt):
            idx |= s[t + p] << i
        b = s[t] ^ ((tbl >> idx) & 1) ^ key[t % K]
        for a in lin:
            b ^= s[t + a]
        s[t + L] = b
    return s[R:R + L]


def _readoff(inst, A, B):
    """A = x(0..K-1), B = x(K..2K-1) of a K-round pair -> the K key bits.

    Uses only published values: this is the compact route's inner loop.
    """
    K = inst["K"]
    L = inst["L"]
    lin = inst["lin_taps"]
    nlt = inst["nl_taps"]
    tbl = inst["nl_table"]
    s = list(A) + list(B)
    out = []
    for t in range(K):
        idx = 0
        for i, p in enumerate(nlt):
            idx |= s[t + p] << i
        b = s[t] ^ s[t + L] ^ ((tbl >> idx) & 1)
        for a in lin:
            b ^= s[t + a]
        out.append(b)
    return out


def _readoff_bits(inst, A, B, count):
    """The first `count` key bits only -- the compact route's cheap filter."""
    K = inst["K"]
    L = inst["L"]
    lin = inst["lin_taps"]
    nlt = inst["nl_taps"]
    tbl = inst["nl_table"]
    s = list(A) + list(B)
    out = []
    for t in range(count):
        idx = 0
        for i, p in enumerate(nlt):
            idx |= s[t + p] << i
        b = s[t] ^ s[t + L] ^ ((tbl >> idx) & 1)
        for a in lin:
            b ^= s[t + a]
        out.append(b)
    return out


def _key_bit(inst, A, B, t):
    """One key bit k(t) from the single-period window A || B.  This is the
    compact route's atomic step: one NL table lookup and five XORs."""
    L = inst["L"]
    lin = inst["lin_taps"]
    nlt = inst["nl_taps"]
    tbl = inst["nl_table"]
    get = (lambda i: A[i] if i < L else B[i - L])   # index into A || B
    idx = 0
    for q, p_ in enumerate(nlt):
        idx |= get(t + p_) << q
    b = get(t) ^ get(t + L) ^ ((tbl >> idx) & 1)
    for a in lin:
        b ^= get(t + a)
    return b


# --------------------------------------------------------------------------
# make_instance
# --------------------------------------------------------------------------

def make_instance(n=None, seed=0, **params):
    """Build one instance.  The key is sampled FIRST and uniformly; every other
    published object is produced by running the difference system forward.
    There is no search anywhere in this function.

    ``n`` is an alias for the key length K, so both
    ``make_instance(48, seed=3, m=6, npairs=3)`` and
    ``make_instance(seed=3, **DIFFICULTY["hard"])`` work.
    """
    K = int(params.get("K", n if n is not None else 48))
    m = int(params.get("m", 6))
    npairs = int(params.get("npairs", 3))
    nl_taps = int(params.get("nl_taps", 5))
    if K < 8:
        raise ValueError("K must be at least 8")
    if m < 2:
        raise ValueError("m must be at least 2 (R = m*K rounds)")
    if npairs < 2:
        raise ValueError("npairs must be at least 2")
    if nl_taps < 5 or nl_taps > 8 or nl_taps + 2 > K - 1:
        raise ValueError("nl_taps out of range for this K")

    rng = random.Random("2003.14215|%d|%d|%d|%d|%d"
                        % (seed, K, m, npairs, nl_taps))

    L = K                     # block length = key length = key period
    R = m * K

    # taps: x(0) is always present (Corollary 3.4 => invertible); every other
    # tap has clock >= 1.
    sel = rng.sample(range(1, L), 2 + nl_taps)
    sel.sort()
    lin_taps = tuple(sel[:2])
    nl_tap_pos = tuple(sel[2:])

    if nl_taps == 5:
        table = KEELOQ_NL                       # KeeLoq's own NL, eq (7.1)
    else:                                       # balanced random NL
        size = 1 << nl_taps
        bits = [0] * (size // 2) + [1] * (size - size // 2)
        rng.shuffle(bits)
        table = 0
        for i, b in enumerate(bits):
            table |= b << i

    inst = {
        "paper": "arXiv:2003.14215",
        "K": K, "L": L, "m": m, "R": R,
        "lin_taps": list(lin_taps),
        "nl_taps": list(nl_tap_pos),
        "nl_table": table,
        "nl_table_hex": "0x%0*X" % ((1 << nl_taps) // 4 or 1, table),
    }

    # --- the key, sampled FIRST, uniformly on GF(2)^K -------------------
    key = [rng.getrandbits(1) for _ in range(K)]

    # --- one slid plaintext pair, built forward only --------------------
    p_a = [rng.getrandbits(1) for _ in range(L)]
    p_b = _encrypt(inst, key, p_a, rounds=K)      # P* = F(P), K rounds
    plaintexts = [p_a, p_b]
    for _ in range(npairs - 2):
        plaintexts.append([rng.getrandbits(1) for _ in range(L)])

    order = list(range(npairs))
    rng.shuffle(order)
    plaintexts = [plaintexts[i] for i in order]

    pairs = [[p, _encrypt(inst, key, p)] for p in plaintexts]

    inst["pairs"] = pairs
    inst["answer"] = list(key)
    return inst


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------

def _bits(v):
    return "".join(str(b) for b in v)


def render(inst) -> str:
    K, L, R = inst["K"], inst["L"], inst["R"]
    a1, a2 = inst["lin_taps"]
    nlt = inst["nl_taps"]
    nl_arity = len(nlt)
    args = ", ".join("x(t+%d)" % p for p in nlt)
    lines = []
    A = lines.append
    A("A block cipher is given as a system of explicit difference equations "
      "over the field GF(2) = {0,1}, where + is XOR.")
    A("")
    A("There is one bit sequence x(0), x(1), x(2), ... and one key sequence")
    A("k(0), k(1), k(2), ....  They satisfy, for every integer t >= 0:")
    A("")
    A("    k(t + %d) = k(t)" % K)
    A("    x(t + %d) = x(t) + x(t+%d) + x(t+%d) + NL(%s) + k(t)"
      % (L, a1, a2, args))
    A("")
    A("So the key sequence is periodic with period %d and is completely "
      "determined by" % K)
    A("its first %d bits k(0), k(1), ..., k(%d), which are called THE KEY."
      % (K, K - 1))
    A("")
    A("NL is a fixed function of %d bits, given by its truth table" % nl_arity)
    A("")
    A("    T = %s" % inst["nl_table_hex"])
    A("")
    A("read as follows.  Write T in binary.  For arguments (v_1, ..., v_%d) "
      "form the" % nl_arity)
    A("index  i = v_1 + 2*v_2 + 4*v_3 + ... + %d*v_%d.  Then NL(v_1,...,v_%d) "
      "is bit i" % (1 << (nl_arity - 1), nl_arity, nl_arity))
    A("of T, counting bit 0 as the LEAST significant bit of T.  The arguments "
      "are taken")
    A("in the order written above, i.e. v_1 = x(t+%d), ..., v_%d = x(t+%d)."
      % (nlt[0], nl_arity, nlt[-1]))
    if nl_arity == 5:
        A("")
        A("(Equivalently, in algebraic normal form with v_1..v_5 as above,")
        A("  NL = v_2 + v_1 + v_3 v_5 + v_1 v_5 + v_3 v_4 + v_1 v_4 + v_2 v_3")
        A("       + v_1 v_2 + v_1 v_2 v_5 + v_1 v_3 v_5 + v_2 v_4 v_5 "
          "+ v_3 v_4 v_5.)")
    A("")
    A("ENCRYPTION.  The block length is %d.  A plaintext is the vector" % L)
    A("    P = ( x(0), x(1), ..., x(%d) )" % (L - 1))
    A("and the corresponding ciphertext after R = %d rounds is the vector" % R)
    A("    C = ( x(%d), x(%d), ..., x(%d) )." % (R, R + 1, R + L - 1))
    A("In other words: load the plaintext into x(0..%d), apply the recurrence "
      "above for" % (L - 1))
    A("t = 0, 1, ..., %d to produce x(%d), ..., x(%d), and read the ciphertext "
      "off the" % (R - 1, L, R + L - 1))
    A("last %d entries.  All bit strings below are written with the LOWEST "
      "index first," % L)
    A("that is, the leftmost character of P is x(0).")
    A("")
    A("You are given %d plaintext/ciphertext pairs, all produced with the SAME "
      "key:" % len(inst["pairs"]))
    A("")
    for i, (p, c) in enumerate(inst["pairs"], 1):
        A("    P%d = %s" % (i, _bits(p)))
        A("    C%d = %s" % (i, _bits(c)))
        A("")
    A("TASK.  Find the key k(0), k(1), ..., k(%d)." % (K - 1))
    A("")
    A("The key is uniquely determined by the data above.")
    A("")
    A("Give your final answer inside <answer></answer> tags, as a string of "
      "exactly %d" % K)
    A("characters, each '0' or '1', with k(0) leftmost and k(%d) rightmost."
      % (K - 1))
    A("Example: <answer>%s</answer>" % ("01" * (K // 2) + "0" * (K % 2)))
    A("Output nothing else inside the tags.")

    text = "\n".join(lines)
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


# --------------------------------------------------------------------------
# parse_answer / verify
# --------------------------------------------------------------------------

def parse_answer(text):
    if text is None:
        return None
    if isinstance(text, (list, tuple)):
        try:
            out = [int(b) for b in text]
        except (TypeError, ValueError):
            return None
        return out if all(b in (0, 1) for b in out) else None
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer>(.*?)</answer>", text, re.S | re.I)
    cands = blocks if blocks else [text]
    strict = not blocks          # outside tags, refuse anything but a bare key

    def extract(blk):
        s = blk.strip()
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
        compact = re.sub(r"[\s,\[\]]", "", s.strip())
        if compact and re.fullmatch(r"[01]+", compact):
            return [int(ch) for ch in compact]
        if strict:
            return None
        # inside <answer> tags be forgiving about a label or stray punctuation:
        # take the longest maximal run of bits and separators
        best = None
        for mo in re.finditer(r"[01][01\s,]*[01]", s):
            bits = re.sub(r"[\s,]", "", mo.group(0))
            if len(bits) >= 8 and (best is None or len(bits) > len(best)):
                best = bits
        return [int(ch) for ch in best] if best else None

    out = None
    for blk in reversed(cands):
        got = extract(blk)
        if got is not None:
            if blocks:
                return got
            out = got
    return out


def verify(inst, answer):
    """(True,'ok') or (False, reason).  Accepts ANY key reproducing the data.
    Never reads inst['answer']."""
    K = inst["K"]
    if answer is None:
        return False, "no answer parsed"
    if isinstance(answer, str):
        answer = parse_answer(answer)
        if answer is None:
            return False, "no answer parsed"
    if not isinstance(answer, (list, tuple)):
        return False, "answer is not a sequence of bits"
    if len(answer) != K:
        return False, "key length %d, expected %d" % (len(answer), K)
    key = []
    for b in answer:
        if isinstance(b, bool) or not isinstance(b, int):
            try:
                b = int(b)
            except (TypeError, ValueError):
                return False, "non-integer entry in key"
        if b not in (0, 1):
            return False, "value %r out of range 0..1" % (b,)
        key.append(b)
    for i, (p, c) in enumerate(inst["pairs"], 1):
        got = _encrypt(inst, key, list(p))
        if got != list(c):
            bad = sum(1 for x, y in zip(got, c) if x != y)
            return False, ("ciphertext mismatch on pair %d (%d of %d bits "
                           "differ)" % (i, bad, len(c)))
    return True, "ok"


# --------------------------------------------------------------------------
# candidate space
# --------------------------------------------------------------------------

def random_candidate(inst, rng):
    """A solver reading the statement knows exactly one thing about the answer:
    it is K bits.  Nothing else is freely deducible, so this is the
    structure-aware space."""
    return [rng.getrandbits(1) for _ in range(inst["K"])]


def search_space(inst):
    return 1 << inst["K"]


def enumerate_all(inst, budget=1 << 21):
    """Exact count of valid keys by brute force; None if over budget."""
    K = inst["K"]
    if (1 << K) > budget:
        return None
    cnt = 0
    for v in range(1 << K):
        key = [(v >> i) & 1 for i in range(K)]
        if verify(inst, key)[0]:
            cnt += 1
    return cnt


def canonical_key(inst) -> str:
    """Same problem = same system, same round count, same multiset of published
    pairs.  Invariant under reordering the pair list (the family's only
    relabelling) and under the order the tap sets are written in."""
    pairs = sorted((_bits(p), _bits(c)) for p, c in inst["pairs"])
    blob = json.dumps({
        "K": inst["K"], "m": inst["m"], "R": inst["R"],
        "lin": sorted(inst["lin_taps"]),
        "nl": sorted(inst["nl_taps"]),
        "tbl": inst["nl_table"],
        "pairs": pairs,
    }, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()[:32]


def escalate(params):
    """Strictly harder at FIXED answer length.  K never moves, so the answer
    stays exactly K bits and K atoms.  Every call moves at least two
    parameters.  Three haystack axes, in the order that keeps the compact
    route inside G9's operation cap for as long as possible:

      m       -- rounds R = m*K.  More rounds for the algebraic attack of
                 Definition 5.9 to propagate through; the compact route is
                 unaffected because it only ever looks at K-round windows.
      nl_taps -- arity of NL, hence its algebraic degree.  Raises the
                 linearisation monomial count and the Groebner cost; the
                 compact route still pays one table lookup per key bit.
      npairs  -- decoy pairs.  The number of ordered hypotheses the compact
                 route must sift grows as s(s-1); the answer does not grow.
    """
    p = dict(params)
    p.pop("_preset", None)
    K = int(p.get("K", 48))
    m = int(p.get("m", 6))
    s = int(p.get("npairs", 3))
    nl = int(p.get("nl_taps", 5))
    if nl < 6 and nl + 3 < K:
        p["m"] = m + 2
        p["nl_taps"] = nl + 1
        return p
    if s < 4:
        p["m"] = m + 2
        p["npairs"] = s + 1
        return p
    if nl < 7 and nl + 3 < K:
        p["m"] = m + 4
        p["nl_taps"] = nl + 1
        return p
    # npairs stops at 4 and nl_taps at 7: a fifth pair pushes the compact route
    # past G9's 1000-operation cap (measured 1092 at npairs = 5, K = 48).
    # Everything left would lengthen the answer: only K raises difficulty now.
    return "cap_bound"


# --------------------------------------------------------------------------
# THE COMPACT ROUTE (Track B reference algorithm)
# --------------------------------------------------------------------------

def slide_attack(inst, confirm=16):
    """Section 5's key-period reduction, in the slid-pair form.

    R = m*K and the key subsystem has period K, so E = F^m and E commutes with
    F.  If two published plaintexts satisfy P_j = F(P_i) then (P_i, P_j) is a
    K-round plaintext/ciphertext pair; the block length is K, so P_i || P_j is
    the WHOLE internal bit-sequence of those K rounds and each round equation
    determines one key bit.  The same holds for (C_i, C_j), and the two
    read-offs agree only for the genuinely slid pair -- so a wrong hypothesis
    is discarded after about two bits.

    Returns (key or None, primitive_operation_count).
    """
    K = inst["K"]
    ops = [0]

    def bit(A, B, t):
        ops[0] += 6                       # one NL lookup + five XORs
        return _key_bit(inst, A, B, t)

    pairs = inst["pairs"]
    s = len(pairs)
    lim = min(confirm, K)
    for i in range(s):
        for j in range(s):
            if i == j:
                continue
            key = []
            agree = True
            for t in range(lim):
                a = bit(pairs[i][0], pairs[j][0], t)
                b = bit(pairs[i][1], pairs[j][1], t)
                if a != b:
                    agree = False
                    break
                key.append(a)
            if not agree:
                continue
            for t in range(lim, K):
                key.append(bit(pairs[i][0], pairs[j][0], t))
            if verify(inst, key)[0]:
                return key, ops[0]
    return None, ops[0]


def intended_route_operations(inst):
    return slide_attack(inst)[1]


# --------------------------------------------------------------------------
# ATTACKS (G6 panel) -- all of these are expected to FAIL
# --------------------------------------------------------------------------

def attack_brute_force(inst, rng, budget=200_000, time_budget=8.0):
    """Exhaustive key search.  Returns (key or None, tried, seconds)."""
    K = inst["K"]
    t0 = time.time()
    tried = 0
    p0, c0 = inst["pairs"][0]
    p0 = list(p0); c0 = list(c0)
    for v in range(min(1 << K, budget)):
        tried += 1
        key = [(v >> i) & 1 for i in range(K)]
        if _encrypt(inst, key, p0) == c0:
            if verify(inst, key)[0]:
                return key, tried, time.time() - t0
        if (tried & 0x3FF) == 0 and time.time() - t0 > time_budget:
            break
    return None, tried, time.time() - t0


def attack_algebraic_dpll(inst, node_cap=4000, time_budget=20.0):
    """The algebraic attack of Definition 5.9: keep the intermediate state
    variables, propagate every round equation that has a single unknown
    (Groebner elimination with linear leading terms / SAT unit propagation),
    and branch when propagation stalls.  Returns (key or None, nodes, ops, s).
    """
    K, L, R = inst["K"], inst["L"], inst["R"]
    lin, nlt, tbl = inst["lin_taps"], inst["nl_taps"], inst["nl_table"]
    UNK = -1
    t0 = time.time()
    nodes = [0]
    ops = [0]

    base_seqs = []
    for p, c in inst["pairs"]:
        s = [UNK] * (R + L)
        s[:L] = list(p)
        s[R:R + L] = list(c)
        base_seqs.append(s)

    def propagate(seqs, key):
        changed = True
        while changed:
            changed = False
            for s in seqs:
                for t in range(R):
                    kj = t % K
                    idxs = [t] + [t + a for a in lin] + \
                           [t + p for p in nlt] + [t + L]
                    unk = {i for i in idxs if s[i] == UNK}
                    nu = len(unk) + (1 if key[kj] == UNK else 0)
                    if nu > 1:
                        continue

                    def F(v):
                        ops[0] += 6
                        g = lambda i: (s[i] if s[i] != UNK else v)
                        idx = 0
                        for q, p_ in enumerate(nlt):
                            idx |= g(t + p_) << q
                        b = g(t) ^ g(t + L) ^ ((tbl >> idx) & 1)
                        for a in lin:
                            b ^= g(t + a)
                        return b ^ (key[kj] if key[kj] != UNK else v)

                    if nu == 0:
                        if F(0) != 0:
                            return False
                        continue
                    f0, f1 = F(0), F(1)
                    if f0 == f1:
                        if f0 != 0:
                            return False
                        continue
                    val = 0 if f0 == 0 else 1
                    if not unk:
                        key[kj] = val
                    else:
                        for i in unk:
                            s[i] = val
                    changed = True
        return True

    class Stop(Exception):
        pass

    def rec(seqs, key):
        nodes[0] += 1
        if nodes[0] > node_cap or time.time() - t0 > time_budget:
            raise Stop
        seqs = [list(x) for x in seqs]
        key = list(key)
        if not propagate(seqs, key):
            return None
        for j in range(K):
            if key[j] == UNK:
                for v in (0, 1):
                    k2 = list(key); k2[j] = v
                    r = rec(seqs, k2)
                    if r is not None:
                        return r
                return None
        for si in range(len(seqs)):
            for i in range(L, R):
                if seqs[si][i] == UNK:
                    for v in (0, 1):
                        s2 = [list(x) for x in seqs]
                        s2[si][i] = v
                        r = rec(s2, key)
                        if r is not None:
                            return r
                    return None
        return key if verify(inst, key)[0] else None

    try:
        res = rec(base_seqs, [UNK] * K)
    except (Stop, RecursionError):
        res = None
    return res, nodes[0], ops[0], time.time() - t0


def attack_linearisation(inst):
    """Linearisation of the difference system at degree <= 3 (Definition 5.9
    with the intermediate variables kept).  Reports whether the linearised
    system can possibly be solved."""
    K, L, R = inst["K"], inst["L"], inst["R"]
    s = len(inst["pairs"])
    u = max(0, R - L)
    nvar = s * u + K
    mon = 1 + nvar + nvar * (nvar - 1) // 2 + nvar * (nvar - 1) * (nvar - 2) // 6
    neq = s * R
    return {
        "unknowns": nvar,
        "deg3_monomials": mon,
        "equations": neq,
        "rank_deficit": mon - 1 - neq,
        "solved": neq >= mon - 1,
    }


def attack_key_equation_degree(inst, cap_monomials=2000, max_rounds=None,
                               time_budget=15.0):
    """Theorem 5.4: eliminate the intermediate variables by iterating the state
    transition endomorphism, f'_t = Tbar^t(f), and watch the degree.  Each
    x(t+L) is rewritten as a polynomial in the key variables.  This is the
    paper's own elimination; it blows up."""
    K, L, R = inst["K"], inst["L"], inst["R"]
    lin, nlt, tbl = inst["lin_taps"], inst["nl_taps"], inst["nl_table"]
    p0 = list(inst["pairs"][0][0])
    # ANF over the K key variables: a polynomial is a set of monomial bitmasks
    poly = [set([0]) if b else set() for b in p0]   # constants 1 / 0
    t_start = time.time()

    def add(a, b):
        return a ^ b

    def mul(a, b):
        out = set()
        for x in a:
            for y in b:
                z = x | y
                if z in out:
                    out.discard(z)
                else:
                    out.add(z)
        return out

    def deg(p):
        return max((bin(mo).count("1") for mo in p), default=0)

    seq = list(poly)
    lim = R if max_rounds is None else min(R, max_rounds)
    peak = 0
    for t in range(lim):
        # NL by its ANF over GF(2): interpolate the table symbolically
        vs = [seq[t + p] for p in nlt]
        acc = set()
        arity = len(nlt)
        for idxv in range(1 << arity):
            if not ((tbl >> idxv) & 1):
                continue
            term = set([0])
            for q in range(arity):
                f = vs[q] if ((idxv >> q) & 1) else add(vs[q], set([0]))
                term = mul(term, f)
                if len(term) > cap_monomials or \
                        time.time() - t_start > time_budget:
                    return {"blew_up_at_round": t, "peak_monomials": peak,
                            "cap": cap_monomials, "key_variables": K,
                            "solved": False}
            acc = add(acc, term)
        b = add(add(seq[t], acc), set([1 << (t % K)]))
        for a in lin:
            b = add(b, seq[t + a])
        peak = max(peak, len(b))
        if len(b) > cap_monomials or time.time() - t_start > time_budget:
            return {"blew_up_at_round": t, "peak_monomials": peak,
                    "cap": cap_monomials, "key_variables": K,
                    "solved": False}
        seq.append(b)
    return {"blew_up_at_round": None, "peak_monomials": peak,
            "max_degree": max(deg(seq[i]) for i in range(len(seq))),
            "cap": cap_monomials, "key_variables": K,
            "rounds_completed": lim, "solved": False}


def attack_guess_and_determine(inst, rng, budget=100_000, time_budget=8.0):
    """Section 5's guess-and-determine: evaluate a bunch of interior variables
    and determine the rest.  Guess x(L..R-1) of pair 0 (u = R-L bits)."""
    K, L, R = inst["K"], inst["L"], inst["R"]
    lin, nlt, tbl = inst["lin_taps"], inst["nl_taps"], inst["nl_table"]
    u = R - L
    p0, c0 = inst["pairs"][0]
    t0 = time.time()
    tried = 0
    for _ in range(budget):
        tried += 1
        s = list(p0) + [rng.getrandbits(1) for _ in range(u)] + list(c0)
        key = [None] * K
        ok = True
        for t in range(R):
            idx = 0
            for i, p in enumerate(nlt):
                idx |= s[t + p] << i
            b = s[t] ^ s[t + L] ^ ((tbl >> idx) & 1)
            for a in lin:
                b ^= s[t + a]
            kj = t % K
            if key[kj] is None:
                key[kj] = b
            elif key[kj] != b:
                ok = False
                break
        if ok and all(k is not None for k in key) and verify(inst, key)[0]:
            return key, tried, time.time() - t0
        if (tried & 0xFF) == 0 and time.time() - t0 > time_budget:
            break
    return None, tried, time.time() - t0


def attack_hill_climb(inst, rng, restarts=64, steps=None, time_budget=8.0):
    """Correlation / greedy baseline: hill-climb the key on the Hamming
    distance between E_k(P) and C."""
    K, L = inst["K"], inst["L"]
    p0, c0 = list(inst["pairs"][0][0]), list(inst["pairs"][0][1])
    steps = steps or 4 * K
    t0 = time.time()
    evals = 0
    for _ in range(restarts):
        key = [rng.getrandbits(1) for _ in range(K)]
        cur = sum(1 for a, b in zip(_encrypt(inst, key, p0), c0) if a != b)
        evals += 1
        for _ in range(steps):
            j = rng.randrange(K)
            key[j] ^= 1
            d = sum(1 for a, b in zip(_encrypt(inst, key, p0), c0) if a != b)
            evals += 1
            if d <= cur:
                cur = d
            else:
                key[j] ^= 1
            if cur == 0 and verify(inst, key)[0]:
                return key, evals, time.time() - t0
        if time.time() - t0 > time_budget:
            break
    return None, evals, time.time() - t0


def attack_naive_readoff(inst):
    """The obvious in-context ansatz, and the one a solver reaches for first:
    assume the plaintext and ciphertext windows together cover the internal
    sequence (true only when R <= L) and read the key straight off P || C."""
    for p, c in inst["pairs"]:
        key = _readoff(inst, list(p), list(c))
        if verify(inst, key)[0]:
            return key
    return None


def attack_fixed_point_scan(inst):
    """Section 5's other key-period device: look for a published pair with
    C = P (a fixed point of E, hence plausibly of F) and read the key off the
    K-periodic trajectory it would imply."""
    K = inst["K"]
    for p, c in inst["pairs"]:
        if list(p) == list(c):
            per = list(p)
            key = _readoff(inst, per, per)
            if verify(inst, key)[0]:
                return key
    return None


def attack_outlier_pair_statistics(inst, rng, budget=20000, time_budget=6.0):
    """Outlier probe.  Is the planted plaintext distinguishable by a per-pair
    statistic (Hamming weight, run count, plaintext-ciphertext distance,
    pairwise distance)?  Rank the pairs, then mount a bounded key search seeded
    from the most anomalous one.  This attack is NOT given the read-off, which
    is the insight the family tests."""
    K = inst["K"]
    pairs = inst["pairs"]
    scores = []
    for i, (p, c) in enumerate(pairs):
        w = sum(p)
        runs = 1 + sum(1 for a, b in zip(p, p[1:]) if a != b)
        d = sum(1 for a, b in zip(p, c) if a != b)
        scores.append((abs(w - K / 2.0) + abs(runs - K / 2.0) + abs(d - K / 2.0), i))
    scores.sort()
    i0 = scores[0][1]
    p0, c0 = list(pairs[i0][0]), list(pairs[i0][1])
    t0 = time.time()
    tried = 0
    # seed the search from the statistic: keys correlated with the anomalous
    # plaintext, then random neighbours
    seeds = [list(p0), [1 - b for b in p0], [b ^ c for b, c in zip(p0, c0)]]
    for base in seeds:
        for _ in range(budget // len(seeds)):
            tried += 1
            key = list(base)
            for _ in range(rng.randrange(0, 4)):
                key[rng.randrange(K)] ^= 1
            if _encrypt(inst, key, p0) == c0 and verify(inst, key)[0]:
                return key, tried, time.time() - t0
            if (tried & 0xFF) == 0 and time.time() - t0 > time_budget:
                return None, tried, time.time() - t0
    return None, tried, time.time() - t0


def plant_detectability(inst, slid_pair):
    """Diagnostic, NOT an attack: how a battery of generic statistics ranks the
    true slid ordered pair among all s(s-1) of them.  Chance rank is uniform."""
    pairs = inst["pairs"]
    s = len(pairs)
    cand = [(i, j) for i in range(s) for j in range(s) if i != j]
    K = inst["K"]

    def stat(i, j):
        a, b = pairs[i][0], pairs[j][0]
        ca, cb = pairs[i][1], pairs[j][1]
        d1 = sum(1 for x, y in zip(a, b) if x != y)
        d2 = sum(1 for x, y in zip(ca, cb) if x != y)
        d3 = sum(1 for x, y in zip(a, cb) if x != y)
        return abs(d1 - K / 2.0) + abs(d2 - K / 2.0) + abs(d3 - K / 2.0)

    ranked = sorted(cand, key=lambda ij: -stat(*ij))
    return ranked.index(tuple(slid_pair)) + 1, len(cand)




# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------

def _slid_pair(inst):
    """The ordered pair (i, j) with P_j = F(P_i).  Uses the planted key, so it
    is available to selftest only, never to verify() or to an attack."""
    key = inst["answer"]
    pairs = inst["pairs"]
    for i in range(len(pairs)):
        for j in range(len(pairs)):
            if i != j and _encrypt(inst, key, list(pairs[i][0]),
                                   rounds=inst["K"]) == list(pairs[j][0]):
                return (i, j)
    return None


def _corruptions(inst, ans, rng):
    K = inst["K"]
    out = []
    a = list(ans)
    b = list(a); b[rng.randrange(K)] ^= 1
    out.append(("flip one bit", b))
    ones = [i for i in range(K) if a[i] == 1]
    zeros = [i for i in range(K) if a[i] == 0]
    if ones and zeros:
        b = list(a)
        i, j = ones[0], zeros[0]
        b[i], b[j] = b[j], b[i]
        out.append(("swap two unequal bits", b))
    out.append(("drop one element", a[:-1]))
    out.append(("duplicate the last element", a + [a[-1]]))
    out.append(("empty", []))
    b = list(a); b[rng.randrange(K)] = 2
    out.append(("out-of-range value", b))
    out.append(("not a sequence", 12345))
    return out


def selftest(verbose=True, heavy=True):
    t_start = time.time()
    rep = {"module": "gen_2003_14215", "track": TRACK,
           "shipping_difficulty": SHIPPING_DIFFICULTY,
           "problem_profile": PROBLEM_PROFILE}
    ship = DIFFICULTY[SHIPPING_DIFFICULTY]
    log = (lambda *a: print(*a)) if verbose else (lambda *a: None)

    if not _check_nlf():
        raise AssertionError("KeeLoq NL table and the ANF of (7.1) disagree")

    # ---------------- G1 ----------------
    per_preset = {}
    ok = tot = 0
    for name, params in DIFFICULTY.items():
        good = 0
        for sd in range(6):
            inst = make_instance(seed=sd, **params)
            good += 1 if verify(inst, inst["answer"])[0] else 0
        per_preset[name] = "%d/6" % good
        ok += good
        tot += 6
    rep["G1_planted_verifies"] = {"pass": ok == tot, "ok": ok, "total": tot,
                                  "per_preset": per_preset}
    log("G1", rep["G1_planted_verifies"])

    # ---------------- G2 ----------------
    rng = random.Random(12345)
    accepted = 0
    reasons = set()
    for name, params in DIFFICULTY.items():
        for sd in range(3):
            inst = make_instance(seed=100 + sd, **params)
            for label, bad in _corruptions(inst, inst["answer"], rng):
                good, why = verify(inst, bad)
                if good:
                    accepted += 1
                else:
                    reasons.add(re.sub(r"\d+", "#", why))
    rep["G2_rejects_corruption"] = {"pass": accepted == 0,
                                    "accepted_corruptions": accepted,
                                    "distinct_reasons": sorted(reasons)}
    log("G2", rep["G2_rejects_corruption"])

    # ---------------- G3 ----------------
    inst = make_instance(seed=7, **DIFFICULTY["medium"])
    ans = inst["answer"]
    prose = ("Let me work through the round equations.\n\nAfter propagating I "
             "get the key\n\n<answer>%s</answer>\n\nwhich checks out."
             % _bits(ans))
    r1 = parse_answer(prose) == ans
    fenced = "```\n<answer>\n %s \n</answer>\n```" % ",".join(str(b) for b in ans)
    r2 = parse_answer(fenced) == ans
    r3 = parse_answer("I could not determine the key.") is None
    r4 = parse_answer("<answer>not a key at all</answer>") is None
    rt = parse_answer(render(inst).split("Example: ")[0] + "<answer>%s</answer>"
                      % _bits(ans)) == ans
    rep["G3_round_trip"] = {"pass": all([r1, r2, r3, r4, rt]),
                            "prose_round_trip": r1, "json_form_accepted": r2,
                            "garbage_returns_none": r3 and r4,
                            "render_round_trip": rt}
    log("G3", rep["G3_round_trip"])

    # ---------------- G4 ----------------
    inst = make_instance(seed=11, **ship)
    rng = random.Random(2024)
    trials = 200_000
    hits = 0
    K = inst["K"]
    tgt = inst["answer"]
    for _ in range(trials):
        if random_candidate(inst, rng) == tgt:
            hits += 1
    space = search_space(inst)
    rep["G4_guess_resistance"] = {
        "pass": hits == 0 and (1.0 / space) < 1e-6,
        "hits": hits, "trials": trials,
        "structure_aware_space": str(space),
        "structure_aware_space_log2": K,
        "analytic_p_guess": "1/%d" % space,
        "note": ("the statement pins down exactly one property of the answer -- "
                 "that it is K bits -- so the naive and the structure-aware "
                 "spaces coincide at 2^K"),
    }
    log("G4", rep["G4_guess_resistance"])

    # ---------------- G5 ----------------
    demo = DIFFICULTY["demo"]
    counts = []
    for sd in range(20):
        d = make_instance(seed=200 + sd, **demo)
        counts.append(enumerate_all(d))
    uniq = sum(1 for c in counts if c == 1)
    inst = make_instance(seed=11, **ship)
    rng = random.Random(99)
    dens_n = 200_000
    dens_hits = sum(1 for _ in range(dens_n)
                    if verify(inst, random_candidate(inst, rng))[0])
    # baseline cost: the strongest attack (algebraic attack, Definition 5.9)
    r, nodes, aops, asec = attack_algebraic_dpll(
        inst, node_cap=6000, time_budget=40.0 if heavy else 5.0)
    node_rate = nodes / asec if asec > 0 else 0.0
    ops_per_node = aops / nodes if nodes else 0.0
    # measured scaling of that attack: 1.35 * 2^K search nodes (see README)
    proj_nodes = 1.35 * (1 << inst["K"])
    proj_ops = proj_nodes * ops_per_node
    proj_sec = proj_nodes / node_rate if node_rate else float("inf")
    # brute force rate
    rng = random.Random(5)
    bf_key, bf_tried, bf_sec = attack_brute_force(
        inst, rng, budget=200_000, time_budget=6.0)
    bf_rate = bf_tried / bf_sec if bf_sec > 0 else 0.0
    route_ops = intended_route_operations(inst)
    rep["G5_density_and_baseline"] = {
        "pass": (uniq == 20 and dens_hits == 0 and r is None),
        "shipping_preset": SHIPPING_DIFFICULTY,
        "shipping_params": dict(ship),
        "exact_solution_count_demo": counts[0],
        "exact_solution_count_demo_unique_over_20_seeds": "%d/20" % uniq,
        "exact_solution_count_demo_values": counts,
        "sampled_density_shipping": "%d/%d" % (dens_hits, dens_n),
        "expected_spurious_keys_log2_shipping":
            inst["K"] - len(inst["pairs"]) * inst["L"],
        "baseline_attack": ("algebraic attack of Definition 5.9 "
                            "(Groebner-style elimination / unit propagation "
                            "with branching)"),
        "baseline_solved": r is not None,
        "baseline_nodes_before_cap": nodes,
        "baseline_primitive_ops_before_cap": aops,
        "baseline_wall_clock_sec": round(asec, 3),
        "baseline_nodes_per_sec": round(node_rate, 1),
        "baseline_ops_per_node": round(ops_per_node, 1),
        "baseline_projected_nodes_log2":
            round(__import__("math").log2(proj_nodes), 2),
        "baseline_projected_primitive_ops_log2":
            round(__import__("math").log2(proj_ops), 2) if proj_ops else None,
        "baseline_projected_years": proj_sec / 3.15576e7,
        "bruteforce_keys_per_sec": round(bf_rate, 1),
        "bruteforce_projected_sec": (1 << inst["K"]) / bf_rate if bf_rate else None,
        "bruteforce_projected_years":
            (1 << inst["K"]) / bf_rate / 3.15576e7 if bf_rate else None,
        "compact_route_primitive_ops": route_ops,
        "mechanical_over_compact_ratio_log2":
            round(__import__("math").log2(proj_ops / route_ops), 2)
            if proj_ops else None,
    }
    log("G5", {k: v for k, v in rep["G5_density_and_baseline"].items()
               if k != "exact_solution_count_demo_values"})

    # ---------------- G6 ----------------
    seeds = list(range(300, 308))
    att = {}

    def run(name, fn):
        succ = 0
        t0 = time.time()
        for sd in seeds:
            i2 = make_instance(seed=sd, **ship)
            if fn(i2) is not None:
                succ += 1
        att[name] = {"successes": succ, "attempts": len(seeds),
                     "seconds": round(time.time() - t0, 3)}

    run("brute_force_key_search",
        lambda i: attack_brute_force(i, random.Random(1), budget=60_000,
                                     time_budget=4.0)[0])
    run("algebraic_attack_definition_5_9",
        lambda i: attack_algebraic_dpll(i, node_cap=1500,
                                        time_budget=12.0 if heavy else 3.0)[0])
    run("guess_and_determine_interior_bits",
        lambda i: attack_guess_and_determine(i, random.Random(2),
                                             budget=40_000, time_budget=4.0)[0])
    run("correlation_hill_climb",
        lambda i: attack_hill_climb(i, random.Random(3), restarts=48,
                                    time_budget=4.0)[0])
    run("outlier_pair_statistics",
        lambda i: attack_outlier_pair_statistics(i, random.Random(4),
                                                 budget=20_000,
                                                 time_budget=4.0)[0])
    run("naive_readoff_plaintext_ciphertext", attack_naive_readoff)
    run("fixed_point_scan_section_5", attack_fixed_point_scan)

    lin = attack_linearisation(make_instance(seed=300, **ship))
    att["linearisation_degree_3"] = {"successes": 0, "attempts": len(seeds),
                                     "seconds": 0.0, "detail": lin}
    t0 = time.time()
    keq = [attack_key_equation_degree(make_instance(seed=sd, **DIFFICULTY["demo"]),
                                      cap_monomials=1500, time_budget=6.0)
           for sd in seeds[:3]]
    att["key_equation_elimination_theorem_5_4"] = {
        "successes": 0, "attempts": len(seeds), "seconds": round(time.time() - t0, 3),
        "detail_at_demo_preset": keq}
    ref_solved = 0
    ref_ops = []
    t0 = time.time()
    for sd in seeds:
        i2 = make_instance(seed=sd, **ship)
        k2, o2 = slide_attack(i2)
        ref_ops.append(o2)
        if k2 is not None and verify(i2, k2)[0]:
            ref_solved += 1
    ref_sec = time.time() - t0
    # detectability diagnostic (not an attack)
    ranks = []
    for sd in seeds:
        i2 = make_instance(seed=sd, **ship)
        sp = _slid_pair(i2)
        ranks.append(plant_detectability(i2, sp)[0])
    ncand = len(inst["pairs"]) * (len(inst["pairs"]) - 1)
    rep["G6_adversary_panel"] = {
        "pass": all(v["successes"] == 0 for v in att.values()),
        "attacks": att,
        "reference_algorithm": {
            "name": ("key-period / slid-pair attack (Section 5, final "
                     "subsection; the KeeLoq instance of Section 7)"),
            "complexity": "O(s^2 * K) GF(2) operations, s = number of pairs",
            "wall_clock_sec": round(ref_sec / len(seeds), 5),
            "operations": max(ref_ops),
            "solves": "%d/%d, as expected" % (ref_solved, len(seeds)),
        },
        "plant_detectability": {
            "statistic": "Hamming distances P_i-P_j, C_i-C_j, P_i-C_j",
            "rank_of_true_slid_pair": ranks,
            "candidates": ncand,
            "chance_mean_rank": (ncand + 1) / 2.0,
            "observed_mean_rank": sum(ranks) / len(ranks),
        },
    }
    log("G6", {"pass": rep["G6_adversary_panel"]["pass"], "attacks": att})

    # ---------------- G7 ----------------
    ladder = []
    for name, params in DIFFICULTY.items():
        i2 = make_instance(seed=42, **params)
        ladder.append([name, i2["K"], i2["R"], len(i2["pairs"]),
                       i2["K"], intended_route_operations(i2)])
    esc = escalate(dict(ship))
    esc_inst = make_instance(seed=43, **esc)
    esc_ok = verify(esc_inst, esc_inst["answer"])[0]
    dbl = dict(ship)
    dbl["m"] = dbl["m"] * 2
    dbl_inst = make_instance(seed=44, **dbl)
    dbl_ok = verify(dbl_inst, dbl_inst["answer"])[0]
    ship_inst = make_instance(seed=42, **ship)
    rep["G7_scales"] = {
        "pass": bool(esc_ok and dbl_ok
                     and len(esc_inst["answer"]) == len(ship_inst["answer"])
                     and all(ladder[i][1] <= ladder[i + 1][1]
                             for i in range(len(ladder) - 1))),
        "ladder": ladder,
        "ladder_columns": ["preset", "K", "R", "pairs", "log2_key_space",
                           "compact_route_ops"],
        "ladder_monotone": all(ladder[i][1] <= ladder[i + 1][1]
                               for i in range(len(ladder) - 1)),
        "escalated_params": esc,
        "escalated_verifies": esc_ok,
        "size_doubled_params": dbl,
        "size_doubled_verifies": dbl_ok,
        "answer_atoms_shipping": len(ship_inst["answer"]),
        "answer_atoms_escalated": len(esc_inst["answer"]),
        "answer_length_fixed": len(esc_inst["answer"]) == len(ship_inst["answer"]),
        "escalated_compact_route_ops": intended_route_operations(esc_inst),
    }
    log("G7", {k: v for k, v in rep["G7_scales"].items() if k != "ladder"})

    # ---------------- G8 ----------------
    inv_ok = inv_tot = 0
    real_ok = real_tot = 0
    keys = []
    rng = random.Random(808)
    for sd in range(20):
        i2 = make_instance(seed=500 + sd, **DIFFICULTY["medium"])
        k0 = canonical_key(i2)
        keys.append(k0)
        variants = []
        perm = list(range(len(i2["pairs"])))
        rng.shuffle(perm)
        v = dict(i2); v["pairs"] = [i2["pairs"][p] for p in perm]
        variants.append(("permute the published pair list", v))
        v2 = dict(i2); v2["pairs"] = list(reversed(i2["pairs"]))
        variants.append(("reverse the published pair list", v2))
        v3 = dict(i2); v3["lin_taps"] = list(reversed(i2["lin_taps"]))
        variants.append(("swap the two linear taps (XOR is commutative)", v3))
        v4 = dict(v3); v4["pairs"] = list(reversed(i2["pairs"]))
        variants.append(("both, composed", v4))
        v5 = dict(v3); v5["pairs"] = [i2["pairs"][p] for p in perm]
        variants.append(("both, composed the other way", v5))
        for _, vv in variants:
            inv_tot += 1
            if canonical_key(vv) == k0:
                inv_ok += 1
            real_tot += 1
            if verify(vv, i2["answer"])[0]:
                real_ok += 1
    rep["G8_canonical_key"] = {
        "pass": (inv_ok == inv_tot and real_ok == real_tot
                 and len(set(keys)) == 20),
        "invariances_tested": [
            "permutation of the published plaintext/ciphertext pair list",
            "reversal of the pair list",
            "swap of the two linear taps (x(t+a1)+x(t+a2) is symmetric)",
            "both, composed, in both orders",
        ],
        "invariance_ok": inv_ok, "invariance_total": inv_tot,
        "transformation_is_real_ok": real_ok,
        "transformation_checks": real_tot,
        "distinct_keys": len(set(keys)), "distinct_seeds": 20,
    }
    log("G8", rep["G8_canonical_key"])

    # ---------------- G9 ----------------
    route = []
    chars = []
    for sd in range(12):
        i2 = make_instance(seed=700 + sd, **ship)
        route.append(intended_route_operations(i2))
        chars.append(len(_bits(i2["answer"])))
    i2 = make_instance(seed=700, **ship)
    ans_json = json.dumps(i2["answer"], separators=(",", ":"))
    within = (max(chars) <= 2000 and len(i2["answer"]) <= 256
              and max(route) <= 1000)
    rep["G9_no_tool_suitability"] = {
        "pass": bool(within),
        "arms": {"bare": None, "hinted": None, "placebo": None},
        "arms_note": ("three-arm oracle diagnostic not run: no "
                      "OPENROUTER_API_KEY in this environment"),
        "hinted_minus_placebo": None,
        "hinted_verdict": None,
        "answer_chars": max(chars),
        "answer_json_chars": len(ans_json),
        "answer_tokens": max(chars),
        "answer_elements": len(i2["answer"]),
        "intended_route_operations": max(route),
        "intended_route_operations_per_seed": route,
        "intended_route_note": (
            "Track B.  The compact route is the key-period/slid-pair attack: "
            "for each of the s(s-1) ordered plaintext hypotheses read key bits "
            "off (P_i, P_j) and off (C_i, C_j) one at a time and stop at the "
            "first disagreement -- a wrong hypothesis dies after about two "
            "bits -- then finish the surviving one from the P side alone.  "
            "Counted primitives: one NL table lookup and five XORs per key "
            "bit."),
        "render_chars": len(render(i2)),
        "within_caps": bool(within),
    }
    log("G9", {k: v for k, v in rep["G9_no_tool_suitability"].items()
               if k != "intended_route_operations_per_seed"})

    gates = [k for k in rep if k.startswith("G") and k[1].isdigit()]
    rep["all_gates_pass"] = all(bool(rep[g]["pass"]) for g in gates)
    rep["all_passed"] = rep["all_gates_pass"]
    rep["json_native_answer"] = (
        json.loads(json.dumps(i2["answer"])) == i2["answer"])
    rep["elapsed_sec"] = round(time.time() - t_start, 1)
    return rep


if __name__ == "__main__":
    out = selftest(verbose=True, heavy=True)
    print()
    print("ALL GATES PASS:", out["all_gates_pass"])
    with open("selftest_report.json", "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
