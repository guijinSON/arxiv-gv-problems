"""Verified generator for S-packing colorings of locally short subcubic graphs.

The native problem is from Section 2 (Theorem 2) of arXiv:2603.25113.
Instances are cyclic necklaces of triangle/square blocks joined by short paths.
Every graph is 1-saturated and every degree-3 vertex has local girth at most 4.
The answer is a concrete (1,2,2,2)-packing coloring.

Generation composes two already-colored graph tiles and then applies a random
vertex relabelling.  It never searches for a coloring of the completed graph.
The verifier independently checks graph distances and never reads inst["answer"].
"""

from __future__ import annotations

import hashlib
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
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "1-saturated subcubic graph",
        "local triangles and 4-cycles",
        "(1,2,2,2)-packing coloring",
    ],
    "verification_operations": [
        "exact graph adjacency check",
        "exact breadth-first graph distance through radius 2",
        "integer color-range comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Contract each local triangle or square to recognize the alternating cycle "
        "of degree-3 ports; without that decomposition one must run the paper's "
        "mechanical local-cycle coloring procedure or a generic coloring search."
    ),
    "hardness_basis": (
        "Track B: Section 2, Theorem 2 gives a constructive polynomial-time "
        "procedure for (1,2,2,2)-packing coloring of 1-saturated subcubic graphs "
        "with g3<=4; at shipping n=36 the audited repeated-BFS reference uses "
        "155,520 exact queue/edge operations and about 0.01 seconds, whereas the "
        "necklace decomposition route uses at most 288 assignments/traversal steps."
    ),
    "max_answer_tokens": 109,
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
    "demo": {"n": 1, "irregularity": 100},
    "easy": {"n": 18, "irregularity": 25},
    "medium": {"n": 27, "irregularity": 60},
    "hard": {"n": 36, "irregularity": 100},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The degree-3 vertices form an alternating cycle whose every other link lies "
    "inside one local triangle or square."
)
PLACEBO_HINT = (
    "Keep the four color names distinct and check every listed edge carefully "
    "before submitting the vector."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly |V| integers in {0,1,2,3}, indexed by vertices "
        "0,1,...,|V|-1; color 0 has radius 1 and colors 1,2,3 have radius 2."
    ),
    "bounds": {
        "length": "number of vertices = 6n",
        "entry_min": 0,
        "entry_max": 3,
        "candidate_count": "4^(6n)",
    },
}

NOTES = (
    "Section 1 fixes S-packing coloring as a partition in which equal color s_i "
    "requires graph distance greater than s_i. Section 2, Theorem 2 is the exact "
    "native regime used here: 1-saturated subcubic graphs with g3 at most 4 are "
    "(1,2,2,2)-packing colorable. Its proof is constructive by deleting a degree-2 "
    "vertex from each local triangle or a pair from each local 4-cycle and extending "
    "the coloring; the introduction explicitly says these proofs yield efficient "
    "algorithms, ruling out Track A. Section 5, Propositions 5--7 show what becomes "
    "easy to falsify when a color is removed, local girth reaches 5, or saturation "
    "reaches 2. The generator stays inside the theorem by composing triangle/path "
    "and square/path tiles. Random relabelling and an irregular binary tile word "
    "defeat degree outliers, visible-order greedy coloring, random greedy restarts, "
    "and independent local orientations; the exact results are in selftest()."
)


# External oracle evidence is filled after the three harness runs.  The initial
# zeroes are explicit rather than pretending that local unit tests are LLM trials.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

# Verification is called hundreds of thousands of times on the same immutable
# instance during density measurement.  Cache only the derived adjacency, keyed
# by object identity and guarded by the object itself; no certificate data enters
# the cache.  The small cap avoids turning repeated API use into an unbounded leak.
_ADJ_CACHE = {}


def _add_edge(edges, u, v):
    if u == v:
        raise ValueError("loops are not allowed")
    edges.append((min(u, v), max(u, v)))


