"""Verified generator for arXiv:0809.3476.

The family asks for the number of inequivalent minimal factorizations of an
n-cycle with one factor of each of several distinct lengths.  The answer is an
exact symbolic product certificate (or, alternatively, the evaluated integer).
Generation uses Theorems 1 and 2 and the classical cycle lemma for rooted plane
trees; it never searches for a factorization.
"""

from __future__ import annotations

import ast
import itertools
import json
import math
import os
import random
import re
import sys
import time
from typing import Any


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # The family only needs Python's exact integers.
    exact_matrices = rationals = None


TRACK = "B"

STRUCTURAL_HINT = (
    "The distinguished root leaf turns each class into a Lukasiewicz "
    "outdegree word with a unique valid cyclic rotation."
)
PLACEBO_HINT = (
    "Careful bookkeeping of every cycle length and convention is useful "
    "for this exact enumeration problem."
)


PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "other",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "cycle-type vector",
        "n-cycle in a symmetric group",
        "equivalence classes of minimal cycle factorizations",
    ],
    "verification_operations": [
        "exact integer product",
        "exact rooted-plane-tree count identity",
        "integer range and order comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Replace a factorization class by the rooted plane tree of Theorem 1 "
        "and encode that tree by its cyclic outdegree word; without this change "
        "of variables one must extract a multivariate recurrence coefficient."
    ),
    "hardness_basis": (
        "Track B: the O(m) cycle-lemma rising-product algorithm exists and its "
        "submitted symbolic form needs 3m=21 small exact operations; direct "
        "coefficient extraction from Theorem 2 by generic Lukasiewicz-prefix DP "
        "costs O(2^m m R) and measured 361,472 additions and 0.1--0.7 seconds "
        "over repeated eight-instance shipping runs, so the task tests "
        "recognition of the compression rather than execution of the recurrence."
    ),
    "max_answer_tokens": 10,
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
    "demo": {"n": 7, "types": 2},
    "easy": {"n": 24, "types": 7},
    "medium": {"n": 40, "types": 9},
    "hard": {"n": 64, "types": 11},
}
SHIPPING_DIFFICULTY = "easy"


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object in one of two bounded forms: {\"value\": V} with "
        "0 <= V < B, or {\"product\": [a1,...,a_(m-1)]} with exactly m-1 "
        "distinct integers 2 <= a1 < ... < a_(m-1) <= U.  B=U^(m-1) and "
        "U are printed in each instance."
    ),
    "bounds": {
        "max_product_factors_shipping": 6,
        "minimum_factor": 2,
        "factor_upper_multiplier_on_rank": 4,
        "strictly_increasing": 1,
        "forms": 2,
    },
}


NOTES = """\
Definition: Section 1 defines type alpha, minimality by
sum (j-1) alpha_j = n-1, and equivalence by swaps of commuting factors.
Theorem 1 identifies inequivalent minimal factorizations with rooted plane
trees whose internal degrees are 2j; its deletion proof also shows that the
obvious factor-ordering search problem has a constructive route, so this is
not a Track A ordering family.  Lemma 1 fixes the orientation convention.
Theorem 2 and Section 4 give the multivariate recurrence used by the reference
dynamic program.  Removing the distinguished root leaf gives internal
outdegrees 2j-1 and 2N-1 ordinary leaves.  The cycle lemma then gives
(2R+m)!/((2R+1)! product alpha_j!).  Our sampled types are distinct, so every
alpha_j is one and the count is the short product (2R+2)...(2R+m).

What makes it easy: Theorems 1 and 2 are constructive, and the standard
rooted-plane-tree enumeration collapses the answer to the displayed short
product once the change of variables is recognized.  This explicitly rules
out Track A.  Track B measures discovery of that compression: the generic
prefix-state dynamic program is exact but mechanical.  The largest/smallest
factor heuristics, independent-slot power, and structure-aware random restart
attacks are checked on eight shipping seeds.  Factor lengths are sampled
uniformly without a planted/decoy distinction.
"""


_G9_ARMS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 1},
}


def _parameters(inst: dict[str, Any]) -> tuple[int, int, int, int, int]:
    lengths = inst.get("factor_lengths")
    if not isinstance(lengths, list) or not lengths:
        raise ValueError("instance has no factor lengths")
    m = len(lengths)
    rank = sum(j - 1 for j in lengths)
    upper = 4 * rank + 2 * m + 17
    k = m - 1
    value_bound = upper**k
    return m, rank, upper, k, value_bound


