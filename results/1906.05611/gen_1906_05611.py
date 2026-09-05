"""Verified problem generator for arXiv:1906.05611.

The generated search problem uses the vertex configuration in Theorems 2.3
and 3.2 of Zanella--Zullo.  Everything is standard-library-only; the optional
gvlib import is retained for repository compatibility but is not needed here.
"""

from __future__ import annotations

import copy
import json
import os
import random
import re
import sys
import time
from itertools import product


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # The implementation below remains standard-library-only.
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "geometry",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "codimension-two projective subspace over GF(q^d)",
        "Frobenius collineation",
        "projective point in homogeneous coordinates",
    ],
    "verification_operations": [
        "exact arithmetic modulo q",
        "diagonalized Frobenius conjugation",
        "homogeneous equation substitution",
        "modular row rank",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize that the displayed Frobenius multipliers are all roots of "
        "unity in Fourier coordinates, so their power sums expose the first "
        "point of the orbit chain."
    ),
    "hardness_basis": (
        "Track B: generic recovery is nullspace elimination on 2(d-3) by d "
        "over GF(q), O(d^3) field operations; at shipping q=3299 and d=97 it "
        "averaged 1,505,250 field operations and 0.05--0.11 seconds over "
        "eight seeds in repeated final selftests, while "
        "the Fourier power-sum route takes at most 109 exact operations."
    ),
    "max_answer_tokens": 115,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": " +
        PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 2, "degree": 7},
    "easy": {"n": 7, "degree": 97},
    "medium": {"n": 11, "degree": 97},
    "hard": {"n": 15, "degree": 97},
}
SHIPPING_DIFFICULTY: str = "medium"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "One 1-by-d normalized homogeneous-coordinate matrix representing a "
        "point of the displayed codimension-two Gamma over GF(q): all d "
        "entries are integers in [0,q-1], the row is nonzero, and its first "
        "nonzero entry is 1."
    ),
    "bounds": {
        "matrix_rows": 1,
        "matrix_columns_shipping": 97,
        "coordinate_min": 0,
        "prime_bits_shipping": 12,
    },
}

STRUCTURAL_HINT: str = (
    "The diagonal Frobenius multipliers form the full set of d-th roots of unity over GF(q)."
)
PLACEBO_HINT: str = (
    "The displayed finite-field equations reward careful handling of homogeneous coordinates over GF(q)."
)

# Filled from the separately-owned harden.py runs after the module is hardened.
G9_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 2, "attempts": 3},
}

NOTES: str = """\
Definition source: Section 1 defines the canonical subgeometry, its Frobenius
collineation, projective vertices, point weights, and maximum scattered linear
sets.  Theorem 2.3 defines the intersection number and produces the orbit-chain
point P; Theorem 3.2 specializes an LP-type vertex to intersection number two
and makes P unique in our degree regime.  The displayed vertex immediately
after Theorem 3.1 supplies the two native equations.  Lemma 4.1 is the easy-case
test: for odd d the LP set is scattered exactly when Norm(delta) != 1, which the
generator enforces.

Step-0 algorithm audit: P is the one-dimensional nullspace of all constraints
obtained by substituting P, sigma(P), ..., sigma^(d-4)(P) in Gamma.  Gaussian
elimination therefore recovers it in polynomial time, so this cannot honestly
be Track A.  It is Track B: the shipping matrix has 2(d-3) dense rows, and
selftest measures both its elimination operations and wall time.  Generation
applies the finite-field Fourier matrix to the paper's displayed LP vertex and
carries the standard point e_2 through the known inverse transform; it never
solves the generated instance.  In the transformed coordinates sigma is
diagonal, its multipliers are all d-th roots of unity, and the certificate is
their coordinatewise square.  The vanishing root-of-unity power sums prove the
orbit conditions, leaving d modular squarings after the invariant is seen.

Attack hardening: a random primitive d-th root permutes the Fourier coordinates
and the LP norm invariant varies independently with the seed.  Both defining
rows are dense and every coordinate has the same support score.  Coordinate-
score, sparse-nullspace, constant or axis ansatz, and 256 structure-aware
random restarts are all tested.  The generic elimination algorithm is reported
separately, as Track B requires.
"""


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small:
        if value == p:
            return True
        if value % p == 0:
            return False
    # Deterministic Miller--Rabin for all unsigned 64-bit inputs.
    d = value - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
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


