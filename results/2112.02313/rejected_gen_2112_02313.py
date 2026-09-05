"""Verified problem generator for arXiv:2112.02313.

The task is bounded Kempe reconfiguration in the tight case of Lemma 1.1:
3-colorings of a 2-degenerate graph.  Rectangular grids are used because
Section 1 explicitly notes that they are 2-degenerate with unbounded
treewidth.  Certificates are compositions of random Kempe changes and are
verified independently by exact replay.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # pragma: no cover - implementation remains stdlib-only
    exact_matrices = rationals = None


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "2-degenerate rectangular grid graph",
        "two proper 3-colorings",
        "Kempe-change sequence",
    ],
    "verification_operations": [
        "exact bichromatic connected-component traversal",
        "integer color swap",
        "exact final-coloring comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "search pruning",
    "intuition_description": (
        "Many vertex-and-color descriptions name the same bichromatic component, "
        "so useful search branches on distinct components from both endpoint "
        "colorings; without that quotient the reconfiguration tree explodes."
    ),
    "hardness_basis": (
        "Track A: Lemma 1.1 in the tight d=2, k=d+1 regime guarantees connectivity "
        "but the paper leaves a polynomial sequence bound open; the shipping 10x10 "
        "grid has treewidth 10, maximum degree 4, and average degree 3.6, outside "
        "Theorems 0.1--0.3, while node-limited exact bidirectional BFS exhausted "
        "220,000 generated successors per instance in about 0.6 seconds and solved 0/8."
    ),
    "max_answer_tokens": 33,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": " + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {
        "n": 9, "burn_in": 18, "moves": 2, "min_hamming": 2,
        "max_route_vertices": 18, "attack_width": 0, "attack_nodes": 0,
    },
    "easy": {
        "n": 36, "burn_in": 144, "moves": 16, "min_hamming": 20,
        "max_route_vertices": 284, "attack_width": 24, "attack_nodes": 18_000,
    },
    "medium": {
        "n": 64, "burn_in": 256, "moves": 16, "min_hamming": 40,
        "max_route_vertices": 284, "attack_width": 28, "attack_nodes": 24_000,
    },
    "hard": {
        "n": 100, "burn_in": 400, "moves": 16, "min_hamming": 64,
        "max_route_vertices": 284, "attack_width": 256, "attack_nodes": 220_000,
    },
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Different anchors name the same move whenever they lie in one bichromatic connected component."
)
PLACEBO_HINT = "Keep the changing vertex colors aligned carefully throughout the proposed sequence."

CERTIFICATE_LANGUAGE = {
    "description": (
        "Exactly s ordered pairs [v,c]. At each step v is in 1..n and c is one "
        "of the two colors different from v's current color; the pair swaps the "
        "current bichromatic component containing v."
    ),
    "bounds": {
        "moves": 16, "atoms_per_move": 2, "max_atomic_elements": 32,
        "max_vertex": 400, "colors": 3,
    },
}

NOTES = (
    "Section 1 fixes proper colorings, Kempe chains, and Kempe changes. Lemma 1.1 "
    "proves connectivity for k>=d+1, but its proof may yield an exponential "
    "sequence; the introduction says a polynomial bound in that general regime "
    "is open. Section 1 explicitly contrasts 2-degenerate rectangular grids, whose "
    "treewidth is unbounded, with bounded-treewidth graphs. Shipping grids avoid "
    "Theorem 0.1 because Delta=4>k=3, Theorem 0.2 because their average degree "
    "exceeds 3, and Theorem 0.3 because treewidth exceeds k-1. Certificates are "
    "compositions of uniformly sampled vertex/color Kempe identities, never "
    "solutions recovered from endpoints. The generator filters walks exposed by "
    "discrepancy, greedy, and random-restart heuristics; the independent gate also "
    "runs node-limited exact bidirectional BFS over distinct component moves, plus "
    "a wider construction-aware bidirectional component beam. This retained module "
    "is rejected: its former G9 count measured replay of an already-known planted "
    "sequence, not the work required to recover that sequence from the endpoints."
)

G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "oracle_unreachable",
}


def _grid_shape(n):
    if not isinstance(n, int) or isinstance(n, bool) or n < 9:
        return 0, 0
    rows = math.isqrt(n)
    while rows >= 2 and n % rows:
        rows -= 1
    return rows, n // rows


def _validate_params(n, burn_in, moves, min_hamming, max_route_vertices, attack_width, attack_nodes):
    values = (n, burn_in, moves, min_hamming, max_route_vertices, attack_width, attack_nodes)
    if any(not isinstance(x, int) or isinstance(x, bool) for x in values):
        raise ValueError("all generation parameters must be integers")
    rows, _cols = _grid_shape(n)
    if rows < 3:
        raise ValueError("n must factor into two dimensions of at least 3")
    if not 1 <= moves <= CERTIFICATE_LANGUAGE["bounds"]["moves"]:
        raise ValueError("moves exceeds the certificate-language bound")
    if not 0 <= min_hamming <= n:
        raise ValueError("min_hamming must lie in 0..n")
    if not moves <= max_route_vertices <= 284:
        raise ValueError("route bound must leave fewer than 300 intended operations")
    if n > CERTIFICATE_LANGUAGE["bounds"]["max_vertex"]:
        raise ValueError("n exceeds the certificate-language vertex bound")
    if min(burn_in, attack_width, attack_nodes) < 0:
        raise ValueError("budgets cannot be negative")


def _grid_edges(rows, cols):
    edges = []
    for i in range(rows):
        for j in range(cols):
            v = i * cols + j
            if i + 1 < rows:
                edges.append((v, v + cols))
            if j + 1 < cols:
                edges.append((v, v + 1))
    return edges


def _adjacency(n, edges):
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    for row in adj:
        row.sort()
    return adj


def _component(adj, colors, start, other, counter=None):
    old = colors[start]
    seen = {start}
    stack = [start]
    while stack:
        v = stack.pop()
        for u in adj[v]:
            if counter is not None:
                counter["edge_scans"] += 1
            if u not in seen and colors[u] in (old, other):
                seen.add(u)
                stack.append(u)
    return sorted(seen)


def _apply_move(adj, colors, vertex, target, counter=None):
    old = colors[vertex]
    component = _component(adj, colors, vertex, target, counter)
    for u in component:
        colors[u] = target if colors[u] == old else old
        if counter is not None:
            counter["color_writes"] += 1
    return component


def _unique_successors(adj, colors, counter=None):
    """Return one canonical representative of every distinct Kempe change."""
    n = len(colors)
    result = []
    for a in (1, 2):
        for b in range(a + 1, 4):
            unseen = {v for v in range(n) if colors[v] in (a, b)}
            while unseen:
                root = min(unseen)
                unseen.remove(root)
                stack = [root]
                component = []
                while stack:
                    v = stack.pop()
                    component.append(v)
                    for u in adj[v]:
                        if counter is not None:
                            counter["edge_scans"] += 1
                        if u in unseen:
                            unseen.remove(u)
                            stack.append(u)
                component.sort()
                nxt = list(colors)
                for v in component:
                    nxt[v] = b if colors[v] == a else a
                    if counter is not None:
                        counter["color_writes"] += 1
                anchor = component[0]
                target = b if colors[anchor] == a else a
                result.append((tuple(nxt), [anchor + 1, target], component))
    return result


def _hamming(left, right):
    return sum(a != b for a, b in zip(left, right))


def _proper(colors, edges):
    return all(colors[u] != colors[v] for u, v in edges)


def _random_walk(adj, colors, length, rng):
    current = list(colors)
    states = {tuple(current)}
    answer = []
    writes = 0
    for _ in range(length):
        chosen = None
        for _try in range(80):
            v = rng.randrange(len(current))
            target = rng.randrange(1, 3)
            if target >= current[v]:
                target += 1
            trial = list(current)
            component = _apply_move(adj, trial, v, target)
            if tuple(trial) not in states:
                chosen = (v, target, trial, len(component))
                break
        if chosen is None:
            return None
        v, target, current, size = chosen
        answer.append([v + 1, target])
        writes += size
        states.add(tuple(current))
    return answer, current, writes


def _greedy_path(inst, reverse=False, outlier=False):
    adj = _adjacency(inst["n"], [tuple(e) for e in inst["edges"]])
    current = tuple(inst["target_coloring"] if reverse else inst["start_coloring"])
    goal = tuple(inst["start_coloring"] if reverse else inst["target_coloring"])
    path = []
    for _ in range(inst["required_moves"]):
        successors = _unique_successors(adj, current)
        if outlier:
            bad = {v for v in range(inst["n"]) if current[v] != goal[v]}
            def rank(item):
                _nxt, move, component = item
                inside = sum(v in bad for v in component)
                boundary = sum(u in bad for v in component for u in adj[v] if u not in component)
                return (-inside, -boundary, len(component), move)
        else:
            def rank(item):
                nxt, move, component = item
                return (_hamming(nxt, goal), len(component), move)
        nxt, move, _component_vertices = min(successors, key=rank)
        old_at_anchor = current[move[0] - 1]
        path.append((move, old_at_anchor))
        current = nxt
    if current != goal:
        return None
    if not reverse:
        return [move for move, _old in path]
    return [[move[0], old] for move, old in reversed(path)]


def _random_restart_path(inst, restarts=16):
    adj = _adjacency(inst["n"], [tuple(e) for e in inst["edges"]])
    goal = tuple(inst["target_coloring"])
    rng = random.Random(int(canonical_key(inst)[:16], 16) ^ 0x5EED)
    for _ in range(restarts):
        current = tuple(inst["start_coloring"])
        path = []
        for step in range(inst["required_moves"]):
            ranked = sorted(
                _unique_successors(adj, current),
                key=lambda item: (_hamming(item[0], goal), rng.random()),
            )
            window = min(len(ranked), max(2, (inst["required_moves"] - step) // 2))
            nxt, move, _component_vertices = ranked[rng.randrange(window)]
            current = nxt
            path.append(move)
        if current == goal:
            return path
    return None


def _bidirectional_component_beam(inst, width, node_budget):
    """Bounded bidirectional search over distinct Kempe components."""
    if width <= 0 or node_budget <= 0:
        return None, {"expanded_states": 0, "generated_successors": 0, "budget_hit": False}
    adj = _adjacency(inst["n"], [tuple(e) for e in inst["edges"]])
    start = tuple(inst["start_coloring"])
    target = tuple(inst["target_coloring"])
    forward, backward = {start: []}, {target: []}
    expanded = generated = 0

    def expand(layer, goal, backward_mode):
        nonlocal expanded, generated
        candidates = {}
        for state, path in layer.items():
            expanded += 1
            for nxt, move, _component_vertices in _unique_successors(adj, state):
                generated += 1
                if generated > node_budget:
                    return None
                if nxt in candidates:
                    continue
                if backward_mode:
                    old = state[move[0] - 1]
                    candidates[nxt] = [[move[0], old]] + path
                else:
                    candidates[nxt] = path + [move]
        ranked = sorted(candidates.items(), key=lambda item: (_hamming(item[0], goal), item[0]))
        return dict(ranked[:width])

    forward_depth = inst["required_moves"] // 2
    backward_depth = inst["required_moves"] - forward_depth
    for _ in range(forward_depth):
        forward = expand(forward, target, False)
        if forward is None:
            return None, {"expanded_states": expanded, "generated_successors": generated, "budget_hit": True}
    for _ in range(backward_depth):
        backward = expand(backward, start, True)
        if backward is None:
            return None, {"expanded_states": expanded, "generated_successors": generated, "budget_hit": True}
    common = set(forward).intersection(backward)
    if common:
        meet = min(common, key=lambda state: (_hamming(state, target), state))
        return forward[meet] + backward[meet], {
            "expanded_states": expanded, "generated_successors": generated, "budget_hit": False,
        }
    return None, {"expanded_states": expanded, "generated_successors": generated, "budget_hit": False}


def _bidirectional_component_bfs(inst, node_budget):
    """Exact bidirectional BFS until its explicit generated-successor budget.

    This is the standard shortest-path algorithm on the implicit, unweighted
    reconfiguration graph.  Unlike the beam attack it never ranks or discards a
    state while under budget.  An even amount of unused exact-length budget is
    filled by a Kempe change followed by its inverse.
    """
    empty = {
        "expanded_states": 0,
        "generated_successors": 0,
        "stored_states": 0,
        "max_forward_depth": 0,
        "max_backward_depth": 0,
        "budget_hit": False,
    }
    if node_budget <= 0:
        return None, empty

    adj = _adjacency(inst["n"], [tuple(e) for e in inst["edges"]])
    start = tuple(inst["start_coloring"])
    target = tuple(inst["target_coloring"])
    if start == target:
        return None, dict(empty, stored_states=1)

    # Forward parents point toward start and carry the forward move.  Backward
    # parents point toward target and carry the inverse move to that parent.
    f_parent = {start: (None, None)}
    b_parent = {target: (None, None)}
    f_depth = {start: 0}
    b_depth = {target: 0}
    f_frontier = {start}
    b_frontier = {target}
    expanded = generated = 0
    max_f = max_b = 0

    def reconstruct(meet):
        left = []
        state = meet
        while f_parent[state][0] is not None:
            previous, move = f_parent[state]
            left.append(move)
            state = previous
        left.reverse()
        right = []
        state = meet
        while b_parent[state][0] is not None:
            toward_target, inverse_move = b_parent[state]
            right.append(inverse_move)
            state = toward_target
        path = left + right
        gap = inst["required_moves"] - len(path)
        if gap < 0 or gap % 2:
            return None
        if gap:
            first = _unique_successors(adj, start)[0]
            _nxt, move, _vertices = first
            inverse = [move[0], start[move[0] - 1]]
            path = ([move, inverse] * (gap // 2)) + path
        return path

    while f_frontier and b_frontier and max_f + max_b < inst["required_moves"]:
        expand_forward = len(f_frontier) <= len(b_frontier)
        frontier = f_frontier if expand_forward else b_frontier
        own_parent = f_parent if expand_forward else b_parent
        own_depth = f_depth if expand_forward else b_depth
        other_depth = b_depth if expand_forward else f_depth
        next_frontier = set()
        for state in sorted(frontier):
            expanded += 1
            depth = own_depth[state]
            for nxt, move, _component_vertices in _unique_successors(adj, state):
                generated += 1
                if generated > node_budget:
                    stats = {
                        "expanded_states": expanded,
                        "generated_successors": generated,
                        "stored_states": len(f_parent) + len(b_parent),
                        "max_forward_depth": max_f,
                        "max_backward_depth": max_b,
                        "budget_hit": True,
                    }
                    return None, stats
                if nxt in own_parent:
                    continue
                if expand_forward:
                    own_parent[nxt] = (state, move)
                else:
                    inverse = [move[0], state[move[0] - 1]]
                    own_parent[nxt] = (state, inverse)
                own_depth[nxt] = depth + 1
                next_frontier.add(nxt)
                if nxt in other_depth and own_depth[nxt] + other_depth[nxt] <= inst["required_moves"]:
                    candidate = reconstruct(nxt)
                    if candidate is not None:
                        stats = {
                            "expanded_states": expanded,
                            "generated_successors": generated,
                            "stored_states": len(f_parent) + len(b_parent),
                            "max_forward_depth": max(max_f, own_depth[nxt]) if expand_forward else max_f,
                            "max_backward_depth": max_b if expand_forward else max(max_b, own_depth[nxt]),
                            "budget_hit": False,
                        }
                        return candidate, stats
        if expand_forward:
            f_frontier = next_frontier
            max_f += 1
        else:
            b_frontier = next_frontier
            max_b += 1

    stats = {
        "expanded_states": expanded,
        "generated_successors": generated,
        "stored_states": len(f_parent) + len(b_parent),
        "max_forward_depth": max_f,
        "max_backward_depth": max_b,
        "budget_hit": False,
    }
    return None, stats


def _reaches_target(inst, answer):
    if answer is None or len(answer) != inst["required_moves"]:
        return False
    adj = _adjacency(inst["n"], [tuple(e) for e in inst["edges"]])
    colors = list(inst["start_coloring"])
    for move in answer:
        if (not isinstance(move, list) or len(move) != 2 or
                not isinstance(move[0], int) or not isinstance(move[1], int) or
                not 1 <= move[0] <= inst["n"] or not 1 <= move[1] <= 3 or
                colors[move[0] - 1] == move[1]):
            return False
        _apply_move(adj, colors, move[0] - 1, move[1])
    return colors == inst["target_coloring"]


def _passes_construction_attacks(inst, width, nodes):
    cheap = (
        _greedy_path(inst), _greedy_path(inst, reverse=True),
        _greedy_path(inst, outlier=True), _random_restart_path(inst, restarts=32),
    )
    return not any(_reaches_target(inst, candidate) for candidate in cheap)


def _permuted_instance(n, edges, start, target, answer, rng):
    vertex_perm = list(range(n))
    rng.shuffle(vertex_perm)
    color_perm = [1, 2, 3]
    rng.shuffle(color_perm)
    cmap = {old: color_perm[old - 1] for old in (1, 2, 3)}
    mapped_edges = []
    for u, v in edges:
        x, y = vertex_perm[u], vertex_perm[v]
        mapped_edges.append([min(x, y), max(x, y)])
    rng.shuffle(mapped_edges)
    mapped_start, mapped_target = [0] * n, [0] * n
    for old in range(n):
        mapped_start[vertex_perm[old]] = cmap[start[old]]
        mapped_target[vertex_perm[old]] = cmap[target[old]]
    mapped_answer = [[vertex_perm[v - 1] + 1, cmap[c]] for v, c in answer]
    return mapped_edges, mapped_start, mapped_target, mapped_answer


def make_instance(n, seed=0, burn_in=144, moves=10, min_hamming=20,
                  max_route_vertices=150, attack_width=64, attack_nodes=35_000, **params):
    """Build a certificate by composition, never by solving the endpoints."""
    _validate_params(n, burn_in, moves, min_hamming, max_route_vertices, attack_width, attack_nodes)
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    rows, cols = _grid_shape(n)
    edges = _grid_edges(rows, cols)
    adj = _adjacency(n, edges)
    rng = random.Random(seed)
    start = [1 + ((i + j) & 1) for i in range(rows) for j in range(cols)]
    for _ in range(burn_in):
        v = rng.randrange(n)
        target_color = rng.randrange(1, 3)
        if target_color >= start[v]:
            target_color += 1
        _apply_move(adj, start, v, target_color)

    for attempt in range(10_000):
        walked = _random_walk(adj, start, moves, rng)
        if walked is None:
            continue
        answer, target, route_vertices = walked
        if route_vertices > max_route_vertices or _hamming(start, target) < min_hamming:
            continue
        mapped = _permuted_instance(n, edges, start, target, answer, rng)
        mapped_edges, mapped_start, mapped_target, mapped_answer = mapped
        candidate = {
            "family": "bounded_kempe_reconfiguration", "n": n, "rows": rows,
            "columns": cols, "k": 3, "edges": mapped_edges,
            "start_coloring": mapped_start, "target_coloring": mapped_target,
            "required_moves": moves,
        }
        if attack_width and not _passes_construction_attacks(candidate, attack_width, attack_nodes):
            continue
        tuple_edges = [tuple(e) for e in mapped_edges]
        if not _proper(mapped_start, tuple_edges) or not _proper(mapped_target, tuple_edges):
            raise AssertionError("constructed coloring is not proper")
        if not _reaches_target(candidate, mapped_answer):
            raise AssertionError("carried certificate failed after relabeling")
        candidate.update({
            "answer": mapped_answer, "construction_attempt": attempt,
            "planted_vertex_writes": route_vertices,
        })
        if json.loads(json.dumps(candidate["answer"])) != candidate["answer"]:
            raise AssertionError("answer is not JSON-native")
        return candidate
    raise RuntimeError("could not construct an attack-resistant walk within 10000 attempts")


def render(inst):
    edges = sorted([[u + 1, v + 1] for u, v in inst["edges"]])
    lines = [
        "Find an exact-length sequence of Kempe changes between two graph colorings.",
        "",
        f"The graph has vertices 1 through {inst['n']} and colors 1, 2, 3.",
        f"It is a {inst['rows']} by {inst['columns']} rectangular grid, with its vertex",
        "labels randomly permuted; use the edge list below rather than assuming a",
        "row-major labeling. Edges are undirected, have distinct endpoints, and their",
        "order carries no meaning. Both displayed colorings are proper: endpoints of",
        "every edge have different colors.",
        "",
        "A move [v,c] is interpreted in the CURRENT coloring. It requires c to differ",
        "from the current color a of v. Keep only vertices whose current color is a or",
        "c, take the entire connected component containing v in that induced subgraph,",
        "and simultaneously swap a and c on every vertex of the component. Recompute",
        "the component and current colors after each move. This is one Kempe change.",
        "",
        f"Edges ({len(edges)}):",
        json.dumps(edges, separators=(",", ":")),
        "Starting coloring [color(1),...,color(n)]:",
        json.dumps(inst["start_coloring"], separators=(",", ":")),
        "Target coloring [color(1),...,color(n)]:",
        json.dumps(inst["target_coloring"], separators=(",", ":")),
        "",
        f"Return exactly {inst['required_moves']} moves as a JSON list of [vertex,color]",
        "pairs. Order matters, repeated vertices are allowed, vertex indexing is 1-based,",
        "and every target color must be in {1,2,3} and differ from that vertex's current",
        "color at that step. The coloring after the final move must equal the displayed",
        "target coloring entry for entry.",
        "",
        "Give your final answer inside <answer></answer> tags, as the JSON list just specified.",
        "Example of the required syntax: <answer>[[3,2],[7,1]]</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    if not blocks:
        return None
    body = blocks[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


_LAST_ADJACENCY = [None, None]
_LAST_RANDOM_RESULT = [None, None, None]


def _instance_adjacency(inst):
    if _LAST_ADJACENCY[0] is inst:
        return _LAST_ADJACENCY[1]
    adj = _adjacency(inst["n"], [tuple(e) for e in inst["edges"]])
    _LAST_ADJACENCY[0] = inst
    _LAST_ADJACENCY[1] = adj
    return adj


def verify(inst, answer):
    """Replay any submitted exact-length sequence; never inspect inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list of moves"
    if not answer:
        return False, "answer must not be empty"
    expected = inst["required_moves"]
    if len(answer) < expected:
        return False, f"too few moves: got {len(answer)}, expected exactly {expected}"
    if len(answer) > expected:
        return False, f"too many moves: got {len(answer)}, expected exactly {expected}"

    n = inst["n"]
    for index, move in enumerate(answer, 1):
        if not isinstance(move, list) or len(move) != 2:
            return False, f"move {index} must be a two-element list [vertex,color]"
        vertex, target = move
        if not isinstance(vertex, int) or isinstance(vertex, bool):
            return False, f"move {index} vertex must be an integer"
        if not 1 <= vertex <= n:
            return False, f"move {index} vertex {vertex} is outside 1..{n}"
        if not isinstance(target, int) or isinstance(target, bool):
            return False, f"move {index} target color must be an integer"
        if not 1 <= target <= 3:
            return False, f"move {index} target color {target} is outside 1..3"

    adj = _instance_adjacency(inst)
    try:
        frozen = tuple(tuple(move) for move in answer)
    except TypeError:
        frozen = None
    if _LAST_RANDOM_RESULT[0] is inst and frozen == _LAST_RANDOM_RESULT[1]:
        # random_candidate already replayed this exact immutable snapshot so that
        # each later target color could exclude the current color. Reusing its
        # endpoint makes the 200k-sample gate linear in one replay, not two.
        colors = list(_LAST_RANDOM_RESULT[2])
    else:
        colors = list(inst["start_coloring"])
        for index, move in enumerate(answer, 1):
            vertex, target = move
            v = vertex - 1
            if colors[v] == target:
                return False, (
                    f"move {index} is trivial because vertex {vertex} already has color {target}"
                )
            _apply_move(adj, colors, v, target)

    for index, (got, want) in enumerate(zip(colors, inst["target_coloring"]), 1):
        if got != want:
            return False, f"final coloring first differs at vertex {index}: got {got}, expected {want}"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the statement-visible dynamic language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    n = inst["n"]
    adj = _instance_adjacency(inst)
    colors = list(inst["start_coloring"])
    answer = []
    for _ in range(inst["required_moves"]):
        vertex = rng.randrange(n)
        target = rng.randrange(1, 3)
        if target >= colors[vertex]:
            target += 1
        answer.append([vertex + 1, target])
        _apply_move(adj, colors, vertex, target)
    _LAST_RANDOM_RESULT[0] = inst
    _LAST_RANDOM_RESULT[1] = tuple(tuple(move) for move in answer)
    _LAST_RANDOM_RESULT[2] = tuple(colors)
    return answer


