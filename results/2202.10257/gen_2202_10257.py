r"""Verified generators for S-integral equivalences of quadratic forms.

The paper studies exact equivalence ``Q_1 \circ g = Q_2`` with
``g in GL(d, Z_S)``.  Here ``S = {infinity, 2}``.  A certificate lists the
positive 2-unit square roots of the relative operator's distinct eigenvalues;
the statement defines the corresponding Lagrange polynomial, whose exact
matrix value is the S-integral change of variables.

Instances are inverse-generated from sampled roots and an integral similarity,
so generation never solves the public instance.  The module is deterministic
in ``(n, seed, params)``, standard-library-only when ``gvlib`` is unavailable,
silent on import, and performs no file I/O.
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


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - intentional fallback
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "number_theory",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "non-degenerate integral quadratic forms",
        "relative endomorphism over Q",
        "S-integral change-of-variables matrix in spectral polynomial form",
    ],
    "verification_operations": [
        "exact rational Lagrange interpolation",
        "exact rational matrix polynomial evaluation",
        "exact matrix multiplication and comparison",
        "Bareiss determinant",
        "power-of-two denominator and determinant tests",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The trace of the relative operator is a carry-free base-four sum of "
        "its distinct 2-unit eigenvalues, avoiding dense spectral search."
    ),
    "hardness_basis": (
        "Track B: Section 5, Theorem 5.1 gives a finite bounded search for "
        "real-isotropic d>=3 forms; the reference determinant scan over the "
        "allowed 2-unit spectrum costs O(E*n^3) exact arithmetic, measured at "
        "479,724 operations and 0.26 seconds worst-case on the shipping audit; "
        "carry-free trace decoding uses at most 84 exact operations."
    ),
    "max_answer_tokens": 30,
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
        "An object {\"roots\":[[u_0,1],...,[u_(k-1),1]]} containing exactly "
        "k strictly increasing positive powers of 2.  If u_i=2^e_i, then "
        "1<=e_i<=E, where k and E are given in the instance.  Each rational "
        "uses the required JSON-native [numerator,denominator] encoding."
    ),
    "bounds": {
        "root_count_max": 8,
        "exponent_min": 1,
        "exponent_max": 180,
        "denominator": 1,
        "strictly_increasing": 1,
    },
}

DIFFICULTY: dict = {
    "demo": {
        "n": 2,
        "root_count": 2,
        "exponent_bound": 5,
        "mix_steps": 8,
    },
    "easy": {
        "n": 18,
        "root_count": 6,
        "exponent_bound": 54,
        "mix_steps": 108,
    },
    "medium": {
        "n": 28,
        "root_count": 7,
        "exponent_bound": 78,
        "mix_steps": 196,
    },
    "hard": {
        "n": 32,
        "root_count": 8,
        "exponent_bound": 104,
        "mix_steps": 256,
    },
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT: str = (
    "The normalized spectral trace is a carry-free sum of powers of four."
)
PLACEBO_HINT: str = (
    "The displayed cross-block uses exact integers in the stated coordinate order."
)

# Filled from the harness-owned files after the three required oracle runs.
_G9_EVIDENCE = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 1, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "too_easy",
}

NOTES: str = r"""
Paper triage. Section 2.1 defines R-equivalence by Q2 = Q1 composed with g
for g in GL(d,R), and identifies a quadratic form with its symmetric bilinear
matrix. Section 5, Theorem 5.1 is the applicable result: in d>=3,
non-degenerate real-isotropic integral forms are Z_S-equivalent exactly when a
bounded S-integral equivalence matrix exists. Its proof produces existence in
a finite search region, not a short formula for a public pair. The opening
paragraph of Section 5 says the everywhere-local-anisotropic case is easy
because every local transporter set is compact; this generator therefore uses
split real-isotropic forms. Dimension two is also avoided because the
Introduction points to Gauss's efficient binary-form algorithm.

