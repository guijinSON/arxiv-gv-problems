"""Self-contained verified generator derived from arXiv:1706.08050.

Section 2, Theorem 4 reduces Connected Vertex Cover to Connected Odd Cycle
Transversal: retain every source edge and add an even parallel path. At p=3
every source edge becomes the base of a triangle. This module inverse-generates
a connected vertex cover, then carries it through that exact construction.

The source graph uses variable-edge/clause-triangle incidence gadgets for a
sparse parity system. The system is nonsingular by construction, not by a rank
search. Generic recovery uses Gaussian elimination; a compact route recognizes
the peelable incidence hypergraph.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # This family remains standard-library-only.
    exact_matrices = rationals = None


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "The four-clause blocks form a sparse parity system whose incidence "
    "hypergraph has a perfect elimination ordering."
)
PLACEBO_HINT: str = (
    "The grouped gadget tables form a regular instance whose labels require "
    "careful and consistent bookkeeping."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite simple graph",
        "connected odd-cycle transversal",
        "triangle expansion of a connected-vertex-cover instance",
    ],
    "verification_operations": [
        "exact vertex membership",
        "source-edge coverage",
        "gadget quota counting",
        "induced connectivity through a universal selected vertex",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 2, Theorem 4 (Connected Vertex Cover to Connected Odd "
        "Cycle Transversal on girth-p graphs), specialized to p=3"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Recognize each four-clause block as one parity constraint and peel "
        "the sparse incidence hypergraph; without that structure one must "
        "run generic elimination or search the exponentially large gadget "
        "choice space."
    ),
    "hardness_basis": (
        "Track B: decoding the parity blocks and applying generic Gaussian "
        "elimination costs O(n^3) bit operations; at shipping n=24 it takes "
        "a measured median 2,678 scalar XORs and 0.000298 seconds, whereas the "
        "incidence-peeling route takes 119 exact XORs and must be recognized "
        "and executed from graph-gadget tables without a SAT solver or "
        "scratchpad."
    ),
    "max_answer_tokens": 272,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 4},
    "easy": {"n": 8},
    "medium": {"n": 16},
    "hard": {"n": 24},
}
SHIPPING_DIFFICULTY: str = "hard"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A strictly increasing list containing the designated connector, "
        "exactly one vertex from every displayed variable pair, and exactly "
        "two vertices from every displayed clause triangle. Every one of the "
        "two choices per variable pair and every one of the three omissions "
        "per clause triangle belongs to the language; semantic edge coverage "
        "is checked by verify. All entries are source labels."
    ),
    "bounds": {
        "structure_aware_candidates": "2^n * 3^(4n)",
        "completion_choices_per_assignment": "3^(4n)",
        "mandatory_connectors": 1,
        "answer_atoms": "9n+1",
        "order": "strictly increasing",
        "repetitions": False,
    },
}

NOTES: str = (
    "Section 1 fixes the transversal and connectivity definitions. Section 2, "
    "Theorem 4 is used verbatim at p=3: each source edge is retained and gets "
    "a length-two parallel path, so a connected source vertex cover is a "
    "connected odd-cycle transversal. The Introduction notes that Connected "
    "Feedback Vertex Set is FPT in solution size, and Theorems 10, 12, and 14 "
    "give polynomial algorithms on sP2-free graphs for fixed s. This family "
    "uses the general p=3 regime but makes no Track-A average-case claim. It "
    "samples the Boolean assignment first, computes parity right-hand sides, "
    "constructs a provably nonsingular sparse system with a four-variable core "
    "and triangular extensions, and only then builds the cover. No solver runs "
    "during generation. Balanced parity blocks give both literal vertices of "
    "each variable the same incidence degree, defeating the outlier probe; "
    "randomized variable and block order removes the greedy scan order; the "
    "unique assignment makes 256 random restarts negligible at n=24; and a "
    "single displayed-order pass that repairs each parity row is frustrated by "
    "later rows disturbing earlier ones."
)


# Replaced with measurements from the three isolated hardening runs before ship.
G9_RESULTS: dict = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "pending",
}


def _require_parameters(n: int) -> None:
    if not isinstance(n, int) or isinstance(n, bool) or n < 4:
        raise ValueError("n must be an integer at least 4")


def _edge(u: int, v: int) -> tuple[int, int]:
    return (u, v) if u < v else (v, u)


def _xor(values) -> int:
    value = 0
    for bit in values:
        value ^= bit
    return value


def _equation_supports(n: int, rng: random.Random) -> list[list[int]]:
    """Construct an invertible n-by-n GF(2) matrix with row weight three."""
    order = list(range(n))
    rng.shuffle(order)
    supports = []
    core = order[:4]
    for missing in core:
        supports.append([v for v in core if v != missing])
    for position in range(4, n):
        parents = rng.sample(order[:position], 2)
        supports.append([order[position], parents[0], parents[1]])
    rng.shuffle(supports)
    return supports


def _clauses_for_parity(
    variables: list[int], rhs: int, rng: random.Random
) -> list[list[tuple[int, int]]]:
    """Return four 3-clauses equivalent to xor(variables) == rhs.

    A tuple (v,b) denotes a literal true exactly when x_v=b. For each
    wrong-parity assignment one clause is false only on that assignment.
    """
    clauses = []
    for bits in itertools.product((0, 1), repeat=3):
        if _xor(bits) != rhs:
            clause = [(variables[i], 1 - bits[i]) for i in range(3)]
            rng.shuffle(clause)
            clauses.append(clause)
    rng.shuffle(clauses)
    return clauses


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a connected OCT instance and its native witness."""
    del params
    _require_parameters(n)
    rng = random.Random(seed)
    solution = [rng.randrange(2) for _ in range(n)]
    supports = _equation_supports(n, rng)

    source_count = 14 * n + 1
    labels = list(range(source_count))
    rng.shuffle(labels)
    cursor = 0
    variable_pairs = []
    for _ in range(n):
        variable_pairs.append([labels[cursor], labels[cursor + 1]])
        cursor += 2

    block_specs = []
    for support in supports:
        rhs = _xor(solution[v] for v in support)
        block_specs.append(_clauses_for_parity(support, rhs, rng))

    blocks = []
    flat_clauses = []
    for block_spec in block_specs:
        block = []
        for literal_spec in block_spec:
            nodes = labels[cursor:cursor + 3]
            cursor += 3
            attachment_nodes = [
                variable_pairs[var][truth] for var, truth in literal_spec
            ]
            clause = {
                "nodes": list(nodes),
                "attachments": list(attachment_nodes),
            }
            block.append(clause)
            flat_clauses.append(clause)
        blocks.append(block)

    connector = labels[cursor]
    assert cursor + 1 == source_count

    source_edges: set[tuple[int, int]] = set()
    for pair in variable_pairs:
        source_edges.add(_edge(pair[0], pair[1]))
    for clause in flat_clauses:
        a, b, c = clause["nodes"]
        source_edges.update((_edge(a, b), _edge(a, c), _edge(b, c)))
        for node, attachment in zip(clause["nodes"], clause["attachments"]):
            source_edges.add(_edge(node, attachment))
    for vertex in labels:
        if vertex != connector:
            source_edges.add(_edge(connector, vertex))

    answer = [connector]
    answer.extend(variable_pairs[v][solution[v]] for v in range(n))
    chosen_variables = set(answer)
    for clause in flat_clauses:
        true_positions = [
            i for i, attachment in enumerate(clause["attachments"])
            if attachment in chosen_variables
        ]
        if not true_positions:
            raise AssertionError("parity encoding produced an unsatisfied clause")
        omitted = rng.choice(true_positions)
        answer.extend(
            node for i, node in enumerate(clause["nodes"]) if i != omitted
        )
    answer.sort()

    edge_list = [list(edge) for edge in source_edges]
    rng.shuffle(edge_list)
    rng.shuffle(variable_pairs)
    rng.shuffle(blocks)
    return {
        "paper": "arXiv:1706.08050",
        "construction": "Section 2, Theorem 4 at p=3 (triangle expansion)",
        "n": n,
        "connector": connector,
        "variable_pairs": variable_pairs,
        "parity_blocks": blocks,
        "source_edges": edge_list,
        "source_vertex_count": source_count,
        "expanded_vertex_count": source_count + len(source_edges),
        "answer": answer,
    }


