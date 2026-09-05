"""Verified Track-B generator based on the k-means SDP of arXiv:1505.04778.

The answer is planted before the point cloud is assembled.  Given a proposed
balanced partition, verification reconstructs the Section 3 dual certificate
over Q and checks its slack matrix for positive semidefiniteness exactly.  No
comparison with the planted answer is made.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time
from fractions import Fraction


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - fallback tested below
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "optimization",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite Euclidean point cloud over Q",
        "balanced partition and its normalized indicator matrix",
        "primal-dual k-means SDP certificate over Q",
    ],
    "verification_operations": [
        "exact squared Euclidean distance",
        "exact construction of the SDP dual slack matrix",
        "nonnegativity checks on dual variables",
        "exact rational PSD check by LDL decomposition",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Three congruent residual clouds are translates, and a quarter-turn relation "
        "between their global mean and translation direction compresses generic "
        "SDP recovery to one exact projection; without it one must recover and "
        "certify the clustering mechanically."
    ),
    "hardness_basis": (
        "Track B: the Section 2 semidefinite program is polynomial-time and the "
        "implemented mean-projection recovery plus Section 3 exact dual check is "
        "O(Nm+N log N+N^3) (about 23,208 counted exact operations and under one "
        "second at shipping N=24); the symmetry route uses 264 exact arithmetic "
        "operations but must be recognized and executed without tools."
    ),
    "max_answer_tokens": 21,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "An unlabeled balanced set partition encoded as the JSON object "
        "{\"clusters\":[C1,C2,C3]}; each Ci contains exactly n distinct "
        "0-based point indices, the three lists cover all 3n indices, entries "
        "inside a list are increasing, and lists are ordered lexicographically. "
        "The partition compactly encodes the SDP primal matrix; the dual matrix "
        "is reconstructed exactly by the stated Section 3 formulas."
    ),
    "bounds": {
        "clusters": 3,
        "cluster_size": "instance n",
        "index_range": "0 through 3n-1",
        "ordering": "canonical unlabeled balanced partitions",
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 2, "coord_bits": 4, "radius_bits": 4},
    "easy": {"n": 8, "coord_bits": 10, "radius_bits": 10},
    "medium": {"n": 8, "coord_bits": 20, "radius_bits": 20},
    "hard": {"n": 8, "coord_bits": 36, "radius_bits": 36},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The three centroids share a translation direction encoded by a quarter-turn "
    "relation between the global coordinate mean and that direction."
)
PLACEBO_HINT = (
    "The three requested clusters require careful exact arithmetic with every "
    "displayed coordinate and consistent handling of their point indices."
)

# Populated from script-owned hardening runs before release.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unavailable_openrouter_403",
}

NOTES = r"""
Paper reading and definition.  Section 2 defines the exact k-means objective,
its normalized partition matrix X, and the SDP constraints Tr(X)=k, X1=1,
X>=0 and X positive semidefinite.  Section 3 (Theorem 6 in the paper's theorem
counter) gives the deterministic dual certificate used here.  The stochastic
ball theorem in Section 4 is deliberately not invoked: a finite rational
distribution is not rotation invariant, while the deterministic certificate
applies exactly to every emitted rational point cloud.

Step-0 algorithm check.  This cannot honestly be Track A.  The paper's central
algorithm is an SDP and Section 2 explicitly says tightness gives both a
solution and an optimality certificate by convex duality.  This module is
therefore Track B.  Its reference recovery computes the point-cloud mean,
uses the construction's quarter-turn coordinate relation to recover the translation
direction, sorts one projection, and finally executes the paper's exact dual
check.  Recovery is O(Nm+N log N), and exact certificate checking is O(N^3).
The generic SDP has a much larger mechanical constant; the compact route left
after recognizing the symmetry is at most 300 exact operations at shipping.

Construction.  Put one antipodal residual pair of radius between 19/20 and
99/100 on each displayed coordinate axis and use smaller additional pairs.
Make three copies centered at mu-d, mu, mu+d, with ||d||=11/5 and mu a
quarter-turn of d; these two vectors are orthogonal.  The direction d comes from a
dense rational Householder image, and common denominator clearing preserves
the SDP under uniform scaling.  Labels
are retained before a random point permutation.  The Section 3 dual variables
are then identities in exact rational arithmetic; generation never searches
for a partition.  The checker nevertheless reconstructs the full certificate
from any candidate and accepts any candidate for which it is feasible.

