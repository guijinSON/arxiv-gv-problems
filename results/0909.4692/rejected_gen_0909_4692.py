"""Verified generators for a planar Subgraph Isomorphism family.

The pattern is the spanning cycle C_n.  The host is a cubic planar graph made
from that cycle and two noncrossing perfect matchings, one drawn on either side.
The Hamiltonian cycle is therefore known by construction, before any instance
is searched.  Only the abstract labelled graph is exposed to the solver.

Paper: Frederic Dorn, "Planar Subgraph Isomorphism Revisited",
https://arxiv.org/abs/0909.4692
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


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "planar cubic host graph",
        "cycle pattern C_n",
        "injective vertex map",
    ],
    "verification_operations": [
        "integer range comparison",
        "permutation check",
        "host-edge membership",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "duality",
    "intuition_description": (
        "In a cubic host, a Hamiltonian cycle is the complement of a perfect "
        "matching; without recognizing the hidden two-page embedding, a solver "
        "must search exponentially many locally indistinguishable edge choices."
    ),
    "hardness_basis": (
        "Rejected Track A claim: although the Introduction cites NP-completeness "
        "for planar Subgraph Isomorphism and this candidate uses k=|V(G)|, a "
        "construction-aware exact-2-in-4 closed-neighbourhood attack recovered a "
        "verified cycle on 7/8 audit seeds at both n=120 and n=148."
    ),
    # Updated from the measured shipping answer by selftest().
    "max_answer_tokens": 123,
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
    "easy": {"n": 80},
    "medium": {"n": 120},
    "hard": {"n": 148},
}

SHIPPING_DIFFICULTY = "medium"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of all n host vertex identifiers exactly once, normalized "
        "to start at vertex 0 and to have second entry smaller than the last; "
        "consecutive entries and the last/first pair must be host edges."
    ),
    "bounds": {
        "length": "n",
        "entry_min": 0,
        "entry_max": "n-1",
        "distinct": True,
        "rotation_normalization": "first entry is 0",
        "reflection_normalization": "second entry < last entry",
        "max_n": 240,
    },
}

STRUCTURAL_HINT = (
    "The omitted edges of a cubic host form a perfect matching that admits two "
    "noncrossing pages around one hidden cyclic order."
)

PLACEBO_HINT = (
    "The requested ordering is sensitive to every endpoint, so check all "
    "consecutive pairs and the closing pair carefully."
)

NOTES = """\
Section 2 fixes subgraph isomorphism as a non-induced edge-preserving copy, so
extra matching edges in the host are allowed.  Theorem 1 gives the important
easy regime: a k-vertex planar pattern can be found and constructed in
2^{O(k)} n time, hence k must grow; this family uses k=n.  The Introduction
identifies planar Hamiltonicity as a source of NP-completeness, and the
Conclusion notes that the specialized k-Longest Path machinery does not extend
to arbitrary patterns.  Generation samples two noncrossing perfect matchings
on alternating vertices around an answer-first cycle, draws one on each side,
and then applies an independent random vertex relabelling.  All vertices have
degree three.  Relabelling defeats position and label-gap probes; identical
degree makes per-vertex outliers useless; randomized greedy walks fail because
wrong matching edges remain locally plausible; and the exact-search baseline
is capped only after recording its full node budget.  The certificate is never
obtained by running any of those searches.

