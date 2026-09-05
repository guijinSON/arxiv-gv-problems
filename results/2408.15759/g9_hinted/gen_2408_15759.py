"""Verified problem generator for arXiv:2408.15759.

The family asks for an exact top intersection of rationally weighted Scorza
divisor classes. Lemma 4.5 supplies the unweighted identity. The weights are a
permuted telescoping chain whose permutation is specified by reversible word maps.
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
from array import array
from fractions import Fraction


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # Fraction is the exact standard-library fallback used here.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "telescoping",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "Scorza divisor classes in the numerical cycle ring N(C^n)",
        "rationally weighted top intersection on a genus-three curve product",
        "a collected two-term rational exponential expression",
    ],
    "verification_operations": [
        "exact rational reduction",
        "exact integer multiplication",
        "symbolic coefficient comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The fixed-width mixer is a composition of bijections, so its hidden "
        "indices preserve the complete residue set and the rational weights "
        "collapse to the two endpoints of one telescoping chain."
    ),
    "hardness_basis": (
        "Track B: exact factor-balance enumeration is an O(n) algorithm; at the "
        "shipping preset n=524288 it executes about 13.1 million counted exact "
        "or bitwise primitives (with measured wall-clock reported by selftest), "
        "whereas recognizing the reversible mixer and Lemma 4.5 leaves eight "
        "exact arithmetic operations."
    ),
    "max_answer_tokens": 42,
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

DIFFICULTY = {
    "demo": {"n": 8, "rounds": 2, "label_bits": 7},
    "easy": {"n": 32768, "rounds": 5, "label_bits": 22},
    "medium": {"n": 131072, "rounds": 7, "label_bits": 27},
    "hard": {"n": 524288, "rounds": 9, "label_bits": 34},
}
SHIPPING_DIFFICULTY = "hard"

if os.environ.get("GV_G9_SINGLE") == "1":
    DIFFICULTY = {SHIPPING_DIFFICULTY: dict(DIFFICULTY[SHIPPING_DIFFICULTY])}


STRUCTURAL_HINT = (
    "The fixed-width index mixer preserves the multiset of all residue labels."
)
PLACEBO_HINT = (
    "The fixed-width notation makes careful tracking of every index convention useful."
)

MAX_N = 1 << 22
MAX_ROUNDS = 12
MAX_LABEL_BITS = 44
GLOBAL_COEFFICIENT_BOUND = 1 << 72
GLOBAL_DENOMINATOR_BOUND = 1 << 45

CERTIFICATE_LANGUAGE = {
    "description": (
        "A collected expression A*3^n+B as exactly two ordered JSON terms. "
        "Term 0 has base 3, positive rational coefficient, and exponent n; "
        "term 1 has base 1, negative rational coefficient, and exponent n. "
        "Rationals are [numerator,denominator] with positive denominator and "
        "the instance's inclusive height bounds; unreduced encodings are allowed."
    ),
    "bounds": {
        "n_terms": 2,
        "max_n": MAX_N,
        "max_rounds": MAX_ROUNDS,
        "max_label_bits": MAX_LABEL_BITS,
        "coefficient_abs_bound": GLOBAL_COEFFICIENT_BOUND,
        "denominator_bound": GLOBAL_DENOMINATOR_BOUND,
        "bases": [3, 1],
    },
}

# Filled after the script-owned oracle runs. Zero-attempt entries are honest
# placeholders while the purely local gates are being developed.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not run",
}

NOTES = """\
Section 2 fixes a heptagon as seven ordered projective lines with no triple
intersection, and its adjoint as the quartic through the fourteen intersections
of nonconsecutive lines. Theorem 5.5 counts the generic inverse fibre, while
Section 3 reconstructs heptagons through a Scorza-correspondence intersection;
neither gives a scalable exact inverse algorithm whose distributional cost could
support the initially suggested planted-heptagon Track-A family. Sections 3 and
5 instead use intersection theory and symbolic computation to analyse fibres.

