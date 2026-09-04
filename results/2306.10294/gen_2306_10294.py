"""Verified symmetric-MinRank pencil generator for arXiv:2306.10294."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import re
import statistics
import time
from collections import Counter


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "The planted rank-three residual has trace zero, so use the matrix trace "
    "before attempting elimination."
)
PLACEBO_HINT: str = (
    "The rank calculation uses exact modular arithmetic, so check every field "
    "reduction before committing."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "symmetric matrix over a prime finite field",
        "two-dimensional symmetric matrix pencil spanned by A and the identity",
    ],
    "verification_operations": [
        "exact prime-field addition and multiplication",
        "exact modular Gaussian rank",
        "matrix trace",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize that the hidden rank-three member has zero trace and recover "
        "its scalar shift by one modular trace; without this invariant, the "
        "obvious route is a matrix-pencil rank computation."
    ),
    "hardness_basis": (
        "Track B: the construction-aware trace solver is O(n) exact field "
        "operations and is expected to solve every instance; at shipping n=192 "
        "it uses 193 counted field operations and took a measured median "
        "0.00000828 seconds over eight seeds, while a no-tool solver must discover the unstated "
        "trace-zero invariant and exactly accumulate the 192-entry diagonal."
    ),
    "max_answer_tokens": 6,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}


# 2^31-1 is prime.  The named non-demo sizes divide p+1, which also keeps the
# final modular division in the intended trace route especially compact.
FIELD_PRIME = 2_147_483_647

DIFFICULTY: dict = {
    "demo": {"n": 7, "p": 101},
    "easy": {"n": 128, "p": FIELD_PRIME},
    "medium": {"n": 192, "p": FIELD_PRIME},
    "hard": {"n": 256, "p": FIELD_PRIME},
}
SHIPPING_DIFFICULTY: str = "medium"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "Exactly two base-10 integers [p,t]: the stated prime modulus p followed "
        "by one field element 0 <= t < p; p is fixed by the instance."
    ),
    "bounds": {
        "atomic_elements": 2,
        "shift_choices_max": FIELD_PRIME,
        "integer_bits": 31,
    },
}

NOTES: str = (
    "Section 1, Problem 1 fixes the native object as symmetric MinRank over a "
    "finite field; Section 3, Proposition 4 proves congruence invariance of the "
    "matrix code, and Section 4, Fact 1 exhibits rank-three relations in odd "
    "characteristic. Section 6.2 explicitly finds rank-defective members of a "
    "matrix pencil by solving det(wD1+D2)=0, and Section 6.3 makes that attack "
    "polynomial, so a Track A claim would be false for this generated pencil. The generator "
    "instead inverse-plants A+tI=U diag(c1,c2,c3) U^T with zero trace and rank "
    "three. A trace algorithm therefore solves it in O(n), disclosed as the "
    "Track B reference. Diagonal outlier/mode, greedy leading-minor, random-shift, "
    "and partial-trace attacks are measured separately and do not recover the "
    "shift on the shipping seeds."
)


# These values are replaced only with transcripts produced by scripts/harden.py.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "hardened",
}


def _is_prime_64(value: int) -> bool:
    """Deterministic Miller--Rabin for the parameter range used here."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value % prime == 0:
            return value == prime
    d = value - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    # This base set is deterministic below 2^64.
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        x = pow(base, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(s - 1):
            x = x * x % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _matrix_rank(matrix, p: int, stop_after: int | None = None) -> int:
    """Exact row rank over F_p, optionally stopping after enough pivots."""
    if not matrix:
        return 0
    rows = [[int(x) % p for x in row] for row in matrix]
    n_rows = len(rows)
    n_cols = len(rows[0])
    rank = 0
    for col in range(n_cols):
        pivot = None
        for row in range(rank, n_rows):
            if rows[row][col]:
                pivot = row
                break
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        pivot_row = rows[rank]
        inverse = pow(pivot_row[col], p - 2, p)
        for j in range(col, n_cols):
            pivot_row[j] = pivot_row[j] * inverse % p
        for row in range(rank + 1, n_rows):
            factor = rows[row][col]
            if factor:
                target = rows[row]
                for j in range(col, n_cols):
                    target[j] = (target[j] - factor * pivot_row[j]) % p
        rank += 1
        if stop_after is not None and rank >= stop_after:
            return rank
        if rank == n_rows:
            break
    return rank


def _det4_shift(matrix, shift: int, p: int) -> int:
    """Determinant of the leading 4x4 principal block of A+shift*I."""
    rows = []
    for i in range(4):
        rows.append(
            [
                (matrix[i][j] + (shift if i == j else 0)) % p
                for j in range(4)
            ]
        )
    det = 1
    for col in range(4):
        pivot = next((r for r in range(col, 4) if rows[r][col]), None)
        if pivot is None:
            return 0
        if pivot != col:
            rows[col], rows[pivot] = rows[pivot], rows[col]
            det = -det
        value = rows[col][col]
        det = det * value % p
        inverse = pow(value, p - 2, p)
        for row in range(col + 1, 4):
            factor = rows[row][col] * inverse % p
            if factor:
                for j in range(col, 4):
                    rows[row][j] = (rows[row][j] - factor * rows[col][j]) % p
    return det % p


def _shifted_rank(inst, shift: int, stop_after: int | None = None) -> int:
    matrix = inst["matrix"]
    p = inst["p"]
    shifted = []
    for i, row in enumerate(matrix):
        shifted.append(
            [(value + (shift if i == j else 0)) % p for j, value in enumerate(row)]
        )
    return _matrix_rank(shifted, p, stop_after=stop_after)


def _rank_three_residual(n: int, p: int, rng: random.Random):
    """Return a symmetric, trace-zero, rank-three matrix by composition."""
    while True:
        columns = [[rng.randrange(p) for _ in range(3)] for _ in range(n)]
        if _matrix_rank(columns, p) != 3:
            continue
        gram_diagonal = [
            sum(row[j] * row[j] for row in columns) % p for j in range(3)
        ]
        if gram_diagonal[2] == 0:
            continue
        c1 = rng.randrange(1, p)
        c2 = rng.randrange(1, p)
        c3 = (
            -(c1 * gram_diagonal[0] + c2 * gram_diagonal[1])
            * pow(gram_diagonal[2], p - 2, p)
        ) % p
        if c3 == 0:
            continue
        coefficients = (c1, c2, c3)
        residual = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i, n):
                value = sum(
                    coefficients[a] * columns[i][a] * columns[j][a]
                    for a in range(3)
                ) % p
                residual[i][j] = value
                residual[j][i] = value
        if sum(residual[i][i] for i in range(n)) % p != 0:
            raise AssertionError("trace-zero construction failed")
        return residual


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate A so that a sampled shift makes A+tI rank exactly three."""
    p = params.pop("p", FIELD_PRIME)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 7:
        raise ValueError("n must be an integer at least 7")
    if isinstance(p, bool) or not isinstance(p, int) or p <= n or not _is_prime_64(p):
        raise ValueError("p must be a prime integer greater than n")
    rng = random.Random(seed)
    planted_shift = rng.randrange(p)
    residual = _rank_three_residual(n, p, rng)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            matrix[i][j] = (residual[i][j] - (planted_shift if i == j else 0)) % p
    return {
        "family": "rank-three shift in a symmetric MinRank pencil",
        "p": p,
        "n": n,
        "rank_target": 3,
        "matrix": matrix,
        "answer": [p, planted_shift],
    }


def _answer_text(answer) -> str:
    return f"{answer[0]}, {answer[1]}"


def render(inst) -> str:
    rows = []
    for i in range(inst["n"]):
        rows.append(f"  {i}: " + " ".join(str(x) for x in inst["matrix"][i][i:]))
    statement = f"""RANK-THREE MEMBER OF A SYMMETRIC MATRIX PENCIL

