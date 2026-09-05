"""Verified balanced K_{2,3} induced-minor certificate generator.

The paper's native witness is a collection of connected branch sets.  In this
family deleting three planted subdivision vertices leaves two equally large
connected components.  Those components, together with the three singleton
deleted vertices, are returned as a full spanning induced-minor model of K_{2,3}.

Generation never searches for the separator.  It first joins two copies of a
regular graph fragment by three edges, remembers those edges, subdivides every
edge, and finally applies a random vertex relabelling.  A successful standard
min-cut algorithm is reported separately because this is deliberately Track B.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import statistics
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # The family uses only exact integer graph operations.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite simple graph given as a full edge-subdivision table",
        "spanning induced-minor branch-set model of K_{2,3}",
        "balanced independent three-vertex separator",
    ],
    "verification_operations": [
        "exact graph degree checks",
        "breadth-first connected-component computation",
        "exact adjacency and cardinality comparisons",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "duality",
    "intuition_description": (
        "Suppressing the degree-two vertices exposes a regular core whose unique "
        "balanced three-edge cut is dual to the requested three singleton branch "
        "sets; without that cut viewpoint one must search triples of subdivision vertices."
    ),
    "hardness_basis": (
        "Track B: Theorem 6.10 detects K_{2,3} induced minors in "
        "O(N^13(N+M)) time and Lemma 3.2 turns decision into finding; on this "
        "subdivision distribution, the stronger Stoer-Wagner global-min-cut "
        "reference runs in O(c^3) on the c-vertex core and at the shipping preset "
        "uses about 6,700 counted operations in under 0.1 seconds, whereas the "
        "compact cut-duality route inspects 75 subdivision rows once (under 300 "
        "exact comparisons) and the bare no-tool oracle must discover that route."
    ),
    "max_answer_tokens": 107,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}


# n is the number of degree-two subdivision vertices: the candidate haystack.
# The answer always contains exactly three vertex identifiers.
DIFFICULTY = {
    "demo": {"n": 9, "degree": 3},
    "easy": {"n": 75, "degree": 5},
    "medium": {"n": 105, "degree": 5},
    "hard": {"n": 115, "degree": 5},
}

SHIPPING_DIFFICULTY = "easy"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON array [BU,BV,BA,BB,BC] of five sorted integer lists that partition "
        "all vertices: BU and BV have the displayed equal size, BA,BB,BC are "
        "singletons, BU precedes BV by minimum vertex, and the singleton vertices "
        "increase from BA through BC."
    ),
    "bounds": {
        "branch_sets": 5,
        "total_vertex_entries": "number of graph vertices",
        "entry_range": "0 <= vertex < number of graph vertices",
        "large_branch_size": "(number of graph vertices - 3)/2",
        "singleton_candidates": "the n displayed subdivision vertices",
        "shipping_subdivision_candidates": 75,
    },
}

STRUCTURAL_HINT = (
    "The suppressed regular core has an involution exchanging two equal halves across its unique three-edge cut."
)
PLACEBO_HINT = (
    "The displayed regular core has uniform notation whose many subdivision rows reward careful bookkeeping."
)

# Filled from script-owned runs after hardening.  These diagnostics never gate
# G9(c), whose caps are checked independently.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 3, "attempts": 3},
    "hinted": {"solved": 3, "attempts": 3},
    "placebo": {"solved": 3, "attempts": 3},
    "hinted_verdict": "too_easy",
}

NOTES = """\
Section 2.2, especially the definition at lines corresponding to items in the
induced-minor model definition, fixes the witness: pairwise-disjoint nonempty
connected branch sets, with an edge between two sets if and only if their target
vertices are adjacent.  Section 6 specializes to K_{2,3}.  Theorem 6.2 gives the
Truemper-configuration characterization, and Theorem 6.10 gives the explicit
O(n^13(n+m)) decision algorithm.  Section 3, Lemma 3.2, says how polynomial-time
decision yields an actual minimal model.  Corollary 5.4 is the decisive easy-case
warning: K_{2,q}, hence K_{2,3}, has a polynomial-time finding algorithm on all
graphs.  A Track A claim would therefore be false.

The construction starts from an odd-degree regular graph, deletes one vertex,
repairs all but three of its deficient neighbors, duplicates the resulting
fragment, and joins corresponding remaining ports.  The remembered three join
edges are a balanced cut by construction.  Every core edge is subdivided once,
so the three cut vertices have exactly the same degree and endpoint-degree
profile as all decoys.  Deleting them produces two equal connected components;
these are the two degree-three branch sets of K_{2,3}, while the deleted vertices
are its degree-two singleton branch sets.

