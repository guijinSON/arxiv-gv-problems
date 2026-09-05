"""Self-contained verified BusOut problem generator for arXiv:2505.09165.

The family is the paper's Theorem 2 reduction, used in the forward direction:
an inversely generated 3-partition is represented by disjoint directed paths of
unit buses and a one-spot, two-colour passenger queue.  The answer is a compact
dispatch schedule (path triples), checked by exact compressed transition replay.
"""

from __future__ import annotations

import copy
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


sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # pragma: no cover - the generator does not require helpers
    exact_matrices = rationals = None


TRACK: str = "B"

# This fixed prime is presentation-independent construction structure.  It is not
# needed by verify(), and the bare problem statement does not reveal it.
MODULUS = 500000003

STRUCTURAL_HINT: str = (
    "Modulo 500000003, the three path lengths assigned to one passenger block "
    "share a residue."
)
PLACEBO_HINT: str = (
    "Track the path identifiers carefully and check every group before finalizing "
    "the dispatch plan."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "congestion graph of disjoint directed bus paths",
        "two-colour passenger queue",
        "compressed BusOut dispatch schedule",
    ],
    "verification_operations": [
        "path-ID range and disjointness checks",
        "exact integer path-length sums",
        "compressed replay of unit-bus dispatch and automatic boarding transitions",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "A hidden common-residue invariant identifies the three paths for each "
        "passenger block; without it, one mechanically indexes pair sums against "
        "every displayed block length."
    ),
    "hardness_basis": (
        "Track B: pair-sum indexing against the block targets followed by exact-cover "
        "propagation solves this generated distribution in O(m^2+bm+z); at shipping "
        "m=246 and b=82 it uses 100,860 exact arithmetic/lookup operations (30,135 "
        "pair builds and 20,172 target probes) and under 0.02 seconds, whereas the "
        "common-residue route uses 246 exact operations but is not mechanically "
        "executable by hand across 246 displayed lengths."
    ),
    "max_answer_tokens": 260,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"]
    + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 2, "target_multiple": 32},
    "easy": {"n": 80, "target_multiple": 80},
    "medium": {"n": 82, "target_multiple": 88},
    "hard": {"n": 84, "target_multiple": 96},
}
SHIPPING_DIFFICULTY: str = "medium"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "An unordered partition of all 3n zero-based path IDs into exactly n "
        "unordered triples.  The JSON representation is a list of n three-integer "
        "lists; canonical ordering is optional."
    ),
    "bounds": {
        "min_groups": 2,
        "max_shipping_groups": 85,
        "triple_size": 3,
        "max_path_id": 254,
        "max_answer_atoms": 255,
    },
}

NOTES: str = (
    "Section 2, especially the two transition bullets, fixes dispatch legality, "
    "automatic priority for passenger boarding, eligibility, and the initially "
    "empty station. Section 3, Theorem 2 fixes the hard native regime and proves "
    "that a clearing schedule is exactly a 3-partition when there is one spot, two "
    "colours, capacity one, and disjoint directed paths. Theorem 1 makes one colour "
    "trivial; Theorem 6 gives polynomial reachability for edgeless graphs with fixed "
    "spot/colour/capacity parameters; Theorem 7 makes edgeless instances trivial "
    "when spots are at least colours. Those regimes are avoided. The answer is "
    "sampled first. Each sampled triple receives one common modular residue, then an "
    "invertible residue scaling, random quotients, varying passenger-block totals, "
    "and a random path relabelling hide the groups. Magnitudes and display positions "
    "therefore do not mark a special subset. Input-order, magnitude, balanced-rank, "
    "and random-restart attacks fail; the successful quadratic reference algorithm "
    "is disclosed because this is Track B."
)


# Filled from the three harness-owned transcripts after the oracle runs.  Keeping
# this explicit lets selftest remain deterministic and perform no file I/O.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 2, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "too_easy_at_shipping",
}


def _moment_code(value: int) -> int:
    """A bounded moment-curve code with unique threefold diagonal sums."""

    return value + 1024 * value * value


def _canonical_answer(groups) -> list[list[int]]:
    return sorted(sorted(int(x) for x in group) for group in groups)


