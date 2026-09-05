"""Verified Grouped 2-way Partition instances from arXiv:2603.12999.

Each displayed group contains two near-equal integers.  A witness chooses one
integer per group for the first part; the other integers form the second part.
The generator composes equal-pair-sum identities among the groups' hidden
half-differences, so it knows an equal-load partition without solving one.
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


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # The family itself needs only the standard library.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "optimization",
    "object_regime": "finite_discrete",
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "groups of near-equal positive integer item sizes",
        "two equal-capacity bins",
        "a balanced grouped partition",
    ],
    "verification_operations": [
        "exact integer selection",
        "exact integer addition",
        "exact equality comparison of bin loads",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "After cancelling each group's common centre, the half-differences "
        "decompose into quartets whose extreme pair and middle pair have the "
        "same sum; without that decomposition one faces a signed subset-sum DP."
    ),
    "hardness_basis": (
        "Track B: Section 2.3 gives a pseudopolynomial dynamic program, and the "
        "n=144 (q=72) shipping preset's centre-normalised word-parallel subset-sum DP solves "
        "8/8 instances in O(qD/word_size) time, taking 2.67 seconds total "
        "and at most 33,300,648 64-bit word operations on the measured seeds; "
        "the compact quartet route uses 180 exact arithmetic operations."
    ),
    "max_answer_tokens": 37,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 8, "spread": 40, "tag_mod": 100},
    "easy": {"n": 144, "spread": 2000, "tag_mod": 1000},
    "medium": {"n": 184, "spread": 3000, "tag_mod": 1000},
    "hard": {"n": 216, "spread": 4000, "tag_mod": 1000},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The within-group half-differences decompose into same-suffix quartets "
    "whose two extreme values and two middle values have equal sums."
)
PLACEBO_HINT = (
    "The grouped item choices reward careful attention to exact values, "
    "indexing conventions, and the requested output format."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A list of exactly q bits in displayed group order; bit i is 0 or 1 "
        "and selects that zero-based item from group i for bin A."
    ),
    "bounds": {
        "choices_per_group": 2,
        "answer_length": "q=n/2",
        "shipping_answer_length": DIFFICULTY[SHIPPING_DIFFICULTY]["n"] // 2,
        "coefficient_set": [0, 1],
    },
}

NOTES = r"""
Section 2.3 and Appendix A fix the exact source problem.  Grouped k-way
Partition has groups G_i of ks near-W integers; every one of the k parts must
take exactly s members of every group and all part sums must equal the average.
This module uses the native k=2, s=1 regime, so a witness is exactly one item
from every displayed two-item group.  Theorem 2.2 gives the SETH lower bound,
but it is a worst-case statement and does not establish hardness of this
inverse-generated distribution.

The same Section 2.3 explicitly states the n^{O(1)} W^{k-1}
pseudopolynomial dynamic-programming upper bound (footnote 7).  That answers
the certificate-producing-algorithm question: centre the two values in every
group, reduce to signed subset sum, and run exact reachability DP.  Therefore
the family is Track B, never Track A.  selftest measures a word-parallel form
of this DP at the shipping preset and requires it to recover a verified witness
on all eight seeds.

Generation is composition of identities, not search.  For each four-group
block it samples positive half-differences with high parts
u, u+a, u+b, u+a+b and one common low tag.  The extremes and the middles have
equal sum.  Independently chosen signs orient each identity, group centres and
item orders are random, and the groups are globally shuffled.  Adding the
oriented identities makes the selected deviations sum to zero by construction.
The common scale W=n^10*max_deficit then puts every integer in the paper's
required interval [W(1-1/n^10), W].

The attack panel tests smaller-item and median-magnitude outliers, signed-load
greed, alternating signs after sorting, a suffix-only positional ansatz, and
256 structure-aware random restarts.  The first-item choice, quartet
orientation, item order, group order, and centre noise are independently
randomised so those probes do not inherit the planted witness.  The exact DP
is disclosed separately as the successful Track-B reference algorithm.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 1 << 18
_WORD_BITS = 64


