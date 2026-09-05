"""Verified Track-B instances of subpower membership in the Brandt semigroup.

The module implements the SAT-to-SMP construction in Theorem 1.1 of Markus
Steindl, "On semigroups with PSPACE-complete subpower membership problem"
(arXiv:1604.01757).  Its SAT instances are uniquely solvable cyclic 3-XOR
systems, written as ordinary CNF parity gadgets and hidden among independently
sampled ternary parity constraints.  The certificate is the paper's normalized
word of Brandt-semigroup generators.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "logic",
    "object_regime": "finite_discrete",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "power tuples over the five-element Brandt semigroup B2",
        "a target tuple in the same direct power",
        "CNF clause coordinates from the paper's SAT reduction",
    ],
    "verification_operations": [
        "exact Brandt-semigroup multiplication",
        "coordinatewise tuple comparison",
        "generator-word syntax and normalization checks",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 2, proof of Theorem 1.1, equations (1)-(2): SAT is mapped "
        "to subpower membership and a satisfying assignment is carried to "
        "the word a_1^{z_1}...a_k^{z_k}"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "reduction recognition",
    "intuition_description": (
        "Recognize each four-clause block as one parity equation and find the "
        "spanning tight cycle hidden among independently sampled ternary "
        "supports; otherwise solve a shuffled overdetermined linear system."
    ),
    "hardness_basis": (
        "Track B: decode the parity gadgets and use Gaussian elimination over "
        "GF(2), which is O(m*n^2); at n=100,m=350 it used 1,322,188 exact "
        "bit XORs across eight measured instances (165,273 per instance on "
        "average, about 0.107 s total on the audit host), while tight-cycle "
        "recognition averaged 119 search nodes and the recurrence takes "
        "3n-1=299 exact XORs."
    ),
    "max_answer_tokens": 125,
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
    "demo": {"n": 5, "decoys": 0},
    "easy": {"n": 46, "decoys": 0},
    "medium": {"n": 73, "decoys": 40},
    "hard": {"n": 100, "decoys": 250},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Hint: The ternary support hypergraph contains a spanning tight cycle, "
    "while every support outside that cycle was sampled independently."
)
PLACEBO_HINT = (
    "Hint: The displayed constraints use distinct integer labels, while every "
    "ordinary clause belongs to an explicitly numbered coordinate block."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A normalized generator word: exactly n distinct integer generator "
        "IDs, with position j choosing one of the two IDs displayed for "
        "control coordinate j; IDs lie in [0,2n-1]."
    ),
    "bounds": {
        "word_length": "n",
        "choices_per_position": 2,
        "generator_id_min": 0,
        "generator_id_max": "2n-1",
        "maximum_shipping_length": 100,
        "candidate_count": "2^n",
    },
}

# Filled only after the script-owned bare/hinted/placebo runs finish.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 1, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES = r"""
Definition. Section 1 defines SMP(S): given generator tuples a_1,...,a_k and
a target b in S^n, decide whether a word in the generators equals b. Section
2, especially the proof of Theorem 1.1 and equations (1)-(2), fixes the exact
SAT reduction used here. For B2 take e=[1,1], f=[2,2], s=[1,2], and g=0.
Then e*s=s*f=s, while a second occurrence of s destroys the required control
coordinate. The first n coordinates force a normalized successful word to
choose one truth generator for every variable in variable order; a clause
coordinate reaches g exactly when one selected literal satisfies that clause.

Step-0 decision. Corollary 1.3 says SMP(B2) is NP-complete, but that worst-case
statement does not prove inverse-generated instances hard on their generated
distribution. This family therefore does not claim Track A. Its restricted
source is polynomial-time solvable: complete CNF truth tables encode ternary
parity equations, and Gaussian elimination over GF(2) recovers the
unique assignment in O(m*n^2). selftest reports that successful algorithm
separately, as Track B requires. The compact no-tool route recognizes that the
ternary equation supports contain the length-three windows of a hidden cycle.
Adjacent cycle equations give x_i XOR x_(i+3)=r_i XOR r_(i+1); since gcd(n,3)=1,
one traversal expresses every bit relative to one bit, and one original
equation fixes it. At n=100 this is 3n-1=299 exact XORs, versus the measured
elimination cost recorded by selftest.

Generation. A Boolean assignment and a uniformly shuffled hidden cycle are
sampled first. Each consecutive triple receives the parity of the planted
bits, and the opposite-parity rows are forbidden by four 3-CNF clauses. The
cyclic matrix I+P+P^2 is nonsingular over GF(2) whenever 3 does not divide n:
its homogeneous recurrence has period three, so cyclic closure forces both
initial bits to zero. The satisfying assignment is therefore unique. Extra
ternary supports are sampled uniformly without replacement and assigned the
parity of the already planted bits. Their individual distribution matches a
randomly labelled cycle window, and they cannot create a second solution
because the cycle subsystem is already nonsingular. Only after the assignment
is known are the clauses, generator IDs, and paper-defined target assembled.

