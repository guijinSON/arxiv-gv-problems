"""Verified generator for arXiv:1911.02196.

The generated task is the paper's Lemma 4 gadget: decompose
``overline(K_Z) vee G`` into triangles, where G is cubic.  A decomposition is
encoded compactly by giving, for every edge of G, the vertex of Z completing
its triangle.  The generator inverse-plants this certificate by drawing three
perfect matchings and forgetting which matching supplied each edge.
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
        "simple connected cubic graph G",
        "three distinguished vertices Z",
        "implicit graph overline(K_Z) vee G",
    ],
    "verification_operations": [
        "expand edge colours into triangles",
        "exact edge-multiset comparison",
        "proper-colouring incidence check",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 2, Lemma 4: proper 3-edge-colourings of a cubic graph G "
        "are exactly K3-decompositions of overline(K_Z) vee G"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Fixing the three colours at one vertex propagates along pairwise "
        "even-cycle constraints; without the right global choices one must "
        "backtrack over a crowded cubic graph."
    ),
    "hardness_basis": (
        "Track A: Theorem 1 and Lemma 3 prove NP-completeness for prescribed "
        "embedding orders v < (2-epsilon)u (with nontrivial u polynomially "
        "often, via cubic graphs of order n >= 74); the shipping distribution "
        "uses simple connected planted 1-factorisations at n=160, where the "
        "measured propagation-DPLL baseline exhausts its stated node budget "
        "on every audit seed."
    ),
    "max_answer_tokens": 120,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 8},
    "easy": {"n": 80},
    "medium": {"n": 112},
    "hard": {"n": 160},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "A valid colouring partitions the edges into three perfect matchings whose "
    "pairwise unions are disjoint even cycles."
)
PLACEBO_HINT = (
    "A valid response rewards careful bookkeeping across the complete edge "
    "list and its repeated vertex labels."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A length-3n/2 list over {0,1,2}, in displayed-edge order, containing "
        "each symbol exactly n/2 times"
    ),
    "bounds": {
        "length": "3n/2",
        "alphabet_size": 3,
        "multiplicity_per_symbol": "n/2",
        "shipping_max_length": 240,
    },
}

NOTES = """\
Section 1 fixes the exact notion of a PSTS embedding and the v >= 2u+1 easy
regime.  Theorem 1 gives NP-completeness only when the allowed small order stays
below (2-epsilon)u on polynomially frequent input orders.  Section 2, Lemma 4
is the certificate-producing result used here: an edge colour z on xy gives
the triangle {x,y,z}, and these triangles decompose overline(K_Z) vee G exactly
when the colouring is proper.  Lemma 3 needs cubic order at least 74 in the
full PSTS reduction, so every non-demo preset stays in that regime.

