"""Verified problem generator for arXiv:1612.00719.

The paper studies simultaneous diagonal quadratic and cubic equations over the
integers. This module chooses a signed-permutation solution first and builds
one quadratic and two cubic forms around it. The quadratic form is a strict
rearrangement inequality. The cubic columns are signed images, under a common
invertible 2-by-2 map, of a telescoping family. Generation never solves the
instance whose witness it returns.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time
from functools import cmp_to_key
from typing import Callable


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "number_theory",
    "object_regime": "integer_lattice",
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "one highly nonsingular quadratic diagonal form over Z",
        "two highly nonsingular cubic diagonal forms over Z",
        "bounded integral vector",
    ],
    "verification_operations": [
        "exact integer exponentiation",
        "exact integer multiplication",
        "exact integer summation",
        "signed-permutation comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Rearrangement equality fixes the magnitude permutation, while pairwise "
        "determinant signs cancel a hidden common 2-by-2 transform and recover "
        "the signs; without that invariant one meets a two-dimensional signed "
        "subset-sum search."
    ),
    "hardness_basis": (
        "In Theorem 1.1's regime r2=1, r3=2, s=n>=17, the reference "
        "meet-in-the-middle signed-subset-sum algorithm takes "
        "O(n log n + 2^((n-1)/2)) time and O(2^((n-1)/2)) memory; at the "
        "shipping n=35 an eight-instance run enumerates 2097152 sign states and "
        "performs 9405614 exact integer additions/subtractions in 3.293 seconds, "
        "whereas the determinant-invariant route uses 245 exact operations."
    ),
    "max_answer_tokens": 42,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 17, "gap_bits": 2, "transform_bits": 2, "demo_pattern": False},
    "easy": {"n": 25, "gap_bits": 10, "transform_bits": 10},
    "medium": {"n": 31, "gap_bits": 16, "transform_bits": 16},
    "hard": {"n": 35, "gap_bits": 22, "transform_bits": 22},
}

SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A length-n signed permutation of 1,...,n satisfying the quadratic "
        "form, whose strict rearrangement equality fixes all magnitudes; the "
        "remaining bounded language has one free sign per coordinate except "
        "that coordinate 0 is positive."
    ),
    "bounds": {
        "max_length": 256,
        "min_magnitude": 1,
        "max_magnitude": 256,
        "signs": 2,
        "coordinate_zero_positive": True,
        "magnitudes_satisfy_quadratic": True,
    },
}

STRUCTURAL_HINT = (
    "The quadratic row is a rearrangement equality, and determinant signs of "
    "the cubic columns preserve a common hidden linear-image invariant."
)

PLACEBO_HINT = (
    "This problem rewards careful bookkeeping of every coordinate, coefficient, "
    "sign, and index throughout all the exact integer calculations."
)

G9_ARMS = {
    "bare": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted": {"solved": 0, "attempts": 0, "errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "errors": 4},
}

NOTES = """
Section 1, equation (1.1), and Theorem 1.1 fix the native objects and the
regime r3 >= 2 r2 > 0 with s >= 6 r3 + floor(14 r2/3) + 1. Section 4 is the
decisive easy/existence qualification: the asymptotic constant may vanish, and
positivity additionally requires nonsingular real and p-adic points. The
planted integral point is checked to have a rank-three Jacobian, so it supplies
those local points directly; the paper's circle-method proof is not a search
algorithm.

Generation is inverse and compositional. The signed permutation is sampled
first. A rearrangement-equality quadratic row has that magnitude assignment as
its unique zero. The two cubic rows are a common invertible image of weighted
points whose last vector cancels the preceding vectors exactly. Multiplying a
cubic column by the planted coordinate sign carries the identity through
because s*s^3=1.