Work in the prime field F_p, represented by integers 0,...,p-1 with every
addition, multiplication, inverse, and equality taken modulo p={inst['p']}.

The input is a symmetric {inst['n']} by {inst['n']} matrix A. Let I be the
{inst['n']} by {inst['n']} identity matrix. Find the unique field element t with
0 <= t < p for which A+tI has rank exactly 3 over F_p. Matrix rank means the
number of pivots under exact Gaussian elimination modulo p; it is not a
floating-point rank.

Only the upper triangle of A is listed. The line labelled i contains, in order,
A[i,i], A[i,i+1], ..., A[i,{inst['n'] - 1}]. Indices are 0-based. The omitted
lower triangle is fixed by A[j,i]=A[i,j]. There are no omitted choices, and the
instance is promised to have exactly one valid t.

Upper triangle of A:
{chr(10).join(rows)}

Give your final answer inside <answer></answer> tags, as two comma-separated
base-10 integers: first the literal modulus p, then t. Do not use brackets.
Example format: <answer>{inst['p']}, 0</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    try:
        matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", str(text), re.I | re.S)
        if not matches:
            return None
        body = matches[-1].strip()
        for fence in ("~~~", chr(96) * 3):
            if body.startswith(fence) and body.endswith(fence):
                body = re.sub("^" + re.escape(fence) + r"[^\n]*\n?", "", body)
                body = re.sub(r"\n?" + re.escape(fence) + "$", "", body).strip()
        if body.startswith("[") and body.endswith("]"):
            body = body[1:-1].strip()
        parts = [piece.strip() for piece in body.split(",")]
        if len(parts) != 2 or any(not re.fullmatch(r"[+-]?\d+", x) for x in parts):
            return None
        return [int(parts[0]), int(parts[1])]
    except Exception:
        return None


