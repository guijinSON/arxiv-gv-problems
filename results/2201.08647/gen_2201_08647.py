"""Verified Track-B generator for minimum connected edge domination.

The generated object is a connected simple graph with a distinguished perfect
matching in its leaf subgraph. A certificate is an exact-size leaf vertex
cover; it denotes the star edges from the graph's centre to those leaves. The
matching is an executable lower bound and supplies a private edge for every
selected star edge. Generation chooses a hidden multiplicative orientation first and
then forgets it, so the answer is known by inverse generation.
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
except ImportError:                 # pragma: no cover - helpers are unnecessary
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "connected simple graph given by an edge list",
        "distinguished perfect matching in the leaf subgraph",
        "minimum connected edge dominating star",
    ],
    "verification_operations": [
        "edge-incidence domination check",
        "matching disjointness check",
        "private-edge minimality check",
        "integer cardinality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The displayed matching has a consistent orientation whose directed "
        "endpoint ratio is constant modulo p; without noticing it, one must "
        "propagate a bipartition through the full leaf-edge list."
    ),
    "hardness_basis": (
        "Track B: BFS bipartition is an O(|V|+|E|) reference algorithm; at "
        "shipping n=120 and leaf degree 8 it examines 3,840 "
        "adjacency items in roughly 0.0006 seconds, whereas "
        "the common-ratio route uses 137 exact modular operations."
    ),
    "max_answer_tokens": 108,
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
        "A strictly increasing JSON list containing exactly one endpoint of "
        "each of the n displayed matching edges. Every entry is a displayed "
        "leaf label; mathematically the list denotes the corresponding n "
        "centre-to-leaf edges."
    ),
    "bounds": {
        "length": "instance n",
        "entry_range": "displayed vertex labels",
        "matching_rule": "exactly one endpoint from each displayed pair",
        "order": "strictly increasing",
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 5, "degree": 3},
    "easy": {"n": 120, "degree": 8},
    "medium": {"n": 158, "degree": 10},
    "hard": {"n": 200, "degree": 12},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The displayed matching admits a consistent orientation with one common "
    "directed endpoint ratio modulo p."
)
PLACEBO_HINT = (
    "The displayed matching and leaf-edge list should both be checked with "
    "careful attention to labels."
)

# Filled only from valid repository-owned oracle runs. API errors are not
# attempts and are deliberately not converted into model failures.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES = r"""
Definition and executable certificate. Section 2 defines edge domination by a
shared endpoint, connected edge domination through the edge-induced graph, and
inclusion-minimality. Proposition 4 says that a connected edge dominating set
is minimal exactly when its edge-induced graph is a tree and every pendant edge
has a private edge. The generated answer denotes a star, so it is a tree. Every
selected star edge has its distinguished-matching edge as a private edge.

Step-0 algorithm check. An arbitrary minimal connected edge dominating set is
not a Track-A family: Lemma 5 computes one inside a connected edge dominating
set in O(m), and Theorem 16 enumerates all minimal solutions with
O(n m^2 Delta) delay. Theorem 18 gives the paper's 4-approximate K-best
enumeration after polynomial preprocessing. Exact minimum connected edge
domination is cited as NP-hard in the Introduction, but worst-case NP-hardness
does not establish hardness for this generated distribution.

Track choice. This module therefore makes an explicit Track-B claim. On its
special graphs, BFS two-colouring of the leaf graph finds an optimum cover in
O(|V|+|E|), and the selftest reports that successful reference algorithm rather
than pretending it fails. At the shipping preset it performs
3,840 counted adjacency insertions/examinations (roughly 0.0006 seconds averaged
over eight seeds). The intended no-tool route
looks only at the n displayed matching pairs: orient the first pair either way,
then retain from every pair the endpoint having the same directed ratio modulo
p. At n=120 that takes 137 elementary modular operations, including
one extended-Euclid inverse. The hint names the
invariant but does not give a sequence of steps.

Inverse generation. With p=2n+1 prime, the generator first partitions the
nonzero field elements into the square subgroup H and its nonsquare coset. It
samples odd powers of a primitive root, including powers one and three, and
uses multiplication by each as a perfect matching between the cosets. It then
discards the primitive root, exponents, and chosen side bit from the public
instance. The first two powers make the leaf graph connected; therefore its
bipartition is unique up to exchange. The planted coset covers every leaf edge.
The distinguished matching lower-bounds every
leaf vertex cover by n. More generally, the endpoints of any connected edge
dominating set form a connected vertex cover: if the centre is present it needs
at least n leaves, and if absent it needs all 2n leaves. Hence the planted n
star edges are minimum. No generated instance is solved to obtain its answer.

