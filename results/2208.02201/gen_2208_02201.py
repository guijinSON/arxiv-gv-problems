"""Structured exact LPN witness problems from arXiv:2208.02201.

Section 3 of the paper turns binary decoding into Learning Parity with Noise
(LPN) samples and identifies maximum-likelihood recovery with a Walsh--Hadamard
maximisation.  This module inverse-generates finite exact instances of that
native problem.  Generic recovery scans millions of secrets at shipping size;
a hidden quadratic evaluation structure gives a short exact route if noticed.
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
import time
from typing import Any


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "labeled LPN samples over F_2",
        "binary secret vector",
        "exact noise Hamming weight",
    ],
    "verification_operations": [
        "exact parity inner product over F_2",
        "exact xor of binary sample columns",
        "exact Hamming-distance comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Viewing the labeled samples as a permuted quadratic Boolean evaluation "
        "table turns noisy maximum-likelihood search into Mobius interpolation "
        "on singleton and pair labels."
    ),
    "hardness_basis": (
        "Track B: Section 3.2 gives Walsh--Hadamard maximum-likelihood recovery "
        "in O(s*2^s), measured at 48,234,493 exact operations and 2.313 s for "
        "shipping s=21; "
        "the stronger exact word-parallel Gray scan measured a median 1,435,390 "
        "candidates, 4,306,170 word operations, and 0.330 s, while the hidden "
        "quadratic change of variables leaves a 60-xor route once noticed."
    ),
    "max_answer_tokens": 14,
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

# n is the number of samples, m=log2(n), and the secret dimension is
# s=m+binom(m,2).  The non-demo noise radius is one below half the minimum
# distance 2^(m-2) of the containing Reed--Muller code RM(2,m).
DIFFICULTY = {
    "demo": {"n": 8, "noise_weight": 0},
    "easy": {"n": 64, "noise_weight": 7},
    "medium": {"n": 128, "noise_weight": 15},
    "hard": {"n": 256, "noise_weight": 31},
}

SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "A degree-two Boolean polynomial's Mobius coefficients are determined by "
    "its values on inputs of Hamming weight at most two."
)
PLACEBO_HINT = (
    "A binary sample table's coordinate conventions determine how its feature "
    "and response bits should be interpreted."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A nonempty strictly increasing JSON list of feature indices from 0 "
        "through s-1; it is the support of the nonzero binary LPN secret."
    ),
    "bounds": {
        "binary_coefficients": 1,
        "nonempty": 1,
        "strictly_increasing": 1,
        "max_support_size_named_ladder": 36,
        "max_feature_index_named_ladder": 35,
        "max_support_size_before_effort_cap": 78,
    },
}

# Filled from the script-owned oracle attempts.  Provider errors are not model
# failures; zero scored attempts therefore makes no oracle hardness claim.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0, "provider_errors": 4},
    "hinted": {"solved": 0, "attempts": 0, "provider_errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "provider_errors": 4},
    "hinted_verdict": "unavailable_provider_error",
}

NOTES = r"""
Problem 1.2 defines LPN samples (a,<secret,a>+noise) over F_2. Section 3.1
obtains these objects from restricted dual codewords. Section 3.2 defines the
sample code and proves hat(f)(x)=N-2*distance(response,codeword_x), so exact ML
recovery is a Walsh--Hadamard maximisation. The finite witness problem here
includes the exact noise weight, making a candidate executable to grade.

The generator samples a nonzero secret before constructing any response. For
m=log2(n), its feature rows are evaluations of all nonconstant square-free
monomials of degree at most two on F_2^m, with the feature coordinates randomly
permuted. Noise is planted only at public labels of Hamming weight at least
three, and one such error lies in the naive first-basis linear solve. The answer
is known by inverse generation; no decoder is run to obtain it.

These rows generate a coordinate-permuted zero-constant subcode of RM(2,m).
Its distance is at least 2^(m-2), while named non-demo noise is 2^(m-3)-1.
Thus the planted secret is unique. verify() does not rely on that theorem: it
recomputes all candidate parity predictions and the exact residual weight.

