"""Inverse generator for bounded-hop IS reconfiguration (arXiv:2407.11768).

The outer problem is exactly the bounded-length k-Jump problem in Section 5.
The E3-SAT input to the paper's reduction encodes inversion of a small nonlinear
Boolean mixing circuit.  A preimage is sampled first; its circuit output is then
made public.  An answer compactly determines a full reconfiguration path, which
the verifier expands and replays without consulting the planted answer.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections import Counter


DIFFICULTY = {
    "demo": {"n": 8, "rounds": 3, "k": 3},
    "easy": {"n": 48, "rounds": 8, "k": 3},
    "medium": {"n": 64, "rounds": 10, "k": 3},
    "hard": {"n": 80, "rounds": 12, "k": 3},
}
SHIPPING_DIFFICULTY = "easy"


NOTES = r"""
Section 2 (Definitions 1 and 2) fixes the exact rule: one occupied vertex is
replaced by one empty vertex at graph distance at most k, and every token set is
independent.  Section 5.1 fixes the clause and variable gadgets reproduced by
render().  Lemma 12 in Section 5.2 proves that the resulting chordal,
diameter-(2k+1) instance has a path of at most 2(m+n) moves iff its E3-SAT
formula is satisfiable; Lemma 14 gives the canonical path expanded here.

The easy regime matters.  Theorem 1 (Section 3) makes unbounded reachability for
all k >= 3 equivalent to Token Jumping, and the introduction/Tables 1--2 record
polynomial algorithms on chordal/even-hole-free graphs for reachability and for
the Token-Jumping shortest problem.  This generator therefore uses the exact
2(m+n) bound in the k >= 3 Section 5 reduction class.  It asks for a witness,
not an optimum and not a claim that no path exists.

