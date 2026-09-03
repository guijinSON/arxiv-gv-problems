"""Verified problem generator for arXiv:2411.16149, Directed Token Sliding.

The generated instances are oriented graphs (there is never an arc in both
directions). A witness is an exact-length sequence of directed token slides
between two independent sets. The inverse construction first samples a hidden
truth assignment, then a regular balanced NAE-3-SAT formula satisfied by it,
and finally compiles that formula into a directed token-sliding instance.

Only the Python standard library is used. Importing this module performs no
I/O and produces no output.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re
import time
from collections import defaultdict, deque


NATIVE = {
    "domain": "combinatorics",
    "core": "graph",
    "objects": [
        "oriented graph",
        "initial and target independent vertex sets",
        "exact move bound",
    ],
    "intuition": "phase invariants expose a hidden Boolean consistency constraint",
    "reduction": None,
}


CERTIFICATE_LANGUAGE = {
    "description": (
        "Normal-form token-slide witnesses: for an instance with n variables, "
        "one JSON move list is determined by each n-bit Boolean assignment. "
        "The phase order is fixed, and each clause gadget uses the lowest-index "
        "locally true gate (or gate 0 when none is locally true). Thus the "
        "language has exactly 2**n candidates, each containing exactly "
        "move_count pairs of vertex IDs in 0..vertex_count-1."
    ),
    "bounds": {
        "assignment_alphabet": 2,
        "assignment_length": "inst['n']",
        "candidate_count": "2 ** inst['n']",
        "moves_per_candidate": "inst['move_count']",
        "endpoints_per_move": 2,
        "endpoint_min": 0,
        "endpoint_max": "inst['vertex_count'] - 1",
    },
}


DIFFICULTY = {
    "easy": {"n": 144, "degree": 8},
    "medium": {"n": 168, "degree": 8},
    "hard": {"n": 192, "degree": 8},
}

SHIPPING_DIFFICULTY = "easy"


NOTES = r"""
Paper basis. Section 2 of Banerjee--Engels--Hoang, Directed Token Sliding
(arXiv:2411.16149v2), fixes the exact rule used here: configurations are
independent in the underlying undirected graph and one move follows one
directed arc from an occupied vertex to an unoccupied vertex. Section 3 proves
PSPACE-completeness on oriented split graphs, bipartite graphs, and even a
bounded-treewidth class; the introduction also recalls NP-completeness on
directed acyclic graphs. Section 4 is the warning that shaped this generator:
oriented cycles and cographs are polynomial-time, and the cited earlier result
makes oriented trees polynomial-time. The generated incidence gadgets have
cycles, induced P4s, and growing treewidth, so none of those algorithms applies.

Why the bounded witness is hard. Successful paths in this construction have
exactly 2*n + 4*m + 2 moves, where m is the number of NAE constraints. The two
choices at each variable encode a Boolean assignment. For each NAE clause, two
token gadgets require respectively a true and a false literal. Conversely,
every valid path yields such an assignment. Thus finding the requested
polynomial-size witness is the search problem for this regular NAE-3-SAT
distribution, rather than an unbounded PSPACE certificate. The worst-case
bounded family is NP-hard and no polynomial-time or closed-form method is
known. This is a distributional hardness claim, not a proof that every
generated instance requires exponential time.

Planting and attacks. Every variable occurs equally often, equally often with
both polarities, and its two value vertices have equal degree. Each constraint
has either one or two literals true under the plant, with the two cases exactly
balanced globally. Hence the planted value is absent from one-vertex degree
and sign-frequency statistics. selftest runs sign-frequency/outlier guessing,
deterministic greedy repair, 256-restart NAE WalkSAT, bounded DPLL with NAE unit
propagation, a signed spectral relaxation followed by repair, and ordinary
configuration-space BFS. Difficulty comes from formula size and constraint
density, not from different plant and decoy distributions.