def _count_from_identity(lengths: list[int]) -> int:
    """Theorem 1 plus the rooted-plane-tree cycle lemma, for alpha_j in {0,1}."""
    rank = sum(j - 1 for j in lengths)
    m = len(lengths)
    result = 1
    for value in range(2 * rank + 2, 2 * rank + m + 1):
        result *= value
    return result


def make_instance(n: int, seed: int = 0, **params: Any) -> dict[str, Any]:
    """Sample a sparse type vector and attach its theorem-backed certificate."""
    types = params.pop("types", None)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if isinstance(types, bool) or not isinstance(types, int) or types < 2:
        raise ValueError("types must be an integer at least 2")
    if types > n - 1:
        raise ValueError("types cannot exceed the number of available lengths")

    rng = random.Random(seed)
    # Every nonzero type coordinate is sampled by the same rule.  Display order
    # is random and has no mathematical significance.
    lengths = rng.sample(range(2, n + 1), types)
    rng.shuffle(lengths)
    rank = sum(j - 1 for j in lengths)
    upper = 4 * rank + 2 * types + 17
    factors = list(range(2 * rank + 2, 2 * rank + types + 1))
    return {
        "size_parameter": n,
        "factor_lengths": lengths,
        "target_cycle_size": rank + 1,
        "factor_upper_bound": upper,
        "value_upper_bound": upper ** (types - 1),
        "answer": {"product": factors},
    }


def render(inst: dict[str, Any]) -> str:
    m, rank, upper, k, value_bound = _parameters(inst)
    lengths = inst["factor_lengths"]
    target_n = rank + 1
    product_intro = (
        "2. {\"product\": [a1]}, containing exactly one integer a1,"
        if k == 1
        else f"2. {{\"product\": [a1,...,a{k}]}}, containing exactly {k} distinct integers,"
    )
    product_bounds = (
        f"   with 2 <= a1 <= {upper},"
        if k == 1
        else f"   satisfying 2 <= a1 < ... < a{k} <= {upper},"
    )
    product_exact = (
        "   and its exact product is H.  Order and distinctness are part of"
        if k == 1
        else "   and their exact product is H.  Order and distinctness are part of"
    )
    example_product = list(range(2, k + 2))
    lines = [
        "Exact count of inequivalent minimal cycle factorizations",
        "",
        f"Work in the symmetric group on the labels 1,...,{target_n}.",
        f"Let C be the cycle (1 2 ... {target_n}).  Permutations are composed",
        "right-to-left: in sigma_m ... sigma_1, sigma_1 acts first.",
        "",
        "A cycle factorization of C is a product sigma_m ... sigma_1 = C.",
        "Its type records how many factors have each cycle length.  It is",
        "minimal when sum over its factors of (cycle_length - 1) equals",
        f"{target_n} - 1.  Two minimal factorizations are equivalent when one",
        "can be obtained from the other by repeatedly swapping adjacent",
        "disjoint cycles; disjoint cycles commute.",
        "",
        f"Here m = {m}.  There must be exactly one factor of each of these",
        "distinct lengths (the displayed order is irrelevant):",
        "  " + " ".join(str(x) for x in lengths),
        f"Their sum of (length-1) values is {rank}, so minimality is exact.",
        "",
        "Find the exact number H of equivalence classes of such minimal",
        "factorizations.  Give one of the following exact certificates as JSON:",
        f"1. {{\"value\": V}}, where V is the integer H and 0 <= V < {value_bound};",
        product_intro,
        product_bounds,
        product_exact,
        "   this canonical product format; repeats are not allowed.",
        "",
        "Give your final answer inside <answer></answer> tags, as one JSON object",
        "in exactly one of the two formats above.",
        "Example format: <answer>"
        + json.dumps({"product": example_product}, separators=(",", ":"))
        + "</answer>",
        "Output nothing else inside the tags.",
    ]
    statement = "\n".join(lines)
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: Any) -> object | None:
    if not isinstance(text, str) or len(text) > 1_000_000:
        return None
    match = re.search(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    if not match:
        return None
    payload = match.group(1).strip()
    if payload.startswith("```") and payload.endswith("```"):
        payload = re.sub(r"^```(?:json|python)?\s*", "", payload, flags=re.I)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        answer = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        try:
            answer = ast.literal_eval(payload)
        except (ValueError, SyntaxError, MemoryError, RecursionError):
            return None
    if not isinstance(answer, dict) or len(answer) != 1:
        return None
    if "value" in answer:
        value = answer["value"]
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        return {"value": value}
    if "product" in answer:
        values = answer["product"]
        if not isinstance(values, (list, tuple)):
            return None
        if any(isinstance(x, bool) or not isinstance(x, int) for x in values):
            return None
        return {"product": list(values)}
    return None


def verify(inst: dict[str, Any], answer: object) -> tuple[bool, str]:
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if not answer:
        return False, "answer object is empty"
    if len(answer) != 1 or not ({"value", "product"} & set(answer)):
        return False, "answer must use exactly one permitted certificate form"

    try:
        m, _rank, upper, k, value_bound = _parameters(inst)
        expected = _count_from_identity(inst["factor_lengths"])
    except (TypeError, ValueError, KeyError):
        return False, "malformed instance"

    if "value" in answer:
        value = answer["value"]
        if isinstance(value, bool) or not isinstance(value, int):
            return False, "value certificate must contain one integer"
        if value < 0 or value >= value_bound:
            return False, "value certificate is outside its permitted range"
        if value != expected:
            return False, "submitted value is not the exact class count"
        return True, "ok"

    values = answer.get("product")
    if not isinstance(values, list):
        return False, "product certificate must contain a JSON list"
    if not values:
        return False, "product factor list is empty"
    if len(values) != k:
        return False, f"product certificate must contain exactly {k} factors"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in values):
        return False, "every product factor must be an integer"
    if len(set(values)) != len(values):
        return False, "product factors must be distinct"
    if values != sorted(values):
        return False, "product factors must be in strictly increasing order"
    if any(x < 2 or x > upper for x in values):
        return False, f"product factor is outside the permitted range [2,{upper}]"
    if math.prod(values) != expected:
        return False, "factor product does not equal the exact class count"
    return True, "ok"


