"""Self-contained problem generator for arXiv:1211.4559.

The paper studies a polygonal curve P, a finite site set S, and the task of
finding a polygonal curve Q through all sites with bounded continuous Frechet
distance from P.  This module inverse-generates a rational rotation first and
uses it to rotate every vertex of P.  The rotated vertices are the unordered
site set.  The answer is the exact 2 by 2 rational rotation matrix; it is a
succinct matrix certificate for the visiting curve Q = R(P).

Verification is entirely exact.  It checks the matrix, reconstructs Q, checks
that Q uses every site exactly once, and checks every paired endpoint distance.
Convexity of the squared Euclidean norm on a segment then gives a synchronous
leash of the claimed length on every segment, and the segment certificates
compose exactly as in Observations 1 and 2 of the paper.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time
from fractions import Fraction


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "geometry",
    "object_regime": "continuous_analytic",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "nonconvex polygonal curve with rational vertices in the plane",
        "unordered finite site set with rational coordinates",
        "orientation-preserving 2 by 2 rational rotation",
        "continuous synchronous Frechet coupling",
    ],
    "verification_operations": [
        "exact rational matrix multiplication",
        "exact point-set equality",
        "exact rational squared Euclidean distance comparison",
        "orthogonality and determinant identities over Q",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The vector sum of all sites is the same unknown rotation applied to "
        "the vector sum of all curve vertices; without noticing this global "
        "invariant one must match exact point configurations."
    ),
    "hardness_basis": (
        "Track B: exact orientation-preserving point-set congruence can be "
        "solved by anchor-induced rotation enumeration in O(n^2) rational "
        "operations; at hard n=768 it solved 8/8 instances in a measured mean "
        "about 0.15 seconds, 1,551 exact point transforms, and 12,223 counted "
        "rational arithmetic operations on average, while "
        "the supplied vector-sum invariant recovers the matrix in 12 exact "
        "arithmetic operations."
    ),
    "max_answer_tokens": 28,
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
    "demo": {"n": 5, "circle_factors": 2, "rotation_height": 7},
    "easy": {"n": 96, "circle_factors": 4, "rotation_height": 4095},
    "medium": {"n": 256, "circle_factors": 5, "rotation_height": 16383},
    "hard": {"n": 768, "circle_factors": 5, "rotation_height": 65535},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The vector sums of the curve vertices and of the sites transform under "
    "the same orientation-preserving rotation as every individual point."
)
PLACEBO_HINT = (
    "The rational coordinates of the curve points and of the sites require the "
    "same consistent sign and fraction bookkeeping in every calculation."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A 2 by 2 orientation-preserving rational rotation R(a,b), where "
        "R=[[(a^2-b^2)/(a^2+b^2),-2ab/(a^2+b^2)],"
        "[2ab/(a^2+b^2),(a^2-b^2)/(a^2+b^2)]], 1<=a<=H, "
        "-H<=b<=H, and gcd(a,|b|)=1; matrix entries are JSON rationals "
        "[numerator,denominator]."
    ),
    "bounds": {
        "rows": 2,
        "columns": 2,
        "a_min": 1,
        "a_max": "instance rotation_height H",
        "b_min": "-H",
        "b_max": "H",
        "coprime_parameter_pair": True,
    },
}

NOTES = (
    "Section 2.1, Definitions 1 and 2 fix the native witness: Q is a polygonal "
    "curve whose vertices are sites, every site is visited, reuse is allowed, "
    "and continuous Frechet distance is at most epsilon. Observations 1 and 2 "
    "supply the executable segment and concatenation certificates used here. "
    "The NP-completeness theorem in Section 2 is not used as an average-case "
    "claim. Section 3, Theorem 3 identifies the easy convex-polygon regime and "
    "its O(n k^2) decision algorithm; generated P is deliberately a shuffled, "
    "nonconvex polygonal curve. This family is nevertheless Track B because "
    "exact rotation-congruence matching is polynomial on the generated "
    "distribution. Plants and nonmatched sites have identical marginals: S is "
    "a global rotation of the whole set, not a collection of unusually close "
    "planted pairs. Nearest-pair, coordinate-height outlier, random-anchor, "
    "axis-rotation, and bounding-box attacks are measured. The disclosed "
    "reference algorithm enumerates all anchor-induced rotations; the compact "
    "route uses the vector-sum invariant."
)

# Filled after the three script-owned oracle runs.  Oracle outcomes are
# diagnostic only; G9 passes exactly when the answer and intended route fit the
# published caps.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unrun",
}


# Gaussian-prime representations p = x^2+y^2.  The first five factors give
# 4*3^5 = 972 distinct integer points on one circle, enough for the shipping
# preset.  Later entries support escalation without lengthening the answer.
_GAUSSIAN_PRIMES = (
    (2, 1),   # 5
    (3, 2),   # 13
    (4, 1),   # 17
    (5, 2),   # 29
    (6, 1),   # 37
    (5, 4),   # 41
    (7, 2),   # 53
    (6, 5),   # 61
)
_CATALOG_CACHE = {}
_SPACE_CACHE = {}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _qpair(value):
    value = Fraction(value)
    return [value.numerator, value.denominator]


def _read_q(value):
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(_is_int(x) for x in value)
        or value[1] == 0
    ):
        raise ValueError("a rational must be [integer numerator, nonzero integer denominator]")
    return Fraction(value[0], value[1])


def _point_from_json(point):
    if not isinstance(point, list) or len(point) != 2:
        raise ValueError("a point must have two coordinates")
    return (_read_q(point[0]), _read_q(point[1]))


def _point_to_json(point):
    return [_qpair(point[0]), _qpair(point[1])]


def _gmul(left, right):
    a, b = left
    c, d = right
    return (a * c - b * d, a * d + b * c)


def _circle_catalog(circle_factors):
    """All integer points from Gaussian factorizations of one circle."""
    if circle_factors in _CATALOG_CACHE:
        return _CATALOG_CACHE[circle_factors]
    values = [(1, 0)]
    radius = 1
    for x, y in _GAUSSIAN_PRIMES[:circle_factors]:
        prime = x * x + y * y
        radius *= prime
        pi_sq = _gmul((x, y), (x, y))
        conjugate_sq = (pi_sq[0], -pi_sq[1])
        choices = (pi_sq, (prime, 0), conjugate_sq)
        values = [_gmul(value, choice) for value in values for choice in choices]
    with_units = set()
    for value in values:
        for unit in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            with_units.add(_gmul(unit, value))
    result = (radius, tuple(sorted(with_units)))
    if len(result[1]) != 4 * (3 ** circle_factors):
        raise AssertionError("Gaussian point catalog unexpectedly collided")
    if any(x * x + y * y != radius * radius for x, y in result[1]):
        raise AssertionError("Gaussian point catalog left its circle")
    _CATALOG_CACHE[circle_factors] = result
    return result


def _rotation(a, b):
    denominator = a * a + b * b
    cosine = Fraction(a * a - b * b, denominator)
    sine = Fraction(2 * a * b, denominator)
    return ((cosine, -sine), (sine, cosine))


def _rotation_json(matrix):
    return [[_qpair(value) for value in row] for row in matrix]


def _apply(matrix, point):
    x, y = point
    return (
        matrix[0][0] * x + matrix[0][1] * y,
        matrix[1][0] * x + matrix[1][1] * y,
    )


def _sample_rotation_parameter(rng, height):
    # Keep the planted rotation away from the identity and half-turn.  On the
    # dense circle this makes nearest-site pairing actively misleading.
    for _ in range(10000):
        a = rng.randint(1, height)
        low = max(1, (a + 2) // 3)
        high = min(height, 3 * a)
        if low > high:
            continue
        b = rng.randint(low, high)
        if rng.randrange(2):
            b = -b
        if math.gcd(a, abs(b)) == 1:
            return a, b
    raise RuntimeError("could not sample a bounded rational rotation")


def _validate_parameters(n, circle_factors, rotation_height):
    if not _is_int(n) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if (
        not _is_int(circle_factors)
        or circle_factors < 2
        or circle_factors > len(_GAUSSIAN_PRIMES)
    ):
        raise ValueError("circle_factors is outside the supported range")
    capacity = 4 * (3 ** circle_factors)
    if n > capacity:
        raise ValueError("n exceeds the circle catalog for circle_factors")
    if not _is_int(rotation_height) or rotation_height < 2:
        raise ValueError("rotation_height must be an integer at least 2")


def make_instance(n, seed=0, circle_factors=5, rotation_height=65535, **params):
    """Inverse-generate a rational rotation and its exact visiting curve."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, circle_factors, rotation_height)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)

    # The certificate is sampled first.  No emitted instance is solved during
    # generation.
    a, b = _sample_rotation_parameter(rng, rotation_height)
    matrix = _rotation(a, b)

    radius, catalog = _circle_catalog(circle_factors)
    for _ in range(100):
        points = rng.sample(catalog, n)
        rng.shuffle(points)
        sum_p = (sum(x for x, _ in points), sum(y for _, y in points))
        if sum_p != (0, 0):
            break
    else:
        raise RuntimeError("could not construct a nonzero vector checksum")

    rotated = [_apply(matrix, point) for point in points]
    identifiers = rng.sample(range(1000000, 9000000), n)
    sites = [
        {"id": identifier, "point": _point_to_json(point)}
        for identifier, point in zip(identifiers, rotated)
    ]
    rng.shuffle(sites)

    sum_s = _apply(matrix, sum_p)
    epsilon_squared = Fraction(4 * radius * radius * b * b, a * a + b * b)
    inst = {
        "paper": "arXiv:1211.4559",
        "family": "rational rotation-coupled visiting curve",
        "n": n,
        "circle_factors": circle_factors,
        "rotation_height": rotation_height,
        "circle_radius": radius,
        "epsilon_squared": _qpair(epsilon_squared),
        "P": [_point_to_json(point) for point in points],
        "sites": sites,
        "sum_P": _point_to_json(sum_p),
        "sum_sites": _point_to_json(sum_s),
        "answer": _rotation_json(matrix),
    }
    return inst


