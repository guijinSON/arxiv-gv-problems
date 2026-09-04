"""Exact sparse approximation under a coherent tensor dictionary.

The certificate is generated first, the target is then obtained by exact matrix
multiplication, and every public interface is deterministic in ``(n, seed)``.
Only the Python standard library is required.  ``gvlib`` is imported when it is
available so this module has the same repository-local compatibility as the
other generators, but the small rational operations here use ``Fraction``.
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
import sys
import time
from fractions import Fraction


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # pragma: no cover - the standard-library path is complete
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "rational",
    "native_objects": [
        "normalized coherent dictionary over Q",
        "target vector over Q",
        "sparse coefficient vector over Q",
    ],
    "verification_operations": [
        "exact rational matrix-vector multiplication",
        "exact rational equality",
        "support-size and coefficient-bound checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "The shuffled dictionary is a mixed-radix tensor product, so undoing "
        "one small transform along each tensor axis replaces a dense solve."
    ),
    "hardness_basis": (
        "Track B: exact Gauss-Jordan elimination solves the square system in "
        "O(n^3); at the shipping preset the measured reference cost is filled "
        "by selftest (about 2e4 exact operations), while the tensor change of "
        "variables uses 189 exact operations but must first be recognized and "
        "executed without a CAS."
    ),
    "max_answer_tokens": 80,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 3, "k": 1, "coeff_num": 2, "coeff_den": 2},
    "easy": {"n": 9, "k": 2, "coeff_num": 5, "coeff_den": 5},
    "medium": {"n": 27, "k": 6, "coeff_num": 12, "coeff_den": 11},
    "hard": {"n": 27, "k": 9, "coeff_num": 31, "coeff_den": 29},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Regroup rows by their displayed coordinate tuples and invert the repeated "
    "three-way tensor transform one axis at a time."
)
PLACEBO_HINT = (
    "Organize every displayed rational carefully and check the selected "
    "dictionary atoms against all coordinates one line at a time."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "Exactly k distinct atom indices in increasing order, each carrying a "
        "nonzero reduced rational [p,q] with |p| <= coeff_num and "
        "1 <= q <= coeff_den."
    ),
    "bounds": {
        "max_terms": 9,
        "max_atom_index": 26,
        "max_abs_numerator": 31,
        "max_denominator": 29,
        "reduced": True,
    },
}

NOTES = r"""
Definition and paper boundary. Section 1, equation (1), defines Sparse as
choosing at most k dictionary atoms and coefficients minimizing the Euclidean
residual; it also requires normalized columns spanning the ambient space.
Theorem 1.7 proves worst-case inapproximability for PCP-reduction dictionaries
of any fixed positive coherence, while Theorem 1.8 gives a UGC-based regime
mu <= k^(-1+epsilon). Sections 2--4 make clear that those are specially reduced
Label-Cover instances, not arbitrary planted vectors. Consequently this module
does not make an average-case Track A claim for inverse-planted targets.

What makes it easy. Theorems 1.2--1.6 list OMP/OLS guarantees under coherence
O(1/k), and the final remarks explicitly leave other algorithmic regimes open.
More decisively for this construction, the dictionary is square and invertible,
so exact Gauss-Jordan elimination recovers its unique coefficient vector in
O(n^3). This is therefore declared Track B. The reference solver is reported,
not hidden among failing attacks.

Generation and compact route. A bounded sparse rational vector is sampled
first. The normalized dictionary is a row/column-shuffled tensor product of
the rational unit-column base B=(2J-I)/3 in every ternary axis; the target is
then multiplied out exactly. In a three-coordinate fibre, y_i=2S-x_i, hence
x_i=2(sum_j y_j)/5-y_i. Repeating that inverse on each axis costs 189 exact
arithmetic operations for n=27, versus a dense exact solve. Row and column
labels expose the coordinate system without exposing the sparse support.

