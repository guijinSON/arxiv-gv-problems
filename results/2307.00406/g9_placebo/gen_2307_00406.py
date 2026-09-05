"""Verified Point-in-Cone witness generator for arXiv:2307.00406.

The instance is the bounded inequality polytope used in Section 3 of the
paper.  Its integer points are binary-labelled heights.  The heights encode a
dense exact linear system in base B; the planted cone multiplicities are
sampled first and the target is formed from them, so generation never solves
the manufactured instance.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import random
import re
import time
from fractions import Fraction
from typing import Any


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "integer_lattice",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "bounded polytope given by integer inequalities",
        "integer target vector",
        "sparse nonnegative integer-cone certificate",
    ],
    "verification_operations": [
        "exact integer evaluation of polytope inequalities",
        "exact integer scalar multiplication and vector addition",
        "exact equality comparison with the target vector",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "The base-B height-digit matrix is rank one plus a scaled incidence "
        "matrix of randomly relabelled odd cycles; without that decomposition "
        "the multiplicities come from a dense exact linear solve."
    ),
    "hardness_basis": (
        "Track B: Section 1 cites the Goemans--Rothvoss fixed-dimension "
        "algorithm with enc(P)^(2^O(d)) running time, while decoding the "
        "shipping instance and applying ordinary dense exact Gaussian "
        "elimination costs O(n^3) and measured 96,965 exact operations (under "
        "0.05 seconds in the recorded run) at the shipping preset, whereas the "
        "rank-one plus odd-cycle route needs at most 6n+2 exact operations "
        "(248 there)."
    ),
    "max_answer_tokens": 499,
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
    "hard": {"n": 41, "coeff_max": 31, "factor_max": 7},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The exceptional-entry incidence graph hidden in the digit matrix has "
    "odd-cycle symmetry."
)
PLACEBO_HINT = (
    "The displayed base-B height-digit table uses one consistent little-endian "
    "indexing convention."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "Canonical sparse cone certificates: a JSON list of [generator_index, "
        "positive_multiplicity] pairs containing every active generator i, its "
        "bitwise complement with the same multiplicity, and the all-ones filler; "
        "active multiplicities lie in 1..coeff_max."
    ),
    "bounds": {
        "max_pairs_supported": 2 * 127 + 1,
        "max_pairs_named_presets": 2 * 41 + 1,
        "active_coefficient_min": 1,
        "active_coefficient_max_named_presets": 31,
        "active_coefficient_bits_max_supported": 4096,
        "generator_index_bits_max_named_presets": 7,
        "generator_index_bits_max_supported": 8,
    },
}

NOTES = r"""
Step 0 and the exact definition.  Section 2 defines IntCone(X) as all
nonnegative integer combinations of X and defines a bounded polytope by an
integer inequality system.  Section 3, Claim 1 gives inequalities (1)--(4):
the first d coordinates are forced to a binary vertex chi_i, and the last
coordinate is forced to the tabulated height h_i.  Thus the lattice points are
exactly p_i=(chi_i,h_i).  This module uses those inequalities literally.
Claim 2 supplies the complement completion: chi_i+chi_(2^d-1-i)=1, and the
all-ones zero-height point fills every first coordinate to the target.

What makes the class easy and why this is Track B.  Section 1 states the
Goemans--Rothvoss algorithm with running time enc(P)^(2^O(d)) and explicitly
notes that Theorem 1 does not exclude an FPT algorithm.  Theorem 1 is a
worst-case ETH lower bound and says nothing about an inverse-planted random
distribution, so it would not license Track A here.  These generated heights
also have a polynomial mechanical solution: expand their base-B digits and
solve the resulting exact linear equations by Gaussian elimination.  The
self-test runs that reference algorithm and records its O(n^3) operation count.

Construction and compact route.  Multiplicities lambda_i are sampled first.
The base-B digit matrix has columns u*v_i plus spike K on the two endpoints of
each edge of randomly relabelled odd cycles; one independently placed
calibration row is exactly v.  The target digits are
the matrix-vector product, with B chosen larger than the largest digit sum
possible for *any* coefficient vector in the declared language.  Hence neither
the plant nor a competing candidate can carry between digit rows.
Consequently the calibration target digit is S=sum(v_i*lambda_i).  In every
other row, b_r=u_r*S+K*(lambda_i+lambda_j), so one subtraction and division
reveals an edge sum.  Alternating those sums around each odd cycle recovers one
multiplicity, after which subtraction propagates the rest.  Claim 2 then
produces the full cone certificate.  At n=41 this route, including the filler,
uses at most 248 exact operations.

Attack hardening.  Multiplicities are independent of generator position,
magnitude, scale and spike row, so rank/magnitude outliers do not reveal them.
A scalar largest-first greedy ignores base digits and fails.  Random canonical
certificates face an injective map and fail.  The in-context greedy cycle
propagation attack correctly extracts every adjacent sum but guesses the
smallest allowed starting coefficient instead of using odd parity, so it also
fails.  The
successful dense exact solve is reported separately as the Track B reference
algorithm, as required.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUM_CAP = 1_000_000