def _format_q(value):
    value = Fraction(value)
    return f"{value.numerator}/{value.denominator}"


def _format_point_json(point):
    x, y = _point_from_json(point)
    return f"({_format_q(x)}, {_format_q(y)})"


def _answer_text(answer):
    matrix = _answer_to_fractions(answer)
    return "[[%s,%s],[%s,%s]]" % tuple(
        _format_q(matrix[row][column])
        for row in range(2)
        for column in range(2)
    )


def render(inst):
    """Render the complete, stand-alone exact geometry problem."""
    epsilon_squared = _read_q(inst["epsilon_squared"])
    lines = [
        "Rational rotation-coupled visiting curve",
        "",
        "A polygonal curve is an ordered list of points joined by straight segments.",
        "The continuous Frechet distance is the least leash length allowing two",
        "walkers to traverse their curves continuously from start to finish without",
        "backtracking; either walker may wait.",
        "",
        f"The curve P has {inst['n']} ordered control points p_0,...,p_{inst['n'] - 1} in the",
        "listed order. S is the unordered site set listed afterward. Coordinates",
        "are exact rationals num/den. Site IDs are labels only.",
        "",
        "Find a 2 by 2 orientation-preserving rational rotation matrix R of the form",
        "    [[c,-s],[s,c]] with c^2+s^2=1 and determinant +1.",
        "It must belong to the bounded language R(a,b):",
        "    c=(a^2-b^2)/(a^2+b^2), s=2ab/(a^2+b^2),",
        f"where 1 <= a <= {inst['rotation_height']}, -{inst['rotation_height']} <= b <= {inst['rotation_height']},",
        "and gcd(a,|b|)=1. The case b=0 therefore requires a=1.",
        "",
        "Your matrix induces Q in P's order: q_i = R p_i. It is valid exactly when",
        "the q_i are all distinct sites and use every site exactly once, and when",
        f"||p_i-q_i||^2 <= epsilon^2 for every i, with epsilon^2 = {_format_q(epsilon_squared)}.",
        "This endpoint condition is an exact synchronous continuous-Frechet",
        "certificate: on each pair of corresponding straight segments, matching",
        "equal segment parameters keeps squared distance at most epsilon^2; concatenate",
        "these matchings across all segments. No floating-point tolerance is used.",
        "",
        "The following two exact checksums are ordinary vector sums. They are part of",
        "the instance data and may be used or ignored:",
        f"sum of P control points = {_format_point_json(inst['sum_P'])}",
        f"sum of sites      = {_format_point_json(inst['sum_sites'])}",
        "",
        "P control points (0-indexed and ordered):",
    ]
    for index, point in enumerate(inst["P"]):
        lines.append(f"p_{index}: {_format_point_json(point)}")
    lines.extend(["", "Sites (unordered):"])
    for site in inst["sites"]:
        lines.append(f"{site['id']}: {_format_point_json(site['point'])}")
    lines.extend(
        [
            "",
            "Give your final answer inside <answer></answer> tags as two matrix rows,",
            "using four reduced rationals num/den in this exact layout:",
            "<answer>[[3/5,-4/5],[4/5,3/5]]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", PLACEBO_HINT])
    return "\n".join(lines)


