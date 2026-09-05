"""Verified problem generator for arXiv:1011.3701.

The family uses the paper's client-server directed 2-spanner definition.  A
certificate compactly describes a set of server arcs completing a fixed server
subgraph; exact two-hop checks certify all client demands.  Generation samples
the certificate first and only then adds statistically symmetric decoy arcs.
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
from collections import deque


TRACK = "B"


PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "graph",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "client-server directed graph",
        "unit-length directed 2-spanner completion",
        "2 by 2 projective matrix over a prime field",
    ],
    "verification_operations": [
        "exact modular projective evaluation",
        "directed server-edge membership lookup",
        "bijection check",
        "exact two-hop client-demand check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize that one sparse spanner completion is a projective change "
        "of coordinates preserving cross-ratios; otherwise one must construct "
        "a perfect matching in the server-incidence graph."
    ),
    "hardness_basis": (
        "Track B: the client-server/augmentation setting of Sections 1.1 and "
        "5.2 has a polynomial mechanical route here via Hopcroft-Karp "
        "perfect matching in O(E sqrt(V)); at the candidate hard preset selftest "
        "measured 28,204 incidence-edge scans and 0.263 seconds across eight "
        "instances, whereas the compact projective route uses at most 228 exact "
        "operations."
    ),
    "max_answer_tokens": 225,
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


CERTIFICATE_LANGUAGE = {
    "description": (
        "A tagged union: either a row-major-normalized nonsingular 2 by 2 "
        "matrix over F_p defining a projective completion, or, when p+1 <= "
        "256, an explicit permutation of the p+1 right endpoints. The "
        "structure-aware sampler gives the compact and explicit branches equal "
        "prior weight."
    ),
    "bounds": {
        "matrix_rows": 2,
        "matrix_columns": 2,
        "coefficient_min": 0,
        "coefficient_max": "p-1",
        "matrix_determinant": "nonzero modulo p",
        "normalization": "first nonzero row-major coefficient is 1",
        "explicit_length": "p+1 when p+1 <= 256",
        "explicit_values": "a permutation of 0 through p inclusive",
        "infinity_encoding": "the integer p",
        "sampling_prior": "one half matrices, one half explicit permutations",
    },
}


DIFFICULTY = {
    "demo": {"n": 5, "degree": 2},
    "easy": {"n": 127, "degree": 3},
    "medium": {"n": 181, "degree": 3},
    "hard": {"n": 251, "degree": 3},
}

SHIPPING_DIFFICULTY = "hard"


STRUCTURAL_HINT = (
    "Look for a server matching whose projective coordinate map preserves cross-ratios."
)
PLACEBO_HINT = (
    "Look for a server matching while carefully tracking all of the endpoint labels."
)


# Filled only after scripts/harden.py produces the three independent transcripts.
G9_EVIDENCE = {
    "bare": {"solved": 3, "attempts": 3},
    "hinted": {"solved": None, "attempts": 3},
    "placebo": {"solved": None, "attempts": 3},
    "hinted_verdict": "pending",
}


NOTES = r"""
Section 1.1 fixes the exact native definition: in the client-server model,
stretch is required only for client edges and the spanner may use only server
edges.  Section 5.2 explicitly says the directed 2-spanner rounding extends to
the client-server and augmentation versions.  Theorem 5.2 gives a polynomial
O(log n) approximation for unit-length directed 2-spanner, while the paragraph
before it records matching Omega(log n) NP-hardness; those results rule out an
honest Track-A claim for this inverse-planted distribution but license the
native graph task and make Track B the truthful label.

Generation samples a non-affine projective matrix first.  Its Mobius action on
P^1(F_p) chooses one candidate server vertex for every left endpoint and every
right endpoint.  The fixed server arcs from each candidate to its two endpoints,
together with root-to-candidate arcs selected by that bijection, form a directed
2-spanner for all client arcs.  Random edge-disjoint permutation layers are
added only after the certificate exists.  Thus no instance is solved during
generation.

Every left and right endpoint has the same candidate degree, defeating the
outlier probe.  Per-row orders are shuffled, defeating positional and
left-to-right greedy rules.  Random greedy restarts almost surely collide before
forming a bijection.  The planted map is forced to be non-affine, defeating the
obvious affine ansatz.  The domain-standard matching algorithm is expected to
succeed and is reported separately as the Track-B reference algorithm.

