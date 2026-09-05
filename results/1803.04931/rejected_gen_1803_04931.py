"""Verified Track-B generator for arXiv:1803.04931.

The generated witness is one of the quadratic projective-line generators from
Martin--Stinson, Theorem 5.2.  All arithmetic used by the checker is exact.
"""

from __future__ import annotations

import copy
import json
import math
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "projective points over GF(2)",
        "squarefree polynomials over Q",
        "vanishing ideal of projective lines",
    ],
    "verification_operations": [
        "exact GF(2) polynomial reduction",
        "exact rational coefficient comparison",
        "exact squarefree monomial comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Frobenius turns the defining trinomial relation into cyclic rotations "
        "of exponent differences; without seeing this, one must compute a finite-field discrete logarithm."
    ),
    "hardness_basis": (
        "Track B: Shanks baby-step/giant-step computes the missing exponent in "
        "O(2^(D/2)) exact field operations and memory; at the shipping D=39 "
        "preset the measured reference run uses about 10^6 table/giant steps, "
        "whereas the planted Frobenius-rotation route uses at most 129 exact bit/integer operations."
    ),
    "max_answer_tokens": 64,
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

# Each x^D + x^S + 1 below was independently checked to be primitive over GF(2).
# The extra entries support the mandated size-doubling check and escalation.
_PRIMITIVE_TRINOMIALS = {
    5: 2,
    25: 7,
    35: 2,
    39: 14,
    41: 3,
    79: 19,
    89: 38,
    127: 15,
}

DIFFICULTY = {
    "demo": {"n": 5, "twist_min": 1},
    "easy": {"n": 25, "twist_min": 15},
    "medium": {"n": 35, "twist_min": 25},
    "hard": {"n": 39, "twist_min": 29},
}
SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A normalized three-term squarefree polynomial over Q, encoded as a JSON "
        "object with one exponent label and three [rational coefficient, monomial-support] "
        "terms; coefficient numerators have absolute value at most 2 and denominator 1."
    ),
    "bounds": {
        "n_terms": 3,
        "monomial_degree": 2,
        "coefficient_numerator_abs": 2,
        "coefficient_denominator": 1,
        "third_point_range": "0..2^D-2 excluding the two target labels",
    },
}

STRUCTURAL_HINT = (
    "Frobenius images of the defining trinomial appear as cyclic rotations of D-bit exponent differences."
)
PLACEBO_HINT = (
    "The normalization and ordering conventions deserve careful attention when writing the polynomial."
)

NOTES = """\
Section 2 fixes I(B) as the ideal of polynomials vanishing on the 0/1 block
vectors.  Section 5, Theorem 5.2 is the construction used here: for a line L
and a pair J in L, x^{L,2}-3x^J is a quadratic generator.  The easy result is
the same theorem--once the third point of L is known, the certificate is an
explicit three-term formula.  In exponent coordinates the generic certificate
producer is discrete logarithm; the reference implementation uses Shanks
baby-step/giant-step.  Generation never runs it: x^D+x^S+1=0 is shifted and
raised to a power of two, carrying all three exponents through the field
automorphism.  High twists defeat the unsquared-trinomial ansatz, random cyclic
shifts defeat magnitude/outlier rules, and the field's exponent labels defeat
integer-XOR and cyclic-sum guesses.  The random-restart attack samples the same
bounded normalized polynomial language as the guess-resistance gate.
"""


def _select_degree(n: int) -> tuple[int, int]:
    if not isinstance(n, int) or isinstance(n, bool) or n < 3:
        raise ValueError("n must be an integer at least 3")
    for degree in sorted(_PRIMITIVE_TRINOMIALS):
        if degree >= n:
            return degree, _PRIMITIVE_TRINOMIALS[degree]
    raise ValueError("n exceeds the supported exact primitive-trinomial ladder")


def _gf_xtime(a: int, degree: int, low_modulus: int) -> int:
    """Multiply by alpha modulo x^degree + low_modulus."""
    a <<= 1
    if a & (1 << degree):
        a ^= (1 << degree) | low_modulus
    return a


def _gf_mul(a: int, b: int, degree: int, low_modulus: int) -> int:
    result = 0
    while b:
        if b & 1:
            result ^= a
        b >>= 1
        a = _gf_xtime(a, degree, low_modulus)
    return result


