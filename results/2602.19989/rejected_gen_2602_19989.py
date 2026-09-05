"""Verified sequenceability generator based on arXiv:2602.19989.

The paper studies orderings of subsets of cyclic groups whose modular partial
sums do not collide.  This module inverse-generates a shuffled multiplicative
orbit in an additive cyclic group.  Its planted orbit order is a sequencing by
an exact geometric-series identity; it is never recovered by solving the
emitted instance.
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


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "permutation",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "subset of the additive cyclic group Z_p",
        "ordering of distinct group elements",
        "modular partial sums",
    ],
    "verification_operations": [
        "exact integer range and permutation checks",
        "exact modular addition",
        "partial-sum equality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "A symmetric checksum reveals the multiplier of a hidden multiplicative "
        "orbit; without that invariant, one must compare candidate ratios across "
        "the whole shuffled set."
    ),
    "hardness_basis": (
        "Track B: exhaustive ratio-overlap orbit recognition runs in "
        "O(n^2 log p + n*min(p,n^2)) exact work and is measured on eight shipping "
        "instances in G6 (about 30000 modular-operation/membership units each), "
        "whereas the checksum-and-geometric-series route is measured below 300 "
        "exact operations and still requires long unaided modular bookkeeping."
    ),
    "max_answer_tokens": 150,
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

DIFFICULTY = {
    "demo": {"n": 7, "slack": 10},
    "easy": {"n": 48, "slack": 56},
    "medium": {"n": 80, "slack": 40},
    "hard": {"n": 120, "slack": 28},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Hint: The common multiplier of the hidden multiplicative orbit equals the "
    "sum of all displayed elements modulo p."
)
PLACEBO_HINT = (
    "Hint: The required ordering is sensitive to every displayed residue and to "
    "exact modular arithmetic throughout."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON array containing every displayed residue exactly once; entries "
        "are distinct integers in 1,...,p-1 and the array length is n."
    ),
    "bounds": {
        "shape": "permutation of the n displayed residues",
        "entry_min": 1,
        "entry_max": "p-1",
        "maximum_supported_n": 240,
        "candidate_count": "n!",
    },
}

# Filled only from transcripts written by scripts/harden.py.  Until then G9 is
# intentionally pending, so a preliminary selftest cannot masquerade as final
# oracle evidence.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 1},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "too_easy",
}

NOTES = r"""
Paper definition. Section 1 defines a valid ordering a_1,...,a_m of a subset of
an abelian group by pairwise distinct partial sums p_i=a_1+...+a_i.  It is a
sequencing when additionally p_i is nonzero for every i<m.  The module hands the
solver exactly a subset of Z_p and requests exactly that native ordering; there
is no graph, finite-field surrogate, or convenience reduction.

Step-0 decision. The paper contains no polynomial-time, FPT, approximation, or
computational-hardness result for finding a sequencing.  Theorems 1.3 and 1.4
are existence bounds, and Lemma 2.7 obtains existence with positive probability
after a structural decomposition, random splitting, conditioned orderings, and
the Lovasz Local Lemma.  Consequently those theorems do not support Track A for
this generated distribution.  The module makes the narrower Track B claim and
names its efficient distribution-specific reference algorithm openly.

Construction and certificate source. Choose a prime p>n+1 and a primitive root
r modulo p.  For G=1+r+...+r^(n-1), set u=r/G modulo p and form
A={u,ur,...,ur^(n-1)}.  Because n<p-1, G is nonzero.  The planted answer is the
orbit order, sampled before A is shuffled.  Every consecutive interval of length
ell has sum u*r^i*(r^ell-1)/(r-1), which is nonzero for 1<=ell<=n because r has
order p-1.  Thus all partial sums are distinct and every proper partial sum is
nonzero.  Also sum(A)=uG=r, which plants the compact checksum invariant without
solving the instance.

Hardness and easy route. Track A is deliberately not claimed.  The exact Track B
reference algorithm forms all pairwise ratios, scores each multiplier by how
many set elements it maps back into the set, and expands the two score-(n-1)
orbit directions.  Selftest measures its wall time and exact operation units on
eight shipping seeds.  The compact route sums the displayed residues to recover
r, evaluates the geometric series by binary powering, recovers u, and emits the
orbit.  That route is also executed and operation-counted in G9; it is short
enough for the cap but long enough that exact unaided bookkeeping remains the
challenge.

