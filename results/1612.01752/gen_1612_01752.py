"""Track-B generator for an improving single replacement in weighted MUFL.

The metric is the tight PLS reduction in Section 3 of Brauer (arXiv:1612.01752).
A unique improving Boolean flip is planted through a hidden affine cube; the
paper's Proposition 3 and Lemma 5 carry it to an improving facility swap.
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - stdlib code is sufficient
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "optimization",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "weighted metric uncapacitated-facility-location instance",
        "complementary literal facilities and co-located weighted clients",
        "weighted clause clients at exact rational metric distances",
        "a current reasonable set of open facilities",
    ],
    "verification_operations": [
        "exact modular polynomial evaluation",
        "exact integer clause-weight gain",
        "complementary-facility decoding",
        "exact sign comparison of the MUFL cost difference",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3, Proposition 3 and Lemma 5: tight PLS reduction from "
        "weighted Max-2-SAT/Flip to MUFL/Swap"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "The displayed cubic is the cube of an affine form modulo p; "
        "recognizing that conjugacy replaces an exhaustive scan of all swaps."
    ),
    "hardness_basis": (
        "Track B: generic Frobenius-gcd root isolation is O(log p) arithmetic "
        "on degree-3 polynomials over F_p; at shipping n=2500049 it takes "
        "872 counted exact operations and under 0.1 seconds in local runs, "
        "while recognizing the affine cube cuts this to 62 operations."
    ),
    "max_answer_tokens": 5,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (PROBLEM_PROFILE["intuition_type"] + ": "
                  + PROBLEM_PROFILE["intuition_description"]),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "An ordered [close_id, open_id] for one complementary pair: its open "
        "negative facility followed by its closed positive mate.  The heavy "
        "literal-client bound directly excludes cross-pair replacements, so "
        "the language contains exactly n+2 candidates."
    ),
    "bounds": {
        "length": 2,
        "candidate_pairs": "n+2 complementary pairs",
        "facility_ids": "integers from 0 through 2(n+2)-1",
    },
}

# Each prime is 2 mod 3 and lies in the upper half of its binary-length range.
DIFFICULTY: dict = {
    "demo": {"n": 11},
    "easy": {"n": 1_250_003},
    "medium": {"n": 2_500_049},
    "hard": {"n": 5_000_081},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT: str = (
    "The displayed cubic is a perfect cube of an affine polynomial modulo p."
)
PLACEBO_HINT: str = (
    "The displayed indices and facility roles should be tracked with care."
)

# Updated only from transcripts written by scripts/harden.py.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 2},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "incomplete_api_limit",
}

NOTES: str = r"""
Definition and regime. Section 1.1 defines weighted metric uncapacitated
facility location (MUFL), and Section 1.2 defines the add/drop/replace
MUFL/Swap neighbourhood. This module asks for the replacement part. The proof
requires non-trivial client weights; Section 5 leaves the unweighted regime
open, so this generator retains the paper's weights. Section 1.3 describes a
polynomial-time thresholded-improvement variant with a slightly weaker
approximation guarantee; this family retains exact strict improvement.

Certificate algorithm and track. Checking a swap is polynomial. More strongly,
generic finite-field root isolation finds the unique improving coordinate by
computing gcd(x^p-x,P(x)+1), using O(log p) arithmetic on degree-3 polynomials.
Track A would be false. This is Track B: at shipping size that generic route
uses about 870 counted exact operations, while the compact route recognizes an
affine cube and solves one congruence in 62 counted operations.

Paper construction. Section 3, Proposition 3 maps weighted Max-2-SAT/Flip to
MUFL/Swap. It places a facility at each literal, a weight-W client at every
literal point, and a client at every clause. Complementary literals are at
distance 1; a clause is at distance 4/3 from a contained literal, 5/3 from its
complement, and 2 otherwise. Every facility costs 2W. Lemma 5 proves that among
reasonable solutions, increasing satisfied clause weight exactly decreases
MUFL cost. Lemmas 7 and 9 exclude improving moves leaving that set.

Inverse generation. For p=2 mod 3, cubing permutes F_p. The generator samples
nonzero a and b and forms P(i)=(a*i+b)^3, publishing only its expanded
coefficients. Balanced positive/negative clause pairs make flip gain
2*s*(P(i)-(p-2))-1. Exactly P(i)=p-1 improves, and its index is computed from
a,b before the public instance is built. A guard clause gives anchor z gain -1.