The per-edge local-signature outlier, first-row, largest-numeric-span,
evenly-spaced-row, and 256-restart triple attacks are tested over eight seeds.
Random relabelling defeats identifier-based rules, and regularity makes every
subdivision vertex locally degree-identical.  The exact Stoer-Wagner min-cut
algorithm is intentionally successful and is reported as the Track-B reference,
not misreported as a failing attack.
"""


_TAG_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 500_000


def _validate_params(n, degree):
    if isinstance(n, bool) or not isinstance(n, int) or n < 9:
        raise ValueError("n must be an integer at least 9")
    if isinstance(degree, bool) or not isinstance(degree, int):
        raise ValueError("degree must be an odd integer at least 3")
    if degree < 3 or degree % 2 == 0:
        raise ValueError("degree must be an odd integer at least 3")
    if n % degree:
        raise ValueError("n must be divisible by degree")
    half_order = n // degree
    if half_order % 2 != 1:
        raise ValueError("n/degree must be odd")
    base_order = half_order + 1
    if base_order < max(4, 2 * ((degree - 1) // 2) + 2):
        raise ValueError("n is too small for this degree")


def _allowed_perfect_matching(order, radius, rng):
    """A random perfect matching avoiding the circulant edges."""
    vertices = list(range(order))
    for _ in range(10_000):
        rng.shuffle(vertices)
        pairs = []
        ok = True
        for i in range(0, order, 2):
            a, b = vertices[i], vertices[i + 1]
            dist = min((a - b) % order, (b - a) % order)
            if dist <= radius:
                ok = False
                break
            pairs.append((min(a, b), max(a, b)))
        if ok:
            return pairs
    raise RuntimeError("could not sample an allowed perfect matching")


def _repair_pairs(neighbors, existing_edges, count, rng):
    """Pair 2*count neighbors by currently absent edges, leaving three ports."""
    if count == 0:
        return []
    choices = [
        (a, b) for a, b in itertools.combinations(neighbors, 2)
        if (min(a, b), max(a, b)) not in existing_edges
    ]
    rng.shuffle(choices)

    def rec(start, used, selected):
        if len(selected) == count:
            return list(selected)
        for index in range(start, len(choices)):
            a, b = choices[index]
            if a in used or b in used:
                continue
            answer = rec(index + 1, used | {a, b}, selected + [(a, b)])
            if answer is not None:
                return answer
        return None

    return rec(0, set(), [])


def _stoer_wagner(vertices, edges):
    """Exact global min cut; return (weight, one shore, counted operations)."""
    verts = list(sorted(vertices))
    weights = {v: {} for v in verts}
    for a, b in edges:
        weights[a][b] = weights[a].get(b, 0) + 1
        weights[b][a] = weights[b].get(a, 0) + 1
    groups = {v: {v} for v in verts}
    best_weight = math.inf
    best_shore = set()
    operations = 0

    while len(verts) > 1:
        used = set()
        connection = {v: 0 for v in verts}
        previous = None
        for phase_index in range(len(verts)):
            candidates = [v for v in verts if v not in used]
            selected = candidates[0]
            for v in candidates[1:]:
                operations += 1
                if (connection[v], -v) > (connection[selected], -selected):
                    selected = v
            used.add(selected)
            if phase_index == len(verts) - 1:
                cut_weight = connection[selected]
                shore = set(groups[selected])
                # Prefer the more balanced shore on a tie.  The shipping
                # construction has a unique weight-three cut, but this also
                # makes the demo's output deterministic.
                old_balance = min(len(best_shore), len(vertices) - len(best_shore))
                new_balance = min(len(shore), len(vertices) - len(shore))
                if (cut_weight < best_weight or
                        (cut_weight == best_weight and new_balance > old_balance)):
                    best_weight = cut_weight
                    best_shore = shore
                if previous is None:
                    break
                for neighbor, weight in list(weights[selected].items()):
                    operations += 1
                    if neighbor == previous or neighbor not in weights:
                        continue
                    weights[previous][neighbor] = weights[previous].get(neighbor, 0) + weight
                    weights[neighbor][previous] = weights[neighbor].get(previous, 0) + weight
                    weights[neighbor].pop(selected, None)
                weights[previous].pop(selected, None)
                groups[previous].update(groups[selected])
                del groups[selected]
                del weights[selected]
                verts.remove(selected)
                break
            previous = selected
            for neighbor, weight in weights[selected].items():
                operations += 1
                if neighbor not in used:
                    connection[neighbor] += weight
    return int(best_weight), best_shore, operations


def _unlabelled_core(n, degree, rng):
    """Return a regular core and the three planted cut edges."""
    half_order = n // degree
    base_order = half_order + 1
    radius = (degree - 1) // 2

    for _ in range(2_000):
        edges = set()
        for v in range(base_order):
            for delta in range(1, radius + 1):
                w = (v + delta) % base_order
                edges.add((min(v, w), max(v, w)))
        edges.update(_allowed_perfect_matching(base_order, radius, rng))
        root = rng.randrange(base_order)
        neighbors = sorted(
            b if a == root else a
            for a, b in edges if a == root or b == root
        )
        repairs = _repair_pairs(
            neighbors, edges, (degree - 3) // 2, rng
        )
        if repairs is None:
            continue
        repaired = {x for pair in repairs for x in pair}
        ports = [v for v in neighbors if v not in repaired]
        if len(ports) != 3:
            continue

        surviving = [v for v in range(base_order) if v != root]
        position = {v: i for i, v in enumerate(surviving)}
        fragment_edges = {
            (position[a], position[b])
            for a, b in edges if a != root and b != root
        }
        fragment_edges.update(
            (min(position[a], position[b]), max(position[a], position[b]))
            for a, b in repairs
        )
        h = half_order
        core_edges = set(fragment_edges)
        core_edges.update((a + h, b + h) for a, b in fragment_edges)
        central = {
            (position[p], position[p] + h) for p in ports
        }
        core_edges.update(central)
        vertices = set(range(2 * h))
        if len(core_edges) != n:
            continue
        degrees = {v: 0 for v in vertices}
        for a, b in core_edges:
            degrees[a] += 1
            degrees[b] += 1
        if set(degrees.values()) != {degree}:
            continue

        # For degrees above three, make the remembered cut the cut returned by
        # the independent exact reference algorithm.  The certificate itself
        # was already known before this check; the check only removes accidental
        # easier cores with a competing smaller cut.
        if degree > 3:
            weight, shore, _ = _stoer_wagner(vertices, core_edges)
            crossing = {
                (min(a, b), max(a, b)) for a, b in core_edges
                if (a in shore) != (b in shore)
            }
            if weight != 3 or crossing != central:
                continue
        return sorted(core_edges), central
    raise RuntimeError("could not construct a core with the required unique cut")


def make_instance(n, seed=0, degree=5, **params):
    """Inverse-generate a balanced spanning K_{2,3} induced-minor instance."""
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_params(n, degree)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    core_count = 2 * (n // degree)
    total_vertices = core_count + n
    side_size = (total_vertices - 3) // 2

    # A few cores have a genuinely rare radius-one signature on all three cut
    # edges.  Reject those, and also randomize away an identifier tie that lets
    # the declared local-outlier probe win.  The separator is already known;
    # this filtering never discovers it by solving the output instance.
    for _ in range(100):
        core_edges, central_edges = _unlabelled_core(n, degree, rng)
        for _ in range(100):
            labels = list(range(total_vertices))
            rng.shuffle(labels)
            relabel = {old: labels[old] for old in range(total_vertices)}
            rows = []
            central_subdividers = []
            for index, (a, b) in enumerate(core_edges):
                subdivision = core_count + index
                row = [relabel[subdivision], relabel[a], relabel[b]]
                row[1:] = sorted(row[1:])
                rows.append(row)
                if (a, b) in central_edges:
                    central_subdividers.append(relabel[subdivision])
            rows.sort(key=lambda row: row[0])
            left = {relabel[v] for v in range(n // degree)}
            right = {
                relabel[v] for v in range(n // degree, 2 * (n // degree))
            }
            for index, (a, b) in enumerate(core_edges):
                subdivision = relabel[core_count + index]
                if (a, b) in central_edges:
                    continue
                if a < n // degree and b < n // degree:
                    left.add(subdivision)
                elif a >= n // degree and b >= n // degree:
                    right.add(subdivision)
                else:
                    raise RuntimeError("a noncentral edge crosses the planted shores")
            large = sorted((sorted(left), sorted(right)), key=lambda branch: branch[0])
            singleton_branches = [[v] for v in sorted(central_subdividers)]
            candidate = {
                "family": "balanced_spanning_K23_induced_minor",
                "n_vertices": total_vertices,
                "core_degree": degree,
                "core_vertices": sorted(relabel[v] for v in range(core_count)),
                "subdivisions": rows,
                "required_side_size": side_size,
                "answer": large + singleton_branches,
            }
            if (degree == 3 or
                    _attack_local_signature(candidate) != sorted(central_subdividers)):
                return candidate
    raise RuntimeError("could not defeat the declared local-signature outlier")


def _adjacency(inst):
    total = inst.get("n_vertices")
    if isinstance(total, bool) or not isinstance(total, int) or total < 1:
        return None
    adjacency = [set() for _ in range(total)]
    try:
        for subdivision, a, b in inst["subdivisions"]:
            if not all(isinstance(x, int) and not isinstance(x, bool)
                       and 0 <= x < total for x in (subdivision, a, b)):
                return None
            if len({subdivision, a, b}) != 3:
                return None
            adjacency[subdivision].add(a)
            adjacency[subdivision].add(b)
            adjacency[a].add(subdivision)
            adjacency[b].add(subdivision)
    except (KeyError, TypeError, ValueError):
        return None
    return adjacency


def _components(adjacency, removed):
    unseen = set(range(len(adjacency))) - set(removed)
    components = []
    while unseen:
        start = min(unseen)
        unseen.remove(start)
        component = {start}
        stack = [start]
        while stack:
            vertex = stack.pop()
            for neighbor in adjacency[vertex]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    component.add(neighbor)
                    stack.append(neighbor)
        components.append(component)
    return components


def render(inst):
    """Render the complete, standalone exact graph problem."""
    rows = "\n".join(
        f"  {s}: {a} {b}" for s, a, b in inst["subdivisions"]
    )
    core = " ".join(map(str, inst["core_vertices"]))
    statement = f"""Find a balanced spanning induced-minor model of K_{{2,3}} in the finite simple undirected graph below.