def _prime_for_bits(bits: int, degree: int) -> int:
    if not isinstance(bits, int) or isinstance(bits, bool) or bits < 2:
        raise ValueError("n must be an integer at least 2 (it controls prime size)")
    if bits > 60:
        raise ValueError("n above 60 exceeds the declared certificate language")
    # The Fourier coordinate change needs a primitive degree-th root in GF(q),
    # so choose q == 1 (mod degree).  Both supported degrees are prime.
    target = max(5, 1 << bits)
    multiplier = max(1, (target - 1 + degree - 1) // degree)
    while True:
        candidate = 1 + multiplier * degree
        if _is_prime(candidate):
            return candidate
        multiplier += 1


def _frobenius_step(vector: list[int], multipliers: list[int], q: int) -> list[int]:
    """The paper's Frobenius cycle after finite-field Fourier diagonalisation."""
    return [(x * eigenvalue) % q
            for x, eigenvalue in zip(vector, multipliers)]


def _normalize(vector: list[int], q: int) -> list[int] | None:
    v = [x % q for x in vector]
    for x in v:
        if x:
            scale = pow(x, -1, q)
            return [(scale * y) % q for y in v]
    return None


def _dot(row: list[int], vector: list[int], q: int) -> int:
    # Generated rows are sparse; retaining the zero test makes the 200k density
    # experiment cheap without changing the exact verifier.
    total = 0
    for a, b in zip(row, vector):
        if a:
            total += a * b
    return total % q


def _rank_mod(rows: list[list[int]], q: int) -> int:
    if not rows:
        return 0
    a = [[x % q for x in row] for row in rows]
    nrows, ncols = len(a), len(a[0])
    rank = 0
    for col in range(ncols):
        pivot = next((i for i in range(rank, nrows) if a[i][col]), None)
        if pivot is None:
            continue
        a[rank], a[pivot] = a[pivot], a[rank]
        inv = pow(a[rank][col], -1, q)
        a[rank] = [(x * inv) % q for x in a[rank]]
        for i in range(nrows):
            if i != rank and a[i][col]:
                factor = a[i][col]
                a[i] = [(x - factor * y) % q
                        for x, y in zip(a[i], a[rank])]
        rank += 1
        if rank == nrows:
            break
    return rank


def _add_rows(left: list[int], right: list[int], scale: int, q: int) -> list[int]:
    return [(x + scale * y) % q for x, y in zip(left, right)]


def _primitive_root_of_degree(q: int, degree: int, rng: random.Random) -> int:
    """Sample a primitive degree-th root; degree is prime and divides q-1."""
    exponent = (q - 1) // degree
    while True:
        root = pow(rng.randrange(2, q), exponent, q)
        if root != 1:
            return root


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse/compositional generation of an LP-type vertex and its point.

    Here ``n`` is the benchmark size knob: q is the first suitable prime at
    least 2**n, while ``degree`` is the paper's extension/projective parameter
    d.  The witness is transported through a finite Fourier coordinate change;
    no generated instance is solved in order to obtain its answer.
    """
    degree = params.pop("degree", 97)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if (not isinstance(degree, int) or isinstance(degree, bool) or
            degree < 7 or degree % 2 == 0 or not _is_prime(degree)):
        raise ValueError("degree must be an odd prime at least 7")
    q = _prime_for_bits(n, degree)
    rng = random.Random(seed)
    omega = _primitive_root_of_degree(q, degree, rng)

    # Vary the LP norm invariant.  For odd degree, Lemma 4.1 says this is
    # exactly the regime where the associated LP linear set is scattered.
    while True:
        delta = rng.randrange(1, q)
        delta_norm = pow(delta, degree, q)
        if delta_norm != 1:
            break

    # Let F[i,j]=omega^(i*j).  Its columns diagonalise the right cyclic
    # Frobenius shift S, with eigenvalues omega^(-j).  Under y=F*x the paper's
    # displayed LP vertex y_0=0, y_{d-1}+delta*y_1=0 becomes the two dense rows
    # below.  Its theorem-backed chain point y=e_2 becomes, projectively,
    # x_j=omega^(-2j)=eigenvalue_j^2.  This is a carried certificate, not a
    # nullspace computed from the generated equations.
    multipliers = [pow(omega, -j, q) for j in range(degree)]
    equation_one = [1] * degree
    equation_two = [
        (value + delta * pow(value, -1, q)) % q
        for value in multipliers
    ]
    point = [(value * value) % q for value in multipliers]

    return {
        "schema": "zz-lp-vertex-chain-v2",
        "size_bits": n,
        "q": q,
        "extension_degree": degree,
        "delta": delta,
        "delta_norm": delta_norm,
        "frobenius_multipliers": multipliers,
        "equations": [equation_one, equation_two],
        "answer": {"point": [point]},
    }


def render(inst: dict) -> str:
    q = inst["q"]
    d = inst["extension_degree"]
    equations = "\n".join(
        f"  E{i + 1}: " + " ".join(str(x) for x in row)
        for i, row in enumerate(inst["equations"])
    )
    example = {"point": [[1] + [0] * (d - 1)]}
    statement = f"""\
Orbit-chain point in a finite projective vertex

Let q={q}, a prime, and d={d}.  Let K=GF(q^d).  We use homogeneous
coordinates [v_0:...:v_{{d-1}}] for PG(d-1,K).  In this instance all displayed
coefficients lie in the distinguished subfield GF(q), represented by the
integers 0,...,q-1; all arithmetic below is therefore exact arithmetic modulo q,
and you do not need to construct K.

The coordinates below are a Fourier eigenbasis for the Frobenius cycle.  For a
coordinate row v over GF(q), the Frobenius collineation sigma acts by
  sigma(v_0,...,v_{{d-1}})=(lambda_0*v_0,...,lambda_{{d-1}}*v_{{d-1}}),
where multiplication is modulo q and the multipliers lambda_j are
  {' '.join(str(x) for x in inst['frobenius_multipliers'])}
in coordinate order j=0,...,d-1.  Superscript sigma^j means j repeated
applications of this coordinatewise map.  On arbitrary K-coordinate rows the
same formula also raises every v_j to its q-th power; answers here are required
over GF(q), where that extra operation is the identity.

The projective subspace Gamma has codimension two and consists of all rows x
whose dot product modulo q with each of the following coefficient rows is zero:
{equations}

The LP parameter is delta={inst['delta']}; its norm to GF(q) is
delta^d={inst['delta_norm']} (mod q), which is not 1.  You are promised that
Gamma is a projection vertex of intersection number two in the sense encoded by
the conditions below.

Find a projective point P represented by one row p=(p_0,...,p_{{d-1}}) over
GF(q) such that:
  1. P, P^sigma, ..., P^sigma^(d-4) all lie in Gamma;
  2. those d-3 coordinate rows are linearly independent over GF(q); and
  3. P^sigma^(d-1) does not lie in Gamma.

The answer row must have exactly d={d} integer entries in 0,...,{q - 1}, must
be nonzero, and must use the unique homogeneous normalization in which its first
nonzero entry is 1.  Return a JSON object containing a one-row matrix.

Give your final answer inside <answer></answer> tags, as JSON of the exact form
{{"point":[[p_0,p_1,...,p_{{d-1}}]]}}.
Example of the required shape: <answer>{json.dumps(example, separators=(',', ':'))}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\s*>(.*?)</answer\s*>", text,
                      flags=re.IGNORECASE | re.DOTALL)
    payload = match.group(1).strip() if match else text.strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", payload,
                         flags=re.IGNORECASE | re.DOTALL)
    if fence:
        payload = fence.group(1).strip()
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(answer, dict) or set(answer) != {"point"}:
        return None
    return answer


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if set(answer) != {"point"}:
        return False, "answer object must contain only the key 'point'"
    matrix = answer["point"]
    if not isinstance(matrix, list) or len(matrix) != 1:
        return False, "point must be a matrix containing exactly one row"
    point = matrix[0]
    d = inst["extension_degree"]
    q = inst["q"]
    if not isinstance(point, list) or len(point) != d:
        return False, f"point row must contain exactly {d} coordinates"
    if any(not isinstance(x, int) or isinstance(x, bool) for x in point):
        return False, "every coordinate must be an integer"
    if any(x < 0 or x >= q for x in point):
        return False, f"every coordinate must lie in 0..{q - 1}"
    normalized = _normalize(point, q)
    if normalized is None:
        return False, "the zero row is not a projective point"
    if normalized != point:
        return False, "point is not in first-nonzero-equals-one normalization"
    equations = inst.get("equations")
    if (not isinstance(equations, list) or len(equations) != 2 or
            any(not isinstance(row, list) or len(row) != d for row in equations)):
        return False, "instance has malformed defining equations"

    orbit_rows = []
    current = list(point)
    multipliers = inst.get("frobenius_multipliers")
    if (not isinstance(multipliers, list) or len(multipliers) != d or
            any(not isinstance(x, int) or isinstance(x, bool) or x <= 0 or x >= q
                for x in multipliers)):
        return False, "instance has malformed Frobenius multipliers"
    for exponent in range(d - 3):  # 0 through d-4 inclusive
        for equation_index, row in enumerate(equations, start=1):
            if _dot(row, current, q):
                return False, (
                    f"orbit point sigma^{exponent} violates equation "
                    f"E{equation_index}"
                )
        orbit_rows.append(current)
        current = _frobenius_step(current, multipliers, q)
    rank = _rank_mod(orbit_rows, q)
    if rank != d - 3:
        return False, f"orbit rows have rank {rank}, expected {d - 3}"
    forbidden = [
        (x * pow(eigenvalue, d - 1, q)) % q
        for x, eigenvalue in zip(point, multipliers)
    ]
    if all(_dot(row, forbidden, q) == 0 for row in equations):
        return False, "orbit point sigma^(d-1) lies in Gamma"
    return True, "ok"


