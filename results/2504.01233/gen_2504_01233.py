"""Verified generator for the XOR-zero Hamming K4 in arXiv:2504.01233.

Section 3 distinguishes one of the two distance-six K4 types in the 10-cube
by the identity that its four vertices XOR to zero. This module uses that
native finite-cube witness on a scalable Walsh--Hadamard family.
"""

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
    "computational_core": "subset_sum",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "Walsh-Hadamard vertices of a Boolean cube",
        "Hamming distance graph",
        "XOR-zero equidistant four-vertex configuration",
    ],
    "verification_operations": [
        "bitwise XOR of coefficient labels",
        "exact Walsh-code Hamming-distance formula",
        "integer index comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Linearity turns the paper's four-vertex XOR invariant into a four-label "
        "XOR relation, while a whole-list checksum and a rotation symmetry expose "
        "two members; without them one compares quadratically many pairs."
    ),
    "hardness_basis": (
        "Track B: Section 3 supplies the XOR-zero K4 invariant; the reference "
        "pair-XOR collision algorithm is O(N^2) and averaged 4,803 pair "
        "operations (0.00691 seconds total for eight shipping runs), while the "
        "aggregate route measured 224 and takes at most 297 exact word operations "
        "after the invariant is recognized."
    ),
    "max_answer_tokens": 5,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "A strictly increasing JSON array of four distinct 0-based indices "
        "chosen from all four-subsets of the N labels. Every such subset "
        "already obeys the pairwise-distance rule."
    ),
    "bounds": {"indices": 4, "minimum": 0, "maximum": "N-1"},
}

DIFFICULTY = {
    "demo": {"n": 12, "label_bits": 8},
    "easy": {"n": 140, "label_bits": 28},
    "medium": {"n": 144, "label_bits": 36},
    "hard": {"n": 148, "label_bits": 44},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The whole-list XOR checksum and a cyclic bit-rotation symmetry are coupled "
    "to the four-label XOR invariant defining the exceptional quartet."
)
PLACEBO_HINT = (
    "The fixed-width hexadecimal labels are useful for keeping the many exact "
    "pairwise comparisons consistently organized."
)

NOTES = (
    "Section 2 defines G(V;k), with cube vertices adjacent exactly at Hamming "
    "distance k. Section 3 displays the two K4 types for n=10,k=6 and states "
    "that the first type has XOR zero. The paper's coloring subroutine uses "
    "kissat with a one-second cutoff, while its outer configuration enumeration "
    "took about 14 days; no distributional hardness theorem is given, hence "
    "Track B rather than Track A. Here label a denotes the full Walsh cube "
    "vertex W_a(x)=parity(a AND x). Distinct labels are exactly equidistant and "
    "W_a XOR W_b=W_(a XOR b), identities the checker executes symbolically. "
    "Generation samples decoys first, derives a planted quartet whose XOR is "
    "zero, total-list XOR is its first label, and a one-bit cyclic rotation of "
    "that label is its second. Pair-XOR uniqueness removes accidental certificates without "
    "finding the planted answer. Weight-outlier, greedy, random-restart, and "
    "bounded pair-XOR attacks are rejected during construction."
)

# Updated after the isolated harden.py arms are run.
G9_MEASURED_ARMS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}


def _values(inst):
    return [int(text, 16) for text in inst["labels"]]


def _rotate_left(value, width, amount=1):
    amount %= width
    mask = (1 << width) - 1
    return ((value << amount) | (value >> (width - amount))) & mask


def _candidate_valid_values(values, candidate):
    if candidate is None or len(candidate) != 4 or len(set(candidate)) != 4:
        return False
    chosen = [values[i] for i in candidate]
    return chosen[0] ^ chosen[1] ^ chosen[2] ^ chosen[3] == 0


def _structural_ok(values, planted_positions):
    """Prove the known plant is the only XOR-zero four-set.

    Four distinct labels XOR to zero iff two disjoint pairs have equal XOR.
    The planted quartet creates exactly three such collisions. Forbidding all
    others proves uniqueness; it is not how the witness is obtained.
    """
    planted = frozenset(planted_positions)
    seen = {}
    collision_keys = set()
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            key = values[i] ^ values[j]
            pair = (i, j)
            old = seen.get(key)
            if old is None:
                seen[key] = pair
                continue
            if ({old[0], old[1]} & {i, j}) or frozenset(old + pair) != planted:
                return False
            if key in collision_keys:
                return False
            collision_keys.add(key)
    return len(collision_keys) == 3


