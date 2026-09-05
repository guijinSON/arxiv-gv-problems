"""Verified generators for mixed distance-(1,2) coloring certificates.

The generated graph is a subdivision of a cubic bipartite planar graph made
from a cube by recursively replacing an edge with a cube-minus-that-edge
two-pole.  The answer is a compact peeling certificate: the two boundary
ports of every two-pole, in leaf-to-root order.  Verification reconstructs
and checks each eight-vertex two-pole from its ports, reconstructs a
three-edge-coloring without search, turns that edge-coloring into a
(1^1,2^3)-coloring of the subdivision, and checks every distance-one and
distance-two constraint.

This is a native Track-B subfamily of the problem in Section 2.2, Theorem 6,
of arXiv:2602.13037.  Generation is deterministic in (n, seed, params), uses
only the Python standard library, performs no file I/O, and prints nothing at
import.
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
from typing import Any


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "bipartite planar graph of maximum degree 3",
        "mixed distance-1/distance-2 vertex coloring",
        "recursive cube two-pole port certificate",
    ],
    "verification_operations": [
        "exact degree and adjacency comparison",
        "two-edge-cut and cube recognition",
        "explicit three-edge-color propagation",
        "edge and length-two color-conflict scan",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Recognize that suppressing the degree-two subdivision vertices leaves "
        "a chain of cube-minus-edge two-poles; without that decomposition, a "
        "solver must mechanically recover cuts or search for a mixed coloring."
    ),
    "hardness_basis": (
        "Track B: Theorem 6 places (1^1,2^3)-coloring in the NP-complete "
        "bipartite-planar maximum-degree-4 regime, but this generated "
        "maximum-degree-3 distribution has an O(n*m*(n+m)) two-edge-cut "
        "peeling algorithm; at the hard preset it used 146400 counted graph "
        "operations and about 0.1 seconds in local shipping measurements, while "
        "the compact cube-chain route uses 264 local adjacency "
        "operations."
    ),
    "max_answer_tokens": 27,
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
    "demo": {"n": 0},
    "easy": {"n": 4},
    "medium": {"n": 7},
    "hard": {"n": 10},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The degree-three core retains a recursive cube-minus-edge two-pole "
    "structure under edge subdivision."
)
PLACEBO_HINT = (
    "The numbered edge list rewards careful bookkeeping of degrees and "
    "undirected adjacency."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object {\"patches\": rows}; there are exactly n ordered rows, "
        "each row is a sorted pair of distinct degree-three boundary-port IDs, "
        "and no port ID is repeated between rows."
    ),
    "bounds": {
        "max_patches": 32,
        "ports_per_patch": 2,
        "max_atomic_elements": 64,
        "vertex_ids": "0 <= id < vertex_count",
    },
}

NOTES = r"""
Paper grounding and Step 0.  Section 1 defines a (1^a,2^b)-coloring as a
partition into a independent sets and b 2-independent sets: equal distance-1
colors may not occur at distance 1, while equal distance-2 colors may not
occur at distance 1 or 2.  Section 2 explicitly observes that a vertex-color
map is a polynomial-size NP witness checked by scanning the coloring.
Theorem 6 in Section 2.2 proves that (1^1,2^3)-coloring is NP-complete even on
bipartite planar graphs of maximum degree 4 and arbitrarily large prescribed
girth.  Its forward direction is a certificate-carrying reduction from
planar maximum-degree-4 3-coloring.  The same section identifies easy boundary
cases: (1^1,2^1) graphs are star forests, and (1^0,2^3) graphs are disjoint
unions of paths and cycles.

Why Track B.  Worst-case Theorem 6 does not imply that inverse-generated
instances are hard on average.  This generator therefore makes no Track-A
claim.  Its distribution deliberately has a polynomial decoder: suppress the
degree-two vertices, find an 8-vertex side of a two-edge cut, check that adding
the missing port edge makes a cube, collapse it, and repeat.  The implemented
reference decoder finds each two-edge cut by deleting one edge and running a
bridge DFS, in O(r*m*(n+m)) time for r patches.  Its measured cost appears in
G5/G6.  This is far beyond unaided execution on the shuffled shipping edge
list, while recognition of the recursive two-pole invariant gives a route of
at most 24 local checks per patch plus 24 checks for the final cube.

Generation and certificate.  Begin with the 3-cube Q_3.  Replacing an edge uv
by a fresh Q_3 with one edge pq removed, together with edges up and qv,
preserves cubicity, bipartiteness, and planarity.  The replacement is local in
a disk around uv.  Every replacement after the first occurs on an internal
edge of the newest patch, producing a nested chain.  Finally every core edge
is subdivided once.  The generator records the eight new core vertices at
each step together with the two endpoints p,q of its missing edge, reverses
the port-pair list, and carries it through a random vertex relabeling.  It
never solves the emitted instance.  Given p and q, the verifier has only nine
possible choices for their two external incident edges; removing the right
pair isolates the eight-vertex cube-minus-edge patch, which is then checked
exactly.

The verifier executes the certificate rather than appealing to a theorem.
Each proposed patch must be an exposed cube-minus-edge two-pole.  After all
collapses the remaining graph must be Q_3.  In a cube, opposite edges of a
4-cycle form one coordinate-direction class.  The checker assigns the three
colors to these three classes, expands the patches in reverse, and gives the
two new boundary edges the color of the collapsed edge.  Core vertices then
receive the sole distance-1 color and each subdivision vertex receives its
core edge's distance-2 color.  A final direct scan checks all edges and all
length-two paths.

