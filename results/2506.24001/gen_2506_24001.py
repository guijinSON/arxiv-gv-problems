"""Verified inverse generator for LS Multi Knapsack from arXiv:2506.24001.

The generated instances use the restricted one-knapsack construction in
Theorem 22 (``MKisHard`` in the source).  An improving local move is exactly a
fixed-cardinality subset-sum witness, but verification is a direct replay of
the proposed item flips.

This module uses only the Python standard library and has no import-time side
effects.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re
from typing import Any


DIFFICULTY = {
    # subset_fraction makes the search radius grow with n.  The large binary
    # weights rule out pseudo-polynomial dynamic programming at these sizes.
    # Their bit widths also keep n / log2(max weight) above the classic
    # low-density subset-sum range in which lattice attacks are strongest.
    "medium": {"n": 64, "subset_fraction": 0.30, "value_bits": 40},
    "hard": {"n": 96, "subset_fraction": 0.31, "value_bits": 48},
}

SHIPPING_DIFFICULTY = "medium"


NOTES = r"""
Paper basis.  Section 4.5 defines LS Multi Knapsack: an input includes a
feasible allocation, and the witness is another feasible allocation with
strictly larger score at flip distance at most k.  Section 5.1, Lemma 21 first
makes Positive d-Sum size-limiting.  Theorem 22 then proves W[1]-hardness in k
and an ETH n^{o(k)} lower bound even for one knapsack, binary-encoded items,
weight=value, and an initial solution that is locally optimal iff globally
optimal.  The construction puts all ordinary items in a capacity-(T+1)
knapsack and leaves one item of weight/value target+1 out.  An improvement must
insert the special item and remove ordinary weight exactly target.

Easy regimes avoided.  Theorem 5 and Section 4.5 give algorithms exponential
in the search radius k and number of distinct item types tau.  Here every
ordinary weight is distinct, tau=n+1, and the required subset size (hence k)
grows linearly with n.  Values are binary-encoded and wide, so the usual
pseudo-polynomial subset-sum table is not polynomial in the input bit length
and is enormous for the presets.

Inverse generation and attacks.  The witness IDs are sampled before any item
weights.  Every ordinary item, planted or decoy, then receives a distinct
uniform random offset from exactly the same interval.  The target is the sum
of the planted weights.  A common large baseline makes the instance
size-limiting without changing the equal distribution of plants and decoys.
The outlier attack chooses weights closest to the target average; the greedy
attack repeatedly chooses the weight closest to the remaining average; the
random-restart attack uses uniform fixed-size starts plus improving one-item
swaps.  selftest requires all three to fail on at least eight seeds.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 250_000


def _derive_subset_size(n: int, subset_fraction: float) -> int:
    if isinstance(n, bool) or not isinstance(n, int) or n < 8:
        raise ValueError("n must be an integer at least 8")
    if not isinstance(subset_fraction, (int, float)) or not (0.10 <= subset_fraction <= 0.45):
        raise ValueError("subset_fraction must be between 0.10 and 0.45")
    return max(3, min(n - 3, int(round(n * float(subset_fraction)))))