Construction. Write J=[[0,I],[I,0]], the matrix of a split integral form in
2n variables. Before public data exists, sample k positive 2-units u_i, each
with the same multiplicity r=n/k, and a unimodular integer matrix R. Put
C=R^T diag(u_i^2) R^{-T}. The public second form is [[0,C],[C^T,0]], whose
relative operator is diag(C^T,C). Lagrange interpolation at u_i^2 produces a
polynomial p with p(u_i^2)=u_i. Thus p(C)=R^T diag(u_i)R^{-T} is integral, its
determinant is a power of 2, p(C)^2=C, and p(JB) carries J to B. The roots are
sampled first and retained as the certificate. No equivalence, eigenproblem,
factorization, or root search is run by make_instance.

Track B discriminator. The paper's general route is bounded matrix search.
The implemented exact reference algorithm scans every allowed power-of-four
eigenvalue using a fraction-free determinant, then expands and verifies the
spectral polynomial. It succeeds by design and costs O(E*n^3) exact
arithmetic. The compact route uses similarity invariance of trace: trace(C)/r
is a base-four integer with digit 1 exactly in the planted exponent positions.
After recognizing that invariant, repeated exact division by 4 recovers every
root without materializing an eigenvector. The measured reference cost and
the n+E+2k compact-operation bound are recorded at the shipping preset.

Attacks. Random unimodular conjugation destroys coordinate outliers while all
roots are sampled uniformly from the same exponent range. The panel tries the
smallest roots, largest roots, evenly spaced roots, a magnitude-based diagonal
outlier rule, and 256 uniform restarts. All miss the carry-free trace code. The
successful determinant scan is reported separately, as Track B requires.

Discarded first design. A degree-one two-eigenvalue polynomial certificate
passed every local gate but every bare level through n=84 had an oracle solve;
the harness correctly returned budget_bound. The current multi-root family
removes the output-format leak instead of merely enlarging that matrix.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 200_000


def _plain_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _identity(size: int) -> list[list[int]]:
    return [[1 if i == j else 0 for j in range(size)] for i in range(size)]


def _transpose(matrix):
    return [list(row) for row in zip(*matrix)]


def _right_shear(matrix, inverse, source: int, target: int, amount: int) -> None:
    """Replace R by R(I+amount*e_source*e_target^T), carrying R^-1."""
    size = len(matrix)
    for row in range(size):
        matrix[row][target] += amount * matrix[row][source]
    inverse[source] = [
        inverse[source][col] - amount * inverse[target][col]
        for col in range(size)
    ]


def _make_unimodular(size: int, steps: int, rng: random.Random):
    matrix = _identity(size)
    inverse = _identity(size)
    for i in range(size):
        _right_shear(matrix, inverse, i, (i + 1) % size,
                     -1 if rng.getrandbits(1) else 1)
    for _ in range(max(0, steps - size)):
        source = rng.randrange(size)
        target = rng.randrange(size - 1)
        if target >= source:
            target += 1
        _right_shear(matrix, inverse, source, target,
                     -1 if rng.getrandbits(1) else 1)
    return matrix, inverse


def _validate_params(n, root_count, exponent_bound, mix_steps):
    if not _plain_int(n) or n < 2:
        raise ValueError("n must be an integer at least 2")
    if (not _plain_int(root_count) or root_count < 2 or root_count > 8
            or n % root_count):
        raise ValueError("root_count must be in [2,8] and divide n")
    if (not _plain_int(exponent_bound) or exponent_bound < root_count
            or exponent_bound > 180):
        raise ValueError("exponent_bound must lie in [root_count,180]")
    if not _plain_int(mix_steps) or mix_steps < n:
        raise ValueError("mix_steps must be an integer at least n")