This module uses the paper's native Section 4 objects. Equation (4.2) gives
[S(eta)]=2*x_1+2*x_2+Delta, and Lemma 4.5 proves that the cyclic top intersection
on C^n is 2*3^n-6. Multiplying each divisor class by a rational scalar multiplies
the top intersection by the product of those scalars. The generator chooses the
answer first as the endpoint quotient r(n)/r(0). It then reindexes all n adjacent
ratios r(j+1)/r(j) by a seed-dependent composition of reversible word operations
and inserts an exposed common factor in each ratio. This is inverse generation
plus a structure-preserving permutation, never solution of a generated instance.

This is Track B. The reference algorithm enumerates every hidden index and keeps
an exact signed factor balance. The compact route recognizes that XOR by a
constant, odd affine maps modulo a power of two, triangular XOR-shifts, and word
rotations are all bijections. Thus the hidden indices are merely a permutation
of 0,...,n-1, every internal r(j) cancels, and only r(n)/r(0) remains. The attack
panel tests an unweighted ansatz, the largest single-scale outlier, a first/last
greedy product, and bounded random symbolic guesses.
"""


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_power_of_two(value):
    return _is_int(value) and value > 0 and (value & (value - 1)) == 0


def _rat_json(value):
    value = Fraction(value)
    return [value.numerator, value.denominator]


def _make_expression(weight, n):
    weight = Fraction(weight)
    return {
        "terms": [
            {"coefficient": _rat_json(2 * weight), "base": 3, "exponent": n},
            {"coefficient": _rat_json(-6 * weight), "base": 1, "exponent": n},
        ]
    }


def _operation_types(rounds):
    cycle = ("xor", "affine", "xorshift_right", "xorshift_left", "rotate_left")
    return [cycle[i % len(cycle)] for i in range(rounds)]


def _generate_mixer(rng, n, rounds):
    bits = n.bit_length() - 1
    types = _operation_types(rounds)
    rng.shuffle(types)
    ops = []
    for kind in types:
        if kind == "xor":
            ops.append({"op": kind, "constant": rng.randrange(n)})
        elif kind == "affine":
            ops.append({
                "op": kind,
                "multiplier": rng.randrange(1, n, 2),
                "offset": rng.randrange(n),
            })
        else:
            ops.append({"op": kind, "shift": rng.randrange(1, bits)})
    return ops


def _apply_mixer(value, n, ops, count=False):
    mask = n - 1
    bits = n.bit_length() - 1
    x = value
    primitive_count = 0
    for operation in ops:
        kind = operation["op"]
        if kind == "xor":
            x ^= operation["constant"]
            primitive_count += 1
        elif kind == "affine":
            x = (operation["multiplier"] * x + operation["offset"]) & mask
            primitive_count += 3
        elif kind == "xorshift_right":
            x ^= x >> operation["shift"]
            primitive_count += 2
        elif kind == "xorshift_left":
            x ^= (x << operation["shift"]) & mask
            primitive_count += 3
        elif kind == "rotate_left":
            shift = operation["shift"]
            x = ((x << shift) & mask) | (x >> (bits - shift))
            primitive_count += 4
        else:
            raise ValueError("unknown mixer operation")
    return (x, primitive_count) if count else x


def _mixer_is_bijective(inst):
    n = inst.get("n")
    ops = inst.get("mixer")
    if not _is_power_of_two(n) or n < 4 or not isinstance(ops, list):
        return False
    bits = n.bit_length() - 1
    for operation in ops:
        if not isinstance(operation, dict) or "op" not in operation:
            return False
        kind = operation["op"]
        if kind == "xor":
            if (set(operation) != {"op", "constant"}
                    or not _is_int(operation["constant"])
                    or not 0 <= operation["constant"] < n):
                return False
        elif kind == "affine":
            if (set(operation) != {"op", "multiplier", "offset"}
                    or not _is_int(operation["multiplier"])
                    or operation["multiplier"] % 2 != 1
                    or not 1 <= operation["multiplier"] < n
                    or not _is_int(operation["offset"])
                    or not 0 <= operation["offset"] < n):
                return False
        elif kind in {"xorshift_right", "xorshift_left", "rotate_left"}:
            if (set(operation) != {"op", "shift"}
                    or not _is_int(operation["shift"])
                    or not 1 <= operation["shift"] < bits):
                return False
        else:
            return False
    return bool(ops)


def _label(inst, index):
    return inst["label_slope"] * index + inst["label_offset"]


def _closed_weight(inst):
    if not _mixer_is_bijective(inst):
        raise ValueError("the index mixer is not certified bijective")
    return Fraction(_label(inst, inst["n"]), _label(inst, 0))


def _language_bounds(n, slope, offset):
    coefficient = 8 * (slope * n + offset)
    denominator = offset
    if coefficient > GLOBAL_COEFFICIENT_BOUND:
        raise ValueError("coefficient bound exceeds the declared certificate language")
    if denominator > GLOBAL_DENOMINATOR_BOUND:
        raise ValueError("denominator bound exceeds the declared certificate language")
    return coefficient, denominator


def make_instance(n, seed=0, **params):
    """Construct a permuted telescoping weighting of Lemma 4.5."""
    rounds = params.pop("rounds", 7)
    label_bits = params.pop("label_bits", 24)
    if params:
        raise ValueError("unknown parameters: " + ", ".join(sorted(params)))
    if not _is_power_of_two(n) or not 8 <= n <= MAX_N:
        raise ValueError(f"n must be a power of two in 8..{MAX_N}")
    bits = n.bit_length() - 1
    if not _is_int(rounds) or not 2 <= rounds <= MAX_ROUNDS:
        raise ValueError(f"rounds must be in 2..{MAX_ROUNDS}")
    if not _is_int(label_bits) or not 7 <= label_bits <= MAX_LABEL_BITS:
        raise ValueError(f"label_bits must be in 7..{MAX_LABEL_BITS}")

    rng = random.Random(seed)
    mixer = _generate_mixer(rng, n, rounds)
    low = 1 << (label_bits - 1)
    high = 1 << label_bits
    slope = rng.randrange(low, high)
    offset = rng.randrange(low, high)
    common = math.gcd(slope, offset)
    slope //= common
    offset //= common
    mask_multiplier = rng.randrange(1, n, 2)
    mask_offset = rng.randrange(n)

    coefficient_bound, denominator_bound = _language_bounds(n, slope, offset)
    weight = Fraction(slope * n + offset, offset)
    answer = _make_expression(weight, n)
    for term in answer["terms"]:
        if abs(term["coefficient"][0]) > coefficient_bound:
            raise AssertionError("constructed numerator exceeds its declared bound")
        if term["coefficient"][1] > denominator_bound:
            raise AssertionError("constructed denominator exceeds its declared bound")

    return {
        "paper": "2408.15759",
        "n": n,
        "word_bits": bits,
        "genus": 3,
        "mixer": mixer,
        "label_slope": slope,
        "label_offset": offset,
        "mask_multiplier": mask_multiplier,
        "mask_offset": mask_offset,
        "language": {
            "coefficient_abs_bound": coefficient_bound,
            "denominator_bound": denominator_bound,
            "exponent": n,
            "bases": [3, 1],
        },
        "answer": answer,
    }


def _render_operation(number, operation, n, bits):
    kind = operation["op"]
    if kind == "xor":
        rule = f"x := x XOR {operation['constant']}"
    elif kind == "affine":
        rule = (f"x := ({operation['multiplier']}*x + {operation['offset']}) "
                f"mod {n}")
    elif kind == "xorshift_right":
        rule = f"x := x XOR (x >> {operation['shift']})"
    elif kind == "xorshift_left":
        rule = f"x := x XOR ((x << {operation['shift']}) AND {n - 1})"
    elif kind == "rotate_left":
        rule = f"x := ROTL_{bits}(x,{operation['shift']})"
    else:
        raise ValueError("unknown mixer operation")
    return f"  {number}. {rule}"


def render(inst):
    n = inst["n"]
    bits = inst["word_bits"]
    coefficient_bound = inst["language"]["coefficient_abs_bound"]
    denominator_bound = inst["language"]["denominator_bound"]
    operations = "\n".join(
        _render_operation(i + 1, operation, n, bits)
        for i, operation in enumerate(inst["mixer"])
    )
    statement = f"""Compute an exact weighted Scorza-class intersection in collected form.

