"""Verified generators for semi-positive debt-swap reachability.

The family is the 3-Partition construction used in Proposition 6.4 and
Theorem 5.8 of Froese, Hoefer, and Wilhelmi, "Dynamic Debt Swapping in
Financial Networks" (arXiv:2302.11250v2).

Only the Python standard library is used.  Importing this module has no side
effects.  Instances are deterministic functions of ``(n, seed, params)``.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import random
import re
from collections import defaultdict, deque
from functools import lru_cache


FAMILY_VERSION = 1

# n is the number of bins in the underlying 3-Partition instance; there are
# 3*n item banks and 4*n-1 swaps in every requested witness.  ``spread`` keeps
# the expected degree of the induced exact-cover hypergraph roughly constant
# as n grows (the deviation range is spread*n^2).
DIFFICULTY = {
    "demo": {"n": 4, "spread": 2.0, "attack_filter": False},
    "easy": {"n": 24, "spread": 0.30, "attack_filter": True},
    "medium": {"n": 32, "spread": 0.30, "attack_filter": True},
    "hard": {"n": 40, "spread": 0.30, "attack_filter": True},
}

SHIPPING_DIFFICULTY = "easy"

NOTES = r"""
Definition.  Section 2 (Definitions 2.1 and 2.3) fixes a debt swap as an
exchange of the creditors of two equal-liability contracts whose two debtors
and two current creditors are four distinct banks.  Edge priorities remain
attached to contracts.  A swap is semi-positive exactly when both old
creditors weakly gain total assets and exactly one gains strictly.

Hard regime.  Section 6, Proposition 6.4 proves strong NP-hardness of deciding
semi-positive reachability under edge-ranking rules, using the acyclic
3-Partition construction of Section 5, Theorem 5.8.  This module instantiates
that construction and asks for the reaching swap sequence, not an optimum.

Easy regimes avoided.  Section 6, Theorem 6.1 gives a polynomial greedy
algorithm for unrestricted reachability, so every swap here must be
semi-positive.  Section 4, Theorem 4.6 gives polynomial local optimization for
semi-positive swaps that improve one bank, and Theorem 4.13 gives further
tractable local cases; neither answers exact target reachability.  Optimization
tasks were not used because an optimum/optimality claim is not an acceptable
witness for this generator task.