def _gamma_coordinates(inst: dict) -> tuple[list[int], tuple[int, int]]:
    """Return free columns and an invertible two-column equation minor."""
    equations = inst["equations"]
    q = inst["q"]
    d = inst["extension_degree"]
    for first in range(d - 1):
        for second in range(first + 1, d):
            determinant = (
                equations[0][first] * equations[1][second]
                - equations[0][second] * equations[1][first]
            ) % q
            if determinant:
                free = [j for j in range(d) if j not in (first, second)]
                return free, (first, second)
    raise ValueError("defining equations do not have codimension two")


def _complete_gamma_point(
        inst: dict, free: list[int], pivots: tuple[int, int],
        values: list[int]) -> list[int]:
    """Complete free coordinates to the unique vector in Gamma."""
    q = inst["q"]
    equations = inst["equations"]
    first, second = pivots
    vector = [0] * inst["extension_degree"]
    for column, value in zip(free, values):
        vector[column] = value % q
    rhs0 = -sum(equations[0][j] * vector[j] for j in free) % q
    rhs1 = -sum(equations[1][j] * vector[j] for j in free) % q
    a, b = equations[0][first] % q, equations[0][second] % q
    c, d = equations[1][first] % q, equations[1][second] % q
    inverse_det = pow((a * d - b * c) % q, -1, q)
    vector[first] = (rhs0 * d - b * rhs1) * inverse_det % q
    vector[second] = (a * rhs1 - rhs0 * c) * inverse_det % q
    return vector