Let C be a smooth plane quartic, and let eta be an even theta characteristic
with h^0(C,eta)=0. On C^{n}, x_k denotes the pullback of the class of a
point from coordinate k, and Delta_kl denotes the pullback of the diagonal
from coordinates k and l. Coordinate indices are 1-based. For i=0,...,{n - 1},
put k=i+1 and l=((i+1) mod {n})+1 and define the Scorza divisor class

    S_i = 2*x_k + 2*x_l + Delta_kl.

The exact intersection rules are: degree(x_1*...*x_{n})=1; x_k^2=0;
x_k*Delta_kl=x_k*x_l; a connected tree of distinct diagonal factors is its
small-diagonal class; and a connected cycle of diagonal factors has degree
-(2g-2)=-4 because g=3. Products over disconnected components multiply,
and degree is linear over rational coefficients. These rules completely
determine the top-degree product below.

All mixer values are unsigned {bits}-bit integers, hence lie in 0,...,{n - 1}.
XOR, AND, <<, and >> are the usual bitwise operations with zero-filled shifts.
ROTL_{bits}(x,s) rotates the {bits}-bit word x left by s positions. For each
i=0,...,{n - 1}, start with x=i and apply these assignments in order; call the
final value j_i:

{operations}

Define the positive integers

    r(z) = {inst['label_slope']}*z + {inst['label_offset']},
    m(i) = 1 + (({inst['mask_multiplier']}*i + {inst['mask_offset']}) mod {n}),

