#!/usr/bin/env python3
"""Verified generalized graph-orientation instances from arXiv:2405.20263.

The paper permits fixed local relations whose tuples are labelled cliques and
whose allowed configurations are tournaments.  This module fixes one such
relation: on an ordered triple (a,b,c), an even number of the arcs a->b,
a->c,b->c must be present.  This affine relation is closed under the paper's
minority operation.

Generation is inverse: sample a tournament first, then choose the coordinate
order of every triple so that it satisfies the fixed relation.  Extra 4-cycle
parity constraints are sampled from the same tournament and are redundant
under vertex switching.  No generated instance is solved in order to obtain
its certificate.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "complete undirected graph",
        "labelled 3- and 4-cliques with allowed tournament relations",
        "tournament adjacency matrix",
    ],
    "verification_operations": [
        "binary matrix shape and antisymmetry checks",
        "exact XOR on directed edge indicators",
        "exact comparison with local relation parity",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 1.3 and Theorem 2 explicitly identify finite graphs with "
        "labelled clique-tournament relations as the generalized orientation "
        "instances; Section 6.2 defines edgewise minority and Corollary 24(3) "
        "covers relations preserved by it"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize that reversing every edge incident with any vertex preserves "
        "all displayed cycle parities, so one star can be gauge-fixed and every "
        "remaining arc read from its anchor triangle."
    ),
    "hardness_basis": (
        "Track B: the affine orientation CSP is solved by Gaussian elimination "
        "over GF(2) in O(mq^2) scalar-bit operations for q=n(n-1)/2 edge "
        "variables; the shipping seed-314159 reference run used 230,225 "
        "counted scalar-bit operations and 0.0065 wall-clock seconds "
        "(machine-dependent), whereas switching invariance reduces the shipping "
        "compact route to 110 parity/placement operations."
    ),
    "max_answer_tokens": 79,
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


# n controls the number q=n(n-1)/2 of oriented edges.  decoys controls the
# number of redundant four-cycle constraints without lengthening the answer.
DIFFICULTY = {
    "demo": {"n": 4, "decoys": 2, "local_restarts": 2},
    "easy": {"n": 9, "decoys": 36, "local_restarts": 4},
    "medium": {"n": 12, "decoys": 160, "local_restarts": 6},
    "hard": {"n": 15, "decoys": 600, "local_restarts": 8},
}
SHIPPING_DIFFICULTY = "medium"


STRUCTURAL_HINT = (
    "Reversing all arcs incident with one vertex leaves every displayed cycle "
    "parity invariant."
)
PLACEBO_HINT = (
    "Checking all arc directions against their ordered coordinates helps avoid "
    "indexing mistakes."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "An n-by-n JSON matrix A of bits: A[i][i]=0 and, for i!=j, exactly one "
        "of A[i][j], A[j][i] is 1; A[i][j]=1 means the arc i->j.  Thus the "
        "bounded language contains exactly 2^(n(n-1)/2) tournament matrices."
    ),
    "bounds": {
        "rows": "inst['n']",
        "columns": "inst['n']",
        "alphabet": [0, 1],
        "diagonal": 0,
        "off_diagonal_rule": "A[i][j] + A[j][i] = 1",
        "max_atomic_elements_at_shipping": 256,
    },
}


NOTES = (
    "Section 1.3 and Theorem 2 fix the exact generalized problem: the input is "
    "an undirected graph plus labelled clique tuples, each required to realize "
    "one of a fixed finite set of tournaments. Section 6.2 defines minority as "
    "edgewise odd parity, and Lemma 23/Corollary 24 say that preservation by "
    "minority is a tractable case. Those results rule out a Track A claim for "
    "the affine relation used here: Gaussian elimination is the standard exact "
    "solver and is reported openly. The compact route instead uses the vertex-"
    "switching invariant: fix every edge incident with vertex 0 toward vertex "
    "0, then the ordered constraint on {0,i,j} determines edge {i,j}. The "
    "sampled certificate is generated before the constraints. Every triple "
    "coordinate order is chosen uniformly among the three orders of the needed "
    "parity, so there is no planted-vs-decoy element distribution. Four-cycle "
    "constraints are genuine local tournament relations but redundant cycle "
    "parities; they crowd the mechanical system while leaving the compact route "
    "and witness length fixed. Uniform tournament bits and coordinate orders "
    "defeat marginal-edge and label-order signatures; shuffled dense equations "
    "defeat one-pass greed; 55 independent shipping constraints make the short "
    "random-restart budget negligible. The adversary panel measures all four. "
    "Exact Gaussian elimination is deliberately "
    "reported separately as the successful Track B reference algorithm."
)


# Filled from script-owned hardening runs after the module itself passes.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 3, "attempts": 3},
    "hinted_verdict": "too_easy",
}


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"^\s*```(?:json|text)?\s*(.*?)\s*```\s*$", re.I | re.S)
_G4_SAMPLES = 200_000
_ENUMERATION_CAP = 200_000
_ATTACK_SEEDS = 8


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate(n, decoys, local_restarts):
    for name, value in (("n", n), ("decoys", decoys),
                        ("local_restarts", local_restarts)):
        if not _is_int(value):
            raise ValueError(f"{name} must be an integer")
    if not 3 <= n <= 32:
        raise ValueError("n must lie in 3..32")
    max_cycles = 3 * math.comb(n, 4) if n >= 4 else 0
    if not 0 <= decoys <= max_cycles:
        raise ValueError(f"decoys must lie in 0..{max_cycles} for n={n}")
    if not 1 <= local_restarts <= 128:
        raise ValueError("local_restarts must lie in 1..128")


def _random_tournament(n, rng):
    A = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            bit = rng.randrange(2)
            A[i][j] = bit
            A[j][i] = 1 - bit
    return A


def _permutation_parity(order):
    inversions = 0
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            inversions ^= order[i] > order[j]
    return int(inversions)


def _random_order_with_parity(vertices, parity, rng):
    perms = [p for p in itertools.permutations(vertices)
             if _permutation_parity(p) == parity]
    return list(rng.choice(perms))


def _cycle_representatives(vertices):
    """The three unoriented Hamilton cycles on one sorted four-set."""
    a, b, c, d = vertices
    return [(a, b, c, d), (a, b, d, c), (a, c, b, d)]


def _random_dihedral_order(cycle, rng):
    cycle = list(cycle)
    if rng.randrange(2):
        cycle = [cycle[0]] + list(reversed(cycle[1:]))
    shift = rng.randrange(4)
    return cycle[shift:] + cycle[:shift]


def _cycle_value(A, cycle):
    return (
        A[cycle[0]][cycle[1]]
        ^ A[cycle[1]][cycle[2]]
        ^ A[cycle[2]][cycle[3]]
        ^ A[cycle[3]][cycle[0]]
    )


def make_instance(n, seed=0, decoys=0, local_restarts=8, **params):
    """Inverse-generate a tournament and build its local relations around it."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    _validate(n, decoys, local_restarts)
    rng = random.Random(seed)

    answer = _random_tournament(n, rng)

    # The relation on an ordered triple (a,b,c) is
    # A[a][b] xor A[a][c] xor A[b][c] == 0.  Reordering a triple changes this
    # parity by the parity of the coordinate permutation.  Pick one of the
    # three orders of the required parity uniformly.
    triangles = []
    for triple in itertools.combinations(range(n), 3):
        a, b, c = triple
        syndrome = answer[a][b] ^ answer[a][c] ^ answer[b][c]
        triangles.append(_random_order_with_parity(triple, syndrome, rng))
    rng.shuffle(triangles)

    # A 4-cycle contains every vertex twice, so its arc parity is invariant
    # under switching all incident arcs at any vertex.  These constraints are
    # redundant once every triangle constraint is present, but they are native
    # local clique relations and enlarge the mechanical input at fixed witness
    # length.
    cycle_pool = []
    for four in itertools.combinations(range(n), 4):
        cycle_pool.extend(_cycle_representatives(four))
    rng.shuffle(cycle_pool)
    cycles = []
    for base in cycle_pool[:decoys]:
        order = _random_dihedral_order(base, rng)
        cycles.append({"vertices": order, "parity": _cycle_value(answer, order)})
    rng.shuffle(cycles)

    return {
        "n": n,
        "graph": "complete",
        "triangle_constraints": triangles,
        "cycle_constraints": cycles,
        "local_restarts": local_restarts,
        "answer": answer,
    }