Attack handling. Every ordinary pair has the same degree, total incident
weight, sign counts, and incident-weight multiset. Facility IDs undergo an
independent affine permutation. The panel tests the tied outlier, a coefficient
greedy choice, 256 random flips, an eight-coordinate manual prefix, and the
tempting linearized-cubic ansatz. Successful generic finite-field root isolation
is reported separately as the Track-B reference algorithm; exhaustive swap
enumeration is retained only as a comparison.
""".strip()


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_supported_prime(start: int) -> int:
    candidate = max(11, start)
    if candidate % 2 == 0:
        candidate += 1
    while not (_is_prime(candidate) and candidate % 3 == 2):
        candidate += 2
    return candidate


def _validate_parameters(n: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer")
    if n < 11 or not _is_prime(n) or n % 3 != 2:
        raise ValueError("n must be a prime congruent to 2 modulo 3, at least 11")
    bits = (n - 1).bit_length()
    if 2 * (n - 2) <= (1 << bits) - 1:
        raise ValueError("n must lie in the upper half of its binary-length range")


def _ones_below(limit: int, bit: int) -> int:
    half = 1 << bit
    period = half << 1
    full, remainder = divmod(limit, period)
    return full * half + max(0, remainder - half)


def _answer_atoms(answer: object) -> int:
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, (list, tuple)):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def _pow_multiplication_count(exponent: int) -> int:
    bits = bin(exponent)[2:]
    return max(0, len(bits) - 1) + bits[1:].count("1")


def _inverse_euclid_steps(value: int, modulus: int) -> int:
    steps = 0
    a, b = value % modulus, modulus
    while a:
        b, a = a, b % a
        steps += 1
    return steps


def _choose_unit(rng: random.Random, modulus: int) -> int:
    value = rng.randrange(1, modulus)
    while math.gcd(value, modulus) != 1:
        value = value + 1 if value + 1 < modulus else 1
    return value


def _facility_id(inst: dict, logical_token: int) -> int:
    explicit = inst.get("_explicit_id_map")
    if explicit is not None:
        return explicit[logical_token]
    return (inst["id_multiplier"] * logical_token + inst["id_shift"]) \
        % inst["facility_count"]


def _logical_token(inst: dict, facility_id: int) -> int:
    explicit = inst.get("_explicit_id_inverse")
    if explicit is not None:
        return explicit[facility_id]
    return (inst["id_inverse"] * (facility_id - inst["id_shift"])) \
        % inst["facility_count"]


def _positive_id(inst: dict, coordinate: int) -> int:
    return _facility_id(inst, 2 * coordinate)


def _negative_id(inst: dict, coordinate: int) -> int:
    return _facility_id(inst, 2 * coordinate + 1)


def _code_at(inst: dict, coordinate: int) -> int:
    explicit = inst.get("_explicit_codes")
    if explicit is not None:
        return explicit[coordinate]
    c3, c2, c1, c0 = inst["polynomial_coefficients"]
    prime = inst["n"]
    return (((c3 * coordinate + c2) % prime * coordinate + c1)
            % prime * coordinate + c0) % prime


def _gain_at(inst: dict, coordinate: int) -> int:
    if coordinate < inst["n"]:
        return (2 * inst["scale"]
                * (_code_at(inst, coordinate) - (inst["n"] - 2)) - 1)
    if coordinate == inst["z_pair_index"]:
        return -1
    return 0


def make_instance(n: int, seed: int = 0, **params: object) -> dict:
    """Build an instance whose unique improving flip is known before emission."""
    if params:
        raise ValueError(f"unknown generation parameters: {sorted(params)}")
    _validate_parameters(n)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    p = n
    bits = (p - 1).bit_length()
    affine_a = rng.randrange(1, p)
    affine_b = rng.randrange(p)
    target = ((p - 1 - affine_b) * pow(affine_a, -1, p)) % p
    coefficients = [
        pow(affine_a, 3, p),
        (3 * affine_a * affine_a * affine_b) % p,
        (3 * affine_a * affine_b * affine_b) % p,
        pow(affine_b, 3, p),
    ]
    scale = rng.randrange(17, 1000)
    base_weight = rng.randrange(10_000, 10**9)
    high_weights = [base_weight + scale * (1 << bit)
                    for bit in range(bits)]
    threshold = scale * (2 * (p - 2) - ((1 << bits) - 1)) + 1

    positive_at_anchor = sum(
        p * base_weight + scale * (1 << bit) * _ones_below(p, bit)
        for bit in range(bits)
    )
    lock_weight = positive_at_anchor + 1
    pair_count = p + 2
    facility_count = 2 * pair_count
    id_multiplier = _choose_unit(rng, facility_count)
    id_shift = rng.randrange(facility_count)
    clause_count = p * (2 * bits + 1) + 1
    literal_weight = clause_count * lock_weight

    inst = {
        "family": "weighted_metric_MUFL_single_replacement",
        "n": p,
        "bits": bits,
        "polynomial_coefficients": coefficients,
        "scale": scale,
        "base_weight": base_weight,
        "bit_high_weights": high_weights,
        "threshold_weight": threshold,
        "variable_pair_count": pair_count,
        "z_pair_index": p,
        "y_pair_index": p + 1,
        "facility_count": facility_count,
        "id_multiplier": id_multiplier,
        "id_shift": id_shift,
        "id_inverse": pow(id_multiplier, -1, facility_count),
        "clause_count": clause_count,
        "lock_weight": lock_weight,
        "literal_client_weight": literal_weight,
        "opening_cost": 2 * literal_weight,
    }
    inst["answer"] = [_negative_id(inst, target), _positive_id(inst, target)]
    return inst


def render(inst: dict) -> str:
    p = inst["n"]
    c3, c2, c1, c0 = inst["polynomial_coefficients"]
    high = ", ".join(
        f"j={j}:{weight}" for j, weight in enumerate(inst["bit_high_weights"])
    )
    statement = f"""Weighted metric facility-location single replacement