def _tile_word(n, irregularity, rng):
    """Return a nonconstant binary word without solving a graph instance."""
    if n == 1:
        return [rng.randrange(2)]
    bits = []
    for i in range(n):
        regular = i & 1
        bit = rng.randrange(2) if rng.randrange(100) < irregularity else regular
        bits.append(bit)
    if len(set(bits)) == 1:
        bits[rng.randrange(n)] ^= 1
    return bits


def make_instance(n, seed=0, **params):
    """Compose colored native graph tiles, then forget their hidden coordinates.

    ``n`` is the number of six-vertex tiles.  Tile 0 is a triangle whose outgoing
    connector has length four; tile 1 is a square whose connector has length
    three.  Both tiles have seven edges and use the same boundary colors, so any
    cyclic word of tiles composes.  The coloring is therefore known before the
    visible vertex permutation and is never found by search.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer")
    irregularity = params.pop("irregularity", 100)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if (
        isinstance(irregularity, bool)
        or not isinstance(irregularity, int)
        or not 0 <= irregularity <= 100
    ):
        raise ValueError("irregularity must be an integer from 0 through 100")

    rng = random.Random(seed)
    word = _tile_word(n, irregularity, rng)
    total = 6 * n
    edges = []
    hidden_colors = [None] * total

    # Hidden tile coordinates are consecutive only during construction.  They
    # are destroyed by the random permutation below and never included in inst.
    for i, kind in enumerate(word):
        base = 6 * i
        nxt_j = 6 * ((i + 1) % n)
        j, k = base, base + 1
        hidden_colors[j] = 1
        hidden_colors[k] = 2
        if kind == 0:  # triangle j-k-a-j, connector k-x-y-z-next_j
            a, x, y, z = base + 2, base + 3, base + 4, base + 5
            for u, v in ((j, k), (j, a), (a, k), (k, x), (x, y), (y, z), (z, nxt_j)):
                _add_edge(edges, u, v)
            hidden_colors[a] = 0
            hidden_colors[x] = 0
            hidden_colors[y] = 3
            hidden_colors[z] = 0
        else:  # square j-a-k-b-j, connector k-x-y-next_j
            a, b, x, y = base + 2, base + 3, base + 4, base + 5
            for u, v in ((j, a), (a, k), (k, b), (b, j), (k, x), (x, y), (y, nxt_j)):
                _add_edge(edges, u, v)
            hidden_colors[a] = 0
            hidden_colors[b] = 0
            hidden_colors[x] = 0
            hidden_colors[y] = 3

    if any(color is None for color in hidden_colors):
        raise AssertionError("incomplete composed coloring")
    if len(set(edges)) != len(edges):
        raise AssertionError("construction produced parallel edges")

    old_to_new = list(range(total))
    rng.shuffle(old_to_new)
    visible_edges = [
        (min(old_to_new[u], old_to_new[v]), max(old_to_new[u], old_to_new[v]))
        for u, v in edges
    ]
    rng.shuffle(visible_edges)
    answer = [0] * total
    for old, new in enumerate(old_to_new):
        answer[new] = hidden_colors[old]

    return {
        "family": "local-girth (1,2,2,2)-packing coloring",
        "n": n,
        "irregularity": irregularity,
        "num_vertices": total,
        "thresholds": [1, 2, 2, 2],
        "edges": [list(edge) for edge in visible_edges],
        "answer": answer,
    }


def _adjacency(inst):
    cached = _ADJ_CACHE.get(id(inst))
    if cached is not None and cached[0] is inst:
        return cached[1]
    n_vertices = inst.get("num_vertices")
    if isinstance(n_vertices, bool) or not isinstance(n_vertices, int) or n_vertices < 1:
        raise ValueError("invalid num_vertices")
    adj = [set() for _ in range(n_vertices)]
    seen = set()
    for raw in inst.get("edges", []):
        if not isinstance(raw, (list, tuple)) or len(raw) != 2:
            raise ValueError("every edge must have two endpoints")
        u, v = raw
        if (
            isinstance(u, bool)
            or isinstance(v, bool)
            or not isinstance(u, int)
            or not isinstance(v, int)
            or not 0 <= u < n_vertices
            or not 0 <= v < n_vertices
            or u == v
        ):
            raise ValueError("invalid edge endpoint")
        edge = (min(u, v), max(u, v))
        if edge in seen:
            raise ValueError("parallel edge")
        seen.add(edge)
        adj[u].add(v)
        adj[v].add(u)
    if len(_ADJ_CACHE) >= 256:
        _ADJ_CACHE.pop(next(iter(_ADJ_CACHE)))
    _ADJ_CACHE[id(inst)] = (inst, adj)
    return adj


def render(inst):
    n_vertices = inst["num_vertices"]
    edge_lines = []
    row = []
    for index, (u, v) in enumerate(inst["edges"], 1):
        row.append(f"{u}-{v}")
        if len(row) == 12 or index == len(inst["edges"]):
            edge_lines.append("  " + " ".join(row))
            row = []
    text = f"""Find an S-packing coloring of the finite simple undirected graph below.

