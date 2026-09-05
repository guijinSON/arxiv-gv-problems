"""Verified generator for polynomial Farkas certificates from arXiv:2002.08085.

Section 4.2 of Greaves--Syatriadi--Yatsyna turns Thompson's principal-
submatrix identity into a nonnegative coefficient system and excludes a
candidate characteristic polynomial with a Farkas vector.  This module keeps
that native algebraic object: rows are integer polynomials, and an answer is a
compact point-evaluation Farkas vector.

Generation is inverse.  An integer root r is sampled first.  Dense
polynomials P_j=(x-r)Q_j are then assembled so that their m-th finite
difference is exactly C(x-r).  The certificate is therefore known without
factoring or solving the generated instance.  A standard modular polynomial
GCD recovers r efficiently and is disclosed as the Track-B reference
algorithm; the intended no-tool route uses the finite-difference identity.
"""

from __future__ import annotations

import copy
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
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "rational",
    "native_objects": [
        "integer polynomials",
        "polynomial coefficient matrix",
        "point-evaluation Farkas certificate over Q",
    ],
    "verification_operations": [
        "exact integer polynomial evaluation",
        "exact rational normalization",
        "exact Farkas sign comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Coefficient columns share a finite-difference invariant: the first "
        "nonzero full difference is a linear polynomial whose root is the "
        "separator; without it one must compute a common polynomial factor."
    ),
    "hardness_basis": (
        "Track B: Section 4.2 searches for a Farkas separator of a polynomial "
        "coefficient system; for this point-evaluation subclass the standard "
        "classical modular-GCD algorithm is O(s*n^2*log p) field operations "
        "for s polynomials of degree n.  At the provisional shipping preset "
        "(degree 96, six polynomials), the included exact reference run is "
        "measured by selftest, while the finite-difference route uses only 23 "
        "exact arithmetic operations after the invariant is recognized."
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


DIFFICULTY = {
    "demo": {
        "n": 8,
        "order": 2,
        "root_bound": 40,
        "coefficient_bound": 3,
    },
    "easy": {
        "n": 96,
        "order": 5,
        "root_bound": 1_000_000_000,
        "coefficient_bound": 7,
    },
    "medium": {
        "n": 144,
        "order": 7,
        "root_bound": 1_000_000_000,
        "coefficient_bound": 11,
    },
    "hard": {
        "n": 216,
        "order": 9,
        "root_bound": 1_000_000_000,
        "coefficient_bound": 17,
    },
}

SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The coefficient columns carry a finite-difference invariant across the "
    "row labels."
)
PLACEBO_HINT = (
    "The coefficient rows reward careful attention to the stated ordering "
    "convention."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One exact rational num/den with denominator exactly 1 and numerator "
        "in the instance interval [-H,H]; JSON stores it as [num,den]."
    ),
    "bounds": {
        "components": 2,
        "denominator": 1,
        "numerator": "inclusive instance interval [-root_bound, root_bound]",
        "canonical_form": "gcd(num,den)=1 and den>0",
        "max_atomic_elements": 2,
    },
}

NOTES = (
    "Section 4.2 fixes the native certificate definition.  If A is the "
    "coefficient matrix of the candidate principal-submatrix polynomials and "
    "b is the derivative-quotient coefficient vector, Theorem 2.3 requires "
    "x^T A=b^T with x>=0; Theorem 4.1 (Farkas) excludes it using y with "
    "Ay>=0 and y^T b<0.  The appendix prints the short rational vectors the "
    "paper found.  Proposition 3.3 and Section 2.3 identify the easy, "
    "computer-driven side: exhaustive totally-real polynomial enumeration "
    "takes 0.52, 0.61, 69.33, and 395.43 seconds in the four main regimes, "
    "and all computations total under 22 minutes.  This module therefore "
    "makes no Track-A claim.  Its point-evaluation vector y(t)=(t^n,...,1) "
    "is represented compactly by t.  Both P_j and -P_j are coefficient rows, "
    "so Ay(t)>=0 is exactly P_j(t)=0 for every j, while b is the polynomial "
    "-1 and hence y(t)^T b=-1.  Generation samples t first and composes the "
    "identity P_j=(x-t)Q_j.  Coefficient columns of Q_j are degree-bounded "
    "functions in the binomial basis; their full finite difference cancels "
    "to a constant, proving uniqueness of the common root.  Individual-row "
    "ratios, Newton-style coefficient greed, random integer restarts, and all "
    "lower-order finite differences are tested as failing attacks.  Modular "
    "polynomial GCD is the successful, explicitly reported Track-B reference."
)


