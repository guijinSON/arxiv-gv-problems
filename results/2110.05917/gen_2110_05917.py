"""Verified generator for Non-Monotone 2-3Sat from arXiv:2110.05917.

The public interface is intentionally standard-library-only and deterministic for
``(n, seed, **params)``.  The hidden assignment is sampled before any clause.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from collections import Counter


DIFFICULTY = {
    "easy": {"n": 12, "degree": 3},
    "hard": {"n": 384, "degree": 3},
}
SHIPPING_DIFFICULTY = "hard"


NOTES = r"""
Section 3 of Lu and Wu, arXiv:2110.05917v4, fixes the exact source problem:
clauses have two or three distinct variables, and every three-variable clause
contains both a positive and a negative literal.  Theorem 3.1 states that this
Non-Monotone 2-3Sat problem is NP-complete.  This module uses that source problem
rather than Theorem 3.2's separator target: the displayed RCTSVS definition has no
separator-cardinality budget, but its proof silently requires |S|=n+2m+p.

The syntactic restriction has a major easy corner.  If every clause has size
three, both constant assignments satisfy every mixed-sign clause; if every clause
has size two, the instance is ordinary 2-SAT and is polynomial-time solvable.
Here a random regular positive one-in-three core is encoded by one mixed-sign
3-clause and three unrestricted 2-clauses per constraint.  The output witness is
sampled before the hidden exact-cover partition and all clauses.  Every variable
occurs in exactly three core constraints, so plants and non-plants have identical
degree.  A hidden truth-name change makes the output witness look balanced even
though each core constraint contains exactly one selected variable.