def _attack_outlier_weight(inst):
    values = _values(inst)
    middle = inst["label_bits"] / 2
    picked = sorted(
        sorted(range(len(values)),
               key=lambda i: (-abs(values[i].bit_count() - middle), i))[:4]
    )
    return picked if _candidate_valid_values(values, picked) else None


def _attack_greedy_low_labels(inst):
    values = _values(inst)
    lookup = {value: i for i, value in enumerate(values)}
    order = sorted(range(len(values)), key=lambda i: values[i])
    a, b = order[:2]
    for c in order[2:18]:
        d = lookup.get(values[a] ^ values[b] ^ values[c])
        if d is not None and len({a, b, c, d}) == 4:
            candidate = sorted([a, b, c, d])
            if _candidate_valid_values(values, candidate):
                return candidate
    return None


def _attack_random_restart(inst, trials=256):
    values = _values(inst)
    attack_seed = (values[0] ^ values[-1] ^ len(values)
                   ^ inst["label_bits"]) & ((1 << 64) - 1)
    rng = random.Random(attack_seed)
    for _ in range(trials):
        candidate = sorted(rng.sample(range(len(values)), 4))
        if _candidate_valid_values(values, candidate):
            return candidate
    return None


def _attack_bounded_pair_xor(inst, budget=256):
    values = _values(inst)
    seen = {}
    inspected = 0
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            if inspected >= budget:
                return None
            inspected += 1
            key = values[i] ^ values[j]
            old = seen.get(key)
            if old is None:
                seen[key] = (i, j)
                continue
            candidate = sorted({old[0], old[1], i, j})
            if len(candidate) == 4 and _candidate_valid_values(values, candidate):
                return candidate
    return None


def _cheap_attacks_fail(inst):
    return all(attack(inst) is None for attack in (
        _attack_outlier_weight,
        _attack_greedy_low_labels,
        _attack_random_restart,
        _attack_bounded_pair_xor,
    ))


def make_instance(n, seed=0, **params):
    """Inverse-generate one unique XOR-zero quartet of Walsh cube vertices."""
    n = int(n)
    label_bits = int(params.get("label_bits", 24))
    if n < 8:
        raise ValueError("n must be at least 8")
    if label_bits < 6 or n >= (1 << label_bits):
        raise ValueError("label_bits must encode at least n distinct labels")
    rng = random.Random(seed)
    modulus = 1 << label_bits
    width = (label_bits + 3) // 4

    for _attempt in range(20000):
        decoys = []
        used = set()
        while len(decoys) < n - 4:
            value = rng.getrandbits(label_bits)
            if value not in used:
                used.add(value)
                decoys.append(value)

        # Compose three exact identities before inserting the plant:
        # p0^p1^p2^p3=0, XOR(all)=p0, ROTL_1(p0)=p1.
        p0 = 0
        for value in decoys:
            p0 ^= value
        p1 = _rotate_left(p0, label_bits)
        p2 = rng.getrandbits(label_bits)
        p3 = p0 ^ p1 ^ p2
        planted = [p0, p1, p2, p3]
        if len(set(planted)) != 4 or any(value in used for value in planted):
            continue
        values = planted + decoys
        if not _structural_ok(values, range(4)):
            continue

        order = list(range(n))
        rng.shuffle(order)
        shuffled = [values[i] for i in order]
        inverse = {old: new for new, old in enumerate(order)}
        inst = {
            "label_bits": label_bits,
            "ambient_dimension": modulus,
            "distance": modulus // 2,
            "labels": [format(value, "0{}X".format(width)) for value in shuffled],
            "answer": sorted(inverse[i] for i in range(4)),
        }
        if n < DIFFICULTY["easy"]["n"] or _cheap_attacks_fail(inst):
            return inst
    raise RuntimeError("could not construct a filtered planted instance")


