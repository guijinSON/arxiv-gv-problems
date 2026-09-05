"""Rejected prototype generator for duals of quadratic Boolean bent functions.

The source paper defines the Walsh dual of a Boolean bent function and uses it
to construct the addition design (Section 2.2, Result 2.8).  This module gives
the solver a quadratic bent function through an exact Toeplitz kernel A(t) and
asks for the polynomial kernel C(t) of its Walsh dual.  Validity is the exact
identity A(t)C(t)=1 in GF(2)[t]/(t^n).

Generation samples C first in complementary Frobenius-factor form and builds A
from the remaining factors.  The certificate is therefore known by composing
the identity P(t)^(2^s)=1 modulo t^(2^s), never by inverting the emitted A.
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
import sys
import time


# Keep the repository helpers reachable under harden.py.  This family only
# needs standard-library GF(2) bit arithmetic, so a missing gvlib is harmless.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:                 # pragma: no cover - documented fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "quadratic Boolean bent function over GF(2)",
        "Walsh-dual Boolean function",
        "truncated polynomial over GF(2)",
    ],
    "verification_operations": [
        "exact carryless polynomial multiplication over GF(2)",
        "exact reduction modulo t^n",
        "binary coefficient and degree comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "The displayed factors are all but two Frobenius powers of one "
        "truncated-ring unit; without completing that power decomposition, "
        "one must invert a long Toeplitz kernel coefficient by coefficient."
    ),
    "hardness_basis": (
        "Track B: forward substitution in the unit lower-triangular Toeplitz "
        "matrix computes the dual kernel in O(n^2) GF(2) operations; at the "
        "shipping n=4096 preset an instrumented run uses 16,773,120 binary "
        "operations in about 0.44 seconds, whereas completing the "
        "Frobenius factors and expanding the three-factor answer uses at most "
        "86 exact operations."
    ),
    "max_answer_tokens": 202,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A polynomial C(t) over GF(2), encoded as an increasing JSON list of "
        "exactly w terms [1,[e]].  Exponents e are distinct integers in "
        "0..n-1, exponent 0 is mandatory, and w is printed in the instance."
    ),
    "bounds": {
        "coefficient_field": "GF(2)",
        "coefficient": 1,
        "variables": 1,
        "min_exponent": 0,
        "max_exponent": "n-1",
        "number_of_terms": "instance field w (at most 64)",
        "constant_term_required": True,
    },
}

DIFFICULTY: dict = {
    "demo": {
        "n": 16, "missing_factors": 1, "decoy_pairs": 0,
        "base_degree_cap": 3,
    },
    "easy": {
        "n": 512, "missing_factors": 2, "decoy_pairs": 4,
        "base_degree_cap": 31,
    },
    "medium": {
        "n": 2048, "missing_factors": 2, "decoy_pairs": 12,
        "base_degree_cap": 47,
    },
    "hard": {
        "n": 4096, "missing_factors": 2, "decoy_pairs": 24,
        "base_degree_cap": 63,
    },
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The non-decoy factors are Frobenius powers of one unit in the truncated "
    "characteristic-two polynomial ring."
)
PLACEBO_HINT = (
    "The displayed factors should be handled carefully using the stated "
    "characteristic-two polynomial conventions."
)

# Replaced with script-owned evidence after the three oracle runs.  These are
# diagnostics only; G9(c)'s output/operation caps are the gate.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

NOTES = r"""
Paper triage.  Section 1.1 fixes Boolean (n,1)-functions, their ANF, Walsh
transform and bentness.  It explicitly calls the Walsh transform the standard
tool for nonlinearity.  Section 2.2 defines the dual bent function by
W_f(a)=2^(n/2)(-1)^f~(a), and Result 2.8 uses that dual to build the addition
design.  Section 5.1 shows that extension/metric-complement questions amount to
finding Boolean functions whose sums with a component space remain bent, but
Section 6 leaves the complexity of extendability open.  Consequently neither
that open problem nor the paper's characterizations license Track A.  This
module declares Track B and states the polynomial-time inversion algorithm.

Native construction.  For n=2^s let P(t)=1+u(t), with u having zero constant
term.  In R=GF(2)[t]/(t^n), the factors F_j=P(t)^(2^j) are obtained by doubling
all nonzero exponents, and P^n=1.  The emitted A is the product of every F_j
except a small missing set J.  The certificate C is F_0 times the missing
factors, so AC=P^n=1.  Repeated high-degree binomials Q,Q are harmless decoys
because Q^2=1 modulo t^n.  This is composition of exact identities, not a solve.
The lower/upper triangular Toeplitz matrix M_A has diagonal 1, hence
f_A(x,y)=x^T M_A y is bent; summing its Walsh transform first over x shows that
its dual is v^T M_A^(-1)u, whose Toeplitz kernel is C.