Planting and attacks.  The complete swap schedule (item identities, filler
pairings, and pulse pairings) is sampled before any item value.  Each planted
triple is then sampled symmetrically from the same bounded zero-sum
distribution, its three roles are permuted, and all item presentation order is
shuffled.  There are no differently distributed decoy items.  The deviation
range is quadratic in n, producing a constant-degree crowded 3-uniform
exact-cover graph rather than isolated planted triples.  Returned production
instances are rejected if a rank/extremes rule, a deterministic minimum-degree
greedy rule, or randomized minimum-degree greedy restarts find any partition.
""".strip()


def _edge(edge_id, debtor, creditor, liability, rank=0):
    return {
        "id": edge_id,
        "debtor": debtor,
        "creditor": creditor,
        "liability": int(liability),
        "rank": int(rank),
    }


def _sample_symmetric_triple(rng, deviation, forbidden):
    """Sample exchangeable distinct x,y,z in [-D,D] with x+y+z=0."""
    for _ in range(100_000):
        x = rng.randint(-deviation, deviation)
        y = rng.randint(-deviation, deviation)
        z = -x - y
        triple = [x, y, z]
        if not (-deviation <= z <= deviation):
            continue
        if len(set(triple)) != 3 or any(v in forbidden for v in triple):
            continue
        rng.shuffle(triple)
        return triple
    raise RuntimeError("could not sample a distinct symmetric planted triple")


def _valid_triples(values, target):
    """All index triples with distinct indices whose values sum to target."""
    # make_instance makes values distinct.  Retain a general duplicate-safe
    # fallback so attacks and enumeration remain correct for transformed data.
    positions = defaultdict(list)
    for i, value in enumerate(values):
        positions[value].append(i)
    out = []
    size = len(values)
    for i in range(size):
        for j in range(i + 1, size):
            want = target - values[i] - values[j]
            for k in positions.get(want, ()):
                if k > j:
                    out.append((i, j, k))
    return out


def _partition_ok(groups, values, target):
    if groups is None or len(groups) * 3 != len(values):
        return False
    flat = [i for group in groups for i in group]
    return (
        sorted(flat) == list(range(len(values)))
        and all(len(group) == 3 for group in groups)
        and all(sum(values[i] for i in group) == target for group in groups)
    )


def _attack_rank_extremes(values, target):
    """Cheap outlier/rank rule: smallest first, largest compatible mate."""
    remaining = set(range(len(values)))
    groups = []
    while remaining:
        first = min(remaining, key=lambda i: (values[i], i))
        others = sorted(remaining - {first}, key=lambda i: (values[i], i), reverse=True)
        chosen = None
        for second in others:
            for third in others:
                if third == second:
                    continue
                if values[first] + values[second] + values[third] == target:
                    chosen = (first, second, third)
                    break
            if chosen is not None:
                break
        if chosen is None:
            return None
        groups.append(chosen)
        remaining.difference_update(chosen)
    return groups


def _attack_greedy(values, target):
    """Minimum-current-degree exact-cover greedy, with no backtracking."""
    triples = _valid_triples(values, target)
    by_item = [[] for _ in values]
    for triple in triples:
        for item in triple:
            by_item[item].append(triple)
    remaining = set(range(len(values)))
    groups = []
    while remaining:
        choices_by_item = {
            item: [t for t in by_item[item] if all(x in remaining for x in t)]
            for item in remaining
        }
        first = min(
            remaining,
            key=lambda i: (len(choices_by_item[i]), abs(3 * values[i] - target), i),
        )
        choices = choices_by_item[first]
        if not choices:
            return None
        chosen = min(
            choices,
            key=lambda t: tuple(sorted((values[i], i) for i in t)),
        )
        groups.append(chosen)
        remaining.difference_update(chosen)
    return groups


def _attack_random_restart(values, target, restarts=24):
    """Randomized minimum-degree greedy with a modest number of restarts."""
    triples = _valid_triples(values, target)
    by_item = [[] for _ in values]
    for triple in triples:
        for item in triple:
            by_item[item].append(triple)
    digest = hashlib.sha256(json.dumps(values, separators=(",", ":")).encode()).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))
    for _ in range(restarts):
        remaining = set(range(len(values)))
        groups = []
        while remaining:
            live = {}
            for item in remaining:
                live[item] = [
                    t for t in by_item[item] if all(x in remaining for x in t)
                ]
            minimum = min(len(live[item]) for item in remaining)
            if minimum == 0:
                break
            tied = [item for item in remaining if len(live[item]) == minimum]
            first = rng.choice(tied)
            chosen = rng.choice(live[first])
            groups.append(chosen)
            remaining.difference_update(chosen)
        if not remaining:
            return groups
    return None


def _attack_results(values, target, restarts=24):
    attacks = {
        "rank_extremes": _attack_rank_extremes(values, target),
        "greedy_min_degree": _attack_greedy(values, target),
        "random_restart": _attack_random_restart(values, target, restarts),
    }
    return {name: _partition_ok(groups, values, target) for name, groups in attacks.items()}


def make_instance(n, seed=0, **params):
    """Sample a reaching sequence first, then construct its debt network.

    ``n`` is the number of target triples.  The instance has 3*n numerical
    items, and increasing n keeps the candidate-triple degree roughly constant
    while increasing exact-cover depth.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    spread = float(params.pop("spread", 0.30))
    attack_filter = bool(params.pop("attack_filter", n >= 20))
    attack_restarts = int(params.pop("attack_restarts", 24))
    max_build_attempts = int(params.pop("max_build_attempts", 500))
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if not (0.05 <= spread <= 10.0):
        raise ValueError("spread must be between 0.05 and 10")
    if attack_restarts < 1 or max_build_attempts < 1:
        raise ValueError("attack_restarts and max_build_attempts must be positive")

    rng = random.Random(seed)
    item_count = 3 * n

    # G: sample the complete abstract witness before any problem numbers.
    item_order = list(range(item_count))
    rng.shuffle(item_order)
    planted_groups = [item_order[3 * j : 3 * j + 3] for j in range(n)]
    c_fillers = list(range(item_count))
    d_fillers = list(range(n - 1))
    rng.shuffle(c_fillers)
    rng.shuffle(d_fillers)
    abstract_answer = []
    filler_pos = 0
    for stage, group in enumerate(planted_groups):
        group_order = list(group)
        rng.shuffle(group_order)
        for item in group_order:
            abstract_answer.append(tuple(sorted((f"i{item}", f"c{c_fillers[filler_pos]}"))))
            filler_pos += 1
        if stage < n - 1:
            abstract_answer.append(tuple(sorted((f"p{stage}", f"d{d_fillers[stage]}"))))

    deviation = max(20, int(round(spread * n * n)))
    base = 8 * deviation + 97
    target = 3 * base
    chosen_values = None
    chosen_density = None

    for _ in range(max_build_attempts):
        deviations = [None] * item_count
        used = set()
        for group in planted_groups:
            triple = _sample_symmetric_triple(rng, deviation, used)
            used.update(triple)
            for item, value in zip(group, triple):
                deviations[item] = value
        values_by_identity = [base + value for value in deviations]

        # The external presentation order is sampled independently of the
        # planted group order.  Edge IDs follow this presentation order so no
        # hidden identity-to-position relation survives.
        presentation = list(range(item_count))
        rng.shuffle(presentation)
        inverse = {old: new for new, old in enumerate(presentation)}
        presented_values = [values_by_identity[old] for old in presentation]
        presented_groups = [[inverse[item] for item in group] for group in planted_groups]

        triples = _valid_triples(presented_values, target)
        degrees = [0] * item_count
        for triple in triples:
            for item in triple:
                degrees[item] += 1
        crowded = (
            (not attack_filter)
            or (4 * n <= len(triples) <= 11 * n and min(degrees) >= 2)
        )
        attacks = _attack_results(presented_values, target, attack_restarts)
        if crowded and (not attack_filter or not any(attacks.values())):
            chosen_values = presented_values
            chosen_density = {
                "candidate_triples": len(triples),
                "min_item_degree": min(degrees),
                "max_item_degree": max(degrees),
                "attack_restarts": attack_restarts,
            }
            # Carry the already-sampled witness through the presentation
            # relabelling; no answer is inferred from the completed instance.
            id_map = {f"i{old}": f"i{new}" for old, new in inverse.items()}
            abstract_answer = [
                tuple(sorted((id_map.get(a, a), id_map.get(b, b))))
                for a, b in abstract_answer
            ]
            planted_groups = presented_groups
            break
    if chosen_values is None:
        raise RuntimeError("could not build a crowded attack-resistant instance")

    c_value = 2 * target + 1
    d_value = 2 * target + 2
    m_value = 2 * target + 3

    nodes = ["V", "R"]
    nodes += [f"I{i}" for i in range(item_count)]
    nodes += [f"C{i}" for i in range(item_count)]
    nodes += [f"U{h}" for h in range(2 * n - 1)]
    nodes += [f"S{j}" for j in range(n - 1)]
    nodes += [f"D{j}" for j in range(n - 1)]
    external = {node: 0 for node in nodes}
    for i, value in enumerate(chosen_values):
        external[f"I{i}"] = value
    for j in range(n - 1):
        external[f"S{j}"] = 1

    edges = []
    for i in range(item_count):
        edges.append(_edge(f"i{i}", f"I{i}", "R", c_value))
        edges.append(_edge(f"c{i}", f"C{i}", "V", c_value))
    for h in range(2 * n - 1):
        liability = target if h % 2 == 0 else 1
        edges.append(_edge(f"g{h}", "V", f"U{h}", liability, rank=h))
    for j in range(n):
        edges.append(_edge(f"r{j}", f"U{2*j}", "R", m_value))
    for j in range(n - 1):
        edges.append(_edge(f"p{j}", f"S{j}", f"U{2*j+1}", d_value))
        edges.append(_edge(f"d{j}", f"D{j}", "V", d_value))

    target_creditors = {edge["id"]: edge["creditor"] for edge in edges}
    for i in range(item_count):
        target_creditors[f"i{i}"] = "V"
        target_creditors[f"c{i}"] = "R"
    for j in range(n - 1):
        target_creditors[f"p{j}"] = "V"
        target_creditors[f"d{d_fillers[j]}"] = f"U{2*j+1}"

    answer = [list(pair) for pair in abstract_answer]
    return {
        "family": "semi-positive debt-swap reachability",
        "family_version": FAMILY_VERSION,
        "n": n,
        "nodes": nodes,
        "external_assets": external,
        "edges": edges,
        "target_creditors": target_creditors,
        "target_sum": target,
        "c": c_value,
        "d": d_value,
        "M": m_value,
        "item_values": chosen_values,
        "sequence_length": 4 * n - 1,
        "density": chosen_density,
        "answer": answer,
    }