An earlier planted NAE-3-SAT version was rejected by G6: min-conflicts solved
8/8 medium instances.  The shipped construction instead samples a uniformly
random preimage before choosing circuit taps, evaluates a nonlinear multi-round
mixing circuit, and exposes only its output.  Formula-variable names, clause
order, and literal order carry no planted-position convention.  The outlier
attack guesses input bits from literal-frequency imbalance, the greedy attack
commits bits by immediate output distance, and random restart performs bounded
single-bit min-conflicts.  These cheap attacks are measured in selftest(); full
SAT/CDCL, algebraic attacks, and cryptanalysis are caveats, not claimed tests.
""".strip()


# ---------------------------------------------------------------------------
# Circuit and exact-3-CNF construction

def _xor_clauses(a, b, y):
    """Clauses for y = a XOR b, in fixed order."""
    return [[-a, -b, -y], [-a, b, y], [a, -b, y], [a, b, -y]]


def _and_clauses(a, b, y, pad):
    """Exact-three-literal clauses for y = a AND b.

    The two binary implications are each duplicated with pad and -pad.  The pad
    remains free; either value enforces the same binary clause.
    """
    return [[-a, -b, y],
            [a, -y, pad], [a, -y, -pad],
            [b, -y, pad], [b, -y, -pad]]


def _force_clauses(literal, pad_a, pad_b):
    """Four exact-three-literal clauses equivalent to a unit literal."""
    return [[literal, pad_a, pad_b], [literal, pad_a, -pad_b],
            [literal, -pad_a, pad_b], [literal, -pad_a, -pad_b]]


def _literal_value(literal, values):
    value = int(values[abs(literal) - 1])
    return value if literal > 0 else 1 - value


def _evaluate_circuit(inst, preimage, keep_wires=False):
    """Evaluate logical wires; wire IDs are one-based."""
    n = inst["n"]
    if len(preimage) != n:
        raise ValueError("wrong preimage length")
    values = [None] + [int(bit) for bit in preimage] + [0, 0]
    next_wire = n + 3
    for branch_offsets in inst["branches"]:
        state = list(range(1, n + 1))
        for a_off, b_off, c_off in branch_offsets:
            old = state
            state = []
            for i in range(n):
                av = values[old[(i + a_off) % n]] & values[old[(i + b_off) % n]]
                values.append(av)
                next_wire += 1
                xv = values[old[i]] ^ values[old[(i + c_off) % n]]
                values.append(xv)
                next_wire += 1
                values.append(av ^ xv)
                state.append(next_wire)
                next_wire += 1
    output = "".join(str(values[wire]) for wire in inst["output_wires"])
    return (output, values) if keep_wires else output


def make_instance(n, seed=0, **params) -> dict:
    """Sample a preimage first, then build its bounded-path graph instance."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 8:
        raise ValueError("n must be an integer at least 8")
    rounds = params.pop("rounds", 6)
    k = params.pop("k", 3)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 1:
        raise ValueError("rounds must be a positive integer")
    if isinstance(k, bool) or not isinstance(k, int) or k < 3:
        raise ValueError("k must be an integer at least 3")

    rng = random.Random(seed)

    # G: the only submitted witness is sampled before taps, output, or clauses.
    preimage = "".join(str(rng.randrange(2)) for _ in range(n))
    branches = []
    for _branch in range(2):
        offsets = []
        for _ in range(rounds):
            c_off = rng.choice([offset for offset in range(1, n)
                                if math.gcd(offset, n) == 1])
            a_off, b_off = rng.sample([offset for offset in range(1, n)
                                       if offset != c_off], 2)
            offsets.append((a_off, b_off, c_off))
        branches.append(offsets)

    pad_a, pad_b = n + 1, n + 2
    next_wire = n + 3
    gates = []
    clauses = []
    output_wires = []
    for branch_offsets in branches:
        state = list(range(1, n + 1))
        for a_off, b_off, c_off in branch_offsets:
            old = state
            state = []
            for i in range(n):
                a_wire = next_wire
                next_wire += 1
                gates.append(["AND", old[(i + a_off) % n],
                              old[(i + b_off) % n], a_wire])
                clauses.extend(_and_clauses(gates[-1][1], gates[-1][2], a_wire, pad_a))

                x_wire = next_wire
                next_wire += 1
                gates.append(["XOR", old[i], old[(i + c_off) % n], x_wire])
                clauses.extend(_xor_clauses(gates[-1][1], gates[-1][2], x_wire))

                y_wire = next_wire
                next_wire += 1
                gates.append(["XOR", a_wire, x_wire, y_wire])
                clauses.extend(_xor_clauses(a_wire, x_wire, y_wire))
                state.append(y_wire)
        output_wires.extend(state)

    formula_n = next_wire - 1
    logical = {
        "n": n, "branches": branches, "formula_n": formula_n,
        "output_wires": output_wires,
    }
    target = _evaluate_circuit(logical, preimage)
    for wire, bit in zip(output_wires, target):
        literal = wire if bit == "1" else -wire
        clauses.extend(_force_clauses(literal, pad_a, pad_b))

    # The indirection supports genuine graph relabelling tests in G8.  Ordinary
    # generated instances use the identity map and no polarity flips.
    wire_to_var = list(range(formula_n + 1))
    wire_flip = [0] * (formula_n + 1)
    m = len(clauses)
    inst = {
        "family": "bounded_k_jump_section5_circuit",
        "n": n,
        "rounds": rounds,
        "k": k,
        "branches": [[list(x) for x in branch] for branch in branches],
        "target": target,
        "gates": gates,
        "output_wires": output_wires,
        "formula_n": formula_n,
        "m": m,
        "clauses": clauses,
        "wire_to_var": wire_to_var,
        "wire_flip": wire_flip,
        "move_limit": 2 * (m + formula_n),
        "logical_vertex_count": m * (2 * k + 3) + formula_n * (k + 2),
        "answer": {"preimage": preimage},
    }
    return inst