Canonicalization caveat. Exact isomorphism of the signed 3-uniform incidence
structure is graph-isomorphism-like. canonical_key therefore uses a strong
cheap invariant: unsigned and switching-invariant signed closed-walk traces of
the variable co-occurrence multigraph. It is exactly invariant under vertex
renumbering, input order, variable permutation, literal order, clause order,
and independent Boolean-coordinate flips. Non-isomorphic cospectral formulas
can theoretically collide; the self-test checks distinctness but does not claim
a complete graph canonizer.
""".strip()


def _normalise_parameters(n: int, degree: int) -> tuple[int, int]:
    if type(n) is not int or type(degree) is not int:
        raise TypeError("n and degree must be integers")
    n = max(3, n)
    degree = max(2, degree)
    if degree % 2:
        degree += 1
    # Need an even m=n*degree/3 for equal one-true/two-true populations.
    while (n * degree) % 6:
        n += 1
    return n, degree


def _constraint_signature(clause: list[tuple[int, bool]]) -> tuple:
    """NAE clauses ignore literal order and complementing all three signs."""

    a = tuple(sorted((v, int(p)) for v, p in clause))
    b = tuple(sorted((v, 1 - int(p)) for v, p in clause))
    return min(a, b)


def _connected_hypergraph(n: int, clauses: list[list[tuple[int, bool]]]) -> bool:
    adj = [set() for _ in range(n)]
    for clause in clauses:
        vs = [v for v, _ in clause]
        for i in range(3):
            for j in range(i + 1, 3):
                adj[vs[i]].add(vs[j])
                adj[vs[j]].add(vs[i])
    seen = {0}
    todo = [0]
    while todo:
        u = todo.pop()
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                todo.append(v)
    return len(seen) == n


def _regular_planted_formula(
    n: int, degree: int, plant: list[int], rng: random.Random
) -> list[list[tuple[int, bool]]]:
    """Generate a degree-regular, polarity-balanced planted NAE-3-SAT formula."""

    m = n * degree // 3
    true_pool0 = [v for v in range(n) for _ in range(degree // 2)]
    false_pool0 = list(true_pool0)
    kinds0 = [1] * (m // 2) + [2] * (m // 2)

    for _ in range(20_000):
        true_pool = true_pool0[:]
        false_pool = false_pool0[:]
        kinds = kinds0[:]
        rng.shuffle(true_pool)
        rng.shuffle(false_pool)
        rng.shuffle(kinds)
        ti = fi = 0
        clauses: list[list[tuple[int, bool]]] = []
        ok = True
        seen = set()

        for true_count in kinds:
            wanted: list[tuple[int, int]] = []
            wanted.extend((v, 1) for v in true_pool[ti : ti + true_count])
            wanted.extend((v, 0) for v in false_pool[fi : fi + 3 - true_count])
            ti += true_count
            fi += 3 - true_count
            if len({v for v, _ in wanted}) != 3:
                ok = False
                break

            clause = []
            for v, truth_at_plant in wanted:
                positive = bool(plant[v]) == bool(truth_at_plant)
                clause.append((v, positive))
            rng.shuffle(clause)
            sig = _constraint_signature(clause)
            if n > 4 and sig in seen:
                ok = False
                break
            seen.add(sig)
            clauses.append(clause)

        if ok and len(clauses) == m and _connected_hypergraph(n, clauses):
            rng.shuffle(clauses)
            return clauses
    raise RuntimeError("could not construct a simple connected regular formula")


def _literal_value(literal: tuple[int, bool] | list, assignment: list[int]) -> int:
    v, positive = int(literal[0]), bool(literal[1])
    return assignment[v] if positive else 1 - assignment[v]


def _nae_satisfied(constraints: list, assignment: list[int]) -> bool:
    for clause in constraints:
        values = [_literal_value(lit, assignment) for lit in clause]
        if values[0] == values[1] == values[2]:
            return False
    return True


def _install_lookups(inst: dict) -> None:
    """Install private derived accelerators; no answer data is involved."""

    arcs = {tuple(x) for x in inst["arcs"]}
    und = [set() for _ in range(inst["vertex_count"])]
    out = [[] for _ in range(inst["vertex_count"])]
    for u, v in arcs:
        und[u].add(v)
        und[v].add(u)
        out[u].append(v)
    for row in out:
        row.sort()
    inst["_arc_set"] = arcs
    inst["_undirected"] = und
    inst["_out"] = out
    if "model" in inst:
        model = inst["model"]
        inst["_move_templates"] = {
            "choose": [
                [[x["s"], x["q"][0]], [x["s"], x["q"][1]]]
                for x in model["variables"]
            ],
            "finish": [
                [[x["q"][0], x["f"]], [x["q"][1], x["f"]]]
                for x in model["variables"]
            ],
            "clause": [
                [
                    ([x["c"], gate], [gate, x["t"]])
                    for gate in x["gates"]
                ]
                for x in model["clauses"]
            ],
        }
        templates = inst["_move_templates"]
        base = [templates["choose"][i][0] for i in range(inst["n"])]
        z0, z1, z2 = model["control"]
        base.append([z0, z1])
        for j in range(len(model["clauses"])):
            first, second = templates["clause"][j][0]
            base.extend((first, second))
        base.append([z1, z2])
        base.extend(templates["finish"][i][0] for i in range(inst["n"]))
        inst["_candidate_base"] = base


def _build_instance(
    n: int,
    degree: int,
    constraints0: list[list[tuple[int, bool]]],
    plant0: list[int],
    label_rng: random.Random,
    answer_rng: random.Random,
    seed: int,
) -> dict:
    """Compile a planted NAE formula to an oriented token-sliding instance."""

    constraints = [
        [[int(v), int(bool(p))] for v, p in clause] for clause in constraints0
    ]
    plant = [int(x) for x in plant0]
    m = len(constraints)
    next_vertex = 0

    def vertex() -> int:
        nonlocal next_vertex
        out = next_vertex
        next_vertex += 1
        return out

    variables = []
    for _ in range(n):
        variables.append({"s": vertex(), "q": [vertex(), vertex()], "f": vertex()})
    control = [vertex(), vertex(), vertex()]

    # Each NAE constraint becomes two OR gadgets: its literals and complements.
    or_literals: list[list[list[int]]] = []
    for clause in constraints:
        or_literals.append([[v, p] for v, p in clause])
        or_literals.append([[v, 1 - p] for v, p in clause])

    clauses = []
    for literals in or_literals:
        clauses.append(
            {
                "c": vertex(),
                "gates": [vertex(), vertex(), vertex()],
                "t": vertex(),
                "literals": [list(lit) for lit in literals],
            }
        )

    arc_set: set[tuple[int, int]] = set()

    def arc(u: int, v: int) -> None:
        if u == v or (v, u) in arc_set:
            raise AssertionError("construction would not be an oriented graph")
        arc_set.add((u, v))

    z0, z1, z2 = control
    arc(z0, z1)
    arc(z1, z2)

    for var in variables:
        s, (q0, q1), f = var["s"], var["q"], var["f"]
        arc(s, q0)
        arc(s, q1)
        arc(q0, f)
        arc(q1, f)
        arc(z0, f)  # z0 blocks premature finalisation.
        arc(z1, s)
        arc(z1, f)  # z1 blocks finalisation during clause checks.

    for clause in clauses:
        c, gates, t = clause["c"], clause["gates"], clause["t"]
        arc(z2, c)  # z1 -> z2 waits until every c is vacated.
        for gate, literal in zip(gates, clause["literals"]):
            v, positive = literal
            false_value = 0 if positive else 1
            arc(c, gate)
            arc(gate, t)
            arc(gate, variables[v]["q"][false_value])
            arc(gate, z0)  # z0 blocks every clause gate initially.

    vertex_count = next_vertex
    labels = list(range(vertex_count))
    label_rng.shuffle(labels)

    def lab(v: int) -> int:
        return labels[v]

    actual_arcs = [[lab(u), lab(v)] for u, v in arc_set]
    label_rng.shuffle(actual_arcs)
    actual_variables = [
        {"s": lab(x["s"]), "q": [lab(x["q"][0]), lab(x["q"][1])], "f": lab(x["f"])}
        for x in variables
    ]
    actual_control = [lab(x) for x in control]
    actual_clauses = [
        {
            "c": lab(x["c"]),
            "gates": [lab(g) for g in x["gates"]],
            "t": lab(x["t"]),
            "literals": [list(lit) for lit in x["literals"]],
        }
        for x in clauses
    ]

    start = [x["s"] for x in actual_variables]
    start.extend(x["c"] for x in actual_clauses)
    start.append(actual_control[0])
    target = [x["f"] for x in actual_variables]
    target.extend(x["t"] for x in actual_clauses)
    target.append(actual_control[2])
    label_rng.shuffle(start)
    label_rng.shuffle(target)

    inst = {
        "paper": "arXiv:2411.16149v2",
        "family": "exact-length directed token sliding encoding regular NAE-3-SAT",
        "n": n,
        "degree": degree,
        "constraint_count": m,
        "vertex_count": vertex_count,
        "move_count": 2 * n + 4 * m + 2,
        "arcs": actual_arcs,
        "start": start,
        "target": target,
        "constraints": constraints,
        "model": {
            "variables": actual_variables,
            "control": actual_control,
            "clauses": actual_clauses,
        },
        "seed": seed,
    }
    _install_lookups(inst)
    answer = _witness_from_assignment(inst, plant, answer_rng, require_solution=True)
    if answer is None:
        raise AssertionError("the planted assignment unexpectedly failed")
    inst["answer"] = answer
    return inst


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Sample the answer first, then build a directed token-sliding instance."""

    degree = params.pop("degree", 8)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    n, degree = _normalise_parameters(n, degree)
    rng = random.Random(seed)
    plant = [rng.randrange(2) for _ in range(n)]
    constraints = _regular_planted_formula(n, degree, plant, rng)
    label_rng = random.Random(rng.getrandbits(128))
    answer_rng = random.Random(rng.getrandbits(128))
    return _build_instance(n, degree, constraints, plant, label_rng, answer_rng, seed)


