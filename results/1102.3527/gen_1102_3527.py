"""Verified problem generator for arXiv:1102.3527.

The generated objects are binary receiver subspaces from the paper's q-IEV
problem.  Each subspace is supplied exactly by one parity check.  A vector is
innovative for every receiver precisely when every displayed parity is one.

Generation is answer-first: cyclic four-coordinate checks are chosen so that
an alternating vector in a hidden coordinate order has odd parity in every
check.  Independent coordinate relabelling hides that order.  No instance is
solved in order to manufacture its certificate.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import random
import re
import sys
import time


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # The module remains standard-library-only.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "receiver subspaces of GF(2)^n",
        "sparse parity-check vectors over GF(2)",
        "binary innovative encoding vector",
    ],
    "verification_operations": [
        "exact GF(2) inner product",
        "exact parity comparison",
        "binary shape and range checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Within a cyclic block of receiver checks, the four receiver-index "
        "parities containing any coordinate have a three-to-one majority that "
        "recovers an innovative bit up to the harmless global complement; "
        "without this invariant, one must eliminate a large binary system."
    ),
    "hardness_basis": (
        "Track B: GF(2) Gaussian elimination solves the hyperplane instance in "
        "O(K*n^2) scalar bit operations; at the shipping hard preset the "
        "reference run used at most 1,614,850 counted scalar operations and "
        "0.030 seconds locally, while the cyclic majority invariant needs "
        "exactly 4n=288 parity/majority operations at n=72."
    ),
    "max_answer_tokens": 54,
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
    "demo": {"n": 8, "layers": 1},
    "easy": {"n": 48, "layers": 6},
    "medium": {"n": 60, "layers": 10},
    "hard": {"n": 72, "layers": 14},
}

SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "One JSON list of exactly n binary integers (0 or 1), in displayed "
        "coordinate order.  All 2^n such vectors are admissible candidates."
    ),
    "bounds": {
        "length": "n",
        "alphabet": [0, 1],
        "max_n_supported": 252,
        "max_shipping_n": 72,
    },
}

STRUCTURAL_HINT = (
    "Within a block of n receivers, the four receiver-index parities containing "
    "each coordinate have a three-to-one majority."
)

PLACEBO_HINT = (
    "Keep every coordinate index aligned carefully while evaluating the many "
    "binary parity conditions."
)

NOTES = """\
Section II defines an encoding vector as innovative for a receiver exactly when
it lies outside the row span already held by that receiver.  Section III defines
q-IEV and proves 2-IEV NP-complete, while also identifying q >= K as an always-
solvable regime; this generator deliberately uses q=2<K.  Theorem 2 and its
proof give the cofactor construction and Section IV gives its
O(K*N^3+K^2*N) cost when q>=K.  That result rules out a Track-A claim here.

