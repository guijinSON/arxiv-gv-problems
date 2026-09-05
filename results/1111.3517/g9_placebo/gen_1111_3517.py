"""Verified generator for hyperplane Roman functions on strong products.

The source is arXiv:1111.3517, especially the definition of the class F in
Section 2 and the closed-neighborhood partition used in the proof of Theorem
26.  Each factor is a Cayley graph on GF(p)^d whose connection set is sampled
as a polynomially parameterised transversal of a hidden hyperplane.  The
hyperplane is therefore an efficient dominating set by construction.  The
Cartesian product of the two hyperplanes efficiently dominates the strong
product, so assigning it value 2 and every other vertex value 0 is a Roman
dominating function.

The certificate is carried from the sampled hyperplane normals; it is never
found by solving the emitted instance.  Verification independently checks the
finite-field transversal identity and never reads ``inst["answer"]``.
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


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "Cayley graphs on finite vector spaces",
        "efficient dominating sets (perfect codes)",
        "strong product graph",
        "Roman dominating function represented by two affine hyperplanes",
    ],
    "verification_operations": [
        "exact finite-field inner product",
        "exact permutation test over GF(p)",
        "closed-neighborhood product identity",
        "exact Roman-weight calculation",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Notice that every nonlinear coefficient column in a factor lies in "
        "one codimension-one subspace; without that invariant one scans all "
        "projective normal directions and tests their connection-set images."
    ),
    "hardness_basis": (
        "Track B: Section 2 defines efficient domination by a partition of "
        "closed neighborhoods and the proof of Theorem 26 uses the same "
        "partition in a strong product; the reference projective-direction "
        "scan is O(p^(d+1)) exact field operations and, at shipping n=p=29 "
        "and d=5, it averaged 25,019,321 operations and 12.498 seconds over "
        "eight seeds, while the "
        "codimension-one coefficient invariant takes fewer than 300 exact "
        "operations for both factors."
    ),
    "max_answer_tokens": 12,
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

DIFFICULTY = {"easy": {"n": 29, "dimension": 5}}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Across all nonlinear powers, the coefficient columns of each factor lie "
    "in the same codimension-one subspace of the finite vector space."
)
PLACEBO_HINT = (
    "Across both factor descriptions, coefficient arithmetic and projective "
    "normalization must be performed carefully in the stated finite field."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object with exactly one key, normals, containing exactly two "
        "projectively normalized nonzero vectors in GF(p)^d.  Each vector has "
        "d canonical integer entries in 0,...,p-1 and its first nonzero entry "
        "is 1.  It represents the zero-offset hyperplane a dot x = 0."
    ),
    "bounds": {
        "factor_normals": 2,
        "dimension": "instance dimension d (at most 5 in the preset ladder)",
        "coefficient_min": 0,
        "coefficient_max": "p-1",
        "projective_normalization": "first nonzero entry equals 1",
        "candidate_count": "((p^d-1)/(p-1))^2",
    },
}

NOTES = (
    "Section 1 fixes Roman domination: only vertices labelled 0 need an "
    "adjacent vertex labelled 2.  Section 2 defines the class F through an "
    "efficient dominating set whose closed neighborhoods are pairwise "
    "disjoint, and explicitly identifies this with a perfect code.  Theorem "
    "8 uses that partition for Cartesian products; Section 3 defines the "
    "strong product, and the proof of Theorem 26 partitions it into sets "
    "N_G[u_i] x V(H).  Here each polynomial connection map is constructed as "
    "F(t)=t*w+sum h_j(t)u_j after sampling a normal a, with a*w=1 and all "
    "a*u_j=0.  Thus a*F(t)=t and ker(a) is a perfect code without search.  "
    "The product of two such codes is a perfect code in the strong product, "
    "and twice its indicator is the required Roman function.  The paper's "
    "Theorems 10, 17, and 23 are explicit upper-bound constructions, which "
    "rules out a Track A claim.  Dense random odd polynomials hide the normal, "
    "projective normalization removes scalar duplicates, and regular Cayley "
    "graphs defeat degree outliers.  The audited attacks cover coefficient "
    "energy, coordinate projection, the linear and leading-term ansatzes, and "
    "random restarts; the successful exhaustive scan is reported separately "
    "as Track B's reference algorithm."
)


# Replaced with script-owned measurements after the three oracle arms run.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unavailable_http_403_key_limit",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_prime(value):
    if not _is_int(value) or value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime(value):
    candidate = max(5, int(value))
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _rank_mod(rows, p):
    matrix = [[entry % p for entry in row] for row in rows]
    if not matrix:
        return 0
    n_rows = len(matrix)
    n_cols = len(matrix[0])
    rank = 0
    for column in range(n_cols):
        pivot = next(
            (row for row in range(rank, n_rows) if matrix[row][column]), None
        )
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        inverse = pow(matrix[rank][column], p - 2, p)
        matrix[rank] = [(value * inverse) % p for value in matrix[rank]]
        for row in range(n_rows):
            if row == rank or not matrix[row][column]:
                continue
            factor = matrix[row][column]
            matrix[row] = [
                (matrix[row][j] - factor * matrix[rank][j]) % p
                for j in range(n_cols)
            ]
        rank += 1
        if rank == n_rows:
            break
    return rank


def _rref_rows(rows, p):
    """Canonical row space over GF(p), returned as a tuple of tuples."""
    matrix = [[entry % p for entry in row] for row in rows]
    if not matrix:
        return ()
    n_rows = len(matrix)
    n_cols = len(matrix[0])
    rank = 0
    for column in range(n_cols):
        pivot = next(
            (row for row in range(rank, n_rows) if matrix[row][column]), None
        )
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        inverse = pow(matrix[rank][column], p - 2, p)
        matrix[rank] = [(value * inverse) % p for value in matrix[rank]]
        for row in range(n_rows):
            if row == rank or not matrix[row][column]:
                continue
            factor = matrix[row][column]
            matrix[row] = [
                (matrix[row][j] - factor * matrix[rank][j]) % p
                for j in range(n_cols)
            ]
        rank += 1
        if rank == n_rows:
            break
    nonzero = [row for row in matrix if any(row)]
    return tuple(tuple(row) for row in nonzero)


def _normalize_projective(vector, p):
    values = [value % p for value in vector]
    pivot = next((value for value in values if value), None)
    if pivot is None:
        return None
    inverse = pow(pivot, p - 2, p)
    return [(value * inverse) % p for value in values]


def _random_normal(dimension, p, rng):
    while True:
        values = [rng.randrange(p) for _ in range(dimension)]
        normal = _normalize_projective(values, p)
        if normal is not None:
            return normal


def _kernel_basis(normal, p):
    dimension = len(normal)
    pivot = next(index for index, value in enumerate(normal) if value)
    pivot_inverse = pow(normal[pivot], p - 2, p)
    basis = []
    for column in range(dimension):
        if column == pivot:
            continue
        vector = [0] * dimension
        vector[column] = 1
        vector[pivot] = (-normal[column] * pivot_inverse) % p
        basis.append(vector)
    return basis, pivot, pivot_inverse


def _randomize_kernel_basis(basis, p, rng):
    vectors = [list(vector) for vector in basis]
    count = len(vectors)
    for _ in range(8 * max(1, count)):
        operation = rng.randrange(3)
        if operation == 0 and count > 1:
            left, right = rng.sample(range(count), 2)
            vectors[left], vectors[right] = vectors[right], vectors[left]
        elif operation == 1:
            index = rng.randrange(count)
            scale = rng.randrange(1, p)
            vectors[index] = [(scale * value) % p for value in vectors[index]]
        elif count > 1:
            target, source = rng.sample(range(count), 2)
            scale = rng.randrange(1, p)
            vectors[target] = [
                (vectors[target][i] + scale * vectors[source][i]) % p
                for i in range(len(vectors[target]))
            ]
    return vectors


def _evaluate_coordinate_rows(coefficients, p):
    points = []
    for parameter in range(p):
        point = []
        for row in coefficients:
            value = 0
            for coefficient in reversed(row):
                value = (value * parameter + coefficient) % p
            point.append(value)
        points.append(point)
    return points


def _make_factor(p, dimension, rng):
    """Inverse-generate a polynomial Cayley factor and its hyperplane code."""
    normal = _random_normal(dimension, p, rng)
    kernel, pivot, pivot_inverse = _kernel_basis(normal, p)
    kernel = _randomize_kernel_basis(kernel, p, rng)

    transversal = [0] * dimension
    transversal[pivot] = pivot_inverse
    for vector in kernel:
        scale = rng.randrange(p)
        transversal = [
            (transversal[i] + scale * vector[i]) % p
            for i in range(dimension)
        ]

    nonlinear_degrees = list(range(3, p, 2))
    width = len(nonlinear_degrees)
    while True:
        mixing = [
            [rng.randrange(p) for _ in range(width)]
            for _ in range(dimension - 1)
        ]
        if _rank_mod(mixing, p) == dimension - 1:
            break

    coefficients = [[0] * p for _ in range(dimension)]
    for coordinate in range(dimension):
        coefficients[coordinate][1] = transversal[coordinate]
    for degree_index, degree in enumerate(nonlinear_degrees):
        for coordinate in range(dimension):
            coefficients[coordinate][degree] = sum(
                mixing[basis_index][degree_index]
                * kernel[basis_index][coordinate]
                for basis_index in range(dimension - 1)
            ) % p

    points = _evaluate_coordinate_rows(coefficients, p)
    # Construction audits: F is injective, odd, and the planted projection is t.
    if len({tuple(point) for point in points}) != p:
        raise AssertionError("constructed connection map is not injective")
    if any(
        sum(normal[i] * point[i] for i in range(dimension)) % p != parameter
        for parameter, point in enumerate(points)
    ):
        raise AssertionError("constructed normal lost its transversal identity")
    return {
        "coefficients": coefficients,
        "points": points,
    }, normal


def _validate_parameters(n, dimension):
    if not _is_int(n) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if not _is_int(dimension) or dimension < 2 or dimension > 5:
        raise ValueError("dimension must be an integer from 2 through 5")
    p = _next_prime(n)
    if (p - 1) // 2 < dimension - 1:
        raise ValueError("the field is too small for the requested dimension")
    return p


def make_instance(n, seed=0, dimension=4, **params) -> dict:
    """Build two factors and carry their perfect-code normals by construction.

    ``n`` controls the least permitted field size; the actual modulus is the
    least odd prime p >= n.  Larger n enlarges the projective direction scan
    while the answer remains two vectors of fixed dimension.
    """
    if params:
        raise ValueError("unknown parameters: " + ", ".join(sorted(params)))
    p = _validate_parameters(n, dimension)
    rng = random.Random(seed)
    factors = []
    normals = []
    for _ in range(2):
        factor, normal = _make_factor(p, dimension, rng)
        factors.append(factor)
        normals.append(normal)
    return {
        "n": n,
        "p": p,
        "dimension": dimension,
        "factors": factors,
        "answer": {"normals": normals},
    }


def _format_polynomial(row, variable="t"):
    terms = []
    for degree, coefficient in enumerate(row):
        if not coefficient:
            continue
        if degree == 0:
            term = str(coefficient)
        elif degree == 1:
            term = f"{coefficient}*{variable}"
        else:
            term = f"{coefficient}*{variable}^{degree}"
        terms.append(term)
    return " + ".join(terms) if terms else "0"


def render(inst) -> str:
    """Render a self-contained strong-product Roman-domination problem."""
    p = inst["p"]
    dimension = inst["dimension"]
    factor_text = []
    for index, factor in enumerate(inst["factors"]):
        lines = [f"Factor {index}: F_{index}(t) has coordinates"]
        for coordinate, row in enumerate(factor["coefficients"]):
            lines.append(
                f"  F_{index},{coordinate}(t) = {_format_polynomial(row)}"
            )
        factor_text.append("\n".join(lines))

    statement = f"""Find a compact Roman dominating function on a strong product graph.

