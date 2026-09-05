"""Verified IC-WCOL(1) instances from arXiv:2203.03358.

The paper reduces Independent Set to Incremental Conservative Weak Coloring.
This module applies that exact reduction to a projective-line constraint graph.
The unique independent transversal is planted before the graph is defined.
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


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - complete stdlib fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "succinct IC-WCOL(1) graph",
        "partial vertex ordering",
        "projective-line compatibility graph",
    ],
    "verification_operations": [
        "exact modular projective matrix multiplication",
        "exact compatibility comparison",
        "paper-licensed independent-set equivalence check",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3.1, Theorem 3.1: the paper's polynomial reduction from "
        "Independent Set to IC-WCOL(r), specialized to r=1 and k=2"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "The directed projective maps have parabolic holonomy around their "
        "unique cycle; without recognizing and composing that invariant one "
        "scans the whole projective line."
    ),
    "hardness_basis": (
        "Track B: exhaustive start-value propagation on the unicyclic CSP is "
        "O((p+1)(g+e)); the latest shipping selftest averaged 346,247 exact "
        "transitions and 0.95 seconds, while parabolic holonomy takes at most "
        "220 exact operations."
    ),
    "max_answer_tokens": 34,
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
        "A JSON list of exactly g pairs [i,t], one for every group i=0,...,g-1; "
        "0<=t<=p, with t=p denoting the projective point infinity.  Pair order "
        "is irrelevant and repeated groups or repeated vertices are forbidden."
    ),
    "bounds": {
        "groups": "instance field g",
        "choices_per_group": "p+1",
        "pair_entries": 2,
        "maximum_atomic_elements": 24,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 5, "groups": 4},
    "easy": {"n": 10_000, "groups": 10},
    "medium": {"n": 50_000, "groups": 11},
    "hard": {"n": 100_000, "groups": 12},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "The product of the directed projective maps around the unique cycle has "
    "parabolic holonomy."
)
PLACEBO_HINT = (
    "The directed compatibility records reward especially careful modular "
    "arithmetic and indexing."
)

# Script-owned oracle runs replace these placeholders before the final report.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "too_easy",
}

NOTES = r"""
Section 2 fixes the exact definitions.  For a partial ordering L_S, the paper
uses Observation 2.1 to define weak r-reachability and calls L_S extendable
exactly when its current weak coloring number is at most k.  Section 3.1,
Theorem 3.1, reduces Independent Set to IC-WCOL(r).  At r=1 and k=2 each base
edge {u,v} becomes u-x-v plus the path y1-y2-x, all y1 vertices are preordered,
and appending c base vertices is extendable iff those vertices are independent.
The verifier uses precisely this proved equivalence, not the planted answer.

The paper also identifies the easy regimes that matter here.  Proposition 3.2
gives the XP enumeration O(|V\S|^c poly(|V|)), so constant c is polynomial.
Theorem 3.3 makes the separate WCOL-Merge problem FPT in k+|S2|, and Section 4
reports that practical successful reconstructions mostly have c=1.  This module
therefore does not claim Track A and does not use WCOL-Merge.

The base independent-set graph has one clique for every vertex of a connected
unicyclic constraint graph.  A clique vertex chooses a point of P^1(F_p).
Internally, each constraint edge is a translated match after changing both
endpoints into planted projective coordinate frames.  Tree-edge shifts are
random, while the last cycle shift is chosen to have nonzero holonomy.  The
emitted instance contains only the composed edge maps: it does not contain the
frames or shifts.  The certificate is the image of infinity in each discarded
frame and is known before the IC-WCOL graph is assembled.

