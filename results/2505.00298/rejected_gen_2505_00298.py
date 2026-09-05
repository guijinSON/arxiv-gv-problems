"""Verified problem generator for arXiv:2505.00298.

Yu and Sun's Theorem 2.6 maps Hypergraph 2-Coloring to the existence of
two internally-disjoint pendant Steiner out-trees in a symmetric digraph.
This module inverse-generates a balanced regular 3-uniform hypergraph after
sampling its coloring, presents the paper's exact digraph construction, and
uses the coloring as the proof's compact certificate for the two trees.

Only the Python standard library is used.  Importing this module performs no
I/O and prints nothing.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time
from collections import Counter


TRACK = "A"


_REDUCTION = (
    "Section 2.2, Theorem 2.6 (Hypergraph 2-Coloring to two internally-"
    "disjoint pendant (S,r)-trees in a symmetric digraph)"
)


PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "symmetric digraph specified by its vertex classes and arc rules",
        "terminal set and root",
        "two-colour set partition encoding two pendant Steiner out-trees",
    ],
    "verification_operations": [
        "exact set-partition checks",
        "exact hyperedge non-monochromaticity checks",
        "deterministic construction of the two directed trees",
        "exact indegree, reachability, terminal-degree, vertex-intersection, and arc-disjointness checks",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": _REDUCTION,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "View every edge-terminal as a not-all-equal constraint and propagate "
        "a forced colour whenever two vertices of an edge agree; without "
        "successful branching, the solver faces the full two-colour partition space."
    ),
    "hardness_basis": (
        "Rejected Track A candidate: although Theorem 2.6 proves NP-completeness "
        "for ell=2 fixed and k=|S| growing, a greedy/noisy WalkSAT attack solves "
        "all eight n=198, degree=6 audit instances in milliseconds; worst-case "
        "hardness therefore does not transfer to this planted distribution."
    ),
    "max_answer_tokens": 176,
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


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object {\"red\":[...],\"blue\":[...]} partitioning the "
        "1-based hypergraph vertices into two nonempty duplicate-free lists.  A "
        "candidate is valid when every 3-edge meets both lists.  Order inside a "
        "list is immaterial.  Global "
        "colour exchange is equivalent, so the bounded sampling language fixes "
        "vertex 1 red; verify accepts either orientation."
    ),
    "bounds": {
        "parts": 2,
        "total_vertex_entries": "n",
        "vertex_range": "1..n inclusive",
        "repetitions": 0,
        "canonical_colour_symmetry": "vertex 1 is red",
        "candidate_count": "2 ** (n - 1) - 1",
    },
}


DIFFICULTY = {
    "demo": {"n": 6, "degree": 2},
    "easy": {"n": 198, "degree": 6},
    "medium": {"n": 222, "degree": 6},
    "hard": {"n": 246, "degree": 6},
}


SHIPPING_DIFFICULTY = "easy"


STRUCTURAL_HINT = (
    "In a partial two-colouring, a hyperedge whose two fixed vertices have the "
    "same colour forces the colour of its third vertex."
)
PLACEBO_HINT = (
    "In this indexed construction, careful bookkeeping of every displayed "
    "vertex and hyperedge prevents transcription errors."
)


# Replaced with the harness-owned measurements after the three oracle runs.
G9_EVIDENCE = {
    "bare": {"solved": None, "attempts": 0, "errors": 4},
    "hinted": {"solved": None, "attempts": 0, "errors": 4},
    "placebo": {"solved": None, "attempts": 0, "errors": 4},
    "hinted_verdict": "unavailable",
}


NOTES = r"""
Section 1.2 fixes the exact object: a pendant (S,r)-tree is an out-tree rooted
at r containing S in which every terminal in S has total degree one; two such
trees are internally-disjoint when they share exactly S and share no arc.
Section 2.2 is decisive for complexity.  Theorem 2.3 makes symmetric instances
polynomial when both k and ell are fixed, by enumerating tree skeletons and
solving a fixed disjoint-paths problem.  This generator therefore does not use
that easy regime.  It uses Theorem 2.6: ell=2 is fixed, while k=|E(H)|+1 grows
with the 3-uniform hypergraph H, and deciding whether the two trees exist is
NP-complete.

The certificate-producing method is the forward direction of Theorem 2.6.
Generation samples a balanced colouring before it samples any hyperedge.  It
then creates a connected, simple, degree-regular 3-uniform hypergraph in which
half the edges contain one red vertex and half contain two.  The proof turns
each colour class into one out-tree: r enters a class anchor, the anchor reaches
the remaining class vertices through the variable clique, and one vertex of
that colour enters each edge-terminal.  Thus the certificate is known by
inverse generation and proof composition, never by running a solver.

