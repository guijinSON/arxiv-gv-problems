"""Planted exact-value cycles in finite abelian-group-labelled graphs.

The public graph is a chain of two-way diamond choices closed by one edge.
Every required-length cycle chooses one branch of every diamond, so finding a
cycle of the requested value is a modular subset-sum search.  The module is
standard-library only, deterministic in ``(n, seed, params)``, and silent on
import.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from typing import Any


DIFFICULTY = {
    "demo": {"n": 3, "bits_num": 1, "bits_den": 1, "min_bits": 8},
    "easy": {"n": 96, "bits_num": 1, "bits_den": 1, "min_bits": 24},
    "medium": {"n": 128, "bits_num": 1, "bits_den": 1, "min_bits": 24},
    "hard": {"n": 160, "bits_num": 1, "bits_den": 1, "min_bits": 24},
}
SHIPPING_DIFFICULTY = "easy"

NOTES = r"""
Paper grounding.  Section 2.4 of Gollin--Hendrey--Kawarabayashi--Kwon--Oum,
"A unified half-integral Erdos-Posa theorem for cycles in graphs labelled by
multiple abelian groups", defines an undirected simple Gamma-labelled graph
and defines a subgraph's value as the unoriented sum of its edge labels.
Corollary 1.4 explicitly treats cycles of one specified value in a finite
abelian group.  The witness here is one such cycle, with an additional stated
length requirement; length is itself a group-labelled-cycle property discussed
in Section 1.

Hard/easy boundary.  The paper proves an Erdos-Posa packing/covering theorem,
not a complexity theorem, and contains no polynomial-time, FPT, or closed-form
search algorithm for the exact-value witness.  The shipped group is
Z/(2^b), with b=n.  If b were fixed, the induced modular
subset sum would have an O(n*2^b) dynamic program, so that regime is excluded.
The exact-value request corresponds in Theorem 1.1 to forbidding all other
group elements; thus omega=2^b-1 grows.  This deliberately avoids the
small-forbidden-set choice argument of Section 7 (Lemma 7.4 and Corollary 7.5)
and the theorem supplies no uniform bound in this regime.  Worst-case
NP-hardness follows directly from SUBSET SUM: put branch totals 0 and a_i,
choose a power-of-two modulus larger than their total, and request value T.
This does not prove average-case hardness of the planted distribution.

Inverse generation.  A uniform branch bit is sampled first at every stage.
All four edge labels in every diamond are then sampled independently from the
same uniform distribution; the target is the planted cycle's recomputed sum.
The selected and unselected branches are therefore exchangeable.  Vertex IDs,
edge orientations, edge order, cycle start, and cycle direction are shuffled.
Two pendant marker paths create no cycles; they only make the graph's cheap
canonical form exact and provide an origin and unit for affine label changes.

Attacks.  The outlier attack chooses the numerically smaller branch at every
stage, the greedy attack repeatedly takes the branch closest to the remaining
cyclic residue, random restart performs modular-distance one-flip local
search, and a capped four-list generalized-birthday attack exploits the exact
diamond reduction.  selftest() requires all four to fail on eight
shipping-level seeds.  An earlier n=64, b=48 candidate held against three LLM
vendors but the four-list attack then solved 8/8 calibration seeds in about
0.2 seconds each; that preset was rejected and is absent from DIFFICULTY.
The random-guess gate samples uniformly from the 2^n structurally possible
long cycles, not from arbitrary vertex lists.  canonical_key reconstructs the
rooted diamond chain, sorts the two branches at each stage, and normalises all
labels by the two pendant anchors.  It is invariant under arbitrary vertex
renumbering, edge reordering/orientation, branch swaps, and every affine label
map x -> u*x+t with odd u.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 2_000_000


def _edge(u: int, v: int) -> tuple[int, int]:
    return (u, v) if u < v else (v, u)