def random_candidate(inst: dict[str, Any], rng: random.Random) -> object:
    """Uniformly sample the union of the two bounded certificate forms."""
    _m, _rank, upper, k, value_bound = _parameters(inst)
    product_space = math.comb(upper - 1, k)
    total = value_bound + product_space
    choice = rng.randrange(total)
    if choice < value_bound:
        return {"value": choice}
    return {"product": sorted(rng.sample(range(2, upper + 1), k))}


def search_space(inst: dict[str, Any]) -> int:
    _m, _rank, upper, k, value_bound = _parameters(inst)
    return value_bound + math.comb(upper - 1, k)


def enumerate_all(inst: dict[str, Any]) -> int | None:
    """Count valid certificate objects exactly when the declared space is tiny."""
    _m, _rank, upper, k, value_bound = _parameters(inst)
    space = search_space(inst)
    if space > 100_000:
        return None
    valid = 0
    for value in range(value_bound):
        valid += int(verify(inst, {"value": value})[0])
    for factors in itertools.combinations(range(2, upper + 1), k):
        valid += int(verify(inst, {"product": list(factors)})[0])
    return valid


def canonical_key(inst: dict[str, Any]) -> str:
    """Canonical under the only input relabelling: reordering type entries."""
    lengths = inst.get("factor_lengths")
    if not isinstance(lengths, list):
        return "invalid"
    return "distinct-cycle-type:" + json.dumps(sorted(lengths), separators=(",", ":"))


def escalate(params: dict[str, Any]) -> dict[str, Any] | str | None:
    """Grow coefficient magnitudes while keeping the product witness length fixed."""
    if not isinstance(params, dict):
        return None
    n = params.get("n")
    types = params.get("types")
    if isinstance(n, bool) or not isinstance(n, int):
        return None
    if isinstance(types, bool) or not isinstance(types, int):
        return None
    # This axis increases the generic DP's rank range and the candidate space,
    # but the compact certificate still contains exactly types-1 integers.
    if n > 10**12:
        return "cap_bound"
    return {"n": max(n + 1, n * 4), "types": types}


def _reference_prefix_dp(inst: dict[str, Any]) -> tuple[int, int]:
    """Generic exact prefix DP for plane-tree outdegree words.

    The distinguished root leaf is removed.  Each internal type j is unique and
    has outdegree 2j-1; all other leaves have outdegree zero.  A state records
    the subset of internal vertices already placed and the number of leaves in
    a preorder prefix.  The final leaf is forced.  `operations` counts exact
    additions into DP states.
    """
    lengths = list(inst["factor_lengths"])
    m = len(lengths)
    increments = [2 * (j - 1) for j in lengths]
    states = 1 << m
    full = states - 1
    capacities = [0] * states
    for mask in range(1, states):
        bit = mask & -mask
        i = bit.bit_length() - 1
        capacities[mask] = capacities[mask ^ bit] + increments[i]

    dp: list[list[int] | None] = [None] * states
    dp[0] = [1]
    operations = 0
    for mask in range(states):
        row = dp[mask]
        if row is None:
            continue
        cap = capacities[mask]
        if len(row) < cap + 1:
            row.extend([0] * (cap + 1 - len(row)))
        for leaves_used in range(cap + 1):
            ways = row[leaves_used]
            if not ways:
                continue
            # A leaf may be placed while at least two open child slots remain.
            # When one remains, either an internal node follows or, at full mask,
            # the omitted final leaf is forced.
            if leaves_used < cap:
                row[leaves_used + 1] += ways
                operations += 1
            remaining = full ^ mask
            while remaining:
                bit = remaining & -remaining
                new_mask = mask | bit
                target = dp[new_mask]
                if target is None:
                    target = [0] * (capacities[new_mask] + 1)
                    dp[new_mask] = target
                target[leaves_used] += ways
                operations += 1
                remaining ^= bit
    final_row = dp[full]
    if final_row is None:
        return 0, operations
    return final_row[capacities[full]], operations