# Updated after the script-owned bare/hinted/placebo runs.  Before those runs,
# zero attempts is an honest diagnostic placeholder; only G9(c) gates locally.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_RATIONAL_RE = re.compile(r"^([+-]?\d+)\s*/\s*([+-]?\d+)$")
_REFERENCE_PRIME = 2_147_483_647  # prime and greater than 2*10^9
_ENUMERATION_CAP = 200_000
_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate(n, order, root_bound, coefficient_bound):
    values = {
        "n": n,
        "order": order,
        "root_bound": root_bound,
        "coefficient_bound": coefficient_bound,
    }
    for name, value in values.items():
        if not _is_int(value):
            raise ValueError(f"{name} must be an integer")
    if not 4 <= n <= 4096:
        raise ValueError("n must lie in 4..4096")
    if not 2 <= order <= 50:
        raise ValueError("order must lie in 2..50")
    if n < order + 2:
        raise ValueError("n must be at least order+2")
    if not 10 <= root_bound <= 1_000_000_000:
        raise ValueError("root_bound must lie in 10..1000000000")
    if not 1 <= coefficient_bound <= 1_000_000:
        raise ValueError("coefficient_bound must lie in 1..1000000")


def _nonzero_random(rng, bound):
    value = rng.randint(-bound, bound)
    while value == 0:
        value = rng.randint(-bound, bound)
    return value


def _multiply_by_linear(quotient, root):
    """Descending coefficients of (x-root)*quotient."""
    out = [quotient[0]]
    for index in range(1, len(quotient)):
        out.append(quotient[index] - root * quotient[index - 1])
    out.append(-root * quotient[-1])
    return out


