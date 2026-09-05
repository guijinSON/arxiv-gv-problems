#!/usr/bin/env python3
"""Verified Track-B generator based on arXiv:2505.16105.

The solver receives an explicit affine image of Gerbicz's integer set U(m,L,B)
and must give the exact cardinalities of its sumset and difference set.  The
answer is obtained at construction time from equations (4)--(6), never by
enumerating the pairs.  Verification independently forms both finite sets.
"""

from __future__ import annotations

import functools
import hashlib
import json
import math
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "number_theory",
    "object_regime": "integer_lattice",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite set of integers",
        "bounded nonnegative lattice simplex",
        "carry-free radix encoding",
        "sumset and difference set",
    ],
    "verification_operations": [
        "exact integer addition and subtraction",
        "finite-set insertion",
        "exact cardinality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Read each normalized integer as a bounded radix digit vector, where "
        "addition and subtraction preserve the vector structure; without that "
        "change of variables one must deduplicate quadratically many pairs."
    ),
    "hardness_basis": (
        "Track B: direct hash-set enumeration of A+A and A-A takes O(|A|^2) "
        "integer pair operations; at the hard shipping preset the reference "
        "implementation performs at least 1,000,000 such operations (measured "
        "wall-clock cost is recorded by selftest), while equations (4)--(6) "
        "give a conservatively counted route of at most 300 exact arithmetic "
        "operations once the carry-free digit-vector change of variables is seen."
    ),
    "max_answer_tokens": 6,
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


# n is a lower bound on |A|.  min_route_operations prevents larger rungs from
# accidentally choosing a numerically trivial parameter triple.
DIFFICULTY = {
    "demo": {"n": 8, "min_route_operations": 0},
    "easy": {"n": 80, "min_route_operations": 80},
    "medium": {"n": 300, "min_route_operations": 130},
    "hard": {"n": 1000, "min_route_operations": 180},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "In the normalized radix expansion, addition and subtraction are carry-free "
    "coordinate operations on a bounded lattice simplex."
)
PLACEBO_HINT = (
    "In the displayed integer list, addition and subtraction should be tracked "
    "carefully while duplicate results are counted only once."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "An ordered JSON list [S,D] of exactly two positive integers, where S is "
        "restricted to 2|A|-1 <= S <= |A|(|A|+1)/2 and D is restricted to the "
        "odd integers 2|A|-1 <= D <= |A|(|A|-1)+1."
    ),
    "bounds": {
        "elements": 2,
        "ordered": True,
        "positive_integers": True,
        "sumset_lower_rule": "2*set_size-1",
        "sumset_upper_rule": "set_size*(set_size+1)//2",
        "difference_lower_rule": "2*set_size-1",
        "difference_upper_rule": "set_size*(set_size-1)+1",
        "difference_must_be_odd": True,
    },
}

NOTES = (
    "Section 1 fixes the native question in terms of finite integer sumsets and "
    "difference sets. Section 2, equations (2)--(6), fixes W(m,L,B), the radix "
    "map g, and the exact inclusion--exclusion formulas used here. Equation (7) "
    "and the paragraph before it identify a genuinely easy task (maximizing U) "
    "that this generator avoids. Theorem 2.2 is an explicit construction rather "
    "than a hardness result, so this family is Track B and makes no Track-A "
    "claim. The theorem proof reports a sub-second parameter search at L=64 and "
    "about 15 hours for exact big-integer evaluation at (81411,65536,5): the "
    "certificate-producing method is equations (4)--(6). Here the generic "
    "reference algorithm instead enumerates all integer pairs, while the compact "
    "route recognizes the carry-free lattice encoding. Affine scaling, reflection, "
    "translation, input shuffling, and varied legal radices remove positional and "
    "magnitude planting signatures. The adversary panel tests interval saturation, "
    "arithmetic-progression greediness, an uncapped-simplex ansatz, a Sidon ansatz, "
    "and 256 structure-aware random restarts."
)


# Filled from three isolated harden.py runs.  Until then G9 truthfully fails.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