Attack hardening. Plants and all displayed elements are the same orbit, so there
is no distinguished planted element.  The panel tries centered-magnitude order,
a locally safe middle-first greedy rule, 256 structure-aware random permutation
restarts, and an in-context shortcut that knows the checksum multiplier but
guesses the numerical minimum as the orbit endpoint.  All are run on eight
shipping instances.  Crowding p close to n, rather than special-looking planted
values, suppresses accidental sequenceings.  Difficulty increases n and reduces
the number of unused residues; escalate tightens crowding at fixed answer length
before lengthening the witness.

Canonicalization. Reordering the displayed set is presentation only, and every
additive automorphism of Z_p scales all elements by one nonzero residue.  The key
is the lexicographically least sorted scaled set over all such units, hashed only
after this exact normal form is obtained.  Selftest checks reordering, scaling,
their composition, carried witnesses, and twenty unrelated canonical forms.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


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


def _next_prime(value: int) -> int:
    candidate = max(3, value)
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _prime_factors(value: int) -> list[int]:
    factors = []
    divisor = 2
    while divisor * divisor <= value:
        if value % divisor == 0:
            factors.append(divisor)
            while value % divisor == 0:
                value //= divisor
        divisor += 1 if divisor == 2 else 2
    if value > 1:
        factors.append(value)
    return factors


