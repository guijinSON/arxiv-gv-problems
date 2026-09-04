"""Exact planted PRODSAT-core equation instances from arXiv:2404.18447.

The paper turns a product-state witness into one multiaffine polynomial equation
per rank-one projector (its Eq. (10)).  This module uses the same equations over
an odd prime field so that witnesses can be represented and checked exactly.

Only the Python standard library is used.  All pseudorandomness is local to a
``random.Random(seed)`` instance.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re


DIFFICULTY = {
    "demo": {"n": 5, "p": 7},
    "easy": {"n": 12, "p": 11},
    "medium": {"n": 20, "p": 17},
    "hard": {"n": 30, "p": 29},
}

SHIPPING_DIFFICULTY = "easy"

NOTES = r"""
Section 2.2, especially Eq. (10), fixes the witness and the exact constraint:
one projective single-qubit state per variable, contracted with every local
coefficient tensor.  Proposition 2.2 says a clause-covering dimer configuration
is the geometric condition supporting product solutions.  The generator uses
the finite N=M, k=3 setting studied in Section 6 and a connected 3-regular
factor graph, so the graph is its own nonempty 2-core and has a perfect matching.

The easy regime is explicit in Section 2.1 and Appendix A: when leaf removal
empties the core, the transfer-matrix reconstruction finds a product state in
O(N).  We exclude that regime by giving every variable and every constraint
degree exactly three.  Section 4 and Appendix C instead use Buchberger/Gröbner
basis machinery on the core; Appendix C records a doubly-exponential generic
degree bound, while the Introduction states that the actual algorithmic
complexity in the core regime is open.  Section 6 reports computations only at
moderate square sizes.  No polynomial-time or closed-form search method is
known for these planted sparse polynomial systems.

For exact automatic grading, complex amplitudes are replaced by projective
points over F_p.  The plant is sampled uniformly first.  Each constraint tensor
is then sampled uniformly from the seven-dimensional hyperplane annihilating
the planted local product vector; plants and alternative projective values use
the same uniform distribution, and no coefficient coordinate is reserved as a
marker.

