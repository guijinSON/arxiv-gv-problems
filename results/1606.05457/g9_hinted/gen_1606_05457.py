"""Exact DHDP transfer-certificate generator for arXiv:1606.05457.

The paper works in the noncommutative ring E_p^(m).  If

    A1 = sum_i u_i M^i,   A2 = sum_j v_j M^j,

then P=A1 X A2 has the executable certificate

    P = sum_{i,j} lambda_ij M^i X M^j,

where lambda_ij=u_i*v_j.  Instances below are generated from u and v, never
solved after construction.  The public question asks for any lambda satisfying
the displayed identity, not necessarily the planted one.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import os
import random
import re
import statistics
import sys
import time
from collections import Counter


sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)
try:  # E_p^(m) has mixed row moduli, so its arithmetic remains local below.
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - the module is standard-library-only.
    exact_matrices = rationals = None


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "Reduce the three matrices modulo p: the diagonal of M is a permuted roots-of-unity grid, so factor the ratios P[i][j]/X[i][j], inverse-NTT the two evaluation vectors, and take their outer product."
)
PLACEBO_HINT: str = (
    "Keep every residue in its stated row modulus: the indexing conventions and exact modular reductions both matter when assembling the requested coefficient matrix."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_discrete",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "elements of the noncommutative ring E_p^(m)",
        "powers of a public ring element",
        "a polynomial two-sided decomposition P=A1 X A2",
    ],
    "verification_operations": [
        "exact integer reduction modulo the row-dependent prime power",
        "exact E_p^(m) matrix multiplication",
        "exact coefficient expansion and matrix comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Reduce the native ring identity modulo p, recognize a rank-one table "
        "of polynomial evaluations on roots of unity, and invert that transform; "
        "without this change of variables one solves a prime-power modular system."
    ),
    "hardness_basis": (
        "Track B: the pseudo-E_p^(m) coefficient-matching attack of Khathuria, "
        "Micheli and Weger (Theorem 15 and Algorithm 1, arXiv:1810.02964) solves "
        "an m^2 by m^2 system in O(m^6) Z/p^mZ operations; the measured shipping "
        "cost and the <=300-operation roots-of-unity route are recorded by selftest()."
    ),
    "max_answer_tokens": 330,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"]
    + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "easy": {"n": 8, "p_bits": 17},
}
SHIPPING_DIFFICULTY: str = "easy"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "An n by n JSON matrix Lambda. Every entry is an integer in "
        "0 <= lambda_ij < q=p^n, and validity is the exact E_p^(n) identity "
        "P=sum_{i,j=0}^{n-1} lambda_ij M^i X M^j."
    ),
    "bounds": {
        "shipping_rows": 8,
        "shipping_columns": 8,
        "shipping_atomic_elements": 64,
        "maximum_shipping_coefficient_bits": 232,
    },
}

NOTES: str = (
    "Section 2 fixes E_p^(m), its row-dependent arithmetic, and its center. "
    "Section 4, equation (6), defines H(M) as central-coefficient polynomials "
    "in M; Protocol 1 and the DHDP definition fix the two-sided decomposition "
    "object, while Theorem 4 identifies the DHDP/EGDP cryptanalytic target. "
    "Section 3's theorem and Corollary 1 expose an easy central-SAP ratio test, "
    "and Section 4 exposes attacks using invertible elements, so neither route "
    "is used as a hardness claim. More decisively, Khathuria--Micheli--Weger, "
    "arXiv:1810.02964, Theorem 15 and Algorithm 1, give a polynomial O(m^6) "
    "linear-system attack on this exact protocol; Track A would therefore be "
    "false. The generator uses the paper's native matrices and inverse-plants "
    "polynomial factors. Random higher p-adic digits defeat raw-entry outliers, "
    "dense factor coefficients defeat sparse/greedy and affine ansatzes, and a "
    "large exact coefficient space defeats random restart. The disclosed Track B "
    "shortcut is reduction modulo p followed by two inverse NTTs."
)


# Updated only from transcripts written by scripts/harden.py.  A pending value
# deliberately makes G9 fail until the external evidence exists.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "pending",
}


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_power_of_two(value: int) -> bool:
    return value >= 2 and value & (value - 1) == 0


def _is_prime_64(value: int) -> bool:
    """Deterministic Miller--Rabin for all 64-bit parameters used here."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value % prime == 0:
            return value == prime
    d = value - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1
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


def _next_ntt_prime(n: int, bits: int) -> int:
    if bits < 2 or bits > 61:
        raise ValueError("p_bits must lie in [2,61]")
    start = 1 << (bits - 1)
    candidate = start + ((1 - start) % n)
    if candidate < 3:
        candidate += n
    while not _is_prime_64(candidate):
        candidate += n
        if candidate >= 1 << bits:
            raise ValueError("no suitable prime in the requested bit interval")
    return candidate


