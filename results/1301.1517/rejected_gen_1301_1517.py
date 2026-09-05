"""Verified K-cycle generator for arXiv:1301.1517.

Wahlstrom's Definition 1 asks for a simple cycle through every terminal.  This
module uses the native special case K=V, which Section 1 identifies with
Hamiltonian Cycle.  The certificate is generated without solving the emitted
graph: closed walks in a hidden even-degree root graph are composed first, and
their root edges become vertices of its line graph.  Consecutive root edges in
the composed Euler circuit are adjacent in the line graph, so the carried list
is a Hamiltonian cycle by construction.
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
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "simple undirected graph",
        "specified terminal vertices",
        "simple cycle through all terminals",
    ],
    "verification_operations": [
        "integer range and distinctness checks",
        "exact undirected-edge membership",
        "cyclic closure check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize the graph as the line graph of a hidden even-degree graph: "
        "its edge partition into root-star cliques turns the requested cycle "
        "into an Euler circuit, while an unstructured solver searches vertex orders."
    ),
    "hardness_basis": (
        "Rejected Track B candidate: Lehot's optimal line-graph recognition and "
        "root-reconstruction algorithm runs in E+O(N), followed by linear-time "
        "Hierholzer; at the 64-vertex, 160-edge preset this is about 328 graph-item "
        "visits including the 40-vertex, 64-edge root traversal, versus 224 "
        "incidence/traversal operations for the claimed compact route, so there "
        "is no meaningful compression gap."
    ),
    "max_answer_tokens": 62,
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

# n counts vertices of the hidden root graph.  Each square adds four root
# edges, hence four vertices to the displayed line graph and to the answer.
DIFFICULTY = {
    "demo": {"n": 6, "decoy_cycles": 0},
    "easy": {"n": 36, "decoy_cycles": 6},
    "medium": {"n": 40, "decoy_cycles": 6},
    "hard": {"n": 44, "decoy_cycles": 7},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "The graph edges partition into root-star cliques that are the incidence "
    "structure of a hidden even-degree graph."
)
PLACEBO_HINT = (
    "The graph data rewards careful tracking of adjacency and the cyclic endpoint convention."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list containing every graph vertex exactly once in cyclic order, "
        "canonically rotated to start at 0 and oriented so the second entry is "
        "smaller than the last."
    ),
    "bounds": {
        "length": "the displayed vertex count N = n + 4*decoy_cycles",
        "entry_min": 0,
        "entry_max": "N-1",
        "distinct": True,
        "canonical_start": 0,
        "canonical_orientation": "second entry < last entry",
        "candidate_count": "(N-1)!/2",
    },
}

NOTES = (
    "Section 3, Definition 1 fixes a K-cycle as one cycle containing every "
    "terminal, while allowing other vertices; Section 1 identifies K=V with "
    "Hamiltonian Cycle. Lemma 3 says the one-terminal case is polynomial and "
    "Theorem 2 gives the O*(2^k) determinant-sum algorithm, so k must grow and "
    "this cannot honestly be Track A once the structured subclass algorithm is "
    "known. Generation composes a spanning root cycle with edge-disjoint square "
    "detours, then carries that Euler circuit through the line-graph transform "
    "and a random relabelling. Vertex labels and input-edge order are shuffled. "
    "The adversary panel tests degree ordering, input ordering, a lowest-label "
    "walk, 256 random self-avoiding walks, and a high-onward-degree by-hand rule. "
    "The successful dense clique reconstruction is reported separately as the "
    "Track B reference algorithm. A final audit found that this O(N^3) reference "
    "was not the strongest known method: Lehot (JACM 1974) recognizes a line graph "
    "and outputs its root in E+O(N) steps. That linear routine followed by "
    "Hierholzer is essentially the intended route itself, so the family is retained "
    "only as a rejected generator; see REJECTED.md."
)


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_GUESS_SAMPLES = 200_000


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _norm_edge(u, v):
    return (u, v) if u < v else (v, u)


def _cycle_edges(vertices):
    return [
        _norm_edge(vertices[i], vertices[(i + 1) % len(vertices)])
        for i in range(len(vertices))
    ]


def _canonical_cycle(cycle):
    """Canonicalize a permutation up to rotation and reversal."""
    if not cycle:
        return []
    at = cycle.index(0)
    out = list(cycle[at:]) + list(cycle[:at])
    if len(out) > 2 and out[1] > out[-1]:
        out = [out[0]] + list(reversed(out[1:]))
    return out


def _validate_params(n, decoy_cycles, seed):
    if not _is_int(n) or n < 6 or n % 2:
        raise ValueError("n must be an even integer at least 6")
    if not _is_int(decoy_cycles) or decoy_cycles < 0:
        raise ValueError("decoy_cycles must be a nonnegative integer")
    if 4 * decoy_cycles > n:
        raise ValueError("vertex-disjoint square detours require 4*decoy_cycles <= n")
    if not _is_int(seed):
        raise ValueError("seed must be an integer")


def _choose_root_cycles(n, decoy_cycles, rng):
    """Return a spanning even cycle and disjoint square detours.

    The bipartition makes the root graph triangle-free.  A whole set of square
    detours is resampled only to avoid reusing a root edge; the Euler witness is
    already known as the composition of the returned closed walks.
    """
    half = n // 2
    left = list(range(half))
    right = list(range(half, n))
    rng.shuffle(left)
    rng.shuffle(right)
    base = []
    for u, v in zip(left, right):
        base.extend((u, v))
    base_edges = set(_cycle_edges(base))
    if decoy_cycles == 0:
        return [base]

    for _ in range(20_000):
        ls = left[:]
        rs = right[:]
        rng.shuffle(ls)
        rng.shuffle(rs)
        squares = []
        used = set(base_edges)
        ok = True
        for index in range(decoy_cycles):
            a, b = ls[2 * index:2 * index + 2]
            c, d = rs[2 * index:2 * index + 2]
            square = [a, c, b, d]
            edges = _cycle_edges(square)
            if len(set(edges)) != 4 or any(edge in used for edge in edges):
                ok = False
                break
            used.update(edges)
            squares.append(square)
        if ok:
            return [base] + squares
    raise RuntimeError("could not place edge-disjoint square detours")


def _compose_euler_walk(cycles):
    """Compose closed walks by inserting each square at its root vertex."""
    root_edges = []
    edge_id = {}
    cycle_ids = []
    for cycle in cycles:
        ids = []
        for edge in _cycle_edges(cycle):
            if edge in edge_id:
                raise ValueError("root cycles unexpectedly share an edge")
            edge_id[edge] = len(root_edges)
            root_edges.append(edge)
            ids.append(edge_id[edge])
        cycle_ids.append(ids)

    vertices = list(cycles[0]) + [cycles[0][0]]
    edge_walk = list(cycle_ids[0])
    for cycle, ids in zip(cycles[1:], cycle_ids[1:]):
        anchor = cycle[0]
        position = vertices[:-1].index(anchor)
        closed = list(cycle) + [anchor]
        vertices = (
            vertices[:position + 1]
            + closed[1:]
            + vertices[position + 1:]
        )
        edge_walk = edge_walk[:position] + list(ids) + edge_walk[position:]

    if len(edge_walk) != len(root_edges) or len(set(edge_walk)) != len(root_edges):
        raise AssertionError("composed walk is not Eulerian")
    for i, edge_index in enumerate(edge_walk):
        edge = root_edges[edge_index]
        if vertices[i] not in edge or vertices[i + 1] not in edge:
            raise AssertionError("composed walk does not follow its root edges")
    if vertices[0] != vertices[-1]:
        raise AssertionError("composed walk is not closed")
    return root_edges, edge_walk


def make_instance(n, seed=0, **params):
    """Build a K-cycle instance and carry its certificate by composition."""
    decoy_cycles = params.pop("decoy_cycles", 0)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, decoy_cycles, seed)
    rng = random.Random(seed)

    root_cycles = _choose_root_cycles(n, decoy_cycles, rng)
    root_edges, euler_edges = _compose_euler_walk(root_cycles)
    vertex_count = len(root_edges)

    # The line graph: one displayed vertex per root edge, adjacent exactly when
    # the two root edges have an endpoint in common.
    line_edges = []
    for i in range(vertex_count):
        a, b = root_edges[i]
        for j in range(i):
            c, d = root_edges[j]
            if a == c or a == d or b == c or b == d:
                line_edges.append((j, i))

    labels = list(range(vertex_count))
    rng.shuffle(labels)
    displayed_edges = [
        _norm_edge(labels[u], labels[v]) for u, v in line_edges
    ]
    rng.shuffle(displayed_edges)
    answer = _canonical_cycle([labels[edge] for edge in euler_edges])

    inst = {
        "paper": "arXiv:1301.1517",
        "family": "K-cycle in a relabelled line graph",
        "vertex_count": vertex_count,
        "terminals": list(range(vertex_count)),
        "edges": [list(edge) for edge in displayed_edges],
        "answer": answer,
    }
    ok, reason = verify(inst, answer)
    if not ok:
        raise AssertionError("constructed witness failed: " + reason)
    return inst


def _instance_data(inst):
    cached = inst.get("_data_cache") if isinstance(inst, dict) else None
    if isinstance(cached, tuple) and len(cached) == 2:
        return cached, "ok"
    try:
        n = inst["vertex_count"]
        terminals = inst["terminals"]
        edges = inst["edges"]
    except (KeyError, TypeError):
        return None, "instance fields are missing"
    if not _is_int(n) or n < 3:
        return None, "invalid vertex count"
    if terminals != list(range(n)):
        return None, "this family requires every vertex to be a terminal"
    if not isinstance(edges, list):
        return None, "edge list is malformed"
    seen = set()
    adjacency = [set() for _ in range(n)]
    for edge in edges:
        if (not isinstance(edge, list) or len(edge) != 2
                or any(not _is_int(v) for v in edge)):
            return None, "edge list is malformed"
        u, v = edge
        if not (0 <= u < n and 0 <= v < n) or u == v:
            return None, "edge endpoint is invalid"
        normalized = _norm_edge(u, v)
        if normalized in seen:
            return None, "duplicate undirected edge"
        seen.add(normalized)
        adjacency[u].add(v)
        adjacency[v].add(u)
    data = (n, adjacency)
    inst["_data_cache"] = data
    return data, "ok"


def verify(inst, answer):
    """Check any canonical Hamiltonian-cycle witness; never read inst['answer']."""
    data, reason = _instance_data(inst)
    if data is None:
        return False, reason
    n, adjacency = data
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer must not be empty"
    if len(answer) != n:
        return False, f"wrong length: expected {n} vertices"
    if any(not _is_int(v) for v in answer):
        return False, "every cycle entry must be an integer"
    if any(v < 0 or v >= n for v in answer):
        return False, f"vertex outside the inclusive range 0..{n - 1}"
    if len(set(answer)) != n:
        return False, "cycle vertices must be distinct"
    if answer[0] != 0:
        return False, "canonical cycle must start with vertex 0"
    if answer[1] >= answer[-1]:
        return False, "canonical orientation requires second entry < last entry"
    for index, u in enumerate(answer):
        v = answer[(index + 1) % n]
        if v not in adjacency[u]:
            return False, f"missing cycle edge between consecutive vertices {u} and {v}"
    return True, "ok"


def render(inst):
    data, reason = _instance_data(inst)
    if data is None:
        raise ValueError(reason)
    n, _ = data
    lines = [
        "Cycle through every specified terminal",
        "",
        f"The input is a simple undirected graph on vertices 0 through {n - 1}.",
        "An edge 'u v' may be traversed in either direction. Every graph vertex",
        "is a terminal. A simple cycle is a cyclic list of distinct vertices in",
        "which every consecutive pair is an edge, including the last vertex paired",
        "with the first. Find one simple cycle containing every terminal; therefore",
        f"your list must contain each of the {n} vertices exactly once.",
        "",
        "To give rotations and reversals one output spelling, start the list with 0",
        "and choose its direction so that the second entry is smaller than the last.",
        "Vertices are 0-indexed. Repeats are forbidden. All bounds are inclusive.",
        "",
        f"Terminals ({n}): " + " ".join(map(str, inst["terminals"])),
        f"Edges ({len(inst['edges'])}), one per line:",
    ]
    lines.extend(f"{u} {v}" for u, v in inst["edges"])
    example = list(range(min(n, 6)))
    if n > 6:
        example.append("...")
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as one JSON list of",
        f"exactly {n} integers satisfying the canonical start and direction rules.",
        "Format example only: <answer>" + json.dumps(example) + "</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def random_candidate(inst, rng):
    data, reason = _instance_data(inst)
    if data is None:
        raise ValueError(reason)
    n, _ = data
    tail = list(range(1, n))
    rng.shuffle(tail)
    candidate = [0] + tail
    if candidate[1] > candidate[-1]:
        candidate = [0] + list(reversed(candidate[1:]))
    return candidate


def search_space(inst):
    data, reason = _instance_data(inst)
    if data is None:
        raise ValueError(reason)
    n, _ = data
    return math.factorial(n - 1) // 2


def enumerate_all(inst):
    if search_space(inst) > 200_000:
        return None
    data, _ = _instance_data(inst)
    n, _ = data
    count = 0
    for tail in itertools.permutations(range(1, n)):
        if tail[0] < tail[-1] and verify(inst, [0] + list(tail))[0]:
            count += 1
    return count


def _recover_root(inst, dense=False):
    """Recover the triangle-free root's star cliques and an Euler cycle.

    With ``dense=True`` all vertex-pair neighborhood intersections are computed;
    this is the deliberately mechanical O(N^3) Track-B reference whose exact
    adjacency-query count is reported.  The fast form is used only for canonical
    keys and validation work.
    """
    data, reason = _instance_data(inst)
    if data is None:
        return None, 0, reason
    n, adjacency = data
    blocks = set()
    operations = 0
    pairs = itertools.combinations(range(n), 2) if dense else (
        (u, v) for u in range(n) for v in adjacency[u] if u < v
    )
    for u, v in pairs:
        adjacent = v in adjacency[u]
        operations += 1
        common = []
        if dense or adjacent:
            for w in range(n):
                left = w in adjacency[u]
                right = w in adjacency[v]
                operations += 2
                if left and right:
                    common.append(w)
        if adjacent:
            block = frozenset([u, v] + common)
            if any(y not in adjacency[x]
                   for x, y in itertools.combinations(block, 2)):
                return None, operations, "neighborhood intersection is not a root-star clique"
            blocks.add(block)
    blocks = sorted(blocks, key=lambda block: (len(block), tuple(sorted(block))))
    if len(blocks) < 3:
        return None, operations, "too few recovered root-star cliques"

    edge_owners = {}
    for u in range(n):
        for v in adjacency[u]:
            if u < v:
                owners = [i for i, block in enumerate(blocks) if u in block and v in block]
                operations += len(blocks)
                if len(owners) != 1:
                    return None, operations, "line edge does not belong to one root-star clique"
                edge_owners[(u, v)] = owners[0]

    incident = [[] for _ in range(n)]
    for block_index, block in enumerate(blocks):
        for line_vertex in block:
            incident[line_vertex].append(block_index)
            operations += 1
    if any(len(owners) != 2 for owners in incident):
        return None, operations, "a line vertex does not have two root endpoints"

    root_adj = [[] for _ in blocks]
    for line_vertex, (u, v) in enumerate(incident):
        if u == v:
            return None, operations, "root edge has identical endpoints"
        root_adj[u].append((line_vertex, v))
        root_adj[v].append((line_vertex, u))
        operations += 2
    if any(len(row) % 2 for row in root_adj):
        return None, operations, "recovered root has odd degree"

    # Deterministic Hierholzer traversal.  Incoming edge IDs emitted during
    # backtracking, then reversed, are a cyclic order of all line vertices.
    work = [sorted(row, reverse=True) for row in root_adj]
    used = set()
    stack = [(0, None)]
    reversed_edges = []
    while stack:
        vertex = stack[-1][0]
        while work[vertex] and work[vertex][-1][0] in used:
            work[vertex].pop()
            operations += 1
        if work[vertex]:
            edge, other = work[vertex].pop()
            operations += 1
            if edge in used:
                continue
            used.add(edge)
            stack.append((other, edge))
        else:
            _, incoming = stack.pop()
            if incoming is not None:
                reversed_edges.append(incoming)
    if len(used) != n:
        return None, operations, "recovered root is disconnected"
    answer = _canonical_cycle(list(reversed(reversed_edges)))
    ok, reason = verify(inst, answer)
    return (answer if ok else None), operations, reason


def _root_adjacency(inst):
    """Return the recovered unlabelled root graph for canonicalization."""
    data, reason = _instance_data(inst)
    if data is None:
        raise ValueError(reason)
    n, adjacency = data
    blocks = set()
    for u in range(n):
        for v in adjacency[u]:
            if u < v:
                common = adjacency[u] & adjacency[v]
                blocks.add(frozenset([u, v]) | common)
    blocks = sorted(blocks, key=lambda b: (len(b), tuple(sorted(b))))
    incident = [[] for _ in range(n)]
    for index, block in enumerate(blocks):
        for v in block:
            incident[v].append(index)
    if any(len(row) != 2 for row in incident):
        raise ValueError("cannot canonicalize a non-line-graph instance")
    root = [set() for _ in blocks]
    for owners in incident:
        u, v = owners
        root[u].add(v)
        root[v].add(u)
    return root


def _distance_profile(adjacency, start):
    distances = [-1] * len(adjacency)
    distances[start] = 0
    queue = deque([start])
    while queue:
        u = queue.popleft()
        for v in adjacency[u]:
            if distances[v] < 0:
                distances[v] = distances[u] + 1
                queue.append(v)
    if any(value < 0 for value in distances):
        return (len(adjacency),)
    return tuple(distances.count(d) for d in range(max(distances) + 1))


def _root_invariant(adjacency):
    """A strong relabelling invariant based on distances and color refinement."""
    n = len(adjacency)
    profiles = [_distance_profile(adjacency, v) for v in range(n)]
    signatures = [(len(adjacency[v]), profiles[v]) for v in range(n)]

    def compress(values):
        order = {value: index for index, value in enumerate(sorted(set(values)))}
        return [order[value] for value in values]

    colors = compress(signatures)
    for _ in range(n):
        refined = [
            (colors[v], tuple(sorted(colors[w] for w in adjacency[v])), profiles[v])
            for v in range(n)
        ]
        new_colors = compress(refined)
        if new_colors == colors:
            break
        colors = new_colors
    vertex_data = sorted(
        (colors[v], profiles[v], tuple(sorted(colors[w] for w in adjacency[v])))
        for v in range(n)
    )
    edge_colors = sorted(
        (min(colors[u], colors[v]), max(colors[u], colors[v]))
        for u in range(n) for v in adjacency[u] if u < v
    )
    return [n, vertex_data, edge_colors]


def canonical_key(inst):
    payload = json.dumps(_root_invariant(_root_adjacency(inst)), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def escalate(params):
    out = dict(params)
    n = int(out.get("n", 36))
    squares = int(out.get("decoy_cycles", 6))
    # Grow the root while keeping the six/square certificate component count
    # fixed; this first enlarges the low-degree haystack more than the detours.
    if n < 64 and (2 * (n + 4) + 24 * squares) <= 300:
        out["n"] = n + 4
        out["decoy_cycles"] = squares
        return out
    return "cap_bound"


def _attack_input_order(inst, _rng):
    return list(range(inst["vertex_count"]))


def _attack_degree_order(inst, _rng):
    data, _ = _instance_data(inst)
    n, adjacency = data
    return _canonical_cycle(sorted(range(n), key=lambda v: (len(adjacency[v]), v)))


def _greedy_walk(inst, rng, rule):
    data, _ = _instance_data(inst)
    n, adjacency = data
    path = [0]
    used = {0}
    while len(path) < n:
        choices = [v for v in adjacency[path[-1]] if v not in used]
        if not choices:
            return None
        if rule == "lowest":
            choice = min(choices)
        elif rule == "high_onward":
            choice = min(
                choices,
                key=lambda v: (-sum(w not in used for w in adjacency[v]), v),
            )
        elif rule == "random":
            choice = rng.choice(choices)
        else:
            raise ValueError("unknown greedy rule")
        path.append(choice)
        used.add(choice)
    if 0 not in adjacency[path[-1]]:
        return None
    return _canonical_cycle(path)


def _attack_random_walks(inst, rng, restarts=256):
    for _ in range(restarts):
        candidate = _greedy_walk(inst, rng, "random")
        if candidate is not None and verify(inst, candidate)[0]:
            return candidate
    return None


def _public_copy(inst):
    return json.loads(json.dumps({k: v for k, v in inst.items() if not k.startswith("_")}))


def _relabel_and_reorder(inst, rng):
    out = _public_copy(inst)
    n = out["vertex_count"]
    labels = list(range(n))
    rng.shuffle(labels)
    out["terminals"] = list(range(n))
    out["edges"] = [list(_norm_edge(labels[u], labels[v])) for u, v in out["edges"]]
    rng.shuffle(out["edges"])
    out["answer"] = _canonical_cycle([labels[v] for v in out["answer"]])
    return out


def _reorder_edges(inst, rng):
    out = _public_copy(inst)
    rng.shuffle(out["edges"])
    return out


G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 2, "attempts": 3},
    "placebo": {"solved": 1, "attempts": 3},
    "hinted_verdict": "too_easy (diagnostic only; retired as a gate)",
}


def selftest():
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    planted_failures = []
    planted_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            planted_attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                planted_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                planted_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not planted_failures,
        "attempts": planted_attempts,
        "failures": planted_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=20260905, **shipping_params)
    answer = shipping["answer"]
    corruptions = {
        "drop_one": answer[:-1],
        "swap_first_two": [answer[1], answer[0]] + answer[2:],
        "duplicate": answer[:-1] + [answer[-2]],
        "empty": [],
        "out_of_range": answer[:-1] + [shipping["vertex_count"]],
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [item["reason"] for item in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruption_results.values())
                and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
    }

    wire = json.dumps(answer)
    parsed = parse_answer(
        "I reconstructed the hidden incidence graph.\n"
        f"My final result is <answer>\n```json\n{wire}\n```\n</answer>."
    )
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("garbage") is None,
        "parsed_equals_answer": parsed == answer,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    guess_rng = random.Random(13011517)
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(_GUESS_SAMPLES):
        if verify(shipping, random_candidate(shipping, guess_rng))[0]:
            guess_hits += 1
    guess_seconds = time.perf_counter() - guess_start
    guess_fraction = guess_hits / _GUESS_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": _GUESS_SAMPLES,
        "observed_fraction": guess_fraction,
        "structure_aware_space": search_space(shipping),
        "sampling_wall_clock_sec": round(guess_seconds, 6),
    }

    ref_start = time.perf_counter()
    ref_answer, ref_operations, ref_reason = _recover_root(shipping, dense=True)
    ref_seconds = time.perf_counter() - ref_start
    ref_ok = ref_answer is not None and verify(shipping, ref_answer)[0]
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": ref_ok and guess_fraction < 1e-6 and demo_count is not None,
        "shipping_density_method": "structure-aware Monte Carlo",
        "shipping_sampled_hits": guess_hits,
        "shipping_sampled_total": _GUESS_SAMPLES,
        "shipping_sampled_fraction": guess_fraction,
        "shipping_candidate_count": search_space(shipping),
        "demo_exact_valid_answers": demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_name": "dense root-star reconstruction plus Hierholzer",
        "baseline_complexity": "O(N^3) exact adjacency queries",
        "baseline_wall_clock_sec": round(ref_seconds, 6),
        "baseline_operations": ref_operations,
        "baseline_reason": ref_reason,
    }

    attacks = {
        "outlier_low_degree_order": {"successes": 0, "attempts": 0},
        "greedy_lowest_label_walk": {"successes": 0, "attempts": 0},
        "random_restart_256_walks": {"successes": 0, "attempts": 0},
        "by_hand_high_onward_degree": {"successes": 0, "attempts": 0},
        "input_order_ansatz": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_operations = 0
    reference_seconds = 0.0
    for seed in range(7100, 7108):
        inst = make_instance(seed=seed, **shipping_params)
        rng = random.Random(seed ^ 0x51A7)
        candidates = {
            "outlier_low_degree_order": _attack_degree_order(inst, rng),
            "greedy_lowest_label_walk": _greedy_walk(inst, rng, "lowest"),
            "random_restart_256_walks": _attack_random_walks(inst, rng),
            "by_hand_high_onward_degree": _greedy_walk(inst, rng, "high_onward"),
            "input_order_ansatz": _attack_input_order(inst, rng),
        }
        for name, candidate in candidates.items():
            attacks[name]["attempts"] += 1
            if candidate is not None and verify(inst, candidate)[0]:
                attacks[name]["successes"] += 1
        started = time.perf_counter()
        candidate, operations, _ = _recover_root(inst, dense=True)
        reference_seconds += time.perf_counter() - started
        reference_operations += operations
        if candidate is not None and verify(inst, candidate)[0]:
            reference_successes += 1
    all_failed = all(
        item["successes"] == 0 and item["attempts"] >= 8
        for item in attacks.values()
    )
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "dense root-star reconstruction plus Hierholzer",
            "complexity": "O(N^3) exact adjacency queries, then O(N+E)",
            "wall_clock_sec_for_8": round(reference_seconds, 6),
            "operations_for_8": reference_operations,
            "solves": f"{reference_successes}/8, as expected on Track B",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=77, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(shipping),
        "shipping_root_vertices": shipping_params["n"],
        "doubled_root_vertices": doubled_params["n"],
        "shipping_displayed_vertices": shipping["vertex_count"],
        "doubled_displayed_vertices": doubled["vertex_count"],
        "shipping_space": search_space(shipping),
        "doubled_space": search_space(doubled),
        "doubled_planted_verifies": doubled_ok,
    }

    invariant_checks = 0
    transformed_checks = 0
    failures = []
    keys = set()
    for seed in range(20):
        inst = make_instance(seed=9000 + seed, **shipping_params)
        key = canonical_key(inst)
        keys.add(key)
        relabelled = _relabel_and_reorder(inst, random.Random(11000 + seed))
        reordered = _reorder_edges(inst, random.Random(12000 + seed))
        composed = _reorder_edges(relabelled, random.Random(13000 + seed))
        for label, transformed in (
            ("vertex relabelling plus edge reorder", relabelled),
            ("edge input reorder", reordered),
            ("composed relabelling and reorder", composed),
        ):
            invariant_checks += 1
            if canonical_key(transformed) != key:
                failures.append(f"seed {seed}: {label} changed key")
            if verify(transformed, transformed["answer"])[0]:
                transformed_checks += 1
            else:
                failures.append(f"seed {seed}: {label} broke carried witness")
    report["G8_canonical_key"] = {
        "pass": not failures and invariant_checks == 60
                and transformed_checks == 60 and len(keys) == 20,
        "invariance_checks": invariant_checks,
        "transformed_witness_checks": transformed_checks,
        "unrelated_distinct_keys": len(keys),
        "unrelated_attempts": 20,
        "failures": failures,
    }

    answer_blob = json.dumps(shipping["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(shipping["answer"])
    # In the compact route, recognize each of E_line root-star incidences once,
    # then traverse each of N hidden root edges once.
    intended_operations = len(shipping["edges"]) + shipping["vertex_count"]
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else 0.0
    )
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["H_final_hardness_audit"] = {
        "pass": False,
        "failed_track": "B",
        "mechanical_algorithm": (
            "Lehot optimal line-graph recognition/root reconstruction plus Hierholzer"
        ),
        "mechanical_complexity": "E + O(N), then O(|V_root|+|E_root|)",
        "shipping_line_vertices": 64,
        "shipping_line_edges": 160,
        "shipping_root_vertices": 40,
        "shipping_root_edges": 64,
        "mechanical_graph_item_visits_approx": 328,
        "compact_route_operations": intended_operations,
        "reason": "the mechanical and compact routes are the same linear method",
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G")
    ) and report["H_final_hardness_audit"]["pass"]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
