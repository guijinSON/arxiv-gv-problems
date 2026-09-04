"""Formal-dual recovery for products of finite-field Gauss configurations.

Instances use the finite abelian-group formulation in Definition 2.9 of
arXiv:1306.6796.  They are generated from Theorem 3.2, transported by affine
automorphisms, and composed with Lemma 3.1.  The answer is a compact quadratic
parametrisation of a formal dual, not an enumeration of all of its points.
"""

from __future__ import annotations

import itertools
import json
import math
import os
import random
import re
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # pragma: no cover - the standard-library path is complete
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "polynomial_identity",
    "certificate_form": "polynomial",
    "native_objects": [
        "subsets of finite abelian groups F_p^2",
        "quadratic polynomial maps over F_p",
        "direct products of formally dual sets",
    ],
    "verification_operations": [
        "modular Gaussian elimination",
        "exact polynomial evaluation over F_p",
        "rank-one quadratic-form kernel",
        "modular determinant and orthogonality checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Each unordered factor is an affine parabola, whose rank-one conic "
        "quadratic part exposes the one direction absent from its differences."
    ),
    "hardness_basis": (
        "Track B: the domain-standard difference-direction histogram uses "
        "O(sum p_i^2) field operations (6,153,554 ordered differences and "
        "0.88 seconds in the final selftest at the tested easy preset), while "
        "fitting two five-point "
        "conics and taking their kernels uses 260 exact field operations once "
        "the invariant is seen."
    ),
    "max_answer_tokens": 11,
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


# n is a lower bound for each prime modulus.  prime_pool controls diversity;
# it does not change the answer length.  The demo has one tiny factor so that
# every direction can be checked on paper.
DIFFICULTY = {
    "demo": {"n": 5, "factors": 1, "prime_pool": 1},
    "easy": {"n": 1601, "factors": 2, "prime_pool": 32},
    "medium": {"n": 2503, "factors": 2, "prime_pool": 32},
    "hard": {"n": 3503, "factors": 2, "prime_pool": 32},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Each factor lies on a conic whose rank-one quadratic part has the missing "
    "difference direction as its kernel."
)
PLACEBO_HINT = (
    "Each factor rewards careful modular arithmetic and consistent coefficient "
    "normalization throughout the calculation."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One canonical 2-by-3 quadratic coefficient matrix per factor: rows "
        "encode q_x*t^2+l_x*t+c_x and q_y*t^2+l_y*t+c_y over F_p; q is a "
        "normalized projective direction, l is its prescribed canonical "
        "complement, and c=(0,0)."
    ),
    "bounds": {
        "max_factors": 2,
        "rows_per_factor": 2,
        "coefficients_per_row": 3,
        "coefficient_range": "0 <= coefficient < the factor prime p",
        "candidate_directions_per_factor": "p+1",
    },
}

NOTES = r"""
Paper boundary. Section 2, Definition 2.9 is the exact finite-group definition
used by the checker. Theorem 3.2 supplies the Gauss-sum parabola pair in
(Z/pZ)^2, and Lemma 3.1 licenses the direct product. The paragraph beginning
Section 4.1 supplies translation invariance; the corresponding contragredient
action of a group automorphism follows immediately from Definition 2.9. No
graph or integer-coordinate surrogate is used.

What makes it easy, and the Track B decision. The paper gives the forward
quadratic construction explicitly, but it does not give a hard recovery
theorem. On this generated distribution a complete histogram of the directions
of all ordered differences recovers the unique absent line in O(sum p_i^2)
finite-field operations. Therefore Track A would be false. At the shipping
preset selftest records both the exact number of pair differences and wall
clock time under reference_algorithm. The compact route fits the unique conic
through any five displayed points, observes that its homogeneous quadratic
part has rank one, and takes its kernel; two forward eliminations remain below
300 counted exact operations. Recognising why the perpendicular kernel gives
the dual is the intended invariant, and executing the dense modular arithmetic
without a CAS remains the Track B obstacle.

Generation. For each independently chosen prime, sample nonparallel vectors q
and l and a translation c, form S={q*t^2+l*t+c:t in F_p}, and shuffle it. The
known dual quadratic direction is the perpendicular to q; it is normalized and
completed canonically before S is built, so generation never solves its own
instance. Products compose by Lemma 3.1. Prime multisets, rather than affine
disguises, provide genuine non-isomorphic diversity.

Attack controls. Translation and a uniform affine basis make coordinate sizes,
axes, and early list positions uninformative. The panel tests a coordinate
outlier, a greedy direction absent from a small prefix, 256 full random
restarts, and the tempting second difference of three adjacent-but-shuffled
points. All are required to fail on eight seeds. The quadratic difference
histogram is reported separately as the successful Track B reference method.
""".strip()