All arithmetic below is in the prime field GF({p}); write every field element as
its canonical integer representative in the inclusive range 0,...,{p - 1}.
Vectors have dimension d={dimension}, coordinates are indexed 0,...,{dimension - 1},
and a dot product is reduced modulo {p}.

For i=0,1, a displayed polynomial map F_i:GF({p})->GF({p})^{dimension}
defines a connection set

  S_i = {{F_i(t) : t in GF({p})}}.

The maps are injective, F_i(0)=0, and F_i(-t)=-F_i(t).  Define the finite
simple undirected Cayley graph G_i as follows.  Its vertices are all vectors in
GF({p})^{dimension}.  Distinct x and y are adjacent exactly when y-x belongs to
S_i without {{0}}.  Thus the closed neighborhood of x is x+S_i.

The strong product G_0 strong G_1 has vertex pairs (x,y).  Two distinct pairs
(x,y) and (x',y') are adjacent exactly when, in each coordinate, the entries
are equal or adjacent in the corresponding factor, and at least one coordinate
is adjacent.  Equivalently,

  N[(x,y)] = N_G0[x] x N_G1[y].

An efficient dominating set (also called a perfect code) is a vertex set C
such that every closed neighborhood contains exactly one member of C.  A Roman
dominating function assigns 0, 1, or 2 to each vertex and requires every vertex
assigned 0 to have a neighbor assigned 2.