@functools.lru_cache(maxsize=None)
def _w_size(m, limit, cap):
    """Equation (4), with the paper's degenerate cases made explicit."""
    if m == 0 or limit == 0 or cap == 0:
        return 1
    return sum(
        (-1 if k & 1 else 1)
        * math.comb(m, k)
        * math.comb(m + limit - k * (cap + 1), m)
        for k in range(limit // (cap + 1) + 1)
    )


@functools.lru_cache(maxsize=None)
def _difference_size(m, limit, cap):
    """Equation (6)."""
    return sum(
        math.comb(m, k)
        * _w_size(k, limit - k, cap - 1)
        * _w_size(m - k, limit, cap)
        for k in range(min(m, limit) + 1)
    )


def _comb_operation_count(n, k):
    """Conservative multiply/divide count for the elementary product formula."""
    if k < 0 or k > n:
        return 0
    return 2 * min(k, n - k)


def _w_operation_count(m, limit, cap):
    if m == 0 or limit == 0 or cap == 0:
        return 0
    total = 0
    for k in range(limit // (cap + 1) + 1):
        total += _comb_operation_count(m, k)
        total += _comb_operation_count(m + limit - k * (cap + 1), m)
        total += 2  # multiply the binomials, add/subtract the term
    return total


def _route_operation_count(m, limit, cap):
    total = _w_operation_count(m, 2 * limit, 2 * cap)
    for k in range(min(m, limit) + 1):
        total += _comb_operation_count(m, k)
        total += _w_operation_count(k, limit - k, cap - 1)
        total += _w_operation_count(m - k, limit, cap)
        total += 3  # two products and one addition
    return total


@functools.lru_cache(maxsize=None)
def _parameter_pool(n, min_route_operations):
    """Parameter triples of comparable explicit size and sub-300 compact cost."""
    upper = (3 * n + 1) // 2
    candidates = []
    # These bounds comfortably support the named ladder and several escalations.
    max_m = max(24, min(90, int((6 * max(n, 8)) ** (1 / 3)) * 8 + 8))
    for cap in range(2, 17):
        for m in range(2, max_m + 1):
            max_limit = min(m * cap - 1, 72)
            for limit in range(cap + 1, max_limit + 1):
                size = _w_size(m, limit, cap)
                if size < n or size > upper:
                    continue
                route = _route_operation_count(m, limit, cap)
                if not min_route_operations <= route <= 300:
                    continue
                sum_size = _w_size(m, 2 * limit, 2 * cap)
                difference_size = _difference_size(m, limit, cap)
                if difference_size <= sum_size:
                    continue
                candidates.append((m, limit, cap, size, route))
    return tuple(candidates)


def _encoded_set(m, limit, cap, radix):
    values = []

    def visit(position, remaining, value, place):
        if position == m:
            values.append(value)
            return
        for digit in range(min(cap, remaining) + 1):
            visit(position + 1, remaining - digit, value + digit * place, place * radix)

    visit(0, limit, 0, 1)
    return values


def _validate_parameters(n, min_route_operations):
    return (
        isinstance(n, int)
        and not isinstance(n, bool)
        and 6 <= n <= 200000
        and isinstance(min_route_operations, int)
        and not isinstance(min_route_operations, bool)
        and 0 <= min_route_operations <= 300
    )


def make_instance(n, seed=0, min_route_operations=0, **params):
    """Build a theorem-backed instance and its cardinality certificate."""
    if params or not _validate_parameters(n, min_route_operations):
        raise ValueError("unsupported parameters")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    pool = _parameter_pool(n, min_route_operations)
    if not pool:
        raise ValueError("no paper parameters satisfy this size/route window")
    m, limit, cap, set_size, route_operations = pool[rng.randrange(len(pool))]

    # Every radix >= 2B+1 is injective on both W+W and W-W.  Varying it gives
    # genuinely different integer sets without changing the paper certificate.
    radix = 2 * cap + 1 + rng.randrange(0, 2000)
    raw = _encoded_set(m, limit, cap, radix)
    if len(raw) != set_size:
        raise AssertionError("construction count disagrees with equation (4)")

    scale = rng.randrange(2, 98)
    if rng.randrange(2):
        scale = -scale
    translation = rng.randrange(-100000, 100001)
    values = [scale * value + translation for value in raw]
    rng.shuffle(values)

    answer = [
        _w_size(m, 2 * limit, 2 * cap),
        _difference_size(m, limit, cap),
    ]
    return {
        "n": n,
        "set": values,
        "set_size": set_size,
        "dimension": m,
        "coordinate_sum_limit": limit,
        "coordinate_cap": cap,
        "radix": radix,
        "affine_scale": scale,
        "affine_translation": translation,
        "route_operations": route_operations,
        "answer": answer,
    }


def render(inst):
    values = inst["set"]
    statement = f"""Exact sumset/difference-set cardinalities

For a finite set A of integers, define
  A+A = {{a+b : a is in A and b is in A}},
  A-A = {{a-b : a is in A and b is in A}}.
Repeated results count only once. Order in these sets does not matter.

The explicit input set A below has {inst['set_size']} distinct integers. Its order
is arbitrary. As structural instance data, A is promised to be exactly the affine
image
  A = {{ {inst['affine_scale']} * (x_0 + x_1*r + ... + x_(m-1)*r^(m-1))
         + {inst['affine_translation']} }},
where r={inst['radix']}, m={inst['dimension']}, every x_i is an integer in the
inclusive range 0 through B={inst['coordinate_cap']}, and
  x_0 + x_1 + ... + x_(m-1) <= L={inst['coordinate_sum_limit']}.
The radix satisfies r >= 2B+1. Indices are 0-based; repetitions among the x_i are
allowed. The promise and the explicit list describe the same set.

A = {json.dumps(values, separators=(',', ':'))}

Compute the two exact positive integers S=|A+A| and D=|A-A|. The difference set
always includes 0, and D is therefore odd.

Give your final answer inside <answer></answer> tags, as the JSON list [S,D].
Example: <answer>[22,23]</answer>
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
    match = re.search(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    payload = match.group(1).strip() if match else text.strip()
    payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
    payload = re.sub(r"\s*```$", "", payload)
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError):
        # Tolerate prose around an otherwise unambiguous two-integer JSON list.
        fallback = re.search(r"\[\s*-?\d+\s*,\s*-?\d+\s*\]", payload)
        if not fallback:
            return None
        try:
            answer = json.loads(fallback.group(0))
        except ValueError:
            return None
    return answer


def _instance_values(inst):
    if not isinstance(inst, dict):
        return None
    values = inst.get("set")
    if not isinstance(values, list) or not values:
        return None
    if any(not isinstance(v, int) or isinstance(v, bool) for v in values):
        return None
    if len(set(values)) != len(values) or inst.get("set_size") != len(values):
        return None
    return values


@functools.lru_cache(maxsize=256)
def _normal_form_tuple(values):
    """Canonical under reorder, nonzero integral scaling, translation, reflection."""
    ordered = sorted(values)
    base = ordered[0]
    gaps = [value - base for value in ordered]
    divisor = 0
    for gap in gaps[1:]:
        divisor = math.gcd(divisor, gap)
    if divisor == 0:
        return None
    forward = tuple(gap // divisor for gap in gaps)
    top = forward[-1]
    reflected = tuple(sorted(top - value for value in forward))
    return min(forward, reflected)


def _normal_form(values):
    return _normal_form_tuple(tuple(values))


@functools.lru_cache(maxsize=96)
def _pair_cardinalities(normalized):
    """Reference/checker algorithm: exact quadratic pair enumeration."""
    size = len(normalized)
    sums = set()
    differences = {0}
    for i in range(size):
        left = normalized[i]
        for j in range(i, size):
            sums.add(left + normalized[j])
        for j in range(i + 1, size):
            delta = normalized[j] - left
            differences.add(delta)
            differences.add(-delta)
    return len(sums), len(differences)


def verify(inst, answer):
    values = _instance_values(inst)
    if values is None:
        return False, "malformed instance set"
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) == 0:
        return False, "answer list is empty"
    if len(answer) == 1:
        return False, "answer has only one cardinality"
    if len(answer) > 2:
        return False, "answer has more than two cardinalities"
    if any(not isinstance(v, int) or isinstance(v, bool) for v in answer):
        return False, "both cardinalities must be integers"
    if any(v <= 0 for v in answer):
        return False, "both cardinalities must be positive"

    normalized = _normal_form(values)
    if normalized is None:
        return False, "instance has no nonzero spacing"
    sum_size, difference_size = _pair_cardinalities(normalized)
    if answer[0] != sum_size:
        return False, "sumset cardinality is incorrect"
    if answer[1] != difference_size:
        return False, "difference-set cardinality is incorrect"
    return True, "ok"


def _candidate_ranges(inst):
    size = len(inst["set"])
    sum_low = 2 * size - 1
    sum_high = size * (size + 1) // 2
    difference_low = 2 * size - 1
    difference_high = size * (size - 1) + 1
    return sum_low, sum_high, difference_low, difference_high


def random_candidate(inst, rng):
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    sum_low, sum_high, difference_low, difference_high = _candidate_ranges(inst)
    sum_size = rng.randrange(sum_low, sum_high + 1)
    n_odd = (difference_high - difference_low) // 2 + 1
    difference_size = difference_low + 2 * rng.randrange(n_odd)
    return [sum_size, difference_size]


def search_space(inst):
    sum_low, sum_high, difference_low, difference_high = _candidate_ranges(inst)
    return (sum_high - sum_low + 1) * ((difference_high - difference_low) // 2 + 1)


def enumerate_all(inst):
    # Cardinalities of two explicitly defined finite sets are unique.  This is
    # an exact solution count, not a claim that computing their values is free.
    return 1


def canonical_key(inst):
    values = _instance_values(inst)
    if values is None:
        return "invalid"
    normalized = _normal_form(values)
    if normalized is None:
        return "invalid"
    payload = ",".join(str(value) for value in normalized).encode("ascii")
    return f"sumdiff:{len(normalized)}:" + hashlib.sha256(payload).hexdigest()


def escalate(params):
    if not isinstance(params, dict):
        return None
    n = params.get("n")
    minimum = params.get("min_route_operations", 0)
    if not _validate_parameters(n, minimum):
        return None
    # The named ladder already reaches the 300-operation compact-route cap.
    # Experiments up to |A|=16000 showed that enlarging only the redundant
    # explicit list does not harden the structured calculation; claiming such
    # padding as another mathematical axis would be misleading.
    return None


def _affine_copy(inst, multiplier, shift, reverse_order=False):
    copied = dict(inst)
    values = [multiplier * value + shift for value in inst["set"]]
    if reverse_order:
        values.reverse()
    copied["set"] = values
    copied["affine_scale"] = multiplier * inst["affine_scale"]
    copied["affine_translation"] = multiplier * inst["affine_translation"] + shift
    copied["answer"] = list(inst["answer"])
    return copied


def _attack_answers(inst):
    values = inst["set"]
    size = len(values)
    span = max(values) - min(values)
    m = inst["dimension"]
    limit = inst["coordinate_sum_limit"]

    uncapped_sum = math.comb(m + 2 * limit, m)
    uncapped_difference = sum(
        math.comb(m, k)
        * math.comb(limit, k)
        * math.comb(m - k + limit, m - k)
        for k in range(min(m, limit) + 1)
    )
    return {
        "outlier_range_saturation": [2 * span + 1, 2 * span + 1],
        "greedy_arithmetic_progression": [2 * size - 1, 2 * size - 1],
        "uncapped_simplex_ansatz": [uncapped_sum, uncapped_difference],
        "obvious_sidon_ansatz": [size * (size + 1) // 2, size * (size - 1) + 1],
    }


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest():
    report = {}

    # G1: every named level and three independent seeds.
    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=20250522, **DIFFICULTY[SHIPPING_DIFFICULTY])

    # G2: five shape/value corruptions, each deliberately reaching a distinct check.
    corruptions = {
        "empty": [],
        "drop_one": [shipping["answer"][0]],
        "duplicate_field": shipping["answer"] + [shipping["answer"][1]],
        "swap": list(reversed(shipping["answer"])),
        "out_of_range": [-1, shipping["answer"][1]],
    }
    g2_reasons = {}
    for name, bad in corruptions.items():
        ok, why = verify(shipping, bad)
        g2_reasons[name] = {"rejected": not ok, "reason": why}
    reasons = [item["reason"] for item in g2_reasons.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in g2_reasons.values())
        and len(set(reasons)) == len(reasons),
        "cases": g2_reasons,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: tagged prose, markdown fences, and the exact emitted representation.
    model_reply = (
        "I counted the distinct values exactly.\n\n"
        "<answer>```json\n"
        + json.dumps(shipping["answer"])
        + "\n```</answer>\n"
    )
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"]
        and parse_answer("garbage without a pair") is None,
        "parsed": parsed,
    }

    # G4: structure-aware guesses already obey all universal integer-set bounds.
    guess_rng = random.Random(4162025)
    guess_total = 200000
    guess_hits = 0
    shipping_truth = list(_pair_cardinalities(_normal_form(shipping["set"])))
    for _ in range(guess_total):
        candidate = random_candidate(shipping, guess_rng)
        if candidate == shipping_truth:
            guess_hits += 1
    exact_guess_probability = 1.0 / search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6 and exact_guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "sampled_probability": guess_hits / guess_total,
        "exact_probability": exact_guess_probability,
        "candidate_space": search_space(shipping),
        "prior": "uniform over the structure-aware bounded [S,D] language",
    }

    # G5: exact density and measured strongest mechanical baseline at shipping.
    baseline_inst = make_instance(seed=8675309, **DIFFICULTY[SHIPPING_DIFFICULTY])
    _pair_cardinalities.cache_clear()
    started = time.perf_counter()
    baseline_ok, baseline_why = verify(baseline_inst, baseline_inst["answer"])
    baseline_seconds = time.perf_counter() - started
    baseline_pairs = len(baseline_inst["set"]) ** 2
    report["G5_density_and_baseline"] = {
        "pass": baseline_ok and enumerate_all(baseline_inst) == 1,
        "shipping_solution_count": 1,
        "shipping_candidate_space": search_space(baseline_inst),
        "shipping_solution_density": 1.0 / search_space(baseline_inst),
        "baseline_wall_seconds": baseline_seconds,
        "baseline_pair_operations": baseline_pairs,
        "baseline_set_size": len(baseline_inst["set"]),
        "baseline_reason": baseline_why,
    }

    # G6: construction-aware and in-context attacks; the successful standard
    # pair enumerator is intentionally separate for Track B.
    attack_names = list(_attack_answers(shipping)) + ["random_restart_256"]
    successes = {name: 0 for name in attack_names}
    attempts = {name: 0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_operations = 0
    for seed in range(100, 108):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        _pair_cardinalities.cache_clear()
        start = time.perf_counter()
        ok, _ = verify(inst, inst["answer"])
        reference_seconds += time.perf_counter() - start
        reference_operations += len(inst["set"]) ** 2
        reference_successes += int(ok)
        truth = list(_pair_cardinalities(_normal_form(inst["set"])))
        for name, candidate in _attack_answers(inst).items():
            attempts[name] += 1
            if candidate == truth:
                successes[name] += 1
        attempts["random_restart_256"] += 1
        attack_rng = random.Random(seed ^ 0x5A17)
        if any(random_candidate(inst, attack_rng) == truth for _ in range(256)):
            successes["random_restart_256"] += 1
    attack_report = {
        name: {"successes": successes[name], "attempts": attempts[name]}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 and item["attempts"] >= 8
                    for item in attack_report.values()),
        "attacks": attack_report,
        "reference_algorithm": {
            "name": "exact pair enumeration into hash sets",
            "complexity": "O(|A|^2) exact integer additions/subtractions",
            "wall_clock_sec_8_instances": reference_seconds,
            "operations_8_instances": reference_operations,
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    # G7: all named ground sets grow, and a doubled shipping instance verifies.
    ladder_sizes = []
    for params in DIFFICULTY.values():
        ladder_sizes.append(len(make_instance(seed=4242, **params)["set"]))
    doubled_params = escalate(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled = make_instance(seed=4242, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": all(a < b for a, b in zip(ladder_sizes, ladder_sizes[1:]))
        and doubled_ok
        and len(doubled["set"]) >= 2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        "named_set_sizes": ladder_sizes,
        "doubled_set_size": len(doubled["set"]),
        "doubled_verification": doubled_why,
    }

    # G8: reorder, affine rescale/translate, reflection, and their composition.
    invariant_checks = 0
    transformed_verify_checks = 0
    unrelated_keys = []
    g8_failures = []
    for seed in range(20):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        unrelated_keys.append(key)
        transforms = [
            _affine_copy(inst, 1, 0, reverse_order=True),
            _affine_copy(inst, 3, 17),
            _affine_copy(inst, -5, 29),
            _affine_copy(inst, -7, -41, reverse_order=True),
        ]
        for changed in transforms:
            invariant_checks += 1
            if canonical_key(changed) != key:
                g8_failures.append(f"seed {seed}: key changed")
        if seed == 0:
            for changed in transforms:
                transformed_verify_checks += 1
                ok, why = verify(changed, inst["answer"])
                if not ok:
                    g8_failures.append(f"real-transform check: {why}")
    report["G8_canonical_key"] = {
        "pass": not g8_failures and len(set(unrelated_keys)) == 20,
        "invariance_checks": invariant_checks,
        "transformed_instances_verified": transformed_verify_checks,
        "distinct_unrelated_keys": len(set(unrelated_keys)),
        "unrelated_instances": 20,
        "failures": g8_failures,
    }

    # G9: transcript-derived oracle numbers plus exact local size/effort caps.
    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(shipping["answer"])
    route_operations = shipping["route_operations"]
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else 0.0
    )
    hinted_hardened = (
        G9_ORACLE_RESULTS["hinted_verdict"] == "hardened"
        and arms["hinted"]["attempts"] >= 3
        and arms["hinted"]["solved"] == 0
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and route_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": route_operations,
    }

    report["all_passed"] = all(
        value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
