"""Rejected prototype generator for Theorem 10 of arXiv:1806.03426.

Kiraĺy and Pálvölgyi reduce NAE-3-SAT to an acyclic orientation in which
every vertex other than a designated source and sink has at least two incoming
and two outgoing edges.  This module inverse-generates a balanced, regular NAE
formula together with a satisfying assignment, presents the exact multigraph
from that reduction, and uses the assignment as the paper's compact encoding
of a topological-order witness.

This file is retained as audit evidence.  A standard break-count WalkSAT
attack solves the shipping distribution, so the family fails Track A's H gate
and must not be shipped.  Only the Python standard library is used.  Importing
the module performs no I/O and prints nothing.
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


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "logic",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "Theorem 10 skeleton/literal/clause multigraph",
        "source and sink with two-path degree requirements",
        "signed Boolean assignment encoding a topological order",
    ],
    "verification_operations": [
        "exact NAE clause evaluation",
        "construction of the paper's topological order",
        "integer predecessor and successor edge counts with multiplicity",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3.1, Theorem 10 (NAE-3-SAT to Problem 1 with k = l = 2)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Coordinate the early/late choice of each complementary literal pair so "
        "every clause gadget sees at least one literal on each side; without this "
        "global invariant one faces the full Boolean assignment space."
    ),
    "hardness_basis": (
        "Rejected Track A attempt: although Theorem 10 proves worst-case "
        "NP-completeness for k = l = 2, standard break-count WalkSAT solves "
        "8/8 generated shipping instances in milliseconds, so the theorem "
        "does not establish hardness for this planted distribution."
    ),
    "max_answer_tokens": 191,
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
    "demo": {"n": 6, "degree": 2},
    "easy": {"n": 174, "degree": 6},
    "medium": {"n": 174, "degree": 8},
    "hard": {"n": 216, "degree": 8},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Each clause vertex records whether its three incident literal choices occupy "
    "both the early and late sides of the skeleton."
)
PLACEBO_HINT = (
    "Each indexed vertex requires careful attention to the displayed naming and "
    "ordering conventions in the skeleton."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of n signed, nonzero integers in variable order: +(i+1) "
        "sets variable i true and -(i+1) sets it false.  Global complementation "
        "preserves NAE, so the bounded canonical language fixes the first entry "
        "to -1; verify also accepts valid complementary witnesses."
    ),
    "bounds": {
        "length": "n",
        "absolute_values": "exactly 1 through n in increasing slot order",
        "signs": 2,
        "canonical_first_sign": "negative",
        "candidate_count": "2 ** (n - 1)",
    },
}

NOTES = (
    "Section 1, Problem 1 and Claim 1 fix the path/orientation and topological-"
    "order definitions. Section 2 is the essential easy-regime warning: Theorem "
    "2 is greedy when only indegree lower bounds remain, Theorem 3 is polynomial "
    "when f(v)g(v)=0 vertexwise, and Theorem 4 is greedy when every vertex is "
    "strict. Theorem 9 also makes k=l=1 polynomial by st-numbering. The generator "
    "therefore uses exactly Theorem 10's k=l=2 multigraph reduction. It samples "
    "the NAE assignment before any clauses, balances every variable equally "
    "between true/false-at-the-plant occurrences, gives every variable the same "
    "degree, balances one-true and two-true clauses, rejects repeated constraints, "
    "and shuffles all labels and incidences. A correct break-count WalkSAT audit "
    "solves every shipping seed quickly. The earlier random-flip probe was not a "
    "domain-standard local-search attack and produced a false pass. Theorem 10 is "
    "worst-case only, so this generated distribution is rejected on Track A."
)


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_DPLL_NODE_LIMIT = 4_000
_GUESS_SAMPLES = 200_000

# Filled after the harness-owned bare/hinted/placebo runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3, "errors": 0},
    "hinted": {"solved": 0, "attempts": 0, "errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted_verdict": "unavailable_key_limit",
    "diagnostic_status": (
        "Bare completed 0/3; hinted and placebo produced no countable attempts "
        "because OpenRouter returned HTTP 403 key-limit errors on every redraw."
    ),
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _normalise_params(n, degree):
    if not _is_int(n) or not _is_int(degree):
        raise TypeError("n and degree must be integers")
    if n < 6:
        raise ValueError("n must be at least 6")
    if degree < 2 or degree % 2:
        raise ValueError("degree must be a positive even integer")
    if (n * degree) % 6:
        raise ValueError("n*degree must be divisible by 6")
    return n, degree


def _literal_value(literal, assignment):
    variable, positive = literal
    return assignment[variable] if positive else 1 - assignment[variable]


def _clause_satisfied(clause, assignment):
    a = _literal_value(clause[0], assignment)
    b = _literal_value(clause[1], assignment)
    c = _literal_value(clause[2], assignment)
    return not (a == b == c)


def _all_satisfied(clauses, assignment):
    return all(_clause_satisfied(clause, assignment) for clause in clauses)


def _constraint_signature(clause):
    """NAE ignores literal order and complementing all three polarities."""

    first = tuple(sorted((int(v), int(bool(p))) for v, p in clause))
    complement = tuple(sorted((v, 1 - p) for v, p in first))
    return min(first, complement)


def _connected_incidence(n, clauses):
    adjacency = [set() for _ in range(n)]
    for clause in clauses:
        variables = [literal[0] for literal in clause]
        for i in range(3):
            for j in range(i + 1, 3):
                adjacency[variables[i]].add(variables[j])
                adjacency[variables[j]].add(variables[i])
    seen = {0}
    stack = [0]
    while stack:
        vertex = stack.pop()
        for neighbor in adjacency[vertex]:
            if neighbor not in seen:
                seen.add(neighbor)
                stack.append(neighbor)
    return len(seen) == n


def _regular_planted_formula(n, degree, plant, rng):
    """Return a regular, polarity-balanced NAE formula satisfied by plant.

    For each variable, degree/2 literal occurrences are true at the plant and
    degree/2 are false.  Exactly half the clauses have one true literal and half
    have two.  Thus the plant has no one-variable degree or polarity signature.
    """

    clause_count = n * degree // 3
    true_pool_template = [v for v in range(n) for _ in range(degree // 2)]
    false_pool_template = list(true_pool_template)
    kinds_template = [1] * (clause_count // 2) + [2] * (clause_count // 2)

    for _ in range(25_000):
        true_pool = true_pool_template[:]
        false_pool = false_pool_template[:]
        kinds = kinds_template[:]
        rng.shuffle(true_pool)
        rng.shuffle(false_pool)
        rng.shuffle(kinds)
        true_at = false_at = 0
        clauses = []
        signatures = set()
        failed = False

        for true_count in kinds:
            selected = []
            selected.extend(
                (v, 1) for v in true_pool[true_at:true_at + true_count]
            )
            selected.extend(
                (v, 0)
                for v in false_pool[false_at:false_at + 3 - true_count]
            )
            true_at += true_count
            false_at += 3 - true_count
            if len({v for v, _ in selected}) != 3:
                failed = True
                break

            clause = []
            for variable, truth_at_plant in selected:
                positive = bool(plant[variable]) == bool(truth_at_plant)
                clause.append([variable, positive])
            rng.shuffle(clause)
            signature = _constraint_signature(clause)
            if signature in signatures:
                failed = True
                break
            signatures.add(signature)
            clauses.append(clause)

        if not failed and _connected_incidence(n, clauses):
            rng.shuffle(clauses)
            return clauses
    raise RuntimeError("could not construct a simple connected regular formula")


def _encode_assignment(assignment):
    return [i + 1 if bit else -(i + 1) for i, bit in enumerate(assignment)]


def _decode_answer_shape(inst, answer):
    if not isinstance(answer, list):
        return None, "malformed answer: expected a JSON list"
    if not answer:
        return None, "empty answer: expected one signed integer per variable"
    n = inst["n"]
    if len(answer) != n:
        return None, f"wrong length: expected {n} entries, got {len(answer)}"
    if any(not _is_int(value) or value == 0 for value in answer):
        return None, "entries must be nonzero integers"
    if any(abs(value) > n for value in answer):
        return None, f"literal index out of range: absolute values must be 1..{n}"
    absolute = [abs(value) for value in answer]
    if len(set(absolute)) != n:
        return None, "duplicate variable index in signed assignment"
    for slot, value in enumerate(answer, 1):
        if abs(value) != slot:
            return None, f"slot {slot} must name variable {slot}"
    return [int(value > 0) for value in answer], "ok"


def _build_instance(n, degree, clauses, assignment):
    answer_assignment = list(assignment)
    if answer_assignment[0]:
        answer_assignment = [1 - bit for bit in answer_assignment]
    return {
        "paper": "arXiv:1806.03426v1",
        "family": "Theorem 10 k=l=2 orientation image of regular NAE-3-SAT",
        "n": n,
        "degree": degree,
        "clause_count": len(clauses),
        "clauses": clauses,
        "graph_vertex_count": 8 * n + 3 * len(clauses) + 2,
        "answer": _encode_assignment(answer_assignment),
    }


def make_instance(n, seed=0, **params):
    """Inverse-generate the paper's Theorem 10 multigraph and its witness."""

    degree = params.pop("degree", 6)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    n, degree = _normalise_params(n, degree)
    if not _is_int(seed):
        raise TypeError("seed must be an integer")
    rng = random.Random(seed)
    plant = [rng.randrange(2) for _ in range(n)]
    clauses = _regular_planted_formula(n, degree, plant, rng)
    return _build_instance(n, degree, clauses, plant)


