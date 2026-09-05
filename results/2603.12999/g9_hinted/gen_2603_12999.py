"""Verified Track-B generator for bounded two-way partition.

Bringmann, Duerr, and Wegrzycki (arXiv:2603.12999) study k-Bin
Packing and equivalent k-way Partition variants.  Their lower-bound gadgets
encode consistency in carry-free blocks of integer digits.  This module keeps
the paper's native integer-partition object and uses the same broad idea in an
inverse-generated promised subfamily: after a hidden common block mask is
removed, the item digits are the incidence vectors of a bipartite tree.

The planted witness is sampled first.  A generic exact meet-in-the-middle
algorithm still solves every generated instance and is measured explicitly;
the benchmark claim is only Track B no-tool compression.
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


sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # The family only needs exact Python integers.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "optimization",
    "object_regime": "finite_discrete",
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "a set of near-equal positive integer item sizes",
        "two identical-capacity bins",
        "an equal-sum partition of the item indices",
    ],
    "verification_operations": [
        "integer index range and disjointness checks",
        "exact integer addition",
        "exact comparison with both bin capacities",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Equal-width decimal blocks share a removable column mask, after which "
        "the residual incidence constraints can be propagated; without that "
        "change of variables one faces balanced subset sum."
    ),
    "hardness_basis": (
        "Track B: exact balanced meet-in-the-middle subset sum runs in "
        "O(2^(n/2)) time and space; at shipping n=38 it averaged 668,750 "
        "states, 2,295,171 counted operations, and 4.16 seconds over eight "
        "builder-host seeds, while the masked-block route takes at most 187 "
        "exact operations."
    ),
    "max_answer_tokens": 28,
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
    "demo": {"n": 6, "block_width": 2},
    "easy": {"n": 38, "block_width": 3},
    "medium": {"n": 40, "block_width": 4},
    "hard": {"n": 42, "block_width": 5},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Read the decimal expansions in equal-width blocks: removing each "
    "column's common mask exposes an incidence invariant."
)
PLACEBO_HINT = (
    "Read the integer list with consistent care: checking each candidate's "
    "two bin totals avoids bookkeeping mistakes."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "An ordered JSON pair [bin_0, bin_1] of index lists; every 0-based "
        "item index occurs exactly once, each inner list has n/2 distinct "
        "indices, and indices inside each bin are in increasing order."
    ),
    "bounds": {
        "bins": 2,
        "indices": "0..n-1",
        "items_per_bin": "n/2",
        "candidate_count": "binomial(n,n/2)",
    },
}

NOTES = (
    "Appendix A defines Bounded k-way Partition on a set of near-equal "
    "positive integers, Observation 3.4 proves that every equal-load part has "
    "the same cardinality, and Theorem 8.1 makes this variant "
    "parameter-preserving equivalent to k-Bin Packing and P_k||C_max.  "
    "Section 2.1 supplies the paper's carry-free bit-block communication idea. "
    "Theorem 1.1 is worst-case ETH hardness, not a distributional theorem, and "
    "Sections 1.1 and 9 explicitly record pseudopolynomial and exponential "
    "algorithms; therefore this promised inverse-generated distribution is "
    "honestly Track B.  The answer bipartition is sampled before a connected "
    "bipartite tree is assembled across it, so generation never solves the "
    "instance.  A random column mask, digit-column permutation, item "
    "permutation, and near-equal common offset hide the incidence witness.  "
    "Magnitude outliers, balanced greedy, sorted alternation, low-block parity, "
    "and random restarts are tested; all items undergo the same masking law, so "
    "there is no separately distributed planted item.  The exact generic "
    "meet-in-the-middle solver is disclosed and measured as the Track B "
    "reference algorithm."
)

_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 100_000
_REFERENCE_SEEDS = tuple(range(8100, 8108))

# Filled from the three script-owned hardening runs at the shipping preset.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}


def _require_int(name, value, minimum):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer at least {minimum}")


def _make_balanced_bipartite_tree(n, rng):
    """Make a tree after choosing its balanced colour classes first."""
    half = n // 2
    left = list(range(half))
    right = list(range(half, n))
    rng.shuffle(left)
    rng.shuffle(right)

    present_left = [left.pop()]
    present_right = [right.pop()]
    edges = [(present_left[0], present_right[0])]
    remainder = [(0, v) for v in left] + [(1, v) for v in right]
    rng.shuffle(remainder)
    for colour, vertex in remainder:
        if colour == 0:
            parent = rng.choice(present_right)
            present_left.append(vertex)
        else:
            parent = rng.choice(present_left)
            present_right.append(vertex)
        edges.append((vertex, parent))
    return edges, (set(range(half)), set(range(half, n)))


def _encode_low_blocks(digits, base):
    value = 0
    place = 1
    for digit in digits:
        value += digit * place
        place *= base
    return value


def _low_blocks(value, base, count):
    out = []
    for _ in range(count):
        value, digit = divmod(value, base)
        out.append(digit)
    return out


def make_instance(n, seed=0, **params):
    """Inverse-generate a certified bounded two-way Partition instance.

    The answer bipartition is fixed first.  A connected tree is then built using
    only cross-part edges.  Its incidence columns are hidden by common random
    base-10^w column masks and a common high offset.  No partition search is
    performed during generation.
    """
    block_width = params.pop("block_width", 3)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _require_int("n", n, 6)
    _require_int("block_width", block_width, 2)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    if n % 2:
        n += 1
    if n > 240:
        raise ValueError("n may not exceed 240 (the certificate atom cap)")

    rng = random.Random(seed)
    base = 10 ** block_width
    if base <= 4 * n:
        raise ValueError("block_width is too small for carry-free masking")

    edges, colours = _make_balanced_bipartite_tree(n, rng)
    rng.shuffle(edges)  # A relabelling of the digit coordinates.
    d = len(edges)

    lo = max(2, base // (5 * n))
    hi = max(lo, base // (3 * n))
    baselines = [rng.randint(lo, hi) for _ in range(d)]
    incidence = [[0] * d for _ in range(n)]
    for column, (u, v) in enumerate(edges):
        incidence[u][column] = 1
        incidence[v][column] = 1

    # The shared high coefficient makes every number lie in the exact bounded
    # range from Appendix A.  Lower blocks remain carry-free in every bin.
    common_coefficient = n ** 10 + rng.randrange(0, n ** 3)
    high_place = base ** d
    common_low = _encode_low_blocks(baselines, base)
    common = common_coefficient * high_place + common_low
    values = [
        common + _encode_low_blocks(incidence[v], base) for v in range(n)
    ]

    order = list(range(n))
    rng.shuffle(order)
    inverse = {old: new for new, old in enumerate(order)}
    items = [values[old] for old in order]
    answer = [
        sorted(inverse[v] for v in colours[0]),
        sorted(inverse[v] for v in colours[1]),
    ]
    capacity = sum(items[i] for i in answer[0])
    if capacity != sum(items[i] for i in answer[1]):
        raise AssertionError("inverse construction failed to balance the bins")

    bounded_w = max(items)
    if min(items) * (n ** 10) < bounded_w * (n ** 10 - 1):
        raise AssertionError("items do not satisfy the promised bounded range")
    if len(set(items)) != n:
        raise AssertionError("the construction must produce a set, not a multiset")

    return {
        "paper": "arXiv:2603.12999",
        "family": "masked_incidence_bounded_two_way_partition",
        "n": n,
        "seed": seed,
        "block_width": block_width,
        "block_base": base,
        "blocks": d,
        "bounded_W": bounded_w,
        "items": items,
        "capacity": capacity,
        "answer": answer,
    }


def render(inst):
    """Render the complete native bounded-partition witness problem."""
    n = inst["n"]
    half = n // 2
    lines = [
        "Bounded two-way integer partition",
        "",
        "You are given a set of distinct positive integer item sizes and two",
        "identical bins.  A partition assigns every item to exactly one bin.",
        "The load of a bin is the exact sum of its assigned item sizes.",
        "",
        f"There are {n} items, indexed 0 through {n - 1}.  Each bin has capacity",
        f"T = {inst['capacity']}.  The listed sizes have total 2T.  They also lie",
        f"in the inclusive interval [W*(1-1/n^10), W] with W = {inst['bounded_W']}.",
        "Consequently a valid equal-load partition has exactly n/2 items per bin;",
        f"your answer must explicitly put exactly {half} indices in each bin.",
        "Bins are labelled 0 and 1, but swapping the two whole bins is accepted.",
        "Indices within each bin must be strictly increasing.  Repeats and",
        "omissions are not",
        "allowed, and all arithmetic is over ordinary decimal integers.",
        "",
        "ITEM SIZES (0-based index: decimal size):",
    ]
    lines.extend(f"{i}: {value}" for i, value in enumerate(inst["items"]))
    lines.extend(
        [
            "",
            "Return a JSON array [bin_0, bin_1], where each bin is a JSON array",
            f"of exactly {half} distinct 0-based integer indices.  Together the",
            f"two arrays must contain every index 0 through {n - 1} exactly once.",
            "Give your final answer inside <answer></answer> tags, in that exact format.",
            "Example syntax only: <answer>[[0,2,5],[1,3,4]]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Extract the last tagged JSON witness, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body).strip()
    try:
        return json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def verify(inst, answer):
    """Check any valid partition using only instance data and exact sums."""
    n = inst["n"]
    if answer == []:
        return False, "empty answer: expected an ordered pair of nonempty bins"
    if not isinstance(answer, list) or len(answer) != 2:
        return False, "malformed shape: expected exactly two JSON index arrays"
    if not all(isinstance(part, list) for part in answer):
        return False, "malformed bins: each bin must be a JSON array"
    flat = answer[0] + answer[1]
    if any(isinstance(i, bool) or not isinstance(i, int) for i in flat):
        return False, "malformed index: every item index must be an integer"
    bad = next((i for i in flat if i < 0 or i >= n), None)
    if bad is not None:
        return False, f"out of range: item index {bad} is not in 0..{n - 1}"
    if len(set(flat)) != len(flat):
        return False, "duplicate index: every item may occur only once"
    present = set(flat)
    if present != set(range(n)):
        missing = sorted(set(range(n)) - present)
        return False, f"missing items: expected every index, absent {missing[:5]}"
    half = n // 2
    if len(answer[0]) != half or len(answer[1]) != half:
        return False, f"wrong cardinality: each bin must contain exactly {half} items"
    if any(part != sorted(part) for part in answer):
        return False, "wrong order: indices within each bin must be strictly increasing"
    sums = [sum(inst["items"][i] for i in part) for part in answer]
    if sums[0] != inst["capacity"] or sums[1] != inst["capacity"]:
        return False, "capacity mismatch: the two exact loads are not both T"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the balanced-partition language, not all 2^n labels."""
    n = inst["n"]
    chosen = set(rng.sample(range(n), n // 2))
    return [sorted(chosen), [i for i in range(n) if i not in chosen]]


def search_space(inst):
    return math.comb(inst["n"], inst["n"] // 2)


def enumerate_all(inst):
    """Brute-force the declared ordered language when it is genuinely small."""
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    n = inst["n"]
    count = 0
    for first in itertools.combinations(range(n), n // 2):
        chosen = set(first)
        candidate = [list(first), [i for i in range(n) if i not in chosen]]
        if verify(inst, candidate)[0]:
            count += 1
    return count


def _decode_tree(inst):
    """Recover the residual incidence tree from the public integer data."""
    n = inst["n"]
    base = inst["block_base"]
    d = inst["blocks"]
    rows = [_low_blocks(value, base, d) for value in inst["items"]]
    edges = []
    for column in range(d):
        values = [row[column] for row in rows]
        baseline = min(values)
        endpoints = [i for i, value in enumerate(values) if value == baseline + 1]
        if len(endpoints) != 2 or any(
            value not in (baseline, baseline + 1) for value in values
        ):
            raise ValueError("item blocks do not encode a two-endpoint incidence column")
        edges.append(tuple(endpoints))
    if len(edges) != n - 1:
        raise ValueError("incidence object is not a tree-sized graph")
    return edges


def _tree_code(n, edges):
    adjacency = [[] for _ in range(n)]
    for u, v in edges:
        adjacency[u].append(v)
        adjacency[v].append(u)
    if any(not row for row in adjacency):
        raise ValueError("decoded incidence graph is disconnected")

    degrees = [len(row) for row in adjacency]
    leaves = [i for i, degree in enumerate(degrees) if degree <= 1]
    removed = len(leaves)
    while removed < n:
        new_leaves = []
        for leaf in leaves:
            for neighbour in adjacency[leaf]:
                degrees[neighbour] -= 1
                if degrees[neighbour] == 1:
                    new_leaves.append(neighbour)
        if removed + len(new_leaves) >= n:
            leaves = new_leaves
            break
        removed += len(new_leaves)
        leaves = new_leaves
    centers = leaves
    if not centers or len(centers) > 2:
        raise ValueError("decoded incidence graph is not a connected tree")

    def rooted(vertex, parent):
        children = [
            rooted(neighbour, vertex)
            for neighbour in adjacency[vertex]
            if neighbour != parent
        ]
        return "(" + "".join(sorted(children)) + ")"

    return min(rooted(center, -1) for center in centers)


def canonical_key(inst):
    """Canonicalise item, block, bin, and tree-vertex relabellings."""
    code = _tree_code(inst["n"], _decode_tree(inst))
    return hashlib.sha256(f"tree:{inst['n']}:{code}".encode()).hexdigest()


def _partition_from_first(n, first):
    chosen = set(first)
    return [sorted(chosen), [i for i in range(n) if i not in chosen]]


def _attack_largest_half(inst):
    ranked = sorted(range(inst["n"]), key=lambda i: inst["items"][i], reverse=True)
    return _partition_from_first(inst["n"], ranked[: inst["n"] // 2])


def _attack_sorted_alternation(inst):
    ranked = sorted(range(inst["n"]), key=lambda i: inst["items"][i], reverse=True)
    return _partition_from_first(inst["n"], ranked[::2])


def _attack_low_block_parity(inst):
    ranked = sorted(
        range(inst["n"]),
        key=lambda i: (inst["items"][i] % inst["block_base"] & 1, inst["items"][i]),
    )
    return _partition_from_first(inst["n"], ranked[: inst["n"] // 2])


def _attack_balanced_greedy(inst):
    n = inst["n"]
    limit = n // 2
    bins = [[], []]
    loads = [0, 0]
    for index in sorted(range(n), key=lambda i: inst["items"][i], reverse=True):
        if len(bins[0]) == limit:
            target = 1
        elif len(bins[1]) == limit:
            target = 0
        else:
            target = 0 if loads[0] <= loads[1] else 1
        bins[target].append(index)
        loads[target] += inst["items"][index]
    return [sorted(bins[0]), sorted(bins[1])]


def _mitm_balanced_partition(inst):
    """Generic exact meet-in-the-middle solver with measured state cost."""
    values = inst["items"]
    n = len(values)
    split = n // 2
    left = values[:split]
    right = values[split:]
    need_count = n // 2
    target = inst["capacity"]
    tables = [dict() for _ in range(len(left) + 1)]

    total = 0
    count = 0
    previous = 0
    states = 0
    operations = 0
    for step in range(1 << len(left)):
        gray = step ^ (step >> 1)
        if step:
            changed = gray ^ previous
            bit = (changed & -changed).bit_length() - 1
            if gray & changed:
                total += left[bit]
                count += 1
            else:
                total -= left[bit]
                count -= 1
            operations += 2
        tables[count].setdefault(total, gray)
        states += 1
        operations += 1
        previous = gray

    total = 0
    count = 0
    previous = 0
    found = None
    for step in range(1 << len(right)):
        gray = step ^ (step >> 1)
        if step:
            changed = gray ^ previous
            bit = (changed & -changed).bit_length() - 1
            if gray & changed:
                total += right[bit]
                count += 1
            else:
                total -= right[bit]
                count -= 1
            operations += 2
        other_count = need_count - count
        other_sum = target - total
        operations += 2
        states += 1
        if 0 <= other_count < len(tables):
            left_mask = tables[other_count].get(other_sum)
            operations += 1
            if left_mask is not None:
                selected = [i for i in range(split) if left_mask >> i & 1]
                selected.extend(
                    split + i for i in range(len(right)) if gray >> i & 1
                )
                found = _partition_from_first(n, selected)
                break
        previous = gray
    return found, {"states": states, "operations": operations}


def _reorder_instance(inst, new_to_old):
    n = inst["n"]
    if sorted(new_to_old) != list(range(n)):
        raise ValueError("not an item permutation")
    old_to_new = {old: new for new, old in enumerate(new_to_old)}
    out = dict(inst)
    out["items"] = [inst["items"][old] for old in new_to_old]
    out["answer"] = [
        sorted(old_to_new[old] for old in part) for part in inst["answer"]
    ]
    out["bounded_W"] = max(out["items"])
    return out


def _permute_blocks(inst, new_to_old):
    d = inst["blocks"]
    if sorted(new_to_old) != list(range(d)):
        raise ValueError("not a digit-block permutation")
    base = inst["block_base"]
    high_place = base ** d

    def transform(value):
        high, low = divmod(value, high_place)
        digits = _low_blocks(low, base, d)
        return high * high_place + _encode_low_blocks(
            [digits[old] for old in new_to_old], base
        )

    out = dict(inst)
    out["items"] = [transform(value) for value in inst["items"]]
    out["capacity"] = transform(inst["capacity"])
    out["bounded_W"] = max(out["items"])
    return out


def _shift_common_high_block(inst, amount):
    out = dict(inst)
    delta = amount * (inst["block_base"] ** inst["blocks"])
    out["items"] = [value + delta for value in inst["items"]]
    out["capacity"] = inst["capacity"] + (inst["n"] // 2) * delta
    out["bounded_W"] = max(out["items"])
    return out


def escalate(params):
    """Raise both search entropy and coefficient range while under answer caps."""
    clean = {k: v for k, v in params.items() if k != "_preset"}
    n = int(clean.get("n", 38))
    width = int(clean.get("block_width", 3))
    if n + 2 > 240:
        return "cap_bound"
    return {"n": n + 2, "block_width": width + 1}


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _measure_guessing(inst, total, seed):
    rng = random.Random(seed)
    hits = 0
    started = time.perf_counter()
    for _ in range(total):
        if verify(inst, random_candidate(inst, rng))[0]:
            hits += 1
    return hits, time.perf_counter() - started


def selftest():
    report = {}

    failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            g1_attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed, "reason": "not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": g1_attempts,
        "failures": failures,
        "generation_route": "inverse generation: balanced colours precede the tree and integers",
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **shipping_params)
    planted = [list(part) for part in inst["answer"]]
    corruptions = {}

    drop = [list(planted[0][:-1]), list(planted[1])]
    swap = [list(planted[0]), list(planted[1])]
    swap[0][0], swap[1][0] = swap[1][0], swap[0][0]
    swap = [sorted(part) for part in swap]
    duplicate = [list(planted[0]), list(planted[1]) + [planted[0][0]]]
    empty = []
    out_of_range = [list(planted[0]), list(planted[1])]
    out_of_range[0][0] = inst["n"]
    for name, candidate in (
        ("drop", drop),
        ("swap", swap),
        ("duplicate", duplicate),
        ("empty", empty),
        ("out_of_range", out_of_range),
    ):
        ok, reason = verify(inst, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = {entry["reason"] for entry in corruptions.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in corruptions.values())
        and len(reasons) == len(corruptions),
        "cases": corruptions,
        "distinct_reasons": len(reasons),
    }

    model_style = (
        "The equal loads follow from the block invariant.\n\n"
        "```json\n<answer>\n"
        + json.dumps(inst["answer"])
        + "\n</answer>\n```\n"
        "The two bins may of course be exchanged."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == inst["answer"],
    }

    guess_total = 200_000
    guess_hits, guess_seconds = _measure_guessing(inst, guess_total, 991827)
    space = search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_hits / guess_total,
        "candidate_space": space,
        "candidate_space_bits": math.log2(space),
        "prior": "uniform ordered balanced bipartitions (all free cardinality constraints enforced)",
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_functions = {
        "outlier_largest_half": _attack_largest_half,
        "greedy_balanced_lpt": _attack_balanced_greedy,
        "sorted_alternation": _attack_sorted_alternation,
        "low_block_parity_ansatz": _attack_low_block_parity,
    }
    attack_results = {
        name: {"successes": 0, "attempts": 8, "wall_clock_sec": 0.0}
        for name in attack_functions
    }
    attack_results["random_restart_256"] = {
        "successes": 0,
        "attempts": 8,
        "restarts_per_attempt": 256,
        "wall_clock_sec": 0.0,
    }
    reference_successes = 0
    reference_states = []
    reference_operations = []
    reference_seconds = []
    for attempt, seed in enumerate(_REFERENCE_SEEDS):
        probe = make_instance(seed=seed, **shipping_params)
        for name, attack in attack_functions.items():
            started = time.perf_counter()
            candidate = attack(probe)
            attack_results[name]["wall_clock_sec"] += time.perf_counter() - started
            if verify(probe, candidate)[0]:
                attack_results[name]["successes"] += 1

        started = time.perf_counter()
        restart_rng = random.Random(700_000 + attempt)
        won = False
        for _ in range(256):
            if verify(probe, random_candidate(probe, restart_rng))[0]:
                won = True
                break
        attack_results["random_restart_256"]["wall_clock_sec"] += (
            time.perf_counter() - started
        )
        if won:
            attack_results["random_restart_256"]["successes"] += 1

        started = time.perf_counter()
        exact_answer, cost = _mitm_balanced_partition(probe)
        elapsed = time.perf_counter() - started
        reference_seconds.append(elapsed)
        reference_states.append(cost["states"])
        reference_operations.append(cost["operations"])
        if exact_answer is not None and verify(probe, exact_answer)[0]:
            reference_successes += 1

    for result in attack_results.values():
        result["wall_clock_sec"] = round(result["wall_clock_sec"], 6)
    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    reference = {
        "name": "exact balanced meet-in-the-middle subset sum",
        "complexity": "O(2^(n/2)) time and space",
        "solves": f"{reference_successes}/8, as expected",
        "states_average": round(sum(reference_states) / len(reference_states)),
        "states_max": max(reference_states),
        "operations_average": round(sum(reference_operations) / len(reference_operations)),
        "operations_max": max(reference_operations),
        "wall_clock_sec_average": round(sum(reference_seconds) / len(reference_seconds), 6),
        "wall_clock_sec_max": round(max(reference_seconds), 6),
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "decimal block normalization followed by tree constraint propagation",
            "operations_upper_bound": 5 * (inst["n"] - 1) + 2,
            "solves": "8/8 by the construction proof",
        },
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    exact_valid = 2
    exact_density = exact_valid / space
    strongest_failed = max(
        attack_results.items(), key=lambda pair: pair[1]["wall_clock_sec"]
    )
    report["G5_density_and_baseline_cost"] = {
        "pass": demo_count == 2 and reference_successes == 8,
        "demo_exact_solution_count": demo_count,
        "shipping_structural_solution_count": exact_valid,
        "shipping_exact_solution_density": exact_density,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_sample_fraction": guess_hits / guess_total,
        "baseline_attack_name": strongest_failed[0],
        "baseline_attack_iterations": (
            8 * strongest_failed[1].get("restarts_per_attempt", 1)
        ),
        "baseline_attack_wall_clock_sec": strongest_failed[1]["wall_clock_sec"],
        "reference_states_average": reference["states_average"],
        "reference_operation_count_average": reference["operations_average"],
        "reference_wall_clock_sec_average": reference["wall_clock_sec_average"],
        "uniqueness_basis": "connected-tree incidence constraints have two complementary colourings",
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * shipping_params["n"]
    started = time.perf_counter()
    doubled = make_instance(seed=4242, **doubled_params)
    doubled_build = time.perf_counter() - started
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > space,
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "candidate_space_bits_shipping": math.log2(space),
        "candidate_space_bits_doubled": math.log2(search_space(doubled)),
        "answer_elements_shipping": _answer_atoms(inst["answer"]),
        "answer_elements_doubled": _answer_atoms(doubled["answer"]),
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_reason,
    }

    invariant = 0
    real = 0
    distinct = set()
    for seed in range(20):
        original = make_instance(seed=50_000 + seed, **shipping_params)
        key = canonical_key(original)
        distinct.add(key)
        local_rng = random.Random(90_000 + seed)

        item_order = list(range(original["n"]))
        local_rng.shuffle(item_order)
        reordered = _reorder_instance(original, item_order)

        block_order = list(range(original["blocks"]))
        local_rng.shuffle(block_order)
        block_permuted = _permute_blocks(original, block_order)

        composed = _shift_common_high_block(
            _permute_blocks(reordered, block_order), seed + 1
        )
        for transformed in (reordered, block_permuted, composed):
            if canonical_key(transformed) == key:
                invariant += 1
            if verify(transformed, transformed["answer"])[0]:
                real += 1
    report["G8_canonical_key"] = {
        "pass": invariant == 60 and real == 60 and len(distinct) == 20,
        "invariant_relabellings": invariant,
        "real_transformations_verified": real,
        "unrelated_attempts": 20,
        "unrelated_distinct_keys": len(distinct),
        "transformations": [
            "item reordering with carried witness",
            "base-digit coordinate permutation",
            "composition with a common high-block translation",
        ],
    }

    answer_sizes = []
    for seed in range(20):
        sized = make_instance(seed=100_000 + seed, **shipping_params)
        blob = json.dumps(sized["answer"], separators=(",", ":"))
        answer_sizes.append((len(blob), _answer_atoms(sized["answer"])))
    answer_chars = max(chars for chars, _atoms in answer_sizes)
    answer_elements = max(atoms for _chars, atoms in answer_sizes)
    intended_operations = 5 * (inst["n"] - 1) + 2
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    report["G9_no_tool_suitability"] = {
        "pass": answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": math.ceil(answer_chars / 4),
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