# Filled after the three independent harden.py runs.  Keeping the counts here
# lets selftest remain deterministic and perform no file I/O.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "too_easy",
}


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    limit = math.isqrt(value)
    divisor = 3
    while divisor <= limit:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _prime_list(lower: int, count: int) -> list[int]:
    candidate = max(3, lower)
    if candidate % 2 == 0:
        candidate += 1
    out = []
    while len(out) < count:
        if _is_prime(candidate):
            out.append(candidate)
        candidate += 2
    return out


def _det(a: tuple[int, int], b: tuple[int, int], p: int) -> int:
    return (a[0] * b[1] - a[1] * b[0]) % p


def _normalize_line(vector: tuple[int, int], p: int) -> tuple[int, int] | None:
    x, y = vector[0] % p, vector[1] % p
    if x:
        return (1, y * pow(x, -1, p) % p)
    if y:
        return (0, 1)
    return None


def _perp(vector: tuple[int, int], p: int) -> tuple[int, int]:
    return (-vector[1] % p, vector[0] % p)


def _canonical_l(q: tuple[int, int]) -> tuple[int, int]:
    return (1, 0) if q == (0, 1) else (0, 1)


def _matrix_for_direction(q: tuple[int, int]) -> list[list[int]]:
    l = _canonical_l(q)
    return [[q[0], l[0], 0], [q[1], l[1], 0]]


def _sample_nonzero_vector(p: int, rng: random.Random) -> tuple[int, int]:
    while True:
        value = (rng.randrange(p), rng.randrange(p))
        if value != (0, 0):
            return value


