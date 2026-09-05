"""Verified generator for compact proper-tree representations.

The family uses the paper's compact-representation characterization directly.
Instances are made from a tree of maximal cliques; the answer is known before
the intersection graph is assembled.  Only the Python standard library is used.
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


TRACK = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "graph",
        "tree host",
        "maximal-clique models on the host tree",
    ],
    "verification_operations": [
        "graph adjacency comparison",
        "maximal-clique test",
        "tree connectedness test",
        "escape-condition test",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Simplicial closed neighborhoods expose the maximal cliques, whose "
        "overlap topology is the nonleaf part of the host tree; without this "
        "decomposition one must search over clique-to-tree assignments."
    ),
    "hardness_basis": (
        "Track B: the Section 4 recognition algorithm runs in "
        "2^{O(t^2 log t)} N^3 time in general; on this distribution the "
        "reference specialization (simplicial-neighborhood enumeration plus "
        "AHU tree isomorphism) is polynomial, O(N^2 Delta + k^2 s + "
        "k^2 log k), and at shipping n=96 used at most 35,723 primitive "
        "set/adjacency operations and 0.005 seconds over eight measured seeds, "
        "whereas the compact decomposition route visits at most 287 objects."
    ),
    "max_answer_tokens": 109,
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
        "A JSON list with one graph-vertex identifier for each nonleaf host "
        "node (host nodes taken in increasing identifier order).  The chosen "
        "vertices are distinct, their closed neighborhoods are distinct "
        "maximal cliques, and exactly one representative of every such "
        "simplicial-neighborhood class is used."
    ),
    "bounds": {
        "rows": 1,
        "length": "number of nonleaf host nodes",
        "entry_min": 0,
        "entry_max": "number of graph vertices minus one",
        "entries_distinct": True,
        "one_representative_per_maximal_clique": True,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 5, "private_twins": 1, "edge_twins": 1},
    "easy": {"n": 40, "private_twins": 1, "edge_twins": 1},
    "medium": {"n": 68, "private_twins": 1, "edge_twins": 1},
    "hard": {"n": 96, "private_twins": 1, "edge_twins": 1},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Look for the nonempty-overlap topology of maximal-clique neighborhoods "
    "centered at simplicial vertices."
)
PLACEBO_HINT = (
    "Keep the two numbered adjacency lists distinct while checking all of the "
    "required incidences carefully."
)

# Filled from script-owned evidence after the three hardening runs.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 2},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "blocked_key_limit",
}

NOTES = r"""
Section 2 fixes the native definition: an H-representation assigns every graph
vertex a nonempty connected node-set in a subdivision of H, adjacency is exactly
intersection, and properness forbids containment.  Section 3, Definition 4
replaces a proper representation by a compact one with (C1) empty host leaves,
(C2) a bijection from nonleaves to maximal cliques, and (C3) an escape edge for
every ordered vertex pair.  Theorem 7 proves that, for connected G and T != K1,
a proper T-representation exists exactly when a compact representation exists.
This module asks for that paper-native compact object, not for a graph surrogate.

The easy-result triage is decisive.  Theorem 1 gives recognition and a witness in
2^{O(t^2 log t)} n^3 time, and the introduction records linear algorithms for
proper interval and proper circular-arc graphs.  A Track A claim would therefore
be false for fixed/small T.  This is Track B: the executable reference route on
our special distribution enumerates maximal cliques from simplicial closed
neighborhoods and applies rooted-tree (AHU) isomorphism.  Generation never runs
that route.  It samples the host tree and its connected singleton/edge models
first, carries them through independent host and graph relabellings, and only
then computes the intersection graph.

Section 5, Theorem 2 proves NP-completeness for one fixed non-tree multigraph by
reducing height-one interval dimension at most three.  That worst-case result did
not justify Track A for an inverse distribution: a prototype made by intersecting
three random interval orders was recovered by incremental cycle-pruning in about
300 search nodes and 0.07 seconds at 20+20 poset elements.  That candidate was
discarded before this module was built.