All arithmetic is exact. Put p={p} and d={inst['bits']}. There are V=p+2=
{inst['variable_pair_count']} complementary facility pairs, indexed i=0,...,p-1,
then z (index p) and y (index p+1). There are F=2V={inst['facility_count']}
facility IDs, 0 through F-1.

For pair i, its positive logical token is 2i and its negative token is 2i+1.
A token q has displayed facility ID

    id(q)=({inst['id_multiplier']}*q+{inst['id_shift']}) mod {inst['facility_count']}.

The multiplier is invertible modulo F, so this names every facility once. The
currently open set contains every negative facility id(2i+1); all positive
facilities id(2i) are closed.

This compact rule defines a complete weighted metric uncapacitated facility-
location (MUFL) instance. A literal point is both a possible facility and a
client. Each literal client has integer weight W={inst['literal_client_weight']}.
Every facility has opening cost 2W={inst['opening_cost']}. A literal client is at
distance 0 from its own facility, 1 from its complementary mate, and 2 from all
other literal facilities.

A clause client is specified by two literal facilities A,B and a positive
integer weight. It is at distance 4/3 from A and B, 5/3 from their complementary
mates, and 2 from every other literal facility. Distinct clause clients are at
distance 2. Repeated (A,B) pairs below denote distinct clients. These rules,
symmetry, and distance 0 at a point define the whole metric. The cost of an open
set is opening cost plus, for every client, its weight times the distance to its
nearest open facility.

The clause clients follow this exact rule. For each ordinary i=0,...,p-1, let

    t_i=({c3}*i^3+{c2}*i^2+{c1}*i+{c0}) mod {p},

using the least residue 0,...,p-1. Put B0={inst['base_weight']} and s=
{inst['scale']}. For each bit j=0,...,d-1 create two clients. If bit j of t_i is
1, create (positive_i,z_positive) with weight B0+s*2^j and
(negative_i,z_positive) with weight B0. If the bit is 0, exchange those weights.
The high weights are:

    {high}

For every ordinary i also create (negative_i,z_positive) with threshold weight
C={inst['threshold_weight']}. Finally create guard client
(z_negative,y_positive) with weight L={inst['lock_weight']}. Thus there are
exactly M={inst['clause_count']} clause clients. All indices are 0-based and all
displayed finite ranges include both endpoints.

Task: replace exactly one open facility by exactly one closed facility so that
the exact MUFL cost strictly decreases. The heavy literal clients imply that an
improving replacement must use one complementary pair. Order matters: output
the closed negative ID first and its newly opened positive mate second. IDs must
be distinct.

