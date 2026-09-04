"""Verified generator for a skew-polynomial locator problem from arXiv:2207.14270.

The construction is Proposition 15 of the paper.  The checker does not trust that
proposition: it verifies P-independence by an exact skew-Vandermonde rank computation
and evaluates the submitted Ore polynomial at every supplied right root.
"""

from __future__ import annotations

import functools
import hashlib
import itertools
import json
import math
import os
import random
import re
import time


TRACK = "B"

# The measured figures in hardness_basis are refreshed after selftest().
PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "finite field quotient",
        "Ore polynomial over a finite field",
        "P-independent skew-conjugacy class",
    ],
    "verification_operations": [
        "exact finite-field multiplication",
        "Frobenius automorphism",
        "right evaluation of an Ore polynomial",
        "skew-Vandermonde rank over a finite field",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize that a full P-independent skew-conjugacy class collapses its "
        "locator to a binomial governed by the common field norm; otherwise one "
        "must carry out iterative Ore-polynomial LCLM arithmetic."
    ),
    "hardness_basis": (
        "Track B: the iterative left-LCM algorithm implicit in Section 4 and "
        "Proposition 15 runs in polynomial time; at the shipping preset our exact "
        "implementation averages 0.221259 seconds and 1,393,359 low-level "
        "multiply-loop steps, whereas the norm-invariant route uses 15 high-level "
        "exact field operations."
    ),
    "max_answer_tokens": 36,
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

DIFFICULTY = {
    "demo": {"n": 2, "delta": 2},
    "easy": {"n": 8, "delta": 32},
    "medium": {"n": 12, "delta": 32},
    "hard": {"n": 16, "delta": 32},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "A full P-independent subset of one skew-conjugacy class has locator x^n "
    "minus the class's common field norm."
)
PLACEBO_HINT = (
    "A careful coefficient-by-coefficient computation helps prevent indexing "
    "mistakes in the requested locator."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "The structure-aware binomial language x^n+c with nonzero c in the fixed "
        "field K=GF(2^delta), represented by two [exponent, coefficient] terms; "
        "each coefficient is an M/4-digit lowercase hexadecimal element of "
        "GF(2^M). The verifier remains more permissive and checks any sparse monic "
        "degree-n polynomial term by term."
    ),
    "bounds": {
        "n_terms": 2,
        "max_degree": "n",
        "coefficient_bits": "M=n*delta",
        "constant_choices": "2^delta-1",
        "leading_coefficient": 1,
    },
}

NOTES = (
    "Section 2, Definition 3 fixes right roots and least common left multiples. "
    "Section 4, Proposition 15 is the theorem-backed construction: a K-basis "
    "c_i gives P-independent points sigma(c_i)*a/c_i, and a complete class has "
    "locator x^mu-N(a). Proposition 16 explains how conjugacy classes combine. "
    "The easy-result discriminator is explicit here: iterative Ore LCLM and the "
    "displayed norm formula are polynomial-time algorithms, so this is Track B, "
    "not Track A. Random basis changes and point shuffling remove positional "
    "outliers; the norm is uniform in a 32-bit fixed field, defeating constant-one, "
    "small-constant, ordinary-product, and truncated-norm guesses."
)

# Monic irreducible binary polynomials.  The integer's bit i is the coefficient
# of z^i.  Each constant was independently checked by Rabin's exact criterion in
# selftest().  The larger four are sparse pentanomials found once during building.
_MODULI = {
    4: 0x13,
    256: int(
        "10000000000000000000000000000000000000000000200000040000080000001", 16
    ),
    384: int(
        "1000000000000000000000000000000000000000000000000000000000000000"
        "000000000200000000000010000008001", 16
    ),
    512: int(
        "1000000000000000000000000000000000000000000000000000000000000000"
        "00000000000000000000000000000000000000000000020000000010000000009", 16
    ),
    640: int(
        "1000000000000000000000000000000000000000000000000000000000000000"
        "0000000000000000000000000000000000000000000000000000000000000000"
        "000000000000000000000000080104001", 16
    ),
}

G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


