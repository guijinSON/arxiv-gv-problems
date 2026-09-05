"""Affine-XOR knowledge-extraction instances from arXiv:2010.08281.

The paper's Theorem 1 reduces 3-SAT to finding a nearby input that makes a
majority-vote tree ensemble take a suspected True joint path.  This module
uses that exact reduction on a structured, satisfiable XOR subfamily.  A
solution is sampled before the forest is built, so generation never solves
the emitted instance.  Verification directly evaluates the displayed trees.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "logic",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "Boolean inputs with public nonzero binary-vector tags",
        "three-test Boolean decision trees",
        "a strict-majority tree ensemble with constant-False trees",
    ],
    "verification_operations": [
        "Boolean literal evaluation along each decision-tree path",
        "exact integer vote counting",
        "exact Hamming-distance comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 6, Theorem 1: the 3-SAT-to-tree-ensemble reduction for "
        "the L0 knowledge-extraction constraint (Eq. 10)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Repeated three-feature tree blocks are affine XOR equations on the "
        "public binary tags; setting the tagged basis features first turns a "
        "large forest into a short recurrence."
    ),
    "hardness_basis": (
        "Track B: Section 6 solves extraction by SMT and Theorem 1 makes the "
        "general problem NP-complete; on this promised affine subfamily, four-tree "
        "XOR recognition plus GF(2) Gaussian elimination is polynomial "
        "(O(e n^2) bit operations), while a domain-standard DPLL/unit-propagation "
        "solver also succeeds mechanically; at the shipping preset DPLL averages "
        "65,873 clause scans and elimination averages 1,140,137 scalar bit operations, "
        "with wall times recorded in selftest_report.json, versus exactly 240 XORs for "
        "the compact tag recurrence after the structure is recognized."
    ),
    "max_answer_tokens": 129,
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


# n is the number of Boolean input features and is one less than a power of 2.
# equation_factor controls redundant affine constraints without lengthening the
# witness.  The hard rung leaves room for the required roughly doubled build.
DIFFICULTY = {
    "demo": {"n": 7, "equation_factor": 1},
    "easy": {"n": 31, "equation_factor": 3},
    "medium": {"n": 63, "equation_factor": 4},
    "hard": {"n": 127, "equation_factor": 5},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Hint: Repeated four-tree blocks encode affine XOR constraints tied to the "
    "public nonzero binary-vector tags."
)
PLACEBO_HINT = (
    "Hint: Careful cross-checking of four-tree blocks helps avoid sign and "
    "indexing mistakes in the displayed data."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One contiguous bit string of exactly n characters; character i is "
        "the Boolean value of feature x_i, so every character is 0 or 1 and "
        "the order is fixed."
    ),
    "bounds": {
        "alphabet_size": 2,
        "minimum_length": 7,
        "length_from_instance": "exactly n",
        "shipping_length": 127,
        "candidate_count_from_instance": "2^n",
    },
}


# Populated after the script-owned three-arm runs.  The arms are diagnostic;
# G9's gate is only the answer/route cap.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0, "api_error_calls": 4},
    "hinted": {"solved": 0, "attempts": 0, "api_error_calls": 4},
    "placebo": {"solved": 0, "attempts": 0, "api_error_calls": 4},
    "hinted_verdict": "unmeasured_openrouter_http_403_key_limit",
}

NOTES = r"""
Definition. Section 2 defines a binary decision tree as a sequence of feature
tests ending at a labelled leaf, and an ensemble as a strict plurality/majority
of its tree labels.  Section 6 defines exact extraction and Eq. (10): find an
input x' within a fixed L0 distance of a training input that traverses a
suspected joint path labelled y.  Theorem 1 represents each 3-SAT clause by a
decision tree and adds one fewer constant-False tree than clause trees, so the
forest votes True exactly when every clause tree votes True.  This module uses
those objects directly; the signed triples are a compact, lossless notation
for the three tests and their early-True leaves.

Step-0 discriminator.  The paper's white-box knowledge insertion (Algorithm 2,
Section 5) is polynomial and its inserted range tests can be read from the
modified nodes, so treating the insertion itself as a Track-A search family
would be false.  The exact extraction problem is instead sent to SMT, its joint
path disjunction may be exponential in the ensemble size, and Theorem 1 proves
NP-completeness.  Our generated distribution is deliberately affine and thus
has a polynomial reference method: group the four clause trees on each feature
triple into one XOR equation and run Gaussian elimination over GF(2).  That is
why TRACK is B, not A.  Selftest records both its wall time and elementary bit
operation count at the shipping preset.

Generation and compact route.  Features are publicly tagged by every nonzero
d-bit vector.  A nonzero random quadratic Boolean form q and a random linear
form l are sampled first; q(tag) XOR l(tag) is the retained witness.  Every
equation has tags u,v,u XOR v and right side q(u) XOR q(v) XOR q(u XOR v), so
the linear part cancels and the planted vector satisfies it.  Each equation is
expanded into the four 3-CNF clauses that exclude the wrong parity, and each
clause is exactly the paper's three-test tree.  render() groups only trees with
the same three tested features and uses a canonical display order; this exposes
no vote that cannot be recovered by sorting the forest, but avoids turning the
intended route into a 2,540-line lookup exercise.  The compulsory equations with
u's lowest set bit form a recurrence; setting the d basis features to zero and
following those equations produces another valid witness in 2(n-d) XORs.  Extra
equations are redundant, sampled from the same XOR-tag relation, and shuffled
with the compulsory ones.  No clause or variable is marked as planted.
The generator accepts every n=2^d-1 with n>=7, so the mathematical family is
unbounded; only escalate() stops at the benchmark's answer and operation caps.