def _primitive_root_representatives(p: int) -> list[int]:
    factors = _prime_factors(p - 1)
    roots = [
        value
        for value in range(2, p)
        if all(pow(value, (p - 1) // factor, p) != 1 for factor in factors)
    ]
    # Forward and reversed orbits use inverse multipliers and give the same set.
    return [value for value in roots if value < pow(value, -1, p)]


def make_instance(n: int, seed: int = 0, slack: int = 28, **params) -> dict:
    """Inverse-generate a sequenceable subset and its orbit-order certificate."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or not 3 <= n <= 240:
        raise ValueError("n must be an integer from 3 through 240")
    if isinstance(slack, bool) or not isinstance(slack, int) or slack < 2:
        raise ValueError("slack must be an integer at least 2")

    rng = random.Random(seed)
    # The modulus stays close to n so a generic permutation has many opportunities
    # for a modular partial-sum collision.  Randomness selects the modulus and the
    # (inverse-paired) primitive-root orbit, not a visibly special planted item.
    p = _next_prime(n + 2 + rng.randrange(slack))
    if p - 1 <= n:
        p = _next_prime(n + 2)
    roots = _primitive_root_representatives(p)
    if not roots:
        raise RuntimeError("failed to find a primitive-root representative")
    r = rng.choice(roots)

    geometric_sum = (pow(r, n, p) - 1) * pow(r - 1, -1, p) % p
    if geometric_sum == 0:
        raise RuntimeError("geometric sum unexpectedly vanished")
    start = r * pow(geometric_sum, -1, p) % p

    answer = []
    value = start
    for _ in range(n):
        answer.append(value)
        value = value * r % p
    if len(set(answer)) != n or sum(answer) % p != r:
        raise RuntimeError("orbit construction invariant failed")

    elements = list(answer)
    rng.shuffle(elements)
    return {
        "family": "sequencing a subset of the additive cyclic group Z_p",
        "p": p,
        "n": n,
        "elements": elements,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the complete native sequencing problem and exact wire format."""
    statement = f"""Sequence a subset of the cyclic group Z_p

All arithmetic below is modulo p = {inst['p']}, using the residues 0 through
{inst['p'] - 1}.  The displayed set A contains {inst['n']} distinct nonzero
residues:

A = {json.dumps(inst['elements'], separators=(',', ':'))}

Output an ordering [a_1,...,a_{inst['n']}] containing every member of A exactly
once, with no repetition.  Define partial sums s_i = a_1+...+a_i (mod p) for
1 <= i <= {inst['n']}.  Your ordering is accepted exactly when all s_i are
pairwise distinct and s_i != 0 for every 1 <= i < {inst['n']}.  The last partial
sum s_{inst['n']} is allowed to be 0.  Array positions are 1-based in this
definition; residues use their displayed representatives.  Order matters.

Give your final answer inside <answer></answer> tags as one JSON array of exactly
{inst['n']} decimal integers, separated by commas.
Example: <answer>[3,17,42]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    """Extract a tagged JSON integer array; malformed material returns None."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    if body.startswith("```") and body.endswith("```"):
        lines = body.splitlines()
        if len(lines) >= 3:
            body = "\n".join(lines[1:-1]).strip()
    try:
        candidate = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(candidate, list):
        return None
    if any(isinstance(value, bool) or not isinstance(value, int) for value in candidate):
        return None
    return candidate


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Check any sequencing directly, never consulting ``inst['answer']``."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if not answer:
        return False, "answer is empty"
    if len(answer) != inst["n"]:
        return False, f"answer length must be exactly {inst['n']}"
    p = inst["p"]
    for index, value in enumerate(answer, 1):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"entry {index} is not an integer"
        if not 1 <= value < p:
            return False, f"entry {index} is outside 1,...,{p - 1}"
    if len(set(answer)) != len(answer):
        return False, "answer repeats a residue"
    if set(answer) != set(inst["elements"]):
        return False, "answer is not a permutation of the displayed set"

    partial = 0
    seen: set[int] = set()
    for index, value in enumerate(answer, 1):
        partial = (partial + value) % p
        if partial in seen:
            return False, f"partial sum at position {index} repeats an earlier partial sum"
        if index < len(answer) and partial == 0:
            return False, f"proper partial sum at position {index} is zero"
        seen.add(partial)
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the statement-aware space of permutations of A."""
    candidate = list(inst["elements"])
    rng.shuffle(candidate)
    return candidate


def search_space(inst: dict) -> int | None:
    """Return the exact size n! of the bounded certificate language."""
    return math.factorial(inst["n"])


def enumerate_all(inst: dict) -> int | None:
    """Count all valid orderings exactly when n! is below a safe work cap."""
    if math.factorial(inst["n"]) > 100_000:
        return None
    count = 0
    for candidate in itertools.permutations(inst["elements"]):
        count += int(verify(inst, list(candidate))[0])
    return count


def canonical_key(inst: dict) -> str:
    """Canonicalize set order and every automorphism x -> c*x of additive Z_p."""
    p = inst["p"]
    elements = inst["elements"]
    normal = min(
        tuple(sorted((unit * value) % p for value in elements))
        for unit in range(1, p)
    )
    payload = json.dumps([p, normal], separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Tighten crowding at fixed witness length before increasing n."""
    clean = {key: value for key, value in params.items() if key != "_preset"}
    n = int(clean.get("n", 120))
    slack = int(clean.get("slack", 28))
    if slack > 4:
        return {"n": n, "slack": max(4, slack // 2)}
    if n < 160:
        return {"n": min(160, n + 20), "slack": 4}
    if n < 220:
        return {"n": min(220, n + 20), "slack": 3}
    return "cap_bound"


# ---------------------------------------------------------------------------
# Exact reference solver, compact route, attacks, and symmetry transforms.


def _inverse_with_count(value: int, modulus: int) -> tuple[int, int]:
    """Extended-Euclid inverse and its exact division-step count."""
    old_r, r = value, modulus
    old_s, s = 1, 0
    divisions = 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        divisions += 1
    if old_r != 1:
        raise ValueError("value is not invertible")
    return old_s % modulus, divisions


def _pow_with_count(base: int, exponent: int, modulus: int) -> tuple[int, int]:
    result = 1
    factor = base % modulus
    multiplications = 0
    while exponent:
        if exponent & 1:
            result = result * factor % modulus
            multiplications += 1
        exponent >>= 1
        if exponent:
            factor = factor * factor % modulus
            multiplications += 1
    return result, multiplications


def _compact_checksum_solver(inst: dict) -> tuple[list[int] | None, int]:
    """The intended checksum/geometric-series route, with operation count."""
    p = inst["p"]
    n = inst["n"]
    operations = 0
    multiplier = 0
    for value in inst["elements"]:
        multiplier = (multiplier + value) % p
        operations += 1
    if multiplier in (0, 1):
        return None, operations
    power, used = _pow_with_count(multiplier, n, p)
    operations += used
    inverse, used = _inverse_with_count(multiplier - 1, p)
    operations += used
    geometric_sum = (power - 1) * inverse % p
    operations += 2
    if geometric_sum == 0:
        return None, operations
    inverse, used = _inverse_with_count(geometric_sum, p)
    operations += used
    start = multiplier * inverse % p
    operations += 1
    answer = [start]
    for _ in range(1, n):
        answer.append(answer[-1] * multiplier % p)
        operations += 1
    return answer, operations


def _reference_orbit_solver(inst: dict) -> tuple[list[int] | None, int]:
    """Structure-aware but checksum-blind exhaustive ratio-overlap recognizer."""
    p = inst["p"]
    elements = list(inst["elements"])
    element_set = set(elements)
    operations = 0
    inverses = {}
    for value in elements:
        inverses[value], used = _inverse_with_count(value, p)
        operations += used

    ratios = set()
    for left in elements:
        for right in elements:
            if left == right:
                continue
            ratios.add(left * inverses[right] % p)
            operations += 1

    scored = []
    for ratio in sorted(ratios):
        overlap = 0
        for value in elements:
            overlap += int(value * ratio % p in element_set)
            operations += 1
        scored.append((overlap, ratio))
    scored.sort(reverse=True)

    for overlap, ratio in scored:
        if overlap < len(elements) - 1:
            break
        inverse, used = _inverse_with_count(ratio, p)
        operations += used
        starts = []
        for value in elements:
            starts.append((value * inverse % p not in element_set, value))
            operations += 1
        for is_start, start in starts:
            if not is_start:
                continue
            candidate = [start]
            for _ in range(1, len(elements)):
                candidate.append(candidate[-1] * ratio % p)
                operations += 1
            if verify(inst, candidate)[0]:
                return candidate, operations
    return None, operations


def _outlier_magnitude_attack(inst: dict) -> list[int]:
    p = inst["p"]
    return sorted(inst["elements"], key=lambda value: (min(value, p - value), value))


def _middle_first_greedy_attack(inst: dict) -> list[int]:
    p = inst["p"]
    remaining = set(inst["elements"])
    candidate = []
    partial = 0
    seen: set[int] = set()
    while remaining:
        legal = [value for value in remaining if (partial + value) % p not in seen]
        if not legal:
            break
        value = min(legal, key=lambda item: (abs(item - p / 2), item))
        candidate.append(value)
        remaining.remove(value)
        partial = (partial + value) % p
        seen.add(partial)
    return candidate


def _checksum_minimum_attack(inst: dict) -> list[int]:
    p = inst["p"]
    multiplier = sum(inst["elements"]) % p
    candidate = [min(inst["elements"])]
    for _ in range(1, inst["n"]):
        candidate.append(candidate[-1] * multiplier % p)
    return candidate


def _random_restart_attack(
    inst: dict, seed: int, trials: int = 256
) -> tuple[list[int] | None, int, int]:
    rng = random.Random(seed)
    prefix_checks = 0
    last = None
    for attempt in range(1, trials + 1):
        last = random_candidate(inst, rng)
        partial = 0
        seen: set[int] = set()
        viable = True
        for index, value in enumerate(last, 1):
            prefix_checks += 1
            partial = (partial + value) % inst["p"]
            if partial in seen or (index < len(last) and partial == 0):
                viable = False
                break
            seen.add(partial)
        if viable and verify(inst, last)[0]:
            return last, attempt, prefix_checks
    return last, trials, prefix_checks


def _scale_and_reorder(inst: dict, unit: int, seed: int | None = None) -> dict:
    transformed = dict(inst)
    p = inst["p"]
    transformed["elements"] = [(unit * value) % p for value in inst["elements"]]
    transformed["answer"] = [(unit * value) % p for value in inst["answer"]]
    if seed is not None:
        rng = random.Random(seed)
        rng.shuffle(transformed["elements"])
    return transformed


def _find_bad_swap(inst: dict) -> list[int] | None:
    planted = inst["answer"]
    for left in range(len(planted)):
        for right in range(left + 1, len(planted)):
            candidate = list(planted)
            candidate[left], candidate[right] = candidate[right], candidate[left]
            if not verify(inst, candidate)[0]:
                return candidate
    return None


def _answer_elements(answer: list[int]) -> int:
    return len(answer)


def selftest() -> dict:
    """Run all mandatory gates and return JSON-native measured evidence."""
    report: dict[str, object] = {
        "paper": "2602.19989",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1: every preset, several seeds, and JSON-native certificate encoding.
    failures = []
    instances = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            json_native = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            instances += 1
            if not ok or not json_native:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "instances": instances,
        "failures": failures,
    }

    ship = make_instance(seed=20260223, **DIFFICULTY[SHIPPING_DIFFICULTY])

    # G2: route the five requested corruptions to five independent checks.
    planted = ship["answer"]
    bad_swap = _find_bad_swap(ship)
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": bad_swap if bad_swap is not None else list(reversed(planted)),
        "duplicate_one": planted[:-1] + [planted[0]],
        "empty": [],
        "out_of_range": [ship["p"]] + planted[1:],
    }
    rejection_flags = {}
    rejection_reasons = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(ship, candidate)
        rejection_flags[name] = not ok
        rejection_reasons[name] = reason
    report["G2_rejects_corruption"] = {
        "pass": all(rejection_flags.values()) and len(set(rejection_reasons.values())) == 5,
        "rejected": rejection_flags,
        "reasons": rejection_reasons,
        "distinct_reasons": len(set(rejection_reasons.values())),
    }

    # G3: prose and a Markdown fence around the exact tagged JSON answer.
    response = (
        "I checked all modular partial sums exactly.\n```json\n"
        f"<answer>{json.dumps(planted)}</answer>\n```\n"
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("not an answer") is None,
        "parsed_equals_answer": parsed == planted,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    # G4 and G5 density use uniform permutations, after every obvious shape and
    # membership condition from the statement has already been imposed.
    guess_rng = random.Random(260219989)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "structure_aware_search_space": search_space(ship),
        "candidate_prior": "uniform over all permutations of the displayed set",
    }

    # G6: four failing, tool-free attacks and a successful Track-B reference.
    attack_seeds = list(range(8))
    attacks = {
        "outlier_centered_magnitude_order": {"successes": 0, "attempts": 0},
        "greedy_locally_safe_middle_first": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
        "in_context_checksum_with_minimum_anchor": {"successes": 0, "attempts": 0},
    }
    random_trials = 0
    random_prefix_checks = 0
    attack_started = time.perf_counter()
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        random_answer, used_trials, prefix_checks = _random_restart_attack(
            inst, seed ^ 0x5E0E, 256
        )
        random_trials += used_trials
        random_prefix_checks += prefix_checks
        candidates = {
            "outlier_centered_magnitude_order": _outlier_magnitude_attack(inst),
            "greedy_locally_safe_middle_first": _middle_first_greedy_attack(inst),
            "random_restart_256": random_answer,
            "in_context_checksum_with_minimum_anchor": _checksum_minimum_attack(inst),
        }
        for name, candidate in candidates.items():
            attacks[name]["attempts"] += 1
            attacks[name]["successes"] += int(verify(inst, candidate)[0])
    attack_wall = time.perf_counter() - attack_started

    reference_successes = 0
    reference_operations = 0
    reference_max_operations = 0
    reference_started = time.perf_counter()
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidate, operations = _reference_orbit_solver(inst)
        reference_operations += operations
        reference_max_operations = max(reference_max_operations, operations)
        reference_successes += int(candidate is not None and verify(inst, candidate)[0])
    reference_wall = time.perf_counter() - reference_started
    all_attacks_failed = all(item["successes"] == 0 for item in attacks.values())
    reference_algorithm = {
        "name": "exhaustive pair-ratio overlap recognition and orbit expansion",
        "complexity": "O(n^2 log p + n*min(p,n^2)) exact operations",
        "wall_clock_sec": round(reference_wall, 6),
        "operations": reference_operations,
        "average_operations": reference_operations // len(attack_seeds),
        "max_operations_one_instance": reference_max_operations,
        "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == len(attack_seeds),
        "attacks": attacks,
        "reference_algorithm": reference_algorithm,
    }

    report["G5_density_and_baseline_cost"] = {
        "pass": guess_probability < 1e-6 and all_attacks_failed,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_valid_fraction": guess_probability,
        "baseline_wall_clock_seconds": round(attack_wall, 6),
        "baseline_iterations": random_trials,
        "baseline_prefix_checks": random_prefix_checks,
        "baseline_attack": "256 uniform permutation restarts plus three deterministic probes",
        "reference_wall_clock_seconds": round(reference_wall, 6),
        "reference_operation_units": reference_operations,
        "demo_exact_solution_count": enumerate_all(
            make_instance(seed=20260223, **DIFFICULTY["demo"])
        ),
    }

    # G7: a literal size doubling builds, verifies, and enlarges the language.
    before = make_instance(n=60, slack=28, seed=771)
    doubled = make_instance(n=120, slack=28, seed=771)
    report["G7_scales"] = {
        "pass": (
            verify(before, before["answer"])[0]
            and verify(doubled, doubled["answer"])[0]
            and search_space(doubled) > search_space(before)
        ),
        "n_before": before["n"],
        "n_after_doubling": doubled["n"],
        "space_before": search_space(before),
        "space_after": search_space(doubled),
        "answer_elements_after": _answer_elements(doubled["answer"]),
    }

    # G8: set reorderings, group automorphisms, their compositions, and diversity.
    invariant_checks = 0
    carried_checks = 0
    invariant_ok = True
    carried_ok = True
    unrelated_keys = []
    diversity_seed = 10_000
    while len(unrelated_keys) < 20 and diversity_seed < 20_000:
        inst = make_instance(
            seed=diversity_seed, **DIFFICULTY[SHIPPING_DIFFICULTY]
        )
        key = canonical_key(inst)
        if key in unrelated_keys:
            diversity_seed += 1
            continue
        unrelated_keys.append(key)
        rng = random.Random(30_000 + diversity_seed)
        unit1 = rng.randrange(1, inst["p"])
        unit2 = rng.randrange(1, inst["p"])
        reordered = _scale_and_reorder(inst, 1, seed=diversity_seed)
        scaled = _scale_and_reorder(inst, unit1)
        composed = _scale_and_reorder(scaled, unit2, seed=diversity_seed + 1)
        base_key = canonical_key(inst)
        for transformed in (reordered, scaled, composed):
            invariant_checks += 1
            invariant_ok = invariant_ok and canonical_key(transformed) == base_key
            carried_checks += 1
            carried_ok = carried_ok and verify(transformed, transformed["answer"])[0]
        diversity_seed += 1
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_ok and carried_ok and distinct_count == 20,
        "invariance_checks": invariant_checks,
        "invariance_passed": invariant_checks if invariant_ok else 0,
        "carried_witness_checks": carried_checks,
        "carried_witness_passed": carried_checks if carried_ok else 0,
        "unrelated_instances": 20,
        "distinct_keys": distinct_count,
        "seeds_examined_for_diversity": diversity_seed - 10_000,
        "symmetries": [
            "reordering of the displayed set",
            "multiplication by an arbitrary nonzero residue",
            "composition of scaling and reordering",
        ],
    }

    # G9 local caps are measured by executing the intended compact solver.  The
    # three oracle arms remain script-owned evidence read from the constant above.
    compact_answer, intended_ops = _compact_checksum_solver(ship)
    compact_ok = compact_answer is not None and verify(ship, compact_answer)[0]
    answer_chars = len(json.dumps(ship["answer"], separators=(",", ":")))
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_elements(ship["answer"])
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else 0.0
    placebo_rate = (
        arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else 0.0
    )
    evidence_complete = all(arms[name]["attempts"] >= 3 for name in arms)
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    hinted_hardened = G9_ORACLE_RESULTS["hinted_verdict"] == "hardened"
    report["G9_no_tool_suitability"] = {
        "pass": evidence_complete and hinted_hardened and within_caps and compact_ok,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_attempts and placebo_attempts
            else None
        ),
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "intended_route_verified": compact_ok,
        "within_caps": within_caps,
    }

    gate_values = [
        value
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_passed"] = all(value.get("pass") is True for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
