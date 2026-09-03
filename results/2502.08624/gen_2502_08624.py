"""Verified generators for large sum-free subsets of integer sets.

The public problem is exactly the one in Bedert's paper: given a finite set A
of integers, exhibit (through its compact deletion-set representation) a
prescribed-size subset B with no x,y,z in B satisfying x+y=z.  Instances are
inverse-generated from a regular graph with a planted independent set.  A
Sidon-style integer encoding makes the graph edges exactly the Schur triples
of A.

Standard library only.  Importing this module has no side effects.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re
from collections import Counter


DIFFICULTY = {
    # n is the number of Boolean variables; occurrences is per sign and must
    # be a positive multiple of three.
    "demo": {"n": 3, "occurrences": 3},
    "easy": {"n": 50, "occurrences": 9},
    "medium": {"n": 65, "occurrences": 9},
    "hard": {"n": 80, "occurrences": 9},
}
SHIPPING_DIFFICULTY = "easy"


NOTES = r"""
Bedert, 'Large sum-free subsets of sets of integers via L^1-estimates for
trigonometric series' (arXiv:2502.08624), Section 1 fixes the definition used
here: B is sum-free when there are no x,y,z in B, with repetitions allowed,
such that x+y=z.  Section 2 explains the easy universal construction: a torus
dilate landing in the open interval (1/3,2/3) gives at least |A|/3 elements.
Theorem 1.1 improves this existential guarantee by c log log |A|, but it is not
a computational hardness theorem.  Consequently this generator does not ask
for a merely one-third-size witness.

Hardness is supplied by the standard graph-to-solution-free-set regime:
Edwards and Noble, 'The complexity of solution-free sets of integers',
Theorem 3.5 and Corollary 3.4, prove strong NP-completeness via Independent
Set, including x+y=z over positive integers; their Theorem 5.3 identifies the
easy fixed-density side (at or below kappa=1/3) and NP-completeness above it.
Our compact Sidon encoding is a special-purpose realization of the same
reduction.  Worst-case hardness does not prove this planted distribution hard,
so the empirical attack panel and the external LLM loop remain essential.

