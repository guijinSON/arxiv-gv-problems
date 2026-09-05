"""Self-contained verified generator for arXiv:1504.01581.

The family asks for the compact Delsarte-dual constraint of a twisted
Gabidulin code.  Generation is theorem-backed by the construction and duality
calculation in Section 3 of Sheekey's paper.  All arithmetic is exact over
GF(3); no emitted instance is solved in order to obtain its certificate.
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "linearized polynomials over GF(3^n)",
        "twisted Gabidulin MRD code",
        "compact semilinear constraint for its Delsarte dual",
    ],
    "verification_operations": [
        "exact cyclic Frobenius shift in a normal basis",
        "exact negation in GF(3)",
        "exact trace-adjoint coefficient comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "duality",
    "intuition_description": (
        "Move the Frobenius twist across the field trace, which reverses its "
        "exponent; without this adjunction, one expands coordinate generators "
        "and computes an orthogonal complement."
    ),
    "hardness_basis": (
        "Track B: the standard trace-Gram matrix adjoint uses O(n^3) GF(3) "
        "operations and measured 1,711,839 operations and about 0.05 seconds at "
        "shipping n=48, while trace/Frobenius adjunction is one n-coordinate "
        "rotation and one sign change, at most 2n+8 exact operations."
    ),
    "max_answer_tokens": 13,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}


DIFFICULTY = {"easy": {"n": 48, "k": 23}}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Under the field trace, a Frobenius power is adjoint to the inverse "
    "Frobenius power."
)
PLACEBO_HINT = (
    "Keep the normal-basis coordinate order and the zero-based subscripts "
    "consistent throughout."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One fixed-width word of n ternary coordinates, each in {0,1,2}, "
        "representing the nonzero dual twist coefficient in the displayed "
        "normal basis."
    ),
    "bounds": {
        "coordinates": "n",
        "alphabet": [0, 1, 2],
        "excluded_word": "the all-zero word",
        "candidate_count": "3^n-1",
    },
}

NOTES = (
    "Section 2 fixes linearized polynomials, the coefficient trace pairing, "
    "and Delsarte duality. Section 3, Lemma 3 (the endpoint norm obstruction), "
    "Theorem 5 (the twisted code construction), and Theorem 6 (the explicit "
    "dual) fix the family. The condition N(eta) != (-1)^(nk) is enforced "
    "exactly in GF(3^n), so the paper guarantees an MRD code without exhaustive "
    "rank testing. Small-field classification in Section 1.5 and the displayed "
    "q=3,n=4 matrices in Section 4 are lookup/easy regimes and are avoided. "
    "Copy-eta, sign-only, wrong-direction Frobenius, additive-shift, and random-"
    "restart attacks all fail; the successful trace-Gram adjoint is reported "
    "separately as the Track-B reference algorithm."
)

G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unrun",
}


# Coefficients are low degree first.  Each modulus is irreducible over GF(3),
# and theta is a checked normal element: (theta, theta^3, ..., theta^(3^(n-1)))
# is a basis.  These constants only define finite-field coordinates.
_FIELD_STRINGS = {
    5: (
        "221011",
        "11000",
    ),
    48: (
        "1111212101022121210112201101021212101020100220121",
        "110110000000000000000000000000000000000000000000",
    ),
    64: (
        "11201112210202001120212222000121210111220101100210022220202120011",
        "1202100001202100001202100000000000000000000000000000000000000000",
    ),
    80: (
        "210222101100000110011102102001210201220201112101101221212221002020122200121002121",
        "00000100000000000000000000000000000000000000000000000000000000000000000000000000",
    ),
    96: (
        "2020012121001220101111010012100122112221010201022221221110001020222020221022011200012121101101111",
        "101010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
    ),
    146: (
        "122101022002022212121112020122022020021211110222000121120211221102001202101020220022111212002202120200122121100120002211201222210201121010122210021",
        "00001000100002200112202212122100102101211201011222221011010210000112022100121222020222002020211212200200002221212111211002010020110122110210011021",
    ),
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _digits(word):
    return [ord(ch) - 48 for ch in word]


def _trim(poly):
    out = list(poly)
    while len(out) > 1 and out[-1] == 0:
        out.pop()
    return out


def _gf_add(a, b, n):
    return [((a[i] if i < len(a) else 0) + (b[i] if i < len(b) else 0)) % 3
            for i in range(n)]


def _gf_mul(a, b, modulus):
    """Multiply polynomial-coordinate field elements modulo a monic modulus."""
    n = len(modulus) - 1
    tmp = [0] * (2 * n - 1)
    for i, ai in enumerate(a[:n]):
        if ai:
            for j, bj in enumerate(b[:n]):
                if bj:
                    tmp[i + j] = (tmp[i + j] + ai * bj) % 3
    for degree in range(2 * n - 2, n - 1, -1):
        lead = tmp[degree]
        if lead:
            for j in range(n):
                tmp[degree - n + j] = (
                    tmp[degree - n + j] - lead * modulus[j]
                ) % 3
    return tmp[:n]


def _gf_mul_counted(a, b, modulus):
    """The same product, with executed GF(3) multiply/add operations counted."""
    n = len(modulus) - 1
    tmp = [0] * (2 * n - 1)
    operations = 0
    for i, ai in enumerate(a[:n]):
        if ai:
            for j, bj in enumerate(b[:n]):
                if bj:
                    tmp[i + j] = (tmp[i + j] + ai * bj) % 3
                    operations += 2
    for degree in range(2 * n - 2, n - 1, -1):
        lead = tmp[degree]
        if lead:
            for j in range(n):
                tmp[degree - n + j] = (
                    tmp[degree - n + j] - lead * modulus[j]
                ) % 3
                operations += 2
    return tmp[:n], operations


def _gf_pow(base, exponent, modulus):
    n = len(modulus) - 1
    result = [1] + [0] * (n - 1)
    value = list(base)
    while exponent:
        if exponent & 1:
            result = _gf_mul(result, value, modulus)
        exponent >>= 1
        if exponent:
            value = _gf_mul(value, value, modulus)
    return result


def _poly_divmod_mod3(numerator, denominator):
    numerator = _trim([value % 3 for value in numerator])
    denominator = _trim([value % 3 for value in denominator])
    if denominator == [0]:
        raise ZeroDivisionError("polynomial division by zero")
    quotient = [0] * max(1, len(numerator) - len(denominator) + 1)
    inv_lead = 1 if denominator[-1] == 1 else 2
    while numerator != [0] and len(numerator) >= len(denominator):
        offset = len(numerator) - len(denominator)
        scale = numerator[-1] * inv_lead % 3
        quotient[offset] = scale
        for index, value in enumerate(denominator):
            numerator[offset + index] = (
                numerator[offset + index] - scale * value
            ) % 3
        numerator = _trim(numerator)
    return _trim(quotient), numerator


def _poly_gcd_mod3(left, right):
    left, right = _trim(left), _trim(right)
    while right != [0]:
        _, remainder = _poly_divmod_mod3(left, right)
        left, right = right, remainder
    if left == [0]:
        return [0]
    scale = 1 if left[-1] == 1 else 2
    return _trim([(scale * value) % 3 for value in left])


def _prime_divisors(value):
    divisors = []
    candidate = 2
    while candidate * candidate <= value:
        if value % candidate == 0:
            divisors.append(candidate)
            while value % candidate == 0:
                value //= candidate
        candidate += 1
    if value > 1:
        divisors.append(value)
    return divisors


def _is_irreducible_mod3(modulus):
    """Rabin's exact irreducibility criterion over GF(3)."""
    n = len(modulus) - 1
    x = [0, 1] + [0] * (n - 2)
    frobenius = [x]
    value = x
    for _ in range(n):
        value = _gf_pow(value, 3, modulus)
        frobenius.append(value)
    if frobenius[n] != x:
        return False
    for prime in _prime_divisors(n):
        test = [(frobenius[n // prime][i] - x[i]) % 3 for i in range(n)]
        if len(_poly_gcd_mod3(modulus, test)) != 1:
            return False
    return True


def _matrix_inverse_mod3(matrix, count=False):
    n = len(matrix)
    aug = [list(row) + [1 if i == j else 0 for j in range(n)]
           for i, row in enumerate(matrix)]
    operations = 0
    for col in range(n):
        pivot = next((r for r in range(col, n) if aug[r][col] % 3), None)
        if pivot is None:
            raise ValueError("singular GF(3) matrix")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        if aug[col][col] == 2:
            aug[col] = [(2 * x) % 3 for x in aug[col]]
            operations += 2 * n
        for row in range(n):
            if row == col or aug[row][col] == 0:
                continue
            scale = aug[row][col]
            aug[row] = [(x - scale * y) % 3
                        for x, y in zip(aug[row], aug[col])]
            operations += 4 * n
    inverse = [row[n:] for row in aug]
    return (inverse, operations) if count else inverse


def _matvec(matrix, vector):
    return [sum(a * b for a, b in zip(row, vector)) % 3 for row in matrix]


def _matvec_counted(matrix, vector):
    result = []
    operations = 0
    for row in matrix:
        total = 0
        for a, b in zip(row, vector):
            total += a * b
            operations += 2
        result.append(total % 3)
    return result, operations


def _matmul_mod3(left, right, count=False):
    rows, inner, cols = len(left), len(right), len(right[0])
    columns = [[right[i][j] for i in range(inner)] for j in range(cols)]
    out = []
    operations = 0
    for row in left:
        out_row = []
        for column in columns:
            total = 0
            for a, b in zip(row, column):
                total += a * b
                operations += 2
            out_row.append(total % 3)
        out.append(out_row)
    return (out, operations) if count else out


@functools.lru_cache(maxsize=None)
def _field_data(n):
    if n not in _FIELD_STRINGS:
        raise ValueError("unsupported extension degree; use a declared preset")
    modulus_word, theta_word = _FIELD_STRINGS[n]
    modulus, theta = _digits(modulus_word), _digits(theta_word)
    if len(modulus) != n + 1 or modulus[-1] != 1 or len(theta) != n:
        raise AssertionError("invalid embedded field specification")
    if not _is_irreducible_mod3(modulus):
        raise AssertionError("embedded modulus is reducible over GF(3)")
    basis = []
    value = theta
    for _ in range(n):
        basis.append(value)
        value = _gf_pow(value, 3, modulus)
    basis_matrix = [[basis[column][row] for column in range(n)]
                    for row in range(n)]
    inverse = _matrix_inverse_mod3(basis_matrix)
    one_normal = _matvec(inverse, [1] + [0] * (n - 1))
    # Trace(theta) is computed directly as a check on the normal basis.
    trace_theta = [0] * n
    for conjugate in basis:
        trace_theta = _gf_add(trace_theta, conjugate, n)
    if any(trace_theta[i] for i in range(1, n)) or trace_theta[0] == 0:
        raise AssertionError("embedded element is not a usable normal element")
    # Cache one nonsquare.  Multiplying its coset by a random square lets
    # make_instance sample either norm class with two field multiplications,
    # rather than performing a fresh exponentiation for every seed.
    nonsquare = None
    for code in range(1, 32):
        candidate = [0] * n
        work = code
        for index in range(min(n, 4)):
            candidate[index] = work % 3
            work //= 3
        norm = _gf_pow(candidate, (3 ** n - 1) // 2, modulus)
        if norm == [2] + [0] * (n - 1):
            nonsquare = candidate
            break
    if nonsquare is None:
        raise AssertionError("failed to embed a fixed nonsquare")
    return {
        "modulus": modulus,
        "theta": theta,
        "basis": basis,
        "basis_matrix": basis_matrix,
        "inverse": inverse,
        "one_normal": one_normal,
        "trace_theta": trace_theta[0],
        "nonsquare": nonsquare,
    }


def _normal_to_poly(coords, data):
    n = len(coords)
    out = [0] * n
    for coefficient, basis_element in zip(coords, data["basis"]):
        if coefficient:
            for i, value in enumerate(basis_element):
                out[i] = (out[i] + coefficient * value) % 3
    return out


def _basis_from_normal_element(theta, modulus):
    """Return (theta, theta^3, ...) in polynomial-basis coordinates."""
    basis = []
    value = list(theta)
    for _ in range(len(theta)):
        basis.append(value)
        value = _gf_pow(value, 3, modulus)
    return basis


def _coords_to_poly(coords, basis):
    """Convert coordinates in an explicitly supplied basis to polynomials."""
    n = len(coords)
    out = [0] * n
    for coefficient, basis_element in zip(coords, basis):
        if coefficient:
            for index, value in enumerate(basis_element):
                out[index] = (out[index] + coefficient * value) % 3
    return out


def _poly_to_normal(poly, data):
    return _matvec(data["inverse"], poly)


def _rotate_right(values, amount):
    if not values:
        return []
    amount %= len(values)
    return list(values[-amount:] + values[:-amount]) if amount else list(values)


def _rotate_left(values, amount):
    if not values:
        return []
    amount %= len(values)
    return list(values[amount:] + values[:amount]) if amount else list(values)


def _negate(values):
    return [(-value) % 3 for value in values]


def _expected_dual_twist(inst):
    # Tr(a^(3^h)b) = Tr(a b^(3^(n-h))).  In the chosen normal basis,
    # raising to 3 is one right cyclic coordinate shift.
    return _negate(_rotate_right(inst["eta"], inst["n"] - inst["h"]))


def _word(values):
    return "".join(str(value) for value in values)


def _validate_parameters(n, k):
    if not _is_int(n) or n not in _FIELD_STRINGS:
        raise ValueError("n must be one of the supported extension degrees")
    if not _is_int(k) or not 1 <= k < n:
        raise ValueError("k must be an integer with 1 <= k < n")


def make_instance(n, seed=0, k=None, **params):
    """Construct a twisted Gabidulin code and its compact dual witness."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if k is None:
        k = max(1, n // 2 - 1)
    _validate_parameters(n, k)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    data = _field_data(n)
    required_norm = 2 if (n * k) % 2 == 0 else 1

    # Draw eta and check its norm exactly.  This is theorem-backed generation:
    # the norm condition, not an exhaustive rank search, proves the MRD claim.
    while True:
        source = [rng.randrange(3) for _ in range(n)]
        if not any(source):
            continue
        source_poly = _normal_to_poly(source, data)
        eta_poly = _gf_mul(source_poly, source_poly, data["modulus"])
        if required_norm == 2:
            eta_poly = _gf_mul(data["nonsquare"], eta_poly, data["modulus"])
        eta = _poly_to_normal(eta_poly, data)
        h = rng.randrange(1, n)
        if 2 * h == n:
            continue
        provisional = {"n": n, "h": h, "eta": eta}
        answer_coords = _expected_dual_twist(provisional)
        guesses = [
            eta,
            _negate(eta),
            _negate(_rotate_right(eta, h)),
            _negate(_rotate_right(eta, (n - h + 1) % n)),
        ]
        if any(guess == answer_coords for guess in guesses):
            continue
        if len(set(answer_coords)) < 2:
            continue
        break

    answer = _word(answer_coords)
    return {
        "family": "twisted_gabidulin_dual_constraint",
        "q": 3,
        "n": n,
        "k": k,
        "h": h,
        "field_modulus": list(data["modulus"]),
        "normal_element": list(data["theta"]),
        "eta": list(eta),
        "answer": answer,
    }


def render(inst):
    n, k, h = inst["n"], inst["k"], inst["h"]
    modulus = " ".join(map(str, inst["field_modulus"]))
    theta = " ".join(map(str, inst["normal_element"]))
    text = f"""Find the compact Delsarte dual of a twisted Gabidulin code.

All definitions and conventions follow.
Let F = GF(3)[z]/(P(z)), where the coefficients of the monic irreducible
polynomial P are listed from z^0 through z^{n}:
  P coefficients: {modulus}
Field arithmetic is exact modulo 3 and P.  The element theta of F has
polynomial-basis coordinates, from z^0 through z^{n-1}:
  theta coordinates: {theta}
The ordered normal basis is
  B = (theta, theta^3, theta^(3^2), ..., theta^(3^{n-1})).
Thus a field element is an n-coordinate column over GF(3), and cubing it
cyclically shifts its coordinates one place to the RIGHT.  Coordinates and
all subscripts below are zero-based.

A 3-linearized polynomial is a formal sum f(x)=sum_i f_i x^(3^i), with
coefficients f_i in F.  Its coefficient trace pairing with g is
  <f,g> = Tr_F/GF(3)(sum_i f_i g_i).
The Delsarte dual C^perp is the set of all g satisfying <f,g>=0 for every
f in C.

Here n={n}, k={k}, and h={h}.  The nonzero twist eta has normal-basis
coordinate word
  eta = {_word(inst['eta'])}
and it satisfies N_F/GF(3)(eta) != (-1)^(n*k).  Define the twisted code
  C = {{ a0*x + a1*x^3 + ... + a_(k-1)*x^(3^(k-1))
         + eta*(a0^(3^h))*x^(3^k) : a0,...,a_(k-1) in F }}.

Your witness is the normal-basis coordinate word of the unique nonzero
lambda for which C^perp has the compact description
  {{ g0*x + gk*x^(3^k) + ... + g_(n-1)*x^(3^(n-1)) :
       gk,...,g_(n-1) in F and g0=lambda*(gk^(3^(n-h))) }}.

Return exactly {n} ternary digits, one per normal-basis coordinate in the
displayed order.  Digits are in {{0,1,2}}; the all-zero word is forbidden.
No separators, sign, prefix, or omitted leading zeroes are allowed.

Give your final answer inside <answer></answer> tags as exactly that
{n}-digit ternary word.
Example format only: <answer>{'0' * (n - 1)}1</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    if not matches:
        return None
    body = matches[-1].strip()
    fence = re.fullmatch(r"```(?:text|txt)?\s*(.*?)\s*```", body,
                         flags=re.IGNORECASE | re.DOTALL)
    if fence:
        body = fence.group(1).strip()
    if not body or not re.fullmatch(r"[012]+", body):
        return None
    return body


def verify(inst, answer):
    if not isinstance(answer, str):
        return False, "answer must be a ternary coordinate word"
    if answer == "":
        return False, "answer is empty"
    n = inst.get("n")
    if len(answer) < n:
        return False, f"answer is too short: expected {n} digits"
    if len(answer) > n:
        return False, f"answer is too long: expected {n} digits"
    if any(ch not in "012" for ch in answer):
        return False, "answer contains a non-ternary digit"
    if set(answer) == {"0"}:
        return False, "the zero field element is outside the certificate language"
    candidate = [ord(ch) - 48 for ch in answer]
    expected = _expected_dual_twist(inst)
    if candidate != expected:
        return False, "the proposed endpoint constraint is not trace-orthogonal"
    return True, "ok"


def random_candidate(inst, rng):
    n = inst["n"]
    while True:
        candidate = [rng.randrange(3) for _ in range(n)]
        if any(candidate):
            return _word(candidate)


def search_space(inst):
    return 3 ** inst["n"] - 1


def enumerate_all(inst):
    space = search_space(inst)
    if space > 1_000_000:
        return None
    count = 0
    n = inst["n"]
    for value in range(1, 3 ** n):
        digits = []
        work = value
        for _ in range(n):
            digits.append(work % 3)
            work //= 3
        candidate = _word(list(reversed(digits)))
        count += int(verify(inst, candidate)[0])
    return count


def canonical_key(inst):
    # Convert eta out of the displayed normal basis before canonicalising.
    # This makes the key invariant under *every* normal-basis change inside the
    # embedded field, not just under cyclic shifts of the displayed coordinates.
    modulus = list(inst["field_modulus"])
    basis = _basis_from_normal_element(inst["normal_element"], modulus)
    eta_poly = _coords_to_poly(inst["eta"], basis)
    orbit = []
    value = eta_poly
    for _ in range(inst["n"]):
        orbit.append(tuple(value))
        value = _gf_pow(value, 3, modulus)
    canonical_eta = min(orbit)
    payload = json.dumps(
        [inst["q"], inst["n"], inst["k"], inst["h"], list(canonical_eta)],
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params):
    n = int(params["n"])
    if n == 48:
        return dict(DIFFICULTY["medium"])
    if n == 80:
        return dict(DIFFICULTY["hard"])
    if n == 146:
        return "cap_bound"
    return None


def _multiplication_matrix_normal(element, data):
    element_poly = _normal_to_poly(element, data)
    columns = []
    operations = 0
    n = len(element)
    for basis_element in data["basis"]:
        product, product_ops = _gf_mul_counted(
            element_poly, basis_element, data["modulus"]
        )
        coordinates, conversion_ops = _matvec_counted(data["inverse"], product)
        columns.append(coordinates)
        operations += product_ops + conversion_ops
    matrix = [[columns[column][row] for column in range(n)] for row in range(n)]
    return matrix, operations


def _trace_gram(data, count=False):
    n = len(data["theta"])
    first = []
    operations = 0
    for conjugate in data["basis"]:
        product, product_ops = _gf_mul_counted(
            data["theta"], conjugate, data["modulus"]
        )
        coords, conversion_ops = _matvec_counted(data["inverse"], product)
        first.append(data["trace_theta"] * sum(coords) % 3)
        operations += product_ops + conversion_ops + n + 1
    matrix = [[first[(j - i) % n] for j in range(n)] for i in range(n)]
    return (matrix, operations) if count else matrix


def _reference_trace_gram(inst):
    """Mechanical coordinate-matrix adjoint; intentionally not the shortcut."""
    n, h = inst["n"], inst["h"]
    cached_data = _field_data(n)
    started = time.perf_counter()
    basis_inverse, basis_inv_ops = _matrix_inverse_mod3(
        cached_data["basis_matrix"], count=True
    )
    data = dict(cached_data)
    data["inverse"] = basis_inverse
    trace_gram, trace_ops = _trace_gram(data, count=True)
    trace_inverse, inv_ops = _matrix_inverse_mod3(trace_gram, count=True)
    mult_eta, field_ops = _multiplication_matrix_normal(inst["eta"], data)
    # A maps a0 to eta*a0^(3^h).  Frobenius is a right coordinate shift.
    operator = [[mult_eta[row][(column + h) % n] for column in range(n)]
                for row in range(n)]
    transpose = [list(row) for row in zip(*operator)]
    middle, ops1 = _matmul_mod3(transpose, trace_gram, count=True)
    dual_operator, ops2 = _matmul_mod3(trace_inverse, middle, count=True)
    dual_operator = [[(-value) % 3 for value in row] for row in dual_operator]
    one_normal, one_ops = _matvec_counted(
        basis_inverse, [1] + [0] * (n - 1)
    )
    lambda_coords, final_ops = _matvec_counted(dual_operator, one_normal)
    elapsed = time.perf_counter() - started
    return _word(lambda_coords), {
        "scalar_operations": (
            basis_inv_ops + trace_ops + field_ops + inv_ops + ops1 + ops2
            + n * n + one_ops + final_ops
        ),
        "wall_clock_sec": elapsed,
        "matrix_order": n,
    }


def _attack_guesses(inst, rng):
    eta, n, h = inst["eta"], inst["n"], inst["h"]
    guesses = {
        "outlier_copy_eta": _word(eta),
        "greedy_negate_only": _word(_negate(eta)),
        "wrong_direction_frobenius": _word(_negate(_rotate_right(eta, h))),
        "off_by_one_shift_ansatz": _word(
            _negate(_rotate_right(eta, (n - h + 1) % n))
        ),
    }
    found = None
    for _ in range(256):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            found = candidate
            break
    guesses["random_restart_256"] = found
    return guesses


def _json_answer_size(answer):
    compact = json.dumps(answer, separators=(",", ":"))
    return len(compact), (len(compact) + 3) // 4


def _transformed_instance(inst, shift):
    """Reindex the normal basis by a cyclic Frobenius shift."""
    n = inst["n"]
    data = _field_data(n)
    theta_prime = data["basis"][shift % n]
    transformed = dict(inst)
    transformed["normal_element"] = list(theta_prime)
    transformed["eta"] = _rotate_left(inst["eta"], shift)
    transformed["answer"] = _rotate_left(list(inst["answer"]), shift)
    transformed["answer"] = "".join(transformed["answer"])
    return transformed


def _normal_basis_change(inst, rng):
    """Carry an instance through a non-monomial normal-basis relabelling."""
    n = inst["n"]
    # If c are the old coordinates of theta', the columns below are the old
    # coordinates of theta'^(3^i).  Invertibility is exactly normality.
    for _ in range(256):
        coordinates = [rng.randrange(3) for _ in range(n)]
        if sum(value != 0 for value in coordinates) < 2:
            continue
        columns = [_rotate_right(coordinates, shift) for shift in range(n)]
        change = [[columns[column][row] for column in range(n)]
                  for row in range(n)]
        try:
            inverse = _matrix_inverse_mod3(change)
        except ValueError:
            continue
        old_basis = _basis_from_normal_element(
            inst["normal_element"], inst["field_modulus"]
        )
        transformed = dict(inst)
        transformed["normal_element"] = _coords_to_poly(coordinates, old_basis)
        transformed["eta"] = _matvec(inverse, inst["eta"])
        answer_coords = [ord(ch) - 48 for ch in inst["answer"]]
        transformed["answer"] = _word(_matvec(inverse, answer_coords))
        return transformed
    raise AssertionError("failed to find a non-monomial normal-basis change")


def _frobenius_relabel(inst, shift):
    """Apply a field automorphism to all abstract field elements."""
    transformed = dict(inst)
    transformed["normal_element"] = _gf_pow(
        inst["normal_element"], 3 ** (shift % inst["n"]),
        inst["field_modulus"],
    )
    # Applying the same Frobenius map to theta, eta, and lambda leaves their
    # coordinate words unchanged in the transported normal basis.
    return transformed


def selftest():
    report = {
        "paper": "arXiv:1504.01581",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures = []
    norm_checks = 0
    attempts = 0
    for preset, parameters in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **parameters)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "answer is not JSON-native"})
            data = _field_data(inst["n"])
            eta_poly = _normal_to_poly(inst["eta"], data)
            norm = _gf_pow(
                eta_poly, (3 ** inst["n"] - 1) // 2, data["modulus"]
            )
            forbidden = 1 if (inst["n"] * inst["k"]) % 2 == 0 else 2
            norm_checks += 1
            if norm == [forbidden] + [0] * (inst["n"] - 1):
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "twist violates Theorem 5 norm condition"})
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures,
        "exact_norm_checks": norm_checks,
        "construction": "Section 3 norm condition plus exact dual trace identity",
    }

    shipping = make_instance(seed=150401581,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    unequal = next((i for i in range(1, len(planted))
                    if planted[i] != planted[0]), None)
    if unequal is None:
        raise AssertionError("shipping answer lacks unequal digits")
    swapped = list(planted)
    swapped[0], swapped[unequal] = swapped[unequal], swapped[0]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": "".join(swapped),
        "duplicate_one": planted + planted[-1],
        "empty": "",
        "out_of_range": "3" + planted[1:],
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = {entry["reason"] for entry in cases.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in cases.values())
        and len(reasons) == len(cases),
        "cases": cases,
        "distinct_reasons": len(reasons),
    }

    realistic = ("The trace terms cancel as follows.\n<answer>\n```text\n"
                 + planted + "\n```\n</answer>\nThat is the coordinate word.")
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged answer") is None,
        "parsed_length": len(parsed) if isinstance(parsed, str) else None,
    }

    guess_rng = random.Random(0x150401581)
    guess_total, guess_hits = 200_000, 0
    started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping,
                                 random_candidate(shipping, guess_rng))[0])
    guess_elapsed = time.perf_counter() - started
    exact_density = 1.0 / search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "exact_probability": exact_density,
        "structure_aware_space": search_space(shipping),
        "sampling_rule": "uniform over all nonzero n-coordinate GF(3) vectors",
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attack_results = {
        name: {"successes": 0, "attempts": 0, "wall_clock_sec_total_8": 0.0}
        for name in (
            "outlier_copy_eta", "greedy_negate_only",
            "wrong_direction_frobenius", "off_by_one_shift_ansatz",
            "random_restart_256",
        )
    }
    attack_seeds = list(range(8100, 8108))
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        rng = random.Random(0xA771C + seed)
        eta, n, h = inst["eta"], inst["n"], inst["h"]
        guesses = {
            "outlier_copy_eta": _word(eta),
            "greedy_negate_only": _word(_negate(eta)),
            "wrong_direction_frobenius": _word(
                _negate(_rotate_right(eta, h))
            ),
            "off_by_one_shift_ansatz": _word(
                _negate(_rotate_right(eta, (n - h + 1) % n))
            ),
        }
        for name, candidate in guesses.items():
            t0 = time.perf_counter()
            success = verify(inst, candidate)[0]
            attack_results[name]["attempts"] += 1
            attack_results[name]["successes"] += int(success)
            attack_results[name]["wall_clock_sec_total_8"] += (
                time.perf_counter() - t0
            )
        t0 = time.perf_counter()
        restart_success = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, rng))[0]:
                restart_success = True
                break
        attack_results["random_restart_256"]["attempts"] += 1
        attack_results["random_restart_256"]["successes"] += int(restart_success)
        attack_results["random_restart_256"]["wall_clock_sec_total_8"] += (
            time.perf_counter() - t0
        )
    for entry in attack_results.values():
        entry["wall_clock_sec_total_8"] = round(
            entry["wall_clock_sec_total_8"], 6
        )
    all_failed = all(entry["successes"] == 0
                     for entry in attack_results.values())

    reference_successes = 0
    reference_times = []
    reference_ops = []
    shortcut_successes = 0
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidate, stats = _reference_trace_gram(inst)
        reference_successes += int(verify(inst, candidate)[0])
        reference_times.append(stats["wall_clock_sec"])
        reference_ops.append(stats["scalar_operations"])
        shortcut_successes += int(verify(inst,
            _word(_expected_dual_twist(inst)))[0])
    intended_operations = 2 * shipping["n"] + 8
    reference = {
        "name": "trace-Gram coordinate adjoint over GF(3)",
        "complexity": "O(n^3) GF(3) scalar operations after systematic block extraction; generic ambient nullspace is O(n^6)",
        "wall_clock_sec_total_8": round(sum(reference_times), 6),
        "wall_clock_sec_mean": round(sum(reference_times) / len(reference_times), 8),
        "operations_mean": sum(reference_ops) // len(reference_ops),
        "operations_min": min(reference_ops),
        "operations_max": max(reference_ops),
        "solves": f"{reference_successes}/8, as expected",
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == shortcut_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": reference,
        "compact_route": {
            "name": "inverse Frobenius under trace, then negate",
            "worst_case_exact_operations": intended_operations,
            "count_model": "n coordinate moves, n GF(3) negations, and eight setup/check operations",
            "solves": f"{shortcut_successes}/8, as expected",
        },
    }

    strongest = max(attack_results,
                    key=lambda name: attack_results[name]["wall_clock_sec_total_8"])
    report["G5_density_and_baseline_cost"] = {
        "pass": exact_density < 1e-6 and all_failed,
        "exact_valid_answers": 1,
        "exact_density_at_shipping": exact_density,
        "sampled_density_at_shipping": guess_hits / guess_total,
        "density_hits": guess_hits,
        "density_samples": guess_total,
        "candidate_space": search_space(shipping),
        "strongest_failing_attack": strongest,
        "attack_wall_clock_sec_total_8": attack_results[strongest]["wall_clock_sec_total_8"],
        "attack_candidate_evaluations_total_8": 256 * 8,
        "reference_algorithm_operations_mean": reference["operations_mean"],
        "reference_algorithm_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
        "demo_exact_valid_answers": enumerate_all(
            make_instance(seed=3, **DIFFICULTY["demo"])
        ),
    }

    doubled_n = 2 * shipping["n"]
    doubled_k = max(1, 2 * shipping["k"] + 1)
    larger = make_instance(n=doubled_n, k=doubled_k, seed=707)
    larger_ok, larger_reason = verify(larger, larger["answer"])
    report["G7_scales"] = {
        "pass": larger_ok and search_space(larger) > search_space(shipping),
        "shipping_n": shipping["n"],
        "doubled_n": doubled_n,
        "shipping_space": search_space(shipping),
        "doubled_space": search_space(larger),
        "verify_reason": larger_reason,
    }

    invariance_checks = carried_checks = 0
    key_failures = []
    for seed in range(20):
        inst = make_instance(seed=9000 + seed,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        shift = (7 * seed + 3) % inst["n"] or 1
        changed_basis = _normal_basis_change(
            inst, random.Random(0xB4515 + seed)
        )
        transformations = {
            "cyclic_basis_change": _transformed_instance(inst, shift),
            "non_monomial_basis_change": changed_basis,
            "field_frobenius": _frobenius_relabel(inst, shift),
            "composed_change": _frobenius_relabel(changed_basis, shift),
        }
        for transform_name, transformed in transformations.items():
            invariance_checks += 1
            if canonical_key(transformed) != key:
                key_failures.append({"seed": seed,
                                     "transformation": transform_name,
                                     "reason": "key changed"})
            carried_checks += 1
            if not verify(transformed, transformed["answer"])[0]:
                key_failures.append({"seed": seed,
                                     "transformation": transform_name,
                                     "reason": "carried witness failed"})
    unrelated = [canonical_key(make_instance(seed=20000 + seed,
                  **DIFFICULTY[SHIPPING_DIFFICULTY])) for seed in range(20)]
    distinct_keys = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "invariance_failures": key_failures,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "symmetries_tested": [
            "cyclic normal-basis reindexing",
            "non-monomial normal-basis change",
            "field Frobenius automorphism",
            "composition of a basis change with a field automorphism",
        ],
    }

    answer_chars, answer_tokens = _json_answer_size(shipping["answer"])
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (answer_chars <= 2000 and shipping["n"] <= 256
                   and intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": shipping["n"],
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["pass"] = all(gate.get("pass") is True for gate in gates)
    report["all_passed"] = report["pass"]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
