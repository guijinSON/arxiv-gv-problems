"""Planted acyclic colourings of co-bipartite graphs.

The family is the connected-perfect-matching formulation in Lemma 8 of
arXiv:2008.09415.  Only the Python standard library is used.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re
from typing import Any


DIFFICULTY = {
    "demo": {"n": 6},
    "easy": {"n": 24},
    "medium": {"n": 32},
    "hard": {"n": 40},
}

SHIPPING_DIFFICULTY = "easy"

NOTES = r"""
Section 1 fixes the definition used here: an acyclic colouring is proper and
every two colour classes induce a forest.  The paper explicitly warns that
properness is not universal in the injective-colouring literature.  Section 3,
Lemma 8 is the key construction: a balanced bipartite graph has a connected
perfect matching exactly when its complement has an acyclic colouring with n
colours; the lemma proves NP-completeness on co-bipartite (hence 3P1-free)
graphs.  Section 2, Theorem 4 and Corollary 5 identify the main easy regime:
fixed-k variants are polynomial-time solvable on H-free graphs when H is a
linear forest.  This generator avoids it because the number of colours is n and
grows with the instance.

The witness permutation is sampled first.  For each unordered pair of planted
matching edges, the two possible connecting cross-edges receive one of the
three admissible patterns 10, 01, and 11 with equal probability.  Thus plant
and decoy nonedges have the same visible representation and the construction
has no positional direction or unequal pattern weight.  The attack panel tests
(1) a degree-sum outlier assignment, (2) deterministic constrained greedy, and
(3) 64 randomized MRV restarts.  All must fail on eight shipping-size seeds.
The canonical key uses bipartition-aware Weisfeiler-Lehman refinement; on the
shipped random instances every cell is normally a singleton, giving a full
canonical matrix.  Its equitable-quotient fallback is invariant but may merge
rare highly symmetric non-isomorphic inputs.
""".strip()


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Sample a witness first, then construct a co-bipartite graph around it."""
    if params:
        unknown = ", ".join(sorted(params))
        raise TypeError(f"unknown parameter(s): {unknown}")
    if isinstance(n, bool) or not isinstance(n, int) or n < 4:
        raise ValueError("n must be an integer at least 4")

    rng = random.Random(seed)

    # The answer is sampled first.  answer[i] is the B-vertex paired with A_i.
    answer0 = list(range(n))
    rng.shuffle(answer0)

    # allowed[i][j] means A_i B_j is an edge in the bipartite complement,
    # equivalently a nonedge in the co-bipartite graph shown to the solver.
    allowed = [[False] * n for _ in range(n)]
    for i, j in enumerate(answer0):
        allowed[i][j] = True

    saw_single_direction = False
    for i in range(n):
        for j in range(i + 1, n):
            pattern = rng.randrange(3)
            # Uniform over 10, 01, 11: the maximum-entropy distribution after
            # conditioning away 00, the sole pattern that breaks the plant.
            if pattern == 0:
                allowed[i][answer0[j]] = True
                saw_single_direction = True
            elif pattern == 1:
                allowed[j][answer0[i]] = True
                saw_single_direction = True
            else:
                allowed[i][answer0[j]] = True
                allowed[j][answer0[i]] = True

    # This astronomically rare repair guarantees that a transposition gives a
    # deterministic G2 corruption even for the smallest supported n.
    if not saw_single_direction:
        if rng.randrange(2):
            allowed[0][answer0[1]] = False
        else:
            allowed[1][answer0[0]] = False

    # The solver sees the target co-bipartite graph.  Its two sides are cliques;
    # matrix 1 records cross-edges and 0 records cross-nonedges.
    matrix = [[0 if allowed[i][j] else 1 for j in range(n)] for i in range(n)]
    return {
        "family": "acyclic_colouring_co_bipartite",
        "n": n,
        "matrix": matrix,
        "answer": [j + 1 for j in answer0],
    }


