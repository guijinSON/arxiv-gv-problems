"""Verified problem generator derived from arXiv:1210.7684.

Farzad and Karimi introduce POSITIVE AND MINIMUM INTERSECTING 1-IN-3 SAT
in Section 3 and use it in their girth-five graph-square reduction.  This
module generates a structured subfamily of that problem directly.  Its
clauses are the incidence triples of a traded Latin square.  Any one of the
three hidden point classes is a satisfying exact-one assignment, so the
certificate is known by composition rather than found by solving.

The generated distribution has a polynomial recognition algorithm: two
variables are in the same hidden class exactly when they never occur together.
Consequently this is an honest Track-B family, not an average-case consequence
of the paper's NP-completeness theorem.
"""

from __future__ import annotations

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
    "native_domain": "logic",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "positive three-variable clauses",
        "minimum-intersection clause system",
        "exact-one truth assignment",
    ],
    "verification_operations": [
        "integer range and distinctness checks",
        "exact set membership",
        "per-clause true-variable counting",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Variables that never occur together form three equivalence classes; "
        "without recognizing noncooccurrence as the invariant, one faces the "
        "full exact-one constraint system."
    ),
    "hardness_basis": (
        "Track B: on this Latin-square incidence distribution the reference "
        "cooccurrence-partition algorithm runs in O(q^2) time and, at shipping "
        "q=64, performs 12,608 counted membership/pair operations (0.00587 seconds "
        "mean over eight measured instances); the compact route uses at most 256 incidence, "
        "marking, and output operations after noticing that noncooccurrence is "
        "an equivalence relation, whereas mechanically processing 4,096 shuffled "
        "clauses is not executable by hand in the no-tool context."
    ),
    "max_answer_tokens": 82,
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

DIFFICULTY = {
    "demo": {"n": 2, "trade_density": 0.0},
    "easy": {"n": 16, "trade_density": 0.25},
    "medium": {"n": 32, "trade_density": 0.40},
    "hard": {"n": 64, "trade_density": 0.50},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Noncooccurrence of variables is an equivalence relation with three hidden classes."
)
PLACEBO_HINT = (
    "Careful bookkeeping of variable identifiers is useful throughout this exact-one instance."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A comma-separated set, written in increasing order, of exactly q distinct "
        "variable IDs from 0 through 3q-1; precisely those q variables are declared true."
    ),
    "bounds": {
        "length": "q (the displayed class size)",
        "entry_minimum": 0,
        "entry_maximum": "3q-1",
        "all_distinct": True,
        "increasing_order": True,
        "candidate_count": "binomial(3q,q)",
    },
}

# Updated after the script-owned three-arm runs.  These values are diagnostics;
# since 2026-09-05 only the size/effort caps gate G9.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0, "service_errors": 4},
    "hinted": {"solved": 0, "attempts": 0, "service_errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "service_errors": 4},
    "hinted_verdict": "unreachable: OpenRouter HTTP 403 key limit",
    "placebo_verdict": "unreachable: OpenRouter HTTP 403 key limit",
}