To defeat construction leakage, the planted object is a balanced satisfiable
3-CNF formula.  Every variable occurs the same number of times with each sign;
half the clauses have one planted-true literal and half have two.  In the
standard clause/contradiction graph every literal occurrence therefore has
exactly the same degree.  Vertex indices are randomly permuted before integer
encoding, defeating position/magnitude rules.  Straightforward greedy and
random-order restart attacks stay below the target at the shipped preset.
Edge-label integers are structurally recognizable, so random_candidate gives a
guesser the normalized representation for free: it deletes only graph-vertex
labels and guesses which target-size independent set remains.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _edge(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _weighted_remaining(counts: list[int], forbidden: set[int],
                        rng: random.Random) -> int | None:
    total = sum(count for v, count in enumerate(counts)
                if count and v not in forbidden)
    if total == 0:
        return None
    pick = rng.randrange(total)
    for v, count in enumerate(counts):
        if not count or v in forbidden:
            continue
        if pick < count:
            return v
        pick -= count
    raise AssertionError("weighted choice fell through")


def _balanced_formula_graph(variable_count: int, occurrences: int,
                            rng: random.Random) -> tuple[list[tuple[int, int]], set[int]]:
    """Build the regular clause/contradiction graph of a planted 3-CNF.

    Each variable occurs ``occurrences`` times as a planted-true literal and
    the same number as a planted-false literal.  Exactly half the clauses have
    one true slot and half have two, so both slot distributions are balanced.
    A graph vertex is a literal occurrence.  Clause triples are cliques, and
    every pair of opposite-sign occurrences of one variable is adjacent.
    """
    if variable_count < 3:
        raise ValueError("n must be at least 3")
    if occurrences < 3 or occurrences % 3:
        raise ValueError("occurrences must be a positive multiple of 3")
    clause_count = 2 * variable_count * occurrences // 3

    # Sample the witness slots before any formula data or graph edges.
    order = list(range(clause_count))
    rng.shuffle(order)
    one_true = set(order[:clause_count // 2])
    patterns: list[list[int]] = []
    selected_slots: set[int] = set()
    for clause in range(clause_count):
        true_count = 1 if clause in one_true else 2
        pattern = [1] * true_count + [0] * (3 - true_count)
        rng.shuffle(pattern)
        patterns.append(pattern)
        selected_slots.add(3 * clause + rng.choice(
            [i for i, truth in enumerate(pattern) if truth]))

    # Assign balanced variable/sign tokens to the pre-sampled slots.  Reject a
    # rare dead end; the accepted formula has three distinct variables/clause.
    slot_variable = []
    slot_truth = []
    for _attempt in range(20_000):
        remaining_true = [occurrences] * variable_count
        remaining_false = [occurrences] * variable_count
        slot_variable = [-1] * (3 * clause_count)
        slot_truth = [-1] * (3 * clause_count)
        clauses = list(range(clause_count))
        rng.shuffle(clauses)
        complete = True
        for clause in clauses:
            positions = [0, 1, 2]
            rng.shuffle(positions)
            used: set[int] = set()
            for position in positions:
                truth = patterns[clause][position]
                counts = remaining_true if truth else remaining_false
                variable = _weighted_remaining(counts, used, rng)
                if variable is None:
                    complete = False
                    break
                counts[variable] -= 1
                used.add(variable)
                slot = 3 * clause + position
                slot_variable[slot] = variable
                slot_truth[slot] = truth
            if not complete:
                break
        if complete:
            break
    else:
        raise RuntimeError("could not construct a balanced formula")

    edges: set[tuple[int, int]] = set()
    for clause in range(clause_count):
        a, b, c = 3 * clause, 3 * clause + 1, 3 * clause + 2
        edges.update((_edge(a, b), _edge(a, c), _edge(b, c)))
    occurrences_by_kind = {(v, truth): [] for v in range(variable_count)
                           for truth in (0, 1)}
    for slot, (variable, truth) in enumerate(zip(slot_variable, slot_truth)):
        occurrences_by_kind[variable, truth].append(slot)
    for variable in range(variable_count):
        for a in occurrences_by_kind[variable, 0]:
            for b in occurrences_by_kind[variable, 1]:
                edges.add(_edge(a, b))

    vertex_count = 3 * clause_count
    degree = occurrences + 2
    degrees = [0] * vertex_count
    for a, b in edges:
        degrees[a] += 1
        degrees[b] += 1
    if any(value != degree for value in degrees):
        raise AssertionError("balanced formula graph is not regular")

    relabel = list(range(vertex_count))
    rng.shuffle(relabel)
    relabelled_edges = sorted({_edge(relabel[a], relabel[b]) for a, b in edges})
    selected = {relabel[v] for v in selected_slots}
    return relabelled_edges, selected


def _encode_graph(vertex_count: int, edges: list[tuple[int, int]],
                  selected: set[int], target_size: int,
                  rng: random.Random, scale: int = 1) -> dict:
    """Encode a simple graph so its only x+y=z relations are graph edges."""
    if scale == 0:
        raise ValueError("scale must be nonzero")
    # r_i = C*i+i^2 is Sidon: equality of two pair sums first forces equal
    # index sums (C dominates), then equal products, hence the same pair.
    c = 2 * vertex_count * vertex_count + 1
    offsets = [c * i + i * i for i in range(vertex_count)]
    radius = offsets[-1]
    base = 2 * radius + 1
    vertices = [(base + x) * scale for x in offsets]
    edge_values = [(vertices[a] + vertices[b]) for a, b in edges]
    if len(set(edge_values)) != len(edge_values):
        raise AssertionError("Sidon encoding collision")
    relations = [(vertices[a], vertices[b], vertices[a] + vertices[b])
                 for a, b in edges]
    numbers = vertices + edge_values
    rng.shuffle(numbers)
    # The witness is represented compactly by the deletion set D.  Keeping all
    # edge labels and exactly the selected graph vertices gives A \\ D.
    answer = sorted(vertices[i] for i in range(vertex_count) if i not in selected)
    inst = {
        "n": vertex_count // 10,
        "vertex_count": vertex_count,
        "degree": (2 * len(edges)) // vertex_count,
        "target_size": target_size,
        "deletion_count": len(numbers) - target_size,
        "numbers": numbers,
        "answer": answer,
        # Private-but-serializable construction data accelerate exact checking
        # and enable the self-test attacks.  render() deliberately reveals only
        # the mathematical instance above.
        "_vertices": vertices,
        "_edge_values": edge_values,
        "_relations": relations,
        "_graph_edges": edges,
        "_selected_indices": sorted(selected),
        "_membership": {x: True for x in numbers},
    }
    return inst


def make_instance(n: int, seed: int = 0, occurrences: int = 6, **params) -> dict:
    """Sample a satisfying witness first, then build its encoded integer set.

    ``n`` is the number of Boolean variables in the hidden balanced 3-CNF.
    ``occurrences`` is the count per variable sign.  Larger n enlarges the
    regular independent-set instance; larger occurrences increases crowding.
    """
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if isinstance(occurrences, bool) or not isinstance(occurrences, int):
        raise ValueError("occurrences must be an integer")
    rng = random.Random(seed)
    # The witness slots are sampled inside the constructor before literal
    # tokens, clauses, contradiction edges, or integer labels are created.
    edges, planted = _balanced_formula_graph(n, occurrences, rng)
    vertex_count = 2 * n * occurrences
    target_size = len(edges) + len(planted)
    inst = _encode_graph(vertex_count, edges, planted, target_size, rng)
    inst["n"] = n
    inst["occurrences"] = occurrences
    return inst


def render(inst: dict) -> str:
    """Return the complete self-contained problem statement."""
    values = ", ".join(str(x) for x in inst["numbers"])
    return (
        "SUM-FREE SUBSET WITNESS\n\n"
        "You are given a finite set A of distinct integers. Produce a deletion "
        f"set D of exactly {inst['deletion_count']} distinct elements of A such "
        f"that the retained set B = A \\ D has exactly {inst['target_size']} "
        "elements and is sum-free.\n\n"
        "Definition: B is sum-free when there do not exist x, y, z in B with "
        "x + y = z. The variables are not required to be distinct, so x = y "
        "must also be checked. Ordinary integer addition is used (not modular "
        "arithmetic).\n\n"
        "The answer is the unordered deletion set D, not the retained set B. "
        "Output each deleted integer exactly once. Every output integer must "
        "occur in A. No other compression or ranges are allowed.\n\n"
        f"|A| = {len(inst['numbers'])}\n"
        f"Required |D| = {inst['deletion_count']}\n"
        f"Resulting |B| = {inst['target_size']}\n"
        f"A = {values}\n\n"
        "Give your final answer inside <answer></answer> tags, as a "
        "comma-separated list of base-10 integers.\n"
        "Example syntax: <answer>3, 17, 42</answer>\n"
        "Output nothing else inside the tags."
    )


def parse_answer(text: str) -> object | None:
    """Parse the last well-formed tagged comma-separated integer list."""
    if not isinstance(text, str):
        return None
    blocks = _ANSWER_RE.findall(text)
    if not blocks:
        return None
    body = blocks[-1].strip()
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1].strip()
    if not body or not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", body):
        return None
    try:
        return [int(piece.strip()) for piece in body.split(",")]
    except (TypeError, ValueError, OverflowError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid witness, without consulting the planted answer."""
    if answer is None:
        return False, "missing_answer"
    if not isinstance(answer, (list, tuple)):
        return False, "answer_not_a_list"
    if len(answer) == 0:
        return False, "empty_answer"
    if len(answer) != inst["deletion_count"]:
        return False, "wrong_length"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "non_integer_element"
    if len(set(answer)) != len(answer):
        return False, "duplicate_element"
    membership = inst.get("_membership")
    if membership is None:
        membership = {x: True for x in inst["numbers"]}
    if any(x not in membership for x in answer):
        return False, "element_not_in_instance"
    deleted = set(answer)
    relations = inst.get("_relations")
    if relations is None:
        relations = _all_relations(inst["numbers"])
    for x, y, z in relations:
        if x not in deleted and y not in deleted and z not in deleted:
            return False, f"sum_relation:{x}+{y}={z}"
    return True, "ok"


def _all_relations(numbers: list[int] | tuple[int, ...]) -> list[tuple[int, int, int]]:
    vals = sorted(set(numbers))
    present = set(vals)
    out = []
    for i, x in enumerate(vals):
        for y in vals[i:]:
            z = x + y
            if z in present:
                out.append((x, y, z))
    return out


def _roles(inst: dict) -> tuple[list[int], list[int]]:
    vertices = inst.get("_vertices")
    edge_values = inst.get("_edge_values")
    if vertices is not None and edge_values is not None:
        return list(vertices), list(edge_values)
    rels = _all_relations(inst["numbers"])
    operands = {x for x, y, _z in rels for x in (x, y)}
    results = {z for _x, _y, z in rels}
    return sorted(operands), sorted(results - operands)


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample from the solver-aware normalized space.

    The Schur triples reveal result-only edge labels.  The graph reduction says
    any size-target retained set can be normalized to contain all of them, so a
    fair guesser deletes only graph vertices and guesses which ones remain.
    """
    vertices, edge_values = _roles(inst)
    keep = inst["target_size"] - len(edge_values)
    delete = len(vertices) - keep
    return rng.sample(vertices, delete)


def search_space(inst: dict) -> int | None:
    """Return the naive number of target-size subsets of A."""
    return math.comb(len(inst["numbers"]), inst["deletion_count"])


def enumerate_all(inst: dict) -> int | None:
    """Exactly count all valid witnesses when at most 500,000 are possible."""
    total = search_space(inst)
    if total is None or total > 500_000:
        return None
    count = 0
    for candidate in itertools.combinations(inst["numbers"], inst["deletion_count"]):
        if verify(inst, candidate)[0]:
            count += 1
    return count


def _extract_graph(numbers: list[int] | tuple[int, ...]) -> tuple[list[int], list[tuple[int, int]]]:
    relations = _all_relations(numbers)
    vertex_values = sorted({q for x, y, _z in relations for q in (x, y)})
    pos = {x: i for i, x in enumerate(vertex_values)}
    graph_edges = sorted({_edge(pos[x], pos[y]) for x, y, _z in relations if x != y})
    return vertex_values, graph_edges


def canonical_key(inst: dict) -> str:
    """Return a relabelling- and scaling-invariant structural graph key.

    General graph isomorphism is not solved here.  The key uses strong exact
    invariants: edge/nonedge common-neighbour histograms and the multiset of
    per-vertex local common-neighbour signatures.
    """
    if "_graph_edges" in inst and "vertex_count" in inst:
        n = inst["vertex_count"]
        edges = [tuple(e) for e in inst["_graph_edges"]]
    else:
        vertices, edges = _extract_graph(inst["numbers"])
        n = len(vertices)
    adj = [set() for _ in range(n)]
    for a, b in edges:
        adj[a].add(b)
        adj[b].add(a)
    masks = []
    for nbrs in adj:
        mask = 0
        for v in nbrs:
            mask |= 1 << v
        masks.append(mask)
    edge_set = set(edges)
    edge_common: Counter[int] = Counter()
    nonedge_common: Counter[int] = Counter()
    local_edge = [Counter() for _ in range(n)]
    local_nonedge = [Counter() for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            # bin(...).count is used instead of int.bit_count for the older
            # Python shipped on some corpus builders.
            common = bin(masks[i] & masks[j]).count("1")
            if (i, j) in edge_set:
                edge_common[common] += 1
                local_edge[i][common] += 1
                local_edge[j][common] += 1
            else:
                nonedge_common[common] += 1
                local_nonedge[i][common] += 1
                local_nonedge[j][common] += 1
    local_signatures = sorted(
        (tuple(sorted(local_edge[v].items())), tuple(sorted(local_nonedge[v].items())))
        for v in range(n))

    payload = {
        "vertices": n,
        "edges": len(edges),
        "target_vertices": inst["target_size"] - len(edges),
        "degrees": sorted(len(x) for x in adj),
        "edge_common": sorted(edge_common.items()),
        "nonedge_common": sorted(nonedge_common.items()),
        "local_common": local_signatures,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return "sumfree-graph-v1:" + hashlib.sha256(raw).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase both graph size and crowding, up to a practical render limit."""
    n = int(params.get("n", 3))
    occurrences = int(params.get("occurrences", 3))
    if n >= 80:
        return None
    return {"n": n + 15, "occurrences": min(occurrences + 3, 12)}


def _adjacency(inst: dict) -> list[set[int]]:
    n = inst["vertex_count"]
    adj = [set() for _ in range(n)]
    for a, b in inst["_graph_edges"]:
        adj[a].add(b)
        adj[b].add(a)
    return adj


def _is_independent(adj: list[set[int]], chosen: list[int] | set[int]) -> bool:
    s = set(chosen)
    return all(not (adj[v] & s) for v in s)


def _greedy_set(adj: list[set[int]], order: list[int]) -> list[int]:
    chosen: list[int] = []
    occupied: set[int] = set()
    for v in order:
        if v not in occupied:
            chosen.append(v)
            occupied.add(v)
            occupied.update(adj[v])
    return chosen


def _dynamic_min_degree(adj: list[set[int]], rng: random.Random | None = None) -> list[int]:
    remaining = set(range(len(adj)))
    chosen = []
    while remaining:
        scores = [(len(adj[v] & remaining), v) for v in remaining]
        minimum = min(x for x, _v in scores)
        tied = [v for x, v in scores if x == minimum]
        v = rng.choice(tied) if rng is not None else min(tied)
        chosen.append(v)
        remaining.discard(v)
        remaining.difference_update(adj[v])
    return chosen


def _attack_outlier(inst: dict) -> dict:
    adj = _adjacency(inst)
    k = len(inst["_selected_indices"])
    triangles = []
    for v, nbrs in enumerate(adj):
        tri = sum(1 for a in nbrs for b in adj[a] if b in nbrs and a < b)
        triangles.append(tri)
    variants = {
        "lowest_position": list(range(k)),
        "highest_position": list(range(len(adj) - k, len(adj))),
        "fewest_triangles": sorted(range(len(adj)), key=lambda v: (triangles[v], v))[:k],
        "most_triangles": sorted(range(len(adj)), key=lambda v: (-triangles[v], v))[:k],
        "lowest_degree": sorted(range(len(adj)), key=lambda v: (len(adj[v]), v))[:k],
        "highest_degree": sorted(range(len(adj)), key=lambda v: (-len(adj[v]), v))[:k],
    }
    solved = [name for name, chosen in variants.items() if _is_independent(adj, chosen)]
    return {"solved": bool(solved), "successful_rules": solved,
            "rules_tried": len(variants)}


def _attack_greedy(inst: dict) -> dict:
    adj = _adjacency(inst)
    n = len(adj)
    k = len(inst["_selected_indices"])
    triangle = [sum(1 for a in adj[v] for b in adj[a] if b in adj[v] and a < b)
                for v in range(n)]
    orders = [
        list(range(n)),
        list(reversed(range(n))),
        sorted(range(n), key=lambda v: (triangle[v], v)),
        sorted(range(n), key=lambda v: (-triangle[v], v)),
    ]
    sizes = [len(_greedy_set(adj, order)) for order in orders]
    sizes.append(len(_dynamic_min_degree(adj)))
    return {"solved": max(sizes) >= k, "best_size": max(sizes),
            "target": k, "rules_tried": len(sizes)}


def _attack_random_restart(inst: dict, seed: int) -> dict:
    adj = _adjacency(inst)
    n = len(adj)
    k = len(inst["_selected_indices"])
    rng = random.Random(seed)
    best = 0
    restarts = 64
    for _ in range(restarts):
        order = list(range(n))
        rng.shuffle(order)
        best = max(best, len(_greedy_set(adj, order)))
    return {"solved": best >= k, "best_size": best, "target": k,
            "restarts": restarts}


def _scale_instance(inst: dict, factor: int, reorder_rng: random.Random | None = None) -> dict:
    out = dict(inst)
    out["numbers"] = [factor * x for x in inst["numbers"]]
    if reorder_rng is not None:
        reorder_rng.shuffle(out["numbers"])
    out["answer"] = [factor * x for x in inst["answer"]]
    out["_vertices"] = [factor * x for x in inst["_vertices"]]
    out["_edge_values"] = [factor * x for x in inst["_edge_values"]]
    out["_relations"] = [(factor * x, factor * y, factor * z)
                         for x, y, z in inst["_relations"]]
    out["_membership"] = {x: True for x in out["numbers"]}
    return out


def _relabel_instance(inst: dict, rng: random.Random, scale: int = 1) -> dict:
    n = inst["vertex_count"]
    p = list(range(n))
    rng.shuffle(p)
    edges = sorted({_edge(p[a], p[b]) for a, b in inst["_graph_edges"]})
    selected = {p[v] for v in inst["_selected_indices"]}
    return _encode_graph(n, edges, selected, inst["target_size"], rng, scale=scale)


def selftest() -> dict:
    """Run gates G1--G8 and return a JSON-serializable evidence report."""
    report: dict[str, object] = {
        "paper": "2502.08624",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: every named preset, several unrelated seeds.
    g1_checks = 0
    g1_by_preset = {}
    g1_ok = True
    for name, params in DIFFICULTY.items():
        passed = 0
        for seed in (0, 1, 7, 41):
            inst = make_instance(seed=seed, **params)
            ok, _why = verify(inst, inst["answer"])
            passed += int(ok)
            g1_ok &= ok
            g1_checks += 1
        g1_by_preset[name] = {"passed": passed, "total": 4}
    report["G1_planted_verifies"] = {
        "pass": g1_ok, "checks": g1_checks, "by_preset": g1_by_preset}

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    base = make_instance(seed=314159, **ship_params)
    good = list(base["answer"])
    selected = set(base["_selected_indices"])
    adj = _adjacency(base)
    outside = next(v for v in range(base["vertex_count"])
                   if v not in selected and len(adj[v] & selected) >= 2)
    remove_idx = next(iter(adj[outside] & selected))
    vertex_values = base["_vertices"]
    swapped = good[:]
    # Stop deleting `outside` and instead delete one planted neighbour.  The
    # newly retained outside vertex still conflicts with another retained
    # planted neighbour, so this is a genuine one-for-one corruption.
    swapped[swapped.index(vertex_values[outside])] = vertex_values[remove_idx]
    corruptions = {
        "drop_one": good[:-1],
        "swap_one": swapped,
        "duplicate": good[:-1] + [good[0]],
        "empty": [],
        "out_of_range": good[:-1] + [max(base["numbers"]) + 1],
    }
    expected_prefix = {
        "drop_one": "wrong_length",
        "swap_one": "sum_relation:",
        "duplicate": "duplicate_element",
        "empty": "empty_answer",
        "out_of_range": "element_not_in_instance",
    }
    rejection_reasons = {}
    g2_ok = True
    for name, candidate in corruptions.items():
        ok, reason = verify(base, candidate)
        rejection_reasons[name] = reason
        g2_ok &= (not ok and reason.startswith(expected_prefix[name]))
    g2_ok &= len(set(rejection_reasons.values())) == len(rejection_reasons)
    report["G2_rejects_corruption"] = {
        "pass": g2_ok, "reasons": rejection_reasons,
        "distinct_reasons": len(set(rejection_reasons.values()))}

    body = ", ".join(map(str, good))
    realistic = ("I checked all pair sums. Here is the requested witness.\n\n"
                 "```text\n<answer>\n" + body + "\n</answer>\n```\n")
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == good, "parsed_count": len(parsed) if isinstance(parsed, list) else None,
        "expected_count": len(good)}

    # G4: the candidate generator keeps every recognizable edge label and
    # guesses only which graph vertices to delete.
    guess_rng = random.Random(271828)
    trials = 200_000
    hits = 0
    for _ in range(trials):
        hits += int(verify(base, random_candidate(base, guess_rng))[0])
    structured_space = math.comb(base["vertex_count"], len(base["_selected_indices"]))
    probability = hits / trials
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": trials,
        "measured_probability": probability,
        "structure_aware_space": structured_space,
        "naive_space": search_space(base),
    }

    # K_7 with one retained graph vertex gives a small member of the exact same
    # graph-encoding family whose full deletion-witness space is enumerable.
    tiny_edges = [_edge(a, b) for a in range(7) for b in range(a + 1, 7)]
    tiny = _encode_graph(7, tiny_edges, {0}, len(tiny_edges) + 1,
                         random.Random(23))
    exact = enumerate_all(tiny)
    naive = search_space(tiny)
    fraction = (exact / naive) if exact is not None and naive else None
    report["G5_sparse"] = {
        "pass": exact is not None and fraction is not None and fraction < 1e-3,
        "preset": "handcrafted_K7_probe", "valid_answers": exact,
        "naive_candidates": naive, "solution_fraction": fraction,
    }

    attack_records = {"outlier": [], "greedy": [], "random_restart": []}
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **ship_params)
        attack_records["outlier"].append({"seed": seed, **_attack_outlier(inst)})
        attack_records["greedy"].append({"seed": seed, **_attack_greedy(inst)})
        attack_records["random_restart"].append(
            {"seed": seed, **_attack_random_restart(inst, seed ^ 0x5A5A)})
    attack_summary = {}
    g6_ok = True
    for name, rows in attack_records.items():
        successes = sum(int(row["solved"]) for row in rows)
        attack_summary[name] = {
            "pass": successes == 0,
            "successes": successes,
            "seeds_tested": len(rows),
            "details": rows,
        }
        g6_ok &= successes == 0 and len(rows) >= 8
    report["G6_adversary_panel"] = {
        "pass": g6_ok, "attacks": attack_summary}

    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=99, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["vertex_count"] == 2 * base["vertex_count"]
                and len(doubled["numbers"]) > len(base["numbers"]),
        "base_vertices": base["vertex_count"],
        "doubled_vertices": doubled["vertex_count"],
        "base_ground_size": len(base["numbers"]),
        "doubled_ground_size": len(doubled["numbers"]),
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = 0
    real_transform_checks = 0
    g8_ok = True
    distinct_keys = []
    for seed in range(20_000, 20_020):
        inst = make_instance(seed=seed, **ship_params)
        key = canonical_key(inst)
        distinct_keys.append(key)

        reorder = dict(inst)
        reorder["numbers"] = list(inst["numbers"])
        random.Random(seed + 1).shuffle(reorder["numbers"])
        transforms = [
            reorder,
            _scale_instance(inst, -3),
            _relabel_instance(inst, random.Random(seed + 2)),
            _relabel_instance(inst, random.Random(seed + 3), scale=-5),
        ]
        for transformed in transforms:
            invariance_checks += 1
            g8_ok &= canonical_key(transformed) == key
            ok, _why = verify(transformed, transformed["answer"])
            g8_ok &= ok
            real_transform_checks += 1
    unique = len(set(distinct_keys))
    g8_ok &= unique == len(distinct_keys)
    report["G8_canonical_key"] = {
        "pass": g8_ok,
        "invariance_checks": invariance_checks,
        "real_transformation_witness_checks": real_transform_checks,
        "unrelated_instances": len(distinct_keys),
        "distinct_keys": unique,
        "transformations": ["input reorder", "global nonzero scaling",
                            "graph-vertex relabelling plus fresh integer encoding",
                            "composition of relabelling, negative scaling, and reorder"],
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(isinstance(g, dict) and g.get("pass") for g in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