def _primitive_root_of_order(n: int, p: int) -> int:
    if (p - 1) % n:
        raise ValueError("n must divide p-1")
    for base in range(2, min(p, 100_000)):
        omega = pow(base, (p - 1) // n, p)
        if pow(omega, n, p) == 1 and pow(omega, n // 2, p) != 1:
            return omega
    raise ValueError("could not find an n-th primitive root")


def _zero(n: int):
    return [[0] * n for _ in range(n)]


def _identity(n: int):
    return [[int(i == j) for j in range(n)] for i in range(n)]


def _mat_add(a, b, p: int, n: int):
    return [
        [(a[i][j] + b[i][j]) % (p ** (i + 1)) for j in range(n)]
        for i in range(n)
    ]


def _scalar_mul(value: int, a, p: int, n: int):
    return [
        [(value * a[i][j]) % (p ** (i + 1)) for j in range(n)]
        for i in range(n)
    ]


def _mat_mul(a, b, p: int, n: int):
    out = _zero(n)
    for i in range(n):
        modulus = p ** (i + 1)
        for j in range(n):
            out[i][j] = sum(a[i][k] * b[k][j] for k in range(n)) % modulus
    return out


def _powers(matrix, p: int, n: int):
    result = [_identity(n)]
    for _ in range(1, n):
        result.append(_mat_mul(result[-1], matrix, p, n))
    return result


def _poly_matrix(coefficients, powers, p: int, n: int):
    out = _zero(n)
    for coefficient, power in zip(coefficients, powers):
        if coefficient:
            out = _mat_add(out, _scalar_mul(coefficient, power, p, n), p, n)
    return out


def _valid_ring_matrix(matrix, p: int, n: int) -> bool:
    if not isinstance(matrix, list) or len(matrix) != n:
        return False
    for i, row in enumerate(matrix):
        if not isinstance(row, list) or len(row) != n:
            return False
        modulus = p ** (i + 1)
        for j, value in enumerate(row):
            if not _is_int(value) or not 0 <= value < modulus:
                return False
            if i > j and value % (p ** (i - j)):
                return False
    return True


def _poly_eval(coefficients, x: int, p: int) -> int:
    value = 0
    for coefficient in reversed(coefficients):
        value = (value * x + coefficient) % p
    return value


def _sample_public_matrices(rng: random.Random, p: int, n: int, roots):
    residues = list(roots)
    rng.shuffle(residues)
    m = _zero(n)
    x = _zero(n)
    for i in range(n):
        modulus = p ** (i + 1)
        for j in range(n):
            lower_power = max(0, i - j)
            if i == j:
                m[i][j] = residues[i] + p * rng.randrange(modulus // p)
            else:
                base = p ** max(1, lower_power)
                m[i][j] = base * rng.randrange(modulus // base)
            if i <= j:
                x[i][j] = rng.randrange(1, p) + p * rng.randrange(modulus // p)
            else:
                base = p ** lower_power
                x[i][j] = base * rng.randrange(p ** (j + 1))
    return m, x


def _sample_dense_factors(rng: random.Random, p: int, diagonal, n: int):
    """Dense coefficient vectors normalized by u[0]=1."""
    while True:
        u = [1] + [rng.randrange(1, p) for _ in range(n - 1)]
        v = [rng.randrange(1, p) for _ in range(n)]
        if _poly_eval(u, diagonal[0], p) == 0:
            continue
        if _poly_eval(v, diagonal[-1], p) == 0:
            continue
        return u, v


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate an exact E_p^(n) decomposition certificate."""
    n = int(n)
    if not _is_power_of_two(n):
        raise ValueError("n must be a power of two and at least 2")
    p_bits = int(params.get("p_bits", 17))
    p_value = params.get("p")
    p = int(p_value) if p_value is not None else _next_ntt_prime(n, p_bits)
    if not _is_prime_64(p) or (p - 1) % n:
        raise ValueError("p must be prime and congruent to 1 modulo n")

    rng = random.Random(seed)
    omega = _primitive_root_of_order(n, p)
    roots = [pow(omega, k, p) for k in range(n)]
    m, x = _sample_public_matrices(rng, p, n, roots)
    diagonal = [m[i][i] % p for i in range(n)]
    u, v = _sample_dense_factors(rng, p, diagonal, n)
    powers = _powers(m, p, n)
    a1 = _poly_matrix(u, powers, p, n)
    a2 = _poly_matrix(v, powers, p, n)
    target = _mat_mul(_mat_mul(a1, x, p, n), a2, p, n)
    q = p ** n
    answer = [[u[i] * v[j] % q for j in range(n)] for i in range(n)]
    return {
        "n": n,
        "p": p,
        "q": q,
        "omega": omega,
        "M": m,
        "X": x,
        "P": target,
        "answer": answer,
    }


def _matrix_lines(name: str, matrix) -> str:
    lines = [name + " = ["]
    lines.extend("  " + json.dumps(row, separators=(",", ":")) for row in matrix)
    lines.append("]")
    return "\n".join(lines)


def render(inst) -> str:
    """Render a complete native E_p^(n) coefficient-certificate problem."""
    n = inst["n"]
    p = inst["p"]
    q = inst["q"]
    statement = f"""Find an exact two-sided polynomial-decomposition certificate in E_p^(n).

Here n={n}, p={p} is prime, and q=p^n={q}. Indices i,j,k start at 0.

Definition of E_p^(n): an element is an n by n integer matrix A. Entry A[i][j]
is represented by its unique integer in 0 <= A[i][j] < p^(i+1). If i>j it
must additionally be divisible by p^(i-j). Addition reduces every entry in row
i modulo p^(i+1). Multiplication is

  (A B)[i][j] = sum(k=0..n-1, A[i][k]*B[k][j]) mod p^(i+1).

M^0 is the identity matrix and higher powers use this multiplication. An integer
lambda acts as the central scalar whose multiplication simply multiplies every
entry and applies that row's modulus.

The public primitive n-th root omega={inst['omega']} is supplied as instance data;
it satisfies omega^n = 1 (mod p), with no smaller positive power equal to 1.

Public matrices:
{_matrix_lines('M', inst['M'])}

{_matrix_lines('X', inst['X'])}

{_matrix_lines('P', inst['P'])}

Output one n by n coefficient matrix Lambda in row-major JSON syntax. Every
lambda[i][j] must be an integer in the inclusive/exclusive range 0 <= value < q.
It is accepted exactly when

  P = sum(i=0..n-1, j=0..n-1, lambda[i][j] * M^i * X * M^j)

in E_p^(n). Order matters, repetitions are not a separate notion, and any
Lambda satisfying the identity is valid; it need not equal a particular planted
certificate.

Give your final answer inside <answer></answer> tags, as a JSON matrix with
exactly n rows and n base-10 integer entries per row.
Format example for n=2: <answer>[[1,2],[3,4]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    """Parse the last tagged JSON answer, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def _linearized_sum(inst, coefficients):
    n, p = inst["n"], inst["p"]
    powers = _powers(inst["M"], p, n)
    left = [_mat_mul(power, inst["X"], p, n) for power in powers]
    total = _zero(n)
    for i in range(n):
        right_poly = _zero(n)
        for j in range(n):
            value = coefficients[i][j]
            if value:
                right_poly = _mat_add(
                    right_poly, _scalar_mul(value, powers[j], p, n), p, n
                )
        total = _mat_add(total, _mat_mul(left[i], right_poly, p, n), p, n)
    return total


def verify(inst, answer) -> tuple[bool, str]:
    """Verify shape, bounds, and the exact native ring identity."""
    n = inst.get("n")
    p = inst.get("p")
    q = inst.get("q")
    if not _is_int(n) or not _is_int(p) or not _is_int(q):
        return False, "instance parameters are malformed"
    if not isinstance(answer, list):
        return False, "answer must be a JSON matrix"
    if not answer:
        return False, "answer matrix must be nonempty"
    if len(answer) != n:
        return False, f"certificate must have exactly {n} rows"
    for i, row in enumerate(answer):
        if not isinstance(row, list):
            return False, f"row {i} must itself be a JSON list"
        if len(row) != n:
            return False, f"row {i} must have exactly {n} entries"
        for j, value in enumerate(row):
            if not _is_int(value):
                return False, f"coefficient ({i},{j}) must be an integer"
            if not 0 <= value < q:
                return False, f"coefficient ({i},{j}) is outside [0,q)"
    try:
        reconstructed = _linearized_sum(inst, answer)
    except Exception as exc:  # malformed instances fail closed.
        return False, f"exact ring arithmetic failed: {type(exc).__name__}"
    if reconstructed != inst.get("P"):
        return False, "coefficient identity does not equal the public target P"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniformly sample the fully constrained n by n residue certificate space."""
    n, q = inst["n"], inst["q"]
    return [[rng.randrange(q) for _ in range(n)] for _ in range(n)]


def search_space(inst) -> int | None:
    return inst["q"] ** (inst["n"] * inst["n"])


def enumerate_all(inst) -> int | None:
    space = search_space(inst)
    if space is None or space > 500_000:
        return None
    n, q = inst["n"], inst["q"]
    count = 0
    for flat in itertools.product(range(q), repeat=n * n):
        candidate = [list(flat[i * n : (i + 1) * n]) for i in range(n)]
        if verify(inst, candidate)[0]:
            count += 1
    return count


def _transform_scale(inst, scalar: int):
    """Central-unit rescaling X->cX, P->cP preserves every certificate."""
    out = copy.deepcopy(inst)
    p, n, q = inst["p"], inst["n"], inst["q"]
    scalar %= q
    if scalar % p == 0:
        raise ValueError("the scaling scalar must be a central unit")
    out["X"] = _scalar_mul(scalar, inst["X"], p, n)
    out["P"] = _scalar_mul(scalar, inst["P"], p, n)
    return out


def canonical_key(inst) -> str:
    """Normalize the declared central-unit rescaling symmetry, then hash data."""
    p, n, q = inst["p"], inst["n"], inst["q"]
    anchor = inst["X"][n - 1][n - 1]
    if math.gcd(anchor, p) != 1:
        raise ValueError("canonical normalization requires the unit X[n-1][n-1]")
    inverse = pow(anchor, -1, q)
    payload = {
        "family": "Epm-two-sided-transfer-certificate-v1",
        "n": n,
        "p": p,
        "M": inst["M"],
        "X": _scalar_mul(inverse, inst["X"], p, n),
        "P": _scalar_mul(inverse, inst["P"], p, n),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def _worst_answer_chars(n: int, p: int) -> int:
    # Planted coefficients are products of two nonzero residues below p.
    largest = (p - 1) * (p - 1)
    value = [[largest] * n for _ in range(n)]
    return len(json.dumps(value, separators=(",", ":")))


def escalate(params) -> dict | str | None:
    """Grow coefficient entropy at fixed answer length before reporting the cap."""
    out = dict(params)
    n = int(out["n"])
    bits = int(out.get("p_bits", 17))
    next_bits = bits + 4
    if next_bits <= 49:
        trial_p = _next_ntt_prime(n, next_bits)
        if _worst_answer_chars(n, trial_p) <= 2000:
            out["p_bits"] = next_bits
            return out
    return "cap_bound"


def _ntt(values, root: int, p: int, *, inverse: bool):
    """Radix-two NTT; return (transformed_values, counted field operations)."""
    a = [value % p for value in values]
    n = len(a)
    operations = 0
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    use_root = pow(root, -1, p) if inverse else root
    if inverse:
        operations += 1
    length = 2
    while length <= n:
        wlen = pow(use_root, n // length, p)
        operations += 1
        half = length // 2
        for start in range(0, n, length):
            w = 1
            for offset in range(half):
                u = a[start + offset]
                v = a[start + offset + half] * w % p
                a[start + offset] = (u + v) % p
                a[start + offset + half] = (u - v) % p
                w = w * wlen % p
                operations += 4  # multiply, add, subtract, twiddle update
        length *= 2
    if inverse:
        inv_n = pow(n, -1, p)
        operations += 1
        a = [value * inv_n % p for value in a]
        operations += n
    return a, operations


def _compact_ntt_certificate(inst):
    """The disclosed <=300-operation Track B route; never reads the answer."""
    n, p, q = inst["n"], inst["p"], inst["q"]
    omega = inst["omega"]
    root_to_index = {}
    value = 1
    operations = 0
    for k in range(n):
        root_to_index[value] = k
        value = value * omega % p
        operations += 1
    try:
        row_order = [root_to_index[inst["M"][i][i] % p] for i in range(n)]
    except KeyError as exc:
        raise ValueError("M diagonal is not the advertised roots-of-unity grid") from exc

    column = n - 1
    s_eval = [0] * n
    for i in range(n):
        denominator = inst["X"][i][column] % p
        s_eval[row_order[i]] = (
            inst["P"][i][column] % p * pow(denominator, -1, p) % p
        )
        operations += 2
    s_coeff, used = _ntt(s_eval, omega, p, inverse=True)
    operations += used
    v_at_column = s_coeff[0]
    if v_at_column == 0:
        raise ValueError("normalizing evaluation unexpectedly vanished")
    inverse_scale = pow(v_at_column, -1, p)
    operations += 1
    u = [coefficient * inverse_scale % p for coefficient in s_coeff]
    operations += n

    row = 0
    u_at_row = s_eval[row_order[row]] * inverse_scale % p
    operations += 1
    if u_at_row == 0:
        raise ValueError("row normalization unexpectedly vanished")
    v_eval = [0] * n
    for j in range(n):
        denominator = inst["X"][row][j] % p * u_at_row % p
        v_eval[row_order[j]] = (
            inst["P"][row][j] % p * pow(denominator, -1, p) % p
        )
        operations += 3
    v, used = _ntt(v_eval, omega, p, inverse=True)
    operations += used
    answer = [[u[i] * v[j] % q for j in range(n)] for i in range(n)]
    operations += n * n
    return answer, {
        "exact_operations": operations,
        "field_transforms": 2,
        "outer_product_entries": n * n,
    }


def _basis_orbit(inst):
    n, p = inst["n"], inst["p"]
    powers = _powers(inst["M"], p, n)
    left = [_mat_mul(power, inst["X"], p, n) for power in powers]
    return [
        _mat_mul(left[i], powers[j], p, n)
        for i in range(n)
        for j in range(n)
    ]


def _p_valuation(value: int, p: int, exponent: int) -> int:
    if value == 0:
        return exponent
    valuation = 0
    while value % p == 0:
        value //= p
        valuation += 1
    return valuation


def _smith_solve_prime_power(matrix, rhs, p: int, exponent: int):
    """Solve A x=b modulo p^exponent by exact Smith-style elimination."""
    modulus = p ** exponent
    a = [[value % modulus for value in row] for row in matrix]
    b = [value % modulus for value in rhs]
    rows = len(a)
    cols = len(a[0]) if rows else 0
    transform = [[int(i == j) for j in range(cols)] for i in range(cols)]
    pivot_valuations = []
    operations = 0
    k = 0
    while k < min(rows, cols):
        location = None
        best = exponent
        for i in range(k, rows):
            for j in range(k, cols):
                valuation = _p_valuation(a[i][j], p, exponent)
                if valuation < best:
                    best = valuation
                    location = (i, j)
                    if best == 0:
                        break
            if best == 0:
                break
        if location is None:
            break
        i, j = location
        a[k], a[i] = a[i], a[k]
        b[k], b[i] = b[i], b[k]
        if j != k:
            for row in a:
                row[k], row[j] = row[j], row[k]
            for row in transform:
                row[k], row[j] = row[j], row[k]

        prime_power = p ** best
        unit = a[k][k] // prime_power
        unit_inverse = pow(unit, -1, modulus)
        operations += 1
        a[k] = [value * unit_inverse % modulus for value in a[k]]
        b[k] = b[k] * unit_inverse % modulus
        operations += cols + 1

        for i in range(rows):
            if i == k or a[i][k] == 0:
                continue
            factor = a[i][k] // prime_power
            a[i] = [
                (value - factor * pivot) % modulus
                for value, pivot in zip(a[i], a[k])
            ]
            b[i] = (b[i] - factor * b[k]) % modulus
            operations += 2 * cols + 2

        for j in range(cols):
            if j == k or a[k][j] == 0:
                continue
            factor = a[k][j] // prime_power
            for i in range(rows):
                a[i][j] = (a[i][j] - factor * a[i][k]) % modulus
            for i in range(cols):
                transform[i][j] = (
                    transform[i][j] - factor * transform[i][k]
                ) % modulus
            operations += 2 * rows + 2 * cols
        pivot_valuations.append(best)
        k += 1

    y = [0] * cols
    for i, valuation in enumerate(pivot_valuations):
        prime_power = p ** valuation
        if b[i] % prime_power:
            raise ValueError("inconsistent prime-power linear system")
        y[i] = (b[i] // prime_power) % (p ** (exponent - valuation))
    for i in range(len(pivot_valuations), rows):
        if b[i] % modulus:
            raise ValueError("inconsistent zero row")
    solution = []
    for i in range(cols):
        value = 0
        for j in range(cols):
            value = (value + transform[i][j] * y[j]) % modulus
            operations += 2
        solution.append(value)
    return solution, {
        "exact_operations": operations,
        "pivot_valuations": pivot_valuations,
        "pivots": len(pivot_valuations),
    }


def _generic_reference_algorithm(inst):
    """Pseudo-E_p^(m) coefficient matching, independent of the plant."""
    start = time.perf_counter()
    n, p, q = inst["n"], inst["p"], inst["q"]
    basis = _basis_orbit(inst)
    matrix = []
    rhs = []
    for i in range(n):
        scale = p ** (n - i - 1)  # the delta isomorphism of arXiv:1810.02964
        for j in range(n):
            matrix.append([item[i][j] * scale % q for item in basis])
            rhs.append(inst["P"][i][j] * scale % q)
    flat, solve_stats = _smith_solve_prime_power(matrix, rhs, p, n)
    answer = [flat[i * n : (i + 1) * n] for i in range(n)]
    # Count the scalar multiply/adds in the orbit construction as well.
    matmul_ops = n * n * (2 * n - 1)
    orbit_multiplications = (n - 1) + n + n * n
    construction_ops = orbit_multiplications * matmul_ops + 2 * n ** 4
    elapsed = time.perf_counter() - start
    return answer, {
        "wall_clock_sec": elapsed,
        "exact_operations": solve_stats["exact_operations"] + construction_ops,
        "solver_operations": solve_stats["exact_operations"],
        "basis_operations": construction_ops,
        "pivot_valuations": solve_stats["pivot_valuations"],
        "pivots": solve_stats["pivots"],
    }


def _anchor_coefficients(inst, basis=None):
    if basis is None:
        basis = _basis_orbit(inst)
    n = inst["n"]
    return [item[n - 1][n - 1] for item in basis]


def _passes_anchor(inst, candidate, anchor_coefficients) -> bool:
    q = inst["q"]
    flat = [value for row in candidate for value in row]
    obtained = sum(a * b for a, b in zip(flat, anchor_coefficients)) % q
    return obtained == inst["P"][-1][-1]


def _attack_outlier_one_term(inst):
    basis = _basis_orbit(inst)
    p, q, n = inst["p"], inst["q"], inst["n"]
    scored = []
    for index, item in enumerate(basis):
        matches = sum(
            item[i][j] % p == inst["P"][i][j] % p
            for i in range(n)
            for j in range(i, n)
        )
        scored.append((matches, -index))
    index = -max(scored)[1]
    anchor = basis[index][-1][-1]
    coefficient = (
        inst["P"][-1][-1] * pow(anchor, -1, q) % q
        if math.gcd(anchor, p) == 1
        else 0
    )
    answer = _zero(n)
    answer[index // n][index % n] = coefficient
    return answer


def _attack_greedy_diagonal(inst):
    """Greedily match diagonal entries using only lambda_ii terms."""
    n, p, q = inst["n"], inst["p"], inst["q"]
    basis = _basis_orbit(inst)
    answer = _zero(n)
    residual = copy.deepcopy(inst["P"])
    for k in range(n):
        item = basis[k * n + k]
        modulus = p ** (k + 1)
        pivot = item[k][k] % modulus
        if math.gcd(pivot, p) == 1:
            value = residual[k][k] * pow(pivot, -1, modulus) % modulus
            answer[k][k] = value % q
            correction = _scalar_mul(value, item, p, n)
            residual = [
                [
                    (residual[i][j] - correction[i][j]) % (p ** (i + 1))
                    for j in range(n)
                ]
                for i in range(n)
            ]
    return answer


def _attack_random_restart(inst, rng: random.Random, restarts=256):
    anchors = _anchor_coefficients(inst)
    last = _zero(inst["n"])
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if _passes_anchor(inst, last, anchors) and verify(inst, last)[0]:
            return last
    return last


def _interpolate_affine(x0, y0, x1, y1, p: int):
    slope = (y1 - y0) * pow((x1 - x0) % p, -1, p) % p
    return [(y0 - slope * x0) % p, slope]


def _attack_affine_factor_ansatz(inst):
    """Use the right mod-p factorization idea, but assume affine factors."""
    n, p, q = inst["n"], inst["p"], inst["q"]
    alpha = [inst["M"][i][i] % p for i in range(n)]
    column = n - 1
    s = [
        inst["P"][i][column]
        * pow(inst["X"][i][column] % p, -1, p)
        % p
        for i in range(2)
    ]
    scaled_u = _interpolate_affine(alpha[0], s[0], alpha[1], s[1], p)
    if scaled_u[0] == 0:
        return _zero(n)
    inv_scale = pow(scaled_u[0], -1, p)
    u = [scaled_u[0] * inv_scale % p, scaled_u[1] * inv_scale % p]
    u_at_zero_row = (u[0] + u[1] * alpha[0]) % p
    if u_at_zero_row == 0:
        return _zero(n)
    values = []
    for j in range(2):
        denominator = inst["X"][0][j] % p * u_at_zero_row % p
        values.append(inst["P"][0][j] * pow(denominator, -1, p) % p)
    v = _interpolate_affine(alpha[0], values[0], alpha[1], values[1], p)
    u += [0] * (n - 2)
    v += [0] * (n - 2)
    return [[u[i] * v[j] % q for j in range(n)] for i in range(n)]


def _answer_size(answer):
    encoded = json.dumps(answer, separators=(",", ":"))

    def count(value):
        if isinstance(value, list):
            return sum(count(item) for item in value)
        if isinstance(value, dict):
            return sum(count(item) for item in value.values())
        return 1

    return {
        "chars": len(encoded),
        "tokens": math.ceil(len(encoded) / 4),
        "elements": count(answer),
    }


def selftest():
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    g1_attempts = 0
    failures = []
    json_roundtrips = 0
    compact_checks = 0
    compact_operations = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                failures.append([preset, seed, "plant", reason])
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
            compact, stats = _compact_ntt_certificate(inst)
            compact_ok, compact_reason = verify(inst, compact)
            compact_checks += 1
            compact_operations.append(stats["exact_operations"])
            if not compact_ok:
                failures.append([preset, seed, "compact", compact_reason])
    report["G1_planted_verifies"] = {
        "pass": not failures
        and json_roundtrips == g1_attempts
        and compact_checks == g1_attempts,
        "attempts": g1_attempts,
        "json_roundtrips": json_roundtrips,
        "independent_compact_route_checks": compact_checks,
        "compact_route_max_operations": max(compact_operations),
        "failures": failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=90210, **ship_params)
    answer = inst["answer"]
    drop = copy.deepcopy(answer)
    drop[0] = drop[0][:-1]
    duplicate = copy.deepcopy(answer) + [copy.deepcopy(answer[0])]
    out_of_range = copy.deepcopy(answer)
    out_of_range[0][0] = inst["q"]
    swap = copy.deepcopy(answer)
    flat_positions = [(i, j) for i in range(inst["n"]) for j in range(inst["n"])]
    swapped = False
    for first, second in itertools.combinations(flat_positions, 2):
        if swap[first[0]][first[1]] == swap[second[0]][second[1]]:
            continue
        trial = copy.deepcopy(answer)
        trial[first[0]][first[1]], trial[second[0]][second[1]] = (
            trial[second[0]][second[1]],
            trial[first[0]][first[1]],
        )
        if not verify(inst, trial)[0]:
            swap = trial
            swapped = True
            break
    corruptions = {
        "drop": drop,
        "swap": swap,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    g2_cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        g2_cases[name] = {"rejected": not ok, "reason": reason}
    reasons = [case["reason"] for case in g2_cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": swapped
        and all(case["rejected"] for case in g2_cases.values())
        and len(set(reasons)) == len(reasons),
        "cases": g2_cases,
    }

    realistic = (
        "The modular identity checks out. My final matrix is below.\n\n"
        "```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("no tags here") is None,
        "parsed_equals_answer": parsed == answer,
        "garbage_returns_none": parse_answer("no tags here") is None,
    }

    samples = 200_000
    sample_rng = random.Random(0x160605457)
    basis = _basis_orbit(inst)
    anchors = _anchor_coefficients(inst, basis)
    hits = 0
    anchor_hits = 0
    for _ in range(samples):
        candidate = random_candidate(inst, sample_rng)
        if _passes_anchor(inst, candidate, anchors):
            anchor_hits += 1
            if verify(inst, candidate)[0]:
                hits += 1
    exact_anchor_upper_bound = 1.0 / inst["q"]
    report["G4_guess_resistance"] = {
        "pass": hits == 0 and exact_anchor_upper_bound < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "anchor_hits": anchor_hits,
        "exact_probability_upper_bound": exact_anchor_upper_bound,
        "structure_aware_space": search_space(inst),
        "sampler": (
            "uniform over all n by n matrices modulo q, after enforcing the exact "
            "shape and residue range stated to the solver"
        ),
    }

    baseline_start = time.perf_counter()
    _attack_random_restart(inst, random.Random(77123), restarts=256)
    baseline_wall = time.perf_counter() - baseline_start
    demo_inst = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)

    attack_results = {
        "outlier_best_single_orbit_term": {"successes": 0, "attempts": 0},
        "greedy_diagonal_coefficients": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
        "in_context_affine_factor_ansatz": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_times = []
    reference_operations = []
    reference_pivots = []
    compact_successes = 0
    compact_times = []
    compact_counts = []
    for seed in range(3100, 3108):
        attacked = make_instance(seed=seed, **ship_params)
        candidates = {
            "outlier_best_single_orbit_term": _attack_outlier_one_term(attacked),
            "greedy_diagonal_coefficients": _attack_greedy_diagonal(attacked),
            "random_restart_256": _attack_random_restart(
                attacked, random.Random(seed ^ 0xA5A5), restarts=256
            ),
            "in_context_affine_factor_ansatz": _attack_affine_factor_ansatz(attacked),
        }
        for name, candidate in candidates.items():
            attack_results[name]["attempts"] += 1
            if verify(attacked, candidate)[0]:
                attack_results[name]["successes"] += 1

        reference, stats = _generic_reference_algorithm(attacked)
        reference_times.append(stats["wall_clock_sec"])
        reference_operations.append(stats["exact_operations"])
        reference_pivots.append(stats["pivots"])
        if verify(attacked, reference)[0]:
            reference_successes += 1

        start = time.perf_counter()
        compact, compact_stats = _compact_ntt_certificate(attacked)
        compact_times.append(time.perf_counter() - start)
        compact_counts.append(compact_stats["exact_operations"])
        if verify(attacked, compact)[0]:
            compact_successes += 1

    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "pseudo-E_p^(m) Smith coefficient matching",
            "source": "arXiv:1810.02964, Theorem 15 and Algorithm 1",
            "complexity": "O(n^6) operations in Z/p^nZ",
            "median_wall_clock_sec": round(statistics.median(reference_times), 6),
            "median_operations": int(statistics.median(reference_operations)),
            "median_pivots": int(statistics.median(reference_pivots)),
            "solves": f"{reference_successes}/8, as expected",
        },
        "compact_route": {
            "name": "mod-p rank-one evaluation factorization plus two inverse NTTs",
            "complexity": "O(n log n + n^2) exact field operations",
            "median_wall_clock_sec": round(statistics.median(compact_times), 8),
            "median_operations": int(statistics.median(compact_counts)),
            "solves": f"{compact_successes}/8, as expected",
        },
    }

    density_reference, density_stats = _generic_reference_algorithm(inst)
    density_reference_ok = verify(inst, density_reference)[0]
    density_valuations = density_stats["pivot_valuations"]
    rank = len(density_valuations)
    valuation_sum = sum(density_valuations)
    variables = inst["n"] * inst["n"]
    exact_solution_count = (
        inst["q"] ** (variables - rank) * inst["p"] ** valuation_sum
    )
    exact_density_log10 = (
        valuation_sum - inst["n"] * rank
    ) * math.log10(inst["p"])
    report["G5_density_and_baseline"] = {
        "pass": hits == 0
        and demo_count is not None
        and demo_count >= 1
        and density_reference_ok
        and reference_successes == 8,
        "shipping_valid_hits": hits,
        "shipping_density_samples": samples,
        "shipping_observed_solution_fraction": hits / samples,
        "shipping_exact_solution_count": exact_solution_count,
        "shipping_exact_density_log10": exact_density_log10,
        "demo_exact_solution_count": demo_count,
        "baseline_wall_seconds": round(baseline_wall, 6),
        "baseline_random_restart_iterations": 256,
        "reference_median_wall_seconds": round(statistics.median(reference_times), 6),
        "reference_median_operations": int(statistics.median(reference_operations)),
    }

    doubled = make_instance(
        n=2 * ship_params["n"],
        p_bits=ship_params["p_bits"],
        seed=77,
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * inst["n"],
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "shipping_generic_dimension": inst["n"] ** 2,
        "doubled_generic_dimension": doubled["n"] ** 2,
        "generic_elimination_growth_factor": 64,
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = 0
    witness_checks = 0
    invariant_failures = []
    unrelated_keys = []
    for seed in range(20):
        original = make_instance(seed=7000 + seed, **ship_params)
        original_key = canonical_key(original)
        unrelated_keys.append(original_key)
        rng = random.Random(8000 + seed)
        units = []
        while len(units) < 2:
            candidate = rng.randrange(1, original["q"])
            if candidate % original["p"] and candidate not in units:
                units.append(candidate)
        variants = [
            _transform_scale(original, units[0]),
            _transform_scale(original, units[1]),
            _transform_scale(original, units[0] * units[1]),
        ]
        alternate_root = copy.deepcopy(original)
        alternate_root["omega"] = pow(original["omega"], -1, original["p"])
        variants.extend(
            [alternate_root, _transform_scale(alternate_root, units[0])]
        )
        for variant in variants:
            invariance_checks += 1
            if canonical_key(variant) != original_key:
                invariant_failures.append([seed, "key changed under central scaling"])
            witness_checks += 1
            if not verify(variant, original["answer"])[0]:
                invariant_failures.append([seed, "original witness did not carry"])
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and len(set(unrelated_keys)) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": witness_checks,
        "distinct_unrelated_keys": len(set(unrelated_keys)),
        "unrelated_instances": 20,
        "failures": invariant_failures,
        "symmetries": (
            "two independent central-unit scalings, their composition, and the "
            "redundant primitive-root inversion"
        ),
        "key_basis": (
            "SHA-256 of the centrally normalized native matrices, never the seed "
            "or rendered question"
        ),
    }

    size = _answer_size(answer)
    worst_chars = _worst_answer_chars(inst["n"], inst["p"])
    worst_tokens = math.ceil(worst_chars / 4)
    arms = copy.deepcopy(G9_RESULTS["arms"])
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else 0.0
    placebo_rate = (
        arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else 0.0
    )
    intended_operations = max(compact_counts)
    hinted_hardened = G9_RESULTS["hinted_verdict"] == "hardened"
    within_caps = (
        size["chars"] <= 2000
        and size["elements"] <= 256
        and intended_operations <= 300
        and worst_chars <= 2000
    )
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": size["chars"],
        "answer_tokens": size["tokens"],
        "answer_elements": size["elements"],
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": worst_tokens,
        "intended_route_operations": intended_operations,
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