def random_candidate(inst: dict, rng: random.Random) -> object:
    q = inst["q"]
    free, pivots = _gamma_coordinates(inst)
    # A solver gets membership in Gamma for free: it is only a two-equation
    # linear solve.  Sampling a uniform nonzero free vector, completing it, and
    # normalizing therefore samples projective points of Gamma exactly uniformly.
    while True:
        values = [rng.randrange(q) for _ in free]
        if any(values):
            row = _normalize(_complete_gamma_point(inst, free, pivots, values), q)
            assert row is not None
            return {"point": [row]}


def search_space(inst: dict) -> int:
    q = inst["q"]
    d = inst["extension_degree"]
    # Gamma has vector dimension d-2 (projective dimension d-3).
    return (pow(q, d - 2) - 1) // (q - 1)


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space > 50_000:
        return None
    q = inst["q"]
    free, pivots = _gamma_coordinates(inst)
    count = 0
    # Normalize in the free-coordinate projective space, then use the linear
    # completion map.  This visits every projective point of Gamma exactly once.
    for first in range(len(free)):
        suffix_length = len(free) - first - 1
        for suffix in product(range(q), repeat=suffix_length):
            values = [0] * first + [1] + list(suffix)
            row = _normalize(
                _complete_gamma_point(inst, free, pivots, values), q
            )
            assert row is not None
            if verify(inst, {"point": [row]})[0]:
                count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Strong cheap invariant under generated coordinate disguises.

    Coordinate permutations remove the private choice of Fourier root.  Reversing
    the root order changes delta to its reciprocal after rescaling the second
    equation, so use the smaller representative of that pair.
    """
    q = inst["q"]
    delta = int(inst["delta"]) % q
    inverse = pow(delta, -1, q)
    payload = [inst["extension_degree"], q, min(delta, inverse)]
    return json.dumps(payload, separators=(",", ":"))


def escalate(params: dict) -> dict | str | None:
    harder = dict(params)
    harder["n"] = int(harder["n"]) + 4
    if harder["n"] > 60:
        return "cap_bound"
    try:
        probe = make_instance(seed=98765, **harder)
    except ValueError:
        return "cap_bound"
    if len(json.dumps(probe["answer"], separators=(",", ":"))) > 2_000:
        return "cap_bound"
    return harder


def _constraint_matrix(inst: dict) -> list[list[int]]:
    """Linear equations for p, sigma(p), ..., sigma^(d-4)(p) in Gamma."""
    d = inst["extension_degree"]
    q = inst["q"]
    multipliers = inst["frobenius_multipliers"]
    constraints = []
    powers = [1] * d
    for exponent in range(d - 3):
        for row in inst["equations"]:
            constraints.append([
                coefficient * power % q
                for coefficient, power in zip(row, powers)
            ])
        powers = [
            power * eigenvalue % q
            for power, eigenvalue in zip(powers, multipliers)
        ]
    return constraints


def _one_dimensional_nullspace(
        rows: list[list[int]], q: int) -> tuple[list[int] | None, int]:
    """Generic RREF nullspace solver, returning a field-operation count."""
    if not rows:
        return None, 0
    a = [[x % q for x in row] for row in rows]
    nrows, ncols = len(a), len(a[0])
    pivot_columns = []
    pivot_row = 0
    operations = 0
    for col in range(ncols):
        pivot = next((i for i in range(pivot_row, nrows) if a[i][col]), None)
        if pivot is None:
            continue
        if pivot != pivot_row:
            a[pivot_row], a[pivot] = a[pivot], a[pivot_row]
        value = a[pivot_row][col]
        if value != 1:
            inv = pow(value, -1, q)
            operations += 1
            for j in range(col, ncols):
                if a[pivot_row][j]:
                    a[pivot_row][j] = a[pivot_row][j] * inv % q
                    operations += 1
        for i in range(nrows):
            if i == pivot_row or not a[i][col]:
                continue
            factor = a[i][col]
            for j in range(col, ncols):
                if a[pivot_row][j] or a[i][j]:
                    a[i][j] = (a[i][j] - factor * a[pivot_row][j]) % q
                    operations += 2
        pivot_columns.append(col)
        pivot_row += 1
        if pivot_row == nrows:
            break
    free = [j for j in range(ncols) if j not in set(pivot_columns)]
    if len(free) != 1:
        return None, operations
    free_col = free[0]
    vector = [0] * ncols
    vector[free_col] = 1
    for i, col in enumerate(pivot_columns):
        vector[col] = (-a[i][free_col]) % q
        operations += 1
    return _normalize(vector, q), operations


def _reference_algorithm(inst: dict) -> tuple[object | None, int]:
    vector, operations = _one_dimensional_nullspace(
        _constraint_matrix(inst), inst["q"]
    )
    if vector is None:
        return None, operations
    return {"point": [vector]}, operations


def _coordinate_score_attack(inst: dict) -> object:
    d = inst["extension_degree"]
    q = inst["q"]
    scores = [sum(1 for row in inst["equations"] if row[j] % q) for j in range(d)]
    index = min(range(d), key=lambda j: (scores[j], j))
    row = [0] * d
    row[index] = 1
    return {"point": [row]}


def _greedy_sparse_attack(inst: dict) -> object:
    # Greedily satisfy Gamma itself using the first dependent triple of equation
    # columns.  This is a genuine sparse point of Gamma, but it ignores the long
    # orbit-chain constraint.
    equations = inst["equations"]
    d, q = inst["extension_degree"], inst["q"]
    for i in range(d - 2):
        for j in range(i + 1, d - 1):
            for k in range(j + 1, d):
                small = [
                    [equations[row][column] for column in (i, j, k)]
                    for row in range(2)
                ]
                coefficients, _ = _one_dimensional_nullspace(small, q)
                if coefficients is None:
                    continue
                vector = [0] * d
                for column, value in zip((i, j, k), coefficients):
                    vector[column] = value
                vector = _normalize(vector, q)
                if vector is not None and all(
                        _dot(row, vector, q) == 0 for row in equations):
                    return {"point": [vector]}
    return {"point": [[1] + [0] * (d - 1)]}


def _constant_axis_attack(inst: dict) -> object:
    d = inst["extension_degree"]
    q = inst["q"]
    candidates = [
        [1] * d,
        [1 if i % 2 == 0 else q - 1 for i in range(d)],
        [1] + [0] * (d - 1),
    ]
    for row in candidates:
        answer = {"point": [row]}
        if verify(inst, answer)[0]:
            return answer
    return {"point": [candidates[0]]}


def _coordinate_relabel(inst: dict, permutation: list[int]) -> dict:
    transformed = copy.deepcopy(inst)
    d = inst["extension_degree"]
    if sorted(permutation) != list(range(d)):
        raise ValueError("coordinate relabelling must be a permutation")
    transformed["equations"] = [
        [row[j] for j in permutation] for row in inst["equations"]
    ]
    transformed["frobenius_multipliers"] = [
        inst["frobenius_multipliers"][j] for j in permutation
    ]
    carried = _normalize(
        [inst["answer"]["point"][0][j] for j in permutation], inst["q"]
    )
    assert carried is not None
    transformed["answer"] = {"point": [carried]}
    return transformed


def _row_relabel(inst: dict, scale: int) -> dict:
    transformed = copy.deepcopy(inst)
    q = inst["q"]
    first, second = inst["equations"]
    # Invertible equation-basis change followed by reordering/scaling.
    transformed["equations"] = [
        [(scale * x) % q for x in second],
        _add_rows(first, second, scale, q),
    ]
    return transformed


def _generator_inverse_relabel(inst: dict) -> dict:
    """Reverse the Frobenius generator and carry the LP vertex and point.

    In the paper's cyclic coordinates this is reversal of the cycle.  It sends
    delta to delta^-1, scales the second defining equation by delta^-1,
    replaces every Frobenius multiplier by its inverse, and carries the known
    orbit point coordinatewise.  All changes are projective/semilinear
    relabellings, not a newly solved instance.
    """
    transformed = copy.deepcopy(inst)
    q = inst["q"]
    d = inst["extension_degree"]
    inverse_delta = pow(inst["delta"], -1, q)
    transformed["delta"] = inverse_delta
    transformed["delta_norm"] = pow(inverse_delta, d, q)
    transformed["frobenius_multipliers"] = [
        pow(value, -1, q) for value in inst["frobenius_multipliers"]
    ]
    transformed["equations"] = [
        list(inst["equations"][0]),
        [(inverse_delta * value) % q for value in inst["equations"][1]],
    ]
    transformed["answer"] = {"point": [[
        pow(value, -1, q) for value in inst["answer"]["point"][0]
    ]]}
    return transformed


def _atom_count(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atom_count(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atom_count(v) for v in value)
    return 1


def selftest() -> dict:
    report: dict = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1: all rungs, several independent seeds, and JSON-native answers.
    g1_attempts = 0
    g1_failures = []
    fourier_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            q_here = inst["q"]
            d_here = inst["extension_degree"]
            multipliers = inst["frobenius_multipliers"]
            construction_ok = (
                len(set(multipliers)) == d_here
                and all(pow(value, d_here, q_here) == 1
                        for value in multipliers)
                and inst["equations"][0] == [1] * d_here
                and inst["equations"][1] == [
                    (value + inst["delta"] * pow(value, -1, q_here)) % q_here
                    for value in multipliers
                ]
                and inst["answer"]["point"][0] == [
                    value * value % q_here for value in multipliers
                ]
            )
            fourier_checks += int(construction_ok)
            g1_attempts += 1
            if not ok or not json_ok or not construction_ok:
                g1_failures.append({
                    "preset": preset, "seed": seed, "reason": reason,
                    "json_native": json_ok,
                    "fourier_construction": construction_ok,
                })
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "fourier_construction_checks": fourier_checks,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]["point"][0]
    d, q = shipping["extension_degree"], shipping["q"]

    # G2: five qualitatively distinct corruptions and distinct diagnostics.
    swapped = list(planted)
    swap_pair = None
    first_nonzero = next(i for i, x in enumerate(swapped) if x)
    for i in range(first_nonzero + 1, d):
        for j in range(i + 1, d):
            if swapped[i] != swapped[j]:
                swap_pair = (i, j)
                break
        if swap_pair:
            break
    if swap_pair:
        i, j = swap_pair
        swapped[i], swapped[j] = swapped[j], swapped[i]
    corruptions = {
        "drop_coordinate": {"point": [planted[:-1]]},
        "swap_coordinates": {"point": [swapped]},
        "duplicate_row": {"point": [planted, planted]},
        "empty": [],
        "out_of_range": {"point": [[q] + planted[1:]]},
    }
    corruption_results = {}
    for name, bad in corruptions.items():
        ok, reason = verify(shipping, bad)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": (all(x["rejected"] for x in corruption_results.values()) and
                 len(set(reasons)) == len(reasons)),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic tagged/fenced answer surrounded by prose.
    model_style = (
        "The orbit constraints determine a unique normalized point.\n"
        "```json\n<answer>" + json.dumps(shipping["answer"]) +
        "</answer>\n```\nThat is my final answer."
    )
    parsed = parse_answer(model_style)
    garbage_none = parse_answer("not an answer") is None
    report["G3_round_trip"] = {
        "pass": (parsed == shipping["answer"] and
                 verify(shipping, parsed)[0] and garbage_none),
        "parsed_equals_answer": parsed == shipping["answer"],
        "garbage_returns_none": garbage_none,
    }

    # G4 and the shipping density portion of G5 share the same 200k experiment.
    samples = 200_000
    sample_rng = random.Random(190605611)
    hits = 0
    for _ in range(samples):
        candidate = random_candidate(shipping, sample_rng)
        if verify(shipping, candidate)[0]:
            hits += 1
    guess_probability = hits / samples
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": guess_probability,
        "candidate_prior": "uniform normalized projective points already in Gamma",
        "search_space": search_space(shipping),
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    start = time.perf_counter()
    reference_answer, reference_operations = _reference_algorithm(shipping)
    reference_wall = time.perf_counter() - start
    reference_ok = (reference_answer is not None and
                    verify(shipping, reference_answer)[0])
    report["G5_density_and_baseline"] = {
        "pass": reference_ok,
        "shipping_density_observed": guess_probability,
        "shipping_density_samples": samples,
        "baseline_wall_clock_sec": reference_wall,
        "baseline_field_operations": reference_operations,
        "shipping_density": {
            "kind": "sampled",
            "hits": hits,
            "total": samples,
            "observed_fraction": guess_probability,
        },
        "demo_exact_valid_answers": demo_count,
        "demo_search_space": search_space(demo),
        "strongest_baseline": {
            "name": "RREF nullspace on all shifted vertex constraints",
            "success": reference_ok,
            "wall_clock_sec": reference_wall,
            "field_operations": reference_operations,
        },
    }

    # G6: Track-B attacks must all fail; the successful polynomial algorithm is
    # deliberately a sibling reference_algorithm rather than an attack.
    attack_counts = {
        "outlier_coordinate_score": 0,
        "greedy_sparse_nullspace": 0,
        "random_restart_256": 0,
        "by_hand_constant_or_axis_ansatz": 0,
    }
    attempts = 8
    ref_successes = 0
    ref_operations = []
    ref_total_wall = 0.0
    for seed in range(attempts):
        inst = make_instance(seed=10_000 + seed,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
        if verify(inst, _coordinate_score_attack(inst))[0]:
            attack_counts["outlier_coordinate_score"] += 1
        if verify(inst, _greedy_sparse_attack(inst))[0]:
            attack_counts["greedy_sparse_nullspace"] += 1
        restart_rng = random.Random(20_000 + seed)
        restart_won = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, restart_rng))[0]:
                restart_won = True
                break
        if restart_won:
            attack_counts["random_restart_256"] += 1
        if verify(inst, _constant_axis_attack(inst))[0]:
            attack_counts["by_hand_constant_or_axis_ansatz"] += 1
        one_ref_start = time.perf_counter()
        solved, ops = _reference_algorithm(inst)
        ref_total_wall += time.perf_counter() - one_ref_start
        ref_operations.append(ops)
        if solved is not None and verify(inst, solved)[0]:
            ref_successes += 1
    attacks_report = {
        name: {"successes": successes, "attempts": attempts}
        for name, successes in attack_counts.items()
    }
    all_failed = all(x["successes"] == 0 for x in attacks_report.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_successes == attempts,
        "attacks": attacks_report,
        "reference_algorithm": {
            "name": "modular RREF/nullspace elimination",
            "complexity": "O(d^3) exact field operations",
            "wall_clock_sec": ref_total_wall / attempts,
            "operations": round(sum(ref_operations) / len(ref_operations)),
            "operation_range": [min(ref_operations), max(ref_operations)],
            "solves": f"{ref_successes}/{attempts}, as expected",
        },
    }

    # G7: n controls q's bit size while the 97-coordinate answer stays fixed.
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": (doubled_ok and doubled["q"] > shipping["q"] and
                 search_space(doubled) > search_space(shipping)),
        "shipping_n": DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        "doubled_n": doubled_params["n"],
        "shipping_q": shipping["q"],
        "doubled_q": doubled["q"],
        "answer_elements_shipping": _atom_count(shipping["answer"]),
        "answer_elements_doubled": _atom_count(doubled["answer"]),
        "doubled_planted_verifies": doubled_ok,
    }

    # G8: arbitrary coordinate relabelling, equation-basis change, reversal of
    # the Frobenius generator (delta -> delta^-1), and every nonempty
    # composition.  The carried point makes each transformation substantive.
    invariant_checks = 0
    invariant_passed = 0
    carried_verifications = 0
    distinct_keys = []
    for seed in range(20):
        inst = make_instance(seed=seed,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        permutation = list(range(inst["extension_degree"]))
        random.Random(40_000 + seed).shuffle(permutation)
        relabelled = _coordinate_relabel(inst, permutation)
        row_changed = _row_relabel(inst, (seed + 2) % inst["q"] or 1)
        inverted = _generator_inverse_relabel(inst)
        coordinate_row = _row_relabel(
            relabelled, (seed + 5) % inst["q"] or 1
        )
        coordinate_inverse = _generator_inverse_relabel(relabelled)
        row_inverse = _generator_inverse_relabel(row_changed)
        all_three = _generator_inverse_relabel(coordinate_row)
        for transformed in (
                relabelled, row_changed, inverted, coordinate_row,
                coordinate_inverse, row_inverse, all_three):
            invariant_checks += 1
            if canonical_key(transformed) == key:
                invariant_passed += 1
            if verify(transformed, transformed["answer"])[0]:
                carried_verifications += 1
        distinct_keys.append(key)
    report["G8_canonical_key"] = {
        "pass": (invariant_passed == 140 and carried_verifications == 140 and
                 len(set(distinct_keys)) == 20),
        "invariance_checks": invariant_checks,
        "invariance_passed": invariant_passed,
        "carried_witness_verifications": carried_verifications,
        "unrelated_instances": 20,
        "distinct_keys": len(set(distinct_keys)),
        "transformations": [
            "arbitrary simultaneous coordinate/eigenvalue relabelling",
            "invertible equation-basis change with row reordering/scaling",
            "Frobenius-generator reversal carrying delta to its inverse",
            "all nonempty compositions of the three transformations",
        ],
    }

    measured_answers = [
        make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])["answer"]
        for seed in range(1_000)
    ]
    answer_chars = max(
        len(json.dumps(answer, separators=(",", ":")))
        for answer in measured_answers
    )
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _atom_count(shipping["answer"])
    intended_operations = d + 12
    arms = copy.deepcopy(G9_ARM_RESULTS)
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else None)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else None)
    report["G9_no_tool_suitability"] = {
        "pass": (answer_chars <= 2_000 and answer_elements <= 256 and
                 intended_operations <= 300),
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None
        ),
        "hinted_verdict": (
            "not_run" if not arms["hinted"]["attempts"] else
            ("too_easy" if arms["hinted"]["solved"] else "hardened")
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    gated = [
        report[name]["pass"] for name in (
            "G1_planted_verifies", "G2_rejects_corruption", "G3_round_trip",
            "G4_guess_resistance", "G5_density_and_baseline",
            "G6_adversary_panel", "G7_scales", "G8_canonical_key",
            "G9_no_tool_suitability",
        )
    ]
    report["all_gates_pass"] = all(gated)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
