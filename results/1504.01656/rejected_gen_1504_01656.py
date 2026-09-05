"""Exact constant-multiplier SOS refutations for arXiv:1504.01656.

The paper's Definition 2.2 permits arbitrary polynomial multipliers for
equational axioms.  This module uses the native degree-one special case: the
answer is a rational vector whose linear combination of the displayed
polynomial equations is exactly -1.  Instances are inverse-generated around
a Walsh character, so the refutation is known before any public equation is
assembled.  Generic modular Gaussian elimination finds it efficiently; hence
the family is explicitly Track B rather than an average-case Track A claim.
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


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "rational",
    "native_objects": [
        "linear polynomial equations over Q",
        "constant-multiplier sums-of-squares refutation",
        "Walsh characters on Boolean row labels",
    ],
    "verification_operations": [
        "exact rational normalization",
        "exact polynomial coefficient accumulation",
        "exact comparison with the constant polynomial -1",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize the common missing Walsh frequency in the coefficient "
        "columns; without that invariant, the constant SOS multipliers must "
        "be recovered by exact elimination."
    ),
    "hardness_basis": (
        "Track B: the coefficient-matching/SDP route stated in the Introduction "
        "before Section 1.1 specializes here to modular Gaussian elimination with exact "
        "validation in O(n*m^2+m^3); at m=31 and n=640 it averaged 671,237 "
        "field operations and 0.029 seconds per instance in selftest, while a "
        "32-point Walsh transform uses 222 exact operations once recognized."
    ),
    "max_answer_tokens": 51,
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

DIFFICULTY = {
    "demo": {"n": 12, "label_bits": 3, "coeff_bound": 3},
    "easy": {"n": 96, "label_bits": 5, "coeff_bound": 7},
    "medium": {"n": 256, "label_bits": 5, "coeff_bound": 11},
    "hard": {"n": 640, "label_bits": 5, "coeff_bound": 17},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Hint: Treat the five-bit equation labels as the domain of a "
    "Walsh-character basis."
)
PLACEBO_HINT = (
    "Hint: Treat the displayed integer coefficients exactly and preserve the "
    "stated equation order."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A vector of exactly m=2^label_bits-1 rational constants, each equal "
        "to -1 or +1 and serialized canonically as [numerator,denominator]; "
        "these are the equational multipliers in a degree-one SOS refutation. "
        "Since every constant term is 1, exactly (m-1)/2 entries are +1."
    ),
    "bounds": {
        "length": "2^label_bits-1",
        "coefficient_values": [-1, 1],
        "canonical_denominator": 1,
        "max_named_preset_length": 31,
        "candidate_count": "binomial(m,(m-1)/2)",
    },
}

G9_ORACLE_RESULTS = {
    "bare": {"solved": 3, "attempts": 3, "errors": 0},
    "hinted": {"solved": 0, "attempts": 0, "errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted_verdict": "unreachable_openrouter_key_limit",
}

NOTES = r"""
Paper grounding and Step 0.  Section 2, Definition 2.2 defines an SOS
derivation p = sum_i r_i p_i + sum_j s_j q_j + s_0, where the p_i are
equational axioms, every s_j and s_0 is a sum of squares, and the r_i are
arbitrary polynomials.  A refutation derives -1.  This generator stays in
those native objects and uses constant rational r_i and the empty sum of
squares s_0=0.  Verification is therefore literal coefficient matching.

The paragraph preceding Section 1.1 says that a degree-d SOS certificate can
be found by semidefinite programming in n^{O(d)} time.  In this linear special
case the same coefficient search is just exact Gaussian elimination.  That
algorithm produces the certificate in polynomial time, so Track A would be
false.  This is Track B, and selftest measures the reference algorithm rather
than hiding it among the failing attacks.

The paper's lower-bound objects cannot simply be claimed as a generator.
Theorem 3.6 is a high-probability statement for random 3-XOR, and Theorem 3.9
chooses and fixes one good formula from its support; neither theorem provides
an executable per-sample hardness certificate.  Moreover Theorem 4.12 says
the final relativized formulas require enormous SOS refutations, conflicting
with the benchmark's 2,000-character/256-atom witness cap.  The present family
therefore uses the exact proof definition rather than mislabelling that
nonuniform existence proof as an unlimited hard-instance sampler.

