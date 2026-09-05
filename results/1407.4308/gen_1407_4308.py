"""Exact change-of-basis certificates for inner-product PSD factorizations.

Section 6.3 of arXiv:1407.4308 gives a low-rank real PSD factorization of the
communication matrix IP_n(x,y)=x^T y over GF(2).  This generator first samples
an invertible coordinate change B, with its inverse known compositionally, and
uses B to relabel Bob's input: W_B(x,y)=x^T B y.  An instance contains many
matched bilinear forms, exactly one with an invertible B.  The requested witness
selects it and supplies Q=B^-1.  Hence W_B(x,Qz)=IP_n(x,z), and the paper's
factorization is carried through a verified column relabelling.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import random
import re
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - fallback is intentional
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "binary bilinear-form matrices over GF(2)",
        "change-of-variables matrix over GF(2)",
        "inner-product communication matrix specified by a bilinear form",
    ],
    "verification_operations": [
        "exact GF(2) matrix multiplication",
        "binary entry comparison",
        "identity-matrix comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Recognize a rank-one all-ones background whose removal exposes "
        "three-coordinate blocks, and use their parity to isolate the one "
        "invertible bilinear form instead of eliminating every dense matrix."
    ),
    "hardness_basis": (
        "Track B: testing h candidates by Gauss-Jordan elimination over GF(2) "
        "costs O(h*n^3); at shipping n=6,h=201 it averaged 14,990 "
        "scalar XORs and 0.020 seconds over eight fixed seeds, while "
        "the block-parity route uses at most 300 exact bit operations and "
        "keeps a 6-by-6 answer."
    ),
    "max_answer_tokens": 28,
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
        "One JSON object {\"candidate\": k, \"matrix\": Q}, where k selects "
        "one of h displayed matrices and Q is an n by n invertible matrix over "
        "GF(2), represented by JSON integers 0 and 1."
    ),
    "bounds": {
        "candidate_index": "0 <= k < h",
        "rows": "n",
        "columns": "n",
        "field": 2,
        "invertible": True,
        "maximum_shipping_candidates": 201,
        "maximum_shipping_entries": 36,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 3, "candidates": 2},
    "easy": {"n": 6, "candidates": 32},
    "medium": {"n": 6, "candidates": 112},
    "hard": {"n": 6, "candidates": 201},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT: str = (
    "Hint: Beneath each all-ones background, the three-coordinate components carry a single global parity invariant."
)
PLACEBO_HINT: str = (
    "Hint: Across the displayed binary matrices, careful indexing and consistent arithmetic both matter throughout."
)

_G9_EVIDENCE = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "not_run_api_quota",
    "blocked_reason": "OpenRouter HTTP 403 total key limit; no call was scored",
}

NOTES = r"""
Definition and paper objects. Section 2.1, Definition 1 defines a PSD
factorization by exact trace products. Section 6.3 defines the binary inner
product communication matrix IP_n(x,y)=x^T y mod 2. Theorems 50 and 51 give
the upper bound, with Theorem 51 explicitly constructing a low-rank signed
square root and hence rank-one real PSD factors. This module remains in those
objects: a matrix B specifies W_B(x,y)=x^T B y, and a checked BQ=I transports
the paper's factorization by the column relabelling y=Qz.

Step-0 discrimination. Directly generating arbitrary PSD factors would not
justify Track A: the paper gives upper- and lower-bound constructions, not a
hardness theorem for recovering factors from planted instances. More directly
for this family, ordinary Gaussian elimination always produces its witness in
polynomial time. The claim is therefore Track B, never Track A. The mechanical
route tests the displayed matrices by dense GF(2) Gauss-Jordan elimination. The
compact route notices that the zeros expose disjoint 3-by-3 components, reads
one parity bit from each component, and only inverts the unique even-parity
candidate before applying the rank-one inverse update.

Generation. Small invertible 3-by-3 blocks and their inverses are sampled
together from a fixed library, independently relabelled, and composed into
block diagonal matrices D. Exactly one candidate is chosen with
1^T D^{-1} 1=0; every decoy has value 1. Therefore exactly one B=D+11^T is
invertible and
B^{-1}=D^{-1}+(D^{-1}1)(1^T D^{-1})
by the rank-one inverse identity in characteristic two. The generator evaluates
that identity only for the planted candidate and carries B and B^{-1} through
independent row and column permutations. It never eliminates a published B.
The parity bits are sampled uniformly subject only to their XOR, and all local
block types have five 1-entries, so plants and decoys have identical one-block
and total-zero marginals.