Definitions.  K_{{2,3}} has two nonadjacent vertices U,V and three nonadjacent vertices A,B,C; every one of U,V is adjacent to every one of A,B,C.  An induced-minor model assigns a nonempty branch set of graph vertices to each target vertex so that branch sets are pairwise disjoint, each branch set induces a connected subgraph, and two branch sets have at least one edge between them if and only if their target vertices are adjacent.

This instance has {inst['n_vertices']} vertices, numbered 0 through {inst['n_vertices'] - 1}.  It is the full subdivision of a {inst['core_degree']}-regular graph.  The core vertices are:
  {core}

Every other vertex has degree two.  The complete edge set is encoded by the following subdivision table.  A row "s: x y" means that edges s-x and s-y exist.  There are no other edges.
{rows}

Your certificate must be [BU,BV,BA,BB,BC], a JSON array of five branch sets.  Every branch set is a JSON array of strictly increasing, unrepeated integer vertex identifiers.  The five sets must partition all graph vertices.  BU and BV must each contain exactly {inst['required_side_size']} vertices; BA, BB, and BC must each contain exactly one degree-two vertex.  For a canonical output, require min(BU) < min(BV) and the sole vertices of BA,BB,BC to increase in that order.  The induced-minor adjacency rule above must hold exactly.  Vertex indexing is zero-based.

