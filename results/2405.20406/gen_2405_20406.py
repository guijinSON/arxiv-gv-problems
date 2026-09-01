"""Verified generators for isomorphisms of finite pentagon-equation solutions.

The paper proves that a group G (the matched-pair case with the other factor
trivial) gives the bijective pentagon solution s_G(x, y) = (xy, y), and that
isomorphisms of these solutions are precisely group isomorphisms.  This module
uses class-2 exponent-p groups represented succinctly by alternating tensors.

Only the Python standard library is used.  All randomness is local to a
``random.Random(seed)`` instance.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re
from functools import lru_cache


DIFFICULTY = {
    "demo": {"n": 3, "m": 2, "p": 3},
    "standard": {"n": 6, "m": 4, "p": 3},
    "hard": {"n": 8, "m": 4, "p": 3},
}

SHIPPING_DIFFICULTY = "standard"

NOTES = r"""
Definition 2.2 fixes the witness: an isomorphism f must be a bijection satisfying
(f x f) s = t (f x f).  Theorem 4.1 constructs an irretractable solution from a
matched pair, and with A trivial its formula is s_G(x,y)=(xy,y).  Proposition
5.6 and Corollary 6.6 identify solution isomorphisms with matched-pair
isomorphisms, hence with group isomorphisms in this special case.

The generated groups are odd-prime, class-2 exponent-p groups whose commutator
map is a surjective, radical-free alternating tensor.  Tensor isometry (and the
equivalent class-2 p-group isomorphism case) has no known polynomial-time
algorithm.  Both displayed tensors are drawn from exactly the same distribution:
the second is obtained by independent uniform changes of basis sampled before
the first tensor is drawn.

Easy regimes deliberately avoided: evaluating the paper's Theorem 4.1 formula
is closed-form; Proposition 6.2 gives an explicit isomorphism between different
extension permutations; and Section 7 shows that involutive finite solutions
collapse to elementary abelian 2-groups with trivial actions.  We use p=3, no
extension set, nonabelian groups, and dimensions of both tensor modes that grow.