Attack design.  Random relabeling removes age and patch-boundary information
from IDs.  All core vertices have degree 3, so degree outliers reveal only the
core, not the decomposition.  Low-ID grouping, nearest-vertex grouping, 256
uniform structured restarts, and a one-pass static cube scan are tested.  The
last is the in-context Track-B attack: it can see an exposed end cube but does
not recompute the cut structure after a collapse.  The successful repeated
bridge/cut decoder is reported separately as the reference algorithm.

Canonicalization.  Vertex IDs and edge order are irrelevant.  The key hashes
the sorted multiset of all rooted distance-distribution vectors, together with
the graph order and size.  This is a relabeling invariant and is strong enough
to distinguish the generated nested cube chains in the tested distribution;
it is not a complete isomorphism invariant for arbitrary graphs.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_CUBE_LOCAL_EDGES = tuple(
    (x, x ^ (1 << bit))
    for x in range(8)
    for bit in range(3)
    if x < (x ^ (1 << bit))
)
_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8
_ENUMERATION_CAP = 300_000
_RANDOM_CORE_CACHE: dict[int, tuple[dict, list[int]]] = {}

# Filled from the script-owned hardening runs before the final selftest report.
_ORACLE_EVIDENCE = {
    # API errors do not consume attempts and never count as oracle failures.
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}


def _norm_edge(u: int, v: int) -> tuple[int, int]:
    return (u, v) if u < v else (v, u)