Attack handling. All leaves have exactly the same graph degree and every
matching pair comes from the same distribution. The panel tries smaller and
even endpoints, alternating orientations, neighbour-label moments, uncovered-
degree greedy cover, and 256 randomized greedy restarts. None uses the common-
ratio invariant. The polynomial BFS algorithm is separately reported as
the successful Track-B reference route. canonical_key uses relabelling-
invariant degree/common-neighbour statistics. It is intentionally described as
a strong cheap invariant, not a complete graph-isomorphism algorithm.
""".strip()


def _is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _prime_divisors(value: int) -> list[int]:
    divisors = []
    candidate = 2
    while candidate * candidate <= value:
        if value % candidate == 0:
            divisors.append(candidate)
            while value % candidate == 0:
                value //= candidate
        candidate += 1 if candidate == 2 else 2
    if value > 1:
        divisors.append(value)
    return divisors


def _primitive_root(prime: int) -> int:
    order = prime - 1
    factors = _prime_divisors(order)
    for candidate in range(2, prime):
        if all(pow(candidate, order // factor, prime) != 1
               for factor in factors):
            return candidate
    raise AssertionError("prime field has no primitive root")


def _next_supported_n(lower_bound: int) -> int:
    candidate = max(3, lower_bound)
    while not _is_prime(2 * candidate + 1):
        candidate += 1
    return candidate


def make_instance(n: int, seed: int = 0, *, degree: int, **params) -> dict:
    """Inverse-generate a certified optimum before forgetting its orientation."""
    del params
    if not isinstance(n, int) or isinstance(n, bool) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if (not isinstance(degree, int) or isinstance(degree, bool)
            or degree < 2 or degree > n):
        raise ValueError("degree must be an integer between 2 and n")

    rng = random.Random(seed)
    prime = 2 * n + 1
    if not _is_prime(prime):
        raise ValueError("2*n+1 must be prime")
    primitive = _primitive_root(prime)
    subgroup = [pow(primitive, 2 * i, prime) for i in range(n)]

    exponents = {1, 3}
    if degree > 2:
        choices = list(range(5, 2 * n, 2))
        exponents.update(rng.sample(choices, degree - 2))
    exponent_list = sorted(exponents)
    multipliers = [pow(primitive, exponent, prime)
                   for exponent in exponent_list]

    leaf_edges = sorted({
        tuple(sorted((value, (multiplier * value) % prime)))
        for value in subgroup
        for multiplier in multipliers
    })
    if len(leaf_edges) != n * degree:
        raise AssertionError("the circulant matchings unexpectedly overlapped")

    matching = [
        list(sorted((value, (primitive * value) % prime)))
        for value in subgroup
    ]
    rng.shuffle(matching)

    side = rng.randrange(2)
    answer = sorted(subgroup if side == 0
                    else [(primitive * value) % prime for value in subgroup])
    centre = 0
    leaves = list(range(1, prime))
    spokes = [[centre, leaf] for leaf in leaves]
    all_edges = sorted([list(edge) for edge in leaf_edges] + spokes)

    return {
        "side_size": n,
        "leaf_degree": degree,
        "vertex_count": prime,
        "center": centre,
        "leaf_vertices": leaves,
        "leaf_edges": [list(edge) for edge in leaf_edges],
        "lower_bound_matching": matching,
        "edges": all_edges,
        "target_size": n,
        "answer": answer,
    }


def _wrapped_pairs(pairs: list[list[int]], width: int = 8) -> str:
    tokens = [f"{a}-{b}" for a, b in pairs]
    return "\n".join(" ".join(tokens[i:i + width])
                     for i in range(0, len(tokens), width))


def render(inst: dict) -> str:
    """Return the complete graph problem and exact output contract."""
    n = inst["side_size"]
    leaves = " ".join(map(str, inst["leaf_vertices"]))
    leaf_edges = _wrapped_pairs(inst["leaf_edges"])
    matching = _wrapped_pairs(inst["lower_bound_matching"])
    example = ",".join(map(str, sorted(
        pair[0] for pair in inst["lower_bound_matching"])))
    text = f"""MINIMUM CONNECTED EDGE DOMINATING STAR

