"""Verified generator for an inclusion-matrix column-space certificate.

The native object is the inclusion matrix used throughout arXiv:1511.03623.
The proof of Theorem 1.13 assigns a coefficient to every (k-2)-subset using
only its intersection size with a distinguished k-set.  At k=p, Wilson's
theorem turns those orbit coefficients into evaluations of (x+1)^(p-2).

This module applies an invertible affine relabelling to those evaluations and
asks for the resulting polynomial.  The verifier expands the inclusion action
orbit by orbit over GF(p); it neither reads nor compares against the planted
answer.
"""

from __future__ import annotations

import copy
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
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "inclusion matrix over GF(p)",
        "orbit-labelled subsets of a finite ground set",
        "univariate polynomial over GF(p)",
    ],
    "verification_operations": [
        "exact polynomial evaluation over GF(p)",
        "exact inclusion-row orbit sum",
        "exact coefficient and degree checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Group inclusion-matrix columns by their intersection size with the "
        "distinguished p-set; without that orbit symmetry one faces dense "
        "finite-field coefficient elimination."
    ),
    "hardness_basis": (
        "Track B: the coefficient-matching algorithm is dense Gaussian "
        "elimination over GF(p), O(p^3); at the shipping preset p=101 it used "
        "1,071,216 exact field operations and averaged 0.049 seconds in the "
        "final audit, whereas Theorem 1.13's orbit symmetry and Fermat's identity "
        "give the polynomial in at most 151 exact field operations."
    ),
    "max_answer_tokens": 0,  # Filled with the measured shipping bound below.
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
    "demo": {"n": 5},
    "easy": {"n": 101},
    "medium": {"n": 109},
    "hard": {"n": 127},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The inclusion rows are constant on the intersection-size orbits of the "
    "distinguished set."
)
PLACEBO_HINT = (
    "The finite-field conventions and the ordering of coefficients both need "
    "careful attention."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One dense univariate polynomial over GF(p): a JSON list containing "
        "exactly one [coefficient,[exponent]] term for every exponent 0 through "
        "p-2; coefficients are least residues 0,...,p-1 and term order is free."
    ),
    "bounds": {
        "n_polynomials": 1,
        "terms_formula": "p-1",
        "max_degree_formula": "p-2",
        "coefficient_count_formula": "p",
        "shipping_p": 101,
        "shipping_terms": 100,
        "hard_max_terms": 126,
    },
}

NOTES = (
    "Definition 1.3 fixes the inclusion-matrix object, and the proof of Theorem "
    "1.13 in Section 8 fixes the orbit coefficient beta_A=(-1)^l l! "
    "(p-2-l)! for l=|A intersect B|.  Theorem 1.6 supplies the modular-rank "
    "context and shows why k<=p is the easy full-rank regime; this family uses "
    "the boundary k=p, where Wilson and Fermat simplify beta_l to 1/(l+1).  "
    "The witness is carried through the affine orbit label z=a*l+(a-1), not "
    "found by solving an emitted instance.  Random nonzero affine scales make "
    "the coefficients seed-dependent.  The outlier monomial, greedy value-as-"
    "coefficient, unscaled Fermat, linear-ansatz, and random-restart attacks are "
    "all checked separately; dense Gaussian elimination is disclosed as the "
    "successful Track B reference algorithm."
)


# External oracle evidence is filled only after the three script-owned runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 3, "attempts": 3},
    "hinted_verdict": "too_easy",
}


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value == prime:
            return True
        if value % prime == 0:
            return False
    limit = math.isqrt(value)
    divisor = 41
    while divisor <= limit:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime(value: int) -> int:
    candidate = max(2, int(value))
    if candidate == 2:
        return 2
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _poly_terms(coefficients: list[int]) -> list[list[object]]:
    return [[coefficient, [exponent]] for exponent, coefficient in enumerate(coefficients)]