def render(inst: dict) -> str:
    """Render a complete, self-contained acyclic-colouring problem."""
    n = inst["n"]
    matrix = inst["matrix"]
    header = "    " + " ".join(f"B{j}" for j in range(1, n + 1))
    rows = [header]
    rows.extend(
        f"A{i + 1}: " + " ".join(str(x) for x in matrix[i])
        for i in range(n)
    )
    return f"""Acyclic colouring of a co-bipartite graph

The graph has 2n vertices, where n = {n}.  They are split into
A1,...,A{n} and B1,...,B{n}.  Every two distinct A-vertices are adjacent,
and every two distinct B-vertices are adjacent.  Cross-adjacency is given by
the matrix below: entry 1 means A_i is adjacent to B_j, and entry 0 means they
are nonadjacent.  The graph is undirected, simple, and has no loops.

{chr(10).join(rows)}

A proper colouring assigns one of the colours 1,...,{n} to every vertex and
never gives adjacent vertices the same colour.  It is acyclic when, for every
two colours, the subgraph induced by all vertices having either colour contains
no cycle.  Find an acyclic colouring using at most {n} colours.

Because each of A and B is a clique of size {n}, every such colouring must pair
each A_i with exactly one B-vertex.  Report the pairing as exactly {n} integers
p1,...,p{n}: p_i = j means A_i and B_j receive the same colour.  The integers
must be a permutation of 1,...,{n}; order is by A-index, and indices are
1-based.  Repetitions are forbidden.  Colour names do not need to be reported.

Give your final answer inside <answer></answer> tags, as comma-separated integers.
Example format: <answer>3, 1, 2</answer>
Output nothing else inside the tags."""


def parse_answer(text: str) -> object | None:
    """Extract the last well-formed comma-separated answer block."""
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    for body in reversed(blocks):
        if not re.fullmatch(r"\s*[+-]?\d+\s*(?:,\s*[+-]?\d+\s*)*", body):
            continue
        try:
            return [int(part.strip()) for part in body.split(",")]
        except (TypeError, ValueError):
            continue
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any witness without consulting the planted answer."""
    n = inst["n"]
    matrix = inst["matrix"]
    if not isinstance(answer, (list, tuple)):
        return False, "answer must be a list of integers"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) != n:
        return False, f"wrong length: expected {n} entries"
    for pos, value in enumerate(answer, 1):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"entry {pos} is not an integer"
        if value < 1 or value > n:
            return False, f"entry {pos} is outside 1..{n}"
    if len(set(answer)) != n:
        return False, f"entries must be a permutation of 1..{n}"

    paired = [value - 1 for value in answer]
    for i, j in enumerate(paired):
        if matrix[i][j] != 0:
            return False, (
                f"pair A{i + 1}-B{j + 1} is an edge, so it cannot share a colour"
            )

    # With two n-cliques and n paired colour classes, every bichromatic cycle
    # is exactly the four-cycle on two reported pairs.
    for i in range(n):
        for j in range(i + 1, n):
            if matrix[i][paired[j]] == 1 and matrix[j][paired[i]] == 1:
                return False, (
                    f"rows {i + 1} and {j + 1} create a bichromatic 4-cycle"
                )
    return True, "ok"


def _augmenting_random_matching(matrix: list[list[int]], rng: random.Random) -> list[int]:
    """Find a randomized perfect matching using only cross-nonedges."""
    n = len(matrix)

    # Dense random instances almost always finish by this cheap sequential pass.
    for _ in range(12):
        rows = list(range(n))
        rng.shuffle(rows)
        unused = list(range(n))
        candidate = [-1] * n
        for i in rows:
            options = [j for j in unused if matrix[i][j] == 0]
            if not options:
                break
            j = rng.choice(options)
            candidate[i] = j
            unused.remove(j)
        else:
            return candidate

    # Guaranteed fallback: randomized Kuhn augmenting paths.  It depends only
    # on the visible matrix and never on inst["answer"].
    col_to_row = [-1] * n

    def augment(i: int, seen: list[bool]) -> bool:
        options = [j for j in range(n) if matrix[i][j] == 0 and not seen[j]]
        rng.shuffle(options)
        for j in options:
            seen[j] = True
            if col_to_row[j] < 0 or augment(col_to_row[j], seen):
                col_to_row[j] = i
                return True
        return False

    rows = list(range(n))
    rng.shuffle(rows)
    for i in rows:
        if not augment(i, [False] * n):
            raise RuntimeError("instance unexpectedly has no perfect matching")
    candidate = [-1] * n
    for j, i in enumerate(col_to_row):
        candidate[i] = j
    return candidate


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample a perfect matching of visible nonedges, not a naive permutation."""
    return [j + 1 for j in _augmenting_random_matching(inst["matrix"], rng)]


