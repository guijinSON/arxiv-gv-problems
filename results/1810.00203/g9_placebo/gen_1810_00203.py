"""Verified problem generator derived from arXiv:1810.00203.

The task stays in the paper's native finite-field/PGL objects.  A solver is
given one projective matrix of order k=(p+1)/2 and must return a factored
polynomial whose distinct roots are further trace parameters of exact order k.
The planted factors are transported from the supplied element by coprime
powers; they are never found by solving the generated root-search instance.
"""

from __future__ import annotations

import itertools
import json
import math
import os
import random
import re
import sys
import time


# Make the repository helpers available when harden.py imports this module from
# the result directory.  Only prime-field arithmetic is needed here, so the
# module remains standard-library-only when gvlib is unavailable.
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)
try:
    from gvlib import exact_matrices  # noqa: F401
except ImportError:  # pragma: no cover - documented graceful fallback
    exact_matrices = None


TRACK = "B"


PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "polynomial",
    "native_objects": [
        "2-by-2 matrix over a prime field",
        "element of PGL(2,p)",
        "split polynomial over a prime field",
        "projective trace parameters",
    ],
    "verification_operations": [
        "exact modular 2-by-2 matrix multiplication",
        "exact projective-order test by repeated squaring",
        "exact finite-field linear-factor decoding",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The squared-trace-over-determinant parameters of powers of one "
        "projective element follow a second-order trace recurrence, avoiding "
        "a scan of the whole field."
    ),
    "hardness_basis": (
        "Track B: a Section 3 sequential exact-order scan stops after the "
        "required 12 roots and measured 19,984 modular scalar operations "
        "(0.008 s) at the hard shipping audit instance, whereas the Section "
        "4 coprime-power recurrence takes 108 exact arithmetic operations."
    ),
    "max_answer_tokens": 31,
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


# n is a lower bound for p.  Seed slots move p without changing the fixed-size
# witness, so increasing n/stride grows the field-sized haystack, not the answer.
DIFFICULTY = {
    "demo": {"n": 31, "factor_count": 3, "seed_slots": 1, "seed_stride": 2},
    "easy": {
        "n": 1009,
        "factor_count": 12,
        "seed_slots": 256,
        "seed_stride": 4,
    },
    "medium": {
        "n": 5003,
        "factor_count": 12,
        "seed_slots": 256,
        "seed_stride": 16,
    },
    "hard": {
        "n": 20011,
        "factor_count": 12,
        "seed_slots": 256,
        "seed_stride": 64,
    },
}

SHIPPING_DIFFICULTY = "hard"


STRUCTURAL_HINT = (
    "The squared-trace-over-determinant invariant of powers of the supplied "
    "projective matrix obeys a second-order trace recurrence."
)
PLACEBO_HINT = (
    "The modular representatives in the factors should be kept in their "
    "required canonical order throughout the calculation."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "A split monic polynomial represented by exactly m ordered linear "
        "factors [1,c] for T+c over F_p; the m decoded nonzero roots are "
        "distinct and in increasing residue order."
    ),
    "bounds": {
        "number_of_factors": "instance field factor_count (3 in demo, 12 otherwise)",
        "degree_per_factor": 1,
        "leading_coefficient": 1,
        "coefficient_min": 0,
        "coefficient_max": "p-1",
        "maximum_factors": 12,
    },
}


