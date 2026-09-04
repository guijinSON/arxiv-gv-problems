"""Verified Track-B generator from arXiv:1402.1429.

The paper encodes a 3SAT clause as a factored cubic over sign variables in
Section 4, equation (4.3).  Four such cubics encode one ternary parity equation.
This module plants a sign vector, derives a connected system of parity equations,
and emits only the shuffled cubic polynomials.  A submitted witness is checked by
exact integer substitution in every displayed polynomial.
"""

from __future__ import annotations

import collections
import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time


# Keep the repository helpers importable when this file is run from its own
# directory.  This family needs only integers, but the graceful import preserves
# the common module contract and does not add a dependency.
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # pragma: no cover - the generator is standard-library-only
    exact_matrices = rationals = None


TRACK = "B"

# The measured figures in hardness_basis are refreshed after the final selftest.
PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "rational_exact",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "factored cubic polynomials over Q",
        "sign-constrained complex variables",
    ],
    "verification_operations": [
        "exact integer substitution",
        "exact multiplication of linear factors",
        "equality comparison with zero",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 4, equation (4.3) and Theorem 4.1: a 3SAT clause is represented "
        "by a factored cubic over variables constrained by x_i^2=1."
    ),
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Group four cubics with the same support into one parity equation, then "
        "recognize the degree-two incidence structure and eliminate along a "
        "spanning tree; without that decomposition the input is a long shuffled "
        "list of unrelated-looking cubic constraints."
    ),
    "hardness_basis": (
        "Track B: grouping the cubic clauses followed by GF(2) Gaussian "
        "elimination solves the family in O(v*e*min(v,e)) bit operations; a "
        "shipping calibration averaged approximately 0.0029 seconds and 63,392 "
        "coefficient "
        "XORs, while the compact spanning-tree route uses 256 exact sign "
        "operations once the hidden incidence decomposition is recognized."
    ),
    "max_answer_tokens": 145,
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
    "demo": {"n": 4},
    "easy": {"n": 32},
    "medium": {"n": 64},
    "hard": {"n": 128},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Group equal three-variable supports into parity equations, view variables "
    "as incidences occurring twice, and eliminate signs from the leaves of a "
    "spanning tree."
)
PLACEBO_HINT = (
    "Keep the variable indices and factor signs carefully aligned while checking "
    "the long list of exact equations."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list giving one sign (+1 or -1) for every variable, in variable "
        "index order; the shipping language has exactly 192 signs and all 2^192 "
        "such lists are sampled uniformly by random_candidate."
    ),
    "bounds": {
        "atomic_alphabet": 2,
        "max_signs_at_shipping": 192,
        "entry_numerator_bits": 1,
        "entry_denominator": 1,
    },
}

NOTES = (
    "Section 2, Definition 2.2 and Lemma 4.1 fix strict positivity and its "
    "nonzero bilinear witness. Section 4, equation (4.3), Lemma 4.3, Lemma 4.4, "
    "and Theorems 4.1-4.2 fix the sign-polynomial encoding and the hard regime. "
    "Corollary 3.1 is the important easy result: irreducibility and primitivity, "
    "unlike strict positivity, are polynomial-time checks. For this generated "
    "subclass, parity recognition and GF(2) elimination are also polynomial, so "
    "the family is honestly Track B rather than an unsupported average-case "
    "Track A claim. Plants and all non-tree degrees of freedom are uniform signs; "
    "clause order, factor order, and variable labels are shuffled. Exact literal "
    "balance defeats polarity/outlier scoring, and the measured greedy, one-pass "
    "repair, alternating-sign, and random-restart probes all fail."
)


# Updated from actual isolated harden.py runs before shipping.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


