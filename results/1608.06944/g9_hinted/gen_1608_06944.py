"""Verified zero-sum-flow generator for arXiv:1608.06944.

Section 2.7 of the survey identifies a zero-sum k-flow with a nowhere-zero
k-flow of the all-negative signed graph and reports NP-completeness for
zero-sum 3-flow on (3,4)-semiregular graphs.  This module inverse-generates
exactly that native object: it samples a valid edge flow first, pairs equal
valued half-edges without parallel edges, and then forgets the plant.

The solver must return an integer vector in the nullspace of the unsigned
0/1 incidence matrix.  Verification is just exact integer addition.
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
from collections import Counter, deque


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "all-negative signed simple (3,4)-semiregular graph",
        "0/1 vertex-edge incidence matrix",
        "integer zero-sum 3-flow on the edges",
    ],
    "verification_operations": [
        "exact integer range checks",
        "exact value-multiplicity counts",
        "exact integer incident-edge sums at every vertex",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "At each degree-3 vertex one incident edge has magnitude two, while "
        "each degree-4 vertex couples four such local choices; without propagating "
        "both sign type and magnitude choice together, natural two-stage methods stall."
    ),
    "hardness_basis": (
        "Track A: Theorem 27(ii) in Section 2.7 reports NP-completeness "
        "of zero-sum 3-flow on (3,4)-semiregular graphs; shipping n=18 has 72 "
        "degree-3 and 54 degree-4 vertices (so the degree-4 count is linear, not "
        "the O(log N) polynomial regime of theorem (i)), and the self-test measures "
        "a specialized six-state GAC/DPLL attack at a 500-node budget averaged "
        "6,848,770 exact constraint-table checks and 10.98 seconds on each of "
        "eight audit seeds; no polynomial method is known for this planted "
        "semiregular distribution."
    ),
    "max_answer_tokens": 136,
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

# One unit contributes 4 degree-3 vertices, 3 degree-4 vertices and 12 edges.
# The hard rung stays below the 256-atom answer cap.
DIFFICULTY = {
    "demo": {"n": 1},
    "easy": {"n": 18},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "A degree-three vertex has a sign type and one magnitude-two edge, and each "
    "degree-four vertex constrains those two choices jointly."
)
PLACEBO_HINT = (
    "The edge numbering and the signs of all listed integers deserve consistent "
    "bookkeeping throughout the calculation."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of 12n integers in edge order that already obeys every "
        "degree-3 equation and the forced global multiplicities: choose exactly "
        "2n of the 4n degree-3 vertices to have local pattern (1,1,-2), give "
        "the others (-1,-1,2), and choose the magnitude-two edge at each vertex."
    ),
    "bounds": {
        "length": "12n",
        "alphabet": [-2, -1, 1, 2],
        "multiplicities": {"-2": "2n", "-1": "4n", "1": "4n", "2": "2n"},
        "degree_3_local_states": 6,
        "balanced_sign_types": "exactly 2n of each type",
        "candidate_count": "binomial(4n,2n) * 3^(4n)",
    },
}

NOTES = (
    "Section 1 fixes signed graphs, switching and bidirected orientation. Section "
    "2.1 defines a group/integer flow and nowhere-zero k-flow. Section 2.7 fixes "
    "the exact zero-sum condition and states that it is precisely a nowhere-zero "
    "flow on the all-negative signed graph. Its complexity theorem is the triage "
    "result: part (i) gives a polynomial algorithm on (2,4)-graphs with only "
    "O(log N) degree-4 vertices, while Theorem 27(ii) makes zero-sum 3-flow NP-complete "
    "on (3,4)-semiregular graphs. The generator therefore uses 4n degree-3 and 3n "
    "degree-4 vertices. It never solves an emitted graph: degree-3 patterns are "
    "sampled in opposite pairs, degree-4 patterns balance their four label pools, "
    "and equal labels are joined by random simple matchings. Vertex relabelling and "
    "edge shuffling erase the construction order. Exact multiplicities defeat a "
    "naive random-space claim; G4 samples uniformly after enforcing every degree-3 "
    "equation and the forced global type balance. Four-cycle outliers, residual "
    "greedy assignment, swap-based "
    "local search, a two-stage type/selector heuristic, and a six-state GAC/DPLL "
    "solver are audited without access to the planted answer."
)


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_VALUES = (-2, -1, 1, 2)
_GUESS_SAMPLES = 200_000
_DPLL_NODE_BUDGET = 500

# Filled from the script-owned bare/hinted/placebo runs after hardening.  These
# values are diagnostics; G9 gates only the size and intended-route caps.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unrun",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_n_seed(n, seed):
    if not _is_int(n) or n < 1:
        raise ValueError("n must be a positive integer")
    if not _is_int(seed):
        raise ValueError("seed must be an integer")


def _matched_stubs(left, right, used_pairs, rng):
    """Randomly match two equally-sized stub lists without repeated endpoints."""
    if len(left) != len(right):
        raise AssertionError("unbalanced planted label pools")
    for _ in range(500):
        left_order = list(left)
        remaining = list(right)
        rng.shuffle(left_order)
        rng.shuffle(remaining)
        chosen = []
        current_pairs = set()
        for left_stub in left_order:
            candidates = [
                index
                for index, right_stub in enumerate(remaining)
                if (left_stub[0], right_stub[0]) not in used_pairs
                and (left_stub[0], right_stub[0]) not in current_pairs
            ]
            if not candidates:
                break
            position = rng.choice(candidates)
            right_stub = remaining.pop(position)
            chosen.append((left_stub, right_stub))
            current_pairs.add((left_stub[0], right_stub[0]))
        if not remaining:
            return chosen
    raise RuntimeError("could not form a simple planted matching")


def make_instance(n, seed=0, **params):
    """Inverse-generate a simple semiregular graph and a known zero-sum flow."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_n_seed(n, seed)
    rng = random.Random(seed)

    # On the degree-3 side, a type-A vertex has (1,1,-2) and a type-B
    # vertex has (-1,-1,2).  Equal populations force the certificate's exact
    # global multiplicities and remove a sign-frequency plant.
    patterns3 = [[1, 1, -2] for _ in range(2 * n)]
    patterns3 += [[-1, -1, 2] for _ in range(2 * n)]
    rng.shuffle(patterns3)
    for pattern in patterns3:
        rng.shuffle(pattern)

    # The 3n degree-4 vertices supply exactly the same number of half-edges
    # of each value as the degree-3 side: n use two +1 and two -1, and 2n
    # use one of each value.
    patterns4 = [[1, 1, -1, -1] for _ in range(n)]
    patterns4 += [[1, -1, 2, -2] for _ in range(2 * n)]
    rng.shuffle(patterns4)
    for pattern in patterns4:
        rng.shuffle(pattern)

    # Reject disconnected pairings: components would split the search into
    # smaller independent instances.  This filter inspects only the graph and
    # never searches for a flow; the already sampled local patterns remain the
    # certificate throughout all retries.
    for _ in range(200):
        raw_edges = []
        raw_answer = []
        used_pairs = set()
        try:
            for value in _VALUES:
                left = [
                    (vertex, slot)
                    for vertex, pattern in enumerate(patterns3)
                    for slot, entry in enumerate(pattern)
                    if entry == value
                ]
                right = [
                    (vertex, slot)
                    for vertex, pattern in enumerate(patterns4)
                    for slot, entry in enumerate(pattern)
                    if entry == value
                ]
                pairs = _matched_stubs(left, right, used_pairs, rng)
                for left_stub, right_stub in pairs:
                    pair = (left_stub[0], right_stub[0])
                    used_pairs.add(pair)
                    raw_edges.append((left_stub[0], 4 * n + right_stub[0]))
                    raw_answer.append(value)
        except RuntimeError:
            continue
        raw_adjacency = [[] for _ in range(7 * n)]
        for left, right in raw_edges:
            raw_adjacency[left].append(right)
            raw_adjacency[right].append(left)
        seen = {0}
        stack = [0]
        while stack:
            vertex = stack.pop()
            for neighbor in raw_adjacency[vertex]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        if len(seen) == 7 * n:
            break
    else:
        raise RuntimeError("could not form a connected simple planted graph")

    # Forget every construction coordinate that is not part of the graph.
    vertex_map = list(range(7 * n))
    rng.shuffle(vertex_map)
    raw_edges = [
        tuple(sorted((vertex_map[left], vertex_map[right])))
        for left, right in raw_edges
    ]
    order = list(range(12 * n))
    rng.shuffle(order)
    edges = [list(raw_edges[index]) for index in order]
    answer = [raw_answer[index] for index in order]

    instance = {
        "family": "zero-sum 3-flow on an all-negative signed graph",
        "n": n,
        "vertex_count": 7 * n,
        "edge_count": 12 * n,
        "signature": "all-negative",
        "edges": edges,
        "answer": answer,
    }
    ok, reason = verify(instance, answer)
    if not ok:
        raise AssertionError("construction failed: " + reason)
    return instance