You must give two nonzero normal vectors a_0,a_1.  They define factor
hyperplanes C_i={{x : a_i dot x = 0}} and the product set C=C_0 x C_1.
Your answer is valid when C is an efficient dominating set of the strong
product.  It then compactly represents the Roman function f that is 2 on C
and 0 off C, of exact weight 2*{p}^(2*{dimension}-2).

For an exact finite check, C_i is an efficient dominating set precisely when
the {p} values a_i dot F_i(t), as t ranges over GF({p}), are all distinct
(equivalently, they are all field residues).  The checker performs this test
for both factors; it never expands the {p ** (2 * dimension)}-vertex product.

Each normal must contain exactly {dimension} integers in 0,...,{p - 1}.  Scalar
multiples name the same hyperplane, so use the unique projective normalization:
the first nonzero entry of each normal must be 1.  The order is factor 0 then
factor 1; vector-coordinate order matters, and no entry may be omitted.

{factor_text[0]}

{factor_text[1]}

Give your final answer inside <answer></answer> tags, as exactly one JSON object
with the single key "normals", whose value is the two arrays just described.
Example for d={dimension}: <answer>{{"normals":[{[1] + [0] * (dimension - 1)},{[0, 1] + [0] * (dimension - 2)}]}}</answer>
Output nothing else inside the tags."""

    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    """Extract the tagged JSON certificate, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    if not match:
        return None
    payload = match.group(1).strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", payload, re.I | re.S)
    if fence:
        payload = fence.group(1).strip()
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return answer