def render(inst):
    """Render a complete, self-contained solver-facing problem statement."""
    n = inst["n"]
    values = ", ".join(f"{i}:{v}" for i, v in enumerate(inst["item_values"]))
    d_targets = ", ".join(
        f"d{i}->{inst['target_creditors'][f'd{i}']}" for i in range(n - 1)
    )
    return f"""Semi-positive debt-swap reachability

A financial network is a directed multigraph of banks and named debt contracts.
A contract e=(debtor -> creditor, liability L) pays an integer amount between 0
and L.  A bank's total assets are its nonnegative integer external assets plus
all incoming payments.  It pays those assets along its outgoing contracts in
increasing rank order, filling each liability before paying the next.  Unspent
assets are allowed only after all outgoing liabilities are full.  This instance
is acyclic, so its clearing state is obtained exactly by processing debtors
before creditors.  Banks and contracts not assigned external assets have 0.

A debt swap chooses two CURRENT contracts with the same liability.  If their
current endpoints are u1->v1 and u2->v2, then u1,u2,v1,v2 must be four pairwise
distinct banks.  The swap changes them to u1->v2 and u2->v1.  Contract names,
debtors, liabilities, and ranks never change.  A swap is semi-positive when,
comparing exact clearing states immediately before and after it, both old
creditors v1 and v2 have weakly larger total assets and exactly one has strictly
larger total assets.

All indices below are 0-based.  Let q={n}, so there are {3*n} item banks and
2q-1 gate banks.  The complete bank set is:
  V, R;
  I0..I{3*n-1}, C0..C{3*n-1};
  U0..U{2*n-2};
  S0..S{n-2}, D0..D{n-2}.

External assets of item bank Ii are listed as index:value:
  {values}
Every listed item value is strictly between T/4 and T/2; consequently exactly
three item payments, neither fewer nor more, can total T.
Each Sj has external assets 1.  Every other bank has external assets 0.

The complete initial contract set is defined by these inclusive index ranges:
  i<idx>: I<idx> -> R, liability c={inst['c']}, rank 0, for idx=0..{3*n-1}.
  c<idx>: C<idx> -> V, liability c={inst['c']}, rank 0, for idx=0..{3*n-1}.
  g<h>: V -> U<h>, rank h, for h=0..{2*n-2}; its liability is T={inst['target_sum']}
      when h is even and 1 when h is odd.
  r<j>: U(2j) -> R, liability M={inst['M']}, rank 0, for j=0..{n-1}.
  p<j>: S<j> -> U(2j+1), liability d={inst['d']}, rank 0, for j=0..{n-2}.
  d<j>: D<j> -> V, liability d={inst['d']}, rank 0, for j=0..{n-2}.
Here, for example, i7 is the literal contract name "i7", and U(2j+1)
means the bank whose name is obtained by evaluating 2j+1 (for j=2, bank U5).

The target network keeps every debtor, liability, and rank unchanged.  Its
creditors are:
  i<i> -> V and c<i> -> R for every i=0..{3*n-1};
  p<j> -> V for every j=0..{n-2};
  the d-contract targets are: {d_targets};
  every g<h> and r<j> keeps its initial creditor.

Find a sequence of exactly {inst['sequence_length']} semi-positive debt swaps
that transforms the initial network into that target.  A contract may occur in
at most one submitted swap.  Sequence order matters.  Each swap is represented
as a JSON array of its two contract-name strings.  Inside each swap, put the
lexicographically smaller contract name first; repeats are forbidden.

Give your final answer inside <answer></answer> tags, as one JSON array of
exactly {inst['sequence_length']} two-string arrays.
Format example only: <answer>[["c0","i0"],["d0","p0"]]</answer>
Output nothing else inside the tags."""


