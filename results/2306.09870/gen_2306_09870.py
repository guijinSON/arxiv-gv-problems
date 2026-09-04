"""Verified IPDS-Extension generator grounded in arXiv:2306.09870.

The generated object is the implicating power-domination graph used in Section 3,
Lemma 10 of the paper.  A quietly planted 4-CNF is expressed as a monotone
circuit with dual-rail inputs, and the lemma's AND/OR construction turns the
circuit into an IPDS-Extension instance.  The satisfying input assignment is
sampled first and carried through the construction; it is never recovered by
solving the generated instance.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import re
import statistics
import time


TRACK: str = "A"

_REDUCTION = (
    "Section 3.4, Lemma 10 (Weighted Monotone Circuit Satisfiability to "
    "IPDS-Extension, using implication arcs and the AND gadget)"
)

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "IPDS-Extension graph",
        "propagating vertices",
        "implication arcs",
        "selectable and excluded vertices",
    ],
    "verification_operations": [
        "exact closed-neighborhood observation",
        "exhaustive implication propagation",
        "exact one-unobserved-neighbor propagation",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "paper_licensed",
    "reduction": _REDUCTION,
    "reduction_source": "paper_central",
    "intuition_type": "reduction recognition",
    "intuition_description": (
        "Recognize the two-input checks as dual-rail Boolean variables and the "
        "four-input checks as clauses; without that recognition one must reason "
        "directly through thousands of implication and propagation events."
    ),
    "hardness_basis": (
        "Track A: Section 3.4 Lemma 10 and Section 3 Corollary 11 establish "
        "W[P]-hardness/completeness parameterized by selected-set size; shipping "
        "uses k=n growing with n in a pairwise-independent planted 4-CNF regime "
        "with balanced first and second literal moments, where no efficient "
        "general recovery method is known and the measured bounded DPLL cost is "
        "reported in G5."
    ),
    "max_answer_tokens": 290,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 6, "clause_ratio": 3.0, "mix_rounds": 1},
    "easy": {"n": 240, "clause_ratio": 10.10, "mix_rounds": 4},
    "medium": {"n": 240, "clause_ratio": 10.30, "mix_rounds": 5},
    "hard": {"n": 240, "clause_ratio": 10.50, "mix_rounds": 6},
}
SHIPPING_DIFFICULTY: str = "easy"

STRUCTURAL_HINT: str = (
    "Treat every two-input check as one dual-rail Boolean variable and every "
    "four-input check as a clause before reasoning about propagation."
)
PLACEBO_HINT: str = (
    "Track the vertex identifiers carefully and check the required cardinality "
    "before reasoning about the propagation process."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A strictly increasing list of exactly n selectable vertex IDs, choosing "
        "exactly one ID from each displayed two-vertex literal pair."
    ),
    "bounds": {
        "max_selected_vertices": 512,
        "choices_per_literal_pair": 2,
        "ordering": "strictly increasing",
    },
}

NOTES: str = r"""
Step 0 paper reading.  Section 2 fixes the exact observation rules: selection
observes a closed neighborhood, and an observed propagating vertex with exactly
one unobserved neighbor observes that neighbor.  Section 3 adds implication arcs
for IPDS.  Section 3.4, Lemma 10 is the construction used here: circuit arcs are
implication arcs, OR gates are ordinary implication targets, and an AND gate is
represented by proxy inputs adjacent to a gate-input vertex whose last neighbor
is the gate output.  The output has implication arcs back to every input.  Lemmas
7 and 9 can remove the extra IPDS/extension features, and Lemma 3 can make every
vertex propagating; Corollary 11 concludes PDS is W[P]-complete.

What produces the certificate.  The generator first samples n Boolean values.
Every generated four-literal clause uses a nonzero relative truth pattern.  A
specific weight-1 pattern has probability 3/32, a weight-2 pattern 2/32, a
weight-3 pattern 1/32, and the weight-4 pattern 4/32.  Thus every clause is
satisfied, each literal is true with probability 1/2, each literal pair is true
with probability 1/4, and the two XOR parities each have probability 1/2.
Unlike the rejected 3-CNF prototype, the plant is not the solution of an exact
linear system.  The CNF is
made monotone with two input vertices per Boolean variable; selecting exactly n
inputs while requiring every pair-check forces exactly one input per variable.
Lemma 10 carries that assignment to the selected vertices in the IPDS instance.
No SAT, PDS, hitting-set, or search algorithm runs in make_instance().

What is easy.  Section 4 gives safe reduction rules and Section 4.3 gives an
exact implicit-hitting-set solver; Section 5 reports that solver solving practical
graphs with 2,000 and 10,024 vertices in about one second and continental graphs
in minutes.  Those are not polynomial worst-case algorithms, so they do not by
themselves invalidate Track A, but they make a theorem-only hardness claim
untenable.  The claimed distribution is therefore tested directly.  The
parameter k equals n (240 at shipping) and grows when n grows; the named main
ladder instead tightens clause density at fixed answer length.

