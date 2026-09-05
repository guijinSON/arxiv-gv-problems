"""Verified generator for proper conflict-free 5-coloring on bipartite graphs.

The construction uses Lemma 3.3 of Ahn--Im--Oum (arXiv:2208.08330): a
proper 5-coloring of a graph G extends to a proper conflict-free 5-coloring
of the 1-subdivision of G.  The core coloring is planted; it is never found by
solving the generated instance.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import sys
import time


# Keep gvlib importable when the module is run from results/2208.08330.  This
# family is purely finite-discrete, so it does not otherwise need the helpers.
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - the module remains stdlib-only
    exact_matrices = rationals = None


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "bipartite 1-subdivision graph",
        "core graph encoded by its edge list",
    ],
    "verification_operations": [
        "integer color comparison",
        "exact neighborhood multiplicity count",
        "deterministic Lemma 3.3 extension",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3, Lemma 3.3 (the 1-subdivision reduction from ordinary "
        "k-coloring for k>=5)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Recognize the hidden five equal independent classes in the regular core; "
        "without that decomposition one must solve a crowded balanced coloring CSP."
    ),
    "hardness_basis": (
        "Track A: Theorem 3.1 together with Lemma 3.3 makes PCF 5-coloring "
        "NP-complete on bipartite 1-subdivisions; at the shipping regime of 120 "
        "core vertices, degree 12, the balanced DSATUR baseline exhausts 300000 "
        "nodes per instance (wall-clock measured by selftest) on 8/8 seeds."
    ),
    "max_answer_tokens": 90,
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
    "demo": {"n": 10, "matchings": 1, "extra_rounds": 0},
    "easy": {"n": 120, "matchings": 3, "extra_rounds": 0},
    "medium": {"n": 160, "matchings": 3, "extra_rounds": 0},
    "hard": {"n": 200, "matchings": 3, "extra_rounds": 0},
}

SHIPPING_DIFFICULTY = "easy"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of n colors in {1,2,3,4,5}, with every color used "
        "exactly n/5 times; it compactly specifies the colors of the original "
        "vertices of the 1-subdivision."
    ),
    "bounds": {
        "colors": 5,
        "max_length_at_shipping": 120,
        "exact_equal_multiplicity": True,
    },
}

STRUCTURAL_HINT = (
    "The regular core is a union of perfect matchings between five equal-size "
    "latent independent classes."
)
PLACEBO_HINT = (
    "The displayed core should be read carefully because every listed edge "
    "contributes one subdivision vertex."
)

G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES = """
Definition: Section 1 defines a PCF coloring as a proper coloring in which every
non-isolated vertex has a neighbor whose color occurs exactly once in its open
neighborhood.  Section 3, Lemma 3.3 fixes the construction used here: for k>=5,
ordinary k-coloring of G and PCF k-coloring of sub_1(G) are equivalent, and the
proof gives the greedy extension implemented below.  Theorem 3.1 supplies the
NP-complete bipartite regime.  The easy regimes explicitly avoided are k<=2
(Section 1), degree at most one for PCF 2-coloring, and bounded clique-width for
fixed k (Section 5, O(n^3) via counting MSO).

The certificate-producing algorithm is not a solver: inverse generation first
chooses five balanced color classes, samples every edge between different
classes, and then executes the constructive extension from Lemma 3.3.  Its cost
is linear in the generated edge set once the planted core coloring is known.
Finding the core coloring is the NP-hard step preserved by the lemma.