def verify(inst, answer) -> tuple[bool, str]:
    if answer is None:
        return False, "answer is absent"
    if not isinstance(answer, list):
        return False, "answer must be a two-integer list"
    if not answer:
        return False, "answer is empty"
    if len(answer) < 2:
        return False, "answer is missing the shift"
    if len(answer) > 2:
        return False, "answer has extra fields"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "both answer fields must be integers"
    p, shift = answer
    if p != inst["p"]:
        return False, "first integer does not equal the field modulus"
    if shift < 0 or shift >= p:
        return False, "shift is outside the canonical field range"

    # Almost every wrong shift is rejected by this exact rank-four witness.  A
    # root of this one minor is sent through full exact elimination below.
    if _det4_shift(inst["matrix"], shift, p) != 0:
        return False, "rank exceeds 3 (a leading 4x4 minor is nonzero)"
    rank = _shifted_rank(inst, shift, stop_after=4)
    if rank > 3:
        return False, "rank exceeds 3 after exact elimination"
    if rank < 3:
        return False, "rank is below 3"
    return True, "ok"


def random_candidate(inst, rng: random.Random) -> object:
    """Uniformly sample the exact stated certificate language."""
    return [inst["p"], rng.randrange(inst["p"])]


def search_space(inst) -> int | None:
    return inst["p"]


def enumerate_all(inst) -> int | None:
    if inst["p"] > 10_000:
        return None
    return sum(verify(inst, [inst["p"], shift])[0] for shift in range(inst["p"]))


def _trace_invariants(inst):
    p = inst["p"]
    matrix = inst["matrix"]
    trace1 = sum(matrix[i][i] for i in range(inst["n"])) % p
    trace2 = 0
    for i in range(inst["n"]):
        trace2 += matrix[i][i] * matrix[i][i]
        for j in range(i + 1, inst["n"]):
            trace2 += 2 * matrix[i][j] * matrix[i][j]
    return trace1, trace2 % p


def canonical_key(inst) -> str:
    """Strong cheap invariant under orthogonal coordinate relabelling."""
    trace1, trace2 = _trace_invariants(inst)
    payload = ["symmetric-shift-pencil", inst["p"], inst["n"], trace1, trace2]
    raw = json.dumps(payload, separators=(",", ":")).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def escalate(params) -> dict | None:
    n = int(params["n"])
    p = int(params.get("p", FIELD_PRIME))
    if n >= 288:
        return None
    return {"n": min(288, n + 32), "p": p}


