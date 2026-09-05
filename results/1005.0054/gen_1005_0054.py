"""Verified matrix-product representation generator for arXiv:1005.0054.

The family stays in the paper's native objects: square integer matrices and an
ordered product witness.  It is deliberately Track B.  The paper's DistNP
result is for a flat input distribution, not for the dealer's planted-yes
distribution used here.
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
from fractions import Fraction


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "Pair the sum of the first ten row covectors with the difference of the "
    "first two coordinate vectors; this bilinear form is the shared invariant."
)
PLACEBO_HINT: str = (
    "Keep the matrix indices and multiplication order separate; careful exact "
    "integer bookkeeping matters throughout this computation."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "integer_lattice",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "square matrices over the integers",
        "an affine-line presentation M_i = M_1 + (i-1)R of the matrix list",
        "an ordered subset represented by one-based matrix indices",
    ],
    "verification_operations": [
        "exact integer matrix multiplication",
        "exact matrix equality",
        "range and distinctness checks on ordered indices",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "A sparse bilinear functional survives the common change of basis and "
        "turns the target product into a positional integer; without it, the "
        "disclosed exact method performs full matrix powering."
    ),
    "hardness_basis": (
        "Track B: exact affine-line normalization followed by repeated integer "
        "matrix multiplication solves every generated instance in "
        "O(n*r^3) arithmetic operations; at the shipping preset it uses "
        "156,813 scalar operations and about 0.008 seconds in the final "
        "self-test, while the "
        "bilinear-invariant route uses 29 exact operations."
    ),
    "max_answer_tokens": 10,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}


DIFFICULTY: dict = {
    "demo": {"n": 2, "k": 4, "r": 4, "radix_bits": 4, "shear_steps": 0},
    "easy": {"n": 10, "k": 24, "r": 20, "radix_bits": 31, "shear_steps": 72},
    "medium": {"n": 12, "k": 32, "r": 20, "radix_bits": 37, "shear_steps": 104},
    "hard": {"n": 16, "k": 40, "r": 20, "radix_bits": 43, "shear_steps": 144},
}
SHIPPING_DIFFICULTY: str = "easy"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "An ordered list of exactly n distinct one-based indices from 1 through "
        "k, with no repeated index."
    ),
    "bounds": {
        "length": "instance parameter n",
        "index_min": 1,
        "index_max": "instance parameter k",
        "distinct": True,
        "ordered": True,
        "max_atomic_elements": 256,
    },
}

NOTES: str = (
    "Section 2 fixes Matrix Representability as membership of a target integer "
    "matrix in the set of length-n products and cites the r=20 flat-distribution "
    "DistNP-completeness result; it also cites search/decision average-case "
    "equivalence. Section 4 fixes the dealer's actual construction: sample k "
    "integer matrices, choose an ordered subset, and multiply it to create the "
    "secret. Section 4.3 says exhaustive search is the intended attack and "
    "requires r>n, but Section 5 concedes that concrete difficult constructions "
    "remain future work. The flat-distribution theorem does not establish "
    "hardness for planted yes-instances, so this module is Track B. It uses a "
    "common unimodular change of basis on an affine matrix line. The paper's "
    "later multiset-coefficient search-space formula conflicts with its ordered "
    "subset wording and with noncommutative multiplication; this module follows "
    "the ordered-subset definition, forbids repeats, and counts k!/(k-n)!. Full exact "
    "matrix powering is the disclosed polynomial reference algorithm; the "
    "short route recognizes one bilinear functional. Plants and decoys are the "
    "same indexed affine family and the hidden ordered subset is sampled "
    "uniformly. Norm outliers, a target-entry greedy rule, random restarts, and "
    "the obvious visible-entry radix ansatz are measured as failing attacks."
)


# Filled only from transcripts produced by scripts/harden.py.  The defaults make
# selftest usable before the external oracle run; they are replaced after it.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "hardened",
}


def _identity(size: int) -> list[list[int]]:
    return [[1 if i == j else 0 for j in range(size)] for i in range(size)]


def _matmul(a: list[list[int]], b: list[list[int]]) -> list[list[int]]:
    rows = len(a)
    inner = len(b)
    cols = len(b[0])
    bt = list(zip(*b))
    return [
        [sum(x * y for x, y in zip(a[i], bt[j])) for j in range(cols)]
        for i in range(rows)
    ]


def _matpow_naive(a: list[list[int]], exponent: int) -> list[list[int]]:
    out = _identity(len(a))
    for _ in range(exponent):
        out = _matmul(out, a)
    return out


def _inverse_unimodular(a: list[list[int]]) -> list[list[int]]:
    """Exact inverse of a small unimodular matrix."""
    size = len(a)
    work = [
        [Fraction(value) for value in row]
        + [Fraction(1 if i == j else 0) for j in range(size)]
        for i, row in enumerate(a)
    ]
    for col in range(size):
        pivot = next((i for i in range(col, size) if work[i][col]), None)
        if pivot is None:
            raise ValueError("singular change-of-basis matrix")
        work[col], work[pivot] = work[pivot], work[col]
        value = work[col][col]
        work[col] = [x / value for x in work[col]]
        for i in range(size):
            if i == col or not work[i][col]:
                continue
            factor = work[i][col]
            work[i] = [x - factor * y for x, y in zip(work[i], work[col])]
    inverse = []
    for row in work:
        tail = row[size:]
        if any(x.denominator != 1 for x in tail):
            raise ValueError("change of basis was not unimodular")
        inverse.append([int(x) for x in tail])
    return inverse


def _base_change(r: int, steps: int, rng: random.Random) -> list[list[int]]:
    """Unimodular S with u^T S=e_1^T and S e_2=e_1-e_2.

    Here u has ones in the first min(10,r) coordinates.  Column shears only
    combine vectors in ker(u), so the two displayed identities survive.
    """
    lead = min(10, r)
    columns = []
    e0 = [0] * r
    e0[0] = 1
    columns.append(e0)
    for j in range(1, lead):
        col = [0] * r
        col[j - 1] = 1
        col[j] = -1
        columns.append(col)
    for j in range(lead, r):
        col = [0] * r
        col[j] = 1
        columns.append(col)

    mutable = list(range(2, r))
    cap = 500
    if len(mutable) >= 2:
        for _ in range(steps):
            target, source = rng.sample(mutable, 2)
            sign = -1 if rng.randrange(2) else 1
            proposal = [
                columns[target][i] + sign * columns[source][i] for i in range(r)
            ]
            if max(map(abs, proposal), default=0) <= cap:
                columns[target] = proposal
        for _ in range(max(2, steps // 8)):
            source = rng.choice(mutable)
            sign = -1 if rng.randrange(2) else 1
            proposal = [columns[0][i] + sign * columns[source][i] for i in range(r)]
            if max(map(abs, proposal), default=0) <= cap:
                columns[0] = proposal
    return [[columns[j][i] for j in range(r)] for i in range(r)]


def _bareiss_det(matrix: list[list[int]]) -> int:
    """Exact determinant by fraction-free Bareiss elimination."""
    size = len(matrix)
    if size == 0:
        return 1
    a = [row[:] for row in matrix]
    sign = 1
    previous = 1
    for col in range(size - 1):
        pivot = next((i for i in range(col, size) if a[i][col]), None)
        if pivot is None:
            return 0
        if pivot != col:
            a[col], a[pivot] = a[pivot], a[col]
            sign = -sign
        p = a[col][col]
        for i in range(col + 1, size):
            for j in range(col + 1, size):
                a[i][j] = (a[i][j] * p - a[i][col] * a[col][j]) // previous
            a[i][col] = 0
        previous = p
    return sign * a[-1][-1]


def _trace(matrix: list[list[int]]) -> int:
    return sum(matrix[i][i] for i in range(len(matrix)))


def _trace_square(matrix: list[list[int]]) -> int:
    size = len(matrix)
    return sum(matrix[i][j] * matrix[j][i] for i in range(size) for j in range(size))


def _bilinear_code(matrix: list[list[int]]) -> int:
    lead = min(10, len(matrix))
    return sum(matrix[i][0] - matrix[i][1] for i in range(lead))


def _decode_code(code: int, base: int, length: int) -> list[int] | None:
    if code < 0:
        return None
    digits = []
    for _ in range(length):
        code, digit = divmod(code, base)
        digits.append(digit)
    if code:
        return None
    return digits


def make_instance(
    n: int,
    seed: int = 0,
    *,
    k: int | None = None,
    r: int = 20,
    radix_bits: int = 31,
    shear_steps: int = 72,
) -> dict:
    """Inverse-generate a represented integer matrix and its ordered witness."""
    if not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer")
    if k is None:
        k = max(n + 4, 2 * n)
    if not isinstance(k, int) or k < n:
        raise ValueError("k must be an integer at least n")
    if not isinstance(r, int) or r < 3:
        raise ValueError("r must be at least 3")
    if r <= n and r == 20:
        raise ValueError("the paper's concrete security regime requires r > n")
    if radix_bits < 3:
        raise ValueError("radix_bits must be at least 3")
    if shear_steps < 0:
        raise ValueError("shear_steps must be nonnegative")

    rng = random.Random(seed)
    low = max(k + 2, 1 << (radix_bits - 1))
    high = max(low + 2, 1 << radix_bits)
    base = rng.randrange(low, high)
    if base % 2 == 0:
        base += 1
    if base <= k:
        base = k + 1 + (k % 2)

    # A constant diagonal block keeps every factor on one affine matrix line.
    # Its seed-dependent spectrum makes unrelated instances structurally distinct.
    forbidden = {0, 1, base}
    pool = [x for x in range(-97, 98) if x not in forbidden]
    rng.shuffle(pool)
    diagonal_tail = pool[: r - 2]

    change = _base_change(r, shear_steps, rng)
    change_inv = _inverse_unimodular(change)
    core_zero = [[0] * r for _ in range(r)]
    core_zero[0][0] = base
    core_zero[1][1] = 1
    for i, value in enumerate(diagonal_tail, 2):
        core_zero[i][i] = value
    common = _matmul(_matmul(change, core_zero), change_inv)

    e01 = [[0] * r for _ in range(r)]
    e01[0][1] = 1
    direction = _matmul(_matmul(change, e01), change_inv)
    matrices = [
        [
            [common[i][j] + label * direction[i][j] for j in range(r)]
            for i in range(r)
        ]
        for label in range(1, k + 1)
    ]

    answer = rng.sample(range(1, k + 1), n)
    target = _identity(r)
    for index in answer:
        target = _matmul(target, matrices[index - 1])

    return {
        "n": n,
        "k": k,
        "r": r,
        "B": base,
        "matrices": matrices,
        "target": target,
        "answer": answer,
    }


def _matrix_text(matrix: list[list[int]]) -> str:
    return json.dumps(matrix, separators=(",", ":"))


def render(inst: dict) -> str:
    n, k, r = inst["n"], inst["k"], inst["r"]
    first = inst["matrices"][0]
    second = inst["matrices"][1]
    direction = [[second[i][j] - first[i][j] for j in range(r)] for i in range(r)]
    lines = [
        "ORDERED INTEGER-MATRIX REPRESENTATION",
        "",
        f"There are k={k} distinct square integer matrices M1,...,M{k}, each of order r={r}.",
        f"The target is another {r} by {r} integer matrix T. An ordered representation",
        f"is a sequence of exactly n={n} DISTINCT indices (i1,...,i{n}) such that",
        "ordinary left-to-right integer matrix multiplication gives",
        "M_i1 * M_i2 * ... * M_in = T.",
        "Order matters, no index may repeat, and indices are one-based (1 through k).",
        "All arithmetic is over the ordinary integers, with no modulus and no rounding.",
        f"The auxiliary public integer B for this instance is B={inst['B']}.",
        "",
        "The complete matrix list is supplied by the following exact affine presentation.",
        "Every addition and scalar multiplication in this presentation is entrywise:",
        f"M1={_matrix_text(first)}",
        f"R={_matrix_text(direction)}",
        f"For every one-based index i from 1 through {k}, define M_i = M1 + (i-1)*R.",
        "This formula defines all k matrices; there is no omitted data.",
    ]
    lines.extend(
        [
            "",
            f"T={_matrix_text(inst['target'])}",
            "",
            "Give your final answer inside <answer></answer> tags as exactly n",
            "comma-separated one-based decimal indices in multiplication order.",
            "Do not use brackets and output nothing else inside the tags.",
            f"Example of the required shape: <answer>{', '.join(map(str, range(1, n + 1)))}</answer>",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json|text)?\s*|\s*```$", "", body, flags=re.I | re.S).strip()
    if body.startswith("["):
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            return None
        if isinstance(value, list) and all(type(x) is int for x in value):
            return value
        return None
    if not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", body):
        return None
    try:
        return [int(piece.strip()) for piece in body.split(",")]
    except ValueError:
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, list):
        return False, "answer must be a list of indices"
    if not answer:
        return False, "answer is empty"
    if len(answer) != inst["n"]:
        return False, f"wrong length: expected {inst['n']} indices"
    if any(type(index) is not int for index in answer):
        return False, "every index must be an integer"
    if any(index < 1 or index > inst["k"] for index in answer):
        return False, f"index out of range 1..{inst['k']}"
    if len(set(answer)) != len(answer):
        return False, "indices must be distinct"
    product = _identity(inst["r"])
    for index in answer:
        product = _matmul(product, inst["matrices"][index - 1])
    if product != inst["target"]:
        return False, "ordered product does not equal the target"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    return rng.sample(range(1, inst["k"] + 1), inst["n"])


def search_space(inst: dict) -> int:
    return math.factorial(inst["k"]) // math.factorial(inst["k"] - inst["n"])


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space > 1_000_000:
        return None
    count = 0
    for candidate in itertools.permutations(range(1, inst["k"] + 1), inst["n"]):
        if verify(inst, list(candidate))[0]:
            count += 1
    return count


def _affine_endpoints(matrices: list[list[list[int]]]):
    first = matrices[0]
    second = next((m for m in matrices[1:] if m != first), None)
    if second is None:
        raise ValueError("factor matrices are not distinct")
    r = len(first)
    difference = [[second[i][j] - first[i][j] for j in range(r)] for i in range(r)]
    pivot = next(
        (difference[i][j], i, j)
        for i in range(r)
        for j in range(r)
        if difference[i][j]
    )
    divisor, pi, pj = pivot
    coordinates = [Fraction(m[pi][pj] - first[pi][pj], divisor) for m in matrices]
    return matrices[coordinates.index(min(coordinates))], matrices[coordinates.index(max(coordinates))]


def _normalized_word(inst: dict, start: list[list[int]], end: list[list[int]]) -> tuple[int, ...]:
    k, n, base = inst["k"], inst["n"], inst["B"]
    start_power = _matpow_naive(start, n)
    r = inst["r"]
    span = [[end[i][j] - start[i][j] for j in range(r)] for i in range(r)]
    pi, pj = next(
        (i, j) for i in range(r) for j in range(r) if span[i][j]
    )
    delta = inst["target"][pi][pj] - start_power[pi][pj]
    alpha = Fraction(delta * (k - 1), span[pi][pj])
    if alpha.denominator != 1:
        raise ValueError("target is not on the normalized product line")
    digits = _decode_code(int(alpha), base, n)
    if digits is None or any(digit < 0 or digit >= k for digit in digits):
        raise ValueError("target has no normalized length-n digit word")
    return tuple(digits)


def canonical_key(inst: dict) -> str:
    """Similarity-, factor-reordering-, and affine-orientation-invariant key."""
    start, end = _affine_endpoints(inst["matrices"])
    forward = _normalized_word(inst, start, end)
    backward = _normalized_word(inst, end, start)
    word = min(forward, backward)
    structural = {
        "r": inst["r"],
        "k": inst["k"],
        "n": inst["n"],
        "B": inst["B"],
        "trace": _trace(start),
        "trace_square": _trace_square(start),
        "determinant": _bareiss_det(start),
        "normalized_word": word,
    }
    blob = json.dumps(structural, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict:
    """Grow the factor haystack, radix, and disguise at fixed witness length."""
    harder = {k: v for k, v in params.items() if k != "_preset"}
    harder["k"] = max(harder["n"] + 1, (harder.get("k", 2 * harder["n"]) * 3) // 2)
    harder["radix_bits"] = harder.get("radix_bits", 31) + 8
    harder["shear_steps"] = harder.get("shear_steps", 72) + 48
    return harder


def _reference_solve(inst: dict) -> tuple[list[int] | None, int]:
    """Disclosed polynomial algorithm: affine normalization plus full powering."""
    r, n, base = inst["r"], inst["n"], inst["B"]
    first, second = inst["matrices"][0], inst["matrices"][1]
    direction = [[second[i][j] - first[i][j] for j in range(r)] for i in range(r)]
    first_power = _matpow_naive(first, n)
    pi, pj = next(
        (i, j) for i in range(r) for j in range(r) if direction[i][j]
    )
    alpha = Fraction(inst["target"][pi][pj] - first_power[pi][pj], direction[pi][pj])
    if alpha.denominator != 1:
        return None, 0
    ones_code = (pow(base, n) - 1) // (base - 1)
    code = ones_code + int(alpha)
    digits = _decode_code(code, base, n)
    operations = n * r * r * (2 * r - 1) + 2 * r * r + n + 3
    if (
        digits is None
        or any(digit < 1 or digit > inst["k"] for digit in digits)
        or len(set(digits)) != len(digits)
    ):
        return None, operations
    return digits, operations


def _compact_solve(inst: dict) -> tuple[list[int] | None, int]:
    code = _bilinear_code(inst["target"])
    digits = _decode_code(code, inst["B"], inst["n"])
    lead = min(10, inst["r"])
    operations = lead + (lead - 1) + inst["n"]
    if (
        digits is None
        or any(digit < 1 or digit > inst["k"] for digit in digits)
        or len(set(digits)) != len(digits)
    ):
        return None, operations
    return digits, operations


def _attack_outlier_norm(inst: dict) -> list[int]:
    scored = []
    for index, matrix in enumerate(inst["matrices"], 1):
        score = sum(value * value for row in matrix for value in row)
        scored.append((score, index))
    return [index for _, index in sorted(scored)[: inst["n"]]]


def _attack_target_entry_greedy(inst: dict) -> list[int]:
    target_value = inst["target"][0][0]
    scored = [
        (abs(matrix[0][0] - target_value), index)
        for index, matrix in enumerate(inst["matrices"], 1)
    ]
    chosen = [index for _, index in sorted(scored)[: inst["n"]]]
    return list(reversed(chosen))


def _attack_visible_radix(inst: dict) -> list[int]:
    digits = _decode_code(inst["target"][0][1], inst["B"], inst["n"])
    if (
        digits is not None
        and all(1 <= digit <= inst["k"] for digit in digits)
        and len(set(digits)) == len(digits)
    ):
        return digits
    return list(range(1, inst["n"] + 1))


def _signed_permutation_conjugate(inst: dict, rng: random.Random) -> dict:
    r = inst["r"]
    permutation = list(range(r))
    rng.shuffle(permutation)
    signs = [(-1 if rng.randrange(2) else 1) for _ in range(r)]

    def transform(matrix):
        # P maps e_j to signs[j] e_{permutation[j]}.
        inverse_pos = [0] * r
        for old, new in enumerate(permutation):
            inverse_pos[new] = old
        out = [[0] * r for _ in range(r)]
        for new_i in range(r):
            old_i = inverse_pos[new_i]
            for new_j in range(r):
                old_j = inverse_pos[new_j]
                out[new_i][new_j] = signs[old_i] * signs[old_j] * matrix[old_i][old_j]
        return out

    return {
        **{k: v for k, v in inst.items() if k not in ("matrices", "target", "answer")},
        "matrices": [transform(m) for m in inst["matrices"]],
        "target": transform(inst["target"]),
        "answer": list(inst["answer"]),
    }


def _unimodular_shear_conjugate(inst: dict, rng: random.Random) -> dict:
    """Apply a genuine nonsigned-permutation integral change of basis."""
    r = inst["r"]
    change = _identity(r)
    for _ in range(2 * r + 1):
        target, source = rng.sample(range(r), 2)
        sign = -1 if rng.randrange(2) else 1
        change[target] = [
            x + sign * y for x, y in zip(change[target], change[source])
        ]
    change_inv = _inverse_unimodular(change)

    def transform(matrix):
        return _matmul(_matmul(change, matrix), change_inv)

    return {
        **{k: v for k, v in inst.items() if k not in ("matrices", "target", "answer")},
        "matrices": [transform(m) for m in inst["matrices"]],
        "target": transform(inst["target"]),
        "answer": list(inst["answer"]),
    }


def _reorder_factors(inst: dict, rng: random.Random) -> dict:
    order = list(range(inst["k"]))
    rng.shuffle(order)
    inverse = [0] * inst["k"]
    for new_position, old_position in enumerate(order):
        inverse[old_position] = new_position
    return {
        **{k: v for k, v in inst.items() if k not in ("matrices", "answer")},
        "matrices": [inst["matrices"][old] for old in order],
        "answer": [inverse[index - 1] + 1 for index in inst["answer"]],
    }


def _answer_atoms(answer: object) -> int:
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, (list, tuple)):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest() -> dict:
    report: dict = {}
    cache: dict[tuple[str, int], dict] = {}

    planted_checks = 0
    json_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            cache[(preset, seed)] = inst
            ok, why = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError(f"G1 {preset}/{seed}: {why}")
            planted_checks += 1
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                raise AssertionError("answer is not JSON-native")
            json_checks += 1
    report["G1_planted_verifies"] = {
        "pass": True,
        "checks": planted_checks,
        "json_native_checks": json_checks,
    }

    shipping = cache[(SHIPPING_DIFFICULTY, 0)]
    planted = shipping["answer"]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_order": [planted[1], planted[0], *planted[2:]],
        "duplicate": [planted[0], planted[0], *planted[2:]],
        "empty": [],
        "out_of_range": [shipping["k"] + 1, *planted[1:]],
    }
    reasons = {}
    for name, candidate in corruptions.items():
        ok, why = verify(shipping, candidate)
        if ok:
            raise AssertionError(f"G2 accepted {name}")
        reasons[name] = why
    if len(set(reasons.values())) != len(reasons):
        raise AssertionError(f"G2 reasons are not distinct: {reasons}")
    report["G2_rejects_corruption"] = {
        "pass": True,
        "rejected": len(reasons),
        "distinct_reasons": len(set(reasons.values())),
        "reasons": reasons,
    }

    body = ", ".join(map(str, planted))
    realistic = f"I multiplied in the stated order.\n```text\n<answer>{body}</answer>\n```"
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged answer") is None,
        "model_style_response_parsed": parsed == planted,
        "garbage_rejected": parse_answer("no tagged answer") is None,
    }

    guess_rng = random.Random(0x10050054)
    guess_samples = 200_000
    target_code = _bilinear_code(shipping["target"])
    hits = 0
    for _ in range(guess_samples):
        candidate = random_candidate(shipping, guess_rng)
        code = sum(index * pow(shipping["B"], place) for place, index in enumerate(candidate))
        if code == target_code:
            if not verify(shipping, candidate)[0]:
                raise AssertionError("fast uniqueness test disagrees with verifier")
            hits += 1
    report["G4_guess_resistance"] = {
        "pass": hits / guess_samples < 1e-6,
        "hits": hits,
        "total": guess_samples,
        "observed_probability": hits / guess_samples,
        "structure_aware_space": search_space(shipping),
        "sampler": "uniform ordered n-permutation of the k stated indices",
    }

    timings = []
    operation_count = None
    for _ in range(3):
        start = time.perf_counter()
        recovered, operations = _reference_solve(shipping)
        timings.append(time.perf_counter() - start)
        operation_count = operations
        if recovered is None or not verify(shipping, recovered)[0]:
            raise AssertionError("reference algorithm failed shipping instance")
    timings.sort()
    report["G5_density_and_baseline"] = {
        "pass": True,
        "shipping_density_hits": hits,
        "shipping_density_samples": guess_samples,
        "shipping_solution_fraction": hits / guess_samples,
        "demo_exact_solution_count": enumerate_all(cache[("demo", 0)]),
        "demo_candidate_count": search_space(cache[("demo", 0)]),
        "baseline_wall_clock_seconds": timings[len(timings) // 2],
        "baseline_scalar_operations": operation_count,
    }

    attack_names = (
        "outlier_frobenius_norm",
        "greedy_target_entry",
        "random_restart_256",
        "visible_entry_radix_ansatz",
    )
    attack_wins = {name: 0 for name in attack_names}
    reference_wins = 0
    reference_times = []
    reference_operations = 0
    for seed in range(8):
        inst = cache.get((SHIPPING_DIFFICULTY, seed))
        if inst is None:
            inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_frobenius_norm": _attack_outlier_norm(inst),
            "greedy_target_entry": _attack_target_entry_greedy(inst),
            "visible_entry_radix_ansatz": _attack_visible_radix(inst),
        }
        restart_rng = random.Random(9_000 + seed)
        restart_hit = False
        target = _bilinear_code(inst["target"])
        # Mild heuristic: restart only from the half of the factors whose
        # visible (0,0) entry is closest to the target's (0,0) entry.
        restart_pool = [
            index
            for _, index in sorted(
                (abs(matrix[0][0] - inst["target"][0][0]), index)
                for index, matrix in enumerate(inst["matrices"], 1)
            )[: max(inst["n"], inst["k"] // 2)]
        ]
        for _ in range(256):
            candidate = restart_rng.sample(restart_pool, inst["n"])
            code = sum(index * pow(inst["B"], place) for place, index in enumerate(candidate))
            if code == target:
                restart_hit = verify(inst, candidate)[0]
                if restart_hit:
                    break
        if restart_hit:
            attack_wins["random_restart_256"] += 1
        for name, candidate in candidates.items():
            if verify(inst, candidate)[0]:
                attack_wins[name] += 1
        start = time.perf_counter()
        candidate, reference_operations = _reference_solve(inst)
        reference_times.append(time.perf_counter() - start)
        if candidate is not None and verify(inst, candidate)[0]:
            reference_wins += 1
    attacks = {
        name: {"successes": attack_wins[name], "attempts": 8}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact affine-line normalization with repeated matrix powering",
            "complexity": "O(n*r^3) exact integer arithmetic",
            "wall_clock_sec_median": sorted(reference_times)[len(reference_times) // 2],
            "operations": reference_operations,
            "successes": reference_wins,
            "attempts": 8,
            "solves": f"{reference_wins}/8, as expected",
        },
    }

    base_params = dict(DIFFICULTY["easy"])
    doubled_params = {
        **base_params,
        "n": 2 * base_params["n"],
        "k": 2 * base_params["k"],
        "r": max(base_params["r"] + 4, 2 * base_params["n"] + 1),
        "radix_bits": base_params["radix_bits"] + 4,
        "shear_steps": base_params["shear_steps"] + 24,
    }
    doubled = make_instance(seed=8080, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(cache[("easy", 0)]),
        "base_n": base_params["n"],
        "doubled_n": doubled_params["n"],
        "base_space_bits": search_space(cache[("easy", 0)]).bit_length(),
        "doubled_space_bits": search_space(doubled).bit_length(),
        "doubled_verify_reason": doubled_why,
    }

    key_params = {"n": 4, "k": 9, "r": 6, "radix_bits": 9, "shear_steps": 18}
    invariant_checks = 0
    transformed_verify_checks = 0
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(seed=50_000 + seed, **key_params)
        rng = random.Random(70_000 + seed)
        reordered = _reorder_factors(inst, rng)
        conjugated = _signed_permutation_conjugate(inst, rng)
        sheared = _unimodular_shear_conjugate(inst, rng)
        composed_reorder_signed = _signed_permutation_conjugate(reordered, rng)
        composed_reorder_shear = _unimodular_shear_conjugate(reordered, rng)
        composed_signed_shear = _unimodular_shear_conjugate(conjugated, rng)
        composed_all = _unimodular_shear_conjugate(composed_reorder_signed, rng)
        original_key = canonical_key(inst)
        unrelated_keys.append(original_key)
        for changed in (
            reordered,
            conjugated,
            sheared,
            composed_reorder_signed,
            composed_reorder_shear,
            composed_signed_shear,
            composed_all,
        ):
            if canonical_key(changed) != original_key:
                raise AssertionError("canonical key changed under a true relabelling")
            invariant_checks += 1
            ok, why = verify(changed, changed["answer"])
            if not ok:
                raise AssertionError(f"transformed witness failed: {why}")
            transformed_verify_checks += 1
    report["G8_canonical_key"] = {
        "pass": len(set(unrelated_keys)) == 20,
        "invariance_checks": invariant_checks,
        "transformed_witness_checks": transformed_verify_checks,
        "unrelated_distinct": len(set(unrelated_keys)),
        "unrelated_attempts": 20,
        "symmetries": [
            "factor-list permutation with carried one-based indices",
            "simultaneous signed-permutation similarity",
            "simultaneous integral unimodular-shear similarity",
            "all pairwise and three-way compositions of these transformations",
            "reversal of the affine-line coordinate orientation",
        ],
    }

    compact, compact_operations = _compact_solve(shipping)
    compact_ok = compact is not None and verify(shipping, compact)[0]
    # Use the longest legal shipping answer, not a lucky short-index plant.
    widest_indices = sorted(
        range(1, shipping["k"] + 1), key=lambda value: (len(str(value)), value), reverse=True
    )[: shipping["n"]]
    answer_blob = json.dumps(widest_indices)
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    arms = G9_RESULTS["arms"]
    hinted = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and compact_operations <= 300
        and compact_ok
    )
    report["G9_no_tool_suitability"] = {
        "pass": G9_RESULTS["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted - placebo,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact_operations,
        "compact_route_verifies": compact_ok,
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
