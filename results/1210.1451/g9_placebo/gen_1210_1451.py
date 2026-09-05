"""Verified problem generator for arXiv:1210.1451.

The family uses the exact square homogeneous system in the proof of Theorem 1:

    F_0 = sum_i c_i x_i,
    F_i = x_0^2 - x_i^2  (1 <= i <= n).

A normalized nonzero common root is inverse-generated before the coefficients
are shuffled and independently sign-switched.  The coefficient magnitudes are
assembled in four-term, equal-pair-sum blocks, so the root certificate follows
by a composition of exact identities and is never obtained by solving the
generated instance.
"""

from __future__ import annotations

import copy
import hashlib
import heapq
import itertools
import json
import math
import os
import random
import re
import statistics
import sys
import time
from fractions import Fraction


# harden.py is run from this directory, whereas gvlib lives at the repo root.
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import rationals
except ImportError:  # The module remains exact and standard-library-only.
    rationals = None


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "Modulo 1000, each four-coefficient residue bucket contains two "
    "complementary pairs with identical sums."
)
PLACEBO_HINT: str = (
    "Careful bookkeeping of every displayed coefficient helps avoid sign and "
    "indexing mistakes in the final vector."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "subset_sum",
    "certificate_form": "rational",
    "native_objects": [
        "square homogeneous polynomial system over Z",
        "normalized rational projective common root",
    ],
    "verification_operations": [
        "exact rational substitution",
        "integer squaring",
        "exact integer dot product",
        "zero comparison",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 2, Theorem 1 (thm:folklore): Partition is encoded by "
        "F_i=x_0^2-x_i^2 and F_0=sum_i w_i x_i"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Coefficient magnitudes sharing one residue modulo 1000 split into two "
        "equal-sum pairs; without that invariant, one executes subset-sum DP."
    ),
    "hardness_basis": (
        "Track B: the standard bitset subset-sum dynamic program costs "
        "O(nS/w) word operations and, at the hard preset, measured about "
        "26.7 million 64-bit word transitions and 0.176 seconds per instance; "
        "the modular-symmetry "
        "route takes at most 276 exact operations once noticed."
    ),
    "max_answer_tokens": 80,
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
    "demo": {
        "n": 8,
        "modulus": 10,
        "center_min": 10,
        "center_max": 24,
    },
    "easy": {
        "n": 24,
        "modulus": 100,
        "center_min": 80,
        "center_max": 140,
    },
    "medium": {
        "n": 36,
        "modulus": 1000,
        "center_min": 140,
        "center_max": 240,
    },
    "hard": {
        "n": 48,
        "modulus": 1000,
        "center_min": 800,
        "center_max": 1200,
    },
}
# G9 scratch copy: exercise only the shipping preset.
DIFFICULTY = {"hard": DIFFICULTY["hard"]}
SHIPPING_DIFFICULTY: str = "hard"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A normalized rational projective vector (x_0,...,x_n), encoded as "
        "n+1 JSON rationals [numerator,denominator], with x_0=1 and every "
        "x_i in {-1,+1}.  Thus the bounded language contains exactly 2^n "
        "vectors; the denominator is 1 and numerators have absolute value 1."
    ),
    "bounds": {
        "max_coordinates": 193,
        "numerator_abs": 1,
        "denominator": 1,
        "normalization": "x_0=1",
    },
}

NOTES: str = (
    "Definition 1 fixes the multivariate resultant as the irreducible "
    "coefficient polynomial vanishing exactly when n homogeneous polynomials "
    "in n variables have a nonzero common root over the algebraic closure. "
    "Section 2, Theorem 1 supplies the exact Partition encoding used here and "
    "shows NP-hardness even at degree at most two; its proof also fixes the "
    "projective signs x_i=+/-x_0. Section 2 explains the easy bivariate dense "
    "regime (a polynomial-size Sylvester determinant), and Section 4 records "
    "Canny's polynomial-space Macaulay method plus exponential matrix size. "
    "This generated distribution is deliberately structured, so worst-case "
    "NP-hardness is not claimed: it is Track B. Plants and decoys are not "
    "separate populations; every coefficient belongs to the same randomized "
    "four-term identity, then all variables are permuted and independently "
    "sign-switched. Magnitude/sign switches defeat the outlier rule, shuffling "
    "defeats sorted alternation, 256 random-sign restarts exploit no bias, and "
    "presentations hit by Karmarkar--Karp are deterministically resampled without "
    "consulting the witness. All four attacks are measured. The successful standard "
    "algorithm is disclosed separately as bitset subset-sum DP."
)


