"""Verified generator for Gaussian-period permutation-polynomial coefficients.

The source is Theorem 1 and Proposition 3(3) of arXiv:1310.0337.  For an
odd m with 5 not dividing m, the paper proves that every noncube u on the
unit circle of GF(2^(2m)) makes x^d + u*x a permutation polynomial, where
d = 6*(2^m-1)+1.

This module chooses a cyclotomic presentation in which a noncube factor is
known by a Gaussian-period identity.  A random public cube W makes the actual
coefficient u=W*z vary from instance to instance.  The answer is the exact
GF(2)-polynomial z; it is constructed from the quadratic residues modulo p,
never recovered by solving the generated equation.
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
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "finite field GF(2)[beta]/(1+beta+...+beta^(p-1))",
        "unit-circle elements in GF(2^(2m))",
        "binomial permutation polynomial x^d+u*x",
    ],
    "verification_operations": [
        "exact carryless polynomial multiplication modulo a cyclotomic polynomial",
        "exact Frobenius squaring over GF(2)",
        "exact finite-field exponentiation and equality",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Split the nonzero powers of the cyclotomic generator into quadratic "
        "residues and nonresidues; Frobenius squaring swaps the two period sums, "
        "whereas a generic method must perform finite-field root extraction."
    ),
    "hardness_basis": (
        "Track B: a standard binary-exponentiation root extraction computes "
        "a nontrivial cube root of unity in O(m) finite-field operations; at the "
        "current shipping preset m=89 it is measured in selftest, while the "
        "compact Gaussian-period route uses exactly 89 modular squarings."
    ),
    "max_answer_tokens": 75,
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

# m is the paper's half-degree.  Each listed p=2m+1 is prime and 2 is a
# primitive root modulo p, so Phi_p is irreducible over GF(2).  make_instance
# also checks these facts and can find the next admissible m for other n.
DIFFICULTY = {
    "demo": {"n": 1},
    "easy": {"n": 29},
    "medium": {"n": 89},
    "hard": {"n": 173},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "The nonzero powers of beta split into quadratic residues and nonresidues "
    "modulo p, and Frobenius squaring swaps their two period sums."
)
PLACEBO_HINT = (
    "The support must be written in increasing order, and every field reduction "
    "should be checked carefully before submission."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A strictly increasing JSON list giving the support of one nonconstant "
        "polynomial z=sum(beta^e) of degree below 2m over GF(2); all exponents "
        "are integers in [0,2m-1], with no repetitions.  The zero and one "
        "polynomials are excluded, leaving 2^(2m)-2 candidates."
    ),
    "bounds": {
        "coefficient_field": 2,
        "max_degree_exclusive": "2m",
        "max_support_size": "2m",
        "excluded_polynomials": ["0", "1"],
        "candidate_count": "2^(2m)-2",
    },
}

NOTES = (
    "Section 2 fixes the exact definition of a permutation polynomial.  Section "
    "3, Theorem 1 reduces the relevant binomial family to a unit-circle element "
    "outside U^r; Proposition 2 specializes to d=s(2^m-1)+1, and Proposition "
    "3(3) proves the s=6 regime for odd m with 5 not dividing m.  The theorem's "
    "power tests make Track A unavailable: the coefficient criterion is "
    "efficient, and a root of z^2+z+1 can be obtained mechanically by finite-"
    "field exponentiation or GF(2) linear algebra.  The generator instead uses "
    "the identity z=sum_{a quadratic residue} beta^a: squaring sends its support "
    "to the nonresidues, and the two supports sum to 1 because Phi_p(beta)=0.  "
    "A random Hilbert-90 image, cubed, supplies W in U^3, so u=Wz is a varying "
    "noncube.  Support-of-W, diagonal, small-support, regular-pattern, and random-"
    "restart attacks are measured and fail; the standard exponentiation route is "
    "reported separately because Track B expects it to succeed."
)


# Filled from the three harness runs before final delivery.  G9's oracle arms are
# diagnostic under the current protocol; only the answer/operation caps are gated.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


def _is_prime(value):
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


def _prime_factors(value):
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


def _two_is_primitive(p):
    order = p - 1
    return pow(2, order, p) == 1 and all(
        pow(2, order // factor, p) != 1 for factor in _prime_factors(order)
    )


def _admissible_m(m):
    if m < 1 or m % 2 == 0 or m % 3 == 0 or m % 5 == 0:
        return False
    p = 2 * m + 1
    return _is_prime(p) and _two_is_primitive(p)


def _next_admissible_m(n):
    m = max(1, n)
    if m % 2 == 0:
        m += 1
    # The named presets and supported escalation range find a value quickly.
    # The cap prevents a malformed call from hanging on an unbounded search.
    for _ in range(100_000):
        if _admissible_m(m):
            return m
        m += 2
    raise ValueError("no admissible cyclotomic degree found near n")


def _mask(inst):
    return (1 << inst["degree"]) - 1


def _mul_bits(left, right, p):
    """Multiply in GF(2)[beta]/Phi_p using beta^p=1 and Phi_p=0."""
    degree = p - 1
    mask = (1 << degree) - 1
    left &= mask
    right &= mask
    if left.bit_count() < right.bit_count():
        left, right = right, left
    raw = 0
    work = right
    while work:
        low = work & -work
        shift = low.bit_length() - 1
        raw ^= left << shift
        work ^= low
    p_mask = (1 << p) - 1
    cyclic = (raw & p_mask) ^ (raw >> p)
    # beta^(p-1) = 1+beta+...+beta^(p-2) in characteristic two.
    if (cyclic >> degree) & 1:
        cyclic ^= p_mask
    return cyclic & mask


def _square_bits(value, p):
    """Frobenius squaring; exponents double modulo p."""
    degree = p - 1
    mask = (1 << degree) - 1
    value &= mask
    out = 0
    while value:
        low = value & -value
        exponent = low.bit_length() - 1
        doubled = (2 * exponent) % p
        if doubled == degree:
            out ^= mask
        else:
            out ^= 1 << doubled
        value ^= low
    return out


def _pow_bits(base, exponent, p):
    result = 1
    while exponent:
        if exponent & 1:
            result = _mul_bits(result, base, p)
        exponent >>= 1
        if exponent:
            base = _square_bits(base, p)
    return result


def _pow_bits_counted(base, exponent, p):
    """Binary exponentiation plus an implementation-independent work count."""
    result = 1
    multiplications = 0
    squarings = 0
    schoolbook_terms = 0
    square_terms = 0
    while exponent:
        if exponent & 1:
            schoolbook_terms += result.bit_count() * base.bit_count()
            result = _mul_bits(result, base, p)
            multiplications += 1
        exponent >>= 1
        if exponent:
            square_terms += base.bit_count()
            base = _square_bits(base, p)
            squarings += 1
    return result, {
        "field_multiplications": multiplications,
        "field_squarings": squarings,
        "schoolbook_coefficient_products": schoolbook_terms,
        "frobenius_coordinate_moves": square_terms,
    }


def _bits_to_support(value, degree):
    return [exponent for exponent in range(degree) if (value >> exponent) & 1]


def _support_to_bits(support):
    value = 0
    for exponent in support:
        value |= 1 << exponent
    return value


def _quadratic_residue_support(p):
    m = (p - 1) // 2
    return sorted({(value * value) % p for value in range(1, m + 1)})


def _nontrivial_cube_root(p):
    return _support_to_bits(_quadratic_residue_support(p))


def make_instance(n, seed=0, **params):
    """Construct a certified coefficient by a Gaussian-period identity.

    z is assembled directly from the quadratic residues.  Independently, a
    random nonzero X is mapped to V=X^(2^m-1) in the unit circle and W=V^3.
    Thus W is a cube and W*z is a noncube by construction; no generated
    equation is solved to obtain the answer.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer")
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    m = _next_admissible_m(n)
    p = 2 * m + 1
    degree = 2 * m
    q = 1 << m
    unit_order = q + 1
    rng = random.Random(seed)

    # This is the certificate-producing construction, not a solve.
    answer = _quadratic_residue_support(p)
    z = _support_to_bits(answer)

    # Hilbert 90: X^(q-1) is uniform on U for uniform nonzero X.  Cubing it
    # gives a public cube W.  Avoid W=1 only to improve instance diversity.
    while True:
        x = rng.randrange(1, 1 << degree)
        circle = _pow_bits(x, q - 1, p)
        w = _pow_bits(circle, 3, p)
        # U has order three in the hand-scale m=1 demo, so its cube subgroup is
        # necessarily {1}; larger presets reject that lone low-diversity value.
        if w != 1 or m == 1:
            break

    return {
        "family": "Gaussian-period noncube coefficient",
        "requested_n": n,
        "m": m,
        "p": p,
        "degree": degree,
        "q": q,
        "unit_order": unit_order,
        "d": 6 * (q - 1) + 1,
        "W": w,
        "W_support": _bits_to_support(w, degree),
        "answer": answer,
    }


