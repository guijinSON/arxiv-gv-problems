"""Verified problem generator for arXiv:1001.3573.

The paper studies rational points on the genus-two curves

    C_k: Y^2 = X^6 + k.

Section 5 records a parametric identity which supplies integer points when
``k = a^12/4 + 1``.  This module samples the point first and constructs the
curve from that identity.  The point is never recovered by solving the curve.
"""

from __future__ import annotations

import copy
import functools
import hashlib
import json
import math
import os
import random
import re
import statistics
import time


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "The two neighboring-square gaps around k conceal an exact sixth-power relation."
)
PLACEBO_HINT: str = (
    "The two signed coordinates in the answer require exact integer arithmetic throughout."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "number_theory",
    "object_regime": "integer_lattice",
    "computational_core": "polynomial_identity",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "genus-two curve C_k: Y^2 = X^6 + k over Q",
        "bounded integral point on C_k",
    ],
    "verification_operations": [
        "exact integer exponentiation",
        "exact integer addition",
        "exact equality comparison",
        "inclusive integer-bound comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "A neighboring-square gap turns the sextic equation into an exact sixth "
        "root; without noticing it, a solver must search the stated height range."
    ),
    "hardness_basis": (
        "Track B: congruence-sieved bounded-height enumeration is O(n M(log k)); "
        "at the shipping n=30000000 it visits tens of millions of X values (the measured "
        "median is reported by selftest), whereas the Section 5 neighboring-square "
        "identity needs fewer than 300 exact arithmetic operations."
    ),
    "max_answer_tokens": 15,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {"hard": {"n": 100_000_000}}
SHIPPING_DIFFICULTY: str = "hard"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON list [X,Y] of two nonzero signed decimal integers.  The instance "
        "requires 1 <= |X| <= n and 1 <= |Y| <= Y_max.  A structure-aware random "
        "candidate chooses one of the 4n sign-and-|X| choices and sets |Y| to "
        "floor(sqrt(k+X^6)); the equation itself decides validity."
    ),
    "bounds": {
        "coordinates": 2,
        "x_absolute_min": 1,
        "x_absolute_max": "instance n",
        "y_absolute_max": "instance Y_max",
        "sign_choices": 4,
    },
}

NOTES: str = (
    "Section 1 fixes the native problem as finite rational points on the genus-two "
    "curve C_k, with the two points at infinity excluded. Section 2 rewrites a "
    "rational point X=x/y, Y=z/y^3 as x^6+k y^6=z^2 and uses exact factorization "
    "and congruences. Section 2.1 identifies the easy zero-rank cases; Section 3 "
    "uses elliptic Chabauty for further small k, so this is not a Track A claim. "
    "Near the end of Section 5 the paper displays k=a^12/4+1 and the point "
    "(a,1+a^6/2); that polynomial identity is the construction and compact route. "
    "The outlier attack tests height landmarks, the greedy attack searches near the "
    "unscaled twelfth-root estimate, the random attack samples the exact declared "
    "candidate prior, and the by-hand ansatz tries simple rational rescalings of "
    "that estimate. None receives the shifted neighboring-square invariant. The "
    "successful reference algorithm is disclosed: a congruence-sieved exhaustive "
    "integer-height scan, not an alleged hardness result for these curves."
)


# Filled from the three isolated harden.py runs after the bare family is fixed.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "pending",
}


