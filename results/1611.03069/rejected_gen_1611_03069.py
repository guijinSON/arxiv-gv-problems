"""Exact planted Reed--Solomon bounded-distance decoding instances.

The native problem is the RS-BDD / polynomial-reconstruction problem defined in
the Introduction and Theorem 1 of arXiv:1611.03069.  Certificates are sampled
first as polynomials over a prime field.  Each instance is then made from full
nine-point multiplicative orbits and four same-distribution errors per orbit.

This is deliberately Track B.  The instances lie in the classical unique-
decoding radius, so Berlekamp--Welch is an efficient reference algorithm.  The
benchmark asks whether a no-tool solver notices a much shorter equivariance
route; it makes no average-case NP-hardness claim.
"""

from __future__ import annotations

import hashlib
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
        "Reed-Solomon evaluation points over a prime field",
        "received word over the same field",
        "low-degree polynomial over the prime field",
    ],
    "verification_operations": [
        "exact finite-field polynomial evaluation",
        "exact Hamming-distance comparison",
        "integer range and coefficient-count checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Multiplication by a ninth root of unity organizes clean evaluations into "
        "equivariant triples; without recognizing those orbits one must decode the "
        "full Reed-Solomon word."
    ),
    "hardness_basis": (
        "Track B: the Introduction's unique-decoding result permits the "
        "Berlekamp-Welch algorithm, O(N^3) field operations; at the medium preset "
        "it used at most 15,134,479 counted field operations and averaged 0.553 "
        "seconds over eight runs, while the orbit route takes 108 exact field "
        "operations."
    ),
    "max_answer_tokens": 17,
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

# n is the number of multiplicative orbits.  From easy onward the answer has
# exactly 20 coefficients; escalation grows only the received word (haystack).
DIFFICULTY = {
    "demo": {"n": 5, "q_degree": 1, "prime": 1009, "orbit_order": 3},
    "easy": {"n": 24, "q_degree": 2, "prime": 1009, "orbit_order": 9},
    "medium": {"n": 32, "q_degree": 2, "prime": 1009, "orbit_order": 9},
    "hard": {"n": 40, "q_degree": 2, "prime": 1009, "orbit_order": 9},
}
SHIPPING_DIFFICULTY = "medium"

if os.environ.get("GV_G9_SINGLE") == "1":
    DIFFICULTY = {
        SHIPPING_DIFFICULTY: dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    }

STRUCTURAL_HINT = (
    "Multiplication by 759 forms nine-point evaluation orbits on which the clean "
    "ratios y/x are constant."
)
PLACEBO_HINT = (
    "Careful bookkeeping of every displayed field element helps prevent avoidable "
    "arithmetic mistakes."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object with exactly K coefficients [c_0,...,c_(K-1)] in GF(p), "
        "each represented by its canonical integer 0<=c_i<p; it denotes the "
        "polynomial sum c_i X^i of degree below K."
    ),
    "bounds": {
        "coefficient_count": "K = orbit_order*q_degree + 2",
        "coefficient_min": 0,
        "coefficient_max": "prime - 1",
        "shipping_coefficient_count": 20,
        "shipping_prime": 1009,
    },
}

NOTES = (
    "The Introduction fixes RS(D,K), Hamming distance, and BDD(d), and restates "
    "BDD as polynomial reconstruction.  Theorem 1 gives NP-hardness only near "
    "the covering radius and therefore does not justify random planted hardness. "
    "The same Introduction identifies the easy regimes: unique decoding through "
    "(N-K)/2 errors and Sudan/Guruswami-Sudan list decoding through the Johnson "
    "radius.  This generator intentionally stays in the former regime and declares "
    "Track B.  It samples the polynomial before the received word, uses a uniform "
    "field error in each multiplicative orbit, and never decodes while generating. "
    "Errors and clean symbols have the same one-coordinate marginal distribution. "
    "The per-symbol outlier, input-order greedy, low-degree ansatz, and 256-restart "
    "interpolation attacks are measured in selftest; exact Berlekamp-Welch is "
    "reported separately as the successful reference algorithm."
)

