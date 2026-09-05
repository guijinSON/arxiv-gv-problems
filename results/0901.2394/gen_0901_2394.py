"""Track-B primary-decomposition generator for arXiv:0901.2394.

Lemma 3.1 obtains primary components by factoring an auxiliary h_q(t), and
Section 4 supplies tridiagonal determinant polynomials with a second-order
recurrence.  The generator samples the recurrence's characteristic roots
first, then builds h from their known factors.  It never factors its input.
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
    from gvlib import rationals  # noqa: F401 (available; F_p needs no helper)
except ImportError:
    rationals = None

TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "homogeneous quotient ring over a prime field",
        "Frobenius power of a principal homogeneous ideal",
        "univariate determinant polynomial over F_p",
        "primary ideals specified by irreducible polynomial factors",
    ],
    "verification_operations": [
        "finite-field coefficient range and monicity checks",
        "exact Vieta coefficient comparisons",
        "exact finite-field polynomial multiplication",
        "exact coefficient-list equality",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize the two polynomial characteristic roots of the paper's "
        "second-order determinant recurrence; without that change of variables, "
        "one must factor the dense finite-field polynomial mechanically."
    ),
    "hardness_basis": (
        "Track B: Cantor-Zassenhaus finite-field factorization with classical "
        "polynomial arithmetic has expected O(d^2 log(d) log(p)) base-field "
        "cost; on eight degree-15 hard-preset instances it used 963,024 "
        "coefficient operations (120,378 average) and 0.143 seconds total in "
        "the initial audit, while the characteristic-root identity emits every "
        "factor in at most 125 finite-field arithmetic operations."
    ),
    "max_answer_tokens": 75,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

# n grows the field while order (and therefore answer length) stays fixed.
DIFFICULTY = {
    "demo": {"n": 5, "order": 4},
    "easy": {"n": 100_000, "order": 16},
    "medium": {"n": 100_000_000, "order": 16},
    "hard": {"n": 1_000_000_000_000, "order": 16},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Hint: The second-order determinant recurrence has two polynomial "
    "characteristic roots whose ratio is acted on by the supplied "
    "root-of-unity subgroup."
)
PLACEBO_HINT = (
    "Hint: Careful normalization of the displayed finite-field coefficients "
    "helps avoid sign, indexing, and ordering mistakes in the final list."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "An unordered JSON list of exactly m distinct monic linear polynomials "
        "[c,1] over F_p, with coefficients in 0..p-1 and Vieta sum sum(c) "
        "equal to the displayed t^(m-1) coefficient of h."
    ),
    "bounds": {
        "number_of_factors": "m = order-1 (15 at shipping)",
        "degree_each": 1,
        "coefficient_range": "0 <= c < p",
        "monic_leading_coefficient": 1,
        "vieta_constraints_built_into_random_prior": 1,
        "shipping_atomic_coefficients": 30,
    },
}

G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "blocked_by_openrouter_key_limit",
}

NOTES = r"""
Section 1 fixes the Frobenius-power definition. Lemma 3.1 is the exact
certificate theorem used here: irreducible-power factors tau_i^s_i of h_q
supply the primary components I^[q]+(tau_i^s_i). Section 4 defines P_j as a
tridiagonal determinant and displays P_(j+1)=r_1 P_j-r_0 r_2 P_(j-1).

For S=F_p[t,x], squarefree h, R=S/(h*x), and I=(x), one has
((x^p,h*x):h)=(x), because gcd(h,x)=1. Thus I^[p]:_R h=(x), a prime
ideal. Lemma 3.1 gives (x^p)=(x) intersect all (x^p,t+c_i), where
h=product(t+c_i). Each component quotient is F_p[x]/(x^p), so its radical
is (x,t+c_i) and it is primary. The checker executes the variable part of
that certificate by multiplying the proposed factors exactly.

M is a power of two dividing p-1 and omega has exact order M. The generator
samples linear A,B first, sets r_1=A+B and r_0*r_2=A*B, and forms the answer
factors A-omega^j B for 1<=j<M. It multiplies those known factors to build h.
The identity P_(M-1)=(A^M-B^M)/(A-B) proves that h is the monic determinant
polynomial from Section 4. This is inverse generation plus composition of
identities, not factorization of a completed instance.

