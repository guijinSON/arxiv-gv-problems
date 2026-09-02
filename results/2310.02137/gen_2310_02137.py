"""Verified generators for prime-coordinate homogeneous quadratic equations.

The mathematical object is the one defined in Section 1 of arXiv:2310.02137:
an integral homogeneous form and a non-diagonal vector of positive primes on
its zero locus.  This module makes the witness domain finite and explicit so
that answers can be graded and the structured search space can be measured.

Only the Python standard library is used.  Importing this module has no side
effects.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re
import time
from typing import Any


# Dict insertion order is the hardening ladder order.
DIFFICULTY = {
    "easy": {"n": 60, "weight_bits": 60},
    "medium": {"n": 72, "weight_bits": 72},
    "hard": {"n": 84, "weight_bits": 84},
}

# Updated, if necessary, after scripts/harden.py identifies the first level
# that holds against its oracle pool.
SHIPPING_DIFFICULTY = "easy"


NOTES = r"""
Paper connection and parameter choice
-------------------------------------
Section 1 defines V_{d,n} as primitive integral homogeneous degree-d forms in
n+1 variables, and V(P) as their non-diagonal prime-coordinate points.  This
generator uses d=2 and m variables, hence the paper's parameter is n=m-1.
Every preset has m >= 60, safely inside Theorem 1.2's n >= d regime and away
from its exceptional (2,2) and (3,3) pairs.  Theorem 1.1 says the prime-local
density is zero in the (2,2) case, which is why that small regime is avoided.
The definition of Xi' immediately before equation (1.2) also confirms that
diagonal prime vectors are expressly excluded.

The paper is an average existence/counting result, not a search algorithm or
a computational-hardness result.  Section 3 gives sieve upper bounds for
prime vectors in lattices; it does not recover a point on an input form.  The
Introduction discusses local-global results for linear equations and for
quadratic forms with many variables, but again these establish existence, not
an efficient bounded-domain search procedure.  To make H independently
checkable, the finite restriction used here contains EQUIPARTITION: for
weights a_i of total zero and x_i in {p,q}, sum_i a_i x_i equals
(q-p) times the sum of weights at the q-positions.  Requiring exactly half of
the positions therefore asks for an equal-cardinality zero-sum subset.
EQUIPARTITION reduces to this by mapping positive inputs w_i of total 2T to
a_i = m*w_i - 2T.  Multiplication by the positive homogeneous factor sum x_i
makes the displayed equation a degree-2 homogeneous form without changing
its roots in the allowed domain.

Generation and attack hardening
-------------------------------
The answer (a uniformly random half-set) is sampled first.  Its weights and
the complement's weights are then independently sampled by the identical
bounded zero-sum routine, shuffled within each block, and rejected only under
global symmetric conditions (zero, duplicate, or opposite weights).  Thus
plant and decoy coordinates have the same one-coordinate distribution.  The
weight range has about n bits: the structured answer space is exponential,
while accidental zero sums remain sparse, without entering the classic
very-low-density subset-sum regime caused by vastly oversized weights.