# Filled from the script-owned oracle runs before the final report is emitted.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 3, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "too_easy",
}


def _is_prime(value):
    if not isinstance(value, int) or isinstance(value, bool) or value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    limit = math.isqrt(value)
    divisor = 3
    while divisor <= limit:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime_one_mod_order(lower, order):
    candidate = max(7, int(lower))
    candidate += (1 - candidate) % order
    while not _is_prime(candidate):
        candidate += order
    return candidate


def _prime_factors(value):
    factors = set()
    divisor = 2
    while divisor * divisor <= value:
        while value % divisor == 0:
            factors.add(divisor)
            value //= divisor
        divisor += 1
    if value > 1:
        factors.add(value)
    return factors


def _root_of_unity(prime, order):
    if order < 3 or order % 2 == 0 or (prime - 1) % order:
        raise ValueError("orbit_order must be odd, at least 3, and divide prime-1")
    exponent = (prime - 1) // order
    for base in range(2, prime):
        omega = pow(base, exponent, prime)
        if (pow(omega, order, prime) == 1
                and all(pow(omega, order // factor, prime) != 1
                        for factor in _prime_factors(order))):
            return omega
    raise ValueError("no root of the requested exact order found")


def _eval_poly(coefficients, x, prime):
    value = 0
    for coefficient in reversed(coefficients):
        value = (value * x + coefficient) % prime
    return value


def _orbit_representatives(prime, omega, order):
    unused = set(range(1, prime))
    representatives = []
    while unused:
        x = min(unused)
        orbit = {(pow(omega, exponent, prime) * x) % prime
                 for exponent in range(order)}
        if len(orbit) != order:
            raise AssertionError("root-of-unity orbit has the wrong size")
        unused.difference_update(orbit)
        representatives.append(min(orbit))
    return representatives


def make_instance(n, seed=0, q_degree=2, prime=1009, orbit_order=9):
    """Inverse-generate an exact RS-BDD instance and its polynomial witness."""
    if not all(isinstance(v, int) and not isinstance(v, bool)
               for v in (n, seed, q_degree, prime, orbit_order)):
        raise ValueError("all generation parameters must be integers")
    if q_degree < 1:
        raise ValueError("q_degree must be positive")
    if not _is_prime(prime) or (prime - 1) % orbit_order:
        raise ValueError("prime must be prime with orbit_order dividing prime-1")

    dimension = orbit_order * q_degree + 2
    if n < dimension:
        raise ValueError("n must be at least the Reed-Solomon dimension")
    omega = _root_of_unity(prime, orbit_order)
    representatives = _orbit_representatives(prime, omega, orbit_order)
    if n > len(representatives):
        raise ValueError("n exceeds the number of nonzero cube-root orbits")

    rng = random.Random(seed)
    chosen = rng.sample(representatives, n)

    # Sample the certificate first.  p(X)=X*q(X^orbit_order), but the answer is the
    # ordinary dense coefficient vector demanded by the native RS problem.
    q_coefficients = [rng.randrange(prime) for _ in range(q_degree)]
    q_coefficients.append(rng.randrange(1, prime))
    coefficients = [0] * dimension
    for index, coefficient in enumerate(q_coefficients):
        coefficients[1 + orbit_order * index] = coefficient

    points = []
    for representative in chosen:
        orbit = [(pow(omega, exponent, prime) * representative) % prime
                 for exponent in range(orbit_order)]
        rng.shuffle(orbit)
        error_positions = set(rng.sample(
            range(orbit_order), (orbit_order - 1) // 2
        ))
        clean_ratio = None
        used_error_ratios = set()
        for position, x in enumerate(orbit):
            correct = _eval_poly(coefficients, x, prime)
            y = correct
            if clean_ratio is None:
                clean_ratio = correct * pow(x, -1, prime) % prime
            if position in error_positions:
                ratio = rng.randrange(prime)
                while ratio == clean_ratio or ratio in used_error_ratios:
                    ratio = rng.randrange(prime)
                used_error_ratios.add(ratio)
                y = x * ratio % prime
            points.append([x, y])
    rng.shuffle(points)

    block_length = len(points)
    radius = n * ((orbit_order - 1) // 2)
    if 2 * radius > block_length - dimension:
        raise AssertionError("instance left the unique-decoding radius")
    return {
        "prime": prime,
        "dimension": dimension,
        "radius": radius,
        "points": points,
        "q_degree": q_degree,
        "orbit_order": orbit_order,
        "answer": {"coefficients": coefficients},
    }


def render(inst):
    prime = inst["prime"]
    dimension = inst["dimension"]
    radius = inst["radius"]
    rows = "\n".join(
        f"{index}: {x} {y}" for index, (x, y) in enumerate(inst["points"])
    )
    text = f"""Decode a Reed-Solomon word over the prime field GF({prime}).

All additions, multiplications, powers, and polynomial evaluations are modulo
{prime}.  The received word consists of N={len(inst['points'])} pairs (x,y)
listed below.  All x values are distinct field elements.  A polynomial
p(X)=c_0+c_1 X+...+c_{dimension - 1} X^{dimension - 1} has dimension bound
K={dimension}: its degree is strictly less than {dimension}, with leading zero
coefficients allowed.  Its Hamming distance from the received word is the
number of displayed pairs for which p(x) is not equal to y.

Find any polynomial of degree less than {dimension} whose Hamming distance is
at most {radius}.  Supply all {dimension} coefficients in ascending-power order,
including zeros, as canonical decimal residues from 0 through {prime - 1}.
Indices before colons are only row labels and are 0-based.

Rows have the format "index: x y":
{rows}
"""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\nStructural hint: " + STRUCTURAL_HINT + "\n"
    elif mode == "placebo":
        text += "\nHint: " + PLACEBO_HINT + "\n"
    text += f"""
Give your final answer inside <answer></answer> tags, as one JSON object
{{"coefficients":[c_0,c_1,...,c_{dimension - 1}]}} containing exactly
{dimension} integers.  Example of format only (not a solution):
<answer>{{"coefficients":{json.dumps(list(range(dimension)))}}}</answer>
Output nothing else inside the tags.
"""
    return text


def parse_answer(text):
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\b[^>]*>(.*?)</answer\s*>", text,
                      flags=re.IGNORECASE | re.DOTALL)
    candidates = []
    if match:
        candidates.append(match.group(1).strip())
    candidates.extend(
        block.strip() for block in re.findall(
            r"```(?:json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL
        )
    )
    if not candidates:
        object_match = re.search(r"\{\s*\"coefficients\"\s*:\s*\[[^\]]*\]\s*\}",
                                 text, flags=re.DOTALL)
        if object_match:
            candidates.append(object_match.group(0))
    for candidate in candidates:
        candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate,
                           flags=re.IGNORECASE | re.DOTALL).strip()
        try:
            answer = json.loads(candidate)
        except (TypeError, ValueError):
            continue
        if (isinstance(answer, dict)
                and set(answer) == {"coefficients"}
                and isinstance(answer["coefficients"], list)):
            return answer
    return None