NOTES = """\
Definition source: Section 2, Theorems 1 and 2, fixes k=(p+1)/2 and proves
that an order-k cyclic action on PL(F_p) has exactly two equal orbits.  Section
3 defines theta=(tr(XY))^2/det(XY), derives g_k(theta) by Cayley--Hamilton,
and Theorem 3 excludes roots belonging to proper divisors of k.  Section 4's
conjugacy-class lemma says that every order-k class meets <z> in {z^i,z^-i}
for a coprime i; its corollary and final counting theorem give phi(k)/2
admissible parameters.  These statements fix both the witness predicate and
the construction used here.

What makes the family easy with tools is the paper's Section 3 method: scan
field parameters and test the displayed matrix recurrence (or factor g_k).
The strongest literal scan stops as soon as it has the requested number of
roots; at the shipping audit instance it still takes 19,984 counted modular
scalar operations.  Therefore this is Track B, not a distributional-hardness
claim.  The compact route uses the Section 4 lemma: compute the invariant of
the supplied Z once, then transport it through small coprime powers by the
trace recurrence.  At shipping size that route takes 108 exact operations.

Generation is inverse/theorem-backed.  It first samples a prime and a seed
parameter whose companion matrix has certified projective order k, reveals
that matrix in the instance, and obtains every answer root by a coprime power.
It never enumerates the requested root set.  Seeds vary p, while conjugation,
nonzero scalar multiplication, and inversion of Z are canonicalised as the
same instance.  The adversary panel tests small coefficients, numerical
neighbours of the seed invariant, random restarts, and the tempting but wrong
ordinary-power ansatz; the full exact-order scan is reported separately as the
successful Track-B reference algorithm.
"""


_MR_BASES_64 = (2, 325, 9375, 28178, 450775, 9780504, 1795265022)