The generic Track-B reference algorithm tries all p+1 root values and propagates
each through the unicyclic CSP.  The compact route composes the maps around the
unique cycle, finds the unique fixed point of its parabolic product, and
propagates it through the trees.  Per-choice degrees are exactly tied, greedy
finite propagation chooses a non-solution, random restarts almost never sample
the root fixed point at the shipping modulus, and the constant-coordinate
ansatz violates an edge map.  Topology, frames, shifts, group labels, edge
order, and projective labels are randomized; canonicalization deliberately
forgets all gauge data and exactly canonizes the underlying unicyclic topology.
""".strip()


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    d = 3
    while d * d <= value:
        if value % d == 0:
            return False
        d += 2
    return True


def _next_prime(value: int) -> int:
    p = max(5, int(value))
    if p % 2 == 0:
        p += 1
    while not _is_prime(p):
        p += 2
    return p


def _mat_mul(left: list[list[int]], right: list[list[int]], p: int) -> list[list[int]]:
    return [
        [
            (left[0][0] * right[0][0] + left[0][1] * right[1][0]) % p,
            (left[0][0] * right[0][1] + left[0][1] * right[1][1]) % p,
        ],
        [
            (left[1][0] * right[0][0] + left[1][1] * right[1][0]) % p,
            (left[1][0] * right[0][1] + left[1][1] * right[1][1]) % p,
        ],
    ]


def _mat_inv(matrix: list[list[int]], p: int) -> list[list[int]]:
    a, b = matrix[0]
    c, d = matrix[1]
    det = (a * d - b * c) % p
    if det == 0:
        raise ValueError("singular projective frame")
    scale = pow(det, p - 2, p)
    return [
        [(d * scale) % p, (-b * scale) % p],
        [(-c * scale) % p, (a * scale) % p],
    ]


def _point_vector(point: int, p: int) -> tuple[int, int]:
    return (1, 0) if point == p else (point, 1)


def _apply_homogeneous(matrix: list[list[int]], point: int, p: int) -> tuple[int, int]:
    x, y = _point_vector(point, p)
    return (
        (matrix[0][0] * x + matrix[0][1] * y) % p,
        (matrix[1][0] * x + matrix[1][1] * y) % p,
    )


def _apply_point(matrix: list[list[int]], point: int, p: int) -> int:
    x, y = _apply_homogeneous(matrix, point, p)
    if y == 0:
        return p
    return x * pow(y, p - 2, p) % p


def _phi_infinity(matrix: list[list[int]], p: int) -> int:
    a = matrix[0][0] % p
    c = matrix[1][0] % p
    if c == 0:
        return p
    # Construction uses c in {1,-1}; retain the general exact definition.
    return a * pow(c, p - 2, p) % p


def _prufer_tree(size: int, rng: random.Random) -> list[tuple[int, int]]:
    """Uniform labelled tree from a Prufer sequence."""
    if size == 2:
        return [(0, 1)]
    seq = [rng.randrange(size) for _ in range(size - 2)]
    degree = [1] * size
    for v in seq:
        degree[v] += 1
    edges = []
    for v in seq:
        leaf = next(i for i, d in enumerate(degree) if d == 1)
        edges.append((leaf, v))
        degree[leaf] -= 1
        degree[v] -= 1
    last = [i for i, d in enumerate(degree) if d == 1]
    edges.append((last[0], last[1]))
    return edges


def _tree_offsets(size: int, tree_edges: list[dict], p: int) -> list[int]:
    adjacency = [[] for _ in range(size)]
    for edge in tree_edges:
        u, v, shift = edge["u"], edge["v"], edge["shift"]
        adjacency[u].append((v, shift))
        adjacency[v].append((u, -shift % p))
    offsets = [None] * size
    offsets[0] = 0
    stack = [0]
    while stack:
        u = stack.pop()
        for v, shift in adjacency[u]:
            if offsets[v] is None:
                offsets[v] = (offsets[u] + shift) % p
                stack.append(v)
    if any(x is None for x in offsets):
        raise AssertionError("tree construction disconnected")
    return [int(x) for x in offsets]


def _random_frame(rng: random.Random, p: int) -> list[list[int]]:
    while True:
        c = 1 if rng.randrange(2) == 0 else p - 1
        a = rng.randrange(2, p - 1)
        b = rng.randrange(p)
        d = rng.randrange(p)
        if (a * d - b * c) % p:
            return [[a, b], [c, d]]


def make_instance(n: int, seed: int = 0, groups: int = 12, **params) -> dict:
    """Construct a certified yes-instance without solving the emitted instance."""
    if params:
        raise ValueError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if isinstance(groups, bool) or not isinstance(groups, int) or groups < 3:
        raise ValueError("groups must be an integer at least 3")
    if groups > 128:
        raise ValueError("groups must be at most 128")

    p = _next_prime(n)
    rng = random.Random(seed)

    # A random tree plus one non-tree edge gives a connected unicyclic topology.
    undirected_tree = _prufer_tree(groups, rng)
    occupied = {tuple(sorted(edge)) for edge in undirected_tree}
    nonedges = [
        (u, v) for u in range(groups) for v in range(u + 1, groups)
        if (u, v) not in occupied
    ]
    close_u, close_v = rng.choice(nonedges)

    tree_edges = []
    for left, right in undirected_tree:
        if rng.randrange(2):
            left, right = right, left
        tree_edges.append({
            "u": left,
            "v": right,
            "shift": rng.randrange(p),
        })
    offsets = _tree_offsets(groups, tree_edges, p)

    if rng.randrange(2):
        close_u, close_v = close_v, close_u
    delta = rng.randrange(1, p)
    close_shift = (offsets[close_v] - offsets[close_u] + delta) % p
    edges = tree_edges + [{"u": close_u, "v": close_v, "shift": close_shift}]

    frames = [_random_frame(rng, p) for _ in range(groups)]
    answer = [[i, _phi_infinity(frames[i], p)] for i in range(groups)]

    # Group and variable labels are presentation symmetries, not the diversity
    # source; the unlabelled unicyclic topology varies with the seed.
    group_perm = list(range(groups))
    rng.shuffle(group_perm)
    remap = {old: new for new, old in enumerate(group_perm)}
    frames = [frames[old] for old in group_perm]
    answer = [[remap[i], t] for i, t in answer]
    answer.sort()
    for edge in edges:
        edge["u"] = remap[edge["u"]]
        edge["v"] = remap[edge["v"]]
        translation = [[1, edge.pop("shift")], [0, 1]]
        edge["matrix"] = _mat_mul(
            frames[edge["v"]],
            _mat_mul(translation, _mat_inv(frames[edge["u"]], p), p),
            p,
        )
    rng.shuffle(edges)

    return {
        "family": "IC-WCOL(1) via projective compatibility Independent Set",
        "n": n,
        "seed": seed,
        "p": p,
        "groups": groups,
        "radius": 1,
        "k": 2,
        "c": groups,
        "constraint_edges": edges,
        "answer": answer,
    }


def _base_vertex_count(inst: dict) -> int:
    return inst["groups"] * (inst["p"] + 1)


def _base_edge_count(inst: dict) -> int:
    p, groups = inst["p"], inst["groups"]
    within = groups * p * (p + 1) // 2
    # Each constraint pair has (p+1)^2 total pairs and p+1 compatible pairs.
    between = len(inst["constraint_edges"]) * p * (p + 1)
    return within + between


def render(inst: dict) -> str:
    p = inst["p"]
    lines = [
        "Incremental Conservative Weak 1-Coloring (IC-WCOL(1))",
        "",
        "All arithmetic below is modulo the printed prime p.  The projective line",
        "P^1(F_p) is encoded by the integers 0,...,p: 0,...,p-1 are the usual",
        "field elements and the integer p denotes the point infinity.",
        "",
        "For a nonsingular matrix P=[[a,b],[c,d]], define",
        "  P(t)=(a*t+b)/(c*t+d) on P^1(F_p).",
        "A zero denominator means infinity; P(infinity)=a/c, with c=0 giving",
        "infinity.  P^{-1} uses [[d,-b],[-c,a]]; a nonzero scalar multiple",
        "represents the same projective map.",
        "",
        f"p = {p}",
        f"number of groups g = {inst['groups']}",
        "The constraint graph on the groups is given by directed records",
        "i j a b c d.  Such a record permits exactly the pairs (t_i,t_j)",
        "satisfying t_j=M(t_i), where M=[[a,b],[c,d]].",
        "Constraint records:",
    ]
    for edge in inst["constraint_edges"]:
        matrix = edge["matrix"]
        lines.append(
            f"  {edge['u']} {edge['v']} {matrix[0][0]} {matrix[0][1]} "
            f"{matrix[1][0]} {matrix[1][1]}"
        )
    lines.extend([
        "",
        "These data specify a base graph B.  Its vertices are all pairs (i,t)",
        "with 0<=i<g and 0<=t<=p.  Distinct vertices in the same group are",
        "adjacent.  Vertices in different groups are adjacent exactly when a",
        "constraint record between their groups exists and their values do NOT",
        "form its permitted pair.  Thus each constraint record describes all",
        "incompatible cross-pairs, not just one edge.",
        "",
        "Now construct the IC-WCOL graph H exactly as follows.  For every edge",
        "{u,v} of B, replace it by u--x_{uv}--v and add",
        "y1_{uv}--y2_{uv}--x_{uv}.  The fixed partial ordering L_S contains all",
        "y1_{uv}, in lexicographic order of {u,v}.  All other vertices are free.",
        f"The radius is r=1, the bound is k=2, and c={inst['c']} vertices must be appended.",
        "",
        "For a partial ordering, a vertex q is weakly 1-reachable from v when",
        "q=v, or q is already ordered and the one-edge path q--v has no ordered",
        "vertex before q.  The weak 1-coloring number is the maximum number of",
        "weakly 1-reachable vertices over all vertices of H.  An extension is",
        "extendable when this maximum is at most k.",
        "",
        "Find an extendable right extension obtained by appending c vertices.",
        "For this construction every valid extension necessarily appends exactly",
        "one base vertex (i,t) from each group.  Give those g vertices; their order",
        "inside the answer is irrelevant.  Repeated groups and repeated vertices",
        "are forbidden.  Bounds are inclusive, and group indices are 0-based.",
        "",
        "Give your final answer inside <answer></answer> tags, as one JSON list",
        "of g pairs [i,t], with t=p representing infinity.",
        "Example: <answer>[[0,3],[1,5],[2,0]]</answer>",
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
    match = re.search(r"<answer>\s*(.*?)\s*</answer>", text, re.I | re.S)
    if not match:
        return None
    payload = match.group(1).strip()
    payload = re.sub(r"^```(?:json)?\s*|\s*```$", "", payload,
                     flags=re.I | re.S).strip()
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError):
        return None
    if not isinstance(answer, list):
        return None
    return answer


def _edge_compatible(inst: dict, edge: dict, left_t: int, right_t: int) -> bool:
    p = inst["p"]
    lx, ly = _apply_homogeneous(edge["matrix"], left_t, p)
    rx, ry = _point_vector(right_t, p)
    return (lx * ry - rx * ly) % p == 0


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Verify any valid extension; never consult inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    groups, p = inst["groups"], inst["p"]
    if len(answer) != groups:
        return False, f"wrong length: expected {groups} vertices"
    pairs = []
    for item in answer:
        if (
            not isinstance(item, list) or len(item) != 2
            or any(isinstance(x, bool) or not isinstance(x, int) for x in item)
        ):
            return False, "each vertex must be a two-integer list [group,value]"
        pairs.append((item[0], item[1]))
    if len(set(pairs)) != len(pairs):
        return False, "duplicate base vertex"
    if any(i < 0 or i >= groups for i, _ in pairs):
        return False, "group index out of range"
    if any(t < 0 or t > p for _, t in pairs):
        return False, "projective value out of range"
    by_group = {i: t for i, t in pairs}
    if len(by_group) != groups or set(by_group) != set(range(groups)):
        return False, "must contain exactly one vertex from every group"
    for edge in inst["constraint_edges"]:
        if not _edge_compatible(
            inst, edge, by_group[edge["u"]], by_group[edge["v"]]
        ):
            return False, (
                f"incompatible choices on constraint {edge['u']}->{edge['v']}"
            )
    return True, "ok"


def random_candidate(inst: dict, rng) -> object:
    groups, p = inst["groups"], inst["p"]
    answer = [[i, rng.randrange(p + 1)] for i in range(groups)]
    rng.shuffle(answer)
    return answer


def search_space(inst: dict) -> int | None:
    return (inst["p"] + 1) ** inst["groups"]


def enumerate_all(inst: dict) -> int | None:
    total = search_space(inst)
    if total is None or total > 200_000:
        return None
    count = 0
    for values in itertools.product(range(inst["p"] + 1), repeat=inst["groups"]):
        candidate = [[i, values[i]] for i in range(inst["groups"])]
        if verify(inst, candidate)[0]:
            count += 1
    return count


def _topology_edges(inst: dict) -> list[tuple[int, int]]:
    return [tuple(sorted((edge["u"], edge["v"])))
            for edge in inst["constraint_edges"]]


def _unicyclic_code(inst: dict) -> str:
    """Exact unlabelled canonical form of the connected unicyclic topology."""
    size = inst["groups"]
    adjacency = [set() for _ in range(size)]
    for u, v in _topology_edges(inst):
        adjacency[u].add(v)
        adjacency[v].add(u)
    degree = [len(a) for a in adjacency]
    queue = [i for i, d in enumerate(degree) if d == 1]
    removed = [False] * size
    head = 0
    while head < len(queue):
        u = queue[head]
        head += 1
        removed[u] = True
        for v in adjacency[u]:
            if not removed[v]:
                degree[v] -= 1
                if degree[v] == 1:
                    queue.append(v)
    cycle = [i for i in range(size) if not removed[i]]
    cycle_set = set(cycle)
    if len(cycle) < 3:
        raise ValueError("topology is not a simple unicyclic graph")

    def tree_code(root: int, parent: int) -> str:
        children = [
            tree_code(v, root) for v in adjacency[root]
            if v != parent and v not in cycle_set
        ]
        return "(" + "".join(sorted(children)) + ")"

    start = cycle[0]
    cycle_neighbors = [v for v in adjacency[start] if v in cycle_set]
    order = [start]
    prev, cur = start, cycle_neighbors[0]
    while cur != start:
        order.append(cur)
        nxt = [v for v in adjacency[cur] if v in cycle_set and v != prev]
        prev, cur = cur, nxt[0]
    labels = [tree_code(v, -1) for v in order]
    variants = []
    for seq in (labels, list(reversed(labels))):
        variants.extend("|".join(seq[i:] + seq[:i]) for i in range(len(seq)))
    return min(variants)


def canonical_key(inst: dict) -> str:
    code = (
        f"ICWCOL1-projective-unicyclic:{inst['p']}:"
        f"{inst['groups']}:{_unicyclic_code(inst)}"
    )
    return hashlib.sha256(code.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    clean = {k: v for k, v in params.items() if k != "_preset"}
    n = clean.get("n")
    groups = clean.get("groups", 12)
    if not isinstance(n, int):
        return None
    # The witness stays at exactly 2*groups atoms; only the projective haystack grows.
    if n < 1_000_000_000:
        return {"n": n * 10 + 1, "groups": groups}
    return None


def _spanning_tree(inst: dict) -> tuple[list[dict], list[dict]]:
    parent = list(range(inst["groups"]))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    tree, extra = [], []
    for edge in inst["constraint_edges"]:
        ru, rv = find(edge["u"]), find(edge["v"])
        if ru != rv:
            parent[ru] = rv
            tree.append(edge)
        else:
            extra.append(edge)
    return tree, extra


def _propagate_value(inst: dict, root_value: int, root_group: int = 0) -> tuple[list[int] | None, int]:
    """Propagate one displayed root value; return values and op count."""
    p, groups = inst["p"], inst["groups"]
    tree, extra = _spanning_tree(inst)
    adjacency = [[] for _ in range(groups)]
    for edge in tree:
        u, v, matrix = edge["u"], edge["v"], edge["matrix"]
        adjacency[u].append((v, matrix))
        adjacency[v].append((u, _mat_inv(matrix, p)))
    values = [None] * groups
    values[root_group] = root_value
    stack = [root_group]
    operations = 0
    while stack:
        u = stack.pop()
        for v, matrix in adjacency[u]:
            if values[v] is None:
                values[v] = _apply_point(matrix, values[u], p)
                operations += 1
                stack.append(v)
    for edge in extra:
        u, v, matrix = edge["u"], edge["v"], edge["matrix"]
        expected = _apply_point(matrix, values[u], p)
        operations += 1
        if expected != values[v]:
            return None, operations
    return [int(x) for x in values], operations


def _candidate_from_values(inst: dict, values: list[int]) -> list[list[int]]:
    return [[i, values[i]] for i in range(inst["groups"])]


def _projective_adjugate(matrix: list[list[int]], p: int) -> list[list[int]]:
    """Inverse projective map without the irrelevant determinant scale."""
    a, b = matrix[0]
    c, d = matrix[1]
    return [[d % p, -b % p], [-c % p, a % p]]


def _cycle_vertices(inst: dict) -> list[int]:
    size = inst["groups"]
    adjacency = [set() for _ in range(size)]
    for u, v in _topology_edges(inst):
        adjacency[u].add(v)
        adjacency[v].add(u)
    degree = [len(a) for a in adjacency]
    queue = [i for i, d in enumerate(degree) if d == 1]
    removed = [False] * size
    head = 0
    while head < len(queue):
        u = queue[head]
        head += 1
        removed[u] = True
        for v in adjacency[u]:
            if not removed[v]:
                degree[v] -= 1
                if degree[v] == 1:
                    queue.append(v)
    cycle_set = {i for i in range(size) if not removed[i]}
    start = min(cycle_set)
    order = [start]
    prev = None
    cur = start
    while True:
        choices = sorted(v for v in adjacency[cur] if v in cycle_set and v != prev)
        nxt = choices[0]
        if nxt == start:
            break
        order.append(nxt)
        prev, cur = cur, nxt
    return order


def _compact_holonomy_solver(inst: dict) -> tuple[object | None, dict]:
    """The intended route: compose the unique cycle and use its double fixed point."""
    p = inst["p"]
    cycle = _cycle_vertices(inst)
    by_pair = {
        tuple(sorted((edge["u"], edge["v"]))): edge
        for edge in inst["constraint_edges"]
    }
    product = [[1, 0], [0, 1]]
    operations = 0
    for index, u in enumerate(cycle):
        v = cycle[(index + 1) % len(cycle)]
        edge = by_pair[tuple(sorted((u, v)))]
        if edge["u"] == u:
            step = edge["matrix"]
        else:
            step = _projective_adjugate(edge["matrix"], p)
            operations += 2
        product = _mat_mul(step, product, p)
        operations += 12
    a, b = product[0]
    c, d = product[1]
    if c % p == 0:
        # A nonidentity upper-triangular parabolic has infinity as its sole fix.
        if (a - d) % p == 0 and b % p:
            fixed = p
            operations += 2
        else:
            return None, {"operations": operations, "cycle_length": len(cycle)}
    else:
        # The repeated root of c*t^2+(d-a)*t-b is (a-d)/(2c).
        fixed = ((a - d) * pow((2 * c) % p, p - 2, p)) % p
        operations += 4
    values, transitions = _propagate_value(inst, fixed, cycle[0])
    # Each normalized projective transition costs at most eight scalar modular
    # operations; allow two extra negations when traversing an edge backwards.
    operations += 10 * transitions
    candidate = None if values is None else _candidate_from_values(inst, values)
    return candidate, {"operations": operations, "cycle_length": len(cycle)}


def _reference_enumeration(inst: dict) -> tuple[object | None, dict]:
    """Mechanical Track-B algorithm: enumerate every projective root value."""
    operations = 0
    trials = 0
    # Infinity is deliberately the last ordinary value in the declared encoding.
    for root in range(inst["p"] + 1):
        trials += 1
        values, used = _propagate_value(inst, root)
        operations += used
        if values is not None:
            candidate = _candidate_from_values(inst, values)
            if verify(inst, candidate)[0]:
                return candidate, {"root_trials": trials, "operations": operations}
    return None, {"root_trials": trials, "operations": operations}


def _attack_outlier_degree(inst: dict) -> object:
    # Every t in a fixed group has exactly p*(1+topological_degree) neighbors.
    # A degree ranking is a full tie; its conventional low-label tie-break is t=0.
    return [[i, 0] for i in range(inst["groups"])]


def _attack_greedy(inst: dict) -> object:
    # Pick the lowest label in group 0, then propagate without backtracking.
    values, _ = _propagate_value(inst, 0)
    if values is None:
        return [[i, 0] for i in range(inst["groups"])]
    return _candidate_from_values(inst, values)


def _attack_constant_coordinate(inst: dict) -> object:
    # The tempting common infinity ansatz ignores the conjugating edge maps.
    return _candidate_from_values(inst, [inst["p"]] * inst["groups"])


def _attack_random_restart(inst: dict, seed: int, restarts: int = 256) -> object | None:
    rng = random.Random(seed)
    for _ in range(restarts):
        root = rng.randrange(inst["p"] + 1)
        values, _ = _propagate_value(inst, root)
        if values is not None:
            candidate = _candidate_from_values(inst, values)
            if verify(inst, candidate)[0]:
                return candidate
    return None


def _relabel_instance(inst: dict, rng: random.Random) -> tuple[dict, list[list[int]]]:
    """Compose group, local-coordinate, projective-label, and input-order symmetries."""
    p, groups = inst["p"], inst["groups"]
    perm = list(range(groups))
    rng.shuffle(perm)
    old_to_new = {old: new for new, old in enumerate(perm)}

    # Vertex relabelling t -> t+r_i in each group (infinity stays infinity).
    label_shifts = [rng.randrange(p) for _ in range(groups)]

    relabel = [
        [[1, label_shifts[i]], [0, 1]] for i in range(groups)
    ]

    edges = []
    for edge in inst["constraint_edges"]:
        u, v = edge["u"], edge["v"]
        edges.append({
            "u": old_to_new[u],
            "v": old_to_new[v],
            "matrix": _mat_mul(
                relabel[v],
                _mat_mul(edge["matrix"], _mat_inv(relabel[u], p), p),
                p,
            ),
        })
    rng.shuffle(edges)

    transformed = {
        **{k: v for k, v in inst.items() if k not in {"constraint_edges", "answer"}},
        "constraint_edges": edges,
    }
    carried = []
    for old, t in inst["answer"]:
        new_t = p if t == p else (t + label_shifts[old]) % p
        carried.append([old_to_new[old], new_t])
    rng.shuffle(carried)
    transformed["answer"] = carried
    return transformed, carried


def _answer_atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _reason_distinct_corruptions(inst: dict) -> dict[str, str]:
    answer = json.loads(json.dumps(inst["answer"]))
    corruptions = {
        "empty": [],
        "drop": answer[:-1],
        "duplicate": answer[:-1] + [answer[0]],
        "out_of_range": answer[:-1] + [[answer[-1][0], inst["p"] + 1]],
    }
    changed = json.loads(json.dumps(answer))
    changed[0][1] = (changed[0][1] + 1) % (inst["p"] + 1)
    corruptions["swap_one"] = changed
    reasons = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        if ok:
            raise AssertionError(f"corruption {name} unexpectedly verified")
        reasons[name] = why
    if len(set(reasons.values())) != len(reasons):
        raise AssertionError(f"corruption reasons are not distinct: {reasons}")
    return reasons


def selftest() -> dict:
    report: dict = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1: every preset over several unrelated seeds.
    planted_checks = 0
    g1_ok = True
    for preset, params in DIFFICULTY.items():
        for seed in (3, 17, 101, 1009):
            inst = make_instance(seed=seed, **params)
            ok, _ = verify(inst, inst["answer"])
            g1_ok &= ok
            planted_checks += 1
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_ok = False
    report["G1_planted_verifies"] = {
        "pass": bool(g1_ok), "checks": planted_checks,
        "json_native_checks": planted_checks,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    reasons = _reason_distinct_corruptions(shipping)
    report["G2_rejects_corruption"] = {
        "pass": len(reasons) == 5 and len(set(reasons.values())) == 5,
        "reasons": reasons,
    }

    prose = (
        "I changed to the local projective coordinates.\n```json\n<answer>"
        + json.dumps(shipping["answer"])
        + "</answer>\n```\nThose vertices give the extension."
    )
    parsed = parse_answer(prose)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and verify(shipping, parsed)[0],
        "parsed": parsed == shipping["answer"],
    }

    # G4 and the shipping-density portion of G5 share a structure-aware sample.
    guess_rng = random.Random(220303358)
    samples = 200_000
    hits = 0
    t0 = time.perf_counter()
    for _ in range(samples):
        if verify(shipping, random_candidate(shipping, guess_rng))[0]:
            hits += 1
    guess_seconds = time.perf_counter() - t0
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "prior": "uniform one projective value per displayed group",
        "search_space": search_space(shipping),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    demo = make_instance(seed=23, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    ref_start = time.perf_counter()
    ref_answer, ref_stats = _reference_enumeration(shipping)
    ref_seconds = time.perf_counter() - ref_start
    ref_ok = ref_answer is not None and verify(shipping, ref_answer)[0]
    compact_answer, compact_stats = _compact_holonomy_solver(shipping)
    compact_ok = compact_answer is not None and verify(shipping, compact_answer)[0]
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and hits / samples < 1e-6 and ref_ok and compact_ok,
        "shipping_sampled_valid_hits": hits,
        "shipping_density_samples": samples,
        "shipping_observed_valid_fraction": hits / samples,
        "shipping_constructed_exact_solution_count": 1,
        "demo_exact_solution_count": demo_count,
        "baseline_wall_clock_sec": round(ref_seconds, 6),
        "baseline_root_trials": ref_stats["root_trials"],
        "baseline_operations": ref_stats["operations"],
        "compact_route_operations": compact_stats["operations"],
        "compact_route_cycle_length": compact_stats["cycle_length"],
    }

    attack_names = {
        "outlier_degree_low_label_tie": 0,
        "greedy_no_backtracking": 0,
        "random_restart_256": 0,
        "common_infinity_ansatz": 0,
    }
    reference_successes = 0
    reference_ops = []
    reference_times = []
    reference_trials = []
    attempts = 8
    for idx in range(attempts):
        inst = make_instance(seed=7000 + idx, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_degree_low_label_tie": _attack_outlier_degree(inst),
            "greedy_no_backtracking": _attack_greedy(inst),
            "random_restart_256": _attack_random_restart(inst, 90000 + idx),
            "common_infinity_ansatz": _attack_constant_coordinate(inst),
        }
        for name, candidate in candidates.items():
            if candidate is not None and verify(inst, candidate)[0]:
                attack_names[name] += 1
        started = time.perf_counter()
        candidate, stats = _reference_enumeration(inst)
        reference_times.append(time.perf_counter() - started)
        reference_ops.append(stats["operations"])
        reference_trials.append(stats["root_trials"])
        if candidate is not None and verify(inst, candidate)[0]:
            reference_successes += 1
    attacks = {
        name: {"successes": successes, "attempts": attempts}
        for name, successes in attack_names.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(v["successes"] == 0 for v in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exhaustive projective root-value propagation",
            "complexity": "O((p+1)(g+e)) exact projective transitions",
            "wall_clock_sec_mean": round(sum(reference_times) / attempts, 6),
            "wall_clock_sec_max": round(max(reference_times), 6),
            "operations_mean": round(sum(reference_ops) / attempts),
            "operations_max": max(reference_ops),
            "root_trials_mean": round(sum(reference_trials) / attempts),
            "root_trials_max": max(reference_trials),
            "solves": f"{reference_successes}/{attempts}, as expected",
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=8080, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(shipping),
        "base_modulus": shipping["p"],
        "doubled_modulus": doubled["p"],
        "base_search_space_bits": search_space(shipping).bit_length(),
        "doubled_search_space_bits": search_space(doubled).bit_length(),
        "answer_atomic_elements_both": _answer_atoms(shipping["answer"]),
    }

    invariant_checks = 0
    preserved_checks = 0
    for seed in range(20):
        inst = make_instance(seed=12000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        transformed, carried = _relabel_instance(inst, random.Random(50000 + seed))
        invariant_checks += 1
        if canonical_key(transformed) != key:
            raise AssertionError("canonical key changed under a composed relabelling")
        if verify(transformed, carried)[0]:
            preserved_checks += 1
    keys = set()
    distinct_draws = 0
    while len(keys) < 20 and distinct_draws < 100:
        inst = make_instance(
            seed=20000 + distinct_draws,
            **DIFFICULTY[SHIPPING_DIFFICULTY],
        )
        keys.add(canonical_key(inst))
        distinct_draws += 1
    report["G8_canonical_key"] = {
        "pass": (
            invariant_checks == 20 and preserved_checks == 20
            and len(keys) == 20
        ),
        "invariance_checks": invariant_checks,
        "real_transform_preserved_witness": preserved_checks,
        "unrelated_distinct_keys": len(keys),
        "unrelated_draws": distinct_draws,
        "canonical_duplicates_resampled": distinct_draws - len(keys),
        "canonicalization": "modulus plus exact unlabelled unicyclic topology code",
    }

    sizing_instances = [
        make_instance(seed=60000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for seed in range(20)
    ]
    blobs = [
        json.dumps(inst["answer"])
        for inst in sizing_instances
    ]
    answer_chars = max(map(len, blobs))
    answer_elements = _answer_atoms(shipping["answer"])
    answer_tokens = math.ceil(answer_chars / 4)
    intended_ops = max(
        _compact_holonomy_solver(inst)[1]["operations"]
        for inst in sizing_instances
    )
    arms = json.loads(json.dumps(G9_EVIDENCE))
    hinted = arms.get("hinted", {"solved": 0, "attempts": 0})
    placebo = arms.get("placebo", {"solved": 0, "attempts": 0})
    h_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    p_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300,
        "arms": {
            "bare": arms.get("bare", {"solved": 0, "attempts": 0}),
            "hinted": hinted,
            "placebo": placebo,
        },
        "hinted_minus_placebo": h_rate - p_rate,
        "hinted_verdict": arms.get("hinted_verdict", "not_run"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    # Keep the declarative profile synchronized with the measured shipping result.
    PROBLEM_PROFILE["max_answer_tokens"] = answer_tokens
    reference = report["G6_adversary_panel"]["reference_algorithm"]
    PROBLEM_PROFILE["hardness_basis"] = (
        "Track B: exhaustive projective root-value propagation is "
        f"O((p+1)(g+e)), measured at shipping at {reference['operations_mean']} "
        f"exact transitions and {reference['wall_clock_sec_mean']:.6f} seconds; "
        f"the shared-fixed-point route uses {intended_ops} exact operations."
    )

    report["instance_metrics"] = {
        "base_vertices": _base_vertex_count(shipping),
        "base_edges": _base_edge_count(shipping),
        "implicit_icwcol_vertices": _base_vertex_count(shipping) + 3 * _base_edge_count(shipping),
        "implicit_icwcol_edges": 4 * _base_edge_count(shipping),
    }
    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