The adversary panel tests both tails of the per-coordinate magnitude ranking,
a cancellation greedy rule, and balanced random restarts with best-improving
one-for-one swaps.  None is used in generation or verification.  The
canonical key removes coefficient gcd and global sign, then sorts the weights;
this is exactly invariant under variable renumbering for this factored family.
"""


_LOW_PRIME = 1_000_000_007
_HIGH_PRIME = 1_000_000_009
_TAG_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL)
_INT_LIST_RE = re.compile(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*")
_ENUMERATION_CAP = 100_000


def _is_prime(value: int) -> bool:
    """Deterministic Miller-Rabin for unsigned 64-bit integers."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value % prime == 0:
            return value == prime
    d = value - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    # This base set is deterministic for n < 2**64.
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        x = pow(base, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = (x * x) % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _sample_zero_sum_block(size: int, limit: int, rng: random.Random) -> list[int]:
    """Uniform ordered bounded nonzero tuple conditional on sum zero.

    Sampling size-1 entries and accepting the forced final entry gives every
    feasible ordered tuple the same probability.  The final shuffle makes the
    construction visibly exchangeable, including in finite samples.
    """
    while True:
        values = []
        while len(values) < size - 1:
            value = rng.randint(-limit, limit)
            if value:
                values.append(value)
        final = -sum(values)
        if final == 0 or abs(final) > limit:
            continue
        values.append(final)
        if len(set(values)) != size:
            continue
        rng.shuffle(values)
        return values


def _normalise_weights(weights: list[int]) -> list[int]:
    divisor = 0
    for value in weights:
        divisor = math.gcd(divisor, abs(value))
    if divisor > 1:
        weights = [value // divisor for value in weights]
    first = next((value for value in weights if value), 0)
    if first < 0:
        weights = [-value for value in weights]
    return weights


def make_instance(n: int, seed: int = 0, weight_bits: int | None = None,
                  **params: Any) -> dict:
    """Sample a balanced prime witness first, then build a form around it.

    ``n`` is the number of variables (not the paper's projective-dimension
    parameter, which is n-1 here).  It must be even.  The answer is the sorted
    list of 1-based positions assigned the larger prime.
    """
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if not isinstance(n, int) or isinstance(n, bool) or n < 6 or n % 2:
        raise ValueError("n must be an even integer at least 6")
    if weight_bits is None:
        weight_bits = n
    if (not isinstance(weight_bits, int) or isinstance(weight_bits, bool)
            or weight_bits < 8):
        raise ValueError("weight_bits must be an integer at least 8")

    rng = random.Random(seed)
    half = n // 2

    # G: the witness is the very first random object drawn.
    planted_zero_based = set(rng.sample(range(n), half))
    limit = (1 << (weight_bits - 1)) - 1

    while True:
        planted_weights = _sample_zero_sum_block(half, limit, rng)
        decoy_weights = _sample_zero_sum_block(half, limit, rng)
        weights = [0] * n
        p_at = d_at = 0
        for index in range(n):
            if index in planted_zero_based:
                weights[index] = planted_weights[p_at]
                p_at += 1
            else:
                weights[index] = decoy_weights[d_at]
                d_at += 1

        # Symmetric rejection removes trivial zero/pair attacks and makes the
        # membership-swap corruption in selftest deterministically non-solving.
        if len(set(weights)) != n:
            continue
        value_set = set(weights)
        if any(-value in value_set for value in weights):
            continue
        break

    weights = _normalise_weights(weights)
    answer = sorted(index + 1 for index in planted_zero_based)
    return {
        "family": "balanced_prime_quadratic_zero_sum",
        "degree": 2,
        "variables": n,
        "paper_n": n - 1,
        "low_prime": _LOW_PRIME,
        "high_prime": _HIGH_PRIME,
        "high_count": half,
        "weights": weights,
        "weight_bits": weight_bits,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a complete, standalone problem statement."""
    n = int(inst["variables"])
    k = int(inst["high_count"])
    low = int(inst["low_prime"])
    high = int(inst["high_prime"])
    weights = list(inst["weights"])
    weight_lines = "\n".join(
        f"  {index}: {value}" for index, value in enumerate(weights, 1)
    )
    example = ", ".join(str(index) for index in range(1, k + 1))
    return f"""BALANCED PRIME-COORDINATE QUADRATIC EQUATION

There are {n} ordered variables x_1,...,x_{n}.  Each variable must be one of
the two primes p={low} and q={high}.  Exactly {k} variables must equal q; all
other variables must equal p.  Thus repeats of prime values are required, but
an index can be chosen only once.  Indices are 1-based and run from 1 through
{n}, inclusive.

For the integer weights a_i below, define

  A(x) = sum from i=1 to {n} of a_i*x_i,
  S(x) = sum from i=1 to {n} of x_i,
  F(x) = A(x)*S(x).

This is a homogeneous polynomial of degree 2.  Equivalently, the coefficient
of x_i^2 is a_i and the coefficient of x_i*x_j for i<j is a_i+a_j.  All
arithmetic is exact integer arithmetic.  Find a permitted, non-diagonal prime
tuple for which F(x)=0.  (The exact-{k} rule already makes it non-diagonal.)

Weights, in `index: a_i` format:
{weight_lines}

Output the {k} distinct indices whose variables equal q.  Their order in the
answer does not matter; every unlisted index is assigned p.

Give your final answer inside <answer></answer> tags, as {k} comma-separated
base-10 integers.  Example of format only:
<answer>{example}</answer>
Output nothing else inside the tags."""


def parse_answer(text: str) -> object | None:
    """Extract the last well-formed tagged comma-separated integer list."""
    if not isinstance(text, str):
        return None
    matches = _TAG_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    # Also tolerate a model putting a Markdown fence inside the tags.
    if body.startswith("```") and body.endswith("```"):
        lines = body.splitlines()
        if len(lines) >= 3:
            body = "\n".join(lines[1:-1]).strip()
    if not body or _INT_LIST_RE.fullmatch(body) is None:
        return None
    try:
        return [int(part.strip(), 10) for part in body.split(",")]
    except (TypeError, ValueError, OverflowError):
        return None


def _candidate_values(inst: dict, positions: set[int]) -> list[int]:
    low = int(inst["low_prime"])
    high = int(inst["high_prime"])
    n = int(inst["variables"])
    return [high if index in positions else low for index in range(1, n + 1)]


def _form_value(inst: dict, positions: set[int]) -> int:
    values = _candidate_values(inst, positions)
    linear = sum(int(weight) * value
                 for weight, value in zip(inst["weights"], values))
    positive_factor = sum(values)
    return linear * positive_factor


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Accept every valid witness; never consult the planted answer."""
    if not isinstance(answer, (list, tuple)):
        return False, "answer_not_a_list"
    if len(answer) == 0:
        return False, "empty_answer"
    if any(not isinstance(value, int) or isinstance(value, bool) for value in answer):
        return False, "non_integer_position"

    try:
        n = int(inst["variables"])
        required = int(inst["high_count"])
        weights = list(inst["weights"])
        low = int(inst["low_prime"])
        high = int(inst["high_prime"])
    except (KeyError, TypeError, ValueError):
        return False, "malformed_instance"
    if len(weights) != n or required <= 0 or required >= n:
        return False, "malformed_instance"
    if not _is_prime(low) or not _is_prime(high) or low == high:
        return False, "invalid_instance_primes"
    if any(value < 1 or value > n for value in answer):
        return False, "position_out_of_range"
    if len(set(answer)) != len(answer):
        return False, "duplicate_position"
    if len(answer) != required:
        return False, f"wrong_count_expected_{required}_got_{len(answer)}"

    positions = set(answer)
    value = _form_value(inst, positions)
    if value != 0:
        return False, "equation_nonzero"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the statement-aware balanced candidate space."""
    n = int(inst["variables"])
    required = int(inst["high_count"])
    return sorted(rng.sample(range(1, n + 1), required))


def search_space(inst: dict) -> int | None:
    """Count all shape-correct balanced witnesses."""
    try:
        n = int(inst["variables"])
        required = int(inst["high_count"])
        if n < 0 or required < 0 or required > n:
            return None
        return math.comb(n, required)
    except (KeyError, TypeError, ValueError):
        return None


def enumerate_all(inst: dict) -> int | None:
    """Exactly count solutions when at most 100,000 candidates are needed."""
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    n = int(inst["variables"])
    required = int(inst["high_count"])
    count = 0
    for chosen in itertools.combinations(range(1, n + 1), required):
        if _form_value(inst, set(chosen)) == 0:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Canonicalise variable permutations, coefficient scale, and form sign."""
    weights = [int(value) for value in inst["weights"]]
    divisor = 0
    for value in weights:
        divisor = math.gcd(divisor, abs(value))
    if divisor:
        weights = [value // divisor for value in weights]
    positive = tuple(sorted(weights))
    negative = tuple(sorted(-value for value in weights))
    canonical_weights = min(positive, negative)
    payload = {
        "family": "balanced_prime_quadratic_zero_sum",
        "degree": 2,
        "variables": int(inst["variables"]),
        "high_count": int(inst["high_count"]),
        "primes": sorted((int(inst["low_prime"]), int(inst["high_prime"]))),
        "weights": canonical_weights,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase the exponential balanced-subset dimension by twelve variables."""
    current = int(params.get("n", 0))
    if current < 6 or current >= 120:
        return None
    harder = current + 12
    result = dict(params)
    old_bits = int(result.get("weight_bits", current))
    result["n"] = harder
    result["weight_bits"] = max(harder, old_bits + 8)
    return result


# --- inexpensive adversaries used by selftest -----------------------------

def _outlier_candidates(inst: dict) -> list[list[int]]:
    weights = list(inst["weights"])
    required = int(inst["high_count"])
    ranked = sorted(range(len(weights)), key=lambda i: (abs(weights[i]), i))
    return [
        sorted(index + 1 for index in ranked[:required]),
        sorted(index + 1 for index in ranked[-required:]),
    ]


def _greedy_candidate(inst: dict) -> list[int]:
    weights = list(inst["weights"])
    required = int(inst["high_count"])
    remaining = set(range(len(weights)))
    chosen: list[int] = []
    total = 0
    while len(chosen) < required:
        best = min(remaining, key=lambda i: (abs(total + weights[i]), i))
        chosen.append(best)
        remaining.remove(best)
        total += weights[best]
    return sorted(index + 1 for index in chosen)


def _random_restart_candidate(inst: dict, rng: random.Random,
                              restarts: int = 48) -> list[int] | None:
    weights = list(inst["weights"])
    n = len(weights)
    required = int(inst["high_count"])
    for _ in range(restarts):
        selected = set(rng.sample(range(n), required))
        total = sum(weights[index] for index in selected)
        if total == 0:
            return sorted(index + 1 for index in selected)
        for _step in range(n):
            outside = set(range(n)) - selected
            best_abs = abs(total)
            best_swap = None
            best_total = total
            for old in selected:
                without = total - weights[old]
                for new in outside:
                    candidate_total = without + weights[new]
                    score = abs(candidate_total)
                    if score < best_abs:
                        best_abs = score
                        best_swap = (old, new)
                        best_total = candidate_total
            if best_swap is None:
                break
            selected.remove(best_swap[0])
            selected.add(best_swap[1])
            total = best_total
            if total == 0:
                return sorted(index + 1 for index in selected)
    return None


def _permuted_instance(inst: dict, new_to_old: list[int], negate: bool = False) -> dict:
    """Relabel variables; ``new_to_old[j]`` is the old zero-based index."""
    transformed = dict(inst)
    sign = -1 if negate else 1
    transformed["weights"] = [sign * int(inst["weights"][old]) for old in new_to_old]
    old_selected = set(int(value) - 1 for value in inst["answer"])
    transformed["answer"] = sorted(
        new + 1 for new, old in enumerate(new_to_old) if old in old_selected
    )
    return transformed


def selftest() -> dict:
    """Run gates G1--G8 and return their measured, JSON-serialisable report."""
    report: dict[str, Any] = {
        "paper": "arXiv:2310.02137",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1: every named preset and several seeds.
    g1_failures = []
    g1_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 41):
            instance = make_instance(seed=seed, **params)
            ok, reason = verify(instance, instance["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    base = make_instance(seed=12345, **ship_params)

    # G2: five corruption classes, deliberately ordered for distinct reasons.
    planted = list(base["answer"])
    selected = set(planted)
    replacement = next(index for index in range(1, base["variables"] + 1)
                       if index not in selected)
    corruptions = {
        "drop_one": planted[:-1],
        "membership_swap": sorted([replacement] + planted[1:]),
        "duplicate": planted[:-1] + [planted[0]],
        "empty": [],
        "out_of_range": [base["variables"] + 1] + planted[1:],
    }
    corruption_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(base, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": (all(item["rejected"] for item in corruption_results.values())
                 and len(set(reasons)) == len(reasons)),
        "distinct_reasons": len(set(reasons)),
        "cases": corruption_results,
    }

    # G3: prose and a Markdown fence around the tagged final answer.
    body = ", ".join(map(str, planted))
    model_style = ("I reduced the form to the balanced zero-sum condition.\n\n"
                   "```text\n<answer>  " + body + "  </answer>\n```\n")
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_count": len(parsed) if isinstance(parsed, list) else None,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    # G4: uniform over exactly the balanced space a solver would search.
    guesses = 200_000
    guess_rng = random.Random(0x231002137)
    hits = 0
    for _ in range(guesses):
        candidate = random_candidate(base, guess_rng)
        if verify(base, candidate)[0]:
            hits += 1
    report["G4_guess_resistance"] = {
        "pass": hits / guesses < 1e-6,
        "hits": hits,
        "total": guesses,
        "empirical_probability": hits / guesses,
        "prior": "uniform over all exactly-n/2 subsets",
        "structured_space": search_space(base),
    }

    # G5: a smaller audit instance remains exactly enumerable.
    sparse_inst = make_instance(n=18, seed=202310, weight_bits=18)
    exact_solutions = enumerate_all(sparse_inst)
    sparse_space = search_space(sparse_inst)
    fraction = (exact_solutions / sparse_space
                if exact_solutions is not None and sparse_space else None)
    report["G5_sparse"] = {
        "pass": exact_solutions is not None and fraction is not None and fraction < 1e-3,
        "audit_n": 18,
        "valid_answers": exact_solutions,
        "candidate_space": sparse_space,
        "fraction": fraction,
        "enumeration_cap": _ENUMERATION_CAP,
    }

    # G6: attacks target construction-specific signatures, not malformed output.
    attack_seeds = list(range(800, 808))
    outlier_successes = 0
    greedy_successes = 0
    restart_successes = 0
    restart_budget = 48
    for seed in attack_seeds:
        instance = make_instance(seed=seed, **ship_params)
        if any(verify(instance, candidate)[0]
               for candidate in _outlier_candidates(instance)):
            outlier_successes += 1
        if verify(instance, _greedy_candidate(instance))[0]:
            greedy_successes += 1
        restart = _random_restart_candidate(
            instance, random.Random(seed ^ 0xA5A5A5A5), restart_budget
        )
        if restart is not None and verify(instance, restart)[0]:
            restart_successes += 1
    report["G6_adversary_panel"] = {
        "pass": outlier_successes == greedy_successes == restart_successes == 0,
        "seeds": len(attack_seeds),
        "attacks": {
            "absolute_magnitude_outliers_both_tails": {
                "successes": outlier_successes,
                "attempts": 2 * len(attack_seeds),
            },
            "greedy_cancellation": {
                "successes": greedy_successes,
                "attempts": len(attack_seeds),
            },
            "random_restart_best_swap": {
                "successes": restart_successes,
                "instances": len(attack_seeds),
                "restarts_per_instance": restart_budget,
            },
        },
    }

    # G7: doubling n increases the structured space and remains generatable.
    start = time.perf_counter()
    doubled_params = dict(ship_params)
    doubled_params["n"] = 2 * int(ship_params["n"])
    doubled_params["weight_bits"] = max(
        2 * int(ship_params["n"]), int(ship_params.get("weight_bits", 0))
    )
    doubled = make_instance(seed=99, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    build_seconds = time.perf_counter() - start
    report["G7_scales"] = {
        "pass": (doubled_ok
                 and search_space(doubled) is not None
                 and search_space(doubled) > search_space(base)),
        "base_n": ship_params["n"],
        "doubled_n": doubled_params["n"],
        "base_space": search_space(base),
        "doubled_space": search_space(doubled),
        "doubled_planted_reason": doubled_reason,
        "doubled_build_seconds": round(build_seconds, 6),
    }

    # G8: variable permutations, equation sign, and their compositions.
    invariant_checks = 0
    carried_witness_checks = 0
    invariant_failures = []
    distinct_keys = []
    for seed in range(20):
        instance = make_instance(seed=10_000 + seed, **ship_params)
        original_key = canonical_key(instance)
        distinct_keys.append(original_key)
        size = int(instance["variables"])
        reverse = list(reversed(range(size)))
        permutation = list(range(size))
        random.Random(seed + 77).shuffle(permutation)
        variants = [
            ("reverse", _permuted_instance(instance, reverse)),
            ("random", _permuted_instance(instance, permutation)),
            ("sign", _permuted_instance(instance, list(range(size)), True)),
            ("random_plus_sign", _permuted_instance(instance, permutation, True)),
        ]
        scaled = dict(instance)
        scaled["weights"] = [3 * value for value in instance["weights"]]
        variants.append(("positive_scale", scaled))
        permuted_scaled = _permuted_instance(scaled, permutation)
        variants.append(("permutation_plus_scale", permuted_scaled))
        for label, transformed in variants:
            invariant_checks += 1
            if canonical_key(transformed) != original_key:
                invariant_failures.append({"seed": seed, "transform": label})
            if label in ("random", "random_plus_sign", "permutation_plus_scale"):
                carried_witness_checks += 1
                if not verify(transformed, transformed["answer"])[0]:
                    invariant_failures.append({"seed": seed, "transform": label,
                                               "error": "carried witness failed"})
        # Complementing high/low choices is a genuine answer symmetry because
        # total weight is zero; test it even though it leaves the instance fixed.
        complement = sorted(set(range(1, size + 1)) - set(instance["answer"]))
        carried_witness_checks += 1
        if not verify(instance, complement)[0]:
            invariant_failures.append({"seed": seed, "transform": "answer_complement"})
    unique_keys = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": (not invariant_failures and unique_keys == 20
                 and carried_witness_checks >= 20),
        "seeds": 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_witness_checks,
        "distinct_keys": unique_keys,
        "unrelated_instances": 20,
        "failures": invariant_failures,
        "transformations": ["variable reversal", "random variable permutation",
                            "global form sign", "positive form scaling",
                            "permutation composed with sign or scaling",
                            "solution complement"],
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(bool(gate.get("pass")) for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
