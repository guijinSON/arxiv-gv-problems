"""Verified generator for a hard special case of quotient-sum (arXiv:2503.01929).

The generated task is the h=0 binary-lamp interval construction used in the
paper's reduction from 3-PARTITION.  A witness gives one integer translation
for every interval-shaped lamp function.

This module uses only the Python standard library, performs no file or network
I/O, and prints nothing at import time.
"""

from __future__ import annotations

import json
import math
import random
import re
from functools import lru_cache
from itertools import combinations


DIFFICULTY: dict = {
    "demo": {"n": 2, "width_factor": 0.5},
    "easy": {"n": 10, "width_factor": 0.5},
    "medium": {"n": 20, "width_factor": 0.5},
    "hard": {"n": 32, "width_factor": 0.5},
}

SHIPPING_DIFFICULTY = "hard"


def _sample_block_cuts(rng: random.Random, q: int) -> tuple[int, int]:
    """Uniformly sample two cuts whose three gaps lie in the 3-PARTITION band."""
    target = 4 * q
    while True:
        a = rng.randrange(q + 1, 2 * q)
        b = rng.randrange(q + 1, 2 * q)
        c = target - a - b
        if q < c < 2 * q and not (a == b == c):
            # Rejection from a symmetric Cartesian product makes every accepted
            # ordered triple equiprobable; no within-triple role has a special
            # marginal distribution.
            return a, a + b


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a planted rank-0 quotient-sum witness.

    ``n`` is the number of target blocks.  There are exactly ``3*n`` input
    functions.  The hidden placement order (the witness skeleton) is sampled
    first; interval lengths are then sampled in symmetric triples around it.
    Larger ``n`` increases both the witness length and the exact-cover core.

    Optional parameter:
        width_factor: controls the integer value range as q ~= factor*n**2.
            The shipped value 0.5 empirically gives crowded sum-T triples
            without making random greedy restarts effective.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    unknown = set(params) - {"width_factor"}
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    width_factor = params.get("width_factor", 0.5)
    if isinstance(width_factor, bool) or not isinstance(width_factor, (int, float)):
        raise TypeError("width_factor must be a positive number")
    if not math.isfinite(float(width_factor)) or width_factor <= 0:
        raise ValueError("width_factor must be a positive finite number")

    rng = random.Random(seed)
    item_count = 3 * n
    q = max(12, int(float(width_factor) * n * n + 0.5))
    target = 4 * q

    # Inverse generation: sample the complete combinatorial placement order
    # before any public interval length is drawn.
    placement_order = list(range(item_count))
    rng.shuffle(placement_order)

    # First finish the numeric witness: each sampled cut becomes the start of
    # an interval.  No public interval length exists yet.
    answer = [0] * item_count
    block_plans = []
    for block in range(n):
        item_ids = placement_order[3 * block : 3 * block + 3]
        cut_1, cut_2 = _sample_block_cuts(rng, q)
        base = block * (target + 1)
        starts = (base, base + cut_1, base + cut_2)
        for item_id, start in zip(item_ids, starts):
            answer[item_id] = start
        block_plans.append((item_ids, (cut_1, cut_2)))

    # Only after the complete answer vector has been sampled do we construct
    # the public lengths around it, as successive differences between cuts.
    lengths = [0] * item_count
    for item_ids, (cut_1, cut_2) in block_plans:
        derived_lengths = (cut_1, cut_2 - cut_1, target - cut_2)
        for item_id, length in zip(item_ids, derived_lengths):
            lengths[item_id] = length

    blocks = [
        [block * (target + 1), block * (target + 1) + target - 1]
        for block in range(n)
    ]
    max_shift = blocks[-1][1]
    return {
        "family": "rank_zero_binary_lamp_quotient_sum",
        "paper": "arXiv:2503.01929",
        "n": n,
        "seed": seed,
        "width_factor": float(width_factor),
        "q": q,
        "target_length": target,
        "gap": 1,
        "lengths": lengths,
        "blocks": blocks,
        "max_shift": max_shift,
        "answer": answer,
    }


