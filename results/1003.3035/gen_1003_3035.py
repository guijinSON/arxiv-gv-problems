"""Verified instances of divided-power cubic decomposition from arXiv:1003.3035.

The family stays in the paper's native algebraic objects.  It asks for a compact
change-of-variables certificate showing that a rational cubic is in the GL orbit
of a divided-power Fermat cubic.  Instances are generated from a hidden Walsh
character table; verification expands every proposed divided-power cube exactly.
"""

import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - exercised without repo root
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "cubic form over Q in the divided-power monomial basis",
        "GL change of variables encoded by a Walsh-character table",
    ],
    "verification_operations": [
        "reconstruct integer linear forms",
        "expand divided-power cubes",
        "exact integer coefficient comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize a hidden Walsh-character change of variables in the cubic "
        "coefficient tensor; without it one forms and solves dense exact "
        "contraction matrices."
    ),
    "hardness_basis": (
        "Track B: exact contraction/matrix-pencil recovery is O(n^4); at the "
        "shipping n=32 preset the implemented reference algorithm solves 8/8 "
        "instances using 2,297,919 exact-operation slots in 2.539553 seconds "
        "(measured median), whereas the Walsh insight uses 255 "
        "small exact operations."
    ),
    "max_answer_tokens": 57,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 4, "scale_floor": 2},
    "easy": {"n": 8, "scale_floor": 5},
    "medium": {"n": 16, "scale_floor": 9},
    "hard": {"n": 32, "scale_floor": 17},
}
SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object with a permutation labels of 0..n-1 and an integer "
        "vector scales whose absolute values are a permutation of "
        "scale_floor..scale_floor+n-1; together they specify n Walsh-character "
        "linear forms exactly."
    ),
    "bounds": {
        "max_shipping_n": 32,
        "label_entries": 32,
        "scale_entries": 32,
        "scale_abs_max": 48,
    },
}

STRUCTURAL_HINT = (
    "Look for a hidden Walsh-character change of variables in the cubic coefficient tensor."
)
PLACEBO_HINT = (
    "Keep the divided-power indexing conventions consistent throughout the coefficient calculations."
)

# Filled from the separately run hardening arms.  They are diagnostics, not gates.
G9_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}

HARDENING_OUTCOME = {
    "verdict": "cap_bound",
    "reason": (
        "The n=32 hard preset was solved by 2 of 3 bare oracles; the next n=64 "
        "route requires 575 intended operations, above the 300-operation no-tool "
        "cap. The family is parked, not rejected or shipped."
    ),
}

NOTES = (
    "Section 1, especially Definition 1.4, Lemma 1.6, and Theorem 1.7, fixes "
    "the native object: a cubic in the divided-power algebra and a sum of "
    "divided cubes, up to GL.  Lemma 1.5 says that a canonical-curve "
    "decomposition must span all variables, which our invertible character "
    "matrix does.  Theorem 1.7 makes the Fermat/GL orbit the easy low-apolarity "
    "case; that forces Track B rather than Track A.  The generic mechanical "
    "route is exact contraction-matrix recovery.  The construction hides a "
    "Walsh character table under an independent coordinate permutation and "
    "independent signed row scales.  This defeats displayed-order, coefficient-"
    "outlier, random-restart, and Gray-order guesses while leaving an exact "
    "single-slice change-of-variables shortcut."
)


def _is_power_of_two(n):
    return isinstance(n, int) and not isinstance(n, bool) and n >= 1 and not (n & (n - 1))


def _fwht(values):
    """Unnormalised Walsh-Hadamard transform over the integers."""
    out = list(values)
    width = 1
    while width < len(out):
        for start in range(0, len(out), 2 * width):
            for j in range(start, start + width):
                a, b = out[j], out[j + width]
                out[j], out[j + width] = a + b, a - b
        width *= 2
    return out


def _signed_cube_root(value):
    """Return the exact integer cube root, or None when value is not a cube."""
    if not isinstance(value, int) or isinstance(value, bool):
        return None
    sign = -1 if value < 0 else 1
    target = abs(value)
    lo, hi = 0, 1
    while hi ** 3 < target:
        hi *= 2
    while lo <= hi:
        mid = (lo + hi) // 2
        cube = mid ** 3
        if cube == target:
            return sign * mid
        if cube < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return None


