"""Native Track-B generator for CM-field Thue equations.

The paper's Theorem 1 applies to binary forms over a totally real field when
one root generates a CM-field.  This module uses K=Q and power-of-two degree d:

    F(X,Y) = L0(X,Y)^d + (s L1(X,Y))^d,

where (L0,L1) is an integral unimodular change of variables and s is a power
of ten.  A root generates Q(zeta_(2d)), a cyclotomic CM-field.  Generation
chooses an integral pair first and evaluates F there, so it never solves the
instance it emits.  Verification is independent exact substitution.
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
from fractions import Fraction


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import rationals, sparse_poly  # noqa: F401
except ImportError:  # The integer-specialized implementation remains standalone.
    rationals = sparse_poly = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "number_theory",
    "object_regime": "integer_lattice",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "irreducible homogeneous binary form over Z",
        "CM-field Thue equation F(X,Y)=b",
        "bounded integral point (x,y)",
    ],
    "verification_operations": [
        "exact homogeneous-polynomial substitution",
        "exact integer multiplication and addition",
        "inclusive integer-bound comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Binomial-normalized coefficients form a rank-two recurrence that reveals "
        "unimodular coordinates in which the right side separates into two even "
        "powers; without that structure one must run a bounded Thue search."
    ),
    "hardness_basis": (
        "Track B: Section 5's SOLVE-THUE-1 computes all solutions and Section 2 "
        "explicitly identifies exhaustive search as the mechanical fallback; the "
        "executable reference here diagonalizes exactly and scans the full feasible "
        "second-coordinate interval in O(V log d) exact operations.  At the initial "
        "hard shipping preset the final measured mean is 1.176 seconds and the worst "
        "trial takes 3,414,289 counted operations, whereas the recurrence-and-radix "
        "route uses 116 exact operations."
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


# n is the feasible transformed-coordinate radius used by the mechanical scan.
# Degree, shear height, and decimal radix are independent hardness axes; none of
# them changes the two-integer answer shape.
DIFFICULTY = {
    "demo": {"n": 3, "degree": 4, "shear_bound": 1, "radix_digits": 1},
    "easy": {"n": 20_000, "degree": 8, "shear_bound": 3, "radix_digits": 4},
    "medium": {"n": 80_000, "degree": 16, "shear_bound": 4, "radix_digits": 6},
    "hard": {"n": 240_000, "degree": 32, "shear_bound": 5, "radix_digits": 8},
}
SHIPPING_DIFFICULTY = "hard"


STRUCTURAL_HINT = (
    "After binomial normalization, the coefficient sequence has Hankel rank two "
    "and its rational modes come from a unimodular coordinate pair."
)
PLACEBO_HINT = (
    "The coefficients are intentionally unordered, so keep the exponent labels, "
    "large integer signs, and stated bounds consistently aligned."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "An ordered JSON list [x,y] of exactly two base-10 integers, each in the "
        "displayed inclusive interval [-B,B].  Order matters, equal coordinates "
        "are allowed, and no quotient by sign symmetries is taken."
    ),
    "bounds": {
        "elements": 2,
        "coordinate_interval": "[-B,B] inclusive, with B supplied per instance",
        "ordered": True,
        "repetitions": True,
    },
}


NOTES = (
    "Section 2, Theorem 1 fixes the exact native object: a degree-n binary form "
    "over the integers of a totally real field, a nonzero right side, and a root "
    "whose extension is a CM-field.  It explicitly permits n>=2 and does not add "
    "an irreducibility hypothesis.  Here d is a power of two at least four; "
    "U^d+(sV)^d is a scaled cyclotomic form Phi_(2d), so a root generates the "
    "cyclotomic CM-field Q(zeta_(2d)), and an SL(2,Z) substitution preserves that "
    "field.  Section 5 gives SOLVE-THUE-1; its Step 1 enumerates bounded-height "
    "elements, while the paragraph after the algorithm says bounded-height and "
    "root-of-unity algorithms exist and the remaining work can be done in MAGMA "
    "or MAPLE.  Section 2 also says exhaustive search supplies the solutions when "
    "the bound is usable.  These results rule out Track A but license Track B.  "
    "The witness is inverse-generated before expansion.  Shuffled coefficient "
    "rows and signed/permuted variables remove positional signals; the panel tests "
    "an endpoint outlier, an eight-ray greedy rule, a one-mode ansatz after exact "
    "diagonalization, and structure-aware random restarts.  The successful exact "
    "diagonalize-and-scan method is reported separately as the Track-B reference."
)


# Updated only from completed script-owned hardening runs.  The current API
# budget ended after one bare hard-preset failure; zero-attempt arms are kept
# explicit so selftest cannot accidentally turn missing evidence into a pass.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 1},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run_api_budget_exhausted",
}


def _is_plain_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_power_of_two(value):
    return _is_plain_int(value) and value > 0 and value & (value - 1) == 0


def _is_power_of_ten(value):
    if not _is_plain_int(value) or value < 10:
        return False
    while value % 10 == 0:
        value //= 10
    return value == 1


def _nonzero_integer(rng, bound):
    value = rng.randint(1, 2 * bound)
    return value if value <= bound else -(value - bound)


def _draw_unimodular(rng, bound):
    """Draw T(p)L(q)T(r), rejecting degenerate displayed entries."""
    while True:
        p = _nonzero_integer(rng, bound)
        q = _nonzero_integer(rng, bound)
        r = _nonzero_integer(rng, bound)
        a = 1 + p * q
        b = (1 + p * q) * r + p
        c = q
        d = q * r + 1
        if a and b and c and d and a * d - b * c == 1:
            return a, b, c, d


def _form_coefficients(degree, scale, matrix):
    a, b, c, d = matrix
    sd = scale**degree
    return [
        math.comb(degree, k)
        * (a ** (degree - k) * b**k + sd * c ** (degree - k) * d**k)
        for k in range(degree + 1)
    ]


def _evaluate_homogeneous(coefficients, x, y):
    """Evaluate sum c_k X^(d-k)Y^k using exact homogeneous Horner."""
    acc = coefficients[0]
    y_power = 1
    for coefficient in coefficients[1:]:
        y_power *= y
        acc = acc * x + coefficient * y_power
    return acc


def _coefficient_terms(coefficients, rng=None):
    terms = [
        {"y_exponent": k, "coefficient": coefficient}
        for k, coefficient in enumerate(coefficients)
    ]
    if rng is not None:
        rng.shuffle(terms)
    return terms


def _decode_instance(inst):
    if not isinstance(inst, dict):
        return None
    degree = inst.get("degree")
    rhs = inst.get("rhs")
    bound = inst.get("coordinate_bound")
    terms = inst.get("coefficient_terms")
    if (
        not _is_power_of_two(degree)
        or not 4 <= degree <= 128
        or not _is_plain_int(rhs)
        or rhs <= 0
        or not _is_plain_int(bound)
        or bound < 1
        or not isinstance(terms, list)
        or len(terms) != degree + 1
    ):
        return None
    coefficients = [None] * (degree + 1)
    for term in terms:
        if not isinstance(term, dict) or set(term) != {"y_exponent", "coefficient"}:
            return None
        k = term["y_exponent"]
        coefficient = term["coefficient"]
        if (
            not _is_plain_int(k)
            or not 0 <= k <= degree
            or coefficients[k] is not None
            or not _is_plain_int(coefficient)
        ):
            return None
        coefficients[k] = coefficient
    if any(value is None for value in coefficients):
        return None
    return degree, rhs, bound, coefficients


def make_instance(n, seed=0, **params):
    """Choose a witness first, then construct and expand its CM-field form."""
    degree = params.pop("degree", 16)
    shear_bound = params.pop("shear_bound", 4)
    radix_digits = params.pop("radix_digits", 6)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if not _is_plain_int(n) or not 2 <= n <= 2_000_000:
        raise ValueError("n must be an integer in [2,2000000]")
    if not _is_power_of_two(degree) or not 4 <= degree <= 128:
        raise ValueError("degree must be a power of two in [4,128]")
    if not _is_plain_int(shear_bound) or not 1 <= shear_bound <= 20:
        raise ValueError("shear_bound must be an integer in [1,20]")
    if not _is_plain_int(radix_digits) or not 1 <= radix_digits <= 32:
        raise ValueError("radix_digits must be an integer in [1,32]")
    if not _is_plain_int(seed):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    matrix = _draw_unimodular(rng, shear_bound)
    a, b, c, d = matrix
    scale = 10**radix_digits

    # Both transformed coordinates are nonzero.  |u|<scale is the compact
    # radix separation, while |v| lies high in [1,n] so the generic scan pays.
    u_abs = rng.randint(max(1, scale // 5), scale - 1)
    v_abs = rng.randint(max(1, n // 2), n)
    u = u_abs if rng.randrange(2) else -u_abs
    v = v_abs if rng.randrange(2) else -v_abs

    # det(matrix)=1, so the inverse is integral.
    x = d * u - b * v
    y = -c * u + a * v
    coefficients = _form_coefficients(degree, scale, matrix)
    rhs = u_abs**degree + scale**degree * v_abs**degree

    # Include all four sign choices of the transformed even powers in the box.
    coordinate_bound = max(
        abs(d) * u_abs + abs(b) * v_abs,
        abs(c) * u_abs + abs(a) * v_abs,
    )
    answer = [x, y]
    return {
        "family": "bounded integral point on a CM-field Thue equation",
        "degree": degree,
        "rhs": rhs,
        "coordinate_bound": coordinate_bound,
        "coefficient_terms": _coefficient_terms(coefficients, rng),
        "answer": answer,
    }


def render(inst):
    decoded = _decode_instance(inst)
    if decoded is None:
        raise ValueError("malformed instance")
    degree, rhs, bound, _coefficients = decoded
    lines = "\n".join(
        f"  {term['y_exponent']} {term['coefficient']}"
        for term in inst["coefficient_terms"]
    )
    statement = f"""Find a bounded integral solution of an exact binary-form equation.