def make_instance(n, seed=0, root_count=6, exponent_bound=54,
                  mix_steps=None, **params) -> dict:
    """Inverse-generate a split S-integral quadratic-form equivalence."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if mix_steps is None:
        mix_steps = 6 * n
    _validate_params(n, root_count, exponent_bound, mix_steps)
    rng = random.Random(seed)

    exponents = sorted(rng.sample(range(1, exponent_bound + 1), root_count))
    roots = [1 << exponent for exponent in exponents]
    eigenvalues = [root * root for root in roots]
    multiplicity = n // root_count
    diagonal = []
    for value in eigenvalues:
        diagonal.extend([value] * multiplicity)
    rng.shuffle(diagonal)

    matrix, inverse = _make_unimodular(n, mix_steps, rng)
    # C = R^T D R^{-T}.
    cross_block = [
        [sum(matrix[k][i] * diagonal[k] * inverse[j][k]
             for k in range(n))
         for j in range(n)]
        for i in range(n)
    ]
    return {
        "family": "multi-spectrum S-integral quadratic-form equivalence",
        "n": n,
        "dimension": 2 * n,
        "S_finite_primes": [2],
        "root_count": root_count,
        "root_multiplicity": multiplicity,
        "exponent_bound": exponent_bound,
        "mix_steps": mix_steps,
        "cross_block": cross_block,
        "answer": {"roots": [[root, 1] for root in roots]},
    }


def _format_matrix(matrix) -> str:
    return "\n".join(" ".join(str(value) for value in row) for row in matrix)


def render(inst) -> str:
    n = inst["n"]
    dimension = inst["dimension"]
    count = inst["root_count"]
    bound = inst["exponent_bound"]
    statement = f"""S-integral equivalence of two quadratic forms

Let Z[1/2] be the rational numbers whose reduced denominator is a power of 2.
A square matrix G is in GL(d,Z[1/2]) when every entry of G and G^(-1) is in
Z[1/2]. For a symmetric integer matrix A, write Q_A(x)=x^T A x. An
S-integral equivalence from Q_A to Q_B is a matrix G in GL(d,Z[1/2]) satisfying
G^T A G = B exactly.

Here d={dimension} and n={n}. Let I be the n by n identity matrix and set

    A = [[0,I],[I,0]].

The other symmetric matrix is

    B = [[0,C],[C^T,0]],

where the complete n by n integer matrix C is:

{_format_matrix(inst['cross_block'])}

Find exactly k={count} distinct positive powers of 2, written in strictly
increasing order as u_0,...,u_(k-1), with u_i=2^e_i and
1 <= e_i <= E={bound}. From them define the rational Lagrange polynomial

  p(t) = sum_i u_i * product_(j!=i) (t-u_j^2)/(u_i^2-u_j^2).

Your roots are a valid certificate exactly when

  G = p(A^(-1)B)

belongs to GL(d,Z[1/2]) and satisfies G^T A G=B. Products over an empty set
are 1; indices are 0-based; roots may not repeat; and the displayed order is
part of the required output shape.

Encode every integer root u as the exact rational pair [u,1]. Give your final
answer inside <answer></answer> tags as exactly one JSON object of the form
{{"roots":[[u_0,1],...,[u_(k-1),1]]}}.
Example for k=2: <answer>{{"roots":[[2,1],[8,1]]}}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Extract the tagged JSON certificate; malformed text returns None."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _power_of_two(value: int) -> bool:
    return value > 0 and value & (value - 1) == 0


def _s_integer(value: Fraction) -> bool:
    return _power_of_two(value.denominator)


def _s_unit(value: Fraction) -> bool:
    return (value != 0 and _power_of_two(abs(value.numerator))
            and _power_of_two(value.denominator))


def _det_fraction(matrix) -> Fraction:
    if exact_matrices is not None:
        return exact_matrices.det(matrix)
    size = len(matrix)
    work = [[Fraction(value) for value in row] for row in matrix]
    determinant = Fraction(1)
    sign = 1
    for col in range(size):
        pivot = next((row for row in range(col, size)
                      if work[row][col] != 0), None)
        if pivot is None:
            return Fraction(0)
        if pivot != col:
            work[col], work[pivot] = work[pivot], work[col]
            sign = -sign
        value = work[col][col]
        determinant *= value
        for row in range(col + 1, size):
            if work[row][col] == 0:
                continue
            factor = work[row][col] / value
            for j in range(col + 1, size):
                work[row][j] -= factor * work[col][j]
    return sign * determinant