def _validate_params(n: int, bits_num: int, bits_den: int,
                     min_bits: int) -> int:
    values = (n, bits_num, bits_den, min_bits)
    if any(isinstance(x, bool) or not isinstance(x, int) for x in values):
        raise ValueError("n and bit-size parameters must be integers")
    if n < 3:
        raise ValueError("n must be at least 3")
    if bits_num < 1 or bits_den < 1:
        raise ValueError("bits_num and bits_den must be positive")
    if min_bits < 8:
        raise ValueError("min_bits must be at least 8")
    bits = max(min_bits, (n * bits_num + bits_den - 1) // bits_den)
    if bits > 4096:
        raise ValueError("the derived modulus is unreasonably large")
    return bits


def _edge_map(inst: dict) -> dict[tuple[int, int], int]:
    cached = inst.get("_edge_labels")
    if isinstance(cached, dict):
        return cached
    out: dict[tuple[int, int], int] = {}
    modulus = inst["modulus"]
    for row in inst.get("edges", []):
        if not isinstance(row, (list, tuple)) or len(row) != 3:
            raise ValueError("malformed edge row")
        u, v, label = row
        key = _edge(u, v)
        if u == v or key in out:
            raise ValueError("graph is not simple")
        out[key] = label % modulus
    return out


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Sample a cycle first, then build and randomly relabel its graph.

    ``n`` is the number of binary diamond stages.  The modulus bit length grows
    linearly with n, so both meet-in-the-middle and residue-DP search scales
    grow exponentially when n grows at fixed bit ratio.
    """
    allowed = {"bits_num", "bits_den", "min_bits"}
    unknown = set(params) - allowed
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    bits_num = params.get("bits_num", 3)
    bits_den = params.get("bits_den", 4)
    min_bits = params.get("min_bits", 24)
    bits = _validate_params(n, bits_num, bits_den, min_bits)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    modulus = 1 << bits

    # G: sample the abstract witness before any problem labels are drawn.
    planted_bits = [rng.randrange(2) for _ in range(n)]

    backbone = list(range(n + 1))
    choices = [(n + 1 + 2 * i, n + 2 + 2 * i) for i in range(n)]
    marker_leaf = 3 * n + 1
    marker_mid = 3 * n + 2
    marker_far = 3 * n + 3
    num_vertices = 3 * n + 4

    template_edges: list[list[int]] = []

    def add(u: int, v: int, label: int | None = None) -> None:
        if label is None:
            label = rng.randrange(modulus)
        template_edges.append([u, v, label % modulus])

    for i, pair in enumerate(choices):
        for choice in pair:
            add(backbone[i], choice)
            add(choice, backbone[i + 1])
    add(backbone[-1], backbone[0])

    # The marker tree lies on no cycle.  Its two distinguished leaf-edge
    # labels differ by an odd unit, enabling exact affine normalisation.
    anchor_zero = rng.randrange(modulus)
    anchor_delta = rng.randrange(modulus) | 1
    add(backbone[0], marker_leaf, anchor_zero)
    add(backbone[0], marker_mid)
    add(marker_mid, marker_far, anchor_zero + anchor_delta)

    labels = {_edge(u, v): label for u, v, label in template_edges}
    planted_template: list[int] = [backbone[0]]
    for i, bit in enumerate(planted_bits):
        planted_template.extend((choices[i][bit], backbone[i + 1]))
    target = 0
    for i, u in enumerate(planted_template):
        v = planted_template[(i + 1) % len(planted_template)]
        target = (target + labels[_edge(u, v)]) % modulus

    # Hide every incidental presentation choice.
    permutation = list(range(num_vertices))
    rng.shuffle(permutation)
    public_edges = []
    for u, v, label in template_edges:
        a, b = permutation[u], permutation[v]
        if rng.randrange(2):
            a, b = b, a
        public_edges.append([a, b, label])
    rng.shuffle(public_edges)

    answer = [permutation[v] for v in planted_template]
    if rng.randrange(2):
        answer.reverse()
    offset = rng.randrange(len(answer))
    answer = answer[offset:] + answer[:offset]

    public_backbone = [permutation[v] for v in backbone]
    public_choices = [tuple(permutation[v] for v in pair) for pair in choices]
    edge_labels = {_edge(u, v): label for u, v, label in public_edges}

    return {
        "family": "exact_value_labelled_cycle",
        "n": n,
        "num_vertices": num_vertices,
        "required_vertices": 2 * n + 1,
        "modulus_bits": bits,
        "modulus": modulus,
        "target": target,
        "edges": public_edges,
        "answer": answer,
        "_edge_labels": edge_labels,
        "_backbone": public_backbone,
        "_choices": public_choices,
    }


def render(inst: dict) -> str:
    """Render a complete, unambiguous problem and exact answer contract."""
    edge_lines = "\n".join(f"{u} {v} {label}" for u, v, label in inst["edges"])
    return f"""Exact-value cycle in an edge-labelled graph

The graph is finite, undirected, and simple.  Its vertices are the integers
0 through {inst['num_vertices'] - 1}.  Every edge has a label in the cyclic
additive group Z/{inst['modulus']}Z.  The value of a cycle is the sum of the
labels of all its edges, reduced modulo {inst['modulus']}; edge traversal
direction does not change a label.

A simple cycle uses distinct vertices and returns from its last listed vertex
to its first.  Find any simple cycle containing exactly
{inst['required_vertices']} distinct vertices whose value is exactly
{inst['target']} modulo {inst['modulus']}.

There are {len(inst['edges'])} edges.  Each following line is
"endpoint endpoint label".  Endpoints are 0-based.  Edge order and endpoint
order carry no meaning.

{edge_lines}

Represent the cycle as a JSON array of exactly {inst['required_vertices']}
distinct vertex IDs in cyclic order.  Do not repeat the first vertex at the
end.  Any starting vertex and either direction are allowed; repeats are not.

Give your final answer inside <answer></answer> tags, as one JSON array of
integers.
Example: <answer>[3, 17, 42]</answer>
Output nothing else inside the tags."""


def parse_answer(text: str) -> object | None:
    """Extract the last well-formed tagged JSON integer array, or return None."""
    if not isinstance(text, str):
        return None
    blocks = _ANSWER_RE.findall(text)
    for body in reversed(blocks):
        body = body.strip()
        if body.startswith("```") and body.endswith("```"):
            lines = body.splitlines()
            if len(lines) >= 3:
                body = "\n".join(lines[1:-1]).strip()
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            continue
        if (isinstance(value, list)
                and all(isinstance(x, int) and not isinstance(x, bool)
                        for x in value)):
            return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid cycle by shape, adjacency, and exact modular sum."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON array of vertex IDs"
    if not answer:
        return False, "cycle list must not be empty"
    if any(isinstance(v, bool) or not isinstance(v, int) for v in answer):
        return False, "every vertex ID must be an integer"
    required = inst["required_vertices"]
    if len(answer) != required:
        return False, f"cycle must list exactly {required} vertices"
    if len(set(answer)) != len(answer):
        return False, "a simple cycle may not repeat a vertex"
    total_vertices = inst["num_vertices"]
    if any(v < 0 or v >= total_vertices for v in answer):
        return False, f"vertex IDs must lie in 0..{total_vertices - 1}"
    try:
        labels = _edge_map(inst)
    except (KeyError, TypeError, ValueError) as exc:
        return False, f"malformed instance: {exc}"
    total = 0
    for i, u in enumerate(answer):
        v = answer[(i + 1) % len(answer)]
        key = _edge(u, v)
        if key not in labels:
            return False, f"consecutive vertices {u} and {v} are not an edge"
        total = (total + labels[key]) % inst["modulus"]
    if total != inst["target"]:
        return False, (f"cycle value is {total} modulo {inst['modulus']}, "
                       f"not target {inst['target']}")
    return True, "ok"


def _adjacency(inst: dict) -> list[list[int]]:
    adj = [[] for _ in range(inst["num_vertices"])]
    for u, v, _ in inst["edges"]:
        adj[u].append(v)
        adj[v].append(u)
    return adj


def _decompose(inst: dict, use_cache: bool = True) -> tuple[
        list[int], list[tuple[int, int]], tuple[int, int],
        tuple[int, int], tuple[int, int]]:
    """Recover backbone, choices, root leaf, far leaf, and root-mid edges."""
    if use_cache and "_backbone" in inst and "_choices" in inst:
        backbone = list(inst["_backbone"])
        choices = [tuple(pair) for pair in inst["_choices"]]
        adj = _adjacency(inst)
        root = backbone[0]
        direct_leaf = next(v for v in adj[root] if len(adj[v]) == 1)
        marker_mid = next(
            v for v in adj[root]
            if len(adj[v]) == 2 and any(len(adj[w]) == 1 for w in adj[v] if w != root)
        )
        far_leaf = next(v for v in adj[marker_mid] if v != root)
        return (backbone, choices, (root, direct_leaf),
                (marker_mid, far_leaf), (root, marker_mid))

    n = inst["n"]
    adj = _adjacency(inst)
    roots = [v for v, row in enumerate(adj) if len(row) == 5]
    if len(roots) != 1:
        raise ValueError("diamond-chain root is not unique")
    root = roots[0]
    direct_leaves = [v for v in adj[root] if len(adj[v]) == 1]
    if len(direct_leaves) != 1:
        raise ValueError("root marker leaf is not unique")
    direct_leaf = direct_leaves[0]
    mids = []
    for v in adj[root]:
        if len(adj[v]) == 2:
            other = next(w for w in adj[v] if w != root)
            if len(adj[other]) == 1:
                mids.append(v)
    if len(mids) != 1:
        raise ValueError("root marker path is not unique")
    marker_mid = mids[0]
    far_leaf = next(v for v in adj[marker_mid] if v != root)

    backbone = [root]
    choices: list[tuple[int, int]] = []
    used_choices: set[int] = set()
    current = root
    for _ in range(n):
        candidates = []
        destinations = []
        for v in adj[current]:
            if v in used_choices or len(adj[v]) != 2 or v == marker_mid:
                continue
            other = next(w for w in adj[v] if w != current)
            if len(adj[other]) >= 3:
                candidates.append(v)
                destinations.append(other)
        if len(candidates) != 2 or destinations[0] != destinations[1]:
            raise ValueError("graph is not the expected diamond chain")
        choices.append(tuple(candidates))
        used_choices.update(candidates)
        current = destinations[0]
        backbone.append(current)
    if _edge(backbone[-1], root) not in _edge_map(inst):
        raise ValueError("diamond chain has no closing edge")
    return (backbone, choices, (root, direct_leaf),
            (marker_mid, far_leaf), (root, marker_mid))


def _cycle_from_bits(inst: dict, bits: list[int]) -> list[int]:
    backbone, choices, _, _, _ = _decompose(inst)
    cycle = [backbone[0]]
    for i, bit in enumerate(bits):
        cycle.extend((choices[i][bit], backbone[i + 1]))
    return cycle


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the 2^n long cycles exposed by the graph structure."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    bits = [rng.randrange(2) for _ in range(inst["n"])]
    cycle = _cycle_from_bits(inst, bits)
    if rng.randrange(2):
        cycle.reverse()
    offset = rng.randrange(len(cycle))
    return cycle[offset:] + cycle[:offset]


def search_space(inst: dict) -> int | None:
    """Number of naive undirected cycles on any required-size vertex subset."""
    total = inst["num_vertices"]
    length = inst["required_vertices"]
    if length < 3 or length > total:
        return 0
    return math.comb(total, length) * math.factorial(length - 1) // 2


def _branch_totals(inst: dict) -> tuple[int, list[tuple[int, int]]]:
    backbone, choices, _, _, _ = _decompose(inst)
    labels = _edge_map(inst)
    modulus = inst["modulus"]
    totals = []
    for i, pair in enumerate(choices):
        row = []
        for choice in pair:
            row.append((labels[_edge(backbone[i], choice)]
                        + labels[_edge(choice, backbone[i + 1])]) % modulus)
        totals.append((row[0], row[1]))
    return labels[_edge(backbone[-1], backbone[0])], totals


def enumerate_all(inst: dict) -> int | None:
    """Count valid cycles up to rotation/reversal when 2^n is capped."""
    count_space = 1 << inst["n"]
    if count_space > _ENUMERATION_CAP:
        return None
    closure, totals = _branch_totals(inst)
    modulus = inst["modulus"]
    current = (closure + sum(row[0] for row in totals)) % modulus
    deltas = [(b - a) % modulus for a, b in totals]
    target = inst["target"]
    hits = 0
    previous_gray = 0
    for index in range(count_space):
        if index:
            gray = index ^ (index >> 1)
            changed = gray ^ previous_gray
            bit = changed.bit_length() - 1
            if gray & changed:
                current = (current + deltas[bit]) % modulus
            else:
                current = (current - deltas[bit]) % modulus
            previous_gray = gray
        if current == target:
            hits += 1
    return hits


def canonical_key(inst: dict) -> str:
    """Exact key for all presentation and affine symmetries of this family."""
    backbone, choices, anchor0, anchor1, root_mid = _decompose(
        inst, use_cache=False)
    labels = _edge_map(inst)
    modulus = inst["modulus"]
    origin = labels[_edge(*anchor0)]
    unit = (labels[_edge(*anchor1)] - origin) % modulus
    if unit % 2 != 1:
        raise ValueError("canonical marker difference is not a unit")
    inverse = pow(unit, -1, modulus)

    def normal(label: int) -> int:
        return ((label - origin) * inverse) % modulus

    stages = []
    for i, pair in enumerate(choices):
        branches = []
        for choice in pair:
            branches.append((
                normal(labels[_edge(backbone[i], choice)]),
                normal(labels[_edge(choice, backbone[i + 1])]),
            ))
        stages.append(sorted(branches))
    length = inst["required_vertices"]
    target = ((inst["target"] - length * origin) * inverse) % modulus
    form = [
        inst["n"], inst["modulus_bits"],
        normal(labels[_edge(*root_mid)]),
        normal(labels[_edge(backbone[-1], backbone[0])]),
        target, stages,
    ]
    payload = json.dumps(form, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase stages while preserving the n/modulus-bit density."""
    if "n" not in params:
        return None
    n = params["n"]
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        return None
    out = dict(params)
    out["n"] = n + max(16, n // 2)
    if out["n"] > 512:
        return None
    return out


def _cyclic_distance(value: int, target: int, modulus: int) -> int:
    d = (value - target) % modulus
    return min(d, modulus - d)


def _outlier_attack(inst: dict) -> list[int]:
    """Use only per-branch numeric magnitude and public vertex ID."""
    _, totals = _branch_totals(inst)
    _, choices, _, _, _ = _decompose(inst)
    bits = []
    for pair, row in zip(choices, totals):
        bits.append(min(range(2), key=lambda j: (row[j], pair[j])))
    return _cycle_from_bits(inst, bits)


def _greedy_attack(inst: dict) -> list[int]:
    """Take the branch apparently closest to the remaining target residue."""
    closure, totals = _branch_totals(inst)
    modulus = inst["modulus"]
    running = closure
    bits = []
    for row in totals:
        bit = min(range(2), key=lambda j: _cyclic_distance(
            (running + row[j]) % modulus, inst["target"], modulus))
        bits.append(bit)
        running = (running + row[bit]) % modulus
    return _cycle_from_bits(inst, bits)


def _random_restart_attack(inst: dict, rng: random.Random,
                           restarts: int = 64, steps: int = 256) -> list[int]:
    """One-flip modular-distance local search from random starts."""
    closure, totals = _branch_totals(inst)
    modulus = inst["modulus"]
    target = inst["target"]
    deltas = [(b - a) % modulus for a, b in totals]
    baseline = (closure + sum(a for a, _ in totals)) % modulus
    last = [0] * len(totals)
    for _ in range(restarts):
        bits = [rng.randrange(2) for _ in totals]
        current = (baseline + sum(delta for bit, delta in zip(bits, deltas)
                                  if bit)) % modulus
        for _ in range(steps):
            if current == target:
                return _cycle_from_bits(inst, bits)
            current_score = _cyclic_distance(current, target, modulus)
            candidates = []
            for i, delta in enumerate(deltas):
                trial = ((current - delta) if bits[i] else (current + delta)) % modulus
                candidates.append((_cyclic_distance(trial, target, modulus), i, trial))
            best_score = min(row[0] for row in candidates)
            pool = [row for row in candidates if row[0] == best_score]
            if best_score < current_score:
                _, index, trial = rng.choice(pool)
            else:
                index = rng.randrange(len(bits))
                delta = deltas[index]
                trial = ((current - delta) if bits[index]
                         else (current + delta)) % modulus
            bits[index] ^= 1
            current = trial
        last = bits
    return _cycle_from_bits(inst, last)


def _subset_sum_samples(deltas: list[int], modulus: int,
                        rng: random.Random,
                        sample_cap: int = 16_384) -> list[tuple[int, int]]:
    """Enumerate a 16-variable group, or sample a capped larger group."""
    if len(deltas) <= 16:
        rows = [(0, 0)]
        for index, delta in enumerate(deltas):
            rows += [((value + delta) % modulus, mask | (1 << index))
                     for value, mask in rows]
        return rows
    total = 1 << len(deltas)
    rows = []
    for mask in rng.sample(range(total), min(sample_cap, total)):
        value = 0
        remaining = mask
        while remaining:
            low = remaining & -remaining
            value += deltas[low.bit_length() - 1]
            remaining ^= low
        rows.append((value % modulus, mask))
    return rows


def _four_list_birthday_attack(inst: dict, rng: random.Random,
                               offset_trials: int = 12) -> list[int]:
    """Capped Wagner-style four-list attack on the modular subset sum.

    Four complete 16-variable lists make the discarded n=64,b=48 setting
    trivial.  At the shipped density-one setting, each 24-variable list is
    capped at 16,384 sampled subsets, keeping this a genuinely cheap attack.
    """
    n = inst["n"]
    if n % 4:
        return _cycle_from_bits(inst, [0] * n)
    closure, totals = _branch_totals(inst)
    modulus = inst["modulus"]
    modulus_bits = inst["modulus_bits"]
    group_size = n // 4
    deltas = [(b - a) % modulus for a, b in totals]
    baseline = (closure + sum(a for a, _ in totals)) % modulus
    desired = (inst["target"] - baseline) % modulus
    groups = [
        _subset_sum_samples(
            deltas[i * group_size:(i + 1) * group_size], modulus, rng)
        for i in range(4)
    ]

    low_bits = max(1, modulus_bits // 3)
    low_modulus = 1 << low_bits
    low_mask = low_modulus - 1
    high_modulus = 1 << (modulus_bits - low_bits)
    buckets = []
    for group in groups:
        table: dict[int, list[tuple[int, int]]] = {}
        for value, mask in group:
            table.setdefault(value & low_mask, []).append((value, mask))
        buckets.append(table)

    offsets = [0]
    offsets.extend(rng.randrange(low_modulus) for _ in range(offset_trials - 1))
    desired_low = desired & low_mask
    desired_high = desired >> low_bits
    for offset in offsets:
        left = []
        for value0, mask0 in groups[0]:
            needed = (offset - value0) & low_mask
            for value1, mask1 in buckets[1].get(needed, ()):
                pair = (value0 + value1) % modulus
                left.append((pair >> low_bits, mask0, mask1))

        right_low = (desired - offset) & low_mask
        carry = (offset + right_low - desired_low) // low_modulus
        right: dict[int, tuple[int, int]] = {}
        for value2, mask2 in groups[2]:
            needed = (right_low - value2) & low_mask
            for value3, mask3 in buckets[3].get(needed, ()):
                pair = (value2 + value3) % modulus
                right.setdefault(pair >> low_bits, (mask2, mask3))

        for high, mask0, mask1 in left:
            needed = (desired_high - carry - high) % high_modulus
            if needed not in right:
                continue
            mask2, mask3 = right[needed]
            bits = []
            for mask in (mask0, mask1, mask2, mask3):
                bits.extend((mask >> i) & 1 for i in range(group_size))
            candidate = _cycle_from_bits(inst, bits)
            if verify(inst, candidate)[0]:
                return candidate
    return _cycle_from_bits(inst, [0] * n)


def _transformed_instance(inst: dict, vertex_permutation: list[int] | None = None,
                          unit: int = 1, translation: int = 0,
                          reorder_seed: int | None = None) -> dict:
    """Carry an instance and its answer through a tested true symmetry."""
    total = inst["num_vertices"]
    if vertex_permutation is None:
        vertex_permutation = list(range(total))
    modulus = inst["modulus"]
    if unit % 2 != 1:
        raise ValueError("unit must be odd modulo a power of two")
    edges = []
    for u, v, label in inst["edges"]:
        edges.append([
            vertex_permutation[u], vertex_permutation[v],
            (unit * label + translation) % modulus,
        ])
    if reorder_seed is not None:
        rng = random.Random(reorder_seed)
        for row in edges:
            if rng.randrange(2):
                row[0], row[1] = row[1], row[0]
        rng.shuffle(edges)
    return {
        "family": inst["family"],
        "n": inst["n"],
        "num_vertices": total,
        "required_vertices": inst["required_vertices"],
        "modulus_bits": inst["modulus_bits"],
        "modulus": modulus,
        "target": (unit * inst["target"]
                   + inst["required_vertices"] * translation) % modulus,
        "edges": edges,
        "answer": [vertex_permutation[v] for v in inst["answer"]],
    }


def selftest() -> dict:
    """Run gates G1--G8 and return their measured evidence."""
    report: dict[str, Any] = {}

    checked = 0
    for name, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 99):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            assert ok, (name, seed, why)
            checked += 1
    report["G1_planted_verifies"] = {"pass": True, "instances": checked}

    ship = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260902, **ship)
    planted = inst["answer"]
    corruptions = {
        "empty": [],
        "drop_one": planted[:-1],
        "duplicate": [planted[0], planted[0]] + planted[2:],
        "out_of_range": [inst["num_vertices"]] + planted[1:],
    }
    swapped = None
    for i in range(len(planted)):
        trial = planted[:]
        j = (i + 1) % len(trial)
        trial[i], trial[j] = trial[j], trial[i]
        ok, why = verify(inst, trial)
        if not ok and "are not an edge" in why:
            swapped = trial
            break
    assert swapped is not None
    corruptions["swap_adjacent"] = swapped
    reasons = {}
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        assert not ok, name
        reasons[name] = why
    assert len(set(reasons.values())) == len(reasons), reasons
    report["G2_rejects_corruption"] = {"pass": True, "reasons": reasons}

    response = ("I found a cycle and checked its residue.\n```json\n<answer>"
                + json.dumps(planted)
                + "</answer>\n```\nThe first vertex is not repeated.")
    assert parse_answer(response) == planted
    assert parse_answer("no tagged answer here") is None
    assert parse_answer("<answer>[1, nope]</answer>") is None
    report["G3_round_trip"] = {"pass": True, "vertices": len(planted)}

    guess_inst = make_instance(seed=8675309, **ship)
    guess_rng = random.Random(13579)
    total_guesses = 200_000
    hits = 0
    for _ in range(total_guesses):
        if verify(guess_inst, random_candidate(guess_inst, guess_rng))[0]:
            hits += 1
    probability = hits / total_guesses
    assert probability < 1e-6, (hits, total_guesses)
    report["G4_guess_resistance"] = {
        "pass": True,
        "hits": hits,
        "total": total_guesses,
        "empirical_probability": probability,
        "prior": "uniform over the 2^n structurally possible long cycles",
        "structure_aware_space": 1 << guess_inst["n"],
        "naive_cycle_space": search_space(guess_inst),
    }

    sparse_rows = []
    for seed in (2, 3, 5):
        small = make_instance(n=20, seed=seed, bits_num=3, bits_den=4,
                              min_bits=24)
        solutions = enumerate_all(small)
        naive = search_space(small)
        structured = 1 << small["n"]
        assert solutions is not None and solutions >= 1
        structured_fraction = solutions / structured
        naive_fraction = solutions / naive
        assert structured_fraction < 1e-4
        sparse_rows.append({
            "seed": seed,
            "solutions": solutions,
            "structure_aware_space": structured,
            "structure_aware_fraction": structured_fraction,
            "naive_cycle_space": naive,
            "naive_fraction": naive_fraction,
        })
    report["G5_sparse"] = {"pass": True, "instances": sparse_rows}

    attack_seeds = list(range(3100, 3108))
    attacks = {
        "per_branch_numeric_outlier": {"solved": 0, "trials": len(attack_seeds)},
        "deterministic_residual_greedy": {"solved": 0, "trials": len(attack_seeds)},
        "random_restart_one_flip_64x256": {"solved": 0, "trials": len(attack_seeds)},
        "capped_four_list_birthday": {"solved": 0, "trials": len(attack_seeds)},
    }
    for seed in attack_seeds:
        target_inst = make_instance(seed=seed, **ship)
        if verify(target_inst, _outlier_attack(target_inst))[0]:
            attacks["per_branch_numeric_outlier"]["solved"] += 1
        if verify(target_inst, _greedy_attack(target_inst))[0]:
            attacks["deterministic_residual_greedy"]["solved"] += 1
        attack_rng = random.Random(seed ^ 0x5A17)
        candidate = _random_restart_attack(target_inst, attack_rng, 64, 256)
        if verify(target_inst, candidate)[0]:
            attacks["random_restart_one_flip_64x256"]["solved"] += 1
        birthday_rng = random.Random(seed ^ 0xB17D4A)
        candidate = _four_list_birthday_attack(target_inst, birthday_rng)
        if verify(target_inst, candidate)[0]:
            attacks["capped_four_list_birthday"]["solved"] += 1
    assert all(row["solved"] == 0 for row in attacks.values()), attacks

    rejected_solved = 0
    for seed in attack_seeds:
        rejected = make_instance(n=64, seed=seed, bits_num=3, bits_den=4,
                                 min_bits=24)
        birthday_rng = random.Random(seed ^ 0xB17D4A)
        candidate = _four_list_birthday_attack(rejected, birthday_rng)
        if verify(rejected, candidate)[0]:
            rejected_solved += 1
    assert rejected_solved == len(attack_seeds), rejected_solved
    report["G6_adversary_panel"] = {
        "pass": True,
        "attacks": attacks,
        "rejected_calibration": {
            "params": {"n": 64, "modulus_bits": 48},
            "four_list_birthday_solved": rejected_solved,
            "trials": len(attack_seeds),
        },
    }

    doubled_params = dict(ship)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=424242, **doubled_params)
    ok, why = verify(doubled, doubled["answer"])
    assert ok, why
    assert doubled["modulus_bits"] > inst["modulus_bits"]
    assert (1 << doubled["n"]) > (1 << inst["n"])
    report["G7_scales"] = {
        "pass": True,
        "base_n": inst["n"],
        "base_modulus_bits": inst["modulus_bits"],
        "doubled_n": doubled["n"],
        "doubled_modulus_bits": doubled["modulus_bits"],
        "planted_verifies": True,
    }

    invariance_checks = 0
    real_transform_checks = 0
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(n=10, seed=9000 + seed, min_bits=16)
        key = canonical_key(base)
        unrelated_keys.append(key)
        rng = random.Random(700_000 + seed)
        permutation = list(range(base["num_vertices"]))
        rng.shuffle(permutation)
        unit = rng.randrange(base["modulus"]) | 1
        translation = rng.randrange(base["modulus"])
        transforms = [
            _transformed_instance(base, reorder_seed=10 + seed),
            _transformed_instance(base, vertex_permutation=permutation),
            _transformed_instance(base, unit=unit, translation=translation),
            _transformed_instance(base, vertex_permutation=permutation,
                                  unit=unit, translation=translation,
                                  reorder_seed=20 + seed),
        ]
        for transformed in transforms:
            assert canonical_key(transformed) == key
            invariance_checks += 1
            ok, why = verify(transformed, transformed["answer"])
            assert ok, (seed, why)
            real_transform_checks += 1
        # Reordering and affine relabelling leave vertex IDs unchanged, so the
        # original untransformed witness itself must still work.
        ok, why = verify(transforms[2], base["answer"])
        assert ok, (seed, why)
    distinct = len(set(unrelated_keys))
    assert distinct == len(unrelated_keys)
    report["G8_canonical_key"] = {
        "pass": True,
        "invariance_checks": invariance_checks,
        "real_transform_checks": real_transform_checks,
        "original_answer_transform_checks": 20,
        "distinct_unrelated": distinct,
        "unrelated_total": len(unrelated_keys),
        "symmetries": ("vertex renumbering, edge order/orientation, per-stage "
                       "branch swap, affine x->u*x+t for odd u, and compositions"),
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for name, value in report.items() if name.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2))