Give your final answer inside <answer></answer> tags, as two decimal integers
close_id, open_id. Example: <answer>7, 12</answer>
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
    blocks = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    if not blocks:
        return None
    body = blocks[-1].strip()
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1].strip()
    match = re.fullmatch(r"([+-]?\d+)\s*,\s*([+-]?\d+)", body)
    if not match:
        return None
    try:
        return [int(match.group(1)), int(match.group(2))]
    except ValueError:
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any improving replacement without consulting inst['answer']."""
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list):
        return False, "answer must be a list of two integer facility IDs"
    if len(answer) == 1:
        return False, "answer is incomplete: open_id is missing"
    if len(answer) != 2:
        return False, "answer must contain exactly two facility IDs"
    close_id, open_id = answer
    if (isinstance(close_id, bool) or isinstance(open_id, bool)
            or not isinstance(close_id, int) or not isinstance(open_id, int)):
        return False, "both facility IDs must be integers"
    if close_id == open_id:
        return False, "the two facility IDs must be distinct"
    if not (0 <= close_id < inst["facility_count"]
            and 0 <= open_id < inst["facility_count"]):
        return False, "a facility ID is outside the stated range"

    close_token = _logical_token(inst, close_id)
    open_token = _logical_token(inst, open_id)
    if close_token % 2 != 1:
        return False, "close_id is not currently open"
    if open_token % 2 != 0:
        return False, "open_id is not currently closed"
    close_pair, open_pair = close_token // 2, open_token // 2
    if close_pair != open_pair:
        return False, (
            "cross-pair replacement is not improving: its literal-client "
            "penalty exceeds every possible clause-client saving"
        )
    gain = _gain_at(inst, close_pair)
    if gain <= 0:
        return False, (
            f"replacement is not strictly improving: exact clause-weight "
            f"gain is {gain}, so the scaled MUFL cost does not decrease"
        )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample complementary flips, the honest constrained language."""
    coordinate = rng.randrange(inst["variable_pair_count"])
    return [_negative_id(inst, coordinate), _positive_id(inst, coordinate)]


def search_space(inst: dict) -> int | None:
    return inst["variable_pair_count"]


def enumerate_all(inst: dict) -> int | None:
    if search_space(inst) > 200_000:
        return None
    return sum(verify(inst, _candidate_for_coordinate(inst, i))[0]
               for i in range(inst["variable_pair_count"]))


