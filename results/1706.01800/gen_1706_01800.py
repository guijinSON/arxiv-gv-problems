"""Verified Cauchy-resolution completion generator for arXiv:1706.01800.

Section 8.2 and Theorem 8.1 construct resolvable clique decompositions of
complete partite hypergraphs from Cauchy matrices.  This module uses the
graph case r=2: a resolution class and one vertex determine a unique
transversal K_f block.  A diagonal scaling of the Cauchy columns preserves
all nonzero minors and hides a residue-form block sampled by construction.

The generated certificate is never found by solving the displayed system.
It is evaluated directly from the partial-fraction identity

    R(X)/prod_j(X-y_j) = sum_j R(y_j)/D'(y_j)/(X-y_j).

With R(X)=c*prod_i(X-x_i), the right side vanishes at every zero-row
generator x_i.  Theorem 8.1 then supplies uniqueness after one coordinate
and the resolution-class equation are fixed.
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
import time
from typing import Any


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "complete partite complex with parts labelled by F_q",
        "generalized Cauchy matrix over F_q",
        "transversal clique in a specified resolution class",
    ],
    "verification_operations": [
        "exact modular inversion",
        "exact finite-field matrix-vector products",
        "coordinate and resolution-class comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "After absorbing the column scales, a Cauchy-kernel vector is the "
        "residue vector of a rational function; without that change of variables "
        "one must solve the displayed dense finite-field system."
    ),
    "hardness_basis": (
        "Track B: Theorem 8.1 explicitly completes the block by a nonsingular "
        "Cauchy linear system; Gauss-Jordan elimination is O(f^3) and the measured "
        "shipping preflights used 116,184 exact field operations in 0.004-0.017 "
        "seconds, "
        "whereas the planted residue recurrence "
        "uses 239 exact field operations and is not stated in the instance."
    ),
    "max_answer_tokens": 83,
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


# n is the number f of partite vertex classes.  q is the prime field order.
# Both the dense system and the arithmetic height grow along the named ladder.
DIFFICULTY = {
    "demo": {"n": 5, "q": 11},
    "easy": {"n": 32, "q": 257},
    "medium": {"n": 36, "q": 4099},
    "hard": {"n": 48, "q": 65537},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Cauchy nullvectors are residue vectors of a rational function over the field."
)
PLACEBO_HINT = (
    "Finite-field expressions should be evaluated with careful modular arithmetic throughout."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list [z_0,...,z_(f-1)] containing exactly one integer residue "
        "0..q-1 for each labelled vertex class, in class order, with the stated "
        "fixed coordinate already enforced."
    ),
    "bounds": {
        "answer_entries_at_shipping": 48,
        "entry_min": 0,
        "entry_max_inclusive_at_shipping": 65536,
        "fixed_coordinates": 1,
    },
}


# Populated from script-owned hardening runs before final delivery.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

NOTES = r"""
Paper grounding. Section 1.1 defines an F-decomposition as copies of F that
cover every edge exactly once. Section 8.2 defines a resolvable
K_f^(r)-decomposition of the complete f-partite complex K_{q x f}. Theorem
8.1 states that one exists whenever q is a prime power, 2f <= q and
1 <= r <= f-1. Its proof identifies each vertex class with F_q, uses a
(f-r+1)-by-f Cauchy matrix, and proves that a fixed (r-1)-set plus a
resolution-class label has exactly one completing transversal f-set. The
proof says exactly what produces the witness: solve the remaining square
Cauchy system. This explicit polynomial-time method rules out Track A.

Track-B decision. This module takes r=2. The reference algorithm forms the
(f-1)-by-(f-1) finite-field system from the fixed vertex and runs exact
Gauss-Jordan elimination, O(f^3). Its measured shipping wall time and exact
field-operation count are recorded in G5 and G6. The compact route changes
variables to u_j=s_j*z_j and recognizes u as a partial-fraction residue
vector. Consecutive row and column generators then give a first-order
recurrence. At f=48 it needs 239 exact field operations, counting each field
addition, multiplication or division once and including removal of the random
column scales, versus roughly one hundred thousand in the
reference elimination. This is no-tool compression, not a claim that the
instances resist algorithms.

