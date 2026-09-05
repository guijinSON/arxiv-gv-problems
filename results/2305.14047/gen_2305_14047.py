"""Self-contained maximal quasi-clique generator for arXiv:2305.14047.

The paper explicitly observes that a 1-quasi-clique is a clique. This module
constructs a succinct Cayley graph over F_q^d. A one-dimensional kernel gives
an affine line which is a maximal clique. The kernel is known before the graph
is assembled: its direction is a geometric-progression vector, and every
displayed linear form is constructed to vanish on it.
"""

from __future__ import annotations

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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # The implementation remains standard-library-only.
    exact_matrices = rationals = None


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "Read each displayed constraint row as polynomial coefficients: the rows "
    "share a root in the stated finite field."
)
PLACEBO_HINT: str = (
    "Keep the finite-field reductions and the coordinate ordering consistent "
    "throughout your calculation."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "graph",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "succinct undirected unweighted Cayley graph",
        "maximal 1-quasi-clique",
        "affine line over a prime field",
    ],
    "verification_operations": [
        "exact modular matrix-vector product",
        "exact affine-line normalization",
        "exact adjacency-rule evaluation",
        "symbolic maximality check using the graph's forced hole",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The graph's dense direction is the common evaluation vector of the "
        "displayed polynomial rows; without recognizing that invariant, a "
        "solver must inspect millions of projective directions."
    ),
    "hardness_basis": (
        "Track B: Section 3's standard Quick+ search is O*(2^N) and Theorem 1 "
        "gives FastQC O(N*d*alpha_k^N); for the displayed algebraic encoding, "
        "the stronger reference algorithm is modular Gaussian elimination in "
        "O(d^3), measured at 495,207 median exact field operations and 0.0159 "
        "seconds on the shipping preset, while "
        "recognizing the common polynomial root and folding exponents modulo "
        "|F_5^*| cuts the route to O(d+q^2), 209 median operations measured "
        "and 215 in the worst case."
    ),
    "max_answer_tokens": 98,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

# n is the vector-space dimension and q the prime field order. The graph has
# q**n vertices; the answer always remains two vectors (base and direction).
DIFFICULTY: dict = {
    "demo": {"n": 2, "q": 3},
    "easy": {"n": 32, "q": 5},
    "medium": {"n": 64, "q": 5},
    "hard": {"n": 96, "q": 5},
}
SHIPPING_DIFFICULTY: str = "hard"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A 2-by-d matrix [base,direction] over F_q encoding an affine line. "
        "The direction's first nonzero coordinate is 1, and the base has 0 in "
        "that pivot coordinate, so every affine line has one encoding."
    ),
    "bounds": {
        "rows": 2,
        "shipping_dimension": 96,
        "shipping_field_order": 5,
        "entry_min": 0,
        "entry_max_shipping": 4,
    },
}

NOTES: str = (
    "Section 2.1 fixes the exact object: all subgraphs are induced; a "
    "gamma-quasi-clique is connected and has internal degree at least "
    "ceil(gamma*(|H|-1)); gamma is at least 1/2; and a 1-quasi-clique is a "
    "clique. The same section warns that maximality testing is NP-hard for "
    "general quasi-cliques. This family uses gamma=1, where heredity makes "
    "maximality executable, and the graph's forced-hole rule supplies an exact "
    "symbolic blocker for every outside vertex. Section 3 gives Quick+'s "
    "O*(2^N) search, Theorem 1 gives FastQC's O(N*d*alpha_k^N) search, and "
    "Section 6 reports that larger gamma and theta are easier while denser "
    "graphs weaken degree pruning. Accordingly this is Track B, not a false "
    "average-case Track A claim. The generator samples the common root first, "
    "constructs independent polynomial multiples of X-root, and carries the "
    "geometric evaluation vector as its certificate. All vertices have the "
    "same degree, defeating degree outliers. Coordinate-axis, one-row greedy, "
    "small-ratio ansatz, and random-line attacks are tested separately. The "
    "successful modular Gaussian elimination is disclosed as the reference "
    "algorithm rather than hidden among failing attacks; the common-root scan "
    "is the substantially shorter intended route."
)