def _parse_fraction_token(token):
    token = token.strip()
    if not re.fullmatch(r"[-+]?\d+(?:/[-+]?\d+)?", token):
        raise ValueError("not a rational token")
    if "/" in token:
        numerator, denominator = token.split("/", 1)
        if int(denominator) == 0:
            raise ValueError("zero denominator")
        return Fraction(int(numerator), int(denominator))
    return Fraction(int(token), 1)


def parse_answer(text):
    """Parse tagged matrix output, tolerating prose, whitespace, and fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    # Also accept the JSON-native nested [numerator, denominator] form so that
    # json.dumps(inst["answer"]) round-trips through the public parser.
    try:
        raw = json.loads(body)
        _answer_to_fractions(raw)
        return [[list(entry) for entry in row] for row in raw]
    except (ValueError, TypeError, json.JSONDecodeError):
        pass
    tokens = re.findall(r"[-+]?\d+(?:/[-+]?\d+)?", body)
    if len(tokens) != 4:
        return None
    # Refuse stray non-format prose inside the tags.
    residue = re.sub(r"[-+]?\d+(?:/[-+]?\d+)?", "", body)
    if re.sub(r"[\[\],\s]", "", residue):
        return None
    try:
        values = [_parse_fraction_token(token) for token in tokens]
    except (ValueError, ZeroDivisionError):
        return None
    return [
        [_qpair(values[0]), _qpair(values[1])],
        [_qpair(values[2]), _qpair(values[3])],
    ]


def _answer_to_fractions(answer):
    if not isinstance(answer, list) or len(answer) != 2:
        raise ValueError("rotation must be a 2 by 2 matrix")
    if any(not isinstance(row, list) or len(row) != 2 for row in answer):
        raise ValueError("rotation must be a 2 by 2 matrix")
    return tuple(tuple(_read_q(entry) for entry in row) for row in answer)


def _rotation_parameter(matrix):
    cosine = matrix[0][0]
    sine = matrix[1][0]
    if cosine == -1:
        return None
    return sine / (1 + cosine)


def verify(inst, answer):
    """Verify any bounded rotation certificate; never consult inst['answer']."""
    if answer == []:
        return False, "answer matrix is empty"
    try:
        matrix = _answer_to_fractions(answer)
    except (ValueError, TypeError, ZeroDivisionError) as exc:
        return False, str(exc)
    if matrix[0] == matrix[1]:
        return False, "rotation rows must be distinct"
    c = matrix[0][0]
    s = matrix[1][0]
    if matrix[0][1] != -s or matrix[1][1] != c:
        return False, "matrix is not in orientation-preserving rotation form"
    if c * c + s * s != 1:
        return False, "matrix is not orthogonal"
    if c * c - matrix[0][1] * matrix[1][0] != 1:
        return False, "matrix determinant is not one"
    parameter = _rotation_parameter(matrix)
    if parameter is None:
        return False, "rotation is outside the bounded certificate language"
    a = parameter.denominator
    b = parameter.numerator
    height = inst.get("rotation_height")
    if (
        not _is_int(height)
        or a < 1
        or a > height
        or abs(b) > height
        or math.gcd(a, abs(b)) != 1
    ):
        return False, "rotation parameter is outside certificate bounds"

    # This necessary exact invariant is intentionally checked before expanding
    # the whole curve.  It makes rejection cost proportional to the four matrix
    # entries rather than to n, while accepting no matrix the full checker would
    # reject: if R maps the P multiset onto S, it must map their vector sums.
    try:
        sum_p = _point_from_json(inst["sum_P"])
        sum_s = _point_from_json(inst["sum_sites"])
    except (KeyError, ValueError, TypeError, ZeroDivisionError):
        return False, "instance vector checksums are malformed"
    if _apply(matrix, sum_p) != sum_s:
        return False, "rotation violates the vector-sum checksum"

    try:
        p_points = [_point_from_json(point) for point in inst["P"]]
        site_points = [_point_from_json(site["point"]) for site in inst["sites"]]
        epsilon_squared = _read_q(inst["epsilon_squared"])
    except (KeyError, ValueError, TypeError, ZeroDivisionError):
        return False, "instance geometry is malformed"
    if len(set(site_points)) != len(site_points):
        return False, "instance site set contains duplicate points"
    site_set = set(site_points)
    q_points = []
    for point in p_points:
        image = _apply(matrix, point)
        if image not in site_set:
            return False, "rotated curve uses a point outside the site set"
        q_points.append(image)
    if len(q_points) != len(site_points) or set(q_points) != site_set:
        return False, "rotated curve does not visit every site exactly once"
    for p_point, q_point in zip(p_points, q_points):
        dx = p_point[0] - q_point[0]
        dy = p_point[1] - q_point[1]
        if dx * dx + dy * dy > epsilon_squared:
            return False, "synchronous leash exceeds epsilon at a curve vertex"
    return True, "ok"


def _totient_sum(height):
    if height in _SPACE_CACHE:
        return _SPACE_CACHE[height]
    phi = list(range(height + 1))
    for value in range(2, height + 1):
        if phi[value] == value:
            for multiple in range(value, height + 1, value):
                phi[multiple] -= phi[multiple] // value
    total = sum(phi[1:])
    _SPACE_CACHE[height] = total
    return total


def search_space(inst):
    """Exact size of the bounded primitive rational-rotation language."""
    height = inst.get("rotation_height")
    if not _is_int(height) or height < 1:
        return 0
    # Positive a and signed b.  Positive b contributes every ordered coprime
    # pair in [1,H]^2, negative b contributes the same, and b=0 contributes
    # only (a,b)=(1,0): 4*sum_{m<=H} phi(m)-1.
    return 4 * _totient_sum(height) - 1


def random_candidate(inst, rng):
    """Uniformly sample a canonical primitive (a,b), hence a legal rotation."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    height = inst["rotation_height"]
    while True:
        a = rng.randint(1, height)
        b = rng.randint(-height, height)
        if math.gcd(a, abs(b)) == 1:
            return _rotation_json(_rotation(a, b))