and the exact rational scale

    s_i = (r(j_i+1)*m(i)) / (r(j_i)*m(i)).

Compute the top intersection

    I = product over i=0,...,{n - 1} of (s_i*S_i).

Give I in collected symbolic form A*3^{n}+B as exactly two ordered terms.
Term 0 must have base 3, exponent {n}, and a positive rational coefficient.
Term 1 must have base 1, exponent {n}, and a negative rational coefficient.
A rational a/b is encoded as [a,b], with 1 <= |a| <= {coefficient_bound}
and 1 <= b <= {denominator_bound}; bounds are inclusive and b is positive.
Coefficients need not be reduced. The term order is mandatory.

Give your final answer inside <answer></answer> tags as one JSON object with
the sole key "terms" and exactly two objects of the displayed shape.
Example: <answer>{{"terms":[{{"coefficient":[2,1],"base":3,"exponent":{n}}},{{"coefficient":[-6,1],"base":1,"exponent":{n}}}]}}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    if not isinstance(text, str):
        return None
    tagged = re.search(r"<answer\b[^>]*>(.*?)</answer>", text,
                       flags=re.IGNORECASE | re.DOTALL)
    candidates = [tagged.group(1)] if tagged else []
    candidates.extend(re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text,
                                 flags=re.IGNORECASE | re.DOTALL))
    if not candidates:
        start, end = text.find("{"), text.rfind("}")
        if 0 <= start < end:
            candidates.append(text[start:end + 1])
    for blob in candidates:
        try:
            value = json.loads(blob.strip())
        except (TypeError, ValueError):
            continue
        if isinstance(value, dict):
            return value
    return None