def render(inst) -> str:
    """Render all instance data and deterministic graph/CNF construction rules."""
    n, r, k = inst["n"], inst["rounds"], inst["k"]
    offsets = "\n".join(
        f"B{branch}R{j}: {a} {b} {c}"
        for branch, branch_offsets in enumerate(inst["branches"])
        for j, (a, b, c) in enumerate(branch_offsets))
    return f"""Bounded-hop independent-set reconfiguration witness

First invert these two fully specified Boolean mixing branches.  Their shared
secret input is S[0],...,S[{n - 1}].  Each branch starts from that input.  In each
round use the three integer offsets a,b,c listed below and simultaneously
compute, for every i=0,...,{n - 1} (all subscripts modulo {n}):

    A[i] = S[i+a] AND S[i+b]
    X[i] = S[i] XOR S[i+c]
    S_new[i] = A[i] XOR X[i]

Read S[0]...S[{n - 1}] after the final round of branch 0 and then after the final
round of branch 1, and concatenate them.  The required
{len(inst['target'])}-bit output is:
{inst['target']}

Branch/round offsets (a b c):
{offsets}

Here is the exact E3-SAT formula and graph implied by that circuit.  This also
defines the reconfiguration witness encoded by your preimage.  Formula variable
IDs are 1-based.  Inputs use IDs 1,...,{n}.  Two free padding variables are
z={n + 1} and w={n + 2}.  Then, in increasing branch, round, and i order,
allocate three fresh IDs A[i], X[i], S_new[i], in that order.  Each branch begins
again with input IDs 1,...,{n}.  A signed integer q denotes
variable q when positive and NOT variable |q| when negative.  Append clauses in
the order shown by these macros, preserving literal order:

AND(a,b,y): (-a,-b,+y), (+a,-y,+z), (+a,-y,-z),
            (+b,-y,+z), (+b,-y,-z)
XOR(a,b,y): (-a,-b,-y), (-a,+b,+y), (+a,-b,+y), (+a,+b,-y)
FORCE(l):   (+l,+z,+w), (+l,+z,-w), (+l,-z,+w), (+l,-z,-w)

For each circuit assignment append AND then XOR then XOR macros in the same
order as the three equations.  Finally append FORCE(output-wire) when its target
bit is 1 and FORCE(-output-wire) when it is 0, from output index 0 upward.  This
creates exactly {inst['formula_n']} variables and {inst['m']} clauses, each with
exactly three distinct literals.

Construct the paper's graph as follows.  Clauses are indexed 0,...,{inst['m'] - 1}
in append order and literal positions are 0,1,2.  For clause i create a path
v(i,0),...,v(i,{2 * k}).  Its gates are g(i,1)=v(i,{k}) and new vertices g(i,0),
g(i,2).  Join g(i,0) and g(i,2) to v(i,{k - 1}) and v(i,{k + 1}), and make all
{3 * inst['m']} gates over all clauses one clique.  For formula variable j create
a path u(j,0),...,u(j,{k - 1}) and vertices s(j,0),s(j,1), each joined to u(j,0).
Write t(j,0)=u(j,0), t(j,1)=u(j,{k - 1}).  A positive literal +j in position p
joins g(i,p) to s(j,0) and t(j,0); a negative literal -j joins it to s(j,1) and
t(j,0).  There are no other edges.

Initially every v(i,0), s(j,0), and s(j,1) has a token.  The target consists of
every v(i,{2 * k}), t(j,0), and t(j,1).  A token set is independent iff no two
occupied vertices share an edge.  One {k}-Jump replaces exactly one occupied
vertex by one empty vertex at shortest-path distance at most {k}, and the new set
must be independent.

Your preimage encodes exactly {inst['move_limit']} moves.  Evaluate every circuit
wire, set z=w=0, and choose the leftmost true literal (position 0, then 1, then
2) in each clause.  First, in increasing variable-ID order, move s(j,0) to
t(j,1) for a true variable and s(j,1) to t(j,1) for a false variable.  Next, in
increasing clause order, move v(i,0) to the chosen gate and that gate to
v(i,{2 * k}).  Finally move the remaining s vertex of each variable to t(j,0),
again in increasing variable order.  The checker reconstructs and replays every
move; it never compares your preimage with a planted one.

All ranges are inclusive, strings are in increasing index order, and repeats are
not allowed where the construction says "fresh".  Any {n}-bit preimage producing
the target is accepted.

Give your final answer inside <answer></answer> tags, as one JSON object with the
single key "preimage", whose value is exactly {n} binary characters.
Example of the required shape: <answer>{{"preimage":"{'0' * n}"}}</answer>
Output nothing else inside the tags."""


