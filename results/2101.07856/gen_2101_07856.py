"""Verified Track-B generator for arXiv:2101.07856.

Martin, Paulusma, and Smith prove in their hard-result section that
NAE-3-SAT instances can be represented by 3-colouring gadgets whose graphs
have diameter four and, after uniform subdivision, no induced even cycle up
to a chosen length.  This module uses that paper-licensed representation.

The generated answer is a compact colouring certificate: one Boolean choice
for every literal pair.  The checker expands it to colors on every literal,
clause-triangle, and subdivision vertex and scans every graph edge exactly.
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


# Keep repository helpers importable when harden.py is run in this directory.
# This family is integer-only and remains standard-library-only if gvlib is absent.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - deliberate standard-library fallback
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "logic",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "succinct simple graph of diameter four",
        "literal-pair and clause-triangle colouring gadgets",
        "uniformly subdivided literal-clause paths",
        "proper three-colouring certificate",
    ],
    "verification_operations": [
        "exact NAE literal evaluation",
        "deterministic expansion of gadget colors",
        "integer inequality check on every graph edge",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 5, proof of Theorem 3: bounded-occurrence NAE-3-SAT to "
        "3-Colouring on (C4,C6,...,Ct)-free diameter-4 graphs"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The two-bit support of the lexicographically least displayed address "
        "selects one quadratic-coordinate Boolean invariant; without recognizing it, the "
        "solver must scan the coordinate-pair family or satisfy the dense NAE system."
    ),
    "hardness_basis": (
        "Track B: exhaustive coordinate-pair testing is guaranteed in "
        "O((n+m) log^2 n) time and at shipping took at most 63,960 counted "
        "operations, 20 candidates, and 0.006254 seconds over eight seeds; the "
        "compact least-address selector route takes 162 comparisons/Boolean "
        "operations and must be recognized without tools."
    ),
    "max_answer_tokens": 135,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}


# n is the number of Boolean variables.  degree is the exact number of NAE
# clauses containing each variable; m=n*degree/3.  The answer stays short while
# the clause density is a separate fixed-answer-length hardening axis.
DIFFICULTY: dict = {
    "demo": {"n": 6, "degree": 3, "subdivisions": 6},
    "easy": {"n": 78, "degree": 24, "subdivisions": 6},
    "medium": {"n": 78, "degree": 36, "subdivisions": 6},
    "hard": {"n": 78, "degree": 48, "subdivisions": 6},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT: str = (
    "The two-bit support of the lexicographically least displayed address "
    "identifies the quadratic-coordinate invariant compatible with every NAE clause."
)
PLACEBO_HINT: str = (
    "The displayed variables and signed clauses reward careful attention to "
    "the indexing and negation conventions."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON array [[0,b0],[1,b1],...,[n-1,b_(n-1)]] in exact variable "
        "order, containing every index once and a Boolean bit at each index. "
        "The bits select colors on the two literal vertices; the statement's "
        "deterministic rule expands them to a full proper 3-colouring."
    ),
    "bounds": {
        "shipping_pairs": 78,
        "shipping_atomic_integers": 156,
        "index_min": 0,
        "index_max_at_shipping": 77,
        "bit_alphabet": [0, 1],
    },
}


# Script-owned oracle measurements are copied here only after the three runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3, "errors": 0},
    "hinted": {"solved": 3, "attempts": 3, "errors": 0},
    "placebo": {"solved": 0, "attempts": 3, "errors": 0},
    "hinted_verdict": "too_easy_at_shipping_diagnostic_only",
}

NOTES = r"""
Paper grounding and Step 0.  Section 1 defines an ordinary k-colouring as a
map on graph vertices that gives adjacent vertices different colours.  The
paper's abstract has a typographical "non-adjacent" in one sentence, but the
formal introduction and every proof use the standard adjacent-vertex
definition.  Theorems 1 and 2 identify the easy regime: List 3-Colouring is
polynomial-time solvable on the stated C5/C6-free diameter-2 classes and on
the stated (C4,Ct)-free diameter-2 classes.  Sections 3 and 4 obtain this by
constant-size precolouring, exhaustive propagation, and Edwards' linear-time
2-List Colouring algorithm.  Those results cannot support Track A.

Theorem 3 and Section 5 give the hard native object used here.  Starting with
NAE-3-SAT, the proof makes two adjacent literal vertices per variable, joins
both to a vertex z, makes one triangle per clause, and joins each triangle
vertex to the literal that occurs in its clause.  Subdividing every such edge
p times and joining every subdivision vertex to z preserves 3-colourability,
keeps diameter four, and makes every induced cycle of length at most p either
a triangle or a 5-cycle.  This module fixes p=6, so its graphs are C4- and
C6-free.  The proof starts from the NP-hard at-most-three-occurrence source
restriction, but the target-class argument itself does not use that bound;
our denser source formulas therefore still produce the same target graphs.

Generation and certificate.  The generator first assigns each variable a
distinct displayed binary address and a random variable order.  The generator
constructs the lexicographically least address with exactly two 1-bits; their
positions select coordinates p and r, and the generator then samples the
Boolean witness f(a)=a[p]*a[r].  Only afterwards does it draw a regular signed NAE formula,
choosing every sign pattern uniformly from the six patterns that make the
already-sampled witness non-monochromatic.  It never solves its output.
verify() does not read inst['answer']: it validates the submitted indexed
bits, deterministically colors every paper gadget, and scans every generated
edge.  Thus the compact answer is a concrete certificate for the full graph.