def _answer_shape(inst, answer):
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if not answer:
        return False, "answer object is empty"
    if set(answer) != {"terms"}:
        return False, "answer must have the sole key 'terms'"
    terms = answer["terms"]
    if not isinstance(terms, list):
        return False, "terms must be a JSON list"
    if not terms:
        return False, "term list is empty"
    if len(terms) != 2:
        return False, "term list must contain exactly two terms"
    if terms[0] == terms[1]:
        return False, "the two term objects must be distinct"
    coefficient_bound = inst["language"]["coefficient_abs_bound"]
    denominator_bound = inst["language"]["denominator_bound"]
    expected_bases = (3, 1)
    for i, term in enumerate(terms):
        if not isinstance(term, dict) or set(term) != {"coefficient", "base", "exponent"}:
            return False, f"term {i} must have coefficient, base, and exponent"
        coefficient = term["coefficient"]
        if (not isinstance(coefficient, list) or len(coefficient) != 2
                or not all(_is_int(x) for x in coefficient)):
            return False, f"term {i} coefficient must be [integer,integer]"
        if not 1 <= abs(coefficient[0]) <= coefficient_bound:
            return False, f"term {i} numerator is outside the inclusive bound"
        if not 1 <= coefficient[1] <= denominator_bound:
            return False, f"term {i} denominator is outside the inclusive bound"
        if i == 0 and coefficient[0] <= 0:
            return False, "term 0 numerator must be positive"
        if i == 1 and coefficient[0] >= 0:
            return False, "term 1 numerator must be negative"
        if term["base"] != expected_bases[i] or not _is_int(term["base"]):
            return False, f"term {i} base must equal {expected_bases[i]}"
        if term["exponent"] != inst["n"] or not _is_int(term["exponent"]):
            return False, f"term {i} exponent must equal n={inst['n']}"
    return True, "ok"


def verify(inst, answer):
    ok, reason = _answer_shape(inst, answer)
    if not ok:
        return False, reason
    try:
        weight = _closed_weight(inst)
        got_leading = Fraction(*answer["terms"][0]["coefficient"])
        got_constant = Fraction(*answer["terms"][1]["coefficient"])
    except (ArithmeticError, OverflowError, TypeError, ValueError, KeyError):
        return False, "answer or instance could not be evaluated exactly"
    if got_leading != 2 * weight:
        return False, "coefficient of 3^n is incorrect"
    if got_constant != -6 * weight:
        return False, "constant coefficient is incorrect"
    return True, "ok"


def random_candidate(inst, rng):
    coefficient_bound = inst["language"]["coefficient_abs_bound"]
    denominator_bound = inst["language"]["denominator_bound"]
    return {"terms": [
        {"coefficient": [rng.randint(1, coefficient_bound),
                         rng.randint(1, denominator_bound)],
         "base": 3, "exponent": inst["n"]},
        {"coefficient": [-rng.randint(1, coefficient_bound),
                         rng.randint(1, denominator_bound)],
         "base": 1, "exponent": inst["n"]},
    ]}


def search_space(inst):
    coefficient_bound = inst["language"]["coefficient_abs_bound"]
    denominator_bound = inst["language"]["denominator_bound"]
    choices_per_coefficient = coefficient_bound * denominator_bound
    return choices_per_coefficient * choices_per_coefficient


def enumerate_all(inst):
    if search_space(inst) > 1_000_000:
        return None
    count = 0
    cb = inst["language"]["coefficient_abs_bound"]
    db = inst["language"]["denominator_bound"]
    for a in range(1, cb + 1):
        for b in range(1, db + 1):
            for c in range(1, cb + 1):
                for d in range(1, db + 1):
                    candidate = {"terms": [
                        {"coefficient": [a, b], "base": 3, "exponent": inst["n"]},
                        {"coefficient": [-c, d], "base": 1, "exponent": inst["n"]},
                    ]}
                    count += verify(inst, candidate)[0]
    return count


