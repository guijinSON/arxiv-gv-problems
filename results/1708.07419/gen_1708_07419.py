"""Verified native Lie-polynomial problems from arXiv:1708.07419.

The certificate is built from Lemma 6's Jacobi recurrence and then transported
through an invertible rank-one change of coordinates.  Verification works in
exact Hall-basis coordinates over Q; generation never solves the displayed
linear system.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import statistics
import time
from fractions import Fraction


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "Subtract the identity matrix from the displayed change of basis and use its "
    "rank-one factorization after telescoping the Jacobi derivatives."
)
PLACEBO_HINT: str = (
    "Keep the zero-based indices and all signed coefficients consistent while "
    "working through the displayed algebraic data."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "polynomial",
    "native_objects": [
        "free Lie algebra over Q on two generators",
        "Hall-basis Lie monomials",
        "rational Lie polynomial in a displayed basis",
    ],
    "verification_operations": [
        "exact rational coefficient arithmetic",
        "Jacobi derivation in Hall-basis coordinates",
        "exact sparse polynomial coefficient comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Telescope the Jacobi-derivative chain from Lemma 6 and recognize the "
        "displayed dense basis as a rank-one perturbation; without both steps "
        "one must perform exact Hall coefficient matching and elimination."
    ),
    "hardness_basis": (
        "Track B: Hall-basis coefficient matching followed by rational Gaussian "
        "elimination is O(k^3); at the shipping preset k=36 it required 55026 "
        "counted exact operations and 0.014 seconds (median over eight seeds), "
        "whereas the Jacobi telescope plus rank-one inverse uses at most 288 exact "
        "operations once the two structures are seen."
    ),
    "max_answer_tokens": 51,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 1, "steps": 3, "mix_magnitude": 1},
    "easy": {"n": 24, "steps": 12, "mix_magnitude": 3},
    "medium": {"n": 64, "steps": 15, "mix_magnitude": 11},
    "hard": {"n": 128, "steps": 18, "mix_magnitude": 37},
}
SHIPPING_DIFFICULTY: str = "hard"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A dense rational Lie polynomial in the k displayed basis elements: "
        "exactly k reduced coefficients num/den, with den=1 and each numerator "
        "in the instance's inclusive interval [-C,C]."
    ),
    "bounds": {
        "max_basis_terms": 36,
        "denominator": 1,
        "max_coefficient_bits_at_named_presets": 12,
    },
}

NOTES: str = (
    "Section 4 fixes the free-Lie objects and left-normed notation. Lemma 6 "
    "supplies the even-adjoint Jacobi identity and its recursively produced "
    "witness; Lemma 4 supplies Hall-basis faithfulness, while Theorem 5 gives "
    "only worst-case undecidability and does not justify average-case Track A. "
    "The special linear coefficient problem here is polynomial-time, so its "
    "Hall matching/Gaussian algorithm is disclosed under Track B. Plants and "
    "decoys are the same displayed Hall terms under one dense invertible change "
    "of basis. Column-norm outliers, one-pass diagonal greed, 256 random "
    "restarts, and the unmixed Jacobi ansatz all fail; the compact route is the "
    "paper's telescope followed by a rank-one inverse."
)

# Replaced with the script-owned transcript counts after the three hardening
# runs.  Keeping the data here makes selftest() reproducible without network.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "hardened",
}


def _canonical_terms(steps, m):
    """The 2*steps Hall terms in the proof of Lemma 6."""
    terms = []
    for j in range(steps):
        terms.append([m + 2 * j, 2 * steps - 2 * j - 1])
        terms.append([m + 2 * j + 1, 2 * steps - 2 * j - 2])
    return terms


def _target_coefficients(k):
    return [1 if i % 2 == 0 else -1 for i in range(k)]


def _rank_one_data(k, rng):
    """Return sign vectors u,v with v.u=0 and v.c bounded away from zero."""
    c = _target_coefficients(k)
    minimum = 2 if k < 12 else max(4, k // 10)
    while True:
        u = [rng.choice((-1, 1)) for _ in range(k)]
        products = [1] * (k // 2) + [-1] * (k // 2)
        rng.shuffle(products)
        v = [products[i] * u[i] for i in range(k)]
        t = sum(v[i] * c[i] for i in range(k))
        if minimum <= abs(t) <= max(minimum, k // 2):
            return u, v, t


def _format_answer(answer):
    return ", ".join(str(num) if den == 1 else f"{num}/{den}"
                     for num, den in answer)


def make_instance(n, seed=0, **params) -> dict:
    """Build a Lemma-6 witness and transport it through a known basis map.

    ``n`` is an ambient-degree padding parameter: increasing it lengthens the
    Lie words without lengthening the certificate.  ``steps`` controls the
    telescope length, and ``mix_magnitude`` increases coefficient arithmetic
    at fixed answer dimension.  No displayed system is solved during generation.
    """
    steps = params.pop("steps", 18)
    mix_magnitude = params.pop("mix_magnitude", 37)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    for name, value, lower in (("n", n, 0), ("steps", steps, 1),
                               ("mix_magnitude", mix_magnitude, 1)):
        if isinstance(value, bool) or not isinstance(value, int) or value < lower:
            raise ValueError(f"{name} must be an integer at least {lower}")
    k = 2 * steps
    if k > 128:
        raise ValueError("steps is capped at 64 so answers remain writable")

    rng = random.Random(seed)
    # m>2*steps makes every H(p,q) below a distinct Hall basis element by the
    # Hall-basis observation immediately preceding Lemma 4 in the paper.
    m = 2 * steps + 3 + n
    u, v, t = _rank_one_data(k, rng)
    scale = mix_magnitude
    matrix = [[(1 if i == j else 0) + scale * u[i] * v[j]
               for j in range(k)] for i in range(k)]

    # If M=I+scale*u*v^T and v^T u=0, M^{-1}=I-scale*u*v^T.
    c = _target_coefficients(k)
    solution = [c[i] - scale * u[i] * t for i in range(k)]
    bound = scale * k + 2
    assert all(abs(x) <= bound for x in solution)

    return {
        "family": "Jacobi telescope in a changed Hall basis",
        "n": n,
        "steps": steps,
        "k": k,
        "m": m,
        "mix_magnitude": scale,
        "coefficient_bound": bound,
        "generators": ["a", "b"],
        "terms": _canonical_terms(steps, m),
        "matrix": matrix,
        "target": [[m, 2 * steps, 1], [m + 2 * steps, 0, -1]],
        "answer": [[x, 1] for x in solution],
    }


def render(inst) -> str:
    a, b = inst["generators"]
    matrix_rows = "\n".join(
        f"  row {i}: " + " ".join(str(x) for x in row)
        for i, row in enumerate(inst["matrix"])
    )
    statement = f"""JACOBI TELESCOPE IN A FREE LIE ALGEBRA