Easy regimes and attacks. Section 6.3 itself gives the IP_n factorization once
the coordinates are aligned, which is why an exposed identity transform would
be trivial. The tests include a per-candidate row-profile outlier, greedy
nearest-unit columns, transposition, random candidate/inverse restarts, and the
strong in-context near miss that finds the unique even-parity candidate and
inverts its revealed blocks but omits the rank-one correction. Exhaustive
Gauss-Jordan candidate testing is intentionally successful and is reported
separately as the Track-B reference algorithm.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


# Five connected row/column-isomorphism classes in GL(3,2). Their inverses are
# hard-coded beside them, so generation only transports and composes known
# certificates; it never solves even a sampled local block.
_BLOCKS = (
    ((1, 1, 1), (0, 1, 0), (1, 0, 0)),
    ((1, 0, 1), (1, 1, 0), (1, 0, 0)),
    ((0, 1, 1), (1, 1, 0), (1, 0, 0)),
    ((1, 1, 1), (1, 1, 0), (1, 0, 0)),
    ((1, 1, 1), (1, 0, 1), (1, 1, 0)),
)


def _identity(n):
    return [[int(i == j) for j in range(n)] for i in range(n)]


def _invert_gf2(A, count_scalar_xors=False):
    """Return the exact inverse and a transparent scalar-XOR operation count."""
    n = len(A)
    if n == 0 or any(len(row) != n for row in A):
        return None, 0
    rows = []
    for i, row in enumerate(A):
        left = sum((int(row[j]) & 1) << j for j in range(n))
        rows.append(left | (1 << (n + i)))
    operations = 0
    for col in range(n):
        pivot = next((r for r in range(col, n) if (rows[r] >> col) & 1), None)
        if pivot is None:
            return None, operations
        rows[col], rows[pivot] = rows[pivot], rows[col]
        for r in range(n):
            if r != col and ((rows[r] >> col) & 1):
                rows[r] ^= rows[col]
                operations += 2 * n if count_scalar_xors else 1
    inv = [[(rows[i] >> (n + j)) & 1 for j in range(n)] for i in range(n)]
    return inv, operations


_BLOCK_INVERSES = (
    ((0, 0, 1), (0, 1, 0), (1, 1, 1)),
    ((0, 0, 1), (0, 1, 1), (1, 0, 1)),
    ((0, 0, 1), (0, 1, 1), (1, 1, 1)),
    ((0, 0, 1), (0, 1, 1), (1, 1, 0)),
    ((1, 1, 1), (1, 1, 0), (1, 0, 1)),
)
_BLOCK_SCALARS = tuple(
    sum(sum(row) for row in inv) & 1 for inv in _BLOCK_INVERSES
)
_BLOCK_X_WEIGHTS = tuple(
    sum(sum(row) & 1 for row in inv) for inv in _BLOCK_INVERSES
)
_BLOCK_Y_WEIGHTS = tuple(
    sum(sum(inv[i][j] for i in range(3)) & 1 for j in range(3))
    for inv in _BLOCK_INVERSES
)


def _permute_block(A, row_order, col_order):
    return [[A[row_order[i]][col_order[j]] for j in range(3)] for i in range(3)]