def _prime_divisors(v):
    out = []
    p = 2
    while p * p <= v:
        if v % p == 0:
            out.append(p)
            while v % p == 0:
                v //= p
        p += 1
    if v > 1:
        out.append(v)
    return out


def _poly2_mod(a, modulus):
    md = modulus.bit_length() - 1
    while a and a.bit_length() - 1 >= md:
        a ^= modulus << (a.bit_length() - 1 - md)
    return a


def _poly2_gcd(a, b):
    while b:
        a, b = b, _poly2_mod(a, b)
    return a


_SPREAD8 = tuple(
    sum(((b >> i) & 1) << (2 * i) for i in range(8)) for b in range(256)
)


def _poly2_square_mod(a, modulus):
    expanded = 0
    shift = 0
    while a:
        expanded |= _SPREAD8[a & 255] << shift
        a >>= 8
        shift += 16
    return _poly2_mod(expanded, modulus)


@functools.lru_cache(maxsize=None)
def _binary_irreducible(modulus, degree):
    if modulus.bit_length() - 1 != degree or not (modulus & 1):
        return False
    x = 2
    checkpoints = {degree // p for p in _prime_divisors(degree)}
    powers = {}
    h = x
    for i in range(1, degree + 1):
        h = _poly2_square_mod(h, modulus)
        if i in checkpoints:
            powers[i] = h
    return h == x and all(_poly2_gcd(powers[i] ^ x, modulus) == 1 for i in checkpoints)


def _gf_mul(a, b, degree, modulus, counter=None):
    """Multiply in GF(2^degree), optionally counting exact loop work."""
    mask = (1 << degree) - 1
    low_modulus = modulus & mask
    result = 0
    loops = 0
    while b:
        if b & 1:
            result ^= a
        b >>= 1
        carry = a >> (degree - 1)
        a = (a << 1) & mask
        if carry:
            a ^= low_modulus
        loops += 1
    if counter is not None:
        counter["field_multiplications"] += 1
        counter["multiply_loop_steps"] += loops
    return result


def _gf_pow(a, exponent, degree, modulus, counter=None):
    result = 1
    base = a
    while exponent:
        if exponent & 1:
            result = _gf_mul(result, base, degree, modulus, counter)
        exponent >>= 1
        if exponent:
            base = _gf_mul(base, base, degree, modulus, counter)
    return result


def _gf_inv(a, degree, modulus, counter=None):
    if a == 0:
        raise ZeroDivisionError("zero has no inverse")
    return _gf_pow(a, (1 << degree) - 2, degree, modulus, counter)


def _sigma(a, delta, degree, modulus, counter=None):
    for _ in range(delta):
        a = _gf_mul(a, a, degree, modulus, counter)
    return a


def _norm(a, delta, order, degree, modulus, counter=None):
    product = 1
    conjugate = a
    for j in range(order):
        product = _gf_mul(product, conjugate, degree, modulus, counter)
        if j + 1 < order:
            conjugate = _sigma(conjugate, delta, degree, modulus, counter)
    return product


def _field_hex(value, degree):
    return f"{value:0{(degree + 3) // 4}x}"


def _modulus_hex(value, degree):
    return f"{value:0{(degree + 4) // 4}x}"


def _field_int(text, degree):
    if not isinstance(text, str):
        return None
    digits = (degree + 3) // 4
    if re.fullmatch(rf"[0-9a-f]{{{digits}}}", text) is None:
        return None
    value = int(text, 16)
    return value if value < (1 << degree) else None


def make_instance(n, seed=0, **params):
    """Construct Proposition 15 points and their locator without solving an LCLM."""
    if not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    delta = params.get("delta", 32)
    if not isinstance(delta, int) or delta < 1:
        raise ValueError("delta must be a positive integer")
    degree = n * delta
    if degree not in _MODULI:
        raise ValueError(f"supported field degrees are {sorted(_MODULI)}")
    modulus = _MODULI[degree]
    rng = random.Random(seed)

    # z has degree n over K=GF(2^delta), so 1,z,...,z^(n-1) is a K-basis.
    # Binary elementary basis changes are also K-linear and invertible.
    basis = [1 << i for i in range(n)]
    for _ in range(8 * n):
        i, j = rng.sample(range(n), 2)
        basis[i] ^= basis[j]
        if rng.randrange(4) == 0:
            basis[i], basis[j] = basis[j], basis[i]
    rng.shuffle(basis)

    a = rng.randrange(1, 1 << degree)
    points = []
    for c in basis:
        conjugator = _gf_mul(
            _sigma(c, delta, degree, modulus),
            _gf_inv(c, degree, modulus),
            degree,
            modulus,
        )
        points.append(_gf_mul(conjugator, a, degree, modulus))
    rng.shuffle(points)
    if len(set(points)) != n:
        raise AssertionError("the theorem-backed points were not distinct")

    common_norm = _norm(a, delta, n, degree, modulus)
    one = _field_hex(1, degree)
    answer = [[0, _field_hex(common_norm, degree)], [n, one]]
    return {
        "n": n,
        "delta": delta,
        "field_degree": degree,
        "modulus": _modulus_hex(modulus, degree),
        "points": [_field_hex(v, degree) for v in points],
        "answer": answer,
    }


def render(inst):
    n = inst["n"]
    degree = inst["field_degree"]
    width = (degree + 3) // 4
    rows = "\n".join(f"  {i + 1}: {a}" for i, a in enumerate(inst["points"]))
    example = json.dumps(
        [[0, "0" * (width - 1) + "1"], [n, "0" * (width - 1) + "1"]],
        separators=(",", ":"),
    )
    parts = [
        "Compute an exact locator polynomial in a skew-polynomial ring.\n\n",
        f"Let L = GF(2^{degree}) = GF(2)[z]/(P(z)), where P is the monic "
        f"irreducible binary polynomial encoded by 0x{inst['modulus']}. Bit i of "
        "this integer is the coefficient of z^i. Field addition is bitwise XOR; "
        "field multiplication is carryless polynomial multiplication reduced "
        "modulo P. Every field element below is exactly ",
        str(width),
        " lowercase hexadecimal digits in this polynomial basis (no 0x prefix).\n\n",
        f"Define sigma(u)=u^(2^{inst['delta']}). In the Ore ring L[x;sigma], "
        "coefficients are written on the left and x*u=sigma(u)*x. For b in L, "
        "define N_0(b)=1 and N_j(b)=b*sigma(b)*...*sigma^(j-1)(b). The right "
        "evaluation of f(x)=sum_j f_j*x^j at b is f[b]=sum_j f_j*N_j(b). Thus b "
        "is a right root exactly when f[b]=0.\n\n",
        f"The following {n} nonzero points are promised to be left P-independent: "
        "equivalently, the square matrix with entry N_j(b_i) in row j=0,...,n-1 "
        "and column i=1,...,n is nonsingular over L. They are also promised to lie "
        "in one sigma-conjugacy class, where b and b' are conjugate when "
        "b'=sigma(c)*b*c^(-1) for some nonzero c.\n\n",
        "Points (their order has no significance):\n",
        rows,
        "\n\nFind the unique monic Ore polynomial of degree exactly n having every listed "
        "point as a right root. A monic polynomial has coefficient 1 on x^n.\n\n",
        "Represent the polynomial sparsely as a JSON list of its nonzero "
        "[exponent,coefficient] terms, in strictly increasing exponent order. "
        f"Exponents are integers from 0 through {n}; coefficients are exactly "
        f"{width}-digit lowercase hexadecimal strings. Omit zero coefficients; "
        f"include the final term [{n},\"{'0' * (width - 1)}1\"].\n",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        parts.extend(["\nHint: ", STRUCTURAL_HINT, "\n"])
    elif mode == "placebo":
        parts.extend(["\nHint: ", PLACEBO_HINT, "\n"])
    parts.extend(
        [
            "\nGive your final answer inside <answer></answer> tags, as the JSON "
            "list just specified.\n",
            f"Example of the required syntax: <answer>{example}</answer>\n",
            "Output nothing else inside the tags.",
        ]
    )
    return "".join(parts)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def _decode_instance(inst):
    degree = inst.get("field_degree")
    delta = inst.get("delta")
    n = inst.get("n")
    try:
        modulus = int(inst.get("modulus"), 16)
        points = tuple(int(a, 16) for a in inst.get("points", ()))
    except (TypeError, ValueError):
        return None
    if (
        not isinstance(n, int)
        or not isinstance(delta, int)
        or not isinstance(degree, int)
        or degree != n * delta
        or len(points) != n
        or modulus.bit_length() - 1 != degree
        or any(not (0 < a < (1 << degree)) for a in points)
    ):
        return None
    return n, delta, degree, modulus, points


def _answer_to_dense(answer, n, degree):
    if not isinstance(answer, list):
        return None, "answer must be a JSON list"
    if not answer:
        return None, "answer must contain at least one term"
    if len(answer) > n + 1:
        return None, "too many nonzero terms"
    pairs = []
    for term in answer:
        if not isinstance(term, list) or len(term) != 2:
            return None, "each term must be [exponent, coefficient]"
        exponent, encoded = term
        if not isinstance(exponent, int) or isinstance(exponent, bool):
            return None, "every exponent must be an integer"
        if exponent < 0 or exponent > n:
            return None, "exponent out of range"
        coefficient = _field_int(encoded, degree)
        if coefficient is None:
            return None, "coefficient has the wrong hexadecimal format"
        if coefficient == 0:
            return None, "zero coefficients must be omitted"
        pairs.append((exponent, coefficient))
    exponents = [e for e, _ in pairs]
    if len(set(exponents)) != len(exponents):
        return None, "exponents must be distinct"
    if exponents != sorted(exponents):
        return None, "terms must be strictly increasing"
    if pairs[-1] != (n, 1):
        return None, "leading term must be monic of degree n"
    dense = [0] * (n + 1)
    for exponent, coefficient in pairs:
        dense[exponent] = coefficient
    return dense, "ok"


def _right_eval_dense(coefficients, point, delta, degree, modulus, counter=None):
    total = coefficients[0]
    partial_norm = 1
    conjugate = point
    for j in range(1, len(coefficients)):
        partial_norm = _gf_mul(partial_norm, conjugate, degree, modulus, counter)
        if coefficients[j]:
            total ^= _gf_mul(coefficients[j], partial_norm, degree, modulus, counter)
        if j + 1 < len(coefficients):
            conjugate = _sigma(conjugate, delta, degree, modulus, counter)
    return total


def _fixed_multiplier_tables(value, degree, modulus):
    shifts = []
    current = value
    mask = (1 << degree) - 1
    low_modulus = modulus & mask
    for _ in range(degree):
        shifts.append(current)
        carry = current >> (degree - 1)
        current = (current << 1) & mask
        if carry:
            current ^= low_modulus
    chunks = []
    for start in range(0, degree, 8):
        atoms = shifts[start : start + 8]
        table = [0] * 256
        for v in range(1, 256):
            low = v & -v
            bit = low.bit_length() - 1
            table[v] = table[v ^ low] ^ (atoms[bit] if bit < len(atoms) else 0)
        chunks.append(tuple(table))
    return tuple(chunks)


def _mul_by_fixed(value, tables):
    result = 0
    i = 0
    while value:
        result ^= tables[i][value & 255]
        value >>= 8
        i += 1
    return result


@functools.lru_cache(maxsize=16)
def _first_point_eval_tables(point, n, delta, degree, modulus):
    values = [1]
    partial_norm = 1
    conjugate = point
    for j in range(1, n + 1):
        partial_norm = _gf_mul(partial_norm, conjugate, degree, modulus)
        values.append(partial_norm)
        if j < n:
            conjugate = _sigma(conjugate, delta, degree, modulus)
    return tuple(_fixed_multiplier_tables(v, degree, modulus) for v in values)


def _eval_with_tables(coefficients, tables):
    total = 0
    for coefficient, table in zip(coefficients, tables):
        if coefficient:
            total ^= _mul_by_fixed(coefficient, table)
    return total


@functools.lru_cache(maxsize=64)
def _p_independent_rank(points, n, delta, degree, modulus):
    columns = []
    for point in points:
        col = [1]
        partial_norm = 1
        conjugate = point
        for j in range(1, n):
            partial_norm = _gf_mul(partial_norm, conjugate, degree, modulus)
            col.append(partial_norm)
            if j + 1 < n:
                conjugate = _sigma(conjugate, delta, degree, modulus)
        columns.append(col)
    matrix = [[columns[c][r] for c in range(n)] for r in range(n)]
    rank = 0
    for column in range(n):
        pivot = next((r for r in range(rank, n) if matrix[r][column]), None)
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        inv = _gf_inv(matrix[rank][column], degree, modulus)
        matrix[rank] = [_gf_mul(v, inv, degree, modulus) for v in matrix[rank]]
        for r in range(n):
            if r != rank and matrix[r][column]:
                factor = matrix[r][column]
                matrix[r] = [
                    a ^ _gf_mul(factor, b, degree, modulus)
                    for a, b in zip(matrix[r], matrix[rank])
                ]
        rank += 1
    return rank


def verify(inst, answer):
    decoded = _decode_instance(inst)
    if decoded is None:
        return False, "malformed instance"
    n, delta, degree, modulus, points = decoded
    coefficients, reason = _answer_to_dense(answer, n, degree)
    if coefficients is None:
        return False, reason

    # Reject almost all bad candidates at one exact right evaluation.  The cached
    # linear maps merely accelerate multiplication by fixed N_j(point); they do not
    # compare with, or read, inst["answer"].
    tables = _first_point_eval_tables(points[0], n, delta, degree, modulus)
    if _eval_with_tables(coefficients, tables) != 0:
        return False, "point 1 is not a right root"
    for i, point in enumerate(points[1:], 2):
        if _right_eval_dense(coefficients, point, delta, degree, modulus) != 0:
            return False, f"point {i} is not a right root"
    rank = _p_independent_rank(points, n, delta, degree, modulus)
    if rank != n:
        return False, f"instance promise failed: skew-Vandermonde rank is {rank}, not {n}"
    return True, "ok"


@functools.lru_cache(maxsize=None)
def _fixed_field_basis(degree, delta, modulus):
    """Return an F2-basis of the unique GF(2^delta) subfield."""
    order = (1 << delta) - 1
    factors = _prime_divisors(order)
    extension_order = degree // delta
    generator = None
    for trial in range(2, 512):
        candidate = _norm(trial, delta, extension_order, degree, modulus)
        if candidate != 1 and all(
            _gf_pow(candidate, order // p, degree, modulus) != 1 for p in factors
        ):
            generator = candidate
            break
    if generator is None:
        raise RuntimeError("could not construct the fixed subfield")
    basis = [1]
    for _ in range(1, delta):
        basis.append(_gf_mul(basis[-1], generator, degree, modulus))
    return tuple(basis)


def _fixed_element_from_mask(mask, degree, delta, modulus):
    value = 0
    for i, basis_value in enumerate(_fixed_field_basis(degree, delta, modulus)):
        if (mask >> i) & 1:
            value ^= basis_value
    return value


def random_candidate(inst, rng):
    decoded = _decode_instance(inst)
    if decoded is None:
        raise ValueError("malformed instance")
    n, delta, degree, modulus, _points = decoded
    mask = rng.randrange(1, 1 << delta)
    constant = _fixed_element_from_mask(mask, degree, delta, modulus)
    return _binomial(inst, constant)


def search_space(inst):
    decoded = _decode_instance(inst)
    if decoded is None:
        return 0
    _n, delta, _degree, _modulus, _points = decoded
    return (1 << delta) - 1


def enumerate_all(inst):
    decoded = _decode_instance(inst)
    if decoded is None:
        return None
    n, delta, degree, modulus, _points = decoded
    space = search_space(inst)
    if space > 200_000:
        return None
    count = 0
    for mask in range(1, 1 << delta):
        constant = _fixed_element_from_mask(mask, degree, delta, modulus)
        candidate = _binomial(inst, constant)
        count += int(verify(inst, candidate)[0])
    return count


def canonical_key(inst):
    decoded = _decode_instance(inst)
    if decoded is None:
        return "malformed"
    n, delta, degree, modulus, points = decoded
    # Every full P-independent subset of this conjugacy class has the same monic
    # locator.  The common norm is computed from the data, never from the answer.
    invariant = _norm(points[0], delta, n, degree, modulus)
    payload = json.dumps(
        [n, delta, _modulus_hex(modulus, degree), _field_hex(invariant, degree)],
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params):
    n = params.get("n")
    delta = params.get("delta", 32)
    if not isinstance(n, int) or n >= 20:
        return None
    candidate = {"n": n + 4, "delta": delta}
    return candidate if candidate["n"] * delta in _MODULI else None


def _sparse_from_dense(coefficients, degree):
    return [
        [i, _field_hex(c, degree)]
        for i, c in enumerate(coefficients)
        if c
    ]


def _reference_lclm(inst):
    """Iteratively adjoin right roots using (x - conjugate) * f."""
    decoded = _decode_instance(inst)
    if decoded is None:
        return None, {}
    n, delta, degree, modulus, points = decoded
    counter = {"field_multiplications": 0, "multiply_loop_steps": 0}
    polynomial = [1]
    for point in points:
        remainder = _right_eval_dense(
            polynomial, point, delta, degree, modulus, counter
        )
        if remainder == 0:
            continue
        conjugated_root = _gf_mul(
            _gf_mul(
                _sigma(remainder, delta, degree, modulus, counter),
                point,
                degree,
                modulus,
                counter,
            ),
            _gf_inv(remainder, degree, modulus, counter),
            degree,
            modulus,
            counter,
        )
        product = [0] * (len(polynomial) + 1)
        for i, coefficient in enumerate(polynomial):
            product[i] ^= _gf_mul(
                conjugated_root, coefficient, degree, modulus, counter
            )
            product[i + 1] ^= _sigma(
                coefficient, delta, degree, modulus, counter
            )
        polynomial = product
    return _sparse_from_dense(polynomial, degree), counter


def _binomial(inst, constant):
    degree = inst["field_degree"]
    return [[0, _field_hex(constant, degree)], [inst["n"], _field_hex(1, degree)]]


def _attack_candidates(inst, seed):
    decoded = _decode_instance(inst)
    n, delta, degree, modulus, points = decoded
    attacks = {}

    # Outlier probe: treat the smallest encoded point as the special constant.
    attacks["outlier_smallest_encoded_point"] = [_binomial(inst, min(points))]

    # Greedy commutative shortcut: multiply the listed points without Frobenius.
    ordinary = 1
    for point in points:
        ordinary = _gf_mul(ordinary, point, degree, modulus)
    attacks["greedy_ordinary_product"] = [_binomial(inst, ordinary)]

    # A genuinely in-context partial-norm ansatz that stops after two factors.
    partial = _gf_mul(
        points[0], _sigma(points[0], delta, degree, modulus), degree, modulus
    )
    attacks["by_hand_two_factor_norm"] = [_binomial(inst, partial)]

    # Structure-aware restarts: sample uniformly from the 2^delta-1 nonzero
    # constants in the fixed field K.
    rng = random.Random(seed ^ 0xA5A55A5A)
    guesses = []
    for _ in range(256):
        mask = rng.randrange(1, 1 << delta)
        guesses.append(
            _binomial(inst, _fixed_element_from_mask(mask, degree, delta, modulus))
        )
    attacks["random_restart_256_fixed_field_constants"] = guesses
    return attacks


def _relabel_variants(inst, seed):
    decoded = _decode_instance(inst)
    n, delta, degree, modulus, points = decoded
    rng = random.Random(seed)
    while True:
        c = rng.randrange(1, 1 << degree)
        norm_one_multiplier = _gf_mul(
            _sigma(c, delta, degree, modulus),
            _gf_inv(c, degree, modulus),
            degree,
            modulus,
        )
        if norm_one_multiplier != 1:
            break
    variants = []
    # Bits select: input reordering, global skew conjugation, global Frobenius.
    # Enumerating masks 1..7 exercises each symmetry and every composition.
    for mask in range(1, 8):
        transformed = list(points)
        if mask & 2:
            transformed = [
                _gf_mul(norm_one_multiplier, p, degree, modulus) for p in transformed
            ]
        if mask & 4:
            transformed = [
                _sigma(p, delta, degree, modulus) for p in transformed
            ]
        if mask & 1:
            transformed = transformed[1:] + transformed[:1]
        out = dict(inst)
        out["points"] = [_field_hex(p, degree) for p in transformed]
        variants.append(out)
    return variants


def selftest():
    report = {}
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    inst = make_instance(seed=19, **shipping)
    answer = inst["answer"]
    corruptions = {
        "drop": answer[:-1],
        "swap": list(reversed(answer)),
        "duplicate": [answer[0], list(answer[0]), answer[1]],
        "empty": [],
        "out_of_range": [[-1, answer[0][1]], answer[1]],
        "coefficient_flip": [
            [0, _field_hex(int(answer[0][1], 16) ^ 1, inst["field_degree"])],
            answer[1],
        ],
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = [v["reason"] for v in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in rejected.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "I used the skew norm identity.\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nThat is my final polynomial."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x220714270)
    guess_total = 200_000
    guess_hits = 0
    t0 = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - t0
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "candidate_space_bits": search_space(inst).bit_length(),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = [
        "outlier_smallest_encoded_point",
        "greedy_ordinary_product",
        "by_hand_two_factor_norm",
        "random_restart_256_fixed_field_constants",
    ]
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_field_multiplications = 0
    reference_loop_steps = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        candidates = _attack_candidates(trial, seed)
        for name in attack_names:
            start = time.perf_counter()
            won = any(verify(trial, candidate)[0] for candidate in candidates[name])
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(won)
        start = time.perf_counter()
        recovered, counts = _reference_lclm(trial)
        reference_seconds += time.perf_counter() - start
        reference_successes += int(verify(trial, recovered)[0])
        reference_field_multiplications += counts["field_multiplications"]
        reference_loop_steps += counts["multiply_loop_steps"]
    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "iterative Ore-polynomial least common left multiple",
        "complexity": "polynomial; O(n^2*delta+n*M) field operations here",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_loop_steps // 8,
        "field_multiplications": reference_field_multiplications // 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
    }

    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6 and all_failed and reference_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density": guess_fraction,
        "demo_exact_solution_count": enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"])),
        "baseline_attack_wall_clock_sec": round(
            attack_seconds["random_restart_256_fixed_field_constants"] / 8, 6
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
    ladder_sizes = [DIFFICULTY[name]["n"] * DIFFICULTY[name]["delta"] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["field_degree"] > inst["field_degree"]
        and len(render(doubled)) > len(render(inst))
        and ladder_sizes == sorted(ladder_sizes)
        and len(set(ladder_sizes)) == len(ladder_sizes),
        "shipping_n": shipping["n"],
        "doubled_n": doubled_params["n"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_why,
        "candidate_space_bits_shipping": search_space(inst).bit_length(),
        "candidate_space_bits_doubled": search_space(doubled).bit_length(),
        "field_bits_shipping": inst["field_degree"],
        "field_bits_doubled": doubled["field_degree"],
    }

    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping)
        for transformed in _relabel_variants(original, seed ^ 0x5A5A):
            if canonical_key(original) == canonical_key(transformed):
                invariant_count += 1
            if verify(transformed, original["answer"])[0]:
                real_transform_count += 1
        unrelated_keys.append(canonical_key(original))
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == 140
        and real_transform_count == 140
        and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "real_transformations_verified": real_transform_count,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "point permutation",
            "global skew conjugation",
            "global Frobenius automorphism",
            "their composition",
        ],
    }

    encoded_answer = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(encoded_answer)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = sum(len(term) for term in inst["answer"])
    intended_ops = 2 * shipping["n"] - 1
    arms = {
        key: dict(G9_ORACLE_RESULTS[key]) for key in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": G9_ORACLE_RESULTS["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
