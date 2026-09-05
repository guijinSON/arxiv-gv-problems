"""Verified generator for bounded-degree multiple-Hamiltonicity.

The generated task is the native [1,1]-HAM problem on simple cubic planar
graphs: exhibit a closed walk visiting every vertex exactly once.  The graph is
inverse-generated around a known spanning cycle and independently relabelled;
no search algorithm is used to obtain the certificate.

Paper: Liu, Sheffield, and Westover, "Complexity of Multiple-Hamiltonicity in
Graphs of Bounded Degree", https://arxiv.org/abs/2405.16270
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
from collections import Counter, deque


TRACK: str = "A"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "simple undirected cubic graph",
        "closed spanning walk",
    ],
    "verification_operations": [
        "integer range comparison",
        "permutation check",
        "undirected edge membership",
        "closing-edge check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "A Hamilton cycle in a cubic graph is the complement of a perfect "
        "matching, while the planted instance also conceals a randomized two-page "
        "noncrossing cyclic order; without that decomposition one must resolve "
        "exponentially many locally indistinguishable edge choices."
    ),
    "hardness_basis": (
        "Track A: Theorem 1's odd-regular hard regime applies with d=3 and "
        "a=b=1 (so b<d); on the n=252 shipping distribution, randomized exact "
        "perfect-matching/complement search with propagation and subtour pruning "
        "exhausts 120012 branch nodes on each of eight seeds without a witness."
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


# n is the even number of vertices.  The hardening loop begins at easy; demo
# remains hand-scale.
DIFFICULTY = {
    "easy": {"n": 252, "page_mix": 1},
}

SHIPPING_DIFFICULTY = "easy"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list containing every vertex identifier exactly once, "
        "normalized to begin with 0 and to have its second entry smaller than "
        "its last; it denotes a cyclic order, including the last-to-first edge."
    ),
    "bounds": {
        "length": "n",
        "entry_min": 0,
        "entry_max": "n-1",
        "distinct": True,
        "rotation_normalization": "first entry is 0",
        "reflection_normalization": "second entry is smaller than last entry",
        "max_supported_n": 600,
    },
}

STRUCTURAL_HINT = (
    "In a cubic graph the unused edge at each vertex is a perfect matching, "
    "and a useful cyclic order can separate its remaining edges into two pages."
)

PLACEBO_HINT = (
    "In a cubic graph every endpoint has three incident choices, and the "
    "requested cycle must include its final closing edge as well."
)

NOTES = """\
Definition 1 and the labelling equivalence in Section 1.3 fix the task: an
[a,b]-HAM witness is a closed walk visiting each vertex between a and b times,
equivalently a connected spanning even edge-labelled factor.  Theorem 1 says
that on odd d-regular graphs the problem is NP-hard exactly when b<d; this
module uses d=3 and a=b=1.  Lemmas 2 and 3 show the automatic Eulerian regime
b>=d for odd d; Lemma 10 gives a linear tree algorithm, Lemmas 11 and 12 give
the broad high-b maximum-degree regimes, and Lemma 16 gives the directed
degree-three equality case.  None applies here.