def _sample_quotients(rng, target_multiple: int, residue: int):
    target = target_multiple * MODULUS + 3 * residue
    choices = []
    for a in range(1, target_multiple):
        for b in range(1, target_multiple - a):
            c = target_multiple - a - b
            if len({a, b, c}) != 3:
                continue
            lengths = [a * MODULUS + residue, b * MODULUS + residue, c * MODULUS + residue]
            if all(4 * length > target and 2 * length < target for length in lengths):
                choices.append((a, b, c))
    if not choices:
        raise ValueError("target_multiple leaves no strict 3-Partition-band encoding")
    return choices[rng.randrange(len(choices))]


def make_instance(n, seed=0, target_multiple=56, **params) -> dict:
    """Inverse-generate a legal Theorem 2 BusOut clearing schedule.

    The n answer triples exist before any path length or path identifier exists.
    Residue and quotient choices then encode each triple, and the final shuffle
    merely transports that held certificate.  No solver is run by generation.
    """

    del params
    if isinstance(n, bool) or not isinstance(n, int) or not 2 <= n <= 256:
        raise ValueError("n must be an integer in [2, 256]")
    if (
        isinstance(target_multiple, bool)
        or not isinstance(target_multiple, int)
        or target_multiple < 32
        or target_multiple % 8 != 0
    ):
        raise ValueError("target_multiple must be an integer multiple of 8, at least 32")

    rng = random.Random(seed)
    # If r(i)+r(j)+r(k)=3r(h), the base-1024 low digits first give
    # i+j+k=3h and the high digits give i^2+j^2+k^2=3h^2.  Zero variance then
    # forces i=j=k=h.  All base sums are below MODULUS, and multiplication by a
    # nonzero field element preserves the relation while hiding the indices.
    base_pool = [_moment_code(i) for i in range(1, 257)]
    selected = rng.sample(base_pool, n)
    scale = rng.randrange(1, MODULUS)

    encoded = []
    for group, base_residue in enumerate(selected):
        residue = (scale * base_residue) % MODULUS
        qa, qb, qc = _sample_quotients(rng, target_multiple, residue)
        lengths = [
            qa * MODULUS + residue,
            qb * MODULUS + residue,
            qc * MODULUS + residue,
        ]
        target = target_multiple * MODULUS + 3 * residue
        if sum(lengths) != target:
            raise AssertionError("internal target encoding error")
        if not all(4 * value > target and 2 * value < target for value in lengths):
            raise AssertionError("internal strict-band error")
        for role, length in enumerate(lengths):
            encoded.append({"length": length, "group": group, "role": role})

    # Paths are the graph components; this shuffle is both their presentation order
    # and their arbitrary vertex-component labelling.
    rng.shuffle(encoded)
    paths = [entry["length"] for entry in encoded]
    answer_groups = [[] for _ in range(n)]
    for path_id, entry in enumerate(encoded):
        answer_groups[entry["group"]].append(path_id)
    answer = _canonical_answer(answer_groups)
    block_targets = [
        sum(paths[path_id] for path_id in group) for group in answer
    ]
    rng.shuffle(block_targets)

    if len(set(paths)) != 3 * n:
        raise AssertionError("path lengths unexpectedly collided")

    return {
        "n": n,
        "target_multiple": target_multiple,
        "spots": 1,
        "bus_capacity": 1,
        "colors": ["R", "G"],
        "paths": paths,
        "block_targets": block_targets,
        "queue_runs": [run for target in block_targets for run in (["R", target], ["G", target])],
        "answer": answer,
    }


def _format_answer(answer) -> str:
    return json.dumps(answer, separators=(",", ":"))