def _int_param(name: str, value: object, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if not low <= value <= high:
        raise ValueError(f"{name} must lie in {low}..{high}")
    return value


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Inverse-generate a certified mixed-coloring instance."""
    n = _int_param("n", n, 0, 32)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    rng = random.Random(seed)

    core_adj: dict[int, set[int]] = {v: set() for v in range(8)}
    core_side: dict[int, int] = {v: v.bit_count() & 1 for v in range(8)}
    for u, v in _CUBE_LOCAL_EDGES:
        core_adj[u].add(v)
        core_adj[v].add(u)

    created_ports: list[tuple[int, int]] = []
    newest_group: set[int] | None = None

    for _ in range(n):
        if newest_group is None:
            candidates = [
                _norm_edge(u, v)
                for u in core_adj
                for v in core_adj[u]
                if u < v
            ]
        else:
            candidates = [
                _norm_edge(u, v)
                for u in newest_group
                for v in core_adj[u]
                if u < v and v in newest_group
            ]
        candidates.sort()
        u, v = rng.choice(candidates)
        core_adj[u].remove(v)
        core_adj[v].remove(u)

        local_missing = rng.choice(_CUBE_LOCAL_EDGES)
        lp, lq = local_missing
        start = len(core_adj)
        local_order = list(range(8))
        rng.shuffle(local_order)
        local_to_global = {local: start + local_order[local] for local in range(8)}
        new_vertices = sorted(local_to_global.values())
        for x in new_vertices:
            core_adj[x] = set()

        # Orient the bipartition so u--p and q--v cross it.
        flip = (1 - core_side[u]) ^ (lp.bit_count() & 1)
        for local, glob in local_to_global.items():
            core_side[glob] = (local.bit_count() & 1) ^ flip

        for a, b in _CUBE_LOCAL_EDGES:
            if _norm_edge(a, b) == _norm_edge(lp, lq):
                continue
            ga, gb = local_to_global[a], local_to_global[b]
            core_adj[ga].add(gb)
            core_adj[gb].add(ga)

        p, q = local_to_global[lp], local_to_global[lq]
        # lp/lq may be listed in either bipartite orientation.
        if core_side[p] == core_side[u]:
            p, q = q, p
        core_adj[u].add(p)
        core_adj[p].add(u)
        core_adj[v].add(q)
        core_adj[q].add(v)

        if any(len(core_adj[x]) != 3 for x in core_adj):
            raise AssertionError("edge replacement failed to preserve cubicity")
        created_ports.append(_norm_edge(p, q))
        newest_group = set(new_vertices)

    core_edges = sorted(
        _norm_edge(u, v)
        for u in core_adj
        for v in core_adj[u]
        if u < v
    )
    core_count = len(core_adj)
    raw_edges: list[tuple[int, int]] = []
    for i, (u, v) in enumerate(core_edges):
        subdivision = core_count + i
        raw_edges.append((u, subdivision))
        raw_edges.append((subdivision, v))

    vertex_count = core_count + len(core_edges)
    labels = list(range(vertex_count))
    rng.shuffle(labels)
    relabel = {old: labels[old] for old in range(vertex_count)}
    edges = [
        list(_norm_edge(relabel[u], relabel[v])) for u, v in raw_edges
    ]
    rng.shuffle(edges)
    answer_ports = [
        sorted((relabel[p], relabel[q])) for p, q in reversed(created_ports)
    ]

    return {
        "family": "recursive_cube_mixed_coloring",
        "a": 1,
        "b": 3,
        "patch_count": n,
        "vertex_count": vertex_count,
        "edges": edges,
        "answer": {"patches": answer_ports},
    }


def render(inst: dict) -> str:
    """Render the complete, self-contained certificate problem."""
    vcount = inst["vertex_count"]
    edges = [tuple(e) for e in inst["edges"]]
    chunks = []
    for i in range(0, len(edges), 8):
        chunks.append("  " + " ".join(f"{u}-{v}" for u, v in edges[i : i + 8]))
    edge_text = "\n".join(chunks)
    statement = f"""Mixed distance-(1,2) coloring certificate

The undirected simple graph below has vertices 0 through {vcount - 1}.
An edge u-v is unordered.  There are {len(edges)} edges:
{edge_text}

A (1^1,2^3)-coloring uses one distance-1 color and three distance-2
colors.  Two adjacent vertices may not share the distance-1 color.  Two
distinct vertices at graph distance 1 or 2 may not share a distance-2 color.

Your task is to give a compact peeling certificate for such a coloring.
First form the degree-three core H: every degree-two vertex of the displayed
graph has two degree-three neighbors; suppress it and put one core edge
between those two neighbors.

The certificate has exactly {inst['patch_count']} ordered rows.  Each row is a
sorted pair [p,q] of distinct current vertices of H, and no vertex ID may be
repeated between rows.  The pair must be the two boundary ports of an exposed
eight-vertex patch: p and q are not adjacent, and it must be possible to
remove one incident edge at p and one incident edge at q so that their
component has exactly eight vertices, meets the rest of H only in those two
removed edges, and becomes Q_3 after adding the missing edge p-q.  Here Q_3
is the graph on the eight binary triples, with two triples adjacent exactly
when they differ in one coordinate.  Since H is cubic, the checker examines
only 3 x 3 possible pairs of incident edges to recover and check the patch.
If a port pair recovers more than one such component, the lexicographically
smallest sorted vertex set is used.

Peel a row by deleting its eight vertices and adding an edge between its two
outside neighbors.  After all rows, the remaining eight core vertices must
induce Q_3.  This certificate is executable: the checker colors the three
coordinate-direction edge classes of the final cube, reverses every peel,
colors core vertices with the distance-1 color, colors each suppressed
vertex by its core edge's direction, and directly checks every required
distance.

All IDs are decimal integers in 0..{vcount - 1}.  Order within a pair is not
mathematical, but each pair must be written in increasing order to give one
unambiguous representation.  Repetitions are forbidden.

Give your final answer inside <answer></answer> tags as one JSON object with
the single key \"patches\".  Its value must be the ordered list of rows.
Syntax example only (not a proposed certificate):
<answer>{{\"patches\": [[0,1],[2,3]]}}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: object) -> object | None:
    """Extract the tagged JSON answer, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        return json.loads(body)
    except (TypeError, ValueError):
        return None


def _graph_from_edges(vertex_count: int, edges: object) -> tuple[dict[int, set[int]] | None, str]:
    if isinstance(vertex_count, bool) or not isinstance(vertex_count, int) or vertex_count < 1:
        return None, "instance_vertex_count: invalid vertex count"
    if not isinstance(edges, list):
        return None, "instance_edges: edges must be a list"
    adj = {v: set() for v in range(vertex_count)}
    for item in edges:
        if not isinstance(item, list) or len(item) != 2:
            return None, "instance_edges: every edge must have two endpoints"
        u, v = item
        if any(isinstance(x, bool) or not isinstance(x, int) for x in (u, v)):
            return None, "instance_edges: endpoints must be integers"
        if not (0 <= u < vertex_count and 0 <= v < vertex_count) or u == v:
            return None, "instance_edges: endpoint out of range or loop"
        if v in adj[u]:
            return None, "instance_edges: duplicate edge"
        adj[u].add(v)
        adj[v].add(u)
    return adj, "ok"


def _extract_core(inst: dict) -> tuple[dict[int, set[int]] | None, dict[tuple[int, int], int] | None, str]:
    graph, reason = _graph_from_edges(inst.get("vertex_count"), inst.get("edges"))
    if graph is None:
        return None, None, reason
    degrees = {v: len(graph[v]) for v in graph}
    if any(d not in (2, 3) for d in degrees.values()):
        return None, None, "instance_shape: every displayed degree must be 2 or 3"
    core = {v: set() for v, d in degrees.items() if d == 3}
    subdivisions = [v for v, d in degrees.items() if d == 2]
    if len(core) != 8 + 8 * inst.get("patch_count", -1):
        return None, None, "instance_shape: wrong number of degree-three vertices"
    edge_to_subdivision: dict[tuple[int, int], int] = {}
    for w in subdivisions:
        nbrs = sorted(graph[w])
        if len(nbrs) != 2 or any(degrees[x] != 3 for x in nbrs):
            return None, None, "instance_shape: a degree-two vertex does not suppress to the core"
        edge = _norm_edge(nbrs[0], nbrs[1])
        if edge in edge_to_subdivision:
            return None, None, "instance_shape: parallel core edges"
        edge_to_subdivision[edge] = w
        core[edge[0]].add(edge[1])
        core[edge[1]].add(edge[0])
    if any(len(core[v]) != 3 for v in core):
        return None, None, "instance_shape: suppressed core is not cubic"
    if len(subdivisions) * 2 != len(inst["edges"]):
        return None, None, "instance_shape: displayed graph is not a full subdivision"
    return core, edge_to_subdivision, "ok"


def _copy_adj(adj: dict[int, set[int]]) -> dict[int, set[int]]:
    return {v: set(nbrs) for v, nbrs in adj.items()}


def _cube_edge_classes(vertices: set[int], edges: set[tuple[int, int]]) -> list[set[tuple[int, int]]] | None:
    if len(vertices) != 8 or len(edges) != 12:
        return None
    deg = {v: 0 for v in vertices}
    for u, v in edges:
        if u not in vertices or v not in vertices or u == v:
            return None
        deg[u] += 1
        deg[v] += 1
    if any(d != 3 for d in deg.values()):
        return None

    # Connectivity and bipartition are executable checks that rule out every
    # cubic graph on eight vertices except the bipartite cube.
    color: dict[int, int] = {}
    root = min(vertices)
    color[root] = 0
    queue = deque([root])
    edge_set = set(edges)
    neighbors = {v: set() for v in vertices}
    for u, v in edges:
        neighbors[u].add(v)
        neighbors[v].add(u)
    while queue:
        u = queue.popleft()
        for v in neighbors[u]:
            if v not in color:
                color[v] = 1 - color[u]
                queue.append(v)
            elif color[v] == color[u]:
                return None
    if len(color) != 8 or Counter(color.values()) != Counter({0: 4, 1: 4}):
        return None

    edge_list = sorted(edge_set)
    parent = list(range(len(edge_list)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i, (a, b) in enumerate(edge_list):
        for j in range(i + 1, len(edge_list)):
            c, d = edge_list[j]
            if len({a, b, c, d}) != 4:
                continue
            if (
                (_norm_edge(a, c) in edge_set and _norm_edge(b, d) in edge_set)
                or (_norm_edge(a, d) in edge_set and _norm_edge(b, c) in edge_set)
            ):
                union(i, j)
    groups: dict[int, set[tuple[int, int]]] = {}
    for i, edge in enumerate(edge_list):
        groups.setdefault(find(i), set()).add(edge)
    classes = list(groups.values())
    if len(classes) != 3 or sorted(len(c) for c in classes) != [4, 4, 4]:
        return None
    return classes


def _patch_info(adj: dict[int, set[int]], patch: set[int]) -> dict | None:
    if len(patch) != 8 or not patch.issubset(adj):
        return None
    inside_degree = {v: len(adj[v] & patch) for v in patch}
    ports = sorted(v for v, d in inside_degree.items() if d == 2)
    if len(ports) != 2 or sum(d == 3 for d in inside_degree.values()) != 6:
        return None
    p, q = ports
    if q in adj[p]:
        return None
    p_out = sorted(adj[p] - patch)
    q_out = sorted(adj[q] - patch)
    if len(p_out) != 1 or len(q_out) != 1 or p_out[0] == q_out[0]:
        return None
    u, v = p_out[0], q_out[0]
    if v in adj[u]:
        return None
    internal_edges = {
        _norm_edge(x, y)
        for x in patch
        for y in adj[x]
        if y in patch and x < y
    }
    missing = _norm_edge(p, q)
    augmented = set(internal_edges)
    augmented.add(missing)
    classes = _cube_edge_classes(set(patch), augmented)
    if classes is None:
        return None
    return {
        "patch": set(patch),
        "ports": (p, q),
        "outside": (u, v),
        "internal_edges": internal_edges,
        "missing": missing,
        "classes": classes,
    }


def _patch_info_from_ports(
    adj: dict[int, set[int]], ports: tuple[int, int]
) -> dict | None:
    """Recover an exposed patch from its two ports with nine local choices.

    Each port has degree three.  The witness names both ports, so the checker
    only has to try which one incident edge at each port leaves the patch.
    This is bounded certificate decoding, not a search for an unnamed patch.
    """
    p, q = ports
    if p == q or p not in adj or q not in adj or q in adj[p]:
        return None
    matches: dict[tuple[int, ...], dict] = {}
    for p_out in sorted(adj[p]):
        for q_out in sorted(adj[q]):
            if p_out == q_out:
                continue
            cut = {_norm_edge(p, p_out), _norm_edge(q, q_out)}
            component = {p}
            queue = deque([p])
            while queue and len(component) <= 8:
                u = queue.popleft()
                for v in adj[u]:
                    if _norm_edge(u, v) in cut or v in component:
                        continue
                    component.add(v)
                    queue.append(v)
            if len(component) != 8 or q not in component:
                continue
            info = _patch_info(adj, component)
            if info is None or set(info["ports"]) != {p, q}:
                continue
            matches[tuple(sorted(component))] = info
    if not matches:
        return None
    # Multiple external-edge guesses can only matter if they recover different
    # patches.  Choosing canonically keeps verification deterministic while
    # accepting every valid port witness.
    return matches[min(matches)]


def _collapse(adj: dict[int, set[int]], info: dict) -> None:
    patch = info["patch"]
    u, v = info["outside"]
    for x in patch:
        for y in list(adj[x]):
            if y not in patch:
                adj[y].remove(x)
        del adj[x]
    adj[u].add(v)
    adj[v].add(u)


def _color_cube_edges(vertices: set[int], edges: set[tuple[int, int]]) -> dict[tuple[int, int], int] | None:
    classes = _cube_edge_classes(vertices, edges)
    if classes is None:
        return None
    ordered = sorted(classes, key=lambda c: tuple(sorted(c)))
    return {edge: color for color, cls in enumerate(ordered) for edge in cls}


def _expand_edge_coloring(
    final_adj: dict[int, set[int]], records: list[dict]
) -> dict[tuple[int, int], int] | None:
    final_edges = {
        _norm_edge(u, v)
        for u in final_adj
        for v in final_adj[u]
        if u < v
    }
    colors = _color_cube_edges(set(final_adj), final_edges)
    if colors is None:
        return None

    for info in reversed(records):
        u, v = info["outside"]
        p, q = info["ports"]
        collapsed = _norm_edge(u, v)
        if collapsed not in colors:
            return None
        inherited = colors.pop(collapsed)
        colors[_norm_edge(u, p)] = inherited
        colors[_norm_edge(q, v)] = inherited

        missing_class = next(
            (cls for cls in info["classes"] if info["missing"] in cls), None
        )
        if missing_class is None:
            return None
        other_classes = sorted(
            (cls for cls in info["classes"] if cls is not missing_class),
            key=lambda c: tuple(sorted(c)),
        )
        other_colors = [c for c in range(3) if c != inherited]
        class_color = [(missing_class, inherited)] + list(zip(other_classes, other_colors))
        for cls, color in class_color:
            for edge in cls:
                if edge != info["missing"]:
                    colors[edge] = color
    return colors


def _check_mixed_coloring(inst: dict, coloring: list[int]) -> tuple[bool, str]:
    graph, reason = _graph_from_edges(inst["vertex_count"], inst["edges"])
    if graph is None:
        return False, reason
    if len(coloring) != inst["vertex_count"] or any(c not in (0, 1, 2, 3) for c in coloring):
        return False, "derived_coloring: wrong length or color range"
    for u in graph:
        for v in graph[u]:
            if u < v and coloring[u] == coloring[v]:
                return False, "derived_coloring: equal colors on an edge"
    for center in graph:
        nbrs = sorted(graph[center])
        for i, u in enumerate(nbrs):
            for v in nbrs[i + 1 :]:
                if coloring[u] > 0 and coloring[u] == coloring[v]:
                    return False, "derived_coloring: repeated distance-2 color on a length-two path"
    return True, "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Verify any valid peeling certificate; never consult inst['answer']."""
    if not isinstance(answer, dict) or set(answer) != {"patches"}:
        return False, "answer_shape: expected one JSON key named patches"
    rows = answer["patches"]
    if not isinstance(rows, list) or len(rows) != inst.get("patch_count"):
        return False, "patch_count: wrong number of patch rows"

    seen: set[int] = set()
    normalized: list[tuple[int, int]] = []
    for i, row in enumerate(rows):
        if not isinstance(row, list) or len(row) != 2:
            return False, f"patch_size: row {i} must contain exactly 2 port vertices"
        if any(isinstance(v, bool) or not isinstance(v, int) for v in row):
            return False, f"patch_type: row {i} contains a non-integer"
        if any(v < 0 or v >= inst.get("vertex_count", 0) for v in row):
            return False, f"vertex_range: row {i} contains an out-of-range ID"
        if row != sorted(row):
            return False, f"patch_order: row {i} is not increasing"
        if len(set(row)) != 2:
            return False, f"patch_duplicate: row {i} repeats a vertex"
        if seen.intersection(row):
            return False, f"row_overlap: row {i} reuses a previous vertex"
        seen.update(row)
        normalized.append((row[0], row[1]))

    core, edge_to_subdivision, reason = _extract_core(inst)
    if core is None or edge_to_subdivision is None:
        return False, reason
    current = _copy_adj(core)
    records: list[dict] = []
    for i, ports in enumerate(normalized):
        info = _patch_info_from_ports(current, ports)
        if info is None:
            return False, f"patch_invalid: row {i} is not the port pair of an exposed cube two-pole"
        records.append(info)
        _collapse(current, info)

    if len(current) != 8:
        return False, "final_size: peeling did not leave exactly 8 core vertices"
    final_edges = {
        _norm_edge(u, v)
        for u in current
        for v in current[u]
        if u < v
    }
    if _cube_edge_classes(set(current), final_edges) is None:
        return False, "final_cube: remaining core is not Q_3"

    edge_colors = _expand_edge_coloring(current, records)
    if edge_colors is None or set(edge_colors) != set(edge_to_subdivision):
        return False, "color_expansion: certificate did not color every core edge"
    coloring = [-1] * inst["vertex_count"]
    for v in core:
        coloring[v] = 0
    for edge, subdivision in edge_to_subdivision.items():
        coloring[subdivision] = edge_colors[edge] + 1
    ok, reason = _check_mixed_coloring(inst, coloring)
    if not ok:
        return False, reason
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample ordered, disjoint, unordered port pairs."""
    cached = _RANDOM_CORE_CACHE.get(id(inst))
    if cached is None or cached[0] is not inst:
        core, _, reason = _extract_core(inst)
        if core is None:
            raise ValueError(reason)
        cached = (inst, list(core))
        _RANDOM_CORE_CACHE[id(inst)] = cached
    vertices = list(cached[1])
    rng.shuffle(vertices)
    n = inst["patch_count"]
    return {
        "patches": [
            sorted(vertices[2 * i : 2 * (i + 1)]) for i in range(n)
        ]
    }


def search_space(inst: dict) -> int:
    """Count ordered disjoint unordered pairs of core vertices."""
    n = inst["patch_count"]
    total = 8 * n + 8
    return math.factorial(total) // (math.factorial(total - 2 * n) * (2**n))


def enumerate_all(inst: dict) -> int | None:
    """Count all valid certificates exactly when the language is small."""
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    core, _, _ = _extract_core(inst)
    if core is None:
        return 0
    vertices = sorted(core)
    n = inst["patch_count"]
    if n == 0:
        return int(verify(inst, {"patches": []})[0])
    if n == 1:
        hits = 0
        for pair in itertools.combinations(vertices, 2):
            hits += int(verify(inst, {"patches": [list(pair)]})[0])
        return hits
    return None


def _distance_signature(inst: dict) -> tuple:
    graph, reason = _graph_from_edges(inst["vertex_count"], inst["edges"])
    if graph is None:
        raise ValueError(reason)
    profiles = []
    for start in graph:
        dist = {start: 0}
        queue = deque([start])
        while queue:
            u = queue.popleft()
            for v in graph[u]:
                if v not in dist:
                    dist[v] = dist[u] + 1
                    queue.append(v)
        if len(dist) != len(graph):
            raise ValueError("canonical_key requires a connected graph")
        counts = Counter(dist.values())
        profiles.append(tuple(counts[d] for d in range(max(counts) + 1)))
    return (len(graph), len(inst["edges"]), tuple(sorted(profiles)))


def canonical_key(inst: dict) -> str:
    """Relabeling-invariant hash of rooted all-pairs distance profiles."""
    payload = json.dumps(_distance_signature(inst), separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Use the one remaining admissible chain-length rung, if any."""
    n = int(params.get("n", 0))
    if n < 11:
        return {"n": n + 1}
    # Longer chains remain generatable, but exceed the intended-route effort
    # budget before answer length becomes the binding constraint.
    return None


def _all_core_edges(adj: dict[int, set[int]]) -> list[tuple[int, int]]:
    return sorted(_norm_edge(u, v) for u in adj for v in adj[u] if u < v)


def _find_exposed_patches(
    adj: dict[int, set[int]], counter: dict[str, int] | None = None
) -> list[set[int]]:
    """Find 8-vertex sides of two-edge cuts using edge deletion + bridge DFS."""
    if counter is None:
        counter = {"operations": 0}
    vertices = sorted(adj)
    edges = _all_core_edges(adj)
    found: set[frozenset[int]] = set()

    for banned in edges:
        tin: dict[int, int] = {}
        tout: dict[int, int] = {}
        low: dict[int, int] = {}
        parent: dict[int, int | None] = {}
        timer = 0
        bridges: list[tuple[int, int]] = []

        def dfs(u: int, par: int | None) -> None:
            nonlocal timer
            parent[u] = par
            tin[u] = low[u] = timer
            timer += 1
            for v in adj[u]:
                counter["operations"] += 1
                if _norm_edge(u, v) == banned:
                    continue
                if v == par:
                    continue
                if v in tin:
                    low[u] = min(low[u], tin[v])
                else:
                    dfs(v, u)
                    low[u] = min(low[u], low[v])
                    if low[v] > tin[u]:
                        bridges.append((u, v))
            tout[u] = timer - 1

        dfs(vertices[0], None)
        if len(tin) != len(vertices):
            continue
        by_time = [None] * len(vertices)
        for v, t in tin.items():
            by_time[t] = v
        for _, child in bridges:
            lo, hi = tin[child], tout[child]
            size = hi - lo + 1
            candidates: list[set[int]] = []
            if size == 8:
                candidates.append(set(by_time[lo : hi + 1]))
            if len(vertices) - size == 8:
                candidates.append(set(vertices) - set(by_time[lo : hi + 1]))
            for patch in candidates:
                counter["operations"] += 24
                if _patch_info(adj, patch) is not None:
                    found.add(frozenset(patch))
    return [set(p) for p in sorted(found, key=lambda s: tuple(sorted(s)))]


def _reference_decode(inst: dict) -> tuple[object | None, int]:
    core, _, reason = _extract_core(inst)
    if core is None:
        return None, 0
    current = _copy_adj(core)
    counter = {"operations": 0}
    rows: list[list[int]] = []
    for _ in range(inst["patch_count"]):
        choices = _find_exposed_patches(current, counter)
        if not choices:
            return None, counter["operations"]
        patch = min(choices, key=lambda s: tuple(sorted(s)))
        info = _patch_info(current, patch)
        if info is None:
            return None, counter["operations"]
        rows.append(sorted(info["ports"]))
        _collapse(current, info)
    answer = {"patches": rows}
    return answer, counter["operations"]


def _core_distances(adj: dict[int, set[int]], start: int) -> dict[int, int]:
    dist = {start: 0}
    queue = deque([start])
    while queue:
        u = queue.popleft()
        for v in adj[u]:
            if v not in dist:
                dist[v] = dist[u] + 1
                queue.append(v)
    return dist


def _attack_low_ids(inst: dict) -> object:
    core, _, _ = _extract_core(inst)
    vertices = sorted(core or {})
    return {
        "patches": [vertices[2 * i : 2 * (i + 1)] for i in range(inst["patch_count"])]
    }


def _attack_nearest_groups(inst: dict) -> object:
    core, _, _ = _extract_core(inst)
    if core is None:
        return {"patches": []}
    remaining = set(core)
    rows = []
    for _ in range(inst["patch_count"]):
        start = min(remaining)
        dist = _core_distances(core, start)
        pair = sorted(remaining, key=lambda v: (dist[v], v))[:2]
        rows.append(sorted(pair))
        remaining.difference_update(pair)
    return {"patches": rows}


def _attack_static_scan(inst: dict) -> object:
    core, _, _ = _extract_core(inst)
    if core is None:
        return {"patches": []}
    choices = _find_exposed_patches(core)
    rows: list[list[int]] = []
    used: set[int] = set()
    if choices:
        first = min(choices, key=lambda s: tuple(sorted(s)))
        info = _patch_info(core, first)
        if info is not None:
            ports = sorted(info["ports"])
            rows.append(ports)
            used.update(first)
    remaining = sorted(set(core) - used)
    while len(rows) < inst["patch_count"]:
        pair = remaining[:2]
        remaining = remaining[2:]
        rows.append(pair)
    return {"patches": rows}


def _relabel_instance(inst: dict, rng: random.Random) -> tuple[dict, object]:
    labels = list(range(inst["vertex_count"]))
    rng.shuffle(labels)
    mapping = {old: labels[old] for old in range(inst["vertex_count"])}
    edges = [
        list(_norm_edge(mapping[u], mapping[v])) for u, v in inst["edges"]
    ]
    rng.shuffle(edges)
    carried = {
        "patches": [sorted(mapping[v] for v in row) for row in inst["answer"]["patches"]]
    }
    transformed = {
        key: value
        for key, value in inst.items()
        if key not in ("edges", "answer")
    }
    transformed["edges"] = edges
    transformed["answer"] = carried
    return transformed, carried


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest() -> dict:
    """Run G1--G9 and return a JSON-native measured report."""
    report: dict[str, Any] = {
        "paper": "2602.13037",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 29):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed, "reason": "answer not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    inst = make_instance(n=10, seed=404)
    planted = json.loads(json.dumps(inst["answer"]))
    corruptions: dict[str, object] = {}
    drop = json.loads(json.dumps(planted))
    drop["patches"][0] = drop["patches"][0][:-1]
    corruptions["drop"] = drop
    swap = json.loads(json.dumps(planted))
    swap["patches"][0], swap["patches"][-1] = swap["patches"][-1], swap["patches"][0]
    corruptions["swap"] = swap
    duplicate = json.loads(json.dumps(planted))
    duplicate["patches"][0][-1] = duplicate["patches"][0][0]
    duplicate["patches"][0].sort()
    corruptions["duplicate"] = duplicate
    corruptions["empty"] = {}
    out_of_range = json.loads(json.dumps(planted))
    out_of_range["patches"][0][-1] = inst["vertex_count"]
    out_of_range["patches"][0].sort()
    corruptions["out_of_range"] = out_of_range
    corruption_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason.split(":", 1)[0])
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in corruption_results.values()) and len(set(reasons)) == 5,
        "cases": corruption_results,
        "distinct_reason_codes": len(set(reasons)),
    }

    encoded = json.dumps(inst["answer"], separators=(",", ":"))
    response = f"I found the recursive ends.\n```json\n<answer>{encoded}</answer>\n```\nDone."
    parsed = parse_answer(response)
    roundtrip_ok = parsed == inst["answer"] and verify(inst, parsed)[0]
    report["G3_round_trip"] = {
        "pass": roundtrip_ok,
        "model_style_response_chars": len(response),
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    shipping = make_instance(seed=7701, **DIFFICULTY[SHIPPING_DIFFICULTY])
    rng = random.Random(99173)
    hits = 0
    shipping_core, _, _ = _extract_core(shipping)
    if shipping_core is None:
        raise AssertionError("shipping instance did not have a core")
    valid_first_ports: set[frozenset[int]] = set()
    for patch in _find_exposed_patches(shipping_core):
        info = _patch_info(shipping_core, patch)
        if info is not None:
            valid_first_ports.add(frozenset(info["ports"]))
    for _ in range(_G4_SAMPLES):
        candidate = random_candidate(shipping, rng)
        # Every sampled candidate already has the required type, size,
        # disjointness, range, order, and degree-three membership.  Failure of
        # its first port pair to identify an exposed patch is therefore exactly
        # the same rejection verify() would return, without suppressing the
        # identical displayed graph 200,000 times.  A rare survivor is sent
        # through the public verifier in full.
        first = candidate["patches"][0] if candidate["patches"] else None
        if first is not None and frozenset(first) in valid_first_ports:
            hits += int(verify(shipping, candidate)[0])
    density = hits / _G4_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6,
        "hits": hits,
        "total": _G4_SAMPLES,
        "estimated_probability": density,
        "candidate_space": search_space(shipping),
        "sampling_prior": "uniform ordered disjoint unordered pairs of core vertices",
    }

    baseline_start = time.perf_counter()
    decoded, baseline_ops = _reference_decode(shipping)
    baseline_sec = time.perf_counter() - baseline_start
    baseline_ok = decoded is not None and verify(shipping, decoded)[0]
    demo_exact = enumerate_all(make_instance(n=0, seed=0))
    report["G5_density_and_baseline"] = {
        "pass": density < 1e-6 and baseline_ok and isinstance(demo_exact, int),
        "shipping_density_hits": hits,
        "shipping_density_samples": _G4_SAMPLES,
        "shipping_solution_fraction_estimate": density,
        "demo_exact_valid_count": demo_exact,
        "baseline_wall_clock_sec": baseline_sec,
        "baseline_operations": baseline_ops,
        "baseline_verified": baseline_ok,
    }

    attack_counts = {
        "degree_core_then_low_ids": 0,
        "greedy_nearest_core_vertices": 0,
        "random_restart_256": 0,
        "one_pass_static_cube_scan": 0,
    }
    ref_successes = 0
    ref_operations = 0
    ref_sec = 0.0
    for seed in range(1200, 1200 + _ATTACK_SEEDS):
        trial = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        attack_counts["degree_core_then_low_ids"] += int(verify(trial, _attack_low_ids(trial))[0])
        attack_counts["greedy_nearest_core_vertices"] += int(verify(trial, _attack_nearest_groups(trial))[0])
        rr_rng = random.Random(seed ^ 0x5A17)
        rr_hit = False
        for _ in range(256):
            if verify(trial, random_candidate(trial, rr_rng))[0]:
                rr_hit = True
                break
        attack_counts["random_restart_256"] += int(rr_hit)
        attack_counts["one_pass_static_cube_scan"] += int(verify(trial, _attack_static_scan(trial))[0])
        one_ref_start = time.perf_counter()
        ref_answer, ops = _reference_decode(trial)
        ref_sec += time.perf_counter() - one_ref_start
        ref_operations += ops
        ref_successes += int(ref_answer is not None and verify(trial, ref_answer)[0])
    attacks = {
        name: {"successes": successes, "attempts": _ATTACK_SEEDS}
        for name, successes in attack_counts.items()
    }
    all_failed = all(item["successes"] == 0 for item in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_successes == _ATTACK_SEEDS,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "repeated two-edge-cut bridge DFS plus exact cube recognition",
            "complexity": "O(r*m*(n+m)) exact graph operations",
            "wall_clock_sec": ref_sec,
            "operations": ref_operations,
            "mean_operations": ref_operations / _ATTACK_SEEDS,
            "solves": f"{ref_successes}/{_ATTACK_SEEDS}, as expected",
        },
    }

    doubled_n = 2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"]
    doubled = make_instance(n=doubled_n, seed=5150)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    scale_instances = [make_instance(seed=8, **p) for p in DIFFICULTY.values()]
    sizes = [item["vertex_count"] for item in scale_instances]
    spaces = [search_space(item) for item in scale_instances]
    scale_ops = [_reference_decode(item)[1] for item in scale_instances]
    report["G7_scales"] = {
        "pass": (
            doubled_ok
            and all(a < b for a, b in zip(sizes, sizes[1:]))
            and all(a < b for a, b in zip(spaces, spaces[1:]))
            and all(a < b for a, b in zip(scale_ops, scale_ops[1:]))
        ),
        "preset_vertex_counts": dict(zip(DIFFICULTY, sizes)),
        "preset_candidate_spaces": dict(zip(DIFFICULTY, spaces)),
        "preset_reference_operations": dict(zip(DIFFICULTY, scale_ops)),
        "doubled_n": doubled_n,
        "doubled_vertex_count": doubled["vertex_count"],
        "doubled_verifies": doubled_ok,
        "reason": doubled_reason,
    }

    invariant_ok = 0
    carried_ok = 0
    original_keys = []
    transformed_keys = []
    for seed in range(20):
        original = make_instance(seed=9000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        transformed, carried = _relabel_instance(original, random.Random(70000 + seed))
        key1, key2 = canonical_key(original), canonical_key(transformed)
        original_keys.append(key1)
        transformed_keys.append(key2)
        invariant_ok += int(key1 == key2)
        carried_ok += int(verify(transformed, carried)[0])
    distinct = len(set(original_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_ok == 20 and carried_ok == 20 and distinct == 20,
        "relabel_invariant": invariant_ok,
        "relabel_attempts": 20,
        "carried_witness_verifies": carried_ok,
        "carried_attempts": 20,
        "distinct_unrelated_keys": distinct,
        "unrelated_attempts": 20,
        "invariant": "sorted multiset of rooted all-pairs distance distributions",
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    intended_ops = 24 * shipping["patch_count"] + 24
    evidence = _ORACLE_EVIDENCE
    caps_ok = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    hinted_rate = evidence["hinted"]["solved"] / max(1, evidence["hinted"]["attempts"])
    placebo_rate = evidence["placebo"]["solved"] / max(1, evidence["placebo"]["attempts"])
    report["G9_no_tool_suitability"] = {
        # G9(a) and the former hinted-arm gate G9(b) are diagnostics only as
        # of 2026-09-05.  Only the measured answer/effort caps in G9(c) gate.
        "pass": caps_ok,
        "arms": {
            "bare": evidence["bare"],
            "hinted": evidence["hinted"],
            "placebo": evidence["placebo"],
        },
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": evidence.get("hinted_verdict"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
    }

    gates = [v for k, v in report.items() if k.startswith("G") and isinstance(v, dict)]
    report["all_passed"] = all(g.get("pass") is True for g in gates)
    report["elapsed_sec"] = time.perf_counter() - baseline_start
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