def verify(inst, answer):
    if not isinstance(answer, dict) or set(answer) != {"coefficients"}:
        return False, "answer must be an object containing only coefficients"
    coefficients = answer["coefficients"]
    if not isinstance(coefficients, list):
        return False, "coefficients must be a JSON list"
    expected = inst["dimension"]
    if len(coefficients) != expected:
        return False, f"expected {expected} coefficients, got {len(coefficients)}"
    prime = inst["prime"]
    for index, coefficient in enumerate(coefficients):
        if not isinstance(coefficient, int) or isinstance(coefficient, bool):
            return False, f"coefficient {index} is not an integer"
        if not 0 <= coefficient < prime:
            return False, f"coefficient {index} is outside 0..{prime - 1}"
    mismatches = 0
    for x, y in inst["points"]:
        if _eval_poly(coefficients, x, prime) != y:
            mismatches += 1
            if mismatches > inst["radius"]:
                return False, f"Hamming distance exceeds {inst['radius']}"
    return True, "ok"


def random_candidate(inst, rng):
    return {
        "coefficients": [
            rng.randrange(inst["prime"]) for _ in range(inst["dimension"])
        ]
    }


def search_space(inst):
    return inst["prime"] ** inst["dimension"]


def enumerate_all(inst):
    space = search_space(inst)
    if space > 1_000_000:
        return None
    count = 0
    prime = inst["prime"]
    dimension = inst["dimension"]
    for number in range(space):
        value = number
        coefficients = []
        for _ in range(dimension):
            coefficients.append(value % prime)
            value //= prime
        if verify(inst, {"coefficients": coefficients})[0]:
            count += 1
    return count