Give your final answer inside <answer></answer> tags, as one nested JSON array in the exact [BU,BV,BA,BB,BC] format.
Example: <answer>[[0,2],[1,3],[4],[5],[6]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse the last tagged branch-set model, tolerating prose/fences."""
    if not isinstance(text, str):
        return None
    matches = _TAG_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if (not isinstance(value, list) or len(value) != 5 or
            not all(isinstance(branch, list) for branch in value) or
            not all(isinstance(x, int) and not isinstance(x, bool)
                    for branch in value for x in branch)):
        return None
    return value


def verify(inst, answer):
    """Check any valid full branch-set model without reading inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if len(answer) == 0:
        return False, "answer is empty; expected five branch sets"
    if len(answer) != 5:
        return False, f"wrong branch-set count: expected 5, received {len(answer)}"
    if not all(isinstance(branch, list) for branch in answer):
        return False, "every branch set must be a JSON array"
    if any(len(branch) == 0 for branch in answer):
        return False, "branch sets must be nonempty"
    if not all(isinstance(x, int) and not isinstance(x, bool)
               for branch in answer for x in branch):
        return False, "every vertex identifier must be an integer"
    total = inst.get("n_vertices")
    flat = [x for branch in answer for x in branch]
    if any(x < 0 or not isinstance(total, int) or x >= total for x in flat):
        return False, f"a vertex identifier lies outside the range 0..{total - 1}"
    if any(branch != sorted(branch) or len(set(branch)) != len(branch)
           for branch in answer):
        return False, "each branch set must be strictly increasing without repeats"
    if len(set(flat)) != len(flat):
        return False, "branch sets must be pairwise disjoint"
    if set(flat) != set(range(total)):
        return False, "the five branch sets must partition every graph vertex"
    wanted = inst.get("required_side_size")
    if [len(answer[0]), len(answer[1])] != [wanted, wanted]:
        return False, (
            f"large branch sizes must be [{wanted}, {wanted}], received "
            f"{[len(answer[0]), len(answer[1])]}"
        )
    if [len(branch) for branch in answer[2:]] != [1, 1, 1]:
        return False, "the last three branch sets must be singletons"
    if answer[0][0] >= answer[1][0]:
        return False, "BU and BV are not in canonical minimum-vertex order"
    singleton_vertices = [branch[0] for branch in answer[2:]]
    if singleton_vertices != sorted(singleton_vertices):
        return False, "BA, BB, and BC are not in increasing singleton order"
    adjacency = _adjacency(inst)
    if adjacency is None:
        return False, "instance graph encoding is malformed"
    if any(len(adjacency[x]) != 2 for x in singleton_vertices):
        return False, "every singleton branch vertex must have graph degree two"
    branch_of = {}
    for index, branch in enumerate(answer):
        for vertex in branch:
            branch_of[vertex] = index
    for index, branch in enumerate(answer):
        reached = {branch[0]}
        stack = [branch[0]]
        allowed = set(branch)
        while stack:
            vertex = stack.pop()
            for neighbor in adjacency[vertex] & allowed:
                if neighbor not in reached:
                    reached.add(neighbor)
                    stack.append(neighbor)
        if reached != allowed:
            return False, f"branch set {index} is not connected"
    target_edges = {
        (0, 2), (0, 3), (0, 4), (1, 2), (1, 3), (1, 4)
    }
    seen_edges = set()
    for vertex in range(total):
        for neighbor in adjacency[vertex]:
            if vertex < neighbor and branch_of[vertex] != branch_of[neighbor]:
                seen_edges.add(tuple(sorted((branch_of[vertex], branch_of[neighbor]))))
    if seen_edges != target_edges:
        extra = sorted(seen_edges - target_edges)
        missing = sorted(target_edges - seen_edges)
        return False, f"branch-set adjacencies mismatch K_{{2,3}}: extra={extra}, missing={missing}"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample the full stated partition shape, including obvious ordering rules."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    candidates = sorted(row[0] for row in inst["subdivisions"])
    singletons = sorted(rng.sample(candidates, 3))
    remaining = [v for v in range(inst["n_vertices"]) if v not in set(singletons)]
    first = set(rng.sample(remaining, inst["required_side_size"]))
    large = [sorted(first), sorted(set(remaining) - first)]
    large.sort(key=lambda branch: branch[0])
    return large + [[v] for v in singletons]


def search_space(inst):
    """Number of canonical shape-valid partitions in the certificate language."""
    separators = math.comb(len(inst["subdivisions"]), 3)
    bisections = math.comb(inst["n_vertices"] - 3,
                           inst["required_side_size"]) // 2
    return separators * bisections


def enumerate_all(inst):
    """Count every valid certificate when the exact search is small enough."""
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    candidates = sorted(row[0] for row in inst["subdivisions"])
    count = 0
    for triple in itertools.combinations(candidates, 3):
        remaining = [v for v in range(inst["n_vertices"]) if v not in triple]
        for first_tuple in itertools.combinations(remaining, inst["required_side_size"]):
            first = set(first_tuple)
            second = set(remaining) - first
            if min(first) > min(second):
                continue
            answer = [sorted(first), sorted(second)] + [[v] for v in triple]
            if verify(inst, answer)[0]:
                count += 1
    return count


def _core_graph(inst):
    vertices = set(inst["core_vertices"])
    edges = []
    subdivision_for_edge = {}
    for subdivision, a, b in inst["subdivisions"]:
        edge = (min(a, b), max(a, b))
        edges.append(edge)
        subdivision_for_edge[edge] = subdivision
    return vertices, edges, subdivision_for_edge


def _model_from_separator(inst, separator):
    """Canonical full candidate determined by a proposed singleton separator."""
    separator = sorted(separator)
    adjacency = _adjacency(inst)
    if adjacency is None or len(separator) != 3 or len(set(separator)) != 3:
        return None
    remaining = [v for v in range(inst["n_vertices"]) if v not in set(separator)]
    components = _components(adjacency, set(separator))
    wanted = inst["required_side_size"]
    if len(components) == 2 and sorted(map(len, components)) == [wanted, wanted]:
        large = [sorted(component) for component in components]
    else:
        # Preserve every obvious format/size rule even when the proposed cut is
        # wrong, so the attack is graded on graph structure rather than syntax.
        large = [remaining[:wanted], remaining[wanted:]]
    large.sort(key=lambda branch: branch[0])
    return large + [[v] for v in separator]


def _reference_algorithm(inst):
    vertices, edges, subdivision_for_edge = _core_graph(inst)
    started = time.perf_counter()
    weight, shore, operations = _stoer_wagner(vertices, edges)
    crossing = sorted(
        subdivision_for_edge[(min(a, b), max(a, b))]
        for a, b in edges if (a in shore) != (b in shore)
    )
    elapsed = time.perf_counter() - started
    if weight != 3 or len(crossing) != 3:
        return None, operations, elapsed
    return _model_from_separator(inst, crossing), operations, elapsed


def _distance_profiles(vertices, edges):
    adjacency = {v: set() for v in vertices}
    for a, b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)
    distances = {}
    for source in vertices:
        dist = {source: 0}
        queue = [source]
        for vertex in queue:
            for neighbor in adjacency[vertex]:
                if neighbor not in dist:
                    dist[neighbor] = dist[vertex] + 1
                    queue.append(neighbor)
        distances[source] = dist
    initial = {}
    for u in vertices:
        histogram = {}
        for distance in distances[u].values():
            histogram[distance] = histogram.get(distance, 0) + 1
        initial[u] = (tuple(sorted(histogram.items())),
                      sum(1 for a, b in itertools.combinations(adjacency[u], 2)
                          if b in adjacency[a]))
    unique = {value: i for i, value in enumerate(sorted(set(initial.values())))}
    colors = {v: unique[initial[v]] for v in vertices}
    for _ in range(len(vertices)):
        raw = {
            v: (colors[v], tuple(sorted(colors[w] for w in adjacency[v])))
            for v in vertices
        }
        palette = {value: i for i, value in enumerate(sorted(set(raw.values())))}
        refined = {v: palette[raw[v]] for v in vertices}
        if refined == colors:
            break
        colors = refined
    profiles = []
    for u in vertices:
        joint = []
        for v in vertices:
            common = len(adjacency[u] & adjacency[v])
            joint.append((distances[u][v], colors[v], common, int(v in adjacency[u])))
        profiles.append((colors[u], tuple(sorted(joint))))
    return sorted(profiles)


