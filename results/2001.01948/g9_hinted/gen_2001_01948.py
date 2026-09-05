"""Verified proper-connection reduction certificates from arXiv:2001.01948.

The paper proves in Theorem 2.1 that deciding whether a graph has proper
connection number two is NP-complete by an explicit reduction from NAE-3SAT.
This module generates the reduction's source formulas by first sampling a
solution, composing a full-rank cyclic family of XOR identities, and encoding
each identity as NAE clauses.  The returned bit vector is a compact symbolic
certificate: fixing the displayed reference variable to zero, its omitted
frequency-two auxiliary bits are deterministically expanded and every NAE
clause is checked exactly.  The theorem's construction then maps that full
assignment to a two-colour proper-path colouring of the symbolically specified
graph G_F.

The generated distribution is deliberately Track B.  Recovering the hidden
XOR system and running Gaussian elimination is efficient; recognizing that its
three-variable supports form one tight overlap cycle replaces that mechanical
calculation by a short recurrence.  Verification never reads ``inst["answer"]``.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import random
import re
import sys
import time


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "NAE-3SAT formula used by the paper's proper-connection reduction",
        "symbolically specified reduction graph G_F",
    ],
    "verification_operations": [
        "deterministic auxiliary-bit expansion",
        "exact NAE-clause truth evaluation",
        "GF(2) parity comparison",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": "Section 2, Theorem 2.1 (NAE-3SAT to pc(G)=2)",
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Frequency-two variables pair NAE clauses into parity quartets whose "
        "three-variable supports form one hidden overlap cycle; without that "
        "invariant, the displayed instance requires mechanical elimination."
    ),
    "hardness_basis": (
        "Track B: frequency-two-pair recovery followed by exact Gaussian "
        "elimination solves this structured distribution in O(C+n^3); at the "
        "hard shipping preset (n=59, two encodings per parity clause) the "
        "measured maximum over eight seeds was 39,881 counted Boolean operations "
        "and 0.001555 seconds on average, while the tight-cycle recurrence uses "
        "at most 298 exact Boolean operations."
    ),
    "max_answer_tokens": 120,
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
    "demo": {"n": 5, "copies": 1},
    "easy": {"n": 23, "copies": 1},
    "medium": {"n": 41, "copies": 1},
    "hard": {"n": 59, "copies": 2},
}
SHIPPING_DIFFICULTY = "hard"

if os.environ.get("GV_G9_SINGLE") == "1":
    DIFFICULTY = {SHIPPING_DIFFICULTY: dict(DIFFICULTY[SHIPPING_DIFFICULTY])}


STRUCTURAL_HINT = (
    "Frequency-two variables pair the NAE clauses into parity quartets whose "
    "three-variable supports form one cyclic overlap pattern."
)
PLACEBO_HINT = (
    "Signed variables and occurrence slots make careful tracking of every "
    "displayed indexing and normalization convention important."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly n bits in the displayed core-variable order; "
        "the distinguished reference variable is normalized to 0, and each "
        "omitted frequency-two auxiliary variable is assigned the smaller bit "
        "that satisfies its two clauses."
    ),
    "bounds": {
        "length": "n",
        "alphabet": [0, 1],
        "shipping_length": 59,
        "shipping_candidate_count": "2^59",
    },
}

NOTES = (
    "Section 1 fixes the exact definitions: a proper path has differently "
    "coloured adjacent edges, and a graph is proper connected when every pair "
    "has such a path. Theorem 2.1 in Section 2 reduces NAE-3SAT to deciding "
    "pc(G)=2; its forward proof explicitly turns a NAE assignment into a "
    "two-colour proper-path colouring, while the cited Edmonds-Manoussakis "
    "result says a proposed two-colouring is checkable in polynomial time. "
    "Section 5 is the easy regime that had to be avoided: Algorithms 1 and 2 "
    "compute the k-colour connection number of trees in linear time (Theorem "
    "5.2). The paper gives no distributional hardness claim, and this module's "
    "cyclic distribution is efficiently solved by clause-pair recovery plus "
    "Gaussian elimination, so declaring Track A would be false. Generation is "
    "inverse: sample the core bits, compose cyclic XOR identities, encode each "
    "identity by four ordinary clauses, and reduce each ordinary clause to two "
    "NAE clauses with a fresh auxiliary bit and one reference bit. Balanced "
    "parity quartets defeat sign-frequency outliers; random variable, clause, "
    "literal, auxiliary-polarity, and occurrence-chain orders defeat positional "
    "probes; greedy, random-restart, and period-three ansatz attacks are measured."
)


# Filled from script-owned oracle runs after hardening.  These values are
# diagnostics only; G9's sole gate is the size/effort cap.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "oracle_unreachable_http_403",
}


def _xor_clauses(variables, rhs):
    """Return four signed 3-clauses equivalent to XOR(variables) == rhs."""
    clauses = []
    for bits in itertools.product((0, 1), repeat=3):
        if (bits[0] ^ bits[1] ^ bits[2]) == rhs:
            continue
        clauses.append([
            variable if bit == 0 else -variable
            for variable, bit in zip(variables, bits)
        ])
    return clauses


def _literal_value(literal, assignment):
    value = assignment[abs(literal)]
    return value if literal > 0 else 1 - value


def _nae_satisfied(literals, assignment):
    values = [_literal_value(literal, assignment) for literal in literals]
    return not (values[0] == values[1] == values[2])


def _assign_occurrence_slots(clauses, q, rng):
    occurrences = {variable: [] for variable in range(1, q + 1)}
    for ci, clause in enumerate(clauses):
        for li, literal in enumerate(clause):
            occurrences[abs(literal)].append((ci, li))
    slots = [[0, 0, 0] for _ in clauses]
    for variable in range(1, q + 1):
        order = list(occurrences[variable])
        rng.shuffle(order)
        for slot, (ci, li) in enumerate(order, 1):
            slots[ci][li] = slot
    return [{"lits": list(clause), "slots": slot}
            for clause, slot in zip(clauses, slots)]


def make_instance(n, seed=0, **params):
    """Inverse-generate a cyclic NAE certificate for Theorem 2.1's reduction."""
    copies = int(params.get("copies", 1))
    if not isinstance(n, int) or isinstance(n, bool) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if n % 3 == 0:
        raise ValueError("n must not be divisible by 3")
    if not isinstance(copies, int) or isinstance(copies, bool) or copies < 1:
        raise ValueError("copies must be a positive integer")

    rng = random.Random(seed)
    answer = [rng.randrange(2) for _ in range(n)]
    cycle = list(range(n))
    rng.shuffle(cycle)

    # Before relabelling, core variables are 1..n and the reference is n+1.
    reference = n + 1
    next_auxiliary = n + 2
    nae_clauses = []
    for i in range(n):
        positions = (cycle[i], cycle[(i + 1) % n], cycle[(i + 2) % n])
        variables = tuple(position + 1 for position in positions)
        rhs = answer[positions[0]] ^ answer[positions[1]] ^ answer[positions[2]]
        for ordinary in _xor_clauses(variables, rhs):
            for _ in range(copies):
                placed = list(ordinary)
                rng.shuffle(placed)
                auxiliary = next_auxiliary
                next_auxiliary += 1
                auxiliary_literal = auxiliary if rng.randrange(2) else -auxiliary
                pair = [
                    [placed[0], placed[1], auxiliary_literal],
                    [-auxiliary_literal, placed[2], reference],
                ]
                # Complementing every literal preserves a NAE clause exactly.
                for clause in pair:
                    if rng.randrange(2):
                        clause[:] = [-literal for literal in clause]
                    rng.shuffle(clause)
                    nae_clauses.append(clause)

    q = next_auxiliary - 1
    permutation = list(range(1, q + 1))
    rng.shuffle(permutation)
    rename = {old: permutation[old - 1] for old in range(1, q + 1)}
    relabelled = [
        [(1 if literal > 0 else -1) * rename[abs(literal)] for literal in clause]
        for clause in nae_clauses
    ]
    rng.shuffle(relabelled)
    clauses = _assign_occurrence_slots(relabelled, q, rng)

    return {
        "n": n,
        "q": q,
        "copies": copies,
        "reference_variable": rename[reference],
        "core_variables": [rename[i] for i in range(1, n + 1)],
        "clauses": clauses,
        "answer": answer,
    }