def _all_triples(n):
    for i in range(n):
        for j in range(i, n):
            for k in range(j, n):
                yield i, j, k


def _coefficient_dict(inst):
    return {(t[0], t[1], t[2]): t[3] for t in inst["terms"]}


def _coefficient(coeffs, i, j, k):
    a, b, c = sorted((i, j, k))
    return coeffs.get((a, b, c), 0)


def make_instance(n, seed=0, scale_floor=None, **params):
    """Inverse-generate a cubic and its compact Walsh Waring certificate."""
    if not _is_power_of_two(n) or n < 4 or n > 64:
        raise ValueError("n must be a power of two between 4 and 64")
    if scale_floor is None:
        scale_floor = n + 1
    if (not isinstance(scale_floor, int) or isinstance(scale_floor, bool)
            or scale_floor < 1):
        raise ValueError("scale_floor must be a positive integer")
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))

    rng = random.Random(seed)
    magnitudes = list(range(scale_floor, scale_floor + n))
    for _ in range(1024):
        rng.shuffle(magnitudes)
        scales = [m if rng.randrange(2) else -m for m in magnitudes]
        spectrum = _fwht([c ** 3 for c in scales])
        # Distinct diagonal coefficients are a genericity condition used by the
        # compact inverse.  This is instance filtering, never certificate search.
        if len(set(spectrum)) == n:
            break
    else:  # extraordinarily unlikely for the stated presets
        raise RuntimeError("could not sample a distinct Walsh spectrum")

    labels = list(range(n))
    rng.shuffle(labels)
    terms = []
    for i, j, k in _all_triples(n):
        coeff = spectrum[labels[i] ^ labels[j] ^ labels[k]]
        if coeff:
            terms.append([i, j, k, coeff])

    answer = {"labels": labels, "scales": scales}
    # JSON round-tripping is part of the public contract.
    assert json.loads(json.dumps(answer)) == answer
    return {
        "n": n,
        "scale_floor": scale_floor,
        "basis": "divided_power",
        "terms": terms,
        "answer": answer,
    }