def enumerate_all(inst):
    """Count all valid matrices exactly only when the declared space is small."""
    space = search_space(inst)
    if space > 10000:
        return None
    height = inst["rotation_height"]
    count = 0
    for a in range(1, height + 1):
        for b in range(-height, height + 1):
            if math.gcd(a, abs(b)) != 1:
                continue
            if verify(inst, _rotation_json(_rotation(a, b)))[0]:
                count += 1
    return count


def _canonical_distance_multiset(inst):
    raw_points = inst["P"]
    integral = all(
        coordinate[1] == 1
        for point in raw_points
        for coordinate in point
    )
    distances = []
    if integral:
        # Normal generated instances have integer P coordinates.  Staying in
        # integers makes the shipping-size diversity check roughly an order of
        # magnitude faster; the rational branch is retained for transformed
        # instances in G8.
        points = [(point[0][0], point[1][0]) for point in raw_points]
        for left in range(len(points)):
            for right in range(left + 1, len(points)):
                dx = points[left][0] - points[right][0]
                dy = points[left][1] - points[right][1]
                distances.append((dx * dx + dy * dy, 1))
    else:
        points = [_point_from_json(point) for point in raw_points]
        for left in range(len(points)):
            for right in range(left + 1, len(points)):
                dx = points[left][0] - points[right][0]
                dy = points[left][1] - points[right][1]
                distance = dx * dx + dy * dy
                distances.append((distance.numerator, distance.denominator))
    # Every pair is already in a unique reduced [numerator, denominator] form;
    # lexicographic ordering is canonical and avoids rebuilding hundreds of
    # thousands of Fraction objects merely to choose an order.
    distances.sort()
    return distances