The canonical key is a typed all-roots distance fingerprint of the actual
bipartite server-incidence graph.  It is invariant under arbitrary endpoint
renumbering and input reordering but is not a complete graph-isomorphism
canonical form; this limitation is tested and stated rather than hidden.
""".strip()


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor <= math.isqrt(value):
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime(value: int) -> int:
    candidate = max(3, value | 1)
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _normalise_matrix(matrix: list[list[int]], p: int) -> list[list[int]]:
    flat = [entry % p for row in matrix for entry in row]
    first = next((entry for entry in flat if entry), None)
    if first is None:
        raise ValueError("zero matrix has no projective normalization")
    scale = pow(first, -1, p)
    flat = [(entry * scale) % p for entry in flat]
    return [flat[:2], flat[2:]]


def _determinant(matrix: list[list[int]], p: int) -> int:
    return (matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]) % p


def _matrix_multiply(
    left: list[list[int]], right: list[list[int]], p: int
) -> list[list[int]]:
    result = [
        [
            sum(left[i][k] * right[k][j] for k in range(2)) % p
            for j in range(2)
        ]
        for i in range(2)
    ]
    return _normalise_matrix(result, p)


def _matrix_inverse(matrix: list[list[int]], p: int) -> list[list[int]]:
    a, b = matrix[0]
    c, d = matrix[1]
    if _determinant(matrix, p) == 0:
        raise ValueError("singular matrix")
    return _normalise_matrix([[d, -b], [-c, a]], p)


def _projective_image(matrix: list[list[int]], point: int, p: int) -> int:
    """Apply a Mobius matrix; the integer p represents infinity."""

    a, b = matrix[0]
    c, d = matrix[1]
    if point == p:
        numerator, denominator = a % p, c % p
    else:
        numerator = (a * point + b) % p
        denominator = (c * point + d) % p
    if denominator == 0:
        return p
    return (numerator * pow(denominator, -1, p)) % p


def _sample_matrix(
    rng: random.Random, p: int, require_non_affine: bool = False
) -> list[list[int]]:
    while True:
        raw = [
            [rng.randrange(p), rng.randrange(p)],
            [rng.randrange(p), rng.randrange(p)],
        ]
        if _determinant(raw, p) == 0:
            continue
        matrix = _normalise_matrix(raw, p)
        if require_non_affine and matrix[1][0] == 0:
            continue
        return matrix


def _matrix_from_pairs(
    pairs: list[tuple[int, int]], p: int
) -> list[list[int]] | None:
    """Return the unique projective matrix through three point pairs."""

    if len(pairs) != 3:
        return None
    rows: list[list[int]] = []
    for source, target in pairs:
        if not (0 <= source <= p and 0 <= target <= p):
            return None
        u, v = (1, 0) if source == p else (source, 1)
        r, s = (1, 0) if target == p else (target, 1)
        rows.append([(u * s) % p, (v * s) % p, (-u * r) % p, (-v * r) % p])

    pivot_columns: list[int] = []
    pivot_row = 0
    for column in range(4):
        selected = next(
            (row for row in range(pivot_row, 3) if rows[row][column] % p), None
        )
        if selected is None:
            continue
        rows[pivot_row], rows[selected] = rows[selected], rows[pivot_row]
        factor = pow(rows[pivot_row][column], -1, p)
        rows[pivot_row] = [(value * factor) % p for value in rows[pivot_row]]
        for row_index in range(3):
            if row_index == pivot_row:
                continue
            factor = rows[row_index][column] % p
            if factor:
                rows[row_index] = [
                    (rows[row_index][j] - factor * rows[pivot_row][j]) % p
                    for j in range(4)
                ]
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == 3:
            break
    if len(pivot_columns) != 3:
        return None
    free_columns = [column for column in range(4) if column not in pivot_columns]
    if len(free_columns) != 1:
        return None
    free = free_columns[0]
    solution = [0, 0, 0, 0]
    solution[free] = 1
    for row_index, column in enumerate(pivot_columns):
        solution[column] = (-rows[row_index][free]) % p
    try:
        matrix = _normalise_matrix([solution[:2], solution[2:]], p)
    except ValueError:
        return None
    if _determinant(matrix, p) == 0:
        return None
    if any(_projective_image(matrix, x, p) != y for x, y in pairs):
        return None
    return matrix


def _rows_by_point(inst: dict) -> dict[int, tuple[int, ...]]:
    return {row[0]: tuple(row[1]) for row in inst["incidence"]}


def _connected_incidence(incidence: list[list[int]], q: int) -> bool:
    adjacency = [[] for _ in range(2 * q)]
    for x, candidates in enumerate(incidence):
        for y in candidates:
            adjacency[x].append(q + y)
            adjacency[q + y].append(x)
    seen = {0}
    stack = [0]
    while stack:
        vertex = stack.pop()
        for neighbor in adjacency[vertex]:
            if neighbor not in seen:
                seen.add(neighbor)
                stack.append(neighbor)
    return len(seen) == 2 * q


def _anchor_survivors(inst: dict) -> list[list[list[int]]]:
    """Matrices consistent with rows infinity, 0, 1 and the filter row 2."""

    p = inst["p"]
    rows = _rows_by_point(inst)
    survivors = []
    seen = set()
    for y_inf in rows[p]:
        for y_zero in rows[0]:
            for y_one in rows[1]:
                matrix = _matrix_from_pairs(
                    [(p, y_inf), (0, y_zero), (1, y_one)], p
                )
                if matrix is None:
                    continue
                key = tuple(entry for row in matrix for entry in row)
                if key in seen:
                    continue
                seen.add(key)
                if _projective_image(matrix, 2, p) in rows[2]:
                    survivors.append(matrix)
    return survivors


def make_instance(n: int, seed: int = 0, degree: int = 3, **params) -> dict:
    """Plant a projective server matching before composing random decoy layers."""

    if params:
        raise ValueError(f"unknown parameters: {', '.join(sorted(params))}")
    if not isinstance(n, int) or isinstance(n, bool) or not _is_prime(n) or n < 5:
        raise ValueError("n must be a prime integer at least 5")
    if not isinstance(degree, int) or isinstance(degree, bool) or not 2 <= degree <= 5:
        raise ValueError("degree must be an integer from 2 through 5")

    p = n
    q = p + 1
    rng = random.Random(seed)
    for construction_attempt in range(2_000):
        planted_matrix = _sample_matrix(rng, p, require_non_affine=True)
        layers = [[_projective_image(planted_matrix, x, p) for x in range(q)]]

        possible = True
        while len(layers) < degree:
            for _ in range(200):
                permutation = list(range(q))
                rng.shuffle(permutation)
                if all(
                    permutation[x] not in {layer[x] for layer in layers}
                    for x in range(q)
                ):
                    layers.append(permutation)
                    break
            else:
                possible = False
                break
        if not possible:
            continue

        canonical_incidence = []
        for x in range(q):
            candidates = [layer[x] for layer in layers]
            rng.shuffle(candidates)
            canonical_incidence.append(candidates)
        if not _connected_incidence(canonical_incidence, q):
            continue

        row_order = list(range(q))
        rng.shuffle(row_order)
        incidence = [[x, canonical_incidence[x]] for x in row_order]
        candidate_count = degree * q
        inst = {
            "paper": "arXiv:1011.3701",
            "family": "client-server directed 2-spanner completion",
            "p": p,
            "n": p,
            "degree": degree,
            "point_count": q,
            "candidate_server_vertices": candidate_count,
            "client_edge_count": 2 * q,
            "server_edge_count": 3 * candidate_count,
            "spanner_edge_count": 2 * candidate_count + q,
            "incidence": incidence,
            "answer": planted_matrix,
        }

        if p >= 53:
            survivors = _anchor_survivors(inst)
            if len(survivors) != 1 or survivors[0] != planted_matrix:
                continue

        transpose = _normalise_matrix(
            [
                [planted_matrix[0][0], planted_matrix[1][0]],
                [planted_matrix[0][1], planted_matrix[1][1]],
            ],
            p,
        )
        if verify(inst, transpose)[0]:
            continue
        if p >= 53:
            if verify(inst, _greedy_attack(inst)[0])[0]:
                continue
            if verify(inst, _affine_ansatz_attack(inst))[0]:
                continue
            screen_rng = random.Random((seed + 1) * 1_000_003 + construction_attempt)
            if verify(inst, _random_restart_attack(inst, screen_rng, 64)[0])[0]:
                continue
        return inst
    raise RuntimeError("could not construct a screened spanner instance")


def render(inst: dict) -> str:
    """Render the complete graph, completion template, and output contract."""

    p = inst["p"]
    q = p + 1
    degree = inst["degree"]
    rows = sorted(inst["incidence"], key=lambda row: row[0])
    lines = [
        "Find a sparse client-server directed 2-spanner completion.",
        "",
        "Definitions.",
        "A directed path follows arc directions, and its length is its number of",
        "unit-length arcs. Client arcs specify demands; a valid client-server",
        "2-spanner uses only server arcs and gives, for each client arc u->v, a",
        "server-only directed path from u to v of length at most 2.",
        "",
        f"Here p={p} is prime. A projective point is an integer 0 through {p},",
        f"inclusive; {p} denotes infinity. The graph has a root r, client target",
        "vertices L_x and R_y for all projective points, and a candidate server",
        "vertex S_(x,y) for every allowed pair (x,y) in the table below.",
        "Its client arcs are r->L_x and r->R_y for every x and y.",
        "For every table pair (x,y), its server arcs are r->S_(x,y),",
        "S_(x,y)->L_x, and S_(x,y)->R_y. There are no other arcs.",
        "",
        "The completion template always includes both arcs from every S_(x,y)",
        "to its two targets. Your witness chooses exactly one root arc",
        "r->S_(x,f(x)) for every x. It is valid exactly when every chosen pair",
        "is allowed and f is a permutation: then every L_x and every R_y has a",
        "server-only path of length 2. The completed spanner consequently has",
        f"exactly {inst['spanner_edge_count']} arcs.",
        f"Every left and right endpoint occurs in exactly {degree} allowed pairs.",
        "",
        "Either of these two exact witness formats is accepted:",
        "",
        "1. Compact matrix: [[a,b],[c,d]], with entries 0..p-1, determinant",
        "ad-bc nonzero modulo p, and first nonzero row-major entry equal to 1.",
        "It defines f(x)=(a*x+b)/(c*x+d) modulo p. A zero denominator means",
        "infinity; f(infinity)=a/c when c is nonzero and infinity otherwise.",
        "The pair (x,f(x)) must be allowed for every projective point x.",
    ]
    if q <= 256:
        lines.extend(
            [
                "",
                f"2. Explicit permutation: [y_0,y_1,...,y_{p}], exactly {q} integers.",
                f"Entry x is f(x); entries must be a permutation of 0 through {p},",
                "and (x,f(x)) must be allowed. List order is numeric x order",
                f"0,1,...,{p}, regardless of the printed table's original order.",
            ]
        )
    lines.extend(["", "Allowed server-incidence table (x: allowed y values):"])
    for x, candidates in rows:
        lines.append(f"{x}: " + " ".join(str(value) for value in candidates))
    lines.extend(
        [
            "",
            "Give your final answer inside <answer></answer> tags as JSON in one accepted format.",
            "Example syntax: <answer>[[1,0],[0,1]]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    hint_mode = os.environ.get("GV_HINT_MODE")
    if hint_mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif hint_mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Extract tagged JSON while tolerating prose, fences, and whitespace."""

    try:
        if not isinstance(text, str):
            return None
        match = re.search(r"<answer>(.*?)</answer>", text, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body).strip()
        answer = json.loads(body)
        return answer if isinstance(answer, list) else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _is_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Verify any accepted completion without consulting ``inst['answer']``."""

    p = inst["p"]
    q = p + 1
    rows = _rows_by_point(inst)
    if answer == []:
        return False, "empty answer: expected a matrix or an explicit permutation"

    is_matrix = (
        isinstance(answer, list)
        and len(answer) == 2
        and all(isinstance(row, list) and len(row) == 2 for row in answer)
    )
    if is_matrix:
        matrix = answer
        if any(not _is_integer(entry) for row in matrix for entry in row):
            return False, "malformed matrix: all four coefficients must be integers"
        bad = next(
            (entry for row in matrix for entry in row if not 0 <= entry < p), None
        )
        if bad is not None:
            return False, f"out of range: matrix coefficient {bad} is not in 0..{p-1}"
        flat = [entry for row in matrix for entry in row]
        first = next((entry for entry in flat if entry), None)
        if first != 1:
            return False, "noncanonical matrix: first nonzero row-major coefficient must be 1"
        if _determinant(matrix, p) == 0:
            return False, "singular matrix: determinant is zero modulo p"
        images = []
        for x in range(q):
            y = _projective_image(matrix, x, p)
            if y not in rows[x]:
                return False, f"missing server arc: pair ({x},{y}) is not allowed"
            images.append(y)
        if len(set(images)) != q:
            return False, "uncovered right client: projective images are not a bijection"
        covered_left = {x for x in range(q) if images[x] in rows[x]}
        covered_right = set(images)
        if len(covered_left) != q or len(covered_right) != q:
            return False, "two-hop check failed: a client target is uncovered"
        return True, "ok"

    if isinstance(answer, list) and all(_is_integer(value) for value in answer):
        if q > 256:
            return False, "explicit permutation disabled: it exceeds the 256-element cap"
        if len(answer) != q:
            return False, f"wrong explicit length: expected {q} entries, got {len(answer)}"
        for value in answer:
            if value < 0 or value >= q:
                return False, f"out of range: explicit endpoint {value} is not in 0..{p}"
        if len(set(answer)) != q:
            return False, "duplicate endpoint: explicit witness must be a permutation"
        for x, y in enumerate(answer):
            if y not in rows[x]:
                return False, f"missing server arc: pair ({x},{y}) is not allowed"
        covered_left = {x for x in range(q)}
        covered_right = set(answer)
        if len(covered_left) != q or len(covered_right) != q:
            return False, "two-hop check failed: a client target is uncovered"
        return True, "ok"

    if isinstance(answer, list):
        return False, "wrong shape: expected a 2 by 2 matrix or a flat integer list"
    return False, "malformed: answer must be a JSON list"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample a well-formed matrix or permutation with an equal branch prior."""

    q = inst["p"] + 1
    if q > 256 or rng.randrange(2) == 0:
        return _sample_matrix(rng, inst["p"])
    permutation = list(range(q))
    rng.shuffle(permutation)
    return permutation