The outlier attack matches coordinates by sparsity fingerprints, the greedy
attack hill-climbs over coordinate swaps, and random restart samples uniformly
from both general linear groups.  Dense independent basis changes and balanced
random tensors defeat all three in selftest.  canonical_key uses a basis-invariant
recursive signature of the projective lattice of the alternating matrix space;
full tensor canonicalization is itself an intractable isomorphism problem, so the
key is intentionally documented as a strong invariant rather than a complete
canonical form.
""".strip()


# ---------------------------------------------------------------------------
# Finite-field matrix and tensor helpers


def _rank(matrix: list[list[int]] | tuple[tuple[int, ...], ...], p: int) -> int:
    if not matrix:
        return 0
    a = [[int(x) % p for x in row] for row in matrix]
    rows, cols = len(a), len(a[0])
    rank = 0
    for col in range(cols):
        pivot = next((r for r in range(rank, rows) if a[r][col]), None)
        if pivot is None:
            continue
        a[rank], a[pivot] = a[pivot], a[rank]
        inv = pow(a[rank][col], -1, p)
        a[rank] = [(x * inv) % p for x in a[rank]]
        for r in range(rows):
            if r != rank and a[r][col]:
                q = a[r][col]
                a[r] = [(a[r][c] - q * a[rank][c]) % p for c in range(cols)]
        rank += 1
        if rank == rows:
            break
    return rank


def _inverse(matrix: list[list[int]], p: int) -> list[list[int]] | None:
    n = len(matrix)
    if n == 0 or any(len(row) != n for row in matrix):
        return None
    a = [
        [int(x) % p for x in row] + [1 if i == j else 0 for j in range(n)]
        for i, row in enumerate(matrix)
    ]
    for col in range(n):
        pivot = next((r for r in range(col, n) if a[r][col]), None)
        if pivot is None:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        inv = pow(a[col][col], -1, p)
        a[col] = [(x * inv) % p for x in a[col]]
        for r in range(n):
            if r != col and a[r][col]:
                q = a[r][col]
                a[r] = [(a[r][c] - q * a[col][c]) % p for c in range(2 * n)]
    return [row[n:] for row in a]


def _identity(n: int) -> list[list[int]]:
    return [[1 if i == j else 0 for j in range(n)] for i in range(n)]


def _transpose(a: list[list[int]]) -> list[list[int]]:
    return [list(row) for row in zip(*a)]


def _matmul(a: list[list[int]], b: list[list[int]], p: int) -> list[list[int]]:
    if not a:
        return []
    bt = list(zip(*b))
    return [[sum(x * y for x, y in zip(row, col)) % p for col in bt] for row in a]


def _random_gl(n: int, p: int, rng: random.Random) -> list[list[int]]:
    """Uniformly sample GL(n,p) by rejection from all n-by-n matrices."""
    while True:
        a = [[rng.randrange(p) for _ in range(n)] for _ in range(n)]
        if _rank(a, p) == n:
            return a


def _gl_size(n: int, p: int) -> int:
    result = 1
    for i in range(n):
        result *= p**n - p**i
    return result


def _alternating_matrix(n: int, p: int, rng: random.Random) -> list[list[int]]:
    a = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            x = rng.randrange(p)
            a[i][j] = x
            a[j][i] = (-x) % p
    return a


def _component_rank(tensor: list[list[list[int]]], p: int) -> int:
    n = len(tensor[0])
    rows = []
    for matrix in tensor:
        rows.append([matrix[i][j] for i in range(n) for j in range(i + 1, n)])
    return _rank(rows, p)


def _common_radical_dimension(tensor: list[list[list[int]]], p: int) -> int:
    n = len(tensor[0])
    stacked = [row for matrix in tensor for row in matrix]
    return n - _rank(stacked, p)


def _random_tensor(n: int, m: int, p: int, rng: random.Random) -> list[list[list[int]]]:
    """Sample a surjective alternating tensor with zero common radical."""
    while True:
        tensor = [_alternating_matrix(n, p, rng) for _ in range(m)]
        if _component_rank(tensor, p) != m:
            continue
        if _common_radical_dimension(tensor, p) != 0:
            continue
        return tensor


def _linear_combination(
    tensor: list[list[list[int]]], coefficients: list[int] | tuple[int, ...], p: int
) -> list[list[int]]:
    n = len(tensor[0])
    return [
        [sum(coefficients[k] * tensor[k][i][j] for k in range(len(tensor))) % p
         for j in range(n)]
        for i in range(n)
    ]


def _transform_tensor(
    tensor: list[list[list[int]]], r: list[list[int]], s: list[list[int]], p: int
) -> list[list[list[int]]]:
    """Return T' with T'(R u,R v)=S T(u,v)."""
    rinv = _inverse(r, p)
    if rinv is None:
        raise ValueError("R must be invertible")
    rinvt = _transpose(rinv)
    transformed = []
    for k in range(len(s)):
        combined = _linear_combination(tensor, s[k], p)
        transformed.append(_matmul(_matmul(rinvt, combined, p), rinv, p))
    return transformed


def _tensor_equation_holds(
    source: list[list[list[int]]],
    target: list[list[list[int]]],
    pmat: list[list[int]],
    qmat: list[list[int]],
    p: int,
) -> bool:
    """Check P^T target[k] P = sum_l Q[k,l] source[l]."""
    n, m = len(pmat), len(qmat)
    for k in range(m):
        for i in range(n):
            for j in range(i + 1, n):
                left = 0
                for a in range(n):
                    pai = pmat[a][i]
                    if not pai:
                        continue
                    for b in range(n):
                        left += pai * target[k][a][b] * pmat[b][j]
                right = sum(qmat[k][ell] * source[ell][i][j] for ell in range(m))
                if (left - right) % p:
                    return False
    return True


def _equation_score(inst: dict, pmat: list[list[int]], qmat: list[list[int]]) -> int:
    source, target, p = inst["source"], inst["target"], inst["p"]
    n, m = inst["n"], inst["m"]
    score = 0
    for k in range(m):
        for i in range(n):
            for j in range(i + 1, n):
                left = sum(
                    pmat[a][i] * target[k][a][b] * pmat[b][j]
                    for a in range(n) for b in range(n)
                )
                right = sum(qmat[k][ell] * source[ell][i][j] for ell in range(m))
                score += (left - right) % p == 0
    return score


# ---------------------------------------------------------------------------
# Public generator interface


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Plant basis changes first, then construct two isomorphic PE solutions.

    ``n`` is the dimension of G/Z(G), ``m`` is the central/commutator
    dimension, and ``p`` is an odd prime.  Larger dimensions enlarge both the
    tensor and the two general-linear search factors.
    """
    m = int(params.pop("m", max(2, n // 2)))
    p = int(params.pop("p", 3))
    if params:
        raise TypeError(f"unknown parameters: {', '.join(sorted(params))}")
    if not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if m < 2 or m > n * (n - 1) // 2:
        raise ValueError("m must lie between 2 and n(n-1)/2")
    if p < 3 or any(p % q == 0 for q in range(2, math.isqrt(p) + 1)):
        raise ValueError("p must be an odd prime")

    rng = random.Random(seed)

    # The answer is sampled before any instance tensor, as required for inverse
    # generation.  Rejection sampling makes both matrices uniform in GL.
    planted_p = _random_gl(n, p, rng)
    planted_q = _random_gl(m, p, rng)

    source = _random_tensor(n, m, p, rng)
    target = _transform_tensor(source, planted_p, planted_q, p)

    return {
        "n": n,
        "m": m,
        "p": p,
        "source": source,
        "target": target,
        "answer": {"P": planted_p, "Q": planted_q},
    }


def render(inst: dict) -> str:
    """Render a complete, unambiguous tensor-isomorphism witness problem."""
    n, m, p = inst["n"], inst["m"], inst["p"]

    def show_tensor(name: str, tensor: list[list[list[int]]]) -> str:
        lines = [f"{name} has {m} component matrices, numbered 0 through {m - 1}:"]
        for k, matrix in enumerate(tensor):
            lines.append(f"{name}[{k}]")
            lines.extend(" ".join(map(str, row)) for row in matrix)
        return "\n".join(lines)

    example_p = json.dumps(_identity(n), separators=(",", ":"))
    example_q = json.dumps(_identity(m), separators=(",", ":"))
    example = '{"P":' + example_p + ',"Q":' + example_q + "}"
    return f"""Find an isomorphism between two finite set-theoretic solutions of the pentagon equation.

All arithmetic below is in the finite field F_{p}: add and multiply integers modulo {p}. Vectors are columns. Indices are 0-based.

An alternating bilinear map B: F_{p}^{n} x F_{p}^{n} -> F_{p}^{m} is encoded by {m} matrices B[k], with
    B(u,v)[k] = u^T B[k] v  (mod {p}).
The displayed matrices are alternating: their diagonal is zero and B[k][j][i] = -B[k][i][j] modulo {p}.

Such a B defines a finite group on pairs (u,z) in F_{p}^{n} x F_{p}^{m}; its multiplication is
    (u,z) * (v,w) = (u+v, z+w+inv2*B(u,v)),
where inv2={pow(2, -1, p)} is the inverse of 2 modulo {p}. This group defines the bijective pentagon map s_B(x,y)=(x*y,y). You do not need to list this exponentially large map.

The two tensors SOURCE and TARGET below define two such pentagon maps. Find two matrices:
  - P, exactly {n} by {n}, invertible over F_{p};
  - Q, exactly {m} by {m}, invertible over F_{p}.
They must satisfy, for every k=0,...,{m - 1},
    P^T TARGET[k] P = sum over ell=0,...,{m - 1} of Q[k][ell] SOURCE[ell]  (mod {p}).
Equivalently, F(u,z)=(P u,Q z) is an isomorphism of the two groups and of their pentagon maps. Other valid isomorphisms may exist; any one is accepted.

Matrix entries must be JSON integers in the inclusive range 0 through {p - 1}. Row order and column order matter. Repetitions are allowed as entries, but P and Q must each be invertible.

{show_tensor("SOURCE", inst["source"])}

{show_tensor("TARGET", inst["target"])}

Give your final answer inside <answer></answer> tags, as one JSON object with exactly the keys "P" and "Q", each containing a row-major array of rows.
Example of the exact syntax (the identity matrices illustrate syntax only and normally are not a solution):
<answer>{example}</answer>
Output nothing else inside the tags."""


_ANSWER_RE = re.compile(r"<answer(?:\s[^>]*)?>(.*?)</answer\s*>", re.I | re.S)


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON answer, tolerating prose and fences."""
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
        return json.loads(body)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid pair of tensor-isometry matrices; never use the plant."""
    n, m, p = inst["n"], inst["m"], inst["p"]
    if not isinstance(answer, dict) or set(answer) != {"P", "Q"}:
        return False, 'answer must be an object with exactly the keys "P" and "Q"'
    pmat, qmat = answer["P"], answer["Q"]
    if not isinstance(pmat, list) or len(pmat) != n:
        return False, f"P must have exactly {n} rows"
    if not isinstance(qmat, list) or len(qmat) != m:
        return False, f"Q must have exactly {m} rows"
    if any(not isinstance(row, list) or len(row) != n for row in pmat):
        return False, f"every row of P must have exactly {n} entries"
    if any(not isinstance(row, list) or len(row) != m for row in qmat):
        return False, f"every row of Q must have exactly {m} entries"
    entries = [x for row in pmat for x in row] + [x for row in qmat for x in row]
    if any(not isinstance(x, int) or isinstance(x, bool) for x in entries):
        return False, "all matrix entries must be JSON integers"
    if any(x < 0 or x >= p for x in entries):
        return False, f"all matrix entries must lie in the inclusive range 0..{p - 1}"
    if _rank(pmat, p) != n:
        return False, f"P is not invertible over F_{p}"
    if _rank(qmat, p) != m:
        return False, f"Q is not invertible over F_{p}"
    if not _tensor_equation_holds(inst["source"], inst["target"], pmat, qmat, p):
        return False, "the tensor isomorphism equation fails"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample GL(n,p) x GL(m,p), the structure-aware search space."""
    return {
        "P": _random_gl(inst["n"], inst["p"], rng),
        "Q": _random_gl(inst["m"], inst["p"], rng),
    }


def search_space(inst: dict) -> int | None:
    """Naive number of pairs of correctly shaped field-valued matrices."""
    return inst["p"] ** (inst["n"] ** 2 + inst["m"] ** 2)


def _all_gl(n: int, p: int):
    for flat in itertools.product(range(p), repeat=n * n):
        matrix = [list(flat[i * n:(i + 1) * n]) for i in range(n)]
        if _rank(matrix, p) == n:
            yield matrix


def enumerate_all(inst: dict) -> int | None:
    """Count exact witnesses only when at most 600,000 structured candidates exist."""
    n, m, p = inst["n"], inst["m"], inst["p"]
    structured = _gl_size(n, p) * _gl_size(m, p)
    if structured > 600_000 or p ** (n * n) > 100_000:
        return None
    qs = list(_all_gl(m, p))
    count = 0
    for pmat in _all_gl(n, p):
        for qmat in qs:
            count += _tensor_equation_holds(
                inst["source"], inst["target"], pmat, qmat, p
            )
    return count


# ---------------------------------------------------------------------------
# A strong cheap isomorphism invariant for canonical_key


@lru_cache(maxsize=None)
def _subspaces(ambient: int, dimension: int, p: int) -> tuple:
    """Enumerate every subspace once, by its unique RREF row basis."""
    if dimension == 0:
        return ((),)
    result = []
    for pivots in itertools.combinations(range(ambient), dimension):
        free = [
            (i, j)
            for i, pivot in enumerate(pivots)
            for j in range(pivot + 1, ambient)
            if j not in pivots
        ]
        for values in itertools.product(range(p), repeat=len(free)):
            rows = [[0] * ambient for _ in range(dimension)]
            for i, pivot in enumerate(pivots):
                rows[i][pivot] = 1
            for (i, j), value in zip(free, values):
                rows[i][j] = value
            result.append(tuple(tuple(row) for row in rows))
    return tuple(result)


def _rref_basis(rows: list[list[int]], p: int) -> tuple[tuple[int, ...], ...]:
    if not rows:
        return ()
    a = [[x % p for x in row] for row in rows]
    rank, cols = 0, len(a[0])
    for col in range(cols):
        pivot = next((r for r in range(rank, len(a)) if a[r][col]), None)
        if pivot is None:
            continue
        a[rank], a[pivot] = a[pivot], a[rank]
        inv = pow(a[rank][col], -1, p)
        a[rank] = [(x * inv) % p for x in a[rank]]
        for r in range(len(a)):
            if r != rank and a[r][col]:
                q = a[r][col]
                a[r] = [(a[r][c] - q * a[rank][c]) % p for c in range(cols)]
        rank += 1
        if rank == len(a):
            break
    return tuple(tuple(row) for row in a[:rank])


def _contained_hyperplanes(
    basis: tuple[tuple[int, ...], ...], p: int
) -> tuple[tuple[tuple[int, ...], ...], ...]:
    k, ambient = len(basis), len(basis[0])
    children = []
    for h in _subspaces(k, k - 1, p):
        rows = [
            [sum(h[i][a] * basis[a][j] for a in range(k)) % p
             for j in range(ambient)]
            for i in range(k - 1)
        ]
        children.append(_rref_basis(rows, p))
    return tuple(children)


def _space_signature(tensor: list[list[list[int]]], p: int) -> tuple:
    """Recursive projective-lattice signature, invariant under GL(n)xGL(m)."""
    m, n = len(tensor), len(tensor[0])
    signatures: dict[tuple[tuple[int, ...], ...], tuple] = {}
    for k in range(1, m + 1):
        spaces = _subspaces(m, k, p) if k < m else (
            tuple(tuple(1 if i == j else 0 for j in range(m)) for i in range(m)),
        )
        for basis in spaces:
            forms = [_linear_combination(tensor, row, p) for row in basis]
            radical = n - _rank([row for form in forms for row in form], p)
            if k == 1:
                signatures[basis] = (radical, _rank(forms[0], p))
            else:
                child_sigs = tuple(sorted(signatures[c] for c in _contained_hyperplanes(basis, p)))
                signatures[basis] = (radical, child_sigs)
    full = tuple(tuple(1 if i == j else 0 for j in range(m)) for i in range(m))
    return signatures[full]


def canonical_key(inst: dict) -> str:
    """Hash a structural tensor invariant, never the seed or rendered text."""
    payload = {
        "p": inst["p"],
        "n": inst["n"],
        "m": inst["m"],
        "projective_lattice_signature": _space_signature(inst["source"], inst["p"]),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params: dict) -> dict | None:
    """Grow both nontrivial tensor modes; this strictly enlarges the search group."""
    result = dict(params)
    result["n"] = int(result["n"]) + 2
    result["m"] = int(result.get("m", max(2, int(params["n"]) // 2))) + 1
    return result


# ---------------------------------------------------------------------------
# Relabellings and deliberately cheap adversaries used by selftest


def _copy_answer(answer: dict) -> dict:
    return {"P": [row[:] for row in answer["P"]], "Q": [row[:] for row in answer["Q"]]}


def _relabel_instance(
    inst: dict,
    r1: list[list[int]], s1: list[list[int]],
    r2: list[list[int]], s2: list[list[int]],
    swap: bool = False,
) -> dict:
    p = inst["p"]
    source = _transform_tensor(inst["source"], r1, s1, p)
    target = _transform_tensor(inst["target"], r2, s2, p)
    pnew = _matmul(_matmul(r2, inst["answer"]["P"], p), _inverse(r1, p), p)
    qnew = _matmul(_matmul(s2, inst["answer"]["Q"], p), _inverse(s1, p), p)
    if swap:
        source, target = target, source
        pnew = _inverse(pnew, p)
        qnew = _inverse(qnew, p)
    return {
        "n": inst["n"], "m": inst["m"], "p": p,
        "source": source, "target": target,
        "answer": {"P": pnew, "Q": qnew},
    }


def _permutation_from_sorted(source_order: list[int], target_order: list[int]) -> list[list[int]]:
    n = len(source_order)
    matrix = [[0] * n for _ in range(n)]
    for src, dst in zip(source_order, target_order):
        matrix[dst][src] = 1
    return matrix


def _outlier_attack(inst: dict) -> dict:
    """Match coordinate and component sparsity fingerprints as if they were labels."""
    n, m, p = inst["n"], inst["m"], inst["p"]

    def coord_key(tensor, i):
        return tuple(sorted(sum(tensor[k][i][j] != 0 for j in range(n)) for k in range(m)))

    def comp_key(tensor, k):
        nonzero = sum(tensor[k][i][j] != 0 for i in range(n) for j in range(i + 1, n))
        return (_rank(tensor[k], p), nonzero)

    source_coords = sorted(range(n), key=lambda i: (coord_key(inst["source"], i), i))
    target_coords = sorted(range(n), key=lambda i: (coord_key(inst["target"], i), i))
    source_components = sorted(range(m), key=lambda k: (comp_key(inst["source"], k), k))
    target_components = sorted(range(m), key=lambda k: (comp_key(inst["target"], k), k))
    return {
        "P": _permutation_from_sorted(source_coords, target_coords),
        "Q": _permutation_from_sorted(source_components, target_components),
    }


def _greedy_attack(inst: dict) -> dict:
    """Hill-climb from the identity using row swaps that improve exact entries."""
    pmat, qmat = _identity(inst["n"]), _identity(inst["m"])
    best = _equation_score(inst, pmat, qmat)
    for _ in range(2):
        choice = None
        for which, matrix in (("P", pmat), ("Q", qmat)):
            for i in range(len(matrix)):
                for j in range(i + 1, len(matrix)):
                    trial_p = [row[:] for row in pmat]
                    trial_q = [row[:] for row in qmat]
                    trial = trial_p if which == "P" else trial_q
                    trial[i], trial[j] = trial[j], trial[i]
                    score = _equation_score(inst, trial_p, trial_q)
                    if score > best:
                        best, choice = score, (trial_p, trial_q)
        if choice is None:
            break
        pmat, qmat = choice
    return {"P": pmat, "Q": qmat}


def _random_restart_attack(inst: dict, seed: int, restarts: int = 64) -> dict | None:
    rng = random.Random(seed)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


# ---------------------------------------------------------------------------
# Mandatory gates


def selftest() -> dict:
    report: dict[str, object] = {}

    # G1: every named preset, several seeds.
    g1_total, g1_failures = 0, []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_total += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "verified": g1_total, "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping_params)

    # G2: five qualitatively different corruptions and five different reasons.
    corruptions = {}
    dropped = _copy_answer(inst["answer"])
    dropped["P"].pop()
    corruptions["drop"] = dropped

    swapped = None
    for i in range(inst["n"]):
        for j in range(i + 1, inst["n"]):
            trial = _copy_answer(inst["answer"])
            trial["P"][i], trial["P"][j] = trial["P"][j], trial["P"][i]
            if not verify(inst, trial)[0]:
                swapped = trial
                break
        if swapped is not None:
            break
    corruptions["swap"] = swapped

    duplicate = _copy_answer(inst["answer"])
    duplicate["P"][1] = duplicate["P"][0][:]
    corruptions["duplicate"] = duplicate
    corruptions["empty"] = {}
    out_of_range = _copy_answer(inst["answer"])
    out_of_range["P"][0][0] = inst["p"]
    corruptions["out_of_range"] = out_of_range

    reasons = {name: verify(inst, bad)[1] for name, bad in corruptions.items()}
    g2_pass = all(not verify(inst, bad)[0] for bad in corruptions.values()) and len(set(reasons.values())) == 5
    report["G2_rejects_corruption"] = {
        "pass": g2_pass, "rejected": sum(not verify(inst, bad)[0] for bad in corruptions.values()),
        "distinct_reasons": len(set(reasons.values())), "reasons": reasons,
    }

    # G3: tagged JSON inside realistic prose and a markdown fence.
    encoded = json.dumps(inst["answer"], separators=(",", ":"))
    response = f"I reduced the equations over F_{inst['p']}.\n\n<answer>```json\n{encoded}\n```</answer>\n"
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0],
        "parsed_equal": parsed == inst["answer"],
    }

    # G4: empirical guessing from the full, obvious GL x GL constraint set.
    trials, hits = 200_000, 0
    guess_rng = random.Random(271828)
    for _ in range(trials):
        hits += verify(inst, random_candidate(inst, guess_rng))[0]
    report["G4_guess_resistance"] = {
        "pass": hits / trials < 1e-6,
        "hits": hits, "total": trials, "measured_probability": hits / trials,
        "prior": "uniform over GL(n,p) x GL(m,p)",
        "structured_space": _gl_size(inst["n"], inst["p"]) * _gl_size(inst["m"], inst["p"]),
        "naive_space": search_space(inst),
    }

    # G5: exact enumeration in the largest small case under the work cap.
    tiny = make_instance(n=3, m=2, p=3, seed=17)
    exact = enumerate_all(tiny)
    tiny_naive = search_space(tiny)
    tiny_structured = _gl_size(3, 3) * _gl_size(2, 3)
    report["G5_sparse"] = {
        "pass": exact is not None and exact / tiny_structured < 0.01,
        "valid_answers": exact,
        "naive_space": tiny_naive,
        "structured_space": tiny_structured,
        "valid_fraction_naive": None if exact is None else exact / tiny_naive,
        "valid_fraction_structured": None if exact is None else exact / tiny_structured,
    }

    # G6: attacks see only public instance data, never the planted answer.
    attack_seeds = list(range(800, 808))
    outlier_success = greedy_success = restart_success = 0
    for seed in attack_seeds:
        attacked = make_instance(seed=seed, **shipping_params)
        outlier_success += verify(attacked, _outlier_attack(attacked))[0]
        greedy_success += verify(attacked, _greedy_attack(attacked))[0]
        restart_success += _random_restart_attack(attacked, seed + 10_000) is not None
    report["G6_adversary_panel"] = {
        "pass": outlier_success == greedy_success == restart_success == 0,
        "seeds": len(attack_seeds),
        "outlier_sparsity_match": {"successes": outlier_success, "attempts": len(attack_seeds)},
        "greedy_coordinate_swaps": {"successes": greedy_success, "attempts": len(attack_seeds)},
        "random_restart_64": {"successes": restart_success, "attempts": len(attack_seeds)},
    }

    # G7: double both tensor modes and compare exact search-space sizes.
    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled_params["m"] *= 2
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst),
        "base_n_m": [inst["n"], inst["m"]],
        "doubled_n_m": [doubled["n"], doubled["m"]],
        "base_search_bits": search_space(inst).bit_length(),
        "doubled_search_bits": search_space(doubled).bit_length(),
        "doubled_verify_reason": doubled_reason,
    }

    # G8: all representation symmetries are GL changes in each tensor, plus
    # swapping source and target.  Dense, permutation, and composed maps are tested.
    invariance_checks = real_transform_checks = 0
    keys = []
    g8_errors = []
    for seed in range(20):
        original = make_instance(seed=50_000 + seed, **shipping_params)
        key = canonical_key(original)
        keys.append(key)
        relabel_rng = random.Random(90_000 + seed)
        n, m, p = original["n"], original["m"], original["p"]
        perm_n = list(range(n))
        perm_m = list(range(m))
        relabel_rng.shuffle(perm_n)
        relabel_rng.shuffle(perm_m)
        rn = [[1 if perm_n[j] == i else 0 for j in range(n)] for i in range(n)]
        sm = [[1 if perm_m[j] == i else 0 for j in range(m)] for i in range(m)]
        dense = (_random_gl(n, p, relabel_rng), _random_gl(m, p, relabel_rng),
                 _random_gl(n, p, relabel_rng), _random_gl(m, p, relabel_rng))
        transforms = [
            (rn, sm, _identity(n), _identity(m), False),
            (_identity(n), _identity(m), rn, sm, False),
            (*dense, False),
            (*dense, True),
        ]
        for transform in transforms:
            changed = _relabel_instance(original, *transform)
            invariance_checks += 1
            if canonical_key(changed) != key:
                g8_errors.append({"seed": seed, "kind": "key_changed"})
            real_transform_checks += 1
            if not verify(changed, changed["answer"])[0]:
                g8_errors.append({"seed": seed, "kind": "carried_answer_failed"})
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not g8_errors and distinct == 20,
        "invariance_checks": invariance_checks,
        "real_transform_checks": real_transform_checks,
        "unrelated_distinct": distinct,
        "unrelated_total": 20,
        "transformations": [
            "source coordinate/component permutations",
            "target coordinate/component permutations",
            "independent dense GL changes on both tensors",
            "dense changes composed with source-target swap",
        ],
        "errors": g8_errors,
        "key_caveat": "strong projective-lattice invariant, not complete tensor canonization",
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping_params)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