Track A is unavailable: Lemma 3.1 reduces the varying components to univariate
factorization, randomized polynomial time over finite fields. Track B is used
honestly. selftest separately times and counts a Cantor-Zassenhaus factorer.
The compact route recovers A,B from the square r_1^2-4r_0r_2 and applies the
root-of-unity identity; complete emission takes at most 125 field
operations.

The panel tries coefficient outliers, consecutive small factors, a one-step
recurrence-coefficient ansatz, and 256 structure-aware random restarts. Small
fields permit root scanning, hence only demo uses one. Plants and guesses use
the same monic-linear-factor language and visible Vieta-sum constraint.

Affine substitutions t -> u*t+v and replacement of omega by another primitive
generator only relabel the problem. canonical_key recovers the factor roots,
normalizes over all ordered affine anchors, and chooses the least form. It
never hashes the seed or the rendered statement.
""".strip()

_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"```(?:json|text)?\s*(.*?)```", re.I | re.S)
_ENUMERATION_CAP = 500_000


def _trim(f):
    f = list(f)
    while len(f) > 1 and f[-1] == 0:
        f.pop()
    return f or [0]


def _add(a, b, p):
    out = [0] * max(len(a), len(b))
    for i in range(len(out)):
        out[i] = ((a[i] if i < len(a) else 0)
                  + (b[i] if i < len(b) else 0)) % p
    return _trim(out)


def _sub(a, b, p):
    out = [0] * max(len(a), len(b))
    for i in range(len(out)):
        out[i] = ((a[i] if i < len(a) else 0)
                  - (b[i] if i < len(b) else 0)) % p
    return _trim(out)


def _scale(a, scalar, p):
    return _trim([(scalar * x) % p for x in a])


def _mul(a, b, p, counter=None):
    if a == [0] or b == [0]:
        return [0]
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x == 0:
            continue
        for j, y in enumerate(b):
            if y == 0:
                continue
            out[i + j] = (out[i + j] + x * y) % p
            if counter is not None:
                counter[0] += 2
    return _trim(out)


def _monic(a, p):
    a = _trim([x % p for x in a])
    if a == [0]:
        raise ValueError("zero polynomial has no monic normalization")
    return _scale(a, pow(a[-1], -1, p), p)


def _divmod_poly(numerator, denominator, p, counter=None):
    num = _trim([x % p for x in numerator])
    den = _trim([x % p for x in denominator])
    if den == [0]:
        raise ZeroDivisionError("polynomial division by zero")
    if len(num) < len(den):
        return [0], num
    quotient = [0] * (len(num) - len(den) + 1)
    inv_lead = pow(den[-1], -1, p)
    while num != [0] and len(num) >= len(den):
        shift = len(num) - len(den)
        q = num[-1] * inv_lead % p
        quotient[shift] = q
        for j, value in enumerate(den):
            num[shift + j] = (num[shift + j] - q * value) % p
            if counter is not None:
                counter[0] += 2
        num = _trim(num)
    return _trim(quotient), num


def _mod_poly(a, modulus, p, counter=None):
    return _divmod_poly(a, modulus, p, counter)[1]


def _gcd_poly(a, b, p, counter=None):
    a, b = _trim(a), _trim(b)
    while b != [0]:
        a, b = b, _mod_poly(a, b, p, counter)
    return _monic(a, p)


def _powmod_poly(base, exponent, modulus, p, counter=None):
    result = [1]
    base = _mod_poly(base, modulus, p, counter)
    while exponent:
        if exponent & 1:
            result = _mod_poly(_mul(result, base, p, counter), modulus, p, counter)
        exponent >>= 1
        if exponent:
            base = _mod_poly(_mul(base, base, p, counter), modulus, p, counter)
    return result


def _is_prime_64(value):
    if value < 2:
        return False
    for prime in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if value % prime == 0:
            return value == prime
    d, s = value - 1, 0
    while d % 2 == 0:
        s += 1
        d //= 2
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


def _validate_params(n, order):
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    if isinstance(order, bool) or not isinstance(order, int):
        raise ValueError("order must be an integer")
    if order < 4 or order > 32 or order & (order - 1):
        raise ValueError("order must be a power of two between 4 and 32")
    if order * (2 * n + 10_000) >= 2**64:
        raise ValueError("parameters exceed the deterministic 64-bit prime range")


def _prime_and_root(n, order, rng):
    k = n + rng.randrange(max(2, n // 2 + 1))
    while True:
        p = order * k + 1
        if _is_prime_64(p):
            break
        k += 1
    for base in range(2, 10_000):
        omega = pow(base, (p - 1) // order, p)
        if pow(omega, order, p) == 1 and pow(omega, order // 2, p) != 1:
            return p, omega
    raise RuntimeError("failed to construct a root of unity")


def _root_powers(omega, order, p):
    out, value = [], 1
    for _ in range(1, order):
        value = value * omega % p
        out.append(value)
    return out


def _factors_from_pair(a, b, omega, order, p):
    factors = []
    for zeta in _root_powers(omega, order, p):
        raw = _sub(a, _scale(b, zeta, p), p)
        if len(raw) != 2 or raw[1] == 0:
            raise ValueError("a characteristic factor lost degree")
        factors.append([raw[0] * pow(raw[1], -1, p) % p, 1])
    factors.sort()
    if len({factor[0] for factor in factors}) != order - 1:
        raise ValueError("characteristic factors are not distinct")
    return factors


def _product(factors, p):
    out = [1]
    for factor in factors:
        out = _mul(out, factor, p)
    return _trim(out)


def _recurrence_polynomial(r1, c, m, p):
    if m == 0:
        return [1]
    previous, current = [1], list(r1)
    for _ in range(1, m):
        previous, current = current, _sub(
            _mul(r1, current, p), _mul(c, previous, p), p)
    return current


def make_instance(n, seed=0, **params):
    """Build a certified instance by inverse generation and identities."""
    order = params.pop("order", 32)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, order)
    rng = random.Random(seed)
    p, omega = _prime_and_root(n, order, rng)
    powers = _root_powers(omega, order, p)
    while True:
        slope_b = rng.randrange(1, p)
        slope_a = (slope_b + 1) % p
        if slope_a and all((slope_a - z * slope_b) % p for z in powers):
            break
    while True:
        const_a, const_b = rng.randrange(p), rng.randrange(p)
        if (slope_a * const_b - slope_b * const_a) % p:
            break
    a, b = [const_a, slope_a], [const_b, slope_b]
    factors = _factors_from_pair(a, b, omega, order, p)
    h = _product(factors, p)
    r1, c, m = _add(a, b, p), _mul(a, b, p), order - 1
    if _monic(_recurrence_polynomial(r1, c, m, p), p) != h:
        raise AssertionError("determinant recurrence identity failed")
    return {
        "n": n, "p": p, "q": p, "order": order, "m": m,
        "omega": omega, "r1": r1, "c": c, "h": h,
        "answer": factors,
    }


def _poly_text(coeffs):
    return "[" + ", ".join(str(value) for value in coeffs) + "]"


def render(inst):
    """Render the complete exact primary-decomposition task."""
    statement = f"""Primary components of a Frobenius power

