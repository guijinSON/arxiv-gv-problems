"""Verified problem generator for arXiv:2103.10687.

The paper constructs low-differential-uniformity permutations on GF(2^(5k))
by replacing the Dobbertin APN power on the subfield GF(2^k).  This module
asks for a normalized differential witness in a multiplicative subfield
coset.  It samples that witness first and derives the displayed target, so
generation never solves the completed instance.

All finite-field arithmetic is exact integer arithmetic on binary-polynomial
coefficient masks.  Importing this module performs no I/O.
"""

from __future__ import annotations

import functools
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
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - the implementation is stdlib-only
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "binary extension field GF(2^(5k))",
        "subfield GF(2^k) in a polynomial basis",
        "Dobbertin piecewise permutation",
        "finite-field differential witness",
    ],
    "verification_operations": [
        "exact binary-polynomial squaring and modular reduction",
        "absolute trace over GF(2)",
        "exact Artin--Schreier identity comparison",
        "exact exponentiation and coordinate comparison in GF(2^(5k))",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Writing x=Uz exposes that the Dobbertin exponent is 3 on the "
        "subfield, turning a huge ambient differential search into one "
        "Artin--Schreier equation."
    ),
    "hardness_basis": (
        "Track B, Theorem 3.2 and Corollary 3.4 with odd k, ambient degree "
        "5k, and g(x)=x^3: the reference half-trace algorithm uses O(k) "
        "field squarings (O(k^3) scalar GF(2) work with the module's "
        "schoolbook polynomial-basis accounting); at shipping k=151 it "
        "averaged 880,088 counted scalar operations and 0.01604 seconds "
        "(888,166 and 0.03651 seconds maximum) in the recorded full self-test, "
        "while the compact route uses 227 exact field additions/squarings."
    ),
    "max_answer_tokens": 16,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object {\"z\":\"0x...\",\"trace\":0}.  The fixed-width "
        "lowercase hexadecimal string is the coefficient mask of a nonzero "
        "polynomial of degree < k in GF(2)[X]/(M); its absolute trace must be "
        "zero."
    ),
    "bounds": {
        "n_fields": 2,
        "fields": ["z", "trace"],
        "coefficient_alphabet": [0, 1],
        "degree_bound": "k-1",
        "shipping_degree_bound": 150,
        "normalization": "nonzero and absolute trace zero",
        "shipping_hex_digits": 38,
    },
}

# n is a public scale index.  k=10n+1 is always odd and coprime to 5, exactly
# the regime needed both by the paper and by the fixed quintic extension below.
DIFFICULTY = {
    "demo": {"n": 1},       # k=11: genuinely workable on paper
    "easy": {"n": 15},      # k=151: 227 compact field operations
    "medium": {"n": 17},    # k=171: 257 compact field operations
    "hard": {"n": 19},      # k=191: 287 compact field operations
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The key invariant is the reduction of the Dobbertin exponent to 3 on "
    "the subfield K."
)
PLACEBO_HINT = (
    "The key precaution is the consistent use of the stated polynomial basis "
    "for every field element."
)

# Replaced with script-owned measurements after the three hardening arms run.
G9_MEASUREMENTS = {
    "bare": {"solved": 0, "attempts": 3, "error_calls": 0},
    "hinted": {"solved": 0, "attempts": 0, "error_calls": 4},
    "placebo": {"solved": 0, "attempts": 0, "error_calls": 4},
    "hinted_verdict": "oracle_unreachable_http_403_key_limit",
}