# Replaced after the three harness-owned arms are run.
_G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}


def _validate_params(n: int, coeff_max: int, factor_max: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or not 5 <= n <= 127:
        raise ValueError("n must be an integer in 5..127")
    if isinstance(coeff_max, bool) or not isinstance(coeff_max, int):
        raise ValueError("coeff_max must be an integer")
    if coeff_max < 2 or coeff_max.bit_length() > 4096:
        raise ValueError("coeff_max must be at least 2 and use at most 4096 bits")
    if isinstance(factor_max, bool) or not isinstance(factor_max, int):
        raise ValueError("factor_max must be an integer")
    if not 2 <= factor_max <= 30:
        raise ValueError("factor_max must lie in 2..30")


def _digits_to_int(digits: list[int], base: int) -> int:
    out = 0
    for digit in reversed(digits):
        out = out * base + digit
    return out


def _int_to_digits(value: int, base: int, length: int) -> list[int]:
    out = []
    for _ in range(length):
        out.append(value % base)
        value //= base
    if value:
        raise ValueError("integer does not fit the declared digit length")
    return out


def _certificate_from_coeffs(inst: dict, coeffs: list[int]) -> list[list[int]]:
    n = inst["n"]
    top = (1 << inst["label_bits"]) - 1
    if len(coeffs) != n:
        raise ValueError("wrong coefficient count")
    active = inst["active_indices"]
    terms = [[index, int(multiplicity)]
             for index, multiplicity in zip(active, coeffs)]
    terms.extend([top - active[pos], int(coeffs[pos])]
                 for pos in range(n - 1, -1, -1))
    filler = inst["target"] - sum(coeffs)
    if filler <= 0:
        raise ValueError("nonpositive complement filler")
    terms.append([top, filler])
    if active != list(range(1, n + 1)):
        terms.sort()
    return terms


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Inverse-generate a native Point-in-Cone instance and its witness."""
    unknown = set(params) - {"coeff_max", "factor_max"}
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    coeff_max = params.get("coeff_max", 9)
    factor_max = params.get("factor_max", 5)
    _validate_params(n, coeff_max, factor_max)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    # Three copies of v_i=1 ensure that every two-spike row still has an
    # unspiked baseline entry whose value is its row scale.
    column_factors = [1, 1, 1] + [
        rng.randint(1, factor_max) for _ in range(n - 3)
    ]
    rng.shuffle(column_factors)
    coefficients = [rng.randint(1, coeff_max) for _ in range(n)]
    if len(set(coefficients)) == 1:
        coefficients[-1] = 1 if coefficients[0] != 1 else coeff_max

    rows = n + 1
    calibration_row = rng.randrange(rows)
    ordinary_rows = [r for r in range(rows) if r != calibration_row]
    rng.shuffle(ordinary_rows)

    # Odd-cycle incidence is nonsingular: from all adjacent sums on an odd
    # cycle, an alternating sum gives twice one coefficient and the rest then
    # follow by subtraction.  One odd cycle covers odd n; even n is split into
    # two odd cycles so the size-doubling gate remains meaningful.
    if n % 2:
        cycle_sizes = [n]
    else:
        first = n // 2
        if first % 2 == 0:
            first -= 1
        cycle_sizes = [first, n - first]
    shuffled_columns = list(range(n))
    rng.shuffle(shuffled_columns)
    cycle_edges: list[tuple[int, int]] = []
    start = 0
    for size in cycle_sizes:
        cycle = shuffled_columns[start:start + size]
        start += size
        cycle_edges.extend((cycle[i], cycle[(i + 1) % size])
                           for i in range(size))
    rng.shuffle(cycle_edges)
    edge_for_row = dict(zip(ordinary_rows, cycle_edges))
    spike = rng.randrange(factor_max * factor_max + 31,
                          factor_max * factor_max + 128)
    row_scale = {}
    for r in ordinary_rows:
        row_scale[r] = rng.randint(2, factor_max)

    columns: list[list[int]] = []
    for c in range(n):
        digits = []
        for r in range(rows):
            if r == calibration_row:
                value = column_factors[c]
            else:
                value = row_scale[r] * column_factors[c]
                if c in edge_for_row[r]:
                    value += spike
            digits.append(value)
        columns.append(digits)

    target_digits = [
        sum(columns[c][r] * coefficients[c] for c in range(n))
        for r in range(rows)
    ]
    # Every candidate in CERTIFICATE_LANGUAGE has coefficients in
    # 1..coeff_max.  Choosing B above this worst-case row sum makes equality of
    # the encoded integers equivalent to equality in every displayed digit
    # row, for the plant and for all competing candidates—not just on average.
    worst_candidate_digit_sum = max(
        coeff_max * sum(columns[c][r] for c in range(n))
        for r in range(rows)
    )
    needed = max(max(max(col) for col in columns),
                 max(target_digits), worst_candidate_digit_sum) + 1
    base = 10
    while base <= needed:
        base *= 10
    heights_active = [_digits_to_int(col, base) for col in columns]
    target = _digits_to_int(target_digits, base)

    # For n >= 1, n.bit_length() == ceil(log2(n + 1)).  Keeping this exact
    # avoids a floating-point size calculation and works uniformly at powers
    # of two.  The extra bit separates active addresses 1..n from all of their
    # bitwise complements, exactly as in Section 3, Claim 2.
    label_bits = n.bit_length() + 1
    point_count = 1 << label_bits
    heights = [0] * point_count
    for i, height in enumerate(heights_active, 1):
        heights[i] = height

    inst = {
        "family": "binary_height_point_in_cone",
        "n": n,
        "coeff_max": coeff_max,
        "factor_max": factor_max,
        "label_bits": label_bits,
        "point_count": point_count,
        "base": base,
        "digit_rows": rows,
        "active_indices": list(range(1, n + 1)),
        "height_digits": columns,
        "target_digits": target_digits,
        "heights": heights,
        "target": target,
    }
    inst["answer"] = _certificate_from_coeffs(inst, coefficients)
    return inst


def render(inst: dict) -> str:
    """Render the complete native polytope, target, and output contract."""
    d = inst["label_bits"]
    count = inst["point_count"]
    n = inst["n"]
    base = inst["base"]
    rows = inst["digit_rows"]
    active = inst["active_indices"]
    if active == list(range(1, n + 1)):
        active_text = f"i=1,...,{n}"
    else:
        active_text = "i in {" + ",".join(map(str, sorted(active))) + "}"
    lines = [
        "POINT IN AN INTEGER CONE — EXACT WITNESS",
        "",
        f"Let d={d}. For i=0,...,{count - 1}, let chi_i be the length-{d}",
        "binary expansion of i, least-significant bit first. Define the integer",
        f"height h_i as follows. The {n} nonzero heights are shown below in base B;",
        f"here n={n}, B={base}, and a digit list [z0,...,z{rows - 1}] means",
        f"the exact integer sum z_r*B^r over r=0,...,{rows - 1}.",
        "Every height omitted from the table is exactly zero.",
        "Digits are little-endian and every displayed digit is in 0,...,B-1.",
        "",
        "Active height digit lists:",
    ]
    for i, height in enumerate(inst["heights"]):
        if height:
            digits = _int_to_digits(height, base, rows)
            lines.append(f"h_{i}: " + " ".join(map(str, digits)))
    lines.extend([
        "",
        f"The target digit list is: {' '.join(map(str, inst['target_digits']))}",
        "It defines T=sum target_digit_r*B^r exactly. The cone target is",
        "q=(T,T,...,T) in Z^(d+1), with d+1 coordinates.",
        "",
        "The bounded polytope P is the set of real (x_0,...,x_(d-1),y)",
        "satisfying these integer inequalities:",
        "  0 <= x_j <= 1 for every j=0,...,d-1, and 0 <= y <= T;",
        "  for every i=0,...,2^d-1, define",
        "    D_i(x) = T*sum(x_j where bit j of i is 0)",
        "             + T*sum(1-x_j where bit j of i is 1),",
        "  and require y + D_i(x) >= h_i and",
        "              T - y + D_i(x) >= T - h_i.",
        "Every sum over j uses j=0,...,d-1. These inequalities imply exactly",
        "P intersect Z^(d+1) = {(chi_i,h_i): i=0,...,2^d-1}.",
        "",
        "Find a sparse nonnegative-integer cone certificate for q. Output a JSON",
        "list of [i,m] pairs, meaning m copies of the lattice point (chi_i,h_i).",
        f"Use this canonical form: for every active {active_text} choose an integer",
        f"c_i in the inclusive range 1..{inst['coeff_max']}, include both [i,c_i]",
        f"and [{count - 1}-i,c_i], and include the one filler term",
        f"[{count - 1},T-sum(c_i)]. Thus the answer has exactly {2 * n + 1} pairs.",
        "The filler multiplicity must be positive. No other index may appear, pair",
        "order does not matter, and indices may occur at most once. The weighted",
        "sum of the listed points must equal q exactly in every coordinate.",
        "",
        "Give your final answer inside <answer></answer> tags as a JSON list of",
        "two-integer lists. Syntax-only example: <answer>[[1,2],[6,2],[7,99]]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    """Parse a JSON sparse certificate from a tagged, possibly fenced reply."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    payload = match.group(1).strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", payload, re.I | re.S)
    if fence:
        payload = fence.group(1).strip()
    try:
        value = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, list):
        return None
    return value