Post-build rejection audit: sign the hidden cycle alternately.  Each closed
neighbourhood then contains exactly two vertices of each sign, because every
vertex has two cycle neighbours of the opposite sign and one matching neighbour
of the same sign.  A DPLL attack with exact-cardinality propagation searches
these local constraints and turns any satisfying colouring whose bichromatic
edges are connected into a Hamiltonian cycle.  It found verified witnesses on
7/8 seeds at n=120 and 7/8 at n=148 under a 200,000-node cap.  This invalidates
the Track A distributional claim; the same search is also the shortest known
post-insight route, so there is no Track B compression gap.
"""


def _noncrossing_matching(points: list[int], rng: random.Random) -> list[tuple[int, int]]:
    """Sample a perfect noncrossing matching in the displayed linear order."""
    if not points:
        return []
    # Pairing the first point with an odd-indexed point leaves even-size pieces.
    partner_index = rng.choice(range(1, len(points), 2))
    return (
        [(points[0], points[partner_index])]
        + _noncrossing_matching(points[1:partner_index], rng)
        + _noncrossing_matching(points[partner_index + 1 :], rng)
    )


def _normalize_cycle(order: list[int]) -> list[int]:
    """Canonicalize rotation and reversal of a spanning cyclic order."""
    if not order:
        return []
    try:
        at = order.index(0)
    except ValueError:
        return order[:]
    out = order[at:] + order[:at]
    if len(out) > 2 and out[1] > out[-1]:
        out = [out[0]] + list(reversed(out[1:]))
    return out


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Construct a certified planar cubic Hamiltonian host without solving it."""
    del params
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer")
    if n < 8 or n % 4:
        raise ValueError("n must be a multiple of 4 and at least 8")
    if n > 240:
        raise ValueError("n exceeds the certificate-language cap of 240")

    rng = random.Random(seed)
    base_cycle = [(i, (i + 1) % n) for i in range(n)]

    # Even endpoints are matched inside the cycle and odd endpoints outside.
    # Consecutive points of either matching are two positions apart on the full
    # cycle, so no matching edge duplicates a cycle edge.
    matching = _noncrossing_matching(list(range(0, n, 2)), rng)
    matching += _noncrossing_matching(list(range(1, n, 2)), rng)

    relabel = list(range(n))
    rng.shuffle(relabel)
    planted = _normalize_cycle([relabel[i] for i in range(n)])

    edges = {
        tuple(sorted((relabel[u], relabel[v])))
        for u, v in base_cycle + matching
    }
    edge_list = [list(e) for e in edges]
    rng.shuffle(edge_list)

    # The pattern is written in its native graph form as C_n, even though render
    # can define it more compactly than listing these predictable edges.
    pattern_edges = [[i, (i + 1) % n] for i in range(n)]
    return {
        "family": "planar_spanning_cycle_subgraph_isomorphism",
        "n": n,
        "host_vertices": list(range(n)),
        "host_edges": edge_list,
        "pattern_vertices": list(range(n)),
        "pattern_edges": pattern_edges,
        "answer": planted,
    }


def render(inst: dict) -> str:
    n = inst["n"]
    edge_text = " ".join(f"{u}-{v}" for u, v in inst["host_edges"])
    statement = f"""Planar spanning-cycle subgraph isomorphism

The pattern graph H is the cycle C_{n}: its vertices are 0,1,...,{n - 1},
and its edges are {{i,(i+1) mod {n}}} for every i.  The host graph G is a
simple undirected planar graph on the same vertex set 0,1,...,{n - 1}.

Find an injective map f from V(H) to V(G) that preserves every pattern edge:
whenever {{i,(i+1) mod {n}}} is an edge of H, {{f(i),f((i+1) mod {n})}}
must be an edge of G.  Because H and G have the same number of vertices, write
the map as the cyclic list [f(0),f(1),...,f({n - 1})], containing every host
vertex exactly once.  Rotations and reversal describe the same undirected
cycle, so normalize the list to start with vertex 0 and require its second
entry to be smaller than its last entry.

Host edges (u-v means the unordered edge {{u,v}}):
{edge_text}

Give your final answer inside <answer></answer> tags, as one JSON list of
exactly {n} integers.  Example format: <answer>[0, 3, 7, 2]</answer>
The example only illustrates syntax and length is not to scale.  Output nothing
else inside the tags."""
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
    candidates = blocks if blocks else re.findall(r"```(?:json)?\s*(.*?)```", text, re.I | re.S)
    for raw in reversed(candidates):
        try:
            value = json.loads(raw.strip())
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, list) and all(type(x) is int for x in value):
            return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
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
    if answer[0] != 0:
        return False, "noncanonical_rotation"
    if answer[1] >= answer[-1]:
        return False, "noncanonical_reflection"

    edges = {tuple(sorted(e)) for e in inst["host_edges"]}
    for i, u in enumerate(answer):
        v = answer[(i + 1) % n]
        if tuple(sorted((u, v))) not in edges:
            return False, f"missing_host_edge_at_position_{i}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the normalized permutation language, not n^n noise."""
    rest = list(range(1, inst["n"]))
    rng.shuffle(rest)
    answer = [0] + rest
    if answer[1] > answer[-1]:
        answer = [0] + list(reversed(answer[1:]))
    return answer