What is easy.  Gaussian elimination makes the affine subfamily easy with a
sandbox, and recognizing the tagged recurrence makes it compact by hand.
Section 6's outlier prefilter is heuristic and explicitly may yield false
alarms; it is not a certificate producer.  Section 7 says regression-tree
exact extraction is not obtained and is only conjectured, so regression is
excluded.  The generator also avoids Algorithm 2's visible insertion-node
signature and the paper's small-feature experimental regime (extraction uses
only three changed features there).

Attacks.  Four-clause XOR encodings have exactly balanced positive/negative
literal counts, defeating a literal-polarity outlier.  A one-pass clause-gain
greedy rule, uniform random restarts, the direct per-feature right-side-majority
ansatz, and the in-context all-zero baseline ansatz are measured on eight seeds.
DPLL/unit propagation and Gaussian elimination are reported separately as
successful Track-B references.  Plants and all other affine solutions differ
only by linear forms, so the stored plant has no special local signature.

Canonicalization.  Feature array positions and tag coordinates are presentation
choices.  The key recovers the XOR equations and applies deterministic colour
refinement to their signed variable-equation incidence graph.  It is invariant
under feature renumbering, tree reordering, literal-test reordering, global
GL(d,2) changes of tag basis, and their compositions.  Exact isomorphism of a
signed 3-uniform hypergraph is not known to be cheap, so the key is deliberately
the strongest inexpensive invariant used here rather than a complete canonical
labelling; this possible over-collision is documented in the README.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_GUESS_SAMPLES = 200_000
_ENUMERATION_CAP = 2_000_000
_ATTACK_SEEDS = tuple(range(8200, 8208))