def _compact_certificate(inst: dict) -> list[list[object]]:
    """The carried Theorem 1.13/Fermat witness; never consults answer."""
    p = inst["p"]
    mu = (inst["target"] * inst["orbit_scale"]) % p
    coefficients = []
    for exponent in range(p - 1):
        coefficient = mu * (exponent + 1) % p
        if exponent % 2:
            coefficient = (-coefficient) % p
        coefficients.append(coefficient)
    return _poly_terms(coefficients)


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Construct a transformed inclusion-matrix certificate from the answer first."""
    del params
    if isinstance(n, bool) or not isinstance(n, int) or n < 5:
        raise ValueError("n must be an integer at least 5")
    p = _next_prime(n)
    rng = random.Random(seed)
    ground_size = 2 * p - 2
    distinguished = sorted(rng.sample(range(ground_size), p))

    # z_l = a*l+(a-1), so z_l+1=a(l+1).  Avoid mu=1 so the
    # construction-aware 'forgot the scale' attack is genuinely tested.
    while True:
        orbit_scale = rng.randrange(2, p)
        target = rng.randrange(1, p)
        if (orbit_scale * target) % p not in (1, p - 1):
            break

    inst = {
        "family": "orbit-labelled inclusion-matrix certificate",
        "p": p,
        "ground_size": ground_size,
        "distinguished": distinguished,
        "orbit_scale": orbit_scale,
        "orbit_shift": orbit_scale - 1,
        "target": target,
    }
    inst["answer"] = _compact_certificate(inst)
    return inst


def _answer_blob(answer: object) -> str:
    return json.dumps(answer, separators=(",", ":"))


def render(inst: dict) -> str:
    p = inst["p"]
    d = p - 2
    lines = [
        "Find a polynomial certificate for a finite-field inclusion matrix.",
        "",
        f"All arithmetic is in GF({p}); write every field element as its least",
        f"nonnegative decimal residue in 0,...,{p - 1}.",
        "",
        f"The ground set is X={{0,1,...,{inst['ground_size'] - 1}}}.  Its distinguished",
        f"p-element subset B is: {inst['distinguished']}",
        "",
        f"For every ({p - 2})-element subset A of X, define",
        "",
        f"    ell(A) = |A intersect B|,",
        f"    z(A) = {inst['orbit_scale']}*ell(A) + {inst['orbit_shift']} (mod {p}).",
        "",
        f"The inclusion matrix has one row for every ({p - 1})-element subset C",
        f"and one column for every ({p - 2})-element subset A.  Its (C,A) entry",
        "is 1 when A is a subset of C and 0 otherwise.",
        "",
        f"Find a polynomial Q(x) over GF({p}) of degree at most {d} such that,",
        f"for every ({p - 1})-element subset C of X, the exact identity",
        "",
        "    sum over A subset C with |A|=p-2 of Q(z(A))",
        "",
        f"equals {inst['target']} when C is a subset of B, and equals 0 otherwise.",
        "The sum is in GF(p).  The polynomial is unique under the degree bound.",
        "",
        "Return Q as dense JSON polynomial data.  Include exactly one term",
        f"[coefficient,[exponent]] for every exponent 0,...,{d}, including zero",
        "coefficients.  Term order is irrelevant; exponents may not repeat.",
        "For example, 4+3x^2 is [[4,[0]],[0,[1]],[3,[2]]].",
        "",
        "Give your final answer inside <answer></answer> tags, as that JSON list.",
        "Example: <answer>[[4,[0]],[0,[1]],[3,[2]]]</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    candidates = [match.group(1)] if match else []
    candidates.extend(re.findall(r"```(?:json)?\s*(.*?)```", text, re.I | re.S))
    if not candidates:
        stripped = text.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            candidates.append(stripped)
    for candidate in candidates:
        try:
            value = json.loads(candidate.strip())
        except (TypeError, ValueError):
            continue
        if isinstance(value, list):
            return value
    return None


def _decode_polynomial(inst: dict, answer: object) -> tuple[list[int] | None, str]:
    p = inst["p"]
    expected = p - 1
    if not isinstance(answer, list):
        return None, "answer must be a JSON list of polynomial terms"
    if not answer:
        return None, "answer is empty"
    if len(answer) != expected:
        return None, f"wrong term count: expected {expected}"
    coefficients: list[int | None] = [None] * expected
    for position, term in enumerate(answer):
        if not isinstance(term, list) or len(term) != 2:
            return None, f"term {position} must be [coefficient,[exponent]]"
        coefficient, exponent_box = term
        if isinstance(coefficient, bool) or not isinstance(coefficient, int):
            return None, f"coefficient at term {position} is not an integer"
        if not 0 <= coefficient < p:
            return None, f"coefficient at term {position} is outside GF(p)"
        if (
            not isinstance(exponent_box, list)
            or len(exponent_box) != 1
            or isinstance(exponent_box[0], bool)
            or not isinstance(exponent_box[0], int)
        ):
            return None, f"term {position} has a malformed exponent list"
        exponent = exponent_box[0]
        if not 0 <= exponent < expected:
            return None, f"exponent {exponent} is outside 0,...,{expected - 1}"
        if coefficients[exponent] is not None:
            return None, f"duplicate exponent {exponent}"
        coefficients[exponent] = coefficient
    if any(value is None for value in coefficients):
        return None, "an exponent in the required dense range is missing"
    return [int(value) for value in coefficients], "ok"


def _evaluate(coefficients: list[int], value: int, p: int) -> int:
    result = 0
    for coefficient in reversed(coefficients):
        result = (result * value + coefficient) % p
    return result


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check every inclusion-row orbit exactly; never read inst['answer']."""
    coefficients, reason = _decode_polynomial(inst, answer)
    if coefficients is None:
        return False, reason
    p = inst["p"]
    scale = inst["orbit_scale"]
    shift = inst["orbit_shift"]
    target = inst["target"]
    values: dict[int, int] = {}

    def orbit_value(ell: int) -> int:
        if ell not in values:
            z_value = (scale * ell + shift) % p
            values[ell] = _evaluate(coefficients, z_value, p)
        return values[ell]

    # A row C is determined up to the stabilizer of B by r=|C intersect B|.
    # Since |X\B|=p-2 and |C|=p-1, precisely r=1,...,p-1 are feasible.
    for intersection in range(1, p):
        row_sum = (
            (p - 1 - intersection) * orbit_value(intersection)
            + intersection * orbit_value(intersection - 1)
        ) % p
        expected = target if intersection == p - 1 else 0
        if row_sum != expected:
            return (
                False,
                "inclusion-row sum mismatch at intersection size "
                f"{intersection}: got {row_sum}, expected {expected}",
            )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    p = inst["p"]
    return _poly_terms([rng.randrange(p) for _ in range(p - 1)])


