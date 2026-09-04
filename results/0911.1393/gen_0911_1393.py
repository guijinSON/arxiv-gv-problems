"""Verified generator for zero singular vectors of a rational 3-tensor.

The family specializes Problem 3.1 of Hillar--Lim (arXiv:0911.1393) to a
1 x n x n tensor.  Generation composes two exact identities; it never solves
the matrix that it emits.  Only standard-library code is required.
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
from fractions import Fraction


# Make the repository helper package available when harden.py imports this file
# from results/0911.1393.  The implementation remains standard-library-only if
# the package is absent.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - supported fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "rational 3-tensor of shape 1 x n x n",
        "left and right rational singular vectors",
    ],
    "verification_operations": [
        "exact integer tensor contraction",
        "exact zero comparison",
        "integer normalization and bound checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The top finite-difference stencil annihilates every polynomial row "
        "of lower degree; without that identity one must compute two exact "
        "nullspaces."
    ),
    "hardness_basis": (
        "Track B: exact Gauss-Jordan elimination solves the 1 x n x n special "
        "case in O(n^3) rational operations; at shipping n=84 an instrumented "
        "run used 774,638 exact operations and about 0.7 seconds, while the "
        "finite-difference route uses 250 exact arithmetic operations and is "
        "not safely executable by hand."
    ),
    "max_answer_tokens": 487,
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
        "A JSON triple [u,v,w] of integer vectors of lengths 1,n,n.  The "
        "specified anchor coordinate of each vector is 1; every other entry "
        "is an integer in the inclusive interval [-B,B], where B is printed "
        "in the instance."
    ),
    "bounds": {
        "vectors": 3,
        "lengths": [1, "n", "n"],
        "anchor_value": 1,
        "coefficient_min": "-B",
        "coefficient_max": "B",
        "integer_coefficients_only": True,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 3, "coefficient_span": 9},
    "easy": {"n": 48, "coefficient_span": 9},
    "medium": {"n": 66, "coefficient_span": 9},
    "hard": {"n": 84, "coefficient_span": 9},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Interpret the binomial rows as finite-difference evaluations, then undo "
    "the listed coordinate orders and column weights."
)
PLACEBO_HINT = (
    "Check the vector lengths and normalizations methodically, then keep the "
    "listed coordinate orders and coefficient bounds in view."
)

# Filled only after the script-owned oracle runs.  Keeping it explicit prevents
# a preliminary local self-test from being mistaken for oracle evidence.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES = r"""
Paper triage.  Section 3, Problem 3.1 fixes tensor bilinear feasibility: for a
tensor A in Q^{l x m x n}, all three partial contractions against nonzero
vectors u,v,w must vanish.  Section 6 identifies the same equations with zero
tensor singular value.  Theorem 3.8 proves the unrestricted problem NP-hard,
but that worst-case theorem does not license a Track A claim for an inverse
distribution.  This module therefore declares Track B.  Its l=1 specialization
is only a matrix: the second and third contraction families are Aw=0 and
v^T A=0.  Exact Gaussian or Bareiss-style elimination is polynomial time.
The introduction's matrix/tensor tractability boundary and the conclusion's
warning that hardness is asymptotic are the easy-regime results that control
this choice.

Construction.  For N=n-1, the Nth forward-difference identity says
sum_j (-1)^j binom(N,j) p(j)=0 for every polynomial p of degree below N.
The first n-1 rows are the binomial basis p_r(j)=binom(j,r), with nonzero
column weights d_j.  The final row is the visible linear combination with
coefficients c_r.  Thus w_j=(-1)^j binom(N,j)/d_j is a right nullvector and
(c_0,...,c_{n-2},-1) is a left nullvector.  Random row and column orders carry
both witnesses through a tensor-coordinate relabelling.  This is composition
of identities, not a solve of the emitted instance.