NOTES = r"""
Paper definition and Step 0.  Section 1 defines D_a f(x)=f(x+a)+f(x)
and differential uniformity by exact solution counts.  Lemma 3.1 is the
subfield-exclusion result used in Theorem 3.2.  Theorem 3.2 requires odd k,
n=5k, and a low-uniformity permutation g on GF(2^k); it proves that the
piecewise function is a permutation and is differentially 4- or 6-uniform.
Corollary 3.4 licenses g(x)=x^3 (its m=2 case), an APN permutation for odd k.
The remark after Theorem 3.2 is the easy boundary: even k loses permutation,
and a nonpermutation g also loses permutation.  The tables use k=2 only for
experiments and explicitly say those functions are not permutations.

Certificate-producing algorithm.  This is Track B, not Track A.  A generic
difference-table scan evaluates 2^(5k) ambient inputs for the displayed (a,B).
On this distribution, however, the exact substitution x=Uz reduces the
equation to z^2+z=c+1 over GF(2^k).  For odd k and trace-zero t, the half-trace
H(t)=sum_{i=0}^{(k-1)/2} t^(2^(2i)) satisfies H(t)^2+H(t)=t and itself has
trace zero.  That is the reference algorithm: O(k) field squarings, or O(k^3)
scalar GF(2) coefficient work under the deliberately explicit schoolbook
accounting used by selftest.  It is efficient and succeeds 8/8 as expected.
The no-tool gap is between carrying out hundreds of thousands of coefficient
operations mechanically and recognizing a 227-operation field-level route.

Construction.  Let K=GF(2)[X]/(M), with k=10n+1 and deterministic irreducible
M.  Since U^5+U^2+1 is irreducible over GF(2) and gcd(k,5)=1,
L=K[U]/(U^5+U^2+1) is GF(2^(5k)).  Sample a nonzero trace-zero z uniformly,
then set c=z^2+z+1 and B=c(1+U^3).  The sampled z is retained as the answer.
For d=2^(4k)+2^(3k)+2^(2k)+2^k-1, d is congruent to 3 modulo 2^k-1 and to 29
modulo 31.  Because U^29=1+U^3, and Uz,U(z+1) are outside K,

  F(U(z+1))+F(Uz) = U^d ((z+1)^d+z^d)
                    = (1+U^3)(z^2+z+1) = B.

The verifier checks both this reduced exact identity and the full extension-
field differential, and never reads the planted answer.  G1 independently
exercises the full equation at every preset.

Attacks.  Plants and random candidates are drawn from the identical uniform
nonzero trace-zero hyperplane.  The panel tries the smallest encoding (a
magnitude/outlier probe), copying the target support, a bounded greedy residual
descent, a short truncated half-trace (the plausible in-context ansatz), and
random restarts.  The successful complete half-trace is reported separately as
Track B's reference algorithm.  Escalation increases k while the two-field JSON
answer stays fixed-size; it stops only when the 300-operation no-tool cap would
be crossed.
""".strip()


def _poly_mod(value: int, modulus: int) -> int:
    degree = modulus.bit_length() - 1
    while value and value.bit_length() - 1 >= degree:
        value ^= modulus << (value.bit_length() - 1 - degree)
    return value


def _poly_gcd(a: int, b: int) -> int:
    while b:
        a, b = b, _poly_mod(a, b)
    return a


def _prime_divisors(value: int) -> list[int]:
    result: list[int] = []
    divisor = 2
    while divisor * divisor <= value:
        if value % divisor == 0:
            result.append(divisor)
            while value % divisor == 0:
                value //= divisor
        divisor += 1
    if value > 1:
        result.append(value)
    return result


def _gf_mul(a: int, b: int, modulus: int, degree: int) -> int:
    """Multiply coefficient masks in GF(2)[X]/(modulus)."""
    result = 0
    while b:
        if b & 1:
            result ^= a
        b >>= 1
        a <<= 1
        if a >> degree:
            a ^= modulus
    return result


def _gf_square(a: int, modulus: int, degree: int) -> int:
    return _gf_mul(a, a, modulus, degree)


def _gf_pow(a: int, exponent: int, modulus: int, degree: int) -> int:
    result = 1
    while exponent:
        if exponent & 1:
            result = _gf_mul(result, a, modulus, degree)
        exponent >>= 1
        if exponent:
            a = _gf_square(a, modulus, degree)
    return result