def make_instance(n, seed=0, order=5, root_bound=1_000_000_000,
                  coefficient_bound=7):
    """Inverse-generate dense polynomial rows and a known Farkas certificate."""
    _validate(n, order, root_bound, coefficient_bound)
    rng = random.Random(seed)

    # Keep the plant away from the few tiny integers an unaided solver gets for
    # free, without making its sign or magnitude an identifying row statistic.
    magnitude = rng.randint(max(3, root_bound // 3), root_bound)
    root = magnitude if rng.randrange(2) else -magnitude

    # A_k has degree at most n-1.  Q_j = sum C(j,k)A_k + C(j,m)C.
    # The leading setup makes every P_j monic.  The x-coefficients make every
    # lower-order difference nonconstant, defeating the tempting truncated
    # finite-difference ansatz without any rejection sampling.
    basis = []
    for k in range(order):
        row = [_nonzero_random(rng, coefficient_bound) for _ in range(n)]
        row[0] = 1 if k == 0 else 0
        row[-2] = 1
        basis.append(row)
    top_constant = rng.randint(1, coefficient_bound)

    polynomials = []
    for label in range(order + 1):
        quotient = [0] * n
        for k, row in enumerate(basis):
            weight = math.comb(label, k)
            if not weight:
                continue
            for index, coefficient in enumerate(row):
                quotient[index] += weight * coefficient
        quotient[-1] += math.comb(label, order) * top_constant
        coefficients = _multiply_by_linear(quotient, root)
        polynomials.append({"label": label, "coefficients": coefficients})

    rng.shuffle(polynomials)
    return {
        "family": "point-evaluation Farkas certificate",
        "degree": n,
        "root_bound": root_bound,
        "difference_order": order,
        "polynomials": polynomials,
        "answer": [root, 1],
    }


def render(inst):
    degree = inst["degree"]
    bound = inst["root_bound"]
    order = inst["difference_order"]
    rows = []
    for entry in inst["polynomials"]:
        coefficients = " ".join(str(value) for value in entry["coefficients"])
        rows.append(f"label {entry['label']}: {coefficients}")

    hint = ""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        hint = f"\n\nHint: {STRUCTURAL_HINT}"
    elif mode == "placebo":
        hint = f"\n\nHint: {PLACEBO_HINT}"

    return (
        "Find a compact Farkas certificate for an exact polynomial "
        "coefficient system.\n\n"
        f"There are {order + 1} integer polynomials P_j(x), each of exact "
        f"degree n={degree}.  A displayed row contains its {degree + 1} "
        "coefficients in descending order: the first multiplies x^n and the "
        "last is the constant coefficient.  The row labels are distinct "
        f"integers 0 through {order}; display order has no mathematical "
        "meaning.\n\n"
        "Form a matrix A having, for every displayed polynomial P_j, both "
        "coeff(P_j) and coeff(-P_j) as rows.  Let b=coeff(-1), padded on the "
        "left to length n+1.  For a rational t define the point-evaluation "
        "column y(t)=(t^n,t^(n-1),...,t,1).  Your task is to give t such "
        "that A y(t) is componentwise nonnegative and y(t)^T b<0.  Since A "
        "contains both signs, this is equivalent to P_j(t)=0 for every "
        "displayed row; the second inequality is then exactly -1<0.  Thus "
        "the answer is an executable Farkas witness that no nonnegative "
        "lambda can satisfy lambda^T A=b^T.\n\n"
        f"The answer must be a reduced rational num/den with denominator "
        f"exactly 1 and numerator in the inclusive interval [-{bound},{bound}]. "
        "All arithmetic and interval endpoints are exact; floating-point "
        "approximations are not accepted.\n\n"
        "Polynomial rows:\n"
        + "\n".join(rows)
        + hint
        + "\n\nGive your final answer inside <answer></answer> tags as one "
        "exact rational num/den.\n"
        "Format example only: <answer>-17/1</answer>\n"
        "Output nothing else inside the tags."
    )


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body).strip()

    match = _RATIONAL_RE.fullmatch(body)
    if match:
        try:
            return [int(match.group(1)), int(match.group(2))]
        except (TypeError, ValueError):
            return None
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if (isinstance(value, list) and len(value) == 2
            and all(_is_int(item) for item in value)):
        return value
    return None


def _eval_mod(coefficients, value, modulus):
    result = 0
    value %= modulus
    for coefficient in coefficients:
        result = (result * value + coefficient) % modulus
    return result


def _eval_exact(coefficients, value):
    result = 0
    for coefficient in coefficients:
        result = result * value + coefficient
    return result


def verify(inst, answer):
    # Deliberately never inspect inst["answer"].
    if not isinstance(answer, list):
        return False, "answer must be a rational pair"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) == 1:
        return False, "answer is missing its denominator"
    if len(answer) > 2:
        return False, "answer has extra components"
    numerator, denominator = answer
    if not _is_int(numerator) or not _is_int(denominator):
        return False, "numerator and denominator must be integers"
    if denominator <= 0:
        return False, "denominator must be positive"
    if denominator != 1:
        return False, "denominator must equal 1"
    if math.gcd(numerator, denominator) != 1:
        return False, "rational must be reduced"
    bound = inst["root_bound"]
    if numerator < -bound or numerator > bound:
        return False, "numerator is outside the inclusive interval"

    # Modular nonzero is an exact rejection, not a floating approximation.  A
    # rare candidate passing the screen is rechecked over Z before acceptance.
    for entry in inst["polynomials"]:
        coefficients = entry["coefficients"]
        if _eval_mod(coefficients, numerator, _REFERENCE_PRIME) != 0:
            return False, f"not a common root: row {entry['label']} is nonzero"
    for entry in inst["polynomials"]:
        if _eval_exact(entry["coefficients"], numerator) != 0:
            return False, f"not a common root over Z: row {entry['label']} fails"
    return True, "ok"


def random_candidate(inst, rng):
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    bound = inst["root_bound"]
    return [rng.randint(-bound, bound), 1]


def search_space(inst):
    return 2 * inst["root_bound"] + 1


def enumerate_all(inst):
    if search_space(inst) > _ENUMERATION_CAP:
        return None
    count = 0
    bound = inst["root_bound"]
    for value in range(-bound, bound + 1):
        if verify(inst, [value, 1])[0]:
            count += 1
    return count