def make_instance(
    n: int,
    seed: int = 0,
    *,
    subset_fraction: float = 0.30,
    value_bits: int = 80,
) -> dict:
    """Create a planted one-knapsack local-search instance.

    The answer (a uniformly random d-subset of the ordinary item IDs) is drawn
    first.  All ordinary weights are then independently drawn without
    replacement from one uniform range, so planted items and decoys have the
    same marginal distribution.  Larger n increases d linearly and increases
    both C(n,d) and the generic exponential-search cost.
    """

    d = _derive_subset_size(n, subset_fraction)
    if isinstance(value_bits, bool) or not isinstance(value_bits, int) or value_bits < 24:
        raise ValueError("value_bits must be an integer at least 24")

    rng = random.Random(seed)

    # G: sample the witness before constructing any numeric instance data.
    planted = sorted(rng.sample(range(1, n + 1), d))
    planted_set = set(planted)

    span = 1 << value_bits
    baseline = (d + 1) * span

    # Draw every ordinary item from the same distribution.  Uniqueness avoids
    # artificial item types and also makes a one-element corruption provably
    # change the removed weight.
    offsets: list[int] = []
    used: set[int] = set()
    while len(offsets) < n:
        x = rng.randrange(span)
        if x not in used:
            used.add(x)
            offsets.append(x)

    weights = [baseline + x for x in offsets]
    removal_target = sum(weights[i - 1] for i in planted)
    ordinary_total = sum(weights)
    special_id = n + 1
    special_weight = removal_target + 1
    capacity = ordinary_total + 1

    items = [
        {
            "id": i,
            "weight": weights[i - 1],
            "value": weights[i - 1],
            "initial": "in",
        }
        for i in range(1, n + 1)
    ]
    items.append(
        {
            "id": special_id,
            "weight": special_weight,
            "value": special_weight,
            "initial": "out",
        }
    )

    # planted_set is deliberately used only while building the target; it is
    # not stored as instance metadata.  The checker never consults "answer".
    assert sum(item["weight"] for item in items if item["id"] in planted_set) == removal_target

    return {
        "family": "LS Multi Knapsack / size-limiting fixed-cardinality subset sum",
        "n": n,
        "required_removals": d,
        "radius": d + 1,
        "capacity": capacity,
        "initial_weight": ordinary_total,
        "initial_score": ordinary_total,
        "removal_target": removal_target,
        "special_id": special_id,
        "items": items,
        "value_bits": value_bits,
        "answer": planted,
    }


def render(inst: dict) -> str:
    """Render the complete, self-contained solver-facing problem statement."""

    d = inst["required_removals"]
    rows = sorted(inst["items"], key=lambda item: item["id"])
    table = "\n".join(
        f'{item["id"]} {item["weight"]} {item["value"]} {item["initial"]}'
        for item in rows
    )
    ordinary_ids = [item["id"] for item in rows if item["id"] != inst["special_id"]]
    example = ", ".join(map(str, ordinary_ids[:d]))

    return f"""LOCAL-SEARCH MULTI KNAPSACK (one knapsack)

There is one knapsack and a set of indivisible items.  Every item has a
nonnegative integer weight and value.  An assignment is feasible when the sum
of weights of the items inside the knapsack is at most its capacity.  Its score
is the sum of values inside.  A flip changes one item's status from inside to
outside or from outside to inside.  The flip distance is the number of items
whose final status differs from the supplied initial assignment.

Find a feasible assignment with score STRICTLY larger than the initial score
and flip distance at most {inst["radius"]}.

This instance has {inst["n"]} ordinary items and one special item.  All
ordinary items start inside; special item {inst["special_id"]} starts outside.
Every value equals its weight.  Your witness must name exactly {d} distinct
ordinary items to remove; special item {inst["special_id"]} is then inserted
automatically.  Order does not matter and repeated IDs are forbidden.  Item
IDs are the integers shown below and are 1-indexed.

Knapsack capacity: {inst["capacity"]}
Initial total weight: {inst["initial_weight"]}
Initial score: {inst["initial_score"]}
Required flip distance: exactly {inst["radius"]} ({d} removals plus the special insertion)

For clarity, with these data the replay is feasible and strictly improving if
and only if the removed ordinary weights sum exactly to
{inst["removal_target"]}.  This equality is a derived aid; the checker still
replays the flips, checks capacity, and recomputes the score.

ITEMS (one row per item: ID WEIGHT VALUE INITIAL_STATUS)
{table}

Give your final answer inside <answer></answer> tags, as a comma-separated list
of exactly {d} distinct ordinary item IDs.  Do not include special item
{inst["special_id"]}; it is inserted automatically.
Example: <answer>{example}</answer>
Output nothing else inside the tags."""


def parse_answer(text: str) -> object | None:
    """Extract the last well-formed tagged integer list from model output."""

    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    for raw in reversed(matches):
        body = raw.strip()
        if body.startswith("```") and body.endswith("```"):
            body = body[3:-3].strip()
            if body.lower().startswith(("json\n", "text\n")):
                body = body.split("\n", 1)[1].strip()
        if body.startswith("[") and body.endswith("]"):
            try:
                value = json.loads(body)
            except (TypeError, ValueError):
                continue
            if isinstance(value, list) and value and all(
                isinstance(x, int) and not isinstance(x, bool) for x in value
            ):
                return value
            continue
        if not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", body):
            continue
        try:
            return [int(part.strip()) for part in body.split(",")]
        except ValueError:
            continue
    return None


