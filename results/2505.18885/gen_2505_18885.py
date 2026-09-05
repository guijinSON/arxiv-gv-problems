"""Verified generator for compressed 2-linear-vertex-arboricity witnesses.

The graph construction is the gadget reduction in Section 2 of arXiv:2505.18885,
"The Parameterized Complexity of Computing the Linear Vertex Arboricity".
The generator first chooses a truth assignment, builds a bounded-occurrence CNF
that it satisfies, and then composes the paper's variable, clause, and link
gadgets.  The answer is the source assignment, a compact symbolic description
of the legal two-colouring produced in the reduction proof.

Only the Python standard library is used.  Importing this module performs no
I/O and has no side effects.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import os
import random
import re
import time


TRACK = "B"

_REDUCTION = (
    "Section 2, Lemmas 1--3 and Theorem 2.1: a satisfying assignment of "
    "Clause-Linked-Planar-Exactly-3-Bounded-3-SAT is carried to a legal "
    "two-colouring of the variable, clause, and link gadgets"
)

PROBLEM_PROFILE = {
    "native_domain": "logic",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "bounded-occurrence CNF formula",
        "maximum-degree-six graph",
        "paper-defined variable, clause, and link gadgets",
    ],
    "verification_operations": [
        "exact Boolean clause evaluation",
        "integer same-colour degree counting",
        "depth-first cycle detection in two induced subgraphs",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": _REDUCTION,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Recognize that truth is constant on the two multiplicative square "
        "cosets of the displayed residue labels; without that symmetry one "
        "must solve the bounded-occurrence CNF or the much larger graph encoding."
    ),
    "hardness_basis": (
        "Track B: Section 5 gives the standard SAT/ILP route, and the measured "
        "source-CNF reference is unit-propagating DPLL with O(2^n*m) worst-case "
        "complexity; at shipping n=240 it averaged 0.119 seconds, 54 "
        "search nodes, and 113,246 literal checks, while the compact square-coset "
        "route uses 120 modular squarings."
    ),
    "max_answer_tokens": 274,
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
    "demo": {"n": 2},
    "easy": {"n": 60},
    "medium": {"n": 126},
    "hard": {"n": 240},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Truth is invariant under multiplication by nonzero squares in the "
    "displayed residue labels modulo p."
)
PLACEBO_HINT = (
    "Success depends on tracking the displayed identifiers and literal signs "
    "with consistent indexing throughout."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly n signed variable IDs in increasing absolute-ID "
        "order: +i assigns variable i true and -i assigns it false."
    ),
    "bounds": {
        "length": "n",
        "absolute_id_min": 1,
        "absolute_id_max": "n",
        "sign_choices_per_entry": 2,
        "candidate_count": "2^n",
        "length_parameter": "n (the shipping preset is capped at 256)",
    },
}

NOTES = r"""
Step 0 and paper grounding.  Section 1 defines a linear forest as a collection
of paths and k-LVA as partitioning all vertices into k sets, each inducing a
linear forest.  Section 2 makes this executable: Lemma 1 fixes the colouring of
the seven-vertex block B, Lemma 2 makes the two positive occurrence ports agree
and the negative port disagree, Lemma 3 propagates the colour of the two
zero-ports through the clause chain, and Theorem 2.1 proves the resulting graph
has a legal two-colouring exactly when the source formula is satisfiable.  The
checker below does not appeal to those lemmas: it expands a submitted source
assignment and directly recounts same-colour degrees and detects cycles.

What makes the native decision problem easy is equally explicit.  Section 1
uses Matsumoto's theorem to dispose of maximum degree at most four (apart from
the complete-graph exception).  Theorem 4.2 is FPT in treewidth.  Section 5
gives a compact SAT/ILP encoding with O(N(N+k)) variables and
O(MNk+N^3) constraints.  Consequently this module does not claim Track A.

Generation samples the answer before any clauses.  Every variable has exactly
two positive and one negative occurrence; all three-literal clauses are
positive, matching (F2)--(F3).  True-positive occurrences anchor the positive
three-clauses and remaining true occurrences anchor the two-clauses.  One
negative-negative clause rules out the all-true shortcut.  The construction
does not enforce the source problem's planar incidence condition (F1), so the
generated graph is not claimed planar; the gadget implication used for G and V
does not depend on the embedding.

Track B structure.  Variable IDs receive a uniformly shuffled copy of all
nonzero residues modulo p=n+1, and the planted true variables are exactly the
quadratic-residue coset.  A generic solver can run DPLL on the displayed CNF or
the Section 5 encoding; a solver that sees the symmetry enumerates the n/2
squares instead.  The outlier/sign-frequency, residue-parity, left-to-right
greedy, half-split, and random-restart attacks are kept separate from the
successful reference algorithm.  The graph vertices are independently
relabelled, so neither gadget block position nor graph vertex magnitude leaks
the assignment.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 1_000_000