def _choose_parameter(n: int, rng: random.Random) -> int:
    """Choose an even, non-round a well inside the stated X interval."""
    lo = max(2, (58 * n + 99) // 100)
    hi = max(lo, (92 * n) // 100)
    even_lo = (lo + 1) // 2
    even_hi = hi // 2
    if even_lo > even_hi:
        raise ValueError("n leaves no even construction parameter")
    choices = even_hi - even_lo + 1
    for _ in range(256):
        a = 2 * (even_lo + rng.randrange(choices))
        # Avoid decimal round numbers and the obvious displayed landmarks.  This
        # only chooses the already-known witness; it never solves a generated curve.
        if a % 10 and all(
            abs(a - t) > min(32, max(1, n // 1000))
            for t in (n // 2, 3 * n // 4, n)
        ):
            return a
    # Small demo ranges may have only one possible even value.
    return 2 * (even_lo + rng.randrange(choices))


def make_instance(n, seed=0, **params) -> dict:
    """Construct C_k from a point sampled first via the Section 5 identity."""
    del params
    if isinstance(n, bool) or not isinstance(n, int) or n < 6:
        raise ValueError("n must be an integer at least 6")
    rng = random.Random(seed)
    a = _choose_parameter(n, rng)
    a6 = a**6
    k = a6 * a6 // 4 + 1
    y = a6 // 2 + 1
    y_max = math.isqrt(k + n**6) + 1
    answer = [a, y]
    # This assertion is the composition-of-identities certificate construction.
    assert y * y == a**6 + k
    return {
        "family": "bounded integral point on Y^2 = X^6 + k",
        "n": n,
        "k": k,
        "x_min_abs": 1,
        "x_max_abs": n,
        "y_min_abs": 1,
        "y_max_abs": y_max,
        "answer": answer,
    }


def render(inst) -> str:
    """Render a self-contained exact Diophantine problem."""
    statement = f"""Find one finite integral point on the curve

    Y^2 = X^6 + k

where

    k = {inst['k']}

An integral point means an ordered pair (X,Y) of ordinary decimal integers
satisfying the equation exactly.  Both signs are allowed and order matters.
Zero is forbidden.  The inclusive bounds are

    1 <= |X| <= {inst['x_max_abs']}
    1 <= |Y| <= {inst['y_max_abs']}

All powers and comparisons are over the integers; no rounding or approximate
equality is accepted.

Give your final answer inside <answer></answer> tags as a JSON list [X,Y].
Example: <answer>[3, 28]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse the delimited JSON pair, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\s*>(.*?)</answer\s*>", text, re.I | re.S)
    if match is None:
        return None
    payload = match.group(1).strip()
    fence = re.fullmatch(r"```(?:json|text)?\s*(.*?)\s*```", payload, re.I | re.S)
    if fence is not None:
        payload = fence.group(1).strip()
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        # A modest fallback for models that omit the JSON brackets.
        plain = re.fullmatch(r"\s*([+-]?\d+)\s*,\s*([+-]?\d+)\s*", payload)
        if plain is None:
            return None
        value = [int(plain.group(1)), int(plain.group(2))]
    if not isinstance(value, list):
        return None
    return value


def verify(inst, answer):
    """Check any bounded integral point; never consult the planted answer."""
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list) or len(answer) != 2:
        return False, "answer must contain exactly two coordinates"
    x, y = answer
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (x, y)):
        return False, "both coordinates must be decimal integers"
    if x == y:
        return False, "the two coordinates cannot be equal within these bounds"
    if not (inst["x_min_abs"] <= abs(x) <= inst["x_max_abs"]):
        return False, "X magnitude is outside the inclusive bound"
    if not (inst["y_min_abs"] <= abs(y) <= inst["y_max_abs"]):
        return False, "Y magnitude is outside the inclusive bound"
    if y * y != x**6 + inst["k"]:
        return False, "the exact equation Y^2 = X^6 + k is not satisfied"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample the structure-aware finite language described above."""
    x = rng.randint(inst["x_min_abs"], inst["x_max_abs"])
    y = math.isqrt(inst["k"] + x**6)
    if rng.getrandbits(1):
        x = -x
    if rng.getrandbits(1):
        y = -y
    return [x, y]


def search_space(inst):
    """There are two independent signs for each permitted |X|."""
    return 4 * (inst["x_max_abs"] - inst["x_min_abs"] + 1)


_SIEVE_MODULUS = 64 * 63 * 65  # 262080; coprime square filters combined.


@functools.lru_cache(maxsize=128)
def _residue_mask(k_mod: int) -> bytes:
    modulus = _SIEVE_MODULUS
    squares = {r * r % modulus for r in range(modulus)}
    mask = bytearray(modulus)
    for r in range(modulus):
        mask[r] = (pow(r, 6, modulus) + k_mod) % modulus in squares
    return bytes(mask)


def _height_enumeration(inst, stop_at_first=True):
    """Congruence-sieved bounded-height enumeration, with operation counters."""
    modulus = _SIEVE_MODULUS
    allowed = _residue_mask(inst["k"] % modulus)
    solutions = []
    visited = 0
    square_tests = 0
    for x in range(inst["x_min_abs"], inst["x_max_abs"] + 1):
        visited += 1
        if not allowed[x % modulus]:
            continue
        square_tests += 1
        value = inst["k"] + x**6
        y = math.isqrt(value)
        if y * y == value:
            solutions.append([x, y])
            if stop_at_first:
                break
    return solutions, visited, square_tests


def enumerate_all(inst):
    """Count signed solutions exactly when the stated height range is manageable."""
    if inst["x_max_abs"] > 12_000_000:
        return None
    solutions, _, _ = _height_enumeration(inst, stop_at_first=False)
    # X -> -X and Y -> -Y independently preserve the curve; X,Y are nonzero.
    return 4 * len(solutions)


def canonical_key(inst):
    """Canonical data have no labels; coordinate-sign symmetries change no field."""
    canonical = {
        "k": inst["k"],
        "x_abs": [inst["x_min_abs"], inst["x_max_abs"]],
        "y_abs": [inst["y_min_abs"], inst["y_max_abs"]],
    }
    blob = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params):
    """Double the height haystack while retaining a two-integer witness."""
    # G9 scratch copy: measure the shipping rung only.
    return None


def _integer_nth_root(value: int, exponent: int) -> int:
    if value < 0 or exponent < 1:
        raise ValueError("root arguments out of range")
    if value < 2:
        return value
    lo, hi = 0, 1 << ((value.bit_length() + exponent - 1) // exponent)
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if mid**exponent <= value:
            lo = mid
        else:
            hi = mid
    return lo


def _pow_with_count(base: int, exponent: int):
    result = 1
    factor = base
    count = 0
    e = exponent
    while e:
        if e & 1:
            result *= factor
            count += 1
        e >>= 1
        if e:
            factor *= factor
            count += 1
    return result, count


def _nth_root_with_count(value: int, exponent: int):
    lo, hi = 0, 1 << ((value.bit_length() + exponent - 1) // exponent)
    operations = 1
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        power, multiplications = _pow_with_count(mid, exponent)
        operations += 3 + multiplications  # add/divide, compare, power multiplies
        if power <= value:
            lo = mid
        else:
            hi = mid
    return lo, operations


def _isqrt_with_count(value: int):
    if value < 2:
        return value, 1
    x = 1 << ((value.bit_length() + 1) // 2)
    operations = 1
    while True:
        y = (x + value // x) // 2
        operations += 3
        if y >= x:
            return x, operations + 1
        x = y


def _compact_solver(inst):
    """The Section 5 route, expressed through neighboring-square gaps."""
    b, operations = _isqrt_with_count(inst["k"])
    y = b + 1
    sixth = y * y - inst["k"]
    operations += 3
    x, root_ops = _nth_root_with_count(sixth, 6)
    operations += root_ops
    x6, mults = _pow_with_count(x, 6)
    operations += mults + 3
    if x6 != sixth:
        return None, operations
    answer = [x, y]
    if not verify(inst, answer)[0]:
        return None, operations
    return answer, operations


def _try_abs_x_values(inst, values):
    for x in values:
        if not isinstance(x, int) or not (1 <= x <= inst["x_max_abs"]):
            continue
        y = math.isqrt(inst["k"] + x**6)
        if verify(inst, [x, y])[0]:
            return [x, y]
    return None


def _attack_outlier_landmarks(inst):
    n = inst["x_max_abs"]
    values = {1, 2, n // 4, n // 2, 3 * n // 4, n - 1, n}
    power = 1
    while power <= n:
        values.add(power)
        power *= 10
    return _try_abs_x_values(inst, values)


def _attack_greedy_unscaled_root(inst):
    root = _integer_nth_root(inst["k"], 12)
    values = []
    for center in (root, inst["x_max_abs"] // 2, 3 * inst["x_max_abs"] // 4):
        values.extend(range(max(1, center - 512), min(inst["x_max_abs"], center + 512) + 1))
    return _try_abs_x_values(inst, values)


def _attack_simple_scale_ansatz(inst):
    root = _integer_nth_root(inst["k"], 12)
    ratios = ((1, 1), (9, 8), (8, 7), (10, 9), (7, 6), (6, 5))
    values = set()
    for numerator, denominator in ratios:
        value = (root * numerator + denominator // 2) // denominator
        values.update((value - 1, value, value + 1))
    return _try_abs_x_values(inst, values)


def _attack_random_restart(inst, seed, restarts=4096):
    rng = random.Random(seed)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _sign_transform(inst, sx, sy):
    moved = copy.deepcopy(inst)
    x, y = moved["answer"]
    moved["answer"] = [sx * abs(x), sy * abs(y)]
    return moved


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest():
    report = {}

    # G1: every named preset, multiple seeds, exact verification and JSON safety.
    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **shipping_params)

    # G2: five corruptions reach five distinct validation branches.
    x, y = inst["answer"]
    corruptions = {
        "drop": [x],
        "swap": [y, x],
        "duplicate": [x, x],
        "empty": [],
        "out_of_range": [x, inst["y_max_abs"] + 1],
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: surrounding prose and a Markdown-fenced payload both survive parsing.
    response = (
        "The exact substitution checks out.\n\n<answer>\n```json\n"
        + json.dumps(inst["answer"])
        + "\n```\n</answer>\nThat is my final point."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"],
        "parsed": parsed,
    }

    # G4: sample the exact structure-aware prior used by search_space().
    sample_total = 200_000
    sample_rng = random.Random(0x10013573)
    sample_hits = 0
    sample_start = time.perf_counter()
    for _ in range(sample_total):
        if verify(inst, random_candidate(inst, sample_rng))[0]:
            sample_hits += 1
    sample_seconds = time.perf_counter() - sample_start
    sample_probability = sample_hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": sample_probability < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "observed_probability": sample_probability,
        "candidate_space": search_space(inst),
        "prior": "uniform |X| and independent signs, with |Y|=floor(sqrt(k+X^6))",
    }

    # G6 and G5 baseline: four failing in-context attacks and the successful
    # Track B reference enumeration, all on eight independent shipping instances.
    attack_names = (
        "outlier_height_landmarks",
        "greedy_unscaled_root_window",
        "random_restart_4096",
        "by_hand_small_rational_scale_ansatz",
    )
    attack_successes = {name: 0 for name in attack_names}
    reference_successes = 0
    reference_times = []
    reference_visited = []
    reference_square_tests = []
    compact_successes = 0
    compact_operations = []
    attack_seeds = list(range(800, 808))
    for seed in attack_seeds:
        attack_inst = make_instance(seed=seed, **shipping_params)
        attack_successes["outlier_height_landmarks"] += int(
            _attack_outlier_landmarks(attack_inst) is not None
        )
        attack_successes["greedy_unscaled_root_window"] += int(
            _attack_greedy_unscaled_root(attack_inst) is not None
        )
        attack_successes["random_restart_4096"] += int(
            _attack_random_restart(attack_inst, seed ^ 0xA551) is not None
        )
        attack_successes["by_hand_small_rational_scale_ansatz"] += int(
            _attack_simple_scale_ansatz(attack_inst) is not None
        )

        t0 = time.perf_counter()
        answers, visited, square_tests = _height_enumeration(attack_inst, True)
        elapsed = time.perf_counter() - t0
        solved = bool(answers) and verify(attack_inst, answers[0])[0]
        reference_successes += int(solved)
        reference_times.append(elapsed)
        reference_visited.append(visited)
        reference_square_tests.append(square_tests)

        compact, operations = _compact_solver(attack_inst)
        compact_successes += int(compact is not None and verify(attack_inst, compact)[0])
        compact_operations.append(operations)

    attacks = {
        name: {"successes": attack_successes[name], "attempts": len(attack_seeds)}
        for name in attack_names
    }
    median_wall = statistics.median(reference_times)
    median_visited = int(statistics.median(reference_visited))
    median_square_tests = int(statistics.median(reference_square_tests))
    max_compact_operations = max(compact_operations)
    panel_pass = all(result["successes"] == 0 for result in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": panel_pass
        and reference_successes == len(attack_seeds)
        and compact_successes == len(attack_seeds),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "congruence-sieved bounded integral-height enumeration",
            "complexity": "O(n M(log k)) exact bit operations up to multiplication factors",
            "wall_clock_sec_median": median_wall,
            "operations_median_x_values_visited": median_visited,
            "median_exact_square_tests_after_sieve": median_square_tests,
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
        "compact_route": {
            "name": "neighboring-square gap followed by an exact sixth root",
            "max_exact_arithmetic_operations": max_compact_operations,
            "solves": f"{compact_successes}/{len(attack_seeds)}, as expected",
        },
    }

    exact_solution_count = enumerate_all(inst)
    exact_density = (
        exact_solution_count / search_space(inst)
        if exact_solution_count is not None
        else None
    )
    report["G5_density_and_baseline_cost"] = {
        "pass": sample_probability < 1e-6
        and reference_successes == len(attack_seeds),
        "shipping_exact_valid_answers": exact_solution_count,
        "shipping_candidate_count": search_space(inst),
        "shipping_exact_solution_density": exact_density,
        "shipping_sample_hits": sample_hits,
        "shipping_sample_total": sample_total,
        "shipping_sample_density": sample_probability,
        "shipping_sampling_wall_seconds": sample_seconds,
        "baseline_wall_seconds_median": median_wall,
        "baseline_x_values_visited_median": median_visited,
        "baseline_exact_square_tests_median": median_square_tests,
    }

    # G7: the named ladder and a doubled shipping instance both preserve G1.
    named_n = [params["n"] for params in DIFFICULTY.values()]
    doubled_params = {"n": 2 * shipping_params["n"]}
    t0 = time.perf_counter()
    doubled = make_instance(seed=31337, **doubled_params)
    doubled_build_seconds = time.perf_counter() - t0
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": all(a < b for a, b in zip(named_n, named_n[1:])) and doubled_ok,
        "named_n": named_n,
        "doubled_n": doubled_params["n"],
        "doubled_build_seconds": doubled_build_seconds,
        "doubled_verify_reason": doubled_reason,
        "answer_atomic_elements_unchanged": _answer_atoms(doubled["answer"]) == 2,
    }

    # G8: the curve's two independent sign involutions and their composition.
    invariance_checks = 0
    carried_checks = 0
    g8_failures = []
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(seed=10_000 + seed, **shipping_params)
        key = canonical_key(base)
        unrelated_keys.append(key)
        for sx, sy in ((-1, 1), (1, -1), (-1, -1)):
            moved = _sign_transform(base, sx, sy)
            invariance_checks += 1
            if canonical_key(moved) != key:
                g8_failures.append(f"seed {seed}, signs {sx},{sy}: key changed")
            ok, why = verify(moved, moved["answer"])
            carried_checks += 1
            if not ok:
                g8_failures.append(f"seed {seed}, signs {sx},{sy}: {why}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_distinct": distinct_keys,
        "unrelated_attempts": 20,
        "failures": g8_failures,
        "method": "hash of k and absolute-coordinate bounds; X/Y sign involutions removed",
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    arms = copy.deepcopy(G9_RESULTS["arms"])
    hinted_verdict = G9_RESULTS["hinted_verdict"]
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and max_compact_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": hinted_verdict == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": hinted_verdict,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": max_compact_operations,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping_params)
    report["all_passed"] = all(
        entry.get("pass") is True
        for key, entry in report.items()
        if key.startswith("G") and isinstance(entry, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