The outlier attack aligns clique size with host degree, the greedy attack aligns
one-hop local degree signatures, the random-restart attack tries 256 uniformly
random structure-aware assignments, and the in-context attack performs only two
rounds of color refinement.  Random asymmetric host trees and independent label
permutations defeat all four, while the complete reference tree-isomorphism
algorithm succeeds as Track B requires.  Private and edge model multiplicities
are uniform throughout an instance; no single planted representative is graded,
and verify accepts every representative and every host-tree automorphism that
forms a valid compact representation.
""".strip()


def _validate_params(n: int, private_twins: int, edge_twins: int) -> None:
    for name, value, lower in (
        ("n", n, 4),
        ("private_twins", private_twins, 1),
        ("edge_twins", edge_twins, 1),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < lower:
            raise ValueError(f"{name} must be an integer at least {lower}")


def _edges_from_prufer(n: int, rng: random.Random) -> list[list[int]]:
    """Uniform labelled tree, returned as sorted two-element lists."""
    seq = [rng.randrange(n) for _ in range(n - 2)]
    degree = [1] * n
    for x in seq:
        degree[x] += 1
    edges = []
    for x in seq:
        leaf = min(i for i, d in enumerate(degree) if d == 1)
        edges.append([leaf, x] if leaf < x else [x, leaf])
        degree[leaf] -= 1
        degree[x] -= 1
    ends = [i for i, d in enumerate(degree) if d == 1]
    edges.append(sorted(ends))
    return sorted(edges)


def _relabel_edges(edges: list[list[int]], mapping: list[int]) -> list[list[int]]:
    return sorted([sorted((mapping[u], mapping[v])) for u, v in edges])


def _adjacency(count: int, edges: list[list[int]]) -> list[set[int]]:
    adj = [set() for _ in range(count)]
    for u, v in edges:
        adj[u].add(v)
        adj[v].add(u)
    return adj


def _intersection_graph(models: list[set[int]]) -> list[list[int]]:
    edges = []
    for u in range(len(models)):
        for v in range(u + 1, len(models)):
            if models[u] & models[v]:
                edges.append([u, v])
    return edges


def make_instance(n: int, seed: int = 0, private_twins: int = 1,
                  edge_twins: int = 1, **params) -> dict:
    """Inverse-generate a certified compact representation.

    The host, all connected models, and the clique representatives are sampled
    before the graph is formed.  No recognition or certificate search occurs.
    """
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, private_twins, edge_twins)
    rng = random.Random(seed)

    core_edges = _edges_from_prufer(n, rng)
    core_adj = _adjacency(n, core_edges)

    # Attach an empty leaf to every leaf of the core.  Therefore precisely the
    # original n nodes are nonleaves and are in bijection with maximal cliques.
    host_edges = [edge[:] for edge in core_edges]
    next_host = n
    for x in range(n):
        if len(core_adj[x]) == 1:
            host_edges.append([x, next_host])
            next_host += 1

    # Paper-native models: private singleton models create each maximal clique;
    # edge models make adjacent clique nodes overlap.  Multiplicity is uniform.
    models: list[set[int]] = []
    private_ids: list[list[int]] = [[] for _ in range(n)]
    for x in range(n):
        for _ in range(private_twins):
            private_ids[x].append(len(models))
            models.append({x})
    for x, y in core_edges:
        for _ in range(edge_twins):
            models.append({x, y})

    # Independent relabellings remove position as a certificate signal.  The
    # witness is carried through these maps rather than rediscovered.
    host_map = list(range(next_host))
    graph_map = list(range(len(models)))
    rng.shuffle(host_map)
    rng.shuffle(graph_map)
    host_edges = _relabel_edges(host_edges, host_map)
    relabelled_models = [set() for _ in models]
    for old_v, model in enumerate(models):
        relabelled_models[graph_map[old_v]] = {host_map[x] for x in model}
    graph_edges = _intersection_graph(relabelled_models)

    active = sorted(host_map[x] for x in range(n))
    host_to_rep = {
        host_map[x]: graph_map[private_ids[x][0]] for x in range(n)
    }
    answer = [host_to_rep[x] for x in active]

    return {
        "family": "compact_proper_tree_representation",
        "n": n,
        "private_twins": private_twins,
        "edge_twins": edge_twins,
        "tree_n": next_host,
        "tree_edges": host_edges,
        "graph_n": len(models),
        "graph_edges": graph_edges,
        "answer": answer,
    }


def _format_adjacency(count: int, edges: list[list[int]]) -> list[str]:
    adj = _adjacency(count, edges)
    return [f"{i}: " + " ".join(map(str, sorted(adj[i]))) for i in range(count)]


def render(inst: dict) -> str:
    tadj = _adjacency(inst["tree_n"], inst["tree_edges"])
    active = [x for x in range(inst["tree_n"]) if len(tadj[x]) > 1]
    lines = [
        "COMPACT PROPER-TREE REPRESENTATION",
        "",
        "All graph and host-tree vertex identifiers are 0-based.  The two "
        "kinds of identifier are separate.",
        "",
        "For a graph vertex v, its closed neighborhood N[v] is v together "
        "with every graph neighbor of v.  A clique is a set of pairwise "
        "adjacent graph vertices.  It is maximal if no strictly larger clique "
        "contains it.  A host node is a leaf exactly when its host-tree degree "
        "is one.",
        "",
        "Your certificate is one graph-vertex identifier for each nonleaf "
        "host node, in the increasing host-node order printed below.  At host "
        "node x, the chosen graph vertex v installs the clique N[v].  Every "
        "chosen N[v] must be maximal; these cliques must be distinct and must "
        "use every distinct maximal-clique neighborhood exactly once.  Host "
        "leaves install the empty clique.",
        "",
        "For each graph vertex u, define its model M_u as the host nodes whose "
        "installed clique contains u.  The certificate is valid exactly when:",
        "(1) every M_u is nonempty and induces a connected host subtree;",
        "(2) two distinct graph vertices are adjacent exactly when their "
        "models intersect; and",
        "(3) for every ordered pair (u,v), including u=v, some oriented host "
        "edge x->y has u in the clique at x and v absent from the clique at y.  "
        "This is the paper's escape condition.  These conditions, empty host "
        "leaves, and the maximal-clique bijection define a compact "
        "representation.  Order matters only because list position names a "
        "host node; graph identifiers may not repeat.",
        "",
        f"Graph G has {inst['graph_n']} vertices.  Its adjacency list is:",
    ]
    lines.extend(_format_adjacency(inst["graph_n"], inst["graph_edges"]))
    lines.extend([
        "",
        f"Host tree T has {inst['tree_n']} nodes.  Its adjacency list is:",
    ])
    lines.extend(_format_adjacency(inst["tree_n"], inst["tree_edges"]))
    lines.extend([
        "",
        "Nonleaf host nodes, in certificate order: " + " ".join(map(str, active)),
        f"The answer must be a JSON list of exactly {len(active)} integers.",
        "Give your final answer inside <answer></answer> tags, as that JSON list.",
        "Example: <answer>[3, 17, 42]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text) -> object | None:
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    candidates = blocks if blocks else re.findall(
        r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text,
        flags=re.IGNORECASE,
    )
    if not candidates:
        # Conservative prose tolerance: take a single bracketed JSON array.
        matches = re.findall(r"\[[\s\d,\-]*\]", text)
        candidates = matches if len(matches) == 1 else []
    if not candidates:
        return None
    raw = candidates[-1].strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
        raw = re.sub(r"```$", "", raw).strip()
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    return value


def _is_tree(count: int, edges: list[list[int]]) -> bool:
    if count < 1 or len(edges) != count - 1:
        return False
    try:
        adj = _adjacency(count, edges)
    except (IndexError, TypeError, ValueError):
        return False
    seen = {0}
    stack = [0]
    while stack:
        u = stack.pop()
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return len(seen) == count


def _connected_subset(adj: list[set[int]], nodes: set[int]) -> bool:
    if not nodes:
        return False
    start = next(iter(nodes))
    seen = {start}
    stack = [start]
    while stack:
        u = stack.pop()
        for v in adj[u] & nodes:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return seen == nodes


def _closed_neighborhoods(inst: dict) -> tuple[list[set[int]], list[set[int]]]:
    gadj = _adjacency(inst["graph_n"], inst["graph_edges"])
    closed = [gadj[v] | {v} for v in range(inst["graph_n"])]
    return gadj, closed


def _all_maximal_cliques(gadj: list[set[int]]) -> set[frozenset[int]]:
    """Enumerate maximal cliques exactly with pivoted Bron--Kerbosch."""
    found: set[frozenset[int]] = set()

    def visit(chosen: set[int], possible: set[int], excluded: set[int]) -> None:
        if not possible and not excluded:
            found.add(frozenset(chosen))
            return
        union = possible | excluded
        pivot = max(union, key=lambda u: len(possible & gadj[u])) if union else None
        branch = possible - (gadj[pivot] if pivot is not None else set())
        for v in sorted(branch):
            visit(chosen | {v}, possible & gadj[v], excluded & gadj[v])
            possible.remove(v)
            excluded.add(v)

    visit(set(), set(range(len(gadj))), set())
    return found


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Check a candidate without consulting inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if not _is_tree(inst["tree_n"], inst["tree_edges"]):
        return False, "the supplied host is not a tree"
    tadj = _adjacency(inst["tree_n"], inst["tree_edges"])
    active = [x for x in range(inst["tree_n"]) if len(tadj[x]) > 1]
    if len(answer) != len(active):
        return False, f"wrong number of representatives: expected {len(active)}"
    for value in answer:
        if isinstance(value, bool) or not isinstance(value, int):
            return False, "every representative must be an integer"
        if value < 0 or value >= inst["graph_n"]:
            return False, "representative identifier out of range"

    gadj, closed = _closed_neighborhoods(inst)
    cliques = []
    for rep in answer:
        clique = closed[rep]
        if any(v not in gadj[u] for u in clique for v in clique
               if u != v):
            return False, "a representative is not simplicial"
        for w in range(inst["graph_n"]):
            if w not in clique and all(w in gadj[u] for u in clique):
                return False, "a represented clique is not maximal"
        cliques.append(set(clique))
    frozen = [frozenset(c) for c in cliques]
    if len(set(frozen)) != len(frozen):
        return False, "duplicate maximal clique represented"
    if set(frozen) != _all_maximal_cliques(gadj):
        return False, "maximal-clique bijection is incomplete"

    # Exact intersection representation and model connectedness.
    at_node = [set() for _ in range(inst["tree_n"])]
    for x, clique in zip(active, cliques):
        at_node[x] = clique
    models = [set() for _ in range(inst["graph_n"])]
    for x, clique in enumerate(at_node):
        for v in clique:
            models[v].add(x)
    for v, model in enumerate(models):
        if not model:
            return False, f"graph vertex {v} has an empty model"
        if not _connected_subset(tadj, model):
            return False, f"graph vertex {v} has a disconnected model"

    edge_set = {tuple(edge) for edge in inst["graph_edges"]}
    for u in range(inst["graph_n"]):
        for v in range(u + 1, inst["graph_n"]):
            intersects = bool(models[u] & models[v])
            if intersects != ((u, v) in edge_set):
                return False, f"model intersection disagrees with graph edge {u}-{v}"

    # C3, using the equivalent direct boundary-edge test.
    for u, model_u in enumerate(models):
        for v, model_v in enumerate(models):
            escaped = any(y not in model_v for x in model_u for y in tadj[x])
            if not escaped:
                return False, f"escape condition fails for ordered pair ({u},{v})"
    return True, "ok"


def _candidate_groups(inst: dict) -> list[tuple[frozenset[int], list[int]]]:
    cache = inst.get("_candidate_groups_cache")
    if cache is not None:
        return cache
    gadj, closed = _closed_neighborhoods(inst)
    groups: dict[frozenset[int], list[int]] = {}
    for v, clique in enumerate(closed):
        if any(y not in gadj[x] for x in clique for y in clique if x != y):
            continue
        if any(w not in clique and all(w in gadj[x] for x in clique)
               for w in range(inst["graph_n"])):
            continue
        groups.setdefault(frozenset(clique), []).append(v)
    result = sorted(groups.items(), key=lambda item: (tuple(sorted(item[0])), item[1]))
    # The cache contains only data derived from the two visible adjacency lists.
    inst["_candidate_groups_cache"] = result
    return result


def random_candidate(inst: dict, rng: random.Random) -> object:
    groups = _candidate_groups(inst)
    reps = [rng.choice(group) for _, group in groups]
    rng.shuffle(reps)
    return reps


def search_space(inst: dict) -> int | None:
    groups = _candidate_groups(inst)
    count = math.factorial(len(groups))
    for _, reps in groups:
        count *= len(reps)
    return count


def _mapping_valid_fast(inst: dict, answer: list[int]) -> bool:
    """Predicate equivalent to verify on the bounded candidate language."""
    tadj = _adjacency(inst["tree_n"], inst["tree_edges"])
    active = [x for x in range(inst["tree_n"]) if len(tadj[x]) > 1]
    if len(answer) != len(active):
        return False
    groups = _candidate_groups(inst)
    cache = inst.get("_fast_mapping_cache")
    if cache is None:
        by_rep = {rep: i for i, (_, reps) in enumerate(groups) for rep in reps}
        source_edges = [
            (i, j) for i in range(len(groups)) for j in range(i + 1, len(groups))
            if groups[i][0] & groups[j][0]
        ]
        target_index = {x: i for i, x in enumerate(active)}
        target_edges = {
            tuple(sorted((target_index[u], target_index[v])))
            for u, v in inst["tree_edges"] if u in target_index and v in target_index
        }
        cache = (by_rep, source_edges, target_edges)
        inst["_fast_mapping_cache"] = cache
    by_rep, source_edges, target_edges = cache
    try:
        order = [by_rep[rep] for rep in answer]
    except (KeyError, TypeError):
        return False
    if len(set(order)) != len(groups):
        return False
    inverse = {group: slot for slot, group in enumerate(order)}
    return all(tuple(sorted((inverse[i], inverse[j]))) in target_edges
               for i, j in source_edges)


def enumerate_all(inst: dict) -> int | None:
    groups = _candidate_groups(inst)
    if len(groups) > 8:
        return None
    reps = [group[0] for _, group in groups]
    valid_group_orders = 0
    for perm in itertools.permutations(reps):
        if _mapping_valid_fast(inst, list(perm)):
            valid_group_orders += 1
    multiplicity = 1
    for _, group in groups:
        multiplicity *= len(group)
    return valid_group_orders * multiplicity


def _tree_centers(adj: list[set[int]], vertices: list[int]) -> list[int]:
    if len(vertices) <= 2:
        return sorted(vertices)
    remaining = set(vertices)
    degree = {v: len(adj[v] & remaining) for v in remaining}
    leaves = [v for v in remaining if degree[v] <= 1]
    while len(remaining) > 2:
        new = []
        for leaf in leaves:
            if leaf not in remaining:
                continue
            remaining.remove(leaf)
            for nb in adj[leaf] & remaining:
                degree[nb] -= 1
                if degree[nb] == 1:
                    new.append(nb)
        leaves = new
    return sorted(remaining)


def _root_code(adj: list[set[int]], root: int, parent: int = -1,
               ops: list[int] | None = None) -> tuple:
    children = []
    for nb in adj[root]:
        if nb != parent:
            if ops is not None:
                ops[0] += 1
            children.append(_root_code(adj, nb, root, ops))
    children.sort()
    if ops is not None:
        ops[0] += max(1, len(children))
    return tuple(children)


def _map_rooted(adj1: list[set[int]], u: int, p1: int,
                adj2: list[set[int]], v: int, p2: int,
                mapping: dict[int, int], ops: list[int]) -> bool:
    c1 = [x for x in adj1[u] if x != p1]
    c2 = [x for x in adj2[v] if x != p2]
    if len(c1) != len(c2):
        return False
    buckets1: dict[tuple, list[int]] = {}
    buckets2: dict[tuple, list[int]] = {}
    for x in c1:
        buckets1.setdefault(_root_code(adj1, x, u, ops), []).append(x)
    for x in c2:
        buckets2.setdefault(_root_code(adj2, x, v, ops), []).append(x)
    if set(buckets1) != set(buckets2):
        return False
    mapping[u] = v
    for code in sorted(buckets1):
        left = sorted(buckets1[code])
        right = sorted(buckets2[code])
        if len(left) != len(right):
            return False
        for x, y in zip(left, right):
            ops[0] += 1
            if not _map_rooted(adj1, x, u, adj2, y, v, mapping, ops):
                return False
    return True


def _tree_isomorphism(adj1: list[set[int]], vertices1: list[int],
                      adj2: list[set[int]], vertices2: list[int],
                      ops: list[int]) -> dict[int, int] | None:
    if len(vertices1) != len(vertices2):
        return None
    centers1 = _tree_centers(adj1, vertices1)
    centers2 = _tree_centers(adj2, vertices2)
    for u in centers1:
        code_u = _root_code(adj1, u, -1, ops)
        for v in centers2:
            ops[0] += 1
            if code_u != _root_code(adj2, v, -1, ops):
                continue
            mapping: dict[int, int] = {}
            if _map_rooted(adj1, u, -1, adj2, v, -1, mapping, ops):
                return mapping
    return None


def _reference_solve(inst: dict) -> tuple[list[int] | None, int, float]:
    """Polynomial reference route for this generated distribution."""
    start = time.perf_counter()
    ops = [0]
    gadj = _adjacency(inst["graph_n"], inst["graph_edges"])
    closed = [gadj[v] | {v} for v in range(inst["graph_n"])]
    raw: dict[frozenset[int], list[int]] = {}
    for v, clique in enumerate(closed):
        simplicial = True
        for x in clique:
            for y in clique:
                if x != y:
                    ops[0] += 1
                    if y not in gadj[x]:
                        simplicial = False
                        break
            if not simplicial:
                break
        if not simplicial:
            continue
        maximal = True
        for w in range(inst["graph_n"]):
            if w in clique:
                continue
            extends = True
            for x in clique:
                ops[0] += 1
                if w not in gadj[x]:
                    extends = False
                    break
            if extends:
                maximal = False
                break
        if maximal:
            raw.setdefault(frozenset(clique), []).append(v)
    groups = sorted(raw.items(), key=lambda item: tuple(sorted(item[0])))
    k = len(groups)
    source_adj = [set() for _ in range(k)]
    for i in range(k):
        for j in range(i + 1, k):
            ops[0] += min(len(groups[i][0]), len(groups[j][0]))
            if groups[i][0] & groups[j][0]:
                source_adj[i].add(j)
                source_adj[j].add(i)

    tadj = _adjacency(inst["tree_n"], inst["tree_edges"])
    active = [x for x in range(inst["tree_n"]) if len(tadj[x]) > 1]
    active_set = set(active)
    target_core = [neighbors & active_set for neighbors in tadj]
    mapping = _tree_isomorphism(source_adj, list(range(k)),
                                target_core, active, ops)
    if mapping is None:
        return None, ops[0], time.perf_counter() - start
    inverse = {host: group for group, host in mapping.items()}
    answer = [groups[inverse[x]][1][0] for x in active]
    return answer, ops[0], time.perf_counter() - start


def _core_graphs(inst: dict):
    groups = _candidate_groups(inst)
    source = [set() for _ in groups]
    for i in range(len(groups)):
        for j in range(i + 1, len(groups)):
            if groups[i][0] & groups[j][0]:
                source[i].add(j); source[j].add(i)
    tadj = _adjacency(inst["tree_n"], inst["tree_edges"])
    active = [x for x in range(inst["tree_n"]) if len(tadj[x]) > 1]
    return groups, source, tadj, active


def _answer_from_pairing(groups, active, pairing) -> list[int] | None:
    if len(pairing) != len(active):
        return None
    inverse = {host: group for group, host in pairing.items()}
    if set(inverse) != set(active):
        return None
    return [groups[inverse[x]][1][0] for x in active]


def _attack_outlier(inst: dict) -> list[int] | None:
    groups, source, tadj, active = _core_graphs(inst)
    left = sorted(range(len(groups)), key=lambda i: (len(groups[i][0]), i))
    right = sorted(active, key=lambda x: (len(tadj[x] & set(active)), x))
    return _answer_from_pairing(groups, active, dict(zip(left, right)))


def _local_signatures(adj: list[set[int]], vertices: list[int], rounds: int):
    colors = {v: len(adj[v] & set(vertices)) for v in vertices}
    for _ in range(rounds):
        signatures = {
            v: (colors[v], tuple(sorted(colors[w] for w in adj[v]
                                        if w in colors)))
            for v in vertices
        }
        palette = {sig: i for i, sig in enumerate(sorted(set(signatures.values())))}
        colors = {v: palette[signatures[v]] for v in vertices}
    return colors


def _attack_refinement(inst: dict, rounds: int) -> list[int] | None:
    groups, source, tadj, active = _core_graphs(inst)
    c1 = _local_signatures(source, list(range(len(groups))), rounds)
    c2 = _local_signatures(tadj, active, rounds)
    if sorted(c1.values()) != sorted(c2.values()):
        return None
    left = sorted(c1, key=lambda x: (c1[x], x))
    right = sorted(c2, key=lambda x: (c2[x], x))
    return _answer_from_pairing(groups, active, dict(zip(left, right)))


def _attack_random(inst: dict, seed: int, restarts: int = 256) -> list[int] | None:
    rng = random.Random(seed)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if _mapping_valid_fast(inst, candidate):
            return candidate
    return None


def _canonical_tree_code(adj: list[set[int]], vertices: list[int]) -> tuple:
    centers = _tree_centers(adj, vertices)
    return min(_root_code(adj, center) for center in centers)


def canonical_key(inst: dict) -> str:
    tadj = _adjacency(inst["tree_n"], inst["tree_edges"])
    active = [x for x in range(inst["tree_n"]) if len(tadj[x]) > 1]
    code = _canonical_tree_code(tadj, active)
    payload = json.dumps({
        "core": repr(code),
        "private_twins": inst["private_twins"],
        "edge_twins": inst["edge_twins"],
    }, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    out = {k: v for k, v in params.items() if k != "_preset"}
    n = int(out.get("n", 4))
    q = int(out.get("private_twins", 1))
    r = int(out.get("edge_twins", 1))
    # First grow the ambient graph at fixed witness length.
    if r < 4:
        out["edge_twins"] = r + 1
        return out
    if q < 3:
        out["private_twins"] = q + 1
        return out
    # The full mapping is one atom per nonleaf.  Stay below the 256-atom cap.
    if n < 240:
        out["n"] = min(240, n + 24)
        return out
    return "cap_bound"


def _relabel_instance(inst: dict, host_perm: list[int], graph_perm: list[int],
                      reorder_edges: bool = False) -> dict:
    out = {
        key: value for key, value in inst.items()
        if key not in ("tree_edges", "graph_edges", "answer",
                       "_candidate_groups_cache", "_fast_mapping_cache")
    }
    out["tree_edges"] = _relabel_edges(inst["tree_edges"], host_perm)
    out["graph_edges"] = _relabel_edges(inst["graph_edges"], graph_perm)
    if reorder_edges:
        out["tree_edges"] = list(reversed(out["tree_edges"]))
        out["graph_edges"] = list(reversed(out["graph_edges"]))
    old_tadj = _adjacency(inst["tree_n"], inst["tree_edges"])
    old_active = [x for x in range(inst["tree_n"]) if len(old_tadj[x]) > 1]
    carried = {
        host_perm[x]: graph_perm[rep] for x, rep in zip(old_active, inst["answer"])
    }
    new_tadj = _adjacency(inst["tree_n"], out["tree_edges"])
    new_active = [x for x in range(inst["tree_n"]) if len(new_tadj[x]) > 1]
    out["answer"] = [carried[x] for x in new_active]
    return out


def _answer_atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(x) for x in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(x) for x in value)
    return 1


def selftest() -> dict:
    report: dict = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    # G1: all presets and several seeds.
    planted_attempts = 0
    planted_failures = []
    json_native = True
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            planted_attempts += 1
            if not ok:
                planted_failures.append([preset, seed, reason])
            json_native &= json.loads(json.dumps(inst["answer"])) == inst["answer"]
    report["G1_planted_verifies"] = {
        "pass": not planted_failures and json_native,
        "attempts": planted_attempts,
        "failures": planted_failures,
        "answers_json_native": json_native,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    base = make_instance(seed=314159, **ship_params)
    answer = base["answer"]
    corruptions = {}
    tests = {
        "drop_one": answer[:-1],
        "duplicate": answer[:-1] + [answer[0]],
        "empty": [],
        "out_of_range": answer[:-1] + [base["graph_n"]],
    }
    # Find a genuine local swap corruption; automorphic swaps are valid answers.
    swapped = None
    for i in range(len(answer)):
        for j in range(i + 1, len(answer)):
            candidate = answer[:]
            candidate[i], candidate[j] = candidate[j], candidate[i]
            if not verify(base, candidate)[0]:
                swapped = candidate
                break
        if swapped is not None:
            break
    tests["swap_two"] = swapped
    for name, candidate in tests.items():
        if candidate is None:
            corruptions[name] = {"rejected": False, "reason": "no invalid swap found"}
        else:
            ok, reason = verify(base, candidate)
            corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = [item["reason"] for item in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruptions.values())
                and len(set(reasons)) == len(reasons),
        "corruptions": corruptions,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "I matched the clique tree to the nonleaf host.\n\n```json\n"
        + json.dumps(answer) + "\n```\n\nTherefore my final response is "
        + "<answer>" + json.dumps(answer) + "</answer>."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("garbage") is None,
        "parsed_equals_answer": parsed == answer,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4/G5 share a structure-aware shipping-density sample.
    guess_rng = random.Random(8675309)
    density_samples = 200_000
    density_hits = 0
    first_hit_checked = False
    density_start = time.perf_counter()
    for _ in range(density_samples):
        candidate = random_candidate(base, guess_rng)
        if _mapping_valid_fast(base, candidate):
            density_hits += 1
            if not first_hit_checked:
                first_hit_checked = verify(base, candidate)[0]
    density_sec = time.perf_counter() - density_start
    report["G4_guess_resistance"] = {
        "pass": density_hits / density_samples < 1e-6,
        "hits": density_hits,
        "total": density_samples,
        "estimated_probability": density_hits / density_samples,
        "candidate_space": str(search_space(base)),
        "structure_aware": True,
        "any_hit_cross_checked_with_verify": first_hit_checked if density_hits else None,
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_exact = enumerate_all(demo)
    demo_space = search_space(demo)
    ref_answer, ref_ops, ref_sec = _reference_solve(base)
    ref_ok = ref_answer is not None and verify(base, ref_answer)[0]
    fail_start = time.perf_counter()
    fail_candidate = _attack_random(base, 271828, 256)
    fail_sec = time.perf_counter() - fail_start
    report["G5_density_and_baseline"] = {
        "pass": density_hits / density_samples < 1e-6 and ref_ok,
        "shipping_density_hits": density_hits,
        "shipping_density_samples": density_samples,
        "shipping_density_fraction": density_hits / density_samples,
        "density_sampling_wall_sec": round(density_sec, 6),
        "demo_valid_solution_count": demo_exact,
        "demo_candidate_count": demo_space,
        "reference_wall_clock_sec": round(ref_sec, 6),
        "reference_operations": ref_ops,
        "reference_solved": ref_ok,
        "strongest_failing_attack_wall_sec": round(fail_sec, 6),
        "strongest_failing_attack_iterations": 256,
        "strongest_failing_attack_solved": fail_candidate is not None,
    }

    attack_names = (
        "outlier_clique_size",
        "greedy_one_hop_signature",
        "random_restart_256",
        "by_hand_two_round_refinement",
    )
    attack_counts = {name: 0 for name in attack_names}
    reference_successes = 0
    reference_ops = []
    reference_times = []
    attempts = 8
    for seed in range(800, 800 + attempts):
        inst = make_instance(seed=seed, **ship_params)
        candidates = {
            "outlier_clique_size": _attack_outlier(inst),
            "greedy_one_hop_signature": _attack_refinement(inst, 1),
            "random_restart_256": _attack_random(inst, seed ^ 0xBAD5EED, 256),
            "by_hand_two_round_refinement": _attack_refinement(inst, 2),
        }
        for name, candidate in candidates.items():
            if candidate is not None and verify(inst, candidate)[0]:
                attack_counts[name] += 1
        ref, ops, seconds = _reference_solve(inst)
        if ref is not None and verify(inst, ref)[0]:
            reference_successes += 1
        reference_ops.append(ops)
        reference_times.append(seconds)
    attacks = {
        name: {"successes": attack_counts[name], "attempts": attempts}
        for name in attack_names
    }
    all_failed = all(item["successes"] == 0 for item in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == attempts,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "simplicial maximal-clique enumeration plus AHU tree isomorphism",
            "complexity": "O(N^2*Delta + k^2*s + k^2*log(k)) on this distribution",
            "wall_clock_sec": round(sum(reference_times), 6),
            "max_wall_clock_sec": round(max(reference_times), 6),
            "operations": sum(reference_ops),
            "max_operations_per_instance": max(reference_ops),
            "solves": f"{reference_successes}/{attempts}, as expected",
        },
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["graph_n"] > base["graph_n"],
        "shipping_n": ship_params["n"],
        "doubled_n": doubled_params["n"],
        "shipping_graph_vertices": base["graph_n"],
        "doubled_graph_vertices": doubled["graph_n"],
        "doubled_verification": doubled_reason,
    }

    invariant_checks = 0
    carried_checks = 0
    keys = []
    g8_failures = []
    for seed in range(20):
        inst = make_instance(seed=10_000 + seed, **ship_params)
        key = canonical_key(inst)
        keys.append(key)
        rng = random.Random(90_000 + seed)
        hp = list(range(inst["tree_n"])); rng.shuffle(hp)
        gp = list(range(inst["graph_n"])); rng.shuffle(gp)
        transforms = [
            _relabel_instance(inst, hp, list(range(inst["graph_n"]))),
            _relabel_instance(inst, list(range(inst["tree_n"])), gp),
            _relabel_instance(inst, hp, gp, reorder_edges=True),
        ]
        for transformed in transforms:
            invariant_checks += 1
            if canonical_key(transformed) != key:
                g8_failures.append([seed, "key changed"])
            carried_checks += 1
            ok, reason = verify(transformed, transformed["answer"])
            if not ok:
                g8_failures.append([seed, reason])
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated_keys": distinct,
        "unrelated_instances": 20,
        "failures": g8_failures,
        "invariant": "AHU canonical form of the nonleaf host tree plus multiplicities",
    }

    # G9(a,b) is updated from script-owned transcripts after the oracle runs.
    worst_chars = 0
    worst_atoms = 0
    for seed in range(20):
        inst = make_instance(seed=70_000 + seed, **ship_params)
        worst_chars = max(worst_chars, len(json.dumps(inst["answer"])))
        worst_atoms = max(worst_atoms, _answer_atoms(inst["answer"]))
    answer_tokens = math.ceil(worst_chars / 4)
    intended_ops = base["graph_n"] + len(base["answer"])
    evidence = G9_EVIDENCE
    hinted_hardened = evidence.get("hinted_verdict") == "hardened"
    within_caps = worst_chars <= 2000 and worst_atoms <= 256 and intended_ops <= 300
    hinted_attempts = evidence.get("hinted", {}).get("attempts", 0)
    g9_ready = hinted_attempts >= 3
    hinted_rate = (
        evidence["hinted"]["solved"] / evidence["hinted"]["attempts"]
        if evidence["hinted"]["attempts"] else None
    )
    placebo_rate = (
        evidence["placebo"]["solved"] / evidence["placebo"]["attempts"]
        if evidence["placebo"]["attempts"] else None
    )
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps and g9_ready,
        "arms": {
            name: dict(evidence[name]) for name in ("bare", "hinted", "placebo")
        },
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None
        ),
        "hinted_verdict": evidence.get("hinted_verdict", "pending"),
        "answer_chars": worst_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": worst_atoms,
        "intended_route_operations": intended_ops,
        "within_caps": within_caps,
        "oracle_evidence_ready": g9_ready,
    }

    gate_values = [value for key, value in report.items()
                   if key.startswith("G") and isinstance(value, dict)]
    report["all_passed"] = all(value.get("pass") is True for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