def _matmul(left, right):
    right_t = _transpose(right)
    return [
        [sum((a * b for a, b in zip(row, col)), Fraction(0))
         for col in right_t]
        for row in left
    ]


def _poly_mul(left, right):
    out = [Fraction(0)] * (len(left) + len(right) - 1)
    for i, a in enumerate(left):
        for j, b in enumerate(right):
            out[i + j] += a * b
    return out


def _interpolation_coefficients(roots):
    """Coefficients low-degree first for p(root_i^2)=root_i."""
    nodes = [root * root for root in roots]
    answer = [Fraction(0)] * len(roots)
    for i, root in enumerate(roots):
        basis = [Fraction(1)]
        denominator = Fraction(1)
        for j, node in enumerate(nodes):
            if i == j:
                continue
            basis = _poly_mul(basis, [-node, Fraction(1)])
            denominator *= nodes[i] - node
        scale = Fraction(root, 1) / denominator
        for degree, coefficient in enumerate(basis):
            answer[degree] += scale * coefficient
    return answer


def _matrix_polynomial(matrix, coefficients):
    size = len(matrix)
    value = [[Fraction(0) for _ in range(size)] for _ in range(size)]
    for coefficient in reversed(coefficients):
        value = _matmul(value, matrix)
        for i in range(size):
            value[i][i] += coefficient
    return value


def _decode_certificate(inst, answer):
    if not isinstance(answer, dict):
        return None, "certificate_not_object"
    if "roots" not in answer:
        return None, "missing_roots"
    items = answer["roots"]
    if not isinstance(items, list) or len(items) != inst["root_count"]:
        return None, "root_count"
    roots = []
    for pair in items:
        if (not isinstance(pair, list) or len(pair) != 2
                or not all(_plain_int(value) for value in pair)
                or pair[1] != 1):
            return None, "rational_encoding"
        roots.append(pair[0])
    if any(root <= 0 or not _power_of_two(root) for root in roots):
        return None, "not_positive_2_units"
    if len(set(roots)) != len(roots):
        return None, "root_repeat"
    if any(roots[i] > roots[i + 1] for i in range(len(roots) - 1)):
        return None, "root_order"
    if any(root.bit_length() - 1 > inst["exponent_bound"] for root in roots):
        return None, "root_out_of_range"
    return roots, "ok"


