"""Verified generator for recovering coefficients of a closed butterfly.

The family uses Theorem 1 and the coefficient identities in Section II of
Li--Li--Helleseth--Qu, arXiv:1912.02640.  A hidden parameter ``s`` is sampled
first and the public invariant and answer are both composed from it; no emitted
instance is searched or solved during generation.  Arithmetic is exact in a
binary finite field and the implementation is standard-library-only.
"""

from __future__ import annotations

import functools
import json
import math
import os
import random
import re
import sys
import time


# Make the repository helper package available when harden.py imports this file
# from results/1912.02640.  gvlib has no binary-field helper, so this module has
# a complete standard-library implementation and merely degrades gracefully as
# requested by the repository interface.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - supported fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "elements of GF(2^n) in a polynomial basis",
        "closed-butterfly coefficients alpha and beta",
        "the normalized butterfly invariant phi_2/phi_4",
    ],
    "verification_operations": [
        "carryless polynomial multiplication modulo an irreducible polynomial",
        "exact finite-field exponentiation",
        "finite-field polynomial identity comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Writing the public trace-zero invariant as t=s^2+s turns the two "
        "high-degree coefficient constraints into direct rational formulas; "
        "without that substitution one must search or eliminate over GF(2^n)."
    ),
    "hardness_basis": (
        "Track B: the Artin--Schreier half-trace algorithm recovers a solution "
        "in O(n^3) bit operations with schoolbook finite-field arithmetic; the "
        "measured n=31 reference mean is 111 field operations, about 4,285 "
        "instrumented bit-loop operations, and 0.00029 seconds, while that exact "
        "polynomial-basis arithmetic is not safely executable in context without "
        "tools."
    ),
    "max_answer_tokens": 23,
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
        "A JSON list [alpha,beta] of two distinct decimal integer encodings of "
        "nonzero GF(2^n) elements, with alpha != 1 and each integer below 2^n."
    ),
    "bounds": {
        "elements": 2,
        "encoding": "decimal integers in [0,2^n-1]",
        "alpha_excluded": [0, 1],
        "beta_excluded": [0, "alpha"],
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 3},
    "easy": {"n": 31},
    "medium": {"n": 47},
    "hard": {"n": 61},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Introduce s through t=s^2+s, and use d=t+1 to express both butterfly "
    "coefficients directly."
)
PLACEBO_HINT = (
    "Track every reduction in the stated field, and keep all butterfly "
    "coefficient equations consistently ordered."
)

# Filled after the script-owned oracle runs.  A preliminary local run therefore
# cannot be mistaken for oracle evidence.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES = r"""
Paper triage.  Section II defines the generalized closed butterfly
V_i(x,y)=(R_i(x,y),R_i(y,x)) over GF(2^n), with
R_i(x,y)=(x+alpha*y)^(2^i+1)+beta*y^(2^i+1).  Theorem 1 fixes the exact good-
coefficient condition: for odd n and gcd(i,n)=1, nonzero alpha,beta with
phi_4 != 0 and phi_2^(2^i)=phi_1*phi_4^(2^i-1) produce a permutation with
boomerang uniformity four.  This module uses the native i=1 case and also fixes
t=phi_2/phi_4 so that a witness is sparse rather than the always-valid (1,1)
pair.  Section V is the decisive easy-regime warning: experiments indicate that
these butterflies are affine equivalent to the Gold function.  In addition,
the coefficient witness here is recoverable in polynomial time by a half-trace.
Those facts rule out Track A and require the explicit Track B declaration.

Construction.  Sample s first in GF(2^n), excluding 0 and 1, and put
t=s^2+s and d=t+1.  For odd n, t has absolute trace zero and d is nonzero.
Set alpha=s^2/d and beta=d^(-3).  Direct substitution into the Section II
formulas (specialized to i=1) gives phi_2=t*phi_4,
phi_2^2=phi_1*phi_4, and phi_4 != 0.  Thus this is inverse generation by a
composition of exact identities, not a search for a pair satisfying the public
instance.  Replacing s by s+1 gives the other accepted witness.