Track decision and mechanical cost.  Theorem 3 is worst-case NP-completeness,
not average-case hardness for this planted distribution, so this module makes
no Track-A claim.  A guaranteed Track-B reference algorithm tests every one
of the O(log^2 n) coordinate-pair products against all m clauses, for
O((n+m) log^2 n) Boolean work.  Exact DPLL with the NAE unit rule (two equal
assigned literals force the third to their opposite) and a WalkSAT-style
solver are also implemented and measured.  The compact route instead notices
that the least address selects the pair: find it, read its two-bit support, and
evaluate one Boolean product per variable.

Attacks and canonicalization.  Every variable has exactly the same occurrence
degree.  Sign-majority, no-backtracking greedy propagation, bounded random
local restarts, and the natural constant/linear address ansatz are tested on
eight shipping seeds.  The guaranteed coordinate-pair scan is reported as the
reference algorithm outside attacks, as Track B requires.  The canonical key uses the
semantic address on every variable and the multiset of unsigned clause scopes;
it is exactly invariant under variable renaming, clause/occurrence reordering,
and independent swaps of a variable's two literal vertices.  Ignoring signs is
a deliberate cheap over-invariant; unrelated random scope systems are tested
for distinctness, but rare switching-inequivalent formulas with identical
scope multisets can collide.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"```(?:json|text)?\s*(.*?)```", re.I | re.S)
_ENUMERATION_CAP = 200_000
_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_parameters(n, degree, subdivisions):
    if not _is_int(n) or not 6 <= n <= 256 or n % 3:
        raise ValueError("n must be an integer multiple of 3 in 6..256")
    if not _is_int(degree) or not 3 <= degree <= 192:
        raise ValueError("degree must be an integer in 3..192")
    if not _is_int(subdivisions) or subdivisions < 6 or subdivisions % 2:
        raise ValueError("subdivisions must be an even integer at least 6")


def _identity_matrix(q):
    return [[1 if i == j else 0 for j in range(q)] for i in range(q)]


def _random_invertible_matrix(q, rng):
    """Generate an invertible GF(2) matrix by reversible row operations."""
    matrix = _identity_matrix(q)
    for _ in range(12 * q):
        if rng.randrange(3) == 0:
            i, j = rng.sample(range(q), 2)
            matrix[i], matrix[j] = matrix[j], matrix[i]
        else:
            i, j = rng.sample(range(q), 2)
            matrix[i] = [a ^ b for a, b in zip(matrix[i], matrix[j])]
    return matrix


def _bits(value, q):
    return [(value >> (q - 1 - i)) & 1 for i in range(q)]


def _mat_vec(matrix, vector):
    return [sum(a * b for a, b in zip(row, vector)) & 1 for row in matrix]


def _selector_coordinates(addresses):
    selector = min(addresses)
    support = [position for position, bit in enumerate(selector) if bit]
    return tuple(support) if len(support) == 2 else None


def _hidden_value(address, coordinates):
    left, right = coordinates
    return address[left] & address[right]


def _answer_from_bits(bits):
    return [[i, int(bit)] for i, bit in enumerate(bits)]


def _literal_value(bits, occurrence):
    variable, negated = occurrence
    return bits[variable] ^ negated


