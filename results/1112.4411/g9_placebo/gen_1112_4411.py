"""Self-contained Track-B generator for generalized MinRank over a prime field.

The paper arXiv:1112.4411 defines generalized MinRank as finding points
where a polynomial matrix evaluates to rank at most r.  This module uses
affine matrices over F_p in the paper's zero-dimensional parameter regime.

For d a power of two, let H be the d by d Walsh matrix.  Generation first
samples a pairwise-distinct d by d solution S and then forms B=-HDS, where
D is a random diagonal sign matrix.  The displayed (d+1) by (d+1) matrix is

                [ H D X + B   0 ]
        M(x) =  [                 ],
                [     0         1 ]

with the d^2 entries of X assigned to randomly permuted variable names.
Thus rank(M(x)) <= 1 exactly at the planted point.  The point is chosen
before B, so generation never solves its own instance.

The generic mechanical route constructs the linear equations exposed by
the 2-minors through the constant anchor and performs modular elimination.
The compact route notices that the coefficient columns are signed Walsh
characters and applies d fast Walsh transforms.  The verifier only
substitutes the proposed point and checks rank exactly over F_p.
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
import sys
import time


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # Finite-field arithmetic below is standard-library-only.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "affine polynomial matrix over a prime field",
        "finite-field point",
        "evaluated matrix with a prescribed rank bound",
    ],
    "verification_operations": [
        "exact substitution modulo a prime",
        "exact finite-field rank comparison",
        "canonical-residue and pairwise-distinctness checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "The linear coefficient columns are signed Walsh characters, so the "
        "rank-one condition can be inverted by shared butterfly transforms; "
        "without recognizing that basis, one performs a large modular elimination."
    ),
    "hardness_basis": (
        "Track B: Section 6 computes MinRank loci by forming minors and using "
        "F5/FGLM; on this affine zero-dimensional specialization those anchor "
        "minors reduce to a 64-variable modular linear system, solved by exact "
        "Gaussian elimination in O(k^3) field operations and measured at about "
        "25,300 field operations / 0.002 s at the shipping preset over F_655211, "
        "whereas the signed Walsh "
        "change of variables takes exactly 278 field operations; about 25,300 "
        "modular operations are mechanically easy with tools but not executable "
        "by hand in the evaluation context."
    ),
    "max_answer_tokens": 128,
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


# n is the requested lower bound on the prime-field size.  The answer has a
# fixed 64 coordinates on the two upper rungs; increasing n grows its entropy
# and modular arithmetic width without adding coordinates.
DIFFICULTY = {
    "hard": {"n": 655211, "dimension": 8},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The nonzero linear coefficient columns are signed characters of the "
    "binary Walsh basis."
)
PLACEBO_HINT = (
    "The field residues and variable indices reward especially careful "
    "bookkeeping throughout."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly k=d^2 pairwise-distinct canonical residues in "
        "{0,...,p-1}, in x0,...,x(k-1) order."
    ),
    "bounds": {
        "length": "k=d^2",
        "coordinate_range": "0..p-1",
        "structural_rule": "all coordinates pairwise distinct",
        "maximum_shipping_coordinates": 64,
    },
}

NOTES = (
    "Section 1 fixes the exact definition: over a field K, evaluate an n by m "
    "degree-D polynomial matrix and find points where its rank is at most r. "
    "Sections 6 and 6.2 identify the certificate-producing mechanical route: "
    "form the (r+1)-minors, compute a grevlex basis with F5, and convert it with "
    "FGLM; Theorem 5 bounds that route for generic affine zero-dimensional "
    "systems.  Section 7 identifies easy asymptotic regimes and Table 1 reports "
    "FGb/Magma costs, so the mere NP-completeness statement for finite fields "
    "cannot justify Track A for this generated distribution.  The family is "
    "therefore Track B.  It stays in the native affine finite-field objects with "
    "D=1, square size d+1, r=1, and k=d^2=(n-r)(m-r).  Generation samples the "
    "point before constructing the constant matrix.  Variable names and Walsh "
    "column signs are randomized.  The outlier, diagonal-greedy, unaligned-Walsh, "
    "and short random-restart probes omit different parts of the shared signed "
    "basis; exact elimination is reported separately as the successful Track-B "
    "reference algorithm."
)


# Filled only from script-owned hardening transcripts.  A fresh build starts
# honestly unmeasured; selftest consequently leaves G9 false until all arms run.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


# ---------------------------------------------------------------------------
# Prime-field and Walsh helpers.


# 2^89-1 is a known Mersenne prime.  It is the largest supported field:
# 64 residues of at most 27 digits still fit the 2,000-character answer cap,
# whereas the next known Mersenne prime, 2^107-1, would not.
_MAX_FIELD = (1 << 89) - 1


def _is_prime(value):
    if value < 2:
        return False
    small_primes = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    if value in small_primes or value == _MAX_FIELD:
        return True
    if any(value % prime == 0 for prime in small_primes):
        return False
    if value >= (1 << 64):
        return False

    # These seven bases make Miller--Rabin deterministic below 2^64.
    odd_part = value - 1
    powers_of_two = 0
    while odd_part % 2 == 0:
        powers_of_two += 1
        odd_part //= 2
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        witness = pow(base, odd_part, value)
        if witness in (1, value - 1):
            continue
        for _ in range(powers_of_two - 1):
            witness = witness * witness % value
            if witness == value - 1:
                break
        else:
            return False
    return True


def _next_prime(value):
    candidate = max(3, int(value))
    if candidate > _MAX_FIELD:
        raise ValueError("n exceeds the largest field allowed by the answer cap")
    if candidate >= (1 << 64):
        return _MAX_FIELD
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _hadamard(dimension):
    return [
        [1 if ((row & column).bit_count() % 2 == 0) else -1
         for column in range(dimension)]
        for row in range(dimension)
    ]


def _fwt(values, modulus, counter=None):
    out = [value % modulus for value in values]
    width = 1
    while width < len(out):
        for start in range(0, len(out), 2 * width):
            for offset in range(width):
                left = out[start + offset]
                right = out[start + offset + width]
                out[start + offset] = (left + right) % modulus
                out[start + offset + width] = (left - right) % modulus
                if counter is not None:
                    counter[0] += 2
        width *= 2
    return out


def _inverse_mod_counted(value, modulus):
    """Extended-Euclidean inverse and a conservative primitive-op count."""
    old_remainder, remainder = modulus, value % modulus
    old_coefficient, coefficient = 0, 1
    operations = 1
    while remainder:
        quotient = old_remainder // remainder
        old_remainder, remainder = remainder, old_remainder - quotient * remainder
        old_coefficient, coefficient = coefficient, old_coefficient - quotient * coefficient
        operations += 5  # division, two multiplications, and two subtractions
    if old_remainder != 1:
        raise ValueError("value has no modular inverse")
    return old_coefficient % modulus, operations + 1


def _cell(constant=0, terms=None):
    return [int(constant), [] if terms is None else [list(t) for t in terms]]


def _zero_matrix(size):
    return [[_cell() for _ in range(size)] for _ in range(size)]


def _sample_distinct_residues(rng, field, count):
    if field <= sys.maxsize:
        return rng.sample(range(field), count)
    selected = set()
    output = []
    while len(output) < count:
        value = rng.randrange(field)
        if value not in selected:
            selected.add(value)
            output.append(value)
    return output


def _canonical_cell(cell, modulus):
    constant, terms = cell
    merged = {}
    for variable, coefficient in terms:
        merged[int(variable)] = (merged.get(int(variable), 0) + int(coefficient)) % modulus
    return [
        int(constant) % modulus,
        [[variable, coefficient] for variable, coefficient in sorted(merged.items()) if coefficient],
    ]


# ---------------------------------------------------------------------------
# Required generator interface.


def make_instance(n, seed=0, dimension=8, **params):
    """Inverse-generate a unique affine generalized-MinRank witness."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if dimension not in (2, 4, 8):
        raise ValueError("dimension must be one of 2, 4, 8")
    field = _next_prime(max(n, dimension * dimension + 3))
    rng = random.Random(seed)
    d = dimension
    variables = d * d
    size = d + 1

    # The certificate is sampled first.  Pairwise distinctness is part of the
    # declared witness language and is cheap for both generation and checking.
    answer = _sample_distinct_residues(rng, field, variables)

    positions = [(a, b) for b in range(d) for a in range(d)]
    rng.shuffle(positions)
    signs = [rng.choice((-1, 1)) for _ in range(d)]
    base_h = _hadamard(d)
    signed_h = [
        [base_h[row][a] * signs[a] for a in range(d)]
        for row in range(d)
    ]

    solution_matrix = [[0] * d for _ in range(d)]
    for variable, (a, b) in enumerate(positions):
        solution_matrix[a][b] = answer[variable]

    constant_block = [[0] * d for _ in range(d)]
    for row in range(d):
        for column in range(d):
            constant_block[row][column] = (
                -sum(
                    signed_h[row][a] * solution_matrix[a][column]
                    for a in range(d)
                )
            ) % field

    matrix = _zero_matrix(size)
    for row in range(d):
        for column in range(d):
            terms = []
            for variable, (a, b) in enumerate(positions):
                if b == column:
                    terms.append([variable, signed_h[row][a] % field])
            matrix[row][column] = _cell(constant_block[row][column], terms)
    matrix[d][d] = _cell(1, [])

    return {
        "paper": "1112.4411",
        "field": field,
        "dimension": d,
        "matrix_size": size,
        "variables": variables,
        "rank_bound": 1,
        "degree": 1,
        "anchor": [d, d],
        "matrix": matrix,
        "answer": list(answer),
    }