def render(inst) -> str:
    """Render a complete, standalone problem statement."""
    lengths = inst["lengths"]
    target = inst["target_length"]
    blocks = inst["blocks"]
    max_shift = inst["max_shift"]
    numbered = "\n".join(
        f"{i}: {length}" for i, length in enumerate(lengths, start=1)
    )
    block_text = ", ".join(f"[{a}, {b}]" for a, b in blocks)
    return f"""Binary-lamp quotient-sum witness problem

All coordinates below are integers.  A binary lamp configuration is a function
from the integers to {{0,1}} with only finitely many 1s.  Configurations are
added pointwise modulo 2 (XOR): at every coordinate, an even number of 1s sums
to 0 and an odd number sums to 1.

There are {len(lengths)} labelled interval configurations.  Item i has the
positive length shown below and initially has value 1 exactly at coordinates
0, 1, ..., length_i-1.  Choosing its integer shift s_i translates those 1s to
the CLOSED interval [s_i, s_i + length_i - 1].

The target configuration is 1 exactly on these {len(blocks)} CLOSED blocks:
{block_text}
It is 0 at every other integer coordinate.  Consecutive target blocks are
separated by exactly the one-coordinate gap visible in their endpoints.

Find one shift for every item such that the XOR sum of all shifted interval
configurations equals the target at every integer coordinate.

Conventions and constraints:
- Items are labelled 1 through {len(lengths)} in the order listed below.
- The answer is an ordered JSON list [s_1, ..., s_{len(lengths)}]; list position
  i corresponds to labelled item i.  Reordering entries changes the answer.
- Every shift is an integer in the inclusive range 0 through {max_shift}.
- All shifts must be distinct; repeated shifts are forbidden.
- Intervals are closed at both ends.  Coordinates and shifts are 0-based.
- Every item is used exactly once.  No item may be omitted or repeated.

Target block length T: {target}
Item lengths (label: length):
{numbered}

Give your final answer inside <answer></answer> tags, as one JSON list of exactly
{len(lengths)} distinct integers in item-label order.
Example format: <answer>[0, 17, 42]</answer>
Output nothing else inside the tags."""


def _parse_payload(payload: str):
    payload = payload.strip()
    try:
        value = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        # A forgiving secondary form for otherwise compliant comma-separated
        # integer output inside the required tags.
        if not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", payload):
            return None
        try:
            value = [int(piece.strip()) for piece in payload.split(",")]
        except ValueError:
            return None
    if not isinstance(value, list):
        return None
    if any(isinstance(x, bool) or not isinstance(x, int) for x in value):
        return None
    return value


def parse_answer(text) -> object | None:
    """Extract a JSON integer list despite prose, fences, and whitespace."""
    if not isinstance(text, str):
        return None

    tagged = re.findall(
        r"<answer\b[^>]*>(.*?)</answer\s*>", text, flags=re.IGNORECASE | re.DOTALL
    )
    for payload in reversed(tagged):
        value = _parse_payload(payload)
        if value is not None:
            return value

    # Models occasionally omit the requested tags while leaving a visibly
    # unambiguous final JSON list.  Recover the last such list rather than
    # treating a renderer-compliance mistake as oracle failure.
    arrays = re.findall(r"\[[\s,+\-\d]*\]", text, flags=re.DOTALL)
    for payload in reversed(arrays):
        value = _parse_payload(payload)
        if value is not None:
            return value
    return None