The Step-0 certificate producer is explicit in Section 3.2: a WHT costs
O(s*2^s), or 44,040,192 scalar additions at shipping s=21. selftest runs that
transform exactly (48,234,493 additions plus comparisons, 2.313 seconds) and
also measures a stronger exact word-parallel Gray-order ML scan. The compact
route notices that singleton labels isolate permuted
linear monomials and that a pair row xor its singleton rows isolates one
quadratic monomial; the identical response xor recovers its coefficient. The
15 pairs at m=6 cost 15*(2+2)=60 exact xors after the insight.

Section 1.1 identifies generic high-noise decoding as polynomial and explains
that solutions proliferate above the GV distance. For this structured family,
zero noise plus an exposed basis would be ordinary elimination, and exposing
the monomial permutation makes interpolation immediate. Only the demo is in
that hand-scale zero-noise regime.

Four attacks are measured over eight shipping seeds. Secret coordinates are a
uniform nonzero subset independent of the feature permutation, defeating
per-coordinate outliers. The panel tries one-feature correlation, greedy
coordinate descent, 2,048 uniform legal restarts, and the in-context ansatz
that the first independent displayed equations are noise-free. The last is
forced wrong by construction. Exact ML succeeds 8/8 as Track B requires and is
reported separately as reference_algorithm.

canonical_key removes sample order and feature-coordinate permutation and then
minimizes the response truth table over all m! permutations of public label
bits. G8 tests each map, compositions, carried witnesses, and unrelated seeds.
Broader linear equivalences of the sample code are not canonicalized; the
README records that limitation.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 250_000
_RANDOM_RESTARTS = 2_048


def _dimension(m: int) -> int:
    return m + m * (m - 1) // 2


def _monomial_vector(x: int, m: int) -> int:
    """Evaluations of x_i and x_i*x_j (i<j), packed in canonical order."""
    value = 0
    for i in range(m):
        if (x >> i) & 1:
            value |= 1 << i
    position = m
    for i in range(m):
        for j in range(i + 1, m):
            if ((x >> i) & 1) and ((x >> j) & 1):
                value |= 1 << position
            position += 1
    return value


def _permute_bits(value: int, permutation: list[int]) -> int:
    """Apply permutation[new position] = old position."""
    result = 0
    for new, old in enumerate(permutation):
        if (value >> old) & 1:
            result |= 1 << new
    return result


def _independent_sample_indices(samples: list[list[int]], dimension: int) -> list[int]:
    basis: dict[int, int] = {}
    selected: list[int] = []
    for sample_index, (_, feature, _) in enumerate(samples):
        value = feature
        while value:
            pivot = value.bit_length() - 1
            if pivot in basis:
                value ^= basis[pivot]
            else:
                basis[pivot] = value
                selected.append(sample_index)
                break
        if len(selected) == dimension:
            return selected
    raise RuntimeError("sample feature rows do not have full rank")


def _packed_columns(samples: list[list[int]], dimension: int) -> tuple[list[int], int]:
    columns = [0] * dimension
    response = 0
    for row, (_, feature, bit) in enumerate(samples):
        response |= bit << row
        value = feature
        while value:
            low = value & -value
            columns[low.bit_length() - 1] |= 1 << row
            value ^= low
    return columns, response