Attacks.  Quiet planting defeats the literal-frequency outlier and signed
pair-correlation spectral probes by construction in expectation.  The panel also
runs a one-pass greedy assignment, random-restart WalkSAT, a signed third-moment
tensor-power attack followed by local repair, and bounded DPLL with unit
propagation as the domain-standard exact attack.  The 3-CNF prototype was
discarded after an exact XOR/Gaussian-elimination shortcut was found, and the
4-CNF ratio-9.5 prototype was discarded when tensor/repair solved 1/8 seeds.
The README records the
budgets and the important caveat that failure at a finite budget is empirical,
not an average-case hardness proof.
"""


# Updated only from actual harden.py transcripts after those runs complete.
_ORACLE_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


def _decode_formula(inst: dict) -> list[list[tuple[int, int]]]:
    """Convert public clause rows to (variable, required bit)."""
    lookup = {}
    for variable, pair in enumerate(inst["literal_pairs"]):
        lookup[pair[0]] = (variable, 0)
        lookup[pair[1]] = (variable, 1)
    return [[lookup[vertex] for vertex in clause] for clause in inst["clauses"]]


def _candidate_from_bits(inst: dict, bits: list[int]) -> list[int]:
    return sorted(inst["literal_pairs"][i][int(bit)] for i, bit in enumerate(bits))


def _formula_satisfied(decoded, bits) -> bool:
    return all(any(bits[var] == required for var, required in clause)
               for clause in decoded)


def _observation_closure(inst: dict, selected) -> tuple[set[int], int]:
    """Apply all paper rules exactly; return observed vertices and event count."""
    order = inst["vertex_count"]
    neighbors = [[] for _ in range(order)]
    for left, right in inst["edges"]:
        neighbors[left].append(right)
        neighbors[right].append(left)
    outgoing = [[] for _ in range(order)]
    for source, target in inst["implications"]:
        outgoing[source].append(target)

    observed = [False] * order
    queue = []
    operations = 0

    def mark(vertex):
        if not observed[vertex]:
            observed[vertex] = True
            queue.append(vertex)

    for vertex in selected:
        mark(vertex)
        for other in neighbors[vertex]:
            operations += 1
            mark(other)

    # Rechecking an observed vertex and its observed neighbors after every mark
    # is simple and exact.  The generated graph is sparse, so this is linear up
    # to a small constant for this family.
    cursor = 0
    while cursor < len(queue):
        vertex = queue[cursor]
        cursor += 1
        for target in outgoing[vertex]:
            operations += 1
            mark(target)
        affected = [vertex]
        affected.extend(neighbors[vertex])
        for source in affected:
            operations += len(neighbors[source])
            if not observed[source]:
                continue
            missing = -1
            count = 0
            for target in neighbors[source]:
                if not observed[target]:
                    count += 1
                    missing = target
                    if count == 2:
                        break
            if count == 1:
                mark(missing)
    return {i for i, value in enumerate(observed) if value}, operations


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a satisfying assignment, then apply Lemma 10."""
    clause_ratio = params.pop("clause_ratio", 10.1)
    mix_rounds = params.pop("mix_rounds", 3)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 4 or n > 512:
        raise ValueError("n must be an integer from 4 through 512")
    if not isinstance(clause_ratio, (int, float)) or not 1.0 <= clause_ratio <= 12.0:
        raise ValueError("clause_ratio must lie in [1,12]")
    if isinstance(mix_rounds, bool) or not isinstance(mix_rounds, int) or mix_rounds < 0:
        raise ValueError("mix_rounds must be a nonnegative integer")

    rng = random.Random(seed)
    planted = [rng.randrange(2) for _ in range(n)]
    input_ids = list(range(2 * n))
    rng.shuffle(input_ids)
    pairs = [[input_ids[2 * i], input_ids[2 * i + 1]] for i in range(n)]

    clause_count = max(1, int(round(n * float(clause_ratio))))
    decoded = []
    seen = set()
    attempts = 0
    while len(decoded) < clause_count:
        attempts += 1
        if attempts > clause_count * 200:
            raise RuntimeError("could not draw enough distinct quiet-planted clauses")
        variables = tuple(sorted(rng.sample(range(n), 4)))
        # Exact pairwise-independent, parity-balanced planting law on the 15
        # nonzero four-bit patterns.  Repetition counts use denominator 32:
        # weight-1 patterns have mass 3/32 each, weight-2 patterns 2/32 each,
        # weight-3 patterns 1/32 each, and 1111 has mass 4/32.
        weighted_patterns = []
        repetitions = {1: 3, 2: 2, 3: 1, 4: 4}
        for mask in range(1, 16):
            weighted_patterns.extend([mask] * repetitions[mask.bit_count()])
        mask = rng.choice(weighted_patterns)
        relative = tuple((mask >> j) & 1 for j in range(4))
        literals = tuple(
            (variable, planted[variable] if rel else 1 - planted[variable])
            for variable, rel in zip(variables, relative)
        )
        key = tuple(literals)
        if key in seen:
            continue
        seen.add(key)
        decoded.append(list(literals))

    # Clause and variable order carry no semantics.  Multiple independent
    # shuffles make that explicit and provide a second difficulty dial without
    # changing the answer length.
    for _ in range(mix_rounds + 1):
        rng.shuffle(decoded)
    clauses = []
    for clause in decoded:
        row = [pairs[variable][bit] for variable, bit in clause]
        rng.shuffle(row)
        clauses.append(row)

    pair_base = 2 * n
    clause_base = pair_base + n
    checks = list(range(pair_base, pair_base + n)) + list(
        range(clause_base, clause_base + clause_count)
    )
    proxy_base = clause_base + clause_count
    root_input = proxy_base + len(checks)
    root_output = root_input + 1
    vertex_count = root_output + 1

    edges = [[proxy_base + i, root_input] for i in range(len(checks))]
    edges.append([root_input, root_output])
    implications = []
    for i, pair in enumerate(pairs):
        implications.extend([[pair[0], pair_base + i], [pair[1], pair_base + i]])
    for j, clause in enumerate(clauses):
        node = clause_base + j
        implications.extend([[literal, node] for literal in clause])
    for i, check in enumerate(checks):
        implications.append([check, proxy_base + i])
    implications.extend([[root_output, vertex] for vertex in input_ids])

    # Edge/arc order is representation only.
    rng.shuffle(edges)
    rng.shuffle(implications)
    return {
        "family": "quiet-planted weighted monotone circuit as IPDS-Extension",
        "n_variables": n,
        "required_size": n,
        "clause_ratio": float(clause_ratio),
        "mix_rounds": mix_rounds,
        "vertex_count": vertex_count,
        "all_vertices_propagating": True,
        "selectable": sorted(input_ids),
        "literal_pairs": pairs,
        "clauses": clauses,
        "pair_check_base": pair_base,
        "clause_check_base": clause_base,
        "proxy_base": proxy_base,
        "root_input": root_input,
        "root_output": root_output,
        "edges": edges,
        "implications": implications,
        "answer": _candidate_from_bits(
            {"literal_pairs": pairs}, planted
        ),
    }


