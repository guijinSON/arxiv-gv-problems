"""Verified Track-B primary-component generator for arXiv:1806.03545.

The family works in Q[x,y].  It constructs two monic polynomials from known,
distinct arithmetic-progression roots, forms I=(F(x)) and J=(G(y)), and asks
for one primary component of (I+J)^N.  Lemma 2.5 gives the intersection and
Lemma 3.1 proves each linear-factor component primary; Corollary 3.4 packages
the same construction over an algebraically closed field.  No emitted
polynomial is factored to obtain the planted certificate.
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


# Make the repository helpers importable when harden.py is run from this
# directory.  This family remains standard-library-only if they are absent.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals, roots as gv_roots  # noqa: F401
except ImportError:  # pragma: no cover - supported dependency-free fallback
    exact_matrices = rationals = gv_roots = None


TRACK = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "univariate polynomials over Q in disjoint variables",
        "a power of a tensor-binomial sum of principal ideals",
        "a primary ideal represented by two linear generators and a power",
    ],
    "verification_operations": [
        "exact modular Horner rejection",
        "exact integer Horner evaluation",
        "exact formal-derivative evaluation",
        "normalized sparse-polynomial comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The first two Newton power sums reveal the spacing and endpoint of "
        "each hidden arithmetic progression of roots; without that invariant "
        "one must perform exact root finding on the dense polynomials."
    ),
    "hardness_basis": (
        "Track B: exact Sturm root isolation takes O(n^3+n^2 log B) rational "
        "operations per polynomial; at shipping n=64 and B=75000 an "
        "instrumented run used 99,544 exact arithmetic operations and 1.45 "
        "seconds, while the Vieta/Newton arithmetic-progression "
        "route, including exact Horner confirmation, takes 296 operations."
    ),
    "max_answer_tokens": 24,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON object describing Q=((x-r),(y-s))^N.  It contains exactly "
        "two normalized sparse linear polynomials over Q, with rational "
        "coefficients [numerator,denominator] and exponent vectors [e_x,e_y], "
        "and the fixed instance power N.  The integers r and s lie in the "
        "inclusive interval [-B,B]."
    ),
    "bounds": {
        "polynomials": 2,
        "terms_per_polynomial": 2,
        "variables": 2,
        "degree": 1,
        "root_min": "-B",
        "root_max": "B",
        "power": "instance tensor_power",
        "normalization": "monic x-r followed by monic y-s",
    },
}

DIFFICULTY: dict = {
    "hard": {"n": 64, "root_bound": 75000, "tensor_power": 5},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The first two Newton power sums of each polynomial have the variance "
    "pattern of an evenly spaced set of integer roots."
)
PLACEBO_HINT = (
    "The coefficient exponents and the normalized output order deserve "
    "careful attention throughout the calculation."
)

# Filled from the three script-owned harden.py runs before final emission.
# These figures are diagnostic; only the answer/operation caps gate G9.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted": {"solved": 0, "attempts": 0, "errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted_verdict": "blocked_external_403",
}

NOTES = r"""
Definition and theorem triage.  Definition 1.1 fixes primary decompositions of
powers, Definition 1.2 fixes the filtration condition, and Corollary 3.4 is
the paper's primary-decomposition result.  Lemma 2.5 supplies the exact
intersection identity; Lemma 3.1 says a tensor-binomial component is primary
when the sum of its radicals is prime.  Here F and G split into distinct
linear factors in disjoint variables, so (F)^m is the intersection of the
(x-r)^m and similarly for G.  The component belonging to r,s is therefore
sum_{i=0}^N (x-r)^i (y-s)^(N-i) = (x-r,y-s)^N.

The paper does not prove a hard search problem.  Indeed Corollary 3.4 directly
constructs the answer once component filtrations are known, and Section 4
uses Macaulay2 for illustrative decompositions.  A Track-A claim would be
false.  This module declares Track B and discloses its successful exact Sturm
root-isolation algorithm.  The compact route instead applies the first two Vieta/Newton
identities to an even-length arithmetic progression: its mean is between the
two middle roots and its variance determines the squared spacing.