Every vertex has the same hypergraph degree; both planted colour classes have
the same size; and the one-red/two-red edge types are balanced.  Those controls
remove simple degree, class-size, and clause-type signatures, but they do not
make the distribution hard.  A stronger construction-aware audit selects a
currently monochromatic edge and greedily flips the endpoint that minimizes the
new monochromatic-edge count, with occasional random noise.  It recovers a
valid colouring on every shipping audit seed in milliseconds.  Raising the
regular degree to 8, 10, or 12 at fixed answer length also gives 8/8 successes.
Theorem 2.6 is only a worst-case result, so this successful attack falsifies the
Track A distributional claim.  It does not become Track B: the local search is
the route that obtains the witness, while no substantially shorter invariant or
change of variables is present for a no-tool solver to exploit.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_DPLL_NODE_LIMIT = 4_000
_GUESS_SAMPLES = 200_000


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _normalise_params(n, degree):
    if not _is_int(n) or not _is_int(degree):
        raise TypeError("n and degree must be integers")
    if n < 6 or n % 2:
        raise ValueError("n must be an even integer at least 6")
    if degree < 2 or degree % 2:
        raise ValueError("degree must be a positive even integer")
    if (n * degree) % 6:
        raise ValueError("n*degree must be divisible by 6")
    return n, degree


def _connected_incidence(n, edges):
    adjacency = [set() for _ in range(n)]
    for edge in edges:
        for i in range(3):
            for j in range(i + 1, 3):
                u, v = edge[i], edge[j]
                adjacency[u].add(v)
                adjacency[v].add(u)
    seen = {0}
    stack = [0]
    while stack:
        vertex = stack.pop()
        for neighbor in adjacency[vertex]:
            if neighbor not in seen:
                seen.add(neighbor)
                stack.append(neighbor)
    return len(seen) == n