def _projection_is_permutation(points, normal, p, operation_counter=None):
    seen = set()
    dimension = len(normal)
    for point in points:
        value = 0
        for index in range(dimension):
            value = (value + normal[index] * point[index]) % p
            if operation_counter is not None:
                operation_counter[0] += 2
        if value in seen:
            return False
        seen.add(value)
    return len(seen) == p


def verify(inst, answer) -> tuple[bool, str]:
    """Verify any valid pair of hyperplane codes; never read the planted one."""
    if not isinstance(answer, dict) or set(answer) != {"normals"}:
        return False, "answer must be an object with exactly the key normals"
    normals = answer["normals"]
    if not isinstance(normals, list) or len(normals) != 2:
        return False, "normals must contain exactly two factor normals"
    dimension = inst["dimension"]
    p = inst["p"]
    for factor_index, normal in enumerate(normals):
        if not isinstance(normal, list) or len(normal) != dimension:
            return False, f"factor {factor_index} normal must have exactly {dimension} entries"
        if any(not _is_int(value) for value in normal):
            return False, f"factor {factor_index} normal entries must be integers"
        if any(value < 0 or value >= p for value in normal):
            return False, f"factor {factor_index} normal entry is outside 0,...,{p - 1}"
        first_nonzero = next((value for value in normal if value), None)
        if first_nonzero != 1:
            return False, f"factor {factor_index} normal is not projectively normalized"
        if not _projection_is_permutation(
            inst["factors"][factor_index]["points"], normal, p
        ):
            return False, f"factor {factor_index} hyperplane is not an efficient dominating set"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Sample uniformly from pairs of normalized projective directions."""
    p = inst["p"]
    dimension = inst["dimension"]
    return {
        "normals": [
            _random_normal(dimension, p, rng),
            _random_normal(dimension, p, rng),
        ]
    }


def _direction_count(p, dimension):
    return (p ** dimension - 1) // (p - 1)


def search_space(inst) -> int | None:
    """Number of ordered pairs of normalized projective normals."""
    directions = _direction_count(inst["p"], inst["dimension"])
    return directions * directions


def _projective_normals(p, dimension):
    for pivot in range(dimension):
        tail_length = dimension - pivot - 1
        for tail in itertools.product(range(p), repeat=tail_length):
            yield [0] * pivot + [1] + list(tail)


def _scan_factor(factor, p, dimension, stop_at_first=False):
    valid = []
    operations = [0]
    for normal in _projective_normals(p, dimension):
        if _projection_is_permutation(factor["points"], normal, p, operations):
            valid.append(normal)
            if stop_at_first:
                break
    return valid, operations[0]


def enumerate_all(inst) -> int | None:
    """Exact count in the symbolic language when the direction scan is capped."""
    directions = _direction_count(inst["p"], inst["dimension"])
    if directions > 250_000:
        return None
    counts = []
    for factor in inst["factors"]:
        valid, _ = _scan_factor(
            factor, inst["p"], inst["dimension"], stop_at_first=False
        )
        counts.append(len(valid))
    return math.prod(counts)


def _canonical_factor(factor, p):
    """Canonicalise ambient GL changes and t -> u*t reparameterisations."""
    rows = factor["coefficients"]
    candidates = []
    for scale in range(1, p):
        scaled = [
            [coefficient * pow(scale, degree, p) % p
             for degree, coefficient in enumerate(row)]
            for row in rows
        ]
        candidates.append(_rref_rows(scaled, p))
    return min(candidates)


def canonical_key(inst) -> str:
    """Canonical key under ambient basis changes and factor reordering."""
    factor_keys = sorted(
        _canonical_factor(factor, inst["p"])
        for factor in inst["factors"]
    )
    record = [inst["p"], inst["dimension"], factor_keys]
    payload = json.dumps(record, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params) -> dict | str | None:
    """Double the field-size target while keeping two fixed-length normals."""
    harder = dict(params)
    current = harder.get("n")
    if not _is_int(current) or current < 5:
        return None
    harder["n"] = current * 2
    return harder


def _compact_normal(factor, p, dimension):
    """Find the nonlinear coefficient-span annihilator and count field ops."""
    coefficient_rows = factor["coefficients"]
    nonlinear = [
        [coefficient_rows[row][degree] for row in range(dimension)]
        for degree in range(3, p, 2)
    ]
    basis = []
    pivots = []
    operations = 0
    for source in nonlinear:
        row = list(source)
        for old, pivot in zip(basis, pivots):
            factor_value = row[pivot]
            if factor_value:
                for column in range(pivot, dimension):
                    row[column] = (
                        row[column] - factor_value * old[column]
                    ) % p
                    operations += 2
        pivot = next((index for index, value in enumerate(row) if value), None)
        if pivot is None:
            continue
        inverse = pow(row[pivot], p - 2, p)
        operations += 1
        for column in range(pivot, dimension):
            row[column] = row[column] * inverse % p
            operations += 1
        basis.append(row)
        pivots.append(pivot)
        if len(basis) == dimension - 1:
            break
    if len(basis) != dimension - 1:
        raise AssertionError("nonlinear coefficient span has wrong rank")
    free_columns = [index for index in range(dimension) if index not in pivots]
    if len(free_columns) != 1:
        raise AssertionError("annihilator is not one-dimensional")
    normal = [0] * dimension
    normal[free_columns[0]] = 1
    for row, pivot in reversed(list(zip(basis, pivots))):
        total = 0
        for column in range(pivot + 1, dimension):
            total = (total + row[column] * normal[column]) % p
            operations += 2
        normal[pivot] = (-total) % p
    first = next(value for value in normal if value)
    inverse = pow(first, p - 2, p)
    operations += 1
    normal = [(value * inverse) % p for value in normal]
    operations += dimension
    return normal, operations


def _compact_answer(inst):
    normals = []
    operations = 0
    for factor in inst["factors"]:
        normal, cost = _compact_normal(
            factor, inst["p"], inst["dimension"]
        )
        normals.append(normal)
        operations += cost
    return {"normals": normals}, operations


def _reference_answer(inst):
    normals = []
    operations = 0
    for factor in inst["factors"]:
        valid, cost = _scan_factor(
            factor, inst["p"], inst["dimension"], stop_at_first=True
        )
        if not valid:
            return None, operations + cost
        normals.append(valid[0])
        operations += cost
    return {"normals": normals}, operations


def _axis_greedy_answer(inst):
    normals = []
    p = inst["p"]
    dimension = inst["dimension"]
    for factor in inst["factors"]:
        best_axis = 0
        best_distinct = -1
        for axis in range(dimension):
            count = len({point[axis] for point in factor["points"]})
            if count > best_distinct:
                best_axis, best_distinct = axis, count
        normal = [0] * dimension
        normal[best_axis] = 1
        normals.append(normal)
    return {"normals": normals}


def _coefficient_vector_answer(inst, degree_selector):
    normals = []
    for factor in inst["factors"]:
        rows = factor["coefficients"]
        degree = degree_selector(rows)
        vector = [row[degree] for row in rows]
        normal = _normalize_projective(vector, inst["p"])
        if normal is None:
            normal = [1] + [0] * (inst["dimension"] - 1)
        normals.append(normal)
    return {"normals": normals}


def _outlier_energy_answer(inst):
    normals = []
    p = inst["p"]
    dimension = inst["dimension"]
    for factor in inst["factors"]:
        energies = []
        for row in factor["coefficients"]:
            energy = sum(min(value, p - value) ** 2 for value in row)
            energies.append(energy)
        axis = max(range(dimension), key=lambda index: energies[index])
        normal = [0] * dimension
        normal[axis] = 1
        normals.append(normal)
    return {"normals": normals}


def _atomic_elements(value):
    if isinstance(value, dict):
        return sum(_atomic_elements(item) for item in value.values())
    if isinstance(value, list):
        return sum(_atomic_elements(item) for item in value)
    return 1


def _parameter_scale_factor(factor, scale, p):
    coefficients = [
        [coefficient * pow(scale, degree, p) % p
         for degree, coefficient in enumerate(row)]
        for row in factor["coefficients"]
    ]
    return {
        "coefficients": coefficients,
        "points": _evaluate_coordinate_rows(coefficients, p),
    }


def _shear_factor(factor, normal, target, source, scale, p):
    coefficients = [list(row) for row in factor["coefficients"]]
    coefficients[target] = [
        (coefficients[target][degree] + scale * coefficients[source][degree]) % p
        for degree in range(p)
    ]
    transformed_normal = list(normal)
    transformed_normal[source] = (
        transformed_normal[source] - scale * transformed_normal[target]
    ) % p
    transformed_normal = _normalize_projective(transformed_normal, p)
    return {
        "coefficients": coefficients,
        "points": _evaluate_coordinate_rows(coefficients, p),
    }, transformed_normal


def _swap_coordinates(factor, normal, left, right, p):
    coefficients = [list(row) for row in factor["coefficients"]]
    coefficients[left], coefficients[right] = (
        coefficients[right], coefficients[left]
    )
    transformed_normal = list(normal)
    transformed_normal[left], transformed_normal[right] = (
        transformed_normal[right], transformed_normal[left]
    )
    transformed_normal = _normalize_projective(transformed_normal, p)
    return {
        "coefficients": coefficients,
        "points": _evaluate_coordinate_rows(coefficients, p),
    }, transformed_normal


def _transform_instance(inst, kind):
    transformed = {
        "n": inst["n"],
        "p": inst["p"],
        "dimension": inst["dimension"],
        "factors": [],
    }
    normals = [list(normal) for normal in inst["answer"]["normals"]]
    p = inst["p"]
    if kind == "parameter":
        transformed["factors"] = [
            _parameter_scale_factor(factor, 2, p)
            for factor in inst["factors"]
        ]
    elif kind == "shear":
        for index, factor in enumerate(inst["factors"]):
            new_factor, normals[index] = _shear_factor(
                factor, normals[index], 0, 1, index + 2, p
            )
            transformed["factors"].append(new_factor)
    elif kind == "coordinate_swap":
        for index, factor in enumerate(inst["factors"]):
            new_factor, normals[index] = _swap_coordinates(
                factor, normals[index], 0, inst["dimension"] - 1, p
            )
            transformed["factors"].append(new_factor)
    elif kind == "factor_swap":
        transformed["factors"] = [inst["factors"][1], inst["factors"][0]]
        normals = [normals[1], normals[0]]
    elif kind == "composition":
        intermediate = _transform_instance(inst, "parameter")
        intermediate["answer"] = {"normals": normals}
        intermediate = _transform_instance(intermediate, "shear")
        intermediate["answer"] = intermediate["answer"]
        return _transform_instance(intermediate, "factor_swap")
    else:
        raise ValueError("unknown transformation")
    transformed["answer"] = {"normals": normals}
    return transformed


def selftest() -> dict:
    """Run all mandatory gates and return their measured evidence."""
    report = {}

    # G1: all rungs, three seeds, JSON-native answers, and construction audits.
    g1_attempts = 0
    g1_verified = 0
    json_native = True
    construction_checks = 0
    for params in DIFFICULTY.values():
        for seed in (0, 1, 19):
            instance = make_instance(seed=seed, **params)
            ok, _ = verify(instance, instance["answer"])
            g1_attempts += 1
            g1_verified += int(ok)
            json_native &= (
                json.loads(json.dumps(instance["answer"])) == instance["answer"]
            )
            for factor, normal in zip(
                instance["factors"], instance["answer"]["normals"]
            ):
                construction_checks += int(
                    all(
                        sum(normal[i] * point[i]
                            for i in range(instance["dimension"]))
                        % instance["p"] == parameter
                        for parameter, point in enumerate(factor["points"])
                    )
                )
    report["G1_planted_verifies"] = {
        "pass": g1_verified == g1_attempts
        and json_native
        and construction_checks == 2 * g1_attempts,
        "verified": g1_verified,
        "attempts": g1_attempts,
        "answer_json_native": json_native,
        "transversal_identity_checks": construction_checks,
        "transversal_identity_attempts": 2 * g1_attempts,
    }

    shipping_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    inst = make_instance(seed=12_345, **shipping_params)
    planted = json.loads(json.dumps(inst["answer"]))

    # G2: five malformed/corrupted categories, each reaching a distinct reason.
    swapped = {"normals": [planted["normals"][1], planted["normals"][0]]}
    variants = {
        "drop": {"normals": planted["normals"][:1]},
        "swap": swapped,
        "duplicate": {
            "normals": [planted["normals"][0] + [0], planted["normals"][1]]
        },
        "empty": {},
        "out_of_range": {
            "normals": [
                [inst["p"]] + planted["normals"][0][1:],
                planted["normals"][1],
            ]
        },
    }
    corruptions = {}
    for name, candidate in variants.items():
        ok, reason = verify(inst, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = {entry["reason"] for entry in corruptions.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in corruptions.values())
        and len(reasons) == len(corruptions),
        "corruptions": corruptions,
        "distinct_reasons": len(reasons),
    }

    # G3: tagged JSON through prose and a Markdown fence.
    encoded = json.dumps(inst["answer"], separators=(",", ":"))
    response = (
        "I used the closed-neighborhood transversal.\n<answer>\n```json\n"
        + encoded
        + "\n```\n</answer>\nThe product code follows."
    )
    parsed = parse_answer(response)
    garbage = parse_answer("No tagged certificate is present here.")
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and garbage is None,
        "realistic_response_recovered": parsed == inst["answer"],
        "garbage_returns_none": garbage is None,
    }

    # Exact shipping density: scan every projective direction in each factor.
    exact_counts = []
    exact_scan_operations = 0
    exact_scan_start = time.perf_counter()
    for factor in inst["factors"]:
        valid, operations = _scan_factor(
            factor, inst["p"], inst["dimension"], stop_at_first=False
        )
        exact_counts.append(len(valid))
        exact_scan_operations += operations
    exact_scan_seconds = time.perf_counter() - exact_scan_start
    exact_solutions = math.prod(exact_counts)
    exact_density = exact_solutions / search_space(inst)

    # G4: sample the exact normalized-projective language, not raw vectors.
    guess_rng = random.Random(0x11113517)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_total >= 200_000
        and guess_fraction < 1e-6
        and exact_density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_fraction,
        "exact_probability": exact_density,
        "valid_directions_per_factor": exact_counts,
        "candidate_space": search_space(inst),
        "sampling_prior": (
            "uniform ordered pairs of normalized projective directions; "
            "zero vectors and scalar duplicates are excluded"
        ),
    }

    # G6: five failing probes and the successful Track-B reference algorithm.
    attack_names = (
        "outlier_coefficient_energy",
        "greedy_coordinate_projection",
        "linear_term_vector_ansatz",
        "leading_term_vector_ansatz",
        "random_restart_256",
    )
    successes = {name: 0 for name in attack_names}
    seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_operations = []
    compact_successes = 0
    compact_seconds = 0.0
    compact_operations = []
    for seed in range(80, 88):
        test_inst = make_instance(seed=seed, **shipping_params)
        candidates = {
            "outlier_coefficient_energy": _outlier_energy_answer(test_inst),
            "greedy_coordinate_projection": _axis_greedy_answer(test_inst),
            "linear_term_vector_ansatz": _coefficient_vector_answer(
                test_inst, lambda rows: 1
            ),
            "leading_term_vector_ansatz": _coefficient_vector_answer(
                test_inst,
                lambda rows: max(
                    degree
                    for degree in range(len(rows[0]))
                    if any(row[degree] for row in rows)
                ),
            ),
        }
        for name, candidate in candidates.items():
            start = time.perf_counter()
            successes[name] += int(verify(test_inst, candidate)[0])
            seconds[name] += time.perf_counter() - start

        restart_rng = random.Random(seed ^ 0xBAD5EED)
        start = time.perf_counter()
        restart_solved = False
        for _ in range(256):
            if verify(test_inst, random_candidate(test_inst, restart_rng))[0]:
                restart_solved = True
                break
        seconds["random_restart_256"] += time.perf_counter() - start
        successes["random_restart_256"] += int(restart_solved)

        start = time.perf_counter()
        reference, operations = _reference_answer(test_inst)
        reference_seconds += time.perf_counter() - start
        reference_operations.append(operations)
        reference_successes += int(
            reference is not None and verify(test_inst, reference)[0]
        )

        start = time.perf_counter()
        compact, operations = _compact_answer(test_inst)
        compact_seconds += time.perf_counter() - start
        compact_operations.append(operations)
        compact_successes += int(verify(test_inst, compact)[0])

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(seconds[name], 6),
        }
        for name in attack_names
    }
    all_failed = all(value == 0 for value in successes.values())
    reference_record = {
        "name": "exhaustive normalized-projective direction scan",
        "complexity": "O(p^(d+1)) exact finite-field operations",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": round(sum(reference_operations) / 8),
        "max_operations": max(reference_operations),
        "solves": f"{reference_successes}/8, as expected",
    }
    compact_record = {
        "name": "annihilator of the shared nonlinear coefficient span",
        "wall_clock_sec": round(compact_seconds / 8, 6),
        "operations": max(compact_operations),
        "solves": f"{compact_successes}/8",
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed
        and reference_successes == 8
        and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference_record,
        "intended_compact_route": compact_record,
    }

    demo_count = enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline_cost"] = {
        "pass": exact_density < 1e-6
        and guess_fraction < 1e-6
        and demo_count is not None
        and reference_successes == 8,
        "shipping_exact_solution_count": exact_solutions,
        "shipping_candidate_count": search_space(inst),
        "shipping_solution_density": exact_density,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_full_scan_wall_clock_sec": round(exact_scan_seconds, 6),
        "shipping_full_scan_operations": exact_scan_operations,
        "demo_exact_solution_count": demo_count,
        "baseline_attack_wall_clock_sec": round(
            seconds["random_restart_256"] / 8, 6
        ),
        "baseline_attack_iterations": 256,
        "reference_wall_clock_sec": reference_record["wall_clock_sec"],
        "reference_operation_count": reference_record["operations"],
    }

    # G7: double n, hence more than double p^d vertices, at fixed answer length.
    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    ladder_primes = [_next_prime(params["n"]) for params in DIFFICULTY.values()]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and doubled["p"] > inst["p"]
        and search_space(doubled) > search_space(inst)
        and _atomic_elements(doubled["answer"])
        == _atomic_elements(inst["answer"])
        and ladder_primes == sorted(ladder_primes)
        and len(set(ladder_primes)) == len(ladder_primes),
        "shipping_n": inst["n"],
        "shipping_prime": inst["p"],
        "shipping_graph_vertices": inst["p"] ** (2 * inst["dimension"]),
        "doubled_n": doubled["n"],
        "doubled_prime": doubled["p"],
        "doubled_graph_vertices": doubled["p"] ** (2 * doubled["dimension"]),
        "answer_elements_shipping": _atomic_elements(inst["answer"]),
        "answer_elements_doubled": _atomic_elements(doubled["answer"]),
        "candidate_space_shipping": search_space(inst),
        "candidate_space_doubled": search_space(doubled),
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_reason,
    }

    # G8: ambient GL generators, parameter scaling, factor swap, compositions.
    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    transform_kinds = (
        "parameter",
        "shear",
        "coordinate_swap",
        "factor_swap",
        "composition",
    )
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping_params)
        key = canonical_key(original)
        for kind in transform_kinds:
            transformed = _transform_instance(original, kind)
            invariant_count += int(canonical_key(transformed) == key)
            real_transform_count += int(
                verify(transformed, transformed["answer"])[0]
            )
        unrelated_keys.append(key)
    expected = 20 * len(transform_kinds)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == expected
        and real_transform_count == expected
        and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "invariant_attempts": expected,
        "real_transformations_verified": real_transform_count,
        "real_transformation_attempts": expected,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "connection-parameter scaling t -> 2t",
            "ambient coordinate shear",
            "ambient coordinate swap",
            "strong-product factor swap",
            "parameter scaling composed with shear and factor swap",
        ],
    }

    # G9: oracle arms are external; only the exact answer/route caps gate locally.
    encoded_answer = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(encoded_answer)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _atomic_elements(inst["answer"])
    worst_answer = {
        "normals": [
            [1] + [inst["p"] - 1] * (inst["dimension"] - 1),
            [1] + [inst["p"] - 1] * (inst["dimension"] - 1),
        ]
    }
    worst_chars = len(json.dumps(worst_answer, separators=(",", ":")))
    worst_tokens = math.ceil(worst_chars / 4)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        hinted_minus_placebo = hinted_rate - placebo_rate
    else:
        hinted_minus_placebo = None
    intended_operations = max(compact_operations)
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
        and worst_tokens <= PROBLEM_PROFILE["max_answer_tokens"]
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": worst_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
