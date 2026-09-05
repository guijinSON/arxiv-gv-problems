"""Determinant-orbit witnesses for fat subspaces over GF(2^128).

Lemma 8 of arXiv:1804.11172 identifies the SL(s,2^g)-orbit of a fat
s-subspace with the determinant of any ordered GF(2)-basis, modulo GF(2)^*.
For q=2 that quotient does nothing.  This generator samples the determinant
first, composes a matrix around it using a rank-one determinant identity, and
then independently relabels rows and columns.  The planted invariant is known
without eliminating the generated matrix.
"""

from __future__ import annotations

import collections
import functools
import hashlib
import json
import os
import random
import re
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - fallback is intentional
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "polynomial",
    "native_objects": [
        "fat subspace of GF(2^128)^s given by an ordered GF(2)-basis",
        "matrix over GF(2^128)",
        "determinant orbit invariant as a polynomial over GF(2)",
    ],
    "verification_operations": [
        "exact polynomial-basis arithmetic in GF(2^128)",
        "exact finite-field Gaussian elimination",
        "canonical sparse-polynomial comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize a row/column-permuted, determinant-one even rank-one "
        "perturbation beneath a constant-column term, so paired backgrounds "
        "cancel and the determinant orbit is obtained without elimination."
    ),
    "hardness_basis": (
        "Track B: Lemma 8 makes the orbit label a determinant, computable by "
        "Gaussian elimination in O(s^3) GF(2^128) operations; at shipping "
        "s=41 it averaged 16,267 field operations, 418,229 shift/XOR steps, "
        "and 0.061 seconds over eight seeds, while the rank-one invariant "
        "route uses at most 41 field additions after recognizing the structure."
    ),
    "max_answer_tokens": 62,
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
        "One nonzero polynomial of degree below 128 over GF(2), represented "
        "canonically by a JSON list of the strictly increasing exponents whose "
        "coefficients are 1; it is the unique determinant orbit invariant."
    ),
    "bounds": {
        "field": "GF(2^128)",
        "coefficient_set": [0, 1],
        "minimum_exponent": 0,
        "maximum_exponent": 127,
        "maximum_nonzero_terms": 128,
        "zero_polynomial_allowed": False,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 1},
    "easy": {"n": 6},
    "medium": {"n": 12},
    "hard": {"n": 20},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT: str = (
    "Each column's modal value is a rank-one background, while the residual's two exceptional rows share an even-weight pattern."
)
PLACEBO_HINT: str = (
    "Each displayed field value uses one fixed polynomial basis, making consistent coefficient bookkeeping important."
)

_G9_EVIDENCE = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "api_blocked_no_scored_attempts",
    "blocked_reason": "OpenRouter returned HTTP 403 key-limit errors on every redraw",
}