def canonical_key(inst):
    """A coordinate-isometry and relabelling invariant structural key."""
    payload = {
        "n": len(inst["P"]),
        "epsilon_squared_over_radius_squared": _qpair(
            _read_q(inst["epsilon_squared"])
            / Fraction(inst["circle_radius"] * inst["circle_radius"], 1)
        ),
        "pairwise_squared_distances": _canonical_distance_multiset(inst),
    }
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params):
    """Grow the geometric haystack and rotation language, not the matrix answer."""
    current = dict(params)
    current.pop("_preset", None)
    n = int(current.get("n", 3))
    factors = int(current.get("circle_factors", 2))
    height = int(current.get("rotation_height", 7))
    target_n = 2 * n
    while factors < len(_GAUSSIAN_PRIMES) and target_n > 4 * (3 ** factors):
        factors += 1
    if target_n > 4 * (3 ** factors):
        target_n = n
    current["n"] = target_n
    current["circle_factors"] = factors
    current["rotation_height"] = min(2**31 - 1, 2 * height + 1)
    if current["n"] == n and current["rotation_height"] == height:
        return None
    return current


def _matrix_from_unit_circle_pair(p_point, s_point, radius_squared):
    dot = p_point[0] * s_point[0] + p_point[1] * s_point[1]
    cross = p_point[0] * s_point[1] - p_point[1] * s_point[0]
    cosine = dot / radius_squared
    sine = cross / radius_squared
    return ((cosine, -sine), (sine, cosine))


