"""Verified signed tensor-degeneracy witnesses from arXiv:2604.17061.

The generator uses the paper's zero-slice reduction from projective bilinear
feasibility to real 3-tensor degeneracy.  It samples the sign witness first,
builds every slice in its bilinear annihilator, and composes sparse signed path
Laplacians into a certificate that is cheap to verify exactly.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import re
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - documented fallback
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "rational 3-tensor given by integer matrix slices",
        "three nonzero real projective vectors represented by primitive bounded integer coordinates",
    ],
    "verification_operations": [
        "exact integer bilinear contraction",
        "exact integer matrix-vector multiplication",
        "zero comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3.3, Theorem 3.5 (zero-slice singular pencil), and Section 4, "
        "Proposition 4.2 (matrix slices are exactly tensor contractions)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Pair near-negative tensor slices so that their sparse residuals assemble "
        "a signed path Laplacian; its off-diagonal signs propagate the two hidden "
        "vectors, whereas blind aggregation performs thousands of scalar additions."
    ),
    "hardness_basis": (
        "Track B: on the generated Theorem 3.5/Proposition 4.2 zero-slice regime, "
        "the aggregate-slices decoder runs in O(m*n^2) exact arithmetic and at "
        "shipping n=16 uses 16,700 integer operations in about 0.0007 seconds; "
        "the near-negative cancellation route uses 188 exact operations after "
        "pairing, but identifying the pairs from 65 dense slices is not mechanical "
        "in a no-tool context."
    ),
    "max_answer_tokens": 61,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}


DIFFICULTY = {
    "demo": {"n": 3, "pair_factor": 1, "coefficient_bound": 4},
    "easy": {"n": 14, "pair_factor": 1, "coefficient_bound": 9},
    "medium": {"n": 16, "pair_factor": 2, "coefficient_bound": 9},
    "hard": {"n": 18, "pair_factor": 3, "coefficient_bound": 9},
}
SHIPPING_DIFFICULTY = "medium"


STRUCTURAL_HINT = (
    "Pair the nonzero slices as near-negatives: their sparse residuals form a "
    "signed path Laplacian whose off-diagonals propagate x and y."
)
PLACEBO_HINT = (
    "Check the slice indices and vector coordinates carefully: the exact signs "
    "and the stated normalization both matter in the final answer."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object with primitive nonzero integer vectors x,y of length n, "
        "coordinates in [-3,3], and first nonzero coordinate positive (the unique "
        "wire representative of each bounded rational projective point), plus a "
        "0/1 vector z of length m whose sole 1 selects the unique zero slice."
    ),
    "bounds": {
        "x_length": "n",
        "y_length": "n",
        "x_y_coordinate_absolute_bound": 3,
        "x_y_primitive_gcd": 1,
        "projective_sign_normalization": "first nonzero coordinate positive",
        "z_length": "number of slices m",
        "z_hamming_weight": 1,
        "z_support": "the unique all-zero slice",
    },
}


NOTES = r"""
Definition 4.1 fixes real 3-tensor degeneracy as three simultaneous modewise
contractions at nonzero x,y,z.  Theorem 3.5 fixes the useful zero-slice pencil
regime: A_0=0 and z=e_0 turn projective bilinear feasibility into singular
pencil feasibility.  Proposition 4.2 proves that stacking those matrices as
slices gives exactly the tensor contractions, and Theorem 4.3 proves the
unrestricted decision problem is existential-real complete.

The paper does not prove average-case hardness for inverse-planted tensors, so
that worst-case theorem is not used as a Track A claim.  This generator is
Track B.  Its certificate-producing construction samples normalized sign
vectors x,y first.  Each dense random matrix R is drawn in the exact bilinear
annihilator x^T R y=0.  It is paired with -R+D, where D is either zero or one
signed edge-Laplacian piece.  The pieces compose to
diag(x)*L_path*diag(y), whose right and left kernels contain y and x.  A unique
zero slice supplies z exactly as in Theorem 3.5.

