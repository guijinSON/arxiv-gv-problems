"""Exact Track-B preimage problems from Theorem 4.10 of arXiv:1508.07590.

Li, Qu, and Chen prove that, for q = 2^(2k+1), every nonzero a in
GF(q) gives the permutation trinomial

    F_a(X) = X + a X^(2^(k+1)-1)
                 + a^(-2^(k+1)-1) X^(2^(k+1)+1).

Generation samples a and a preimage x first, then publishes y = F_a(x).  The
certificate is therefore known without solving the emitted instance.  A witness
is the unique field element x, encoded compactly as its binary polynomial.

The paper's proof derives Equation (21), a one-line inverse after the Frobenius
symmetry is recognized.  Generic exhaustive evaluation is also exact and
efficient in the input's finite domain, but takes millions of table operations
at the shipping preset.  This is consequently a Track-B family, not a claim of
structural or complexity-theoretic hardness.
"""

from __future__ import annotations

import copy
import json
import math
import os
import random
import re
import sys
import time
from array import array
from functools import lru_cache


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # Binary-polynomial field arithmetic is implemented below.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "binary extension field GF(2^(2k+1))",
        "sparse permutation trinomial over that field",
        "field element represented by a polynomial over GF(2)",
    ],
    "verification_operations": [
        "exact XOR addition in GF(2)[t]",
        "exact polynomial multiplication modulo an irreducible polynomial",
        "exact finite-field exponentiation",
        "exact polynomial evaluation and equality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "The two nonlinear exponents straddle the Frobenius power 2^(k+1), "
        "so a Frobenius-conjugate cancellation makes the unknown linear; "
        "without seeing it, one enumerates the field."
    ),
    "hardness_basis": (
        "Track B: exhaustive logarithm-table evaluation is O(2^(2k+1)) time "
        "and memory and, at shipping k=10, used 18,557,039 exact table/XOR/"
        "index operations and 1.08 seconds, while "
        "Equation (21) in the proof of Theorem 4.10 gives a 68-operation "
        "Frobenius-and-division route that is short only after its symmetry is "
        "recognized."
    ),
    "max_answer_tokens": 7,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}


# Here n is the paper's k, so the actual field degree is m=2n+1.  Doubling n
# remains inside the theorem's parameter regime and squares the exponent length.
DIFFICULTY = {
    "demo": {"n": 2},       # GF(2^5), genuinely hand-scale
    "easy": {"n": 10},      # GF(2^21), first rung satisfying G4
    "medium": {"n": 14},    # GF(2^29)
    "hard": {"n": 19},      # GF(2^39)
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The two nonlinear exponents are symmetric around the Frobenius power "
    "2^(k+1), which creates cancellations under Frobenius conjugation."
)
PLACEBO_HINT = (
    "The hexadecimal field notation contains several interacting parts, so "
    "careful and consistent bookkeeping across each exact operation matters."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object with exactly one key, polynomial_hex, whose value is a "
        "fixed-width lowercase hexadecimal encoding of a nonzero binary "
        "polynomial of degree below m=2k+1; bit i is the coefficient of t^i."
    ),
    "bounds": {
        "fields": ["polynomial_hex"],
        "coefficient_field": "GF(2)",
        "degree": "strictly less than m=2k+1",
        "hex_digits": "ceil(m/4)",
        "numeric_range": "1..2^m-1",
        "shipping_atomic_elements": 1,
    },
}

NOTES = (
    "Section 2 fixes the paper's native definition: a permutation polynomial "
    "is a polynomial whose associated function bijects its finite field, and "
    "Definition 2.1 records the multiplicative equivalence used throughout. "
    "Section 4.B and Theorem 4.10 fix this exact odd-degree binary-field "
    "trinomial family.  Its proof's Equation (21) is decisive at Step 0: it "
    "makes inversion a short Frobenius-and-division computation, so Track A "
    "would be false, but it leaves a large gap to exhaustive field evaluation "
    "and therefore supports Track B.  Generation samples the preimage before "
    "evaluating the theorem-backed permutation.  The outlier probe chooses "
    "among conspicuous displayed field elements, the greedy probe fixes bits "
    "without backtracking, random restart tries 256 uniform nonzero elements, "
    "and the obvious monomial ansatz tries low-complexity products and "
    "Frobenius powers; none performs the division identity.  Canonicalization "
    "quotients term order, Frobenius automorphisms, and the paper's linear "
    "input/output scaling equivalence."
)