def search_space(inst: dict) -> int | None:
    """Return the naive pairing space; the structural prior is narrower."""
    return math.factorial(inst["n"])


def enumerate_all(inst: dict) -> int | None:
    """Count all valid witnesses exactly when at most 9! need inspection."""
    n = inst["n"]
    if n > 9:
        return None
    matrix = inst["matrix"]
    count = 0
    for perm in itertools.permutations(range(n)):
        if any(matrix[i][perm[i]] for i in range(n)):
            continue
        if any(
            matrix[i][perm[j]] and matrix[j][perm[i]]
            for i in range(n) for j in range(i + 1, n)
        ):
            continue
        count += 1
    return count


def _wl_orientation_signature(matrix: list[list[int]]) -> str:
    """Canonical orientation signature under independent row/column relabelling."""
    n = len(matrix)
    row_colours = [0] * n
    col_colours = [1] * n
    for _ in range(2 * n + 2):
        signatures = []
        for i in range(n):
            signatures.append((
                "R", row_colours[i],
                tuple(sorted(col_colours[j] for j in range(n) if matrix[i][j])),
            ))
        for j in range(n):
            signatures.append((
                "C", col_colours[j],
                tuple(sorted(row_colours[i] for i in range(n) if matrix[i][j])),
            ))
        ids = {sig: k for k, sig in enumerate(sorted(set(signatures)))}
        new_rows = [ids[sig] for sig in signatures[:n]]
        new_cols = [ids[sig] for sig in signatures[n:]]
        if new_rows == row_colours and new_cols == col_colours:
            break
        row_colours, col_colours = new_rows, new_cols

    if len(set(row_colours)) == n and len(set(col_colours)) == n:
        row_order = sorted(range(n), key=row_colours.__getitem__)
        col_order = sorted(range(n), key=col_colours.__getitem__)
        payload = {
            "kind": "discrete",
            "n": n,
            "matrix": [
                "".join(str(matrix[i][j]) for j in col_order)
                for i in row_order
            ],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    # Exact for the stable equitable quotient, but not a complete isomorphism
    # invariant when refinement leaves non-singleton cells.
    row_cells = sorted(set(row_colours))
    col_cells = sorted(set(col_colours))
    row_groups = {c: [i for i in range(n) if row_colours[i] == c] for c in row_cells}
    col_groups = {c: [j for j in range(n) if col_colours[j] == c] for c in col_cells}
    quotient_rows = []
    for c in row_cells:
        i = row_groups[c][0]
        quotient_rows.append((
            len(row_groups[c]),
            tuple(sum(matrix[i][j] for j in col_groups[d]) for d in col_cells),
        ))
    quotient_cols = []
    for d in col_cells:
        j = col_groups[d][0]
        quotient_cols.append((
            len(col_groups[d]),
            tuple(sum(matrix[i][j] for i in row_groups[c]) for c in row_cells),
        ))
    payload = {
        "kind": "quotient",
        "n": n,
        "rows": quotient_rows,
        "cols": quotient_cols,
        "row_common": sorted(
            sum(matrix[i][j] and matrix[k][j] for j in range(n))
            for i in range(n) for k in range(i + 1, n)
        ),
        "col_common": sorted(
            sum(matrix[i][j] and matrix[i][k] for i in range(n))
            for j in range(n) for k in range(j + 1, n)
        ),
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def canonical_key(inst: dict) -> str:
    """Key invariant under row/column permutations and exchange of the cliques."""
    matrix = inst["matrix"]
    transposed = [list(row) for row in zip(*matrix)]
    structural = min(
        _wl_orientation_signature(matrix),
        _wl_orientation_signature(transposed),
    )
    return "wl-bipartite-v1:" + hashlib.sha256(structural.encode()).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase the permutation CSP dimension, its genuine exponential axis."""
    n = params.get("n")
    if isinstance(n, bool) or not isinstance(n, int) or n < 4:
        return None
    return {"n": n + max(8, n // 3)}


def _hungarian(cost: list[list[int]]) -> list[int]:
    """Minimum-cost square assignment, used only by the outlier attack."""
    n = len(cost)
    u = [0] * (n + 1)
    v = [0] * (n + 1)
    p = [0] * (n + 1)
    way = [0] * (n + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [10**30] * (n + 1)
        used = [False] * (n + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = 10**30
            j1 = 0
            for j in range(1, n + 1):
                if not used[j]:
                    cur = cost[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j
            for j in range(n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    assignment = [-1] * n
    for j in range(1, n + 1):
        assignment[p[j] - 1] = j - 1
    return assignment


def _attack_outlier(inst: dict) -> list[int]:
    """Exploit the degree-sum concentration that planting could have leaked."""
    matrix = inst["matrix"]
    n = inst["n"]
    allowed = [[1 - x for x in row] for row in matrix]
    row_degree = [sum(row) for row in allowed]
    col_degree = [sum(allowed[i][j] for i in range(n)) for j in range(n)]
    allowed_count = sum(row_degree)
    both_estimate = 2 * (allowed_count - n) / (n * (n - 1)) - 1
    both_estimate = min(1.0, max(0.0, both_estimate))
    target = n + 1 + both_estimate * (n - 1)
    huge = 10**9
    cost = [
        [
            int(1000 * (row_degree[i] + col_degree[j] - target) ** 2)
            if allowed[i][j] else huge
            for j in range(n)
        ]
        for i in range(n)
    ]
    return [j + 1 for j in _hungarian(cost)]


def _compatible_options(matrix: list[list[int]], assignment: list[int],
                        unused: set[int], i: int) -> list[int]:
    n = len(matrix)
    return [
        j for j in unused
        if matrix[i][j] == 0 and all(
            matrix[i][assignment[h]] == 0 or matrix[h][j] == 0
            for h in range(n) if assignment[h] >= 0
        )
    ]


def _attack_greedy(inst: dict) -> list[int] | None:
    """MRV plus least-constraining-value, with no backtracking."""
    matrix = inst["matrix"]
    n = inst["n"]
    unassigned = set(range(n))
    unused = set(range(n))
    assignment = [-1] * n
    while unassigned:
        domains = {
            i: _compatible_options(matrix, assignment, unused, i)
            for i in unassigned
        }
        if any(not domain for domain in domains.values()):
            return None
        size = min(map(len, domains.values()))
        i = min(i for i, domain in domains.items() if len(domain) == size)

        def future_score(j: int) -> int:
            return sum(
                matrix[r][c] == 0 and c != j
                and (matrix[r][j] == 0 or matrix[i][c] == 0)
                for r in unassigned if r != i
                for c in unused if c != j
            )

        j = max(domains[i], key=lambda c: (future_score(c), -c))
        assignment[i] = j
        unassigned.remove(i)
        unused.remove(j)
    return [j + 1 for j in assignment]


def _attack_random_restart(inst: dict, rng: random.Random,
                           restarts: int = 64) -> list[int] | None:
    """Randomized incremental MRV search without backtracking."""
    matrix = inst["matrix"]
    n = inst["n"]
    for _ in range(restarts):
        unassigned = set(range(n))
        unused = set(range(n))
        assignment = [-1] * n
        while unassigned:
            domains = {
                i: _compatible_options(matrix, assignment, unused, i)
                for i in unassigned
            }
            if any(not domain for domain in domains.values()):
                break
            size = min(map(len, domains.values()))
            rows = [i for i, domain in domains.items() if len(domain) == size]
            i = rng.choice(rows)
            j = rng.choice(domains[i])
            assignment[i] = j
            unassigned.remove(i)
            unused.remove(j)
        else:
            return [j + 1 for j in assignment]
    return None


def _relabel(inst: dict, row_order: list[int], col_order: list[int],
             swap_sides: bool) -> dict:
    """Carry an instance and its witness through a genuine graph relabelling."""
    n = inst["n"]
    matrix = [
        [inst["matrix"][row_order[i]][col_order[j]] for j in range(n)]
        for i in range(n)
    ]
    old_answer = [x - 1 for x in inst["answer"]]
    inverse_col = [0] * n
    for new_j, old_j in enumerate(col_order):
        inverse_col[old_j] = new_j
    answer = [inverse_col[old_answer[row_order[i]]] for i in range(n)]
    if swap_sides:
        matrix = [list(row) for row in zip(*matrix)]
        inverse_answer = [0] * n
        for i, j in enumerate(answer):
            inverse_answer[j] = i
        answer = inverse_answer
    return {
        "family": inst["family"],
        "n": n,
        "matrix": matrix,
        "answer": [x + 1 for x in answer],
    }


def selftest() -> dict:
    """Run all mandatory generation, verification, attack, and symmetry gates."""
    report: dict[str, Any] = {
        "paper": "2008.09415",
        "family": "acyclic colouring of co-bipartite graphs",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: every named preset, several unrelated seeds.
    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2, 17, 99):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=7001, **shipping)
    planted = list(inst["answer"])

    # G2: five corruption types, all with distinct rejection reasons.
    single_pair = None
    for i in range(inst["n"]):
        for j in range(i + 1, inst["n"]):
            pi, pj = planted[i] - 1, planted[j] - 1
            if inst["matrix"][i][pj] or inst["matrix"][j][pi]:
                single_pair = (i, j)
                break
        if single_pair:
            break
    swapped = planted.copy()
    if single_pair:
        i, j = single_pair
        swapped[i], swapped[j] = swapped[j], swapped[i]
    duplicate = planted.copy()
    duplicate[1] = duplicate[0]
    out_of_range = planted.copy()
    out_of_range[0] = inst["n"] + 1
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    g2_reasons = {name: verify(inst, value)[1] for name, value in corruptions.items()}
    g2_rejected = all(not verify(inst, value)[0] for value in corruptions.values())
    report["G2_rejects_corruption"] = {
        "pass": g2_rejected and len(set(g2_reasons.values())) == len(corruptions),
        "reasons": g2_reasons,
        "distinct_reasons": len(set(g2_reasons.values())),
    }

    # G3: prose, Markdown, and whitespace around a real witness.
    body = ", ".join(map(str, planted))
    model_style = f"I checked every pair.\n```text\n<answer>\n {body}\n</answer>\n```\nDone."
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_length": len(parsed) if isinstance(parsed, list) else None,
    }

    # G4: the prior already obeys shape, permutation, and all cross-nonedge
    # constraints.  Only the pairwise acyclicity condition remains unplanted.
    total = 200_000
    per_seed = []
    hits = 0
    for instance_seed in (301, 302, 303, 304):
        guess_inst = make_instance(seed=instance_seed, **shipping)
        guess_rng = random.Random(9_000_000 + instance_seed)
        local_hits = 0
        for _ in range(total // 4):
            candidate = random_candidate(guess_inst, guess_rng)
            if verify(guess_inst, candidate)[0]:
                local_hits += 1
        hits += local_hits
        per_seed.append({"seed": instance_seed, "hits": local_hits, "total": total // 4})
    rate = hits / total
    report["G4_guess_resistance"] = {
        "pass": rate < 1e-6,
        "hits": hits,
        "total": total,
        "rate": rate,
        "prior": "randomized perfect matchings of the visible cross-nonedges",
        "naive_search_space": search_space(inst),
        "per_instance": per_seed,
    }

    # G5: an exact audit at the largest enumerated size.
    sparse_inst = make_instance(n=9, seed=1)
    solution_count = enumerate_all(sparse_inst)
    sparse_space = search_space(sparse_inst)
    sparse_fraction = solution_count / sparse_space if solution_count is not None else None
    report["G5_sparse"] = {
        "pass": solution_count is not None and sparse_fraction < 1e-4,
        "n": 9,
        "seed": 1,
        "valid_answers": solution_count,
        "naive_candidates": sparse_space,
        "fraction": sparse_fraction,
    }

    # G6: attacks exploiting the actual planting mechanism.
    attack_rows: dict[str, Any] = {}
    attack_solvers = {
        "degree_sum_outlier": lambda x, s: _attack_outlier(x),
        "deterministic_greedy": lambda x, s: _attack_greedy(x),
        "random_mrv_64_restarts": lambda x, s: _attack_random_restart(
            x, random.Random(800_000 + s), 64
        ),
    }
    for name, attack in attack_solvers.items():
        solved_seeds = []
        produced = 0
        for seed in range(8):
            attack_inst = make_instance(seed=seed, **shipping)
            candidate = attack(attack_inst, seed)
            if candidate is not None:
                produced += 1
                if verify(attack_inst, candidate)[0]:
                    solved_seeds.append(seed)
        attack_rows[name] = {
            "attempted_seeds": 8,
            "candidates_produced": produced,
            "solved": len(solved_seeds),
            "solved_seeds": solved_seeds,
            "pass": not solved_seeds,
        }
    report["G6_adversary_panel"] = {
        "pass": all(row["pass"] for row in attack_rows.values()),
        "attacks": attack_rows,
    }

    # G7: construction and verification at twice the shipping dimension.
    doubled_n = 2 * shipping["n"]
    doubled = make_instance(n=doubled_n, seed=123456)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == doubled_n,
        "shipping_n": shipping["n"],
        "doubled_n": doubled_n,
        "vertices": 2 * doubled_n,
        "verify_reason": doubled_why,
    }

    # G8: independent row/column permutations, their composition, side swap,
    # and every such combination.  The witness is carried through each map.
    transformed_count = 0
    carried_verified = 0
    invariant_failures = []
    unrelated_keys = []
    for seed in range(20):
        key_inst = make_instance(seed=10_000 + seed, **shipping)
        original_key = canonical_key(key_inst)
        unrelated_keys.append(original_key)
        symmetry_rng = random.Random(90_000 + seed)
        row_perm = list(range(key_inst["n"]))
        col_perm = list(range(key_inst["n"]))
        symmetry_rng.shuffle(row_perm)
        symmetry_rng.shuffle(col_perm)
        identity = list(range(key_inst["n"]))
        for use_rows, use_cols, swap_sides in itertools.product((False, True), repeat=3):
            if not (use_rows or use_cols or swap_sides):
                continue
            changed = _relabel(
                key_inst,
                row_perm if use_rows else identity,
                col_perm if use_cols else identity,
                swap_sides,
            )
            transformed_count += 1
            ok, _ = verify(changed, changed["answer"])
            carried_verified += int(ok)
            if canonical_key(changed) != original_key:
                invariant_failures.append({
                    "seed": seed,
                    "rows": use_rows,
                    "cols": use_cols,
                    "swap": swap_sides,
                })
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": (
            not invariant_failures
            and carried_verified == transformed_count
            and distinct_keys == 20
        ),
        "source_seeds": 20,
        "transforms_tested": transformed_count,
        "invariant": transformed_count - len(invariant_failures),
        "carried_answers_verified": carried_verified,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "failures": invariant_failures,
        "fallback_caveat": "WL equitable quotient can over-collapse rare symmetric graphs",
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