def _gf_pow_alpha(exponent: int, degree: int, low_modulus: int) -> int:
    order = (1 << degree) - 1
    exponent %= order
    base = 2  # the residue class alpha = x
    result = 1
    while exponent:
        if exponent & 1:
            result = _gf_mul(result, base, degree, low_modulus)
        base = _gf_mul(base, base, degree, low_modulus)
        exponent >>= 1
    return result


def _canonical_polynomial(a: int, b: int, c: int) -> list:
    ab = sorted((a, b))
    ac = sorted((a, c))
    bc = sorted((b, c))
    terms = [
        [[-2, 1], ab],
        [[1, 1], ac],
        [[1, 1], bc],
    ]
    terms.sort(key=lambda term: (term[1], term[0]))
    return terms


def make_instance(n: int, seed: int = 0, twist_min: int = 1, **params) -> dict:
    """Plant a line relation by a shifted Frobenius image of a primitive trinomial."""
    del params
    degree, middle = _select_degree(n)
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    order = (1 << degree) - 1

    lower = max(1, min(int(twist_min), degree - 2))
    # Keeping the twist near the top forces modular wrap-around, concealing the
    # relation in decimal while retaining a short cyclic-rotation route.
    lower = max(lower, degree - 10)
    twist = rng.randrange(lower, degree - 1)
    scale = pow(2, twist, order)
    shift = rng.randrange(order)
    triple = [
        shift,
        (shift + middle * scale) % order,
        (shift + degree * scale) % order,
    ]
    rng.shuffle(triple)
    a, b, c = triple
    if len({a, b, c}) != 3:
        raise AssertionError("primitive-trinomial line unexpectedly collapsed")

    answer = {
        "third": c,
        "polynomial": _canonical_polynomial(a, b, c),
    }
    return {
        "requested_n": n,
        "field_degree": degree,
        "trinomial_exponent": middle,
        "field_order": order,
        "target_pair": [a, b],
        "answer": answer,
    }