def make_instance(
    n: int,
    seed: int = 0,
    noise_weight: int | None = None,
    **params: Any,
) -> dict:
    """Inverse-generate a labeled finite LPN maximum-likelihood instance."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    for name, value in (("n", n), ("seed", seed)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if n < 8 or n & (n - 1):
        raise ValueError("n must be a power of two and at least 8")
    m = n.bit_length() - 1
    dimension = _dimension(m)
    if noise_weight is None:
        noise_weight = max(0, (1 << (m - 3)) - 1)
    if isinstance(noise_weight, bool) or not isinstance(noise_weight, int):
        raise ValueError("noise_weight must be an integer")
    half_distance = 1 << (m - 3)
    eligible_labels = [x for x in range(n) if x.bit_count() >= 3]
    if not 0 <= noise_weight < half_distance:
        raise ValueError("noise_weight must be below 2^(log2(n)-3)")
    if noise_weight > len(eligible_labels):
        raise ValueError("not enough labels of Hamming weight at least three")

    rng = random.Random(seed)
    feature_permutation = list(range(dimension))
    rng.shuffle(feature_permutation)
    secret_mask = rng.randrange(1, 1 << dimension)
    features = [
        _permute_bits(_monomial_vector(x, m), feature_permutation)
        for x in range(n)
    ]

    # Randomize presentation while ensuring a high-weight label occurs in the
    # first independent basis, so the explicitly tested noise-free ansatz fails.
    order = list(range(n))
    blank = [[x, features[x], 0] for x in range(n)]
    for _ in range(10_000):
        rng.shuffle(order)
        ordered = [blank[x] for x in order]
        pivots = _independent_sample_indices(ordered, dimension)
        eligible_pivots = [
            ordered[row][0] for row in pivots if ordered[row][0].bit_count() >= 3
        ]
        if eligible_pivots or noise_weight == 0:
            break
    else:
        raise RuntimeError("could not create a presentation with an eligible pivot")

    noise_labels: set[int] = set()
    if noise_weight:
        anchor = rng.choice(eligible_pivots)
        noise_labels.add(anchor)
        noise_labels.update(
            rng.sample([x for x in eligible_labels if x != anchor], noise_weight - 1)
        )

    samples: list[list[int]] = []
    for x in order:
        feature = features[x]
        response = (secret_mask & feature).bit_count() & 1
        response ^= int(x in noise_labels)
        samples.append([x, feature, response])
    feature_columns, response_mask = _packed_columns(samples, dimension)
    answer = [j for j in range(dimension) if (secret_mask >> j) & 1]
    return {
        "family": "labeled finite LPN maximum-likelihood recovery",
        "paper": "arXiv:2208.02201",
        "n": n,
        "label_bits": m,
        "secret_dimension": dimension,
        "noise_weight": noise_weight,
        "feature_hex_width": (dimension + 3) // 4,
        "samples": samples,
        "feature_columns": feature_columns,
        "response_mask": response_mask,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a complete finite LPN witness problem and output contract."""
    m = inst["label_bits"]
    width = inst["feature_hex_width"]
    lines = "\n".join(
        f"{x:0{m}b}  {feature:0{width}x}  {bit}"
        for x, feature, bit in inst["samples"]
    )
    statement = f"""Exact finite Learning Parity with Noise (LPN)

All arithmetic is over the binary field F_2: addition is xor and <z,a> is the
parity (0 or 1) of the coordinates where binary vectors z and a both have a 1.

There are {inst['n']} labeled samples. Each line has a public {m}-bit label x,
a feature vector a in F_2^{inst['secret_dimension']} written as exactly {width}
hexadecimal digits, and one response bit b. In a, feature 0 is the
least-significant bit of the hexadecimal integer, feature 1 is the next bit,
and so on. The x label is exact public instance data; line order has no
mathematical significance.

Find the unique nonzero secret z in F_2^{inst['secret_dimension']} for which
exactly {inst['noise_weight']} displayed equations b=<z,a> disagree. Output the
support of z: precisely the feature indices whose secret coefficient is 1.

The support must be a nonempty JSON list of distinct integers, strictly
increasing, with every index between 0 and {inst['secret_dimension'] - 1}
inclusive. Indices are zero-based, repeats are forbidden, and all data and
comparisons are exact.

number of samples: {inst['n']}
secret dimension: {inst['secret_dimension']}
required number of disagreements: {inst['noise_weight']}
sample table (x_binary  a_hex  b):
{lines}

Give your final answer inside <answer></answer> tags as one nonempty JSON list
of strictly increasing feature indices.
Example format: <answer>[0, 3]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: object) -> object | None:
    """Extract the last tagged JSON integer list, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.I | re.S)
    if fence:
        body = fence.group(1).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    if any(isinstance(item, bool) or not isinstance(item, int) for item in value):
        return None
    return value