def _format_affine(cell, field):
    constant, terms = _canonical_cell(cell, field)
    pieces = [str(constant)] if constant else []
    for variable, coefficient in terms:
        signed = coefficient if coefficient <= field // 2 else coefficient - field
        if signed == 1:
            term = f"x{variable}"
        elif signed == -1:
            term = f"-x{variable}"
        else:
            term = f"{signed}*x{variable}"
        pieces.append(term)
    if not pieces:
        return "0"
    expression = pieces[0]
    for term in pieces[1:]:
        expression += (" - " + term[1:]) if term.startswith("-") else (" + " + term)
    return expression


def render(inst):
    field = inst["field"]
    size = inst["matrix_size"]
    variables = inst["variables"]
    lines = [
        "Generalized MinRank over a prime field",
        "",
        f"Work in the prime field F_{field}; every displayed integer is reduced modulo {field}.",
        f"There are {variables} variables x0,...,x{variables - 1}, numbered from 0.",
        f"The following is an affine {size} by {size} polynomial matrix M(x).",
        "Entry (row,column) is shown below with both indices 0-based. A missing",
        "variable has coefficient 0. Matrix rank means ordinary row rank over the field.",
        f"Find a point x in F_{field}^{variables} for which rank(M(x)) is at most",
        f"{inst['rank_bound']}. The required coordinates must be pairwise distinct.",
        f"Use canonical integer representatives 0 through {field - 1}, inclusive.",
        "",
        "Matrix entries:",
    ]
    for row in range(size):
        for column in range(size):
            lines.append(
                f"  ({row},{column}) = {_format_affine(inst['matrix'][row][column], field)}"
            )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    example = ", ".join(str(i) for i in range(variables))
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags, as one JSON list",
        f"of exactly {variables} pairwise-distinct integers in x0,...,x{variables - 1} order.",
        f"Example of the syntax only: <answer>[{example}]</answer>",
        "The example is not asserted to solve this instance. Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    tagged = re.search(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    candidates = [tagged.group(1)] if tagged else [text]
    decoder = json.JSONDecoder()
    for candidate in candidates:
        for match in re.finditer(r"\[", candidate):
            try:
                value, _end = decoder.raw_decode(candidate[match.start():])
            except (ValueError, TypeError):
                continue
            if isinstance(value, list):
                return value
    return None