# Updated only from successful script-owned hardening runs.  The current zero-
# attempt state is deliberate: HTTP errors are not oracle failures.
_ORACLE_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unavailable_openrouter_403",
}


def _is_prime(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _validate_n(n):
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer")
    if n != 2 and (n < 6 or n % 6):
        raise ValueError("n must be 2 (demo) or a multiple of 6 at least 6")


def _next_prime(value):
    candidate = max(2, value)
    while not _is_prime(candidate):
        candidate += 1
    return candidate


def _truth_bits_from_residues(residues, prime):
    squares = {x * x % prime for x in range(1, prime)}
    return [int(value in squares) for value in residues]


def _literal_true(literal, bits):
    value = bits[abs(literal) - 1]
    return bool(value) if literal > 0 else not bool(value)


def _formula_satisfied(clauses, bits):
    for index, clause in enumerate(clauses):
        if not any(_literal_true(literal, bits) for literal in clause):
            return False, index
    return True, None


def _build_formula(bits, rng):
    """Build an F2--F3 formula around ``bits`` without solving anything."""
    n = len(bits)
    if n == 2:
        true_variable = bits.index(1) + 1
        false_variable = bits.index(0) + 1
        token_clauses = [
            [(true_variable, True, 0), (false_variable, True, 0)],
            [(true_variable, False, 0), (false_variable, False, 0)],
            [(true_variable, False, 1), (false_variable, False, 1)],
        ]
        for clause in token_clauses:
            rng.shuffle(clause)
        rng.shuffle(token_clauses)
        clauses = [
            [(-variable if negative else variable)
             for variable, negative, _occurrence in clause]
            for clause in token_clauses
        ]
        return clauses, token_clauses

    tokens = [(variable, False, occurrence)
              for variable in range(1, n + 1) for occurrence in range(2)]
    tokens += [(variable, True, 0) for variable in range(1, n + 1)]

    true_positive = [token for token in tokens
                     if not token[1] and bits[token[0] - 1] == 1]
    false_positive = [token for token in tokens
                      if not token[1] and bits[token[0] - 1] == 0]
    true_negative = [token for token in tokens
                     if token[1] and bits[token[0] - 1] == 0]

    triple_count = n // 3
    for _ in range(20_000):
        tp = list(true_positive)
        fp = list(false_positive)
        rng.shuffle(tp)
        rng.shuffle(fp)
        triple_tokens = []
        good = True
        for index in range(triple_count):
            triple = [tp[index], fp[2 * index], fp[2 * index + 1]]
            if len({token[0] for token in triple}) != 3:
                good = False
                break
            rng.shuffle(triple)
            triple_tokens.append(triple)
        if good:
            break
    else:
        raise RuntimeError("could not assemble distinct-variable 3-clauses")

    used = set(itertools.chain.from_iterable(triple_tokens))
    remaining = [token for token in tokens if token not in used]

    # Reserve a satisfied negative-negative clause.  It makes both constant
    # assignments fail and removes the most obvious sign-frequency shortcut.
    rng.shuffle(true_negative)
    reserve = true_negative[:2]
    if len(reserve) != 2 or reserve[0][0] == reserve[1][0]:
        raise AssertionError("balanced truth assignment lacks two negative anchors")
    for token in reserve:
        remaining.remove(token)

    true_remaining = [token for token in remaining
                      if _literal_true(-token[0] if token[1] else token[0], bits)]
    for _ in range(20_000):
        anchors = list(true_remaining)
        rng.shuffle(anchors)
        anchors = anchors[:n - 1]
        extras = list(remaining)
        for token in anchors:
            extras.remove(token)
        rng.shuffle(extras)
        if all(a[0] != b[0] for a, b in zip(anchors, extras)):
            pair_tokens = [[reserve[0], reserve[1]]]
            pair_tokens += [[a, b] for a, b in zip(anchors, extras)]
            break
    else:
        raise RuntimeError("could not assemble distinct-variable 2-clauses")

    token_clauses = pair_tokens + triple_tokens
    for clause in token_clauses:
        rng.shuffle(clause)
    rng.shuffle(token_clauses)
    clauses = [
        [(-variable if negative else variable)
         for variable, negative, _occurrence in clause]
        for clause in token_clauses
    ]
    port_tokens = [
        [(variable, negative, occurrence)
         for variable, negative, occurrence in clause]
        for clause in token_clauses
    ]
    ok, _ = _formula_satisfied(clauses, bits)
    if not ok:
        raise AssertionError("inverse-generated formula lost its witness")
    return clauses, port_tokens


def _add_edge(edge_set, u, v):
    if u == v:
        raise AssertionError("self-loop in construction")
    edge_set.add((u, v) if u < v else (v, u))


def _add_basic_block(new_vertex, edge_set):
    """Add the seven-vertex block B from Fig. 2 and return its vertices."""
    block = [new_vertex() for _ in range(7)]
    triangles = (
        (1, 2, 3), (0, 1, 3), (0, 1, 4), (2, 3, 4),
        (1, 3, 4), (1, 3, 5), (1, 3, 6), (1, 5, 6),
    )
    for triangle in triangles:
        for index in range(3):
            _add_edge(edge_set, block[triangle[index]],
                      block[triangle[(index + 1) % 3]])
    return block


def _relabel_graph(data, rng):
    vertex_count = data["vertex_count"]
    permutation = list(range(vertex_count))
    rng.shuffle(permutation)

    def vertices(values):
        return [permutation[value] for value in values]

    data["edges"] = sorted(
        (min(permutation[u], permutation[v]), max(permutation[u], permutation[v]))
        for u, v in data["edges"]
    )
    for block in data["variable_blocks"]:
        block["b"] = vertices(block["b"])
        block["positive_ports"] = vertices(block["positive_ports"])
        block["auxiliary_pair"] = vertices(block["auxiliary_pair"])
        block["negative_port"] = permutation[block["negative_port"]]
    for block in data["clause_blocks"]:
        block["zeros"] = vertices(block["zeros"])
        block["ports"] = vertices(block["ports"])
    for block in data["link_blocks"]:
        block["b"] = vertices(block["b"])
        block["left_zero"] = permutation[block["left_zero"]]
        block["right_zero"] = permutation[block["right_zero"]]


def _signed_answer(bits):
    return [index if bit else -index for index, bit in enumerate(bits, 1)]


def make_instance(n, seed=0, **params):
    """Inverse-generate a formula and compose its certified LVA graph.

    The truth assignment is fixed before clauses or graph edges exist.  The
    proof-colouring is carried through an independent graph-vertex relabelling;
    neither SAT nor graph search is used by generation.
    """
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_n(n)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    prime = _next_prime(n + 1)

    # The named presets use every nonzero residue.  Selecting equal-size samples
    # from the two cosets also lets arbitrary larger multiples of six scale.
    all_squares = sorted({x * x % prime for x in range(1, prime)})
    square_set = set(all_squares)
    all_nonsquares = [x for x in range(1, prime) if x not in square_set]
    rng.shuffle(all_squares)
    rng.shuffle(all_nonsquares)
    residues = all_squares[:n // 2] + all_nonsquares[:n // 2]
    rng.shuffle(residues)
    bits = _truth_bits_from_residues(residues, prime)
    clauses, token_clauses = _build_formula(bits, rng)

    edges = set()
    next_vertex = 0

    def new_vertex():
        nonlocal next_vertex
        value = next_vertex
        next_vertex += 1
        return value

    variable_blocks = []
    port_for_token = {}
    for variable in range(1, n + 1):
        basic = _add_basic_block(new_vertex, edges)
        positive = [new_vertex(), new_vertex()]
        auxiliary = [new_vertex(), new_vertex()]
        negative = new_vertex()
        for vertex in positive:
            _add_edge(edges, vertex, basic[0])
        for vertex in auxiliary:
            _add_edge(edges, vertex, basic[6])
        _add_edge(edges, auxiliary[0], auxiliary[1])
        _add_edge(edges, auxiliary[0], negative)
        _add_edge(edges, auxiliary[1], negative)
        port_for_token[(variable, False, 0)] = positive[0]
        port_for_token[(variable, False, 1)] = positive[1]
        port_for_token[(variable, True, 0)] = negative
        variable_blocks.append({
            "var": variable,
            "b": basic,
            "positive_ports": positive,
            "auxiliary_pair": auxiliary,
            "negative_port": negative,
        })

    clause_blocks = []
    for literals, token_clause in zip(clauses, token_clauses):
        left_zero = new_vertex()
        right_zero = new_vertex()
        ports = [port_for_token[token] for token in token_clause]
        cycle = [left_zero] + ports + [right_zero]
        for u, v in zip(cycle, cycle[1:] + cycle[:1]):
            _add_edge(edges, u, v)
        clause_blocks.append({
            "literals": list(literals),
            "zeros": [left_zero, right_zero],
            "ports": ports,
        })

    link_blocks = []
    for left, right in zip(clause_blocks, clause_blocks[1:]):
        basic = _add_basic_block(new_vertex, edges)
        left_zero = left["zeros"][1]
        right_zero = right["zeros"][0]
        _add_edge(edges, basic[0], left_zero)
        _add_edge(edges, basic[6], right_zero)
        link_blocks.append({
            "b": basic,
            "left_zero": left_zero,
            "right_zero": right_zero,
        })

    data = {
        "family": "compressed 2-linear-vertex-arboricity via Section 2 gadgets",
        "n": n,
        "prime": prime,
        "variable_residues": residues,
        "clauses": clauses,
        "vertex_count": next_vertex,
        "edges": sorted(edges),
        "variable_blocks": variable_blocks,
        "clause_blocks": clause_blocks,
        "link_blocks": link_blocks,
    }
    _relabel_graph(data, rng)
    data["answer"] = _signed_answer(bits)

    degrees = [0] * data["vertex_count"]
    for u, v in data["edges"]:
        degrees[u] += 1
        degrees[v] += 1
    if max(degrees, default=0) > 6:
        raise AssertionError("paper construction exceeded maximum degree six")
    ok, reason = verify(data, data["answer"])
    if not ok:
        raise AssertionError("constructed witness failed: " + reason)
    return data


def render(inst):
    """Render the complete, self-contained compressed-certificate problem."""
    variable_lines = [
        f"{index}:{residue}"
        for index, residue in enumerate(inst["variable_residues"], 1)
    ]
    clause_lines = [
        f"C{index} " + " ".join(f"{literal:+d}" for literal in clause)
        for index, clause in enumerate(inst["clauses"], 1)
    ]
    variable_block_lines = []
    for block in sorted(inst["variable_blocks"], key=lambda row: row["var"]):
        variable_block_lines.append(
            "V{var} B={b} P={p} A={a} N={neg}".format(
                var=block["var"],
                b=",".join(map(str, block["b"])),
                p=",".join(map(str, block["positive_ports"])),
                a=",".join(map(str, block["auxiliary_pair"])),
                neg=block["negative_port"],
            )
        )
    clause_block_lines = [
        "C{idx} Z={zeros} P={ports}".format(
            idx=index,
            zeros=",".join(map(str, block["zeros"])),
            ports=",".join(map(str, block["ports"])),
        )
        for index, block in enumerate(inst["clause_blocks"], 1)
    ]
    link_lines = [
        "L{idx} B={b} ATTACH={left},{right}".format(
            idx=index,
            b=",".join(map(str, block["b"])),
            left=block["left_zero"],
            right=block["right_zero"],
        )
        for index, block in enumerate(inst["link_blocks"], 1)
    ]
    edge_lines = [f"{u} {v}" for u, v in inst["edges"]]
    hint = ""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        hint = "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        hint = "\n\nHint: " + PLACEBO_HINT

    return f"""COMPRESSED CERTIFICATE FOR TWO LINEAR VERTEX FORESTS

An undirected graph is given below.  A linear forest is a graph whose connected
components are paths, including isolated vertices.  Equivalently it is acyclic
and every vertex has degree at most two.  A legal two-colouring assigns every
graph vertex colour 0 or 1 so that each colour's induced subgraph is a linear
forest.

This graph is written in the variable, clause, and link blocks of Section 2 of
the cited construction.  Instead of transcribing all {inst['vertex_count']}
colours, submit the source truth assignment.  The following deterministic
expansion is part of the certificate definition.

For variable i, let its row be `Vi B=b0,...,b6 P=p0,p1 A=a0,a1 N=q`.
When i is FALSE, colour b0,b2,b4,b5,b6,q with 1 and the other six row vertices
with 0.  When i is TRUE, reverse all twelve colours in that row.  Colour every
Z vertex in every clause row 0.  Colour each link block's b0,b2,b4,b5,b6 with
1 and b1,b3 with 0.  The P entries of a clause row are occurrence ports already
coloured in their variable rows.  These rules assign every graph vertex once.
The checker performs this expansion and directly verifies maximum induced
degree two and absence of monochromatic cycles using the edge list; it does not
trust the claimed reduction.

The source formula has variables 1 through {inst['n']}.  A positive literal +i
is true exactly when variable i is TRUE; a negative literal -i is true exactly
when variable i is FALSE.  A clause is satisfied when at least one listed
literal is true, and all clauses must be satisfied.  Clauses have two or three
distinct variables, each variable occurs exactly twice positively and once
negatively, and every three-literal clause is positive.  These conditions do
not replace the checks above: a submitted assignment must also expand to a
legal graph colouring.

Each variable additionally has a distinct LABEL in the nonzero residues modulo
p={inst['prime']}.  Labels are ordinary instance data; variable IDs, not labels,
are used in the answer.

VARIABLES (ID:LABEL)
{' '.join(variable_lines)}

CLAUSES
{chr(10).join(clause_lines)}

VARIABLE BLOCKS
{chr(10).join(variable_block_lines)}

CLAUSE BLOCKS
{chr(10).join(clause_block_lines)}

LINK BLOCKS
{chr(10).join(link_lines)}

GRAPH
Vertices are the integers 0 through {inst['vertex_count'] - 1}, inclusive.
Edges are unordered, have no repeats or loops, and are listed one per line:
{chr(10).join(edge_lines)}
{hint}

Give your final answer inside <answer></answer> tags as one JSON list of exactly
{inst['n']} signed integers.  At position i (positions are 1-indexed), write +i
to assign variable i TRUE or -i to assign it FALSE.  Thus absolute IDs must be
1,2,...,{inst['n']} in that order; repeats and zero are forbidden.
Example format for three variables only: <answer>[1,-2,3]</answer>
Output nothing else inside the tags."""


def parse_answer(text):
    """Extract the last well-formed tagged JSON value, tolerating prose/fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    for body in reversed(matches):
        body = body.strip()
        if body.startswith("```") and body.endswith("```"):
            lines = body.splitlines()
            body = "\n".join(lines[1:-1]).strip() if len(lines) >= 2 else body
        try:
            return json.loads(body)
        except (TypeError, ValueError):
            continue
    return None


def _decode_answer(inst, answer):
    n = inst["n"]
    if not isinstance(answer, list):
        return None, "answer must be a JSON list"
    if not answer:
        return None, "answer is empty"
    if len(answer) != n:
        return None, f"expected exactly {n} signed entries"
    if any(isinstance(value, bool) or not isinstance(value, int) for value in answer):
        return None, "every entry must be an integer"
    absolute = [abs(value) for value in answer]
    if any(value < 1 or value > n for value in absolute):
        return None, f"variable id outside 1..{n}"
    if len(set(absolute)) != n:
        return None, "variable IDs must be unique"
    if absolute != list(range(1, n + 1)):
        return None, "entries must be in increasing variable-ID order"
    return [int(value > 0) for value in answer], "ok"


def _expanded_colouring(inst, bits):
    colours = [-1] * inst["vertex_count"]

    def set_colour(vertex, colour):
        if not (0 <= vertex < len(colours)):
            raise ValueError("gadget vertex out of range")
        if colours[vertex] not in (-1, colour):
            raise ValueError("gadget expansion assigns conflicting colours")
        colours[vertex] = colour

    base_ones = {0, 2, 4, 5, 6}
    for block in inst["variable_blocks"]:
        bit = bits[block["var"] - 1]
        local = list(block["b"]) + list(block["positive_ports"])
        local += list(block["auxiliary_pair"]) + [block["negative_port"]]
        false_ones = {block["b"][index] for index in base_ones}
        false_ones.add(block["negative_port"])
        for vertex in local:
            colour = int(vertex in false_ones)
            set_colour(vertex, colour ^ bit)
    for block in inst["clause_blocks"]:
        for vertex in block["zeros"]:
            set_colour(vertex, 0)
    for block in inst["link_blocks"]:
        for index, vertex in enumerate(block["b"]):
            set_colour(vertex, int(index in base_ones))
    if any(colour < 0 for colour in colours):
        raise ValueError("gadget expansion leaves an uncoloured vertex")
    return colours


def _check_linear_forests(inst, colours):
    vertex_count = inst["vertex_count"]
    adjacency = [[] for _ in range(vertex_count)]
    seen_edges = set()
    for edge in inst["edges"]:
        if (not isinstance(edge, (list, tuple)) or len(edge) != 2
                or any(isinstance(v, bool) or not isinstance(v, int) for v in edge)):
            return False, "malformed graph edge"
        u, v = edge
        if not (0 <= u < vertex_count and 0 <= v < vertex_count) or u == v:
            return False, "graph edge endpoint invalid"
        key = (min(u, v), max(u, v))
        if key in seen_edges:
            return False, "duplicate graph edge"
        seen_edges.add(key)
        adjacency[u].append(v)
        adjacency[v].append(u)

    for vertex in range(vertex_count):
        same = sum(colours[neighbor] == colours[vertex]
                   for neighbor in adjacency[vertex])
        if same > 2:
            return False, f"vertex {vertex} has same-colour degree {same}"

    visited = [False] * vertex_count
    for start in range(vertex_count):
        if visited[start]:
            continue
        stack = [(start, -1)]
        while stack:
            vertex, parent = stack.pop()
            if visited[vertex]:
                return False, f"colour {colours[vertex]} contains a cycle"
            visited[vertex] = True
            for neighbor in adjacency[vertex]:
                if colours[neighbor] == colours[vertex] and neighbor != parent:
                    stack.append((neighbor, vertex))
    return True, "ok"


def verify(inst, answer):
    """Accept every source assignment whose exact expansion is a legal witness."""
    bits, reason = _decode_answer(inst, answer)
    if bits is None:
        return False, reason
    formula_ok, clause_index = _formula_satisfied(inst["clauses"], bits)
    if not formula_ok:
        return False, f"clause {clause_index + 1} is false"
    try:
        colours = _expanded_colouring(inst, bits)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return False, "malformed gadget map: " + str(exc)
    return _check_linear_forests(inst, colours)


def random_candidate(inst, rng):
    """Sample uniformly from the fully structure-aware signed assignment space."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    return [index if rng.randrange(2) else -index
            for index in range(1, inst["n"] + 1)]


def search_space(inst):
    return 1 << inst["n"]


def enumerate_all(inst):
    space = search_space(inst)
    # Bound actual verification work, not merely the number of assignments.
    # A candidate verification is linear in the displayed formula and graph.
    work_per_candidate = (
        sum(len(clause) for clause in inst["clauses"])
        + inst["vertex_count"]
        + len(inst["edges"])
    )
    if space > _ENUMERATION_CAP or space * work_per_candidate > 2_000_000:
        return None
    count = 0
    for mask in range(space):
        bits = [(mask >> index) & 1 for index in range(inst["n"])]
        candidate = _answer_from_bits(bits)
        count += int(verify(inst, candidate)[0])
    return count


def _canonical_formula(inst, multiplier):
    prime = inst["prime"]
    residues = inst["variable_residues"]
    rows = []
    for clause in inst["clauses"]:
        row = []
        for literal in clause:
            residue = residues[abs(literal) - 1] * multiplier % prime
            row.append((int(literal < 0), residue))
        rows.append(tuple(sorted(row)))
    return tuple(sorted(rows))


def canonical_key(inst):
    """Canonicalize variable names, graph labels, order, and square scaling."""
    prime = inst["prime"]
    squares = sorted({x * x % prime for x in range(1, prime)})
    canonical = min(_canonical_formula(inst, multiplier) for multiplier in squares)
    payload = json.dumps([prime, canonical], separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params):
    n = params.get("n")
    for candidate in (60, 126, 240):
        if candidate > n:
            return {"n": candidate}
    return "cap_bound"


def _answer_from_bits(bits):
    return _signed_answer(bits)


def _attack_sign_frequency(inst):
    # Every variable appears twice positively and once negatively, so this is
    # exactly the tempting all-true per-variable statistic.
    return list(range(1, inst["n"] + 1))


def _attack_residue_parity(inst):
    bits = [residue & 1 for residue in inst["variable_residues"]]
    return _answer_from_bits(bits)


def _attack_half_split(inst):
    bits = [int(index < inst["n"] // 2) for index in range(inst["n"])]
    return _answer_from_bits(bits)


def _attack_greedy_one_pass(inst):
    """A by-hand, no-backtracking left-to-right clause-satisfaction heuristic."""
    n = inst["n"]
    bits = [None] * n
    clauses_by_var = [[] for _ in range(n)]
    for clause in inst["clauses"]:
        for literal in clause:
            clauses_by_var[abs(literal) - 1].append(clause)
    for variable in range(n):
        scores = []
        for trial in (0, 1):
            bits[variable] = trial
            score = 0
            for clause in clauses_by_var[variable]:
                for literal in clause:
                    value = bits[abs(literal) - 1]
                    if value is not None and (bool(value) if literal > 0 else not bool(value)):
                        score += 1
                        break
            scores.append(score)
        bits[variable] = int(scores[1] > scores[0])
    return _answer_from_bits([int(value) for value in bits])


def _dpll_reference(inst, node_cap=1_000_000):
    """DPLL with unit propagation; return candidate and exact work counters."""
    n = inst["n"]
    clauses = inst["clauses"]
    stats = {"nodes": 0, "literal_checks": 0, "cap_reached": False}

    def search(assignment):
        stats["nodes"] += 1
        if stats["nodes"] > node_cap:
            stats["cap_reached"] = True
            return None
        while True:
            unit = None
            occurrence = [0] * n
            for clause in clauses:
                satisfied = False
                undecided = []
                for literal in clause:
                    stats["literal_checks"] += 1
                    value = assignment[abs(literal) - 1]
                    if value < 0:
                        undecided.append(literal)
                        occurrence[abs(literal) - 1] += 1
                    elif bool(value) if literal > 0 else not bool(value):
                        satisfied = True
                        break
                if satisfied:
                    continue
                if not undecided:
                    return False
                if len(undecided) == 1:
                    unit = undecided[0]
                    break
            if unit is None:
                break
            variable = abs(unit) - 1
            forced = int(unit > 0)
            if assignment[variable] >= 0 and assignment[variable] != forced:
                return False
            assignment[variable] = forced

        if all(value >= 0 for value in assignment):
            return assignment
        variable = max(
            (occurrence[index], -index)
            for index, value in enumerate(assignment) if value < 0
        )[1]
        variable = -variable
        for value in (1, 0):
            branch = list(assignment)
            branch[variable] = value
            result = search(branch)
            if result is None:
                return None
            if result is not False:
                return result
        return False

    result = search([-1] * n)
    if result is None or result is False:
        return None, stats
    return _answer_from_bits(result), stats


def _compact_square_decode(inst):
    representatives = range(1, (inst["prime"] + 1) // 2)
    squares = {x * x % inst["prime"] for x in representatives}
    bits = [int(residue in squares) for residue in inst["variable_residues"]]
    return _answer_from_bits(bits), (inst["prime"] - 1) // 2


def _apply_transform(inst, seed, mask):
    """Apply a composition of four genuine presentation/domain symmetries."""
    out = copy.deepcopy(inst)
    rng = random.Random(seed)
    carried = list(inst["answer"])
    n = inst["n"]

    if mask & 1:  # arbitrary graph-vertex relabelling
        permutation = list(range(out["vertex_count"]))
        rng.shuffle(permutation)

        def values(row):
            return [permutation[value] for value in row]

        out["edges"] = [
            [min(permutation[u], permutation[v]), max(permutation[u], permutation[v])]
            for u, v in out["edges"]
        ]
        for block in out["variable_blocks"]:
            block["b"] = values(block["b"])
            block["positive_ports"] = values(block["positive_ports"])
            block["auxiliary_pair"] = values(block["auxiliary_pair"])
            block["negative_port"] = permutation[block["negative_port"]]
        for block in out["clause_blocks"]:
            block["zeros"] = values(block["zeros"])
            block["ports"] = values(block["ports"])
        for block in out["link_blocks"]:
            block["b"] = values(block["b"])
            block["left_zero"] = permutation[block["left_zero"]]
            block["right_zero"] = permutation[block["right_zero"]]

    if mask & 2:  # variable renaming with the witness carried through
        permutation = list(range(1, n + 1))
        rng.shuffle(permutation)
        new_residues = [0] * n
        new_bits = [0] * n
        old_bits, _ = _decode_answer(inst, carried)
        for old in range(1, n + 1):
            new = permutation[old - 1]
            new_residues[new - 1] = out["variable_residues"][old - 1]
            new_bits[new - 1] = old_bits[old - 1]
        out["variable_residues"] = new_residues
        for block in out["variable_blocks"]:
            block["var"] = permutation[block["var"] - 1]
        out["clauses"] = [
            [(1 if literal > 0 else -1) * permutation[abs(literal) - 1]
             for literal in clause]
            for clause in out["clauses"]
        ]
        for block in out["clause_blocks"]:
            block["literals"] = [
                (1 if literal > 0 else -1) * permutation[abs(literal) - 1]
                for literal in block["literals"]
            ]
        carried = _answer_from_bits(new_bits)

    if mask & 4:  # reorder all unordered input collections
        rng.shuffle(out["edges"])
        paired = list(zip(out["clauses"], out["clause_blocks"]))
        rng.shuffle(paired)
        out["clauses"] = []
        out["clause_blocks"] = []
        for clause, block in paired:
            order = list(range(len(clause)))
            rng.shuffle(order)
            out["clauses"].append([clause[index] for index in order])
            block["literals"] = [block["literals"][index] for index in order]
            block["ports"] = [block["ports"][index] for index in order]
            out["clause_blocks"].append(block)

    if mask & 8:  # multiply every field label by a square
        square = pow(rng.randrange(1, out["prime"]), 2, out["prime"])
        out["variable_residues"] = [
            square * value % out["prime"] for value in out["variable_residues"]
        ]

    out["answer"] = carried
    return out


def selftest():
    report = {}
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
        "construction_route": "inverse formula plus composition of Section 2 gadget colourings",
    }

    inst = make_instance(seed=19, **shipping)
    answer = inst["answer"]
    swapped = list(answer)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = list(answer)
    duplicated[1] = duplicated[0]
    out_of_range = list(answer)
    out_of_range[0] = inst["n"] + 1
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": reason}
    reasons = [row["reason"] for row in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in rejected.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The coset classification gives this assignment.\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nThe signs use the requested variable order."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x250518885)
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
        "structure_aware_space": str(search_space(inst)),
        "space_bits": inst["n"],
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = (
        "outlier_sign_frequency",
        "residue_parity",
        "half_split_by_variable_id",
        "greedy_left_to_right_no_backtracking",
        "random_restart_256",
    )
    attack_successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_nodes = 0
    reference_checks = 0
    compact_successes = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        candidates = {
            "outlier_sign_frequency": [_attack_sign_frequency(trial)],
            "residue_parity": [_attack_residue_parity(trial)],
            "half_split_by_variable_id": [_attack_half_split(trial)],
            "greedy_left_to_right_no_backtracking": [_attack_greedy_one_pass(trial)],
        }
        rrng = random.Random(seed ^ 0x5A17)
        candidates["random_restart_256"] = [
            random_candidate(trial, rrng) for _ in range(256)
        ]
        for name in attack_names:
            started = time.perf_counter()
            solved = any(verify(trial, candidate)[0]
                         for candidate in candidates[name])
            attack_seconds[name] += time.perf_counter() - started
            attack_successes[name] += int(solved)

        started = time.perf_counter()
        reference, stats = _dpll_reference(trial)
        reference_seconds += time.perf_counter() - started
        reference_nodes += stats["nodes"]
        reference_checks += stats["literal_checks"]
        reference_successes += int(
            reference is not None and verify(trial, reference)[0]
        )
        compact, _operations = _compact_square_decode(trial)
        compact_successes += int(verify(trial, compact)[0])

    attacks = {
        name: {
            "successes": attack_successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "DPLL on the displayed CNF with unit propagation and occurrence branching",
        "complexity": "O(2^n * m) worst case; measured on this Track B distribution",
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_checks // 8,
        "search_nodes": reference_nodes // 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in attack_successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "enumerate the nonzero quadratic residues and match labels",
            "operations": inst["n"] // 2,
            "solves": f"{compact_successes}/8",
        },
    }

    demo_inst = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6 and demo_count is not None
        and all_failed and reference_successes == 8 and compact_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density_estimate": guess_fraction,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo_inst),
        "strongest_attack": reference["name"],
        "baseline_wall_clock_sec": reference["wall_clock_sec"],
        "baseline_search_nodes": reference["search_nodes"],
        "baseline_operation_count": reference["operations"],
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    started = time.perf_counter()
    scaled = make_instance(seed=77, **doubled_params)
    scaled_build = time.perf_counter() - started
    scaled_ok, scaled_reason = verify(scaled, scaled["answer"])
    ladder = [DIFFICULTY[name]["n"] for name in DIFFICULTY]
    report["G7_scales"] = {
        "pass": scaled_ok and scaled["n"] == 2 * inst["n"]
        and ladder == sorted(ladder)
        and len(set(ladder)) == len(ladder)
        and search_space(scaled) > search_space(inst),
        "shipping_n": inst["n"],
        "scaled_n": scaled["n"],
        "literal_size_double_built": True,
        "shipping_cap_safe_maximum": 240,
        "scaled_build_sec": round(scaled_build, 6),
        "scaled_verify_reason": scaled_reason,
        "candidate_space_bits_shipping": inst["n"],
        "candidate_space_bits_scaled": scaled["n"],
    }

    invariant = 0
    real = 0
    unrelated = []
    masks = range(1, 16)
    # Canonicalization is tested at easy size; the same routine is size-agnostic,
    # while doing 300 deep copies of the 12k-edge hard graph adds no coverage.
    for seed in range(201, 221):
        original = make_instance(seed=seed, **DIFFICULTY["easy"])
        key = canonical_key(original)
        for mask in masks:
            transformed = _apply_transform(original, seed ^ 0x9E3779B9, mask)
            invariant += int(canonical_key(transformed) == key)
            real += int(verify(transformed, transformed["answer"])[0])
        unrelated.append(key)
    distinct = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": invariant == 300 and real == 300 and distinct == 20,
        "invariant_relabellings": invariant,
        "real_transformations_verified": real,
        "unrelated_distinct_keys": distinct,
        "unrelated_attempts": 20,
        "transformations": [
            "graph-vertex relabelling",
            "variable renaming with carried assignment",
            "edge/clause/literal reordering",
            "multiplication of residue labels by a nonzero square",
            "all 15 nonempty compositions",
        ],
    }

    encoded = json.dumps(answer, separators=(",", ":"))
    answer_chars = len(encoded)
    answer_tokens = math.ceil(answer_chars / 4)
    worst_chars = 2 + (inst["n"] - 1) + sum(
        len(str(index)) + 1 for index in range(1, inst["n"] + 1)
    )
    worst_tokens = math.ceil(worst_chars / 4)
    elements = len(answer)
    operations = inst["n"] // 2
    arms = {name: dict(_ORACLE_EVIDENCE[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2_000 and elements <= 256 and operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == worst_tokens
    )
    report["G9_no_tool_suitability"] = {
        # G9(a) and the former hinted-arm gate G9(b) are diagnostics as of
        # 2026-09-05.  Only the answer-size and intended-effort caps in G9(c)
        # gate shipment.
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _ORACLE_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": worst_tokens,
        "answer_elements": elements,
        "intended_route_operations": operations,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