def canonical_key(inst):
    """A strong relabelling-invariant fingerprint of the suppressed core."""
    vertices, edges, _ = _core_graph(inst)
    payload = {
        "vertices": len(vertices),
        "edges": len(edges),
        "degree": inst["core_degree"],
        "distance_refinement_profiles": _distance_profiles(vertices, edges),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def escalate(params):
    """Grow candidate crowding at fixed degree while keeping three outputs."""
    p = {k: v for k, v in params.items() if k != "_preset"}
    current_n = int(p.get("n", 0))
    current_degree = int(p.get("degree", 5))
    # Keeping the degree fixed and adding two vertices to each duplicated core
    # half increases both the subdivision haystack and the rendered graph.  It
    # also preserves the required odd quotient n/degree.
    next_n = current_n + 2 * current_degree
    next_vertices = next_n + 2 * (next_n // current_degree)
    next_route_operations = next_n + next_vertices + 12
    # Past this point the compact one-pass route crosses G9's 300-operation
    # no-tool cap.  This is an effort bound, not a claim that the family is easy.
    if next_route_operations > 300 or next_vertices > 256:
        return "cap_bound"
    p["degree"] = current_degree
    p["n"] = next_n
    return p


def _relabel_instance(inst, rng, reorder=True):
    total = inst["n_vertices"]
    labels = list(range(total))
    rng.shuffle(labels)
    mapping = {old: labels[old] for old in range(total)}
    rows = [
        [mapping[s], mapping[a], mapping[b]]
        for s, a, b in inst["subdivisions"]
    ]
    for row in rows:
        if rng.randrange(2):
            row[1], row[2] = row[2], row[1]
    if reorder:
        rng.shuffle(rows)
    large = [sorted(mapping[v] for v in branch) for branch in inst["answer"][:2]]
    large.sort(key=lambda branch: branch[0])
    singleton_values = sorted(mapping[branch[0]] for branch in inst["answer"][2:])
    out = {
        "family": inst["family"],
        "n_vertices": total,
        "core_degree": inst["core_degree"],
        "core_vertices": [mapping[v] for v in reversed(inst["core_vertices"])],
        "subdivisions": rows,
        "required_side_size": inst["required_side_size"],
        "answer": large + [[v] for v in singleton_values],
    }
    return out


def _attack_first_rows(inst):
    return sorted(row[0] for row in inst["subdivisions"])[:3]


def _attack_largest_numeric_span(inst):
    rows = sorted(inst["subdivisions"],
                  key=lambda row: (abs(row[1] - row[2]), row[0]), reverse=True)
    return sorted(row[0] for row in rows[:3])


def _attack_evenly_spaced_rows(inst):
    candidates = sorted(row[0] for row in inst["subdivisions"])
    indices = [len(candidates) // 4, len(candidates) // 2,
               (3 * len(candidates)) // 4]
    return sorted(candidates[i] for i in indices)


def _attack_local_signature(inst):
    vertices, edges, subdivision_for_edge = _core_graph(inst)
    adjacency = {v: set() for v in vertices}
    for a, b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)
    triangles = {
        v: sum(1 for a, b in itertools.combinations(adjacency[v], 2)
               if b in adjacency[a])
        for v in vertices
    }
    scored = []
    signatures = []
    for a, b in edges:
        signature = (
            len(adjacency[a] & adjacency[b]),
            min(triangles[a], triangles[b]),
            max(triangles[a], triangles[b]),
        )
        signatures.append(signature)
    frequency = {s: signatures.count(s) for s in set(signatures)}
    for (a, b), signature in zip(edges, signatures):
        edge = (min(a, b), max(a, b))
        scored.append((frequency[signature], signature,
                       subdivision_for_edge[edge]))
    scored.sort()
    return sorted(item[2] for item in scored[:3])


def _attack_random_restart(inst, seed, restarts=256):
    rng = random.Random(seed)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest():
    """Run all mandatory correctness, resistance, scaling, and invariance gates."""
    report = {
        "paper": "arXiv:2402.08332",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    g1_failures = []
    construction_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append(f"{preset}/seed={seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/seed={seed}: answer is not JSON-native")
            adjacency = _adjacency(inst)
            if adjacency is None:
                g1_failures.append(f"{preset}/seed={seed}: malformed graph")
            else:
                core = set(inst["core_vertices"])
                for vertex in range(inst["n_vertices"]):
                    wanted = inst["core_degree"] if vertex in core else 2
                    construction_checks += 1
                    if len(adjacency[vertex]) != wanted:
                        g1_failures.append(
                            f"{preset}/seed={seed}: degree identity failed at {vertex}"
                        )
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": 16,
        "construction_identity_checks": construction_checks,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=17, **shipping)
    answer = json.loads(json.dumps(inst["answer"]))
    dropped = json.loads(json.dumps(answer))
    dropped[0] = dropped[0][:-1]
    swapped = json.loads(json.dumps(answer))
    swapped[0][0], swapped[1][0] = swapped[1][0], swapped[0][0]
    swapped[0].sort()
    swapped[1].sort()
    duplicated = json.loads(json.dumps(answer))
    duplicated[0][1] = duplicated[0][0]
    out_of_range = json.loads(json.dumps(answer))
    out_of_range[0][0] = inst["n_vertices"]
    wrong_singleton = json.loads(json.dumps(answer))
    core_vertex = next(v for v in wrong_singleton[0]
                       if v in set(inst["core_vertices"]))
    old_singleton = wrong_singleton[2][0]
    wrong_singleton[0].remove(core_vertex)
    wrong_singleton[0].append(old_singleton)
    wrong_singleton[0].sort()
    singleton_values = sorted(
        [core_vertex] + [branch[0] for branch in wrong_singleton[3:]]
    )
    wrong_singleton[2:] = [[v] for v in singleton_values]
    corruptions = {
        "drop_one": dropped,
        "swap_two": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
        "wrong_singleton_shape": wrong_singleton,
    }
    corruption_report = {}
    reasons = set()
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        corruption_report[name] = {"rejected": not ok, "reason": reason}
        if not ok:
            reasons.add(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in corruption_report.values())
        and len(reasons) == len(corruptions),
        "distinct_reasons": len(reasons),
        "corruptions": corruption_report,
    }

    realistic = (
        "I used the component criterion.\n```json\n"
        f"<answer>{json.dumps(answer)}</answer>\n```\n"
        "The two shores have the requested size."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer,
        "parsed": parsed,
    }

    guess_rng = random.Random(240208332)
    guess_total = 200_000
    guess_hits = 0
    guess_started = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            guess_hits += 1
    guess_elapsed = time.perf_counter() - guess_started
    probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": probability,
        "sampler": (
            "uniform degree-two singleton triple followed by a uniform balanced "
            "bisection of all remaining vertices, with canonical branch ordering"
        ),
        "structure_aware_space": search_space(inst),
        "wall_clock_sec": guess_elapsed,
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    attack_started = time.perf_counter()
    strongest_answer = _model_from_separator(inst, _attack_local_signature(inst))
    strongest_elapsed = time.perf_counter() - attack_started
    strongest_ok = verify(inst, strongest_answer)[0]
    ref_answer, ref_ops, ref_elapsed = _reference_algorithm(inst)
    ref_ok = ref_answer is not None and verify(inst, ref_answer)[0]
    report["G5_density_and_baseline"] = {
        "pass": probability < 1e-6 and ref_ok and not strongest_ok,
        "shipping_valid_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_observed_solution_fraction": probability,
        "shipping_structure_aware_space": search_space(inst),
        "demo_exact_solution_count": demo_count,
        "demo_exact_space": search_space(demo),
        "demo_exact_solution_fraction": demo_count / search_space(demo),
        "strongest_failing_attack_name": "rarest_local_triangle_signature",
        "strongest_failing_attack_successes": int(strongest_ok),
        "strongest_failing_attack_wall_clock_sec": strongest_elapsed,
        "baseline_reference_verified": ref_ok,
        "baseline_reference_operations": ref_ops,
        "baseline_reference_wall_clock_sec": ref_elapsed,
    }

    attacks = {
        "outlier_rarest_local_triangle_signature": 0,
        "greedy_first_three_table_rows": 0,
        "greedy_largest_numeric_endpoint_span": 0,
        "by_hand_evenly_spaced_table_rows": 0,
        "random_restart_256": 0,
    }
    reference_successes = 0
    reference_operations = []
    reference_times = []
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **shipping)
        candidates = {
            "outlier_rarest_local_triangle_signature": _model_from_separator(
                trial, _attack_local_signature(trial)),
            "greedy_first_three_table_rows": _model_from_separator(
                trial, _attack_first_rows(trial)),
            "greedy_largest_numeric_endpoint_span": _model_from_separator(
                trial, _attack_largest_numeric_span(trial)),
            "by_hand_evenly_spaced_table_rows": _model_from_separator(
                trial, _attack_evenly_spaced_rows(trial)),
            "random_restart_256": _attack_random_restart(trial, seed + 9000),
        }
        for name, candidate in candidates.items():
            if candidate is not None and verify(trial, candidate)[0]:
                attacks[name] += 1
        found, operations, elapsed = _reference_algorithm(trial)
        reference_operations.append(operations)
        reference_times.append(elapsed)
        if found is not None and verify(trial, found)[0]:
            reference_successes += 1
    attack_records = {
        name: {"successes": successes, "attempts": 8}
        for name, successes in attacks.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(value == 0 for value in attacks.values())
        and reference_successes == 8,
        "attacks": attack_records,
        "reference_algorithm": {
            "name": "Stoer-Wagner exact global minimum cut on the suppressed core",
            "complexity": "O(c^3) for c core vertices",
            "successes": reference_successes,
            "attempts": 8,
            "solves": f"{reference_successes}/8, as expected",
            "median_operations": int(statistics.median(reference_operations)),
            "median_wall_clock_sec": statistics.median(reference_times),
        },
    }

    doubled_n = 2 * shipping["n"]
    degree = shipping["degree"]
    quotient = math.ceil(doubled_n / degree)
    if quotient % 2 == 0:
        quotient += 1
    scaled_params = {"n": degree * quotient, "degree": degree}
    scaled = make_instance(seed=29, **scaled_params)
    scaled_ok, scaled_reason = verify(scaled, scaled["answer"])
    report["G7_scales"] = {
        "pass": scaled_ok and scaled_params["n"] >= 2 * shipping["n"],
        "shipping_n": shipping["n"],
        "doubled_n": scaled_params["n"],
        "shipping_graph_vertices": inst["n_vertices"],
        "doubled_graph_vertices": scaled["n_vertices"],
        "verify_reason": scaled_reason,
    }

    invariant_failures = []
    invariant_checks = 0
    carried_checks = 0
    keys = []
    for seed in range(20):
        original = make_instance(seed=1000 + seed, **shipping)
        key = canonical_key(original)
        keys.append(key)
        relabelled = _relabel_instance(original, random.Random(seed + 7000))
        reordered = _relabel_instance(original, random.Random(seed + 8000), reorder=True)
        composed = _relabel_instance(relabelled, random.Random(seed + 9000), reorder=True)
        for transformed in (relabelled, reordered, composed):
            invariant_checks += 1
            if canonical_key(transformed) != key:
                invariant_failures.append(f"seed {seed}: key changed")
            ok, reason = verify(transformed, transformed["answer"])
            carried_checks += 1
            if not ok:
                invariant_failures.append(f"seed {seed}: carried witness failed: {reason}")
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and len(set(keys)) == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": len(set(keys)),
        "symmetries": [
            "arbitrary vertex relabelling",
            "subdivision-table row reordering",
            "endpoint order reversal",
            "compositions of relabelling and storage-order changes",
        ],
        "failures": invariant_failures,
    }

    answer_blob = json.dumps(inst["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = max(1, math.ceil(answer_chars / 4))
    answer_elements = _answer_atoms(inst["answer"])
    intended_operations = (
        len(inst["subdivisions"]) + inst["n_vertices"] + 12
    )
    arms = {
        name: dict(G9_ORACLE_RESULTS.get(name, {"solved": 0, "attempts": 0}))
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS.get("hinted_verdict", "not_run"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "note": "oracle arms are recorded diagnostics; only the size/effort caps gate",
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
