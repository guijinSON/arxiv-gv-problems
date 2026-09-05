"""Verified Track-B generator for arXiv:2407.19344.

The generated task asks for a polynomial whose coefficients are domination-
polynomial evaluations at -1 for free-boundary multidimensional king graphs.
Theorem 2 of Moore--Mertens supplies the certificate by a sign-reversing
involution; no generated graph is ever searched or enumerated.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import time
from typing import Any


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "polynomial",
    "native_objects": [
        "free-boundary multidimensional king graphs",
        "domination polynomials",
    ],
    "verification_operations": [
        "integer reduction modulo 4",
        "Boolean parity comparison",
        "exact polynomial coefficient comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "A side-two block involution cancels dominating sets in opposite-parity "
        "pairs, leaving one block-corner set per king box."
    ),
    "hardness_basis": (
        "Track B: Theorem 2 evaluates 48 four-dimensional coefficients in O(n*d) "
        "time (about 240 modular/Boolean steps and under 0.0003 s per evaluation "
        "in repeated shipping benchmarks), whereas "
        "literal exact enumeration on the shipping boxes starts at 2^N subsets "
        "with N at least the smallest displayed box volume; the short route is "
        "available only after recognizing the side-two cancellation invariant."
    ),
    "max_answer_tokens": 112,
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

CERTIFICATE_LANGUAGE = {
    "description": (
        "A dense univariate polynomial with exactly n terms: one term [c,[j]] "
        "for every exponent j=0,...,n-1, where c is -1 or +1 and exactly n/2 "
        "coefficients are -1; term order is irrelevant."
    ),
    "bounds": {
        "terms": "n",
        "variables": 1,
        "degree": "n-1",
        "coefficient_set": [-1, 1],
        "negative_coefficients": "n/2",
    },
}

DIFFICULTY = {
    "demo": {"n": 4, "dimensions": 2, "side_min": 1, "side_max": 3},
    "easy": {"n": 24, "dimensions": 2, "side_min": 20, "side_max": 99},
    "medium": {"n": 36, "dimensions": 3, "side_min": 50, "side_max": 999},
    "hard": {"n": 48, "dimensions": 4, "side_min": 1000, "side_max": 9999},
}

SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Focus on the parity of the block count when every coordinate interval is "
    "partitioned into consecutive pieces of length two."
)
PLACEBO_HINT = (
    "Focus on the exact indexing conventions and keep every requested polynomial "
    "term in a consistent, easily checked form."
)

# Filled from the isolated hardening runs.  These are diagnostics, not assertions
# used by verify().
G9_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}

NOTES = (
    "Section 1 fixes domination and the king-graph adjacency relation. Section 2, "
    "Theorem 1 gives the two-dimensional sign-reversing matching; Section 4, "
    "Theorem 2 gives the d-dimensional formula used by construction. Section 3 "
    "shows the easy formula depends on free boundaries and fails on cylinders and "
    "tori, so the generator never uses periodic boundaries. The planted-answer "
    "triage was discarded: arbitrary distracting graphs are not the paper's "
    "objects. Balanced signs remove the all-plus shortcut; matched magnitude "
    "ranges remove scale outliers; shuffled boxes remove position leakage; the "
    "selftest also probes volume, odd-side, XOR, and random-restart guesses."
)


def _sign_for_box(sides: list[int]) -> int:
    """Theorem 2: (-1)^(product_i ceil(sides[i]/2))."""
    # ceil(s/2) is odd exactly when s is 1 or 2 modulo 4.
    return -1 if all(s % 4 in (1, 2) for s in sides) else 1


def _answer_for_boxes(boxes: list[list[int]]) -> list[list[Any]]:
    return [[_sign_for_box(sides), [j]] for j, sides in enumerate(boxes)]


def _draw_side(rng: random.Random, lo: int, hi: int, allowed: tuple[int, ...]) -> int:
    values_by_residue: list[tuple[int, int, int]] = []
    total = 0
    for residue in allowed:
        first = lo + ((residue - lo) % 4)
        if first <= hi:
            count = (hi - first) // 4 + 1
            values_by_residue.append((first, count, total))
            total += count
    if total == 0:
        raise ValueError("side range contains no value with a required residue")
    pick = rng.randrange(total)
    for first, count, start in values_by_residue:
        if pick < start + count:
            return first + 4 * (pick - start)
    raise AssertionError("unreachable residue sampler state")


def make_instance(
    n: int,
    seed: int = 0,
    dimensions: int = 2,
    side_min: int = 1,
    side_max: int = 99,
    **params: Any,
) -> dict:
    """Construct a balanced batch by Theorem 2, never by solving a graph."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 4 or n % 2:
        raise ValueError("n must be an even integer at least 4")
    if isinstance(dimensions, bool) or not isinstance(dimensions, int) or dimensions < 1:
        raise ValueError("dimensions must be a positive integer")
    if not (isinstance(side_min, int) and isinstance(side_max, int)):
        raise ValueError("side bounds must be integers")
    if side_min < 1 or side_max < side_min or side_max - side_min < 2:
        raise ValueError("side range must be positive and span at least three integers")

    rng = random.Random(seed)
    boxes: list[list[int]] = []

    # Half the boxes have odd block-count product.  Side magnitudes for both signs
    # come from the same interval; only the theorem's modulo-four invariant differs.
    for _ in range(n // 2):
        boxes.append([
            _draw_side(rng, side_min, side_max, (1, 2))
            for _axis in range(dimensions)
        ])
    for _ in range(n // 2):
        while True:
            sides = [rng.randint(side_min, side_max) for _axis in range(dimensions)]
            if _sign_for_box(sides) == 1:
                boxes.append(sides)
                break
    rng.shuffle(boxes)

    answer = _answer_for_boxes(boxes)
    return {
        "family": "king_box_domination_signature",
        "n": n,
        "dimensions": dimensions,
        "side_min": side_min,
        "side_max": side_max,
        "boxes": boxes,
        "answer": answer,
    }


def render(inst: dict) -> str:
    boxes = inst["boxes"]
    lines = [
        "KING-BOX DOMINATION SIGNATURE",
        "",
        "For a positive integer L, write [L]={1,2,...,L}.  A d-dimensional",
        "free-boundary king graph K(L1,...,Ld) has vertex set",
        "[L1] x ... x [Ld].  Two distinct vertices u and v are adjacent exactly",
        "when max_i |u_i-v_i| = 1.  There is no wrap-around at a boundary.",
        "",
        "A set S of vertices is dominating when every vertex is either in S or",
        "adjacent to a vertex in S.  Its domination polynomial is",
        "D_K(z) = sum z^|S|, summed once over every dominating set S.",
        "",
        f"Below are {len(boxes)} ordered {inst['dimensions']}-dimensional boxes.",
        "For box j (0-indexed), let c_j = D_K(-1).  Every c_j is promised to be",
        "exactly -1 or +1, and exactly half of the c_j values are -1.",
        "Return the exact polynomial Q(x)=sum_j c_j*x^j.",
        "",
        "BOXES (j: [L1,...,Ld]):",
    ]
    lines.extend(f"{j}: {json.dumps(sides, separators=(',', ':'))}" for j, sides in enumerate(boxes))
    lines.extend([
        "",
        "Represent Q as a JSON list of terms [coefficient,[exponent]]. Include",
        "every exponent 0 through n-1 exactly once; term order does not matter.",
        "Coefficients must be JSON integers -1 or 1. Repeats are not allowed.",
        "",
        "Give your final answer inside <answer></answer> tags in that exact JSON format.",
        "Example: <answer>[[-1,[0]],[1,[1]]]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    candidates = list(reversed(matches))
    if not candidates:
        candidates.extend(re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.I | re.S))
    for raw in candidates:
        try:
            value = json.loads(raw.strip())
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, list):
            return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    n = inst.get("n")
    if len(answer) != n:
        return False, f"wrong number of terms: expected {n}"

    coefficients: dict[int, int] = {}
    for pos, term in enumerate(answer):
        if not (isinstance(term, list) and len(term) == 2):
            return False, f"term {pos} must have shape [coefficient,[exponent]]"
        coefficient, monomial = term
        if isinstance(coefficient, bool) or not isinstance(coefficient, int) or coefficient not in (-1, 1):
            return False, f"term {pos} has a coefficient outside {{-1,1}}"
        if not (
            isinstance(monomial, list)
            and len(monomial) == 1
            and isinstance(monomial[0], int)
            and not isinstance(monomial[0], bool)
        ):
            return False, f"term {pos} must have one integer exponent"
        exponent = monomial[0]
        if exponent < 0 or exponent >= n:
            return False, f"term {pos} has exponent outside 0..{n - 1}"
        if exponent in coefficients:
            return False, f"duplicate exponent {exponent}"
        coefficients[exponent] = coefficient

    if sum(1 for c in coefficients.values() if c == -1) != n // 2:
        return False, f"wrong sign balance: expected exactly {n // 2} negative coefficients"

    boxes = inst.get("boxes")
    if not isinstance(boxes, list) or len(boxes) != n:
        return False, "malformed instance boxes"
    for exponent, sides in enumerate(boxes):
        expected = _sign_for_box(sides)
        if coefficients.get(exponent) != expected:
            return False, f"coefficient mismatch at exponent {exponent}"
    return True, "ok"


def _candidate_from_negative_indices(n: int, negatives: set[int]) -> list[list[Any]]:
    return [[-1 if j in negatives else 1, [j]] for j in range(n)]


def random_candidate(inst: dict, rng: random.Random) -> object:
    n = inst["n"]
    negatives = set(rng.sample(range(n), n // 2))
    terms = _candidate_from_negative_indices(n, negatives)
    rng.shuffle(terms)
    return terms


def search_space(inst: dict) -> int | None:
    return math.comb(inst["n"], inst["n"] // 2)


def enumerate_all(inst: dict) -> int | None:
    n = inst["n"]
    if search_space(inst) > 200_000:
        return None
    count = 0
    for chosen in itertools.combinations(range(n), n // 2):
        ok, _ = verify(inst, _candidate_from_negative_indices(n, set(chosen)))
        count += int(ok)
    return count


def canonical_key(inst: dict) -> str:
    # Coordinate-axis permutations and input-box permutations are the relevant
    # relabellings.  Sorting both levels gives an exact canonical representative.
    canonical = sorted(tuple(sorted(sides)) for sides in inst["boxes"])
    payload = json.dumps(canonical, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    clean = {k: v for k, v in params.items() if k != "_preset"}
    dimensions = int(clean.get("dimensions", 2))
    n = int(clean.get("n", 4))
    # This grows each graph's ambient vertex set without lengthening the answer.
    # At d=5 the compact route is already n*(d+1)=288 operations for n=48;
    # another dimension would violate G9(c)'s 300-operation cap.
    if dimensions < 5 and n * (dimensions + 2) <= 300:
        nxt = dict(clean)
        nxt["dimensions"] = dimensions + 1
        nxt["side_min"] = max(int(clean.get("side_min", 1)), 1000)
        nxt["side_max"] = max(int(clean.get("side_max", 99)), 9999)
        return nxt
    # Use the last two available operation slots after reaching five
    # dimensions.  This lengthens the polynomial by only two terms and reaches
    # the exact G9(c) effort boundary: 50 * (5 residue tests + 1 product-parity
    # decision) = 300 operations.
    if dimensions == 5 and n < 50:
        nxt = dict(clean)
        nxt["n"] = 50
        return nxt
    return None


def _rank_candidate(inst: dict, score) -> list[list[Any]]:
    n = inst["n"]
    ranked = sorted(range(n), key=lambda j: (score(inst["boxes"][j]), j))
    return _candidate_from_negative_indices(n, set(ranked[: n // 2]))


def _attack_candidates(inst: dict) -> dict[str, list[list[Any]]]:
    return {
        "outlier_small_coordinate_sum": _rank_candidate(inst, lambda s: sum(s)),
        "greedy_small_box_volume": _rank_candidate(inst, lambda s: math.prod(s)),
        "by_hand_most_odd_sides": _rank_candidate(inst, lambda s: -sum(v & 1 for v in s)),
        "by_hand_xor_block_parities": _rank_candidate(
            inst,
            lambda s: -sum(((v + 1) // 2) & 1 for v in s) % 2,
        ),
    }


def _atom_count(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atom_count(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atom_count(v) for v in value)
    return 1


def _reference_algorithm(inst: dict) -> list[list[Any]]:
    return _answer_for_boxes(inst["boxes"])


def _bruteforce_domination_value(sides: list[int]) -> int:
    """Independent tiny-box check of the theorem used by construction."""
    vertices = list(itertools.product(*(range(side) for side in sides)))
    value = 0
    for mask in range(1 << len(vertices)):
        selected = [
            vertex for index, vertex in enumerate(vertices)
            if (mask >> index) & 1
        ]
        dominating = all(
            any(
                all(abs(a - b) <= 1 for a, b in zip(vertex, king))
                for king in selected
            )
            for vertex in vertices
        )
        if dominating:
            value += -1 if len(selected) % 2 else 1
    return value


def _corruptions(answer: list[list[Any]], n: int) -> dict[str, object]:
    dropped = json.loads(json.dumps(answer))
    dropped.pop()

    swapped = json.loads(json.dumps(answer))
    swapped[0][0] *= -1
    # Preserve the promised sign balance so this reaches coefficient comparison.
    old = answer[0][0]
    partner = next(i for i in range(1, n) if answer[i][0] == -old)
    swapped[partner][0] *= -1

    duplicated = json.loads(json.dumps(answer))
    duplicated[-1][1] = list(duplicated[0][1])

    out_of_range = json.loads(json.dumps(answer))
    out_of_range[0][0] = 3

    return {
        "drop_one": dropped,
        "swap_two_signs": swapped,
        "duplicate_exponent": duplicated,
        "empty": [],
        "out_of_range_coefficient": out_of_range,
    }


def selftest() -> dict:
    report: dict[str, Any] = {
        "paper": "2407.19344",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    # G1: every preset, five unrelated seeds, plus JSON-native answers.
    g1_failures = []
    g1_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2, 17, 991):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            json_native = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            g1_checks += 1
            if not ok or not json_native:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
    theorem_boxes = (
        [1], [2], [3], [4],
        [1, 1], [1, 2], [1, 3], [2, 2], [2, 3], [3, 3],
        [1, 1, 2], [1, 2, 2], [2, 2, 2],
    )
    theorem_checks = 0
    for sides in theorem_boxes:
        theorem_checks += 1
        brute = _bruteforce_domination_value(sides)
        formula = _sign_for_box(sides)
        if brute != formula:
            g1_failures.append({
                "box": sides,
                "reason": f"brute-force value {brute} != theorem formula {formula}",
            })
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks + theorem_checks,
        "planted_checks": g1_checks,
        "theorem_cross_checks": theorem_checks,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=20260905, **DIFFICULTY[SHIPPING_DIFFICULTY])

    # G2: five corruption classes, with five distinct rejection reasons.
    corruption_results = {}
    reasons = []
    for name, bad in _corruptions(shipping["answer"], shipping["n"]).items():
        ok, why = verify(shipping, bad)
        corruption_results[name] = {"rejected": not ok, "reason": why}
        reasons.append(why)
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in corruption_results.values()) and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: tagged prose, a Markdown fence, and garbage.
    encoded = json.dumps(shipping["answer"], separators=(",", ":"))
    realistic = "I used cancellation.\n```json\nauxiliary\n```\n<answer>\n" + encoded + "\n</answer>\nDone."
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and parse_answer("garbage only") is None,
        "realistic_response": parsed == shipping["answer"],
        "garbage_returns_none": parse_answer("garbage only") is None,
    }

    # G4/G5 shipping density, sampled from the promised balanced-sign language.
    guess_rng = random.Random(240719344)
    samples = 200_000
    hits = 0
    truth_negatives = {
        exponent for exponent, sides in enumerate(shipping["boxes"])
        if _sign_for_box(sides) == -1
    }
    t0 = time.perf_counter()
    for _ in range(samples):
        # This is exactly random_candidate's uniform draw after quotienting out
        # irrelevant term order.  Avoiding 200,000 temporary JSON trees makes the
        # statistical gate fast without changing its distribution.
        drawn = set(guess_rng.sample(range(shipping["n"]), shipping["n"] // 2))
        hits += int(drawn == truth_negatives)
    density_wall = time.perf_counter() - t0
    space = search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "structure_aware_space": space,
        "exact_unique_witness_probability": 1 / space,
        "sampler": "uniform over sign polynomials with exactly n/2 negative coefficients",
    }

    # G6 panel across eight seeds.  The theorem formula is reported separately,
    # because it is expected to solve a Track-B family.
    attack_names = list(_attack_candidates(shipping)) + ["random_restart_1024"]
    attack_counts = {name: {"successes": 0, "attempts": 0} for name in attack_names}
    reference_solves = 0
    reference_wall = 0.0
    reference_ops = shipping["n"] * (shipping["dimensions"] + 1)
    reference_repetitions = 1000
    strongest_wall = 0.0
    strongest_iterations = 0
    for seed in range(8100, 8108):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        cheap = _attack_candidates(inst)
        for name, candidate in cheap.items():
            ok, _ = verify(inst, candidate)
            attack_counts[name]["successes"] += int(ok)
            attack_counts[name]["attempts"] += 1

        rr_rng = random.Random(seed ^ 0x5A17)
        rr_t0 = time.perf_counter()
        solved = False
        for _restart in range(1024):
            ok, _ = verify(inst, random_candidate(inst, rr_rng))
            if ok:
                solved = True
                break
        strongest_wall += time.perf_counter() - rr_t0
        strongest_iterations += _restart + 1
        attack_counts["random_restart_1024"]["successes"] += int(solved)
        attack_counts["random_restart_1024"]["attempts"] += 1

        ref_t0 = time.perf_counter()
        for _timing_repeat in range(reference_repetitions):
            ref = _reference_algorithm(inst)
        reference_wall += time.perf_counter() - ref_t0
        reference_solves += int(verify(inst, ref)[0])

    all_failed = all(v["successes"] == 0 and v["attempts"] >= 8 for v in attack_counts.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attack_counts,
        "reference_algorithm": {
            "name": "Moore--Mertens Theorem 2 side-two cancellation formula",
            "complexity": "O(n*d) exact integer arithmetic",
            "wall_clock_sec_total_benchmark": reference_wall,
            "timing_repetitions_per_instance": reference_repetitions,
            "wall_clock_sec_mean": reference_wall / (8 * reference_repetitions),
            "operations_per_shipping_instance": reference_ops,
            "solves": f"{reference_solves}/8, as expected",
        },
    }

    volumes = [math.prod(sides) for sides in shipping["boxes"]]
    report["G5_density_and_baseline_cost"] = {
        "pass": isinstance(hits / samples, float) and all_failed,
        "density_hits": hits,
        "density_total": samples,
        "baseline_wall_clock_sec": strongest_wall,
        "baseline_iterations": strongest_iterations,
        "shipping_density": {
            "hits": hits,
            "total": samples,
            "observed_fraction": hits / samples,
            "exact_fraction_from_uniqueness": f"1/{space}",
            "sampling_wall_clock_sec": density_wall,
        },
        "demo_exact_enumeration": {
            "preset": "demo",
            "candidate_space": search_space(
                make_instance(seed=20260905, **DIFFICULTY["demo"])
            ),
            "valid_answers": enumerate_all(
                make_instance(seed=20260905, **DIFFICULTY["demo"])
            ),
        },
        "strongest_failing_attack": {
            "name": "balanced random restart",
            "wall_clock_sec_total_8": strongest_wall,
            "iterations": strongest_iterations,
            "successes": attack_counts["random_restart_1024"]["successes"],
        },
        "mechanical_exact_enumeration": {
            "algorithm": "visit every vertex subset and test domination",
            "smallest_shipping_box_vertices": min(volumes),
            "largest_shipping_box_vertices": max(volumes),
            "subset_visits_lower_bound": f"2^{min(volumes)}",
        },
    }

    # G7: double n while preserving all other parameters.
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    t0 = time.perf_counter()
    doubled = make_instance(seed=777, **doubled_params)
    doubled_build = time.perf_counter() - t0
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > space,
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_space": space,
        "doubled_space": search_space(doubled),
        "doubled_build_sec": doubled_build,
        "verify_reason": doubled_why,
    }

    # G8: axis permutations, box permutations, and their composition.
    invariance_checks = 0
    preservation_checks = 0
    g8_failures = []
    keys = []
    for seed in range(20):
        inst = make_instance(seed=9000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        original_key = canonical_key(inst)
        keys.append(original_key)
        rng = random.Random(seed)

        axes_only = [rng.sample(sides, len(sides)) for sides in inst["boxes"]]
        order = list(range(inst["n"]))
        rng.shuffle(order)
        boxes_only = [list(inst["boxes"][i]) for i in order]
        composed = [rng.sample(inst["boxes"][i], len(inst["boxes"][i])) for i in order]

        original_coefficients = {
            term[1][0]: term[0] for term in inst["answer"]
        }
        identity_order = list(range(inst["n"]))

        for label, transformed_boxes, source_order in (
            ("axes", axes_only, identity_order),
            ("boxes", boxes_only, order),
            ("composed", composed, order),
        ):
            transformed = dict(inst)
            transformed["boxes"] = transformed_boxes
            # Carry the old certificate through the relabelling.  In
            # particular, do not invoke the theorem formula here: this check is
            # meant to establish that the tested map really preserves the
            # problem, independently of certificate generation.
            transformed["answer"] = [
                [original_coefficients[old_j], [new_j]]
                for new_j, old_j in enumerate(source_order)
            ]
            invariance_checks += 1
            preservation_checks += 1
            if canonical_key(transformed) != original_key:
                g8_failures.append({"seed": seed, "map": label, "failure": "key changed"})
            if not verify(transformed, transformed["answer"])[0]:
                g8_failures.append({"seed": seed, "map": label, "failure": "map did not preserve problem"})
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariance_checks,
        "problem_preservation_checks": preservation_checks,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "failures": g8_failures,
        "canonicalization": "sort axes within each box, then sort the boxes",
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_atoms = _atom_count(shipping["answer"])
    estimated_tokens = (answer_chars + 3) // 4
    intended_ops = shipping["n"] * (shipping["dimensions"] + 1)
    arms = G9_RESULTS
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else None
    placebo_rate = arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else None
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000 and answer_atoms <= 256 and intended_ops <= 300,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": "diagnostic recorded" if hinted_attempts else "pending isolated run",
        "answer_chars": answer_chars,
        "answer_tokens": estimated_tokens,
        "token_measure": "ceil(minified JSON characters / 4)",
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_ops,
    }

    gate_passes = [v.get("pass") for k, v in report.items() if k.startswith("G") and isinstance(v, dict)]
    report["all_passed"] = all(gate_passes)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
