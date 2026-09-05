"""Verified generator for pre-assignment uniquification of Vertex Cover.

The construction follows the bipartite reduction in Section 3 of
arXiv:2312.10599.  A planted independent dominating set D in a regular
bipartite core G is known before the instance is built.  Attaching one private
leaf v' to each core vertex v gives G'; Lemma 4 proves that excluding D leaves
exactly one minimum vertex cover of G'.
"""

from __future__ import annotations

import collections
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
except ImportError:                 # pragma: no cover - no helper is needed
    exact_matrices = rationals = None


TRACK = "A"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "regular bipartite graph with a distinguished core and one private leaf per core vertex",
        "Exclude pre-assignment for minimum vertex cover",
    ],
    "verification_operations": [
        "pendant-pair consistency check",
        "core-edge adjacency lookup",
        "independence check",
        "closed-neighborhood domination check",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3, Lemmas 4 and 5 and Theorem 4: the pendant-corona "
        "reduction from bipartite Independent Dominating Set to PAU-VC"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Across the two core colour classes the wanted vertices are the two "
        "shores of a small maximal all-zero rectangle; without closing both "
        "shores under non-neighborhoods one must branch over core subsets."
    ),
    "hardness_basis": (
        "Track A: Section 3, Theorem 4 proves NP-completeness for bipartite "
        "PAU-VC via exactly the pendant-corona regime, while the augmented "
        "vertex-cover number grows with n outside the paper's small-tau easy "
        "regime; on the regular planted distribution at the shipping preset, "
        "the measured capped DPLL-style independent-domination search and the "
        "construction-aware attacks in G5--G6 find no witness."
    ),
    "max_answer_tokens": 18,
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
        "A strictly increasing JSON list of between 1 and k distinct vertex "
        "labels, all from the displayed core W.  It denotes vertices forbidden "
        "from the minimum vertex cover."
    ),
    "bounds": {
        "length_min": 1,
        "length_max": "instance k",
        "entries": "distinct labels from the instance's core W",
        "order": "strictly increasing canonical order",
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 8, "k": 2, "core_degree": 3, "incidence_high": 1},
    "easy": {"n": 240, "k": 16, "core_degree": 20, "incidence_high": 3},
    "medium": {"n": 256, "k": 16, "core_degree": 21, "incidence_high": 3},
    "hard": {"n": 272, "k": 16, "core_degree": 23, "incidence_high": 3},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "In the core bipartition, the target is a small maximal all-zero rectangle "
    "under the cross-shore adjacency relation."
)
PLACEBO_HINT = (
    "Keep the vertex labels in increasing order and check the listed pairs "
    "carefully before committing to the final set."
)

# Filled from the script-owned runs after STEP 4 and the two G9 scratch runs.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unavailable: OpenRouter key limit exhausted",
}

NOTES = r"""
Definition.  Section 2 defines an Exclude pre-assignment X as feasible when
exactly one minimum vertex cover avoids X.  The size is |X|.  Section 3's
bipartite reduction is the decisive construction: from a bipartite core G it
forms G' by giving every core vertex a private leaf.  Lemma 4 proves that an
independent dominating set D of G makes (empty,D) feasible, and its proof
writes the unique compatible cover as (V(G)-D) union {the private mates of D}.
Lemma 5 proves the converse after canonicalising a mixed pre-assignment.

Step-0 algorithm check.  Candidate verification on a bipartite graph is
polynomial by Corollary 1 and Hopcroft--Karp.  That does not solve the search:
Theorem 4 proves the Exclude/Mixed problem NP-complete via the pendant
bipartite graphs used here.  The paper gives O(1.9181^n) time on bipartite
graphs and O*(3.6791^tau) when parameterised by vertex-cover number; it warns
that small tau is the easy generation regime.  The presets therefore keep k
fixed for writable answers while growing a dense core whose augmented graph
has tau=n and use a capped exact branching implementation as the standard
attack.  This is Track A, subject to the empirical distribution checks.

Generation.  D is sampled first, half from each side of an internal balanced
bipartition.  Edges between the two selected halves are forbidden.  Each
unselected vertex receives either one or three random selected neighbors on
the opposite shore, certifying domination.  A separately randomised
degree-sequence graph on the two unselected shores fills every remaining
degree.  Consequently every core vertex has exactly core_degree neighbors:
planted vertices are not degree outliers, and the old one-neighbor
construction's pairwise-disjoint-neighborhood fingerprint is absent.
Degree-preserving switches randomise all three blocks before all public labels
are uniformly permuted.  The certificate is known by inverse generation and
Lemma 4; no instance is solved.

Attack handling.  Plants and decoys occupy uniformly random core positions and
all have exactly the same degree.  The panel tests degree outliers,
deterministic domination-gain greedy, randomized greedy restarts, one-shore
maximum-coverage descent, a construction-aware low-codegree descent, centered
biadjacency power iteration, and capped exact branch-and-propagate search for a
size-k independent dominating set.  The latter is the domain-standard attack
for the paper's reduction.  The canonical key hashes relabelling-invariant
codegree profiles of the marked core; it is not a complete isomorphism test.
""".strip()


def _choose_weighted_subset(rng: random.Random, population: list[int], size: int) -> list[int]:
    return rng.sample(population, size)