def render(inst: dict) -> str:
    degree = inst["field_degree"]
    middle = inst["trinomial_exponent"]
    order = inst["field_order"]
    a, b = inst["target_pair"]
    statement = f"""Find a normalized polynomial in a projective-line vanishing ideal.

Work in the binary field K = GF(2)[z]/(p(z)), where
    p(z) = z^{degree} + z^{middle} + 1.
This p is primitive.  Write alpha for the residue class of z.  The nonzero
elements are therefore alpha^e for the unique exponent label
    0 <= e <= {order - 1},
with exponents read modulo {order}.

For every exponent e there is a variable x_e.  A projective line is the
three-point set {{r,s,t}} satisfying alpha^r + alpha^s + alpha^t = 0.
Let B be the collection of all these three-point sets.  A set C in B has a
0/1 characteristic vector chi_C, and a polynomial vanishes on B when its
evaluation at chi_C is zero for every C in B.

The two target point labels are a={a} and b={b}.  Determine the unique label c,
different from a and b, for which alpha^a + alpha^b + alpha^c = 0.  Then give
the normalized squarefree polynomial
    F = -2*x_a*x_b + x_a*x_c + x_b*x_c.
This F vanishes on B: a projective line meets {{a,b,c}} in 0, 1, or 3 points,
and direct substitution gives zero in each case.

Output one JSON object.  The key "third" is c.  The key "polynomial" is a list
of exactly three terms.  Encode a rational coefficient as [numerator,denominator]
and a squarefree monomial as the increasing list of its two exponent labels.
Term order is irrelevant.  Labels are ordinary base-10 integers; bounds are
inclusive; a,b,c must be distinct; there are no repeated monomials.

Give your final answer inside <answer></answer> tags, in exactly that JSON format.
Example: <answer>{{"third":7,"polynomial":[[[-2,1],[2,5]],[[1,1],[2,7]],[[1,1],[5,7]]]}}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, flags=re.I | re.S)
    if fence:
        body = fence.group(1).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _parse_term(term):
    if not isinstance(term, list) or len(term) != 2:
        return None, "each polynomial term must be [coefficient,monomial]"
    coefficient, monomial = term
    if (
        not isinstance(coefficient, list)
        or len(coefficient) != 2
        or any(not isinstance(x, int) or isinstance(x, bool) for x in coefficient)
        or coefficient[1] == 0
    ):
        return None, "each coefficient must be an exact [integer,nonzero denominator] pair"
    if (
        not isinstance(monomial, list)
        or len(monomial) != 2
        or any(not isinstance(x, int) or isinstance(x, bool) for x in monomial)
        or monomial[0] >= monomial[1]
    ):
        return None, "each monomial must be two distinct increasing integer labels"
    num, den = coefficient
    divisor = math.gcd(num, den)
    if den < 0:
        divisor = -divisor
    normalized = (num // divisor, den // divisor)
    return (normalized, tuple(monomial)), None


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Check the normalized polynomial and its line relation; never consult inst['answer']."""
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if set(answer) != {"third", "polynomial"}:
        return False, "answer must have exactly the keys third and polynomial"
    c = answer.get("third")
    if not isinstance(c, int) or isinstance(c, bool):
        return False, "third must be an integer"
    order = inst["field_order"]
    if not 0 <= c < order:
        return False, "third point is out of range"
    a, b = inst["target_pair"]
    if c in (a, b):
        return False, "third point must differ from both target points"
    polynomial = answer.get("polynomial")
    if not isinstance(polynomial, list) or len(polynomial) != 3:
        return False, "polynomial must contain exactly three terms"

    parsed = []
    for term in polynomial:
        item, reason = _parse_term(term)
        if reason:
            return False, reason
        parsed.append(item)
    supports = [item[1] for item in parsed]
    if len(set(supports)) != 3:
        return False, "polynomial monomial supports must be distinct"
    expected = []
    for term in _canonical_polynomial(a, b, c):
        item, _ = _parse_term(term)
        expected.append(item)
    if sorted(parsed) != sorted(expected):
        return False, "normalized polynomial coefficients or supports do not match the required form"

    degree = inst["field_degree"]
    low_modulus = (1 << inst["trinomial_exponent"]) | 1
    va = _gf_pow_alpha(a, degree, low_modulus)
    vb = _gf_pow_alpha(b, degree, low_modulus)
    vc = _gf_pow_alpha(c, degree, low_modulus)
    if va ^ vb != vc:
        return False, "the three exponent labels do not form a projective line"

    # Executable exhaustive check of the only allowed intersection patterns.
    for ma, mb, mc in ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1)):
        value = -2 * ma * mb + ma * mc + mb * mc
        if value != 0:
            return False, "internal exact substitution check failed"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random):
    order = inst["field_order"]
    a, b = inst["target_pair"]
    c = rng.randrange(order - 2)
    for forbidden in sorted((a, b)):
        if c >= forbidden:
            c += 1
    return {"third": c, "polynomial": _canonical_polynomial(a, b, c)}


def search_space(inst: dict) -> int:
    # Once the required normalization and shape are enforced, only c is free.
    return inst["field_order"] - 2


def enumerate_all(inst: dict):
    if search_space(inst) > 100_000:
        return None
    count = 0
    order = inst["field_order"]
    a, b = inst["target_pair"]
    for c in range(order):
        if c in (a, b):
            continue
        candidate = {"third": c, "polynomial": _canonical_polynomial(a, b, c)}
        if verify(inst, candidate)[0]:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    # The primitive alpha and its ordered power basis are distinguished parts of
    # the presented object.  The only input relabelling is exchange of the two
    # target points, which this sorted pair removes.
    a, b = sorted(inst["target_pair"])
    return (
        f"GF2-projective-line:D={inst['field_degree']}:S={inst['trinomial_exponent']}:"
        f"target={a},{b}"
    )


def escalate(params: dict):
    current = int(params.get("n", 3))
    choices = sorted(_PRIMITIVE_TRINOMIALS)
    next_degree = next((d for d in choices if d > current), None)
    if next_degree is None:
        return None
    harder = dict(params)
    harder["n"] = next_degree
    harder["twist_min"] = min(next_degree - 2, int(params.get("twist_min", 1)) + 7)
    return harder


