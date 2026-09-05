"""Verified problem generator for arXiv:2105.06349.

The paper's Lemma 4 reduces 3-SAT to 2-Disjoint Connected Subgraphs on
line graphs.  This module uses that reduction in its original rail-and-clause
form.  It inverse-generates a satisfiable XOR circuit, expands each ternary
parity equation to four 3-CNF clauses, and carries the sampled input through
the reduction to two disjoint connected vertex sets in a claw-free line graph.

The submitted witness is a compact rail-choice vector for the input wires.
The checker deterministically expands it to every formula variable and then
checks the two connected sets in the line graph exactly.  No answer is found
by solving a generated instance.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time
from collections import defaultdict, deque


TRACK = "B"


PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "claw-free line graph specified by the paper's rail-and-clause construction",
        "two terminal sets for Disjoint Connected Subgraphs",
        "ternary GF(2) equations expanded into 3-CNF clause gadgets",
    ],
    "verification_operations": [
        "exact XOR evaluation over GF(2)",
        "exact construction of the two line-graph vertex sets",
        "line-graph edge-intersection connectivity",
        "set disjointness and terminal containment",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3, Lemma 4: the explicit 3-SAT rail-and-clause construction "
        "followed by its line graph"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "reduction recognition",
    "intuition_description": (
        "Recognize the four-clause blocks as cyclic parity equations, invert the "
        "three-shift relation, and reverse the XOR circuit; without that structure "
        "one performs general elimination on the whole encoded system."
    ),
    "hardness_basis": (
        "Track B: exact Gaussian elimination over GF(2) solves the encoded system "
        "in O(V^3); at the shipping preset V=268 the scalar reference baseline "
        "uses about 263,000 XOR/pivot operations and 0.03 seconds (measured in "
        "selftest), whereas the cyclic inverse plus circuit reversal uses 300 XORs."
    ),
    "max_answer_tokens": 24,
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


CERTIFICATE_LANGUAGE = {
    "description": (
        "A length-n binary rail-choice vector. Entry i is 0 or 1 and fixes the "
        "rail for the i-th displayed input wire; the gate equations uniquely "
        "extend it to a concrete pair of connected vertex sets."
    ),
    "bounds": {
        "length": "n input wires",
        "alphabet": [0, 1],
        "candidate_count": "2^n",
        "shipping_length": 32,
    },
}


DIFFICULTY = {
    "demo": {"n": 4, "gates": 4},
    "easy": {"n": 32, "gates": 160},
    "medium": {"n": 32, "gates": 192},
    "hard": {"n": 32, "gates": 236},
}

SHIPPING_DIFFICULTY = "hard"


STRUCTURAL_HINT = (
    "The first-to-second wire maps in the CHECK rows form one cyclic parity "
    "operator, with each third wire at the antipodal position."
)
PLACEBO_HINT = (
    "The wire identifiers and equation identifiers are exact labels, so careful "
    "bookkeeping across the displayed rows is important."
)


# Patched only after transcripts have been produced by scripts/harden.py.
G9_ORACLE_RESULTS = {
    "bare": {"solved": None, "attempts": 0},
    "hinted": {"solved": None, "attempts": 0},
    "placebo": {"solved": None, "attempts": 0},
    "hinted_verdict": "pending",
}


NOTES = r"""
Section 1 fixes both native problems and the disjointness convention.  The
generator uses 2-Disjoint Connected Subgraphs, not fixed-k Disjoint Paths:
Theorem 1.1 says fixed-k Disjoint Paths is polynomial-time solvable on every
graph, so the prior suggestion to plant a fixed number of paths cannot support
a Track A claim.

Section 3, Lemma 4 is the construction used here.  Its proof replaces every
Boolean variable by positive and negative rails, joins successive rail gadgets
with both straight and crossed edges, attaches clause vertices to literal
occurrences, and takes the line graph.  A satisfying assignment selects the
false-literal rails for S1 and the complementary true-literal rails plus all
clause edges for S2.  This module executes those set and connectivity checks.
Every produced graph is claw-free because it is a line graph.

The easy-result triage changes the track.  Theorem 6.2 gives O(3^N k m) dynamic
programming for arbitrary Disjoint Connected Subgraphs, and our structured
source system has the still stronger polynomial Gaussian-elimination route.
Track A would therefore be false for this distribution.  Track B reports the
Gaussian route and measures it.  The compact route uses
(I+T+T^(n/2))^(-1)=T^(n/2-2)+T^(n-2)+T^(n-1) for power-of-two n, followed by
reversing the displayed linear XOR gates.