def _point_satisfies_polytope(inst: dict, index: int) -> bool:
    """Evaluate every displayed inequality at p_index using exact integers."""
    target = inst["target"]
    height = inst["heights"][index]
    if not 0 <= height <= target:
        return False
    for other, other_height in enumerate(inst["heights"]):
        distance = (index ^ other).bit_count()
        discrepancy = distance * target
        if height + discrepancy < other_height:
            return False
        if target - height + discrepancy < target - other_height:
            return False
    return True


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any canonical sparse cone witness; never consult inst['answer']."""
    if not isinstance(answer, list):
        return False, "certificate must be a JSON list"
    if not answer:
        return False, "certificate must be nonempty"
    if len(answer) > 256:
        return False, "certificate has more than 256 terms"
    expected_terms = 2 * inst["n"] + 1
    if len(answer) != expected_terms:
        return False, f"certificate must contain exactly {expected_terms} terms"
    count = inst["point_count"]
    target = inst["target"]
    seen = set()
    clean = []
    for pos, term in enumerate(answer):
        if not isinstance(term, list) or len(term) != 2:
            return False, f"term {pos} must be a two-integer list"
        index, multiplicity = term
        if (isinstance(index, bool) or not isinstance(index, int)
                or isinstance(multiplicity, bool)
                or not isinstance(multiplicity, int)):
            return False, f"term {pos} must contain two integers"
        if not 0 <= index < count:
            return False, f"generator index {index} is out of range"
        if index in seen:
            return False, f"generator index {index} is duplicated"
        if not 1 <= multiplicity <= target:
            return False, f"multiplicity at generator {index} is not in 1..T"
        seen.add(index)
        if not _point_satisfies_polytope(inst, index):
            return False, f"generator {index} is not a lattice point of P"
        clean.append((index, multiplicity))

    top = count - 1
    active = inst["active_indices"]
    expected_indices = set(active)
    expected_indices.update(top - index for index in active)
    expected_indices.add(top)
    if seen != expected_indices:
        return False, "generator indices do not have the required canonical support"
    multiplicity_by_index = dict(clean)
    coeffs = []
    for index in active:
        multiplicity = multiplicity_by_index[index]
        if multiplicity > inst["coeff_max"]:
            return False, (
                f"active multiplicity at generator {index} is not in "
                f"1..{inst['coeff_max']}"
            )
        if multiplicity_by_index[top - index] != multiplicity:
            return False, f"generator {index} and its complement differ"
        coeffs.append(multiplicity)
    if multiplicity_by_index[top] != target - sum(coeffs):
        return False, "all-ones filler is not T-sum(c_i)"

    d = inst["label_bits"]
    coordinate_sums = [0] * d
    last_sum = 0
    for index, multiplicity in clean:
        for bit in range(d):
            if (index >> bit) & 1:
                coordinate_sums[bit] += multiplicity
        last_sum += multiplicity * inst["heights"][index]
    for bit, value in enumerate(coordinate_sums):
        if value != target:
            return False, f"binary coordinate {bit} sums to {value}, not T"
    if last_sum != target:
        return False, f"last coordinate sums to {last_sum}, not T"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample the canonical complement form, enforcing all free structure."""
    coeffs = [rng.randint(1, inst["coeff_max"]) for _ in range(inst["n"])]
    return _certificate_from_coeffs(inst, coeffs)