def _add_edge(edges: set[tuple[int, int]], a: int, b: int) -> None:
    if a == b:
        raise ValueError("loops are not allowed")
    edges.add((a, b) if a < b else (b, a))


def _add_degree_sequence_bipartite(
        edges: set[tuple[int, int]], left: list[int], right: list[int],
        left_degrees: list[int], right_degrees: list[int],
        rng: random.Random, *, switch_factor: int = 24) -> None:
    """Add a randomized simple bipartite degree-sequence realization.

    Bipartite Havel--Hakimi supplies a realization; random legal two-edge
    switches then erase its deterministic ordering while preserving every
    degree.  All random choices use the instance-local RNG.
    """
    if (len(left) != len(left_degrees) or len(right) != len(right_degrees)
            or sum(left_degrees) != sum(right_degrees)
            or any(d < 0 or d > len(right) for d in left_degrees)
            or any(d < 0 or d > len(left) for d in right_degrees)):
        raise ValueError("invalid bipartite degree sequence")

    remaining = dict(zip(right, right_degrees))
    pending = list(zip(left, left_degrees))
    rng.shuffle(pending)
    pending.sort(key=lambda item: item[1], reverse=True)
    block: set[tuple[int, int]] = set()
    for u, degree in pending:
        choices = list(right)
        rng.shuffle(choices)
        choices.sort(key=lambda v: remaining[v], reverse=True)
        selected = choices[:degree]
        if degree and (len(selected) != degree or remaining[selected[-1]] <= 0):
            raise ValueError("nongraphical bipartite degree sequence")
        for v in selected:
            block.add((u, v))
            remaining[v] -= 1
    if any(remaining.values()):
        raise ValueError("nongraphical bipartite degree sequence")

    edge_list = list(block)
    for _ in range(switch_factor * len(edge_list)):
        if len(edge_list) < 2:
            break
        i = rng.randrange(len(edge_list))
        j = rng.randrange(len(edge_list))
        if i == j:
            continue
        a, b = edge_list[i]
        c, d = edge_list[j]
        if a == c or b == d or (a, d) in block or (c, b) in block:
            continue
        block.remove((a, b))
        block.remove((c, d))
        block.add((a, d))
        block.add((c, b))
        edge_list[i] = (a, d)
        edge_list[j] = (c, b)

    for u, v in block:
        _add_edge(edges, u, v)


def _recommended_core_degree(n: int, k: int, incidence_high: int = 3) -> int:
    """Choose a roughly one-sixth-dense feasible degree for escalation."""
    side = n // 2
    half = k // 2
    other = side - half
    target = max(1, round(side / 6))
    for delta in range(side + 1):
        for degree in ({target} if delta == 0 else {target - delta, target + delta}):
            if degree < 1 or degree >= side:
                continue
            extra = half * degree - other
            if incidence_high == 1:
                if extra == 0:
                    return degree
            elif (0 <= extra <= (incidence_high - 1) * other
                  and extra % (incidence_high - 1) == 0):
                return degree
    raise ValueError("no feasible core degree for these parameters")


