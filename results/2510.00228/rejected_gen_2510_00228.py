"""Rejected radio-graceful-labeling candidate for arXiv:2510.00228.

The generated graph G is the complement of a planar cubic graph H that is
assembled around a Hamiltonian cycle.  Thus G has diameter two and H is its
antipodal graph.  Theorem 2.4 of the paper turns the planted Hamiltonian path
in H into a radio graceful labeling of G.  The certificate is carried through
a random vertex relabeling; it is never recovered by solving the final graph.

This module is retained for audit.  It is not shippable: an external
cycle-cover MILP with iterative subtour cuts recovered a Hamiltonian cycle on
7/8 shipping instances.  See REJECTED.md and EXTERNAL_MILP_AUDIT below.
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
from collections import Counter, deque
from functools import lru_cache


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - this family needs no helper library
    exact_matrices = rationals = None


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "diameter-two graph given by its antipodal nonedges",
        "antipodal graph",
        "radio graceful vertex labeling",
    ],
    "verification_operations": [
        "permutation check",
        "antipodal-edge membership",
        "exact radio-inequality implication for diameter two",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "reduction recognition",
    "intuition_description": (
        "For diameter two, consecutive radio labels must trace a Hamiltonian "
        "path in the antipodal graph; without recognizing that equivalence, "
        "a solver confronts all pairwise radio inequalities."
    ),
    "hardness_basis": (
        "Rejected Track A claim: although Theorem 2.4 makes the task "
        "Hamiltonian-path search in a cubic planar antipodal graph, a "
        "cycle-cover MILP with iterative subtour cuts solved 7/8 shipping "
        "instances in a 20-second-per-seed audit, so worst-case planar cubic "
        "Hamiltonicity does not support this generated distribution."
    ),
    "max_answer_tokens": 273,
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
    "demo": {"n": 8},
    "easy": {"n": 120},
    "medium": {"n": 180},
    "hard": {"n": 240},
}

SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of length n containing every vertex identifier 0 through "
        "n-1 exactly once; position i (zero based) names the vertex receiving "
        "radio label i+1."
    ),
    "bounds": {
        "length": "n",
        "entry_min": 0,
        "entry_max": "n-1",
        "distinct": True,
        "order_matters": True,
        "shipping_max_n": 240,
    },
}

STRUCTURAL_HINT = (
    "For a diameter-two graph, inspect consecutive labels through the "
    "Hamiltonian-path structure of its antipodal graph."
)

PLACEBO_HINT = (
    "For this finite graph, keep careful track of every vertex identifier "
    "and every consecutive position."
)

NOTES = """\
Definition 2.2 fixes the exact radio inequality and the meaning of graceful.
Theorem 2.4 fixes the decisive diameter-two equivalence: a graceful radio
labeling exists exactly when the antipodal graph has a Hamiltonian path.
Theorem 3.26 also states directly that the complement of a low-degree
traceable graph is radio graceful.  The generated cubic graph H is traceable
by construction and has maximum degree 3, so G=complement(H) lies in that
paper-native regime.

The paper's easy regimes were checked before choosing this one.  The Dirac and
Moon-Moser degree tests (Theorems 2.5 and 2.6), Proposition 3.4, and Porism
3.22 certify existence but do not reveal the path in this sparse antipodal
graph.  Constructions 3.33 and 3.34 were rejected as a family because their
Singer-graph labels come from a direct O(n) recurrence; there is no Track B
compression gap.  Even-diameter bipartite negatives from Theorem 3.1 are
decided by elementary connectivity and likewise fail H.

Generation samples the answer cycle first.  It randomly divides the vertices
between two drawing pages, then samples a noncrossing perfect matching on each
page while forbidding cycle-edge duplicates.  The union is therefore a simple
planar cubic Hamiltonian graph.  Randomizing the page division is essential:
an earlier alternating-page draft made the planted cycle's parity vector an
exact -1 eigenvector and was rejected by a construction-aware spectral audit.
An independent random relabeling is applied to both graph and certificate.
Individual cycle and matching edges have the same relabeled marginal
distribution.  All vertices have degree three, defeating degree outliers; the
displayed order is shuffled, defeating label order; constrained greedy walks
and randomized restarts encounter locally plausible matching edges; spectral
seriation does not recover the cycle; and a bounded exact Hamiltonian-path DFS
is reported as the domain-standard attack.  Worst-case NP-hardness does not
prove this planted distribution hard, so G5's measured attack cost is an
essential caveat rather than decoration.