The generated receiver spans are hyperplanes, represented without loss by
their one-row parity checks; Section III itself uses the equivalent orthogonal
B-matrix representation in the proof of Theorem 1.  Thus this special
distribution has an even more
direct polynomial reference algorithm: GF(2) Gaussian elimination.  It is
therefore declared Track B.  Each cyclic layer uses four offsets with an odd
number of odd offsets; the hidden alternating vector has parity one in every
row.  The first layer is required by construction to have rank n-1, so exactly
two certificates exist (global complements).  Coordinate degrees are exactly
equal, layers use the same construction throughout, and coordinates are
randomly relabelled.  These choices defeat degree outliers, label-parity
ansatzes, a one-pass greedy assignment, and random restarts.  The structural
shortcut is the three-to-one parity majority among the four occurrences of a
coordinate inside one cyclic receiver block.
"""


def _gf2_rank_masks(rows: list[int], n: int) -> int:
    work = list(rows)
    rank = 0
    for col in range(n):
        pivot = next((r for r in range(rank, len(work)) if (work[r] >> col) & 1), None)
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        for r in range(len(work)):
            if r != rank and ((work[r] >> col) & 1):
                work[r] ^= work[rank]
        rank += 1
        if rank == len(work):
            break
    return rank


def _layer_masks(n: int, offsets: tuple[int, int, int, int]) -> list[int]:
    rows = []
    for i in range(n):
        mask = 0
        for offset in offsets:
            mask ^= 1 << ((i + offset) % n)
        rows.append(mask)
    return rows


def _offset_class(n: int, offsets: tuple[int, ...]) -> tuple[int, ...]:
    """Translation/reflection normal form for a subset of the cyclic group."""
    source = set(offsets)
    variants = []
    for sign in (1, -1):
        reflected = {(sign * x) % n for x in source}
        for shift in range(n):
            variants.append(tuple(sorted((x + shift) % n for x in reflected)))
    return min(variants)


def _sample_offsets(
    n: int,
    rng: random.Random,
    used: set[tuple[int, ...]],
    require_rank: bool,
) -> tuple[int, int, int, int]:
    for _ in range(20000):
        candidate = tuple(sorted(rng.sample(range(n), 4)))
        # Four entries remove dependence on the row's parity.  An odd number of
        # odd offsets makes the alternating vector evaluate to one.
        if sum(x & 1 for x in candidate) not in (1, 3):
            continue
        normal = _offset_class(n, candidate)
        if normal in used:
            continue
        if require_rank and _gf2_rank_masks(_layer_masks(n, candidate), n) != n - 1:
            continue
        used.add(normal)
        return candidate
    raise ValueError("could not sample enough inequivalent full-rank cyclic layers")


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Construct a certified binary innovative-vector instance answer-first."""
    layers = params.pop("layers", 1)
    if params:
        raise ValueError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 8 or n % 2:
        raise ValueError("n must be an even integer at least 8")
    if n > 252:
        raise ValueError("n exceeds the 252-element certificate-language cap")
    if isinstance(layers, bool) or not isinstance(layers, int) or layers < 1:
        raise ValueError("layers must be a positive integer")
    if layers > 32:
        raise ValueError("layers exceeds the supported cap of 32")

    rng = random.Random(seed)
    coordinate_label = list(range(n))
    rng.shuffle(coordinate_label)
    global_flip = rng.randrange(2)
    answer = [0] * n
    for hidden, shown in enumerate(coordinate_label):
        answer[shown] = (hidden & 1) ^ global_flip

    used: set[tuple[int, ...]] = set()
    checks: list[list[int]] = []
    for layer in range(layers):
        offsets = _sample_offsets(n, rng, used, require_rank=(layer == 0))
        shift = rng.randrange(n)
        direction = rng.choice((-1, 1))
        for shown_row in range(n):
            base = (shift + direction * shown_row) % n
            support = sorted(coordinate_label[(base + d) % n] for d in offsets)
            checks.append(support)

    return {
        "family": "binary_innovative_vector_for_receiver_hyperplanes",
        "q": 2,
        "n": n,
        "layers": layers,
        "receiver_checks": checks,
        "answer": answer,
    }


def render(inst: dict) -> str:
    n = inst["n"]
    checks = inst["receiver_checks"]
    lines = "\n".join(
        f"R{i}: " + " ".join(map(str, support))
        for i, support in enumerate(checks)
    )
    statement = f"""Binary innovative encoding vector

All arithmetic is in GF(2): addition is XOR, so a sum is 1 exactly when it
contains an odd number of ones.  Vector coordinates are indexed 0 through
{n - 1}.  Receiver R_i already knows the hyperplane

    H_i = {{y in GF(2)^{n} : XOR of y[j] over the listed indices j is 0}}.

Find one encoding vector x in GF(2)^{n} that is innovative for every receiver,
meaning x is outside every H_i.  Equivalently, for every line below, the XOR of
the four listed coordinates of x must equal 1.  Receiver order has no effect on
validity.  Repeated coordinates are not allowed in a support (none occur here).

The {len(checks)} receiver parity-check supports are:
{lines}
"""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\nHint: " + STRUCTURAL_HINT + "\n"
    elif mode == "placebo":
        statement += "\nHint: " + PLACEBO_HINT + "\n"
    statement += f"""
Give your final answer inside <answer></answer> tags as one JSON list of exactly
{n} integers, each 0 or 1, in coordinate-index order.  Example syntax:
<answer>[0, 1, 0, 1]</answer>
The example is format-only and has the wrong length for this instance.  Output
nothing else inside the tags."""
    return statement


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.I | re.S)
    candidates = tagged if tagged else fenced
    if not candidates:
        candidates = re.findall(r"(\[[\s\d,]+\])", text, flags=re.S)
    for raw in reversed(candidates):
        try:
            value = json.loads(raw.strip())
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, list) and all(type(v) is int for v in value):
            return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    n = inst["n"]
    if not isinstance(answer, list):
        return False, "answer_not_list"
    if not answer:
        return False, "answer_empty"
    if len(answer) < n:
        return False, f"answer_too_short:{len(answer)}_expected_{n}"
    if len(answer) > n:
        return False, f"answer_too_long:{len(answer)}_expected_{n}"
    if any(type(v) is not int for v in answer):
        return False, "non_integer_entry"
    if any(v not in (0, 1) for v in answer):
        return False, "entry_out_of_range"
    for receiver, support in enumerate(inst["receiver_checks"]):
        parity = 0
        for coordinate in support:
            parity ^= answer[coordinate]
        if parity != 1:
            return False, f"noninnovative_receiver:{receiver}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    return [rng.randrange(2) for _ in range(inst["n"])]