The reference algorithm first sorts the quadratic row and then runs the
standard meet-in-the-middle algorithm for two-dimensional signed subset sum.
The intended compact route instead reads the arithmetic progression in the
quadratic row and uses signs of 2-by-2 determinants: the common row transform
contributes one global determinant sign, and all planted column signs cancel
pairwise. Per-column sign guesses, residual-greedy assignment, random local
restart, and direct all-positive/alternating ansatzes are the failing attacks.
There are no special planted coordinates versus decoys: every coordinate
participates in the witness and is transformed identically.
""".strip()


def _det2(u: tuple[int, int] | list[int], v: tuple[int, int] | list[int]) -> int:
    return u[0] * v[1] - u[1] * v[0]


def _rank_at_least_three(rows: list[list[int]]) -> bool:
    if len(rows) != 3 or not rows or len(rows[0]) < 3:
        return False
    a, b, c = rows
    size = len(a)
    for i in range(size - 2):
        for j in range(i + 1, size - 1):
            for k in range(j + 1, size):
                value = (
                    a[i] * (b[j] * c[k] - b[k] * c[j])
                    - a[j] * (b[i] * c[k] - b[k] * c[i])
                    + a[k] * (b[i] * c[j] - b[j] * c[i])
                )
                if value:
                    return True
    return False


def _cubic_highly_nonsingular(rows: list[list[int]]) -> bool:
    a, b = rows
    return all(
        a[i] * b[j] - a[j] * b[i] != 0
        for i in range(len(a))
        for j in range(i + 1, len(a))
    )


def _valid_paper_hypotheses(
    quadratic: list[int], cubics: list[list[int]], witness: list[int]
) -> bool:
    if any(value == 0 for value in quadratic):
        return False
    if not _cubic_highly_nonsingular(cubics):
        return False
    jacobian = [
        [2 * quadratic[i] * witness[i] for i in range(len(witness))],
        [3 * cubics[0][i] * witness[i] ** 2 for i in range(len(witness))],
        [3 * cubics[1][i] * witness[i] ** 2 for i in range(len(witness))],
    ]
    return _rank_at_least_three(jacobian)


def _random_positive_det_matrix(rng: random.Random, bits: int) -> list[list[int]]:
    lo = 1 << max(0, bits - 1)
    hi = 1 << bits
    while True:
        values = [
            rng.randrange(lo, hi) * (-1 if rng.randrange(2) else 1)
            for _ in range(4)
        ]
        matrix = [values[:2], values[2:]]
        determinant = values[0] * values[3] - values[1] * values[2]
        if determinant == 0:
            continue
        if determinant < 0:
            matrix[0], matrix[1] = matrix[1], matrix[0]
        return matrix


def _matvec(matrix: list[list[int]], vector: tuple[int, int]) -> tuple[int, int]:
    return (
        matrix[0][0] * vector[0] + matrix[0][1] * vector[1],
        matrix[1][0] * vector[0] + matrix[1][1] * vector[1],
    )


def _base_cubic_columns(n: int, t_values: list[int]) -> list[tuple[int, int]]:
    """Simple one-closing-vector construction used only by the readable demo."""

    scale = n**3
    columns = [(scale, scale * t) for t in t_values]
    sum_cubes = sum(m**3 for m in range(1, n))
    weighted_t = sum(m**3 * t_values[m - 1] for m in range(1, n))
    columns.append((-sum_cubes, -weighted_t))
    return columns


def _zero_sum_components(n: int, rng: random.Random, bits: int) -> list[int]:
    """Generate n nonzero integer components whose sum is zero."""

    ceiling = max(4 * n, 1 << bits)
    coordinates = sorted(rng.sample(range(ceiling), n))
    low = high = coordinates[0]
    components = []
    for value in coordinates[1:-1]:
        if rng.randrange(2):
            components.append(value - high)
            high = value
        else:
            components.append(low - value)
            low = value
    components.extend((coordinates[-1] - high, low - coordinates[-1]))
    assert len(components) == n and sum(components) == 0
    return components


def _angle_compare(u: tuple[int, int], v: tuple[int, int]) -> int:
    upper_u = u[1] > 0 or (u[1] == 0 and u[0] > 0)
    upper_v = v[1] > 0 or (v[1] == 0 and v[0] > 0)
    if upper_u != upper_v:
        return -1 if upper_u else 1
    determinant = _det2(u, v)
    if determinant:
        return -1 if determinant > 0 else 1
    return 0


def _random_convex_edges(
    n: int, rng: random.Random, bits: int
) -> list[tuple[int, int]]:
    """Balanced integer polygon edges in strict counterclockwise order."""

    for _ in range(256):
        xs = _zero_sum_components(n, rng, bits)
        ys = _zero_sum_components(n, rng, bits)
        rng.shuffle(ys)
        edges = sorted(zip(xs, ys), key=cmp_to_key(_angle_compare))
        if any(
            _det2(edges[i], edges[j]) == 0
            for i in range(n)
            for j in range(i + 1, n)
        ):
            continue
        if any(_det2(edges[i], edges[(i + 1) % n]) <= 0 for i in range(n)):
            continue
        assert sum(x for x, _ in edges) == 0
        assert sum(y for _, y in edges) == 0
        return edges
    raise RuntimeError("could not sample a strict convex integer edge cycle")


def _balanced_base_columns(n: int, edges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Scale polygon edges so m^3*b_m has one common positive factor."""

    common = 1
    for magnitude in range(1, n + 1):
        common = math.lcm(common, magnitude)
    common **= 3
    return [
        (
            (common // magnitude**3) * edge[0],
            (common // magnitude**3) * edge[1],
        )
        for magnitude, edge in enumerate(edges, 1)
    ]


def make_instance(
    n: int,
    seed: int = 0,
    gap_bits: int = 16,
    transform_bits: int = 16,
    demo_pattern: bool = False,
    **params: object,
) -> dict:
    """Build a native diagonal system around a preselected integral point."""

    del params
    if isinstance(n, bool) or not isinstance(n, int) or n < 17:
        raise ValueError("n must be an integer at least 17 (Theorem 1.1 regime)")
    if n > 256:
        raise ValueError("n exceeds the 256-atom certificate-language bound")
    if not (2 <= gap_bits <= 60 and 2 <= transform_bits <= 60):
        raise ValueError("gap_bits and transform_bits must lie in 2..60")

    rng = random.Random(seed)
    if demo_pattern:
        magnitudes = list(range(1, n + 1))
        signs = [1] * n
    else:
        magnitudes = list(range(1, n + 1))
        rng.shuffle(magnitudes)
        signs = [1 if i == 0 or not rng.randrange(2) else -1 for i in range(n)]
    witness = [sign * magnitude for sign, magnitude in zip(signs, magnitudes)]

    sum_squares = sum(m * m for m in range(1, n + 1))
    minimum_dot = sum(rank * (n + 1 - rank) ** 2 for rank in range(1, n + 1))
    q_scale = 1 if demo_pattern else rng.randrange(1 << (gap_bits - 1), 1 << gap_bits)
    quadratic = [
        q_scale * (sum_squares * (n + 1 - magnitude) - minimum_dot)
        for magnitude in magnitudes
    ]

    # Only coefficient structure is resampled; the witness remains fixed.
    for construction_attempt in range(1, 129):
        if demo_pattern:
            t_values = list(range(1, n))
            transform = [[1, 0], [0, 1]]
            base_columns = _base_cubic_columns(n, t_values)
        else:
            edges = _random_convex_edges(n, rng, gap_bits)
            base_columns = _balanced_base_columns(n, edges)
            transform = _random_positive_det_matrix(rng, transform_bits)
        if any(
            _det2(base_columns[i], base_columns[j]) == 0
            for i in range(n)
            for j in range(i + 1, n)
        ):
            if demo_pattern:
                raise RuntimeError("demo base columns unexpectedly collide")
            continue

        cubics = [[0] * n, [0] * n]
        for coordinate, (magnitude, sign) in enumerate(zip(magnitudes, signs)):
            image = _matvec(transform, base_columns[magnitude - 1])
            cubics[0][coordinate] = sign * image[0]
            cubics[1][coordinate] = sign * image[1]
        if _valid_paper_hypotheses(quadratic, cubics, witness):
            break
        if demo_pattern:
            raise RuntimeError("demo construction is unexpectedly singular")
    else:
        raise RuntimeError("could not sample nonsingular diagonal coefficient rows")

    return {
        "paper": "arXiv:1612.00719",
        "family": "signed-permutation point on one quadratic and two cubic diagonal forms",
        "n": n,
        "r2": 1,
        "r3": 2,
        "bound": n,
        "gap_bits": gap_bits,
        "transform_bits": transform_bits,
        "demo_pattern": bool(demo_pattern),
        "quadratic": quadratic,
        "cubics": cubics,
        "construction_attempt": construction_attempt,
        "answer": witness,
    }


def render(inst: dict) -> str:
    n = inst["n"]
    lines = [
        "Find a bounded nonzero integral solution of simultaneous diagonal equations.",
        "",
        "Definitions and constraints.",
        f"There are {n} integer variables x_0,...,x_{n - 1}; indices are 0-based.",
        f"Your answer must contain exactly {n} integers.",
        f"Their absolute values must be exactly 1,2,...,{n}, each used once.",
        "Signs are free except that x_0 must be positive; this removes global sign ambiguity.",
        "For a coefficient row a, its degree-d diagonal form is sum_i a_i*x_i^d.",
        "All sums and powers are over the ordinary integers, with no modulus.",
        "A valid answer makes the following one quadratic and two cubic forms exactly zero.",
        "",
        "Quadratic row Q (degree 2):",
        " ".join(map(str, inst["quadratic"])),
        "",
        "Cubic row C1 (degree 3):",
        " ".join(map(str, inst["cubics"][0])),
        "",
        "Cubic row C2 (degree 3):",
        " ".join(map(str, inst["cubics"][1])),
        "",
        "Thus Q(x)=C1(x)=C2(x)=0 must hold exactly.",
        "Order matters: entry j is x_j, and repeated absolute values are forbidden.",
        "",
        "Give your final answer inside <answer></answer> tags, as a JSON-style list of integers.",
        "Example: <answer>[1, -3, 2]</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    if not isinstance(text, str):
        return None
    try:
        match = re.search(r"<answer>(.*?)</answer>", text, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:json|python|text)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
        if not body:
            return []
        if body.startswith("[") and body.endswith("]"):
            value = json.loads(body)
            if not isinstance(value, list):
                return None
            if not all(isinstance(x, int) and not isinstance(x, bool) for x in value):
                return None
            return value
        tokens = [token for token in re.split(r"[\s,]+", body) if token]
        if not tokens or not all(re.fullmatch(r"[+-]?\d+", token) for token in tokens):
            return None
        return [int(token) for token in tokens]
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    n = inst["n"]
    if not isinstance(answer, list) or not all(
        isinstance(x, int) and not isinstance(x, bool) for x in answer
    ):
        return False, "malformed: expected a list containing only integers"
    if not answer:
        return False, "empty answer: expected a nonzero signed permutation"
    if len(answer) < n:
        return False, f"wrong length: too few entries ({len(answer)} instead of {n})"
    if len(answer) > n:
        return False, f"wrong length: too many entries ({len(answer)} instead of {n})"
    magnitudes = [abs(x) for x in answer]
    outside = [m for m in magnitudes if m < 1 or m > n]
    if outside:
        return False, f"magnitude out of range: {outside[0]} is not in 1..{n}"
    if len(set(magnitudes)) != n:
        return False, "duplicate magnitude: absolute values must be a permutation of 1..n"
    if answer[0] <= 0:
        return False, "sign convention: x_0 must be positive"

    q_value = sum(c * x * x for c, x in zip(inst["quadratic"], answer))
    if q_value != 0:
        return False, f"quadratic residual is {q_value}, not zero"
    c1_value = sum(c * x * x * x for c, x in zip(inst["cubics"][0], answer))
    if c1_value != 0:
        return False, f"first cubic residual is {c1_value}, not zero"
    c2_value = sum(c * x * x * x for c, x in zip(inst["cubics"][1], answer))
    if c2_value != 0:
        return False, f"second cubic residual is {c2_value}, not zero"
    return True, "ok"


def _decode_magnitudes(inst: dict) -> list[int]:
    n = inst["n"]
    order = sorted(range(n), key=lambda i: inst["quadratic"][i])
    magnitudes = [0] * n
    for rank, coordinate in enumerate(order, 1):
        magnitudes[coordinate] = n + 1 - rank
    return magnitudes


def _compact_decode(inst: dict) -> list[int] | None:
    """The intended rearrangement-plus-determinant route, with no search."""

    n = inst["n"]
    q = inst["quadratic"]
    q_min, q_max = min(q), max(q)
    span = q_max - q_min
    if span <= 0 or span % (n - 1):
        return None
    step = span // (n - 1)
    magnitudes = []
    for value in q:
        offset = value - q_min
        if offset % step:
            return None
        rank = offset // step + 1
        magnitudes.append(n + 1 - rank)
    if sorted(magnitudes) != list(range(1, n + 1)):
        return None

    if inst.get("demo_pattern"):
        demo = magnitudes[:]
        return demo if verify(inst, demo)[0] else None
    if n % 2 == 0:
        return None

    coordinate = {magnitude: i for i, magnitude in enumerate(magnitudes)}
    points = list(zip(inst["cubics"][0], inst["cubics"][1]))
    cyclic_signs = []
    for magnitude in range(1, n + 1):
        i = coordinate[magnitude]
        j = coordinate[1 if magnitude == n else magnitude + 1]
        determinant = _det2(points[i], points[j])
        if determinant == 0:
            return None
        cyclic_signs.append(1 if determinant > 0 else -1)

    # Consecutive base edges have positive determinant. Around an odd cycle,
    # multiplying observed determinant signs cancels every planted sign twice
    # and leaves exactly sign(det M).
    det_transform_sign = math.prod(cyclic_signs)
    relative_by_magnitude = {1: 1}
    for magnitude in range(1, n):
        relative_by_magnitude[magnitude + 1] = (
            relative_by_magnitude[magnitude]
            * cyclic_signs[magnitude - 1]
            * det_transform_sign
        )
    relative = [relative_by_magnitude[magnitude] for magnitude in magnitudes]
    sign_at_magnitude_one = relative[0]
    answer = [magnitude * sign_at_magnitude_one * relative[i] for i, magnitude in enumerate(magnitudes)]
    return answer if verify(inst, answer)[0] else None


def random_candidate(inst: dict, rng: random.Random) -> object:
    # Q cheaply fixes magnitudes, so the structure-aware prior randomizes signs.
    candidate = _decode_magnitudes(inst)
    for i in range(1, len(candidate)):
        if rng.randrange(2):
            candidate[i] = -candidate[i]
    return candidate


def search_space(inst: dict) -> int | None:
    return 1 << (inst["n"] - 1)


def enumerate_all(inst: dict) -> int | None:
    n = inst["n"]
    if n > 22:
        return None
    magnitudes = _decode_magnitudes(inst)
    count = 0
    for mask in range(1 << (n - 1)):
        candidate = magnitudes[:]
        for i in range(1, n):
            if mask & (1 << (i - 1)):
                candidate[i] = -candidate[i]
        if verify(inst, candidate)[0]:
            count += 1
    return count


def _reduced_fraction(numerator: int, denominator: int) -> tuple[int, int]:
    if denominator == 0:
        raise ZeroDivisionError("projective invariant denominator is zero")
    if denominator < 0:
        numerator, denominator = -numerator, -denominator
    divisor = math.gcd(abs(numerator), denominator)
    return numerator // divisor, denominator // divisor


def _key_for_q_orientation(inst: dict, q_sign: int) -> str:
    n = inst["n"]
    q = inst["quadratic"]
    order = sorted(range(n), key=lambda i: q_sign * q[i])
    divisor = 0
    for value in q:
        divisor = math.gcd(divisor, abs(value))
    q_normal = [q_sign * q[i] // max(1, divisor) for i in order]
    points = [(inst["cubics"][0][i], inst["cubics"][1][i]) for i in order]
    a, b, c = points[:3]
    ac = _det2(a, c)
    bc = _det2(b, c)
    projective = []
    for point in points[3:]:
        numerator = ac * _det2(b, point)
        denominator = _det2(a, point) * bc
        projective.append(_reduced_fraction(numerator, denominator))
    determinant_gcd = 0
    determinant_magnitudes = []
    for i in range(n):
        for j in range(i + 1, n):
            value = abs(_det2(points[i], points[j]))
            determinant_magnitudes.append(value)
            determinant_gcd = math.gcd(determinant_gcd, value)
    determinant_magnitudes = [
        value // max(1, determinant_gcd) for value in determinant_magnitudes
    ]
    return json.dumps(
        [q_normal, projective, determinant_magnitudes], separators=(",", ":")
    )


def canonical_key(inst: dict) -> str:
    """Invariant under variable relabelling/signs and equation-basis changes."""

    payload = min(_key_for_q_orientation(inst, 1), _key_for_q_orientation(inst, -1))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    harder = {k: v for k, v in params.items() if k != "_preset"}
    harder.pop("demo_pattern", None)
    n = int(harder.get("n", 25))
    gap_bits = int(harder.get("gap_bits", 10))
    transform_bits = int(harder.get("transform_bits", 10))
    if max(gap_bits, transform_bits) < 30:
        harder["gap_bits"] = min(30, gap_bits + 4)
        harder["transform_bits"] = min(30, transform_bits + 4)
        return harder
    if n + 4 <= 256 and 7 * (n + 4) <= 300:
        harder["n"] = n + 4
        harder["gap_bits"] = min(40, gap_bits + 2)
        harder["transform_bits"] = min(40, transform_bits + 2)
        return harder
    return "cap_bound"


# ---------------------------------------------------------------------------
# Attacks and the Track B reference algorithm used by selftest.


def _cubic_terms(inst: dict, magnitudes: list[int]) -> list[tuple[int, int]]:
    return [
        (
            inst["cubics"][0][i] * magnitudes[i] ** 3,
            inst["cubics"][1][i] * magnitudes[i] ** 3,
        )
        for i in range(inst["n"])
    ]


def _candidate_from_signs(magnitudes: list[int], signs: list[int]) -> list[int]:
    candidate = [m * s for m, s in zip(magnitudes, signs)]
    if candidate[0] < 0:
        candidate = [-x for x in candidate]
    return candidate


def _attack_per_element(inst: dict, rng: random.Random) -> list[list[int]]:
    del rng
    magnitudes = _decode_magnitudes(inst)
    c1, c2 = inst["cubics"]
    rules = [
        [1 if x >= 0 else -1 for x in c1],
        [1 if x >= 0 else -1 for x in c2],
        [1 if x + y >= 0 else -1 for x, y in zip(c1, c2)],
        [1 if (x if abs(x) >= abs(y) else y) >= 0 else -1 for x, y in zip(c1, c2)],
    ]
    return [_candidate_from_signs(magnitudes, signs) for signs in rules]


def _attack_greedy(inst: dict, rng: random.Random) -> list[list[int]]:
    magnitudes = _decode_magnitudes(inst)
    terms = _cubic_terms(inst, magnitudes)
    candidates = []
    for trial in range(4):
        order = list(range(1, inst["n"]))
        if trial == 0:
            order.sort(key=lambda i: abs(terms[i][0]) + abs(terms[i][1]), reverse=True)
        else:
            rng.shuffle(order)
        signs = [1] * inst["n"]
        total = [terms[0][0], terms[0][1]]
        for i in order:
            plus = (total[0] + terms[i][0], total[1] + terms[i][1])
            minus = (total[0] - terms[i][0], total[1] - terms[i][1])
            if abs(minus[0]) + abs(minus[1]) < abs(plus[0]) + abs(plus[1]):
                signs[i] = -1
                total[:] = minus
            else:
                total[:] = plus
        candidates.append(_candidate_from_signs(magnitudes, signs))
    return candidates


def _attack_random_restart(
    inst: dict, rng: random.Random, restarts: int = 32, moves: int = 1600
) -> list[list[int]]:
    magnitudes = _decode_magnitudes(inst)
    terms = _cubic_terms(inst, magnitudes)
    scales = [max(1, sum(abs(term[h]) for term in terms)) for h in range(2)]
    best = []
    for _ in range(restarts):
        signs = [1] + [(-1 if rng.randrange(2) else 1) for _ in range(1, inst["n"])]
        sums = [sum(signs[i] * terms[i][h] for i in range(inst["n"])) for h in range(2)]
        score = abs(sums[0]) / scales[0] + abs(sums[1]) / scales[1]
        for _ in range(moves):
            i = rng.randrange(1, inst["n"])
            proposal = [sums[h] - 2 * signs[i] * terms[i][h] for h in range(2)]
            proposal_score = abs(proposal[0]) / scales[0] + abs(proposal[1]) / scales[1]
            if proposal_score < score:
                signs[i] = -signs[i]
                sums, score = proposal, proposal_score
            if sums == [0, 0]:
                candidate = _candidate_from_signs(magnitudes, signs)
                if verify(inst, candidate)[0]:
                    return [candidate]
        best.append(_candidate_from_signs(magnitudes, signs))
    return best


def _attack_obvious_ansatz(inst: dict, rng: random.Random) -> list[list[int]]:
    del rng
    magnitudes = _decode_magnitudes(inst)
    n = inst["n"]
    coordinate_by_magnitude = {m: i for i, m in enumerate(magnitudes)}
    patterns = [
        [1] * n,
        [1 if magnitudes[i] % 2 else -1 for i in range(n)],
        [1 if inst["quadratic"][i] >= 0 else -1 for i in range(n)],
        [1] * n,
    ]
    patterns[-1][coordinate_by_magnitude[n]] = -1
    return [_candidate_from_signs(magnitudes, signs) for signs in patterns]


def _signed_sum_states(
    terms: list[tuple[int, int]], indices: list[int]
) -> tuple[list[tuple[int, int, int]], int]:
    states = [(0, 0, 0)]
    operations = 0
    for bit, index in enumerate(indices):
        a, b = terms[index]
        expanded = []
        for x, y, mask in states:
            expanded.append((x + a, y + b, mask | (1 << bit)))
            expanded.append((x - a, y - b, mask))
            operations += 4
        states = expanded
    return states, operations


def _reference_meet_in_middle(inst: dict) -> tuple[list[int] | None, dict]:
    magnitudes = _decode_magnitudes(inst)
    terms = _cubic_terms(inst, magnitudes)
    remaining = list(range(1, inst["n"]))
    midpoint = len(remaining) // 2
    left_indices = remaining[:midpoint]
    right_indices = remaining[midpoint:]
    left, operations_left = _signed_sum_states(terms, left_indices)
    right, operations_right = _signed_sum_states(terms, right_indices)
    lookup = {}
    for x, y, mask in left:
        lookup.setdefault((x, y), mask)
    target = (-terms[0][0], -terms[0][1])
    operations = operations_left + operations_right
    for x, y, right_mask in right:
        operations += 2
        left_mask = lookup.get((target[0] - x, target[1] - y))
        if left_mask is None:
            continue
        signs = [1] * inst["n"]
        for bit, index in enumerate(left_indices):
            signs[index] = 1 if left_mask & (1 << bit) else -1
        for bit, index in enumerate(right_indices):
            signs[index] = 1 if right_mask & (1 << bit) else -1
        candidate = _candidate_from_signs(magnitudes, signs)
        if verify(inst, candidate)[0]:
            return candidate, {
                "states": len(left) + len(right),
                "integer_add_subtract_operations": operations,
            }
    return None, {
        "states": len(left) + len(right),
        "integer_add_subtract_operations": operations,
    }


def _run_attack_panel(params: dict, seeds: list[int]) -> tuple[dict, dict]:
    attacks = {
        "per_element_coefficient_sign": {"successes": 0, "attempts": len(seeds)},
        "greedy_vector_residual": {"successes": 0, "attempts": len(seeds)},
        "random_restart_sign_flip_32x1600": {"successes": 0, "attempts": len(seeds)},
        "in_context_direct_ansatz": {"successes": 0, "attempts": len(seeds)},
    }
    built = [make_instance(seed=seed, **params) for seed in seeds]
    probes: list[tuple[str, Callable[[dict, random.Random], list[list[int]]]]] = [
        ("per_element_coefficient_sign", _attack_per_element),
        ("greedy_vector_residual", _attack_greedy),
        ("random_restart_sign_flip_32x1600", _attack_random_restart),
        ("in_context_direct_ansatz", _attack_obvious_ansatz),
    ]
    for name, attack in probes:
        for seed, inst in zip(seeds, built):
            candidates = attack(inst, random.Random(100_000 + seed))
            if any(verify(inst, candidate)[0] for candidate in candidates):
                attacks[name]["successes"] += 1

    started = time.perf_counter()
    successes = 0
    states = 0
    operations = 0
    for inst in built:
        candidate, cost = _reference_meet_in_middle(inst)
        states += cost["states"]
        operations += cost["integer_add_subtract_operations"]
        if candidate is not None and verify(inst, candidate)[0]:
            successes += 1
    wall = time.perf_counter() - started
    reference = {
        "name": "quadratic rank sort plus meet-in-the-middle 2D signed subset sum",
        "complexity": "O(n log n + 2^((n-1)/2)) time and O(2^((n-1)/2)) memory",
        "wall_clock_sec": round(wall, 6),
        "states": states,
        "integer_add_subtract_operations": operations,
        "attempts": len(seeds),
        "successes": successes,
        "solves": f"{successes}/{len(seeds)}, as expected",
    }
    return attacks, reference


def _corruption_results(inst: dict) -> dict[str, str]:
    planted = list(inst["answer"])
    swapped = planted[:]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    swapped[0] = abs(swapped[0])
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": swapped,
        "duplicate": planted[:-1] + [abs(planted[0])],
        "empty": [],
        "out_of_range": [inst["n"] + 1] + planted[1:],
    }
    reasons = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        reasons[name] = "ACCEPTED" if ok else reason
    return reasons


def _transform_instance(inst: dict, rng: random.Random) -> tuple[dict, list[int]]:
    n = inst["n"]
    permutation = list(range(n))
    rng.shuffle(permutation)
    coordinate_signs = [(-1 if rng.randrange(2) else 1) for _ in range(n)]
    transformed = dict(inst)
    transformed["quadratic"] = [-3 * inst["quadratic"][i] for i in permutation]
    permuted_cubics = [
        [coordinate_signs[j] * row[i] for j, i in enumerate(permutation)]
        for row in inst["cubics"]
    ]
    transformed["cubics"] = [
        [2 * x + y for x, y in zip(permuted_cubics[0], permuted_cubics[1])],
        [x + y for x, y in zip(permuted_cubics[0], permuted_cubics[1])],
    ]
    answer = [coordinate_signs[j] * inst["answer"][i] for j, i in enumerate(permutation)]
    if answer[0] < 0:
        answer = [-x for x in answer]
    transformed["answer"] = answer
    return transformed, answer


def _canonical_gate(params: dict) -> dict:
    invariance_checks = 0
    carried_witness_checks = 0
    keys = []
    for seed in range(20):
        inst = make_instance(seed=seed + 7000, **params)
        base = canonical_key(inst)
        keys.append(base)
        for offset in range(3):
            transformed, answer = _transform_instance(
                inst, random.Random(seed * 17 + offset)
            )
            invariance_checks += 1
            if canonical_key(transformed) != base:
                return {
                    "pass": False,
                    "invariance_checks": invariance_checks,
                    "carried_witness_checks": carried_witness_checks,
                    "distinct_keys": len(set(keys)),
                    "unrelated_instances": len(keys),
                }
            ok, _ = verify(transformed, answer)
            carried_witness_checks += 1
            if not ok:
                return {
                    "pass": False,
                    "invariance_checks": invariance_checks,
                    "carried_witness_checks": carried_witness_checks,
                    "distinct_keys": len(set(keys)),
                    "unrelated_instances": len(keys),
                }
    return {
        "pass": len(set(keys)) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_witness_checks,
        "distinct_keys": len(set(keys)),
        "unrelated_instances": 20,
        "transformations": [
            "variable permutation",
            "independent variable sign changes",
            "quadratic row scaling/sign",
            "GL(2,Z) cubic equation-basis change",
            "all transformations composed",
        ],
    }


def selftest() -> dict:
    report: dict[str, object] = {}
    seeds = [0, 1, 2, 3]

    checked = 0
    failures = []
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in seeds:
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            checked += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not failures and json_roundtrips == checked,
        "instances_checked": checked,
        "json_native_answers": json_roundtrips,
        "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=12345, **shipping)
    corruption = _corruption_results(inst)
    report["G2_rejects_corruption"] = {
        "pass": (
            all(not reason.startswith("ACCEPTED") for reason in corruption.values())
            and len(set(corruption.values())) == len(corruption)
        ),
        "reasons": corruption,
        "distinct_reasons": len(set(corruption.values())),
    }

    response = (
        "The exact checks agree.\n\n<answer>\n```json\n"
        + json.dumps(inst["answer"])
        + "\n```\n</answer>\nThat is my final witness."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"],
        "realistic_prose": True,
        "parsed_entries": len(parsed) if isinstance(parsed, list) else None,
    }

    rng = random.Random(99001)
    sample_total = 200_000
    sample_hits = 0
    for _ in range(sample_total):
        if verify(inst, random_candidate(inst, rng))[0]:
            sample_hits += 1
    density = sample_hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "observed_structure_aware_probability": density,
        "prior": "uniform signs after Q's rearrangement equality fixes magnitudes and x_0 positive",
        "search_space": search_space(inst),
    }

    attacks, reference = _run_attack_panel(shipping, list(range(8)))
    demo_inst = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    report["G5_density_and_baseline_cost"] = {
        "pass": density < 1e-6 and reference["successes"] == reference["attempts"],
        "shipping_n": inst["n"],
        "sample_hits": sample_hits,
        "sample_total": sample_total,
        "sampled_valid_fraction": density,
        "known_valid_answers_in_structure_aware_language": "at least 1",
        "demo_n": demo_inst["n"],
        "demo_exact_solution_count_by_enumeration": demo_count,
        "baseline_wall_seconds": reference["wall_clock_sec"],
        "baseline_states": reference["states"],
        "baseline_integer_operations": reference["integer_add_subtract_operations"],
        "baseline_attempts": reference["attempts"],
        "baseline_successes": reference["successes"],
    }
    report["G6_adversary_panel"] = {
        "pass": (
            len(attacks) >= 4
            and all(result["successes"] == 0 for result in attacks.values())
            and reference["successes"] == reference["attempts"]
        ),
        "attacks": attacks,
        "reference_algorithm": reference,
    }

    doubled_params = dict(shipping)
    doubled_params["n"] = 2 * int(shipping["n"])
    doubled = make_instance(seed=54321, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    ladder_spaces = [
        search_space(make_instance(seed=321, **params)) for params in DIFFICULTY.values()
    ]
    report["G7_scales"] = {
        "pass": doubled_ok and all(
            a is not None and b is not None and b > a
            for a, b in zip(ladder_spaces, ladder_spaces[1:])
        ),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "log2_search_spaces": [
            round(math.log2(value), 3) if value is not None else None
            for value in ladder_spaces
        ],
    }

    report["G8_canonical_key"] = _canonical_gate(shipping)

    answer_blob = json.dumps(inst["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    worst_chars = (
        2
        + 2 * (inst["n"] - 1)
        + sum(len(str(i)) + 1 for i in range(1, inst["n"] + 1))
    )
    intended_operations = 7 * inst["n"]
    compact_checks = 0
    for seed in range(20):
        compact_inst = make_instance(seed=50_000 + seed, **shipping)
        compact_answer = _compact_decode(compact_inst)
        if compact_answer is not None and verify(compact_inst, compact_answer)[0]:
            compact_checks += 1
    hinted_rate = (
        G9_ARMS["hinted"]["solved"] / G9_ARMS["hinted"]["attempts"]
        if G9_ARMS["hinted"]["attempts"]
        else None
    )
    placebo_rate = (
        G9_ARMS["placebo"]["solved"] / G9_ARMS["placebo"]["attempts"]
        if G9_ARMS["placebo"]["attempts"]
        else None
    )
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000 and inst["n"] <= 256 and intended_operations <= 300,
        "arms": G9_ARMS,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": (
            "not_run"
            if not G9_ARMS["hinted"]["attempts"]
            else ("hardened" if G9_ARMS["hinted"]["solved"] == 0 else "too_easy")
        ),
        "answer_chars": answer_chars,
        "worst_case_answer_chars": worst_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_tokens": (worst_chars + 3) // 4,
        "answer_elements": inst["n"],
        "intended_route_operations": intended_operations,
        "compact_route_verified": f"{compact_checks}/20",
        "operation_convention": (
            "4n comparisons/subtractions/divisions recover Q ranks and 3n multiplications/subtractions recover determinant signs"
        ),
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }
    report["G9_no_tool_suitability"]["pass"] = (
        report["G9_no_tool_suitability"]["pass"] and compact_checks == 20
    )

    gates = [
        value
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_passed"] = all(bool(gate.get("pass")) for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