def search_space(inst):
    # At every dynamic state there are n vertices and exactly two other colors.
    return (2 * inst["n"]) ** inst["required_moves"]


def enumerate_all(inst):
    space = search_space(inst)
    if space > 200_000:
        return None
    n = inst["n"]
    steps = inst["required_moves"]
    adj = _instance_adjacency(inst)
    target = tuple(inst["target_coloring"])
    valid = 0

    def visit(depth, colors):
        nonlocal valid
        if depth == steps:
            valid += int(tuple(colors) == target)
            return
        for vertex in range(n):
            for color in (1, 2, 3):
                if color == colors[vertex]:
                    continue
                nxt = list(colors)
                _apply_move(adj, nxt, vertex, color)
                visit(depth + 1, nxt)

    visit(0, list(inst["start_coloring"]))
    return valid


def _wl_key(inst):
    """A strong relabeling invariant of graph plus the ordered coloring pair."""
    n = inst["n"]
    total = n + 3
    relations = [[] for _ in range(total)]
    for u, v in inst["edges"]:
        relations[u].append(("E", v))
        relations[v].append(("E", u))
    for v in range(n):
        start_node = n + inst["start_coloring"][v] - 1
        target_node = n + inst["target_coloring"][v] - 1
        relations[v].append(("S", start_node))
        relations[start_node].append(("S", v))
        relations[v].append(("T", target_node))
        relations[target_node].append(("T", v))
    labels = ["V"] * n + ["C"] * 3
    for _ in range(total + 1):
        signatures = []
        for v in range(total):
            neighborhood = sorted((kind, labels[u]) for kind, u in relations[v])
            signatures.append((labels[v], tuple(neighborhood)))
        palette = {sig: str(i) for i, sig in enumerate(sorted(set(signatures)))}
        new_labels = [palette[sig] for sig in signatures]
        if new_labels == labels:
            break
        labels = new_labels
    histogram = sorted((label, labels.count(label)) for label in set(labels))
    relation_counts = {}
    for v in range(total):
        for kind, u in relations[v]:
            if v < u:
                pair = tuple(sorted((labels[v], labels[u])))
                key = (kind,) + pair
                relation_counts[key] = relation_counts.get(key, 0) + 1
    payload = [
        inst["rows"], inst["columns"], inst["required_moves"], histogram,
        sorted((list(key), count) for key, count in relation_counts.items()),
    ]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def canonical_key(inst):
    return _wl_key(inst)


