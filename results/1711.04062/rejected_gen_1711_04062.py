"""Archived supersingular 2-isogeny-path generator for arXiv:1711.04062.

The paper defines the isogeny-path problem and the CGL non-backtracking hash
walk on supersingular isogeny graphs.  This module inverse-generates one such
walk over F_(p^2), retaining each order-two kernel root.  The endpoint is
computed from the retained path; generation never recovers a path from two
endpoints.

Everything is exact and standard-library-only.  Field elements are pairs
``(a,b)`` representing ``a + b*i`` with ``i^2 = -1`` modulo a Mersenne prime
``p == 3 (mod 4)``.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import os
import random
import re
import statistics
import time
from typing import Any


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "number_theory",
    "object_regime": "finite_field",
    "computational_core": "other",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "supersingular elliptic curves over F_(p^2)",
        "cyclic kernels of separable degree-2 isogenies",
        "a non-backtracking isogeny walk",
    ],
    "verification_operations": [
        "exact arithmetic in F_(p^2)",
        "substitution in the 2-torsion polynomial",
        "exact degree-2 quotient recurrence",
        "coefficient comparison of elliptic-curve models",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "search pruning",
    "intuition_description": (
        "Meet a forward and a reverse non-backtracking isogeny frontier in the "
        "middle; without that collision structure, direct replay examines the "
        "full binary tree of kernel choices."
    ),
    "hardness_basis": (
        "Archived Track A candidate: Section 11, Theorem 47 proves expansion for "
        "the graph on supersingular j-invariants and Sections 12 and 14.2 give "
        "exponential meet-in-the-middle attacks, but this implementation asks for "
        "an exact coordinate-normalized target model rather than a j-invariant; "
        "the paper therefore does not establish hardness for the generated lift."
    ),
    "max_answer_tokens": 400,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 4, "mersenne_exponent": 5},
    "easy": {"n": 58, "mersenne_exponent": 61},
    "medium": {"n": 59, "mersenne_exponent": 61},
    "hard": {"n": 60, "mersenne_exponent": 61},
}

SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "A useful collision is between equal curve models on forward and reverse "
    "non-backtracking isogeny frontiers."
)
PLACEBO_HINT = (
    "Careful bookkeeping is useful when working through the displayed finite-"
    "field curve data."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON array of exactly e lowercase base-36 strings.  Each string "
        "canonically encodes one F_(p^2) x-coordinate a+b*i as the integer "
        "a+p*b; the first coordinate is any 2-torsion root and every later "
        "coordinate is one of the two nonzero roots, so the walk never "
        "immediately follows a dual edge."
    ),
    "bounds": {
        "path_length": "e=n",
        "first_kernel_choices": 3,
        "later_kernel_choices": 2,
        "field_code_min": 0,
        "field_code_max": "p^2-1",
        "max_shipping_atomic_elements": 58,
    },
}


NOTES = r"""
Paper grounding (Step 0).  Section 2 defines an isogeny as a nonconstant
algebraic group map with finite kernel.  Section 9 defines isogeny-graph
vertices to be j-invariants, with prime-degree isogenies as edges.  Section 11,
Theorem 47 says that, for distinct primes p and l, the supersingular
l-isogeny graph over the algebraic closure is connected, (l+1)-regular and
Ramanujan.  We use l=2.  Section 12, Problem 3 defines the isogeny-path problem
and states that only algorithms exponential in log(#E) are known in general;
it gives the birthday/meet-in-the-middle strategy.  Section 13 defines CGL as
a non-backtracking walk and its preimage problem as path finding.  Section
14.2 states more precisely that a hidden walk of degree l^e is recovered by
meet-in-the-middle in O(l^(e/2)) time and storage, and observes that a
non-backtracking l-walk has a cyclic kernel of order l^e.

Exact object and construction.  Vertices here are actual Weierstrass models
over F_(p^2), not an adjacency matrix.  Starting from the supersingular curve
y^2=x^3+x (supersingular for p=3 mod 4), one fixed 2-isogeny gives the public
start model y^2=x^3-6*i*x^2-x.  At each generated step a uniformly chosen
2-torsion root t is retained, with t=0 excluded after the first step because it
is the dual kernel.  For x=X+t, write
  y^2 = X^3 + A X^2 + B X,
where A=3t+a2 and B=3t^2+2*a2*t+a4.  The standard degree-2 quotient is
  y^2 = x^3 - 2A x^2 + (A^2-4B)x.
For nonzero t, using t^2+a2*t+a4=0, the same quotient simplifies exactly to
  a2'=-6*t-2*a2,  a4'=a2^2+a2*t-a4.
Those identities are the construction and the executable certificate check.

What makes it easy, and what was avoided.  The Section 12 "Isogeny
computation" problem is easy when its kernel is supplied: Velu's formulas cost
quasi-linear time in the kernel size.  The "Explicit isogeny" problem with
known small degree has O(d^2) or O(d^3) algorithms.  Neither is our search
problem: only the endpoints and length are public.  Ordinary l-isogeny graphs
are volcanoes with rigid ascending/descending structure (Section 9), so this
module instead uses the supersingular regime of Section 11.  It deliberately
omits the auxiliary torsion-point images published by SIDH: modern attacks
break that extra-data distribution, not the generic endpoint-only path
problem generated here.

Archive finding.  The paper's hard graph is on j-invariants, whereas verify()
requires equality with the exact Weierstrass model selected by this module's
coordinate normalization.  canonical_key() then quotients those exact-model
instances by j-invariant even though verify() does not.  Repairing verification
to accept the target up to isomorphism restores the paper's object, but it does
not produce a no-tool route: after recognizing meet-in-the-middle, a solver
still performs about 2^(e/2) frontier expansions.  At e=58 this is at least
536,870,912 candidate-side expansions, far above G9(c)'s 300-operation cap.

Attacks.  Plants and random candidates use exactly the same three-then-two
kernel distribution.  The outlier attack always takes the smallest kernel;
the greedy attack picks the child whose displayed coefficients look closest
to the target; random restart samples the exact certificate language.  The
domain attack implements the paper's meet-in-the-middle idea using both the
forward quotient recurrence and its exact reverse recurrence, but caps each
frontier far below the complete 3*2^(floor(e/2)-1) and 2^ceil(e/2) frontiers.
All measured attack outcomes, node counts and times are in selftest_report.
"""


# Known Mersenne-prime exponents used by the fixed ladder and G7.
_MERSENNE_EXPONENTS = {5, 7, 13, 17, 19, 31, 61, 89, 107, 127, 521}
_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"
_BASE36_RE = re.compile(r"^[0-9a-z]+$")
_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer>", re.I | re.S)

# These fields are filled from the script-owned oracle artifacts after the
# three arms are run.  They are diagnostic only; G9 passes solely on the caps.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


# ---------------------------------------------------------------------------
# Exact F_(p^2) arithmetic, represented internally by two Python integers.


def _f(x: Any, p: int) -> tuple[int, int]:
    """Return a canonical internal field pair."""
    return (int(x[0]) % p, int(x[1]) % p)


def _add(x: tuple[int, int], y: tuple[int, int], p: int) -> tuple[int, int]:
    return ((x[0] + y[0]) % p, (x[1] + y[1]) % p)


def _sub(x: tuple[int, int], y: tuple[int, int], p: int) -> tuple[int, int]:
    return ((x[0] - y[0]) % p, (x[1] - y[1]) % p)


def _neg(x: tuple[int, int], p: int) -> tuple[int, int]:
    return ((-x[0]) % p, (-x[1]) % p)


def _mul(x: tuple[int, int], y: tuple[int, int], p: int) -> tuple[int, int]:
    return ((x[0] * y[0] - x[1] * y[1]) % p,
            (x[0] * y[1] + x[1] * y[0]) % p)


def _scale(k: int, x: tuple[int, int], p: int) -> tuple[int, int]:
    return ((k * x[0]) % p, (k * x[1]) % p)


def _square(x: tuple[int, int], p: int) -> tuple[int, int]:
    return ((x[0] * x[0] - x[1] * x[1]) % p,
            (2 * x[0] * x[1]) % p)


def _inv(x: tuple[int, int], p: int) -> tuple[int, int]:
    den = (x[0] * x[0] + x[1] * x[1]) % p
    if den == 0:
        raise ZeroDivisionError("zero in F_(p^2)")
    dinv = pow(den, p - 2, p)
    return ((x[0] * dinv) % p, (-x[1] * dinv) % p)


def _div(x: tuple[int, int], y: tuple[int, int], p: int) -> tuple[int, int]:
    return _mul(x, _inv(y, p), p)


def _pow(x: tuple[int, int], e: int, p: int) -> tuple[int, int]:
    out = (1, 0)
    base = x
    while e:
        if e & 1:
            out = _mul(out, base, p)
        base = _square(base, p)
        e >>= 1
    return out


def _fp_sqrt(a: int, p: int) -> int | None:
    """Square root in F_p for p=3 mod 4, with a canonical sign."""
    a %= p
    if a == 0:
        return 0
    if pow(a, (p - 1) // 2, p) != 1:
        return None
    r = pow(a, (p + 1) // 4, p)
    return min(r, (-r) % p)


def _sqrt(x: tuple[int, int], p: int) -> tuple[int, int] | None:
    """A deterministic square root in F_(p^2), or None.

    The direct formula is valid because p=3 mod 4.  Choosing the smaller of a
    root and its negative makes every transition deterministic.
    """
    a, b = x
    if a == 0 and b == 0:
        return (0, 0)
    if b == 0:
        r = _fp_sqrt(a, p)
        if r is not None:
            roots = [(r, 0), ((-r) % p, 0)]
            return min(roots)
        r = _fp_sqrt(-a, p)
        if r is None:
            return None
        roots = [(0, r), (0, (-r) % p)]
        return min(roots)

    norm = (a * a + b * b) % p
    # Every call made by the walk is on a promised square.  Its norm is
    # therefore a square in F_p; avoid a redundant Euler-criterion power.
    norm_root = pow(norm, (p + 1) // 4, p)
    if (norm_root * norm_root) % p != norm:
        return None
    inv2 = (p + 1) // 2
    for alpha in (norm_root, (-norm_root) % p):
        c2 = ((a + alpha) * inv2) % p
        if c2 == 0 or pow(c2, (p - 1) // 2, p) != 1:
            continue
        c = pow(c2, (p + 1) // 4, p)
        d = (b * pow(2 * c, p - 2, p)) % p
        root = (c, d)
        if _square(root, p) == x:
            return min(root, _neg(root, p))
    return None


def _conj(x: tuple[int, int], p: int) -> tuple[int, int]:
    return (x[0], (-x[1]) % p)


def _zero(x: tuple[int, int]) -> bool:
    return x[0] == 0 and x[1] == 0


# ---------------------------------------------------------------------------
# Encoding and elliptic-curve/isogeny recurrences.


def _to_base36(value: int) -> str:
    if value == 0:
        return "0"
    chars = []
    while value:
        value, digit = divmod(value, 36)
        chars.append(_BASE36[digit])
    return "".join(reversed(chars))


def _from_base36(text: str) -> int:
    if not isinstance(text, str) or not _BASE36_RE.fullmatch(text):
        raise ValueError("not canonical lowercase base36")
    if len(text) > 1 and text[0] == "0":
        raise ValueError("leading zero")
    return int(text, 36)


def _encode(x: tuple[int, int], p: int) -> str:
    return _to_base36(x[0] + p * x[1])


def _decode(text: str, p: int) -> tuple[int, int]:
    value = _from_base36(text)
    if value >= p * p:
        raise OverflowError("outside field")
    return (value % p, value // p)


def _curve_key(curve: tuple[tuple[int, int], tuple[int, int]]) -> tuple[int, ...]:
    a2, a4 = curve
    return (a2[0], a2[1], a4[0], a4[1])


def _nonsingular(curve: tuple[tuple[int, int], tuple[int, int]], p: int) -> bool:
    # For y^2=x(x^2+a2*x+a4): Delta=16*a4^2*(a2^2-4*a4).
    a2, a4 = curve
    disc = _sub(_square(a2, p), _scale(4, a4, p), p)
    return not _zero(a4) and not _zero(disc)


def _roots(curve: tuple[tuple[int, int], tuple[int, int]], p: int,
           allow_zero: bool) -> list[tuple[int, int]]:
    """Return the three roots, or the two roots excluding the dual root 0."""
    a2, a4 = curve
    disc = _sub(_square(a2, p), _scale(4, a4, p), p)
    s = _sqrt(disc, p)
    if s is None:
        raise ArithmeticError("2-torsion did not split over F_(p^2)")
    inv2 = (p + 1) // 2
    r1 = _scale(inv2, _sub(_neg(a2, p), s, p), p)
    r2 = _scale(inv2, _add(_neg(a2, p), s, p), p)
    nonzero = sorted((r1, r2))
    if _zero(nonzero[0]) or _zero(nonzero[1]) or nonzero[0] == nonzero[1]:
        raise ArithmeticError("singular or repeated 2-torsion roots")
    return sorted([(0, 0)] + nonzero) if allow_zero else nonzero


def _is_root(curve: tuple[tuple[int, int], tuple[int, int]],
             t: tuple[int, int], p: int) -> bool:
    if _zero(t):
        return True
    a2, a4 = curve
    return _zero(_add(_add(_square(t, p), _mul(a2, t, p), p), a4, p))


def _advance(curve: tuple[tuple[int, int], tuple[int, int]],
             t: tuple[int, int], p: int
             ) -> tuple[tuple[int, int], tuple[int, int]]:
    """Exact degree-2 quotient by the point (t,0)."""
    a2, a4 = curve
    if _zero(t):
        # The simplification below divides the root equation by t.  The first
        # step alone may use t=0, so retain the unsimplified special case.
        out = (
            _scale(-2, a2, p),
            _sub(_square(a2, p), _scale(4, a4, p), p),
        )
    else:
        a2t = _mul(a2, t, p)
        out = (
            _sub(_scale(-6, t, p), _scale(2, a2, p), p),
            _sub(_add(_square(a2, p), a2t, p), a4, p),
        )
    if not _nonsingular(out, p):
        raise ArithmeticError("quotient unexpectedly singular")
    return out


def _predecessors(curve: tuple[tuple[int, int], tuple[int, int]], p: int
                  ) -> list[tuple[tuple[tuple[int, int], tuple[int, int]],
                                  tuple[int, int]]]:
    """Two exact non-backtracking predecessors (source curve, source kernel)."""
    c, d = curve
    inv2 = (p + 1) // 2
    aa = _scale(-inv2, c, p)  # A=-c/2
    s = _sqrt(d, p)
    if s is None:
        return []
    out = []
    for signed in (s, _neg(s, p)):
        t = _scale(inv2, _sub(aa, signed, p), p)
        if _zero(t):
            continue
        src_a2 = _sub(aa, _scale(3, t, p), p)
        src_a4 = _sub(_scale(2, _square(t, p), p), _mul(aa, t, p), p)
        src = (src_a2, src_a4)
        if (_nonsingular(src, p) and _is_root(src, t, p)
                and _advance(src, t, p) == curve):
            out.append((src, t))
    # At a nonexceptional vertex there are two; de-duplicate defensively.
    unique = {}
    for src, t in out:
        unique[(_curve_key(src), t)] = (src, t)
    return [unique[k] for k in sorted(unique)]


def _start_curve(p: int) -> tuple[tuple[int, int], tuple[int, int]]:
    # Quotient y^2=x^3+x by the kernel x=i.  This is supersingular because
    # p=3 mod 4 and supersingularity is invariant under isogeny.
    return ((0, (-6) % p), ((-1) % p, 0))


def _walk_from_choices(p: int, n: int, first: int, bits: list[int],
                       start: tuple[tuple[int, int], tuple[int, int]] | None = None
                      ) -> tuple[list[str], tuple[tuple[int, int], tuple[int, int]]]:
    curve = _start_curve(p) if start is None else start
    answer = []
    for step in range(n):
        roots = _roots(curve, p, allow_zero=(step == 0))
        index = first if step == 0 else bits[step - 1]
        t = roots[index]
        answer.append(_encode(t, p))
        curve = _advance(curve, t, p)
    return answer, curve


def _random_walk(p: int, n: int, rng: random.Random,
                 start: tuple[tuple[int, int], tuple[int, int]] | None = None
                ) -> tuple[list[str], tuple[tuple[int, int], tuple[int, int]]]:
    first = rng.randrange(3)
    bits = [rng.randrange(2) for _ in range(max(0, n - 1))]
    return _walk_from_choices(p, n, first, bits, start=start)


def _sample_density(inst: dict, total: int, rng: random.Random,
                    suffix_depth: int = 17) -> tuple[int, dict]:
    """Exactly test uniform random paths using a shared-prefix/reverse split.

    This samples the same first-trit/following-bit representation used by
    ``random_candidate``.  Reverse enumeration records precisely which suffix
    bit strings reach the target.  Sorted sampled prefixes are then replayed
    through a trie, so common work is performed once without changing a single
    sampled candidate or endpoint test.
    """
    p = inst["p"]
    n = inst["n"]
    suffix_depth = min(suffix_depth, n - 1)
    prefix_depth = n - suffix_depth
    suffix_mask = (1 << suffix_depth) - 1
    sampled: dict[int, dict[int, int]] = {}
    for _ in range(total):
        first = rng.randrange(3)
        tail = rng.getrandbits(n - 1)
        prefix_tail = tail >> suffix_depth
        suffix = tail & suffix_mask
        prefix = (first << (prefix_depth - 1)) | prefix_tail
        bucket = sampled.setdefault(prefix, {})
        bucket[suffix] = bucket.get(suffix, 0) + 1

    target = _internal_curve(inst["target_curve"], p)
    reverse: dict[tuple[int, ...], set[int]] = {}
    reverse_nodes = 0

    def reverse_dfs(curve, depth, suffix_value):
        nonlocal reverse_nodes
        reverse_nodes += 1
        if depth == suffix_depth:
            reverse.setdefault(_curve_key(curve), set()).add(suffix_value)
            return
        for source, kernel in _predecessors(curve, p):
            roots = _roots(source, p, allow_zero=False)
            bit = roots.index(kernel)
            # A newly prepended bit occupies position ``depth`` from the right
            # once recursion reaches the split point.
            reverse_dfs(source, depth + 1,
                        suffix_value | (bit << depth))

    reverse_dfs(target, 0, 0)

    def prefix_digits(code: int) -> tuple[int, ...]:
        first = code >> (prefix_depth - 1)
        rest = code & ((1 << (prefix_depth - 1)) - 1)
        return (first,) + tuple(
            (rest >> shift) & 1
            for shift in range(prefix_depth - 2, -1, -1)
        )

    start = _internal_curve(inst["start_curve"], p)
    previous: tuple[int, ...] = ()
    stack = [start]  # stack[d] is the curve after d prefix digits.
    prefix_nodes = 0
    hits = 0
    witnessed_hit = None
    for prefix in sorted(sampled):
        digits = prefix_digits(prefix)
        lcp = 0
        limit = min(len(previous), len(digits))
        while lcp < limit and previous[lcp] == digits[lcp]:
            lcp += 1
        del stack[lcp + 1:]
        curve = stack[-1]
        for depth in range(lcp, prefix_depth):
            roots = _roots(curve, p, allow_zero=(depth == 0))
            curve = _advance(curve, roots[digits[depth]], p)
            stack.append(curve)
            prefix_nodes += 1
        suffixes = reverse.get(_curve_key(curve), set())
        for suffix, multiplicity in sampled[prefix].items():
            if suffix in suffixes:
                hits += multiplicity
                if witnessed_hit is None:
                    tail_bits = [
                        (suffix >> shift) & 1
                        for shift in range(suffix_depth - 1, -1, -1)
                    ]
                    witnessed_hit = (digits, tail_bits)
        previous = digits

    if witnessed_hit is not None:
        digits, tail_bits = witnessed_hit
        candidate, endpoint = _walk_from_choices(
            p, n, digits[0], list(digits[1:]) + tail_bits,
            start=_internal_curve(inst["start_curve"], p),
        )
        if endpoint != target or not verify(inst, candidate)[0]:
            raise AssertionError("split density hit did not verify")
    return hits, {
        "prefix_depth": prefix_depth,
        "suffix_depth": suffix_depth,
        "unique_sampled_prefixes": len(sampled),
        "shared_prefix_nodes": prefix_nodes,
        "reverse_nodes": reverse_nodes,
        "reverse_frontier_states": len(reverse),
    }


def _public_curve(curve: tuple[tuple[int, int], tuple[int, int]]) -> dict:
    return {"a2": [curve[0][0], curve[0][1]],
            "a4": [curve[1][0], curve[1][1]]}


def _internal_curve(data: dict, p: int
                   ) -> tuple[tuple[int, int], tuple[int, int]]:
    return (_f(data["a2"], p), _f(data["a4"], p))


def make_instance(n: int, seed: int = 0, mersenne_exponent: int = 61,
                  **params: Any) -> dict:
    """Inverse-generate a non-backtracking supersingular 2-isogeny path."""
    del params
    if not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer path length")
    if mersenne_exponent not in _MERSENNE_EXPONENTS:
        raise ValueError("mersenne_exponent must name a supported known prime")
    p = (1 << mersenne_exponent) - 1
    if p % 4 != 3:
        raise ValueError("the selected prime must be 3 modulo 4")
    rng = random.Random(seed)
    answer, target = _random_walk(p, n, rng)
    start = _start_curve(p)
    inst = {
        "family": "supersingular_nonbacktracking_2_isogeny_path",
        "n": n,
        "p": p,
        "mersenne_exponent": mersenne_exponent,
        "field_nonresidue": -1,
        "start_curve": _public_curve(start),
        "target_curve": _public_curve(target),
        "answer": answer,
    }
    # The answer is deliberately JSON-native; assert this at construction time.
    assert json.loads(json.dumps(answer)) == answer
    return inst


def _fmt_fp2(pair: list[int] | tuple[int, int]) -> str:
    return f"[{int(pair[0])},{int(pair[1])}]"


def render(inst: dict) -> str:
    """Render the complete standalone problem statement."""
    p = inst["p"]
    n = inst["n"]
    s = inst["start_curve"]
    t = inst["target_curve"]
    statement = f"""Find a non-backtracking path of {n} degree-2 isogenies.

All arithmetic is exact in the finite field F_(p^2), where
  p = {p}
and i^2 = -1.  Represent a field element as [a,b], meaning a+b*i, with
0 <= a,b < p.  Add componentwise modulo p and multiply by
  [a,b]*[c,d] = [(a*c-b*d) mod p, (a*d+b*c) mod p].

Every curve in this problem has the model
  E(a2,a4): y^2 = x^3 + a2*x^2 + a4*x
over F_(p^2).  The starting curve is
  a2 = {_fmt_fp2(s['a2'])}
  a4 = {_fmt_fp2(s['a4'])}
and the required final curve is exactly the displayed model
  a2 = {_fmt_fp2(t['a2'])}
  a4 = {_fmt_fp2(t['a4'])}.

A step is specified by the x-coordinate t=[u,v] of a nonzero point (t,0)
of order 2, except that t=0 is also allowed on the first step.  Thus t must
satisfy t*(t^2+a2*t+a4)=0.  Immediate backtracking is forbidden: after the
first step, t must never be 0, because x=0 is the kernel of the dual isogeny.

To replay a nonzero-kernel step, first check t^2+a2*t+a4=0, then replace
the curve by the exact degree-2 quotient model
  a2 := -6*t - 2*a2
  a4 := a2^2 + a2*t - a4
(the right-hand side uses the old coefficients).  For the exceptional value
t=0, allowed only on step 1, instead use a2 := -2*a2 and
a4 := a2^2-4*a4.
with all operations in F_(p^2).  Supply exactly {n} kernel coordinates and
the replayed model after step {n} must equal the required final model above.

Encode each t=[u,v] canonically as follows: form z=u+p*v, then write z in
lowercase base 36 using digits 0-9 and letters a-z, with no leading zero
(zero itself is "0").  Your answer is a JSON array of exactly {n} such
strings, in path order.  Order matters and repetitions are permitted when
they happen to be valid on their respective current curves.

Give your final answer inside <answer></answer> tags, as one JSON array of
lowercase base-36 strings.
Example syntax for a three-step instance: <answer>["0","2f","a1"]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: Any) -> object | None:
    """Parse a JSON path from tags, a Markdown fence, or surrounding prose."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    candidates = [match.group(1).strip()] if match else []
    candidates.extend(m.group(1).strip() for m in re.finditer(
        r"```(?:json)?\s*(.*?)```", text, re.I | re.S
    ))
    # A conservative prose fallback: answer arrays contain strings and no
    # nested arrays, so the first bracketed block is unambiguous.
    candidates.extend(m.group(0) for m in re.finditer(r"\[[^\[\]]*\]", text, re.S))
    for raw in candidates:
        try:
            value = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            continue
        if any(not _BASE36_RE.fullmatch(x) or (len(x) > 1 and x[0] == "0")
               for x in value):
            continue
        return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid kernel path without consulting ``inst['answer']``."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if not answer:
        return False, "answer path is empty"
    if len(answer) != inst["n"]:
        return False, f"path length is {len(answer)}, expected {inst['n']}"
    if not all(isinstance(code, str) for code in answer):
        return False, "every kernel code must be a string"

    p = inst["p"]
    try:
        curve = _internal_curve(inst["start_curve"], p)
        target = _internal_curve(inst["target_curve"], p)
    except (KeyError, TypeError, ValueError):
        return False, "malformed instance curve data"

    previous_code = None
    for step, code in enumerate(answer):
        try:
            t = _decode(code, p)
        except ValueError:
            return False, f"kernel code at step {step + 1} is not canonical lowercase base36"
        except OverflowError:
            return False, f"kernel code at step {step + 1} lies outside F_(p^2)"

        if step > 0 and _zero(t):
            return False, f"path backtracks through the dual kernel at step {step + 1}"
        if not _is_root(curve, t, p):
            if previous_code == code:
                return False, f"duplicated kernel code is not a root at step {step + 1}"
            if step == 0:
                return False, "initial kernel is not a 2-torsion root"
            return False, f"kernel is not a 2-torsion root at step {step + 1}"
        try:
            curve = _advance(curve, t, p)
        except ArithmeticError as exc:
            return False, f"invalid quotient at step {step + 1}: {exc}"
        previous_code = code

    if curve != target:
        return False, "replayed path ends at a different curve model"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the stated three-then-two path language."""
    answer, _ = _random_walk(
        inst["p"], inst["n"], rng,
        start=_internal_curve(inst["start_curve"], inst["p"]),
    )
    return answer