def _attack_candidates(inst: dict[str, Any], seed: int) -> dict[str, object]:
    lengths = sorted(inst["factor_lengths"])
    m, rank, upper, k, _bound = _parameters(inst)
    return {
        "outlier_largest_lengths": {"product": lengths[-k:]},
        "greedy_smallest_factors": {"product": list(range(2, k + 2))},
        "independent_open_slots": {"value": (2 * rank + 1) ** k},
        "shifted_rising_product": {
            "product": list(range(2 * rank + 1, 2 * rank + m))
        },
    }


def _atomic_elements(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atomic_elements(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atomic_elements(v) for v in value)
    return 1


def selftest() -> dict[str, Any]:
    report: dict[str, Any] = {
        "paper": "0809.3476",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: construction and JSON nativeness over the whole ladder.
    g1_checks = 0
    g1_failures: list[str] = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 65537):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {why}")
            try:
                if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                    g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
            except (TypeError, ValueError) as exc:
                g1_failures.append(f"{preset}/{seed}: JSON error {exc}")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=20260905, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = list(shipping["answer"]["product"])
    upper = shipping["factor_upper_bound"]
    corruptions = {
        "empty": {},
        "drop_one": {"product": planted[:-1]},
        "swap_two": {"product": [planted[1], planted[0], *planted[2:]]},
        "duplicate": {"product": [planted[0], planted[0], *planted[2:]]},
        "out_of_range": {"product": [*planted[:-1], upper + 1]},
        "wrong_product": {"product": [*planted[:-1], planted[-1] + 1]},
    }
    corruption_results: dict[str, dict[str, Any]] = {}
    reasons: list[str] = []
    for name, candidate in corruptions.items():
        ok, why = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": why}
        reasons.append(why)
    report["G2_rejects_corruption"] = {
        "pass": all(x["rejected"] for x in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "I used the rooted-tree encoding.\n```json\n<answer>"
        + json.dumps(shipping["answer"])
        + "</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    roundtrip_ok = parsed == shipping["answer"] and verify(shipping, parsed)[0]
    report["G3_round_trip"] = {
        "pass": roundtrip_ok and parse_answer("garbage") is None,
        "realistic_response_parsed": parsed is not None,
        "equals_planted": parsed == shipping["answer"],
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4/G5 share the same shipping-preset, structure-aware sample.
    guess_rng = random.Random(0x8093476)
    sample_total = 200_000
    sample_hits = 0
    for _ in range(sample_total):
        sample_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    empirical = sample_hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": empirical < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "empirical_probability": empirical,
        "candidate_space": search_space(shipping),
        "prior": "uniform over the union of both fully constrained certificate forms",
    }

    # Run the Track-B reference algorithm and all in-context attacks on 8 seeds.
    attack_names = list(_attack_candidates(shipping, 0)) + ["random_restart_256"]
    attack_stats = {name: {"successes": 0, "attempts": 0} for name in attack_names}
    ref_successes = 0
    ref_operations = 0
    ref_elapsed = 0.0
    ref_instances: list[dict[str, Any]] = []
    for seed in range(8100, 8108):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, candidate in _attack_candidates(inst, seed).items():
            attack_stats[name]["attempts"] += 1
            attack_stats[name]["successes"] += int(verify(inst, candidate)[0])

        rr_rng = random.Random(seed ^ 0xA55A5AA5)
        rr_solved = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, rr_rng))[0]:
                rr_solved = True
                break
        attack_stats["random_restart_256"]["attempts"] += 1
        attack_stats["random_restart_256"]["successes"] += int(rr_solved)

        start = time.perf_counter()
        count, operations = _reference_prefix_dp(inst)
        elapsed = time.perf_counter() - start
        ref_ok = verify(inst, {"value": count})[0]
        ref_successes += int(ref_ok)
        ref_operations += operations
        ref_elapsed += elapsed
        ref_instances.append(
            {
                "seed": seed,
                "rank": sum(x - 1 for x in inst["factor_lengths"]),
                "operations": operations,
                "wall_clock_sec": round(elapsed, 6),
                "solved": ref_ok,
            }
        )

    all_attacks_failed = all(v["successes"] == 0 for v in attack_stats.values())
    reference = {
        "name": "generic Lukasiewicz-prefix dynamic programming",
        "complexity": "O(2^m * m * R) exact additions; O(2^m * R) memory",
        "wall_clock_sec": round(ref_elapsed, 6),
        "mean_wall_clock_sec": round(ref_elapsed / 8, 6),
        "operations": ref_operations,
        "mean_operations": ref_operations // 8,
        "solves": f"{ref_successes}/8, as expected",
        "instances": ref_instances,
    }
    report["G5_density_and_baseline"] = {
        "pass": sample_total >= 200_000 and ref_successes == 8,
        "shipping_sampled_solution_hits": sample_hits,
        "shipping_sampled_solution_total": sample_total,
        "shipping_sampled_solution_fraction": empirical,
        "strongest_attack_wall_sec": round(ref_elapsed, 6),
        "strongest_attack_operations": ref_operations,
        "strongest_attack_solved_instances": ref_successes,
        "demo_exact_valid_certificate_count": enumerate_all(
            make_instance(seed=0, **DIFFICULTY["demo"])
        ),
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed,
        "attacks": attack_stats,
        "reference_algorithm": reference,
    }

    # G7: double the size parameter without lengthening the product witness.
    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    doubled_params = {
        "n": shipping_params["n"] * 2,
        "types": shipping_params["types"],
    }
    doubled = make_instance(seed=314159, **doubled_params)
    base = make_instance(seed=314159, **shipping_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok
        and search_space(doubled) > search_space(base)
        and len(doubled["answer"]["product"]) == len(base["answer"]["product"]),
        "base_n": shipping_params["n"],
        "doubled_n": doubled_params["n"],
        "base_space": search_space(base),
        "doubled_space": search_space(doubled),
        "base_answer_elements": len(base["answer"]["product"]),
        "doubled_answer_elements": len(doubled["answer"]["product"]),
    }

    invariant_checks = 0
    carried_checks = 0
    keys: set[str] = set()
    g8_ok = True
    for seed in range(20):
        inst = make_instance(
            seed=90000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY]
        )
        key = canonical_key(inst)
        keys.add(key)
        variants = []
        for values in (
            list(reversed(inst["factor_lengths"])),
            inst["factor_lengths"][3:] + inst["factor_lengths"][:3],
        ):
            variant = dict(inst)
            variant["factor_lengths"] = list(values)
            variants.append(variant)
        composed = dict(inst)
        composed["factor_lengths"] = list(
            reversed(variants[1]["factor_lengths"][2:] + variants[1]["factor_lengths"][:2])
        )
        variants.append(composed)
        for variant in variants:
            invariant_checks += 1
            g8_ok = g8_ok and canonical_key(variant) == key
            carried_checks += 1
            g8_ok = g8_ok and verify(variant, inst["answer"])[0]
    report["G8_canonical_key"] = {
        "pass": g8_ok and len(keys) == 20,
        "invariance_checks": invariant_checks,
        "carried_certificate_checks": carried_checks,
        "unrelated_distinct_keys": len(keys),
        "unrelated_instances": 20,
        "symmetries_tested": ["input reversal", "cyclic input reorder", "composition"],
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_elements = _atomic_elements(shipping["answer"])
    answer_tokens = math.ceil(answer_chars / 4)
    intended_ops = 3 * len(shipping["factor_lengths"])
    hinted = _G9_ARMS["hinted"]
    placebo = _G9_ARMS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = (
        placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    )
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000
        and answer_elements <= 256
        and intended_ops <= 300,
        "arms": _G9_ARMS,
        "diagnostic_complete": all(
            arm["attempts"] >= 3 for arm in _G9_ARMS.values()
        ),
        "diagnostic_note": (
            "The placebo arm has one scored attempt; four subsequent HTTP 403 "
            "records show that the OpenRouter key reached its total quota."
        ),
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": (
            "hardened" if hinted["attempts"] and hinted["solved"] == 0 else "diagnostic_pending"
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gate_values = [
        value
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict) and "pass" in value
    ]
    report["all_passed"] = all(value["pass"] for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