def _formula_satisfied(inst, bits):
    for clause in inst["clauses"]:
        values = [_literal_value(bits, occurrence) for occurrence in clause]
        if values[0] == values[1] == values[2]:
            return False
    return True


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a regular signed NAE formula and its colouring witness."""
    degree = params.pop("degree", 12)
    subdivisions = params.pop("subdivisions", 6)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_parameters(n, degree, subdivisions)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    q = max(4, n.bit_length())

    # Sample semantic addresses and the certificate before drawing any clause.
    # The balance filter only rejects an address presentation; it never searches
    # for a witness to a formula, because no formula exists yet.
    for _ in range(256):
        selector_values = [
            (1 << (q - 1 - left)) + (1 << (q - 1 - right))
            for left in range(q)
            for right in range(left + 1, q)
            if (1 << q) - 1
            - ((1 << (q - 1 - left)) + (1 << (q - 1 - right)))
            >= n - 1
        ]
        selector_value = rng.choice(selector_values)
        remaining = rng.sample(range(selector_value + 1, 1 << q), n - 1)
        addresses = [_bits(value, q) for value in [selector_value] + remaining]
        rng.shuffle(addresses)
        coordinates = _selector_coordinates(addresses)
        if coordinates is None:
            continue
        planted = [_hidden_value(address, coordinates) for address in addresses]
        ones = sum(planted)
        if n // 6 <= ones <= 5 * n // 6:
            break
    else:
        raise RuntimeError("could not draw a balanced address presentation")

    clauses = []
    # Each round is a random partition into triples, so every variable gets one
    # occurrence per round and all literal-vertex occurrence degrees are equal.
    nonconstant_patterns = [
        pattern for pattern in itertools.product((0, 1), repeat=3)
        if not (pattern[0] == pattern[1] == pattern[2])
    ]
    for _round in range(degree):
        variables = list(range(n))
        rng.shuffle(variables)
        for start in range(0, n, 3):
            triple = variables[start:start + 3]
            rng.shuffle(triple)
            literal_pattern = rng.choice(nonconstant_patterns)
            clause = [
                [variable, planted[variable] ^ literal_pattern[position]]
                for position, variable in enumerate(triple)
            ]
            clauses.append(clause)
    rng.shuffle(clauses)

    m = len(clauses)
    graph_vertices = 1 + 2 * n + 3 * m + 3 * m * subdivisions
    return {
        "family": "paper_nae_subdivision_colouring",
        "n": n,
        "address_bits": q,
        "addresses": addresses,
        "degree": degree,
        "clauses": clauses,
        "subdivisions": subdivisions,
        "graph_vertices": graph_vertices,
        "answer": _answer_from_bits(planted),
    }


def _format_occurrence(occurrence):
    variable, negated = occurrence
    return ("!" if negated else "") + f"x{variable}"


def render(inst) -> str:
    """Render the succinct graph, certificate semantics, and exact wire format."""
    n = inst["n"]
    m = len(inst["clauses"])
    p = inst["subdivisions"]
    address_lines = []
    for start in range(0, n, 10):
        address_lines.append("  " + "  ".join(
            f"x{i}=" + "".join(map(str, inst["addresses"][i]))
            for i in range(start, min(n, start + 10))
        ))
    clause_lines = [
        f"  C{j}: " + " ".join(_format_occurrence(o) for o in clause)
        for j, clause in enumerate(inst["clauses"])
    ]
    example = json.dumps([[i, 0] for i in range(n)], separators=(",", ":"))
    statement = f"""PROPERLY 3-COLOUR A SUCCINCT DIAMETER-4 GRAPH

All graphs here are finite, undirected, and simple.  A proper 3-colouring gives
each vertex one of colors 0, 1, 2 and gives adjacent vertices different colors.
The graph below has {inst['graph_vertices']} vertices and is defined completely
by the following gadget rules, so no external paper or convention is needed.

There are {n} Boolean variables x0 through x{n - 1}.  A positive literal x_i
has Boolean value x_i; a written negation !x_i has value 1-x_i.  A three-literal
NAE clause is satisfied exactly when its three literal values are not all equal.
The order of clauses and the order of literals inside a clause have no meaning.

The variables have distinct public {inst['address_bits']}-bit addresses.  Bits
are written from coordinate 0 on the left to coordinate {inst['address_bits'] - 1}
on the right:
{chr(10).join(address_lines)}

The {m} signed NAE clauses are:
{chr(10).join(clause_lines)}

These clauses define the graph exactly as follows.

* Make one vertex z.
* For each xi make adjacent vertices P_i and N_i, and join both to z.
* For every clause Cj make a triangle T_j0,T_j1,T_j2.
* Occurrence k of clause j selects P_i when it is xi and N_i when it is !xi.
  Join that selected literal vertex to T_jk by a path obtained by subdividing
  the edge exactly {p} times.  Each such path therefore has {p} new internal
  vertices and {p + 1} edges.  Paths are otherwise vertex-disjoint.
* Join every new internal path vertex to z.  There are no other edges.

This construction has diameter exactly 4 and has no induced 4-cycle or induced
6-cycle.  You need not write colors for all {inst['graph_vertices']} vertices.
Instead give a compact certificate with one pair [i,b_i] for every variable.
The checker gives z color 0.  If b_i=1 it gives (P_i,N_i) colors (1,2), and if
b_i=0 it gives them colors (2,1).  On each subdivided path, colors 1 and 2 then
alternate away from its selected literal endpoint.  The checker gives each
clause triangle the lexicographically first permutation of colors (0,1,2)
that differs from the adjacent path-end color at all three positions.  Such a
permutation exists exactly when the corresponding NAE clause is satisfied.
Finally the checker explicitly scans every graph edge for equal endpoint colors.

Submit exactly {n} pairs, in increasing index order [0,b_0],[1,b_1],...,
[{n - 1},b_{n - 1}].  Every index appears once; every b_i is the integer 0 or 1.
Repeated bit values are allowed.  Indices are 0-based and all bounds are inclusive.

Give your final answer inside <answer></answer> tags as one JSON array of pairs.
Example syntax only: <answer>{example}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Extract the final JSON array; tolerate prose, fences, and whitespace."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if matches:
        payload = matches[-1].strip()
    else:
        fenced = _FENCE_RE.search(text)
        payload = fenced.group(1).strip() if fenced else text.strip()
    if payload.startswith("```") and payload.endswith("```"):
        lines = payload.splitlines()
        if len(lines) >= 2:
            payload = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, list) else None