def search_space(inst: dict) -> int | None:
    return math.factorial(inst["n"] - 1) // 2


def enumerate_all(inst: dict) -> int | None:
    if search_space(inst) > 200_000:
        return None
    n = inst["n"]
    edges = {tuple(sorted(e)) for e in inst["host_edges"]}
    count = 0
    for tail in itertools.permutations(range(1, n)):
        if tail[0] >= tail[-1]:
            continue
        order = (0,) + tail
        if all(
            tuple(sorted((order[i], order[(i + 1) % n]))) in edges
            for i in range(n)
        ):
            count += 1
    return count


def _adjacency(inst: dict) -> list[list[int]]:
    adj = [[] for _ in range(inst["n"])]
    for u, v in inst["host_edges"]:
        adj[u].append(v)
        adj[v].append(u)
    for row in adj:
        row.sort()
    return adj


def canonical_key(inst: dict) -> str:
    """A strong relabelling invariant from all directed-edge distance profiles."""
    n = inst["n"]
    adj = _adjacency(inst)
    distances: list[list[int]] = []
    for source in range(n):
        dist = [-1] * n
        dist[source] = 0
        queue = deque([source])
        while queue:
            u = queue.popleft()
            for v in adj[u]:
                if dist[v] < 0:
                    dist[v] = dist[u] + 1
                    queue.append(v)
        distances.append(dist)

    vertex_profiles = [tuple(Counter(row).get(d, 0) for d in range(n)) for row in distances]
    edge_profiles = []
    for u in range(n):
        for v in adj[u]:
            if u >= v:
                continue
            joint = Counter((distances[u][x], distances[v][x]) for x in range(n))
            forward = tuple(sorted(joint.items()))
            backward = tuple(sorted(((b, a), count) for (a, b), count in joint.items()))
            endpoint_pair = tuple(sorted((vertex_profiles[u], vertex_profiles[v])))
            edge_profiles.append((endpoint_pair, min(forward, backward)))
    payload = json.dumps([n, sorted(vertex_profiles), sorted(edge_profiles)], separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    n = int(params.get("n", 0))
    # A spanning-cycle witness necessarily grows with the host.  The named
    # ladder already reaches the no-tool operation ceiling; the next meaningful
    # sizes would eventually violate the 256-atom output cap.
    if n < 196:
        return {"n": 196}
    if n < 240:
        return {"n": 240}
    return "cap_bound"


def _candidate_from_path(path: list[int] | None) -> list[int] | None:
    if path is None:
        return None
    return _normalize_cycle(path)


def _attack_label_order(inst: dict) -> list[int] | None:
    return list(range(inst["n"]))


def _attack_greedy(inst: dict) -> list[int] | None:
    adj = _adjacency(inst)
    n = inst["n"]
    path = [0]
    seen = {0}
    while len(path) < n:
        choices = [v for v in adj[path[-1]] if v not in seen]
        if not choices:
            return None
        choices.sort(key=lambda v: (sum(w not in seen for w in adj[v]), v))
        nxt = choices[0]
        path.append(nxt)
        seen.add(nxt)
    if path[0] not in adj[path[-1]]:
        return None
    return _candidate_from_path(path)


def _attack_random_restarts(
    inst: dict, rng: random.Random, restarts: int = 64
) -> tuple[list[int] | None, int]:
    adj = _adjacency(inst)
    n = inst["n"]
    operations = 0
    for _ in range(restarts):
        path = [0]
        seen = {0}
        while len(path) < n:
            choices = [v for v in adj[path[-1]] if v not in seen]
            operations += len(adj[path[-1]])
            if not choices:
                break
            # Prefer constrained vertices, but randomize equally constrained ties.
            scores = [(sum(w not in seen for w in adj[v]), v) for v in choices]
            best = min(s for s, _ in scores)
            tied = [v for s, v in scores if s == best]
            nxt = rng.choice(tied)
            path.append(nxt)
            seen.add(nxt)
        if len(path) == n and path[0] in adj[path[-1]]:
            return _candidate_from_path(path), operations
    return None, operations


def _attack_balanced_closed_neighborhoods(
    inst: dict, node_budget: int = 200_000
) -> tuple[list[int] | None, int]:
    """Exploit the hidden alternating parity as exact-2-in-4 constraints.

    If cycle vertices receive alternating bits, every vertex and its three
    neighbours contain two zeroes and two ones.  This DPLL search propagates
    those exact-cardinality constraints.  For a complete colouring it tests
    whether the bichromatic edges form one spanning cycle.
    """
    adj = _adjacency(inst)
    n = inst["n"]
    constraints = [tuple([u] + adj[u]) for u in range(n)]
    occurrences = [[] for _ in range(n)]
    for ci, constraint in enumerate(constraints):
        for vertex in constraint:
            occurrences[vertex].append(ci)

    assignment = [-1] * n
    assignment[0] = 0  # Complementing all bits gives the same cut.
    nodes = 0

    def cycle_from_assignment() -> list[int] | None:
        cut = [
            [v for v in adj[u] if assignment[u] != assignment[v]]
            for u in range(n)
        ]
        if any(len(row) != 2 for row in cut):
            return None
        order = [0]
        previous = -1
        current = 0
        while True:
            nxt = cut[current][0] if cut[current][0] != previous else cut[current][1]
            if nxt == 0:
                return _normalize_cycle(order) if len(order) == n else None
            if nxt in order:
                return None
            order.append(nxt)
            previous, current = current, nxt

    def visit() -> list[int] | None:
        nonlocal nodes
        nodes += 1
        if nodes > node_budget:
            return None

        forced_here: list[int] = []
        while True:
            progress = False
            for constraint in constraints:
                ones = sum(assignment[v] == 1 for v in constraint)
                unknown = [v for v in constraint if assignment[v] < 0]
                if ones > 2 or ones + len(unknown) < 2:
                    for vertex in reversed(forced_here):
                        assignment[vertex] = -1
                    return None
                forced = None
                if unknown and ones == 2:
                    forced = 0
                elif unknown and ones + len(unknown) == 2:
                    forced = 1
                if forced is not None:
                    for vertex in unknown:
                        if assignment[vertex] < 0:
                            assignment[vertex] = forced
                            forced_here.append(vertex)
                            progress = True
            if not progress:
                break

        if all(value >= 0 for value in assignment):
            result = cycle_from_assignment()
            if result is not None:
                return result
            for vertex in reversed(forced_here):
                assignment[vertex] = -1
            return None

        candidates = [v for v in range(n) if assignment[v] < 0]

        def score(vertex: int) -> tuple[int, int]:
            pressure = sum(
                12 - sum(assignment[x] < 0 for x in constraints[ci])
                for ci in occurrences[vertex]
            )
            return pressure, -vertex

        branch = max(candidates, key=score)
        for value in (0, 1):
            assignment[branch] = value
            result = visit()
            if result is not None:
                return result
            assignment[branch] = -1
            if nodes > node_budget:
                break
        for vertex in reversed(forced_here):
            assignment[vertex] = -1
        return None

    return visit(), nodes


def _attack_spectral_seriation(inst: dict) -> tuple[list[int] | None, int]:
    """Try to read a circular order from two deflated Laplacian-style modes."""
    adj = _adjacency(inst)
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
        # Power iteration on A+3I makes the nontrivial positive modes dominate
        # after the constant mode has been removed.
        for _ in range(180):
            values = [3.0 * vector[u] + sum(vector[v] for v in adj[u]) for u in range(n)]
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
            answer = _normalize_cycle(direction)
            if verify(inst, answer)[0]:
                return answer, operations
    return None, operations


def _attack_hamilton_dfs(
    inst: dict, node_budget: int = 250_000
) -> tuple[list[int] | None, int]:
    """A bounded exact depth-first Hamiltonian-cycle search with propagation."""
    adj = _adjacency(inst)
    n = inst["n"]
    seen = [False] * n
    seen[0] = True
    path = [0]
    nodes = 0
    exhausted = False

    def connected_remainder(current: int) -> bool:
        allowed = {u for u in range(n) if not seen[u]}
        allowed.add(current)
        allowed.add(0)
        stack = [current]
        reached = {current}
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if v in allowed and v not in reached:
                    reached.add(v)
                    stack.append(v)
        return allowed <= reached

    def visit(current: int) -> list[int] | None:
        nonlocal nodes, exhausted
        nodes += 1
        if nodes > node_budget:
            exhausted = True
            return None
        if len(path) == n:
            return path[:] if 0 in adj[current] else None

        # Every unvisited vertex must still be able to acquire two incident
        # cycle edges from the unvisited set plus the two path endpoints.
        endpoints = {current, 0}
        for u in range(n):
            if not seen[u]:
                available = sum((not seen[v]) or v in endpoints for v in adj[u])
                if available < 2:
                    return None
        if len(path) % 12 == 0 and not connected_remainder(current):
            return None

        choices = [v for v in adj[current] if not seen[v]]
        choices.sort(
            key=lambda v: (
                sum((not seen[w]) or w == 0 for w in adj[v]),
                v,
            )
        )
        for nxt in choices:
            seen[nxt] = True
            path.append(nxt)
            result = visit(nxt)
            if result is not None:
                return result
            path.pop()
            seen[nxt] = False
            if exhausted:
                return None
        return None

    return _candidate_from_path(visit(0)), nodes


def _cycle_from_matching(adj: list[list[int]], matching: list[tuple[int, int]]) -> list[int] | None:
    """Return the complementary 2-factor when it is one spanning cycle."""
    removed = {tuple(sorted(edge)) for edge in matching}
    complement = [
        [v for v in adj[u] if tuple(sorted((u, v))) not in removed]
        for u in range(len(adj))
    ]
    if any(len(row) != 2 for row in complement):
        return None
    order = [0]
    previous = -1
    current = 0
    while True:
        choices = [v for v in complement[current] if v != previous]
        if not choices:
            return None
        nxt = choices[0]
        if nxt == 0:
            return _normalize_cycle(order) if len(order) == len(adj) else None
        if nxt in order:
            return None
        order.append(nxt)
        previous, current = current, nxt


def _attack_matching_complement(
    inst: dict, node_budget: int = 200_000
) -> tuple[list[int] | None, int]:
    """Enumerate perfect matchings; in a cubic graph their complements are 2-factors."""
    adj = _adjacency(inst)
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
            return _cycle_from_matching(adj, chosen)
        current = min(
            unmatched,
            key=lambda u: (sum(not matched[v] for v in adj[u]), u),
        )
        choices = [v for v in adj[current] if not matched[v]]
        for nxt in choices:
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
    out = dict(inst)
    out["host_vertices"] = list(range(n))
    out["host_edges"] = [
        sorted((permutation[u], permutation[v])) for u, v in inst["host_edges"]
    ]
    random.Random(reorder_seed).shuffle(out["host_edges"])
    out["answer"] = _normalize_cycle([permutation[v] for v in inst["answer"]])
    return out


# Filled from the three isolated harden.py runs.  They are data, not a claim
# inferred by selftest; update only from their transcripts.
_G9_ARMS = {
    # The bare shipping rung completed two genuine attempts before the required
    # third attempt timed out and redraws hit the OpenRouter account limit.
    "bare": {"solved": 0, "attempts": 2},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}
_G9_HINTED_VERDICT = "not_run"


def selftest() -> dict:
    report: dict[str, object] = {
        "paper": "0909.4692",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    # G1: every named rung and several independent seeds.
    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2, 19):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed, "reason": "not_json_native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=731, **ship_params)
    planted = inst["answer"]

    # G2: choose a swap that genuinely breaks an edge, and demand five distinct
    # rejection codes (prefix before optional detail).
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
        if not ok and why.startswith("missing_host_edge"):
            swapped = trial
            break
    corruptions["swap"] = swapped if swapped is not None else planted[1:] + planted[:1]
    corruption_results = {}
    reasons = []
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        code = why.split(":", 1)[0]
        if code.startswith("missing_host_edge"):
            code = "missing_host_edge"
        corruption_results[name] = {"rejected": not ok, "reason": why}
        reasons.append(code)
    report["G2_rejects_corruption"] = {
        "pass": all(x["rejected"] for x in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reason_codes": len(set(reasons)),
    }

    # G3: realistic surrounding prose and a fenced JSON answer inside the tags.
    response = (
        "I followed the cycle and checked the closing edge.\n\n"
        "<answer>\n" + json.dumps(planted) + "\n</answer>\n"
        "The list is normalized as requested."
    )
    parsed = parse_answer(response)
    parsed_ok, parsed_why = verify(inst, parsed)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parsed_ok,
        "parsed_equals_answer": parsed == planted,
        "verify_reason": parsed_why,
        "garbage_returns_none": parse_answer("no delimited answer here") is None,
    }

    # G4/G5 density at the actual shipping preset, using the normalized
    # permutation language that a reader gets for free from the statement.
    guess_rng = random.Random(20260905)
    guess_total = 200_000
    guess_hits = 0
    t0 = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            guess_hits += 1
    density_seconds = time.perf_counter() - t0
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "candidate_prior": "uniform normalized permutations of all host vertices",
        "search_space": str(search_space(inst)),
    }

    demo = make_instance(seed=731, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)

    # G6 and the G5 strongest-baseline measurement share the same eight runs.
    attack_seeds = list(range(9100, 9108))
    successes = {
        "label_order_outlier": 0,
        "greedy_constrained_walk": 0,
        "random_restart_64": 0,
        "spectral_cycle_seriation": 0,
        "balanced_closed_neighborhood_dpll_200k": 0,
        "perfect_matching_complement_200k": 0,
    }
    random_operations = 0
    spectral_operations = 0
    balanced_nodes = 0
    balanced_wall = 0.0
    balanced_per_seed_nodes = []
    dfs_nodes = 0
    dfs_wall = 0.0
    per_seed_nodes = []
    for seed in attack_seeds:
        attack_inst = make_instance(seed=seed, **ship_params)
        if _valid_if_any(attack_inst, _attack_label_order(attack_inst)):
            successes["label_order_outlier"] += 1
        if _valid_if_any(attack_inst, _attack_greedy(attack_inst)):
            successes["greedy_constrained_walk"] += 1
        cand, ops = _attack_random_restarts(
            attack_inst, random.Random(seed ^ 0x5A17), restarts=64
        )
        random_operations += ops
        if _valid_if_any(attack_inst, cand):
            successes["random_restart_64"] += 1
        cand, ops = _attack_spectral_seriation(attack_inst)
        spectral_operations += ops
        if _valid_if_any(attack_inst, cand):
            successes["spectral_cycle_seriation"] += 1
        start = time.perf_counter()
        cand, nodes = _attack_balanced_closed_neighborhoods(
            attack_inst, node_budget=200_000
        )
        balanced_wall += time.perf_counter() - start
        balanced_nodes += nodes
        balanced_per_seed_nodes.append(nodes)
        if _valid_if_any(attack_inst, cand):
            successes["balanced_closed_neighborhood_dpll_200k"] += 1
        start = time.perf_counter()
        cand, nodes = _attack_matching_complement(attack_inst, node_budget=200_000)
        elapsed = time.perf_counter() - start
        dfs_wall += elapsed
        dfs_nodes += nodes
        per_seed_nodes.append(nodes)
        if _valid_if_any(attack_inst, cand):
            successes["perfect_matching_complement_200k"] += 1

    attacks = {
        name: {"successes": count, "attempts": len(attack_seeds)}
        for name, count in successes.items()
    }
    attacks["random_restart_64"]["operations"] = random_operations
    attacks["spectral_cycle_seriation"]["operations"] = spectral_operations
    attacks["balanced_closed_neighborhood_dpll_200k"].update(
        {
            "nodes": balanced_nodes,
            "wall_clock_sec": round(balanced_wall, 6),
            "nodes_per_seed": balanced_per_seed_nodes,
            "construction_aware": True,
        }
    )
    attacks["perfect_matching_complement_200k"].update(
        {
            "nodes": dfs_nodes,
            "wall_clock_sec": round(dfs_wall, 6),
            "nodes_per_seed": per_seed_nodes,
            "standard_algorithm": True,
        }
    )
    ordered_balanced_nodes = sorted(balanced_per_seed_nodes)
    balanced_median_nodes = (
        ordered_balanced_nodes[3] + ordered_balanced_nodes[4]
    ) // 2
    all_failed = all(x["successes"] == 0 for x in attacks.values())
    report["G5_density_and_baseline"] = {
        "pass": guess_hits / guess_total < 1e-6 and all_failed and dfs_nodes > 0,
        "shipping_density": {
            "hits": guess_hits,
            "samples": guess_total,
            "observed_fraction": guess_hits / guess_total,
            "wall_clock_sec": round(density_seconds, 6),
        },
        "demo_exact_valid_answers": demo_count,
        "demo_search_space": search_space(demo),
        "strongest_attack": {
            "name": "exact-2-in-4 closed-neighborhood DPLL",
            "wall_clock_sec": round(balanced_wall, 6),
            "nodes": balanced_nodes,
            "median_nodes": balanced_median_nodes,
            "attempts": len(attack_seeds),
            "successes": successes["balanced_closed_neighborhood_dpll_200k"],
        },
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and len(attacks) >= 4,
        "attacks": attacks,
    }

    doubled_params = {"n": ship_params["n"] * 2}
    scale_start = time.perf_counter()
    doubled = make_instance(seed=4471, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] > inst["n"],
        "base_n": inst["n"],
        "doubled_n": doubled["n"],
        "build_and_verify_sec": round(time.perf_counter() - scale_start, 6),
        "verify_reason": doubled_why,
    }

    # G8: vertex relabelling, edge-order changes, and their composition.
    invariance_checks = 0
    transport_checks = 0
    transformed_different = 0
    keys = []
    for seed in range(20):
        original = make_instance(seed=12000 + seed, **ship_params)
        key = canonical_key(original)
        keys.append(key)
        rng = random.Random(33000 + seed)
        p = list(range(original["n"]))
        q = list(range(original["n"]))
        rng.shuffle(p)
        rng.shuffle(q)
        composed = [q[p[i]] for i in range(original["n"])]
        variants = [
            _relabel_instance(original, p, 44000 + seed),
            _relabel_instance(original, list(range(original["n"])), 55000 + seed),
            _relabel_instance(original, composed, 66000 + seed),
        ]
        for variant in variants:
            invariance_checks += 1
            if canonical_key(variant) != key:
                break
            ok, _ = verify(variant, variant["answer"])
            transport_checks += int(ok)
            transformed_different += int(variant["host_edges"] != original["host_edges"])
    report["G8_canonical_key"] = {
        "pass": invariance_checks == 60
        and transport_checks == 60
        and transformed_different >= 20
        and len(set(keys)) == 20,
        "invariance_checks": invariance_checks,
        "witness_transport_checks": transport_checks,
        "nontrivial_transformations": transformed_different,
        "unrelated_distinct": len(set(keys)),
        "unrelated_attempts": len(keys),
        "invariant": "multiset of all directed-edge distance-pair profiles",
    }

    answer_blob = json.dumps(inst["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    # The duality observation does not identify the omitted matching.  The
    # shortest reproducible post-insight route found in the rejection audit is
    # the exact-2-in-4 search above; its node count is already a lower bound on
    # its exact operations and is far over the no-tool cap.
    intended_ops = balanced_median_nodes
    hinted = _G9_ARMS["hinted"]
    placebo = _G9_ARMS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    within_caps = answer_chars <= 2000 and inst["n"] <= 256 and intended_ops <= 300
    hinted_hardened = _G9_HINTED_VERDICT == "hardened"
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": _G9_ARMS,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _G9_HINTED_VERDICT,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": inst["n"],
        "intended_route_operations": intended_ops,
        "caps_pass": within_caps,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(bool(gate.get("pass")) for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