Construction. Choose nonzero diagonal column scales and a nonzero residue
scale c first. For zero-row generators x=0,...,f-3 and column generators
y=f-1,...,2f-2, let B(X)=prod_x(X-x), D(X)=prod_y(X-y), set
u_j=c*B(y_j)/D'(y_j), and z_j=u_j/s_j. The partial-fraction identity makes
every zero-row dot product vanish. The target is evaluated directly at the
distinguished row x=f-2, and the coordinate with y=f-1 is revealed. Columns
and zero rows are then independently reordered. This is composition of an
identity followed by a structure-preserving diagonal scaling, never a solve.

Attacks. Column scales are independent uniform nonzero field elements, so
the planted coordinates have no raw magnitude/rank signature. A scale-rank
outlier candidate, a one-row greedy repair, 256 uniform restarts, and the
obvious constant-coordinate ansatz all fail on the shipping seeds. The exact
Gauss-Jordan reference algorithm succeeds, as Track B requires, and is kept
outside the failing attack panel. A specialized O(f^2) Cauchy solver was not
implemented; it would also succeed and reinforces rather than weakens the
Track-B label.

Canonicalization. Coordinate relabelling, zero-row reordering, simultaneous
affine changes of every Cauchy generator, and global scaling of all columns
and the target preserve the problem. The key fixes the distinguished row at
zero, tries every second affine anchor, normalizes the global column scale,
sorts the typed generators, and hashes the lexicographically least form. It
does not use the seed, rendered text, or planted answer.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"```(?:json|text)?\s*(.*?)```", re.I | re.S)
_LIST_RE = re.compile(r"\[[^\[\]]*\]", re.S)
_ENUMERATION_CAP = 200_000
_G4_SAMPLES = 200_000


def _is_prime(value: int) -> bool:
    """Deterministic Miller-Rabin for the supported 64-bit parameter range."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small:
        if value % p == 0:
            return value == p
    d = value - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    # Deterministic for unsigned 64-bit integers.
    for a in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if a % value == 0:
            continue
        x = pow(a, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _next_prime(value: int) -> int:
    candidate = max(3, value | 1)
    while candidate < 2**63 and not _is_prime(candidate):
        candidate += 2
    if candidate >= 2**63:
        raise ValueError("no supported next prime")
    return candidate


def _validate_params(n: int, q: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or not 3 <= n <= 256:
        raise ValueError("n must be an integer number of classes in 3..256")
    if isinstance(q, bool) or not isinstance(q, int) or not _is_prime(q):
        raise ValueError("q must be a prime")
    if q < 2 * n:
        raise ValueError("Theorem 8.1 requires q >= 2*n")
    if q >= 2**63:
        raise ValueError("q must be smaller than 2^63")


def _prod(values: Any, q: int) -> int:
    out = 1
    for value in values:
        out = out * (value % q) % q
    return out


def _coefficient(x: int, column: list[int], q: int) -> int:
    y, scale = column
    return scale * pow((x - y) % q, -1, q) % q


def _row_dot(inst: dict, x: int, vector: list[int]) -> int:
    q = inst["q"]
    return sum(
        _coefficient(x, column, q) * value
        for column, value in zip(inst["columns"], vector)
    ) % q


def make_instance(n: int, seed: int = 0, q: int = 65537, **params: Any) -> dict:
    """Build a unique Cauchy-resolution block by a residue identity.

    n is f, the number of vertex classes.  The construction samples the
    residue scale and diagonal column scales before it creates the equations.
    It evaluates a known partial-fraction identity; it never solves the system
    that is handed to the solver.
    """
    if params:
        raise TypeError(f"unexpected parameters: {sorted(params)}")
    _validate_params(n, q)
    rng = random.Random(seed)

    zero_rows = list(range(n - 2))
    target_row = n - 2
    y_values = list(range(n - 1, 2 * n - 1))
    scales = [rng.randrange(1, q) for _ in range(n)]
    residue_scale = rng.randrange(1, q)

    unscaled: list[int] = []
    for j, y in enumerate(y_values):
        numerator = _prod((y - x for x in zero_rows), q)
        denominator = _prod(
            (y - other for k, other in enumerate(y_values) if k != j), q
        )
        unscaled.append(
            residue_scale * numerator * pow(denominator % q, -1, q) % q
        )

    answer = [u * pow(scale, -1, q) % q for u, scale in zip(unscaled, scales)]
    target = sum(
        u * pow((target_row - y) % q, -1, q)
        for u, y in zip(unscaled, y_values)
    ) % q

    # The known vertex is the first consecutive column before public relabelling.
    fixed_old_index = 0
    permutation = list(range(n))
    rng.shuffle(permutation)
    columns = [[y_values[j], scales[j]] for j in permutation]
    answer = [answer[j] for j in permutation]
    fixed_index = permutation.index(fixed_old_index)
    rng.shuffle(zero_rows)

    inst = {
        "paper": "arXiv:1706.01800",
        "q": q,
        "f": n,
        "zero_row_generators": zero_rows,
        "target_row_generator": target_row,
        "columns": columns,
        "fixed_coordinate": [fixed_index, answer[fixed_index]],
        "target": target,
        "answer": answer,
    }
    ok, reason = verify(inst, answer)
    if not ok:
        raise AssertionError(f"construction identity failed: {reason}")
    return inst


def render(inst: dict) -> str:
    q = inst["q"]
    f = inst["f"]
    fixed_index, fixed_value = inst["fixed_coordinate"]
    column_lines = "\n".join(
        f"  part {j}: y={column[0]}, s={column[1]}"
        for j, column in enumerate(inst["columns"])
    )
    statement = f"""Cauchy resolution completion over F_{q}