Attack handling.  Plants and decoys are not separate objects: all coordinates
participate in the same Pascal evaluation matrix.  The per-column outlier,
small-coefficient greedy cancellation, 256 bounded random restarts, and the
constant/alternating/geometric by-hand ansatz are tested on eight seeds and do
not return a certificate.  The standard exact nullspace algorithm is reported
separately, as Track B requires, and succeeds.  Column divisors make the right
vector a non-tabulated weighted stencil; random final-row coefficients and two
coordinate orders remove positional and magnitude shortcuts while preserving
the finite-difference route.
""".strip()


def _validate_params(n: int, coefficient_span: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if (isinstance(coefficient_span, bool)
            or not isinstance(coefficient_span, int)
            or coefficient_span < 2):
        raise ValueError("coefficient_span must be an integer at least 2")


def _nonzero_small(rng: random.Random, span: int) -> int:
    x = rng.randint(-span, span - 1)
    return x if x != 0 else span


def _base_vectors(inst: dict) -> tuple[list[int], list[int]]:
    n = inst["n"]
    left = list(inst["combination_coefficients"]) + [-1]
    right = [
        (-1 if j & 1 else 1) *
        (math.comb(n - 1, j) // inst["column_weights"][j])
        for j in range(n)
    ]
    return left, right


def _from_base(base: list[int], order: list[int]) -> list[int]:
    """Coordinates in displayed order; displayed i is base order[i]."""
    return [base[order[i]] for i in range(len(order))]


def _certificate(inst: dict) -> list[list[int]]:
    left, right = _base_vectors(inst)
    if inst.get("transpose_modes", False):
        left, right = right, left
    return [
        [1],
        _from_base(left, inst["row_order"]),
        _from_base(right, inst["column_order"]),
    ]


def make_instance(n: int, seed: int = 0, coefficient_span: int = 9,
                  **params) -> dict:
    """Construct a certified zero-singular-vector instance by identities."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, coefficient_span)
    rng = random.Random(seed)

    c = [1] + [_nonzero_small(rng, coefficient_span) for _ in range(n - 2)]
    weights = []
    for j in range(n):
        value = math.comb(n - 1, j)
        divisors = [d for d in range(1, coefficient_span + 1)
                    if value % d == 0]
        weights.append(rng.choice(divisors))
    # Preserve a displayed normalization anchor while randomizing everything
    # else.  G8 separately tests arbitrary relabellings that move the anchor.
    row_order = [0] + list(range(1, n))
    column_order = [0] + list(range(1, n))
    # These two discarded shuffles are part of the published seed mapping.  Do
    # not remove them: the oracle transcripts were generated with these draws.
    discarded = list(range(1, n)); rng.shuffle(discarded)
    discarded = list(range(1, n)); rng.shuffle(discarded)
    row_tail = row_order[1:]
    col_tail = column_order[1:]
    rng.shuffle(row_tail)
    rng.shuffle(col_tail)
    row_order = [0] + row_tail
    column_order = [0] + col_tail

    bound = max(coefficient_span, math.comb(n - 1, (n - 1) // 2))
    inst = {
        "family": "weighted_pascal_zero_singular_vectors",
        "n": n,
        "tensor_shape": [1, n, n],
        "combination_coefficients": c,
        "column_weights": weights,
        "row_order": row_order,
        "column_order": column_order,
        "row_anchor": row_order.index(0),
        "column_anchor": column_order.index(0),
        "coefficient_bound": bound,
    }
    inst["answer"] = _certificate(inst)
    # The shipping family promises a writable certificate for every seed, not
    # merely for the sampled seeds.  An exceptionally all-negative c can add
    # one character per coordinate; reflecting c preserves the construction.
    if n <= DIFFICULTY["hard"]["n"] and len(json.dumps(inst["answer"])) > 2000:
        inst["combination_coefficients"] = [abs(x) for x in c]
        inst["answer"] = _certificate(inst)
        if len(json.dumps(inst["answer"])) > 2000:
            raise AssertionError("certificate exceeds the shipping character cap")
    return inst


def _base_matrix(inst: dict) -> list[list[int]]:
    n = inst["n"]
    c = inst["combination_coefficients"]
    d = inst["column_weights"]
    rows = [[d[j] * math.comb(j, r) for j in range(n)]
            for r in range(n - 1)]
    rows.append([
        d[j] * sum(c[r] * math.comb(j, r) for r in range(n - 1))
        for j in range(n)
    ])
    return rows


def _display_matrix(inst: dict) -> list[list[int]]:
    base = _base_matrix(inst)
    if inst.get("transpose_modes", False):
        base = [list(col) for col in zip(*base)]
    ro, co = inst["row_order"], inst["column_order"]
    return [[base[ro[i]][co[j]] for j in range(inst["n"])]
            for i in range(inst["n"])]


def render(inst: dict) -> str:
    n = inst["n"]
    lines = [
        "ZERO SINGULAR VECTORS OF A RATIONAL 3-TENSOR",
        "",
        "All indices below are 0-based.  For integers j,r, binom(j,r) is "
        "the binomial coefficient, with binom(j,r)=0 when r>j.",
        "",
        f"n = {n}",
        f"Tensor shape = 1 x {n} x {n}",
        "combination_coefficients c[0..n-2] = "
        + json.dumps(inst["combination_coefficients"], separators=(",", ":")),
        "column_weights d[0..n-1] = "
        + json.dumps(inst["column_weights"], separators=(",", ":")),
        "row_order = " + json.dumps(inst["row_order"], separators=(",", ":")),
        "column_order = "
        + json.dumps(inst["column_order"], separators=(",", ":")),
        f"row_anchor = {inst['row_anchor']}",
        f"column_anchor = {inst['column_anchor']}",
        f"B = {inst['coefficient_bound']}",
        "",
        "These arrays define the tensor completely.  It has one n x n slice A. "
        "First define a base matrix M.  For 0 <= r <= n-2 and 0 <= j < n,",
        "    M[r,j] = d[j] * binom(j,r).",
        "For its final row,",
        "    M[n-1,j] = d[j] * sum(c[r] * binom(j,r) for r=0..n-2).",
        "The displayed tensor coordinates are",
        ("    A[i,j] = M[column_order[j], row_order[i]]."
         if inst.get("transpose_modes", False) else
         "    A[i,j] = M[row_order[i], column_order[j]]."),
        "Every operation in these formulas is exact integer arithmetic.",
        "",
        "Find three NONZERO integer vectors u, v, w for which 0 is a tensor "
        "singular value.  Here u has length 1 and v,w each have length n.  "
        "They must satisfy all three exact contraction conditions:",
        "    sum(v[i]*A[i,j]*w[j] for i=0..n-1, j=0..n-1) = 0;",
        "    u[0] * sum(A[i,j]*w[j] for j=0..n-1) = 0 for every i;",
        "    u[0] * sum(v[i]*A[i,j] for i=0..n-1) = 0 for every j.",
        "Use the projective normalization u[0]=1, v[row_anchor]=1, and "
        "w[column_anchor]=1.  Every coordinate must be a base-10 integer in "
        "the inclusive interval [-B,B].  Vector order matters; repeated "
        "coordinate values are allowed.",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as one JSON "
        "array [u,v,w] of the three integer arrays.",
        "Example: <answer>[[1],[1,2,-1],[1,-2,1]]</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text) -> object | None:
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, list) else None


def _integer_vector(value: object, length: int, name: str,
                    bound: int) -> tuple[list[int] | None, str | None]:
    if not isinstance(value, list):
        return None, f"{name} is not an array"
    if len(value) != length:
        return None, f"{name} has wrong length: expected {length}, got {len(value)}"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in value):
        return None, f"{name} contains a non-integer coordinate"
    if any(abs(x) > bound for x in value):
        return None, f"{name} has a coefficient outside inclusive [-B,B]"
    return list(value), None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any bounded normalized singular-vector witness; never use answer."""
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list):
        return False, "answer is not a JSON array"
    if len(answer) != 3:
        return False, f"expected exactly three vectors [u,v,w], got {len(answer)}"
    n, bound = inst["n"], inst["coefficient_bound"]
    u, why = _integer_vector(answer[0], 1, "u", bound)
    if why:
        return False, why
    v, why = _integer_vector(answer[1], n, "v", bound)
    if why:
        return False, why
    w, why = _integer_vector(answer[2], n, "w", bound)
    if why:
        return False, why
    assert u is not None and v is not None and w is not None
    if u[0] != 1:
        return False, "normalization failed: u[0] must equal 1"
    if v[inst["row_anchor"]] != 1:
        return False, "normalization failed: v[row_anchor] must equal 1"
    if w[inst["column_anchor"]] != 1:
        return False, "normalization failed: w[column_anchor] must equal 1"

    # Undo only the coordinate ordering.  This computes the tensor contractions
    # from the displayed definition, with Python's unbounded exact integers.
    vb = [0] * n
    wb = [0] * n
    for i, base_i in enumerate(inst["row_order"]):
        vb[base_i] = v[i]
    for j, base_j in enumerate(inst["column_order"]):
        wb[base_j] = w[j]
    c, d = inst["combination_coefficients"], inst["column_weights"]

    def left_m(x: list[int]) -> list[int]:
        return [d[j] * sum(
            (x[r] + x[n - 1] * c[r]) * math.comb(j, r)
            for r in range(n - 1)
        ) for j in range(n)]

    if not inst.get("transpose_modes", False):
        right_values = []
        for r in range(n - 1):
            val = sum(d[j] * math.comb(j, r) * wb[j] for j in range(n))
            right_values.append(val)
            if val != 0:
                return False, f"right contraction A*w is nonzero in base row {r}"
        last = sum(c[r] * right_values[r] for r in range(n - 1))
        right_values.append(last)
        if last != 0:
            return False, "right contraction A*w is nonzero in the final base row"
        left_values = left_m(vb)
        for j, val in enumerate(left_values):
            if val != 0:
                return False, f"left contraction v^T*A is nonzero in base column {j}"
        scalar = sum(vb[r] * right_values[r] for r in range(n))
    else:
        right_values = left_m(wb)       # M^T w
        for r, val in enumerate(right_values):
            if val != 0:
                return False, (
                    "right contraction A*w is nonzero in transposed base row "
                    f"{r}"
                )
        left_values = [                 # v^T M^T = (M v)^T
            sum(d[k] * math.comb(k, r) * vb[k] for k in range(n))
            for r in range(n - 1)
        ]
        left_values.append(sum(c[r] * left_values[r] for r in range(n - 1)))
        for j, val in enumerate(left_values):
            if val != 0:
                return False, (
                    "left contraction v^T*A is nonzero in transposed base "
                    f"column {j}"
                )
        scalar = sum(vb[r] * right_values[r] for r in range(n))
    if scalar != 0:
        return False, "bilinear scalar contraction v^T*A*w is nonzero"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniform over the stated bounded, anchored integer-vector language."""
    n, bound = inst["n"], inst["coefficient_bound"]
    v = [rng.randint(-bound, bound) for _ in range(n)]
    w = [rng.randint(-bound, bound) for _ in range(n)]
    v[inst["row_anchor"]] = 1
    w[inst["column_anchor"]] = 1
    return [[1], v, w]


def search_space(inst: dict) -> int:
    # u and the two anchors are fixed; all remaining coordinates are free.
    return (2 * inst["coefficient_bound"] + 1) ** (2 * (inst["n"] - 1))


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the exact bounded language only when it has <=200k words."""
    if search_space(inst) > 200_000:
        return None
    n, bound = inst["n"], inst["coefficient_bound"]
    vi = [i for i in range(n) if i != inst["row_anchor"]]
    wi = [i for i in range(n) if i != inst["column_anchor"]]
    count = 0
    for values in itertools.product(range(-bound, bound + 1),
                                    repeat=len(vi) + len(wi)):
        v, w = [0] * n, [0] * n
        v[inst["row_anchor"]] = w[inst["column_anchor"]] = 1
        for i, x in zip(vi, values[:len(vi)]):
            v[i] = x
        for i, x in zip(wi, values[len(vi):]):
            w[i] = x
        if verify(inst, [[1], v, w])[0]:
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """Construction-normal form, invariant under row/column relabelling."""
    payload = {
        "family": inst["family"],
        "n": inst["n"],
        "c": inst["combination_coefficients"],
        "d": inst["column_weights"],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params: dict) -> dict | None:
    n = int(params.get("n", 0))
    if n < DIFFICULTY["hard"]["n"]:
        return {"n": DIFFICULTY["hard"]["n"],
                "coefficient_span": int(params.get("coefficient_span", 9))}
    return None


def _relabel_instance(inst: dict, row_new_to_old: list[int],
                      col_new_to_old: list[int]) -> tuple[dict, object]:
    """Apply genuine tensor-coordinate permutations and carry the witness."""
    n = inst["n"]
    if sorted(row_new_to_old) != list(range(n)):
        raise ValueError("bad row permutation")
    if sorted(col_new_to_old) != list(range(n)):
        raise ValueError("bad column permutation")
    out = {k: (list(v) if isinstance(v, list) else v)
           for k, v in inst.items() if k != "answer"}
    out["row_order"] = [inst["row_order"][i] for i in row_new_to_old]
    out["column_order"] = [inst["column_order"][j] for j in col_new_to_old]
    out["row_anchor"] = out["row_order"].index(0)
    out["column_anchor"] = out["column_order"].index(0)
    old = inst["answer"]
    carried = [
        list(old[0]),
        [old[1][i] for i in row_new_to_old],
        [old[2][j] for j in col_new_to_old],
    ]
    out["answer"] = carried
    return out, carried


def _transpose_instance(inst: dict) -> tuple[dict, object]:
    """Swap tensor modes 2 and 3 and exchange their carried witnesses."""
    out = {k: (list(v) if isinstance(v, list) else v)
           for k, v in inst.items() if k != "answer"}
    out["transpose_modes"] = not inst.get("transpose_modes", False)
    out["row_order"], out["column_order"] = (
        list(inst["column_order"]), list(inst["row_order"])
    )
    out["row_anchor"], out["column_anchor"] = (
        inst["column_anchor"], inst["row_anchor"]
    )
    old = inst["answer"]
    carried = [list(old[0]), list(old[2]), list(old[1])]
    out["answer"] = carried
    return out, carried


def _true_left_from_public_data(inst: dict) -> list[int]:
    base = list(inst["combination_coefficients"]) + [-1]
    return _from_base(base, inst["row_order"])


def _attack_outlier(inst: dict) -> object:
    n = inst["n"]
    base = _base_matrix(inst)
    choices = [j for j in range(1, n) if inst["column_weights"][j] == 1]
    j = min(choices or list(range(1, n)),
            key=lambda q: sum(abs(base[r][q]) for r in range(n)))
    wb = [0] * n
    wb[0] = 1
    if inst["column_weights"][j] == 1:
        wb[j] = -1
    return [[1], _true_left_from_public_data(inst),
            _from_base(wb, inst["column_order"])]


def _attack_greedy_small(inst: dict) -> object:
    """Cancel the first row greedily while insisting on small coefficients."""
    n = inst["n"]
    wb = [0] * n
    wb[0] = 1
    residual = inst["column_weights"][0]
    for j in range(1, n):
        d = inst["column_weights"][j]
        proposal = max(-9, min(9, -residual // d))
        wb[j] = proposal
        residual += d * proposal
        if residual == 0:
            break
    return [[1], _true_left_from_public_data(inst),
            _from_base(wb, inst["column_order"])]


def _attack_ansatz(inst: dict) -> bool:
    n = inst["n"]
    candidates = [
        [1] * n,
        [1 if j % 2 == 0 else -1 for j in range(n)],
        [j + 1 for j in range(n)],
        [(1 if j % 2 == 0 else -1) * (j + 1) for j in range(n)],
        [2 ** j for j in range(n)],
    ]
    left = _true_left_from_public_data(inst)
    for wb in candidates:
        ans = [[1], left, _from_base(wb, inst["column_order"])]
        if verify(inst, ans)[0]:
            return True
    return False


def _attack_random_restart(inst: dict, seed: int, restarts: int = 256) -> bool:
    rng = random.Random(seed ^ 0x5A17D3)
    n = inst["n"]
    left = _true_left_from_public_data(inst)
    for _ in range(restarts):
        wb = [rng.randint(-2, 2) for _ in range(n)]
        wb[0] = 1
        ans = [[1], left, _from_base(wb, inst["column_order"])]
        if verify(inst, ans)[0]:
            return True
    return False


def _rref_nullvector(A: list[list[int]], anchor: int) -> tuple[list[int] | None, int]:
    """Generic exact Gauss-Jordan nullspace; return anchored integer vector."""
    R = [[Fraction(x) for x in row] for row in A]
    m, n = len(R), len(R[0])
    pivots = []
    row = 0
    operations = 0
    for col in range(n):
        pivot = next((i for i in range(row, m) if R[i][col]), None)
        if pivot is None:
            continue
        R[row], R[pivot] = R[pivot], R[row]
        pv = R[row][col]
        for j in range(col, n):
            R[row][j] /= pv
            operations += 1
        for i in range(m):
            if i == row or not R[i][col]:
                continue
            factor = R[i][col]
            for j in range(col, n):
                R[i][j] -= factor * R[row][j]
                operations += 2
        pivots.append(col)
        row += 1
        if row == m:
            break
    free = [j for j in range(n) if j not in pivots]
    if len(free) != 1:
        return None, operations
    x = [Fraction(0) for _ in range(n)]
    x[free[0]] = 1
    for i, col in enumerate(pivots):
        x[col] = -R[i][free[0]]
    if x[anchor] == 0:
        return None, operations
    scale = x[anchor]
    x = [z / scale for z in x]
    operations += n
    if any(z.denominator != 1 for z in x):
        return None, operations
    return [z.numerator for z in x], operations


def _reference_algorithm(inst: dict) -> dict:
    """The Track B standard algorithm: two generic exact nullspaces."""
    A = _display_matrix(inst)
    t0 = time.perf_counter()
    w, right_ops = _rref_nullvector(A, inst["column_anchor"])
    At = [list(col) for col in zip(*A)]
    v, left_ops = _rref_nullvector(At, inst["row_anchor"])
    elapsed = time.perf_counter() - t0
    answer = [[1], v, w] if v is not None and w is not None else None
    ok = answer is not None and verify(inst, answer)[0]
    return {
        "ok": ok,
        "answer": answer,
        "wall_clock_sec": elapsed,
        "operations": left_ops + right_ops,
    }


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    wire = json.dumps(answer)
    assert isinstance(answer, list)
    elements = sum(len(v) for v in answer if isinstance(v, list))
    return len(wire), math.ceil(len(wire) / 4), elements


def selftest() -> dict:
    report: dict = {}

    # G1: all four presets, three seeds each.
    failures = []
    attempts = 0
    for name, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": name, "seed": seed, "reason": why})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": name, "seed": seed,
                                 "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260904, **ship_params)
    original = inst["answer"]
    corruptions = {}

    bad = json.loads(json.dumps(original))
    bad[2].pop()
    corruptions["drop_one"] = verify(inst, bad)
    bad = json.loads(json.dumps(original))
    a = inst["column_anchor"]
    b = next(i for i, x in enumerate(bad[2]) if i != a and x != 1)
    bad[2][a], bad[2][b] = bad[2][b], bad[2][a]
    corruptions["swap_one"] = verify(inst, bad)
    bad = json.loads(json.dumps(original)) + [list(original[2])]
    corruptions["duplicate"] = verify(inst, bad)
    corruptions["empty"] = verify(inst, [])
    bad = json.loads(json.dumps(original))
    idx = next(i for i in range(inst["n"]) if i != inst["row_anchor"])
    bad[1][idx] = inst["coefficient_bound"] + 1
    corruptions["out_of_range"] = verify(inst, bad)
    reasons = [why for ok, why in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not ok for ok, _ in corruptions.values())
                and len(set(reasons)) == len(reasons),
        "cases": {k: {"rejected": not val[0], "reason": val[1]}
                  for k, val in corruptions.items()},
        "distinct_reasons": len(set(reasons)),
    }

    wire = json.dumps(original, separators=(",", ":"))
    parsed = parse_answer(
        "I used the finite-difference identity.\n```json\n<answer>"
        + wire + "</answer>\n```\nThe contractions vanish."
    )
    report["G3_round_trip"] = {
        "pass": parsed == original,
        "surrounding_prose_and_fence": True,
        "json_round_trip": parsed == original,
    }

    # One structure-aware density sample serves G4 and the shipping part of G5.
    guess_rng = random.Random(0x9141393)
    guess_total = 200_000
    hits = 0
    t_guess = time.perf_counter()
    for _ in range(guess_total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    guess_sec = time.perf_counter() - t_guess
    report["G4_guess_resistance"] = {
        "pass": hits / guess_total < 1e-6,
        "hits": hits,
        "total": guess_total,
        "empirical_probability": hits / guess_total,
        "prior": (
            "uniform over every free bounded integer coordinate after fixing "
            "all three stated normalization anchors"
        ),
        "candidate_space_bits": search_space(inst).bit_length(),
        "sampling_wall_seconds": guess_sec,
    }

    baseline = _reference_algorithm(inst)
    demo_count = enumerate_all(make_instance(seed=0, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline"] = {
        "pass": baseline["ok"] and hits / guess_total < 1e-6
                and demo_count is not None,
        "shipping_observed_valid_fraction": hits / guess_total,
        "shipping_density_sample_count": guess_total,
        "shipping_valid_hits": hits,
        "baseline_wall_seconds": baseline["wall_clock_sec"],
        "baseline_operation_count": baseline["operations"],
        "baseline_success_count": int(baseline["ok"]),
        "demo_exact_solution_count": demo_count,
        "shipping_candidate_space_bits": search_space(inst).bit_length(),
        "enumerate_all_shipping": None,
    }

    attack_names = {
        "outlier_lowest_column_norm": 0,
        "greedy_small_coefficient_cancellation": 0,
        "random_restart_256_bounded": 0,
        "obvious_constant_alternating_geometric_ansatz": 0,
    }
    reference_runs = []
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **ship_params)
        if verify(trial, _attack_outlier(trial))[0]:
            attack_names["outlier_lowest_column_norm"] += 1
        if verify(trial, _attack_greedy_small(trial))[0]:
            attack_names["greedy_small_coefficient_cancellation"] += 1
        if _attack_random_restart(trial, seed):
            attack_names["random_restart_256_bounded"] += 1
        if _attack_ansatz(trial):
            attack_names["obvious_constant_alternating_geometric_ansatz"] += 1
        reference_runs.append(_reference_algorithm(trial))
    all_failed = all(x == 0 for x in attack_names.values())
    ref_ok = sum(int(x["ok"]) for x in reference_runs)
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_ok == 8,
        "attacks": {
            name: {"successes": successes, "attempts": 8}
            for name, successes in attack_names.items()
        },
        "reference_algorithm": {
            "name": "exact Gauss-Jordan left and right nullspaces over Q",
            "complexity": "O(n^3) exact rational arithmetic",
            "wall_clock_sec": sum(x["wall_clock_sec"] for x in reference_runs),
            "mean_wall_clock_sec": (
                sum(x["wall_clock_sec"] for x in reference_runs) / 8
            ),
            "operations": sum(x["operations"] for x in reference_runs),
            "mean_operations": sum(x["operations"] for x in reference_runs) // 8,
            "solves": f"{ref_ok}/8, as expected",
        },
    }

    doubled = make_instance(n=2 * ship_params["n"], seed=77,
                            coefficient_span=ship_params["coefficient_span"])
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok,
        "base_n": ship_params["n"],
        "doubled_n": doubled["n"],
        "doubled_verify": doubled_why,
        "reference_complexity_ratio": 8,
    }

    invariance_checks = 0
    witness_checks = 0
    for seed in range(20):
        small = make_instance(n=12, seed=seed, coefficient_span=9)
        rng = random.Random(seed ^ 0xC4108)
        rp = list(range(12)); rng.shuffle(rp)
        cp = list(range(12)); rng.shuffle(cp)
        r2 = list(range(12)); rng.shuffle(r2)
        c2 = list(range(12)); rng.shuffle(c2)
        transforms = [(rp, list(range(12))),
                      (list(range(12)), cp),
                      ([rp[r2[i]] for i in range(12)],
                       [cp[c2[i]] for i in range(12)])]
        for rows, cols in transforms:
            moved, carried = _relabel_instance(small, rows, cols)
            invariance_checks += int(canonical_key(moved) == canonical_key(small))
            witness_checks += int(verify(moved, carried)[0])
        transposed, carried = _transpose_instance(small)
        invariance_checks += int(canonical_key(transposed) == canonical_key(small))
        witness_checks += int(verify(transposed, carried)[0])
        composed, carried = _relabel_instance(transposed, rp, cp)
        invariance_checks += int(canonical_key(composed) == canonical_key(small))
        witness_checks += int(verify(composed, carried)[0])
    keys = {canonical_key(make_instance(n=12, seed=seed, coefficient_span=9))
            for seed in range(1000, 1020)}
    report["G8_canonical_key"] = {
        "pass": invariance_checks == 100 and witness_checks == 100
                and len(keys) == 20,
        "invariance_checks": invariance_checks,
        "transformed_witness_checks": witness_checks,
        "unrelated_distinct": len(keys),
        "unrelated_attempts": 20,
        "transformations": (
            "arbitrary row relabelling, arbitrary column relabelling, their "
            "composition, tensor-mode transposition, and transposition "
            "composed with relabelling"
        ),
    }

    size_measurements = [
        _answer_metrics(make_instance(seed=seed, **ship_params)["answer"])
        for seed in range(1000)
    ]
    chars, tokens, elements = max(size_measurements, key=lambda item: item[0])
    intended_ops = 3 * (inst["n"] - 1) + 1
    ev = G9_EVIDENCE
    hinted_pass = ev["hinted_verdict"] == "hardened"
    within_caps = chars <= 2000 and elements <= 256 and intended_ops <= 300
    hp_attempts = ev["hinted"]["attempts"]
    pp_attempts = ev["placebo"]["attempts"]
    hinted_rate = ev["hinted"]["solved"] / hp_attempts if hp_attempts else 0.0
    placebo_rate = ev["placebo"]["solved"] / pp_attempts if pp_attempts else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": hinted_pass and within_caps,
        "arms": {
            "bare": dict(ev["bare"]),
            "hinted": dict(ev["hinted"]),
            "placebo": dict(ev["placebo"]),
        },
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": ev["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "answer_size_sample_count": len(size_measurements),
        "intended_route_operations": intended_ops,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship_params)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