G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0, "error_records": 4},
        "hinted": {"solved": 0, "attempts": 0, "error_records": 4},
        "placebo": {"solved": 0, "attempts": 0, "error_records": 4},
    },
    "hinted_verdict": "unavailable_api_limit",
}

_ENUMERATION_CAP = 100_000
_RANDOM_LINE_RESTARTS = 16_384


def _is_prime(value):
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _validate_parameters(n, q):
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer dimension")
    if isinstance(q, bool) or not isinstance(q, int):
        raise TypeError("q must be an integer prime")
    if n < 2:
        raise ValueError("n must be at least 2")
    if q < 3 or q % 2 == 0 or not _is_prime(q):
        raise ValueError("q must be an odd prime")


def _dot(left, right, q):
    return sum(a * b for a, b in zip(left, right)) % q


def _poly_eval(coefficients, value, q):
    result = 0
    for coefficient in reversed(coefficients):
        result = (result * value + coefficient) % q
    return result


def _multiply_by_linear(quotient, root, q):
    """Coefficient list of (X-root)*quotient(X)."""
    product = [0] * (len(quotient) + 1)
    for index, coefficient in enumerate(quotient):
        product[index] = (product[index] - root * coefficient) % q
        product[index + 1] = (product[index + 1] + coefficient) % q
    return product


def _sample_root_free_quotient(length, q, rng):
    """Sample Q with Q(0)=1 and no root in F_q (normally full degree)."""
    if length == 1:
        return [1]
    # A nonconstant linear polynomial over a field always has a root.  Keep a
    # padded constant here so the supported n=3 case remains total.
    if length == 2:
        return [1, 0]
    while True:
        coefficients = [1]
        coefficients.extend(rng.randrange(q) for _ in range(length - 2))
        coefficients.append(rng.randrange(1, q))
        if all(_poly_eval(coefficients, value, q) != 0
               for value in range(q)):
            return coefficients


def _mixed_quotient_basis(first_row, q, rng):
    """An invertible row basis whose first row stays fixed."""
    size = len(first_row)
    if size == 1:
        return [list(first_row)]
    rows = [list(first_row)]
    for index in range(1, size):
        row = [0] * size
        row[index] = 1
        rows.append(row)
    # Independence is preserved by invertible elementary row operations.
    for _ in range(10 * size):
        operation = rng.randrange(3)
        if operation == 0 and size > 2:
            i, j = rng.sample(range(1, size), 2)
            rows[i], rows[j] = rows[j], rows[i]
        elif operation == 1:
            i = rng.randrange(1, size)
            factor = rng.randrange(1, q)
            rows[i] = [(entry + factor * base) % q
                       for entry, base in zip(rows[i], rows[0])]
        elif size > 2:
            i, j = rng.sample(range(1, size), 2)
            factor = rng.randrange(1, q)
            rows[i] = [(entry + factor * other) % q
                       for entry, other in zip(rows[i], rows[j])]
    return rows


def _threshold_vector(n, q, seed):
    half_bound = (q - 3) // 2
    if half_bound == 0:
        return [0] * (n - 1)
    radix = half_bound + 1
    code = seed % (radix ** (n - 1))
    thresholds = []
    for _ in range(n - 1):
        thresholds.append(code % radix)
        code //= radix
    return thresholds


def make_instance(n, seed=0, q=5, **params) -> dict:
    """Construct a maximal affine-line 1-quasi-clique certificate first."""
    if params:
        unknown = ", ".join(sorted(params))
        raise TypeError(f"unknown parameters: {unknown}")
    _validate_parameters(n, q)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    rng = random.Random(seed)

    root = 1 if q == 3 else rng.randrange(2, q - 1)
    direction = [1]
    for _ in range(1, n):
        direction.append(direction[-1] * root % q)

    quotient = _sample_root_free_quotient(n - 1, q, rng)
    quotient_rows = _mixed_quotient_basis(quotient, q, rng)
    constraints = [_multiply_by_linear(row, root, q)
                   for row in quotient_rows]

    # Complete the constraint rows to an invertible coordinate transform.
    leading_form = [rng.randrange(q) for _ in range(n)]
    correction = (1 - _dot(leading_form, direction, q)) % q
    leading_form[0] = (leading_form[0] + correction) % q

    holes = [rng.randrange(q) for _ in range(n - 1)]
    thresholds = _threshold_vector(n, q, seed)
    base = [0] + [rng.randrange(q) for _ in range(n - 1)]
    return {
        "n": n,
        "q": q,
        "gamma": [1, 1],
        "vertex_count": q ** n,
        "leading_form": leading_form,
        "constraints": constraints,
        "thresholds": thresholds,
        "holes": holes,
        "answer": [base, direction],
    }