def parse_answer(text) -> object | None:
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    for body in reversed(blocks):
        cleaned = body.strip()
        fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned,
                             flags=re.IGNORECASE | re.DOTALL)
        if fence:
            cleaned = fence.group(1).strip()
        try:
            value = json.loads(cleaned)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            return value
    return None


# ---------------------------------------------------------------------------
# Exact graph reconstruction and sequence replay

def _cv(i, h):
    return ("c", i, "v", h)


def _gate(i, p, k):
    return _cv(i, k) if p == 1 else ("c", i, "g", p)


def _u(j, h):
    return ("x", j, "u", h)


def _s(j, b):
    return ("x", j, "s", b)


def _gate_info(vertex, k):
    if vertex[0] != "c":
        return None
    if vertex[2] == "g":
        return vertex[1], vertex[3]
    if vertex[2] == "v" and vertex[3] == k:
        return vertex[1], 1
    return None


def _adjacent(inst, a, b):
    if a == b:
        return False
    k = inst["k"]
    ga, gb = _gate_info(a, k), _gate_info(b, k)
    if ga is not None and gb is not None:
        return True
    if a[0] == b[0] == "c" and a[1] == b[1]:
        if a[2] == b[2] == "v":
            return abs(a[3] - b[3]) == 1
        if ga is not None and b[2] == "v":
            return ga[1] in (0, 2) and b[3] in (k - 1, k + 1)
        if gb is not None and a[2] == "v":
            return gb[1] in (0, 2) and a[3] in (k - 1, k + 1)
    if a[0] == b[0] == "x" and a[1] == b[1]:
        if a[2] == b[2] == "u":
            return abs(a[3] - b[3]) == 1
        if a[2] == "s" and b[2] == "u":
            return b[3] == 0
        if b[2] == "s" and a[2] == "u":
            return a[3] == 0
    if ga is not None and b[0] == "x":
        i, p = ga
        literal = inst["clauses"][i][p]
        j, neg = abs(literal) - 1, int(literal < 0)
        return b == _u(j, 0) or b == _s(j, neg)
    if gb is not None and a[0] == "x":
        return _adjacent(inst, b, a)
    return False


def _initial_state(inst):
    return ({_cv(i, 0) for i in range(inst["m"])} |
            {_s(j, b) for j in range(inst["formula_n"]) for b in (0, 1)})


def _target_state(inst):
    k = inst["k"]
    return ({_cv(i, 2 * k) for i in range(inst["m"])} |
            {_u(j, h) for j in range(inst["formula_n"]) for h in (0, k - 1)})


def _move_route(inst, source, destination):
    k = inst["k"]
    if source[0] == "x" and source[2] == "s" and destination == _u(source[1], k - 1):
        return [source] + [_u(source[1], h) for h in range(k)]
    if source[0] == "x" and source[2] == "s" and destination == _u(source[1], 0):
        return [source, destination]
    if source[0] == "c" and source[2] == "v" and source[3] == 0:
        info = _gate_info(destination, k)
        if info is not None and info[0] == source[1]:
            i, p = info
            return ([_cv(i, h) for h in range(k + 1)] if p == 1 else
                    [_cv(i, h) for h in range(k)] + [destination])
    info = _gate_info(source, k)
    if info is not None and destination == _cv(info[0], 2 * k):
        i, p = info
        return ([_cv(i, h) for h in range(k, 2 * k + 1)] if p == 1 else
                [source] + [_cv(i, h) for h in range(k + 1, 2 * k + 1)])
    return None