def _is_prime(value: int) -> bool:
    """Deterministic Miller--Rabin for unsigned 64-bit integers."""
    if value < 2:
        return False
    for small in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if value % small == 0:
            return value == small
    d = value - 1
    shifts = 0
    while d % 2 == 0:
        d //= 2
        shifts += 1
    for base in _MR_BASES_64:
        if base % value == 0:
            continue
        x = pow(base, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(shifts - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _prime_divisors(value: int) -> tuple[int, ...]:
    factors = []
    divisor = 2
    remaining = value
    while divisor * divisor <= remaining:
        if remaining % divisor == 0:
            factors.append(divisor)
            while remaining % divisor == 0:
                remaining //= divisor
        divisor = 3 if divisor == 2 else divisor + 2
    if remaining > 1:
        factors.append(remaining)
    return tuple(factors)


def _totient_from_factors(value: int, factors: tuple[int, ...]) -> int:
    result = value
    for prime in factors:
        result = result // prime * (prime - 1)
    return result


def _mat_mul(left, right, modulus: int):
    return [
        [
            (
                left[0][0] * right[0][0]
                + left[0][1] * right[1][0]
            )
            % modulus,
            (
                left[0][0] * right[0][1]
                + left[0][1] * right[1][1]
            )
            % modulus,
        ],
        [
            (
                left[1][0] * right[0][0]
                + left[1][1] * right[1][0]
            )
            % modulus,
            (
                left[1][0] * right[0][1]
                + left[1][1] * right[1][1]
            )
            % modulus,
        ],
    ]


def _mat_pow(matrix, exponent: int, modulus: int):
    result = [[1, 0], [0, 1]]
    base = matrix
    while exponent:
        if exponent & 1:
            result = _mat_mul(result, base, modulus)
        base = _mat_mul(base, base, modulus)
        exponent //= 2
    return result


def _mat_pow_count(matrix, exponent: int, modulus: int):
    result = [[1, 0], [0, 1]]
    base = matrix
    multiplications = 0
    while exponent:
        if exponent & 1:
            result = _mat_mul(result, base, modulus)
            multiplications += 1
        base = _mat_mul(base, base, modulus)
        multiplications += 1
        exponent //= 2
    return result, multiplications


def _is_scalar(matrix, modulus: int) -> bool:
    return (
        matrix[0][1] % modulus == 0
        and matrix[1][0] % modulus == 0
        and (matrix[0][0] - matrix[1][1]) % modulus == 0
        and matrix[0][0] % modulus != 0
    )


def _theta_matrix(theta: int, modulus: int):
    # det(A_theta)=theta, tr(A_theta)=theta, hence tr^2/det=theta.
    return [[0, modulus - 1], [theta % modulus, theta % modulus]]


def _has_exact_projective_order(
    theta: int,
    modulus: int,
    order: int,
    prime_divisors: tuple[int, ...],
) -> bool:
    if not isinstance(theta, int) or isinstance(theta, bool):
        return False
    if theta <= 0 or theta >= modulus:
        return False
    matrix = _theta_matrix(theta, modulus)
    if not _is_scalar(_mat_pow(matrix, order, modulus), modulus):
        return False
    return all(
        not _is_scalar(_mat_pow(matrix, order // prime, modulus), modulus)
        for prime in prime_divisors
    )


def _exact_order_with_count(
    theta: int,
    modulus: int,
    order: int,
    prime_divisors: tuple[int, ...],
):
    matrix = _theta_matrix(theta, modulus)
    power, matrix_multiplications = _mat_pow_count(matrix, order, modulus)
    if not _is_scalar(power, modulus):
        return False, matrix_multiplications
    for prime in prime_divisors:
        power, count = _mat_pow_count(matrix, order // prime, modulus)
        matrix_multiplications += count
        if _is_scalar(power, modulus):
            return False, matrix_multiplications
    return True, matrix_multiplications


def _matrix_invariant(matrix, modulus: int) -> int:
    trace = (matrix[0][0] + matrix[1][1]) % modulus
    determinant = (
        matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
    ) % modulus
    if determinant == 0:
        raise ValueError("matrix must be invertible")
    return trace * trace * pow(determinant, -1, modulus) % modulus


def _find_modulus(
    n: int,
    seed: int,
    factor_count: int,
    seed_slots: int,
    seed_stride: int,
):
    start = n + (seed % seed_slots) * seed_stride
    candidate = max(5, start)
    if candidate % 2 == 0:
        candidate += 1
    while candidate < 2**63:
        if _is_prime(candidate):
            order = (candidate + 1) // 2
            factors = _prime_divisors(order)
            if (
                order not in (1, 2, 6)
                and _totient_from_factors(order, factors) // 2 >= factor_count
            ):
                return candidate, order, factors
        candidate += 2
    raise ValueError("no supported 64-bit prime found")


def _coprime_power_parameters(
    theta: int,
    modulus: int,
    order: int,
    factor_count: int,
):
    """Transport theta through the first small coprime powers.

    If w is the eigenvalue ratio, theta=w+w^-1+2.  Thus c_e=theta_e-2
    satisfies c_0=2, c_1=theta-2, c_(e+1)=(theta-2)c_e-c_(e-1).
    """
    trace_ratio = (theta - 2) % modulus
    previous = 2 % modulus
    current = trace_ratio
    roots = []
    exponent = 1
    while len(roots) < factor_count:
        if math.gcd(exponent, order) == 1:
            value = (current + 2) % modulus
            if value and value not in roots:
                roots.append(value)
        exponent += 1
        previous, current = (
            current,
            (trace_ratio * current - previous) % modulus,
        )
        if exponent >= order:
            raise ValueError("not enough distinct coprime-power parameters")
    return roots, exponent - 1


def _factors_from_roots(roots, modulus: int):
    return [[1, (-root) % modulus] for root in sorted(roots)]


def make_instance(
    n: int,
    seed: int = 0,
    factor_count: int = 12,
    seed_slots: int = 256,
    seed_stride: int = 16,
) -> dict:
    """Build a root certificate from coprime powers of a known PGL element."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if (
        not isinstance(factor_count, int)
        or isinstance(factor_count, bool)
        or factor_count < 1
        or factor_count > 12
    ):
        raise ValueError("factor_count must be an integer from 1 through 12")
    if not isinstance(seed_slots, int) or seed_slots < 1:
        raise ValueError("seed_slots must be positive")
    if not isinstance(seed_stride, int) or seed_stride < 1:
        raise ValueError("seed_stride must be positive")

    modulus, order, order_factors = _find_modulus(
        n, seed, factor_count, seed_slots, seed_stride
    )
    rng = random.Random(seed)

    # Inverse generation: choose and certify the reference object before the
    # problem is exposed.  The requested roots are then transported from it.
    seed_parameter = None
    trials = 0
    while seed_parameter is None:
        trials += 1
        if trials > 100000:
            raise RuntimeError("could not sample a reference projective element")
        candidate = rng.randrange(1, modulus)
        if _has_exact_projective_order(
            candidate, modulus, order, order_factors
        ):
            seed_parameter = candidate

    reference_matrix = _theta_matrix(seed_parameter, modulus)
    roots, largest_exponent = _coprime_power_parameters(
        seed_parameter, modulus, order, factor_count
    )
    answer = _factors_from_roots(roots, modulus)

    return {
        "family": "hecke_januarial_trace_parameters",
        "size_parameter": n,
        "p": modulus,
        "k": order,
        "prime_divisors_of_k": list(order_factors),
        "factor_count": factor_count,
        "reference_matrix": reference_matrix,
        "construction_trials": trials,
        "compact_largest_exponent": largest_exponent,
        "answer": answer,
    }


def render(inst: dict) -> str:
    p = inst["p"]
    k = inst["k"]
    factors = ", ".join(str(value) for value in inst["prime_divisors_of_k"])
    matrix = inst["reference_matrix"]
    m = inst["factor_count"]
    example = json.dumps(
        [[1, (p - root) % p] for root in range(1, m + 1)],
        separators=(",", ":"),
    )
    statement = f"""Januarial trace-parameter certificate over a prime field

Work in the field F_p of integers modulo the prime p={p}.  A 2-by-2 matrix is
viewed projectively: two invertible matrices represent the same element of
PGL(2,p) when one is a nonzero scalar multiple of the other.  Consequently a
matrix has projective order k when its kth power is a nonzero scalar matrix and
no smaller positive power is scalar.

Here k=(p+1)/2={k}, whose distinct prime divisors are [{factors}].  The supplied
reference matrix

  Z = [[{matrix[0][0]}, {matrix[0][1]}],
       [{matrix[1][0]}, {matrix[1][1]}]]  (entries modulo p)

is promised to have projective order k.  For a nonzero residue theta in F_p,
define

  A_theta = [[0, -1], [theta, theta]] modulo p.

Its determinant and trace are both theta, so its conjugacy invariant
(trace(A_theta)^2 / determinant(A_theta)) modulo p is theta.  Call theta
admissible exactly when A_theta has projective order k.  Equivalently, because
the prime divisors of k are listed above, A_theta^k must be scalar and
A_theta^(k/r) must be non-scalar for every listed prime r.

Return one split monic polynomial H(T) as exactly {m} linear factors over F_p.
Encode a factor T+c as the JSON pair [1,c], with c the canonical integer in
0..p-1.  The decoded roots (-c modulo p) must be nonzero, pairwise distinct,
and the factors must be ordered by increasing decoded root.  Every decoded
root must be admissible.  Any {m} roots satisfying these rules are accepted;
repeats are forbidden.

Give your final answer inside <answer></answer> tags as a JSON list of exactly
{m} pairs [[1,c1],[1,c2],...,[1,c{m}]].
Example shape and ordering (not claimed admissible): <answer>{example}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def _decode_json_fragment(fragment: str):
    candidate = fragment.strip()
    fence = re.fullmatch(
        r"```(?:json)?\s*(.*?)\s*```", candidate, re.DOTALL | re.I
    )
    if fence:
        candidate = fence.group(1).strip()
    try:
        return json.loads(candidate)
    except (TypeError, ValueError):
        return None


def parse_answer(text: str):
    """Parse tagged/fenced JSON or a JSON list surrounded by prose."""
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer>(.*?)</answer>", text, re.DOTALL | re.I)
    if tagged:
        return _decode_json_fragment(tagged[-1])

    fenced = re.findall(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.I)
    for fragment in reversed(fenced):
        parsed = _decode_json_fragment(fragment)
        if parsed is not None:
            return parsed

    decoder = json.JSONDecoder()
    for match in re.finditer(r"\[", text):
        try:
            parsed, _ = decoder.raw_decode(text[match.start() :])
        except ValueError:
            continue
        if isinstance(parsed, list):
            return parsed
    return None


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Verify any polynomial in the language; never inspect inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list of linear factors"
    if not answer:
        return False, "factor list is empty"
    expected = inst["factor_count"]
    if len(answer) != expected:
        return False, f"wrong number of factors: expected {expected}"

    p = inst["p"]
    roots = []
    for factor in answer:
        if not isinstance(factor, list) or len(factor) != 2:
            return False, "each factor must be a two-entry list [1,c]"
        leading, constant = factor
        if (
            not isinstance(leading, int)
            or isinstance(leading, bool)
            or not isinstance(constant, int)
            or isinstance(constant, bool)
        ):
            return False, "factor coefficients must be integers"
        if leading != 1:
            return False, "every linear factor must be monic"
        if constant < 0 or constant >= p:
            return False, "factor coefficient is outside the canonical field range"
        root = (-constant) % p
        if root == 0:
            return False, "decoded roots must be nonzero"
        roots.append(root)

    if len(set(roots)) != len(roots):
        return False, "decoded roots must be pairwise distinct"
    if roots != sorted(roots):
        return False, "factors are not ordered by increasing decoded root"

    k = inst["k"]
    order_factors = tuple(inst["prime_divisors_of_k"])
    for root in roots:
        if not _has_exact_projective_order(root, p, k, order_factors):
            return False, f"decoded root {root} is not admissible"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random):
    """Uniformly sample the obvious distinct/sorted split-polynomial space."""
    roots = rng.sample(range(1, inst["p"]), inst["factor_count"])
    return _factors_from_roots(roots, inst["p"])


def search_space(inst: dict) -> int:
    return math.comb(inst["p"] - 1, inst["factor_count"])


def enumerate_all(inst: dict):
    space = search_space(inst)
    if space > 100000:
        return None
    valid = 0
    for roots in itertools.combinations(
        range(1, inst["p"]), inst["factor_count"]
    ):
        valid += int(verify(inst, _factors_from_roots(roots, inst["p"]))[0])
    return valid


def canonical_key(inst: dict) -> str:
    """Canonical under PGL conjugation, scalar choice, and Z -> Z^-1."""
    # The admissible polynomial language depends on p, k and m only.  All
    # reference matrices of exact order k are route-equivalent auxiliary data.
    return json.dumps(
        ["hecke_januarial_trace_parameters", inst["p"], inst["k"], inst["factor_count"]],
        separators=(",", ":"),
    )


def escalate(params: dict):
    """Grow the field and seed spacing while preserving twelve factors."""
    harder = dict(params)
    current_n = int(harder.get("n", 1009))
    current_stride = int(harder.get("seed_stride", 4))
    if current_n >= 2**60:
        return None
    harder["n"] = current_n * 4 + 1
    harder["seed_stride"] = current_stride * 2
    return harder


def _reference_scan(inst: dict, stop_after=None):
    """Section-3-style field scan, with transparent exact-operation counts.

    ``stop_after`` gives the honest task-solving baseline: stop once enough
    admissible parameters have been found.  Passing ``None`` scans the full
    field, which selftest uses only to audit the exact density independently.
    """
    p = inst["p"]
    k = inst["k"]
    divisors = tuple(inst["prime_divisors_of_k"])
    started = time.perf_counter()
    valid = []
    matrix_multiplications = 0
    for theta in range(1, p):
        ok, count = _exact_order_with_count(theta, p, k, divisors)
        matrix_multiplications += count
        if ok:
            valid.append(theta)
            if stop_after is not None and len(valid) >= stop_after:
                break
    elapsed = time.perf_counter() - started
    # Each 2-by-2 product evaluates four entries, each with two scalar
    # multiplications, one addition, and one modular reduction.
    modular_scalar_operations = 16 * matrix_multiplications
    return tuple(valid), {
        "wall_clock_sec": elapsed,
        "parameters_scanned": theta,
        "matrix_multiplications": matrix_multiplications,
        "modular_scalar_operations": modular_scalar_operations,
    }


def _candidate_from_roots(inst: dict, roots):
    return _factors_from_roots(list(roots), inst["p"])


def _attack_candidates(inst: dict, rng: random.Random):
    p = inst["p"]
    m = inst["factor_count"]
    theta0 = _matrix_invariant(inst["reference_matrix"], p)

    smallest = list(range(1, m + 1))
    neighbourhood = []
    step = 0
    while len(neighbourhood) < m:
        value = (theta0 + step) % p
        if value and value not in neighbourhood:
            neighbourhood.append(value)
        step += 1

    ordinary_powers = []
    exponent = 1
    while len(ordinary_powers) < m and exponent < p:
        value = pow(theta0, exponent, p)
        if value and value not in ordinary_powers:
            ordinary_powers.append(value)
        exponent += 1

    attacks = {
        "outlier_smallest_parameters": _candidate_from_roots(inst, smallest),
        "greedy_seed_neighbourhood": _candidate_from_roots(inst, neighbourhood),
        "ordinary_field_power_ansatz": _candidate_from_roots(inst, ordinary_powers),
    }

    last = None
    solved = False
    for _ in range(256):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            solved = True
            break
    attacks["random_restart_256"] = (last, solved)
    return attacks


def _matrix_det(matrix, p: int) -> int:
    return (
        matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]
    ) % p


def _matrix_inverse(matrix, p: int):
    determinant = _matrix_det(matrix, p)
    inverse_det = pow(determinant, -1, p)
    return [
        [matrix[1][1] * inverse_det % p, -matrix[0][1] * inverse_det % p],
        [-matrix[1][0] * inverse_det % p, matrix[0][0] * inverse_det % p],
    ]


def _conjugate(matrix, change, p: int):
    return _mat_mul(_mat_mul(change, matrix, p), _matrix_inverse(change, p), p)


ORACLE_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}


def _answer_atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(item) for item in value)
    return 1


def _intended_operation_bound(inst: dict) -> int:
    # 8 field operations form tr^2/det, two per recurrence step, one negation
    # per factor, and a conservative insertion-sort comparison budget.
    recurrence = 2 * max(0, inst["compact_largest_exponent"] - 1)
    m = inst["factor_count"]
    return 8 + recurrence + m + m * (m - 1) // 2


def selftest() -> dict:
    report = {}

    # G1: all rungs, several seeds, exact verification, and JSON nativeness.
    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 99):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping = make_instance(
        seed=20260518, **DIFFICULTY[SHIPPING_DIFFICULTY]
    )
    planted = shipping["answer"]

    # G2: five common corruptions reach five distinct messages.
    corruptions = {"drop": [factor[:] for factor in planted[:-1]], "empty": []}
    swapped = [factor[:] for factor in planted]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    corruptions["swap"] = swapped
    duplicate = [factor[:] for factor in planted]
    duplicate[1] = duplicate[0][:]
    corruptions["duplicate"] = duplicate
    outside = [factor[:] for factor in planted]
    outside[0][1] = shipping["p"]
    corruptions["out_of_range"] = outside
    rejected = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        rejected[name] = {"rejected": not ok, "reason": reason}
    reasons = [item["reason"] for item in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in rejected.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic tagged/fenced output plus malformed text.
    encoded = json.dumps(planted, separators=(",", ":"))
    response = (
        "I used the projective trace recurrence to obtain the factors.\n"
        "<answer>\n```json\n"
        + encoded
        + "\n```\n</answer>\nAll residues are canonical."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no certificate here") is None,
        "realistic_response_parsed": parsed == planted,
        "garbage_returns_none": parse_answer("no certificate here") is None,
    }

    # A full scan gives an independently checked admissible set for cheap,
    # exact membership during the 200k G4 draws.  It is a density audit, not
    # the task-solving Track-B baseline, which stops after factor_count roots.
    valid_roots, density_scan_detail = _reference_scan(shipping)
    valid_set = set(valid_roots)
    expected_root_count = _totient_from_factors(
        shipping["k"], tuple(shipping["prime_divisors_of_k"])
    ) // 2
    scan_answer = _factors_from_roots(
        valid_roots[: shipping["factor_count"]], shipping["p"]
    )
    reference_ok, reference_reason = verify(shipping, scan_answer)
    reference_roots, reference_detail = _reference_scan(
        shipping, stop_after=shipping["factor_count"]
    )
    early_scan_answer = _factors_from_roots(reference_roots, shipping["p"])
    early_reference_ok, early_reference_reason = verify(
        shipping, early_scan_answer
    )

    sample_total = 200000
    sample_hits = 0
    guess_rng = random.Random(181000203)
    density_started = time.perf_counter()
    for _ in range(sample_total):
        candidate = random_candidate(shipping, guess_rng)
        roots = [(-factor[1]) % shipping["p"] for factor in candidate]
        sample_hits += int(all(root in valid_set for root in roots))
    density_elapsed = time.perf_counter() - density_started
    observed_density = sample_hits / sample_total
    exact_valid_answers = math.comb(
        expected_root_count, shipping["factor_count"]
    )
    exact_space = search_space(shipping)
    exact_density = exact_valid_answers / exact_space
    report["G4_guess_resistance"] = {
        "pass": observed_density < 1e-6 and sample_total >= 200000,
        "hits": sample_hits,
        "total": sample_total,
        "observed_probability": observed_density,
        "exact_probability": exact_density,
        "valid_root_count": len(valid_roots),
        "declared_space": exact_space,
        "structure_aware": True,
        "sampling_wall_clock_sec": density_elapsed,
    }

    attack_started = time.perf_counter()
    shipping_attacks = _attack_candidates(shipping, random.Random(550203))
    restart_candidate, restart_shortcut = shipping_attacks["random_restart_256"]
    restart_success = restart_shortcut or verify(shipping, restart_candidate)[0]
    attack_elapsed = time.perf_counter() - attack_started
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_exact_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": (
            observed_density < 1e-6
            and len(valid_roots) == expected_root_count
            and reference_ok
            and early_reference_ok
            and demo_exact_count == 4
        ),
        "shipping_density_hits": sample_hits,
        "shipping_density_samples": sample_total,
        "shipping_density_estimate": observed_density,
        "shipping_exact_density_from_Section_4_count": exact_density,
        "shipping_exact_valid_answer_count": exact_valid_answers,
        "shipping_certificate_space": exact_space,
        "demo_exact_valid_answer_count": demo_exact_count,
        "demo_certificate_space": search_space(demo),
        "strongest_failing_attack_wall_sec": attack_elapsed,
        "strongest_failing_attack_iterations": 256,
        "strongest_failing_attack_successes": int(restart_success),
        "reference_algorithm_wall_sec": reference_detail["wall_clock_sec"],
        "reference_algorithm_parameters_scanned": reference_detail[
            "parameters_scanned"
        ],
        "reference_algorithm_matrix_multiplications": reference_detail[
            "matrix_multiplications"
        ],
        "reference_algorithm_modular_scalar_operations": reference_detail[
            "modular_scalar_operations"
        ],
        "reference_algorithm_verify_reason": reference_reason,
        "reference_algorithm_early_stop_verify_reason": early_reference_reason,
        "density_audit_full_scan_wall_sec": density_scan_detail["wall_clock_sec"],
        "density_audit_full_scan_parameters": density_scan_detail[
            "parameters_scanned"
        ],
        "density_audit_full_scan_modular_scalar_operations": density_scan_detail[
            "modular_scalar_operations"
        ],
    }

    # G6: four no-tool attacks fail; the exact scan succeeds separately.
    attack_names = (
        "outlier_smallest_parameters",
        "greedy_seed_neighbourhood",
        "random_restart_256",
        "ordinary_field_power_ansatz",
    )
    panel = {name: {"successes": 0, "attempts": 8} for name in attack_names}
    reference_successes = 0
    reference_times = []
    reference_matrix_counts = []
    reference_scalar_counts = []
    for offset in range(8):
        inst = make_instance(
            seed=8800 + offset, **DIFFICULTY[SHIPPING_DIFFICULTY]
        )
        bundle = _attack_candidates(inst, random.Random(9900 + offset))
        for name in attack_names:
            if name == "random_restart_256":
                candidate, shortcut = bundle[name]
                success = shortcut or verify(inst, candidate)[0]
            else:
                success = verify(inst, bundle[name])[0]
            panel[name]["successes"] += int(success)

        scan, detail = _reference_scan(
            inst, stop_after=inst["factor_count"]
        )
        candidate = _factors_from_roots(scan[: inst["factor_count"]], inst["p"])
        reference_successes += int(verify(inst, candidate)[0])
        reference_times.append(detail["wall_clock_sec"])
        reference_matrix_counts.append(detail["matrix_multiplications"])
        reference_scalar_counts.append(detail["modular_scalar_operations"])
    all_failed = all(item["successes"] == 0 for item in panel.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": panel,
        "reference_algorithm": {
            "name": "Section 3 sequential exact-order scan, stopping after 12 roots",
            "complexity": (
                "O(p * omega(k) * log k) worst-case exact time; "
                "O(factor_count) output memory"
            ),
            "wall_clock_sec_mean": sum(reference_times) / len(reference_times),
            "wall_clock_sec_max": max(reference_times),
            "matrix_multiplications_max": max(reference_matrix_counts),
            "operations": max(reference_scalar_counts),
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    # G7: field/cardinality growth, then an n-doubled construction and G1 check.
    spaces = {
        name: search_space(make_instance(seed=17, **params))
        for name, params in DIFFICULTY.items()
    }
    named_spaces = list(spaces.values())
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled_params["seed_stride"] *= 2
    doubled = make_instance(seed=17, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": all(a < b for a, b in zip(named_spaces, named_spaces[1:]))
        and doubled_ok
        and doubled["p"] > shipping["p"],
        "search_spaces": spaces,
        "shipping_modulus": shipping["p"],
        "doubled_n": doubled_params["n"],
        "doubled_modulus": doubled["p"],
        "doubled_search_space": search_space(doubled),
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
    }

    # G8: conjugation, projective scalar choice, inversion, and composition.
    invariant_checks = 0
    witness_transport_checks = 0
    invariant_failures = []
    distinct_keys = []
    for offset in range(20):
        inst = make_instance(
            seed=12000 + offset, **DIFFICULTY[SHIPPING_DIFFICULTY]
        )
        key = canonical_key(inst)
        distinct_keys.append(key)
        p = inst["p"]
        z = inst["reference_matrix"]

        change = [[1, (offset + 1) % p], [1, (offset + 2) % p]]
        if _matrix_det(change, p) == 0:
            change = [[1, 1], [1, 3]]
        conjugated = dict(inst)
        conjugated["reference_matrix"] = _conjugate(z, change, p)

        scalar = offset + 2
        scaled = dict(inst)
        scaled["reference_matrix"] = [
            [scalar * entry % p for entry in row] for row in z
        ]

        inverted = dict(inst)
        inverted["reference_matrix"] = _matrix_inverse(z, p)

        composed = dict(inst)
        composite_matrix = _conjugate(_matrix_inverse(z, p), change, p)
        composed["reference_matrix"] = [
            [scalar * entry % p for entry in row] for row in composite_matrix
        ]

        for label, transformed in (
            ("conjugation", conjugated),
            ("nonzero scalar", scaled),
            ("inversion", inverted),
            ("composed", composed),
        ):
            invariant_checks += 1
            if canonical_key(transformed) != key:
                invariant_failures.append(f"seed {offset}: {label}")
            witness_transport_checks += int(
                verify(transformed, inst["answer"])[0]
            )

    report["G8_canonical_key"] = {
        "pass": (
            not invariant_failures
            and witness_transport_checks == invariant_checks
            and len(set(distinct_keys)) == 20
        ),
        "invariance_checks": invariant_checks,
        "witness_transport_checks": witness_transport_checks,
        "invariance_failures": invariant_failures,
        "unrelated_distinct": len(set(distinct_keys)),
        "unrelated_attempts": 20,
        "transformations": [
            "PGL conjugation",
            "nonzero scalar representative",
            "projective inversion",
            "composition of all three",
        ],
    }

    # G9: transcript arms are patched after script-owned runs.  Under the
    # current contract they are diagnostic; only the measured caps gate.
    answer_blob = json.dumps(planted, separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(planted)
    intended_operations = _intended_operation_bound(shipping)
    arms = {
        key: dict(ORACLE_ARM_RESULTS[key])
        for key in ("bare", "hinted", "placebo")
    }
    hinted_minus_placebo = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]
        else 0.0
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "caps_pass": within_caps,
        "diagnostic_complete": all(arms[key]["attempts"] > 0 for key in arms),
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": ORACLE_ARM_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    report["shipping_instance_audit"] = {
        "seed": 20260518,
        "p": shipping["p"],
        "k": shipping["k"],
        "reference_parameter_count": len(valid_roots),
    }
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