Attack controls. All supports and coefficients, including plants, are drawn
from exactly the same bounded language as random guesses; every column has
the same norm and marginal entry multiset. The panel tests correlation
outliers with a restricted solve, full OMP with exact refitting, 256 uniform
restarts, and a plausible no-tool shortcut that performs only one tensor
inverse stage. Any success makes G6 fail. canonical_key ignores the answer,
seed, labels, and input order and hashes a weighted bipartite refinement of
the matrix/target incidence structure.
""".strip()


# Populated only after the three harness runs.  Keeping this data in the module
# makes selftest independent of the filesystem and avoids reading transcripts.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}


def _factor_radices(n: int) -> list[int]:
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    left = n
    factors = []
    while left % 2 == 0:
        factors.append(2)
        left //= 2
    while left % 3 == 0:
        factors.append(3)
        left //= 3
    if left != 1:
        raise ValueError("n must have no prime factors other than 2 and 3")
    return factors


def _mixed_digits(index: int, radices: list[int] | tuple[int, ...]) -> tuple[int, ...]:
    out = [0] * len(radices)
    for pos in range(len(radices) - 1, -1, -1):
        out[pos] = index % radices[pos]
        index //= radices[pos]
    return tuple(out)


def _mixed_index(digits: tuple[int, ...] | list[int],
                 radices: list[int] | tuple[int, ...]) -> int:
    value = 0
    for digit, radix in zip(digits, radices):
        value = value * radix + digit
    return value


def _base_entry(radix: int, row_digit: int, col_digit: int) -> int:
    if radix == 3:
        # B_3 = 2J-I: diagonal 1, off-diagonal 2, column norm 3.
        return 1 if row_digit == col_digit else 2
    if radix == 2:
        # Used only to support the G7 doubled size: rational unit columns after /5.
        return 3 if row_digit == col_digit else 4
    raise AssertionError("unsupported radix")


def _dictionary(radices: list[int]) -> tuple[list[list[int]], list[list[int]], int]:
    n = math.prod(radices)
    labels = [list(_mixed_digits(i, radices)) for i in range(n)]
    matrix = []
    for row in labels:
        line = []
        for col in labels:
            value = 1
            for radix, rd, cd in zip(radices, row, col):
                value *= _base_entry(radix, rd, cd)
            line.append(value)
        matrix.append(line)
    scale = math.prod(3 if d == 3 else 5 for d in radices)
    return matrix, labels, scale


def _frac_json(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _json_frac(raw) -> Fraction | None:
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        return None
    p, q = raw
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (p, q)):
        return None
    if q <= 0:
        return None
    return Fraction(p, q)


@functools.lru_cache(maxsize=None)
def _coefficient_values(max_num: int, max_den: int) -> tuple[Fraction, ...]:
    values = set()
    for q in range(1, max_den + 1):
        for p in range(1, max_num + 1):
            if math.gcd(p, q) == 1:
                values.add(Fraction(p, q))
                values.add(Fraction(-p, q))
    return tuple(sorted(values))


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a sparse rational coefficient vector and its target."""
    k = params.pop("k", None)
    coeff_num = params.pop("coeff_num", None)
    coeff_den = params.pop("coeff_den", None)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    radices = _factor_radices(n)
    for name, value in (("k", k), ("coeff_num", coeff_num),
                        ("coeff_den", coeff_den)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    if k > n:
        raise ValueError("k cannot exceed n")

    rng = random.Random(seed)
    coeff_pool = _coefficient_values(coeff_num, coeff_den)

    # The witness is the first random object sampled.  Everything below is built
    # around this canonical sparse vector.
    support = sorted(rng.sample(range(n), k))
    canonical_x = {j: rng.choice(coeff_pool) for j in support}

    canonical_matrix, labels, scale = _dictionary(radices)
    canonical_target = []
    for row in range(n):
        canonical_target.append(sum(
            (Fraction(canonical_matrix[row][j]) * canonical_x[j]
             for j in support), Fraction(0)))

    row_order = list(range(n))
    col_order = list(range(n))
    rng.shuffle(row_order)
    rng.shuffle(col_order)
    old_to_display = {old: new for new, old in enumerate(col_order)}

    display_matrix = [
        [canonical_matrix[old_row][old_col] for old_col in col_order]
        for old_row in row_order
    ]
    answer = sorted(
        [[old_to_display[j], _frac_json(canonical_x[j])] for j in support],
        key=lambda term: term[0],
    )
    coherence = Fraction(0)
    if 3 in radices:
        coherence = max(coherence, Fraction(8, 9))
    if 2 in radices:
        coherence = max(coherence, Fraction(24, 25))
    return {
        "n": n,
        "k": k,
        "coeff_num": coeff_num,
        "coeff_den": coeff_den,
        "radices": radices,
        "column_scale": scale,
        "coherence": _frac_json(coherence),
        "row_labels": [labels[i] for i in row_order],
        "atom_labels": [labels[j] for j in col_order],
        "matrix_numerators": display_matrix,
        "target_numerators": [_frac_json(canonical_target[i]) for i in row_order],
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the complete exact sparse-representation problem."""
    n = inst["n"]
    k = inst["k"]
    scale = inst["column_scale"]
    lines = [
        "EXACT SPARSE APPROXIMATION UNDER A COHERENT DICTIONARY",
        "",
        f"There are {n} coordinates and {n} dictionary atoms, numbered 0 through {n - 1}.",
        f"The normalized dictionary Phi is A/{scale}; every column has Euclidean norm 1.",
        f"Its coherence max_{{i!=j}} |<Phi_i,Phi_j>| is {inst['coherence'][0]}/{inst['coherence'][1]}.",
        f"The target is y=b/{scale}. Therefore Phi*x=y is exactly equivalent to A*x=b.",
        "A and b are given below without approximation. A rational [p,q] means p/q,",
        "where q is positive. Tuple labels are coordinate labels, not atom numbers;",
        "the displayed atom number is the zero-based column position in each matrix row.",
        "",
        f"Find exactly {k} distinct atoms and nonzero rational coefficients such that A*x=b.",
        "Atom indices must be in strictly increasing order. Each coefficient [p,q]",
        f"must be reduced, with 1 <= |p| <= {inst['coeff_num']} and 1 <= q <= {inst['coeff_den']}.",
        "Unlisted coefficients are zero. Repeated atom indices are forbidden.",
        "All interval bounds above are inclusive, and exact equality—not a tolerance—is required.",
        "",
        "TENSOR_RADICES " + " ".join(map(str, inst["radices"])),
        "ATOM_LABELS (displayed_index: mixed-radix tuple)",
    ]
    lines.extend(
        f"{j}:" + ",".join(map(str, label))
        for j, label in enumerate(inst["atom_labels"])
    )
    lines.extend([
        "END_ATOM_LABELS",
        "",
        "ROWS (coordinate_tuple | b_numerator | A_row_numerators)",
    ])
    for label, target, row in zip(inst["row_labels"], inst["target_numerators"],
                                  inst["matrix_numerators"]):
        label_text = ",".join(map(str, label))
        target_text = f"{target[0]}/{target[1]}"
        lines.append(f"{label_text} | {target_text} | " + " ".join(map(str, row)))
    lines.extend([
        "END_ROWS",
        "",
        "Give your final answer inside <answer></answer> tags as a JSON array of",
        f"exactly {k} terms [atom_index,[numerator,denominator]], in increasing",
        "atom-index order. Rationals use the same [p,q] encoding as above.",
        "Example: <answer>[[0,[1,1]]]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _answer_shape(value) -> bool:
    if not isinstance(value, list):
        return False
    for term in value:
        if not isinstance(term, list) or len(term) != 2:
            return False
        idx, coeff = term
        if isinstance(idx, bool) or not isinstance(idx, int):
            return False
        if not isinstance(coeff, list) or len(coeff) != 2:
            return False
        if any(isinstance(v, bool) or not isinstance(v, int) for v in coeff):
            return False
    return True


def parse_answer(text: str) -> object | None:
    """Parse the advertised JSON, tolerating prose, fences, and whitespace."""
    if not isinstance(text, str):
        return None
    bodies = list(reversed(_ANSWER_RE.findall(text)))
    bodies.extend(reversed(re.findall(r"```(?:json)?\s*(.*?)\s*```", text,
                                      re.I | re.S)))
    for body in bodies:
        try:
            value = json.loads(body.strip())
        except (TypeError, ValueError):
            continue
        if _answer_shape(value):
            return value
    decoder = json.JSONDecoder()
    for start in (i for i, ch in enumerate(text) if ch == "["):
        try:
            value, _ = decoder.raw_decode(text[start:])
        except (TypeError, ValueError):
            continue
        if _answer_shape(value):
            return value
    return None


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Check any bounded sparse rational solution; never inspect inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer must not be empty"
    if len(answer) != inst["k"]:
        return False, f"wrong number of terms: expected {inst['k']}, got {len(answer)}"

    indices = []
    coeffs = []
    for pos, term in enumerate(answer):
        if not isinstance(term, (list, tuple)) or len(term) != 2:
            return False, f"term {pos} must be [atom_index,[numerator,denominator]]"
        index, raw_coeff = term
        if isinstance(index, bool) or not isinstance(index, int):
            return False, f"term {pos} has a non-integer atom index"
        if index < 0 or index >= inst["n"]:
            return False, f"atom index {index} is outside the inclusive range 0..{inst['n'] - 1}"
        coeff = _json_frac(raw_coeff)
        if coeff is None:
            return False, f"term {pos} has a malformed rational coefficient"
        p, q = raw_coeff
        if p == 0:
            return False, f"term {pos} has zero coefficient"
        if math.gcd(abs(p), q) != 1:
            return False, f"term {pos} coefficient is not reduced"
        if abs(p) > inst["coeff_num"] or q > inst["coeff_den"]:
            return False, f"term {pos} coefficient exceeds the inclusive bounds"
        indices.append(index)
        coeffs.append(coeff)

    if len(set(indices)) != len(indices):
        return False, "duplicate atom index"
    if indices != sorted(indices):
        return False, "atom indices are not in strictly increasing order"

    for row_index, (row, raw_target) in enumerate(zip(
            inst["matrix_numerators"], inst["target_numerators"])):
        got = sum((Fraction(row[j]) * c for j, c in zip(indices, coeffs)),
                  Fraction(0))
        target = _json_frac(raw_target)
        if target is None:
            return False, "instance has a malformed target rational"
        if got != target:
            return False, (
                f"exact equation fails in row {row_index}: got "
                f"{got.numerator}/{got.denominator}, expected "
                f"{target.numerator}/{target.denominator}"
            )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the fully shape-aware certificate language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    support = sorted(rng.sample(range(inst["n"]), inst["k"]))
    pool = _coefficient_values(inst["coeff_num"], inst["coeff_den"])
    return [[j, _frac_json(rng.choice(pool))] for j in support]


def search_space(inst: dict) -> int | None:
    """Exact size of the finite language sampled by random_candidate."""
    values = len(_coefficient_values(inst["coeff_num"], inst["coeff_den"]))
    return math.comb(inst["n"], inst["k"]) * values ** inst["k"]


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the tiny demo language, with an explicit candidate cap."""
    space = search_space(inst)
    if space is None or space > 100_000:
        return None
    count = 0
    pool = _coefficient_values(inst["coeff_num"], inst["coeff_den"])
    for support in itertools.combinations(range(inst["n"]), inst["k"]):
        for coeffs in itertools.product(pool, repeat=inst["k"]):
            candidate = [[j, _frac_json(c)] for j, c in zip(support, coeffs)]
            if verify(inst, candidate)[0]:
                count += 1
    return count


def _digest_signature(value) -> str:
    return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()


def canonical_key(inst: dict) -> str:
    """Weighted bipartite refinement, invariant under row/column relabelling."""
    matrix = inst["matrix_numerators"]
    targets = [tuple(v) for v in inst["target_numerators"]]
    n_rows = len(matrix)
    n_cols = len(matrix[0]) if matrix else 0
    row_colors = [_digest_signature(("target", targets[i])) for i in range(n_rows)]
    col_colors = [_digest_signature(("atom",)) for _ in range(n_cols)]
    for _ in range(5):
        row_colors = [
            _digest_signature((targets[i], tuple(sorted(
                (matrix[i][j], col_colors[j]) for j in range(n_cols)))))
            for i in range(n_rows)
        ]
        col_colors = [
            _digest_signature(tuple(sorted(
                (matrix[i][j], row_colors[i]) for i in range(n_rows))))
            for j in range(n_cols)
        ]
    incidence = sorted(
        (row_colors[i], col_colors[j], matrix[i][j])
        for i in range(n_rows) for j in range(n_cols)
    )
    payload = (
        tuple(sorted(row_colors)), tuple(sorted(col_colors)), tuple(incidence),
        inst["k"], inst["coeff_num"], inst["coeff_den"], inst["column_scale"],
    )
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | None:
    """The named hard rung exhausts the G9-compliant intended-route window."""
    return None


def _solve_square(matrix, vector, counter=None):
    """Exact Gauss-Jordan solve, with arithmetic-operation instrumentation."""
    n = len(matrix)
    if n == 0 or len(vector) != n or any(len(row) != n for row in matrix):
        return None
    aug = [[Fraction(v) for v in row] + [Fraction(vector[i])]
           for i, row in enumerate(matrix)]
    ops = 0
    for col in range(n):
        pivot = next((r for r in range(col, n) if aug[r][col]), None)
        if pivot is None:
            return None
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        pv = aug[col][col]
        if pv != 1:
            for j in range(col, n + 1):
                aug[col][j] /= pv
                ops += 1
        for row in range(n):
            if row == col or aug[row][col] == 0:
                continue
            factor = aug[row][col]
            for j in range(col, n + 1):
                aug[row][j] -= factor * aug[col][j]
                ops += 2
    if counter is not None:
        counter[0] += ops
    return [aug[i][n] for i in range(n)]


def _candidate_from_dense(inst, dense):
    terms = []
    for j, value in enumerate(dense):
        value = Fraction(value)
        if value:
            terms.append([j, _frac_json(value)])
    return terms


def _reference_solve(inst, counter=None):
    matrix = inst["matrix_numerators"]
    target = [Fraction(*v) for v in inst["target_numerators"]]
    dense = _solve_square(matrix, target, counter)
    return None if dense is None else _candidate_from_dense(inst, dense)


def _restricted_fit(inst, support, counter=None):
    matrix = inst["matrix_numerators"]
    target = [Fraction(*v) for v in inst["target_numerators"]]
    k = len(support)
    gram = [[Fraction(0) for _ in range(k)] for _ in range(k)]
    rhs = [Fraction(0) for _ in range(k)]
    ops = 0
    for a, ca in enumerate(support):
        for row in range(inst["n"]):
            rhs[a] += matrix[row][ca] * target[row]
            ops += 2
        for b, cb in enumerate(support):
            for row in range(inst["n"]):
                gram[a][b] += matrix[row][ca] * matrix[row][cb]
                ops += 2
    local = [0]
    values = _solve_square(gram, rhs, local)
    ops += local[0]
    if counter is not None:
        counter[0] += ops
    if values is None:
        return None
    dense = [Fraction(0)] * inst["n"]
    for col, value in zip(support, values):
        dense[col] = value
    return _candidate_from_dense(inst, dense)


def _attack_correlation(inst, counter=None):
    matrix = inst["matrix_numerators"]
    target = [Fraction(*v) for v in inst["target_numerators"]]
    scores = []
    ops = 0
    for col in range(inst["n"]):
        dot = Fraction(0)
        for row in range(inst["n"]):
            dot += matrix[row][col] * target[row]
            ops += 2
        scores.append((abs(dot), -col, col))
    support = sorted(item[2] for item in sorted(scores, reverse=True)[:inst["k"]])
    local = [0]
    candidate = _restricted_fit(inst, support, local)
    if counter is not None:
        counter[0] += ops + local[0]
    return candidate


def _attack_omp(inst, counter=None):
    matrix = inst["matrix_numerators"]
    target = [Fraction(*v) for v in inst["target_numerators"]]
    residual = target[:]
    support = []
    ops = 0
    candidate = None
    for _ in range(inst["k"]):
        choices = []
        for col in range(inst["n"]):
            if col in support:
                continue
            dot = Fraction(0)
            for row in range(inst["n"]):
                dot += matrix[row][col] * residual[row]
                ops += 2
            choices.append((abs(dot), -col, col))
        support.append(max(choices)[2])
        support.sort()
        local = [0]
        candidate = _restricted_fit(inst, support, local)
        ops += local[0]
        dense = [Fraction(0)] * inst["n"]
        if candidate is not None:
            for col, raw in candidate:
                dense[col] = Fraction(*raw)
        for row in range(inst["n"]):
            fitted = sum((matrix[row][col] * dense[col] for col in support),
                         Fraction(0))
            ops += 2 * len(support)
            residual[row] = target[row] - fitted
            ops += 1
    if counter is not None:
        counter[0] += ops
    return candidate


def _canonical_target(inst):
    pairs = sorted((tuple(label), Fraction(*value)) for label, value in zip(
        inst["row_labels"], inst["target_numerators"]))
    return [value for _, value in pairs]


def _invert_axis(values, radices, axis, counter=None):
    out = list(values)
    n = len(values)
    d = radices[axis]
    ops = 0
    for index in range(n):
        digits = list(_mixed_digits(index, radices))
        if digits[axis] != 0:
            continue
        positions = []
        for digit in range(d):
            digits[axis] = digit
            positions.append(_mixed_index(digits, radices))
        ys = [values[p] for p in positions]
        if d == 3:
            total = ys[0] + ys[1] + ys[2]
            common = Fraction(2, 5) * total
            xs = [common - y for y in ys]
            ops += 7  # 2 adds, multiply/divide by 2/5, and 3 subtractions.
        else:
            xs = [Fraction(4 * ys[1] - 3 * ys[0], 7),
                  Fraction(4 * ys[0] - 3 * ys[1], 7)]
            ops += 8
        for p, x in zip(positions, xs):
            out[p] = x
    if counter is not None:
        counter[0] += ops
    return out


def _structured_solve(inst, stages=None, counter=None):
    values = _canonical_target(inst)
    radices = inst["radices"]
    use = len(radices) if stages is None else min(stages, len(radices))
    for axis in range(use):
        values = _invert_axis(values, radices, axis, counter)
    if use != len(radices):
        return values
    label_to_display = {tuple(label): j for j, label in enumerate(inst["atom_labels"])}
    dense = [Fraction(0)] * inst["n"]
    for canonical_index, value in enumerate(values):
        dense[label_to_display[_mixed_digits(canonical_index, radices)]] = value
    return _candidate_from_dense(inst, dense)


def _nearest_allowed(value, pool):
    return min(pool, key=lambda candidate: (abs(candidate - value), candidate))


def _attack_one_axis(inst, counter=None):
    partial = _structured_solve(inst, stages=1, counter=counter)
    chosen = sorted(range(inst["n"]), key=lambda j: (abs(partial[j]), -j),
                    reverse=True)[:inst["k"]]
    pool = _coefficient_values(inst["coeff_num"], inst["coeff_den"])
    label_to_display = {tuple(label): j for j, label in enumerate(inst["atom_labels"])}
    terms = []
    for canonical_index in chosen:
        display = label_to_display[_mixed_digits(canonical_index, inst["radices"])]
        terms.append([display, _frac_json(_nearest_allowed(partial[canonical_index], pool))])
    return sorted(terms)


def _reordered(inst, row_order, col_order, carry_answer=True):
    """Test helper: independently reorder rows and displayed atom numbers."""
    old_to_new = {old: new for new, old in enumerate(col_order)}
    transformed = {k: v for k, v in inst.items() if k != "answer"}
    transformed["row_labels"] = [inst["row_labels"][i] for i in row_order]
    transformed["target_numerators"] = [inst["target_numerators"][i] for i in row_order]
    transformed["atom_labels"] = [inst["atom_labels"][j] for j in col_order]
    transformed["matrix_numerators"] = [
        [inst["matrix_numerators"][i][j] for j in col_order]
        for i in row_order
    ]
    if carry_answer:
        transformed["answer"] = sorted(
            [[old_to_new[j], coeff] for j, coeff in inst["answer"]]
        )
    return transformed


def _answer_measure(inst):
    text = json.dumps(inst["answer"], separators=(",", ":"))
    atoms = sum(3 for _ in inst["answer"])
    return len(text), (len(text) + 3) // 4, atoms


def _count_transcript_arm(arm):
    data = G9_EVIDENCE[arm]
    return int(data["solved"]), int(data["attempts"])


def selftest() -> dict:
    """Run G1--G9 and return a fully JSON-serialisable evidence dictionary."""
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    g1_ok = 0
    g1_total = 0
    compact_ok = 0
    json_ok = 0
    for params in DIFFICULTY.values():
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            g1_total += 1
            if verify(inst, inst["answer"])[0]:
                g1_ok += 1
            if verify(inst, _structured_solve(inst))[0]:
                compact_ok += 1
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_ok += 1
    report["G1_planted_verifies"] = {
        "pass": g1_ok == g1_total == compact_ok == json_ok,
        "verified": g1_ok,
        "attempts": g1_total,
        "compact_route_verified": compact_ok,
        "json_roundtrips": json_ok,
    }

    ship = make_instance(seed=9137, **DIFFICULTY[SHIPPING_DIFFICULTY])
    original = ship["answer"]
    corruptions = {}
    cases = {
        "drop": original[:-1],
        "swap": [original[1], original[0]] + original[2:],
        "duplicate": [original[0], original[0]] + original[2:],
        "empty": [],
        "out_of_range": [[ship["n"], original[0][1]]] + original[1:],
    }
    for name, candidate in cases.items():
        ok, why = verify(ship, candidate)
        corruptions[name] = {"rejected": not ok, "reason": why}
    reasons = {entry["reason"] for entry in corruptions.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in corruptions.values()) and len(reasons) == 5,
        "corruptions": corruptions,
        "distinct_reasons": len(reasons),
    }

    encoded = json.dumps(original)
    prose = "I used exact rational arithmetic.\n```json\n" + encoded + "\n```\nDone."
    tagged = "Reasoning omitted. <answer>\n" + encoded + "\n</answer>"
    parsed_prose = parse_answer(prose)
    parsed_tagged = parse_answer(tagged)
    report["G3_round_trip"] = {
        "pass": parsed_prose == original and parsed_tagged == original,
        "model_style_cases": 2,
        "recovered": int(parsed_prose == original) + int(parsed_tagged == original),
    }

    guess_rng = random.Random(0x170202885)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        if verify(ship, random_candidate(ship, guess_rng))[0]:
            guess_hits += 1
    empirical = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": empirical < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "empirical_probability": empirical,
        "certificate_language_size": search_space(ship),
        "structure_aware": True,
    }

    attack_counter = [0]
    t0 = time.perf_counter()
    attack_answer = _attack_omp(ship, attack_counter)
    attack_wall = time.perf_counter() - t0
    reference_counter = [0]
    t1 = time.perf_counter()
    reference_answer = _reference_solve(ship, reference_counter)
    reference_wall = time.perf_counter() - t1
    report["G5_density_and_baseline"] = {
        "pass": empirical < 1e-6 and verify(ship, reference_answer)[0],
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_estimate": empirical,
        "demo_exact_solution_count": enumerate_all(
            make_instance(seed=0, **DIFFICULTY["demo"])),
        "strongest_failing_attack_wall_seconds": round(attack_wall, 6),
        "strongest_failing_attack_operations": attack_counter[0],
        "reference_wall_seconds": round(reference_wall, 6),
        "reference_operations": reference_counter[0],
    }

    attacks = {
        "correlation_outlier_restricted_fit": {"successes": 0, "attempts": 0,
                                                "operations": 0},
        "greedy_omp_exact_refit": {"successes": 0, "attempts": 0,
                                    "operations": 0},
        "random_restart_256": {"successes": 0, "attempts": 0,
                               "candidates": 0},
        "by_hand_one_tensor_axis": {"successes": 0, "attempts": 0,
                                    "operations": 0},
    }
    ref_success = 0
    ref_operations = 0
    ref_wall_total = 0.0
    for seed in range(100, 108):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, attack in (("correlation_outlier_restricted_fit", _attack_correlation),
                             ("greedy_omp_exact_refit", _attack_omp),
                             ("by_hand_one_tensor_axis", _attack_one_axis)):
            counter = [0]
            candidate = attack(inst, counter)
            attacks[name]["attempts"] += 1
            attacks[name]["operations"] += counter[0]
            if candidate is not None and verify(inst, candidate)[0]:
                attacks[name]["successes"] += 1
        restart_rng = random.Random(seed ^ 0xBAD5EED)
        found = False
        for _ in range(256):
            attacks["random_restart_256"]["candidates"] += 1
            if verify(inst, random_candidate(inst, restart_rng))[0]:
                found = True
                break
        attacks["random_restart_256"]["attempts"] += 1
        attacks["random_restart_256"]["successes"] += int(found)

        counter = [0]
        start = time.perf_counter()
        candidate = _reference_solve(inst, counter)
        ref_wall_total += time.perf_counter() - start
        ref_operations += counter[0]
        ref_success += int(candidate is not None and verify(inst, candidate)[0])
    all_failed = all(v["successes"] == 0 and v["attempts"] >= 8
                     for v in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_success == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact Gauss-Jordan elimination over Q",
            "complexity": "O(n^3) exact arithmetic",
            "wall_clock_sec_total_8": round(ref_wall_total, 6),
            "wall_clock_sec_mean": round(ref_wall_total / 8, 6),
            "operations_total_8": ref_operations,
            "operations_mean": ref_operations // 8,
            "solves": f"{ref_success}/8, as expected",
        },
    }

    double = make_instance(n=2 * ship["n"], seed=404,
                           k=min(2 * ship["k"], 2 * ship["n"]),
                           coeff_num=ship["coeff_num"], coeff_den=ship["coeff_den"])
    double_ok = verify(double, double["answer"])[0]
    report["G7_scales"] = {
        "pass": double_ok and double["n"] == 2 * ship["n"],
        "shipping_n": ship["n"],
        "doubled_n": double["n"],
        "doubled_matrix_entries": double["n"] ** 2,
        "doubled_plant_verifies": double_ok,
    }

    invariant = 0
    carried = 0
    distinct_keys = []
    for seed in range(20):
        inst = make_instance(seed=2000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        distinct_keys.append(key)
        rng = random.Random(seed)
        rows = list(range(inst["n"]))
        cols = list(range(inst["n"]))
        rng.shuffle(rows)
        rng.shuffle(cols)
        transformations = [
            (list(reversed(range(inst["n"]))), list(range(inst["n"]))),
            (list(range(inst["n"])), cols),
            (rows, list(reversed(cols))),
        ]
        for row_order, col_order in transformations:
            changed = _reordered(inst, row_order, col_order)
            invariant += int(canonical_key(changed) == key)
            carried += int(verify(changed, changed["answer"])[0])
    report["G8_canonical_key"] = {
        "pass": invariant == 60 and carried == 60 and len(set(distinct_keys)) == 20,
        "invariance_checks_passed": invariant,
        "invariance_checks_total": 60,
        "carried_witness_checks_passed": carried,
        "carried_witness_checks_total": 60,
        "unrelated_distinct": len(set(distinct_keys)),
        "unrelated_total": 20,
    }

    answer_chars = answer_tokens = answer_elements = 0
    for seed in range(20):
        measures = _answer_measure(make_instance(
            seed=3000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY]))
        answer_chars = max(answer_chars, measures[0])
        answer_tokens = max(answer_tokens, measures[1])
        answer_elements = max(answer_elements, measures[2])
    intended_counter = [0]
    intended_answer = _structured_solve(ship, counter=intended_counter)
    bare_solved, bare_attempts = _count_transcript_arm("bare")
    hinted_solved, hinted_attempts = _count_transcript_arm("hinted")
    placebo_solved, placebo_attempts = _count_transcript_arm("placebo")
    hint_delta = ((hinted_solved / hinted_attempts if hinted_attempts else 0.0)
                  - (placebo_solved / placebo_attempts if placebo_attempts else 0.0))
    hinted_hardened = G9_EVIDENCE["hinted_verdict"] == "hardened"
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_counter[0] <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps and verify(ship, intended_answer)[0],
        "arms": {
            "bare": {"solved": bare_solved, "attempts": bare_attempts},
            "hinted": {"solved": hinted_solved, "attempts": hinted_attempts},
            "placebo": {"solved": placebo_solved, "attempts": placebo_attempts},
        },
        "hinted_minus_placebo": hint_delta,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_counter[0],
    }

    report["all_passed"] = all(
        value.get("pass", False) for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