def make_instance(n: int, seed: int = 0, factors: int = 2,
                  prime_pool: int = 32, **params) -> dict:
    """Build a theorem-backed product and carry its dual through affine maps."""
    del params
    if isinstance(n, bool) or not isinstance(n, int) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if isinstance(factors, bool) or not isinstance(factors, int) or not 1 <= factors <= 2:
        raise ValueError("factors must be 1 or 2")
    if (isinstance(prime_pool, bool) or not isinstance(prime_pool, int)
            or prime_pool < factors):
        raise ValueError("prime_pool must be an integer at least factors")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    primes = rng.sample(_prime_list(n, prime_pool), factors)
    components = []
    answer = []
    for p in primes:
        q = _sample_nonzero_vector(p, rng)
        while True:
            linear = _sample_nonzero_vector(p, rng)
            if _det(q, linear, p):
                break
        constant = (rng.randrange(p), rng.randrange(p))
        points = [
            [
                (q[0] * t * t + linear[0] * t + constant[0]) % p,
                (q[1] * t * t + linear[1] * t + constant[1]) % p,
            ]
            for t in range(p)
        ]
        rng.shuffle(points)
        components.append({"p": p, "points": points})

        dual_q = _normalize_line(_perp(q, p), p)
        assert dual_q is not None
        answer.append(_matrix_for_direction(dual_q))

    return {
        "n": n,
        "factors": factors,
        "prime_pool": prime_pool,
        "components": components,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a complete finite-group recovery problem."""
    lines = [
        "FORMAL DUAL OF A PRODUCT OF FINITE-FIELD CONFIGURATIONS",
        "",
        "For an odd prime p, F_p means integers modulo p.  Identify the additive",
        "group G=F_p^2 with its character group using",
        "  <(x1,x2),(y1,y2)> = exp(2*pi*i*(x1*y1+x2*y2)/p).",
        "For a subset U and g in G, let nu_U(g) be the number of ordered pairs",
        "(u,u') in U x U with g=u-u'.  Subsets S,T of G, each of size p,",
        "are formally dual when, for every y in G,",
        "  |sum_{s in S} <s,y>|^2 / p^2 = nu_T(y) / p.",
        "All coordinates and polynomial coefficients below are reduced to 0..p-1.",
        "",
        "You are given unordered point sets S_i in separate groups F_{p_i}^2.",
        "It is promised that every S_i has a formal dual of the required form.",
        "For each factor output a 2-by-3 matrix",
        "  [[q_x,l_x,c_x],[q_y,l_y,c_y]],",
        "which represents T_i={q*t^2+l*t+c : t in F_p}.",
        "The required canonical form is: q is nonzero and its first nonzero",
        "coordinate is 1; c=(0,0); and l=(1,0) when q=(0,1), otherwise l=(0,1).",
        "The matrices must appear in the same factor order as the input.  Their",
        "Cartesian product is then the requested formal dual of the product of",
        "the S_i.  Input point order is irrelevant and points never repeat.",
        "",
    ]
    for index, component in enumerate(inst["components"], 1):
        p = component["p"]
        lines.append(f"Factor {index}: p={p}, |S_{index}|={p}")
        chunks = []
        row = []
        for point in component["points"]:
            row.append(f"({point[0]},{point[1]})")
            if len(row) == 12:
                chunks.append(" ".join(row))
                row = []
        if row:
            chunks.append(" ".join(row))
        lines.extend("  " + chunk for chunk in chunks)
        lines.append("")

    syntax = ",".join("[[1,0,0],[0,1,0]]" for _ in inst["components"])
    lines.extend([
        "Give your final answer inside <answer></answer> tags as a JSON list of",
        f"exactly {len(inst['components'])} matrices in factor order.",
        f"Syntax example only (not asserted valid here): <answer>[{syntax}]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str):
    """Extract the JSON matrix list from tags, a fence, or surrounding prose."""
    if not isinstance(text, str):
        return None
    tagged = re.search(r"<answer\s*>(.*?)</answer\s*>", text,
                       flags=re.IGNORECASE | re.DOTALL)
    candidates = [tagged.group(1)] if tagged else []
    candidates.extend(re.findall(r"```(?:json)?\s*(.*?)```", text,
                                 flags=re.IGNORECASE | re.DOTALL))
    candidates.append(text)
    decoder = json.JSONDecoder()
    for candidate in candidates:
        for match in re.finditer(r"\[", candidate):
            try:
                value, _ = decoder.raw_decode(candidate[match.start():])
            except (ValueError, TypeError):
                continue
            if isinstance(value, list):
                return value
    return None


def _fit_conic(points: list[list[int]], p: int,
               counter: list[int] | None = None) -> list[int]:
    """Return [A,B,C,D,E,F] for the conic through the first five points."""
    if len(points) < 5:
        raise ValueError("fewer than five points")
    matrix = []
    for x, y in points[:5]:
        matrix.append([x * x % p, x * y % p, y * y % p, x % p, y % p, 1])

    pivot_cols = []
    row = 0
    for col in range(6):
        pivot = next((r for r in range(row, 5) if matrix[r][col] % p), None)
        if pivot is None:
            continue
        matrix[row], matrix[pivot] = matrix[pivot], matrix[row]
        inv = pow(matrix[row][col], -1, p)
        if counter is not None:
            counter[0] += 1
        matrix[row][col] = 1
        for j in range(col + 1, 6):
            matrix[row][j] = matrix[row][j] * inv % p
            if counter is not None:
                counter[0] += 1
        for r in range(row + 1, 5):
            factor = matrix[r][col] % p
            if not factor:
                continue
            matrix[r][col] = 0
            for j in range(col + 1, 6):
                matrix[r][j] = (matrix[r][j] - factor * matrix[row][j]) % p
                if counter is not None:
                    counter[0] += 2
        pivot_cols.append(col)
        row += 1
        if row == 5:
            break
    if row != 5:
        raise ValueError("first five points do not determine a unique conic")
    free_cols = [col for col in range(6) if col not in pivot_cols]
    if len(free_cols) != 1:
        raise ValueError("conic nullspace is not one-dimensional")
    solution = [0] * 6
    solution[free_cols[0]] = 1
    for r in range(4, -1, -1):
        col = pivot_cols[r]
        total = 0
        for j in range(col + 1, 6):
            if solution[j]:
                total = (total + matrix[r][j] * solution[j]) % p
                if counter is not None:
                    counter[0] += 2
        solution[col] = -total % p
    return solution


def _missing_direction_conic(component: dict,
                             counter: list[int] | None = None) -> tuple[int, int]:
    p = component["p"]
    points = component["points"]
    if len(points) != p or len({tuple(v) for v in points}) != p:
        raise ValueError("component must contain p distinct points")
    if any(not isinstance(v, list) or len(v) != 2 for v in points):
        raise ValueError("component points must be coordinate pairs")
    if any(isinstance(z, bool) or not isinstance(z, int) or not 0 <= z < p
           for v in points for z in v):
        raise ValueError("component coordinate outside F_p")

    coeff = _fit_conic(points, p, counter)
    a, b, c, d, e, f = coeff
    if (b * b - 4 * a * c) % p != 0 or (a, b, c) == (0, 0, 0):
        raise ValueError("component conic does not have rank-one quadratic part")
    if a or b:
        kernel = _normalize_line((b, -2 * a), p)
    else:
        kernel = (1, 0)
    assert kernel is not None
    if (d * kernel[0] + e * kernel[1]) % p == 0:
        raise ValueError("component conic is degenerate along its kernel")
    for x, y in points:
        value = (a * x * x + b * x * y + c * y * y + d * x + e * y + f) % p
        if value:
            raise ValueError("a listed point is off the recovered conic")
    return kernel


def _instance_missing_lines(inst: dict) -> list[tuple[int, int]]:
    cached = inst.get("_conic_line_cache")
    if cached is not None:
        return [tuple(v) for v in cached]
    lines = [_missing_direction_conic(component)
             for component in inst["components"]]
    inst["_conic_line_cache"] = [list(v) for v in lines]
    return lines


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Check canonical polynomial witnesses exactly, without reading answer key."""
    if not isinstance(answer, list) or not answer:
        return False, "answer must be a nonempty list"
    components = inst.get("components")
    if not isinstance(components, list) or len(answer) != len(components):
        return False, "wrong number of factor matrices"

    directions = []
    for index, (matrix, component) in enumerate(zip(answer, components), 1):
        p = component["p"]
        if (not isinstance(matrix, list) or len(matrix) != 2
                or any(not isinstance(row, list) or len(row) != 3 for row in matrix)):
            return False, f"factor {index}: matrix must have shape 2 by 3"
        flat = [entry for row in matrix for entry in row]
        if any(isinstance(entry, bool) or not isinstance(entry, int)
               or not 0 <= entry < p for entry in flat):
            return False, f"factor {index}: coefficient outside 0..p-1"
        q = (matrix[0][0], matrix[1][0])
        linear = (matrix[0][1], matrix[1][1])
        constant = (matrix[0][2], matrix[1][2])
        if _normalize_line(q, p) != q:
            return False, f"factor {index}: quadratic column is not normalized"
        if _det(q, linear, p) == 0:
            return False, f"factor {index}: quadratic and linear columns are dependent"
        if linear != _canonical_l(q):
            return False, f"factor {index}: linear column is not canonical"
        if constant != (0, 0):
            return False, f"factor {index}: constant column must be zero"
        directions.append(q)

    try:
        missing = _instance_missing_lines(inst)
    except (ValueError, KeyError, TypeError) as exc:
        return False, f"invalid instance: {exc}"
    for index, (q, source_line, component) in enumerate(
            zip(directions, missing, components), 1):
        target = _normalize_line(_perp(source_line, component["p"]), component["p"])
        if q != target:
            return False, f"factor {index}: quadratic direction is not formally dual"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random):
    """Sample uniformly from canonical matrices, one projective line per factor."""
    out = []
    for component in inst["components"]:
        p = component["p"]
        choice = rng.randrange(p + 1)
        q = (0, 1) if choice == 0 else (1, choice - 1)
        out.append(_matrix_for_direction(q))
    return out