The following data define one finite undirected simple graph G. Its vertex
labels are the integers 0 through {inst['vertex_count'] - 1}. The distinguished
center is {inst['center']}. The other {2*n} displayed vertices are called leaves.
The graph contains center--v for every leaf v, plus exactly the displayed leaf
edges below, and no other edges. An item u-v denotes the unordered edge {{u,v}}.

Two edges dominate one another when they share an endpoint; an edge therefore
dominates itself. An edge set F is connected edge dominating when its
edge-induced subgraph is connected and every edge of G is dominated by an edge
of F. It is minimal if deleting any edge destroys connectivity or domination,
and minimum if no connected edge dominating set has fewer edges.

Your answer must be a strictly increasing JSON list of exactly n={n} distinct
leaf labels. It denotes F={{center--v : v occurs in the list}}. Order has no
mathematical significance, but increasing order is required for an unambiguous
serialization. Labels are 0-based integers and all stated bounds are inclusive.

The instance also supplies a lower-bound matching of n={n} pairwise-disjoint
leaf edges. Your list must contain exactly one endpoint of every displayed
matching edge and must meet every displayed leaf edge. These checks imply that
F is minimum: the matching forces every leaf vertex cover to have at least n
vertices. They also imply minimality: each retained spoke has its matching edge
as a private edge, meaning that no other edge of F touches that matching edge.

CENTER
{inst['center']}

LEAF VERTICES ({2*n})
{leaves}

LEAF EDGES ({len(inst['leaf_edges'])})
{leaf_edges}

LOWER-BOUND MATCHING ({n})
{matching}

Give your final answer inside <answer></answer> tags, as one JSON list.
Example of syntax only (not claimed valid):
<answer>[{example}]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def parse_answer(text: str) -> object | None:
    """Extract the final tagged JSON list; malformed text returns None."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json|text|python)?\s*", "", body,
                  flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, list) else None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any certificate in the stated language; never read inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer list must not be empty"
    if len(answer) != inst["target_size"]:
        return False, f"answer must contain exactly {inst['target_size']} labels"
    if any(not isinstance(value, int) or isinstance(value, bool)
           for value in answer):
        return False, "every answer label must be an integer"
    if len(set(answer)) != len(answer):
        return False, "answer labels must not repeat"
    if answer != sorted(answer):
        return False, "answer labels must be in strictly increasing order"
    vertex_count = inst["vertex_count"]
    if any(value < 0 or value >= vertex_count for value in answer):
        return False, f"answer label is outside 0 through {vertex_count - 1}"
    leaves = set(inst["leaf_vertices"])
    if any(value not in leaves for value in answer):
        return False, "every answer label must be a displayed leaf"

    matching = inst["lower_bound_matching"]
    if len(matching) != inst["target_size"]:
        return False, "instance matching has the wrong number of edges"
    chosen = set(answer)
    # Check candidate-dependent constraints first. Random G4 candidates almost
    # always fail after a few leaf edges, so verification stays genuinely cheap
    # without caching or trusting inst["answer"].
    for raw_edge in matching:
        if (not isinstance(raw_edge, list) or len(raw_edge) != 2
                or any(not isinstance(v, int) or isinstance(v, bool)
                       for v in raw_edge)):
            return False, "instance matching contains a malformed edge"
        a, b = raw_edge
        if (a in chosen) == (b in chosen):
            return False, "answer must choose exactly one endpoint per matching edge"
    for a, b in inst["leaf_edges"]:
        if a not in chosen and b not in chosen:
            return False, f"leaf edge {a}-{b} is not dominated by the star"

    # A surviving answer is rare. Now inspect the instance-supplied lower bound
    # completely, including edge membership and pairwise disjointness.
    leaf_edges = {tuple(sorted(edge)) for edge in inst["leaf_edges"]}
    used: set[int] = set()
    for raw_edge in matching:
        if (not isinstance(raw_edge, list) or len(raw_edge) != 2
                or any(not isinstance(v, int) or isinstance(v, bool)
                       for v in raw_edge)):
            return False, "instance matching contains a malformed edge"
        a, b = raw_edge
        edge = tuple(sorted((a, b)))
        if a == b or edge not in leaf_edges:
            return False, "instance matching contains a non-leaf-edge"
        if a in used or b in used:
            return False, "instance matching repeats a leaf endpoint"
        used.add(a)
        used.add(b)
    if used != leaves:
        return False, "instance matching does not cover every leaf"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly orient every supplied matching pair, then canonicalize."""
    return sorted(pair[rng.randrange(2)]
                  for pair in inst["lower_bound_matching"])