def render(inst) -> str:
    """Render all BusOut rules, data, and answer conventions inline."""

    lines = [
        "BUSOUT CLEARING SCHEDULE",
        "",
        "There is one bus parking spot, initially empty, and two passenger colors: R and G.",
        "Every bus has capacity 1. Passengers form a strict queue: only its first passenger",
        "may board. Whenever that passenger matches the bus in the spot, boarding happens",
        "automatically before another dispatch; the now-full bus immediately leaves and the",
        "spot becomes empty. A nonmatching bus remains in the only spot and causes deadlock.",
        "",
        "The congestion graph is a disjoint union of directed paths. The current first",
        "remaining bus of each path is free and may be dispatched; removing it exposes the",
        "next bus of that path. A path listed with length L contains, in dispatch order,",
        "exactly L red unit buses followed by exactly L green unit buses.",
        "",
        f"There are {len(inst['paths'])} paths, numbered 0 through {len(inst['paths']) - 1}.",
        "Path lengths L (path_id: L):",
    ]
    for start in range(0, len(inst["paths"]), 8):
        segment = [
            f"{i}:{inst['paths'][i]}"
            for i in range(start, min(start + 8, len(inst["paths"])))
        ]
        lines.append("  " + "  ".join(segment))
    lines.extend(
        [
            "",
            "Passenger queue, split into consecutive blocks (block_id: R-run length = G-run length):",
        ]
    )
    for start in range(0, len(inst["block_targets"]), 8):
        segment = [
            f"{i}:{inst['block_targets'][i]}"
            for i in range(start, min(start + 8, len(inst["block_targets"])))
        ]
        lines.append("  " + "  ".join(segment))
    lines.extend(
        [
            "The full queue is R^T G^T for block 0, followed by R^T G^T for block 1,",
            "and so on, using each block's displayed T. Exponents are exact repeat counts.",
            "",
            f"Give a clearing schedule as exactly {inst['n']} triples of path IDs. For each",
            "passenger block, use the submitted triple whose three path lengths sum to that",
            "block's T: dispatch all red buses from those paths, in any order, followed by all",
            "green buses from the same paths. Each submitted triple must match one block.",
            "Every path ID must occur exactly once. IDs are zero-based; repetitions are forbidden.",
            "Every block T is distinct, so this matching is unambiguous. The order of submitted",
            "triples and the order of IDs within a triple do not affect validity.",
            "",
            "Give your final answer inside <answer></answer> tags, as a JSON array of",
            f"exactly {inst['n']} arrays, each containing exactly three integer path IDs.",
            "Syntax example for a hypothetical six-path instance:",
            "<answer>[[0,2,4],[1,3,5]]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text) -> object | None:
    """Extract the tagged JSON answer, tolerating prose and Markdown fences."""

    if not isinstance(text, str):
        return None
    tagged = re.search(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    candidates = [tagged.group(1)] if tagged else []
    candidates.append(text)
    decoder = json.JSONDecoder()
    for candidate in candidates:
        cleaned = re.sub(r"```(?:json)?", "", candidate, flags=re.I).replace("```", "")
        for match in re.finditer(r"\[", cleaned):
            try:
                value, _ = decoder.raw_decode(cleaned[match.start() :])
            except (ValueError, json.JSONDecodeError):
                continue
            if isinstance(value, list):
                return value
    return None


def _replay_compressed(inst, groups) -> tuple[bool, str]:
    """Replay Theorem 2's dispatch transitions by exact run counts."""

    remaining_paths = set(range(len(inst["paths"])))
    boarded = 0
    spot_empty = True
    by_target = {}
    for group in groups:
        target = sum(inst["paths"][path_id] for path_id in group)
        if target not in set(inst["block_targets"]):
            return False, "triple_not_a_passenger_block"
        if target in by_target:
            return False, "duplicate_block_target"
        by_target[target] = group
    for target in inst["block_targets"]:
        group = by_target.get(target)
        if group is None:
            return False, "passenger_block_unmatched"
        if not spot_empty:
            return False, "occupied_spot"
        red = sum(inst["paths"][path_id] for path_id in group)
        if red != target:
            return False, "triple_not_a_passenger_block"
        # Each red bus matches the current R run, boards, and departs.  Dispatching
        # all reds exposes the green suffixes without putting a green bus in the spot.
        for path_id in group:
            if path_id not in remaining_paths:
                return False, "path_reused_during_replay"
        boarded += red
        # The same equality clears the following G run one unit bus at a time.
        green = red
        boarded += green
        for path_id in group:
            remaining_paths.remove(path_id)
    expected = 2 * sum(inst["block_targets"])
    if boarded != expected:
        return False, "passengers_remaining"
    if remaining_paths:
        return False, "buses_remaining"
    return True, "ok"


def verify(inst, answer) -> tuple[bool, str]:
    """Accept every legal compressed schedule; never inspect inst['answer']."""

    if not isinstance(answer, list):
        return False, "answer_not_list"
    if not answer:
        return False, "empty_answer"
    if len(answer) != inst["n"]:
        return False, "wrong_group_count"
    for group in answer:
        if not isinstance(group, list) or len(group) != 3:
            return False, "wrong_triple_size"
        for path_id in group:
            if isinstance(path_id, bool) or not isinstance(path_id, int):
                return False, "noninteger_path_id"
            if not 0 <= path_id < len(inst["paths"]):
                return False, "path_out_of_range"
    flattened = [path_id for group in answer for path_id in group]
    if len(set(flattened)) != len(flattened):
        return False, "duplicate_path"
    if len(flattened) != len(inst["paths"]):
        return False, "paths_missing"
    return _replay_compressed(inst, answer)


def random_candidate(inst, rng) -> object:
    """Uniformly sample an unlabeled partition into triples, the stated shape."""

    ids = list(range(len(inst["paths"])))
    rng.shuffle(ids)
    return _canonical_answer(
        ids[start : start + 3] for start in range(0, len(ids), 3)
    )


def search_space(inst) -> int | None:
    """Number of partitions of 3n labeled paths into n unordered triples."""

    n = inst["n"]
    return math.factorial(3 * n) // (6**n * math.factorial(n))


def enumerate_all(inst) -> int | None:
    """Brute-force exact valid-answer count when the whole language is small."""

    if search_space(inst) > 1_000_000:
        return None
    lengths = inst["paths"]
    targets = set(inst["block_targets"])

    def count(remaining: tuple[int, ...]) -> int:
        if not remaining:
            return 1
        first = remaining[0]
        total = 0
        tail = remaining[1:]
        for j, k in itertools.combinations(tail, 2):
            if lengths[first] + lengths[j] + lengths[k] not in targets:
                continue
            used = {first, j, k}
            total += count(tuple(x for x in remaining if x not in used))
        return total

    return count(tuple(range(len(lengths))))


def canonical_key(inst) -> str:
    """Canonicalize the multiset of directed-path lengths, not labels or seed."""

    payload = {
        "spots": inst["spots"],
        "capacity": inst["bus_capacity"],
        "colors": len(inst["colors"]),
        "block_targets": sorted(inst["block_targets"]),
        "path_lengths": sorted(inst["paths"]),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params) -> dict | str | None:
    """Increase path crowding and integer range while the answer remains writable."""

    n = int(params.get("n", 80))
    target_multiple = int(params.get("target_multiple", 80))
    if n >= 84:
        return "cap_bound"
    return {
        "n": min(84, n + 12),
        "target_multiple": target_multiple + 16,
    }


def _reference_algorithm(inst):
    """Index all pair sums, query every target/path, and propagate exact cover."""

    lengths = inst["paths"]
    pair_sums = {}
    pair_builds = 0
    for i in range(len(lengths)):
        for j in range(i + 1, len(lengths)):
            pair_builds += 1
            pair_sums.setdefault(lengths[i] + lengths[j], []).append((i, j))
    triples = set()
    target_probes = 0
    pair_scans = 0
    for target in inst["block_targets"]:
        for k, length in enumerate(lengths):
            target_probes += 1
            for i, j in pair_sums.get(target - length, ()):
                pair_scans += 1
                if k != i and k != j:
                    triples.add(tuple(sorted((i, j, k))))
    candidate = _canonical_answer(triples)
    operations = 2 * pair_builds + 2 * target_probes + pair_scans
    return candidate, {
        "pair_builds": pair_builds,
        "target_probes": target_probes,
        "pair_scans": pair_scans,
        "operations": operations,
        "candidate_triples": len(triples),
    }


def _display_order_candidate(inst):
    return _canonical_answer(
        list(range(start, start + 3))
        for start in range(0, len(inst["paths"]), 3)
    )


def _sorted_adjacent_candidate(inst):
    ids = sorted(range(len(inst["paths"])), key=lambda i: inst["paths"][i])
    return _canonical_answer(ids[start : start + 3] for start in range(0, len(ids), 3))


def _balanced_rank_candidate(inst):
    ids = sorted(range(len(inst["paths"])), key=lambda i: inst["paths"][i])
    n = inst["n"]
    return _canonical_answer(
        [ids[i], ids[n + i], ids[3 * n - 1 - i]] for i in range(n)
    )


def _central_magnitude_candidate(inst):
    center3 = sum(inst["block_targets"]) // inst["n"]
    ids = sorted(
        range(len(inst["paths"])),
        key=lambda i: (abs(3 * inst["paths"][i] - center3), i),
    )
    return _canonical_answer(ids[start : start + 3] for start in range(0, len(ids), 3))


def _relabel_paths(inst, order):
    """Carry a schedule through an arbitrary component relabelling."""

    moved = copy.deepcopy(inst)
    moved["paths"] = [inst["paths"][old] for old in order]
    old_to_new = {old: new for new, old in enumerate(order)}
    moved["answer"] = _canonical_answer(
        [old_to_new[path_id] for path_id in group] for group in inst["answer"]
    )
    return moved


def _answer_atoms(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest() -> dict:
    """Run correctness, resistance, scaling, canonicalization, and size gates."""

    report = {}

    # G1: every named setting, multiple seeds, deterministic and JSON-native.
    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 23, 101):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {why}")
            if make_instance(seed=seed, **params) != inst:
                g1_failures.append(f"{preset}/{seed}: nondeterministic")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
        "generation_route": "inverse generation plus certificate-preserving relabelling",
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping_params)

    # G2: arrange five independent corruptions to reach five distinct checks.
    corruptions = {}
    dropped = copy.deepcopy(inst["answer"])
    dropped[0] = dropped[0][:-1]
    corruptions["drop_one"] = dropped
    swapped = copy.deepcopy(inst["answer"])
    swapped[0][0], swapped[1][0] = swapped[1][0], swapped[0][0]
    corruptions["swap_across_triples"] = swapped
    duplicated = copy.deepcopy(inst["answer"])
    duplicated[0][0] = duplicated[1][0]
    corruptions["duplicate"] = duplicated
    corruptions["empty"] = []
    out_of_range = copy.deepcopy(inst["answer"])
    out_of_range[0][0] = len(inst["paths"])
    corruptions["out_of_range"] = out_of_range
    reasons = {name: verify(inst, bad)[1] for name, bad in corruptions.items()}
    report["G2_rejects_corruption"] = {
        "pass": all(not verify(inst, bad)[0] for bad in corruptions.values())
        and len(set(reasons.values())) == len(reasons),
        "reasons": reasons,
    }

    # G3: exact round trip and prose/fence tolerance.
    realistic = (
        "I grouped every path exactly once.\n```json\n<answer>\n"
        + _format_answer(inst["answer"])
        + "\n</answer>\n```\nThe block is my final answer."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0],
        "parsed": parsed == inst["answer"],
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    # G4: structure-aware samples are already partitions into n triples.
    guess_rng = random.Random(0x250509165)
    sample_total = 200_000
    sample_hits = 0
    t0 = time.perf_counter()
    for _ in range(sample_total):
        candidate = random_candidate(inst, guess_rng)
        sample_hits += int(verify(inst, candidate)[0])
    sampling_seconds = time.perf_counter() - t0
    guess_fraction = sample_hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "fraction": guess_fraction,
        "sampler": "uniform unlabeled partitions into triples",
        "search_space": search_space(inst),
        "sampling_wall_seconds": sampling_seconds,
    }

    # G6 and G5 share the eight-seed reference and attack measurements.
    attack_names = (
        "outlier_central_magnitude",
        "greedy_display_order",
        "random_restart_256",
        "sorted_adjacent_triples",
        "by_hand_balanced_rank_zip",
    )
    successes = {name: 0 for name in attack_names}
    reference_successes = 0
    reference_times = []
    reference_operations = []
    reference_pair_builds = []
    reference_target_probes = []
    attack_seeds = list(range(800, 808))
    for seed in attack_seeds:
        trial = make_instance(seed=seed, **shipping_params)
        candidates = {
            "outlier_central_magnitude": _central_magnitude_candidate(trial),
            "greedy_display_order": _display_order_candidate(trial),
            "sorted_adjacent_triples": _sorted_adjacent_candidate(trial),
            "by_hand_balanced_rank_zip": _balanced_rank_candidate(trial),
        }
        for name, candidate in candidates.items():
            successes[name] += int(verify(trial, candidate)[0])
        restart_rng = random.Random(seed ^ 0xA55A5AA5)
        restart_won = False
        for _ in range(256):
            if verify(trial, random_candidate(trial, restart_rng))[0]:
                restart_won = True
                break
        successes["random_restart_256"] += int(restart_won)

        t0 = time.perf_counter()
        reference_answer, metrics = _reference_algorithm(trial)
        reference_times.append(time.perf_counter() - t0)
        reference_operations.append(metrics["operations"])
        reference_pair_builds.append(metrics["pair_builds"])
        reference_target_probes.append(metrics["target_probes"])
        reference_successes += int(verify(trial, reference_answer)[0])

    attacks = {
        name: {"successes": successes[name], "attempts": len(attack_seeds)}
        for name in attack_names
    }
    median_wall = statistics.median(reference_times)
    median_operations = int(statistics.median(reference_operations))
    median_pair_builds = int(statistics.median(reference_pair_builds))
    median_target_probes = int(statistics.median(reference_target_probes))
    report["G6_adversary_panel"] = {
        "pass": all(entry["successes"] == 0 for entry in attacks.values())
        and reference_successes == len(attack_seeds),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "pair-sum index plus forced exact-cover propagation",
            "complexity": "O(m^2 + bm + z) time and O(m^2) pair-index space",
            "wall_clock_sec_median": median_wall,
            "operations_median": median_operations,
            "pair_builds_median": median_pair_builds,
            "target_probes_median": median_target_probes,
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
    }

    demo = make_instance(seed=11, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and demo_count is not None
        and reference_successes == len(attack_seeds),
        "shipping_density_hits": sample_hits,
        "shipping_density_samples": sample_total,
        "shipping_density_fraction": guess_fraction,
        "shipping_sampling_wall_seconds": sampling_seconds,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_wall_seconds_median": median_wall,
        "baseline_operations_median": median_operations,
        "baseline_pair_builds_median": median_pair_builds,
        "baseline_target_probes_median": median_target_probes,
    }

    # G7: the named search spaces strictly increase; 2n remains constructible.
    named_log2_spaces = [
        math.log2(search_space(make_instance(seed=9, **params)))
        for params in DIFFICULTY.values()
    ]
    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * shipping_params["n"]
    doubled_params["target_multiple"] += 16
    t0 = time.perf_counter()
    doubled = make_instance(seed=31337, **doubled_params)
    doubled_build_seconds = time.perf_counter() - t0
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": all(a < b for a, b in zip(named_log2_spaces, named_log2_spaces[1:]))
        and doubled_ok,
        "ladder_log2_search_spaces": named_log2_spaces,
        "doubled_n": doubled_params["n"],
        "doubled_build_seconds": doubled_build_seconds,
        "doubled_verify_reason": doubled_why,
    }

    # G8: arbitrary path and passenger-block reorderings and their compositions.
    invariance_checks = 0
    carried_checks = 0
    g8_failures = []
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(seed=10_000 + seed, **shipping_params)
        key = canonical_key(base)
        unrelated_keys.append(key)
        m = len(base["paths"])
        rng = random.Random(90_000 + seed)
        random_order = list(range(m))
        rng.shuffle(random_order)
        rotation = list(range(seed % m, m)) + list(range(seed % m))
        composed = [random_order[i] for i in reversed(rotation)]
        orders = (random_order, list(reversed(range(m))), rotation, composed)
        for index, order in enumerate(orders):
            moved = _relabel_paths(base, order)
            if index in (2, 3):
                block_order = list(range(base["n"]))
                rng.shuffle(block_order)
                moved["block_targets"] = [moved["block_targets"][i] for i in block_order]
                moved["queue_runs"] = [
                    run
                    for target in moved["block_targets"]
                    for run in (["R", target], ["G", target])
                ]
            invariance_checks += 1
            if canonical_key(moved) != key:
                g8_failures.append(f"seed {seed}, transform {index}: key changed")
            ok, why = verify(moved, moved["answer"])
            carried_checks += 1
            if not ok:
                g8_failures.append(f"seed {seed}, transform {index}: {why}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_distinct": distinct_keys,
        "unrelated_attempts": 20,
        "failures": g8_failures,
        "method": "sorted directed-path lengths and block targets plus fixed station data",
    }

    answer_blob = _format_answer(inst["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    intended_operations = 3 * inst["n"]
    arms = copy.deepcopy(G9_RESULTS["arms"])
    hinted_verdict = G9_RESULTS["hinted_verdict"]
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": hinted_verdict == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": hinted_verdict,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping_params
    report["all_passed"] = all(
        entry.get("pass") is True
        for key, entry in report.items()
        if key.startswith("G") and isinstance(entry, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
