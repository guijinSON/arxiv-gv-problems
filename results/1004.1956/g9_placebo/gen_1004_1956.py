"""Verified planted Circular-Ordering generator for arXiv:1004.1956.

The paper's Pi_7 constraints are cyclically oriented triples.  This module
samples a circular order first and then draws a degree-balanced collection of
triples oriented consistently with it.  The witness is therefore known by
inverse generation, while verification is exact cyclic-order substitution.
"""

from __future__ import annotations

import cmath
import hashlib
import heapq
import itertools
import json
import math
import os
import random
import re
import time


TRACK: str = "A"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "permutation",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite variable set",
        "multiset of cyclically oriented ternary permutation constraints",
        "linear representation of a circular ordering",
    ],
    "verification_operations": [
        "exact permutation validation",
        "integer position lookup",
        "exact cyclic-orientation comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "reduction recognition",
    "intuition_description": (
        "Recognize each cyclic triple as a directed 3-cycle whose satisfied "
        "orders have exactly two forward arcs; without that recognition the "
        "ternary constraints offer no useful global score."
    ),
    "hardness_basis": (
        "Track A: Section 3 Table 1 gives NP-completeness of Pi_7 Circular "
        "Ordering and Section 7 preserves it as directed 3-cycles; the "
        "shipping regular planted regime has k=m/2 growing linearly, has no "
        "known efficient exact recovery method, and its measured capped "
        "subset-DP cost is reported in G5."
    ),
    "max_answer_tokens": 34,
}

NATIVE: dict = {
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

DIFFICULTY: dict = {
    "easy": {"n": 48, "rounds": 10},
}
SHIPPING_DIFFICULTY: str = "easy"

STRUCTURAL_HINT: str = (
    "Each oriented triple is a directed 3-cycle, and its accepted cyclic "
    "orientations have two forward arcs."
)
PLACEBO_HINT: str = (
    "Keep the clockwise convention and zero-based variable labels consistent "
    "while checking every displayed triple."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A comma-separated permutation of all n variable labels, represented "
        "as a JSON-native list of n integers, with label 0 first to remove the "
        "otherwise free cyclic rotation."
    ),
    "bounds": {
        "length": "n",
        "labels": "all integers 0 through n-1 exactly once",
        "normalization": "label 0 is first",
        "max_variables": 240,
        "candidate_count": "(n-1)!",
    },
}

# These fields are replaced only after the script-owned oracle runs exist.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}

NOTES: str = r"""
Definition. Section 3 defines a ternary Pi-CSP constraint (v1,v2,v3) as
satisfied when the variables appear according to a permutation in Pi. For
Pi_7={(123),(231),(312)}, this is exactly one orientation of a circular order:
starting at v1 and moving clockwise, v2 is met before v3. Table 1 records that
satisfying all Pi_7 constraints is NP-complete. A uniformly random order
satisfies one half of them, so requiring all m constraints is the Pi_7-AA
instance with k=m/2. The generated m is always even.

Step-0 algorithm check. The paper's main Theorem 5 gives O(k^2)-variable
kernels and hence an FPT route when k is small. This generator deliberately
uses k=m/2 with m linear in n, so k grows. The easy Pi in {empty,S_3}, the
polynomial exact-feasibility languages Pi_0 through Pi_3 in Table 1, and fixed
k are all avoided. In particular, the prior-triage idea of generating only
Pi_0 triples consistent with a hidden linear order would be solved by the
polynomial feasibility algorithm in the same table.

Certificate production. A uniformly random circular ordering, normalized to
start at variable 0, is sampled before any constraints. Each round partitions
all variables into triples, so every variable has exactly the same constraint
degree. Every triple is oriented by the sampled circle and then independently
cyclically rotated, which preserves the Pi_7 constraint while removing tuple
position marginals. Thus the stored ordering is known by inverse generation;
no generated instance is solved to obtain it.

Hardness claim and domain attack. Worst-case NP-completeness alone does not
prove this planted distribution hard. Section 7 gives the construction-aware
standard attack: replace (u,v,w) by arcs u->v, v->w, w->u. A constraint
contributes two forward arcs exactly when satisfied and one otherwise, so an
all-satisfying order has the maximum possible 2m forward arcs. Exact subset
dynamic programming costs O(n*2^n); selftest runs its recurrence with a wide
beam and records the actual truncated-state cost. It also runs tuple-role,
greedy insertion, random-restart local search, and a skew-adjacency spectral
attack. All must fail on eight shipping seeds. This is empirical evidence for
the generated distribution, not an average-case theorem.

Canonicalization. Tuple order, cyclic rotation within a tuple, arbitrary
variable relabelling, and simultaneous reversal of the circle and every
constraint are presentation symmetries. canonical_key hashes a directed
two-step/common-neighborhood invariant of the Section 7 arc multigraph and
minimizes it against global reversal. It is not a complete directed-graph
isomorphism algorithm and can theoretically miss duplicate presentations;
that limitation is repeated in README.md.
""".strip()