def _regular_planted_hypergraph(n, degree, colours, rng):
    """Sample a simple regular 3-graph with no monochromatic planted edge."""

    red_vertices = [i for i, colour in enumerate(colours) if colour == 0]
    blue_vertices = [i for i, colour in enumerate(colours) if colour == 1]
    if len(red_vertices) != len(blue_vertices):
        raise ValueError("the planted colouring must be balanced")

    edge_count = n * degree // 3
    if edge_count % 2:
        raise ValueError("the balanced edge-type construction needs even m")
    red_template = [v for v in red_vertices for _ in range(degree)]
    blue_template = [v for v in blue_vertices for _ in range(degree)]
    kinds_template = [1] * (edge_count // 2) + [2] * (edge_count // 2)

    for _ in range(30_000):
        red_pool = red_template[:]
        blue_pool = blue_template[:]
        kinds = kinds_template[:]
        rng.shuffle(red_pool)
        rng.shuffle(blue_pool)
        rng.shuffle(kinds)
        red_at = blue_at = 0
        edges = []
        signatures = set()
        failed = False
        for red_count in kinds:
            chosen = red_pool[red_at:red_at + red_count]
            chosen += blue_pool[blue_at:blue_at + 3 - red_count]
            red_at += red_count
            blue_at += 3 - red_count
            if len(chosen) != 3 or len(set(chosen)) != 3:
                failed = True
                break
            signature = tuple(sorted(chosen))
            if signature in signatures:
                failed = True
                break
            signatures.add(signature)
            edge = list(signature)
            rng.shuffle(edge)
            edges.append(edge)
        if not failed and _connected_incidence(n, edges):
            rng.shuffle(edges)
            return edges
    raise RuntimeError("could not construct a simple connected regular hypergraph")


def _partition_from_colours(colours):
    red = [i + 1 for i, colour in enumerate(colours) if colour == 0]
    blue = [i + 1 for i, colour in enumerate(colours) if colour == 1]
    return {"red": red, "blue": blue}


def _build_instance(n, degree, edges, colours):
    normalised = list(colours)
    if normalised[0] == 1:
        normalised = [1 - value for value in normalised]
    edge_count = len(edges)
    return {
        "paper": "arXiv:2505.00298v2",
        "family": "Theorem 2.6 hypergraph-colouring image in a symmetric digraph",
        "n": n,
        "degree": degree,
        "edge_count": edge_count,
        "edges": [list(edge) for edge in edges],
        "root": 0,
        "terminal_vertices": [0] + list(range(n + 1, n + edge_count + 1)),
        "digraph_vertex_count": n + edge_count + 1,
        "target_tree_count": 2,
        "answer": _partition_from_colours(normalised),
    }


def make_instance(n, seed=0, **params):
    """Inverse-generate the paper's symmetric digraph and two-tree witness."""

    degree = params.pop("degree", 6)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    n, degree = _normalise_params(n, degree)
    if not _is_int(seed):
        raise TypeError("seed must be an integer")
    rng = random.Random(seed)
    order = list(range(n))
    rng.shuffle(order)
    colours = [0] * n
    for vertex in order[n // 2:]:
        colours[vertex] = 1
    edges = _regular_planted_hypergraph(n, degree, colours, rng)
    return _build_instance(n, degree, edges, colours)


def _answer_text(answer):
    return json.dumps(answer, separators=(",", ":"), sort_keys=True)


def render(inst):
    """Return the complete solver-facing statement and exact output contract."""

    n = inst["n"]
    m = inst["edge_count"]
    lines = [
        "TWO INTERNALLY-DISJOINT PENDANT STEINER OUT-TREES",
        "",
        "A directed out-tree rooted at r is a directed tree in which r has",
        "indegree 0 and every other vertex has indegree 1.  The total degree of",
        "a vertex is its indegree plus outdegree.  For a terminal set S containing",
        "r, a pendant (S,r)-tree is an out-tree rooted at r that contains every",
        "vertex of S and gives every vertex of S total degree exactly 1.  Two such",
        "trees are internally-disjoint when they have no common arc and their",
        "common vertex set is exactly S.",
        "",
        f"The symmetric digraph D has root r, variable vertices v1,...,v{n},",
        f"and edge-terminal vertices e1,...,e{m}.  'Symmetric' means every",
        "listed adjacency supplies both directed arcs.  The following rules are",
        "the complete definition of D; there are no other arcs:",
        f"1. r is adjacent to every variable vertex v1,...,v{n}.",
        "2. Every two distinct variable vertices are adjacent.",
        "3. Variable vi is adjacent to terminal ej exactly when vi belongs to",
        "   hyperedge ej in the list below.",
        "4. No two edge-terminals are adjacent, and r is adjacent to no edge-terminal.",
        "",
        "The terminal set is S={r,e1,...,e%d}; r is the root." % m,
        "The target is a packing of exactly two internally-disjoint pendant",
        "(S,r)-trees.",
        "",
        "Use the following compact certificate from the construction of these",
        "trees.  Partition the 1-based variable indices into nonempty sets red",
        "and blue so that every displayed hyperedge contains at least one index",
        "of each colour.  The checker expands each colour class C into one tree:",
        "it uses the smallest index of C as its anchor, includes r->anchor and",
        "anchor->vi for every other vi in C, and for every ej includes vi->ej",
        "from the smallest-indexed member of C that lies in ej.  It then checks",
        "the resulting directed trees against D and the definition above.",
        "",
        "Hyperedges (the order of vertices within an edge is irrelevant):",
    ]
    for index, edge in enumerate(inst["edges"], 1):
        lines.append("e%d: %s" % (index, " ".join("v%d" % (v + 1) for v in edge)))
    lines.extend(
        [
            "",
            f"Return each integer 1,...,{n} exactly once across the two lists.",
            "List order is irrelevant, repeats are forbidden, and exchanging the",
            "names red and blue is allowed.  Indices are 1-based and bounds are inclusive.",
            "Give your final answer inside <answer></answer> tags, as one JSON object",
            'with exactly the keys "red" and "blue" and integer-array values.',
            'Example syntax: <answer>{"red":[1,3],"blue":[2,4]}</answer>',
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Parse a tagged JSON partition through prose and Markdown fences."""

    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.I | re.S)
    if fence:
        body = fence.group(1).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _decode_partition(inst, answer):
    if answer == {}:
        return None, "empty answer: expected red and blue parts"
    if not isinstance(answer, dict) or set(answer) != {"red", "blue"}:
        return None, 'malformed answer: expected exactly the keys "red" and "blue"'
    red = answer["red"]
    blue = answer["blue"]
    if not isinstance(red, list) or not isinstance(blue, list):
        return None, "malformed parts: red and blue must both be JSON arrays"
    if not red or not blue:
        return None, "empty colour class: both parts must be nonempty"
    entries = red + blue
    if any(not _is_int(value) for value in entries):
        return None, "non-integer vertex index in partition"
    n = inst["n"]
    if any(value < 1 or value > n for value in entries):
        return None, f"vertex index out of range: allowed range is 1..{n}"
    if len(set(red)) != len(red) or len(set(blue)) != len(blue):
        return None, "duplicate vertex inside a colour class"
    overlap = set(red) & set(blue)
    if overlap:
        return None, "red and blue overlap at a vertex"
    union = set(entries)
    if union != set(range(1, n + 1)):
        return None, "partition does not cover every variable vertex exactly once"
    colours = [-1] * n
    for value in red:
        colours[value - 1] = 0
    for value in blue:
        colours[value - 1] = 1
    return colours, "ok"


def _digraph_has_arc(inst, tail, head, incidence):
    if tail == head:
        return False
    n = inst["n"]
    if tail == 0:
        return 1 <= head <= n
    if head == 0:
        return 1 <= tail <= n
    tail_variable = 1 <= tail <= n
    head_variable = 1 <= head <= n
    if tail_variable and head_variable:
        return True
    if tail_variable and head > n:
        return tail - 1 in incidence[head - n - 1]
    if head_variable and tail > n:
        return head - 1 in incidence[tail - n - 1]
    return False


def _construct_trees(inst, colours):
    n = inst["n"]
    classes = [[i for i, value in enumerate(colours) if value == colour] for colour in (0, 1)]
    trees = []
    for vertices in classes:
        anchor = min(vertices)
        arcs = [(0, anchor + 1)]
        arcs.extend((anchor + 1, vertex + 1) for vertex in vertices if vertex != anchor)
        vertex_set = set(vertices)
        for edge_index, edge in enumerate(inst["edges"]):
            chosen = min(vertex_set & set(edge))
            arcs.append((chosen + 1, n + edge_index + 1))
        trees.append(arcs)
    return trees


def _check_one_tree(inst, arcs, incidence):
    if len(set(arcs)) != len(arcs):
        return False, "expanded tree repeats an arc"
    for tail, head in arcs:
        if not _digraph_has_arc(inst, tail, head, incidence):
            return False, "expanded tree uses an arc absent from D"
    vertices = {0}
    for tail, head in arcs:
        vertices.add(tail)
        vertices.add(head)
    terminals = set(inst["terminal_vertices"])
    if not terminals <= vertices:
        return False, "expanded tree omits a terminal"
    indegree = Counter()
    outdegree = Counter()
    adjacency = {}
    for tail, head in arcs:
        indegree[head] += 1
        outdegree[tail] += 1
        adjacency.setdefault(tail, []).append(head)
    if indegree[0] != 0:
        return False, "root has positive indegree in expanded tree"
    if any(indegree[vertex] != 1 for vertex in vertices if vertex != 0):
        return False, "a non-root vertex lacks unique parent in expanded tree"
    reached = {0}
    stack = [0]
    while stack:
        vertex = stack.pop()
        for neighbor in adjacency.get(vertex, ()):
            if neighbor not in reached:
                reached.add(neighbor)
                stack.append(neighbor)
    if reached != vertices or len(arcs) != len(vertices) - 1:
        return False, "expanded arcs do not form one out-tree rooted at r"
    for terminal in terminals:
        if indegree[terminal] + outdegree[terminal] != 1:
            return False, "a terminal does not have total degree one"
    return True, "ok"


def verify(inst, answer):
    """Check any valid colour certificate and its exact expanded tree packing."""

    colours, reason = _decode_partition(inst, answer)
    if colours is None:
        return False, reason
    for edge_index, edge in enumerate(inst["edges"], 1):
        values = {colours[vertex] for vertex in edge}
        if len(values) != 2:
            return False, f"monochromatic hyperedge e{edge_index}"
    try:
        trees = _construct_trees(inst, colours)
    except (ValueError, KeyError, IndexError, TypeError):
        return False, "could not expand partition into two trees"
    incidence = [set(edge) for edge in inst["edges"]]
    for index, tree in enumerate(trees, 1):
        ok, tree_reason = _check_one_tree(inst, tree, incidence)
        if not ok:
            return False, f"tree {index}: {tree_reason}"
    arc_sets = [set(tree) for tree in trees]
    if arc_sets[0] & arc_sets[1]:
        return False, "expanded trees share an arc"
    vertex_sets = []
    for tree in trees:
        vertices = {0}
        for tail, head in tree:
            vertices.add(tail)
            vertices.add(head)
        vertex_sets.append(vertices)
    if vertex_sets[0] & vertex_sets[1] != set(inst["terminal_vertices"]):
        return False, "expanded trees share a nonterminal or omit a common terminal"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the canonical two-partition space modulo colour swap."""

    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    while True:
        colours = [0] + [rng.randrange(2) for _ in range(inst["n"] - 1)]
        if any(colours):
            break
    return _partition_from_colours(colours)


def search_space(inst):
    return (1 << (inst["n"] - 1)) - 1


def enumerate_all(inst):
    """Count proper colourings modulo global exchange for small instances."""

    n = inst["n"]
    if n > 24:
        return None
    total = 0
    for mask in range(1, 1 << (n - 1)):
        colours = [0] + [(mask >> (i - 1)) & 1 for i in range(1, n)]
        if all(len({colours[v] for v in edge}) == 2 for edge in inst["edges"]):
            total += 1
    return total


def _rooted_wl_signature(inst, root):
    """A strong relabelling invariant of the vertex-edge incidence graph."""

    n = inst["n"]
    m = inst["edge_count"]
    adjacency = [[] for _ in range(n + m)]
    for edge_index, edge in enumerate(inst["edges"]):
        edge_node = n + edge_index
        for vertex in edge:
            adjacency[vertex].append(edge_node)
            adjacency[edge_node].append(vertex)
    colours = [0] * n + [1] * m
    colours[root] = 2
    history = []
    for _ in range(10):
        signatures = [
            (colours[index], tuple(sorted(colours[neighbor] for neighbor in adjacency[index])))
            for index in range(n + m)
        ]
        palette = {signature: code for code, signature in enumerate(sorted(set(signatures)))}
        new_colours = [palette[signature] for signature in signatures]
        history.append((new_colours[root], tuple(sorted(Counter(new_colours).items()))))
        colours = new_colours
    return tuple(history)


def canonical_key(inst):
    """Hash a rooted-WL deck invariant under all vertex/edge reorderings."""

    rooted_deck = sorted(_rooted_wl_signature(inst, root) for root in range(inst["n"]))
    payload = {
        "n": inst["n"],
        "m": inst["edge_count"],
        "degree": inst["degree"],
        "rooted_wl_deck": rooted_deck,
    }
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params):
    """Increase the vertex haystack while the certificate stays under 256 atoms."""

    current = dict(params)
    n = int(current.get("n", 0))
    degree = int(current.get("degree", 6))
    if n < 256:
        next_n = min(256, n + 24)
        if next_n % 2:
            next_n += 1
        return {"n": next_n, "degree": degree}
    return "cap_bound"


def _candidate_if_valid(inst, colours):
    if colours is None:
        return None
    answer = _partition_from_colours(colours)
    return answer if verify(inst, answer)[0] else None


def _bad_edges(inst, colours):
    return {
        index
        for index, edge in enumerate(inst["edges"])
        if colours[edge[0]] == colours[edge[1]] == colours[edge[2]]
    }


def _occurrences(inst):
    result = [[] for _ in range(inst["n"])]
    for edge_index, edge in enumerate(inst["edges"]):
        for vertex in edge:
            result[vertex].append(edge_index)
    return result


def _attack_outlier(inst, rng):
    del rng
    n = inst["n"]
    co = [Counter() for _ in range(n)]
    for edge in inst["edges"]:
        for i in range(3):
            for j in range(i + 1, 3):
                u, v = edge[i], edge[j]
                co[u][v] += 1
                co[v][u] += 1
    scores = [sum(value * value for value in row.values()) for row in co]
    ordered = sorted(range(n), key=lambda vertex: (scores[vertex], vertex))
    colours = [1] * n
    for vertex in ordered[: n // 2]:
        colours[vertex] = 0
    if colours[0]:
        colours = [1 - value for value in colours]
    return _candidate_if_valid(inst, colours)


def _attack_greedy(inst, rng):
    del rng
    n = inst["n"]
    occurrences = _occurrences(inst)
    colours = [-1] * n
    colours[0] = 0
    for vertex in range(1, n):
        scores = []
        for choice in (0, 1):
            colours[vertex] = choice
            monochromatic = 0
            forced_risk = 0
            for edge_index in occurrences[vertex]:
                edge = inst["edges"][edge_index]
                assigned = [colours[v] for v in edge if colours[v] >= 0]
                if len(assigned) == 3 and assigned[0] == assigned[1] == assigned[2]:
                    monochromatic += 1
                elif len(assigned) == 2 and assigned[0] == assigned[1]:
                    forced_risk += 1
            scores.append((monochromatic, forced_risk, choice))
        colours[vertex] = min(scores)[2]
    return _candidate_if_valid(inst, colours)


def _attack_random_restart(inst, rng, restarts=256):
    n = inst["n"]
    occurrences = _occurrences(inst)
    checks = 0
    for _ in range(restarts):
        colours = [0] + [rng.randrange(2) for _ in range(n - 1)]
        bad = _bad_edges(inst, colours)
        for _ in range(4 * n):
            checks += 1
            if not bad:
                return _candidate_if_valid(inst, colours), checks
            edge_index = rng.choice(tuple(bad))
            vertex = rng.choice(inst["edges"][edge_index])
            colours[vertex] ^= 1
            for affected in occurrences[vertex]:
                edge = inst["edges"][affected]
                if colours[edge[0]] == colours[edge[1]] == colours[edge[2]]:
                    bad.add(affected)
                else:
                    bad.discard(affected)
    return None, checks


def _attack_walksat(inst, rng, restarts=128, steps_factor=10, noise=0.25):
    """Greedy/noisy NAE-WalkSAT; this attack falsifies the Track A claim."""

    n = inst["n"]
    occurrences = _occurrences(inst)
    stats = {
        "restarts_budget": restarts,
        "steps_per_restart": steps_factor * n,
        "restarts_used": 0,
        "flips": 0,
        "edge_inspections": 0,
    }
    for restart in range(restarts):
        stats["restarts_used"] = restart + 1
        colours = [0] + [rng.randrange(2) for _ in range(n - 1)]
        bad = _bad_edges(inst, colours)
        stats["edge_inspections"] += len(inst["edges"])
        for _ in range(steps_factor * n):
            if not bad:
                return _candidate_if_valid(inst, colours), stats
            edge_index = rng.choice(tuple(bad))
            edge = inst["edges"][edge_index]
            if rng.random() < noise:
                vertex = rng.choice(edge)
            else:
                scored = []
                for candidate in edge:
                    delta = 0
                    for affected in occurrences[candidate]:
                        affected_edge = inst["edges"][affected]
                        before = (
                            colours[affected_edge[0]]
                            == colours[affected_edge[1]]
                            == colours[affected_edge[2]]
                        )
                        colours[candidate] ^= 1
                        after = (
                            colours[affected_edge[0]]
                            == colours[affected_edge[1]]
                            == colours[affected_edge[2]]
                        )
                        colours[candidate] ^= 1
                        delta += int(after) - int(before)
                        stats["edge_inspections"] += 1
                    scored.append((delta, rng.random(), candidate))
                vertex = min(scored)[2]
            colours[vertex] ^= 1
            stats["flips"] += 1
            for affected in occurrences[vertex]:
                affected_edge = inst["edges"][affected]
                stats["edge_inspections"] += 1
                if (
                    colours[affected_edge[0]]
                    == colours[affected_edge[1]]
                    == colours[affected_edge[2]]
                ):
                    bad.add(affected)
                else:
                    bad.discard(affected)
    return None, stats


def _attack_spectral(inst, rng):
    n = inst["n"]
    pairs = Counter()
    for edge in inst["edges"]:
        for i in range(3):
            for j in range(i + 1, 3):
                u, v = sorted((edge[i], edge[j]))
                pairs[(u, v)] += 1
    shift = 2 * inst["degree"] + 1.0
    vector = [rng.uniform(-1.0, 1.0) for _ in range(n)]
    for _ in range(100):
        nxt = [shift * value for value in vector]
        for (u, v), weight in pairs.items():
            nxt[u] -= weight * vector[v]
            nxt[v] -= weight * vector[u]
        norm = math.sqrt(sum(value * value for value in nxt)) or 1.0
        vector = [value / norm for value in nxt]
    base = [int(value >= 0.0) for value in vector]
    for colours in (base, [1 - value for value in base]):
        candidate = _candidate_if_valid(inst, colours)
        if candidate is not None:
            return candidate
    return None


class _DPLLLimit(Exception):
    pass


def _nae_propagate(edges, colours, stats):
    changed = True
    while changed:
        changed = False
        for edge in edges:
            stats["edge_inspections"] += 1
            known = [colours[v] for v in edge if colours[v] >= 0]
            unknown = [v for v in edge if colours[v] < 0]
            if not unknown:
                if known[0] == known[1] == known[2]:
                    return False
            elif len(unknown) == 1 and known[0] == known[1]:
                vertex = unknown[0]
                needed = 1 - known[0]
                if colours[vertex] >= 0 and colours[vertex] != needed:
                    return False
                if colours[vertex] < 0:
                    colours[vertex] = needed
                    stats["propagations"] += 1
                    changed = True
    return True


def _dpll_search(inst, node_limit=_DPLL_NODE_LIMIT):
    occurrence_count = [0] * inst["n"]
    for edge in inst["edges"]:
        for vertex in edge:
            occurrence_count[vertex] += 1
    stats = {
        "nodes": 0,
        "node_limit": node_limit,
        "edge_inspections": 0,
        "propagations": 0,
        "limit_reached": False,
    }

    def solve(colours):
        stats["nodes"] += 1
        if stats["nodes"] > node_limit:
            raise _DPLLLimit
        colours = colours[:]
        if not _nae_propagate(inst["edges"], colours, stats):
            return None
        if all(value >= 0 for value in colours):
            return colours
        unassigned = [i for i, value in enumerate(colours) if value < 0]
        vertex = max(unassigned, key=lambda i: (occurrence_count[i], -i))
        for choice in (0, 1):
            child = colours[:]
            child[vertex] = choice
            result = solve(child)
            if result is not None:
                return result
        return None

    initial = [-1] * inst["n"]
    initial[0] = 0
    try:
        result = solve(initial)
    except _DPLLLimit:
        result = None
        stats["limit_reached"] = True
    return _candidate_if_valid(inst, result), stats


def _run_attacks(params, seeds):
    attack_functions = {
        "outlier_local_cooccurrence": lambda inst, rng: _attack_outlier(inst, rng),
        "greedy_left_to_right": lambda inst, rng: _attack_greedy(inst, rng),
        "random_restart_min_conflicts_256": lambda inst, rng: _attack_random_restart(inst, rng, 256)[0],
        "walksat_greedy_noise_128": lambda inst, rng: _attack_walksat(inst, rng, 128)[0],
        "spectral_pair_relaxation": lambda inst, rng: _attack_spectral(inst, rng),
        "nae_dpll_unit_propagation_4000": lambda inst, rng: _dpll_search(inst)[0],
    }
    instances = [(seed, make_instance(seed=seed, **params)) for seed in seeds]
    report = {}
    for name, attack in attack_functions.items():
        successes = 0
        outcomes = []
        for seed, inst in instances:
            candidate = attack(inst, random.Random(900_000 + seed))
            if candidate is None:
                outcomes.append("no candidate")
                continue
            ok, reason = verify(inst, candidate)
            successes += int(ok)
            outcomes.append(reason)
        report[name] = {
            "successes": successes,
            "attempts": len(seeds),
            "results": outcomes,
        }
    return report


def _transform_instance(inst, rng):
    n = inst["n"]
    permutation = list(range(n))
    rng.shuffle(permutation)
    transformed_edges = []
    for edge in inst["edges"]:
        transformed = [permutation[vertex] for vertex in edge]
        rng.shuffle(transformed)
        transformed_edges.append(transformed)
    rng.shuffle(transformed_edges)
    colours, reason = _decode_partition(inst, inst["answer"])
    if colours is None:
        raise AssertionError(reason)
    carried = [0] * n
    for old_vertex, new_vertex in enumerate(permutation):
        carried[new_vertex] = colours[old_vertex]
    transformed = _build_instance(n, inst["degree"], transformed_edges, carried)
    return transformed, _partition_from_colours(carried)


def _answer_atoms(answer):
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def _monochromatic_swap_corruption(inst):
    colours, reason = _decode_partition(inst, inst["answer"])
    if colours is None:
        raise AssertionError(reason)
    for edge in inst["edges"]:
        counts = Counter(colours[v] for v in edge)
        minority = 0 if counts[0] == 1 else 1
        minority_vertex = next(v for v in edge if colours[v] == minority)
        outside = next(
            v for v in range(inst["n"])
            if v not in edge and colours[v] == 1 - minority
        )
        changed = colours[:]
        changed[minority_vertex], changed[outside] = changed[outside], changed[minority_vertex]
        answer = _partition_from_colours(changed)
        if not verify(inst, answer)[0]:
            return answer
    raise AssertionError("could not make swap corruption")


def selftest():
    """Run every mandatory generation, grading, attack, and scaling gate."""

    report = {
        "paper": "2505.00298",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    g1_rows = {}
    g1_pass = True
    for preset, params in DIFFICULTY.items():
        rows = []
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            json_native = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            rows.append({"seed": seed, "verified": ok, "reason": reason, "json": json_native})
            g1_pass &= ok and json_native
        g1_rows[preset] = rows
    report["G1_planted_verifies"] = {"pass": g1_pass, "presets": g1_rows}

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=12_345, **shipping_params)
    answer = {key: list(value) for key, value in inst["answer"].items()}
    drop = {key: list(value) for key, value in answer.items()}
    drop_key = "red" if len(drop["red"]) > 1 else "blue"
    drop[drop_key].pop()
    duplicate = {key: list(value) for key, value in answer.items()}
    duplicate["blue"].append(duplicate["red"][0])
    out_of_range = {key: list(value) for key, value in answer.items()}
    out_of_range["red"][0] = inst["n"] + 1
    corruptions = {
        "drop_one": drop,
        "swap_between_parts": _monochromatic_swap_corruption(inst),
        "duplicate_across_parts": duplicate,
        "empty": {},
        "out_of_range": out_of_range,
    }
    corruption_rows = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_rows[name] = {"accepted": ok, "reason": reason}
    reasons = [row["reason"] for row in corruption_rows.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not row["accepted"] for row in corruption_rows.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_rows,
        "distinct_reasons": len(set(reasons)),
    }

    model_response = (
        "The edge-terminals are bichromatic, so the construction gives both trees.\n\n"
        "<answer>\n```json\n"
        + _answer_text(inst["answer"])
        + "\n```\n</answer>\nThis is the requested partition."
    )
    parsed = parse_answer(model_response)
    parsed_ok, parsed_reason = verify(inst, parsed)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and parsed_ok,
        "verify_reason": parsed_reason,
        "surrounding_prose_and_fence": True,
    }

    guess_rng = random.Random(991_337)
    hits = 0
    for _ in range(_GUESS_SAMPLES):
        hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    measured_density = hits / _GUESS_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": _GUESS_SAMPLES >= 200_000 and measured_density < 1e-6,
        "hits": hits,
        "total": _GUESS_SAMPLES,
        "measured_probability": measured_density,
        "candidate_space": search_space(inst),
        "sampler": "uniform over all n-bit partitions after quotienting global colour exchange",
    }

    baseline_started = time.perf_counter()
    baseline_candidate, baseline_stats = _attack_walksat(
        inst, random.Random(812_881), restarts=128
    )
    baseline_seconds = time.perf_counter() - baseline_started
    baseline_solved = baseline_candidate is not None and verify(inst, baseline_candidate)[0]
    demo = make_instance(seed=77, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": measured_density < 1e-6 and not baseline_solved and demo_count is not None,
        "shipping_density_hits": hits,
        "shipping_density_samples": _GUESS_SAMPLES,
        "shipping_solution_fraction_estimate": measured_density,
        "shipping_baseline": "greedy/noisy NAE-WalkSAT with 128 restarts",
        "shipping_baseline_wall_clock_sec": round(baseline_seconds, 6),
        "shipping_baseline_solved": baseline_solved,
        **baseline_stats,
        "demo_exact_valid_answer_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "demo_exact_solution_fraction": demo_count / search_space(demo),
    }

    attacks = _run_attacks(shipping_params, list(range(800, 808)))
    report["G6_adversary_panel"] = {
        "pass": all(row["successes"] == 0 for row in attacks.values()),
        "attacks": attacks,
        "standard_algorithm": (
            "DPLL on the two monotone 3-CNF clauses equivalent to each NAE "
            "hyperedge, implemented directly with forced-third-vertex propagation; "
            "the panel also records the successful construction-aware WalkSAT attack"
        ),
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled_started = time.perf_counter()
    doubled = make_instance(seed=54_321, **doubled_params)
    doubled_seconds = time.perf_counter() - doubled_started
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and search_space(doubled) > search_space(inst),
        "base_n": inst["n"],
        "doubled_n": doubled["n"],
        "base_candidate_space": search_space(inst),
        "doubled_candidate_space": search_space(doubled),
        "doubled_build_sec": round(doubled_seconds, 6),
        "verify_reason": doubled_reason,
    }

    invariant_checks = 0
    carried_checks = 0
    invariant_failures = []
    for seed in range(20):
        base = make_instance(n=30, degree=4, seed=10_000 + seed)
        key = canonical_key(base)
        transformed, carried = _transform_instance(base, random.Random(20_000 + seed))
        if canonical_key(transformed) != key:
            invariant_failures.append(seed)
        invariant_checks += 1
        ok, _ = verify(transformed, carried)
        carried_checks += int(ok)
        composed, carried_again = _transform_instance(transformed, random.Random(30_000 + seed))
        if canonical_key(composed) != key:
            invariant_failures.append(f"composed-{seed}")
        invariant_checks += 1
        ok, _ = verify(composed, carried_again)
        carried_checks += int(ok)
    unrelated_keys = {
        canonical_key(make_instance(n=30, degree=4, seed=40_000 + seed))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and carried_checks == 40 and len(unrelated_keys) == 20,
        "invariance_checks": invariant_checks,
        "invariance_failures": invariant_failures,
        "real_transformation_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "unrelated_distinct_keys": len(unrelated_keys),
        "invariant": "ten-round rooted Weisfeiler-Leman deck of the incidence graph",
        "complete_isomorphism_canonizer": False,
    }

    answer_chars = max(
        len(_answer_text(make_instance(seed=seed, **shipping_params)["answer"]))
        for seed in range(64)
    )
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    intended_operations = inst["n"]
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    arms = {name: dict(G9_EVIDENCE[name]) for name in ("bare", "hinted", "placebo")}
    hinted_solved = arms["hinted"]["solved"]
    placebo_solved = arms["placebo"]["solved"]
    hinted_minus_placebo = (
        None
        if hinted_solved is None or placebo_solved is None
        else hinted_solved / max(1, arms["hinted"]["attempts"])
        - placebo_solved / max(1, arms["placebo"]["attempts"])
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "diagnostic_recorded_not_gated": True,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [
        value
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    ]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