def make_instance(n: int, seed: int = 0, *, k: int = 16,
                  core_degree: int | None = None,
                  incidence_high: int = 3, **params) -> dict:
    """Build a certified PAU-VC instance by the paper's pendant reduction."""
    del params
    if not isinstance(n, int) or n < 8 or n % 2:
        raise ValueError("n must be an even integer at least 8")
    if not isinstance(k, int) or k < 2 or k % 2 or k >= n // 2:
        raise ValueError("k must be even, at least 2, and smaller than n/2")
    side = n // 2
    half = k // 2
    other = side - half
    if not isinstance(incidence_high, int) or incidence_high < 1 or incidence_high > half:
        raise ValueError("incidence_high must lie between 1 and k/2")
    if core_degree is None:
        core_degree = _recommended_core_degree(n, k, incidence_high)
    if (not isinstance(core_degree, int) or core_degree < 1
            or core_degree >= side or core_degree < incidence_high):
        raise ValueError("core_degree is invalid for the bipartition")

    # Each decoy has either one or incidence_high planted neighbors.  The
    # count of high-incidence decoys is forced by degree conservation: all
    # `half` planted vertices must themselves have degree core_degree.
    extra = half * core_degree - other
    if incidence_high == 1:
        if extra != 0:
            raise ValueError("incidence_high=1 requires half*degree=side-half")
        high_count = 0
    else:
        stride = incidence_high - 1
        if extra < 0 or extra > stride * other or extra % stride:
            raise ValueError("degree does not yield an integral incidence mixture")
        high_count = extra // stride

    rng = random.Random(seed)
    left = list(range(side))
    right = list(range(side, n))
    d_left = set(_choose_weighted_subset(rng, left, half))
    d_right = set(_choose_weighted_subset(rng, right, half))
    other_left = [v for v in left if v not in d_left]
    other_right = [v for v in right if v not in d_right]

    left_incidence = ([incidence_high] * high_count
                      + [1] * (other - high_count))
    right_incidence = list(left_incidence)
    rng.shuffle(left_incidence)
    rng.shuffle(right_incidence)

    core_edges: set[tuple[int, int]] = set()
    _add_degree_sequence_bipartite(
        core_edges, sorted(d_left), other_right,
        [core_degree] * half, right_incidence, rng)
    _add_degree_sequence_bipartite(
        core_edges, other_left, sorted(d_right),
        left_incidence, [core_degree] * half, rng)
    _add_degree_sequence_bipartite(
        core_edges, other_left, other_right,
        [core_degree - value for value in left_incidence],
        [core_degree - value for value in right_incidence], rng)

    # This is a construction check, not a search: every core vertex must be
    # exactly regular, and the sampled D must dominate the rest.
    built_degree = [0] * n
    for u, v in core_edges:
        built_degree[u] += 1
        built_degree[v] += 1
    if any(value != core_degree for value in built_degree):  # pragma: no cover
        raise RuntimeError("degree-sequence construction lost regularity")

    # Paper's G -> G': one private leaf for every core vertex.
    edges = set(core_edges)
    private_pairs = []
    for v in range(n):
        leaf = n + v
        _add_edge(edges, v, leaf)
        private_pairs.append((v, leaf))

    # Conceal construction positions by a uniform relabelling of the entire
    # augmented graph.  The marked core and private pairing remain public.
    labels = list(range(2 * n))
    rng.shuffle(labels)
    relabel = {old: labels[old] for old in range(2 * n)}
    public_edges = sorted(
        (min(relabel[a], relabel[b]), max(relabel[a], relabel[b]))
        for a, b in edges
    )
    public_core = sorted(relabel[v] for v in range(n))
    public_pairs = sorted((relabel[v], relabel[n + v]) for v in range(n))
    answer = sorted(relabel[v] for v in d_left | d_right)

    return {
        "vertex_count": 2 * n,
        "core_n": n,
        "k": k,
        "core_degree": core_degree,
        "incidence_high": incidence_high,
        "core_vertices": public_core,
        "private_pairs": [list(pair) for pair in public_pairs],
        "edges": [list(edge) for edge in public_edges],
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the complete problem, with hints disabled by default."""
    core = " ".join(map(str, inst["core_vertices"]))
    pairs = "\n".join(f"{a} {b}" for a, b in inst["private_pairs"])
    edges = "\n".join(f"{a} {b}" for a, b in inst["edges"])
    text = f"""PRE-ASSIGNMENT FOR A UNIQUE MINIMUM VERTEX COVER

The undirected simple graph below has vertices 0 through {inst['vertex_count'] - 1}.
A vertex cover is a set C such that every edge has at least one endpoint in C.
A minimum vertex cover has the smallest possible cardinality.

An Exclude pre-assignment is a set X of vertices.  It is feasible when exactly
one minimum vertex cover C satisfies C intersection X = empty.

This graph has a distinguished bipartite core W in which every core vertex has
exactly {inst['core_degree']} core neighbors.  The two color classes are not
listed, but can be recovered by 2-coloring the core.  Every core vertex w has
one private leaf w', joined only to w; the private pairs are listed below.  For
this promised form, a set X contained in W is a feasible Exclude pre-assignment
exactly when X is an independent dominating set of the core: no edge with both
endpoints in W has both endpoints in X, and every vertex of W is either in X or
has a core neighbor in X.

Find a nonempty feasible Exclude pre-assignment X contained in W with |X| at
most {inst['k']}.  Vertex labels may not repeat.  Inside the answer tags list them
as decimal integers in strictly increasing order, separated only by commas.

CORE W ({inst['core_n']} vertices)
{core}

PRIVATE PAIRS (core leaf)
{pairs}

EDGES ({len(inst['edges'])} edges)
{edges}

Give your final answer inside <answer></answer> tags, as a comma-separated list
of 1 through {inst['k']} strictly increasing core-vertex labels.
Example of syntax only (not claimed feasible): <answer>{inst['core_vertices'][0]}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def parse_answer(text: str) -> object | None:
    """Extract the last tagged comma-separated integer list."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    if not matches:
        return None
    body = matches[-1].strip()
    # Tolerate a markdown fence placed inside the required tags.
    body = re.sub(r"^```(?:text|json|python)?\s*", "", body,
                  flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body).strip()
    if not body:
        return []
    if not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", body):
        return None
    try:
        return [int(piece.strip()) for piece in body.split(",")]
    except (TypeError, ValueError):
        return None


def _core_adjacency(inst: dict) -> tuple[list[int], dict[int, set[int]]]:
    core = list(inst["core_vertices"])
    core_set = set(core)
    adjacency = {v: set() for v in core}
    for raw in inst["edges"]:
        if not isinstance(raw, (list, tuple)) or len(raw) != 2:
            continue
        a, b = raw
        if a in core_set and b in core_set:
            adjacency[a].add(b)
            adjacency[b].add(a)
    return core, adjacency


def _pendant_structure_ok(inst: dict) -> tuple[bool, str]:
    """Execute the reduction promise instead of trusting hidden generator state."""
    vertex_count = inst.get("vertex_count")
    core = inst.get("core_vertices")
    pairs = inst.get("private_pairs")
    raw_edges = inst.get("edges")
    if not isinstance(vertex_count, int) or vertex_count < 1:
        return False, "instance has an invalid vertex count"
    if not isinstance(core, list) or len(core) != inst.get("core_n"):
        return False, "instance has an invalid displayed core"
    if len(set(core)) != len(core) or any(
            not isinstance(v, int) or isinstance(v, bool)
            or v < 0 or v >= vertex_count for v in core):
        return False, "instance has invalid core labels"
    if not isinstance(pairs, list) or len(pairs) != len(core):
        return False, "instance has an invalid private-pair list"
    core_set = set(core)
    leaves: set[int] = set()
    paired: dict[int, int] = {}
    for pair in pairs:
        if (not isinstance(pair, (list, tuple)) or len(pair) != 2
                or pair[0] not in core_set):
            return False, "a private pair does not start with its core vertex"
        u, leaf = pair
        if (not isinstance(leaf, int) or isinstance(leaf, bool)
                or leaf < 0 or leaf >= vertex_count or leaf in core_set
                or u in paired or leaf in leaves):
            return False, "private pairs are not a one-to-one core/leaf pairing"
        paired[u] = leaf
        leaves.add(leaf)
    if core_set | leaves != set(range(vertex_count)):
        return False, "core vertices and private leaves do not partition the graph"
    if not isinstance(raw_edges, list):
        return False, "instance edge list is malformed"
    edge_set: set[tuple[int, int]] = set()
    degree = [0] * vertex_count
    for edge in raw_edges:
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            return False, "instance edge list is malformed"
        a, b = edge
        if (not isinstance(a, int) or isinstance(a, bool)
                or not isinstance(b, int) or isinstance(b, bool)
                or a < 0 or b < 0 or a >= vertex_count or b >= vertex_count
                or a == b):
            return False, "instance contains an invalid edge"
        key = (a, b) if a < b else (b, a)
        if key in edge_set:
            return False, "instance contains a repeated edge"
        edge_set.add(key)
        degree[a] += 1
        degree[b] += 1
        if a in leaves and b in leaves:
            return False, "two private leaves are adjacent"
        if (a in leaves) != (b in leaves):
            leaf, owner = (a, b) if a in leaves else (b, a)
            if paired.get(owner) != leaf:
                return False, "a private leaf is joined to the wrong core vertex"
    for owner, leaf in paired.items():
        key = (owner, leaf) if owner < leaf else (leaf, owner)
        if key not in edge_set or degree[leaf] != 1:
            return False, "a listed private leaf is not degree one"
    return True, "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check an arbitrary allowed witness without consulting inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a list of vertex labels"
    if not answer:
        return False, "pre-assignment must be nonempty"
    if len(answer) > inst["k"]:
        return False, f"pre-assignment has more than k={inst['k']} vertices"
    if any(not isinstance(v, int) or isinstance(v, bool) for v in answer):
        return False, "every vertex label must be an integer"
    if len(set(answer)) != len(answer):
        return False, "vertex labels must not repeat"
    if answer != sorted(answer):
        return False, "vertex labels must be strictly increasing"
    if any(v < 0 or v >= inst["vertex_count"] for v in answer):
        return False, "vertex label is outside the graph's range"
    structure_ok, structure_reason = _pendant_structure_ok(inst)
    if not structure_ok:
        return False, structure_reason
    core, adjacency = _core_adjacency(inst)
    core_set = set(core)
    if any(v not in core_set for v in answer):
        return False, "every selected vertex must belong to the displayed core W"
    chosen = set(answer)
    for u in answer:
        if adjacency[u] & chosen:
            return False, "selected core vertices are not independent"
    for v in core:
        if v not in chosen and not (adjacency[v] & chosen):
            return False, f"selected vertices do not dominate core vertex {v}"
    return True, "ok"


def _unrank_combination(n: int, r: int, rank: int) -> list[int]:
    out: list[int] = []
    start = 0
    for remaining in range(r, 0, -1):
        for value in range(start, n):
            count = math.comb(n - value - 1, remaining - 1)
            if rank < count:
                out.append(value)
                start = value + 1
                break
            rank -= count
    return out


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniform sample from all nonempty core subsets of cardinality at most k."""
    n = len(inst["core_vertices"])
    counts = [math.comb(n, size) for size in range(1, inst["k"] + 1)]
    rank = rng.randrange(sum(counts))
    size = 1
    for count in counts:
        if rank < count:
            break
        rank -= count
        size += 1
    # Conditional on `size`, an independent uniform combination remains a
    # uniform draw from the same bounded language and is much cheaper than
    # walking the combinatorial-number-system rank for every G4 sample.
    positions = sorted(rng.sample(range(n), size))
    return [inst["core_vertices"][i] for i in positions]


def search_space(inst: dict) -> int:
    n = len(inst["core_vertices"])
    return sum(math.comb(n, size) for size in range(1, inst["k"] + 1))


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space > 1_000_000:
        return None
    count = 0
    core = inst["core_vertices"]
    for size in range(1, inst["k"] + 1):
        for candidate in itertools.combinations(core, size):
            count += int(verify(inst, list(candidate))[0])
    return count


def canonical_key(inst: dict) -> str:
    """Codegree-profile invariant of the marked core graph (not seed/render)."""
    vertices, adjacency = _core_adjacency(inst)
    pair_histogram: collections.Counter[int] = collections.Counter()
    per_vertex: dict[int, collections.Counter[int]] = {
        v: collections.Counter() for v in vertices
    }
    for i, u in enumerate(vertices):
        for v in vertices[i + 1:]:
            common = len(adjacency[u] & adjacency[v])
            pair_histogram[common] += 1
            per_vertex[u][common] += 1
            per_vertex[v][common] += 1
    vertex_profiles = sorted(
        tuple(sorted(profile.items())) for profile in per_vertex.values()
    )
    payload = {
        "core_n": len(vertices),
        "k": inst["k"],
        "degrees": sorted(len(adjacency[v]) for v in vertices),
        "pair_codegrees": sorted(pair_histogram.items()),
        "vertex_codegree_profiles": vertex_profiles,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the regular core at fixed certificate length and edge density."""
    nxt = dict(params)
    n = int(nxt.get("n", 240))
    if n >= 320:
        return None
    k = int(nxt.get("k", 16))
    incidence_high = int(nxt.get("incidence_high", 3))
    nxt["n"] = min(320, n + 16)
    nxt["core_degree"] = _recommended_core_degree(
        nxt["n"], k, incidence_high)
    return nxt


def _bipartition(vertices: list[int], adjacency: dict[int, set[int]]) -> tuple[list[int], list[int]]:
    color: dict[int, int] = {}
    for start in vertices:
        if start in color:
            continue
        color[start] = 0
        queue = collections.deque([start])
        while queue:
            v = queue.popleft()
            for w in adjacency[v]:
                if w not in color:
                    color[w] = 1 - color[v]
                    queue.append(w)
    return ([v for v in vertices if color[v] == 0],
            [v for v in vertices if color[v] == 1])


def _attack_outlier_degree(inst: dict) -> bool:
    vertices, adjacency = _core_adjacency(inst)
    k = inst["k"]
    ranked = sorted(vertices, key=lambda v: (len(adjacency[v]), v))
    candidates = [ranked[:k], ranked[-k:]]
    # Also try vertices closest to the median degree, since the generator is
    # explicitly degree-balanced.
    degrees = sorted(len(adjacency[v]) for v in vertices)
    median = degrees[len(degrees) // 2]
    candidates.append(sorted(vertices, key=lambda v: (abs(len(adjacency[v]) - median), v))[:k])
    return any(verify(inst, sorted(candidate))[0] for candidate in candidates)


def _greedy_once(inst: dict, rng: random.Random | None = None) -> list[int] | None:
    vertices, adjacency = _core_adjacency(inst)
    chosen: set[int] = set()
    forbidden: set[int] = set()
    dominated: set[int] = set()
    while len(dominated) < len(vertices) and len(chosen) < inst["k"]:
        options = [v for v in vertices if v not in forbidden]
        if not options:
            return None
        scored = []
        for v in options:
            gain = len(({v} | adjacency[v]) - dominated)
            scored.append((gain, -len(adjacency[v]), -v, v))
        scored.sort(reverse=True)
        if rng is None:
            pick = scored[0][3]
        else:
            width = min(6, len(scored))
            weights = list(range(width, 0, -1))
            pick = rng.choices([row[3] for row in scored[:width]], weights=weights, k=1)[0]
        chosen.add(pick)
        forbidden.add(pick)
        forbidden.update(adjacency[pick])
        dominated.add(pick)
        dominated.update(adjacency[pick])
    answer = sorted(chosen)
    return answer if verify(inst, answer)[0] else None


def _attack_greedy(inst: dict) -> bool:
    return _greedy_once(inst) is not None


def _attack_random_restart(inst: dict, seed: int, restarts: int = 256) -> bool:
    rng = random.Random(seed)
    return any(_greedy_once(inst, rng) is not None for _ in range(restarts))


def _attack_spectral_zero_block(inst: dict, seed: int) -> bool:
    """Centered bipartite power iteration aimed at the planted zero block."""
    vertices, adjacency = _core_adjacency(inst)
    left, right = _bipartition(vertices, adjacency)
    # The generated cores are connected; retain a defined failure on an
    # unexpected component orientation rather than using hidden information.
    if not left or not right:
        return False
    density = sum(len(adjacency[u]) for u in left) / (len(left) * len(right))
    rng = random.Random(seed)
    x = [rng.uniform(-1.0, 1.0) for _ in left]
    y = [0.0 for _ in right]

    def normalize(vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    # Alternating multiplication by the centered biadjacency matrix is the
    # cheap singular-vector attack a planted-biclique specialist would try.
    for _ in range(40):
        y = [sum(((1.0 if v in adjacency[u] else 0.0) - density) * x[i]
                 for i, u in enumerate(left)) for v in right]
        y = normalize(y)
        x = [sum(((1.0 if v in adjacency[u] else 0.0) - density) * y[j]
                 for j, v in enumerate(right)) for u in left]
        x = normalize(x)
    half = inst["k"] // 2
    left_orders = [
        sorted(range(len(left)), key=lambda i: x[i]),
        sorted(range(len(left)), key=lambda i: -x[i]),
        sorted(range(len(left)), key=lambda i: -abs(x[i])),
    ]
    right_orders = [
        sorted(range(len(right)), key=lambda j: y[j]),
        sorted(range(len(right)), key=lambda j: -y[j]),
        sorted(range(len(right)), key=lambda j: -abs(y[j])),
    ]
    for lo in left_orders:
        for ro in right_orders:
            candidate = sorted([left[i] for i in lo[:half]]
                               + [right[j] for j in ro[:half]])
            if verify(inst, candidate)[0]:
                return True
    return False


def _one_shore_candidate(inst: dict, selected: list[int],
                         opposite: list[int],
                         adjacency: dict[int, set[int]]) -> list[int] | None:
    covered: set[int] = set()
    for vertex in selected:
        covered.update(adjacency[vertex])
    missing = [vertex for vertex in opposite if vertex not in covered]
    candidate = sorted(selected + missing)
    if len(candidate) > inst["k"]:
        return None
    return candidate if verify(inst, candidate)[0] else None


def _attack_one_shore_coverage(inst: dict, seed: int,
                               restarts: int = 128) -> bool:
    """Hill-climb the set-cover view exposed by the bipartite reduction."""
    vertices, adjacency = _core_adjacency(inst)
    shores = _bipartition(vertices, adjacency)
    width = inst["k"] // 2
    rng = random.Random(seed)
    for shore, opposite in (shores, shores[::-1]):
        opposite_index = {v: i for i, v in enumerate(opposite)}
        masks = []
        for vertex in shore:
            mask = 0
            for neighbor in adjacency[vertex]:
                mask |= 1 << opposite_index[neighbor]
            masks.append(mask)
        for _ in range(restarts):
            selected = set(rng.sample(range(len(shore)), width))
            for _step in range(40):
                covered = 0
                for index in selected:
                    covered |= masks[index]
                candidate = _one_shore_candidate(
                    inst, [shore[i] for i in selected], opposite, adjacency)
                if candidate is not None:
                    return True
                score = covered.bit_count()
                best_score = score
                moves: list[tuple[int, int]] = []
                for removed in selected:
                    base = 0
                    for index in selected:
                        if index != removed:
                            base |= masks[index]
                    for added in range(len(shore)):
                        if added in selected:
                            continue
                        changed = (base | masks[added]).bit_count()
                        if changed > best_score:
                            best_score = changed
                            moves = [(removed, added)]
                        elif changed == best_score and changed > score:
                            moves.append((removed, added))
                if not moves:
                    break
                removed, added = rng.choice(moves)
                selected.remove(removed)
                selected.add(added)
    return False


def _attack_low_codegree(inst: dict, seed: int,
                         restarts: int = 128) -> bool:
    """Exploit the old plant's low-overlap fingerprint, if any remains."""
    vertices, adjacency = _core_adjacency(inst)
    shores = _bipartition(vertices, adjacency)
    width = inst["k"] // 2
    rng = random.Random(seed)
    for shore, opposite in (shores, shores[::-1]):
        common = [[0] * len(shore) for _ in shore]
        for i in range(len(shore)):
            for j in range(i):
                value = len(adjacency[shore[i]] & adjacency[shore[j]])
                common[i][j] = common[j][i] = value
        for _ in range(restarts):
            selected = [rng.randrange(len(shore))]
            while len(selected) < width:
                scores = [
                    (sum(common[index][chosen] for chosen in selected), index)
                    for index in range(len(shore)) if index not in selected
                ]
                best = min(score for score, _ in scores)
                selected.append(rng.choice(
                    [index for score, index in scores if score == best]))
            candidate = _one_shore_candidate(
                inst, [shore[i] for i in selected], opposite, adjacency)
            if candidate is not None:
                return True
            while True:
                current = sum(common[selected[i]][selected[j]]
                              for i in range(width) for j in range(i))
                selected_set = set(selected)
                best = current
                moves: list[tuple[int, int]] = []
                for removed in selected:
                    removed_cost = sum(common[removed][other]
                                       for other in selected if other != removed)
                    for added in range(len(shore)):
                        if added in selected_set:
                            continue
                        changed = (current - removed_cost
                                   + sum(common[added][other]
                                         for other in selected
                                         if other != removed))
                        if changed < best:
                            best = changed
                            moves = [(removed, added)]
                        elif changed == best and changed < current:
                            moves.append((removed, added))
                if not moves:
                    break
                removed, added = rng.choice(moves)
                selected.remove(removed)
                selected.append(added)
                candidate = _one_shore_candidate(
                    inst, [shore[i] for i in selected], opposite, adjacency)
                if candidate is not None:
                    return True
    return False


def _exact_ids_search(inst: dict, node_cap: int = 100_000) -> dict:
    """Capped branch-and-propagate search for an IDS of size at most k."""
    vertices, adjacency_sets = _core_adjacency(inst)
    index = {v: i for i, v in enumerate(vertices)}
    n = len(vertices)
    closed = [0] * n
    neighbors = [0] * n
    for i, v in enumerate(vertices):
        bits = 0
        for w in adjacency_sets[v]:
            bits |= 1 << index[w]
        neighbors[i] = bits
        closed[i] = bits | (1 << i)
    all_bits = (1 << n) - 1
    nodes = 0
    solution: list[int] | None = None

    def rec(chosen: tuple[int, ...], forbidden: int, dominated: int) -> None:
        nonlocal nodes, solution
        if solution is not None or nodes >= node_cap:
            return
        nodes += 1
        if dominated == all_bits:
            solution = [vertices[i] for i in chosen]
            return
        if len(chosen) >= inst["k"]:
            return
        selectable = all_bits & ~forbidden
        undominated = all_bits & ~dominated
        best_options = 0
        best_count = n + 1
        scan = undominated
        while scan:
            bit = scan & -scan
            i = bit.bit_length() - 1
            options = closed[i] & selectable
            count = options.bit_count()
            if count == 0:
                return
            if count < best_count:
                best_count = count
                best_options = options
                if count == 1:
                    break
            scan ^= bit
        choices = []
        scan = best_options
        while scan:
            bit = scan & -scan
            u = bit.bit_length() - 1
            gain = (closed[u] & ~dominated).bit_count()
            choices.append((-gain, u))
            scan ^= bit
        for _, u in sorted(choices):
            rec(chosen + (u,), forbidden | closed[u], dominated | closed[u])
            if solution is not None or nodes >= node_cap:
                return

    started = time.perf_counter()
    rec((), 0, 0)
    elapsed = time.perf_counter() - started
    if solution is not None:
        solution.sort()
    return {
        "success": solution is not None and verify(inst, solution)[0],
        "answer": solution,
        "nodes": nodes,
        "node_cap": node_cap,
        "wall_clock_sec": elapsed,
        "cap_reached": nodes >= node_cap and solution is None,
    }


def _relabel_instance(inst: dict, seed: int) -> dict:
    rng = random.Random(seed)
    order = list(range(inst["vertex_count"]))
    rng.shuffle(order)
    mapping = {old: order[old] for old in range(inst["vertex_count"])}
    moved = {key: value for key, value in inst.items()
             if key not in {"core_vertices", "private_pairs", "edges", "answer"}}
    moved["core_vertices"] = [mapping[v] for v in reversed(inst["core_vertices"])]
    moved["private_pairs"] = [
        [mapping[a], mapping[b]] for a, b in reversed(inst["private_pairs"])
    ]
    moved["edges"] = [
        [mapping[b], mapping[a]] for a, b in reversed(inst["edges"])
    ]
    moved["answer"] = sorted(mapping[v] for v in inst["answer"])
    return moved


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))
    return len(encoded), math.ceil(len(encoded) / 4), len(answer) if isinstance(answer, list) else 0