_ANSWER_RE = re.compile(
    r"<answer\b[^>]*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL
)


def _valid_parameters(n: int, rounds: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 6 or n % 6:
        raise ValueError("n must be an integer multiple of 6 and at least 6")
    if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 1:
        raise ValueError("rounds must be a positive integer")
    if rounds > (n - 1) * (n - 2) // 2:
        raise ValueError("rounds exceed the number of triples available per variable")


def _is_positive_cycle(
    positions: list[int], triple: list[int] | tuple[int, int, int], n: int
) -> bool:
    a, b, c = triple
    return (positions[b] - positions[a]) % n < (positions[c] - positions[a]) % n


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a regular planted Pi_7 Circular-Ordering instance."""
    if set(params) != {"rounds"}:
        unknown = sorted(set(params) - {"rounds"})
        missing = "rounds" not in params
        detail = ("missing rounds" if missing else "unknown parameters: " + ", ".join(unknown))
        raise TypeError(detail)
    rounds = params["rounds"]
    _valid_parameters(n, rounds)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")

    rng = random.Random(seed)
    answer = [0] + rng.sample(range(1, n), n - 1)
    positions = [0] * n
    for i, variable in enumerate(answer):
        positions[variable] = i

    constraints: list[list[int]] = []
    used_unordered: set[tuple[int, int, int]] = set()
    for _ in range(rounds):
        groups = None
        for _attempt in range(2_000):
            shuffled = list(range(n))
            rng.shuffle(shuffled)
            proposed = [
                tuple(sorted(shuffled[i : i + 3])) for i in range(0, n, 3)
            ]
            if all(group not in used_unordered for group in proposed):
                groups = proposed
                break
        if groups is None:
            raise RuntimeError("could not draw another duplicate-free triple partition")
        for group in groups:
            cyclic = sorted(group, key=positions.__getitem__)
            rotation = rng.randrange(3)
            oriented = cyclic[rotation:] + cyclic[:rotation]
            constraints.append(oriented)
            used_unordered.add(group)
    rng.shuffle(constraints)

    m = len(constraints)
    return {
        "family": "Pi_7 Circular Ordering Above Average",
        "pi": [[1, 2, 3], [2, 3, 1], [3, 1, 2]],
        "n": n,
        "rounds": rounds,
        "constraint_count": m,
        "above_average_k": m // 2,
        "constraints": constraints,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Return the complete native Circular-Ordering problem statement."""
    n = inst["n"]
    rows = "\n".join(
        f"  {i}: {a} {b} {c}"
        for i, (a, b, c) in enumerate(inst["constraints"])
    )
    example = ", ".join(str(i) for i in range(n))
    hint = ""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        hint = "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        hint = "\n\nHint: " + PLACEBO_HINT

    return f"""CIRCULAR ORDERING ABOVE AVERAGE (Pi_7)

The variables are the integers 0 through {n - 1}. Place every variable exactly
once around an oriented circle. Submit the circle as a linear list read
clockwise, with variable 0 first. Requiring 0 first removes only cyclic
rotation; it does not restrict which circles are allowed. Reflection is not
free: reversing a submitted list usually changes whether constraints hold.

An oriented constraint is a row (a,b,c) of three distinct variables. It is
satisfied exactly when, starting at a and moving clockwise, b is encountered
strictly before c. Equivalently, the clockwise restrictions (a,b,c), (b,c,a),
and (c,a,b) describe the same accepted orientation; the reverse orientation is
rejected. There are no repeated variables inside a row and no repeated
unordered triples. All {inst['constraint_count']} displayed constraints must be
satisfied. Since a uniformly random circular order satisfies half of the rows,
this is the paper's Pi_7 Above-Average target m/2+k with m={inst['constraint_count']}
and k={inst['above_average_k']}.

Constraint rows are 0-indexed; row order has no meaning:
{rows}{hint}

Give your final answer inside <answer></answer> tags as exactly {n}
comma-separated base-10 integers: every label 0 through {n - 1} exactly once,
with 0 first. Do not use brackets, and do not repeat a label.
Example of the required syntax (not necessarily a solution):
<answer>{example}</answer>
Output nothing else inside the tags."""


def parse_answer(text: str) -> object | None:
    """Parse the delimited comma-separated permutation, tolerating prose/fences."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    if body.startswith("```") and body.endswith("```"):
        lines = body.splitlines()
        if len(lines) >= 3:
            lines = lines[1:-1]
            body = "\n".join(lines).strip()
    if not body:
        return []
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1].strip()
    pieces = [piece.strip() for piece in body.split(",")]
    if any(not re.fullmatch(r"[+-]?\d+", piece) for piece in pieces):
        return None
    try:
        return [int(piece, 10) for piece in pieces]
    except (TypeError, ValueError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid circular ordering; never consult ``inst['answer']``."""
    n = inst["n"]
    if not isinstance(answer, list):
        return False, "answer must be a list of integers"
    if not answer:
        return False, "answer is empty"
    if len(answer) != n:
        return False, f"wrong length: expected {n}, got {len(answer)}"
    for i, value in enumerate(answer):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"entry {i} is not an integer"
        if value < 0 or value >= n:
            return False, f"entry {i} is outside the range 0..{n - 1}"
    if len(set(answer)) != n:
        return False, "a variable label is duplicated"
    if answer[0] != 0:
        return False, "the circular ordering is not normalized with variable 0 first"

    positions = [0] * n
    for i, variable in enumerate(answer):
        positions[variable] = i
    for row, triple in enumerate(inst["constraints"]):
        if not _is_positive_cycle(positions, triple, n):
            return False, f"constraint row {row} has the reverse cyclic orientation"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from normalized circular orders, the stated language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    return [0] + rng.sample(range(1, inst["n"]), inst["n"] - 1)


def search_space(inst: dict) -> int | None:
    return math.factorial(inst["n"] - 1)


def enumerate_all(inst: dict) -> int | None:
    """Count every valid normalized circle when at most 9! are possible."""
    n = inst["n"]
    if n > 10:
        return None
    count = 0
    for tail in itertools.permutations(range(1, n)):
        count += int(verify(inst, [0, *tail])[0])
    return count


def _arc_matrix(inst: dict) -> list[list[int]]:
    n = inst["n"]
    matrix = [[0] * n for _ in range(n)]
    for a, b, c in inst["constraints"]:
        matrix[a][b] += 1
        matrix[b][c] += 1
        matrix[c][a] += 1
    return matrix


def _invariant_blob(matrix: list[list[int]]) -> bytes:
    """A relabelling-invariant directed two-step signature, not a labeling."""
    n = len(matrix)
    signatures = []
    for u in range(n):
        for v in range(n):
            if u == v:
                continue
            two_uv = 0
            two_vu = 0
            common_out = 0
            common_in = 0
            mixed = 0
            for w in range(n):
                two_uv += matrix[u][w] * matrix[w][v]
                two_vu += matrix[v][w] * matrix[w][u]
                common_out += matrix[u][w] * matrix[v][w]
                common_in += matrix[w][u] * matrix[w][v]
                mixed += matrix[u][w] * matrix[w][u] * (
                    matrix[v][w] + matrix[w][v]
                )
            signatures.append(
                (
                    matrix[u][v], matrix[v][u], two_uv, two_vu,
                    common_out, common_in, mixed,
                )
            )
    signatures.sort()
    payload = json.dumps(signatures, separators=(",", ":")).encode()
    return hashlib.sha256(payload).digest()


def canonical_key(inst: dict) -> str:
    """Cheap invariant under relabelling, tuple rotation/order, and reflection."""
    matrix = _arc_matrix(inst)
    direct = _invariant_blob(matrix)
    transpose = _invariant_blob([list(row) for row in zip(*matrix)])
    header = f"Pi7;n={inst['n']};m={inst['constraint_count']}|".encode()
    return hashlib.sha256(header + min(direct, transpose)).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Tighten at fixed answer length, then enlarge n while under the caps."""
    if not isinstance(params, dict) or set(params) != {"n", "rounds"}:
        return None
    n = params["n"]
    rounds = params["rounds"]
    _valid_parameters(n, rounds)
    target = max(rounds, math.ceil(3.0 * (math.log2(n) - 1.25)))
    if rounds < target + 1:
        harder_rounds = rounds + 1
        return {"n": n, "rounds": harder_rounds}
    if n < 240:
        harder_n = min(240, n + 24)
        harder_n -= harder_n % 6
        harder_rounds = max(
            rounds + 1, math.ceil(3.0 * (math.log2(harder_n) - 1.25))
        )
        return {"n": harder_n, "rounds": harder_rounds}
    return "cap_bound"


def _arc_score(order: list[int] | tuple[int, ...], matrix: list[list[int]]) -> int:
    score = 0
    for i, u in enumerate(order):
        row = matrix[u]
        for v in order[i + 1 :]:
            score += row[v]
    return score


def _best_orientation(candidates: list[list[int]], inst: dict) -> list[int]:
    matrix = _arc_matrix(inst)
    normalized = []
    for candidate in candidates:
        cut = candidate.index(0)
        candidate = candidate[cut:] + candidate[:cut]
        normalized.append(candidate)
        normalized.append([0] + list(reversed(candidate[1:])))
    return max(normalized, key=lambda order: _arc_score(order, matrix))


def _outlier_role_attack(inst: dict) -> tuple[list[int], int]:
    """Try to turn tuple-position frequencies into circular phases."""
    n = inst["n"]
    counts = [[0, 0, 0] for _ in range(n)]
    operations = 0
    for triple in inst["constraints"]:
        for role, variable in enumerate(triple):
            counts[variable][role] += 1
            operations += 1
    omega = complex(-0.5, math.sqrt(3.0) / 2.0)
    phases = []
    for variable, row in enumerate(counts):
        value = row[0] + omega * row[1] + omega * omega * row[2]
        phases.append((cmath.phase(value) if value else 0.0, variable))
    candidate = [variable for _, variable in sorted(phases)]
    return _best_orientation([candidate], inst), operations + n


def _greedy_insertion_attack(inst: dict) -> tuple[list[int], int]:
    """Insert variables where the Section-7 arc score rises the most."""
    n = inst["n"]
    matrix = _arc_matrix(inst)
    role = [[0, 0, 0] for _ in range(n)]
    for triple in inst["constraints"]:
        for j, variable in enumerate(triple):
            role[variable][j] += 1
    remaining = sorted(range(1, n), key=lambda v: (role[v], v))
    order = [0]
    operations = 0
    for variable in remaining:
        best_gain = None
        best_position = 1
        for position in range(1, len(order) + 1):
            gain = 0
            for u in order[:position]:
                gain += matrix[u][variable]
                operations += 1
            for u in order[position:]:
                gain += matrix[variable][u]
                operations += 1
            if best_gain is None or gain > best_gain:
                best_gain = gain
                best_position = position
        order.insert(best_position, variable)
    return order, operations


def _spectral_attack(inst: dict, iterations: int = 96) -> tuple[list[int], int]:
    """Phase-sort a leading vector of i(A-A^T), a Hermitian matrix."""
    n = inst["n"]
    matrix = _arc_matrix(inst)
    vector = [
        complex(
            math.cos(2.0 * math.pi * (i + 0.371) / n),
            math.sin(2.0 * math.pi * (i + 0.371) / n),
        )
        for i in range(n)
    ]
    operations = 0
    for _ in range(iterations):
        nxt = []
        for i in range(n):
            value = 0j
            for j in range(n):
                weight = matrix[i][j] - matrix[j][i]
                if weight:
                    value += 1j * weight * vector[j]
                    operations += 1
            nxt.append(value)
        norm = math.sqrt(sum(abs(value) ** 2 for value in nxt))
        if norm == 0.0:
            break
        vector = [value / norm for value in nxt]
    phase_order = sorted(range(n), key=lambda i: (cmath.phase(vector[i]), i))
    return _best_orientation([phase_order], inst), operations


def _random_restart_attack(
    inst: dict, rng: random.Random, restarts: int = 32, sweeps: int = 6
) -> tuple[list[int], int]:
    """Random permutations followed by adjacent-swap hill climbing."""
    matrix = _arc_matrix(inst)
    n = inst["n"]
    best_order = list(range(n))
    best_score = _arc_score(best_order, matrix)
    operations = n * n
    for _ in range(restarts):
        order = [0] + rng.sample(range(1, n), n - 1)
        score = _arc_score(order, matrix)
        operations += n * n
        for _sweep in range(sweeps):
            improved = False
            for i in range(1, n - 1):
                candidate = list(order)
                candidate[i], candidate[i + 1] = candidate[i + 1], candidate[i]
                candidate_score = _arc_score(candidate, matrix)
                operations += n * n
                if candidate_score > score:
                    order, score = candidate, candidate_score
                    improved = True
            if not improved:
                break
        if score > best_score:
            best_order, best_score = order, score
    return best_order, operations


def _subset_dp_beam_attack(
    inst: dict, width: int = 256
) -> tuple[list[int], int, int]:
    """Run the exact maximum-acyclic-subgraph subset recurrence with a beam.

    Without truncation this is the standard O(n*2^n) exact dynamic program.
    The beam makes the shipping attack executable and records how much of the
    state space was actually explored.
    """
    n = inst["n"]
    matrix = _arc_matrix(inst)
    beam: list[tuple[int, tuple[int, ...], int]] = [(0, (0,), 1)]
    operations = 0
    states = 1
    for _depth in range(1, n):
        best_by_mask: dict[int, tuple[int, tuple[int, ...], int]] = {}
        for score, order, mask in beam:
            for variable in range(1, n):
                if mask & (1 << variable):
                    continue
                gain = 0
                for u in order:
                    gain += matrix[u][variable]
                    operations += 1
                new_mask = mask | (1 << variable)
                state = (score + gain, order + (variable,), new_mask)
                previous = best_by_mask.get(new_mask)
                if previous is None or state[0] > previous[0]:
                    best_by_mask[new_mask] = state
        states += len(best_by_mask)
        beam = heapq.nlargest(width, best_by_mask.values(), key=lambda row: row[0])
    best = max(beam, key=lambda row: row[0])
    return list(best[1]), states, operations


def _transform_instance(
    inst: dict,
    mapping: list[int] | None = None,
    row_order: list[int] | None = None,
    rotations: list[int] | None = None,
    reflect: bool = False,
) -> dict:
    """Apply presentation symmetries and carry the planted witness."""
    n = inst["n"]
    if mapping is None:
        mapping = list(range(n))
    if row_order is None:
        row_order = list(range(len(inst["constraints"])))
    if rotations is None:
        rotations = [0] * len(inst["constraints"])

    transformed = []
    for new_row, old_row in enumerate(row_order):
        triple = [mapping[v] for v in inst["constraints"][old_row]]
        if reflect:
            triple = [triple[0], triple[2], triple[1]]
        shift = rotations[old_row] % 3
        transformed.append(triple[shift:] + triple[:shift])

    answer = [mapping[v] for v in inst["answer"]]
    if reflect:
        answer = [answer[0]] + list(reversed(answer[1:]))
    cut = answer.index(0)
    answer = answer[cut:] + answer[:cut]
    moved = dict(inst)
    moved["constraints"] = transformed
    moved["answer"] = answer
    return moved


def _answer_metrics(answer: list[int]) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))
    return len(encoded), math.ceil(len(encoded) / 4), len(answer)


def selftest() -> dict:
    """Run every correctness, density, attack, scale, and symmetry gate."""
    report: dict = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            try:
                restored = json.loads(json.dumps(inst["answer"]))
            except (TypeError, ValueError) as exc:
                g1_failures.append(f"{preset}/{seed}: JSON error {exc}")
            else:
                if restored != inst["answer"]:
                    g1_failures.append(f"{preset}/{seed}: JSON round-trip changed answer")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=123, **shipping)
    answer = ship["answer"]

    swapped = None
    for i in range(1, len(answer)):
        for j in range(i + 1, len(answer)):
            trial = list(answer)
            trial[i], trial[j] = trial[j], trial[i]
            if verify(ship, trial)[1].startswith("constraint row"):
                swapped = trial
                break
        if swapped is not None:
            break
    if swapped is None:
        swapped = [answer[1], answer[0], *answer[2:]]
    duplicate = list(answer)
    duplicate[-1] = duplicate[-2]
    out_of_range = list(answer)
    out_of_range[-1] = ship["n"]
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    corruption_results = {
        name: {
            "accepted": verify(ship, candidate)[0],
            "reason": verify(ship, candidate)[1],
        }
        for name, candidate in corruptions.items()
    }
    reasons = [row["reason"] for row in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": (
            all(not row["accepted"] for row in corruption_results.values())
            and len(set(reasons)) == len(reasons)
        ),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    body = ", ".join(str(value) for value in answer)
    realistic = (
        "The directed-cycle score reaches the target.\n```text\n"
        f"<answer>\n{body}\n</answer>\n```\n"
        "This is normalized at variable zero."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(ship, parsed)[0]
        and parse_answer("unrelated garbage") is None,
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("unrelated garbage") is None,
    }

    guess_rng = random.Random(0x10041956)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_wall = time.perf_counter() - guess_start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_fraction,
        "candidate_space": search_space(ship),
        "sampling_prior": "uniform normalized circular orders (all permutations with 0 first)",
        "wall_clock_sec": round(guess_wall, 6),
    }

    attack_names = (
        "outlier_tuple_role",
        "greedy_arc_insertion",
        "random_restart_adjacent_hillclimb_32",
        "spectral_skew_adjacency",
        "subset_dp_beam_256",
    )
    attacks = {
        name: {
            "successes": 0,
            "attempts": 0,
            "operations": 0,
            "states": 0,
            "wall_clock_sec": 0.0,
        }
        for name in attack_names
    }
    for seed in range(800, 808):
        current = make_instance(seed=seed, **shipping)

        start = time.perf_counter()
        candidate, operations = _outlier_role_attack(current)
        elapsed = time.perf_counter() - start
        row = attacks[attack_names[0]]
        row["attempts"] += 1
        row["successes"] += int(verify(current, candidate)[0])
        row["operations"] += operations
        row["wall_clock_sec"] += elapsed

        start = time.perf_counter()
        candidate, operations = _greedy_insertion_attack(current)
        elapsed = time.perf_counter() - start
        row = attacks[attack_names[1]]
        row["attempts"] += 1
        row["successes"] += int(verify(current, candidate)[0])
        row["operations"] += operations
        row["wall_clock_sec"] += elapsed

        start = time.perf_counter()
        candidate, operations = _random_restart_attack(
            current, random.Random(seed ^ 0xC1AC1E)
        )
        elapsed = time.perf_counter() - start
        row = attacks[attack_names[2]]
        row["attempts"] += 1
        row["successes"] += int(verify(current, candidate)[0])
        row["operations"] += operations
        row["wall_clock_sec"] += elapsed

        start = time.perf_counter()
        candidate, operations = _spectral_attack(current)
        elapsed = time.perf_counter() - start
        row = attacks[attack_names[3]]
        row["attempts"] += 1
        row["successes"] += int(verify(current, candidate)[0])
        row["operations"] += operations
        row["wall_clock_sec"] += elapsed

        start = time.perf_counter()
        candidate, states, operations = _subset_dp_beam_attack(current)
        elapsed = time.perf_counter() - start
        row = attacks[attack_names[4]]
        row["attempts"] += 1
        row["successes"] += int(verify(current, candidate)[0])
        row["operations"] += operations
        row["states"] += states
        row["wall_clock_sec"] += elapsed

    for row in attacks.values():
        row["wall_clock_sec"] = round(row["wall_clock_sec"], 6)
    all_failed = all(row["successes"] == 0 for row in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attacks,
        "domain_standard_attack": "subset_dp_beam_256",
        "domain_standard_full_complexity": "O(n*2^n) states for exact subset DP",
        "construction_aware_attack": "spectral_skew_adjacency",
    }

    demo = make_instance(seed=123, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    strongest_name, strongest = max(
        attacks.items(), key=lambda item: item[1]["operations"]
    )
    domain_baseline = attacks["subset_dp_beam_256"]
    report["G5_density_and_baseline"] = {
        "pass": guess_hits == 0 and demo_count is not None and demo_count > 0 and all_failed,
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": guess_total,
        "shipping_sampled_density": guess_fraction,
        "shipping_candidate_space": search_space(ship),
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "demo_n": demo["n"],
        "strongest_attack": strongest_name,
        "strongest_attack_wall_clock_sec": strongest["wall_clock_sec"],
        "strongest_attack_operations": strongest["operations"],
        "strongest_attack_states": strongest["states"],
        "domain_baseline": "Section-7 maximum-acyclic-subgraph subset-DP recurrence, beam width 256",
        "domain_baseline_wall_clock_sec": domain_baseline["wall_clock_sec"],
        "domain_baseline_operations": domain_baseline["operations"],
        "domain_baseline_states": domain_baseline["states"],
    }

    ladder = [
        (params["n"], params["rounds"], search_space(make_instance(seed=2, **params)))
        for params in DIFFICULTY.values()
    ]
    doubled_params = {
        "n": 2 * shipping["n"],
        "rounds": shipping["rounds"] + 5,
    }
    doubled = make_instance(seed=909, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    harder_fixed = escalate(shipping)
    report["G7_scales"] = {
        "pass": (
            doubled_ok
            and isinstance(harder_fixed, dict)
            and harder_fixed != shipping
            and harder_fixed["rounds"] > shipping["rounds"]
            and all(ladder[i][2] <= ladder[i + 1][2] for i in range(len(ladder) - 1))
        ),
        "preset_n_rounds_space": {
            name: {"n": row[0], "rounds": row[1], "space": row[2]}
            for name, row in zip(DIFFICULTY, ladder)
        },
        "fixed_length_escalation": harder_fixed,
        "doubled_params": doubled_params,
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
    }

    invariant_checks = 0
    witness_checks = 0
    invariant_failures = []
    unrelated_keys = []
    for seed in range(20):
        original = make_instance(n=30, rounds=8, seed=20_000 + seed)
        base_key = canonical_key(original)
        unrelated_keys.append(base_key)
        rng = random.Random(30_000 + seed)
        mapping = list(range(original["n"]))
        rng.shuffle(mapping)
        rows = list(range(original["constraint_count"]))
        rng.shuffle(rows)
        rotations = [rng.randrange(3) for _ in rows]
        variants = (
            _transform_instance(original, mapping=mapping),
            _transform_instance(original, row_order=rows, rotations=rotations),
            _transform_instance(
                original, mapping=mapping, row_order=rows, rotations=rotations
            ),
            _transform_instance(
                original, mapping=mapping, row_order=rows,
                rotations=rotations, reflect=True,
            ),
        )
        for number, moved in enumerate(variants):
            invariant_checks += 1
            if canonical_key(moved) != base_key:
                invariant_failures.append(f"key/{seed}/{number}")
            witness_checks += 1
            if not verify(moved, moved["answer"])[0]:
                invariant_failures.append(f"witness/{seed}/{number}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and distinct_keys == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": witness_checks,
        "invariance_failures": invariant_failures,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "transformations": [
            "arbitrary variable relabelling",
            "constraint-row permutation and independent tuple cyclic rotation",
            "composition of relabelling and row/tuple transformations",
            "global reflection with every constraint orientation reversed",
        ],
        "key_caveat": "strong cheap invariant, not complete digraph isomorphism",
    }

    chars, tokens, elements = _answer_metrics(ship["answer"])
    intended_operations = ship["n"]
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        chars <= 2_000
        and elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": G9_ORACLE_RESULTS["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