def _random_cubic_graph(vertex_count, rng):
    """A connected simple cubic graph: Hamiltonian cycle plus a matching."""
    order = list(range(vertex_count))
    rng.shuffle(order)
    cycle = []
    cycle_set = set()
    for i, u in enumerate(order):
        v = order[(i + 1) % vertex_count]
        edge = (min(u, v), max(u, v))
        cycle.append(edge)
        cycle_set.add(edge)

    # A random pairing avoids cycle neighbors with constant probability.  The
    # bounded fallback is deterministic and cannot be reached for supported n in
    # practice, but keeps make_instance total for every integer seed.
    matching = None
    for _ in range(10_000):
        paired = list(range(vertex_count))
        rng.shuffle(paired)
        trial = []
        good = True
        for i in range(0, vertex_count, 2):
            edge = (min(paired[i], paired[i + 1]), max(paired[i], paired[i + 1]))
            if edge in cycle_set:
                good = False
                break
            trial.append(edge)
        if good:
            matching = trial
            break
    if matching is None:
        # Pair opposite points of the known Hamiltonian order.  For even n >= 4
        # these are not cycle edges (at n=4 they are the two diagonals).
        half = vertex_count // 2
        matching = [
            (min(order[i], order[i + half]), max(order[i], order[i + half]))
            for i in range(half)
        ]
    edges = cycle + matching
    rng.shuffle(edges)
    return edges


def _clause_group(support, target, rng):
    """Four paper-style cubics whose common zeros have product=target."""
    clauses = []
    forbidden_product = -target
    for p in (-1, 1):
        for q in (-1, 1):
            r = forbidden_product * p * q
            literals = [[support[0], p], [support[1], q], [support[2], r]]
            rng.shuffle(literals)
            clauses.append(literals)
    return clauses


def make_instance(n, seed=0, **params):
    """Inverse-generate cubic equations from a uniformly planted sign vector."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 4 or n % 2:
        raise ValueError("n must be an even integer at least 4")
    rng = random.Random(seed)
    edges = _random_cubic_graph(n, rng)
    variable_count = len(edges)
    incident = [[] for _ in range(n)]
    for variable, (u, v) in enumerate(edges, 1):
        incident[u].append(variable)
        incident[v].append(variable)
    if any(len(row) != 3 for row in incident):
        raise AssertionError("constructed incidence system is not cubic")

    # This is the certificate.  Everything below is derived from it; no solving.
    answer = [rng.choice((-1, 1)) for _ in range(variable_count)]
    clauses = []
    for support in incident:
        target = math.prod(answer[j - 1] for j in support)
        clauses.extend(_clause_group(support, target, rng))
    rng.shuffle(clauses)
    return {
        "n_variables": variable_count,
        "n_equations": len(clauses),
        "clauses": clauses,
        "answer": answer,
    }


def _factor(variable, coefficient):
    sign = "+" if coefficient == 1 else "-"
    return f"(1 {sign} x{variable})"


def render(inst):
    rows = []
    for i, clause in enumerate(inst["clauses"], 1):
        polynomial = "".join(_factor(variable, coefficient) for variable, coefficient in clause)
        rows.append(f"  {i}: {polynomial} = 0")
    parts = [
        "Find a common zero of the following exact polynomial system.\n\n",
        f"There are {inst['n_variables']} variables x1,...,x{inst['n_variables']}. "
        "Every variable must be a sign: xj is either -1 or +1 (equivalently, "
        "xj^2=1). Every displayed product is an ordinary polynomial over the "
        "rational numbers. A row is satisfied exactly when its integer value "
        "after substitution is zero. Row order and factor order carry no "
        "meaning. Variable indices are 1-based.\n\n",
        f"The {inst['n_equations']} equations are:\n",
        "\n".join(rows),
        "\n\nReturn exactly one sign for each variable, in the order "
        f"[x1,x2,...,x{inst['n_variables']}]. Use a JSON list containing only the "
        "integers -1 and 1; order matters and no entry may be omitted or repeated.\n",
    ]
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        parts.extend(["\nHint: ", STRUCTURAL_HINT, "\n"])
    elif mode == "placebo":
        parts.extend(["\nHint: ", PLACEBO_HINT, "\n"])
    parts.extend(
        [
            "\nGive your final answer inside <answer></answer> tags, as the JSON "
            "list just specified.\n",
            "Example of the required syntax: <answer>[1,-1,1]</answer>\n",
            "Output nothing else inside the tags.",
        ]
    )
    return "".join(parts)


def parse_answer(text):
    """Parse the last delimited JSON list, tolerating prose and code fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, list) else None


def _answer_shape(inst, answer):
    expected = inst.get("n_variables")
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer must not be empty"
    if len(answer) != expected:
        return False, f"answer has {len(answer)} signs; expected {expected}"
    for i, value in enumerate(answer, 1):
        if not isinstance(value, int) or isinstance(value, bool) or value not in (-1, 1):
            return False, f"entry {i} is not +1 or -1"
    return True, "ok"