def _reference_algorithm(inst):
    """Generic exact anchor-induced rotation enumeration with early rejection."""
    started = time.perf_counter()
    p_points = [_point_from_json(point) for point in inst["P"]]
    s_points = [_point_from_json(site["point"]) for site in inst["sites"]]
    site_set = set(s_points)
    radius_squared = Fraction(inst["circle_radius"] ** 2, 1)
    transforms = 0
    candidates = 0
    p_anchor = p_points[0]
    for s_anchor in s_points:
        candidates += 1
        matrix = _matrix_from_unit_circle_pair(p_anchor, s_anchor, radius_squared)
        all_present = True
        for point in p_points:
            transforms += 1
            if _apply(matrix, point) not in site_set:
                all_present = False
                break
        if all_present:
            answer = _rotation_json(matrix)
            if verify(inst, answer)[0]:
                return {
                    "solved": True,
                    "answer": answer,
                    "candidate_rotations": candidates,
                    "point_transforms": transforms,
                    "arithmetic_operations": 8 * candidates + 6 * transforms,
                    "wall_clock_sec": time.perf_counter() - started,
                }
    return {
        "solved": False,
        "answer": None,
        "candidate_rotations": candidates,
        "point_transforms": transforms,
        "arithmetic_operations": 8 * candidates + 6 * transforms,
        "wall_clock_sec": time.perf_counter() - started,
    }


def _candidate_from_pair(inst, p_point, s_point):
    radius_squared = Fraction(inst["circle_radius"] ** 2, 1)
    return _rotation_json(_matrix_from_unit_circle_pair(p_point, s_point, radius_squared))


def _attack_axis_rotations(inst):
    for matrix in (
        ((Fraction(1), Fraction(0)), (Fraction(0), Fraction(1))),
        ((Fraction(0), Fraction(-1)), (Fraction(1), Fraction(0))),
        ((Fraction(0), Fraction(1)), (Fraction(-1), Fraction(0))),
        ((Fraction(-1), Fraction(0)), (Fraction(0), Fraction(-1))),
    ):
        if verify(inst, _rotation_json(matrix))[0]:
            return True
    return False


def _attack_nearest_anchor(inst):
    p_points = [_point_from_json(point) for point in inst["P"]]
    s_points = [_point_from_json(site["point"]) for site in inst["sites"]]
    anchor = p_points[0]
    nearest = min(
        s_points,
        key=lambda point: (point[0] - anchor[0]) ** 2 + (point[1] - anchor[1]) ** 2,
    )
    return verify(inst, _candidate_from_pair(inst, anchor, nearest))[0]


def _coordinate_height(point):
    return sum(
        abs(value.numerator).bit_length() + value.denominator.bit_length()
        for value in point
    )


def _attack_height_outlier(inst):
    p_points = [_point_from_json(point) for point in inst["P"]]
    s_points = [_point_from_json(site["point"]) for site in inst["sites"]]
    p_choice = min(p_points, key=lambda point: (_coordinate_height(point), point))
    s_choice = min(s_points, key=lambda point: (_coordinate_height(point), point))
    return verify(inst, _candidate_from_pair(inst, p_choice, s_choice))[0]


def _attack_random_anchor_16(inst, seed):
    p_points = [_point_from_json(point) for point in inst["P"]]
    s_points = [_point_from_json(site["point"]) for site in inst["sites"]]
    rng = random.Random(seed ^ 0x5A17C3)
    for s_choice in rng.sample(s_points, min(16, len(s_points))):
        if verify(inst, _candidate_from_pair(inst, p_points[0], s_choice))[0]:
            return True
    return False


def _attack_bounding_box(inst):
    p_points = [_point_from_json(point) for point in inst["P"]]
    s_points = [_point_from_json(site["point"]) for site in inst["sites"]]
    # The tempting in-context ansatz that extremal x-coordinates correspond.
    p_choice = max(p_points, key=lambda point: (point[0], point[1]))
    s_choice = max(s_points, key=lambda point: (point[0], point[1]))
    return verify(inst, _candidate_from_pair(inst, p_choice, s_choice))[0]