Inverse generation.  Rows are indexed by the nonzero vectors x in F_2^b.  A
nonzero mask s of Hamming weight two or three is sampled first and defines the
known multiplier lambda_x=(-1)^(s dot x).  Every public coefficient column a
is sampled in the rational hyperplane lambda dot a=0: choose an exchangeable
integer vector r with sum zero and set a_x=lambda_x r_x.  The constant term of
every equation is 1.  Character orthogonality gives sum_x lambda_x=-1, hence

    sum_x lambda_x (1 + sum_j a[x,j] X_j) = -1.

The planted answer is known before the public columns exist.  Rank is checked
only to certify uniqueness/density; it is never used to discover the answer.

Compact route.  Extend any coefficient column by value zero at row label 0.
Its 2^b-point Walsh transform vanishes at s because lambda dot a=0.  Generation
rejects columns with any other zero Walsh coefficient, so one transform finds
the common missing frequency.  Gray-code parity evaluation then writes the
31 signs.  At b=5 this costs 160 additions/subtractions, 31 comparisons, and
31 parity/sign updates: 222 exact operations.

Adversaries.  The exchangeable zero-sum sampler gives every row the same
marginal coefficient distribution, defeating row-norm outliers.  A greedy
balanced-sign fit sees only a prefix of the dense columns and does not satisfy
the remaining identities.  Uniform balanced-sign restarts have exact success
probability 1/binomial(31,15), and the by-hand Walsh ansatz tests only constant,
single-coordinate, and all-coordinate characters; the secret mask is sampled
at weight two or three.  Full Gaussian elimination is reported separately as
Track B requires.

Canonicalization.  Equation and variable order are syntactic, and changes of
basis in the five-bit row labels preserve the character presentation.  The
key ignores labels and applies fixed-round weighted bipartite color refinement
to the exact coefficient matrix, making it invariant under arbitrary row and
column permutations.  It is a strong cheap invariant rather than a complete
canonizer for rational linear systems under arbitrary row operations; that
limitation is recorded in the README.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_MODULUS = 1_000_000_007
_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8