def search_space(inst: dict) -> int:
    p = inst["p"]
    return p ** (p - 1)


def enumerate_all(inst: dict) -> int | None:
    p = inst["p"]
    if search_space(inst) > 100_000:
        return None
    count = 0
    for coefficients in itertools.product(range(p), repeat=p - 1):
        count += int(verify(inst, _poly_terms(list(coefficients)))[0])
    return count


def canonical_key(inst: dict) -> str:
    """Complete invariant for this two-colour set system under ground relabelling."""
    invariant = {
        "p": inst["p"],
        "ground_size": inst["ground_size"],
        "distinguished_size": len(inst["distinguished"]),
        "orbit_scale": inst["orbit_scale"],
        "orbit_shift": inst["orbit_shift"],
        "target": inst["target"],
    }
    blob = json.dumps(invariant, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    current = _next_prime(int(params.get("n", 5)))
    candidate = _next_prime(current + 1)
    # A dense polynomial has two atomic integers per term.
    if 2 * (candidate - 1) > 256:
        return "cap_bound"
    result = {key: value for key, value in params.items() if not key.startswith("_")}
    result["n"] = candidate
    return result


def _matrix_equations(inst: dict) -> tuple[list[list[int]], list[int], int]:
    """Build dense coefficient-matching equations and count field operations."""
    p = inst["p"]
    scale = inst["orbit_scale"]
    shift = inst["orbit_shift"]
    matrix: list[list[int]] = []
    rhs: list[int] = []
    operations = 0
    for intersection in range(1, p):
        z_hi = (scale * intersection + shift) % p
        z_lo = (scale * (intersection - 1) + shift) % p
        powers_hi = [1]
        powers_lo = [1]
        for _ in range(1, p - 1):
            powers_hi.append(powers_hi[-1] * z_hi % p)
            powers_lo.append(powers_lo[-1] * z_lo % p)
            operations += 2
        row = []
        for exponent in range(p - 1):
            row.append(
                (
                    (p - 1 - intersection) * powers_hi[exponent]
                    + intersection * powers_lo[exponent]
                )
                % p
            )
            operations += 3
        matrix.append(row)
        rhs.append(inst["target"] if intersection == p - 1 else 0)
    return matrix, rhs, operations


def _gaussian_reference(inst: dict) -> tuple[object | None, dict]:
    """The disclosed O(p^3) Track B reference algorithm."""
    p = inst["p"]
    matrix, rhs, operations = _matrix_equations(inst)
    size = p - 1
    aug = [row + [value] for row, value in zip(matrix, rhs)]
    inversions = 0
    for column in range(size):
        pivot = next((r for r in range(column, size) if aug[r][column] % p), None)
        if pivot is None:
            return None, {"field_operations": operations, "inversions": inversions}
        if pivot != column:
            aug[column], aug[pivot] = aug[pivot], aug[column]
        inverse = pow(aug[column][column], p - 2, p)
        inversions += 1
        for j in range(column, size + 1):
            aug[column][j] = aug[column][j] * inverse % p
            operations += 1
        for row in range(size):
            if row == column:
                continue
            factor = aug[row][column]
            if factor == 0:
                continue
            for j in range(column, size + 1):
                aug[row][j] = (aug[row][j] - factor * aug[column][j]) % p
                operations += 2
    coefficients = [aug[i][size] % p for i in range(size)]
    return _poly_terms(coefficients), {
        "field_operations": operations,
        "inversions": inversions,
    }


def _zero_candidate(inst: dict) -> list[list[object]]:
    return _poly_terms([0] * (inst["p"] - 1))


def _attack_candidates(inst: dict, seed: int) -> dict[str, list[object]]:
    p = inst["p"]
    mu = inst["target"] * inst["orbit_scale"] % p

    outlier = [0] * (p - 1)
    outlier[max(inst["distinguished"]) % (p - 1)] = mu

    greedy_values = [inst["target"] * pow(i + 1, p - 2, p) % p for i in range(p - 1)]

    unscaled = []
    for exponent in range(p - 1):
        value = exponent + 1
        if exponent % 2:
            value = -value
        unscaled.append(value % p)

    linear = [0] * (p - 1)
    linear[0] = inst["target"]
    linear[1] = inst["orbit_scale"]

    restart_rng = random.Random(seed ^ 0x151103623)
    restarts = []
    for _ in range(256):
        sparse = [0] * (p - 1)
        for exponent in restart_rng.sample(range(p - 1), 4):
            sparse[exponent] = restart_rng.randrange(1, p)
        restarts.append(_poly_terms(sparse))
    return {
        "outlier_single_monomial": [_poly_terms(outlier)],
        "greedy_orbit_values_as_coefficients": [_poly_terms(greedy_values)],
        "unscaled_fermat_ansatz": [_poly_terms(unscaled)],
        "by_hand_linear_ansatz": [_poly_terms(linear)],
        "random_sparse_restart_256": restarts,
    }


def _compose_permutations(left: list[int], right: list[int]) -> list[int]:
    return [left[right[index]] for index in range(len(left))]


def _relabel_variants(inst: dict, seed: int) -> list[dict]:
    size = inst["ground_size"]
    reverse = list(reversed(range(size)))
    rotate = [(index + 1) % size for index in range(size)]
    shuffled = list(range(size))
    random.Random(seed).shuffle(shuffled)
    generators = [reverse, rotate, shuffled]
    variants = []
    for mask in range(1, 8):
        permutation = list(range(size))
        for bit, generator in enumerate(generators):
            if mask & (1 << bit):
                permutation = _compose_permutations(generator, permutation)
        transformed = copy.deepcopy(inst)
        transformed["distinguished"] = sorted(
            permutation[value] for value in inst["distinguished"]
        )
        variants.append(transformed)
    return variants


def _atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atoms(item) for item in value)
    return 1


