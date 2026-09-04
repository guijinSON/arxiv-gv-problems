"""Exact Gram-dependence instances derived from arXiv:2504.18110.

Section 2, Lemma 2 of the paper gives a one-dimensional dependence for a
2-by-n block Gram matrix.  This generator applies independent invertible
integer recombinations to its n column pairs and then relabels the vectors.
The planted dependence is transported through those maps; it is never found
by solving the generated matrix.
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
from collections import Counter
from fractions import Fraction


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - fallback is intentional
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "geometry",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "positive-semidefinite Gram matrix over Q",
        "formal dependence among Euclidean vectors",
    ],
    "verification_operations": [
        "exact integer Gram-matrix multiplication",
        "integer gcd normalization",
        "exact zero comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Transport the paper's equality of two vector sums through hidden "
        "pairwise changes of generators instead of eliminating the full matrix."
    ),
    "hardness_basis": (
        "Track B: exact rational RREF is an O(m^3) reference algorithm; at the "
        "shipping preset it used 261,006 exact operations and about 0.09 seconds, "
        "while the pair-invariant route uses 161 exact operations and must be "
        "recognized and executed without tools."
    ),
    "max_answer_tokens": 47,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A matrix-kernel certificate {\"coefficients\": [c_0,...,c_(m-1)]}: "
        "exactly m integers in [-3,3], not all zero, primitive (gcd 1), with "
        "the first nonzero coefficient positive."
    ),
    "bounds": {
        "coefficient_count": "m = 2*n, at most 112 at every shippable preset",
        "coefficient_abs": 3,
        "primitive": True,
        "canonical_global_sign": True,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 2},
    "easy": {"n": 32},
    "medium": {"n": 40},
    "hard": {"n": 48},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT: str = (
    "Hint: Use each listed pair's local Gram norm, then align its sign against one anchor pair."
)
PLACEBO_HINT: str = (
    "Hint: Keep every listed coefficient in range, then check its value carefully against each matrix row."
)

# Filled from harness-owned transcripts after the three runs.  The values are
# data, not a substitute for the transcript files themselves.
_G9_EVIDENCE = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "hardened",
}

NOTES = r"""
Paper definition and construction. Section 1 defines a 2-distance set by its
Euclidean pairwise distances. Section 2 works natively with Gram matrices and
switching roots. The scalable identity used here is exactly Section 2, Lemma 2:
vectors a_1,...,a_n,b_1,...,b_n with Gram matrix [[nI,J],[J,nI]] obey
sum a_i = sum b_i. Its proof checks that the squared norm of the difference is
zero. Independent invertible 2-by-2 integer changes of each (a_i,b_i) generator
pair preserve positive semidefiniteness, rank, and the carried dependence.

Step-0 discrimination. The paper's headline 277-point construction is not a
Track-A search family: Theorem 1 writes u=x_1+x_2+x_3-r, and Section 2 writes r
explicitly. On the other hand, Proposition 3's standard maximality computation
enumerates 16,689,170 short dual-lattice vectors; Appendix A reports 788.600
seconds and 4584.38 MB. Thus "an explicit formula exists" is not a valid Track-A
claim or a valid rejection by itself. This module makes the honest Track-B claim
on the lemma's scalable Gram objects. Exact RREF always solves the shipped task;
its measured cost is reported separately as the reference algorithm.

Generation. The null vector (1,...,1,-1,...,-1) exists before random choices.
For each a_i,b_i pair the generator samples a unimodular 2-by-2 recombination,
transports that two-entry slice by the inverse matrix, and only then permutes all
vectors. It constructs the new Gram matrix by exact congruence. No nullspace
routine is called by make_instance.

Easy regimes and attacks. The unmixed block matrix is visually trivial, so every
pair is mixed and the public order is shuffled. Constant and alternating
vectors, a diagonal outlier rule, greedy row cancellation, random restarts, and
locally correct but independently oriented pair slices are tested. The last is
the strongest in-context failure: it notices each 2-by-2 local invariant but
misses the single global sign alignment across pairs. Exact RREF is intentionally
successful and is reported under reference_algorithm, as Track B requires.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_BOUND = 3