Work in the free Lie algebra over the rational numbers Q on the two generators
{a} and {b}. The bracket is bilinear, [u,u]=0, [u,v]=-[v,u], and it obeys
the Jacobi identity. All brackets below are left-normed. Define

  ad_{a}^0(u)=u,    ad_{a}^(r+1)(u)=[ad_{a}^r(u),{a}],
  H(p,q)=[ad_{a}^p({b}), ad_{a}^q({b})].

For this instance m={inst['m']} and h={inst['steps']}. Define k={inst['k']}
Hall terms T_0,...,T_{inst['k'] - 1}, using zero-based indices, by

  T_(2j)   = H(m+2j,   2h-2j-1),
  T_(2j+1) = H(m+2j+1, 2h-2j-2)       for 0 <= j < h.

Every first exponent is larger than its second exponent, so these are distinct
Hall-basis elements. Now define displayed Lie polynomials P_0,...,P_{inst['k'] - 1} by

  P_j = sum from i=0 to k-1 of M[i,j]*T_i.

The integer matrix M is written by rows (each row has exactly k entries):
{matrix_rows}

Find the rational coefficients x_0,...,x_{inst['k'] - 1} of the Lie polynomial

  S = sum from j=0 to k-1 of x_j*P_j

such that the following equality holds in the free Lie algebra:

  [S,{a}] = H({inst['m']},{2 * inst['steps']}) - H({inst['m'] + 2 * inst['steps']},0).