def _primitive(coefficients):
    divisor = 0
    for value in coefficients:
        divisor = math.gcd(divisor, abs(value))
    divisor = divisor or 1
    values = [value // divisor for value in coefficients]
    first = next((value for value in values if value), 0)
    if first < 0:
        values = [-value for value in values]
    return tuple(values)


def _reflected(coefficients):
    degree = len(coefficients) - 1
    return [
        coefficient if (degree - index) % 2 == 0 else -coefficient
        for index, coefficient in enumerate(coefficients)
    ]


def canonical_key(inst):
    """Invariant under row order/scale/sign and the reflection x -> -x."""
    rows = [entry["coefficients"] for entry in inst["polynomials"]]
    direct = tuple(sorted(_primitive(row) for row in rows))
    reflected = tuple(sorted(_primitive(_reflected(row)) for row in rows))
    canonical_rows = min(direct, reflected)
    payload = {
        "root_bound": inst["root_bound"],
        "rows": canonical_rows,
    }
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params):
    current = {key: value for key, value in params.items() if key != "_preset"}
    n = current["n"]
    order = current["order"]
    coefficient_bound = current["coefficient_bound"]
    if n >= 4096 or order >= 50 or coefficient_bound >= 1_000_000:
        return None
    harder = dict(current)
    harder["n"] = min(4096, max(n + 8, (5 * n) // 4))
    harder["order"] = min(50, order + 2)
    harder["coefficient_bound"] = min(1_000_000, coefficient_bound * 2 + 1)
    return harder


def _difference_weights(order):
    return [(-1 if (order - index) % 2 else 1) * math.comb(order, index)
            for index in range(order + 1)]


def _compact_answer(inst):
    rows = sorted(inst["polynomials"], key=lambda entry: entry["label"])
    weights = _difference_weights(inst["difference_order"])
    linear = sum(weight * entry["coefficients"][-2]
                 for weight, entry in zip(weights, rows))
    constant = sum(weight * entry["coefficients"][-1]
                   for weight, entry in zip(weights, rows))
    if linear == 0 or (-constant) % linear:
        return None
    return [-constant // linear, 1]


def _poly_trim(poly):
    while len(poly) > 1 and poly[-1] == 0:
        poly.pop()
    return poly


def _poly_remainder_mod(dividend, divisor, modulus, counter):
    remainder = list(dividend)
    divisor = _poly_trim(list(divisor))
    inverse = pow(divisor[-1], modulus - 2, modulus)
    counter[0] += 2 * modulus.bit_length()
    while (len(remainder) >= len(divisor)
           and not (len(remainder) == 1 and remainder[0] == 0)):
        shift = len(remainder) - len(divisor)
        factor = remainder[-1] * inverse % modulus
        counter[0] += 1
        for index, value in enumerate(divisor):
            position = shift + index
            remainder[position] = (remainder[position] - factor * value) % modulus
            counter[0] += 2
        _poly_trim(remainder)
    return remainder


def _poly_gcd_mod(left, right, modulus, counter):
    left = _poly_trim([value % modulus for value in left])
    right = _poly_trim([value % modulus for value in right])
    while not (len(right) == 1 and right[0] == 0):
        left, right = right, _poly_remainder_mod(left, right, modulus, counter)
    inverse = pow(left[-1], modulus - 2, modulus)
    counter[0] += 2 * modulus.bit_length()
    return [(value * inverse) % modulus for value in left]


def _reference_modular_gcd(inst):
    """Domain-standard common-factor attack; returns (answer, op_count)."""
    modulus = _REFERENCE_PRIME
    rows = [list(reversed(entry["coefficients"]))
            for entry in inst["polynomials"]]
    counter = [0]
    gcd_poly = rows[0]
    for row in rows[1:]:
        gcd_poly = _poly_gcd_mod(gcd_poly, row, modulus, counter)
        if len(gcd_poly) == 2:
            break
    if len(gcd_poly) != 2 or gcd_poly[1] % modulus == 0:
        return None, counter[0]
    residue = (-gcd_poly[0] * pow(gcd_poly[1], modulus - 2, modulus)) % modulus
    counter[0] += 2 * modulus.bit_length() + 1
    bound = inst["root_bound"]
    if residue <= bound:
        candidate = residue
    elif residue >= modulus - bound:
        candidate = residue - modulus
    else:
        return None, counter[0]
    answer = [candidate, 1]
    return (answer if verify(inst, answer)[0] else None), counter[0]


def _try_candidates(inst, candidates):
    seen = set()
    for candidate in candidates:
        if not _is_int(candidate) or candidate in seen:
            continue
        seen.add(candidate)
        if -inst["root_bound"] <= candidate <= inst["root_bound"]:
            if verify(inst, [candidate, 1])[0]:
                return [candidate, 1]
    return None


def _attack_outlier_ratios(inst):
    candidates = []
    n = inst["degree"]
    for entry in inst["polynomials"]:
        row = entry["coefficients"]
        leading, next_coefficient = row[0], row[1]
        linear, constant = row[-2], row[-1]
        if linear:
            candidates.extend([(-constant) // linear,
                               -((-constant) // -linear)])
        if leading:
            denominator = n * leading
            candidates.extend([(-next_coefficient) // denominator,
                               -((-next_coefficient) // -denominator)])
    return _try_candidates(inst, candidates), len(candidates) * 4


def _poly_and_derivative(coefficients, value):
    polynomial = coefficients[0]
    derivative = 0
    for coefficient in coefficients[1:]:
        derivative = derivative * value + polynomial
        polynomial = polynomial * value + coefficient
    return polynomial, derivative


def _attack_greedy_newton(inst):
    rows = sorted(inst["polynomials"], key=lambda entry: entry["label"])
    coefficients = rows[0]["coefficients"]
    bound = inst["root_bound"]
    starts = [0, 1, -1, bound // 2, -(bound // 2)]
    candidates = list(starts)
    operations = 0
    for start in starts:
        value = start
        for _ in range(6):
            polynomial, derivative = _poly_and_derivative(coefficients, value)
            operations += 4 * inst["degree"]
            if derivative == 0:
                break
            value -= polynomial // derivative
            value = max(-bound, min(bound, value))
            candidates.append(value)
    return _try_candidates(inst, candidates), operations


def _attack_random_restart(inst, rng, restarts=512):
    bound = inst["root_bound"]
    operations = 0
    first = inst["polynomials"][0]["coefficients"]
    for _ in range(restarts):
        value = rng.randint(-bound, bound)
        operations += 2 * len(first)
        if _eval_mod(first, value, _REFERENCE_PRIME) != 0:
            continue
        if verify(inst, [value, 1])[0]:
            return [value, 1], operations
    return None, operations


def _attack_lower_differences(inst):
    rows = sorted(inst["polynomials"], key=lambda entry: entry["label"])
    full_order = inst["difference_order"]
    candidates = []
    operations = 0
    for order in range(1, full_order):
        weights = _difference_weights(order)
        linear = sum(weight * rows[index]["coefficients"][-2]
                     for index, weight in enumerate(weights))
        constant = sum(weight * rows[index]["coefficients"][-1]
                       for index, weight in enumerate(weights))
        operations += 4 * order + 2
        if linear:
            base = (-constant) // linear
            candidates.extend([base - 1, base, base + 1])
    return _try_candidates(inst, candidates), operations


def _atom_count(value):
    if isinstance(value, dict):
        return sum(_atom_count(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atom_count(item) for item in value)
    return 1


def _transformed_instance(inst, rng, reflect=False, rescale=False):
    transformed = copy.deepcopy(inst)
    rows = transformed["polynomials"]
    rng.shuffle(rows)
    for index, entry in enumerate(rows):
        coefficients = entry["coefficients"]
        if reflect:
            coefficients = _reflected(coefficients)
        if rescale:
            factor = (index % 5) + 1
            if index % 2:
                factor = -factor
            coefficients = [factor * value for value in coefficients]
        entry["coefficients"] = coefficients
    transformed.pop("answer", None)
    return transformed


def selftest():
    report = {}

    # G1: every named preset, three seeds, plus the construction's compact route.
    planted_attempts = 0
    compact_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            planted_attempts += 1
            if not verify(inst, inst["answer"])[0]:
                raise AssertionError(f"G1 failed for {preset}, seed {seed}")
            compact_attempts += 1
            recovered = _compact_answer(inst)
            if recovered is None or not verify(inst, recovered)[0]:
                raise AssertionError(f"finite difference failed for {preset}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                raise AssertionError("answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": True,
        "verified": planted_attempts,
        "compact_identity_recovered": compact_attempts,
    }

    params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=4242, **params)
    numerator = shipping["answer"][0]
    corruptions = {
        "empty": [],
        "drop_denominator": [numerator],
        "duplicate_component": [numerator, 1, 1],
        "swap_components": [1, numerator],
        "out_of_range": [shipping["root_bound"] + 1, 1],
    }
    reasons = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        if ok:
            raise AssertionError(f"G2 accepted {name}")
        reasons[name] = reason
    distinct_reasons = len(set(reasons.values()))
    report["G2_rejects_corruption"] = {
        "pass": distinct_reasons == len(corruptions),
        "rejected": len(reasons),
        "distinct_reasons": distinct_reasons,
        "reasons": reasons,
    }

    model_style = (
        "The simultaneous vanishing gives the separator.\n\n```text\n"
        f"<answer>{numerator}/1</answer>\n```\nThis is exact."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"],
        "parsed": parsed,
    }

    guess_rng = random.Random(0x200208085)
    guess_hits = 0
    t0 = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        candidate = random_candidate(shipping, guess_rng)
        if verify(shipping, candidate)[0]:
            guess_hits += 1
    guess_elapsed = time.perf_counter() - t0
    report["G4_guess_resistance"] = {
        "pass": guess_hits / _G4_SAMPLES < 1e-6,
        "hits": guess_hits,
        "total": _G4_SAMPLES,
        "observed_probability": guess_hits / _G4_SAMPLES,
        "certificate_language_size": search_space(shipping),
        "exact_valid_answers_by_identity": 1,
        "elapsed_seconds": round(guess_elapsed, 6),
    }

    # G6 also supplies G5's measured strongest failing baseline.
    attack_totals = {
        "per_row_outlier_ratios": 0,
        "greedy_integer_newton": 0,
        "random_restart_512": 0,
        "lower_order_finite_difference": 0,
    }
    attack_operations = {name: 0 for name in attack_totals}
    attack_wall = {name: 0.0 for name in attack_totals}
    reference_successes = 0
    reference_operations = 0
    reference_wall = 0.0
    for seed in range(_ATTACK_SEEDS):
        inst = make_instance(seed=10_000 + seed, **params)
        attacks = [
            ("per_row_outlier_ratios", lambda: _attack_outlier_ratios(inst)),
            ("greedy_integer_newton", lambda: _attack_greedy_newton(inst)),
            ("random_restart_512", lambda: _attack_random_restart(
                inst, random.Random(90_000 + seed), 512)),
            ("lower_order_finite_difference", lambda: _attack_lower_differences(inst)),
        ]
        for name, attack in attacks:
            started = time.perf_counter()
            answer, operations = attack()
            attack_wall[name] += time.perf_counter() - started
            attack_operations[name] += operations
            if answer is not None and verify(inst, answer)[0]:
                attack_totals[name] += 1

        started = time.perf_counter()
        answer, operations = _reference_modular_gcd(inst)
        reference_wall += time.perf_counter() - started
        reference_operations += operations
        if answer is not None and verify(inst, answer)[0]:
            reference_successes += 1

    attack_report = {}
    for name in attack_totals:
        attack_report[name] = {
            "successes": attack_totals[name],
            "attempts": _ATTACK_SEEDS,
            "mean_operations": attack_operations[name] // _ATTACK_SEEDS,
            "mean_wall_clock_sec": round(attack_wall[name] / _ATTACK_SEEDS, 6),
        }
    all_failed = all(value == 0 for value in attack_totals.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == _ATTACK_SEEDS,
        "attacks": attack_report,
        "reference_algorithm": {
            "name": "classical modular polynomial GCD over a 31-bit prime",
            "complexity": "O(s*n^2*log p) modular field operations",
            "wall_clock_sec": round(reference_wall / _ATTACK_SEEDS, 6),
            "operations": reference_operations // _ATTACK_SEEDS,
            "solves": f"{reference_successes}/{_ATTACK_SEEDS}, as expected",
        },
    }

    strongest_name = max(attack_operations,
                         key=lambda name: attack_operations[name])
    report["G5_density_and_baseline"] = {
        "pass": all_failed,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": _G4_SAMPLES,
        "shipping_observed_valid_fraction": guess_hits / _G4_SAMPLES,
        "exact_valid_solution_count_by_finite_difference_identity": 1,
        "strongest_failing_attack": strongest_name,
        "baseline_mean_operations": attack_operations[strongest_name] // _ATTACK_SEEDS,
        "baseline_mean_wall_seconds": round(
            attack_wall[strongest_name] / _ATTACK_SEEDS, 6),
    }

    doubled_params = dict(params)
    doubled_params["n"] *= 2
    scaled = make_instance(seed=707, **doubled_params)
    small_answer, small_ops = _reference_modular_gcd(shipping)
    large_answer, large_ops = _reference_modular_gcd(scaled)
    report["G7_scales"] = {
        "pass": (
            verify(scaled, scaled["answer"])[0]
            and small_answer is not None
            and large_answer is not None
            and large_ops > small_ops
            and _atom_count(scaled["answer"]) == _atom_count(shipping["answer"])
            and len(json.dumps(scaled["answer"])) <= 32
        ),
        "degree_before": params["n"],
        "degree_after": doubled_params["n"],
        "reference_operations_before": small_ops,
        "reference_operations_after": large_ops,
        "answer_chars_before": len(json.dumps(shipping["answer"])),
        "answer_chars_after": len(json.dumps(scaled["answer"])),
        "answer_elements_before": _atom_count(shipping["answer"]),
        "answer_elements_after": _atom_count(scaled["answer"]),
    }

    invariant_checks = 0
    carried_witness_checks = 0
    distinct_keys = set()
    for seed in range(20):
        inst = make_instance(seed=30_000 + seed, **params)
        key = canonical_key(inst)
        distinct_keys.add(key)
        for transform_index, (reflect, rescale) in enumerate((
                (False, False), (False, True), (True, False), (True, True))):
            transformed = _transformed_instance(
                inst, random.Random(seed * 17 + transform_index),
                reflect=reflect, rescale=rescale)
            invariant_checks += 1
            if canonical_key(transformed) != key:
                raise AssertionError("canonical key lost an admitted symmetry")
            carried = [-inst["answer"][0], 1] if reflect else list(inst["answer"])
            carried_witness_checks += 1
            if not verify(transformed, carried)[0]:
                raise AssertionError("G8 transformation did not preserve witness")
    report["G8_canonical_key"] = {
        "pass": (
            invariant_checks == 80
            and carried_witness_checks == 80
            and len(distinct_keys) == 20
        ),
        "invariant_relabellings": invariant_checks,
        "carried_witnesses_valid": carried_witness_checks,
        "unrelated_distinct": len(distinct_keys),
        "unrelated_attempts": 20,
        "symmetries": [
            "polynomial row reordering",
            "nonzero integer row rescaling/sign",
            "global variable reflection x->-x",
            "all listed compositions",
        ],
    }

    answer_blobs = []
    answer_atoms = []
    for seed in range(20):
        answer = make_instance(seed=50_000 + seed, **params)["answer"]
        answer_blobs.append(json.dumps(answer, separators=(",", ":")))
        answer_atoms.append(_atom_count(answer))
    answer_chars = max(map(len, answer_blobs))
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = max(answer_atoms)
    route_operations = 4 * params["order"] + 3
    hinted = G9_ORACLE_RESULTS["hinted"]
    placebo = G9_ORACLE_RESULTS["placebo"]
    hinted_rate = (hinted["solved"] / hinted["attempts"]
                   if hinted["attempts"] else None)
    placebo_rate = (placebo["solved"] / placebo["attempts"]
                    if placebo["attempts"] else None)
    delta = (hinted_rate - placebo_rate
             if hinted_rate is not None and placebo_rate is not None else None)
    report["G9_no_tool_suitability"] = {
        "pass": (
            answer_chars <= 2000
            and answer_elements <= 256
            and route_operations <= 300
        ),
        "arms": {
            "bare": dict(G9_ORACLE_RESULTS["bare"]),
            "hinted": dict(hinted),
            "placebo": dict(placebo),
        },
        "hinted_minus_placebo": delta,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": route_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
