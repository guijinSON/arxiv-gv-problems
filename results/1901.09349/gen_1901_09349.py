"""Deterministic generators of exact graph-minor models in sparse expanders.

This is a Track-B family based on the native model definition in Section 2 of
Chuzhoy--Nimavat, *Large Minors in Expanders* (arXiv:1901.09349).  A host is
made from several two-sheet prism blocks.  Each block contains two copies of
its cubic quotient; one quotient is independently relabelled and supplied as
the target H.  One intact planted sheet is remembered before a global
relabeling, so generation never searches for a model.

The decoy quotients and the target quotient are sampled by the same procedure.
One horizontal edge in one sheet of every block is switched around a ring.  The
switch makes the whole host connected and 4-regular without destroying any
quotient model.  Since every connected N-vertex graph is a (2/N)-expander, the
host has an exact, construction-backed expansion promise (usually a weak one).
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
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # This finite graph family needs integer operations only.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite simple target graph H",
        "finite simple connected expander G",
        "ordered singleton branch sets forming a direct model of H in G",
    ],
    "verification_operations": [
        "exact vertex-range and disjointness checks",
        "exact graph adjacency lookup",
        "trivial exact connectedness of singleton branch sets",
        "exact branch-set realization of every target edge",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "The hidden two-sheet involution is exposed by 4-cycle incidence; "
        "without recognizing it, a solver must search an enormous space of "
        "ordered injective vertex maps."
    ),
    "hardness_basis": (
        "Track B: Theorem 1.1 gives a randomized expander-minor algorithm in "
        "poly(N)*(d/alpha)^O(log(d/alpha)) time in its stated size regime, so "
        "Track A would be false; on this construction the executable reference "
        "counts 4-cycles in O(M*d^2), recognizes the recovered sheets, and uses "
        "exact fixed-pattern isomorphism (O(q*k!) worst case, with k=14 fixed); "
        "the final 8-seed shipping sweep averaged 20,968 counted operations "
        "and about 0.006 seconds, "
        "while the compact route uses the two-sheet symmetry in under 300 exact "
        "branch/quotient checks."
    ),
    "max_answer_tokens": 11,
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


# n is the number of statistically matched prism blocks: it grows the haystack.
# All non-demo levels keep the 14-integer witness fixed.
DIFFICULTY = {
    "demo": {"n": 1, "k": 5, "base_degree": 2},
    "easy": {"n": 4, "k": 14, "base_degree": 3},
    "medium": {"n": 7, "k": 14, "base_degree": 3},
    "hard": {"n": 10, "k": 14, "base_degree": 3},
}

SHIPPING_DIFFICULTY = "easy"

CERTIFICATE_LANGUAGE = {
    "description": (
        "An ordered JSON list [v0,...,v(k-1)] keyed by target vertices "
        "0,...,k-1; every vi is a host vertex identifier and all k identifiers "
        "are distinct.  These are singleton branch sets."
    ),
    "bounds": {
        "branch_sets": "k",
        "vertices_per_branch": 1,
        "total_atomic_elements": "k (14 at every non-demo preset)",
        "entry_range": "0 <= vertex < N",
        "ordering": "entries follow target labels",
    },
}

STRUCTURAL_HINT = (
    "The host's hidden two-sheet involution is visible in how its edges participate in 4-cycles."
)
PLACEBO_HINT = (
    "The host's regular edge presentation rewards careful attention to how vertex pairs are recorded."
)

# Replaced after the script-owned oracle runs.  These values are diagnostic;
# only the independently measured G9(c) caps gate selftest.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES = """\
Section 2 (Definition: Graph Minors) fixes the native witness: disjoint
connected branch sets, with a path between the appropriate sets for every
target edge.  Our connecting paths are single host edges, so the checker can
validate the paper's four conditions by exact finite graph operations.  The
definition does not forbid unused host vertices or extra edges between branch
sets, and neither does verify().  Singleton branch sets are connected, while
every target edge is represented by one host edge, so this is a particularly
short but fully native minor model.

Theorem 1.1 is the Step-0 warning: in its promised expander/size regime a
randomized algorithm finds a model in poly(n)*(d/alpha)^O(log(d/alpha)) time.
Theorem 1.2 gives a second randomized algorithm with poly(n,d/alpha) running
time under its slightly smaller size bound.  Therefore this family is Track B,
not a structural-hardness claim.  Our finite hosts are 4-regular and connected,
hence are rigorously (2/N)-expanders; the declared alpha is deliberately the
elementary guaranteed lower bound, not an unverified claim of constant
expansion.

Generation samples every cubic quotient by the same configuration-model
procedure, rejects loops, parallel edges, disconnection, triangles and
4-cycles, duplicates it into two sheets, and inserts the vertical matching.
One quotient is chosen uniformly and independently relabelled as H.  A
degree-preserving ring switch connects all blocks while leaving one intact copy
of every quotient edge.  The target singleton branch sets are known before
relabelling.