The finite field F_{q} is represented by the integers 0,...,{q - 1}, with all
arithmetic modulo {q}.  For a nonzero residue a, a^(-1) means its unique
multiplicative inverse modulo {q}.

There are {f} labelled parts, numbered 0,...,{f - 1}; part j has one choice for
every value z_j in F_{q}.  A transversal block is a vector
z=[z_0,...,z_{f - 1}] selecting exactly one value from every part.

For a row generator x and the displayed column data (y_j,s_j), define

    L_x(z) = sum over j=0,...,{f - 1} of s_j*z_j*(x-y_j)^(-1)  (mod {q}).

All displayed x and y values are distinct, so every inverse exists.  Find the
unique transversal block z satisfying all of the following:

  1. L_x(z)=0 for every x in the zero-row list;
  2. L_{inst['target_row_generator']}(z)={inst['target']}; and
  3. z_{fixed_index}={fixed_value}.

The zero-row generators (their order is irrelevant) are:
  {', '.join(map(str, inst['zero_row_generators']))}

The target-row generator is x={inst['target_row_generator']} and its required
value is {inst['target']}.

Column data, in labelled part order:
{column_lines}

The fixed choice is part {fixed_index}, value {fixed_value}.

Give your final answer inside <answer></answer> tags as one JSON list of exactly
{f} integer residues in part order.  Indices are 0-based, repetitions between
different parts are allowed, and every entry must lie in 0..{q - 1} inclusive.
Example of the syntax only: <answer>[0, 1, 2]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: Any) -> object | None:
    """Extract a flat JSON integer list from tags, fences, or surrounding prose."""
    if not isinstance(text, str):
        return None
    tagged = _ANSWER_RE.findall(text)
    candidates = list(reversed(tagged))
    if not candidates:
        candidates.extend(reversed(_FENCE_RE.findall(text)))
    if not candidates:
        candidates.extend(reversed(_LIST_RE.findall(text)))
    for candidate in candidates:
        fenced = _FENCE_RE.search(candidate)
        if fenced:
            candidate = fenced.group(1)
        candidate = candidate.strip()
        try:
            value = json.loads(candidate)
        except (TypeError, ValueError, json.JSONDecodeError):
            match = _LIST_RE.search(candidate)
            if not match:
                continue
            try:
                value = json.loads(match.group(0))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        if isinstance(value, list) and all(
            isinstance(entry, int) and not isinstance(entry, bool) for entry in value
        ):
            return value
    return None