def _rank_mod(matrix, modulus):
    work = [[int(value) % modulus for value in row] for row in matrix]
    rows = len(work)
    columns = len(work[0]) if rows else 0
    rank = 0
    for column in range(columns):
        pivot = next((r for r in range(rank, rows) if work[r][column]), None)
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        inverse = pow(work[rank][column], modulus - 2, modulus)
        work[rank] = [(value * inverse) % modulus for value in work[rank]]
        for row in range(rows):
            if row == rank or not work[row][column]:
                continue
            factor = work[row][column]
            work[row] = [
                (left - factor * right) % modulus
                for left, right in zip(work[row], work[rank])
            ]
        rank += 1
        if rank == rows:
            break
    return rank


def _evaluate(inst, point):
    field = inst["field"]
    evaluated = []
    for row in inst["matrix"]:
        output_row = []
        for constant, terms in row:
            value = int(constant)
            for variable, coefficient in terms:
                value += int(coefficient) * point[int(variable)]
            output_row.append(value % field)
        evaluated.append(output_row)
    return evaluated


def verify(inst, answer):
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer list must not be empty"
    variables = inst.get("variables")
    if len(answer) != variables:
        return False, f"point must contain exactly {variables} coordinates"
    field = inst.get("field")
    for index, value in enumerate(answer):
        if isinstance(value, bool) or not isinstance(value, int) or not (0 <= value < field):
            return False, f"coordinate {index} is not a canonical field residue"
    if len(set(answer)) != variables:
        return False, "point coordinates must be pairwise distinct"
    # Every instance made by make_instance has an isolated nonzero anchor; the
    # anchor location is part of the instance representation and is carried by
    # every supported relabelling.  Any nonzero complementary entry forms a
    # nonzero 2-minor with it.  This is an exact rank check and lets random-
    # candidate measurement reject after the first failed entry instead of row-
    # reducing 200,000 matrices.
    anchor = inst.get("anchor")
    matrix = inst.get("matrix")
    if (
        isinstance(anchor, list)
        and len(anchor) == 2
        and all(isinstance(v, int) for v in anchor)
        and isinstance(matrix, list)
    ):
        ar, ac = anchor
        if 0 <= ar < len(matrix) and 0 <= ac < len(matrix):
            for row_index, row in enumerate(matrix):
                if row_index == ar:
                    continue
                for column_index, (constant, terms) in enumerate(row):
                    if column_index == ac:
                        continue
                    value = int(constant)
                    for variable, coefficient in terms:
                        value += int(coefficient) * answer[int(variable)]
                    if value % field:
                        return False, "evaluated matrix has rank at least 2, exceeding bound 1"
            return True, "ok"

    evaluated = _evaluate(inst, answer)
    rank = _rank_mod(evaluated, field)
    if rank > inst["rank_bound"]:
        return False, f"evaluated matrix has rank {rank}, exceeding bound {inst['rank_bound']}"
    return True, "ok"