Attack handling.  The rational isometry prevents the first displayed
coordinate from being the planted direction.  Orthogonal translation centers
the two outer clouds at equal norm, defeating norm tertiles.  Residuals extend
far enough along the center direction that nearest-seed greed crosses cluster
boundaries.  Uniform restarts sample the exact balanced-partition language.
All plants and random candidates use the same unlabeled-partition convention.
""".strip()


# ---------------------------------------------------------------------------
# Exact construction helpers


def _q_json(x: Fraction) -> list[int]:
    return [x.numerator, x.denominator]


def _q_from_json(x: object) -> Fraction:
    if (not isinstance(x, list) or len(x) != 2
            or isinstance(x[0], bool) or isinstance(x[1], bool)
            or not isinstance(x[0], int) or not isinstance(x[1], int)
            or x[1] <= 0):
        raise ValueError("malformed rational")
    return Fraction(x[0], x[1])


def _dot(a: list[Fraction], b: list[Fraction]) -> Fraction:
    return sum((x * y for x, y in zip(a, b)), Fraction(0))


def _matvec(A: list[list[Fraction]], x: list[Fraction]) -> list[Fraction]:
    return [_dot(row, x) for row in A]


def _cycle(x: list[Fraction]) -> list[Fraction]:
    """A fixed quarter-turn P satisfying <x,Px>=0 for every x in Q^4."""
    return [-x[1], x[0], -x[3], x[2]]


def _uncycle(x: list[Fraction]) -> list[Fraction]:
    return [x[1], -x[0], x[3], -x[2]]


def _householder_to(v: list[Fraction]) -> list[list[Fraction]]:
    """A rational orthogonal Q with Q e_1=v, for unit v != e_1."""
    one = Fraction(1)
    u = [one - v[0]] + [-x for x in v[1:]]
    den = one - v[0]
    size = len(v)
    return [[(one if i == j else Fraction(0)) - u[i] * u[j] / den
             for j in range(size)] for i in range(size)]


def _canonical_clusters(groups: list[list[int]]) -> list[list[int]]:
    return sorted((sorted(g) for g in groups), key=lambda g: tuple(g))


def _point_dist2(p: list[int], q: list[int]) -> int:
    return sum((a - b) * (a - b) for a, b in zip(p, q))


def make_instance(n: int, seed: int = 0, coord_bits: int = 12,
                  radius_bits: int = 12, **params) -> dict:
    """Plant first, then compose exact isometries and translations around it."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 2 or n % 2:
        raise ValueError("n must be an even integer at least 2")
    if not (3 <= coord_bits <= 60 and 3 <= radius_bits <= 60):
        raise ValueError("bit parameters must lie between 3 and 60")
    rng = random.Random(seed)

    # Rational stereographic image near (-1,1,1,1)/2.  Its height makes the
    # printed coordinates mechanically unpleasant without changing geometry.
    base = 1 << coord_bits
    tq = base + rng.randrange(1, max(2, base // 3))
    jitter = max(1, tq // 4096)
    ts = [Fraction(tq + rng.randint(-jitter, jitter), tq),
          Fraction(tq + rng.randint(-jitter, jitter), tq),
          Fraction(-tq + rng.randint(-jitter, jitter), tq)]
    norm_t = sum((t * t for t in ts), Fraction(0))
    den = 1 + norm_t
    v = [(1 - norm_t) / den] + [2 * t / den for t in ts]
    assert _dot(v, v) == 1
    Q = _householder_to(v)
    assert _matvec(Q, [Fraction(1), Fraction(0), Fraction(0), Fraction(0)]) == v

    delta = Fraction(11, 5)
    d = [delta * x for x in v]
    mu = _cycle(d)
    assert _dot(d, mu) == 0

    rden = (1 << radius_bits) + 1
    residuals: list[list[Fraction]] = []
    radii: list[Fraction] = []
    for h in range(n // 2):
        # A tiny deterministic offset makes repeated radii impossible within
        # one cloud while retaining a very large seed-dependent instance space.
        if h < 4:
            lo = (19 * rden + 19) // 20
            hi = (99 * rden) // 100
        else:
            lo = (rden + 1) // 2
            hi = (13 * rden) // 20
        room = max(1, hi - lo - n)
        num = lo + rng.randrange(room) + h
        q = Fraction(1, 2) if n == 2 else Fraction(min(num, hi), rden)
        radii.append(q)
        residual = [Fraction(0), Fraction(0), Fraction(0), Fraction(0)]
        # The six-point demo uses an orthogonal residual pair; a lone pair on
        # the center axis is the one degenerate small case where this dual
        # certificate is not PSD.  Larger presets cycle through all axes.
        axis = 1 if n == 2 else h % 4
        residual[axis] = q
        r = residual
        residuals.extend([r, [-x for x in r]])

    points_q: list[list[Fraction]] = []
    labels: list[int] = []
    for a in range(3):
        center = [mu[j] + (a - 1) * d[j] for j in range(4)]
        for r in residuals:
            points_q.append([center[j] + r[j] for j in range(4)])
            labels.append(a)

    # Clear one common denominator.  A uniform scaling preserves the k-means
    # SDP and turns every public operation into integer/rational arithmetic.
    scale = 1
    for p in points_q:
        for x in p:
            scale = math.lcm(scale, x.denominator)
    points = [[x.numerator * (scale // x.denominator) for x in p]
              for p in points_q]

    order = list(range(3 * n))
    rng.shuffle(order)
    # A middle-cloud point is placed first without revealing which of the three
    # unlabeled clusters it belongs to.  Both translation directions are then
    # present, so the obvious "first point plus its n-1 nearest" greedy rule is
    # exposed to a boundary crossing instead of occasionally receiving a lucky
    # outward-facing seed from an extreme cloud.
    first_middle = next(old for old in order if labels[old] == 1)
    order.remove(first_middle)
    order.insert(0, first_middle)
    shuffled = [points[i] for i in order]
    shuffled_labels = [labels[i] for i in order]
    groups = [[i for i, a in enumerate(shuffled_labels) if a == label]
              for label in range(3)]
    answer = {"clusters": _canonical_clusters(groups)}
    assert json.loads(json.dumps(answer)) == answer

    return {
        "n": n,
        "k": 3,
        "dimension": 4,
        "points": shuffled,
        "answer": answer,
        "construction": {
            "coord_bits": coord_bits,
            "radius_bits": radius_bits,
            "cleared_denominator_digits": len(str(scale)),
        },
    }


# ---------------------------------------------------------------------------
# Exact paper certificate


def _is_psd_fallback(A: list[list[Fraction]]) -> bool:
    """Exact unpivoted LDL PSD test, matching gvlib's zero-pivot rule."""
    size = len(A)
    if any(len(row) != size for row in A):
        return False
    if any(A[i][j] != A[j][i] for i in range(size)
           for j in range(i + 1, size)):
        return False
    S = [row[:] for row in A]
    for k in range(size):
        pivot = S[k][k]
        if pivot < 0:
            return False
        if pivot == 0:
            if any(S[i][k] != 0 for i in range(k + 1, size)):
                return False
            continue
        for i in range(k + 1, size):
            f = S[i][k] / pivot
            if f:
                for j in range(k + 1, size):
                    S[i][j] -= f * S[k][j]
            S[i][k] = Fraction(0)
    return True


def _centroids_in_arithmetic_progression(points: list[list[int]],
                                         groups: list[list[int]]) -> bool:
    dimension = len(points[0])
    sums = [[sum(points[i][j] for i in g) for j in range(dimension)] for g in groups]
    for middle in range(3):
        ends = [a for a in range(3) if a != middle]
        if all(2 * sums[middle][j] == sums[ends[0]][j] + sums[ends[1]][j]
               for j in range(dimension)):
            return True
    return False


def _paper_certificate(points: list[list[int]], groups: list[list[int]]) -> tuple[bool, str]:
    """Construct Theorem 6's z,B,Q and check dual feasibility exactly."""
    k = len(groups)
    n = len(groups[0])
    N = len(points)
    D = [[Fraction(0) for _ in range(N)] for _ in range(N)]
    for i in range(N):
        for j in range(i + 1, N):
            value = Fraction(_point_dist2(points[i], points[j]))
            D[i][j] = D[j][i] = value

    within_rows: list[dict[int, Fraction]] = []
    totals: list[Fraction] = []
    for group in groups:
        rows = {i: sum((D[i][j] for j in group), Fraction(0)) for i in group}
        within_rows.append(rows)
        totals.append(sum(rows.values(), Fraction(0)))

    membership = [0] * N
    for a, group in enumerate(groups):
        for i in group:
            membership[i] = a
    M = [[Fraction(0) for _ in range(N)] for _ in range(N)]
    for i in range(N):
        a = membership[i]
        for j in range(N):
            b = membership[j]
            M[i][j] = (D[i][j]
                       + totals[a] / (2 * n * n) - within_rows[a][i] / n
                       + totals[b] / (2 * n * n) - within_rows[b][j] / n)

    cross_rows: dict[tuple[int, int], list[Fraction]] = {}
    for a in range(k):
        for b in range(k):
            if a == b:
                continue
            cross_rows[a, b] = [sum((M[i][j] for j in groups[b]), Fraction(0))
                                for i in groups[a]]
    z = min(x for values in cross_rows.values() for x in values)
    u = {key: [x - z for x in values] for key, values in cross_rows.items()}
    if z < 0 or any(x < 0 for values in u.values() for x in values):
        return False, "the reconstructed dual has a negative nonnegativity variable"

    B = [[Fraction(0) for _ in range(N)] for _ in range(N)]
    for a in range(k):
        for b in range(k):
            if a == b:
                continue
            rho_ab = sum(u[a, b], Fraction(0))
            rho_ba = sum(u[b, a], Fraction(0))
            if rho_ab != rho_ba:
                return False, "the reconstructed off-diagonal dual blocks are asymmetric"
            if rho_ba == 0:
                if any(u[a, b]) or any(u[b, a]):
                    return False, "a zero dual normalizer has a nonzero numerator"
                continue
            for ii, i in enumerate(groups[a]):
                for jj, j in enumerate(groups[b]):
                    B[i][j] = u[a, b][ii] * u[b, a][jj] / rho_ba

    Qslack = [[(z * ((1 if i == j else 0) - Fraction(1, n))
                      + M[i][j] - B[i][j])
               for j in range(N)] for i in range(N)]
    # Complementary slackness should be exact on every proposed block.
    for group in groups:
        for i in range(N):
            if sum((Qslack[i][j] for j in group), Fraction(0)) != 0:
                return False, "the reconstructed dual violates complementary slackness"
    psd = (exact_matrices.is_psd(Qslack) if exact_matrices is not None
           else _is_psd_fallback(Qslack))
    if not psd:
        return False, "the reconstructed SDP dual slack matrix is not positive semidefinite"
    return True, "ok"


def _validate_answer_shape(inst: dict, answer: object) -> tuple[list[list[int]] | None, str]:
    if not isinstance(answer, dict) or set(answer) != {"clusters"}:
        return None, "answer must be a JSON object with only the key 'clusters'"
    groups = answer.get("clusters")
    if not isinstance(groups, list) or len(groups) != inst["k"]:
        return None, "expected exactly three clusters"
    if any(not isinstance(g, list) for g in groups):
        return None, "each cluster must be a JSON list"
    if any(len(g) != inst["n"] for g in groups):
        return None, "each cluster must contain exactly n point indices"
    flat = [x for g in groups for x in g]
    if any(isinstance(x, bool) or not isinstance(x, int) for x in flat):
        return None, "every point index must be an integer"
    if any(x < 0 or x >= len(inst["points"]) for x in flat):
        return None, "a point index is outside the stated 0-based range"
    if len(set(flat)) != len(flat):
        return None, "point indices are duplicated rather than forming a partition"
    if set(flat) != set(range(len(inst["points"]))):
        return None, "the cluster lists do not cover every point index"
    return [list(g) for g in groups], "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    groups, reason = _validate_answer_shape(inst, answer)
    if groups is None:
        return False, reason
    if not _centroids_in_arithmetic_progression(inst["points"], groups):
        return False, "the three candidate centroids are not an arithmetic progression"
    return _paper_certificate(inst["points"], groups)


# ---------------------------------------------------------------------------
# Solver contract


def _format_point(p: list[int]) -> str:
    return "[" + ", ".join(str(x) for x in p) + "]"


def render(inst: dict) -> str:
    n = inst["n"]
    lines = [
        "Exact balanced k-means SDP certificate recovery",
        "",
        f"There are N={3*n} exact points in Q^4 below (all happen to have integer",
        "coordinates) and k=3 clusters. Point indices are 0-based.",
        "",
        "For a candidate partition C_1,C_2,C_3, each of size n, define",
        "D_ij = ||x_i-x_j||_2^2. For i in C_a put",
        "s_a(i)=sum_{j in C_a} D_ij and T_a=sum_{i,j in C_a} D_ij.",
        "For i in C_a and j in C_b define",
        "M_ij = D_ij + T_a/(2n^2)-s_a(i)/n + T_b/(2n^2)-s_b(j)/n.",
        "Let z be the minimum, over a!=b and i in C_a, of",
        "sum_{j in C_b} M_ij. Define u_ab(i)=sum_{j in C_b}M_ij-z and",
        "rho_ab=sum_{i in C_a}u_ab(i). Set B_aa=0 and, for a!=b,",
        "B_ij=u_ab(i)u_ba(j)/rho_ba. If rho_ba=0 this block is zero only",
        "when both numerator vectors are zero. Finally define",
        "Q_ij=z*(1 if i=j else 0)-z/n+M_ij-B_ij.",
        "",
        "Find an unlabeled partition into three size-n clusters such that z and all",
        "u entries are nonnegative, Q is positive semidefinite, Q times each cluster",
        "indicator is zero, and the three centroids form an arithmetic progression",
        "in some order. These exact checks make the partition matrix optimal for the",
        "k-means SDP (the dual construction in Section 3 of the source paper).",
        "",
        "Points:",
    ]
    lines.extend(f"  {i}: {_format_point(p)}" for i, p in enumerate(inst["points"]))
    lines.extend([
        "",
        "Cluster order is irrelevant. Inside the answer, sort every cluster's indices",
        "in increasing order and sort the three cluster lists lexicographically.",
        "Give your final answer inside <answer></answer> tags as one JSON object",
        "with exactly the key \"clusters\" and three lists of n indices.",
        "Example format: <answer>{\"clusters\":[[0,3],[1,4],[2,5]]}</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*|\s*```$", "", body,
                  flags=re.IGNORECASE | re.DOTALL).strip()
    try:
        obj = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(obj, dict) or set(obj) != {"clusters"}:
        return None
    groups = obj.get("clusters")
    if not isinstance(groups, list) or any(not isinstance(g, list) for g in groups):
        return None
    if any(any(isinstance(x, bool) or not isinstance(x, int) for x in g)
           for g in groups):
        return None
    return obj


# ---------------------------------------------------------------------------
# Bounded language, attacks, invariance, and measurements


def random_candidate(inst: dict, rng: random.Random) -> object:
    order = list(range(len(inst["points"])))
    rng.shuffle(order)
    n = inst["n"]
    return {"clusters": _canonical_clusters(
        [order[a * n:(a + 1) * n] for a in range(3)])}


def search_space(inst: dict) -> int:
    n = inst["n"]
    return math.factorial(3 * n) // (math.factorial(n) ** 3 * math.factorial(3))


def _balanced_partitions(items: tuple[int, ...], n: int, k: int):
    if k == 1:
        if len(items) == n:
            yield [list(items)]
        return
    first = items[0]
    for rest in itertools.combinations(items[1:], n - 1):
        block = (first,) + rest
        chosen = set(block)
        remaining = tuple(x for x in items if x not in chosen)
        for tail in _balanced_partitions(remaining, n, k - 1):
            yield [list(block)] + tail


def enumerate_all(inst: dict) -> int | None:
    if search_space(inst) > 50_000:
        return None
    count = 0
    for groups in _balanced_partitions(tuple(range(len(inst["points"]))),
                                       inst["n"], inst["k"]):
        ok, _ = verify(inst, {"clusters": _canonical_clusters(groups)})
        count += int(ok)
    return count


def canonical_key(inst: dict) -> str:
    """Scale/isometry/translation/point-order invariant distance-spectrum key."""
    points = inst["points"]
    distances = [_point_dist2(points[i], points[j])
                 for i in range(len(points)) for j in range(i + 1, len(points))]
    nonzero = [d for d in distances if d]
    base = min(nonzero) if nonzero else 1
    normalized = sorted((Fraction(d, base).numerator,
                         Fraction(d, base).denominator) for d in distances)
    payload = json.dumps({"k": inst["k"], "n": inst["n"], "d": normalized},
                         separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    p = {k: v for k, v in params.items() if k != "_preset"}
    p["coord_bits"] = min(60, int(p.get("coord_bits", 12)) + 8)
    p["radius_bits"] = min(60, int(p.get("radius_bits", 12)) + 8)
    if p["coord_bits"] == int(params.get("coord_bits", 12)):
        return "cap_bound"
    return p


def _answer_from_order(inst: dict, order: list[int]) -> dict:
    n = inst["n"]
    return {"clusters": _canonical_clusters(
        [order[a * n:(a + 1) * n] for a in range(3)])}


def _attack_coordinate(inst: dict, coordinate: int) -> dict:
    return _answer_from_order(inst, sorted(range(len(inst["points"])),
                                           key=lambda i: (inst["points"][i][coordinate], i)))


def _attack_first_coordinate(inst: dict) -> dict:
    return _attack_coordinate(inst, 0)


def _attack_coordinate_sum(inst: dict) -> dict:
    return _answer_from_order(inst, sorted(range(len(inst["points"])), key=lambda i: (
        sum(inst["points"][i]), i)))


def _attack_norm(inst: dict) -> dict:
    return _answer_from_order(inst, sorted(range(len(inst["points"])), key=lambda i: (
        sum(x * x for x in inst["points"][i]), i)))


def _attack_nearest_seed(inst: dict) -> dict:
    unused = set(range(len(inst["points"])))
    groups = []
    while unused:
        seed = min(unused)
        block = sorted(unused, key=lambda i: (_point_dist2(
            inst["points"][seed], inst["points"][i]), i))[:inst["n"]]
        groups.append(block)
        unused.difference_update(block)
    return {"clusters": _canonical_clusters(groups)}


def _reference_recover(inst: dict) -> tuple[dict, int]:
    """The disclosed polynomial-time construction-aware recovery algorithm."""
    points = inst["points"]
    N = len(points)
    # mean mu; the construction has mu=P(d), hence d=P^{-1}(mu).
    dimension = inst["dimension"]
    sums = [sum(p[j] for p in points) for j in range(dimension)]
    mu = [Fraction(x, N) for x in sums]
    d = _uncycle(mu)
    scores = [(sum((d[j] * points[i][j] for j in range(dimension)),
                   Fraction(0)), i) for i in range(N)]
    order = [i for _, i in sorted(scores)]
    # 3(N-1) sums, 3 divisions, per point 3 subtracts + 3 multiplies +
    # 2 additions, and two balanced-bucket comparisons per point.
    operations = dimension * N + N * (2 * dimension - 1)
    return _answer_from_order(inst, order), operations


def _atoms(obj: object) -> int:
    if isinstance(obj, dict):
        return sum(_atoms(v) for v in obj.values())
    if isinstance(obj, list):
        return sum(_atoms(v) for v in obj)
    return 1


def _permute_instance(inst: dict, new_to_old: list[int]) -> tuple[dict, dict]:
    old_to_new = {old: new for new, old in enumerate(new_to_old)}
    out = dict(inst)
    out["points"] = [inst["points"][old][:] for old in new_to_old]
    carried = {"clusters": _canonical_clusters(
        [[old_to_new[i] for i in group] for group in inst["answer"]["clusters"]])}
    out["answer"] = carried
    return out, carried


def _isometric_instance(inst: dict, perm: tuple[int, ...],
                        signs: tuple[int, ...], shift: tuple[int, ...]) -> dict:
    out = dict(inst)
    dimension = inst["dimension"]
    out["points"] = [[3 * signs[j] * p[perm[j]] + shift[j] for j in range(dimension)]
                     for p in inst["points"]]
    out["answer"] = json.loads(json.dumps(inst["answer"]))
    return out


def selftest() -> dict:
    report: dict = {}

    # G1: every preset and three seeds.
    g1_total = 0
    for params in DIFFICULTY.values():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            assert ok, (params, seed, why)
            g1_total += 1
    report["G1_planted_verifies"] = {"pass": True, "verified": g1_total,
                                      "attempts": g1_total}

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **ship_params)
    planted = json.loads(json.dumps(inst["answer"]))

    # G2: corruption paths intentionally exercise distinct rejection reasons.
    corruptions: dict[str, object] = {}
    a = json.loads(json.dumps(planted)); a["clusters"][0].pop()
    corruptions["drop_one"] = a
    a = json.loads(json.dumps(planted))
    a["clusters"][0][0], a["clusters"][1][0] = a["clusters"][1][0], a["clusters"][0][0]
    corruptions["swap_memberships"] = a
    a = json.loads(json.dumps(planted)); a["clusters"][0][0] = a["clusters"][0][1]
    corruptions["duplicate"] = a
    corruptions["empty"] = []
    a = json.loads(json.dumps(planted)); a["clusters"][0][0] = len(inst["points"])
    corruptions["out_of_range"] = a
    reasons = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        assert not ok, name
        reasons[name] = why
    assert len(set(reasons.values())) == len(reasons), reasons
    report["G2_rejects_corruption"] = {"pass": True, "rejected": len(reasons),
                                        "distinct_reasons": len(set(reasons.values())),
                                        "reasons": reasons}

    # G3: exact tagged-JSON round trip with ordinary surrounding prose.
    body = json.dumps(planted, separators=(",", ":"))
    model_reply = "I used the dual slack test.\n```json\n<answer>" + body + "</answer>\n```"
    parsed = parse_answer(model_reply)
    assert parsed == planted and parse_answer("no tagged witness") is None
    report["G3_round_trip"] = {"pass": True, "realistic_reply": True,
                                "garbage_returns_none": True}

    # G4 and shipping density: uniform over the exact unlabeled balanced language.
    rng = random.Random(880301)
    guesses = 200_000
    hits = 0
    for _ in range(guesses):
        candidate = random_candidate(inst, rng)
        ok, _ = verify(inst, candidate)
        hits += int(ok)
    assert hits / guesses < 1e-6
    report["G4_guess_resistance"] = {
        "pass": True, "hits": hits, "total": guesses,
        "observed_probability": hits / guesses,
        "candidate_space": search_space(inst),
        "sampling_prior": "uniform unlabeled balanced 3-partitions",
    }

    # Reference algorithm: expected to solve on Track B; time includes exact cert.
    ref_attempts = 8
    ref_successes = 0
    ref_operations = []
    ref_elapsed = []
    for seed in range(3100, 3100 + ref_attempts):
        x = make_instance(seed=seed, **ship_params)
        t0 = time.perf_counter()
        candidate, recovery_ops = _reference_recover(x)
        ok, _ = verify(x, candidate)
        ref_elapsed.append(time.perf_counter() - t0)
        N = len(x["points"])
        # Conservative counted primitive exact operations in distance/M/LDL work.
        certificate_ops = (N * (N - 1) // 2) * 8 + 12 * N * N + N ** 3
        ref_operations.append(recovery_ops + certificate_ops)
        ref_successes += int(ok)
    assert ref_successes == ref_attempts

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    assert isinstance(demo_count, int) and demo_count >= 1
    report["G5_density_and_baseline_cost"] = {
        "pass": True,
        "shipping_density_hits": hits,
        "shipping_density_samples": guesses,
        "shipping_density_estimate": hits / guesses,
        "demo_exact_valid_answers": demo_count,
        "demo_candidate_space": search_space(demo),
        "baseline_wall_clock_sec_mean": sum(ref_elapsed) / len(ref_elapsed),
        "baseline_wall_clock_sec_max": max(ref_elapsed),
        "baseline_operations_mean": sum(ref_operations) / len(ref_operations),
        "baseline_attempts": ref_attempts,
        "baseline_successes": ref_successes,
    }

    # G6: construction-aware cheap failures. The polynomial reference is separate.
    attack_counts = {
        "outlier_any_single_coordinate_tertiles": [0, 0],
        "outlier_squared_norm_tertiles": [0, 0],
        "greedy_nearest_seed": [0, 0],
        "by_hand_coordinate_sum_tertiles": [0, 0],
        "random_balanced_restart_256": [0, 0],
    }
    for seed in range(4100, 4108):
        x = make_instance(seed=seed, **ship_params)
        fixed = {
            "outlier_squared_norm_tertiles": _attack_norm(x),
            "greedy_nearest_seed": _attack_nearest_seed(x),
            "by_hand_coordinate_sum_tertiles": _attack_coordinate_sum(x),
        }
        coordinate_ok = False
        for coordinate in range(x["dimension"]):
            ok, _ = verify(x, _attack_coordinate(x, coordinate))
            coordinate_ok = coordinate_ok or ok
        attack_counts["outlier_any_single_coordinate_tertiles"][0] += int(coordinate_ok)
        attack_counts["outlier_any_single_coordinate_tertiles"][1] += 1
        for name, candidate in fixed.items():
            ok, _ = verify(x, candidate)
            attack_counts[name][0] += int(ok)
            attack_counts[name][1] += 1
        rr_ok = False
        rr_rng = random.Random(seed ^ 0x515151)
        for _ in range(256):
            candidate = random_candidate(x, rr_rng)
            ok, _ = verify(x, candidate)
            if ok:
                rr_ok = True
                break
        attack_counts["random_balanced_restart_256"][0] += int(rr_ok)
        attack_counts["random_balanced_restart_256"][1] += 1
    attacks = {name: {"successes": values[0], "attempts": values[1]}
               for name, values in attack_counts.items()}
    all_failed = all(v["successes"] == 0 and v["attempts"] >= 8
                     for v in attacks.values())
    assert all_failed, attacks
    report["G6_adversary_panel"] = {
        "pass": True,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "mean-projection recovery followed by the paper's exact dual check",
            "complexity": "O(Nm + N log N + N^3) exact",
            "wall_clock_sec_mean": sum(ref_elapsed) / len(ref_elapsed),
            "wall_clock_sec_max": max(ref_elapsed),
            "operations_mean": sum(ref_operations) / len(ref_operations),
            "solves": f"{ref_successes}/{ref_attempts}, as expected",
        },
    }

    # G7: double the cluster size while leaving the answer language unchanged.
    doubled = dict(ship_params)
    doubled["n"] *= 2
    bigger = make_instance(seed=777, **doubled)
    ok, why = verify(bigger, bigger["answer"])
    assert ok, why
    report["G7_scales"] = {
        "pass": True, "shipping_points": len(inst["points"]),
        "doubled_points": len(bigger["points"]),
        "shipping_search_space": search_space(inst),
        "doubled_search_space": search_space(bigger),
    }

    # G8: point relabels, signed coordinate permutations, translations, compositions.
    invariant_checks = 0
    real_transform_checks = 0
    keys = []
    for seed in range(20):
        x = make_instance(seed=5000 + seed, **ship_params)
        key = canonical_key(x)
        keys.append(key)
        prng = random.Random(seed)
        order = list(range(len(x["points"]))); prng.shuffle(order)
        xp, carried = _permute_instance(x, order)
        assert canonical_key(xp) == key
        ok, why = verify(xp, carried); assert ok, why
        invariant_checks += 1; real_transform_checks += 1
        dimension = x["dimension"]
        perm = tuple(prng.sample(range(dimension), dimension))
        signs = tuple(prng.choice((-1, 1)) for _ in range(dimension))
        shift = tuple(prng.randint(-1000, 1000) for _ in range(dimension))
        xi = _isometric_instance(xp, perm, signs, shift)
        assert canonical_key(xi) == key
        ok, why = verify(xi, xi["answer"]); assert ok, why
        invariant_checks += 1; real_transform_checks += 1
    assert len(set(keys)) == len(keys)
    report["G8_canonical_key"] = {
        "pass": True, "invariance_checks": invariant_checks,
        "real_transform_verifications": real_transform_checks,
        "unrelated_distinct": len(set(keys)), "unrelated_attempts": len(keys),
        "invariances": ["point relabeling", "coordinate permutation",
                        "coordinate sign changes", "global translation",
                        "uniform scale normalization"],
    }

    blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _atoms(inst["answer"])
    intended_ops = 11 * len(inst["points"])
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    assert within_caps
    arms = {k: dict(v) for k, v in G9_EVIDENCE.items()
            if k in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "diagnostic_not_gated": True,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
    }
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
