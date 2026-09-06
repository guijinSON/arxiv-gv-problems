"""Self-contained problem generator for arXiv:2605.05233.

The paper studies bottleneck multiple knapsack (BMKP): allocate weighted,
profitable items to capacity-constrained knapsacks while maximizing the least
profit. This module generates exact, identical-capacity BMKP instances whose
certificates are composed from equal-sum four-item identities. A conventional
bounded-weight dynamic program solves the generated distribution mechanically;
the intended no-tool route is to recognize a hidden residue-orbit invariant.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # This finite-discrete family needs no helper library.
    exact_matrices = rationals = None


TRACK = "B"

# 20 has order four modulo 401 because 20^2 == -1 (mod 401). Every nonzero
# residue therefore lies in a four-cycle {r, 20r, -r, -20r}; its four least
# positive representatives sum to 2*401.
_MODULUS = 401
_MULTIPLIER = 20
_N_KNAPSACKS = 4

PROBLEM_PROFILE = {
    "native_domain": "optimization",
    "object_regime": "finite_discrete",
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "unit-profit weighted items",
        "identical-capacity knapsacks",
        "item-to-knapsack allocation",
    ],
    "verification_operations": [
        "integer item-usage count",
        "integer weight addition",
        "capacity and profit comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Weights reduced modulo 401 form four-cycles under multiplication by "
        "20, and every lifted cycle has the same total; without this invariant "
        "one must mechanically solve balanced subset-sum constraints."
    ),
    "hardness_basis": (
        "Track B: sequential cardinality-constrained subset-sum bitset DP "
        "(pseudo-polynomial O(mNnB/word_size), polynomial on this fixed-height "
        "bounded-weight distribution) solves all 8 shipping instances; at "
        "n=36,height=10 its measured median is 0.300 seconds and 6,616,998 "
        "estimated 64-bit word operations per instance, while the residue-orbit "
        "route uses at most 288 exact arithmetic operations and still requires "
        "recognizing the invariant."
    ),
    "max_answer_tokens": 119,
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
    "demo": {"n": 4, "height": 0},
    "easy": {"n": 12, "height": 6},
    "medium": {"n": 24, "height": 8},
    "hard": {"n": 36, "height": 10},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The item weights' residues modulo 401 form four-cycles under "
    "multiplication by 20."
)
PLACEBO_HINT = (
    "The item list contains many close values, so careful bookkeeping of "
    "identifiers matters."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of four knapsack bundles; each bundle contains exactly n "
        "distinct integer item IDs from 0 through 4n-1, and every ID occurs in "
        "exactly one bundle. Bundle order is knapsack order; IDs inside a "
        "bundle are unordered and random candidates store them sorted."
    ),
    "bounds": {
        "knapsacks": 4,
        "items_per_knapsack": "n",
        "total_item_ids": "4n",
        "item_id_min": 0,
        "item_id_max": "4n-1",
        "repetitions": 0,
    },
}

NOTES = (
    "Section 3 fixes the native BMKP definition used here: disjoint item sets, "
    "one capacity per knapsack, and a max-min profit objective. Theorem 1 in "
    "Section 4 is the easy-side result: identical capacities admit a "
    "polynomial-time (2/3-epsilon)-approximation for fixed epsilon, but it does "
    "not directly produce the exact optimum witness requested here. Section 6 "
    "shows why exact target allocation is delicate by using unit-profit BMKP "
    "in the RN3DM hardness reduction, although this generator does not use that "
    "reduction. Certificates are composed before the instance exists: each "
    "four-cycle of residues is lifted so its four weights have a common sum, "
    "then equal numbers of cycles are assigned to four bins. Item order, "
    "smallest-weight blocks, LPT load balancing, extreme-pair balancing, and "
    "random balanced allocations all fail in selftest(); the successful "
    "reference DP is reported separately because this is Track B."
)

# Filled only from script-owned oracle runs. API failures are retained as
# failures of evidence, never reclassified as model failures. G9's arms are
# diagnostic; only the answer/effort caps gate this module.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0, "api_errors": 4},
    "hinted": {"solved": 0, "attempts": 0, "api_errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "api_errors": 4},
    "hinted_verdict": "pending: OpenRouter HTTP 403 total key limit",
}


def _residue_orbits():
    seen = set()
    result = []
    for start in range(1, _MODULUS):
        if start in seen:
            continue
        orbit = []
        value = start
        for _ in range(4):
            orbit.append(value)
            seen.add(value)
            value = (value * _MULTIPLIER) % _MODULUS
        if value != start or len(set(orbit)) != 4 or sum(orbit) != 2 * _MODULUS:
            raise AssertionError("invalid residue-orbit constants")
        result.append(tuple(orbit))
    return tuple(result)


_ORBITS = _residue_orbits()


def _validate_parameters(n, height):
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer")
    if n < 4 or n % _N_KNAPSACKS != 0 or n > len(_ORBITS):
        raise ValueError("n must be a multiple of 4 between 4 and 100")
    if isinstance(height, bool) or not isinstance(height, int) or height < 0:
        raise ValueError("height must be a nonnegative integer")


def _weak_composition(total, rng):
    """Uniform weak composition of total into four labelled parts."""
    cuts = sorted(rng.sample(range(total + 3), 3))
    return [
        cuts[0],
        cuts[1] - cuts[0] - 1,
        cuts[2] - cuts[1] - 1,
        total + 2 - cuts[2],
    ]


def make_instance(n, seed=0, height=10, **params):
    """Compose a certified four-knapsack BMKP instance from identities.

    ``n`` is the number of four-item residue orbits and also the number of
    items each knapsack must receive. The four lifted weights in every orbit
    have the common sum 401*(height+2). Assigning n/4 complete orbits to each
    knapsack therefore gives a known certificate without solving the instance.
    """
    del params
    _validate_parameters(n, height)
    rng = random.Random(seed)

    orbit_order = list(_ORBITS)
    rng.shuffle(orbit_order)
    groups = []
    group_sum = _MODULUS * (height + 2)
    for raw_orbit in orbit_order[:n]:
        residues = list(raw_orbit)
        rng.shuffle(residues)
        lifts = _weak_composition(height, rng)
        rng.shuffle(lifts)
        weights = [
            _MODULUS * lift + residue
            for lift, residue in zip(lifts, residues)
        ]
        if sum(weights) != group_sum:
            raise AssertionError("four-cycle identity did not compose")
        groups.append(weights)

    # Choose the certificate before item labels exist. All groups have the same
    # distribution and sum; no group or item is a planted outlier.
    shuffled_groups = list(range(n))
    rng.shuffle(shuffled_groups)
    groups_per_bin = n // _N_KNAPSACKS
    group_bin = [0] * n
    for pos, group_id in enumerate(shuffled_groups):
        group_bin[group_id] = pos // groups_per_bin

    tokens = [
        (weight, group_id)
        for group_id, weights in enumerate(groups)
        for weight in weights
    ]
    rng.shuffle(tokens)
    item_weights = [weight for weight, _group_id in tokens]
    answer = [[] for _ in range(_N_KNAPSACKS)]
    for item_id, (_weight, group_id) in enumerate(tokens):
        answer[group_bin[group_id]].append(item_id)
    for bundle in answer:
        bundle.sort()

    capacity = groups_per_bin * group_sum
    return {
        "paper": "arXiv:2605.05233",
        "family": "identical-capacity bottleneck multiple knapsack",
        "n": n,
        "height": height,
        "seed": seed,
        "item_weights": item_weights,
        "item_profits": [1] * (4 * n),
        "capacities": [capacity] * _N_KNAPSACKS,
        "target_profit": n,
        "answer": answer,
    }


def render(inst):
    n = inst["n"]
    weights = json.dumps(inst["item_weights"], separators=(",", ":"))
    capacities = json.dumps(inst["capacities"], separators=(",", ":"))
    lines = [
        "Find an exact bottleneck multiple-knapsack allocation.",
        "",
        "Definitions and conventions.",
        f"There are {4 * n} distinct items, with IDs 0 through {4 * n - 1}, and four knapsacks, with IDs 0 through 3.",
        "Item i has integer weight W[i] and profit 1. Each item may be assigned to at most one knapsack.",
        "Knapsack j has integer capacity B[j]. Its assigned items must have total weight at most B[j].",
        f"The profit of a knapsack is the sum of its item profits. Every knapsack must receive profit at least {n}.",
        f"Your witness must assign exactly {n} distinct item IDs to each knapsack and use every item exactly once.",
        "Bundle order follows knapsack order: entry j is the bundle for knapsack j. IDs inside a bundle are unordered; any order is accepted.",
        "All indexing is 0-based. Capacity bounds and the profit target are inclusive. Repeated item IDs are forbidden.",
        "",
        f"W = {weights}",
        f"B = {capacities}",
        "",
        "Give your final answer inside <answer></answer> tags, as a JSON list of four integer lists of the required size.",
        "Syntax example for four items per bundle (not an answer to this instance): <answer>[[0,1,2,3],[4,5,6,7],[8,9,10,11],[12,13,14,15]]</answer>",
        "Output nothing else inside the tags.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Parse tagged JSON while tolerating prose and Markdown fences."""
    try:
        match = re.search(
            r"<answer>(.*?)</answer>", str(text),
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body).strip()
        return json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def verify(inst, answer):
    """Check any valid allocation; never consult ``inst['answer']``."""
    n = inst["n"]
    if answer == []:
        return False, "empty answer: expected four knapsack bundles"
    if not isinstance(answer, list):
        return False, "malformed: expected a JSON list of four bundles"
    if len(answer) != _N_KNAPSACKS:
        return False, f"wrong bundle count: expected 4, got {len(answer)}"

    flat = []
    for j, bundle in enumerate(answer):
        if not isinstance(bundle, list) or len(bundle) != n:
            return False, (
                f"wrong bundle size: knapsack {j} needs exactly {n} item IDs"
            )
        for item_id in bundle:
            if isinstance(item_id, bool) or not isinstance(item_id, int):
                return False, f"non-integer item ID in knapsack {j}"
            if item_id < 0 or item_id >= 4 * n:
                return False, f"out-of-range item ID {item_id} in knapsack {j}"
            flat.append(item_id)

    seen = set()
    for item_id in flat:
        if item_id in seen:
            return False, f"reused item ID {item_id}"
        seen.add(item_id)
    if len(seen) != 4 * n:
        return False, "not all items are used exactly once"

    for j, bundle in enumerate(answer):
        load = sum(inst["item_weights"][item_id] for item_id in bundle)
        if load > inst["capacities"][j]:
            return False, (
                f"capacity exceeded at knapsack {j}: "
                f"load {load} > {inst['capacities'][j]}"
            )
        profit = sum(inst["item_profits"][item_id] for item_id in bundle)
        if profit < inst["target_profit"]:
            return False, f"profit target missed at knapsack {j}"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniform balanced allocation, with all statement-implied rules applied."""
    n = inst["n"]
    item_ids = list(range(4 * n))
    rng.shuffle(item_ids)
    return [
        sorted(item_ids[j * n:(j + 1) * n])
        for j in range(_N_KNAPSACKS)
    ]


def search_space(inst):
    n = inst["n"]
    return math.factorial(4 * n) // (math.factorial(n) ** 4)


def enumerate_all(inst):
    """Count valid certificates exactly for the hand-scale demo only."""
    n = inst["n"]
    if 4 * n > 16:
        return None
    weights = inst["item_weights"]
    capacities = inst["capacities"]
    count = 0

    def visit(bin_id, remaining):
        nonlocal count
        if bin_id == _N_KNAPSACKS - 1:
            if (len(remaining) == n
                    and sum(weights[i] for i in remaining)
                    == capacities[bin_id]):
                count += 1
            return
        for bundle in itertools.combinations(remaining, n):
            # Total item weight equals total capacity, so any complete valid
            # allocation makes all four capacity inequalities equalities.
            if sum(weights[i] for i in bundle) != capacities[bin_id]:
                continue
            chosen = set(bundle)
            visit(bin_id + 1, tuple(i for i in remaining if i not in chosen))

    visit(0, tuple(range(4 * n)))
    return count


def _normalizing_gcd(values):
    result = 0
    for value in values:
        result = math.gcd(result, abs(value))
    return max(result, 1)


def canonical_key(inst):
    """Invariant under item/bin relabelling and global unit rescaling."""
    wgcd = _normalizing_gcd(inst["item_weights"] + inst["capacities"])
    pgcd = _normalizing_gcd(inst["item_profits"] + [inst["target_profit"]])
    item_types = sorted(
        (weight // wgcd, profit // pgcd)
        for weight, profit in zip(inst["item_weights"], inst["item_profits"])
    )
    payload = [
        inst["target_profit"] // pgcd,
        item_types,
        sorted(capacity // wgcd for capacity in inst["capacities"]),
    ]
    raw = json.dumps(payload, separators=(",", ":"))
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def escalate(params):
    """Raise DP cost at fixed answer length by increasing lift height."""
    out = dict(params)
    height = out.get("height", 10)
    out["height"] = max(height + 1, 2 * height)
    return out


# ---------------------------------------------------------------------------
# Adversaries and the Track-B reference algorithm.

def _chunks(inst, item_order):
    n = inst["n"]
    return [
        sorted(item_order[j * n:(j + 1) * n])
        for j in range(_N_KNAPSACKS)
    ]


def _input_order_attack(inst):
    return _chunks(inst, list(range(4 * inst["n"])))


def _smallest_weight_blocks_attack(inst):
    order = sorted(
        range(4 * inst["n"]),
        key=lambda item_id: (inst["item_weights"][item_id], item_id),
    )
    return _chunks(inst, order)


def _lpt_attack(inst):
    """Largest weight first, always use the currently lightest nonfull bin."""
    n = inst["n"]
    answer = [[] for _ in range(_N_KNAPSACKS)]
    loads = [0] * _N_KNAPSACKS
    order = sorted(
        range(4 * n),
        key=lambda item_id: (-inst["item_weights"][item_id], item_id),
    )
    for item_id in order:
        eligible = [j for j in range(_N_KNAPSACKS) if len(answer[j]) < n]
        j = min(eligible, key=lambda b: (loads[b], len(answer[b]), b))
        answer[j].append(item_id)
        loads[j] += inst["item_weights"][item_id]
    return [sorted(bundle) for bundle in answer]


def _extreme_pair_attack(inst):
    """By-hand ansatz: pair lightest with heaviest, round-robin the pairs."""
    order = sorted(
        range(4 * inst["n"]),
        key=lambda item_id: (inst["item_weights"][item_id], item_id),
    )
    pairs = []
    while order:
        pairs.append((order.pop(0), order.pop()))
    answer = [[] for _ in range(_N_KNAPSACKS)]
    for pos, pair in enumerate(pairs):
        answer[pos % _N_KNAPSACKS].extend(pair)
    return [sorted(bundle) for bundle in answer]


def _random_balanced_restart(inst, rng, restarts=128):
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate, {"restarts": restarts}
    return None, {"restarts": restarts}


def _one_cardinality_subset(weights, cardinality, target):
    """Bitset subset-sum with snapshots for exact witness recovery."""
    mask = (1 << (target + 1)) - 1
    dp = [0] * (cardinality + 1)
    dp[0] = 1
    snapshots = [tuple(dp)]
    transitions = 0
    word_operations = 0
    words_per_bitset = math.ceil((target + 1) / 64)

    for pos, weight in enumerate(weights):
        for count in range(min(cardinality, pos + 1), 0, -1):
            dp[count] |= (dp[count - 1] << weight) & mask
            transitions += 1
            word_operations += words_per_bitset
        snapshots.append(tuple(dp))

    if not ((dp[cardinality] >> target) & 1):
        return None, {
            "bitset_transitions": transitions,
            "word_operations": word_operations,
        }

    selected = []
    count = cardinality
    subtotal = target
    for pos in range(len(weights), 0, -1):
        if (snapshots[pos - 1][count] >> subtotal) & 1:
            continue
        weight = weights[pos - 1]
        if (count <= 0 or subtotal < weight
                or not ((snapshots[pos - 1][count - 1]
                         >> (subtotal - weight)) & 1)):
            return None, {
                "bitset_transitions": transitions,
                "word_operations": word_operations,
            }
        selected.append(pos - 1)
        count -= 1
        subtotal -= weight
    if count != 0 or subtotal != 0:
        return None, {
            "bitset_transitions": transitions,
            "word_operations": word_operations,
        }
    return selected, {
        "bitset_transitions": transitions,
        "word_operations": word_operations,
    }


def _reference_bitset_dp(inst):
    """Mechanical Track-B baseline; it never reads the planted answer."""
    n = inst["n"]
    remaining = list(range(4 * n))
    answer = []
    transitions = 0
    word_operations = 0
    for j in range(_N_KNAPSACKS - 1):
        weights = [inst["item_weights"][item_id] for item_id in remaining]
        selected_positions, metrics = _one_cardinality_subset(
            weights, n, inst["capacities"][j]
        )
        transitions += metrics["bitset_transitions"]
        word_operations += metrics["word_operations"]
        if selected_positions is None:
            return None, {
                "bitset_transitions": transitions,
                "word_operations": word_operations,
            }
        chosen = {remaining[pos] for pos in selected_positions}
        answer.append(sorted(chosen))
        remaining = [item_id for item_id in remaining if item_id not in chosen]
    answer.append(sorted(remaining))
    return answer, {
        "bitset_transitions": transitions,
        "word_operations": word_operations,
    }


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _relabel_instance(
        inst, rng, reorder_items=False, reorder_bins=False,
        weight_scale=1, profit_scale=1):
    n = inst["n"]
    item_order = list(range(4 * n))
    bin_order = list(range(_N_KNAPSACKS))
    if reorder_items:
        rng.shuffle(item_order)
    if reorder_bins:
        rng.shuffle(bin_order)
    old_to_new = [0] * (4 * n)
    for new, old in enumerate(item_order):
        old_to_new[old] = new
    answer = [
        sorted(old_to_new[item_id] for item_id in inst["answer"][old_bin])
        for old_bin in bin_order
    ]
    return {
        "paper": inst.get("paper"),
        "family": inst.get("family"),
        "n": n,
        "height": inst["height"],
        "seed": inst.get("seed"),
        "item_weights": [
            weight_scale * inst["item_weights"][old] for old in item_order
        ],
        "item_profits": [
            profit_scale * inst["item_profits"][old] for old in item_order
        ],
        "capacities": [
            weight_scale * inst["capacities"][old] for old in bin_order
        ],
        "target_profit": profit_scale * inst["target_profit"],
        "answer": answer,
    }


def _capacity_breaking_swap(inst):
    answer = [bundle[:] for bundle in inst["answer"]]
    weights = inst["item_weights"]
    for j in range(_N_KNAPSACKS):
        for k in range(j + 1, _N_KNAPSACKS):
            for x in range(inst["n"]):
                for y in range(inst["n"]):
                    bad = [bundle[:] for bundle in answer]
                    bad[j][x], bad[k][y] = bad[k][y], bad[j][x]
                    load_j = sum(weights[item_id] for item_id in bad[j])
                    load_k = sum(weights[item_id] for item_id in bad[k])
                    if (load_j > inst["capacities"][j]
                            or load_k > inst["capacities"][k]):
                        return bad
    raise AssertionError("no capacity-breaking cross-bin swap found")


def selftest():
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    planted_ok = json_ok = attempts = 0
    for _name, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            attempts += 1
            planted_ok += int(verify(inst, inst["answer"])[0])
            json_ok += int(json.loads(json.dumps(inst["answer"])) == inst["answer"])
    report["G1_planted_verifies"] = {
        "pass": planted_ok == attempts and json_ok == attempts,
        "verified": planted_ok,
        "attempts": attempts,
        "json_native_roundtrips": json_ok,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=424242, **shipping)
    answer = inst["answer"]
    corruptions = {
        "drop": [answer[0][:-1]] + [bundle[:] for bundle in answer[1:]],
        "swap": _capacity_breaking_swap(inst),
        "duplicate": (
            [[answer[0][0], answer[0][0]] + answer[0][2:]]
            + [bundle[:] for bundle in answer[1:]]
        ),
        "empty": [],
        "out_of_range": (
            [[4 * inst["n"]] + answer[0][1:]]
            + [bundle[:] for bundle in answer[1:]]
        ),
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": reason}
    reasons = [row["reason"] for row in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": (
            all(row["rejected"] for row in rejected.values())
            and len(set(reasons)) == len(reasons)
        ),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "The residue cycles give equal-sum bundles.\n"
        "```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("no tagged answer") is None,
        "realistic_response": parsed == answer,
        "garbage_returns_none": parse_answer("no tagged answer") is None,
    }

    guess_rng = random.Random(90210)
    guess_total = 200_000
    guess_hits = 0
    t0 = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - t0
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_fraction,
        "candidate_space": search_space(inst),
        "wall_clock_sec": round(guess_seconds, 6),
        "structure_aware_prior": (
            "uniform allocations using every distinct item once and placing "
            "exactly n items in each of four labelled knapsacks"
        ),
    }

    panel_seeds = list(range(8))
    attack_names = [
        "outlier_smallest_weight_blocks",
        "input_order_blocks",
        "greedy_lpt_lightest_bin",
        "random_balanced_restart_128",
        "by_hand_extreme_pair_round_robin",
    ]
    attacks = {
        name: {"successes": 0, "attempts": len(panel_seeds)}
        for name in attack_names
    }
    reference_successes = 0
    reference_times = []
    reference_transitions = []
    reference_word_ops = []
    for seed in panel_seeds:
        current = make_instance(seed=seed, **shipping)
        random_answer, _random_metrics = _random_balanced_restart(
            current, random.Random(seed ^ 0xBAD5EED), restarts=128
        )
        candidates = {
            "outlier_smallest_weight_blocks": _smallest_weight_blocks_attack(current),
            "input_order_blocks": _input_order_attack(current),
            "greedy_lpt_lightest_bin": _lpt_attack(current),
            "random_balanced_restart_128": random_answer,
            "by_hand_extreme_pair_round_robin": _extreme_pair_attack(current),
        }
        for name, candidate in candidates.items():
            attacks[name]["successes"] += int(verify(current, candidate)[0])

        reference_start = time.perf_counter()
        reference_answer, metrics = _reference_bitset_dp(current)
        reference_times.append(time.perf_counter() - reference_start)
        reference_transitions.append(metrics["bitset_transitions"])
        reference_word_ops.append(metrics["word_operations"])
        reference_successes += int(verify(current, reference_answer)[0])

    all_failed = all(row["successes"] == 0 for row in attacks.values())
    reference_algorithm = {
        "name": "sequential cardinality-constrained subset-sum bitset DP",
        "complexity": (
            "O(m*N*n*B/word_size) word operations per pass; pseudo-polynomial "
            "in general and polynomial on the fixed-height bounded-weight preset"
        ),
        "wall_clock_sec_total": round(sum(reference_times), 6),
        "median_wall_clock_sec": round(statistics.median(reference_times), 6),
        "bitset_transitions_total": sum(reference_transitions),
        "median_bitset_transitions": int(statistics.median(reference_transitions)),
        "word_operations_total": sum(reference_word_ops),
        "median_word_operations": int(statistics.median(reference_word_ops)),
        "wall_clock_sec": round(statistics.median(reference_times), 6),
        "operations": int(statistics.median(reference_word_ops)),
        "solves": f"{reference_successes}/{len(panel_seeds)}, as expected",
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == len(panel_seeds),
        "attacks": attacks,
        "reference_algorithm": reference_algorithm,
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    report["G5_density_and_baseline"] = {
        "pass": (
            guess_fraction < 1e-6
            and all_failed
            and reference_successes == len(panel_seeds)
        ),
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_fraction": guess_fraction,
        "baseline_wall_clock_seconds": round(sum(reference_times), 6),
        "baseline_word_operations": sum(reference_word_ops),
        "baseline_bitset_transitions": sum(reference_transitions),
        "demo_exact_valid_solutions": enumerate_all(demo),
        "demo_n": demo["n"],
    }

    doubled = make_instance(
        n=2 * shipping["n"], height=shipping["height"], seed=31337
    )
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok,
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_verifies": doubled_ok,
        "escalate_from_shipping": escalate(shipping),
        "fixed_answer_length_axis": "height increases while n stays fixed",
    }

    invariant_ok = preserving_ok = 0
    unrelated_keys = []
    key_params = DIFFICULTY["easy"]
    for seed in range(20):
        current = make_instance(seed=20_000 + seed, **key_params)
        key = canonical_key(current)
        unrelated_keys.append(key)
        rng = random.Random(30_000 + seed)
        variants = [
            _relabel_instance(current, rng, reorder_items=True),
            _relabel_instance(current, rng, reorder_bins=True),
            _relabel_instance(
                current, rng, reorder_items=True, reorder_bins=True
            ),
            _relabel_instance(current, rng, weight_scale=3),
            _relabel_instance(current, rng, profit_scale=2),
            _relabel_instance(
                current, rng, reorder_items=True, reorder_bins=True,
                weight_scale=5, profit_scale=3,
            ),
        ]
        for variant in variants:
            invariant_ok += int(canonical_key(variant) == key)
            preserving_ok += int(verify(variant, variant["answer"])[0])
    report["G8_canonical_key"] = {
        "pass": (
            invariant_ok == 120
            and preserving_ok == 120
            and len(set(unrelated_keys)) == 20
        ),
        "invariance_passed": invariant_ok,
        "invariance_attempts": 120,
        "transform_preservation_passed": preserving_ok,
        "transform_preservation_attempts": 120,
        "distinct_keys": len(set(unrelated_keys)),
        "unrelated_instances": 20,
        "invariant": (
            "normalized item (weight,profit) multiset, capacity multiset, and "
            "target; invariant under item/bin relabelling and unit scaling"
        ),
    }

    blob = json.dumps(answer, separators=(",", ":"))
    elements = _answer_atoms(answer)
    tokens = math.ceil(len(blob) / 4)
    # 4n reductions; for each of n orbits, one multiply, one remainder, and two
    # subtractions recover the other residues from a representative.
    intended_operations = 8 * inst["n"]
    oracle = G9_ORACLE_RESULTS
    placebo_rate = (
        oracle["placebo"]["solved"] / oracle["placebo"]["attempts"]
        if oracle["placebo"]["attempts"] else None
    )
    hinted_rate = (
        oracle["hinted"]["solved"] / oracle["hinted"]["attempts"]
        if oracle["hinted"]["attempts"] else None
    )
    delta = (
        hinted_rate - placebo_rate
        if hinted_rate is not None and placebo_rate is not None else None
    )
    within_caps = (
        len(blob) <= 2000
        and elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {
            "bare": dict(oracle["bare"]),
            "hinted": dict(oracle["hinted"]),
            "placebo": dict(oracle["placebo"]),
        },
        "hinted_minus_placebo": delta,
        "hinted_verdict": oracle["hinted_verdict"],
        "answer_chars": len(blob),
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "size_and_effort_caps_pass": within_caps,
        "diagnostic_complete": all(
            oracle[name]["attempts"] >= 3
            for name in ("bare", "hinted", "placebo")
        ),
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2))
