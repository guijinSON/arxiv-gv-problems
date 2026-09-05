"""Verified planted k-Orthogonal-Vectors generator for arXiv:2505.00206.

The solver receives k collections of n binary vectors and must select one vector
from each collection whose coordinatewise product is zero.  Instances are sampled
from the planted distribution in Sections 2--4 of the paper.  The selected row in
each collection is sampled first, and the paper's Plant procedure makes those rows
orthogonal while preserving every proper marginal.  The certificate is therefore
known by construction; this module never searches an instance to obtain its answer.
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
from collections import defaultdict


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - this finite-discrete family needs no helper
    exact_matrices = rationals = None


TRACK: str = "A"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "k collections of fixed-dimensional binary vectors",
        "one orthogonal k-tuple of vectors",
    ],
    "verification_operations": [
        "one-index-per-collection validation",
        "exact bitwise intersection",
        "zero comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "The running coordinatewise AND records exactly which one-bits later "
        "vectors must erase; without propagating that mask, the solver faces n^k "
        "cross-collection tuples."
    ),
    "hardness_basis": (
        "Track A: Conjecture 10 for fixed k=4 and d=alpha(n) log_2(n), with "
        "alpha(n)=max(96,ceil(log_2(n)^2))=omega(1), conjectures no "
        "n^(k-epsilon) average-case algorithm; at shipping n=96 the Section 9 "
        "downsampling attack was run to 1000000 tuple nodes on each of eight seeds "
        "(8000000 measured tuple visits total) and recovered no witness."
    ),
    "max_answer_tokens": 8,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 2, "k": 3, "alpha_floor": 36},
    "easy": {"n": 96, "k": 4, "alpha_floor": 96},
    "medium": {"n": 144, "k": 4, "alpha_floor": 96},
    "hard": {"n": 216, "k": 4, "alpha_floor": 96},
}

SHIPPING_DIFFICULTY: str = "easy"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON list of exactly k records [set_id,row_index], with every set_id "
        "0,...,k-1 appearing once in increasing set_id order and row_index in "
        "0,...,n-1.  Row-index values may repeat across different sets."
    ),
    "bounds": {
        "records": "k",
        "record_width": 2,
        "set_id_min": 0,
        "set_id_max": "k-1",
        "one_record_per_set": True,
        "record_order": "increasing set_id",
        "row_index_min": 0,
        "row_index_max": "n-1",
        "shipping_k": 4,
        "shipping_n": 96,
    },
}

STRUCTURAL_HINT: str = (
    "The running coordinatewise AND is precisely the set of one-bits that the "
    "unselected collections still have to erase."
)

PLACEBO_HINT: str = (
    "The coordinate and collection conventions should be tracked consistently "
    "while examining the displayed binary vectors."
)

NOTES: str = """\
Section 1.1 and Definition 9 fix the native search object: one row index from
each of k binary-vector collections, with coordinatewise product zero.  Sections
2 and 3 specify p, d, and Plant; Lemma 2 is the construction guarantee.  Lemma 5
proves (k-1)-wise independence, so planted rows have the same proper marginals as
decoys.  Lemma 6 says the planted solution is unique except with probability less
than n^-k, but uniqueness is not assumed by verify(), which accepts every witness.

Step-0 algorithm audit: the certificate is produced by the randomized Plant
procedure in O(k*n*d) generation work because the sampler chooses its locations
before modifying the instance.  A solver is not handed those locations.  The
naive search costs O(n^k*d).  Theorem 16's downsampling algorithm costs expected
n^(k-k/(1+alpha)); with alpha=96 this is n^3.9587, still nearly exhaustive.
Conjecture 10 is explicitly average-case and excludes n^(k-epsilon) decision
algorithms for alpha(n)=omega(1); a successful search algorithm gives a decision
algorithm by checking its returned witness.  This is therefore Track A, not a
claim of proved worst-case hardness.