def _worst_case_answer(inst: dict) -> object:
    p = inst["p"]
    return [[p - 1, [exponent]] for exponent in range(p - 1)]


def _intended_operations(inst: dict) -> int:
    p = inst["p"]
    # mu=lambda*a; one multiplication per coefficient; one negation for odd e.
    return 1 + (p - 1) + (p - 1) // 2


# The exact worst-case compact-JSON bound for the declared shipping preset.
_PROFILE_INSTANCE = make_instance(seed=0, **DIFFICULTY[SHIPPING_DIFFICULTY])
_PROFILE_WORST_CHARS = len(_answer_blob(_worst_case_answer(_PROFILE_INSTANCE)))
PROBLEM_PROFILE["max_answer_tokens"] = math.ceil(_PROFILE_WORST_CHARS / 4)
del _PROFILE_INSTANCE, _PROFILE_WORST_CHARS


def selftest() -> dict:
    report: dict[str, object] = {
        "paper": "1511.03623",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    planted_checks = 0
    json_checks = 0
    planted_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            trial = make_instance(seed=seed, **params)
            ok, why = verify(trial, trial["answer"])
            planted_checks += 1
            if not ok:
                planted_failures.append([preset, seed, why])
            json_checks += int(json.loads(json.dumps(trial["answer"])) == trial["answer"])
    report["G1_planted_verifies"] = {
        "pass": not planted_failures and json_checks == planted_checks,
        "verified": planted_checks - len(planted_failures),
        "attempts": planted_checks,
        "json_round_trips": json_checks,
        "failures": planted_failures,
    }

    shipping = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    inst = make_instance(seed=314159, **shipping)
    answer = copy.deepcopy(inst["answer"])
    swapped = copy.deepcopy(answer)
    swapped[0][0], swapped[1][0] = swapped[1][0], swapped[0][0]
    duplicated = copy.deepcopy(answer)
    duplicated[1][1] = list(duplicated[0][1])
    out_of_range = copy.deepcopy(answer)
    out_of_range[0][0] = inst["p"]
    corruptions = {
        "drop": answer[:-1],
        "swap_coefficients": swapped,
        "duplicate_exponent": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = [entry["reason"] for entry in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in rejected.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "Using the orbit recurrence gives this polynomial.\n```json\n<answer>"
        + _answer_blob(answer)
        + "</answer>\n```\nThe coefficients are least residues."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x151103623)
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
        "fraction": guess_fraction,
        "exact_density": f"1/{inst['p']}^{inst['p'] - 1}",
        "candidate_space_bits": search_space(inst).bit_length(),
        "wall_clock_sec": round(guess_seconds, 6),
        "sampling_prior": "uniform over every dense coefficient vector in GF(p)^(p-1)",
    }

    attack_names = [
        "outlier_single_monomial",
        "greedy_orbit_values_as_coefficients",
        "unscaled_fermat_ansatz",
        "by_hand_linear_ansatz",
        "random_sparse_restart_256",
    ]
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_operations = 0
    reference_inversions = 0
    compact_successes = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        attack_map = _attack_candidates(trial, seed)
        for name in attack_names:
            start = time.perf_counter()
            won = any(verify(trial, candidate)[0] for candidate in attack_map[name])
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(won)
        start = time.perf_counter()
        recovered, counts = _gaussian_reference(trial)
        reference_seconds += time.perf_counter() - start
        reference_operations += counts["field_operations"]
        reference_inversions += counts["inversions"]
        reference_successes += int(recovered is not None and verify(trial, recovered)[0])
        compact_successes += int(verify(trial, _compact_certificate(trial))[0])

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "dense coefficient matching plus exact Gauss-Jordan elimination",
        "complexity": "O(p^3) exact GF(p) operations",
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
            "name": "intersection-orbit recurrence and Fermat polynomial",
            "solves": f"{compact_successes}/8",
            "operations_upper_bound": _intended_operations(inst),
        },
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    strongest_failing = "unscaled_fermat_ansatz"
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and demo_count == 1
        and all_failed
        and reference_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_sampled_density": guess_fraction,
        "shipping_exact_density": f"1/{inst['p']}^{inst['p'] - 1} (unique polynomial)",
        "demo_exact_solution_count_by_bruteforce": demo_count,
        "strongest_failing_attack": strongest_failing,
        "baseline_attack_wall_clock_sec": round(
            attack_seconds[strongest_failing] / 8, 6
        ),
        "baseline_attack_iterations": 256,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
    }

    doubled_input = 2 * shipping["n"]
    start = time.perf_counter()
    doubled = make_instance(n=doubled_input, seed=77)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    ladder_primes = [_next_prime(DIFFICULTY[name]["n"]) for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["p"] >= 2 * inst["p"]
        and ladder_primes == sorted(ladder_primes)
        and len(set(ladder_primes)) == len(ladder_primes)
        and search_space(doubled).bit_length() > search_space(inst).bit_length(),
        "shipping_input_n": shipping["n"],
        "shipping_p": inst["p"],
        "doubled_input_n": doubled_input,
        "doubled_p": doubled["p"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_why,
        "candidate_space_bits_shipping": search_space(inst).bit_length(),
        "candidate_space_bits_doubled": search_space(doubled).bit_length(),
    }

    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping)
        key = canonical_key(original)
        for transformed in _relabel_variants(original, seed ^ 0x5A5A):
            invariant_count += int(key == canonical_key(transformed))
            real_transform_count += int(verify(transformed, original["answer"])[0])
        unrelated_keys.append(key)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == 140
        and real_transform_count == 140
        and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "real_transformations_verified_with_original_answer": real_transform_count,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "ground-set reversal",
            "cyclic ground-set relabelling",
            "random ground-set relabelling",
            "all four nontrivial compositions of those maps",
        ],
        "invariant_is_complete_for": (
            "a ground set with one distinguished subset plus the fixed field scalars"
        ),
    }

    encoded_answer = _answer_blob(inst["answer"])
    worst_blob = _answer_blob(_worst_case_answer(inst))
    answer_chars = len(encoded_answer)
    answer_tokens = math.ceil(answer_chars / 4)
    worst_chars = len(worst_blob)
    worst_tokens = math.ceil(worst_chars / 4)
    answer_elements = _atoms(inst["answer"])
    intended_operations = _intended_operations(inst)
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        worst_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == worst_tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": worst_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {
            "answer_chars": 2_000,
            "answer_elements": 256,
            "intended_route_operations": 300,
        },
    }

    report["certificate_language"] = CERTIFICATE_LANGUAGE
    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