def _candidate_codeword(inst: dict, support: list[int]) -> int:
    codeword = 0
    for index in support:
        codeword ^= inst["feature_columns"][index]
    return codeword


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any exact secret witness; never consult inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "secret support must be nonempty"
    if any(isinstance(index, bool) or not isinstance(index, int) for index in answer):
        return False, "every support entry must be an integer"
    if len(set(answer)) != len(answer):
        return False, "repeated feature indices are not allowed"
    if any(index < 0 or index >= inst["secret_dimension"] for index in answer):
        return False, f"feature index must lie in 0..{inst['secret_dimension'] - 1}"
    if answer != sorted(answer):
        return False, "feature indices must be in strictly increasing order"
    residual_weight = (
        _candidate_codeword(inst, answer) ^ inst["response_mask"]
    ).bit_count()
    if residual_weight != inst["noise_weight"]:
        return (
            False,
            f"candidate disagrees with {residual_weight} samples, expected "
            f"exactly {inst['noise_weight']}",
        )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the stated language of nonzero binary secrets."""
    mask = rng.randrange(1, 1 << inst["secret_dimension"])
    return [j for j in range(inst["secret_dimension"]) if (mask >> j) & 1]


def search_space(inst: dict) -> int:
    return (1 << inst["secret_dimension"]) - 1


def enumerate_all(inst: dict) -> int | None:
    if search_space(inst) > _ENUMERATION_CAP:
        return None
    valid = 0
    for mask in range(1, 1 << inst["secret_dimension"]):
        valid += int(verify(inst, _support_from_mask(mask, inst["secret_dimension"]))[0])
    return valid


def _permute_label(value: int, permutation: tuple[int, ...] | list[int]) -> int:
    result = 0
    for new, old in enumerate(permutation):
        result |= ((value >> old) & 1) << new
    return result


def canonical_key(inst: dict) -> str:
    """Remove sample order, feature permutations, and label-bit renamings."""
    m = inst["label_bits"]
    responses = [0] * inst["n"]
    for label, _, response in inst["samples"]:
        responses[label] = response
    best: int | None = None
    for permutation in itertools.permutations(range(m)):
        transformed = 0
        for old_label, response in enumerate(responses):
            if response:
                transformed |= 1 << _permute_label(old_label, permutation)
        if best is None or transformed < best:
            best = transformed
    payload = {
        "n": inst["n"],
        "secret_dimension": inst["secret_dimension"],
        "noise_weight": inst["noise_weight"],
        "canonical_response_table": best,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Double the sample table while the compact route stays under G9(c)."""
    clean = {key: value for key, value in params.items() if key != "_preset"}
    next_n = 2 * int(clean["n"])
    next_m = next_n.bit_length() - 1
    if 4 * math.comb(next_m, 2) > 300:
        return "cap_bound"
    return {"n": next_n, "noise_weight": (1 << (next_m - 3)) - 1}


def _support_from_mask(mask: int, dimension: int) -> list[int]:
    return [j for j in range(dimension) if (mask >> j) & 1]


def _outlier_correlation_attack(inst: dict) -> list[int]:
    base_distance = inst["response_mask"].bit_count()
    mask = 0
    for index, column in enumerate(inst["feature_columns"]):
        if (inst["response_mask"] ^ column).bit_count() < base_distance:
            mask |= 1 << index
    return _support_from_mask(mask, inst["secret_dimension"])


def _greedy_coordinate_attack(inst: dict) -> list[int]:
    mask = 0
    codeword = 0
    distance = inst["response_mask"].bit_count()
    seen = {mask}
    for _ in range(4 * inst["secret_dimension"]):
        next_distance, index = min(
            ((codeword ^ col ^ inst["response_mask"]).bit_count(), j)
            for j, col in enumerate(inst["feature_columns"])
        )
        if next_distance >= distance:
            break
        mask ^= 1 << index
        codeword ^= inst["feature_columns"][index]
        distance = next_distance
        if mask in seen:
            break
        seen.add(mask)
    return _support_from_mask(mask, inst["secret_dimension"])