The outlier attack chooses each coordinate by the number of locally compatible
partner pairs.  The greedy attack repeatedly maximizes the number of satisfied
incident constraints.  The random-restart attack runs min-conflicts from 64
uniform starts.  Square 3-regular cores and uniformly conditioned dense local
tensors defeat all three in selftest.  canonical_key is invariant under variable
and clause relabelling, tensor-axis reorderings, and independent GL(2,p) changes
of every local qubit basis, as well as nonzero rescaling of each equation.  It
uses graph trace/color signatures and the square
class of Cayley's 2x2x2 hyperdeterminant; it is a strong cheap invariant, not a
complete canonical form for colored tensor-network isomorphism.
""".strip()


# ---------------------------------------------------------------------------
# Finite-field and projective helpers


def _is_prime(p: int) -> bool:
    return p >= 2 and all(p % q for q in range(2, math.isqrt(p) + 1))


def _point(q: int, p: int) -> tuple[int, int]:
    """Canonical representative of q in P^1(F_p); q=p denotes infinity."""
    return (0, 1) if q == p else (1, q)


def _apply_gl2(a: list[list[int]], q: int, p: int) -> int:
    x, y = _point(q, p)
    u = (a[0][0] * x + a[0][1] * y) % p
    v = (a[1][0] * x + a[1][1] * y) % p
    if u:
        return v * pow(u, -1, p) % p
    return p


def _inverse_gl2(a: list[list[int]], p: int) -> list[list[int]]:
    det = (a[0][0] * a[1][1] - a[0][1] * a[1][0]) % p
    if not det:
        raise ValueError("matrix is singular")
    inv = pow(det, -1, p)
    return [
        [a[1][1] * inv % p, -a[0][1] * inv % p],
        [-a[1][0] * inv % p, a[0][0] * inv % p],
    ]


def _random_gl2(p: int, rng: random.Random) -> list[list[int]]:
    while True:
        a = [[rng.randrange(p), rng.randrange(p)],
             [rng.randrange(p), rng.randrange(p)]]
        if (a[0][0] * a[1][1] - a[0][1] * a[1][0]) % p:
            return a


def _feature(values: list[int] | tuple[int, int, int], p: int) -> list[int]:
    vecs = [_point(q, p) for q in values]
    return [
        vecs[0][(idx >> 2) & 1]
        * vecs[1][(idx >> 1) & 1]
        * vecs[2][idx & 1] % p
        for idx in range(8)
    ]


def _eval_coeff(coeff: list[int], values: list[int] | tuple[int, int, int], p: int) -> int:
    feats = _feature(values, p)
    return sum(c * x for c, x in zip(coeff, feats)) % p


def _sample_annihilator(local_answer: list[int], p: int, rng: random.Random) -> list[int]:
    """Uniform nonzero tensor from the hyperplane annihilating local_answer."""
    feat = _feature(local_answer, p)
    pivots = [i for i, x in enumerate(feat) if x]
    while True:
        pivot = pivots[rng.randrange(len(pivots))]
        coeff = [rng.randrange(p) for _ in range(8)]
        rest = sum(coeff[i] * feat[i] for i in range(8) if i != pivot) % p
        coeff[pivot] = -rest * pow(feat[pivot], -1, p) % p
        if any(coeff):
            return coeff


# ---------------------------------------------------------------------------
# Factor-graph generation


def _connected(scopes: list[list[int]], n: int) -> bool:
    variable_to_clauses = [[] for _ in range(n)]
    for ci, scope in enumerate(scopes):
        for v in scope:
            variable_to_clauses[v].append(ci)
    seen_v = {0}
    seen_c: set[int] = set()
    todo_v = [0]
    while todo_v:
        v = todo_v.pop()
        for ci in variable_to_clauses[v]:
            if ci in seen_c:
                continue
            seen_c.add(ci)
            for w in scopes[ci]:
                if w not in seen_v:
                    seen_v.add(w)
                    todo_v.append(w)
    return len(seen_v) == n and len(seen_c) == len(scopes)


def _sample_core_graph(n: int, rng: random.Random) -> list[list[int]]:
    """Connected 3-regular bipartite graph, sampled as three matchings."""
    for _ in range(20_000):
        matchings = []
        for _color in range(3):
            perm = list(range(n))
            rng.shuffle(perm)
            matchings.append(perm)
        scopes = []
        for ci in range(n):
            scope = [matchings[j][ci] for j in range(3)]
            if len(set(scope)) != 3:
                break
            rng.shuffle(scope)  # hide the sampled matching colors
            scopes.append(scope)
        if len(scopes) != n:
            continue
        if len({tuple(sorted(scope)) for scope in scopes}) != n:
            continue
        if _connected(scopes, n):
            return scopes
    raise RuntimeError("failed to sample a connected simple 3-regular factor graph")


# ---------------------------------------------------------------------------
# Public generator interface


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Sample a product-state answer first, then tensors annihilating it.

    ``n`` is both the number of projective variables and constraints.  ``p`` is
    an odd prime.  Larger n and p enlarge the square core and candidate space.
    """
    p = int(params.pop("p", 17))
    if params:
        raise TypeError(f"unknown parameters: {', '.join(sorted(params))}")
    if not isinstance(n, int) or isinstance(n, bool) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    if p < 3 or p % 2 == 0 or not _is_prime(p):
        raise ValueError("p must be an odd prime")

    rng = random.Random(seed)

    # G: the complete witness is sampled before any problem data.
    answer = [rng.randrange(p + 1) for _ in range(n)]
    scopes = _sample_core_graph(n, rng)
    clauses = []
    for scope in scopes:
        local = [answer[v] for v in scope]
        clauses.append({
            "vars": scope,
            "coeff": _sample_annihilator(local, p, rng),
        })

    return {"n": n, "m": n, "k": 3, "p": p,
            "clauses": clauses, "answer": answer}