# Replaced after the three script-owned oracle runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


# Primitive trinomials for the named presets and the size-doubled G7 instance.
# Dynamic levels use a deterministically found irreducible polynomial instead.
_MODULUS_OVERRIDES = {
    5: (1 << 5) | (1 << 2) | 1,
    11: (1 << 11) | (1 << 2) | 1,
    15: (1 << 15) | (1 << 1) | 1,
    21: (1 << 21) | (1 << 2) | 1,
    25: (1 << 25) | (1 << 3) | 1,
    29: (1 << 29) | (1 << 2) | 1,
    33: (1 << 33) | (1 << 13) | 1,
    35: (1 << 35) | (1 << 2) | 1,
    39: (1 << 39) | (1 << 4) | 1,
    41: (1 << 41) | (1 << 3) | 1,
    47: (1 << 47) | (1 << 5) | 1,
    49: (1 << 49) | (1 << 9) | 1,
}


def _prime_factors(value):
    factors = []
    divisor = 2
    while divisor * divisor <= value:
        if value % divisor == 0:
            factors.append(divisor)
            while value % divisor == 0:
                value //= divisor
        divisor = 3 if divisor == 2 else divisor + 2
    if value > 1:
        factors.append(value)
    return factors


def _poly_gcd(left, right):
    while right:
        shift = left.bit_length() - right.bit_length()
        if shift < 0:
            left, right = right, left
            shift = left.bit_length() - right.bit_length()
        left ^= right << shift
    return left


def _gf_mul(left, right, degree, modulus):
    """Multiply bit-polynomials exactly modulo the monic modulus."""
    value = 0
    limit = 1 << degree
    mask = limit - 1
    while right:
        if right & 1:
            value ^= left
        right >>= 1
        left <<= 1
        if left & limit:
            left ^= modulus
    return value & mask


def _gf_pow(base, exponent, degree, modulus):
    value = 1
    while exponent:
        if exponent & 1:
            value = _gf_mul(value, base, degree, modulus)
        exponent >>= 1
        if exponent:
            base = _gf_mul(base, base, degree, modulus)
    return value


def _gf_inv(value, degree, modulus):
    if value == 0:
        raise ZeroDivisionError("zero has no inverse in a field")
    return _gf_pow(value, (1 << degree) - 2, degree, modulus)


def _gf_div(numerator, denominator, degree, modulus):
    return _gf_mul(numerator, _gf_inv(denominator, degree, modulus), degree, modulus)