def verify(inst, answer) -> tuple[bool, str]:
    """Expand and check any certificate in the stated bounded language."""
    roots, reason = _decode_certificate(inst, answer)
    if roots is None:
        return False, reason

    trace = sum(inst["cross_block"][i][i] for i in range(inst["n"]))
    expected = inst["root_multiplicity"] * sum(root * root for root in roots)
    if trace != expected:
        return False, "spectral_trace"

    coefficients = _interpolation_coefficients(roots)
    cross = [[Fraction(value) for value in row]
             for row in inst["cross_block"]]
    square_root = _matrix_polynomial(cross, coefficients)
    if any(not _s_integer(value) for row in square_root for value in row):
        return False, "matrix_not_S_integral"
    if _matmul(square_root, square_root) != cross:
        return False, "matrix_square"
    determinant = _det_fraction(square_root)
    if not _s_unit(determinant):
        return False, "determinant_not_S_unit"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Sample uniformly from sorted k-subsets of allowed 2-unit roots."""
    exponents = sorted(rng.sample(
        range(1, inst["exponent_bound"] + 1), inst["root_count"]
    ))
    return {"roots": [[1 << exponent, 1] for exponent in exponents]}


def search_space(inst) -> int | None:
    return math.comb(inst["exponent_bound"], inst["root_count"])


def enumerate_all(inst) -> int | None:
    if search_space(inst) > _ENUMERATION_CAP:
        return None
    count = 0
    for exponents in itertools.combinations(
            range(1, inst["exponent_bound"] + 1), inst["root_count"]):
        candidate = {"roots": [[1 << exponent, 1] for exponent in exponents]}
        count += int(verify(inst, candidate)[0])
    return count


def canonical_key(inst) -> str:
    """A cheap invariant under signed coordinate relabelling and transpose."""
    absolute_multiset = sorted(
        abs(value) for row in inst["cross_block"] for value in row
    )
    trace = sum(inst["cross_block"][i][i] for i in range(inst["n"]))
    payload = json.dumps(
        [inst["n"], inst["root_count"], trace, absolute_multiset],
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def escalate(params) -> dict | str | None:
    """Grow matrix work, exponent haystack, and conjugation crowding."""
    current = dict(params)
    roots = int(current.get("root_count", 8))
    n = int(current.get("n", 4 * roots))
    bound = int(current.get("exponent_bound", 104))
    mix_steps = int(current.get("mix_steps", 8 * n))
    return {
        "n": n + roots,
        "root_count": roots,
        "exponent_bound": min(180, bound + 12),
        "mix_steps": mix_steps + 8 * roots,
    }


def _roots_from_exponents(exponents):
    return {"roots": [[1 << exponent, 1] for exponent in sorted(exponents)]}


def _attack_evenly_spaced(inst):
    count = inst["root_count"]
    bound = inst["exponent_bound"]
    exponents = [1 + (i * (bound - 1)) // (count - 1) for i in range(count)]
    return _roots_from_exponents(exponents)


def _attack_diagonal_magnitudes(inst):
    """Use individual diagonal magnitudes, ignoring similarity cancellation."""
    count = inst["root_count"]
    bound = inst["exponent_bound"]
    candidates = set()
    for i in range(inst["n"]):
        value = abs(inst["cross_block"][i][i])
        if value:
            candidates.add(max(1, min(bound, value.bit_length() // 2)))
    for exponent in range(1, bound + 1):
        if len(candidates) >= count:
            break
        candidates.add(exponent)
    return _roots_from_exponents(sorted(candidates)[:count])


def _signed_relabel(inst, permutation, signs, take_transpose=False):
    size = inst["n"]
    if sorted(permutation) != list(range(size)):
        raise ValueError("permutation is invalid")
    if len(signs) != size or any(sign not in (-1, 1) for sign in signs):
        raise ValueError("sign vector is invalid")
    source = _transpose(inst["cross_block"]) if take_transpose else inst["cross_block"]
    cross = [
        [signs[i] * signs[j] * source[permutation[i]][permutation[j]]
         for j in range(size)]
        for i in range(size)
    ]
    out = dict(inst)
    out["cross_block"] = cross
    out["answer"] = json.loads(json.dumps(inst["answer"]))
    return out


def _bareiss_det_count(matrix):
    """Integer Bareiss determinant and a counted exact-arithmetic cost."""
    size = len(matrix)
    work = [row[:] for row in matrix]
    sign = 1
    previous = 1
    operations = 0
    for col in range(size - 1):
        if work[col][col] == 0:
            pivot = next((row for row in range(col + 1, size)
                          if work[row][col] != 0), None)
            if pivot is None:
                return 0, operations
            work[col], work[pivot] = work[pivot], work[col]
            sign = -sign
        pivot_value = work[col][col]
        for row in range(col + 1, size):
            for j in range(col + 1, size):
                work[row][j] = (
                    work[row][j] * pivot_value
                    - work[row][col] * work[col][j]
                ) // previous
                operations += 4
            work[row][col] = 0
        previous = pivot_value
    return sign * work[-1][-1], operations


def _reference_algorithm(inst):
    """Scan the allowed spectrum with exact determinants, then verify."""
    roots = []
    operations = 0
    size = inst["n"]
    cross = inst["cross_block"]
    for exponent in range(1, inst["exponent_bound"] + 1):
        eigenvalue = 1 << (2 * exponent)
        shifted = [
            [cross[i][j] - (eigenvalue if i == j else 0)
             for j in range(size)]
            for i in range(size)
        ]
        determinant, cost = _bareiss_det_count(shifted)
        operations += cost + size
        if determinant == 0:
            roots.append(1 << exponent)
    if len(roots) != inst["root_count"]:
        return None, operations
    answer = {"roots": [[root, 1] for root in roots]}
    operations += (inst["root_count"] + 2) * 2 * size ** 3
    if not verify(inst, answer)[0]:
        return None, operations
    return answer, operations


def _answer_atom_count(answer) -> int:
    if not isinstance(answer, dict):
        return 0
    roots = answer.get("roots", [])
    return sum(len(pair) for pair in roots if isinstance(pair, list))


def selftest() -> dict:
    report = {}

    planted_ok = 0
    planted_total = 0
    for params in DIFFICULTY.values():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, _ = verify(inst, inst["answer"])
            planted_ok += int(ok)
            planted_total += 1
    report["G1_planted_verifies"] = {
        "pass": planted_ok == planted_total,
        "verified": planted_ok,
        "attempts": planted_total,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    base = shipping["answer"]["roots"]
    swapped = [pair[:] for pair in base]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = [pair[:] for pair in base]
    duplicated[1] = duplicated[0][:]
    corruptions = {
        "drop": {"roots": base[:-1]},
        "swap": {"roots": swapped},
        "duplicate": {"roots": duplicated},
        "empty": {},
        "out_of_range": {
            "roots": [pair[:] for pair in base[:-1]]
                     + [[1 << (shipping["exponent_bound"] + 1), 1]]
        },
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, why = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": why}
    reasons = {value["reason"] for value in corruption_results.values()}
    report["G2_rejects_corruption"] = {
        "pass": (all(value["rejected"] for value in corruption_results.values())
                 and len(reasons) == len(corruption_results)),
        "cases": corruption_results,
        "distinct_reasons": len(reasons),
    }

    wire = json.dumps(shipping["answer"], separators=(",", ":"))
    realistic = (
        "I used the relative spectrum.\n"
        f"<answer>```json\n{wire}\n```</answer>\n"
        "These are exact positive 2-units."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": (parsed == shipping["answer"]
                 and json.loads(json.dumps(shipping["answer"]))
                 == shipping["answer"]),
        "parsed_equals_answer": parsed == shipping["answer"],
        "json_native": (json.loads(json.dumps(shipping["answer"]))
                        == shipping["answer"]),
    }

    guess_rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "candidate_space": search_space(shipping),
        "prior": "uniform k-subsets of exponents 1..E, encoded as sorted 2-units",
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    started = time.perf_counter()
    reference_answer, reference_ops = _reference_algorithm(shipping)
    reference_seconds = time.perf_counter() - started
    reference_ok = (reference_answer is not None
                    and verify(shipping, reference_answer)[0])
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_total >= 200_000 and guess_rate < 1e-6 and reference_ok,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_fraction": guess_rate,
        "shipping_exact_enumeration": enumerate_all(shipping),
        "demo_exact_solution_count": enumerate_all(demo),
        "baseline_wall_clock_seconds": round(reference_seconds, 6),
        "baseline_exact_operations": reference_ops,
        "baseline_algorithm": "Bareiss determinant scan of allowed 2-unit spectrum",
    }

    attack_names = (
        "outlier_diagonal_magnitudes",
        "greedy_smallest_exponents",
        "greedy_largest_exponents",
        "obvious_evenly_spaced_exponents",
        "random_restart_256",
    )
    attacks = {name: {"successes": 0, "attempts": 8} for name in attack_names}
    reference_successes = 0
    reference_times = []
    reference_operations = []
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        count = inst["root_count"]
        bound = inst["exponent_bound"]
        candidates = {
            "outlier_diagonal_magnitudes": _attack_diagonal_magnitudes(inst),
            "greedy_smallest_exponents": _roots_from_exponents(range(1, count + 1)),
            "greedy_largest_exponents": _roots_from_exponents(
                range(bound - count + 1, bound + 1)
            ),
            "obvious_evenly_spaced_exponents": _attack_evenly_spaced(inst),
        }
        for name, candidate in candidates.items():
            attacks[name]["successes"] += int(verify(inst, candidate)[0])
        rrng = random.Random(seed ^ 0x5A17)
        random_hit = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, rrng))[0]:
                random_hit = True
                break
        attacks["random_restart_256"]["successes"] += int(random_hit)

        started = time.perf_counter()
        candidate, operations = _reference_algorithm(inst)
        reference_times.append(time.perf_counter() - started)
        reference_operations.append(operations)
        reference_successes += int(candidate is not None and verify(inst, candidate)[0])

    all_failed = all(value["successes"] == 0 and value["attempts"] >= 8
                     for value in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Bareiss determinant scan of allowed 2-unit spectrum",
            "complexity": "O(E*n^3) exact integer arithmetic",
            "wall_clock_sec_mean": round(sum(reference_times) / len(reference_times), 6),
            "wall_clock_sec_max": round(max(reference_times), 6),
            "operations_mean": round(sum(reference_operations) / len(reference_operations)),
            "operations_max": max(reference_operations),
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled_params["mix_steps"] *= 2
    doubled = make_instance(seed=2718, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    shipping_scale = (shipping["exponent_bound"] * shipping["n"] ** 3)
    doubled_scale = (doubled["exponent_bound"] * doubled["n"] ** 3)
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["dimension"] == 2 * shipping["dimension"]
                and doubled_scale > shipping_scale,
        "shipping_dimension": shipping["dimension"],
        "doubled_dimension": doubled["dimension"],
        "doubled_planted_verifies": doubled_ok,
        "shipping_reference_operation_scale": shipping_scale,
        "doubled_reference_operation_scale": doubled_scale,
        "answer_elements_unchanged": (
            _answer_atom_count(shipping["answer"])
            == _answer_atom_count(doubled["answer"])
        ),
    }

    invariant = 0
    original_answer_valid = 0
    changed = 0
    for seed in range(20):
        inst = make_instance(seed=1000 + seed,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
        rrng = random.Random(9000 + seed)
        first_perm = list(range(inst["n"]))
        second_perm = list(range(inst["n"]))
        rrng.shuffle(first_perm)
        rrng.shuffle(second_perm)
        first_signs = [(-1 if rrng.getrandbits(1) else 1)
                       for _ in range(inst["n"])]
        second_signs = [(-1 if rrng.getrandbits(1) else 1)
                        for _ in range(inst["n"])]
        transformed = _signed_relabel(inst, first_perm, first_signs,
                                      take_transpose=bool(seed % 2))
        transformed = _signed_relabel(transformed, second_perm, second_signs,
                                      take_transpose=bool((seed // 2) % 2))
        invariant += int(canonical_key(inst) == canonical_key(transformed))
        original_answer_valid += int(verify(transformed, inst["answer"])[0])
        changed += int(transformed["cross_block"] != inst["cross_block"])
    unrelated_keys = {
        canonical_key(make_instance(seed=2000 + seed,
                                    **DIFFICULTY[SHIPPING_DIFFICULTY]))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": (invariant == 20 and original_answer_valid == 20
                 and changed == 20 and len(unrelated_keys) == 20),
        "composed_relabellings_invariant": invariant,
        "transformed_instances_changed": changed,
        "original_answers_valid_after_relabelling": original_answer_valid,
        "unrelated_distinct_keys": len(unrelated_keys),
        "attempts_each": 20,
    }

    answer_chars = 0
    answer_atoms = 0
    for seed in range(40):
        answer = make_instance(seed=3000 + seed,
                               **DIFFICULTY[SHIPPING_DIFFICULTY])["answer"]
        answer_chars = max(
            answer_chars, len(json.dumps(answer, separators=(",", ":")))
        )
        answer_atoms = max(answer_atoms, _answer_atom_count(answer))
    answer_tokens = (answer_chars + 3) // 4
    intended_operations = (
        shipping["n"] + shipping["exponent_bound"]
        + 2 * shipping["root_count"]
    )
    arms = _G9_EVIDENCE["arms"]
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = (arms["hinted"]["solved"] / hinted_attempts
                   if hinted_attempts else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / placebo_attempts
                    if placebo_attempts else 0.0)
    within_caps = (answer_chars <= 2000 and answer_atoms <= 256
                   and intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass") for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = DIFFICULTY[SHIPPING_DIFFICULTY]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
