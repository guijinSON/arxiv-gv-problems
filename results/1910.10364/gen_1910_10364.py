"""Verified problem generator for arXiv:1910.10364.

The generated task is a compact certificate for List Coloring on the split
graphs used in Section 5 of the paper.  A regular planted Exact-Cover-by-3-Sets
instance supplies the Independent Set instance in the paper's reduction.

Only the Python standard library is used.  Every instance is deterministic in
``(n, seed, **params)`` and the planted cover is sampled before the triples.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re
import time
from collections import deque


NATIVE = {
    "domain": "combinatorics",
    "core": "exact_cover",
    "objects": [
        "regular 3-uniform hypergraph as indexed triples",
        "implicitly defined split graph with vertex color lists",
    ],
    "intuition": "recognize exact cover inside the split-graph coloring reduction",
    "reduction": (
        "Section 5, Lemma 5 (Independent Set to List Coloring on split graphs); "
        "the generator restricts the Independent Set graph to the intersection "
        "graph of a planted regular 3-uniform exact-cover instance"
    ),
}


CERTIFICATE_LANGUAGE = {
    "description": (
        "An unordered set of exactly n distinct integer triple IDs in the "
        "inclusive range 0 through triple_count - 1, rendered as a "
        "comma-separated list; for each instance the language has exactly "
        "binomial(triple_count, n) members"
    ),
    "bounds": {
        "answer_length": "exactly inst['n']",
        "minimum_id": 0,
        "maximum_id": "inst['triple_count'] - 1",
        "distinct_ids": True,
        "order_significant": False,
    },
}


DIFFICULTY = {
    "easy": {"n": 6, "degree": 3},
    "medium": {"n": 40, "degree": 5},
    "hard": {"n": 80, "degree": 5},
}

SHIPPING_DIFFICULTY = "medium"


NOTES = r"""
Section 2 of Reddy, "Parameterized Coloring Problems on Threshold Graphs"
(arXiv:1910.10364v3), defines a split graph as a clique plus an independent
set.  Section 5, Lemma 5, fixes the hard problem and the exact reduction used
here.  Given Independent Set (G,k), it creates one clique vertex c_v per vertex
of G and, for every edge uv of G, one independent vertex adjacent to every
clique vertex except c_u and c_v.  Clique lists are [|V(G)|], while independent
vertices may use only colors k+1 through |V(G)|.  The clique vertices receiving
the first k colors are exactly an independent set of size k in G.

The easy boundary is equally important.  Section 5, Lemma 6, gives an
O(K^K(m+n)) algorithm on split graphs when K is the palette/list parameter: try
all clique colorings, then extend greedily to the independent set.  Here K is
degree*n, so it grows with n.  The polynomial-time threshold-graph and FPT
results in Sections 3 and 4 are not used as hardness claims.

For inverse generation, the answer slots are sampled first.  They receive a
uniform random partition of 3n elements into n triples.  The remaining triples
are generated from shuffled residual element stubs so every element occurs
exactly ``degree`` times; all triple IDs are hidden among the pre-sampled slots.
All triples have size three, every element has the same frequency, and plant
and decoy IDs and element labels are randomized.  Intersecting triples form G,
so the planted partition is an independent set and therefore completes to a
proper list coloring of the paper's split graph.