A homogeneous binary form of degree d={degree} is

  F(X,Y) = sum from k=0 to {degree} of c_k * X^({degree}-k) * Y^k.

Every coefficient c_k is an integer.  The following unordered lines give all
coefficients exactly as `k c_k`; k is the exponent of Y, so the exponent of X
is {degree}-k.  A listed zero is a genuine zero coefficient, and no coefficient
is omitted:

{lines}

Find any ordered pair of ordinary integers (x,y) satisfying

  F(x,y) = {rhs}

and the inclusive bounds -{bound} <= x <= {bound} and
-{bound} <= y <= {bound}.  At least one such pair is promised.  The order is
X-coordinate first and Y-coordinate second; signs matter, while x=y is allowed.
All arithmetic is over the ordinary integers, with no modular reduction.

Give your final answer inside <answer></answer> tags as one JSON list [x,y] of
exactly two base-10 integers.
Example of the required syntax: <answer>[3,-17]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Extract the last tagged JSON pair, tolerating prose and code fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        answer = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        match = re.fullmatch(r"\(?\s*([+-]?\d+)\s*,\s*([+-]?\d+)\s*\)?", body)
        if not match:
            return None
        answer = [int(match.group(1)), int(match.group(2))]
    if not isinstance(answer, list):
        return None
    if any(not _is_plain_int(value) for value in answer):
        return None
    return answer