def render(inst: dict) -> str:
    """Render a complete finite-field PRODSAT witness problem."""
    n, p = inst["n"], inst["p"]
    rows = []
    for ci, clause in enumerate(inst["clauses"]):
        scope = " ".join(map(str, clause["vars"]))
        coeff = " ".join(map(str, clause["coeff"]))
        rows.append(f"{ci}: vars {scope} ; coeff {coeff}")
    data = "\n".join(rows)
    example = "[" + ",".join("0" for _ in range(n)) + "]"
    return f"""Find a zero-energy product-state witness for this finite-field 3-QSAT core.

All arithmetic is in the prime field F_{p}: add and multiply modulo {p}. Indices are 0-based.

There are {n} variables q[0],...,q[{n - 1}]. Each variable is one projective point of P^1(F_{p}), encoded by exactly one integer in the inclusive range 0 through {p}:
  q in 0,...,{p - 1} represents the nonzero two-vector v(q)=(1,q);
  q={p} represents the point at infinity v(q)=(0,1).
Vectors differing by a nonzero scalar represent the same point, which is why this encoding is canonical.

Each constraint lists three DISTINCT variable indices (a,b,c), in that order, and eight coefficients C000,C001,C010,C011,C100,C101,C110,C111 in that exact binary order. It is satisfied when
  sum over i,j,k in {{0,1}} of Cijk * v(q[a])[i] * v(q[b])[j] * v(q[c])[k] = 0 (mod {p}).
All {n} constraints must be satisfied simultaneously. The factor graph is connected; every variable occurs in exactly three constraints and every constraint contains exactly three variables. Repeated q values are allowed, and the order of the {n} answer entries matters. Any satisfying witness is accepted.

Constraint data, one constraint per line:
{data}

Give your final answer inside <answer></answer> tags, as one JSON array of exactly {n} integers, in variable-index order.
Example of the exact syntax (illustrates syntax only and normally is not a solution):
<answer>{example}</answer>
Output nothing else inside the tags."""