Attack hardening: all core vertices have equal degree, so degree outliers carry
no signal.  Plants and decoys are the same random perfect-matching edges.  The
panel includes a local-statistic partition, balanced greedy saturation, random
restarts, a bottom-eigenspace spectral clustering attack, and exact balanced
DSATUR with a node cap.  The shipping cost and all successes are measured afresh
by selftest().
""".strip()


def _add_random_matching(rng, left, right, edges):
    """Add a uniformly shuffled perfect matching, rejecting duplicate edges."""
    for _ in range(2000):
        perm = list(right)
        rng.shuffle(perm)
        proposed = [tuple(sorted((left[i], perm[i]))) for i in range(len(left))]
        if all(edge not in edges for edge in proposed):
            edges.update(proposed)
            return
    raise RuntimeError("could not draw an edge-disjoint perfect matching")


def make_instance(n, seed=0, matchings=3, extra_rounds=0, **params):
    """Inverse-generate a balanced core coloring and its bipartite subdivision."""
    if params:
        unknown = ", ".join(sorted(params))
        raise TypeError(f"unknown parameters: {unknown}")
    if not isinstance(n, int) or isinstance(n, bool) or n < 10 or n % 5:
        raise ValueError("n must be an integer multiple of 5 and at least 10")
    if not isinstance(matchings, int) or matchings < 1:
        raise ValueError("matchings must be a positive integer")
    if not isinstance(extra_rounds, int) or extra_rounds < 0:
        raise ValueError("extra_rounds must be a nonnegative integer")
    class_size = n // 5
    if matchings + 2 * extra_rounds >= class_size:
        raise ValueError("too many matchings for the class size")

    rng = random.Random(seed)
    labels = list(range(n))
    rng.shuffle(labels)
    groups = [labels[i * class_size : (i + 1) * class_size] for i in range(5)]

    edges = set()
    for a in range(5):
        for b in range(a + 1, 5):
            for _ in range(matchings):
                _add_random_matching(rng, groups[a], groups[b], edges)

    # Each extra round is a randomly ordered 5-cycle of class pairs.  It adds
    # degree two everywhere while retaining perfect balance and no degree cue.
    for _ in range(extra_rounds):
        cycle = list(range(5))
        rng.shuffle(cycle)
        for i in range(5):
            _add_random_matching(
                rng, groups[cycle[i]], groups[cycle[(i + 1) % 5]], edges
            )

    edge_list = list(edges)
    rng.shuffle(edge_list)

    color_names = [1, 2, 3, 4, 5]
    rng.shuffle(color_names)
    answer = [0] * n
    for group_index, group in enumerate(groups):
        for vertex in group:
            answer[vertex] = color_names[group_index]

    return {
        "family": "pcf5_one_subdivision",
        "n": n,
        "k": 5,
        "class_size": class_size,
        "matchings": matchings,
        "extra_rounds": extra_rounds,
        "regular_degree": 4 * matchings + 2 * extra_rounds,
        # Public labels and rendered labels are 1-based.
        "core_edges": [[u + 1, v + 1] for u, v in edge_list],
        "subdivision_vertex_count": len(edge_list),
        "total_vertices": n + len(edge_list),
        "answer": answer,
    }


def _core_adjacency(inst):
    n = inst["n"]
    adjacency = [[] for _ in range(n)]
    for edge in inst["core_edges"]:
        u, v = edge[0] - 1, edge[1] - 1
        adjacency[u].append(v)
        adjacency[v].append(u)
    for neighbors in adjacency:
        neighbors.sort()
    return adjacency


def _extend_core_coloring(inst, core_colors):
    """Execute the greedy extension in the proof of Lemma 3.3."""
    n = inst["n"]
    counts = [[0] * 6 for _ in range(n)]
    subdivision_colors = []
    for edge in inst["core_edges"]:
        u, v = edge[0] - 1, edge[1] - 1
        forbidden = {core_colors[u], core_colors[v]}
        for endpoint in (u, v):
            unique = next((c for c in range(1, 6) if counts[endpoint][c] == 1), None)
            if unique is not None:
                forbidden.add(unique)
        color = next(c for c in range(1, 6) if c not in forbidden)
        subdivision_colors.append(color)
        counts[u][color] += 1
        counts[v][color] += 1
    return subdivision_colors, counts


def render(inst):
    """Render a complete, standalone PCF-coloring problem."""
    n = inst["n"]
    m = len(inst["core_edges"])
    edges = " ".join(f"{u}-{v}" for u, v in inst["core_edges"])
    statement = f"""Proper conflict-free 5-coloring of a bipartite 1-subdivision

A proper conflict-free (PCF) coloring of a finite simple graph assigns a color
to every vertex so that (i) adjacent vertices have different colors and (ii)
every non-isolated vertex has at least one neighbor whose color occurs exactly
once among all of that vertex's neighbors.  Neighborhoods are open: a vertex is
not its own neighbor.