def render(inst: dict) -> str:
    """Return the complete, self-contained problem statement."""

    lines = [
        "DIRECTED TOKEN SLIDING — EXACT-LENGTH SEARCH",
        "",
        "Definitions and rules:",
        f"- The graph has vertices 0 through {inst['vertex_count'] - 1}.",
        "- Each ordered pair u v listed below is a directed arc u -> v. No reverse arc is implied.",
        "- A configuration is a set of occupied vertices, with at most one token per vertex.",
        "- A configuration is independent when no two occupied vertices are adjacent after arc directions are ignored; in other words, for no listed arc u -> v may both u and v be occupied.",
        "- One legal slide chooses an occupied source u and an unoccupied destination v, requires the listed arc u -> v, moves that token from u to v, and leaves an independent configuration.",
        "- Tokens are indistinguishable. Vertex numbers are 0-indexed. Reusing a directed arc at different times is allowed if the move is legal each time.",
        "",
        f"Start configuration ({len(inst['start'])} occupied vertices):",
        " ".join(str(x) for x in sorted(inst["start"])),
        "",
        f"Target configuration ({len(inst['target'])} occupied vertices):",
        " ".join(str(x) for x in sorted(inst["target"])),
        "",
        f"Find exactly {inst['move_count']} legal slides that transform the start configuration into the target configuration.",
        "Order matters and every move is applied to the configuration produced by the preceding move.",
        "",
        f"Directed arcs ({len(inst['arcs'])} total), one `u v` pair per line:",
    ]
    lines.extend(f"{u} {v}" for u, v in inst["arcs"])
    lines.extend(
        [
            "",
            "Give your final answer inside <answer></answer> tags, as a JSON list of exactly the required number of [source,destination] integer pairs.",
            "Example: <answer>[[3,17],[8,42]]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Parse the delimited JSON witness, tolerating prose and Markdown fences."""

    try:
        match = re.search(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
        obj = json.loads(body)
        if not isinstance(obj, list):
            return None
        answer = []
        for move in obj:
            if (
                not isinstance(move, (list, tuple))
                or len(move) != 2
                or type(move[0]) is not int
                or type(move[1]) is not int
            ):
                return None
            answer.append([move[0], move[1]])
        return answer
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Replay a candidate exactly. The planted answer is never inspected."""

    if not isinstance(answer, list):
        return False, "malformed answer: expected a JSON list of moves"
    if not answer:
        return False, "empty answer: at least one slide is required"
    if len(answer) != inst["move_count"]:
        return False, f"wrong length: expected {inst['move_count']} moves, got {len(answer)}"

    vertex_count = inst["vertex_count"]
    arcs = inst.get("_arc_set")
    und = inst.get("_undirected")
    if arcs is None or und is None:
        arcs = {tuple(x) for x in inst["arcs"]}
        und = [set() for _ in range(vertex_count)]
        for u, v in arcs:
            und[u].add(v)
            und[v].add(u)

    occupied = set(inst["start"])
    if len(occupied) != len(inst["start"]):
        return False, "invalid instance: duplicate start vertex"
    for step, move in enumerate(answer):
        if not isinstance(move, (list, tuple)) or len(move) != 2:
            return False, f"move {step}: malformed move, expected [source,destination]"
        u, v = move
        if type(u) is not int or type(v) is not int:
            return False, f"move {step}: endpoints must be integers"
        if not (0 <= u < vertex_count) or not (0 <= v < vertex_count):
            return False, f"move {step}: endpoint out of range 0..{vertex_count - 1}"
        if u not in occupied:
            return False, f"move {step}: source {u} is unoccupied"
        if v in occupied:
            return False, f"move {step}: destination {v} is occupied"
        if (u, v) not in arcs:
            return False, f"move {step}: {u}->{v} is not a directed arc"
        conflicts = (und[v] & occupied) - {u}
        if conflicts:
            w = min(conflicts)
            return False, f"move {step}: independence violation between {v} and occupied {w}"
        occupied.remove(u)
        occupied.add(v)

    target = set(inst["target"])
    if occupied != target:
        missing = sorted(target - occupied)
        extra = sorted(occupied - target)
        return False, f"wrong final configuration: missing {missing[:4]}, extra {extra[:4]}"
    return True, "ok"


def _witness_from_assignment(
    inst: dict,
    assignment: list[int],
    rng: random.Random,
    require_solution: bool,
    shuffle_order: bool = True,
) -> list[list[int]] | None:
    """Use the natural shortest-path template for an assignment."""

    if len(assignment) != inst["n"] or any(x not in (0, 1) for x in assignment):
        return None
    model = inst["model"]
    templates = inst["_move_templates"]
    moves: list[list[int]] = []

    order = list(range(inst["n"]))
    if shuffle_order:
        rng.shuffle(order)
    for i in order:
        moves.append(templates["choose"][i][assignment[i]])
    z0, z1, z2 = model["control"]
    moves.append([z0, z1])

    clause_order = list(range(len(model["clauses"])))
    if shuffle_order:
        rng.shuffle(clause_order)
    for j in clause_order:
        clause = model["clauses"][j]
        choices = [
            k
            for k, literal in enumerate(clause["literals"])
            if _literal_value(literal, assignment)
        ]
        if not choices:
            if require_solution:
                return None
            choices = [rng.randrange(3)]
        k = rng.choice(choices)
        first, second = templates["clause"][j][k]
        moves.append(first)
        moves.append(second)

    moves.append([z1, z2])
    if shuffle_order:
        rng.shuffle(order)
    for i in order:
        moves.append(templates["finish"][i][assignment[i]])
    return moves


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample after enforcing the obvious shortest-path structure.

    Sources, destinations, length, directions, phase order, and a locally true
    gate whenever one exists are built in. What remains random is the global
    assignment; satisfying every NAE constraint is exactly the hard part. No
    planted data is read.
    """

    n = inst["n"]
    assignment = [rng.randrange(2) for _ in range(n)]
    templates = inst["_move_templates"]
    answer = inst["_candidate_base"].copy()
    clause_count = len(inst["model"]["clauses"])
    finish_offset = n + 2 + 2 * clause_count
    for i, value in enumerate(assignment):
        answer[i] = templates["choose"][i][value]
        answer[finish_offset + i] = templates["finish"][i][value]

    # Clause gadgets are paired in the same order as NAE constraints. Even
    # after a global contradiction, choose a locally true gate in every later
    # gadget whenever one exists. Lowest-index tie-breaking makes this exactly
    # the 2**n-element language declared in CERTIFICATE_LANGUAGE.
    for j, constraint in enumerate(inst["constraints"]):
        values = [_literal_value(lit, assignment) for lit in constraint]
        for complement in (0, 1):
            gadget = 2 * j + complement
            wanted = 1 - complement
            choices = [k for k, value in enumerate(values) if value == wanted]
            k = choices[0] if choices else 0
            first, second = templates["clause"][gadget][k]
            offset = n + 1 + 2 * gadget
            answer[offset] = first
            answer[offset + 1] = second
    return answer


def search_space(inst: dict) -> int:
    """Return the exact size of the declared normal-form language."""

    return 1 << inst["n"]


def _linear_extension_count(n: int, clause_gadgets: int) -> int:
    """Count legal orderings of the shortest-path event partial order."""

    c = clause_gadgets
    middle = 0
    for r in range(c + 1):
        prefix = math.comb(c, r) * math.factorial(c + r) // (1 << r)
        suffix = math.factorial(c - r + n)
        middle += prefix * suffix
    return math.factorial(n) * middle


def enumerate_all(inst: dict) -> int | None:
    """Count valid candidates in CERTIFICATE_LANGUAGE when n <= 22."""

    n = inst["n"]
    if n > 22:
        return None
    satisfying = 0
    for bits in itertools.product((0, 1), repeat=n):
        if _nae_satisfied(inst["constraints"], list(bits)):
            satisfying += 1
    return satisfying


def _pair_edges(inst: dict, signed: bool) -> list[tuple[int, int, int]]:
    weights: dict[tuple[int, int], int] = defaultdict(int)
    for clause in inst["constraints"]:
        for i in range(3):
            for j in range(i + 1, 3):
                vi, pi = clause[i]
                vj, pj = clause[j]
                if vi > vj:
                    vi, vj, pi, pj = vj, vi, pj, pi
                weight = (1 if pi else -1) * (1 if pj else -1) if signed else 1
                weights[(vi, vj)] += weight
    return [(u, v, w) for (u, v), w in sorted(weights.items()) if w]


def _closed_walk_traces(n: int, edges: list[tuple[int, int, int]], steps: int) -> list[int]:
    """Traces of adjacency powers modulo a prime, invariant under relabelling."""

    prime = 1_000_000_007
    traces = [0] * (steps + 1)
    for start in range(n):
        vec = [0] * n
        vec[start] = 1
        for k in range(1, steps + 1):
            nxt = [0] * n
            for u, v, w in edges:
                nxt[u] += w * vec[v]
                nxt[v] += w * vec[u]
            vec = [x % prime for x in nxt]
            traces[k] = (traces[k] + vec[start]) % prime
    return traces[2:]


def canonical_key(inst: dict) -> str:
    """Return a structural key invariant under all supported relabellings.

    Signed traces are invariant under independent variable value flips because
    those conjugate the signed adjacency matrix by a diagonal +/-1 matrix.
    This is a strong invariant, not a complete graph-isomorphism canonizer.
    """

    n = inst["n"]
    steps = min(16, n)
    payload = {
        "family": "regular-nae-dts-v1",
        "n": n,
        "degree": inst["degree"],
        "m": inst["constraint_count"],
        "unsigned_traces": _closed_walk_traces(n, _pair_edges(inst, False), steps),
        "signed_traces": _closed_walk_traces(n, _pair_edges(inst, True), steps),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase the hidden assignment dimension while retaining density."""

    n = int(params.get("n", 144))
    degree = int(params.get("degree", 8))
    if n >= 240:
        return None
    return {"n": n + 24, "degree": degree}


# ---------------------------------------------------------------------------
# Adversary panel


def _candidate_for_assignment(inst: dict, assignment: list[int], salt: int) -> object | None:
    if not _nae_satisfied(inst["constraints"], assignment):
        return None
    return _witness_from_assignment(
        inst, assignment, random.Random(salt), require_solution=True
    )


def _attack_outlier_literal_frequency(inst: dict, rng: random.Random) -> object | None:
    del rng
    positive = [0] * inst["n"]
    negative = [0] * inst["n"]
    for clause in inst["constraints"]:
        for v, p in clause:
            (positive if p else negative)[v] += 1
    assignment = [int(positive[v] > negative[v]) for v in range(inst["n"])]
    return _candidate_for_assignment(inst, assignment, 101)


def _violated_clauses(inst: dict, assignment: list[int]) -> list[int]:
    bad = []
    for j, clause in enumerate(inst["constraints"]):
        values = [_literal_value(lit, assignment) for lit in clause]
        if values[0] == values[1] == values[2]:
            bad.append(j)
    return bad


def _greedy_repair(inst: dict, assignment: list[int], steps: int) -> list[int] | None:
    """Deterministic best-improvement local repair."""

    current = len(_violated_clauses(inst, assignment))
    for _ in range(steps):
        if current == 0:
            return assignment
        best_value = current
        best_var = None
        for v in range(inst["n"]):
            assignment[v] ^= 1
            value = len(_violated_clauses(inst, assignment))
            assignment[v] ^= 1
            if value < best_value:
                best_value = value
                best_var = v
        if best_var is None:
            return None
        assignment[best_var] ^= 1
        current = best_value
    return assignment if current == 0 else None


def _attack_greedy(inst: dict, rng: random.Random) -> object | None:
    del rng
    assignment = [0] * inst["n"]
    found = _greedy_repair(inst, assignment, 2 * inst["n"])
    return None if found is None else _candidate_for_assignment(inst, found, 102)


def _attack_random_restart(inst: dict, rng: random.Random) -> object | None:
    """NAE WalkSAT: select a violated clause and flip a random incident variable."""

    n = inst["n"]
    for _ in range(256):
        assignment = [rng.randrange(2) for _ in range(n)]
        for _ in range(4 * n):
            bad = _violated_clauses(inst, assignment)
            if not bad:
                return _candidate_for_assignment(inst, assignment, rng.getrandbits(64))
            clause = inst["constraints"][rng.choice(bad)]
            assignment[rng.choice(clause)[0]] ^= 1
    return None


class _DPLLLimit(Exception):
    pass


def _nae_propagate(constraints: list, assignment: list[int]) -> bool:
    changed = True
    while changed:
        changed = False
        for clause in constraints:
            known = []
            unknown = []
            for v, p in clause:
                if assignment[v] < 0:
                    unknown.append((v, bool(p)))
                else:
                    known.append(assignment[v] if p else 1 - assignment[v])
            if not unknown:
                if known[0] == known[1] == known[2]:
                    return False
                continue
            if len(unknown) == 1 and known[0] == known[1]:
                v, positive = unknown[0]
                literal_needed = 1 - known[0]
                value_needed = literal_needed if positive else 1 - literal_needed
                if assignment[v] >= 0 and assignment[v] != value_needed:
                    return False
                if assignment[v] < 0:
                    assignment[v] = value_needed
                    changed = True
    return True


def _dpll_search(inst: dict, node_limit: int = 10_000) -> tuple[object | None, dict]:
    """Run bounded NAE DPLL and return both its candidate and measured work."""

    constraints = inst["constraints"]
    occurrence = [0] * inst["n"]
    for clause in constraints:
        for v, _ in clause:
            occurrence[v] += 1
    nodes = 0

    def solve(assignment: list[int]) -> list[int] | None:
        nonlocal nodes
        nodes += 1
        if nodes > node_limit:
            raise _DPLLLimit
        assignment = assignment[:]
        if not _nae_propagate(constraints, assignment):
            return None
        if all(x >= 0 for x in assignment):
            return assignment
        unassigned = [v for v, x in enumerate(assignment) if x < 0]
        v = max(unassigned, key=lambda x: (occurrence[x], -x))
        for value in (0, 1):
            child = assignment[:]
            child[v] = value
            out = solve(child)
            if out is not None:
                return out
        return None

    limit_reached = False
    try:
        found = solve([-1] * inst["n"])
    except _DPLLLimit:
        found = None
        limit_reached = True
    candidate = (
        None if found is None else _candidate_for_assignment(inst, found, 103)
    )
    return candidate, {
        "nodes": nodes,
        "node_limit": node_limit,
        "limit_reached": limit_reached,
    }


def _attack_dpll(
    inst: dict, rng: random.Random, node_limit: int = 10_000
) -> object | None:
    """Standard DPLL with NAE unit propagation and a bounded search budget."""

    del rng
    candidate, _ = _dpll_search(inst, node_limit)
    return candidate


def _attack_spectral(inst: dict, rng: random.Random) -> object | None:
    """Signed smallest-eigenvector relaxation, then local repair."""

    n = inst["n"]
    edges = _pair_edges(inst, True)
    shift = 2 * inst["degree"] + 1.0
    vec = [rng.uniform(-1.0, 1.0) for _ in range(n)]
    for _ in range(100):
        nxt = [shift * x for x in vec]
        for u, v, w in edges:
            nxt[u] -= w * vec[v]
            nxt[v] -= w * vec[u]
        norm = math.sqrt(sum(x * x for x in nxt)) or 1.0
        vec = [x / norm for x in nxt]
    base = [int(x >= 0.0) for x in vec]
    for candidate in (base, [1 - x for x in base]):
        if _nae_satisfied(inst["constraints"], candidate):
            return _candidate_for_assignment(inst, candidate, 104)
        repaired = _greedy_repair(inst, candidate[:], 2 * n)
        if repaired is not None:
            return _candidate_for_assignment(inst, repaired, 105)
    return None


def _attack_configuration_bfs(
    inst: dict, rng: random.Random, state_limit: int = 20_000
) -> object | None:
    """The standard explicit configuration-graph breadth-first search."""

    del rng
    start = tuple(sorted(inst["start"]))
    target = tuple(sorted(inst["target"]))
    out = inst["_out"]
    und = inst["_undirected"]
    queue = deque([start])
    parent: dict[tuple[int, ...], tuple[tuple[int, ...], list[int]] | None] = {start: None}

    while queue and len(parent) < state_limit:
        state = queue.popleft()
        occupied = set(state)
        for u in state:
            for v in out[u]:
                if v in occupied or ((und[v] & occupied) - {u}):
                    continue
                nxt_set = occupied.copy()
                nxt_set.remove(u)
                nxt_set.add(v)
                nxt = tuple(sorted(nxt_set))
                if nxt in parent:
                    continue
                parent[nxt] = (state, [u, v])
                if nxt == target:
                    moves = []
                    cur = nxt
                    while parent[cur] is not None:
                        prev, move = parent[cur]
                        moves.append(move)
                        cur = prev
                    moves.reverse()
                    return moves
                queue.append(nxt)
                if len(parent) >= state_limit:
                    break
            if len(parent) >= state_limit:
                break
    return None


def _corruptions(inst: dict) -> dict[str, object]:
    answer = [move[:] for move in inst["answer"]]
    swapped = [move[:] for move in answer]
    swapped[0] = [swapped[0][1], swapped[0][0]]
    duplicated = [move[:] for move in answer]
    duplicated[1] = duplicated[0][:]
    out_of_range = [move[:] for move in answer]
    out_of_range[0] = [inst["vertex_count"], out_of_range[0][1]]
    return {
        "drop_one": answer[:-1],
        "swap_one": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }


def _relabel_instance(inst: dict, rng: random.Random) -> tuple[dict, list[list[int]]]:
    """Apply an arbitrary vertex permutation and input-list reorder."""

    perm = list(range(inst["vertex_count"]))
    rng.shuffle(perm)

    def pv(v: int) -> int:
        return perm[v]

    variables = [
        {"s": pv(x["s"]), "q": [pv(x["q"][0]), pv(x["q"][1])], "f": pv(x["f"])}
        for x in inst["model"]["variables"]
    ]
    clauses = [
        {
            "c": pv(x["c"]),
            "gates": [pv(g) for g in x["gates"]],
            "t": pv(x["t"]),
            "literals": [lit[:] for lit in x["literals"]],
        }
        for x in inst["model"]["clauses"]
    ]
    arcs = [[pv(u), pv(v)] for u, v in inst["arcs"]]
    start = [pv(v) for v in inst["start"]]
    target = [pv(v) for v in inst["target"]]
    answer = [[pv(u), pv(v)] for u, v in inst["answer"]]
    rng.shuffle(arcs)
    rng.shuffle(start)
    rng.shuffle(target)
    changed = {
        k: v
        for k, v in inst.items()
        if k not in {"arcs", "start", "target", "answer", "model", "_arc_set", "_undirected", "_out"}
    }
    changed.update(
        arcs=arcs,
        start=start,
        target=target,
        answer=answer,
        model={
            "variables": variables,
            "control": [pv(v) for v in inst["model"]["control"]],
            "clauses": clauses,
        },
    )
    _install_lookups(changed)
    return changed, answer


def _formula_symmetry_instance(inst: dict, rng: random.Random) -> dict:
    """Compose variable permutation/value flips and clause/literal reorder."""

    n = inst["n"]
    var_perm = list(range(n))
    rng.shuffle(var_perm)
    flips = [rng.randrange(2) for _ in range(n)]

    transformed = []
    for clause in inst["constraints"]:
        row = []
        for old_v, old_p in clause:
            row.append((var_perm[old_v], bool(old_p ^ flips[old_v])))
        # Complementing one entire NAE clause merely swaps its two compiled OR
        # gadgets, so include this independent family-specific symmetry too.
        if rng.randrange(2):
            row = [(v, not p) for v, p in row]
        rng.shuffle(row)
        transformed.append(row)
    rng.shuffle(transformed)

    # Recover one satisfying assignment from the stored planted witness without
    # reading inst["answer"] is unnecessary here: this is a self-test helper,
    # and a small DPLL run obtains a witness for the transformed formula.
    assignment = [-1] * n
    source_constraints = [
        [[int(v), int(bool(p))] for v, p in clause] for clause in transformed
    ]

    def solve(pos: int) -> list[int] | None:
        if pos == n:
            return assignment[:] if _nae_satisfied(source_constraints, assignment) else None
        # Unit propagation keeps this transformation test cheap even for n=48.
        trial = assignment[:]
        if not _nae_propagate(source_constraints, trial):
            return None
        if all(x >= 0 for x in trial):
            return trial
        v = next(i for i, x in enumerate(trial) if x < 0)
        for value in (0, 1):
            saved = assignment[:]
            assignment[:] = trial
            assignment[v] = value
            result = solve(v + 1)
            if result is not None:
                return result
            assignment[:] = saved
        return None

    found = solve(0)
    if found is None:
        raise AssertionError("formula symmetry lost satisfiability")
    return _build_instance(
        n,
        inst["degree"],
        transformed,
        found,
        random.Random(rng.getrandbits(128)),
        random.Random(rng.getrandbits(128)),
        inst.get("seed", 0),
    )


def _run_attacks(params: dict, seeds: list[int]) -> dict:
    attacks = {
        "outlier_literal_frequency": _attack_outlier_literal_frequency,
        "greedy_best_improvement": _attack_greedy,
        "random_restart_256": _attack_random_restart,
        "dpll_unit_propagation_10000": _attack_dpll,
        "spectral_signed_eigenvector": _attack_spectral,
        "configuration_bfs_20000": _attack_configuration_bfs,
    }
    instances = [(seed, make_instance(seed=seed, **params)) for seed in seeds]
    results = {}
    for name, attack in attacks.items():
        successes = 0
        reasons = []
        for seed, inst in instances:
            candidate = attack(inst, random.Random(700_000 + seed))
            if candidate is None:
                reasons.append("no candidate")
                continue
            ok, why = verify(inst, candidate)
            if ok:
                successes += 1
                reasons.append("ok")
            else:
                reasons.append(why)
        results[name] = {
            "successes": successes,
            "attempts": len(seeds),
            "results": reasons,
        }
    return results


def selftest() -> dict:
    """Run all mandatory correctness, resistance, scaling, and invariance gates."""

    report: dict[str, object] = {
        "paper": "2411.16149",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: every named preset, several seeds.
    g1_rows = {}
    g1_pass = True
    for name, params in DIFFICULTY.items():
        rows = []
        for seed in (0, 1, 2, 3):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            rows.append({"seed": seed, "ok": ok, "reason": why})
            g1_pass &= ok
        g1_rows[name] = rows
    report["G1_planted_verifies"] = {"pass": g1_pass, "presets": g1_rows}

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=12_345, **shipping)

    # G2: five corruptions and five distinct diagnostics.
    corruption_rows = {}
    for name, candidate in _corruptions(inst).items():
        ok, why = verify(inst, candidate)
        corruption_rows[name] = {"accepted": ok, "reason": why}
    reasons = [row["reason"] for row in corruption_rows.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not row["accepted"] for row in corruption_rows.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_rows,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic prose plus a fenced JSON payload.
    response = (
        "I replayed every directed slide and obtained the target.\n\n"
        "<answer>\n```json\n"
        + json.dumps(inst["answer"], separators=(",", ":"))
        + "\n```\n</answer>\nThe tagged block is my final witness."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"],
        "parsed_moves": None if parsed is None else len(parsed),
    }

    # G4: the sampler has already enforced arcs, length, start/target paths,
    # phase structure, and local gate choice. Only global NAE consistency remains.
    guess_rng = random.Random(999_001)
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
        "p_hat": hits / total,
        "prior": "uniform assignment; legal shortest-path template and locally true gates built in",
    }

    # G5: measure the same shipping instance used by G4. Exact enumeration is
    # intentionally bounded to n <= 22, so shipping density is sampled. The
    # strongest systematic G6 attack is also timed on this shipping instance.
    baseline_started = time.perf_counter()
    baseline_candidate, baseline_stats = _dpll_search(inst)
    baseline_seconds = time.perf_counter() - baseline_started
    baseline_ok = (
        False
        if baseline_candidate is None
        else verify(inst, baseline_candidate)[0]
    )
    small = make_instance(n=9, degree=4, seed=77)
    small_valid = enumerate_all(small)
    small_space = search_space(small)
    small_ratio = small_valid / small_space
    report["G5_sparse"] = {
        "pass": hits / total < 1e-6,
        "shipping_density": {
            "preset": SHIPPING_DIFFICULTY,
            "n": inst["n"],
            "degree": inst["degree"],
            "method": "random_candidate samples checked by verify",
            "valid_samples": hits,
            "samples": total,
            "observed_fraction": hits / total,
            "search_space": search_space(inst),
        },
        "shipping_baseline_cost": {
            "attack": "NAE DPLL with unit propagation",
            "seed": inst["seed"],
            "solved": baseline_ok,
            "wall_seconds": round(baseline_seconds, 6),
            **baseline_stats,
        },
        "small_exact_reference": {
            "n": small["n"],
            "degree": small["degree"],
            "valid_candidates": small_valid,
            "search_space": small_space,
            "fraction": small_ratio,
        },
    }

    # G6: generic planting probes plus both domain-standard solver views.
    attacks = _run_attacks(shipping, list(range(100, 108)))
    report["G6_adversary_panel"] = {
        "pass": all(row["successes"] == 0 for row in attacks.values()),
        "attacks": attacks,
    }

    # G7: double only n, retaining the same constraint density.
    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=54_321, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["vertex_count"] > inst["vertex_count"]
        and doubled["move_count"] > inst["move_count"],
        "base_n": inst["n"],
        "base_vertices": inst["vertex_count"],
        "base_moves": inst["move_count"],
        "doubled_n": doubled["n"],
        "doubled_vertices": doubled["vertex_count"],
        "doubled_moves": doubled["move_count"],
        "verify": [doubled_ok, doubled_why],
    }

    # G8: arbitrary vertex relabelling/input order, then composition with the
    # formula's variable/sign/clause/literal symmetries.
    invariant_checks = 0
    carried_witness_checks = 0
    invariant_ok = True
    carried_ok = True
    for seed in range(20):
        base = make_instance(n=24, degree=6, seed=10_000 + seed)
        key = canonical_key(base)
        relabelled, carried = _relabel_instance(base, random.Random(20_000 + seed))
        invariant_ok &= canonical_key(relabelled) == key
        invariant_checks += 1
        ok, _ = verify(relabelled, carried)
        carried_ok &= ok
        carried_witness_checks += 1

        symmetric = _formula_symmetry_instance(base, random.Random(30_000 + seed))
        invariant_ok &= canonical_key(symmetric) == key
        invariant_checks += 1
        ok, _ = verify(symmetric, symmetric["answer"])
        carried_ok &= ok
        carried_witness_checks += 1

        composed, carried2 = _relabel_instance(symmetric, random.Random(40_000 + seed))
        invariant_ok &= canonical_key(composed) == key
        invariant_checks += 1
        ok, _ = verify(composed, carried2)
        carried_ok &= ok
        carried_witness_checks += 1

    unrelated = {
        canonical_key(make_instance(n=24, degree=6, seed=50_000 + seed))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariant_ok and carried_ok and len(unrelated) == 20,
        "invariance_checks": invariant_checks,
        "invariance_passed": invariant_checks if invariant_ok else None,
        "carried_witness_checks": carried_witness_checks,
        "carried_witness_passed": carried_witness_checks if carried_ok else None,
        "unrelated_instances": 20,
        "distinct_keys": len(unrelated),
        "invariant": "unsigned and switching-invariant signed closed-walk traces",
        "complete_isomorphism_canonizer": False,
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