_ANSWER_RE = re.compile(r"<answer(?:\s[^>]*)?>(.*?)</answer\s*>", re.I | re.S)


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON list, tolerating prose and fences."""
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
    except (json.JSONDecodeError, TypeError, ValueError):
        # A common otherwise-unambiguous model slip is to omit only the outer
        # JSON brackets.  Accept that comma-separated form as well.
        try:
            value = json.loads("[" + body + "]")
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
    return value if isinstance(value, list) else None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any satisfying projective assignment; never inspect the plant."""
    n, p = inst["n"], inst["p"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON array"
    if not answer:
        return False, "answer array must not be empty"
    if len(answer) < n:
        return False, f"answer has too few entries: expected {n}, got {len(answer)}"
    if len(answer) > n:
        return False, f"answer has too many entries: expected {n}, got {len(answer)}"
    if any(not isinstance(q, int) or isinstance(q, bool) for q in answer):
        return False, "every answer entry must be an integer"
    if any(q < 0 or q > p for q in answer):
        return False, f"every answer entry must lie in the inclusive range 0..{p}"
    for ci, clause in enumerate(inst["clauses"]):
        local = [answer[v] for v in clause["vars"]]
        residue = _eval_coeff(clause["coeff"], local, p)
        if residue:
            return False, f"constraint {ci} evaluates to nonzero residue {residue} modulo {p}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the statement-implied space (P^1(F_p))^n."""
    return [rng.randrange(inst["p"] + 1) for _ in range(inst["n"])]


def search_space(inst: dict) -> int | None:
    """Exact size of the obvious, structure-aware assignment space."""
    return (inst["p"] + 1) ** inst["n"]


def enumerate_all(inst: dict) -> int | None:
    """Count all witnesses when at most 250,000 assignments are present."""
    if search_space(inst) > 250_000:
        return None
    count = 0
    for candidate in itertools.product(range(inst["p"] + 1), repeat=inst["n"]):
        if verify(inst, list(candidate))[0]:
            count += 1
    return count


# ---------------------------------------------------------------------------
# Structural canonical key


def _hyperdet(coeff: list[int], p: int) -> int:
    """Cayley's hyperdeterminant of a 2x2x2 tensor."""
    a0, a1, a2, a3, a4, a5, a6, a7 = coeff
    value = (
        a0 * a0 * a7 * a7 + a1 * a1 * a6 * a6
        + a2 * a2 * a5 * a5 + a4 * a4 * a3 * a3
        - 2 * (a0 * a1 * a6 * a7 + a0 * a2 * a5 * a7
               + a0 * a4 * a3 * a7 + a1 * a2 * a5 * a6
               + a1 * a4 * a3 * a6 + a2 * a4 * a3 * a5)
        + 4 * (a0 * a3 * a5 * a6 + a1 * a2 * a4 * a7)
    )
    return value % p


def _tensor_color(coeff: list[int], p: int) -> int:
    delta = _hyperdet(coeff, p)
    if delta == 0:
        return 0
    return 1 if pow(delta, (p - 1) // 2, p) == 1 else 2


def _trace_powers(matrix: list[list[int]], count: int = 8) -> list[int]:
    n = len(matrix)
    power = [row[:] for row in matrix]
    traces = []
    for exponent in range(1, count + 1):
        traces.append(sum(power[i][i] for i in range(n)))
        if exponent == count:
            break
        power = [
            [sum(power[i][k] * matrix[k][j] for k in range(n))
             for j in range(n)]
            for i in range(n)
        ]
    return traces


def canonical_key(inst: dict) -> str:
    """A basis- and relabelling-invariant structural fingerprint.

    Full tensor-network canonization is not attempted.  The key combines exact
    incidence invariants with local GL(2,p)-invariant tensor colors.
    """
    n, m, p = inst["n"], inst["m"], inst["p"]
    scopes = [clause["vars"] for clause in inst["clauses"]]
    colors = [_tensor_color(clause["coeff"], p) for clause in inst["clauses"]]
    gram = [[len(set(scopes[i]) & set(scopes[j])) for j in range(m)] for i in range(m)]
    colored = [row[:] for row in gram]
    for i, color in enumerate(colors):
        colored[i][i] += 17 + 5 * color

    clause_profiles = []
    for i in range(m):
        profile = sorted((gram[i][j], colors[j]) for j in range(m) if j != i)
        clause_profiles.append((colors[i], profile))
    variable_profiles = []
    for v in range(n):
        incident = sorted(colors[i] for i, scope in enumerate(scopes) if v in scope)
        variable_profiles.append(incident)

    invariant = {
        "n": n,
        "m": m,
        "p": p,
        "degrees": sorted(sum(v in scope for scope in scopes) for v in range(n)),
        "colors": sorted(colors),
        "gram_traces": _trace_powers(gram),
        "colored_traces": _trace_powers(colored),
        "clause_profiles": sorted(clause_profiles),
        "variable_profiles": sorted(variable_profiles),
    }
    raw = json.dumps(invariant, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _next_prime(x: int) -> int:
    q = x + 1
    if q % 2 == 0:
        q += 1
    while not _is_prime(q):
        q += 2
    return q


def escalate(params: dict) -> dict | None:
    """Grow both the core and the projective alphabet."""
    n = int(params.get("n", 20))
    p = int(params.get("p", 17))
    return {"n": n + max(10, n // 3), "p": _next_prime(p + 6)}


# ---------------------------------------------------------------------------
# Cheap adversaries used by selftest


def _slice_rank(coeff: list[int], axis: int, q: int, p: int) -> int:
    vec = _point(q, p)
    other = [a for a in range(3) if a != axis]
    mat = [[0, 0], [0, 0]]
    for u in range(2):
        for v in range(2):
            total = 0
            for bit in range(2):
                bits = [0, 0, 0]
                bits[axis] = bit
                bits[other[0]] = u
                bits[other[1]] = v
                idx = (bits[0] << 2) | (bits[1] << 1) | bits[2]
                total += coeff[idx] * vec[bit]
            mat[u][v] = total % p
    if not any(mat[i][j] for i in range(2) for j in range(2)):
        return 0
    return 2 if (mat[0][0] * mat[1][1] - mat[0][1] * mat[1][0]) % p else 1


def _outlier_attack(inst: dict) -> list[int]:
    """Pick each value with the most locally compatible partner pairs."""
    n, p = inst["n"], inst["p"]
    incident = [[] for _ in range(n)]
    for ci, clause in enumerate(inst["clauses"]):
        for axis, v in enumerate(clause["vars"]):
            incident[v].append((ci, axis))
    candidate = []
    for v in range(n):
        best_q, best_score = 0, -1
        for q in range(p + 1):
            score = 0
            for ci, axis in incident[v]:
                rank = _slice_rank(inst["clauses"][ci]["coeff"], axis, q, p)
                score += ((p + 1) ** 2 if rank == 0 else
                          2 * p + 1 if rank == 1 else p + 1)
            if score > best_score:
                best_q, best_score = q, score
        candidate.append(best_q)
    return candidate


def _incidence(inst: dict) -> list[list[int]]:
    incident = [[] for _ in range(inst["n"])]
    for ci, clause in enumerate(inst["clauses"]):
        for v in clause["vars"]:
            incident[v].append(ci)
    return incident


def _clause_ok(inst: dict, ci: int, candidate: list[int]) -> bool:
    clause = inst["clauses"][ci]
    return _eval_coeff(clause["coeff"], [candidate[v] for v in clause["vars"]], inst["p"]) == 0


def _greedy_attack(inst: dict, start: list[int] | None = None, sweeps: int = 8) -> list[int]:
    p = inst["p"]
    candidate = list(start) if start is not None else [0] * inst["n"]
    incident = _incidence(inst)
    for _ in range(sweeps):
        changed = False
        for v in range(inst["n"]):
            scored = []
            old = candidate[v]
            for q in range(p + 1):
                candidate[v] = q
                scored.append(sum(_clause_ok(inst, ci, candidate) for ci in incident[v]))
            best = max(scored)
            choices = [q for q, score in enumerate(scored) if score == best]
            chosen = old if old in choices else choices[0]
            candidate[v] = chosen
            changed |= chosen != old
        if verify(inst, candidate)[0] or not changed:
            break
    return candidate


def _random_restart_attack(inst: dict, rng: random.Random, restarts: int = 64) -> list[int]:
    p, n = inst["p"], inst["n"]
    incident = _incidence(inst)
    best_candidate = [0] * n
    best_score = -1
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        for _step in range(10 * n):
            sat = [_clause_ok(inst, ci, candidate) for ci in range(inst["m"])]
            score = sum(sat)
            if score > best_score:
                best_score, best_candidate = score, list(candidate)
            if score == inst["m"]:
                return candidate
            unsat = [ci for ci, ok in enumerate(sat) if not ok]
            ci = unsat[rng.randrange(len(unsat))]
            moves = []
            move_score = -1
            for v in inst["clauses"][ci]["vars"]:
                old = candidate[v]
                for q in range(p + 1):
                    candidate[v] = q
                    local_score = sum(_clause_ok(inst, cj, candidate) for cj in incident[v])
                    if local_score > move_score:
                        move_score, moves = local_score, [(v, q)]
                    elif local_score == move_score:
                        moves.append((v, q))
                candidate[v] = old
            v, q = moves[rng.randrange(len(moves))]
            candidate[v] = q
    return best_candidate


# ---------------------------------------------------------------------------
# Relabellings and basis changes used to prove canonical-key invariance


def _permute_tensor_axes(coeff: list[int], axis_order: list[int]) -> list[int]:
    out = [0] * 8
    for new_idx in range(8):
        new_bits = [(new_idx >> 2) & 1, (new_idx >> 1) & 1, new_idx & 1]
        old_bits = [0, 0, 0]
        for new_axis, old_axis in enumerate(axis_order):
            old_bits[old_axis] = new_bits[new_axis]
        old_idx = (old_bits[0] << 2) | (old_bits[1] << 1) | old_bits[2]
        out[new_idx] = coeff[old_idx]
    return out


def _relabel_instance(
    inst: dict,
    variable_perm: list[int],
    clause_order: list[int],
    axis_orders: list[list[int]],
) -> dict:
    """variable_perm maps old variable ids to new ids."""
    transformed = []
    for old_ci, clause in enumerate(inst["clauses"]):
        axes = axis_orders[old_ci]
        transformed.append({
            "vars": [variable_perm[clause["vars"][old_axis]] for old_axis in axes],
            "coeff": _permute_tensor_axes(clause["coeff"], axes),
        })
    answer = [0] * inst["n"]
    for old_v, q in enumerate(inst["answer"]):
        answer[variable_perm[old_v]] = q
    return {
        "n": inst["n"], "m": inst["m"], "k": 3, "p": inst["p"],
        "clauses": [transformed[i] for i in clause_order], "answer": answer,
    }


def _basis_transform_tensor(
    coeff: list[int], inverses: list[list[list[int]]], p: int
) -> list[int]:
    out = [0] * 8
    for new_idx in range(8):
        a = (new_idx >> 2) & 1
        b = (new_idx >> 1) & 1
        c = new_idx & 1
        total = 0
        for i in range(2):
            for j in range(2):
                for k in range(2):
                    old_idx = (i << 2) | (j << 1) | k
                    total += (coeff[old_idx] * inverses[0][i][a]
                              * inverses[1][j][b] * inverses[2][k][c])
        out[new_idx] = total % p
    return out


def _basis_change_instance(inst: dict, matrices: list[list[list[int]]]) -> dict:
    p = inst["p"]
    inverses = [_inverse_gl2(a, p) for a in matrices]
    clauses = []
    for clause in inst["clauses"]:
        local_inv = [inverses[v] for v in clause["vars"]]
        clauses.append({
            "vars": list(clause["vars"]),
            "coeff": _basis_transform_tensor(clause["coeff"], local_inv, p),
        })
    answer = [_apply_gl2(matrices[v], q, p) for v, q in enumerate(inst["answer"])]
    return {"n": inst["n"], "m": inst["m"], "k": 3, "p": p,
            "clauses": clauses, "answer": answer}


def _scale_constraints(inst: dict, scales: list[int]) -> dict:
    """Multiply equations by nonzero field scalars without changing their zeros."""
    p = inst["p"]
    clauses = [
        {"vars": list(clause["vars"]),
         "coeff": [scale * x % p for x in clause["coeff"]]}
        for clause, scale in zip(inst["clauses"], scales)
    ]
    return {"n": inst["n"], "m": inst["m"], "k": 3, "p": p,
            "clauses": clauses, "answer": list(inst["answer"])}


# ---------------------------------------------------------------------------
# Mandatory gates


def selftest() -> dict:
    report: dict[str, object] = {}

    # G1: all presets, three independent seeds each.
    g1_failures = []
    verified = 0
    for name, params in DIFFICULTY.items():
        for seed in (0, 1, 97):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            verified += int(ok)
            if not ok:
                g1_failures.append({"preset": name, "seed": seed, "reason": why})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "verified": verified, "failures": g1_failures,
    }

    ship = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260429, **ship)
    planted = list(inst["answer"])

    # G2: five named corruption classes, with distinct diagnostics.
    swapped = None
    for i in range(inst["n"]):
        for j in range(i + 1, inst["n"]):
            if planted[i] != planted[j]:
                trial = list(planted)
                trial[i], trial[j] = trial[j], trial[i]
                if not verify(inst, trial)[0]:
                    swapped = trial
                    break
        if swapped is not None:
            break
    corruptions = {
        "drop": planted[:-1],
        "swap": swapped if swapped is not None else list(reversed(planted)),
        "duplicate": planted + [planted[-1]],
        "empty": [],
        "out_of_range": [inst["p"] + 1] + planted[1:],
    }
    reasons = {name: verify(inst, value)[1] for name, value in corruptions.items()}
    rejected = sum(not verify(inst, value)[0] for value in corruptions.values())
    report["G2_rejects_corruption"] = {
        "pass": rejected == 5 and len(set(reasons.values())) == 5,
        "rejected": rejected, "distinct_reasons": len(set(reasons.values())),
        "reasons": reasons,
    }

    # G3: prose and a Markdown fence around a tagged answer.
    response = ("I solved the modular constraints.\n\n<answer>\n```json\n"
                + json.dumps(planted) + "\n```\n</answer>\nThat is my final answer.")
    parsed = parse_answer(response)
    report["G3_round_trip"] = {"pass": parsed == planted, "parsed_equal": parsed == planted}

    # G4: uniform over every projective assignment, not over malformed noise.
    guess_rng = random.Random(0x240418447)
    total = 200_000
    hits = 0
    for _ in range(total):
        hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    probability = hits / total
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits, "total": total, "measured_probability": probability,
        "prior": "uniform over (P^1(F_p))^n; all shape/range rules enforced",
        "structured_space": search_space(inst),
    }

    # G5: an exact small count.
    tiny = make_instance(n=6, p=5, seed=314159)
    valid_count = enumerate_all(tiny)
    tiny_space = search_space(tiny)
    fraction = valid_count / tiny_space if valid_count is not None else None
    report["G5_sparse"] = {
        "pass": valid_count is not None and fraction is not None and fraction < 0.001,
        "valid_answers": valid_count, "structured_space": tiny_space,
        "valid_fraction": fraction,
    }

    # G6: attacks explicitly aimed at the planting distribution.
    attacks = {
        "outlier_local_slice_count": 0,
        "greedy_coordinate_descent": 0,
        "random_restart_min_conflicts_64": 0,
    }
    attack_seeds = list(range(800, 808))
    for seed in attack_seeds:
        attacked = make_instance(seed=seed, **ship)
        outlier = _outlier_attack(attacked)
        greedy = _greedy_attack(attacked, outlier)
        restart = _random_restart_attack(attacked, random.Random(seed ^ 0xA5A5A5A5))
        attacks["outlier_local_slice_count"] += int(verify(attacked, outlier)[0])
        attacks["greedy_coordinate_descent"] += int(verify(attacked, greedy)[0])
        attacks["random_restart_min_conflicts_64"] += int(verify(attacked, restart)[0])
    report["G6_adversary_panel"] = {
        "pass": all(successes == 0 for successes in attacks.values()),
        "seeds": len(attack_seeds),
        "attacks": {name: {"successes": value, "attempts": len(attack_seeds)}
                    for name, value in attacks.items()},
    }

    # G7: doubling n grows a square core and the exact candidate space.
    doubled_params = dict(ship)
    doubled_params["n"] = 2 * int(ship["n"])
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    base_bits = search_space(inst).bit_length()
    doubled_bits = search_space(doubled).bit_length()
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_bits > base_bits,
        "base_n": inst["n"], "doubled_n": doubled["n"],
        "base_search_bits": base_bits, "doubled_search_bits": doubled_bits,
        "doubled_verify_reason": doubled_why,
    }

    # G8: all representation symmetries, their composition, and diversity.
    invariance_checks = 0
    real_checks = 0
    errors = []
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(seed=10_000 + seed, **ship)
        base_key = canonical_key(base)
        unrelated_keys.append(base_key)
        trng = random.Random(90_000 + seed)

        clause_order = list(range(base["m"]))
        trng.shuffle(clause_order)
        identity_vars = list(range(base["n"]))
        identity_axes = [[0, 1, 2] for _ in range(base["m"])]
        reordered = _relabel_instance(base, identity_vars, clause_order, identity_axes)

        variable_perm = list(range(base["n"]))
        trng.shuffle(variable_perm)
        axis_orders = []
        for _ in range(base["m"]):
            axes = [0, 1, 2]
            trng.shuffle(axes)
            axis_orders.append(axes)
        relabelled = _relabel_instance(base, variable_perm, clause_order, axis_orders)

        matrices = [_random_gl2(base["p"], trng) for _ in range(base["n"])]
        based = _basis_change_instance(base, matrices)
        scales = [trng.randrange(1, base["p"]) for _ in range(base["m"])]
        scaled = _scale_constraints(base, scales)
        composed_matrices = [_random_gl2(base["p"], trng) for _ in range(base["n"])]
        composed = _basis_change_instance(relabelled, composed_matrices)
        composed_scales = [trng.randrange(1, base["p"]) for _ in range(base["m"])]
        composed = _scale_constraints(composed, composed_scales)

        for label, transformed in (("clause reorder", reordered),
                                   ("variable/axis relabel", relabelled),
                                   ("local GL2 basis", based),
                                   ("constraint rescaling", scaled),
                                   ("composed", composed)):
            invariance_checks += 1
            if canonical_key(transformed) != base_key:
                errors.append(f"seed {seed}: key changed under {label}")
            ok, why = verify(transformed, transformed["answer"])
            real_checks += 1
            if not ok:
                errors.append(f"seed {seed}: carried answer failed under {label}: {why}")
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not errors and distinct == 20,
        "invariance_checks": invariance_checks,
        "real_transform_checks": real_checks,
        "unrelated_distinct": distinct, "unrelated_total": 20,
        "transformations": ["clause reorder", "variable and tensor-axis relabelling",
                            "independent local GL(2,p) basis changes",
                            "independent nonzero constraint rescaling", "all composed"],
        "key_caveat": "strong invariant, not complete tensor-network canonization",
        "errors": errors,
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