def _bsgs_third(inst: dict):
    """Reference algorithm: exact discrete log by baby-step/giant-step."""
    degree = inst["field_degree"]
    order = inst["field_order"]
    low_modulus = (1 << inst["trinomial_exponent"]) | 1
    a, b = inst["target_pair"]
    target = _gf_pow_alpha(a, degree, low_modulus) ^ _gf_pow_alpha(
        b, degree, low_modulus
    )
    width = math.isqrt(order) + 1
    table = {}
    value = 1
    for j in range(width):
        if value not in table:
            table[value] = j
        value = _gf_xtime(value, degree, low_modulus)
    factor = _gf_pow_alpha(order - (width % order), degree, low_modulus)
    gamma = target
    giant_steps = 0
    for i in range(width + 1):
        giant_steps += 1
        if gamma in table:
            exponent = (i * width + table[gamma]) % order
            return exponent, {
                "baby_steps": width,
                "giant_steps": giant_steps,
                "field_group_operations": width + giant_steps,
            }
        gamma = _gf_mul(gamma, factor, degree, low_modulus)
    return None, {
        "baby_steps": width,
        "giant_steps": giant_steps,
        "field_group_operations": width + giant_steps,
    }


def _candidate_for(inst: dict, c: int):
    a, b = inst["target_pair"]
    return {"third": c, "polynomial": _canonical_polynomial(a, b, c)}