def render(inst):
    """Render a complete, standalone generalized orientation problem."""
    n = inst["n"]
    lines = [
        "GENERALIZED TOURNAMENT-ORIENTATION PROBLEM",
        "",
        f"The vertices are the integers 0 through {n - 1}. The undirected graph",
        "is complete: every pair of distinct vertices must receive exactly one",
        "direction. Represent the orientation by an n-by-n binary matrix A, where",
        "A[i][j]=1 means i -> j. Require A[i][i]=0 and",
        "A[i][j]+A[j][i]=1 for every i != j.",
        "",
        "All XORs below are exact addition modulo 2.",
        "",
        "TRIANGLE RELATION T:",
        "For every listed ordered triple [a,b,c], require",
        "    A[a][b] XOR A[a][c] XOR A[b][c] = 0.",
        "The coordinate order is part of the constraint; do not sort a triple.",
        "Triangle constraints:",
    ]
    lines.extend("  " + json.dumps(t) for t in inst["triangle_constraints"])
    lines.extend([
        "",
        "FOUR-CYCLE RELATIONS Q0 AND Q1:",
        "For every entry [a,b,c,d] : p, require",
        "    A[a][b] XOR A[b][c] XOR A[c][d] XOR A[d][a] = p.",
        "Here p is the displayed bit 0 or 1. The cyclic order is part of the",
        "constraint; rotations or reversal describe the same four-cycle parity.",
        "Four-cycle constraints:",
    ])
    if inst["cycle_constraints"]:
        lines.extend(
            "  " + json.dumps(c["vertices"]) + " : " + str(c["parity"])
            for c in inst["cycle_constraints"]
        )
    else:
        lines.append("  (none)")
    lines.extend([
        "",
        f"Return exactly one {n}-by-{n} JSON array of integer bits satisfying all",
        "requirements. Rows and columns use vertex order 0,1,...,n-1.",
        "Give your final answer inside <answer></answer> tags, as the JSON matrix.",
        "Example: <answer>[[0,1],[0,0]]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Extract a JSON matrix from tagged or fenced model output."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    candidates = list(reversed(matches))
    if not candidates:
        fences = re.findall(r"```(?:json|text)?\s*(.*?)```", text, re.I | re.S)
        candidates.extend(reversed(fences))
        candidates.append(text)
    for body in candidates:
        fenced = _FENCE_RE.match(body)
        if fenced:
            body = fenced.group(1)
        body = body.strip()
        try:
            return json.loads(body)
        except (TypeError, ValueError, json.JSONDecodeError):
            pass
        # Tolerate prose inside a fence by asking the JSON decoder to start at
        # each opening bracket.  Shape validation remains verify()'s job.
        decoder = json.JSONDecoder()
        for match in re.finditer(r"\[", body):
            try:
                value, _ = decoder.raw_decode(body[match.start():])
                return value
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
    return None


def verify(inst, answer):
    """Check a candidate tournament matrix and every local relation exactly."""
    n = inst.get("n")
    if not isinstance(answer, list):
        return False, "answer is not a JSON matrix"
    if not answer:
        return False, "answer matrix is empty"
    if len(answer) != n:
        return False, f"matrix has wrong row count: expected {n}, got {len(answer)}"
    for i, row in enumerate(answer):
        if not isinstance(row, list):
            return False, f"row {i} is not a JSON list"
        if len(row) != n:
            return False, f"row {i} has wrong length: expected {n}, got {len(row)}"
    for i, row in enumerate(answer):
        for j, value in enumerate(row):
            if not _is_int(value) or value not in (0, 1):
                return False, f"entry [{i}][{j}] is not an integer bit"
    if len({tuple(row) for row in answer}) != n:
        return False, "matrix contains duplicate rows"
    for i in range(n):
        if answer[i][i] != 0:
            return False, f"diagonal entry [{i}][{i}] must be 0"
    for i in range(n):
        for j in range(i + 1, n):
            if answer[i][j] + answer[j][i] != 1:
                return False, f"antisymmetry fails on vertex pair [{i},{j}]"
    for index, triple in enumerate(inst["triangle_constraints"]):
        a, b, c = triple
        if answer[a][b] ^ answer[a][c] ^ answer[b][c]:
            return False, f"triangle constraint {index} is violated"
    for index, constraint in enumerate(inst["cycle_constraints"]):
        cycle = constraint["vertices"]
        got = _cycle_value(answer, cycle)
        if got != constraint["parity"]:
            return False, f"four-cycle constraint {index} is violated"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from all matrices satisfying the obvious tournament rules."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    return _random_tournament(inst["n"], rng)


def search_space(inst):
    """The number of n-vertex tournament matrices."""
    n = inst["n"]
    return 1 << (n * (n - 1) // 2)


def _matrix_from_upper_bits(n, bits):
    A = [[0] * n for _ in range(n)]
    position = 0
    for i in range(n):
        for j in range(i + 1, n):
            bit = (bits >> position) & 1
            A[i][j] = bit
            A[j][i] = 1 - bit
            position += 1
    return A


def enumerate_all(inst):
    """Brute-force exact valid-answer count when the tournament space is small."""
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    hits = 0
    for bits in range(space):
        if verify(inst, _matrix_from_upper_bits(inst["n"], bits))[0]:
            hits += 1
    return hits


def _edge_index(n):
    pairs = []
    index = {}
    for i in range(n):
        for j in range(i + 1, n):
            index[(i, j)] = len(pairs)
            pairs.append((i, j))
    return pairs, index


def _normalised_equation(terms, required, edge_to_col):
    mask = 0
    rhs = required
    for a, b in terms:
        if a > b:
            rhs ^= 1
            a, b = b, a
        mask ^= 1 << edge_to_col[(a, b)]
    return mask, rhs


def _linear_rows(inst):
    _, edge_to_col = _edge_index(inst["n"])
    rows = []
    for a, b, c in inst["triangle_constraints"]:
        rows.append(_normalised_equation(
            [(a, b), (a, c), (b, c)], 0, edge_to_col
        ))
    for constraint in inst["cycle_constraints"]:
        a, b, c, d = constraint["vertices"]
        rows.append(_normalised_equation(
            [(a, b), (b, c), (c, d), (d, a)],
            constraint["parity"], edge_to_col
        ))
    return rows


def _matrix_from_assignment(n, assignment):
    bits = 0
    for i, bit in enumerate(assignment):
        bits |= (bit & 1) << i
    return _matrix_from_upper_bits(n, bits)


def _gaussian_reference(inst):
    """Bit-packed exact Gaussian elimination; return solution and cost stats."""
    rows0 = _linear_rows(inst)
    q = inst["n"] * (inst["n"] - 1) // 2
    rows = [mask | (rhs << q) for mask, rhs in rows0]
    m = len(rows)
    r = 0
    pivots = []
    pivot_tests = 0
    row_xors = 0
    t0 = time.perf_counter()
    for col in range(q):
        pivot = None
        for i in range(r, m):
            pivot_tests += 1
            if (rows[i] >> col) & 1:
                pivot = i
                break
        if pivot is None:
            continue
        rows[r], rows[pivot] = rows[pivot], rows[r]
        for i in range(m):
            if i == r:
                continue
            pivot_tests += 1
            if (rows[i] >> col) & 1:
                rows[i] ^= rows[r]
                row_xors += 1
        pivots.append(col)
        r += 1
        if r == m:
            break
    coefficient_mask = (1 << q) - 1
    for row in rows:
        if not (row & coefficient_mask) and ((row >> q) & 1):
            return None, {
                "rank": len(pivots),
                "pivot_tests": pivot_tests,
                "row_xors": row_xors,
                "scalar_bit_operations": pivot_tests + row_xors * (q + 1),
                "wall_clock_sec": time.perf_counter() - t0,
            }
    assignment = [0] * q
    for row_index, col in enumerate(pivots):
        assignment[col] = (rows[row_index] >> q) & 1
    stats = {
        "rank": len(pivots),
        "variables": q,
        "equations": m,
        "pivot_tests": pivot_tests,
        "row_xors": row_xors,
        "scalar_bit_operations": pivot_tests + row_xors * (q + 1),
        "wall_clock_sec": time.perf_counter() - t0,
    }
    return _matrix_from_assignment(inst["n"], assignment), stats


def _compact_solution(inst):
    """Gauge-fix the star at 0, then read every other edge from its triangle."""
    n = inst["n"]
    by_set = {frozenset(t): t for t in inst["triangle_constraints"]}
    assignment = [0] * (n * (n - 1) // 2)
    _, edge_to_col = _edge_index(n)
    for i in range(1, n):
        assignment[edge_to_col[(0, i)]] = 0
    for i in range(1, n):
        for j in range(i + 1, n):
            triple = by_set[frozenset((0, i, j))]
            # With star variables set to zero, the remaining upper-triangle
            # variable equals the coordinate permutation's inversion parity.
            assignment[edge_to_col[(i, j)]] = _permutation_parity(triple)
    return _matrix_from_assignment(n, assignment)


def _matmul_int(A, B):
    n = len(A)
    BT = list(zip(*B))
    return [[sum(a * b for a, b in zip(A[i], BT[j]))
             for j in range(n)] for i in range(n)]


def _charpoly_coefficients(A):
    """Exact Faddeev-LeVerrier characteristic polynomial coefficients."""
    n = len(A)
    B = [[int(i == j) for j in range(n)] for i in range(n)]
    coeffs = [1]
    for k in range(1, n + 1):
        AB = _matmul_int(A, B)
        trace = sum(AB[i][i] for i in range(n))
        if trace % k:
            raise ArithmeticError("non-integral characteristic coefficient")
        coefficient = -trace // k
        coeffs.append(coefficient)
        for i in range(n):
            AB[i][i] += coefficient
        B = AB
    return coeffs


def _seidel_matrix(A):
    n = len(A)
    S = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            value = 1 if A[i][j] else -1
            S[i][j] = value
            S[j][i] = -value
    return S


def canonical_key(inst):
    """A strong exact invariant of the tournament switching class.

    The skew-Seidel characteristic polynomial and its vertex-deleted deck are
    invariant under vertex relabelling and under every vertex switch.  This is
    deliberately not a hash of the seed, answer, or rendered statement.
    """
    solution = _compact_solution(inst)
    S = _seidel_matrix(solution)
    whole = _charpoly_coefficients(S)
    deck = []
    for deleted in range(inst["n"]):
        minor = [row[:deleted] + row[deleted + 1:]
                 for i, row in enumerate(S) if i != deleted]
        deck.append(_charpoly_coefficients(minor))
    payload = json.dumps([inst["n"], whole, sorted(deck)], separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params):
    """Increase clutter at fixed witness size, then use the final legal matrix size."""
    p = {k: v for k, v in params.items() if k != "_preset"}
    n = int(p.get("n", 15))
    decoys = int(p.get("decoys", 0))
    restarts = int(p.get("local_restarts", 8))
    if n < 16:
        p["n"] = 16
        p["decoys"] = max(decoys + 400, 1_000)
        p["local_restarts"] = min(128, restarts + 2)
        return p
    maximum = 3 * math.comb(n, 4)
    if decoys < maximum:
        p["decoys"] = min(maximum, max(decoys + 500, (3 * decoys) // 2))
        p["local_restarts"] = min(128, restarts + 2)
        return p
    # n=17 would make a 289-atom matrix, beyond the 256-atom answer cap.
    return "cap_bound"


def _attack_marginal(inst):
    rows = _linear_rows(inst)
    q = inst["n"] * (inst["n"] - 1) // 2
    ones = [0] * q
    zeros = [0] * q
    for mask, rhs in rows:
        todo = mask
        while todo:
            low = todo & -todo
            col = low.bit_length() - 1
            (ones if rhs else zeros)[col] += 1
            todo ^= low
    guess = [int(ones[i] > zeros[i]) for i in range(q)]
    return _matrix_from_assignment(inst["n"], guess), len(rows)


def _attack_greedy(inst):
    rows = _linear_rows(inst)
    q = inst["n"] * (inst["n"] - 1) // 2
    values = [None] * q
    conflicts = 0
    steps = 0
    for mask, rhs in rows:
        assigned_parity = 0
        unassigned = []
        todo = mask
        while todo:
            low = todo & -todo
            col = low.bit_length() - 1
            if values[col] is None:
                unassigned.append(col)
            else:
                assigned_parity ^= values[col]
            todo ^= low
        steps += 1
        if not unassigned:
            conflicts += assigned_parity != rhs
            continue
        for col in unassigned[:-1]:
            values[col] = 0
        values[unassigned[-1]] = assigned_parity ^ rhs
    guess = [0 if value is None else value for value in values]
    return _matrix_from_assignment(inst["n"], guess), steps + conflicts


def _attack_local_repair(inst, rng):
    rows = _linear_rows(inst)
    q = inst["n"] * (inst["n"] - 1) // 2
    iterations = 0
    for _ in range(inst["local_restarts"]):
        assignment = rng.getrandbits(q)
        for _step in range(2 * q):
            bad = [(mask, rhs) for mask, rhs in rows
                   if ((assignment & mask).bit_count() & 1) != rhs]
            if not bad:
                return _matrix_from_upper_bits(inst["n"], assignment), iterations
            mask, _ = rng.choice(bad)
            choices = [i for i in range(q) if (mask >> i) & 1]
            assignment ^= 1 << rng.choice(choices)
            iterations += 1
    return _matrix_from_upper_bits(inst["n"], assignment), iterations


def _attack_label_order(inst):
    """The simplest in-context ansatz: orient every edge low label to high."""
    A = [[0] * inst["n"] for _ in range(inst["n"])]
    for i in range(inst["n"]):
        for j in range(i + 1, inst["n"]):
            A[i][j] = 1
            A[j][i] = 1 - A[i][j]
    return A, inst["n"] * (inst["n"] - 1) // 2


def _relabel(inst, permutation):
    n = inst["n"]
    out = copy.deepcopy(inst)
    out["triangle_constraints"] = [
        [permutation[v] for v in triple]
        for triple in inst["triangle_constraints"]
    ]
    out["cycle_constraints"] = [
        {"vertices": [permutation[v] for v in c["vertices"]],
         "parity": c["parity"]}
        for c in inst["cycle_constraints"]
    ]
    A = inst["answer"]
    carried = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            carried[permutation[i]][permutation[j]] = A[i][j]
    out["answer"] = carried
    return out


def _apply_tuple_symmetries(inst):
    out = copy.deepcopy(inst)
    out["triangle_constraints"] = [t[1:] + t[:1]
                                   for t in out["triangle_constraints"]]
    transformed_cycles = []
    for index, c in enumerate(out["cycle_constraints"]):
        vertices = c["vertices"]
        if index % 2:
            vertices = list(reversed(vertices))
        else:
            vertices = vertices[1:] + vertices[:1]
        transformed_cycles.append({"vertices": vertices, "parity": c["parity"]})
    out["cycle_constraints"] = transformed_cycles
    return out


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest():
    """Run all mandatory construction, parsing, hardness, and invariance gates."""
    report = {}

    g1_failures = []
    g1_tests = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 29):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_tests += 1
            if not ok:
                g1_failures.append([preset, seed, why])
            try:
                if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                    g1_failures.append([preset, seed, "answer is not JSON-native"])
            except (TypeError, ValueError) as exc:
                g1_failures.append([preset, seed, f"JSON encoding failed: {exc}"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "tests": g1_tests,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=314159, **ship_params)
    planted = ship["answer"]
    corruptions = {}

    dropped = copy.deepcopy(planted)
    dropped.pop()
    corruptions["drop_one_row"] = verify(ship, dropped)

    swapped = copy.deepcopy(planted)
    swapped[0][1], swapped[1][0] = swapped[1][0], swapped[0][1]
    corruptions["swap_opposite_entries"] = verify(ship, swapped)

    duplicated = copy.deepcopy(planted)
    duplicated[1] = duplicated[0][:]
    corruptions["duplicate_one_row"] = verify(ship, duplicated)

    corruptions["empty"] = verify(ship, [])

    outside = copy.deepcopy(planted)
    outside[0][0] = 2
    corruptions["out_of_range"] = verify(ship, outside)

    reasons = [why for ok, why in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not ok for ok, _ in corruptions.values())
                and len(set(reasons)) == len(reasons),
        "cases": {name: {"accepted": ok, "reason": why}
                  for name, (ok, why) in corruptions.items()},
        "distinct_reasons": len(set(reasons)),
    }

    encoded = json.dumps(planted, separators=(",", ":"))
    response = (
        "I used the switching symmetry and checked the local parities.\n"
        "```json\n<answer>\n" + encoded + "\n</answer>\n```\n"
        "The matrix is antisymmetric off the diagonal."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("garbage without JSON") is None,
        "model_style_response_parsed": parsed == planted,
        "garbage_returns_none": parse_answer("garbage without JSON") is None,
    }

    guess_rng = random.Random(0x240520263)
    guess_hits = 0
    guess_t0 = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        candidate = random_candidate(ship, guess_rng)
        guess_hits += int(verify(ship, candidate)[0])
    guess_wall = time.perf_counter() - guess_t0
    guess_fraction = guess_hits / _G4_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": _G4_SAMPLES,
        "sampled_fraction": guess_fraction,
        "sampling_wall_clock_sec": guess_wall,
        "candidate_prior": "uniform over valid tournament matrices",
    }

    ref_solution, ref_stats = _gaussian_reference(ship)
    ref_ok, ref_why = verify(ship, ref_solution) if ref_solution is not None \
        else (False, "Gaussian elimination returned no solution")

    # G6 is measured once and feeds the G5 cost fields as well.
    attack_results = {
        "outlier_marginal_rhs": {"successes": 0, "attempts": 0,
                                  "iterations": 0, "wall_clock_sec": 0},
        "greedy_one_pass": {"successes": 0, "attempts": 0,
                             "iterations": 0, "wall_clock_sec": 0},
        "random_restart_local_repair": {"successes": 0, "attempts": 0,
                                         "iterations": 0, "wall_clock_sec": 0},
        "by_hand_label_order_ansatz": {"successes": 0, "attempts": 0,
                                        "iterations": 0, "wall_clock_sec": 0},
    }
    reference_solutions = 0
    reference_operations = 0
    reference_wall = 0
    for seed in range(100, 100 + _ATTACK_SEEDS):
        inst = make_instance(seed=seed, **ship_params)
        rng = random.Random(seed ^ 0xA5A5A5)
        attacks = (
            ("outlier_marginal_rhs", lambda: _attack_marginal(inst)),
            ("greedy_one_pass", lambda: _attack_greedy(inst)),
            ("random_restart_local_repair", lambda: _attack_local_repair(inst, rng)),
            ("by_hand_label_order_ansatz", lambda: _attack_label_order(inst)),
        )
        for name, attack in attacks:
            t0 = time.perf_counter()
            candidate, iterations = attack()
            elapsed = time.perf_counter() - t0
            ok, _ = verify(inst, candidate)
            attack_results[name]["successes"] += int(ok)
            attack_results[name]["attempts"] += 1
            attack_results[name]["iterations"] += iterations
            attack_results[name]["wall_clock_sec"] += elapsed
        candidate, stats = _gaussian_reference(inst)
        ok, _ = verify(inst, candidate) if candidate is not None else (False, "none")
        reference_solutions += int(ok)
        reference_operations += stats["scalar_bit_operations"]
        reference_wall += stats["wall_clock_sec"]

    all_attacks_failed = all(v["successes"] == 0 and v["attempts"] >= 8
                             for v in attack_results.values())
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6 and ref_ok,
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_density_samples": _G4_SAMPLES,
        "shipping_sampled_valid_fraction": guess_fraction,
        "shipping_exact_valid_solution_count_theoretical": 1 << (ship["n"] - 1),
        "shipping_exact_density_denominator_theoretical": 1 << (
            (ship["n"] - 1) * (ship["n"] - 2) // 2
        ),
        "reference_wall_clock_sec": ref_stats["wall_clock_sec"],
        "reference_scalar_bit_operations": ref_stats["scalar_bit_operations"],
        "reference_rank": ref_stats["rank"],
        "strongest_failed_attack_wall_clock_sec": max(
            v["wall_clock_sec"] for v in attack_results.values()
        ),
        "strongest_failed_attack_iterations": max(
            v["iterations"] for v in attack_results.values()
        ),
        "reference_verify_reason": ref_why,
    }

    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_solutions == _ATTACK_SEEDS,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "bit-packed Gaussian elimination over GF(2)",
            "complexity": "O(m q^2) scalar-bit operations; q=n(n-1)/2",
            "wall_clock_sec": reference_wall,
            "operations": reference_operations,
            "attempts": _ATTACK_SEEDS,
            "successes": reference_solutions,
            "solves": f"{reference_solutions}/{_ATTACK_SEEDS}, as expected",
        },
    }

    doubled = dict(ship_params)
    doubled["n"] *= 2
    doubled["decoys"] = min(
        doubled["decoys"], 3 * math.comb(doubled["n"], 4)
    )
    doubled_inst = make_instance(seed=271828, **doubled)
    doubled_ok, doubled_why = verify(doubled_inst, doubled_inst["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
                and search_space(doubled_inst) > search_space(ship),
        "shipping_n": ship["n"],
        "doubled_n": doubled_inst["n"],
        "shipping_edge_variables": ship["n"] * (ship["n"] - 1) // 2,
        "doubled_edge_variables": doubled_inst["n"] * (doubled_inst["n"] - 1) // 2,
        "verify_reason": doubled_why,
    }

    invariance = {"vertex_relabellings": 0, "constraint_reorderings": 0,
                  "tuple_symmetries": 0, "composed_transformations": 0}
    transformation_valid = 0
    switched_answers_valid = 0
    original_keys = []
    g8_failures = []
    for seed in range(20):
        inst = make_instance(seed=10_000 + seed, **ship_params)
        key = canonical_key(inst)
        original_keys.append(key)

        switched = copy.deepcopy(inst["answer"])
        vertex = seed % inst["n"]
        for other in range(inst["n"]):
            if other != vertex:
                switched[vertex][other], switched[other][vertex] = (
                    switched[other][vertex], switched[vertex][other]
                )
        switched_answers_valid += int(verify(inst, switched)[0])

        rng = random.Random(20_000 + seed)
        permutation = list(range(inst["n"]))
        rng.shuffle(permutation)
        relabelled = _relabel(inst, permutation)
        if canonical_key(relabelled) == key:
            invariance["vertex_relabellings"] += 1
        else:
            g8_failures.append([seed, "vertex relabelling changed key"])

        reordered = copy.deepcopy(inst)
        rng.shuffle(reordered["triangle_constraints"])
        rng.shuffle(reordered["cycle_constraints"])
        if canonical_key(reordered) == key:
            invariance["constraint_reorderings"] += 1
        else:
            g8_failures.append([seed, "constraint reordering changed key"])

        symmetrised = _apply_tuple_symmetries(inst)
        if canonical_key(symmetrised) == key:
            invariance["tuple_symmetries"] += 1
        else:
            g8_failures.append([seed, "tuple symmetry changed key"])

        composed = _apply_tuple_symmetries(relabelled)
        rng.shuffle(composed["triangle_constraints"])
        rng.shuffle(composed["cycle_constraints"])
        if canonical_key(composed) == key:
            invariance["composed_transformations"] += 1
        else:
            g8_failures.append([seed, "composed transformation changed key"])
        carried_ok, _ = verify(composed, composed["answer"])
        transformation_valid += int(carried_ok)

    distinct_keys = len(set(original_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures
                and all(count == 20 for count in invariance.values())
                and transformation_valid == 20
                and switched_answers_valid == 20
                and distinct_keys == 20,
        "invariance_counts": invariance,
        "transformed_answers_verified": transformation_valid,
        "vertex_switched_answers_verified": switched_answers_valid,
        "unrelated_distinct_keys": distinct_keys,
        "unrelated_instances": 20,
        "failures": g8_failures,
        "invariant": "skew-Seidel characteristic polynomial plus deletion deck",
    }

    answer_blob = json.dumps(planted, separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(planted)
    compact_operations = 2 * math.comb(ship["n"] - 1, 2)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0)
    within_caps = (answer_chars <= 2_000 and answer_elements <= 256
                   and compact_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact_operations,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    PROBLEM_PROFILE["max_answer_tokens"] = answer_tokens
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