def _has_occupied_neighbor(inst, vertex, state, active_gate):
    """Exact local neighbor query without materializing the enormous gate clique."""
    k = inst["k"]
    info = _gate_info(vertex, k)
    candidates = []
    if info is not None:
        if active_gate is not None and active_gate != vertex and active_gate in state:
            return True
        i, p = info
        candidates.extend((_cv(i, k - 1), _cv(i, k + 1)))
        literal = inst["clauses"][i][p]
        j, neg = abs(literal) - 1, int(literal < 0)
        candidates.extend((_u(j, 0), _s(j, neg)))
    elif vertex[0] == "c":
        i, h = vertex[1], vertex[3]
        if h > 0:
            candidates.append(_cv(i, h - 1))
        if h < 2 * k:
            candidates.append(_cv(i, h + 1))
        if h in (k - 1, k + 1):
            candidates.extend(_gate(i, p, k) for p in (0, 1, 2))
    elif vertex[2] == "u":
        j, h = vertex[1], vertex[3]
        if h > 0:
            candidates.append(_u(j, h - 1))
        if h < k - 1:
            candidates.append(_u(j, h + 1))
        if h == 0:
            candidates.extend((_s(j, 0), _s(j, 1)))
            if active_gate is not None and _adjacent(inst, vertex, active_gate):
                return True
    else:  # s(j,b)
        candidates.append(_u(vertex[1], 0))
        if active_gate is not None and _adjacent(inst, vertex, active_gate):
            return True
    return any(candidate in state and candidate != vertex for candidate in candidates)


def _formula_assignment(inst, logical_values):
    values = [0] * inst["formula_n"]
    for wire in range(1, inst["formula_n"] + 1):
        variable = inst["wire_to_var"][wire]
        values[variable - 1] = logical_values[wire] ^ inst["wire_flip"][wire]
    return values


def verify(inst, answer) -> tuple[bool, str]:
    """Accept any valid preimage by expanding and replaying its canonical path."""
    # Deliberately never inspect inst["answer"].
    if answer is None:
        return False, "answer is absent"
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if not answer:
        return False, "answer is an empty object"
    if set(answer) != {"preimage"}:
        return False, "answer must contain exactly the preimage key"
    preimage = answer["preimage"]
    if not isinstance(preimage, str):
        return False, "preimage must be a binary string"
    if len(preimage) < inst["n"]:
        return False, f"preimage is too short: {len(preimage)} < {inst['n']}"
    if len(preimage) > inst["n"]:
        return False, f"preimage is too long: {len(preimage)} > {inst['n']}"
    if any(bit not in "01" for bit in preimage):
        return False, "preimage contains a non-binary character"

    output, logical_values = _evaluate_circuit(inst, preimage, keep_wires=True)
    if output != inst["target"]:
        return False, "preimage produces the wrong circuit output"
    assignment = _formula_assignment(inst, logical_values)
    choices = []
    for i, clause in enumerate(inst["clauses"]):
        true_positions = [p for p, literal in enumerate(clause)
                          if _literal_value(literal, assignment)]
        if not true_positions:
            return False, f"internal circuit assignment falsifies clause C{i}"
        choices.append(true_positions[0])

    state = _initial_state(inst)
    active_gate = None
    moves = []
    for j, bit in enumerate(assignment):
        moves.append((_s(j, 0 if bit else 1), _u(j, inst["k"] - 1)))
    for i, choice in enumerate(choices):
        gate = _gate(i, choice, inst["k"])
        moves.extend(((_cv(i, 0), gate), (gate, _cv(i, 2 * inst["k"]))))
    for j, bit in enumerate(assignment):
        moves.append((_s(j, 1 if bit else 0), _u(j, 0)))
    if len(moves) != inst["move_limit"]:
        return False, "internal expansion produced the wrong move count"

    for move_number, (source, destination) in enumerate(moves, 1):
        if source not in state:
            return False, f"move {move_number}: source is unoccupied"
        if destination in state:
            return False, f"move {move_number}: destination is occupied"
        route = _move_route(inst, source, destination)
        if (route is None or route[0] != source or route[-1] != destination or
                len(route) - 1 > inst["k"] or
                any(not _adjacent(inst, a, b) for a, b in zip(route, route[1:]))):
            return False, f"move {move_number}: endpoints are farther than k"
        state.remove(source)
        if _has_occupied_neighbor(inst, destination, state,
                                  None if source == active_gate else active_gate):
            state.add(source)
            return False, f"move {move_number}: resulting set is not independent"
        state.add(destination)
        if source == active_gate:
            active_gate = None
        if _gate_info(destination, inst["k"]) is not None:
            active_gate = destination
    if state != _target_state(inst):
        return False, "expanded sequence does not end at the target set"
    return True, "ok"