def _item_map(inst: dict) -> dict[int, dict]:
    return {item["id"]: item for item in inst["items"]}


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Replay a candidate move; never consult the planted ``inst['answer']``."""

    if not isinstance(answer, list):
        return False, "answer must be a list of item IDs"
    if not answer:
        return False, "answer is empty"
    if any(not isinstance(x, int) or isinstance(x, bool) for x in answer):
        return False, "every item ID must be an integer"
    if len(answer) != inst["required_removals"]:
        return False, f'expected exactly {inst["required_removals"]} removal IDs'
    if len(set(answer)) != len(answer):
        return False, "removal IDs must be distinct"

    by_id = _item_map(inst)
    unknown = [x for x in answer if x not in by_id]
    if unknown:
        return False, f"unknown item ID: {unknown[0]}"
    if inst["special_id"] in answer:
        return False, "the special item must be inserted, not removed"
    if any(by_id[x]["initial"] != "in" for x in answer):
        return False, "every listed removal must initially be inside"

    removed_weight = sum(by_id[x]["weight"] for x in answer)
    removed_value = sum(by_id[x]["value"] for x in answer)
    special = by_id[inst["special_id"]]
    final_weight = inst["initial_weight"] - removed_weight + special["weight"]
    final_score = inst["initial_score"] - removed_value + special["value"]

    if final_weight > inst["capacity"]:
        return False, f"replayed assignment exceeds capacity by {final_weight - inst['capacity']}"
    if final_score <= inst["initial_score"]:
        return False, "replayed score does not strictly improve"
    if len(answer) + 1 > inst["radius"]:
        return False, "replayed assignment exceeds the flip radius"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the solver-visible fixed-size structural search space."""

    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    ordinary = [
        item["id"]
        for item in inst["items"]
        if item["id"] != inst["special_id"] and item["initial"] == "in"
    ]
    return sorted(rng.sample(ordinary, inst["required_removals"]))


def search_space(inst: dict) -> int | None:
    """Number of shape-correct witnesses: d-subsets of the n ordinary IDs."""

    return math.comb(inst["n"], inst["required_removals"])


def enumerate_all(inst: dict) -> int | None:
    """Count all valid witnesses exactly when brute force stays below a cap."""

    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    ordinary = sorted(
        item["id"]
        for item in inst["items"]
        if item["id"] != inst["special_id"] and item["initial"] == "in"
    )
    count = 0
    for candidate in itertools.combinations(ordinary, inst["required_removals"]):
        if verify(inst, list(candidate))[0]:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Canonical key under IDs, row order, and numeric affine symmetry.

    For an exact-d sum, replacing each ordinary weight ``w`` by ``u*w+c`` and
    the target by ``u*t+d*c`` (u a positive integer) preserves precisely the
    same witnesses.  Subtracting the minimum ordinary weight and dividing by
    the common numeric gcd puts that symmetry in a deterministic normal form.
    The seed, planted answer, render order, and raw rendered text are absent.
    """

    special = _item_map(inst)[inst["special_id"]]
    ordinary = [item for item in inst["items"] if item["id"] != inst["special_id"]]
    origin = min(int(item["weight"]) for item in ordinary)
    raw_offsets = sorted(int(item["weight"]) - origin for item in ordinary)
    target_offset = int(inst["removal_target"]) - inst["required_removals"] * origin
    improvement_unit = int(special["weight"]) - int(inst["removal_target"])
    capacity_unit = int(inst["capacity"]) - int(inst["initial_weight"])
    scale = 0
    for number in raw_offsets + [target_offset, improvement_unit, capacity_unit]:
        scale = math.gcd(scale, abs(number))
    scale = max(1, scale)
    payload = {
        "family": inst["family"],
        "ordinary_offsets": [number // scale for number in raw_offsets],
        "target_offset": target_offset // scale,
        "improvement_unit": improvement_unit // scale,
        "capacity_unit": capacity_unit // scale,
        "weight_equals_value": all(item["weight"] == item["value"] for item in inst["items"]),
        "ordinary_initially_in": all(item["initial"] == "in" for item in ordinary),
        "special_initially_out": special["initial"] == "out",
        "radius": int(inst["radius"]),
        "required_removals": int(inst["required_removals"]),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase both combinatorial crowding and numeric width."""

    if not isinstance(params, dict) or "n" not in params:
        return None
    n = int(params["n"])
    if n >= 220:
        return None
    harder = dict(params)
    harder["n"] = min(220, max(n + 16, int(math.ceil(n * 1.35))))
    harder["subset_fraction"] = min(0.36, float(params.get("subset_fraction", 0.30)) + 0.01)
    harder["value_bits"] = min(112, int(params.get("value_bits", 40)) + 8)
    return harder