def search_space(inst: dict) -> int:
    """Number of syntactically and structurally valid non-backtracking paths."""
    return 3 * (1 << (inst["n"] - 1))


def enumerate_all(inst: dict) -> int | None:
    """Count endpoint-reaching paths exactly when at most 200,000 exist."""
    space = search_space(inst)
    if space > 200_000:
        return None
    p = inst["p"]
    target = _internal_curve(inst["target_curve"], p)
    hits = 0
    for first in range(3):
        for mask in range(1 << max(0, inst["n"] - 1)):
            bits = [(mask >> k) & 1 for k in range(inst["n"] - 1)]
            _, endpoint = _walk_from_choices(
                p, inst["n"], first, bits,
                start=_internal_curve(inst["start_curve"], p),
            )
            if endpoint == target:
                hits += 1
    return hits


def _j_invariant(curve: tuple[tuple[int, int], tuple[int, int]], p: int
                ) -> tuple[int, int]:
    """j for y^2=x^3+a2*x^2+a4*x (a1=a3=a6=0)."""
    a2, a4 = curve
    b2 = _scale(4, a2, p)
    b4 = _scale(2, a4, p)
    b8 = _neg(_square(a4, p), p)
    c4 = _sub(_square(b2, p), _scale(24, b4, p), p)
    delta = _sub(_neg(_mul(_square(b2, p), b8, p), p),
                 _scale(8, _mul(_square(b4, p), b4, p), p), p)
    if _zero(delta):
        raise ZeroDivisionError("singular curve")
    return _div(_mul(_square(c4, p), c4, p), delta, p)