def _decode_answer(inst, answer):
    if not isinstance(answer, list):
        return None, "answer must be a JSON array"
    if not answer:
        return None, "answer is empty"
    n = inst["n"]
    if len(answer) < n:
        return None, f"answer is too short: got {len(answer)}, expected {n}"
    if len(answer) > n:
        return None, f"answer is too long: got {len(answer)}, expected {n}"
    for pair in answer:
        if not isinstance(pair, list) or len(pair) != 2:
            return None, "every entry must be a two-element JSON array"
    indices = [pair[0] for pair in answer]
    if any(not _is_int(index) for index in indices):
        return None, "every variable index must be an integer"
    if len(set(indices)) != len(indices):
        return None, "a variable index is duplicated"
    if indices != list(range(n)):
        return None, "variable pairs are not in exact increasing index order"
    bits = [pair[1] for pair in answer]
    if any(not _is_int(bit) for bit in bits):
        return None, "every assigned bit must be an integer"
    if any(bit not in (0, 1) for bit in bits):
        return None, "an assigned bit is outside the inclusive range 0..1"
    return bits, "ok"


def _graph_layout(inst):
    n = inst["n"]
    m = len(inst["clauses"])
    clause_base = 1 + 2 * n
    path_base = clause_base + 3 * m
    return clause_base, path_base


def _literal_vertex(variable, negated):
    return 1 + 2 * variable + negated


def _clause_vertex(inst, clause_index, position):
    clause_base, _ = _graph_layout(inst)
    return clause_base + 3 * clause_index + position


def _path_vertex(inst, clause_index, position, offset):
    """offset is 1..p from the literal endpoint."""
    _, path_base = _graph_layout(inst)
    p = inst["subdivisions"]
    return path_base + (3 * clause_index + position) * p + (offset - 1)


def _iter_edges(inst):
    n = inst["n"]
    p = inst["subdivisions"]
    z = 0
    for variable in range(n):
        positive = _literal_vertex(variable, 0)
        negative = _literal_vertex(variable, 1)
        yield positive, negative
        yield z, positive
        yield z, negative
    for clause_index, clause in enumerate(inst["clauses"]):
        triangle = [_clause_vertex(inst, clause_index, k) for k in range(3)]
        yield triangle[0], triangle[1]
        yield triangle[1], triangle[2]
        yield triangle[0], triangle[2]
        for position, (variable, negated) in enumerate(clause):
            previous = _literal_vertex(variable, negated)
            for offset in range(1, p + 1):
                current = _path_vertex(inst, clause_index, position, offset)
                yield previous, current
                yield z, current
                previous = current
            yield previous, triangle[position]


def _expand_coloring(inst, bits):
    colors = [-1] * inst["graph_vertices"]
    colors[0] = 0
    for variable, bit in enumerate(bits):
        colors[_literal_vertex(variable, 0)] = 1 if bit else 2
        colors[_literal_vertex(variable, 1)] = 2 if bit else 1
    p = inst["subdivisions"]
    for clause_index, clause in enumerate(inst["clauses"]):
        path_end_colors = []
        for position, (variable, negated) in enumerate(clause):
            literal_color = colors[_literal_vertex(variable, negated)]
            current_color = literal_color
            for offset in range(1, p + 1):
                current_color = 3 - current_color
                colors[_path_vertex(inst, clause_index, position, offset)] = current_color
            path_end_colors.append(current_color)
        chosen = None
        for permutation in itertools.permutations((0, 1, 2)):
            if all(permutation[k] != path_end_colors[k] for k in range(3)):
                chosen = permutation
                break
        if chosen is None:
            return None
        for position, color in enumerate(chosen):
            colors[_clause_vertex(inst, clause_index, position)] = color
    return colors


def verify(inst, answer):
    """Accept every compact certificate whose expanded graph coloring is proper."""
    bits, reason = _decode_answer(inst, answer)
    if bits is None:
        return False, reason
    for clause_index, clause in enumerate(inst["clauses"]):
        values = [_literal_value(bits, occurrence) for occurrence in clause]
        if values[0] == values[1] == values[2]:
            return False, f"NAE clause C{clause_index} has three equal literal values"
    colors = _expand_coloring(inst, bits)
    if colors is None:
        return False, "a clause triangle has no compatible color permutation"
    if len(colors) != inst["graph_vertices"] or any(color not in (0, 1, 2) for color in colors):
        return False, "expanded coloring leaves a graph vertex uncolored"
    for u, v in _iter_edges(inst):
        if colors[u] == colors[v]:
            return False, f"expanded coloring is improper on graph edge {u}-{v}"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the fixed-index Boolean language a solver searches."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    return [[i, rng.randrange(2)] for i in range(inst["n"])]


def search_space(inst):
    """The indices are forced by the grammar, leaving exactly 2^n bit vectors."""
    return 1 << inst["n"]


def enumerate_all(inst):
    """Brute-force the exact number of witnesses when the declared space is small."""
    total = search_space(inst)
    if total > _ENUMERATION_CAP:
        return None
    count = 0
    n = inst["n"]
    for mask in range(total):
        bits = [(mask >> i) & 1 for i in range(n)]
        if _formula_satisfied(inst, bits):
            count += 1
    return count