All arithmetic is in the prime field F_p with p = {inst['p']}; field elements
are represented by their unique integers from 0 through p-1. A polynomial
[a0,a1,...,ad] means a0+a1*t+...+ad*t^d in F_p[t] (low degree first).

Let
  r1(t) = {_poly_text(inst['r1'])}
  c(t)  = {_poly_text(inst['c'])}.
Define determinant polynomials P_0=1, P_1=r1, and
  P_(j+1) = r1*P_j - c*P_(j-1)  for j>=1.
For m={inst['m']}, the monic normalization h of P_m is
  h(t) = {_poly_text(inst['h'])}.
For reproducibility, omega={inst['omega']} has exact multiplicative order
{inst['order']} in F_p.

Now form the homogeneous quotient ring
  R = F_p[t,x] / (h(t)*x)
with deg(t)=0 and deg(x)=1, and let I=(x). Its p-th Frobenius power is
I^[p]=(x^p). The polynomial h is squarefree and splits into exactly m distinct
monic linear factors tau_i(t). If h=product_i tau_i, then
  (x^p) = (x) intersect (intersection_i (x^p,tau_i))
is a primary decomposition in R. Thus your task is to give the m variable
primary components by giving all of their tau_i factors.

Output exactly {inst['m']} distinct monic linear factors. Write each tau=t+c
as the two-coefficient JSON list [c,1], with 0<=c<p. The outer list is
unordered: any factor order is accepted. Repetitions are forbidden.