def search_space(inst: dict) -> int:
    return 1 << inst["target_size"]


def enumerate_all(inst: dict) -> int | None:
    n = inst["target_size"]
    if n > 20:
        return None
    count = 0
    matching = inst["lower_bound_matching"]
    for choices in itertools.product((0, 1), repeat=n):
        candidate = sorted(matching[i][choice]
                           for i, choice in enumerate(choices))
        count += int(verify(inst, candidate)[0])
    return count


def _canonical_profile(inst: dict) -> dict:
    """Strong cheap graph+distinguished-matching isomorphism invariant."""
    vertices = sorted(inst["leaf_vertices"])
    adjacency = {v: set() for v in vertices}
    edge_set: set[tuple[int, int]] = set()
    for a, b in inst["leaf_edges"]:
        edge = tuple(sorted((a, b)))
        edge_set.add(edge)
        adjacency[a].add(b)
        adjacency[b].add(a)
    matching_set = {tuple(sorted(edge))
                    for edge in inst["lower_bound_matching"]}
    pair_of: dict[int, int] = {}
    for pair_index, (a, b) in enumerate(inst["lower_bound_matching"]):
        pair_of[a] = pair_index
        pair_of[b] = pair_index
    pair_profile: collections.Counter[tuple[int, int, int, int]] = (
        collections.Counter()
    )
    for index, a in enumerate(vertices):
        for b in vertices[index + 1:]:
            pair_profile[(
                int(tuple(sorted((a, b))) in edge_set),
                int(tuple(sorted((a, b))) in matching_set),
                len(adjacency[a] & adjacency[b]),
                len(adjacency[a]) + len(adjacency[b]),
            )] += 1

    # Contract the distinguished matching.  The resulting weighted multigraph
    # retains how the other perfect matchings intertwine.  Sorted closed-walk
    # profiles are invariant under vertex and matching-pair renumbering and are
    # substantially stronger than a single four-cycle count.
    pair_count = len(inst["lower_bound_matching"])
    contracted = [collections.Counter() for _ in range(pair_count)]
    for a, b in edge_set - matching_set:
        left = pair_of[a]
        right = pair_of[b]
        if left == right:
            continue
        contracted[left][right] += 1
        contracted[right][left] += 1
    closed_walk_profiles = []
    for root in range(pair_count):
        vector = [0] * pair_count
        vector[root] = 1
        profile = []
        for length in range(1, 11):
            following = [0] * pair_count
            for vertex, count in enumerate(vector):
                if not count:
                    continue
                for other, multiplicity in contracted[vertex].items():
                    following[other] += count * multiplicity
            vector = following
            if length >= 2:
                profile.append(vector[root])
        closed_walk_profiles.append(tuple(profile))
    return {
        "vertices": len(vertices),
        "edges": len(edge_set),
        "degrees": sorted(len(adjacency[v]) for v in vertices),
        "matching_edges": len(matching_set),
        "pair_profile": sorted([list(key) + [count]
                                for key, count in pair_profile.items()]),
        "contracted_closed_walks_2_to_10": [
            list(row) for row in sorted(closed_walk_profiles)
        ],
    }