def canonical_key(inst):
    # Mixer keys and exposed masks only re-present the same complete product.
    slope = inst["label_slope"]
    offset = inst["label_offset"]
    common = math.gcd(slope, offset)
    payload = {"n": inst["n"], "label_slope": slope // common,
               "label_offset": offset // common}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def _equivalent_reencoding(inst, seed):
    out = json.loads(json.dumps(inst))
    rng = random.Random(seed)
    out["mixer"] = _generate_mixer(rng, out["n"], len(out["mixer"]))
    out["mask_multiplier"] = rng.randrange(1, out["n"], 2)
    out["mask_offset"] = rng.randrange(out["n"])
    scale = rng.randrange(2, 12)
    out["label_slope"] *= scale
    out["label_offset"] *= scale
    cb, db = _language_bounds(out["n"], out["label_slope"], out["label_offset"])
    out["language"]["coefficient_abs_bound"] = cb
    out["language"]["denominator_bound"] = db
    return out


def _reference_solve(inst):
    """Expand every hidden index and maintain an exact signed factor balance."""
    n = inst["n"]
    balance = array("b", [0]) * (n + 1)
    operations = 0
    for i in range(n):
        j, mixer_operations = _apply_mixer(i, n, inst["mixer"], count=True)
        operations += mixer_operations
        balance[j + 1] += 1
        balance[j] -= 1
        operations += 2
    negative = positive = None
    for index, multiplicity in enumerate(balance):
        operations += 1
        if multiplicity == -1:
            negative = index
        elif multiplicity == 1:
            positive = index
        elif multiplicity != 0:
            return None, operations
    if negative is None or positive is None:
        return None, operations
    operations += 8
    weight = Fraction(_label(inst, positive), _label(inst, negative))
    return _make_expression(weight, n), operations


def _compact_solve(inst):
    """Use mixer bijectivity and the endpoint quotient without enumerating indices."""
    if not _mixer_is_bijective(inst):
        return None, 0
    return _make_expression(_closed_weight(inst), inst["n"]), 8


def _attack_unweighted(inst):
    return _make_expression(Fraction(1), inst["n"])


def _attack_largest_single_scale(inst):
    return _make_expression(Fraction(_label(inst, 1), _label(inst, 0)), inst["n"])


def _attack_first_last(inst):
    n = inst["n"]
    first = _apply_mixer(0, n, inst["mixer"])
    last = _apply_mixer(n - 1, n, inst["mixer"])
    weight = (Fraction(_label(inst, first + 1), _label(inst, first))
              * Fraction(_label(inst, last + 1), _label(inst, last)))
    return _make_expression(weight, n)


def escalate(params):
    if os.environ.get("GV_G9_SINGLE") == "1":
        return None
    harder = dict(params)
    n = int(harder.get("n", 8))
    rounds = int(harder.get("rounds", 2))
    label_bits = int(harder.get("label_bits", 7))
    changed = False
    if n < MAX_N:
        harder["n"] = min(MAX_N, 2 * n)
        changed = True
    if rounds < MAX_ROUNDS:
        harder["rounds"] = rounds + 1
        changed = True
    if label_bits < MAX_LABEL_BITS:
        harder["label_bits"] = min(MAX_LABEL_BITS, label_bits + 2)
        changed = True
    return harder if changed else None


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _fast_candidate_ok(inst, answer, expected_coefficients):
    ok, _ = _answer_shape(inst, answer)
    if not ok:
        return False
    leading = Fraction(*answer["terms"][0]["coefficient"])
    constant = Fraction(*answer["terms"][1]["coefficient"])
    return (leading, constant) == expected_coefficients


def selftest():
    report = {}
    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 3, 11):
            inst = make_instance(seed=seed, **params)
            attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts,
        "construction": "Lemma 4.5, scalar multilinearity, and a permuted telescope",
        "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=97, **shipping_params)
    answer = json.loads(json.dumps(inst["answer"]))
    corruptions = {}
    bad = json.loads(json.dumps(answer)); bad["terms"] = bad["terms"][:-1]
    corruptions["drop_one_element"] = verify(inst, bad)
    bad = json.loads(json.dumps(answer)); bad["terms"][1] = json.loads(json.dumps(bad["terms"][0]))
    corruptions["duplicate_one_element"] = verify(inst, bad)
    corruptions["empty"] = verify(inst, {})
    bad = json.loads(json.dumps(answer)); bad["terms"][0]["coefficient"][0] = (
        inst["language"]["coefficient_abs_bound"] + 1)
    corruptions["out_of_range"] = verify(inst, bad)
    bad = json.loads(json.dumps(answer)); bad["terms"][0]["base"], bad["terms"][1]["base"] = (
        bad["terms"][1]["base"], bad["terms"][0]["base"])
    corruptions["swap_two_elements"] = verify(inst, bad)
    reasons = [why for ok, why in corruptions.values() if not ok]
    report["G2_rejects_corruption"] = {
        "pass": all(not ok for ok, _ in corruptions.values()) and len(set(reasons)) == 5,
        "distinct_reasons": len(set(reasons)),
        "cases": {name: {"rejected": not result[0], "reason": result[1]}
                  for name, result in corruptions.items()},
    }

    model_reply = ("The collected coefficients are below.\n```json\n<answer>"
                   + json.dumps(answer) + "</answer>\n```\n")
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("garbage") is None,
        "parsed_equals_answer": parsed == answer,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    weight = _closed_weight(inst)
    expected_coefficients = (2 * weight, -6 * weight)
    guess_rng = random.Random(240815759)
    guess_total = 200_000
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += _fast_candidate_ok(
            inst, random_candidate(inst, guess_rng), expected_coefficients)
    guess_elapsed = time.perf_counter() - start
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits, "total": guess_total,
        "fraction": guess_hits / guess_total,
        "candidate_space": search_space(inst),
        "structure_aware_constraints": [
            "exactly two ordered collected terms",
            "bases already fixed to 3 and 1",
            "both exponents already fixed to n",
            "coefficient signs, heights, and positive denominators already enforced",
        ],
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attack_instances = [make_instance(seed=1000 + i, **shipping_params) for i in range(8)]
    reference_results = []
    compact_results = []
    for candidate_inst in attack_instances:
        start = time.perf_counter()
        candidate, operations = _reference_solve(candidate_inst)
        elapsed = time.perf_counter() - start
        reference_results.append((candidate is not None and verify(candidate_inst, candidate)[0],
                                  operations, elapsed))
        start = time.perf_counter()
        candidate, operations = _compact_solve(candidate_inst)
        elapsed = time.perf_counter() - start
        compact_results.append((candidate is not None and verify(candidate_inst, candidate)[0],
                                operations, elapsed))

    baseline_rng = random.Random(424242)
    baseline_restarts = 4096
    baseline_hits = 0
    start = time.perf_counter()
    for _ in range(baseline_restarts):
        baseline_hits += _fast_candidate_ok(
            inst, random_candidate(inst, baseline_rng), expected_coefficients)
    baseline_elapsed = time.perf_counter() - start
    report["G5_density_and_baseline_cost"] = {
        "pass": (guess_hits == 0 and baseline_hits == 0
                 and all(result[0] for result in reference_results)),
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density_estimate": guess_hits / guess_total,
        "shipping_candidate_space": search_space(inst),
        "exact_enumeration": None,
        "exact_enumeration_reason": "bounded symbolic language exceeds the 1,000,000 cap",
        "strongest_failing_attack": "random_restart_4096",
        "baseline_attack_restarts": baseline_restarts,
        "baseline_attack_successes": baseline_hits,
        "baseline_attack_wall_clock_sec": round(baseline_elapsed, 6),
        "reference_operation_count_max": max(result[1] for result in reference_results),
        "reference_wall_clock_sec_total_8": round(sum(result[2] for result in reference_results), 6),
        "reference_wall_clock_sec_per_instance": round(
            sum(result[2] for result in reference_results) / 8, 6),
    }

    attack_names = (
        "outlier_largest_single_scale", "greedy_first_last_scales",
        "random_restart_256", "by_hand_unweighted_scorza_ansatz",
    )
    attacks = {name: {"successes": 0, "attempts": 8} for name in attack_names}
    attack_times = {name: 0.0 for name in attack_names}
    for index, candidate_inst in enumerate(attack_instances):
        probes = {
            "outlier_largest_single_scale": lambda: _attack_largest_single_scale(candidate_inst),
            "greedy_first_last_scales": lambda: _attack_first_last(candidate_inst),
            "by_hand_unweighted_scorza_ansatz": lambda: _attack_unweighted(candidate_inst),
        }
        for name, probe in probes.items():
            start = time.perf_counter(); candidate = probe()
            attack_times[name] += time.perf_counter() - start
            attacks[name]["successes"] += verify(candidate_inst, candidate)[0]
        restart_rng = random.Random(70000 + index)
        candidate_weight = _closed_weight(candidate_inst)
        candidate_expected = (2 * candidate_weight, -6 * candidate_weight)
        start = time.perf_counter()
        solved = any(_fast_candidate_ok(candidate_inst,
                                        random_candidate(candidate_inst, restart_rng),
                                        candidate_expected)
                     for _ in range(256))
        attack_times["random_restart_256"] += time.perf_counter() - start
        attacks["random_restart_256"]["successes"] += solved
    for name in attacks:
        attacks[name]["wall_clock_sec"] = round(attack_times[name], 6)
    report["G6_adversary_panel"] = {
        "pass": (all(result["successes"] == 0 and result["attempts"] >= 8
                     for result in attacks.values())
                 and all(result[0] for result in reference_results)
                 and all(result[0] for result in compact_results)),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact factor-balance enumeration of every mixed index",
            "complexity": "O(n*r) exact/bitwise primitives for r mixer operations",
            "operations": max(result[1] for result in reference_results),
            "wall_clock_sec": round(sum(result[2] for result in reference_results) / 8, 6),
            "wall_clock_sec_total_8": round(sum(result[2] for result in reference_results), 6),
            "solves": f"{sum(result[0] for result in reference_results)}/8, as expected",
        },
        "intended_compact_route": {
            "name": "mixer-bijection invariant and endpoint quotient",
            "operations": max(result[1] for result in compact_results),
            "wall_clock_sec": round(sum(result[2] for result in compact_results) / 8, 6),
            "wall_clock_sec_total_8": round(sum(result[2] for result in compact_results), 6),
            "solves": f"{sum(result[0] for result in compact_results)}/8",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=81, **doubled_params)
    start = time.perf_counter(); doubled_ok = verify(doubled, doubled["answer"])
    doubled_elapsed = time.perf_counter() - start
    report["G7_scales"] = {
        "pass": doubled_ok[0] and search_space(doubled) > search_space(inst),
        "shipping_n": inst["n"], "doubled_n": doubled["n"],
        "shipping_search_space_bits": search_space(inst).bit_length(),
        "doubled_search_space_bits": search_space(doubled).bit_length(),
        "doubled_build_verifies": doubled_ok[0],
        "doubled_verify_reason": doubled_ok[1],
        "doubled_verify_sec": round(doubled_elapsed, 6),
        "escalation_after_shipping": escalate(shipping_params),
    }

    invariant_checks = 0
    real_transform_checks = 0
    key_failures = []
    unrelated_keys = []
    for seed in range(20):
        candidate_inst = make_instance(seed=2000 + seed, **shipping_params)
        base_key = canonical_key(candidate_inst)
        unrelated_keys.append(base_key)
        for salt in (9000 + seed, 19000 + seed):
            transformed = _equivalent_reencoding(candidate_inst, salt)
            invariant_checks += 1
            if canonical_key(transformed) != base_key:
                key_failures.append({"seed": seed, "salt": salt,
                                     "reason": "canonical key changed"})
            real_transform_checks += 1
            if not verify(transformed, candidate_inst["answer"])[0]:
                key_failures.append({"seed": seed, "salt": salt,
                                     "reason": "equivalent re-encoding changed the answer"})
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "real_transformation_checks": real_transform_checks,
        "unrelated_instances": 20, "distinct_unrelated_keys": distinct,
        "transformations": [
            "replacement by another certified index permutation",
            "replacement of cancelling presentation masks",
            "common rescaling of every affine label",
            "all listed transformations composed",
        ],
        "failures": key_failures,
    }

    size_records = []
    for seed in range(20):
        size_answer = make_instance(seed=3000 + seed, **shipping_params)["answer"]
        blob = json.dumps(size_answer, separators=(",", ":"))
        size_records.append((len(blob), (len(blob) + 3) // 4, _answer_atoms(size_answer)))
    answer_chars = max(record[0] for record in size_records)
    answer_tokens = max(record[1] for record in size_records)
    answer_elements = max(record[2] for record in size_records)
    intended_operations = max(result[1] for result in compact_results)
    arms = {name: dict(G9_ORACLE_RESULTS.get(name, {"solved": 0, "attempts": 0}))
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    report["G9_no_tool_suitability"] = {
        "pass": (answer_chars <= 2000 and answer_elements <= 256
                 and intended_operations <= 300),
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS.get("hinted_verdict", "not run"),
        "answer_chars": answer_chars, "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