def _literal_name(variable, positive):
    return ("x" if positive else "~x") + str(variable + 1)


def _topological_order(inst, assignment):
    n = inst["n"]
    m = inst["clause_count"]
    middle = [f"y{i}" for i in range(1, n + 1)]
    middle.extend(f"C{j}" for j in range(1, m + 1))
    middle.extend(f"z{i}" for i in range(1, n + 1))
    early = []
    late = []
    for i, bit in enumerate(assignment):
        early.append(_literal_name(i, bool(bit)))
        late.append(_literal_name(i, not bool(bit)))

    order = ["a0"]
    last_middle = len(middle)
    for position, vertex in enumerate(middle, 1):
        order.append(f"a{2 * position - 1}")
        if position == 1:
            order.extend(early)
        order.append(vertex)
        if position == last_middle:
            order.extend(late)
        order.append(f"a{2 * position}")
    order.append(f"a{2 * last_middle + 1}")
    return order


def _graph_edges(inst):
    """Build the exact multiedge list in Theorem 10."""

    n = inst["n"]
    m = inst["clause_count"]
    length = 2 * n + m
    edges = []

    for i in range(length + 1):
        u, v = f"a{2 * i}", f"a{2 * i + 1}"
        edges.extend(((u, v), (u, v)))
    for i in range(1, length + 1):
        edges.append((f"a{2 * i - 1}", f"a{2 * i}"))
    for i in range(1, n + 1):
        edges.extend(
            (
                (f"a{2 * i - 1}", f"y{i}"),
                (f"y{i}", f"a{2 * i}"),
            )
        )
    for j in range(1, m + 1):
        offset = n + j
        edges.extend(
            (
                (f"a{2 * offset - 1}", f"C{j}"),
                (f"C{j}", f"a{2 * offset}"),
            )
        )
    for i in range(1, n + 1):
        offset = n + m + i
        edges.extend(
            (
                (f"a{2 * offset - 1}", f"z{i}"),
                (f"z{i}", f"a{2 * offset}"),
            )
        )
        for literal in (f"x{i}", f"~x{i}"):
            edges.extend(((literal, f"y{i}"), (literal, f"z{i}")))
            edges.extend((("a0", literal), ("a0", literal)))
            sink = f"a{2 * length + 1}"
            edges.extend(((literal, sink), (literal, sink)))
    for j, clause in enumerate(inst["clauses"], 1):
        for variable, positive in clause:
            edges.append((f"C{j}", _literal_name(variable, positive)))
    return edges