def render(inst):
    m = inst["m"]
    p = inst["p"]
    degree = inst["degree"]
    q = inst["q"]
    unit_order = inst["unit_order"]
    d = inst["d"]
    w_support = json.dumps(inst["W_support"], separators=(",", ":"))
    statement = f"""Find a certified coefficient for a binomial permutation polynomial.

Work over the field

    F = GF(2)[beta] / (sum_(j=0)^({p - 1}) beta^j).

Here p={p}, m={m}, and 2 is a primitive root modulo p.  Consequently the
displayed cyclotomic polynomial is irreducible of degree p-1={degree}, so every
element of F has a unique form sum_(e=0)^({degree - 1}) a_e beta^e with a_e in
GF(2).  Addition is coefficientwise XOR; multiplication is ordinary polynomial
multiplication with coefficients modulo 2, reduced by the displayed relation.

Let q=2^m={q}.  The unit circle is U={{y in F: y^(q+1)=1}} and has order
q+1={unit_order}.  A public cube W in U is

    W = sum_(e in S_W) beta^e,
    S_W = {w_support}.

The public data satisfy W^((q+1)/3)=1.  Find a nonconstant element

    z = sum_(e in S_z) beta^e

such that z^2+z+1=0.  Your witness is the support S_z.  It also certifies the
actual coefficient u=W*z: the checker requires u^(q+1)=1 and
u^((q+1)/3) != 1.  For these paper parameters, Section 3's criterion then makes

    f(X) = X^d + u*X,       d={d},

a permutation of F (and u^(-1) X^d a complete permutation monomial).

Write S_z as a JSON list of distinct integer exponents in strictly increasing
order.  Bounds are inclusive: 0 <= e <= {degree - 1}.  A listed exponent has
coefficient 1, an omitted exponent has coefficient 0, and repetitions are not
allowed.  Either of the two valid roots is accepted.

Give your final answer inside <answer></answer> tags, as that JSON list.
Example format: <answer>[0,1]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse a tagged JSON support list, tolerating prose and markdown fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        return None
    return value


def verify(inst, answer):
    """Check any valid polynomial witness exactly; never consult inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "support must not be empty"
    if any(isinstance(item, bool) or not isinstance(item, int) for item in answer):
        return False, "every support exponent must be an integer"
    degree = inst["degree"]
    if any(item < 0 or item >= degree for item in answer):
        return False, f"support exponent outside 0..{degree - 1}"
    if len(set(answer)) != len(answer):
        return False, "support contains a repeated exponent"
    if answer != sorted(answer):
        return False, "support must be strictly increasing"

    z = _support_to_bits(answer)
    if z in (0, 1):
        return False, "z must be nonconstant"
    p = inst["p"]
    if _square_bits(z, p) ^ z ^ 1:
        return False, "z^2+z+1 is not zero in F"

    u = _mul_bits(inst["W"], z, p)
    unit_order = inst["unit_order"]
    if _pow_bits(u, unit_order, p) != 1:
        return False, "W*z is not on the unit circle"
    if _pow_bits(u, unit_order // 3, p) == 1:
        return False, "W*z is a cube on the unit circle"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample all nonzero, nonconstant canonical field polynomials."""
    value = rng.randrange(2, 1 << inst["degree"])
    return _bits_to_support(value, inst["degree"])


def search_space(inst):
    return (1 << inst["degree"]) - 2


def enumerate_all(inst):
    total = search_space(inst)
    if total > 100_000:
        return None
    return sum(
        verify(inst, _bits_to_support(value, inst["degree"]))[0]
        for value in range(2, 1 << inst["degree"])
    )


def _frobenius(value, steps, p):
    for _ in range(steps % (p - 1)):
        value = _square_bits(value, p)
    return value


def canonical_key(inst):
    """Canonicalize the public cube under every GF(2)-field automorphism.

    Since 2 is primitive modulo p, changing the cyclotomic generator to any
    conjugate beta^(2^j) is exactly a Frobenius power.  The least coordinate
    integer on W's full Frobenius orbit is therefore representation-invariant.
    """
    p = inst["p"]
    value = inst["W"]
    orbit_min = value
    for _ in range(1, inst["degree"]):
        value = _square_bits(value, p)
        orbit_min = min(orbit_min, value)
    payload = f"{inst['m']}:{p}:{orbit_min}".encode()
    return hashlib.sha256(payload).hexdigest()


def escalate(params):
    """Increase field degree until the native polynomial witness hits its cap."""
    current = params.get("n")
    if not isinstance(current, int):
        return None
    for candidate in (209, 221, 233):
        if current < candidate:
            return {"n": candidate}
    # The next admissible half-degree is 329, forcing at least 329 support atoms
    # for one root, beyond the 256-atom output cap.
    return "cap_bound"


def _standard_root_extraction(inst):
    """Generic multiplicative root extraction, independent of the construction."""
    p = inst["p"]
    degree = inst["degree"]
    exponent = ((1 << degree) - 1) // 3
    rng = random.Random(0x13100337 ^ p)
    totals = {
        "field_multiplications": 0,
        "field_squarings": 0,
        "schoolbook_coefficient_products": 0,
        "frobenius_coordinate_moves": 0,
        "trials": 0,
    }
    for _ in range(64):
        trial = rng.randrange(2, 1 << degree)
        root, counts = _pow_bits_counted(trial, exponent, p)
        totals["trials"] += 1
        for key, value in counts.items():
            totals[key] += value
        if root != 1 and (_square_bits(root, p) ^ root ^ 1) == 0:
            return _bits_to_support(root, degree), totals
    return None, totals


def _linear_algebra_reference(inst):
    """Solve z^2+z=1 as a GF(2) system, with packed exact row reduction."""
    degree = inst["degree"]
    p = inst["p"]
    rows = [0] * degree
    for column in range(degree):
        image = _square_bits(1 << column, p) ^ (1 << column)
        work = image
        while work:
            low = work & -work
            row = low.bit_length() - 1
            rows[row] |= 1 << column
            work ^= low
    rows[0] |= 1 << degree

    pivot_row = 0
    pivots = []
    row_xors = 0
    coefficient_inspections = 0
    for column in range(degree):
        pivot = None
        for row in range(pivot_row, degree):
            coefficient_inspections += 1
            if (rows[row] >> column) & 1:
                pivot = row
                break
        if pivot is None:
            continue
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        for row in range(degree):
            coefficient_inspections += 1
            if row != pivot_row and ((rows[row] >> column) & 1):
                rows[row] ^= rows[pivot_row]
                row_xors += 1
        pivots.append(column)
        pivot_row += 1

    for row in rows:
        if (row & ((1 << degree) - 1)) == 0 and ((row >> degree) & 1):
            return None, {}
    solution = 0
    for row_index, column in enumerate(pivots):
        if (rows[row_index] >> degree) & 1:
            solution |= 1 << column
    counts = {
        "rank": len(pivots),
        "packed_row_xors": row_xors,
        "coefficient_inspections": coefficient_inspections,
        "bit_xor_operations": row_xors * (degree + 1),
    }
    return _bits_to_support(solution, degree), counts


def _normalized_candidate(value, degree):
    value &= (1 << degree) - 1
    if value in (0, 1):
        value ^= 2
    return _bits_to_support(value, degree)


def _attack_candidates(inst, seed):
    degree = inst["degree"]
    m = inst["m"]
    w = inst["W"]
    mask = (1 << degree) - 1

    outlier = [
        _normalized_candidate(w, degree),
        _normalized_candidate(w ^ mask, degree),
        _bits_to_support(sum(1 << i for i in range(m)), degree),
        _bits_to_support(sum(1 << i for i in range(m, degree)), degree),
    ]

    # A coefficientwise diagonal approximation to (Frobenius+I)z=1.
    diagonal = 0
    for i in range(degree):
        image = _square_bits(1 << i, inst["p"]) ^ (1 << i)
        rhs = 1 if i == 0 else 0
        if ((image >> i) & 1) and rhs:
            diagonal |= 1 << i
    diagonal_candidates = [_normalized_candidate(diagonal, degree)]

    small_support = []
    for i in range(1, degree):
        small_support.append([i])
        small_support.append([0, i])

    regular_values = []
    for support in (
        list(range(0, degree, 2)),
        list(range(1, degree, 2)),
        list(range(0, degree, 3)),
        list(range(1, degree, 3)),
        list(range(2, degree, 3)),
        list(range(m)),
        list(range(m, degree)),
    ):
        value = _support_to_bits(support)
        regular_values.append(_normalized_candidate(value, degree))

    rrng = random.Random(seed ^ 0x5A17C0DE)
    restarts = [random_candidate(inst, rrng) for _ in range(256)]
    return {
        "outlier_public_cube_support": outlier,
        "greedy_diagonal_frobenius_solve": diagonal_candidates,
        "small_support_monomial_binomial": small_support,
        "by_hand_regular_support_patterns": regular_values,
        "random_restart_256": restarts,
    }


def _relabel_variants(inst, seed):
    rng = random.Random(seed)
    degree = inst["degree"]
    p = inst["p"]
    variants = []
    steps = sorted({1, degree - 1, rng.randrange(1, degree)})
    for step, swap_root in itertools.product(steps, (False, True)):
        transformed = dict(inst)
        transformed["W"] = _frobenius(inst["W"], step, p)
        transformed["W_support"] = _bits_to_support(transformed["W"], degree)
        answer_bits = _frobenius(_support_to_bits(inst["answer"]), step, p)
        if swap_root:
            answer_bits ^= 1
        transformed["answer"] = _bits_to_support(answer_bits, degree)
        variants.append(transformed)
    return variants


def selftest():
    report = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    g1_failures = []
    g1_attempts = 0
    parameter_checks = {}
    for preset, params in DIFFICULTY.items():
        probe = make_instance(seed=0, **params)
        probe_z = _support_to_bits(probe["answer"])
        probe_u = _mul_bits(probe["W"], probe_z, probe["p"])
        parameter_checks[preset] = {
            "m": probe["m"],
            "p_prime": _is_prime(probe["p"]),
            "two_primitive_mod_p": _two_is_primitive(probe["p"]),
            "m_odd": probe["m"] % 2 == 1,
            "five_not_dividing_m": probe["m"] % 5 != 0,
            "nine_not_dividing_unit_order": probe["unit_order"] % 9 != 0,
            "public_W_on_unit_circle": (
                _pow_bits(probe["W"], probe["unit_order"], probe["p"]) == 1
            ),
            "public_W_is_cube": (
                _pow_bits(
                    probe["W"], probe["unit_order"] // 3, probe["p"]
                )
                == 1
            ),
            "constructed_z_is_quadratic_root": (
                _square_bits(probe_z, probe["p"]) ^ probe_z ^ 1
            )
            == 0,
            "constructed_u_is_noncube": (
                _pow_bits(probe_u, probe["unit_order"] // 3, probe["p"])
                != 1
            ),
        }
        if preset == "demo":
            outputs = [
                _pow_bits(x, probe["d"], probe["p"])
                ^ _mul_bits(probe_u, x, probe["p"])
                for x in range(1 << probe["degree"])
            ]
            parameter_checks[preset]["binomial_bijection_exhaustive"] = (
                len(set(outputs)) == 1 << probe["degree"]
            )
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    all_parameters = all(all(checks.values()) for checks in parameter_checks.values())
    report["G1_planted_verifies"] = {
        "pass": not g1_failures and all_parameters,
        "attempts": g1_attempts,
        "failures": g1_failures,
        "parameter_checks": parameter_checks,
    }

    inst = make_instance(seed=19, **shipping)
    answer = inst["answer"]
    swapped = list(answer)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = list(answer) + [answer[-1]]
    out_of_range = list(answer)
    out_of_range[-1] = inst["degree"]
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = [item["reason"] for item in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in rejected.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The two period sums are exchanged by Frobenius.\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nThe support is in canonical order."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x13100337)
    guess_total = 200_000
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - start
    guess_fraction = guess_hits / guess_total
    exact_numerator = 2
    exact_denominator = search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "exact_density": f"{exact_numerator}/{exact_denominator}",
        "candidate_space_bits": exact_denominator.bit_length(),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = [
        "outlier_public_cube_support",
        "greedy_diagonal_frobenius_solve",
        "small_support_monomial_binomial",
        "by_hand_regular_support_patterns",
        "random_restart_256",
    ]
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_counts = None
    linear_successes = 0
    linear_seconds = 0.0
    linear_counts = None
    compact_successes = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        candidates = _attack_candidates(trial, seed)
        for name in attack_names:
            start = time.perf_counter()
            won = any(verify(trial, candidate)[0] for candidate in candidates[name])
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(won)

        start = time.perf_counter()
        root, counts = _standard_root_extraction(trial)
        reference_seconds += time.perf_counter() - start
        reference_successes += int(root is not None and verify(trial, root)[0])
        reference_counts = counts

        start = time.perf_counter()
        linear_root, counts = _linear_algebra_reference(trial)
        linear_seconds += time.perf_counter() - start
        linear_successes += int(
            linear_root is not None and verify(trial, linear_root)[0]
        )
        linear_counts = counts

        compact = _quadratic_residue_support(trial["p"])
        compact_successes += int(verify(trial, compact)[0])

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name] / 8, 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "binary exponentiation to (2^(2m)-1)/3 with random trials",
        "complexity": "O(m) finite-field operations; O(m^3) schoolbook bit operations",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": (
            reference_counts["schoolbook_coefficient_products"]
            + reference_counts["frobenius_coordinate_moves"]
        ),
        **reference_counts,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed
        and reference_successes == 8
        and linear_successes == 8
        and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "additional_reference_algorithm": {
            "name": "packed Gaussian elimination on (Frobenius+I)z=1",
            "complexity": "O((2m)^3) bit operations in the dense model",
            "wall_clock_sec": round(linear_seconds / 8, 6),
            **linear_counts,
            "solves": f"{linear_successes}/8, as expected",
        },
        "intended_compact_route": {
            "name": "quadratic-residue Gaussian period",
            "solves": f"{compact_successes}/8",
            "operations_upper_bound": inst["m"],
        },
    }

    demo_count = enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))
    exact_density_float = exact_numerator / exact_denominator
    report["G5_density_and_baseline_cost"] = {
        "pass": exact_density_float < 1e-6
        and demo_count == 2
        and all_failed
        and reference_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_sample_density": guess_fraction,
        "shipping_exact_solution_count": 2,
        "shipping_exact_candidate_count": exact_denominator,
        "shipping_exact_density": exact_density_float,
        "demo_exact_solution_count": demo_count,
        "baseline_attack": "random_restart_256",
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
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    ladder_m = [make_instance(seed=0, **params)["m"] for params in DIFFICULTY.values()]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["m"] >= 2 * inst["m"]
        and len(render(doubled)) > len(render(inst))
        and ladder_m == sorted(ladder_m)
        and len(set(ladder_m)) == len(ladder_m),
        "shipping_m": inst["m"],
        "doubled_requested_n": doubled_params["n"],
        "doubled_actual_m": doubled["m"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_why,
        "candidate_space_bits_shipping": search_space(inst).bit_length(),
        "candidate_space_bits_doubled": search_space(doubled).bit_length(),
    }

    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    variants_per_seed = None
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping)
        key = canonical_key(original)
        variants = _relabel_variants(original, seed ^ 0xBEEF)
        variants_per_seed = len(variants)
        for transformed in variants:
            invariant_count += int(key == canonical_key(transformed))
            real_transform_count += int(
                verify(transformed, transformed["answer"])[0]
            )
        unrelated_keys.append(key)
    expected_invariants = 20 * variants_per_seed
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == expected_invariants
        and real_transform_count == expected_invariants
        and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "invariant_attempts": expected_invariants,
        "real_transformations_verified": real_transform_count,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "Frobenius relabelling beta -> beta^2",
            "two additional powers of the Frobenius relabelling",
            "each relabelling composed with swapping the two valid quadratic roots",
        ],
    }

    encoded_answer = json.dumps(inst["answer"], separators=(",", ":"))
    alternate_bits = _support_to_bits(inst["answer"]) ^ 1
    alternate_answer = _bits_to_support(alternate_bits, inst["degree"])
    alternate_encoded = json.dumps(alternate_answer, separators=(",", ":"))
    answer_chars = len(encoded_answer)
    worst_case_answer_chars = max(len(encoded_answer), len(alternate_encoded))
    answer_tokens = math.ceil(answer_chars / 4)
    worst_case_answer_tokens = math.ceil(worst_case_answer_chars / 4)
    answer_elements = len(inst["answer"])
    worst_case_answer_elements = max(len(inst["answer"]), len(alternate_answer))
    intended_operations = inst["m"]
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        worst_case_answer_chars <= 2_000
        and worst_case_answer_elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == worst_case_answer_tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "diagnostic_only": True,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_case_answer_chars,
        "worst_case_answer_tokens": worst_case_answer_tokens,
        "answer_elements": answer_elements,
        "worst_case_answer_elements": worst_case_answer_elements,
        "intended_route_operations": intended_operations,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