def random_candidate(inst, rng):
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    return _sample_distinct_residues(rng, inst["field"], inst["variables"])


def search_space(inst):
    field = inst["field"]
    variables = inst["variables"]
    if variables > field:
        return 0
    result = 1
    for value in range(field - variables + 1, field + 1):
        result *= value
    return result


def enumerate_all(inst):
    space = search_space(inst)
    if space > 200_000:
        return None
    count = 0
    for candidate in itertools.permutations(range(inst["field"]), inst["variables"]):
        if verify(inst, list(candidate))[0]:
            count += 1
    return count


# ---------------------------------------------------------------------------
# Structural canonicalization and real relabellings used by G8.


def _cell_key(cell, field, keep_variables=False):
    constant, terms = _canonical_cell(cell, field)
    if keep_variables:
        return (constant, tuple((int(v), int(c)) for v, c in terms))
    return (constant, tuple(sorted(int(c) for _v, c in terms)))


def canonical_key(inst):
    """Strong cheap invariant under variable and matrix row/column relabelling."""
    field = inst["field"]
    matrix = inst["matrix"]
    size = inst["matrix_size"]

    constants = [[int(matrix[r][c][0]) % field for c in range(size)] for r in range(size)]
    constant_rows = sorted(tuple(sorted(row)) for row in constants)
    constant_columns = sorted(
        tuple(sorted(constants[r][c] for r in range(size))) for c in range(size)
    )
    cell_profiles = sorted(_cell_key(matrix[r][c], field) for r in range(size) for c in range(size))

    # Couple each unnamed variable to the constants at every location where it
    # occurs.  Sorting first within a signature and then across signatures makes
    # variable names irrelevant while retaining much more than a coefficient histogram.
    variable_profiles = []
    for variable in range(inst["variables"]):
        occurrences = []
        for row in range(size):
            for column in range(size):
                constant, terms = _canonical_cell(matrix[row][column], field)
                coefficient = next((c for v, c in terms if v == variable), 0)
                if coefficient:
                    occurrences.append((constant, coefficient))
        variable_profiles.append(tuple(sorted(occurrences)))
    variable_profiles.sort()
    payload = repr((
        field,
        size,
        inst["rank_bound"],
        tuple(constant_rows),
        tuple(constant_columns),
        tuple(cell_profiles),
        tuple(variable_profiles),
    )).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def _relabel_variables(inst, old_to_new):
    transformed = copy.deepcopy(inst)
    for row in transformed["matrix"]:
        for cell in row:
            cell[1] = sorted([[old_to_new[v], c] for v, c in cell[1]])
    carried = [0] * inst["variables"]
    for old, new in enumerate(old_to_new):
        carried[new] = inst["answer"][old]
    transformed["answer"] = carried
    return transformed