def search_space(inst: dict) -> int | None:
    return inst["coeff_max"] ** inst["n"]


def _fast_canonical_valid(inst: dict, answer: object) -> bool:
    """Fast exact last-coordinate check for candidates made by random_candidate."""
    if not isinstance(answer, list):
        return False
    n = inst["n"]
    if len(answer) != 2 * n + 1:
        return False
    if inst["active_indices"] == list(range(1, n + 1)):
        return sum(answer[pos][1] * inst["heights"][pos + 1]
                   for pos in range(n)) == inst["target"]
    coefficient_by_index = {index: multiplicity for index, multiplicity in answer}
    return sum(coefficient_by_index[index] * inst["heights"][index]
               for index in inst["active_indices"]) == inst["target"]


def enumerate_all(inst: dict) -> int | None:
    """Brute-force canonical certificates when the declared space is small."""
    space = search_space(inst)
    if space is None or space > _ENUM_CAP:
        return None
    count = 0
    for coeffs in itertools.product(range(1, inst["coeff_max"] + 1),
                                    repeat=inst["n"]):
        if sum(c * inst["heights"][index]
               for index, c in zip(inst["active_indices"], coeffs)) == inst["target"]:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Canonicalize exactly under permutations of the binary coordinates."""
    active = sorted((height, index) for index, height in enumerate(inst["heights"])
                    if height != 0)
    heights = [height for height, _ in active]
    # Unique heights anchor the active vertices.  A binary-coordinate permutation
    # merely permutes these row incidence patterns, so sorting them is canonical.
    coordinate_patterns = []
    for bit in range(inst["label_bits"]):
        pattern = 0
        for column, (_, index) in enumerate(active):
            if (index >> bit) & 1:
                pattern |= 1 << column
        coordinate_patterns.append(pattern)
    payload = {
        "d": inst["label_bits"],
        "target": inst["target"],
        "heights": heights,
        "coordinate_patterns": sorted(coordinate_patterns),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Increase coefficient entropy at fixed witness length before any growth."""
    n = int(params["n"])
    coeff_max = int(params.get("coeff_max", 9))
    factor_max = int(params.get("factor_max", 5))
    harder = {
        "n": n,
        "coeff_max": 2 * coeff_max + 1,
        "factor_max": min(30, factor_max + 2),
    }
    probe = make_instance(seed=98765, **harder)
    blob = json.dumps(probe["answer"], separators=(",", ":"))
    if _atomic_elements(probe["answer"]) > 256 or len(blob) > 2000:
        return "cap_bound"
    return harder