There are {n_vertices} vertices, numbered 0 through {n_vertices - 1}.  Its undirected
edges are listed once each as u-v:
{chr(10).join(edge_lines)}

Use exactly one integer color from {{0,1,2,3}} on every vertex.  The answer position
is the vertex number: entry i is the color of vertex i.  Color 0 has packing radius
1, so two vertices colored 0 must have graph distance strictly greater than 1.
Colors 1, 2, and 3 each have packing radius 2, so two vertices with the same one of
those colors must have graph distance strictly greater than 2.  Graph distance is
the minimum number of edges in a path.  Distinct color numbers remain distinct even
though 1, 2, and 3 have equal radii.  All vertices must be colored; repeats are
allowed subject to these distance rules.

Give your final answer inside <answer></answer> tags, as one JSON list of exactly
{n_vertices} integers in vertex order.  Example syntax: <answer>[0,1,2,3]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def parse_answer(text):
    if not isinstance(text, str):
        return None
    bodies = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not bodies:
        return None
    for body in reversed(bodies):
        cleaned = body.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            value = json.loads(cleaned)
        except (TypeError, ValueError):
            # Tolerate a model omitting the brackets but keeping comma-separated ints.
            if re.fullmatch(r"\s*-?\d+(?:\s*,\s*-?\d+)*\s*", cleaned):
                try:
                    value = [int(piece.strip()) for piece in cleaned.split(",")]
                except ValueError:
                    continue
            else:
                continue
        if isinstance(value, list):
            return value
    return None


def verify(inst, answer):
    """Check any candidate coloring exactly; never consult the planted answer."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    n_vertices = inst.get("num_vertices")
    if len(answer) != n_vertices:
        return False, f"expected exactly {n_vertices} colors, received {len(answer)}"
    for vertex, color in enumerate(answer):
        if isinstance(color, bool) or not isinstance(color, int):
            return False, f"color at vertex {vertex} is not an integer"
        if not 0 <= color <= 3:
            return False, f"color at vertex {vertex} is outside 0..3"
    try:
        adj = _adjacency(inst)
    except (TypeError, ValueError) as exc:
        return False, f"malformed instance: {exc}"

    # Radius 1 needs only the edges.
    for u, neighbours in enumerate(adj):
        if answer[u] != 0:
            continue
        for v in neighbours:
            if u < v and answer[v] == 0:
                return False, f"color 0 conflict on adjacent vertices {u} and {v}"

    # For radii 2, inspect exactly the closed two-hop neighborhood of each vertex.
    for u in range(n_vertices):
        color = answer[u]
        if color == 0:
            continue
        near = set(adj[u])
        for w in adj[u]:
            near.update(adj[w])
        near.discard(u)
        for v in near:
            if u < v and answer[v] == color:
                return False, f"color {color} conflict within distance 2 at vertices {u} and {v}"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from the stated shape/range-aware coloring language."""
    return [rng.randrange(4) for _ in range(inst["num_vertices"])]