def _reference_trace(inst):
    """Construction-aware Track B solver; never consults inst['answer']."""
    p = inst["p"]
    diagonal_sum = sum(inst["matrix"][i][i] for i in range(inst["n"])) % p
    shift = (-diagonal_sum * pow(inst["n"], -1, p)) % p
    return [p, shift], {
        "field_additions": inst["n"] - 1,
        "field_inversions": 1,
        "field_multiplications": 1,
        "exact_operations": inst["n"] + 1,
    }


def _attack_outlier_diagonal(inst):
    diagonal = [inst["matrix"][i][i] for i in range(inst["n"])]
    value = Counter(diagonal).most_common(1)[0][0]
    return [inst["p"], (-value) % inst["p"]]


def _attack_greedy_leading_minor(inst):
    p = inst["p"]
    candidates = [(-inst["matrix"][i][i]) % p for i in range(min(32, inst["n"]))]
    # Prefer a shift making the leading principal block look most singular.
    scored = []
    for shift in candidates:
        block = [
            [
                (inst["matrix"][i][j] + (shift if i == j else 0)) % p
                for j in range(4)
            ]
            for i in range(4)
        ]
        scored.append((_matrix_rank(block, p), shift))
    return [p, min(scored)[1]]


def _attack_random_shifts(inst, rng, restarts=4096):
    last = [inst["p"], 0]
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last
    return last


def _attack_partial_trace(inst, prefix=12):
    p = inst["p"]
    count = min(prefix, inst["n"])
    partial = sum(inst["matrix"][i][i] for i in range(count)) % p
    return [p, (-partial * pow(count, -1, p)) % p]


def _transform_instance(inst, permutation=None, signs=None):
    out = copy.deepcopy(inst)
    n = inst["n"]
    if permutation is None:
        permutation = list(range(n))
    if signs is None:
        signs = [1] * n
    p = inst["p"]
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            matrix[i][j] = (
                signs[i] * signs[j] * inst["matrix"][permutation[i]][permutation[j]]
            ) % p
    out["matrix"] = matrix
    return out


def _answer_size(answer):
    encoded = json.dumps(answer, separators=(",", ":"))
    return {
        "chars": len(encoded),
        "tokens": math.ceil(len(encoded) / 4),
        "elements": len(answer),
    }


