"""Verified VC-shattering problem generator for arXiv:1705.09517.

The solver receives exactly the paper's native object: an explicit finite concept
class, represented by its Boolean incidence matrix.  The requested witness is a
fixed-size subset of universe elements shattered by that class.

Generation is inverse.  Rows indexed by (x, t) contain every labelling of the
planted coordinates (twice), while the other coordinates come from a disguised
low-dimensional Walsh family and flip when t flips.  Thus the planted subset is
known without solving the generated instance.  The shared flip is also the Track
B compression: mechanically finding its translation symmetry takes many row-set
lookups, while recognizing the aligned two-half representation exposes it in one
row XOR.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import time
from collections import Counter


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": ["finite universe", "explicit Boolean concept-incidence matrix"],
    "verification_operations": [
        "project each concept onto the proposed subset",
        "exact bit-pattern comparison with all binary labellings",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "The two equal halves of the concept list differ by one common symmetric-"
        "difference mask, whose fixed coordinates form a shattered subset; without "
        "recognizing it, one searches fixed-size subsets and their projections."
    ),
    "hardness_basis": (
        "Track B: the paper's exact VC-dimension algorithm enumerates universe "
        "subsets in m^{O(log |C|)} time, while this distribution also has an "
        "O(|C|^2) word-operation translation-stabilizer scan; at the shipping "
        "preset the measured scan uses 524,860 XOR/set-membership operations "
        "and 0.22--0.43 seconds across the final validation runs, "
        "whereas the aligned-half symmetry gives a 120-operation no-tool route."
    ),
    "max_answer_tokens": 9,
}

NATIVE = {
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

DIFFICULTY = {
    "demo": {"n": 7, "witness_size": 3, "decoy_rank": 2},
    "easy": {"n": 8, "witness_size": 4, "decoy_rank": 2},
    "medium": {"n": 10, "witness_size": 5, "decoy_rank": 3},
    "hard": {"n": 60, "witness_size": 9, "decoy_rank": 6},
}

SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A strictly increasing JSON list of exactly k distinct 0-based universe "
        "indices; order is semantically irrelevant and the canonical encoding is "
        "increasing."
    ),
    "bounds": {"max_length": 32, "max_universe_size": 512, "index_min": 0},
}

STRUCTURAL_HINT = (
    "The two equal halves of the concept list have a common symmetric-difference mask."
)
PLACEBO_HINT = (
    "The explicit indexing conventions are worth checking carefully before answering."
)

# Filled from the three isolated harden.py runs.  These diagnostics do not gate;
# only the exact size/effort caps in G9 do.
G9_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}

NOTES = """\
Section 2 (Preliminaries), Definition 3 fixes the exact shattering condition used
by render() and verify().  Theorem 1 and Section 3 give the hard approximation
regime for explicit incidence matrices, but do not imply average-case hardness
for planted yes-instances.  Section 1 (Related Work/Techniques) identifies the
quasi-polynomial exact method: enumerate element tuples up to log |C|; this is why
the module honestly uses Track B.  The construction equalizes every column degree
and every pairwise 2x2 contingency table, defeating marginal/outlier and pairwise
correlation attacks.  Random row and column disguises defeat first-index and
left-to-right greedy choices, while the decoy functions come from one random
low-dimensional Walsh affine space so random restarts almost never shatter.  The
reference translation-stabilizer scan is reported as a successful algorithm, not
as a failed attack.  Section 3's Label-Cover reduction is not used: instantiating
it with an ad-hoc satisfiable planted Label-Cover distribution would not inherit
the paper's rETH distributional hardness claim.  The aligned-half translation is
generator-added Track-B structure, not a claim that it occurs in Theorem 13's
hard instances.
"""


def _rank_gf2(rows: list[int], width: int) -> int:
    work = list(rows)
    rank = 0
    for bit in range(width):
        pivot = None
        for j in range(rank, len(work)):
            if (work[j] >> bit) & 1:
                pivot = j
                break
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        for j in range(rank + 1, len(work)):
            if (work[j] >> bit) & 1:
                work[j] ^= work[rank]
        rank += 1
    return rank


def _random_independent_vectors(
    width: int, count: int, rng: random.Random
) -> list[int]:
    basis: list[int] = []
    while len(basis) < count:
        candidate = rng.randrange(1, 1 << width)
        if _rank_gf2(basis + [candidate], width) > len(basis):
            basis.append(candidate)
    return basis


def _affine_walsh_labels(
    width: int, dimension: int, count: int, rng: random.Random
) -> list[int]:
    """Return `count` distinct labels in a random affine GF(2) subspace."""

    basis = _random_independent_vectors(width, dimension, rng)
    offset = rng.randrange(1 << width)
    labels = []
    for selector in range(1 << dimension):
        value = offset
        for i, vector in enumerate(basis):
            if (selector >> i) & 1:
                value ^= vector
        labels.append(value)
    rng.shuffle(labels)
    return labels[:count]


def make_instance(
    n: int,
    seed: int = 0,
    witness_size: int = 9,
    decoy_rank: int = 6,
    **params,
) -> dict:
    """Construct an explicit concept class and a known shattered subset.

    `n` is the universe size (the haystack), not the witness length.  Rows are
    constructed from all `(x,t)` with x in {0,1}^k and t in {0,1}.  The planted
    columns reproduce x, so their projection contains every k-bit label.  No
    search for a shattered subset occurs during generation.
    """

    del params
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError("n must be an integer")
    if not (3 <= witness_size <= 16):
        raise ValueError("witness_size must lie in 3..16")
    if n < witness_size + 1:
        raise ValueError("n must exceed witness_size")
    decoys = n - witness_size
    needed_rank = max(1, (decoys - 1).bit_length())
    actual_rank = max(decoy_rank, needed_rank)
    if actual_rank > witness_size:
        raise ValueError("too many decoys for this witness_size")

    rng = random.Random(seed)
    patterns = 1 << witness_size
    walsh_labels = _affine_walsh_labels(
        witness_size, actual_rank, decoys, rng
    )

    # A random bijection makes each Walsh decoy look unrelated to the visible x
    # labels.  A separate common row order is used in both t-halves.
    disguised = list(range(patterns))
    rng.shuffle(disguised)
    x_order = list(range(patterns))
    rng.shuffle(x_order)

    old_columns = list(range(n))
    rng.shuffle(old_columns)
    complements = [rng.randrange(2) for _ in range(n)]

    concepts: list[int] = []
    for t in (0, 1):
        for x in x_order:
            y = disguised[x]
            old_bits = [(x >> i) & 1 for i in range(witness_size)]
            old_bits.extend(
                t ^ ((label & y).bit_count() & 1) for label in walsh_labels
            )
            row = 0
            for new_index, old_index in enumerate(old_columns):
                bit = old_bits[old_index] ^ complements[old_index]
                row |= bit << new_index
            concepts.append(row)

    answer = sorted(
        new_index
        for new_index, old_index in enumerate(old_columns)
        if old_index < witness_size
    )
    return {
        "paper": "arXiv:1705.09517",
        "family": "explicit VC-shattering with a concealed translation symmetry",
        "n": n,
        "seed": seed,
        "witness_size": witness_size,
        "decoy_rank": actual_rank,
        "concepts": concepts,
        "answer": answer,
    }


def render(inst: dict) -> str:
    n = inst["n"]
    k = inst["witness_size"]
    concepts = inst["concepts"]
    lines = [
        "Find a shattered subset in an explicit finite concept class.",
        "",
        "Definitions.",
        f"The universe is U = {{0,1,...,{n - 1}}}.",
        "A concept is a subset of U.  Below, each concept is one binary row of",
        f"exactly {n} bits: bit i (counted from 0 at the LEFT) is 1 exactly when",
        "universe element i belongs to that concept.",
        f"There are {len(concepts)} concepts; their displayed order has no effect",
        "on whether a proposed subset is shattered.",
        "",
        "A subset S of U is shattered when every binary labelling of S occurs:",
        "for each subset T of S, at least one displayed concept C satisfies",
        "C intersect S = T.",
        "",
        f"Return exactly {k} DISTINCT universe indices.  Indices are 0-based,",
        "order does not matter, and repeats are forbidden.",
        "",
        "Concept rows:",
    ]
    for i, row in enumerate(concepts):
        lines.append(
            f"{i:04d}: "
            + "".join("1" if (row >> j) & 1 else "0" for j in range(n))
        )
    lines.extend(
        [
            "",
            "Give your final answer inside <answer></answer> tags as a JSON list",
            f"of exactly {k} distinct 0-based integers.",
            f"Example: <answer>{json.dumps(list(range(k)))}</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    try:
        match = re.search(
            r"<answer>(.*?)</answer>", str(text), flags=re.IGNORECASE | re.DOTALL
        )
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:json|python|text)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
        if body == "":
            return []
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            bare = body[1:-1] if body.startswith("[") and body.endswith("]") else body
            tokens = [token for token in re.split(r"[\s,]+", bare.strip()) if token]
            if not tokens or not all(re.fullmatch(r"-?\d+", token) for token in tokens):
                return None
            value = [int(token) for token in tokens]
        if not isinstance(value, list):
            return None
        if not all(isinstance(x, int) and not isinstance(x, bool) for x in value):
            return None
        return value
    except Exception:
        return None


def _column_masks(inst: dict) -> list[int]:
    cached = inst.get("_column_masks_cache")
    if isinstance(cached, list) and len(cached) == inst["n"]:
        return cached
    columns = [0] * inst["n"]
    for row_index, row in enumerate(inst["concepts"]):
        bit = 1 << row_index
        for j in range(inst["n"]):
            if (row >> j) & 1:
                columns[j] |= bit
    inst["_column_masks_cache"] = columns
    return columns


def _is_shattered_indices(inst: dict, indices: list[int]) -> bool:
    all_rows = (1 << len(inst["concepts"])) - 1
    columns = _column_masks(inst)
    cells = [all_rows]
    for index in indices:
        column = columns[index]
        next_cells = []
        for cell in cells:
            zero = cell & (all_rows ^ column)
            one = cell & column
            if zero == 0 or one == 0:
                return False
            next_cells.extend((zero, one))
        cells = next_cells
    return True


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    k = inst["witness_size"]
    n = inst["n"]
    if not isinstance(answer, list) or not all(
        isinstance(x, int) and not isinstance(x, bool) for x in answer
    ):
        return False, "malformed answer: expected a JSON list of integer indices"
    if len(answer) == 0:
        return False, f"empty answer: expected exactly {k} indices"
    if len(answer) != k:
        return False, f"wrong length: expected {k} indices, got {len(answer)}"
    for index in answer:
        if index < 0 or index >= n:
            return False, f"out of range: index {index} is not in 0..{n - 1}"
    if len(set(answer)) != k:
        return False, "duplicate index: all proposed universe elements must be distinct"

    if not _is_shattered_indices(inst, answer):
        seen = set()
        for concept in inst["concepts"]:
            pattern = 0
            for bit, index in enumerate(answer):
                pattern |= ((concept >> index) & 1) << bit
            seen.add(pattern)
        needed = 1 << k
        return False, f"not shattered: only {len(seen)} of {needed} label patterns occur"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    return sorted(rng.sample(range(inst["n"]), inst["witness_size"]))


def search_space(inst: dict) -> int | None:
    return math.comb(inst["n"], inst["witness_size"])


def enumerate_all(inst: dict) -> int | None:
    if search_space(inst) > 200_000:
        return None
    count = 0
    for candidate in itertools.combinations(range(inst["n"]), inst["witness_size"]):
        if _is_shattered_indices(inst, list(candidate)):
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """A row/column-relabel invariant based on all 3-column cell histograms.

    Exact incidence isomorphism is graph-isomorphism hard in general.  The sorted
    multiset below is a deliberately strong cheap invariant, not a claim to be a
    complete canonical form.  It is unchanged by every row or column permutation.
    """

    columns = _column_masks(inst)
    row_count = len(inst["concepts"])
    all_rows = (1 << row_count) - 1
    signatures = []
    for a, b, c in itertools.combinations(columns, 3):
        counts = []
        for pattern in range(8):
            mask = all_rows
            mask &= a if pattern & 1 else (all_rows ^ a)
            mask &= b if pattern & 2 else (all_rows ^ b)
            mask &= c if pattern & 4 else (all_rows ^ c)
            counts.append(mask.bit_count())
        # Sorting the eight cells removes coordinate order (and harmlessly also
        # forgets coordinate complements), while retaining the interaction sizes.
        signatures.append(tuple(sorted(counts)))
    signatures.sort()
    payload = json.dumps(
        [inst["n"], row_count, inst["witness_size"], signatures],
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def escalate(params: dict) -> dict | str | None:
    clean = {k: v for k, v in params.items() if k != "_preset"}
    n = int(clean.get("n", 60))
    k = int(clean.get("witness_size", 9))
    rank = int(clean.get("decoy_rank", 6))
    max_n_at_rank = k + (1 << rank)
    if n < max_n_at_rank:
        clean["n"] = min(max_n_at_rank, n + 12)
        return clean
    if rank < k - 2:
        clean["decoy_rank"] = rank + 1
        clean["n"] = min(k + (1 << (rank + 1)), n + 24)
        return clean
    if 2 * n <= 300:
        clean["n"] = min(k + (1 << rank), n + 8)
        if clean["n"] > n:
            return clean
    return "cap_bound"


def _permute_columns(inst: dict, permutation: list[int]) -> tuple[dict, list[int]]:
    """Move old column i to new column permutation[i], carrying the answer."""

    n = inst["n"]
    rows = []
    for row in inst["concepts"]:
        moved = 0
        for old, new in enumerate(permutation):
            moved |= ((row >> old) & 1) << new
        rows.append(moved)
    out = dict(inst)
    out["concepts"] = rows
    out.pop("_column_masks_cache", None)
    carried = sorted(permutation[i] for i in inst["answer"])
    return out, carried


def _recover_translation(inst: dict) -> tuple[list[int] | None, int]:
    """Mechanical Track-B reference algorithm on the unordered row set."""

    rows = inst["concepts"]
    row_set = set(rows)
    frequencies = Counter()
    operations = 0
    for i, row in enumerate(rows):
        for other in rows[i + 1 :]:
            frequencies[row ^ other] += 1
            operations += 1
    for delta, _frequency in frequencies.most_common():
        stable = True
        for row in rows:
            operations += 1
            if (row ^ delta) not in row_set:
                stable = False
                break
        if stable:
            candidate = [j for j in range(inst["n"]) if not ((delta >> j) & 1)]
            operations += inst["n"]
            if len(candidate) == inst["witness_size"]:
                return candidate, operations
    return None, operations


def _recover_aligned_halves(inst: dict) -> tuple[list[int] | None, int]:
    """The intended no-tool route: one aligned XOR and its zero coordinates."""

    rows = inst["concepts"]
    half = len(rows) // 2
    operations = 0
    if half == 0 or len(rows) != 2 * half:
        return None, operations
    delta = rows[0] ^ rows[half]
    operations += inst["n"]  # compare the two displayed bit rows
    candidate = []
    for index in range(inst["n"]):
        operations += 1
        if not ((delta >> index) & 1):
            candidate.append(index)
    if len(candidate) != inst["witness_size"]:
        return None, operations
    return candidate, operations


def _attack_degree(inst: dict) -> list[int]:
    columns = _column_masks(inst)
    target = len(inst["concepts"]) // 2
    ranked = sorted(range(inst["n"]), key=lambda j: (abs(columns[j].bit_count() - target), j))
    return sorted(ranked[: inst["witness_size"]])


def _attack_pairwise(inst: dict) -> list[int]:
    columns = _column_masks(inst)
    total = len(inst["concepts"])
    scores = [0] * inst["n"]
    for i in range(inst["n"]):
        for j in range(i + 1, inst["n"]):
            both = (columns[i] & columns[j]).bit_count()
            deviation = abs(4 * both - total)
            scores[i] += deviation
            scores[j] += deviation
    ranked = sorted(range(inst["n"]), key=lambda j: (scores[j], j))
    return sorted(ranked[: inst["witness_size"]])


def _attack_greedy(inst: dict) -> list[int]:
    rows = inst["concepts"]
    selected: list[int] = []
    codes = [0] * len(rows)
    for depth in range(inst["witness_size"]):
        best = None
        best_score = -1
        for candidate in range(inst["n"]):
            if candidate in selected:
                continue
            flag = 1 << depth
            score = len(
                {
                    codes[r] | (flag if (row >> candidate) & 1 else 0)
                    for r, row in enumerate(rows)
                }
            )
            if score > best_score:
                best_score = score
                best = candidate
        assert best is not None
        flag = 1 << depth
        for r, row in enumerate(rows):
            if (row >> best) & 1:
                codes[r] |= flag
        selected.append(best)
    return sorted(selected)


def _attack_adjacent_difference(inst: dict) -> list[int]:
    rows = inst["concepts"]
    differences = Counter(rows[i] ^ rows[i + 1] for i in range(0, len(rows) - 1, 2))
    delta, _ = differences.most_common(1)[0]
    zeros = [j for j in range(inst["n"]) if not ((delta >> j) & 1)]
    if len(zeros) >= inst["witness_size"]:
        return sorted(zeros[: inst["witness_size"]])
    return list(range(inst["witness_size"]))


def _find_bad_corruption(inst: dict) -> list[int]:
    answer = list(inst["answer"])
    outsiders = [j for j in range(inst["n"]) if j not in set(answer)]
    for remove_count in (2, 3, 1):
        for replacement in itertools.combinations(outsiders[:12], remove_count):
            candidate = sorted(answer[remove_count:] + list(replacement))
            if not verify(inst, candidate)[0]:
                return candidate
    raise AssertionError("could not find a non-shattered corruption")


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest() -> dict:
    report: dict = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    g1_cases = 0
    g1_ok = True
    for params in DIFFICULTY.values():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, _ = verify(inst, inst["answer"])
            g1_cases += 1
            g1_ok &= ok
            g1_ok &= json.loads(json.dumps(inst["answer"])) == inst["answer"]
    report["G1_planted_verifies"] = {"pass": bool(g1_ok), "cases": g1_cases}

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = list(shipping["answer"])
    corruptions = {
        "drop": answer[:-1],
        "swap_for_decoys": _find_bad_corruption(shipping),
        "duplicate": answer[:-1] + [answer[0]],
        "empty": [],
        "out_of_range": answer[:-1] + [shipping["n"]],
    }
    rejection_reasons = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        rejection_reasons[name] = {"rejected": not ok, "reason": reason}
    reason_classes = {item["reason"].split(":", 1)[0] for item in rejection_reasons.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(x["rejected"] for x in rejection_reasons.values())
        and len(reason_classes) == len(rejection_reasons),
        "cases": rejection_reasons,
        "distinct_reason_classes": len(reason_classes),
    }

    model_style = (
        "The repeated projection patterns identify the coordinates.\n\n"
        "```text\n<answer>\n" + json.dumps(answer) + "\n</answer>\n```"
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(shipping, parsed)[0],
        "parsed": parsed,
    }

    guess_rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    guess_shortcuts = Counter()
    planted_set = set(shipping["answer"])
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(shipping, guess_rng)
        decoy_count = sum(index not in planted_set for index in candidate)
        # These are exact consequences of make_instance(), used only to make the
        # 200k-sample density audit cheaper.  With zero decoys this is the planted
        # basis.  With one, the common t bit supplies the missing binary choice.
        # With more than rank+1 decoys, quotienting that t flip leaves at most
        # decoy_rank independent Walsh bits, hence fewer than 2^k projections.
        if decoy_count <= 1:
            candidate_ok = True
            guess_shortcuts["proved_shattered"] += 1
        elif decoy_count > shipping["decoy_rank"] + 1:
            candidate_ok = False
            guess_shortcuts["proved_not_shattered"] += 1
        else:
            candidate_ok = _is_shattered_indices(shipping, candidate)
            guess_shortcuts["checked_exactly"] += 1
        if candidate_ok:
            guess_hits += 1
    guess_seconds = time.perf_counter() - guess_start
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "structure_aware_space": search_space(shipping),
        "exact_shortcut_cases": dict(guess_shortcuts),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    demo = make_instance(seed=5, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    ref_start = time.perf_counter()
    ref_answer, ref_operations = _recover_translation(shipping)
    ref_seconds = time.perf_counter() - ref_start
    ref_ok = ref_answer is not None and verify(shipping, ref_answer)[0]
    report["G5_density_and_baseline"] = {
        "pass": guess_total >= 200_000 and ref_ok,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_estimate": guess_probability,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_wall_clock_sec": round(ref_seconds, 6),
        "baseline_operations": ref_operations,
        "baseline_solved": ref_ok,
    }

    attack_functions = {
        "outlier_column_degree": _attack_degree,
        "greedy_projection_growth": _attack_greedy,
        "random_restart_256": None,
        "pairwise_correlation": _attack_pairwise,
        "adjacent_row_difference": _attack_adjacent_difference,
    }
    attack_results = {name: {"successes": 0, "attempts": 8} for name in attack_functions}
    ref_successes = 0
    ref_total_operations = 0
    ref_total_seconds = 0.0
    compact_successes = 0
    compact_worst_operations = 0
    compact_total_seconds = 0.0
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for name, attack in attack_functions.items():
            if attack is None:
                rng = random.Random(seed ^ 0xBAD5EED)
                solved = False
                for _ in range(256):
                    if _is_shattered_indices(inst, random_candidate(inst, rng)):
                        solved = True
                        break
                candidate_ok = solved
            else:
                candidate_ok = verify(inst, attack(inst))[0]
            attack_results[name]["successes"] += int(candidate_ok)
        start = time.perf_counter()
        candidate, operations = _recover_translation(inst)
        ref_total_seconds += time.perf_counter() - start
        ref_total_operations += operations
        ref_successes += int(candidate is not None and verify(inst, candidate)[0])
        start = time.perf_counter()
        compact_candidate, compact_operations = _recover_aligned_halves(inst)
        compact_total_seconds += time.perf_counter() - start
        compact_worst_operations = max(compact_worst_operations, compact_operations)
        compact_successes += int(
            compact_candidate is not None and verify(inst, compact_candidate)[0]
        )
    all_failed = all(item["successes"] == 0 for item in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_successes == 8 and compact_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "translation-stabilizer scan on the concept-row set",
            "complexity": "O(|C|^2) machine-word XOR and hash-membership operations",
            "wall_clock_sec": round(ref_total_seconds / 8, 6),
            "operations": round(ref_total_operations / 8),
            "solves": f"{ref_successes}/8, as expected",
        },
        "intended_compact_route": {
            "name": "XOR one pair of rows at equal offsets in the two halves",
            "operations_worst_of_8": compact_worst_operations,
            "wall_clock_sec": round(compact_total_seconds / 8, 6),
            "solves": f"{compact_successes}/8",
        },
        "paper_general_algorithm": {
            "name": "enumerate all element subsets up to log2(|C|)",
            "shipping_k_subset_count": search_space(shipping),
            "complexity": "|U|^{O(log |C|)} (Section 1 of the paper)",
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    scale_start = time.perf_counter()
    doubled = make_instance(seed=4242, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * shipping["n"],
        "base_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_concepts": len(doubled["concepts"]),
        "build_and_verify_sec": round(time.perf_counter() - scale_start, 6),
    }

    invariance_checks = 0
    transformation_checks = 0
    base_keys = []
    for seed in range(20):
        inst = make_instance(seed=10_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        base_keys.append(key)
        rng = random.Random(50_000 + seed)

        permutation = list(range(inst["n"]))
        rng.shuffle(permutation)
        complement_mask = rng.randrange(1 << inst["n"])
        row_order = list(range(len(inst["concepts"])))
        rng.shuffle(row_order)

        # Shattering is invariant under all three operations below. Exercise
        # every nonempty composition, not only each generator separately.
        for flags in range(1, 8):
            transformed = dict(inst)
            carried = list(inst["answer"])
            if flags & 1:  # reorder concepts
                transformed["concepts"] = [
                    transformed["concepts"][i] for i in row_order
                ]
                transformed.pop("_column_masks_cache", None)
            if flags & 2:  # relabel universe elements
                transformed, carried = _permute_columns(transformed, permutation)
            if flags & 4:  # complement any fixed set of universe coordinates
                moved_mask = complement_mask
                if flags & 2:
                    moved_mask = 0
                    for old, new in enumerate(permutation):
                        moved_mask |= ((complement_mask >> old) & 1) << new
                transformed["concepts"] = [
                    row ^ moved_mask for row in transformed["concepts"]
                ]
                transformed.pop("_column_masks_cache", None)
            invariance_checks += int(canonical_key(transformed) == key)
            transformation_checks += int(verify(transformed, carried)[0])
    distinct_keys = len(set(base_keys))
    report["G8_canonical_key"] = {
        "pass": invariance_checks == 140
        and transformation_checks == 140
        and distinct_keys == 20,
        "invariance_checks_passed": invariance_checks,
        "invariance_checks_total": 140,
        "transformed_witness_checks_passed": transformation_checks,
        "transformed_witness_checks_total": 140,
        "distinct_unrelated_keys": distinct_keys,
        "unrelated_instances": 20,
        "invariant": "multiset of exact 3-column projection cell-count histograms",
        "transformations": [
            "concept-row reorder",
            "universe-element permutation",
            "fixed coordinate complementation",
            "all four nontrivial multi-operation compositions",
        ],
    }

    answer_size_samples = [
        make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])["answer"]
        for seed in range(100)
    ]
    answer_chars = max(len(json.dumps(value)) for value in answer_size_samples)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    compact_answer, route_operations = _recover_aligned_halves(shipping)
    hinted = G9_RESULTS["hinted"]
    placebo = G9_RESULTS["placebo"]
    arms_measured = bool(hinted["attempts"] and placebo["attempts"])
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else None
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else None
    report["G9_no_tool_suitability"] = {
        "pass": compact_answer is not None
        and verify(shipping, compact_answer)[0]
        and answer_chars <= 2000
        and answer_elements <= 256
        and route_operations <= 300,
        "arms": G9_RESULTS,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate if arms_measured else None
        ),
        "hinted_verdict": (
            "too_easy" if hinted["solved"] else "hardened"
        ) if hinted["attempts"] else "not_run",
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "answer_size_seeds": len(answer_size_samples),
        "intended_route_operations": route_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(item.get("pass") for item in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