def render(inst):
    """Render the complete compact description of the theorem's multigraph."""

    n = inst["n"]
    m = inst["clause_count"]
    length = 2 * n + m
    lines = [
        "ACYCLIC ORIENTATION WITH TWO-SIDED DEGREE CONSTRAINTS",
        "",
        "A multigraph may contain parallel edges but no loops.  An ordering of its",
        "vertices orients every edge from the earlier endpoint to the later endpoint,",
        "and is therefore acyclic.  Edge multiplicity counts toward degree.",
        "",
        f"Here n={n} and m={m}.  The instance has Boolean variables x1,...,x{n}",
        f"and clauses C1,...,C{m}.",
        "A positive literal xi has the value of xi; a negative literal ~xi has the",
        "opposite value.  A clause is NAE-satisfied when its three literal values are",
        "not all equal.",
        "",
        "The multigraph is specified by the following complete construction (all",
        "indices below are inclusive, and these are all its edges):",
        f"1. Skeleton vertices are a0,...,a{2 * length + 1}.  Put two parallel edges",
        f"   a(2i)--a(2i+1) for i=0,...,{length}, and one edge",
        f"   a(2i-1)--a(2i) for i=1,...,{length}.",
        f"2. For i=1,...,{n}, yi is adjacent to a(2i-1), a(2i), xi, and ~xi.",
        f"3. For j=1,...,{m}, Cj is adjacent to a(2n+2j-1), a(2n+2j),",
        "   and to the three literal vertices displayed in clause j below.",
        f"4. For i=1,...,{n}, zi is adjacent to",
        "   a(2n+2m+2i-1), a(2n+2m+2i), xi, and ~xi.",
        f"5. For every literal vertex xi and ~xi, put two parallel edges from a0",
        f"   to it and two parallel edges from it to a{2 * length + 1}.",
        "",
        f"The designated source is s=a0 and sink is t=a{2 * length + 1}.",
        "A witness must make every other graph vertex have at least two incident",
        "edges to earlier vertices and at least two incident edges to later vertices;",
        "parallel edges are counted separately.",
        "",
        "Your compact witness chooses each variable's truth value.  It denotes the",
        "following ordering: a0 first; each true literal vertex is placed immediately",
        "after a1; yi, then Cj, then zi occupy their indexed gaps in the skeleton;",
        "each false literal vertex is placed immediately before the last even-indexed",
        "skeleton vertex; and the final odd-indexed skeleton vertex is last.  Within",
        "either literal block, increasing variable index is used.  The checker builds",
        "this full order and checks every multiedge and degree bound exactly.",
        "",
        "Clauses (variables and clause numbers are 1-indexed):",
    ]
    for j, clause in enumerate(inst["clauses"], 1):
        rendered = " ".join(
            _literal_name(variable, positive) for variable, positive in clause
        )
        lines.append(f"C{j}: {rendered}")
    lines.extend(
        [
            "",
            f"Output exactly {n} signed integers in a JSON list, in variable order.",
            "+i means xi=true and -i means xi=false; absolute values must therefore",
            f"be exactly 1,2,...,{n}.  The first sign may be either sign, because",
            "globally complementing all values preserves every NAE clause.",
            "Give your final answer inside <answer></answer> tags.",
            "Syntax example for a hypothetical four-variable instance:",
            "<answer>[-1,2,-3,4]</answer>",
            f"For this instance your list must contain all {n} entries.",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(("", "Hint: " + STRUCTURAL_HINT))
    elif mode == "placebo":
        lines.extend(("", "Hint: " + PLACEBO_HINT))
    return "\n".join(lines)


def parse_answer(text):
    """Extract a signed-integer JSON list from tagged model output."""

    try:
        match = _ANSWER_RE.search(text)
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
        answer = json.loads(body)
        if not isinstance(answer, list) or any(not _is_int(x) for x in answer):
            return None
        return answer
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def verify(inst, answer):
    """Check any valid compact witness; never consult inst['answer']."""

    assignment, reason = _decode_answer_shape(inst, answer)
    if assignment is None:
        return False, reason
    for j, clause in enumerate(inst["clauses"], 1):
        if not _clause_satisfied(clause, assignment):
            return False, f"clause C{j} is monochromatic under the assignment"

    order = _topological_order(inst, assignment)
    if len(order) != inst["graph_vertex_count"] or len(set(order)) != len(order):
        return False, "internal order construction is not a vertex permutation"
    position = {vertex: i for i, vertex in enumerate(order)}
    indegree = {vertex: 0 for vertex in order}
    outdegree = {vertex: 0 for vertex in order}
    for u, v in _graph_edges(inst):
        if u not in position or v not in position:
            return False, "internal graph construction references an unknown vertex"
        if position[u] < position[v]:
            outdegree[u] += 1
            indegree[v] += 1
        else:
            outdegree[v] += 1
            indegree[u] += 1

    source = "a0"
    sink = f"a{2 * (2 * inst['n'] + inst['clause_count']) + 1}"
    for vertex in order:
        if vertex in (source, sink):
            continue
        if indegree[vertex] < 2:
            return False, f"vertex {vertex} has only {indegree[vertex]} earlier edges"
        if outdegree[vertex] < 2:
            return False, f"vertex {vertex} has only {outdegree[vertex]} later edges"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly after quotienting the obvious global complement."""

    assignment = [0]
    assignment.extend(rng.randrange(2) for _ in range(inst["n"] - 1))
    return _encode_assignment(assignment)


def search_space(inst):
    return 1 << (inst["n"] - 1)


def enumerate_all(inst):
    """Exact number of canonical witnesses for small instances."""

    if inst["n"] > 22:
        return None
    count = 0
    for tail in itertools.product((0, 1), repeat=inst["n"] - 1):
        if _all_satisfied(inst["clauses"], [0, *tail]):
            count += 1
    return count


def _pair_edges(inst, signed):
    weights = {}
    for clause in inst["clauses"]:
        for i in range(3):
            for j in range(i + 1, 3):
                vi, pi = clause[i]
                vj, pj = clause[j]
                if vi > vj:
                    vi, vj, pi, pj = vj, vi, pj, pi
                weight = (1 if pi else -1) * (1 if pj else -1) if signed else 1
                weights[(vi, vj)] = weights.get((vi, vj), 0) + weight
    return [(u, v, w) for (u, v), w in sorted(weights.items()) if w]


def _closed_walk_traces(n, edges, steps):
    prime = 1_000_000_007
    traces = [0] * (steps + 1)
    for start in range(n):
        vector = [0] * n
        vector[start] = 1
        for step in range(1, steps + 1):
            nxt = [0] * n
            for u, v, weight in edges:
                nxt[u] += weight * vector[v]
                nxt[v] += weight * vector[u]
            vector = [value % prime for value in nxt]
            traces[step] = (traces[step] + vector[start]) % prime
    return traces[2:]


def canonical_key(inst):
    """Strong switching/isomorphism invariant of the signed incidence data."""

    steps = min(10, inst["n"])
    payload = {
        "family": "theorem10-regular-nae-v1",
        "n": inst["n"],
        "m": inst["clause_count"],
        "degree_multiset": sorted(
            sum(variable == v for clause in inst["clauses"] for variable, _ in clause)
            for v in range(inst["n"])
        ),
        "unsigned_traces": _closed_walk_traces(
            inst["n"], _pair_edges(inst, False), steps
        ),
        "signed_traces": _closed_walk_traces(
            inst["n"], _pair_edges(inst, True), steps
        ),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params):
    """Tighten constraints first, then grow n up to the 256-atom cap."""

    n = int(params.get("n", 150))
    degree = int(params.get("degree", 6))
    if degree < 8:
        return {"n": n, "degree": 8}
    harder = n + 18
    if harder > 252:
        return "cap_bound"
    while (harder * degree) % 6:
        harder += 1
    if harder > 252:
        return "cap_bound"
    return {"n": harder, "degree": degree}


# ---------------------------------------------------------------------------
# Construction-aware adversaries


def _occurrences(inst):
    occurrences = [[] for _ in range(inst["n"])]
    for clause_index, clause in enumerate(inst["clauses"]):
        for variable, _ in clause:
            occurrences[variable].append(clause_index)
    return occurrences


def _bad_clause_set(inst, assignment):
    return {
        j
        for j, clause in enumerate(inst["clauses"])
        if not _clause_satisfied(clause, assignment)
    }


def _candidate_if_valid(inst, assignment):
    if assignment is None or not _all_satisfied(inst["clauses"], assignment):
        return None
    if assignment[0]:
        assignment = [1 - bit for bit in assignment]
    return _encode_assignment(assignment)


def _attack_outlier(inst, rng):
    del rng
    positive = [0] * inst["n"]
    negative = [0] * inst["n"]
    for clause in inst["clauses"]:
        for variable, sign in clause:
            (positive if sign else negative)[variable] += 1
    assignment = [int(positive[i] > negative[i]) for i in range(inst["n"])]
    return _candidate_if_valid(inst, assignment)


def _greedy_repair(inst, assignment, steps):
    occurrences = _occurrences(inst)
    bad = _bad_clause_set(inst, assignment)
    for _ in range(steps):
        if not bad:
            return assignment
        best_delta = 0
        best_variable = None
        for variable in range(inst["n"]):
            before = sum(index in bad for index in occurrences[variable])
            assignment[variable] ^= 1
            after = sum(
                not _clause_satisfied(inst["clauses"][index], assignment)
                for index in occurrences[variable]
            )
            assignment[variable] ^= 1
            delta = before - after
            if delta > best_delta:
                best_delta = delta
                best_variable = variable
        if best_variable is None:
            return None
        assignment[best_variable] ^= 1
        for index in occurrences[best_variable]:
            if _clause_satisfied(inst["clauses"][index], assignment):
                bad.discard(index)
            else:
                bad.add(index)
    return assignment if not bad else None


def _attack_greedy(inst, rng):
    del rng
    return _candidate_if_valid(
        inst, _greedy_repair(inst, [0] * inst["n"], 2 * inst["n"])
    )


def _walksat_search(inst, rng, restarts=32, flips_per_variable=100, noise=0.30):
    """Standard break-count WalkSAT specialized to NAE clauses.

    At each violated clause, choose a random variable with probability ``noise``;
    otherwise flip a variable minimizing the total number of violated incident
    clauses after the flip.  This is the construction-aware local-search attack
    that the earlier prototype accidentally omitted.
    """

    occurrences = _occurrences(inst)
    stats = {
        "restarts_started": 0,
        "flips": 0,
        "incident_clause_evaluations": 0,
        "restart_limit": restarts,
        "flips_per_restart": flips_per_variable * inst["n"],
    }
    for restart in range(restarts):
        stats["restarts_started"] = restart + 1
        assignment = [rng.randrange(2) for _ in range(inst["n"])]
        bad = _bad_clause_set(inst, assignment)
        for _ in range(flips_per_variable * inst["n"]):
            if not bad:
                return _candidate_if_valid(inst, assignment), stats
            clause_index = rng.choice(tuple(bad))
            variables = [literal[0] for literal in inst["clauses"][clause_index]]
            if rng.random() < noise:
                variable = rng.choice(variables)
            else:
                scored = []
                for candidate in variables:
                    assignment[candidate] ^= 1
                    score = sum(
                        not _clause_satisfied(inst["clauses"][affected], assignment)
                        for affected in occurrences[candidate]
                    )
                    assignment[candidate] ^= 1
                    stats["incident_clause_evaluations"] += len(
                        occurrences[candidate]
                    )
                    scored.append((score, rng.random(), candidate))
                variable = min(scored)[2]
            assignment[variable] ^= 1
            stats["flips"] += 1
            for affected in occurrences[variable]:
                if _clause_satisfied(inst["clauses"][affected], assignment):
                    bad.discard(affected)
                else:
                    bad.add(affected)
    return None, stats


def _attack_random_restart(inst, rng):
    return _walksat_search(inst, rng)[0]


class _DPLLLimit(Exception):
    pass


def _nae_propagate(clauses, assignment, stats):
    changed = True
    while changed:
        changed = False
        for clause in clauses:
            stats["clause_inspections"] += 1
            known = []
            unknown = []
            for variable, positive in clause:
                if assignment[variable] < 0:
                    unknown.append((variable, positive))
                else:
                    known.append(
                        assignment[variable]
                        if positive
                        else 1 - assignment[variable]
                    )
            if not unknown:
                if known[0] == known[1] == known[2]:
                    return False
                continue
            if len(unknown) == 1 and known[0] == known[1]:
                variable, positive = unknown[0]
                needed_literal = 1 - known[0]
                needed_value = needed_literal if positive else 1 - needed_literal
                if assignment[variable] >= 0 and assignment[variable] != needed_value:
                    return False
                if assignment[variable] < 0:
                    assignment[variable] = needed_value
                    stats["propagations"] += 1
                    changed = True
    return True


def _dpll_search(inst, node_limit=_DPLL_NODE_LIMIT):
    clauses = inst["clauses"]
    occurrence_count = [0] * inst["n"]
    for clause in clauses:
        for variable, _ in clause:
            occurrence_count[variable] += 1
    stats = {
        "nodes": 0,
        "node_limit": node_limit,
        "clause_inspections": 0,
        "propagations": 0,
        "limit_reached": False,
    }

    def solve(assignment):
        stats["nodes"] += 1
        if stats["nodes"] > node_limit:
            raise _DPLLLimit
        assignment = assignment[:]
        if not _nae_propagate(clauses, assignment, stats):
            return None
        if all(value >= 0 for value in assignment):
            return assignment
        unassigned = [i for i, value in enumerate(assignment) if value < 0]
        variable = max(unassigned, key=lambda i: (occurrence_count[i], -i))
        for value in (0, 1):
            child = assignment[:]
            child[variable] = value
            result = solve(child)
            if result is not None:
                return result
        return None

    initial = [-1] * inst["n"]
    initial[0] = 0
    try:
        result = solve(initial)
    except _DPLLLimit:
        result = None
        stats["limit_reached"] = True
    return _candidate_if_valid(inst, result), stats


def _attack_dpll(inst, rng):
    del rng
    return _dpll_search(inst)[0]


def _attack_spectral(inst, rng):
    n = inst["n"]
    edges = _pair_edges(inst, True)
    shift = 2 * inst["degree"] + 1.0
    vector = [rng.uniform(-1.0, 1.0) for _ in range(n)]
    for _ in range(100):
        nxt = [shift * value for value in vector]
        for u, v, weight in edges:
            nxt[u] -= weight * vector[v]
            nxt[v] -= weight * vector[u]
        norm = math.sqrt(sum(value * value for value in nxt)) or 1.0
        vector = [value / norm for value in nxt]
    base = [int(value >= 0.0) for value in vector]
    for assignment in (base, [1 - bit for bit in base]):
        candidate = _candidate_if_valid(inst, assignment)
        if candidate is not None:
            return candidate
        repaired = _greedy_repair(inst, assignment[:], 2 * n)
        candidate = _candidate_if_valid(inst, repaired)
        if candidate is not None:
            return candidate
    return None


def _run_attacks(params, seeds):
    attacks = {
        "outlier_polarity_and_degree": _attack_outlier,
        "greedy_best_improvement": _attack_greedy,
        "walksat_breakcount_32x100n": _attack_random_restart,
        "spectral_signed_pair_matrix": _attack_spectral,
        "dpll_unit_propagation_4000": _attack_dpll,
    }
    instances = [(seed, make_instance(seed=seed, **params)) for seed in seeds]
    report = {}
    for name, attack in attacks.items():
        successes = 0
        outcomes = []
        for seed, inst in instances:
            candidate = attack(inst, random.Random(900_000 + seed))
            if candidate is None:
                outcomes.append("no candidate")
                continue
            ok, reason = verify(inst, candidate)
            successes += int(ok)
            outcomes.append(reason)
        report[name] = {
            "successes": successes,
            "attempts": len(seeds),
            "results": outcomes,
        }
    return report


def _transform_instance(inst, rng):
    """Apply variable permutation, coordinate flips, and input reorderings."""

    n = inst["n"]
    permutation = list(range(n))
    rng.shuffle(permutation)
    flips = [rng.randrange(2) for _ in range(n)]
    transformed_clauses = []
    for clause in inst["clauses"]:
        transformed = []
        for variable, positive in clause:
            transformed.append(
                [permutation[variable], bool(positive) ^ bool(flips[variable])]
            )
        rng.shuffle(transformed)
        transformed_clauses.append(transformed)
    rng.shuffle(transformed_clauses)

    old_assignment, reason = _decode_answer_shape(inst, inst["answer"])
    if old_assignment is None:
        raise AssertionError(reason)
    new_assignment = [0] * n
    for old in range(n):
        new_assignment[permutation[old]] = old_assignment[old] ^ flips[old]
    transformed = _build_instance(
        n, inst["degree"], transformed_clauses, new_assignment
    )
    return transformed, transformed["answer"]


def _answer_atoms(answer):
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest():
    """Run all required generation, grading, attack, scale, and key gates."""

    report = {
        "paper": "1806.03426",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    g1_rows = {}
    g1_pass = True
    for preset, params in DIFFICULTY.items():
        rows = []
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            json_native = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            rows.append(
                {"seed": seed, "verified": ok, "reason": reason, "json": json_native}
            )
            g1_pass &= ok and json_native
        g1_rows[preset] = rows
    report["G1_planted_verifies"] = {"pass": g1_pass, "presets": g1_rows}

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=12_345, **shipping)
    answer = inst["answer"][:]
    corruptions = {
        "drop_one": answer[:-1],
        "swap_two_slots": [answer[1], answer[0], *answer[2:]],
        "duplicate_variable": [answer[0], answer[0], *answer[2:]],
        "empty": [],
        "out_of_range": [inst["n"] + 1, *answer[1:]],
    }
    corruption_rows = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_rows[name] = {"accepted": ok, "reason": reason}
    reasons = [row["reason"] for row in corruption_rows.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not row["accepted"] for row in corruption_rows.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_rows,
        "distinct_reasons": len(set(reasons)),
    }

    model_response = (
        "The early and late literal blocks give the required degrees.\n\n"
        "<answer>\n```json\n"
        + json.dumps(inst["answer"], separators=(",", ":"))
        + "\n```\n</answer>\nThis is my final witness."
    )
    parsed = parse_answer(model_response)
    parsed_ok, parsed_reason = verify(inst, parsed)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and parsed_ok,
        "verify_reason": parsed_reason,
    }

    guess_rng = random.Random(991_337)
    hits = 0
    for _ in range(_GUESS_SAMPLES):
        hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    report["G4_guess_resistance"] = {
        "pass": hits / _GUESS_SAMPLES < 1e-6,
        "hits": hits,
        "total": _GUESS_SAMPLES,
        "measured_probability": hits / _GUESS_SAMPLES,
        "candidate_space": search_space(inst),
        "sampler": "uniform canonical n-bit assignment with global complement removed",
    }

    baseline_started = time.perf_counter()
    baseline_candidate, baseline_stats = _walksat_search(
        inst, random.Random(771_991)
    )
    baseline_seconds = time.perf_counter() - baseline_started
    baseline_solved = baseline_candidate is not None and verify(inst, baseline_candidate)[0]
    demo = make_instance(seed=77, **DIFFICULTY["demo"])
    demo_valid = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": hits / _GUESS_SAMPLES < 1e-6 and not baseline_solved,
        "shipping_density_hits": hits,
        "shipping_density_samples": _GUESS_SAMPLES,
        "shipping_solution_fraction_estimate": hits / _GUESS_SAMPLES,
        "shipping_baseline_wall_clock_sec": round(baseline_seconds, 6),
        "shipping_baseline_solved": baseline_solved,
        **baseline_stats,
        "baseline_name": "break-count WalkSAT (32 restarts, 100n flips each)",
        "demo_exact_valid_answers": demo_valid,
        "demo_candidate_space": search_space(demo),
        "demo_exact_fraction": demo_valid / search_space(demo),
    }

    attacks = _run_attacks(shipping, list(range(800, 808)))
    report["G6_adversary_panel"] = {
        "pass": all(row["successes"] == 0 for row in attacks.values()),
        "attacks": attacks,
        "standard_algorithm": (
            "DPLL with NAE unit propagation, plus standard break-count WalkSAT "
            "as the domain local-search attack"
        ),
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled_started = time.perf_counter()
    doubled = make_instance(seed=54_321, **doubled_params)
    doubled_seconds = time.perf_counter() - doubled_started
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and search_space(doubled) > search_space(inst),
        "base_n": inst["n"],
        "doubled_n": doubled["n"],
        "base_candidate_space": search_space(inst),
        "doubled_candidate_space": search_space(doubled),
        "doubled_build_sec": round(doubled_seconds, 6),
        "verify_reason": doubled_reason,
    }

    invariant_checks = 0
    carried_checks = 0
    invariant_failures = []
    for seed in range(20):
        base = make_instance(n=30, degree=4, seed=10_000 + seed)
        key = canonical_key(base)
        transformed, carried = _transform_instance(base, random.Random(20_000 + seed))
        if canonical_key(transformed) != key:
            invariant_failures.append(seed)
        invariant_checks += 1
        ok, _ = verify(transformed, carried)
        carried_checks += int(ok)
        composed, carried_again = _transform_instance(
            transformed, random.Random(30_000 + seed)
        )
        if canonical_key(composed) != key:
            invariant_failures.append(f"composed-{seed}")
        invariant_checks += 1
        ok, _ = verify(composed, carried_again)
        carried_checks += int(ok)
    unrelated_keys = {
        canonical_key(make_instance(n=30, degree=4, seed=40_000 + seed))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": not invariant_failures
        and carried_checks == 40
        and len(unrelated_keys) == 20,
        "invariance_checks": invariant_checks,
        "invariance_failures": invariant_failures,
        "real_transformation_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "unrelated_distinct_keys": len(unrelated_keys),
        "invariant": "signed-switching and unsigned closed-walk traces",
        "complete_isomorphism_canonizer": False,
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    worst_answer_blob = json.dumps(
        [-(i + 1) for i in range(inst["n"])], separators=(",", ":")
    )
    answer_chars = len(worst_answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        hinted_minus_placebo = hinted_rate - placebo_rate
    else:
        hinted_minus_placebo = None
    caps_pass = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and inst["n"] <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": caps_pass,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "oracle_diagnostic_status": G9_ORACLE_RESULTS["diagnostic_status"],
        "diagnostic_recorded_not_gated": True,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "sample_answer_chars": len(answer_blob),
        "answer_elements": answer_elements,
        "intended_route_operations": inst["n"],
        "caps_pass": caps_pass,
    }

    gates = [
        value
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_passed"] = all(bool(gate.get("pass")) for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