def search_space(inst: dict) -> int:
    return math.prod(component["p"] + 1 for component in inst["components"])


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space > 50_000:
        return None
    total = 0
    ranges = [range(component["p"] + 1) for component in inst["components"]]
    for choices in itertools.product(*ranges):
        candidate = []
        for choice, component in zip(choices, inst["components"]):
            q = (0, 1) if choice == 0 else (1, choice - 1)
            candidate.append(_matrix_for_direction(q))
        total += int(verify(inst, candidate)[0])
    return total


def canonical_key(inst: dict) -> str:
    """Exact affine-isomorphism key for this factorised generated family."""
    moduli = sorted(component["p"] for component in inst["components"])
    return json.dumps({"gauss_product_prime_multiset": moduli}, separators=(",", ":"))


def escalate(params: dict) -> dict:
    harder = dict(params)
    harder.pop("_preset", None)
    harder["n"] = int(harder["n"] * 3 // 2) + 1
    harder["prime_pool"] = max(32, int(harder.get("prime_pool", 32)))
    return harder


def _solve_by_conics(inst: dict, counter: list[int] | None = None):
    answer = []
    for component in inst["components"]:
        source = _missing_direction_conic(component, counter)
        target = _normalize_line(_perp(source, component["p"]), component["p"])
        assert target is not None
        answer.append(_matrix_for_direction(target))
    return answer


def _solve_by_difference_histogram(inst: dict,
                                   counter: list[int] | None = None):
    answer = []
    for component in inst["components"]:
        p = component["p"]
        points = component["points"]
        inverses = [0] * p
        if p > 1:
            inverses[1] = 1
        for value in range(2, p):
            inverses[value] = (p - (p // value) * inverses[p % value] % p) % p
        seen = [False] * (p + 1)
        for i, first in enumerate(points):
            for j, second in enumerate(points):
                if i == j:
                    continue
                dx = (first[0] - second[0]) % p
                dy = (first[1] - second[1]) % p
                direction = 0 if dx == 0 else 1 + dy * inverses[dx] % p
                seen[direction] = True
                if counter is not None:
                    counter[0] += 1
        absent = [index for index, present in enumerate(seen) if not present]
        if len(absent) != 1:
            return None
        source = (0, 1) if absent[0] == 0 else (1, absent[0] - 1)
        target = _normalize_line(_perp(source, p), p)
        assert target is not None
        answer.append(_matrix_for_direction(target))
    return answer


def _candidate_from_source_guesses(inst: dict,
                                   guesses: list[tuple[int, int]]):
    out = []
    for guess, component in zip(guesses, inst["components"]):
        p = component["p"]
        line = _normalize_line(guess, p) or (1, 0)
        target = _normalize_line(_perp(line, p), p)
        assert target is not None
        out.append(_matrix_for_direction(target))
    return out


def _attack_coordinate_outlier(inst: dict, counter: list[int] | None = None):
    guesses = []
    for component in inst["components"]:
        point = max(component["points"], key=lambda v: (v[0] + v[1], v[0], v[1]))
        guesses.append(tuple(point))
        if counter is not None:
            counter[0] += len(component["points"])
    return _candidate_from_source_guesses(inst, guesses)


def _attack_greedy_prefix(inst: dict, counter: list[int] | None = None):
    guesses = []
    for component in inst["components"]:
        p = component["p"]
        prefix = component["points"][:8]
        seen = set()
        for i in range(len(prefix)):
            for j in range(i):
                diff = ((prefix[i][0] - prefix[j][0]) % p,
                        (prefix[i][1] - prefix[j][1]) % p)
                line = _normalize_line(diff, p)
                if line is not None:
                    seen.add(line)
                if counter is not None:
                    counter[0] += 1
        choices = [(0, 1)] + [(1, slope) for slope in range(p)]
        guesses.append(next(line for line in choices if line not in seen))
    return _candidate_from_source_guesses(inst, guesses)


def _attack_three_point_second_difference(inst: dict,
                                          counter: list[int] | None = None):
    guesses = []
    for component in inst["components"]:
        p = component["p"]
        a, b, c = component["points"][:3]
        guess = ((a[0] - 2 * b[0] + c[0]) % p,
                 (a[1] - 2 * b[1] + c[1]) % p)
        guesses.append(guess)
        if counter is not None:
            counter[0] += 8
    return _candidate_from_source_guesses(inst, guesses)


def _random_restart(inst: dict, rng: random.Random, attempts: int) -> tuple[bool, int]:
    for trial in range(1, attempts + 1):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True, trial
    return False, attempts


def _answer_measure(inst: dict) -> tuple[int, int, int]:
    blob = json.dumps(inst["answer"], separators=(",", ":"))
    atoms = sum(len(row) for matrix in inst["answer"] for row in matrix)
    return len(blob), (len(blob) + 3) // 4, atoms


def _inverse_transpose_apply(matrix: tuple[tuple[int, int], tuple[int, int]],
                             vector: tuple[int, int], p: int) -> tuple[int, int]:
    (a, b), (c, d) = matrix
    inv_det = pow((a * d - b * c) % p, -1, p)
    return ((d * vector[0] - c * vector[1]) * inv_det % p,
            (-b * vector[0] + a * vector[1]) * inv_det % p)


def _transformed(inst: dict, rng: random.Random, *, shuffle_points: bool = False,
                 translate: bool = False, linear: bool = False,
                 reorder_factors: bool = False) -> dict:
    components = []
    answers = []
    for component, old_matrix in zip(inst["components"], inst["answer"]):
        p = component["p"]
        if linear:
            while True:
                affine = ((rng.randrange(p), rng.randrange(p)),
                          (rng.randrange(p), rng.randrange(p)))
                if _det(affine[0], affine[1], p):
                    break
        else:
            affine = ((1, 0), (0, 1))
        shift = (rng.randrange(p), rng.randrange(p)) if translate else (0, 0)
        new_points = []
        for x, y in component["points"]:
            new_points.append([
                (affine[0][0] * x + affine[0][1] * y + shift[0]) % p,
                (affine[1][0] * x + affine[1][1] * y + shift[1]) % p,
            ])
        if shuffle_points:
            rng.shuffle(new_points)
        components.append({"p": p, "points": new_points})

        old_q = (old_matrix[0][0], old_matrix[1][0])
        new_q = _normalize_line(_inverse_transpose_apply(affine, old_q, p), p)
        assert new_q is not None
        answers.append(_matrix_for_direction(new_q))
    if reorder_factors:
        order = list(range(len(components)))
        rng.shuffle(order)
        if len(order) > 1 and order == list(range(len(order))):
            order.reverse()
        components = [components[i] for i in order]
        answers = [answers[i] for i in order]
    return {
        "n": inst["n"], "factors": inst["factors"],
        "prime_pool": inst["prime_pool"], "components": components,
        "answer": answers,
    }


def selftest() -> dict:
    """Run all mandatory gates and return JSON-native measurements."""
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    verified = json_roundtrips = compact_verified = 0
    total = 0
    compact_max_ops = 0
    for params in DIFFICULTY.values():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            total += 1
            verified += int(verify(inst, inst["answer"])[0])
            counter = [0]
            compact = _solve_by_conics(inst, counter)
            compact_max_ops = max(compact_max_ops, counter[0])
            compact_verified += int(verify(inst, compact)[0])
            json_roundtrips += int(json.loads(json.dumps(inst["answer"])) == inst["answer"])
    report["G1_planted_verifies"] = {
        "pass": verified == compact_verified == json_roundtrips == total,
        "verified": verified, "attempts": total,
        "compact_route_verified": compact_verified,
        "json_roundtrips": json_roundtrips,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=9137, **ship_params)
    original = ship["answer"]
    first_p = ship["components"][0]["p"]
    target_q = (original[0][0][0], original[0][1][0])
    wrong_q = (0, 1) if target_q != (0, 1) else (1, 0)
    corruptions = {
        "empty": [],
        "drop_one_factor": original[:-1],
        "swap_quadratic_direction": [_matrix_for_direction(wrong_q)] + original[1:],
        "duplicate_columns": [[[1, 2, 0], [0, 0, 0]]] + original[1:],
        "out_of_range": [[[first_p, original[0][0][1], 0], original[0][1]]] + original[1:],
    }
    corruption_rows = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(ship, candidate)
        corruption_rows[name] = {"rejected": not ok, "reason": reason}
    distinct_reasons = len({row["reason"] for row in corruption_rows.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in corruption_rows.values())
                and distinct_reasons == len(corruption_rows),
        "corruptions": corruption_rows,
        "distinct_reasons": distinct_reasons,
    }

    encoded = json.dumps(original, separators=(",", ":"))
    prose = "I found the normalized maps.\n```json\n" + encoded + "\n```\nThese are exact."
    tagged = "Reasoning above. <answer>\n" + encoded + "\n</answer>"
    parsed = [parse_answer(prose), parse_answer(tagged)]
    report["G3_round_trip"] = {
        "pass": parsed == [original, original],
        "model_style_cases": 2,
        "recovered": sum(value == original for value in parsed),
    }

    guess_rng = random.Random(0x13066796)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    density = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6,
        "hits": guess_hits, "total": guess_total,
        "empirical_probability": density,
        "exact_probability": 1.0 / search_space(ship),
        "certificate_language_size": search_space(ship),
        "structure_aware": True,
    }

    baseline_rng = random.Random(0xBAD5EED)
    baseline_start = time.perf_counter()
    baseline_success, baseline_trials = _random_restart(ship, baseline_rng, 4096)
    baseline_wall = time.perf_counter() - baseline_start
    ref_counter = [0]
    ref_start = time.perf_counter()
    ref_answer = _solve_by_difference_histogram(ship, ref_counter)
    ref_wall = time.perf_counter() - ref_start
    report["G5_density_and_baseline"] = {
        "pass": density < 1e-6 and not baseline_success
                and ref_answer is not None and verify(ship, ref_answer)[0],
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_estimate": density,
        "shipping_exact_solution_count": 1,
        "shipping_exact_density": 1.0 / search_space(ship),
        "demo_exact_solution_count": enumerate_all(
            make_instance(seed=0, **DIFFICULTY["demo"])),
        "strongest_failing_attack_wall_seconds": round(baseline_wall, 6),
        "strongest_failing_attack_iterations": baseline_trials,
        "reference_wall_seconds": round(ref_wall, 6),
        "reference_pair_difference_operations": ref_counter[0],
    }

    attacks = {
        "coordinate_outlier": {"successes": 0, "attempts": 0, "operations": 0},
        "greedy_prefix_missing_direction": {"successes": 0, "attempts": 0, "operations": 0},
        "random_restart_256": {"successes": 0, "attempts": 0, "candidates": 0},
        "by_hand_three_point_second_difference": {"successes": 0, "attempts": 0,
                                                   "operations": 0},
    }
    ref_successes = ref_operations = 0
    ref_wall_total = 0.0
    for seed in range(100, 108):
        inst = make_instance(seed=seed, **ship_params)
        for name, attack in (
                ("coordinate_outlier", _attack_coordinate_outlier),
                ("greedy_prefix_missing_direction", _attack_greedy_prefix),
                ("by_hand_three_point_second_difference",
                 _attack_three_point_second_difference)):
            counter = [0]
            candidate = attack(inst, counter)
            attacks[name]["attempts"] += 1
            attacks[name]["operations"] += counter[0]
            attacks[name]["successes"] += int(verify(inst, candidate)[0])
        restart_rng = random.Random(seed ^ 0x51A7)
        success, used = _random_restart(inst, restart_rng, 256)
        attacks["random_restart_256"]["attempts"] += 1
        attacks["random_restart_256"]["candidates"] += used
        attacks["random_restart_256"]["successes"] += int(success)

        counter = [0]
        started = time.perf_counter()
        reference = _solve_by_difference_histogram(inst, counter)
        ref_wall_total += time.perf_counter() - started
        ref_operations += counter[0]
        ref_successes += int(reference is not None and verify(inst, reference)[0])
    all_failed = all(row["successes"] == 0 and row["attempts"] >= 8
                     for row in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "complete ordered-difference direction histogram",
            "complexity": "O(sum p_i^2) finite-field operations",
            "wall_clock_sec_total_8": round(ref_wall_total, 6),
            "wall_clock_sec_mean": round(ref_wall_total / 8, 6),
            "operations_total_8": ref_operations,
            "operations_mean": ref_operations // 8,
            "solves": f"{ref_successes}/8, as expected",
        },
    }

    doubled = make_instance(n=2 * ship_params["n"], seed=404,
                            factors=ship_params["factors"],
                            prime_pool=ship_params["prime_pool"])
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * ship_params["n"]
                and _answer_measure(doubled)[2] == _answer_measure(ship)[2],
        "shipping_n_lower_bound": ship_params["n"],
        "doubled_n_lower_bound": doubled["n"],
        "shipping_pair_cost": sum(c["p"] * (c["p"] - 1)
                                  for c in ship["components"]),
        "doubled_pair_cost": sum(c["p"] * (c["p"] - 1)
                                 for c in doubled["components"]),
        "answer_elements_fixed": _answer_measure(doubled)[2],
        "doubled_plant_verifies": doubled_ok,
    }

    invariance = carried = total_transforms = 0
    keys = []
    for seed in range(20):
        inst = make_instance(seed=2000 + seed, **ship_params)
        key = canonical_key(inst)
        keys.append(key)
        variants = [
            _transformed(inst, random.Random(seed * 10 + 1), shuffle_points=True),
            _transformed(inst, random.Random(seed * 10 + 2), translate=True),
            _transformed(inst, random.Random(seed * 10 + 3), linear=True),
            _transformed(inst, random.Random(seed * 10 + 4), reorder_factors=True),
            _transformed(inst, random.Random(seed * 10 + 5), shuffle_points=True,
                         translate=True, linear=True, reorder_factors=True),
        ]
        for changed in variants:
            total_transforms += 1
            invariance += int(canonical_key(changed) == key)
            carried += int(verify(changed, changed["answer"])[0])
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": invariance == carried == total_transforms and distinct == 20,
        "invariance_checks_passed": invariance,
        "invariance_checks_total": total_transforms,
        "carried_witness_checks_passed": carried,
        "carried_witness_checks_total": total_transforms,
        "unrelated_distinct": distinct,
        "unrelated_total": 20,
        "transformations": ["point reorder", "translation", "GL(2,p)",
                            "factor reorder", "composition of all four"],
    }

    answer_chars = answer_tokens = answer_elements = 0
    intended_max = 0
    intended_verified = True
    for seed in range(20):
        inst = make_instance(seed=3000 + seed, **ship_params)
        chars, tokens, elements = _answer_measure(inst)
        answer_chars = max(answer_chars, chars)
        answer_tokens = max(answer_tokens, tokens)
        answer_elements = max(answer_elements, elements)
        counter = [0]
        candidate = _solve_by_conics(inst, counter)
        intended_max = max(intended_max, counter[0])
        intended_verified &= verify(inst, candidate)[0]
    arms = {name: dict(G9_EVIDENCE[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else None)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else None)
    hint_delta = (hinted_rate - placebo_rate
                  if hinted_rate is not None and placebo_rate is not None else None)
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_max <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": G9_EVIDENCE["hinted_verdict"] == "hardened"
                and within_caps and intended_verified,
        "arms": arms,
        "hinted_minus_placebo": hint_delta,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_max,
    }

    report["all_passed"] = all(
        value.get("pass", False) for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