def search_space(inst: dict) -> int:
    return 1 << inst["n"]


def enumerate_all(inst: dict) -> int | None:
    n = inst["n"]
    if n > 20:
        return None
    count = 0
    for bits in itertools.product((0, 1), repeat=n):
        if verify(inst, list(bits))[0]:
            count += 1
    return count


def _row_mask(support: list[int]) -> int:
    mask = 0
    for coordinate in support:
        mask ^= 1 << coordinate
    return mask


def _reference_gaussian(inst: dict) -> tuple[list[int] | None, dict]:
    """Solve A*x=1 without consulting inst['answer']; count scalar work."""
    n = inst["n"]
    rows = [_row_mask(s) | (1 << n) for s in inst["receiver_checks"]]
    pivot_row = 0
    pivot_cols: list[int] = []
    pivot_tests = 0
    row_xors = 0
    for col in range(n):
        pivot = None
        for r in range(pivot_row, len(rows)):
            pivot_tests += 1
            if (rows[r] >> col) & 1:
                pivot = r
                break
        if pivot is None:
            continue
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        for r in range(len(rows)):
            if r != pivot_row and ((rows[r] >> col) & 1):
                rows[r] ^= rows[pivot_row]
                row_xors += 1
        pivot_cols.append(col)
        pivot_row += 1

    coefficient_mask = (1 << n) - 1
    for row in rows:
        if (row & coefficient_mask) == 0 and ((row >> n) & 1):
            return None, {
                "rank": len(pivot_cols),
                "pivot_tests": pivot_tests,
                "row_xors": row_xors,
                "scalar_operations": pivot_tests + row_xors * (n + 1),
            }

    answer = [0] * n
    # The matrix is in reduced echelon form; free variables remain zero.
    for r, col in enumerate(pivot_cols):
        answer[col] = (rows[r] >> n) & 1
    return answer, {
        "rank": len(pivot_cols),
        "pivot_tests": pivot_tests,
        "row_xors": row_xors,
        "scalar_operations": pivot_tests + row_xors * (n + 1),
    }