Generation samples the input certificate first, evaluates a random reversible
XOR circuit, and forms the cyclic right-hand sides.  Random wire relabelling,
equation numbering, clause-slot ordering, rail ordering and gate topology remove
positional planting signals.  Literal signs are exactly
balanced inside every four-clause parity block.  The adversary panel tests sign
frequency, one-pass greedy descent, constant/alternating ansatzes, unbranched
unit propagation, and restarted coordinate descent; the expected-success
Gaussian solver is reported separately.
""".strip()


def _is_power_of_two(value):
    return value >= 1 and value & (value - 1) == 0


def _forbidden_codes(rhs, rng):
    codes = [
        f"{a}{b}{c}"
        for a in (0, 1)
        for b in (0, 1)
        for c in (0, 1)
        if (a ^ b ^ c) != rhs
    ]
    rng.shuffle(codes)
    return codes


def make_instance(n, seed=0, **params):
    """Inverse-generate a certified Lemma-4 line-graph instance.

    ``n`` is the number of input bits and must be a power of two.  ``gates``
    increases circuit mixing and graph size without increasing answer length.
    The input assignment is sampled before any right-hand side is constructed.
    """

    gates = params.pop("gates", 3 * n)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 4 or not _is_power_of_two(n):
        raise ValueError("n must be a power of two and at least 4")
    if isinstance(gates, bool) or not isinstance(gates, int) or gates < 0:
        raise ValueError("gates must be a nonnegative integer")

    rng = random.Random(seed)

    # Draw a non-degenerate certificate first.  This is rejection sampling of a
    # known witness, never solution search on a constructed instance.
    while True:
        answer = [rng.randrange(2) for _ in range(n)]
        weight = sum(answer)
        alternating = all(answer[i] == (i & 1) for i in range(n)) or all(
            answer[i] == (1 ^ (i & 1)) for i in range(n)
        )
        if max(1, n // 4) <= weight <= n - max(1, n // 4) and not alternating:
            break

    values = {i: answer[i] for i in range(n)}
    current = list(range(n))
    raw_gates = []
    next_var = n

    target_order = list(range(n))
    rng.shuffle(target_order)
    for step in range(gates):
        if step and step % n == 0:
            rng.shuffle(target_order)
        target_pos = target_order[step % n]
        control_pos = rng.randrange(n - 1)
        if control_pos >= target_pos:
            control_pos += 1
        a = current[control_pos]
        b = current[target_pos]
        z = next_var
        next_var += 1
        # Keeping this circuit linear makes the compact-route count literal:
        # reversing one gate costs one binary XOR.  A random affine constant
        # would require a second GF(2) addition and exceed G9(c) at ``hard``.
        affine = 0
        values[z] = values[a] ^ values[b] ^ affine
        raw_gates.append([step, z, a, b, affine])
        current[target_pos] = z

    variable_count = next_var
    equation_ids = list(range(gates + n))
    rng.shuffle(equation_ids)

    # Random wire identifiers are a carried graph relabelling.
    wire_map = list(range(variable_count))
    rng.shuffle(wire_map)

    gate_records = []
    for step, z, a, b, rhs in raw_gates:
        gate_records.append({
            "step": step,
            "eid": equation_ids[step],
            "z": wire_map[z],
            "a": wire_map[a],
            "b": wire_map[b],
            "rhs": rhs,
            "codes": _forbidden_codes(rhs, rng),
        })

    checks = []
    half = n // 2
    for i in range(n):
        a = current[i]
        b = current[(i + 1) % n]
        c = current[(i + half) % n]
        rhs = values[a] ^ values[b] ^ values[c]
        checks.append({
            "eid": equation_ids[gates + i],
            "a": wire_map[a],
            "b": wire_map[b],
            "c": wire_map[c],
            "rhs": rhs,
            "codes": _forbidden_codes(rhs, rng),
        })
    rng.shuffle(checks)

    rail_order = list(range(variable_count))
    rng.shuffle(rail_order)

    inst = {
        "paper": "arXiv:2105.06349",
        "family": "Lemma-4 claw-free 2-Disjoint Connected Subgraphs",
        "n_inputs": n,
        "n_variables": variable_count,
        "gate_count": gates,
        "inputs": [wire_map[i] for i in range(n)],
        "gates": gate_records,
        "checks": checks,
        "rail_order": [wire_map[i] for i in rail_order],
        "forbidden_induced_subgraph": "K1,3 (the claw)",
        "answer": answer,
    }
    inst["input_checks"] = _derive_input_checks(inst)
    return inst


def _equations(inst):
    rows = []
    for gate in inst["gates"]:
        rows.append((
            gate["eid"],
            [gate["z"], gate["a"], gate["b"]],
            gate["rhs"],
            list(gate["codes"]),
        ))
    for check in inst["checks"]:
        rows.append((
            check["eid"],
            [check["a"], check["b"], check["c"]],
            check["rhs"],
            list(check["codes"]),
        ))
    rows.sort(key=lambda item: item[0])
    return rows


def _derive_input_checks(inst):
    """Compile every CHECK row to an exact affine equation on input bits."""

    width = inst["n_variables"]
    expressions = [None] * width
    for position, wire in enumerate(inst["inputs"]):
        expressions[wire] = (1 << position, 0)
    for gate in sorted(inst["gates"], key=lambda row: row["step"]):
        left = expressions[gate["a"]]
        right = expressions[gate["b"]]
        if left is None or right is None or expressions[gate["z"]] is not None:
            raise ValueError("gate circuit is not topological")
        expressions[gate["z"]] = (
            left[0] ^ right[0],
            left[1] ^ right[1] ^ gate["rhs"],
        )
    compiled = []
    for check in inst["checks"]:
        terms = [expressions[check[field]] for field in ("a", "b", "c")]
        if any(term is None for term in terms):
            raise ValueError("CHECK row uses an undefined wire")
        mask = terms[0][0] ^ terms[1][0] ^ terms[2][0]
        constant = terms[0][1] ^ terms[1][1] ^ terms[2][1]
        compiled.append([check["eid"], mask, check["rhs"] ^ constant])
    compiled.sort()
    return compiled


def _edge(u, v):
    if u == v:
        raise ValueError("base graph may not contain loops")
    return (u, v) if u < v else (v, u)


def _build_base(inst):
    """Construct the paper's base graph B; L(B) is the problem graph."""

    rails = defaultdict(list)
    edges = set()
    clause_edges = set()

    for eid, variables, rhs, codes in _equations(inst):
        if len(set(variables)) != 3 or rhs not in (0, 1):
            raise ValueError(f"malformed ternary equation E{eid}")
        if len(codes) != 4 or len(set(codes)) != 4:
            raise ValueError(f"E{eid} must have four distinct clause slots")
        for slot, code in enumerate(codes):
            if not re.fullmatch(r"[01]{3}", code):
                raise ValueError(f"malformed forbidden code in E{eid}")
            bits = [int(ch) for ch in code]
            if (bits[0] ^ bits[1] ^ bits[2]) == rhs:
                raise ValueError(f"clause slot in E{eid} forbids a satisfying row")
            clause = ("c", eid, slot)
            for position, variable in enumerate(variables):
                # bit 0 is excluded by the positive literal; bit 1 by negation.
                sign = bits[position]
                occurrence = ("o", variable, eid, slot)
                rails[(variable, sign)].append(occurrence)
                ce = _edge(clause, occurrence)
                edges.add(ce)
                clause_edges.add(ce)

    rail_edges = {}
    for variable in range(inst["n_variables"]):
        for sign in (0, 1):
            p = ("p", variable, sign)
            q = ("q", variable, sign)
            occurrences = sorted(rails[(variable, sign)], key=lambda x: (x[2], x[3]))
            chain = [p] + occurrences + [q]
            chain_edges = []
            for left, right in zip(chain, chain[1:]):
                item = _edge(left, right)
                edges.add(item)
                chain_edges.append(item)
            rail_edges[(variable, sign)] = chain_edges

    order = inst["rail_order"]
    if sorted(order) != list(range(inst["n_variables"])):
        raise ValueError("rail_order is not a permutation of the variables")
    connectors = {}
    for left, right in zip(order, order[1:]):
        for left_sign in (0, 1):
            for right_sign in (0, 1):
                item = _edge(
                    ("q", left, left_sign),
                    ("p", right, right_sign),
                )
                edges.add(item)
                connectors[(left, left_sign, right, right_sign)] = item

    first = order[0]
    last = order[-1]
    start_edge = _edge(("p", first, 0), ("p", first, 1))
    finish_edge = _edge(("q", last, 0), ("q", last, 1))
    edges.add(start_edge)
    edges.add(finish_edge)
    return {
        "edges": sorted(edges),
        "rail_edges": rail_edges,
        "connectors": connectors,
        "start": start_edge,
        "finish": finish_edge,
        "z1": {start_edge, finish_edge},
        "z2": clause_edges,
    }