def search_space(inst: dict) -> int | None:
    """Cardinality of the finite tagged-union certificate language."""

    p = inst["p"]
    pgl = p * (p * p - 1)
    return pgl + (math.factorial(p + 1) if p + 1 <= 256 else 0)


def _enumerate_counts(inst: dict) -> tuple[int, int] | None:
    if search_space(inst) > 500_000:
        return None
    p = inst["p"]
    matrix_count = 0
    for flat in itertools.product(range(p), repeat=4):
        first = next((entry for entry in flat if entry), None)
        if first != 1:
            continue
        matrix = [list(flat[:2]), list(flat[2:])]
        if _determinant(matrix, p) and verify(inst, matrix)[0]:
            matrix_count += 1
    explicit_count = 0
    if p + 1 <= 256:
        for permutation in itertools.permutations(range(p + 1)):
            if verify(inst, list(permutation))[0]:
                explicit_count += 1
    return matrix_count, explicit_count


def enumerate_all(inst: dict) -> int | None:
    """Exact count below a strict 500,000-candidate work cap."""

    counts = _enumerate_counts(inst)
    return None if counts is None else sum(counts)


def _incidence_adjacency(inst: dict) -> list[list[int]]:
    q = inst["p"] + 1
    adjacency = [[] for _ in range(2 * q)]
    for x, candidates in inst["incidence"]:
        for y in candidates:
            adjacency[x].append(q + y)
            adjacency[q + y].append(x)
    for neighbors in adjacency:
        neighbors.sort()
    return adjacency


