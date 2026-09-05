"""Verified cyclic instances of r-Multiple k-Orthogonal Vectors.

The family uses the exact intermediate problem defined in Section 3.2 of
Kunnemann and Redzic, arXiv:2409.08037.  Here r=1, so a witness chooses one
binary vector from every displayed set and their coordinatewise AND must be
zero.  The generator samples a Boolean assignment first, builds a full-rank
cyclic 3-XOR system around it, converts every XOR row into its four exact CNF
clauses, and splits the variables into small assignment blocks.  Each block
assignment is one vector.  The planted tuple is therefore known without
solving the generated instance.

Verification uses only the displayed vector construction and candidate row
indices.  It never reads ``inst["answer"]``.
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
        "the paper's r-Multiple k-Orthogonal Vectors instance at r=1",
        "sets of exactly specified binary vectors",
    ],
    "verification_operations": [
        "candidate-row range checks",
        "exact bitwise intersection of selected binary vectors",
        "zero comparison in every coordinate",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Clauses on the same variable triple are parity quartets whose two-variable "
        "overlaps form one hidden cycle; without recognizing that invariant, the "
        "instance presents a vast tuple space."
    ),
    "hardness_basis": (
        "Track B: this structured distribution is solved by XOR-quartet recovery "
        "plus O(n^3) Gauss-Jordan elimination; at the hard shipping preset "
        "(59 Boolean variables) it used at most 33,001 counted Boolean operations "
        "and averaged 0.0005--0.0046 seconds across repeated eight-seed local "
        "audits, while "
        "recognizing the tight cycle reduces the exact arithmetic to at most 298 "
        "Boolean operations."
    ),
    "max_answer_tokens": 26,
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
    "demo": {"n": 5, "block_bits": 2, "copies": 1},
    "easy": {"n": 23, "block_bits": 2, "copies": 1},
    "medium": {"n": 41, "block_bits": 4, "copies": 1},
    "hard": {"n": 59, "block_bits": 5, "copies": 1},
}
SHIPPING_DIFFICULTY = "hard"

if os.environ.get("GV_G9_SINGLE") == "1":
    DIFFICULTY = {SHIPPING_DIFFICULTY: dict(DIFFICULTY[SHIPPING_DIFFICULTY])}


STRUCTURAL_HINT = (
    "Clauses sharing one variable triple are parity quartets, and consecutive "
    "triples overlap along a single hidden cycle."
)
PLACEBO_HINT = (
    "Candidate rows and signed clauses reward careful attention to the stated "
    "indexing, formatting, and local conventions."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list with one zero-based local row index for each displayed vector "
        "set A_i; the index for A_i lies in [0, |A_i|-1], and repetition across "
        "different sets is allowed because row numbers are local."
    ),
    "bounds": {
        "length": "ceil(n/block_bits)",
        "row_bound": "2^(number of variables in that block)",
        "shipping_sets": 12,
        "shipping_max_row_exclusive": 32,
        "shipping_candidate_count": "2^59",
    },
}

NOTES = (
    "Definition 3.10 in Section 3.2 defines r-Multiple k-Orthogonal Vectors and "
    "states that r=1 is exactly k-OV; Lemma 3.11 maps those native objects to "
    "sparse multiple-domination graphs.  Lemma 3.15 gives a conditional "
    "full-product lower bound for general fixed-k instances with r<=k-2, while "
    "Theorem 1.1 gives the matrix-product algorithm for that domination regime, "
    "Theorem 1.3 treats r=k-1 through unbalanced clique, and Section 1 observes "
    "that r>=k is trivial.  None of those worst-case statements "
    "makes this growing-k cyclic-XOR distribution Track A: its certificate is found "
    "by XOR recovery and Gaussian elimination.  Here the answer is sampled first, "
    "cyclic XOR identities are composed, and each identity is represented by four "
    "clauses.  Complete assignment blocks make planted and decoy rows exactly "
    "symmetric.  Balanced parity quartets defeat literal-frequency and row-weight "
    "outliers; random block and row orders defeat visible-order guesses; greedy "
    "coverage and random restarts are measured; the reference Gauss-Jordan and "
    "plain-DPLL solvers succeed as Track B requires."
)


# Updated after the three script-owned hardening runs.  These are diagnostics,
# not assertions used by verify().
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "oracle_unreachable_http_403",
}


def _xor_clauses(variables, rhs):
    """Four 3-clauses exactly equivalent to XOR(variables) == rhs."""
    clauses = []
    for bits in itertools.product((0, 1), repeat=3):
        if (bits[0] ^ bits[1] ^ bits[2]) == rhs:
            continue
        # The clause below is false only at this wrong-parity assignment.
        clause = [v + 1 if bit == 0 else -(v + 1)
                  for v, bit in zip(variables, bits)]
        clauses.append(clause)
    return clauses


def _candidate_mask(variables, bits, clauses):
    partial = {v: bit for v, bit in zip(variables, bits)}
    mask = 0
    for ci, clause in enumerate(clauses):
        locally_true = False
        for literal in clause:
            variable = abs(literal) - 1
            if variable in partial:
                bit = partial[variable]
                if bit == (1 if literal > 0 else 0):
                    locally_true = True
                    break
        if not locally_true:
            mask |= 1 << ci
    return mask


def _rebuild_vectors(inst):
    clauses = inst["clauses"]
    return [
        [_candidate_mask(group["variables"], row, clauses)
         for row in group["rows"]]
        for group in inst["groups"]
    ]


def make_instance(n, seed=0, **params):
    """Inverse-generate a unique cyclic-XOR k-OV witness."""
    block_bits = int(params.get("block_bits", 4))
    copies = int(params.get("copies", 1))
    if not isinstance(n, int) or isinstance(n, bool) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if n % 3 == 0:
        raise ValueError("n must not be divisible by 3")
    if not isinstance(block_bits, int) or block_bits < 1 or block_bits > 8:
        raise ValueError("block_bits must be an integer in [1,8]")
    if not isinstance(copies, int) or copies < 1:
        raise ValueError("copies must be a positive integer")

    rng = random.Random(seed)
    planted_bits = [rng.randrange(2) for _ in range(n)]

    cycle = list(range(n))
    rng.shuffle(cycle)
    unique_clauses = []
    for i in range(n):
        triple = (cycle[i], cycle[(i + 1) % n], cycle[(i + 2) % n])
        rhs = (planted_bits[triple[0]] ^ planted_bits[triple[1]]
               ^ planted_bits[triple[2]])
        unique_clauses.extend(_xor_clauses(triple, rhs))

    clauses = []
    for clause in unique_clauses:
        for _ in range(copies):
            placed = list(clause)
            rng.shuffle(placed)
            clauses.append(placed)
    rng.shuffle(clauses)

    shuffled_variables = list(range(n))
    rng.shuffle(shuffled_variables)
    groups = []
    answer = []
    for start in range(0, n, block_bits):
        variables = shuffled_variables[start:start + block_bits]
        rows = [list(bits) for bits in itertools.product((0, 1), repeat=len(variables))]
        rng.shuffle(rows)
        target = [planted_bits[v] for v in variables]
        answer.append(rows.index(target))
        groups.append({"variables": variables, "rows": rows})

    inst = {
        "n": n,
        "r": 1,
        "k": len(groups),
        "block_bits": block_bits,
        "copies": copies,
        "clauses": clauses,
        "groups": groups,
        "answer": answer,
    }
    inst["vectors"] = _rebuild_vectors(inst)
    return inst


def render(inst):
    lines = [
        "Find a witness for this 1-Multiple k-Orthogonal Vectors instance.",
        "",
        "There are k ordered sets A_1,...,A_k of equal-length binary vectors.",
        "Choose exactly one vector from each set.  The choice is valid exactly",
        "when, in every coordinate, at least r=1 chosen vector has bit 0;",
        "equivalently, the coordinatewise Boolean AND of all chosen vectors is",
        "the all-zero vector.",
        "",
        "The vectors are specified exactly and compactly below.  Variables are",
        "Boolean.  A signed integer +j is variable x_j and -j is its negation;",
        "variables in clauses are 1-indexed.  Every clause is the OR of its three",
        "listed literals.  Each clause is one vector coordinate.  A row in A_i",
        "is a partial assignment to A_i's displayed variables, in that displayed",
        "order.  Its bit in a clause-coordinate is 0 iff one or more literals of",
        "that clause belonging to A_i is made true by the row; otherwise it is 1.",
        "Thus all vector bits are fixed by the data below, with no omitted edges,",
        "conditions, or conventions.",
        "",
        f"Number of variables n: {inst['n']}",
        f"Number of vector sets k: {inst['k']}",
        f"Number of coordinates (indexed clauses): {len(inst['clauses'])}",
        "",
        "Vector sets.  Local row indices are zero-based.  A bit string gives the",
        "partial assignment in the exact variable order printed for that set:",
    ]
    for gi, group in enumerate(inst["groups"], 1):
        variables = ",".join(str(v + 1) for v in group["variables"])
        rows = " ".join(
            f"{ri}:{''.join(map(str, row))}" for ri, row in enumerate(group["rows"])
        )
        lines.append(f"A_{gi} variables [{variables}] | {rows}")

    lines.extend(["", "Coordinates, one signed JSON triple per line:"])
    for ci, clause in enumerate(inst["clauses"], 1):
        lines.append(f"c{ci}: {json.dumps(clause, separators=(',', ':'))}")

    lines.extend([
        "",
        "Return a JSON list of exactly k local row indices, in A_1,...,A_k",
        "order.  The row for A_i must lie from 0 through |A_i|-1 inclusive.",
        "Row numbers are local, so repetitions across different sets are allowed;",
        "the order of the k output positions is mandatory.",
        "",
        "Give your final answer inside <answer></answer> tags, as a JSON list of integers.",
        "Example format for three sets: <answer>[2,0,3]</answer>",
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
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    bodies = list(reversed(matches))
    if not bodies:
        arrays = re.findall(r"\[[\s\d,+-]*\]", text, flags=re.DOTALL)
        bodies = list(reversed(arrays))
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
    k = inst["k"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) < k:
        return False, f"answer has too few row indices: expected {k}, got {len(answer)}"
    if len(answer) > k:
        return False, f"answer has too many row indices: expected {k}, got {len(answer)}"
    for gi, (row, vectors) in enumerate(zip(answer, inst["vectors"]), 1):
        if type(row) is not int:
            return False, f"row index for A_{gi} is not an integer"
        if row < 0 or row >= len(vectors):
            return False, (
                f"row index for A_{gi} is out of range: expected 0..{len(vectors)-1}, "
                f"got {row}"
            )
    return True, "ok"


def verify(inst, answer):
    ok, reason = _shape(inst, answer)
    if not ok:
        return False, reason
    uncovered = (1 << len(inst["clauses"])) - 1
    for gi, row in enumerate(answer):
        uncovered &= inst["vectors"][gi][row]
    if uncovered:
        first = (uncovered & -uncovered).bit_length()
        count = uncovered.bit_count()
        return False, (
            f"chosen vectors leave {count} coordinate(s) uncovered; "
            f"first is clause c{first}"
        )
    return True, "ok"


def random_candidate(inst, rng):
    return [rng.randrange(len(vectors)) for vectors in inst["vectors"]]


def search_space(inst):
    total = 1
    for vectors in inst["vectors"]:
        total *= len(vectors)
    return total


def enumerate_all(inst):
    space = search_space(inst)
    if space > 100_000:
        return None
    count = 0
    for candidate in itertools.product(*(range(len(v)) for v in inst["vectors"])):
        if verify(inst, list(candidate))[0]:
            count += 1
    return count


def _extract_equations(inst):
    """Recover one XOR rhs for each absolute-variable triple."""
    parities = {}
    patterns = {}
    counts = {}
    for clause in inst["clauses"]:
        key = tuple(sorted(abs(literal) - 1 for literal in clause))
        false_bits = {abs(literal) - 1: (0 if literal > 0 else 1)
                      for literal in clause}
        wrong_parity = 0
        signature = []
        for variable in key:
            wrong_parity ^= false_bits[variable]
            signature.append(false_bits[variable])
        rhs = wrong_parity ^ 1
        if key in parities and parities[key] != rhs:
            raise ValueError("inconsistent XOR quartet")
        parities[key] = rhs
        patterns.setdefault(key, set()).add(tuple(signature))
        counts[key] = counts.get(key, 0) + 1
    expected_copies = inst["copies"]
    for key, seen in patterns.items():
        if len(seen) != 4:
            raise ValueError(f"triple {key} is not a complete parity quartet")
        if counts[key] != 4 * expected_copies:
            raise ValueError(f"triple {key} has the wrong multiplicity")
    if len(parities) != inst["n"]:
        raise ValueError("wrong number of XOR equations")
    return parities


def _extract_equations_compact(inst):
    """Decode one representative per recognized quartet.

    For a three-literal clause from an XOR quartet, the equation's right-hand
    side is the parity of its positive signs.  Once clauses have been bucketed
    by absolute-variable triple, the other three representatives are redundant.
    """
    parities = {}
    for clause in inst["clauses"]:
        key = tuple(sorted(abs(literal) - 1 for literal in clause))
        if key not in parities:
            positive = [int(literal > 0) for literal in clause]
            parities[key] = positive[0] ^ positive[1] ^ positive[2]
    if len(parities) != inst["n"]:
        raise ValueError("wrong number of compact XOR equations")
    return parities


def _cycle_equation_order(equations):
    keys = list(equations)
    adjacency = {key: [] for key in keys}
    key_sets = {key: set(key) for key in keys}
    for i, left in enumerate(keys):
        for right in keys[i + 1:]:
            if len(key_sets[left] & key_sets[right]) == 2:
                adjacency[left].append(right)
                adjacency[right].append(left)
    if any(len(adjacency[key]) != 2 for key in keys):
        raise ValueError("equation-overlap graph is not one cycle")
    start = min(keys)
    order = [start]
    previous = None
    current = start
    while True:
        choices = [x for x in adjacency[current] if x != previous]
        if previous is None:
            nxt = min(choices)
        else:
            nxt = choices[0]
        if nxt == start:
            break
        if nxt in order:
            raise ValueError("overlap cycle closes early")
        order.append(nxt)
        previous, current = current, nxt
    if len(order) != len(keys):
        raise ValueError("overlap graph is disconnected")
    return order


def _ordered_cycle_data(inst, *, compact=False):
    equations = (_extract_equations_compact(inst) if compact
                 else _extract_equations(inst))
    edge_order = _cycle_equation_order(equations)
    variables = []
    for i, edge in enumerate(edge_order):
        leaving = set(edge) - set(edge_order[(i + 1) % len(edge_order)])
        if len(leaving) != 1:
            raise ValueError("consecutive equations do not have one leaving variable")
        variables.append(next(iter(leaving)))
    for i, edge in enumerate(edge_order):
        expected = {variables[i], variables[(i + 1) % len(variables)],
                    variables[(i + 2) % len(variables)]}
        if set(edge) != expected:
            raise ValueError("recovered variable order is not a tight cycle")
    rhs = [equations[edge] for edge in edge_order]
    return variables, rhs


def _assignment_to_rows(inst, assignment):
    answer = []
    for group in inst["groups"]:
        wanted = [assignment[v] for v in group["variables"]]
        try:
            answer.append(group["rows"].index(wanted))
        except ValueError:
            return None
    return answer


def _gaussian_reference(inst):
    """Generic exact linear algebra after recovering the parity quartets."""
    equations = _extract_equations(inst)
    n = inst["n"]
    rows = []
    for variables, rhs in equations.items():
        row = 0
        for variable in variables:
            row |= 1 << variable
        row |= rhs << n
        rows.append(row)

    # Four Boolean operations decode each clause's parity and four more build
    # each equation bitset.  This deliberately counts preprocessing rather than
    # presenting elimination alone as the full mechanical cost.
    operations = 4 * len(inst["clauses"]) + 4 * len(equations)
    pivot_row = 0
    pivots = []
    for column in range(n):
        operations += max(0, len(rows) - pivot_row)  # pivot-bit inspections
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
                operations += n + 1  # scalar Boolean XORs represented by the bitset op
        pivots.append(column)
        pivot_row += 1
        if pivot_row == len(rows):
            break
    if len(pivots) != n:
        return None, operations
    assignment = [0] * n
    for r, column in enumerate(pivots):
        assignment[column] = (rows[r] >> n) & 1
    return _assignment_to_rows(inst, assignment), operations


def _dpll_reference(inst):
    """Plain DPLL with repeated unit propagation on the displayed 3-CNF."""
    clauses = inst["clauses"]
    n = inst["n"]
    operations = 0
    nodes = 0

    def recurse(assignment):
        nonlocal operations, nodes
        nodes += 1
        assignment = list(assignment)
        while True:
            changed = False
            for clause in clauses:
                satisfied = False
                unknown = []
                for literal in clause:
                    operations += 1  # one literal inspection
                    variable = abs(literal) - 1
                    value = assignment[variable]
                    if value is None:
                        unknown.append(literal)
                    elif value == int(literal > 0):
                        satisfied = True
                        break
                if satisfied:
                    continue
                if not unknown:
                    return None
                if len(unknown) == 1:
                    literal = unknown[0]
                    variable = abs(literal) - 1
                    value = int(literal > 0)
                    if assignment[variable] is None:
                        assignment[variable] = value
                        operations += 1
                        changed = True
                    elif assignment[variable] != value:
                        return None
            if not changed:
                break

        try:
            variable = assignment.index(None)
        except ValueError:
            return assignment
        for value in (0, 1):
            branch = list(assignment)
            branch[variable] = value
            operations += 1
            solution = recurse(branch)
            if solution is not None:
                return solution
        return None

    assignment = recurse([None] * n)
    return (_assignment_to_rows(inst, assignment) if assignment is not None else None,
            nodes, operations)


def _compact_cycle_reference(inst):
    """Solve the tight cycle using one recurrence, not generic elimination.

    Once the parity-quartet invariant has been recognized, one representative
    clause fixes each right-hand side: it is the parity of the clause's three
    positive-sign bits, requiring two XORs.  The operation counter includes
    those 2n XORs as well as the recurrence and homogeneous correction.
    """
    variables, rhs = _ordered_cycle_data(inst, compact=True)
    n = len(variables)
    # Particular solution with y_0=y_1=0 for all non-wrapping equations.
    y = [0, 0]
    operations = 2 * n
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
    cycle_bits = []
    for i, particular in enumerate(y):
        cycle_bits.append(particular ^ homogeneous[i % 3])
        operations += 1
    assignment = [0] * n
    for variable, bit in zip(variables, cycle_bits):
        assignment[variable] = bit
    return _assignment_to_rows(inst, assignment), operations


def _normalise_labels(sequence):
    mapping = {}
    next_label = 0
    out = []
    for item in sequence:
        if item not in mapping:
            mapping[item] = next_label
            next_label += 1
        out.append(mapping[item])
    return tuple(out)


def canonical_key(inst):
    """Canonicalise row/group/coordinate order and the tight-cycle dihedral action."""
    variables, _ = _ordered_cycle_data(inst)
    group_of = {}
    for gi, group in enumerate(inst["groups"]):
        for variable in group["variables"]:
            group_of[variable] = gi
    sequence = [group_of[v] for v in variables]
    candidates = []
    for oriented in (sequence, list(reversed(sequence))):
        for shift in range(len(oriented)):
            rotated = oriented[shift:] + oriented[:shift]
            candidates.append(_normalise_labels(rotated))
    canonical_partition = min(candidates)
    payload = {
        "n": inst["n"],
        "r": inst["r"],
        "copies": inst["copies"],
        "partition": canonical_partition,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def escalate(params):
    p = dict(params)
    # Including RHS decoding, the compact route costs 5n+3 bit operations.
    # The named ladder grows n while raising block_bits so the witness remains
    # about twelve indices long.  n=59 is the last supported point below G9's
    # 300-operation no-tool ceiling.
    n = int(p.get("n", 0))
    for next_n, next_block_bits in ((23, 2), (41, 4), (59, 5)):
        if n < next_n:
            p["n"] = next_n
            p["block_bits"] = next_block_bits
            p["copies"] = 1
            return p
    return "cap_bound"


def _attack_outlier(inst):
    # Choose the row with most zero coordinates in each set.
    answer = []
    for vectors in inst["vectors"]:
        answer.append(min(range(len(vectors)),
                          key=lambda i: (vectors[i].bit_count(), i)))
    return answer


def _attack_greedy(inst):
    remaining = (1 << len(inst["clauses"])) - 1
    answer = []
    for vectors in inst["vectors"]:
        chosen = min(range(len(vectors)),
                     key=lambda i: ((remaining & vectors[i]).bit_count(), i))
        answer.append(chosen)
        remaining &= vectors[chosen]
    return answer


def _attack_literal_majority(inst):
    scores = [0] * inst["n"]
    for clause in inst["clauses"]:
        for literal in clause:
            scores[abs(literal) - 1] += 1 if literal > 0 else -1
    assignment = [1 if score > 0 else 0 for score in scores]
    return _assignment_to_rows(inst, assignment)


def _random_restart(inst, rng, restarts):
    for attempt in range(1, restarts + 1):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate, attempt
    return None, restarts


def _copy_instance(inst):
    return json.loads(json.dumps(inst))


def _transform_instance(inst, rng, *, rows=False, clauses=False,
                        variables=False, groups=False, complement=False,
                        group_coordinates=False):
    transformed = _copy_instance(inst)
    answer = list(transformed["answer"])

    if variables:
        permutation = list(range(transformed["n"]))
        rng.shuffle(permutation)
        transformed["clauses"] = [
            [(permutation[abs(lit) - 1] + 1) * (1 if lit > 0 else -1)
             for lit in clause]
            for clause in transformed["clauses"]
        ]
        for group in transformed["groups"]:
            group["variables"] = [permutation[v] for v in group["variables"]]

    if complement:
        flipped = {v for v in range(transformed["n"]) if rng.randrange(2)}
        if not flipped:
            flipped.add(rng.randrange(transformed["n"]))
        transformed["clauses"] = [
            [(-lit if abs(lit) - 1 in flipped else lit) for lit in clause]
            for clause in transformed["clauses"]
        ]
        for group in transformed["groups"]:
            for row in group["rows"]:
                for j, variable in enumerate(group["variables"]):
                    if variable in flipped:
                        row[j] ^= 1

    if group_coordinates:
        for group in transformed["groups"]:
            order = list(range(len(group["variables"])))
            rng.shuffle(order)
            group["variables"] = [group["variables"][old] for old in order]
            group["rows"] = [[row[old] for old in order] for row in group["rows"]]

    if rows:
        for gi, group in enumerate(transformed["groups"]):
            order = list(range(len(group["rows"])))
            rng.shuffle(order)
            old_answer = answer[gi]
            group["rows"] = [group["rows"][old] for old in order]
            answer[gi] = order.index(old_answer)

    if clauses:
        for clause in transformed["clauses"]:
            rng.shuffle(clause)
        rng.shuffle(transformed["clauses"])

    if groups:
        order = list(range(len(transformed["groups"])))
        rng.shuffle(order)
        transformed["groups"] = [transformed["groups"][old] for old in order]
        answer = [answer[old] for old in order]

    transformed["answer"] = answer
    transformed["k"] = len(transformed["groups"])
    transformed["vectors"] = _rebuild_vectors(transformed)
    return transformed


def _find_corruptions(inst):
    answer = list(inst["answer"])
    corruptions = {
        "drop_one_element": answer[:-1],
        "empty": [],
        "out_of_range": [len(inst["vectors"][0])] + answer[1:],
    }

    used_reasons = {verify(inst, candidate)[1] for candidate in corruptions.values()}

    duplicate = None
    for i in range(len(answer)):
        for j in range(len(answer)):
            if i == j:
                continue
            candidate = list(answer)
            candidate[j] = candidate[i]
            if candidate.count(candidate[i]) < 2:
                continue
            ok, reason = verify(inst, candidate)
            if not ok and reason not in used_reasons:
                duplicate = candidate
                used_reasons.add(reason)
                break
        if duplicate is not None:
            break
    if duplicate is None:
        duplicate = answer + [answer[0]]
    corruptions["duplicate_one_element"] = duplicate

    swap = None
    for i in range(len(answer)):
        for j in range(i + 1, len(answer)):
            if answer[i] == answer[j]:
                continue
            candidate = list(answer)
            candidate[i], candidate[j] = candidate[j], candidate[i]
            ok, reason = verify(inst, candidate)
            if not ok and reason not in used_reasons:
                swap = candidate
                break
        if swap is not None:
            break
    if swap is None:
        # A different length error remains a genuine swap-plus-corruption probe.
        swap = list(reversed(answer)) + [0, 0]
    corruptions["swap_two_elements"] = swap
    return corruptions


def _answer_size(answer):
    blob = json.dumps(answer, separators=(",", ":"))
    atoms = len(answer)
    # Conservative corpus convention: roughly two tokens per integer plus brackets.
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
                assert json.loads(json.dumps(inst["answer"])) == inst["answer"]
            except (AssertionError, TypeError, ValueError) as exc:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": f"answer is not JSON-native: {exc}"})
            if any(len(vectors) != len(set(vectors)) for vectors in inst["vectors"]):
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": "a displayed A_i contains duplicate vectors"})
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
        "pass": all(case["rejected"] for case in cases.values())
                and len(set(reasons)) == len(reasons),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "I grouped the parity constraints and obtained the following tuple.\n"
        "```json\n<answer>\n"
        + json.dumps(inst["answer"])
        + "\n</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and parse_answer("no usable tuple here") is None,
        "parsed_equals_answer": parsed == inst["answer"],
        "garbage_returns_none": parse_answer("no usable tuple here") is None,
    }

    guess_rng = random.Random(0x240908037)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            guess_hits += 1
    guess_elapsed = time.perf_counter() - guess_start
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_hits / guess_total,
        "exact_fraction": 2.0 ** (-inst["n"]),
        "candidate_space_bits": inst["n"],
        "structure_aware_constraints": [
            "exactly one row from every displayed set",
            "every row index already satisfies its group-specific range",
            "rows jointly sample the full Boolean assignment space uniformly",
        ],
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    baseline_rng = random.Random(99173)
    baseline_start = time.perf_counter()
    baseline_answer, baseline_restarts = _random_restart(inst, baseline_rng, 2048)
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
        "shipping_exact_solution_fraction": 2.0 ** (-inst["n"]),
        "demo_candidate_space": search_space(demo),
        "demo_exact_solution_count": demo_count,
        "demo_exact_solution_fraction": demo_count / search_space(demo),
        "baseline_attack_restarts": baseline_restarts,
        "baseline_attack_successes": 1 if baseline_answer is not None else 0,
        "baseline_attack_nodes": baseline_restarts,
        "baseline_attack_wall_clock_sec": round(baseline_elapsed, 6),
        "reference_operation_count": reference_ops,
        "reference_wall_clock_sec": round(reference_elapsed, 6),
        "strongest_failing_attack": "random_restart_2048",
    }

    attack_names = (
        "outlier_min_vector_weight",
        "greedy_group_coverage",
        "random_restart_256",
        "by_hand_literal_majority",
    )
    attack_results = {name: {"successes": 0, "attempts": 0, "wall_clock_sec": 0.0}
                      for name in attack_names}
    reference_successes = 0
    reference_ops_max = 0
    reference_total_time = 0.0
    dpll_successes = 0
    dpll_nodes_max = 0
    dpll_ops_max = 0
    dpll_total_time = 0.0
    compact_successes = 0
    compact_ops_max = 0
    compact_total_time = 0.0
    for seed in range(100, 108):
        trial = make_instance(seed=seed, **shipping_params)

        started = time.perf_counter()
        candidate = _attack_outlier(trial)
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
        candidate = _attack_literal_majority(trial)
        attack_results[attack_names[3]]["wall_clock_sec"] += time.perf_counter() - started
        attack_results[attack_names[3]]["attempts"] += 1
        attack_results[attack_names[3]]["successes"] += int(verify(trial, candidate)[0])

        started = time.perf_counter()
        candidate, operations = _gaussian_reference(trial)
        reference_total_time += time.perf_counter() - started
        reference_ops_max = max(reference_ops_max, operations)
        reference_successes += int(candidate is not None and verify(trial, candidate)[0])

        started = time.perf_counter()
        candidate, nodes, operations = _dpll_reference(trial)
        dpll_total_time += time.perf_counter() - started
        dpll_nodes_max = max(dpll_nodes_max, nodes)
        dpll_ops_max = max(dpll_ops_max, operations)
        dpll_successes += int(candidate is not None and verify(trial, candidate)[0])

        started = time.perf_counter()
        candidate, operations = _compact_cycle_reference(trial)
        compact_total_time += time.perf_counter() - started
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
            "name": "XOR-quartet recovery plus Gauss-Jordan elimination over GF(2)",
            "complexity": "O(C log C + n^3) exact Boolean operations",
            "wall_clock_sec": round(reference_total_time / 8, 6),
            "wall_clock_sec_total_8": round(reference_total_time, 6),
            "operations": reference_ops_max,
            "solves": f"{reference_successes}/8, as expected",
        },
        "additional_reference_algorithm": {
            "name": "plain DPLL with unit propagation on the displayed 3-CNF",
            "complexity": "exponential worst case",
            "wall_clock_sec": round(dpll_total_time / 8, 6),
            "wall_clock_sec_total_8": round(dpll_total_time, 6),
            "max_nodes": dpll_nodes_max,
            "max_literal_operations": dpll_ops_max,
            "solves": f"{dpll_successes}/8, as expected for a Track B reference",
        },
        "intended_compact_route": {
            "name": "tight-cycle recovery and cyclic XOR recurrence",
            "wall_clock_sec": round(compact_total_time / 8, 6),
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
    escalated_before_shipping = escalate(DIFFICULTY["medium"])
    escalated_at_shipping = escalate(shipping_params)
    report["G7_scales"] = {
        "pass": doubled_ok and isinstance(escalated_before_shipping, dict)
                and escalated_before_shipping.get("n", 0) > DIFFICULTY["medium"]["n"]
                and len(escalated_before_shipping) == len(shipping_params)
                and escalated_at_shipping == "cap_bound",
        "shipping_n": shipping_params["n"],
        "shipping_sets": inst["k"],
        "shipping_coordinates": len(inst["clauses"]),
        "doubled_n": doubled_n,
        "doubled_sets": doubled["k"],
        "doubled_coordinates": len(doubled["clauses"]),
        "doubled_build_and_verify_sec": round(scale_elapsed, 6),
        "doubled_verify_reason": doubled_reason,
        "escalation_from_medium": escalated_before_shipping,
        "escalation_after_shipping": escalated_at_shipping,
        "cap_reason": "5n+3 exact bit operations would exceed G9(c) above n=59",
    }

    invariance = 0
    real_verified = 0
    g8_failures = []
    # Relabelling invariance is structural, so exercise it on the easy rung to
    # avoid rebuilding 80 copies of the much wider shipping vectors.
    g8_params = DIFFICULTY["easy"]
    for seed in range(20):
        original = make_instance(seed=4000 + seed, **g8_params)
        original_key = canonical_key(original)
        for ti, flags in enumerate((
            {"rows": True},
            {"clauses": True, "variables": True},
            {"groups": True},
            {"complement": True},
            {"group_coordinates": True},
            {"rows": True, "clauses": True, "variables": True, "groups": True,
             "complement": True, "group_coordinates": True},
        )):
            changed = _transform_instance(original, random.Random(seed * 17 + ti), **flags)
            if canonical_key(changed) == original_key:
                invariance += 1
            else:
                g8_failures.append({"seed": seed, "transform": ti, "reason": "key changed"})
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
        "pass": not g8_failures and invariance == 120 and real_verified == 120
                and len(unrelated_keys) == 20,
        "transformations": [
            "candidate-row reordering with carried witness",
            "coordinate/literal ordering plus arbitrary variable renaming",
            "vector-set reordering with carried witness",
            "independent Boolean value complementation with carried semantics",
            "within-set variable-coordinate reordering",
            "composition of all preceding transformations",
        ],
        "invariant_relabellings": invariance,
        "real_transformations_verified": real_verified,
        "unrelated_attempts": 20,
        "unrelated_distinct_keys": len(unrelated_keys),
        "failures": g8_failures,
    }

    planted_chars, _, _ = _answer_size(inst["answer"])
    # Use the longest in-language row indices, not a lucky short planted tuple,
    # so G9(c) and max_answer_tokens describe the whole shipping distribution.
    longest_candidate = [len(vectors) - 1 for vectors in inst["vectors"]]
    chars, tokens, elements = _answer_size(longest_candidate)
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