def _is_irreducible(modulus: int, degree: int) -> bool:
    if modulus.bit_length() - 1 != degree or not modulus & 1:
        return False
    x = 2
    power = x
    checkpoints = {degree // p for p in _prime_divisors(degree)}
    for index in range(1, degree + 1):
        power = _gf_square(power, modulus, degree)
        if index in checkpoints and _poly_gcd(power ^ x, modulus) != 1:
            return False
    return power == x


@functools.lru_cache(maxsize=None)
def _find_irreducible(degree: int) -> int:
    """Deterministically find one monic irreducible binary polynomial."""
    rng = random.Random(0x210310687 ^ (degree << 17))
    while True:
        middle = rng.getrandbits(degree - 1) << 1
        candidate = (1 << degree) | middle | 1
        if _is_irreducible(candidate, degree):
            return candidate


@functools.lru_cache(maxsize=None)
def _trace_mask(modulus: int, degree: int) -> int:
    """Mask m such that Tr(a)=parity(a&m), derived exactly once."""
    mask = 0
    for basis_index in range(degree):
        value = 1 << basis_index
        conjugate = value
        trace_value = 0
        for _ in range(degree):
            trace_value ^= conjugate
            conjugate = _gf_square(conjugate, modulus, degree)
        if trace_value == 1:
            mask |= 1 << basis_index
        elif trace_value != 0:
            raise ArithmeticError("absolute trace did not land in GF(2)")
    return mask


def _trace_fast(value: int, modulus: int, degree: int) -> int:
    return (value & _trace_mask(modulus, degree)).bit_count() & 1


def _trace_exact(value: int, modulus: int, degree: int) -> int:
    conjugate = value
    result = 0
    for _ in range(degree):
        result ^= conjugate
        conjugate = _gf_square(conjugate, modulus, degree)
    if result not in (0, 1):
        raise ArithmeticError("absolute trace did not land in GF(2)")
    return result


def _hex_width(degree: int) -> int:
    return (degree + 3) // 4


def _hex_element(value: int, degree: int) -> str:
    return "0x" + format(value, f"0{_hex_width(degree)}x")


def _answer_from_value(value: int, degree: int) -> dict[str, object]:
    return {"z": _hex_element(value, degree), "trace": 0}


def _sample_trace_zero_nonzero(rng: random.Random, modulus: int,
                               degree: int) -> int:
    # Projection y -> y + Tr(y) is exactly two-to-one onto the trace-zero
    # hyperplane because degree is odd and therefore Tr(1)=1.
    while True:
        value = rng.randrange(1 << degree)
        value ^= _trace_fast(value, modulus, degree)
        if value:
            return value


def _extension_mul(a: tuple[int, ...], b: tuple[int, ...], modulus: int,
                   degree: int) -> tuple[int, ...]:
    """Multiply in K[U]/(U^5+U^2+1), for construction cross-checks."""
    raw = [0] * 9
    for i, left in enumerate(a):
        for j, right in enumerate(b):
            if left and right:
                raw[i + j] ^= _gf_mul(left, right, modulus, degree)
    # U^5=U^2+1 in characteristic two.
    for power in range(8, 4, -1):
        coefficient = raw[power]
        if coefficient:
            raw[power - 5] ^= coefficient
            raw[power - 3] ^= coefficient
    return tuple(raw[:5])


def _extension_pow(value: tuple[int, ...], exponent: int, modulus: int,
                   degree: int) -> tuple[int, ...]:
    result = (1, 0, 0, 0, 0)
    while exponent:
        if exponent & 1:
            result = _extension_mul(result, value, modulus, degree)
        exponent >>= 1
        if exponent:
            value = _extension_mul(value, value, modulus, degree)
    return result


def _extension_add(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(left ^ right for left, right in zip(a, b))


def _paper_function(value: tuple[int, ...], exponent: int, modulus: int,
                    degree: int) -> tuple[int, ...]:
    if all(coefficient == 0 for coefficient in value[1:]):
        return _extension_pow(value, 3, modulus, degree)
    return _extension_pow(value, exponent, modulus, degree)


def _full_equation_holds(inst: dict, z: int) -> bool:
    degree = inst["k"]
    modulus = inst["modulus"]
    u = (0, 1, 0, 0, 0)
    x = (0, z, 0, 0, 0)
    x_plus_u = _extension_add(x, u)
    left = _extension_add(
        _paper_function(x_plus_u, inst["d"], modulus, degree),
        _paper_function(x, inst["d"], modulus, degree),
    )
    return left == tuple(inst["target"])


def make_instance(n: int, seed: int = 0, **params: object) -> dict:
    """Inverse-generate a normalized native finite-field differential witness."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer scale index")
    if params:
        unknown = ", ".join(sorted(params))
        raise TypeError(f"unknown parameters: {unknown}")
    degree = 10 * n + 1
    modulus = _find_irreducible(degree)
    rng = random.Random(seed)
    z = _sample_trace_zero_nonzero(rng, modulus, degree)
    c = _gf_square(z, modulus, degree) ^ z ^ 1
    exponent = ((1 << (4 * degree)) + (1 << (3 * degree))
                + (1 << (2 * degree)) + (1 << degree) - 1)
    # U^d=U^29=1+U^3 because degree == 1 (mod 5).
    target = [c, 0, 0, c, 0]
    return {
        "scale_n": n,
        "k": degree,
        "ambient_degree": 5 * degree,
        "modulus": modulus,
        "extension_relation": [1, 0, 1, 0, 0, 1],
        "d": exponent,
        "target": target,
        "answer": _answer_from_value(z, degree),
    }


def render(inst: dict) -> str:
    """Render a self-contained finite-field differential-witness problem."""
    degree = inst["k"]
    width = _hex_width(degree)
    modulus_width = (degree + 4) // 4
    modulus_hex = "0x" + format(inst["modulus"], f"0{modulus_width}x")
    target_hex = [_hex_element(value, degree) for value in inst["target"]]
    example = json.dumps(
        {"z": "0x" + "0" * (width - 1) + "2", "trace": 0},
        separators=(",", ":"),
    )
    statement = f"""Find a normalized differential witness for a piecewise Dobbertin permutation.

Binary polynomials are encoded as hexadecimal coefficient masks: bit i is the
coefficient of X^i.  All hexadecimal strings are lowercase and include leading
zeroes to their stated width.

Let k={degree} and let

  K = GF(2)[X]/(M),   M mask = {modulus_hex}.

M is monic irreducible of degree k.  Addition in K is bitwise XOR and
multiplication is carryless polynomial multiplication reduced modulo M.  For
q in K, its absolute trace is

  Tr(q) = q + q^2 + q^(2^2) + ... + q^(2^(k-1)),

which is either 0 or 1.

Let L=K[U]/(U^5+U^2+1), so every element of L has a unique coordinate vector
(q0,q1,q2,q3,q4) meaning q0+q1*U+...+q4*U^4.  Put

  d = 2^(4k)+2^(3k)+2^(2k)+2^k-1.

Define F:L->L by

  F(y) = y^3  if y lies in K (coordinates q1=q2=q3=q4=0),
  F(y) = y^d  otherwise.

This is the g(y)=y^3 case of the paper's piecewise permutation.  Set a=U.
The target B, written as five K-coordinate masks of exactly {width} hex digits,
is

  B = {json.dumps(target_hex, separators=(',', ':'))}.

Find a NONZERO z in K such that Tr(z)=0 and

  F(U*z + a) + F(U*z) = B.

All additions are in characteristic two.  Equality means exact equality of all
five K coordinates.  The trace-zero condition chooses one of the two roots;
there is exactly one admissible answer.  Encode z as exactly {width} lowercase
hexadecimal digits after 0x.  The JSON field named trace is the integer 0, not a
string.  No approximation is permitted.

Give your final answer inside <answer></answer> tags as the JSON object
{{\"z\":\"0x...\",\"trace\":0}} with exactly those two fields.
Example of the required syntax: <answer>{example}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON object, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    if not matches:
        return None
    payload = matches[-1].strip()
    payload = re.sub(r"^```(?:json|text)?\s*", "", payload,
                     flags=re.IGNORECASE)
    payload = re.sub(r"\s*```$", "", payload)
    def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(payload, object_pairs_hook=reject_duplicate_keys)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _instance_data(inst: dict) -> tuple[int, int, int]:
    degree = inst.get("k")
    scale = inst.get("scale_n")
    modulus = inst.get("modulus")
    if any(isinstance(value, bool) or not isinstance(value, int)
           for value in (degree, scale, modulus)):
        raise ValueError("noninteger field parameter")
    if scale < 1 or degree != 10 * scale + 1:
        raise ValueError("k must equal 10*n+1")
    if modulus != _find_irreducible(degree):
        raise ValueError("unexpected field modulus")
    if inst.get("ambient_degree") != 5 * degree:
        raise ValueError("ambient degree is not 5k")
    if inst.get("extension_relation") != [1, 0, 1, 0, 0, 1]:
        raise ValueError("extension relation is not U^5+U^2+1")
    expected_d = ((1 << (4 * degree)) + (1 << (3 * degree))
                  + (1 << (2 * degree)) + (1 << degree) - 1)
    if inst.get("d") != expected_d:
        raise ValueError("wrong Dobbertin exponent")
    target = inst.get("target")
    if (not isinstance(target, list) or len(target) != 5
            or any(isinstance(value, bool) or not isinstance(value, int)
                   or not 0 <= value < 1 << degree for value in target)):
        raise ValueError("invalid target coordinates")
    if target[1] or target[2] or target[4] or target[0] != target[3]:
        raise ValueError("target is not in the promised (1+U^3) coset")
    return degree, modulus, target[0]


def _decode_answer(answer: object, degree: int) -> tuple[int | None, str | None]:
    if not isinstance(answer, dict):
        return None, "answer must be a JSON object"
    if not answer:
        return None, "answer object is empty"
    if set(answer) != {"z", "trace"}:
        if "z" not in answer:
            return None, "answer is missing field z"
        if "trace" not in answer:
            return None, "answer is missing the trace normalization"
        return None, "answer has unexpected or duplicated fields"
    if isinstance(answer["trace"], bool) or answer["trace"] != 0:
        return None, "trace marker must be the integer zero"
    encoded = answer["z"]
    if not isinstance(encoded, str):
        return None, "z must be a hexadecimal string"
    width = _hex_width(degree)
    if not re.fullmatch(r"0x[0-9a-f]+", encoded):
        return None, "z is not canonical lowercase hexadecimal"
    if len(encoded) != width + 2:
        return None, f"z must contain exactly {width} hexadecimal digits"
    value = int(encoded[2:], 16)
    if value >= 1 << degree:
        return None, "z is outside the degree-k field range"
    if value == 0:
        return None, "z must be nonzero"
    return value, None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Verify any admissible witness using exact finite-field identities."""
    try:
        degree, modulus, c = _instance_data(inst)
    except (KeyError, TypeError, ValueError) as exc:
        return False, f"invalid instance: {exc}"
    value, error = _decode_answer(answer, degree)
    if error is not None or value is None:
        return False, error or "malformed z"
    try:
        if _trace_exact(value, modulus, degree) != 0:
            return False, "z does not have absolute trace zero"
    except ArithmeticError as exc:
        return False, f"trace computation failed: {exc}"
    if (_gf_square(value, modulus, degree) ^ value ^ 1) != c:
        return False, "the exact differential identity does not equal B"
    # Check the native equation stated to the solver as well as its reduced
    # Artin--Schreier form.  This is deliberately last: malformed and incorrect
    # candidates are rejected by the cheap exact checks above.
    if not _full_equation_holds(inst, value):
        return False, "the full extension-field differential does not equal B"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the stated nonzero trace-zero certificate language."""
    degree, modulus, _ = _instance_data(inst)
    value = _sample_trace_zero_nonzero(rng, modulus, degree)
    return _answer_from_value(value, degree)


def search_space(inst: dict) -> int | None:
    """Count nonzero elements of the trace-zero hyperplane exactly."""
    degree, _, _ = _instance_data(inst)
    return (1 << (degree - 1)) - 1


def enumerate_all(inst: dict) -> int | None:
    """Count exact valid witnesses when the normalized language is small."""
    space = search_space(inst)
    if space is None or space > 65_536:
        return None
    degree, modulus, c = _instance_data(inst)
    count = 0
    for value in range(1, 1 << degree):
        if (_trace_fast(value, modulus, degree) == 0
                and (_gf_square(value, modulus, degree) ^ value ^ 1) == c):
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Canonicalize the target under every Frobenius field automorphism."""
    degree, modulus, c = _instance_data(inst)
    orbit = []
    value = c
    for _ in range(degree):
        orbit.append(value)
        value = _gf_square(value, modulus, degree)
    normalized = {"k": degree, "M": modulus, "frobenius_orbit_min": min(orbit)}
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the field while keeping the two-field answer shape unchanged."""
    result = {key: value for key, value in params.items() if key != "_preset"}
    n = int(result.get("n", 1))
    next_degree = 10 * (n + 1) + 1
    # The half-trace route costs (3k+1)/2 exact field operations.
    if (3 * next_degree + 1) // 2 > 300:
        return "cap_bound"
    result["n"] = n + 1
    return result


def _half_trace(target_t: int, modulus: int, degree: int,
                counted: bool = False) -> tuple[int, dict[str, int]]:
    """Return H(t), with optional scalar-GF(2) operation accounting."""
    accumulator = 0
    term = target_t
    additions = 0
    squarings = 0
    scalar_operations = 0
    rounds = (degree + 1) // 2
    for index in range(rounds):
        accumulator ^= term
        additions += 1
        scalar_operations += degree
        if index + 1 < rounds:
            if counted:
                term, cost = _gf_square_counted(term, modulus, degree)
                scalar_operations += cost
                term, cost = _gf_square_counted(term, modulus, degree)
                scalar_operations += cost
            else:
                term = _gf_square(_gf_square(term, modulus, degree),
                                  modulus, degree)
            squarings += 2
    return accumulator, {
        "field_squarings": squarings,
        "field_additions": additions,
        "gf2_coefficient_operations": scalar_operations,
    }


def _gf_square_counted(value: int, modulus: int,
                       degree: int) -> tuple[int, int]:
    """Schoolbook square and exact scalar coefficient-operation count."""
    raw = 0
    operations = degree  # inspect each input coefficient
    for index in range(degree):
        if value >> index & 1:
            raw |= 1 << (2 * index)
            operations += 1
    modulus_weight = modulus.bit_count()
    while raw.bit_length() - 1 >= degree:
        raw ^= modulus << (raw.bit_length() - 1 - degree)
        operations += modulus_weight
    return raw, operations


def _compact_route(inst: dict, counted: bool = False
                   ) -> tuple[dict[str, object] | None, dict[str, int]]:
    degree, modulus, c = _instance_data(inst)
    value, metrics = _half_trace(c ^ 1, modulus, degree, counted=counted)
    metrics = dict(metrics)
    metrics["field_additions"] += 1  # t=c+1
    metrics["gf2_coefficient_operations"] += degree
    answer = _answer_from_value(value, degree)
    return (answer if value else None), metrics


def _valid_answer_fast(inst: dict, answer: object) -> bool:
    degree = inst["k"]
    value, error = _decode_answer(answer, degree)
    if error is not None or value is None:
        return False
    modulus = inst["modulus"]
    return (_trace_fast(value, modulus, degree) == 0
            and (_gf_square(value, modulus, degree) ^ value ^ 1)
            == inst["target"][0])


def _lowest_trace_zero(modulus: int, degree: int) -> int:
    value = 1
    while _trace_fast(value, modulus, degree) or value == 0:
        value += 1
    return value


def _attack_candidates(inst: dict, seed: int) -> dict[str, object | None]:
    degree, modulus, c = _instance_data(inst)
    t = c ^ 1
    fallback = _lowest_trace_zero(modulus, degree)

    # Magnitude/Hamming-weight outlier guess.
    smallest = fallback

    # The most obvious direct ansatz copies the Artin--Schreier target.
    support_copy = t if t else fallback

    # Bounded greedy descent over trace-zero basis vectors.  Twelve rounds are
    # deliberately an in-context effort, not hidden Gaussian elimination.
    greedy = 0
    unused = []
    for index in range(1, degree):
        basis = 1 << index
        if _trace_fast(basis, modulus, degree):
            basis ^= 1
        unused.append(basis)
    for _ in range(12):
        current_residual = (_gf_square(greedy, modulus, degree) ^ greedy ^ t)
        best = None
        best_weight = current_residual.bit_count()
        for basis in unused:
            candidate = greedy ^ basis
            residual = (_gf_square(candidate, modulus, degree)
                        ^ candidate ^ t)
            if residual.bit_count() < best_weight:
                best = basis
                best_weight = residual.bit_count()
        if best is None:
            break
        greedy ^= best
        unused.remove(best)
    if greedy == 0:
        greedy = fallback

    # A solver who knows the right family but cannot execute the whole route
    # might try only the first four even Frobenius conjugates.
    truncated = 0
    term = t
    for _ in range(4):
        truncated ^= term
        term = _gf_square(_gf_square(term, modulus, degree), modulus, degree)
    if truncated == 0:
        truncated = fallback

    restart = None
    rng = random.Random(seed)
    for _ in range(4096):
        candidate = random_candidate(inst, rng)
        if _valid_answer_fast(inst, candidate):
            restart = candidate
            break

    return {
        "outlier_lowest_encoding": _answer_from_value(smallest, degree),
        "obvious_copy_target": _answer_from_value(support_copy, degree),
        "greedy_residual_12": _answer_from_value(greedy, degree),
        "in_context_truncated_half_trace_4": _answer_from_value(
            truncated, degree),
        "random_restart_4096": restart,
    }


def _frobenius_transform(inst: dict, power: int
                         ) -> tuple[dict, dict[str, object]]:
    degree, modulus, c = _instance_data(inst)
    transformed_c = c
    planted_value, error = _decode_answer(inst["answer"], degree)
    if error is not None or planted_value is None:
        raise ValueError("source instance has malformed planted answer")
    transformed_z = planted_value
    for _ in range(power % degree):
        transformed_c = _gf_square(transformed_c, modulus, degree)
        transformed_z = _gf_square(transformed_z, modulus, degree)
    transformed = dict(inst)
    transformed["target"] = [transformed_c, 0, 0, transformed_c, 0]
    # canonical_key and verify must not gain access to the carried certificate.
    transformed["answer"] = dict(inst["answer"])
    return transformed, _answer_from_value(transformed_z, degree)


def _atom_count(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atom_count(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atom_count(item) for item in value)
    return 1


def selftest() -> dict:
    """Run G1--G9 and return a JSON-native evidence report."""
    report: dict[str, Any] = {
        "paper": "2103.10687",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    g1_failures: list[str] = []
    attempts = 0
    full_crosschecks = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(3):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
            if seed == 0:
                value, error = _decode_answer(inst["answer"], inst["k"])
                if error is None and value is not None and _full_equation_holds(inst, value):
                    full_crosschecks += 1
                else:
                    g1_failures.append(f"{preset}/{seed}: full L equation failed")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures and full_crosschecks == len(DIFFICULTY),
        "attempts": attempts,
        "full_extension_crosschecks": full_crosschecks,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=314159, **ship_params)
    planted = dict(ship["answer"])
    corruptions = {
        "drop_one": {"z": planted["z"]},
        "swap_fields": {"z": planted["trace"], "trace": planted["z"]},
        "duplicate_one": {**planted, "z_copy": planted["z"]},
        "empty": {},
        "out_of_range": {
            "z": _hex_element(1 << ship["k"], ship["k"]), "trace": 0,
        },
    }
    corruption_cases = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(ship, candidate)
        corruption_cases[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in corruption_cases.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "cases": corruption_cases,
    }

    planted_json = json.dumps(planted, separators=(",", ":"))
    realistic = (
        "Reducing the derivative gives the following exact field element.\n"
        "```json\n"
        f"<answer>{planted_json}</answer>\n"
        "```\nThe trace normalization selects this root."
    )
    parsed = parse_answer(realistic)
    duplicate_json = (
        '<answer>{"z":"' + str(planted["z"])
        + '","z":"' + str(planted["z"]) + '","trace":0}</answer>'
    )
    report["G3_round_trip"] = {
        "pass": (parsed == planted
                 and parse_answer("no tagged answer") is None
                 and parse_answer(duplicate_json) is None),
        "parsed": parsed,
        "duplicate_keys_rejected": parse_answer(duplicate_json) is None,
    }

    sample_total = 250_000
    sample_rng = random.Random(8675309)
    sample_hits = 0
    for _ in range(sample_total):
        candidate = random_candidate(ship, sample_rng)
        sample_hits += int(_valid_answer_fast(ship, candidate))
    observed_probability = sample_hits / sample_total
    candidate_space = search_space(ship)
    exact_probability = 1 / candidate_space
    report["G4_guess_resistance"] = {
        "pass": observed_probability < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "observed_probability": observed_probability,
        "construction_proved_probability": exact_probability,
        "construction_proved_valid_answers": 1,
        "candidate_space": candidate_space,
        "sampler": "uniform nonzero elements of the trace-zero hyperplane",
    }

    attack_names = [
        "outlier_lowest_encoding",
        "obvious_copy_target",
        "greedy_residual_12",
        "in_context_truncated_half_trace_4",
        "random_restart_4096",
    ]
    attacks = {name: {"successes": 0, "attempts": 8}
               for name in attack_names}
    reference_successes = 0
    reference_times: list[float] = []
    reference_scalar_ops: list[int] = []
    reference_squarings: list[int] = []
    reference_additions: list[int] = []
    for seed in range(8):
        trial = make_instance(seed=12_000 + seed, **ship_params)
        for name, candidate in _attack_candidates(trial, 700_000 + seed).items():
            if candidate is not None and verify(trial, candidate)[0]:
                attacks[name]["successes"] += 1
        started = time.perf_counter()
        found, metrics = _compact_route(trial, counted=True)
        reference_times.append(time.perf_counter() - started)
        reference_scalar_ops.append(metrics["gf2_coefficient_operations"])
        reference_squarings.append(metrics["field_squarings"])
        reference_additions.append(metrics["field_additions"])
        reference_successes += int(found is not None and verify(trial, found)[0])

    reference = {
        "name": "odd-degree half-trace solution of z^2+z=c+1",
        "complexity": (
            "O(k) field squarings; O(k^3) scalar GF(2) operations under "
            "schoolbook polynomial-basis reduction"
        ),
        "wall_clock_sec_mean": sum(reference_times) / len(reference_times),
        "wall_clock_sec_max": max(reference_times),
        "operations_mean": sum(reference_scalar_ops) / len(reference_scalar_ops),
        "operations_max": max(reference_scalar_ops),
        "field_squarings": reference_squarings[0],
        "field_additions": reference_additions[0],
        "solves": f"{reference_successes}/8, as expected",
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    shipping_count = enumerate_all(ship)
    report["G5_density_and_baseline"] = {
        "pass": (sample_total >= 200_000 and demo_count == 1
                 and reference_successes == 8),
        "shipping_density_hits": sample_hits,
        "shipping_density_total": sample_total,
        "shipping_observed_fraction": observed_probability,
        "shipping_construction_proved_fraction": exact_probability,
        "shipping_construction_proved_valid_solution_count": 1,
        "shipping_valid_solution_count": shipping_count,
        "shipping_structure_aware_space": candidate_space,
        "demo_valid_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "baseline_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
        "baseline_wall_clock_sec_max": reference["wall_clock_sec_max"],
        "baseline_operations_mean": reference["operations_mean"],
        "baseline_operations_max": reference["operations_max"],
        "baseline_field_squarings": reference["field_squarings"],
        "baseline_field_additions": reference["field_additions"],
    }

    all_attacks_failed = all(
        result["successes"] == 0 and result["attempts"] >= 8
        for result in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] = 2 * int(doubled_params["n"])
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > candidate_space,
        "shipping_n": ship["scale_n"],
        "shipping_k": ship["k"],
        "doubled_n": doubled["scale_n"],
        "doubled_k": doubled["k"],
        "shipping_space": candidate_space,
        "doubled_space": search_space(doubled),
        "doubled_verify_reason": doubled_reason,
        "answer_elements_shipping": _atom_count(ship["answer"]),
        "answer_elements_doubled": _atom_count(doubled["answer"]),
    }

    invariance_checks = 0
    real_transforms = 0
    composed_checks = 0
    unrelated_keys = []
    g8_failures = []
    for seed in range(20):
        original = make_instance(seed=20_000 + seed, **DIFFICULTY["medium"])
        key = canonical_key(original)
        unrelated_keys.append(key)
        transformed, carried = _frobenius_transform(original, seed + 1)
        if canonical_key(transformed) == key:
            invariance_checks += 1
        else:
            g8_failures.append(f"Frobenius transform changed key at seed {seed}")
        if verify(transformed, carried)[0]:
            real_transforms += 1
        else:
            g8_failures.append(f"carried Frobenius witness failed at seed {seed}")
        transformed_with_answer = dict(transformed)
        transformed_with_answer["answer"] = carried
        transformed_twice, carried_twice = _frobenius_transform(
            transformed_with_answer, 2 * seed + 3)
        if (canonical_key(transformed_twice) == key
                and verify(transformed_twice, carried_twice)[0]):
            composed_checks += 1
        else:
            g8_failures.append(f"composed Frobenius map failed at seed {seed}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "real_transformation_checks": real_transforms,
        "composed_transformation_checks": composed_checks,
        "unrelated_distinct": distinct_keys,
        "unrelated_attempts": 20,
        "transformations": [
            "Frobenius automorphism q -> q^(2^j) on target and witness",
            "composition of two Frobenius automorphisms",
        ],
        "failures": g8_failures,
    }

    compact_answer, compact_metrics = _compact_route(ship)
    compact_ok = compact_answer is not None and verify(ship, compact_answer)[0]
    width = _hex_width(ship["k"])
    worst_answer = {"z": "0x" + "f" * width, "trace": 0}
    # emit.sh serialises with ordinary json.dumps, including its default spaces.
    worst_blob = json.dumps(worst_answer)
    answer_chars = len(worst_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _atom_count(ship["answer"])
    intended_operations = (3 * ship["k"] + 1) // 2
    arms = {name: dict(G9_MEASUREMENTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else None)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else None)
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps and compact_ok,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None),
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "measured_instance_route_operations": (
            compact_metrics["field_squarings"]
            + compact_metrics["field_additions"]),
        "compact_route_verifies": compact_ok,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gate_values = [value for key, value in report.items()
                   if key.startswith("G") and isinstance(value, dict)]
    report["all_passed"] = all(value.get("pass") for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