def _permute_matrix(inst, row_old_to_new, column_old_to_new):
    transformed = copy.deepcopy(inst)
    size = inst["matrix_size"]
    matrix = [[None] * size for _ in range(size)]
    for old_row in range(size):
        for old_column in range(size):
            matrix[row_old_to_new[old_row]][column_old_to_new[old_column]] = copy.deepcopy(
                inst["matrix"][old_row][old_column]
            )
    transformed["matrix"] = matrix
    if "anchor" in inst:
        transformed["anchor"] = [
            row_old_to_new[inst["anchor"][0]],
            column_old_to_new[inst["anchor"][1]],
        ]
    return transformed


def escalate(params):
    harder = dict(params)
    current = harder.get("n")
    if isinstance(current, bool) or not isinstance(current, int):
        return None
    if current >= _MAX_FIELD:
        return "cap_bound"
    target = current * 10 + 1
    # Avoid a long sequence of ever larger 64-bit searches; the field-size axis
    # ends at the largest exact prime whose 64-coordinate answer stays writable.
    if target >= 10**18:
        target = _MAX_FIELD
    harder["n"] = _next_prime(target)
    return harder


# ---------------------------------------------------------------------------
# Independent solvers used only for measurements and adversarial checks.


def _linear_equations(inst):
    field = inst["field"]
    variables = inst["variables"]
    equations = []
    for row in inst["matrix"]:
        for constant, terms in row:
            coefficients = [0] * variables
            for variable, coefficient in terms:
                coefficients[int(variable)] = int(coefficient) % field
            if any(coefficients):
                equations.append(coefficients + [(-int(constant)) % field])
    return equations