def _json_array_from_text(text):
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\[", text):
        try:
            value, _ = decoder.raw_decode(text[match.start() :])
        except (ValueError, TypeError):
            continue
        if isinstance(value, list):
            return value
    return None


def parse_answer(text):
    """Extract the tagged JSON witness, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    for block in reversed(blocks):
        cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", block, flags=re.I | re.S)
        try:
            value = json.loads(cleaned)
        except (ValueError, TypeError):
            value = _json_array_from_text(cleaned)
        if isinstance(value, list):
            return value
    # Be liberal for a model that obeys the JSON format but accidentally leaves
    # the tags outside its Markdown fence.
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, re.I | re.S)
    for block in reversed(fenced):
        value = _json_array_from_text(block)
        if isinstance(value, list):
            return value
    return None


def _edge_maps(inst):
    edges = {edge["id"]: edge for edge in inst["edges"]}
    creditors = {edge_id: edge["creditor"] for edge_id, edge in edges.items()}
    return edges, creditors


def _clearing(inst, edges, creditors):
    """Exact clearing for this family's (invariantly acyclic) networks."""
    nodes = list(inst["nodes"])
    indegree = {node: 0 for node in nodes}
    outgoing = defaultdict(list)
    for edge_id, edge in edges.items():
        debtor = edge["debtor"]
        creditor = creditors[edge_id]
        if debtor not in indegree or creditor not in indegree:
            return None, None
        indegree[creditor] += 1
        outgoing[debtor].append(edge_id)
    queue = deque(node for node in nodes if indegree[node] == 0)
    order = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for edge_id in outgoing[node]:
            creditor = creditors[edge_id]
            indegree[creditor] -= 1
            if indegree[creditor] == 0:
                queue.append(creditor)
    if len(order) != len(nodes):
        return None, None

    assets = {node: int(inst["external_assets"].get(node, 0)) for node in nodes}
    payments = {edge_id: 0 for edge_id in edges}
    for node in order:
        available = assets[node]
        ranked = sorted(outgoing[node], key=lambda e: (edges[e]["rank"], e))
        for edge_id in ranked:
            payment = min(available, edges[edge_id]["liability"])
            payments[edge_id] = payment
            available -= payment
            assets[creditors[edge_id]] += payment
    return assets, payments


def _canonical_pairs_shape(inst, answer):
    """Fast exact check for the canonical structure sampled by random_candidate."""
    n = inst["n"]
    item_value = {f"i{i}": value for i, value in enumerate(inst["item_values"])}
    seen_i, seen_c, seen_d = set(), set(), set()
    position = 0
    for stage in range(n):
        total = 0
        for _ in range(3):
            a, b = answer[position]
            position += 1
            pair = {a, b}
            items = [x for x in pair if x.startswith("i") and x[1:].isdigit()]
            fillers = [x for x in pair if x.startswith("c") and x[1:].isdigit()]
            if len(items) != 1 or len(fillers) != 1:
                return None
            item, filler = items[0], fillers[0]
            if item not in item_value or item in seen_i or filler in seen_c:
                return None
            if not (0 <= int(filler[1:]) < 3 * n):
                return None
            seen_i.add(item)
            seen_c.add(filler)
            total += item_value[item]
        if total != inst["target_sum"]:
            return False, f"swap {position} is not semi-positive: its item block does not sum to T"
        if stage < n - 1:
            a, b = answer[position]
            position += 1
            pair = {a, b}
            pulse = f"p{stage}"
            fillers = [x for x in pair if x.startswith("d") and x[1:].isdigit()]
            if pulse not in pair or len(fillers) != 1 or fillers[0] in seen_d:
                return None
            if not (0 <= int(fillers[0][1:]) < n - 1):
                return None
            if inst["target_creditors"].get(fillers[0]) != f"U{2*stage+1}":
                return None
            seen_d.add(fillers[0])
    if len(seen_i) != 3 * n or len(seen_c) != 3 * n or len(seen_d) != n - 1:
        return None
    return True, "ok"


def _verify_replay(inst, answer):
    """Literal clearing-state replay after answer syntax has been validated."""
    edges, creditors = _edge_maps(inst)
    for step, (left, right) in enumerate(answer, 1):
        edge1, edge2 = edges[left], edges[right]
        if edge1["liability"] != edge2["liability"]:
            return False, f"swap {step} uses unequal liabilities"
        u1, u2 = edge1["debtor"], edge2["debtor"]
        v1, v2 = creditors[left], creditors[right]
        if len({u1, u2, v1, v2}) != 4:
            return False, f"swap {step} does not have four distinct endpoint banks"
        before, _ = _clearing(inst, edges, creditors)
        if before is None:
            return False, f"swap {step} starts from a cyclic or malformed network"
        creditors[left], creditors[right] = v2, v1
        after, _ = _clearing(inst, edges, creditors)
        if after is None:
            return False, f"swap {step} creates a cyclic or malformed network"
        weak = after[v1] >= before[v1] and after[v2] >= before[v2]
        strict = (after[v1] > before[v1]) + (after[v2] > before[v2])
        if not weak or strict != 1:
            if after[v1] < before[v1] or after[v2] < before[v2]:
                return False, f"swap {step} is not semi-positive: an old creditor loses assets"
            return False, f"swap {step} is not semi-positive: neither old creditor gains strictly"

    target = inst["target_creditors"]
    if creditors != target:
        wrong = sum(creditors.get(edge_id) != creditor for edge_id, creditor in target.items())
        return False, f"final network differs from target on {wrong} contract(s)"
    return True, "ok"


def verify(inst, answer):
    """Replay and exactly check any submitted reaching sequence."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "sequence is empty"
    expected = int(inst["sequence_length"])
    if len(answer) != expected:
        return False, f"wrong number of swaps: expected {expected}, got {len(answer)}"

    edges, _ = _edge_maps(inst)
    used = set()
    for step, pair in enumerate(answer, 1):
        if not isinstance(pair, list) or len(pair) != 2 or not all(isinstance(x, str) for x in pair):
            return False, f"swap {step} must be a two-string JSON array"
        left, right = pair
        if left == right:
            return False, f"swap {step} repeats an edge"
        if left not in edges or right not in edges:
            return False, f"swap {step} names an unknown edge"
        if pair != sorted(pair):
            return False, f"swap {step} edge names are not in lexicographic order"
        if left in used or right in used:
            return False, f"swap {step} reuses an edge from an earlier swap"
        used.add(left)
        used.add(right)

    fast = _canonical_pairs_shape(inst, answer)
    if fast is not None:
        return fast

    # Noncanonical candidates receive a literal clearing-state replay.  This is
    # needed to accept any valid sequence, not merely the planted normal form.
    return _verify_replay(inst, answer)


def random_candidate(inst, rng):
    """Sample uniformly from the solver-obvious block/pairing candidate space.

    Pulse/filler pairs are fixed because their target creditors reveal them.
    """
    if not hasattr(rng, "shuffle"):
        raise TypeError("rng must provide shuffle")
    n = inst["n"]
    items = [f"i{i}" for i in range(3 * n)]
    c_fillers = [f"c{i}" for i in range(3 * n)]
    d_for_stage = {}
    for i in range(n - 1):
        target = inst["target_creditors"][f"d{i}"]
        stage = (int(target[1:]) - 1) // 2
        d_for_stage[stage] = f"d{i}"
    rng.shuffle(items)
    rng.shuffle(c_fillers)
    answer = []
    position = 0
    for stage in range(n):
        for _ in range(3):
            answer.append(sorted((items[position], c_fillers[position])))
            position += 1
        if stage < n - 1:
            answer.append(sorted((f"p{stage}", d_for_stage[stage])))
    return answer


def search_space(inst):
    """Size of random_candidate's structure-aware candidate space."""
    n = inst["n"]
    k = 3 * n
    return math.factorial(k) * math.factorial(k)


def _count_partitions(values, target, state_cap=2_000_000):
    triples = _valid_triples(values, target)
    by_item = [[] for _ in values]
    for triple in triples:
        mask = sum(1 << i for i in triple)
        for item in triple:
            by_item[item].append(mask)
    all_mask = (1 << len(values)) - 1
    states = 0

    @lru_cache(maxsize=None)
    def visit(mask):
        nonlocal states
        states += 1
        if states > state_cap:
            raise OverflowError
        if mask == all_mask:
            return 1
        first = next(i for i in range(len(values)) if not (mask >> i) & 1)
        count = 0
        for triple_mask in by_item[first]:
            if mask & triple_mask == 0:
                count += visit(mask | triple_mask)
        return count

    return visit(0), states


def enumerate_all(inst):
    """Exact brute-force answer count for small instances; capped otherwise."""
    n = inst["n"]
    if n > 6:
        return None
    try:
        partitions, _ = _count_partitions(inst["item_values"], inst["target_sum"])
    except OverflowError:
        return None
    item_orders = partitions * math.factorial(n) * (math.factorial(3) ** n)
    return item_orders * math.factorial(3 * n)


def canonical_key(inst):
    """Complete invariant for this fixed gadget, ignoring all bank/edge labels."""
    # In this family external assets >1 occur exactly at item banks.  The fixed
    # gadget is determined, up to arbitrary bank/contract relabelling and input
    # ordering, by this multiset.  Pulse sources have external assets exactly 1.
    item_multiset = sorted(
        int(value) for value in inst["external_assets"].values() if int(value) > 1
    )
    payload = {
        "family": "semi-positive-3partition-reach",
        "version": FAMILY_VERSION,
        "n": len(item_multiset) // 3,
        "item_multiset": item_multiset,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params):
    """Increase exact-cover depth while retaining the crowded density regime."""
    current = int(params.get("n", 0))
    if current < 2 or current >= 96:
        return None
    harder = dict(params)
    harder["n"] = max(current + 8, math.ceil(current * 1.30))
    harder["attack_filter"] = True
    return harder


def _relabel_nodes(inst, rng):
    transformed = copy.deepcopy(inst)
    old_nodes = list(transformed["nodes"])
    new_nodes = [f"B{i}" for i in range(len(old_nodes))]
    rng.shuffle(new_nodes)
    mapping = dict(zip(old_nodes, new_nodes))
    transformed["nodes"] = [mapping[node] for node in old_nodes]
    transformed["external_assets"] = {
        mapping[node]: value for node, value in transformed["external_assets"].items()
    }
    for edge in transformed["edges"]:
        edge["debtor"] = mapping[edge["debtor"]]
        edge["creditor"] = mapping[edge["creditor"]]
    transformed["target_creditors"] = {
        edge_id: mapping[creditor]
        for edge_id, creditor in transformed["target_creditors"].items()
    }
    return transformed


def _relabel_edges(inst, rng):
    transformed = copy.deepcopy(inst)
    old_ids = [edge["id"] for edge in transformed["edges"]]
    new_ids = [f"E{i}" for i in range(len(old_ids))]
    rng.shuffle(new_ids)
    mapping = dict(zip(old_ids, new_ids))
    for edge in transformed["edges"]:
        edge["id"] = mapping[edge["id"]]
    transformed["target_creditors"] = {
        mapping[edge_id]: creditor
        for edge_id, creditor in transformed["target_creditors"].items()
    }
    transformed["answer"] = [
        sorted((mapping[left], mapping[right])) for left, right in transformed["answer"]
    ]
    return transformed


def _build_answer_from_groups(inst, groups):
    if not _partition_ok(groups, inst["item_values"], inst["target_sum"]):
        return None
    n = inst["n"]
    d_for_stage = {}
    for d_index in range(n - 1):
        target = inst["target_creditors"][f"d{d_index}"]
        d_for_stage[(int(target[1:]) - 1) // 2] = f"d{d_index}"
    answer = []
    filler = 0
    for stage, group in enumerate(groups):
        for item in group:
            answer.append(sorted((f"i{item}", f"c{filler}")))
            filler += 1
        if stage < n - 1:
            answer.append(sorted((f"p{stage}", d_for_stage[stage])))
    return answer


def selftest():
    """Run gates G1--G8 and return a fully JSON-serializable report."""
    report = {}

    # G1: every named preset, multiple seeds.
    g1_checks = 0
    g1_failures = []
    for preset, preset_params in DIFFICULTY.items():
        for seed in (0, 1, 7, 19):
            inst = make_instance(seed=seed, **preset_params)
            ok, reason = verify(inst, inst["answer"])
            replay_ok, replay_reason = _verify_replay(inst, inst["answer"])
            g1_checks += 2
            if not ok or not replay_ok:
                g1_failures.append(
                    {
                        "preset": preset,
                        "seed": seed,
                        "reason": reason,
                        "literal_replay_reason": replay_reason,
                    }
                )
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping_params)
    planted = copy.deepcopy(inst["answer"])

    # G2: five independently diagnosed corruptions.
    corruptions = {}
    cases = {}
    cases["drop_one"] = planted[:-1]
    swapped = copy.deepcopy(planted)
    swapped[2], swapped[3] = swapped[3], swapped[2]
    cases["swap_one"] = swapped
    duplicate = copy.deepcopy(planted)
    duplicate[0] = [duplicate[0][0], duplicate[0][0]]
    cases["duplicate"] = duplicate
    cases["empty"] = []
    out_of_range = copy.deepcopy(planted)
    out_of_range[0] = sorted(("NO_SUCH_EDGE", out_of_range[0][1]))
    cases["out_of_range"] = out_of_range
    for name, candidate in cases.items():
        ok, reason = verify(inst, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in corruptions.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruptions,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: prose + Markdown + tags, and malformed input.
    realistic = (
        "I found the following reaching sequence.\n\n```json\n<answer>\n"
        + json.dumps(planted)
        + "\n</answer>\n```\nThe checks are complete."
    )
    parsed = parse_answer(realistic)
    garbage_none = parse_answer("No usable witness here: ```not json```") is None
    report["G3_round_trip"] = {
        "pass": parsed == planted and garbage_none,
        "prose_markdown_round_trip": parsed == planted,
        "garbage_returns_none": garbage_none,
    }

    # G4: structure-aware sampling.  Pairing and exact block shape are already
    # enforced; only the hard equal-sum grouping remains random.
    trials = 200_000
    hits = 0
    guess_rng = random.Random(0x230211250)
    for _ in range(trials):
        candidate = random_candidate(inst, guess_rng)
        ok, _ = verify(inst, candidate)
        hits += int(ok)
    probability = hits / trials
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": trials,
        "empirical_probability": probability,
        "sampler": "uniform item order and c-filler bijection; target-forced pulse pairs and fixed 3-item/pulse block shape",
        "structure_aware_space": str(search_space(inst)),
    }

    # G5: exact small enumeration.
    small = make_instance(seed=2718, **DIFFICULTY["demo"])
    exact = enumerate_all(small)
    small_space = search_space(small)
    fraction = None if exact is None else exact / small_space
    report["G5_sparse"] = {
        "pass": exact is not None and fraction < 1e-3,
        "preset": "demo",
        "valid_answers": None if exact is None else str(exact),
        "candidate_space": str(small_space),
        "fraction": fraction,
    }

    # G6: attacks must fail on at least eight unrelated production instances.
    attack_counts = {
        "rank_extremes": {"attempts": 0, "successes": 0},
        "greedy_min_degree": {"attempts": 0, "successes": 0},
        "random_restart": {"attempts": 0, "successes": 0},
    }
    for seed in range(800, 808):
        attacked = make_instance(seed=seed, **shipping_params)
        results = _attack_results(
            attacked["item_values"],
            attacked["target_sum"],
            attacked["density"]["attack_restarts"],
        )
        for name, succeeded in results.items():
            attack_counts[name]["attempts"] += 1
            attack_counts[name]["successes"] += int(succeeded)
    report["G6_adversary_panel"] = {
        "pass": all(v["attempts"] >= 8 and v["successes"] == 0 for v in attack_counts.values()),
        "attacks": attack_counts,
        "note": "success means producing any full equal-sum partition, which converts directly to a verified swap sequence",
    }

    # G7: double the shipping size and confirm construction and G1.
    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * int(shipping_params["n"])
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["sequence_length"] > inst["sequence_length"],
        "base_n": shipping_params["n"],
        "doubled_n": doubled_params["n"],
        "base_swaps": inst["sequence_length"],
        "doubled_swaps": doubled["sequence_length"],
        "doubled_verify_reason": doubled_reason,
    }

    # G8: node renaming, edge renaming, input reordering, and compositions.
    invariance_checks = 0
    carried_witness_checks = 0
    invariant_failures = []
    for seed in range(20):
        base_inst = make_instance(seed=10_000 + seed, **DIFFICULTY["demo"])
        key = canonical_key(base_inst)
        local_rng = random.Random(90_000 + seed)
        variants = []
        node_variant = _relabel_nodes(base_inst, local_rng)
        variants.append(("node_rename", node_variant))
        edge_variant = _relabel_edges(base_inst, local_rng)
        variants.append(("edge_rename", edge_variant))
        reordered = copy.deepcopy(base_inst)
        local_rng.shuffle(reordered["nodes"])
        local_rng.shuffle(reordered["edges"])
        variants.append(("input_reorder", reordered))
        composed = _relabel_edges(_relabel_nodes(base_inst, local_rng), local_rng)
        local_rng.shuffle(composed["nodes"])
        local_rng.shuffle(composed["edges"])
        variants.append(("composed", composed))
        for name, variant in variants:
            invariance_checks += 1
            if canonical_key(variant) != key:
                invariant_failures.append({"seed": seed, "transform": name})
        for variant in (node_variant, edge_variant, composed):
            ok, _ = _verify_replay(variant, variant["answer"])
            carried_witness_checks += 1
            if not ok:
                invariant_failures.append({"seed": seed, "transform": "witness_" + str(carried_witness_checks)})

    distinct_keys = {
        canonical_key(make_instance(seed=20_000 + seed, **DIFFICULTY["demo"]))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and len(distinct_keys) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_witness_checks,
        "distinct_unrelated": len(distinct_keys),
        "unrelated_trials": 20,
        "failures": invariant_failures,
        "transforms": ["arbitrary bank renaming", "arbitrary contract renaming", "input reordering", "all composed"],
    }

    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping_params
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