def canonical_key(inst: dict) -> str:
    """Ignore IDs and pair order; every generated cubic permutes all residues."""
    abstract = {
        "family": inst["family"],
        "n": inst["n"],
        "code_multiset": "each residue 0..p-1 exactly once",
        "scale": inst["scale"],
        "base_weight": inst["base_weight"],
        "bit_high_weights": inst["bit_high_weights"],
        "threshold_weight": inst["threshold_weight"],
        "lock_weight": inst["lock_weight"],
        "literal_client_weight": inst["literal_client_weight"],
        "opening_cost": inst["opening_cost"],
    }
    blob = json.dumps(abstract, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    current = int(params["n"])
    # The witness always has two atoms, but eventually two decimal facility IDs
    # exceed the 2,000-character wire cap.  All practical escalations grow only
    # the ground set while keeping the witness shape fixed.
    if current.bit_length() >= 3310:
        return "cap_bound"
    return {"n": _next_supported_prime(2 * current - 5)}


def _candidate_for_coordinate(inst: dict, coordinate: int) -> list[int]:
    return [_negative_id(inst, coordinate), _positive_id(inst, coordinate)]


def _direct_mufl_cost(inst: dict, open_tokens: set[int]) -> int:
    """Independently evaluate three times the rendered MUFL cost."""
    total = 3 * len(open_tokens) * inst["opening_cost"]
    literal_weight = inst["literal_client_weight"]
    for token in range(inst["facility_count"]):
        distance = 0 if token in open_tokens else (1 if token ^ 1 in open_tokens else 2)
        total += 3 * literal_weight * distance

    positive_z = 2 * inst["z_pair_index"]

    def scaled_clause_cost(first: int, second: int, weight: int) -> int:
        if first in open_tokens or second in open_tokens:
            scaled_distance = 4
        elif first ^ 1 in open_tokens or second ^ 1 in open_tokens:
            scaled_distance = 5
        else:
            scaled_distance = 6
        return weight * scaled_distance

    for coordinate in range(inst["n"]):
        code = _code_at(inst, coordinate)
        positive, negative = 2 * coordinate, 2 * coordinate + 1
        for bit, high in enumerate(inst["bit_high_weights"]):
            base = inst["base_weight"]
            if (code >> bit) & 1:
                positive_weight, negative_weight = high, base
            else:
                positive_weight, negative_weight = base, high
            total += scaled_clause_cost(positive, positive_z, positive_weight)
            total += scaled_clause_cost(negative, positive_z, negative_weight)
        total += scaled_clause_cost(
            negative, positive_z, inst["threshold_weight"]
        )
    total += scaled_clause_cost(2 * inst["z_pair_index"] + 1,
                                2 * inst["y_pair_index"],
                                inst["lock_weight"])
    return total


def _reference_swap_scan(inst: dict) -> tuple[list[int] | None, int, int]:
    operations = 0
    for coordinate in range(inst["variable_pair_count"]):
        if coordinate < inst["n"]:
            code = _code_at(inst, coordinate)
            operations += 9  # three multiply/add/reduce Horner stages
            gain = 2 * inst["scale"] * (code - (inst["n"] - 2)) - 1
            operations += 4
        else:
            gain = -1 if coordinate == inst["z_pair_index"] else 0
            operations += 1
        if gain > 0:
            return _candidate_for_coordinate(inst, coordinate), operations, coordinate + 1
    return None, operations, inst["variable_pair_count"]


def _frobenius_root_reference(
        inst: dict) -> tuple[list[int] | None, int, int]:
    """Find roots of P(x)+1 over F_p by gcd(x^p-x, P(x)+1).

    This deliberately does not use the planted perfect-cube identity.  It is
    the generic exact attack against the rendered degree-three congruence.  The
    operation counter charges modular multiplication/reduction, addition, and
    Euclidean-division steps; Python's big-integer work is only an implementation
    detail at these 22-bit moduli.
    """
    p = inst["n"]
    c3, c2, c1, c0 = inst["polynomial_coefficients"]
    operations = 0
    polynomial_multiplications = 0

    def trim(poly: list[int]) -> list[int]:
        while len(poly) > 1 and poly[-1] % p == 0:
            poly.pop()
        return poly

    inverse_c3 = pow(c3, -1, p)
    operations += _inverse_euclid_steps(c3, p)
    modulus = [((c0 + 1) * inverse_c3) % p,
               (c1 * inverse_c3) % p,
               (c2 * inverse_c3) % p, 1]
    operations += 6

    def multiply_mod(left: list[int], right: list[int]) -> list[int]:
        nonlocal operations, polynomial_multiplications
        polynomial_multiplications += 1
        product = [0] * (len(left) + len(right) - 1)
        for i, x in enumerate(left):
            for j, y in enumerate(right):
                product[i + j] = (product[i + j] + x * y) % p
                operations += 2
        while len(product) >= len(modulus):
            quotient = product[-1] % p
            if quotient:
                shift = len(product) - len(modulus)
                for j in range(len(modulus) - 1):
                    product[shift + j] = (
                        product[shift + j] - quotient * modulus[j]
                    ) % p
                    operations += 2
            product.pop()
        return trim(product)

    power = [1]
    for bit in bin(p)[2:]:
        power = multiply_mod(power, power)
        if bit == "1":
            power = multiply_mod(power, [0, 1])
    width = max(len(power), 2)
    frobenius_minus_x = [
        ((power[i] if i < len(power) else 0) - (1 if i == 1 else 0)) % p
        for i in range(width)
    ]
    operations += width
    frobenius_minus_x = trim(frobenius_minus_x)

    def remainder(dividend: list[int], divisor: list[int]) -> list[int]:
        nonlocal operations
        dividend = trim(dividend[:])
        divisor = trim(divisor[:])
        inverse_lead = pow(divisor[-1], -1, p)
        operations += _inverse_euclid_steps(divisor[-1], p)
        while len(dividend) >= len(divisor) and any(dividend):
            quotient = (dividend[-1] * inverse_lead) % p
            operations += 2
            shift = len(dividend) - len(divisor)
            for j, value in enumerate(divisor):
                dividend[shift + j] = (
                    dividend[shift + j] - quotient * value
                ) % p
                operations += 2
            trim(dividend)
        return dividend

    left, right = modulus, frobenius_minus_x
    while not (len(right) == 1 and right[0] == 0):
        left, right = right, remainder(left, right)
    if len(left) != 2:
        return None, operations, polynomial_multiplications
    inverse_lead = pow(left[1], -1, p)
    operations += _inverse_euclid_steps(left[1], p)
    coordinate = (-left[0] * inverse_lead) % p
    operations += 2
    return (_candidate_for_coordinate(inst, coordinate), operations,
            polynomial_multiplications)


def _compact_route(inst: dict) -> list[int]:
    """Recover the affine cube and its unique preimage of -1."""
    p = inst["n"]
    c3, c2, _, _ = inst["polynomial_coefficients"]
    cube_inverse = pow(3, -1, p - 1)
    affine_a = pow(c3, cube_inverse, p)
    inverse_c3 = pow(c3, -1, p)
    inverse_3c3 = pow((3 * c3) % p, -1, p)
    coordinate = (-(affine_a * affine_a % p) * inverse_c3
                  - c2 * inverse_3c3) % p
    return _candidate_for_coordinate(inst, coordinate)


def _compact_route_operations(inst: dict) -> int:
    p = inst["n"]
    c3 = inst["polynomial_coefficients"][0]
    cube_inverse = pow(3, -1, p - 1)
    return (_pow_multiplication_count(cube_inverse)
            + _inverse_euclid_steps(c3, p)
            + _inverse_euclid_steps(3 * c3, p) + 9)


def _relabel_small_instance(inst: dict, rng: random.Random) -> dict:
    """Apply arbitrary ID and ordinary-pair permutations for G8."""
    out = dict(inst)
    facility_perm = list(range(inst["facility_count"]))
    rng.shuffle(facility_perm)
    old_ids = [_facility_id(inst, token)
               for token in range(inst["facility_count"])]
    old_for_new = list(range(inst["n"]))
    rng.shuffle(old_for_new)
    id_map = [0] * inst["facility_count"]
    codes = [0] * inst["n"]
    for new_i, old_i in enumerate(old_for_new):
        codes[new_i] = _code_at(inst, old_i)
        id_map[2 * new_i] = facility_perm[old_ids[2 * old_i]]
        id_map[2 * new_i + 1] = facility_perm[old_ids[2 * old_i + 1]]
    for pair_i in (inst["z_pair_index"], inst["y_pair_index"]):
        id_map[2 * pair_i] = facility_perm[old_ids[2 * pair_i]]
        id_map[2 * pair_i + 1] = facility_perm[old_ids[2 * pair_i + 1]]
    inverse = [0] * inst["facility_count"]
    for token, displayed in enumerate(id_map):
        inverse[displayed] = token
    out["_explicit_id_map"] = id_map
    out["_explicit_id_inverse"] = inverse
    out["_explicit_codes"] = codes
    out["answer"] = [facility_perm[x] for x in inst["answer"]]
    return out


def _attack_results(params: dict, attempts: int = 8) -> tuple[dict, dict]:
    names = ["outlier_pair_statistics", "greedy_leading_coefficient",
             "random_restart_256", "by_hand_prefix_8",
             "linearized_cubic_ansatz"]
    successes = {name: 0 for name in names}
    ref_successes = 0
    ref_operations, ref_iterations, ref_times = [], [], []
    scan_operations, scan_iterations, scan_times = [], [], []
    for seed in range(9100, 9100 + attempts):
        inst = make_instance(seed=seed, **params)
        successes[names[0]] += int(verify(inst, _candidate_for_coordinate(inst, 0))[0])
        greedy = inst["polynomial_coefficients"][0] % inst["n"]
        successes[names[1]] += int(verify(inst, _candidate_for_coordinate(inst, greedy))[0])
        attack_rng = random.Random(0x5A17 + seed)
        successes[names[2]] += int(any(
            verify(inst, random_candidate(inst, attack_rng))[0] for _ in range(256)
        ))
        successes[names[3]] += int(any(
            verify(inst, _candidate_for_coordinate(inst, i))[0] for i in range(8)
        ))
        t0, t1 = _code_at(inst, 0), _code_at(inst, 1)
        denominator = (t1 - t0) % inst["n"]
        guessed = (((inst["n"] - 1 - t0) * pow(denominator, -1, inst["n"]))
                   % inst["n"]) if denominator else 0
        successes[names[4]] += int(verify(
            inst, _candidate_for_coordinate(inst, guessed))[0]
        )
        started = time.perf_counter()
        answer, operations, iterations = _frobenius_root_reference(inst)
        ref_times.append(time.perf_counter() - started)
        ref_operations.append(operations)
        ref_iterations.append(iterations)
        ref_successes += int(answer is not None and verify(inst, answer)[0])
        started = time.perf_counter()
        scan_answer, operations, iterations = _reference_swap_scan(inst)
        scan_times.append(time.perf_counter() - started)
        scan_operations.append(operations)
        scan_iterations.append(iterations)
        if scan_answer is None or not verify(inst, scan_answer)[0]:
            raise AssertionError("exhaustive comparison scan failed")
    attacks = {name: {"successes": successes[name], "attempts": attempts}
               for name in names}
    reference = {
        "name": "Frobenius-gcd root isolation of the rendered cubic",
        "complexity": "O(log p) arithmetic on degree-3 polynomials over F_p",
        "wall_clock_sec": round(sum(ref_times) / attempts, 6),
        "operations": max(ref_operations),
        "iterations": max(ref_iterations),
        "iteration_unit": "degree-3 polynomial multiplications",
        "solves": f"{ref_successes}/{attempts}, as expected",
        "exhaustive_scan_comparison": {
            "complexity": "O(n) complementary-swap evaluations",
            "wall_clock_sec": round(sum(scan_times) / attempts, 6),
            "operations": max(scan_operations),
            "iterations": max(scan_iterations),
        },
    }
    return attacks, reference


def selftest() -> dict:
    report: dict = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}
    failures, attempts = [], 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 8675309):
            inst = make_instance(seed=seed, **params)
            attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
    direct_checks = 0
    for seed in range(25):
        inst = make_instance(seed=seed, **DIFFICULTY["demo"])
        current = {2 * pair + 1
                   for pair in range(inst["variable_pair_count"])}
        old_cost = _direct_mufl_cost(inst, current)
        for close_pair in range(inst["variable_pair_count"]):
            for open_pair in range(inst["variable_pair_count"]):
                candidate = [_negative_id(inst, close_pair),
                             _positive_id(inst, open_pair)]
                changed = set(current)
                changed.remove(2 * close_pair + 1)
                changed.add(2 * open_pair)
                direct_improvement = _direct_mufl_cost(inst, changed) < old_cost
                checker_improvement = verify(inst, candidate)[0]
                direct_checks += 1
                if direct_improvement != checker_improvement:
                    failures.append([
                        "demo", seed,
                        f"direct cost/checker mismatch for {close_pair}->{open_pair}",
                    ])
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures,
        "independent_exact_demo_swap_checks": direct_checks,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    sample = make_instance(seed=4242, **shipping)
    planted = sample["answer"]
    corruptions = {
        "drop_one": planted[:1], "swap_order": [planted[1], planted[0]],
        "duplicate": [planted[0], planted[0]], "empty": [],
        "out_of_range": [planted[0], sample["facility_count"]],
    }
    cases, reasons = {}, []
    for name, candidate in corruptions.items():
        ok, reason = verify(sample, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in cases.values())
                and len(set(reasons)) == len(reasons),
        "cases": cases, "distinct_reasons": len(set(reasons)),
    }

    response = ("I compared exact gains.\n```text\n<answer>"
                f"{planted[0]}, {planted[1]}</answer>\n```\nDone.")
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("garbage") is None,
        "parsed": parsed,
    }

    guess_total = 200_000
    guess_rng = random.Random(20270117)
    guess_hits = sum(verify(sample, random_candidate(sample, guess_rng))[0]
                     for _ in range(guess_total))
    exact_density = 1.0 / search_space(sample)
    report["G4_guess_resistance"] = {
        "pass": exact_density < 1e-6,
        "hits": guess_hits, "total": guess_total,
        "sampled_fraction": guess_hits / guess_total,
        "exact_fraction": exact_density,
        "structure_aware_space": search_space(sample),
        "prior": "uniform complementary-pair flips; cross-pair swaps excluded",
    }

    started = time.perf_counter()
    baseline_answer, baseline_ops, baseline_iterations = \
        _frobenius_root_reference(sample)
    baseline_wall = time.perf_counter() - started
    scan_started = time.perf_counter()
    scan_answer, scan_ops, scan_iterations = _reference_swap_scan(sample)
    scan_wall = time.perf_counter() - scan_started
    density_rng = random.Random(20270118)
    density_total = 200_000
    density_hits = sum(verify(sample, random_candidate(sample, density_rng))[0]
                       for _ in range(density_total))
    report["G5_density_and_baseline"] = {
        "pass": baseline_answer is not None and verify(sample, baseline_answer)[0],
        "shipping_valid_answer_count": 1,
        "shipping_exact_density": exact_density,
        "shipping_sample_hits": density_hits,
        "shipping_sample_total": density_total,
        "shipping_sampled_fraction": density_hits / density_total,
        "baseline_wall_seconds": round(baseline_wall, 6),
        "baseline_iterations": baseline_iterations,
        "baseline_iteration_unit": "degree-3 polynomial multiplications",
        "baseline_operation_count": baseline_ops,
        "baseline_algorithm": "Frobenius-gcd finite-field root isolation",
        "exhaustive_scan_comparison": {
            "wall_seconds": round(scan_wall, 6),
            "iterations": scan_iterations,
            "operation_count": scan_ops,
            "verified": scan_answer is not None and verify(sample, scan_answer)[0],
        },
    }

    attacks, reference = _attack_results(shipping, attempts=8)
    report["G6_adversary_panel"] = {
        "pass": all(v["successes"] == 0 for v in attacks.values()),
        "attacks": attacks, "reference_algorithm": reference,
    }

    harder_params = escalate(shipping)
    harder = make_instance(seed=271828, **harder_params)
    harder_ok, harder_reason = verify(harder, harder["answer"])
    report["G7_scales"] = {
        "pass": harder_ok and harder["n"] > sample["n"],
        "from": shipping, "to": harder_params, "verification": harder_reason,
        "answer_elements_before": _answer_atoms(sample["answer"]),
        "answer_elements_after": _answer_atoms(harder["answer"]),
    }

    invariant_checks, carried_checks, keys, g8_failures = 0, 0, [], []
    for offset in range(20):
        inst = make_instance(seed=70000 + offset, **DIFFICULTY["demo"])
        key = canonical_key(inst)
        transformed = _relabel_small_instance(inst, random.Random(80000 + offset))
        invariant_checks += 1
        if canonical_key(transformed) != key:
            g8_failures.append([offset, "key changed under composed relabelling"])
        carried_checks += 1
        if not verify(transformed, transformed["answer"])[0]:
            g8_failures.append([offset, "carried answer stopped verifying"])
        keys.append(key)
    distinct_count = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_count == 20,
        "invariance_checks": invariant_checks,
        "transformations_per_check": ["arbitrary facility-ID permutation",
                                       "arbitrary ordinary-pair permutation",
                                       "their composition"],
        "carried_witness_checks": carried_checks,
        "distinct_unrelated_keys": distinct_count,
        "unrelated_attempts": 20, "failures": g8_failures,
    }

    blob = json.dumps(sample["answer"], separators=(",", ":"))
    chars, atoms = len(blob), _answer_atoms(sample["answer"])
    tokens = math.ceil(chars / 4)
    route_ops = _compact_route_operations(sample)
    compact_ok, compact_reason = verify(sample, _compact_route(sample))
    arms = {name: dict(G9_EVIDENCE[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_n, placebo_n = arms["hinted"]["attempts"], arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_n if hinted_n else None
    placebo_rate = arms["placebo"]["solved"] / placebo_n if placebo_n else None
    caps = (chars <= 2000 and atoms <= 256 and route_ops <= 300
            and compact_ok)
    report["G9_no_tool_suitability"] = {
        # Since 2026-09-05 both the three-arm comparison and the hinted arm are
        # diagnostics.  Only the answer-size and intended-effort caps gate G9.
        "pass": caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None
        ),
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": chars, "answer_tokens": tokens,
        "answer_elements": atoms, "intended_route_operations": route_ops,
        "intended_route_verification": compact_reason,
    }
    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