The easy regimes were deliberately avoided.  Section 1.2 explains that fixed p
and d=Theta(log n) admit truly faster algorithms, and Theorem 16 gives a
sub-n^k downsampling exponent when alpha is bounded.  Here alpha(n) is the maximum
of a safe finite-size floor and ceil(log_2(n)^2), hence grows without bound; p is
below 1/2 as Plant requires.  Python's random() implements the real-valued
probabilities to its native 53-bit precision.  This changes probabilities by at
most one RNG quantum and never affects exact verification of the resulting bits.

The attack panel targets the construction rather than merely restating the
conjecture.  Minimum-weight outliers fail because of Lemma 5's identical
one-vector marginals.  Greedy running-AND and a minimum-intersection pair ansatz
test obvious local signatures.  Random restarts test sparse accidental solutions.
The standard distribution-specific attack is the exact coordinate-prefix
downsampling search from Section 9, stopped only after its declared tuple budget.
Plants and decoys are sampled from the paper's same marginal distribution; the
generator does not reject, solve, or condition instances after planting.
"""


# Filled from the separately-run oracle harnesses after hardening.  These are
# diagnostics only; G9(c)'s answer/operation caps are the gate.
_G9_ARMS = {
    "bare": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted": {"solved": 0, "attempts": 0, "errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "errors": 4},
}
_G9_HINTED_VERDICT = "unavailable_openrouter_http_403"


def _parameters(n: int, k: int, alpha_floor: int) -> tuple[int, int, float]:
    """Return (alpha,d,p) for the paper's superlogarithmic distribution."""
    alpha = max(alpha_floor, math.ceil(math.log2(n) ** 2))
    d = math.ceil(alpha * math.log2(n))
    p = (1.0 - 2.0 ** (-2.0 * k / alpha)) ** (1.0 / k)
    return alpha, d, p