The answer is unique. Give exactly k={inst['k']} coefficients in index order.
Each coefficient must be a reduced rational num/den with positive denominator;
integers may be written as num and mean num/1. Here every denominator must equal
1 and every numerator must lie in the inclusive interval
[-{inst['coefficient_bound']},{inst['coefficient_bound']}]. Repeats are allowed.

Give your final answer inside <answer></answer> tags, as exactly k comma-separated
coefficients num/den (or integer num).
Example format for k=3 only: <answer>2, -3/1, 0</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    try:
        matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", str(text),
                             re.I | re.S)
        if not matches:
            return None
        body = matches[-1].strip()
        body = re.sub(r"^```(?:text|json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
        if not body:
            return []
        out = []
        for token in body.split(","):
            token = token.strip()
            match = re.fullmatch(r"([+-]?\d+)(?:\s*/\s*([+]?[1-9]\d*))?", token)
            if not match:
                return None
            num = int(match.group(1))
            den = int(match.group(2) or "1")
            common = math.gcd(abs(num), den)
            out.append([num // common, den // common])
        return out
    except (TypeError, ValueError, OverflowError):
        return None


def _add_hall(coordinates, p, q, value):
    if not value or p == q:
        return
    if p < q:
        p, q, value = q, p, -value
    key = (p, q)
    coordinates[key] = coordinates.get(key, Fraction(0)) + value
    if coordinates[key] == 0:
        del coordinates[key]


def _expanded_derivative(inst, t_coefficients):
    coordinates = {}
    for coefficient, (p, q) in zip(t_coefficients, inst["terms"]):
        # Jacobi: [H(p,q),a] = H(p+1,q) + H(p,q+1).
        _add_hall(coordinates, p + 1, q, coefficient)
        _add_hall(coordinates, p, q + 1, coefficient)
    return coordinates


def _target_coordinates(inst):
    target = {}
    for p, q, coefficient in inst["target"]:
        _add_hall(target, p, q, Fraction(coefficient))
    return target


def _validate_coefficients(inst, answer):
    if not isinstance(answer, list):
        return None, "answer must be a list of rational coefficients"
    if len(answer) != inst["k"]:
        return None, f"expected exactly {inst['k']} coefficients, got {len(answer)}"
    values = []
    for i, item in enumerate(answer):
        if (not isinstance(item, list) or len(item) != 2
                or any(isinstance(x, bool) or not isinstance(x, int) for x in item)):
            return None, f"coefficient {i} must be a JSON pair [numerator, denominator]"
        num, den = item
        if den <= 0:
            return None, f"coefficient {i} has a nonpositive denominator"
        if math.gcd(abs(num), den) != 1:
            return None, f"coefficient {i} is not in reduced form"
        if den != 1:
            return None, f"coefficient {i} denominator must equal 1"
        if abs(num) > inst["coefficient_bound"]:
            return None, f"coefficient {i} numerator is outside the inclusive bound"
        values.append(Fraction(num, den))
    return values, None


def verify(inst, answer) -> tuple[bool, str]:
    """Check any bounded witness; never consult ``inst['answer']``."""
    values, error = _validate_coefficients(inst, answer)
    if error:
        return False, error

    # The target's telescoping T-coefficients are (+1,-1,+1,-1,...).
    # Compare rows early: random invalid candidates normally cost only one row.
    t_coefficients = []
    for i, row in enumerate(inst["matrix"]):
        got = sum((Fraction(entry) * values[j]
                   for j, entry in enumerate(row)), Fraction(0))
        expected = Fraction(1 if i % 2 == 0 else -1)
        if got != expected:
            return False, (f"Lie identity mismatch at Hall coefficient T_{i}: "
                           f"got {got}, expected {expected}")
        t_coefficients.append(got)

    # Execute the Lie-algebra check itself.  This is not merely Mx=c: each T_i
    # is differentiated by Jacobi and the resulting Hall coordinates are
    # compared with the displayed right-hand side.
    got_coordinates = _expanded_derivative(inst, t_coefficients)
    expected_coordinates = _target_coordinates(inst)
    if got_coordinates != expected_coordinates:
        keys = sorted(set(got_coordinates) | set(expected_coordinates))
        for p, q in keys:
            got = got_coordinates.get((p, q), Fraction(0))
            expected = expected_coordinates.get((p, q), Fraction(0))
            if got != expected:
                return False, (f"expanded Jacobi coordinate H({p},{q}) differs: "
                               f"got {got}, expected {expected}")
        return False, "expanded Jacobi coordinates differ"
    return True, "ok"


def _candidate_numerators(candidate):
    return [item[0] for item in candidate]


def random_candidate(inst, rng) -> object:
    bound = inst["coefficient_bound"]
    return [[rng.randint(-bound, bound), 1] for _ in range(inst["k"])]


def search_space(inst) -> int | None:
    return (2 * inst["coefficient_bound"] + 1) ** inst["k"]


def enumerate_all(inst) -> int | None:
    space = search_space(inst)
    if space is None or space > 200_000:
        return None
    count = 0
    choices = range(-inst["coefficient_bound"], inst["coefficient_bound"] + 1)
    for vector in itertools.product(choices, repeat=inst["k"]):
        ok, _ = verify(inst, [[x, 1] for x in vector])
        count += int(ok)
    return count


def canonical_key(inst) -> str:
    """Ignore generator names and displayed-basis order, retaining Lie data."""
    columns = [tuple(inst["matrix"][i][j] for i in range(inst["k"]))
               for j in range(inst["k"])]
    payload = {
        "m": inst["m"],
        "steps": inst["steps"],
        "terms": inst["terms"],
        "target": inst["target"],
        "columns": sorted(columns),
        "coefficient_bound": inst["coefficient_bound"],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params) -> dict | str | None:
    """Increase ambient degree and coefficient size at fixed witness length."""
    harder = dict(params)
    harder["n"] = int(harder.get("n", 128)) * 2
    harder["mix_magnitude"] = int(harder.get("mix_magnitude", 37)) * 3 + 2
    harder["steps"] = int(harder.get("steps", 18))
    # Even at three harness escalations this remains well below the output cap;
    # later callers can keep growing the two fixed-length hardness axes.
    return harder


def _gaussian_reference(inst):
    """Generic exact coefficient matching, deliberately not the rank-one route."""
    k = inst["k"]
    augmented = [[Fraction(x) for x in row] +
                 [Fraction(1 if i % 2 == 0 else -1)]
                 for i, row in enumerate(inst["matrix"])]
    operations = 4 * k * k  # forming the Jacobi/Hall coefficient system
    for col in range(k):
        pivot = next((r for r in range(col, k) if augmented[r][col]), None)
        if pivot is None:
            return None, operations
        if pivot != col:
            augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        pivot_value = augmented[col][col]
        for j in range(col, k + 1):
            augmented[col][j] /= pivot_value
            operations += 1
        for row in range(k):
            if row == col or not augmented[row][col]:
                continue
            factor = augmented[row][col]
            for j in range(col, k + 1):
                augmented[row][j] -= factor * augmented[col][j]
                operations += 2
    result = []
    for row in augmented:
        value = row[-1]
        result.append([value.numerator, value.denominator])
    return result, operations


def _attack_outlier(inst):
    c = _target_coefficients(inst["k"])
    scores = [sum(abs(inst["matrix"][i][j]) for i in range(inst["k"]))
              for j in range(inst["k"])]
    median = statistics.median(scores)
    guess = [c[j] if scores[j] <= median else -c[j] for j in range(inst["k"])]
    return [[x, 1] for x in guess]


def _attack_greedy(inst):
    k = inst["k"]
    c = _target_coefficients(k)
    x = [0] * k
    bound = inst["coefficient_bound"]
    for i in range(k):
        residual = c[i] - sum(inst["matrix"][i][j] * x[j] for j in range(i))
        diagonal = inst["matrix"][i][i]
        if diagonal:
            value = int(round(residual / diagonal))
            x[i] = max(-bound, min(bound, value))
    return [[value, 1] for value in x]


def _attack_unmixed(inst):
    return [[x, 1] for x in _target_coefficients(inst["k"])]


def _permuted_instance(inst, permutation):
    out = {key: value for key, value in inst.items() if key not in ("matrix", "answer")}
    out["matrix"] = [[row[j] for j in permutation] for row in inst["matrix"]]
    out["answer"] = [inst["answer"][j] for j in permutation]
    return out


def _renamed_instance(inst):
    out = dict(inst)
    out["generators"] = list(reversed(inst["generators"]))
    return out


def _answer_metrics(params):
    max_chars = 0
    max_tokens = 0
    elements = 0
    for seed in range(20):
        answer = make_instance(seed=seed, **params)["answer"]
        body = _format_answer(answer)
        max_chars = max(max_chars, len(body))
        max_tokens = max(max_tokens, (len(body) + 3) // 4)
        elements = max(elements, 2 * len(answer))
    return max_chars, max_tokens, elements


def selftest() -> dict:
    report = {}

    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=9137, **shipping)
    planted = json.loads(json.dumps(inst["answer"]))
    unequal = next(i for i in range(inst["k"] - 1)
                   if planted[i] != planted[i + 1])
    corruptions = {
        "drop": planted[:-1],
        "swap": planted[:unequal] + [planted[unequal + 1], planted[unequal]]
        + planted[unequal + 2:],
        "duplicate": planted + [planted[0]],
        "empty": [],
        "out_of_range": [[inst["coefficient_bound"] + 1, 1]] + planted[1:],
    }
    rejection_reasons = {}
    all_rejected = True
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        all_rejected &= not ok
        rejection_reasons[name] = reason
    distinct_reasons = len(set(rejection_reasons.values())) == len(rejection_reasons)
    report["G2_rejects_corruption"] = {
        "pass": all_rejected and distinct_reasons,
        "rejected": sum(1 for name in corruptions if rejection_reasons[name] != "ok"),
        "distinct_reasons": len(set(rejection_reasons.values())),
        "reasons": rejection_reasons,
    }

    response = ("I used the Hall recurrence.\n```text\n<answer>" +
                _format_answer(inst["answer"]) +
                "</answer>\n```\nThose are the coefficients.")
    parsed = parse_answer(response)
    garbage_cases = ["", "no answer here", "<answer>1/no</answer>",
                     "<answer>1,</answer>"]
    g3_pass = parsed == inst["answer"] and all(
        parse_answer(value) is None for value in garbage_cases)
    report["G3_round_trip"] = {
        "pass": g3_pass, "realistic_response_parsed": parsed == inst["answer"],
        "garbage_rejected": sum(parse_answer(value) is None for value in garbage_cases),
    }

    samples = 200_000
    guess_rng = random.Random(0x170807419)
    hits = 0
    t0 = time.perf_counter()
    for _ in range(samples):
        candidate = random_candidate(inst, guess_rng)
        ok, _ = verify(inst, candidate)
        hits += int(ok)
    guess_seconds = time.perf_counter() - t0
    fraction = hits / samples
    report["G4_guess_resistance"] = {
        "pass": fraction < 1e-6,
        "hits": hits, "total": samples, "observed_fraction": fraction,
        "candidate_space": str(search_space(inst)),
        "structure_aware": True, "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_seeds = list(range(8))
    attack_counts = {
        "outlier_column_l1": 0,
        "greedy_diagonal_one_pass": 0,
        "random_restart_256": 0,
        "obvious_unmixed_jacobi_ansatz": 0,
    }
    restart_checks = 0
    attack_t0 = time.perf_counter()
    reference_successes = 0
    reference_times = []
    reference_operations = []
    for seed in attack_seeds:
        test_inst = make_instance(seed=seed + 2000, **shipping)
        for name, function in (
                ("outlier_column_l1", _attack_outlier),
                ("greedy_diagonal_one_pass", _attack_greedy),
                ("obvious_unmixed_jacobi_ansatz", _attack_unmixed)):
            ok, _ = verify(test_inst, function(test_inst))
            attack_counts[name] += int(ok)
        local_rng = random.Random(seed + 9000)
        random_solved = False
        for _ in range(256):
            restart_checks += 1
            ok, _ = verify(test_inst, random_candidate(test_inst, local_rng))
            random_solved |= ok
        attack_counts["random_restart_256"] += int(random_solved)

        reference_t0 = time.perf_counter()
        reference_answer, operations = _gaussian_reference(test_inst)
        reference_times.append(time.perf_counter() - reference_t0)
        reference_operations.append(operations)
        ok, _ = verify(test_inst, reference_answer)
        reference_successes += int(ok)
    attack_seconds = time.perf_counter() - attack_t0
    attacks = {name: {"successes": successes, "attempts": len(attack_seeds)}
               for name, successes in attack_counts.items()}
    reference_wall = statistics.median(reference_times)
    reference_ops = int(statistics.median(reference_operations))
    report["G5_density_and_baseline"] = {
        "pass": fraction < 1e-6 and reference_successes == len(attack_seeds),
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_observed_solution_fraction": fraction,
        "strongest_failing_attack_wall_sec": round(attack_seconds, 6),
        "strongest_failing_attack_candidate_checks": restart_checks,
        "reference_wall_clock_sec": round(reference_wall, 6),
        "reference_exact_operations": reference_ops,
    }
    report["G6_adversary_panel"] = {
        "pass": all(value["successes"] == 0 for value in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Hall coefficient matching plus exact Gaussian elimination",
            "complexity": "O(k^3) exact rational arithmetic",
            "wall_clock_sec": round(reference_wall, 6),
            "operations": reference_ops,
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
    }

    doubled = dict(shipping)
    doubled["n"] *= 2
    doubled["mix_magnitude"] = doubled["mix_magnitude"] * 3 + 2
    large_inst = make_instance(seed=77, **doubled)
    large_ok, large_reason = verify(large_inst, large_inst["answer"])
    report["G7_scales"] = {
        "pass": large_ok and large_inst["m"] > inst["m"]
        and large_inst["mix_magnitude"] > inst["mix_magnitude"],
        "base_ambient_degree": inst["m"] + 2 * inst["steps"] + 2,
        "doubled_ambient_degree": large_inst["m"] + 2 * large_inst["steps"] + 2,
        "base_answer_coefficients": inst["k"],
        "doubled_answer_coefficients": large_inst["k"],
        "verify_reason": large_reason,
    }

    invariant_checks = 0
    preserved_checks = 0
    distinct_keys = []
    for seed in range(20):
        original = make_instance(seed=seed + 4000, **shipping)
        perm_rng = random.Random(seed + 5000)
        permutation = list(range(original["k"]))
        perm_rng.shuffle(permutation)
        permuted = _permuted_instance(original, permutation)
        renamed = _renamed_instance(original)
        composed = _renamed_instance(permuted)
        key = canonical_key(original)
        for transformed in (permuted, renamed, composed):
            invariant_checks += 1
            if canonical_key(transformed) == key:
                preserved_checks += int(verify(transformed, transformed["answer"])[0])
        distinct_keys.append(key)
    report["G8_canonical_key"] = {
        "pass": preserved_checks == invariant_checks
        and len(set(distinct_keys)) == len(distinct_keys),
        "invariance_checks": invariant_checks,
        "preserving_transformations_verified": preserved_checks,
        "unrelated_instances": len(distinct_keys),
        "distinct_unrelated_keys": len(set(distinct_keys)),
        "transformations": ["displayed basis permutation", "generator renaming",
                            "their composition"],
    }

    answer_chars, answer_tokens, answer_elements = _answer_metrics(shipping)
    intended_operations = 8 * inst["k"]
    arms = G9_RESULTS["arms"]
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    hinted_rate = hinted["solved"] / max(1, hinted["attempts"])
    placebo_rate = placebo["solved"] / max(1, placebo["attempts"])
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_operations <= 300)
    hinted_hardened = G9_RESULTS["hinted_verdict"] == "hardened"
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    report["all_passed"] = all(
        value.get("pass", False) for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