def _reference_algorithm(inst):
    """Generic exact modular elimination; never reads inst['answer']."""
    started = time.perf_counter()
    field = inst["field"]
    variables = inst["variables"]
    rows = _linear_equations(inst)
    operations = 0
    pivot_row = 0
    pivots = []
    for column in range(variables):
        pivot = next((r for r in range(pivot_row, len(rows)) if rows[r][column] % field), None)
        if pivot is None:
            continue
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        inverse = pow(rows[pivot_row][column] % field, field - 2, field)
        operations += max(1, 2 * (field.bit_length() - 1))
        for index in range(column, variables + 1):
            rows[pivot_row][index] = rows[pivot_row][index] * inverse % field
            operations += 1
        for row_index in range(len(rows)):
            if row_index == pivot_row:
                continue
            factor = rows[row_index][column] % field
            if not factor:
                continue
            # Deliberately use the standard dense row update; this is the
            # mechanical route whose cost Track B contrasts with the invariant.
            for index in range(column, variables + 1):
                rows[row_index][index] = (
                    rows[row_index][index] - factor * rows[pivot_row][index]
                ) % field
                operations += 2
        pivots.append(column)
        pivot_row += 1
        if pivot_row == len(rows):
            break
    if len(pivots) != variables:
        return None, {
            "operations": operations,
            "wall_clock_sec": time.perf_counter() - started,
            "rank": len(pivots),
        }
    answer = [0] * variables
    for row_index, column in enumerate(pivots):
        answer[column] = rows[row_index][variables] % field
    return answer, {
        "operations": operations,
        "wall_clock_sec": time.perf_counter() - started,
        "rank": len(pivots),
    }


def _compact_route(inst):
    """Recover the point from signed Walsh coefficient characters."""
    started = time.perf_counter()
    field = inst["field"]
    d = inst["dimension"]
    variables = inst["variables"]
    size = inst["matrix_size"]
    if d & (d - 1) or variables != d * d or size != d + 1:
        return None, {"operations": 0, "wall_clock_sec": 0.0}

    base_h = _hadamard(d)
    patterns = {}
    for a in range(d):
        vector = tuple(base_h[row][a] % field for row in range(d))
        negative = tuple((-base_h[row][a]) % field for row in range(d))
        patterns[vector] = (a, 1)
        patterns[negative] = (a, -1)

    locations = {}
    for variable in range(variables):
        nonzero_columns = set()
        vector_by_column = {}
        for column in range(d):
            vector = []
            for row in range(d):
                _constant, terms = _canonical_cell(inst["matrix"][row][column], field)
                vector.append(next((c for v, c in terms if v == variable), 0))
            if any(vector):
                nonzero_columns.add(column)
                vector_by_column[column] = tuple(vector)
        if len(nonzero_columns) != 1:
            return None, {"operations": 0, "wall_clock_sec": time.perf_counter() - started}
        column = next(iter(nonzero_columns))
        match = patterns.get(vector_by_column[column])
        if match is None:
            return None, {"operations": 0, "wall_clock_sec": time.perf_counter() - started}
        a, sign = match
        if (a, column) in locations:
            return None, {"operations": 0, "wall_clock_sec": time.perf_counter() - started}
        locations[(a, column)] = (variable, sign)

    counter = [0]
    inverse_d, inverse_operations = _inverse_mod_counted(d, field)
    counter[0] += inverse_operations
    output_scale = {1: (-inverse_d) % field, -1: inverse_d}
    answer = [None] * variables
    for column in range(d):
        constants = [inst["matrix"][row][column][0] % field for row in range(d)]
        transformed = _fwt(constants, field, counter)
        for a in range(d):
            variable, sign = locations[(a, column)]
            answer[variable] = output_scale[sign] * transformed[a] % field
            counter[0] += 1
    return answer, {
        "operations": counter[0],
        "wall_clock_sec": time.perf_counter() - started,
    }


def _make_injective(values, field):
    used = set()
    output = []
    for raw in values:
        value = int(raw) % field
        while value in used:
            value = (value + 1) % field
        used.add(value)
        output.append(value)
    return output


def _attack_outlier_support(inst):
    values = []
    field = inst["field"]
    for variable in range(inst["variables"]):
        score = 0
        for row_index, row in enumerate(inst["matrix"]):
            for column_index, (_constant, terms) in enumerate(row):
                coefficient = next((c for v, c in terms if v == variable), 0)
                if coefficient:
                    score += (row_index + 1) * (column_index + 3) * coefficient
        values.append(score % field)
    return verify(inst, _make_injective(values, field))[0]