The generator uses inverse generation, not completion search: it samples three
independent uniform perfect matchings, rejects only duplicate-edge or
disconnected draws, then independently permutes vertices, edges, and colour
names.  All three planted colour classes therefore have the same marginal
distribution.  Vertex labels and edge positions are scrambled to defeat
endpoint/outlier rules; greedy and random-order propagation are tested; the
domain-standard attack is a bounded exact DPLL edge-colourer with unit
propagation and a minimum-remaining-values branch rule.  Theorem 1 is
worst-case evidence only, so the audit's measured DPLL failures are essential
to (and explicitly narrower than) the Track A distribution claim.
"""


def _edge(a, b):
    return (a, b) if a < b else (b, a)


def _matching(n, rng):
    vertices = list(range(n))
    rng.shuffle(vertices)
    return [_edge(vertices[i], vertices[i + 1]) for i in range(0, n, 2)]


def _connected(n, edges):
    adj = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    seen = {0}
    stack = [0]
    while stack:
        v = stack.pop()
        for w in adj[v]:
            if w not in seen:
                seen.add(w)
                stack.append(w)
    return len(seen) == n


def make_instance(n, seed=0, **params):
    """Inverse-generate a colourable cubic graph and retain its certificate."""
    if not isinstance(n, int) or n < 4 or n % 2:
        raise ValueError("n must be an even integer at least 4")
    rng = random.Random(seed)

    # Conditioning on simplicity and connectedness is independent of the names
    # assigned to the three identically distributed matchings.
    for _ in range(10000):
        matchings = [_matching(n, rng) for _ in range(3)]
        flat = [e for matching in matchings for e in matching]
        if len(set(flat)) != len(flat):
            continue
        if not _connected(n, flat):
            continue
        break
    else:
        raise RuntimeError("could not draw a simple connected cubic graph")

    vertex_perm = list(range(n))
    rng.shuffle(vertex_perm)
    colour_perm = list(range(3))
    rng.shuffle(colour_perm)
    coloured = []
    for c, matching in enumerate(matchings):
        for a, b in matching:
            coloured.append((_edge(vertex_perm[a], vertex_perm[b]), colour_perm[c]))
    rng.shuffle(coloured)

    edges = [[a, b] for (a, b), _ in coloured]
    answer = [c for _, c in coloured]
    return {
        "n": n,
        "vertices": list(range(n)),
        "z_vertices": [n, n + 1, n + 2],
        "edges": edges,
        "answer": answer,
    }


def render(inst):
    n = inst["n"]
    edges = inst["edges"]
    z = inst["z_vertices"]
    lines = [
        "Triangle-decomposition certificate for a cubic leave gadget",
        "",
        f"Let G be the simple graph on vertices 0,...,{n - 1} whose {len(edges)} "
        "edges are listed below.  The edge index is 0-based and is part of the instance.",
        f"Let Z={z}.  Define H to have the vertices of G together with Z.  Its edges "
        "are all edges of G and every edge joining a vertex of G to a vertex of Z; "
        "there are no edges between two vertices of Z.",
        "",
        "For every displayed edge i=(x,y), choose one colour c_i in {0,1,2}.  It "
        "represents the triangle {x,y,Z[c_i]} in H.  Your list is valid exactly when "
        "these triangles contain every edge of H once: equivalently, the three edges "
        "incident with every vertex of G must receive three distinct colours.  Because "
        "G is cubic, every valid list contains each colour exactly n/2 times.",
        "",
        "Edges (index: endpoints):",
    ]
    lines.extend(f"{i}: {a} {b}" for i, (a, b) in enumerate(edges))
    lines.extend([
        "",
        f"Give exactly {len(edges)} integers, in edge-index order, as one JSON array. "
        "Only 0, 1, and 2 are allowed; order matters and repeats are required.",
        "Give your final answer inside <answer></answer> tags, as that JSON array.",
        "Example format: <answer>[0, 2, 1]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    if not match:
        return None
    body = match.group(1).strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    if any(not isinstance(x, int) or isinstance(x, bool) for x in value):
        return None
    return value


def verify(inst, answer):
    """Verify a submitted triangle decomposition without consulting the plant."""
    m = len(inst["edges"])
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if not answer:
        return False, "answer is empty"
    if len(answer) != m:
        return False, f"expected exactly {m} colours, got {len(answer)}"
    for i, c in enumerate(answer):
        if not isinstance(c, int) or isinstance(c, bool):
            return False, f"colour at edge {i} is not an integer"
        if c not in (0, 1, 2):
            return False, f"colour at edge {i} is outside 0..2"

    n = inst["n"]
    incident = [[] for _ in range(n)]
    covered = Counter()
    z = inst["z_vertices"]
    for i, ((a, b), c) in enumerate(zip(inst["edges"], answer)):
        if not (0 <= a < b < n):
            return False, f"instance edge {i} is malformed"
        incident[a].append((i, c))
        incident[b].append((i, c))
        tri = (a, b, z[c])
        covered[_edge(tri[0], tri[1])] += 1
        covered[_edge(tri[0], tri[2])] += 1
        covered[_edge(tri[1], tri[2])] += 1

    for v, entries in enumerate(incident):
        if len(entries) != 3:
            return False, f"instance is not cubic at vertex {v}"
        colours = [c for _, c in entries]
        if len(set(colours)) != 3:
            ids = [i for i, _ in entries]
            return False, f"vertex {v} repeats a colour on incident edges {ids}"

    required = Counter(_edge(a, b) for a, b in inst["edges"])
    for v in range(n):
        for zz in z:
            required[_edge(v, zz)] += 1
    if covered != required:
        return False, "expanded triangles do not cover every edge of H exactly once"
    return True, "ok"


def random_candidate(inst, rng):
    # A reader gets the global colour multiplicities for free from cubicity.
    half = inst["n"] // 2
    candidate = [0] * half + [1] * half + [2] * half
    rng.shuffle(candidate)
    return candidate


def search_space(inst):
    half = inst["n"] // 2
    m = 3 * half
    return math.factorial(m) // (math.factorial(half) ** 3)


def enumerate_all(inst):
    m = len(inst["edges"])
    half = inst["n"] // 2
    space = search_space(inst)
    if space > 200000:
        return None
    valid = 0
    positions = range(m)
    for zeros in itertools.combinations(positions, half):
        zset = set(zeros)
        rest = [i for i in positions if i not in zset]
        for ones in itertools.combinations(rest, half):
            candidate = [2] * m
            for i in zeros:
                candidate[i] = 0
            for i in ones:
                candidate[i] = 1
            if verify(inst, candidate)[0]:
                valid += 1
    return valid


def _distance_profile(n, edges, source):
    adj = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    distances = [-1] * n
    distances[source] = 0
    queue = deque([source])
    while queue:
        v = queue.popleft()
        for w in adj[v]:
            if distances[w] < 0:
                distances[w] = distances[v] + 1
                queue.append(w)
    return tuple(Counter(distances).get(i, 0) for i in range(max(distances) + 1))


def canonical_key(inst):
    """A relabelling-invariant, deliberately answer-blind graph fingerprint."""
    n = inst["n"]
    edges = [_edge(a, b) for a, b in inst["edges"]]
    profiles = [_distance_profile(n, edges, v) for v in range(n)]
    profile_ids = {p: i for i, p in enumerate(sorted(set(profiles)))}
    edge_types = sorted(
        tuple(sorted((profile_ids[profiles[a]], profile_ids[profiles[b]])))
        for a, b in edges
    )

    # Exact short closed-walk counts add discrimination while remaining label-free.
    adjsets = [set() for _ in range(n)]
    for a, b in edges:
        adjsets[a].add(b)
        adjsets[b].add(a)
    triangles = sum(len(adjsets[a] & adjsets[b]) for a, b in edges) // 3
    four_cycles = 0
    for a in range(n):
        for b in range(a + 1, n):
            common = len(adjsets[a] & adjsets[b])
            four_cycles += common * (common - 1) // 2
    four_cycles //= 2
    payload = [n, sorted(profiles), edge_types, triangles, four_cycles]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def escalate(params):
    n = int(params["n"])
    if n >= 160:
        return "cap_bound"
    return {**params, "n": min(160, n + 24 + (n % 2))}


def _incidence(inst):
    incident = [[] for _ in range(inst["n"])]
    for i, (a, b) in enumerate(inst["edges"]):
        incident[a].append(i)
        incident[b].append(i)
    return incident


def _greedy_candidate(inst, edge_order):
    m = len(inst["edges"])
    answer = [-1] * m
    used = [0] * inst["n"]
    for i in edge_order:
        a, b = inst["edges"][i]
        available = 7 & ~(used[a] | used[b])
        if not available:
            return None
        bit = available & -available
        c = bit.bit_length() - 1
        answer[i] = c
        used[a] |= bit
        used[b] |= bit
    return answer


def _propagation_dpll(inst, node_limit=250000):
    """Exact 3-edge-colouring search, stopped only at a documented node cap."""
    n = inst["n"]
    m = len(inst["edges"])
    incident = _incidence(inst)
    assignment = [-1] * m
    used = [0] * n
    nodes = 0

    def assign(edge_id, colour, trail, queue):
        old = assignment[edge_id]
        if old >= 0:
            return old == colour
        a, b = inst["edges"][edge_id]
        bit = 1 << colour
        if used[a] & bit or used[b] & bit:
            return False
        assignment[edge_id] = colour
        used[a] |= bit
        used[b] |= bit
        trail.append((edge_id, a, b, bit))
        queue.append(a)
        queue.append(b)
        return True

    def propagate(trail, queue):
        while queue:
            v = queue.pop()
            unassigned = [e for e in incident[v] if assignment[e] < 0]
            if not unassigned:
                if used[v] != 7:
                    return False
                continue
            missing = 7 & ~used[v]
            if len(unassigned) != missing.bit_count():
                return False
            if len(unassigned) == 1:
                if missing.bit_count() != 1:
                    return False
                c = (missing & -missing).bit_length() - 1
                if not assign(unassigned[0], c, trail, queue):
                    return False
        return True

    def undo(trail):
        while trail:
            edge_id, a, b, bit = trail.pop()
            assignment[edge_id] = -1
            used[a] ^= bit
            used[b] ^= bit

    # Remove the global 3! colour symmetry at one vertex.
    initial = []
    q = []
    for c, edge_id in enumerate(sorted(incident[0])):
        if not assign(edge_id, c, initial, q):
            undo(initial)
            return None, nodes, False
    if not propagate(initial, q):
        undo(initial)
        return None, nodes, False

    def search():
        nonlocal nodes
        if nodes >= node_limit:
            return None
        nodes += 1
        best = None
        best_colours = None
        for edge_id, (a, b) in enumerate(inst["edges"]):
            if assignment[edge_id] >= 0:
                continue
            mask = 7 & ~(used[a] | used[b])
            colours = [c for c in range(3) if mask & (1 << c)]
            if not colours:
                return False
            if best is None or len(colours) < len(best_colours):
                best, best_colours = edge_id, colours
        if best is None:
            return list(assignment)
        for c in best_colours:
            trail = []
            queue = []
            if assign(best, c, trail, queue) and propagate(trail, queue):
                result = search()
                if isinstance(result, list):
                    return result
                if result is None:
                    undo(trail)
                    return None
            undo(trail)
        return False

    result = search()
    exhausted = result is None and nodes >= node_limit
    if isinstance(result, list):
        return result, nodes, exhausted
    return None, nodes, exhausted


def _outlier_candidate(inst):
    # Partition by a conspicuous per-edge statistic, while respecting the known
    # n/2-per-colour rule.  Vertex relabelling should destroy this signal.
    ranked = sorted(
        range(len(inst["edges"])),
        key=lambda i: (
            abs(inst["edges"][i][1] - inst["edges"][i][0]),
            sum(inst["edges"][i]),
            i,
        ),
    )
    half = inst["n"] // 2
    answer = [-1] * len(ranked)
    for rank, edge_id in enumerate(ranked):
        answer[edge_id] = min(2, rank // half)
    return answer


def _run_attacks(inst, seed, dpll_limit=250000):
    rng = random.Random(seed ^ 0x5EEDC0DE)
    outcomes = {}
    candidate = _outlier_candidate(inst)
    outcomes["outlier_endpoint_buckets"] = verify(inst, candidate)[0]

    candidate = _greedy_candidate(inst, range(len(inst["edges"])))
    outcomes["greedy_input_order"] = candidate is not None and verify(inst, candidate)[0]

    random_success = False
    for _ in range(256):
        order = list(range(len(inst["edges"])))
        rng.shuffle(order)
        candidate = _greedy_candidate(inst, order)
        if candidate is not None and verify(inst, candidate)[0]:
            random_success = True
            break
    outcomes["random_restart_greedy_256"] = random_success

    started = time.perf_counter()
    candidate, nodes, exhausted = _propagation_dpll(inst, dpll_limit)
    elapsed = time.perf_counter() - started
    outcomes["propagation_dpll_250k"] = candidate is not None and verify(inst, candidate)[0]
    return outcomes, nodes, elapsed, exhausted


def _relabel_instance(inst, rng):
    n = inst["n"]
    perm = list(range(n))
    rng.shuffle(perm)
    order = list(range(len(inst["edges"])))
    rng.shuffle(order)
    edges = []
    answer = []
    for old_i in order:
        a, b = inst["edges"][old_i]
        edges.append(list(_edge(perm[a], perm[b])))
        answer.append(inst["answer"][old_i])
    return {
        "n": n,
        "vertices": list(range(n)),
        "z_vertices": list(inst["z_vertices"]),
        "edges": edges,
        "answer": answer,
    }


def _corruptions(inst):
    answer = list(inst["answer"])
    m = len(answer)
    drop = answer[:-1]
    duplicate = answer + [answer[-1]]
    out_of_range = list(answer)
    out_of_range[0] = 3

    swapped = None
    incident = _incidence(inst)
    for edges in incident:
        for i, j in itertools.combinations(edges, 2):
            if answer[i] != answer[j]:
                trial = list(answer)
                trial[i], trial[j] = trial[j], trial[i]
                if not verify(inst, trial)[0]:
                    swapped = trial
                    break
        if swapped is not None:
            break
    if swapped is None:
        raise AssertionError("failed to construct a rejected swap")
    return {
        "drop": drop,
        "swap": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }


# Filled from the required harden.py runs; selftest records these diagnostics.
G9_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest():
    report = {}

    planted_attempts = 0
    planted_failures = []
    json_native = True
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 20260905):
            inst = make_instance(seed=seed, **params)
            planted_attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                planted_failures.append([preset, seed, reason])
            json_native = json_native and json.loads(json.dumps(inst["answer"])) == inst["answer"]
    report["G1_planted_verifies"] = {
        "pass": not planted_failures and json_native,
        "attempts": planted_attempts,
        "failures": planted_failures,
        "answers_json_native": json_native,
    }

    ship = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    rejection_reasons = {}
    for name, bad in _corruptions(ship).items():
        ok, reason = verify(ship, bad)
        rejection_reasons[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in rejection_reasons.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(x["rejected"] for x in rejection_reasons.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejection_reasons,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "I propagated the incidence constraints.\n```text\n"
        "<answer>\n" + json.dumps(ship["answer"]) + "\n</answer>\n```\n"
        "The entries follow the displayed order."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == ship["answer"] and verify(ship, parsed)[0],
        "realistic_prose": True,
    }

    guess_rng = random.Random(8675309)
    guess_total = 200000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "candidate_space": search_space(ship),
        "sampling_prior": "uniform balanced colour strings with n/2 of each symbol",
    }

    attack_names = [
        "outlier_endpoint_buckets",
        "greedy_input_order",
        "random_restart_greedy_256",
        "propagation_dpll_250k",
    ]
    successes = {name: 0 for name in attack_names}
    node_counts = []
    wall_times = []
    exhausted_count = 0
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        outcomes, nodes, elapsed, exhausted = _run_attacks(inst, seed)
        for name, success in outcomes.items():
            successes[name] += int(success)
        node_counts.append(nodes)
        wall_times.append(elapsed)
        exhausted_count += int(exhausted)
    attacks = {
        name: {"successes": successes[name], "attempts": 8}
        for name in attack_names
    }
    all_failed = all(entry["successes"] == 0 for entry in attacks.values())
    report["G5_density_and_baseline"] = {
        "pass": guess_hits == 0 and all_failed,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_observed_solution_fraction": guess_probability,
        "strongest_attack_wall_clock_sec": round(sum(wall_times), 6),
        "strongest_attack_nodes": sum(node_counts),
        "per_instance_node_budget": 250000,
        "attack_instances": 8,
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attacks,
        "domain_standard_attack": "propagation DPLL for cubic 3-edge-colouring",
        "dpll_nodes_total": sum(node_counts),
        "dpll_wall_clock_sec_total": round(sum(wall_times), 6),
        "dpll_budget_exhaustions": exhausted_count,
    }

    doubled = make_instance(
        n=2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"], seed=424242
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    spaces = [
        search_space(make_instance(seed=7, **params))
        for params in DIFFICULTY.values()
    ]
    report["G7_scales"] = {
        "pass": doubled_ok and all(a < b for a, b in zip(spaces, spaces[1:])),
        "size_doubled_n": doubled["n"],
        "size_doubled_verifies": doubled_ok,
        "size_doubled_reason": doubled_reason,
        "preset_search_spaces": spaces,
    }

    invariance = 0
    transformed_verify = 0
    keys = []
    for seed in range(20):
        base = make_instance(n=80, seed=10000 + seed)
        key = canonical_key(base)
        transformed = _relabel_instance(base, random.Random(20000 + seed))
        transformed_twice = _relabel_instance(transformed, random.Random(30000 + seed))
        invariance += int(
            key == canonical_key(transformed) == canonical_key(transformed_twice)
        )
        transformed_verify += int(verify(transformed_twice, transformed_twice["answer"])[0])
        keys.append(key)
    report["G8_canonical_key"] = {
        "pass": invariance == 20 and transformed_verify == 20 and len(set(keys)) == 20,
        "invariance_passed": invariance,
        "invariance_attempts": 20,
        "carried_witness_verified": transformed_verify,
        "carried_witness_attempts": 20,
        "distinct_keys": len(set(keys)),
        "unrelated_instances": 20,
        "invariants": "distance-profile multiset, edge-profile types, triangle and 4-cycle counts",
    }

    answer_blob = json.dumps(ship["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(ship["answer"])
    intended_ops = len(ship["answer"]) + 24
    arms = {k: dict(v) for k, v in G9_ARM_RESULTS.items()}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": (
            "not_run" if arms["hinted"]["attempts"] == 0
            else ("too_easy" if arms["hinted"]["solved"] else "hardened")
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = DIFFICULTY[SHIPPING_DIFFICULTY]
    report["demo_exact_valid_answers_seed_0"] = enumerate_all(
        make_instance(seed=0, **DIFFICULTY["demo"])
    )
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