def _extend_inputs(inst, answer):
    values = [-1] * inst["n_variables"]
    known = 0
    for i, wire in enumerate(inst["inputs"]):
        if values[wire] != -1:
            raise ValueError("input wires are not distinct")
        values[wire] = answer[i]
        known += 1
    gates = inst["gates"]
    if any(row["step"] != i for i, row in enumerate(gates)):
        gates = sorted(gates, key=lambda row: row["step"])
    for expected_step, gate in enumerate(gates):
        if gate["step"] != expected_step:
            raise ValueError("gate steps are not 0..gate_count-1")
        z, a, b, rhs = gate["z"], gate["a"], gate["b"], gate["rhs"]
        if values[a] == -1 or values[b] == -1 or values[z] != -1:
            raise ValueError(f"gate step {gate['step']} is not topological")
        values[z] = values[a] ^ values[b] ^ rhs
        known += 1
    if known != inst["n_variables"] or any(value == -1 for value in values):
        raise ValueError("gate circuit does not define every variable")
    return values


def _line_connected(edge_vertices):
    """Connectivity in a line graph, using exact endpoint incidence."""

    if not edge_vertices:
        return False
    incident = defaultdict(list)
    for item in edge_vertices:
        left, right = item
        incident[left].append(item)
        incident[right].append(item)
    start = next(iter(edge_vertices))
    seen = {start}
    queue = deque([start])
    while queue:
        item = queue.popleft()
        for endpoint in item:
            for other in incident[endpoint]:
                if other not in seen:
                    seen.add(other)
                    queue.append(other)
    return len(seen) == len(edge_vertices)


def _graph_witness(inst, values):
    base = _build_base(inst)
    order = inst["rail_order"]
    s1 = {base["start"], base["finish"]}
    s2 = set(base["z2"])

    for variable in order:
        sign = values[variable]
        s1.update(base["rail_edges"][(variable, sign)])
        s2.update(base["rail_edges"][(variable, 1 - sign)])
    for left, right in zip(order, order[1:]):
        left_sign = values[left]
        right_sign = values[right]
        s1.add(base["connectors"][(left, left_sign, right, right_sign)])
        s2.add(base["connectors"][(left, 1 - left_sign, right, 1 - right_sign)])

    if not base["z1"].issubset(s1):
        return False, "constructed S1 omits a terminal"
    if not base["z2"].issubset(s2):
        return False, "constructed S2 omits a terminal"
    if s1 & s2:
        return False, "constructed connected sets are not vertex-disjoint in L(B)"
    if not _line_connected(s1):
        return False, "constructed S1 is disconnected in L(B)"
    if not _line_connected(s2):
        return False, "constructed S2 is disconnected in L(B)"
    return True, "ok"