def render(inst):
    lines = [
        "Find a compact certificate for the Huang-Li proper-connection reduction graph G_F.",
        "",
        "Boolean and NAE conventions.",
        "A variable X_j has value 0 or 1. A signed literal +j has value X_j;",
        "a signed literal -j has value 1-X_j. A three-literal NAE clause is",
        "satisfied exactly when its three literal values are not all equal.",
        "Every clause below uses three distinct variables. Clauses and their",
        "three literals are unordered for satisfiability.",
        "",
        "Why this is a graph certificate.",
        "The graph G_F is specified by the following finite gadget rules. For",
        "each formula variable X_i with d_i occurrences, create blocks H(i,k),",
        "k=1,...,d_i, with vertices u(i,k,1),...,u(i,k,15). In each block add",
        "the path 1-2-3-4-5-6-7-8 and edges 9-1, 10-1, 11-5, 12-7,",
        "13-8, 14-8, 15-4, 15-7, and 7-3. Add 15(i,k)-1(i,k+1)",
        "for k<d_i. Add five vertices a_i,b_i,c_i,d_i,e_i and edges",
        "a_i-1(i,1), b_i-c_i, c_i-15(i,d_i), c_i-d_i, c_i-e_i.",
        "The @s number printed on a literal means that clause occurrence uses",
        "slot k=s in this variable chain.",
        "",
        "For each clause C_j create vertices v(j,0),...,v(j,11) and three arm",
        "vertices w(j,1),w(j,2),w(j,3). Add paths 0-1-5-4, 0-2-6-4,",
        "0-3-7-4 and edges 4-8, 8-9, 8-10, 8-11, and v(j,r)-w(j,r)",
        "for r=1,2,3. For arm r carrying +i@s, add w(j,r)-u(i,s,8);",
        "for arm r carrying -i@s, identify w(j,r) with u(i,s,8). Finally",
        "make {a_i,b_i for all i} union {v(j,11) for all j} union {z}",
        "a clique. These rules specify every vertex and edge of the simple graph.",
        "They are the symbolic form of the construction in Theorem 2.1.",
        "",
        "Certificate language and normalization.",
        "The distinguished reference variable R is fixed to 0. Every variable",
        "that is neither R nor a listed core variable occurs exactly twice. Once",
        "the core bits are supplied, assign each such auxiliary variable the",
        "smaller value in {0,1} satisfying both clauses in which it occurs; reject",
        "the certificate if neither value works. The resulting full assignment",
        "must satisfy every displayed NAE clause. Theorem 2.1 then expands it to",
        "a two-colour proper-path colouring of G_F; globally swapping the two",
        "colours is removed by the convention R=0.",
        "",
        f"Number of output core bits n: {inst['n']}",
        f"Number of formula variables q: {inst['q']}",
        f"Number of NAE clauses: {len(inst['clauses'])}",
        f"Reference variable R: X_{inst['reference_variable']}",
        "Core variables in mandatory output order: "
        + json.dumps(inst["core_variables"], separators=(",", ":")),
        "",
        "NAE clauses. An entry signed_variable@occurrence_slot gives both the",
        "literal and its one-based position in that variable's gadget chain:",
    ]
    for ci, clause in enumerate(inst["clauses"], 1):
        entries = []
        for literal, slot in zip(clause["lits"], clause["slots"]):
            entries.append(f"{literal:+d}@{slot}")
        lines.append(f"C{ci}: [" + ",".join(entries) + "]")

    lines.extend([
        "",
        "Return exactly n bits as a JSON list, in the displayed core-variable",
        "order. Each entry must be the integer 0 or 1; order matters and no",
        "entries may be omitted or repeated beyond their positions in the list.",
        "",
        "Give your final answer inside <answer></answer> tags, as a JSON list of bits.",
        "Example format for three core variables: <answer>[0,1,0]</answer>",
        "Output nothing else inside the tags.",
    ])

    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    tagged = re.findall(
        r"<answer\b[^>]*>(.*?)</answer>", text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    bodies = list(reversed(tagged))
    if not bodies:
        bodies = list(reversed(re.findall(r"\[[\s\d,+-]*\]", text, re.DOTALL)))
    for body in bodies:
        cleaned = body.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            value = json.loads(cleaned)
        except (TypeError, ValueError):
            continue
        if isinstance(value, list):
            return value
    return None


def _shape(inst, answer):
    n = inst["n"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) < n:
        return False, f"answer has too few core bits: expected {n}, got {len(answer)}"
    if len(answer) > n:
        return False, f"answer has too many core bits: expected {n}, got {len(answer)}"
    for position, bit in enumerate(answer, 1):
        if type(bit) is not int or bit not in (0, 1):
            return False, f"entry {position} is not an integer bit 0 or 1"
    return True, "ok"


def _normalise_clause_for_reference(literals, reference):
    out = list(literals)
    reference_literal = next((literal for literal in out
                              if abs(literal) == reference), None)
    if reference_literal is not None and reference_literal < 0:
        out = [-literal for literal in out]
    return out


def _recover_pairs(inst):
    """Recover each ordinary clause from its two-clause NAE reduction."""
    core = set(inst["core_variables"])
    reference = inst["reference_variable"]
    auxiliary = set(range(1, inst["q"] + 1)) - core - {reference}
    occurrences = {variable: [] for variable in auxiliary}
    for ci, clause in enumerate(inst["clauses"]):
        for literal in clause["lits"]:
            variable = abs(literal)
            if variable in occurrences:
                occurrences[variable].append(ci)

    records = []
    for variable in sorted(auxiliary):
        where = occurrences[variable]
        if len(where) != 2 or where[0] == where[1]:
            raise ValueError(f"auxiliary X_{variable} does not occur in two clauses")
        clauses = [inst["clauses"][ci]["lits"] for ci in where]
        with_reference = [i for i, clause in enumerate(clauses)
                          if any(abs(literal) == reference for literal in clause)]
        if len(with_reference) != 1:
            raise ValueError(f"auxiliary X_{variable} has no unique reference clause")
        ri = with_reference[0]
        bi = 1 - ri
        ref_clause = _normalise_clause_for_reference(clauses[ri], reference)
        base_clause = list(clauses[bi])
        ref_aux = next(literal for literal in ref_clause
                       if abs(literal) == variable)
        base_aux = next(literal for literal in base_clause
                        if abs(literal) == variable)
        if (ref_aux > 0) == (base_aux > 0):
            base_clause = [-literal for literal in base_clause]
            base_aux = -base_aux
        if (ref_aux > 0) == (base_aux > 0):
            raise ValueError(f"auxiliary X_{variable} has inconsistent polarity")

        left = [literal for literal in base_clause if abs(literal) != variable]
        right = [literal for literal in ref_clause
                 if abs(literal) not in (variable, reference)]
        ordinary = left + right
        if len(ordinary) != 3 or any(abs(literal) not in core
                                     for literal in ordinary):
            raise ValueError(f"auxiliary X_{variable} does not decode a core clause")
        records.append({
            "auxiliary": variable,
            "clause_indices": tuple(where),
            "ordinary": tuple(ordinary),
        })
    return records


def _decode_equations(inst):
    cached = inst.get("_decoded_equations")
    if cached is not None:
        return {tuple(key): rhs for key, rhs in cached}

    rhs_by_support = {}
    signatures = {}
    counts = {}
    for record in _recover_pairs(inst):
        ordinary = record["ordinary"]
        support = tuple(sorted(abs(literal) for literal in ordinary))
        if len(set(support)) != 3:
            raise ValueError("an ordinary clause repeats a core variable")
        false_bits = {abs(literal): int(literal < 0) for literal in ordinary}
        signature = tuple(false_bits[variable] for variable in support)
        wrong_parity = signature[0] ^ signature[1] ^ signature[2]
        rhs = wrong_parity ^ 1
        if support in rhs_by_support and rhs_by_support[support] != rhs:
            raise ValueError("a parity quartet has inconsistent right-hand sides")
        rhs_by_support[support] = rhs
        signatures.setdefault(support, set()).add(signature)
        counts[support] = counts.get(support, 0) + 1

    if len(rhs_by_support) != inst["n"]:
        raise ValueError("the formula does not contain n parity supports")
    for support in rhs_by_support:
        if len(signatures[support]) != 4:
            raise ValueError(f"support {support} is not a complete parity quartet")
        if counts[support] != 4 * inst["copies"]:
            raise ValueError(f"support {support} has the wrong copy count")
    inst["_decoded_equations"] = [[list(key), value]
                                   for key, value in rhs_by_support.items()]
    return rhs_by_support


def _expand_full_assignment(inst, core_bits):
    assignment = {inst["reference_variable"]: 0}
    assignment.update(zip(inst["core_variables"], core_bits))
    for record in _recover_pairs(inst):
        auxiliary = record["auxiliary"]
        viable = []
        for value in (0, 1):
            trial = dict(assignment)
            trial[auxiliary] = value
            if all(_nae_satisfied(inst["clauses"][ci]["lits"], trial)
                   for ci in record["clause_indices"]):
                viable.append(value)
        if not viable:
            return None, auxiliary
        assignment[auxiliary] = viable[0]
    return assignment, None


def verify(inst, answer):
    ok, reason = _shape(inst, answer)
    if not ok:
        return False, reason
    try:
        position_equations = inst.get("_position_equations")
        if position_equations is None:
            equations = _decode_equations(inst)
            position = {variable: i for i, variable in enumerate(inst["core_variables"])}
            position_equations = [
                ([position[variable] for variable in support], rhs, list(support))
                for support, rhs in equations.items()
            ]
            inst["_position_equations"] = position_equations
    except (KeyError, TypeError, ValueError) as exc:
        return False, f"malformed instance: {exc}"

    for positions, rhs, support in position_equations:
        parity = answer[positions[0]] ^ answer[positions[1]] ^ answer[positions[2]]
        if parity != rhs:
            shown = ",".join(f"X_{variable}" for variable in support)
            return False, f"parity constraint on [{shown}] is violated"

    full, bad_auxiliary = _expand_full_assignment(inst, answer)
    if full is None:
        return False, f"auxiliary X_{bad_auxiliary} has no satisfying bit"
    for ci, clause in enumerate(inst["clauses"], 1):
        if not _nae_satisfied(clause["lits"], full):
            return False, f"expanded assignment violates NAE clause C{ci}"
    return True, "ok"


def random_candidate(inst, rng):
    return [rng.randrange(2) for _ in range(inst["n"])]


def search_space(inst):
    return 1 << inst["n"]


def enumerate_all(inst):
    if search_space(inst) > 100_000:
        return None
    return sum(
        verify(inst, list(bits))[0]
        for bits in itertools.product((0, 1), repeat=inst["n"])
    )


def _cycle_equation_order(equations):
    supports = list(equations)
    support_sets = {support: set(support) for support in supports}
    adjacency = {support: [] for support in supports}
    for i, left in enumerate(supports):
        for right in supports[i + 1:]:
            if len(support_sets[left] & support_sets[right]) == 2:
                adjacency[left].append(right)
                adjacency[right].append(left)
    if any(len(neighbours) != 2 for neighbours in adjacency.values()):
        raise ValueError("the parity-support overlap graph is not a cycle")
    start = min(supports)
    order = [start]
    previous = None
    current = start
    while True:
        choices = [support for support in adjacency[current] if support != previous]
        nxt = min(choices) if previous is None else choices[0]
        if nxt == start:
            break
        if nxt in order:
            raise ValueError("the overlap cycle closes early")
        order.append(nxt)
        previous, current = current, nxt
    if len(order) != len(supports):
        raise ValueError("the overlap graph is disconnected")
    return order


def _ordered_cycle_data(inst):
    equations = _decode_equations(inst)
    supports = _cycle_equation_order(equations)
    variables = []
    for i, support in enumerate(supports):
        leaving = set(support) - set(supports[(i + 1) % len(supports)])
        if len(leaving) != 1:
            raise ValueError("successive supports do not have one leaving variable")
        variables.append(next(iter(leaving)))
    for i, support in enumerate(supports):
        expected = {
            variables[i],
            variables[(i + 1) % len(variables)],
            variables[(i + 2) % len(variables)],
        }
        if set(support) != expected:
            raise ValueError("the recovered supports are not a tight cycle")
    return variables, [equations[support] for support in supports]


def _bits_to_answer(inst, assignment):
    return [assignment[variable] for variable in inst["core_variables"]]


def _gaussian_reference(inst):
    """Recover parity rows, then run generic exact elimination over GF(2)."""
    equations = _decode_equations(inst)
    core_order = {variable: i for i, variable in enumerate(inst["core_variables"])}
    n = inst["n"]
    rows = []
    for support, rhs in equations.items():
        row = 0
        for variable in support:
            row |= 1 << core_order[variable]
        row |= rhs << n
        rows.append(row)

    operations = 6 * len(inst["clauses"]) + 4 * len(equations)
    pivot_row = 0
    pivots = []
    for column in range(n):
        operations += max(0, len(rows) - pivot_row)
        found = next((r for r in range(pivot_row, len(rows))
                      if (rows[r] >> column) & 1), None)
        if found is None:
            continue
        if found != pivot_row:
            rows[pivot_row], rows[found] = rows[found], rows[pivot_row]
            operations += 1
        for r in range(len(rows)):
            operations += 1
            if r != pivot_row and ((rows[r] >> column) & 1):
                rows[r] ^= rows[pivot_row]
                operations += n + 1
        pivots.append(column)
        pivot_row += 1
        if pivot_row == len(rows):
            break
    if len(pivots) != n:
        return None, operations
    answer = [0] * n
    for r, column in enumerate(pivots):
        answer[column] = (rows[r] >> n) & 1
    return answer, operations


def _dpll_reference(inst):
    """Plain DPLL with unit propagation on the decoded ordinary 3-CNF."""
    clauses = [record["ordinary"] for record in _recover_pairs(inst)]
    variables = list(inst["core_variables"])
    occurrences = {variable: [] for variable in variables}
    for ci, clause in enumerate(clauses):
        for literal in clause:
            occurrences[abs(literal)].append(ci)
    operations = 0
    nodes = 0

    def recurse(partial):
        nonlocal operations, nodes
        nodes += 1
        partial = dict(partial)
        while True:
            changed = False
            for clause in clauses:
                satisfied = False
                unknown = []
                for literal in clause:
                    operations += 1
                    variable = abs(literal)
                    if variable not in partial:
                        unknown.append(literal)
                    elif partial[variable] == int(literal > 0):
                        satisfied = True
                        break
                if satisfied:
                    continue
                if not unknown:
                    return None
                if len(unknown) == 1:
                    literal = unknown[0]
                    variable = abs(literal)
                    value = int(literal > 0)
                    if variable in partial and partial[variable] != value:
                        return None
                    if variable not in partial:
                        partial[variable] = value
                        operations += 1
                        changed = True
            if not changed:
                break

        if len(partial) == len(variables):
            return partial

        # A standard dynamic branching heuristic: prefer a variable in clauses
        # that already contain assigned variables, then prefer high occurrence.
        best = None
        best_score = None
        for variable in variables:
            if variable in partial:
                continue
            touched = 0
            for ci in occurrences[variable]:
                touched = max(
                    touched,
                    sum(abs(literal) in partial for literal in clauses[ci]),
                )
                operations += 3
            score = (touched, len(occurrences[variable]), -variable)
            if best_score is None or score > best_score:
                best = variable
                best_score = score
        for value in (0, 1):
            branch = dict(partial)
            branch[best] = value
            operations += 1
            solution = recurse(branch)
            if solution is not None:
                return solution
        return None

    assignment = recurse({})
    return (_bits_to_answer(inst, assignment) if assignment is not None else None,
            nodes, operations)


def _compact_cycle_reference(inst):
    """Use the tight overlap cycle as a second-order GF(2) recurrence."""
    variables, rhs = _ordered_cycle_data(inst)
    n = len(variables)
    y = [0, 0]
    operations = 2 * n  # decode one representative sign triple per support
    for i in range(n - 2):
        y.append(rhs[i] ^ y[i] ^ y[i + 1])
        operations += 2

    wrap1 = rhs[n - 2] ^ y[n - 2] ^ y[n - 1] ^ y[0]
    wrap2 = rhs[n - 1] ^ y[n - 1] ^ y[0] ^ y[1]
    operations += 6
    if n % 3 == 2:
        b = wrap1
        a = wrap2
        c = a ^ b
    elif n % 3 == 1:
        c = wrap1
        b = wrap2
        a = c ^ b
    else:
        return None, operations
    operations += 1

    homogeneous = (a, b, c)
    assignment = {}
    for i, (variable, particular) in enumerate(zip(variables, y)):
        assignment[variable] = particular ^ homogeneous[i % 3]
        operations += 1
    return _bits_to_answer(inst, assignment), operations


def _attack_sign_outlier(inst):
    scores = {variable: 0 for variable in inst["core_variables"]}
    for clause in inst["clauses"]:
        for literal in clause["lits"]:
            if abs(literal) in scores:
                scores[abs(literal)] += 1 if literal > 0 else -1
    return [int(scores[variable] > 0) for variable in inst["core_variables"]]


def _attack_greedy(inst):
    equations = _decode_equations(inst)
    assignment = {}
    for variable in inst["core_variables"]:
        scores = []
        for bit in (0, 1):
            trial = dict(assignment)
            trial[variable] = bit
            violations = 0
            for support, rhs in equations.items():
                if all(item in trial for item in support):
                    parity = trial[support[0]] ^ trial[support[1]] ^ trial[support[2]]
                    violations += int(parity != rhs)
            scores.append(violations)
        assignment[variable] = 0 if scores[0] <= scores[1] else 1
    return _bits_to_answer(inst, assignment)


def _random_restart(inst, rng, restarts):
    for attempt in range(1, restarts + 1):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate, attempt
    return None, restarts


def _attack_period_three(inst):
    variables, _ = _ordered_cycle_data(inst)
    for pattern in itertools.product((0, 1), repeat=3):
        assignment = {variable: pattern[i % 3]
                      for i, variable in enumerate(variables)}
        candidate = _bits_to_answer(inst, assignment)
        if verify(inst, candidate)[0]:
            return candidate
    return [0] * inst["n"]


def _copy_instance(inst):
    copied = json.loads(json.dumps({key: value for key, value in inst.items()
                                    if not key.startswith("_")}))
    return copied


def _transform_instance(inst, rng, *, variables=False, clauses=False,
                        literals=False, core_order=False):
    transformed = _copy_instance(inst)
    answer = list(transformed["answer"])
    if variables:
        order = list(range(1, transformed["q"] + 1))
        rng.shuffle(order)
        rename = {old: order[old - 1] for old in range(1, transformed["q"] + 1)}
        transformed["reference_variable"] = rename[transformed["reference_variable"]]
        transformed["core_variables"] = [rename[v] for v in transformed["core_variables"]]
        for clause in transformed["clauses"]:
            clause["lits"] = [
                (1 if literal > 0 else -1) * rename[abs(literal)]
                for literal in clause["lits"]
            ]
    if literals:
        for clause in transformed["clauses"]:
            order = [0, 1, 2]
            rng.shuffle(order)
            clause["lits"] = [clause["lits"][i] for i in order]
            clause["slots"] = [clause["slots"][i] for i in order]
    if clauses:
        rng.shuffle(transformed["clauses"])
    if core_order:
        order = list(range(transformed["n"]))
        rng.shuffle(order)
        transformed["core_variables"] = [transformed["core_variables"][i]
                                           for i in order]
        answer = [answer[i] for i in order]
    transformed["answer"] = answer
    return transformed


def _add_edge(adjacency, left, right):
    adjacency[left].add(right)
    adjacency[right].add(left)


def canonical_key(inst):
    """A label-invariant WL hash of the signed, occurrence-ordered formula."""
    adjacency = {}
    base = {}

    def add_node(name, colour):
        if name not in adjacency:
            adjacency[name] = set()
            base[name] = colour

    core = set(inst["core_variables"])
    reference = inst["reference_variable"]
    for variable in range(1, inst["q"] + 1):
        role = "reference" if variable == reference else ("core" if variable in core else "aux")
        add_node(("v", variable), "variable:" + role)
    for ci, clause in enumerate(inst["clauses"]):
        cnode = ("c", ci)
        add_node(cnode, "clause")
        for li, literal in enumerate(clause["lits"]):
            onode = ("o", ci, li)
            add_node(onode, "occurrence:+" if literal > 0 else "occurrence:-")
            _add_edge(adjacency, onode, cnode)
            _add_edge(adjacency, onode, ("v", abs(literal)))

    by_variable = {variable: {} for variable in range(1, inst["q"] + 1)}
    for ci, clause in enumerate(inst["clauses"]):
        for li, (literal, slot) in enumerate(zip(clause["lits"], clause["slots"])):
            by_variable[abs(literal)][slot] = ("o", ci, li)
    for variable, slots in by_variable.items():
        degree = len(slots)
        if set(slots) != set(range(1, degree + 1)):
            raise ValueError(f"occurrence slots for X_{variable} are not contiguous")
        start = ("start", variable)
        end = ("end", variable)
        add_node(start, "chain:start")
        add_node(end, "chain:end")
        _add_edge(adjacency, start, slots[1])
        _add_edge(adjacency, end, slots[degree])
        for slot in range(1, degree):
            link = ("link", variable, slot)
            add_node(link, "chain:link")
            _add_edge(adjacency, link, slots[slot])
            _add_edge(adjacency, link, slots[slot + 1])

    colours = {
        node: hashlib.sha256(base[node].encode()).hexdigest()
        for node in adjacency
    }
    for _ in range(12):
        colours = {
            node: hashlib.sha256(
                (colours[node] + "|" + "|".join(sorted(colours[nbr]
                                                        for nbr in neighbours))).encode()
            ).hexdigest()
            for node, neighbours in adjacency.items()
        }
    payload = json.dumps(sorted(colours.values()), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def escalate(params):
    p = dict(params)
    n = int(p.get("n", 0))
    copies = int(p.get("copies", 1))
    for next_n in (23, 41, 59):
        if n < next_n:
            p["n"] = next_n
            p["copies"] = 1 if next_n < 59 else max(2, copies)
            return p
    # Grow the clause/auxiliary haystack while the 59-bit witness and the
    # 298-operation compact route stay fixed.
    if copies < 8:
        p["copies"] = copies + 1
        return p
    return "cap_bound"


def _find_corruptions(inst):
    answer = list(inst["answer"])
    corruptions = {
        "drop_one_element": answer[:-1],
        "empty": [],
        "out_of_range": [2] + answer[1:],
        "duplicate_one_element": answer + [answer[-1]],
    }
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
    if swap is None:
        swap = [1 - answer[0]] + answer[1:]
    corruptions["swap_two_elements"] = swap
    return corruptions


def _answer_size(answer):
    blob = json.dumps(answer, separators=(",", ":"))
    atoms = len(answer)
    tokens = 2 * atoms + 2
    return len(blob), tokens, atoms


def selftest():
    report = {}

    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
            try:
                if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                    raise ValueError("JSON round-trip changed the answer")
            except (TypeError, ValueError) as exc:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": f"answer is not JSON-native: {exc}"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
        "construction": "inverse generation plus composition of cyclic XOR identities",
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **shipping_params)
    cases = {}
    reasons = []
    for name, candidate in _find_corruptions(inst).items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": (all(case["rejected"] for case in cases.values())
                 and len(set(reasons)) == len(reasons)),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "The reference-normalized core assignment I obtain is:\n"
        "```json\n<answer>\n" + json.dumps(inst["answer"])
        + "\n</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and parse_answer("no answer here") is None,
        "parsed_equals_answer": parsed == inst["answer"],
        "garbage_returns_none": parse_answer("no answer here") is None,
    }

    guess_rng = random.Random(0x200101948)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            guess_hits += 1
    guess_elapsed = time.perf_counter() - guess_start
    exact_fraction = 2.0 ** (-inst["n"])
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_hits / guess_total,
        "exact_fraction": exact_fraction,
        "candidate_space_bits": inst["n"],
        "structure_aware_constraints": [
            "exactly one normalized bit for each listed core variable",
            "every sampled entry is already an integer in {0,1}",
            "frequency-two auxiliary bits are deterministically expanded, not guessed",
        ],
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    baseline_start = time.perf_counter()
    baseline_answer, baseline_restarts = _random_restart(
        inst, random.Random(99173), 2048,
    )
    baseline_elapsed = time.perf_counter() - baseline_start
    reference_start = time.perf_counter()
    reference_answer, reference_ops = _gaussian_reference(inst)
    reference_elapsed = time.perf_counter() - reference_start
    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": (guess_hits / guess_total < 1e-6
                 and demo_count is not None
                 and reference_answer is not None
                 and verify(inst, reference_answer)[0]),
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density_estimate": guess_hits / guess_total,
        "shipping_exact_solution_count": 1,
        "shipping_exact_solution_fraction": exact_fraction,
        "demo_candidate_space": search_space(demo),
        "demo_exact_solution_count": demo_count,
        "demo_exact_solution_fraction": demo_count / search_space(demo),
        "baseline_attack_restarts": baseline_restarts,
        "baseline_attack_successes": int(baseline_answer is not None),
        "baseline_attack_nodes": baseline_restarts,
        "baseline_attack_wall_clock_sec": round(baseline_elapsed, 6),
        "reference_operation_count": reference_ops,
        "reference_wall_clock_sec": round(reference_elapsed, 6),
        "strongest_failing_attack": "random_restart_2048",
    }

    attack_names = (
        "outlier_literal_sign_balance",
        "greedy_completed_equations",
        "random_restart_256",
        "by_hand_period_three_ansatz",
    )
    attack_results = {
        name: {"successes": 0, "attempts": 0, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    reference_successes = 0
    reference_ops_max = 0
    reference_time = 0.0
    dpll_successes = 0
    dpll_nodes_max = 0
    dpll_ops_max = 0
    dpll_time = 0.0
    compact_successes = 0
    compact_ops_max = 0
    compact_time = 0.0
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **shipping_params)

        started = time.perf_counter()
        candidate = _attack_sign_outlier(trial)
        attack_results[attack_names[0]]["wall_clock_sec"] += time.perf_counter() - started
        attack_results[attack_names[0]]["attempts"] += 1
        attack_results[attack_names[0]]["successes"] += int(verify(trial, candidate)[0])

        started = time.perf_counter()
        candidate = _attack_greedy(trial)
        attack_results[attack_names[1]]["wall_clock_sec"] += time.perf_counter() - started
        attack_results[attack_names[1]]["attempts"] += 1
        attack_results[attack_names[1]]["successes"] += int(verify(trial, candidate)[0])

        started = time.perf_counter()
        candidate, _ = _random_restart(trial, random.Random(seed ^ 0xA55A), 256)
        attack_results[attack_names[2]]["wall_clock_sec"] += time.perf_counter() - started
        attack_results[attack_names[2]]["attempts"] += 1
        attack_results[attack_names[2]]["successes"] += int(candidate is not None)

        started = time.perf_counter()
        candidate = _attack_period_three(trial)
        attack_results[attack_names[3]]["wall_clock_sec"] += time.perf_counter() - started
        attack_results[attack_names[3]]["attempts"] += 1
        attack_results[attack_names[3]]["successes"] += int(verify(trial, candidate)[0])

        started = time.perf_counter()
        candidate, operations = _gaussian_reference(trial)
        reference_time += time.perf_counter() - started
        reference_ops_max = max(reference_ops_max, operations)
        reference_successes += int(candidate is not None and verify(trial, candidate)[0])

        started = time.perf_counter()
        candidate, nodes, operations = _dpll_reference(trial)
        dpll_time += time.perf_counter() - started
        dpll_nodes_max = max(dpll_nodes_max, nodes)
        dpll_ops_max = max(dpll_ops_max, operations)
        dpll_successes += int(candidate is not None and verify(trial, candidate)[0])

        started = time.perf_counter()
        candidate, operations = _compact_cycle_reference(trial)
        compact_time += time.perf_counter() - started
        compact_ops_max = max(compact_ops_max, operations)
        compact_successes += int(candidate is not None and verify(trial, candidate)[0])

    for result in attack_results.values():
        result["wall_clock_sec"] = round(result["wall_clock_sec"], 6)
    all_failed = all(result["successes"] == 0 and result["attempts"] >= 8
                     for result in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": (all_failed and reference_successes == 8 and dpll_successes == 8
                 and compact_successes == 8),
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "NAE-pair recovery plus Gauss-Jordan elimination over GF(2)",
            "complexity": "O(C + n^3) exact Boolean operations",
            "wall_clock_sec": round(reference_time / 8, 6),
            "wall_clock_sec_total_8": round(reference_time, 6),
            "operations": reference_ops_max,
            "solves": f"{reference_successes}/8, as expected",
        },
        "additional_reference_algorithm": {
            "name": "plain DPLL with unit propagation on the decoded ordinary 3-CNF",
            "complexity": "exponential worst case",
            "wall_clock_sec": round(dpll_time / 8, 6),
            "wall_clock_sec_total_8": round(dpll_time, 6),
            "max_nodes": dpll_nodes_max,
            "max_literal_operations": dpll_ops_max,
            "solves": f"{dpll_successes}/8, as expected for Track B",
        },
        "intended_compact_route": {
            "name": "tight-overlap-cycle recurrence",
            "wall_clock_sec": round(compact_time / 8, 6),
            "wall_clock_sec_total_8": round(compact_time, 6),
            "operations": compact_ops_max,
            "solves": f"{compact_successes}/8",
        },
    }

    doubled_n = shipping_params["n"] * 2
    if doubled_n % 3 == 0:
        doubled_n += 1
    doubled_params = dict(shipping_params)
    doubled_params["n"] = doubled_n
    scale_start = time.perf_counter()
    doubled = make_instance(seed=8181, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    scale_elapsed = time.perf_counter() - scale_start
    escalated_from_medium = escalate(DIFFICULTY["medium"])
    escalated_at_shipping = escalate(shipping_params)
    report["G7_scales"] = {
        "pass": (doubled_ok and isinstance(escalated_from_medium, dict)
                 and escalated_from_medium["n"] > DIFFICULTY["medium"]["n"]
                 and isinstance(escalated_at_shipping, dict)
                 and escalated_at_shipping["copies"] > shipping_params["copies"]),
        "shipping_n": shipping_params["n"],
        "shipping_copies": shipping_params["copies"],
        "shipping_formula_variables": inst["q"],
        "shipping_clauses": len(inst["clauses"]),
        "doubled_n": doubled_n,
        "doubled_formula_variables": doubled["q"],
        "doubled_clauses": len(doubled["clauses"]),
        "doubled_build_and_verify_sec": round(scale_elapsed, 6),
        "doubled_verify_reason": doubled_reason,
        "escalation_from_medium": escalated_from_medium,
        "escalation_after_shipping": escalated_at_shipping,
        "fixed_witness_axis": "copies raises clause and auxiliary crowding at n=59",
    }

    invariant = 0
    real_verified = 0
    g8_failures = []
    g8_params = DIFFICULTY["easy"]
    transformations = (
        {"variables": True},
        {"clauses": True},
        {"literals": True},
        {"core_order": True},
        {"variables": True, "clauses": True, "literals": True, "core_order": True},
    )
    for seed in range(20):
        original = make_instance(seed=4000 + seed, **g8_params)
        original_key = canonical_key(original)
        for ti, flags in enumerate(transformations):
            changed = _transform_instance(
                original, random.Random(seed * 31 + ti), **flags,
            )
            if canonical_key(changed) == original_key:
                invariant += 1
            else:
                g8_failures.append({"seed": seed, "transform": ti,
                                    "reason": "canonical key changed"})
            ok, reason = verify(changed, changed["answer"])
            if ok:
                real_verified += 1
            else:
                g8_failures.append({"seed": seed, "transform": ti, "reason": reason})
    unrelated_keys = {
        canonical_key(make_instance(seed=9000 + seed, **g8_params))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": (not g8_failures and invariant == 100 and real_verified == 100
                 and len(unrelated_keys) == 20),
        "method": "12-round signed occurrence-incidence Weisfeiler-Lehman invariant",
        "transformations": [
            "arbitrary formula-variable renaming",
            "NAE-clause reordering",
            "literal reordering inside every NAE clause",
            "core-output reordering with carried witness",
            "composition of all preceding relabellings",
        ],
        "invariant_relabellings": invariant,
        "real_transformations_verified": real_verified,
        "unrelated_attempts": 20,
        "unrelated_distinct_keys": len(unrelated_keys),
        "failures": g8_failures,
    }

    planted_chars, _, _ = _answer_size(inst["answer"])
    longest = [1] * inst["n"]
    chars, tokens, elements = _answer_size(longest)
    arms = {
        "bare": dict(G9_ORACLE_RESULTS["bare"]),
        "hinted": dict(G9_ORACLE_RESULTS["hinted"]),
        "placebo": dict(G9_ORACLE_RESULTS["placebo"]),
    }
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else None)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else None)
    within_caps = chars <= 2000 and elements <= 256 and compact_ops_max <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None
        ),
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "oracle_evidence_ready": all(arm["attempts"] >= 3 for arm in arms.values()),
        "answer_chars": chars,
        "planted_answer_chars": planted_chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": compact_ops_max,
        "within_caps": within_caps,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass", False) for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