An efficient distribution-specific algorithm exists and is disclosed: add all
slices, then read the signs recursively from the two off-diagonals of the
signed path Laplacian.  It costs O(m*n^2) scalar additions.  The compressed
route pairs near-negative slices and adds only their four-entry residuals
before the same sign propagation.  Dense values are sampled symmetrically and
all slice order is shuffled.  The attack panel tests slice-norm outliers,
single-slice greedy signs, randomized coordinate descent, and simple by-hand
ansatzes; the successful aggregate decoder is reported separately as Track
B's reference algorithm.
""".strip()


# Populated from independently produced harden.py transcripts before shipping.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _sign(rng):
    return 1 if rng.randrange(2) else -1


def _zero_matrix(n):
    return [[0 for _ in range(n)] for _ in range(n)]


def _edge_piece(x, y, edge):
    """diag(x)*(e_i-e_j)(e_i-e_j)^T*diag(y), j=i+1."""
    n = len(x)
    i, j = edge, edge + 1
    out = _zero_matrix(n)
    out[i][i] = x[i] * y[i]
    out[i][j] = -x[i] * y[j]
    out[j][i] = -x[j] * y[i]
    out[j][j] = x[j] * y[j]
    return out


def _dense_annihilator(x, y, bound, rng):
    """An exchangeable dense integer matrix R with x^T R y exactly zero."""
    n = len(x)
    count = n * n
    values = []
    for _ in range(count // 2):
        value = rng.randint(1, bound)
        values.extend((value, -value))
    if count % 2:
        values.append(0)
    rng.shuffle(values)
    out = _zero_matrix(n)
    for position, value in enumerate(values):
        i, j = divmod(position, n)
        out[i][j] = x[i] * y[j] * value
    return out


def _matrix_add(a, b):
    return [[u + v for u, v in zip(ra, rb)] for ra, rb in zip(a, b)]


def _matrix_neg_plus(a, d):
    return [[-u + v for u, v in zip(ra, rd)] for ra, rd in zip(a, d)]


def make_instance(n, seed=0, **params):
    """Inverse-generate a rational tensor and its exact degeneracy witness."""
    pair_factor = params.pop("pair_factor", 1)
    coefficient_bound = params.pop("coefficient_bound", 9)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if (isinstance(pair_factor, bool) or not isinstance(pair_factor, int)
            or pair_factor < 1):
        raise ValueError("pair_factor must be a positive integer")
    if (isinstance(coefficient_bound, bool)
            or not isinstance(coefficient_bound, int)
            or coefficient_bound < 2):
        raise ValueError("coefficient_bound must be an integer at least 2")

    rng = random.Random(seed)
    x = [1] + [_sign(rng) for _ in range(n - 1)]
    y = [1] + [_sign(rng) for _ in range(n - 1)]
    pair_count = max(n - 1, n * pair_factor)

    residuals = [_edge_piece(x, y, i) for i in range(n - 1)]
    residuals.extend(_zero_matrix(n) for _ in range(pair_count - (n - 1)))
    rng.shuffle(residuals)

    slices = []
    for residual in residuals:
        r = _dense_annihilator(x, y, coefficient_bound, rng)
        slices.append(r)
        slices.append(_matrix_neg_plus(r, residual))
    slices.append(_zero_matrix(n))
    rng.shuffle(slices)

    zero_positions = [k for k, a in enumerate(slices)
                      if all(value == 0 for row in a for value in row)]
    if len(zero_positions) != 1:
        raise AssertionError("construction did not create exactly one zero slice")
    z = [0] * len(slices)
    z[zero_positions[0]] = 1
    answer = {"x": x, "y": y, "z": z}
    return {
        "family": "signed real 3-tensor degeneracy",
        "n": n,
        "pair_factor": pair_factor,
        "coefficient_bound": coefficient_bound,
        "slices": slices,
        "answer": answer,
    }


def _compact_json(value):
    return json.dumps(value, separators=(",", ":"))


def render(inst):
    n = inst["n"]
    slices = inst["slices"]
    m = len(slices)
    rows = []
    for k, matrix in enumerate(slices):
        rows.append(f"slice {k}:")
        rows.extend("  " + " ".join(str(v) for v in row) for row in matrix)

    example = {
        "x": [1] * n,
        "y": [1] * n,
        "z": [1] + [0] * (m - 1),
    }
    hint = ""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        hint = "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        hint = "\n\nHint: " + PLACEBO_HINT

    return f"""Find an exact degeneracy witness for a rational 3-tensor.