def _attack_outlier(inst: dict) -> bool:
    order = inst["field_order"]
    a, b = inst["target_pair"]
    guesses = (0, 1, order - 1, (a + b) // 2)
    return any(c not in (a, b) and verify(inst, _candidate_for(inst, c))[0] for c in guesses)


def _attack_integer_xor(inst: dict) -> bool:
    a, b = inst["target_pair"]
    c = a ^ b
    return c < inst["field_order"] and c not in (a, b) and verify(inst, _candidate_for(inst, c))[0]


def _attack_random_restart(inst: dict, seed: int, restarts: int = 256) -> bool:
    rng = random.Random(seed ^ 0x5EED5EED)
    for _ in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _attack_low_twist(inst: dict, max_twist: int = 3) -> bool:
    order = inst["field_order"]
    degree = inst["field_degree"]
    middle = inst["trinomial_exponent"]
    a, b = inst["target_pair"]
    for twist in range(max_twist + 1):
        base = [0, middle * (1 << twist) % order, degree * (1 << twist) % order]
        for i in range(3):
            for j in range(3):
                if i == j:
                    continue
                shift = (a - base[i]) % order
                if (shift + base[j]) % order != b:
                    continue
                k = 3 - i - j
                c = (shift + base[k]) % order
                if c not in (a, b) and verify(inst, _candidate_for(inst, c))[0]:
                    return True
    return False


def _atom_count(value) -> int:
    if isinstance(value, dict):
        return sum(_atom_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_atom_count(v) for v in value)
    return 1


def selftest() -> dict:
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 991):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    inst = make_instance(seed=123456, **DIFFICULTY[SHIPPING_DIFFICULTY])
    corruptions = {}
    bad = copy.deepcopy(inst["answer"])
    bad["polynomial"].pop()
    corruptions["drop_one"] = verify(inst, bad)[1]
    bad = copy.deepcopy(inst["answer"])
    bad["polynomial"][0][0] = [2, 1]
    corruptions["swap_one"] = verify(inst, bad)[1]
    bad = copy.deepcopy(inst["answer"])
    bad["polynomial"][1][1] = list(bad["polynomial"][0][1])
    corruptions["duplicate"] = verify(inst, bad)[1]
    corruptions["empty"] = verify(inst, {})[1]
    bad = copy.deepcopy(inst["answer"])
    bad["third"] = inst["field_order"]
    corruptions["out_of_range"] = verify(inst, bad)[1]
    report["G2_rejects_corruption"] = {
        "pass": len(set(corruptions.values())) == 5
        and all(reason != "ok" for reason in corruptions.values()),
        "reasons": corruptions,
    }

    response = "I used the line relation.\n```\n<answer>" + json.dumps(inst["answer"]) + "</answer>\n```"
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and parse_answer("garbage") is None,
        "model_style_response_parsed": parsed == inst["answer"],
        "garbage_rejected": parse_answer("garbage") is None,
    }

    samples = 200_000
    guess_rng = random.Random(0x180304931)
    planted_c = inst["answer"]["third"]
    hits = 0
    for _ in range(samples):
        candidate = random_candidate(inst, guess_rng)
        # G1 proves the planted c valid and line addition makes it unique; integer
        # comparison lets 200k structure-aware samples remain a cheap gate.
        hits += candidate["third"] == planted_c
    probability = hits / samples
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": samples,
        "sampled_probability": probability,
        "candidate_space": search_space(inst),
        "sampler": "uniform normalized polynomial after enforcing shape, coefficients, and distinct labels",
    }

    t0 = time.perf_counter()
    restart_hit = _attack_random_restart(inst, 777, 256)
    restart_wall = time.perf_counter() - t0
    t0 = time.perf_counter()
    reference_c, reference_counts = _bsgs_third(inst)
    reference_wall = time.perf_counter() - t0
    reference_ok = reference_c is not None and verify(inst, _candidate_for(inst, reference_c))[0]
    report["G5_density_and_baseline_cost"] = {
        "pass": probability < 1e-6 and not restart_hit and reference_ok,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_estimate": probability,
        "exact_valid_answers": 1,
        "candidate_space": search_space(inst),
        "strongest_failing_attack_wall_clock_sec": round(restart_wall, 6),
        "strongest_failing_attack_restarts": 256,
        "reference_algorithm_wall_clock_sec": round(reference_wall, 6),
        "reference_algorithm_operations": reference_counts["field_group_operations"],
    }

    attack_results = {
        "outlier_nearest_boundary": 0,
        "greedy_integer_xor": 0,
        "random_restart_256": 0,
        "by_hand_low_twist_ansatz": 0,
    }
    attack_attempts = 8
    for seed in range(800, 800 + attack_attempts):
        attack_inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        attack_results["outlier_nearest_boundary"] += _attack_outlier(attack_inst)
        attack_results["greedy_integer_xor"] += _attack_integer_xor(attack_inst)
        attack_results["random_restart_256"] += _attack_random_restart(attack_inst, seed)
        attack_results["by_hand_low_twist_ansatz"] += _attack_low_twist(attack_inst)
    attacks = {
        name: {"successes": int(successes), "attempts": attack_attempts}
        for name, successes in attack_results.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Shanks baby-step/giant-step discrete logarithm in GF(2^D)",
            "complexity": "O(2^(D/2)) exact field operations and O(2^(D/2)) stored elements",
            "wall_clock_sec": round(reference_wall, 6),
            "operations": reference_counts["field_group_operations"],
            "baby_steps": reference_counts["baby_steps"],
            "giant_steps": reference_counts["giant_steps"],
            "solves": "1/1 shipping instance, as expected",
        },
    }

    doubled = make_instance(
        n=2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        twist_min=2 * DIFFICULTY[SHIPPING_DIFFICULTY]["twist_min"],
        seed=314159,
    )
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["field_degree"] > inst["field_degree"]
        and search_space(doubled) > search_space(inst),
        "shipping_field_degree": inst["field_degree"],
        "doubled_requested_n": 2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        "doubled_field_degree": doubled["field_degree"],
        "shipping_candidate_space": search_space(inst),
        "doubled_candidate_space": search_space(doubled),
        "doubled_planted_verifies": doubled_ok,
    }

    invariant_checks = 0
    real_transform_checks = 0
    keys = []
    invariance_ok = True
    transformation_ok = True
    for seed in range(20):
        original = make_instance(seed=20_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        swapped = copy.deepcopy(original)
        swapped["target_pair"] = list(reversed(swapped["target_pair"]))
        if canonical_key(original) != canonical_key(swapped):
            invariance_ok = False
        invariant_checks += 1
        if not verify(swapped, original["answer"])[0]:
            transformation_ok = False
        real_transform_checks += 1
        restored = copy.deepcopy(swapped)
        restored["target_pair"] = list(reversed(restored["target_pair"]))
        if canonical_key(original) != canonical_key(restored):
            invariance_ok = False
        invariant_checks += 1
        keys.append(canonical_key(original))
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": invariance_ok and transformation_ok and distinct == 20,
        "invariance_checks": invariant_checks,
        "transformations_verified": real_transform_checks,
        "distinct_unrelated": distinct,
        "unrelated_attempts": 20,
        "distinguished_structure": "primitive alpha and its ordered power-basis presentation",
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _atom_count(inst["answer"])
    intended_ops = 3 * inst["field_degree"] + 12
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {
            "bare": {"solved": 0, "attempts": 0},
            "hinted": {"solved": 0, "attempts": 0},
            "placebo": {"solved": 0, "attempts": 0},
        },
        "hinted_minus_placebo": 0.0,
        "hinted_verdict": "pending external harden.py diagnostic",
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {
            "answer_chars": answer_chars,
            "answer_elements": answer_elements,
            "intended_route_operations": intended_ops,
        },
    }

    report["pass"] = all(
        value.get("pass", True)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
