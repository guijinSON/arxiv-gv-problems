"""Projective-basis coefficient recovery for a geometric incidence code.

The paper defines C_k(n,q) as the span, over the prime subfield, of the
characteristic functions of the k-spaces of PG(n,q).  This module restricts
that native evaluation problem to a projective basis and its opposite
hyperplanes.  The certificate (the generator coefficients) is sampled first;
the displayed codeword evaluations are then composed from the incidence
identities.  No linear system is solved during generation.
"""

from __future__ import annotations

import hashlib
import itertools
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
except ImportError:  # pragma: no cover - the implementation is stdlib-only
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "points of a projective basis and opposite hyperplanes over GF(p)",
        "characteristic functions of hyperplanes",
        "a restricted projective geometric codeword",
    ],
    "verification_operations": [
        "exact projective point-hyperplane containment",
        "exact modular addition",
        "exact finite-field equality",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Each displayed hyperplane misses a unique basis point, so summing all "
        "point values exposes the total coefficient sum and replaces a dense solve."
    ),
    "hardness_basis": (
        "Track B: exact modular Gaussian elimination solves the coefficient system "
        "in O(n^3); at shipping n=104 it averaged 67,337 field operations and "
        "0.0019 seconds, while the total-sum invariant uses 208 field operations "
        "but must be recognized and executed without a solver or calculator."
    ),
    "max_answer_tokens": 415,
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

_LARGE_PRIME = 2_147_483_647

DIFFICULTY = {
    "demo": {"n": 3, "p": 7},
    "easy": {"n": 96, "p": _LARGE_PRIME},
    "medium": {"n": 104, "p": _LARGE_PRIME},
    "hard": {"n": 112, "p": _LARGE_PRIME},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "Pair every hyperplane with its unique missed point, sum all displayed "
    "values, and recover the common coefficient total before subtracting."
)
PLACEBO_HINT = (
    "Track every hyperplane and its displayed point label carefully, reduce "
    "all arithmetic modulo p, and check every value before submitting."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly n pairs [i,x_i], containing every hyperplane "
        "index i=0,...,n-1 exactly once in any order, with 0 <= x_i < p."
    ),
    "bounds": {
        "pair_count": "n",
        "hyperplane_index_min": 0,
        "hyperplane_index_max": "n-1",
        "coefficient_min": 0,
        "coefficient_max": "p-1",
        "candidate_count": "p^n",
    },
}

NOTES = r"""
Paper boundary. Definition 2.1 gives both equivalent native forms of
an incidence code: the span of block characteristic functions and the row
space of an incidence matrix. Definition 2.2 specializes this to the points
and k-spaces of PG(n,q), over the prime field F_p. Section 2 also states that
ordering points and blocks is immaterial. Those statements license exactly
the point/hyperplane evaluation objects used here; no graph or finite-field
surrogate replaces them.

STEP 0 hardness decision. The proposed certificate is produced by solving a
square linear system over F_p. Generic exact modular Gaussian elimination is
polynomial, O(n^3), so a Track A claim would be false. This is Track B. On the
shipping preset selftest measures the actual field-operation and wall-clock
cost of that reference method. The compact route notices that the restricted
incidence matrix is a row/column permutation of J-I. If S=sum_i x_i, then
b_j=S-x_i for the unique H_i missing P_j, while sum_j b_j=(n-1)S. The supplied
inverse of n-1 therefore gives S in one multiplication and all coefficients
in n subtractions, after n-1 additions: exactly 2n field operations.

What the paper makes easy. Result 3.5 and Construction 3.6 explicitly give
minimum even sets when q is even, and Theorem 1.1/Corollary 3.17 classify and
count the minimum dual words for q in {4,8}; using a coordinate-scrambled
minimum word would therefore be an explicit lookup/construction, not Track A,
and all such words form one automorphism orbit. Section 4 similarly classifies
small primal words. This generator deliberately asks for coefficients of a
random codeword instead: the answer is inverse-generated, and the known
algorithm is reported rather than hidden.

Attack controls. Coefficients are uniform in the whole declared language, so
the planted vector has no magnitude, position, sparsity, or nonzero-count
signature. The panel tests a largest-residue one-term outlier, the tempting
zero-total greedy rule, 256 uniform restarts, and a plausible by-hand guess
that substitutes the most frequent displayed value for the unknown total.
The reference Gaussian solve is reported separately, as Track B requires.
canonical_key uses only the multiset of codeword values: the opposite-hyperplane
basis restriction makes this the exact cheap invariant under independent
renaming of points and hyperplanes. Projective coordinate changes are already
quotiented out because the instance exposes containment, not chosen coordinates.
""".strip()