def verify(inst: dict, answer: Any) -> tuple[bool, str]:
    """Check a candidate directly; deliberately never consult inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer list is empty"
    f = inst["f"]
    q = inst["q"]
    if len(answer) != f:
        return False, f"expected exactly {f} coordinates, got {len(answer)}"
    for index, value in enumerate(answer):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"coordinate {index} is not an integer"
        if not 0 <= value < q:
            return False, f"coordinate {index} is outside 0..{q - 1}"
    fixed_index, fixed_value = inst["fixed_coordinate"]
    if answer[fixed_index] != fixed_value:
        return False, f"fixed coordinate {fixed_index} does not match"
    for x in inst["zero_row_generators"]:
        value = _row_dot(inst, x, answer)
        if value != 0:
            return False, f"zero-row equation x={x} has residue {value}"
    value = _row_dot(inst, inst["target_row_generator"], answer)
    if value != inst["target"]:
        return False, f"target-row equation has residue {value}, not {inst['target']}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly after enforcing shape, field range, and the fixed vertex."""
    candidate = [rng.randrange(inst["q"]) for _ in range(inst["f"])]
    fixed_index, fixed_value = inst["fixed_coordinate"]
    candidate[fixed_index] = fixed_value
    return candidate


def search_space(inst: dict) -> int | None:
    """The structure-aware language fixes one of f field coordinates."""
    return inst["q"] ** (inst["f"] - 1)


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the bounded language only when it has at most 200k words."""
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    fixed_index, fixed_value = inst["fixed_coordinate"]
    free = [j for j in range(inst["f"]) if j != fixed_index]
    count = 0
    candidate = [0] * inst["f"]
    candidate[fixed_index] = fixed_value
    for values in itertools.product(range(inst["q"]), repeat=len(free)):
        for index, value in zip(free, values):
            candidate[index] = value
        if verify(inst, candidate)[0]:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Canonicalize the generated linear problem under its public relabellings."""
    q = inst["q"]
    x_hat = inst["target_row_generator"]
    fixed_index, fixed_value = inst["fixed_coordinate"]
    generators = (
        list(inst["zero_row_generators"])
        + [x_hat]
        + [column[0] for column in inst["columns"]]
    )
    best: tuple | None = None

    # Any affine equivalence must carry the distinguished target generator to
    # the distinguished target generator.  Fix it at zero, and try every other
    # generator as the unit anchor.
    for anchor in generators:
        if anchor == x_hat:
            continue
        delta = (anchor - x_hat) % q
        inv_delta = pow(delta, -1, q)
        normalized_zero = tuple(
            sorted((x - x_hat) * inv_delta % q for x in inst["zero_row_generators"])
        )
        raw_columns = []
        for index, (y, scale) in enumerate(inst["columns"]):
            raw_columns.append(
                ((y - x_hat) * inv_delta % q, scale, int(index == fixed_index))
            )
        raw_columns.sort()
        scale_pivot = raw_columns[0][1]
        inv_scale = pow(scale_pivot, -1, q)
        normalized_columns = tuple(
            (y, scale * inv_scale % q, marker)
            for y, scale, marker in raw_columns
        )
        # Under v -> (v-x_hat)/delta, every Cauchy coefficient and the
        # target are multiplied by delta.  A common column scaling is then
        # divided out with scale_pivot.
        normalized_target = inst["target"] * delta * inv_scale % q
        form = (
            q,
            inst["f"],
            normalized_zero,
            normalized_columns,
            fixed_value,
            normalized_target,
        )
        if best is None or form < best:
            best = form
    if best is None:
        raise ValueError("instance has no second affine anchor")
    return hashlib.sha256(repr(best).encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Raise field height first, preserving the 48-coordinate witness."""
    harder = {key: value for key, value in params.items() if key != "_preset"}
    n = int(harder["n"])
    q = int(harder["q"])
    field_ladder = [
        257,
        4099,
        65537,
        1_000_003,
        10_000_019,
        100_000_007,
        1_000_000_007,
        2_147_483_647,
        32_416_190_071,
    ]
    for candidate in field_ladder:
        if candidate > q and candidate >= 2 * n:
            harder["q"] = candidate
            return harder
    # A longer block remains mathematically possible, but at f>60 the residue
    # recurrence crosses the 300-operation no-tool cap.
    if n < 60:
        harder["n"] = 60
        harder["q"] = _next_prime(max(q + 2, 2 * 60 + 1))
        return harder
    return "cap_bound"


def _reference_solve(inst: dict) -> tuple[list[int], int]:
    """Exact Gauss-Jordan completion; return solution and counted field ops."""
    q = inst["q"]
    fixed_index, fixed_value = inst["fixed_coordinate"]
    unknown = [j for j in range(inst["f"]) if j != fixed_index]
    rows = list(inst["zero_row_generators"]) + [inst["target_row_generator"]]
    matrix: list[list[int]] = []
    rhs: list[int] = []
    operations = 0

    for row_number, x in enumerate(rows):
        line = []
        for index in unknown:
            y, scale = inst["columns"][index]
            difference = (x - y) % q
            coefficient = scale * pow(difference, -1, q) % q
            operations += 3  # subtraction, inversion, multiplication
            line.append(coefficient)
        fixed_coefficient = _coefficient(x, inst["columns"][fixed_index], q)
        operations += 3
        wanted = inst["target"] if row_number == len(rows) - 1 else 0
        rhs.append((wanted - fixed_coefficient * fixed_value) % q)
        operations += 2
        matrix.append(line)

    size = len(unknown)
    for pivot_column in range(size):
        pivot_row = next(
            (r for r in range(pivot_column, size) if matrix[r][pivot_column]),
            None,
        )
        if pivot_row is None:
            raise ArithmeticError("singular completion system")
        if pivot_row != pivot_column:
            matrix[pivot_column], matrix[pivot_row] = (
                matrix[pivot_row],
                matrix[pivot_column],
            )
            rhs[pivot_column], rhs[pivot_row] = rhs[pivot_row], rhs[pivot_column]
        inverse = pow(matrix[pivot_column][pivot_column], -1, q)
        operations += 1
        for column in range(pivot_column, size):
            matrix[pivot_column][column] = (
                matrix[pivot_column][column] * inverse % q
            )
            operations += 1
        rhs[pivot_column] = rhs[pivot_column] * inverse % q
        operations += 1
        for row in range(size):
            if row == pivot_column:
                continue
            factor = matrix[row][pivot_column]
            if factor == 0:
                continue
            for column in range(pivot_column, size):
                matrix[row][column] = (
                    matrix[row][column]
                    - factor * matrix[pivot_column][column]
                ) % q
                operations += 2
            rhs[row] = (rhs[row] - factor * rhs[pivot_column]) % q
            operations += 2

    answer = [0] * inst["f"]
    answer[fixed_index] = fixed_value
    for index, value in zip(unknown, rhs):
        answer[index] = value
    return answer, operations


def _compact_residue_solve(inst: dict) -> tuple[list[int], int]:
    """The intended residue recurrence, counted in exact F_q operations.

    Addition, multiplication, and division in F_q each count as one operation;
    comparisons, sorting public labels, indexing, and sign changes do not.
    This routine is a test oracle for the claimed compact route, not the method
    used by make_instance to obtain its planted certificate.
    """
    q = inst["q"]
    f = inst["f"]
    by_y = sorted(range(f), key=lambda index: inst["columns"][index][0])
    fixed_index, fixed_value = inst["fixed_coordinate"]
    if by_y[0] != fixed_index or inst["columns"][fixed_index][0] != f - 1:
        raise ValueError("instance is outside the consecutive-residue family")

    # u_0=s_0*z_0.  The target identity t*f*(f-1)=-u_0 proves that
    # the degree-at-most-one numerator takes the same value at two points,
    # hence is constant.
    u = inst["columns"][fixed_index][1] * fixed_value % q
    operations = 1
    ff = f * (f - 1) % q
    target_check = (inst["target"] * ff + u) % q
    operations += 3
    if target_check != 0:
        raise ValueError("target does not select the constant numerator")

    answer = [0] * f
    answer[fixed_index] = fixed_value
    for j in range(f - 1):
        numerator = -u * (f + j) % q
        numerator = numerator * (f - 1 - j) % q
        denominator = (j + 2) * (j + 1) % q
        u = numerator * pow(denominator, -1, q) % q
        operations += 4  # two products, one denominator product, one field division
        index = by_y[j + 1]
        scale = inst["columns"][index][1]
        answer[index] = u * pow(scale, -1, q) % q
        operations += 1  # one field division by the column scale
    return answer, operations


def _outlier_scale_rank(inst: dict) -> list[int]:
    """Guess values from the public multiplier ranks, preserving the fixed one."""
    q = inst["q"]
    order = sorted(range(inst["f"]), key=lambda j: inst["columns"][j][1])
    candidate = [0] * inst["f"]
    for rank, index in enumerate(order):
        candidate[index] = rank % q
    fixed_index, fixed_value = inst["fixed_coordinate"]
    candidate[fixed_index] = fixed_value
    return candidate


def _greedy_one_row(inst: dict) -> list[int]:
    """Set almost everything to zero and repair the first displayed equation."""
    candidate = [0] * inst["f"]
    fixed_index, fixed_value = inst["fixed_coordinate"]
    candidate[fixed_index] = fixed_value
    repair = next(index for index in range(inst["f"]) if index != fixed_index)
    x = inst["zero_row_generators"][0]
    residual = _row_dot(inst, x, candidate)
    coefficient = _coefficient(x, inst["columns"][repair], inst["q"])
    candidate[repair] = -residual * pow(coefficient, -1, inst["q"]) % inst["q"]
    return candidate


def _constant_coordinate_ansatz(inst: dict) -> list[int]:
    """Assume all selected field labels equal the one revealed label."""
    return [inst["fixed_coordinate"][1]] * inst["f"]


def _relabel_columns(inst: dict, permutation: list[int]) -> dict:
    transformed = copy.deepcopy(inst)
    transformed["columns"] = [copy.deepcopy(inst["columns"][j]) for j in permutation]
    transformed["answer"] = [inst["answer"][j] for j in permutation]
    old_fixed, fixed_value = inst["fixed_coordinate"]
    transformed["fixed_coordinate"] = [permutation.index(old_fixed), fixed_value]
    return transformed


def _affine_generators(inst: dict, multiplier: int, translation: int) -> dict:
    transformed = copy.deepcopy(inst)
    q = inst["q"]
    transformed["zero_row_generators"] = [
        (multiplier * x + translation) % q for x in inst["zero_row_generators"]
    ]
    transformed["target_row_generator"] = (
        multiplier * inst["target_row_generator"] + translation
    ) % q
    transformed["columns"] = [
        [(multiplier * y + translation) % q, scale]
        for y, scale in inst["columns"]
    ]
    transformed["target"] = inst["target"] * pow(multiplier, -1, q) % q
    return transformed


def _global_column_scale(inst: dict, multiplier: int) -> dict:
    transformed = copy.deepcopy(inst)
    q = inst["q"]
    transformed["columns"] = [
        [y, scale * multiplier % q] for y, scale in inst["columns"]
    ]
    transformed["target"] = inst["target"] * multiplier % q
    return transformed


def _answer_atoms(answer: Any) -> int:
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest() -> dict:
    """Run all mandatory correctness, resistance, scaling and format gates."""
    report: dict[str, Any] = {
        "paper": "1706.01800",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: every named preset, three independent seeds.
    planted_checks = 0
    json_checks = 0
    planted_failures: list[str] = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            planted_checks += 1
            if not ok:
                planted_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_checks += 1
    report["G1_planted_verifies"] = {
        "pass": not planted_failures and json_checks == planted_checks,
        "checks": planted_checks,
        "json_native_checks": json_checks,
        "failures": planted_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **shipping_params)

    # G2: choose corruptions whose first failed conditions are intentionally distinct.
    corruptions: dict[str, list[int]] = {
        "empty": [],
        "drop": list(inst["answer"][:-1]),
        "out_of_range": list(inst["answer"]),
    }
    corruptions["out_of_range"][0] = inst["q"]
    fixed_index = inst["fixed_coordinate"][0]
    swap_index = next(
        j for j, value in enumerate(inst["answer"])
        if j != fixed_index and value != inst["answer"][fixed_index]
    )
    swapped = list(inst["answer"])
    swapped[fixed_index], swapped[swap_index] = swapped[swap_index], swapped[fixed_index]
    corruptions["swap"] = swapped
    duplicate_index = next(
        j for j, value in enumerate(inst["answer"])
        if j != fixed_index and value != inst["answer"][fixed_index]
    )
    duplicated = list(inst["answer"])
    duplicated[duplicate_index] = inst["answer"][fixed_index]
    corruptions["duplicate"] = duplicated
    rejection_reasons = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        rejection_reasons[name] = {"rejected": not ok, "reason": reason}
    distinct_reasons = len({entry["reason"] for entry in rejection_reasons.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in rejection_reasons.values())
        and distinct_reasons == len(rejection_reasons),
        "distinct_reasons": distinct_reasons,
        "cases": rejection_reasons,
    }

    # G3: exact round-trip through a realistic fenced/prose response.
    realistic = (
        "I used the modular equations.\n```json\n<answer>"
        + json.dumps(inst["answer"])
        + "</answer>\n```\nThe list is in class order."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"],
        "parsed_entries": len(parsed) if isinstance(parsed, list) else 0,
        "garbage_returns_none": parse_answer("no delimited answer here") is None,
    }

    # G4 and shipping-density sample: uniform over the structure-aware language.
    guess_rng = random.Random(0x170601800)
    guess_hits = 0
    t0 = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            guess_hits += 1
    sampling_wall = time.perf_counter() - t0
    report["G4_guess_resistance"] = {
        "pass": guess_hits / _G4_SAMPLES < 1e-6,
        "hits": guess_hits,
        "total": _G4_SAMPLES,
        "observed_probability": guess_hits / _G4_SAMPLES,
        "structure_aware_space": search_space(inst),
        "sampler_constraints": "shape, field range, and fixed coordinate enforced",
        "wall_clock_sec": round(sampling_wall, 6),
    }

    # G5: demo enumeration plus shipping density and measured reference cost.
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    t0 = time.perf_counter()
    reference_answer, reference_operations = _reference_solve(inst)
    reference_wall = time.perf_counter() - t0
    reference_ok = verify(inst, reference_answer)[0]
    exact_density = 1 / search_space(inst)
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and reference_ok,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": _G4_SAMPLES,
        "shipping_sampled_density": guess_hits / _G4_SAMPLES,
        "shipping_theorem_exact_density": exact_density,
        "baseline_wall_clock_sec": round(reference_wall, 6),
        "baseline_field_operations": reference_operations,
        "baseline_iterations": inst["f"] - 1,
        "baseline_verified": reference_ok,
    }

    # G6: four failures, and the successful Track-B reference kept separate.
    attack_counts = {
        "outlier_scale_rank": 0,
        "greedy_one_row_repair": 0,
        "random_restart_256": 0,
        "constant_coordinate_ansatz": 0,
    }
    reference_successes = 0
    reference_total_operations = 0
    reference_total_wall = 0.0
    attack_seeds = list(range(8))
    for seed in attack_seeds:
        attacked = make_instance(seed=seed + 9000, **shipping_params)
        candidates = {
            "outlier_scale_rank": _outlier_scale_rank(attacked),
            "greedy_one_row_repair": _greedy_one_row(attacked),
            "constant_coordinate_ansatz": _constant_coordinate_ansatz(attacked),
        }
        restart_rng = random.Random(seed + 70000)
        random_success = False
        for _ in range(256):
            if verify(attacked, random_candidate(attacked, restart_rng))[0]:
                random_success = True
                break
        attack_counts["random_restart_256"] += int(random_success)
        for name, candidate in candidates.items():
            attack_counts[name] += int(verify(attacked, candidate)[0])
        rt0 = time.perf_counter()
        solved, operations = _reference_solve(attacked)
        reference_total_wall += time.perf_counter() - rt0
        reference_total_operations += operations
        reference_successes += int(verify(attacked, solved)[0])
    attacks = {
        name: {"successes": successes, "attempts": len(attack_seeds)}
        for name, successes in attack_counts.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Gauss-Jordan elimination over F_q",
            "complexity": "O(f^3) exact field operations",
            "wall_clock_sec": round(reference_total_wall, 6),
            "mean_field_operations": reference_total_operations // len(attack_seeds),
            "operations_total": reference_total_operations,
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
    }

    # G7: ladder spaces strictly increase and a doubled class count still builds.
    ladder_spaces = []
    for preset, params in DIFFICULTY.items():
        ladder_inst = make_instance(seed=31337, **params)
        ladder_spaces.append([preset, search_space(ladder_inst).bit_length()])
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    doubled_n = 2 * shipping["n"]
    doubled_q = shipping["q"] if shipping["q"] >= 2 * doubled_n else _next_prime(2 * doubled_n)
    doubled = make_instance(n=doubled_n, q=doubled_q, seed=271828)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    strict = all(
        ladder_spaces[index][1] < ladder_spaces[index + 1][1]
        for index in range(len(ladder_spaces) - 1)
    )
    report["G7_scales"] = {
        "pass": strict and doubled_ok,
        "candidate_space_bits_by_preset": ladder_spaces,
        "doubled_n": doubled_n,
        "doubled_build_and_verify": doubled_ok,
    }

    # G8: four generators of the equivalence group and their composition.
    invariance_checks = 0
    carried_checks = 0
    canonical_failures: list[str] = []
    distinct_keys = set()
    for seed in range(20):
        base = make_instance(seed=100000 + seed, **shipping_params)
        distinct_keys.add(canonical_key(base))
        rng = random.Random(seed + 500000)
        permutation = list(range(base["f"]))
        rng.shuffle(permutation)
        relabelled = _relabel_columns(base, permutation)
        reordered = copy.deepcopy(base)
        reordered["zero_row_generators"].reverse()
        affine = _affine_generators(
            base, rng.randrange(1, base["q"]), rng.randrange(base["q"])
        )
        scaled = _global_column_scale(base, rng.randrange(1, base["q"]))
        composed = _global_column_scale(
            _affine_generators(
                _relabel_columns(base, permutation),
                rng.randrange(1, base["q"]),
                rng.randrange(base["q"]),
            ),
            rng.randrange(1, base["q"]),
        )
        base_key = canonical_key(base)
        for name, transformed in (
            ("column_relabelling", relabelled),
            ("zero_row_reordering", reordered),
            ("affine_generator_map", affine),
            ("global_column_scaling", scaled),
            ("composed", composed),
        ):
            invariance_checks += 1
            if canonical_key(transformed) != base_key:
                canonical_failures.append(f"seed {seed}: {name} changed key")
            carried_checks += 1
            if not verify(transformed, transformed["answer"])[0]:
                canonical_failures.append(f"seed {seed}: {name} broke witness")
    report["G8_canonical_key"] = {
        "pass": not canonical_failures and len(distinct_keys) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated_keys": len(distinct_keys),
        "unrelated_instances": 20,
        "failures": canonical_failures,
    }

    # G9(c) is gated; the three oracle arms are script-owned diagnostics.
    blobs = [
        json.dumps(make_instance(seed=seed, **shipping_params)["answer"])
        for seed in range(20)
    ]
    answer_chars = max(map(len, blobs))
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = max(
        _answer_atoms(make_instance(seed=seed, **shipping_params)["answer"])
        for seed in range(20)
    )
    compact_verified = 0
    compact_operation_counts = []
    for seed in range(20):
        compact_inst = make_instance(seed=seed, **shipping_params)
        compact_answer, compact_operations = _compact_residue_solve(compact_inst)
        compact_operation_counts.append(compact_operations)
        compact_verified += int(verify(compact_inst, compact_answer)[0])
    intended_operations = max(compact_operation_counts)
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    hinted = G9_ORACLE_RESULTS["hinted"]
    placebo = G9_ORACLE_RESULTS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {
            "bare": dict(G9_ORACLE_RESULTS["bare"]),
            "hinted": dict(hinted),
            "placebo": dict(placebo),
        },
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "intended_route_verified_instances": compact_verified,
        "operation_unit": "one exact F_q addition, multiplication, or division",
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