def verify(inst, answer) -> tuple[bool, str]:
    """Check any valid translation witness; never consult the planted answer."""
    lengths = inst["lengths"]
    item_count = len(lengths)
    if not isinstance(answer, list):
        return False, "answer_not_a_list"
    if len(answer) == 0:
        return False, "empty_answer"
    if len(answer) != item_count:
        return False, f"wrong_length_expected_{item_count}_got_{len(answer)}"

    max_shift = inst["max_shift"]
    for i, shift in enumerate(answer, start=1):
        if isinstance(shift, bool) or not isinstance(shift, int):
            return False, f"non_integer_shift_at_item_{i}"
        if shift < 0 or shift > max_shift:
            return False, f"shift_out_of_range_at_item_{i}"
    seen: dict[int, int] = {}
    for i, shift in enumerate(answer, start=1):
        if shift in seen:
            return False, f"duplicate_shift_at_items_{seen[shift]}_and_{i}"
        seen[shift] = i

    target = inst["target_length"]
    block_count = inst["n"]
    buckets: list[list[tuple[int, int, int]]] = [[] for _ in range(block_count)]
    for item, (shift, length) in enumerate(zip(answer, lengths), start=1):
        block = shift // (target + 1)
        offset = shift - block * (target + 1)
        if block >= block_count or offset >= target:
            return False, f"interval_starts_outside_target_at_item_{item}"
        end = shift + length - 1
        block_end = block * (target + 1) + target - 1
        if end > block_end:
            return False, f"interval_crosses_block_boundary_at_item_{item}"
        buckets[block].append((shift, end, item))

    # The total input length equals the target support size.  Exact, disjoint
    # coverage is therefore equivalent to the required pointwise mod-2 sum.
    for block, intervals in enumerate(buckets):
        cursor = block * (target + 1)
        block_end = cursor + target - 1
        for start, end, _item in sorted(intervals):
            if start < cursor:
                return False, f"overlap_in_block_{block}_at_coordinate_{start}"
            if start > cursor:
                return False, f"gap_in_block_{block}_at_coordinate_{cursor}"
            cursor = end + 1
        if cursor <= block_end:
            return False, f"uncovered_suffix_in_block_{block}_at_coordinate_{cursor}"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniformly sample an ordered vector of distinct in-range shifts."""
    item_count = len(inst["lengths"])
    population = inst["max_shift"] + 1
    return rng.sample(range(population), item_count)


def search_space(inst) -> int | None:
    """Count all syntactically valid ordered vectors of distinct shifts."""
    population = inst["max_shift"] + 1
    item_count = len(inst["lengths"])
    if population < item_count:
        return 0
    return math.prod(range(population - item_count + 1, population + 1))


def _sum_triples(lengths: list[int], target: int):
    positions: dict[int, list[int]] = {}
    for i, value in enumerate(lengths):
        positions.setdefault(value, []).append(i)
    triples: list[tuple[int, int, int]] = []
    by_item: list[list[int]] = [[] for _ in lengths]
    for i in range(len(lengths) - 2):
        for j in range(i + 1, len(lengths) - 1):
            needed = target - lengths[i] - lengths[j]
            for k in positions.get(needed, ()):
                if k > j:
                    edge_id = len(triples)
                    triple = (i, j, k)
                    triples.append(triple)
                    for item in triple:
                        by_item[item].append(edge_id)
    return triples, by_item


def enumerate_all(inst) -> int | None:
    """Exactly count valid shift vectors when bounded exact-cover search is small."""
    lengths = inst["lengths"]
    item_count = len(lengths)
    if item_count > 18:
        return None

    triples, by_item = _sum_triples(lengths, inst["target_length"])
    edge_masks = [sum(1 << item for item in edge) for edge in triples]
    state_cap = 2_000_000
    states = 0

    class _CapReached(Exception):
        pass

    @lru_cache(maxsize=None)
    def count_partitions(mask: int) -> int:
        nonlocal states
        states += 1
        if states > state_cap:
            raise _CapReached
        if mask == 0:
            return 1
        lowest_bit = mask & -mask
        pivot = lowest_bit.bit_length() - 1
        total = 0
        for edge_id in by_item[pivot]:
            edge_mask = edge_masks[edge_id]
            if mask & edge_mask == edge_mask:
                total += count_partitions(mask ^ edge_mask)
        return total

    try:
        partitions = count_partitions((1 << item_count) - 1)
    except _CapReached:
        return None
    block_count = inst["n"]
    # Each unordered item partition can be assigned to labelled blocks in n!
    # ways and ordered left-to-right inside every block in 3! ways.
    return partitions * math.factorial(block_count) * (math.factorial(3) ** block_count)


def _groups_to_answer(inst, groups) -> list[int] | None:
    """Convert disjoint sum-T triples to shifts, using public data only."""
    if len(groups) != inst["n"]:
        return None
    lengths = inst["lengths"]
    target = inst["target_length"]
    answer = [None] * len(lengths)
    used: set[int] = set()
    for block, group in enumerate(groups):
        if len(group) != 3 or sum(lengths[i] for i in group) != target:
            return None
        cursor = block * (target + 1)
        for item in group:
            if item in used or item < 0 or item >= len(lengths):
                return None
            used.add(item)
            answer[item] = cursor
            cursor += lengths[item]
    if len(used) != len(lengths):
        return None
    return answer


def _attack_degree_outlier(inst) -> list[int] | None:
    """Exploit low per-item triple degree, then make no backtracking choices."""
    lengths = inst["lengths"]
    triples, by_item = _sum_triples(lengths, inst["target_length"])
    remaining = set(range(len(lengths)))
    groups = []
    global_degree = [len(edges) for edges in by_item]
    while remaining:
        choices = []
        for item in remaining:
            available = [
                edge_id
                for edge_id in by_item[item]
                if all(v in remaining for v in triples[edge_id])
            ]
            if not available:
                return None
            choices.append((len(available), item, available))
        _, _pivot, available = min(choices)
        edge_id = min(
            available,
            key=lambda e: (
                sum(global_degree[v] for v in triples[e]),
                triples[e],
            ),
        )
        edge = triples[edge_id]
        groups.append(edge)
        remaining.difference_update(edge)
    return _groups_to_answer(inst, groups)


def _attack_largest_first(inst) -> list[int] | None:
    """Largest-first greedy grouping with the first exact complement pair."""
    lengths = inst["lengths"]
    target = inst["target_length"]
    remaining = set(range(len(lengths)))
    groups = []
    while remaining:
        first = max(remaining, key=lambda i: (lengths[i], -i))
        rest = sorted(remaining - {first}, key=lambda i: (lengths[i], i))
        found = None
        for pos, second in enumerate(rest):
            for third in rest[pos + 1 :]:
                if lengths[first] + lengths[second] + lengths[third] == target:
                    found = (first, second, third)
                    break
            if found is not None:
                break
        if found is None:
            return None
        groups.append(found)
        remaining.difference_update(found)
    return _groups_to_answer(inst, groups)


def _public_attack_seed(inst, salt: int) -> int:
    value = salt & ((1 << 64) - 1)
    for i, length in enumerate(inst["lengths"], start=1):
        value = (value * 6364136223846793005 + i * length + 1442695040888963407) & (
            (1 << 64) - 1
        )
    return value


def _attack_random_restart(inst, restarts: int = 256) -> list[int] | None:
    """Random compatible-triple greedy search, restarted without backtracking."""
    lengths = inst["lengths"]
    triples, by_item = _sum_triples(lengths, inst["target_length"])
    rng = random.Random(_public_attack_seed(inst, 0xA17AC))
    for _ in range(restarts):
        remaining = set(range(len(lengths)))
        groups = []
        while remaining:
            pivot = rng.choice(sorted(remaining))
            available = [
                edge_id
                for edge_id in by_item[pivot]
                if all(v in remaining for v in triples[edge_id])
            ]
            if not available:
                break
            edge = triples[rng.choice(available)]
            groups.append(edge)
            remaining.difference_update(edge)
        if not remaining:
            return _groups_to_answer(inst, groups)
    return None


def _swap_corruption(inst, planted: list[int]) -> list[int]:
    target = inst["target_length"]
    lengths = inst["lengths"]
    by_block: dict[int, list[int]] = {}
    for item, shift in enumerate(planted):
        by_block.setdefault(shift // (target + 1), []).append(item)
    for items in by_block.values():
        for i, j in combinations(items, 2):
            if lengths[i] != lengths[j]:
                result = planted.copy()
                result[i], result[j] = result[j], result[i]
                return result
    raise AssertionError("generator unexpectedly produced no unequal pair to swap")


def selftest() -> dict:
    """Run gates G1--G7 and return all measurements without printing."""
    report: dict = {}

    # G1: every preset, four independent seeds.
    g1_failures = []
    g1_seeds = (0, 1, 7, 19)
    for preset, kwargs in DIFFICULTY.items():
        for seed in g1_seeds:
            inst = make_instance(seed=seed, **kwargs)
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "tested": len(DIFFICULTY) * len(g1_seeds),
        "failures": g1_failures,
    }

    hard = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = hard["answer"]

    # G2: five corruption classes, with distinct diagnostic reasons.
    duplicate = planted.copy()
    duplicate[1] = duplicate[0]
    out_of_range = planted.copy()
    out_of_range[0] = hard["max_shift"] + 1
    corruptions = {
        "drop_one": planted[:-1],
        "swap_pair": _swap_corruption(hard, planted),
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    g2_results = {name: verify(hard, value) for name, value in corruptions.items()}
    g2_reasons = {name: result[1] for name, result in g2_results.items()}
    g2_pass = all(not result[0] for result in g2_results.values()) and len(
        set(g2_reasons.values())
    ) == len(corruptions)
    report["G2_rejects_corruption"] = {
        "pass": g2_pass,
        "reasons": g2_reasons,
    }

    # G3: realistic fenced, prose-surrounded response.
    response = (
        "I checked the translations against every block.\n\n```json\n"
        + "<answer>\n"
        + json.dumps(planted)
        + "\n</answer>\n```\nThat is my final witness."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_length": len(parsed) if isinstance(parsed, list) else None,
    }

    # G4: required empirical random-guess measurement.
    guess_rng = random.Random(0x250301929)
    trials = 200_000
    hits = 0
    for _ in range(trials):
        candidate = random_candidate(hard, guess_rng)
        if verify(hard, candidate)[0]:
            hits += 1
    report["G4_guess_resistance"] = {
        "pass": hits / trials < 1e-6,
        "hits": hits,
        "total": trials,
        "empirical_probability": hits / trials,
        "search_space": search_space(hard),
    }

    # G5: exact enumeration on a deliberately small member of the same family.
    small = make_instance(4, seed=11, width_factor=0.5)
    valid_count = enumerate_all(small)
    small_space = search_space(small)
    fraction = None if valid_count is None else valid_count / small_space
    report["G5_sparse"] = {
        "pass": valid_count is not None and 0 < fraction < 1e-6,
        "n": small["n"],
        "valid_answers": valid_count,
        "search_space": small_space,
        "solution_fraction": fraction,
    }

    # G6: eight unseen generators and three generator-aware cheap attacks.
    attack_functions = {
        "per_item_degree_outlier": _attack_degree_outlier,
        "largest_first_greedy": _attack_largest_first,
        "random_restart_256": _attack_random_restart,
    }
    attack_seeds = tuple(range(8))
    attack_report = {}
    for name, attack in attack_functions.items():
        per_seed = []
        successes = 0
        for seed in attack_seeds:
            inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
            candidate = attack(inst)
            solved = candidate is not None and verify(inst, candidate)[0]
            successes += int(solved)
            per_seed.append({"seed": seed, "solved": solved})
        attack_report[name] = {
            "successes": successes,
            "attempts": len(attack_seeds),
            "per_seed": per_seed,
        }
    report["G6_adversary_panel"] = {
        "pass": all(entry["successes"] == 0 for entry in attack_report.values()),
        "attacks": attack_report,
    }

    # G7: double n at the shipping parameters and check construction plus G1.
    doubled = make_instance(
        2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        seed=271828,
        width_factor=DIFFICULTY[SHIPPING_DIFFICULTY]["width_factor"],
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    hard_space = search_space(hard)
    doubled_space = search_space(doubled)
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_space > hard_space,
        "shipping_n": hard["n"],
        "doubled_n": doubled["n"],
        "shipping_items": len(hard["lengths"]),
        "doubled_items": len(doubled["lengths"]),
        "shipping_search_bits": hard_space.bit_length(),
        "doubled_search_bits": doubled_space.bit_length(),
        "doubled_verify": [doubled_ok, doubled_reason],
    }

    report["all_pass"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


NOTES = """
Paper grounding:
- Section 3.2 fixes the exact Quotient Sum Problem: choose translations and a
  subgroup N so shifted finitely supported functions sum to zero in A^(B/N).
- Section 4.1, Proposition 4.2 constructs the h=0 interval-lamp instance from
  3-PARTITION, and Theorem 4.3 proves NP-hardness for nontrivial A and infinite
  B.  This module fixes A=Z_2, B=Z, h=0 and normalizes the target translation.
- The easy-case exclusions come from Theorem 4.4 (finite B), Theorem 4.20
  (h at least rank(B)), Theorem 4.23 (one function), Theorem 4.24 (bounded
  number of functions), and Section 5's corresponding genus results.

Generator hardening:
- The witness placement order is sampled before lengths.  Every length is drawn
  through the same symmetric rejection sampler; item labels are uniformly
  shuffled, so no plant/decoy distribution split exists.
- The per-item outlier attack uses exact sum-triple degrees and minimum-degree
  propagation; the greedy attack packs the largest remaining length first; the
  random-restart attack makes 256 compatible-triple greedy attempts.  The
  shipped n and width factor were selected only after all three had 0/8 wins.
""".strip()