def verify(inst, answer):
    """Evaluate every supplied cubic exactly; never inspect inst['answer']."""
    if not isinstance(inst, dict):
        return False, "malformed instance"
    valid, reason = _answer_shape(inst, answer)
    if not valid:
        return False, reason
    clauses = inst.get("clauses")
    if not isinstance(clauses, list) or len(clauses) != inst.get("n_equations"):
        return False, "malformed instance equation list"
    for row_number, clause in enumerate(clauses, 1):
        if not isinstance(clause, list) or len(clause) != 3:
            return False, f"malformed polynomial equation {row_number}"
        value = 1
        for literal in clause:
            if not isinstance(literal, list) or len(literal) != 2:
                return False, f"malformed factor in polynomial equation {row_number}"
            variable, coefficient = literal
            if (
                not isinstance(variable, int)
                or isinstance(variable, bool)
                or variable < 1
                or variable > inst["n_variables"]
                or coefficient not in (-1, 1)
            ):
                return False, f"malformed factor in polynomial equation {row_number}"
            value *= 1 + coefficient * answer[variable - 1]
        if value != 0:
            return False, f"polynomial equation {row_number} evaluates to {value}, not 0"
    return True, "ok"


def _extract_groups(inst):
    """Recover ternary parity equations solely from the displayed cubics."""
    n_variables = inst.get("n_variables")
    clauses = inst.get("clauses")
    if not isinstance(n_variables, int) or not isinstance(clauses, list):
        return None
    grouped = collections.defaultdict(list)
    for clause in clauses:
        if not isinstance(clause, list) or len(clause) != 3:
            return None
        by_variable = {}
        for literal in clause:
            if not isinstance(literal, list) or len(literal) != 2:
                return None
            variable, coefficient = literal
            if (
                not isinstance(variable, int)
                or variable < 1
                or variable > n_variables
                or variable in by_variable
                or coefficient not in (-1, 1)
            ):
                return None
            by_variable[variable] = coefficient
        support = tuple(sorted(by_variable))
        grouped[support].append(tuple(by_variable[v] for v in support))
    out = []
    for support, patterns in grouped.items():
        if len(patterns) != 4 or len(set(patterns)) != 4:
            return None
        products = {math.prod(pattern) for pattern in patterns}
        if len(products) != 1:
            return None
        forbidden_product = next(iter(products))
        expected = {
            pattern
            for pattern in itertools.product((-1, 1), repeat=3)
            if math.prod(pattern) == forbidden_product
        }
        if set(patterns) != expected:
            return None
        out.append((support, -forbidden_product))
    out.sort()
    return out