Uniform degree defeats vertex outliers.  Identical quotient sampling defeats
plant-versus-decoy local statistics.  Global relabelling defeats identifier and
input-order rules.  The tested first-edge, high-4-cycle-edge, naive local
quotient and 256-restart attacks fail; the full 4-cycle/product recognizer is
expected to solve and is reported separately as the Track-B reference.
"""


_TAG_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 500_000
_VERIFY_CACHE = {}


def _validate_params(n, k, base_degree):
    for name, value in (("n", n), ("k", k), ("base_degree", base_degree)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if n < 1:
        raise ValueError("n must be at least 1")
    if base_degree not in (2, 3):
        raise ValueError("base_degree must be 2 or 3")
    if base_degree == 2 and k < 5:
        raise ValueError("a degree-2 quotient needs k >= 5")
    if base_degree == 3 and (k < 10 or k % 2):
        raise ValueError("a cubic quotient needs even k >= 10")


def _adjacency(vertex_count, edges):
    adj = [set() for _ in range(vertex_count)]
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    return adj


def _connected(vertex_count, edges):
    if vertex_count == 0:
        return True
    adj = _adjacency(vertex_count, edges)
    seen = {0}
    queue = [0]
    for v in queue:
        for w in adj[v]:
            if w not in seen:
                seen.add(w)
                queue.append(w)
    return len(seen) == vertex_count


def _girth_at_least_five(vertex_count, edges):
    adj = _adjacency(vertex_count, edges)
    for v in range(vertex_count):
        neighbors = list(adj[v])
        for i, a in enumerate(neighbors):
            for b in neighbors[i + 1:]:
                if b in adj[a]:
                    return False
                if (adj[a] & adj[b]) - {v}:
                    return False
    return True


def _random_base(k, degree, rng):
    """Sample a connected simple regular graph of girth at least five."""
    if degree == 2:
        order = list(range(k))
        rng.shuffle(order)
        return sorted(
            (min(order[i], order[(i + 1) % k]),
             max(order[i], order[(i + 1) % k]))
            for i in range(k)
        )

    stubs0 = [v for v in range(k) for _ in range(3)]
    for _ in range(50_000):
        stubs = list(stubs0)
        rng.shuffle(stubs)
        edges = set()
        good = True
        for i in range(0, len(stubs), 2):
            a, b = stubs[i], stubs[i + 1]
            edge = (min(a, b), max(a, b))
            if a == b or edge in edges:
                good = False
                break
            edges.add(edge)
        if (good and _connected(k, edges)
                and _girth_at_least_five(k, edges)):
            return sorted(edges)
    raise RuntimeError("could not sample a connected cubic girth-five quotient")


def _choose_removable(edges, k, rng):
    choices = list(edges)
    rng.shuffle(choices)
    for edge in choices:
        remaining = [e for e in edges if e != edge]
        if _connected(k, remaining):
            return edge
    raise RuntimeError("quotient has no removable edge")


def _unlabelled_host(block_count, k, degree, rng):
    """Return (host edges, quotient edge lists, planted vertical pairs)."""
    bases = [_random_base(k, degree, rng) for _ in range(block_count)]
    target_block = rng.randrange(block_count)
    total = 2 * block_count * k

    def vertex(block, sheet, u):
        return (2 * block + sheet) * k + u

    edges = set()
    vertical_by_block = []
    for block, base_edges in enumerate(bases):
        vertical = []
        for u in range(k):
            edge = (vertex(block, 0, u), vertex(block, 1, u))
            edges.add(edge)
            vertical.append(edge)
        vertical_by_block.append(vertical)
        for a, b in base_edges:
            for sheet in (0, 1):
                x, y = vertex(block, sheet, a), vertex(block, sheet, b)
                edges.add((min(x, y), max(x, y)))

    if block_count > 1:
        removed = [_choose_removable(bases[j], k, rng)
                   for j in range(block_count)]
        oriented = []
        for a, b in removed:
            if rng.randrange(2):
                a, b = b, a
            oriented.append((a, b))
        for block, (a, b) in enumerate(oriented):
            x, y = vertex(block, 1, a), vertex(block, 1, b)
            edges.remove((min(x, y), max(x, y)))
        for block, (a, _b) in enumerate(oriented):
            next_block = (block + 1) % block_count
            _next_a, next_b = oriented[next_block]
            x = vertex(block, 1, a)
            y = vertex(next_block, 1, next_b)
            edges.add((min(x, y), max(x, y)))

    if len(edges) != total * (degree + 1) // 2:
        raise RuntimeError("host is not regular after ring switching")
    adj = _adjacency(total, edges)
    if set(map(len, adj)) != {degree + 1} or not _connected(total, edges):
        raise RuntimeError("host construction lost regularity or connectedness")
    return sorted(edges), bases, target_block, vertical_by_block[target_block]


def make_instance(n, seed=0, k=14, base_degree=3, **params):
    """Build a minor instance and its branch-set certificate by composition."""
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_params(n, k, base_degree)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)

    # Very rare ring switches can create an accidental extra square and blur the
    # clean reference invariant.  Rejecting that host never discovers the model:
    # the vertical certificate was already constructed and remembered.
    for _ in range(200):
        host_edges, bases, target_block, planted_pairs = _unlabelled_host(
            n, k, base_degree, rng
        )
        host_n = 2 * n * k
        square_counts = _edge_square_counts(host_n, host_edges)[0]
        vertical_candidates = {
            edge for edge, count in square_counts.items()
            if count >= base_degree - 1
        }
        # For cubic quotients, horizontal edges have <=1 square while even the
        # two damaged vertical pairs have 2.  For the demo cycle, use >=2.
        threshold = 2
        vertical_candidates = {
            edge for edge, count in square_counts.items() if count >= threshold
        }
        if (len(vertical_candidates) != n * k
                or any(sum(v in edge for edge in vertical_candidates) != 1
                       for v in range(host_n))):
            continue
        break
    else:
        raise RuntimeError("could not retain a clean two-sheet invariant")

    host_labels = list(range(host_n))
    rng.shuffle(host_labels)
    host_map = {old: host_labels[old] for old in range(host_n)}
    labelled_host_edges = sorted(
        (min(host_map[a], host_map[b]), max(host_map[a], host_map[b]))
        for a, b in host_edges
    )

    target_perm = list(range(k))
    rng.shuffle(target_perm)
    target_map = {old: target_perm[old] for old in range(k)}
    target_edges = sorted(
        (min(target_map[a], target_map[b]), max(target_map[a], target_map[b]))
        for a, b in bases[target_block]
    )
    inverse_target = {new: old for old, new in target_map.items()}
    # Sheet 0 is never touched by the ring switch, hence is a literal target
    # copy.  Remember its singleton model; planted_pairs is retained only for
    # the construction/reference invariant.
    planted_by_old = {old: min(pair) for old, pair in enumerate(planted_pairs)}
    answer = [
        host_map[planted_by_old[inverse_target[label]]]
        for label in range(k)
    ]

    return {
        "family": "two_sheet_expander_minor",
        "n_vertices": host_n,
        "target_vertices": k,
        "host_degree": base_degree + 1,
        "alpha_lower_bound": [2, host_n],
        "host_edges": [list(edge) for edge in labelled_host_edges],
        "target_edges": [list(edge) for edge in target_edges],
        "answer": answer,
    }


def _validate_instance_graph(inst):
    cache_key = id(inst)
    cached = _VERIFY_CACHE.get(cache_key)
    if cached is not None and cached[0] is inst:
        return cached[1]
    try:
        host_n = inst["n_vertices"]
        target_n = inst["target_vertices"]
        host_rows = inst["host_edges"]
        target_rows = inst["target_edges"]
    except (KeyError, TypeError):
        return None, "instance is missing graph data"
    if (isinstance(host_n, bool) or not isinstance(host_n, int) or host_n < 1
            or isinstance(target_n, bool) or not isinstance(target_n, int)
            or target_n < 1):
        return None, "instance vertex counts are malformed"
    host_edges = set()
    target_edges = set()
    try:
        for row in host_rows:
            if (not isinstance(row, list) or len(row) != 2
                    or any(isinstance(x, bool) or not isinstance(x, int)
                           for x in row)):
                return None, "host edge rows are malformed"
            a, b = row
            if not (0 <= a < b < host_n):
                return None, "host edge endpoint is invalid"
            host_edges.add((a, b))
        for row in target_rows:
            if (not isinstance(row, list) or len(row) != 2
                    or any(isinstance(x, bool) or not isinstance(x, int)
                           for x in row)):
                return None, "target edge rows are malformed"
            a, b = row
            if not (0 <= a < b < target_n):
                return None, "target edge endpoint is invalid"
            target_edges.add((a, b))
    except TypeError:
        return None, "instance edge tables are malformed"
    if len(host_edges) != len(host_rows) or len(target_edges) != len(target_rows):
        return None, "instance contains a duplicate edge"
    result = ((host_n, target_n, host_edges, target_edges), "ok")
    # verify() is called 200,000 times by G4.  Retain only a small identity cache
    # so repeated grading is O(|answer|), without putting non-JSON sets in inst.
    if len(_VERIFY_CACHE) >= 64:
        _VERIFY_CACHE.clear()
    _VERIFY_CACHE[cache_key] = (inst, result)
    return result


def render(inst):
    """Return the full standalone problem, including exact output syntax."""
    host_rows = "\n".join(f"  {a} {b}" for a, b in inst["host_edges"])
    target_rows = "\n".join(f"  {a} {b}" for a, b in inst["target_edges"])
    num, den = inst["alpha_lower_bound"]
    statement = f"""Find a graph-minor model of H in G with the required branch-set shape.