def verify(inst, answer):
    decoded = _decode_instance(inst)
    if decoded is None:
        return False, "malformed instance"
    degree, rhs, bound, coefficients = decoded
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) < 2:
        return False, f"answer has {len(answer)} coordinate; expected 2"
    if len(answer) > 2:
        return False, f"answer has {len(answer)} coordinates; expected exactly 2"
    x, y = answer
    if not _is_plain_int(x) or not _is_plain_int(y):
        return False, "both coordinates must be ordinary integers"
    if not -bound <= x <= bound:
        return False, "x is outside the inclusive coordinate bound"
    if not -bound <= y <= bound:
        return False, "y is outside the inclusive coordinate bound"
    if _evaluate_homogeneous(coefficients, x, y) != rhs:
        return False, "exact substitution gives a nonzero residual"
    return True, "ok"


def random_candidate(inst, rng):
    decoded = _decode_instance(inst)
    if decoded is None or not hasattr(rng, "randint"):
        return []
    _degree, _rhs, bound, _coefficients = decoded
    return [rng.randint(-bound, bound), rng.randint(-bound, bound)]


def search_space(inst):
    decoded = _decode_instance(inst)
    if decoded is None:
        return None
    return (2 * decoded[2] + 1) ** 2


def enumerate_all(inst):
    decoded = _decode_instance(inst)
    if decoded is None:
        return None
    _degree, _rhs, bound, _coefficients = decoded
    if (2 * bound + 1) ** 2 > 200_000:
        return None
    total = 0
    for x in range(-bound, bound + 1):
        for y in range(-bound, bound + 1):
            total += int(verify(inst, [x, y])[0])
    return total


