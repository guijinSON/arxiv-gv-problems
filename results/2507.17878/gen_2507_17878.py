"""Verified planted monotone 1-in-3-SAT instance generator.

This module is self-contained and uses only the Python standard library.  It
does not perform I/O and does not print when imported.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections import Counter, deque


DIFFICULTY = {
    "demo": {"n": 3, "degree3_pct": 35},
    "easy": {"n": 8, "degree3_pct": 35},
    "medium": {"n": 16, "degree3_pct": 40},
    "hard": {"n": 96, "degree3_pct": 45},
}

SHIPPING_DIFFICULTY = "hard"

NOTES = r"""
Definition source: Section 1 (Introduction) of Bedert--Nakajima--Okrasa--
Zivny, "Strong Sparsification for 1-in-3-SAT via Polynomial Freiman-Ruzsa",
defines monotone 1-in-3-SAT exactly: variables are Boolean and each ordered
triple/3-uniform hyperedge must contain exactly one 1.  The generated clauses
use three distinct variables, and clause order is explicitly immaterial here.

Hard/easy boundary: Section 1 treats this exact CSP as NP-hard.  Section 3
also exposes an important easy attack: every exact constraint has a modulo-2
linear relaxation (the paper swaps 1-in-3 and 2-in-3, which only changes the
right-hand side).  A dense random plant is often isolated by Gaussian
elimination.  This generator therefore keeps m < N, explicitly computes the
affine GF(2) solution space, and makes its dimension grow with n.  Section 4's
reduction from non-monotone to monotone instances does not solve the witness
search.  Section 5's statement that an optimal strong sparsifier can be found
by listing every solution is exponential, not a polynomial-time search
algorithm.  The paper
gives no FPT algorithm for finding an assignment and no closed form for this
search task.