def _is_ids(candidate: list[int], core: list[int],
            adjacency: dict[int, set[int]]) -> bool:
    """Fast exact IDS predicate after the instance promise was checked once."""
    chosen = set(candidate)
    return (all(not (adjacency[v] & chosen) for v in candidate)
            and all(v in chosen or bool(adjacency[v] & chosen) for v in core))


def selftest() -> dict:
    report: dict = {}

    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2026):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            checks += 1
            if not (ok and json_ok):
                failures.append({"preset": preset, "seed": seed,
                                 "reason": reason, "json_native": json_ok})
    report["G1_planted_verifies"] = {
        "pass": not failures, "checks": checks, "failures": failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **ship_params)
    answer = inst["answer"]
    corruptions = {
        "drop_one": answer[:-1],
        "swap_two": [answer[1], answer[0]] + answer[2:],
        "duplicate": answer[:-1] + [answer[-2]],
        "empty": [],
        "out_of_range": answer[:-1] + [inst["vertex_count"]],
    }
    rejections = {}
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        rejections[name] = {"rejected": not ok, "reason": reason}
    reasons = [row["reason"] for row in rejections.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in rejections.values())
                and len(set(reasons)) == len(reasons),
        "rejections": rejections,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "I checked independence and domination.\n```text\nwork omitted\n```\n"
        f"<answer> {','.join(map(str, answer))} </answer>\n"
        "These labels are in increasing order."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0]
                and parse_answer("garbage") is None,
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    rng = random.Random(0x231210599)
    total = 200_000
    hits = 0
    structure_ok, structure_reason = _pendant_structure_ok(inst)
    guess_core, guess_adjacency = _core_adjacency(inst)
    predicate_cross_checks = 0
    started = time.perf_counter()
    for sample_index in range(total):
        candidate = random_candidate(inst, rng)
        fast_ok = structure_ok and _is_ids(candidate, guess_core, guess_adjacency)
        hits += int(fast_ok)
        if sample_index < 100:
            predicate_cross_checks += int(fast_ok == verify(inst, candidate)[0])
    sample_seconds = time.perf_counter() - started
    probability = hits / total
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6 and structure_ok
                and predicate_cross_checks == 100,
        "hits": hits,
        "total": total,
        "empirical_probability": probability,
        "candidate_space": search_space(inst),
        "prior": "uniform over every nonempty core subset of size at most k",
        "instance_structure_check": structure_reason,
        "fast_predicate_matches_verify": f"{predicate_cross_checks}/100",
        "sampling_wall_seconds": sample_seconds,
    }

    exact_node_cap = 3_000_000
    baseline = _exact_ids_search(inst, node_cap=exact_node_cap)
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": probability < 1e-6 and not baseline["success"]
                and demo_count is not None and demo_count >= 1,
        "shipping_observed_valid_fraction": probability,
        "shipping_density_sample_count": total,
        "shipping_valid_hits": hits,
        "shipping_candidate_space": search_space(inst),
        "shipping_exact_valid_count": None,
        "baseline_wall_seconds": baseline["wall_clock_sec"],
        "baseline_nodes": baseline["nodes"],
        "baseline_node_cap": baseline["node_cap"],
        "baseline_cap_reached": baseline["cap_reached"],
        "baseline_successes": int(baseline["success"]),
        "demo_exact_valid_count": demo_count,
    }

    attack_successes = {
        "outlier_core_degree": 0,
        "greedy_maximum_domination_gain": 0,
        "random_restart_256_greedy": 0,
        "one_shore_coverage_descent_128": 0,
        "construction_low_codegree_descent_128": 0,
        "spectral_centered_zero_block": 0,
        "exact_ids_branch_and_propagate_3m": 0,
    }
    exact_costs = []
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **ship_params)
        attack_successes["outlier_core_degree"] += int(_attack_outlier_degree(trial))
        attack_successes["greedy_maximum_domination_gain"] += int(_attack_greedy(trial))
        attack_successes["random_restart_256_greedy"] += int(
            _attack_random_restart(trial, seed, restarts=256))
        attack_successes["one_shore_coverage_descent_128"] += int(
            _attack_one_shore_coverage(trial, seed, restarts=128))
        attack_successes["construction_low_codegree_descent_128"] += int(
            _attack_low_codegree(trial, seed, restarts=128))
        attack_successes["spectral_centered_zero_block"] += int(
            _attack_spectral_zero_block(trial, seed))
        exact = _exact_ids_search(trial, node_cap=exact_node_cap)
        attack_successes["exact_ids_branch_and_propagate_3m"] += int(exact["success"])
        exact_costs.append(exact)
    report["G6_adversary_panel"] = {
        "pass": all(value == 0 for value in attack_successes.values()),
        "attacks": {
            name: {"successes": successes, "attempts": 8}
            for name, successes in attack_successes.items()
        },
        "standard_attack_cost": {
            "name": "capped exact independent-domination branch and propagation",
            "complexity": "exponential worst case",
            "nodes_total": sum(row["nodes"] for row in exact_costs),
            "nodes_mean": sum(row["nodes"] for row in exact_costs) / 8,
            "wall_clock_sec_total": sum(row["wall_clock_sec"] for row in exact_costs),
            "wall_clock_sec_mean": sum(row["wall_clock_sec"] for row in exact_costs) / 8,
            "caps_reached": sum(int(row["cap_reached"]) for row in exact_costs),
        },
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] = 2 * ship_params["n"]
    doubled_params["core_degree"] = _recommended_core_degree(
        doubled_params["n"], doubled_params["k"],
        doubled_params["incidence_high"])
    started = time.perf_counter()
    doubled = make_instance(seed=7, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    doubled_seconds = time.perf_counter() - started
    spaces = [search_space(make_instance(seed=9, **params))
              for name, params in DIFFICULTY.items() if name != "demo"]
    report["G7_scales"] = {
        "pass": doubled_ok and spaces == sorted(spaces)
                and len(set(spaces)) == len(spaces),
        "shipping_core_n": ship_params["n"],
        "doubled_core_n": doubled_params["n"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "doubled_build_and_verify_seconds": doubled_seconds,
        "named_candidate_spaces": spaces,
        "answer_length_fixed": ship_params["k"],
    }

    invariant = True
    invariance_checks = 0
    transform_checks = 0
    for seed in range(20):
        trial = make_instance(seed=10_000 + seed, **ship_params)
        key = canonical_key(trial)
        moved_once = _relabel_instance(trial, seed + 1)
        transformations = [
            moved_once,
            _relabel_instance(trial, 1000 + seed),
            _relabel_instance(trial, 2000 + seed),
            _relabel_instance(moved_once, 3000 + seed),
        ]
        for moved in transformations:
            invariance_checks += 1
            invariant &= canonical_key(moved) == key
            transform_checks += 1
            invariant &= verify(moved, moved["answer"])[0]
    unrelated = {
        canonical_key(make_instance(seed=20_000 + seed, **ship_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariant and len(unrelated) == 20,
        "invariance_checks": invariance_checks,
        "real_transformation_verify_checks": transform_checks,
        "distinct_unrelated_keys": len(unrelated),
        "unrelated_instances": 20,
        "symmetries": ["arbitrary vertex relabelling", "edge-order reversal",
                       "core-list and private-pair reordering"],
        "key_kind": "marked-core codegree-profile invariant",
    }

    chars, tokens, elements = _answer_metrics(answer)
    # After identifying one shore of the maximal zero rectangle, at most k/2
    # neighborhood unions recover the other shore.  Two more unions/checks per
    # selected vertex certify independence and domination.  Scanning and
    # serialising labels are not exact arithmetic.
    intended_operations = 4 * inst["k"] + 8
    arms = {name: dict(G9_EVIDENCE[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = chars <= 2000 and elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        # Since 2026-09-05 the three oracle arms, including the hinted arm,
        # are diagnostic.  Only the answer/route caps are a gate.
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship_params)
    report["certificate_language"] = CERTIFICATE_LANGUAGE
    report["problem_profile"] = PROBLEM_PROFILE
    report["all_passed"] = all(
        value.get("pass", False) for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