NOTES = r"""
Definition. Section 3, immediately before Theorem 2, defines POSITIVE AND
MINIMUM INTERSECTING 1-IN-3 SAT: every clause contains exactly three positive
variables, distinct clauses share at most one variable, and a witness makes
exactly one variable in each clause true. That exact definition fixes render()
and verify(). Theorem 2 states NP-completeness, and Lemma 3 is the paper's
certificate-preserving reduction from these assignments to girth-five graph
square roots.

Step-0 algorithm question. Theorem 4 proves worst-case NP-completeness for
girth-five square roots, but it says nothing about inverse-generated random
roots. Moreover, Section 1 records the O(|V||E|) reconstruction algorithm once
the root girth is at least six. For this module's distribution an even stronger
special-purpose algorithm exists: build variable cooccurrence sets and take a
noncooccurrence class. It is O(q^2), succeeds on every generated instance, and
is reported as the Track-B reference algorithm rather than hidden in a Track-A
claim. At q=64 it processes 4,096 clauses and 12,608 counted primitive
operations. The shorter intended route is to focus on the q occurrences of one
variable after recognizing the invariant, mark its 2q cooccurring variables,
and output the q-variable complement (at most 4q=256 operations after the
relevant occurrences have been identified in context).

Construction. Start with the addition table of Z_q. Independently switch
disjoint 2x2 intercalates; each switch preserves the Latin property. Randomly
relabel the three q-element point classes and shuffle all q^2 triples. Any two
clauses still meet in at most one variable. Each clause contains one member of
each hidden class, so any whole class is a certificate. The checker does not
assume these are the only certificates: it accepts every q-subset satisfying
all displayed clauses. Exact brute-force demo enumeration finds three
bounded-language answers.

Attacks. Equal occurrence degree defeats the frequency outlier. A one-pass
greedy exact-one assignment, 256 uniform fixed-weight restarts, a modular-ID
ansatz, and a bounded prefix version of the noncooccurrence idea all fail on
eight shipping seeds. The complete cooccurrence partition is intentionally
successful and is recorded separately as the Track-B reference algorithm.

Canonicalization. Variable relabeling, clause reordering, and reordering within
a clause are presentation symmetries. canonical_key derives the three
noncooccurrence classes and records the relabeling-invariant distribution of
Pasch/intercalate participation. It is a strong invariant rather than a complete
isomorphism canon; selftest checks carried-witness invariance and twenty-seed
distinctness at the shipping preset.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_GUESS_SAMPLES = 200_000


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_params(q, trade_density, seed):
    if not _is_int(q) or q < 2 or q % 2:
        raise ValueError("n must be an even integer at least 2")
    if not isinstance(trade_density, (int, float)) or isinstance(trade_density, bool):
        raise ValueError("trade_density must be numeric")
    if not 0.0 <= trade_density <= 1.0:
        raise ValueError("trade_density must lie in [0,1]")
    if not _is_int(seed):
        raise ValueError("seed must be an integer")


def _traded_latin_square(q, trade_density, rng):
    """Transform the cyclic Latin square by disjoint 2x2 Latin trades."""
    table = [[(r + c) % q for c in range(q)] for r in range(q)]
    half = q // 2
    for r in range(half):
        for c in range(half):
            if rng.random() >= trade_density:
                continue
            rr, cc = r + half, c + half
            table[r][c], table[r][cc] = table[r][cc], table[r][c]
            table[rr][c], table[rr][cc] = table[rr][cc], table[rr][c]
    return table


def make_instance(n, seed=0, **params):
    """Build a certified minimum-intersection exact-one instance by composition."""
    trade_density = params.pop("trade_density", 0.5)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, trade_density, seed)
    q = n
    rng = random.Random(seed)
    table = _traded_latin_square(q, trade_density, rng)

    # Relabel all variables uniformly; no ID interval or residue class identifies
    # the planted class.  The first abstract class is retained only as the known
    # certificate and disappears from the public instance.
    relabel = list(range(3 * q))
    rng.shuffle(relabel)
    clauses = []
    for r in range(q):
        for c in range(q):
            clause = [relabel[r], relabel[q + c], relabel[2 * q + table[r][c]]]
            rng.shuffle(clause)
            clauses.append(clause)
    rng.shuffle(clauses)

    return {
        "class_size": q,
        "variable_count": 3 * q,
        "clauses": clauses,
        "answer": sorted(relabel[:q]),
    }


def render(inst):
    q = inst["class_size"]
    lines = [
        "POSITIVE MINIMUM-INTERSECTION 1-IN-3 SAT",
        "",
        "There are %d Boolean variables, numbered 0 through %d." %
        (inst["variable_count"], inst["variable_count"] - 1),
        "Every displayed clause is a triple of distinct positive variables.",
        "A clause is satisfied exactly when precisely one of its three variables is true.",
        "Any two different clauses share at most one variable.",
        "Find a satisfying assignment having exactly %d true variables." % q,
        "All variables not listed in your answer are false; answer order is ignored,",
        "but use increasing order and do not repeat an ID.",
        "",
        "Clauses (one [a,b,c] triple per clause; line breaks are only formatting):",
    ]
    chunk = 8
    clauses = inst["clauses"]
    for start in range(0, len(clauses), chunk):
        lines.append(" ".join("[%d,%d,%d]" % tuple(c) for c in clauses[start:start + chunk]))
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as exactly %d " % q
        + "comma-separated decimal variable IDs in increasing order.",
        "Example format: <answer>0, 7, 19</answer>",
        "The example shows syntax only and does not have the required length.",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json|text|python)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
    try:
        if body.startswith("["):
            value = json.loads(body)
        else:
            if not body:
                return []
            if not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", body):
                return None
            value = [int(piece.strip()) for piece in body.split(",")]
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, list) or any(not _is_int(x) for x in value):
        return None
    return value


def verify(inst, answer):
    """Check a proposed exact-one assignment without consulting inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a list of variable IDs"
    if not answer:
        return False, "answer is empty"
    q = inst["class_size"]
    if len(answer) != q:
        return False, "expected exactly %d true-variable IDs, got %d" % (q, len(answer))
    if any(not _is_int(x) for x in answer):
        return False, "every variable ID must be an integer"
    if len(set(answer)) != len(answer):
        return False, "variable IDs must be distinct"
    total = inst["variable_count"]
    if any(x < 0 or x >= total for x in answer):
        return False, "variable ID outside the inclusive range 0..%d" % (total - 1)
    chosen = set(answer)
    for index, clause in enumerate(inst["clauses"]):
        count = sum(v in chosen for v in clause)
        if count != 1:
            return False, "clause %d has %d true variables, expected exactly 1" % (index, count)
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the statement-implied fixed-weight candidate space."""
    return sorted(rng.sample(range(inst["variable_count"]), inst["class_size"]))


def search_space(inst):
    return math.comb(inst["variable_count"], inst["class_size"])


def enumerate_all(inst):
    space = search_space(inst)
    if space > 200_000:
        return None
    count = 0
    for candidate in itertools.combinations(
            range(inst["variable_count"]), inst["class_size"]):
        count += int(verify(inst, list(candidate))[0])
    return count


def _noncooccurrence_classes(inst):
    total = inst["variable_count"]
    co = [set() for _ in range(total)]
    for a, b, c in inst["clauses"]:
        co[a].update((b, c))
        co[b].update((a, c))
        co[c].update((a, b))
    remaining = set(range(total))
    classes = []
    while remaining:
        pivot = min(remaining)
        block = {v for v in range(total) if v == pivot or v not in co[pivot]}
        if not block <= remaining:
            return None
        classes.append(block)
        remaining -= block
    if len(classes) != 3 or any(len(block) != inst["class_size"] for block in classes):
        return None
    return classes


def _pasch_profile(inst):
    """Relabeling-invariant per-variable Pasch participation counts."""
    classes = _noncooccurrence_classes(inst)
    if classes is None:
        return None
    classes = sorted((sorted(block) for block in classes), key=lambda x: tuple(x))
    rows, cols, syms = classes
    row_set, col_set, sym_set = set(rows), set(cols), set(syms)
    table = {}
    for clause in inst["clauses"]:
        r = next((v for v in clause if v in row_set), None)
        c = next((v for v in clause if v in col_set), None)
        s = next((v for v in clause if v in sym_set), None)
        if r is None or c is None or s is None or (r, c) in table:
            return None
        table[(r, c)] = s
    if len(table) != len(rows) * len(cols):
        return None

    counts = [0] * inst["variable_count"]
    pasches = 0
    for ia, a in enumerate(rows):
        for b in rows[ia + 1:]:
            permutation = {table[(a, c)]: table[(b, c)] for c in cols}
            col_of = {table[(a, c)]: c for c in cols}
            for s, t in permutation.items():
                if s < t and permutation.get(t) == s:
                    c, d = col_of[s], col_of[t]
                    for v in (a, b, c, d, s, t):
                        counts[v] += 1
                    pasches += 1
    return pasches, sorted(counts)


def canonical_key(inst):
    profile = _pasch_profile(inst)
    if profile is None:
        # This branch is only for malformed external instances.  It remains
        # deterministic but is not used by generated instances or the G8 claim.
        normalized = sorted(tuple(sorted(c)) for c in inst.get("clauses", []))
        payload = {"variables": inst.get("variable_count"), "clauses": normalized}
    else:
        payload = {
            "variables": inst["variable_count"],
            "clauses": len(inst["clauses"]),
            "pasches": profile[0],
            "participation": profile[1],
        }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params):
    current = dict(params)
    current.pop("_preset", None)
    q = int(current.get("n", 16))
    density = float(current.get("trade_density", 0.5))
    if density < 0.5:
        current["trade_density"] = min(0.5, density + 0.1)
        return current
    if q < 64:
        current["n"] = min(64, 2 * q)
        return current
    # The only remaining axis is q.  The intended 4q incidence/mark/output
    # route crosses G9(c)'s 300-operation no-tool cap before the next meaningful
    # power-of-two rung, so the family is cap-bound rather than exhausted.
    return "cap_bound"


def _reference_algorithm(inst):
    """Successful Track-B algorithm: return the class containing variable 0."""
    pivot = 0
    co = set()
    operations = 0
    for clause in inst["clauses"]:
        operations += 3
        if pivot in clause:
            for v in clause:
                if v != pivot:
                    co.add(v)
                    operations += 1
    answer = []
    for v in range(inst["variable_count"]):
        operations += 1
        if v not in co:
            answer.append(v)
    return answer, operations


def _attack_frequency_outlier(inst):
    degree = [0] * inst["variable_count"]
    for clause in inst["clauses"]:
        for v in clause:
            degree[v] += 1
    return sorted(range(inst["variable_count"]), key=lambda v: (degree[v], v))[
        :inst["class_size"]]


def _attack_greedy(inst):
    chosen = set()
    forbidden = set()
    for clause in inst["clauses"]:
        present = [v for v in clause if v in chosen]
        if len(present) > 1:
            break
        if len(present) == 1:
            forbidden.update(v for v in clause if v not in chosen)
            continue
        available = [v for v in clause if v not in forbidden]
        if available:
            v = min(available)
            chosen.add(v)
            forbidden.update(x for x in clause if x != v)
        if len(chosen) > inst["class_size"]:
            break
    if len(chosen) < inst["class_size"]:
        for v in range(inst["variable_count"]):
            if v not in chosen and v not in forbidden:
                chosen.add(v)
                if len(chosen) == inst["class_size"]:
                    break
    return sorted(chosen)[:inst["class_size"]]


def _attack_prefix_noncooccurrence(inst):
    """Bounded no-tool version of the right invariant; it sees only 4q clauses."""
    q = inst["class_size"]
    pivot = inst["clauses"][0][0]
    co = set()
    for clause in inst["clauses"][:4 * q]:
        if pivot in clause:
            co.update(v for v in clause if v != pivot)
    candidate = [v for v in range(inst["variable_count"]) if v not in co]
    return sorted(candidate[:q])


def _attack_modular_ids(inst):
    q = inst["class_size"]
    candidates = []
    for residue in range(3):
        candidate = [v for v in range(inst["variable_count"]) if v % 3 == residue]
        if len(candidate) == q:
            candidates.append(candidate)
    return candidates


def _relabel_instance(inst, rng):
    total = inst["variable_count"]
    permutation = list(range(total))
    rng.shuffle(permutation)
    clauses = [[permutation[v] for v in clause] for clause in inst["clauses"]]
    for clause in clauses:
        rng.shuffle(clause)
    rng.shuffle(clauses)
    return {
        "class_size": inst["class_size"],
        "variable_count": total,
        "clauses": clauses,
        "answer": sorted(permutation[v] for v in inst["answer"]),
    }


def _corruptions(inst):
    answer = list(inst["answer"])
    outside = next(v for v in range(inst["variable_count"]) if v not in set(answer))
    replacement = answer[1:] + [outside]
    return {
        "empty": [],
        "drop_one": answer[:-1],
        "duplicate": answer[:-1] + [answer[0]],
        "out_of_range": answer[:-1] + [inst["variable_count"]],
        "replace_one": replacement,
    }


def selftest():
    report = {}

    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": why})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checked": checks,
        "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=314159, **shipping_params)

    cases = {}
    reasons = []
    for name, candidate in _corruptions(shipping).items():
        ok, why = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": why}
        if not ok:
            reasons.append(why)
    report["G2_rejects_corruption"] = {
        "pass": all(c["rejected"] for c in cases.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "cases": cases,
    }

    response = (
        "The noncooccurrence classes give the assignment.\n\n"
        "<answer>```text\n"
        + ", ".join(map(str, shipping["answer"]))
        + "\n```</answer>\nThat is my final answer."
    )
    parsed = parse_answer(response)
    parsed_ok, parsed_why = verify(shipping, parsed)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and parsed_ok,
        "verify_reason": parsed_why,
    }

    guess_rng = random.Random(271828)
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(_GUESS_SAMPLES):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_wall = time.perf_counter() - guess_start
    report["G4_guess_resistance"] = {
        "pass": guess_hits / _GUESS_SAMPLES < 1e-6,
        "hits": guess_hits,
        "total": _GUESS_SAMPLES,
        "measured_probability": guess_hits / _GUESS_SAMPLES,
        "candidate_space": search_space(shipping),
        "sampler": "uniform q-subsets of the 3q variables (fixed weight enforced)",
        "wall_clock_sec": round(guess_wall, 6),
    }

    attack_seeds = list(range(800, 808))
    attack_results = {
        "outlier_occurrence_degree": {"successes": 0, "attempts": 8},
        "greedy_clause_first_fit": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "prefix_noncooccurrence_4q": {"successes": 0, "attempts": 8},
        "modular_id_three_class_ansatz": {"successes": 0, "attempts": 8},
    }
    attack_wall_start = time.perf_counter()
    reference_operations = []
    reference_walls = []
    reference_successes = 0
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **shipping_params)
        candidates = {
            "outlier_occurrence_degree": [_attack_frequency_outlier(inst)],
            "greedy_clause_first_fit": [_attack_greedy(inst)],
            "prefix_noncooccurrence_4q": [_attack_prefix_noncooccurrence(inst)],
            "modular_id_three_class_ansatz": _attack_modular_ids(inst),
        }
        rrng = random.Random(1_000_000 + seed)
        candidates["random_restart_256"] = [
            random_candidate(inst, rrng) for _ in range(256)
        ]
        for name, tries in candidates.items():
            solved = any(verify(inst, candidate)[0] for candidate in tries)
            attack_results[name]["successes"] += int(solved)

        t0 = time.perf_counter()
        reference, operations = _reference_algorithm(inst)
        reference_walls.append(time.perf_counter() - t0)
        reference_operations.append(operations)
        reference_successes += int(verify(inst, reference)[0])
    attack_wall = time.perf_counter() - attack_wall_start
    all_failed = all(item["successes"] == 0 for item in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "complete cooccurrence partition",
            "complexity": "O(q^2) time and O(q) space for one class",
            "wall_clock_sec_total_8": round(sum(reference_walls), 6),
            "wall_clock_sec_mean": round(sum(reference_walls) / 8, 6),
            "operations_mean": sum(reference_operations) / 8,
            "operations_max": max(reference_operations),
            "solves": "%d/8, as expected" % reference_successes,
        },
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    report["G5_density_and_baseline"] = {
        "pass": guess_hits / _GUESS_SAMPLES < 1e-6 and all_failed,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": _GUESS_SAMPLES,
        "shipping_solution_fraction_estimate": guess_hits / _GUESS_SAMPLES,
        "demo_exact_valid_answer_count": enumerate_all(demo),
        "demo_candidate_count": search_space(demo),
        "baseline_attack_wall_clock_sec_total": round(attack_wall, 6),
        "baseline_random_restart_candidates": 8 * 256,
        "reference_wall_clock_sec_total": round(sum(reference_walls), 6),
        "reference_operation_count_max": max(reference_operations),
    }

    doubled = make_instance(
        n=2 * shipping_params["n"], seed=12345,
        trade_density=shipping_params["trade_density"])
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(shipping),
        "shipping_n": shipping_params["n"],
        "doubled_n": 2 * shipping_params["n"],
        "doubled_clause_count": len(doubled["clauses"]),
        "doubled_verify_reason": doubled_why,
        "shipping_candidate_bits": search_space(shipping).bit_length(),
        "doubled_candidate_bits": search_space(doubled).bit_length(),
    }

    invariant_checks = 0
    carried_checks = 0
    keys = []
    g8_failures = []
    for seed in range(20):
        inst = make_instance(seed=seed, **shipping_params)
        key = canonical_key(inst)
        keys.append(key)
        transformed = _relabel_instance(inst, random.Random(90_000 + seed))
        invariant_checks += 1
        if canonical_key(transformed) != key:
            g8_failures.append({"seed": seed, "reason": "key changed under relabeling"})
        ok, why = verify(transformed, transformed["answer"])
        carried_checks += 1
        if not ok:
            g8_failures.append({"seed": seed, "reason": "carried witness: " + why})
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated_keys": distinct,
        "unrelated_instances": 20,
        "transformations": [
            "arbitrary variable relabeling",
            "clause reordering",
            "within-clause reordering",
            "their composition",
        ],
        "failures": g8_failures,
    }

    answer_chars = max(
        len(json.dumps(make_instance(seed=seed, **shipping_params)["answer"]))
        for seed in range(128)
    )
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(shipping["answer"])
    intended_operations = 4 * shipping["class_size"]
    arms = {
        name: dict(G9_ORACLE_RESULTS.get(name, {"solved": 0, "attempts": 0}))
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    within_caps = answer_chars <= 2000 and answer_elements <= 256 \
        and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS.get("hinted_verdict", "not yet run"),
        "placebo_verdict": G9_ORACLE_RESULTS.get("placebo_verdict", "not yet run"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