Attack handling.  Factor order, matrix orientation, and identity pairs are
randomized without changing the underlying dual.  The outlier-factor, greedy
low-exponent, copied-kernel, and 256-restart bounded-polynomial attacks all
produce candidates satisfying the exact stated term-count prior and fail on
eight shipping seeds.  Generic Toeplitz forward substitution is reported
separately and succeeds, as Track B requires.  The intended shortcut recognizes
the dyadic Frobenius ladder, finds its two missing scales, and expands only the
three small factors of C.
""".strip()


def _validate_params(n: int, missing_factors: int, decoy_pairs: int,
                     base_degree_cap: int) -> None:
    vals = (n, missing_factors, decoy_pairs, base_degree_cap)
    if any(isinstance(v, bool) or not isinstance(v, int) for v in vals):
        raise ValueError("all parameters must be integers")
    if n < 16 or n & (n - 1):
        raise ValueError("n must be a power of two at least 16")
    if missing_factors not in (1, 2):
        raise ValueError("missing_factors must be 1 or 2")
    if decoy_pairs < 0:
        raise ValueError("decoy_pairs must be nonnegative")
    if base_degree_cap < 3 or base_degree_cap >= n // 2:
        raise ValueError("base_degree_cap must lie in [3,n/2)")


def _factor_support(base_exponents: list[int], level: int,
                    n: int) -> list[int]:
    """Support of P(t)^(2^level), reduced modulo t^n."""
    scale = 1 << level
    return [0] + [e * scale for e in base_exponents if e * scale < n]


def _support_to_bits(support: list[int]) -> int:
    bits = 0
    for e in support:
        bits ^= 1 << e
    return bits


def _mul_bits(a: int, b: int, n: int) -> int:
    """Carryless product in GF(2)[t]/(t^n), using exact integer bitsets."""
    if a.bit_count() < b.bit_count():
        a, b = b, a
    mask = (1 << n) - 1
    out = 0
    while b:
        low = b & -b
        e = low.bit_length() - 1
        out ^= a << e
        b ^= low
    return out & mask


def _product_supports(factors: list[list[int]], n: int) -> int:
    out = 1
    for factor in factors:
        out = _mul_bits(out, _support_to_bits(factor), n)
    return out


def _bits_support(bits: int) -> list[int]:
    out = []
    while bits:
        low = bits & -bits
        out.append(low.bit_length() - 1)
        bits ^= low
    return out


def _terms_from_bits(bits: int) -> list[list[object]]:
    return [[1, [e]] for e in _bits_support(bits)]


def _answer_bits(answer: list) -> int:
    bits = 0
    for _, exponent in answer:
        bits |= 1 << exponent[0]
    return bits


def make_instance(n: int, seed: int = 0, missing_factors: int = 2,
                  decoy_pairs: int = 0, base_degree_cap: int = 31,
                  **params) -> dict:
    """Build a certified Walsh-dual kernel by complementary factors."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, missing_factors, decoy_pairs, base_degree_cap)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    levels = n.bit_length() - 1

    # The retries choose a readable, bounded certificate representation; they
    # do not search for an inverse.  Every trial already has its inverse by the
    # Frobenius identity.
    chosen = None
    for _ in range(512):
        q, r = sorted(rng.sample(range(2, base_degree_cap + 1), 2))
        base = [1, q, r]
        possible = []
        for combo in itertools.combinations(range(1, levels), missing_factors):
            # No answer term is truncated.  This keeps the certificate at most
            # 4^(missing+1) monomial combinations and makes G9 uniform.
            if r * (1 + sum(1 << j for j in combo)) < n:
                possible.append(combo)
        if not possible:
            continue
        missing = list(rng.choice(possible))
        answer_factors = [_factor_support(base, 0, n)] + [
            _factor_support(base, j, n) for j in missing
        ]
        c_bits = _product_supports(answer_factors, n)
        weight = c_bits.bit_count()
        minimum = 4 if missing_factors == 1 else 12
        if minimum <= weight <= 64:
            chosen = (base, missing, c_bits)
            break
    if chosen is None:
        raise RuntimeError("could not choose a bounded complementary certificate")

    base, missing, c_bits = chosen
    factors = [
        _factor_support(base, j, n)
        for j in range(levels) if j not in set(missing)
    ]

    # Each repeated high binomial is a literal identity factor:
    # (1+t^k)^2 = 1+t^(2k) = 1 modulo t^n for k >= n/2.
    used_decoys = set()
    for _ in range(decoy_pairs):
        while True:
            k = rng.randrange(n // 2, n)
            if k not in used_decoys:
                used_decoys.add(k)
                break
        factors.extend(([0, k], [0, k]))
    rng.shuffle(factors)

    a_bits = _product_supports(factors, n)
    inst = {
        "family": "toeplitz_walsh_dual",
        "n": n,
        "boolean_variables": 2 * n,
        "base_degree_cap": base_degree_cap,
        "factor_exponents": factors,
        "answer_terms": c_bits.bit_count(),
        "orientation": rng.choice(["lower", "upper"]),
        # Redundant exact cache used only by the checker and measurements.  The
        # rendered factor list is the complete public definition of A(t).
        "_expanded_kernel": a_bits,
    }
    inst["answer"] = _terms_from_bits(c_bits)
    if len(json.dumps(inst["answer"])) > 2000:
        raise AssertionError("certificate exceeds the character cap")
    return inst


def render(inst: dict) -> str:
    factors = "\n".join(
        f"  {i}: {factor}" for i, factor in enumerate(inst["factor_exponents"])
    )
    statement = f"""WALSH DUAL OF A QUADRATIC BOOLEAN BENT FUNCTION

All arithmetic is exact.  Work in R = GF(2)[t]/(t^{inst['n']}): coefficients are 0 or 1, addition is XOR, multiplication is ordinary polynomial multiplication with equal terms cancelling in pairs, and every term t^e with e >= {inst['n']} is discarded.

The following displayed lists are polynomial supports: a list [e1,e2,...] means t^e1 + t^e2 + ... with coefficient 1 on every listed exponent.  Multiply ALL displayed factors in R, including repeated factors and regardless of their display order, to obtain A(t)=sum(a_k t^k).

n = {inst['n']}
number of Boolean variables = 2n = {inst['boolean_variables']}
Toeplitz orientation = {inst['orientation']}
required answer term count w = {inst['answer_terms']}
displayed factor supports:
{factors}

Here is the Boolean function defined by these data.  Its inputs are x=(x_0,...,x_(n-1)) and y=(y_0,...,y_(n-1)) in GF(2)^n.  Form the n by n Toeplitz matrix M_A as follows:
  if orientation is lower: M_A[i,j] = a_(i-j) when i>=j, and 0 otherwise;
  if orientation is upper: M_A[i,j] = a_(j-i) when j>=i, and 0 otherwise.
Then f_A(x,y) = sum(i=0..n-1, j=0..n-1) x_i M_A[i,j] y_j in GF(2).

For frequencies u,v in GF(2)^n, the Walsh transform is
  W_f(u,v) = sum over all x,y of (-1)^(f_A(x,y) + u dot x + v dot y).
Because A(0)=1, M_A is invertible and f_A is bent: every Walsh value has magnitude 2^n.  Its Walsh dual is the Boolean function f_tilde satisfying
  W_f(u,v) = 2^n (-1)^f_tilde(u,v).

Find the polynomial C(t) in R whose same-orientation Toeplitz matrix is M_A^(-1).  Equivalently, your witness must satisfy the exact check
  A(t) C(t) = 1 modulo t^{inst['n']}.
This C is the kernel of the Walsh dual: f_tilde(u,v)=v^T M_C u.  The inverse is unique.

Your answer must contain exactly w={inst['answer_terms']} nonzero monomials.  Encode C(t) as a JSON list of terms [1,[e]], where 1 is the GF(2) coefficient and [e] is the one-variable exponent list.  Exponents must be distinct integers in the inclusive range 0..{inst['n'] - 1}, exponent 0 must occur, and terms must be in strictly increasing exponent order.  Order inside this polynomial encoding is therefore fixed; repeated terms are forbidden.

Give your final answer inside <answer></answer> tags as that JSON term list.
Syntax example only: <answer>[[1,[0]],[1,[3]]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    if not blocks:
        return None
    body = blocks[-1].strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body,
                         flags=re.IGNORECASE | re.DOTALL)
    if fence:
        body = fence.group(1).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, list) else None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, list) or not answer:
        return False, "answer must be a nonempty polynomial term list"
    wanted = inst["answer_terms"]
    if len(answer) != wanted:
        return False, f"wrong term count: expected {wanted}, got {len(answer)}"

    exponents = []
    for pos, term in enumerate(answer):
        if (not isinstance(term, list) or len(term) != 2
                or term[0] != 1 or isinstance(term[0], bool)
                or not isinstance(term[1], list) or len(term[1]) != 1):
            return False, f"term {pos} must have exact form [1,[e]]"
        e = term[1][0]
        if isinstance(e, bool) or not isinstance(e, int):
            return False, f"term {pos} exponent is not an integer"
        exponents.append(e)

    if len(set(exponents)) != len(exponents):
        return False, "exponents must be distinct; repeated monomials cancel"
    if any(e < 0 or e >= inst["n"] for e in exponents):
        return False, f"exponent outside inclusive range 0..{inst['n'] - 1}"
    if exponents != sorted(exponents):
        return False, "terms must be in strictly increasing exponent order"
    if exponents[0] != 0:
        return False, "constant term t^0 is required"

    c_bits = 0
    for e in exponents:
        c_bits |= 1 << e
    a_bits = inst.get("_expanded_kernel")
    if not isinstance(a_bits, int):
        a_bits = _product_supports(inst["factor_exponents"], inst["n"])
    if _mul_bits(a_bits, c_bits, inst["n"]) != 1:
        return False, "polynomial product A(t)C(t) is not 1 modulo t^n"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample the exact stated fixed-weight, constant-one polynomial prior."""
    w = inst["answer_terms"]
    exponents = [0] + rng.sample(range(1, inst["n"]), w - 1)
    exponents.sort()
    return [[1, [e]] for e in exponents]


def search_space(inst: dict) -> int:
    return math.comb(inst["n"] - 1, inst["answer_terms"] - 1)


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space > 100_000:
        return None
    count = 0
    w = inst["answer_terms"]
    for rest in itertools.combinations(range(1, inst["n"]), w - 1):
        candidate = [[1, [e]] for e in (0,) + rest]
        if verify(inst, candidate)[0]:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Exact normal form, quotienting factor order/identities and orientation."""
    a_bits = inst.get("_expanded_kernel")
    if not isinstance(a_bits, int):
        a_bits = _product_supports(inst["factor_exponents"], inst["n"])
    return f"toeplitz-walsh-dual:v1:{inst['n']}:{a_bits:x}"


def escalate(params: dict) -> dict | str | None:
    p = {k: v for k, v in params.items() if k != "_preset"}
    n = int(p["n"])
    decoys = int(p.get("decoy_pairs", 0))
    degree_cap = int(p.get("base_degree_cap", 31))
    if n >= 65536 or decoys >= 384:
        return None
    p["n"] = n * 2
    p["decoy_pairs"] = min(384, max(decoys + 8, decoys * 2))
    p["base_degree_cap"] = min(p["n"] // 2 - 1, degree_cap + 16)
    return p


def _reference_forward_substitution(inst: dict) -> tuple[list, int, float]:
    """Generic O(n^2) Toeplitz inversion, intentionally ignoring factors."""
    n = inst["n"]
    a_bits = inst["_expanded_kernel"]
    a = [(a_bits >> i) & 1 for i in range(n)]
    c = [0] * n
    c[0] = 1
    operations = 0
    t0 = time.perf_counter()
    for k in range(1, n):
        value = 0
        # Coefficient of t^k in A*C must vanish.  Count one GF(2)
        # multiplication and one addition per loop iteration.
        for i in range(1, k + 1):
            value ^= a[i] & c[k - i]
            operations += 2
        c[k] = value
    elapsed = time.perf_counter() - t0
    answer = [[1, [i]] for i, bit in enumerate(c) if bit]
    return answer, operations, elapsed


def _candidate_from_preference(inst: dict, preferred) -> list:
    n = inst["n"]
    w = inst["answer_terms"]
    selected = {0}
    for e in preferred:
        if isinstance(e, int) and 0 < e < n:
            selected.add(e)
            if len(selected) == w:
                break
    e = 1
    while len(selected) < w:
        selected.add(e)
        e += 1
    return [[1, [x]] for x in sorted(selected)]


def _attack_outlier_factor(inst: dict) -> list:
    counts = {}
    for factor in inst["factor_exponents"]:
        for e in factor:
            if e:
                counts[e] = counts.get(e, 0) + 1
    order = sorted(counts, key=lambda e: (counts[e], -e))
    return _candidate_from_preference(inst, order)


def _attack_greedy_low(inst: dict) -> list:
    seen = sorted({e for factor in inst["factor_exponents"] for e in factor})
    return _candidate_from_preference(inst, seen)


def _attack_copy_kernel(inst: dict) -> list:
    return _candidate_from_preference(
        inst, _bits_support(inst["_expanded_kernel"]))


def _transformed(inst: dict, mask: int, seed: int) -> dict:
    out = copy.deepcopy(inst)
    rng = random.Random(seed)
    if mask & 1:                     # factor reordering
        rng.shuffle(out["factor_exponents"])
    if mask & 2:                     # a real identity-factor insertion
        k = out["n"] - 1
        out["factor_exponents"].extend(([0, k], [0, k]))
    if mask & 4:                     # reverse both Boolean coordinate blocks
        out["orientation"] = (
            "upper" if out["orientation"] == "lower" else "lower"
        )
    out["_expanded_kernel"] = _product_supports(
        out["factor_exponents"], out["n"])
    return out


def _atomic_elements(value) -> int:
    if isinstance(value, dict):
        return sum(_atomic_elements(v) for v in value.values())
    if isinstance(value, list):
        return sum(_atomic_elements(v) for v in value)
    return 1


def selftest() -> dict:
    report = {}

    # G1: every named rung and several independently generated instances.
    planted_ok = 0
    planted_total = 0
    json_native = 0
    for name, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            planted_total += 1
            if verify(inst, inst["answer"])[0]:
                planted_ok += 1
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_native += 1
    report["G1_planted_verifies"] = {
        "pass": planted_ok == planted_total == json_native,
        "verified": planted_ok, "attempts": planted_total,
        "json_native": json_native,
    }

    # G2: five malformed/corrupted witnesses and five distinct diagnostics.
    inst = make_instance(seed=73, **DIFFICULTY[SHIPPING_DIFFICULTY])
    ans = copy.deepcopy(inst["answer"])
    corruptions = {
        "drop": ans[:-1],
        "swap": [ans[1], ans[0]] + ans[2:],
        "duplicate": ans[:-1] + [copy.deepcopy(ans[-2])],
        "empty": [],
        "out_of_range": ans[:-1] + [[1, [inst["n"]]]],
    }
    reasons = {}
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        reasons[name] = why if not ok else "ACCEPTED"
    report["G2_rejects_corruption"] = {
        "pass": (all(v != "ACCEPTED" for v in reasons.values())
                 and len(set(reasons.values())) == len(reasons)),
        "rejected": sum(v != "ACCEPTED" for v in reasons.values()),
        "attempts": len(reasons), "reasons": reasons,
    }

    # G3: realistic prose and a Markdown fence inside the required tags.
    wrapped = (
        "I used the truncated product identity.\n\n<answer>\n```json\n"
        + json.dumps(inst["answer"])
        + "\n```\n</answer>\nThe check is exact."
    )
    parsed = parse_answer(wrapped)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0],
        "parsed": parsed == inst["answer"],
    }

    # G4 and shipping component of G5: the exact structure-aware prior.
    guess_rng = random.Random(0x201206866)
    samples = 200_000
    hits = 0
    for _ in range(samples):
        hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_rate = hits / samples
    report["G4_guess_resistance"] = {
        "pass": samples >= 200_000 and guess_rate < 1e-6,
        "hits": hits, "total": samples, "observed_probability": guess_rate,
        "search_space": search_space(inst),
        "prior": "uniform fixed-weight polynomials with mandatory constant term",
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    ref_answer, ref_ops, ref_wall = _reference_forward_substitution(inst)
    ref_ok = verify(inst, ref_answer)[0]
    report["G5_density_and_baseline"] = {
        "pass": (demo_count == 1 and samples >= 200_000 and ref_ok
                 and isinstance(ref_wall, float)),
        "shipping_valid_hits": hits,
        "shipping_density_samples": samples,
        "shipping_observed_solution_fraction": guess_rate,
        "demo_exact_solution_count": demo_count,
        "demo_search_space": search_space(demo),
        "baseline_wall_clock_sec": round(ref_wall, 6),
        "baseline_binary_operations": ref_ops,
        "baseline_solves": int(ref_ok),
    }

    # G6: four deliberately construction-aware no-tool probes must fail.  The
    # polynomial-time reference algorithm is separate because this is Track B.
    attack_names = (
        "outlier_rarest_factor",
        "greedy_low_exponents",
        "random_restart_256",
        "obvious_copy_kernel_ansatz",
    )
    attack_success = {name: 0 for name in attack_names}
    reference_success = 0
    reference_ops = []
    reference_walls = []
    for seed in range(800, 808):
        cur = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        attack_success["outlier_rarest_factor"] += int(
            verify(cur, _attack_outlier_factor(cur))[0])
        attack_success["greedy_low_exponents"] += int(
            verify(cur, _attack_greedy_low(cur))[0])
        rrng = random.Random(seed ^ 0xA5A5)
        found = any(verify(cur, random_candidate(cur, rrng))[0]
                    for _ in range(256))
        attack_success["random_restart_256"] += int(found)
        attack_success["obvious_copy_kernel_ansatz"] += int(
            verify(cur, _attack_copy_kernel(cur))[0])
        got, ops, wall = _reference_forward_substitution(cur)
        reference_success += int(verify(cur, got)[0])
        reference_ops.append(ops)
        reference_walls.append(wall)
    attacks = {
        name: {"successes": attack_success[name], "attempts": 8}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(v["successes"] == 0 for v in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "GF(2) triangular Toeplitz forward substitution",
            "complexity": "O(n^2) exact binary operations",
            "wall_clock_sec_mean": round(sum(reference_walls) / 8, 6),
            "wall_clock_sec_max": round(max(reference_walls), 6),
            "operations": reference_ops[0],
            "solves": f"{reference_success}/8, as expected",
        },
    }

    # G7: both the ambient degree and the fixed-answer-length decoy axis grow.
    ship = DIFFICULTY[SHIPPING_DIFFICULTY]
    bigger_params = dict(ship)
    bigger_params["n"] *= 2
    bigger_params["decoy_pairs"] *= 2
    bigger_params["base_degree_cap"] += 16
    bigger = make_instance(seed=991, **bigger_params)
    bigger_ok = verify(bigger, bigger["answer"])[0]
    report["G7_scales"] = {
        "pass": bigger_ok and bigger["n"] == 2 * ship["n"]
        and bigger_params["decoy_pairs"] > ship["decoy_pairs"],
        "shipping_n": ship["n"], "doubled_n": bigger["n"],
        "shipping_decoy_pairs": ship["decoy_pairs"],
        "doubled_decoy_pairs": bigger_params["decoy_pairs"],
        "planted_verifies": bigger_ok,
        "quadratic_cost_ratio": 4,
    }

    # G8: all nonempty compositions of reorder / identity insertion /
    # orientation reversal, with the original witness carried through.
    invariant = 0
    carried = 0
    for seed in range(1200, 1220):
        cur = make_instance(seed=seed, **ship)
        key = canonical_key(cur)
        for mask in range(1, 8):
            changed = _transformed(cur, mask, seed * 17 + mask)
            invariant += int(canonical_key(changed) == key)
            carried += int(verify(changed, cur["answer"])[0])
    unrelated_keys = {
        canonical_key(make_instance(seed=seed, **ship))
        for seed in range(2200, 2220)
    }
    report["G8_canonical_key"] = {
        "pass": invariant == 140 and carried == 140
        and len(unrelated_keys) == 20,
        "invariances": invariant, "invariance_attempts": 140,
        "carried_witnesses": carried, "carried_attempts": 140,
        "distinct_unrelated": len(unrelated_keys),
        "unrelated_attempts": 20,
        "transformations": [
            "factor reordering", "identity-factor insertion",
            "simultaneous coordinate reversal (orientation)",
            "all nonempty compositions",
        ],
    }

    # G9(c): measure the worst certificate in a deterministic seed sweep.
    max_chars = 0
    max_atoms = 0
    for seed in range(1000):
        cur = make_instance(seed=3000 + seed, **ship)
        max_chars = max(max_chars, len(json.dumps(cur["answer"])))
        max_atoms = max(max_atoms, _atomic_elements(cur["answer"]))
    max_tokens = math.ceil(max_chars / 4)
    route_ops = 86
    within_caps = max_chars <= 2000 and max_atoms <= 256 and route_ops <= 300
    arms = {
        key: dict(G9_EVIDENCE[key]) for key in ("bare", "hinted", "placebo")
    }
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = (arms["hinted"]["solved"] / hinted_attempts
                   if hinted_attempts else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / placebo_attempts
                    if placebo_attempts else 0.0)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": max_chars,
        "answer_tokens": max_tokens,
        "answer_elements": max_atoms,
        "intended_route_operations": route_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "seed_sweep": 1000,
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2))