def _random_restart_attack(inst: dict, seed: int) -> list[int] | None:
    rng = random.Random(seed ^ 0x220802201)
    for _ in range(_RANDOM_RESTARTS):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _solve_square_rows(rows: list[tuple[int, int]], dimension: int) -> int | None:
    augmented = [feature | (rhs << dimension) for feature, rhs in rows]
    pivot_row = 0
    for column in range(dimension):
        found = next(
            (
                row
                for row in range(pivot_row, len(augmented))
                if (augmented[row] >> column) & 1
            ),
            None,
        )
        if found is None:
            return None
        augmented[pivot_row], augmented[found] = augmented[found], augmented[pivot_row]
        for row in range(len(augmented)):
            if row != pivot_row and ((augmented[row] >> column) & 1):
                augmented[row] ^= augmented[pivot_row]
        pivot_row += 1
    solution = 0
    feature_mask = (1 << dimension) - 1
    for row in augmented:
        pivot = (row & feature_mask).bit_length() - 1
        if (row >> dimension) & 1:
            solution |= 1 << pivot
    return solution


def _noise_free_linear_ansatz(inst: dict) -> list[int]:
    selected = _independent_sample_indices(inst["samples"], inst["secret_dimension"])
    rows = [(inst["samples"][r][1], inst["samples"][r][2]) for r in selected]
    mask = _solve_square_rows(rows, inst["secret_dimension"])
    return [] if mask is None else _support_from_mask(mask, inst["secret_dimension"])


def _reference_gray_ml(inst: dict) -> tuple[list[int] | None, int, int, float]:
    """Exact ML scan in Gray order using one packed sample codeword."""
    started = time.perf_counter()
    previous_gray = 0
    codeword = 0
    operations = 0
    for ordinal in range(1, 1 << inst["secret_dimension"]):
        gray = ordinal ^ (ordinal >> 1)
        changed = (gray ^ previous_gray).bit_length() - 1
        codeword ^= inst["feature_columns"][changed]
        residual = (codeword ^ inst["response_mask"]).bit_count()
        operations += 3  # one column xor, one response xor, one exact popcount
        if residual == inst["noise_weight"]:
            return (
                _support_from_mask(gray, inst["secret_dimension"]),
                ordinal,
                operations,
                time.perf_counter() - started,
            )
        previous_gray = gray
    return None, search_space(inst), operations, time.perf_counter() - started


def _reference_walsh_hadamard(
    inst: dict,
) -> tuple[list[int] | None, int, int, int, float]:
    """Run Section 3.2's exact Walsh--Hadamard maximum-likelihood algorithm."""
    started = time.perf_counter()
    size = 1 << inst["secret_dimension"]
    spectrum = [0] * size
    for _, feature, response in inst["samples"]:
        spectrum[feature] += 1 if response == 0 else -1

    additions = 0
    half = 1
    while half < size:
        block = 2 * half
        for start in range(0, size, block):
            stop = start + half
            for left in range(start, stop):
                right = left + half
                a = spectrum[left]
                b = spectrum[right]
                spectrum[left] = a + b
                spectrum[right] = a - b
                additions += 2
        half = block

    # The certificate language excludes the zero secret.
    best_index = 1
    best_value = spectrum[1]
    target_value = inst["n"] - 2 * inst["noise_weight"]
    valid_count = int(spectrum[1] == target_value)
    comparisons = 1
    for index in range(2, size):
        comparisons += 2
        valid_count += int(spectrum[index] == target_value)
        if spectrum[index] > best_value:
            best_index = index
            best_value = spectrum[index]
    return (
        _support_from_mask(best_index, inst["secret_dimension"]),
        additions,
        comparisons,
        valid_count,
        time.perf_counter() - started,
    )


def _compact_mobius_recovery(inst: dict) -> tuple[list[int], int]:
    """Recover the secret through the hidden singleton/pair evaluation identity."""
    by_label = {
        label: (feature, response) for label, feature, response in inst["samples"]
    }
    m = inst["label_bits"]
    secret_mask = 0
    singleton_features: list[int] = []
    singleton_responses: list[int] = []
    for i in range(m):
        feature, response = by_label[1 << i]
        if feature.bit_count() != 1:
            raise AssertionError("singleton label did not isolate one linear feature")
        singleton_features.append(feature)
        singleton_responses.append(response)
        if response:
            secret_mask |= feature

    operations = 0
    for i in range(m):
        for j in range(i + 1, m):
            feature, response = by_label[(1 << i) | (1 << j)]
            quadratic_feature = feature ^ singleton_features[i]
            quadratic_feature ^= singleton_features[j]
            coefficient = response ^ singleton_responses[i]
            coefficient ^= singleton_responses[j]
            operations += 4
            if quadratic_feature.bit_count() != 1:
                raise AssertionError("pair label did not isolate one quadratic feature")
            if coefficient:
                secret_mask |= quadratic_feature
    return _support_from_mask(secret_mask, inst["secret_dimension"]), operations