def search_space(inst):
    return 4 ** inst["num_vertices"]


def enumerate_all(inst):
    n_vertices = inst["num_vertices"]
    if n_vertices > 8:
        return None
    count = 0
    for code in range(4 ** n_vertices):
        value = code
        candidate = []
        for _ in range(n_vertices):
            candidate.append(value & 3)
            value >>= 2
        count += int(verify(inst, candidate)[0])
    return count


def _partner_data(adj):
    """Recognize each local triangle/square using graph data only."""
    degree3 = [v for v, neighbours in enumerate(adj) if len(neighbours) == 3]
    d3set = set(degree3)
    partners = {}
    arms = {}
    kinds = {}
    for pos, u in enumerate(degree3):
        for v in degree3[pos + 1 :]:
            common = (adj[u] & adj[v]) - d3set
            if v in adj[u] and len(common) == 1:
                kind = "T"
            elif v not in adj[u] and len(common) == 2:
                kind = "S"
            else:
                continue
            if u in partners or v in partners:
                raise ValueError("ambiguous local-cycle partner")
            partners[u] = v
            partners[v] = u
            arms[u] = set(common)
            arms[v] = set(common)
            kinds[u] = kind
            kinds[v] = kind
    if len(partners) != len(degree3):
        raise ValueError("not every degree-3 vertex has one local-cycle partner")
    return degree3, partners, arms, kinds


def _quotient_data(inst):
    """Return the graph-invariant alternating port cycle and connector paths."""
    adj = _adjacency(inst)
    degree3, partners, arms, kinds = _partner_data(adj)
    connector = {}
    paths = {}
    for u in degree3:
        forbidden = set(arms[u]) | {partners[u]}
        starts = adj[u] - forbidden
        if len(starts) != 1:
            raise ValueError("degree-3 port does not have one external path")
        previous, current = u, next(iter(starts))
        internal = []
        while len(adj[current]) == 2:
            internal.append(current)
            following = next(x for x in adj[current] if x != previous)
            previous, current = current, following
            if len(internal) > inst["num_vertices"]:
                raise ValueError("external path does not terminate")
        if len(adj[current]) != 3 or current == u:
            raise ValueError("external path has invalid endpoint")
        connector[u] = current
        paths[u] = list(internal)
    for u in degree3:
        if connector.get(connector[u]) != u:
            raise ValueError("connector relation is not symmetric")
        if len(paths[u]) not in (2, 3):
            raise ValueError("connector length is not 3 or 4")
    return adj, degree3, partners, arms, kinds, connector, paths


def _canonical_cycle_tokens(inst):
    _adj, degree3, partners, _arms, kinds, connector, paths = _quotient_data(inst)
    if len(degree3) == 2 and partners[degree3[0]] == connector[degree3[0]]:
        # For the one-tile demo, the partner link and connector link are parallel
        # only in the quotient (the original graph is still simple).
        u = degree3[0]
        return tuple(sorted((kinds[u], str(len(paths[u]) + 1))))
    qadj = {u: [partners[u], connector[u]] for u in degree3}
    if not degree3:
        raise ValueError("no degree-3 cycle")
    representations = []
    for start in degree3:
        for first in qadj[start]:
            tokens = []
            previous, current = start, first
            for _ in range(len(degree3)):
                if current == partners[previous]:
                    tokens.append(kinds[previous])
                else:
                    tokens.append(str(len(paths[previous]) + 1))
                nxt = qadj[current][0] if qadj[current][1] == previous else qadj[current][1]
                previous, current = current, nxt
            if previous != start or current != first:
                raise ValueError("quotient is not one cycle")
            representations.append(tuple(tokens))
    return min(representations)