Easy regimes and attacks. Section 3, Algorithm 1, is the paper's polynomial
case for one-block Rees matrices; B2 is deliberately outside it. Section 5
shows that adjoining an identity changes the relevant regimes, so this module
uses B2 without an identity and the NP construction, not B2^1 and the
exponentially long Q3SAT word from Section 4. Literal-majority has exactly tied
marginals in every parity block, so the outlier probe gets no signal. Generator
IDs are shuffled independently of truth values, defeating label ansatzes. The
uniform planted bits and independently sampled extra constraints leave the
single-bit greedy rule in local optima, while uniqueness in a 2^100 normalized
space makes 256 random restarts negligible. All four are tested on eight
shipping seeds and must fail. Gaussian elimination is expected to succeed and
is not misreported as a failing Track-B attack.

Canonicalization. Generator-list order, equation-block order, literal order,
arbitrary variable renaming, and complementing a Boolean coordinate preserve
the represented SMP problem. Right-hand sides therefore cannot supply honest
diversity. Exact hypergraph isomorphism is not attempted; the key uses a
label-invariant Weisfeiler-Lehman incidence signature of the full support
hypergraph. selftest applies the listed transformations, including their
composition, and carries the planted word through them.

Hardening. The bare oracle loop held at n=100 with 150 decoys, but one of three
structurally hinted oracles solved that level. G9(b) permits one upward move, so
the final hard preset uses the fixed-length 250-decoy haystack. Fresh bare
evidence and the hinted rerun both held 0/3 there; no second adjustment was made.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 1 << 20

# B2 = ({1,2} x {1,2}) union {0}, with diagonal sandwich matrix.
_ZERO = 0
_E = 1       # [1,1]
_S = 2       # [1,2]
_T = 3       # [2,1], included for the full multiplication table
_F = 4       # [2,2]
_PAIR_TO_ELEMENT = {(1, 1): _E, (1, 2): _S, (2, 1): _T, (2, 2): _F}
_ELEMENT_TO_PAIR = {value: key for key, value in _PAIR_TO_ELEMENT.items()}


def _mul(left: int, right: int) -> int:
    """Multiply two elements of the five-element Brandt semigroup exactly."""
    if left == _ZERO or right == _ZERO:
        return _ZERO
    i, lam = _ELEMENT_TO_PAIR[left]
    j, mu = _ELEMENT_TO_PAIR[right]
    return _PAIR_TO_ELEMENT[(i, mu)] if lam == j else _ZERO