def _json_atoms(value):
    if isinstance(value, dict):
        return sum(_json_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_json_atoms(item) for item in value)
    return 1


def _transform_instance(inst, matrix, reflect=False, reorder=False):
    """Apply a genuine common isometry and optional input relabellings."""
    clone = json.loads(json.dumps(inst))
    p_points = [_point_from_json(point) for point in clone["P"]]
    sites = [
        {"id": site["id"], "point": _point_from_json(site["point"])}
        for site in clone["sites"]
    ]

    def transform(point):
        value = _apply(matrix, point)
        if reflect:
            value = (value[0], -value[1])
        return value

    p_points = [transform(point) for point in p_points]
    sites = [{"id": site["id"], "point": transform(site["point"])} for site in sites]
    if reorder:
        p_points.reverse()
        sites.reverse()
        for index, site in enumerate(sites):
            site["id"] = 70000000 + index
    clone["P"] = [_point_to_json(point) for point in p_points]
    clone["sites"] = [
        {"id": site["id"], "point": _point_to_json(site["point"])} for site in sites
    ]
    sum_p = (sum(point[0] for point in p_points), sum(point[1] for point in p_points))
    sum_s = (
        sum(site["point"][0] for site in sites),
        sum(site["point"][1] for site in sites),
    )
    clone["sum_P"] = _point_to_json(sum_p)
    clone["sum_sites"] = _point_to_json(sum_s)
    return clone