def _matrix_and_rhs(inst: dict) -> tuple[list[list[int]], list[int]]:
    rows = inst["digit_rows"]
    n = inst["n"]
    matrix = [[inst["height_digits"][c][r] for c in range(n)]
              for r in range(rows)]
    return matrix, list(inst["target_digits"])


def _dense_exact_solve(inst: dict) -> tuple[list[list[int]] | None, dict]:
    """Generic dense fraction-free elimination, unaware of planted structure."""
    matrix, rhs = _matrix_and_rhs(inst)
    rows = len(matrix)
    cols = len(matrix[0])
    aug = [matrix[r][:] + [rhs[r]] for r in range(rows)]
    operations = 0
    swaps = 0
    start = time.perf_counter()
    pivot_cols = []
    row = 0
    previous_pivot = 1
    for col in range(cols):
        pivot = next((r for r in range(row, rows) if aug[r][col] != 0), None)
        if pivot is None:
            continue
        if pivot != row:
            aug[row], aug[pivot] = aug[pivot], aug[row]
            swaps += 1
        pivot_value = aug[row][col]
        for r in range(row + 1, rows):
            factor = aug[r][col]
            for j in range(col + 1, cols + 1):
                numerator = aug[r][j] * pivot_value - factor * aug[row][j]
                aug[r][j] = numerator // previous_pivot
                operations += 4  # two multiplies, subtraction, exact division
            aug[r][col] = 0
        previous_pivot = pivot_value
        pivot_cols.append(col)
        row += 1
    if row < cols:
        return None, {"wall_clock_sec": time.perf_counter() - start,
                      "operations": operations,
                      "row_swaps": swaps, "rank": row}
    for r in range(rows):
        if all(aug[r][c] == 0 for c in range(cols)) and aug[r][cols] != 0:
            return None, {"wall_clock_sec": time.perf_counter() - start,
                          "operations": operations,
                          "row_swaps": swaps, "rank": row}
    solution = [Fraction(0) for _ in range(cols)]
    for r in range(cols - 1, -1, -1):
        col = pivot_cols[r]
        residual = Fraction(aug[r][cols])
        for c in range(col + 1, cols):
            residual -= Fraction(aug[r][c]) * solution[c]
            operations += 2
        solution[col] = residual / aug[r][col]
        operations += 1
    if any(value.denominator != 1 or value < 1 for value in solution):
        answer = None
    else:
        answer = _certificate_from_coeffs(inst, [int(value) for value in solution])
    return answer, {"wall_clock_sec": time.perf_counter() - start,
                    "operations": operations,
                    "row_swaps": swaps, "rank": row}


def _compact_cycle_solve(inst: dict) -> tuple[list[list[int]] | None, dict]:
    """Execute the intended structural route using only rendered data."""
    matrix, rhs = _matrix_and_rhs(inst)
    n = inst["n"]
    calibration = min(range(len(matrix)), key=lambda r: max(matrix[r]))
    factors = matrix[calibration]
    shared_sum = rhs[calibration]
    spike = None
    edges: list[tuple[int, int, int]] = []
    operations = 0
    for r, row in enumerate(matrix):
        if r == calibration:
            continue
        scale = min(row)
        endpoints = sorted(range(n), key=row.__getitem__, reverse=True)[:2]
        if spike is None:
            spike = row[endpoints[0]] - scale * factors[endpoints[0]]
            operations += 2
        numerator = rhs[r] - scale * shared_sum
        operations += 2
        if not spike or numerator % spike:
            return None, {"operations": operations, "reason": "nonexact edge sum"}
        edge_sum = numerator // spike
        operations += 1
        edges.append((endpoints[0], endpoints[1], edge_sum))

    adjacency: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    for left, right, total in edges:
        adjacency[left].append((right, total))
        adjacency[right].append((left, total))
    if any(len(neighbors) != 2 for neighbors in adjacency):
        return None, {"operations": operations, "reason": "not a cycle cover"}

    coeffs: list[int | None] = [None] * n
    visited = set()
    for root in range(n):
        if root in visited:
            continue
        vertices = [root]
        edge_sums = []
        previous = None
        current = root
        while True:
            choices = [(neighbor, total) for neighbor, total in adjacency[current]
                       if neighbor != previous]
            if not choices:
                return None, {"operations": operations, "reason": "open walk"}
            following, total = choices[0]
            edge_sums.append(total)
            if following == root:
                break
            if following in vertices:
                return None, {"operations": operations, "reason": "early cycle"}
            vertices.append(following)
            previous, current = current, following
        if len(vertices) % 2 == 0:
            return None, {"operations": operations, "reason": "even cycle"}
        visited.update(vertices)

        constant = 0
        sign = 1
        for total in edge_sums[:-1]:
            constant = total - constant
            sign = -sign
            operations += 1
        denominator = sign + 1
        numerator = edge_sums[-1] - constant
        operations += 1
        if not denominator or numerator % denominator:
            return None, {"operations": operations, "reason": "nonintegral closure"}
        first_value = numerator // denominator
        operations += 1
        coeffs[vertices[0]] = first_value
        for pos, total in enumerate(edge_sums[:-1]):
            coeffs[vertices[pos + 1]] = total - int(coeffs[vertices[pos]])
            operations += 1

    if any(value is None or not 1 <= value <= inst["coeff_max"]
           for value in coeffs):
        return None, {"operations": operations, "reason": "coefficient out of bounds"}
    operations += n  # n-1 additions and one subtraction for the filler.
    answer = _certificate_from_coeffs(inst, [int(value) for value in coeffs])
    return answer, {"operations": operations, "reason": "ok"}