The tensor T has shape {n} x {n} x {m}.  Its third-mode slices A_k are the
integer matrices printed below, with k=0,...,{m - 1}.  For column vectors x,y
of length {n} and z of length {m}, define M(z)=sum_k z[k] A_k.

A tensor-degeneracy witness is a triple of nonzero vectors satisfying all three
conditions:

1. x^T A_k y = 0 for every k=0,...,{m - 1};
2. M(z) y is the all-zero length-{n} vector;
3. M(z)^T x is the all-zero length-{n} vector.

For this bounded exact task, x and y must be primitive nonzero integer vectors:
every entry is in the inclusive interval [-3,3], the greatest common divisor of
their absolute entries is 1, and the first nonzero entry is positive.  This is
the unique wire representative of each allowed rational projective point.  The
vector z must have entries only in {{0,1}} and its unique 1 must select the unique
all-zero printed slice.  Indices are 0-based.  Matrix rows and vector coordinates
are in the displayed order; no repeats or omitted coordinates are allowed.

Tensor slices:
{chr(10).join(rows)}{hint}

Give your final answer inside <answer></answer> tags as one JSON object with
exactly the keys \"x\", \"y\", and \"z\", whose values are the three arrays.
Example syntax only: <answer>{_compact_json(example)}</answer>
The real arrays must have lengths {n}, {n}, and {m}. Output nothing else inside
the tags."""


def parse_answer(text):
    """Parse the last delimited JSON answer, tolerating prose and fences."""
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
        return json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _shape_reason(answer, inst):
    if not isinstance(answer, dict):
        return "answer must be a JSON object"
    if not answer:
        return "answer object is empty"
    keys = set(answer)
    if keys != {"x", "y", "z"}:
        missing = sorted({"x", "y", "z"} - keys)
        extra = sorted(keys - {"x", "y", "z"})
        return f"answer keys are wrong (missing={missing}, extra={extra})"
    x, y, z = answer["x"], answer["y"], answer["z"]
    if not all(isinstance(v, list) for v in (x, y, z)):
        return "x, y, and z must each be JSON arrays"
    n, m = inst["n"], len(inst["slices"])
    if len(x) != n:
        return f"x has wrong length: expected {n}, got {len(x)}"
    if len(y) != n:
        return f"y has wrong length: expected {n}, got {len(y)}"
    if len(z) != m:
        return f"z has wrong length: expected {m}, got {len(z)}"
    return None


def verify(inst, answer):
    """Verify any bounded witness using only the public tensor and candidate."""
    reason = _shape_reason(answer, inst)
    if reason:
        return False, reason
    x, y, z = answer["x"], answer["y"], answer["z"]
    for name, vector in (("x", x), ("y", y)):
        for i, value in enumerate(vector):
            if isinstance(value, bool) or not isinstance(value, int):
                return False, f"{name}[{i}] is not an integer"
            if not -3 <= value <= 3:
                return False, f"{name}[{i}] is outside the inclusive bound [-3,3]"
        if not any(vector):
            return False, f"{name} is the zero vector"
        common = 0
        for value in vector:
            common = math.gcd(common, abs(value))
        if common != 1:
            return False, f"{name} is not primitive (coordinate gcd is {common})"
        first = next(value for value in vector if value)
        if first < 0:
            return False, f"{name}'s first nonzero coordinate must be positive"
    for i, value in enumerate(z):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"z[{i}] is not an integer"
        if value not in (0, 1):
            return False, f"z[{i}] is outside the allowed binary alphabet"
    if sum(z) != 1:
        return False, "z must contain exactly one 1"
    selected = z.index(1)
    a_selected = inst["slices"][selected]
    if any(value != 0 for row in a_selected for value in row):
        return False, "z does not select the unique all-zero slice"

    n = inst["n"]
    for k, matrix in enumerate(inst["slices"]):
        contraction = 0
        for i in range(n):
            row_dot = 0
            for j in range(n):
                row_dot += matrix[i][j] * y[j]
            contraction += x[i] * row_dot
        if contraction != 0:
            return False, f"first contraction is nonzero at slice {k}"

    # Keep the two remaining tensor conditions explicit, even though the
    # certificate language makes M(z) the selected zero slice.
    my = [0] * n
    mtx = [0] * n
    for k, weight in enumerate(z):
        if not weight:
            continue
        matrix = inst["slices"][k]
        for i in range(n):
            for j in range(n):
                my[i] += weight * matrix[i][j] * y[j]
                mtx[j] += weight * matrix[i][j] * x[i]
    if any(my):
        return False, "second contraction M(z)y is nonzero"
    if any(mtx):
        return False, "third contraction M(z)^T x is nonzero"
    return True, "ok"


def _zero_slice_vector(inst):
    positions = [k for k, matrix in enumerate(inst["slices"])
                 if all(value == 0 for row in matrix for value in row)]
    if len(positions) != 1:
        return None
    z = [0] * len(inst["slices"])
    z[positions[0]] = 1
    return z


def random_candidate(inst, rng):
    """Uniformly sample bounded primitive projective vectors and infer z."""
    if not hasattr(rng, "randrange"):
        raise TypeError("rng must provide randrange")
    n = inst["n"]

    def vector():
        while True:
            values = [rng.randrange(-3, 4) for _ in range(n)]
            common = 0
            for value in values:
                common = math.gcd(common, abs(value))
            if common != 1:
                continue
            first = next(value for value in values if value)
            if first < 0:
                values = [-value for value in values]
            return values

    x, y = vector(), vector()
    z = _zero_slice_vector(inst)
    return {"x": x, "y": y, "z": z or []}


def search_space(inst):
    # For B=3, Mobius inversion gives primitive nonzero vectors in [-B,B]^n:
    # (7^n-1) - (3^n-1) - (3^n-1).  Quotient by v ~ -v.
    n = inst["n"]
    projective_vectors = (7 ** n - 2 * 3 ** n + 1) // 2
    return projective_vectors * projective_vectors


def enumerate_all(inst):
    space = search_space(inst)
    if space > 1_000_000:
        return None
    n = inst["n"]
    z = _zero_slice_vector(inst)
    count = 0
    vectors = []
    total_raw = 7 ** n
    for code in range(total_raw):
        value = code
        vector = []
        for _ in range(n):
            vector.append(value % 7 - 3)
            value //= 7
        common = 0
        for entry in vector:
            common = math.gcd(common, abs(entry))
        if common != 1:
            continue
        if next(entry for entry in vector if entry) < 0:
            continue
        vectors.append(vector)
    for x in vectors:
        for y in vectors:
            if verify(inst, {"x": x, "y": y, "z": z})[0]:
                count += 1
    return count


def _aggregate_slices(inst):
    n = inst["n"]
    total = _zero_matrix(n)
    operations = 0
    for matrix in inst["slices"]:
        for i in range(n):
            for j in range(n):
                total[i][j] += matrix[i][j]
                operations += 1
    return total, operations


def _reference_algorithm(inst):
    """Polynomial decoder for this distribution; deliberately not an attack."""
    started = time.perf_counter()
    q, operations = _aggregate_slices(inst)
    n = inst["n"]
    x = [1] * n
    y = [1] * n
    for i in range(n - 1):
        y[i + 1] = -q[i][i + 1] * x[i]
        x[i + 1] = -q[i + 1][i] * y[i]
        operations += 4
    answer = {"x": x, "y": y, "z": _zero_slice_vector(inst)}
    elapsed = time.perf_counter() - started
    return answer, operations, elapsed


def _candidate_from_scores(inst, row_scores, col_scores):
    x = [1] + [1 if value >= 0 else -1 for value in row_scores[1:]]
    y = [1] + [1 if value >= 0 else -1 for value in col_scores[1:]]
    return {"x": x, "y": y, "z": _zero_slice_vector(inst)}


def _attack_outlier_slice(inst, rng=None):
    nonzero = [a for a in inst["slices"] if any(v for row in a for v in row)]
    matrix = min(nonzero, key=lambda a: sum(abs(v) for row in a for v in row))
    row_scores = [sum(row) for row in matrix]
    col_scores = [sum(matrix[i][j] for i in range(inst["n"]))
                  for j in range(inst["n"])]
    return _candidate_from_scores(inst, row_scores, col_scores)


def _energy(inst, x, y):
    score = 0
    n = inst["n"]
    for matrix in inst["slices"]:
        value = 0
        for i in range(n):
            value += x[i] * sum(matrix[i][j] * y[j] for j in range(n))
        score += value * value
    return score


def _attack_greedy_first_slice(inst, rng=None):
    n = inst["n"]
    matrix = next(a for a in inst["slices"] if any(v for row in a for v in row))
    x, y = [1] * n, [1] * n
    for _ in range(2):
        for i in range(1, n):
            choices = []
            for sign in (-1, 1):
                x[i] = sign
                value = sum(x[r] * sum(matrix[r][c] * y[c] for c in range(n))
                            for r in range(n))
                choices.append((abs(value), sign))
            x[i] = min(choices)[1]
        for j in range(1, n):
            choices = []
            for sign in (-1, 1):
                y[j] = sign
                value = sum(x[r] * sum(matrix[r][c] * y[c] for c in range(n))
                            for r in range(n))
                choices.append((abs(value), sign))
            y[j] = min(choices)[1]
    return {"x": x, "y": y, "z": _zero_slice_vector(inst)}


def _local_descent(inst, x, y, sweeps=2):
    n = inst["n"]
    best = _energy(inst, x, y)
    for _ in range(sweeps):
        improved = False
        for vector, index in ((x, i) for i in range(1, n)):
            vector[index] *= -1
            score = _energy(inst, x, y)
            if score < best:
                best, improved = score, True
            else:
                vector[index] *= -1
        for vector, index in ((y, j) for j in range(1, n)):
            vector[index] *= -1
            score = _energy(inst, x, y)
            if score < best:
                best, improved = score, True
            else:
                vector[index] *= -1
        if best == 0 or not improved:
            break
    return best


def _attack_random_restart(inst, rng, restarts=64):
    n = inst["n"]
    for _ in range(restarts):
        x = [1] + [_sign(rng) for _ in range(n - 1)]
        y = [1] + [_sign(rng) for _ in range(n - 1)]
        if _local_descent(inst, x, y, sweeps=2) == 0:
            return {"x": x, "y": y, "z": _zero_slice_vector(inst)}
    return {"x": [1] * n, "y": [1] * n, "z": _zero_slice_vector(inst)}


def _attack_by_hand_ansatz(inst, rng=None):
    n = inst["n"]
    z = _zero_slice_vector(inst)
    trials = []
    trials.append(([1] * n, [1] * n))
    trials.append(([1 if i % 2 == 0 else -1 for i in range(n)],
                   [1 if i % 2 == 0 else -1 for i in range(n)]))
    first = next(a for a in inst["slices"] if any(v for row in a for v in row))
    diag = [1] + [1 if first[i][i] >= 0 else -1 for i in range(1, n)]
    trials.append((diag, diag[:]))
    trials.append((diag, [1] + [-v for v in diag[1:]]))
    for x, y in trials:
        answer = {"x": x, "y": y, "z": z}
        if verify(inst, answer)[0]:
            return answer
    return {"x": trials[0][0], "y": trials[0][1], "z": z}


def canonical_key(inst):
    """Cheap invariant under monomial bases and nonzero slice rescaling."""
    normalized_slices = []
    for matrix in inst["slices"]:
        values = [abs(value) for row in matrix for value in row]
        common = 0
        for value in values:
            common = math.gcd(common, value)
        common = common or 1
        normalized_slices.append(sorted(value // common for value in values))
    normalized_slices.sort()
    payload = {
        "shape": [inst["n"], inst["n"], len(inst["slices"])],
        "normalized_slice_coefficients": normalized_slices,
    }
    return hashlib.sha256(_compact_json(payload).encode()).hexdigest()


def _carry_answer(inst, x, y, z):
    out = copy.deepcopy(inst)
    out["answer"] = {"x": x, "y": y, "z": z}
    return out


def _permute_slices(inst, permutation):
    x, y, z = (inst["answer"][k][:] for k in ("x", "y", "z"))
    out = copy.deepcopy(inst)
    out["slices"] = [copy.deepcopy(inst["slices"][old]) for old in permutation]
    out["answer"] = {"x": x, "y": y, "z": [z[old] for old in permutation]}
    return out


def _permute_rows(inst, permutation):
    out = copy.deepcopy(inst)
    out["slices"] = [[[row[j] for j in range(inst["n"])]
                      for row in [matrix[old] for old in permutation]]
                     for matrix in inst["slices"]]
    x = [inst["answer"]["x"][old] for old in permutation]
    if x[0] == -1:
        x = [-v for v in x]
    out["answer"] = {"x": x, "y": inst["answer"]["y"][:],
                     "z": inst["answer"]["z"][:]}
    return out


def _permute_cols(inst, permutation):
    out = copy.deepcopy(inst)
    out["slices"] = [[[row[old] for old in permutation] for row in matrix]
                     for matrix in inst["slices"]]
    y = [inst["answer"]["y"][old] for old in permutation]
    if y[0] == -1:
        y = [-v for v in y]
    out["answer"] = {"x": inst["answer"]["x"][:], "y": y,
                     "z": inst["answer"]["z"][:]}
    return out


def _flip_rows(inst, signs):
    out = copy.deepcopy(inst)
    out["slices"] = [[[signs[i] * value for value in row]
                      for i, row in enumerate(matrix)] for matrix in inst["slices"]]
    x = [a * b for a, b in zip(signs, inst["answer"]["x"])]
    if x[0] == -1:
        x = [-v for v in x]
    out["answer"] = {"x": x, "y": inst["answer"]["y"][:],
                     "z": inst["answer"]["z"][:]}
    return out


def _flip_cols(inst, signs):
    out = copy.deepcopy(inst)
    out["slices"] = [[[signs[j] * value for j, value in enumerate(row)]
                      for row in matrix] for matrix in inst["slices"]]
    y = [a * b for a, b in zip(signs, inst["answer"]["y"])]
    if y[0] == -1:
        y = [-v for v in y]
    out["answer"] = {"x": inst["answer"]["x"][:], "y": y,
                     "z": inst["answer"]["z"][:]}
    return out


def _transpose_modes(inst):
    out = copy.deepcopy(inst)
    n = inst["n"]
    out["slices"] = [[[matrix[j][i] for j in range(n)] for i in range(n)]
                     for matrix in inst["slices"]]
    out["answer"] = {"x": inst["answer"]["y"][:],
                     "y": inst["answer"]["x"][:],
                     "z": inst["answer"]["z"][:]}
    return out


def _scale_tensor(inst, factor):
    if not isinstance(factor, int) or factor == 0:
        raise ValueError("scale factor must be a nonzero integer")
    out = copy.deepcopy(inst)
    out["slices"] = [[[factor * value for value in row] for row in matrix]
                     for matrix in inst["slices"]]
    return out


def _scale_slices(inst, factors):
    if (len(factors) != len(inst["slices"])
            or any(not isinstance(f, int) or f == 0 for f in factors)):
        raise ValueError("one nonzero integer factor is required per slice")
    out = copy.deepcopy(inst)
    out["slices"] = [
        [[factor * value for value in row] for row in matrix]
        for factor, matrix in zip(factors, inst["slices"])
    ]
    return out


def escalate(params):
    n = params.get("n")
    pair_factor = params.get("pair_factor", 1)
    bound = params.get("coefficient_bound", 9)
    if not isinstance(n, int):
        return None
    nxt = {"n": n + 2, "pair_factor": pair_factor + 1,
           "coefficient_bound": bound}
    pair_count = (nxt["n"] * nxt["pair_factor"])
    answer_elements = 2 * nxt["n"] + (2 * pair_count + 1)
    return nxt if answer_elements <= 256 else None


def _answer_metrics(inst):
    # Worst-case wire length over the declared bounded language: negative
    # one-digit coordinates are longest, and the leading +1 keeps gcd 1.
    n, m = inst["n"], len(inst["slices"])
    longest = {"x": [1] + [-3] * (n - 1),
               "y": [1] + [-3] * (n - 1),
               "z": [1] + [0] * (m - 1)}
    encoded = _compact_json(longest)
    elements = 2 * n + m
    return len(encoded), math.ceil(len(encoded) / 4), elements


def _run_attack_panel(params, seeds=range(8)):
    attacks = {
        "outlier_lowest_l1_slice": {"successes": 0, "attempts": 0,
                                     "wall_clock_sec": 0.0},
        "greedy_single_slice_signs": {"successes": 0, "attempts": 0,
                                       "wall_clock_sec": 0.0},
        "random_restart_64_coordinate_descent": {"successes": 0, "attempts": 0,
                                                  "wall_clock_sec": 0.0},
        "by_hand_constant_alternating_diagonal_ansatz": {
            "successes": 0, "attempts": 0, "wall_clock_sec": 0.0},
    }
    functions = [
        ("outlier_lowest_l1_slice", _attack_outlier_slice),
        ("greedy_single_slice_signs", _attack_greedy_first_slice),
        ("random_restart_64_coordinate_descent", _attack_random_restart),
        ("by_hand_constant_alternating_diagonal_ansatz", _attack_by_hand_ansatz),
    ]
    for seed in seeds:
        inst = make_instance(seed=seed, **params)
        for offset, (name, function) in enumerate(functions):
            rng = random.Random(10_000_019 * seed + offset + 17)
            started = time.perf_counter()
            answer = function(inst, rng)
            elapsed = time.perf_counter() - started
            ok = verify(inst, answer)[0]
            attacks[name]["successes"] += int(ok)
            attacks[name]["attempts"] += 1
            attacks[name]["wall_clock_sec"] += elapsed
    for result in attacks.values():
        result["wall_clock_sec"] = round(result["wall_clock_sec"], 6)
    return attacks


def selftest():
    report = {}

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            attempts += 1
            ok, why = verify(inst, inst["answer"])
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": why})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures}

    params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=73, **params)
    a = inst["answer"]
    corruptions = {}
    cases = {}
    cases["empty"] = {}
    dropped = copy.deepcopy(a)
    dropped["x"] = dropped["x"][:-1]
    cases["drop_coordinate"] = dropped
    swapped = copy.deepcopy(a)
    swapped["x"], swapped["z"] = swapped["z"], swapped["x"]
    cases["swap_vectors"] = swapped
    duplicate = copy.deepcopy(a)
    zero = duplicate["z"].index(1)
    duplicate["z"][(zero + 1) % len(duplicate["z"])] = 1
    cases["duplicate_one_in_z"] = duplicate
    out_of_range = copy.deepcopy(a)
    out_of_range["x"][1] = 4
    cases["out_of_range_sign"] = out_of_range
    wrong_norm = copy.deepcopy(a)
    wrong_norm["y"] = [-v for v in wrong_norm["y"]]
    cases["normalization_flip"] = wrong_norm
    for name, candidate in cases.items():
        ok, why = verify(inst, candidate)
        corruptions[name] = {"rejected": not ok, "reason": why}
    reasons = {value["reason"] for value in corruptions.values()}
    report["G2_rejects_corruption"] = {
        "pass": (all(v["rejected"] for v in corruptions.values())
                 and len(reasons) == len(corruptions)),
        "distinct_reasons": len(reasons), "cases": corruptions}

    body = _compact_json(inst["answer"])
    realistic = ("I used the three contraction identities.\n<answer>\n```json\n"
                 + body + "\n```\n</answer>\n")
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"],
        "parsed_equals_answer": parsed == inst["answer"],
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    rng = random.Random(0x260417061)
    samples = 200_000
    hits = 0
    started = time.perf_counter()
    for _ in range(samples):
        hits += int(verify(inst, random_candidate(inst, rng))[0])
    guess_time = time.perf_counter() - started
    density = hits / samples
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6,
        "hits": hits, "total": samples, "fraction": density,
        "candidate_space": search_space(inst),
        "candidate_space_bits": round(math.log2(search_space(inst)), 6),
        "wall_clock_sec": round(guess_time, 6),
    }

    reference_successes = 0
    reference_operations = []
    reference_times = []
    for seed in range(8):
        sample = make_instance(seed=seed, **params)
        decoded, operations, elapsed = _reference_algorithm(sample)
        reference_successes += int(verify(sample, decoded)[0])
        reference_operations.append(operations)
        reference_times.append(elapsed)
    attack_started = time.perf_counter()
    for restart_seed in range(64):
        _attack_random_restart(inst, random.Random(90_000 + restart_seed), restarts=1)
    attack_elapsed = time.perf_counter() - attack_started
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": (density < 1e-6 and reference_successes == 8
                 and isinstance(demo_count, int)),
        "shipping_solution_density": density,
        "shipping_sample_hits": hits,
        "shipping_sample_total": samples,
        "demo_exact_solution_count": demo_count,
        "baseline_attack_restarts": 64,
        "baseline_attack_wall_clock_sec": round(attack_elapsed, 6),
        "reference_successes": reference_successes,
        "reference_attempts": 8,
        "reference_operations_average": round(sum(reference_operations) / 8),
        "reference_wall_clock_sec_average": round(sum(reference_times) / 8, 6),
    }

    attacks = _run_attack_panel(params)
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 and result["attempts"] >= 8
                    for result in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "aggregate every slice, then decode the signed path Laplacian",
            "complexity": "O(m*n^2) exact integer additions plus O(n) sign propagation",
            "wall_clock_sec": round(sum(reference_times) / 8, 6),
            "operations": round(sum(reference_operations) / 8),
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    doubled = dict(params)
    doubled["n"] *= 2
    started = time.perf_counter()
    larger = make_instance(seed=19, **doubled)
    build_sec = time.perf_counter() - started
    large_ok, large_why = verify(larger, larger["answer"])
    report["G7_scales"] = {
        "pass": (large_ok and len(larger["slices"]) > len(inst["slices"])
                 and len(larger["slices"]) * larger["n"] ** 2
                 > len(inst["slices"]) * inst["n"] ** 2),
        "shipping_n": inst["n"], "doubled_n": larger["n"],
        "shipping_tensor_entries": len(inst["slices"]) * inst["n"] ** 2,
        "doubled_tensor_entries": len(larger["slices"]) * larger["n"] ** 2,
        "doubled_build_sec": round(build_sec, 6),
        "doubled_verify_reason": large_why,
    }

    invariant = 0
    carried = 0
    transformations = ["slice permutation", "row permutation", "column permutation",
                       "row signs", "column signs", "mode transpose",
                       "global integer scaling", "independent slice scaling",
                       "composition"]
    for seed in range(20):
        original = make_instance(seed=seed, **params)
        rng2 = random.Random(700_001 + seed)
        sp = list(range(len(original["slices"])))
        rp = list(range(original["n"]))
        cp = list(range(original["n"]))
        rng2.shuffle(sp)
        rng2.shuffle(rp)
        rng2.shuffle(cp)
        rs = [_sign(rng2) for _ in range(original["n"])]
        cs = [_sign(rng2) for _ in range(original["n"])]
        sf = [-3 if k % 2 else 2 for k in range(len(original["slices"]))]
        variants = [
            _permute_slices(original, sp),
            _permute_rows(original, rp),
            _permute_cols(original, cp),
            _flip_rows(original, rs),
            _flip_cols(original, cs),
            _transpose_modes(original),
            _scale_tensor(original, -3),
            _scale_slices(original, sf),
        ]
        composed = _transpose_modes(_flip_cols(_flip_rows(
            _permute_cols(_permute_rows(_permute_slices(original, sp), rp), cp),
            rs), cs))
        variants.append(composed)
        key = canonical_key(original)
        for variant in variants:
            invariant += int(canonical_key(variant) == key)
            carried += int(verify(variant, variant["answer"])[0])
    unrelated = [canonical_key(make_instance(seed=10_000 + seed, **params))
                 for seed in range(20)]
    expected = 20 * len(transformations)
    report["G8_canonical_key"] = {
        "pass": (invariant == expected and carried == expected
                 and len(set(unrelated)) == 20),
        "transformations": transformations,
        "invariant_relabellings": invariant,
        "invariance_attempts": expected,
        "real_transformations_verified": carried,
        "real_transformation_attempts": expected,
        "unrelated_distinct_keys": len(set(unrelated)),
        "unrelated_attempts": 20,
    }

    chars, tokens, elements = _answer_metrics(inst)
    pair_count = max(inst["n"] - 1, inst["n"] * inst["pair_factor"])
    intended_operations = 4 * pair_count + 4 * (inst["n"] - 1)
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    hinted_hardened = G9_ORACLE_RESULTS["hinted_verdict"] == "hardened"
    caps = chars <= 2000 and elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "caps_pass": caps,
    }

    PROBLEM_PROFILE["max_answer_tokens"] = tokens
    report["all_passed"] = all(
        value.get("pass", False) for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict))
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