Attack handling.  There are no separately distributed plants and decoys: the
answer and public invariant are images of one uniformly sampled field element.
The panel checks minimum/maximum Hamming-weight guesses, lexicographically
small coefficients, 512 uniform structure-aware restarts, and a small ansatz
made from t,t+1,t^2,t^2+1.  The standard polynomial-time half-trace algorithm is
reported separately, as Track B requires, and succeeds on every tested seed.
""".strip()


# ---------------------------------------------------------------------------
# Exact binary-polynomial and finite-field arithmetic


def _validate_n(n: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer")
    if n < 3 or n % 2 == 0:
        raise ValueError("n must be an odd integer at least 3")


def _poly_degree(x: int) -> int:
    return x.bit_length() - 1


def _poly_remainder(value: int, modulus: int) -> int:
    md = _poly_degree(modulus)
    while value and _poly_degree(value) >= md:
        value ^= modulus << (_poly_degree(value) - md)
    return value


def _poly_gcd(a: int, b: int) -> int:
    while b:
        a, b = b, _poly_remainder(a, b)
    return a


def _mul_raw_mod(a: int, b: int, modulus: int, n: int) -> int:
    """Carryless product modulo a monic degree-n binary polynomial."""
    result = 0
    top = 1 << n
    while b:
        if b & 1:
            result ^= a
        b >>= 1
        a <<= 1
        if a & top:
            a ^= modulus
    return result & (top - 1)


def _prime_divisors(n: int) -> list[int]:
    out = []
    d = 2
    while d * d <= n:
        if n % d == 0:
            out.append(d)
            while n % d == 0:
                n //= d
        d += 1
    if n > 1:
        out.append(n)
    return out


def _is_irreducible(modulus: int, n: int) -> bool:
    """Rabin's exact irreducibility test over F_2."""
    if modulus >> n != 1 or modulus & 1 == 0:
        return False
    x = 0b10
    z = x
    for _ in range(n):
        z = _mul_raw_mod(z, z, modulus, n)
    if z != x:
        return False
    for prime in _prime_divisors(n):
        z = x
        for _ in range(n // prime):
            z = _mul_raw_mod(z, z, modulus, n)
        if _poly_gcd(z ^ x, modulus) != 1:
            return False
    return True


@functools.lru_cache(maxsize=None)
def _first_irreducible(n: int) -> int:
    """Lexicographically first monic odd irreducible of degree n."""
    _validate_n(n)
    high = 1 << n
    for low in range(1, high, 2):
        candidate = high | low
        if _is_irreducible(candidate, n):
            return candidate
    raise RuntimeError("no irreducible polynomial found")  # mathematically unreachable


class _FieldCounter:
    """Optional operation counter used only for measured reference costs."""

    __slots__ = ("field_additions", "field_multiplications", "field_squarings",
                 "bit_iterations", "reduction_xors")

    def __init__(self) -> None:
        self.field_additions = 0
        self.field_multiplications = 0
        self.field_squarings = 0
        self.bit_iterations = 0
        self.reduction_xors = 0

    @property
    def field_operations(self) -> int:
        return (self.field_additions + self.field_multiplications
                + self.field_squarings)

    @property
    def bit_operations(self) -> int:
        return self.bit_iterations + self.reduction_xors


def _add(a: int, b: int, counter: _FieldCounter | None = None) -> int:
    if counter is not None:
        counter.field_additions += 1
    return a ^ b


def _mul(a: int, b: int, modulus: int, n: int,
         counter: _FieldCounter | None = None) -> int:
    if counter is not None:
        counter.field_multiplications += 1
    result = 0
    top = 1 << n
    while b:
        if counter is not None:
            counter.bit_iterations += 1
        if b & 1:
            result ^= a
        b >>= 1
        a <<= 1
        if a & top:
            a ^= modulus
            if counter is not None:
                counter.reduction_xors += 1
    return result & (top - 1)


def _square(a: int, modulus: int, n: int,
            counter: _FieldCounter | None = None) -> int:
    if counter is not None:
        counter.field_squarings += 1
    # Do not count a square again as a generic field multiplication.
    return _mul_raw_counted(a, a, modulus, n, counter)


def _mul_raw_counted(a: int, b: int, modulus: int, n: int,
                     counter: _FieldCounter | None) -> int:
    result = 0
    top = 1 << n
    while b:
        if counter is not None:
            counter.bit_iterations += 1
        if b & 1:
            result ^= a
        b >>= 1
        a <<= 1
        if a & top:
            a ^= modulus
            if counter is not None:
                counter.reduction_xors += 1
    return result & (top - 1)


def _pow(a: int, exponent: int, modulus: int, n: int,
         counter: _FieldCounter | None = None) -> int:
    result = 1
    while exponent:
        if exponent & 1:
            result = _mul(result, a, modulus, n, counter)
        exponent >>= 1
        a = _square(a, modulus, n, counter)
    return result


def _inverse(a: int, modulus: int, n: int,
             counter: _FieldCounter | None = None) -> int:
    if a == 0:
        raise ZeroDivisionError("zero has no finite-field inverse")
    return _pow(a, (1 << n) - 2, modulus, n, counter)


def _trace(a: int, modulus: int, n: int) -> int:
    total = 0
    current = a
    for _ in range(n):
        total ^= current
        current = _square(current, modulus, n)
    if total not in (0, 1):
        raise AssertionError("absolute trace escaped the prime field")
    return total


def _half_trace(a: int, modulus: int, n: int,
                counter: _FieldCounter | None = None) -> int:
    """H(a)=sum_{j=0}^{(n-1)/2} a^(2^(2j)), for odd n."""
    result = a
    current = a
    for _ in range((n - 1) // 2):
        current = _square(current, modulus, n, counter)
        current = _square(current, modulus, n, counter)
        result = _add(result, current, counter)
    return result


# ---------------------------------------------------------------------------
# Paper identities and inverse construction


def _phis(alpha: int, beta: int, modulus: int, n: int) -> tuple[int, int, int]:
    """Section-II phi_1, phi_2, phi_4 specialized to i=1."""
    a2 = _square(alpha, modulus, n)
    a4 = _square(a2, modulus, n)
    a5 = _mul(a4, alpha, modulus, n)
    a6 = _mul(a4, a2, modulus, n)
    b2 = _square(beta, modulus, n)
    p1 = a6 ^ _mul(alpha, beta, modulus, n) ^ b2 ^ 1
    p2 = (a6 ^ a5 ^ a4 ^ a2 ^ alpha
          ^ _mul(a2, beta, modulus, n) ^ b2 ^ 1)
    p4 = a6 ^ a4 ^ a2 ^ b2 ^ 1
    return p1, p2, p4


def _certificate_from_hidden(s: int, modulus: int, n: int) -> tuple[int, int, int]:
    """Return (t,alpha,beta) from the sampled preimage s."""
    s2 = _square(s, modulus, n)
    t = s2 ^ s
    d = t ^ 1
    d_inv = _inverse(d, modulus, n)
    alpha = _mul(s2, d_inv, modulus, n)
    beta = _mul(_square(d_inv, modulus, n), d_inv, modulus, n)
    return t, alpha, beta


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a certified Theorem-1 coefficient-recovery instance."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_n(n)
    rng = random.Random(seed)
    modulus = _first_irreducible(n)
    q = 1 << n

    # s is sampled before either the public invariant or the witness exists.
    # Excluding 0 and 1 makes t nonzero; no rejection search touches the answer.
    s = rng.randrange(2, q)
    t, alpha, beta = _certificate_from_hidden(s, modulus, n)
    p1, p2, p4 = _phis(alpha, beta, modulus, n)
    if not (t and p4 and p2 == _mul(t, p4, modulus, n)
            and _square(p2, modulus, n) == _mul(p1, p4, modulus, n)):
        raise AssertionError("construction identity failed")
    if alpha in (0, 1) or beta == 0 or alpha == beta:
        raise AssertionError("constructed witness escaped the bounded language")

    return {
        "n": n,
        "i": 1,
        "modulus": modulus,
        "t": t,
        "answer": [alpha, beta],
    }


def render(inst: dict) -> str:
    """Render a complete finite-field problem and an exact answer contract."""
    n = inst["n"]
    q = 1 << n
    statement = f"""Recover coefficients of a cryptographic closed butterfly

Work in the binary finite field F = GF(2^{n}) represented as F_2[X]/(P).
Field elements are decimal integers from 0 through {q - 1}.  Integer bit j is
the coefficient of X^j.  The irreducible modulus is the integer

    P = {inst['modulus']}

(its bit n is the leading X^n term).  Addition in F is bitwise XOR.  To
multiply, multiply the corresponding binary polynomials without carries and
take the remainder modulo P.  Every product and power below is in F.

For coefficients alpha,beta in F, the paper's i=1 closed butterfly is

    R(x,y) = (x + alpha*y)^3 + beta*y^3,
    V(x,y) = (R(x,y), R(y,x)).

Define its three coefficient expressions

    phi1 = alpha^6 + alpha*beta + beta^2 + 1,
    phi2 = alpha^6 + alpha^5 + alpha^4 + alpha^2 + alpha
           + alpha^2*beta + beta^2 + 1,
    phi4 = alpha^6 + alpha^4 + alpha^2 + beta^2 + 1.

The public normalized invariant is

    t = {inst['t']}.

Find two decimal integers [alpha,beta] such that, in F:

  1. 0 < alpha,beta < {q}, alpha != 1, and alpha != beta;
  2. phi4 != 0;
  3. phi2 = t*phi4; and
  4. phi2^2 = phi1*phi4.

These are exactly the normalized i=1 coefficient identities used in Theorem 1
of the paper; a valid pair defines the displayed closed butterfly.  There may
be more than one accepted pair, and any pair satisfying every condition is a
valid witness.  All bounds are inclusive where written, and the list order is
[alpha,beta], not [beta,alpha].

"""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "Hint: " + STRUCTURAL_HINT + "\n\n"
    elif mode == "placebo":
        statement += "Hint: " + PLACEBO_HINT + "\n\n"
    statement += (
        "Give your final answer inside <answer></answer> tags as one JSON list "
        "of two decimal integers.\n"
        "Example: <answer>[2, 3]</answer>\n"
        "Output nothing else inside the tags."
    )
    return statement


def parse_answer(text: str) -> object | None:
    """Parse the last tagged JSON pair, tolerating prose and markdown fences."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\s*>(.*?)</answer\s*>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    if not blocks:
        return None
    body = blocks[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        # Also tolerate the exact comma-pair notation models commonly emit.
        match = re.fullmatch(r"\s*(\d+)\s*,\s*(\d+)\s*", body)
        if not match:
            return None
        value = [int(match.group(1)), int(match.group(2))]
    if (not isinstance(value, list) or len(value) != 2
            or any(isinstance(x, bool) or not isinstance(x, int) for x in value)):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid witness using only exact finite-field identities."""
    # This function deliberately never reads inst["answer"].
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) != 2:
        return False, "answer must contain exactly two field elements"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "both field elements must be decimal integers"
    alpha, beta = answer
    q = 1 << inst["n"]
    if not (0 <= alpha < q and 0 <= beta < q):
        return False, "a field-element encoding is out of range"
    if alpha == 0 or beta == 0:
        return False, "both coefficients must be nonzero"
    if alpha == 1:
        return False, "alpha must not equal one for this nonzero-invariant family"
    if alpha == beta:
        return False, "the two coefficients must be distinct"

    p1, p2, p4 = _phis(alpha, beta, inst["modulus"], inst["n"])
    if p4 == 0:
        return False, "phi4 is zero"
    if p2 != _mul(inst["t"], p4, inst["modulus"], inst["n"]):
        return False, "the normalized identity phi2=t*phi4 fails"
    if _square(p2, inst["modulus"], inst["n"]) != _mul(
            p1, p4, inst["modulus"], inst["n"]):
        return False, "the Theorem-1 identity phi2^2=phi1*phi4 fails"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniform sample from every explicitly legal coefficient pair."""
    q = 1 << inst["n"]
    alpha = rng.randrange(2, q)
    # Uniform in {1,...,q-1} minus alpha.
    beta = rng.randrange(1, q - 1)
    if beta >= alpha:
        beta += 1
    return [alpha, beta]


def search_space(inst: dict) -> int | None:
    q = 1 << inst["n"]
    return (q - 2) ** 2


def enumerate_all(inst: dict) -> int | None:
    """Brute-force exact count only when the declared language is small."""
    size = search_space(inst)
    if size is None or size > 200_000:
        return None
    q = 1 << inst["n"]
    count = 0
    for alpha in range(2, q):
        for beta in range(1, q):
            if beta != alpha and verify(inst, [alpha, beta])[0]:
                count += 1
    return count


def _frobenius(value: int, power: int, modulus: int, n: int) -> int:
    for _ in range(power % n):
        value = _square(value, modulus, n)
    return value


def canonical_key(inst: dict) -> str:
    """Canonicalize the public invariant under every GF(2)-automorphism."""
    n = inst["n"]
    modulus = inst["modulus"]
    orbit = []
    value = inst["t"]
    for _ in range(n):
        orbit.append(value)
        value = _square(value, modulus, n)
    # The modulus is fixed canonically by n.  Keeping it in the key rejects a
    # malformed instance without pretending the seed is structural data.
    return json.dumps([n, inst["i"], modulus, min(orbit)], separators=(",", ":"))


def escalate(params: dict) -> dict | None:
    """Raise the extension degree while the no-tool operation cap permits it."""
    n = params.get("n")
    if isinstance(n, bool) or not isinstance(n, int) or n >= 71:
        return None
    return {"n": n + 10}


# ---------------------------------------------------------------------------
# Reference algorithm and construction-aware adversaries


def _reference_algorithm(inst: dict) -> dict:
    """Polynomial-time Track-B solver: half-trace then direct formulas."""
    n = inst["n"]
    modulus = inst["modulus"]
    counter = _FieldCounter()
    start = time.perf_counter()
    s = _half_trace(inst["t"], modulus, n, counter)
    d = _add(inst["t"], 1, counter)
    d_inv = _inverse(d, modulus, n, counter)
    alpha = _mul(_square(s, modulus, n, counter), d_inv,
                 modulus, n, counter)
    beta = _mul(_square(d_inv, modulus, n, counter), d_inv,
                modulus, n, counter)
    answer = [alpha, beta]
    elapsed = time.perf_counter() - start
    ok, reason = verify(inst, answer)
    return {
        "answer": answer,
        "ok": ok,
        "reason": reason,
        "wall_clock_sec": elapsed,
        "field_operations": counter.field_operations,
        "bit_operations": counter.bit_operations,
    }


def _candidate_ok(inst: dict, answer: list[int]) -> bool:
    return verify(inst, answer)[0]


def _attack_outlier_bit_weight(inst: dict) -> bool:
    n = inst["n"]
    q = 1 << n
    alphas = [1 << j for j in range(1, n)] + [q - 1]
    betas = [inst["t"], inst["t"] ^ 1]
    for alpha in alphas:
        for beta in betas:
            if alpha not in (0, 1) and beta not in (0, alpha):
                if _candidate_ok(inst, [alpha, beta]):
                    return True
    return False


def _attack_greedy_small(inst: dict) -> bool:
    # The lexicographically first legal coefficients and their first few peers.
    for alpha in range(2, 7):
        for beta in range(1, 7):
            if alpha != beta and _candidate_ok(inst, [alpha, beta]):
                return True
    return False


def _attack_random_restart(inst: dict, seed: int, restarts: int = 512) -> bool:
    rng = random.Random(seed ^ 0x1912026400)
    for _ in range(restarts):
        if _candidate_ok(inst, random_candidate(inst, rng)):
            return True
    return False


def _attack_small_expression_ansatz(inst: dict) -> bool:
    t = inst["t"]
    t2 = _square(t, inst["modulus"], inst["n"])
    values = {t, t ^ 1, t2, t2 ^ 1}
    for alpha in values:
        for beta in values:
            if alpha not in (0, 1) and beta not in (0, alpha):
                if _candidate_ok(inst, [alpha, beta]):
                    return True
    return False


def _frobenius_relabel(inst: dict, power: int) -> tuple[dict, list[int]]:
    """Carry an instance and witness through x -> x^(2^power)."""
    moved = {k: v for k, v in inst.items() if k != "answer"}
    moved["t"] = _frobenius(inst["t"], power, inst["modulus"], inst["n"])
    carried = [
        _frobenius(x, power, inst["modulus"], inst["n"])
        for x in inst["answer"]
    ]
    moved["answer"] = carried
    return moved, carried


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))
    # Tokenizers vary; one token per character is a safe, measured upper bound.
    tokens = len(encoded)
    elements = len(answer) if isinstance(answer, list) else 1
    return len(encoded), tokens, elements


def selftest() -> dict:
    """Run all mandatory gates and return their measured JSON-native report."""
    report: dict = {}

    # G1 over every named preset and several seeds, plus JSON-native answers.
    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2026):
            trial = make_instance(seed=seed, **params)
            ok, why = verify(trial, trial["answer"])
            json_ok = json.loads(json.dumps(trial["answer"])) == trial["answer"]
            g1_checks += 1
            if not (ok and json_ok):
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": why, "json_native": json_ok})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **ship_params)
    alpha, beta = inst["answer"]

    corruptions = {
        "drop_one": [alpha],
        "swap_order": [beta, alpha],
        "duplicate": [alpha, alpha],
        "empty": [],
        "out_of_range": [1 << inst["n"], beta],
    }
    rejection_reasons = {}
    all_rejected = True
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        all_rejected &= not ok
        rejection_reasons[name] = why
    distinct_reasons = len(set(rejection_reasons.values())) == len(corruptions)
    report["G2_rejects_corruption"] = {
        "pass": all_rejected and distinct_reasons,
        "rejections": rejection_reasons,
        "distinct_reasons": len(set(rejection_reasons.values())),
    }

    realistic = (
        "I reduced the two identities in the polynomial basis.\n\n"
        "```text\nFinal result follows.\n```\n"
        f"<answer>\n{json.dumps(inst['answer'])}\n</answer>\n"
        "The order is alpha, beta."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0]
                and parse_answer("garbage") is None,
        "parsed_matches": parsed == inst["answer"],
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # One 200k structure-aware sample serves both G4 and shipping-density G5.
    guess_rng = random.Random(0x19120240)
    guess_total = 200_000
    hits = 0
    sample_start = time.perf_counter()
    for _ in range(guess_total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    sampling_seconds = time.perf_counter() - sample_start
    empirical = hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": empirical < 1e-6,
        "hits": hits,
        "total": guess_total,
        "empirical_probability": empirical,
        "prior": (
            "uniform over all distinct nonzero [alpha,beta] with alpha != 1, "
            "exactly the explicitly bounded certificate language"
        ),
        "candidate_space": search_space(inst),
        "sampling_wall_seconds": sampling_seconds,
    }

    baseline_start = time.perf_counter()
    baseline_success = _attack_random_restart(inst, 0xB451, restarts=4096)
    baseline_seconds = time.perf_counter() - baseline_start
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": (empirical < 1e-6 and not baseline_success
                 and demo_count is not None),
        "shipping_observed_valid_fraction": empirical,
        "shipping_density_sample_count": guess_total,
        "shipping_valid_hits": hits,
        "shipping_candidate_space": search_space(inst),
        "known_valid_answers_from_two_Artin_Schreier_roots": 2,
        "baseline_wall_seconds": baseline_seconds,
        "baseline_iterations": 4096,
        "baseline_successes": int(baseline_success),
        "demo_exact_solution_count": demo_count,
        "enumerate_all_shipping": None,
    }

    attack_successes = {
        "outlier_extreme_hamming_weight": 0,
        "greedy_lexicographically_small_coefficients": 0,
        "random_restart_512_structure_aware": 0,
        "obvious_t_tplus1_tsquare_ansatz": 0,
    }
    reference_runs = []
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **ship_params)
        attack_successes["outlier_extreme_hamming_weight"] += int(
            _attack_outlier_bit_weight(trial))
        attack_successes["greedy_lexicographically_small_coefficients"] += int(
            _attack_greedy_small(trial))
        attack_successes["random_restart_512_structure_aware"] += int(
            _attack_random_restart(trial, seed))
        attack_successes["obvious_t_tplus1_tsquare_ansatz"] += int(
            _attack_small_expression_ansatz(trial))
        reference_runs.append(_reference_algorithm(trial))
    ref_ok = sum(int(run["ok"]) for run in reference_runs)
    all_failed = all(value == 0 for value in attack_successes.values())
    ref_wall = sum(run["wall_clock_sec"] for run in reference_runs)
    ref_field = sum(run["field_operations"] for run in reference_runs)
    ref_bits = sum(run["bit_operations"] for run in reference_runs)
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_ok == 8,
        "attacks": {
            name: {"successes": successes, "attempts": 8}
            for name, successes in attack_successes.items()
        },
        "reference_algorithm": {
            "name": "Artin-Schreier half-trace plus direct coefficient formulas",
            "complexity": "O(n^3) bit operations with schoolbook GF(2^n) arithmetic",
            "wall_clock_sec": ref_wall,
            "mean_wall_clock_sec": ref_wall / 8,
            "operations": ref_bits,
            "mean_bit_operations": ref_bits // 8,
            "mean_field_operations": ref_field // 8,
            "solves": f"{ref_ok}/8, as expected",
        },
    }

    doubled_n = 2 * ship_params["n"] + 1  # next valid odd degree above 2n
    doubled = make_instance(n=doubled_n, seed=77)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_n > 2 * ship_params["n"],
        "base_n": ship_params["n"],
        "doubled_valid_n": doubled_n,
        "doubled_verify": doubled_why,
        "candidate_space_bit_growth_lower_bound": 2 * ship_params["n"],
    }

    invariance_checks = 0
    witness_checks = 0
    transform_count = 0
    for seed in range(20):
        trial = make_instance(seed=seed + 700, **ship_params)
        # Basic automorphism, a second power, its inverse, and a composition.
        for power in (1, 2, trial["n"] - 1, 3):
            moved, carried = _frobenius_relabel(trial, power)
            transform_count += 1
            invariance_checks += int(canonical_key(moved) == canonical_key(trial))
            witness_checks += int(verify(moved, carried)[0])
    unrelated = {
        canonical_key(make_instance(seed=seed + 9000, **ship_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": (invariance_checks == transform_count
                 and witness_checks == transform_count and len(unrelated) == 20),
        "invariance_checks": invariance_checks,
        "invariance_attempts": transform_count,
        "transformed_witness_checks": witness_checks,
        "unrelated_distinct": len(unrelated),
        "unrelated_attempts": 20,
        "transformations": (
            "Frobenius automorphisms x->x^(2^k), including powers 1, 2, -1 "
            "and the composition of powers 1 and 2"
        ),
    }

    chars, tokens, elements = _answer_metrics(inst["answer"])
    route = _reference_algorithm(inst)
    intended_operations = route["field_operations"]
    evidence = G9_EVIDENCE
    hinted_pass = evidence["hinted_verdict"] == "hardened"
    within_caps = (chars <= 2000 and tokens <= 500 and elements <= 256
                   and intended_operations <= 300)
    h_attempts = evidence["hinted"]["attempts"]
    p_attempts = evidence["placebo"]["attempts"]
    h_rate = evidence["hinted"]["solved"] / h_attempts if h_attempts else 0.0
    p_rate = evidence["placebo"]["solved"] / p_attempts if p_attempts else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": hinted_pass and within_caps,
        "arms": {
            "bare": dict(evidence["bare"]),
            "hinted": dict(evidence["hinted"]),
            "placebo": dict(evidence["placebo"]),
        },
        "hinted_minus_placebo": h_rate - p_rate,
        "hinted_verdict": evidence["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship_params)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