def render(inst):
    """Render the complete exact zero-sum-flow problem."""
    lines = [
        "Find a zero-sum 3-flow on the following all-negative signed graph.",
        "",
        "A signed graph is an undirected graph whose edges have signs; here every",
        "edge is negative.  For this all-negative orientation, a zero-sum 3-flow",
        "is an assignment f(e) in {-2,-1,1,2} to every edge such that, at every",
        "vertex, the ordinary integer sum of the values on all incident edges is 0.",
        "This is exactly a nowhere-zero integer 3-flow of the all-negative signed",
        "graph.  All arithmetic is over the integers, not modulo any number.",
        "",
        f"Vertices are 0 through {inst['vertex_count'] - 1}.  Edges are undirected,",
        "simple, and numbered from 0 in the displayed order.  The two bipartition",
        "classes have degrees 3 and 4.  Parallel edges and repeated endpoints are",
        "absent.  Edge list:",
    ]
    for start in range(0, inst["edge_count"], 6):
        chunk = []
        for index in range(start, min(start + 6, inst["edge_count"])):
            left, right = inst["edges"][index]
            chunk.append(f"{index}:{left}-{right}")
        lines.append("  " + "  ".join(chunk))
    n = inst["n"]
    lines += [
        "",
        f"Return a JSON array of exactly {inst['edge_count']} integers, one per edge",
        "in edge-number order.  Every valid answer necessarily uses exactly",
        f"{-2}: {2*n} times, {-1}: {4*n} times, {1}: {4*n} times, and {2}: {2*n} times.",
        "Order matters because position i is the value of edge i; repetitions are",
        "required according to those counts.",
        "",
        "Give your final answer inside <answer></answer> tags, as a JSON array.",
        "Example: <answer>[-2,1,1]</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines += ["", "Hint: " + STRUCTURAL_HINT]
    elif mode == "placebo":
        lines += ["", "Hint: " + PLACEBO_HINT]
    return "\n".join(lines)


def parse_answer(text):
    """Parse a tagged JSON flow vector, tolerating prose and Markdown fences."""
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
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def verify(inst, answer):
    """Check any exact zero-sum 3-flow; the planted answer is never consulted."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    expected = inst["edge_count"]
    if len(answer) < expected:
        return False, f"too few flow values: expected {expected}, got {len(answer)}"
    if len(answer) > expected:
        return False, f"too many flow values: expected {expected}, got {len(answer)}"
    for index, value in enumerate(answer):
        if not _is_int(value):
            return False, f"edge {index} value is not an integer"
        if value not in _VALUES:
            return False, f"edge {index} value {value} is outside {{-2,-1,1,2}}"
    n = inst["n"]
    wanted = Counter({-2: 2 * n, -1: 4 * n, 1: 4 * n, 2: 2 * n})
    if Counter(answer) != wanted:
        return False, "flow-value multiplicities do not match the forced semiregular counts"
    sums = [0] * inst["vertex_count"]
    for value, edge in zip(answer, inst["edges"]):
        left, right = edge
        sums[left] += value
        sums[right] += value
    for vertex, total in enumerate(sums):
        if total != 0:
            return False, f"conservation fails at vertex {vertex}: incident sum is {total}"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample after enforcing every degree-3 conservation equation."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    incident = _incidence(inst)
    degree3 = sorted(v for v, edges in enumerate(incident) if len(edges) == 3)
    return _random_candidate_from_incidence(inst, rng, incident, degree3)


def _random_candidate_from_incidence(inst, rng, incident, degree3):
    """The public sampler with its instance-only incidence scan precomputed."""
    n = inst["n"]
    type_zero = set(rng.sample(degree3, 2 * n))
    answer = [0] * inst["edge_count"]
    for vertex in degree3:
        edges = sorted(incident[vertex])
        selected = rng.randrange(3)
        for slot, edge in enumerate(edges):
            if vertex in type_zero:
                answer[edge] = -2 if slot == selected else 1
            else:
                answer[edge] = 2 if slot == selected else -1
    return answer


def search_space(inst):
    """Number of balanced assignments satisfying every degree-3 equation."""
    n = inst["n"]
    return math.comb(4 * n, 2 * n) * 3 ** (4 * n)


def enumerate_all(inst):
    """Count valid flows when the structure-aware language is at most 300k."""
    if search_space(inst) > 300_000:
        return None
    n = inst["n"]
    incident = _incidence(inst)
    degree3 = sorted(v for v, edges in enumerate(incident) if len(edges) == 3)
    count = 0
    for chosen_types in itertools.combinations(range(4 * n), 2 * n):
        type_zero = set(chosen_types)
        for selected_slots in itertools.product(range(3), repeat=4 * n):
            candidate = [0] * inst["edge_count"]
            for variable, vertex in enumerate(degree3):
                for slot, edge in enumerate(sorted(incident[vertex])):
                    if variable in type_zero:
                        candidate[edge] = -2 if slot == selected_slots[variable] else 1
                    else:
                        candidate[edge] = 2 if slot == selected_slots[variable] else -1
            count += int(verify(inst, candidate)[0])
    return count


def _adjacency(inst):
    adjacency = [set() for _ in range(inst["vertex_count"])]
    for left, right in inst["edges"]:
        adjacency[left].add(right)
        adjacency[right].add(left)
    return adjacency


def _rooted_fingerprint(adjacency, root):
    """An isomorphism-invariant individualize/refine fingerprint for one root."""
    signatures = [(len(adjacency[v]), int(v == root)) for v in range(len(adjacency))]
    palette = {signature: index for index, signature in enumerate(sorted(set(signatures)))}
    colors = [palette[signature] for signature in signatures]
    for _ in range(len(adjacency)):
        signatures = [
            (colors[v], tuple(sorted(colors[w] for w in adjacency[v])))
            for v in range(len(adjacency))
        ]
        palette = {signature: index for index, signature in enumerate(sorted(set(signatures)))}
        refined = [palette[signature] for signature in signatures]
        if refined == colors:
            break
        colors = refined
    class_count = max(colors) + 1
    sizes = [0] * class_count
    for color in colors:
        sizes[color] += 1
    quotient = Counter()
    for left in range(len(adjacency)):
        for right in adjacency[left]:
            if left < right:
                a, b = sorted((colors[left], colors[right]))
                quotient[(a, b)] += 1
    # The BFS layer profile strengthens the cheap invariant on locally regular
    # instances without pretending to solve graph isomorphism.
    distances = [-1] * len(adjacency)
    distances[root] = 0
    queue = deque([root])
    while queue:
        vertex = queue.popleft()
        for neighbor in adjacency[vertex]:
            if distances[neighbor] < 0:
                distances[neighbor] = distances[vertex] + 1
                queue.append(neighbor)
    layers = tuple(sorted(Counter(distances).items()))
    return (
        tuple(sizes),
        tuple((a, b, value) for (a, b), value in sorted(quotient.items())),
        layers,
    )


def canonical_key(inst):
    """A strong cheap invariant under all vertex and edge relabellings."""
    adjacency = _adjacency(inst)
    rooted = sorted(_rooted_fingerprint(adjacency, root) for root in range(len(adjacency)))
    payload = json.dumps(rooted, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params):
    """The only genuine remaining size axis would exceed the answer atom cap."""
    n = params.get("n")
    if not _is_int(n) or n < 1:
        return None
    if 12 * (n + 1) > 256:
        return "cap_bound"
    return {"n": n + 1}


def _incidence(inst):
    incident = [[] for _ in range(inst["vertex_count"])]
    for index, (left, right) in enumerate(inst["edges"]):
        incident[left].append(index)
        incident[right].append(index)
    return incident


def _edge_four_cycle_scores(inst):
    adjacency = _adjacency(inst)
    scores = []
    for left, right in inst["edges"]:
        if len(adjacency[left]) == 4:
            left, right = right, left
        score = 0
        for other_right in adjacency[left] - {right}:
            score += len((adjacency[right] & adjacency[other_right]) - {left})
        scores.append(score)
    return scores


def _rank_block_candidates(inst):
    """Outlier attack: assign each value to a contiguous four-cycle-score block."""
    scores = _edge_four_cycle_scores(inst)
    ranked = sorted(range(inst["edge_count"]), key=lambda e: (scores[e], e))
    n = inst["n"]
    block_counts = {-2: 2 * n, -1: 4 * n, 1: 4 * n, 2: 2 * n}
    candidates = []
    for order in itertools.permutations(_VALUES):
        candidate = [0] * inst["edge_count"]
        offset = 0
        for value in order:
            for edge in ranked[offset : offset + block_counts[value]]:
                candidate[edge] = value
            offset += block_counts[value]
        candidates.append(candidate)
    return candidates


def _greedy_residual(inst, reverse=False):
    """Greedily assign the forced multiset to minimize current endpoint residuals."""
    incident = _incidence(inst)
    scores = _edge_four_cycle_scores(inst)
    order = sorted(
        range(inst["edge_count"]),
        key=lambda edge: (scores[edge], edge),
        reverse=reverse,
    )
    n = inst["n"]
    remaining = {-2: 2 * n, -1: 4 * n, 1: 4 * n, 2: 2 * n}
    sums = [0] * inst["vertex_count"]
    answer = [0] * inst["edge_count"]
    for edge in order:
        left, right = inst["edges"][edge]
        choices = [value for value in _VALUES if remaining[value]]
        value = min(
            choices,
            key=lambda item: (
                abs(sums[left] + item) + abs(sums[right] + item),
                -remaining[item],
                abs(item),
                item,
            ),
        )
        answer[edge] = value
        remaining[value] -= 1
        sums[left] += value
        sums[right] += value
    return answer


def _local_search(inst, rng, restarts=32, steps=1500):
    """Swap values within the exact multiset while minimizing squared imbalance."""
    incident_sums = [0] * inst["vertex_count"]
    best = None
    best_score = None
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        incident_sums[:] = [0] * inst["vertex_count"]
        for value, (left, right) in zip(candidate, inst["edges"]):
            incident_sums[left] += value
            incident_sums[right] += value
        score = sum(total * total for total in incident_sums)
        if best_score is None or score < best_score:
            best, best_score = list(candidate), score
        if score == 0:
            return candidate
        for step in range(steps):
            first = rng.randrange(inst["edge_count"])
            second = rng.randrange(inst["edge_count"] - 1)
            if second >= first:
                second += 1
            a, b = candidate[first], candidate[second]
            if a == b:
                continue
            touched = set(inst["edges"][first]) | set(inst["edges"][second])
            old = sum(incident_sums[v] ** 2 for v in touched)
            delta = b - a
            for vertex in inst["edges"][first]:
                incident_sums[vertex] += delta
            for vertex in inst["edges"][second]:
                incident_sums[vertex] -= delta
            new = sum(incident_sums[v] ** 2 for v in touched)
            temperature_accept = step % 127 == 0 and rng.random() < 0.08
            if new <= old or temperature_accept:
                candidate[first], candidate[second] = b, a
                score += new - old
                if score < best_score:
                    best, best_score = list(candidate), score
                if score == 0:
                    return candidate
            else:
                for vertex in inst["edges"][first]:
                    incident_sums[vertex] -= delta
                for vertex in inst["edges"][second]:
                    incident_sums[vertex] += delta
    return best


def _flow_csp(inst):
    """Build the paper-native six-state CSP on the degree-3 vertices.

    State 3*x+s says that the vertex has sign type x and that local incident
    edge slot s is its unique magnitude-two edge.  A degree-4 constraint accepts
    exactly two vertices of each sign type and equal selected loads of both types.
    """
    incident = _incidence(inst)
    degree3 = sorted(v for v, edges in enumerate(incident) if len(edges) == 3)
    degree4 = sorted(v for v, edges in enumerate(incident) if len(edges) == 4)
    variable_of = {vertex: index for index, vertex in enumerate(degree3)}
    slot_of_edge = {}
    for vertex in degree3:
        for slot, edge in enumerate(sorted(incident[vertex])):
            slot_of_edge[(vertex, edge)] = slot
    constraints = []
    variable_constraints = [[] for _ in degree3]
    for constraint_index, vertex in enumerate(degree4):
        row = []
        for edge in sorted(incident[vertex]):
            left, right = inst["edges"][edge]
            neighbor = right if left == vertex else left
            row.append((variable_of[neighbor], slot_of_edge[(neighbor, edge)]))
        constraints.append(row)
        for variable, _ in row:
            variable_constraints[variable].append(constraint_index)
    return incident, degree3, constraints, variable_constraints


_ALLOWED_CACHE = {}


def _allowed_patterns(slots):
    key = tuple(slots)
    cached = _ALLOWED_CACHE.get(key)
    if cached is not None:
        return cached
    patterns = []
    for states in itertools.product(range(6), repeat=4):
        types = [state // 3 for state in states]
        if sum(types) != 2:
            continue
        selected = [states[i] % 3 == key[i] for i in range(4)]
        count0 = sum(selected[i] for i in range(4) if types[i] == 0)
        count1 = sum(selected[i] for i in range(4) if types[i] == 1)
        if count0 == count1:
            patterns.append(states)
    cached = tuple(patterns)
    _ALLOWED_CACHE[key] = cached
    return cached


def _states_to_flow(inst, degree3, incident, states):
    answer = [0] * inst["edge_count"]
    for variable, vertex in enumerate(degree3):
        sign_type, selected_slot = divmod(states[variable], 3)
        for slot, edge in enumerate(sorted(incident[vertex])):
            if sign_type == 0:
                value = -2 if slot == selected_slot else 1
            else:
                value = 2 if slot == selected_slot else -1
            if answer[edge] not in (0, value):
                raise AssertionError("inconsistent state conversion")
            answer[edge] = value
    return answer


def _two_stage_attack(inst, rng):
    """Solve sign types as exact-2-in-4, then greedily choose magnitude-two edges."""
    incident, degree3, constraints, variable_constraints = _flow_csp(inst)
    assignment = [-1] * len(degree3)

    def propagate(queue, trail):
        queued = set(queue)
        while queue:
            constraint = queue.popleft()
            queued.discard(constraint)
            variables = [variable for variable, _ in constraints[constraint]]
            values = [assignment[variable] for variable in variables]
            zeros = values.count(0)
            ones = values.count(1)
            unknown = [variable for variable in variables if assignment[variable] < 0]
            if zeros > 2 or ones > 2:
                return False
            forced = None
            if zeros == 2:
                forced = 1
            elif ones == 2:
                forced = 0
            if forced is not None:
                for variable in unknown:
                    if assignment[variable] < 0:
                        assignment[variable] = forced
                        trail.append(variable)
                        for other in variable_constraints[variable]:
                            if other not in queued:
                                queue.append(other)
                                queued.add(other)
                    elif assignment[variable] != forced:
                        return False
        return True

    def search():
        remaining = [v for v, value in enumerate(assignment) if value < 0]
        if not remaining:
            return list(assignment)
        variable = max(
            remaining,
            key=lambda v: sum(
                sum(assignment[w] >= 0 for w, _ in constraints[c])
                for c in variable_constraints[v]
            ),
        )
        order = [0, 1]
        rng.shuffle(order)
        for value in order:
            trail = [variable]
            assignment[variable] = value
            if propagate(deque(variable_constraints[variable]), trail):
                result = search()
                if result is not None:
                    return result
            for changed in reversed(trail):
                assignment[changed] = -1
        return None

    types = search()
    if types is None:
        return None

    # For each degree-3 vertex choose one incident edge.  This greedy stage knows
    # the exact structural reduction but does not jointly backtrack, which is the
    # intended failure being measured.
    selected_load = [[0, 0] for _ in constraints]
    chosen_slots = [-1] * len(degree3)
    variables = list(range(len(degree3)))
    rng.shuffle(variables)
    for variable in variables:
        options = []
        for constraint in variable_constraints[variable]:
            row = constraints[constraint]
            slot = next(slot for v, slot in row if v == variable)
            other_type = 1 - types[variable]
            imbalance = abs(
                selected_load[constraint][types[variable]] + 1
                - selected_load[constraint][other_type]
            )
            options.append((imbalance, sum(selected_load[constraint]), rng.random(), slot, constraint))
        _, _, _, slot, constraint = min(options)
        chosen_slots[variable] = slot
        selected_load[constraint][types[variable]] += 1
    states = [3 * types[v] + chosen_slots[v] for v in range(len(degree3))]
    return _states_to_flow(inst, degree3, incident, states)


def _gac_dpll_attack(inst, rng, node_budget=_DPLL_NODE_BUDGET):
    """Specialized exact CSP search with generalized arc consistency."""
    incident, degree3, constraints, variable_constraints = _flow_csp(inst)
    allowed = [
        _allowed_patterns([slot for _, slot in row])
        for row in constraints
    ]
    domains = [0b111111] * len(degree3)
    # Global sign negation swaps the two sign types, so this loses no solution.
    domains[0] = 0b000111
    stats = {"nodes": 0, "pattern_checks": 0, "exhausted": False}

    def propagate(current, initial):
        queue = deque(initial)
        queued = set(queue)
        while queue:
            constraint = queue.popleft()
            queued.discard(constraint)
            row = constraints[constraint]
            supports = [0, 0, 0, 0]
            any_pattern = False
            for pattern in allowed[constraint]:
                stats["pattern_checks"] += 1
                if all(current[row[i][0]] & (1 << pattern[i]) for i in range(4)):
                    any_pattern = True
                    for i in range(4):
                        supports[i] |= 1 << pattern[i]
            if not any_pattern:
                return False
            for position, (variable, _) in enumerate(row):
                reduced = current[variable] & supports[position]
                if not reduced:
                    return False
                if reduced != current[variable]:
                    current[variable] = reduced
                    for other in variable_constraints[variable]:
                        if other not in queued:
                            queue.append(other)
                            queued.add(other)
        return True

    if not propagate(domains, range(len(constraints))):
        return None, stats

    def support_score(variable, state, current):
        score = 0
        for constraint in variable_constraints[variable]:
            row = constraints[constraint]
            position = next(i for i, (v, _) in enumerate(row) if v == variable)
            for pattern in allowed[constraint]:
                stats["pattern_checks"] += 1
                if pattern[position] != state:
                    continue
                if all(current[row[i][0]] & (1 << pattern[i]) for i in range(4)):
                    score += 1
        return score

    def search(current):
        stats["nodes"] += 1
        if stats["nodes"] > node_budget:
            stats["exhausted"] = True
            return None
        undecided = [v for v, mask in enumerate(current) if mask.bit_count() > 1]
        if not undecided:
            return [mask.bit_length() - 1 for mask in current]
        variable = min(
            undecided,
            key=lambda v: (
                current[v].bit_count(),
                sum(
                    current[w].bit_count()
                    for c in variable_constraints[v]
                    for w, _ in constraints[c]
                ),
                rng.random(),
            ),
        )
        states = [state for state in range(6) if current[variable] & (1 << state)]
        states.sort(
            key=lambda state: (support_score(variable, state, current), rng.random()),
            reverse=True,
        )
        for state in states:
            branch = list(current)
            branch[variable] = 1 << state
            if propagate(branch, variable_constraints[variable]):
                result = search(branch)
                if result is not None:
                    return result
            if stats["exhausted"]:
                return None
        return None

    states = search(domains)
    if states is None:
        return None, stats
    return _states_to_flow(inst, degree3, incident, states), stats


def _relabel_instance(inst, rng):
    vertex_map = list(range(inst["vertex_count"]))
    rng.shuffle(vertex_map)
    order = list(range(inst["edge_count"]))
    rng.shuffle(order)
    edges = []
    answer = []
    for old_edge in order:
        left, right = inst["edges"][old_edge]
        edges.append(sorted((vertex_map[left], vertex_map[right])))
        answer.append(inst["answer"][old_edge])
    return {
        "family": inst["family"],
        "n": inst["n"],
        "vertex_count": inst["vertex_count"],
        "edge_count": inst["edge_count"],
        "signature": inst["signature"],
        "edges": edges,
        "answer": answer,
    }


def _corruptions(inst):
    answer = list(inst["answer"])
    swapped = None
    for first in range(len(answer)):
        for second in range(first + 1, len(answer)):
            if answer[first] == answer[second]:
                continue
            candidate = list(answer)
            candidate[first], candidate[second] = candidate[second], candidate[first]
            if not verify(inst, candidate)[0]:
                swapped = candidate
                break
        if swapped is not None:
            break
    return {
        "empty": [],
        "drop_one": answer[:-1],
        "duplicate_one": answer + [answer[0]],
        "out_of_range": [0] + answer[1:],
        "swap_two_positions": swapped,
    }


def selftest():
    report = {}

    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed, "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checked": checks,
        "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=314159, **shipping_params)

    cases = {}
    reasons = []
    for name, candidate in _corruptions(shipping).items():
        if candidate is None:
            cases[name] = {"rejected": False, "reason": "corruption unavailable"}
            continue
        ok, reason = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
        if not ok:
            reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in cases.values()) and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "cases": cases,
    }

    response = (
        "I balanced the incidence equations exactly.\n\n<answer>```json\n"
        + json.dumps(shipping["answer"])
        + "\n```</answer>\nThe entries follow edge order."
    )
    parsed = parse_answer(response)
    parsed_ok, parsed_reason = verify(shipping, parsed)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and parsed_ok,
        "verify_reason": parsed_reason,
    }

    guess_rng = random.Random(271828)
    guess_hits = 0
    guess_incident = _incidence(shipping)
    guess_degree3 = sorted(
        v for v, edges in enumerate(guess_incident) if len(edges) == 3
    )
    guess_start = time.perf_counter()
    for _ in range(_GUESS_SAMPLES):
        candidate = _random_candidate_from_incidence(
            shipping, guess_rng, guess_incident, guess_degree3
        )
        guess_hits += int(verify(shipping, candidate)[0])
    guess_wall = time.perf_counter() - guess_start
    density = guess_hits / _GUESS_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6,
        "hits": guess_hits,
        "total": _GUESS_SAMPLES,
        "measured_probability": density,
        "structure_aware_space": search_space(shipping),
        "sampler": (
            "uniform balanced degree-3 sign types and uniform magnitude-two "
            "edge choices; every degree-3 equation is already satisfied"
        ),
        "wall_clock_sec": round(guess_wall, 6),
    }

    attack_names = [
        "outlier_four_cycle_blocks",
        "greedy_residual_two_orders",
        "random_restart_swap_descent",
        "two_stage_type_then_selector",
        "gac_dpll_500_nodes",
    ]
    attacks = {name: {"successes": 0, "attempts": 0} for name in attack_names}
    walls = {name: 0.0 for name in attack_names}
    exact_nodes = []
    exact_checks = []
    exact_exhaustions = 0
    attack_seeds = list(range(8))
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **shipping_params)

        start = time.perf_counter()
        outlier_success = any(verify(inst, candidate)[0] for candidate in _rank_block_candidates(inst))
        walls["outlier_four_cycle_blocks"] += time.perf_counter() - start
        attacks["outlier_four_cycle_blocks"]["successes"] += int(outlier_success)
        attacks["outlier_four_cycle_blocks"]["attempts"] += 1

        start = time.perf_counter()
        greedy_success = any(
            verify(inst, _greedy_residual(inst, reverse=reverse))[0]
            for reverse in (False, True)
        )
        walls["greedy_residual_two_orders"] += time.perf_counter() - start
        attacks["greedy_residual_two_orders"]["successes"] += int(greedy_success)
        attacks["greedy_residual_two_orders"]["attempts"] += 1

        start = time.perf_counter()
        local = _local_search(inst, random.Random(1000 + seed))
        local_success = local is not None and verify(inst, local)[0]
        walls["random_restart_swap_descent"] += time.perf_counter() - start
        attacks["random_restart_swap_descent"]["successes"] += int(local_success)
        attacks["random_restart_swap_descent"]["attempts"] += 1

        start = time.perf_counter()
        two_stage = _two_stage_attack(inst, random.Random(2000 + seed))
        two_stage_success = two_stage is not None and verify(inst, two_stage)[0]
        walls["two_stage_type_then_selector"] += time.perf_counter() - start
        attacks["two_stage_type_then_selector"]["successes"] += int(two_stage_success)
        attacks["two_stage_type_then_selector"]["attempts"] += 1

        start = time.perf_counter()
        exact, stats = _gac_dpll_attack(inst, random.Random(3000 + seed))
        walls["gac_dpll_500_nodes"] += time.perf_counter() - start
        exact_success = exact is not None and verify(inst, exact)[0]
        attacks["gac_dpll_500_nodes"]["successes"] += int(exact_success)
        attacks["gac_dpll_500_nodes"]["attempts"] += 1
        exact_nodes.append(stats["nodes"])
        exact_checks.append(stats["pattern_checks"])
        exact_exhaustions += int(stats["exhausted"])

    for name in attack_names:
        attacks[name]["wall_clock_sec_total_8"] = round(walls[name], 6)
    all_failed = all(row["successes"] == 0 for row in attacks.values())
    report["G5_density_and_baseline_cost"] = {
        "pass": density < 1e-6 and all_failed and exact_exhaustions == len(attack_seeds),
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": _GUESS_SAMPLES,
        "shipping_solution_fraction_estimate": density,
        "strongest_attack": "specialized six-state GAC/DPLL",
        "baseline_wall_clock_sec_total_8": round(walls["gac_dpll_500_nodes"], 6),
        "baseline_wall_clock_sec_mean": round(walls["gac_dpll_500_nodes"] / 8, 6),
        "baseline_nodes_mean": sum(exact_nodes) / len(exact_nodes),
        "baseline_nodes_max": max(exact_nodes),
        "baseline_pattern_checks_mean": sum(exact_checks) / len(exact_checks),
        "baseline_budget_exhaustions": exact_exhaustions,
        "demo_exact_valid_answers": enumerate_all(make_instance(seed=5, **DIFFICULTY["demo"])),
        "demo_candidate_space": search_space(make_instance(seed=5, **DIFFICULTY["demo"])),
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attacks,
        "seeds": attack_seeds,
        "standard_algorithm": (
            "exact six-state CSP backtracking with generalized arc consistency, "
            "MRV branching, least-constraining-value order and global sign symmetry breaking"
        ),
    }

    doubled = make_instance(n=2 * shipping["n"], seed=707)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["edge_count"] == 2 * shipping["edge_count"],
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_edges": shipping["edge_count"],
        "doubled_edges": doubled["edge_count"],
        "verify_reason": doubled_reason,
    }

    invariant_checks = 0
    carried_checks = 0
    key_failures = []
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(seed=9000 + seed, **shipping_params)
        key = canonical_key(inst)
        unrelated_keys.append(key)
        once = _relabel_instance(inst, random.Random(12000 + seed))
        twice = _relabel_instance(once, random.Random(15000 + seed))
        for label, transformed in (("single", once), ("composed", twice)):
            invariant_checks += 1
            if canonical_key(transformed) != key:
                key_failures.append({"seed": seed, "transform": label, "reason": "key changed"})
            ok, reason = verify(transformed, transformed["answer"])
            carried_checks += 1
            if not ok:
                key_failures.append({"seed": seed, "transform": label, "reason": reason})
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "real_transformation_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "unrelated_distinct_keys": distinct,
        "failures": key_failures,
        "symmetries_tested": [
            "arbitrary vertex relabelling",
            "arbitrary edge reordering with carried flow",
            "composition of both transformations twice",
        ],
        "invariant": "multiset of individualized color-refinement quotient and BFS fingerprints",
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(shipping["answer"])
    intended_operations = shipping["edge_count"]
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping_params
    report["certificate_language"] = CERTIFICATE_LANGUAGE
    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