# Replaced from the transcripts after the three hardening runs.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "not_run",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _rational_json(value):
    """Return the canonical JSON pair for an exact rational."""
    if rationals is not None:
        return rationals.to_json(value)
    q = value if isinstance(value, Fraction) else Fraction(value)
    return [q.numerator, q.denominator]


def _vector_json(values):
    if rationals is not None:
        return rationals.vector_to_json(values)
    return [_rational_json(value) for value in values]


def _build_once(n, seed, modulus, center_min, center_max):
    """Build one inverse-generated presentation before adversarial filtering.

    In each four-variable block, magnitudes are q(C+a), q(C-a), q(C+b),
    q(C-b), with one common residue added.  The first complementary pair and
    second complementary pair have the same sum.  Their chosen signs therefore
    cancel identically.  Independent variable sign switches and one final
    permutation carry that known root to the displayed system.
    """
    if not _is_int(n) or n < 4 or n % 4:
        raise ValueError("n must be an integer divisible by 4 and at least 4")
    if n > 192:
        raise ValueError("n must be at most 192 so answers remain within the cap")
    if not _is_int(modulus) or modulus < n // 4 + 2:
        raise ValueError("modulus must be an integer larger than the block count")
    if not _is_int(center_min) or not _is_int(center_max):
        raise ValueError("center bounds must be integers")
    if center_min < 6 or center_max < center_min:
        raise ValueError("center bounds must satisfy 6 <= center_min <= center_max")

    rng = random.Random(seed)
    blocks = n // 4
    residues = rng.sample(range(1, modulus), blocks)
    entries = []
    for residue in residues:
        center = rng.randint(center_min, center_max)
        offset_cap = max(2, center_min // 3)
        a, b = rng.sample(range(1, offset_cap + 1), 2)
        magnitudes = [
            modulus * (center + a) + residue,
            modulus * (center - a) + residue,
            modulus * (center + b) + residue,
            modulus * (center - b) + residue,
        ]
        orientation = rng.choice((-1, 1))
        identity_signs = [orientation, orientation, -orientation, -orientation]
        for magnitude, identity_sign in zip(magnitudes, identity_signs):
            switch = rng.choice((-1, 1))
            coefficient = switch * magnitude
            root_coordinate = switch * identity_sign
            entries.append([coefficient, root_coordinate])

    # Both signs make the corruption tests meaningful.  Flipping all four
    # identity signs of one block preserves that block's zero identity.
    root_values = [entry[1] for entry in entries]
    if all(value == root_values[0] for value in root_values):
        for index in range(4):
            entries[index][1] *= -1

    rng.shuffle(entries)
    coefficients = [entry[0] for entry in entries]
    answer = _vector_json([1] + [entry[1] for entry in entries])
    return {
        "family": "normalized common root of a square homogeneous system",
        "n": n,
        "variables": n + 1,
        "coefficients": coefficients,
        "answer": answer,
    }


def make_instance(n, seed=0, modulus=1000, center_min=800, center_max=1200, **params):
    """Inverse-generate a root, rejecting presentations leaked by greedy differencing.

    The root is known before filtering: filtering never finds or modifies the
    certificate.  It only prevents a known construction-sensitive heuristic
    from selecting an exact zero partition.  The retry stream is local and
    deterministic in ``seed``.
    """
    del params
    retry_rng = random.Random(f"1210.1451/retry/{seed}")
    for attempt in range(64):
        trial_seed = seed if attempt == 0 else retry_rng.randrange(1 << 63)
        inst = _build_once(n, trial_seed, modulus, center_min, center_max)
        greedy = _karmarkar_karp_candidate(inst)
        # Demo/easy are illustrations, not the shipping adversarial regime.
        if n < 32 or not verify(inst, greedy)[0]:
            inst["generation_attempts"] = attempt + 1
            return inst
    raise RuntimeError("could not hide the planted identity from greedy differencing")


def _answer_text(answer):
    return ", ".join(f"{pair[0]}/{pair[1]}" for pair in answer)


def render(inst):
    n = inst["n"]
    lines = [
        "Find an exact nonzero common root of this square homogeneous polynomial system over Q.",
        "",
        f"Variables: x_0, x_1, ..., x_{n}.",
        f"There are {n + 1} homogeneous equations in {n + 1} variables:",
        "  F_0 = c_1*x_1 + ... + c_n*x_n = 0,",
        f"  F_i = x_0^2 - x_i^2 = 0 for every i=1,...,{n}.",
        "The integer c_i values, in 1-based x_i order, are:",
    ]
    for start in range(0, n, 8):
        chunk = inst["coefficients"][start : start + 8]
        rendered = ", ".join(
            f"c_{start + offset + 1}={value}"
            for offset, value in enumerate(chunk)
        )
        lines.append("  " + rendered)
    lines.extend(
        [
            "",
            "A common root is projective: multiplying every coordinate by one nonzero rational gives the same point.",
            "Return one representative normalized by x_0=1, in the exact order x_0,x_1,...,x_n.",
            f"The answer must contain exactly {n + 1} rationals; repeats are allowed and order matters.",
            "Write every rational as num/den in lowest terms with den>0; no decimals or omitted denominators.",
            "Give your final answer inside <answer></answer> tags, as one comma-separated rational vector.",
            "Example: <answer>1/1, -1/1, 1/1</answer>",
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
    """Parse the last tagged comma-separated exact rational vector."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    fence = re.fullmatch(r"```(?:text|txt)?\s*(.*?)\s*```", body, re.I | re.S)
    if fence:
        body = fence.group(1).strip()
    if not body:
        return None
    pieces = [piece.strip() for piece in body.split(",")]
    if any(not piece for piece in pieces):
        return None
    answer = []
    for piece in pieces:
        match = re.fullmatch(r"([+-]?\d+)\s*/\s*([+-]?\d+)", piece)
        if not match:
            return None
        numerator, denominator = int(match.group(1)), int(match.group(2))
        if denominator == 0:
            return None
        q = Fraction(numerator, denominator)
        if q.denominator <= 0:
            return None
        answer.append([q.numerator, q.denominator])
    return answer


def _coerce_vector(answer):
    if not isinstance(answer, (list, tuple)):
        return None, "answer must be a list of rational pairs"
    values = []
    for index, pair in enumerate(answer):
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            return None, f"coordinate {index} is not a [numerator, denominator] pair"
        numerator, denominator = pair
        if not _is_int(numerator) or not _is_int(denominator):
            return None, f"coordinate {index} does not contain two integers"
        if denominator == 0:
            return None, f"coordinate {index} has zero denominator"
        values.append(Fraction(numerator, denominator))
    return values, None


def verify(inst, answer):
    """Check any normalized rational common root by exact substitution."""
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, (list, tuple)):
        return False, "answer must be a rational vector"
    expected = inst["n"] + 1
    if len(answer) != expected:
        return False, f"wrong vector length: expected {expected}, got {len(answer)}"
    values, error = _coerce_vector(answer)
    if error is not None:
        return False, error
    if values[0] != 1:
        return False, "first coordinate must equal the normalization x_0=1"
    x0_squared = values[0] * values[0]
    for index, value in enumerate(values[1:], 1):
        if value * value != x0_squared:
            return False, f"quadratic equation F_{index} is nonzero"
    linear = sum(
        coefficient * value
        for coefficient, value in zip(inst["coefficients"], values[1:])
    )
    if linear != 0:
        return False, f"linear equation F_0 is nonzero (value {linear})"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from all normalized vectors forced by F_i=0."""
    return _vector_json([1] + [rng.choice((-1, 1)) for _ in range(inst["n"])])


def search_space(inst):
    return 1 << inst["n"]


def enumerate_all(inst):
    n = inst["n"]
    if n > 20:
        return None
    coefficients = inst["coefficients"]
    return sum(
        1
        for signs in itertools.product((-1, 1), repeat=n)
        if sum(c * s for c, s in zip(coefficients, signs)) == 0
    )


def canonical_key(inst):
    """Canonical under variable permutation/sign switches and equation scaling."""
    magnitudes = [abs(value) for value in inst["coefficients"]]
    common = 0
    for value in magnitudes:
        common = math.gcd(common, value)
    common = common or 1
    normal = sorted(value // common for value in magnitudes)
    payload = json.dumps([inst["n"], normal], separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params):
    """Increase coefficient height at fixed witness length and fixed modulus."""
    harder = dict(params)
    low = int(harder.get("center_min", 800))
    high = int(harder.get("center_max", 1200))
    if high > 10**9:
        return None
    harder["center_min"] = low * 4
    harder["center_max"] = high * 4
    return harder


def _candidate_from_identity_signs(inst, identity_signs):
    coordinates = [
        (1 if coefficient > 0 else -1) * identity_sign
        for coefficient, identity_sign in zip(inst["coefficients"], identity_signs)
    ]
    return _vector_json([1] + coordinates)


def _outlier_candidate(inst):
    order = sorted(range(inst["n"]), key=lambda i: abs(inst["coefficients"][i]))
    identity = [-1] * inst["n"]
    for index in order[: inst["n"] // 2]:
        identity[index] = 1
    return _candidate_from_identity_signs(inst, identity)


def _sorted_alternation_candidate(inst):
    order = sorted(range(inst["n"]), key=lambda i: abs(inst["coefficients"][i]))
    identity = [0] * inst["n"]
    for rank, index in enumerate(order):
        identity[index] = 1 if rank % 2 == 0 else -1
    return _candidate_from_identity_signs(inst, identity)


def _compact_symmetry_candidate(inst, modulus=1000):
    """Execute the intended Track B route using only displayed coefficients."""
    buckets = {}
    for index, coefficient in enumerate(inst["coefficients"]):
        buckets.setdefault(abs(coefficient) % modulus, []).append(index)
    if len(buckets) != inst["n"] // 4 or any(
        len(indices) != 4 for indices in buckets.values()
    ):
        return None
    identity = [0] * inst["n"]
    for indices in buckets.values():
        ordered = sorted(indices, key=lambda i: abs(inst["coefficients"][i]))
        outer = {ordered[0], ordered[3]}
        outer_sum = sum(abs(inst["coefficients"][index]) for index in outer)
        inner_sum = sum(
            abs(inst["coefficients"][index]) for index in ordered[1:3]
        )
        if outer_sum != inner_sum:
            return None
        for index in indices:
            identity[index] = 1 if index in outer else -1
    return _candidate_from_identity_signs(inst, identity)


def _karmarkar_karp_candidate(inst):
    heap = []
    serial = 0
    for index, coefficient in enumerate(inst["coefficients"]):
        vector = {index: 1}
        heapq.heappush(heap, (-abs(coefficient), serial, vector))
        serial += 1
    while len(heap) > 1:
        neg_a, _, vec_a = heapq.heappop(heap)
        neg_b, _, vec_b = heapq.heappop(heap)
        merged = dict(vec_a)
        for index, sign in vec_b.items():
            merged[index] = -sign
        heapq.heappush(heap, (-((-neg_a) - (-neg_b)), serial, merged))
        serial += 1
    identity = [0] * inst["n"]
    for index, sign in heap[0][2].items():
        identity[index] = sign
    return _candidate_from_identity_signs(inst, identity)


def _bitset_partition(inst, checkpoint_stride=8):
    """Standard pseudo-polynomial subset-sum DP with exact reconstruction."""
    weights = [abs(value) for value in inst["coefficients"]]
    total = sum(weights)
    if total % 2:
        return None, {"word_operations": 0, "target": total // 2}
    target = total // 2
    mask = (1 << (target + 1)) - 1
    checkpoints = {0: 1}
    bits = 1
    prefix_sum = 0
    word_operations = 0
    for position, weight in enumerate(weights, 1):
        word_operations += (min(prefix_sum, target) + 64) // 64
        bits = (bits | (bits << weight)) & mask
        prefix_sum += weight
        if position % checkpoint_stride == 0 or position == len(weights):
            checkpoints[position] = bits
    if ((bits >> target) & 1) == 0:
        return None, {"word_operations": word_operations, "target": target}

    included = [False] * len(weights)
    position = len(weights)
    remaining = target
    prefix_sums = [0]
    for weight in weights:
        prefix_sums.append(prefix_sums[-1] + weight)
    while position:
        start = ((position - 1) // checkpoint_stride) * checkpoint_stride
        local = [checkpoints[start]]
        local_bits = local[0]
        for index in range(start, position):
            word_operations += (min(prefix_sums[index], target) + 64) // 64
            local_bits = (local_bits | (local_bits << weights[index])) & mask
            local.append(local_bits)
        for index in range(position - 1, start - 1, -1):
            before = local[index - start]
            if (before >> remaining) & 1:
                included[index] = False
            elif remaining >= weights[index] and (
                (before >> (remaining - weights[index])) & 1
            ):
                included[index] = True
                remaining -= weights[index]
            else:
                raise RuntimeError("subset-sum reconstruction invariant failed")
        position = start
    if remaining != 0:
        raise RuntimeError("subset-sum reconstruction ended at a nonzero target")
    identity = [1 if chosen else -1 for chosen in included]
    answer = _candidate_from_identity_signs(inst, identity)
    return answer, {
        "word_operations": word_operations,
        "target": target,
        "checkpoint_stride": checkpoint_stride,
    }


def _relabel_instance(inst, rng, permute=False, sign_switch=False, scale=1):
    out = copy.deepcopy(inst)
    coefficients = list(out["coefficients"])
    answer = copy.deepcopy(out["answer"])
    n = out["n"]
    if sign_switch:
        switches = [rng.choice((-1, 1)) for _ in range(n)]
        coefficients = [c * t for c, t in zip(coefficients, switches)]
        answer = [answer[0]] + [
            _rational_json(Fraction(pair[0], pair[1]) * t)
            for pair, t in zip(answer[1:], switches)
        ]
    if permute:
        permutation = list(range(n))
        rng.shuffle(permutation)
        coefficients = [coefficients[index] for index in permutation]
        answer = [answer[0]] + [answer[index + 1] for index in permutation]
    coefficients = [scale * value for value in coefficients]
    out["coefficients"] = coefficients
    out["answer"] = answer
    return out


def _answer_atoms(answer):
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, (list, tuple)):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest():
    report = {}

    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **shipping_params)

    # G2 deliberately reaches five separate validation branches.
    signs = [Fraction(pair[0], pair[1]) for pair in inst["answer"][1:]]
    negative = next(i for i, value in enumerate(signs, 1) if value == -1)
    positive = next(i for i, value in enumerate(signs, 1) if value == 1)
    dropped = copy.deepcopy(inst["answer"][:-1])
    swapped = copy.deepcopy(inst["answer"])
    swapped[0], swapped[negative] = swapped[negative], swapped[0]
    duplicated = copy.deepcopy(inst["answer"])
    duplicated[negative] = copy.deepcopy(duplicated[positive])
    out_of_range = copy.deepcopy(inst["answer"])
    out_of_range[1] = [2, 1]
    corruptions = {}
    for name, candidate in (
        ("drop", dropped),
        ("swap", swapped),
        ("duplicate", duplicated),
        ("empty", []),
        ("out_of_range", out_of_range),
    ):
        ok, reason = verify(inst, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in corruptions.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruptions,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The common projective root follows from exact cancellation.\n\n"
        "<answer>\n```text\n"
        + _answer_text(inst["answer"])
        + "\n```\n</answer>\nThis is normalized by x_0=1."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"],
        "parsed_coordinates": len(parsed) if isinstance(parsed, list) else None,
    }

    sample_total = 200_000
    sample_rng = random.Random(0x12101451)
    sample_hits = 0
    sample_start = time.perf_counter()
    coefficients = inst["coefficients"]
    for _ in range(sample_total):
        candidate = random_candidate(inst, sample_rng)
        # random_candidate already enforces normalization, shape, and all n
        # quadratic equations.  The remaining exact check is F_0.
        if sum(c * pair[0] for c, pair in zip(coefficients, candidate[1:])) == 0:
            sample_hits += 1
    sample_seconds = time.perf_counter() - sample_start
    observed = sample_hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "observed_probability": observed,
        "candidate_space": search_space(inst),
        "prior": "uniform over normalized sign vectors already satisfying every F_i, i>=1",
    }

    attack_names = (
        "outlier_smallest_half",
        "greedy_karmarkar_karp",
        "random_sign_restart_256",
        "by_hand_sorted_alternation",
    )
    attack_successes = {name: 0 for name in attack_names}
    reference_successes = 0
    reference_times = []
    reference_operations = []
    attack_seeds = list(range(800, 808))
    for seed in attack_seeds:
        attack_inst = make_instance(seed=seed, **shipping_params)
        if verify(attack_inst, _outlier_candidate(attack_inst))[0]:
            attack_successes["outlier_smallest_half"] += 1
        if verify(attack_inst, _karmarkar_karp_candidate(attack_inst))[0]:
            attack_successes["greedy_karmarkar_karp"] += 1
        restart_rng = random.Random(seed ^ 0xA55A)
        restart_won = False
        for _ in range(256):
            if verify(attack_inst, random_candidate(attack_inst, restart_rng))[0]:
                restart_won = True
                break
        attack_successes["random_sign_restart_256"] += int(restart_won)
        if verify(attack_inst, _sorted_alternation_candidate(attack_inst))[0]:
            attack_successes["by_hand_sorted_alternation"] += 1

        started = time.perf_counter()
        reference_answer, stats = _bitset_partition(attack_inst)
        elapsed = time.perf_counter() - started
        solved = reference_answer is not None and verify(
            attack_inst, reference_answer
        )[0]
        reference_successes += int(solved)
        reference_times.append(elapsed)
        reference_operations.append(stats["word_operations"])

    median_wall = statistics.median(reference_times)
    median_operations = int(statistics.median(reference_operations))
    attacks = {
        name: {"successes": attack_successes[name], "attempts": len(attack_seeds)}
        for name in attack_names
    }
    report["G6_adversary_panel"] = {
        "pass": all(entry["successes"] == 0 for entry in attacks.values())
        and reference_successes == len(attack_seeds),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "bitset subset-sum dynamic programming with exact backtracking",
            "complexity": "O(nS/w) word operations and O((n/k+k)S) bits with checkpoints",
            "wall_clock_sec_median": median_wall,
            "operations_median_64bit_word_transitions": median_operations,
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
    }

    demo_inst = make_instance(seed=11, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    report["G5_density_and_baseline_cost"] = {
        "pass": observed < 1e-6
        and demo_count is not None
        and reference_successes == len(attack_seeds),
        "shipping_density_hits": sample_hits,
        "shipping_density_samples": sample_total,
        "shipping_density_fraction": observed,
        "shipping_sampling_wall_seconds": sample_seconds,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo_inst),
        "baseline_wall_seconds_median": median_wall,
        "baseline_word_operations_median": median_operations,
    }

    ladder_bits = [params["n"] for params in DIFFICULTY.values()]
    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    build_start = time.perf_counter()
    doubled = make_instance(seed=31337, **doubled_params)
    doubled_build = time.perf_counter() - build_start
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": all(a < b for a, b in zip(ladder_bits, ladder_bits[1:]))
        and doubled_ok,
        "ladder_log2_candidate_spaces": ladder_bits,
        "doubled_n": doubled_params["n"],
        "doubled_build_seconds": doubled_build,
        "doubled_verify_reason": doubled_why,
    }

    invariance_checks = 0
    carried_checks = 0
    g8_failures = []
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(seed=10_000 + seed, **shipping_params)
        key = canonical_key(base)
        unrelated_keys.append(key)
        transforms = (
            {"permute": True},
            {"sign_switch": True},
            {"scale": 3},
            {"permute": True, "sign_switch": True, "scale": 5},
        )
        for index, flags in enumerate(transforms):
            moved = _relabel_instance(base, random.Random(seed * 101 + index), **flags)
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
        "method": "sorted absolute primitive coefficient multiset",
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    blocks = inst["n"] // 4
    intended_operations = 4 * inst["n"] + 7 * blocks
    compact_route_checks = 0
    for seed in range(8):
        route_inst = make_instance(seed=90_000 + seed, **shipping_params)
        route_answer = _compact_symmetry_candidate(route_inst)
        compact_route_checks += int(
            route_answer is not None and verify(route_inst, route_answer)[0]
        )
    arms = copy.deepcopy(G9_RESULTS["arms"])
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / max(1, hinted_attempts)
    placebo_rate = arms["placebo"]["solved"] / max(1, placebo_attempts)
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps and compact_route_checks == 8,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "compact_route_checks": compact_route_checks,
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
