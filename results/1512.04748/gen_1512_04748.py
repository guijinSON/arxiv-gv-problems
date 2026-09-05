"""Verified generator for total-domatic partitions from arXiv:1512.04748.

The paper proves that every cubic graph with no copy of its obstruction L has
two disjoint total dominating sets.  This module composes the certificate from
a hidden factor of 4-cycles: two consecutive vertices of each square receive
one colour and the other two receive the other colour.  A random perfect
matching supplies the third edge at every vertex.  Thus generation never solves
the displayed graph.

The displayed vertex names and adjacency rows are independently shuffled.  A
reference solver, which never reads ``inst["answer"]``, recovers a 4-cycle
factor and colours it.  That deliberately successful algorithm is reported as
Track B's mechanical route.
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
try:  # Present in the repository; this finite graph family does not need it.
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - graceful standard-library fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "simple cubic graph",
        "open neighborhoods",
        "two total dominating colour classes",
    ],
    "verification_operations": [
        "exact graph adjacency lookup",
        "integer colour comparison",
        "open-neighborhood colour-set equality",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Recognize a spanning factor of 4-cycles and use each square's internal "
        "neighbors to witness both colours; without that decomposition one must "
        "solve the shuffled neighborhood constraints mechanically."
    ),
    "hardness_basis": (
        "Track B: Section 2, Lemma 2 and Theorem 2 give a constructive algorithm "
        "for the L-free cubic regime; the executable bounded-decoy C4-factor "
        "reference algorithm runs in O(V*Delta^3 + 2^d*V), where d is the number "
        "of non-factor 4-cycles.  At shipping V=224 and d=0 it solved 8/8 in "
        "0.001250 seconds on average with 7,056 counted operations, whereas the "
        "compact square-factor route uses 280 local selections/colour assignments "
        "and is not mechanically executable in the no-tool prompt context."
    ),
    "max_answer_tokens": 113,
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


# n is the number of planted squares; the graph has 4n vertices.  The named
# ladder also raises the number of misleading overlapping squares and the label
# range.  ``escalate`` raises only the decoy count, keeping the answer length
# fixed, before considering the 256-atom cap.
DIFFICULTY = {
    "demo": {"n": 3, "decoy_cycles": 0, "label_bound": 97},
    "easy": {"n": 56, "decoy_cycles": 0, "label_bound": 1000003},
    "medium": {"n": 58, "decoy_cycles": 3, "label_bound": 1000003},
    "hard": {"n": 58, "decoy_cycles": 4, "label_bound": 1000003},
}

SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Look for a spanning factor of 4-cycles whose internal edges alone can "
    "witness both neighborhood colours."
)
PLACEBO_HINT = (
    "Track every displayed vertex carefully and check all three neighbors "
    "before finalizing the colour list."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly one bit for every displayed vertex, in the "
        "displayed vertex order; 0 and 1 name the two total dominating sets."
    ),
    "bounds": {
        "length": "four times n",
        "alphabet": [0, 1],
        "candidate_count": "2^(4n)",
        "shipping_max_atoms": 232,
    },
}

NOTES = (
    "Section 1 fixes the exact native definitions: a total dominating set meets "
    "the open neighborhood of every vertex, and a 2-coupon coloring is exactly "
    "a partition into two such sets. Lemma 1 identifies triangles and 4-cycles "
    "as the local structure of L-free cubic graphs. Lemma 2 explicitly provides "
    "an iterative F-partition algorithm, and Theorem 2 colors its pieces; this "
    "polynomial constructive route rules out Track A for the theorem's regime. "
    "The easy regimes noted in the paper are r-regular graphs for r>=4 by "
    "Theorem 1 and cycles precisely when their order is divisible by four. "
    "Here each vertex is placed in a planted C4 before a random external perfect "
    "matching is sampled, so no vertex can be the center of the ten-vertex "
    "radius-two tree L. Each planted square is colored 0011 cyclically, with an "
    "independent random rotation, before all vertex names and rows are shuffled. "
    "Degree/cycle-incidence, label parity, display-period, BFS parity, centered "
    "spectral, one-pass greedy, and randomized greedy attacks are measured; the "
    "successful C4-factor algorithm is reported separately as Track B's "
    "reference route."
)


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"^\s*```(?:json|python)?\s*(.*?)\s*```\s*$", re.I | re.S)
_GUESS_SAMPLES = 200_000

# These are diagnostics, not local gates.  They are updated after the three
# script-owned oracle runs; their transcript files remain authoritative.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0, "service_errors": 4},
    "hinted": {"solved": 0, "attempts": 0, "service_errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "service_errors": 4},
    "hinted_verdict": "unreachable",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_params(n, decoy_cycles, label_bound, seed):
    if not _is_int(n) or n < 3:
        raise ValueError("n must be an integer at least 3 (the number of squares)")
    if not _is_int(decoy_cycles) or not 0 <= decoy_cycles <= 8:
        raise ValueError("decoy_cycles must be an integer from 0 through 8")
    if not _is_int(label_bound) or label_bound <= 4 * n:
        raise ValueError("label_bound must exceed the number of vertices")
    if not _is_int(seed):
        raise ValueError("seed must be an integer")


def _base_adjacency(n):
    adjacency = [set() for _ in range(4 * n)]
    for block in range(n):
        for port in range(4):
            u = 4 * block + port
            v = 4 * block + (port + 1) % 4
            adjacency[u].add(v)
            adjacency[v].add(u)
    return adjacency


def _four_cycles(adjacency, counts=None):
    """Return all 4-cycles as vertex sets in a simple maximum-degree-3 graph."""
    cycles = set()
    for u, neighbors in enumerate(adjacency):
        for a in neighbors:
            if counts is not None:
                counts["path_steps"] += 1
            for v in adjacency[a]:
                if counts is not None:
                    counts["path_steps"] += 1
                if v == u:
                    continue
                for b in adjacency[v]:
                    if counts is not None:
                        counts["path_steps"] += 1
                    if b != a and u in adjacency[b]:
                        cycle = tuple(sorted((u, a, v, b)))
                        if len(set(cycle)) == 4:
                            cycles.add(cycle)
    return sorted(cycles)


def _connected(adjacency):
    seen = {0}
    stack = [0]
    while stack:
        u = stack.pop()
        for v in adjacency[u]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return len(seen) == len(adjacency)


def _sample_matching(n, target_decoys, rng):
    """Sample a connected matching with exactly target_decoys extra C4s."""
    vertex_count = 4 * n
    base_cycles = {tuple(range(4 * b, 4 * b + 4)) for b in range(n)}
    vertices = list(range(vertex_count))
    # Exact decoy counts 0--5 occur with constant-ish probability in this sparse
    # model.  The generous deterministic cap protects malformed extreme params.
    for attempt in range(200_000):
        rng.shuffle(vertices)
        matching = []
        admissible = True
        for i in range(0, vertex_count, 2):
            u, v = vertices[i], vertices[i + 1]
            if u // 4 == v // 4:
                admissible = False
                break
            matching.append((u, v))
        if not admissible:
            continue
        adjacency = _base_adjacency(n)
        for u, v in matching:
            adjacency[u].add(v)
            adjacency[v].add(u)
        if not _connected(adjacency):
            continue
        cycles = set(_four_cycles(adjacency))
        if not base_cycles.issubset(cycles):
            raise AssertionError("a planted square disappeared")
        if len(cycles - base_cycles) == target_decoys:
            return adjacency, matching, attempt + 1
    raise RuntimeError(
        "could not sample the requested decoy-cycle count within the work cap"
    )


def make_instance(n, seed=0, **params):
    """Inverse-generate a connected cubic coupon-colouring instance.

    The four-cycle factor and one of its valid local colourings are sampled
    before the external perfect matching.  No coloring of the completed graph
    is searched for.
    """
    decoy_cycles = params.pop("decoy_cycles", 0)
    label_bound = params.pop("label_bound", max(97, 20 * n + 1))
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, decoy_cycles, label_bound, seed)
    rng = random.Random(seed)

    hidden_colors = [0] * (4 * n)
    rotations = []
    for block in range(n):
        rotation = rng.randrange(4)
        rotations.append(rotation)
        hidden_colors[4 * block + rotation] = 1
        hidden_colors[4 * block + (rotation + 1) % 4] = 1

    adjacency, _matching, sampling_attempts = _sample_matching(
        n, decoy_cycles, rng
    )

    hidden_vertices = list(range(4 * n))
    labels = rng.sample(range(1, label_bound + 1), 4 * n)
    display_hidden = list(hidden_vertices)
    rng.shuffle(display_hidden)
    vertex_order = [labels[v] for v in display_hidden]
    display_position = {v: i for i, v in enumerate(display_hidden)}

    neighbors = []
    for hidden in display_hidden:
        row = [display_position[v] for v in adjacency[hidden]]
        rng.shuffle(row)
        neighbors.append(row)
    answer = [hidden_colors[v] for v in display_hidden]

    return {
        "n": n,
        "vertex_count": 4 * n,
        "decoy_cycles": decoy_cycles,
        "label_bound": label_bound,
        "vertex_order": vertex_order,
        "neighbors": neighbors,
        "sampling_attempts": sampling_attempts,
        "answer": answer,
    }


def render(inst):
    """Render the complete self-contained problem and optional diagnostic hint."""
    lines = [
        "Find a two-colour total-domatic partition of the displayed graph.",
        "",
        "Definitions.",
        "The graph is finite, undirected, simple (no loops or repeated edges),",
        "and cubic (every vertex has exactly three distinct neighbors). The open",
        "neighborhood of a vertex consists of its three neighbors, not the vertex",
        "itself. A set is total dominating when every vertex has at least one",
        "neighbor in that set. A valid two-colouring assigns every vertex colour",
        "0 or 1 so that both colour classes are total dominating. Equivalently,",
        "the three neighbors of every vertex must include at least one 0 and at",
        "least one 1. The two colour names may be globally exchanged.",
        "",
        f"There are {inst['vertex_count']} vertices. Vertex identifiers are arbitrary",
        "positive integers. In the output, bit i colours the vertex in position i",
        "of the following order; positions are 1-based in this explanation:",
        "  " + " ".join(str(v) for v in inst["vertex_order"]),
        "",
        "Adjacency list (each undirected edge consequently appears in two rows):",
    ]
    labels = inst["vertex_order"]
    for index, label in enumerate(labels):
        neighbor_labels = sorted(labels[j] for j in inst["neighbors"][index])
        lines.append(
            "  " + str(label) + ": " + " ".join(str(v) for v in neighbor_labels)
        )
    lines.extend([
        "",
        f"Output exactly {inst['vertex_count']} comma-separated bits as one JSON list,",
        "in the displayed vertex order. Only the integers 0 and 1 are allowed;",
        "list order matters, no position may be omitted, and no extra position",
        "may be inserted. Bit values themselves may of course repeat.",
        "",
        "Give your final answer inside <answer></answer> tags, as that JSON list.",
        "Example syntax for four slots only: <answer>[0,1,1,0]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Extract a JSON bit list from tagged, fenced, or prose-surrounded output."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    candidates = list(reversed(matches))
    if not candidates:
        candidates = re.findall(r"\[[\s\d,\-+]*\]", text, re.S)
        candidates.reverse()
    for candidate in candidates:
        fenced = _FENCE_RE.match(candidate)
        if fenced:
            candidate = fenced.group(1)
        candidate = candidate.strip()
        try:
            value = json.loads(candidate)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, list):
            return value
    return None


def verify(inst, answer):
    """Check any candidate coloring exactly, without consulting the planted one."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer list is empty"
    expected = inst.get("vertex_count")
    if len(answer) < expected:
        return False, f"answer is too short: expected {expected} bits"
    if len(answer) > expected:
        return False, f"answer is too long: expected {expected} bits"
    for i, bit in enumerate(answer):
        if not _is_int(bit) or bit not in (0, 1):
            return False, f"entry {i + 1} is not the integer 0 or 1"
    neighbors = inst.get("neighbors")
    labels = inst.get("vertex_order")
    if not isinstance(neighbors, list) or len(neighbors) != expected:
        return False, "instance has a malformed adjacency table"
    if not isinstance(labels, list) or len(labels) != expected:
        return False, "instance has a malformed vertex order"
    for i, row in enumerate(neighbors):
        if (
            not isinstance(row, list)
            or len(row) != 3
            or any(not _is_int(v) or not 0 <= v < expected for v in row)
            or len(set(row)) != 3
        ):
            return False, f"instance has a malformed neighborhood at {labels[i]}"
        seen = {answer[v] for v in row}
        if seen != {0, 1}:
            only = next(iter(seen)) if seen else "no"
            return False, (
                f"vertex {labels[i]} has a monochromatic open neighborhood "
                f"of colour {only}"
            )
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from the stated, structure-aware language of bit lists."""
    vertex_count = inst["vertex_count"]
    mask = rng.getrandbits(vertex_count)
    return [(mask >> i) & 1 for i in range(vertex_count)]


def search_space(inst):
    return 1 << inst["vertex_count"]


def enumerate_all(inst):
    vertex_count = inst["vertex_count"]
    if vertex_count > 22:
        return None
    count = 0
    for mask in range(1 << vertex_count):
        answer = [(mask >> i) & 1 for i in range(vertex_count)]
        count += int(verify(inst, answer)[0])
    return count


def _wl_root_profile(neighbors, root):
    """A label-independent rooted 1-WL profile for a strong cheap invariant."""
    n = len(neighbors)
    colors = [1 if v == root else 0 for v in range(n)]
    history = []
    for _ in range(n):
        signatures = [
            (colors[v], tuple(sorted(colors[w] for w in neighbors[v])))
            for v in range(n)
        ]
        kinds = {signature: i for i, signature in enumerate(sorted(set(signatures)))}
        new_colors = [kinds[signature] for signature in signatures]
        counts = {}
        for color in new_colors:
            counts[color] = counts.get(color, 0) + 1
        snapshot = (new_colors[root], tuple(sorted(counts.values())))
        history.append(snapshot)
        # Refinement includes the old colour, so colour classes never merge.
        # Numeric colour IDs can be permuted between stable rounds; equality of
        # the class count, not equality of those incidental IDs, is the stop test.
        if len(set(new_colors)) == len(set(colors)):
            break
        colors = new_colors
    return tuple(history)


def canonical_key(inst):
    """Strong relabeling invariant: rooted WL profiles plus cycle statistics."""
    neighbors = [tuple(row) for row in inst["neighbors"]]
    adjacency = [set(row) for row in neighbors]
    cycle_counts = [0] * len(neighbors)
    cycles = _four_cycles(adjacency)
    for cycle in cycles:
        for v in cycle:
            cycle_counts[v] += 1
    rooted = sorted(_wl_root_profile(neighbors, root) for root in range(len(neighbors)))
    payload = {
        "vertices": len(neighbors),
        "four_cycles": len(cycles),
        "cycle_incidence": sorted(cycle_counts),
        "rooted_wl": rooted,
    }
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _cycle_factor(inst, counts=None):
    """Find a vertex-disjoint C4 cover by Algorithm X on the short-cycle list."""
    if counts is None:
        counts = {
            "path_steps": 0,
            "cover_nodes": 0,
            "incidence_checks": 0,
            "branches": 0,
        }
    adjacency = [set(row) for row in inst["neighbors"]]
    cycles = _four_cycles(adjacency, counts)
    by_vertex = [[] for _ in adjacency]
    masks = []
    for index, cycle in enumerate(cycles):
        mask = 0
        for v in cycle:
            mask |= 1 << v
            by_vertex[v].append(index)
        masks.append(mask)
    full = (1 << len(adjacency)) - 1

    def visit(covered):
        counts["cover_nodes"] += 1
        if covered == full:
            return []
        best = None
        choices = None
        for v in range(len(adjacency)):
            if covered >> v & 1:
                continue
            available = []
            for cycle_index in by_vertex[v]:
                counts["incidence_checks"] += 1
                if not (masks[cycle_index] & covered):
                    available.append(cycle_index)
            if not available:
                return None
            if choices is None or len(available) < len(choices):
                best, choices = v, available
                if len(choices) == 1:
                    break
        if best is None:
            return []
        for cycle_index in choices:
            counts["branches"] += 1
            suffix = visit(covered | masks[cycle_index])
            if suffix is not None:
                return [cycles[cycle_index]] + suffix
        return None

    return visit(0), counts


def _reference_solve(inst):
    """Recover and color a C4 factor without using construction metadata."""
    counts = {
        "path_steps": 0,
        "cover_nodes": 0,
        "incidence_checks": 0,
        "branches": 0,
    }
    factor, counts = _cycle_factor(inst, counts)
    if factor is None:
        return None, counts
    adjacency = [set(row) for row in inst["neighbors"]]
    answer = [None] * inst["vertex_count"]
    for cycle in factor:
        cycle_set = set(cycle)
        start = min(cycle)
        adjacent = sorted(adjacency[start] & cycle_set)
        if len(adjacent) != 2:
            return None, counts
        first, last = adjacent
        opposite = next(v for v in cycle if v not in (start, first, last))
        answer[start] = 0
        answer[first] = 0
        answer[opposite] = 1
        answer[last] = 1
        counts["colour_assignments"] = counts.get("colour_assignments", 0) + 4
    return answer, counts


def _attack_label_parity(inst):
    return [label & 1 for label in inst["vertex_order"]]


def _attack_display_period(inst):
    return [(i // 2) & 1 for i in range(inst["vertex_count"])]


def _attack_cycle_incidence(inst):
    adjacency = [set(row) for row in inst["neighbors"]]
    incidence = [0] * len(adjacency)
    for cycle in _four_cycles(adjacency):
        for v in cycle:
            incidence[v] += 1
    return [
        (incidence[i] + inst["vertex_order"][i]) & 1
        for i in range(len(adjacency))
    ]


def _attack_bfs_parity(inst):
    n = inst["vertex_count"]
    colors = [None] * n
    for start in range(n):
        if colors[start] is not None:
            continue
        colors[start] = 0
        queue = [start]
        cursor = 0
        while cursor < len(queue):
            u = queue[cursor]
            cursor += 1
            for v in inst["neighbors"][u]:
                if colors[v] is None:
                    colors[v] = 1 - colors[u]
                    queue.append(v)
    return colors


def _attack_spectral_nontrivial(inst):
    """Threshold a centered nontrivial adjacency eigenvector.

    A cubic graph's leading adjacency eigenvector is the constant vector.  Power
    iteration on A+3I, with the mean removed each round, targets the next
    algebraic eigendirection while damping large negative eigenvalues.  This is
    the dependency-free cheap spectral attack appropriate to a planted graph
    partition.
    """
    n = inst["vertex_count"]
    rng = random.Random(0x5EEC7A1)
    vector = [rng.uniform(-1.0, 1.0) for _ in range(n)]
    mean = sum(vector) / n
    vector = [value - mean for value in vector]
    for _ in range(96):
        nxt = [
            3.0 * vector[v] + sum(vector[w] for w in inst["neighbors"][v])
            for v in range(n)
        ]
        mean = sum(nxt) / n
        nxt = [value - mean for value in nxt]
        norm = math.sqrt(sum(value * value for value in nxt))
        if norm == 0.0:
            break
        vector = [value / norm for value in nxt]
    median = sorted(vector)[n // 2]
    return [int(value >= median) for value in vector]


def _greedy_candidate(inst, rng, random_order):
    """One-pass NAE greedy: prevent only constraints completed so far."""
    n = inst["vertex_count"]
    order = list(range(n))
    if random_order:
        rng.shuffle(order)
    assignment = [None] * n
    containing = [[] for _ in range(n)]
    for center, row in enumerate(inst["neighbors"]):
        for vertex in row:
            containing[vertex].append(center)
    operations = 0
    for vertex in order:
        preferred = rng.randrange(2) if random_order else (
            inst["vertex_order"][vertex] & 1
        )
        allowed = []
        for value in (preferred, 1 - preferred):
            assignment[vertex] = value
            bad = False
            for center in containing[vertex]:
                operations += 1
                values = [assignment[x] for x in inst["neighbors"][center]]
                if None not in values and len(set(values)) == 1:
                    bad = True
                    break
            if not bad:
                allowed.append(value)
        if not allowed:
            assignment[vertex] = preferred
        else:
            assignment[vertex] = allowed[0]
    return assignment, operations


def _attack_random_greedy(inst, rng, restarts):
    operations = 0
    last = None
    for _ in range(restarts):
        last, used = _greedy_candidate(inst, rng, True)
        operations += used
        if verify(inst, last)[0]:
            return last, True, operations
    return last, False, operations


def _relabel_instance(inst, rng):
    """Compose vertex renaming, row permutation, and neighbor reordering."""
    n = inst["vertex_count"]
    old_order = list(range(n))
    rng.shuffle(old_order)
    old_to_new = {old: new for new, old in enumerate(old_order)}
    new_labels = rng.sample(range(10_000_000, 20_000_000), n)
    neighbors = []
    answer = []
    for old in old_order:
        row = [old_to_new[v] for v in inst["neighbors"][old]]
        rng.shuffle(row)
        neighbors.append(row)
        answer.append(inst["answer"][old])
    return {
        "n": inst["n"],
        "vertex_count": n,
        "decoy_cycles": inst["decoy_cycles"],
        "label_bound": 20_000_000,
        "vertex_order": new_labels,
        "neighbors": neighbors,
        "sampling_attempts": inst["sampling_attempts"],
        "answer": answer,
    }


def _find_bad_swap(inst):
    answer = inst["answer"]
    zeros = [i for i, value in enumerate(answer) if value == 0]
    ones = [i for i, value in enumerate(answer) if value == 1]
    for i in zeros:
        for j in ones:
            trial = list(answer)
            trial[i], trial[j] = trial[j], trial[i]
            if not verify(inst, trial)[0]:
                return trial
    raise AssertionError("could not find a rejecting two-position colour swap")


def escalate(params):
    """Add overlapping decoy squares at fixed answer length before the cap."""
    params = dict(params)
    decoys = params.get("decoy_cycles", 0)
    if decoys < 5:
        params["n"] = max(params.get("n", 0), 58)
        params["decoy_cycles"] = decoys + 1
        params["label_bound"] = max(params.get("label_bound", 0), 1_000_003)
        return params
    # More vertices would exceed the 300-operation intended-route cap, and the
    # 232-atom answer is already near the published 256-atom cap.  The harness
    # will classify this measured boundary as cap_bound rather than too_easy.
    return None


def selftest():
    """Run the nine mandatory local gates and return JSON-native measurements."""
    report = {
        "paper": "1512.04748",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    g1_failures = []
    g1_attempts = 0
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 7, 29):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            json_roundtrips += int(json_ok)
            if not ok or not json_ok:
                g1_failures.append([preset, seed, why, json_ok])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "json_native_roundtrips": json_roundtrips,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=151204748, **shipping_params)
    planted = shipping["answer"]
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two_colours": _find_bad_swap(shipping),
        "duplicate_one": planted + [planted[-1]],
        "empty": [],
        "out_of_range": [2] + planted[1:],
    }
    corruption_cases = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, why = verify(shipping, candidate)
        corruption_cases[name] = {"accepted": bool(ok), "reason": why}
        reasons.append(why)
    report["G2_rejects_corruption"] = {
        "pass": (
            all(not case["accepted"] for case in corruption_cases.values())
            and len(set(reasons)) == len(reasons)
        ),
        "cases": corruption_cases,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "I used the square decomposition.\n\n<answer>\n```json\n"
        + json.dumps(planted)
        + "\n```\n</answer>\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and verify(shipping, parsed)[0],
        "parsed": parsed is not None,
        "roundtrip_equal": parsed == planted,
    }

    guess_rng = random.Random(0x151204748)
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(_GUESS_SAMPLES):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_wall = time.perf_counter() - guess_start
    guess_fraction = guess_hits / _GUESS_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": _GUESS_SAMPLES >= 200_000 and guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": _GUESS_SAMPLES,
        "observed_fraction": guess_fraction,
        "structure_aware_space": search_space(shipping),
        "prior": "uniform over all length-V bit lists, exactly the stated language",
        "wall_clock_sec": round(guess_wall, 6),
    }

    attack_names = [
        "outlier_cycle_incidence",
        "label_parity",
        "display_period_0011",
        "bfs_parity",
        "spectral_nontrivial_eigenvector",
        "greedy_one_pass",
        "random_greedy_restart_64",
    ]
    attacks = {
        name: {"successes": 0, "attempts": 0, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    reference = {
        "name": "bounded-decoy C4 enumeration plus Algorithm X",
        "complexity": "O(V*Delta^3 + 2^d*V), Delta=3 and d=non-factor C4s",
        "successes": 0,
        "attempts": 0,
        "wall_clock_sec": 0.0,
        "path_steps": 0,
        "cover_nodes": 0,
        "incidence_checks": 0,
        "branches": 0,
        "colour_assignments": 0,
    }
    random_greedy_operations = 0
    for seed in range(8):
        inst = make_instance(seed=80_000 + seed, **shipping_params)
        rng = random.Random(90_000 + seed)
        start = time.perf_counter()
        greedy, greedy_operations = _greedy_candidate(inst, rng, False)
        greedy_elapsed = time.perf_counter() - start
        start = time.perf_counter()
        restarted, _won, restart_operations = _attack_random_greedy(inst, rng, 64)
        restart_elapsed = time.perf_counter() - start
        random_greedy_operations += restart_operations
        candidates = {
            "outlier_cycle_incidence": _attack_cycle_incidence(inst),
            "label_parity": _attack_label_parity(inst),
            "display_period_0011": _attack_display_period(inst),
            "bfs_parity": _attack_bfs_parity(inst),
            "spectral_nontrivial_eigenvector": _attack_spectral_nontrivial(inst),
            "greedy_one_pass": greedy,
            "random_greedy_restart_64": restarted,
        }
        for name, candidate in candidates.items():
            start = time.perf_counter()
            won = verify(inst, candidate)[0]
            attacks[name]["wall_clock_sec"] += time.perf_counter() - start
            attacks[name]["successes"] += int(won)
            attacks[name]["attempts"] += 1
        attacks["greedy_one_pass"]["wall_clock_sec"] += greedy_elapsed
        attacks["random_greedy_restart_64"]["wall_clock_sec"] += restart_elapsed

        start = time.perf_counter()
        recovered, counts = _reference_solve(inst)
        reference["wall_clock_sec"] += time.perf_counter() - start
        reference["attempts"] += 1
        reference["successes"] += int(
            recovered is not None and verify(inst, recovered)[0]
        )
        for field in (
            "path_steps", "cover_nodes", "incidence_checks", "branches",
            "colour_assignments",
        ):
            reference[field] += counts.get(field, 0)

    for attack in attacks.values():
        attack["wall_clock_sec"] = round(attack["wall_clock_sec"], 6)
    reference["wall_clock_sec"] = round(reference["wall_clock_sec"] / 8, 6)
    for field in (
        "path_steps", "cover_nodes", "incidence_checks", "branches",
        "colour_assignments",
    ):
        reference[field] = round(reference[field] / 8, 3)
    reference["operations"] = int(
        reference["path_steps"]
        + reference["incidence_checks"]
        + reference["branches"]
        + reference["colour_assignments"]
    )
    reference["solves"] = (
        f"{reference['successes']}/{reference['attempts']}, as expected"
    )
    all_attacks_failed = all(
        result["successes"] == 0 and result["attempts"] >= 8
        for result in attacks.values()
    )
    intended_operations = 5 * shipping["n"] + 2 * shipping["decoy_cycles"]
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference["successes"] == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "recognize C4 factor and assign a cyclic 0011 pattern per square",
            "operations": intended_operations,
        },
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count_start = time.perf_counter()
    demo_count = enumerate_all(demo)
    demo_count_wall = time.perf_counter() - demo_count_start
    strongest = attacks["random_greedy_restart_64"]
    report["G5_density_and_baseline_cost"] = {
        "pass": (
            guess_fraction < 1e-6
            and demo_count is not None
            and strongest["successes"] == 0
            and reference["successes"] == 8
        ),
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": _GUESS_SAMPLES,
        "shipping_sampled_density": guess_fraction,
        "shipping_candidate_space": search_space(shipping),
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "demo_count_wall_sec": round(demo_count_wall, 6),
        "strongest_failing_attack": "random_greedy_restart_64",
        "baseline_attack_restarts": 64 * 8,
        "baseline_attack_operations": random_greedy_operations,
        "baseline_attack_wall_sec": strongest["wall_clock_sec"],
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled_params["label_bound"] = max(
        doubled_params["label_bound"], 20 * doubled_params["n"] + 1
    )
    start = time.perf_counter()
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": bool(doubled_ok),
        "base_squares": shipping["n"],
        "base_vertices": shipping["vertex_count"],
        "doubled_squares": doubled["n"],
        "doubled_vertices": doubled["vertex_count"],
        "build_wall_sec": round(doubled_build, 6),
        "verify_reason": doubled_why,
    }

    invariant_checks = 0
    carried_checks = 0
    distinct_keys = []
    g8_failures = []
    g8_params = dict(DIFFICULTY["easy"])
    for seed in range(20):
        inst = make_instance(seed=110_000 + seed, **g8_params)
        transformed = _relabel_instance(inst, random.Random(120_000 + seed))
        invariant_checks += 1
        if canonical_key(inst) != canonical_key(transformed):
            g8_failures.append([seed, "key changed under composed relabeling"])
        carried_checks += 1
        if not verify(transformed, transformed["answer"])[0]:
            g8_failures.append([seed, "carried coloring did not verify"])
        distinct_keys.append(canonical_key(inst))
    distinct_count = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": (
            not g8_failures
            and invariant_checks >= 20
            and carried_checks >= 20
            and distinct_count == 20
        ),
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct_count,
        "failures": g8_failures,
        "key_kind": "rooted Weisfeiler-Leman plus exact 4-cycle incidence invariant",
    }

    answer_blob = json.dumps(planted, separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(planted)
    arms = {
        name: {
            "solved": int(G9_ORACLE_RESULTS[name]["solved"]),
            "attempts": int(G9_ORACLE_RESULTS[name]["attempts"]),
            "service_errors": int(
                G9_ORACLE_RESULTS[name].get("service_errors", 0)
            ),
        }
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else None
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else None
    )
    hint_delta = (
        hinted_rate - placebo_rate
        if hinted_rate is not None and placebo_rate is not None else None
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hint_delta,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