def _format_answer(answer: list[int]) -> str:
    return ", ".join(map(str, answer))


def _outlier_attack(inst: dict) -> list[int]:
    """Pick the d weights closest to the target's per-item average."""

    d = inst["required_removals"]
    ordinary = [item for item in inst["items"] if item["id"] != inst["special_id"]]
    ranked = sorted(ordinary, key=lambda item: (abs(d * item["weight"] - inst["removal_target"]), item["id"]))
    return sorted(item["id"] for item in ranked[:d])


def _greedy_attack(inst: dict) -> list[int]:
    """Repeatedly choose the item closest to the remaining target average."""

    remaining = [item for item in inst["items"] if item["id"] != inst["special_id"]]
    chosen: list[int] = []
    residual = inst["removal_target"]
    slots = inst["required_removals"]
    while slots:
        pick = min(remaining, key=lambda item: (abs(slots * item["weight"] - residual), item["id"]))
        chosen.append(pick["id"])
        residual -= pick["weight"]
        remaining.remove(pick)
        slots -= 1
    return sorted(chosen)


def _random_restart_attack(inst: dict, rng: random.Random) -> list[int]:
    """Fixed-size random starts followed by sampled improving one-item swaps."""

    by_id = _item_map(inst)
    ordinary = [item["id"] for item in inst["items"] if item["id"] != inst["special_id"]]
    d = inst["required_removals"]
    target = inst["removal_target"]
    best: list[int] | None = None
    best_error: int | None = None

    for _ in range(128):
        selected = set(rng.sample(ordinary, d))
        total = sum(by_id[x]["weight"] for x in selected)
        for _ in range(12):
            error = abs(total - target)
            if error == 0:
                return sorted(selected)
            outside = [x for x in ordinary if x not in selected]
            best_swap: tuple[int, int, int, int] | None = None
            for _ in range(64):
                gone = rng.choice(tuple(selected))
                added = rng.choice(outside)
                new_total = total - by_id[gone]["weight"] + by_id[added]["weight"]
                new_error = abs(new_total - target)
                if new_error < error and (best_swap is None or new_error < best_swap[0]):
                    best_swap = (new_error, gone, added, new_total)
            if best_swap is None:
                break
            _, gone, added, total = best_swap
            selected.remove(gone)
            selected.add(added)
        final_error = abs(total - target)
        candidate = sorted(selected)
        if best_error is None or final_error < best_error:
            best, best_error = candidate, final_error
    assert best is not None
    return best


def _relabel_instance(inst: dict, rng: random.Random, *, reorder: bool) -> dict:
    """Return an isomorphic instance under an arbitrary item-ID permutation."""

    ids = [item["id"] for item in inst["items"]]
    shuffled = ids[:]
    rng.shuffle(shuffled)
    mapping = dict(zip(ids, shuffled))
    transformed = {key: value for key, value in inst.items() if key not in {"items", "answer"}}
    transformed["items"] = [dict(item, id=mapping[item["id"]]) for item in inst["items"]]
    if reorder:
        rng.shuffle(transformed["items"])
    transformed["special_id"] = mapping[inst["special_id"]]
    transformed["answer"] = sorted(mapping[x] for x in inst["answer"])
    return transformed


def _reorder_instance(inst: dict, rng: random.Random) -> dict:
    transformed = {key: value for key, value in inst.items() if key not in {"items", "answer"}}
    transformed["items"] = [dict(item) for item in inst["items"]]
    rng.shuffle(transformed["items"])
    transformed["answer"] = list(inst["answer"])
    return transformed


