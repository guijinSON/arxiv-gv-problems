"""Verified generator for shortest dominating-set TAR reconfiguration paths.

The native definition is from Section 1 of arXiv:2006.16726.  A witness is a
word of typed token additions/removals taking one dominating set to another
without exceeding the token threshold.  Instances are inverse-generated around
a hidden precedence order, so the witness is known before the graph is labelled.

This is deliberately Track B.  An endpoint-directed legal-pair scan recovers the
path in polynomial time, but performs far more exact domination checks than the
compact leaf-peeling route exposed by the constraint-incidence invariant.
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


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "finite simple graph",
        "dominating sets",
        "symbolic token-addition/removal word",
    ],
    "verification_operations": [
        "exact set insertion and deletion",
        "exact closed-neighborhood domination check",
        "exact endpoint and cardinality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Degree-two domination constraints induce a uniquely peelable alternating "
        "incidence order; without recognizing it, one repeatedly tests many "
        "candidate additions and removals."
    ),
    "hardness_basis": (
        "Track B: the endpoint-directed legal-pair scan is polynomial, with "
        "complexity O(n^3(|V|+|E|)); at provisional shipping n=44 the local "
        "audit averaged 2.49 seconds, 3,728,299 exact membership tests, "
        "and 14,556 candidate pairs over eight seeds, whereas the incidence "
        "leaf-peeling route uses at most 197 "
        "link/move operations."
    ),
    "max_answer_tokens": 155,
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

DIFFICULTY = {
    "demo": {"n": 3, "decoys": 2, "extra_precedence": 0, "noise_edges": 1},
    "easy": {"n": 32, "decoys": 48, "extra_precedence": 16, "noise_edges": 36},
    "medium": {"n": 44, "decoys": 66, "extra_precedence": 22, "noise_edges": 66},
    "hard": {"n": 60, "decoys": 90, "extra_precedence": 30, "noise_edges": 100},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "The degree-two constraints between source-only and target-only vertices carry "
    "a uniquely peelable alternating-path invariant."
)
PLACEBO_HINT = (
    "The typed move convention and endpoint labels reward consistently careful "
    "bookkeeping throughout the sequence."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly 2n tokens A<vertex> and R<vertex>, alternating add "
        "then remove, that adds every target-only vertex once and removes every "
        "source-only vertex once; the two endpoint-difference orders are otherwise "
        "independent."
    ),
    "bounds": {
        "length": "2n",
        "A_tokens": "a permutation of target minus source",
        "R_tokens": "a permutation of source minus target",
        "candidate_count": "(n!)^2",
    },
}

# Filled from script-owned harness runs.  The current counts are intentionally
# incomplete because OpenRouter exhausted its key limit during the bare loop;
# only the size/effort caps in G9 are gates.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 1},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run_oracle_budget_exhausted_during_bare_loop",
}

NOTES = (
    "Section 1 fixes the definition: every state is a dominating set of size at "
    "most k and consecutive states have symmetric difference one.  The same "
    "section records PSPACE-completeness in general, linear-time algorithms on "
    "trees, interval graphs, and cographs, and an FPT algorithm for K_{d,d}-free "
    "graphs parameterized by k.  Theorem 2 and the minor/treewidth results in "
    "Sections 4 and 5 also give polynomial constructive paths at their generous "
    "thresholds, so this is "
    "not a Track A family.  The generator samples a precedence order first, makes "
    "its pair and precedence constraints into ordinary graph vertices, records "
    "the legal TAR path, and only then randomly labels the graph.  Core and decoy "
    "pairs use the same local gadget; redundant forward constraints and noise "
    "edges remove label and degree signatures.  Static degree, smallest-label, "
    "one-shot private-neighbor, and 256-restart attacks are audited separately."
)


def _add_edge(edges, u, v):
    if u == v:
        raise ValueError("loops are not allowed")
    edges.add((u, v) if u < v else (v, u))


def make_instance(n, seed=0, **params):
    """Inverse-generate a native TAR instance and its exact shortest path.

    The hidden order and witness are sampled before vertex labels.  No path
    search, domination solver, or graph algorithm is used to obtain the answer.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    decoys = params.pop("decoys", max(2, n))
    extra = params.pop("extra_precedence", n // 2)
    noise_edges = params.pop("noise_edges", decoys)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    for name, value in (
        ("decoys", decoys),
        ("extra_precedence", extra),
        ("noise_edges", noise_edges),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a nonnegative integer")
    if decoys < 1:
        raise ValueError("decoys must be at least 1")

    eligible_extra = (n - 1) * (n - 2) // 2
    if extra > eligible_extra:
        raise ValueError("too many extra precedence constraints")
    eligible_noise = decoys * (decoys - 1) // 2
    if noise_edges > eligible_noise:
        raise ValueError("too many decoy noise edges")

    rng = random.Random(seed)

    # Abstract vertex identifiers are consecutive integers.  They are randomly
    # relabelled only after the planted path and every constraint are complete.
    next_vertex = 0

    def fresh():
        nonlocal next_vertex
        value = next_vertex
        next_vertex += 1
        return value

    hub, hub_leaf = fresh(), fresh()
    total_pairs = n + decoys
    a_vertices = [fresh() for _ in range(total_pairs)]
    b_vertices = [fresh() for _ in range(total_pairs)]
    pair_constraints = [fresh() for _ in range(total_pairs)]
    edges = set()
    _add_edge(edges, hub, hub_leaf)
    for a, b, constraint in zip(a_vertices, b_vertices, pair_constraints):
        _add_edge(edges, hub, a)
        _add_edge(edges, hub, b)
        _add_edge(edges, constraint, a)
        _add_edge(edges, constraint, b)

    order = list(range(n))
    rng.shuffle(order)

    # A constraint adjacent to b_i and a_j forbids switching j before i.  The
    # consecutive constraints force one total order; sampled forward chords are
    # logically redundant but erase the pristine-path signature.
    precedence_pairs = [(order[i], order[i + 1]) for i in range(n - 1)]
    extra_positions = [
        (i, j) for i in range(n) for j in range(i + 2, n)
    ]
    for i, j in rng.sample(extra_positions, extra):
        precedence_pairs.append((order[i], order[j]))
    for before, after in precedence_pairs:
        constraint = fresh()
        _add_edge(edges, constraint, b_vertices[before])
        _add_edge(edges, constraint, a_vertices[after])

    # All decoy pairs have the same local A--constraint--B form.  Random edges
    # among their unselected B endpoints create genuine non-isomorphic instances
    # without changing either endpoint or the planted shortest path.
    decoy_b = b_vertices[n:]
    possible_noise = [
        (decoy_b[i], decoy_b[j])
        for i in range(decoys)
        for j in range(i + 1, decoys)
    ]
    for u, v in rng.sample(possible_noise, noise_edges):
        _add_edge(edges, u, v)

    source_abstract = {hub, *a_vertices}
    target_abstract = {
        hub,
        *[b_vertices[i] for i in range(n)],
        *a_vertices[n:],
    }
    answer_abstract = []
    for index in order:
        answer_abstract.extend((
            ("A", b_vertices[index]),
            ("R", a_vertices[index]),
        ))

    # Use 1-based public labels in a word over the typed TAR-operation alphabet.
    public_labels = list(range(1, next_vertex + 1))
    rng.shuffle(public_labels)
    label = {abstract: public_labels[abstract] for abstract in range(next_vertex)}
    public_edges = sorted((min(label[u], label[v]), max(label[u], label[v])) for u, v in edges)
    rng.shuffle(public_edges)
    source = sorted(label[v] for v in source_abstract)
    target = sorted(label[v] for v in target_abstract)
    answer = [operation + str(label[vertex]) for operation, vertex in answer_abstract]

    return {
        "family": "shortest dominating-set TAR reconfiguration",
        "vertex_count": next_vertex,
        "edges": [list(edge) for edge in public_edges],
        "source": source,
        "target": target,
        "limit": len(source) + 1,
        "required_moves": 2 * n,
        "core_swaps": n,
        "decoy_pairs": decoys,
        "extra_precedence": extra,
        "noise_edges": noise_edges,
        "answer": answer,
    }


def _adjacency(inst):
    count = inst["vertex_count"]
    adj = [set((v,)) for v in range(1, count + 1)]
    for edge in inst["edges"]:
        if (
            not isinstance(edge, list)
            or len(edge) != 2
            or any(isinstance(v, bool) or not isinstance(v, int) for v in edge)
        ):
            raise ValueError("malformed edge")
        u, v = edge
        if not (1 <= u <= count and 1 <= v <= count) or u == v:
            raise ValueError("malformed edge endpoint")
        adj[u - 1].add(v)
        adj[v - 1].add(u)
    return adj


def _first_undominated(adj, state):
    for vertex, closed_neighborhood in enumerate(adj, 1):
        if state.isdisjoint(closed_neighborhood):
            return vertex
    return None


def render(inst):
    edge_lines = "\n".join(f"  {u} {v}" for u, v in inst["edges"])
    source_line = " ".join(map(str, inst["source"]))
    target_line = " ".join(map(str, inst["target"]))
    statement = f"""Find an exact shortest token-addition/removal reconfiguration between dominating sets.

The input is a finite simple undirected graph with vertices 1 through {inst['vertex_count']}.
A set D of vertices is dominating when every graph vertex either belongs to D or
has a neighbor in D.  A legal TAR move adds one absent vertex or removes one
present vertex.  After every individual move, including removals, the current
set must be dominating and contain at most k={inst['limit']} vertices.

Start at this dominating set (order is irrelevant, no repetitions):
  {source_line}

Finish at this dominating set (order is irrelevant, no repetitions):
  {target_line}

The graph has {len(inst['edges'])} edges, listed once each as two endpoints:
{edge_lines}

Give exactly {inst['required_moves']} moves.  This is the symmetric-difference lower
bound, so it is a shortest sequence: every target-only vertex must be added once,
every source-only vertex must be removed once, and no other vertex may be moved.
Encode adding vertex v by the JSON string "Av" and removing it by "Rv", with the
decimal 1-based label substituted for v: for example, "A12" adds vertex 12 and
"R7" removes vertex 7.  The JSON list must alternate an addition and a removal,
beginning with an addition; the order of moves matters.

Give your final answer inside <answer></answer> tags, as one JSON list of operation strings.
Format-only example (deliberately too short to be legal): <answer>["A1","R2"]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse the last tagged JSON list, tolerating prose and markdown fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    if any(not isinstance(x, str) for x in value):
        return None
    return value


def _verify_compiled(inst, answer, adj, source_prechecked=False):
    """Replay against a precompiled adjacency list (used by sampled audits)."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "move sequence is empty"
    required = inst["required_moves"]
    if len(answer) != required:
        return False, f"expected {required} moves, got {len(answer)}"
    count = inst["vertex_count"]
    state = set(inst["source"])
    if len(state) > inst["limit"]:
        return False, "source exceeds the token limit"
    if not source_prechecked:
        bad = _first_undominated(adj, state)
        if bad is not None:
            return False, f"source does not dominate vertex {bad}"
    for step_number, move in enumerate(answer, 1):
        if not isinstance(move, str):
            return False, f"step {step_number} is not an operation string"
        match = re.fullmatch(r"([AR])([1-9][0-9]*)", move)
        if match is None:
            return False, f"step {step_number} is not A<vertex> or R<vertex>"
        operation, digits = match.groups()
        vertex = int(digits)
        if vertex > count:
            return False, f"step {step_number} vertex {vertex} is out of range"
        if operation == "A":
            if vertex in state:
                return False, f"step {step_number} adds vertex {vertex} already present"
            state.add(vertex)
        else:
            if vertex not in state:
                return False, f"step {step_number} removes absent vertex {vertex}"
            state.remove(vertex)
        if len(state) > inst["limit"]:
            return False, f"step {step_number} exceeds the token limit"
        # Adding a vertex cannot destroy domination.  Removal is the only move
        # that needs a fresh exact neighborhood scan.
        if operation == "R":
            bad = _first_undominated(adj, state)
            if bad is not None:
                return False, f"step {step_number} does not dominate vertex {bad}"
    if state != set(inst["target"]):
        return False, "final state does not equal the target"
    return True, "ok"


def verify(inst, answer):
    """Replay any candidate TAR witness exactly; never consult inst['answer']."""
    try:
        adj = _adjacency(inst)
    except (KeyError, TypeError, ValueError) as exc:
        return False, f"malformed instance: {exc}"
    return _verify_compiled(inst, answer, adj)


def random_candidate(inst, rng):
    """Sample the exact endpoint/length/capacity-aware certificate language."""
    additions = list(set(inst["target"]) - set(inst["source"]))
    removals = list(set(inst["source"]) - set(inst["target"]))
    rng.shuffle(additions)
    rng.shuffle(removals)
    candidate = []
    for add, remove in zip(additions, removals):
        candidate.extend((f"A{add}", f"R{remove}"))
    return candidate


def search_space(inst):
    n = len(set(inst["target"]) - set(inst["source"]))
    return math.factorial(n) ** 2


def enumerate_all(inst):
    additions = sorted(set(inst["target"]) - set(inst["source"]))
    removals = sorted(set(inst["source"]) - set(inst["target"]))
    total = math.factorial(len(additions)) ** 2
    if total > 100_000:
        return None
    count = 0
    for add_order in itertools.permutations(additions):
        for remove_order in itertools.permutations(removals):
            candidate = []
            for add, remove in zip(add_order, remove_order):
                candidate.extend((f"A{add}", f"R{remove}"))
            count += int(verify(inst, candidate)[0])
    return count


def _wl_payload(inst):
    """Relabelling-invariant color refinement payload for the colored graph."""
    adj = _adjacency(inst)
    source, target = set(inst["source"]), set(inst["target"])
    initial = [(int(v in source), int(v in target)) for v in range(1, len(adj) + 1)]
    palette = {signature: i for i, signature in enumerate(sorted(set(initial)))}
    colors = [palette[signature] for signature in initial]
    for _ in range(len(adj) + 1):
        signatures = [
            (colors[v - 1], tuple(sorted(colors[u - 1] for u in adj[v - 1] if u != v)))
            for v in range(1, len(adj) + 1)
        ]
        palette = {signature: i for i, signature in enumerate(sorted(set(signatures)))}
        refined = [palette[signature] for signature in signatures]
        if refined == colors:
            break
        colors = refined
    color_counts = {}
    for color in colors:
        color_counts[color] = color_counts.get(color, 0) + 1
    edge_colors = {}
    for u, v in inst["edges"]:
        pair = tuple(sorted((colors[u - 1], colors[v - 1])))
        edge_colors[pair] = edge_colors.get(pair, 0) + 1
    return {
        "vertices": inst["vertex_count"],
        "limit": inst["limit"],
        "moves": inst["required_moves"],
        "color_counts": sorted(color_counts.items()),
        "edge_colors": sorted((list(pair), count) for pair, count in edge_colors.items()),
    }


def canonical_key(inst):
    """A strong cheap colored-graph invariant, independent of labels and order."""
    encoded = json.dumps(_wl_payload(inst), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def escalate(params):
    """Grow constraint/decoy haystacks before lengthening the move sequence."""
    out = dict(params)
    n = int(out.get("n", 2))
    decoys = int(out.get("decoys", n))
    extra = int(out.get("extra_precedence", n // 2))
    noise = int(out.get("noise_edges", decoys))
    if decoys < 4 * n:
        out["decoys"] = min(4 * n, max(decoys + 1, 2 * decoys))
        max_noise = out["decoys"] * (out["decoys"] - 1) // 2
        out["noise_edges"] = min(max_noise, max(noise, out["decoys"]))
        return out
    operation_room = 300 - (4 * n - 1)
    max_extra = min((n - 1) * (n - 2) // 2, max(0, operation_room))
    if extra < max_extra:
        out["extra_precedence"] = min(max_extra, extra + max(1, n // 4))
        out["noise_edges"] = min(
            out["decoys"] * (out["decoys"] - 1) // 2,
            noise + max(1, n // 2),
        )
        return out
    next_n = n + max(4, n // 5)
    if 2 * next_n > 256 or 4 * next_n - 1 > 300:
        return "cap_bound"
    out["n"] = next_n
    out["decoys"] = max(decoys, 2 * next_n)
    out["extra_precedence"] = min(extra, max(0, 300 - (4 * next_n - 1)))
    out["noise_edges"] = min(
        out["decoys"] * (out["decoys"] - 1) // 2,
        max(noise, out["decoys"]),
    )
    return out


def _relation_graph(inst):
    """Public degree-two incidence graph on endpoint-difference vertices."""
    adj = _adjacency(inst)
    source_only = set(inst["source"]) - set(inst["target"])
    target_only = set(inst["target"]) - set(inst["source"])
    relation = {a: set() for a in source_only}
    relation.update({b: set() for b in target_only})
    links = 0
    endpoints = source_only | target_only
    for q in range(1, len(adj) + 1):
        if q in endpoints:
            continue
        neighbors = set(adj[q - 1]) - {q}
        if len(neighbors) != 2:
            continue
        left = neighbors & source_only
        right = neighbors & target_only
        if len(left) == 1 and len(right) == 1:
            a, b = next(iter(left)), next(iter(right))
            relation[a].add(b)
            relation[b].add(a)
            links += 1
    return relation, source_only, target_only, links


def _compact_leaf_peeling(inst):
    """Recover the planted path from the public alternating incidence invariant."""
    relation, remaining_a, remaining_b, links = _relation_graph(inst)
    remaining_a, remaining_b = set(remaining_a), set(remaining_b)
    answer = []
    while remaining_a:
        leaves = [a for a in remaining_a if len(relation[a] & remaining_b) == 1]
        if len(leaves) != 1:
            return None, links + len(answer)
        a = leaves[0]
        b = next(iter(relation[a] & remaining_b))
        answer.extend((f"A{b}", f"R{a}"))
        remaining_a.remove(a)
        remaining_b.remove(b)
    if remaining_b:
        return None, links + len(answer)
    return answer, links + len(answer)


def _dominating_counted(adj, state):
    operations = 0
    for closed_neighborhood in adj:
        dominated = False
        for vertex in closed_neighborhood:
            operations += 1
            if vertex in state:
                dominated = True
                break
        if not dominated:
            return False, operations
    return True, operations


def _reference_legal_pair_scan(inst):
    """Polynomial endpoint-directed scan, intentionally structure-agnostic."""
    adj = _adjacency(inst)
    state = set(inst["source"])
    additions = set(inst["target"]) - state
    removals = state - set(inst["target"])
    answer = []
    operations = 0
    trials = 0
    while additions:
        found = None
        for add in sorted(additions):
            state.add(add)
            for remove in sorted(removals):
                state.remove(remove)
                legal, cost = _dominating_counted(adj, state)
                operations += cost
                trials += 1
                state.add(remove)
                if legal:
                    found = (add, remove)
                    break
            state.remove(add)
            if found is not None:
                break
        if found is None:
            return None, {"membership_tests": operations, "candidate_pairs": trials}
        add, remove = found
        state.add(add)
        state.remove(remove)
        additions.remove(add)
        removals.remove(remove)
        answer.extend((f"A{add}", f"R{remove}"))
    return answer, {"membership_tests": operations, "candidate_pairs": trials}


def _zipped_candidate(additions, removals):
    candidate = []
    for add, remove in zip(additions, removals):
        candidate.extend((f"A{add}", f"R{remove}"))
    return candidate


def _attack_candidates(inst, seed):
    adj = _adjacency(inst)
    source_only = set(inst["source"]) - set(inst["target"])
    target_only = set(inst["target"]) - set(inst["source"])

    degree_add = sorted(target_only, key=lambda v: (len(adj[v - 1]), v))
    degree_remove = sorted(source_only, key=lambda v: (len(adj[v - 1]), v))
    outlier = [_zipped_candidate(degree_add, degree_remove)]

    # Commit to the smallest target label and never backtrack over that choice;
    # choose its first legal removal when one exists.
    state = set(inst["source"])
    remaining_a, remaining_b = set(source_only), set(target_only)
    greedy_moves = []
    while remaining_b:
        add = min(remaining_b)
        state.add(add)
        chosen = None
        for remove in sorted(remaining_a):
            state.remove(remove)
            if _first_undominated(adj, state) is None:
                chosen = remove
                state.add(remove)
                break
            state.add(remove)
        if chosen is None:
            chosen = min(remaining_a)
        state.remove(chosen)
        remaining_a.remove(chosen)
        remaining_b.remove(add)
        greedy_moves.extend((f"A{add}", f"R{chosen}"))

    # One-shot private-neighbor scores see the first source token but do not
    # propagate after removal.  Target order uses only a static incidence score.
    source_state = set(inst["source"])
    private_score = {}
    for a in source_only:
        private_score[a] = sum(
            1
            for closed in adj
            if a in closed and len(closed & source_state) == 1
        )
    one_shot_a = sorted(source_only, key=lambda v: (private_score[v], v))
    relation, _, _, _ = _relation_graph(inst)
    unused_b = set(target_only)
    one_shot_b = []
    for a in one_shot_a:
        choices = sorted(relation[a] & unused_b)
        chosen = choices[0] if choices else min(unused_b)
        one_shot_b.append(chosen)
        unused_b.remove(chosen)
    one_shot = [_zipped_candidate(one_shot_b, one_shot_a)]

    rrng = random.Random(seed ^ 0x200616726)
    restarts = [random_candidate(inst, rrng) for _ in range(256)]
    return {
        "outlier_static_degree_order": outlier,
        "greedy_smallest_target_no_backtrack": [greedy_moves],
        "random_restart_256": restarts,
        "one_shot_private_neighbor_order": one_shot,
    }


def _relabel_variants(inst, seed):
    rng = random.Random(seed)
    count = inst["vertex_count"]
    shuffled = list(range(1, count + 1))
    rng.shuffle(shuffled)
    mapping = {old: shuffled[old - 1] for old in range(1, count + 1)}
    variants = []
    for mask in range(1, 8):
        out = {key: value for key, value in inst.items() if key not in ("edges", "source", "target", "answer")}
        edges = [list(edge) for edge in inst["edges"]]
        source, target = list(inst["source"]), list(inst["target"])
        carried = list(inst["answer"])
        if mask & 1:
            edges = [[mapping[u], mapping[v]] for u, v in edges]
            source = [mapping[v] for v in source]
            target = [mapping[v] for v in target]
            carried = [move[0] + str(mapping[int(move[1:])]) for move in carried]
        if mask & 2:
            rng.shuffle(edges)
            edges = [edge[::-1] if rng.randrange(2) else edge for edge in edges]
        if mask & 4:
            rng.shuffle(source)
            rng.shuffle(target)
        out["edges"] = edges
        out["source"] = source
        out["target"] = target
        out["answer"] = carried
        variants.append(out)
    return variants


def _worst_answer_size(inst):
    n = inst["core_swaps"]
    digits = len(str(inst["vertex_count"]))
    chars = 1 + 2 * n * (digits + 4)
    return chars, math.ceil(chars / 4)


def selftest():
    report = {}
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
        "generation_route": "inverse generation before random vertex labelling",
    }

    inst = make_instance(seed=19, **shipping)
    answer = inst["answer"]
    swapped = list(answer)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = list(answer)
    duplicated[2] = duplicated[0]
    out_of_range = list(answer)
    out_of_range[0] = "A" + str(inst["vertex_count"] + 1)
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": why}
    reasons = [case["reason"] for case in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and len(reasons) == len(set(reasons)),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The forced incidence order gives this sequence.\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nEach R-token is a removal."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
        "garbage_returns_none": parse_answer("no tagged witness here") is None,
    }

    guess_rng = random.Random(0x200616726)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    guess_adj = _adjacency(inst)
    for _ in range(guess_total):
        guess_hits += int(
            _verify_compiled(
                inst, random_candidate(inst, guess_rng), guess_adj, source_prechecked=True
            )[0]
        )
    guess_seconds = time.perf_counter() - guess_start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "structure_aware_space": search_space(inst),
        "space_bits": search_space(inst).bit_length(),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = [
        "outlier_static_degree_order",
        "greedy_smallest_target_no_backtrack",
        "random_restart_256",
        "one_shot_private_neighbor_order",
    ]
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_operations = 0
    reference_trials = 0
    compact_successes = 0
    compact_operations = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        trial_adj = _adjacency(trial)
        candidates = _attack_candidates(trial, seed)
        for name in attack_names:
            start = time.perf_counter()
            won = any(
                _verify_compiled(trial, candidate, trial_adj, source_prechecked=True)[0]
                for candidate in candidates[name]
            )
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(won)
        start = time.perf_counter()
        recovered, counts = _reference_legal_pair_scan(trial)
        reference_seconds += time.perf_counter() - start
        reference_operations += counts["membership_tests"]
        reference_trials += counts["candidate_pairs"]
        reference_successes += int(recovered is not None and verify(trial, recovered)[0])
        compact, operations = _compact_leaf_peeling(trial)
        compact_operations = max(compact_operations, operations)
        compact_successes += int(compact is not None and verify(trial, compact)[0])
    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "endpoint-directed exact legal-pair scan",
        "complexity": "O(n^3(|V|+|E|)) exact membership tests",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_operations // 8,
        "candidate_pairs": reference_trials // 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "alternating-incidence leaf peeling",
            "solves": f"{compact_successes}/8",
            "operations_upper_bound": compact_operations,
        },
    }

    demo_count = enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and demo_count == 1
        and all_failed
        and reference_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density": guess_fraction,
        "construction_proved_valid_sequences": 1,
        "demo_exact_solution_count": demo_count,
        "baseline_attack_wall_clock_sec": round(
            attack_seconds["random_restart_256"] / 8, 6
        ),
        "baseline_attack_restarts": 256,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled_params["decoys"] *= 2
    doubled_params["extra_precedence"] *= 2
    doubled_params["noise_edges"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    ladder_n = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    ladder_space = [
        search_space(make_instance(seed=0, **DIFFICULTY[name]))
        for name in DIFFICULTY
    ]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["core_swaps"] == 2 * inst["core_swaps"]
        and len(render(doubled)) > len(render(inst))
        and ladder_n == sorted(ladder_n)
        and len(set(ladder_n)) == len(ladder_n)
        and ladder_space == sorted(ladder_space),
        "shipping_n": inst["core_swaps"],
        "doubled_n": doubled["core_swaps"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_why,
        "space_bits_shipping": search_space(inst).bit_length(),
        "space_bits_doubled": search_space(doubled).bit_length(),
    }

    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping)
        key = canonical_key(original)
        for transformed in _relabel_variants(original, seed ^ 0x5A5A):
            invariant_count += int(key == canonical_key(transformed))
            real_transform_count += int(verify(transformed, transformed["answer"])[0])
        unrelated_keys.append(key)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == 140
        and real_transform_count == 140
        and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "real_transformations_verified": real_transform_count,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "arbitrary vertex relabelling with carried witness",
            "edge reordering and endpoint reversal",
            "source/target list reordering",
            "all nonempty compositions of those three",
        ],
        "caveat": "1-WL is a strong invariant, not a complete graph canoniser",
    }

    encoded_answer = json.dumps(answer, separators=(",", ":"))
    answer_chars = len(encoded_answer)
    worst_chars, worst_tokens = _worst_answer_size(inst)
    compact, intended_operations = _compact_leaf_peeling(inst)
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2_000
        and len(answer) <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == worst_tokens
        and compact is not None
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": math.ceil(answer_chars / 4),
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": worst_tokens,
        "answer_elements": len(answer),
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