def _transformed_difference(inst, difference):
    q = inst["q"]
    leading = _dot(inst["leading_form"], difference, q)
    syndrome = [_dot(row, difference, q)
                for row in inst["constraints"]]
    return leading, syndrome


def _adjacent_difference(inst, difference):
    """Exact adjacency for a non-oriented Cayley difference."""
    q = inst["q"]
    if all(value % q == 0 for value in difference):
        return False
    leading, syndrome = _transformed_difference(inst, difference)
    if not any(syndrome):
        return True
    first = next(index for index, value in enumerate(syndrome) if value)
    residue = syndrome[first]
    if min(residue, q - residue) > inst["thresholds"][first]:
        return False
    hole = _dot(inst["holes"], syndrome, q)
    return leading != hole


def _canonical_line(base, direction, q):
    nonzero = [index for index, value in enumerate(direction) if value % q]
    if not nonzero:
        return None
    pivot = nonzero[0]
    scale = pow(direction[pivot] % q, -1, q)
    normalized = [value * scale % q for value in direction]
    shift = base[pivot] % q
    canonical_base = [(value - shift * step) % q
                      for value, step in zip(base, normalized)]
    return [canonical_base, normalized]


def render(inst) -> str:
    """Render the complete succinct graph and exact output contract."""
    n = inst["n"]
    q = inst["q"]
    example = [[0] * n, [1] + [0] * (n - 1)]
    rows = "\n".join(f"m{i} = " + " ".join(map(str, row))
                     for i, row in enumerate(inst["constraints"]))
    text = f"""Find a maximal affine-line 1-quasi-clique in a succinct graph.

All arithmetic below is in the prime field F_{q}: reduce every integer modulo
{q}. The graph is finite, simple, undirected, and unweighted. Its vertices are
all {n}-coordinate vectors over F_{q}, so it has {q}^{n} =
{inst['vertex_count']} vertices. The subgraph induced by a vertex set contains
exactly the edges whose endpoints both belong to that set.

For two distinct vertices x and y, put delta=x-y coordinatewise modulo {q}.
Compute z0 = r dot delta and s_i = m_i dot delta for i=0,...,{n - 2},
where "dot" is the ordinary dot product reduced modulo {q}, and

r  = {' '.join(map(str, inst['leading_form']))}
{rows}

The {n - 1} displayed rows m_i are promised to be linearly independent over
F_{q}.

Let s=(s_0,...,s_{n - 2}). If every s_i is zero, x and y are adjacent.
Otherwise let j be the smallest index with s_j nonzero. They are adjacent if
and only if BOTH conditions hold:

  1. min(s_j, {q}-s_j) <= h_j, where
     h = {' '.join(map(str, inst['thresholds']))};
  2. z0 is not equal to c dot s modulo {q}, where
     c = {' '.join(map(str, inst['holes']))}.

This rule is symmetric under delta -> -delta, so it defines an undirected
graph. A gamma-quasi-clique H is a connected induced subgraph in which every
vertex has at least ceil(gamma*(|H|-1)) neighbors in H. Here gamma=1, so a
1-quasi-clique is exactly a clique. It is maximal when no strictly larger
1-quasi-clique contains it.

An affine line is L(b,v)={{b+t*v : t in F_{q}}}, with v nonzero. Return one
affine line whose {q} vertices induce a maximal 1-quasi-clique. Encode it as
the JSON matrix [b,v], with exactly two rows of {n} integers in 0..{q - 1}.
Use the unique canonical encoding: the first nonzero coordinate v[p] must be
1, and b[p] must be 0. Vector order and coordinate order are fixed as printed;
no repeated/missing coordinates are allowed.

Give your final answer inside <answer></answer> tags as that JSON matrix.
Example of the required shape: <answer>{json.dumps(example, separators=(',', ':'))}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def _json_arrays(text):
    decoder = json.JSONDecoder()
    values = []
    for match in re.finditer(r"\[", text):
        try:
            value, _ = decoder.raw_decode(text[match.start():])
        except (ValueError, TypeError):
            continue
        if isinstance(value, list):
            values.append(value)
    return values


def parse_answer(text) -> object | None:
    """Parse the last tagged/fenced 2-row JSON matrix without raising."""
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer\s*>(.*?)</answer\s*>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    sources = tagged[-1:] if tagged else re.findall(
        r"```(?:json|text)?\s*(.*?)```", text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    for source in reversed(sources or [text]):
        arrays = _json_arrays(source)
        for value in reversed(arrays):
            if len(value) == 2 and all(isinstance(row, list) for row in value):
                return value
    return None


def verify(inst, answer) -> tuple[bool, str]:
    """Verify any canonical affine-line certificate, never the planted one."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON matrix"
    if not answer:
        return False, "answer is empty"
    if len(answer) != 2:
        return False, "answer must contain exactly two rows: base and direction"
    if any(not isinstance(row, list) for row in answer):
        return False, "both matrix rows must be lists"
    n = inst["n"]
    if any(len(row) != n for row in answer):
        return False, f"each row must contain exactly {n} coordinates"
    if any(isinstance(value, bool) or not isinstance(value, int)
           for row in answer for value in row):
        return False, "every coordinate must be an integer"
    q = inst["q"]
    if any(value < 0 or value >= q for row in answer for value in row):
        return False, f"coordinate outside the inclusive range 0..{q - 1}"

    base, direction = answer
    nonzero = [index for index, value in enumerate(direction) if value]
    if not nonzero:
        return False, "direction must be nonzero"
    pivot = nonzero[0]
    if direction[pivot] != 1:
        return False, "direction is not canonical: first nonzero entry must be 1"
    if base[pivot] != 0:
        return False, "base is not canonical: its pivot coordinate must be 0"

    leading, syndrome = _transformed_difference(inst, direction)
    if any(syndrome):
        return False, "the affine line is not a 1-quasi-clique"
    if leading == 0:
        return False, "invalid graph transform: line direction maps to zero"

    # For an outside vertex, s is nonzero and constant along the line. As t
    # ranges over F_q, z0 ranges over F_q (leading != 0), so one point hits the
    # executable hole z0=c dot s. No outside vertex extends the clique.
    bound = (q - 3) // 2
    if (len(inst["thresholds"]) != n - 1
            or any(value < 0 or value > bound for value in inst["thresholds"])
            or len(inst["holes"]) != n - 1):
        return False, "instance does not provide a valid maximality hole"
    return True, "ok"