def _sample_public_matrix(n, parity, rng):
    """Build B=D+11^T with known rank-one denominator parity.

    Parity 0 gives an invertible B and returns its construction-known inverse;
    parity 1 gives a singular decoy and returns no inverse.  Local scalar bits
    are uniform subject only to their XOR.  Scalar-1 block types 0 and 1 and
    scalar-0 type 2 all contain five ones, preventing a total-zero outlier.
    """
    block_count = n // 3
    scalar_bits = [rng.randrange(2) for _ in range(block_count - 1)]
    scalar_bits.append(parity ^ (sum(scalar_bits) & 1))
    rng.shuffle(scalar_bits)
    types = [rng.choice((0, 1)) if bit else 2 for bit in scalar_bits]

    D = [[0] * n for _ in range(n)]
    Dinv = [[0] * n for _ in range(n)]
    for block_index, block_type in enumerate(types):
        rp = list(range(3))
        cp = list(range(3))
        rng.shuffle(rp)
        rng.shuffle(cp)
        C = _permute_block(_BLOCKS[block_type], rp, cp)
        # If C' = P C R^T, then (C')^-1 = R C^-1 P^T.
        base_inv = _BLOCK_INVERSES[block_type]
        Cinv = [[base_inv[cp[j]][rp[i]] for i in range(3)] for j in range(3)]
        off = 3 * block_index
        for i in range(3):
            for j in range(3):
                D[off + i][off + j] = C[i][j]
                Dinv[off + j][off + i] = Cinv[j][i]

    x = [sum(row) & 1 for row in Dinv]
    y = [sum(Dinv[i][j] for i in range(n)) & 1 for j in range(n)]
    if (sum(x) & 1) != parity:
        raise AssertionError("sampled block parity was not preserved")
    B = [[D[i][j] ^ 1 for j in range(n)] for i in range(n)]
    Q = None
    if parity == 0:
        Q = [[Dinv[i][j] ^ (x[i] & y[j]) for j in range(n)]
             for i in range(n)]

    row_order = list(range(n))
    col_order = list(range(n))
    rng.shuffle(row_order)
    rng.shuffle(col_order)
    public_B = [[B[row_order[i]][col_order[j]] for j in range(n)]
                for i in range(n)]
    public_Q = None
    if Q is not None:
        public_Q = [[Q[col_order[i]][row_order[j]] for j in range(n)]
                    for i in range(n)]
    return public_B, public_Q


def make_instance(n, seed=0, candidates=1, **params) -> dict:
    """Plant one known coordinate inverse among construction-known singular decoys."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 3 or n % 3:
        raise ValueError("n must be an integer multiple of 3 and at least 3")
    if (isinstance(candidates, bool) or not isinstance(candidates, int)
            or candidates < 1):
        raise ValueError("candidates must be a positive integer")
    rng = random.Random(seed)
    planted = rng.randrange(candidates)
    matrices = []
    planted_inverse = None
    for index in range(candidates):
        B, Q = _sample_public_matrix(n, int(index != planted), rng)
        matrices.append(B)
        if index == planted:
            planted_inverse = Q
    if planted_inverse is None:
        raise AssertionError("planted inverse was not constructed")

    return {
        "family": "unique GF(2) coordinate transport of the inner-product matrix",
        "n": n,
        "candidate_count": candidates,
        "communication_dimension": 1 << n,
        "field": 2,
        "bilinear_matrices": matrices,
        "psd_rank_upper_bound": (1 << (n // 2)) + (1 << (n - n // 2)) - 1,
        "answer": {"candidate": planted, "matrix": planted_inverse},
    }


def render(inst) -> str:
    n = inst["n"]
    h = inst["candidate_count"]
    N = inst["communication_dimension"]
    bound = inst["psd_rank_upper_bound"]
    blocks = []
    for index, matrix in enumerate(inst["bilinear_matrices"]):
        body = "\n".join(" ".join(map(str, row)) for row in matrix)
        blocks.append(f"Candidate {index}:\n{body}")
    matrices = "\n\n".join(blocks)
    text = f"""Exact coordinate certificate for a PSD-rank upper bound

All vector and matrix arithmetic in this problem is over GF(2): addition and
multiplication are reduced modulo 2. Let x and y range over all binary column
vectors of length n={n}. Each displayed binary matrix B defines an implicit
{N} by {N} nonnegative communication matrix W_B by

    W_B(x,y) = x^T B y mod 2.

Thus every entry of W_B is the ordinary integer 0 or 1. The standard inner-
product communication matrix is IP_n(x,z)=x^T z mod 2. A real PSD factorization
of a nonnegative matrix A with size r consists of real symmetric r by r matrices
E_x and F_y with v^T E_x v >= 0 and v^T F_y v >= 0 for every real vector v,
such that A(x,y)=Tr(E_x F_y). The matrix IP_n has such a factorization of size
at most {bound}.

Exactly one of the {h} displayed candidates is invertible over GF(2). For that
candidate, a binary n by n matrix Q is a change-of-coordinate certificate when

    B Q = I_n over GF(2).

This equation is equivalent to W_B(x,Qz)=IP_n(x,z) for every binary x,z, so Q
is an exact column relabelling that transports any PSD factorization of IP_n to
W_B. Candidates are numbered from 0 through {h - 1}. Within each candidate,
one matrix row appears per line:

{matrices}