def _validate_parameters(n, spread, tag_mod):
    if isinstance(n, bool) or not isinstance(n, int) or n < 8 or n % 8:
        raise ValueError("n must be an integer multiple of 8 and at least 8")
    if isinstance(spread, bool) or not isinstance(spread, int) or spread < 16:
        raise ValueError("spread must be an integer at least 16")
    if isinstance(tag_mod, bool) or not isinstance(tag_mod, int) or tag_mod < 16:
        raise ValueError("tag_mod must be an integer at least 16")
    blocks = n // 8
    if blocks >= tag_mod:
        raise ValueError("tag_mod must exceed the number of four-group blocks")


def make_instance(n, seed=0, **params):
    """Inverse-generate a native Grouped 2-way Partition instance."""
    spread = int(params.get("spread", 2000))
    tag_mod = int(params.get("tag_mod", 1000))
    _validate_parameters(n, spread, tag_mod)
    rng = random.Random(seed)
    q = n // 2
    block_count = q // 4

    tags = rng.sample(range(1, tag_mod), block_count)
    entries = []
    for block, tag in enumerate(tags):
        # {u,u+a,u+b,u+a+b} has the exact identity
        # u+(u+a+b)=(u+a)+(u+b).  No solving occurs here.
        quarter = max(3, spread // 4)
        while True:
            u = rng.randint(1, max(2, spread // 2))
            a = rng.randint(1, quarter)
            b = rng.randint(1, quarter)
            if a != b and u + a + b <= spread:
                break
        highs = [u, u + a, u + b, u + a + b]
        order = sorted(range(4), key=lambda j: highs[j])
        extremes = {order[0], order[3]}
        orientation = rng.choice((-1, 1))
        for j, high in enumerate(highs):
            d = high * tag_mod + tag
            identity_sign = 1 if j in extremes else -1
            entries.append((d, orientation * identity_sign, block))

    rng.shuffle(entries)
    used_offsets = set()
    raw_groups = []
    planted_signs = []
    centre_floor = (spread + 2) * tag_mod
    centre_noise = max(tag_mod * spread, q * 32)
    for d, sign, _block in entries:
        for _ in range(10000):
            centre_deficit = d + centre_floor + rng.randrange(centre_noise)
            offsets = (centre_deficit - d, centre_deficit + d)
            if offsets[0] > 0 and not (set(offsets) & used_offsets):
                used_offsets.update(offsets)
                break
        else:
            raise RuntimeError("could not sample distinct item offsets")
        raw_groups.append((centre_deficit, d, sign, offsets))
        planted_signs.append(sign)

    max_deficit = max(max(offsets) for _, _, _, offsets in raw_groups)
    W = max_deficit * (n ** 10)
    groups = []
    answer = []
    for centre_deficit, d, sign, offsets in raw_groups:
        # Relative to the group centre, W-(c-d) is +d and W-(c+d) is -d.
        plus_value = W - offsets[0]
        minus_value = W - offsets[1]
        pair = [plus_value, minus_value]
        if rng.randrange(2):
            pair.reverse()
        groups.append(pair)
        wanted = plus_value if sign == 1 else minus_value
        answer.append(pair.index(wanted))

    target = sum((pair[0] + pair[1]) // 2 for pair in groups)
    inst = {
        "family": "Grouped 2-way Partition",
        "n": n,
        "q": q,
        "k": 2,
        "s": 1,
        "W": W,
        "target": target,
        "tag_mod": tag_mod,
        "groups": groups,
        "answer": answer,
    }
    ok, why = verify(inst, answer)
    if not ok:
        raise AssertionError("constructed witness failed: " + why)
    return inst


def render(inst):
    """Render a self-contained exact grouped-partition problem."""
    groups = inst["groups"]
    lines = [
        "Grouped 2-way Partition (exact integer version)",
        "",
        "There are two labelled bins, A and B, and q displayed groups.  Each",
        "group contains exactly two positive integer items.  Choose exactly one",
        "item from every group for bin A; the unchosen item from that group goes",
        "to bin B.  A valid answer makes both bin loads exactly the target shown",
        "below.  Thus every item is used once and item order within a bin is irrelevant.",
        "",
        f"q = {len(groups)} groups ({2 * len(groups)} items total)",
        f"W = {inst['W']}",
        f"target load of EACH bin = {inst['target']}",
        "All item sizes are integers in the inclusive interval",
        f"[W*(1-1/{inst['n']}^10), W], as in the paper's definition.",
        "",
        "Groups are numbered 0 through q-1.  Within each displayed pair the",
        "left item has index 0 and the right item has index 1:",
    ]
    for i, pair in enumerate(groups):
        lines.append(f"{i}: {pair[0]}  {pair[1]}")
    example = "[0" + ",0" * (len(groups) - 1) + "]"
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as one JSON list",
        "of exactly q bits in group order.  Bit i is 0 or 1 and chooses that",
        "zero-based item from group i for bin A; no group may be skipped or repeated.",
        f"Example of the required shape: <answer>{example}</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Parse the last tagged JSON list, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
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
    return value if isinstance(value, list) else None


def _instance_shape(inst):
    try:
        groups = inst["groups"]
        target = inst["target"]
    except (KeyError, TypeError):
        return None, "instance is missing groups or target"
    if not isinstance(groups, list) or not groups:
        return None, "instance groups must be a nonempty list"
    converted = []
    for i, pair in enumerate(groups):
        if (not isinstance(pair, list) or len(pair) != 2
                or any(isinstance(x, bool) or not isinstance(x, int) or x <= 0
                       for x in pair)):
            return None, f"instance group {i} is not a pair of positive integers"
        converted.append((pair[0], pair[1]))
    if isinstance(target, bool) or not isinstance(target, int) or target <= 0:
        return None, "instance target must be a positive integer"
    if sum(a + b for a, b in converted) != 2 * target:
        return None, "instance total is not twice the target"
    return converted, None


def verify(inst, answer):
    """Check any exact balanced grouped partition; never inspect inst['answer']."""
    try:
        groups = inst["groups"]
        target = inst["target"]
    except (KeyError, TypeError):
        return False, "instance is missing groups or target"
    if not isinstance(groups, list) or not groups:
        return False, "instance groups must be a nonempty list"
    q = len(groups)
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) < q:
        return False, f"too few choices: expected {q}, got {len(answer)}"
    if len(answer) > q:
        return False, f"too many choices: expected {q}, got {len(answer)}"
    for i, choice in enumerate(answer):
        if isinstance(choice, bool) or not isinstance(choice, int):
            return False, f"choice {i} must be the integer 0 or 1"
        if choice not in (0, 1):
            return False, f"choice {i} is outside the allowed range 0..1"
    try:
        load_a = sum(pair[answer[i]] for i, pair in enumerate(groups))
        load_b = sum(pair[1 - answer[i]] for i, pair in enumerate(groups))
    except (IndexError, TypeError):
        return False, "instance groups must be pairs of positive integers"
    if load_a + load_b != 2 * target:
        return False, "instance total is not twice the target"
    if load_a != target:
        return False, f"bin A load {load_a} differs from target {target}"
    if load_b != target:
        return False, f"bin B load {load_b} differs from target {target}"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample one legal 0/1 choice per displayed group."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    q = len(inst["groups"])
    bits = rng.getrandbits(q)
    return [(bits >> i) & 1 for i in range(q)]


def search_space(inst):
    return 1 << len(inst["groups"])


def enumerate_all(inst):
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    count = 0
    q = len(inst["groups"])
    for mask in range(space):
        answer = [(mask >> i) & 1 for i in range(q)]
        count += int(verify(inst, answer)[0])
    return count


def _centres_differences(inst):
    centres = []
    differences = []
    higher_choices = []
    for pair in inst["groups"]:
        total = pair[0] + pair[1]
        gap = abs(pair[0] - pair[1])
        if total % 2 or gap % 2:
            raise ValueError("group does not have an integral centre/half-difference")
        centres.append(total // 2)
        differences.append(gap // 2)
        higher_choices.append(0 if pair[0] > pair[1] else 1)
    residual = inst["target"] - sum(centres)
    return centres, differences, higher_choices, residual


def canonical_key(inst):
    """Normalise all solution-preserving relabellings used by this family."""
    _centres, differences, _higher, residual = _centres_differences(inst)
    common = 0
    for value in differences + [abs(residual)]:
        common = math.gcd(common, value)
    common = common or 1
    payload = [
        len(differences),
        residual // common,
        sorted(d // common for d in differences),
    ]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def escalate(params):
    """Increase numeric state range first, then answer length up to the atom cap."""
    harder = dict(params)
    spread = int(harder.get("spread", 2000))
    tag_mod = int(harder.get("tag_mod", 1000))
    n = int(harder.get("n", 144))
    if spread < 8000:
        harder["spread"] = min(8000, spread + max(1000, spread // 2))
        return harder
    if tag_mod < 10000:
        harder["tag_mod"] = min(10000, tag_mod * 2)
        return harder
    if n < 504:
        harder["n"] = min(504, n + 24)
        return harder
    return "cap_bound"


def _answer_from_signs(inst, signs):
    _centres, _differences, higher, _residual = _centres_differences(inst)
    return [higher[i] if signs[i] > 0 else 1 - higher[i]
            for i in range(len(signs))]


def _reference_algorithm(inst):
    """Exact centre-normalised subset-sum DP with block reconstruction."""
    start_time = time.perf_counter()
    _centres, differences, higher, residual = _centres_differences(inst)
    total = sum(differences)
    numerator = total + residual
    if numerator % 2:
        return None, {
            "wall_clock_sec": time.perf_counter() - start_time,
            "word_operations": 0,
            "reconstruction_masks": 0,
            "target_state": None,
        }
    target = numerator // 2
    if target < 0 or target > total:
        return None, {
            "wall_clock_sec": time.perf_counter() - start_time,
            "word_operations": 0,
            "reconstruction_masks": 0,
            "target_state": target,
        }

    block_size = 12
    ranges = [(i, min(i + block_size, len(differences)))
              for i in range(0, len(differences), block_size)]
    before = []
    bits = 1
    limit = (1 << (target + 1)) - 1
    word_operations = 0
    words = (target + _WORD_BITS) // _WORD_BITS
    for lo, hi in ranges:
        before.append(bits)
        for d in differences[lo:hi]:
            bits = (bits | (bits << d)) & limit
            word_operations += words
    if not ((bits >> target) & 1):
        return None, {
            "wall_clock_sec": time.perf_counter() - start_time,
            "word_operations": word_operations,
            "reconstruction_masks": 0,
            "target_state": target,
        }

    selected = [False] * len(differences)
    current = target
    masks_tested = 0
    for block_index in range(len(ranges) - 1, -1, -1):
        lo, hi = ranges[block_index]
        vals = differences[lo:hi]
        subset_sums = [0] * (1 << len(vals))
        found_mask = None
        prior = before[block_index]
        for mask in range(1 << len(vals)):
            if mask:
                low = mask & -mask
                bit = low.bit_length() - 1
                subset_sums[mask] = subset_sums[mask ^ low] + vals[bit]
            masks_tested += 1
            remaining = current - subset_sums[mask]
            if remaining >= 0 and ((prior >> remaining) & 1):
                found_mask = mask
                current = remaining
                break
        if found_mask is None:
            raise AssertionError("bitset reconstruction failed")
        for j in range(len(vals)):
            if (found_mask >> j) & 1:
                selected[lo + j] = True
    if current != 0:
        raise AssertionError("bitset reconstruction did not reach zero")
    answer = [higher[i] if selected[i] else 1 - higher[i]
              for i in range(len(differences))]
    return answer, {
        "wall_clock_sec": time.perf_counter() - start_time,
        "word_operations": word_operations,
        "reconstruction_masks": masks_tested,
        "target_state": target,
    }


def _compact_quartet_algorithm(inst):
    """Execute the intended suffix-quartet route without the planted witness."""
    start = time.perf_counter()
    _centres, differences, _higher, _residual = _centres_differences(inst)
    modulus = int(inst["tag_mod"])
    buckets = {}
    for i, d in enumerate(differences):
        buckets.setdefault(d % modulus, []).append(i)
    signs = [0] * len(differences)
    additions = 0
    for indices in buckets.values():
        if len(indices) != 4:
            return None, {"wall_clock_sec": time.perf_counter() - start,
                          "exact_arithmetic_operations": 2 * len(differences)}
        ordered = sorted(indices, key=lambda i: differences[i])
        signs[ordered[0]] = signs[ordered[3]] = 1
        signs[ordered[1]] = signs[ordered[2]] = -1
        # These are the two exact additions used to confirm the identity.
        if (differences[ordered[0]] + differences[ordered[3]]
                != differences[ordered[1]] + differences[ordered[2]]):
            return None, {"wall_clock_sec": time.perf_counter() - start,
                          "exact_arithmetic_operations": 2 * len(differences) + additions + 2}
        additions += 2
    return _answer_from_signs(inst, signs), {
        "wall_clock_sec": time.perf_counter() - start,
        "exact_arithmetic_operations": 2 * len(differences) + additions,
    }


def _attack_smaller(inst):
    return [0 if pair[0] < pair[1] else 1 for pair in inst["groups"]]


def _attack_median_magnitude(inst):
    _centres, ds, _higher, _residual = _centres_differences(inst)
    median = sorted(ds)[len(ds) // 2]
    signs = [1 if d <= median else -1 for d in ds]
    return _answer_from_signs(inst, signs)


def _attack_greedy(inst):
    _centres, ds, _higher, _residual = _centres_differences(inst)
    signs = [0] * len(ds)
    running = 0
    for i in sorted(range(len(ds)), key=lambda j: (-ds[j], j)):
        sign = -1 if running > 0 else 1
        signs[i] = sign
        running += sign * ds[i]
    return _answer_from_signs(inst, signs)


def _attack_alternating(inst):
    _centres, ds, _higher, _residual = _centres_differences(inst)
    signs = [0] * len(ds)
    for rank, i in enumerate(sorted(range(len(ds)), key=lambda j: (ds[j], j))):
        signs[i] = 1 if rank % 2 == 0 else -1
    return _answer_from_signs(inst, signs)


def _attack_suffix_position(inst):
    _centres, ds, _higher, _residual = _centres_differences(inst)
    modulus = int(inst.get("tag_mod", 1000))
    buckets = {}
    for i, d in enumerate(ds):
        buckets.setdefault(d % modulus, []).append(i)
    signs = [-1] * len(ds)
    for indices in buckets.values():
        for i in sorted(indices)[:len(indices) // 2]:
            signs[i] = 1
    return _answer_from_signs(inst, signs)


def _adversary_panel(params):
    names = (
        "outlier_choose_smaller_item",
        "outlier_median_half_difference",
        "greedy_signed_load_balance",
        "in_context_alternating_differences",
        "suffix_bucket_first_half",
        "random_restart_256",
    )
    attacks = {name: {"successes": 0, "attempts": 8} for name in names}
    reference_successes = 0
    reference_times = []
    reference_words = []
    reference_masks = []
    compact_successes = 0
    compact_times = []
    compact_operations = []
    attack_candidates = 0
    attack_start = time.perf_counter()
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **params)
        candidates = {
            "outlier_choose_smaller_item": _attack_smaller(inst),
            "outlier_median_half_difference": _attack_median_magnitude(inst),
            "greedy_signed_load_balance": _attack_greedy(inst),
            "in_context_alternating_differences": _attack_alternating(inst),
            "suffix_bucket_first_half": _attack_suffix_position(inst),
        }
        for name, candidate in candidates.items():
            attacks[name]["successes"] += int(verify(inst, candidate)[0])
            attack_candidates += 1
        rng = random.Random(seed ^ 0x260312999)
        found = False
        for _ in range(256):
            attack_candidates += 1
            if verify(inst, random_candidate(inst, rng))[0]:
                found = True
                break
        attacks["random_restart_256"]["successes"] += int(found)

        recovered, metrics = _reference_algorithm(inst)
        reference_times.append(metrics["wall_clock_sec"])
        reference_words.append(metrics["word_operations"])
        reference_masks.append(metrics["reconstruction_masks"])
        reference_successes += int(
            recovered is not None and verify(inst, recovered)[0]
        )
        compact, compact_metrics = _compact_quartet_algorithm(inst)
        compact_times.append(compact_metrics["wall_clock_sec"])
        compact_operations.append(compact_metrics["exact_arithmetic_operations"])
        compact_successes += int(compact is not None and verify(inst, compact)[0])
    elapsed = time.perf_counter() - attack_start - sum(reference_times)
    all_failed = all(result["successes"] == 0 for result in attacks.values())
    return {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "failing_attacks_wall_clock_sec": elapsed,
        "failing_attack_candidates_checked": attack_candidates,
        "reference_algorithm": {
            "name": "centre-normalised word-parallel subset-sum dynamic programming",
            "complexity": "O(q*D/word_size) word operations and O(D) bits",
            "wall_clock_sec_total": sum(reference_times),
            "wall_clock_sec_max": max(reference_times),
            "word_operations_total": sum(reference_words),
            "word_operations_max": max(reference_words),
            "reconstruction_masks_total": sum(reference_masks),
            "solves": f"{reference_successes}/8, as expected",
        },
        "intended_compact_route": {
            "name": "same-suffix quartet decomposition",
            "wall_clock_sec_total": sum(compact_times),
            "exact_arithmetic_operations_max": max(compact_operations),
            "solves": f"{compact_successes}/8, as expected",
        },
    }


def _transformed_instance(inst, rng, reorder=False, swap=False,
                          translate=False, scale=1):
    q = len(inst["groups"])
    permutation = list(range(q))
    if reorder:
        rng.shuffle(permutation)
    deltas = [rng.randint(1, 97) if translate else 0 for _ in range(q)]
    groups = []
    answer = []
    for new_i, old_i in enumerate(permutation):
        pair = [scale * (x + deltas[old_i]) for x in inst["groups"][old_i]]
        choice = inst["answer"][old_i]
        do_swap = swap and bool(rng.randrange(2))
        if do_swap:
            pair.reverse()
            choice = 1 - choice
        groups.append(pair)
        answer.append(choice)
    target = scale * (inst["target"] + sum(deltas))
    return {
        "family": inst["family"],
        "n": inst["n"],
        "q": q,
        "k": 2,
        "s": 1,
        "W": max(max(pair) for pair in groups),
        "target": target,
        "tag_mod": inst.get("tag_mod", 1000) * scale,
        "groups": groups,
        "answer": answer,
    }


def _corruption_tests(inst):
    original = list(inst["answer"])
    cases = {}

    dropped = original[:-1]
    cases["drop_one"] = verify(inst, dropped)

    swapped = list(original)
    positions = next(((i, j) for i in range(len(swapped))
                      for j in range(i + 1, len(swapped))
                      if swapped[i] != swapped[j]), None)
    if positions is None:
        swapped[0] = 1 - swapped[0]
    else:
        i, j = positions
        swapped[i], swapped[j] = swapped[j], swapped[i]
    cases["swap_two"] = verify(inst, swapped)

    duplicated = list(original) + [original[0]]
    cases["duplicate_one"] = verify(inst, duplicated)
    cases["empty"] = verify(inst, [])

    out_of_range = list(original)
    out_of_range[0] = 2
    cases["out_of_range"] = verify(inst, out_of_range)

    reasons = [reason for ok, reason in cases.values() if not ok]
    passed = all(not ok for ok, _ in cases.values()) and len(set(reasons)) == len(cases)
    return passed, {
        name: {"rejected": not result[0], "reason": result[1]}
        for name, result in cases.items()
    }


def _count_atoms(value):
    if isinstance(value, dict):
        return sum(_count_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_count_atoms(v) for v in value)
    return 1


# Filled from the isolated harden.py runs after a level holds.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}


def selftest():
    shipping_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    report = {
        "paper": "2603.12999",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": shipping_params,
    }

    verified = 0
    json_native = True
    interval_checks = 0
    for preset_index, (_preset, params) in enumerate(DIFFICULTY.items()):
        for seed in range(3):
            inst = make_instance(seed=10000 * (preset_index + 1) + seed, **params)
            verified += int(verify(inst, inst["answer"])[0])
            json_native = json_native and json.loads(json.dumps(inst["answer"])) == inst["answer"]
            lower_scaled = inst["W"] * (inst["n"] ** 10 - 1)
            denominator = inst["n"] ** 10
            interval_checks += int(all(
                lower_scaled <= value * denominator <= inst["W"] * denominator
                for pair in inst["groups"] for value in pair
            ))
    report["G1_planted_verifies"] = {
        "pass": verified == 12 and json_native and interval_checks == 12,
        "verified": verified,
        "attempts": 12,
        "answers_json_native": json_native,
        "paper_interval_checks": interval_checks,
    }

    shipping = make_instance(seed=424242, **shipping_params)
    g2_pass, corruption_results = _corruption_tests(shipping)
    report["G2_rejects_corruption"] = {
        "pass": g2_pass,
        "cases": corruption_results,
    }

    response = (
        "The centred deviations balance by quartet.\n```json\n<answer>\n"
        + json.dumps(shipping["answer"], separators=(",", ":"))
        + "\n</answer>\n```\nBoth exact loads agree."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and parse_answer("garbage") is None,
        "model_style_response_parsed": parsed is not None,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    rng = random.Random(260312999)
    guess_total = 200000
    guess_hits = 0
    guess_start = time.perf_counter()
    _centres, guess_ds, guess_higher, guess_residual = _centres_differences(shipping)
    for _ in range(guess_total):
        candidate = random_candidate(shipping, rng)
        signed_sum = sum(
            d if candidate[i] == guess_higher[i] else -d
            for i, d in enumerate(guess_ds)
        )
        if signed_sum == guess_residual:
            # The centred equality is algebraically equivalent, and the public
            # verifier rechecks every observed hit against the original integers.
            guess_hits += int(verify(shipping, candidate)[0])
    guess_seconds = time.perf_counter() - guess_start
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "structure_aware_space": str(search_space(shipping)),
        "prior": "uniform over one legal 0/1 choice per displayed group",
        "hit_test": "exact centred-load equality; every hit is rechecked by verify",
        "sampling_wall_clock_sec": guess_seconds,
    }

    panel = _adversary_panel(shipping_params)
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_rate < 1e-6 and demo_count is not None,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_sampled_density": guess_rate,
        "demo_exact_valid_answers": demo_count,
        "demo_candidate_space": search_space(demo),
        "strongest_failing_attack_wall_clock_sec": panel["failing_attacks_wall_clock_sec"],
        "strongest_failing_attack_candidates": panel["failing_attack_candidates_checked"],
        "reference_wall_clock_sec": panel["reference_algorithm"]["wall_clock_sec_total"],
        "reference_word_operations_max": panel["reference_algorithm"]["word_operations_max"],
    }
    report["G6_adversary_panel"] = panel

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=808080, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(shipping),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_groups": len(shipping["groups"]),
        "doubled_groups": len(doubled["groups"]),
        "shipping_search_space_bits": search_space(shipping).bit_length() - 1,
        "doubled_search_space_bits": search_space(doubled).bit_length() - 1,
        "verify_reason": doubled_reason,
    }

    invariance = 0
    carried = 0
    changed = 0
    unrelated = []
    transformations = [
        {"reorder": True},
        {"swap": True},
        {"translate": True},
        {"scale": 3},
        {"reorder": True, "swap": True, "translate": True, "scale": 5},
    ]
    for seed in range(20):
        inst = make_instance(seed=300000 + seed, **shipping_params)
        key = canonical_key(inst)
        unrelated.append(key)
        original_blob = json.dumps(inst["groups"], separators=(",", ":"))
        for t_index, kwargs in enumerate(transformations):
            transformed = _transformed_instance(
                inst, random.Random(400000 + 100 * seed + t_index), **kwargs
            )
            invariance += int(canonical_key(transformed) == key)
            carried += int(verify(transformed, transformed["answer"])[0])
            changed += int(json.dumps(transformed["groups"], separators=(",", ":")) != original_blob)
    report["G8_canonical_key"] = {
        "pass": invariance == 100 and carried == 100
        and changed == 100 and len(set(unrelated)) == 20,
        "invariance_checks": invariance,
        "invariance_attempts": 100,
        "carried_witness_checks": carried,
        "carried_witness_attempts": 100,
        "changed_serializations": changed,
        "unrelated_instances": 20,
        "distinct_keys": len(set(unrelated)),
        "transformations": [
            "group reordering",
            "within-group item swaps",
            "independent group translations with target translation",
            "positive global scaling",
            "composition of all four",
        ],
        "normal_form": "sorted half-differences divided by their common gcd",
    }

    answer_blobs = [
        json.dumps(make_instance(seed=500000 + seed, **shipping_params)["answer"],
                   separators=(",", ":"))
        for seed in range(32)
    ]
    answer_chars = max(map(len, answer_blobs))
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _count_atoms(shipping["answer"])
    q = len(shipping["groups"])
    block_count = q // 4
    intended_operations = 2 * q + 2 * block_count
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
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
        "operation_accounting": (
            "one subtraction and one exact halving per group, plus two pair-sum "
            "additions per quartet"
        ),
        "diagnostic_recorded_not_gated": True,
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