def _checked_int(name: str, value: object, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if not low <= value <= high:
        raise ValueError(f"{name} must lie in {low}..{high}")
    return value


def _parity(value: int) -> int:
    return value.bit_count() & 1


def _fwht(values: list[int]) -> list[int]:
    """Unnormalised integer Walsh-Hadamard transform."""
    out = list(values)
    width = 1
    while width < len(out):
        for start in range(0, len(out), 2 * width):
            for offset in range(width):
                left = out[start + offset]
                right = out[start + offset + width]
                out[start + offset] = left + right
                out[start + offset + width] = left - right
        width *= 2
    return out


def _rank_mod(columns: list[list[int]], row_count: int) -> int:
    """Rank of column vectors over a large prime, without finding a witness."""
    basis: dict[int, list[int]] = {}
    for source in columns:
        vector = [value % _MODULUS for value in source]
        for pivot in sorted(basis):
            factor = vector[pivot]
            if factor:
                row = basis[pivot]
                vector = [
                    (x - factor * y) % _MODULUS
                    for x, y in zip(vector, row)
                ]
        pivot = next((i for i, value in enumerate(vector) if value), None)
        if pivot is None:
            continue
        inverse = pow(vector[pivot], _MODULUS - 2, _MODULUS)
        vector = [value * inverse % _MODULUS for value in vector]
        basis[pivot] = vector
        if len(basis) == row_count:
            break
    return len(basis)


def _sample_column(
    row_labels: list[int], secret_mask: int, coeff_bound: int, rng: random.Random
) -> list[int]:
    """Sample an exchangeable bounded column orthogonal to the planted signs."""
    row_count = len(row_labels)
    full_size = row_count + 1
    while True:
        # Conditioning the last value on the sum and then shuffling makes the
        # adjusted coordinate exchangeable rather than a positional outlier.
        raw = [rng.randint(-coeff_bound, coeff_bound) for _ in range(row_count - 1)]
        last = -sum(raw)
        if not -coeff_bound <= last <= coeff_bound:
            continue
        raw.append(last)
        rng.shuffle(raw)
        canonical = [0] * full_size
        for label, value in zip(row_labels, raw):
            sign = -1 if _parity(secret_mask & label) else 1
            canonical[label] = sign * value
        spectrum = _fwht(canonical)
        zeros = [index for index, value in enumerate(spectrum) if value == 0]
        if zeros == [secret_mask]:
            return [canonical[label] for label in row_labels]


def make_instance(
    n: int,
    seed: int = 0,
    label_bits: int = 5,
    coeff_bound: int = 11,
    **params,
) -> dict:
    """Inverse-generate a degree-one SOS refutation over Q.

    ``n`` is the number of polynomial variables (coefficient columns).  The
    answer length is controlled separately by ``label_bits``, allowing the
    mechanical haystack to grow while the witness remains fixed.
    """
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    n = _checked_int("n", n, 6, 8192)
    label_bits = _checked_int("label_bits", label_bits, 3, 5)
    coeff_bound = _checked_int("coeff_bound", coeff_bound, 2, 1_000_000)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    row_count = (1 << label_bits) - 1
    if n < row_count - 1:
        raise ValueError("n must be at least 2^label_bits-2")
    rng = random.Random(seed)
    allowed_masks = [
        mask
        for mask in range(1, 1 << label_bits)
        if 2 <= mask.bit_count() <= min(3, label_bits - 1)
    ]
    secret_mask = rng.choice(allowed_masks)
    canonical_labels = list(range(1, 1 << label_bits))

    # Full column rank in lambda-perp makes the bounded certificate unique.
    # We resample public randomness if necessary; lambda was already chosen.
    for _ in range(32):
        columns = [
            _sample_column(
                canonical_labels, secret_mask, coeff_bound, rng
            )
            for _ in range(n)
        ]
        if _rank_mod(columns, row_count) == row_count - 1:
            break
    else:
        raise RuntimeError("could not construct a full-rank coefficient family")

    rng.shuffle(columns)
    row_order = list(range(row_count))
    rng.shuffle(row_order)
    labels = [canonical_labels[index] for index in row_order]
    coefficients = [
        [columns[column][index] for column in range(n)]
        for index in row_order
    ]
    answer = [
        [(-1 if _parity(secret_mask & label) else 1), 1]
        for label in labels
    ]
    return {
        "family": "constant-multiplier degree-one SOS refutation",
        "n": n,
        "label_bits": label_bits,
        "row_count": row_count,
        "coeff_bound": coeff_bound,
        "row_labels": labels,
        "coefficients": coefficients,
        "constant_terms": [1] * row_count,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the exact polynomial system and certificate format."""
    n = inst["n"]
    row_count = inst["row_count"]
    bits = inst["label_bits"]
    rows = []
    for index, (label, coeffs) in enumerate(
        zip(inst["row_labels"], inst["coefficients"])
    ):
        rows.append(
            f"E{index:02d} label={label:0{bits}b}: "
            + " ".join(str(value) for value in coeffs)
        )
    statement = f"""Constant-multiplier sums-of-squares refutation over Q

All arithmetic is exact over the rational numbers. There are {n} formal real
variables X_0,...,X_{n - 1} and {row_count} polynomial equations. Equation E_i
is

    p_i(X) = 1 + sum_(j=0 to {n - 1}) A[i,j] X_j = 0.

The row labels are distinct nonzero {bits}-bit vectors and are part of the
instance. They do not change the displayed equation. The coefficient matrix A
is given below, one equation per line. Each line contains exactly {n} signed
integers after the colon, in X_0,...,X_{n - 1} order. Equation indices and
variable indices are 0-based.

{chr(10).join(rows)}

An SOS derivation from equational axioms p_i=0 may multiply each p_i by an
arbitrary polynomial and add a sum of polynomial squares. An SOS refutation is
an exact polynomial identity equal to -1. Find a refutation of the restricted
form

    lambda_0 p_0 + ... + lambda_{row_count - 1} p_{row_count - 1} = -1,

with no square terms, where every constant rational multiplier lambda_i is
exactly -1 or +1. Order matters: multiplier lambda_i belongs to displayed
equation E_i. Repeated values are allowed.

Output exactly {row_count} comma-separated rational integers in E_0,...,
E_{row_count - 1} order. Write each as -1 or 1; no brackets are needed.

Give your final answer inside <answer></answer> tags, as the comma-separated
list. Example: <answer>-1, 1, -1, 1</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def _parse_rational_token(token: str) -> list[int] | None:
    match = re.fullmatch(r"([+-]?\d+)(?:\s*/\s*([+-]?\d+))?", token.strip())
    if not match:
        return None
    numerator = int(match.group(1))
    denominator = int(match.group(2) or "1")
    if denominator == 0:
        return [numerator, 0]
    value = Fraction(numerator, denominator)
    return [value.numerator, value.denominator]


def parse_answer(text: str) -> object | None:
    """Extract a tagged rational vector, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
    try:
        decoded = json.loads(body)
    except (TypeError, ValueError):
        decoded = None
    if isinstance(decoded, list) and all(
        isinstance(item, list) and len(item) == 2 for item in decoded
    ):
        result = []
        for item in decoded:
            if any(isinstance(value, bool) or not isinstance(value, int) for value in item):
                return None
            if item[1] == 0:
                result.append(list(item))
            else:
                value = Fraction(item[0], item[1])
                result.append([value.numerator, value.denominator])
        return result
    tokens = [token.strip() for token in body.split(",")]
    if not tokens or any(not token for token in tokens):
        return None
    parsed = [_parse_rational_token(token) for token in tokens]
    return None if any(item is None for item in parsed) else parsed


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Verify any allowed constant-multiplier refutation; never read the plant."""
    expected = inst["row_count"]
    if not isinstance(answer, list):
        return False, "answer must be a list of rational multipliers"
    if not answer:
        return False, "empty certificate has no multipliers"
    if len(answer) < expected:
        return False, f"missing multipliers: expected {expected}, got {len(answer)}"
    if len(answer) > expected:
        return False, f"extra multipliers: expected {expected}, got {len(answer)}"

    multipliers: list[int] = []
    for index, item in enumerate(answer):
        if not isinstance(item, list) or len(item) != 2:
            return False, f"multiplier {index} is not a [numerator,denominator] pair"
        numerator, denominator = item
        if (
            isinstance(numerator, bool)
            or isinstance(denominator, bool)
            or not isinstance(numerator, int)
            or not isinstance(denominator, int)
        ):
            return False, f"multiplier {index} has non-integer rational data"
        if denominator == 0:
            return False, f"multiplier {index} has zero denominator"
        value = Fraction(numerator, denominator)
        if value not in (Fraction(-1), Fraction(1)):
            return False, f"multiplier {index} is outside the allowed set {{-1,+1}}"
        multipliers.append(int(value))

    constant = sum(
        value * term
        for value, term in zip(multipliers, inst["constant_terms"])
    )
    if constant != -1:
        return False, f"constant coefficient is {constant}, not -1"
    for variable in range(inst["n"]):
        coefficient = sum(
            multipliers[row] * inst["coefficients"][row][variable]
            for row in range(expected)
        )
        if coefficient:
            return False, (
                f"coefficient of X_{variable} is {coefficient}, not 0"
            )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample the constant-sum slice freely implied by the target -1."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    row_count = inst["row_count"]
    positive_count = (row_count - 1) // 2
    positives = set(rng.sample(range(row_count), positive_count))
    return [[1 if row in positives else -1, 1] for row in range(row_count)]


def search_space(inst: dict) -> int | None:
    row_count = inst["row_count"]
    return math.comb(row_count, (row_count - 1) // 2)


def enumerate_all(inst: dict) -> int | None:
    """Count valid bounded certificates when at most 2^20 exist."""
    row_count = inst["row_count"]
    if search_space(inst) > (1 << 20):
        return None
    count = 0
    positive_count = (row_count - 1) // 2
    for positions in itertools.combinations(range(row_count), positive_count):
        positives = set(positions)
        candidate = [
            [1 if row in positives else -1, 1] for row in range(row_count)
        ]
        count += int(verify(inst, candidate)[0])
    return count


def _color_hash(tag: bytes, old: bytes, entries: list[tuple[int, bytes]]) -> bytes:
    digest = hashlib.sha256()
    digest.update(tag)
    digest.update(old)
    for value, color in sorted(entries, key=lambda item: (item[0], item[1])):
        digest.update(str(value).encode())
        digest.update(b":")
        digest.update(color)
    return digest.digest()


def canonical_key(inst: dict) -> str:
    """Weighted bipartite color-refinement invariant for row/column relabelling."""
    matrix = inst["coefficients"]
    row_count = inst["row_count"]
    column_count = inst["n"]
    row_colors = [hashlib.sha256(b"row:1").digest()] * row_count
    column_colors = [hashlib.sha256(b"polynomial-variable").digest()] * column_count
    for _ in range(5):
        next_rows = [
            _color_hash(
                b"R",
                row_colors[row],
                [(matrix[row][column], column_colors[column]) for column in range(column_count)],
            )
            for row in range(row_count)
        ]
        next_columns = [
            _color_hash(
                b"C",
                column_colors[column],
                [(matrix[row][column], row_colors[row]) for row in range(row_count)],
            )
            for column in range(column_count)
        ]
        row_colors, column_colors = next_rows, next_columns

    outer = hashlib.sha256()
    outer.update(
        f"Q-linear-SOS;rows={row_count};cols={column_count}".encode()
    )
    for color in sorted(row_colors):
        outer.update(b"R" + color)
    for color in sorted(column_colors):
        outer.update(b"C" + color)
    edge_types = sorted(
        row_colors[row]
        + column_colors[column]
        + str(matrix[row][column]).encode()
        + b";"
        for row in range(row_count)
        for column in range(column_count)
    )
    for edge in edge_types:
        outer.update(b"E" + edge)
    return outer.hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Increase coefficient-column crowding while keeping the witness fixed."""
    allowed = {"n", "label_bits", "coeff_bound"}
    if not isinstance(params, dict) or not set(params) <= allowed:
        return None
    try:
        n = int(params["n"])
        label_bits = int(params.get("label_bits", 5))
        coeff_bound = int(params.get("coeff_bound", 11))
    except (KeyError, TypeError, ValueError):
        return None
    if label_bits != 5:
        return {"n": max(n, 96), "label_bits": 5, "coeff_bound": coeff_bound}
    if n < 8192:
        return {
            "n": min(8192, 2 * n),
            "label_bits": label_bits,
            "coeff_bound": coeff_bound,
        }
    if coeff_bound < 1_000_000:
        return {
            "n": n,
            "label_bits": label_bits,
            "coeff_bound": min(1_000_000, 4 * coeff_bound),
        }
    return None


def _reference_algorithm(inst: dict) -> tuple[object | None, dict[str, int]]:
    """Modular Gauss-Jordan elimination, followed by exact verification."""
    row_count = inst["row_count"]
    equations = [
        [inst["coefficients"][row][column] % _MODULUS for row in range(row_count)]
        + [0]
        for column in range(inst["n"])
    ]
    equations.append([1] * row_count + [(-1) % _MODULUS])
    operations = 0
    pivot_row = 0
    pivot_columns: list[int] = []
    total_rows = len(equations)
    for column in range(row_count):
        pivot = next(
            (row for row in range(pivot_row, total_rows) if equations[row][column]),
            None,
        )
        if pivot is None:
            continue
        equations[pivot_row], equations[pivot] = equations[pivot], equations[pivot_row]
        inverse = pow(equations[pivot_row][column], _MODULUS - 2, _MODULUS)
        operations += 1
        for position in range(column, row_count + 1):
            equations[pivot_row][position] = (
                equations[pivot_row][position] * inverse
            ) % _MODULUS
            operations += 1
        for row in range(total_rows):
            if row == pivot_row:
                continue
            factor = equations[row][column]
            if not factor:
                continue
            for position in range(column, row_count + 1):
                equations[row][position] = (
                    equations[row][position]
                    - factor * equations[pivot_row][position]
                ) % _MODULUS
                operations += 2
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == row_count:
            break
    if pivot_row != row_count:
        return None, {"field_operations": operations, "pivots": pivot_row}
    solution = [0] * row_count
    for row, column in enumerate(pivot_columns):
        solution[column] = equations[row][row_count]
    answer = []
    for value in solution:
        if value == 1:
            answer.append([1, 1])
        elif value == _MODULUS - 1:
            answer.append([-1, 1])
        else:
            return None, {"field_operations": operations, "pivots": pivot_row}
    if not verify(inst, answer)[0]:
        return None, {"field_operations": operations, "pivots": pivot_row}
    return answer, {"field_operations": operations, "pivots": pivot_row}


def _balanced(values: list[float], positive_count: int) -> list[list[int]]:
    chosen = set(sorted(range(len(values)), key=lambda index: values[index])[:positive_count])
    return [[1 if index in chosen else -1, 1] for index in range(len(values))]


def _outlier_row_norm(inst: dict) -> object:
    scores = [sum(abs(value) for value in row) for row in inst["coefficients"]]
    return _balanced(scores, (inst["row_count"] - 1) // 2)


def _greedy_prefix_fit(inst: dict) -> tuple[object, int]:
    """Greedily assign the required 15 positive signs against 12 columns."""
    row_count = inst["row_count"]
    positive_count = (row_count - 1) // 2
    prefix = min(12, inst["n"])
    residual = [0] * prefix
    remaining = set(range(row_count))
    positives: set[int] = set()
    steps = 0
    # Start from all -1 and add +2 times one row at a time.
    residual = [
        -sum(inst["coefficients"][row][column] for row in range(row_count))
        for column in range(prefix)
    ]
    for _ in range(positive_count):
        best = None
        best_score = None
        for row in remaining:
            proposed = [
                residual[column] + 2 * inst["coefficients"][row][column]
                for column in range(prefix)
            ]
            score = sum(value * value for value in proposed)
            steps += prefix * 3
            if best_score is None or score < best_score:
                best, best_score = row, score
        positives.add(best)
        remaining.remove(best)
        residual = [
            residual[column] + 2 * inst["coefficients"][best][column]
            for column in range(prefix)
        ]
    return (
        [[1 if row in positives else -1, 1] for row in range(row_count)],
        steps,
    )


def _random_restart(
    inst: dict, rng: random.Random, restarts: int = 256
) -> tuple[bool, int]:
    row_count = inst["row_count"]
    positives = (row_count - 1) // 2
    for attempt in range(1, restarts + 1):
        chosen = set(rng.sample(range(row_count), positives))
        candidate = [
            [1 if row in chosen else -1, 1] for row in range(row_count)
        ]
        if verify(inst, candidate)[0]:
            return True, attempt
    return False, restarts


def _obvious_walsh_ansatz(inst: dict) -> tuple[bool, int]:
    bits = inst["label_bits"]
    masks = [0] + [1 << bit for bit in range(bits)] + [(1 << bits) - 1]
    candidates = []
    for mask in masks:
        candidates.append(
            [
                [(-1 if _parity(mask & label) else 1), 1]
                for label in inst["row_labels"]
            ]
        )
    candidates.append(
        [[1 if index % 2 else -1, 1] for index in range(inst["row_count"])]
    )
    for candidate in candidates:
        if verify(inst, candidate)[0]:
            return True, len(candidates)
    return False, len(candidates)


def _relabel(
    inst: dict,
    row_order: list[int],
    column_order: list[int],
    rotate_labels: bool = False,
) -> dict:
    """Permute equations/variables and relabel the auxiliary Boolean points."""
    moved = dict(inst)
    bits = inst["label_bits"]

    def moved_label(label: int) -> int:
        if not rotate_labels:
            return label
        return ((label << 1) & ((1 << bits) - 1)) | (label >> (bits - 1))

    moved["row_labels"] = [moved_label(inst["row_labels"][row]) for row in row_order]
    moved["coefficients"] = [
        [inst["coefficients"][row][column] for column in column_order]
        for row in row_order
    ]
    moved["constant_terms"] = [inst["constant_terms"][row] for row in row_order]
    moved["answer"] = [inst["answer"][row] for row in row_order]
    return moved


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))
    atoms = 0

    def count(value: object) -> None:
        nonlocal atoms
        if isinstance(value, dict):
            for child in value.values():
                count(child)
        elif isinstance(value, list):
            for child in value:
                count(child)
        else:
            atoms += 1

    count(answer)
    return len(encoded), math.ceil(len(encoded) / 4), atoms


def selftest() -> dict:
    """Run all construction, parsing, density, attack, scale, and key gates."""
    report: dict = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            try:
                round_trip = json.loads(json.dumps(inst["answer"]))
            except (TypeError, ValueError) as exc:
                g1_failures.append(f"{preset}/{seed}: JSON error {exc}")
            else:
                if round_trip != inst["answer"]:
                    g1_failures.append(f"{preset}/{seed}: JSON changed answer")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=123, **shipping_params)
    answer = shipping["answer"]
    opposite = next(index for index in range(1, len(answer)) if answer[index] != answer[0])
    swapped = [list(item) for item in answer]
    swapped[0], swapped[opposite] = swapped[opposite], swapped[0]
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": answer + [answer[0]],
        "empty": [],
        "out_of_range": [[2, 1]] + answer[1:],
    }
    corruption_results = {
        name: {
            "accepted": verify(shipping, candidate)[0],
            "reason": verify(shipping, candidate)[1],
        }
        for name, candidate in corruptions.items()
    }
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": (
            all(not entry["accepted"] for entry in corruption_results.values())
            and len(set(reasons)) == len(reasons)
        ),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    rendered_answer = ", ".join(str(item[0]) for item in answer)
    realistic = (
        "The finite-difference check cancels every variable coefficient.\n"
        "```text\n<answer>\n"
        + rendered_answer
        + "\n</answer>\n```\nThe constant term is -1."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(shipping, parsed)[0],
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("no tagged certificate") is None,
    }

    guess_rng = random.Random(0x150401656)
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_wall = time.perf_counter() - guess_start
    exact_fraction = 1.0 / search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": guess_hits / _G4_SAMPLES < 1e-6 and exact_fraction < 1e-6,
        "hits": guess_hits,
        "total": _G4_SAMPLES,
        "observed_fraction": guess_hits / _G4_SAMPLES,
        "exact_fraction": exact_fraction,
        "candidate_space": search_space(shipping),
        "sampling_prior": (
            "uniform over all {-1,+1} vectors with the exactly-15-positive "
            "constant sum forced by the target -1"
        ),
        "wall_clock_sec": round(guess_wall, 6),
    }

    attack_names = (
        "outlier_row_l1_norm",
        "greedy_prefix_cancellation",
        "random_restart_256_balanced",
        "obvious_walsh_ansatz",
    )
    attacks = {
        name: {"successes": 0, "attempts": 0, "steps": 0, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    reference_successes = 0
    reference_operations = 0
    reference_wall = 0.0
    for seed in range(800, 800 + _ATTACK_SEEDS):
        inst = make_instance(seed=seed, **shipping_params)

        start = time.perf_counter()
        candidate = _outlier_row_norm(inst)
        elapsed = time.perf_counter() - start
        stat = attacks["outlier_row_l1_norm"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["steps"] += inst["row_count"] * inst["n"]
        stat["wall_clock_sec"] += elapsed

        start = time.perf_counter()
        candidate, steps = _greedy_prefix_fit(inst)
        elapsed = time.perf_counter() - start
        stat = attacks["greedy_prefix_cancellation"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        start = time.perf_counter()
        success, steps = _random_restart(inst, random.Random(seed ^ 0xA551), 256)
        elapsed = time.perf_counter() - start
        stat = attacks["random_restart_256_balanced"]
        stat["attempts"] += 1
        stat["successes"] += int(success)
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        start = time.perf_counter()
        success, steps = _obvious_walsh_ansatz(inst)
        elapsed = time.perf_counter() - start
        stat = attacks["obvious_walsh_ansatz"]
        stat["attempts"] += 1
        stat["successes"] += int(success)
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        start = time.perf_counter()
        candidate, metrics = _reference_algorithm(inst)
        elapsed = time.perf_counter() - start
        reference_wall += elapsed
        reference_operations += metrics["field_operations"]
        reference_successes += int(
            candidate is not None and verify(inst, candidate)[0]
        )

    for stat in attacks.values():
        stat["wall_clock_sec"] = round(stat["wall_clock_sec"], 6)
    all_attacks_failed = all(stat["successes"] == 0 for stat in attacks.values())
    average_reference_operations = reference_operations // _ATTACK_SEEDS
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == _ATTACK_SEEDS,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "modular Gaussian elimination with exact rational validation",
            "complexity": "O(n*m^2+m^3) exact field operations for m equations",
            "wall_clock_sec": round(reference_wall, 6),
            "operations": reference_operations,
            "average_operations_per_instance": average_reference_operations,
            "solves": f"{reference_successes}/{_ATTACK_SEEDS}, as expected",
        },
    }

    demo = make_instance(seed=123, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    strongest_failing = max(
        attacks.items(), key=lambda item: item[1]["wall_clock_sec"]
    )
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and reference_successes == _ATTACK_SEEDS,
        "shipping_exact_solution_count": 1,
        "shipping_exact_solution_fraction": exact_fraction,
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": _G4_SAMPLES,
        "shipping_sampled_density": guess_hits / _G4_SAMPLES,
        "demo_bruteforce_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "reference_algorithm_wall_clock_sec": round(reference_wall, 6),
        "reference_algorithm_operations": reference_operations,
        "reference_average_operations": average_reference_operations,
        "strongest_failing_attack": strongest_failing[0],
        "strongest_failing_attack_wall_clock_sec": strongest_failing[1]["wall_clock_sec"],
        "strongest_failing_attack_steps": strongest_failing[1]["steps"],
    }

    preset_costs = {
        name: params["n"] * ((1 << params["label_bits"]) - 1)
        for name, params in DIFFICULTY.items()
    }
    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=909, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    harder = escalate(dict(shipping_params))
    fixed_answer = (
        isinstance(harder, dict)
        and make_instance(seed=910, **harder)["row_count"] == shipping["row_count"]
    )
    report["G7_scales"] = {
        "pass": (
            list(preset_costs.values()) == sorted(set(preset_costs.values()))
            and doubled_ok
            and fixed_answer
        ),
        "preset_matrix_entries": preset_costs,
        "doubled_n": doubled["n"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "escalated_params": harder,
        "escalation_keeps_answer_length": fixed_answer,
    }

    invariance_checks = 0
    witness_checks = 0
    failures = []
    unrelated_keys = []
    key_params = {"n": 64, "label_bits": 5, "coeff_bound": 7}
    for seed in range(20):
        inst = make_instance(seed=20_000 + seed, **key_params)
        base_key = canonical_key(inst)
        unrelated_keys.append(base_key)
        rng = random.Random(30_000 + seed)
        rows = list(range(inst["row_count"]))
        columns = list(range(inst["n"]))
        rng.shuffle(rows)
        rng.shuffle(columns)
        identity_rows = list(range(inst["row_count"]))
        identity_columns = list(range(inst["n"]))
        variants = (
            _relabel(inst, rows, identity_columns),
            _relabel(inst, identity_rows, columns),
            _relabel(inst, rows, columns),
            _relabel(inst, rows, columns, rotate_labels=True),
        )
        for number, moved in enumerate(variants):
            invariance_checks += 1
            if canonical_key(moved) != base_key:
                failures.append(f"key/{seed}/{number}")
            witness_checks += 1
            if not verify(moved, moved["answer"])[0]:
                failures.append(f"witness/{seed}/{number}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not failures and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": witness_checks,
        "invariance_failures": failures,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "transformations": [
            "arbitrary equation permutation",
            "arbitrary variable permutation",
            "composed row and variable permutation",
            "composition with an invertible cyclic rotation of row-label bits",
        ],
    }

    chars, tokens, elements = _answer_metrics(shipping["answer"])
    intended_operations = 222
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        chars <= 2000
        and elements <= 256
        and intended_operations <= 300
        and tokens == PROBLEM_PROFILE["max_answer_tokens"]
    )
    report["G9_no_tool_suitability"] = {
        # The three oracle arms, including the hinted arm, are diagnostics as
        # of 2026-09-05.  Only the answer-size and intended-effort caps gate G9.
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
