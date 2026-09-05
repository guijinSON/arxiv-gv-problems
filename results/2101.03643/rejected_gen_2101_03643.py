"""Rejected candidate generator for a missing Noetherian operator.

The native object is an m-primary ideal in Q[x_1,...,x_n].  Its quadratic
generators have codimension one in the vector space of all quadrics, and the
ideal also contains m^3.  Consequently a single quadratic differential
operator, together with evaluation and the first derivatives at the origin,
is a minimal differential primary decomposition.

Instances are inverse-generated: the normalized operator is sampled first,
then an independent basis of quadrics annihilated by it is assembled.  The
generator never recovers the operator from the ideal it has just made.
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
from fractions import Fraction


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "polynomial",
    "native_objects": [
        "m-primary ideal in a polynomial ring over Q",
        "quadratic Weyl-algebra differential operator",
    ],
    "verification_operations": [
        "exact integer coefficient pairing",
        "exact symmetry and normalization checks",
        "exact rational rank/nullspace computation in the audit",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize that the quadratic coefficient block is identity plus rank "
        "one, so its one-dimensional annihilator follows from one scalar "
        "invariant instead of a full Weyl-Noether nullspace computation."
    ),
    "hardness_basis": (
        "Track B: Section 5, Algorithm 5.4 computes the Weyl-Noether vector "
        "space and a complementary basis by exact linear algebra (O(M^3) for "
        "M=n(n+1)/2 quadratic monomials); at the hard n=8 preset the exact "
        "reference solve averaged 45,866 arithmetic operations and about 0.015 s "
        "over eight seeds, while the rank-one route uses 210 operations."
    ),
    "max_answer_tokens": 57,
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
    "demo": {"n": 2, "coeff_bound": 3, "mix_bound": 2},
    "easy": {"n": 6, "coeff_bound": 31, "mix_bound": 3},
    "medium": {"n": 7, "coeff_bound": 63, "mix_bound": 3},
    "hard": {"n": 8, "coeff_bound": 127, "mix_bound": 3},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The quadratic coefficient block before the normalized final monomial "
    "differs from the identity by a rank-one matrix."
)
PLACEBO_HINT = (
    "The quadratic coefficient table rewards careful attention to the stated "
    "monomial order and normalization convention."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One symmetric n by n integer matrix X encoding a divided-power "
        "quadratic differential operator; every upper-triangular entry is in "
        "1..coeff_bound and at least one upper-triangular entry equals 1."
    ),
    "bounds": {
        "shape": "n by n symmetric",
        "entry_min": 1,
        "entry_max": "coeff_bound",
        "normalization": "the minimum upper-triangular entry is 1",
        "candidate_count": "C^M-(C-1)^M, M=n(n+1)/2",
    },
}

NOTES = (
    "Definition 3.2 fixes differential primary decomposition as exact ideal "
    "membership by differential conditions, and Theorem 3.6 identifies the "
    "minimal number of operators with arithmetic multiplicity.  Section 5 "
    "specializes the operators to the Weyl algebra; Theorem 5.3 gives the "
    "minimal polynomial-ring representation and Algorithm 5.4 computes it. "
    "The Introduction explicitly says that rational maximal ideals are the "
    "standard inverse-system case, so this is Track B, not Track A.  The "
    "certificate is sampled first.  Its orthogonal hyperplane is written as "
    "[I|-z] and left-multiplied by I+uv^T, which makes every ideal generator "
    "dense without changing the ideal.  Column-size, diagonal-only, greedy, "
    "constant-ansatz, and random-restart attacks are audited; the disclosed "
    "reference algorithm is exact Gaussian elimination."
)

# Filled after the three harness arms.  Until then this is an explicit record
# of no external trials, not a claim that any oracle failed.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


def _pairs(n):
    return [(i, j) for i in range(n) for j in range(i, n)]


def _nonzero_int(rng, bound):
    value = 0
    while value == 0:
        value = rng.randint(-bound, bound)
    return value


def _matrix_from_upper(values, n):
    out = [[0] * n for _ in range(n)]
    for value, (i, j) in zip(values, _pairs(n)):
        out[i][j] = value
        out[j][i] = value
    return out


def _upper_from_matrix(matrix):
    n = len(matrix)
    return [matrix[i][j] for i, j in _pairs(n)]


def make_instance(n, seed=0, **params):
    """Inverse-generate an ideal and its top Noetherian operator."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    coeff_bound = params.pop("coeff_bound", 31)
    mix_bound = params.pop("mix_bound", 3)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if (
        isinstance(coeff_bound, bool)
        or not isinstance(coeff_bound, int)
        or coeff_bound < 2
    ):
        raise ValueError("coeff_bound must be an integer at least 2")
    if isinstance(mix_bound, bool) or not isinstance(mix_bound, int) or mix_bound < 1:
        raise ValueError("mix_bound must be a positive integer")

    rng = random.Random(seed)
    monomials = _pairs(n)
    m = len(monomials)
    r = m - 1

    # The certificate is chosen before any ideal data.  Positivity and the
    # final 1 are merely the finite-language normalization exposed to solvers.
    z = [rng.randint(1, coeff_bound) for _ in range(r)] + [1]

    # B=I+uv^T is invertible exactly when 1+v^T u is nonzero.  u_0=v_0=1
    # lets the compact route read both factors from B-I without divisions.
    while True:
        u = [1] + [_nonzero_int(rng, mix_bound) for _ in range(r - 1)]
        v = [1] + [_nonzero_int(rng, mix_bound) for _ in range(r - 1)]
        if 1 + sum(a * b for a, b in zip(u, v)) != 0:
            break
    block = [
        [(1 if i == j else 0) + u[i] * v[j] for j in range(r)]
        for i in range(r)
    ]

    # Start from [I|-z], whose row space is the exact hyperplane z^perp,
    # and change its generator basis by the invertible matrix B.
    quadrics = []
    for row in block:
        last = -sum(row[j] * z[j] for j in range(r))
        quadrics.append(row + [last])

    return {
        "family": "missing quadratic Noetherian operator",
        "n": n,
        "coeff_bound": coeff_bound,
        "mix_bound": mix_bound,
        "monomials": [[i, j] for i, j in monomials],
        "quadrics": quadrics,
        "answer": _matrix_from_upper(z, n),
    }