def canonical_key(inst):
    """Canonicalize the edge-labelled degree-3 cycle, not the seed or rendering."""
    tokens = _canonical_cycle_tokens(inst)
    payload = json.dumps([inst["num_vertices"], list(tokens)], separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _structural_solve(inst):
    """The compact graph-decomposition route; uses no construction metadata."""
    adj, degree3, partners, arms, _kinds, connector, paths = _quotient_data(inst)
    qadj = {u: {partners[u], connector[u]} for u in degree3}
    port_color = {}
    todo = deque([degree3[0]])
    port_color[degree3[0]] = 1
    while todo:
        u = todo.popleft()
        for v in qadj[u]:
            want = 3 - port_color[u]
            if v in port_color and port_color[v] != want:
                raise ValueError("degree-3 quotient cycle is not bipartite")
            if v not in port_color:
                port_color[v] = want
                todo.append(v)
    if len(port_color) != len(degree3):
        raise ValueError("degree-3 quotient is disconnected")

    answer = [None] * inst["num_vertices"]
    for u, color in port_color.items():
        answer[u] = color
        for a in arms[u]:
            answer[a] = 0
    used_connectors = set()
    for u in degree3:
        v = connector[u]
        edge = (min(u, v), max(u, v))
        if edge in used_connectors:
            continue
        used_connectors.add(edge)
        internal = paths[u]
        if len(internal) == 3:
            connector_colors = [0, 3, 0]
        elif port_color[u] == 2:
            connector_colors = [0, 3]
        else:
            connector_colors = [3, 0]
        for vertex, color in zip(internal, connector_colors):
            answer[vertex] = color
    if any(color is None for color in answer):
        raise ValueError("decomposition left a vertex uncolored")
    return answer


def _all_pairs_bfs_cost(inst):
    """Mechanical local-girth/distance preprocessing used by the reference route."""
    adj = _adjacency(inst)
    queue_pops = 0
    edge_inspections = 0
    for source in range(len(adj)):
        distances = [-1] * len(adj)
        distances[source] = 0
        todo = deque([source])
        while todo:
            u = todo.popleft()
            queue_pops += 1
            for v in adj[u]:
                edge_inspections += 1
                if distances[v] < 0:
                    distances[v] = distances[u] + 1
                    todo.append(v)
    return queue_pops, edge_inspections


def _reference_algorithm(inst):
    """Literal polynomial route: compute distances/local girths, then construct."""
    queue_pops, edge_inspections = _all_pairs_bfs_cost(inst)
    candidate = _structural_solve(inst)
    return candidate, {
        "queue_pops": queue_pops,
        "edge_inspections": edge_inspections,
        "operations": queue_pops + edge_inspections,
    }


def _distance_conflicts(inst):
    adj = _adjacency(inst)
    conflicts0 = [set(neighbours) for neighbours in adj]
    conflicts2 = []
    for u in range(len(adj)):
        near = set(adj[u])
        for v in adj[u]:
            near.update(adj[v])
        near.discard(u)
        conflicts2.append(near)
    return adj, conflicts0, conflicts2


def _greedy_candidate(inst, order, conflicts0, conflicts2):
    answer = [-1] * inst["num_vertices"]
    for u in order:
        chosen = None
        for color in range(4):
            conflicts = conflicts0[u] if color == 0 else conflicts2[u]
            if all(answer[v] != color for v in conflicts):
                chosen = color
                break
        if chosen is None:
            return answer
        answer[u] = chosen
    return answer


def _local_orientation_candidate(inst):
    """Orient each block independently by visible labels: plausible, globally wrong."""
    _adj, degree3, partners, arms, _kinds, connector, paths = _quotient_data(inst)
    answer = [None] * inst["num_vertices"]
    for u in degree3:
        answer[u] = 1 if u < partners[u] else 2
        for vertex in arms[u]:
            answer[vertex] = 0
    used = set()
    for u in degree3:
        v = connector[u]
        edge = (min(u, v), max(u, v))
        if edge in used:
            continue
        used.add(edge)
        internal = paths[u]
        colors = [0, 3, 0] if len(internal) == 3 else [0, 3]
        for vertex, color in zip(internal, colors):
            answer[vertex] = color
    return answer


def _attack_candidates(inst, seed):
    adj, conflicts0, conflicts2 = _distance_conflicts(inst)
    n_vertices = inst["num_vertices"]

    degree_only = [0 if len(adj[v]) == 2 else 1 + (v & 1) for v in range(n_vertices)]
    visible_greedy = _greedy_candidate(
        inst, list(range(n_vertices)), conflicts0, conflicts2
    )
    rng = random.Random(seed ^ 0x260325113)
    restart_candidates = []
    for _ in range(32):
        order = list(range(n_vertices))
        rng.shuffle(order)
        restart_candidates.append(
            _greedy_candidate(inst, order, conflicts0, conflicts2)
        )
    return {
        "outlier_degree_and_label_parity": [degree_only],
        "greedy_visible_order_first_fit": [visible_greedy],
        "random_restart_greedy_32": restart_candidates,
        "by_hand_independent_local_orientations": [_local_orientation_candidate(inst)],
    }


def _relabel(inst, permutation, reorder_edges=False):
    n_vertices = inst["num_vertices"]
    if sorted(permutation) != list(range(n_vertices)):
        raise ValueError("not a vertex permutation")
    out = {k: v for k, v in inst.items() if k not in ("edges", "answer")}
    edges = [
        [min(permutation[u], permutation[v]), max(permutation[u], permutation[v])]
        for u, v in inst["edges"]
    ]
    if reorder_edges:
        edges.reverse()
    out["edges"] = edges
    carried = [0] * n_vertices
    for old, new in enumerate(permutation):
        carried[new] = inst["answer"][old]
    out["answer"] = carried
    return out


def escalate(params):
    """Increase irregularity first, then size until the 300-operation route cap."""
    out = {k: v for k, v in params.items() if k != "_preset"}
    irregularity = int(out.get("irregularity", 100))
    n = int(out.get("n", 1))
    if irregularity < 100:
        out["irregularity"] = min(100, irregularity + 25)
        return out
    if n < 37:
        out["n"] = n + 1
        return out
    return "cap_bound"


def selftest():
    report = {}
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    # G1: construction, theorem regime, JSON encoding, and certificate validity.
    failures = []
    regime_checks = 0
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, why])
            try:
                adj = _adjacency(inst)
                d3 = [v for v in range(len(adj)) if len(adj[v]) == 3]
                saturated = all(sum(len(adj[u]) == 3 for u in adj[v]) <= 1 for v in d3)
                subcubic = max(map(len, adj)) <= 3
                tokens = _canonical_cycle_tokens(inst)
                local_short = all(token in ("T", "S", "3", "4") for token in tokens)
                regime_checks += int(saturated and subcubic and local_short)
            except ValueError:
                pass
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not failures and regime_checks == attempts,
        "attempts": attempts,
        "theorem_regime_checks": regime_checks,
        "failures": failures,
    }

    # G2: construct mutations that hit five separate validation paths.
    inst = make_instance(seed=19, **shipping)
    answer = inst["answer"]
    adj = _adjacency(inst)
    edge01 = next(
        (u, v)
        for u in range(len(adj))
        for v in adj[u]
        if u < v and {answer[u], answer[v]} == {0, 1}
    )
    swap_answer = list(answer)
    swap_answer[edge01[0]], swap_answer[edge01[1]] = (
        swap_answer[edge01[1]],
        swap_answer[edge01[0]],
    )
    edge02 = next(
        (u, v)
        for u in range(len(adj))
        for v in adj[u]
        if u < v and answer[u] == 0 and answer[v] != 0
    )
    duplicate_answer = list(answer)
    duplicate_answer[edge02[1]] = 0
    out_of_range = list(answer)
    out_of_range[0] = 4
    corruptions = {
        "drop": answer[:-1],
        "swap": swap_answer,
        "duplicate": duplicate_answer,
        "empty": [],
        "out_of_range": out_of_range,
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": why}
    reasons = [case["reason"] for case in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and len(set(reasons)) == len(reasons),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The decomposition gives this coloring.\n```json\n<answer>\n"
        + json.dumps(answer, separators=(",", ":"))
        + "\n</answer>\n```\nThe positions are vertex numbers."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x260325113)
    guess_total = 200_000
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "structure_aware_space_bits": search_space(inst).bit_length(),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = [
        "outlier_degree_and_label_parity",
        "greedy_visible_order_first_fit",
        "random_restart_greedy_32",
        "by_hand_independent_local_orientations",
    ]
    successes = {name: 0 for name in attack_names}
    attack_times = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_operations = 0
    compact_successes = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        candidates = _attack_candidates(trial, seed)
        for name in attack_names:
            start = time.perf_counter()
            won = any(verify(trial, candidate)[0] for candidate in candidates[name])
            attack_times[name] += time.perf_counter() - start
            successes[name] += int(won)
        start = time.perf_counter()
        recovered, counts = _reference_algorithm(trial)
        reference_seconds += time.perf_counter() - start
        reference_operations += counts["operations"]
        reference_successes += int(verify(trial, recovered)[0])
        compact_successes += int(verify(trial, _structural_solve(trial))[0])
    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_times[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "constructive local-cycle coloring after repeated exact BFS distances",
        "complexity": "O(|V|(|V|+|E|)) exact, polynomial",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_operations // 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "local-cycle contraction and alternating port-cycle coloring",
            "solves": f"{compact_successes}/8",
            "operations_upper_bound": inst["num_vertices"] + 2 * inst["n"],
        },
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and isinstance(demo_count, int)
        and demo_count > 0
        and all_failed
        and reference_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density": guess_fraction,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_attack_wall_clock_sec": round(
            attack_times["random_restart_greedy_32"] / 8, 6
        ),
        "baseline_attack_iterations": 32,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    ladder_n = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    ladder_irregularity = [DIFFICULTY[name]["irregularity"] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["num_vertices"] == 2 * inst["num_vertices"]
        and len(render(doubled)) > len(render(inst))
        and ladder_n == sorted(ladder_n)
        and ladder_irregularity == sorted(ladder_irregularity),
        "shipping_vertices": inst["num_vertices"],
        "doubled_vertices": doubled["num_vertices"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_why,
        "space_bits_shipping": search_space(inst).bit_length(),
        "space_bits_doubled": search_space(doubled).bit_length(),
    }

    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping)
        key = canonical_key(original)
        rng = random.Random(seed ^ 0x8A8A)
        permutation = list(range(original["num_vertices"]))
        rng.shuffle(permutation)
        identity = list(range(original["num_vertices"]))
        variants = [
            _relabel(original, permutation, False),
            _relabel(original, identity, True),
            _relabel(original, permutation, True),
        ]
        for transformed in variants:
            invariant_count += int(canonical_key(transformed) == key)
            real_transform_count += int(verify(transformed, transformed["answer"])[0])
        unrelated_keys.append(key)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == 60
        and real_transform_count == 60
        and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "real_transformations_verified": real_transform_count,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "arbitrary vertex permutation",
            "edge-list reordering",
            "their composition",
        ],
    }

    encoded = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(encoded)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(inst["answer"])
    worst_chars = 2 * inst["num_vertices"] + 1
    worst_tokens = math.ceil(worst_chars / 4)
    intended_operations = inst["num_vertices"] + 2 * inst["n"]
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == worst_tokens
    )
    report["G9_no_tool_suitability"] = {
        # The oracle arms are diagnostic.  Only the size/effort caps gate.
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": worst_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