def _sqrt_fraction_exact(value):
    if not isinstance(value, Fraction) or value < 0:
        return None
    numerator = math.isqrt(value.numerator)
    denominator = math.isqrt(value.denominator)
    if numerator * numerator != value.numerator or denominator * denominator != value.denominator:
        return None
    return Fraction(numerator, denominator)


def _floor_power_two_root(value, degree):
    if not _is_plain_int(value) or value < 0 or not _is_power_of_two(degree):
        return None
    root = value
    for _ in range(degree.bit_length() - 1):
        root = math.isqrt(root)
    return root


def _exact_power_two_root(value, degree):
    root = _floor_power_two_root(value, degree)
    if root is None or root**degree != value:
        return None
    return root


def _recover_diagonal(inst):
    """Recover rank-two Waring data from four normalized coefficients."""
    decoded = _decode_instance(inst)
    if decoded is None:
        return None
    degree, _rhs, _bound, coefficients = decoded
    moments = [
        Fraction(coefficients[k], math.comb(degree, k)) for k in range(4)
    ]
    m0, m1, m2, m3 = moments
    delta = m0 * m2 - m1 * m1
    if delta == 0:
        return None
    mode_sum = (m0 * m3 - m1 * m2) / delta
    mode_product = (m1 * m3 - m2 * m2) / delta
    discriminant_root = _sqrt_fraction_exact(mode_sum * mode_sum - 4 * mode_product)
    if discriminant_root is None or discriminant_root == 0:
        return None
    roots = [
        (mode_sum + discriminant_root) / 2,
        (mode_sum - discriminant_root) / 2,
    ]
    weights = [
        (m1 - roots[1] * m0) / (roots[0] - roots[1]),
        (m1 - roots[0] * m0) / (roots[1] - roots[0]),
    ]

    for first, second in ((0, 1), (1, 0)):
        wa, wz = weights[first], weights[second]
        if wa.denominator != 1 or wz.denominator != 1 or wa <= 0 or wz <= 0:
            continue
        a_abs = _exact_power_two_root(wa.numerator, degree)
        scaled_c_abs = _exact_power_two_root(wz.numerator, degree)
        if a_abs is None or scaled_c_abs is None:
            continue
        ra, rc = roots[first], roots[second]
        c_abs_q = Fraction(1, 1) / (a_abs * abs(rc - ra))
        if c_abs_q.denominator != 1 or c_abs_q <= 0:
            continue
        c_abs = c_abs_q.numerator
        if scaled_c_abs % c_abs:
            continue
        scale = scaled_c_abs // c_abs
        if not _is_power_of_ten(scale):
            continue
        b_q = ra * a_abs
        d_q = rc * c_abs
        if b_q.denominator != 1 or d_q.denominator != 1:
            continue
        matrix = (a_abs, b_q.numerator, c_abs, d_q.numerator)
        if abs(matrix[0] * matrix[3] - matrix[1] * matrix[2]) != 1:
            continue
        if _form_coefficients(degree, scale, matrix) == coefficients:
            return degree, scale, matrix
    return None