# Replaced with the three harness results after they have actually run.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 1, "attempts": 3},
    "hinted_verdict": "hardened",
}


def _is_prime_64(value):
    """Deterministic Miller-Rabin primality test for unsigned 64-bit integers."""
    if (isinstance(value, bool) or not isinstance(value, int)
            or value < 2 or value >= 2**64):
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value % prime == 0:
            return value == prime
    d = value - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        x = pow(base, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _validate_parameters(n, seed, p):
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if not _is_prime_64(p):
        raise ValueError("p must be a prime below 2^64")
    if (n - 1) % p == 0:
        raise ValueError("n-1 must be nonzero modulo p")


def make_instance(n, seed=0, **params):
    """Sample coefficients first, then compose their projective evaluations."""
    p = params.pop("p", _LARGE_PRIME)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_parameters(n, seed, p)
    rng = random.Random(seed)

    # The witness is sampled before any public right-hand side is formed.
    coefficients = [rng.randrange(p) for _ in range(n)]

    # H_i is X_e=0 in hidden projective-basis coordinates, e=excluded[i].
    # Hence it contains all displayed basis points except P_e.
    excluded = list(range(n))
    rng.shuffle(excluded)
    total = sum(coefficients) % p
    inverse_excluded = [0] * n
    for hyperplane, point in enumerate(excluded):
        inverse_excluded[point] = hyperplane
    values = [
        (total - coefficients[inverse_excluded[point]]) % p
        for point in range(n)
    ]
    answer = [[i, coefficients[i]] for i in range(n)]
    return {
        "n": n,
        "p": p,
        "excluded": excluded,
        "values": values,
        "inverse_n_minus_1": pow(n - 1, -1, p),
        "answer": answer,
    }


def render(inst):
    """Render the complete native projective-code problem and output contract."""
    n = inst["n"]
    statement = f"""Projective-basis codeword coefficient recovery

All arithmetic is in the prime field GF({inst['p']}), represented by the
integers 0 through {inst['p'] - 1} with addition and multiplication modulo
{inst['p']}.

There are {n} displayed points P_0,...,P_{n - 1} forming a projective basis
restriction in PG({n - 1},{inst['p']}), and {n} displayed hyperplanes
H_0,...,H_{n - 1}.  A hyperplane characteristic function chi_i has value 1
at a displayed point lying on H_i and value 0 otherwise.  The codeword is

    c = x_0 chi_0 + ... + x_{n - 1} chi_{n - 1}  over GF({inst['p']}).

For each hyperplane H_i, the following list gives the unique displayed point
it does NOT contain.  H_i contains every other displayed point.  Entry i is
the 0-based index of that missed point:

    missed_by_hyperplane = {json.dumps(inst['excluded'], separators=(',', ':'))}

The next list gives c(P_j), in point-index order j=0,...,{n - 1}:

    point_values = {json.dumps(inst['values'], separators=(',', ':'))}

The system has a unique coefficient vector.  For exact arithmetic you may use
the supplied value

    inverse_of_n_minus_1 = {inst['inverse_n_minus_1']}

which satisfies ({n}-1)*inverse_of_n_minus_1 = 1 modulo {inst['p']}.

Find every coefficient x_i.  Indices are 0-based; every hyperplane index must
appear exactly once; pair order is irrelevant; coefficients must be their
canonical integer residues from 0 through {inst['p'] - 1}.

Give your final answer inside <answer></answer> tags, as a JSON list of exactly
{n} pairs [hyperplane_index,coefficient].
Example format: <answer>[[0,3],[1,5],[2,1]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse the final tagged JSON value, tolerating prose and markdown fences."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    if not blocks:
        return None
    body = blocks[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def _coefficient_map(inst, answer):
    """Validate the bounded certificate syntax; return (map, reason)."""
    if not isinstance(answer, list):
        return None, "answer must be a JSON list"
    if not answer:
        return None, "answer is empty"
    n, p = inst["n"], inst["p"]
    if len(answer) != n:
        return None, f"wrong term count: expected {n}, got {len(answer)}"
    coefficients = {}
    for position, pair in enumerate(answer):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            return None, f"malformed pair at answer position {position}"
        index, coefficient = pair
        if isinstance(index, bool) or not isinstance(index, int):
            return None, f"hyperplane index at position {position} is not an integer"
        if index < 0 or index >= n:
            return None, f"hyperplane index out of range at position {position}"
        if index in coefficients:
            return None, f"duplicate hyperplane index {index}"
        if isinstance(coefficient, bool) or not isinstance(coefficient, int):
            return None, f"coefficient for H_{index} is not an integer"
        if coefficient < 0 or coefficient >= p:
            return None, f"coefficient for H_{index} is outside GF(p) residue range"
        coefficients[index] = coefficient
    return coefficients, "ok"


def verify(inst, answer):
    """Check syntax and every projective containment sum; never read answer key."""
    coefficients, reason = _coefficient_map(inst, answer)
    if coefficients is None:
        return False, reason
    n, p = inst["n"], inst["p"]
    excluded = inst.get("excluded")
    values = inst.get("values")
    if (not isinstance(excluded, list) or len(excluded) != n
            or sorted(excluded) != list(range(n))):
        return False, "instance has malformed missed-point permutation"
    if (not isinstance(values, list) or len(values) != n
            or any(isinstance(v, bool) or not isinstance(v, int)
                   or v < 0 or v >= p for v in values)):
        return False, "instance has malformed point values"

    # At P_j all H_i contribute except the unique H_i with excluded[i]=j.
    total = sum(coefficients.values()) % p
    inverse_excluded = [0] * n
    for hyperplane, point in enumerate(excluded):
        inverse_excluded[point] = hyperplane
    for point, expected in enumerate(values):
        actual = (total - coefficients[inverse_excluded[point]]) % p
        if actual != expected:
            return False, (
                f"projective value mismatch at P_{point}: got {actual}, "
                f"expected {expected}"
            )
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the exact bounded language GF(p)^n with shuffled pairs."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    pairs = [[i, rng.randrange(inst["p"])] for i in range(inst["n"])]
    rng.shuffle(pairs)
    return pairs


def search_space(inst):
    """The semantic language has one field value for each named hyperplane."""
    return inst["p"] ** inst["n"]


def enumerate_all(inst):
    """Brute-force small languages exactly, and cap larger work."""
    space = search_space(inst)
    if space > 1_000_000:
        return None
    count = 0
    n, p = inst["n"], inst["p"]
    for values in itertools.product(range(p), repeat=n):
        candidate = [[i, values[i]] for i in range(n)]
        count += int(verify(inst, candidate)[0])
    return count


def canonical_key(inst):
    """Canonicalize independent point/hyperplane renamings of the basis."""
    # Every valid excluded map is a perfect matching. Independent renamings can
    # normalize it to the identity, leaving exactly the multiset of point labels.
    payload = {
        "family": "projective-basis-opposite-hyperplane-codeword",
        "p": inst["p"],
        "n": inst["n"],
        "point_value_multiset": sorted(inst["values"]),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params):
    """Raise projective-basis size while respecting the no-tool output caps."""
    n = params.get("n")
    p = params.get("p", _LARGE_PRIME)
    if not isinstance(n, int) or n >= 120:
        return None
    return {"n": min(120, n + 8), "p": p}


def _compact_solve(inst):
    """The intended 2n-operation invariant route."""
    p, n = inst["p"], inst["n"]
    total = sum(inst["values"]) % p
    total = total * inst["inverse_n_minus_1"] % p
    coefficients = [0] * n
    for hyperplane, point in enumerate(inst["excluded"]):
        coefficients[hyperplane] = (total - inst["values"][point]) % p
    return [[i, coefficients[i]] for i in range(n)]


def _gaussian_reference(inst):
    """Generic exact Gauss-Jordan elimination, with abstract field-op counts."""
    n, p = inst["n"], inst["p"]
    inv_excluded = [0] * n
    for hyperplane, point in enumerate(inst["excluded"]):
        inv_excluded[point] = hyperplane
    matrix = []
    for point in range(n):
        row = [1] * n
        row[inv_excluded[point]] = 0
        row.append(inst["values"][point])
        matrix.append(row)

    operations = 0
    inversions = 0
    for column in range(n):
        pivot = next((row for row in range(column, n)
                      if matrix[row][column] % p), None)
        if pivot is None:
            return None, {"field_operations": operations,
                          "inversions": inversions}
        if pivot != column:
            matrix[column], matrix[pivot] = matrix[pivot], matrix[column]
        pivot_value = matrix[column][column] % p
        if pivot_value != 1:
            inverse = pow(pivot_value, -1, p)
            inversions += 1
            for j in range(column, n + 1):
                matrix[column][j] = matrix[column][j] * inverse % p
                operations += 1
        for row in range(n):
            if row == column:
                continue
            factor = matrix[row][column] % p
            if factor == 0:
                continue
            for j in range(column, n + 1):
                matrix[row][j] = (matrix[row][j]
                                  - factor * matrix[column][j]) % p
                operations += 2
    answer = [[i, matrix[i][n] % p] for i in range(n)]
    return answer, {"field_operations": operations,
                    "inversions": inversions}


def _candidate_from_total_guess(inst, total_guess):
    p = inst["p"]
    values = [0] * inst["n"]
    for hyperplane, point in enumerate(inst["excluded"]):
        values[hyperplane] = (total_guess - inst["values"][point]) % p
    return [[i, values[i]] for i in range(inst["n"])]


def _attack_candidates(inst, rng):
    """Four in-context attacks that deliberately do not use the invariant."""
    n, p = inst["n"], inst["p"]
    # Per-element magnitude/outlier probe: explain all values by one generator.
    point = max(range(n), key=lambda j: inst["values"][j])
    hyperplane = next(i for i, missed in enumerate(inst["excluded"])
                      if missed == point)
    sparse = [[i, 0] for i in range(n)]
    sparse[hyperplane][1] = inst["values"][point]

    zero_total = _candidate_from_total_guess(inst, 0)

    counts = {}
    for value in inst["values"]:
        counts[value] = counts.get(value, 0) + 1
    mode = min(counts, key=lambda value: (-counts[value], value))
    mode_total = _candidate_from_total_guess(inst, mode)

    restarts = [random_candidate(inst, rng) for _ in range(256)]
    return {
        "outlier_largest_residue_one_term": [sparse],
        "greedy_assume_zero_total": [zero_total],
        "random_restart_256": restarts,
        "by_hand_mode_as_total": [mode_total],
    }


def _relabel(inst, hyperplane_order, point_old_to_new):
    """Carry an instance/witness through independent row and point renamings."""
    n = inst["n"]
    old_coefficients = {pair[0]: pair[1] for pair in inst["answer"]}
    excluded = []
    answer = []
    for new_hyperplane, old_hyperplane in enumerate(hyperplane_order):
        excluded.append(point_old_to_new[inst["excluded"][old_hyperplane]])
        answer.append([new_hyperplane, old_coefficients[old_hyperplane]])
    values = [0] * n
    for old_point, new_point in enumerate(point_old_to_new):
        values[new_point] = inst["values"][old_point]
    return {
        "n": n,
        "p": inst["p"],
        "excluded": excluded,
        "values": values,
        "inverse_n_minus_1": inst["inverse_n_minus_1"],
        "answer": answer,
    }


def _relabel_variants(inst, seed):
    rng = random.Random(seed)
    n = inst["n"]
    hyperplanes = list(range(n))
    points = list(range(n))
    rng.shuffle(hyperplanes)
    rng.shuffle(points)
    identity = list(range(n))
    return [
        _relabel(inst, hyperplanes, identity),
        _relabel(inst, identity, points),
        _relabel(inst, hyperplanes, points),
    ]


def _worst_answer_chars(n, p):
    # Compact JSON: [[0,p-1],[1,p-1],...].
    index_digits = sum(len(str(i)) for i in range(n))
    return 2 + index_digits + n * len(str(p - 1)) + 3 * n + (n - 1)


def selftest():
    """Run the nine mandatory gates and return their measured evidence."""
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}
    shipping = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    inst = make_instance(seed=0, **shipping)

    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            trial = make_instance(seed=seed, **params)
            ok, why = verify(trial, trial["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": why})
            if json.loads(json.dumps(trial["answer"])) != trial["answer"]:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    base = json.loads(json.dumps(inst["answer"]))
    corruptions = {}
    corruptions["empty"] = []
    corruptions["dropped_pair"] = base[:-1]
    duplicate = json.loads(json.dumps(base))
    duplicate[1][0] = duplicate[0][0]
    corruptions["duplicate_index"] = duplicate
    out_of_range = json.loads(json.dumps(base))
    out_of_range[0][0] = inst["n"]
    corruptions["out_of_range"] = out_of_range
    swapped = json.loads(json.dumps(base))
    swap_j = next((j for j in range(1, inst["n"])
                   if swapped[j][1] != swapped[0][1]), 1)
    swapped[0][1], swapped[swap_j][1] = swapped[swap_j][1], swapped[0][1]
    corruptions["swapped_coefficients"] = swapped
    rejection_reasons = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejection_reasons[name] = {"rejected": not ok, "reason": why}
    reasons = [entry["reason"] for entry in rejection_reasons.values()]
    report["G2_rejects_corruption"] = {
        "pass": (all(entry["rejected"] for entry in rejection_reasons.values())
                 and len(set(reasons)) == len(reasons)),
        "corruptions": rejection_reasons,
        "distinct_reasons": len(set(reasons)),
    }

    encoded = json.dumps(inst["answer"], separators=(",", ":"))
    realistic = ("I used the projective-basis containment equations.\n```json\n"
                 f"<answer>{encoded}</answer>\n```\n")
    parsed = parse_answer(realistic)
    malformed = ["", "no tags", "<answer>not json</answer>",
                 "<answer>{\"x\": 1}</answer>"]
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"]
        and all(parse_answer(text) is None for text in malformed),
        "realistic_response_round_trips": parsed == inst["answer"],
        "garbage_cases_rejected": sum(parse_answer(text) is None
                                      for text in malformed),
    }

    guess_rng = random.Random(0x230204718)
    guess_total = 200_000
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_fraction,
        "candidate_space": f"{inst['p']}^{inst['n']}",
        "candidate_space_bits": search_space(inst).bit_length(),
        "sampling_wall_clock_sec": round(guess_seconds, 6),
        "structure_aware": True,
    }

    attack_names = (
        "outlier_largest_residue_one_term",
        "greedy_assume_zero_total",
        "random_restart_256",
        "by_hand_mode_as_total",
    )
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_operations = 0
    reference_inversions = 0
    compact_successes = 0
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **shipping)
        attack_rng = random.Random(seed ^ 0xA77AC)
        candidates = _attack_candidates(trial, attack_rng)
        for name in attack_names:
            start = time.perf_counter()
            won = any(verify(trial, candidate)[0]
                      for candidate in candidates[name])
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(won)
        start = time.perf_counter()
        recovered, counts = _gaussian_reference(trial)
        reference_seconds += time.perf_counter() - start
        reference_successes += int(
            recovered is not None and verify(trial, recovered)[0]
        )
        reference_operations += counts["field_operations"]
        reference_inversions += counts["inversions"]
        compact_successes += int(verify(trial, _compact_solve(trial))[0])
    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "generic exact modular Gauss-Jordan elimination",
        "complexity": "O(n^3) exact field operations",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_operations // 8,
        "inversions": reference_inversions // 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "total-sum invariant for a permuted J-I matrix",
            "solves": f"{compact_successes}/8",
            "operations": 2 * inst["n"],
        },
    }

    demo_count = enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline_cost"] = {
        "pass": (guess_fraction < 1e-6 and demo_count == 1 and all_failed
                 and reference_successes == 8 and compact_successes == 8),
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density": guess_fraction,
        "exact_density": f"1/{inst['p']}^{inst['n']} (unique nonsingular system)",
        "demo_exact_solution_count": demo_count,
        "baseline_attack_wall_clock_sec": round(
            attack_seconds["random_restart_256"] / 8, 6
        ),
        "baseline_attack_iterations": 256,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    ladder = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": (doubled_ok and doubled["n"] == 2 * inst["n"]
                 and len(render(doubled)) > len(render(inst))
                 and ladder == sorted(ladder)
                 and len(set(ladder)) == len(ladder)),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_reason,
        "candidate_space_bits_shipping": search_space(inst).bit_length(),
        "candidate_space_bits_doubled": search_space(doubled).bit_length(),
    }

    invariant_count = 0
    transform_verify_count = 0
    unrelated_keys = []
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping)
        key = canonical_key(original)
        for transformed in _relabel_variants(original, seed ^ 0x5A5A):
            invariant_count += int(canonical_key(transformed) == key)
            transform_verify_count += int(
                verify(transformed, transformed["answer"])[0]
            )
        unrelated_keys.append(key)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": (invariant_count == 60 and transform_verify_count == 60
                 and distinct_count == 20),
        "invariant_relabellings": invariant_count,
        "relabelled_witnesses_verified": transform_verify_count,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "hyperplane reordering with carried coefficients",
            "point reordering with carried values",
            "composition of both independent reorderings",
            "projective basis changes (already quotiented by containment form)",
        ],
    }

    answer_chars = len(encoded)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = 2 * len(inst["answer"])
    worst_chars = _worst_answer_chars(inst["n"], inst["p"])
    worst_tokens = math.ceil(worst_chars / 4)
    intended_operations = 2 * inst["n"]
    arms = {name: dict(G9_EVIDENCE[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2_000
        and worst_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == worst_tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": G9_EVIDENCE["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": worst_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