def random_candidate(inst, rng):
    """Uniformly sample the full statement-visible sign-vector language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    count = inst.get("n_variables")
    if not isinstance(count, int) or count < 1:
        raise ValueError("malformed instance")
    return [rng.choice((-1, 1)) for _ in range(count)]


def search_space(inst):
    count = inst.get("n_variables") if isinstance(inst, dict) else None
    return 2**count if isinstance(count, int) and count >= 0 else 0


def enumerate_all(inst):
    count = inst.get("n_variables") if isinstance(inst, dict) else None
    if not isinstance(count, int) or count < 0 or count > 22:
        return None
    valid = 0
    for bits in itertools.product((-1, 1), repeat=count):
        valid += int(verify(inst, list(bits))[0])
    return valid


def _incidence_graph(groups, n_variables):
    occurrences = [[] for _ in range(n_variables + 1)]
    for vertex, (support, _target) in enumerate(groups):
        for variable in support:
            occurrences[variable].append(vertex)
    if any(len(occurrences[v]) != 2 for v in range(1, n_variables + 1)):
        return None
    adjacency = [set() for _ in groups]
    for variable in range(1, n_variables + 1):
        u, v = occurrences[variable]
        if u == v:
            return None
        adjacency[u].add(v)
        adjacency[v].add(u)
    if any(len(row) != 3 for row in adjacency):
        return None
    return adjacency, occurrences


def _rooted_refinement_digest(adjacency, root):
    """Label-invariant individualization/refinement fingerprint of a cubic graph."""
    size = len(adjacency)
    colors = [1 if v == root else 0 for v in range(size)]
    history = []
    for _ in range(size):
        signatures = [
            (colors[v], tuple(sorted(colors[w] for w in adjacency[v])))
            for v in range(size)
        ]
        palette = {sig: i for i, sig in enumerate(sorted(set(signatures)))}
        new_colors = [palette[sig] for sig in signatures]
        history.append(tuple(sorted(collections.Counter(new_colors).items())))
        if new_colors == colors:
            break
        colors = new_colors
    if len(set(colors)) == size:
        order = sorted(range(size), key=lambda v: colors[v])
        position = {v: i for i, v in enumerate(order)}
        canonical_edges = sorted(
            (min(position[u], position[v]), max(position[u], position[v]))
            for u in range(size)
            for v in adjacency[u]
            if u < v
        )
        payload = ["individualized", canonical_edges]
    else:
        vertex_types = sorted(
            (colors[v], tuple(sorted(colors[w] for w in adjacency[v])))
            for v in range(size)
        )
        edge_types = sorted(
            (min(colors[u], colors[v]), max(colors[u], colors[v]))
            for u in range(size)
            for v in adjacency[u]
            if u < v
        )
        payload = ["refined", history, vertex_types, edge_types]
    encoded = json.dumps(payload, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


def canonical_key(inst):
    """Invariant under equation/factor/variable relabeling and sign switching."""
    groups = _extract_groups(inst) if isinstance(inst, dict) else None
    if groups is None:
        return "malformed"
    graph = _incidence_graph(groups, inst["n_variables"])
    if graph is None:
        return "malformed"
    adjacency, _occurrences = graph
    # Charges are deliberately absent: independently replacing x_j by -x_j is a
    # relabeling of the two-element domain and switches the adjacent charges.
    rooted = sorted(
        _rooted_refinement_digest(adjacency, root) for root in range(len(adjacency))
    )
    payload = json.dumps(
        [len(adjacency), inst["n_variables"], rooted], separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params):
    n = params.get("n") if isinstance(params, dict) else None
    if not isinstance(n, int) or n >= 132:
        return None
    return {"n": 132}


def _reference_gaussian(inst):
    """Generic exact GF(2) elimination after recovering the parity groups."""
    groups = _extract_groups(inst)
    if groups is None:
        return None, {"coefficient_xors": 0, "row_xors": 0, "pivots": 0}
    n_variables = inst["n_variables"]
    matrix = []
    for support, target in groups:
        row = [0] * (n_variables + 1)
        for variable in support:
            row[variable - 1] = 1
        row[-1] = int(target == -1)
        matrix.append(row)
    rank = 0
    pivots = []
    row_xors = 0
    coefficient_xors = 0
    for column in range(n_variables):
        pivot = next((r for r in range(rank, len(matrix)) if matrix[r][column]), None)
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        for r in range(len(matrix)):
            if r != rank and matrix[r][column]:
                for c in range(column, n_variables + 1):
                    matrix[r][c] ^= matrix[rank][c]
                    coefficient_xors += 1
                row_xors += 1
        pivots.append(column)
        rank += 1
        if rank == len(matrix):
            break
    for row in matrix:
        if not any(row[:-1]) and row[-1]:
            return None, {
                "coefficient_xors": coefficient_xors,
                "row_xors": row_xors,
                "pivots": rank,
            }
    bits = [0] * n_variables
    for row_index, column in enumerate(pivots):
        bits[column] = matrix[row_index][-1]
    answer = [-1 if bit else 1 for bit in bits]
    return answer, {
        "coefficient_xors": coefficient_xors,
        "row_xors": row_xors,
        "pivots": rank,
    }


def _spanning_tree_solution(inst):
    """The intended compact route, using the incidence decomposition."""
    groups = _extract_groups(inst)
    if groups is None:
        return None, 0
    graph = _incidence_graph(groups, inst["n_variables"])
    if graph is None:
        return None, 0
    adjacency, occurrences = graph
    pair_to_variable = {}
    for variable in range(1, inst["n_variables"] + 1):
        u, v = occurrences[variable]
        pair_to_variable[frozenset((u, v))] = variable
    parent = [-1] * len(groups)
    parent_edge = [None] * len(groups)
    parent[0] = 0
    order = [0]
    for u in order:
        for v in sorted(adjacency[u]):
            if parent[v] == -1:
                parent[v] = u
                parent_edge[v] = pair_to_variable[frozenset((u, v))]
                order.append(v)
    if len(order) != len(groups):
        return None, 0
    tree_edges = {edge for edge in parent_edge[1:] if edge is not None}
    answer = [1] * inst["n_variables"]
    operations = 0
    for vertex in reversed(order[1:]):
        edge = parent_edge[vertex]
        other = [e for e in groups[vertex][0] if e != edge]
        product = answer[other[0] - 1] * answer[other[1] - 1]
        operations += 1
        answer[edge - 1] = groups[vertex][1] * product
        operations += 1
    # Checking the root costs two more exact sign multiplications.
    root_support, root_target = groups[0]
    root_value = answer[root_support[0] - 1] * answer[root_support[1] - 1]
    operations += 1
    root_value *= answer[root_support[2] - 1]
    operations += 1
    if root_value != root_target:
        return None, operations
    # Non-tree signs were initialized to +1, exactly as the route prescribes.
    if any(answer[e - 1] != 1 for e in range(1, inst["n_variables"] + 1) if e not in tree_edges):
        raise AssertionError("non-tree variable changed during leaf elimination")
    return answer, operations


def _literal_balance_candidate(inst):
    score = [0] * inst["n_variables"]
    for clause in inst["clauses"]:
        for variable, coefficient in clause:
            score[variable - 1] += coefficient
    return [1 if value >= 0 else -1 for value in score]


def _greedy_clause_candidate(inst):
    answer = [1] * inst["n_variables"]
    for clause in inst["clauses"]:
        value = math.prod(1 + coefficient * answer[variable - 1] for variable, coefficient in clause)
        if value != 0:
            variable, _coefficient = clause[0]
            answer[variable - 1] *= -1
    return answer


def _single_sweep_repair_candidate(inst):
    groups = _extract_groups(inst)
    answer = [1] * inst["n_variables"]
    for support, target in groups or []:
        if math.prod(answer[v - 1] for v in support) != target:
            answer[min(support) - 1] *= -1
    return answer


def _attack_candidates(inst, seed):
    rng = random.Random(seed ^ 0x14021429)
    return {
        "outlier_literal_balance": [_literal_balance_candidate(inst)],
        "greedy_first_violated_clause": [_greedy_clause_candidate(inst)],
        "by_hand_single_sweep_parity_repair": [_single_sweep_repair_candidate(inst)],
        "alternating_sign_ansatz": [
            [1 if i % 2 == 0 else -1 for i in range(inst["n_variables"])]
        ],
        "random_restart_256_sign_vectors": [
            random_candidate(inst, rng) for _ in range(256)
        ],
    }


def _relabel_variants(inst, seed):
    rng = random.Random(seed)
    count = inst["n_variables"]
    permutation = list(range(count))
    rng.shuffle(permutation)  # old zero-based index -> new zero-based index
    flips = [rng.choice((-1, 1)) for _ in range(count)]
    variants = []
    for mask in range(1, 8):
        clauses = []
        for clause in inst["clauses"]:
            transformed = []
            for variable, coefficient in clause:
                old = variable - 1
                new = permutation[old] if mask & 1 else old
                new_coefficient = coefficient * flips[old] if mask & 2 else coefficient
                transformed.append([new + 1, new_coefficient])
            if mask & 4:
                rng.shuffle(transformed)
            clauses.append(transformed)
        if mask & 4:
            rng.shuffle(clauses)
        answer = [0] * count
        for old, value in enumerate(inst["answer"]):
            new = permutation[old] if mask & 1 else old
            answer[new] = value * flips[old] if mask & 2 else value
        variants.append(
            {
                "n_variables": count,
                "n_equations": len(clauses),
                "clauses": clauses,
                "answer": answer,
            }
        )
    return variants


def selftest():
    report = {}
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    inst = make_instance(seed=19, **shipping)
    answer = inst["answer"]
    swap = None
    for i in range(len(answer)):
        for j in range(i + 1, len(answer)):
            if answer[i] != answer[j]:
                candidate = list(answer)
                candidate[i], candidate[j] = candidate[j], candidate[i]
                if not verify(inst, candidate)[0]:
                    swap = candidate
                    break
        if swap is not None:
            break
    corruptions = {
        "drop": answer[:-1],
        "swap": swap if swap is not None else list(reversed(answer)),
        "duplicate": [answer[0]] + list(answer),
        "empty": [],
        "out_of_range": [0] + answer[1:],
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = [value["reason"] for value in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(value["rejected"] for value in rejected.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "I grouped the repeated supports and eliminated on a tree.\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nThis is the sign vector."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x14021429)
    guess_total = 200_000
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "candidate_space_bits": inst["n_variables"],
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = [
        "outlier_literal_balance",
        "greedy_first_violated_clause",
        "by_hand_single_sweep_parity_repair",
        "alternating_sign_ansatz",
        "random_restart_256_sign_vectors",
    ]
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    coefficient_xors = 0
    row_xors = 0
    pivots = 0
    compact_successes = 0
    compact_seconds = 0.0
    compact_operations = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        candidates = _attack_candidates(trial, seed)
        for name in attack_names:
            start = time.perf_counter()
            won = any(verify(trial, candidate)[0] for candidate in candidates[name])
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(won)
        start = time.perf_counter()
        recovered, counts = _reference_gaussian(trial)
        reference_seconds += time.perf_counter() - start
        reference_successes += int(recovered is not None and verify(trial, recovered)[0])
        coefficient_xors += counts["coefficient_xors"]
        row_xors += counts["row_xors"]
        pivots += counts["pivots"]
        start = time.perf_counter()
        compact, operations = _spanning_tree_solution(trial)
        compact_seconds += time.perf_counter() - start
        compact_successes += int(compact is not None and verify(trial, compact)[0])
        compact_operations += operations
    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "group cubics, then dense GF(2) Gaussian elimination",
        "complexity": "O(v*e*min(v,e)) coefficient XORs",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": coefficient_xors // 8,
        "row_xors": row_xors // 8,
        "pivots": pivots // 8,
        "solves": f"{reference_successes}/8, as expected",
        "compact_route": "incidence spanning-tree leaf elimination",
        "compact_route_wall_clock_sec": round(compact_seconds / 8, 6),
        "compact_route_operations": compact_operations // 8,
        "compact_route_solves": f"{compact_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
    }

    vertex_count = 2 * inst["n_variables"] // 3
    exact_valid_answers = 2 ** (inst["n_variables"] - vertex_count + 1)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6 and all_failed and reference_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density": guess_fraction,
        "shipping_exact_valid_answer_count_by_incidence_rank": exact_valid_answers,
        "shipping_exact_density_denominator": 2 ** (vertex_count - 1),
        "demo_exact_solution_count": enumerate_all(
            make_instance(seed=3, **DIFFICULTY["demo"])
        ),
        "baseline_attack_wall_clock_sec": round(
            attack_seconds["random_restart_256_sign_vectors"] / 8, 6
        ),
        "baseline_attack_iterations": 256,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
    }

    doubled_params = {"n": shipping["n"] * 2}
    start = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    ladder_sizes = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n_variables"] == 2 * inst["n_variables"]
        and len(render(doubled)) > len(render(inst))
        and ladder_sizes == sorted(ladder_sizes)
        and len(set(ladder_sizes)) == len(ladder_sizes),
        "shipping_n": shipping["n"],
        "doubled_n": doubled_params["n"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_why,
        "candidate_space_bits_shipping": inst["n_variables"],
        "candidate_space_bits_doubled": doubled["n_variables"],
    }

    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping)
        original_key = canonical_key(original)
        for transformed in _relabel_variants(original, seed ^ 0x5A5A):
            if original_key == canonical_key(transformed):
                invariant_count += 1
            if verify(transformed, transformed["answer"])[0]:
                real_transform_count += 1
        unrelated_keys.append(original_key)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == 140
        and real_transform_count == 140
        and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "real_transformations_verified": real_transform_count,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "variable permutation",
            "independent sign-domain switching",
            "equation and factor reordering",
            "all compositions",
        ],
    }

    # -1 takes one more character than +1, so the all-negative vector is the
    # exact worst-case serialization at this fixed answer length.
    encoded_answer = json.dumps(
        [-1] * inst["n_variables"], separators=(",", ":")
    )
    answer_chars = len(encoded_answer)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(inst["answer"])
    _compact_answer, intended_ops = _spanning_tree_solution(inst)
    arms = {
        key: dict(G9_ORACLE_RESULTS[key]) for key in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": G9_ORACLE_RESULTS["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