def _attack_greedy_single_equation(inst):
    field = inst["field"]
    values = []
    for variable in range(inst["variables"]):
        guess = 0
        found = False
        for row in inst["matrix"]:
            for constant, terms in row:
                coefficient = next((c for v, c in terms if v == variable), 0)
                if coefficient:
                    guess = (-constant * pow(coefficient, field - 2, field)) % field
                    found = True
                    break
            if found:
                break
        values.append(guess)
    return verify(inst, _make_injective(values, field))[0]


def _attack_unaligned_walsh(inst):
    field = inst["field"]
    d = inst["dimension"]
    inverse_d = pow(d, field - 2, field)
    values = [0] * inst["variables"]
    for column in range(d):
        constants = [inst["matrix"][row][column][0] for row in range(d)]
        transformed = _fwt(constants, field)
        for a in range(d):
            # This plausible by-hand ansatz sees Walsh structure but ignores the
            # shuffled variable labels and randomized character signs.
            values[a * d + column] = (-inverse_d * transformed[a]) % field
    return verify(inst, _make_injective(values, field))[0]


def _attack_random_restart(inst, seed, restarts=256):
    rng = random.Random(seed ^ int(canonical_key(inst)[:16], 16))
    for _ in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _answer_atoms(answer):
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


# ---------------------------------------------------------------------------
# Mandatory local gates.