def escalate(params):
    """Grow the grid and attack budget while holding the 16-move answer fixed."""
    p = {key: value for key, value in params.items() if key != "_preset"}
    n = p.get("n", 36)
    side = math.isqrt(n)
    next_side = side + 1
    next_n = next_side * next_side
    if next_n > CERTIFICATE_LANGUAGE["bounds"]["max_vertex"]:
        return "cap_bound"
    p["n"] = next_n
    p["burn_in"] = 4 * next_n
    # The larger ambient state space is the hardness axis.  Raising the endpoint
    # distance here would lengthen the route's changed-vertex trace and collide
    # with G9's intended-operation cap without adding answer entropy.
    p["min_hamming"] = min(next_n - 1, p.get("min_hamming", 0))
    p["max_route_vertices"] = min(284, max(p.get("max_route_vertices", 0), 260))
    p["attack_width"] = min(512, p.get("attack_width", 64) + 64)
    p["attack_nodes"] = min(500_000, p.get("attack_nodes", 35_000) + 100_000)
    p["moves"] = 16
    return p


def _relabel_instance(inst, vertex_perm=None, color_perm=None, reverse_edges=False):
    n = inst["n"]
    vp = vertex_perm or list(range(n))
    cp = color_perm or [1, 2, 3]
    cmap = {old: cp[old - 1] for old in (1, 2, 3)}
    transformed = copy.deepcopy(inst)
    transformed["edges"] = []
    for u, v in inst["edges"]:
        a, b = vp[u], vp[v]
        transformed["edges"].append([min(a, b), max(a, b)])
    if reverse_edges:
        transformed["edges"].reverse()
    transformed["start_coloring"] = [0] * n
    transformed["target_coloring"] = [0] * n
    for old in range(n):
        transformed["start_coloring"][vp[old]] = cmap[inst["start_coloring"][old]]
        transformed["target_coloring"][vp[old]] = cmap[inst["target_coloring"][old]]
    transformed["answer"] = [[vp[v - 1] + 1, cmap[c]] for v, c in inst["answer"]]
    return transformed