def _permute_features(inst: dict, permutation: list[int]) -> dict:
    dimension = inst["secret_dimension"]
    if sorted(permutation) != list(range(dimension)):
        raise ValueError("not a feature permutation")
    transformed = dict(inst)
    transformed["samples"] = [
        [label, _permute_bits(feature, permutation), response]
        for label, feature, response in inst["samples"]
    ]
    transformed["feature_columns"], transformed["response_mask"] = _packed_columns(
        transformed["samples"], dimension
    )
    old_mask = sum(1 << index for index in inst["answer"])
    transformed["answer"] = _support_from_mask(
        _permute_bits(old_mask, permutation), dimension
    )
    return transformed


def _permute_label_bits(inst: dict, permutation: list[int]) -> dict:
    if sorted(permutation) != list(range(inst["label_bits"])):
        raise ValueError("not a label-bit permutation")
    transformed = dict(inst)
    transformed["samples"] = [
        [_permute_label(label, permutation), feature, response]
        for label, feature, response in inst["samples"]
    ]
    return transformed


def _reorder_samples(inst: dict, permutation: list[int]) -> dict:
    if sorted(permutation) != list(range(inst["n"])):
        raise ValueError("not a sample permutation")
    transformed = dict(inst)
    transformed["samples"] = [inst["samples"][old] for old in permutation]
    transformed["feature_columns"], transformed["response_mask"] = _packed_columns(
        transformed["samples"], inst["secret_dimension"]
    )
    return transformed