def _encode_vector(code, n, q):
    vector = []
    for _ in range(n):
        vector.append(code % q)
        code //= q
    return vector


def random_candidate(inst, rng) -> object:
    """Uniformly sample the stated language of canonical affine lines."""
    n, q = inst["n"], inst["q"]
    raw = rng.randrange(1, q ** n)
    direction = _encode_vector(raw, n, q)
    pivot = next(index for index, value in enumerate(direction) if value)
    scale = pow(direction[pivot], -1, q)
    direction = [value * scale % q for value in direction]
    base = [rng.randrange(q) for _ in range(n)]
    shift = base[pivot]
    base = [(value - shift * step) % q
            for value, step in zip(base, direction)]
    return [base, direction]


def search_space(inst) -> int | None:
    n, q = inst["n"], inst["q"]
    return ((q ** n - 1) // (q - 1)) * q ** (n - 1)


def enumerate_all(inst) -> int | None:
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    n, q = inst["n"], inst["q"]
    valid = 0
    for raw in range(1, q ** n):
        direction = _encode_vector(raw, n, q)
        pivot = next(index for index, value in enumerate(direction) if value)
        if direction[pivot] != 1:
            continue
        for free in itertools.product(range(q), repeat=n - 1):
            iterator = iter(free)
            base = [0 if index == pivot else next(iterator)
                    for index in range(n)]
            valid += verify(inst, [base, direction])[0]
    return valid


def _allowed_syndrome_count(inst):
    q = inst["q"]
    width = len(inst["thresholds"])
    return sum(2 * threshold * q ** (width - index - 1)
               for index, threshold in enumerate(inst["thresholds"]))


def canonical_key(inst) -> str:
    """Strong cheap invariant: order, field, and exact regular degree."""
    q = inst["q"]
    degree = (q - 1) * (1 + _allowed_syndrome_count(inst))
    payload = [inst["vertex_count"], q, inst["n"], degree, inst["gamma"]]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def _next_prime(value):
    candidate = value + 1
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def escalate(params) -> dict | str | None:
    n, q = params.get("n"), params.get("q")
    if not isinstance(n, int) or not isinstance(q, int):
        return None
    # Exponent folding keeps the compact route below 300 operations through
    # n=128, which is also the 256-atom certificate limit.
    if q == 5 and n < 128:
        return {"n": min(128, n + 16), "q": q}
    return None


# ---------------------------------------------------------------------------
# Reference solver and construction-aware attacks.


def _root_reference(inst):
    """Compact Track-B algorithm: fold exponents, then scan field roots."""
    q = inst["q"]
    coefficients = inst["constraints"][0]
    operations = 0
    cycle = q - 1
    folded = [0] * cycle
    for exponent, coefficient in enumerate(coefficients):
        folded[exponent % cycle] = (
            folded[exponent % cycle] + coefficient
        ) % q
        operations += 1
    # The constant coefficient is nonzero in generated instances, so zero is
    # not a root.  For nonzero x, x^(q-1)=1 justifies the exponent folding.
    for root in range(1, q):
        value = folded[-1]
        for coefficient in reversed(folded[:-1]):
            value = (value * root + coefficient) % q
            operations += 2
        if value == 0:
            direction = [1]
            for _ in range(1, inst["n"]):
                direction.append(direction[-1] * root % q)
                operations += 1
            candidate = [[0] * inst["n"], direction]
            if verify(inst, candidate)[0]:
                return candidate, operations, root
    return None, operations, q - 1


def _mechanical_reference(inst):
    """Find the one-dimensional kernel by modular Gaussian elimination.

    This deliberately ignores the polynomial interpretation of the rows.  It
    is the strongest standard algorithm exposed by the succinct encoding and
    therefore the honest Track-B mechanical baseline.
    """
    q, n = inst["q"], inst["n"]
    matrix = [row[:] for row in inst["constraints"]]
    row_index = 0
    pivots = []
    operations = 0
    for column in range(n):
        pivot = next((r for r in range(row_index, len(matrix))
                      if matrix[r][column] % q), None)
        if pivot is None:
            continue
        matrix[row_index], matrix[pivot] = matrix[pivot], matrix[row_index]
        inverse = pow(matrix[row_index][column], -1, q)
        operations += 1
        for j in range(column, n):
            matrix[row_index][j] = matrix[row_index][j] * inverse % q
            operations += 1
        for other in range(len(matrix)):
            if other == row_index:
                continue
            factor = matrix[other][column] % q
            if factor:
                for j in range(column, n):
                    matrix[other][j] = (
                        matrix[other][j] - factor * matrix[row_index][j]
                    ) % q
                    operations += 2
        pivots.append(column)
        row_index += 1
        if row_index == len(matrix):
            break

    free_columns = [column for column in range(n) if column not in pivots]
    if len(free_columns) != 1 or len(pivots) != n - 1:
        return None, operations, len(pivots)
    direction = [0] * n
    direction[free_columns[0]] = 1
    for r in range(len(pivots) - 1, -1, -1):
        pivot_column = pivots[r]
        total = 0
        for column in range(pivot_column + 1, n):
            total = (total + matrix[r][column] * direction[column]) % q
            operations += 2
        direction[pivot_column] = -total % q
        operations += 1
    candidate = _canonical_line([0] * n, direction, q)
    return candidate, operations, len(pivots)


def _try_directions(inst, directions):
    q = inst["q"]
    for direction in directions:
        candidate = _canonical_line([0] * inst["n"], direction, q)
        if candidate is not None and verify(inst, candidate)[0]:
            return candidate
    return None


def _outlier_regular_attack(inst):
    n, q = inst["n"], inst["q"]
    directions = []
    for index in range(n):
        vector = [0] * n
        vector[index] = 1
        directions.append(vector)
    directions.extend(([1] * n,
                       [1 if i % 2 == 0 else q - 1 for i in range(n)]))
    return _try_directions(inst, directions)


def _greedy_one_row_attack(inst):
    q, n = inst["q"], inst["n"]
    row = inst["constraints"][0]
    directions = []
    for free_index in range(1, n):
        vector = [0] * n
        vector[free_index] = 1
        if row[0] % q:
            vector[0] = -row[free_index] * pow(row[0], -1, q) % q
        directions.append(vector)
    return _try_directions(inst, directions)


def _small_ratio_ansatz(inst):
    q, n = inst["q"], inst["n"]
    directions = []
    for ratio in (0, 1, q - 1):
        vector = [1]
        for _ in range(1, n):
            vector.append(vector[-1] * ratio % q)
        directions.append(vector)
    return _try_directions(inst, directions)


def _matrix_row_ansatz(inst):
    return _try_directions(
        inst, list(inst["constraints"]) + [inst["leading_form"]]
    )


def _random_line_attack(inst, attack_seed, attempts=_RANDOM_LINE_RESTARTS):
    rng = random.Random(attack_seed ^ 0x230514047)
    for _ in range(attempts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _invert_matrix(matrix, q):
    """Gauss-Jordan inverse used only to carry G8 relabellings."""
    size = len(matrix)
    augmented = [list(row) + [1 if i == j else 0 for j in range(size)]
                 for i, row in enumerate(matrix)]
    for column in range(size):
        pivot = next((row for row in range(column, size)
                      if augmented[row][column] % q), None)
        if pivot is None:
            raise ValueError("matrix is singular")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        scale = pow(augmented[column][column] % q, -1, q)
        augmented[column] = [value * scale % q for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column] % q
            if factor:
                augmented[row] = [(value - factor * source) % q
                                  for value, source in
                                  zip(augmented[row], augmented[column])]
    return [row[size:] for row in augmented]


def _mat_vec(matrix, vector, q):
    return [_dot(row, vector, q) for row in matrix]


def _mat_mul(left, right, q):
    columns = list(zip(*right))
    return [[_dot(row, column, q) for column in columns] for row in left]


def _random_invertible_pair(size, q, rng):
    matrix = [[1 if i == j else 0 for j in range(size)] for i in range(size)]
    inverse = [row[:] for row in matrix]
    for _ in range(8 * size):
        kind = rng.randrange(3)
        if kind == 0:
            i, j = rng.sample(range(size), 2)
            matrix[i], matrix[j] = matrix[j], matrix[i]
            for row in inverse:
                row[i], row[j] = row[j], row[i]
        elif kind == 1:
            i = rng.randrange(size)
            factor = rng.randrange(1, q)
            inv_factor = pow(factor, -1, q)
            matrix[i] = [factor * value % q for value in matrix[i]]
            for row in inverse:
                row[i] = row[i] * inv_factor % q
        else:
            i, j = rng.sample(range(size), 2)
            factor = rng.randrange(1, q)
            matrix[i] = [(value + factor * other) % q
                         for value, other in zip(matrix[i], matrix[j])]
            for row in inverse:
                row[j] = (row[j] - factor * row[i]) % q
    return matrix, inverse


def _relabel_instance(inst, linear, inverse, translation):
    """Carry x -> linear*x+translation through the succinct graph."""
    q = inst["q"]
    inverse_columns = list(zip(*inverse))
    leading = [_dot(inst["leading_form"], column, q)
               for column in inverse_columns]
    constraints = [[_dot(row, column, q) for column in inverse_columns]
                   for row in inst["constraints"]]
    old_base, old_direction = inst["answer"]
    new_base = [(value + shift) % q for value, shift in
                zip(_mat_vec(linear, old_base, q), translation)]
    new_direction = _mat_vec(linear, old_direction, q)
    return {
        **inst,
        "leading_form": leading,
        "constraints": constraints,
        "answer": _canonical_line(new_base, new_direction, q),
    }


def _atomic_elements(value):
    if isinstance(value, dict):
        return sum(_atomic_elements(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atomic_elements(item) for item in value)
    return 1


def selftest() -> dict:
    report = {}
    failures = []
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            json_roundtrips += json.loads(json.dumps(inst["answer"])) == inst["answer"]
    report["G1_planted_verifies"] = {
        "pass": not failures and json_roundtrips == 12,
        "attempts": 12,
        "failures": failures,
        "json_roundtrips": json_roundtrips,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=101, **shipping_params)
    base, direction = [row[:] for row in inst["answer"]]
    axis = [1] + [0] * (inst["n"] - 1)
    corruptions = {
        "drop": [base],
        "swap_one": [base, axis],
        "duplicate": [direction, direction],
        "empty": [],
        "out_of_range": [[inst["q"]] + base[1:], direction],
    }
    cases, reasons = {}, []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and len(set(reasons)) == len(reasons),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    response = ("The common direction is below.\n```json\n<answer>"
                + json.dumps(inst["answer"], separators=(",", ":"))
                + "</answer>\n```\n")
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and parse_answer("no matrix here") is None,
        "parsed_matches": parsed == inst["answer"],
        "garbage_returns_none": parse_answer("no matrix here") is None,
    }

    guess_rng = random.Random(0x230514047)
    guess_total = 200_000
    guess_hits = sum(
        verify(inst, random_candidate(inst, guess_rng))[0]
        for _ in range(guess_total)
    )
    directions = (inst["q"] ** inst["n"] - 1) // (inst["q"] - 1)
    exact_probability = 1 / directions
    report["G4_guess_resistance"] = {
        "pass": exact_probability < 1e-6 and guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "exact_probability": exact_probability,
        "valid_directions": 1,
        "projective_directions": directions,
        "structure_aware_space": search_space(inst),
        "sampler": "uniform over canonical affine lines, not arbitrary vertex sets",
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    attack_names = (
        "outlier_regular_degree",
        "greedy_one_constraint",
        "small_ratio_geometric_ansatz",
        "matrix_row_ansatz",
        "random_affine_lines_16384",
    )
    successes = {name: 0 for name in attack_names}
    random_times, reference_times = [], []
    reference_operations, reference_candidates = [], []
    compact_times, compact_operations, compact_checked = [], [], []
    reference_failures = []
    attempts = 8
    for seed in range(attempts):
        attacked = make_instance(seed=10_000 + seed, **shipping_params)
        successes["outlier_regular_degree"] += _outlier_regular_attack(attacked) is not None
        successes["greedy_one_constraint"] += _greedy_one_row_attack(attacked) is not None
        successes["small_ratio_geometric_ansatz"] += _small_ratio_ansatz(attacked) is not None
        successes["matrix_row_ansatz"] += _matrix_row_ansatz(attacked) is not None
        started = time.perf_counter()
        random_answer = _random_line_attack(attacked, seed)
        random_times.append(time.perf_counter() - started)
        successes["random_affine_lines_16384"] += random_answer is not None

        started = time.perf_counter()
        reference, operations, checked = _mechanical_reference(attacked)
        reference_times.append(time.perf_counter() - started)
        reference_operations.append(operations)
        reference_candidates.append(checked)
        if reference is None or not verify(attacked, reference)[0]:
            reference_failures.append(seed)

        started = time.perf_counter()
        compact, operations, checked = _root_reference(attacked)
        compact_times.append(time.perf_counter() - started)
        compact_operations.append(operations)
        compact_checked.append(checked)
        if compact is None or not verify(attacked, compact)[0]:
            reference_failures.append(seed)

    attacks = {name: {"successes": successes[name], "attempts": attempts}
               for name in attack_names}
    exact_valid_lines = inst["q"] ** (inst["n"] - 1)
    report["G5_density_and_baseline"] = {
        "pass": isinstance(demo_count, int) and demo_count > 0,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_sampled_solution_fraction": guess_hits / guess_total,
        "shipping_exact_valid_line_count": exact_valid_lines,
        "shipping_exact_solution_fraction": exact_probability,
        "demo_exact_solution_count": demo_count,
        "demo_certificate_space": search_space(demo),
        "strongest_failing_attack": "random affine-line restarts",
        "baseline_restarts_per_seed": _RANDOM_LINE_RESTARTS,
        "baseline_median_wall_seconds": statistics.median(random_times),
        "baseline_seed_times_seconds": random_times,
        "reference_matrix_shape": [inst["n"] - 1, inst["n"]],
    }
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attacks.values())
        and not reference_failures,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "modular Gaussian elimination",
            "complexity": "O(d^3) exact field operations",
            "wall_clock_sec_median": statistics.median(reference_times),
            "wall_clock_sec_by_seed": reference_times,
            "operations_median": int(statistics.median(reference_operations)),
            "operations_max": max(reference_operations),
            "pivots_median": int(statistics.median(reference_candidates)),
            "pivots_by_seed": reference_candidates,
            "solves": "8/8, as expected" if not reference_failures else "failed",
        },
        "compact_algorithm": {
            "name": "common-root scan after finite-field exponent folding",
            "complexity": "O(d+q^2) after recognizing polynomial rows",
            "wall_clock_sec_median": statistics.median(compact_times),
            "operations_median": int(statistics.median(compact_operations)),
            "operations_max": max(compact_operations),
            "field_values_checked": compact_checked,
            "solves": "8/8, as expected" if not reference_failures else "failed",
        },
    }

    doubled = make_instance(n=2 * shipping_params["n"],
                            q=shipping_params["q"], seed=2026)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst),
        "shipping_dimension": inst["n"],
        "doubled_dimension": doubled["n"],
        "shipping_graph_vertices": inst["vertex_count"],
        "doubled_graph_vertices": doubled["vertex_count"],
        "shipping_space_bits": search_space(inst).bit_length(),
        "doubled_space_bits": search_space(doubled).bit_length(),
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = carried_checks = 0
    for seed in range(20):
        original = make_instance(seed=50_000 + seed, **shipping_params)
        key = canonical_key(original)
        rng = random.Random(60_000 + seed)
        linear, inverse = _random_invertible_pair(original["n"], original["q"], rng)
        identity = [[1 if i == j else 0 for j in range(original["n"])]
                    for i in range(original["n"])]
        zero = [0] * original["n"]
        translation = [rng.randrange(original["q"]) for _ in range(original["n"])]
        order = list(range(original["n"]))
        rng.shuffle(order)
        permutation = [[1 if order[i] == j else 0 for j in range(original["n"])]
                       for i in range(original["n"])]
        permutation_inverse = _invert_matrix(permutation, original["q"])
        composed = _mat_mul(permutation, linear, original["q"])
        composed_inverse = _mat_mul(inverse, permutation_inverse, original["q"])
        transforms = ((linear, inverse, zero),
                      (identity, identity, translation),
                      (permutation, permutation_inverse, zero),
                      (composed, composed_inverse, translation))
        for matrix, matrix_inverse, shift in transforms:
            transformed = _relabel_instance(original, matrix, matrix_inverse, shift)
            invariance_checks += canonical_key(transformed) == key
            carried_checks += verify(transformed, transformed["answer"])[0]

    unrelated_keys = {
        canonical_key(make_instance(seed=70_000 + seed, **shipping_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariance_checks == 80 and carried_checks == 80
        and len(unrelated_keys) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_attempts": 20,
        "unrelated_distinct": len(unrelated_keys),
        "transformations": [
            "random invertible linear coordinate change",
            "global affine translation",
            "coordinate permutation",
            "composed linear change, permutation, and translation",
        ],
        "key_basis": "vertex count and exact regular degree",
    }

    compact = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(compact)
    answer_elements = _atomic_elements(inst["answer"])
    answer_tokens = math.ceil(answer_chars / 4)
    intended_ops = (inst["n"]
                    + 2 * (inst["q"] - 1) * (inst["q"] - 2)
                    + inst["n"] - 1)
    arms = G9_RESULTS["arms"]
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else 0.0
    placebo_rate = arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else 0.0
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_ops <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "operation_definition": (
            "fold one degree-(d-1) row by exponents modulo q-1, evaluate the "
            "folded row at every nonzero field value, and write the direction"
        ),
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(value.get("pass", False)
                                  for key, value in report.items()
                                  if key.startswith("G"))
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["track"] = TRACK
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