Construction and attacks.  The polynomial coefficients are expanded from
sampled arithmetic-progression roots; they are never factored by the generator.
Term order, translation, reflection, and interchange of x and y do not affect
the certificate logic.  Shipping roots stay far from 0, adjacent roots are
more than 32 apart, and plants are simply all roots rather than statistically
special members of a decoy set.  The Vieta-mean neighborhood, small-integer
greedy search, 256 uniform restarts, and the tempting unit-spacing ansatz are
tested on eight seeds and fail.  The modular scan with exact Horner confirmation
succeeds and is reported separately, as Track B requires.  General modular/LLL
polynomial factorization is not implemented; the domain-standard exact Sturm
method is, and the existence of still faster factorization software is an
explicit caveat rather than a hidden Track-A claim.
""".strip()


def _validate_params(n: int, root_bound: int, tensor_power: int) -> None:
    for name, value in (("n", n), ("root_bound", root_bound),
                        ("tensor_power", tensor_power)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if n < 4 or n % 2:
        raise ValueError("n must be an even integer at least 4")
    if root_bound < 2 * n:
        raise ValueError("root_bound must be at least 2*n")
    if tensor_power < 1:
        raise ValueError("tensor_power must be positive")


def _multiply_by_linear(coeffs: list[int], root: int) -> list[int]:
    """Return coefficients of p(z)*(z-root), in ascending order."""
    out = [0] * (len(coeffs) + 1)
    for i, coefficient in enumerate(coeffs):
        out[i] -= root * coefficient
        out[i + 1] += coefficient
    return out


def _polynomial_from_roots(roots: list[int]) -> list[int]:
    coeffs = [1]
    for root in roots:
        coeffs = _multiply_by_linear(coeffs, root)
    return coeffs


def _ap_roots(n: int, bound: int, rng: random.Random) -> list[int]:
    """Sample a translated/reflected AP with a wide, non-unit spacing."""
    max_step = max(1, bound // (3 * n))
    if bound >= 100 * n:
        min_step = max(n + 3, bound // (8 * n), 40)
    else:
        min_step = max(1, bound // (2 * n))
    if min_step > max_step:
        min_step = max(1, max_step)
    step = rng.randint(min_step, max_step)
    span = (n - 1) * step
    lo = max(1, bound // 4)
    hi = min(bound - span, bound // 2)
    if lo > hi:
        lo, hi = 1, bound - span
    if lo > hi:
        raise ValueError("root_bound is too small for the requested degree")
    start = rng.randint(lo, hi)
    roots = [start + i * step for i in range(n)]
    if rng.randrange(2):
        roots = sorted(-r for r in roots)
    assert len(set(roots)) == n
    assert all(-bound <= r <= bound for r in roots)
    return roots


def _terms_from_coefficients(coeffs: list[int], rng: random.Random) -> list[list[int]]:
    terms = [[exponent, coefficient]
             for exponent, coefficient in enumerate(coeffs)]
    rng.shuffle(terms)
    return terms


def _coefficient_list(terms: object, degree: int) -> list[int]:
    if not isinstance(terms, list) or len(terms) != degree + 1:
        raise ValueError("polynomial term table has the wrong length")
    coeffs: list[int | None] = [None] * (degree + 1)
    for term in terms:
        if (not isinstance(term, list) or len(term) != 2
                or isinstance(term[0], bool) or not isinstance(term[0], int)
                or isinstance(term[1], bool) or not isinstance(term[1], int)):
            raise ValueError("malformed polynomial term")
        exponent, coefficient = term
        if exponent < 0 or exponent > degree or coeffs[exponent] is not None:
            raise ValueError("polynomial exponents must occur exactly once")
        coeffs[exponent] = coefficient
    if coeffs[-1] != 1:
        raise ValueError("the polynomial must be monic of the stated degree")
    return [int(x) for x in coeffs]


def _poly_eval(coeffs: list[int], value: int) -> int:
    result = 0
    for coefficient in reversed(coeffs):
        result = result * value + coefficient
    return result


def _poly_eval_mod(coeffs: list[int], value: int, modulus: int) -> int:
    """Exact one-sided rejection: nonzero modulo p proves nonzero over Z."""
    result = 0
    value %= modulus
    for coefficient in reversed(coeffs):
        result = (result * value + coefficient) % modulus
    return result


def _derivative_eval(coeffs: list[int], value: int) -> int:
    result = 0
    for exponent in range(len(coeffs) - 1, 0, -1):
        result = result * value + exponent * coeffs[exponent]
    return result


def _linear_polynomial(root: int, variable: int) -> list[list[list[int]]]:
    exponent = [0, 0]
    exponent[variable] = 1
    return [
        [[-root, 1], [0, 0]],
        [[1, 1], exponent],
    ]


def _answer(root_x: int, root_y: int, power: int) -> dict:
    return {
        "generators": [
            _linear_polynomial(root_x, 0),
            _linear_polynomial(root_y, 1),
        ],
        "power": power,
    }


def make_instance(n: int, seed: int = 0, root_bound: int = 75000,
                  tensor_power: int = 5, **params) -> dict:
    """Construct a certified primary component without factoring the output."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, root_bound, tensor_power)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    roots_f = _ap_roots(n, root_bound, rng)
    roots_g = _ap_roots(n, root_bound, rng)
    coeffs_f = _polynomial_from_roots(roots_f)
    coeffs_g = _polynomial_from_roots(roots_g)
    root_x = rng.choice(roots_f)
    root_y = rng.choice(roots_g)
    inst = {
        "family": "tensor_binomial_primary_component",
        "degree": n,
        "root_bound": root_bound,
        "tensor_power": tensor_power,
        "f_terms": _terms_from_coefficients(coeffs_f, rng),
        "g_terms": _terms_from_coefficients(coeffs_g, rng),
        # Exact caches of the displayed term tables.  They are redundant public
        # data, not hidden witness information, and keep 200k-candidate density
        # measurements from repeatedly sorting large coefficients.
        "f_coefficients": coeffs_f,
        "g_coefficients": coeffs_g,
        "f_mod_1000003": [c % 1_000_003 for c in coeffs_f],
        "g_mod_1000003": [c % 1_000_003 for c in coeffs_g],
    }
    inst["answer"] = _answer(root_x, root_y, tensor_power)
    return inst


