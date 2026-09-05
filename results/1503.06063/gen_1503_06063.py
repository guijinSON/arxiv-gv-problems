"""Verified compressed tree 4-spanners from cyclic parity formulas.

This Track-B family uses the exact reduction in the ``Stretch factor equals
4`` subsection of arXiv:1503.06063.  A satisfying assignment is sampled first,
a shuffled cyclic 3-XOR system is built around it, and each XOR equation is
encoded by four ordinary 3-CNF clauses.  Proposition 2 then gives a concrete
tree 4-spanner of the paper's graph f(I), of diameter at most five.

The submitted bit vector is a compact description of that tree.  Verification
expands both f(I) and the tree from the paper and checks the graph conditions
directly; it never reads the planted answer.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time
from collections import defaultdict, deque


# Keep the shared exact-arithmetic helpers importable under harden.py's working
# directory.  This family is discrete and does not need them, so absence is a
# supported standard-library-only fallback.
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
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
        "the paper's graph f(I), specified by indexed 3-SAT clause gadgets",
        "a compressed spanning tree encoded by variable-to-center choices",
    ],
    "verification_operations": [
        "exact expansion of the paper's graph and certificate tree",
        "disjoint-set tree test",
        "integer breadth-first distances and stretch comparison",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 'Stretch factor equals 4', Proposition 2 "
        "(3-SAT instance I maps to graph f(I))"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "reduction recognition",
    "intuition_description": (
        "Regroup clauses sharing three variables into parity equations and "
        "recognize that their overlap graph is one hidden cycle; without this "
        "recognition the displayed instance invites generic SAT or linear solving."
    ),
    "hardness_basis": (
        "Track B: Proposition 2 transfers the t=4, diameter-5 witness through "
        "the paper's 3-SAT gadget; the reference algorithm recovers the XOR rows "
        "and uses O(n^3) Gauss-Jordan elimination over GF(2), requiring at most "
        "38,950 counted Boolean operations and about 0.003 seconds per hard "
        "shipping instance (n=95, three copies), whereas the executed hidden-"
        "cycle recurrence needs at most 212 exact bit operations."
    ),
    "max_answer_tokens": 143,
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


# n is the number of Boolean variables.  ``copies`` adds indistinguishable
# clause-gadget crowding without lengthening the witness.
DIFFICULTY = {
    "demo": {"n": 5, "copies": 1},
    "easy": {"n": 31, "copies": 1},
    "medium": {"n": 47, "copies": 2},
    "hard": {"n": 95, "copies": 3},
}
SHIPPING_DIFFICULTY = "hard"

# G9 scratch runs use the exact shipping module but expose only its shipping
# rung to harden.py.
if os.environ.get("GV_G9_SINGLE") == "1":
    DIFFICULTY = {
        SHIPPING_DIFFICULTY: dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    }


STRUCTURAL_HINT = (
    "Clauses with the same three variables form parity quartets whose triple "
    "overlaps carry a single hidden cyclic order."
)
PLACEBO_HINT = (
    "Clauses with repeated variable names deserve careful bookkeeping because "
    "all listed signs and positions matter."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly n Boolean integers, one 0 or 1 for each displayed "
        "variable X_1,...,X_n; it encodes the variable-center edges of the "
        "paper's canonical certificate tree."
    ),
    "bounds": {
        "length": "n",
        "alphabet": [0, 1],
        "candidate_count": "2^n",
        "shipping_max_atoms": 95,
    },
}

NOTES = (
    "Definition 1 fixes a tree t-spanner and observes that checking graph edges "
    "suffices.  Theorem 1 supplies a shortest-path representative for diameter "
    "t+1.  Proposition 1 gives a polynomial recognition/construction algorithm "
    "for t=3, which rules out Track A there.  In the subsection 'Stretch factor "
    "equals 4', Proposition 2 gives the six-row/eight-column clause gadget and "
    "proves I satisfiable iff f(I) has a tree 4-spanner of diameter at most 5; "
    "Theorem 2 summarizes NP-completeness for every t>=4.  This generator samples "
    "the assignment first, encodes each cyclic XOR equation by its four exact "
    "3-CNF clauses, and carries the assignment through Proposition 2.  Balanced "
    "XOR quartets defeat literal-frequency outliers; clause shuffling defeats the "
    "one-pass greedy and visible-order recurrence attacks; full-rank cycle length "
    "n not divisible by 3 makes the certificate unique; random restarts are "
    "measured against the exact 2^n language."
)

# Counts copied from the script-owned hard-rung transcripts.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


_MATRIX = (
    (1, 1, 1, 1, 0, 0, 0, 0),
    (0, 0, 0, 0, 1, 1, 1, 1),
    (1, 1, 0, 0, 1, 1, 0, 0),
    (0, 0, 1, 1, 0, 0, 1, 1),
    (1, 0, 1, 0, 1, 0, 1, 0),
    (0, 1, 0, 1, 0, 1, 0, 1),
)


def _edge(a, b):
    if a == b:
        raise ValueError("loops are not graph edges")
    return (a, b) if a < b else (b, a)


def _literal_true(literal, assignment):
    bit = assignment[abs(literal) - 1]
    return bit == (1 if literal > 0 else 0)


def _xor_clauses(variables, rhs):
    """The four 3-clauses exactly equivalent to xor(variables) == rhs."""
    out = []
    for bits in itertools.product((0, 1), repeat=3):
        if (bits[0] ^ bits[1] ^ bits[2]) == rhs:
            continue
        # This clause alone excludes ``bits``.
        clause = []
        for variable, bit in zip(variables, bits):
            clause.append(variable + 1 if bit == 0 else -(variable + 1))
        out.append(clause)
    return out


def make_instance(n, seed=0, **params):
    """Inverse-generate a full-rank cyclic XOR formula and its graph witness."""
    copies = int(params.get("copies", 1))
    if not isinstance(n, int) or isinstance(n, bool) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if n % 3 == 0:
        raise ValueError("n must not be divisible by 3")
    if copies < 1:
        raise ValueError("copies must be positive")

    rng = random.Random(seed)
    answer = [rng.randrange(2) for _ in range(n)]
    cycle = list(range(n))
    rng.shuffle(cycle)

    clauses = []
    for i in range(n):
        triple = (cycle[i], cycle[(i + 1) % n], cycle[(i + 2) % n])
        rhs = answer[triple[0]] ^ answer[triple[1]] ^ answer[triple[2]]
        quartet = _xor_clauses(triple, rhs)
        for _ in range(copies):
            for clause in quartet:
                placed = list(clause)
                rng.shuffle(placed)
                clauses.append(placed)
    rng.shuffle(clauses)

    return {
        "n": n,
        "copies": copies,
        "stretch": 4,
        "diameter_bound": 5,
        "clauses": clauses,
        "answer": answer,
    }


def _answer_shape(answer, n):
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) < n:
        return False, f"answer has too few bits: expected {n}, got {len(answer)}"
    if len(answer) > n:
        return False, f"answer has too many bits: expected {n}, got {len(answer)}"
    for i, bit in enumerate(answer, 1):
        if type(bit) is not int or bit not in (0, 1):
            return False, f"bit {i} is not the integer 0 or 1"
    return True, "ok"


def _first_false_clause(inst, assignment):
    for i, clause in enumerate(inst["clauses"], 1):
        if not any(_literal_true(literal, assignment) for literal in clause):
            return i
    return None


def _build_graph_and_tree(inst, assignment):
    """Expand f(I) and the exact forward certificate in Proposition 2."""
    n = inst["n"]
    clauses = inst["clauses"]
    graph = set()
    tree = set()

    # IDs 0..5 are u,v,h_u,h'_u,h'_v,h_v.
    fixed_path = (
        _edge(2, 3),
        _edge(3, 0),
        _edge(0, 1),
        _edge(1, 4),
        _edge(4, 5),
    )
    graph.update(fixed_path)
    tree.update(fixed_path)

    for variable in range(n):
        vertex = 6 + variable
        graph.add(_edge(vertex, 0))
        graph.add(_edge(vertex, 1))
        tree.add(_edge(vertex, 0 if assignment[variable] else 1))

    for ci, clause in enumerate(clauses):
        base = 6 + n + 11 * ci
        occurrences = [base + j for j in range(3)]
        qverts = [base + 3 + j for j in range(8)]
        variables = [6 + abs(literal) - 1 for literal in clause]

        for j, literal in enumerate(clause):
            center = 0 if literal > 0 else 1
            edge = _edge(occurrences[j], center)
            graph.add(edge)
            tree.add(edge)

        for row in range(6):
            source = variables[row // 2] if row % 2 == 0 else occurrences[row // 2]
            for col in range(8):
                if _MATRIX[row][col]:
                    graph.add(_edge(source, qverts[col]))

        for left, right in zip(qverts, qverts[1:]):
            graph.add(_edge(left, right))

        chosen = next(
            j for j, literal in enumerate(clause)
            if _literal_true(literal, assignment)
        )
        for col, qvertex in enumerate(qverts):
            if _MATRIX[2 * chosen][col]:
                tree.add(_edge(variables[chosen], qvertex))
            else:
                tree.add(_edge(occurrences[chosen], qvertex))

    vertex_count = 6 + n + 11 * len(clauses)
    return vertex_count, graph, tree


def _tree_distances(tree, vertex_count):
    adjacency = [[] for _ in range(vertex_count)]
    for a, b in tree:
        adjacency[a].append(b)
        adjacency[b].append(a)

    parent = [-1] * vertex_count
    depth = [-1] * vertex_count
    parent[0] = 0
    depth[0] = 0
    queue = deque([0])
    while queue:
        here = queue.popleft()
        for there in adjacency[here]:
            if depth[there] < 0:
                depth[there] = depth[here] + 1
                parent[there] = here
                queue.append(there)
    return adjacency, parent, depth


def _distance(a, b, parent, depth):
    distance = 0
    while depth[a] > depth[b]:
        a = parent[a]
        distance += 1
    while depth[b] > depth[a]:
        b = parent[b]
        distance += 1
    while a != b:
        a = parent[a]
        b = parent[b]
        distance += 2
    return distance


def verify(inst, answer):
    """Check any assignment certificate by expanding and testing its tree."""
    n = inst.get("n")
    ok, reason = _answer_shape(answer, n)
    if not ok:
        return False, reason

    bad_clause = _first_false_clause(inst, answer)
    if bad_clause is not None:
        return False, f"clause {bad_clause} is false under the certificate"

    try:
        vertex_count, graph, tree = _build_graph_and_tree(inst, answer)
    except (IndexError, StopIteration, TypeError, ValueError) as exc:
        return False, f"certificate expansion failed: {exc}"

    if not tree <= graph:
        return False, "expanded certificate uses a non-edge of G"
    if len(tree) != vertex_count - 1:
        return False, "expanded certificate has the wrong edge count"

    parent_dsu = list(range(vertex_count))

    def find(x):
        while parent_dsu[x] != x:
            parent_dsu[x] = parent_dsu[parent_dsu[x]]
            x = parent_dsu[x]
        return x

    for a, b in tree:
        ra, rb = find(a), find(b)
        if ra == rb:
            return False, "expanded certificate contains a cycle"
        parent_dsu[ra] = rb
    if len({find(v) for v in range(vertex_count)}) != 1:
        return False, "expanded certificate is disconnected"

    adjacency, parent, depth = _tree_distances(tree, vertex_count)
    if any(d < 0 for d in depth):
        return False, "expanded certificate is not spanning"

    # A double sweep computes a tree's exact diameter.
    def farthest(start):
        dist = [-1] * vertex_count
        dist[start] = 0
        queue = deque([start])
        last = start
        while queue:
            last = queue.popleft()
            for there in adjacency[last]:
                if dist[there] < 0:
                    dist[there] = dist[last] + 1
                    queue.append(there)
        far = max(range(vertex_count), key=dist.__getitem__)
        return far, dist[far]

    endpoint, _ = farthest(0)
    _, diameter = farthest(endpoint)
    if diameter > inst["diameter_bound"]:
        return False, f"expanded tree diameter {diameter} exceeds 5"

    for a, b in graph:
        dist = _distance(a, b, parent, depth)
        if dist > inst["stretch"]:
            return False, f"graph edge ({a},{b}) has tree distance {dist} > 4"
    return True, "ok"


def render(inst):
    n = inst["n"]
    clauses = inst["clauses"]
    lines = [
        "Find a compressed tree 4-spanner certificate for the graph below.",
        "",
        "A tree 4-spanner of an undirected graph G is a spanning tree T contained",
        "in G such that the distance in T between the endpoints of every edge of",
        "G is at most 4.  The diameter of T is the largest distance in T between",
        "any two vertices.  Here T must have diameter at most 5.",
        "",
        "The graph G is given exactly by the following finite gadget specification.",
        "A signed integer +k means Boolean variable X_k; -k means its negation.",
        "Variables are 1-indexed, and each listed clause is an OR of its three",
        "distinct literals.  Clause order and literal position are part of the",
        "graph specification; repeated clauses create separate indexed gadgets.",
        "",
        f"Number of variables: {n}",
        f"Number of indexed clauses: {len(clauses)}",
        "Clauses (one JSON triple per indexed gadget):",
    ]
    lines.extend(f"c{i}: {json.dumps(clause, separators=(',', ':'))}"
                 for i, clause in enumerate(clauses, 1))
    lines.extend([
        "",
        "Graph construction (this uniquely specifies every vertex and edge):",
        "Create vertices u,v,h_u,h'_u,h'_v,h_v and the path",
        "h_u--h'_u--u--v--h'_v--h_v.  Create one vertex X_k per variable and",
        "join every X_k to both u and v.  For each indexed clause c=(l1,l2,l3),",
        "create occurrence vertices O_c1,O_c2,O_c3 and q_c1,...,q_c8.  Join O_cj",
        "to u when lj is positive and to v when lj is negative.  Put the q vertices",
        "on the path q_c1--q_c2--...--q_c8.  Finally, in the row order",
        "X_|l1|,O_c1,X_|l2|,O_c2,X_|l3|,O_c3, join a row vertex to q_ck exactly",
        "where the following 6-by-8 matrix has a 1:",
        "11110000",
        "00001111",
        "11001100",
        "00110011",
        "10101010",
        "01010101",
        "There are no other vertices or edges; all edges are undirected and there",
        "are no loops.",
        "",
        "Your answer is a compact certificate for T: give one bit a_k for each",
        "X_k, in X_1,...,X_n order.  It expands as follows.  Include the fixed",
        "six-vertex path.  Include X_k--u if a_k=1 and X_k--v if a_k=0.  Include",
        "every occurrence-to-u/v edge.  In each clause, use the first listed literal",
        "made true by the bits; if it is in position j, attach each q_ck through",
        "the unique 1 in rows 2j-1 and 2j of column k.  (Those two rows are",
        "complements.)  No q-path edge is included in T.  A certificate is valid",
        "only if every clause has a true literal and the expanded subgraph is a",
        "tree 4-spanner of diameter at most 5.",
        "",
        f"Give your final answer inside <answer></answer> tags, as a JSON list of exactly {n} integers, each 0 or 1.",
        "Example format for four variables: <answer>[0,1,1,0]</answer>",
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
    match = re.search(r"<answer\b[^>]*>(.*?)</answer\s*>", text,
                      flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    payload = match.group(1).strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.IGNORECASE)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        answer = json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return None
    return answer if isinstance(answer, list) else None


def random_candidate(inst, rng):
    return [rng.randrange(2) for _ in range(inst["n"])]


def search_space(inst):
    return 1 << inst["n"]


def enumerate_all(inst):
    n = inst["n"]
    if n > 20:
        return None
    count = 0
    for mask in range(1 << n):
        candidate = [(mask >> i) & 1 for i in range(n)]
        if _first_false_clause(inst, candidate) is None:
            count += 1
    return count


def _canonical_clause(clause):
    return tuple(clause)


def _recover_xor_rows(inst):
    """Recover (variable triple, rhs) from duplicated/shuffled CNF quartets."""
    groups = defaultdict(list)
    for clause in inst["clauses"]:
        if len(clause) != 3 or len({abs(x) for x in clause}) != 3:
            raise ValueError("not a three-distinct-variable clause")
        key = tuple(sorted(abs(x) - 1 for x in clause))
        signs = {}
        for literal in clause:
            signs[abs(literal) - 1] = 1 if literal > 0 else -1
        groups[key].append(tuple(signs[v] for v in key))

    rows = []
    multiplicities = set()
    for key, patterns in groups.items():
        counts = defaultdict(int)
        for pattern in patterns:
            counts[pattern] += 1
        if len(counts) != 4 or len(set(counts.values())) != 1:
            raise ValueError("clauses do not form uniformly copied XOR quartets")
        multiplicities.add(next(iter(counts.values())))
        allowed = []
        for bits in itertools.product((0, 1), repeat=3):
            if all(any(bits[j] == (1 if sign > 0 else 0)
                       for j, sign in enumerate(pattern))
                   for pattern in counts):
                allowed.append(bits)
        parities = {bits[0] ^ bits[1] ^ bits[2] for bits in allowed}
        if len(allowed) != 4 or len(parities) != 1:
            raise ValueError("clause quartet is not one XOR relation")
        rows.append((key, next(iter(parities))))
    if len(multiplicities) != 1:
        raise ValueError("inconsistent quartet multiplicities")
    if len(rows) != inst["n"]:
        raise ValueError("wrong number of XOR rows")
    return rows, next(iter(multiplicities))


def _recover_cycle(inst):
    rows, copies = _recover_xor_rows(inst)
    pair_counts = defaultdict(int)
    for triple, _ in rows:
        for pair in itertools.combinations(triple, 2):
            pair_counts[tuple(sorted(pair))] += 1
    adjacency = {v: [] for v in range(inst["n"])}
    for (a, b), count in pair_counts.items():
        if count == 2:
            adjacency[a].append(b)
            adjacency[b].append(a)
    if any(len(adjacency[v]) != 2 for v in adjacency):
        raise ValueError("overlap graph is not a cycle")
    start = min(adjacency)
    order = [start]
    previous = None
    current = start
    while len(order) < inst["n"]:
        choices = [v for v in adjacency[current] if v != previous]
        if previous is None:
            nxt = min(choices)
        else:
            nxt = choices[0]
        if nxt == start or nxt in order:
            raise ValueError("overlap graph closed too early")
        order.append(nxt)
        previous, current = current, nxt
    if start not in adjacency[current]:
        raise ValueError("overlap graph does not close")
    expected = {frozenset((order[i], order[(i + 1) % len(order)],
                           order[(i + 2) % len(order)]))
                for i in range(len(order))}
    if expected != {frozenset(row[0]) for row in rows}:
        raise ValueError("XOR triples are not the windows of one cycle")
    return order, rows, copies


def canonical_key(inst):
    """Canonicalize variable renaming, clause order, and global polarity."""
    cycle, _, copies = _recover_cycle(inst)
    n = inst["n"]
    best = None
    for direction in (1, -1):
        for start in range(n):
            mapping = {
                cycle[(start + direction * i) % n]: i + 1
                for i in range(n)
            }
            for polarity in (1, -1):
                normalized = []
                for clause in inst["clauses"]:
                    normalized.append(tuple(
                        polarity * (1 if literal > 0 else -1)
                        * mapping[abs(literal) - 1]
                        for literal in clause
                    ))
                candidate = tuple(sorted(normalized))
                if best is None or candidate < best:
                    best = candidate
    payload = json.dumps(
        {"n": n, "copies": copies, "clauses": best},
        separators=(",", ":"),
    ).encode()
    return "xor-fI:" + hashlib.sha256(payload).hexdigest()


def escalate(params):
    if os.environ.get("GV_G9_SINGLE") == "1":
        return None
    n = int(params["n"])
    copies = int(params["copies"])
    if n < 95:
        nxt = min(95, n + 24)
        while nxt % 3 == 0:
            nxt += 1
        return {"n": nxt, "copies": min(4, copies + 1)}
    if copies < 6:
        return {"n": n, "copies": copies + 1}
    if n < 137:
        nxt = min(137, n + 24)
        while nxt % 3 == 0:
            nxt += 1
        return {"n": nxt, "copies": copies}
    # More copies only repeat the same mathematical information, while n>137
    # breaks the 300-operation compact-route cap.  There is no honest remaining
    # hardness axis under the required no-tool contract.
    return None


def _gaussian_reference(inst):
    """Recover XOR rows and solve them by generic dense Gauss-Jordan."""
    rows, _ = _recover_xor_rows(inst)
    n = inst["n"]
    matrix = []
    operations = 3 * len(inst["clauses"])
    for triple, rhs in rows:
        row = [0] * (n + 1)
        for variable in triple:
            row[variable] = 1
        row[n] = rhs
        matrix.append(row)
    pivot_row = 0
    pivot_for_col = {}
    for col in range(n):
        pivot = None
        for r in range(pivot_row, len(matrix)):
            operations += 1
            if matrix[r][col]:
                pivot = r
                break
        if pivot is None:
            continue
        if pivot != pivot_row:
            matrix[pivot_row], matrix[pivot] = matrix[pivot], matrix[pivot_row]
            operations += n + 1
        for r in range(len(matrix)):
            if r == pivot_row:
                continue
            operations += 1
            if matrix[r][col]:
                for j in range(col, n + 1):
                    matrix[r][j] ^= matrix[pivot_row][j]
                    operations += 1
        pivot_for_col[col] = pivot_row
        pivot_row += 1
    if pivot_row != n:
        raise ValueError("reference system is not full rank")
    answer = [matrix[pivot_for_col[col]][n] for col in range(n)]
    return answer, operations


def _compact_cycle_solve(inst):
    """Execute the intended cyclic recurrence with symbolic first two bits.

    Grouping clauses and traversing exact set overlaps use comparisons, not
    arithmetic.  The returned count conservatively charges one exact bit
    operation for each ternary-XOR recurrence, each affine-bit evaluation, and
    24 operations for testing the four possible initial pairs against the two
    wraparound equations.
    """
    order, rows, _ = _recover_cycle(inst)
    n = inst["n"]
    rhs_by_triple = {frozenset(triple): rhs for triple, rhs in rows}
    rhs = [rhs_by_triple[frozenset((order[i], order[(i + 1) % n],
                                    order[(i + 2) % n]))]
           for i in range(n)]

    # y_i has affine form alpha_i*a xor beta_i*b xor constant_i.  The
    # coefficient pairs repeat (1,0),(0,1),(1,1), so only constants need the
    # recurrence.
    constants = [0, 0]
    for i in range(n - 2):
        constants.append(constants[i] ^ constants[i + 1] ^ rhs[i])

    def affine_value(i, a, b):
        residue = i % 3
        if residue == 0:
            return a ^ constants[i]
        if residue == 1:
            return b ^ constants[i]
        return a ^ b ^ constants[i]

    initial = None
    for a, b in itertools.product((0, 1), repeat=2):
        tail_one = (
            affine_value(n - 2, a, b)
            ^ affine_value(n - 1, a, b)
            ^ affine_value(0, a, b)
        )
        tail_two = (
            affine_value(n - 1, a, b)
            ^ affine_value(0, a, b)
            ^ affine_value(1, a, b)
        )
        if tail_one == rhs[n - 2] and tail_two == rhs[n - 1]:
            initial = (a, b)
            break
    if initial is None:
        raise ValueError("cyclic recurrence has no solution")

    cyclic_answer = [affine_value(i, *initial) for i in range(n)]
    answer = [0] * n
    for i, variable in enumerate(order):
        answer[variable] = cyclic_answer[i]
    operations = (n - 2) + n + 24
    return answer, operations


def _attack_outlier(inst):
    positive = [0] * inst["n"]
    negative = [0] * inst["n"]
    for clause in inst["clauses"]:
        for literal in clause:
            (positive if literal > 0 else negative)[abs(literal) - 1] += 1
    return [int(positive[i] > negative[i]) for i in range(inst["n"])]


def _attack_greedy(inst):
    assignment = [None] * inst["n"]
    for clause in inst["clauses"]:
        if any(assignment[abs(lit) - 1] is not None
               and _literal_true(lit, assignment) for lit in clause):
            continue
        unassigned = [lit for lit in clause if assignment[abs(lit) - 1] is None]
        if unassigned:
            literal = unassigned[0]
            assignment[abs(literal) - 1] = 1 if literal > 0 else 0
    return [0 if bit is None else bit for bit in assignment]


def _attack_visible_order(inst):
    rows, _ = _recover_xor_rows(inst)
    rhs = {frozenset(triple): value for triple, value in rows}
    assignment = [0] * inst["n"]
    for i in range(inst["n"] - 2):
        key = frozenset((i, i + 1, i + 2))
        if key in rhs:
            assignment[i + 2] = assignment[i] ^ assignment[i + 1] ^ rhs[key]
    return assignment


def _attack_random_restart(inst, rng, restarts=256):
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if _first_false_clause(inst, candidate) is None:
            return candidate
    return [0] * inst["n"]


def _transform_instance(inst, rng, *, rename=False, reorder=False,
                        polarity=False):
    n = inst["n"]
    permutation = list(range(n))
    if rename:
        rng.shuffle(permutation)
    clauses = []
    for clause in inst["clauses"]:
        changed = []
        for literal in clause:
            sign = 1 if literal > 0 else -1
            if polarity:
                sign *= -1
            changed.append(sign * (permutation[abs(literal) - 1] + 1))
        clauses.append(changed)
    if reorder:
        rng.shuffle(clauses)
    answer = [0] * n
    for old, bit in enumerate(inst["answer"]):
        answer[permutation[old]] = bit ^ int(polarity)
    return {
        "n": n,
        "copies": inst["copies"],
        "stretch": 4,
        "diameter_bound": 5,
        "clauses": clauses,
        "answer": answer,
    }


def _fast_valid(inst, candidate):
    ok, _ = _answer_shape(candidate, inst["n"])
    return ok and _first_false_clause(inst, candidate) is None


def _answer_metrics(answer):
    blob = json.dumps(answer)
    atoms = len(answer)
    # Conservative token proxy for a comma-separated list of one-digit atoms.
    tokens = math.ceil(len(blob) / 2)
    return len(blob), tokens, atoms


def selftest():
    report = {}

    # G1: construction and explicit graph verification on every named rung.
    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "construction": "inverse generation plus Proposition 2's forward tree",
        "failures": g1_failures,
    }

    # G2: five materially different corruptions and five distinct diagnostics.
    params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=42, **params)
    answer = inst["answer"]
    unequal = next((i for i in range(1, len(answer)) if answer[i] != answer[0]), 1)
    swapped = list(answer)
    swapped[0], swapped[unequal] = swapped[unequal], swapped[0]
    corruptions = {
        "drop_one_element": answer[:-1],
        "swap_two_unequal_elements": swapped,
        "duplicate_one_element": answer + [answer[-1]],
        "empty": [],
        "out_of_range": [2] + answer[1:],
    }
    cases = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": why}
        reasons.append(why)
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
                and len(set(reasons)) == len(reasons),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic prose/fence wrapping plus malformed input.
    wrapped = (
        "I grouped the constraints first.\n\n<answer>\n```json\n"
        + json.dumps(answer)
        + "\n```\n</answer>\n"
    )
    parsed = parse_answer(wrapped)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("no tagged answer") is None,
        "parsed_equals_answer": parsed == answer,
        "garbage_returns_none": parse_answer("no tagged answer") is None,
    }

    # G4/G5: exact language prior; fast validation is equivalent to full graph
    # verification by the same executable expansion checked throughout G1.
    guess_rng = random.Random(150306063)
    sample_total = 200_000
    hits = 0
    t0 = time.perf_counter()
    for _ in range(sample_total):
        candidate = random_candidate(inst, guess_rng)
        if _fast_valid(inst, candidate):
            hits += 1
            if not verify(inst, candidate)[0]:
                raise AssertionError("fast validity disagrees with full verifier")
    guess_sec = time.perf_counter() - t0
    report["G4_guess_resistance"] = {
        "pass": hits / sample_total < 1e-6,
        "hits": hits,
        "total": sample_total,
        "fraction": hits / sample_total,
        "candidate_space_bits": inst["n"],
        "structure_aware_constraints": [
            "exactly n positions",
            "every position is already a Boolean integer",
        ],
        "wall_clock_sec": round(guess_sec, 6),
    }

    # Reference algorithm measurements on eight fresh shipping instances.
    ref_operations = []
    ref_failures = 0
    compact_operations = []
    compact_failures = 0
    ref_sec = 0.0
    compact_sec = 0.0
    for seed in range(800, 808):
        trial = make_instance(seed=seed, **params)
        algorithm_t0 = time.perf_counter()
        solved, operations = _gaussian_reference(trial)
        ref_sec += time.perf_counter() - algorithm_t0
        ref_operations.append(operations)
        if not verify(trial, solved)[0]:
            ref_failures += 1
        algorithm_t0 = time.perf_counter()
        compact, compact_ops = _compact_cycle_solve(trial)
        compact_sec += time.perf_counter() - algorithm_t0
        compact_operations.append(compact_ops)
        if not verify(trial, compact)[0]:
            compact_failures += 1

    # The strongest failing attack is the 256-restart sampler.
    baseline_t0 = time.perf_counter()
    baseline_hits = 0
    for seed in range(8):
        trial = make_instance(seed=900 + seed, **params)
        candidate = _attack_random_restart(
            trial, random.Random(7000 + seed), restarts=256
        )
        baseline_hits += int(_fast_valid(trial, candidate))
    baseline_sec = time.perf_counter() - baseline_t0
    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": hits / sample_total < 1e-6 and baseline_hits == 0,
        "shipping_sample_hits": hits,
        "shipping_sample_total": sample_total,
        "shipping_solution_density_estimate": hits / sample_total,
        "shipping_exact_density_from_full_rank": 1 / search_space(inst),
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "demo_exact_solution_fraction": demo_count / search_space(demo),
        "strongest_failing_attack": "random_restart_256",
        "baseline_attack_restarts": 8 * 256,
        "baseline_attack_successes": baseline_hits,
        "baseline_attack_wall_clock_sec": round(baseline_sec, 6),
        "reference_operation_count_max": max(ref_operations),
        "reference_wall_clock_sec_total_8": round(ref_sec, 6),
        "reference_wall_clock_sec_per_instance": round(ref_sec / 8, 6),
    }

    attack_functions = {
        "outlier_literal_frequency": lambda x, r: _attack_outlier(x),
        "greedy_one_pass_clause": lambda x, r: _attack_greedy(x),
        "random_restart_256": lambda x, r: _attack_random_restart(x, r, 256),
        "by_hand_visible_order_recurrence": lambda x, r: _attack_visible_order(x),
    }
    attack_results = {}
    for attack_index, (name, attack) in enumerate(attack_functions.items()):
        successes = 0
        start = time.perf_counter()
        for seed in range(8):
            trial = make_instance(seed=1200 + seed, **params)
            candidate = attack(trial, random.Random(attack_index * 10000 + seed))
            successes += int(_fast_valid(trial, candidate))
        attack_results[name] = {
            "successes": successes,
            "attempts": 8,
            "wall_clock_sec": round(time.perf_counter() - start, 6),
        }
    all_failed = all(item["successes"] == 0 for item in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_failures == 0 and compact_failures == 0,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "XOR-quartet recovery plus dense Gauss-Jordan over GF(2)",
            "complexity": "O(m log m + n^3) exact Boolean operations",
            "wall_clock_sec": round(ref_sec / 8, 6),
            "wall_clock_sec_total_8": round(ref_sec, 6),
            "operations": max(ref_operations),
            "solves": f"{8 - ref_failures}/8, as expected",
        },
        "intended_compact_route": {
            "name": "overlap-cycle reconstruction and cyclic XOR recurrence",
            "operations": max(compact_operations),
            "solves": f"{8 - compact_failures}/8",
            "wall_clock_sec": round(compact_sec / 8, 6),
        },
    }

    doubled_n = 2 * inst["n"]
    while doubled_n % 3 == 0:
        doubled_n += 1
    doubled_t0 = time.perf_counter()
    doubled = make_instance(n=doubled_n, copies=inst["copies"], seed=71)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_n > inst["n"],
        "shipping_n": inst["n"],
        "doubled_n": doubled_n,
        "shipping_graph_vertices": 6 + inst["n"] + 11 * len(inst["clauses"]),
        "doubled_graph_vertices": 6 + doubled_n + 11 * len(doubled["clauses"]),
        "doubled_build_and_verify_sec": round(time.perf_counter() - doubled_t0, 6),
        "doubled_verify_reason": doubled_why,
        "escalation_after_shipping": escalate(params),
    }

    invariant = 0
    real = 0
    transform_failures = []
    for seed in range(20):
        original = make_instance(seed=2000 + seed, **params)
        key = canonical_key(original)
        choices = (
            {"rename": True},
            {"reorder": True},
            {"polarity": True},
            {"rename": True, "reorder": True, "polarity": True},
        )
        for j, choice in enumerate(choices):
            transformed = _transform_instance(
                original, random.Random(50000 + 10 * seed + j), **choice
            )
            if canonical_key(transformed) == key:
                invariant += 1
            else:
                transform_failures.append({"seed": seed, "transform": choice,
                                           "failure": "key changed"})
            ok, why = verify(transformed, transformed["answer"])
            if ok:
                real += 1
            else:
                transform_failures.append({"seed": seed, "transform": choice,
                                           "failure": why})
    unrelated = [canonical_key(make_instance(seed=3000 + seed, **params))
                 for seed in range(20)]
    report["G8_canonical_key"] = {
        "pass": not transform_failures and invariant == 80 and real == 80
                and len(set(unrelated)) == 20,
        "transformations": [
            "variable renaming",
            "indexed-clause reordering",
            "global literal polarity with carried assignment",
            "their composition",
        ],
        "invariant_relabellings": invariant,
        "real_transformations_verified": real,
        "unrelated_attempts": 20,
        "unrelated_distinct_keys": len(set(unrelated)),
        "failures": transform_failures,
    }

    answer_chars, answer_tokens, answer_atoms = _answer_metrics(inst["answer"])
    route_ops = max(compact_operations)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    oracle_ready = all(arms[name]["attempts"] >= 3 for name in arms)
    hinted_hardened = (
        G9_ORACLE_RESULTS.get("hinted_verdict") == "hardened"
        and arms["hinted"]["solved"] == 0
    )
    within_caps = answer_chars <= 2000 and answer_atoms <= 256 and route_ops <= 300
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    report["G9_no_tool_suitability"] = {
        "pass": oracle_ready and hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS.get("hinted_verdict"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": route_ops,
        "within_caps": within_caps,
        "oracle_evidence_ready": oracle_ready,
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