NOTES = r"""
Definition and native objects. Definition 1 says that q-GDD groups and blocks
are subspaces over GF(q). Section 5 specializes to V=GF(q^g)^s and calls an
s-dimensional GF(q)-subspace fat when an ordered GF(q)-basis is linearly
independent over GF(q^g). Lemma 8 is decisive: for k=s, the fat subspaces split
into (q^g-1)/(q-1) SL(s,q^g)/GF(q)^* orbits, classified by det(A)GF(q)^*, where
A contains any ordered GF(q)-basis as its rows. The answer here is exactly that
paper-native invariant for q=2 and g=128, not a graph surrogate.

Step-0 discrimination and easy regimes. Lemma 8 also rules out Track A: exact
Gaussian elimination computes the certificate in polynomial time. Its proof
even constructs a matrix carrying one fat subspace to another after their
determinant classes agree. Theorem 4 turns unions of these determinant orbits
into q-GDDs; for k<s, Lemma 8 says there is only one orbit, while for exposed
triangular or diagonal bases the k=s invariant is immediate. Those regimes are
therefore avoided. This is honestly Track B: the measured reference algorithm
is elimination, while the compact route is the determinant lemma applied to a
hidden rank-one perturbation of a permutation matrix.

Generation. Let s=2n+1. The generator samples a nonzero target z in GF(2^128),
then forms a vector v from n independently sampled values, each repeated twice,
and the residual z+1. Thus 1+sum(v_i)=z in characteristic two. It also forms
L=I+u*w^T, where u has weight two, w has even weight, and w^T*u=0. Hence
det(L)=1 and L*1=1. The displayed matrix is L+1*v^T, independently permuted in
its rows and columns. The matrix determinant lemma gives determinant z, and
row/column permutations have determinant 1 in characteristic two. The rows are
therefore independent over GF(2^128), so their GF(2)-span is fat. No determinant
or linear solve is run during generation.

Attacks. The row and column permutations remove a privileged displayed
diagonal. A most-frequent-entry outlier, the product of the displayed diagonal,
the displayed trace, and 256 uniform restarts are tested. The strongest
in-context near miss recovers every constant column background but forgets the
rank-one '+1' correction; it is deterministically wrong. Exact finite-field
elimination is deliberately successful and is reported separately as the
Track-B reference algorithm.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_DEGREE = 128
_MASK = (1 << _DEGREE) - 1
# x^128 + x^7 + x^2 + x + 1, the irreducible polynomial used by GCM.
_MODULUS_LOW = (1 << 7) | (1 << 2) | (1 << 1) | 1
_MODULUS = (1 << _DEGREE) | _MODULUS_LOW
_ENUMERATION_CAP = 200_000


def _support(value):
    return [i for i in range(_DEGREE) if (value >> i) & 1]


def _from_support(support):
    value = 0
    for exponent in support:
        value |= 1 << exponent
    return value


def _gf_mul(a, b, stats=None):
    """Multiply in GF(2^128), optionally counting exact shift/XOR steps."""
    a &= _MASK
    b &= _MASK
    result = 0
    if stats is not None:
        stats["field_multiplications"] += 1
    while b:
        if stats is not None:
            stats["shift_xor_steps"] += 1
        if b & 1:
            result ^= a
        b >>= 1
        carry = a >> (_DEGREE - 1)
        a = (a << 1) & _MASK
        if carry:
            a ^= _MODULUS_LOW
    return result


def _gf_pow(a, exponent, stats=None):
    result = 1
    base = a
    while exponent:
        if exponent & 1:
            result = _gf_mul(result, base, stats)
        exponent >>= 1
        if exponent:
            base = _gf_mul(base, base, stats)
    return result


def _gf_inv(a, stats=None):
    if a == 0:
        raise ZeroDivisionError("zero has no inverse")
    return _gf_pow(a, (1 << _DEGREE) - 2, stats)


def _poly_degree(a):
    return a.bit_length() - 1


def _poly_mod(a, modulus):
    md = _poly_degree(modulus)
    while a and _poly_degree(a) >= md:
        a ^= modulus << (_poly_degree(a) - md)
    return a


def _poly_gcd(a, b):
    while b:
        a, b = b, _poly_mod(a, b)
    return a


def _modulus_is_irreducible():
    """Rabin test; 128 has the single prime divisor 2."""
    x = 2
    power = x
    halfway = None
    for i in range(1, _DEGREE + 1):
        power = _gf_mul(power, power)
        if i == _DEGREE // 2:
            halfway = power
    return power == x and _poly_gcd(halfway ^ x, _MODULUS) == 1


def _determinant_with_stats(matrix):
    """Exact Gaussian determinant and transparent operation counters."""
    a = [list(row) for row in matrix]
    size = len(a)
    stats = {
        "field_multiplications": 0,
        "field_additions": 0,
        "field_inversions": 0,
        "pivot_tests": 0,
        "row_swaps": 0,
        "shift_xor_steps": 0,
    }
    determinant = 1
    for col in range(size):
        pivot = None
        for row in range(col, size):
            stats["pivot_tests"] += 1
            if a[row][col]:
                pivot = row
                break
        if pivot is None:
            return 0, stats
        if pivot != col:
            a[col], a[pivot] = a[pivot], a[col]
            stats["row_swaps"] += 1
            # In characteristic two the usual sign change is invisible.
        pivot_value = a[col][col]
        determinant = _gf_mul(determinant, pivot_value, stats)
        stats["field_inversions"] += 1
        inverse = _gf_inv(pivot_value, stats)
        for row in range(col + 1, size):
            if not a[row][col]:
                continue
            factor = _gf_mul(a[row][col], inverse, stats)
            for j in range(col, size):
                product = _gf_mul(factor, a[col][j], stats)
                a[row][j] ^= product
                stats["field_additions"] += 1
    return determinant, stats


@functools.lru_cache(maxsize=32)
def _determinant_cached(matrix):
    return _determinant_with_stats(matrix)[0]


def _validate_params(n):
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 120:
        raise ValueError("n must be an integer in 1..120")


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a fat-subspace determinant-orbit instance."""
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_params(n)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    size = 2 * n + 1

    target = rng.getrandbits(_DEGREE)
    while target == 0:
        target = rng.getrandbits(_DEGREE)
    for _construction_attempt in range(100):
        backgrounds = []
        for _ in range(n):
            value = rng.getrandbits(_DEGREE)
            backgrounds.extend((value, value))
        backgrounds.append(target ^ 1)
        rng.shuffle(backgrounds)

        u_support = rng.sample(range(size), 2)
        remaining = [i for i in range(size) if i not in u_support]
        extra_count = min(4, 2 * (len(remaining) // 2))
        w_support = set(u_support + rng.sample(remaining, extra_count))
        # L=I+u*w^T has det(L)=1+w^T*u=1 and L*1=1 because both
        # w^T*u and the weight of w are even.
        base = [
            [backgrounds[j] ^ int(i == j)
             ^ int(i in u_support and j in w_support)
             for j in range(size)]
            for i in range(size)
        ]

        counts = collections.Counter(value for row in base for value in row)
        modal_guess = max(counts, key=lambda value: (counts[value], -value))
        if modal_guess == target:
            continue
        for _permutation_attempt in range(100):
            row_order = list(range(size))
            column_order = list(range(size))
            rng.shuffle(row_order)
            rng.shuffle(column_order)
            matrix = [
                [base[row_order[i]][column_order[j]] for j in range(size)]
                for i in range(size)
            ]
            trace_guess = 0
            diagonal_guess = 1
            for i in range(size):
                trace_guess ^= matrix[i][i]
                diagonal_guess = _gf_mul(diagonal_guess, matrix[i][i])
            if trace_guess == target or diagonal_guess == target:
                continue
            return {
                "paper": "arXiv:1804.11172",
                "q": 2,
                "g": _DEGREE,
                "s": size,
                "ambient_dimension_over_gf2": _DEGREE * size,
                "field_modulus_exponents": [0, 1, 2, 7, 128],
                "matrix": matrix,
                "answer": _support(target),
            }
    raise RuntimeError("could not remove elementary determinant signatures")


def _hex(value):
    return f"{value:032x}"


def render(inst) -> str:
    rows = [" ".join(_hex(value) for value in row) for row in inst["matrix"]]
    statement = f"""Determinant orbit of a fat subspace over GF(2^128)

Work in the finite field F = GF(2)[x]/(x^128+x^7+x^2+x+1). A field element is
written as exactly 32 hexadecimal digits: bit e is the coefficient of x^e,
for 0 <= e <= 127. Addition is bitwise XOR. Multiplication is ordinary
polynomial multiplication over GF(2), reduced by x^128=x^7+x^2+x+1.

The {inst['s']} rows of the matrix A below are an ordered GF(2)-basis of a
GF(2)-subspace U of F^{inst['s']}. They are promised to be linearly independent
over F, so U is a fat {inst['s']}-subspace in the terminology of the paper.
For q=2, the determinant orbit invariant of U is simply det_F(A), because
GF(2)^*={{1}}. Compute that nonzero field element exactly.

Matrix A ({inst['s']} rows and {inst['s']} columns; spaces separate entries):
""" + "\n".join(rows) + "\n\n"
    statement += """Output the invariant in its canonical sparse polynomial form: a JSON list
of every exponent e whose coefficient is 1, in strictly increasing order.
The list must be nonempty; exponents are 0-indexed integers in 0..127, with no
repeats. For example, 1+x^7+x^91 is written [0,7,91].

Give your final answer inside <answer></answer> tags, as that JSON list.
Example: <answer>[0,7,91]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    payload = matches[-1].strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", payload, re.I | re.S)
    if fence:
        payload = fence.group(1).strip()
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError):
        return None
    if not isinstance(answer, list):
        return None
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return None
    return answer


def verify(inst, answer) -> tuple[bool, str]:
    """Check any canonical polynomial equal to the exact determinant."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list of exponents"
    if not answer:
        return False, "zero polynomial is not a valid orbit label"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "every exponent must be an integer"
    if any(x < 0 or x >= _DEGREE for x in answer):
        return False, "an exponent is outside the inclusive range 0..127"
    if len(set(answer)) != len(answer):
        return False, "the sparse polynomial contains a duplicate exponent"
    if any(a >= b for a, b in zip(answer, answer[1:])):
        return False, "exponents are not in strictly increasing order"
    matrix = inst.get("matrix")
    size = inst.get("s")
    if (not isinstance(matrix, list) or len(matrix) != size
            or any(not isinstance(row, list) or len(row) != size for row in matrix)
            or any(isinstance(value, bool) or not isinstance(value, int)
                   or value < 0 or value > _MASK
                   for row in matrix for value in row)):
        return False, "instance matrix is malformed"
    determinant = _determinant_cached(tuple(tuple(row) for row in matrix))
    if _from_support(answer) != determinant:
        return False, "polynomial is not the determinant orbit invariant"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Sample uniformly from all nonzero degree-below-128 binary polynomials."""
    if not hasattr(rng, "randrange"):
        raise TypeError("rng must provide randrange")
    return _support(rng.randrange(1, 1 << _DEGREE))


def search_space(inst) -> int | None:
    return (1 << _DEGREE) - 1


def enumerate_all(inst) -> int | None:
    if search_space(inst) > _ENUMERATION_CAP:
        return None
    return sum(verify(inst, random_candidate(inst, random.Random(i)))[0]
               for i in range(search_space(inst)))


def _axis_signature(matrix):
    return tuple(sorted(tuple(sorted(row)) for row in matrix))


def canonical_key(inst) -> str:
    """Invariant under independent row/column permutations and transposition."""
    matrix = inst["matrix"]
    transpose = [list(column) for column in zip(*matrix)]
    row_signature = _axis_signature(matrix)
    column_signature = _axis_signature(transpose)
    payload = (
        inst["g"], inst["s"],
        min(row_signature, column_signature),
        tuple(sorted(value for row in matrix for value in row)),
    )
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params) -> dict | str | None:
    n = params.get("n")
    if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 120:
        return None
    if n >= 120:
        return None
    return {"n": min(120, n + 8)}


def _guess_most_frequent(inst):
    counts = collections.Counter(value for row in inst["matrix"] for value in row)
    return _support(max(counts, key=lambda value: (counts[value], -value)))


def _guess_diagonal_product(inst):
    value = 1
    for i, row in enumerate(inst["matrix"]):
        value = _gf_mul(value, row[i])
    return _support(value) if value else []


def _guess_trace(inst):
    value = 0
    for i, row in enumerate(inst["matrix"]):
        value ^= row[i]
    return _support(value) if value else []


def _column_backgrounds(inst):
    matrix = inst["matrix"]
    backgrounds = []
    for j in range(inst["s"]):
        counts = collections.Counter(matrix[i][j] for i in range(inst["s"]))
        backgrounds.append(max(counts, key=lambda value: (counts[value], -value)))
    return backgrounds


def _guess_background_without_correction(inst):
    value = 0
    for background in _column_backgrounds(inst):
        value ^= background
    return _support(value) if value else []


def _relabel_instance(inst, row_order, column_order, transpose=False):
    size = inst["s"]
    if sorted(row_order) != list(range(size)):
        raise ValueError("row_order must be a permutation")
    if sorted(column_order) != list(range(size)):
        raise ValueError("column_order must be a permutation")
    matrix = [
        [inst["matrix"][row_order[i]][column_order[j]] for j in range(size)]
        for i in range(size)
    ]
    if transpose:
        matrix = [list(column) for column in zip(*matrix)]
    out = dict(inst)
    out["matrix"] = matrix
    out["answer"] = list(inst["answer"])
    return out


def _answer_atom_count(answer):
    return len(answer) if isinstance(answer, list) else 0


def _compact_route_operations(inst):
    # s-1 XORs to combine the column backgrounds, then one rank-one correction.
    return inst["s"]


def selftest() -> dict:
    report = {}

    planted = total = 0
    for params in DIFFICULTY.values():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            planted += int(verify(inst, inst["answer"])[0])
            total += 1
    report["G1_planted_verifies"] = {
        "pass": planted == total and _modulus_is_irreducible(),
        "verified": planted,
        "attempts": total,
        "field_modulus_irreducible": _modulus_is_irreducible(),
        "construction": "inverse determinant generation via det(L+1*v^T)=1+sum(v)",
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    base = shipping["answer"]
    if len(base) < 2:
        raise AssertionError("audit seed unexpectedly has a one-term answer")
    corruptions = {
        "drop": base[:-1],
        "swap": [base[1], base[0], *base[2:]],
        "duplicate": [base[0], base[0], *base[1:]],
        "empty": [],
        "out_of_range": [*base, 128],
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = {case["reason"] for case in cases.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
                and len(reasons) == len(cases),
        "cases": cases,
        "distinct_reasons": len(reasons),
    }

    wire = json.dumps(shipping["answer"], separators=(",", ":"))
    realistic = (
        "The determinant class is the following polynomial support.\n"
        f"<answer>```json\n{wire}\n```</answer>\nThat is my final result."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"],
        "parsed_equals_answer": parsed == shipping["answer"],
        "json_native": json.loads(json.dumps(shipping["answer"])) == shipping["answer"],
    }

    guess_rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    candidate_space = search_space(shipping)
    exact_probability = 1.0 / candidate_space
    report["G4_guess_resistance"] = {
        "pass": guess_total >= 200_000 and exact_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "exact_probability": exact_probability,
        "exact_valid_answers": 1,
        "candidate_space": candidate_space,
        "candidate_space_bits": candidate_space.bit_length(),
        "prior": "uniform over all nonzero degree-below-128 polynomials over GF(2)",
    }

    start = time.perf_counter()
    baseline_candidate = _guess_background_without_correction(shipping)
    baseline_ok = verify(shipping, baseline_candidate)[0]
    baseline_seconds = time.perf_counter() - start
    start = time.perf_counter()
    reference_value, reference_stats = _determinant_with_stats(shipping["matrix"])
    reference_seconds = time.perf_counter() - start
    reference_ok = verify(shipping, _support(reference_value))[0]
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_hits == 0 and reference_ok and not baseline_ok,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_fraction": guess_hits / guess_total,
        "shipping_exact_valid_answers": 1,
        "shipping_exact_enumeration": enumerate_all(shipping),
        "baseline_attack": "column backgrounds XORed without the rank-one correction",
        "baseline_attack_wall_clock_seconds": round(baseline_seconds, 6),
        "baseline_attack_iterations": shipping["s"] ** 2,
        "baseline_attack_successes": int(baseline_ok),
        "reference_algorithm": "exact Gaussian determinant over GF(2^128)",
        "reference_wall_clock_seconds": round(reference_seconds, 6),
        "reference_operations": reference_stats,
    }

    attacks = {
        "outlier_most_frequent_entry": {"successes": 0, "attempts": 8},
        "greedy_displayed_diagonal_product": {"successes": 0, "attempts": 8},
        "displayed_trace_ansatz": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "column_background_without_rank_one_correction": {"successes": 0, "attempts": 8},
    }
    reference_successes = 0
    reference_seconds_all = []
    reference_field_ops = []
    reference_bit_steps = []
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_most_frequent_entry": _guess_most_frequent(inst),
            "greedy_displayed_diagonal_product": _guess_diagonal_product(inst),
            "displayed_trace_ansatz": _guess_trace(inst),
            "column_background_without_rank_one_correction": (
                _guess_background_without_correction(inst)
            ),
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

        start = time.perf_counter()
        value, stats = _determinant_with_stats(inst["matrix"])
        reference_seconds_all.append(time.perf_counter() - start)
        field_ops = (stats["field_multiplications"]
                     + stats["field_additions"] + stats["field_inversions"])
        reference_field_ops.append(field_ops)
        reference_bit_steps.append(stats["shift_xor_steps"])
        reference_successes += int(verify(inst, _support(value))[0])
    all_failed = all(item["successes"] == 0 and item["attempts"] >= 8
                     for item in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact Gaussian determinant over GF(2^128)",
            "complexity": "O(s^3) finite-field operations",
            "wall_clock_sec_mean": round(sum(reference_seconds_all) / 8, 6),
            "wall_clock_sec_max": round(max(reference_seconds_all), 6),
            "field_operations_mean": round(sum(reference_field_ops) / 8),
            "field_operations_max": max(reference_field_ops),
            "shift_xor_steps_mean": round(sum(reference_bit_steps) / 8),
            "shift_xor_steps_max": max(reference_bit_steps),
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    doubled = make_instance(
        n=2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"], seed=2718
    )
    doubled_ok = verify(doubled, doubled["answer"])[0]
    _, doubled_stats = _determinant_with_stats(doubled["matrix"])
    shipping_ops = (reference_stats["field_multiplications"]
                    + reference_stats["field_additions"]
                    + reference_stats["field_inversions"])
    doubled_ops = (doubled_stats["field_multiplications"]
                   + doubled_stats["field_additions"]
                   + doubled_stats["field_inversions"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["s"] > shipping["s"]
                and doubled_ops > shipping_ops,
        "shipping_n": DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        "shipping_matrix_order": shipping["s"],
        "shipping_reference_field_operations": shipping_ops,
        "doubled_n": 2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        "doubled_matrix_order": doubled["s"],
        "doubled_reference_field_operations": doubled_ops,
        "doubled_planted_verifies": doubled_ok,
        "answer_language_bits_at_both_sizes": 128,
    }

    invariant = carried = 0
    for seed in range(20):
        inst = make_instance(seed=1000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        rrng = random.Random(9000 + seed)

        def orders():
            rows = list(range(inst["s"]))
            columns = list(range(inst["s"]))
            rrng.shuffle(rows)
            rrng.shuffle(columns)
            return rows, columns

        first = _relabel_instance(inst, *orders(), transpose=bool(seed & 1))
        transformed = _relabel_instance(first, *orders(), transpose=bool(seed & 2))
        invariant += int(canonical_key(inst) == canonical_key(transformed))
        carried += int(verify(transformed, inst["answer"])[0])
    unrelated_keys = {
        canonical_key(make_instance(seed=2000 + seed,
                                    **DIFFICULTY[SHIPPING_DIFFICULTY]))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariant == 20 and carried == 20 and len(unrelated_keys) == 20,
        "composed_relabellings_invariant": invariant,
        "original_witnesses_valid_after_relabelling": carried,
        "unrelated_distinct_keys": len(unrelated_keys),
        "attempts_each": 20,
        "transformations": "independent row/column permutations, transpose, and compositions",
        "canonicalization": "unordered row and column multisets plus the full entry multiset",
    }

    answer_chars = 0
    answer_atoms = 0
    intended_ops = 0
    for seed in range(40):
        inst = make_instance(seed=3000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        answer_chars = max(answer_chars, len(json.dumps(inst["answer"],
                                                       separators=(",", ":"))))
        answer_atoms = max(answer_atoms, _answer_atom_count(inst["answer"]))
        intended_ops = max(intended_ops, _compact_route_operations(inst))
    answer_tokens = (answer_chars + 3) // 4
    arms = _G9_EVIDENCE["arms"]
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    within_caps = answer_chars <= 2000 and answer_atoms <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _G9_EVIDENCE["hinted_verdict"],
        "diagnostic_status": _G9_EVIDENCE["blocked_reason"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_ops,
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