def _mixing_library():
    """Small unimodular maps whose transported signed slice is nontrivial."""
    out = []
    for a, b, c, d in itertools.product(range(-2, 3), repeat=4):
        det = a * d - b * c
        if abs(det) != 1:
            continue
        # T^{-1} (1,-1)^t, integral because det is +/-1.
        x = (d + b) // det
        y = (-c - a) // det
        if x == 0 or y == 0 or max(abs(x), abs(y)) > _BOUND:
            continue
        if abs(x) == abs(y) == 1:
            continue
        out.append((a, b, c, d))
    return tuple(out)


_MIXINGS = _mixing_library()


def _block_product(left, right, n, diagonal):
    """Return T_left^t D T_right or T_left^t H T_right."""
    a, b, c, d = left
    e, f, g, h = right
    if diagonal:
        # D = [[n,1],[1,n]].
        return (
            (n * a * e + a * g + c * e + n * c * g,
             n * a * f + a * h + c * f + n * c * h),
            (n * b * e + b * g + d * e + n * d * g,
             n * b * f + b * h + d * f + n * d * h),
        )
    # H = [[0,1],[1,0]].
    return (
        (a * g + c * e, a * h + c * f),
        (b * g + d * e, b * h + d * f),
    )


def _transported_slice(T):
    a, b, c, d = T
    det = a * d - b * c
    return ((d + b) // det, (-c - a) // det)


def make_instance(n, seed=0, **params) -> dict:
    """Construct a congruence-transformed Lemma-2 Gram matrix.

    The known null vector is transported while the random transformations are
    applied.  No linear system or nullspace is solved.
    """
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    rng = random.Random(seed)
    transforms = [rng.choice(_MIXINGS) for _ in range(n)]
    m = 2 * n
    natural = [[0] * m for _ in range(m)]
    natural_answer = [0] * m

    for i, T in enumerate(transforms):
        x, y = _transported_slice(T)
        natural_answer[2 * i] = x
        natural_answer[2 * i + 1] = y
        for j in range(i, n):
            B = _block_product(T, transforms[j], n, i == j)
            for u in range(2):
                for v in range(2):
                    r, c = 2 * i + u, 2 * j + v
                    natural[r][c] = B[u][v]
                    natural[c][r] = B[u][v]

    # new position -> old position; matrix and witness travel together.
    order = list(range(m))
    rng.shuffle(order)
    inverse = [0] * m
    for new, old in enumerate(order):
        inverse[old] = new
    matrix = [[natural[order[i]][order[j]] for j in range(m)] for i in range(m)]
    coeffs = [natural_answer[old] for old in order]
    pairs = [[inverse[2 * i], inverse[2 * i + 1]] for i in range(n)]
    for pair in pairs:
        pair.sort()
    rng.shuffle(pairs)

    first = next(c for c in coeffs if c)
    if first < 0:
        coeffs = [-c for c in coeffs]

    return {
        "family": "transported two-block Gram dependence",
        "n": n,
        "dimension": m,
        "coefficient_bound": _BOUND,
        "local_norm_target": 2 * (n - 1),
        "pairs": pairs,
        "gram_matrix": matrix,
        "answer": {"coefficients": coeffs},
    }


def render(inst) -> str:
    pairs = "\n".join(f"{a} {b}" for a, b in inst["pairs"])
    matrix = "\n".join(" ".join(map(str, row)) for row in inst["gram_matrix"])
    text = f"""Exact dependence in a Euclidean Gram matrix

A Gram matrix K of vectors v_0,...,v_{{m-1}} is defined by
K[i,j] = <v_i,v_j>, their Euclidean inner product.  The symmetric integer
matrix below is promised to be positive semidefinite, to have a one-dimensional
nullspace, and therefore to describe m vectors with exactly one linear
dependence up to scale.  You need not construct coordinates.  A coefficient
vector c is a dependence exactly when Kc=0 over the integers, equivalently
sum_i c_i v_i is the zero vector.

Here m={inst['dimension']} and n={inst['n']}.  The vector positions are 0-based.
For structural bookkeeping, the m positions are partitioned into the following
{inst['n']} unordered pairs; pair order and order inside a pair are irrelevant:

{pairs}

The exact {inst['dimension']} by {inst['dimension']} Gram matrix K, one row per line, is:

{matrix}

Return the unique normalized dependence c.  It must contain exactly
{inst['dimension']} integers, one for each position in matrix order.  Every
coefficient is in the inclusive interval [-{inst['coefficient_bound']},{inst['coefficient_bound']}].
The coefficients are not all zero, their nonzero absolute values have greatest
common divisor 1, and the first nonzero coefficient is positive.  These rules
fix both scale and global sign.  Repeated coefficient values are allowed; vector
positions may not be omitted or reordered.

Give your final answer inside <answer></answer> tags as one JSON object with the
single key \"coefficients\" and an integer array of length {inst['dimension']}.
Example format only: <answer>{{\"coefficients\":[1,-1]}}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\n" + PLACEBO_HINT
    return text


def parse_answer(text) -> object | None:
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json|python)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
    try:
        obj = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def _normalize_integer_vector(values):
    if not values or not any(values):
        return values
    g = 0
    for value in values:
        g = math.gcd(g, abs(value))
    values = [value // g for value in values]
    if next(value for value in values if value) < 0:
        values = [-value for value in values]
    return values


def verify(inst, answer) -> tuple[bool, str]:
    """Check any bounded primitive kernel witness; never inspect inst['answer']."""
    if not isinstance(answer, dict) or set(answer) != {"coefficients"}:
        return False, "answer must be an object with only the key 'coefficients'"
    coeffs = answer["coefficients"]
    if not isinstance(coeffs, list):
        return False, "coefficients must be a JSON array"
    if not coeffs:
        return False, "coefficient vector is empty"
    m = inst["dimension"]
    if len(coeffs) != m:
        return False, f"wrong coefficient count: expected {m}, got {len(coeffs)}"
    for i, value in enumerate(coeffs):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"coefficient {i} is not an integer"
        if abs(value) > inst["coefficient_bound"]:
            return False, f"coefficient {i} is outside the inclusive bound"
    if not any(coeffs):
        return False, "all-zero vector is not a dependence certificate"
    g = 0
    for value in coeffs:
        g = math.gcd(g, abs(value))
    if g != 1:
        return False, f"coefficients are not primitive: gcd is {g}"
    if next(value for value in coeffs if value) < 0:
        return False, "first nonzero coefficient must be positive"

    # Exact integer arithmetic; random candidates almost always fail on row 0,
    # keeping the 200k-sample density test cheap without weakening verification.
    for i, row in enumerate(inst["gram_matrix"]):
        residual = sum(a * b for a, b in zip(row, coeffs))
        if residual:
            return False, f"Gram product is nonzero at row {i}: {residual}"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniformly sample the declared primitive, sign-normalized integer cube."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    m = inst["dimension"]
    B = inst["coefficient_bound"]
    while True:
        values = [rng.randint(-B, B) for _ in range(m)]
        if not any(values):
            continue
        g = 0
        for value in values:
            g = math.gcd(g, abs(value))
        if g != 1:
            continue
        if next(value for value in values if value) < 0:
            values = [-value for value in values]
        return {"coefficients": values}


def _mobius(k):
    if k == 1:
        return 1
    primes = 0
    d = 2
    while d * d <= k:
        if k % d == 0:
            k //= d
            primes += 1
            if k % d == 0:
                return 0
            while k % d == 0:
                k //= d
        d += 1
    if k > 1:
        primes += 1
    return -1 if primes % 2 else 1


def search_space(inst) -> int | None:
    """Number of primitive vectors in the coefficient cube, modulo global sign."""
    m = inst["dimension"]
    B = inst["coefficient_bound"]
    primitive = 0
    for d in range(1, B + 1):
        primitive += _mobius(d) * ((2 * (B // d) + 1) ** m - 1)
    return primitive // 2


def enumerate_all(inst) -> int | None:
    """Brute-force the declared language only when its raw cube is small."""
    m = inst["dimension"]
    B = inst["coefficient_bound"]
    if (2 * B + 1) ** m > 100_000:
        return None
    count = 0
    for values in itertools.product(range(-B, B + 1), repeat=m):
        if not any(values):
            continue
        g = 0
        for value in values:
            g = math.gcd(g, abs(value))
        if g != 1 or next(value for value in values if value) < 0:
            continue
        ok, _ = verify(inst, {"coefficients": list(values)})
        count += int(ok)
    return count


def canonical_key(inst) -> str:
    """A strong simultaneous-row/column-permutation invariant of the Gram data."""
    K = inst["gram_matrix"]
    row_profiles = sorted(
        (K[i][i], tuple(sorted(K[i]))) for i in range(len(K))
    )
    entry_hist = Counter(
        K[i][j] for i in range(len(K)) for j in range(i, len(K))
    )
    payload = {
        "dimension": inst["dimension"],
        "rows": row_profiles,
        "upper_entry_histogram": sorted(entry_hist.items()),
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params) -> dict | None:
    n = params.get("n")
    if isinstance(n, bool) or not isinstance(n, int):
        return None
    if n >= 56:
        return None
    return {"n": min(56, n + 8)}


def _rref_reference(inst):
    """Exact RREF nullspace basis with an arithmetic-operation counter."""
    R = [[Fraction(x) for x in row] for row in inst["gram_matrix"]]
    rows, cols = len(R), len(R[0])
    pivots = []
    r = 0
    operations = 0
    for c in range(cols):
        if r >= rows:
            break
        pivot = next((i for i in range(r, rows) if R[i][c]), None)
        if pivot is None:
            continue
        R[r], R[pivot] = R[pivot], R[r]
        pv = R[r][c]
        for j in range(c, cols):
            R[r][j] /= pv
            operations += 1
        for i in range(rows):
            if i == r or not R[i][c]:
                continue
            f = R[i][c]
            for j in range(c, cols):
                R[i][j] -= f * R[r][j]
                operations += 2
        pivots.append(c)
        r += 1
    free = [c for c in range(cols) if c not in pivots]
    if len(free) != 1:
        return None, operations
    f = free[0]
    vec = [Fraction(0)] * cols
    vec[f] = Fraction(1)
    for rr, c in enumerate(pivots):
        vec[c] = -R[rr][f]
        operations += 1
    L = 1
    for value in vec:
        L = math.lcm(L, value.denominator)
    ints = [value.numerator * (L // value.denominator) for value in vec]
    return {"coefficients": _normalize_integer_vector(ints)}, operations


def _attack_outlier_diagonal(inst):
    diag = [row[i] for i, row in enumerate(inst["gram_matrix"])]
    median = sorted(diag)[len(diag) // 2]
    values = [1 if value <= median else -1 for value in diag]
    return {"coefficients": _normalize_integer_vector(values)}


def _attack_alternating(inst):
    return {"coefficients": [1 if i % 2 == 0 else -1
                             for i in range(inst["dimension"])]}


def _attack_greedy_rows(inst):
    K = inst["gram_matrix"]
    m = inst["dimension"]
    values = [0] * m
    values[0] = 1
    for j in range(1, m):
        # Myopic: make the current row's already-visible residual small, while
        # pretending all future coefficients are zero.
        partial = sum(K[j][k] * values[k] for k in range(j))
        choices = range(-_BOUND, _BOUND + 1)
        values[j] = min(choices, key=lambda x: (abs(partial + K[j][j] * x), abs(x), x))
    values = _normalize_integer_vector(values)
    if max(map(abs, values), default=0) > _BOUND:
        values = [1] + [0] * (m - 1)
    return {"coefficients": values}


def _local_pair_candidate(inst):
    """Use every local norm correctly but do not align signs between pairs."""
    K = inst["gram_matrix"]
    target = inst["local_norm_target"]
    values = [0] * inst["dimension"]
    for a, b in inst["pairs"]:
        found = []
        for x in range(-_BOUND, _BOUND + 1):
            for y in range(-_BOUND, _BOUND + 1):
                if math.gcd(abs(x), abs(y)) != 1:
                    continue
                q = K[a][a] * x * x + 2 * K[a][b] * x * y + K[b][b] * y * y
                if q == target and (x > 0 or (x == 0 and y > 0)):
                    found.append((x, y))
        if not found:
            return {"coefficients": [1] + [0] * (inst["dimension"] - 1)}
        values[a], values[b] = min(found)
    return {"coefficients": _normalize_integer_vector(values)}


def _relabel_instance(inst, order):
    """Carry an instance and its witness through new-position -> old-position."""
    m = inst["dimension"]
    if sorted(order) != list(range(m)):
        raise ValueError("order is not a permutation")
    inverse = [0] * m
    for new, old in enumerate(order):
        inverse[old] = new
    out = dict(inst)
    K = inst["gram_matrix"]
    out["gram_matrix"] = [[K[order[i]][order[j]] for j in range(m)] for i in range(m)]
    out["pairs"] = [[inverse[a], inverse[b]] for a, b in inst["pairs"]]
    for pair in out["pairs"]:
        pair.sort()
    out["pairs"].reverse()
    carried = [inst["answer"]["coefficients"][old] for old in order]
    out["answer"] = {"coefficients": _normalize_integer_vector(carried)}
    return out


def _answer_atom_count(answer):
    return len(answer.get("coefficients", [])) if isinstance(answer, dict) else 0


def selftest() -> dict:
    report = {}

    # G1: every named preset, three independent seeds.
    planted_ok = 0
    planted_total = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, _ = verify(inst, inst["answer"])
            planted_ok += int(ok)
            planted_total += 1
    report["G1_planted_verifies"] = {
        "pass": planted_ok == planted_total,
        "verified": planted_ok,
        "attempts": planted_total,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    base = shipping["answer"]["coefficients"]
    swap = base[:]
    pair_to_swap = next((p for p in shipping["pairs"] if base[p[0]] != base[p[1]]),
                        shipping["pairs"][0])
    swap[pair_to_swap[0]], swap[pair_to_swap[1]] = swap[pair_to_swap[1]], swap[pair_to_swap[0]]
    corruptions = {
        "drop": {"coefficients": base[:-1]},
        "swap": {"coefficients": swap},
        "duplicate": {"coefficients": base + [base[-1]]},
        "empty": {"coefficients": []},
        "out_of_range": {"coefficients": [_BOUND + 1] + base[1:]},
    }
    corruption_reasons = {}
    for name, candidate in corruptions.items():
        ok, why = verify(shipping, candidate)
        corruption_reasons[name] = {"rejected": not ok, "reason": why}
    reason_set = {v["reason"] for v in corruption_reasons.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(v["rejected"] for v in corruption_reasons.values())
                and len(reason_set) == len(corruption_reasons),
        "cases": corruption_reasons,
        "distinct_reasons": len(reason_set),
    }

    wire = json.dumps(shipping["answer"], separators=(",", ":"))
    realistic = f"I used the Gram relation.\n<answer>```json\n{wire}\n```</answer>\nDone."
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"],
        "parsed_equals_answer": parsed == shipping["answer"],
        "json_native": json.loads(json.dumps(shipping["answer"])) == shipping["answer"],
    }

    # G4 and the shipping-density half of G5 use the exact declared prior.
    guess_rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        ok, _ = verify(shipping, random_candidate(shipping, guess_rng))
        guess_hits += int(ok)
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "candidate_space": search_space(shipping),
        "prior": "uniform primitive sign-normalized vectors in [-3,3]^m",
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    t0 = time.perf_counter()
    reference_answer, reference_ops = _rref_reference(shipping)
    reference_sec = time.perf_counter() - t0
    reference_ok = reference_answer is not None and verify(shipping, reference_answer)[0]
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_total >= 200_000 and guess_rate < 1e-6 and reference_ok,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_fraction": guess_rate,
        "shipping_exact_enumeration": enumerate_all(shipping),
        "demo_exact_solution_count": enumerate_all(demo),
        "baseline_wall_clock_seconds": round(reference_sec, 6),
        "baseline_arithmetic_operations": reference_ops,
        "baseline_algorithm": "exact rational reduced row echelon form",
    }

    attacks = {
        "outlier_diagonal_median": {"successes": 0, "attempts": 8},
        "alternating_public_order": {"successes": 0, "attempts": 8},
        "greedy_row_cancellation": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "pair_local_norm_without_sign_alignment": {"successes": 0, "attempts": 8},
    }
    ref_success = 0
    ref_operations = []
    ref_seconds = []
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_diagonal_median": _attack_outlier_diagonal(inst),
            "alternating_public_order": _attack_alternating(inst),
            "greedy_row_cancellation": _attack_greedy_rows(inst),
            "pair_local_norm_without_sign_alignment": _local_pair_candidate(inst),
        }
        for name, candidate in candidates.items():
            attacks[name]["successes"] += int(verify(inst, candidate)[0])
        rrng = random.Random(seed ^ 0x5A17)
        random_hit = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, rrng))[0]:
                random_hit = True
                break
        attacks["random_restart_256"]["successes"] += int(random_hit)
        rt0 = time.perf_counter()
        answer, ops = _rref_reference(inst)
        ref_seconds.append(time.perf_counter() - rt0)
        ref_operations.append(ops)
        ref_success += int(answer is not None and verify(inst, answer)[0])
    all_failed = all(v["successes"] == 0 and v["attempts"] >= 8
                     for v in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_success == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact rational RREF",
            "complexity": "O(m^3) exact arithmetic",
            "wall_clock_sec_mean": round(sum(ref_seconds) / len(ref_seconds), 6),
            "wall_clock_sec_max": round(max(ref_seconds), 6),
            "operations_mean": round(sum(ref_operations) / len(ref_operations)),
            "operations_max": max(ref_operations),
            "solves": f"{ref_success}/8, as expected",
        },
    }

    doubled = make_instance(n=2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"], seed=2718)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["dimension"] > shipping["dimension"]
                and search_space(doubled) > search_space(shipping),
        "shipping_dimension": shipping["dimension"],
        "doubled_dimension": doubled["dimension"],
        "doubled_planted_verifies": doubled_ok,
        "shipping_search_space_bits": search_space(shipping).bit_length(),
        "doubled_search_space_bits": search_space(doubled).bit_length(),
    }

    invariant = valid_carried = 0
    for seed in range(20):
        inst = make_instance(seed=1000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        rrng = random.Random(9000 + seed)
        first = list(range(inst["dimension"]))
        second = list(range(inst["dimension"]))
        rrng.shuffle(first)
        rrng.shuffle(second)
        composed = [first[second[i]] for i in range(inst["dimension"])]
        transformed = _relabel_instance(inst, composed)
        invariant += int(canonical_key(inst) == canonical_key(transformed))
        valid_carried += int(verify(transformed, transformed["answer"])[0])
    unrelated_keys = {
        canonical_key(make_instance(seed=2000 + seed,
                                    **DIFFICULTY[SHIPPING_DIFFICULTY]))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariant == 20 and valid_carried == 20 and len(unrelated_keys) == 20,
        "composed_relabellings_invariant": invariant,
        "carried_witnesses_valid": valid_carried,
        "unrelated_distinct_keys": len(unrelated_keys),
        "attempts_each": 20,
    }

    answer_lengths = []
    answer_chars = 0
    answer_atoms = 0
    for seed in range(40):
        ans = make_instance(seed=3000 + seed,
                            **DIFFICULTY[SHIPPING_DIFFICULTY])["answer"]
        encoded = json.dumps(ans, separators=(",", ":"))
        answer_lengths.append(len(encoded))
        answer_chars = max(answer_chars, len(encoded))
        answer_atoms = max(answer_atoms, _answer_atom_count(ans))
    answer_tokens = max((length + 3) // 4 for length in answer_lengths)
    intended_ops = 5 * shipping["n"] + 1
    arms = _G9_EVIDENCE["arms"]
    hinted_minus_placebo = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
    )
    within_caps = answer_chars <= 2000 and answer_atoms <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": _G9_EVIDENCE["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": _G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_ops,
    }

    report["all_passed"] = all(
        value.get("pass") for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = DIFFICULTY[SHIPPING_DIFFICULTY]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