Planting and attacks: variables are incidence sets of size two or three in the
dual exact-cover view.  Exactly one planted variable covers every clause.  True
and false variables receive the same 2/3-degree mixture, so degree is not a
plant marker; stubs are uniformly shuffled and labels, clauses, and positions
are independently shuffled.  The self-test checks (1) degree/position/
co-occurrence outlier scores, (2) a deterministic exact-cover greedy rule,
(3) the canonical GF(2) representative, and (4) randomized greedy restarts.
G4 is stronger than uniform bit guessing: it samples uniformly from all parity
solutions, incorporating the cheapest global consequence of every clause.
""".strip()


_ANSWER_RE = re.compile(r"<answer\s*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL)


def _xor_echelon(n_variables, clauses):
    """Return echelon equations and free columns for Ax=1 over GF(2).

    Each equation is stored as (pivot, lower_mask, rhs), with pivot the largest
    column in that row.  Processing pivots in increasing order reconstructs a
    solution from arbitrary values of the free columns.
    """
    basis = {}
    for clause in clauses:
        lhs = 0
        for variable in clause:
            lhs ^= 1 << (variable - 1)
        row = lhs | (1 << n_variables)
        while row & ((1 << n_variables) - 1):
            current_lhs = row & ((1 << n_variables) - 1)
            pivot = current_lhs.bit_length() - 1
            if pivot in basis:
                row ^= basis[pivot]
            else:
                basis[pivot] = row
                break
        else:
            if (row >> n_variables) & 1:
                raise ValueError("inconsistent parity relaxation")
    pivots = set(basis)
    equations = []
    for pivot in sorted(basis):
        row = basis[pivot]
        lhs = row & ((1 << n_variables) - 1)
        equations.append((pivot, lhs ^ (1 << pivot), (row >> n_variables) & 1))
    free = tuple(i for i in range(n_variables) if i not in pivots)
    return tuple(equations), free


def _materialize_from_free(inst, free_bits):
    value_mask = 0
    for offset, variable in enumerate(inst["xor_free"]):
        if (free_bits >> offset) & 1:
            value_mask |= 1 << variable
    for pivot, lower_mask, rhs in inst["xor_echelon"]:
        bit = rhs ^ ((lower_mask & value_mask).bit_count() & 1)
        if bit:
            value_mask |= 1 << pivot
    return [i + 1 for i in range(inst["n_variables"]) if (value_mask >> i) & 1]


def _connected(n_variables, clauses):
    if not clauses:
        return False
    incident = [[] for _ in range(n_variables)]
    for ci, clause in enumerate(clauses):
        for variable in clause:
            incident[variable - 1].append(ci)
    seen_v = {0}
    seen_c = set()
    queue = deque([(0, 0)])  # 0 for a variable node, 1 for a clause node
    while queue:
        side, index = queue.popleft()
        if side == 0:
            for ci in incident[index]:
                if ci not in seen_c:
                    seen_c.add(ci)
                    queue.append((1, ci))
        else:
            for variable in clauses[index]:
                vi = variable - 1
                if vi not in seen_v:
                    seen_v.add(vi)
                    queue.append((0, vi))
    return len(seen_v) == n_variables and len(seen_c) == len(clauses)


def _build_instance_dict(n_variables, clauses, degree3_pct, answer=None):
    clean_clauses = [list(map(int, clause)) for clause in clauses]
    equations, free = _xor_echelon(n_variables, clean_clauses)
    inst = {
        "family": "planted_monotone_1_in_3_sat",
        "n_variables": int(n_variables),
        "clauses": clean_clauses,
        "degree3_pct": int(degree3_pct),
        "xor_echelon": [list(row) for row in equations],
        "xor_free": list(free),
    }
    if answer is not None:
        inst["answer"] = sorted(map(int, answer))
    return inst


def make_instance(n, seed=0, **params):
    """Plant an exact cover first, then manufacture a monotone 1-in-3 formula.

    ``n`` is the number of variables set to 1 by the planted witness.  The
    rendered formula has exactly ``3*n`` variables.  ``degree3_pct`` controls
    the fraction (rounded to an integer count) of variables of each truth class
    that occur three times; all others occur twice.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    unknown = set(params) - {"degree3_pct"}
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    degree3_pct = params.get("degree3_pct", 35)
    if (isinstance(degree3_pct, bool) or not isinstance(degree3_pct, int)
            or not 10 <= degree3_pct <= 60):
        raise ValueError("degree3_pct must be an integer from 10 through 60")

    rng = random.Random(seed)
    n_variables = 3 * n
    labels = list(range(1, n_variables + 1))
    rng.shuffle(labels)
    planted = labels[:n]
    unselected = labels[n:]

    degree3_true_count = max(1, min(n - 1, (n * degree3_pct + 50) // 100))
    true_degree3 = set(rng.sample(planted, degree3_true_count))
    false_degree3 = set(rng.sample(unselected, 2 * degree3_true_count))
    degrees = {}
    for variable in planted:
        degrees[variable] = 3 if variable in true_degree3 else 2
    for variable in unselected:
        degrees[variable] = 3 if variable in false_degree3 else 2

    true_stubs = [v for v in planted for _ in range(degrees[v])]
    false_stubs_base = [v for v in unselected for _ in range(degrees[v])]
    if len(false_stubs_base) != 2 * len(true_stubs):
        raise AssertionError("unbalanced configuration model")

    clauses = None
    # Reject only defects which the statement rules out.  Repeating the whole
    # pairing preserves uniform treatment of planted and non-planted stubs.
    for _ in range(1000):
        ts = true_stubs[:]
        fs = false_stubs_base[:]
        rng.shuffle(ts)
        rng.shuffle(fs)
        trial = []
        used = set()
        valid = True
        for ci, tv in enumerate(ts):
            f1, f2 = fs[2 * ci], fs[2 * ci + 1]
            if f1 == f2:
                valid = False
                break
            clause_key = tuple(sorted((tv, f1, f2)))
            if clause_key in used:
                valid = False
                break
            used.add(clause_key)
            clause = [tv, f1, f2]
            rng.shuffle(clause)
            trial.append(clause)
        if valid:
            rng.shuffle(trial)
            if _connected(n_variables, trial):
                clauses = trial
                break
    if clauses is None:
        raise RuntimeError("could not sample a simple connected incidence graph")

    return _build_instance_dict(
        n_variables, clauses, degree3_pct, answer=planted
    )


def render(inst):
    """Render a complete problem statement containing all instance data."""
    n_variables = inst["n_variables"]
    clauses = inst["clauses"]
    lines = [
        "MONOTONE 1-IN-3-SAT WITNESS PROBLEM",
        "",
        f"There are {n_variables} Boolean variables x1,...,x{n_variables}.",
        "A variable has value 0 (false) or 1 (true). Each clause below lists",
        "three distinct variable indices and contains no negations. An assignment",
        "satisfies a clause exactly when exactly one of its three variables has",
        "value 1; the other two must have value 0. Find one assignment satisfying",
        "every clause.",
        "",
        "Clause order and the order of indices within a clause do not matter.",
        f"There are {len(clauses)} clauses:",
    ]
    width = max(2, len(str(len(clauses))))
    for number, clause in enumerate(clauses, 1):
        lines.append(f"C{number:0{width}d}: {clause[0]} {clause[1]} {clause[2]}")
    lines.extend([
        "",
        "Output the complete set of indices whose variables have value 1. All",
        f"indices must be integers in the inclusive range 1..{n_variables}. The",
        "list must be nonempty, must contain no repeated index, and may have any",
        "length. Variables omitted from the list are assigned 0. Index order does",
        "not matter. Do not include brackets or explanatory text inside the tags.",
        "",
        "Give your final answer inside <answer></answer> tags, as a comma-separated",
        "list of variable indices.",
        "Example: <answer>3, 17, 42</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text):
    """Extract the last well-formed tagged comma-separated integer list."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if not body or not re.fullmatch(r"[0-9]+(?:\s*,\s*[0-9]+)*", body):
        return None
    try:
        return [int(part.strip()) for part in body.split(",")]
    except (TypeError, ValueError):
        return None


def verify(inst, answer):
    """Accept any satisfying assignment encoded as the indices set to 1."""
    if not isinstance(answer, list):
        return False, "answer must be a list of true-variable indices"
    if not answer:
        return False, "answer selects no variables"
    n_variables = inst.get("n_variables")
    selected = set()
    for value in answer:
        if isinstance(value, bool) or not isinstance(value, int):
            return False, "every variable index must be an integer"
        if value < 1 or value > n_variables:
            return False, f"variable index {value} is outside 1..{n_variables}"
        if value in selected:
            return False, f"variable index {value} is repeated"
        selected.add(value)

    empty_clauses = []
    crowded_clauses = []
    for number, clause in enumerate(inst.get("clauses", ()), 1):
        count = sum(variable in selected for variable in clause)
        if count == 0:
            empty_clauses.append(number)
        elif count != 1:
            crowded_clauses.append((number, count))
    if empty_clauses and crowded_clauses:
        return False, (f"mixed clause violations: C{empty_clauses[0]} has zero true "
                       f"variables and C{crowded_clauses[0][0]} has "
                       f"{crowded_clauses[0][1]}")
    if empty_clauses:
        return False, f"clause C{empty_clauses[0]} has zero true variables"
    if crowded_clauses:
        number, count = crowded_clauses[0]
        return False, f"clause C{number} has {count} true variables"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from assignments satisfying every implied XOR equation."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    dimension = len(inst["xor_free"])
    return _materialize_from_free(inst, rng.getrandbits(dimension))


def search_space(inst):
    """Return the naive space of all subsets of variables."""
    return 1 << inst["n_variables"]


def enumerate_all(inst):
    """Count exact answers through the parity space, capped at 2^20 trials."""
    dimension = len(inst["xor_free"])
    if dimension > 20:
        return None
    count = 0
    for free_bits in range(1 << dimension):
        candidate = _materialize_from_free(inst, free_bits)
        if verify(inst, candidate)[0]:
            count += 1
    return count


def _refine_colors(adjacency, sides):
    signatures = [(sides[i], len(adjacency[i])) for i in range(len(adjacency))]
    palette = {sig: number for number, sig in enumerate(sorted(set(signatures)))}
    colors = [palette[sig] for sig in signatures]
    history = []
    for _ in range(len(adjacency) + 1):
        signatures = [
            (sides[i], colors[i], tuple(sorted(colors[j] for j in adjacency[i])))
            for i in range(len(adjacency))
        ]
        ordered = sorted(set(signatures))
        palette = {sig: number for number, sig in enumerate(ordered)}
        new_colors = [palette[sig] for sig in signatures]
        history.append(tuple(sorted(Counter(new_colors).items())))
        if new_colors == colors:
            break
        colors = new_colors
    return colors, history


def canonical_key(inst):
    """Compute a relabelling-invariant incidence-graph certificate.

    Stable color refinement is exact on the asymmetric random graphs normally
    generated here.  If color classes remain tied, this is deliberately only a
    strong invariant, not a claimed solution to general graph isomorphism.
    """
    n_variables = inst["n_variables"]
    clauses = inst["clauses"]
    total = n_variables + len(clauses)
    adjacency = [[] for _ in range(total)]
    sides = [0] * n_variables + [1] * len(clauses)
    for ci, clause in enumerate(clauses):
        cn = n_variables + ci
        for variable in clause:
            vn = variable - 1
            adjacency[vn].append(cn)
            adjacency[cn].append(vn)
    colors, history = _refine_colors(adjacency, sides)
    vertex_profile = sorted(
        (sides[i], colors[i], len(adjacency[i]),
         tuple(sorted(colors[j] for j in adjacency[i])))
        for i in range(total)
    )
    edge_profile = sorted(
        (colors[v - 1], colors[n_variables + ci])
        for ci, clause in enumerate(clauses) for v in clause
    )
    certificate = {
        "parts": [n_variables, len(clauses)],
        "history": history,
        "vertices": vertex_profile,
        "edges": edge_profile,
    }
    payload = json.dumps(certificate, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params):
    """Increase both scale and exact-cover crowding while preserving nullity."""
    current = dict(params)
    n = int(current.get("n", 32))
    if n >= 192:
        return None
    current["n"] = max(n + 1, math.ceil(1.5 * n))
    current["degree3_pct"] = min(45, int(current.get("degree3_pct", 35)) + 3)
    return current


def _degree_position_attack(inst):
    n_variables = inst["n_variables"]
    target = n_variables // 3
    occurrences = [[] for _ in range(n_variables + 1)]
    neighbors = [set() for _ in range(n_variables + 1)]
    for ci, clause in enumerate(inst["clauses"]):
        for variable in clause:
            occurrences[variable].append(ci)
            neighbors[variable].update(v for v in clause if v != variable)
    degrees = [0] + [len(occurrences[v]) for v in range(1, n_variables + 1)]
    scores = {
        "low_degree": lambda v: (degrees[v], v),
        "high_degree": lambda v: (-degrees[v], v),
        "early_position": lambda v: (sum(occurrences[v]) / degrees[v], v),
        "neighbor_degree": lambda v: (sum(degrees[w] for w in neighbors[v]), v),
    }
    for score in scores.values():
        candidate = sorted(sorted(range(1, n_variables + 1), key=score)[:target])
        if verify(inst, candidate)[0]:
            return candidate
    return sorted(sorted(range(1, n_variables + 1), key=scores["neighbor_degree"])[:target])


def _greedy_attack(inst):
    clauses = inst["clauses"]
    n_variables = inst["n_variables"]
    covers = [set() for _ in range(n_variables + 1)]
    for ci, clause in enumerate(clauses):
        for variable in clause:
            covers[variable].add(ci)
    uncovered = set(range(len(clauses)))
    selected = []
    while uncovered:
        ci = min(uncovered)
        choices = [v for v in clauses[ci] if covers[v] <= uncovered]
        if not choices:
            break
        variable = max(choices, key=lambda v: (len(covers[v]), -v))
        selected.append(variable)
        uncovered.difference_update(covers[variable])
    return sorted(selected)


def _parity_attack(inst):
    return _materialize_from_free(inst, 0)


def _random_restart_attack(inst, rng, restarts=64):
    clauses = inst["clauses"]
    n_variables = inst["n_variables"]
    covers = [set() for _ in range(n_variables + 1)]
    for ci, clause in enumerate(clauses):
        for variable in clause:
            covers[variable].add(ci)
    last = []
    for _ in range(restarts):
        uncovered = set(range(len(clauses)))
        selected = []
        while uncovered:
            best_clause = None
            best_choices = None
            for ci in uncovered:
                choices = [v for v in clauses[ci] if covers[v] <= uncovered]
                if best_choices is None or len(choices) < len(best_choices):
                    best_clause, best_choices = ci, choices
                    if not choices:
                        break
            if not best_choices:
                break
            weights = [len(covers[v]) ** 2 for v in best_choices]
            variable = rng.choices(best_choices, weights=weights, k=1)[0]
            selected.append(variable)
            uncovered.difference_update(covers[variable])
        last = sorted(selected)
        if not uncovered and verify(inst, last)[0]:
            return last
    return last


def _relabel_instance(inst, permutation, reverse_clauses=False, reverse_literals=False):
    clauses = []
    source = list(reversed(inst["clauses"])) if reverse_clauses else inst["clauses"]
    for clause in source:
        mapped = [permutation[v] for v in clause]
        if reverse_literals:
            mapped.reverse()
        clauses.append(mapped)
    answer = [permutation[v] for v in inst.get("answer", [])]
    return _build_instance_dict(
        inst["n_variables"], clauses, inst.get("degree3_pct", 35), answer=answer
    )


def selftest():
    """Run all mandatory gates and return a JSON-serializable report."""
    report = {}

    planted_failures = []
    checked = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            checked += 1
            if not ok:
                planted_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not planted_failures, "checked": checked, "failures": planted_failures
    }

    shipping = make_instance(seed=321, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    planted_set = set(planted)
    false_variables = [v for v in range(1, shipping["n_variables"] + 1)
                       if v not in planted_set]
    corruptions = {
        "drop": planted[:-1],
        "duplicate": planted + [planted[0]],
        "empty": [],
        "out_of_range": planted + [shipping["n_variables"] + 1],
    }
    swapped = None
    for old in planted:
        for new in false_variables:
            trial = sorted((planted_set - {old}) | {new})
            ok, reason = verify(shipping, trial)
            if not ok and reason.startswith("mixed clause violations"):
                swapped = trial
                break
        if swapped is not None:
            break
    corruptions["swap"] = swapped if swapped is not None else sorted(
        (planted_set - {planted[0]}) | {false_variables[0]}
    )
    corruption_reasons = {}
    corruption_failures = []
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_reasons[name] = reason
        if ok:
            corruption_failures.append(name)
    reasons_distinct = len(set(corruption_reasons.values())) == len(corruption_reasons)
    report["G2_rejects_corruption"] = {
        "pass": not corruption_failures and reasons_distinct,
        "rejected": len(corruptions) - len(corruption_failures),
        "total": len(corruptions),
        "distinct_reasons": reasons_distinct,
        "reasons": corruption_reasons,
    }

    realistic = ("I checked each clause.\n```text\n<answer>"
                 + ", ".join(map(str, planted))
                 + "</answer>\n```\nThat is my final assignment.")
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_count": len(parsed) if isinstance(parsed, list) else None,
    }

    guess_rng = random.Random(8675309)
    total_guesses = 200_000
    hits = 0
    for _ in range(total_guesses):
        hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_probability = hits / total_guesses
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": hits,
        "total": total_guesses,
        "empirical_probability": guess_probability,
        "prior": "uniform over the complete affine GF(2) parity-solution space",
        "affine_dimension": len(shipping["xor_free"]),
        "naive_space": search_space(shipping),
    }

    small = make_instance(n=6, seed=404, degree3_pct=35)
    solution_count = enumerate_all(small)
    naive_space = search_space(small)
    fraction = None if solution_count is None else solution_count / naive_space
    report["G5_sparse"] = {
        "pass": solution_count is not None and fraction < 1e-3,
        "n_variables": small["n_variables"],
        "solutions": solution_count,
        "naive_space": naive_space,
        "solution_fraction": fraction,
    }

    attack_names = ("outlier", "greedy", "parity", "random_restart")
    attack_results = {name: {"solved": 0, "attempts": 0, "seeds_solved": []}
                      for name in attack_names}
    for seed in range(700, 708):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier": _degree_position_attack(inst),
            "greedy": _greedy_attack(inst),
            "parity": _parity_attack(inst),
            "random_restart": _random_restart_attack(inst, random.Random(seed ^ 0xBAD5EED)),
        }
        for name, candidate in candidates.items():
            attack_results[name]["attempts"] += 1
            if verify(inst, candidate)[0]:
                attack_results[name]["solved"] += 1
                attack_results[name]["seeds_solved"].append(seed)
    attacks_pass = all(result["solved"] == 0 for result in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": attacks_pass, "seeds": 8, "attacks": attack_results
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=909, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n_variables"] == 2 * shipping["n_variables"],
        "base_variables": shipping["n_variables"],
        "doubled_variables": doubled["n_variables"],
        "doubled_clauses": len(doubled["clauses"]),
        "verify_reason": doubled_reason,
        "base_affine_dimension": len(shipping["xor_free"]),
        "doubled_affine_dimension": len(doubled["xor_free"]),
    }

    invariant_checks = 0
    real_transform_checks = 0
    invariant_failures = []
    keys = []
    for seed in range(20):
        inst = make_instance(n=12, seed=10_000 + seed, degree3_pct=35)
        original_key = canonical_key(inst)
        keys.append(original_key)
        rng = random.Random(20_000 + seed)
        shuffled = list(range(1, inst["n_variables"] + 1))
        rng.shuffle(shuffled)
        permutation = {old: shuffled[old - 1]
                       for old in range(1, inst["n_variables"] + 1)}
        identity = {old: old for old in range(1, inst["n_variables"] + 1)}
        variants = [
            _relabel_instance(inst, permutation),
            _relabel_instance(inst, identity, reverse_clauses=True,
                              reverse_literals=True),
            _relabel_instance(inst, permutation, reverse_clauses=True,
                              reverse_literals=True),
        ]
        for variant in variants:
            invariant_checks += 1
            if canonical_key(variant) != original_key:
                invariant_failures.append(seed)
        transformed_ok, _ = verify(variants[-1], variants[-1]["answer"])
        real_transform_checks += 1
        if not transformed_ok:
            invariant_failures.append(f"witness-{seed}")
    distinct_keys = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and distinct_keys == 20,
        "invariance_checks": invariant_checks,
        "real_transform_checks": real_transform_checks,
        "distinct_unrelated": distinct_keys,
        "unrelated_total": 20,
        "failures": invariant_failures,
        "method": "bipartite incidence-graph color-refinement invariant",
    }

    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["all_passed"] = all(
        value.get("pass", False) for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


__all__ = [
    "DIFFICULTY", "SHIPPING_DIFFICULTY", "NOTES", "make_instance", "render",
    "parse_answer", "verify", "random_candidate", "search_space",
    "enumerate_all", "canonical_key", "escalate", "selftest",
]