def _corruptions(inst):
    answer = copy.deepcopy(inst["answer"])
    cases = {
        "drop": answer[:-1],
        "duplicate": answer + [copy.deepcopy(answer[-1])],
        "empty": [],
        "out_of_range": copy.deepcopy(answer),
    }
    cases["out_of_range"][0][0] = 0
    swapped = None
    for i in range(len(answer)):
        for j in range(i + 1, len(answer)):
            trial = copy.deepcopy(answer)
            trial[i], trial[j] = trial[j], trial[i]
            if not verify(inst, trial)[0]:
                swapped = trial
                break
        if swapped is not None:
            break
    if swapped is None:
        swapped = copy.deepcopy(answer)
        anchor_index = next((i for i, move in enumerate(swapped) if move[0] > 3), 0)
        swapped[anchor_index][0], swapped[anchor_index][1] = (
            swapped[anchor_index][1], swapped[anchor_index][0]
        )
    cases["swap"] = swapped
    return cases


def selftest():
    report = {}

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed, "reason": "answer not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping)
    cases = {}
    reasons = []
    for name, corrupted in _corruptions(inst).items():
        ok, reason = verify(inst, corrupted)
        cases[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values()) and len(set(reasons)) == 5,
        "distinct_reasons": len(set(reasons)), "cases": cases,
    }

    response = (
        "The component quotient gives the following route.\n```json\n<answer>\n"
        + json.dumps(inst["answer"])
        + "\n</answer>\n```\nI checked the endpoint."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and parse_answer("no tagged answer") is None,
        "parsed_equals_answer": parsed == inst["answer"],
        "garbage_returns_none": parse_answer("no tagged answer") is None,
    }

    guess_rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    start_time = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        guess_hits += int(verify(inst, candidate)[0])
    guess_seconds = time.perf_counter() - start_time
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits, "total": guess_total, "fraction": guess_fraction,
        "candidate_space": search_space(inst),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = [
        "endpoint_discrepancy_outlier",
        "greedy_hamming_forward",
        "greedy_hamming_reverse",
        "random_restart_32",
        "bidirectional_component_bfs_node_limited",
        "bidirectional_component_beam",
    ]
    successes = {name: 0 for name in attack_names}
    seconds = {name: 0.0 for name in attack_names}
    beam_generated = beam_expanded = beam_budget_hits = 0
    bfs_generated = bfs_expanded = bfs_stored = bfs_budget_hits = 0
    bfs_max_forward = bfs_max_backward = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        attack_calls = {
            "endpoint_discrepancy_outlier": lambda: _greedy_path(trial, outlier=True),
            "greedy_hamming_forward": lambda: _greedy_path(trial),
            "greedy_hamming_reverse": lambda: _greedy_path(trial, reverse=True),
            "random_restart_32": lambda: _random_restart_path(trial, restarts=32),
        }
        for name, call in attack_calls.items():
            t0 = time.perf_counter()
            answer = call()
            seconds[name] += time.perf_counter() - t0
            successes[name] += int(_reaches_target(trial, answer))
        t0 = time.perf_counter()
        answer, stats = _bidirectional_component_bfs(trial, shipping["attack_nodes"])
        seconds["bidirectional_component_bfs_node_limited"] += time.perf_counter() - t0
        successes["bidirectional_component_bfs_node_limited"] += int(
            _reaches_target(trial, answer)
        )
        bfs_generated += stats["generated_successors"]
        bfs_expanded += stats["expanded_states"]
        bfs_stored += stats["stored_states"]
        bfs_budget_hits += int(stats["budget_hit"])
        bfs_max_forward = max(bfs_max_forward, stats["max_forward_depth"])
        bfs_max_backward = max(bfs_max_backward, stats["max_backward_depth"])
        t0 = time.perf_counter()
        answer, stats = _bidirectional_component_beam(
            trial, shipping["attack_width"], shipping["attack_nodes"]
        )
        seconds["bidirectional_component_beam"] += time.perf_counter() - t0
        successes["bidirectional_component_beam"] += int(_reaches_target(trial, answer))
        beam_generated += stats["generated_successors"]
        beam_expanded += stats["expanded_states"]
        beam_budget_hits += int(stats["budget_hit"])
    attacks = {
        name: {
            "successes": successes[name], "attempts": 8,
            "wall_clock_sec": round(seconds[name], 6),
        }
        for name in attack_names
    }
    attacks["bidirectional_component_bfs_node_limited"].update({
        "generated_successors": bfs_generated,
        "expanded_states": bfs_expanded,
        "stored_states_sum": bfs_stored,
        "budget_hits": bfs_budget_hits,
        "max_forward_depth": bfs_max_forward,
        "max_backward_depth": bfs_max_backward,
        "node_budget_per_instance": shipping["attack_nodes"],
        "standard_algorithm": True,
    })
    attacks["bidirectional_component_beam"].update({
        "generated_successors": beam_generated,
        "expanded_states": beam_expanded,
        "budget_hits": beam_budget_hits,
        "width": shipping["attack_width"],
        "node_budget_per_instance": shipping["attack_nodes"],
    })
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {"pass": all_failed, "attacks": attacks}

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6 and all_failed,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density": guess_fraction,
        "demo_n": demo["n"],
        "demo_exact_solution_count": enumerate_all(demo),
        "baseline_attack_name": "bidirectional component BFS (node-limited)",
        "baseline_attack_wall_clock_sec": round(
            seconds["bidirectional_component_bfs_node_limited"] / 8, 6
        ),
        "baseline_attack_generated_successors": bfs_generated // 8,
        "baseline_attack_expanded_states": bfs_expanded // 8,
        "baseline_attack_stored_states": bfs_stored // 8,
        "baseline_attack_budget_hits": bfs_budget_hits,
    }

    doubled_params = dict(shipping)
    doubled_params.update({
        "n": 200, "burn_in": 800, "min_hamming": 120,
        "max_route_vertices": 284,
    })
    t0 = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - t0
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    sizes = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and search_space(doubled) > search_space(inst)
        and len(render(doubled)) > len(render(inst))
        and sizes == sorted(sizes)
        and len(set(sizes)) == 4,
        "shipping_n": inst["n"], "doubled_n": doubled["n"],
        "shipping_candidate_space": search_space(inst),
        "doubled_candidate_space": search_space(doubled),
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_reason,
    }

    invariant_count = 0
    real_count = 0
    unrelated_keys = []
    key_params = shipping
    for seed in range(201, 221):
        original = make_instance(seed=seed, **key_params)
        original_key = canonical_key(original)
        rng = random.Random(seed ^ 0xA5A5)
        vp = list(range(original["n"]))
        rng.shuffle(vp)
        cp = [1, 2, 3]
        rng.shuffle(cp)
        variants = [
            _relabel_instance(original, vertex_perm=vp),
            _relabel_instance(original, color_perm=cp),
            _relabel_instance(original, reverse_edges=True),
            _relabel_instance(original, vertex_perm=vp, color_perm=cp),
            _relabel_instance(original, vertex_perm=vp, reverse_edges=True),
            _relabel_instance(original, color_perm=cp, reverse_edges=True),
            _relabel_instance(original, vertex_perm=vp, color_perm=cp, reverse_edges=True),
        ]
        for transformed in variants:
            invariant_count += int(canonical_key(transformed) == original_key)
            real_count += int(verify(transformed, transformed["answer"])[0])
        unrelated_keys.append(original_key)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == 140 and real_count == 140 and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "real_transformations_verified": real_count,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "arbitrary vertex permutation", "global color permutation",
            "edge-list reordering", "all compositions",
        ],
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_elements = 2 * len(inst["answer"])
    # Honest G9 accounting must include acquisition of the witness.  The earlier
    # build counted only replay after the planted route was already known, which
    # is checker cost rather than a solver's compact route.  The component-
    # quotient insight leaves the node-limited exact search below; even its first
    # 220,001 generated successors do not recover a shipping witness.
    intended_operations = report["G5_density_and_baseline_cost"][
        "baseline_attack_generated_successors"
    ]
    arms = {
        "bare": dict(G9_ORACLE_RESULTS["bare"]),
        "hinted": dict(G9_ORACLE_RESULTS["hinted"]),
        "placebo": dict(G9_ORACLE_RESULTS["placebo"]),
    }
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        hinted_minus_placebo = hinted_rate - placebo_rate
    else:
        hinted_minus_placebo = None
    report["G9_no_tool_suitability"] = {
        "pass": len(answer_blob) <= 2000 and answer_elements <= 256 and intended_operations <= 300,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": len(answer_blob),
        "answer_tokens": (len(answer_blob) + 3) // 4,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "intended_route_note": (
            "No sub-300-operation recovery route is known; 225 operations only "
            "replay the planted witness after it has already been supplied."
        ),
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["certificate_language"] = CERTIFICATE_LANGUAGE
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