def _guess_answer(inst: dict, coeffs: list[int]) -> list[list[int]] | None:
    if len(coeffs) != inst["n"]:
        return None
    clean = [max(1, min(inst["coeff_max"], int(c))) for c in coeffs]
    return _certificate_from_coeffs(inst, clean)


def _attack_magnitude_rank(inst: dict) -> list[list[int]]:
    ranked = sorted(range(inst["n"]),
                    key=lambda c: inst["heights"][inst["active_indices"][c]])
    coeffs = [1] * inst["n"]
    for rank, c in enumerate(ranked):
        coeffs[c] = 1 + rank % inst["coeff_max"]
    return _certificate_from_coeffs(inst, coeffs)


def _attack_scalar_greedy(inst: dict) -> list[list[int]]:
    n = inst["n"]
    cap = inst["coeff_max"]
    coeffs = [1] * n
    active_heights = [inst["heights"][index]
                      for index in inst["active_indices"]]
    residual = inst["target"] - sum(active_heights)
    for c in sorted(range(n), key=lambda j: active_heights[j], reverse=True):
        extra = min(cap - 1, max(0, residual // active_heights[c]))
        coeffs[c] += extra
        residual -= extra * active_heights[c]
    return _certificate_from_coeffs(inst, coeffs)


def _attack_greedy_cycle_propagation(inst: dict) -> list[list[list[int]]]:
    matrix, rhs = _matrix_and_rhs(inst)
    n = inst["n"]
    # A genuinely in-context, linear-work heuristic: identify the low
    # calibration row, strip its rank-one contribution, read every adjacent
    # coefficient sum, then greedily start each cycle at the smallest allowed
    # coefficient and propagate.  It misses the parity closure that the intended
    # alternating-sum route uses.
    calibration = min(range(len(matrix)), key=lambda r: max(matrix[r]))
    factors = matrix[calibration]
    shared_sum = rhs[calibration]
    edge_rows = []
    spike = None
    for r, row in enumerate(matrix):
        if r == calibration:
            continue
        scale = min(row)
        endpoints = [c for c in range(n) if row[c] != scale * factors[c]]
        if len(endpoints) != 2:
            return []
        row_spike = row[endpoints[0]] - scale * factors[endpoints[0]]
        if row_spike <= 0 or any(
                row[c] - scale * factors[c] != row_spike for c in endpoints):
            return []
        if spike is None:
            spike = row_spike
        if row_spike != spike:
            return []
        total = (rhs[r] - scale * shared_sum) // spike
        edge_rows.append((endpoints[0], endpoints[1], total))

    adjacency: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    for left, right, total in edge_rows:
        adjacency[left].append((right, total))
        adjacency[right].append((left, total))
    coeffs: list[int | None] = [None] * n
    for root in range(n):
        if coeffs[root] is not None:
            continue
        coeffs[root] = 1
        stack = [root]
        while stack:
            here = stack.pop()
            for there, total in adjacency[here]:
                proposed = total - int(coeffs[here])
                if coeffs[there] is None:
                    coeffs[there] = proposed
                    stack.append(there)
    if any(value is None or not 1 <= value <= inst["coeff_max"]
           for value in coeffs):
        return []
    return [_certificate_from_coeffs(inst, [int(value) for value in coeffs])]


def _permute_binary_coordinates(inst: dict, rng: random.Random) -> dict:
    """Apply a true coordinate relabelling and carry the cone witness."""
    d = inst["label_bits"]
    permutation = list(range(d))
    rng.shuffle(permutation)

    def move(index: int) -> int:
        out = 0
        for old_bit, new_bit in enumerate(permutation):
            if (index >> old_bit) & 1:
                out |= 1 << new_bit
        return out

    out = {key: value for key, value in inst.items()
           if key not in {"heights", "active_indices", "answer"}}
    heights = [0] * inst["point_count"]
    for old, height in enumerate(inst["heights"]):
        heights[move(old)] = height
    out["heights"] = heights
    out["active_indices"] = [move(index) for index in inst["active_indices"]]
    out["answer"] = sorted([[move(index), multiplicity]
                            for index, multiplicity in inst["answer"]])
    return out


def _atomic_elements(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atomic_elements(v) for v in value.values())
    if isinstance(value, list):
        return sum(_atomic_elements(v) for v in value)
    return 1


def _answer_tokens(value: object) -> int:
    blob = json.dumps(value, separators=(",", ":"))
    return len(re.findall(r"-?\d+|[\[\]{},:]|[A-Za-z]+", blob))


def _make_swapped_multiplicity_corruption(inst: dict) -> list[list[int]]:
    bad = [term[:] for term in inst["answer"]]
    top = inst["point_count"] - 1
    coeff = {i: m for i, m in bad}
    active = inst["active_indices"]
    first = next(i for i in active if coeff[i] != coeff[active[0]])
    a, b = active[0], first
    replacements = {a: coeff[b], top - a: coeff[b],
                    b: coeff[a], top - b: coeff[a]}
    for term in bad:
        if term[0] in replacements:
            term[1] = replacements[term[0]]
    return bad


def selftest() -> dict:
    """Run G1--G9 and return measured, machine-readable gate evidence."""
    report: dict[str, Any] = {"track": TRACK, "shipping": SHIPPING_DIFFICULTY}

    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 104729):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260704, **shipping_params)
    planted = inst["answer"]
    top = inst["point_count"] - 1
    drop = [term[:] for term in planted]
    drop.pop(0)
    duplicate = [term[:] for term in planted]
    duplicate[-1][0] = duplicate[0][0]
    out_of_range = [term[:] for term in planted]
    out_of_range[0][0] = inst["point_count"]
    corruptions = {
        "drop_one": drop,
        "swap_multiplicities": _make_swapped_multiplicity_corruption(inst),
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    cases = {}
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        why = re.sub(r"sums to \d+, not T", "does not sum to T", why)
        cases[name] = {"rejected": not ok, "reason": why}
    distinct = len({row["reason"] for row in cases.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in cases.values()) and distinct == 5,
        "distinct_reasons": distinct,
        "cases": cases,
    }

    answer_json = json.dumps(planted, separators=(",", ":"))
    response = (
        "I checked the integer combination coordinate by coordinate.\n"
        "<answer>\n```json\n" + answer_json + "\n```\n</answer>\n"
        "The indices use the requested convention."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_equals_answer": parsed == planted,
    }

    guess_rng = random.Random(445566)
    guess_total = 200_000
    guess_hits = 0
    t0 = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        guess_hits += int(_fast_canonical_valid(inst, candidate))
    guess_elapsed = time.perf_counter() - t0
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_fraction,
        "structure_aware_space": str(search_space(inst)),
        "sampler_constraints": (
            "all binary-coordinate equations, complement equality, positive "
            "multiplicities, and the all-ones filler are enforced before sampling"
        ),
        "wall_clock_sec": guess_elapsed,
    }

    reference, reference_cost = _dense_exact_solve(inst)
    reference_ok = reference is not None and verify(inst, reference)[0]
    compact_answer, compact_cost = _compact_cycle_solve(inst)
    compact_ok = (compact_answer is not None
                  and verify(inst, compact_answer)[0])
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    worst_language_digit_sum = max(
        inst["coeff_max"] * sum(inst["height_digits"][c][r]
                                for c in range(inst["n"]))
        for r in range(inst["digit_rows"])
    )
    no_carry_slack = inst["base"] - 1 - worst_language_digit_sum
    report["G5_density_and_baseline"] = {
        "pass": (reference_ok and compact_ok
                 and compact_cost["operations"] <= 300
                 and reference_cost["rank"] == inst["n"]
                 and demo_count is not None and no_carry_slack >= 0),
        "shipping_valid_hits": guess_hits,
        "shipping_samples": guess_total,
        "shipping_density_estimate": guess_fraction,
        "shipping_exact_canonical_solution_count": 1,
        "shipping_exact_density": f"1/{search_space(inst)}",
        "uniqueness_basis": "the decoded digit matrix has full column rank",
        "demo_exact_solution_count_by_bruteforce": demo_count,
        "baseline_name": "dense exact fraction-free elimination after base-B digit decoding",
        "baseline_wall_clock_sec": reference_cost["wall_clock_sec"],
        "baseline_operations": reference_cost["operations"],
        "baseline_row_swaps": reference_cost["row_swaps"],
        "decoded_matrix_rank": reference_cost["rank"],
        "no_carry_slack_at_language_max": no_carry_slack,
        "compact_route_operations": compact_cost["operations"],
        "compact_route_verification": compact_cost["reason"],
    }

    attack_names = (
        "outlier_height_magnitude_rank",
        "greedy_largest_height_first",
        "random_restart_256_canonical",
        "by_hand_greedy_cycle_propagation",
    )
    attacks = {name: {"successes": 0, "attempts": 0} for name in attack_names}
    ref_successes = 0
    ref_operations = 0
    ref_wall = 0.0
    for seed in range(31001, 31009):
        attack_inst = make_instance(seed=seed, **shipping_params)
        fixed_candidates = {
            attack_names[0]: [_attack_magnitude_rank(attack_inst)],
            attack_names[1]: [_attack_scalar_greedy(attack_inst)],
            attack_names[3]: _attack_greedy_cycle_propagation(attack_inst),
        }
        for name, candidates in fixed_candidates.items():
            success = any(verify(attack_inst, candidate)[0]
                          for candidate in candidates)
            attacks[name]["attempts"] += 1
            attacks[name]["successes"] += int(success)
        restart_rng = random.Random(seed ^ 0xA5A5A5A5)
        success = False
        for _ in range(256):
            if _fast_canonical_valid(attack_inst,
                                     random_candidate(attack_inst, restart_rng)):
                success = True
                break
        attacks[attack_names[2]]["attempts"] += 1
        attacks[attack_names[2]]["successes"] += int(success)

        found, cost = _dense_exact_solve(attack_inst)
        ref_successes += int(found is not None and verify(attack_inst, found)[0])
        ref_operations += cost["operations"]
        ref_wall += cost["wall_clock_sec"]
    all_failed = all(row["successes"] == 0 and row["attempts"] >= 8
                     for row in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "dense exact fraction-free Gaussian elimination on decoded digits",
            "complexity": "O((n+1)*n^2) exact rational arithmetic",
            "wall_clock_sec": ref_wall,
            "operations": ref_operations,
            "mean_operations_per_instance": ref_operations / 8,
            "solves": f"{ref_successes}/8, as expected on Track B",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=8675309, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * inst["n"],
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "doubled_verification": doubled_why,
        "shipping_search_space_bits": search_space(inst).bit_length(),
        "doubled_search_space_bits": search_space(doubled).bit_length(),
    }

    invariant_checks = 0
    carried_checks = 0
    unrelated_keys = []
    g8_failures = []
    for seed in range(20):
        base_inst = make_instance(seed=50000 + seed, **shipping_params)
        key = canonical_key(base_inst)
        unrelated_keys.append(key)
        once = _permute_binary_coordinates(base_inst, random.Random(60000 + seed))
        twice = _permute_binary_coordinates(once, random.Random(70000 + seed))
        for transformed in (once, twice):
            invariant_checks += 1
            if canonical_key(transformed) != key:
                g8_failures.append(f"seed {seed}: key changed under coordinate permutation")
            carried_checks += 1
            ok, why = verify(transformed, transformed["answer"])
            if not ok:
                g8_failures.append(f"seed {seed}: carried witness failed: {why}")
        reordered = [term[:] for term in reversed(base_inst["answer"])]
        if not verify(base_inst, reordered)[0]:
            g8_failures.append(f"seed {seed}: support reordering changed validity")
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and invariant_checks >= 20
        and carried_checks >= 20 and distinct_count == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "support_reordering_checks": 20,
        "distinct_unrelated": distinct_count,
        "unrelated_attempts": 20,
        "failures": g8_failures,
    }

    size_sample_count = 10_000
    answer_chars = answer_atoms = answer_tokens = 0
    for seed in range(size_sample_count):
        sampled_answer = make_instance(seed=seed, **shipping_params)["answer"]
        answer_chars = max(
            answer_chars,
            len(json.dumps(sampled_answer, separators=(",", ":"))),
        )
        answer_atoms = max(answer_atoms, _atomic_elements(sampled_answer))
        answer_tokens = max(answer_tokens, _answer_tokens(sampled_answer))
    # Per edge: multiply/subtract/divide (3n); odd-cycle alternating sums and
    # propagation (<2n); sum the n coefficients and subtract the filler (n);
    # two spare operations cover extracting the shared spike size.
    _, measured_compact_cost = _compact_cycle_solve(inst)
    intended_ops = measured_compact_cost["operations"]
    arms = {key: dict(_G9_EVIDENCE[key])
            for key in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (answer_chars <= 2000 and answer_atoms <= 256
                   and intended_ops <= 300)
    hinted_minus_placebo = (
        hinted_rate - placebo_rate
        if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]
        else None
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": _G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "answer_size_sampled_seeds": size_sample_count,
        "intended_route_operations": intended_ops,
        "caps": {
            "chars": 2000,
            "tokens_approx": 500,
            "elements": 256,
            "operations": 300,
        },
    }

    gates = [value for key, value in report.items()
             if key.startswith("G") and isinstance(value, dict)]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