def _all_clauses(inst: dict):
    for block in inst["parity_blocks"]:
        for clause in block:
            yield clause


def _answer_text(answer: list[int]) -> str:
    return ", ".join(str(x) for x in answer)


def render(inst: dict) -> str:
    pair_lines = []
    for index, (zero, one) in enumerate(inst["variable_pairs"]):
        pair_lines.append(
            f"  x{index}: ({zero}, {one})  [first means 0; second means 1]"
        )
    block_lines = []
    for block_index, block in enumerate(inst["parity_blocks"]):
        block_lines.append(f"  block {block_index}:")
        for clause_index, clause in enumerate(block):
            parts = [
                f"{node}->{attachment}"
                for node, attachment in zip(
                    clause["nodes"], clause["attachments"]
                )
            ]
            block_lines.append(
                f"    triangle {clause_index}: " + ", ".join(parts)
            )
    n_clauses = 4 * inst["n"]
    answer_size = 9 * inst["n"] + 1
    statement = f"""Connected odd-cycle transversal in a triangle-expanded graph

All graphs here are finite, simple, and undirected. A vertex set T is an
odd-cycle transversal if deleting T leaves a bipartite graph (equivalently, no
odd cycle). It is connected if the subgraph induced by T is connected.

The source graph H has the designated connector vertex C={inst['connector']},
{inst['n']} variable-pair gadgets, and {n_clauses} clause-triangle gadgets.
Each integer names one source vertex. Variable labels recur as attachment
targets; all variable and clause vertices themselves are pairwise distinct.

Variable pairs (the parenthetical order only defines the 0/1 convention):
{chr(10).join(pair_lines)}

Clause triangles are grouped into four-triangle blocks. A record a->b means
that a is a vertex of that triangle and {{a,b}} is an attachment edge:
{chr(10).join(block_lines)}

These tables define every source edge of H, as follows and with no others:
1. the edge joining the two vertices in each variable pair;
2. all three edges inside each listed clause triangle;
3. every listed attachment edge a->b; and
4. an edge from C to every other source vertex.

Construct G from H by retaining every source edge {{u,v}} and, for each such
edge, adding one fresh vertex q_{{u,v}} and the two edges {{u,q_{{u,v}}}} and
{{q_{{u,v}},v}}. All q vertices are distinct and there are no other vertices
or edges. Thus every source edge is the base of exactly one triangle in G.

Find exactly {answer_size} SOURCE vertices that form a connected odd-cycle
transversal of G. The set must contain C, exactly one vertex from each variable
pair, and exactly two vertices from each clause triangle. Do not output any q
vertex. Output the {answer_size} distinct base-10 integer labels in strictly
increasing order; order otherwise has no meaning, and repetitions are forbidden.
"""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    statement += """

Give your final answer inside <answer></answer> tags, as comma-separated base-10
integers. Example: <answer>3, 17, 42</answer>
Output nothing else inside the tags."""
    return statement


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    if not body:
        return []
    if body.startswith("[") and body.endswith("]"):
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            return None
        if isinstance(value, list) and all(
            isinstance(x, int) and not isinstance(x, bool) for x in value
        ):
            return value
        return None
    parts = [part.strip() for part in body.split(",")]
    if not parts or any(not re.fullmatch(r"-?\d+", part) for part in parts):
        return None
    try:
        return [int(part) for part in parts]
    except ValueError:
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check the claimed transversal without consulting ``inst['answer']``."""
    if not isinstance(answer, list):
        return False, "answer_not_a_list"
    if not answer:
        return False, "empty_answer"
    expected = 9 * inst["n"] + 1
    if len(answer) != expected:
        return False, f"wrong_length_expected_{expected}"
    if any(not isinstance(x, int) or isinstance(x, bool) for x in answer):
        return False, "non_integer_label"
    if len(set(answer)) != len(answer):
        return False, "duplicate_label"
    if answer != sorted(answer):
        return False, "labels_not_strictly_increasing"

    allowed = {inst["connector"]}
    for pair in inst["variable_pairs"]:
        allowed.update(pair)
    for clause in _all_clauses(inst):
        allowed.update(clause["nodes"])
    if any(vertex not in allowed for vertex in answer):
        return False, "unknown_or_expansion_vertex"
    chosen = set(answer)
    if inst["connector"] not in chosen:
        return False, "mandatory_connector_missing"

    for pair_index, pair in enumerate(inst["variable_pairs"]):
        if sum(vertex in chosen for vertex in pair) != 1:
            return False, f"variable_pair_quota_{pair_index}"
    for clause_index, clause in enumerate(_all_clauses(inst)):
        selected = [node in chosen for node in clause["nodes"]]
        if sum(selected) != 2:
            return False, f"clause_triangle_quota_{clause_index}"
        omitted = selected.index(False)
        if clause["attachments"][omitted] not in chosen:
            return False, f"uncovered_attachment_{clause_index}_{omitted}"

    # The quotas cover every variable edge and clause-triangle edge. The test
    # above covers the only attachment whose clause endpoint is omitted, and C
    # covers every universal edge. The set is connected through C. After the
    # triangle expansion and deletion, every remaining q has at most one
    # neighbor, so the remainder is a forest and therefore bipartite.
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    selected = {inst["connector"]}
    for pair in inst["variable_pairs"]:
        selected.add(pair[rng.randrange(2)])
    for clause in _all_clauses(inst):
        omitted = rng.randrange(3)
        selected.update(
            node for index, node in enumerate(clause["nodes"])
            if index != omitted
        )
    return sorted(selected)


def search_space(inst: dict) -> int | None:
    return (2 ** inst["n"]) * (3 ** (4 * inst["n"]))


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 200_000:
        return None
    count = 0
    for pair_bits in itertools.product((0, 1), repeat=inst["n"]):
        if verify(inst, _answer_from_assignment(inst, list(pair_bits)))[0]:
            count += 1
    return count


def _source_roles(inst: dict) -> dict[int, int]:
    roles = {inst["connector"]: 0}
    for pair in inst["variable_pairs"]:
        for vertex in pair:
            roles[vertex] = 1
    for clause in _all_clauses(inst):
        for vertex in clause["nodes"]:
            roles[vertex] = 2
    return roles


def canonical_key(inst: dict) -> str:
    """Return a label-invariant stable colored 1-WL quotient signature."""
    roles = _source_roles(inst)
    adjacency = {vertex: set() for vertex in roles}
    for u, v in inst["source_edges"]:
        adjacency[u].add(v)
        adjacency[v].add(u)
    colors = dict(roles)
    for _ in range(len(colors)):
        signatures = {
            vertex: (colors[vertex], tuple(sorted(colors[w] for w in neighbors)))
            for vertex, neighbors in adjacency.items()
        }
        palette = {
            signature: index
            for index, signature in enumerate(sorted(set(signatures.values())))
        }
        new_colors = {
            vertex: palette[signature] for vertex, signature in signatures.items()
        }
        old_cells = {frozenset(v for v, c in colors.items() if c == cell)
                     for cell in set(colors.values())}
        new_cells = {frozenset(v for v, c in new_colors.items() if c == cell)
                     for cell in set(new_colors.values())}
        colors = new_colors
        if old_cells == new_cells:
            break

    cell_sizes = [0] * (max(colors.values()) + 1)
    for color in colors.values():
        cell_sizes[color] += 1
    quotient: dict[tuple[int, int], int] = {}
    for u, v in inst["source_edges"]:
        key = _edge(colors[u], colors[v])
        quotient[key] = quotient.get(key, 0) + 1
    payload = {
        "n": inst["n"],
        "cell_sizes": cell_sizes,
        "quotient_edges": [list(key) + [value]
                           for key, value in sorted(quotient.items())],
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params: dict) -> dict | str | None:
    n = int(params.get("n", 8))
    # Every new parity equation necessarily adds eight clause-cover vertices;
    # there is no honest fixed-witness-length axis for this construction.
    if n < 26:
        return {"n": 26}
    if n < 28:
        return {"n": 28}
    return "cap_bound"


def _decode_parity_system(inst: dict, validate: bool = True):
    """Decode displayed four-clause blocks into GF(2) equations."""
    node_to_varbit = {}
    for variable, pair in enumerate(inst["variable_pairs"]):
        node_to_varbit[pair[0]] = (variable, 0)
        node_to_varbit[pair[1]] = (variable, 1)
    equations = []
    decode_xors = 0
    for block in inst["parity_blocks"]:
        bad_assignments = []
        support = None
        for clause in block:
            literals = [node_to_varbit[node] for node in clause["attachments"]]
            literal_map = {variable: truth for variable, truth in literals}
            variables = tuple(sorted(literal_map))
            if len(variables) != 3 or (support is not None and variables != support):
                raise ValueError("malformed parity block")
            support = variables
            bad_assignments.append(tuple(1 - literal_map[v] for v in variables))
        representative = bad_assignments[0]
        bad_parity = representative[0] ^ representative[1] ^ representative[2]
        decode_xors += 2
        if validate:
            parities = []
            for bits in bad_assignments[1:]:
                parities.append(bits[0] ^ bits[1] ^ bits[2])
                decode_xors += 2
            if (
                len(set(bad_assignments)) != 4
                or any(parity != bad_parity for parity in parities)
            ):
                raise ValueError("block is not a three-variable parity encoding")
        equations.append((support, 1 ^ bad_parity))
        decode_xors += 1
    return equations, decode_xors


def _answer_from_assignment(inst: dict, bits: list[int]) -> list[int]:
    selected = {inst["connector"]}
    for variable, pair in enumerate(inst["variable_pairs"]):
        selected.add(pair[bits[variable]])
    for clause in _all_clauses(inst):
        omitted = next(
            (i for i, attachment in enumerate(clause["attachments"])
             if attachment in selected),
            None,
        )
        if omitted is None:
            # Keep the right shape; verify will report the semantic failure.
            omitted = 0
        selected.update(
            node for i, node in enumerate(clause["nodes"]) if i != omitted
        )
    return sorted(selected)


def _gaussian_solution(inst: dict) -> tuple[list[int], dict[str, int]]:
    equations, decode_xors = _decode_parity_system(inst)
    n = inst["n"]
    rows = []
    for support, rhs in equations:
        mask = 0
        for variable in support:
            mask |= 1 << variable
        rows.append([mask, rhs])
    row = 0
    scalar_xors = decode_xors
    for column in range(n):
        pivot = next(
            (r for r in range(row, n) if (rows[r][0] >> column) & 1),
            None,
        )
        if pivot is None:
            continue
        rows[row], rows[pivot] = rows[pivot], rows[row]
        for other in range(n):
            if other != row and ((rows[other][0] >> column) & 1):
                rows[other][0] ^= rows[row][0]
                rows[other][1] ^= rows[row][1]
                # One packed xor represents n coefficient xors plus the RHS.
                scalar_xors += n + 1
        row += 1
    if row != n:
        raise ValueError("decoded parity system is singular")
    solution = [0] * n
    for mask, rhs in rows:
        column = (mask & -mask).bit_length() - 1
        if mask != 1 << column:
            raise ValueError("elimination did not reach reduced form")
        solution[column] = rhs
    return _answer_from_assignment(inst, solution), {
        "decoded_equations": len(equations),
        "scalar_gf2_xors": scalar_xors,
    }


def _peeling_solution(inst: dict) -> tuple[list[int], dict[str, int]]:
    # Once the four-clause parity identity has been recognized, one clause in
    # each block determines the RHS; inspecting the other three is structural
    # pattern recognition, not further exact arithmetic.
    equations, decode_xors = _decode_parity_system(inst, validate=False)
    remaining = [set(support) for support, _ in equations]
    rhs_values = [rhs for _, rhs in equations]
    active_eq = set(range(len(equations)))
    active_vars = set(range(inst["n"]))
    peeled = []
    while len(active_vars) > 4:
        incidence = {variable: [] for variable in active_vars}
        for equation in active_eq:
            for variable in remaining[equation]:
                if variable in active_vars:
                    incidence[variable].append(equation)
        leaf = next(
            (v for v in sorted(active_vars) if len(incidence[v]) == 1),
            None,
        )
        if leaf is None:
            raise ValueError("no perfect elimination ordering")
        equation = incidence[leaf][0]
        peeled.append((leaf, equation))
        active_vars.remove(leaf)
        active_eq.remove(equation)

    if len(active_eq) != 4:
        raise ValueError("unexpected parity core")
    core = sorted(active_vars)
    rhs_by_missing = {}
    for equation in active_eq:
        support = remaining[equation] & active_vars
        missing = set(core) - support
        if len(support) != 3 or len(missing) != 1:
            raise ValueError("unexpected core incidence")
        rhs_by_missing[missing.pop()] = rhs_values[equation]
    if set(rhs_by_missing) != set(core):
        raise ValueError("incomplete parity core")

    core_parity = 0
    exact_xors = decode_xors
    for index, variable in enumerate(core):
        core_parity ^= rhs_by_missing[variable]
        if index:
            exact_xors += 1
    solution = {}
    for variable in core:
        solution[variable] = core_parity ^ rhs_by_missing[variable]
        exact_xors += 1
    for leaf, equation in reversed(peeled):
        known = [v for v in remaining[equation] if v != leaf]
        solution[leaf] = (
            rhs_values[equation] ^ solution[known[0]] ^ solution[known[1]]
        )
        exact_xors += 2
    bits = [solution[v] for v in range(inst["n"])]
    return _answer_from_assignment(inst, bits), {
        "decoded_equations": len(equations),
        "scalar_gf2_xors": exact_xors,
        "peeled_variables": len(peeled),
    }


def _dpll_solution(inst: dict) -> tuple[list[int] | None, dict[str, int]]:
    """Run ordinary DPLL with unit propagation on the displayed 3-clauses."""
    node_to_varbit = {}
    for variable, pair in enumerate(inst["variable_pairs"]):
        node_to_varbit[pair[0]] = (variable, 0)
        node_to_varbit[pair[1]] = (variable, 1)
    clauses = [
        [node_to_varbit[node] for node in clause["attachments"]]
        for clause in _all_clauses(inst)
    ]
    n = inst["n"]
    stats = {"nodes": 0, "decisions": 0, "unit_propagations": 0,
             "literal_checks": 0}

    def recurse(assignment):
        stats["nodes"] += 1
        assignment = list(assignment)
        while True:
            changed = False
            for clause in clauses:
                satisfied = False
                unassigned = []
                for variable, truth in clause:
                    stats["literal_checks"] += 1
                    if assignment[variable] is None:
                        unassigned.append((variable, truth))
                    elif assignment[variable] == truth:
                        satisfied = True
                        break
                if satisfied:
                    continue
                if not unassigned:
                    return None
                if len(unassigned) == 1:
                    variable, truth = unassigned[0]
                    if assignment[variable] is None:
                        assignment[variable] = truth
                        stats["unit_propagations"] += 1
                        changed = True
                    elif assignment[variable] != truth:
                        return None
            if not changed:
                break
        if all(value is not None for value in assignment):
            return assignment

        occurrence = [0] * n
        for clause in clauses:
            if any(
                assignment[variable] == truth
                for variable, truth in clause
                if assignment[variable] is not None
            ):
                continue
            for variable, _ in clause:
                if assignment[variable] is None:
                    occurrence[variable] += 1
        variable = max(
            (v for v in range(n) if assignment[v] is None),
            key=lambda v: occurrence[v],
        )
        for truth in (0, 1):
            stats["decisions"] += 1
            branch = list(assignment)
            branch[variable] = truth
            result = recurse(branch)
            if result is not None:
                return result
        return None

    bits = recurse([None] * n)
    if bits is None:
        return None, stats
    return _answer_from_assignment(inst, bits), stats


def _attack_outlier_degree(inst: dict) -> list[int]:
    degree = {vertex: 0 for vertex in _source_roles(inst)}
    for u, v in inst["source_edges"]:
        degree[u] += 1
        degree[v] += 1
    bits = []
    for pair in inst["variable_pairs"]:
        score0 = (degree[pair[0]], -pair[0])
        score1 = (degree[pair[1]], -pair[1])
        bits.append(0 if score0 >= score1 else 1)
    return _answer_from_assignment(inst, bits)


def _attack_clause_greedy(inst: dict) -> list[int]:
    node_to_varbit = {}
    for variable, pair in enumerate(inst["variable_pairs"]):
        node_to_varbit[pair[0]] = (variable, 0)
        node_to_varbit[pair[1]] = (variable, 1)
    clauses = list(_all_clauses(inst))
    bits = [None] * inst["n"]
    for variable in range(inst["n"]):
        scores = [0, 0]
        for clause in clauses:
            literals = [node_to_varbit[node] for node in clause["attachments"]]
            if any(
                bits[v] == truth for v, truth in literals if bits[v] is not None
            ):
                continue
            for v, truth in literals:
                if v == variable:
                    scores[truth] += 1
        bits[variable] = 0 if scores[0] >= scores[1] else 1
    return _answer_from_assignment(inst, bits)


def _attack_one_pass_parity_repair(inst: dict) -> list[int]:
    """Decode the blocks but make only one cheap displayed-order repair pass."""
    equations, _ = _decode_parity_system(inst, validate=False)
    bits = [0] * inst["n"]
    for support, rhs in equations:
        if _xor(bits[variable] for variable in support) != rhs:
            bits[support[-1]] ^= 1
    return _answer_from_assignment(inst, bits)


def _attack_random_restart(
    inst: dict, rng: random.Random, restarts: int = 256
) -> list[int]:
    candidate = random_candidate(inst, rng)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return candidate


def _reordered_instance(inst: dict, seed: int) -> dict:
    rng = random.Random(seed)
    out = {key: value for key, value in inst.items() if key != "answer"}
    out["variable_pairs"] = [list(pair) for pair in inst["variable_pairs"]]
    rng.shuffle(out["variable_pairs"])
    out["parity_blocks"] = []
    for block in inst["parity_blocks"]:
        new_block = []
        for clause in block:
            order = [0, 1, 2]
            rng.shuffle(order)
            new_block.append({
                "nodes": [clause["nodes"][i] for i in order],
                "attachments": [clause["attachments"][i] for i in order],
            })
        rng.shuffle(new_block)
        out["parity_blocks"].append(new_block)
    rng.shuffle(out["parity_blocks"])
    out["source_edges"] = [list(edge) for edge in inst["source_edges"]]
    rng.shuffle(out["source_edges"])
    out["answer"] = list(inst["answer"])
    return out


def _relabeled_instance(inst: dict, seed: int) -> dict:
    rng = random.Random(seed)
    old_labels = sorted(_source_roles(inst))
    new_labels = list(range(10_000, 10_000 + len(old_labels)))
    rng.shuffle(new_labels)
    mapping = dict(zip(old_labels, new_labels))
    out = {key: value for key, value in inst.items() if key != "answer"}
    out["connector"] = mapping[inst["connector"]]
    out["variable_pairs"] = [
        [mapping[pair[0]], mapping[pair[1]]] for pair in inst["variable_pairs"]
    ]
    out["parity_blocks"] = [
        [
            {
                "nodes": [mapping[node] for node in clause["nodes"]],
                "attachments": [mapping[node] for node in clause["attachments"]],
            }
            for clause in block
        ]
        for block in inst["parity_blocks"]
    ]
    out["source_edges"] = [
        list(_edge(mapping[u], mapping[v])) for u, v in inst["source_edges"]
    ]
    out["answer"] = sorted(mapping[vertex] for vertex in inst["answer"])
    return out


def selftest() -> dict:
    report: dict = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    g1_checks = 0
    g1_failures = []
    json_checks = 0
    for preset, parameters in DIFFICULTY.items():
        for seed in range(5):
            inst = make_instance(seed=seed, **parameters)
            ok, reason = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append(f"{preset}:{seed}:{reason}")
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_checks += 1
    report["G1_planted_verifies"] = {
        "pass": not g1_failures and json_checks == g1_checks,
        "checks": g1_checks,
        "json_native_checks": json_checks,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=424242, **ship_params)
    answer = list(inst["answer"])
    corruptions = {
        "drop_one": answer[:-1],
        "swap_two": answer[:1] + [answer[2], answer[1]] + answer[3:],
        "duplicate": answer[:-2] + [answer[-2], answer[-2]],
        "empty": [],
        "out_of_range": [-1] + answer[1:],
    }
    corruption_results = {
        name: verify(inst, value) for name, value in corruptions.items()
    }
    reasons = [reason for ok, reason in corruption_results.values() if not ok]
    report["G2_rejects_corruption"] = {
        "pass": (
            all(not ok for ok, _ in corruption_results.values())
            and len(set(reasons)) == len(corruptions)
        ),
        "cases": {
            name: {"accepted": ok, "reason": reason}
            for name, (ok, reason) in corruption_results.items()
        },
    }

    model_style = (
        "The connector covers all universal source edges.\n```text\n"
        f"<answer>{_answer_text(answer)}</answer>\n```\n"
        "The remaining choices cover every attachment."
    )
    parsed = parse_answer(model_style)
    render_example = parse_answer(render(inst))
    report["G3_round_trip"] = {
        "pass": parsed == answer and render_example is not None,
        "realistic_response_round_trips": parsed == answer,
        "renderer_example_parses": render_example is not None,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    samples = 200_000
    guess_rng = random.Random(0x170608050)
    hits = 0
    for _ in range(samples):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    space = search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "structure_aware_space": space,
        "sampling_prior": (
            "uniform over one choice from every variable pair and, independently, "
            "one omitted vertex from every clause triangle; this enforces every "
            "stated shape constraint but not semantic attachment coverage"
        ),
    }

    start = time.perf_counter()
    reference, reference_stats = _gaussian_solution(inst)
    reference_wall = time.perf_counter() - start
    exact_solution_count = 3 ** inst["n"]
    exact_fraction = exact_solution_count / space
    demo_inst = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_assignment_count = sum(
        verify(demo_inst, _answer_from_assignment(demo_inst, list(bits)))[0]
        for bits in itertools.product((0, 1), repeat=demo_inst["n"])
    )
    report["G5_density_and_baseline"] = {
        "pass": (
            verify(inst, reference)[0]
            and exact_fraction < 1e-6
            and demo_assignment_count == 1
        ),
        "shipping_exact_solution_count": exact_solution_count,
        "shipping_exact_solution_fraction": exact_fraction,
        "shipping_structure_aware_space": space,
        "shipping_sampled_valid_hits": hits,
        "shipping_density_samples": samples,
        "demo_bruteforce_assignment_projection_count": demo_assignment_count,
        "enumerate_all_result": enumerate_all(demo_inst),
        "baseline_wall_seconds": round(reference_wall, 6),
        "baseline_scalar_gf2_xors": reference_stats["scalar_gf2_xors"],
        "baseline_decoded_equations": reference_stats["decoded_equations"],
        "count_justification": (
            "the nonsingular parity system has one variable assignment; in each "
            "four-clause parity block three clauses have one true literal and "
            "one clause has three, giving exactly 3^n accepted output lists"
        ),
    }

    attacks = {
        "outlier_incidence_degree": {"successes": 0, "attempts": 0},
        "greedy_clause_satisfaction": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
        "in_context_one_pass_parity_repair": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_times = []
    reference_operations = []
    compact_successes = 0
    compact_operations = []
    dpll_successes = 0
    dpll_times = []
    dpll_nodes = []
    dpll_literal_checks = []
    for seed in range(8100, 8108):
        attacked = make_instance(seed=seed, **ship_params)
        candidates = {
            "outlier_incidence_degree": _attack_outlier_degree(attacked),
            "greedy_clause_satisfaction": _attack_clause_greedy(attacked),
            "random_restart_256": _attack_random_restart(
                attacked, random.Random(seed ^ 0xC0FFEE), 256
            ),
            "in_context_one_pass_parity_repair": (
                _attack_one_pass_parity_repair(attacked)
            ),
        }
        for name, candidate in candidates.items():
            attacks[name]["attempts"] += 1
            if verify(attacked, candidate)[0]:
                attacks[name]["successes"] += 1
        t0 = time.perf_counter()
        candidate, stats = _gaussian_solution(attacked)
        reference_times.append(time.perf_counter() - t0)
        reference_operations.append(stats["scalar_gf2_xors"])
        if verify(attacked, candidate)[0]:
            reference_successes += 1
        compact, compact_stats = _peeling_solution(attacked)
        compact_operations.append(compact_stats["scalar_gf2_xors"])
        if verify(attacked, compact)[0]:
            compact_successes += 1
        dpll_start = time.perf_counter()
        dpll_candidate, dpll_stats = _dpll_solution(attacked)
        dpll_times.append(time.perf_counter() - dpll_start)
        dpll_nodes.append(dpll_stats["nodes"])
        dpll_literal_checks.append(dpll_stats["literal_checks"])
        if dpll_candidate is not None and verify(attacked, dpll_candidate)[0]:
            dpll_successes += 1
    all_failed = all(result["successes"] == 0 for result in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": (
            all_failed and reference_successes == 8
            and compact_successes == 8 and dpll_successes == 8
        ),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "decode parity blocks, then Gaussian elimination over GF(2)",
            "complexity": "O(n^3) scalar GF(2) operations",
            "median_wall_clock_sec": round(statistics.median(reference_times), 6),
            "median_operations": int(statistics.median(reference_operations)),
            "operation_definition": "one scalar GF(2) XOR",
            "solves": f"{reference_successes}/8, as expected",
        },
        "compact_route_validation": {
            "name": "incidence peeling and four-variable core identity",
            "median_exact_operations": int(statistics.median(compact_operations)),
            "solves": f"{compact_successes}/8, as expected",
        },
        "additional_domain_algorithm": {
            "name": "DPLL with unit propagation and occurrence branching",
            "complexity": "O(2^n * n) worst case",
            "median_wall_clock_sec": round(statistics.median(dpll_times), 6),
            "median_nodes": int(statistics.median(dpll_nodes)),
            "median_literal_checks": int(statistics.median(dpll_literal_checks)),
            "solves": f"{dpll_successes}/8, as expected",
        },
    }

    doubled_params = {"n": ship_params["n"] * 2}
    doubled = make_instance(seed=77, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > space,
        "shipping_n": ship_params["n"],
        "doubled_n": doubled_params["n"],
        "shipping_space_bits": space.bit_length() - 1,
        "doubled_space_bits": search_space(doubled).bit_length() - 1,
        "doubled_verify_reason": doubled_reason,
        "note": (
            "the doubled build demonstrates scaling; it exceeds the output "
            "cap and is not a shipping preset"
        ),
    }

    invariant_checks = 0
    carried_checks = 0
    keys = []
    for seed in range(9200, 9220):
        original = make_instance(seed=seed, **ship_params)
        key = canonical_key(original)
        keys.append(key)
        reordered = _reordered_instance(original, seed ^ 0xABC)
        relabeled = _relabeled_instance(original, seed ^ 0xDEF)
        composed = _reordered_instance(relabeled, seed ^ 0x123)
        for transformed in (reordered, relabeled, composed):
            invariant_checks += 1
            if canonical_key(transformed) == key:
                carried_checks += int(verify(transformed, transformed["answer"])[0])
    report["G8_canonical_key"] = {
        "pass": (
            invariant_checks == 60
            and carried_checks == 60
            and len(set(keys)) == 20
        ),
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_distinct_keys": len(set(keys)),
        "unrelated_instances": 20,
        "transformations": [
            "variable/block/clause/triangle/input-edge reorder",
            "arbitrary source-vertex relabeling with carried witness",
            "arbitrary relabeling composed with all input reorderings",
        ],
        "canonicalization_strength": "stable colored 1-WL quotient invariant",
    }

    answer_blob = json.dumps(inst["answer"])
    answer_chars = len(answer_blob)
    answer_atoms = len(inst["answer"])
    answer_tokens = math.ceil(answer_chars / 4)
    largest_labels = list(range(inst["source_vertex_count"] - answer_atoms,
                                inst["source_vertex_count"]))
    worst_case_answer_chars = len(json.dumps(largest_labels))
    worst_case_answer_tokens = math.ceil(worst_case_answer_chars / 4)
    compact, compact_stats = _peeling_solution(inst)
    intended_ops = compact_stats["scalar_gf2_xors"]
    arms = G9_RESULTS["arms"]
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    if hinted["attempts"] and placebo["attempts"]:
        hinted_minus_placebo = (
            hinted["solved"] / hinted["attempts"]
            - placebo["solved"] / placebo["attempts"]
        )
    else:
        hinted_minus_placebo = None
    within_caps = answer_chars <= 2000 and answer_atoms <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        # Since 2026-09-05 the three arms, including the hinted verdict, are
        # diagnostic only. G9 gates only the answer-size and intended-route caps.
        "pass": within_caps and verify(inst, compact)[0],
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_RESULTS.get("hinted_verdict", "pending"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_case_answer_chars,
        "worst_case_answer_tokens": worst_case_answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_ops,
        "caps_pass": within_caps,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