def _validate_n(n: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if n % 3 == 0:
        raise ValueError("n must not be divisible by 3")


def _wrong_parity_clauses(
    variables: tuple[int, ...], rhs: int, rng: random.Random
) -> list[list[int]]:
    """CNF truth-table clauses whose models have XOR equal to rhs.

    A positive signed literal +(j+1) denotes x_j; a negative one denotes not
    x_j.  For every assignment of the wrong parity, one clause forbids exactly
    that assignment.
    """
    clauses: list[list[int]] = []
    arity = len(variables)
    if arity not in (2, 3):
        raise ValueError("parity gadgets support arity 2 or 3")
    for mask in range(1 << arity):
        bits = tuple((mask >> q) & 1 for q in range(arity))
        if sum(bits) % 2 == rhs:
            continue
        clause = [
            (variable + 1) if bit == 0 else -(variable + 1)
            for variable, bit in zip(variables, bits)
        ]
        rng.shuffle(clause)
        clauses.append(clause)
    rng.shuffle(clauses)
    return clauses


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a unique SAT assignment and its B2 word witness."""
    decoys = params.pop("decoys", 0)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _validate_n(n)
    if isinstance(decoys, bool) or not isinstance(decoys, int) or decoys < 0:
        raise ValueError("decoys must be a nonnegative integer")
    if decoys > math.comb(n, 3) - n:
        raise ValueError("too many distinct decoy supports for n")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    cycle = list(range(n))
    rng.shuffle(cycle)
    planted = [rng.randrange(2) for _ in range(n)]

    cycle_supports = {
        tuple(sorted((cycle[i], cycle[(i + 1) % n], cycle[(i + 2) % n])))
        for i in range(n)
    }
    supports = set(cycle_supports)
    while len(supports) < n + decoys:
        supports.add(tuple(sorted(rng.sample(range(n), 3))))

    groups = []
    for triple in sorted(supports):
        rhs = planted[triple[0]] ^ planted[triple[1]] ^ planted[triple[2]]
        groups.append(_wrong_parity_clauses(triple, rhs, rng))
    rng.shuffle(groups)

    generator_labels = list(range(2 * n))
    rng.shuffle(generator_labels)
    pairs = [generator_labels[2 * j : 2 * j + 2] for j in range(n)]
    answer = [pairs[j][planted[j]] for j in range(n)]
    return {
        "family": "theorem_1_1_brandt_smp_from_cyclic_xor",
        "semigroup": "B2",
        "n": n,
        "clause_groups": groups,
        "generator_pairs": pairs,
        "coordinate_count": n + sum(len(group) for group in groups),
        "ternary_block_count": n + decoys,
        "cycle_block_count": n,
        "decoy_block_count": decoys,
        "target": {
            "control_coordinates": [_S] * n,
            "clause_coordinates": [_ZERO] * sum(len(group) for group in groups),
        },
        "answer": answer,
    }


def _literal_text(literal: int) -> str:
    index = abs(literal) - 1
    return f"x{index}" if literal > 0 else f"not x{index}"


def render(inst: dict) -> str:
    """Render a self-contained, implicit description of the generator tuples."""
    n = inst["n"]
    pair_lines = "\n".join(
        f"  variable {j}: value 0 -> generator {pair[0]}; "
        f"value 1 -> generator {pair[1]}"
        for j, pair in enumerate(inst["generator_pairs"])
    )
    clause_lines = []
    coordinate = n
    for block_number, group in enumerate(inst["clause_groups"]):
        clause_lines.append(f"  block {block_number}:")
        for clause in group:
            text = " OR ".join(_literal_text(literal) for literal in clause)
            clause_lines.append(f"    coordinate {coordinate}: ({text})")
            coordinate += 1

    statement = f"""Find a normalized generator word for a target tuple in a direct power of the Brandt semigroup B2.

Definitions and exact conventions:
- B2 has five elements 0, [1,1], [1,2], [2,1], [2,2]. Multiplication is 0*u=u*0=0. For nonzero elements,
      [i,lambda] * [j,mu] = [i,mu] if lambda=j, and 0 otherwise.
  Tuple multiplication is coordinatewise and word products are evaluated left to right.
- There are {n} Boolean variables x0,...,x{n - 1}, {2 * n} generator IDs 0,...,{2 * n - 1}, and {inst['coordinate_count']} tuple coordinates numbered 0,...,{inst['coordinate_count'] - 1}.
- For variable j and value z in {{0,1}}, call the displayed generator ID a_j^z. Its tuple is defined without abbreviation as follows.
  * At control coordinate i in 0,...,{n - 1}, a_j^z(i) is [2,2] if i<j, [1,2] if i=j, and [1,1] if i>j.
  * At a clause coordinate, a_j^z is 0 if assigning xj=z makes at least one occurrence of xj or not xj in that displayed clause true; it is [1,1] otherwise. Variables absent from the clause therefore contribute [1,1].
- The target tuple is [1,2] at every control coordinate 0,...,{n - 1}, and 0 at every clause coordinate {n},...,{inst['coordinate_count'] - 1}.
- A normalized answer has exactly {n} generator IDs. At word position j it must choose exactly one of the two IDs displayed for variable j. Thus repetitions are forbidden and order is fixed by j; the choice at position j is the encoded value of xj.
- Each clause block below is one ternary parity truth table with four ordinary OR-clauses. Every displayed clause is a separate target coordinate. A clause is satisfied if at least one of its literals is true.

Generator IDs:
{pair_lines}

Clause-coordinate blocks:
{chr(10).join(clause_lines)}

Give your final answer inside <answer></answer> tags, as one JSON array of exactly {n} integer generator IDs in word order.
Example format (not necessarily a solution): <answer>{json.dumps([pair[0] for pair in inst['generator_pairs']])}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract a JSON integer list from tags, a fence, or surrounding prose."""
    if not isinstance(text, str):
        return None
    tagged = _ANSWER_RE.findall(text)
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, re.I | re.S)
    bare = re.findall(r"\[(?:\s*-?\d+\s*,)*\s*-?\d+\s*\]", text, re.S)
    bodies = tagged if tagged else (fenced if fenced else bare)
    for body in reversed(bodies):
        body = body.strip()
        if body.startswith("```") and body.endswith("```"):
            body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
            body = re.sub(r"\s*```$", "", body).strip()
        try:
            value = json.loads(body)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, list) and all(
            not isinstance(x, bool) and isinstance(x, int) for x in value
        ):
            return value
    return None


def _assignment_from_word(inst: dict, answer: object) -> tuple[list[int] | None, str]:
    n = inst["n"]
    if not isinstance(answer, list):
        return None, "answer must be a JSON list"
    if not answer:
        return None, "answer is empty"
    if len(answer) != n:
        return None, f"wrong length: expected {n}, got {len(answer)}"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return None, "every generator ID must be an integer"
    bad = next((x for x in answer if x < 0 or x >= 2 * n), None)
    if bad is not None:
        return None, f"generator index out of range: {bad}"
    if len(set(answer)) != n:
        return None, "a generator ID is repeated"
    bits: list[int] = []
    for j, (choice, pair) in enumerate(zip(answer, inst["generator_pairs"])):
        if choice == pair[0]:
            bits.append(0)
        elif choice == pair[1]:
            bits.append(1)
        else:
            return None, f"wrong generator pair at word position {j}"
    return bits, "ok"


def _literal_is_true(literal: int, bits: list[int]) -> bool:
    value = bits[abs(literal) - 1]
    return bool(value) if literal > 0 else not bool(value)


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any normalized word by exact B2 multiplication; never read answer."""
    bits, reason = _assignment_from_word(inst, answer)
    if bits is None:
        return False, reason

    # Check every clause coordinate. Variables absent from a clause contribute
    # E=[1,1], so it is exact (and much faster) to multiply only the three
    # possibly-zero factors, in variable order.
    clause_number = 0
    for group in inst["clause_groups"]:
        for clause in group:
            accumulator = _E
            for variable in sorted(abs(literal) - 1 for literal in clause):
                matching = next(lit for lit in clause if abs(lit) - 1 == variable)
                factor = _ZERO if _literal_is_true(matching, bits) else _E
                accumulator = _mul(accumulator, factor)
            if accumulator != _ZERO:
                return False, f"clause coordinate {inst['n'] + clause_number} misses target 0"
            clause_number += 1

    # Check all control coordinates by multiplying the actual paper-defined
    # entries of the submitted generator word.
    n = inst["n"]
    for coordinate in range(n):
        accumulator = None
        for variable in range(n):
            if coordinate < variable:
                factor = _F
            elif coordinate == variable:
                factor = _S
            else:
                factor = _E
            accumulator = factor if accumulator is None else _mul(accumulator, factor)
        if accumulator != _S:
            return False, f"control coordinate {coordinate} misses target [1,2]"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the full normalized language, one choice per position."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    return [pair[rng.randrange(2)] for pair in inst["generator_pairs"]]


def search_space(inst: dict) -> int | None:
    return 1 << inst["n"]


def enumerate_all(inst: dict) -> int | None:
    """Count normalized successful words exactly when the language is small."""
    n = inst["n"]
    if (1 << n) > _ENUMERATION_CAP:
        return None
    count = 0
    for mask in range(1 << n):
        candidate = [
            pair[(mask >> j) & 1] for j, pair in enumerate(inst["generator_pairs"])
        ]
        count += int(verify(inst, candidate)[0])
    return count


def _decode_group(group: list[list[int]]) -> tuple[tuple[int, ...], int]:
    """Recover a binary/ternary XOR equation from its complete CNF table."""
    if not group or len(group[0]) not in (2, 3):
        raise ValueError("a parity block must have arity two or three")
    arity = len(group[0])
    if len(group) != 1 << (arity - 1):
        raise ValueError("a parity block has the wrong number of clauses")
    supports = [tuple(sorted(abs(lit) - 1 for lit in clause)) for clause in group]
    if any(len(clause) != arity for clause in group) or len(set(supports)) != 1:
        raise ValueError("malformed parity block")
    forbidden_parities = set()
    forbidden_rows = set()
    variables = supports[0]
    for clause in group:
        signs = {abs(lit) - 1: int(lit < 0) for lit in clause}
        row = tuple(signs[v] for v in variables)
        forbidden_rows.add(row)
        forbidden_parities.add(sum(row) % 2)
    if len(forbidden_rows) != 1 << (arity - 1) or len(forbidden_parities) != 1:
        raise ValueError("block is not a complete XOR CNF truth table")
    return variables, 1 ^ next(iter(forbidden_parities))


def _equations(inst: dict) -> list[tuple[tuple[int, ...], int]]:
    return [_decode_group(group) for group in inst["clause_groups"]]


def _find_tight_cycle(
    equations: list[tuple[tuple[int, ...], int]], n: int, node_cap: int = 1_000_000
) -> tuple[list[int], int]:
    """Find a spanning tight cycle by exact support backtracking."""
    supports = {frozenset(support) for support, _ in equations if len(support) == 3}
    transitions: dict[frozenset[int], set[int]] = {}
    for support in supports:
        a, b, c = tuple(support)
        for u, v, w in ((a, b, c), (a, c, b), (b, c, a)):
            transitions.setdefault(frozenset((u, v)), set()).add(w)

    first = 0
    nodes = 0
    used = {first}

    def extend(path: list[int]) -> list[int] | None:
        nonlocal nodes
        nodes += 1
        if nodes > node_cap:
            raise RuntimeError("tight-cycle search exceeded its node cap")
        if len(path) == n:
            closing_one = frozenset((path[-2], path[-1], path[0]))
            closing_two = frozenset((path[-1], path[0], path[1]))
            return list(path) if closing_one in supports and closing_two in supports else None
        pair = frozenset((path[-2], path[-1]))
        candidates = [v for v in transitions.get(pair, ()) if v not in used]

        # A true cycle continuation leaves another support through its new pair;
        # isolated random triples usually do not.  This changes only search order.
        candidates.sort(
            key=lambda v: -sum(
                w not in used and w != path[-2]
                for w in transitions.get(frozenset((path[-1], v)), ())
            )
        )
        for candidate in candidates:
            used.add(candidate)
            path.append(candidate)
            found = extend(path)
            if found is not None:
                return found
            path.pop()
            used.remove(candidate)
        return None

    second_choices = sorted(
        v for v in range(1, n) if frozenset((first, v)) in transitions
    )
    for second in second_choices:
        used.add(second)
        found = extend([first, second])
        used.remove(second)
        if found is not None:
            return found, nodes
    raise ValueError("support hypergraph has no spanning tight cycle")


def _incidence_signature(
    equations: list[tuple[tuple[int, ...], int]], n: int
) -> dict:
    """A label-invariant color-refinement signature of the support hypergraph."""
    supports = sorted(tuple(sorted(support)) for support, _ in equations)
    incident: list[list[int]] = [[] for _ in range(n)]
    for edge, support in enumerate(supports):
        for variable in support:
            incident[variable].append(edge)

    variable_colors = [len(edges) for edges in incident]
    edge_colors = [len(support) for support in supports]
    rounds = 0
    for rounds in range(1, 13):
        signatures = [
            ("v", variable_colors[v], tuple(sorted(edge_colors[e] for e in incident[v])))
            for v in range(n)
        ] + [
            ("e", edge_colors[e], tuple(sorted(variable_colors[v] for v in support)))
            for e, support in enumerate(supports)
        ]
        palette = {signature: color for color, signature in enumerate(sorted(set(signatures)))}
        new_variables = [palette[signature] for signature in signatures[:n]]
        new_edges = [palette[signature] for signature in signatures[n:]]
        if new_variables == variable_colors and new_edges == edge_colors:
            break
        variable_colors, edge_colors = new_variables, new_edges

    variable_hist: dict[int, int] = {}
    edge_hist: dict[int, int] = {}
    incidence_hist: dict[str, int] = {}
    for color in variable_colors:
        variable_hist[color] = variable_hist.get(color, 0) + 1
    for color in edge_colors:
        edge_hist[color] = edge_hist.get(color, 0) + 1
    for edge, support in enumerate(supports):
        for variable in support:
            key = f"{variable_colors[variable]}:{edge_colors[edge]}"
            incidence_hist[key] = incidence_hist.get(key, 0) + 1
    return {
        "n": n,
        "edges": len(supports),
        "rounds": rounds,
        "variable_colors": sorted(variable_hist.items()),
        "edge_colors": sorted(edge_hist.items()),
        "incidence_colors": sorted(incidence_hist.items()),
    }


def canonical_key(inst: dict) -> str:
    """Hash a structural incidence invariant, never a seed or rendered prompt."""
    signature = _incidence_signature(_equations(inst), inst["n"])
    payload = json.dumps(signature, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(payload.encode("ascii")).hexdigest()
    return f"cyclic-3xor-smp-wl:{digest}"


def escalate(params: dict) -> dict | str | None:
    """Grow the constraint haystack while keeping answer and route fixed."""
    if not isinstance(params, dict) or set(params) != {"n", "decoys"}:
        return None
    n = params["n"]
    decoys = params["decoys"]
    if not isinstance(n, int) or not isinstance(decoys, int):
        return None
    if n < 100:
        return {"n": 100, "decoys": max(decoys, 150)}
    support_limit = math.comb(n, 3) - n
    if decoys < support_limit:
        return {"n": n, "decoys": min(support_limit, decoys + 100)}
    return None


def _gaussian_solve(inst: dict) -> tuple[list[int] | None, int]:
    """Decode the blocks and solve densely over GF(2), counting bit XORs."""
    n = inst["n"]
    augmented = []
    for triple, rhs in _equations(inst):
        row = [0] * (n + 1)
        for variable in triple:
            row[variable] = 1
        row[n] = rhs
        augmented.append(row)

    operations = 0
    pivot_row = 0
    pivot_columns: list[int] = []
    row_count = len(augmented)
    for column in range(n):
        pivot = next(
            (r for r in range(pivot_row, row_count) if augmented[r][column]), None
        )
        if pivot is None:
            continue
        augmented[pivot_row], augmented[pivot] = augmented[pivot], augmented[pivot_row]
        for r in range(row_count):
            if r == pivot_row or not augmented[r][column]:
                continue
            for j in range(column, n + 1):
                augmented[r][j] ^= augmented[pivot_row][j]
                operations += 1
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == n:
            break
    if pivot_row != n:
        return None, operations
    bits = [0] * n
    for row, column in enumerate(pivot_columns):
        bits[column] = augmented[row][n]
    answer = [inst["generator_pairs"][j][bits[j]] for j in range(n)]
    return answer, operations


def _compact_cycle_solve(inst: dict) -> tuple[list[int], int, int]:
    """Use the hidden-cycle recurrence, counting only exact bit XORs."""
    n = inst["n"]
    equations = _equations(inst)
    order, search_nodes = _find_tight_cycle(equations, n)
    rhs_by_support = {frozenset(support): rhs for support, rhs in equations}
    rhs = [
        rhs_by_support[
            frozenset((order[i], order[(i + 1) % n], order[(i + 2) % n]))
        ]
        for i in range(n)
    ]

    # x_i XOR x_(i+3) = rhs_i XOR rhs_(i+1).  Since gcd(n,3)=1,
    # stepping by three visits every position.  Compute offsets from x_0.
    offsets = [0] * n
    operations = 0
    position = 0
    for _ in range(n - 1):
        difference = rhs[position] ^ rhs[(position + 1) % n]
        operations += 1
        following = (position + 3) % n
        offsets[following] = offsets[position] ^ difference
        operations += 1
        position = following

    # rhs_0 = x_0 XOR x_1 XOR x_2, and each x_i=x_0 XOR offsets_i.
    base = rhs[0] ^ offsets[1] ^ offsets[2]
    operations += 2
    bits_by_position = [base]
    for i in range(1, n):
        bits_by_position.append(base ^ offsets[i])
        operations += 1
    bits = [0] * n
    for position, variable in enumerate(order):
        bits[variable] = bits_by_position[position]
    return (
        [inst["generator_pairs"][j][bits[j]] for j in range(n)],
        operations,
        search_nodes,
    )


def _satisfied_clause_count(inst: dict, bits: list[int]) -> int:
    return sum(
        any(_literal_is_true(lit, bits) for lit in clause)
        for group in inst["clause_groups"]
        for clause in group
    )


def _literal_majority(inst: dict) -> list[int]:
    n = inst["n"]
    positive = [0] * n
    negative = [0] * n
    for group in inst["clause_groups"]:
        for clause in group:
            for literal in clause:
                (positive if literal > 0 else negative)[abs(literal) - 1] += 1
    bits = [int(positive[j] > negative[j]) for j in range(n)]
    return [inst["generator_pairs"][j][bits[j]] for j in range(n)]


def _greedy_clause_gain(inst: dict, passes: int = 4) -> tuple[list[int], int]:
    n = inst["n"]
    bits = [0] * n
    score = _satisfied_clause_count(inst, bits)
    steps = 0
    for _ in range(passes):
        changed = False
        for j in range(n):
            bits[j] ^= 1
            proposed = _satisfied_clause_count(inst, bits)
            steps += 1
            if proposed > score:
                score = proposed
                changed = True
            else:
                bits[j] ^= 1
        if not changed:
            break
    return [inst["generator_pairs"][j][bits[j]] for j in range(n)], steps


def _random_restart(
    inst: dict, rng: random.Random, restarts: int = 256
) -> tuple[bool, int]:
    for attempt in range(1, restarts + 1):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True, attempt
    return False, restarts


def _label_ansatz(inst: dict) -> tuple[bool, int]:
    pairs = inst["generator_pairs"]
    candidates = [
        [min(pair) for pair in pairs],
        [max(pair) for pair in pairs],
        [pair[pair[0] & 1] for pair in pairs],
        [pair[pair[1] & 1] for pair in pairs],
        [pair[j & 1] for j, pair in enumerate(pairs)],
    ]
    for candidate in candidates:
        if verify(inst, candidate)[0]:
            return True, len(candidates)
    return False, len(candidates)


def _decode_answer_bits(inst: dict) -> list[int]:
    bits, reason = _assignment_from_word(inst, inst["answer"])
    if bits is None:
        raise AssertionError(reason)
    return bits


def _relabel(
    inst: dict,
    old_to_new_variable: list[int],
    old_to_new_generator: list[int],
    rng: random.Random,
    complemented_variables: set[int] | None = None,
) -> dict:
    """Rename/reorder and optionally complement variables, carrying the answer."""
    n = inst["n"]
    complemented_variables = complemented_variables or set()
    bits_old = _decode_answer_bits(inst)
    bits_new = [0] * n
    pairs_new = [[0, 0] for _ in range(n)]
    for old in range(n):
        new = old_to_new_variable[old]
        flip = int(old in complemented_variables)
        bits_new[new] = bits_old[old] ^ flip
        old_pair = inst["generator_pairs"][old]
        pairs_new[new] = [
            old_to_new_generator[old_pair[z ^ flip]] for z in (0, 1)
        ]

    groups_new = []
    for group in inst["clause_groups"]:
        moved_group = []
        for clause in group:
            moved_clause = []
            for literal in clause:
                old_variable = abs(literal) - 1
                new_variable = old_to_new_variable[old_variable]
                positive = literal > 0
                if old_variable in complemented_variables:
                    positive = not positive
                moved_clause.append((new_variable + 1) if positive else -(new_variable + 1))
            rng.shuffle(moved_clause)
            moved_group.append(moved_clause)
        rng.shuffle(moved_group)
        groups_new.append(moved_group)
    rng.shuffle(groups_new)

    moved = dict(inst)
    moved["generator_pairs"] = pairs_new
    moved["clause_groups"] = groups_new
    moved["answer"] = [pairs_new[j][bits_new[j]] for j in range(n)]
    return moved


def _answer_metrics(answer: list[int]) -> tuple[int, int, int]:
    encoded = json.dumps(answer)
    return len(encoded), math.ceil(len(encoded) / 4), len(answer)


def selftest() -> dict:
    """Run all local correctness, density, attack, scale, and symmetry gates."""
    report: dict = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1: every preset, several seeds, and JSON-native certificates.
    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            compact, compact_operations, _ = _compact_cycle_solve(inst)
            if compact != inst["answer"] or compact_operations != 3 * inst["n"] - 1:
                g1_failures.append(
                    f"{preset}/{seed}: compact route mismatch ({compact_operations} XORs)"
                )
            try:
                recovered = json.loads(json.dumps(inst["answer"]))
            except (TypeError, ValueError) as exc:
                g1_failures.append(f"{preset}/{seed}: JSON error {exc}")
            else:
                if recovered != inst["answer"]:
                    g1_failures.append(f"{preset}/{seed}: JSON changed answer")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
        "construction_audit": "compact recurrence recovered every planted word",
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=123, **shipping)
    answer = ship["answer"]

    # G2: five distinct corruptions, with five distinct diagnostic reasons.
    swapped = list(answer)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = list(answer)
    duplicated[1] = duplicated[0]
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": [2 * ship["n"]] + answer[1:],
    }
    corruption_results = {
        name: {"accepted": verify(ship, candidate)[0], "reason": verify(ship, candidate)[1]}
        for name, candidate in corruptions.items()
    }
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": (
            all(not entry["accepted"] for entry in corruption_results.values())
            and len(set(reasons)) == len(reasons)
        ),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "I used the clause-coordinate invariant.\n```json\n"
        f"<answer>\n{json.dumps(answer)}\n</answer>\n```\n"
        "The tagged list is the normalized word."
    )
    parsed = parse_answer(realistic)
    untagged = parse_answer(
        "Here is the normalized word:\n```json\n" + json.dumps(answer) + "\n```"
    )
    report["G3_round_trip"] = {
        "pass": (
            parsed == answer
            and untagged == answer
            and verify(ship, parsed)[0]
            and verify(ship, untagged)[0]
        ),
        "parsed_matches": parsed == answer,
        "untagged_fence_matches": untagged == answer,
        "realistic_wrapper": True,
    }

    # G4: candidates already obey the forced one-per-pair ordered word shape.
    guess_rng = random.Random(0x160401757)
    guess_total = 200_000
    guess_hits = 0
    guess_t0 = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_wall = time.perf_counter() - guess_t0
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_fraction,
        "candidate_space": search_space(ship),
        "sampling_prior": "uniform over normalized words choosing one generator from each displayed pair",
        "wall_clock_sec": round(guess_wall, 6),
    }

    # G6: four failing no-tool attacks; the successful reference solver is separate.
    attack_names = (
        "outlier_literal_majority",
        "greedy_single_bit_clause_gain",
        "random_restart_256",
        "generator_label_ansatz",
    )
    attacks = {
        name: {"successes": 0, "attempts": 0, "steps": 0, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    reference_successes = 0
    reference_operations = 0
    reference_wall = 0.0
    compact_successes = 0
    compact_operations = 0
    compact_search_nodes = 0
    attack_seeds = list(range(800, 808))
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **shipping)

        t0 = time.perf_counter()
        candidate = _literal_majority(inst)
        elapsed = time.perf_counter() - t0
        stat = attacks["outlier_literal_majority"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["steps"] += sum(
            len(clause) for group in inst["clause_groups"] for clause in group
        )
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        candidate, steps = _greedy_clause_gain(inst)
        elapsed = time.perf_counter() - t0
        stat = attacks["greedy_single_bit_clause_gain"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        success, steps = _random_restart(inst, random.Random(seed ^ 0xB2), 256)
        elapsed = time.perf_counter() - t0
        stat = attacks["random_restart_256"]
        stat["attempts"] += 1
        stat["successes"] += int(success)
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        success, steps = _label_ansatz(inst)
        elapsed = time.perf_counter() - t0
        stat = attacks["generator_label_ansatz"]
        stat["attempts"] += 1
        stat["successes"] += int(success)
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        solved, operations = _gaussian_solve(inst)
        elapsed = time.perf_counter() - t0
        reference_wall += elapsed
        reference_operations += operations
        reference_successes += int(solved is not None and verify(inst, solved)[0])

        compact, operations, search_nodes = _compact_cycle_solve(inst)
        compact_operations += operations
        compact_search_nodes += search_nodes
        compact_successes += int(verify(inst, compact)[0])

    for stat in attacks.values():
        stat["wall_clock_sec"] = round(stat["wall_clock_sec"], 6)
    average_reference_operations = reference_operations // len(attack_seeds)
    all_failed = all(stat["successes"] == 0 for stat in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": (
            all_failed
            and reference_successes == len(attack_seeds)
            and compact_successes == len(attack_seeds)
        ),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "parity-gadget decoding plus dense Gaussian elimination over GF(2)",
            "complexity": "O(m*n^2) exact bit operations for m parity blocks",
            "wall_clock_sec": round(reference_wall, 6),
            "operations": reference_operations,
            "average_operations_per_instance": average_reference_operations,
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
        "compact_route_audit": {
            "name": "hidden-cycle adjacent-equation recurrence",
            "complexity": "O(n) after recognizing the incidence invariant",
            "operations": compact_operations,
            "average_operations_per_instance": compact_operations // len(attack_seeds),
            "support_search_nodes": compact_search_nodes,
            "average_search_nodes": compact_search_nodes // len(attack_seeds),
            "solves": f"{compact_successes}/{len(attack_seeds)}, as expected",
        },
    }

    demo = make_instance(seed=123, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    strongest_failing = max(attacks.items(), key=lambda item: item[1]["wall_clock_sec"])
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and reference_successes == len(attack_seeds),
        "shipping_certified_solution_count": 1,
        "shipping_exact_solution_fraction": 2.0 ** (-ship["n"]),
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": guess_total,
        "shipping_sampled_density": guess_fraction,
        "demo_bruteforce_solution_count": demo_count,
        "demo_n": demo["n"],
        "reference_algorithm_wall_clock_sec": round(reference_wall, 6),
        "reference_algorithm_operations": reference_operations,
        "reference_average_operations": average_reference_operations,
        "strongest_failing_attack": strongest_failing[0],
        "strongest_failing_attack_wall_clock_sec": strongest_failing[1]["wall_clock_sec"],
        "strongest_failing_attack_steps": strongest_failing[1]["steps"],
    }

    ladder_n = [params["n"] for params in DIFFICULTY.values()]
    ladder_spaces = [1 << n for n in ladder_n]
    doubled = make_instance(
        n=2 * ship["n"], decoys=2 * ship["decoy_block_count"], seed=909
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (
            ladder_n == sorted(set(ladder_n))
            and ladder_spaces == sorted(set(ladder_spaces))
            and doubled_ok
            and doubled["coordinate_count"] > ship["coordinate_count"]
            and len(doubled["answer"]) == 2 * len(ship["answer"])
        ),
        "preset_n": dict(zip(DIFFICULTY, ladder_n)),
        "preset_candidate_spaces": dict(zip(DIFFICULTY, ladder_spaces)),
        "doubled_n": doubled["n"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
    }

    # G8: input reorder, label renaming, value complementation, and composition.
    invariant_checks = 0
    witness_checks = 0
    failures = []
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(n=29, decoys=40, seed=20_000 + seed)
        base_key = canonical_key(inst)
        unrelated_keys.append(base_key)
        rng = random.Random(30_000 + seed)
        variable_map = list(range(inst["n"]))
        generator_map = list(range(2 * inst["n"]))
        rng.shuffle(variable_map)
        rng.shuffle(generator_map)
        identity_v = list(range(inst["n"]))
        identity_g = list(range(2 * inst["n"]))
        complemented = {j for j in range(inst["n"]) if rng.randrange(2)}
        variants = (
            _relabel(inst, identity_v, identity_g, random.Random(seed + 1)),
            _relabel(inst, variable_map, identity_g, random.Random(seed + 2)),
            _relabel(inst, identity_v, generator_map, random.Random(seed + 3)),
            _relabel(
                inst, identity_v, identity_g, random.Random(seed + 4), complemented
            ),
            _relabel(
                inst, variable_map, generator_map, random.Random(seed + 5), complemented
            ),
        )
        for number, moved in enumerate(variants):
            invariant_checks += 1
            if canonical_key(moved) != base_key:
                failures.append(f"key/{seed}/{number}")
            witness_checks += 1
            if not verify(moved, moved["answer"])[0]:
                failures.append(f"witness/{seed}/{number}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not failures and distinct_keys == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": witness_checks,
        "invariance_failures": failures,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "transformations": [
            "equation-block, clause, and literal reorder",
            "arbitrary Boolean-variable renaming",
            "arbitrary generator-ID renaming",
            "independent Boolean-value complementation with generator-pair swaps",
            "composition of all listed transformations",
        ],
    }

    chars, tokens, elements = _answer_metrics(ship["answer"])
    intended_operations = 3 * ship["n"] - 1
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        chars <= 2_000
        and elements <= 256
        and intended_operations <= 300
        and tokens <= PROBLEM_PROFILE["max_answer_tokens"]
    )
    report["G9_no_tool_suitability"] = {
        "pass": G9_ORACLE_RESULTS["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