# ---------------------------------------------------------------------------
# Candidate distribution, counting, and canonicalization

def random_candidate(inst, rng) -> object:
    """Uniformly sample the only free structural choice: the n-bit preimage."""
    return {"preimage": "".join(str(rng.randrange(2)) for _ in range(inst["n"]))}


def search_space(inst) -> int | None:
    return 1 << inst["n"]


def enumerate_all(inst) -> int | None:
    """Count preimages exactly with bit-parallel exhaustive evaluation."""
    n = inst["n"]
    if n > 22:
        return None
    count = 1 << n
    universe = (1 << count) - 1
    state = []
    for j in range(n):
        block = 1 << j
        period_mask = (1 << (2 * block)) - 1
        repeated = universe // period_mask
        state.append((repeated * ((1 << block) - 1)) << block)
    outputs = []
    inputs = list(state)
    for branch_offsets in inst["branches"]:
        state = list(inputs)
        for a_off, b_off, c_off in branch_offsets:
            old = state
            state = [((old[i] ^ old[(i + c_off) % n]) ^
                      (old[(i + a_off) % n] & old[(i + b_off) % n]))
                     for i in range(n)]
        outputs.extend(state)
    survivors = universe
    for values, bit in zip(outputs, inst["target"]):
        survivors &= values if bit == "1" else universe ^ values
    return survivors.bit_count()


def _wl_invariant(n, clauses):
    """Stable color-refinement invariant of the signed incidence graph."""
    count = 3 * n + len(clauses)
    neighbors = [[] for _ in range(count)]
    edges = []

    def add(a, b):
        neighbors[a].append(b)
        neighbors[b].append(a)
        edges.append((a, b))

    for j in range(n):
        add(j, n + 2 * j)
        add(j, n + 2 * j + 1)
    for i, clause in enumerate(clauses):
        cnode = 3 * n + i
        for literal in clause:
            j = abs(literal) - 1
            add(cnode, n + 2 * j + int(literal < 0))
    colors = [0] * n + [1] * (2 * n) + [2] * len(clauses)
    for _ in range(count + 1):
        signatures = [(colors[v], tuple(sorted(colors[w] for w in neighbors[v])))
                      for v in range(count)]
        palette = {sig: c for c, sig in enumerate(sorted(set(signatures)))}
        new_colors = [palette[sig] for sig in signatures]
        old_classes = len(set(colors))
        colors = new_colors
        if len(set(colors)) == old_classes:
            break
    hist = sorted(Counter(colors).items())
    quotient = Counter(tuple(sorted((colors[a], colors[b]))) for a, b in edges)
    return {"hist": hist, "edges": sorted((list(key), value)
                                            for key, value in quotient.items())}