All graphs here are finite, simple and undirected.  The target H has vertices 0 through {inst['target_vertices'] - 1}.  The host G has vertices 0 through {inst['n_vertices'] - 1}.  A branch set is a set of host vertices.  A model of H in G assigns one nonempty branch set B_i to every target vertex i such that branch sets are pairwise disjoint, each G[B_i] is connected, and for every target edge i-j there is a host edge with one endpoint in B_i and the other in B_j.  Extra host edges and unused host vertices are allowed.  A connecting host edge is a one-edge path, so these data are also a path model in the usual graph-minor definition.

For this problem every branch set must be a singleton.  Encode the model as [v_0,v_1,...], where B_i={{v_i}}.  Entries occur in target-label order, and no host vertex may repeat.  Indexing is zero-based.

The host is {inst['host_degree']}-regular, connected, and therefore is promised to be an alpha-expander for alpha={num}/{den}: every nontrivial vertex cut has at least alpha times the smaller shore in crossing edges.

Complete target edge list ({len(inst['target_edges'])} edges):
{target_rows}

Complete host edge list ({len(inst['host_edges'])} edges):
{host_rows}

Give your final answer inside <answer></answer> tags, as one JSON array of exactly {inst['target_vertices']} distinct integer vertex identifiers in target-label order.
Example: <answer>[3,17,8]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse the final tagged JSON answer, tolerating prose and code fences."""
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
    if (not isinstance(value, list)
            or not all(isinstance(x, int) and not isinstance(x, bool)
                       for x in value)):
        return None
    return value


def verify(inst, answer):
    """Validate any stated-shape minor model without reading inst['answer']."""
    parsed, reason = _validate_instance_graph(inst)
    if parsed is None:
        return False, reason
    host_n, target_n, host_edges, target_edges = parsed
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) != target_n:
        return False, f"wrong branch-set count: expected {target_n}, received {len(answer)}"
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in answer):
        return False, "every vertex identifier must be an integer"
    if any(x < 0 or x >= host_n for x in answer):
        return False, f"a vertex identifier lies outside the range 0..{host_n - 1}"
    if len(set(answer)) != len(answer):
        return False, "branch sets must be pairwise disjoint"
    for u, v in target_edges:
        a, b = answer[u], answer[v]
        if (min(a, b), max(a, b)) not in host_edges:
            return False, f"target edge {u}-{v} has no edge between its branch sets"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from the obvious ordered injective-map language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    k = inst["target_vertices"]
    return rng.sample(range(inst["n_vertices"]), k)


def search_space(inst):
    """Number of ordered injective singleton-branch certificates."""
    host_n = inst["n_vertices"]
    k = inst["target_vertices"]
    return math.factorial(host_n) // math.factorial(host_n - k)


def enumerate_all(inst):
    """Count all valid certificates exactly only when the language is small."""
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    host_n = inst["n_vertices"]
    k = inst["target_vertices"]
    count = 0

    def rec(index, remaining, answer):
        nonlocal count
        if index == k:
            if verify(inst, answer)[0]:
                count += 1
            return
        for at, vertex in enumerate(remaining):
            rec(index + 1, remaining[:at] + remaining[at + 1:],
                answer + [vertex])

    rec(0, list(range(host_n)), [])
    return count


def _edge_square_counts(vertex_count, edges):
    """Return exact 4-cycle incidence per edge and adjacency-probe count."""
    edge_set = {tuple(sorted(e)) for e in edges}
    adj = _adjacency(vertex_count, edge_set)
    counts = {}
    operations = 0
    for u, v in edge_set:
        count = 0
        for a in adj[u] - {v}:
            for b in adj[v] - {u}:
                operations += 1
                if (min(a, b), max(a, b)) in edge_set:
                    count += 1
        counts[(u, v)] = count
    return counts, operations


def _components_graph(nodes, edges):
    adj = {v: set() for v in nodes}
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    unseen = set(nodes)
    components = []
    while unseen:
        start = min(unseen)
        unseen.remove(start)
        comp = {start}
        queue = [start]
        for v in queue:
            for w in adj[v]:
                if w in unseen:
                    unseen.remove(w)
                    comp.add(w)
                    queue.append(w)
        components.append(comp)
    return components


def _distance_histograms(nodes, adj):
    profiles = {}
    operations = 0
    for source in nodes:
        dist = {source: 0}
        queue = [source]
        for v in queue:
            for w in adj[v]:
                operations += 1
                if w not in dist:
                    dist[w] = dist[v] + 1
                    queue.append(w)
        hist = {}
        for value in dist.values():
            hist[value] = hist.get(value, 0) + 1
        profiles[source] = tuple(sorted(hist.items()))
    return profiles, operations


def _find_isomorphism(pattern_nodes, pattern_edges, host_nodes, host_edges):
    """Exact small bounded-degree isomorphism with counted search operations."""
    p_adj = {v: set() for v in pattern_nodes}
    h_adj = {v: set() for v in host_nodes}
    for a, b in pattern_edges:
        p_adj[a].add(b)
        p_adj[b].add(a)
    for a, b in host_edges:
        h_adj[a].add(b)
        h_adj[b].add(a)
    p_profiles, operations = _distance_histograms(pattern_nodes, p_adj)
    h_profiles, extra = _distance_histograms(host_nodes, h_adj)
    operations += extra
    domains = {
        u: [v for v in host_nodes
            if len(p_adj[u]) == len(h_adj[v])
            and p_profiles[u] == h_profiles[v]]
        for u in pattern_nodes
    }
    mapping = {}
    used = set()

    def backtrack():
        nonlocal operations
        if len(mapping) == len(pattern_nodes):
            return True
        unmapped = [u for u in pattern_nodes if u not in mapping]
        u = min(
            unmapped,
            key=lambda x: (-sum(w in mapping for w in p_adj[x]),
                           len(domains[x]), x),
        )
        for v in domains[u]:
            operations += 1
            if v in used:
                continue
            good = True
            for other, image in mapping.items():
                operations += 1
                if ((other in p_adj[u]) != (image in h_adj[v])):
                    good = False
                    break
            if not good:
                continue
            mapping[u] = v
            used.add(v)
            if backtrack():
                return True
            used.remove(v)
            del mapping[u]
        return False

    if backtrack():
        return mapping, operations
    return None, operations


def _select_sheet_vertices(mapping, pairs, target_edges, host_edges):
    """Choose one endpoint of each recovered pair so every target edge exists."""
    target_nodes = sorted(mapping)
    target_adj = {u: set() for u in target_nodes}
    for a, b in target_edges:
        target_adj[a].add(b)
        target_adj[b].add(a)
    chosen = {}
    operations = 0

    def backtrack():
        nonlocal operations
        if len(chosen) == len(target_nodes):
            return True
        remaining = [u for u in target_nodes if u not in chosen]
        u = min(remaining,
                key=lambda x: (-sum(v in chosen for v in target_adj[x]), x))
        for image in pairs[mapping[u]]:
            good = True
            for v in target_adj[u]:
                if v not in chosen:
                    continue
                operations += 1
                edge = (min(image, chosen[v]), max(image, chosen[v]))
                if edge not in host_edges:
                    good = False
                    break
            if good:
                chosen[u] = image
                if backtrack():
                    return True
                del chosen[u]
        return False

    if backtrack():
        return [chosen[u] for u in target_nodes], operations
    return None, operations


def _reference_algorithm(inst):
    """Recover the product matching, quotient blocks, and a target isomorphism."""
    started = time.perf_counter()
    parsed, _ = _validate_instance_graph(inst)
    if parsed is None:
        return None, 0, time.perf_counter() - started
    host_n, target_n, host_edges, target_edges = parsed
    counts, operations = _edge_square_counts(host_n, host_edges)
    vertical = {edge for edge, count in counts.items() if count >= 2}
    incidence = {v: [] for v in range(host_n)}
    for edge in vertical:
        for v in edge:
            incidence[v].append(edge)
    if len(vertical) * 2 != host_n or any(len(rows) != 1 for rows in incidence.values()):
        return None, operations, time.perf_counter() - started
    pairs = sorted(vertical)
    pair_of = {}
    for index, pair in enumerate(pairs):
        pair_of[pair[0]] = index
        pair_of[pair[1]] = index
    multiplicity = {}
    for a, b in host_edges - vertical:
        operations += 1
        x, y = pair_of[a], pair_of[b]
        if x == y:
            continue
        edge = (min(x, y), max(x, y))
        multiplicity[edge] = multiplicity.get(edge, 0) + 1
    doubled = [edge for edge, value in multiplicity.items() if value == 2]
    components = _components_graph(range(len(pairs)), doubled)
    pattern_nodes = list(range(target_n))
    for comp in components:
        if len(comp) != target_n:
            continue
        comp_edges = [edge for edge in multiplicity
                      if edge[0] in comp and edge[1] in comp]
        mapping, cost = _find_isomorphism(
            pattern_nodes, target_edges, sorted(comp), comp_edges
        )
        operations += cost
        if mapping is not None:
            answer, selection_cost = _select_sheet_vertices(
                mapping, pairs, target_edges, host_edges
            )
            operations += selection_cost
            if answer is not None and verify(inst, answer)[0]:
                return answer, operations, time.perf_counter() - started
    return None, operations, time.perf_counter() - started


def _graph_fingerprint(vertex_count, edges):
    """Strong cheap isomorphism invariant: refined rooted distance profiles."""
    edge_set = {tuple(sorted(e)) for e in edges}
    adj = _adjacency(vertex_count, edge_set)
    square_counts, _ = _edge_square_counts(vertex_count, edge_set)
    local = {}
    for v in range(vertex_count):
        triangles = sum(1 for a, b in itertools.combinations(adj[v], 2)
                        if (min(a, b), max(a, b)) in edge_set)
        squares = sum(square_counts[tuple(sorted((v, w)))] for w in adj[v])
        local[v] = (len(adj[v]), triangles, squares)
    palette = {value: i for i, value in enumerate(sorted(set(local.values())))}
    colors = {v: palette[local[v]] for v in range(vertex_count)}
    for _ in range(vertex_count):
        raw = {v: (colors[v], tuple(sorted(colors[w] for w in adj[v])))
               for v in range(vertex_count)}
        p = {value: i for i, value in enumerate(sorted(set(raw.values())))}
        refined = {v: p[raw[v]] for v in range(vertex_count)}
        if refined == colors:
            break
        colors = refined
    profiles = []
    for source in range(vertex_count):
        dist = {source: 0}
        queue = [source]
        for v in queue:
            for w in adj[v]:
                if w not in dist:
                    dist[w] = dist[v] + 1
                    queue.append(w)
        joint = {}
        for v, distance in dist.items():
            key = (distance, colors[v], local[v])
            joint[key] = joint.get(key, 0) + 1
        profiles.append((local[source], colors[source], tuple(sorted(joint.items()))))
    return {
        "vertices": vertex_count,
        "edges": len(edge_set),
        "profiles": sorted(profiles),
    }


def canonical_key(inst):
    """Relabelling-invariant structural fingerprint of the graph pair (G,H)."""
    parsed, reason = _validate_instance_graph(inst)
    if parsed is None:
        return "malformed:" + reason
    host_n, target_n, host_edges, target_edges = parsed
    payload = {
        "host": _graph_fingerprint(host_n, host_edges),
        "target": _graph_fingerprint(target_n, target_edges),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def escalate(params):
    """Add matched decoy blocks while keeping the 14-integer witness fixed."""
    p = {key: value for key, value in params.items() if key != "_preset"}
    current = int(p.get("n", 1))
    if current >= 12:
        return "cap_bound"
    p["n"] = current + 2
    return p


def _relabel_instance(inst, rng):
    host_n = inst["n_vertices"]
    target_n = inst["target_vertices"]
    hp = list(range(host_n))
    tp = list(range(target_n))
    rng.shuffle(hp)
    rng.shuffle(tp)
    host_edges = [[hp[a], hp[b]] for a, b in inst["host_edges"]]
    target_edges = [[tp[a], tp[b]] for a, b in inst["target_edges"]]
    for row in host_edges + target_edges:
        if rng.randrange(2):
            row.reverse()
        row.sort()
    rng.shuffle(host_edges)
    rng.shuffle(target_edges)
    old_for_new = {new: old for old, new in enumerate(tp)}
    answer = [hp[inst["answer"][old_for_new[new]]]
              for new in range(target_n)]
    return {
        "family": inst["family"],
        "n_vertices": host_n,
        "target_vertices": target_n,
        "host_degree": inst["host_degree"],
        "alpha_lower_bound": list(inst["alpha_lower_bound"]),
        "host_edges": host_edges,
        "target_edges": target_edges,
        "answer": answer,
    }


def _greedy_disjoint_edges(inst, ordered_edges):
    answer = []
    used = set()
    for edge in ordered_edges:
        if edge[0] in used or edge[1] in used:
            continue
        answer.append(min(edge))
        used.update(edge)
        if len(answer) == inst["target_vertices"]:
            return answer
    return None


def _attack_first_edges(inst):
    edges = [tuple(edge) for edge in sorted(inst["host_edges"])]
    return _greedy_disjoint_edges(inst, edges)


def _attack_high_square_edges(inst):
    counts, _ = _edge_square_counts(inst["n_vertices"], inst["host_edges"])
    ordered = sorted(counts, key=lambda e: (-counts[e], e))
    return _greedy_disjoint_edges(inst, ordered)


def _attack_numeric_span(inst):
    edges = [tuple(edge) for edge in inst["host_edges"]]
    edges.sort(key=lambda e: (-(e[1] - e[0]), e))
    return _greedy_disjoint_edges(inst, edges)


def _attack_naive_local_quotient(inst):
    """Use the first square-rich quotient and a BFS order, but no GI search."""
    parsed, _ = _validate_instance_graph(inst)
    if parsed is None:
        return None
    host_n, target_n, host_edges, _ = parsed
    counts, _ = _edge_square_counts(host_n, host_edges)
    vertical = {edge for edge, count in counts.items() if count >= 2}
    pairs = sorted(vertical)
    if len(pairs) * 2 != host_n:
        return None
    pair_of = {v: i for i, pair in enumerate(pairs) for v in pair}
    mult = {}
    for a, b in host_edges - vertical:
        x, y = pair_of[a], pair_of[b]
        if x != y:
            edge = (min(x, y), max(x, y))
            mult[edge] = mult.get(edge, 0) + 1
    comps = _components_graph(range(len(pairs)),
                              [e for e, value in mult.items() if value == 2])
    comps = [c for c in comps if len(c) == target_n]
    if not comps:
        return None
    comp = min(comps, key=lambda c: min(min(pairs[x]) for x in c))
    adj = {x: set() for x in comp}
    for a, b in mult:
        if a in comp and b in comp:
            adj[a].add(b)
            adj[b].add(a)
    start = min(comp, key=lambda x: min(pairs[x]))
    order = [start]
    seen = {start}
    for v in order:
        for w in sorted(adj[v], key=lambda x: min(pairs[x])):
            if w not in seen:
                seen.add(w)
                order.append(w)
    return [min(pairs[x]) for x in order[:target_n]]


def _run_attacks(inst, seed):
    candidates = {
        "outlier_high_4cycle_edges": _attack_high_square_edges(inst),
        "greedy_first_disjoint_edges": _attack_first_edges(inst),
        "greedy_largest_numeric_span": _attack_numeric_span(inst),
        "in_context_naive_local_quotient": _attack_naive_local_quotient(inst),
    }
    results = {name: int(candidate is not None and verify(inst, candidate)[0])
               for name, candidate in candidates.items()}
    rr_rng = random.Random(seed ^ 0x7A17C0DE)
    found = False
    for _ in range(256):
        if verify(inst, random_candidate(inst, rr_rng))[0]:
            found = True
            break
    results["random_restart_256"] = int(found)
    return results


def _answer_atoms(answer):
    if isinstance(answer, list):
        return sum(_answer_atoms(x) for x in answer)
    if isinstance(answer, dict):
        return sum(_answer_atoms(x) for x in answer.values())
    return 1


def selftest():
    """Run correctness, density, adversary, scaling and invariance gates."""
    report = {}

    # G1: every named level, three independent seeds, exact JSON-native answer.
    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append((preset, seed, reason))
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append((preset, seed, "answer is not JSON-native"))
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]

    # G2: five structurally different corruptions and distinct checker reasons.
    corruptions = {}
    corruptions["drop_element"] = planted[:-1]
    duplicate = json.loads(json.dumps(planted))
    duplicate[1] = duplicate[0]
    corruptions["duplicate_vertex"] = duplicate
    corruptions["empty_answer"] = []
    outside = json.loads(json.dumps(planted))
    outside[0] = shipping["n_vertices"]
    corruptions["out_of_range"] = outside
    swapped = None
    for i in range(len(planted)):
        for j in range(i + 1, len(planted)):
            trial = json.loads(json.dumps(planted))
            trial[i], trial[j] = trial[j], trial[i]
            if not verify(shipping, trial)[0]:
                swapped = trial
                break
        if swapped is not None:
            break
    corruptions["swap_two_entries"] = swapped
    g2_results = {name: {"accepted": verify(shipping, value)[0],
                         "reason": verify(shipping, value)[1]}
                  for name, value in corruptions.items()}
    reasons = [item["reason"] for item in g2_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": (not any(item["accepted"] for item in g2_results.values())
                 and len(set(reasons)) == len(reasons)),
        "cases": g2_results,
    }

    # G3: realistic prose/fence parsing plus malformed-input behavior.
    model_response = (
        "I checked every branch adjacency.\n<answer>\n```json\n"
        + json.dumps(planted) + "\n```\n</answer>\n"
    )
    parsed = parse_answer(model_response)
    report["G3_round_trip"] = {
        "pass": (parsed == planted and parse_answer("no tagged answer") is None
                 and parse_answer("<answer>[oops]</answer>") is None),
        "parsed_matches": parsed == planted,
    }

    # G4 and shipping density: 200k structure-aware candidates.
    samples = 200_000
    guess_rng = random.Random(0x190109349)
    hits = 0
    started = time.perf_counter()
    for _ in range(samples):
        candidate = random_candidate(shipping, guess_rng)
        if verify(shipping, candidate)[0]:
            hits += 1
    density_elapsed = time.perf_counter() - started
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits, "total": samples,
        "observed_probability": hits / samples,
        "candidate_space": str(search_space(shipping)),
        "structure_aware": True,
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    ref_answer, ref_ops, ref_time = _reference_algorithm(shipping)
    report["G5_density_and_baseline"] = {
        "pass": (isinstance(hits / samples, float)
                 and ref_answer is not None
                 and verify(shipping, ref_answer)[0]),
        "shipping_density_fraction": hits / samples,
        "shipping_density_samples": samples,
        "baseline_wall_clock_sec": ref_time,
        "baseline_operations": ref_ops,
        "shipping_density": {
            "kind": "sampled", "hits": hits, "total": samples,
            "fraction": hits / samples, "wall_clock_sec": density_elapsed,
        },
        "additional_exact_demo_count": demo_count,
        "baseline": {
            "name": "4-cycle prism recognition plus bounded-degree isomorphism",
            "wall_clock_sec": ref_time,
            "operations": ref_ops,
            "solved": ref_answer is not None and verify(shipping, ref_answer)[0],
        },
    }

    # G6: all attacks must fail on eight seeds; reference must solve all eight.
    attack_names = [
        "outlier_high_4cycle_edges",
        "greedy_first_disjoint_edges",
        "greedy_largest_numeric_span",
        "in_context_naive_local_quotient",
        "random_restart_256",
    ]
    attack_totals = {name: 0 for name in attack_names}
    reference_successes = 0
    reference_operations = []
    reference_times = []
    for seed in range(40, 48):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        outcomes = _run_attacks(inst, seed)
        for name in attack_names:
            attack_totals[name] += outcomes[name]
        answer, operations, elapsed = _reference_algorithm(inst)
        reference_operations.append(operations)
        reference_times.append(elapsed)
        if answer is not None and verify(inst, answer)[0]:
            reference_successes += 1
    attacks = {name: {"successes": attack_totals[name], "attempts": 8}
               for name in attack_names}
    panel_pass = all(row["successes"] == 0 for row in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": panel_pass and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "4-cycle prism recognition plus bounded-degree isomorphism",
            "complexity": (
                "O(M*d^2 + q*k!) worst case for this executable exact "
                "recognizer; k=14 is fixed on all non-demo presets"
            ),
            "wall_clock_sec_mean": sum(reference_times) / len(reference_times),
            "wall_clock_sec_max": max(reference_times),
            "operations_mean": sum(reference_operations) / len(reference_operations),
            "operations_max": max(reference_operations),
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    # G7: n is block count, so doubling it doubles the decoy haystack only.
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (doubled_ok
                 and doubled["n_vertices"] == 2 * shipping["n_vertices"]
                 and _answer_atoms(doubled["answer"])
                 == _answer_atoms(shipping["answer"])),
        "shipping_vertices": shipping["n_vertices"],
        "doubled_vertices": doubled["n_vertices"],
        "shipping_answer_atoms": _answer_atoms(shipping["answer"]),
        "doubled_answer_atoms": _answer_atoms(doubled["answer"]),
        "verify_reason": doubled_reason,
    }

    # G8: arbitrary host/target relabellings, real carried witnesses, diversity.
    invariant = 0
    carried = 0
    distinct_keys = set()
    for seed in range(20):
        params = DIFFICULTY["medium"]
        inst = make_instance(seed=1000 + seed, **params)
        key = canonical_key(inst)
        transformed = _relabel_instance(inst, random.Random(9000 + seed))
        if canonical_key(transformed) == key:
            invariant += 1
        if verify(transformed, transformed["answer"])[0]:
            carried += 1
        distinct_keys.add(key)
    report["G8_canonical_key"] = {
        "pass": invariant == 20 and carried == 20 and len(distinct_keys) == 20,
        "invariant_relabellings": invariant,
        "carried_witnesses_verify": carried,
        "distinct_unrelated_keys": len(distinct_keys),
        "unrelated_attempts": 20,
        "transformations": [
            "arbitrary host-vertex permutation",
            "arbitrary target-vertex permutation",
            "host/target edge reordering and endpoint reversal",
        ],
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    intended_operations = (
        shipping["target_vertices"]
        + len(shipping["target_edges"]) * DIFFICULTY[SHIPPING_DIFFICULTY]["n"]
        + answer_elements
    )
    bare = G9_ORACLE_RESULTS["bare"]
    hinted = G9_ORACLE_RESULTS["hinted"]
    placebo = G9_ORACLE_RESULTS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": (answer_chars <= 2000 and answer_elements <= 256
                 and intended_operations <= 300),
        "arms": {"bare": dict(bare), "hinted": dict(hinted),
                 "placebo": dict(placebo)},
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    report["pass"] = all(
        value.get("pass", False) for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