def _affine_numeric_instance(inst: dict, multiplier: int, translation: int) -> dict:
    """Apply a witness-preserving affine map to the fixed-cardinality kernel."""

    if multiplier <= 0 or translation < 0:
        raise ValueError("affine test map requires multiplier > 0 and translation >= 0")
    transformed = {key: value for key, value in inst.items() if key not in {"items", "answer"}}
    d = inst["required_removals"]
    n = inst["n"]
    new_target = multiplier * inst["removal_target"] + d * translation
    new_initial = multiplier * inst["initial_weight"] + n * translation
    transformed["removal_target"] = new_target
    transformed["initial_weight"] = new_initial
    transformed["initial_score"] = new_initial
    transformed["capacity"] = new_initial + multiplier
    transformed["items"] = []
    for item in inst["items"]:
        changed = dict(item)
        if item["id"] == inst["special_id"]:
            changed["weight"] = new_target + multiplier
            changed["value"] = new_target + multiplier
        else:
            changed["weight"] = multiplier * item["weight"] + translation
            changed["value"] = multiplier * item["value"] + translation
        transformed["items"].append(changed)
    transformed["answer"] = list(inst["answer"])
    return transformed


def selftest() -> dict:
    """Run gates G1--G8 and return a JSON-serializable evidence dictionary."""

    report: dict[str, Any] = {
        "paper": "2506.24001",
        "family": "LS Multi Knapsack, one knapsack, weight=value",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: every named preset, several independent seeds.
    g1_checks = 0
    g1_failures: list[dict[str, Any]] = []
    for preset, params in DIFFICULTY.items():
        for seed in range(6):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=271828, **ship_params)
    planted = list(inst["answer"])
    ordinary_ids = {item["id"] for item in inst["items"] if item["id"] != inst["special_id"]}
    unused = sorted(ordinary_ids - set(planted))

    # G2: validation order intentionally yields a distinct diagnostic per case.
    replacement = unused[0]
    swapped = list(planted)
    swapped[0] = replacement
    corruptions = {
        "drop_one": planted[:-1],
        "swap_one": swapped,
        "duplicate": planted[:-1] + [planted[0]],
        "empty": [],
        "out_of_range": planted[:-1] + [max(ordinary_ids) + 1000],
    }
    corruption_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"accepted": ok, "reason": reason}
        reasons.append(reason)
    g2_pass = all(not row["accepted"] for row in corruption_results.values()) and len(set(reasons)) == len(reasons)
    report["G2_rejects_corruption"] = {
        "pass": g2_pass,
        "distinct_reasons": len(set(reasons)),
        "cases": corruption_results,
    }

    # G3: prose and a Markdown fence surround the tagged wire format.
    model_style = (
        "I balanced the capacity and recomputed the score.\n```text\n"
        f"<answer>{_format_answer(planted)}</answer>\n```\nThis is the improving flip."
    )
    parsed = parse_answer(model_style)
    malformed = ["", "no tags", "<answer>1, nope</answer>", "<answer></answer>"]
    malformed_none = sum(parse_answer(x) is None for x in malformed)
    report["G3_round_trip"] = {
        "pass": parsed == planted and malformed_none == len(malformed),
        "realistic_response_round_trip": parsed == planted,
        "malformed_returned_none": f"{malformed_none}/{len(malformed)}",
    }

    # G4: uniform over the exact-d subset space, not arbitrary bit vectors.
    guess_rng = random.Random(314159265)
    total_guesses = 200_000
    hits = 0
    for _ in range(total_guesses):
        hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    empirical = hits / total_guesses
    report["G4_guess_resistance"] = {
        "pass": empirical < 1e-6,
        "hits": hits,
        "total": total_guesses,
        "empirical_probability": empirical,
        "sampling_prior": "uniform over all d-subsets of ordinary items",
        "structure_aware_space": search_space(inst),
    }

    # G5: an exact brute-force count on a deliberately small probe instance.
    probe = make_instance(n=20, seed=1234567, subset_fraction=0.30, value_bits=40)
    probe_solutions = enumerate_all(probe)
    probe_space = search_space(probe)
    probe_fraction = None if probe_solutions is None else probe_solutions / probe_space
    report["G5_sparse"] = {
        "pass": probe_solutions is not None and probe_solutions >= 1 and probe_fraction < 0.01,
        "probe_n": probe["n"],
        "probe_d": probe["required_removals"],
        "valid_answers": probe_solutions,
        "candidate_space": probe_space,
        "solution_fraction": probe_fraction,
        "shipping_enumeration": enumerate_all(inst),
    }

    # G6: attacks know the planting mechanism but not the sampled witness.
    attack_seeds = list(range(800, 808))
    attack_success = {"outlier_target_average": 0, "greedy_remaining_average": 0, "random_restart_swap": 0}
    attack_reasons: dict[str, list[str]] = {name: [] for name in attack_success}
    for seed in attack_seeds:
        attacked = make_instance(seed=seed, **ship_params)
        candidates = {
            "outlier_target_average": _outlier_attack(attacked),
            "greedy_remaining_average": _greedy_attack(attacked),
            "random_restart_swap": _random_restart_attack(attacked, random.Random(seed ^ 0x5A17)),
        }
        for name, candidate in candidates.items():
            ok, reason = verify(attacked, candidate)
            attack_success[name] += int(ok)
            attack_reasons[name].append(reason)
    attack_rows = {
        name: {
            "successes": successes,
            "seeds": len(attack_seeds),
            "failed_all": successes == 0,
            "reasons": sorted(set(attack_reasons[name])),
        }
        for name, successes in attack_success.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(row["failed_all"] for row in attack_rows.values()),
        "attacks": attack_rows,
    }

    # G7: doubling n also grows d; construction and the planted replay survive.
    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["required_removals"] > inst["required_removals"]
        and search_space(doubled) > search_space(inst),
        "base_n": inst["n"],
        "base_d": inst["required_removals"],
        "base_space": search_space(inst),
        "doubled_n": doubled["n"],
        "doubled_d": doubled["required_removals"],
        "doubled_space": search_space(doubled),
        "doubled_verify_reason": doubled_reason,
    }

    # G8: row order, IDs, and affine fixed-cardinality symmetry, including compositions.
    invariant_checks = 0
    real_transform_checks = 0
    invariant_failures = []
    for seed in range(20):
        original = make_instance(n=24, seed=10_000 + seed, subset_fraction=0.25, value_bits=48)
        key = canonical_key(original)
        rng = random.Random(90_000 + seed)
        reordered = _reorder_instance(original, rng)
        relabelled = _relabel_instance(original, rng, reorder=False)
        composed = _relabel_instance(reordered, rng, reorder=True)
        affine = _affine_numeric_instance(original, multiplier=3, translation=17 + seed)
        affine_composed = _affine_numeric_instance(composed, multiplier=5, translation=31 + seed)
        reversed_rows = _reorder_instance(original, random.Random(seed))
        reversed_rows["items"].reverse()
        variants = {
            "row_permutation": reordered,
            "id_relabelling": relabelled,
            "id_and_row_composed": composed,
            "affine_numeric": affine,
            "affine_id_row_composed": affine_composed,
            "reversed_rows": reversed_rows,
        }
        for name, variant in variants.items():
            invariant_checks += 1
            if canonical_key(variant) != key:
                invariant_failures.append({"seed": seed, "transform": name})
        # Row order preserves the literal witness; ID relabelling carries it.
        real_transform_checks += int(verify(reordered, original["answer"])[0])
        real_transform_checks += int(verify(relabelled, relabelled["answer"])[0])
        real_transform_checks += int(verify(affine, original["answer"])[0])
        real_transform_checks += int(verify(affine_composed, affine_composed["answer"])[0])

    unrelated_keys = {
        canonical_key(make_instance(n=24, seed=20_000 + seed, subset_fraction=0.25, value_bits=48))
        for seed in range(24)
    }
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and real_transform_checks == 80 and len(unrelated_keys) == 24,
        "invariance_checks_passed": invariant_checks - len(invariant_failures),
        "invariance_checks_total": invariant_checks,
        "real_transformation_verifications": f"{real_transform_checks}/80",
        "distinct_unrelated_keys": f"{len(unrelated_keys)}/24",
        "transformations": [
            "input-row permutation",
            "arbitrary item-ID permutation",
            "positive affine map of the fixed-cardinality numeric kernel",
            "their compositions",
        ],
        "failures": invariant_failures,
    }

    gate_values = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