def _is_irreducible(modulus, degree):
    if modulus.bit_length() != degree + 1 or not (modulus & 1):
        return False
    checkpoints = {degree // p for p in _prime_factors(degree)}
    value = 2  # the residue class of t
    checkpoint_values = {}
    for step in range(1, degree + 1):
        value = _gf_mul(value, value, degree, modulus)
        if step in checkpoints:
            checkpoint_values[step] = value
    if value != 2:
        return False
    return all(_poly_gcd(checkpoint_values[d] ^ 2, modulus) == 1 for d in checkpoints)


@lru_cache(maxsize=None)
def _find_irreducible(degree):
    if degree in _MODULUS_OVERRIDES:
        return _MODULUS_OVERRIDES[degree]
    # Low-weight moduli keep rendered arithmetic readable.  Trinomials are tried
    # first; the complete odd-tail scan is a deterministic fallback.
    for tap in range(1, degree):
        candidate = (1 << degree) | (1 << tap) | 1
        if _is_irreducible(candidate, degree):
            return candidate
    for tail in range(3, 1 << min(degree, 20), 2):
        candidate = (1 << degree) | tail
        if _is_irreducible(candidate, degree):
            return candidate
    raise ValueError(f"could not find a small irreducible modulus of degree {degree}")


def _validate_n(n):
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n (the paper's k) must be a positive integer")
    degree = 2 * n + 1
    modulus = _find_irreducible(degree)
    return degree, modulus


def _hex_width(degree):
    return (degree + 3) // 4


def _hex(value, degree):
    return format(value, f"0{_hex_width(degree)}x")


def _answer(value, degree):
    return {"polynomial_hex": _hex(value, degree)}


def _answer_value(answer, degree):
    """Validate the bounded witness grammar; return (value, reason)."""
    if not isinstance(answer, dict):
        return None, "answer must be a JSON object"
    if set(answer) != {"polynomial_hex"}:
        return None, "answer object must contain exactly the key polynomial_hex"
    encoded = answer["polynomial_hex"]
    if not isinstance(encoded, str):
        return None, "polynomial_hex must be a string"
    width = _hex_width(degree)
    if len(encoded) != width:
        return None, f"hex encoding must contain exactly {width} digits"
    if encoded != encoded.lower() or not re.fullmatch(r"[0-9a-f]+", encoded):
        return None, "hex encoding must use lowercase hexadecimal digits only"
    value = int(encoded, 16)
    if value >= (1 << degree):
        return None, f"polynomial has a nonzero coefficient above degree {degree - 1}"
    if value == 0:
        return None, "the statement implies that the preimage is nonzero"
    return value, "ok"


def _trinomial_data(n, degree, modulus, parameter):
    field_order = 1 << degree
    middle = 1 << (n + 1)
    third_coefficient = _gf_pow(
        parameter, field_order - middle - 2, degree, modulus
    )
    return middle, third_coefficient


def _eval_terms(value, terms, degree, modulus):
    result = 0
    for term in terms:
        coefficient = int(term["coefficient_hex"], 16)
        power = _gf_pow(value, term["exponent"], degree, modulus)
        result ^= _gf_mul(coefficient, power, degree, modulus)
    return result


def _ordered_terms(n, degree, modulus, parameter):
    middle, third_coefficient = _trinomial_data(n, degree, modulus, parameter)
    return [
        {"coefficient_hex": _hex(1, degree), "exponent": 1},
        {"coefficient_hex": _hex(parameter, degree), "exponent": middle - 1},
        {
            "coefficient_hex": _hex(third_coefficient, degree),
            "exponent": middle + 1,
        },
    ]


def make_instance(n, seed=0, **params):
    """Inverse-generate a unique preimage under Theorem 4.10's permutation."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    degree, modulus = _validate_n(n)
    field_order = 1 << degree
    rng = random.Random(seed)
    parameter = rng.randrange(1, field_order)
    planted_preimage = rng.randrange(1, field_order)
    terms = _ordered_terms(n, degree, modulus, parameter)
    target = _eval_terms(planted_preimage, terms, degree, modulus)
    if target == 0:  # The theorem says this cannot happen for nonzero x.
        raise AssertionError("Theorem 4.10 construction unexpectedly mapped nonzero x to 0")
    rng.shuffle(terms)  # Term order is deliberately not a clue.
    return {
        "family": "theorem_4_10_permutation_trinomial_preimage",
        "k": n,
        "extension_degree": degree,
        "field_order": field_order,
        "modulus_hex": format(modulus, "x"),
        "modulus_exponents": [
            power for power in range(degree + 1) if (modulus >> power) & 1
        ],
        "parameter_a_hex": _hex(parameter, degree),
        "polynomial_terms": terms,
        "target_hex": _hex(target, degree),
        "answer": _answer(planted_preimage, degree),
    }


def _polynomial_text(exponents, variable="t"):
    pieces = []
    for power in sorted(exponents, reverse=True):
        if power == 0:
            pieces.append("1")
        elif power == 1:
            pieces.append(variable)
        else:
            pieces.append(f"{variable}^{power}")
    return " + ".join(pieces)


def render(inst):
    degree = inst["extension_degree"]
    width = _hex_width(degree)
    lines = [
        "PREIMAGE OF A SPARSE PERMUTATION TRINOMIAL",
        "",
        f"Work in the binary field K = GF(2^{degree}) represented as GF(2)[t]/(M(t)),",
        f"where M(t) = {_polynomial_text(inst['modulus_exponents'])}.",
        f"The hexadecimal modulus bit mask is 0x{inst['modulus_hex']}; bit i is",
        "the coefficient of t^i.  A field element is encoded the same way using",
        f"exactly {width} lowercase hexadecimal digits (leading zeros included).",
        "Addition is bitwise XOR.  Multiplication is ordinary binary-polynomial",
        "multiplication followed by reduction using M(t)=0.  Powers are field powers.",
        "All arithmetic is exact; hexadecimal strings are not ordinary integers",
        "for multiplication.",
        "",
        "Define F(X) by these three terms (their displayed order is irrelevant):",
    ]
    for term in inst["polynomial_terms"]:
        lines.append(
            f"  coefficient 0x{term['coefficient_hex']} times X^{term['exponent']}"
        )
    lines.extend(
        [
            "",
            f"The target is Y = 0x{inst['target_hex']}.",
            "This displayed F is guaranteed to permute K, and F(0)=0 while Y is",
            "nonzero.  Find the unique nonzero field element X with F(X)=Y.",
            "",
            "Encode X as the unique binary polynomial of degree strictly below",
            f"{degree}: if X=sum_i c_i t^i, bit i of polynomial_hex is c_i.",
            f"The value must be in 000...001 through {_hex((1 << degree) - 1, degree)}",
            f"and polynomial_hex must contain exactly {width} lowercase hex digits.",
            "",
            "Give your final answer inside <answer></answer> tags, as a JSON object",
            "with exactly the key polynomial_hex.",
            f'Example: <answer>{{"polynomial_hex":"{_hex(1, degree)}"}}</answer>',
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        parsed = json.loads(body)
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def verify(inst, answer):
    try:
        degree = inst["extension_degree"]
        modulus = int(inst["modulus_hex"], 16)
        terms = inst["polynomial_terms"]
        target = int(inst["target_hex"], 16)
    except (KeyError, TypeError, ValueError):
        return False, "malformed instance"
    value, reason = _answer_value(answer, degree)
    if value is None:
        return False, reason
    try:
        image = _eval_terms(value, terms, degree, modulus)
    except (KeyError, TypeError, ValueError):
        return False, "malformed polynomial terms in instance"
    if image != target:
        return False, "the submitted polynomial does not evaluate to the target"
    return True, "ok"


def random_candidate(inst, rng):
    degree = inst["extension_degree"]
    value = rng.randrange(1, 1 << degree)
    return _answer(value, degree)


def search_space(inst):
    return (1 << inst["extension_degree"]) - 1


def enumerate_all(inst):
    space = search_space(inst)
    if space > 4095:
        return None
    return sum(1 for value in range(1, space + 1) if verify(inst, _answer(value, inst["extension_degree"]))[0])


def _parameter_and_target(inst):
    degree = inst["extension_degree"]
    return int(inst["parameter_a_hex"], 16), int(inst["target_hex"], 16), degree, int(inst["modulus_hex"], 16)


def canonical_key(inst):
    """Quotient term order, input/output scaling, and Frobenius automorphisms."""
    parameter, target, degree, modulus = _parameter_and_target(inst)
    n = inst["k"]
    field_order = 1 << degree
    exponent = (1 << (n + 1)) - 2
    exponent_inverse = pow(exponent, -1, field_order - 1)
    # Under x=bz, b^-1 F_a(bz)=F_(a*b^exponent)(z).  The unique b
    # below normalizes the parameter to one; target/b is then scaling-invariant.
    normalizer = _gf_pow(
        parameter,
        (-exponent_inverse) % (field_order - 1),
        degree,
        modulus,
    )
    normalized_target = _gf_div(target, normalizer, degree, modulus)
    conjugates = []
    value = normalized_target
    for _ in range(degree):
        conjugates.append(value)
        value = _gf_mul(value, value, degree, modulus)
    canonical_target = min(conjugates)
    return (
        f"theorem4.10:k={n}:m={degree}:mod={modulus:x}:"
        f"orbit={canonical_target:0{_hex_width(degree)}x}"
    )


def escalate(params):
    n = params.get("n")
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        return None
    harder_n = max(n + 1, math.ceil(1.35 * n))
    harder_degree = 2 * harder_n + 1
    projected = json.dumps(_answer((1 << harder_degree) - 1, harder_degree))
    if len(projected) > 2000:
        return "cap_bound"
    return {"n": harder_n}


# ---- Compact and mechanical solvers used only for measurement ----------------

def _pow_left_to_right_counted(base, exponent, degree, modulus):
    bits = bin(exponent)[2:]
    value = base
    operations = 0
    for bit in bits[1:]:
        value = _gf_mul(value, value, degree, modulus)
        operations += 1
        if bit == "1":
            value = _gf_mul(value, base, degree, modulus)
            operations += 1
    return value, operations


def _frobenius_counted(value, times, degree, modulus):
    first_square = None
    for index in range(times):
        value = _gf_mul(value, value, degree, modulus)
        if index == 0:
            first_square = value
    return value, first_square, times


def _compact_inverse(inst):
    """Equation (21) from Theorem 4.10's proof, with operation count."""
    parameter, target, degree, modulus = _parameter_and_target(inst)
    n = inst["k"]
    frobenius_steps = n + 1
    target_frob, target_square, target_ops = _frobenius_counted(
        target, frobenius_steps, degree, modulus
    )
    parameter_frob, parameter_square, parameter_ops = _frobenius_counted(
        parameter, frobenius_steps, degree, modulus
    )
    numerator = _gf_mul(parameter, target, degree, modulus)
    numerator = _gf_mul(numerator, target_frob, degree, modulus)
    term_one = _gf_mul(parameter_frob, parameter_square, degree, modulus)
    term_two = _gf_mul(parameter, target_frob, degree, modulus)
    denominator = term_one ^ term_two ^ target_square
    inverse, inverse_ops = _pow_left_to_right_counted(
        denominator, (1 << degree) - 2, degree, modulus
    )
    value = _gf_mul(numerator, inverse, degree, modulus)
    operations = target_ops + parameter_ops + 2 + 2 + 2 + inverse_ops + 1
    return _answer(value, degree), operations


def _build_log_tables(inst):
    """Build exact log/antilog tables; named moduli make t primitive."""
    degree = inst["extension_degree"]
    modulus = int(inst["modulus_hex"], 16)
    field_order = 1 << degree
    order = field_order - 1
    exponents = array("I", [0]) * order
    logarithms = array("I", [0]) * field_order
    value = 1
    for exponent in range(order):
        exponents[exponent] = value
        logarithms[value] = exponent
        value <<= 1
        if value & field_order:
            value ^= modulus
    if value != 1:
        raise ValueError("the displayed modulus does not make t primitive")
    return exponents, logarithms, order


def _reference_exhaustive(inst, tables):
    """Domain-standard exhaustive value-table inversion, not Equation (21)."""
    exponents, logarithms, order = tables
    parameter, target, degree, modulus = _parameter_and_target(inst)
    del modulus
    n = inst["k"]
    middle = 1 << (n + 1)
    third = next(
        int(term["coefficient_hex"], 16)
        for term in inst["polynomial_terms"]
        if term["exponent"] == middle + 1
    )
    index_one = logarithms[parameter]
    index_two = logarithms[third]
    step_one = middle - 1
    step_two = middle + 1
    for exponent in range(order):
        candidate_image = exponents[exponent] ^ exponents[index_one] ^ exponents[index_two]
        if candidate_image == target:
            # 8 counted operations per tested element: three reads, two XORs,
            # one equality, and two modular index advances (the final advances
            # are charged too, making this a conservative whole-loop count).
            return _answer(exponents[exponent], degree), exponent + 1, 8 * (exponent + 1)
        index_one += step_one
        if index_one >= order:
            index_one %= order
        index_two += step_two
        if index_two >= order:
            index_two %= order
    return None, order, 8 * order


# ---- Construction-aware attacks ---------------------------------------------

def _attack_outlier_displayed(inst):
    parameter, target, degree, modulus = _parameter_and_target(inst)
    del modulus
    shown = {1, parameter, target}
    shown.update(int(term["coefficient_hex"], 16) for term in inst["polynomial_terms"])
    candidate = min(shown, key=lambda value: (bin(value).count("1"), value))
    return _answer(candidate, degree)


def _attack_greedy_bits(inst):
    degree = inst["extension_degree"]
    target = int(inst["target_hex"], 16)
    modulus = int(inst["modulus_hex"], 16)
    terms = inst["polynomial_terms"]
    value = 0
    for bit in range(degree - 1, -1, -1):
        without = _eval_terms(value, terms, degree, modulus)
        with_bit_value = value | (1 << bit)
        with_bit = _eval_terms(with_bit_value, terms, degree, modulus)
        if bin(with_bit ^ target).count("1") < bin(without ^ target).count("1"):
            value = with_bit_value
    return _answer(value or 1, degree)


def _attack_random_restart(inst, rng, restarts=256):
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _attack_obvious_ansatz(inst):
    parameter, target, degree, modulus = _parameter_and_target(inst)
    n = inst["k"]
    middle = 1 << (n + 1)
    third = next(
        int(term["coefficient_hex"], 16)
        for term in inst["polynomial_terms"]
        if term["exponent"] == middle + 1
    )
    bases = [1, parameter, third, target]
    candidates = set(bases)
    for value in bases:
        candidates.add(_gf_mul(value, value, degree, modulus))
        candidates.add(_gf_pow(value, middle, degree, modulus))
    for left in bases:
        for right in bases:
            candidates.add(_gf_mul(left, right, degree, modulus))
    for candidate in sorted(candidates):
        if candidate and verify(inst, _answer(candidate, degree))[0]:
            return _answer(candidate, degree)
    return None


# ---- Exact relabellings for G8 -----------------------------------------------

def _replace_problem_data(inst, parameter, target, answer_value=None):
    out = copy.deepcopy(inst)
    degree = out["extension_degree"]
    modulus = int(out["modulus_hex"], 16)
    old_exponents = [term["exponent"] for term in out["polynomial_terms"]]
    by_exponent = {
        term["exponent"]: term
        for term in _ordered_terms(out["k"], degree, modulus, parameter)
    }
    out["parameter_a_hex"] = _hex(parameter, degree)
    out["polynomial_terms"] = [copy.deepcopy(by_exponent[e]) for e in old_exponents]
    out["target_hex"] = _hex(target, degree)
    if answer_value is not None:
        out["answer"] = _answer(answer_value, degree)
    return out


def _scale_relabelling(inst, scale):
    parameter, target, degree, modulus = _parameter_and_target(inst)
    n = inst["k"]
    exponent = (1 << (n + 1)) - 2
    new_parameter = _gf_mul(
        parameter, _gf_pow(scale, exponent, degree, modulus), degree, modulus
    )
    inverse_scale = _gf_inv(scale, degree, modulus)
    new_target = _gf_mul(target, inverse_scale, degree, modulus)
    answer_value, reason = _answer_value(inst["answer"], degree)
    if answer_value is None:
        raise ValueError(reason)
    new_answer = _gf_mul(answer_value, inverse_scale, degree, modulus)
    return _replace_problem_data(inst, new_parameter, new_target, new_answer)


def _frobenius_relabelling(inst, times):
    parameter, target, degree, modulus = _parameter_and_target(inst)
    answer_value, reason = _answer_value(inst["answer"], degree)
    if answer_value is None:
        raise ValueError(reason)
    for _ in range(times % degree):
        parameter = _gf_mul(parameter, parameter, degree, modulus)
        target = _gf_mul(target, target, degree, modulus)
        answer_value = _gf_mul(answer_value, answer_value, degree, modulus)
    return _replace_problem_data(inst, parameter, target, answer_value)


def _answer_atoms(answer):
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, (list, tuple)):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def _make_swap_corruption(answer, degree):
    value, reason = _answer_value(answer, degree)
    if value is None:
        raise ValueError(reason)
    one = next((bit for bit in range(degree) if (value >> bit) & 1), 0)
    zero = next((bit for bit in range(degree) if not ((value >> bit) & 1)), None)
    if zero is None:
        value ^= 1
    else:
        value ^= (1 << one) | (1 << zero)
    return _answer(value or 1, degree)


def selftest():
    report = {}

    # G1: every named preset, three unrelated seeds, JSON-native answers.
    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            g1_attempts += 1
            ok, reason = verify(inst, inst["answer"])
            try:
                json_native = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            except (TypeError, ValueError):
                json_native = False
            if not ok or not json_native:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=12345, **shipping_params)
    degree = shipping["extension_degree"]
    encoded = shipping["answer"]["polynomial_hex"]
    corruptions = {
        "drop_one": {"polynomial_hex": encoded[:-1]},
        "swap_one": _make_swap_corruption(shipping["answer"], degree),
        "duplicate": {"polynomial_hex": [encoded, encoded]},
        "empty": {},
        "out_of_range": {"polynomial_hex": "f" + encoded[1:]},
    }
    g2_cases = {}
    for name, bad in corruptions.items():
        ok, reason = verify(shipping, bad)
        g2_cases[name] = {"accepted": ok, "reason": reason}
    reasons = {row["reason"] for row in g2_cases.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(not row["accepted"] for row in g2_cases.values()) and len(reasons) == 5,
        "distinct_reasons": len(reasons),
        "cases": g2_cases,
    }

    model_style = (
        "The Frobenius terms cancel as expected.\n```json\n<answer>"
        + json.dumps(shipping["answer"], separators=(",", ":"))
        + "</answer>\n```\nThat is the unique preimage."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and verify(shipping, parsed)[0],
        "parsed": parsed == shipping["answer"],
    }

    # G4 and the shipping density part of G5 share the same 200k exact trials.
    sample_total = 200_000
    sample_rng = random.Random(0x150807590)
    sample_hits = 0
    sample_started = time.perf_counter()
    for _ in range(sample_total):
        if verify(shipping, random_candidate(shipping, sample_rng))[0]:
            sample_hits += 1
    sample_wall = time.perf_counter() - sample_started
    observed_probability = sample_hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": observed_probability < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "observed_probability": observed_probability,
        "exact_probability": 1 / search_space(shipping),
        "certificate_space": search_space(shipping),
        "structure_aware_prior": (
            "uniform over all nonzero degree-<m binary polynomials; nonzero is "
            "deduced from F(0)=0 and the displayed nonzero target"
        ),
        "wall_clock_sec": sample_wall,
    }

    # Reference preprocessing once, followed by eight independently generated
    # targets.  Standalone cost charges preprocessing plus the largest query.
    reference_instances = [make_instance(seed=9000 + seed, **shipping_params) for seed in range(8)]
    prep_started = time.perf_counter()
    tables = _build_log_tables(shipping)
    prep_wall = time.perf_counter() - prep_started
    prep_operations = search_space(shipping)
    ref_successes = 0
    ref_rows = []
    for inst in reference_instances:
        query_started = time.perf_counter()
        found, candidates, scan_operations = _reference_exhaustive(inst, tables)
        query_wall = time.perf_counter() - query_started
        ok = found is not None and verify(inst, found)[0]
        ref_successes += int(ok)
        ref_rows.append(
            {
                "candidates_tested": candidates,
                "scan_operations": scan_operations,
                "query_wall_clock_sec": query_wall,
            }
        )
    max_ref = max(ref_rows, key=lambda row: row["scan_operations"])
    standalone_operations = prep_operations + max_ref["scan_operations"]
    standalone_wall = prep_wall + max(row["query_wall_clock_sec"] for row in ref_rows)

    compact_answer, compact_operations = _compact_inverse(shipping)
    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_exact = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": (
            demo_exact == 1
            and sample_hits / sample_total < 1e-6
            and ref_successes == 8
            and verify(shipping, compact_answer)[0]
        ),
        "shipping_density_hits": sample_hits,
        "shipping_density_samples": sample_total,
        "shipping_sampled_valid_fraction": sample_hits / sample_total,
        "demo_exact_solution_count": demo_exact,
        "demo_certificate_space": search_space(demo),
        "baseline_operations": standalone_operations,
        "baseline_wall_clock_sec": standalone_wall,
        "reference_preprocessing_operations": prep_operations,
        "reference_preprocessing_wall_clock_sec": prep_wall,
        "reference_max_candidates_tested": max_ref["candidates_tested"],
        "reference_max_query_wall_clock_sec": max(row["query_wall_clock_sec"] for row in ref_rows),
        "compact_route_operations": compact_operations,
    }

    attacks = {
        "outlier_displayed_low_hamming_weight": {"successes": 0, "attempts": 0},
        "greedy_bitwise_image_distance": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
        "obvious_monomial_frobenius_ansatz": {"successes": 0, "attempts": 0},
    }
    for index, inst in enumerate(reference_instances):
        candidates = {
            "outlier_displayed_low_hamming_weight": _attack_outlier_displayed(inst),
            "greedy_bitwise_image_distance": _attack_greedy_bits(inst),
            "random_restart_256": _attack_random_restart(
                inst, random.Random(700_000 + index)
            ),
            "obvious_monomial_frobenius_ansatz": _attack_obvious_ansatz(inst),
        }
        for name, candidate in candidates.items():
            attacks[name]["attempts"] += 1
            if candidate is not None and verify(inst, candidate)[0]:
                attacks[name]["successes"] += 1
    report["G6_adversary_panel"] = {
        "pass": all(row["successes"] == 0 for row in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "primitive-element logarithm table plus exhaustive value evaluation",
            "complexity": "O(2^(2k+1)) exact time and memory",
            "wall_clock_sec": standalone_wall,
            "operations": standalone_operations,
            "preprocessing_operations": prep_operations,
            "max_candidates_tested": max_ref["candidates_tested"],
            "solves": f"{ref_successes}/8, as expected",
        },
    }

    doubled_n = 2 * shipping_params["n"]
    doubled = make_instance(n=doubled_n, seed=314159)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(shipping),
        "shipping_n": shipping_params["n"],
        "shipping_field_degree": shipping["extension_degree"],
        "doubled_n": doubled_n,
        "doubled_field_degree": doubled["extension_degree"],
        "doubled_verify_reason": doubled_reason,
        "shipping_answer_elements": _answer_atoms(shipping["answer"]),
        "doubled_answer_elements": _answer_atoms(doubled["answer"]),
        "search_space_growth_bits": (
            search_space(doubled).bit_length() - search_space(shipping).bit_length()
        ),
    }

    g8_failures = []
    invariance_checks = 0
    carried_checks = 0
    for seed in range(20):
        inst = make_instance(seed=50_000 + seed, **shipping_params)
        rng = random.Random(80_000 + seed)
        scale = rng.randrange(1, inst["field_order"])
        frobenius_steps = rng.randrange(1, inst["extension_degree"])
        reordered = copy.deepcopy(inst)
        reordered["polynomial_terms"].reverse()
        transformed = [
            ("term_order", reordered),
            ("scaling", _scale_relabelling(inst, scale)),
            ("frobenius", _frobenius_relabelling(inst, frobenius_steps)),
            (
                "scaling_then_frobenius",
                _frobenius_relabelling(_scale_relabelling(inst, scale), frobenius_steps),
            ),
        ]
        original_key = canonical_key(inst)
        for name, changed in transformed:
            invariance_checks += 1
            if canonical_key(changed) != original_key:
                g8_failures.append({"seed": seed, "transform": name, "failure": "key changed"})
            carried_checks += 1
            ok, reason = verify(changed, changed["answer"])
            if not ok:
                g8_failures.append({"seed": seed, "transform": name, "failure": reason})
    unrelated_keys = {
        canonical_key(make_instance(seed=90_000 + seed, **shipping_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": not g8_failures and len(unrelated_keys) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_attempts": 20,
        "distinct_unrelated": len(unrelated_keys),
        "failures": g8_failures,
        "transformations": [
            "trinomial term permutation",
            "nonzero input/output scaling",
            "Frobenius field automorphism",
            "scaling composed with Frobenius",
        ],
        "key_method": "normalize a by scaling, then minimize target over its Frobenius orbit",
    }

    answer_blob = json.dumps(shipping["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    hinted = G9_ORACLE_RESULTS["hinted"]
    placebo = G9_ORACLE_RESULTS["placebo"]
    difference = None
    if hinted["attempts"] and placebo["attempts"]:
        difference = hinted["solved"] / hinted["attempts"] - placebo["solved"] / placebo["attempts"]
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and compact_operations <= 1000
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {
            "bare": dict(G9_ORACLE_RESULTS["bare"]),
            "hinted": dict(hinted),
            "placebo": dict(placebo),
        },
        "hinted_minus_placebo": difference,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 1000},
    }

    report["all_passed"] = all(
        value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