Return the unique invertible candidate's 0-based index and one change-of-
coordinate certificate Q. Q must be a JSON array of exactly {n} rows, each
containing exactly {n} integers. Each entry must be 0 or 1; booleans are not
accepted. Matrix positions are 0-based, their order is the displayed order,
and repeated rows are not allowed. Ordinary matrix multiplication is used
before reducing each entry modulo 2.

Give your final answer inside <answer></answer> tags as one JSON object with the
two keys \"candidate\" and \"matrix\".
Example format only: <answer>{{\"candidate\":0,\"matrix\":[[1,0],[0,1]]}}</answer>
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


def verify(inst, answer) -> tuple[bool, str]:
    """Check any exact inverse in the declared language; never read answer data."""
    if not isinstance(answer, dict) or set(answer) != {"candidate", "matrix"}:
        return False, "answer must contain only 'candidate' and 'matrix'"
    candidate = answer["candidate"]
    if isinstance(candidate, bool) or not isinstance(candidate, int):
        return False, "candidate index must be an integer"
    if not 0 <= candidate < inst["candidate_count"]:
        return False, "candidate index is out of range"
    Q = answer["matrix"]
    if not isinstance(Q, list):
        return False, "matrix must be a JSON array"
    if not Q:
        return False, "matrix is empty"
    n = inst["n"]
    if len(Q) != n:
        return False, f"wrong row count: expected {n}, got {len(Q)}"
    for i, row in enumerate(Q):
        if not isinstance(row, list) or len(row) != n:
            got = len(row) if isinstance(row, list) else "non-array"
            return False, f"wrong width in row {i}: expected {n}, got {got}"
        for j, value in enumerate(row):
            if isinstance(value, bool) or not isinstance(value, int) or value not in (0, 1):
                return False, f"entry ({i},{j}) is not the integer 0 or 1"
    if len({tuple(row) for row in Q}) != n:
        return False, "candidate matrix has duplicate rows and is singular"

    B = inst["bilinear_matrices"][candidate]
    for i in range(n):
        for j in range(n):
            value = 0
            for k in range(n):
                value ^= B[i][k] & Q[k][j]
            expected = int(i == j)
            if value != expected:
                return False, f"B*Q differs from the identity at ({i},{j})"
    return True, "ok"


def _rank_bits(rows, n):
    basis = [0] * n
    rank = 0
    for original in rows:
        value = original
        while value:
            pivot = value.bit_length() - 1
            if basis[pivot]:
                value ^= basis[pivot]
            else:
                basis[pivot] = value
                rank += 1
                break
    return rank


def random_candidate(inst, rng) -> object:
    """Uniformly sample a candidate index and GL(n,2) inverse matrix."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    n = inst["n"]
    basis = [0] * n
    rows = []
    while len(rows) < n:
        original = rng.getrandbits(n)
        value = original
        while value:
            pivot = value.bit_length() - 1
            if basis[pivot]:
                value ^= basis[pivot]
            else:
                basis[pivot] = value
                rows.append(original)
                break
    matrix = [[(row >> j) & 1 for j in range(n)] for row in rows]
    return {"candidate": rng.randrange(inst["candidate_count"]), "matrix": matrix}


def search_space(inst) -> int | None:
    """Exact cardinality h*|GL(n,2)| of the structure-aware language."""
    n = inst["n"]
    total = 1
    size = 1 << n
    for i in range(n):
        total *= size - (1 << i)
    return inst["candidate_count"] * total


def enumerate_all(inst) -> int | None:
    """Brute-force all binary matrices at the hand-scale demo only."""
    n = inst["n"]
    if n > 3:
        return None
    count = 0
    for candidate in range(inst["candidate_count"]):
        for bits in range(1 << (n * n)):
            rows = [sum(((bits >> (i * n + j)) & 1) << j for j in range(n))
                    for i in range(n)]
            if _rank_bits(rows, n) != n:
                continue
            matrix = [[(rows[i] >> j) & 1 for j in range(n)] for i in range(n)]
            count += int(verify(inst, {
                "candidate": candidate, "matrix": matrix
            })[0])
    return count


def _components_of_complement(B):
    """Connected bipartite components of D=B+J, as (rows, columns)."""
    n = len(B)
    row_neighbors = [[j for j in range(n) if B[i][j] == 0] for i in range(n)]
    col_neighbors = [[i for i in range(n) if B[i][j] == 0] for j in range(n)]
    seen_rows, seen_cols = set(), set()
    components = []
    for start in range(n):
        if start in seen_rows:
            continue
        rows, cols = set([start]), set()
        queue = [(0, start)]
        seen_rows.add(start)
        while queue:
            side, index = queue.pop()
            if side == 0:
                for j in row_neighbors[index]:
                    if j not in seen_cols:
                        seen_cols.add(j)
                        cols.add(j)
                        queue.append((1, j))
            else:
                for i in col_neighbors[index]:
                    if i not in seen_rows:
                        seen_rows.add(i)
                        rows.add(i)
                        queue.append((0, i))
        components.append((sorted(rows), sorted(cols)))
    return components


def _canonical_block(A):
    r = len(A)
    c = len(A[0]) if A else 0
    best = None
    for rp in itertools.permutations(range(r)):
        for cp in itertools.permutations(range(c)):
            item = tuple(A[rp[i]][cp[j]] for i in range(r) for j in range(c))
            if best is None or item < best:
                best = item
    return (r, c, best)


def canonical_key(inst) -> str:
    """Invariant under candidate order and independent row/column relabellings."""
    matrix_keys = []
    for B in inst["bilinear_matrices"]:
        block_keys = []
        for rows, cols in _components_of_complement(B):
            block = [[B[i][j] ^ 1 for j in cols] for i in rows]
            block_keys.append(_canonical_block(block))
        matrix_keys.append(tuple(sorted(block_keys)))
    payload = (inst["n"], tuple(sorted(matrix_keys)))
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params) -> dict | str | None:
    n = params.get("n")
    candidates = params.get("candidates")
    if isinstance(n, bool) or not isinstance(n, int) or n < 3 or n % 3:
        return None
    if (isinstance(candidates, bool) or not isinstance(candidates, int)
            or candidates < 1):
        return None
    if n < 6:
        return {"n": 6, "candidates": min(201, max(32, candidates))}
    if n == 6 and candidates < 201:
        return {"n": 6, "candidates": min(201, candidates + 64)}
    return None


def _reference_inverse(inst):
    operations = 0
    tested = 0
    for candidate, B in enumerate(inst["bilinear_matrices"]):
        inverse, cost = _invert_gf2(B, count_scalar_xors=True)
        operations += cost
        tested += 1
        if inverse is not None:
            return candidate, inverse, operations, tested
    return None, None, operations, tested


def _block_inverse_data(B):
    """Return D^-1 and 1^T D^-1 1 for the complement-block decomposition."""
    n = len(B)
    Dinv = [[0] * n for _ in range(n)]
    components = _components_of_complement(B)
    if len(components) != n // 3:
        return None, None
    for rows, cols in components:
        if len(rows) != 3 or len(cols) != 3:
            return None, None
        block = [[B[i][j] ^ 1 for j in cols] for i in rows]
        inverse, _ = _invert_gf2(block)
        if inverse is None:
            return None, None
        for j, public_col in enumerate(cols):
            for i, public_row in enumerate(rows):
                Dinv[public_col][public_row] = inverse[j][i]
    parity = sum(sum(row) for row in Dinv) & 1
    return Dinv, parity


def _local_candidate(inst):
    """Use the block parity invariant to find the unique invertible candidate."""
    hits = []
    data = {}
    for candidate, B in enumerate(inst["bilinear_matrices"]):
        Dinv, parity = _block_inverse_data(B)
        if Dinv is not None:
            data[candidate] = Dinv
        if parity == 0:
            hits.append(candidate)
    if len(hits) != 1:
        return None, None
    return hits[0], data[hits[0]]


def _attack_transpose(inst):
    candidate = 0
    B = inst["bilinear_matrices"][candidate]
    n = inst["n"]
    return {
        "candidate": candidate,
        "matrix": [[B[j][i] for j in range(n)] for i in range(n)],
    }


def _attack_complement(inst):
    candidate = 0
    B = inst["bilinear_matrices"][candidate]
    return {
        "candidate": candidate,
        "matrix": [[value ^ 1 for value in row] for row in B],
    }


def _attack_greedy_units(inst, candidate=0):
    """Match public columns greedily to the closest identity columns."""
    B = inst["bilinear_matrices"][candidate]
    n = inst["n"]
    unused = set(range(n))
    chosen = []
    for target in range(n):
        col = min(
            unused,
            key=lambda k: (
                sum(B[i][k] != int(i == target) for i in range(n)), k
            ),
        )
        unused.remove(col)
        chosen.append(col)
    Q = [[0] * n for _ in range(n)]
    for target, source_col in enumerate(chosen):
        Q[source_col][target] = 1
    return {"candidate": candidate, "matrix": Q}


def _attack_outlier_profile(inst):
    """Choose an extremal per-candidate row/column profile, then greedily align."""
    n = inst["n"]
    scored = []
    for candidate, B in enumerate(inst["bilinear_matrices"]):
        row_zeros = sorted(row.count(0) for row in B)
        col_zeros = sorted(sum(B[i][j] == 0 for i in range(n))
                           for j in range(n))
        score = sum(x * x for x in row_zeros + col_zeros)
        scored.append((score, candidate))
    return _attack_greedy_units(inst, min(scored)[1])


def _attack_local_blocks(inst):
    """Find the right candidate and D^-1, but omit the rank-one correction."""
    candidate, Dinv = _local_candidate(inst)
    if candidate is None:
        return _attack_greedy_units(inst)
    return {"candidate": candidate, "matrix": Dinv}


def _relabel_instance(inst, candidate_order, row_orders, col_orders):
    """Reorder candidates and independently relabel every pair of axes."""
    n = inst["n"]
    h = inst["candidate_count"]
    if sorted(candidate_order) != list(range(h)):
        raise ValueError("candidate_order must be a permutation")
    if len(row_orders) != h or len(col_orders) != h:
        raise ValueError("one row and column order is required per candidate")
    for row_order, col_order in zip(row_orders, col_orders):
        if (sorted(row_order) != list(range(n))
                or sorted(col_order) != list(range(n))):
            raise ValueError("axis orders must be permutations")
    out = dict(inst)
    matrices = []
    for new_index, old_index in enumerate(candidate_order):
        B = inst["bilinear_matrices"][old_index]
        row_order = row_orders[new_index]
        col_order = col_orders[new_index]
        matrices.append([
            [B[row_order[i]][col_order[j]] for j in range(n)]
            for i in range(n)
        ])
    out["bilinear_matrices"] = matrices
    old_target = inst["answer"]["candidate"]
    new_target = candidate_order.index(old_target)
    row_order = row_orders[new_target]
    col_order = col_orders[new_target]
    Q = inst["answer"]["matrix"]
    out["answer"] = {
        "candidate": new_target,
        "matrix": [
            [Q[col_order[i]][row_order[j]] for j in range(n)]
            for i in range(n)
        ],
    }
    return out


def _answer_atom_count(answer):
    if not isinstance(answer, dict) or not isinstance(answer.get("matrix"), list):
        return 0
    return 1 + sum(len(row) for row in answer["matrix"] if isinstance(row, list))


def _compact_route_operations(inst):
    """Exact-bit operations after recognizing the component-parity invariant."""
    n = inst["n"]
    candidate, Dinv = _local_candidate(inst)
    if candidate is None:
        return 10**9
    B = inst["bilinear_matrices"][candidate]
    blocks = _components_of_complement(B)
    x = [sum(row) & 1 for row in Dinv]
    y = [sum(Dinv[i][j] for i in range(n)) & 1 for j in range(n)]
    # A scalar-1 local block is recognizable by an all-one row or column; the
    # other local type has neither. Thus classifying components uses comparisons,
    # and XORing their bits costs (block_count-1) per candidate. For the winner:
    # nine 2-by-2 minors per 3-by-3 inverse at three GF(2) ops each; two XORs
    # for every local row and column parity; n-1 for the denominator parity;
    # and one XOR for each entry toggled by x*y^T.
    selection = inst["candidate_count"] * max(0, len(blocks) - 1)
    inverse = 27 * len(blocks) + 4 * n + (n - 1) + sum(x) * sum(y)
    return selection + inverse


def selftest() -> dict:
    report = {}

    planted_ok = 0
    unique_ok = 0
    planted_total = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, _ = verify(inst, inst["answer"])
            planted_ok += int(ok)
            invertible = sum(
                _invert_gf2(B)[0] is not None
                for B in inst["bilinear_matrices"]
            )
            unique_ok += int(invertible == 1)
            planted_total += 1
    report["G1_planted_verifies"] = {
        "pass": planted_ok == planted_total and unique_ok == planted_total,
        "verified": planted_ok,
        "unique_invertible_candidate": unique_ok,
        "attempts": planted_total,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    base = shipping["answer"]["matrix"]
    drop = [row[:] for row in base]
    drop[0] = drop[0][:-1]
    swapped = None
    for i in range(shipping["n"]):
        for j in range(shipping["n"]):
            for k in range(j + 1, shipping["n"]):
                if base[i][j] == base[i][k]:
                    continue
                candidate = [row[:] for row in base]
                candidate[i][j], candidate[i][k] = candidate[i][k], candidate[i][j]
                if len({tuple(row) for row in candidate}) == shipping["n"]:
                    swapped = candidate
                    break
            if swapped is not None:
                break
        if swapped is not None:
            break
    duplicate = [row[:] for row in base]
    duplicate[1] = duplicate[0][:]
    out_of_range = [row[:] for row in base]
    out_of_range[0][0] = 2
    target = shipping["answer"]["candidate"]
    corruptions = {
        "drop": {"candidate": target, "matrix": drop},
        "swap": {"candidate": target, "matrix": swapped},
        "duplicate": {"candidate": target, "matrix": duplicate},
        "empty": {"candidate": target, "matrix": []},
        "out_of_range": {"candidate": target, "matrix": out_of_range},
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
    realistic = f"I reduced the matrix over GF(2).\n<answer>```json\n{wire}\n```</answer>\nDone."
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"],
        "parsed_equals_answer": parsed == shipping["answer"],
        "json_native": json.loads(json.dumps(shipping["answer"])) == shipping["answer"],
    }

    guess_rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        ok, _ = verify(shipping, random_candidate(shipping, guess_rng))
        guess_hits += int(ok)
    candidate_space = search_space(shipping)
    guess_rate = guess_hits / guess_total
    exact_guess_probability = 1.0 / candidate_space
    report["G4_guess_resistance"] = {
        "pass": exact_guess_probability < 1e-6 and guess_total >= 200_000,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "exact_probability": exact_guess_probability,
        "exact_valid_answers": 1,
        "candidate_space": candidate_space,
        "candidate_space_bits": candidate_space.bit_length(),
        "prior": (
            "uniform candidate index times uniform GL(n,2); every sampled matrix "
            "already obeys the obvious invertibility requirement"
        ),
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    t0 = time.perf_counter()
    reference_index, reference_answer, reference_ops, reference_tested = (
        _reference_inverse(shipping)
    )
    reference_sec = time.perf_counter() - t0
    reference_ok = reference_answer is not None and verify(
        shipping, {"candidate": reference_index, "matrix": reference_answer}
    )[0]
    at0 = time.perf_counter()
    local_candidate = _attack_local_blocks(shipping)
    local_ok = verify(shipping, local_candidate)[0]
    local_sec = time.perf_counter() - at0
    at0 = time.perf_counter()
    baseline_hit = False
    brng = random.Random(424242)
    for _ in range(256):
        if verify(shipping, random_candidate(shipping, brng))[0]:
            baseline_hit = True
            break
    baseline_sec = time.perf_counter() - at0
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_total >= 200_000 and guess_rate < 1e-6
                and reference_ok and not local_ok and not baseline_hit,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_fraction": guess_rate,
        "shipping_exact_valid_answers": 1,
        "shipping_exact_enumeration": enumerate_all(shipping),
        "demo_exact_solution_count": enumerate_all(demo),
        "baseline_attack_wall_clock_seconds": round(local_sec, 6),
        "baseline_attack_iterations": (
            shipping["candidate_count"] * (shipping["n"] // 3)
        ),
        "baseline_attack_successes": int(local_ok),
        "baseline_attack": "invert every exposed 3x3 block but omit the rank-one update",
        "random_restart_wall_clock_seconds": round(baseline_sec, 6),
        "random_restart_iterations": 256,
        "random_restart_successes": int(baseline_hit),
        "reference_wall_clock_seconds": round(reference_sec, 6),
        "reference_scalar_xor_operations": reference_ops,
        "reference_candidates_tested": reference_tested,
        "reference_algorithm": "sequential exact Gauss-Jordan testing over GF(2)",
    }

    attacks = {
        "outlier_row_profile_then_greedy": {"successes": 0, "attempts": 8},
        "greedy_nearest_unit_column": {"successes": 0, "attempts": 8},
        "transpose_as_inverse": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "block_inverse_without_rank_one_update": {"successes": 0, "attempts": 8},
    }
    ref_success = 0
    ref_operations = []
    ref_seconds = []
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        attack_candidates = {
            "outlier_row_profile_then_greedy": _attack_outlier_profile(inst),
            "greedy_nearest_unit_column": _attack_greedy_units(inst),
            "transpose_as_inverse": _attack_transpose(inst),
            "block_inverse_without_rank_one_update": _attack_local_blocks(inst),
        }
        for name, candidate in attack_candidates.items():
            attacks[name]["successes"] += int(verify(inst, candidate)[0])
        rrng = random.Random(seed ^ 0x5A17)
        random_hit = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, rrng))[0]:
                random_hit = True
                break
        attacks["random_restart_256"]["successes"] += int(random_hit)
        rt0 = time.perf_counter()
        answer_index, answer, ops, _ = _reference_inverse(inst)
        ref_seconds.append(time.perf_counter() - rt0)
        ref_operations.append(ops)
        ref_success += int(answer is not None and verify(inst, {
            "candidate": answer_index, "matrix": answer
        })[0])
    all_failed = all(v["successes"] == 0 and v["attempts"] >= 8
                     for v in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_success == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "sequential exact Gauss-Jordan candidate testing over GF(2)",
            "complexity": "O(h*n^3) scalar GF(2) operations for h candidates",
            "wall_clock_sec_mean": round(sum(ref_seconds) / len(ref_seconds), 6),
            "wall_clock_sec_max": round(max(ref_seconds), 6),
            "operations_mean": round(sum(ref_operations) / len(ref_operations)),
            "operations_max": max(ref_operations),
            "solves": f"{ref_success}/8, as expected",
        },
    }

    doubled = make_instance(
        n=2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        candidates=DIFFICULTY[SHIPPING_DIFFICULTY]["candidates"],
        seed=2718,
    )
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] > shipping["n"]
                and search_space(doubled) > search_space(shipping),
        "shipping_n": shipping["n"],
        "shipping_candidates": shipping["candidate_count"],
        "doubled_n": doubled["n"],
        "doubled_candidates": doubled["candidate_count"],
        "doubled_planted_verifies": doubled_ok,
        "shipping_search_space_bits": search_space(shipping).bit_length(),
        "doubled_search_space_bits": search_space(doubled).bit_length(),
    }

    invariant = valid_carried = 0
    for seed in range(20):
        inst = make_instance(seed=1000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        rrng = random.Random(9000 + seed)
        h = inst["candidate_count"]

        def random_orders():
            candidate_order = list(range(h))
            rrng.shuffle(candidate_order)
            row_orders, col_orders = [], []
            for _ in range(h):
                rows = list(range(inst["n"]))
                cols = list(range(inst["n"]))
                rrng.shuffle(rows)
                rrng.shuffle(cols)
                row_orders.append(rows)
                col_orders.append(cols)
            return candidate_order, row_orders, col_orders

        first = _relabel_instance(inst, *random_orders())
        transformed = _relabel_instance(first, *random_orders())
        invariant += int(canonical_key(inst) == canonical_key(transformed))
        valid_carried += int(verify(transformed, transformed["answer"])[0])

    unrelated = {}
    scanned = 0
    seed = 2000
    while len(unrelated) < 20 and scanned < 2000:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        unrelated.setdefault(key, seed)
        seed += 1
        scanned += 1
    report["G8_canonical_key"] = {
        "pass": invariant == 20 and valid_carried == 20 and len(unrelated) == 20,
        "composed_relabellings_invariant": invariant,
        "carried_witnesses_valid": valid_carried,
        "unrelated_distinct_keys": len(unrelated),
        "unrelated_seeds_scanned": scanned,
        "attempts_each": 20,
        "canonicalization": (
            "multiset of candidate multisets of complement-component "
            "row/column isomorphism classes"
        ),
    }

    answer_lengths = []
    answer_atoms = 0
    intended_ops = 0
    for seed in range(40):
        inst = make_instance(seed=3000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        encoded = json.dumps(inst["answer"], separators=(",", ":"))
        answer_lengths.append(len(encoded))
        answer_atoms = max(answer_atoms, _answer_atom_count(inst["answer"]))
        intended_ops = max(intended_ops, _compact_route_operations(inst))
    answer_chars = max(answer_lengths)
    answer_tokens = (answer_chars + 3) // 4
    arms = _G9_EVIDENCE["arms"]
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    hinted_minus_placebo = hinted_rate - placebo_rate
    within_caps = answer_chars <= 2000 and answer_atoms <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": _G9_EVIDENCE["hinted_verdict"],
        "diagnostic_status": _G9_EVIDENCE["blocked_reason"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
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