The graph H below is specified as the 1-subdivision of a core graph G.  G has
original vertices 1 through {n}.  For each displayed core edge u-v, in the exact
left-to-right order shown, H replaces u-v by u-s-v using one new subdivision
vertex s.  Thus H has {n}+{m}={n + m} vertices, and is bipartite even though G
need not be.  Core edges are unordered, have no repeats, and vertex labels are
1-based.

Core edges ({m}):
{edges}

Give a compressed PCF 5-coloring certificate: a JSON list of exactly {n}
integers, where entry i is the color of original vertex i+1.  Allowed colors are
1,2,3,4,5; every color must occur exactly {n // 5} times.  The listed core colors
must be proper on every displayed core edge.

The checker completes your list to all subdivision vertices deterministically.
It processes core edges in displayed order.  At each endpoint it marks that
endpoint's own color and, if one exists, the smallest color currently occurring
exactly once on already processed subdivision neighbors.  The new subdivision
vertex receives the smallest color in 1..5 not marked at either endpoint.  The
checker then directly verifies both PCF conditions on all of H.  Five colors
guarantee that the prescribed choice always exists for a proper core coloring.

Give your final answer inside <answer></answer> tags, as one JSON list of {n}
integers.  Example syntax: <answer>[1,2,3,4,5]</answer> (your list must have
exactly {n} entries).  Output nothing else inside the tags."""
    hint_mode = os.environ.get("GV_HINT_MODE")
    if hint_mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif hint_mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse a JSON color list from tags, fences, or surrounding prose."""
    if not isinstance(text, str):
        return None
    tagged = re.search(r"<answer>\s*(.*?)\s*</answer>", text, re.I | re.S)
    candidates = [tagged.group(1)] if tagged else []
    candidates.extend(re.findall(r"\[[\s\d,+-]*\]", text, re.S))
    for raw in candidates:
        raw = re.sub(r"^```(?:json|text)?\s*|\s*```$", "", raw.strip(), flags=re.I)
        try:
            value = json.loads(raw)
        except (TypeError, ValueError):
            # A common model variation omits the square brackets inside tags.
            if re.fullmatch(r"[\s\d,+-]+", raw or ""):
                try:
                    value = [int(x.strip()) for x in raw.split(",") if x.strip()]
                except ValueError:
                    continue
            else:
                continue
        if isinstance(value, list) and all(
            isinstance(x, int) and not isinstance(x, bool) for x in value
        ):
            return value
    return None


def verify(inst, answer):
    """Check any balanced core witness and its exact PCF extension."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    n = inst["n"]
    if len(answer) < n:
        return False, f"too few colors: expected {n}, received {len(answer)}"
    if len(answer) > n:
        return False, f"too many colors: expected {n}, received {len(answer)}"
    for i, color in enumerate(answer):
        if not isinstance(color, int) or isinstance(color, bool):
            return False, f"entry {i + 1} is not an integer"
        if not 1 <= color <= 5:
            return False, f"entry {i + 1} has color outside 1..5"
    expected = n // 5
    multiplicities = [answer.count(color) for color in range(1, 6)]
    if multiplicities != [expected] * 5:
        return False, f"color multiplicities are not all {expected}"

    for u1, v1 in inst["core_edges"]:
        if answer[u1 - 1] == answer[v1 - 1]:
            return False, f"core edge {u1}-{v1} has equal endpoint colors"

    subdivision, counts = _extend_core_coloring(inst, answer)
    for vertex, row in enumerate(counts, 1):
        if not any(row[color] == 1 for color in range(1, 6)):
            return False, f"original vertex {vertex} has no unique neighbor color"
    for edge_index, ((u1, v1), color) in enumerate(
        zip(inst["core_edges"], subdivision), 1
    ):
        u_color, v_color = answer[u1 - 1], answer[v1 - 1]
        if color in (u_color, v_color):
            return False, f"subdivision vertex {edge_index} violates properness"
        if u_color == v_color:
            return False, f"subdivision vertex {edge_index} has no unique neighbor color"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from the explicit balanced certificate language."""
    candidate = []
    for color in range(1, 6):
        candidate.extend([color] * inst["class_size"])
    rng.shuffle(candidate)
    return candidate


def search_space(inst):
    """Number of labeled balanced five-color strings."""
    numerator = math.factorial(inst["n"])
    denominator = math.factorial(inst["class_size"]) ** 5
    return numerator // denominator


def enumerate_all(inst):
    """Count valid balanced witnesses exactly when the space is small."""
    if inst["n"] > 10 or search_space(inst) > 500_000:
        return None
    adjacency = _core_adjacency(inst)
    n = inst["n"]
    quota = inst["class_size"]
    colors = [-1] * n
    used = [0] * 5

    # Color labels are symmetric.  Fix vertex 0 to color 0 and multiply by 5.
    colors[0] = 0
    used[0] = 1

    def count_completions(colored):
        if colored == n:
            return 1
        uncolored = [v for v in range(n) if colors[v] < 0]
        vertex = max(
            uncolored,
            key=lambda v: (
                len({colors[w] for w in adjacency[v] if colors[w] >= 0}),
                len(adjacency[v]),
                -v,
            ),
        )
        forbidden = {colors[w] for w in adjacency[vertex] if colors[w] >= 0}
        total = 0
        for color in range(5):
            if color in forbidden or used[color] >= quota:
                continue
            colors[vertex] = color
            used[color] += 1
            total += count_completions(colored + 1)
            used[color] -= 1
            colors[vertex] = -1
        return total

    return 5 * count_completions(1)


def _structural_signature(inst):
    """A strong cheap isomorphism invariant; not a claimed canonical labeling."""
    adjacency = _core_adjacency(inst)
    n = len(adjacency)
    sets = [set(row) for row in adjacency]
    degree_sequence = sorted(len(row) for row in adjacency)
    edge_common = [0] * (n + 1)
    nonedge_common = [0] * (n + 1)
    vertex_signatures = []
    for v in range(n):
        adjacent_hist = [0] * (n + 1)
        nonadjacent_hist = [0] * (n + 1)
        triangles = 0
        for w in range(n):
            if w == v:
                continue
            common = len(sets[v].intersection(sets[w]))
            if w in sets[v]:
                adjacent_hist[common] += 1
                triangles += common
            else:
                nonadjacent_hist[common] += 1
            if v < w:
                if w in sets[v]:
                    edge_common[common] += 1
                else:
                    nonedge_common[common] += 1
        vertex_signatures.append(
            (
                len(adjacency[v]),
                triangles // 2,
                tuple((i, x) for i, x in enumerate(adjacent_hist) if x),
                tuple((i, x) for i, x in enumerate(nonadjacent_hist) if x),
            )
        )
    return {
        "n": n,
        "m": len(inst["core_edges"]),
        "degrees": degree_sequence,
        "edge_common": [(i, x) for i, x in enumerate(edge_common) if x],
        "nonedge_common": [(i, x) for i, x in enumerate(nonedge_common) if x],
        "vertices": sorted(vertex_signatures),
    }


def canonical_key(inst):
    """Hash a relabeling-invariant collection of local graph invariants."""
    payload = json.dumps(_structural_signature(inst), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params):
    """Tighten first at fixed witness length, then grow up to the atom cap."""
    current = dict(params)
    current.pop("_preset", None)
    if current.get("extra_rounds", 0) == 0:
        current["extra_rounds"] = 1
        return current
    n = current["n"]
    if n < 240:
        current["n"] = min(240, 5 * math.ceil((n * 1.25) / 5))
        return current
    return "cap_bound"


def _attack_outlier_partition(inst):
    adjacency = _core_adjacency(inst)
    neighbor_sets = [set(row) for row in adjacency]
    scores = []
    for v, row in enumerate(adjacency):
        triangles_twice = sum(len(neighbor_sets[v] & neighbor_sets[w]) for w in row)
        scores.append((len(row), triangles_twice // 2, v))
    order = [v for _, _, v in sorted(scores)]
    answer = [0] * inst["n"]
    size = inst["class_size"]
    for rank, vertex in enumerate(order):
        answer[vertex] = rank // size + 1
    return answer


def _balanced_greedy(inst, rng=None):
    adjacency = _core_adjacency(inst)
    n, k, quota = inst["n"], 5, inst["class_size"]
    colors = [-1] * n
    used = [0] * k
    for _ in range(n):
        candidates = [v for v in range(n) if colors[v] < 0]
        scored = []
        best_score = None
        for v in candidates:
            score = (len({colors[w] for w in adjacency[v] if colors[w] >= 0}), len(adjacency[v]))
            if best_score is None or score > best_score:
                best_score = score
                scored = [v]
            elif score == best_score:
                scored.append(v)
        vertex = rng.choice(scored) if rng is not None else min(scored)
        forbidden = {colors[w] for w in adjacency[vertex] if colors[w] >= 0}
        available = [c for c in range(k) if c not in forbidden and used[c] < quota]
        if not available:
            return None
        if rng is None:
            color = min(
                available,
                key=lambda c: (
                    sum(
                        1
                        for w in adjacency[vertex]
                        if colors[w] < 0
                        and all(colors[z] != c for z in adjacency[w] if colors[z] >= 0)
                    ),
                    used[c],
                    c,
                ),
            )
        else:
            minimum_use = min(used[c] for c in available)
            choices = [c for c in available if used[c] == minimum_use]
            color = rng.choice(choices)
        colors[vertex] = color
        used[color] += 1
    return [c + 1 for c in colors]


def _attack_random_restarts(inst, rng, restarts=64):
    for _ in range(restarts):
        candidate = _balanced_greedy(inst, rng)
        if candidate is not None and verify(inst, candidate)[0]:
            return candidate
    return None


def _orthogonalize(vector, basis):
    n = len(vector)
    mean = sum(vector) / n
    vector = [x - mean for x in vector]
    for old in basis:
        dot = sum(x * y for x, y in zip(vector, old))
        vector = [x - dot * y for x, y in zip(vector, old)]
    norm = math.sqrt(sum(x * x for x in vector))
    if norm < 1e-14:
        return None
    return [x / norm for x in vector]


def _attack_spectral(inst, rng):
    """Bottom-adjacency eigenspace plus balanced k-means, without numpy."""
    adjacency = _core_adjacency(inst)
    n = inst["n"]
    shift = max(len(row) for row in adjacency) + 1
    basis = []
    for _ in range(4):
        vector = _orthogonalize([rng.uniform(-1.0, 1.0) for _ in range(n)], basis)
        if vector is None:
            return None
        for _ in range(60):
            product = [
                shift * vector[v] - sum(vector[w] for w in adjacency[v])
                for v in range(n)
            ]
            vector = _orthogonalize(product, basis)
            if vector is None:
                return None
        basis.append(vector)
    points = [tuple(vector[v] for vector in basis) for v in range(n)]

    def distance2(a, b):
        return sum((x - y) ** 2 for x, y in zip(a, b))

    first = max(range(n), key=lambda v: sum(x * x for x in points[v]))
    centers = [points[first]]
    while len(centers) < 5:
        vertex = max(
            range(n), key=lambda v: min(distance2(points[v], c) for c in centers)
        )
        centers.append(points[vertex])
    assignment = [0] * n
    for _ in range(20):
        assignment = [
            min(range(5), key=lambda c: distance2(point, centers[c]))
            for point in points
        ]
        new_centers = []
        for c in range(5):
            members = [points[v] for v in range(n) if assignment[v] == c]
            if not members:
                new_centers.append(centers[c])
            else:
                new_centers.append(
                    tuple(sum(point[j] for point in members) / len(members) for j in range(4))
                )
        centers = new_centers

    preferences = []
    for v, point in enumerate(points):
        distances = sorted((distance2(point, centers[c]), c) for c in range(5))
        margin = distances[1][0] - distances[0][0]
        preferences.append((-margin, v, [c for _, c in distances]))
    capacities = [inst["class_size"]] * 5
    balanced = [-1] * n
    for _, vertex, choices in sorted(preferences):
        color = next((c for c in choices if capacities[c]), None)
        if color is None:
            return None
        balanced[vertex] = color + 1
        capacities[color] -= 1
    return balanced


def _balanced_dsatur(inst, node_cap=300_000):
    """Exact balanced DSATUR, resource-capped; returns answer and statistics."""
    adjacency = _core_adjacency(inst)
    n, k, quota = inst["n"], 5, inst["class_size"]
    colors = [-1] * n
    used = [0] * k
    saturation = [0] * n
    neighbor_color_count = [[0] * k for _ in range(n)]
    nodes = 0
    cutoff = False

    def visit(left, maximum_introduced):
        nonlocal nodes, cutoff
        nodes += 1
        if nodes > node_cap:
            cutoff = True
            return None
        if left == 0:
            return [c + 1 for c in colors]
        vertex = max(
            (v for v in range(n) if colors[v] < 0),
            key=lambda v: (saturation[v].bit_count(), len(adjacency[v]), -v),
        )
        options = [
            color
            for color in range(k)
            if not (saturation[vertex] >> color) & 1
            and used[color] < quota
            and color <= maximum_introduced + 1
        ]
        options.sort(
            key=lambda color: (
                -used[color],
                sum(
                    1
                    for w in adjacency[vertex]
                    if colors[w] < 0 and neighbor_color_count[w][color] == 0
                ),
                color,
            )
        )
        for color in options:
            colors[vertex] = color
            used[color] += 1
            changed = []
            for neighbor in adjacency[vertex]:
                if colors[neighbor] < 0:
                    if neighbor_color_count[neighbor][color] == 0:
                        saturation[neighbor] |= 1 << color
                    neighbor_color_count[neighbor][color] += 1
                    changed.append(neighbor)
            result = visit(left - 1, max(maximum_introduced, color))
            if result is not None:
                return result
            for neighbor in changed:
                neighbor_color_count[neighbor][color] -= 1
                if neighbor_color_count[neighbor][color] == 0:
                    saturation[neighbor] &= ~(1 << color)
            used[color] -= 1
            colors[vertex] = -1
        return None

    start = time.perf_counter()
    answer = visit(n, -1)
    elapsed = time.perf_counter() - start
    return answer, {"nodes": nodes, "cutoff": cutoff, "wall_seconds": elapsed}


def _relabel_instance(inst, permutation, reverse_edges=False):
    """Carry an instance and its planted witness through old->new relabeling."""
    transformed = dict(inst)
    edges = [
        [permutation[u - 1] + 1, permutation[v - 1] + 1]
        for u, v in inst["core_edges"]
    ]
    if reverse_edges:
        edges.reverse()
    transformed["core_edges"] = edges
    answer = [0] * inst["n"]
    for old, new in enumerate(permutation):
        answer[new] = inst["answer"][old]
    transformed["answer"] = answer
    return transformed


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest():
    report = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
        "certificate_language": CERTIFICATE_LANGUAGE,
    }

    verified = 0
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError(f"{preset}/{seed}: {reason}")
            verified += 1
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                raise AssertionError("answer is not JSON-native")
            json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": True,
        "verified": verified,
        "json_roundtrips": json_roundtrips,
        "construction": "inverse generation plus Lemma 3.3 extension",
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **shipping_params)
    planted = list(inst["answer"])
    edge_u, edge_v = (x - 1 for x in inst["core_edges"][0])
    swapped = list(planted)
    swapped[edge_u], swapped[edge_v] = swapped[edge_v], swapped[edge_u]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_one": swapped,
        "duplicate": planted + [planted[0]],
        "empty": [],
        "out_of_range": [6] + planted[1:],
    }
    corruption_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(x["rejected"] for x in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "cases": corruption_results,
    }

    encoded = json.dumps(planted, separators=(",", ":"))
    response = (
        "The core classes give the following coloring.\n```json\n"
        f"<answer>{encoded}</answer>\n```\nThe extension is forced by the rule."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted and verify(inst, parsed)[0],
        "parsed_entries": len(parsed) if parsed is not None else 0,
    }

    guess_rng = random.Random(0x220808330)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_wall = time.perf_counter() - guess_start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "wall_seconds": round(guess_wall, 6),
        "structure_aware_space": search_space(inst),
        "prior": "uniform over exactly balanced five-color strings",
    }

    attack_results = {
        "outlier_local_statistics": {"successes": 0, "attempts": 0},
        "greedy_balanced_saturation": {"successes": 0, "attempts": 0},
        "random_restart_balanced_64": {"successes": 0, "attempts": 0},
        "spectral_bottom_eigenspace": {"successes": 0, "attempts": 0},
        "balanced_DSatur_300k": {"successes": 0, "attempts": 0},
    }
    dsatur_stats = []
    for seed in range(8):
        trial = make_instance(seed=50_000 + seed, **shipping_params)
        candidates = {
            "outlier_local_statistics": _attack_outlier_partition(trial),
            "greedy_balanced_saturation": _balanced_greedy(trial),
            "random_restart_balanced_64": _attack_random_restarts(
                trial, random.Random(60_000 + seed), 64
            ),
            "spectral_bottom_eigenspace": _attack_spectral(
                trial, random.Random(70_000 + seed)
            ),
        }
        dsatur_answer, stats = _balanced_dsatur(trial, 300_000)
        candidates["balanced_DSatur_300k"] = dsatur_answer
        dsatur_stats.append(stats)
        for name, candidate in candidates.items():
            attack_results[name]["attempts"] += 1
            attack_results[name]["successes"] += int(verify(trial, candidate)[0])

    all_failed = all(item["successes"] == 0 for item in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attack_results,
        "standard_algorithm": "balanced DSATUR with color-symmetry breaking",
        "dsatur_node_cap_per_instance": 300_000,
        "dsatur_total_nodes": sum(x["nodes"] for x in dsatur_stats),
        "dsatur_total_wall_seconds": round(
            sum(x["wall_seconds"] for x in dsatur_stats), 6
        ),
        "dsatur_all_hit_cap": all(x["cutoff"] for x in dsatur_stats),
    }

    demo = make_instance(seed=11, **DIFFICULTY["demo"])
    demo_count_start = time.perf_counter()
    demo_count = enumerate_all(demo)
    demo_count_wall = time.perf_counter() - demo_count_start
    report["G5_density_and_baseline"] = {
        "pass": demo_count is not None
        and demo_count > 0
        and guess_fraction < 1e-6
        and all_failed,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_fraction": guess_fraction,
        "demo_n": demo["n"],
        "demo_exact_solution_count": demo_count,
        "demo_count_wall_seconds": round(demo_count_wall, 6),
        "baseline_name": "balanced DSATUR",
        "baseline_attempts": 8,
        "baseline_successes": attack_results["balanced_DSatur_300k"]["successes"],
        "baseline_nodes_average": round(sum(x["nodes"] for x in dsatur_stats) / 8),
        "baseline_nodes_max": max(x["nodes"] for x in dsatur_stats),
        "baseline_wall_seconds_average": round(
            sum(x["wall_seconds"] for x in dsatur_stats) / 8, 6
        ),
        "baseline_wall_seconds_max": round(
            max(x["wall_seconds"] for x in dsatur_stats), 6
        ),
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=31337, **doubled_params)
    report["G7_scales"] = {
        "pass": verify(doubled, doubled["answer"])[0]
        and search_space(doubled) > search_space(inst),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "shipping_core_edges": len(inst["core_edges"]),
        "doubled_core_edges": len(doubled["core_edges"]),
        "search_space_increased": search_space(doubled) > search_space(inst),
    }

    invariance_checks = 0
    carried_checks = 0
    unrelated_keys = set()
    for seed in range(20):
        original = make_instance(seed=80_000 + seed, **shipping_params)
        base_key = canonical_key(original)
        unrelated_keys.add(base_key)
        permutation = list(range(original["n"]))
        random.Random(90_000 + seed).shuffle(permutation)
        variants = []
        reordered = dict(original)
        reordered["core_edges"] = list(reversed(original["core_edges"]))
        variants.append(reordered)
        variants.append(_relabel_instance(original, permutation, False))
        variants.append(_relabel_instance(original, permutation, True))
        for variant in variants:
            invariance_checks += 1
            if canonical_key(variant) != base_key:
                raise AssertionError("canonical key changed under a graph relabeling")
            carried_checks += int(verify(variant, variant["answer"])[0])
    report["G8_canonical_key"] = {
        "pass": invariance_checks == 60
        and carried_checks == 60
        and len(unrelated_keys) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated": len(unrelated_keys),
        "unrelated_attempts": 20,
        "symmetries": [
            "core-edge input reordering",
            "arbitrary original-vertex relabeling",
            "composition of relabeling and edge reordering",
        ],
        "key_kind": "strong local isomorphism invariant, not full canonical labeling",
    }

    answer_blob = json.dumps(inst["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    intended_operations = inst["n"] + 5
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_minus_placebo = (
            arms["hinted"]["solved"] / arms["hinted"]["attempts"]
            - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        )
    else:
        hinted_minus_placebo = None
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "operation_accounting": (
            "one class assignment per original vertex plus five color-name choices "
            "after recognizing the latent decomposition"
        ),
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