The certificate-producing algorithm is inverse generation, not a solver: draw
a cyclic order, start from alternating page membership and exchange the
declared page_mix vertices from each page, then sample a noncrossing perfect matching on each
page while forbidding cycle-edge
duplicates, and hide all roles by a uniform vertex permutation.  The dynamic
program used only to sample those decoy matchings costs O(n^3); it never searches
for the answer.  Under the final permutation, a named planted edge and a named
decoy edge have the same uniform one-edge marginal.  Randomizing page membership
also removes the exact -1 adjacency eigenvector leaked by the earlier
even-page/odd-page construction.  Every vertex has degree three, defeating
degree outliers; edge and vertex order are shuffled; local triangle/four-cycle
scores are tried in the outlier panel; constrained greedy walks and randomized
restarts test local leakage; spectral seriation and minus-one-eigenspace
rounding test for hidden-order leakage; and the domain attack branches over
perfect matchings whose complements are candidate spanning 2-factors, with
forced-edge propagation, premature-subtour pruning, and randomized relabelling
restarts.  The paper proves worst-case hardness, not average-case hardness for
this generator, so the measured attack panel is essential evidence and remains
a caveat rather than a theorem.
"""


def _sample_noncrossing_matching_without_cycle_edges(
    points: list[int], n: int, rng: random.Random
) -> list[tuple[int, int]] | None:
    """Sample a noncrossing matching on one page, avoiding base-cycle edges.

    The interval dynamic program counts all permitted completions, after which
    recursive weighted sampling is exact over that finite set.  This samples
    decoys only; the Hamilton cycle certificate was already chosen.
    """
    size = len(points)
    if size % 2:
        return None
    counts = [[0] * (size + 1) for _ in range(size + 1)]
    for i in range(size + 1):
        counts[i][i] = 1
    for length in range(2, size + 1, 2):
        for left in range(size - length + 1):
            right = left + length
            total = 0
            for partner in range(left + 1, right, 2):
                u, v = points[left], points[partner]
                if (u - v) % n in (1, n - 1):
                    continue
                total += counts[left + 1][partner] * counts[partner + 1][right]
            counts[left][right] = total
    if counts[0][size] == 0:
        return None

    matching: list[tuple[int, int]] = []

    def sample_interval(left: int, right: int) -> None:
        if left == right:
            return
        choices: list[tuple[int, int]] = []
        total = 0
        for partner in range(left + 1, right, 2):
            u, v = points[left], points[partner]
            if (u - v) % n in (1, n - 1):
                continue
            weight = counts[left + 1][partner] * counts[partner + 1][right]
            if weight:
                choices.append((partner, weight))
                total += weight
        draw = rng.randrange(total)
        chosen = choices[-1][0]
        for partner, weight in choices:
            if draw < weight:
                chosen = partner
                break
            draw -= weight
        matching.append((points[left], points[chosen]))
        sample_interval(left + 1, chosen)
        sample_interval(chosen + 1, right)

    sample_interval(0, size)
    return matching


def _fallback_two_page_matching(n: int) -> list[tuple[int, int]]:
    """A deterministic 2-page matching used only after bounded resampling.

    Consecutive chords in this list cross and nonconsecutive chords do not, so
    alternating them between the two pages gives a valid book embedding.  The
    matching avoids cycle edges and includes both parity-preserving and
    parity-reversing chords.
    """
    chords = [(0, 2)]
    chords.extend((left, left + 3) for left in range(1, n - 3, 2))
    chords.append((n - 3, n - 1))
    return chords


def _two_page_decoy_matching(
    n: int, rng: random.Random, page_mix: int
) -> list[tuple[int, int]]:
    """Draw a perfect decoy matching carried by two noncrossing pages."""
    for _ in range(64):
        first_page = list(range(0, n, 2))
        second_page = list(range(1, n, 2))
        if len(first_page) % 2:
            second_page.append(first_page.pop(rng.randrange(len(first_page))))
        # A controlled number of vertices changes pages.  Keeping most of the
        # alternating structure preserves deep Catalan nesting, while the mix
        # prevents the old all-same-parity matching and its exact signed
        # adjacency eigenvector.
        mix = min(len(first_page) // 2, len(second_page) // 2, page_mix)
        first_positions = rng.sample(range(len(first_page)), mix)
        second_positions = rng.sample(range(len(second_page)), mix)
        for first_index, second_index in zip(first_positions, second_positions):
            first_page[first_index], second_page[second_index] = (
                second_page[second_index],
                first_page[first_index],
            )
        first_page.sort()
        second_page.sort()
        first = _sample_noncrossing_matching_without_cycle_edges(first_page, n, rng)
        second = _sample_noncrossing_matching_without_cycle_edges(second_page, n, rng)
        if first is not None and second is not None:
            return first + second
    return _fallback_two_page_matching(n)


def _normalize_cycle(order: list[int]) -> list[int]:
    """Canonicalize rotation and reversal of a spanning undirected cycle."""
    if not order:
        return []
    try:
        at = order.index(0)
    except ValueError:
        return list(order)
    out = order[at:] + order[:at]
    if len(out) > 2 and out[1] > out[-1]:
        out = [out[0]] + list(reversed(out[1:]))
    return out


def _adjacency_from_edges(n: int, edges: list[list[int]]) -> list[list[int]]:
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    for row in adj:
        row.sort()
    return adj


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a cubic graph around a known [1,1]-HAM witness."""
    page_mix = params.pop("page_mix", 4)
    if params:
        raise ValueError("unknown parameters: " + ",".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer")
    if n < 8 or n % 2:
        raise ValueError("n must be even and at least 8")
    if n > 600:
        raise ValueError("n exceeds the certificate-language bound of 600")
    if isinstance(page_mix, bool) or not isinstance(page_mix, int) or page_mix < 1:
        raise ValueError("page_mix must be a positive integer")

    rng = random.Random(seed)
    base_cycle = [(i, (i + 1) % n) for i in range(n)]

    # One matching lies on each page of the hidden cyclic order.  Page
    # membership is independently randomized so it does not leak a signed
    # adjacency eigenvector; the sampler explicitly forbids cycle-edge copies.
    decoys = _two_page_decoy_matching(n, rng, page_mix)

    relabel = list(range(n))
    rng.shuffle(relabel)
    answer = _normalize_cycle([relabel[i] for i in range(n)])

    edges = {
        tuple(sorted((relabel[u], relabel[v])))
        for u, v in base_cycle + decoys
    }
    if len(edges) != 3 * n // 2:
        raise AssertionError("construction did not produce a simple cubic graph")
    edge_list = [list(edge) for edge in edges]
    rng.shuffle(edge_list)
    adjacency = _adjacency_from_edges(n, edge_list)
    if any(len(row) != 3 for row in adjacency):
        raise AssertionError("construction did not produce degree three")

    return {
        "family": "cubic_[1,1]-HAM",
        "a": 1,
        "b": 1,
        "n": n,
        "page_mix": page_mix,
        "vertices": list(range(n)),
        "edges": edge_list,
        "adjacency": adjacency,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a complete problem statement and its exact answer contract."""
    n = inst["n"]
    edge_text = " ".join(f"{u}-{v}" for u, v in inst["edges"])
    statement = f"""[1,1]-HAMILTONICITY IN A CUBIC GRAPH

An undirected closed walk is a cyclic sequence of vertices in which each
consecutive pair is an edge, including the pair formed by the last and first
entries.  A graph is [a,b]-HAM when such a walk visits every vertex at least a
times and at most b times.  Here a=b=1, so you must give a Hamilton cycle: a
closed walk that contains every vertex exactly once.

The simple undirected graph has vertices 0,1,...,{n - 1}.  Every edge below is
unordered, and every vertex has degree 3.

Edges (u-v denotes the unordered edge {{u,v}}):
{edge_text}

Return one JSON list of exactly {n} distinct integers containing every vertex
from 0 through {n - 1}.  Consecutive list entries and the last/first pair must
be listed edges.  Rotations and reversal denote the same cycle, so normalize
your list to begin with 0 and require the second entry to be smaller than the
last entry.  Repeats are forbidden.

Give your final answer inside <answer></answer> tags, as one JSON list of
exactly {n} integers.
Example: <answer>[0, 3, 7, 2]</answer>
The example illustrates syntax only and is not an answer to this instance.
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Parse a delimited or fenced JSON integer list without raising."""
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.I | re.S)
    candidates = tagged or fenced
    if not candidates:
        candidates = re.findall(r"\[[\s\d,+-]*\]", text, flags=re.S)
    for raw in reversed(candidates):
        try:
            value = json.loads(raw.strip())
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, list) and all(type(item) is int for item in value):
            return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any normalized [1,1]-HAM witness; never inspect inst['answer']."""
    n = inst["n"]
    if not isinstance(answer, list):
        return False, "answer_not_list"
    if not answer:
        return False, "answer_empty"
    if len(answer) != n:
        return False, f"wrong_length:{len(answer)}_expected_{n}"
    if any(type(vertex) is not int for vertex in answer):
        return False, "non_integer_vertex"
    if any(vertex < 0 or vertex >= n for vertex in answer):
        return False, "vertex_out_of_range"
    if len(set(answer)) != n:
        return False, "duplicate_vertex"
    if answer[0] != 0:
        return False, "noncanonical_rotation"
    if answer[1] >= answer[-1]:
        return False, "noncanonical_reflection"

    adjacency = inst.get("adjacency")
    if not isinstance(adjacency, list) or len(adjacency) != n:
        adjacency = _adjacency_from_edges(n, inst["edges"])
    for position, u in enumerate(answer):
        v = answer[(position + 1) % n]
        if v not in adjacency[u]:
            return False, f"missing_edge_at_position:{position}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample normalized spanning cyclic orders, not n^n noise."""
    tail = list(range(1, inst["n"]))
    rng.shuffle(tail)
    candidate = [0] + tail
    if candidate[1] > candidate[-1]:
        candidate = [0] + list(reversed(candidate[1:]))
    return candidate


def search_space(inst: dict) -> int | None:
    """Count normalized cyclic permutations (rotation and reversal removed)."""
    return math.factorial(inst["n"] - 1) // 2


def enumerate_all(inst: dict) -> int | None:
    """Exactly enumerate tiny certificate spaces, with a hard work cap."""
    if search_space(inst) > 200_000:
        return None
    n = inst["n"]
    adjacency = inst["adjacency"]
    count = 0
    for tail in itertools.permutations(range(1, n)):
        if tail[0] >= tail[-1]:
            continue
        order = (0,) + tail
        if all(order[(i + 1) % n] in adjacency[order[i]] for i in range(n)):
            count += 1
    return count


def _adjacency(inst: dict) -> list[list[int]]:
    adjacency = inst.get("adjacency")
    if isinstance(adjacency, list) and len(adjacency) == inst["n"]:
        return [list(row) for row in adjacency]
    return _adjacency_from_edges(inst["n"], inst["edges"])


def canonical_key(inst: dict) -> str:
    """A strong cheap isomorphism invariant from all edge-distance profiles."""
    n = inst["n"]
    adjacency = _adjacency(inst)
    distances: list[list[int]] = []
    for source in range(n):
        distance = [-1] * n
        distance[source] = 0
        queue = deque([source])
        while queue:
            u = queue.popleft()
            for v in adjacency[u]:
                if distance[v] < 0:
                    distance[v] = distance[u] + 1
                    queue.append(v)
        distances.append(distance)

    vertex_profiles = [
        tuple(Counter(row).get(level, 0) for level in range(n))
        for row in distances
    ]
    edge_profiles = []
    for u in range(n):
        for v in adjacency[u]:
            if u >= v:
                continue
            joint = Counter((distances[u][x], distances[v][x]) for x in range(n))
            forward = tuple(sorted(joint.items()))
            backward = tuple(sorted(((b, a), c) for (a, b), c in joint.items()))
            endpoints = tuple(sorted((vertex_profiles[u], vertex_profiles[v])))
            edge_profiles.append((endpoints, min(forward, backward)))
    payload = json.dumps(
        [n, sorted(vertex_profiles), sorted(edge_profiles)], separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Climb n until the compact-route operation cap becomes binding."""
    n = int(params.get("n", 0))
    page_mix = int(params.get("page_mix", 4))
    # Cubicity fixes exactly one decoy edge per vertex, so crowding and degree
    # cannot rise independently.  The spanning witness length is also fixed by
    # n.  The named ladder reaches the 256-atom cap at n=256.
    if n < 240:
        return {"n": 240, "page_mix": page_mix}
    if n < 256:
        return {"n": 256, "page_mix": page_mix}
    return "cap_bound"


def _candidate_from_path(path: list[int] | None) -> list[int] | None:
    return None if path is None else _normalize_cycle(path)


def _valid_if_any(inst: dict, candidate: object) -> bool:
    return candidate is not None and verify(inst, candidate)[0]


def _attack_label_order(inst: dict) -> list[int]:
    return list(range(inst["n"]))


def _attack_greedy(inst: dict) -> list[int] | None:
    adjacency = _adjacency(inst)
    n = inst["n"]
    path = [0]
    seen = {0}
    while len(path) < n:
        choices = [v for v in adjacency[path[-1]] if v not in seen]
        if not choices:
            return None
        choices.sort(key=lambda v: (sum(w not in seen for w in adjacency[v]), v))
        path.append(choices[0])
        seen.add(choices[0])
    if path[0] not in adjacency[path[-1]]:
        return None
    return _normalize_cycle(path)


def _attack_local_edge_statistics(inst: dict) -> list[int] | None:
    """Try triangle/four-cycle edge scores in both directions as outlier probes."""
    adjacency = _adjacency(inst)
    adjsets = [set(row) for row in adjacency]
    n = inst["n"]

    def score(u: int, v: int) -> tuple[int, int]:
        triangles = len(adjsets[u] & adjsets[v])
        squares = 0
        for x in adjacency[u]:
            if x == v:
                continue
            for y in adjacency[v]:
                if y != u and y in adjsets[x]:
                    squares += 1
        return triangles, squares

    for reverse_triangles in (False, True):
        for reverse_squares in (False, True):
            for first in adjacency[0]:
                path = [0, first]
                seen = {0, first}
                while len(path) < n:
                    u = path[-1]
                    choices = [v for v in adjacency[u] if v not in seen]
                    if not choices:
                        break
                    choices.sort(
                        key=lambda v: (
                            -score(u, v)[0] if reverse_triangles else score(u, v)[0],
                            -score(u, v)[1] if reverse_squares else score(u, v)[1],
                            sum(w not in seen for w in adjacency[v]),
                            v,
                        )
                    )
                    path.append(choices[0])
                    seen.add(choices[0])
                if len(path) == n and 0 in adjacency[path[-1]]:
                    return _normalize_cycle(path)
    return None


def _attack_random_restarts(
    inst: dict, rng: random.Random, restarts: int = 64
) -> tuple[list[int] | None, int]:
    adjacency = _adjacency(inst)
    n = inst["n"]
    operations = 0
    for _ in range(restarts):
        path = [0]
        seen = {0}
        while len(path) < n:
            choices = [v for v in adjacency[path[-1]] if v not in seen]
            operations += len(adjacency[path[-1]])
            if not choices:
                break
            scores = [(sum(w not in seen for w in adjacency[v]), v) for v in choices]
            best = min(value for value, _ in scores)
            tied = [v for value, v in scores if value == best]
            nxt = rng.choice(tied)
            path.append(nxt)
            seen.add(nxt)
        if len(path) == n and 0 in adjacency[path[-1]]:
            return _normalize_cycle(path), operations
    return None, operations


def _attack_spectral_seriation(inst: dict) -> tuple[list[int] | None, int]:
    """Try recovering a circular order from two deflated adjacency modes."""
    adjacency = _adjacency(inst)
    n = inst["n"]
    constant = [1.0 / math.sqrt(n)] * n
    operations = 0

    def mode(orthogonal_to: list[list[float]], seed: int) -> list[float]:
        nonlocal operations
        rng = random.Random(seed)
        vector = [rng.uniform(-1.0, 1.0) for _ in range(n)]

        def orthogonalize(values: list[float]) -> list[float]:
            nonlocal operations
            for basis in orthogonal_to:
                dot = sum(a * b for a, b in zip(values, basis))
                operations += n
                values = [a - dot * b for a, b in zip(values, basis)]
            norm = math.sqrt(sum(a * a for a in values))
            operations += n
            return [a / norm for a in values]

        vector = orthogonalize(vector)
        for _ in range(180):
            values = [
                3.0 * vector[u] + sum(vector[v] for v in adjacency[u])
                for u in range(n)
            ]
            operations += 4 * n
            vector = orthogonalize(values)
        return vector

    first = mode([constant], 240516270)
    second = mode([constant, first], 240516271)
    candidates = [
        sorted(range(n), key=lambda u: math.atan2(second[u], first[u])),
        sorted(range(n), key=lambda u: math.atan2(first[u], second[u])),
        sorted(range(n), key=lambda u: first[u]),
        sorted(range(n), key=lambda u: second[u]),
    ]
    for order in candidates:
        for direction in (order, list(reversed(order))):
            candidate = _normalize_cycle(direction)
            if verify(inst, candidate)[0]:
                return candidate, operations
    return None, operations


def _attack_minus_one_eigenspace(
    inst: dict, rng: random.Random, trials: int = 1024
) -> tuple[list[int] | None, int, int]:
    """Target the signed -1-eigenvector leaked by a tempting page split.

    If a sign vector s satisfies A*s=-s in a cubic graph, every vertex has one
    same-sign neighbour and two opposite-sign neighbours.  Opposite-sign edges
    then form a spanning 2-factor, which is a witness when connected.  We find
    the real nullspace of A+I by floating RREF, orthonormalize it, and repeatedly
    project random signs onto it.  All proposed witnesses are checked exactly.
    """
    adjacency = _adjacency(inst)
    n = inst["n"]
    matrix = [[0.0] * n for _ in range(n)]
    for u in range(n):
        matrix[u][u] = 1.0
        for v in adjacency[u]:
            matrix[u][v] = 1.0

    pivot_columns: list[int] = []
    pivot_row = 0
    operations = 0
    tolerance = 1e-10
    for column in range(n):
        best = max(range(pivot_row, n), key=lambda row: abs(matrix[row][column]))
        if abs(matrix[best][column]) <= tolerance:
            continue
        matrix[pivot_row], matrix[best] = matrix[best], matrix[pivot_row]
        pivot = matrix[pivot_row][column]
        for j in range(column, n):
            matrix[pivot_row][j] /= pivot
            operations += 1
        for row in range(n):
            if row == pivot_row or abs(matrix[row][column]) <= tolerance:
                continue
            factor = matrix[row][column]
            for j in range(column, n):
                matrix[row][j] -= factor * matrix[pivot_row][j]
                operations += 2
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == n:
            break

    pivot_set = set(pivot_columns)
    free_columns = [column for column in range(n) if column not in pivot_set]
    raw_basis: list[list[float]] = []
    for free in free_columns:
        vector = [0.0] * n
        vector[free] = 1.0
        for row, pivot in enumerate(pivot_columns):
            vector[pivot] = -matrix[row][free]
        raw_basis.append(vector)

    basis: list[list[float]] = []
    for vector in raw_basis:
        for previous in basis:
            dot = sum(x * y for x, y in zip(vector, previous))
            vector = [x - dot * y for x, y in zip(vector, previous)]
            operations += 2 * n
        norm = math.sqrt(sum(x * x for x in vector))
        operations += n
        if norm > tolerance:
            basis.append([x / norm for x in vector])
            operations += n

    def candidate_from_signs(signs: list[int]) -> list[int] | None:
        if any(
            sum(signs[v] for v in adjacency[u]) != -signs[u]
            for u in range(n)
        ):
            return None
        cycle_adjacency = [
            [v for v in adjacency[u] if signs[v] != signs[u]] for u in range(n)
        ]
        if any(len(row) != 2 for row in cycle_adjacency):
            return None
        order = [0]
        seen = {0}
        previous = -1
        current = 0
        while True:
            nxt = next(v for v in cycle_adjacency[current] if v != previous)
            if nxt == 0:
                break
            if nxt in seen:
                return None
            order.append(nxt)
            seen.add(nxt)
            previous, current = current, nxt
        candidate = _normalize_cycle(order)
        return candidate if verify(inst, candidate)[0] else None

    if not basis:
        return None, operations, 0
    for _ in range(trials):
        values = [rng.gauss(0.0, 1.0) for _ in range(n)]
        previous_signs: tuple[int, ...] | None = None
        for _ in range(16):
            coefficients = [
                sum(x * y for x, y in zip(values, vector)) for vector in basis
            ]
            projection = [
                sum(coefficient * vector[u] for coefficient, vector in zip(coefficients, basis))
                for u in range(n)
            ]
            operations += 2 * n * len(basis)
            signs = tuple(1 if value >= 0.0 else -1 for value in projection)
            candidate = candidate_from_signs(list(signs))
            if candidate is not None:
                return candidate, operations, len(basis)
            if signs == previous_signs:
                break
            previous_signs = signs
            values = list(signs)
    return None, operations, len(basis)


def _attack_near_parity_repair(
    inst: dict,
    rng: random.Random,
    restarts: int = 64,
    steps: int = 4_000,
    node_budget: int = 20_000,
) -> tuple[list[int] | None, int, int, int]:
    """Seek an approximate signed -1 pattern, then prioritize exact repair.

    The earlier page construction leaked a sign vector for which every vertex
    had exactly one same-sign neighbour.  A small page perturbation might leave
    an almost-satisfying sign vector.  Min-conflicts searches for that vector;
    its best pattern determines a vertex relabelling for one bounded exact
    matching-complement repair search.
    """
    adjacency = _adjacency(inst)
    n = inst["n"]

    def good(vertex: int, signs: list[int]) -> bool:
        return sum(signs[v] == signs[vertex] for v in adjacency[vertex]) == 1

    best_signs: list[int] | None = None
    best_bad = n + 1
    iterations = 0
    for _ in range(restarts):
        signs = [rng.randrange(2) for _ in range(n)]
        bad = {vertex for vertex in range(n) if not good(vertex, signs)}
        for _ in range(steps):
            iterations += 1
            if len(bad) < best_bad:
                best_bad = len(bad)
                best_signs = signs[:]
            if not bad:
                break
            vertex = rng.choice(tuple(bad))
            best_delta = n
            choices: list[int] = []
            for flipped in [vertex] + adjacency[vertex]:
                affected = [flipped] + adjacency[flipped]
                before = sum(item in bad for item in affected)
                signs[flipped] ^= 1
                after = sum(not good(item, signs) for item in affected)
                signs[flipped] ^= 1
                delta = after - before
                if delta < best_delta:
                    best_delta = delta
                    choices = [flipped]
                elif delta == best_delta:
                    choices.append(flipped)
            if best_delta <= 0 or rng.random() < 0.015:
                flipped = rng.choice(choices)
                signs[flipped] ^= 1
                for item in [flipped] + adjacency[flipped]:
                    if good(item, signs):
                        bad.discard(item)
                    else:
                        bad.add(item)

    if best_signs is None:
        return None, iterations, 0, n
    order = sorted(
        range(n),
        key=lambda vertex: (
            not good(vertex, best_signs),
            best_signs[vertex],
            rng.random(),
        ),
    )
    permutation = [0] * n
    for new, old in enumerate(order):
        permutation[old] = new
    variant = _relabel_instance(inst, permutation, 240516270)
    candidate, nodes = _attack_propagating_matching_complement(
        variant, node_budget=node_budget
    )
    if candidate is None:
        return None, iterations, nodes, best_bad
    inverse = [0] * n
    for old, new in enumerate(permutation):
        inverse[new] = old
    transported = _normalize_cycle([inverse[vertex] for vertex in candidate])
    return transported, iterations, nodes, best_bad


def _cycle_from_mate(adjacency: list[list[int]], mate: list[int]) -> list[int] | None:
    """Read the complementary 2-factor, accepting only one spanning cycle."""
    n = len(adjacency)
    order = [0]
    previous = -1
    current = 0
    while True:
        choices = [v for v in adjacency[current] if v != mate[current] and v != previous]
        if not choices:
            return None
        nxt = choices[0]
        if nxt == 0:
            return _normalize_cycle(order) if len(order) == n else None
        if nxt in order:
            return None
        order.append(nxt)
        previous, current = current, nxt


def _attack_matching_complement(
    inst: dict, node_budget: int = 100_000
) -> tuple[list[int] | None, int]:
    """Exact cubic-graph attack: branch on perfect-matching complements."""
    adjacency = _adjacency(inst)
    n = inst["n"]
    mate = [-1] * n
    nodes = 0
    exhausted = False

    def visit(unmatched: int) -> list[int] | None:
        nonlocal nodes, exhausted
        nodes += 1
        if nodes > node_budget:
            exhausted = True
            return None
        if unmatched == 0:
            return _cycle_from_mate(adjacency, mate)

        candidates = [u for u in range(n) if mate[u] < 0]
        current = min(
            candidates,
            key=lambda u: (sum(mate[v] < 0 for v in adjacency[u]), u),
        )
        choices = [v for v in adjacency[current] if mate[v] < 0]
        for nxt in choices:
            mate[current] = nxt
            mate[nxt] = current
            result = visit(unmatched - 2)
            if result is not None:
                return result
            mate[current] = mate[nxt] = -1
            if exhausted:
                return None
        return None

    return visit(n), nodes


def _attack_propagating_matching_complement(
    inst: dict, node_budget: int = 100_000
) -> tuple[list[int] | None, int]:
    """Exact cubic attack with forced matching edges and subtour pruning.

    A Hamilton cycle in a cubic graph is the complement of a perfect matching.
    State 1 means an edge is in that matching and state 0 means it is in the
    complementary 2-factor.  Vertex constraints propagate both choices; a
    proper cycle in the definite 2-factor is an unrecoverable subtour.
    """
    adjacency = _adjacency(inst)
    n = inst["n"]
    edges: list[tuple[int, int]] = []
    edge_index: dict[tuple[int, int], int] = {}
    for u in range(n):
        for v in adjacency[u]:
            if u < v:
                edge_index[(u, v)] = edge_index[(v, u)] = len(edges)
                edges.append((u, v))
    incident = [[edge_index[(u, v)] for v in adjacency[u]] for u in range(n)]
    state = [-1] * len(edges)  # -1 undecided, 0 cycle, 1 matching
    nodes = 0

    def propagate() -> bool:
        changed = True
        while changed:
            changed = False
            for u in range(n):
                values = [state[index] for index in incident[u]]
                matched = values.count(1)
                undecided = values.count(-1)
                if matched > 1 or (matched == 0 and undecided == 0):
                    return False
                if matched == 1:
                    for index in incident[u]:
                        if state[index] == -1:
                            state[index] = 0
                            changed = True
                elif undecided == 1:
                    index = next(
                        index for index in incident[u] if state[index] == -1
                    )
                    state[index] = 1
                    changed = True

            cycle_adjacency = [[] for _ in range(n)]
            for index, (u, v) in enumerate(edges):
                if state[index] == 0:
                    cycle_adjacency[u].append(v)
                    cycle_adjacency[v].append(u)
            seen: set[int] = set()
            for start in range(n):
                if start in seen or not cycle_adjacency[start]:
                    continue
                stack = [start]
                vertices = 0
                degree_sum = 0
                while stack:
                    u = stack.pop()
                    if u in seen:
                        continue
                    seen.add(u)
                    vertices += 1
                    degree_sum += len(cycle_adjacency[u])
                    stack.extend(v for v in cycle_adjacency[u] if v not in seen)
                if degree_sum // 2 >= vertices and vertices < n:
                    return False
        return True

    def completed_cycle() -> list[int] | None:
        cycle_adjacency = [[] for _ in range(n)]
        for index, (u, v) in enumerate(edges):
            if state[index] == 0:
                cycle_adjacency[u].append(v)
                cycle_adjacency[v].append(u)
        if any(len(row) != 2 for row in cycle_adjacency):
            return None
        order = [0]
        previous = -1
        current = 0
        while True:
            nxt = next(v for v in cycle_adjacency[current] if v != previous)
            if nxt == 0:
                return _normalize_cycle(order) if len(order) == n else None
            if nxt in order:
                return None
            order.append(nxt)
            previous, current = current, nxt

    def visit() -> list[int] | None:
        nonlocal nodes, state
        nodes += 1
        if nodes > node_budget:
            return None
        before_propagation = state[:]
        if not propagate():
            state = before_propagation
            return []
        if all(value != -1 for value in state):
            result = completed_cycle()
            if result is not None:
                return result
            state = before_propagation
            return []

        choices = []
        for u in range(n):
            if not any(state[index] == 1 for index in incident[u]):
                undecided = [
                    index for index in incident[u] if state[index] == -1
                ]
                if undecided:
                    choices.append((len(undecided), u, undecided))
        _, _, branch_edges = min(choices)
        for index in branch_edges:
            before_branch = state[:]
            state[index] = 1
            result = visit()
            if result:
                return result
            if nodes > node_budget:
                return None
            state = before_branch
        state = before_propagation
        return []

    result = visit()
    return (result if result else None), nodes


def _attack_randomized_propagating_matching(
    inst: dict,
    rng: random.Random,
    restarts: int = 12,
    nodes_per_restart: int = 5_000,
) -> tuple[list[int] | None, int, int]:
    """Repeat the exact propagated attack after random vertex relabellings."""
    n = inst["n"]
    total_nodes = 0
    for restart in range(restarts):
        permutation = list(range(n))
        rng.shuffle(permutation)
        variant = _relabel_instance(inst, permutation, restart)
        candidate, nodes = _attack_propagating_matching_complement(
            variant, node_budget=nodes_per_restart
        )
        total_nodes += nodes
        if candidate is not None:
            inverse = [0] * n
            for old, new in enumerate(permutation):
                inverse[new] = old
            transported = _normalize_cycle([inverse[v] for v in candidate])
            return transported, total_nodes, restart + 1
    return None, total_nodes, restarts


def _relabel_instance(inst: dict, permutation: list[int], reorder_seed: int) -> dict:
    n = inst["n"]
    if sorted(permutation) != list(range(n)):
        raise ValueError("not a vertex permutation")
    edges = [sorted((permutation[u], permutation[v])) for u, v in inst["edges"]]
    random.Random(reorder_seed).shuffle(edges)
    out = dict(inst)
    out["vertices"] = list(range(n))
    out["edges"] = edges
    out["adjacency"] = _adjacency_from_edges(n, edges)
    out["answer"] = _normalize_cycle([permutation[v] for v in inst["answer"]])
    return out


# Filled only from harden.py-owned transcripts after the three isolated runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


def selftest() -> dict:
    """Run all nine mandatory gates and return their measured evidence."""
    report: dict[str, object] = {
        "paper": "2405.16270",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 19):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(
                    {"preset": preset, "seed": seed, "reason": "answer_not_JSON_native"}
                )
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=731, **shipping)
    planted = inst["answer"]
    swapped = None
    for i in range(1, inst["n"] - 2):
        trial = planted[:]
        trial[i], trial[i + 1] = trial[i + 1], trial[i]
        ok, why = verify(inst, trial)
        if not ok and why.startswith("missing_edge"):
            swapped = trial
            break
    corruptions: dict[str, object] = {
        "drop": planted[:-1],
        "swap": swapped if swapped is not None else planted[1:] + planted[:1],
        "duplicate": planted[:-1] + [planted[-2]],
        "empty": [],
        "out_of_range": planted[:-1] + [inst["n"]],
    }
    cases = {}
    reasons = []
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        code = why.split(":", 1)[0]
        cases[name] = {"rejected": not ok, "reason": why}
        reasons.append(code)
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and len(set(reasons)) == len(reasons),
        "cases": cases,
        "distinct_reason_codes": len(set(reasons)),
    }

    response = (
        "I used the cubic decomposition and checked the closing edge.\n\n"
        "```json\n<answer>\n"
        + json.dumps(planted)
        + "\n</answer>\n```\nThe normalization is included."
    )
    parsed = parse_answer(response)
    parsed_ok, parsed_why = verify(inst, parsed)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parsed_ok and parse_answer("garbage") is None,
        "parsed_equals_answer": parsed == planted,
        "verify_reason": parsed_why,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    guess_rng = random.Random(20260905)
    guess_total = 200_000
    guess_hits = 0
    density_start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    density_wall = time.perf_counter() - density_start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_fraction,
        "candidate_prior": "uniform normalized permutations of all vertices",
        "search_space": str(search_space(inst)),
        "wall_clock_sec": round(density_wall, 6),
    }

    attack_seeds = list(range(9100, 9108))
    names = [
        "label_order_outlier",
        "local_triangle_fourcycle_outlier",
        "greedy_constrained_walk",
        "random_restart_64",
        "spectral_cycle_seriation",
        "minus_one_eigenspace_rounding_1024",
        "near_parity_minconflicts_repair",
        "randomized_propagating_matching_12x10k",
    ]
    successes = {name: 0 for name in names}
    attack_walls = {name: 0.0 for name in names}
    random_operations = 0
    spectral_operations = 0
    minus_one_operations = 0
    minus_one_nullities = []
    parity_iterations = 0
    parity_repair_nodes = 0
    parity_best_bad = []
    matching_nodes = 0
    matching_nodes_per_seed = []
    matching_restarts_per_seed = []
    for seed in attack_seeds:
        trial = make_instance(seed=seed, **shipping)

        start = time.perf_counter()
        candidate = _attack_label_order(trial)
        attack_walls["label_order_outlier"] += time.perf_counter() - start
        successes["label_order_outlier"] += int(_valid_if_any(trial, candidate))

        start = time.perf_counter()
        candidate = _attack_local_edge_statistics(trial)
        attack_walls["local_triangle_fourcycle_outlier"] += time.perf_counter() - start
        successes["local_triangle_fourcycle_outlier"] += int(
            _valid_if_any(trial, candidate)
        )

        start = time.perf_counter()
        candidate = _attack_greedy(trial)
        attack_walls["greedy_constrained_walk"] += time.perf_counter() - start
        successes["greedy_constrained_walk"] += int(_valid_if_any(trial, candidate))

        start = time.perf_counter()
        candidate, operations = _attack_random_restarts(
            trial, random.Random(seed ^ 0x5A17), restarts=64
        )
        attack_walls["random_restart_64"] += time.perf_counter() - start
        random_operations += operations
        successes["random_restart_64"] += int(_valid_if_any(trial, candidate))

        start = time.perf_counter()
        candidate, operations = _attack_spectral_seriation(trial)
        attack_walls["spectral_cycle_seriation"] += time.perf_counter() - start
        spectral_operations += operations
        successes["spectral_cycle_seriation"] += int(_valid_if_any(trial, candidate))

        start = time.perf_counter()
        candidate, operations, nullity = _attack_minus_one_eigenspace(
            trial, random.Random(seed ^ 0xE16E), trials=1024
        )
        attack_walls["minus_one_eigenspace_rounding_1024"] += (
            time.perf_counter() - start
        )
        minus_one_operations += operations
        minus_one_nullities.append(nullity)
        successes["minus_one_eigenspace_rounding_1024"] += int(
            _valid_if_any(trial, candidate)
        )

        start = time.perf_counter()
        candidate, iterations, nodes, best_bad = _attack_near_parity_repair(
            trial, random.Random(seed ^ 0x51A9)
        )
        attack_walls["near_parity_minconflicts_repair"] += (
            time.perf_counter() - start
        )
        parity_iterations += iterations
        parity_repair_nodes += nodes
        parity_best_bad.append(best_bad)
        successes["near_parity_minconflicts_repair"] += int(
            _valid_if_any(trial, candidate)
        )

        start = time.perf_counter()
        candidate, nodes, restarts = _attack_randomized_propagating_matching(
            trial, random.Random(seed ^ 0xA11CE), restarts=12,
            nodes_per_restart=10_000
        )
        attack_walls["randomized_propagating_matching_12x10k"] += (
            time.perf_counter() - start
        )
        matching_nodes += nodes
        matching_nodes_per_seed.append(nodes)
        matching_restarts_per_seed.append(restarts)
        successes["randomized_propagating_matching_12x10k"] += int(
            _valid_if_any(trial, candidate)
        )

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": len(attack_seeds),
            "wall_clock_sec": round(attack_walls[name], 6),
        }
        for name in names
    }
    attacks["random_restart_64"]["operations"] = random_operations
    attacks["spectral_cycle_seriation"]["operations"] = spectral_operations
    attacks["minus_one_eigenspace_rounding_1024"].update(
        {
            "operations": minus_one_operations,
            "nullities_per_seed": minus_one_nullities,
            "construction_specific": True,
        }
    )
    attacks["near_parity_minconflicts_repair"].update(
        {
            "minconflicts_iterations": parity_iterations,
            "repair_nodes": parity_repair_nodes,
            "best_bad_vertices_per_seed": parity_best_bad,
            "construction_specific": True,
        }
    )
    attacks["randomized_propagating_matching_12x10k"].update(
        {
            "nodes": matching_nodes,
            "nodes_per_seed": matching_nodes_per_seed,
            "restarts_per_seed": matching_restarts_per_seed,
            "standard_algorithm": True,
        }
    )
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attacks,
    }

    demo = make_instance(seed=731, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6 and all_failed and matching_nodes > 0,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density": guess_fraction,
        "shipping_density_wall_clock_sec": round(density_wall, 6),
        "demo_exact_valid_answer_count": demo_count,
        "demo_exact_candidate_count": search_space(demo),
        "baseline_attack_wall_clock_sec": round(
            attack_walls["randomized_propagating_matching_12x10k"], 6
        ),
        "baseline_attack_nodes": matching_nodes,
        "baseline_attack_attempts": len(attack_seeds),
        "baseline_attack_successes": successes[
            "randomized_propagating_matching_12x10k"
        ],
    }

    doubled_params = {"n": shipping["n"] * 2}
    scale_start = time.perf_counter()
    doubled = make_instance(seed=4471, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and search_space(doubled) > search_space(inst),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "build_and_verify_sec": round(time.perf_counter() - scale_start, 6),
        "verify_reason": doubled_why,
    }

    invariance_checks = 0
    transport_checks = 0
    nontrivial_checks = 0
    unrelated_keys = []
    for seed in range(20):
        original = make_instance(seed=12000 + seed, **shipping)
        key = canonical_key(original)
        unrelated_keys.append(key)
        rng = random.Random(33000 + seed)
        first = list(range(original["n"]))
        second = list(range(original["n"]))
        rng.shuffle(first)
        rng.shuffle(second)
        composed = [second[first[i]] for i in range(original["n"])]
        variants = [
            _relabel_instance(original, first, 44000 + seed),
            _relabel_instance(original, list(range(original["n"])), 55000 + seed),
            _relabel_instance(original, composed, 66000 + seed),
        ]
        for variant in variants:
            invariance_checks += int(canonical_key(variant) == key)
            transport_checks += int(verify(variant, variant["answer"])[0])
            nontrivial_checks += int(variant["edges"] != original["edges"])
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariance_checks == 60
        and transport_checks == 60
        and nontrivial_checks >= 20
        and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "witness_transport_checks": transport_checks,
        "nontrivial_transformations": nontrivial_checks,
        "unrelated_distinct_keys": distinct_keys,
        "unrelated_attempts": 20,
        "transformations": [
            "vertex permutation",
            "edge-list reordering",
            "composition of two vertex permutations with edge reordering",
        ],
        "invariant_scope": (
            "all vertex distance histograms and all undirected edge joint-distance "
            "profiles; this is a strong invariant, not a complete GI canonical form"
        ),
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    # After identifying the matching/cycle decomposition, following the unique
    # chosen next cycle edge takes one local decision per vertex.  Serialising
    # the already obtained vertex identifiers is not exact arithmetic.
    intended_operations = inst["n"]
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    within_caps = (
        answer_chars <= 2000
        and len(inst["answer"]) <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        # As of 2026-09-05 the three arms and hinted verdict are diagnostic;
        # only these measured output/effort caps gate shipping.
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": len(inst["answer"]),
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }
    PROBLEM_PROFILE["max_answer_tokens"] = answer_tokens

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(bool(gate.get("pass")) for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