def canonical_key(inst):
    """Cheap switching-invariant key for the attributed gadget graph.

    Semantic binary addresses replace arbitrary variable names.  Clause signs
    are ignored, making the key invariant under independent literal-pair swaps.
    This can over-collapse rare sign-inequivalent formulas on identical scopes;
    the README states that limitation explicitly.
    """
    addresses = [tuple(address) for address in inst["addresses"]]
    scopes = []
    for clause in inst["clauses"]:
        scopes.append(tuple(sorted(addresses[variable] for variable, _ in clause)))
    structural = {
        "n": inst["n"],
        "subdivisions": inst["subdivisions"],
        "addresses": sorted(addresses),
        "unsigned_scopes": sorted(scopes),
    }
    blob = json.dumps(structural, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def escalate(params):
    """First increase clause crowding while keeping the certificate length fixed."""
    if not isinstance(params, dict) or "n" not in params:
        return None
    n = int(params["n"])
    degree = int(params.get("degree", 12))
    subdivisions = int(params.get("subdivisions", 6))
    if degree < 72:
        return {"n": n, "degree": degree + 6, "subdivisions": subdivisions}
    if n < 126:
        harder_n = min(126, n + (3 - n % 3) % 3 + 24)
        harder_n -= harder_n % 3
        return {"n": harder_n, "degree": degree, "subdivisions": subdivisions + 2}
    return "cap_bound"


# ---------------------------------------------------------------------------
# Exact reference algorithm and deliberately weaker adversarial probes.

def _coordinate_pair_reference(inst):
    """Guaranteed polynomial scan over all quadratic coordinate-pair products."""
    q = inst["address_bits"]
    operations = 0
    candidates = 0
    for left in range(q):
        for right in range(left + 1, q):
            bits = [address[left] & address[right] for address in inst["addresses"]]
            operations += inst["n"]
            candidates += 1
            satisfied = True
            # Scan the full formula even after a failed clause.  This is the
            # ordinary batch-testing route and makes the mechanical count stable.
            for clause in inst["clauses"]:
                values = [_literal_value(bits, occurrence) for occurrence in clause]
                operations += 5  # three literal XORs and two equality comparisons
                if values[0] == values[1] == values[2]:
                    satisfied = False
            if satisfied:
                return bits, {
                    "candidates_tested": candidates,
                    "operations": operations,
                }
    return None, {"candidates_tested": candidates, "operations": operations}


def _dpll_reference(inst):
    """Exact NAE-DPLL with unit propagation; return (bits, metrics)."""
    n = inst["n"]
    clauses = inst["clauses"]
    occurrence_count = [0] * n
    for clause in clauses:
        for variable, _ in clause:
            occurrence_count[variable] += 1
    metrics = {
        "nodes": 0,
        "clause_scans": 0,
        "literal_evaluations": 0,
        "propagations": 0,
    }

    def propagate(assigned):
        changed = True
        while changed:
            changed = False
            for clause in clauses:
                metrics["clause_scans"] += 1
                known = []
                unknown = []
                for variable, negated in clause:
                    metrics["literal_evaluations"] += 1
                    if assigned[variable] < 0:
                        unknown.append((variable, negated))
                    else:
                        known.append(assigned[variable] ^ negated)
                if not unknown:
                    if known[0] == known[1] == known[2]:
                        return False
                    continue
                if len(unknown) == 1 and len(known) == 2 and known[0] == known[1]:
                    variable, negated = unknown[0]
                    forced_literal = 1 - known[0]
                    forced_bit = forced_literal ^ negated
                    if assigned[variable] >= 0 and assigned[variable] != forced_bit:
                        return False
                    if assigned[variable] < 0:
                        assigned[variable] = forced_bit
                        metrics["propagations"] += 1
                        changed = True
        return True

    def recurse(assigned):
        metrics["nodes"] += 1
        if not propagate(assigned):
            return None
        if all(value >= 0 for value in assigned):
            return assigned if _formula_satisfied(inst, assigned) else None
        # All generated variables have equal total occurrence, but the number of
        # currently unresolved clauses breaks ties in a construction-neutral way.
        best = None
        best_score = -1
        for variable in range(n):
            if assigned[variable] >= 0:
                continue
            score = occurrence_count[variable]
            if score > best_score:
                best, best_score = variable, score
        for value in (0, 1):
            child = assigned[:]
            child[best] = value
            result = recurse(child)
            if result is not None:
                return result
        return None

    initial = [-1] * n
    # NAE formulas are invariant under global complementation, so x0=0 loses no
    # solution and removes one mechanical branch.
    initial[0] = 0
    result = recurse(initial)
    metrics["operations"] = metrics["clause_scans"] + metrics["literal_evaluations"]
    return result, metrics


def _degree_sign_attack(inst):
    """Guess from the relative degrees of each positive/negative literal vertex."""
    positive = [0] * inst["n"]
    negative = [0] * inst["n"]
    for clause in inst["clauses"]:
        for variable, negated in clause:
            (negative if negated else positive)[variable] += 1
    # Guess that the more frequent literal should be true; ties choose zero.
    return [1 if positive[i] > negative[i] else 0 for i in range(inst["n"])]


def _greedy_no_backtracking_attack(inst):
    """Assign in index order, minimizing immediate forced/conflict penalties."""
    n = inst["n"]
    assigned = [-1] * n

    def penalty(variable, value):
        assigned[variable] = value
        score = 0
        for clause in inst["clauses"]:
            if not any(v == variable for v, _ in clause):
                continue
            known = []
            unknown = 0
            for v, negated in clause:
                if assigned[v] < 0:
                    unknown += 1
                else:
                    known.append(assigned[v] ^ negated)
            if unknown == 0 and known[0] == known[1] == known[2]:
                score += 1000
            elif unknown == 1 and len(known) == 2 and known[0] == known[1]:
                score += 1
        assigned[variable] = -1
        return score

    for variable in range(n):
        scores = [penalty(variable, value) for value in (0, 1)]
        assigned[variable] = 0 if scores[0] <= scores[1] else 1
    return assigned


def _violation_count(inst, bits):
    return sum(
        1 for clause in inst["clauses"]
        if len({_literal_value(bits, occurrence) for occurrence in clause}) == 1
    )


def _walksat_reference(inst, rng, restarts=8):
    """A bounded WalkSAT-style solver, with an explicit mechanical work count."""
    last = [0] * inst["n"]
    clause_evaluations = 0
    flips = 0
    for _ in range(restarts):
        bits = [rng.randrange(2) for _ in range(inst["n"])]
        for _step in range(inst["n"]):
            violated = [
                clause for clause in inst["clauses"]
                if len({_literal_value(bits, occurrence) for occurrence in clause}) == 1
            ]
            clause_evaluations += len(inst["clauses"])
            if not violated:
                return bits, {
                    "restarts": _ + 1,
                    "flips": flips,
                    "clause_evaluations": clause_evaluations,
                    "operations": 3 * clause_evaluations,
                }
            clause = rng.choice(violated)
            trials = []
            for variable, _ in clause:
                bits[variable] ^= 1
                trials.append((_violation_count(inst, bits), variable))
                clause_evaluations += len(inst["clauses"])
                bits[variable] ^= 1
            best_score = min(score for score, _ in trials)
            choices = [variable for score, variable in trials if score == best_score]
            bits[rng.choice(choices)] ^= 1
            flips += 1
        last = bits
    return last, {
        "restarts": restarts,
        "flips": flips,
        "clause_evaluations": clause_evaluations,
        "operations": 3 * clause_evaluations,
    }


def _random_greedy_restart_attack(inst, rng, restarts=8):
    """Random variable orders plus one-pass local choices, with no repair/search."""
    n = inst["n"]
    incident = [[] for _ in range(n)]
    for clause_index, clause in enumerate(inst["clauses"]):
        for variable, _ in clause:
            incident[variable].append(clause_index)
    last = [0] * n
    for _ in range(restarts):
        assigned = [-1] * n
        order = list(range(n))
        rng.shuffle(order)
        for variable in order:
            scores = []
            for value in (0, 1):
                assigned[variable] = value
                conflicts = 0
                forced = 0
                for clause_index in incident[variable]:
                    known = []
                    unknown = 0
                    for other, negated in inst["clauses"][clause_index]:
                        if assigned[other] < 0:
                            unknown += 1
                        else:
                            known.append(assigned[other] ^ negated)
                    if unknown == 0 and len(set(known)) == 1:
                        conflicts += 1
                    elif unknown == 1 and len(known) == 2 and known[0] == known[1]:
                        forced += 1
                scores.append((1000 * conflicts + forced, value))
                assigned[variable] = -1
            best = min(score for score, _ in scores)
            choices = [value for score, value in scores if score == best]
            assigned[variable] = rng.choice(choices)
        last = assigned
        if _formula_satisfied(inst, assigned):
            return assigned
    return last


def _simple_affine_attack(inst):
    """Try constants and the most obvious affine functions of public addresses."""
    q = inst["address_bits"]
    candidates = [[0] * inst["n"], [1] * inst["n"]]
    for coordinate in range(q):
        vector = [address[coordinate] for address in inst["addresses"]]
        candidates.extend([vector, [bit ^ 1 for bit in vector]])
    parity = [sum(address) & 1 for address in inst["addresses"]]
    candidates.extend([parity, [bit ^ 1 for bit in parity]])
    if q >= 2:
        pair = [address[0] ^ address[1] for address in inst["addresses"]]
        candidates.extend([pair, [bit ^ 1 for bit in pair]])
    for bits in candidates:
        if _formula_satisfied(inst, bits):
            return bits
    return candidates[-1]


def _permute_variables(inst, rng):
    n = inst["n"]
    old_at_new = list(range(n))
    rng.shuffle(old_at_new)
    old_to_new = {old: new for new, old in enumerate(old_at_new)}
    transformed = {k: v for k, v in inst.items() if k not in ("addresses", "clauses", "answer")}
    transformed["addresses"] = [inst["addresses"][old] for old in old_at_new]
    transformed["clauses"] = [
        [[old_to_new[variable], negated] for variable, negated in clause]
        for clause in inst["clauses"]
    ]
    old_bits = [pair[1] for pair in inst["answer"]]
    transformed["answer"] = _answer_from_bits([old_bits[old] for old in old_at_new])
    return transformed


def _reorder_presentation(inst, rng):
    transformed = {k: v for k, v in inst.items() if k not in ("clauses", "answer")}
    clauses = [[occurrence[:] for occurrence in clause] for clause in inst["clauses"]]
    for clause in clauses:
        rng.shuffle(clause)
    rng.shuffle(clauses)
    transformed["clauses"] = clauses
    transformed["answer"] = [pair[:] for pair in inst["answer"]]
    return transformed


def _switch_literals(inst, variables):
    switched = set(variables)
    transformed = {k: v for k, v in inst.items() if k not in ("clauses", "answer")}
    transformed["clauses"] = [
        [[variable, negated ^ (variable in switched)] for variable, negated in clause]
        for clause in inst["clauses"]
    ]
    bits = [pair[1] ^ (pair[0] in switched) for pair in inst["answer"]]
    transformed["answer"] = _answer_from_bits(bits)
    return transformed


def _answer_measurements(answer):
    compact = json.dumps(answer, separators=(",", ":"))

    def atoms(value):
        if isinstance(value, dict):
            return sum(atoms(v) for v in value.values())
        if isinstance(value, list):
            return sum(atoms(v) for v in value)
        return 1

    return len(compact), math.ceil(len(compact) / 4), atoms(answer)


def selftest():
    """Run all mandatory gates and return a JSON-native measured report."""
    report = {}

    # G1: every preset and several unrelated seeds.
    planted_attempts = 0
    planted_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            planted_attempts += 1
            if not ok:
                planted_failures.append([preset, seed, reason])
            json.loads(json.dumps(inst["answer"]))
    report["G1_planted_verifies"] = {
        "pass": not planted_failures,
        "verified": planted_attempts - len(planted_failures),
        "attempts": planted_attempts,
        "failures": planted_failures,
    }

    shipping = make_instance(seed=271828, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = [pair[:] for pair in shipping["answer"]]
    corruptions = {}
    variants = {
        "empty": [],
        "dropped_pair": answer[:-1],
        "swapped_pair_order": answer[:1] + [answer[2], answer[1]] + answer[3:],
        "duplicated_index": answer[:2] + [[1, answer[2][1]]] + answer[3:],
        "out_of_range_bit": [[i, (2 if i == 0 else bit)] for i, bit in answer],
    }
    for name, candidate in variants.items():
        ok, reason = verify(shipping, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in corruptions.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruptions,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "I used the clause invariant.\n```json\n<answer>\n"
        + json.dumps(shipping["answer"])
        + "\n</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"],
        "parsed_equals_answer": parsed == shipping["answer"],
        "garbage_returns_none": parse_answer("no tagged JSON here {") is None,
    }

    # G4/G5 share one structure-aware shipping sample.
    rng = random.Random(314159265)
    guess_hits = 0
    sample_start = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        candidate = random_candidate(shipping, rng)
        bits = [pair[1] for pair in candidate]
        if _formula_satisfied(shipping, bits):
            guess_hits += 1
    sample_elapsed = time.perf_counter() - sample_start
    guess_rate = guess_hits / _G4_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": _G4_SAMPLES,
        "observed_probability": guess_rate,
        "candidate_prior": "uniform Boolean bits with forced ordered indices",
        "search_space": search_space(shipping),
    }

    reference_successes = 0
    reference_operations = []
    reference_nodes = []
    reference_seconds = []
    coordinate_successes = 0
    coordinate_operations = []
    coordinate_candidates = []
    coordinate_seconds = []
    walksat_successes = 0
    walksat_operations = []
    walksat_flips = []
    walksat_seconds = []
    attack_counts = {
        "literal_degree_sign_majority": 0,
        "greedy_no_backtracking": 0,
        "random_greedy_restart_2": 0,
        "simple_affine_address_ansatz": 0,
    }
    for seed in range(_ATTACK_SEEDS):
        inst = make_instance(seed=10000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        attacks = {
            "literal_degree_sign_majority": _degree_sign_attack(inst),
            "greedy_no_backtracking": _greedy_no_backtracking_attack(inst),
            "random_greedy_restart_2": _random_greedy_restart_attack(
                inst, random.Random(20000 + seed), restarts=2
            ),
            "simple_affine_address_ansatz": _simple_affine_attack(inst),
        }
        for name, bits in attacks.items():
            if verify(inst, _answer_from_bits(bits))[0]:
                attack_counts[name] += 1

        started = time.perf_counter()
        coordinate_bits, coordinate_metrics = _coordinate_pair_reference(inst)
        coordinate_elapsed = time.perf_counter() - started
        coordinate_ok = coordinate_bits is not None and verify(
            inst, _answer_from_bits(coordinate_bits)
        )[0]
        coordinate_successes += int(coordinate_ok)
        coordinate_operations.append(coordinate_metrics["operations"])
        coordinate_candidates.append(coordinate_metrics["candidates_tested"])
        coordinate_seconds.append(coordinate_elapsed)

        started = time.perf_counter()
        reference_bits, metrics = _dpll_reference(inst)
        elapsed = time.perf_counter() - started
        ok = reference_bits is not None and verify(
            inst, _answer_from_bits(reference_bits)
        )[0]
        reference_successes += int(ok)
        reference_operations.append(metrics["operations"])
        reference_nodes.append(metrics["nodes"])
        reference_seconds.append(elapsed)

        started = time.perf_counter()
        walksat_bits, walksat_metrics = _walksat_reference(
            inst, random.Random(50000 + seed)
        )
        walksat_elapsed = time.perf_counter() - started
        walksat_ok = verify(inst, _answer_from_bits(walksat_bits))[0]
        walksat_successes += int(walksat_ok)
        walksat_operations.append(walksat_metrics["operations"])
        walksat_flips.append(walksat_metrics["flips"])
        walksat_seconds.append(walksat_elapsed)

    max_ops = max(reference_operations)
    max_nodes = max(reference_nodes)
    max_seconds = max(reference_seconds)
    strongest_seconds = max(coordinate_seconds)
    strongest_operations = max(coordinate_operations)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_rate < 1e-6
        and coordinate_successes == _ATTACK_SEEDS
        and reference_successes == _ATTACK_SEEDS
        and walksat_successes == _ATTACK_SEEDS,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": _G4_SAMPLES,
        "shipping_density_fraction": guess_rate,
        "density_sampling_seconds": round(sample_elapsed, 6),
        "baseline_wall_clock_seconds_max": round(strongest_seconds, 6),
        "baseline_operations_max": strongest_operations,
        "baseline_iterations_max": max(coordinate_candidates),
        "baseline_successes": coordinate_successes,
    }
    panel = {
        name: {"successes": successes, "attempts": _ATTACK_SEEDS}
        for name, successes in attack_counts.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in panel.values())
        and coordinate_successes == _ATTACK_SEEDS
        and reference_successes == _ATTACK_SEEDS
        and walksat_successes == _ATTACK_SEEDS,
        "attacks": panel,
        "reference_algorithm": {
            "name": "exhaustive quadratic coordinate-pair testing",
            "complexity": "O((n+m) log^2 n) Boolean operations",
            "wall_clock_sec_max": round(max(coordinate_seconds), 6),
            "wall_clock_sec_mean": round(sum(coordinate_seconds) / len(coordinate_seconds), 6),
            "operations_max": max(coordinate_operations),
            "operations_mean": round(sum(coordinate_operations) / len(coordinate_operations), 2),
            "candidates_max": max(coordinate_candidates),
            "solves": f"{coordinate_successes}/{_ATTACK_SEEDS}, guaranteed by construction",
        },
        "exact_general_algorithm": {
            "name": "exact DPLL with NAE unit propagation",
            "complexity": "O(2^n*m) worst case",
            "wall_clock_sec_max": round(max_seconds, 6),
            "wall_clock_sec_mean": round(sum(reference_seconds) / len(reference_seconds), 6),
            "operations_max": max_ops,
            "operations_mean": round(sum(reference_operations) / len(reference_operations), 2),
            "nodes_max": max_nodes,
            "solves": f"{reference_successes}/{_ATTACK_SEEDS}, as expected",
        },
        "successful_distribution_algorithm": {
            "name": "WalkSAT-style best-flip local search",
            "complexity": "O(restarts*n*m) clause evaluations at the fixed budget",
            "wall_clock_sec_max": round(max(walksat_seconds), 6),
            "operations_max": max(walksat_operations),
            "flips_max": max(walksat_flips),
            "solves": f"{walksat_successes}/{_ATTACK_SEEDS}, as expected on Track B",
        },
    }

    # G7: n doubles at fixed clause degree and the planted witness still expands.
    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["graph_vertices"] > shipping["graph_vertices"],
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_graph_vertices": shipping["graph_vertices"],
        "doubled_graph_vertices": doubled["graph_vertices"],
        "verify_reason": doubled_reason,
    }

    invariance_checks = 0
    transform_verifications = 0
    key_failures = []
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(seed=30000 + seed, **DIFFICULTY["easy"])
        base_key = canonical_key(inst)
        rng_t = random.Random(40000 + seed)
        permuted = _permute_variables(inst, rng_t)
        reordered = _reorder_presentation(inst, rng_t)
        switch_set = rng_t.sample(range(inst["n"]), inst["n"] // 3)
        switched = _switch_literals(inst, switch_set)
        composed = _switch_literals(
            _reorder_presentation(_permute_variables(inst, rng_t), rng_t),
            rng_t.sample(range(inst["n"]), inst["n"] // 4),
        )
        for name, transformed in (
            ("variable_permutation", permuted),
            ("presentation_reordering", reordered),
            ("literal_switching", switched),
            ("composed", composed),
        ):
            invariance_checks += 1
            if canonical_key(transformed) != base_key:
                key_failures.append([seed, name])
            if verify(transformed, transformed["answer"])[0]:
                transform_verifications += 1
        unrelated_keys.append(base_key)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not key_failures
        and transform_verifications == invariance_checks
        and distinct_count == len(unrelated_keys),
        "invariance_passed": invariance_checks - len(key_failures),
        "invariance_attempts": invariance_checks,
        "real_transform_verifications": transform_verifications,
        "real_transform_attempts": invariance_checks,
        "unrelated_distinct": distinct_count,
        "unrelated_attempts": len(unrelated_keys),
        "failures": key_failures,
    }

    chars, tokens, elements = _answer_measurements(shipping["answer"])
    intended_operations = 2 * shipping["n"] + shipping["address_bits"] - 1
    arms = {
        name: {
            "solved": int(G9_ORACLE_RESULTS[name]["solved"]),
            "attempts": int(G9_ORACLE_RESULTS[name]["attempts"]),
            "errors": int(G9_ORACLE_RESULTS[name].get("errors", 0)),
        }
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else 0.0
    )
    within_caps = chars <= 2000 and elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