def render(inst):
    n = inst["n"]
    floor = inst["scale_floor"]
    lines = [
        "Exact divided-power cubic decomposition",
        "",
        f"Work over the rational numbers with variables y_0,...,y_{n-1}.",
        "For a multi-index alpha of total degree 3, y^[alpha] denotes a divided-power monomial.",
        "If L = sum_j a_j y_j, then the coefficient of y^[alpha] in L^[3] is",
        "the exact integer product product_j a_j^alpha_j; there is no multinomial factor.",
        "",
        "The cubic f is listed below.  A record (i,j,k): c, with 0 <= i <= j <= k < n,",
        "means coefficient c on the divided-power monomial whose three variable indices are",
        "i,j,k (repetitions give exponents 2 or 3).  Every omitted degree-3 monomial has coefficient 0.",
        "",
    ]
    row = []
    for i, j, k, coeff in inst["terms"]:
        row.append(f"({i},{j},{k}):{coeff}")
        if len(row) == 5:
            lines.append("  " + "  ".join(row))
            row = []
    if row:
        lines.append("  " + "  ".join(row))
    magnitudes = list(range(floor, floor + n))
    example_labels = list(range(n))
    example_scales = magnitudes
    lines.extend([
        "",
        "Find a compact exact decomposition certificate with these rules:",
        f"1. labels is a permutation of the integers 0,...,{n-1} (all indexing is 0-based).",
        "2. scales is an integer list of length n; order matters, signs may be positive or negative,",
        f"   and its absolute values must be exactly {magnitudes} in some order.",
        "3. For each a=0,...,n-1 define",
        "      L_a = scales[a] * sum_j (-1)^popcount(a AND labels[j]) y_j,",
        "   where AND is bitwise AND and popcount is the number of 1 bits.",
        "   Your certificate is valid exactly when f = sum_a L_a^[3].",
        "",
        "Give your final answer inside <answer></answer> tags as one JSON object",
        'with exactly the arrays "labels" and "scales".',
        "Example of the required syntax (it is only a format example, not this instance's answer):",
        "<answer>" + json.dumps({"labels": example_labels, "scales": example_scales},
                                  separators=(",", ":")) + "</answer>",
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
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _shape_check(inst, answer):
    n = inst["n"]
    if not isinstance(answer, dict) or "labels" not in answer or "scales" not in answer:
        return False, "answer must be an object containing labels and scales"
    labels, scales = answer["labels"], answer["scales"]
    if not isinstance(labels, list) or len(labels) != n:
        return False, f"labels must contain exactly {n} entries"
    if any(not isinstance(x, int) or isinstance(x, bool) for x in labels):
        return False, "every label must be an integer"
    if any(x < 0 or x >= n for x in labels):
        return False, f"a label is outside the inclusive range 0..{n-1}"
    if len(set(labels)) != n:
        return False, "labels must not repeat"
    if not isinstance(scales, list) or len(scales) != n:
        return False, f"scales must contain exactly {n} entries"
    if any(not isinstance(x, int) or isinstance(x, bool) for x in scales):
        return False, "every scale must be an integer"
    floor = inst["scale_floor"]
    if sorted(abs(x) for x in scales) != list(range(floor, floor + n)):
        return False, "scale absolute values do not match the required magnitude set"
    return True, "ok"


def verify(inst, answer):
    """Expand every proposed divided cube and compare every coefficient exactly."""
    ok, reason = _shape_check(inst, answer)
    if not ok:
        return False, reason
    n = inst["n"]
    labels = answer["labels"]
    weights = [c ** 3 for c in answer["scales"]]

    # Nearly every bad bounded-language candidate is ruled out by one exact
    # coefficient.  Do this before materialising the 5,984-entry shipping map;
    # valid witnesses still undergo the complete expansion below.
    first_target = next((term[3] for term in inst["terms"]
                         if term[:3] == [0, 0, 0]), 0)
    first_mask = labels[0]
    first_actual = sum(-weight if ((a & first_mask).bit_count() & 1) else weight
                       for a, weight in enumerate(weights))
    if first_actual != first_target:
        return False, (
            "coefficient mismatch at divided-power monomial (0,0,0): "
            f"got {first_actual}, expected {first_target}"
        )

    target = _coefficient_dict(inst)
    for i, j, k in _all_triples(n):
        parity_mask = labels[i] ^ labels[j] ^ labels[k]
        actual = 0
        # This is literal coefficient expansion of sum_a L_a^[3].
        for a, weight in enumerate(weights):
            actual += -weight if ((a & parity_mask).bit_count() & 1) else weight
        wanted = target.get((i, j, k), 0)
        if actual != wanted:
            return False, (
                f"coefficient mismatch at divided-power monomial ({i},{j},{k}): "
                f"got {actual}, expected {wanted}"
            )
    return True, "ok"


def random_candidate(inst, rng):
    n = inst["n"]
    labels = list(range(n))
    rng.shuffle(labels)
    floor = inst["scale_floor"]
    scales = list(range(floor, floor + n))
    rng.shuffle(scales)
    scales = [x if rng.randrange(2) else -x for x in scales]
    return {"labels": labels, "scales": scales}


def search_space(inst):
    n = inst["n"]
    return math.factorial(n) * math.factorial(n) * (1 << n)


def enumerate_all(inst):
    """Brute-force the bounded language only for the 9,216-candidate demo."""
    n = inst["n"]
    if n != 4:
        return None
    floor = inst["scale_floor"]
    magnitudes = tuple(range(floor, floor + n))
    count = 0
    for labels in itertools.permutations(range(n)):
        for mag_order in itertools.permutations(magnitudes):
            for signs in itertools.product((-1, 1), repeat=n):
                answer = {
                    "labels": list(labels),
                    "scales": [m * s for m, s in zip(mag_order, signs)],
                }
                if verify(inst, answer)[0]:
                    count += 1
    return count


def canonical_key(inst):
    """A variable-relabel invariant coefficient histogram, split by exponent type."""
    n = inst["n"]
    coeffs = _coefficient_dict(inst)
    pure, double, distinct = [], [], []
    for i, j, k in _all_triples(n):
        value = coeffs.get((i, j, k), 0)
        if i == k:
            pure.append(value)
        elif i == j or j == k:
            double.append(value)
        else:
            distinct.append(value)
    structural = [n, inst["scale_floor"], sorted(pure), sorted(double), sorted(distinct)]
    blob = json.dumps(structural, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(blob).hexdigest()


def escalate(params):
    n = int(params.get("n", 0))
    if n < 32:
        return {"n": n * 2, "scale_floor": int(params.get("scale_floor", n + 1)) + n}
    # n=64 builds and verifies, but its compact inverse needs 447 operations,
    # above G9(c)'s 300-operation no-tool cap.  No fixed-answer-size disguise is
    # left: coordinates are already fully permuted and every cubic coefficient is present.
    return "cap_bound"


def _recover_scales_for_labels(inst, labels):
    """Use the diagonal coefficient vector and a proposed labeling."""
    n = inst["n"]
    coeffs = _coefficient_dict(inst)
    spectrum = [0] * n
    for pos, label in enumerate(labels):
        spectrum[label] = _coefficient(coeffs, pos, pos, pos)
    transformed = _fwht(spectrum)
    if any(x % n for x in transformed):
        return None
    roots = [_signed_cube_root(x // n) for x in transformed]
    if any(x is None for x in roots):
        return None
    return roots


def _inverse_fraction_matrix(A):
    """Gauss-Jordan inverse with a reproducible scalar-operation count."""
    n = len(A)
    aug = [[Fraction(A[i][j]) for j in range(n)]
           + [Fraction(int(i == j)) for j in range(n)] for i in range(n)]
    operations = 0
    for col in range(n):
        pivot = next((r for r in range(col, n) if aug[r][col]), None)
        if pivot is None:
            return None, operations
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        pv = aug[col][col]
        if pv != 1:
            aug[col] = [x / pv for x in aug[col]]
            operations += 2 * n
        for r in range(n):
            if r == col or aug[r][col] == 0:
                continue
            factor = aug[r][col]
            aug[r] = [x - factor * y for x, y in zip(aug[r], aug[col])]
            operations += 4 * n
    return [row[n:] for row in aug], operations


def _matmul(A, B):
    if exact_matrices is not None:
        return exact_matrices.matmul(A, B)
    BT = list(zip(*B))
    return [[sum((x * y for x, y in zip(row, col)), Fraction(0))
             for col in BT] for row in A]


def reference_algorithm(inst):
    """Dense exact contraction/matrix-pencil recovery; never reads inst['answer']."""
    started = time.perf_counter()
    n = inst["n"]
    coeffs = _coefficient_dict(inst)
    operations = len(inst["terms"])

    slices = []
    for k in range(n):
        slices.append([[Fraction(_coefficient(coeffs, i, j, k))
                        for j in range(n)] for i in range(n)])
    operations += n ** 3

    inverse, inv_ops = _inverse_fraction_matrix(slices[0])
    operations += inv_ops
    if inverse is None:
        return None, operations, time.perf_counter() - started

    translations = []
    for matrix in slices:
        product = _matmul(inverse, matrix)
        operations += 2 * n ** 3
        permutation = []
        for col in range(n):
            ones = [row for row in range(n) if product[row][col] == 1]
            if len(ones) != 1 or any(product[row][col] not in (0, 1)
                                     for row in range(n)):
                return None, operations, time.perf_counter() - started
            permutation.append(ones[0])
        translations.append(permutation)
        operations += n ** 2

    origin = 0
    labels = [None] * n
    labels[origin] = 0
    span = {origin}
    bit = 1
    for candidate in range(n):
        if candidate in span:
            continue
        old_span = list(span)
        for x in old_span:
            y = translations[candidate][x]
            if labels[y] is not None and labels[y] != labels[x] | bit:
                return None, operations, time.perf_counter() - started
            labels[y] = labels[x] | bit
            operations += 1
        span.update(translations[candidate][x] for x in old_span)
        bit <<= 1
        if len(span) == n:
            break
    if any(x is None for x in labels):
        return None, operations, time.perf_counter() - started
    scales = _recover_scales_for_labels(inst, labels)
    operations += n * int(math.log2(n)) + n
    if scales is None:
        return None, operations, time.perf_counter() - started
    answer = {"labels": labels, "scales": scales}
    return answer, operations, time.perf_counter() - started


def _attack_candidate(inst, kind):
    n = inst["n"]
    coeffs = _coefficient_dict(inst)
    diagonal = [_coefficient(coeffs, i, i, i) for i in range(n)]
    if kind == "display_order":
        labels = list(range(n))
    elif kind == "outlier_rank":
        labels = [0] * n
        for label, pos in enumerate(sorted(range(n), key=lambda x: diagonal[x])):
            labels[pos] = label
    elif kind == "gray_order":
        labels = [j ^ (j >> 1) for j in range(n)]
    elif kind == "magnitude_order":
        labels = [0] * n
        for label, pos in enumerate(sorted(range(n), key=lambda x: abs(diagonal[x]))):
            labels[pos] = label
    else:
        raise ValueError(kind)
    scales = _recover_scales_for_labels(inst, labels)
    if scales is None:
        floor = inst["scale_floor"]
        scales = list(range(floor, floor + n))
    return {"labels": labels, "scales": scales}


def _relabel_instance(inst, old_to_new, reverse_terms=False):
    n = inst["n"]
    terms = []
    for i, j, k, coeff in inst["terms"]:
        a, b, c = sorted((old_to_new[i], old_to_new[j], old_to_new[k]))
        terms.append([a, b, c, coeff])
    terms.sort()
    if reverse_terms:
        terms.reverse()
    old_answer = inst["answer"]
    labels = [0] * n
    for old, new in enumerate(old_to_new):
        labels[new] = old_answer["labels"][old]
    return {
        "n": n,
        "scale_floor": inst["scale_floor"],
        "basis": inst["basis"],
        "terms": terms,
        "answer": {"labels": labels, "scales": list(old_answer["scales"])},
    }


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest():
    report = {}

    # G1: every named preset, three unrelated seeds.
    g1_cases = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_cases += 1
            if not ok:
                g1_failures.append([preset, seed, reason])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "cases": g1_cases, "failures": g1_failures,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    corruptions = {}
    variants = {}
    variants["drop_one"] = {"labels": planted["labels"][:-1],
                            "scales": list(planted["scales"])}
    swapped = {"labels": list(planted["labels"]), "scales": list(planted["scales"])}
    swapped["labels"][0], swapped["labels"][1] = swapped["labels"][1], swapped["labels"][0]
    variants["swap_two"] = swapped
    duplicate = {"labels": list(planted["labels"]), "scales": list(planted["scales"])}
    duplicate["labels"][0] = duplicate["labels"][1]
    variants["duplicate"] = duplicate
    variants["empty"] = {}
    out_range = {"labels": list(planted["labels"]), "scales": list(planted["scales"])}
    out_range["labels"][0] = shipping["n"]
    variants["out_of_range"] = out_range
    for name, candidate in variants.items():
        ok, reason = verify(shipping, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = [v["reason"] for v in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in corruptions.values())
                and len(set(reasons)) == len(reasons),
        "corruptions": corruptions,
        "distinct_reasons": len(set(reasons)),
    }

    encoded = json.dumps(planted, separators=(",", ":"))
    model_reply = "I used the character parity invariant.\n```json\n<answer>" + encoded + "</answer>\n```"
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == planted and verify(shipping, parsed)[0],
        "prose_and_fence_tolerated": parsed == planted,
        "json_native": json.loads(json.dumps(planted)) == planted,
    }

    # G4/G5 share a 200k structure-aware shipping sample.
    guess_rng = random.Random(20260905)
    guess_total = 200_000
    guess_hits = 0
    guess_started = time.perf_counter()
    for _ in range(guess_total):
        if verify(shipping, random_candidate(shipping, guess_rng))[0]:
            guess_hits += 1
    guess_wall = time.perf_counter() - guess_started
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "structure_aware": True,
        "candidate_space": search_space(shipping),
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)

    # G6: four deliberately cheap, in-context guesses; the dense exact method
    # is reported separately because Track B expects it to solve.
    attack_names = {
        "outlier_diagonal_rank": "outlier_rank",
        "greedy_display_order": "display_order",
        "obvious_gray_walsh_ansatz": "gray_order",
        "absolute_magnitude_order": "magnitude_order",
    }
    attack_results = {name: {"successes": 0, "attempts": 8}
                      for name in attack_names}
    restart_successes = 0
    restart_nodes = 0
    restart_started = time.perf_counter()
    reference_successes = 0
    reference_ops = []
    reference_walls = []
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for public_name, kind in attack_names.items():
            if verify(inst, _attack_candidate(inst, kind))[0]:
                attack_results[public_name]["successes"] += 1
        rrng = random.Random(seed ^ 0x5A17)
        solved = False
        for _ in range(256):
            restart_nodes += 1
            if verify(inst, random_candidate(inst, rrng))[0]:
                solved = True
                break
        restart_successes += int(solved)
        recovered, ops, wall = reference_algorithm(inst)
        reference_ops.append(ops)
        reference_walls.append(wall)
        if recovered is not None and verify(inst, recovered)[0]:
            reference_successes += 1
    restart_wall = time.perf_counter() - restart_started
    attack_results["random_restart_256"] = {
        "successes": restart_successes, "attempts": 8,
        "nodes": restart_nodes, "wall_clock_sec": round(restart_wall, 6),
    }
    all_failed = all(v["successes"] == 0 for v in attack_results.values())
    sorted_walls = sorted(reference_walls)
    median_wall = sorted_walls[len(sorted_walls) // 2]
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "exact contraction matrices plus simultaneous matrix pencil",
            "complexity": "O(n^4) exact arithmetic",
            "wall_clock_sec_median": round(median_wall, 6),
            "wall_clock_sec_total": round(sum(reference_walls), 6),
            "operations_median": sorted(reference_ops)[len(reference_ops) // 2],
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    report["G5_density_and_baseline"] = {
        "pass": guess_hits / guess_total < 1e-6 and all_failed,
        "shipping_density_hits": guess_hits,
        "shipping_density_total": guess_total,
        "shipping_density_estimate": guess_hits / guess_total,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "strongest_failing_attack_nodes": restart_nodes,
        "strongest_failing_attack_wall_sec": round(restart_wall, 6),
        "guess_sampling_wall_sec": round(guess_wall, 6),
    }

    doubled = make_instance(n=64, scale_floor=49, seed=271828)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and len(doubled["terms"]) > len(shipping["terms"]),
        "shipping_n": shipping["n"], "doubled_n": doubled["n"],
        "shipping_terms": len(shipping["terms"]),
        "doubled_terms": len(doubled["terms"]),
        "doubled_verify_reason": doubled_reason,
    }

    invariant_checks = 0
    transformed_valid = 0
    keys = []
    for seed in range(20):
        inst = make_instance(seed=1000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        keys.append(key)
        prng = random.Random(9000 + seed)
        permutation = list(range(inst["n"]))
        prng.shuffle(permutation)
        relabeled = _relabel_instance(inst, permutation)
        reordered = _relabel_instance(inst, list(range(inst["n"])), reverse_terms=True)
        composed = _relabel_instance(inst, permutation, reverse_terms=True)
        for changed in (relabeled, reordered, composed):
            invariant_checks += 1
            if canonical_key(changed) != key:
                continue
            if verify(changed, changed["answer"])[0]:
                transformed_valid += 1
    report["G8_canonical_key"] = {
        "pass": invariant_checks == transformed_valid and len(set(keys)) == 20,
        "invariance_checks": invariant_checks,
        "transformed_instances_valid": transformed_valid,
        "unrelated_distinct": len(set(keys)),
        "unrelated_attempts": 20,
        "transformations": ["variable permutation", "term reorder", "composition"],
    }

    answer_chars = 0
    answer_atoms = 0
    for seed in range(20):
        ans = make_instance(seed=5000 + seed,
                            **DIFFICULTY[SHIPPING_DIFFICULTY])["answer"]
        answer_chars = max(answer_chars, len(json.dumps(ans, separators=(",", ":"))))
        answer_atoms = max(answer_atoms, _answer_atoms(ans))
    answer_tokens = math.ceil(answer_chars / 4)
    n = shipping["n"]
    intended_ops = n + (n - 1) + n * int(math.log2(n)) + n
    arms = json.loads(json.dumps(G9_ARM_RESULTS))
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    within_caps = answer_chars <= 2000 and answer_atoms <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": (
            "not_run_cap_bound" if not arms["hinted"]["attempts"]
            else ("too_easy" if arms["hinted"]["solved"] else "hardened")
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(v.get("pass") for k, v in report.items()
                                  if k.startswith("G"))
    report["hardening_outcome"] = dict(HARDENING_OUTCOME)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