def render(inst):
    m = inst["label_bits"]
    lines = [
        "XOR-zero equidistant quartet of Walsh cube vertices", "",
        "For each displayed {}-bit hexadecimal label a, define a Boolean-cube".format(m),
        "vertex W_a with one coordinate for every {}-bit word x. Its coordinate".format(m),
        "at x is parity(a AND x): 0 when a AND x has even popcount, otherwise 1.",
        "Thus W_a lies in {{0,1}}^D, where D = 2^{} = {}.".format(
            m, inst["ambient_dimension"]),
        "All listed labels are distinct. For distinct a,b, W_a and W_b differ",
        "in exactly D/2 = {} coordinates, and W_a XOR W_b = W_(a XOR b).".format(
            inst["distance"]),
        "These identities follow directly from the definition: every nonzero",
        "linear parity is 0 on half of all x and 1 on the other half.", "",
        "Find four distinct listed labels whose corresponding cube vertices have",
        "bitwise XOR equal to the all-zero D-bit vertex. Their six pairwise",
        "Hamming distances are then (as for every four-subset here) exactly D/2,",
        "so they form the XOR-zero analogue of the paper's exceptional K4 type.", "",
        "Labels are indexed from 0. Give each index once, in strictly increasing",
        "order. Input order has no mathematical significance. Hex labels are",
        "unsigned integers; leading zeroes are retained only for fixed width.", "",
        "Labels:",
    ]
    lines.extend("{}: {}".format(i, value) for i, value in enumerate(inst["labels"]))
    lines.extend([
        "", "Give your final answer inside <answer></answer> tags, as a JSON array",
        "of exactly four strictly increasing 0-based indices.",
        "Example: <answer>[1, 3, 7, 10]</answer>",
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
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        answer = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(answer, list) or not all(
            isinstance(item, int) and not isinstance(item, bool) for item in answer):
        return None
    return answer


def verify(inst, answer):
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if len(answer) == 0:
        return False, "answer is empty"
    if not all(isinstance(item, int) and not isinstance(item, bool) for item in answer):
        return False, "every index must be an integer"
    if len(answer) != 4:
        return False, "answer must contain exactly four indices"
    if len(set(answer)) != 4:
        return False, "indices must be distinct"
    if answer != sorted(answer):
        return False, "indices must be strictly increasing"
    if answer[0] < 0 or answer[-1] >= len(inst["labels"]):
        return False, "index out of range"

    values = _values(inst)
    for a in range(4):
        for b in range(a + 1, 4):
            difference = values[answer[a]] ^ values[answer[b]]
            got = 0 if difference == 0 else inst["ambient_dimension"] // 2
            if got != inst["distance"]:
                return False, "pair ({},{}) has Hamming distance {}, expected {}".format(
                    answer[a], answer[b], got, inst["distance"])
    xor_value = 0
    for index in answer:
        xor_value ^= values[index]
    if xor_value:
        return False, "quartet XOR is nonzero"
    return True, "ok"


def random_candidate(inst, rng):
    return sorted(rng.sample(range(len(inst["labels"])), 4))


def search_space(inst):
    return math.comb(len(inst["labels"]), 4)


def enumerate_all(inst):
    if search_space(inst) > 250000:
        return None
    return sum(verify(inst, list(c))[0]
               for c in itertools.combinations(range(len(inst["labels"])), 4))


def _affine_rank(values):
    if not values:
        return 0
    basis = {}
    for value in (v ^ values[0] for v in values[1:]):
        while value:
            bit = value.bit_length() - 1
            if bit in basis:
                value ^= basis[bit]
            else:
                basis[bit] = value
                break
    return len(basis)


def canonical_key(inst):
    """Strong cheap affine invariant, not a complete affine canonical form."""
    values = _values(inst)
    buckets = {}
    for triple in itertools.combinations(range(len(values)), 3):
        key = values[triple[0]] ^ values[triple[1]] ^ values[triple[2]]
        old = buckets.get(key)
        if old is None:
            buckets[key] = triple
        elif isinstance(old, tuple):
            buckets[key] = [old, triple]
        else:
            old.append(triple)
    involvement = [0] * len(values)
    bucket_sizes = []
    for group in buckets.values():
        if isinstance(group, tuple):
            continue
        bucket_sizes.append(len(group))
        for left, right in itertools.combinations(group, 2):
            symmetric = set(left) ^ set(right)
            if len(symmetric) == 6:
                for index in symmetric:
                    involvement[index] += 1
    payload = json.dumps({
        "n": len(values), "m": inst["label_bits"],
        "affine_rank": _affine_rank(values),
        "triple_bucket_sizes": sorted(bucket_sizes),
        "six_relation_involvement": sorted(involvement),
    }, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params):
    p = {k: v for k, v in dict(params).items() if k != "_preset"}
    p["label_bits"] = int(p.get("label_bits", 48)) * 2
    return p


def _pair_xor_reference(inst):
    values = _values(inst)
    seen = {}
    pair_operations = 0
    collision_checks = 0
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            pair_operations += 1
            key = values[i] ^ values[j]
            old = seen.get(key)
            if old is None:
                seen[key] = (i, j)
                continue
            collision_checks += 1
            candidate = sorted({old[0], old[1], i, j})
            if len(candidate) == 4 and _candidate_valid_values(values, candidate):
                return candidate, pair_operations, collision_checks
    return None, pair_operations, collision_checks


def _aggregate_route(inst):
    values = _values(inst)
    xor_total = values[0]
    operations = 0
    for value in values[1:]:
        xor_total ^= value
        operations += 1
    rotated = _rotate_left(xor_total, inst["label_bits"])
    operations += 1
    lookup = {value: index for index, value in enumerate(values)}
    first = lookup.get(xor_total)
    second = lookup.get(rotated)
    if first is None or second is None or first == second:
        return None, operations
    pair_target = xor_total ^ rotated
    operations += 1
    for third, value in enumerate(values):
        if third in (first, second):
            continue
        fourth = lookup.get(pair_target ^ value)
        operations += 1
        if fourth is not None and len({first, second, third, fourth}) == 4:
            candidate = sorted([first, second, third, fourth])
            if _candidate_valid_values(values, candidate):
                return candidate, operations
    return None, operations


def _permute_label_bits(value, permutation):
    out = 0
    for old, new in enumerate(permutation):
        if (value >> old) & 1:
            out |= 1 << new
    return out


def _transformed(inst, order=None, bit_permutation=None, translation=0,
                 shear=None):
    values = _values(inst)
    if bit_permutation is not None:
        values = [_permute_label_bits(value, bit_permutation) for value in values]
    if shear is not None:
        source, target = shear
        values = [value ^ (((value >> source) & 1) << target) for value in values]
    if translation:
        values = [value ^ translation for value in values]
    if order is None:
        order = list(range(len(values)))
    inverse = {old: new for new, old in enumerate(order)}
    width = (inst["label_bits"] + 3) // 4
    return {
        "label_bits": inst["label_bits"],
        "ambient_dimension": inst["ambient_dimension"],
        "distance": inst["distance"],
        "labels": [format(values[i], "0{}X".format(width)) for i in order],
        "answer": sorted(inverse[i] for i in inst["answer"]),
    }


def selftest():
    report = {}
    planted_checks = json_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError((preset, seed, reason))
            planted_checks += 1
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                raise AssertionError("answer is not JSON-native")
            json_checks += 1
    report["G1_planted_verifies"] = {
        "pass": True, "checks": planted_checks, "json_native_checks": json_checks}

    inst = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = inst["answer"]
    corruptions = {
        "empty": [], "drop_one": answer[:-1],
        "swap_order": [answer[1], answer[0], answer[2], answer[3]],
        "duplicate": [answer[0], answer[0], answer[2], answer[3]],
        "out_of_range": [answer[0], answer[1], answer[2], len(inst["labels"])],
    }
    reasons = {}
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        if ok:
            raise AssertionError("corruption accepted: " + name)
        reasons[name] = reason
    if len(set(reasons.values())) != len(reasons):
        raise AssertionError("corruptions did not receive distinct reasons")
    report["G2_rejects_corruption"] = {
        "pass": True, "rejected": len(reasons), "reasons": reasons}

    model_text = "Reasoning omitted.\n```json\n<answer>{}</answer>\n```".format(
        json.dumps(answer))
    parsed = parse_answer(model_text)
    report["G3_round_trip"] = {"pass": parsed == answer, "parsed": parsed}

    samples = 200000
    guess_rng = random.Random(20260905)
    hits = sum(verify(inst, random_candidate(inst, guess_rng))[0]
               for _ in range(samples))
    exact_valid = 1
    exact_probability = exact_valid / search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": exact_probability < 1e-6 and hits / samples < 1e-6,
        "hits": hits, "total": samples, "sampled_fraction": hits / samples,
        "exact_valid_answers": exact_valid, "search_space": search_space(inst),
        "exact_probability": exact_probability,
        "sampler": "uniform over all four-subsets; all are automatically equidistant",
    }

    start = time.perf_counter()
    reference_answer, pair_ops, collision_checks = _pair_xor_reference(inst)
    reference_wall = time.perf_counter() - start
    ref_ok = reference_answer is not None and verify(inst, reference_answer)[0]
    report["G5_density_and_baseline"] = {
        "pass": exact_probability < 1e-6 and ref_ok,
        "shipping_valid_answer_count": exact_valid,
        "shipping_solution_density": exact_probability,
        "density_sample_hits": hits, "density_sample_total": samples,
        "baseline_wall_clock_seconds": reference_wall,
        "baseline_pair_operations": pair_ops,
        "baseline_collision_checks": collision_checks,
    }

    attacks = {name: {"successes": 0, "attempts": 0} for name in (
        "outlier_label_weight", "greedy_two_lowest_labels",
        "random_restart_256", "lexicographic_pair_xor_256")}
    attack_functions = {
        "outlier_label_weight": _attack_outlier_weight,
        "greedy_two_lowest_labels": _attack_greedy_low_labels,
        "random_restart_256": _attack_random_restart,
        "lexicographic_pair_xor_256": _attack_bounded_pair_xor,
    }
    reference_successes = reference_operations = 0
    reference_elapsed = 0.0
    for seed in range(8):
        trial = make_instance(seed=9000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, attack in attack_functions.items():
            candidate = attack(trial)
            attacks[name]["attempts"] += 1
            if candidate is not None and verify(trial, candidate)[0]:
                attacks[name]["successes"] += 1
        start = time.perf_counter()
        candidate, operations, _ = _pair_xor_reference(trial)
        reference_elapsed += time.perf_counter() - start
        reference_operations += operations
        if candidate is not None and verify(trial, candidate)[0]:
            reference_successes += 1
    all_failed = all(item["successes"] == 0 for item in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8, "attacks": attacks,
        "reference_algorithm": {
            "name": "pair-XOR collision hashing",
            "complexity": "O(N^2) exact word operations and O(N^2) memory",
            "wall_clock_sec_total_8": reference_elapsed,
            "operations_total_8": reference_operations,
            "operations_mean": reference_operations / 8,
            "solves": "{}/8, as expected".format(reference_successes),
        },
    }

    spaces = [math.comb(params["n"], 4) for params in DIFFICULTY.values()]
    doubled_params = {"n": 2 * DIFFICULTY["hard"]["n"], "label_bits": 96}
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": spaces == sorted(spaces) and len(set(spaces)) == 4 and doubled_ok,
        "preset_search_spaces": spaces,
        "size_doubled_n": doubled_params["n"],
        "size_doubled_verifies": doubled_ok,
    }

    invariance_checks = real_transform_checks = 0
    distinct_keys = set()
    for seed in range(20):
        base = make_instance(seed=12000 + seed, **DIFFICULTY["easy"])
        key = canonical_key(base)
        distinct_keys.add(key)
        trng = random.Random(50000 + seed)
        order = list(range(len(base["labels"])))
        trng.shuffle(order)
        permutation = list(range(base["label_bits"]))
        trng.shuffle(permutation)
        translation = trng.getrandbits(base["label_bits"])
        shear = (0, 1)
        variants = [
            _transformed(base, order=order),
            _transformed(base, bit_permutation=permutation),
            _transformed(base, shear=shear),
            _transformed(base, translation=translation),
            _transformed(base, order=order, bit_permutation=permutation,
                         translation=translation, shear=shear),
        ]
        for variant in variants:
            invariance_checks += 1
            if canonical_key(variant) != key:
                raise AssertionError("canonical key changed under affine relabelling")
            real_transform_checks += 1
            if not verify(variant, variant["answer"])[0]:
                raise AssertionError("carried witness failed under affine relabelling")
    report["G8_canonical_key"] = {
        "pass": invariance_checks == 100 and real_transform_checks == 100
        and len(distinct_keys) == 20,
        "invariance_checks": invariance_checks,
        "real_transformation_checks": real_transform_checks,
        "unrelated_distinct": len(distinct_keys), "unrelated_attempts": 20,
        "invariant": "affine rank plus triple-XOR collision profile",
    }

    route_answer, route_operations = _aggregate_route(inst)
    encoded = json.dumps(answer)
    answer_tokens = max(1, math.ceil(len(encoded) / 4))
    within_caps = len(encoded) <= 2000 and len(answer) <= 256 and route_operations <= 300
    hinted_rate = G9_MEASURED_ARMS["hinted"]["solved"] / max(
        1, G9_MEASURED_ARMS["hinted"]["attempts"])
    placebo_rate = G9_MEASURED_ARMS["placebo"]["solved"] / max(
        1, G9_MEASURED_ARMS["placebo"]["attempts"])
    report["G9_no_tool_suitability"] = {
        "pass": within_caps, "arms": G9_MEASURED_ARMS,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": (
            "hardened" if G9_MEASURED_ARMS["hinted"]["attempts"]
            and G9_MEASURED_ARMS["hinted"]["solved"] == 0 else "not_yet_run"),
        "answer_chars": len(encoded), "answer_tokens": answer_tokens,
        "answer_elements": len(answer),
        "intended_route_operations": route_operations,
        "route_verified": route_answer is not None and verify(inst, route_answer)[0],
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }
    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G"))
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