def _invert_coordinates(matrix, u, v):
    a, b, c, d = matrix
    determinant = a * d - b * c
    x_num = d * u - b * v
    y_num = -c * u + a * v
    if determinant not in (-1, 1):
        return None
    return [x_num // determinant, y_num // determinant]


def _compact_solution(inst):
    recovered = _recover_diagonal(inst)
    decoded = _decode_instance(inst)
    if recovered is None or decoded is None:
        return None
    degree, scale, matrix = recovered
    rhs = decoded[1]
    radix = scale**degree
    u_abs = _exact_power_two_root(rhs % radix, degree)
    v_abs = _exact_power_two_root(rhs // radix, degree)
    if u_abs is None or v_abs is None:
        return None
    for su, sv in itertools.product((-1, 1), repeat=2):
        candidate = _invert_coordinates(matrix, su * u_abs, sv * v_abs)
        if candidate is not None and verify(inst, candidate)[0]:
            return candidate
    return None


def _intended_route_operations(degree):
    # Scan the unordered coefficient labels, normalize four terms, solve the
    # 2x2 recurrence, take exact roots, split one radix, and test four signs.
    return degree + 84


def _reference_scan(inst):
    """Exact generic diagonal scan, deliberately not using radix separation."""
    recovered = _recover_diagonal(inst)
    decoded = _decode_instance(inst)
    if recovered is None or decoded is None:
        return None, {"iterations": 0, "exact_operations": 0}
    degree, scale, matrix = recovered
    rhs, bound = decoded[1], decoded[2]
    radix = scale**degree
    outer_root = _floor_power_two_root(rhs, degree)
    if outer_root is None:
        return None, {"iterations": 0, "exact_operations": 0}
    v_max = outer_root // scale
    root_steps = degree.bit_length() - 1
    operations = _intended_route_operations(degree)
    iterations = 0
    for v_abs in range(v_max + 1):
        iterations += 1
        remainder = rhs - radix * v_abs**degree
        operations += 2 * root_steps + 5
        if remainder < 0:
            break
        u_abs = _exact_power_two_root(remainder, degree)
        if u_abs is None:
            continue
        for su, sv in itertools.product((-1, 1), repeat=2):
            candidate = _invert_coordinates(matrix, su * u_abs, sv * v_abs)
            operations += 8
            if candidate is not None and all(-bound <= z <= bound for z in candidate):
                if verify(inst, candidate)[0]:
                    return candidate, {
                        "iterations": iterations,
                        "exact_operations": operations,
                    }
    return None, {"iterations": iterations, "exact_operations": operations}


def _signed_permutation_coefficients(coefficients, swap, sign_x, sign_y):
    degree = len(coefficients) - 1
    out = [0] * (degree + 1)
    for k, coefficient in enumerate(coefficients):
        signed = coefficient * sign_x ** (degree - k) * sign_y**k
        if swap:
            out[degree - k] = signed
        else:
            out[k] = signed
    return out


def _relabel_instance(inst, swap, sign_x, sign_y, shuffle_seed):
    decoded = _decode_instance(inst)
    if decoded is None:
        raise ValueError("malformed instance")
    degree, rhs, bound, coefficients = decoded
    transformed = _signed_permutation_coefficients(
        coefficients, swap, sign_x, sign_y
    )
    old_x, old_y = inst["answer"]
    if swap:
        answer = [sign_y * old_y, sign_x * old_x]
    else:
        answer = [sign_x * old_x, sign_y * old_y]
    rng = random.Random(shuffle_seed)
    return {
        "family": inst["family"],
        "degree": degree,
        "rhs": rhs,
        "coordinate_bound": bound,
        "coefficient_terms": _coefficient_terms(transformed, rng),
        "answer": answer,
    }


def canonical_key(inst):
    """Canonicalize row order and every signed permutation of X and Y."""
    decoded = _decode_instance(inst)
    if decoded is None:
        return "malformed"
    degree, rhs, bound, coefficients = decoded
    forms = []
    for swap, sign_x, sign_y in itertools.product((False, True), (-1, 1), (-1, 1)):
        forms.append(
            tuple(
                _signed_permutation_coefficients(
                    coefficients, swap, sign_x, sign_y
                )
            )
        )
    payload = json.dumps(
        [degree, rhs, bound, min(forms)], separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params):
    """Increase three fixed-answer-length axes, respecting the route cap."""
    out = {key: value for key, value in params.items() if key != "_preset"}
    degree = out.get("degree", 16)
    if degree < 64:
        out["degree"] = degree * 2
        out["n"] = min(2_000_000, out.get("n", 80_000) * 2)
        out["radix_digits"] = min(32, out.get("radix_digits", 6) + 2)
        out["shear_bound"] = min(20, out.get("shear_bound", 4) + 1)
        return out
    if out.get("n", 0) < 2_000_000:
        out["n"] = min(2_000_000, out["n"] * 2)
        out["radix_digits"] = min(32, out.get("radix_digits", 8) + 2)
        out["shear_bound"] = min(20, out.get("shear_bound", 5) + 1)
        return out
    return None


def _ray_candidates(inst, rays):
    decoded = _decode_instance(inst)
    if decoded is None:
        return []
    degree, rhs, bound, coefficients = decoded
    candidates = []
    for dx, dy in rays:
        value = _evaluate_homogeneous(coefficients, dx, dy)
        if value <= 0:
            continue
        multiplier = _floor_power_two_root(rhs // value, degree)
        if multiplier is None:
            continue
        for offset in (0, 1, -1):
            z = multiplier + offset
            candidate = [z * dx, z * dy]
            if all(-bound <= item <= bound for item in candidate):
                candidates.append(candidate)
    return candidates


def _attack_candidates(inst, seed):
    decoded = _decode_instance(inst)
    degree, rhs, bound, coefficients = decoded
    endpoint = (1, 0) if abs(coefficients[0]) <= abs(coefficients[-1]) else (0, 1)
    outlier = _ray_candidates(inst, [endpoint])
    greedy = _ray_candidates(
        inst,
        [(1, 0), (0, 1), (1, 1), (1, -1), (2, 1), (1, 2), (2, -1), (1, -2)],
    )

    one_mode = []
    recovered = _recover_diagonal(inst)
    if recovered is not None:
        _degree, scale, matrix = recovered
        dominant = _floor_power_two_root(rhs, degree)
        if dominant is not None:
            guesses = [(dominant, 0), (-dominant, 0)]
            v_guess = dominant // scale
            guesses.extend([(0, v_guess), (0, -v_guess)])
            for u, v in guesses:
                candidate = _invert_coordinates(matrix, u, v)
                if candidate is not None and all(-bound <= item <= bound for item in candidate):
                    one_mode.append(candidate)

    rng = random.Random(seed ^ 0x14076556)
    randoms = [random_candidate(inst, rng) for _ in range(256)]
    return {
        "outlier_smaller_endpoint": outlier,
        "greedy_eight_integer_rays": greedy,
        "by_hand_one_mode_ansatz": one_mode,
        "random_restart_256_bounded_pairs": randoms,
    }


def selftest():
    report = {}
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
    }

    inst = make_instance(seed=19, **shipping)
    answer = inst["answer"]
    swapped = [answer[1], answer[0]]
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": answer + answer[:1],
        "empty": [],
        "out_of_range": [inst["coordinate_bound"] + 1, answer[1]],
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
        "The recurrence gives the following integral point.\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nSubstitution is exact."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x14076556)
    guess_total = 200_000
    guess_hits = 0
    started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - started
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "structure_aware_space": search_space(inst),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = [
        "outlier_smaller_endpoint",
        "greedy_eight_integer_rays",
        "by_hand_one_mode_ansatz",
        "random_restart_256_bounded_pairs",
    ]
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_iterations = []
    reference_operations = []
    compact_successes = 0
    compact_operations = []
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        attack_sets = _attack_candidates(trial, seed)
        for name in attack_names:
            tick = time.perf_counter()
            won = any(verify(trial, candidate)[0] for candidate in attack_sets[name])
            attack_seconds[name] += time.perf_counter() - tick
            successes[name] += int(won)

        tick = time.perf_counter()
        recovered, cost = _reference_scan(trial)
        reference_seconds += time.perf_counter() - tick
        reference_iterations.append(cost["iterations"])
        reference_operations.append(cost["exact_operations"])
        reference_successes += int(recovered is not None and verify(trial, recovered)[0])

        compact = _compact_solution(trial)
        compact_successes += int(compact is not None and verify(trial, compact)[0])
        compact_operations.append(_intended_route_operations(trial["degree"]))

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name] / 8, 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "exact rank-two diagonalization plus feasible-coordinate scan",
        "complexity": "O(V log d) exact integer operations after O(1) rational recurrence recovery",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": max(reference_operations),
        "iterations": max(reference_iterations),
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "compact_route": {
            "name": "rank-two recurrence, exact radix split, and unimodular inverse",
            "operations": max(compact_operations),
            "solves": f"{compact_successes}/8",
        },
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and all_failed
        and reference_successes == 8
        and isinstance(demo_count, int)
        and demo_count >= 1,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density": guess_fraction,
        "demo_exact_solution_count": demo_count,
        "baseline_attack_wall_clock_sec": round(
            attack_seconds["random_restart_256_bounded_pairs"] / 8, 6
        ),
        "baseline_attack_iterations": 256,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
        "reference_scan_iterations": reference["iterations"],
    }

    scale_base = make_instance(seed=77, **shipping)
    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    tick = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_seconds = time.perf_counter() - tick
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    ladder_n = [params["n"] for params in DIFFICULTY.values()]
    ladder_degrees = [params["degree"] for params in DIFFICULTY.values()]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled_params["n"] == 2 * shipping["n"]
        and search_space(doubled) > search_space(scale_base)
        and ladder_n == sorted(ladder_n)
        and ladder_degrees == sorted(ladder_degrees)
        and len(set(ladder_n)) == 4
        and len(doubled["answer"]) == len(answer),
        "shipping_n": shipping["n"],
        "doubled_n": doubled_params["n"],
        "shipping_candidate_space": search_space(scale_base),
        "doubled_candidate_space": search_space(doubled),
        "doubled_build_sec": round(doubled_seconds, 6),
        "doubled_verify_reason": doubled_why,
        "answer_elements_unchanged": len(doubled["answer"]) == len(answer),
    }

    invariance_passed = 0
    carried_passed = 0
    total_symmetries = 0
    for seed in range(20):
        original = make_instance(seed=1000 + seed, **shipping)
        original_key = canonical_key(original)
        for swap, sign_x, sign_y in itertools.product((False, True), (-1, 1), (-1, 1)):
            transformed = _relabel_instance(
                original,
                swap,
                sign_x,
                sign_y,
                5000 + seed * 8 + 4 * int(swap) + 2 * (sign_x > 0) + (sign_y > 0),
            )
            total_symmetries += 1
            invariance_passed += int(canonical_key(transformed) == original_key)
            carried_passed += int(verify(transformed, transformed["answer"])[0])
    unrelated = [
        canonical_key(make_instance(seed=9000 + seed, **shipping))
        for seed in range(20)
    ]
    report["G8_canonical_key"] = {
        "pass": invariance_passed == total_symmetries
        and carried_passed == total_symmetries
        and len(set(unrelated)) == 20,
        "symmetries_tested": "all 8 signed permutations of two variables, including compositions",
        "invariance_checks_passed": invariance_passed,
        "invariance_checks_total": total_symmetries,
        "carried_certificate_checks_passed": carried_passed,
        "carried_certificate_checks_total": total_symmetries,
        "unrelated_distinct": len(set(unrelated)),
        "unrelated_total": 20,
    }

    # Report a measured worst case, not merely the convenient seed used above.
    answer_blobs = [
        json.dumps(
            make_instance(seed=seed, **shipping)["answer"],
            separators=(",", ":"),
        )
        for seed in range(1000)
    ]
    answer_chars = max(map(len, answer_blobs))
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = len(answer)
    intended_operations = _intended_route_operations(inst["degree"])
    hinted = G9_ORACLE_RESULTS["hinted"]
    placebo = G9_ORACLE_RESULTS["placebo"]
    hinted_verdict = G9_ORACLE_RESULTS["hinted_verdict"]
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": hinted_verdict == "hardened" and within_caps,
        "arms": {
            "bare": dict(G9_ORACLE_RESULTS["bare"]),
            "hinted": dict(hinted),
            "placebo": dict(placebo),
        },
        "hinted_minus_placebo": (
            hinted["solved"] / hinted["attempts"]
            - placebo["solved"] / placebo["attempts"]
            if hinted["attempts"] and placebo["attempts"]
            else None
        ),
        "hinted_verdict": hinted_verdict,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