def canonical_key(inst) -> str:
    """Structural invariant; never includes the seed, answer, or rendered text.

    Exact signed-formula isomorphism is intractable in general, so this uses
    stable color refinement of the signed incidence graph.  It is invariant
    under all tested reduction-graph relabellings but may conservatively collide.
    """
    payload = {
        "family": "section5-reduction", "k": inst["k"],
        "move_limit": inst["move_limit"],
        "wl": _wl_invariant(inst["formula_n"], inst["clauses"]),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params) -> dict | None:
    if "n" not in params:
        return None
    result = dict(params)
    result["n"] = int(params["n"]) + max(16, int(params["n"]) // 2)
    result["rounds"] = int(params.get("rounds", 6)) + 2
    return result


# ---------------------------------------------------------------------------
# Gate implementations

def _transform_for_g8(inst, rng):
    """Compose formula-variable renaming/polarity and all input reorderings."""
    total = inst["formula_n"]
    permutation = list(range(1, total + 1))
    rng.shuffle(permutation)  # old displayed variable v -> permutation[v-1]
    flips = [rng.randrange(2) for _ in range(total + 1)]
    records = []
    for clause in inst["clauses"]:
        changed = []
        for literal in clause:
            old = abs(literal)
            neg = int(literal < 0) ^ flips[old]
            new = permutation[old - 1]
            changed.append(-new if neg else new)
        rng.shuffle(changed)
        records.append(changed)
    rng.shuffle(records)

    changed = {key: value for key, value in inst.items()
               if key not in ("answer", "clauses", "wire_to_var", "wire_flip")}
    changed["clauses"] = records
    changed["wire_to_var"] = [0] * (total + 1)
    changed["wire_flip"] = [0] * (total + 1)
    for wire in range(1, total + 1):
        old_var = inst["wire_to_var"][wire]
        changed["wire_to_var"][wire] = permutation[old_var - 1]
        changed["wire_flip"][wire] = inst["wire_flip"][wire] ^ flips[old_var]
    changed["answer"] = dict(inst["answer"])
    return changed


def _outlier_attack(inst):
    positive = [0] * inst["formula_n"]
    negative = [0] * inst["formula_n"]
    for clause in inst["clauses"]:
        for literal in clause:
            (positive if literal > 0 else negative)[abs(literal) - 1] += 1
    # Only primary input variables are guessed; degree/sign imbalance is the
    # cheapest per-element statistic visible in the generated formula.
    bits = "".join("1" if positive[j] > negative[j] else "0"
                   for j in range(inst["n"]))
    return {"preimage": bits}


def _greedy_attack(inst):
    bits = [0] * inst["n"]
    for j in range(inst["n"]):
        distances = []
        for value in (0, 1):
            bits[j] = value
            output = _evaluate_circuit(inst, "".join(map(str, bits)))
            distances.append(sum(a != b for a, b in zip(output, inst["target"])))
        bits[j] = 0 if distances[0] <= distances[1] else 1
    return {"preimage": "".join(map(str, bits))}


def _restart_attack(inst, rng):
    n = inst["n"]
    best = None
    for _ in range(4):
        bits = [rng.randrange(2) for _ in range(n)]
        for _step in range(8 * n):
            output = _evaluate_circuit(inst, "".join(map(str, bits)))
            distance = sum(a != b for a, b in zip(output, inst["target"]))
            if distance == 0:
                return {"preimage": "".join(map(str, bits))}
            scored = []
            for j in range(n):
                bits[j] ^= 1
                trial = _evaluate_circuit(inst, "".join(map(str, bits)))
                bits[j] ^= 1
                scored.append((sum(a != b for a, b in zip(trial, inst["target"])),
                               rng.random(), j))
            next_score, _, chosen = min(scored)
            # Permit occasional uphill steps; this is still a bounded cheap
            # min-conflicts/restart attack rather than exhaustive search.
            if next_score <= distance or rng.random() < 0.08:
                bits[chosen] ^= 1
        best = {"preimage": "".join(map(str, bits))}
    return best


def selftest() -> dict:
    """Run G1--G8 and return a JSON-serializable measured report."""
    report = {}

    failures = []
    checked = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 101):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            checked += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": why})
    report["G1_planted_verifies"] = {
        "pass": not failures, "verified": checked, "failures": failures}

    params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **params)
    base = inst["answer"]
    text = base["preimage"]
    corruptions = {
        "drop_one": {"preimage": text[:-1]},
        "swap_type": {"preimage": list(text)},
        "duplicate_one": {"preimage": text + text[-1]},
        "empty": {},
        "out_of_range": {"preimage": "2" + text[1:]},
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": why}
    reasons = [case["reason"] for case in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values()) and
                len(set(reasons)) == len(reasons),
        "cases": cases, "distinct_reasons": len(set(reasons))}

    wire = json.dumps(base, separators=(",", ":"))
    response = ("I inverted the circuit and encoded the path.\n```json\n"
                f"<answer>{wire}</answer>\n```\nThat is my final witness.")
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == base and parse_answer("garbage") is None,
        "parsed_equal": parsed == base,
        "garbage_returns_none": parse_answer("garbage") is None}

    trials = 200_000
    hits = 0
    guess_rng = random.Random(20240711768)
    for _ in range(trials):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    probability = hits / trials
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6, "hits": hits, "total": trials,
        "measured_probability": probability,
        "sampler": "uniform over every correctly shaped n-bit preimage",
        "candidate_space": search_space(inst)}

    demo = make_instance(n=22, rounds=4, k=3, seed=2718)
    exact = enumerate_all(demo)
    space = search_space(demo)
    fraction = exact / space if exact is not None else None
    report["G5_sparse"] = {
        "pass": exact is not None and fraction < 1e-6,
        "preset": "exact-count audit (n=22, rounds=4)", "valid_preimages": exact,
        "candidate_space": space, "fraction": fraction}

    attack_results = {name: [] for name in ("outlier", "greedy", "random_restart")}
    attack_hits = Counter()
    for seed in range(800, 808):
        attacked = make_instance(seed=seed, **params)
        candidates = {
            "outlier": _outlier_attack(attacked),
            "greedy": _greedy_attack(attacked),
            "random_restart": _restart_attack(attacked,
                                                random.Random(seed ^ 0xBAD5EED)),
        }
        for name, candidate in candidates.items():
            ok, why = verify(attacked, candidate)
            attack_hits[name] += int(ok)
            attack_results[name].append({"seed": seed, "solved": ok, "reason": why})
    report["G6_adversary_panel"] = {
        "pass": all(attack_hits[name] == 0 for name in attack_results),
        "seeds_per_attack": 8, "hits": dict(attack_hits),
        "results": attack_results}

    doubled_params = dict(params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * inst["n"] and
                doubled["move_limit"] > inst["move_limit"],
        "base_n": inst["n"], "doubled_n": doubled["n"],
        "base_moves": inst["move_limit"], "doubled_moves": doubled["move_limit"],
        "doubled_verify_reason": doubled_why}

    invariant_count = 0
    real_count = 0
    invariant_failures = []
    for seed in range(20):
        original = make_instance(seed=10_000 + seed, **DIFFICULTY["easy"])
        transformed = _transform_for_g8(original, random.Random(90_000 + seed))
        same = canonical_key(original) == canonical_key(transformed)
        carried, why = verify(transformed, transformed["answer"])
        invariant_count += int(same)
        real_count += int(carried)
        if not same or not carried:
            invariant_failures.append({"seed": seed, "same_key": same,
                                       "carried_answer": carried, "reason": why})
    unrelated = [canonical_key(make_instance(seed=20_000 + seed,
                                              **DIFFICULTY["easy"]))
                 for seed in range(20)]
    distinct = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": invariant_count == 20 and real_count == 20 and distinct == 20,
        "invariance_passed": invariant_count, "invariance_total": 20,
        "real_transform_answers_verified": real_count,
        "real_transform_total": 20,
        "unrelated_distinct": distinct, "unrelated_total": 20,
        "transformations": ["formula-variable renaming", "local polarity flips",
                            "literal reordering", "clause/input reordering"],
        "failures": invariant_failures}

    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["all_passed"] = all(value.get("pass", False) for key, value in report.items()
                                  if key.startswith("G"))
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