The final audit supplied the missing stronger domain attack: a binary
cycle-cover MILP with degree-two constraints and iterative subtour cuts.  It
solved seven of eight n=240 seeds, so this candidate fails H on Track A and is
retained only as rejected evidence.
"""


EXTERNAL_MILP_AUDIT = {
    "name": "binary cycle-cover MILP with iterative subtour cuts (SciPy/HiGHS)",
    "measured_externally": True,
    "time_limit_sec_per_seed": 20,
    "successes": 7,
    "attempts": 8,
    "total_wall_clock_sec": 59.862305,
    "total_milp_rounds": 113,
    "total_subtour_cuts": 648,
    "seeds": {
        "9100": {"solved": True, "seconds": 11.108759, "rounds": 18, "cuts": 111},
        "9101": {"solved": True, "seconds": 15.610094, "rounds": 23, "cuts": 112},
        "9102": {"solved": True, "seconds": 1.264518, "rounds": 8, "cuts": 57},
        "9103": {"solved": True, "seconds": 0.612444, "rounds": 9, "cuts": 53},
        "9104": {"solved": False, "seconds": 20.002786, "rounds": 20, "cuts": 110},
        "9105": {"solved": True, "seconds": 4.678584, "rounds": 14, "cuts": 76},
        "9106": {"solved": True, "seconds": 1.361113, "rounds": 6, "cuts": 39},
        "9107": {"solved": True, "seconds": 5.224006, "rounds": 15, "cuts": 90},
    },
}


def _noncrossing_matching(
    points: list[int], n: int, rng: random.Random
) -> tuple[int, list[tuple[int, int]] | None]:
    """Uniformly sample an allowed noncrossing matching on one page.

    Points occur in their cyclic order.  Pairing positions ``a`` and ``j``
    leaves two independent even subintervals, which gives the Catalan
    recurrence used below.  A pair of neighbors on the planted n-cycle is
    forbidden because it would duplicate a cycle edge.  The returned count is
    also a construction check: a page division with count zero is resampled.
    """
    ordered = tuple(points)

    @lru_cache(maxsize=None)
    def count(a: int, b: int) -> int:
        if a == b:
            return 1
        if (b - a) % 2:
            return 0
        u = ordered[a]
        total = 0
        for j in range(a + 1, b, 2):
            v = ordered[j]
            if (u - v) % n in (1, n - 1):
                continue
            total += count(a + 1, j) * count(j + 1, b)
        return total

    def draw(a: int, b: int) -> list[tuple[int, int]]:
        if a == b:
            return []
        u = ordered[a]
        choices = []
        total = 0
        for j in range(a + 1, b, 2):
            v = ordered[j]
            if (u - v) % n in (1, n - 1):
                continue
            weight = count(a + 1, j) * count(j + 1, b)
            if weight:
                choices.append((j, weight))
                total += weight
        ticket = rng.randrange(total)
        for j, weight in choices:
            if ticket < weight:
                return (
                    [(u, ordered[j])]
                    + draw(a + 1, j)
                    + draw(j + 1, b)
                )
            ticket -= weight
        raise AssertionError("weighted matching draw fell through")

    total = count(0, len(ordered))
    return total, draw(0, len(ordered)) if total else None


def _make_adjacency(n: int, edges: list[list[int]]) -> list[list[int]]:
    adjacency = [[] for _ in range(n)]
    for u, v in edges:
        adjacency[u].append(v)
        adjacency[v].append(u)
    for row in adjacency:
        row.sort()
    return adjacency


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a radio graceful graph and carry its certificate."""
    del params
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer")
    if n < 8 or n % 4:
        raise ValueError("n must be a multiple of 4 and at least 8")
    if n > 512:
        raise ValueError("n exceeds the supported scaling-test bound of 512")

    rng = random.Random(seed)
    cycle_edges = [(i, (i + 1) % n) for i in range(n)]

    # A random page division avoids the exact parity eigenvector leaked by the
    # earlier even/odd division.  Each page has even size because n is a
    # multiple of four.  Zero-count divisions are rejected before drawing.
    for _ in range(10_000):
        first_page = set(rng.sample(range(n), n // 2))
        page0 = sorted(first_page)
        page1 = [v for v in range(n) if v not in first_page]
        count0, matching0 = _noncrossing_matching(page0, n, rng)
        count1, matching1 = _noncrossing_matching(page1, n, rng)
        if count0 and count1 and matching0 is not None and matching1 is not None:
            matching_edges = matching0 + matching1
            break
    else:  # pragma: no cover - no supported n comes remotely close in tests
        raise RuntimeError("could not sample two admissible page matchings")

    relabel = list(range(n))
    rng.shuffle(relabel)
    answer = [relabel[i] for i in range(n)]
    edge_set = {
        tuple(sorted((relabel[u], relabel[v])))
        for u, v in cycle_edges + matching_edges
    }
    if len(edge_set) != 3 * n // 2:
        raise AssertionError("construction did not produce a simple cubic graph")
    antipodal_edges = [list(edge) for edge in edge_set]
    rng.shuffle(antipodal_edges)

    return {
        "family": "radio_graceful_complement_of_planar_cubic_hamiltonian",
        "n": n,
        "vertices": list(range(n)),
        "antipodal_edges": antipodal_edges,
        "antipodal_adjacency": _make_adjacency(n, antipodal_edges),
        "answer": answer,
    }


def render(inst: dict) -> str:
    n = inst["n"]
    edge_text = " ".join(f"{u}-{v}" for u, v in inst["antipodal_edges"])
    statement = f"""Radio graceful labeling of a diameter-two graph

Let G be the simple undirected graph with vertex set 0,1,...,{n - 1}.  Every
pair of distinct vertices is an edge of G except for the pairs in the list
below.  A listed token u-v denotes the unordered nonedge {{u,v}}.  Each vertex
occurs in exactly three listed pairs; consequently G is connected and has
diameter 2.

Nonedges of G:
{edge_text}

For vertices u and v, d(u,v) is the number of edges in a shortest G-path from
u to v.  A radio labeling is a bijection f from the vertices to the integers
1,2,...,{n} such that, for every two distinct vertices u,v,

    |f(u)-f(v)| + d(u,v) >= 3.

Find a radio labeling.  Encode it as a list [x1,x2,...,x{n}] of exactly {n}
distinct integers, where xi is the vertex assigned label i.  Thus every integer
from 0 through {n - 1} must occur exactly once.  Order matters and indexing in
the list is one-based only in the names x1,...,x{n}; vertex identifiers remain
zero-based.

Give your final answer inside <answer></answer> tags, as one JSON list of
exactly {n} integers.  Example format: <answer>[3, 0, 2, 1]</answer>
The example illustrates syntax only and is not an answer to this instance.
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
    blocks = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    candidates = blocks if blocks else re.findall(
        r"```(?:json)?\s*(.*?)```", text, flags=re.I | re.S
    )
    for raw in reversed(candidates):
        try:
            value = json.loads(raw.strip())
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, list) and all(type(x) is int for x in value):
            return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Verify any valid labeling without consulting the planted answer."""
    n = inst["n"]
    if not isinstance(answer, list):
        return False, "answer_not_list"
    if not answer:
        return False, "answer_empty"
    if len(answer) != n:
        return False, f"wrong_length:{len(answer)}_expected_{n}"
    if any(type(v) is not int for v in answer):
        return False, "non_integer_vertex"
    if any(v < 0 or v >= n for v in answer):
        return False, "vertex_out_of_range"
    if len(set(answer)) != n:
        return False, "duplicate_vertex"

    adjacency = inst["antipodal_adjacency"]
    for i in range(n - 1):
        if answer[i + 1] not in adjacency[answer[i]]:
            return False, f"consecutive_labels_are_adjacent_in_G:{i + 1},{i + 2}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the obvious bijection language, not length-n noise."""
    candidate = list(range(inst["n"]))
    rng.shuffle(candidate)
    return candidate


def search_space(inst: dict) -> int | None:
    return math.factorial(inst["n"])


def enumerate_all(inst: dict) -> int | None:
    if search_space(inst) > 200_000:
        return None
    count = 0
    for candidate in itertools.permutations(range(inst["n"])):
        if verify(inst, list(candidate))[0]:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Strong relabeling invariant from all antipodal edge-distance profiles."""
    n = inst["n"]
    adjacency = inst["antipodal_adjacency"]
    distances: list[list[int]] = []
    for source in range(n):
        dist = [-1] * n
        dist[source] = 0
        queue = deque([source])
        while queue:
            u = queue.popleft()
            for v in adjacency[u]:
                if dist[v] < 0:
                    dist[v] = dist[u] + 1
                    queue.append(v)
        distances.append(dist)

    vertex_profiles = [
        tuple(Counter(row).get(d, 0) for d in range(n)) for row in distances
    ]
    edge_profiles = []
    for u in range(n):
        for v in adjacency[u]:
            if u >= v:
                continue
            joint = Counter((distances[u][x], distances[v][x]) for x in range(n))
            forward = tuple(sorted(joint.items()))
            backward = tuple(
                sorted(((b, a), count) for (a, b), count in joint.items())
            )
            endpoint_pair = tuple(sorted((vertex_profiles[u], vertex_profiles[v])))
            edge_profiles.append((endpoint_pair, min(forward, backward)))
    payload = json.dumps(
        [n, sorted(vertex_profiles), sorted(edge_profiles)], separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    n = int(params.get("n", 0))
    if n < 180:
        return {"n": 180}
    if n < 240:
        return {"n": 240}
    if n < 256:
        return {"n": 256}
    return "cap_bound"


def _normalize_cycle(order: list[int]) -> list[int]:
    if not order:
        return []
    at = order.index(0)
    out = order[at:] + order[:at]
    if len(out) > 2 and out[1] > out[-1]:
        out = [out[0]] + list(reversed(out[1:]))
    return out


def _attack_label_order(inst: dict) -> list[int]:
    return list(range(inst["n"]))


def _attack_greedy(inst: dict) -> list[int] | None:
    adjacency = inst["antipodal_adjacency"]
    n = inst["n"]
    for start in range(n):
        path = [start]
        seen = {start}
        while len(path) < n:
            choices = [v for v in adjacency[path[-1]] if v not in seen]
            if not choices:
                break
            nxt = min(
                choices,
                key=lambda v: (
                    sum(w not in seen for w in adjacency[v]),
                    v,
                ),
            )
            path.append(nxt)
            seen.add(nxt)
        if len(path) == n:
            return path
    return None


def _attack_random_restarts(
    inst: dict, rng: random.Random, restarts: int = 256
) -> tuple[list[int] | None, int]:
    adjacency = inst["antipodal_adjacency"]
    n = inst["n"]
    operations = 0
    for _ in range(restarts):
        start = rng.randrange(n)
        path = [start]
        seen = {start}
        while len(path) < n:
            choices = [v for v in adjacency[path[-1]] if v not in seen]
            operations += len(adjacency[path[-1]])
            if not choices:
                break
            scores = [(sum(w not in seen for w in adjacency[v]), v) for v in choices]
            best = min(score for score, _ in scores)
            tied = [v for score, v in scores if score == best]
            nxt = rng.choice(tied)
            path.append(nxt)
            seen.add(nxt)
        if len(path) == n:
            return path, operations
    return None, operations


def _attack_spectral_seriation(inst: dict) -> tuple[list[int] | None, int]:
    """Try to order the planted cycle using two deflated adjacency modes."""
    adjacency = inst["antipodal_adjacency"]
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

    first = mode([constant], 8171)
    second = mode([constant, first], 8179)
    candidates = [
        sorted(range(n), key=lambda u: math.atan2(second[u], first[u])),
        sorted(range(n), key=lambda u: math.atan2(first[u], second[u])),
        sorted(range(n), key=lambda u: first[u]),
        sorted(range(n), key=lambda u: second[u]),
    ]
    for order in candidates:
        for direction in (order, list(reversed(order))):
            if verify(inst, direction)[0]:
                return direction, operations
    return None, operations


def _attack_hamilton_path_dfs(
    inst: dict, node_budget: int = 100_000
) -> tuple[list[int] | None, int]:
    """Bounded exact DFS with least-onward-choice branching."""
    adjacency = inst["antipodal_adjacency"]
    n = inst["n"]
    path = [0]
    stopped = False
    nodes = 0

    def visit(current: int, used: int) -> list[int] | None:
        nonlocal stopped, nodes
        nodes += 1
        if nodes > node_budget:
            stopped = True
            return None
        if len(path) == n:
            return path[:]
        choices = [v for v in adjacency[current] if not (used >> v) & 1]
        choices.sort(
            key=lambda v: (
                sum(not (used >> w) & 1 for w in adjacency[v]),
                v,
            )
        )
        for nxt in choices:
            path.append(nxt)
            result = visit(nxt, used | (1 << nxt))
            if result is not None:
                return result
            path.pop()
            if stopped:
                return None
        return None

    return visit(0, 1), nodes


def _cycle_from_matching(
    adjacency: list[list[int]], matching: list[tuple[int, int]]
) -> list[int] | None:
    """Return the complementary 2-factor if it is one spanning cycle."""
    removed = {tuple(sorted(edge)) for edge in matching}
    complement = [
        [v for v in adjacency[u] if tuple(sorted((u, v))) not in removed]
        for u in range(len(adjacency))
    ]
    if any(len(row) != 2 for row in complement):
        return None
    order = [0]
    seen = {0}
    previous = -1
    current = 0
    while True:
        choices = [v for v in complement[current] if v != previous]
        if not choices:
            return None
        nxt = choices[0]
        if nxt == 0:
            return _normalize_cycle(order) if len(order) == len(adjacency) else None
        if nxt in seen:
            return None
        order.append(nxt)
        seen.add(nxt)
        previous, current = current, nxt


def _attack_matching_complement(
    inst: dict, node_budget: int = 200_000
) -> tuple[list[int] | None, int]:
    """Enumerate perfect matchings and test their complementary 2-factors."""
    adjacency = inst["antipodal_adjacency"]
    n = inst["n"]
    matched = [False] * n
    chosen: list[tuple[int, int]] = []
    nodes = 0
    exhausted = False

    def visit() -> list[int] | None:
        nonlocal nodes, exhausted
        nodes += 1
        if nodes > node_budget:
            exhausted = True
            return None
        unmatched = [u for u in range(n) if not matched[u]]
        if not unmatched:
            return _cycle_from_matching(adjacency, chosen)
        current = min(
            unmatched,
            key=lambda u: (sum(not matched[v] for v in adjacency[u]), u),
        )
        for nxt in (v for v in adjacency[current] if not matched[v]):
            matched[current] = matched[nxt] = True
            chosen.append((current, nxt))
            result = visit()
            if result is not None:
                return result
            chosen.pop()
            matched[current] = matched[nxt] = False
            if exhausted:
                return None
        return None

    return visit(), nodes


def _valid_if_any(inst: dict, candidate: object) -> bool:
    return candidate is not None and verify(inst, candidate)[0]


def _relabel_instance(inst: dict, permutation: list[int], reorder_seed: int) -> dict:
    n = inst["n"]
    if sorted(permutation) != list(range(n)):
        raise ValueError("not a vertex permutation")
    edges = [
        sorted((permutation[u], permutation[v])) for u, v in inst["antipodal_edges"]
    ]
    random.Random(reorder_seed).shuffle(edges)
    return {
        **inst,
        "vertices": list(range(n)),
        "antipodal_edges": edges,
        "antipodal_adjacency": _make_adjacency(n, edges),
        "answer": [permutation[v] for v in inst["answer"]],
    }


# Script-owned oracle results are copied here only after their transcripts exist.
_G9_ARMS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}
_G9_HINTED_VERDICT = "oracle_unreachable_http_403_key_limit"


def selftest() -> dict:
    report: dict[str, object] = {
        "paper": "2510.00228",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2, 19):
            instance = make_instance(seed=seed, **params)
            ok, why = verify(instance, instance["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
            if json.loads(json.dumps(instance["answer"])) != instance["answer"]:
                g1_failures.append(
                    {"preset": preset, "seed": seed, "reason": "answer_not_json_native"}
                )
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=731, **ship_params)
    planted = inst["answer"]

    corruptions: dict[str, object] = {
        "drop": planted[:-1],
        "duplicate": planted[:-1] + [planted[-2]],
        "empty": [],
        "out_of_range": planted[:-1] + [inst["n"]],
    }
    swapped = None
    for i in range(1, inst["n"] - 2):
        trial = planted[:]
        trial[i], trial[i + 1] = trial[i + 1], trial[i]
        ok, why = verify(inst, trial)
        if not ok and why.startswith("consecutive_labels_are_adjacent_in_G"):
            swapped = trial
            break
    corruptions["swap"] = swapped if swapped is not None else planted[1:] + planted[:1]
    corruption_results = {}
    reason_codes = []
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        code = why.split(":", 1)[0]
        corruption_results[name] = {"rejected": not ok, "reason": why}
        reason_codes.append(code)
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruption_results.values())
        and len(set(reason_codes)) == len(reason_codes),
        "cases": corruption_results,
        "distinct_reason_codes": len(set(reason_codes)),
    }

    response = (
        "I used the diameter-two antipodal condition and checked every step.\n\n"
        "```json\n<answer>\n"
        + json.dumps(planted)
        + "\n</answer>\n```\nThe list contains each vertex once."
    )
    parsed = parse_answer(response)
    parsed_ok, parsed_why = verify(inst, parsed)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parsed_ok,
        "parsed_equals_answer": parsed == planted,
        "verify_reason": parsed_why,
        "garbage_returns_none": parse_answer("no delimited answer here") is None,
    }

    guess_rng = random.Random(20260905)
    guess_total = 200_000
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(guess_total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            guess_hits += 1
    density_wall = time.perf_counter() - start
    observed = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": observed,
        "candidate_prior": "uniform bijections from vertices to labels",
        "search_space": str(search_space(inst)),
    }

    demo = make_instance(seed=731, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)

    attack_seeds = list(range(9100, 9108))
    successes = {
        "degree_then_label_outlier": 0,
        "greedy_least_onward": 0,
        "random_restart_256": 0,
        "spectral_cycle_seriation": 0,
        "hamilton_path_dfs_100k": 0,
        "perfect_matching_complement_200k": 0,
    }
    random_operations = 0
    spectral_operations = 0
    dfs_nodes = 0
    dfs_wall = 0.0
    per_seed_nodes = []
    matching_nodes = 0
    matching_wall = 0.0
    matching_per_seed_nodes = []
    for seed in attack_seeds:
        attack_inst = make_instance(seed=seed, **ship_params)
        if _valid_if_any(attack_inst, _attack_label_order(attack_inst)):
            successes["degree_then_label_outlier"] += 1
        if _valid_if_any(attack_inst, _attack_greedy(attack_inst)):
            successes["greedy_least_onward"] += 1
        candidate, operations = _attack_random_restarts(
            attack_inst, random.Random(seed ^ 0x5A17), restarts=256
        )
        random_operations += operations
        if _valid_if_any(attack_inst, candidate):
            successes["random_restart_256"] += 1
        candidate, operations = _attack_spectral_seriation(attack_inst)
        spectral_operations += operations
        if _valid_if_any(attack_inst, candidate):
            successes["spectral_cycle_seriation"] += 1
        start = time.perf_counter()
        candidate, nodes = _attack_hamilton_path_dfs(
            attack_inst, node_budget=100_000
        )
        elapsed = time.perf_counter() - start
        dfs_wall += elapsed
        dfs_nodes += nodes
        per_seed_nodes.append(nodes)
        if _valid_if_any(attack_inst, candidate):
            successes["hamilton_path_dfs_100k"] += 1
        start = time.perf_counter()
        candidate, nodes = _attack_matching_complement(
            attack_inst, node_budget=200_000
        )
        elapsed = time.perf_counter() - start
        matching_wall += elapsed
        matching_nodes += nodes
        matching_per_seed_nodes.append(nodes)
        if _valid_if_any(attack_inst, candidate):
            successes["perfect_matching_complement_200k"] += 1

    attacks = {
        name: {"successes": count, "attempts": len(attack_seeds)}
        for name, count in successes.items()
    }
    attacks["random_restart_256"]["operations"] = random_operations
    attacks["spectral_cycle_seriation"]["operations"] = spectral_operations
    attacks["hamilton_path_dfs_100k"].update(
        {
            "nodes": dfs_nodes,
            "nodes_per_seed": per_seed_nodes,
            "wall_clock_sec": round(dfs_wall, 6),
            "standard_algorithm": True,
        }
    )
    attacks["perfect_matching_complement_200k"].update(
        {
            "nodes": matching_nodes,
            "nodes_per_seed": matching_per_seed_nodes,
            "wall_clock_sec": round(matching_wall, 6),
            "construction_aware_standard_algorithm": True,
        }
    )
    # This dependency-bearing audit is recorded, rather than rerun here, so
    # the retained module remains standard-library-only.  Its nonzero success
    # count deliberately makes the rejected candidate fail G5/G6.
    attacks["cycle_cover_milp_subtour_cuts"] = {
        key: value
        for key, value in EXTERNAL_MILP_AUDIT.items()
        if key not in ("name", "seeds")
    }
    attacks["cycle_cover_milp_subtour_cuts"]["seed_results"] = (
        EXTERNAL_MILP_AUDIT["seeds"]
    )
    all_failed = all(item["successes"] == 0 for item in attacks.values())
    report["G5_density_and_baseline"] = {
        "pass": observed < 1e-6 and all_failed and dfs_nodes > 0,
        "shipping_density": {
            "hits": guess_hits,
            "samples": guess_total,
            "observed_fraction": observed,
            "wall_clock_sec": round(density_wall, 6),
        },
        "demo_exact_valid_answers": demo_count,
        "demo_search_space": search_space(demo),
        "strongest_attack": {
            "name": EXTERNAL_MILP_AUDIT["name"],
            "wall_clock_sec": EXTERNAL_MILP_AUDIT["total_wall_clock_sec"],
            "milp_rounds": EXTERNAL_MILP_AUDIT["total_milp_rounds"],
            "subtour_cuts": EXTERNAL_MILP_AUDIT["total_subtour_cuts"],
            "attempts": EXTERNAL_MILP_AUDIT["attempts"],
            "successes": EXTERNAL_MILP_AUDIT["successes"],
            "measured_externally": True,
        },
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and len(attacks) >= 4,
        "attacks": attacks,
    }

    doubled_params = {"n": ship_params["n"] * 2}
    start = time.perf_counter()
    doubled = make_instance(seed=4471, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] > inst["n"],
        "base_n": inst["n"],
        "doubled_n": doubled["n"],
        "build_and_verify_sec": round(time.perf_counter() - start, 6),
        "verify_reason": doubled_why,
    }

    invariance_checks = 0
    transport_checks = 0
    nontrivial = 0
    unrelated_keys = []
    for seed in range(20):
        original = make_instance(seed=12000 + seed, **ship_params)
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
            invariance_checks += 1
            if canonical_key(variant) != key:
                continue
            ok, _ = verify(variant, variant["answer"])
            transport_checks += int(ok)
            nontrivial += int(variant["antipodal_edges"] != original["antipodal_edges"])
    report["G8_canonical_key"] = {
        "pass": invariance_checks == 60
        and transport_checks == 60
        and nontrivial >= 20
        and len(set(unrelated_keys)) == 20,
        "invariance_checks": invariance_checks,
        "witness_transport_checks": transport_checks,
        "nontrivial_transformations": nontrivial,
        "unrelated_distinct": len(set(unrelated_keys)),
        "unrelated_attempts": len(unrelated_keys),
        "invariant": "multiset of antipodal directed-edge distance-pair profiles",
    }

    answer_blob = json.dumps(inst["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    intended_operations = inst["n"]
    hinted = _G9_ARMS["hinted"]
    placebo = _G9_ARMS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = (
        placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    )
    within_caps = (
        answer_chars <= 2000
        and inst["n"] <= 256
        and intended_operations <= 300
    )
    hint_delta = (
        hinted_rate - placebo_rate
        if hinted["attempts"] and placebo["attempts"]
        else None
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": _G9_ARMS,
        "hinted_minus_placebo": hint_delta,
        "hinted_verdict": _G9_HINTED_VERDICT,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": inst["n"],
        "intended_route_operations": intended_operations,
        "caps_pass": within_caps,
        "diagnostic_arms_are_not_gated": True,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(bool(gate.get("pass")) for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