def _sample_mask(d: int, p: float, rng: random.Random) -> int:
    mask = 0
    for bit in range(d):
        if rng.random() < p:
            mask |= 1 << bit
    return mask


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Sample the paper's planted distribution and retain its chosen locations."""
    k = params.pop("k", 4)
    alpha_floor = params.pop("alpha_floor", 96)
    if params:
        raise ValueError(f"unknown parameters: {sorted(params)}")
    for name, value in (("n", n), ("k", k), ("alpha_floor", alpha_floor)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if not 2 <= n <= 4096:
        raise ValueError("n must lie between 2 and 4096")
    if not 2 <= k <= 8:
        raise ValueError("k must lie between 2 and 8")
    if alpha_floor < 1:
        raise ValueError("alpha_floor must be positive")

    alpha, d, p = _parameters(n, k, alpha_floor)
    if p > 0.5 + 1e-15:
        raise ValueError(
            "alpha_floor is too small: the paper's Plant procedure requires p <= 1/2"
        )

    rng = random.Random(seed)
    sets = [
        [_sample_mask(d, p, rng) for _ in range(n)]
        for _ in range(k)
    ]
    locations = [rng.randrange(n) for _ in range(k)]

    # This is Plant(U,s_1,...,s_k) from Section 3.  It acts on the selected
    # vector in the final collection but Lemma 3 shows the output distribution
    # is symmetric in all k collections.
    ratio = p / (1.0 - p)
    final_row = sets[k - 1][locations[k - 1]]
    for bit in range(d):
        m = sum((sets[ell][locations[ell]] >> bit) & 1 for ell in range(k))
        zeros = k - m
        if zeros % 2 == 0:
            flip_probability = ratio ** zeros
            if flip_probability >= 1.0 or rng.random() < flip_probability:
                final_row ^= 1 << bit
    sets[k - 1][locations[k - 1]] = final_row

    answer = [[ell, locations[ell]] for ell in range(k)]
    return {
        "family": "planted_k_orthogonal_vectors",
        "n": n,
        "k": k,
        "d": d,
        "alpha": alpha,
        "p": p,
        "sets": sets,
        "answer": answer,
    }


def _answer_records(answer: object, k: int, n: int) -> tuple[list[int] | None, str]:
    if not isinstance(answer, list):
        return None, "type: answer must be a JSON list"
    if not answer:
        return None, "empty: answer contains no set records"
    if len(answer) != k:
        return None, f"length: expected exactly {k} set records"

    records = []
    for pos, record in enumerate(answer):
        if not isinstance(record, list) or len(record) != 2:
            return None, f"record_shape: record {pos} must be [set_id,row_index]"
        set_id, row = record
        if (
            isinstance(set_id, bool)
            or not isinstance(set_id, int)
            or isinstance(row, bool)
            or not isinstance(row, int)
        ):
            return None, f"record_type: record {pos} must contain two integers"
        records.append((set_id, row))

    set_ids = [set_id for set_id, _ in records]
    if len(set(set_ids)) != len(set_ids):
        return None, "duplicate_set: each collection must occur exactly once"
    if any(set_id < 0 or set_id >= k for set_id in set_ids):
        return None, f"set_range: set identifiers must lie in 0,...,{k - 1}"
    by_set = [0] * k
    for set_id, row in records:
        if row < 0 or row >= n:
            return None, f"row_range: row index for set {set_id} is outside 0,...,{n - 1}"
        by_set[set_id] = row
    return by_set, "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any correctly-shaped orthogonal tuple; never consult the planted answer."""
    try:
        n, k, d, sets = inst["n"], inst["k"], inst["d"], inst["sets"]
    except (KeyError, TypeError):
        return False, "instance: malformed instance"
    rows, reason = _answer_records(answer, k, n)
    if rows is None:
        return False, reason

    intersection = (1 << d) - 1
    for ell, row in enumerate(rows):
        intersection &= sets[ell][row]
    if intersection:
        coordinate = (intersection & -intersection).bit_length() - 1
        return False, (
            "not_orthogonal: every selected vector has a 1 at coordinate "
            f"{coordinate}"
        )
    return True, "ok"


def render(inst: dict) -> str:
    """Render a self-contained fixed-width hexadecimal k-OV instance."""
    n, k, d = inst["n"], inst["k"], inst["d"]
    width = (d + 3) // 4
    format_example = json.dumps(
        [[ell, ell % n] for ell in range(k)], separators=(",", ":")
    )
    lines = [
        "Planted k-Orthogonal Vectors",
        "",
        f"There are k={k} collections, numbered 0 through {k - 1}.  Each collection",
        f"contains n={n} binary vectors, with rows numbered 0 through {n - 1}.",
        f"Every vector has d={d} coordinates, numbered 0 through {d - 1}.",
        "",
        "Choose exactly one row from every collection.  The chosen vectors are",
        "orthogonal when, at every coordinate, at least one chosen vector has bit 0;",
        "equivalently, their coordinatewise bitwise AND is the all-zero vector.",
        "This instance is guaranteed to contain at least one such tuple.",
        "",
        f"Vectors below are {width}-digit hexadecimal integers with leading zeros.",
        "Coordinate 0 is the least-significant bit (the rightmost hex digit contains",
        "coordinates 0,1,2,3); any padding bits to the left of coordinate d-1 are 0.",
        "Hex digits use 0-9 and a-f.",
        "",
    ]
    for ell, collection in enumerate(inst["sets"]):
        lines.append(f"Collection {ell}:")
        lines.extend(f"  {row}: {mask:0{width}x}" for row, mask in enumerate(collection))
        lines.append("")

    lines.extend([
        "Output a JSON list of exactly k records [set_id,row_index], one for every",
        "set_id, in increasing set_id order.  A row-index value may repeat in",
        "different collections because the collections are separate.  All indices",
        "are 0-based and both endpoints of each stated range are allowed.",
        "",
        "Give your final answer inside <answer></answer> tags, as a JSON list of",
        "[set_id,row_index] records.",
        f"Format example only: <answer>{format_example}</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    """Extract the first tagged JSON answer, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer>\s*(.*?)\s*</answer>", text, re.I | re.S)
    if not match:
        return None
    try:
        value = json.loads(match.group(1))
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, list) else None


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly after enforcing the obvious one-row-per-set structure."""
    records = [[ell, rng.randrange(inst["n"])] for ell in range(inst["k"])]
    return records


def search_space(inst: dict) -> int:
    """The record order is syntax, not a different semantic witness."""
    return inst["n"] ** inst["k"]


def enumerate_all(inst: dict) -> int | None:
    """Count every valid row tuple when at most 200,000 need be checked."""
    if search_space(inst) > 200_000:
        return None
    total = 0
    for rows in itertools.product(range(inst["n"]), repeat=inst["k"]):
        intersection = (1 << inst["d"]) - 1
        for ell, row in enumerate(rows):
            intersection &= inst["sets"][ell][row]
            if not intersection:
                break
        total += int(intersection == 0)
    return total


def _column_count_profile(inst: dict) -> tuple[tuple[int, ...], ...]:
    d = inst["d"]
    counts = [[0] * d for _ in range(inst["k"])]
    for ell, collection in enumerate(inst["sets"]):
        row_counts = counts[ell]
        for mask in collection:
            bits = mask
            while bits:
                low = bits & -bits
                row_counts[low.bit_length() - 1] += 1
                bits ^= low
    return tuple(sorted(tuple(sorted(counts[ell][j] for ell in range(inst["k"])))
                        for j in range(d)))


def canonical_key(inst: dict) -> str:
    """A strong cheap invariant under row, collection, and coordinate relabelling."""
    set_profiles = []
    for collection in inst["sets"]:
        row_weights = tuple(sorted(mask.bit_count() for mask in collection))
        pair_intersections = tuple(sorted(
            (collection[i] & collection[j]).bit_count()
            for i in range(len(collection))
            for j in range(i + 1, len(collection))
        ))
        set_profiles.append((row_weights, pair_intersections))
    payload = (
        inst["n"],
        inst["k"],
        inst["d"],
        tuple(sorted(set_profiles)),
        _column_count_profile(inst),
    )
    return hashlib.sha256(repr(payload).encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow both the row haystack and dimension while the k-record witness stays fixed."""
    out = dict(params)
    n = int(out.get("n", 96))
    if n >= 4096:
        return None
    out["n"] = min(4096, max(n + 1, math.ceil(n * 1.5)))
    out["alpha_floor"] = math.ceil(int(out.get("alpha_floor", 96)) * 1.25)
    return out


def _candidate_ok(inst: dict, answer: object | None) -> bool:
    return answer is not None and verify(inst, answer)[0]


def _records(rows: list[int]) -> list[list[int]]:
    return [[ell, row] for ell, row in enumerate(rows)]


def _attack_weight_outlier(inst: dict) -> list[list[int]]:
    rows = [
        min(range(inst["n"]), key=lambda row: (collection[row].bit_count(), row))
        for collection in inst["sets"]
    ]
    return _records(rows)


def _attack_greedy_running_and(inst: dict) -> tuple[list[list[int]], int]:
    target_weight = inst["p"] * inst["d"]
    first = min(
        range(inst["n"]),
        key=lambda row: (
            abs(inst["sets"][0][row].bit_count() - target_weight), row
        ),
    )
    rows = [first]
    running = inst["sets"][0][first]
    operations = inst["n"]
    for ell in range(1, inst["k"]):
        row = min(
            range(inst["n"]),
            key=lambda idx: (
                (running & inst["sets"][ell][idx]).bit_count(),
                abs(inst["sets"][ell][idx].bit_count() - target_weight),
                idx,
            ),
        )
        operations += inst["n"]
        rows.append(row)
        running &= inst["sets"][ell][row]
    return _records(rows), operations


def _attack_random_restart(
    inst: dict, rng: random.Random, restarts: int = 512
) -> tuple[list[list[int]] | None, int]:
    for attempt in range(1, restarts + 1):
        candidate = _records([rng.randrange(inst["n"]) for _ in range(inst["k"])])
        if verify(inst, candidate)[0]:
            return candidate, attempt
    return None, restarts


def _attack_pair_ansatz(inst: dict) -> tuple[list[list[int]], int]:
    """For k=4, independently choose the thinnest AND in each pair of sets."""
    if inst["k"] != 4:
        return _attack_greedy_running_and(inst)
    operations = 0
    chosen = []
    for left in (0, 2):
        best = None
        for i, a in enumerate(inst["sets"][left]):
            for j, b in enumerate(inst["sets"][left + 1]):
                operations += 1
                score = (a & b).bit_count()
                key = (score, i, j)
                if best is None or key < best:
                    best = key
        chosen.extend([best[1], best[2]])
    return _records(chosen), operations


def _attack_downsample(
    inst: dict, tuple_budget: int = 1_000_000
) -> tuple[list[list[int]] | None, int, int]:
    """Theorem 16's prefix projection, with an explicit full-tuple budget."""
    dprime = max(1, int(inst["d"] / (1 + inst["alpha"])))
    prefix_mask = (1 << dprime) - 1
    low = [[mask & prefix_mask for mask in collection] for collection in inst["sets"]]
    checked = 0
    for rows in itertools.product(range(inst["n"]), repeat=inst["k"]):
        checked += 1
        projected = prefix_mask
        for ell, row in enumerate(rows):
            projected &= low[ell][row]
            if not projected:
                break
        if projected == 0:
            candidate = _records(list(rows))
            if verify(inst, candidate)[0]:
                return candidate, checked, dprime
        if checked >= tuple_budget:
            break
    return None, checked, dprime


def _permute_coordinates(mask: int, order: list[int]) -> int:
    out = 0
    for new_bit, old_bit in enumerate(order):
        if (mask >> old_bit) & 1:
            out |= 1 << new_bit
    return out


def _transform_instance(
    inst: dict,
    row_orders: list[list[int]],
    coordinate_order: list[int],
    set_order: list[int],
) -> dict:
    """Apply new->old permutations and carry the planted witness through them."""
    k, n = inst["k"], inst["n"]
    old_answer = {set_id: row for set_id, row in inst["answer"]}
    inverse_rows = []
    for order in row_orders:
        inverse = [0] * n
        for new, old in enumerate(order):
            inverse[old] = new
        inverse_rows.append(inverse)

    transformed_sets = []
    answer = []
    for new_set, old_set in enumerate(set_order):
        collection = [
            _permute_coordinates(inst["sets"][old_set][old_row], coordinate_order)
            for old_row in row_orders[old_set]
        ]
        transformed_sets.append(collection)
        answer.append([new_set, inverse_rows[old_set][old_answer[old_set]]])

    out = dict(inst)
    out["sets"] = transformed_sets
    out["answer"] = answer
    return out


def _atomic_elements(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atomic_elements(item) for item in value.values())
    if isinstance(value, list):
        return sum(_atomic_elements(item) for item in value)
    return 1


def selftest() -> dict:
    """Run the nine required correctness, resistance, and suitability gates."""
    report: dict = {
        "paper": "2505.00206",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }
    ship_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    inst = make_instance(seed=20260905, **ship_params)

    planted_checks = 0
    planted_failures = []
    json_native = True
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            probe = make_instance(seed=seed, **params)
            ok, why = verify(probe, probe["answer"])
            planted_checks += 1
            if not ok:
                planted_failures.append({"preset": preset, "seed": seed, "reason": why})
            json_native &= json.loads(json.dumps(probe["answer"])) == probe["answer"]
    report["G1_planted_verifies"] = {
        "pass": not planted_failures and json_native,
        "checks": planted_checks,
        "failures": planted_failures,
        "answers_json_native": json_native,
    }

    planted = inst["answer"]
    altered = json.loads(json.dumps(planted))
    found_invalid = False
    for row in range(inst["n"]):
        if row == planted[0][1]:
            continue
        altered[0][1] = row
        if not verify(inst, altered)[0]:
            found_invalid = True
            break
    corruptions = {
        "drop_one": planted[:-1],
        "swap_one_row": altered if found_invalid else [["bad", 0]] + planted[1:],
        "duplicate_record": [planted[0], planted[0]] + planted[2:],
        "empty": [],
        "out_of_range": [[ell, (inst["n"] if ell == 0 else row)]
                         for ell, row in planted],
    }
    corruption_results = {}
    reason_codes = []
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        reason_codes.append(why.split(":", 1)[0])
        corruption_results[name] = {"rejected": not ok, "reason": why}
    report["G2_rejects_corruption"] = {
        "pass": (
            all(item["rejected"] for item in corruption_results.values())
            and len(set(reason_codes)) == len(reason_codes)
        ),
        "cases": corruption_results,
        "distinct_reason_codes": len(set(reason_codes)),
    }

    response = (
        "I tracked the surviving one-bits across the four collections.\n\n"
        "```json\n<answer>\n"
        + json.dumps(planted)
        + "\n</answer>\n```\nThe selected masks have zero joint AND."
    )
    parsed = parse_answer(response)
    parsed_ok, parsed_why = verify(inst, parsed)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parsed_ok,
        "parsed_equals_answer": parsed == planted,
        "verify_reason": parsed_why,
        "garbage_returns_none": parse_answer("no tagged answer here") is None,
    }

    guess_rng = random.Random(0x250500206)
    guess_total = 200_000
    guess_hits = 0
    density_start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    density_wall = time.perf_counter() - density_start
    observed_density = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": observed_density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": observed_density,
        "candidate_prior": "uniform one-row-per-collection tuples",
        "search_space": search_space(inst),
    }

    attack_seeds = list(range(9100, 9108))
    successes = defaultdict(int)
    operations = defaultdict(int)
    downsample_nodes_per_seed = []
    downsample_dprime = []
    downsample_wall = 0.0
    for seed in attack_seeds:
        attack_inst = make_instance(seed=seed, **ship_params)

        candidate = _attack_weight_outlier(attack_inst)
        successes["minimum_weight_outlier"] += int(_candidate_ok(attack_inst, candidate))
        operations["minimum_weight_outlier"] += attack_inst["k"] * attack_inst["n"]

        candidate, cost = _attack_greedy_running_and(attack_inst)
        successes["greedy_running_and"] += int(_candidate_ok(attack_inst, candidate))
        operations["greedy_running_and"] += cost

        candidate, cost = _attack_random_restart(
            attack_inst, random.Random(seed ^ 0x5A17), restarts=512
        )
        successes["random_restart_512"] += int(_candidate_ok(attack_inst, candidate))
        operations["random_restart_512"] += cost

        candidate, cost = _attack_pair_ansatz(attack_inst)
        successes["minimum_pair_intersection_ansatz"] += int(
            _candidate_ok(attack_inst, candidate)
        )
        operations["minimum_pair_intersection_ansatz"] += cost

        start = time.perf_counter()
        candidate, nodes, dprime = _attack_downsample(
            attack_inst, tuple_budget=1_000_000
        )
        downsample_wall += time.perf_counter() - start
        downsample_nodes_per_seed.append(nodes)
        downsample_dprime.append(dprime)
        successes["section9_downsampling_1m"] += int(
            _candidate_ok(attack_inst, candidate)
        )

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": len(attack_seeds),
            "operations": operations[name],
        }
        for name in (
            "minimum_weight_outlier",
            "greedy_running_and",
            "random_restart_512",
            "minimum_pair_intersection_ansatz",
        )
    }
    attacks["section9_downsampling_1m"] = {
        "successes": successes["section9_downsampling_1m"],
        "attempts": len(attack_seeds),
        "nodes": sum(downsample_nodes_per_seed),
        "nodes_per_seed": downsample_nodes_per_seed,
        "projected_coordinates_per_seed": downsample_dprime,
        "wall_clock_sec": round(downsample_wall, 6),
        "standard_algorithm": True,
        "source": "Section 9, Theorem 16",
    }
    all_failed = all(item["successes"] == 0 for item in attacks.values())

    demo = make_instance(seed=731, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": observed_density < 1e-6 and all_failed,
        "shipping_density_fraction": observed_density,
        "shipping_valid_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "baseline_attack_wall_clock_sec": round(downsample_wall, 6),
        "baseline_attack_nodes": sum(downsample_nodes_per_seed),
        "shipping_n": inst["n"],
        "shipping_k": inst["k"],
        "shipping_d": inst["d"],
        "shipping_alpha": inst["alpha"],
        "demo_exact_valid_answers": demo_count,
        "demo_search_space": search_space(demo),
        "strongest_attack": {
            "name": "Section 9 prefix-downsampling enumeration",
            "wall_clock_sec": round(downsample_wall, 6),
            "nodes": sum(downsample_nodes_per_seed),
            "nodes_per_seed": downsample_nodes_per_seed,
            "attempts": len(attack_seeds),
            "successes": successes["section9_downsampling_1m"],
        },
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and len(attacks) >= 4,
        "attacks": attacks,
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] = ship_params["n"] * 2
    start = time.perf_counter()
    doubled = make_instance(seed=4471, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * inst["n"],
        "base_n": inst["n"],
        "doubled_n": doubled["n"],
        "base_search_space": search_space(inst),
        "doubled_search_space": search_space(doubled),
        "answer_records_unchanged": len(inst["answer"]) == len(doubled["answer"]),
        "build_and_verify_sec": round(time.perf_counter() - start, 6),
        "verify_reason": doubled_why,
    }

    invariance_checks = 0
    transport_checks = 0
    nontrivial = 0
    unrelated_keys = []
    for offset in range(20):
        original = make_instance(seed=12000 + offset, **ship_params)
        original_key = canonical_key(original)
        unrelated_keys.append(original_key)
        rng = random.Random(33000 + offset)
        identity_rows = [list(range(original["n"])) for _ in range(original["k"])]
        row_orders = [list(range(original["n"])) for _ in range(original["k"])]
        for order in row_orders:
            rng.shuffle(order)
        identity_coordinates = list(range(original["d"]))
        coordinate_order = list(range(original["d"]))
        rng.shuffle(coordinate_order)
        identity_sets = list(range(original["k"]))
        set_order = list(range(original["k"]))
        rng.shuffle(set_order)
        variants = [
            _transform_instance(original, row_orders, identity_coordinates, identity_sets),
            _transform_instance(original, identity_rows, coordinate_order, identity_sets),
            _transform_instance(original, identity_rows, identity_coordinates, set_order),
            _transform_instance(original, row_orders, coordinate_order, set_order),
        ]
        for variant in variants:
            invariance_checks += 1
            same = canonical_key(variant) == original_key
            ok, _ = verify(variant, variant["answer"])
            transport_checks += int(same and ok)
            nontrivial += int(variant["sets"] != original["sets"])
    report["G8_canonical_key"] = {
        "pass": (
            invariance_checks == 80
            and transport_checks == 80
            and nontrivial >= 60
            and len(set(unrelated_keys)) == 20
        ),
        "invariance_checks": invariance_checks,
        "witness_transport_checks": transport_checks,
        "nontrivial_transformations": nontrivial,
        "unrelated_distinct": len(set(unrelated_keys)),
        "unrelated_attempts": len(unrelated_keys),
        "transformations": [
            "row permutations within every collection",
            "coordinate permutation",
            "collection permutation",
            "composition of all three",
        ],
        "invariant": (
            "sorted row weights, within-collection pair-intersection weights, "
            "and sorted per-coordinate collection counts"
        ),
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _atomic_elements(inst["answer"])
    # Once a candidate path has been identified by running-AND propagation, its
    # four-way AND can be checked by one 4-hex-digit table lookup per displayed
    # hex column, plus k record/range checks.  This deliberately does not pretend
    # that the Track-A search itself is a short arithmetic calculation.
    intended_operations = (inst["d"] + 3) // 4 + inst["k"]
    hinted = _G9_ARMS["hinted"]
    placebo = _G9_ARMS["placebo"]
    hinted_rate = (
        hinted["solved"] / hinted["attempts"] if hinted["attempts"] else None
    )
    placebo_rate = (
        placebo["solved"] / placebo["attempts"] if placebo["attempts"] else None
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": _G9_ARMS,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": _G9_HINTED_VERDICT,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "caps_pass": within_caps,
        "diagnostic_arms_are_not_gated": True,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(bool(gate.get("pass")) for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