The adversary panel attacks the signatures created by planting: minimum
conflict degree (outlier), input-order greedy packing, 256 randomized greedy
restarts, a shifted-adjacency power iteration for a bottom spectral vector, and
min-column Algorithm X capped at 10,000 nodes.  None may return a verified
witness on the eight shipping trials.  canonical_key intentionally ignores the
seed, answer, and rendering.  It hashes a typed incidence-graph invariant made
from all rooted distance profiles and their incidence pairings.  This is
invariant under element relabeling, triple/clique renumbering, and input order,
but it is a strong polynomial fingerprint rather than a complete solution to
hypergraph isomorphism.
""".strip()


def _connected_incidence(triples: list[tuple[int, int, int]], universe: int) -> bool:
    """Whether the element--triple incidence graph is connected."""

    by_element = [[] for _ in range(universe)]
    for triple_id, triple in enumerate(triples):
        for element in triple:
            by_element[element].append(triple_id)
    seen_elements = {0}
    seen_triples: set[int] = set()
    element_stack = [0]
    while element_stack:
        element = element_stack.pop()
        for triple_id in by_element[element]:
            if triple_id in seen_triples:
                continue
            seen_triples.add(triple_id)
            for other in triples[triple_id]:
                if other not in seen_elements:
                    seen_elements.add(other)
                    element_stack.append(other)
    return len(seen_elements) == universe and len(seen_triples) == len(triples)


def make_instance(n: int, seed: int = 0, degree: int = 5, **params) -> dict:
    """Sample an exact-cover/list-coloring witness first, then build its input.

    ``n`` is the number of triples required in the cover.  The universe has
    ``3*n`` elements and the input has ``degree*n`` triples.  Thus increasing
    n grows the witness, palette, split graph, and combinatorial search space.
    """

    if params:
        raise ValueError(f"unknown parameters: {', '.join(sorted(params))}")
    if not isinstance(n, int) or isinstance(n, bool) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if not isinstance(degree, int) or isinstance(degree, bool) or not 2 <= degree <= 8:
        raise ValueError("degree must be an integer from 2 through 8")

    rng = random.Random(seed)
    universe = 3 * n
    triple_count = degree * n

    # G: choose the public witness positions before constructing any triple.
    answer = sorted(rng.sample(range(triple_count), n))

    elements = list(range(universe))
    rng.shuffle(elements)
    planted = [tuple(sorted(elements[3 * i:3 * i + 3])) for i in range(n)]

    # A configuration-model residual makes every element occur degree-1 more
    # times.  Reject loops, duplicate triples, and disconnected factorizations.
    triples = None
    for _ in range(20_000):
        stubs = [element for element in range(universe) for _ in range(degree - 1)]
        rng.shuffle(stubs)
        decoys: list[tuple[int, int, int]] = []
        seen = set(planted)
        acceptable = True
        for offset in range(0, len(stubs), 3):
            triple = tuple(sorted(stubs[offset:offset + 3]))
            if len(set(triple)) != 3 or triple in seen:
                acceptable = False
                break
            seen.add(triple)
            decoys.append(triple)
        if not acceptable:
            continue
        trial: list[tuple[int, int, int] | None] = [None] * triple_count
        for slot, triple in zip(answer, planted):
            trial[slot] = triple
        decoy_iter = iter(decoys)
        for slot in range(triple_count):
            if trial[slot] is None:
                trial[slot] = next(decoy_iter)
        complete = [triple for triple in trial if triple is not None]
        if _connected_incidence(complete, universe):
            triples = complete
            break
    if triples is None:
        raise RuntimeError("could not construct a connected regular instance")

    frequencies = [0] * universe
    for triple in triples:
        for element in triple:
            frequencies[element] += 1
    if any(count != degree for count in frequencies):
        raise RuntimeError("internal error: the instance is not regular")

    return {
        "paper": "arXiv:1910.10364",
        "family": "split-graph list-coloring certificate",
        "n": n,
        "degree": degree,
        "universe": universe,
        "triple_count": triple_count,
        "triples": triples,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the entire implicit split graph and output contract."""

    n = inst["n"]
    universe = inst["universe"]
    triple_count = inst["triple_count"]
    lines = [
        "Find a compact certificate for a proper list coloring of a split graph.",
        "",
        "Definitions and construction.",
        "A proper coloring assigns a color to every vertex so adjacent vertices",
        "have different colors. A list coloring must assign each vertex a color",
        "from that vertex's permitted list. A split graph has a clique (all pairs",
        "adjacent) and an independent set (no pairs adjacent).",
        "",
        f"There are {triple_count} clique vertices c_0 through c_{triple_count - 1}.",
        f"Clique vertex c_i represents triple T_i below and permits every color 1 through {triple_count}.",
        "Two triples intersect when they contain at least one equal element.",
        "For every intersecting pair T_i,T_j, the split graph has one independent",
        "vertex p_{i,j}. It is adjacent to every clique vertex except c_i and c_j,",
        f"and its permitted colors are {n + 1} through {triple_count}, inclusive.",
        "There are no other vertices or edges. This completely defines the graph",
        "and all lists; you do not need to print the full coloring.",
        "",
        "A compact certificate is exactly the IDs of the clique vertices that",
        f"receive the low colors 1 through {n}. It is valid exactly when the chosen",
        "triples are pairwise disjoint. Because each triple has three elements and",
        f"there are {universe} elements, choosing {n} pairwise-disjoint triples",
        "also covers every element. Such a certificate always completes to a list",
        "coloring: give selected clique vertices the low colors, unselected clique",
        "vertices distinct high colors, and each p_{i,j} the high color of an",
        "unselected endpoint.",
        "",
        f"Choose exactly {n} distinct triple IDs from 0 through {triple_count - 1}, inclusive.",
        "Order does not matter. Repeats are forbidden. Element labels are integers",
        f"from 0 through {universe - 1}, inclusive.",
        "",
        "Triples, in the format ID: element element element:",
    ]
    for triple_id, triple in enumerate(inst["triples"]):
        lines.append(f"{triple_id}: {triple[0]} {triple[1]} {triple[2]}")
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags, as a comma-separated list of triple IDs.",
        "Example format: <answer>0, 1, 2</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Extract the first tagged comma/whitespace-separated integer list."""

    try:
        if not isinstance(text, str):
            return None
        match = re.search(r"<answer>(.*?)</answer>", text, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:[A-Za-z0-9_-]+)?\s*", "", body)
        body = re.sub(r"\s*```$", "", body).strip()
        if body.startswith("[") and body.endswith("]"):
            body = body[1:-1].strip()
        if not body:
            return None
        tokens = [token for token in re.split(r"[\s,]+", body) if token]
        if not tokens or any(re.fullmatch(r"[+-]?\d+", token) is None for token in tokens):
            return None
        return [int(token) for token in tokens]
    except Exception:
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any compact coloring certificate; never consult the planted one."""

    n = inst["n"]
    triple_count = inst["triple_count"]
    if not isinstance(answer, list) or any(
        not isinstance(value, int) or isinstance(value, bool) for value in answer
    ):
        return False, "malformed: expected a list of integer triple IDs"
    if not answer:
        return False, f"empty answer: expected exactly {n} triple IDs"
    if len(answer) != n:
        return False, f"wrong length: expected {n} triple IDs, got {len(answer)}"
    for triple_id in answer:
        if triple_id < 0 or triple_id >= triple_count:
            return False, f"out of range: triple ID {triple_id} is not in 0..{triple_count - 1}"
    if len(set(answer)) != len(answer):
        return False, "duplicate triple ID: every selected ID must be distinct"

    owner: dict[int, int] = {}
    for triple_id in answer:
        for element in inst["triples"][triple_id]:
            if element in owner:
                return False, (
                    f"overlap: triples {owner[element]} and {triple_id} both contain "
                    f"element {element}"
                )
            owner[element] = triple_id
    if len(owner) != inst["universe"]:
        missing = min(set(range(inst["universe"])) - set(owner))
        return False, f"not a cover: element {missing} is uncovered"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the statement-implied space of size-n distinct ID sets."""

    return rng.sample(range(inst["triple_count"]), inst["n"])