def canonical_key(inst: dict) -> str:
    """Strong cheap invariant under receiver/coordinate relabelling.

    Complete hypergraph isomorphism is deliberately not attempted.  The key is
    the sorted collection of receiver intersection profiles together with the
    sorted coordinate co-occurrence profiles.
    """
    n = inst["n"]
    supports = [set(row) for row in inst["receiver_checks"]]
    row_profiles = [[0, 0, 0, 0, 0] for _ in supports]
    for i in range(len(supports)):
        for j in range(i + 1, len(supports)):
            overlap = len(supports[i] & supports[j])
            row_profiles[i][overlap] += 1
            row_profiles[j][overlap] += 1

    cooccurrence = [[0] * n for _ in range(n)]
    for support in supports:
        for a, b in itertools.combinations(sorted(support), 2):
            cooccurrence[a][b] += 1
            cooccurrence[b][a] += 1
    column_profiles = [sorted(row[:i] + row[i + 1 :]) for i, row in enumerate(cooccurrence)]

    invariant = {
        "n": n,
        "receivers": len(supports),
        "row_profiles": sorted(row_profiles),
        "column_profiles": sorted(column_profiles),
    }
    payload = json.dumps(invariant, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    harder = dict(params)
    n = int(harder.get("n", 8))
    layers = int(harder.get("layers", 1))
    if layers < 32:
        harder["layers"] = min(32, layers + 4)
        harder["n"] = n
        return harder
    if n + 2 <= 74:
        harder["n"] = n + 2
        harder["layers"] = layers
        return harder
    return "cap_bound"


def _attack_outlier(inst: dict) -> list[int]:
    degrees = [0] * inst["n"]
    for support in inst["receiver_checks"]:
        for coordinate in support:
            degrees[coordinate] += 1
    ordered = sorted(degrees)
    median = ordered[len(ordered) // 2]
    return [int(degree > median) for degree in degrees]


def _attack_greedy(inst: dict) -> list[int]:
    values = [-1] * inst["n"]
    for support in inst["receiver_checks"]:
        parity = 0
        unknown = []
        for coordinate in support:
            if values[coordinate] < 0:
                unknown.append(coordinate)
            else:
                parity ^= values[coordinate]
        if unknown:
            chosen = min(unknown)
            values[chosen] = parity ^ 1
            for coordinate in unknown:
                if values[coordinate] < 0:
                    values[coordinate] = 0
    return [max(0, value) for value in values]


def _attack_obvious_ansatzes(inst: dict) -> bool:
    n = inst["n"]
    candidates = [
        [0] * n,
        [1] * n,
        [i & 1 for i in range(n)],
        [1 ^ (i & 1) for i in range(n)],
    ]
    first = set(inst["receiver_checks"][0])
    candidates.append([int(i in first) for i in range(n)])
    candidates.append([int(i not in first) for i in range(n)])
    return any(verify(inst, candidate)[0] for candidate in candidates)


def _compact_majority_route(inst: dict) -> tuple[list[int], int]:
    """Use the cyclic incidence invariant, independent of the planted answer."""
    n = inst["n"]
    occurrences: list[list[int]] = [[] for _ in range(n)]
    for receiver, support in enumerate(inst["receiver_checks"][:n]):
        for coordinate in support:
            occurrences[coordinate].append(receiver & 1)
    # Four parity observations can be reduced to three additions and one sign
    # test, counted as four exact logical/arithmetic operations per coordinate.
    candidate = [int(sum(parities) >= 3) for parities in occurrences]
    return candidate, 4 * n


def _transformed_instance(inst: dict, seed: int) -> tuple[dict, list[int]]:
    rng = random.Random(seed)
    n = inst["n"]
    permutation = list(range(n))
    rng.shuffle(permutation)  # old coordinate -> new coordinate
    order = list(range(len(inst["receiver_checks"])))
    rng.shuffle(order)
    transformed_checks = []
    for old_receiver in order:
        support = [permutation[x] for x in inst["receiver_checks"][old_receiver]]
        rng.shuffle(support)
        transformed_checks.append(support)
    transformed_answer = [0] * n
    for old, new in enumerate(permutation):
        transformed_answer[new] = inst["answer"][old]
    transformed = {
        "family": inst["family"],
        "q": 2,
        "n": n,
        "layers": inst["layers"],
        "receiver_checks": transformed_checks,
        "answer": transformed_answer,
    }
    return transformed, transformed_answer


# Replaced with measured hardening-arm results after STEP 4.
G9_ARMS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}


def selftest() -> dict:
    report: dict = {}

    g1_attempts = 0
    g1_failures = []
    for preset, kwargs in DIFFICULTY.items():
        for seed in (0, 1, 29):
            inst = make_instance(**kwargs, seed=seed)
            g1_attempts += 1
            ok, why = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed, "reason": "not_json_native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(**shipping_params, seed=0)
    planted = inst["answer"]
    opposite_pairs = [
        (i, j)
        for i in range(inst["n"])
        for j in range(i + 1, inst["n"])
        if planted[i] != planted[j]
    ]
    swapped = planted[:]
    swap_rejected = False
    for i, j in opposite_pairs:
        candidate = planted[:]
        candidate[i], candidate[j] = candidate[j], candidate[i]
        if not verify(inst, candidate)[0]:
            swapped = candidate
            swap_rejected = True
            break
    corruptions = {
        "drop": planted[:-1],
        "swap": swapped,
        "duplicate": planted + [planted[-1]],
        "empty": [],
        "out_of_range": planted[:-1] + [2],
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": why}
    reasons = [entry["reason"] for entry in corruption_results.values()]
    g2_pass = swap_rejected and all(x["rejected"] for x in corruption_results.values())
    g2_pass = g2_pass and len(reasons) == len(set(reasons))
    report["G2_rejects_corruption"] = {
        "pass": g2_pass,
        "distinct_reasons": len(set(reasons)),
        "cases": corruption_results,
    }

    model_style = (
        "The parity checks are satisfied.\n```json\n"
        + "<answer>"
        + json.dumps(planted)
        + "</answer>\n```\n"
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("garbage") is None,
        "model_style_recovered": parsed == planted,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    guess_rng = random.Random(0x11023527)
    guess_total = 200000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "exact_probability": 2.0 ** (1 - inst["n"]),
        "candidate_space": search_space(inst),
    }

    reference_times = []
    reference_ops = []
    reference_successes = 0
    reference_ranks = []
    for seed in range(8):
        attack_inst = make_instance(**shipping_params, seed=1000 + seed)
        started = time.perf_counter()
        solved, stats = _reference_gaussian(attack_inst)
        reference_times.append(time.perf_counter() - started)
        reference_ops.append(stats["scalar_operations"])
        reference_ranks.append(stats["rank"])
        if solved is not None and verify(attack_inst, solved)[0]:
            reference_successes += 1
    rank = _gf2_rank_masks([_row_mask(s) for s in inst["receiver_checks"]], inst["n"])
    valid_count = 1 << (inst["n"] - rank)
    density = valid_count / search_space(inst)
    report["G5_density_and_baseline_cost"] = {
        "pass": reference_successes == 8 and rank == inst["n"] - 1,
        "shipping_exact_valid_solution_count": valid_count,
        "shipping_exact_density_denominator": search_space(inst),
        "shipping_solution_density": density,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "baseline_attack_wall_clock_sec": max(reference_times),
        "baseline_attack_operations": max(reference_ops),
        "baseline_attack_row_rank": rank,
    }

    attack_counts = {
        "equal_degree_outlier": 0,
        "greedy_single_pass": 0,
        "random_restart_1024": 0,
        "constant_and_label_parity_ansatzes": 0,
    }
    for seed in range(8):
        attack_inst = make_instance(**shipping_params, seed=2000 + seed)
        attack_counts["equal_degree_outlier"] += int(
            verify(attack_inst, _attack_outlier(attack_inst))[0]
        )
        attack_counts["greedy_single_pass"] += int(
            verify(attack_inst, _attack_greedy(attack_inst))[0]
        )
        rr_rng = random.Random(0xBAD000 + seed)
        restart_success = any(
            verify(attack_inst, random_candidate(attack_inst, rr_rng))[0]
            for _ in range(1024)
        )
        attack_counts["random_restart_1024"] += int(restart_success)
        attack_counts["constant_and_label_parity_ansatzes"] += int(
            _attack_obvious_ansatzes(attack_inst)
        )
    attacks = {
        name: {"successes": successes, "attempts": 8}
        for name, successes in attack_counts.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "reduced-row-echelon Gaussian elimination over GF(2)",
            "complexity": "O(K*n^2) scalar bit operations",
            "wall_clock_sec_max": max(reference_times),
            "wall_clock_sec_mean": sum(reference_times) / len(reference_times),
            "operations_max": max(reference_ops),
            "operations_mean": sum(reference_ops) / len(reference_ops),
            "ranks": reference_ranks,
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled_started = time.perf_counter()
    doubled = make_instance(**doubled_params, seed=77)
    doubled_build = time.perf_counter() - doubled_started
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok,
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "layers": doubled["layers"],
        "build_wall_clock_sec": doubled_build,
        "verify_reason": doubled_why,
    }

    invariant_ok = 0
    transform_valid = 0
    unrelated_keys = []
    for seed in range(20):
        key_inst = make_instance(**shipping_params, seed=3000 + seed)
        original_key = canonical_key(key_inst)
        changed, carried_answer = _transformed_instance(key_inst, 9000 + seed)
        if canonical_key(changed) == original_key:
            invariant_ok += 1
        if verify(changed, carried_answer)[0]:
            transform_valid += 1
        unrelated_keys.append(original_key)
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_ok == 20 and transform_valid == 20 and distinct == 20,
        "invariant_relabellings": invariant_ok,
        "invariant_attempts": 20,
        "valid_carried_witnesses": transform_valid,
        "validity_attempts": 20,
        "distinct_unrelated": distinct,
        "distinct_attempts": 20,
        "invariant": "sorted row-intersection and coordinate-cooccurrence profiles",
    }

    answer_text = json.dumps(planted)
    answer_chars = len(answer_text)
    answer_elements = len(planted)
    answer_tokens = (answer_chars + 3) // 4
    intended_ops = 4 * inst["n"]
    arms = json.loads(json.dumps(G9_ARMS))
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    compact_answer, compact_ops = _compact_majority_route(inst)
    compact_ok, compact_why = verify(inst, compact_answer)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps and compact_ok and compact_ops == intended_ops,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": (
            "not_run"
            if arms["hinted"]["attempts"] == 0
            else ("hardened" if arms["hinted"]["solved"] == 0 else "too_easy")
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "compact_route_verifies": compact_ok,
        "compact_route_verify_reason": compact_why,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