The first balanced-clause generator was discarded because bounded WalkSAT solved
7/8 shipping trials.  The adversary panel for this version checks (1) a
per-variable occurrence outlier guess, (2) a left-to-right greedy repair, and (3)
bounded randomized WalkSAT restarts.  Clause and literal order and variable names
are shuffled.  The canonical key is a switching-invariant fingerprint made from
exact closed-walk and intersection counts of the unsigned clause hypergraph; it is
invariant under variable renaming, independent truth-value renaming, and input
reordering, though as a polynomial fingerprint it is not a complete
graph-isomorphism canonical form.
""".strip()


def _lit_value(lit, bits):
    value = bits[abs(lit) - 1]
    return value if lit > 0 else not value


def _answer_from_bits(bits):
    return [i + 1 if bit else -(i + 1) for i, bit in enumerate(bits)]


def _bits_from_answer(answer, n):
    return [answer[i] > 0 for i in range(n)]


def make_instance(n, seed=0, degree=3):
    """Sample a full assignment first, then manufacture clauses it satisfies.

    ``n`` is the final number of Boolean variables.  Increasing it at fixed
    regular degree grows both the witness space (2**n) and the constraint system.
    """
    if not isinstance(n, int) or isinstance(n, bool) or n < 12 or n % 3:
        raise ValueError("n must be an integer multiple of 3 and at least 12")
    if not isinstance(degree, int) or isinstance(degree, bool) or not 3 <= degree <= 6:
        raise ValueError("degree must be an integer from 3 through 6")

    rng = random.Random(seed)
    # G: this is the public witness, sampled before the hidden core or any clause.
    planted_bits = [bool(rng.getrandbits(1)) for _ in range(n)]

    edges = None
    orientation = None
    selected = None
    # The configuration model below makes a degree-regular 3-uniform hypergraph
    # with exactly one selected vertex per edge.  Written polarities are changed
    # by ``orientation`` so the planted public bits need not reveal that 1/3 split.
    for _partition_try in range(100):
        selected = [False] * n
        for var in rng.sample(range(n), n // 3):
            selected[var] = True
        orientation = [selected[i] ^ planted_bits[i] for i in range(n)]
        selected_vars = [i for i in range(n) if selected[i]]
        other_vars = [i for i in range(n) if not selected[i]]

        p0 = [i for i in selected_vars for _ in range(degree) if not orientation[i]]
        p1 = [i for i in selected_vars for _ in range(degree) if orientation[i]]
        f0 = [i for i in other_vars for _ in range(degree) if not orientation[i]]
        f1 = [i for i in other_vars for _ in range(degree) if orientation[i]]
        a, b, c = len(p0), len(p1), len(f0)
        edge_count = a + b
        low = max(0, edge_count - c)
        high = min(a, b + edge_count - c)
        if low > high:
            continue
        p0_with_11 = rng.randint(low, high)
        p1_with_00 = c - edge_count + p0_with_11

        for _pairing_try in range(2000):
            rng.shuffle(p0)
            rng.shuffle(p1)
            rng.shuffle(f0)
            rng.shuffle(f1)
            requirements = (
                [(p, 1, 1) for p in p0[:p0_with_11]]
                + [(p, 0, 1) for p in p0[p0_with_11:]]
                + [(p, 0, 0) for p in p1[:p1_with_00]]
                + [(p, 0, 1) for p in p1[p1_with_00:]]
            )
            rng.shuffle(requirements)
            at0 = 0
            at1 = 0
            trial_edges = []
            seen_edges = set()
            good = True
            for p, first_kind, second_kind in requirements:
                if first_kind:
                    first = f1[at1]
                    at1 += 1
                else:
                    first = f0[at0]
                    at0 += 1
                if second_kind:
                    second = f1[at1]
                    at1 += 1
                else:
                    second = f0[at0]
                    at0 += 1
                edge = tuple(sorted((p, first, second)))
                if first == second or edge in seen_edges:
                    good = False
                    break
                seen_edges.add(edge)
                trial_edges.append(edge)
            if not good:
                continue

            # A disconnected core factors into smaller independent puzzles.
            incidence = [[] for _ in range(n)]
            for edge_index, edge in enumerate(trial_edges):
                for var in edge:
                    incidence[var].append(edge_index)
            reached_vars = {0}
            reached_edges = set()
            frontier = [0]
            while frontier:
                var = frontier.pop()
                for edge_index in incidence[var]:
                    if edge_index in reached_edges:
                        continue
                    reached_edges.add(edge_index)
                    for neighbor in trial_edges[edge_index]:
                        if neighbor not in reached_vars:
                            reached_vars.add(neighbor)
                            frontier.append(neighbor)
            if len(reached_vars) == n:
                edges = trial_edges
                break
        if edges is not None:
            break
    if edges is None:
        raise RuntimeError("could not construct a connected regular core")

    def positive_x(var):
        # x = y xor orientation; express positive x as a literal over public y.
        return -(var + 1) if orientation[var] else var + 1

    def negative_x(var):
        return var + 1 if orientation[var] else -(var + 1)

    clauses = []
    for one, two, three in edges:
        # At least one x is true, followed by all three pairwise at-most-one rules.
        clauses.append([positive_x(one), positive_x(two), positive_x(three)])
        clauses.append([negative_x(one), negative_x(two)])
        clauses.append([negative_x(one), negative_x(three)])
        clauses.append([negative_x(two), negative_x(three)])
    for clause in clauses:
        rng.shuffle(clause)
    rng.shuffle(clauses)
    answer = _answer_from_bits(planted_bits)

    inst = {
        "family": "Non-Monotone 2-3Sat",
        "n": n,
        "clauses": clauses,
        "answer": answer,
        "degree": degree,
    }
    if any(
        len(clause) not in (2, 3)
        or len({abs(lit) for lit in clause}) != len(clause)
        or (len(clause) == 3 and len({lit > 0 for lit in clause}) != 2)
        for clause in clauses
    ):
        raise AssertionError("generator violated the Non-Monotone 2-3Sat syntax")
    ok, reason = verify(inst, answer)
    if not ok:  # This is an internal invariant, never a satisfiability search.
        raise AssertionError("generator produced a bad plant: " + reason)
    return inst


def render(inst):
    """Return the complete, standalone problem statement."""
    n = inst["n"]
    lines = [
        "Non-Monotone 2-3Sat witness problem",
        "",
        f"There are {n} Boolean variables, numbered 1 through {n} (1-indexed).",
        "A positive literal +i is true exactly when variable i is true; a negative",
        "literal -i is true exactly when variable i is false. A clause is an OR:",
        "it is satisfied when at least one listed literal is true. Satisfy every",
        "clause simultaneously. Each line below is one clause; literal order and",
        "clause order have no meaning. Variables within a clause are distinct.",
        "Every clause has two or three literals, and every three-literal clause",
        "contains at least one positive and at least one negative literal.",
        "",
        f"Clauses ({len(inst['clauses'])}):",
    ]
    for i, clause in enumerate(inst["clauses"], 1):
        lines.append(f"C{i}: " + " ".join(f"{lit:+d}" for lit in clause))
    lines.extend(
        [
            "",
            f"Output exactly {n} comma-separated signed integers in variable order.",
            "At position i write +i to set variable i true or -i to set it false.",
            "Every variable must occur exactly once; repetitions are forbidden.",
            "Order inside the answer therefore matters and is fixed as 1,2,...,n.",
            "",
            "Give your final answer inside <answer></answer> tags, as signed integers.",
            "Example: <answer>1, -2, 3</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    return "\n".join(lines)


_ANSWER_BLOCK = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def parse_answer(text):
    """Extract the last well-formed tagged integer list, or return None."""
    if not isinstance(text, str):
        return None
    blocks = _ANSWER_BLOCK.findall(text)
    if not blocks:
        return None
    body = blocks[-1].strip()
    if not body or not re.fullmatch(r"[+\-]?\d+(?:\s*(?:,|\s)\s*[+\-]?\d+)*", body):
        return None
    try:
        return [int(token) for token in re.findall(r"[+\-]?\d+", body)]
    except (TypeError, ValueError, OverflowError):
        return None


def verify(inst, answer):
    """Accept any satisfying assignment in the required witness encoding."""
    n = inst.get("n")
    if not isinstance(answer, (list, tuple)):
        return False, "answer must be a list of signed integers"
    if len(answer) == 0:
        return False, "empty answer"
    if len(answer) != n:
        return False, f"wrong length: expected {n}, got {len(answer)}"
    if any(not isinstance(x, int) or isinstance(x, bool) for x in answer):
        return False, "every entry must be an integer"
    if any(x == 0 or abs(x) > n for x in answer):
        return False, f"literal out of range: expected absolute values 1 through {n}"
    absolute = [abs(x) for x in answer]
    if len(set(absolute)) != n:
        return False, "duplicate variable"
    if absolute != list(range(1, n + 1)):
        return False, "literals must appear in variable order"

    bits = _bits_from_answer(answer, n)
    for index, clause in enumerate(inst.get("clauses", ()), 1):
        if not any(_lit_value(lit, bits) for lit in clause):
            return False, f"clause {index} is unsatisfied"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the actual structural search space: one sign per variable."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    return [i if rng.getrandbits(1) else -i for i in range(1, inst["n"] + 1)]


def search_space(inst):
    """There are exactly two sign choices for each of n ordered variables."""
    return 1 << inst["n"]


def enumerate_all(inst):
    """Count satisfying assignments exactly for n <= 22; cap larger work."""
    n = inst["n"]
    if n > 22:
        return None
    encoded = []
    for clause in inst["clauses"]:
        positive = 0
        negative = 0
        for lit in clause:
            if lit > 0:
                positive |= 1 << (lit - 1)
            else:
                negative |= 1 << (-lit - 1)
        encoded.append((positive, negative))
    full = (1 << n) - 1
    count = 0
    for assignment in range(1 << n):
        false_bits = full ^ assignment
        if all((assignment & pos) or (false_bits & neg) for pos, neg in encoded):
            count += 1
    return count


def canonical_key(inst):
    """Switching-invariant structural fingerprint of the clause hypergraph.

    Signs disappear because swapping a variable's two truth names is a witness-
    preserving isomorphism.  Closed-walk moments of a weighted primal graph are
    much stronger than ordinary color refinement on these deliberately regular
    instances, while remaining polynomial and exactly integer-valued.
    """
    n = inst["n"]
    clauses = inst["clauses"]
    adjacency = [dict() for _ in range(n)]
    absolute_clauses = {2: [], 3: []}
    for clause in clauses:
        vertices = tuple(sorted(abs(lit) - 1 for lit in clause))
        absolute_clauses[len(clause)].append(vertices)
        weight = 1 if len(clause) == 2 else 5
        for at, left in enumerate(vertices):
            for right in vertices[at + 1:]:
                adjacency[left][right] = adjacency[left].get(right, 0) + weight
                adjacency[right][left] = adjacency[right].get(left, 0) + weight

    traces = [0] * 14
    for start in range(n):
        vector = {start: 1}
        for power in range(14):
            following = {}
            for left, paths in vector.items():
                for right, weight in adjacency[left].items():
                    following[right] = following.get(right, 0) + paths * weight
            vector = following
            traces[power] += vector.get(start, 0)

    intersection_profile = Counter()
    all_edges = [(arity, set(vertices)) for arity in (2, 3) for vertices in absolute_clauses[arity]]
    for i, (arity_i, edge_i) in enumerate(all_edges):
        for arity_j, edge_j in all_edges[:i]:
            intersection_profile[(arity_i, arity_j, len(edge_i & edge_j))] += 1
    material = json.dumps(
        {
            "n": n,
            "arity_counts": {str(k): len(v) for k, v in absolute_clauses.items()},
            "weighted_degrees": sorted(sum(row.values()) for row in adjacency),
            "closed_walk_traces_1_to_14": traces,
            "intersection_profile": sorted((list(k), v) for k, v in intersection_profile.items()),
        },
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode()).hexdigest()


def escalate(params):
    """Increase the exponential dimension while keeping the regular regime stable."""
    if not isinstance(params, dict) or "n" not in params:
        return None
    n = int(params["n"])
    if n >= 1152:
        return None
    harder = dict(params)
    proposed = max(n + 3, int(round(n * 1.5)))
    harder["n"] = proposed + (-proposed % 3)
    return harder


def _occurrence_attack(inst):
    counts = [[0, 0] for _ in range(inst["n"])]  # negative, positive
    for clause in inst["clauses"]:
        for lit in clause:
            counts[abs(lit) - 1][1 if lit > 0 else 0] += 1
    bits = [positive > negative for negative, positive in counts]
    return _answer_from_bits(bits)


def _greedy_attack(inst):
    n = inst["n"]
    bits = [False] * n
    frequency = Counter(abs(lit) for clause in inst["clauses"] for lit in clause)
    for clause in inst["clauses"]:
        if not any(_lit_value(lit, bits) for lit in clause):
            lit = min(clause, key=lambda x: (frequency[abs(x)], abs(x)))
            bits[abs(lit) - 1] = lit > 0
    return _answer_from_bits(bits)


def _random_restart_attack(inst, rng, restarts=4, flips_per_variable=8):
    n = inst["n"]
    clauses = inst["clauses"]
    incidence = [[] for _ in range(n)]
    for clause_index, clause in enumerate(clauses):
        for lit in clause:
            incidence[abs(lit) - 1].append(clause_index)

    def clause_count(clause, bits):
        return sum(_lit_value(lit, bits) for lit in clause)

    last = [False] * n
    for _ in range(restarts):
        bits = [bool(rng.getrandbits(1)) for _ in range(n)]
        counts = [clause_count(clause, bits) for clause in clauses]
        unsatisfied = {i for i, count in enumerate(counts) if count == 0}
        for _step in range(flips_per_variable * n):
            if not unsatisfied:
                return _answer_from_bits(bits)
            clause = clauses[rng.choice(tuple(unsatisfied))]
            if rng.random() < 0.25:
                chosen_var = abs(rng.choice(clause)) - 1
            else:
                scored = []
                for lit in clause:
                    var = abs(lit) - 1
                    bits[var] = not bits[var]
                    delta = 0
                    for affected in incidence[var]:
                        after_unsatisfied = clause_count(clauses[affected], bits) == 0
                        before_unsatisfied = counts[affected] == 0
                        delta += after_unsatisfied - before_unsatisfied
                    bits[var] = not bits[var]
                    scored.append((len(unsatisfied) + delta, rng.random(), var))
                chosen_var = min(scored)[2]
            bits[chosen_var] = not bits[chosen_var]
            for affected in incidence[chosen_var]:
                counts[affected] = clause_count(clauses[affected], bits)
                if counts[affected]:
                    unsatisfied.discard(affected)
                else:
                    unsatisfied.add(affected)
        last = bits
    return _answer_from_bits(last)


def _transformed_instance(
    inst, seed, permute=False, global_flip=False, reorder=False, flip_variables=None
):
    rng = random.Random(seed)
    n = inst["n"]
    destinations = list(range(1, n + 1))
    if permute:
        rng.shuffle(destinations)
    mapping = {old: destinations[old - 1] for old in range(1, n + 1)}
    flip_variables = set(flip_variables or ())

    clauses = []
    for clause in inst["clauses"]:
        mapped = []
        for lit in clause:
            sign = 1 if lit > 0 else -1
            if global_flip or abs(lit) in flip_variables:
                sign = -sign
            mapped.append(sign * mapping[abs(lit)])
        if reorder:
            rng.shuffle(mapped)
        clauses.append(mapped)
    if reorder:
        rng.shuffle(clauses)

    old_bits = _bits_from_answer(inst["answer"], n)
    new_bits = [False] * n
    for old, bit in enumerate(old_bits, 1):
        should_flip = global_flip or old in flip_variables
        new_bits[mapping[old] - 1] = (not bit) if should_flip else bit
    return {
        "family": inst["family"],
        "n": n,
        "clauses": clauses,
        "answer": _answer_from_bits(new_bits),
        "degree": inst.get("degree"),
    }


def _safe_single_variable_switch(inst):
    """Find a non-global truth-name swap that keeps every 3-clause mixed."""
    for var in range(1, inst["n"] + 1):
        safe = True
        for clause in inst["clauses"]:
            if len(clause) != 3 or all(abs(lit) != var for lit in clause):
                continue
            signs = [(-lit if abs(lit) == var else lit) > 0 for lit in clause]
            if len(set(signs)) != 2:
                safe = False
                break
        if safe:
            return {var}
    return set()


def selftest():
    """Run mandatory G1--G8 gates and return their machine-readable report."""
    report = {"family": "Non-Monotone 2-3Sat", "shipping_difficulty": SHIPPING_DIFFICULTY}

    # G1: every named preset, several independent seeds.
    g1_total = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 99):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_total += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checked": g1_total,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=123456, **shipping)
    planted = list(inst["answer"])

    # G2: five structurally different corruptions and five distinct diagnostics.
    duplicate = list(planted)
    duplicate[1] = (1 if planted[0] > 0 else -1) * 1
    swapped = list(planted)
    swapped[0], swapped[-1] = swapped[-1], swapped[0]
    out_of_range = list(planted)
    out_of_range[-1] = inst["n"] + 1
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    reasons = {}
    g2_ok = True
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        g2_ok = g2_ok and not ok
        reasons[name] = reason
    g2_ok = g2_ok and len(set(reasons.values())) == len(reasons)
    report["G2_rejects_corruption"] = {
        "pass": g2_ok,
        "rejected": sum(verify(inst, value)[0] is False for value in corruptions.values()),
        "distinct_reasons": len(set(reasons.values())),
        "reasons": reasons,
    }

    # G3: realistic surrounding prose and a Markdown fence.
    response = (
        "I checked each clause. My final assignment is:\n```text\n<answer>"
        + ", ".join(str(x) for x in planted)
        + "</answer>\n```\nThat is the requested witness."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_length": len(parsed) if parsed is not None else None,
    }

    # G4: uniform over all structurally valid signed assignments, not junk lists.
    guess_rng = random.Random(20260902)
    total = 200_000
    hits = 0
    for _ in range(total):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            hits += 1
    report["G4_guess_resistance"] = {
        "pass": hits / total < 1e-6,
        "hits": hits,
        "total": total,
        "rate": hits / total,
        "sampler": "uniform over the 2^n ordered one-sign-per-variable witnesses",
    }

    # G5: exact enumeration on a capped micro-instance.
    tiny = make_instance(n=18, seed=314159, degree=3)
    solutions = enumerate_all(tiny)
    space = search_space(tiny)
    fraction = solutions / space
    report["G5_sparse"] = {
        "pass": solutions is not None and fraction < 0.01,
        "n": tiny["n"],
        "solutions": solutions,
        "search_space": space,
        "fraction": fraction,
    }

    # G6: attacks know the construction but never read inst['answer'].
    attack_rows = {
        "occurrence_outlier": [],
        "left_to_right_greedy": [],
        "random_restart_walksat": [],
    }
    for seed in range(800, 808):
        attacked = make_instance(seed=seed, **shipping)
        candidates = {
            "occurrence_outlier": _occurrence_attack(attacked),
            "left_to_right_greedy": _greedy_attack(attacked),
            "random_restart_walksat": _random_restart_attack(
                attacked, random.Random(seed ^ 0x5A17)
            ),
        }
        for name, candidate in candidates.items():
            ok, reason = verify(attacked, candidate)
            attack_rows[name].append({"seed": seed, "solved": ok, "reason": reason})
    attack_summary = {
        name: {
            "successes": sum(row["solved"] for row in rows),
            "trials": len(rows),
            "rows": rows,
        }
        for name, rows in attack_rows.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 and item["trials"] >= 8 for item in attack_summary.values()),
        "attacks": attack_summary,
    }

    # G7: n doubles without leaving the planted satisfiable regime.
    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * inst["n"] and len(doubled["clauses"]) > len(inst["clauses"]),
        "base_n": inst["n"],
        "base_clauses": len(inst["clauses"]),
        "doubled_n": doubled["n"],
        "doubled_clauses": len(doubled["clauses"]),
        "verify_reason": doubled_reason,
    }

    # G8: reorder, rename variables, swap truth names, and compose the maps.
    invariance_checks = 0
    carried_witness_checks = 0
    g8_failures = []
    unrelated_keys = []
    key_params = {"n": 36, "degree": 3}
    for seed in range(20):
        original = make_instance(seed=10_000 + seed, **key_params)
        key = canonical_key(original)
        unrelated_keys.append(key)
        safe_switch = _safe_single_variable_switch(original)
        if not safe_switch:
            g8_failures.append({"seed": seed, "kind": "no_safe_independent_switch"})
        variants = [
            _transformed_instance(original, seed + 1, reorder=True),
            _transformed_instance(original, seed + 2, permute=True),
            _transformed_instance(original, seed + 3, global_flip=True),
            _transformed_instance(original, seed + 30, flip_variables=safe_switch),
            _transformed_instance(
                original, seed + 4, permute=True, global_flip=True, reorder=True
            ),
        ]
        for variant in variants:
            invariance_checks += 1
            if canonical_key(variant) != key:
                g8_failures.append({"seed": seed, "kind": "key_changed"})
            syntax_ok = all(
                len(clause) in (2, 3)
                and len({abs(lit) for lit in clause}) == len(clause)
                and (len(clause) != 3 or len({lit > 0 for lit in clause}) == 2)
                for clause in variant["clauses"]
            )
            if not syntax_ok:
                g8_failures.append({"seed": seed, "kind": "map_left_family"})
            carried_ok, reason = verify(variant, variant["answer"])
            carried_witness_checks += 1
            if not carried_ok:
                g8_failures.append({"seed": seed, "kind": "map_not_real", "reason": reason})
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_witness_checks,
        "unrelated_distinct": distinct,
        "unrelated_total": 20,
        "failures": g8_failures,
        "invariant_under": [
            "clause and literal reordering",
            "variable permutation",
            "global truth-name swap",
            "family-preserving independent truth-name swap",
            "their composition",
        ],
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