def _validate_parameters(n: int, equation_factor: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 7:
        raise ValueError("n must be an integer at least 7")
    if n & (n + 1):
        raise ValueError("n must be one less than a power of two")
    if (
        isinstance(equation_factor, bool)
        or not isinstance(equation_factor, int)
        or not 1 <= equation_factor <= 8
    ):
        raise ValueError("equation_factor must be an integer in 1..8")


def _dimension(n: int) -> int:
    return (n + 1).bit_length() - 1


def _quadratic_value(tag: int, quadratic_mask: int, d: int) -> int:
    value = 0
    position = 0
    for i in range(d):
        for j in range(i + 1, d):
            if ((tag >> i) & 1) and ((tag >> j) & 1):
                value ^= (quadratic_mask >> position) & 1
            position += 1
    return value


def _affine_value(tag: int, quadratic_mask: int, linear_mask: int, d: int) -> int:
    return _quadratic_value(tag, quadratic_mask, d) ^ ((tag & linear_mask).bit_count() & 1)


def _xor_clauses(indices: tuple[int, int, int], rhs: int, rng: random.Random) -> list[list[int]]:
    """Four clauses false exactly on assignments of parity 1-rhs."""
    clauses: list[list[int]] = []
    for forbidden in itertools.product((0, 1), repeat=3):
        if (forbidden[0] ^ forbidden[1] ^ forbidden[2]) == rhs:
            continue
        clause = [
            (index + 1) if bit == 0 else -(index + 1)
            for index, bit in zip(indices, forbidden)
        ]
        rng.shuffle(clause)
        clauses.append(clause)
    return clauses


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a satisfiable affine extraction instance."""
    equation_factor = params.pop("equation_factor", 3)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_parameters(n, equation_factor)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    d = _dimension(n)
    coefficient_count = d * (d - 1) // 2
    quadratic_mask = rng.randrange(1, 1 << coefficient_count)
    linear_mask = rng.randrange(1 << d)

    tags = list(range(1, n + 1))
    rng.shuffle(tags)
    index_of = {tag: index for index, tag in enumerate(tags)}

    # The compulsory rows are a triangular recurrence when tags are ordered by
    # Hamming weight.  Random redundant rows crowd the forest without changing
    # either the certificate length or the compact route.
    triples: set[tuple[int, int, int]] = set()
    for tag in range(1, n + 1):
        if tag & (tag - 1):
            basis = tag & -tag
            triples.add(tuple(sorted((basis, tag ^ basis, tag))))

    maximum_triples = n * (n - 1) // 6
    target = min(maximum_triples, max(len(triples), equation_factor * n))
    while len(triples) < target:
        left = rng.randrange(1, n + 1)
        right = rng.randrange(1, n + 1)
        if left == right:
            continue
        triples.add(tuple(sorted((left, right, left ^ right))))

    equations: list[tuple[tuple[int, int, int], int]] = []
    for tag_triple in triples:
        indices = tuple(index_of[tag] for tag in tag_triple)
        rhs = 0
        for tag in tag_triple:
            rhs ^= _quadratic_value(tag, quadratic_mask, d)
        equations.append((indices, rhs))
    rng.shuffle(equations)

    clause_trees: list[list[int]] = []
    for indices, rhs in equations:
        clause_trees.extend(_xor_clauses(indices, rhs, rng))
    rng.shuffle(clause_trees)

    planted = "".join(
        str(_affine_value(tag, quadratic_mask, linear_mask, d)) for tag in tags
    )
    baseline = "0" * n
    false_trees = len(clause_trees) - 1
    return {
        "family": "affine_xor_tree_ensemble_extraction",
        "n": n,
        "tag_bits": d,
        "tags": tags,
        "clause_trees": clause_trees,
        "constant_false_trees": false_trees,
        "baseline": baseline,
        "l0_budget": n,
        "target_label": True,
        "equation_factor": equation_factor,
        "answer": planted,
    }


def _literal_text(literal: int) -> str:
    return ("+" if literal > 0 else "-") + str(abs(literal))


def _display_blocks(inst: dict) -> list[tuple[tuple[int, int, int], list[list[int]]]]:
    """Group equivalent clause-tree supports for a compact, canonical display.

    The four trees in a block remain four independent ensemble votes.  Sorting
    their three tests and sorting the trees within a support are semantic
    symmetries of disjunction; the instance itself remains shuffled.
    """
    groups: dict[tuple[int, int, int], list[list[int]]] = {}
    for clause in inst["clause_trees"]:
        support = tuple(sorted(abs(literal) - 1 for literal in clause))
        groups.setdefault(support, []).append(clause)

    tags = inst["tags"]
    blocks: list[tuple[tuple[int, int, int], list[list[int]]]] = []
    for support, clauses in groups.items():
        if len(clauses) != 4:
            raise ValueError("clause trees do not form four-tree blocks")
        ordered_support = tuple(sorted(support, key=lambda index: tags[index]))
        normalized = []
        for clause in clauses:
            by_index = {abs(literal) - 1: literal for literal in clause}
            normalized.append([by_index[index] for index in ordered_support])
        normalized.sort(
            key=lambda clause: tuple(0 if literal > 0 else 1 for literal in clause)
        )
        tag_triple = tuple(tags[index] for index in ordered_support)
        blocks.append((tag_triple, normalized))
    blocks.sort(key=lambda item: item[0])
    return blocks


def render(inst: dict) -> str:
    n = inst["n"]
    d = inst["tag_bits"]
    tags = inst["tags"]
    clauses = inst["clause_trees"]
    tag_lines = []
    for start in range(0, n, 8):
        tag_lines.append(
            "  "
            + "  ".join(
                f"x_{i}=<{tags[i]:0{d}b}>" for i in range(start, min(n, start + 8))
            )
        )
    block_lines = []
    for block_index, (tag_triple, block_clauses) in enumerate(_display_blocks(inst)):
        tag_text = ",".join(f"{tag:0{d}b}" for tag in tag_triple)
        tree_text = " | ".join(
            "(" + " ".join(_literal_text(lit) for lit in clause) + ")"
            for clause in block_clauses
        )
        block_lines.append(f"  B_{block_index} <{tag_text}>: {tree_text}")
    statement = f"""Knowledge extraction from a Boolean tree ensemble

There are {n} Boolean input features x_0,...,x_{n - 1}.  A candidate input is
a bit string z of length {n}; its character at zero-based position i is x_i.
The features also have the following public, fixed {d}-bit vector tags.  Angle
brackets delimit a tag and are not part of the feature value:
{chr(10).join(tag_lines)}

The ensemble contains the {len(clauses)} clause trees listed below and
{inst['constant_false_trees']} additional constant-False trees.  In a clause
tree, +j means the literal x_(j-1)=1 and -j means x_(j-1)=0; signed feature
numbers are therefore one-based even though bit-string positions are
zero-based.  A listed tree tests its three literals from left to right, returns
True immediately when a literal is true, and returns False if all three are
false.  Reordering the three tests would not change that tree's Boolean
function.  The complete ensemble returns the label with a strict majority of
votes.  Its total number of trees is odd, so there is no tie.

For compact display, each B-line groups the four separate clause trees that
test the same three features.  Parentheses delimit individual trees and the
vertical bar separates them; every parenthesized tree contributes one vote.
The angle-bracket header repeats those features' public tags in increasing
binary order.  Blocks are ordered lexicographically by their tag triples.
Grouping and ordering are presentation only and do not add a vote or constraint.

Clause-tree blocks:
{chr(10).join(block_lines)}

The baseline input is {inst['baseline']}.  The L0 distance between two bit
strings is the number of positions at which they differ.  Find any candidate
z whose L0 distance from the baseline is at most {inst['l0_budget']} and for
which the ensemble's strict-majority label is True.  Any such input is valid;
you do not have to recover a distinguished planted input."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    statement += f"""

Give your final answer inside <answer></answer> tags as one contiguous
{n}-character bit string in x_0,...,x_{n - 1} order.
Example format (showing syntax, not a claimed solution): <answer>{'0' * n}</answer>
Output nothing else inside the tags."""
    return statement


def parse_answer(text: object) -> object | None:
    if not isinstance(text, str):
        return None
    for raw_body in reversed(_ANSWER_RE.findall(text)):
        body = raw_body.strip()
        body = re.sub(r"^```(?:text|json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
        if len(body) >= 2 and body[0] == body[-1] and body[0] in "\"'":
            body = body[1:-1].strip()
        if re.fullmatch(r"[01]+", body):
            return body
        # Tolerate a model spacing or comma-separating individual bits.
        if re.fullmatch(r"[01](?:[\s,]+[01])+", body):
            return "".join(re.findall(r"[01]", body))
    return None


def _clause_value(clause: list[int], answer: str) -> bool:
    for literal in clause:
        bit = answer[abs(literal) - 1] == "1"
        if bit == (literal > 0):
            return True
    return False


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, str):
        return False, "answer must be a bit string"
    if answer == "":
        return False, "answer is empty"
    n = inst.get("n")
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        return False, "instance feature count is malformed"
    if len(answer) < n:
        return False, f"answer is too short: expected {n} bits"
    if len(answer) > n:
        return False, f"answer is too long: expected {n} bits"
    if any(bit not in "01" for bit in answer):
        return False, "answer contains a non-binary character"

    baseline = inst.get("baseline")
    budget = inst.get("l0_budget")
    if not isinstance(baseline, str) or len(baseline) != n:
        return False, "instance baseline is malformed"
    if isinstance(budget, bool) or not isinstance(budget, int) or budget < 0:
        return False, "instance L0 budget is malformed"
    distance = sum(a != b for a, b in zip(answer, baseline))
    if distance > budget:
        return False, f"L0 distance {distance} exceeds budget {budget}"

    clauses = inst.get("clause_trees")
    false_trees = inst.get("constant_false_trees")
    if (
        not isinstance(clauses, list)
        or isinstance(false_trees, bool)
        or not isinstance(false_trees, int)
        or false_trees < 0
    ):
        return False, "instance forest is malformed"
    true_votes = 0
    first_false = None
    for tree_index, clause in enumerate(clauses):
        if (
            not isinstance(clause, list)
            or len(clause) != 3
            or any(isinstance(x, bool) or not isinstance(x, int) or x == 0 or abs(x) > n for x in clause)
            or len({abs(x) for x in clause}) != 3
        ):
            return False, "instance contains a malformed clause tree"
        if _clause_value(clause, answer):
            true_votes += 1
        elif first_false is None:
            first_false = tree_index
    if true_votes <= (len(clauses) + false_trees) // 2:
        detail = f": clause tree {first_false} voted False" if first_false is not None else ""
        return False, "forest majority is False" + detail
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    n = inst["n"]
    return format(rng.getrandbits(n), f"0{n}b")


def search_space(inst: dict) -> int | None:
    return 1 << inst["n"]


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    n = inst["n"]
    count = 0
    for value in range(space):
        candidate = format(value, f"0{n}b")
        count += int(verify(inst, candidate)[0])
    return count


def canonical_key(inst: dict) -> str:
    """Strong cheap invariant under feature, tree, test, and tag-basis relabelling.

    Exact isomorphism of the signed 3-uniform incidence structure is not known
    to be cheap.  Colour refinement gives a deterministic structural fingerprint
    and, unlike hashing the rendered tags, also quotients a global GL(d,2)
    change of coordinates on those tags.
    """
    n = inst["n"]
    tags = inst["tags"]
    if len(tags) != n or len(set(tags)) != n:
        raise ValueError("malformed tag list")
    equations = _extract_xor_equations(inst)
    baseline = inst.get("baseline")
    if not isinstance(baseline, str) or len(baseline) != n:
        raise ValueError("malformed baseline")

    incident: list[list[int]] = [[] for _ in range(n)]
    for edge_index, (indices, _) in enumerate(equations):
        for index in indices:
            incident[index].append(edge_index)

    # One-dimensional Weisfeiler--Lehman refinement on the bipartite incidence
    # graph, with equation right sides and baseline bits as initial colours.
    variable_colours = [int(bit) for bit in baseline]
    equation_colours = [rhs for _, rhs in equations]
    for _ in range(n + 1):
        variable_signatures = [
            (variable_colours[index], tuple(sorted(equation_colours[e] for e in incident[index])))
            for index in range(n)
        ]
        variable_palette = {
            signature: colour
            for colour, signature in enumerate(sorted(set(variable_signatures)))
        }
        new_variable_colours = [variable_palette[s] for s in variable_signatures]

        equation_signatures = [
            (rhs, tuple(sorted(new_variable_colours[index] for index in indices)))
            for indices, rhs in equations
        ]
        equation_palette = {
            signature: colour
            for colour, signature in enumerate(sorted(set(equation_signatures)))
        }
        new_equation_colours = [equation_palette[s] for s in equation_signatures]
        if (
            new_variable_colours == variable_colours
            and new_equation_colours == equation_colours
        ):
            break
        variable_colours = new_variable_colours
        equation_colours = new_equation_colours

    canonical_equations = tuple(
        sorted(
            (rhs, tuple(sorted(variable_colours[index] for index in indices)))
            for indices, rhs in equations
        )
    )
    payload = (
        n,
        inst["tag_bits"],
        tuple(sorted(variable_colours)),
        canonical_equations,
        inst["constant_false_trees"],
        inst["l0_budget"],
        inst["target_label"],
    )
    raw = repr(payload).encode("ascii")
    return hashlib.sha256(raw).hexdigest()


def escalate(params: dict) -> dict | str | None:
    result = dict(params)
    n = int(result.get("n", 31))
    factor = int(result.get("equation_factor", 3))
    if factor < 8:
        result["equation_factor"] = factor + 1
        return result
    if n < 255:
        next_n = 2 * n + 1
        next_operations = 2 * (next_n - _dimension(next_n))
        if next_n > 256 or next_operations > 300:
            return "cap_bound"
        result["n"] = next_n
        result["equation_factor"] = 5
        return result
    return "cap_bound"


def _extract_xor_equations(inst: dict) -> list[tuple[tuple[int, int, int], int]]:
    """Recognize the four-tree 3-CNF encoding of every XOR row."""
    groups: dict[tuple[int, int, int], list[list[int]]] = {}
    for clause in inst["clause_trees"]:
        key = tuple(sorted(abs(literal) - 1 for literal in clause))
        groups.setdefault(key, []).append(clause)
    equations = []
    for key, clauses in groups.items():
        if len(clauses) != 4:
            raise ValueError("clause trees do not form four-tree XOR blocks")
        forbidden_patterns = set()
        forbidden_parities = set()
        for clause in clauses:
            by_index = {abs(literal) - 1: literal for literal in clause}
            forbidden = tuple(0 if by_index[index] > 0 else 1 for index in key)
            forbidden_patterns.add(forbidden)
            forbidden_parities.add(forbidden[0] ^ forbidden[1] ^ forbidden[2])
        if len(forbidden_patterns) != 4 or len(forbidden_parities) != 1:
            raise ValueError("malformed XOR clause block")
        forbidden_parity = next(iter(forbidden_parities))
        equations.append((key, 1 ^ forbidden_parity))
    return equations


def _reference_gaussian(inst: dict) -> tuple[str | None, dict]:
    """Polynomial Track-B reference solver, with elementary bit-op accounting."""
    started = time.perf_counter()
    n = inst["n"]
    equations = _extract_xor_equations(inst)
    variable_mask = (1 << n) - 1
    pivots: dict[int, int] = {}
    bit_operations = 0
    row_xors = 0
    pivot_tests = 0
    for indices, rhs in equations:
        row = (1 << indices[0]) | (1 << indices[1]) | (1 << indices[2]) | (rhs << n)
        while row & variable_mask:
            pivot = (row & variable_mask).bit_length() - 1
            pivot_tests += 1
            bit_operations += 1
            if pivot in pivots:
                row ^= pivots[pivot]
                row_xors += 1
                bit_operations += n + 1
            else:
                pivots[pivot] = row
                break
        if not (row & variable_mask) and ((row >> n) & 1):
            return None, {
                "wall_clock_sec": time.perf_counter() - started,
                "bit_operations": bit_operations,
                "row_xors": row_xors,
                "pivot_tests": pivot_tests,
                "rank": len(pivots),
            }

    solution = 0
    for pivot, row in sorted(pivots.items()):
        lower = row & ((1 << pivot) - 1)
        rhs = (row >> n) & 1
        bit = rhs ^ ((lower & solution).bit_count() & 1)
        bit_operations += pivot + 2
        if bit:
            solution |= 1 << pivot
    answer = "".join("1" if (solution >> i) & 1 else "0" for i in range(n))
    return answer, {
        "wall_clock_sec": time.perf_counter() - started,
        "bit_operations": bit_operations,
        "row_xors": row_xors,
        "pivot_tests": pivot_tests,
        "rank": len(pivots),
    }


def _reference_dpll(inst: dict) -> tuple[str | None, dict]:
    """A small domain-standard SAT baseline: DPLL with unit propagation."""
    started = time.perf_counter()
    clauses = inst["clause_trees"]
    n = inst["n"]
    activity = [0] * n
    for clause in clauses:
        for literal in clause:
            activity[abs(literal) - 1] += 1

    metrics = {
        "nodes": 0,
        "decisions": 0,
        "propagations": 0,
        "clause_scans": 0,
        "literal_checks": 0,
    }

    def solve(values: list[int]) -> list[int] | None:
        metrics["nodes"] += 1
        while True:
            unit_literal = None
            all_satisfied = True
            for clause in clauses:
                metrics["clause_scans"] += 1
                unknown = []
                satisfied = False
                for literal in clause:
                    metrics["literal_checks"] += 1
                    value = values[abs(literal) - 1]
                    if value < 0:
                        unknown.append(literal)
                    elif bool(value) == (literal > 0):
                        satisfied = True
                        break
                if satisfied:
                    continue
                all_satisfied = False
                if not unknown:
                    return None
                if len(unknown) == 1:
                    unit_literal = unknown[0]
                    break
            if all_satisfied:
                return [0 if value < 0 else value for value in values]
            if unit_literal is None:
                break
            index = abs(unit_literal) - 1
            forced = int(unit_literal > 0)
            if values[index] >= 0 and values[index] != forced:
                return None
            if values[index] < 0:
                values[index] = forced
                metrics["propagations"] += 1

        variable = max(
            (index for index, value in enumerate(values) if value < 0),
            key=lambda index: (activity[index], -index),
            default=None,
        )
        if variable is None:
            return values
        for chosen in (0, 1):
            metrics["decisions"] += 1
            branch = values.copy()
            branch[variable] = chosen
            result = solve(branch)
            if result is not None:
                return result
        return None

    solution = solve([-1] * n)
    metrics["wall_clock_sec"] = time.perf_counter() - started
    if solution is None:
        return None, metrics
    return "".join(map(str, solution)), metrics


def _compact_tag_recurrence(inst: dict) -> tuple[str, dict]:
    """Execute the intended no-tool route without consulting the planted answer.

    Basis-tagged variables are free and are set to zero.  Every other tag t has
    a compulsory row on (lowbit(t), t XOR lowbit(t), t), whose first two values
    are already known when tags are processed by Hamming weight.
    """
    started = time.perf_counter()
    equations = _extract_xor_equations(inst)
    tags = inst["tags"]
    index_of_tag = {tag: index for index, tag in enumerate(tags)}
    rhs_by_tags = {
        tuple(sorted(tags[index] for index in indices)): rhs
        for indices, rhs in equations
    }
    values: dict[int, int] = {}
    xor_operations = 0
    for tag in sorted(tags, key=lambda value: (value.bit_count(), value)):
        if tag & (tag - 1) == 0:
            values[tag] = 0
            continue
        basis = tag & -tag
        remainder = tag ^ basis
        rhs = rhs_by_tags[tuple(sorted((basis, remainder, tag)))]
        values[tag] = values[basis] ^ values[remainder] ^ rhs
        xor_operations += 2
    answer = "".join(str(values[tag]) for tag in tags)
    return answer, {
        "wall_clock_sec": time.perf_counter() - started,
        "xor_operations": xor_operations,
        "basis_assignments": inst["tag_bits"],
        "derived_features": inst["n"] - inst["tag_bits"],
    }


def _equation_violations(equations: list[tuple[tuple[int, int, int], int]], bits: list[int]) -> int:
    return sum((bits[a] ^ bits[b] ^ bits[c]) != rhs for (a, b, c), rhs in equations)


def _candidate_satisfies_equations(
    candidate: str, equations: list[tuple[tuple[int, int, int], int]]
) -> bool:
    """Fast exact equivalent of the forest vote for prevalidated instances."""
    for (a, b, c), rhs in equations:
        if ((candidate[a] == "1") ^ (candidate[b] == "1") ^ (candidate[c] == "1")) != bool(rhs):
            return False
    return True


def _attack_outlier_tag_degree(inst: dict) -> tuple[str, int]:
    equations = _extract_xor_equations(inst)
    degree = [0] * inst["n"]
    for indices, _ in equations:
        for index in indices:
            degree[index] += 1
    ordered = sorted(degree)
    median = ordered[len(ordered) // 2]
    return "".join("1" if value > median else "0" for value in degree), len(equations) * 3


def _attack_greedy_single_sweep(inst: dict) -> tuple[str, int]:
    equations = _extract_xor_equations(inst)
    bits = [0] * inst["n"]
    operations = 0
    current = _equation_violations(equations, bits)
    operations += len(equations)
    # A deliberately plausible no-backtracking local repair: keep a flip only
    # if it strictly improves the number of satisfied clause blocks.
    for index in range(inst["n"]):
        bits[index] ^= 1
        trial = _equation_violations(equations, bits)
        operations += len(equations)
        if trial < current:
            current = trial
        else:
            bits[index] ^= 1
    return "".join(map(str, bits)), operations


def _attack_random_restart(inst: dict, seed: int, restarts: int = 256) -> tuple[str | None, int]:
    rng = random.Random(seed)
    equations = _extract_xor_equations(inst)
    for attempt in range(restarts):
        candidate = random_candidate(inst, rng)
        if _candidate_satisfies_equations(candidate, equations):
            return candidate, attempt + 1
    return None, restarts


def _attack_rhs_majority(inst: dict) -> tuple[str, int]:
    equations = _extract_xor_equations(inst)
    zero_votes = [0] * inst["n"]
    one_votes = [0] * inst["n"]
    for indices, rhs in equations:
        for index in indices:
            if rhs:
                one_votes[index] += 1
            else:
                zero_votes[index] += 1
    answer = "".join(
        "1" if one_votes[index] > zero_votes[index] else "0" for index in range(inst["n"])
    )
    return answer, len(equations) * 3


def _attack_all_zero_baseline(inst: dict) -> tuple[str, int]:
    """The most obvious in-context ansatz: submit the displayed baseline."""
    return "0" * inst["n"], inst["n"]


def _run_adversary_panel(params: dict) -> dict:
    names = (
        "outlier_tag_degree",
        "greedy_single_sweep",
        "random_restart_256",
        "rhs_majority_ansatz",
        "all_zero_baseline_ansatz",
    )
    results = {
        name: {"successes": 0, "attempts": 0, "operations": 0, "wall_clock_sec": 0.0}
        for name in names
    }
    reference_successes = 0
    reference_operations = 0
    reference_wall = 0.0
    reference_ranks = []
    dpll_successes = 0
    dpll_clause_scans = 0
    dpll_literal_checks = 0
    dpll_nodes = 0
    dpll_wall = 0.0
    for attack_seed in _ATTACK_SEEDS:
        inst = make_instance(seed=attack_seed, **params)
        attacks = {
            "outlier_tag_degree": lambda: _attack_outlier_tag_degree(inst),
            "greedy_single_sweep": lambda: _attack_greedy_single_sweep(inst),
            "random_restart_256": lambda: _attack_random_restart(inst, attack_seed ^ 0x5A5A),
            "rhs_majority_ansatz": lambda: _attack_rhs_majority(inst),
            "all_zero_baseline_ansatz": lambda: _attack_all_zero_baseline(inst),
        }
        for name, attack in attacks.items():
            started = time.perf_counter()
            candidate, operations = attack()
            elapsed = time.perf_counter() - started
            results[name]["attempts"] += 1
            results[name]["operations"] += operations
            results[name]["wall_clock_sec"] += elapsed
            if candidate is not None and verify(inst, candidate)[0]:
                results[name]["successes"] += 1

        reference, metrics = _reference_gaussian(inst)
        reference_successes += int(reference is not None and verify(inst, reference)[0])
        reference_operations += metrics["bit_operations"]
        reference_wall += metrics["wall_clock_sec"]
        reference_ranks.append(metrics["rank"])

        dpll_answer, dpll_metrics = _reference_dpll(inst)
        dpll_successes += int(dpll_answer is not None and verify(inst, dpll_answer)[0])
        dpll_clause_scans += dpll_metrics["clause_scans"]
        dpll_literal_checks += dpll_metrics["literal_checks"]
        dpll_nodes += dpll_metrics["nodes"]
        dpll_wall += dpll_metrics["wall_clock_sec"]

    for value in results.values():
        value["wall_clock_sec"] = round(value["wall_clock_sec"], 6)
    all_failed = all(value["successes"] == 0 for value in results.values())
    return {
        "pass": (
            all_failed
            and reference_successes == len(_ATTACK_SEEDS)
            and dpll_successes == len(_ATTACK_SEEDS)
        ),
        "attacks": results,
        "reference_algorithm": {
            "name": "DPLL with unit propagation (domain-standard SAT baseline)",
            "complexity": (
                "O(2^n*C) clause work in the worst case; the promised XOR "
                "subfamily also admits polynomial GF(2) elimination"
            ),
            "wall_clock_sec": round(dpll_wall, 6),
            "average_wall_clock_sec": round(dpll_wall / len(_ATTACK_SEEDS), 6),
            "operations": dpll_clause_scans,
            "operation_unit": "clause scans",
            "average_operations": dpll_clause_scans // len(_ATTACK_SEEDS),
            "literal_checks": dpll_literal_checks,
            "nodes": dpll_nodes,
            "solves": f"{dpll_successes}/{len(_ATTACK_SEEDS)}, as expected",
            "promised_polynomial_algorithm": {
                "name": "four-tree XOR recognition plus GF(2) Gaussian elimination",
                "complexity": "O(e*n^2) elementary bit operations; polynomial",
                "wall_clock_sec": round(reference_wall, 6),
                "average_wall_clock_sec": round(
                    reference_wall / len(_ATTACK_SEEDS), 6
                ),
                "operations": reference_operations,
                "average_operations": reference_operations // len(_ATTACK_SEEDS),
                "operation_unit": "scalar bit operations",
                "ranks": reference_ranks,
                "solves": f"{reference_successes}/{len(_ATTACK_SEEDS)}, as expected",
            },
        },
    }


def _relabel_instance(inst: dict, rng: random.Random) -> tuple[dict, str]:
    """Reorder features, trees, and literal tests; carry the answer through."""
    n = inst["n"]
    old_at_new = list(range(n))
    rng.shuffle(old_at_new)
    new_of_old = [0] * n
    for new, old in enumerate(old_at_new):
        new_of_old[old] = new

    transformed = {key: value for key, value in inst.items() if key != "answer"}
    transformed["tags"] = [inst["tags"][old] for old in old_at_new]
    transformed["baseline"] = "".join(inst["baseline"][old] for old in old_at_new)
    clauses = []
    for old_clause in reversed(inst["clause_trees"]):
        clause = []
        for literal in reversed(old_clause):
            new_index = new_of_old[abs(literal) - 1] + 1
            clause.append(new_index if literal > 0 else -new_index)
        clauses.append(clause)
    transformed["clause_trees"] = clauses
    carried = "".join(inst["answer"][old] for old in old_at_new)
    transformed["answer"] = carried
    return transformed, carried


def _reorder_trees(inst: dict) -> tuple[dict, str]:
    transformed = {key: value for key, value in inst.items() if key != "answer"}
    transformed["clause_trees"] = list(reversed(inst["clause_trees"]))
    transformed["answer"] = inst["answer"]
    return transformed, inst["answer"]


def _reorder_tests(inst: dict) -> tuple[dict, str]:
    transformed = {key: value for key, value in inst.items() if key != "answer"}
    transformed["clause_trees"] = [list(reversed(clause)) for clause in inst["clause_trees"]]
    transformed["answer"] = inst["answer"]
    return transformed, inst["answer"]


def _change_tag_basis(inst: dict) -> tuple[dict, str]:
    """Apply the invertible transvection e_0 -> e_0+e_1 to every tag."""
    transformed = {key: value for key, value in inst.items() if key != "answer"}
    transformed["tags"] = [tag ^ (((tag >> 0) & 1) << 1) for tag in inst["tags"]]
    transformed["answer"] = inst["answer"]
    return transformed, inst["answer"]


def _corruptions(inst: dict) -> dict[str, object]:
    answer = inst["answer"]
    left = next(i for i, bit in enumerate(answer) if bit == "0")
    right = next(i for i, bit in enumerate(answer) if bit == "1")
    swapped = list(answer)
    swapped[left], swapped[right] = swapped[right], swapped[left]
    return {
        "drop_one": answer[:-1],
        "swap_unequal": "".join(swapped),
        "duplicate_one": answer + answer[-1],
        "empty": "",
        "out_of_range": "2" + answer[1:],
    }


def selftest() -> dict:
    report: dict[str, object] = {
        "paper": "arXiv:2010.08281",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1: every named rung, several independently generated instances.
    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed, "reason": "answer not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=4242, **shipping_params)
    corruptions = {}
    reasons = set()
    for name, candidate in _corruptions(shipping).items():
        ok, reason = verify(shipping, candidate)
        corruptions[name] = {"rejected": not ok, "reason": reason}
        reasons.add(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(value["rejected"] for value in corruptions.values()) and len(reasons) == len(corruptions),
        "corruptions": corruptions,
        "distinct_reasons": len(reasons),
    }

    realistic = (
        "I grouped the repeated paths and checked the vote.\n\n```text\n"
        f"<answer>{shipping['answer']}</answer>\n```"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": (
            parsed == shipping["answer"]
            and verify(shipping, parsed)[0]
            and parse_answer("no tagged answer here") is None
        ),
        "parsed_matches": parsed == shipping["answer"],
        "garbage_returns_none": parse_answer("no tagged answer here") is None,
    }

    guess_rng = random.Random(99173)
    guess_hits = 0
    shipping_equations = _extract_xor_equations(shipping)
    guess_started = time.perf_counter()
    for _ in range(_GUESS_SAMPLES):
        candidate = random_candidate(shipping, guess_rng)
        guess_hits += int(_candidate_satisfies_equations(candidate, shipping_equations))
    guess_elapsed = time.perf_counter() - guess_started
    report["G4_guess_resistance"] = {
        "pass": guess_hits / _GUESS_SAMPLES < 1e-6,
        "hits": guess_hits,
        "total": _GUESS_SAMPLES,
        "observed_probability": guess_hits / _GUESS_SAMPLES,
        "structure_aware_space": str(search_space(shipping)),
        "sampling_wall_clock_sec": round(guess_elapsed, 6),
    }

    panel = _run_adversary_panel(shipping_params)
    shipping_reference, shipping_reference_metrics = _reference_gaussian(shipping)
    shipping_rank = shipping_reference_metrics["rank"]
    shipping_exact_count = 1 << (shipping["n"] - shipping_rank)
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    strongest_name = max(
        panel["attacks"],
        key=lambda name: panel["attacks"][name]["operations"],
    )
    report["G5_density_and_baseline"] = {
        "pass": (
            panel["pass"]
            and shipping_reference is not None
            and verify(shipping, shipping_reference)[0]
            and shipping_rank == shipping["n"] - shipping["tag_bits"]
            and demo_count == (1 << demo["tag_bits"])
        ),
        # Kept at top level as well as in the descriptive records below so the
        # repository's mechanical gate can see both required measured numbers.
        "shipping_valid_hits": guess_hits,
        "shipping_samples": _GUESS_SAMPLES,
        "shipping_density_fraction": guess_hits / _GUESS_SAMPLES,
        "baseline_operations": panel["attacks"][strongest_name]["operations"] // len(_ATTACK_SEEDS),
        "baseline_wall_clock_sec": round(
            panel["attacks"][strongest_name]["wall_clock_sec"] / len(_ATTACK_SEEDS), 6
        ),
        "shipping_density": {
            "method": (
                "structure-aware uniform sampling from all n-bit inputs, checked "
                "against the exact XOR rows decoded from the forest"
            ),
            "hits": guess_hits,
            "samples": _GUESS_SAMPLES,
            "observed_fraction": guess_hits / _GUESS_SAMPLES,
            "measured_gf2_rank": shipping_rank,
            "exact_solution_count_by_rank": shipping_exact_count,
            "exact_fraction": f"2^-{shipping_rank}",
        },
        "small_preset_exact_count": {
            "preset": "demo",
            "n": demo["n"],
            "valid_answers": demo_count,
            "candidate_space": search_space(demo),
        },
        "strongest_failing_attack": {
            "name": strongest_name,
            **panel["attacks"][strongest_name],
        },
        "reference_cost": panel["reference_algorithm"],
    }
    report["G6_adversary_panel"] = panel

    next_n = 2 * shipping["n"] + 1
    doubled = make_instance(n=next_n, seed=31337, equation_factor=shipping["equation_factor"])
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    beyond_cap_n = 2 * next_n + 1
    beyond_cap = make_instance(
        n=beyond_cap_n,
        seed=31338,
        equation_factor=shipping["equation_factor"],
    )
    beyond_cap_ok, beyond_cap_reason = verify(beyond_cap, beyond_cap["answer"])
    report["G7_scales"] = {
        "pass": (
            doubled_ok
            and beyond_cap_ok
            and search_space(doubled) > search_space(shipping)
            and search_space(beyond_cap) > search_space(doubled)
        ),
        "shipping_n": shipping["n"],
        "next_supported_n": next_n,
        "size_ratio": next_n / shipping["n"],
        "shipping_clause_trees": len(shipping["clause_trees"]),
        "doubled_clause_trees": len(doubled["clause_trees"]),
        "doubled_verify_reason": doubled_reason,
        "beyond_shipping_cap_n": beyond_cap_n,
        "beyond_shipping_cap_clause_trees": len(beyond_cap["clause_trees"]),
        "beyond_shipping_cap_verify_reason": beyond_cap_reason,
        "generator_size_bound": None,
    }

    invariance_checks = 0
    carried_checks = 0
    invariant_failures = []
    distinct_keys = set()
    for seed in range(20):
        original = make_instance(seed=1000 + seed, **DIFFICULTY["easy"])
        feature_and_order, carried = _relabel_instance(original, random.Random(9000 + seed))
        variants = {
            "feature_tree_test_composition": (feature_and_order, carried),
            "tree_order": _reorder_trees(original),
            "literal_test_order": _reorder_tests(original),
            "tag_basis": _change_tag_basis(original),
            "tag_basis_after_composition": _change_tag_basis(feature_and_order),
        }
        for transformation, (transformed, transformed_answer) in variants.items():
            invariance_checks += 1
            if canonical_key(original) != canonical_key(transformed):
                invariant_failures.append({"seed": seed, "transformation": transformation})
            carried_checks += int(verify(transformed, transformed_answer)[0])
        distinct_keys.add(canonical_key(make_instance(seed=2000 + seed, **DIFFICULTY["easy"])))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and carried_checks == 100 and len(distinct_keys) == 20,
        "invariance_checks": invariance_checks,
        "invariance_failures": invariant_failures,
        "carried_witness_verifications": carried_checks,
        "unrelated_distinct_keys": len(distinct_keys),
        "unrelated_instances": 20,
        "transformations": [
            "feature renumbering with tags carried",
            "clause-tree reordering",
            "literal-test reordering",
            "global GL(d,2) tag-coordinate transvection",
            "compositions of the above transformations",
        ],
    }

    serialized = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_elements = len(shipping["answer"])
    answer_tokens = len(serialized)  # conservative: at most one token per character
    compact_answer, compact_metrics = _compact_tag_recurrence(shipping)
    compact_ok, compact_reason = verify(shipping, compact_answer)
    intended_operations = compact_metrics["xor_operations"]
    arms = {
        name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else 0.0
    )
    within_caps = (
        len(serialized) <= 2000
        and answer_elements <= 256
        and answer_tokens <= 500
        and intended_operations <= 300
        and compact_ok
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "diagnostic_recorded_not_gated": True,
        "answer_chars": len(serialized),
        "answer_tokens": answer_tokens,
        "answer_token_measure": "conservative upper bound of one token per serialized character",
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "intended_route_execution": {
            "verified": compact_ok,
            "verify_reason": compact_reason,
            **compact_metrics,
        },
    }

    gate_values = [value for key, value in report.items() if key.startswith("G")]
    report["all_pass"] = all(value.get("pass") is True for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