def search_space(inst: dict) -> int | None:
    """Number of unordered, distinct, in-range candidates."""

    return math.comb(inst["triple_count"], inst["n"])


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the exact number of covers when at most 500,000 candidates."""

    space = search_space(inst)
    if space is None or space > 500_000:
        return None
    count = 0
    for candidate in itertools.combinations(range(inst["triple_count"]), inst["n"]):
        if verify(inst, list(candidate))[0]:
            count += 1
    return count


def _incidence_adjacency(inst: dict) -> list[list[int]]:
    universe = inst["universe"]
    total = universe + inst["triple_count"]
    adjacency = [[] for _ in range(total)]
    for triple_id, triple in enumerate(inst["triples"]):
        triple_vertex = universe + triple_id
        for element in triple:
            adjacency[element].append(triple_vertex)
            adjacency[triple_vertex].append(element)
    for neighbors in adjacency:
        neighbors.sort()
    return adjacency


def canonical_key(inst: dict) -> str:
    """A relabeling-invariant typed incidence-graph fingerprint.

    Exact hypergraph isomorphism is not known to be cheaply canonical.  This key
    uses every rooted all-pairs distance profile plus the way element and triple
    profiles are paired by incidences.  It ignores seed, answer, and input order.
    """

    universe = inst["universe"]
    triple_count = inst["triple_count"]
    adjacency = _incidence_adjacency(inst)
    total = len(adjacency)
    profiles: list[tuple[tuple[int, int], ...]] = []
    for start in range(total):
        distances = [-1] * total
        distances[start] = 0
        queue = deque([start])
        while queue:
            vertex = queue.popleft()
            for neighbor in adjacency[vertex]:
                if distances[neighbor] < 0:
                    distances[neighbor] = distances[vertex] + 1
                    queue.append(neighbor)
        diameter = max(distances)
        histogram = []
        for distance in range(diameter + 1):
            element_count = sum(
                1 for vertex in range(universe) if distances[vertex] == distance
            )
            triple_vertex_count = sum(
                1 for vertex in range(universe, total) if distances[vertex] == distance
            )
            histogram.append((element_count, triple_vertex_count))
        profiles.append(tuple(histogram))

    incidence_pairs = []
    for triple_id, triple in enumerate(inst["triples"]):
        triple_profile = profiles[universe + triple_id]
        for element in triple:
            incidence_pairs.append((profiles[element], triple_profile))
    payload = {
        "sizes": [universe, triple_count],
        "element_profiles": sorted(profiles[:universe]),
        "triple_profiles": sorted(profiles[universe:]),
        "incidence_pairs": sorted(incidence_pairs),
    }
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase crowding first, then grow the regular exact-cover core."""

    n = int(params.get("n", 6))
    degree = int(params.get("degree", 3))
    if degree < 5:
        return {"n": max(n, 24), "degree": 5}
    return {"n": max(n + 1, (3 * n) // 2), "degree": degree}


# ---------------------------------------------------------------------------
# Cheap adversaries used by selftest.


def _conflict_adjacency(inst: dict) -> list[set[int]]:
    by_element = [[] for _ in range(inst["universe"])]
    for triple_id, triple in enumerate(inst["triples"]):
        for element in triple:
            by_element[element].append(triple_id)
    adjacency = [set() for _ in range(inst["triple_count"])]
    for incident in by_element:
        for triple_id in incident:
            adjacency[triple_id].update(other for other in incident if other != triple_id)
    return adjacency


def _greedy_from_order(inst: dict, order) -> list[int]:
    selected = []
    occupied: set[int] = set()
    for triple_id in order:
        triple = inst["triples"][triple_id]
        if occupied.isdisjoint(triple):
            selected.append(triple_id)
            occupied.update(triple)
            if len(selected) == inst["n"]:
                break
    return selected


def _outlier_attack(inst: dict) -> list[int]:
    adjacency = _conflict_adjacency(inst)
    order = sorted(range(inst["triple_count"]), key=lambda i: (len(adjacency[i]), i))
    return order[:inst["n"]]


def _random_restart_attack(inst: dict, rng: random.Random, restarts: int = 256) -> list[int]:
    order = list(range(inst["triple_count"]))
    last = []
    for _ in range(restarts):
        rng.shuffle(order)
        last = _greedy_from_order(inst, order)
        if verify(inst, last)[0]:
            return last
    return last


def _spectral_attack(inst: dict) -> list[int]:
    """Rank from a bottom adjacency eigenvector, then greedily repair both signs."""

    adjacency = _conflict_adjacency(inst)
    size = len(adjacency)
    shift = max(len(neighbors) for neighbors in adjacency) + 1
    rng = random.Random(0x191010364 + size)
    vector = [rng.random() - 0.5 for _ in range(size)]
    mean = sum(vector) / size
    vector = [value - mean for value in vector]
    for _ in range(100):
        updated = [
            shift * vector[i] - sum(vector[j] for j in adjacency[i])
            for i in range(size)
        ]
        norm = math.sqrt(sum(value * value for value in updated)) or 1.0
        vector = [value / norm for value in updated]
    last = []
    for reverse in (False, True):
        order = sorted(range(size), key=lambda i: vector[i], reverse=reverse)
        last = _greedy_from_order(inst, order)
        if verify(inst, last)[0]:
            return last
    return last


def _algorithm_x(inst: dict, node_cap: int = 10_000) -> tuple[list[int] | None, int]:
    """Min-column Algorithm X on the exact-cover matrix, with a node cap."""

    universe = inst["universe"]
    full = (1 << universe) - 1
    masks = []
    by_element = [[] for _ in range(universe)]
    for triple_id, triple in enumerate(inst["triples"]):
        mask = sum(1 << element for element in triple)
        masks.append(mask)
        for element in triple:
            by_element[element].append(triple_id)

    nodes = 0
    partial: list[int] = []

    def visit(covered: int) -> list[int] | bool | None:
        nonlocal nodes
        nodes += 1
        if nodes > node_cap:
            return None
        if covered == full:
            return partial[:]
        remaining = full ^ covered
        best_options = None
        while remaining:
            bit = remaining & -remaining
            element = bit.bit_length() - 1
            remaining -= bit
            options = [
                triple_id for triple_id in by_element[element]
                if masks[triple_id] & covered == 0
            ]
            if not options:
                return False
            if best_options is None or len(options) < len(best_options):
                best_options = options
                if len(best_options) == 1:
                    break
        for triple_id in best_options or []:
            partial.append(triple_id)
            result = visit(covered | masks[triple_id])
            partial.pop()
            if result is None or result:
                return result
        return False

    result = visit(0)
    return (result if isinstance(result, list) else None), nodes


def _relabel_instance(
    inst: dict, element_map: list[int], old_triple_order: list[int]
) -> tuple[dict, list[int]]:
    """Apply an element relabeling and clique/triple renumbering."""

    old_to_new = {old: new for new, old in enumerate(old_triple_order)}
    triples = [
        tuple(element_map[element] for element in inst["triples"][old])
        for old in old_triple_order
    ]
    carried_answer = [old_to_new[old] for old in inst["answer"]]
    changed = dict(inst)
    changed["triples"] = triples
    changed["answer"] = carried_answer
    return changed, carried_answer


def selftest() -> dict:
    """Run gates G1--G8 and return their measured, JSON-serializable report."""

    report: dict[str, object] = {
        "paper": "arXiv:1910.10364",
        "family": "regular exact-cover core encoded as split-graph list coloring",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1: all presets, several independent seeds.
    planted_checks = 0
    planted_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 19):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            planted_checks += 1
            if not ok:
                planted_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not planted_failures,
        "checks": planted_checks,
        "failures": planted_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=271828, **shipping)
    planted = list(inst["answer"])
    unselected = next(i for i in range(inst["triple_count"]) if i not in set(planted))
    corruptions = {
        "drop_one": planted[:-1],
        "replace_one": [unselected] + planted[1:],
        "duplicate": [planted[0]] + planted[:-1],
        "empty": [],
        "out_of_range": [inst["triple_count"]] + planted[1:],
    }
    corruption_reasons = {}
    all_rejected = True
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        all_rejected &= not ok
        corruption_reasons[name] = reason
    distinct_reasons = len(set(corruption_reasons.values())) == len(corruption_reasons)
    report["G2_rejects_corruption"] = {
        "pass": all_rejected and distinct_reasons,
        "rejected": sum(not verify(inst, candidate)[0] for candidate in corruptions.values()),
        "attempts": len(corruptions),
        "distinct_reasons": distinct_reasons,
        "reasons": corruption_reasons,
    }

    answer_body = ", ".join(map(str, planted))
    model_reply = (
        "I checked the disjointness constraints.\n```text\n"
        f"<answer>\n{answer_body}\n</answer>\n```\nThat is my final certificate."
    )
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_items": len(parsed) if isinstance(parsed, list) else None,
        "surrounding_prose_and_fence": True,
    }

    # G4: sample the structure-aware space: exactly n distinct in-range IDs.
    guess_rng = random.Random(314159265)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "prior": "uniform over unordered size-n subsets of distinct in-range triple IDs",
        "naive_search_space": search_space(inst),
    }

    # G5: measure the same shipping instance used by G4.  Its density estimate
    # is over exactly the language declared in CERTIFICATE_LANGUAGE.  The exact
    # small count is retained only as an explicitly labelled calibration.
    baseline_node_cap = 10_000
    baseline_started = time.perf_counter()
    baseline_candidate, baseline_nodes = _algorithm_x(inst, baseline_node_cap)
    baseline_seconds = time.perf_counter() - baseline_started
    baseline_verified = verify(inst, baseline_candidate)[0]

    small = make_instance(n=5, degree=3, seed=0)
    small_count = enumerate_all(small)
    small_space = search_space(small)
    small_fraction = small_count / small_space if small_count is not None else None
    report["G5_sparse"] = {
        "pass": (
            guess_rate < 1e-3
            and not baseline_verified
            and baseline_nodes > 0
            and baseline_seconds >= 0.0
            and small_count is not None
            and small_fraction is not None
            and small_fraction < 1e-3
        ),
        "shipping_preset": SHIPPING_DIFFICULTY,
        "shipping_n": inst["n"],
        "shipping_degree": inst["degree"],
        "density": {
            "method": "uniform random_candidate sampling",
            "instance_seed": 271828,
            "sampler_seed": 314159265,
            "hits": guess_hits,
            "sample_size": guess_total,
            "observed_fraction": guess_rate,
            "candidate_space": search_space(inst),
        },
        "baseline": {
            "attack": "min-column Algorithm X",
            "instance_seed": 271828,
            "result": (
                "verified witness"
                if baseline_verified
                else "node cap reached"
                if baseline_nodes > baseline_node_cap
                else "search exhausted without a witness"
            ),
            "wall_seconds": baseline_seconds,
            "nodes": baseline_nodes,
            "node_cap": baseline_node_cap,
        },
        "small_exact_calibration": {
            "n": small["n"],
            "degree": small["degree"],
            "valid_answers": small_count,
            "candidate_space": small_space,
            "solution_fraction": small_fraction,
        },
    }

    attack_names = (
        "outlier_conflict_degree",
        "greedy_input_order",
        "random_restart_256",
        "spectral_bottom_eigenvector",
        "algorithm_x_min_column_10000",
    )
    successes = {name: 0 for name in attack_names}
    algorithm_nodes = []
    attack_attempts = 8
    for offset in range(attack_attempts):
        attack_inst = make_instance(seed=700 + offset, **shipping)
        candidates = {
            "outlier_conflict_degree": _outlier_attack(attack_inst),
            "greedy_input_order": _greedy_from_order(
                attack_inst, range(attack_inst["triple_count"])
            ),
            "random_restart_256": _random_restart_attack(
                attack_inst, random.Random(90_000 + offset), 256
            ),
            "spectral_bottom_eigenvector": _spectral_attack(attack_inst),
        }
        algorithm_candidate, nodes = _algorithm_x(attack_inst, 10_000)
        candidates["algorithm_x_min_column_10000"] = algorithm_candidate
        algorithm_nodes.append(nodes)
        for name, candidate in candidates.items():
            successes[name] += int(verify(attack_inst, candidate)[0])
    attacks = {
        name: {"successes": successes[name], "attempts": attack_attempts}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(value == 0 for value in successes.values()),
        "attacks": attacks,
        "algorithm_x_node_cap": 10_000,
        "algorithm_x_nodes_min": min(algorithm_nodes),
        "algorithm_x_nodes_max": max(algorithm_nodes),
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=1618033, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["triple_count"] > inst["triple_count"],
        "base_n": inst["n"],
        "doubled_n": doubled["n"],
        "base_triples": inst["triple_count"],
        "doubled_triples": doubled["triple_count"],
        "doubled_verify_reason": doubled_reason,
        "base_search_space_digits": len(str(search_space(inst))),
        "doubled_search_space_digits": len(str(search_space(doubled))),
    }

    invariance_checks = 0
    invariant_successes = 0
    real_transform_checks = 0
    real_transform_successes = 0
    unrelated_keys = []
    for offset in range(20):
        key_inst = make_instance(seed=20_000 + offset, **shipping)
        original_key = canonical_key(key_inst)
        unrelated_keys.append(original_key)
        transform_rng = random.Random(50_000 + offset)
        element_map = list(range(key_inst["universe"]))
        transform_rng.shuffle(element_map)
        triple_order = list(range(key_inst["triple_count"]))
        transform_rng.shuffle(triple_order)
        identity_elements = list(range(key_inst["universe"]))
        identity_triples = list(range(key_inst["triple_count"]))
        transformations = (
            (element_map, identity_triples),
            (identity_elements, triple_order),
            (element_map, triple_order),
        )
        for elem_map, order in transformations:
            changed, carried = _relabel_instance(key_inst, elem_map, order)
            invariance_checks += 1
            invariant_successes += int(canonical_key(changed) == original_key)
            real_transform_checks += 1
            real_transform_successes += int(verify(changed, carried)[0])
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": (
            invariant_successes == invariance_checks
            and real_transform_successes == real_transform_checks
            and distinct_count == len(unrelated_keys)
        ),
        "invariance_successes": invariant_successes,
        "invariance_checks": invariance_checks,
        "real_transform_successes": real_transform_successes,
        "real_transform_checks": real_transform_checks,
        "distinct_unrelated_keys": distinct_count,
        "unrelated_instances": len(unrelated_keys),
        "transformations": [
            "element relabeling",
            "triple/clique renumbering",
            "composition of both (including within-triple reorder)",
        ],
        "key_kind": "typed incidence all-distance fingerprint; not complete GI canonicalization",
    }

    gates = [
        value for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    ]
    report["all_passed"] = all(
        isinstance(gate, dict) and bool(gate.get("pass")) for gate in gates
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