def _answer_text(answer) -> str:
    return ", ".join(str(value) for value in answer)


def render(inst) -> str:
    pair_lines = [
        f"  {i}: {left} {right} -> {inst['pair_check_base'] + i}"
        for i, (left, right) in enumerate(inst["literal_pairs"])
    ]
    clause_lines = [
        f"  {j}: {' '.join(map(str, clause))} -> {inst['clause_check_base'] + j}"
        for j, clause in enumerate(inst["clauses"])
    ]
    example = sorted(pair[0] for pair in inst["literal_pairs"])
    statement = f"""IMPLICATING POWER DOMINATING SET EXTENSION

There are {inst['vertex_count']} vertices, with integer IDs 0 through
{inst['vertex_count'] - 1}. Every vertex is propagating. The only vertices that
may be selected are IDs 0 through {2 * inst['n_variables'] - 1}; every other
vertex is excluded from selection. Select exactly {inst['required_size']} distinct
vertices.

Starting from the selected set, repeatedly apply these rules until no rule can
add a vertex:

1. Domination: every selected vertex and every endpoint joined to it by an
   undirected edge is observed.
2. Implication: if the source of a directed implication arc is observed, its
   target is observed.
3. Propagation: if an observed vertex has exactly one unobserved undirected
   neighbor, that neighbor is observed.

Your selected set is valid iff eventually every vertex is observed. Rule order
does not matter because rules only add observed vertices.

The graph is specified exactly by the following tables and formulas. A pair row
"i: a b -> q" creates implication arcs a->q and b->q. A clause row
"j: a b c d -> q" creates implication arcs from all four listed IDs to q. IDs in each
literal pair are distinct, pairs are disjoint, and clause rows never repeat a
pair. The pair order is only descriptive; the answer itself is a set.

Literal-pair checks:
{chr(10).join(pair_lines)}

Four-input clause checks:
{chr(10).join(clause_lines)}

For every check vertex q above, in table order (all pair checks, then all clause
checks), create one proxy p={inst['proxy_base']}+its_zero_based_table_position,
add implication q->p, and add the undirected edge {{p,{inst['root_input']}}}.
Also add the undirected edge {{{inst['root_input']},{inst['root_output']}}} and
the implication arcs {inst['root_output']}->v for every selectable vertex v.
There are no other edges or implication arcs.

Give your final answer inside <answer></answer> tags as exactly
{inst['required_size']} comma-separated base-10 vertex IDs in strictly increasing
order. Repeats are forbidden. The IDs must choose exactly one member of every
displayed literal pair. Do not use brackets.
Example of the required syntax (not necessarily a valid solution):
<answer>{_answer_text(example)}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    try:
        matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", str(text), re.I | re.S)
        if not matches:
            return None
        body = matches[-1].strip()
        for fence in ("~~~", chr(96) * 3):
            if body.startswith(fence) and body.endswith(fence):
                body = re.sub("^" + re.escape(fence) + r"[^\n]*\n?", "", body)
                body = re.sub(r"\n?" + re.escape(fence) + "$", "", body).strip()
        if body.startswith("[") and body.endswith("]"):
            body = body[1:-1].strip()
        if not body:
            return []
        pieces = [piece.strip() for piece in body.split(",")]
        if any(not re.fullmatch(r"[+-]?\d+", piece) for piece in pieces):
            return None
        return [int(piece) for piece in pieces]
    except Exception:
        return None


def verify(inst, answer) -> tuple[bool, str]:
    if answer is None:
        return False, "answer is absent"
    if not isinstance(answer, list):
        return False, "answer must be a list of vertex IDs"
    if not answer:
        return False, "answer is empty"
    if any(isinstance(value, bool) or not isinstance(value, int) for value in answer):
        return False, "every selected vertex ID must be an integer"
    if len(answer) != inst["required_size"]:
        return False, f"expected exactly {inst['required_size']} selected vertex IDs"
    if len(set(answer)) != len(answer):
        return False, "selected vertex IDs must be distinct"
    if any(answer[i] >= answer[i + 1] for i in range(len(answer) - 1)):
        return False, "selected vertex IDs must be in strictly increasing order"
    selectable = set(inst["selectable"])
    unknown = next((value for value in answer if value not in selectable), None)
    if unknown is not None:
        return False, f"vertex {unknown} is excluded from selection"
    selected = set(answer)
    if any((pair[0] in selected) + (pair[1] in selected) != 1
           for pair in inst["literal_pairs"]):
        return False, "the selection must contain exactly one ID from every literal pair"

    # This cheap scan is exactly the implication condition for every displayed
    # four-input OR.  It rejects almost all random candidates before materializing
    # the closure; a passing candidate is still checked by the paper's rules below.
    missed = next((j for j, clause in enumerate(inst["clauses"])
                   if not any(vertex in selected for vertex in clause)), None)
    if missed is not None:
        return False, f"clause-check {missed} has no selected implication source"
    observed, _ = _observation_closure(inst, selected)
    if len(observed) != inst["vertex_count"]:
        return False, f"observation closure leaves {inst['vertex_count'] - len(observed)} vertices unobserved"
    return True, "ok"


def random_candidate(inst, rng: random.Random) -> object:
    """Sample uniformly after enforcing the pair constraint visible in render()."""
    bits = [rng.randrange(2) for _ in inst["literal_pairs"]]
    return _candidate_from_bits(inst, bits)


def search_space(inst) -> int | None:
    return 1 << inst["n_variables"]


def enumerate_all(inst) -> int | None:
    n = inst["n_variables"]
    if n > 22:
        return None
    decoded = _decode_formula(inst)
    count = 0
    for word in range(1 << n):
        bits = [(word >> i) & 1 for i in range(n)]
        if _formula_satisfied(decoded, bits):
            count += 1
    return count


def canonical_key(inst) -> str:
    """WL-style invariant of the pair/clause incidence structure.

    Exact CNF isomorphism is not known to be easy.  Six rounds of typed incidence
    refinement are the strongest cheap invariant used here; the self-test checks
    actual vertex, row, and within-row relabelings and unrelated-seed diversity.
    """
    pairs = inst["literal_pairs"]
    clauses = inst["clauses"]
    literals = sorted(inst["selectable"])
    literal_pos = {value: i for i, value in enumerate(literals)}
    total = len(literals) + len(pairs) + len(clauses)
    adjacency = [[] for _ in range(total)]
    pair_offset = len(literals)
    clause_offset = pair_offset + len(pairs)
    for i, pair in enumerate(pairs):
        node = pair_offset + i
        for literal in pair:
            other = literal_pos[literal]
            adjacency[node].append(other)
            adjacency[other].append(node)
    for j, clause in enumerate(clauses):
        node = clause_offset + j
        for literal in clause:
            other = literal_pos[literal]
            adjacency[node].append(other)
            adjacency[other].append(node)
    colors = (["L"] * len(literals) + ["P"] * len(pairs) + ["C"] * len(clauses))
    for _ in range(8):
        colors = [
            hashlib.sha256(
                (colors[v] + "|" + "|".join(sorted(colors[w] for w in adjacency[v]))).encode()
            ).hexdigest()
            for v in range(total)
        ]
    edge_colors = []
    for left in range(total):
        for right in adjacency[left]:
            if left < right:
                edge_colors.append(tuple(sorted((colors[left], colors[right]))))
    payload = {
        "family": "ipds-quiet-3cnf",
        "n": inst["n_variables"],
        "m": len(clauses),
        "vertex_colors": sorted(colors),
        "incidence_colors": sorted(edge_colors),
    }
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def escalate(params) -> dict | str | None:
    n = int(params["n"])
    ratio = float(params.get("clause_ratio", 10.1))
    rounds = int(params.get("mix_rounds", 3))
    # First tighten/crowd the same certificate language.  Only after that axis is
    # exhausted do we grow n, and we stop honestly at the output cap.
    if ratio < 10.5:
        return {"n": n, "clause_ratio": round(min(10.5, ratio + 0.2), 2),
                "mix_rounds": rounds + 1}
    if n < 240:
        return {"n": min(240, n + 20), "clause_ratio": ratio,
                "mix_rounds": rounds + 1}
    return "cap_bound"


def _bits_from_candidate(inst, candidate) -> list[int] | None:
    selected = set(candidate or [])
    bits = []
    for pair in inst["literal_pairs"]:
        matches = [bit for bit, vertex in enumerate(pair) if vertex in selected]
        if len(matches) != 1:
            return None
        bits.append(matches[0])
    return bits


def _attack_frequency(inst):
    decoded = _decode_formula(inst)
    counts = [[[0, 0] for _ in range(inst["n_variables"])][i]
              for i in range(inst["n_variables"])]
    for clause in decoded:
        for variable, bit in clause:
            counts[variable][bit] += 1
    bits = [1 if row[1] > row[0] else 0 for row in counts]
    return _candidate_from_bits(inst, bits)


def _attack_greedy(inst):
    decoded = _decode_formula(inst)
    n = inst["n_variables"]
    assignment = [-1] * n
    occurrences = [[[], []] for _ in range(n)]
    for ci, clause in enumerate(decoded):
        for variable, bit in clause:
            occurrences[variable][bit].append(ci)
    order = sorted(range(n), key=lambda v: -(len(occurrences[v][0]) + len(occurrences[v][1])))
    satisfied = [False] * len(decoded)
    for variable in order:
        scores = [sum(not satisfied[ci] for ci in occurrences[variable][bit])
                  for bit in (0, 1)]
        bit = 1 if scores[1] > scores[0] else 0
        assignment[variable] = bit
        for ci in occurrences[variable][bit]:
            satisfied[ci] = True
    return _candidate_from_bits(inst, assignment)


def _walksat(inst, rng, restarts=8, steps_per_restart=4000, initial_bits=None):
    decoded = _decode_formula(inst)
    n = inst["n_variables"]
    occurrences = [[] for _ in range(n)]
    for ci, clause in enumerate(decoded):
        for variable, bit in clause:
            occurrences[variable].append((ci, bit))
    operations = 0
    last = None
    for restart in range(restarts):
        bits = (list(initial_bits) if restart == 0 and initial_bits is not None
                else [rng.randrange(2) for _ in range(n)])
        sat_count = [sum(bits[v] == b for v, b in clause) for clause in decoded]
        unsatisfied = {i for i, count in enumerate(sat_count) if count == 0}
        operations += sum(len(clause) for clause in decoded)
        for _step in range(steps_per_restart):
            if not unsatisfied:
                return _candidate_from_bits(inst, bits), operations
            ci = rng.choice(tuple(unsatisfied))
            variables = [v for v, _ in decoded[ci]]
            if rng.randrange(100) < 12:
                variable = rng.choice(variables)
            else:
                scored = []
                for variable in variables:
                    breaks = makes = 0
                    for cj, required in occurrences[variable]:
                        operations += 1
                        before = bits[variable] == required
                        if before and sat_count[cj] == 1:
                            breaks += 1
                        elif not before and sat_count[cj] == 0:
                            makes += 1
                    scored.append((breaks - makes, variable))
                best = min(score for score, _ in scored)
                variable = rng.choice([v for score, v in scored if score == best])
            old = bits[variable]
            bits[variable] ^= 1
            for cj, required in occurrences[variable]:
                operations += 1
                if old == required:
                    sat_count[cj] -= 1
                else:
                    sat_count[cj] += 1
                if sat_count[cj] == 0:
                    unsatisfied.add(cj)
                else:
                    unsatisfied.discard(cj)
        last = _candidate_from_bits(inst, bits)
    return last, operations


def _spectral_pair_attack(inst, iterations=80):
    decoded = _decode_formula(inst)
    n = inst["n_variables"]
    matrix = [[0.0] * n for _ in range(n)]
    for clause in decoded:
        for i in range(len(clause)):
            vi, bi = clause[i]
            si = 1.0 if bi else -1.0
            for j in range(i + 1, len(clause)):
                vj, bj = clause[j]
                sj = 1.0 if bj else -1.0
                matrix[vi][vj] += si * sj
                matrix[vj][vi] += si * sj
    vector = [1.0 if i % 2 else -1.0 for i in range(n)]
    operations = 0
    for _ in range(iterations):
        nxt = [sum(row[j] * vector[j] for j in range(n)) for row in matrix]
        operations += n * n
        norm = math.sqrt(sum(value * value for value in nxt)) or 1.0
        vector = [value / norm for value in nxt]
    candidates = []
    for flip in (False, True):
        bits = [int((value >= 0) ^ flip) for value in vector]
        candidates.append(_candidate_from_bits(inst, bits))
    for candidate in candidates:
        if verify(inst, candidate)[0]:
            return candidate, operations
    return candidates[0], operations


def _tensor_third_moment_attack(inst, rng, restarts=8, iterations=80):
    """Construction-aware signed third-moment recovery plus local repair."""
    decoded = _decode_formula(inst)
    n = inst["n_variables"]
    triples = []
    for clause in decoded:
        for omitted in range(len(clause)):
            row = [literal for i, literal in enumerate(clause) if i != omitted]
            (a, ba), (b, bb), (c, bc) = row
            coefficient = (1 if ba else -1) * (1 if bb else -1) * (1 if bc else -1)
            triples.append((a, b, c, coefficient))
    operations = 0
    last = None
    for _ in range(restarts):
        vector = [rng.uniform(-1.0, 1.0) for _ in range(n)]
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        vector = [value / norm for value in vector]
        for _step in range(iterations):
            nxt = [0.0] * n
            for a, b, c, coefficient in triples:
                nxt[a] += coefficient * vector[b] * vector[c]
                nxt[b] += coefficient * vector[a] * vector[c]
                nxt[c] += coefficient * vector[a] * vector[b]
                operations += 9
            norm = math.sqrt(sum(value * value for value in nxt)) or 1.0
            vector = [value / norm for value in nxt]
        for flip in (False, True):
            bits = [int((value >= 0) ^ flip) for value in vector]
            candidate = _candidate_from_bits(inst, bits)
            if verify(inst, candidate)[0]:
                return candidate, operations
            repaired, repair_ops = _walksat(
                inst, rng, restarts=1, steps_per_restart=20_000, initial_bits=bits
            )
            operations += repair_ops
            if repaired is not None and verify(inst, repaired)[0]:
                return repaired, operations
            last = repaired
    return last, operations


def _dpll_attack(inst, node_budget=50_000):
    """Bounded exact DPLL with two-watched-literal unit propagation."""
    decoded = _decode_formula(inst)
    n = inst["n_variables"]
    clauses = [[2 * variable + bit for variable, bit in clause]
               for clause in decoded]
    nodes = 0
    operations = 0
    assignment = [-1] * n
    trail = []
    watched = [[0, 1] for _ in clauses]
    watchlists = [[] for _ in range(2 * n)]
    for ci, clause in enumerate(clauses):
        watchlists[clause[0]].append(ci)
        watchlists[clause[1]].append(ci)

    occurrence = [[0, 0] for _ in range(n)]
    for clause in decoded:
        for variable, bit in clause:
            occurrence[variable][bit] += 1
    variable_order = sorted(
        range(n), key=lambda v: (-(occurrence[v][0] + occurrence[v][1]), v)
    )

    def state(literal):
        variable, bit = divmod(literal, 2)
        value = assignment[variable]
        if value < 0:
            return 0
        return 1 if value == bit else -1

    def assign_literal(literal):
        variable, bit = divmod(literal, 2)
        if assignment[variable] < 0:
            assignment[variable] = bit
            trail.append(variable)
            return True
        return assignment[variable] == bit

    def propagate(start):
        nonlocal operations
        cursor = start
        while cursor < len(trail):
            variable = trail[cursor]
            cursor += 1
            false_literal = 2 * variable + (1 - assignment[variable])
            bucket = watchlists[false_literal]
            index = 0
            while index < len(bucket):
                ci = bucket[index]
                clause = clauses[ci]
                left, right = watched[ci]
                if clause[left] == false_literal:
                    false_slot, other_slot = 0, right
                elif clause[right] == false_literal:
                    false_slot, other_slot = 1, left
                else:  # Defensive stale-entry cleanup.
                    bucket[index] = bucket[-1]
                    bucket.pop()
                    continue
                other_literal = clause[other_slot]
                replacement = None
                for position, literal in enumerate(clause):
                    operations += 1
                    if position != other_slot and state(literal) >= 0:
                        replacement = position
                        break
                if replacement is not None:
                    watched[ci][false_slot] = replacement
                    new_literal = clause[replacement]
                    bucket[index] = bucket[-1]
                    bucket.pop()
                    watchlists[new_literal].append(ci)
                    continue
                other_state = state(other_literal)
                operations += 1
                if other_state < 0:
                    return False
                if other_state == 0 and not assign_literal(other_literal):
                    return False
                index += 1
        return True

    def undo(level):
        while len(trail) > level:
            assignment[trail.pop()] = -1

    def search(propagate_from):
        nonlocal nodes
        if nodes >= node_budget:
            return None
        nodes += 1
        if not propagate(propagate_from):
            return False
        if all(value >= 0 for value in assignment):
            return assignment[:]
        variable = next(v for v in variable_order if assignment[v] < 0)
        preferred = 1 if occurrence[variable][1] > occurrence[variable][0] else 0
        for bit in (preferred, 1 - preferred):
            level = len(trail)
            assignment[variable] = bit
            trail.append(variable)
            result = search(level)
            if isinstance(result, list):
                return result
            undo(level)
            if result is None and nodes >= node_budget:
                return None
        return False

    result = search(0)
    candidate = _candidate_from_bits(inst, result) if isinstance(result, list) else None
    return candidate, nodes, operations


def _transform_instance(inst, permutation, pair_order=None, clause_order=None,
                        reverse_entries=False):
    """Carry an instance and certificate through genuine graph relabelings."""
    count = inst["vertex_count"]
    if sorted(permutation) != list(range(count)):
        raise ValueError("permutation is not a vertex relabeling")
    out = copy.deepcopy(inst)
    out["selectable"] = sorted(permutation[v] for v in inst["selectable"])
    out["literal_pairs"] = [[permutation[v] for v in pair]
                            for pair in inst["literal_pairs"]]
    out["clauses"] = [[permutation[v] for v in clause] for clause in inst["clauses"]]
    if pair_order is not None:
        out["literal_pairs"] = [out["literal_pairs"][i] for i in pair_order]
    if clause_order is not None:
        out["clauses"] = [out["clauses"][i] for i in clause_order]
    if reverse_entries:
        out["literal_pairs"] = [list(reversed(pair)) for pair in out["literal_pairs"]]
        out["clauses"] = [list(reversed(clause)) for clause in out["clauses"]]
    out["edges"] = [[permutation[u], permutation[v]] for u, v in inst["edges"]]
    out["implications"] = [[permutation[u], permutation[v]]
                            for u, v in inst["implications"]]
    if reverse_entries:
        out["edges"].reverse()
        out["implications"].reverse()
    out["root_input"] = permutation[inst["root_input"]]
    out["root_output"] = permutation[inst["root_output"]]
    # Base fields no longer describe numeric ranges after an arbitrary relabel;
    # render() is not used on transformed self-test instances.
    out["answer"] = sorted(permutation[v] for v in inst["answer"])
    return out


def _answer_size(answer):
    # Match emit.sh/harden.py, which use ordinary json.dumps with separators.
    encoded = json.dumps(answer)
    return {
        "chars": len(encoded),
        "tokens": math.ceil(len(encoded) / 4),
        "elements": len(answer),
    }


def selftest():
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    failures = []
    json_roundtrips = 0
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not failures and json_roundtrips == attempts,
        "attempts": attempts,
        "json_roundtrips": json_roundtrips,
        "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=90210, **shipping)
    answer = inst["answer"]
    swapped = answer[:]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicate = answer[:]
    duplicate[1] = duplicate[0]
    corruptions = {
        "drop_one": answer[:-1],
        "swap_order": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": answer[:-1] + [inst["vertex_count"]],
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = [row["reason"] for row in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in cases.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "cases": cases,
    }

    realistic = (
        "I decoded the implication gadget and checked the closure.\n\n```text\n"
        f"<answer>{_answer_text(answer)}</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("no tagged answer") is None,
        "parsed_length": len(parsed) if isinstance(parsed, list) else None,
        "garbage_returns_none": parse_answer("no tagged answer") is None,
    }

    samples = 200_000
    guess_rng = random.Random(0x230609870)
    hits = 0
    for _ in range(samples):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    measured = hits / samples
    report["G4_guess_resistance"] = {
        "pass": measured < 1e-6,
        "hits": hits,
        "total": samples,
        "measured_probability": measured,
        "structure_aware_space": search_space(inst),
        "sampler": "uniform one-of-two choice independently in every required literal pair",
    }

    baseline_start = time.perf_counter()
    baseline_candidate, baseline_nodes, baseline_operations = _dpll_attack(
        inst, node_budget=50_000
    )
    baseline_seconds = time.perf_counter() - baseline_start
    baseline_solved = bool(baseline_candidate and verify(inst, baseline_candidate)[0])
    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": hits == 0 and not baseline_solved and isinstance(demo_count, int),
        "shipping_valid_hits": hits,
        "shipping_density_samples": samples,
        "shipping_observed_solution_fraction": measured,
        "shipping_rule_of_three_upper_95pct": 3 / samples if hits == 0 else None,
        "demo_exact_solution_count": demo_count,
        "demo_search_space": search_space(demo),
        "baseline_wall_seconds": round(baseline_seconds, 6),
        "baseline_nodes": baseline_nodes,
        "baseline_literal_inspections": baseline_operations,
        "baseline_node_budget": 50_000,
        "baseline_solved": baseline_solved,
    }

    attack_names = [
        "outlier_literal_frequency",
        "greedy_clause_gain_no_backtrack",
        "random_restart_walksat_8x4000",
        "signed_pair_spectral_80_iterations",
        "signed_third_moment_tensor_plus_repair",
        "standard_dpll_unit_propagation_50000_nodes",
    ]
    attacks = {name: {"successes": 0, "attempts": 8} for name in attack_names}
    costs = {name: 0 for name in attack_names}
    for seed in range(3100, 3108):
        current = make_instance(seed=seed, **shipping)
        candidates = {
            attack_names[0]: _attack_frequency(current),
            attack_names[1]: _attack_greedy(current),
        }
        candidate, operations = _walksat(
            current, random.Random(seed ^ 0xA5A5A5A5)
        )
        candidates[attack_names[2]] = candidate
        costs[attack_names[2]] += operations
        candidate, operations = _spectral_pair_attack(current)
        candidates[attack_names[3]] = candidate
        costs[attack_names[3]] += operations
        candidate, operations = _tensor_third_moment_attack(
            current, random.Random(seed ^ 0xC3C3C3C3)
        )
        candidates[attack_names[4]] = candidate
        costs[attack_names[4]] += operations
        candidate, nodes, operations = _dpll_attack(current, node_budget=50_000)
        candidates[attack_names[5]] = candidate
        costs[attack_names[5]] += nodes
        for name, candidate in candidates.items():
            if candidate is not None and verify(current, candidate)[0]:
                attacks[name]["successes"] += 1
    for name in attack_names:
        attacks[name]["operations_or_nodes"] = costs[name]
    all_failed = all(row["successes"] == 0 for row in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attacks,
        "domain_standard_attack": attack_names[5],
        "construction_aware_attack": attack_names[4],
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=777, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    escalated = escalate(shipping)
    report["G7_scales"] = {
        "pass": doubled_ok and isinstance(escalated, dict) and escalated != shipping,
        "shipping_variables": inst["n_variables"],
        "shipping_vertices": inst["vertex_count"],
        "doubled_variables": doubled["n_variables"],
        "doubled_vertices": doubled["vertex_count"],
        "doubled_verify_reason": doubled_reason,
        "escalated_params": escalated,
    }

    invariance = 0
    witness_checks = 0
    invariant_failures = []
    unrelated = []
    for seed in range(20):
        original = make_instance(n=40, clause_ratio=10.1, mix_rounds=2, seed=7000 + seed)
        original_key = canonical_key(original)
        unrelated.append(original_key)
        rng = random.Random(9000 + seed)
        permutation = list(range(original["vertex_count"]))
        rng.shuffle(permutation)
        pair_order = list(range(len(original["literal_pairs"])))
        clause_order = list(range(len(original["clauses"])))
        rng.shuffle(pair_order)
        rng.shuffle(clause_order)
        variants = [
            _transform_instance(original, permutation),
            _transform_instance(original, permutation, pair_order=pair_order),
            _transform_instance(original, permutation, clause_order=clause_order),
            _transform_instance(original, permutation, pair_order, clause_order,
                                reverse_entries=True),
        ]
        for variant in variants:
            invariance += 1
            if canonical_key(variant) != original_key:
                invariant_failures.append([seed, "key changed under relabeling"])
            witness_checks += 1
            if not verify(variant, variant["answer"])[0]:
                invariant_failures.append([seed, "carried witness failed"])
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and len(set(unrelated)) == 20,
        "invariance_checks": invariance,
        "carried_witness_checks": witness_checks,
        "distinct_unrelated_keys": len(set(unrelated)),
        "unrelated_instances": 20,
        "failures": invariant_failures,
        "symmetries": "arbitrary graph-vertex relabeling, row/within-row/edge-order permutations, and compositions",
        "key_basis": "eight-round typed incidence refinement; never seed or rendered text",
    }

    size = _answer_size(answer)
    arms = {key: dict(_ORACLE_EVIDENCE[key]) for key in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"]
    placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"]
    intended_operations = inst["n_variables"]
    within_caps = (size["chars"] <= 2000 and size["elements"] <= 256
                   and intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": _ORACLE_EVIDENCE["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _ORACLE_EVIDENCE["hinted_verdict"],
        "answer_chars": size["chars"],
        "answer_tokens": size["tokens"],
        "answer_elements": size["elements"],
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