def canonical_key(inst: dict) -> str:
    """Key on ordered endpoint j-invariants, modulo F_p conjugation."""
    p = inst["p"]
    start_j = _j_invariant(_internal_curve(inst["start_curve"], p), p)
    target_j = _j_invariant(_internal_curve(inst["target_curve"], p), p)
    pair = (start_j, target_j)
    conjugate = (_conj(start_j, p), _conj(target_j, p))
    normalized = min(pair, conjugate)
    payload = {
        "family": inst["family"],
        "p": p,
        "n": inst["n"],
        "ordered_j_pair": normalized,
        "nonbacktracking": True,
        "degree": 2,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the path/search tree while keeping each kernel a single atom."""
    n = int(params.get("n", 1))
    exponent = int(params.get("mersenne_exponent", 61))
    # At exponent 61, 60 path atoms remain within the measured answer cap.
    if exponent == 61 and n < 60:
        return {"n": min(60, n + 4), "mersenne_exponent": 61}
    # Raising the field together with the walk would make the exact witness
    # exceed the 2,000-character/approximately-500-token budget.
    return "cap_bound"


# ---------------------------------------------------------------------------
# Construction-aware attacks.


def _path_by_rule(inst: dict, rule: str) -> list[str]:
    p = inst["p"]
    curve = _internal_curve(inst["start_curve"], p)
    target = _internal_curve(inst["target_curve"], p)
    answer = []
    for step in range(inst["n"]):
        options = []
        for t in _roots(curve, p, allow_zero=(step == 0)):
            child = _advance(curve, t, p)
            if rule == "smallest":
                score = int(_encode(t, p), 36)
            elif rule == "largest":
                score = -int(_encode(t, p), 36)
            else:
                ck = _curve_key(child)
                tk = _curve_key(target)
                score = sum(abs(a - b) for a, b in zip(ck, tk))
            options.append((score, t, child))
        _, chosen, curve = min(options, key=lambda row: (row[0], row[1]))
        answer.append(_encode(chosen, p))
    return answer


def _mitm_attack(inst: dict, leaf_cap_each: int = 2048
                ) -> tuple[list[str] | None, dict]:
    """Capped exact bidirectional search using the paper's standard attack."""
    p = inst["p"]
    n = inst["n"]
    split = n // 2
    start = _internal_curve(inst["start_curve"], p)
    target = _internal_curve(inst["target_curve"], p)
    forward: dict[tuple[int, ...], list[str]] = {}
    reverse: dict[tuple[int, ...], list[str]] = {}
    stats = {"forward_nodes": 0, "reverse_nodes": 0,
             "forward_leaves": 0, "reverse_leaves": 0,
             "leaf_cap_each": leaf_cap_each}

    def dfs_forward(curve, depth, path):
        if stats["forward_leaves"] >= leaf_cap_each:
            return
        stats["forward_nodes"] += 1
        if depth == split:
            forward.setdefault(_curve_key(curve), list(path))
            stats["forward_leaves"] += 1
            return
        for kernel in _roots(curve, p, allow_zero=(depth == 0)):
            dfs_forward(_advance(curve, kernel, p), depth + 1,
                        path + [_encode(kernel, p)])
            if stats["forward_leaves"] >= leaf_cap_each:
                break

    suffix_depth = n - split

    def dfs_reverse(curve, depth, suffix):
        if stats["reverse_leaves"] >= leaf_cap_each:
            return
        stats["reverse_nodes"] += 1
        if depth == suffix_depth:
            reverse.setdefault(_curve_key(curve), list(suffix))
            stats["reverse_leaves"] += 1
            return
        for source, kernel in _predecessors(curve, p):
            dfs_reverse(source, depth + 1, [_encode(kernel, p)] + suffix)
            if stats["reverse_leaves"] >= leaf_cap_each:
                break

    started = time.perf_counter()
    dfs_forward(start, 0, [])
    dfs_reverse(target, 0, [])
    stats["wall_clock_sec"] = time.perf_counter() - started
    stats["nodes"] = stats["forward_nodes"] + stats["reverse_nodes"]
    common = set(forward).intersection(reverse)
    for key in sorted(common):
        candidate = forward[key] + reverse[key]
        if verify(inst, candidate)[0]:
            stats["collision"] = True
            return candidate, stats
    stats["collision"] = False
    return None, stats


def _relabel_instance(inst: dict, u: tuple[int, int], conjugate: bool
                     ) -> tuple[dict, list[str]]:
    """Apply x=u^2*x' (and optionally Frobenius) and carry the witness."""
    moved = copy.deepcopy(inst)
    p = inst["p"]
    v = _square(u, p)
    vinv = _inv(v, p)
    vinv2 = _square(vinv, p)

    def tx(x, power):
        value = _f(x, p)
        if conjugate:
            value = _conj(value, p)
        return _mul(value, vinv if power == 1 else vinv2, p)

    for name in ("start_curve", "target_curve"):
        a2 = tx(moved[name]["a2"], 1)
        a4 = tx(moved[name]["a4"], 2)
        moved[name] = _public_curve((a2, a4))
    carried = []
    for code in inst["answer"]:
        root = _decode(code, p)
        if conjugate:
            root = _conj(root, p)
        root = _mul(root, vinv, p)
        carried.append(_encode(root, p))
    moved["answer"] = carried
    return moved, carried


def _scale_target_only(inst: dict, u: tuple[int, int]) -> dict:
    """Change only the target model within its j-isomorphism class.

    This is a genuine relabelling of the paper's terminal graph vertex, but the
    retained answer language has no final-isomorphism component.  The helper is
    kept to make the archive's representation mismatch executable in G8.
    """
    moved = copy.deepcopy(inst)
    p = inst["p"]
    v_inv = _inv(_square(u, p), p)
    v_inv2 = _square(v_inv, p)
    target = _internal_curve(inst["target_curve"], p)
    moved["target_curve"] = _public_curve((
        _mul(target[0], v_inv, p),
        _mul(target[1], v_inv2, p),
    ))
    return moved


def _translate_start_instance(inst: dict, h: tuple[int, int]
                             ) -> tuple[dict, list[str]]:
    """Translate only the source x=x'+h by a source 2-torsion root.

    The local quotient coordinate is x-t=x'-(t-h), so the first quotient
    model, and hence every later model, is unchanged.
    """
    moved = copy.deepcopy(inst)
    p = inst["p"]
    start = _internal_curve(inst["start_curve"], p)
    if not _is_root(start, h, p):
        raise ValueError("translation must use a source 2-torsion root")
    a2, a4 = start
    h2 = _square(h, p)
    moved_start = (
        _add(a2, _scale(3, h, p), p),
        _add(_add(a4, _scale(2, _mul(a2, h, p), p), p),
             _scale(3, h2, p), p),
    )
    carried = list(inst["answer"])
    first = _decode(carried[0], p)
    carried[0] = _encode(_sub(first, h, p), p)
    moved["start_curve"] = _public_curve(moved_start)
    moved["answer"] = carried
    return moved, carried


def _answer_atoms(value: Any) -> int:
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    return 1


def selftest() -> dict:
    report: dict[str, Any] = {}

    # G1: every named rung and three independent seeds.
    g1_failures = []
    tested = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            case = make_instance(seed=seed, **params)
            tested += 1
            ok, reason = verify(case, case["answer"])
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(case["answer"])) != case["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "instances": tested,
        "failures": g1_failures,
        "generation_route": "inverse generation of kernel choices",
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **ship_params)

    # G2: deliberately target separate validation layers.
    mutations = {}
    dropped = inst["answer"][:-1]
    mutations["drop_one"] = verify(inst, dropped)
    mutations["empty"] = verify(inst, [])
    outside = list(inst["answer"])
    outside[0] = _to_base36(inst["p"] * inst["p"])
    mutations["out_of_range"] = verify(inst, outside)

    swapped = None
    for i in range(1, min(inst["n"], 8)):
        trial = list(inst["answer"])
        trial[0], trial[i] = trial[i], trial[0]
        result = verify(inst, trial)
        if not result[0]:
            swapped = result
            break
    mutations["swap"] = swapped or (True, "unexpectedly valid")

    duplicated = None
    for i in range(1, inst["n"]):
        if inst["answer"][i - 1] == "0":
            continue
        trial = list(inst["answer"])
        trial[i] = trial[i - 1]
        result = verify(inst, trial)
        if not result[0] and "duplicated" in result[1]:
            duplicated = result
            break
    mutations["duplicate"] = duplicated or (True, "could not construct duplicate corruption")
    reasons = [result[1] for result in mutations.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not result[0] for result in mutations.values())
                and len(set(reasons)) == len(reasons),
        "mutations": {name: {"accepted": result[0], "reason": result[1]}
                      for name, result in mutations.items()},
        "distinct_reasons": len(set(reasons)),
    }

    # G3: exact round trip from realistic surrounding prose and a fence.
    blob = json.dumps(inst["answer"], separators=(",", ":"))
    model_reply = (
        "I replayed the quotient recurrence exactly.\n```json\n"
        + blob
        + "\n```\nTherefore my final response is <answer>"
        + blob
        + "</answer>."
    )
    parsed = parse_answer(model_reply)
    parsed_ok = parsed == inst["answer"] and verify(inst, parsed)[0]
    malformed = parse_answer("Here is no delimited or JSON answer.") is None
    report["G3_round_trip"] = {
        "pass": parsed_ok and malformed,
        "model_style_round_trip": parsed_ok,
        "garbage_returns_none": malformed,
    }

    # G4/G5 density: sample the exact declared prior.  The bidirectional helper
    # shares common prefixes and exact reverse suffixes; it does not alter the
    # random_candidate distribution or approximate endpoint equality.
    sample_total = 200_000
    rng = random.Random(0x171104062)
    density_started = time.perf_counter()
    sample_hits, density_stats = _sample_density(inst, sample_total, rng)
    density_elapsed = time.perf_counter() - density_started
    probability = sample_hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": sample_total >= 200_000 and probability < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "probability": probability,
        "candidate_prior": "uniform first kernel, then uniform non-dual kernel",
        "search_space": search_space(inst),
        "sampling_wall_clock_sec": density_elapsed,
        "measurement": density_stats,
    }

    # G6 across eight independently generated shipping instances.
    attack_successes = {
        "outlier_smallest_kernel": 0,
        "greedy_endpoint_coefficients": 0,
        "random_restart_64": 0,
        "meet_in_middle_capped_16384": 0,
    }
    attack_attempts = {name: 0 for name in attack_successes}
    mitm_stats = []
    for seed in range(8):
        case = make_instance(seed=8000 + seed, **ship_params)

        for name, rule in (("outlier_smallest_kernel", "smallest"),
                           ("greedy_endpoint_coefficients", "target")):
            candidate = _path_by_rule(case, rule)
            attack_attempts[name] += 1
            if verify(case, candidate)[0]:
                attack_successes[name] += 1

        name = "random_restart_64"
        attack_attempts[name] += 1
        rrng = random.Random(9000 + seed)
        solved = False
        for _ in range(64):
            candidate = random_candidate(case, rrng)
            if verify(case, candidate)[0]:
                solved = True
                break
        attack_successes[name] += int(solved)

        name = "meet_in_middle_capped_16384"
        attack_attempts[name] += 1
        candidate, stats = _mitm_attack(case, 16_384)
        mitm_stats.append(stats)
        if candidate is not None and verify(case, candidate)[0]:
            attack_successes[name] += 1

    attacks = {
        name: {"successes": attack_successes[name],
               "attempts": attack_attempts[name]}
        for name in attack_successes
    }
    all_failed = len(attacks) >= 4 and all(v["successes"] == 0
                                           and v["attempts"] >= 8
                                           for v in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attacks,
        "standard_algorithm": "bidirectional meet-in-the-middle isogeny walk",
        "mitm_leaf_cap_each": 16_384,
        "mitm_total_nodes": sum(s["nodes"] for s in mitm_stats),
        "mitm_total_wall_clock_sec": sum(s["wall_clock_sec"] for s in mitm_stats),
        "complete_forward_leaves": 3 * (1 << (inst["n"] // 2 - 1)),
        "complete_reverse_leaves": 1 << (inst["n"] - inst["n"] // 2),
    }

    # G5 combines shipping density with the actual strongest-attack cost.
    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": isinstance(probability, float) and bool(mitm_stats),
        "shipping_density_hits": sample_hits,
        "shipping_density_total": sample_total,
        "shipping_density": probability,
        "shipping_density_kind": "sampled exact certificate-language prior",
        "demo_n": demo["n"],
        "demo_exact_solutions": demo_count,
        "demo_search_space": search_space(demo),
        "strongest_attack": "capped bidirectional meet-in-the-middle",
        "baseline_attempts": 8,
        "baseline_successes": attack_successes["meet_in_middle_capped_16384"],
        "baseline_nodes_total": sum(s["nodes"] for s in mitm_stats),
        "baseline_nodes_median": statistics.median(s["nodes"] for s in mitm_stats),
        "baseline_wall_clock_sec_total": sum(s["wall_clock_sec"] for s in mitm_stats),
        "baseline_wall_clock_sec_median": statistics.median(
            s["wall_clock_sec"] for s in mitm_stats
        ),
        "full_frontier_leaves_estimate": (
            3 * (1 << (inst["n"] // 2 - 1))
            + (1 << (inst["n"] - inst["n"] // 2))
        ),
    }

    # G7: named ladder monotonicity and an actually doubled path/field build.
    sizes = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    doubled_params = {"n": 2 * DIFFICULTY["hard"]["n"],
                      "mersenne_exponent": 127}
    doubled = make_instance(seed=77, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": sizes == sorted(sizes) and len(set(sizes)) == 4 and doubled_ok,
        "preset_n": sizes,
        "doubled_n": doubled["n"],
        "doubled_field_bits": doubled["p"].bit_length(),
        "doubled_planted_verifies": doubled_ok,
        "search_space_shipping_bits": math.log2(search_space(inst)),
        "search_space_doubled_bits": math.log2(search_space(doubled)),
    }

    # G8: source-root translation, coordinate scaling, Frobenius, and
    # compositions of those genuine curve-model relabelings.
    invariant_checks = 0
    carried_checks = 0
    unrelated_keys = []
    g8_failures = []
    symmetry_params = {"n": 16, "mersenne_exponent": 31}
    for seed in range(20):
        case = make_instance(seed=30_000 + seed, **symmetry_params)
        base_key = canonical_key(case)
        unrelated_keys.append(base_key)
        srng = random.Random(40_000 + seed)
        u = (srng.randrange(1, case["p"]), srng.randrange(case["p"]))
        if _zero(u):
            u = (1, 1)
        start = _internal_curve(case["start_curve"], case["p"])
        h = _roots(start, case["p"], allow_zero=True)[(seed % 2) + 1]
        translated, _ = _translate_start_instance(case, h)
        variants = [
            _relabel_instance(case, u, False),
            _relabel_instance(case, u, True),
            _relabel_instance(translated, u, True),
        ]
        for number, (moved, carried) in enumerate(variants):
            invariant_checks += 1
            if canonical_key(moved) != base_key:
                g8_failures.append(f"key/{seed}/{number}")
            if verify(moved, carried)[0]:
                carried_checks += 1
            else:
                g8_failures.append(f"witness/{seed}/{number}")
    # The original test covered only simultaneous source/target coordinate
    # changes.  The paper's vertices are j-invariants, so independently
    # changing the terminal model is also a relabelling.  canonical_key treats
    # it as such, but verify() has no way to carry the terminal isomorphism.
    native_case = make_instance(seed=7, n=8, mersenne_exponent=13)
    target_scaled = _scale_target_only(native_case, (2, 0))
    target_only_same_key = canonical_key(target_scaled) == canonical_key(native_case)
    target_only_verify = verify(target_scaled, native_case["answer"])
    invariant_checks += 1
    if not target_only_same_key:
        g8_failures.append("target-only-isomorphism/key")
    if not target_only_verify[0]:
        g8_failures.append("target-only-isomorphism/witness-language")
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and invariant_checks == 61
                and carried_checks == 60 and distinct == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct,
        "failures": g8_failures,
        "target_only_isomorphism_same_key": target_only_same_key,
        "target_only_original_witness_accepted": target_only_verify[0],
        "target_only_verify_reason": target_only_verify[1],
        "transformations": [
            "random elliptic-curve coordinate scaling",
            "F_(p^2)/F_p Frobenius conjugation composed with scaling",
            "source translation by a 2-torsion root composed with scaling and Frobenius",
        ],
        "key_definition": "ordered endpoint j-invariants modulo joint conjugation",
    }

    # G9(c) counts the route that FINDS the witness, not the much cheaper work
    # of replaying an already supplied witness.  The paper's strongest compact
    # idea here is balanced meet-in-the-middle; it still leaves 2^(e/2)
    # frontier expansions for an e-edge path.  This is why the candidate is
    # archived even though certificate replay itself is cheap.
    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    intended_operations = 1 << (inst["n"] // 2)
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_operations <= 300)
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "operation_interpretation": (
            "conservative one-frontier size for the O(2^(e/2)) meet-in-the-middle "
            "path-finding route in Section 14.2; certificate replay is not the "
            "intended route"
        ),
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass") is True
        for key, value in report.items() if key.startswith("G")
    )
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship_params)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