def _answer_atoms(answer: object) -> int:
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest() -> dict:
    """Run every mandatory construction, hardness, diversity, and size gate."""
    report: dict[str, object] = {}

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 2025):
            instance = make_instance(seed=seed, **params)
            ok, reason = verify(instance, instance["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, reason])
            if json.loads(json.dumps(instance["answer"])) != instance["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=271828, **shipping_params)
    base = list(inst["answer"])
    swapped = list(base)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicate = list(base)
    duplicate[1] = duplicate[0]
    outside = list(base)
    outside[-1] = inst["secret_dimension"]
    corruptions = {
        "drop_one": base[:-1],
        "swap_adjacent": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": outside,
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = [case["reason"] for case in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and len(set(reasons)) == 5,
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    blob = json.dumps(inst["answer"], separators=(",", ":"))
    model_response = (
        "I evaluated the binary parities and counted the residuals.\n"
        f"<answer>```json\n{blob}\n```</answer>\n"
        "The listed feature indices are zero-based."
    )
    parsed = parse_answer(model_response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0],
        "parsed_exactly": parsed == inst["answer"],
    }

    density_samples = 200_000
    density_rng = random.Random(0x220802201)
    hits = 0
    started = time.perf_counter()
    for _ in range(density_samples):
        hits += int(verify(inst, random_candidate(inst, density_rng))[0])
    density_elapsed = time.perf_counter() - started
    observed_probability = hits / density_samples
    exact_probability = 1 / search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": exact_probability < 1e-6 and observed_probability < 1e-6,
        "hits": hits,
        "total": density_samples,
        "observed_probability": observed_probability,
        "exact_probability_from_unique_witness": exact_probability,
        "structure_aware": True,
        "candidate_space": search_space(inst),
        "candidate_space_bits": round(math.log2(search_space(inst)), 6),
        "wall_clock_sec": round(density_elapsed, 6),
    }

    demo_inst = make_instance(seed=11, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    wht_candidate, wht_additions, wht_comparisons, wht_valid_count, wht_elapsed = (
        _reference_walsh_hadamard(inst)
    )
    wht_ok = wht_candidate is not None and verify(inst, wht_candidate)[0]
    reference_records = []
    reference_successes = 0
    compact_successes = 0
    compact_operation_counts = []
    for seed in range(8):
        attack_inst = make_instance(seed=10_000 + seed, **shipping_params)
        candidate, iterations, operations, elapsed = _reference_gray_ml(attack_inst)
        solved = candidate is not None and verify(attack_inst, candidate)[0]
        reference_successes += int(solved)
        compact_candidate, compact_operations = _compact_mobius_recovery(attack_inst)
        compact_ok = verify(attack_inst, compact_candidate)[0]
        compact_successes += int(compact_ok)
        compact_operation_counts.append(compact_operations)
        reference_records.append(
            {
                "seed": 10_000 + seed,
                "solved": solved,
                "candidate_iterations": iterations,
                "word_operations": operations,
                "wall_clock_sec": round(elapsed, 6),
            }
        )
    iterations = [r["candidate_iterations"] for r in reference_records]
    operations = [r["word_operations"] for r in reference_records]
    times = [r["wall_clock_sec"] for r in reference_records]
    report["G5_density_and_baseline_cost"] = {
        "pass": observed_probability < 1e-6
        and reference_successes == 8
        and compact_successes == 8
        and wht_ok
        and wht_valid_count == 1
        and demo_count == 1,
        "shipping_density_hits": hits,
        "shipping_density_samples": density_samples,
        "shipping_observed_fraction": observed_probability,
        "shipping_exact_solution_count_measured_by_wht": wht_valid_count,
        "shipping_solution_count_distance_guarantee": 1,
        "exact_demo_solution_count": demo_count,
        "exact_demo_candidate_space": search_space(demo_inst),
        "baseline_algorithm": "exact bit-packed Gray-order maximum-likelihood scan",
        "baseline_successes": reference_successes,
        "baseline_attempts": 8,
        "baseline_candidate_iterations_median": int(statistics.median(iterations)),
        "baseline_word_operations_median": int(statistics.median(operations)),
        "baseline_wall_clock_sec_median": round(statistics.median(times), 6),
        "baseline_wall_clock_sec_max": round(max(times), 6),
        "paper_walsh_hadamard_scalar_additions": wht_additions,
        "paper_walsh_hadamard_comparisons": wht_comparisons,
        "paper_walsh_hadamard_wall_clock_sec": round(wht_elapsed, 6),
        "paper_walsh_hadamard_verified": wht_ok,
        "compact_route_successes": compact_successes,
        "compact_route_attempts": 8,
        "compact_route_operations": max(compact_operation_counts),
        "records": reference_records,
    }

    attack_results = {
        "outlier_one_feature_correlation": {"successes": 0, "attempts": 8},
        "greedy_coordinate_descent": {"successes": 0, "attempts": 8},
        "random_restart_2048": {"successes": 0, "attempts": 8},
        "noise_free_first_basis_ansatz": {"successes": 0, "attempts": 8},
    }
    for seed in range(8):
        attack_inst = make_instance(seed=10_000 + seed, **shipping_params)
        candidates = {
            "outlier_one_feature_correlation": _outlier_correlation_attack(attack_inst),
            "greedy_coordinate_descent": _greedy_coordinate_attack(attack_inst),
            "random_restart_2048": _random_restart_attack(attack_inst, seed),
            "noise_free_first_basis_ansatz": _noise_free_linear_ansatz(attack_inst),
        }
        for name, candidate in candidates.items():
            if candidate is not None and verify(attack_inst, candidate)[0]:
                attack_results[name]["successes"] += 1
    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed
        and reference_successes == 8
        and compact_successes == 8
        and wht_ok,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "Section 3.2 Walsh--Hadamard maximum-likelihood recovery",
            "complexity": "O(s*2^s) exact scalar additions plus O(2^s) comparisons",
            "wall_clock_sec": round(wht_elapsed, 6),
            "operations": wht_additions + wht_comparisons,
            "additions": wht_additions,
            "comparisons": wht_comparisons,
            "solves": "1/1 measured shipping instance, as expected",
            "stronger_practical_control": {
                "name": "bit-packed Gray-order exact ML scan",
                "complexity": "O(2^s) fixed-width word xor/popcount operations for N=64",
                "wall_clock_sec_median": round(statistics.median(times), 6),
                "operations_median": int(statistics.median(operations)),
                "solves": f"{reference_successes}/8",
            },
        },
    }

    doubled = make_instance(
        seed=314159,
        n=2 * inst["n"],
        noise_weight=2 * inst["noise_weight"] + 1,
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst),
        "base_n": inst["n"],
        "doubled_n": doubled["n"],
        "base_secret_dimension": inst["secret_dimension"],
        "doubled_secret_dimension": doubled["secret_dimension"],
        "base_search_bits": round(math.log2(search_space(inst)), 6),
        "doubled_search_bits": round(math.log2(search_space(doubled)), 6),
        "doubled_verification": doubled_reason,
        "escalation_axes": ["n", "noise_weight"],
    }

    direct_invariance = composed_invariance = label_invariance = 0
    direct_carried = composed_carried = label_carried = 0
    unrelated_keys = []
    for seed in range(20):
        original = make_instance(seed=30_000 + seed, **shipping_params)
        key = canonical_key(original)
        unrelated_keys.append(key)
        feature_perm = list(range(original["secret_dimension"]))
        random.Random(seed ^ 0xC0FFEE).shuffle(feature_perm)
        transformed = _permute_features(original, feature_perm)
        direct_invariance += int(canonical_key(transformed) == key)
        direct_carried += int(verify(transformed, transformed["answer"])[0])
        sample_perm = list(range(original["n"]))
        random.Random(seed ^ 0xBAD5EED).shuffle(sample_perm)
        composed = _reorder_samples(transformed, sample_perm)
        composed_invariance += int(canonical_key(composed) == key)
        composed_carried += int(verify(composed, composed["answer"])[0])
        label_perm = list(range(original["label_bits"]))
        random.Random(seed ^ 0xA11CE).shuffle(label_perm)
        relabeled = _permute_label_bits(composed, label_perm)
        label_invariance += int(canonical_key(relabeled) == key)
        label_carried += int(verify(relabeled, relabeled["answer"])[0])
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": direct_invariance == 20
        and composed_invariance == 20
        and label_invariance == 20
        and direct_carried == 20
        and composed_carried == 20
        and label_carried == 20
        and distinct_keys == 20,
        "direct_feature_relabelling_invariance": direct_invariance,
        "composed_feature_and_sample_invariance": composed_invariance,
        "label_variable_relabelling_invariance": label_invariance,
        "direct_valid_carried_witnesses": direct_carried,
        "composed_valid_carried_witnesses": composed_carried,
        "label_valid_carried_witnesses": label_carried,
        "distinct_unrelated_keys": distinct_keys,
        "unrelated_attempts": 20,
        "key_kind": (
            "response truth table minimized over label-variable permutations; "
            "sample and feature order removed"
        ),
    }

    answer_chars = len(json.dumps(inst["answer"], separators=(",", ":")))
    answer_elements = _answer_atoms(inst["answer"])
    answer_tokens = math.ceil(answer_chars / 4)
    worst_answer = list(range(inst["secret_dimension"]))
    worst_chars = len(json.dumps(worst_answer, separators=(",", ":")))
    worst_tokens = math.ceil(worst_chars / 4)
    intended_operations = 4 * math.comb(inst["label_bits"], 2)
    compact_gate_answer, compact_gate_operations = _compact_mobius_recovery(inst)
    compact_gate_ok = verify(inst, compact_gate_answer)[0]
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_attempts = arms["hinted"].get("attempts", 0)
    placebo_attempts = arms["placebo"].get("attempts", 0)
    hinted_rate = arms["hinted"].get("solved", 0) / hinted_attempts if hinted_attempts else None
    placebo_rate = arms["placebo"].get("solved", 0) / placebo_attempts if placebo_attempts else None
    hinted_minus_placebo = (
        hinted_rate - placebo_rate
        if hinted_rate is not None and placebo_rate is not None
        else None
    )
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
        and worst_tokens <= PROBLEM_PROFILE["max_answer_tokens"]
        and compact_gate_ok
        and compact_gate_operations == intended_operations
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS.get("hinted_verdict", "pending"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_chars,
        "measured_worst_case_answer_tokens": worst_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "intended_route": "15 pair labels times two feature xors and two response xors",
        "intended_route_verified": compact_gate_ok,
        "within_caps": within_caps,
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