def _monomial_name(pair):
    i, j = pair
    if i == j:
        return f"x{i + 1}^2"
    return f"x{i + 1}*x{j + 1}"


def render(inst):
    n = inst["n"]
    m = len(inst["monomials"])
    order = ", ".join(_monomial_name(pair) for pair in inst["monomials"])
    rows = "\n".join(
        f"q{k + 1:03d}: " + " ".join(str(value) for value in row)
        for k, row in enumerate(inst["quadrics"])
    )
    example = json.dumps([[1] * n for _ in range(n)], separators=(",", ":"))
    statement = f"""Work over the exact polynomial ring R=Q[x1,...,x{n}].
Let m=<x1,...,x{n}>.  A quadratic coefficient row a=(a_ij) denotes
q=sum_(i<=j) a_ij*x_i*x_j in the monomial order printed below.

The ideal is I=<q1,...,q{m - 1}> + m^3, where m^3 means every polynomial
whose monomials all have total degree at least 3.  The displayed quadratic
rows are linearly independent.

A symmetric integer matrix X defines the divided-power differential operator
  D_X = sum_i (X_ii/2)*partial_i^2
        + sum_(i<j) X_ij*partial_i*partial_j.
Thus D_X(q)(0)=sum_(i<=j) a_ij*X_ij exactly; no floating point is involved.

Find X such that D_X(qk)(0)=0 for every displayed qk.  Together with the
operators 1, partial_1,...,partial_{n}, this D_X then characterizes membership
in I.  The required normalization is: X is exactly {n} by {n}, symmetric,
every upper-triangular entry is an integer in 1..{inst['coeff_bound']} inclusive,
and at least one upper-triangular entry equals 1.  This last condition fixes
the positive integer scale and is invariant under variable renaming.  Repeats
are allowed.

Monomial order ({m} entries):
{order}

Quadratic coefficient rows:
{rows}

Give your final answer inside <answer></answer> tags, as one JSON array of
{n} rows, each containing {n} integers in matrix order.
Example of the format only: <answer>{example}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse a tagged JSON matrix while tolerating prose and code fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    if any(not isinstance(row, list) for row in value):
        return None
    if any(
        isinstance(entry, bool) or not isinstance(entry, int)
        for row in value
        for entry in row
    ):
        return None
    return value


def verify(inst, answer):
    """Check any normalized operator exactly; never inspect inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON matrix"
    if not answer:
        return False, "answer must not be empty"
    n = inst["n"]
    if len(answer) != n:
        return False, f"expected {n} matrix rows, got {len(answer)}"
    for i, row in enumerate(answer):
        if not isinstance(row, list) or len(row) != n:
            return False, f"matrix row {i + 1} must contain exactly {n} entries"
        for j, value in enumerate(row):
            if isinstance(value, bool) or not isinstance(value, int):
                return False, f"matrix entry ({i + 1},{j + 1}) is not an integer"
    for i in range(n):
        for j in range(i + 1, n):
            if answer[i][j] != answer[j][i]:
                return False, f"matrix is not symmetric at ({i + 1},{j + 1})"
    bound = inst["coeff_bound"]
    for i, j in _pairs(n):
        if not 1 <= answer[i][j] <= bound:
            return False, f"upper entry ({i + 1},{j + 1}) is outside 1..{bound}"
    if min(answer[i][j] for i, j in _pairs(n)) != 1:
        return False, "normalization requires at least one upper entry equal to 1"

    vector = _upper_from_matrix(answer)
    for k, row in enumerate(inst["quadrics"]):
        if sum(a * x for a, x in zip(row, vector)) != 0:
            return False, f"operator does not annihilate quadratic q{k + 1}"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from the normalized symmetric-matrix language."""
    n, bound = inst["n"], inst["coeff_bound"]
    m = len(_pairs(n))
    # Partition by the position of the first 1.  A first 1 at k leaves
    # (bound-1)^k choices before it and bound^(m-k-1) choices after it.
    weights = [(bound - 1) ** k * bound ** (m - k - 1) for k in range(m)]
    pick = rng.randrange(sum(weights))
    first = 0
    while pick >= weights[first]:
        pick -= weights[first]
        first += 1
    values = [rng.randint(2, bound) for _ in range(first)]
    values.append(1)
    values.extend(rng.randint(1, bound) for _ in range(m - first - 1))
    return _matrix_from_upper(values, n)


def search_space(inst):
    bound = inst["coeff_bound"]
    m = len(inst["monomials"])
    return bound**m - (bound - 1) ** m


def enumerate_all(inst):
    total = search_space(inst)
    if total > 100_000:
        return None
    n, bound = inst["n"], inst["coeff_bound"]
    count = 0
    for values in itertools.product(range(1, bound + 1), repeat=len(_pairs(n))):
        if 1 not in values:
            continue
        candidate = _matrix_from_upper(list(values), n)
        count += int(verify(inst, candidate)[0])
    return count


def _solve_square_fraction(matrix, rhs, count_operations=False):
    """Exact Gauss-Jordan solve; return (solution, arithmetic-operation count)."""
    n = len(matrix)
    if len(rhs) != n or any(len(row) != n for row in matrix):
        return None, 0
    aug = [list(map(Fraction, row)) + [Fraction(rhs[i])] for i, row in enumerate(matrix)]
    operations = 0
    for col in range(n):
        pivot = next((r for r in range(col, n) if aug[r][col]), None)
        if pivot is None:
            return None, operations
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        pivot_value = aug[col][col]
        for j in range(col, n + 1):
            aug[col][j] /= pivot_value
            operations += 1
        for r in range(n):
            if r == col or not aug[r][col]:
                continue
            factor = aug[r][col]
            for j in range(col, n + 1):
                aug[r][j] -= factor * aug[col][j]
                operations += 2
    return [aug[i][n] for i in range(n)], operations if count_operations else 0


def _kernel_primitive(inst):
    """Recover the primitive integer normal to the quadratic row space."""
    rows = inst["quadrics"]
    r = len(rows)
    if not rows or any(len(row) != r + 1 for row in rows):
        return None
    square = [row[:r] for row in rows]
    rhs = [-row[r] for row in rows]
    solved, _ = _solve_square_fraction(square, rhs)
    if solved is None:
        return None
    vector = solved + [Fraction(1)]
    common = 1
    for value in vector:
        common = math.lcm(common, value.denominator)
    integers = [value.numerator * (common // value.denominator) for value in vector]
    divisor = 0
    for value in integers:
        divisor = math.gcd(divisor, abs(value))
    if divisor == 0:
        return None
    integers = [value // divisor for value in integers]
    if next(value for value in integers if value) < 0:
        integers = [-value for value in integers]
    return integers


def _trace_powers(matrix, maximum=4):
    n = len(matrix)
    power = [list(row) for row in matrix]
    traces = []
    for exponent in range(1, min(maximum, n) + 1):
        traces.append(sum(power[i][i] for i in range(n)))
        if exponent < min(maximum, n):
            power = [
                [sum(power[i][k] * matrix[k][j] for k in range(n)) for j in range(n)]
                for i in range(n)
            ]
    return traces


def canonical_key(inst):
    """Invariant under generator-basis changes and variable permutations.

    Full rational congruence classification of quadratic forms is deliberately
    not attempted; the README records this limitation.  The invariant first
    removes the arbitrary ideal-generator basis by recovering the primitive
    normal, then uses permutation-invariant weighted-graph signatures.
    """
    primitive = _kernel_primitive(inst)
    if primitive is None:
        payload = {"malformed": True, "shape": [len(r) for r in inst.get("quadrics", [])]}
    else:
        n = inst["n"]
        matrix = _matrix_from_upper(primitive, n)
        diagonal = sorted(matrix[i][i] for i in range(n))
        off_diagonal = sorted(matrix[i][j] for i in range(n) for j in range(i + 1, n))
        row_signatures = sorted(
            [matrix[i][i], sorted(matrix[i][j] for j in range(n) if j != i)]
            for i in range(n)
        )
        payload = {
            "n": n,
            "coeff_bound": inst["coeff_bound"],
            "diagonal": diagonal,
            "off_diagonal": off_diagonal,
            "rows": row_signatures,
            "traces": _trace_powers(matrix),
        }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def escalate(params):
    n = params.get("n")
    bound = params.get("coeff_bound", 31)
    mix = params.get("mix_bound", 3)
    if isinstance(n, int) and n < 9:
        return {"n": n + 1, "coeff_bound": 2 * bound + 1, "mix_bound": mix}
    # n=10 would still fit the serialized answer, but its intended rank-one
    # route costs 6*(10*11/2-1)=324 arithmetic operations and violates G9(c).
    # This is therefore genuine exhaustion of admissible axes, not cap_bound.
    return None


def _gaussian_reference(inst):
    """Paper-algorithm core: recover the one-dimensional exact nullspace."""
    rows = inst["quadrics"]
    r = len(rows)
    start = time.perf_counter()
    solution, operations = _solve_square_fraction(
        [row[:r] for row in rows], [-row[r] for row in rows], True
    )
    elapsed = time.perf_counter() - start
    if solution is None or any(value.denominator != 1 for value in solution):
        return None, {"operations": operations, "wall_clock_sec": elapsed}
    vector = [int(value) for value in solution] + [1]
    return _matrix_from_upper(vector, inst["n"]), {
        "operations": operations,
        "wall_clock_sec": elapsed,
    }


def _compact_rank_one(inst):
    """Sherman-Morrison recovery from B=I+uv^T, without answer access."""
    rows = inst["quadrics"]
    r = len(rows)
    block = [row[:r] for row in rows]
    correction = [
        [block[i][j] - (1 if i == j else 0) for j in range(r)]
        for i in range(r)
    ]
    u = [correction[i][0] for i in range(r)]
    v = list(correction[0])
    if correction[0][0] != 1:
        return None, 0
    if any(correction[i][j] != u[i] * v[j] for i in range(r) for j in range(r)):
        return None, 0
    rhs = [-row[r] for row in rows]
    beta = sum(a * b for a, b in zip(v, u))
    alpha = sum(a * b for a, b in zip(v, rhs))
    denominator = 1 + beta
    if denominator == 0 or alpha % denominator:
        return None, 6 * r
    scalar = alpha // denominator
    vector = [rhs[i] - u[i] * scalar for i in range(r)] + [1]
    return _matrix_from_upper(vector, inst["n"]), 6 * r


def _clamp(value, bound):
    return min(bound, max(1, int(value)))


def _candidate_from_prefix(inst, prefix):
    r = len(inst["quadrics"])
    values = [_clamp(value, inst["coeff_bound"]) for value in prefix[:r]] + [1]
    return _matrix_from_upper(values, inst["n"])


def _attack_candidates(inst, seed):
    rows = inst["quadrics"]
    r = len(rows)
    block = [row[:r] for row in rows]
    rhs = [-row[r] for row in rows]
    bound = inst["coeff_bound"]

    norms = [sum(abs(rows[i][j]) for i in range(r)) for j in range(r)]
    norm_order = {value: rank + 1 for rank, value in enumerate(sorted(set(norms)))}
    outlier = _candidate_from_prefix(inst, [norm_order[value] for value in norms])

    diagonal = []
    for i in range(r):
        den = block[i][i]
        if den == 0:
            diagonal.append(1)
        else:
            diagonal.append(_clamp(abs(rhs[i]) // max(1, abs(den)), bound))

    greedy = [1] * r
    for i in range(r):
        residual = rhs[i] - sum(block[i][j] * greedy[j] for j in range(i))
        den = block[i][i]
        if den:
            greedy[i] = _clamp(abs(residual) // max(1, abs(den)), bound)

    ansatz = [
        _candidate_from_prefix(inst, [1] * r),
        _candidate_from_prefix(inst, [bound] * r),
        _candidate_from_prefix(inst, [(i % bound) + 1 for i in range(r)]),
        _candidate_from_prefix(inst, [((i * i + 1) % bound) + 1 for i in range(r)]),
    ]

    rrng = random.Random(seed ^ 0x210103643)
    restarts = [random_candidate(inst, rrng) for _ in range(256)]
    return {
        "outlier_column_l1_rank": [outlier],
        "diagonal_only_relaxation": [_candidate_from_prefix(inst, diagonal)],
        "greedy_left_to_right": [_candidate_from_prefix(inst, greedy)],
        "by_hand_constant_and_small_patterns": ansatz,
        "random_restart_256": restarts,
    }


def _permute_variables(inst, permutation):
    n = inst["n"]
    old_pairs = _pairs(n)
    old_index = {pair: k for k, pair in enumerate(old_pairs)}
    column_map = []
    for i, j in old_pairs:
        a, b = permutation[i], permutation[j]
        column_map.append(old_index[(min(a, b), max(a, b))])
    out = {key: value for key, value in inst.items() if key not in {"quadrics", "answer"}}
    out["quadrics"] = [[row[k] for k in column_map] for row in inst["quadrics"]]
    out["answer"] = [
        [inst["answer"][permutation[i]][permutation[j]] for j in range(n)]
        for i in range(n)
    ]
    return out


def _relabel_variants(inst, seed):
    rng = random.Random(seed)
    n = inst["n"]
    permutation = list(range(n))
    rng.shuffle(permutation)

    reordered = {key: value for key, value in inst.items() if key != "quadrics"}
    reordered["quadrics"] = list(reversed([list(row) for row in inst["quadrics"]]))

    changed_basis = {key: value for key, value in inst.items() if key != "quadrics"}
    changed_basis["quadrics"] = [list(row) for row in inst["quadrics"]]
    changed_basis["quadrics"][1] = [
        a + 2 * b
        for a, b in zip(changed_basis["quadrics"][1], changed_basis["quadrics"][0])
    ]

    variable = _permute_variables(inst, permutation)
    composed = _permute_variables(changed_basis, permutation)
    return [reordered, changed_basis, variable, composed]


def selftest():
    report = {}
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
        "generation_route": "inverse generation: operator first, ideal second",
    }

    inst = make_instance(seed=19, **shipping)
    answer = inst["answer"]
    dropped = [list(row) for row in answer[:-1]]
    duplicated = [list(row) for row in answer] + [list(answer[0])]
    swapped = [list(row) for row in answer]
    swapped[0][1], swapped[0][2] = swapped[0][2], swapped[0][1]
    out_of_range = [list(row) for row in answer]
    out_of_range[0][0] = inst["coeff_bound"] + 1
    corruptions = {
        "drop": dropped,
        "swap": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": why}
    reasons = [case["reason"] for case in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and len(set(reasons)) == len(reasons),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The normalized divided-power operator is below.\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nIts coefficient pairing vanishes on every row."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    guess_rng = random.Random(0x210103643)
    guess_total = 200_000
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "exact_density": f"1/{search_space(inst)}",
        "candidate_space_bits": search_space(inst).bit_length(),
        "wall_clock_sec": round(guess_seconds, 6),
        "sampling_prior": "uniform over every stated symmetry, bound, and normalization constraint",
    }

    attack_names = [
        "outlier_column_l1_rank",
        "diagonal_only_relaxation",
        "greedy_left_to_right",
        "by_hand_constant_and_small_patterns",
        "random_restart_256",
    ]
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_operations = 0
    compact_successes = 0
    compact_operations = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        candidates = _attack_candidates(trial, seed)
        for name in attack_names:
            start = time.perf_counter()
            won = any(verify(trial, candidate)[0] for candidate in candidates[name])
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(won)
        recovered, cost = _gaussian_reference(trial)
        reference_seconds += cost["wall_clock_sec"]
        reference_operations += cost["operations"]
        reference_successes += int(recovered is not None and verify(trial, recovered)[0])
        compact, operations = _compact_rank_one(trial)
        compact_operations = max(compact_operations, operations)
        compact_successes += int(compact is not None and verify(trial, compact)[0])

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "exact rational Gaussian elimination for the Weyl-Noether nullspace",
        "paper_route": "Section 5, Algorithm 5.4, steps (2.5)-(2.7)",
        "complexity": "O(M^3) exact arithmetic for M=n(n+1)/2",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_operations // 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "rank-one Sherman-Morrison scalar invariant",
            "solves": f"{compact_successes}/8",
            "operations_upper_bound": compact_operations,
        },
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and demo_count == 1
        and all_failed
        and reference_successes == 8
        and compact_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_sample_density": guess_fraction,
        "shipping_exact_solution_count": 1,
        "shipping_exact_density": f"1/{search_space(inst)}",
        "demo_exact_solution_count": demo_count,
        "baseline_attack": "random_restart_256",
        "baseline_attack_wall_clock_sec": round(
            attack_seconds["random_restart_256"] / 8, 6
        ),
        "baseline_attack_iterations": 256,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    ladder = [len(_pairs(DIFFICULTY[name]["n"])) for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and len(render(doubled)) > len(render(inst))
        and ladder == sorted(ladder)
        and len(set(ladder)) == len(ladder),
        "quadratic_monomials_by_preset": ladder,
        "shipping_n": inst["n"],
        "shipping_monomials": len(inst["monomials"]),
        "doubled_n": doubled["n"],
        "doubled_monomials": len(doubled["monomials"]),
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_why,
        "candidate_space_bits_shipping": search_space(inst).bit_length(),
        "candidate_space_bits_doubled": search_space(doubled).bit_length(),
    }

    invariant_count = 0
    real_transform_count = 0
    invariant_failures = []
    for seed in range(20):
        original = make_instance(seed=1000 + seed, **shipping)
        key = canonical_key(original)
        for variant in _relabel_variants(original, seed):
            invariant_count += 1
            carried_ok, carried_why = verify(variant, variant["answer"])
            real_transform_count += int(carried_ok)
            if canonical_key(variant) != key or not carried_ok:
                invariant_failures.append([seed, carried_why])
    unrelated_keys = {
        canonical_key(make_instance(seed=2000 + seed, **shipping)) for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": not invariant_failures
        and real_transform_count == invariant_count
        and len(unrelated_keys) == 20,
        "invariance_checks": invariant_count,
        "invariance_failures": invariant_failures,
        "real_transform_verifications": real_transform_count,
        "unrelated_distinct": len(unrelated_keys),
        "unrelated_attempts": 20,
        "canonicalized_symmetries": [
            "quadratic-generator reorder",
            "invertible quadratic-generator basis shear",
            "variable permutation",
            "compositions of these",
        ],
    }

    serialized_lengths = []
    for seed in range(20):
        sample = make_instance(seed=3000 + seed, **shipping)["answer"]
        serialized_lengths.append(len(json.dumps(sample, separators=(",", ":"))))
    answer_chars = max(serialized_lengths)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = inst["n"] * inst["n"]
    within_caps = (
        answer_chars <= 2000
        and answer_tokens <= 500
        and answer_elements <= 256
        and compact_operations <= 300
    )
    arms = {
        name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else 0.0
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "diagnostic_only": True,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact_operations,
    }

    report["pass"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