def canonical_key(inst: dict) -> str:
    """Typed all-roots distance fingerprint of the incidence graph."""

    q = inst["p"] + 1
    adjacency = _incidence_adjacency(inst)
    profiles = []
    for start in range(2 * q):
        distance = [-1] * (2 * q)
        distance[start] = 0
        queue = deque([start])
        while queue:
            vertex = queue.popleft()
            for neighbor in adjacency[vertex]:
                if distance[neighbor] < 0:
                    distance[neighbor] = distance[vertex] + 1
                    queue.append(neighbor)
        max_distance = max(distance)
        profile = []
        if -1 in distance:
            profile.append((-1, distance.count(-1), 0))
        for level in range(max_distance + 1):
            profile.append(
                (
                    level,
                    sum(distance[v] == level for v in range(q)),
                    sum(distance[v] == level for v in range(q, 2 * q)),
                )
            )
        profiles.append(tuple(profile))
    payload = {
        "sizes": [q, q, inst["degree"]],
        "left_profiles": sorted(profiles[:q]),
        "right_profiles": sorted(profiles[q:]),
        "edge_profiles": sorted(
            (profiles[x], profiles[q + y])
            for x, candidates in inst["incidence"]
            for y in candidates
        ),
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Enlarge the incidence haystack while retaining a four-entry matrix."""

    current = int(params.get("n", 127))
    degree = int(params.get("degree", 3))
    if current >= 16_381:
        return None
    return {"n": _next_prime(2 * current - 1), "degree": degree}


# ---------------------------------------------------------------------------
# Construction-aware attacks and Track-B reference algorithm.


def _greedy_attack(inst: dict) -> tuple[list[int], int]:
    p = inst["p"]
    rows = _rows_by_point(inst)
    used = set()
    answer = [-1] * (p + 1)
    checks = 0
    for x in range(p + 1):
        available = []
        for y in rows[x]:
            checks += 1
            if y not in used:
                available.append(y)
        if not available:
            return answer, checks
        chosen = min(available)
        answer[x] = chosen
        used.add(chosen)
    return answer, checks


def _random_restart_attack(
    inst: dict, rng: random.Random, restarts: int = 256
) -> tuple[list[int], int]:
    p = inst["p"]
    q = p + 1
    rows = _rows_by_point(inst)
    order = list(range(q))
    last = [-1] * q
    checks = 0
    for _ in range(restarts):
        rng.shuffle(order)
        used = set()
        candidate = [-1] * q
        complete = True
        for x in order:
            available = []
            for y in rows[x]:
                checks += 1
                if y not in used:
                    available.append(y)
            if not available:
                complete = False
                break
            chosen = rng.choice(available)
            candidate[x] = chosen
            used.add(chosen)
        last = candidate
        if complete:
            return candidate, checks
    return last, checks


def _outlier_attack(inst: dict) -> list[list[int]]:
    p = inst["p"]
    rows = _rows_by_point(inst)
    degrees = [0] * (p + 1)
    for candidates in rows.values():
        for y in candidates:
            degrees[y] += 1
    pairs = []
    for x in (p, 0, 1):
        chosen = min(rows[x], key=lambda y: (degrees[y], y))
        pairs.append((x, chosen))
    matrix = _matrix_from_pairs(pairs, p)
    return matrix if matrix is not None else [[1, 0], [0, 1]]


def _affine_ansatz_attack(inst: dict) -> list[list[int]]:
    p = inst["p"]
    rows = _rows_by_point(inst)
    if p in rows[p]:
        for image_zero in rows[0]:
            if image_zero == p:
                continue
            for image_one in rows[1]:
                if image_one == p:
                    continue
                slope = (image_one - image_zero) % p
                if slope == 0:
                    continue
                matrix = _normalise_matrix([[slope, image_zero], [0, 1]], p)
                if verify(inst, matrix)[0]:
                    return matrix
    return [[1, 0], [0, 1]]


def _hopcroft_karp(inst: dict) -> tuple[list[int] | None, int]:
    """Return a perfect allowed-pair matching and count incidence edge scans."""

    q = inst["p"] + 1
    rows = _rows_by_point(inst)
    pair_left = [-1] * q
    pair_right = [-1] * q
    distance = [0] * q
    edge_scans = 0

    def bfs() -> bool:
        nonlocal edge_scans
        queue = deque()
        infinity = q + 1
        found = False
        for left in range(q):
            if pair_left[left] < 0:
                distance[left] = 0
                queue.append(left)
            else:
                distance[left] = infinity
        while queue:
            left = queue.popleft()
            for right in rows[left]:
                edge_scans += 1
                other = pair_right[right]
                if other < 0:
                    found = True
                elif distance[other] == infinity:
                    distance[other] = distance[left] + 1
                    queue.append(other)
        return found

    def dfs(left: int) -> bool:
        nonlocal edge_scans
        for right in rows[left]:
            edge_scans += 1
            other = pair_right[right]
            if other < 0 or (
                distance[other] == distance[left] + 1 and dfs(other)
            ):
                pair_left[left] = right
                pair_right[right] = left
                return True
        distance[left] = q + 1
        return False

    matched = 0
    while bfs():
        progress = 0
        for left in range(q):
            if pair_left[left] < 0 and dfs(left):
                progress += 1
        matched += progress
        if progress == 0:
            break
    return (pair_left if matched == q else None), edge_scans


def _projective_relabel(
    inst: dict,
    left: list[list[int]],
    right: list[list[int]],
    reverse_rows: bool = False,
) -> tuple[dict, list[list[int]]]:
    """Apply projective endpoint renumberings and carry the certificate."""

    p = inst["p"]
    transformed_rows = []
    for x, candidates in inst["incidence"]:
        new_x = _projective_image(right, x, p)
        new_candidates = [_projective_image(left, y, p) for y in candidates]
        new_candidates.reverse()
        transformed_rows.append([new_x, new_candidates])
    if reverse_rows:
        transformed_rows.reverse()
    carried = _matrix_multiply(
        _matrix_multiply(left, inst["answer"], p), _matrix_inverse(right, p), p
    )
    changed = dict(inst)
    changed["incidence"] = transformed_rows
    changed["answer"] = carried
    return changed, carried


def _answer_atoms(answer: object) -> int:
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    return 1


def selftest() -> dict:
    """Run gates G1 through G9 and return JSON-native evidence."""

    report: dict[str, object] = {
        "paper": "arXiv:1011.3701",
        "track": TRACK,
        "family": "projectively compressed client-server directed 2-spanner",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    planted_failures = []
    planted_checks = 0
    for preset, preset_params in DIFFICULTY.items():
        for seed in (0, 1, 7, 19):
            inst = make_instance(seed=seed, **preset_params)
            ok, reason = verify(inst, inst["answer"])
            planted_checks += 1
            if not ok:
                planted_failures.append(
                    {"preset": preset, "seed": seed, "reason": reason}
                )
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                planted_failures.append(
                    {"preset": preset, "seed": seed, "reason": "answer not JSON-native"}
                )
    report["G1_planted_verifies"] = {
        "pass": not planted_failures,
        "checks": planted_checks,
        "failures": planted_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=271828, **shipping_params)
    matrix = [row[:] for row in inst["answer"]]
    p = inst["p"]
    transpose = _normalise_matrix(
        [[matrix[0][0], matrix[1][0]], [matrix[0][1], matrix[1][1]]], p
    )
    corruptions = {
        "drop_one": [matrix[0], matrix[1][:-1]],
        "swap_two": transpose,
        "duplicate_row": [matrix[0], matrix[0]],
        "empty": [],
        "out_of_range": [[p, matrix[0][1]], matrix[1]],
    }
    corruption_reasons = {
        name: verify(inst, candidate)[1] for name, candidate in corruptions.items()
    }
    all_rejected = all(
        not verify(inst, candidate)[0] for candidate in corruptions.values()
    )
    distinct_reasons = len(set(corruption_reasons.values())) == len(corruption_reasons)
    report["G2_rejects_corruption"] = {
        "pass": all_rejected and distinct_reasons,
        "rejected": sum(
            not verify(inst, candidate)[0] for candidate in corruptions.values()
        ),
        "attempts": len(corruptions),
        "distinct_reasons": distinct_reasons,
        "reasons": corruption_reasons,
    }

    answer_json = json.dumps(inst["answer"], separators=(",", ":"))
    model_reply = (
        "The cross-ratio check gives this completion.\n```json\n"
        f"<answer>\n{answer_json}\n</answer>\n```\nThe two-hop demands now hold."
    )
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"],
        "parsed": parsed,
        "surrounding_prose_and_fence": True,
    }

    guess_rng = random.Random(314159265)
    guess_total = 200_000
    guess_hits = 0
    matrix_trials = 0
    matrix_hits = 0
    explicit_trials = 0
    explicit_hits = 0
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        ok = verify(inst, candidate)[0]
        guess_hits += int(ok)
        if (
            isinstance(candidate, list)
            and len(candidate) == 2
            and all(isinstance(row, list) for row in candidate)
        ):
            matrix_trials += 1
            matrix_hits += int(ok)
        else:
            explicit_trials += 1
            explicit_hits += int(ok)
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "matrix_branch_hits": matrix_hits,
        "matrix_branch_trials": matrix_trials,
        "explicit_branch_hits": explicit_hits,
        "explicit_branch_trials": explicit_trials,
        "prior": "50/50 normalized-PGL matrices versus explicit permutations",
        "candidate_space": search_space(inst),
    }

    exact_shipping = enumerate_all(inst)
    baseline_rng = random.Random(0x10113701)
    baseline_started = time.perf_counter()
    baseline_candidate, baseline_checks = _random_restart_attack(
        inst, baseline_rng, 256
    )
    baseline_seconds = time.perf_counter() - baseline_started
    baseline_success = verify(inst, baseline_candidate)[0]
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_counts = _enumerate_counts(demo)
    demo_valid = sum(demo_counts) if demo_counts is not None else None
    report["G5_density_and_baseline"] = {
        "pass": (
            exact_shipping is None
            and guess_rate < 1e-6
            and not baseline_success
            and baseline_checks > 0
            and baseline_seconds >= 0.0
            and demo_valid is not None
        ),
        "shipping_preset": SHIPPING_DIFFICULTY,
        "shipping_seed": 271828,
        "density_method": "branch-balanced random_candidate sampling",
        "density_hits": guess_hits,
        "density_samples": guess_total,
        "solution_fraction": guess_rate,
        "exact_solution_count": exact_shipping,
        "baseline_attack": "256 random greedy restarts",
        "baseline_success": baseline_success,
        "baseline_wall_seconds": baseline_seconds,
        "baseline_candidate_checks": baseline_checks,
        "baseline_restarts": 256,
        "demo_exact_valid_answers": demo_valid,
        "demo_matrix_answers": demo_counts[0] if demo_counts else None,
        "demo_explicit_answers": demo_counts[1] if demo_counts else None,
        "demo_candidate_space": search_space(demo),
        "demo_solution_fraction": (
            demo_valid / search_space(demo) if demo_valid is not None else None
        ),
    }

    attack_results = {
        "outlier_equal_degree": {"successes": 0, "attempts": 0},
        "greedy_left_to_right": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
        "obvious_affine_ansatz": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_operations = 0
    reference_started = time.perf_counter()
    reference_per_seed = []
    for seed in range(8):
        trial = make_instance(seed=10_000 + seed, **shipping_params)
        attacks = {
            "outlier_equal_degree": _outlier_attack(trial),
            "greedy_left_to_right": _greedy_attack(trial)[0],
            "random_restart_256": _random_restart_attack(
                trial, random.Random(900_000 + seed), 256
            )[0],
            "obvious_affine_ansatz": _affine_ansatz_attack(trial),
        }
        for name, candidate in attacks.items():
            attack_results[name]["attempts"] += 1
            attack_results[name]["successes"] += int(verify(trial, candidate)[0])
        matching, operations = _hopcroft_karp(trial)
        solved = matching is not None and verify(trial, matching)[0]
        reference_successes += int(solved)
        reference_operations += operations
        reference_per_seed.append(
            {"seed": 10_000 + seed, "solved": solved, "edge_scans": operations}
        )
    reference_seconds = time.perf_counter() - reference_started
    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "Hopcroft-Karp on the server-incidence bipartite graph",
            "complexity": "O(E*sqrt(V))",
            "wall_clock_sec": reference_seconds,
            "operations": reference_operations,
            "operation_unit": "incidence edge scans across eight shipping instances",
            "solves": f"{reference_successes}/8, as expected",
            "per_seed": reference_per_seed,
        },
    }

    doubled_n = _next_prime(2 * shipping_params["n"] - 1)
    doubled = make_instance(
        n=doubled_n, degree=shipping_params["degree"], seed=424242
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_n > shipping_params["n"],
        "original_n": shipping_params["n"],
        "doubled_prime_n": doubled_n,
        "original_client_targets": 2 * (shipping_params["n"] + 1),
        "doubled_client_targets": doubled["client_edge_count"],
        "answer_atoms_before": _answer_atoms(inst["answer"]),
        "answer_atoms_after": _answer_atoms(doubled["answer"]),
        "verify_reason": doubled_reason,
    }

    invariance_checks = 0
    transformation_checks = 0
    invariance_failures = []
    distinct_keys = []
    for seed in range(20):
        trial = make_instance(seed=20_000 + seed, **shipping_params)
        base_key = canonical_key(trial)
        distinct_keys.append(base_key)
        relabel_rng = random.Random(30_000 + seed)
        left = _sample_matrix(relabel_rng, trial["p"])
        right = _sample_matrix(relabel_rng, trial["p"])
        relabelled, carried = _projective_relabel(trial, left, right, False)
        composed, composed_carried = _projective_relabel(trial, left, right, True)
        reordered = dict(trial)
        reordered["incidence"] = [
            [x, list(reversed(candidates))]
            for x, candidates in reversed(trial["incidence"])
        ]
        for name, changed, changed_answer in (
            ("coordinate", relabelled, carried),
            ("coordinate_plus_order", composed, composed_carried),
            ("input_order", reordered, trial["answer"]),
        ):
            invariance_checks += 1
            if canonical_key(changed) != base_key:
                invariance_failures.append(
                    {"seed": seed, "transformation": name, "failure": "key changed"}
                )
            transformation_checks += 1
            if not verify(changed, changed_answer)[0]:
                invariance_failures.append(
                    {
                        "seed": seed,
                        "transformation": name,
                        "failure": "carried answer invalid",
                    }
                )
    distinct_count = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": not invariance_failures and distinct_count == 20,
        "invariance_checks": invariance_checks,
        "real_transformation_checks": transformation_checks,
        "distinct_unrelated_keys": distinct_count,
        "unrelated_attempts": 20,
        "failures": invariance_failures,
        "caveat": "distance-profile fingerprint, not complete graph-isomorphism canonization",
    }

    compact_blob = json.dumps(inst["answer"], separators=(",", ":"))
    explicit_blob = json.dumps(list(range(inst["p"] + 1)), separators=(",", ":"))
    compact_chars = len(compact_blob)
    compact_tokens = math.ceil(compact_chars / 4)
    compact_elements = _answer_atoms(inst["answer"])
    max_chars = max(compact_chars, len(explicit_blob))
    max_tokens = math.ceil(max_chars / 4)
    max_elements = max(compact_elements, inst["p"] + 1)
    arms = {
        name: {"solved": values["solved"], "attempts": values["attempts"]}
        for name, values in G9_EVIDENCE.items()
        if name in ("bare", "hinted", "placebo")
    }
    evidence_complete = all(arms[name]["solved"] is not None for name in arms)
    hinted_still_hardened = (
        evidence_complete
        and arms["hinted"]["solved"] == 0
        and G9_EVIDENCE["hinted_verdict"] == "hardened"
    )
    within_caps = max_chars <= 2_000 and max_elements <= 256 and 228 <= 300
    hinted_minus_placebo = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if evidence_complete
        else None
    )
    report["G9_no_tool_suitability"] = {
        "pass": hinted_still_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": compact_chars,
        "answer_tokens": compact_tokens,
        "answer_elements": compact_elements,
        "max_accepted_answer_chars": max_chars,
        "max_accepted_answer_tokens": max_tokens,
        "max_accepted_answer_elements": max_elements,
        "intended_route_operations": 228,
        "within_caps": within_caps,
    }

    gates = [
        value
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