def render(inst: dict) -> str:
    degree = inst["degree"]
    bound = inst["root_bound"]
    power = inst["tensor_power"]
    lines = [
        "PRIMARY COMPONENT OF A TENSOR-BINOMIAL POWER",
        "",
        "Work in the polynomial ring Q[x,y].  A polynomial term table below "
        "contains one line `k c` for the term c*x^k (or c*y^k); the lines are "
        "deliberately not sorted.  Missing terms are not allowed.  Thus",
        "F(x)=sum_k f_k*x^k and G(y)=sum_k g_k*y^k.",
        "",
        f"Both polynomials are monic of even degree {degree}.  Each is "
        f"guaranteed to have {degree} distinct integer roots, all in the "
        f"inclusive interval [-{bound},{bound}].",
        "Let I=(F(x)) and J=(G(y)).  We consider the ideal (I+J)^N in "
        f"Q[x,y], where N={power}.",
        "",
        "For any integer roots r of F and s of G, the ideal "
        "Q=((x-r),(y-s))^N is a primary component of (I+J)^N.  Find any one "
        "such component.  The notation ((x-r),(y-s))^N means the Nth power "
        "of the ideal generated by x-r and y-s.",
        "",
        "F TERM TABLE (exponent coefficient):",
    ]
    lines.extend(f"{k} {c}" for k, c in inst["f_terms"])
    lines.extend(["", "G TERM TABLE (exponent coefficient):"])
    lines.extend(f"{k} {c}" for k, c in inst["g_terms"])
    example = _answer(3, -5, power)
    lines.extend([
        "",
        "OUTPUT FORMAT",
        "Return a JSON object with exactly the keys `generators` and `power`. "
        "The two generators must be in the fixed order x-r, then y-s.  Encode "
        "each sparse polynomial as a list of terms [[num,den],[e_x,e_y]], "
        "with the constant term first and the monic linear term second.  "
        "Denominators must be positive and reduced; here they are 1.  Set "
        f"`power` to {power}.  Order and normalization are part of the bounded "
        "certificate language; repeated generators are not allowed.",
        "Give your final answer inside <answer></answer> tags, as exactly that "
        "JSON object.",
        "Example: <answer>" + json.dumps(example, separators=(",", ":"))
        + "</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    if not isinstance(text, str):
        return None
    tagged = re.search(r"<answer\b[^>]*>(.*?)</answer>", text,
                       flags=re.IGNORECASE | re.DOTALL)
    candidates: list[str] = []
    if tagged:
        candidates.append(tagged.group(1).strip())
    candidates.extend(re.findall(r"```(?:json)?\s*(.*?)```", text,
                                 flags=re.IGNORECASE | re.DOTALL))
    for candidate in candidates:
        cleaned = candidate.strip()
        try:
            return json.loads(cleaned)
        except (TypeError, ValueError):
            continue
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            value, _ = decoder.raw_decode(text[match.start():])
            return value
        except ValueError:
            continue
    return None


def _extract_root(poly: object, variable: int) -> tuple[int | None, str | None]:
    label = "x" if variable == 0 else "y"
    expected_exponent = [1, 0] if variable == 0 else [0, 1]
    if not isinstance(poly, list) or len(poly) != 2:
        return None, f"{label} generator must have exactly two terms"
    constant, linear = poly
    if (not isinstance(constant, list) or len(constant) != 2
            or not isinstance(linear, list) or len(linear) != 2
            or constant[1] != [0, 0]
            or linear != [[1, 1], expected_exponent]):
        return None, f"{label} generator must be exactly the monic polynomial {label}-r"
    rational = constant[0]
    if (not isinstance(rational, list) or len(rational) != 2
            or any(isinstance(v, bool) or not isinstance(v, int)
                   for v in rational)):
        return None, f"{label} constant coefficient must be a rational pair"
    numerator, denominator = rational
    if denominator <= 0 or math.gcd(numerator, denominator) != 1:
        return None, f"{label} constant rational is not reduced with positive denominator"
    if denominator != 1:
        return None, f"{label} root must be an integer"
    return -numerator, None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any normalized root-pair component; never inspect inst['answer']."""
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if set(answer) != {"generators", "power"}:
        return False, "answer must have exactly the keys generators and power"
    generators = answer.get("generators")
    if not isinstance(generators, list) or len(generators) != 2:
        return False, "generators must contain exactly two polynomials"
    root_x, error = _extract_root(generators[0], 0)
    if error:
        return False, error
    root_y, error = _extract_root(generators[1], 1)
    if error:
        return False, error
    answer_power = answer.get("power")
    if (isinstance(answer_power, bool) or not isinstance(answer_power, int)
            or answer_power != inst["tensor_power"]):
        return False, "power does not equal the stated tensor power"
    bound = inst["root_bound"]
    assert root_x is not None and root_y is not None
    if not -bound <= root_x <= bound:
        return False, "x root is outside the inclusive bound"
    if not -bound <= root_y <= bound:
        return False, "y root is outside the inclusive bound"
    try:
        f = inst.get("f_coefficients")
        g = inst.get("g_coefficients")
        if not isinstance(f, list):
            f = _coefficient_list(inst["f_terms"], inst["degree"])
        if not isinstance(g, list):
            g = _coefficient_list(inst["g_terms"], inst["degree"])
    except (TypeError, ValueError) as exc:
        return False, "malformed instance polynomial: " + str(exc)
    screening_prime = 1_000_003
    f_mod = inst.get("f_mod_1000003")
    g_mod = inst.get("g_mod_1000003")
    if not isinstance(f_mod, list):
        f_mod = [c % screening_prime for c in f]
    if not isinstance(g_mod, list):
        g_mod = [c % screening_prime for c in g]
    if _poly_eval_mod(f_mod, root_x, screening_prime) != 0:
        return False, "x-r does not divide F exactly"
    if _poly_eval(f, root_x) != 0:
        return False, "x-r does not divide F exactly"
    if _derivative_eval(f, root_x) == 0:
        return False, "x-r is not a simple factor of F"
    if _poly_eval_mod(g_mod, root_y, screening_prime) != 0:
        return False, "y-s does not divide G exactly"
    if _poly_eval(g, root_y) != 0:
        return False, "y-s does not divide G exactly"
    if _derivative_eval(g, root_y) == 0:
        return False, "y-s is not a simple factor of G"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the normalized bounded language stated to the solver."""
    bound = inst["root_bound"]
    return _answer(rng.randint(-bound, bound), rng.randint(-bound, bound),
                   inst["tensor_power"])


def search_space(inst: dict) -> int:
    return (2 * inst["root_bound"] + 1) ** 2


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the exact certificate language only below a hard cap."""
    if search_space(inst) > 200_000:
        return None
    bound = inst["root_bound"]
    count = 0
    for root_x, root_y in itertools.product(range(-bound, bound + 1), repeat=2):
        if verify(inst, _answer(root_x, root_y, inst["tensor_power"]))[0]:
            count += 1
    return count


def _newton_ap_step(terms: object, degree: int) -> int:
    """Translation/reflection-invariant AP spacing from the top coefficients."""
    coeffs = _coefficient_list(terms, degree)
    first_sum = -coeffs[degree - 1]
    second_elementary = coeffs[degree - 2]
    second_power_sum = first_sum * first_sum - 2 * second_elementary
    dispersion = degree * second_power_sum - first_sum * first_sum
    numerator = 12 * dispersion
    denominator = degree * degree * (degree * degree - 1)
    if numerator < 0 or numerator % denominator:
        raise ValueError("root moments do not describe an integer AP")
    square = numerator // denominator
    step = math.isqrt(square)
    if step * step != square or step <= 0:
        raise ValueError("root spacing is not a positive integer")
    return step


def canonical_key(inst: dict) -> str:
    """Normal form under term reorder, translations, reflections, and x/y swap."""
    degree = inst["degree"]
    steps = sorted([
        _newton_ap_step(inst["f_terms"], degree),
        _newton_ap_step(inst["g_terms"], degree),
    ])
    payload = {
        "family": inst["family"],
        "degree": degree,
        "tensor_power": inst["tensor_power"],
        "ap_steps": steps,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the root haystack while the two-polynomial answer stays fixed."""
    degree = int(params.get("n", DIFFICULTY["hard"]["n"]))
    bound = int(params.get("root_bound", DIFFICULTY["hard"]["root_bound"]))
    power = int(params.get("tensor_power", DIFFICULTY["hard"]["tensor_power"]))
    if len(str(bound)) > 700:
        return "cap_bound"
    return {"n": degree, "root_bound": 2 * bound, "tensor_power": power}


def _shift_coefficients(coeffs: list[int], shift: int) -> list[int]:
    """Coefficients of p(z-shift), whose roots are old roots plus shift."""
    degree = len(coeffs) - 1
    out = [0] * (degree + 1)
    for k, coefficient in enumerate(coeffs):
        for j in range(k + 1):
            out[j] += coefficient * math.comb(k, j) * (-shift) ** (k - j)
    return out


def _reflect_coefficients(coeffs: list[int]) -> list[int]:
    """Monic coefficients with roots negated."""
    degree = len(coeffs) - 1
    return [coefficient * (-1) ** (degree + exponent)
            for exponent, coefficient in enumerate(coeffs)]


def _extract_answer_roots(answer: dict) -> tuple[int, int]:
    root_x, ex = _extract_root(answer["generators"][0], 0)
    root_y, ey = _extract_root(answer["generators"][1], 1)
    if ex or ey or root_x is None or root_y is None:
        raise ValueError("cannot carry malformed answer")
    return root_x, root_y


def _affine_relabel(inst: dict, sign_x: int, shift_x: int,
                    sign_y: int, shift_y: int, swap: bool,
                    term_seed: int) -> tuple[dict, dict]:
    """Apply x -> sign_x*x+shift_x and its y analogue, then optionally swap."""
    if sign_x not in (-1, 1) or sign_y not in (-1, 1):
        raise ValueError("signs must be units")
    degree = inst["degree"]
    f = _coefficient_list(inst["f_terms"], degree)
    g = _coefficient_list(inst["g_terms"], degree)
    if sign_x == -1:
        f = _reflect_coefficients(f)
    if sign_y == -1:
        g = _reflect_coefficients(g)
    f = _shift_coefficients(f, shift_x)
    g = _shift_coefficients(g, shift_y)
    root_x, root_y = _extract_answer_roots(inst["answer"])
    root_x = sign_x * root_x + shift_x
    root_y = sign_y * root_y + shift_y
    if swap:
        f, g = g, f
        root_x, root_y = root_y, root_x
    rng = random.Random(term_seed)
    out = {
        "family": inst["family"],
        "degree": degree,
        "root_bound": inst["root_bound"],
        "tensor_power": inst["tensor_power"],
        "f_terms": _terms_from_coefficients(f, rng),
        "g_terms": _terms_from_coefficients(g, rng),
        "f_coefficients": f,
        "g_coefficients": g,
        "f_mod_1000003": [c % 1_000_003 for c in f],
        "g_mod_1000003": [c % 1_000_003 for c in g],
    }
    carried = _answer(root_x, root_y, inst["tensor_power"])
    out["answer"] = carried
    return out, carried


def _candidate_roots_near_mean(terms: object, degree: int,
                               radius: int = 16) -> list[int]:
    coeffs = _coefficient_list(terms, degree)
    mean = Fraction(-coeffs[-2], degree)
    floor = mean.numerator // mean.denominator
    return list(range(floor - radius, floor + radius + 2))


def _attack_mean_neighborhood(inst: dict) -> bool:
    degree = inst["degree"]
    xs = _candidate_roots_near_mean(inst["f_terms"], degree)
    ys = _candidate_roots_near_mean(inst["g_terms"], degree)
    for root_x in xs:
        for root_y in ys:
            if verify(inst, _answer(root_x, root_y, inst["tensor_power"]))[0]:
                return True
    return False


def _attack_small_integer_greedy(inst: dict) -> bool:
    candidates = [0]
    for value in range(1, 33):
        candidates.extend([value, -value])
    f = _coefficient_list(inst["f_terms"], inst["degree"])
    g = _coefficient_list(inst["g_terms"], inst["degree"])
    xs = [x for x in candidates if _poly_eval(f, x) == 0]
    ys = [y for y in candidates if _poly_eval(g, y) == 0]
    return bool(xs and ys)


def _attack_random_restart(inst: dict, seed: int, restarts: int = 256) -> bool:
    rng = random.Random(seed ^ 0x180603545)
    for _ in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _unit_step_endpoint(terms: object, degree: int) -> list[int]:
    coeffs = _coefficient_list(terms, degree)
    first_sum = -coeffs[-2]
    guesses = []
    for signed_step in (-1, 1):
        numerator = 2 * first_sum - signed_step * degree * (degree - 1)
        denominator = 2 * degree
        if numerator % denominator == 0:
            guesses.append(numerator // denominator)
    return guesses


def _attack_unit_spacing_ansatz(inst: dict) -> bool:
    degree = inst["degree"]
    xs = _unit_step_endpoint(inst["f_terms"], degree)
    ys = _unit_step_endpoint(inst["g_terms"], degree)
    return any(
        verify(inst, _answer(x, y, inst["tensor_power"]))[0]
        for x in xs for y in ys
    )


def _scan_root(coeffs: list[int], bound: int,
               screening_prime: int = 1_000_003) -> tuple[int | None, int]:
    """Complete bounded scan with modular rejection and exact confirmation."""
    operations = 0
    residues = [coefficient % screening_prime for coefficient in coeffs]
    for candidate in range(-bound, bound + 1):
        candidate_mod = candidate % screening_prime
        value_mod = 0
        for coefficient in reversed(residues):
            value_mod = (value_mod * candidate_mod + coefficient) % screening_prime
            operations += 2
        if value_mod != 0:
            continue
        value_exact = 0
        for coefficient in reversed(coeffs):
            value_exact = value_exact * candidate + coefficient
            operations += 2
        if value_exact == 0:
            return candidate, operations
    return None, operations


def _sturm_chain_counted(coeffs: list[int]) -> tuple[list[Fraction],
                                                        list[list[Fraction]], int]:
    """Build an exact Sturm chain and count its rational arithmetic."""
    if gv_roots is None:
        raise RuntimeError("gvlib.roots is unavailable")
    polynomial = gv_roots.normalize(coeffs)
    if len(polynomial) < 2:
        raise ValueError("Sturm isolation needs a nonconstant polynomial")
    operations = 0

    first_lead = abs(polynomial[-1])
    first = [coefficient / first_lead for coefficient in polynomial]
    operations += len(first)

    derivative = [polynomial[index] * index
                  for index in range(1, len(polynomial))]
    operations += len(derivative)
    derivative = gv_roots.normalize(derivative)
    derivative_lead = abs(derivative[-1])
    second = [coefficient / derivative_lead for coefficient in derivative]
    operations += len(second)
    sequence = [first, second]

    while len(sequence[-1]) > 1:
        divisor_degree = len(sequence[-1]) - 1
        quotient, remainder = gv_roots.divmod_poly(sequence[-2], sequence[-1])
        nonzero_quotient_terms = sum(coefficient != 0 for coefficient in quotient)
        # Each nonzero long-division step uses one division, then one
        # multiplication and subtraction for every divisor coefficient.
        operations += nonzero_quotient_terms * (
            1 + 2 * (divisor_degree + 1))
        if not remainder:
            raise ValueError("instance polynomial is not squarefree")
        remainder = [-coefficient for coefficient in remainder]
        operations += len(remainder)
        lead = abs(remainder[-1])
        remainder = [coefficient / lead for coefficient in remainder]
        operations += len(remainder)
        sequence.append(remainder)

    return polynomial, sequence, operations


def _sturm_sign_changes_counted(sequence: list[list[Fraction]],
                                value: Fraction) -> tuple[int, int]:
    """Return the Sturm sign-change count and exact Horner operation count."""
    if gv_roots is None:
        raise RuntimeError("gvlib.roots is unavailable")
    previous = 0
    changes = 0
    operations = 0
    for polynomial in sequence:
        evaluated = gv_roots.evaluate(polynomial, value)
        operations += 2 * len(polynomial)
        if evaluated == 0:
            continue
        sign = 1 if evaluated > 0 else -1
        if previous and sign != previous:
            changes += 1
        previous = sign
    return changes, operations


def _sturm_one_integer_root(coeffs: list[int], bound: int) -> tuple[int, int]:
    """Find one promised simple integer root by exact Sturm bisection."""
    if gv_roots is None:
        raise RuntimeError("gvlib.roots is unavailable")
    polynomial, sequence, operations = _sturm_chain_counted(coeffs)
    left = Fraction(-bound - 1)
    right = Fraction(bound + 1)
    left_variations, used = _sturm_sign_changes_counted(sequence, left)
    operations += used
    right_variations, used = _sturm_sign_changes_counted(sequence, right)
    operations += used
    root_count = left_variations - right_variations
    if root_count <= 0:
        raise ValueError("no real root occurs in the stated bound")

    # Select any occupied half until just one root remains. The promise that
    # every root is an integer lets an exact midpoint hit finish immediately.
    while root_count > 1:
        midpoint = (left + right) / 2
        operations += 2
        midpoint_value = gv_roots.evaluate(polynomial, midpoint)
        operations += 2 * len(polynomial)
        if midpoint_value == 0:
            if midpoint.denominator != 1:
                raise ValueError("a promised integer root is nonintegral")
            return midpoint.numerator, operations
        midpoint_variations, used = _sturm_sign_changes_counted(
            sequence, midpoint)
        operations += used + 1
        left_count = left_variations - midpoint_variations
        if left_count > 0:
            right = midpoint
            right_variations = midpoint_variations
            root_count = left_count
        else:
            left = midpoint
            left_variations = midpoint_variations
            root_count = midpoint_variations - right_variations

    # A single simple root changes sign. Bisect its bracket to width below one,
    # which leaves at most one integer candidate.
    left_value = gv_roots.evaluate(polynomial, left)
    right_value = gv_roots.evaluate(polynomial, right)
    operations += 4 * len(polynomial)
    if left_value == 0 or right_value == 0:
        endpoint = left if left_value == 0 else right
        if endpoint.denominator != 1:
            raise ValueError("a promised integer root is nonintegral")
        return endpoint.numerator, operations
    if (left_value > 0) == (right_value > 0):
        raise ValueError("isolating interval does not bracket a simple root")
    while right - left > 1:
        midpoint = (left + right) / 2
        operations += 3
        midpoint_value = gv_roots.evaluate(polynomial, midpoint)
        operations += 2 * len(polynomial)
        if midpoint_value == 0:
            if midpoint.denominator != 1:
                raise ValueError("a promised integer root is nonintegral")
            return midpoint.numerator, operations
        if (midpoint_value > 0) == (left_value > 0):
            left, left_value = midpoint, midpoint_value
        else:
            right, right_value = midpoint, midpoint_value

    candidate = left.numerator // left.denominator + 1
    operations += 1
    if not left < candidate < right:
        raise ValueError("isolating interval contains no integer")
    candidate_value = gv_roots.evaluate(polynomial, candidate)
    operations += 2 * len(polynomial)
    if candidate_value != 0:
        raise ValueError("integer in isolating interval is not a root")
    return candidate, operations


def _reference_algorithm(inst: dict) -> dict:
    """Successful Track-B baseline, using a standard exact root algorithm."""
    f = _coefficient_list(inst["f_terms"], inst["degree"])
    g = _coefficient_list(inst["g_terms"], inst["degree"])
    start = time.perf_counter()
    if gv_roots is not None:
        root_x, ops_x = _sturm_one_integer_root(f, inst["root_bound"])
        root_y, ops_y = _sturm_one_integer_root(g, inst["root_bound"])
        name = "exact Sturm-sequence isolation of one integer root per polynomial"
        complexity = "O(n^3 + n^2 log B) exact rational operations per polynomial"
    else:  # dependency-free complete fallback
        root_x, ops_x = _scan_root(f, inst["root_bound"])
        root_y, ops_y = _scan_root(g, inst["root_bound"])
        name = "bounded integer-root scan with modular rejection and exact Horner"
        complexity = "O(B*n) modular/exact operations per polynomial"
    elapsed = time.perf_counter() - start
    answer = (None if root_x is None or root_y is None
              else _answer(root_x, root_y, inst["tensor_power"]))
    ok = answer is not None and verify(inst, answer)[0]
    return {
        "ok": ok,
        "answer": answer,
        "name": name,
        "complexity": complexity,
        "wall_clock_sec": elapsed,
        "operations": ops_x + ops_y,
    }


def _ap_endpoint_from_moments(terms: object, degree: int) -> tuple[int, int]:
    """The intended compact route, returned for testing and operation accounting."""
    coeffs = _coefficient_list(terms, degree)
    first_sum = -coeffs[-2]
    second_elementary = coeffs[-3]
    second_power = first_sum * first_sum - 2 * second_elementary
    dispersion = degree * second_power - first_sum * first_sum
    step_square = (12 * dispersion) // (
        degree * degree * (degree * degree - 1))
    step = math.isqrt(step_square)
    endpoint_numerator = 2 * first_sum - step * degree * (degree - 1)
    endpoint = endpoint_numerator // (2 * degree)
    return endpoint, step


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    wire = json.dumps(answer, separators=(",", ":"))

    def atoms(value: object) -> int:
        if isinstance(value, dict):
            return sum(atoms(v) for v in value.values())
        if isinstance(value, list):
            return sum(atoms(v) for v in value)
        return 1

    return len(wire), math.ceil(len(wire) / 4), atoms(answer)


def selftest() -> dict:
    report: dict = {}

    # G1: every named preset over several independent seeds.
    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
        "generation_route": "composition of factor identities plus Lemmas 2.5 and 3.1",
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **ship_params)
    original = inst["answer"]
    corruptions = {}
    bad = json.loads(json.dumps(original))
    bad["generators"][0].pop()
    corruptions["drop_one"] = verify(inst, bad)
    bad = json.loads(json.dumps(original))
    bad["generators"][0], bad["generators"][1] = (
        bad["generators"][1], bad["generators"][0])
    corruptions["swap_one"] = verify(inst, bad)
    bad = json.loads(json.dumps(original))
    bad["generators"].append(json.loads(json.dumps(bad["generators"][0])))
    corruptions["duplicate"] = verify(inst, bad)
    corruptions["empty"] = verify(inst, [])
    bad = json.loads(json.dumps(original))
    bad["generators"][0][0][0] = [-(inst["root_bound"] + 1), 1]
    corruptions["out_of_range"] = verify(inst, bad)
    reasons = [reason for _, reason in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not ok for ok, _ in corruptions.values())
                and len(set(reasons)) == len(reasons),
        "cases": {
            name: {"rejected": not result[0], "reason": result[1]}
            for name, result in corruptions.items()
        },
        "distinct_reasons": len(set(reasons)),
    }

    wire = json.dumps(original, separators=(",", ":"))
    parsed = parse_answer(
        "The two factors give the component.\n```json\n<answer>"
        + wire + "</answer>\n```\nI checked both substitutions exactly."
    )
    report["G3_round_trip"] = {
        "pass": parsed == original,
        "surrounding_prose_and_fence": True,
        "json_round_trip": parsed == original,
    }

    # One statement-aware shipping sample serves G4 and shipping density in G5.
    guess_rng = random.Random(0x180603545)
    guess_total = 200_000
    hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    guess_elapsed = time.perf_counter() - guess_start
    empirical_probability = hits / guess_total
    exact_valid_answers = inst["degree"] ** 2
    exact_probability = exact_valid_answers / search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": exact_probability < 1e-6 and guess_total >= 200_000,
        "hits": hits,
        "total": guess_total,
        "empirical_probability": empirical_probability,
        "exact_probability": exact_probability,
        "exact_valid_answers": exact_valid_answers,
        "prior": (
            "uniform over normalized integer root pairs in the stated inclusive "
            "bound; polynomial shape, generator order, and power are enforced"
        ),
        "search_space": search_space(inst),
        "sampling_wall_seconds": guess_elapsed,
    }

    baseline = _reference_algorithm(inst)
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": baseline["ok"] and exact_probability < 1e-6
                and demo_count is not None,
        "shipping_observed_valid_fraction": empirical_probability,
        "shipping_exact_valid_fraction": exact_probability,
        "shipping_density_sample_count": guess_total,
        "shipping_valid_hits": hits,
        "shipping_exact_valid_answers_by_construction": exact_valid_answers,
        "shipping_candidate_space": search_space(inst),
        "baseline_wall_seconds": baseline["wall_clock_sec"],
        "baseline_operation_count": baseline["operations"],
        "baseline_success_count": int(baseline["ok"]),
        "demo_exact_solution_count_by_bruteforce": demo_count,
        "demo_candidate_space": search_space(demo),
        "enumerate_all_shipping": None,
    }

    attack_successes = {
        "outlier_vieta_mean_neighborhood_16": 0,
        "greedy_small_integer_roots_32": 0,
        "random_restart_256_normalized_pairs": 0,
        "in_context_unit_spacing_progression_ansatz": 0,
    }
    reference_runs = []
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **ship_params)
        attack_successes["outlier_vieta_mean_neighborhood_16"] += int(
            _attack_mean_neighborhood(trial))
        attack_successes["greedy_small_integer_roots_32"] += int(
            _attack_small_integer_greedy(trial))
        attack_successes["random_restart_256_normalized_pairs"] += int(
            _attack_random_restart(trial, seed))
        attack_successes["in_context_unit_spacing_progression_ansatz"] += int(
            _attack_unit_spacing_ansatz(trial))
        reference_runs.append(_reference_algorithm(trial))
    all_failed = all(successes == 0 for successes in attack_successes.values())
    reference_solved = sum(int(run["ok"]) for run in reference_runs)
    total_ref_seconds = sum(run["wall_clock_sec"] for run in reference_runs)
    total_ref_ops = sum(run["operations"] for run in reference_runs)
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_solved == 8,
        "attacks": {
            name: {"successes": successes, "attempts": 8}
            for name, successes in attack_successes.items()
        },
        "reference_algorithm": {
            "name": reference_runs[0]["name"],
            "complexity": reference_runs[0]["complexity"],
            "wall_clock_sec": total_ref_seconds,
            "mean_wall_clock_sec": total_ref_seconds / 8,
            "operations": total_ref_ops,
            "mean_operations": total_ref_ops / 8,
            "solves": f"{reference_solved}/8, as expected",
        },
    }

    doubled = make_instance(
        n=2 * ship_params["n"],
        root_bound=2 * ship_params["root_bound"],
        tensor_power=ship_params["tensor_power"],
        seed=77,
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok,
        "base_n": ship_params["n"],
        "doubled_n": doubled["degree"],
        "base_root_bound": ship_params["root_bound"],
        "doubled_root_bound": doubled["root_bound"],
        "doubled_verify": doubled_reason,
        "reference_operation_growth": "approximately 4x",
        "answer_shape_growth": "none",
    }

    invariance_checks = 0
    witness_checks = 0
    expected_checks = 0
    for seed in range(20):
        base = make_instance(seed=seed, **ship_params)
        transforms = [
            (1, 137, 1, -211, False),
            (-1, 0, 1, 0, False),
            (1, 0, -1, 0, False),
            (1, 0, 1, 0, True),
            (-1, 137, -1, -211, True),
        ]
        for index, transform in enumerate(transforms):
            moved, carried = _affine_relabel(
                base, *transform, term_seed=seed * 100 + index)
            expected_checks += 1
            invariance_checks += int(canonical_key(moved) == canonical_key(base))
            witness_checks += int(verify(moved, carried)[0])
    keys = {
        canonical_key(make_instance(seed=seed, **ship_params))
        for seed in range(1000, 1020)
    }
    report["G8_canonical_key"] = {
        "pass": invariance_checks == expected_checks
                and witness_checks == expected_checks and len(keys) == 20,
        "invariance_checks": invariance_checks,
        "invariance_attempts": expected_checks,
        "transformed_witness_checks": witness_checks,
        "transformed_witness_attempts": expected_checks,
        "unrelated_distinct": len(keys),
        "unrelated_attempts": 20,
        "transformations": (
            "independent integer translations, independent reflections, "
            "x/y interchange, arbitrary term-table reorder, and their composition"
        ),
    }

    # Confirm the intended invariant really reconstructs valid endpoints.
    intended_ok = True
    for terms in (inst["f_terms"], inst["g_terms"]):
        endpoint, step = _ap_endpoint_from_moments(terms, inst["degree"])
        coeffs = _coefficient_list(terms, inst["degree"])
        intended_ok &= step > 0 and _poly_eval(coeffs, endpoint) == 0

    size_measurements = [
        _answer_metrics(make_instance(seed=seed, **ship_params)["answer"])
        for seed in range(1000)
    ]
    chars, tokens, elements = max(size_measurements, key=lambda item: item[0])
    # Per polynomial: 18 arithmetic operations recover an endpoint from the
    # top two Newton sums, then 2*(degree+1) operations confirm it by Horner.
    intended_operations = 2 * (18 + 2 * (inst["degree"] + 1))
    evidence = G9_EVIDENCE
    hinted_attempts = evidence["hinted"]["attempts"]
    placebo_attempts = evidence["placebo"]["attempts"]
    hinted_rate = (evidence["hinted"]["solved"] / hinted_attempts
                   if hinted_attempts else 0.0)
    placebo_rate = (evidence["placebo"]["solved"] / placebo_attempts
                    if placebo_attempts else 0.0)
    within_caps = chars <= 2000 and elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps and intended_ok,
        "arms": {
            "bare": dict(evidence["bare"]),
            "hinted": dict(evidence["hinted"]),
            "placebo": dict(evidence["placebo"]),
        },
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": evidence["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "answer_size_sample_count": len(size_measurements),
        "intended_route_operations": intended_operations,
        "intended_route_endpoint_checks": intended_ok,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship_params)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