def selftest():
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    g1_attempts = 0
    g1_failures = []
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not g1_failures and json_roundtrips == g1_attempts,
        "attempts": g1_attempts,
        "json_roundtrips": json_roundtrips,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=90210, **ship_params)
    answer = inst["answer"]
    corruptions = {
        "drop": answer[:1],
        "swap": [answer[1], answer[0]],
        "duplicate": [answer[0], answer[1], answer[1]],
        "empty": [],
        "out_of_range": [answer[0], answer[0]],
    }
    g2_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        g2_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in g2_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(x["rejected"] for x in g2_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": g2_results,
    }

    realistic = (
        "I used the invariant and checked the rank exactly.\n\n"
        "```text\n<answer>" + _answer_text(answer) + "</answer>\n```"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("no tagged answer") is None,
        "parsed": parsed,
        "garbage_returns_none": parse_answer("no tagged answer") is None,
    }

    samples = 200_000
    guess_rng = random.Random(0x230610294)
    hits = 0
    for _ in range(samples):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    exact_guess_probability = 1.0 / inst["p"]
    report["G4_guess_resistance"] = {
        "pass": hits == 0 and exact_guess_probability < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "exact_probability": exact_guess_probability,
        "structure_aware_space": search_space(inst),
        "sampler": "uniform field shift with the required modulus field already fixed",
    }

    baseline_start = time.perf_counter()
    _attack_random_shifts(inst, random.Random(99173), restarts=4096)
    baseline_wall = time.perf_counter() - baseline_start
    demo_count = enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline"] = {
        "pass": hits == 0 and demo_count == 1,
        "shipping_valid_hits": hits,
        "shipping_density_samples": samples,
        "shipping_observed_solution_fraction": hits / samples,
        "shipping_exact_solution_fraction": exact_guess_probability,
        "demo_exact_solution_count": demo_count,
        "baseline_wall_seconds": round(baseline_wall, 6),
        "baseline_random_restart_iterations": 4096,
    }

    attack_results = {
        "outlier_diagonal_mode": {"successes": 0, "attempts": 0},
        "greedy_leading_minor_from_diagonal": {"successes": 0, "attempts": 0},
        "random_restart_4096_shifts": {"successes": 0, "attempts": 0},
        "in_context_partial_trace_12": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_times = []
    reference_operations = []
    for seed in range(3100, 3108):
        attacked = make_instance(seed=seed, **ship_params)
        candidates = {
            "outlier_diagonal_mode": _attack_outlier_diagonal(attacked),
            "greedy_leading_minor_from_diagonal": _attack_greedy_leading_minor(attacked),
            "random_restart_4096_shifts": _attack_random_shifts(
                attacked, random.Random(seed ^ 0xA5A5), restarts=4096
            ),
            "in_context_partial_trace_12": _attack_partial_trace(attacked, prefix=12),
        }
        for name, candidate in candidates.items():
            attack_results[name]["attempts"] += 1
            if verify(attacked, candidate)[0]:
                attack_results[name]["successes"] += 1
        start = time.perf_counter()
        reference_answer, stats = _reference_trace(attacked)
        reference_times.append(time.perf_counter() - start)
        reference_operations.append(stats["exact_operations"])
        if verify(attacked, reference_answer)[0]:
            reference_successes += 1
    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "trace-zero residual invariant",
            "complexity": "O(n) exact prime-field operations",
            "median_wall_clock_sec": round(statistics.median(reference_times), 8),
            "median_operations": int(statistics.median(reference_operations)),
            "operation_definition": "n-1 additions, one field inverse, one multiplication",
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    doubled = make_instance(n=2 * ship_params["n"], p=ship_params["p"], seed=77)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] > inst["n"],
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "shipping_upper_triangle_entries": inst["n"] * (inst["n"] + 1) // 2,
        "doubled_upper_triangle_entries": doubled["n"] * (doubled["n"] + 1) // 2,
        "shipping_reference_operations": inst["n"] + 1,
        "doubled_reference_operations": doubled["n"] + 1,
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = 0
    witness_checks = 0
    invariant_failures = []
    distinct_keys = []
    for seed in range(20):
        original = make_instance(seed=7000 + seed, **ship_params)
        original_key = canonical_key(original)
        distinct_keys.append(original_key)
        rng = random.Random(8000 + seed)
        permutation = list(range(original["n"]))
        rng.shuffle(permutation)
        signs = [1 if rng.randrange(2) == 0 else original["p"] - 1 for _ in range(original["n"])]
        variants = [
            _transform_instance(original, permutation=permutation),
            _transform_instance(original, signs=signs),
            _transform_instance(original, permutation=permutation, signs=signs),
            _transform_instance(
                original, permutation=list(reversed(permutation)), signs=list(reversed(signs))
            ),
        ]
        for variant in variants:
            invariance_checks += 1
            if canonical_key(variant) != original_key:
                invariant_failures.append([seed, "key changed"])
            witness_checks += 1
            if not verify(variant, original["answer"])[0]:
                invariant_failures.append([seed, "carried witness failed"])
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and len(set(distinct_keys)) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": witness_checks,
        "distinct_unrelated_keys": len(set(distinct_keys)),
        "unrelated_instances": 20,
        "failures": invariant_failures,
        "symmetries": "coordinate permutations, sign changes, and their compositions",
        "key_basis": "SHA-256 of n,p,trace(A),trace(A^2), not of the seed or rendering",
    }

    size = _answer_size(answer)
    arms = copy.deepcopy(G9_RESULTS["arms"])
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_rate = arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else 0.0
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else 0.0
    hinted_hardened = G9_RESULTS["hinted_verdict"] == "hardened"
    intended_operations = inst["n"] + 1
    within_caps = size["chars"] <= 2000 and size["elements"] <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": size["chars"],
        "answer_tokens": size["tokens"],
        "answer_elements": size["elements"],
        "intended_route_operations": intended_operations,
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