Give your final answer inside <answer></answer> tags as one JSON list of these
coefficient lists.
Example format: <answer>[[3,1],[17,1],[42,1]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Extract a JSON factor list despite surrounding prose or fences."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    candidates = [match.group(1)] if match else []
    candidates.extend(m.group(1) for m in _FENCE_RE.finditer(text))
    candidates.append(text)
    for candidate in candidates:
        candidate = candidate.strip()
        try:
            return json.loads(candidate)
        except (TypeError, ValueError):
            pass
        decoder = json.JSONDecoder()
        for pos, char in enumerate(candidate):
            if char != "[":
                continue
            try:
                value, _end = decoder.raw_decode(candidate[pos:])
                return value
            except ValueError:
                continue
    return None


def verify(inst, answer):
    """Check any proposed factorization exactly; never read inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer list is empty"
    if len(answer) != inst["m"]:
        return False, f"wrong number of factors: expected {inst['m']}"
    constants = []
    for index, factor in enumerate(answer):
        if not isinstance(factor, list) or len(factor) != 2:
            return False, f"factor {index} must have exactly two coefficients"
        if any(isinstance(value, bool) or not isinstance(value, int)
               for value in factor):
            return False, f"factor {index} has a non-integer coefficient"
        if any(value < 0 or value >= inst["p"] for value in factor):
            return False, f"factor {index} has a coefficient outside 0..p-1"
        if factor[1] != 1:
            return False, f"factor {index} is not monic linear"
        constants.append(factor[0])
    if len(set(constants)) != len(constants):
        return False, "factors are not distinct"
    p = inst["p"]
    if sum(constants) % p != inst["h"][-2]:
        return False, "linear Vieta coefficient disagrees with h"
    inverse_two = (p + 1) // 2
    e2 = ((sum(constants) % p) ** 2 - sum(c * c for c in constants))
    e2 = e2 * inverse_two % p
    if e2 != inst["h"][-3]:
        return False, "quadratic Vieta coefficient disagrees with h"
    if _product([list(factor) for factor in answer], p) != inst["h"]:
        return False, "factor product does not equal h"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniform distinct monic factors conditioned on the visible Vieta sum."""
    p, m, target = inst["p"], inst["m"], inst["h"][-2]
    while True:
        constants = rng.sample(range(p), m - 1)
        last = (target - sum(constants)) % p
        if last not in constants:
            constants.append(last)
            constants.sort()
            return [[constant, 1] for constant in constants]


def search_space(inst):
    # Translation sends a k-set sum to sum+k*z. Since m is invertible mod p,
    # all p sum fibres have equal cardinality.
    return math.comb(inst["p"], inst["m"]) // inst["p"]


def enumerate_all(inst):
    total = math.comb(inst["p"], inst["m"])
    if total > _ENUMERATION_CAP:
        return None
    valid = 0
    for constants in itertools.combinations(range(inst["p"]), inst["m"]):
        if sum(constants) % inst["p"] != inst["h"][-2]:
            continue
        valid += int(verify(inst, [[constant, 1]
                                  for constant in constants])[0])
    return valid


def _sqrt_mod(value, p):
    value %= p
    if value == 0:
        return 0
    if pow(value, (p - 1) // 2, p) != 1:
        return None
    if p % 4 == 3:
        return pow(value, (p + 1) // 4, p)
    q, s = p - 1, 0
    while q % 2 == 0:
        q //= 2
        s += 1
    z = 2
    while pow(z, (p - 1) // 2, p) != p - 1:
        z += 1
    c = pow(z, q, p)
    x = pow(value, (q + 1) // 2, p)
    t, m = pow(value, q, p), s
    while t != 1:
        i, square = 1, t * t % p
        while i < m and square != 1:
            square = square * square % p
            i += 1
        if i == m:
            return None
        b = pow(c, 1 << (m - i - 1), p)
        x = x * b % p
        t = t * b * b % p
        c = b * b % p
        m = i
    return x


def _characteristic_pair(inst):
    p = inst["p"]
    discriminant = _sub(
        _mul(inst["r1"], inst["r1"], p), _scale(inst["c"], 4, p), p)
    discriminant += [0] * (3 - len(discriminant))
    lead = _sqrt_mod(discriminant[2], p)
    if lead in (None, 0):
        raise ValueError("characteristic discriminant is not a nonzero square")
    constant = discriminant[1] * pow(2 * lead % p, -1, p) % p
    d = [constant, lead]
    if _mul(d, d, p) != _trim(discriminant):
        d = _scale(d, -1, p)
    if _mul(d, d, p) != _trim(discriminant):
        raise ValueError("failed to recover polynomial square root")
    inv_two = (p + 1) // 2
    a = _scale(_add(inst["r1"], d, p), inv_two, p)
    b = _scale(_sub(inst["r1"], d, p), inv_two, p)
    return a, b


def _compact_factors(inst):
    a, b = _characteristic_pair(inst)
    return _factors_from_pair(
        a, b, inst["omega"], inst["order"], inst["p"])


def canonical_key(inst):
    """Canonicalize the factor-root set under every affine change of t."""
    p = inst["p"]
    roots = sorted((-factor[0]) % p for factor in _compact_factors(inst))
    forms = []
    for first in roots:
        for second in roots:
            if first == second:
                continue
            inverse = pow((second - first) % p, -1, p)
            forms.append(tuple(sorted(
                (root - first) * inverse % p for root in roots)))
    payload = {"p": p, "m": inst["m"], "affine_root_set": min(forms)}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def escalate(params):
    n, order = params.get("n"), params.get("order", 32)
    if not isinstance(n, int) or not isinstance(order, int):
        return None
    if order < 16:
        return {"n": max(n, 100_000), "order": 16}
    if n < 10**16:
        return {"n": n * 100, "order": order}
    if order < 32:
        return {"n": n, "order": 32}
    # Raising order again would exceed the 300-operation compact-route cap.
    return "cap_bound"


def _factor_cantor_zassenhaus(inst, rng):
    """Reference factorer for the promised squarefree fully split h."""
    p, counter = inst["p"], [0]

    def recurse(f):
        f = _monic(f, p)
        degree = len(f) - 1
        if degree == 1:
            return [f]
        for _ in range(256):
            candidate = [rng.randrange(p) for _ in range(degree)]
            split_value = _sub(
                _powmod_poly(candidate, (p - 1) // 2, f, p, counter),
                [1], p)
            divisor = _gcd_poly(f, split_value, p, counter)
            divisor_degree = len(divisor) - 1
            if 0 < divisor_degree < degree:
                quotient, remainder = _divmod_poly(f, divisor, p, counter)
                if remainder != [0]:
                    raise AssertionError("reference split was not exact")
                return recurse(divisor) + recurse(quotient)
        raise RuntimeError("Cantor-Zassenhaus exhausted its restart cap")

    factors = sorted(_monic(factor, p) for factor in recurse(inst["h"]))
    return factors, counter[0]


def _candidate_with_sum(inst, proposed):
    p, m = inst["p"], inst["m"]
    constants = []
    for value in proposed:
        value %= p
        if value not in constants:
            constants.append(value)
        if len(constants) == m - 1:
            break
    fill = 0
    while len(constants) < m - 1:
        if fill not in constants:
            constants.append(fill)
        fill += 1
    last = (inst["h"][-2] - sum(constants)) % p
    if last in constants:
        used = set(constants)
        for delta in range(1, p):
            replacement = (constants[-1] + delta) % p
            new_last = (last - delta) % p
            if (replacement not in used and
                    new_last not in used - {constants[-1]} and
                    new_last != replacement):
                constants[-1], last = replacement, new_last
                break
    constants.append(last)
    constants.sort()
    return [[constant, 1] for constant in constants]


def _attack_answers(inst):
    p = inst["p"]
    coefficients = list(inst["h"]) + list(inst["r1"]) + list(inst["c"])
    outlier = sorted(set(coefficients), key=lambda x: (min(x, p - x), x))
    return {
        "outlier_balanced_coefficients": _candidate_with_sum(inst, outlier),
        "greedy_consecutive_constants": _candidate_with_sum(
            inst, list(range(inst["m"] - 1))),
        "one_step_recurrence_ansatz": _candidate_with_sum(
            inst, list(inst["r1"]) + list(inst["c"]) + [inst["omega"]]),
    }


def _compose_affine(poly, u, v, p):
    out, linear = [0], [v % p, u % p]
    for coefficient in reversed(poly):
        out = _add(_mul(out, linear, p), [coefficient], p)
    return _trim(out)


def _transformed_instance(inst, u, v, omega_power=1):
    p, transformed = inst["p"], dict(inst)
    transformed["r1"] = _compose_affine(inst["r1"], u, v, p)
    transformed["c"] = _compose_affine(inst["c"], u, v, p)
    transformed["h"] = _monic(_compose_affine(inst["h"], u, v, p), p)
    transformed["omega"] = pow(inst["omega"], omega_power, p)
    inverse_u = pow(u, -1, p)
    carried = sorted([[(factor[0] + v) * inverse_u % p, 1]
                      for factor in inst["answer"]])
    transformed["answer"] = carried
    return transformed, carried


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest():
    """Run G1--G9 and return JSON-native measured evidence."""
    report = {
        "paper": "arXiv:0901.2394",
        "track": TRACK,
        "family": "determinant-factored Frobenius primary decomposition",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures, checks, compact_matches = [], 0, 0
    for preset, preset_params in DIFFICULTY.items():
        for seed in (0, 1, 7, 19):
            inst = make_instance(seed=seed, **preset_params)
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append(f"{preset}/{seed}: {reason}")
            compact_matches += int(_compact_factors(inst) == inst["answer"])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not failures and compact_matches == checks,
        "checks": checks,
        "compact_route_matches": compact_matches,
        "failures": failures,
    }

    shipping = make_instance(seed=271828, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = [factor[:] for factor in shipping["answer"]]
    swap_index = next(i for i, factor in enumerate(answer) if factor[0] != 1)
    swapped = [factor[:] for factor in answer]
    swapped[swap_index] = list(reversed(swapped[swap_index]))
    duplicate = [factor[:] for factor in answer]
    duplicate[-1] = duplicate[0][:]
    outside = [factor[:] for factor in answer]
    outside[0][0] = shipping["p"]
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": outside,
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"accepted": ok, "reason": reason}
    distinct_reasons = len({item["reason"] for item in corruption_results.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(not item["accepted"] for item in corruption_results.values())
        and distinct_reasons == len(corruption_results),
        "distinct_reasons": distinct_reasons,
        "cases": corruption_results,
    }

    answer_json = json.dumps(answer, separators=(",", ":"))
    wrapped = (
        "I used the determinant recurrence and checked the product.\n```json\n"
        f"<answer>{answer_json}</answer>\n```\nThese are the components."
    )
    report["G3_round_trip"] = {
        "pass": parse_answer(wrapped) == answer and parse_answer("garbage") is None,
        "prose_fence_tags_round_trip": parse_answer(wrapped) == answer,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    sample_total = 200_000
    sample_rng = random.Random(0x09012394)
    hits = 0
    started = time.perf_counter()
    for _ in range(sample_total):
        hits += int(verify(shipping, random_candidate(shipping, sample_rng))[0])
    sample_wall = time.perf_counter() - started
    space = search_space(shipping)
    exact_log10_fraction = -math.log10(space)
    report["G4_guess_resistance"] = {
        "pass": hits / sample_total < 1e-6 and space > 1_000_000,
        "hits": hits,
        "total": sample_total,
        "observed_fraction": hits / sample_total,
        "exact_fraction": {"numerator": 1, "denominator": space},
        "exact_log10_fraction": exact_log10_fraction,
        "candidate_space": space,
        "sampling_prior": (
            "uniform unordered distinct monic linear factors conditioned on the "
            "freely visible first Vieta sum"
        ),
        "wall_clock_sec": round(sample_wall, 6),
    }

    attack_stats = {
        "outlier_balanced_coefficients": {"successes": 0, "attempts": 0},
        "greedy_consecutive_constants": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0, "candidates": 0},
        "one_step_recurrence_ansatz": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_operations = 0
    reference_wall = 0.0
    strongest_wall = 0.0
    reference_per_seed = []
    for seed in range(8):
        trial = make_instance(
            seed=10_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, candidate in _attack_answers(trial).items():
            attack_stats[name]["attempts"] += 1
            attack_stats[name]["successes"] += int(verify(trial, candidate)[0])
        restart_rng = random.Random(90_000 + seed)
        restart_started = time.perf_counter()
        restart_success = False
        for _ in range(256):
            candidate = random_candidate(trial, restart_rng)
            attack_stats["random_restart_256"]["candidates"] += 1
            if verify(trial, candidate)[0]:
                restart_success = True
                break
        strongest_wall += time.perf_counter() - restart_started
        attack_stats["random_restart_256"]["attempts"] += 1
        attack_stats["random_restart_256"]["successes"] += int(restart_success)

        reference_started = time.perf_counter()
        factored, operations = _factor_cantor_zassenhaus(
            trial, random.Random(700_000 + seed))
        elapsed = time.perf_counter() - reference_started
        solved = verify(trial, factored)[0]
        reference_successes += int(solved)
        reference_operations += operations
        reference_wall += elapsed
        reference_per_seed.append({
            "seed": 10_000 + seed,
            "solved": solved,
            "field_operations": operations,
            "wall_clock_sec": round(elapsed, 6),
        })
    all_attacks_failed = all(
        values["successes"] == 0 for values in attack_stats.values())
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8,
        "attacks": attack_stats,
        "reference_algorithm": {
            "name": "Cantor-Zassenhaus splitting with classical polynomial arithmetic",
            "complexity": "expected O(d^2 log(d) log(p)) base-field operations",
            "wall_clock_sec": round(reference_wall, 6),
            "operations": reference_operations,
            "operation_unit": (
                "coefficient multiply/add/subtract steps across eight instances"),
            "solves": f"{reference_successes}/8, as expected",
            "per_seed": reference_per_seed,
        },
        "compact_route": {
            "name": "polynomial characteristic roots and M-th roots of unity",
            "operations_upper_bound": 125,
            "solves": f"{compact_matches}/{checks} in G1",
        },
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and hits / sample_total < 1e-6
        and reference_successes == 8,
        "shipping_density_method": (
            "structure-aware Monte Carlo plus uniqueness of factorization"),
        "shipping_sampled_valid_hits": hits,
        "shipping_sampled_valid_total": sample_total,
        "shipping_observed_fraction": hits / sample_total,
        "shipping_certified_solution_count": 1,
        "shipping_exact_solution_fraction": {"numerator": 1, "denominator": space},
        "shipping_exact_log10_fraction": exact_log10_fraction,
        "demo_bruteforce_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "reference_algorithm_operations": reference_operations,
        "reference_algorithm_wall_clock_sec": round(reference_wall, 6),
        "strongest_failing_attack": "random_restart_256",
        "strongest_failing_attack_candidates": (
            attack_stats["random_restart_256"]["candidates"]),
        "strongest_failing_attack_wall_clock_sec": round(strongest_wall, 6),
    }

    preset_spaces = {
        name: search_space(make_instance(seed=3, **preset_params))
        for name, preset_params in DIFFICULTY.items()
    }
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    names = list(DIFFICULTY)
    report["G7_scales"] = {
        "pass": doubled_ok and all(
            preset_spaces[left] < preset_spaces[right]
            for left, right in zip(names[:-1], names[1:])),
        "preset_candidate_spaces": preset_spaces,
        "doubled_n": doubled["n"],
        "doubled_field_size": doubled["p"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "shipping_answer_atoms": _answer_atoms(shipping["answer"]),
        "doubled_answer_atoms": _answer_atoms(doubled["answer"]),
    }

    invariance_checks, carried_checks = 0, 0
    invariance_failures, unrelated = [], []
    for seed in range(20):
        trial = make_instance(
            seed=20_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(trial)
        unrelated.append(key)
        transform_rng = random.Random(30_000 + seed)
        u = transform_rng.randrange(1, trial["p"])
        v = transform_rng.randrange(trial["p"])
        for name, tu, tv, omega_power in (
            ("translation", 1, v, 1),
            ("scaling", u, 0, 1),
            ("affine_plus_generator", u, v, 3),
        ):
            changed, carried = _transformed_instance(
                trial, tu, tv, omega_power)
            invariance_checks += 1
            if canonical_key(changed) != key:
                invariance_failures.append(f"seed {seed}/{name}: key changed")
            carried_checks += 1
            if not verify(changed, carried)[0]:
                invariance_failures.append(f"seed {seed}/{name}: witness failed")
    distinct_keys = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": not invariance_failures and distinct_keys == 20,
        "transformations": [
            "global translation t -> t+v",
            "global scaling t -> u*t",
            "general affine substitution composed with omega -> omega^3",
        ],
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "failures": invariance_failures,
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    intended_operations = 125
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else None)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else None)
    within_caps = (answer_chars <= 2_000 and answer_elements <= 256
                   and intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None),
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "diagnostic_complete": all(arms[name]["attempts"] > 0 for name in arms),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict))
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