def _canonical_payload(inst):
    """Cheap invariants under row order and x -> u*x+t over GF(p)."""
    prime = inst["prime"]
    points = inst["points"]
    inv_n = pow(len(points), -1, prime)
    center = (sum(x for x, _ in points) * inv_n) % prime
    normalized_moments = []
    for power in range(1, 7):
        vector = []
        for y_power in range(7):
            total = 0
            for x, y in points:
                total += pow(y, y_power, prime) * pow((x - center) % prime,
                                                       power, prime)
            vector.append(total % prime)
        denominator = next((value for value in vector if value), None)
        if denominator is None:
            normalized_moments.append(vector)
        else:
            inverse = pow(denominator, -1, prime)
            normalized_moments.append([(value * inverse) % prime for value in vector])
    return [
        prime,
        inst["dimension"],
        inst["radius"],
        sorted(y for _, y in points),
        normalized_moments,
    ]


def canonical_key(inst):
    blob = json.dumps(_canonical_payload(inst), separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params):
    if not isinstance(params, dict):
        return None
    current_n = int(params.get("n", 0))
    q_degree = int(params.get("q_degree", 2))
    prime = int(params.get("prime", 1009))
    orbit_order = int(params.get("orbit_order", 9))
    target_n = max(current_n + 1, (3 * current_n + 1) // 2)
    if target_n > (prime - 1) // orbit_order:
        prime = _next_prime_one_mod_order(orbit_order * target_n + 1, orbit_order)
    return {"n": target_n, "q_degree": q_degree, "prime": prime,
            "orbit_order": orbit_order}


def _interpolate_coefficients(points, prime):
    """Unique degree <len(points) interpolant in the monomial basis."""
    xs = [point[0] for point in points]
    if len(set(xs)) != len(xs):
        raise ValueError("interpolation x values must be distinct")
    differences = [point[1] % prime for point in points]
    size = len(points)
    for order in range(1, size):
        for index in range(size - 1, order - 1, -1):
            numerator = (differences[index] - differences[index - 1]) % prime
            denominator = (xs[index] - xs[index - order]) % prime
            differences[index] = numerator * pow(denominator, -1, prime) % prime
    polynomial = [differences[-1]]
    for index in range(size - 2, -1, -1):
        expanded = [0] * (len(polynomial) + 1)
        for degree, coefficient in enumerate(polynomial):
            expanded[degree] = (expanded[degree] - xs[index] * coefficient) % prime
            expanded[degree + 1] = (expanded[degree + 1] + coefficient) % prime
        expanded[0] = (expanded[0] + differences[index]) % prime
        polynomial = expanded
    return polynomial


def _candidate_from_rows(inst, rows):
    try:
        coefficients = _interpolate_coefficients(rows, inst["prime"])
    except (ValueError, ZeroDivisionError):
        return None
    coefficients += [0] * (inst["dimension"] - len(coefficients))
    if len(coefficients) != inst["dimension"]:
        return None
    return {"coefficients": coefficients}


def _attack_greedy_input_order(inst):
    return _candidate_from_rows(inst, inst["points"][:inst["dimension"]])


def _attack_outlier_small_y(inst):
    rows = sorted(inst["points"], key=lambda point: (point[1], point[0]))
    return _candidate_from_rows(inst, rows[:inst["dimension"]])


def _attack_low_degree_ansatz(inst):
    degree = min(4, inst["dimension"] - 1)
    candidate = _candidate_from_rows(inst, inst["points"][:degree + 1])
    if candidate is None:
        return None
    candidate["coefficients"] += [0] * (
        inst["dimension"] - len(candidate["coefficients"])
    )
    return candidate


def _attack_random_restart(inst, rng, restarts=256):
    width = inst["dimension"]
    points = inst["points"]
    for _ in range(restarts):
        rows = rng.sample(points, width)
        candidate = _candidate_from_rows(inst, rows)
        if candidate is not None and verify(inst, candidate)[0]:
            return candidate
    return None


def _solve_linear_mod(matrix, rhs, prime):
    """Solve an overdetermined full-column-rank system; count field operations."""
    if not matrix:
        raise ValueError("empty system")
    rows = [list(row) + [value % prime] for row, value in zip(matrix, rhs)]
    n_rows = len(rows)
    n_cols = len(matrix[0])
    pivot_rows = []
    operations = 0
    row = 0
    for column in range(n_cols):
        pivot = next((index for index in range(row, n_rows)
                      if rows[index][column] % prime), None)
        if pivot is None:
            raise ValueError("system is rank deficient")
        rows[row], rows[pivot] = rows[pivot], rows[row]
        pivot_value = rows[row][column] % prime
        pivot_inverse = pow(pivot_value, -1, prime)
        operations += 1
        for lower in range(row + 1, n_rows):
            entry = rows[lower][column] % prime
            if not entry:
                continue
            factor = entry * pivot_inverse % prime
            operations += 1
            rows[lower][column] = 0
            for index in range(column + 1, n_cols + 1):
                rows[lower][index] = (
                    rows[lower][index] - factor * rows[row][index]
                ) % prime
                operations += 2
        pivot_rows.append(row)
        row += 1
    for lower in range(row, n_rows):
        if all(rows[lower][column] % prime == 0 for column in range(n_cols)):
            if rows[lower][-1] % prime:
                raise ValueError("system is inconsistent")
    solution = [0] * n_cols
    for column in range(n_cols - 1, -1, -1):
        pivot = pivot_rows[column]
        value = rows[pivot][-1]
        for index in range(column + 1, n_cols):
            value = (value - rows[pivot][index] * solution[index]) % prime
            operations += 2
        solution[column] = value * pow(rows[pivot][column], -1, prime) % prime
        operations += 2
    return solution, operations


def _berlekamp_welch(inst):
    """Classical unique decoder, independent of the planted symmetry."""
    prime = inst["prime"]
    dimension = inst["dimension"]
    errors = inst["radius"]
    q_count = dimension + errors
    unknowns = q_count + errors
    matrix = []
    rhs = []
    operations = 0
    for x, y in inst["points"]:
        powers = [1]
        for _ in range(max(q_count - 1, errors)):
            powers.append(powers[-1] * x % prime)
            operations += 1
        row = powers[:q_count]
        row.extend((-y * powers[index]) % prime for index in range(errors))
        operations += errors
        matrix.append(row)
        rhs.append(y * powers[errors] % prime)
        operations += 1
    solution, solve_operations = _solve_linear_mod(matrix, rhs, prime)
    operations += solve_operations
    numerator = solution[:q_count]
    locator = solution[q_count:] + [1]

    quotient = [0] * max(1, len(numerator) - len(locator) + 1)
    remainder = list(numerator)
    for degree in range(len(remainder) - 1, len(locator) - 2, -1):
        coefficient = remainder[degree] % prime
        quotient_degree = degree - (len(locator) - 1)
        quotient[quotient_degree] = coefficient
        for index, divisor_coefficient in enumerate(locator):
            remainder[quotient_degree + index] = (
                remainder[quotient_degree + index]
                - coefficient * divisor_coefficient
            ) % prime
            operations += 2
    if any(value % prime for value in remainder[:len(locator) - 1]):
        raise ValueError("Berlekamp-Welch division left a nonzero remainder")
    quotient += [0] * (dimension - len(quotient))
    if len(quotient) != dimension:
        raise ValueError("decoded polynomial has the wrong dimension")
    return {"coefficients": quotient}, operations


def _affine_transform(inst, scale, translation, reorder_seed=None):
    """Carry an RS instance and witness through x -> scale*x+translation."""
    prime = inst["prime"]
    scale %= prime
    translation %= prime
    if scale == 0:
        raise ValueError("affine scale must be nonzero")
    points = [[(scale * x + translation) % prime, y]
              for x, y in inst["points"]]
    if reorder_seed is not None:
        random.Random(reorder_seed).shuffle(points)

    source = inst["answer"]["coefficients"]
    inverse_scale = pow(scale, -1, prime)
    offset = (-translation * inverse_scale) % prime
    carried = [0] * len(source)
    for degree, coefficient in enumerate(source):
        if coefficient == 0:
            continue
        for output_degree in range(degree + 1):
            term = coefficient
            term *= math.comb(degree, output_degree)
            term *= pow(inverse_scale, output_degree, prime)
            term *= pow(offset, degree - output_degree, prime)
            carried[output_degree] = (carried[output_degree] + term) % prime
    transformed = dict(inst)
    transformed["points"] = points
    transformed["answer"] = {"coefficients": carried}
    return transformed


def _atom_count(value):
    if isinstance(value, dict):
        return sum(_atom_count(item) for item in value.values())
    if isinstance(value, list):
        return sum(_atom_count(item) for item in value)
    return 1


def _intended_operations(q_degree, orbit_order):
    groups = q_degree + 1
    divided_difference_pairs = q_degree * (q_degree + 1) // 2
    per_group = (orbit_order - 1) + orbit_order + (orbit_order - 1) + 4
    return per_group * groups + 6 * divided_difference_pairs + groups


def selftest():
    report = {}

    g1_failures = []
    g1_attempts = 0
    json_native = True
    for name, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            g1_attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append({"preset": name, "seed": seed, "reason": reason})
            try:
                json_native = json_native and (
                    json.loads(json.dumps(inst["answer"])) == inst["answer"]
                )
            except (TypeError, ValueError):
                json_native = False
    report["G1_planted_verifies"] = {
        "pass": not g1_failures and json_native,
        "attempts": g1_attempts,
        "failures": g1_failures,
        "json_native": json_native,
        "construction": "inverse generation of p(X)=X*q(X^3)",
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=19, **shipping)
    planted = inst["answer"]["coefficients"]
    corruptions = {}
    variants = {
        "drop_one_coefficient": {"coefficients": planted[:-1]},
        "swap_two_coefficients": {
            "coefficients": planted[:-2] + [planted[-1], planted[-2]]
        },
        "duplicate_one_coefficient": {"coefficients": planted + [planted[-1]]},
        "empty_coefficients": {"coefficients": []},
        "out_of_range_coefficient": {
            "coefficients": [inst["prime"]] + planted[1:]
        },
    }
    for name, candidate in variants.items():
        ok, reason = verify(inst, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = [item["reason"] for item in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruptions.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruptions,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "I used finite-field interpolation.\n```json\n"
        + "<answer>"
        + json.dumps(inst["answer"])
        + "</answer>\n```\nThe vector is in ascending powers."
    )
    report["G3_round_trip"] = {
        "pass": parse_answer(realistic) == inst["answer"]
        and parse_answer("no usable final answer here") is None,
        "parsed_equals_answer": parse_answer(realistic) == inst["answer"],
        "garbage_returns_none": parse_answer("no usable final answer here") is None,
    }

    guess_rng = random.Random(0x161103069)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    # Since 2*radius <= N-K and an RS code has minimum distance N-K+1,
    # at most one polynomial can verify.  Equality with the planted polynomial
    # is therefore exactly equivalent to verify() for this sample measurement.
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        if candidate == inst["answer"]:
            guess_hits += 1
    guess_wall = time.perf_counter() - guess_start
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_hits / guess_total,
        "wall_clock_sec": round(guess_wall, 6),
        "candidate_space_bits": search_space(inst).bit_length(),
        "structure_aware_constraints": [
            "exactly K coefficients",
            "every coefficient is a canonical GF(p) residue",
            "the degree-less-than-K rule is built into the fixed vector length",
        ],
        "uniqueness_justification": "2*radius <= N-K < minimum RS distance",
    }

    baseline_rng = random.Random(424242)
    baseline_start = time.perf_counter()
    baseline_candidate = _attack_random_restart(inst, baseline_rng, 256)
    baseline_wall = time.perf_counter() - baseline_start
    baseline_success = (
        baseline_candidate is not None and verify(inst, baseline_candidate)[0]
    )

    attack_names = [
        "outlier_small_received_symbols",
        "greedy_input_order_interpolation",
        "random_restart_256_interpolations",
        "by_hand_degree_four_ansatz",
    ]
    attack_results = {
        name: {"successes": 0, "attempts": 8, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    reference_successes = 0
    reference_operations = []
    reference_wall = 0.0
    for seed in range(100, 108):
        attack_inst = make_instance(seed=seed, **shipping)
        probes = {}
        start = time.perf_counter()
        probes[attack_names[0]] = _attack_outlier_small_y(attack_inst)
        attack_results[attack_names[0]]["wall_clock_sec"] += time.perf_counter() - start
        start = time.perf_counter()
        probes[attack_names[1]] = _attack_greedy_input_order(attack_inst)
        attack_results[attack_names[1]]["wall_clock_sec"] += time.perf_counter() - start
        start = time.perf_counter()
        probes[attack_names[2]] = _attack_random_restart(
            attack_inst, random.Random(seed ^ 0xBEEF), 256
        )
        attack_results[attack_names[2]]["wall_clock_sec"] += time.perf_counter() - start
        start = time.perf_counter()
        probes[attack_names[3]] = _attack_low_degree_ansatz(attack_inst)
        attack_results[attack_names[3]]["wall_clock_sec"] += time.perf_counter() - start
        for name, candidate in probes.items():
            if candidate is not None and verify(attack_inst, candidate)[0]:
                attack_results[name]["successes"] += 1

        start = time.perf_counter()
        decoded, operations = _berlekamp_welch(attack_inst)
        reference_wall += time.perf_counter() - start
        reference_operations.append(operations)
        if verify(attack_inst, decoded)[0]:
            reference_successes += 1
    for result in attack_results.values():
        result["wall_clock_sec"] = round(result["wall_clock_sec"], 6)

    report["G5_density_and_baseline_cost"] = {
        "pass": not baseline_success,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density_estimate": guess_hits / guess_total,
        "exact_valid_polynomial_count": 1,
        "exact_density_numerator": 1,
        "exact_density_denominator": search_space(inst),
        "strongest_failing_attack": "random_restart_256_interpolations",
        "baseline_attack_iterations": 256,
        "baseline_attack_wall_clock_sec": round(baseline_wall, 6),
        "reference_operation_count": max(reference_operations),
        "reference_wall_clock_sec": round(reference_wall / 8, 6),
    }

    all_attacks_failed = all(
        result["successes"] == 0 and result["attempts"] >= 8
        for result in attack_results.values()
    )
    intended = _intended_operations(inst["q_degree"], inst["orbit_order"])
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "Berlekamp-Welch error-locator linear system",
            "complexity": "O(N^3) exact GF(p) operations",
            "wall_clock_sec": round(reference_wall / 8, 6),
            "operations": max(reference_operations),
            "solves": f"{reference_successes}/8, as expected",
        },
        "intended_compact_route": {
            "name": "ninth-root orbit normalization plus three-point interpolation",
            "operations": intended,
            "solves": "by construction",
        },
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    if doubled_params["n"] > ((doubled_params["prime"] - 1)
                               // doubled_params["orbit_order"]):
        doubled_params["prime"] = _next_prime_one_mod_order(
            doubled_params["orbit_order"] * doubled_params["n"] + 1,
            doubled_params["orbit_order"],
        )
    start = time.perf_counter()
    doubled = make_instance(seed=7, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and len(doubled["points"]) > len(inst["points"])
        and doubled["dimension"] == inst["dimension"],
        "shipping_orbits": shipping["n"],
        "doubled_orbits": doubled_params["n"],
        "shipping_points": len(inst["points"]),
        "doubled_points": len(doubled["points"]),
        "answer_coefficients_unchanged": doubled["dimension"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_reason,
        "escalation_after_shipping": escalate(shipping),
    }

    invariant_relabellings = 0
    real_transformations = 0
    g8_failures = []
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(seed=10_000 + seed, **shipping)
        base_key = canonical_key(base)
        unrelated_keys.append(base_key)

        reordered = dict(base)
        reordered["points"] = [list(point) for point in base["points"]]
        random.Random(20_000 + seed).shuffle(reordered["points"])
        for label, transformed in (
            ("row permutation", reordered),
            ("affine x relabelling", _affine_transform(
                base, 2 + seed, 17 + 3 * seed
            )),
            ("affine x relabelling plus row permutation", _affine_transform(
                base, 2 + seed, 17 + 3 * seed, reorder_seed=30_000 + seed
            )),
        ):
            invariant_relabellings += 1
            if canonical_key(transformed) != base_key:
                g8_failures.append({"seed": seed, "transform": label, "kind": "key"})
            ok, reason = verify(transformed, transformed["answer"])
            if ok:
                real_transformations += 1
            else:
                g8_failures.append({
                    "seed": seed, "transform": label, "kind": reason
                })
    report["G8_canonical_key"] = {
        "pass": not g8_failures and len(set(unrelated_keys)) == len(unrelated_keys),
        "invariant_relabellings": invariant_relabellings,
        "real_transformations_verified": real_transformations,
        "unrelated_attempts": len(unrelated_keys),
        "unrelated_distinct_keys": len(set(unrelated_keys)),
        "transformations": [
            "row permutation",
            "affine x -> u*x+t",
            "their composition",
        ],
        "failures": g8_failures,
    }

    worst_chars = 0
    worst_atoms = 0
    for seed in range(1000):
        sample = make_instance(seed=40_000 + seed, **shipping)["answer"]
        worst_chars = max(worst_chars, len(json.dumps(sample, separators=(",", ":"))))
        worst_atoms = max(worst_atoms, _atom_count(sample))
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    within_caps = worst_chars <= 2000 and worst_atoms <= 256 and intended <= 300
    hinted_hardened = (
        G9_ORACLE_RESULTS["hinted_verdict"] == "hardened"
        and arms["hinted"]["attempts"] >= 3
        and arms["hinted"]["solved"] == 0
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps and hinted_hardened,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": len(json.dumps(inst["answer"], separators=(",", ":"))),
        "answer_tokens": math.ceil(
            len(json.dumps(inst["answer"], separators=(",", ":"))) / 4
        ),
        "answer_elements": _atom_count(inst["answer"]),
        "intended_route_operations": intended,
        "measured_worst_over_seeds": 1000,
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": math.ceil(worst_chars / 4),
        "worst_case_answer_elements": worst_atoms,
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