def canonical_key(inst: dict) -> str:
    """Hash only relabelling-invariant structure, never seed or rendered text."""
    blob = json.dumps(_canonical_profile(inst), sort_keys=True,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow decoy density first; stop when every safe named axis is exhausted."""
    result = dict(params)
    n = int(result.get("n", DIFFICULTY["hard"]["n"]))
    degree = int(result.get("degree", DIFFICULTY["hard"]["degree"]))
    if degree < 12:
        result["degree"] = min(12, degree + 2)
        return result
    if n < 256:
        candidate = _next_supported_n(n + 20)
        operation_bound = candidate + 2 * (2 * candidate + 1).bit_length() + 1
        if candidate > 256 or operation_bound > 300:
            return "cap_bound"
        result["n"] = candidate
        return result
    return "cap_bound"


def _candidate_from_rule(inst: dict, chooser) -> list[int]:
    return sorted(chooser(index, pair)
                  for index, pair in enumerate(inst["lower_bound_matching"]))


def _attack_smaller_endpoint(inst: dict) -> bool:
    candidate = _candidate_from_rule(inst, lambda _i, pair: min(pair))
    return verify(inst, candidate)[0]


def _attack_even_endpoint(inst: dict) -> bool:
    def choose(_index: int, pair: list[int]) -> int:
        evens = [value for value in pair if value % 2 == 0]
        return evens[0] if evens else min(pair)
    return verify(inst, _candidate_from_rule(inst, choose))[0]


def _attack_alternating_pairs(inst: dict) -> bool:
    candidate = _candidate_from_rule(
        inst, lambda index, pair: sorted(pair)[index % 2])
    return verify(inst, candidate)[0]


def _attack_neighbor_moment(inst: dict) -> bool:
    adjacency = {v: [] for v in inst["leaf_vertices"]}
    for a, b in inst["leaf_edges"]:
        adjacency[a].append(b)
        adjacency[b].append(a)

    def choose(_index: int, pair: list[int]) -> int:
        return min(pair, key=lambda v: (sum(adjacency[v]), v))

    return verify(inst, _candidate_from_rule(inst, choose))[0]


def _greedy_vertex_cover(inst: dict,
                         rng: random.Random | None = None) -> list[int]:
    edges = [tuple(edge) for edge in inst["leaf_edges"]]
    incident = {v: [] for v in inst["leaf_vertices"]}
    degree = {v: 0 for v in inst["leaf_vertices"]}
    for edge_id, (a, b) in enumerate(edges):
        incident[a].append(edge_id)
        incident[b].append(edge_id)
        degree[a] += 1
        degree[b] += 1
    active = [True] * len(edges)
    active_count = len(edges)
    chosen: set[int] = set()
    while active_count:
        maximum = max(degree.values())
        choices = sorted(v for v, value in degree.items() if value == maximum)
        vertex = choices[0] if rng is None else rng.choice(choices)
        chosen.add(vertex)
        for edge_id in incident[vertex]:
            if not active[edge_id]:
                continue
            active[edge_id] = False
            active_count -= 1
            a, b = edges[edge_id]
            degree[a] -= 1
            degree[b] -= 1
        if len(chosen) > inst["target_size"]:
            break
    return sorted(chosen)


def _attack_greedy(inst: dict) -> bool:
    return verify(inst, _greedy_vertex_cover(inst))[0]


def _attack_random_restart(inst: dict, seed: int,
                           restarts: int = 256) -> bool:
    rng = random.Random(seed)
    for _ in range(restarts):
        if verify(inst, _greedy_vertex_cover(inst, rng))[0]:
            return True
    return False


def _reference_algorithm(inst: dict) -> dict:
    """Expand adjacency and two-colour the connected bipartite leaf graph."""
    started = time.perf_counter()
    operations = 0
    adjacency = {v: [] for v in inst["leaf_vertices"]}
    for a, b in inst["leaf_edges"]:
        adjacency[a].append(b)
        adjacency[b].append(a)
        operations += 2
    colors: dict[int, int] = {}
    for start in sorted(adjacency):
        if start in colors:
            continue
        colors[start] = 0
        queue = collections.deque([start])
        while queue:
            vertex = queue.popleft()
            for other in adjacency[vertex]:
                operations += 1
                if other not in colors:
                    colors[other] = 1 - colors[vertex]
                    queue.append(other)
                elif colors[other] == colors[vertex]:
                    return {
                        "success": False,
                        "operations": operations,
                        "wall_clock_sec": time.perf_counter() - started,
                        "reason": "leaf graph is not bipartite",
                    }
    candidates = [
        sorted(v for v in colors if colors[v] == side)
        for side in (0, 1)
    ]
    answer = next((candidate for candidate in candidates
                   if verify(inst, candidate)[0]), None)
    success = answer is not None
    return {
        "success": success,
        "answer": answer,
        "operations": operations,
        "wall_clock_sec": time.perf_counter() - started,
        "reason": "ok" if success else "no color class verified",
    }


def _compact_route(inst: dict) -> dict:
    """Use the hidden matching-ratio invariant, for testing and costing."""
    started = time.perf_counter()
    modulus = inst["vertex_count"]
    matching = inst["lower_bound_matching"]
    first_a, first_b = matching[0]
    ratio = (first_b * pow(first_a, -1, modulus)) % modulus
    operations = 2 * modulus.bit_length() + 1
    cover = []
    for a, b in matching:
        forward = (ratio * a) % modulus
        operations += 1
        cover.append(a if forward == b else b)
    cover.sort()
    success, reason = verify(inst, cover)
    return {
        "success": success,
        "answer": cover,
        "ratio": ratio,
        "operations": operations,
        "wall_clock_sec": time.perf_counter() - started,
        "reason": reason,
    }


def _relabel_instance(inst: dict, seed: int) -> dict:
    """Carry graph, matching, and answer through an arbitrary vertex relabel."""
    rng = random.Random(seed)
    labels = list(range(inst["vertex_count"]))
    rng.shuffle(labels)
    mapping = dict(enumerate(labels))
    moved = {key: value for key, value in inst.items()
             if key not in {"center", "leaf_vertices", "leaf_edges",
                            "lower_bound_matching", "edges", "answer"}}
    moved["center"] = mapping[inst["center"]]
    moved["leaf_vertices"] = [mapping[v]
                              for v in reversed(inst["leaf_vertices"])]
    moved["leaf_edges"] = [[mapping[b], mapping[a]]
                           for a, b in reversed(inst["leaf_edges"])]
    moved["lower_bound_matching"] = [
        [mapping[b], mapping[a]]
        for a, b in reversed(inst["lower_bound_matching"])
    ]
    moved["edges"] = [[mapping[b], mapping[a]]
                      for a, b in reversed(inst["edges"])]
    moved["answer"] = sorted(mapping[v] for v in inst["answer"])
    return moved


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))

    def atoms(value: object) -> int:
        if isinstance(value, dict):
            return sum(atoms(item) for item in value.values())
        if isinstance(value, list):
            return sum(atoms(item) for item in value)
        return 1

    return len(encoded), math.ceil(len(encoded) / 4), atoms(answer)


def selftest() -> dict:
    report: dict = {}

    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2026):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            compact = _compact_route(inst)
            json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            checks += 1
            if not (ok and compact["success"] and json_ok):
                failures.append({
                    "preset": preset,
                    "seed": seed,
                    "reason": reason,
                    "compact_reason": compact["reason"],
                    "json_native": json_ok,
                })
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "failures": failures,
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

    answer_json = json.dumps(answer, separators=(",", ":"))
    realistic = (
        "The matching orientation gives the following cover.\n"
        f"<answer>```json\n{answer_json}\n```</answer>\n"
        "I checked every remaining leaf edge."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0]
                and parse_answer("garbage") is None,
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    rng = random.Random(0x220108647)
    total = 200_000
    hits = 0
    started = time.perf_counter()
    for _ in range(total):
        hits += int(verify(inst, random_candidate(inst, rng))[0])
    sample_seconds = time.perf_counter() - started
    probability = hits / total
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": total,
        "empirical_probability": probability,
        "candidate_space": search_space(inst),
        "prior": "uniform independent orientation of every displayed matching edge",
        "freely_deducible_constraints": [
            "exact answer length",
            "distinct displayed leaves",
            "strictly increasing serialization",
            "exactly one endpoint of each lower-bound matching edge",
        ],
        "sampling_wall_seconds": sample_seconds,
    }

    reference = _reference_algorithm(inst)
    compact = _compact_route(inst)
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": probability < 1e-6 and reference["success"]
                and compact["success"] and demo_count is not None,
        "shipping_observed_valid_fraction": probability,
        "shipping_density_sample_count": total,
        "shipping_valid_hits": hits,
        "shipping_candidate_space": search_space(inst),
        "shipping_exact_valid_count": None,
        "reference_wall_seconds": reference["wall_clock_sec"],
        "reference_operations": reference["operations"],
        "reference_successes": int(reference["success"]),
        "compact_route_wall_seconds": compact["wall_clock_sec"],
        "compact_route_operations": compact["operations"],
        "compact_route_successes": int(compact["success"]),
        "demo_exact_valid_count": demo_count,
    }

    attack_functions = {
        "matching_smaller_endpoint": _attack_smaller_endpoint,
        "matching_even_endpoint": _attack_even_endpoint,
        "matching_alternating_orientation": _attack_alternating_pairs,
        "neighbor_label_moment_outlier": _attack_neighbor_moment,
        "greedy_max_uncovered_degree": _attack_greedy,
    }
    successes = {name: 0 for name in attack_functions}
    successes["random_restart_256_greedy"] = 0
    references = []
    compacts = []
    restart_wall_seconds = 0.0
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **ship_params)
        for name, attack in attack_functions.items():
            successes[name] += int(attack(trial))
        restart_started = time.perf_counter()
        successes["random_restart_256_greedy"] += int(
            _attack_random_restart(trial, seed, 256))
        restart_wall_seconds += time.perf_counter() - restart_started
        references.append(_reference_algorithm(trial))
        compacts.append(_compact_route(trial))
    reference_successes = sum(int(row["success"]) for row in references)
    compact_successes = sum(int(row["success"]) for row in compacts)
    report["G6_adversary_panel"] = {
        "pass": all(value == 0 for value in successes.values())
                and reference_successes == 8 and compact_successes == 8,
        "attacks": {
            name: {"successes": successes[name], "attempts": 8}
            for name in successes
        },
        "reference_algorithm": {
            "name": "expanded adjacency plus BFS bipartition",
            "complexity": "O(|V|+|E|)",
            "wall_clock_sec": (
                sum(row["wall_clock_sec"] for row in references) / 8
            ),
            "operations": sum(row["operations"] for row in references) / 8,
            "operation_definition": "adjacency insertions and examinations",
            "solves": f"{reference_successes}/8, as expected",
        },
        "intended_compact_route": {
            "name": "constant directed ratio across matching pairs",
            "operations": sum(row["operations"] for row in compacts) / 8,
            "solves": f"{compact_successes}/8",
        },
    }
    report["G5_density_and_baseline"]["strongest_failing_attack"] = {
        "name": "random_restart_256_greedy",
        "wall_clock_sec": restart_wall_seconds,
        "restarts": 8 * 256,
        "successes": successes["random_restart_256_greedy"],
        "attempted_instances": 8,
    }

    doubled_params = {
        "n": _next_supported_n(2 * ship_params["n"]),
        "degree": min(2 * ship_params["degree"], 2 * ship_params["n"]),
    }
    started = time.perf_counter()
    doubled = make_instance(seed=7, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    doubled_seconds = time.perf_counter() - started
    spaces = [search_space(make_instance(seed=9, **params))
              for name, params in DIFFICULTY.items() if name != "demo"]
    report["G7_scales"] = {
        "pass": doubled_ok and spaces == sorted(spaces)
                and len(set(spaces)) == len(spaces),
        "shipping_side_size": ship_params["n"],
        "doubled_side_size": doubled_params["n"],
        "doubled_degree": doubled_params["degree"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "doubled_build_and_verify_seconds": doubled_seconds,
        "named_candidate_spaces": spaces,
    }

    invariant = True
    invariance_checks = 0
    transform_checks = 0
    for seed in range(20):
        trial = make_instance(seed=10_000 + seed, **ship_params)
        key = canonical_key(trial)
        for salt in (seed + 1, 1000 + seed, 2000 + seed):
            moved = _relabel_instance(trial, salt)
            invariance_checks += 1
            invariant &= canonical_key(moved) == key
            transform_checks += 1
            invariant &= verify(moved, moved["answer"])[0]
    unrelated_keys = [canonical_key(make_instance(
        seed=20_000 + seed, **ship_params)) for seed in range(20)]
    report["G8_canonical_key"] = {
        "pass": invariant and len(set(unrelated_keys)) == len(unrelated_keys),
        "invariance_checks": invariance_checks,
        "real_transformation_verify_checks": transform_checks,
        "distinct_unrelated_keys": len(set(unrelated_keys)),
        "unrelated_instances": len(unrelated_keys),
        "symmetries": [
            "arbitrary vertex relabelling with the answer carried",
            "leaf-edge and matching-edge reordering",
            "endpoint reversal inside every undirected edge",
        ],
        "key_kind": "degree and common-neighbour profile with matching colors",
        "is_complete_isomorphism_test": False,
    }

    chars, tokens, elements = _answer_metrics(answer)
    PROBLEM_PROFILE["max_answer_tokens"] = tokens
    intended_operations = compact["operations"]
    arms = {name: dict(G9_EVIDENCE[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = chars <= 2000 and elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
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
    report["problem_profile"] = dict(PROBLEM_PROFILE)
    report["all_passed"] = all(
        value.get("pass", False) for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