def selftest():
    report = {}
    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=872341, **shipping_params)

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (3, 19, 101):
            attempts += 1
            instance = make_instance(seed=seed, **params)
            ok, reason = verify(instance, instance["answer"])
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(instance["answer"])) != instance["answer"]:
                failures.append({"preset": preset, "seed": seed, "reason": "answer not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
    }

    planted = list(shipping["answer"])
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": [planted[1], planted[0]] + planted[2:],
        "duplicate": [planted[0], planted[0]] + planted[2:],
        "empty": [],
        "out_of_range": [shipping["field"]] + planted[1:],
    }
    corruption_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"accepted": ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(not value["accepted"] for value in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    encoded = json.dumps(shipping["answer"])
    response = "I used the rank-one anchor.\n```json\n<answer>\n" + encoded + "\n</answer>\n```\n"
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and verify(shipping, parsed)[0],
        "parsed": parsed == shipping["answer"],
    }

    sample_total = 200_000
    sample_hits = 0
    sample_rng = random.Random(604211)
    sample_started = time.perf_counter()
    for _ in range(sample_total):
        if verify(shipping, random_candidate(shipping, sample_rng))[0]:
            sample_hits += 1
    sample_wall = time.perf_counter() - sample_started
    report["G4_guess_resistance"] = {
        "pass": sample_hits / sample_total < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "observed_probability": sample_hits / sample_total,
        "certificate_space": search_space(shipping),
        "wall_clock_sec": round(sample_wall, 6),
    }

    reference_answer, reference_stats = _reference_algorithm(shipping)
    compact_answer, compact_stats = _compact_route(shipping)
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": (
            demo_count == 1
            and reference_answer is not None
            and verify(shipping, reference_answer)[0]
            and compact_answer is not None
            and verify(shipping, compact_answer)[0]
        ),
        "shipping_density_hits": sample_hits,
        "shipping_density_samples": sample_total,
        "shipping_sampled_valid_fraction": sample_hits / sample_total,
        "demo_exact_solution_count": demo_count,
        "demo_certificate_space": search_space(demo),
        "reference_algorithm_operations": reference_stats["operations"],
        "reference_algorithm_wall_clock_sec": round(reference_stats["wall_clock_sec"], 6),
        "compact_route_operations": compact_stats["operations"],
    }

    attack_counts = {
        "outlier_coefficient_support": 0,
        "greedy_single_equation": 0,
        "random_restart_256": 0,
        "unaligned_walsh_ansatz": 0,
    }
    reference_runs = []
    for seed in range(310, 318):
        attacked = make_instance(seed=seed, **shipping_params)
        attack_counts["outlier_coefficient_support"] += int(_attack_outlier_support(attacked))
        attack_counts["greedy_single_equation"] += int(_attack_greedy_single_equation(attacked))
        attack_counts["random_restart_256"] += int(_attack_random_restart(attacked, seed))
        attack_counts["unaligned_walsh_ansatz"] += int(_attack_unaligned_walsh(attacked))
        found, stats = _reference_algorithm(attacked)
        stats["solved"] = bool(found is not None and verify(attacked, found)[0])
        reference_runs.append(stats)
    attacks = {
        name: {"successes": successes, "attempts": 8}
        for name, successes in attack_counts.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attacks.values())
        and all(run["solved"] for run in reference_runs),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "anchor-minor extraction followed by exact modular Gaussian elimination",
            "complexity": "O(k^3) field operations for k=d^2 variables",
            "operations": reference_stats["operations"],
            "max_operations": max(run["operations"] for run in reference_runs),
            "wall_clock_sec": round(reference_stats["wall_clock_sec"], 6),
            "max_wall_clock_sec": round(max(run["wall_clock_sec"] for run in reference_runs), 6),
            "solves": f"{sum(run['solved'] for run in reference_runs)}/8, as expected",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] = _next_prime(2 * shipping["field"] + 1)
    doubled = make_instance(seed=991, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["field"] > shipping["field"]
        and search_space(doubled) > search_space(shipping)
        and len(json.dumps(doubled["answer"])) < 2000,
        "shipping_n": shipping["field"],
        "doubled_n": doubled["field"],
        "doubled_verify_reason": doubled_reason,
        "answer_coordinates_unchanged": doubled["variables"] == shipping["variables"],
        "search_space_growth_bits": search_space(doubled).bit_length() - search_space(shipping).bit_length(),
    }

    invariance_checks = 0
    carried_checks = 0
    key_failures = []
    unrelated_keys = set()
    for seed in range(20):
        instance = make_instance(seed=8000 + seed, **shipping_params)
        base_key = canonical_key(instance)
        unrelated_keys.add(base_key)
        rng = random.Random(9000 + seed)
        variable_perm = list(range(instance["variables"]))
        row_perm = list(range(instance["matrix_size"]))
        column_perm = list(range(instance["matrix_size"]))
        rng.shuffle(variable_perm)
        rng.shuffle(row_perm)
        rng.shuffle(column_perm)
        variants = [
            _relabel_variables(instance, variable_perm),
            _permute_matrix(instance, row_perm, column_perm),
            _permute_matrix(_relabel_variables(instance, variable_perm), row_perm, column_perm),
        ]
        for variant in variants:
            invariance_checks += 1
            if canonical_key(variant) != base_key:
                key_failures.append({"seed": seed, "kind": "invariance"})
            carried_checks += 1
            if not verify(variant, variant["answer"])[0]:
                key_failures.append({"seed": seed, "kind": "carried_witness"})
    report["G8_canonical_key"] = {
        "pass": not key_failures and len(unrelated_keys) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated": len(unrelated_keys),
        "unrelated_attempts": 20,
        "failures": key_failures,
    }

    answer_blobs = [
        json.dumps(make_instance(seed=seed, **shipping_params)["answer"])
        for seed in range(100)
    ]
    answer_chars = max(map(len, answer_blobs))
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    compact_ok = compact_answer is not None and verify(shipping, compact_answer)[0]
    arms = copy.deepcopy(G9_ORACLE_RESULTS)
    hinted_verdict = arms.pop("hinted_verdict", "not_run")
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    g9_measured = all(arms[name]["attempts"] >= 3 for name in ("bare", "hinted", "placebo"))
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and compact_stats["operations"] <= 300
    report["G9_no_tool_suitability"] = {
        "pass": g9_measured and hinted_verdict == "hardened" and within_caps and compact_ok,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": hinted_verdict,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact_stats["operations"],
        "intended_route_verified": compact_ok,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping_params)
    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