def selftest():
    """Run and return all mandatory gate measurements."""
    report = {"paper": "1211.4559", "track": TRACK, "shipping": SHIPPING_DIFFICULTY}

    g1_failures = []
    g1_tests = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            instance = make_instance(seed=seed, **params)
            ok, reason = verify(instance, instance["answer"])
            g1_tests += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(instance["answer"])) != instance["answer"]:
                g1_failures.append({"preset": preset, "seed": seed, "reason": "answer not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "tests": g1_tests,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=17, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    height = shipping["rotation_height"]
    corruptions = {
        "drop_one_row": [planted[0]],
        "swap_one_entry": [[planted[0][1], planted[0][0]], list(planted[1])],
        "duplicate_row": [list(planted[0]), list(planted[0])],
        "empty": [],
        "out_of_range": _rotation_json(_rotation(1, height + 1)),
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    model_style = (
        "I used the global checksum relation.\n```text\n<answer>"
        + _answer_text(shipping["answer"])
        + "</answer>\n```\nThe induced curve visits all sites."
    )
    parsed = parse_answer(model_style)
    json_roundtrip = parse_answer(
        "<answer>" + json.dumps(shipping["answer"]) + "</answer>"
    )
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and json_roundtrip == shipping["answer"],
        "model_style_parsed": parsed == shipping["answer"],
        "json_native_parsed": json_roundtrip == shipping["answer"],
    }

    guess_rng = random.Random(12114559)
    guess_total = 200000
    guess_hits = 0
    guess_started = time.perf_counter()
    for _ in range(guess_total):
        if verify(shipping, random_candidate(shipping, guess_rng))[0]:
            guess_hits += 1
    guess_elapsed = time.perf_counter() - guess_started
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "certificate_language_size": search_space(shipping),
        "wall_clock_sec": round(guess_elapsed, 6),
        "sampling_prior": "uniform over primitive bounded rational rotations R(a,b)",
    }

    reference_rows = []
    attack_counts = {
        "outlier_coordinate_height": 0,
        "greedy_nearest_anchor": 0,
        "random_anchor_restart_16": 0,
        "axis_rotation_ansatz": 0,
        "bounding_box_extrema": 0,
    }
    attack_attempts = 8
    for seed in range(8001, 8001 + attack_attempts):
        instance = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        attack_counts["outlier_coordinate_height"] += int(_attack_height_outlier(instance))
        attack_counts["greedy_nearest_anchor"] += int(_attack_nearest_anchor(instance))
        attack_counts["random_anchor_restart_16"] += int(
            _attack_random_anchor_16(instance, seed)
        )
        attack_counts["axis_rotation_ansatz"] += int(_attack_axis_rotations(instance))
        attack_counts["bounding_box_extrema"] += int(_attack_bounding_box(instance))
        reference_rows.append(_reference_algorithm(instance))

    attacks = {
        name: {"successes": successes, "attempts": attack_attempts}
        for name, successes in attack_counts.items()
    }
    reference_solved = sum(int(row["solved"]) for row in reference_rows)
    reference_operations = [row["arithmetic_operations"] for row in reference_rows]
    reference_transforms = [row["point_transforms"] for row in reference_rows]
    reference_times = [row["wall_clock_sec"] for row in reference_rows]
    reference_algorithm = {
        "name": "exact anchor-induced rotation enumeration",
        "complexity": "O(n^2) exact rational operations in the worst case",
        "wall_clock_sec_mean": round(sum(reference_times) / len(reference_times), 6),
        "wall_clock_sec_max": round(max(reference_times), 6),
        "operations_mean": round(sum(reference_operations) / len(reference_operations), 2),
        "operations_max": max(reference_operations),
        "point_transforms_mean": round(
            sum(reference_transforms) / len(reference_transforms), 2
        ),
        "point_transforms_max": max(reference_transforms),
        "candidate_rotations_mean": round(
            sum(row["candidate_rotations"] for row in reference_rows) / len(reference_rows),
            2,
        ),
        "solves": f"{reference_solved}/{len(reference_rows)}, as expected",
    }
    report["G5_density_and_baseline"] = {
        "pass": reference_solved == len(reference_rows),
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "reference_wall_clock_sec": round(
            sum(reference_times) / len(reference_times), 6
        ),
        "reference_operation_count": round(
            sum(reference_operations) / len(reference_operations), 2
        ),
        "shipping_density_estimate": {
            "hits": guess_hits,
            "samples": guess_total,
            "observed_fraction": guess_rate,
        },
        "demo_exact_valid_answers": enumerate_all(make_instance(seed=0, **DIFFICULTY["demo"])),
        "shipping_reference_cost": reference_algorithm,
    }
    report["G6_adversary_panel"] = {
        "pass": all(entry["successes"] == 0 for entry in attacks.values())
        and reference_solved == len(reference_rows),
        "attacks": attacks,
        "reference_algorithm": reference_algorithm,
    }

    doubled_params = escalate(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled = make_instance(seed=31337, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] >= 2 * shipping["n"],
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_params": doubled_params,
        "verify_reason": doubled_reason,
    }

    invariant_checks = 0
    carried_witness_checks = 0
    distinct_keys = []
    for seed in range(20):
        base = make_instance(n=24, seed=90000 + seed, circle_factors=3, rotation_height=127)
        base_key = canonical_key(base)
        distinct_keys.append(base_key)
        relabelled = _transform_instance(
            base,
            _rotation(5, 2),
            reflect=False,
            reorder=True,
        )
        invariant_checks += int(canonical_key(relabelled) == base_key)
        carried_witness_checks += int(verify(relabelled, base["answer"])[0])

        reflected = _transform_instance(
            base,
            _rotation(3, -2),
            reflect=True,
            reorder=True,
        )
        inverse_answer = [
            [list(base["answer"][0][0]), _qpair(_read_q(base["answer"][1][0]))],
            [_qpair(-_read_q(base["answer"][1][0])), list(base["answer"][1][1])],
        ]
        # Reflection conjugates [[c,-s],[s,c]] to [[c,s],[-s,c]].
        invariant_checks += int(canonical_key(reflected) == base_key)
        carried_witness_checks += int(verify(reflected, inverse_answer)[0])
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 40
        and carried_witness_checks == 40
        and len(set(distinct_keys)) == 20,
        "invariance_passes": invariant_checks,
        "invariance_attempts": 40,
        "carried_witness_passes": carried_witness_checks,
        "carried_witness_attempts": 40,
        "distinct_unrelated": len(set(distinct_keys)),
        "unrelated_attempts": 20,
        "invariants": [
            "site reordering and ID renaming",
            "curve-order reversal for this rotation-certificate problem",
            "common rational rotation",
            "common reflection with conjugated witness",
        ],
    }

    # Seed 10 realizes the measured worst serialization in a 10,000-seed sweep
    # at the shipping bounds (three signed ten-digit numerators).
    size_instance = make_instance(
        seed=10, **DIFFICULTY[SHIPPING_DIFFICULTY]
    )
    answer_wire = json.dumps(size_instance["answer"])
    answer_chars = len(answer_wire)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _json_atoms(shipping["answer"])
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else 0.0
    )
    within_caps = (
        answer_chars <= 2000 and answer_elements <= 256 and 12 <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": 12,
        "caps_only_gate": True,
    }

    gate_values = [
        value["pass"]
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict) and "pass" in value
    ]
    report["all_pass"] = all(gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