def render(inst):
    lines = [
        "Find a compressed witness for two disjoint connected subgraphs in a claw-free line graph.",
        "",
        "All graphs here are finite, simple, and undirected. A vertex set is connected",
        "when the subgraph induced by it has a path between every two of its vertices;",
        "two vertex sets are disjoint when they share no vertex. A claw is the four-",
        "vertex star K1,3, and claw-free means having no induced claw.",
        "",
        "All bits below are in GF(2): XOR is addition modulo 2. Wire labels v0,",
        f"..., v{inst['n_variables'] - 1} are identifiers, not an ordering. Every displayed",
        "equation has three distinct wires. Its four listed 3-bit codes are exactly",
        "the falsifying rows, in clause-slot order. A code abc creates the 3-CNF",
        "clause that is false at (a,b,c): use a positive literal for code bit 0",
        "and a negated literal for code bit 1.",
        "",
        "The graph is specified exactly as follows. Make a positive and a negative",
        "rail for every wire, in the displayed RAIL ORDER. On a rail, place that",
        "literal's clause occurrences in increasing (equation id, clause slot) order.",
        "Join consecutive vertices of each rail. Between consecutive wire gadgets",
        "join both rail ends to both next rail starts. Join the two starts of the",
        "first gadget by edge e and the two ends of the last gadget by edge f. For",
        "each clause make one clause vertex and join it to its three occurrence",
        "vertices. Call this base graph B. The problem graph is the line graph L(B):",
        "each edge of B is a vertex, and two such vertices are adjacent exactly when",
        "their B-edges share an endpoint. Thus L(B) is claw-free.",
        "",
        "Terminal set Z1 is {e,f}. Terminal set Z2 is every B-edge from a clause",
        "vertex to an occurrence vertex. A witness bit 0 chooses the positive rail",
        "and bit 1 the negative rail for S1. Concretely, S1 contains e, f, every",
        "B-edge along each chosen rail, and between consecutive gadgets the one",
        "connector B-edge joining the two chosen rails. S2 contains every B-edge",
        "along the complementary rails, their corresponding connector B-edges, and",
        "all Z2 vertices, but not e or f. The gate rows extend the input bits in step",
        "order. The CHECK rows must all hold. Thus the bits specify concrete vertex",
        "sets S1,S2 in L(B); validity means they are disjoint, connected, and contain",
        "Z1,Z2, respectively.",
        "",
        f"Number of input bits: {inst['n_inputs']}",
        "Input wires in answer order:",
        "  " + " ".join(f"v{x}" for x in inst["inputs"]),
        "Rail order:",
        "  " + " ".join(f"v{x}" for x in inst["rail_order"]),
        "",
        "GATE rows (semantic form z = a XOR b XOR rhs):",
    ]
    for gate in sorted(inst["gates"], key=lambda row: row["step"]):
        lines.append(
            f"  step {gate['step']:03d}, E{gate['eid']}: v{gate['z']} = "
            f"v{gate['a']} XOR v{gate['b']} XOR {gate['rhs']}; "
            f"codes={','.join(gate['codes'])}"
        )
    lines.extend([
        "",
        "CHECK rows (the operand order shown is part of the data):",
    ])
    for check in inst["checks"]:
        lines.append(
            f"  E{check['eid']}: v{check['a']} XOR v{check['b']} XOR "
            f"v{check['c']} = {check['rhs']}; codes={','.join(check['codes'])}"
        )

    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])

    lines.extend([
        "",
        f"Return exactly {inst['n_inputs']} bits, one for each input wire in the listed",
        "answer order: the first bit is for the first listed wire. Only 0 and 1 are",
        "allowed; no separators, spaces, repeats, or ellipsis may occur in the string.",
        "",
        "Give your final answer inside <answer></answer> tags, as that bit string.",
        "Example: <answer>0101</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    try:
        tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
        if tagged:
            payload = tagged[-1].strip()
        else:
            fenced = re.findall(r"```(?:json|text)?\s*([01\s,\[\]]+)\s*```", text, re.I)
            if not fenced:
                return None
            payload = fenced[-1].strip()
        payload = re.sub(r"^```(?:json|text)?\s*", "", payload, flags=re.I)
        payload = re.sub(r"\s*```$", "", payload).strip()
        if re.fullmatch(r"[01]+", payload):
            return [int(ch) for ch in payload]
        value = json.loads(payload)
        if not isinstance(value, list):
            return None
        if any(isinstance(bit, bool) or not isinstance(bit, int) or bit not in (0, 1)
               for bit in value):
            return None
        return value
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def verify(inst, answer):
    """Check any encoded rail-choice witness; never consult inst['answer']."""

    n = inst.get("n_inputs")
    if not isinstance(answer, list):
        return False, "malformed answer: expected a binary list or bit string"
    if len(answer) == 0:
        return False, "empty answer: at least four input rail choices are required"
    if len(answer) < n:
        return False, f"too few bits: expected {n}, got {len(answer)}"
    if len(answer) > n:
        return False, f"too many bits: expected {n}, got {len(answer)}"
    for index, bit in enumerate(answer):
        if isinstance(bit, bool) or not isinstance(bit, int) or bit not in (0, 1):
            return False, f"non-binary entry at position {index}: expected 0 or 1"

    try:
        packed = sum(bit << index for index, bit in enumerate(answer))
        for eid, mask, rhs in inst["input_checks"]:
            got = (packed & mask).bit_count() & 1
            if got != rhs:
                return False, f"parity check E{eid} fails: got {got}, expected {rhs}"
        values = _extend_inputs(inst, answer)
        for check in inst["checks"]:
            got = values[check["a"]] ^ values[check["b"]] ^ values[check["c"]]
            if got != check["rhs"]:
                return False, (
                    f"parity check E{check['eid']} fails: got {got}, "
                    f"expected {check['rhs']}"
                )
        return _graph_witness(inst, values)
    except (KeyError, TypeError, ValueError) as exc:
        return False, "malformed instance: " + str(exc)


def random_candidate(inst, rng):
    """Uniform sample from the stated structure-aware binary language."""

    return [rng.randrange(2) for _ in range(inst["n_inputs"])]


def search_space(inst):
    return 1 << inst["n_inputs"]


def enumerate_all(inst):
    n = inst["n_inputs"]
    if n > 16:
        return None
    count = 0
    for packed in range(1 << n):
        candidate = [(packed >> i) & 1 for i in range(n)]
        count += int(verify(inst, candidate)[0])
    return count


def _line_graph(inst):
    base = _build_base(inst)
    edges = base["edges"]
    index = {item: i for i, item in enumerate(edges)}
    incident = defaultdict(list)
    for i, (left, right) in enumerate(edges):
        incident[left].append(i)
        incident[right].append(i)
    adjacency = [set() for _ in edges]
    for bucket in incident.values():
        for i in bucket:
            adjacency[i].update(j for j in bucket if j != i)
    terminal_colour = []
    for item in edges:
        terminal_colour.append(1 if item in base["z1"] else 2 if item in base["z2"] else 0)
    return adjacency, terminal_colour, index


def canonical_key(inst):
    """Normal form for the rail-and-clause representation.

    Wire names, input-coordinate order, equation-record order, and independent
    swaps of a variable's positive/negative rails disappear from the form.  We
    also minimize over reversal of the entire rail, which simultaneously
    reverses the equation/slot order and swaps the two Z1 terminal edges.
    """

    order = inst["rail_order"]
    if sorted(order) != list(range(inst["n_variables"])):
        raise ValueError("rail_order is not a permutation of the variables")
    position = {wire: i for i, wire in enumerate(order)}
    equations = _equations(inst)

    def oriented(reverse):
        clauses = []
        source = reversed(equations) if reverse else equations
        for _eid, variables, _rhs, codes in source:
            rows = list(reversed(codes)) if reverse else codes
            for code in rows:
                clause = []
                for index, wire in enumerate(variables):
                    pos = position[wire]
                    if reverse:
                        pos = len(order) - 1 - pos
                    clause.append([pos, int(code[index])])
                clause.sort()
                clauses.append(clause)

        # Swapping the two rails of one variable is a graph relabelling.  Choose
        # the lexicographically smaller sign column independently at each rail
        # position, then apply those choices to every clause occurrence.
        columns = [[] for _ in order]
        for clause in clauses:
            for pos, bit in clause:
                columns[pos].append(bit)
        toggles = []
        for bits in columns:
            flipped = [bit ^ 1 for bit in bits]
            toggles.append(int(flipped < bits))
        normalized = [
            [[pos, bit ^ toggles[pos]] for pos, bit in clause]
            for clause in clauses
        ]
        return json.dumps(normalized, separators=(",", ":"))

    raw = min(oriented(False), oriented(True))
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def escalate(params):
    """Exhaust circuit mixing first, then lengthen the still-writable witness."""

    out = {key: value for key, value in params.items() if key != "_preset"}
    n = out["n"]
    gates = out.get("gates", 3 * n)
    # The compact route costs 2*n XORs for the cyclic inverse plus one per gate.
    maximum = 300 - 2 * n
    if gates < maximum:
        out["gates"] = min(maximum, gates + max(32, n))
        return out
    # Fixed-length circuit mixing is now exhausted.  Only then increase answer
    # entropy, keeping the compact route exactly at the 300-operation cap.
    if n < 64:
        out.update(n=64, gates=172)
        return out
    if n < 128:
        out.update(n=128, gates=44)
        return out
    # The next supported power of two would need at least 512 XORs merely to
    # apply the three-term cyclic inverse, beyond G9(c)'s operation cap.
    return None


def _linear_rows(inst):
    width = inst["n_variables"]
    rows = []
    for _eid, variables, rhs, _codes in _equations(inst):
        bits = 0
        for variable in variables:
            bits ^= 1 << variable
        rows.append([bits, rhs])
    return rows, width


def _gaussian_reference(inst):
    """Exact scalar-accounted Gaussian elimination over GF(2)."""

    packed_rows, width = _linear_rows(inst)
    rows = [
        [(bits >> column) & 1 for column in range(width)] + [rhs]
        for bits, rhs in packed_rows
    ]
    operations = 0
    pivot_tests = 0
    rank = 0
    pivots = []
    for column in range(width):
        pivot = None
        for row_index in range(rank, len(rows)):
            pivot_tests += 1
            if rows[row_index][column]:
                pivot = row_index
                break
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for row_index in range(rank + 1, len(rows)):
            pivot_tests += 1
            if rows[row_index][column]:
                for j in range(column, width + 1):
                    rows[row_index][j] ^= rows[rank][j]
                    operations += 1
        pivots.append(column)
        rank += 1
        if rank == len(rows):
            break
    if rank != width:
        return None, {"bit_operations": operations, "pivot_tests": pivot_tests}

    solution = [0] * width
    for row_index in range(rank - 1, -1, -1):
        column = pivots[row_index]
        value = rows[row_index][width]
        for j in range(column + 1, width):
            value ^= rows[row_index][j] & solution[j]
            operations += 2
        solution[column] = value
    answer = [solution[wire] for wire in inst["inputs"]]
    return answer, {"bit_operations": operations, "pivot_tests": pivot_tests}


def _compact_solve(inst):
    """Invert the cyclic checks, then reverse the affine XOR circuit."""

    n = inst["n_inputs"]
    successor = {}
    antipode = {}
    rhs_by_anchor = {}
    for check in inst["checks"]:
        successor[check["a"]] = check["b"]
        antipode[check["a"]] = check["c"]
        rhs_by_anchor[check["a"]] = check["rhs"]
    if len(successor) != n:
        return None
    start = next(iter(successor))
    cycle = [start]
    for _ in range(1, n):
        cycle.append(successor[cycle[-1]])
    if successor[cycle[-1]] != start or len(set(cycle)) != n:
        return None
    position = {wire: i for i, wire in enumerate(cycle)}
    half = n // 2
    if any(antipode[wire] != cycle[(position[wire] + half) % n] for wire in cycle):
        return None

    values = {}
    for i, wire in enumerate(cycle):
        values[wire] = (
            rhs_by_anchor[cycle[(i + half - 2) % n]]
            ^ rhs_by_anchor[cycle[(i + n - 2) % n]]
            ^ rhs_by_anchor[cycle[(i + n - 1) % n]]
        )
    for gate in sorted(inst["gates"], key=lambda row: row["step"], reverse=True):
        z, a, b, rhs = gate["z"], gate["a"], gate["b"], gate["rhs"]
        if z not in values or a not in values:
            return None
        value = values[z] ^ values[a]
        if rhs:
            # Only relabelled G8 variants need this carried complementation;
            # make_instance() emits rhs=0 gates, so the shipping route pays one
            # XOR per reversed gate as reported in G9.
            value ^= 1
        values[b] = value
    try:
        return [values[wire] for wire in inst["inputs"]]
    except KeyError:
        return None


def _residual_count(inst, candidate):
    packed = sum(bit << index for index, bit in enumerate(candidate))
    return sum(
        ((packed & mask).bit_count() & 1) != rhs
        for _eid, mask, rhs in inst["input_checks"]
    )


def _expanded_clauses(inst):
    clauses = []
    for _eid, variables, _rhs, codes in _equations(inst):
        for code in codes:
            clauses.append([
                (variables[i], code[i] == "0") for i in range(3)
            ])
    return clauses


def _unit_propagation_candidate(inst):
    assignments = {}
    clauses = _expanded_clauses(inst)
    changed = True
    while changed:
        changed = False
        for clause in clauses:
            satisfied = False
            unknown = []
            for variable, positive in clause:
                if variable not in assignments:
                    unknown.append((variable, positive))
                elif assignments[variable] == int(positive):
                    satisfied = True
                    break
            if satisfied:
                continue
            if not unknown:
                return None
            if len(unknown) == 1:
                variable, positive = unknown[0]
                value = int(positive)
                if variable in assignments and assignments[variable] != value:
                    return None
                if variable not in assignments:
                    assignments[variable] = value
                    changed = True
    if any(wire not in assignments for wire in inst["inputs"]):
        return None
    return [assignments[wire] for wire in inst["inputs"]]


def _attack_candidates(inst, seed):
    n = inst["n_inputs"]
    input_index = {wire: i for i, wire in enumerate(inst["inputs"])}
    positive = [0] * n
    negative = [0] * n
    for clause in _expanded_clauses(inst):
        for variable, is_positive in clause:
            if variable in input_index:
                bucket = positive if is_positive else negative
                bucket[input_index[variable]] += 1
    outlier = [int(negative[i] > positive[i]) for i in range(n)]

    greedy = list(outlier)
    for i in range(n):
        left = list(greedy)
        right = list(greedy)
        left[i] = 0
        right[i] = 1
        greedy[i] = int(_residual_count(inst, right) < _residual_count(inst, left))

    ansatzes = [
        [0] * n,
        [1] * n,
        [i & 1 for i in range(n)],
        [1 ^ (i & 1) for i in range(n)],
    ]

    rng = random.Random(seed ^ 0x210506349)
    restarted = []
    for _ in range(64):
        candidate = [rng.randrange(2) for _ in range(n)]
        for _sweep in range(2):
            improved = False
            order = list(range(n))
            rng.shuffle(order)
            for i in order:
                before = _residual_count(inst, candidate)
                candidate[i] ^= 1
                after = _residual_count(inst, candidate)
                if after < before:
                    improved = True
                else:
                    candidate[i] ^= 1
            if not improved:
                break
        restarted.append(candidate)

    unit = _unit_propagation_candidate(inst)
    return {
        "outlier_literal_frequency": [outlier],
        "greedy_one_pass_coordinate": [greedy],
        "constant_and_alternating_ansatz": ansatzes,
        "unit_propagation_without_branching": [] if unit is None else [unit],
        "random_restart_coordinate_64": restarted,
    }


def _transform_variants(inst, seed):
    rng = random.Random(seed)
    variable_count = inst["n_variables"]

    variable_permutation = list(range(variable_count))
    rng.shuffle(variable_permutation)
    input_permutation = list(range(inst["n_inputs"]))
    rng.shuffle(input_permutation)
    toggles = [rng.randrange(2) for _ in range(variable_count)]

    def relabel(source):
        out = json.loads(json.dumps(source))
        out["inputs"] = [variable_permutation[x] for x in out["inputs"]]
        out["rail_order"] = [variable_permutation[x] for x in out["rail_order"]]
        for gate in out["gates"]:
            for field in ("z", "a", "b"):
                gate[field] = variable_permutation[gate[field]]
        for check in out["checks"]:
            for field in ("a", "b", "c"):
                check[field] = variable_permutation[check[field]]
        out["input_checks"] = _derive_input_checks(out)
        return out

    def reorder_records(source):
        out = json.loads(json.dumps(source))
        rng.shuffle(out["gates"])
        rng.shuffle(out["checks"])
        out["input_checks"] = _derive_input_checks(out)
        return out

    def reorder_inputs(source):
        out = json.loads(json.dumps(source))
        out["inputs"] = [source["inputs"][i] for i in input_permutation]
        out["answer"] = [source["answer"][i] for i in input_permutation]
        out["input_checks"] = _derive_input_checks(out)
        return out

    def complement(source):
        out = json.loads(json.dumps(source))
        out["answer"] = [
            bit ^ toggles[wire] for bit, wire in zip(out["answer"], out["inputs"])
        ]
        for gate in out["gates"]:
            variables = [gate["z"], gate["a"], gate["b"]]
            gate["rhs"] ^= toggles[variables[0]] ^ toggles[variables[1]] ^ toggles[variables[2]]
            gate["codes"] = [
                "".join(str(int(code[i]) ^ toggles[variables[i]]) for i in range(3))
                for code in gate["codes"]
            ]
        for check in out["checks"]:
            variables = [check["a"], check["b"], check["c"]]
            check["rhs"] ^= toggles[variables[0]] ^ toggles[variables[1]] ^ toggles[variables[2]]
            check["codes"] = [
                "".join(str(int(code[i]) ^ toggles[variables[i]]) for i in range(3))
                for code in check["codes"]
            ]
        out["input_checks"] = _derive_input_checks(out)
        return out

    def reverse_rail(source):
        out = json.loads(json.dumps(source))
        equation_count = out["gate_count"] + out["n_inputs"]
        out["rail_order"].reverse()
        for row in out["gates"] + out["checks"]:
            row["eid"] = equation_count - 1 - row["eid"]
            row["codes"].reverse()
        out["input_checks"] = _derive_input_checks(out)
        return out

    transformations = [
        relabel,
        reorder_records,
        reorder_inputs,
        complement,
        reverse_rail,
    ]
    variants = []
    # Exercise every non-empty composition of the four representation-preserving
    # maps.  This includes all single maps and every composition rather than
    # relying on one hand-picked combined case.
    for mask in range(1, 1 << len(transformations)):
        out = inst
        for index, transform in enumerate(transformations):
            if mask & (1 << index):
                out = transform(out)
        variants.append(out)
    return variants


def _is_claw_free(adjacency):
    for center, neighbors in enumerate(adjacency):
        row = list(neighbors)
        for i in range(len(row)):
            for j in range(i + 1, len(row)):
                if row[j] in adjacency[row[i]]:
                    continue
                for k in range(j + 1, len(row)):
                    if row[k] not in adjacency[row[i]] and row[k] not in adjacency[row[j]]:
                        return False
    return True


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest():
    report = {}
    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
            compact = _compact_solve(inst)
            if compact is None or not verify(inst, compact)[0]:
                failures.append([preset, seed, "compact cyclic inverse failed"])
            if preset in ("demo", "hard") and seed == 0:
                adjacency, _colours, _index = _line_graph(inst)
                if not _is_claw_free(adjacency):
                    failures.append([preset, seed, "constructed line graph contains a claw"])
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
        "construction_checks": "expanded Lemma-4 witness and executable claw-free check",
    }

    inst = make_instance(seed=19, **shipping_params)
    answer = inst["answer"]
    zero = next(i for i, bit in enumerate(answer) if bit == 0)
    one = next(i for i, bit in enumerate(answer) if bit == 1)
    swapped = list(answer)
    swapped[zero], swapped[one] = swapped[one], swapped[zero]
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": answer + [answer[0]],
        "empty": [],
        "out_of_range": answer[:3] + [2] + answer[4:],
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = [item["reason"] for item in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in rejected.values()) and len(set(reasons)) == 5,
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    bitstring = "".join(map(str, answer))
    response = (
        "The cyclic checks determine the final wires; reversing the gates gives:\n"
        "```text\n<answer>" + bitstring + "</answer>\n```\n"
        "I also checked both connected sets."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x210506349)
    guess_total = 200_000
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_elapsed = time.perf_counter() - start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "exact_candidate_space": search_space(inst),
        "candidate_space_bits": inst["n_inputs"],
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attack_names = [
        "outlier_literal_frequency",
        "greedy_one_pass_coordinate",
        "constant_and_alternating_ansatz",
        "unit_propagation_without_branching",
        "random_restart_coordinate_64",
    ]
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_operations = 0
    reference_pivot_tests = 0
    compact_successes = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping_params)
        start = time.perf_counter()
        candidates = _attack_candidates(trial, seed)
        construction_time = time.perf_counter() - start
        for name in attack_names:
            start = time.perf_counter()
            won = any(verify(trial, candidate)[0] for candidate in candidates[name])
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(won)
        attack_seconds["random_restart_coordinate_64"] += construction_time

        start = time.perf_counter()
        recovered, counts = _gaussian_reference(trial)
        reference_seconds += time.perf_counter() - start
        reference_operations += counts["bit_operations"]
        reference_pivot_tests += counts["pivot_tests"]
        reference_successes += int(recovered is not None and verify(trial, recovered)[0])
        compact = _compact_solve(trial)
        compact_successes += int(compact is not None and verify(trial, compact)[0])

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name] / 8, 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "exact Gaussian elimination over GF(2)",
        "complexity": "O(V^3) scalar bit operations",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": (reference_operations + reference_pivot_tests) // 8,
        "xor_operations": reference_operations // 8,
        "pivot_tests": reference_pivot_tests // 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_attacks_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "three-shift cyclic inverse followed by gate reversal",
            "solves": f"{compact_successes}/8",
            "operations": 2 * inst["n_inputs"] + inst["gate_count"],
        },
    }

    demo_count = enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline_cost"] = {
        "pass": (
            guess_fraction < 1e-6
            and demo_count == 1
            and all_attacks_failed
            and reference_successes == 8
        ),
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density": guess_fraction,
        "exact_solution_count_by_invertibility": 1,
        "exact_solution_density_by_invertibility": 1.0 / search_space(inst),
        "exact_density": f"1/2^{inst['n_inputs']} (invertible affine system)",
        "demo_exact_solution_count": demo_count,
        "baseline_attack_wall_clock_sec": round(
            attack_seconds["random_restart_coordinate_64"] / 8, 6
        ),
        "baseline_attack_restarts": 64,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
    }

    doubled_params = {"n": 2 * shipping_params["n"], "gates": 2 * shipping_params["gates"]}
    start = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    scores = [params["n"] + params["gates"] for params in DIFFICULTY.values()]
    report["G7_scales"] = {
        "pass": (
            doubled_ok
            and doubled["n_inputs"] == 2 * inst["n_inputs"]
            and search_space(doubled) == search_space(inst) ** 2
            and scores == sorted(scores)
            and len(set(scores)) == 4
        ),
        "shipping_n_inputs": inst["n_inputs"],
        "shipping_variables": inst["n_variables"],
        "doubled_n_inputs": doubled["n_inputs"],
        "doubled_variables": doubled["n_variables"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_why,
        "candidate_space_bits_shipping": inst["n_inputs"],
        "candidate_space_bits_doubled": doubled["n_inputs"],
    }

    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping_params)
        key = canonical_key(original)
        for transformed in _transform_variants(original, seed ^ 0x5A5A):
            invariant_count += int(key == canonical_key(transformed))
            real_transform_count += int(verify(transformed, transformed["answer"])[0])
        unrelated_keys.append(key)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": (
            invariant_count == 620
            and real_transform_count == 620
            and distinct_count == 20
        ),
        "invariant_relabellings": invariant_count,
        "invariance_attempts": 620,
        "real_transformations_verified": real_transform_count,
        "real_transformation_attempts": 620,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "arbitrary wire relabelling",
            "gate/check record reordering",
            "input-list reordering with carried answer coordinates",
            "independent literal complementation with carried witness",
            "whole-rail reversal with carried equation and clause-slot order",
            "all 26 non-singleton compositions of these five maps",
        ],
    }

    encoded = json.dumps(inst["answer"])
    answer_chars = len(encoded)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    intended_operations = 2 * inst["n_inputs"] + inst["gate_count"]
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    hinted_rate = (
        hinted["solved"] / hinted["attempts"]
        if hinted["attempts"] and hinted["solved"] is not None
        else None
    )
    placebo_rate = (
        placebo["solved"] / placebo["attempts"]
        if placebo["attempts"] and placebo["solved"] is not None
        else None
    )
    delta = (
        hinted_rate - placebo_rate
        if hinted_rate is not None and placebo_rate is not None
        else None
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] >= answer_tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": delta,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [
        value
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    ]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
