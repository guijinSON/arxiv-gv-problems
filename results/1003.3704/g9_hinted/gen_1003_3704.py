"""Verified generator for arXiv:1003.3704.

The module inverse-generates bounded-occurrence, 5-colourable monotone
NAE-3SAT instances.  A witness is the two sides of a not-all-equal truth
assignment.  The hidden assignment is sampled before the clauses; verification
only scans the submitted partition and the public clauses.

Only the Python standard library is used.  Importing this module performs no
I/O and prints nothing.
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
import time
from collections import defaultdict


TRACK: str = "A"

PROBLEM_PROFILE: dict = {
    "native_domain": "logic",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "monotone three-variable NAE clauses",
        "a promised 5-colourable variable co-occurrence graph",
        "a two-part truth assignment",
    ],
    "verification_operations": [
        "integer range and partition checks",
        "exact Boolean not-all-equal evaluation of every clause",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "The regular clause-incidence structure hides a balanced two-way split "
        "inside a five-colouring; without recognizing that global split, local "
        "truth choices provide no distinguished starting variable."
    ),
    "hardness_basis": (
        "Track A: Theorem 2 proves NP-completeness for 5-colourable monotone "
        "NAE-3SAT when every variable occurs at most seven times; the shipping "
        "distribution uses 180 variables of occurrence seven, and the measured "
        "10,000-node NAE-DPLL baseline exhausts its budget on every "
        "reported shipping seed."
    ),
    "max_answer_tokens": 158,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON object {left:[...],right:[...]} encoding an ordered partition "
        "of vertices 0..n-1. Lists are strictly increasing, vertex 0 is in left "
        "to quotient the global-complement symmetry, and both sides are nonempty."
    ),
    "bounds": {
        "parts": 2,
        "total_vertex_entries": "n",
        "entry_minimum": 0,
        "entry_maximum": "n-1",
        "left_contains_vertex_zero": True,
        "parts_nonempty": True,
    },
}

DIFFICULTY: dict = {
    "easy": {"n": 180, "degree": 6, "extra_layers": 3},
}
SHIPPING_DIFFICULTY: str = "easy"

STRUCTURAL_HINT: str = (
    "The regular co-occurrence structure conceals a balanced two-cell refinement of a five-colouring."
)
PLACEBO_HINT: str = (
    "The clause table rewards careful tracking of vertex numbers and the two requested sides."
)

# Filled only from script-owned hardening transcripts.  Pending evidence makes
# G9 fail, rather than manufacturing an oracle result inside selftest().
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "not_run",
}

NOTES: str = r"""
Section 2 fixes the exact native definition: a monotone clause has three
distinct unnegated variables, and it is NAE-satisfied exactly when its three
values are not all equal.  The same section defines the co-occurrence graph by
joining variables that share a clause and explicitly says that the
4-colourable case is polynomial-time.  Theorem 2 is the hard-regime result:
the problem remains NP-complete for k >= 5 even when each variable occurs at
most seven times.  This generator stays in that regime without a surrogate.

Step-0 certificate question: no formula, spectral characterization, linear
solve, SDP, or classification table in the paper produces an assignment.  The
paper gives a polynomial reduction establishing NP-completeness; the general
certificate-producing method is exponential SAT search.  The generator does
not run that search.  It first samples ten equally sized hidden roles (five
proper colours crossed with the two planted truth values), then composes
balanced NAE clause templates and carries the planted partition through a
random relabelling.  Every clause uses three different hidden colours, so the
public primal graph really is 5-colourable, and every variable occurs six or
seven times at the non-demo presets.

This is a distributional Track-A claim, not an assertion that worst-case
NP-completeness proves average-case hardness.  Degree regularity removes the
most direct planted outlier.  Complement-paired extra templates keep both
truth populations identically distributed.  selftest measures occurrence
outliers, one-pass greedy assignment, random-restart NAE-WalkSAT, a bottom-
eigenvector co-occurrence relaxation with local repair, and the domain-standard
NAE-DPLL with unit propagation.  The README records the finite attack budgets
and the remaining average-case caveat.
""".strip()


def _validate_params(n: int, degree: int, extra_layers: int) -> None:
    if any(type(x) is not int for x in (n, degree, extra_layers)):
        raise TypeError("n, degree, and extra_layers must be integers")
    if n == 10:
        if degree != 3 or extra_layers != 0:
            raise ValueError("the hand-scale n=10 instance uses degree=3 and no extras")
        return
    if n < 30 or n % 30:
        raise ValueError("non-demo n must be a positive multiple of 30")
    if degree != 6:
        raise ValueError("non-demo base degree must be 6")
    if extra_layers < 0 or extra_layers > n // 60:
        raise ValueError("extra_layers must lie between 0 and floor(n/60)")


def _all_role_templates() -> list[tuple[tuple[int, int], ...]]:
    """The 60 colour-distinct, planted-NAE triples of ten roles."""

    return [
        tuple(zip(colours, bits))
        for colours in itertools.combinations(range(5), 3)
        for bits in itertools.product((0, 1), repeat=3)
        if 0 < sum(bits) < 3
    ]


def _connected(n: int, clauses: list[list[int]]) -> bool:
    adjacency = [set() for _ in range(n)]
    for clause in clauses:
        a, b, c = clause
        adjacency[a].update((b, c))
        adjacency[b].update((a, c))
        adjacency[c].update((a, b))
    seen = {0}
    todo = [0]
    while todo:
        v = todo.pop()
        for w in adjacency[v]:
            if w not in seen:
                seen.add(w)
                todo.append(w)
    return len(seen) == n


def _demo_templates(rng: random.Random) -> list[tuple[tuple[int, int], ...]]:
    """Ten templates, each of the ten roles occurring exactly three times."""

    colour_triples = list(itertools.combinations(range(5), 3))
    bit_patterns = [x for x in itertools.product((0, 1), repeat=3) if 0 < sum(x) < 3]
    for _ in range(20_000):
        out = []
        counts = {(c, b): 0 for c in range(5) for b in range(2)}
        for colours in colour_triples:
            bits = rng.choice(bit_patterns)
            template = tuple(zip(colours, bits))
            out.append(template)
            for role in template:
                counts[role] += 1
        if all(value == 3 for value in counts.values()):
            rng.shuffle(out)
            return out
    raise RuntimeError("could not balance the demo role templates")


def _template_schedule(n: int, degree: int, extra_layers: int,
                       rng: random.Random) -> list[tuple[tuple[int, int], ...]]:
    if n == 10:
        return _demo_templates(rng)

    # In all 60 valid templates, each role occurs 18 times.  Repeating the
    # complete orbit n/30 times therefore supplies six stubs per variable.
    templates = _all_role_templates() * (n // 30)

    # Each extra layer contains all ten colour triples.  A random nonconstant
    # bit pattern and its complement consume one stub from each bit population
    # of every selected colour.  Thus extra degree is independent of plant bit.
    bit_patterns = [x for x in itertools.product((0, 1), repeat=3) if 0 < sum(x) < 3]
    for _ in range(extra_layers):
        colour_triples = list(itertools.combinations(range(5), 3))
        rng.shuffle(colour_triples)
        for colours in colour_triples:
            bits = rng.choice(bit_patterns)
            templates.append(tuple(zip(colours, bits)))
            templates.append(tuple(zip(colours, tuple(1 - b for b in bits))))
    rng.shuffle(templates)
    return templates


def _partition_from_bits(bits: list[int]) -> dict:
    if bits[0]:
        bits = [1 - b for b in bits]
    return {
        "left": [v for v, value in enumerate(bits) if value == 0],
        "right": [v for v, value in enumerate(bits) if value == 1],
    }


def make_instance(n: int, seed: int = 0, degree: int = 6,
                  extra_layers: int = 0, **params) -> dict:
    """Inverse-generate a promised 5-colourable monotone NAE-3SAT instance."""

    del params
    _validate_params(n, degree, extra_layers)
    rng = random.Random(seed)
    if n % 10:
        raise ValueError("n must be divisible by ten so all hidden roles are balanced")

    variables = list(range(n))
    rng.shuffle(variables)
    role_size = n // 10
    buckets: dict[tuple[int, int], list[int]] = {}
    plant = [0] * n
    for colour in range(5):
        for bit in range(2):
            start = (2 * colour + bit) * role_size
            bucket = variables[start:start + role_size]
            buckets[(colour, bit)] = bucket
            for vertex in bucket:
                plant[vertex] = bit

    for _attempt in range(200):
        schedule = _template_schedule(n, degree, extra_layers, rng)
        role_uses = defaultdict(int)
        for template in schedule:
            for role in template:
                role_uses[role] += 1

        pools = {}
        possible = True
        for role, bucket in buckets.items():
            uses = role_uses[role]
            base = uses // len(bucket)
            remainder = uses % len(bucket)
            if base > 7 or (remainder and base >= 7):
                possible = False
                break
            order = bucket[:]
            rng.shuffle(order)
            pool = [v for v in order for _ in range(base)] + order[:remainder]
            rng.shuffle(pool)
            pools[role] = pool
        if not possible:
            raise ValueError("requested parameters exceed occurrence seven")

        clauses = []
        for template in schedule:
            clause = sorted(pools[role].pop() for role in template)
            clauses.append(clause)
        clause_set = {tuple(c) for c in clauses}
        if len(clause_set) != len(clauses) or not _connected(n, clauses):
            continue
        rng.shuffle(clauses)
        break
    else:
        raise RuntimeError("could not realize a simple connected balanced formula")

    occurrence = [0] * n
    for clause in clauses:
        for vertex in clause:
            occurrence[vertex] += 1
    answer = _partition_from_bits(plant)
    return {
        "family": "five-colourable-monotone-nae-3sat",
        "n": n,
        "clauses": clauses,
        "clause_count": len(clauses),
        "maximum_occurrence": max(occurrence),
        "answer": answer,
    }


def render(inst: dict) -> str:
    n = inst["n"]
    lines = [
        "Find a not-all-equal truth assignment for this monotone 3-CNF instance.",
        "",
        "Definitions and promises:",
        f"- The variables are the integers 0 through {n - 1}.",
        "- Every displayed triple is a clause of three distinct, unnegated variables.",
        "- A clause is satisfied exactly when its three variables are not all assigned the same side.",
        "- The variable co-occurrence graph joins two variables that occur in a clause together.",
        "- The instance is promised to have a 5-colourable co-occurrence graph and each variable occurs at most seven times.",
        "- Return two nonempty sides that partition all variables. Order within each side does not matter mathematically, but the output lists must be strictly increasing.",
        "- To remove the global-complement ambiguity, vertex 0 must be in `left`.",
        "",
        f"n = {n}",
        f"clauses ({len(inst['clauses'])} total):",
    ]
    for index, clause in enumerate(inst["clauses"], 1):
        lines.append(f"{index}: ({clause[0]}, {clause[1]}, {clause[2]})")
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as one JSON object with exactly the keys `left` and `right`.",
        "Each value must be a strictly increasing JSON list of 0-indexed vertex integers; repetitions are forbidden.",
        'Example format: <answer>{"left":[0,2],"right":[1,3]}</answer>',
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(("", "Hint: " + STRUCTURAL_HINT))
    elif mode == "placebo":
        lines.extend(("", "Hint: " + PLACEBO_HINT))
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Parse the last tagged JSON object, tolerating prose and fences."""

    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    if not blocks:
        return None
    body = blocks[-1].strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, re.I | re.S)
    if fence:
        body = fence.group(1).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, dict) or set(value) != {"left", "right"}:
        return None
    if not isinstance(value["left"], list) or not isinstance(value["right"], list):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any submitted partition; never consult inst['answer']."""

    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if "left" not in answer or "right" not in answer:
        return False, "answer is missing a required side"
    if set(answer) != {"left", "right"}:
        return False, "answer has unexpected fields"
    left, right = answer["left"], answer["right"]
    if not isinstance(left, list) or not isinstance(right, list):
        return False, "both sides must be JSON lists"
    entries = left + right
    if any(type(v) is not int for v in entries):
        return False, "every vertex must be an integer"
    n = inst["n"]
    if any(v < 0 or v >= n for v in entries):
        return False, "vertex is outside the allowed range"
    if len(set(left)) != len(left) or len(set(right)) != len(right):
        return False, "a side contains a duplicate vertex"
    if any(left[i] >= left[i + 1] for i in range(len(left) - 1)) or any(
        right[i] >= right[i + 1] for i in range(len(right) - 1)
    ):
        return False, "each side must be strictly increasing"
    if set(left) & set(right):
        return False, "the two sides overlap"
    present = set(entries)
    required = set(range(n))
    if present != required:
        return False, "the partition is missing at least one vertex"
    if not left or not right:
        return False, "both sides must be nonempty"
    if left[0] != 0:
        return False, "vertex 0 must be in left"

    side = [1] * n
    for vertex in left:
        side[vertex] = 0
    for index, clause in enumerate(inst["clauses"], 1):
        a, b, c = clause
        if side[a] == side[b] == side[c]:
            return False, f"clause {index} is monochromatic"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from oriented nontrivial two-partitions."""

    n = inst["n"]
    while True:
        bits = [0] + [rng.randrange(2) for _ in range(n - 1)]
        if any(bits):
            return _partition_from_bits(bits)


def search_space(inst: dict) -> int:
    return (1 << (inst["n"] - 1)) - 1


def enumerate_all(inst: dict) -> int | None:
    n = inst["n"]
    if n > 22:
        return None
    count = 0
    for tail in itertools.product((0, 1), repeat=n - 1):
        if not any(tail):
            continue
        answer = _partition_from_bits([0] + list(tail))
        count += int(verify(inst, answer)[0])
    return count


def _pair_edges(inst: dict) -> list[tuple[int, int, int]]:
    weights = defaultdict(int)
    for clause in inst["clauses"]:
        for a, b in itertools.combinations(clause, 2):
            if a > b:
                a, b = b, a
            weights[(a, b)] += 1
    return [(a, b, weight) for (a, b), weight in sorted(weights.items())]


def _closed_walk_traces(inst: dict, steps: int = 12) -> list[int]:
    """Permutation-invariant traces of powers of the co-occurrence matrix."""

    n = inst["n"]
    prime = 1_000_000_007
    edges = _pair_edges(inst)
    traces = [0] * (steps + 1)
    for start in range(n):
        vector = [0] * n
        vector[start] = 1
        for power in range(1, steps + 1):
            nxt = [0] * n
            for a, b, weight in edges:
                nxt[a] += weight * vector[b]
                nxt[b] += weight * vector[a]
            vector = [value % prime for value in nxt]
            traces[power] = (traces[power] + vector[start]) % prime
    return traces[2:]


def canonical_key(inst: dict) -> str:
    """Strong cheap invariant; exact hypergraph isomorphism is not attempted."""

    occurrence = [0] * inst["n"]
    pair_multiplicities = defaultdict(int)
    for clause in inst["clauses"]:
        for v in clause:
            occurrence[v] += 1
        for pair in itertools.combinations(sorted(clause), 2):
            pair_multiplicities[pair] += 1
    payload = {
        "family": "five-colourable-monotone-nae-v1",
        "n": inst["n"],
        "m": len(inst["clauses"]),
        "occurrence_multiset": sorted(occurrence),
        "pair_multiplicity_multiset": sorted(pair_multiplicities.values()),
        "cooccurrence_traces": _closed_walk_traces(inst),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """First add fixed-witness crowding, then grow n until the answer cap binds."""

    out = {
        "n": int(params.get("n", 150)),
        "degree": int(params.get("degree", 6)),
        "extra_layers": int(params.get("extra_layers", 0)),
    }
    if out["n"] == 10:
        return dict(DIFFICULTY["easy"])
    maximum_layers = out["n"] // 60
    if out["extra_layers"] < maximum_layers:
        out["extra_layers"] += 1
        return out
    if out["n"] < 240:
        out["n"] = min(240, out["n"] + 30)
        out["n"] -= out["n"] % 30
        out["extra_layers"] = min(out["extra_layers"], out["n"] // 60)
        return out
    return "cap_bound"


# ---------------------------------------------------------------------------
# Adversary panel


def _bits_from_answer(inst: dict, answer: object) -> list[int] | None:
    if not isinstance(answer, dict) or not isinstance(answer.get("left"), list):
        return None
    bits = [1] * inst["n"]
    for v in answer["left"]:
        if type(v) is int and 0 <= v < inst["n"]:
            bits[v] = 0
    return bits


def _bad_clauses(inst: dict, bits: list[int]) -> list[int]:
    return [
        index
        for index, (a, b, c) in enumerate(inst["clauses"])
        if bits[a] == bits[b] == bits[c]
    ]


def _incidence(inst: dict) -> list[list[int]]:
    rows = [[] for _ in range(inst["n"])]
    for index, clause in enumerate(inst["clauses"]):
        for vertex in clause:
            rows[vertex].append(index)
    return rows


def _local_repair(inst: dict, bits: list[int], steps: int) -> tuple[list[int] | None, int]:
    incidence = _incidence(inst)
    bad = set(_bad_clauses(inst, bits))
    operations = 0
    for _ in range(steps):
        if not bad:
            return bits, operations
        best_gain = 0
        best_vertex = None
        for vertex in range(inst["n"]):
            before = sum(index in bad for index in incidence[vertex])
            bits[vertex] ^= 1
            after = 0
            for index in incidence[vertex]:
                a, b, c = inst["clauses"][index]
                after += int(bits[a] == bits[b] == bits[c])
                operations += 1
            bits[vertex] ^= 1
            gain = before - after
            if gain > best_gain:
                best_gain = gain
                best_vertex = vertex
        if best_vertex is None:
            return None, operations
        bits[best_vertex] ^= 1
        for index in incidence[best_vertex]:
            a, b, c = inst["clauses"][index]
            if bits[a] == bits[b] == bits[c]:
                bad.add(index)
            else:
                bad.discard(index)
    return (bits if not bad else None), operations


def _attack_occurrence_outlier(inst: dict) -> tuple[object | None, int]:
    occurrence = [0] * inst["n"]
    index_sum = [0] * inst["n"]
    for index, clause in enumerate(inst["clauses"]):
        for vertex in clause:
            occurrence[vertex] += 1
            index_sum[vertex] += index
    ordered = sorted(range(inst["n"]), key=lambda v: (occurrence[v], index_sum[v], v))
    bits = [0] * inst["n"]
    for vertex in ordered[inst["n"] // 2:]:
        bits[vertex] = 1
    return _partition_from_bits(bits), len(inst["clauses"]) * 3


def _attack_greedy(inst: dict) -> tuple[object | None, int]:
    bits = [-1] * inst["n"]
    bits[0] = 0
    operations = 0
    for vertex in range(1, inst["n"]):
        scores = []
        for value in (0, 1):
            bits[vertex] = value
            violations = 0
            for a, b, c in inst["clauses"]:
                values = (bits[a], bits[b], bits[c])
                if -1 not in values and values[0] == values[1] == values[2]:
                    violations += 1
                operations += 1
            scores.append(violations)
        bits[vertex] = 0 if scores[0] <= scores[1] else 1
    return _partition_from_bits(bits), operations


def _attack_walksat(inst: dict, rng: random.Random, restarts: int = 64,
                    steps_per_variable: int = 8) -> tuple[object | None, int]:
    n = inst["n"]
    incidence = _incidence(inst)
    operations = 0
    for _ in range(restarts):
        bits = [0] + [rng.randrange(2) for _ in range(n - 1)]
        bad = set(_bad_clauses(inst, bits))
        for _ in range(steps_per_variable * n):
            if not bad:
                return _partition_from_bits(bits), operations
            clause_index = rng.choice(tuple(bad))
            vertex = rng.choice(inst["clauses"][clause_index])
            bits[vertex] ^= 1
            operations += 1
            for index in incidence[vertex]:
                a, b, c = inst["clauses"][index]
                if bits[a] == bits[b] == bits[c]:
                    bad.add(index)
                else:
                    bad.discard(index)
        # Vertex zero only orients the answer; complement if a walk flipped it.
        if bits[0]:
            bits = [1 - value for value in bits]
    return None, operations


def _attack_spectral(inst: dict, rng: random.Random) -> tuple[object | None, int]:
    n = inst["n"]
    neighbours = [defaultdict(int) for _ in range(n)]
    for a, b, weight in _pair_edges(inst):
        neighbours[a][b] += weight
        neighbours[b][a] += weight
    vector = [rng.uniform(-1.0, 1.0) for _ in range(n)]
    operations = 0
    shift = 2 * inst["maximum_occurrence"] + 3.0
    for _ in range(160):
        nxt = []
        for vertex in range(n):
            value = shift * vector[vertex]
            for other, weight in neighbours[vertex].items():
                value -= weight * vector[other]
                operations += 1
            nxt.append(value)
        norm = math.sqrt(sum(value * value for value in nxt)) or 1.0
        vector = [value / norm for value in nxt]
    bits = [int(value >= 0.0) for value in vector]
    repaired, repair_ops = _local_repair(inst, bits, n)
    operations += repair_ops
    if repaired is None:
        return None, operations
    return _partition_from_bits(repaired), operations


class _DPLLLimit(Exception):
    pass


def _dpll_search(inst: dict, node_limit: int = 10_000) -> tuple[object | None, dict]:
    clauses = inst["clauses"]
    incidence = _incidence(inst)
    nodes = 0
    clause_scans = 0

    def propagate(bits: list[int]) -> bool:
        nonlocal clause_scans
        changed = True
        while changed:
            changed = False
            for a, b, c in clauses:
                clause_scans += 1
                values = (bits[a], bits[b], bits[c])
                unknown = [index for index, value in enumerate(values) if value < 0]
                if not unknown:
                    if values[0] == values[1] == values[2]:
                        return False
                elif len(unknown) == 1:
                    known = [value for value in values if value >= 0]
                    if known[0] == known[1]:
                        vertex = (a, b, c)[unknown[0]]
                        needed = 1 - known[0]
                        if bits[vertex] >= 0 and bits[vertex] != needed:
                            return False
                        if bits[vertex] < 0:
                            bits[vertex] = needed
                            changed = True
        return True

    def solve(bits: list[int]) -> list[int] | None:
        nonlocal nodes
        nodes += 1
        if nodes > node_limit:
            raise _DPLLLimit
        bits = bits[:]
        if not propagate(bits):
            return None
        if all(value >= 0 for value in bits):
            return bits
        candidates = [v for v, value in enumerate(bits) if value < 0]
        vertex = max(
            candidates,
            key=lambda v: (
                sum(sum(bits[x] >= 0 for x in clauses[index]) for index in incidence[v]),
                len(incidence[v]),
                -v,
            ),
        )
        for value in (0, 1):
            child = bits[:]
            child[vertex] = value
            found = solve(child)
            if found is not None:
                return found
        return None

    limit_reached = False
    try:
        initial = [-1] * inst["n"]
        initial[0] = 0
        found = solve(initial)
    except _DPLLLimit:
        found = None
        limit_reached = True
    return (
        None if found is None else _partition_from_bits(found),
        {
            "nodes": nodes,
            "node_limit": node_limit,
            "clause_scans": clause_scans,
            "limit_reached": limit_reached,
        },
    )


def _relabel_instance(inst: dict, rng: random.Random) -> dict:
    permutation = list(range(inst["n"]))
    rng.shuffle(permutation)  # old -> new
    clauses = [[permutation[v] for v in clause] for clause in inst["clauses"]]
    for clause in clauses:
        rng.shuffle(clause)
    rng.shuffle(clauses)
    left = sorted(permutation[v] for v in inst["answer"]["left"])
    right = sorted(permutation[v] for v in inst["answer"]["right"])
    if 0 in right:
        left, right = right, left
    return {
        "family": inst["family"],
        "n": inst["n"],
        "clauses": clauses,
        "clause_count": len(clauses),
        "maximum_occurrence": inst["maximum_occurrence"],
        "answer": {"left": left, "right": right},
    }


def _reorder_instance(inst: dict, rng: random.Random) -> dict:
    out = {
        "family": inst["family"],
        "n": inst["n"],
        "clauses": [clause[:] for clause in inst["clauses"]],
        "clause_count": inst["clause_count"],
        "maximum_occurrence": inst["maximum_occurrence"],
        "answer": {"left": inst["answer"]["left"][:], "right": inst["answer"]["right"][:]},
    }
    for clause in out["clauses"]:
        rng.shuffle(clause)
    rng.shuffle(out["clauses"])
    return out


def _corruptions(inst: dict) -> dict[str, object]:
    answer = inst["answer"]
    left, right = answer["left"], answer["right"]
    dropped = {"left": left[:-1], "right": right[:]}
    swapped_left = left[:]
    swapped_left[0], swapped_left[1] = swapped_left[1], swapped_left[0]
    swapped = {"left": swapped_left, "right": right[:]}
    duplicated_left = left[:]
    duplicated_left.insert(1, duplicated_left[0])
    duplicated = {"left": duplicated_left, "right": right[:]}
    outside_right = right[:]
    outside_right[-1] = inst["n"]
    outside = {"left": left[:], "right": outside_right}
    return {
        "drop_one": dropped,
        "swap_order": swapped,
        "duplicate": duplicated,
        "empty": {},
        "out_of_range": outside,
    }


def selftest() -> dict:
    report: dict[str, object] = {"paper": "1003.3704", "track": TRACK}

    g1_rows = {}
    g1_pass = True
    json_native = 0
    total_instances = 0
    for preset, params in DIFFICULTY.items():
        rows = []
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            roundtrip = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            rows.append({"seed": seed, "ok": ok, "reason": why, "json_native": roundtrip})
            g1_pass &= ok and roundtrip
            json_native += int(roundtrip)
            total_instances += 1
        g1_rows[preset] = rows
    report["G1_planted_verifies"] = {
        "pass": g1_pass,
        "instances_checked": total_instances,
        "json_native_roundtrips": json_native,
        "presets": g1_rows,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=314_159, **shipping_params)
    corruption_rows = {}
    for name, candidate in _corruptions(ship).items():
        accepted, reason = verify(ship, candidate)
        corruption_rows[name] = {"accepted": accepted, "reason": reason}
    reasons = [row["reason"] for row in corruption_rows.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not row["accepted"] for row in corruption_rows.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_rows,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The two sides below satisfy every NAE clause.\n\n<answer>\n```json\n"
        + json.dumps(ship["answer"], separators=(",", ":"))
        + "\n```\n</answer>\nI used zero-based indexing."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == ship["answer"],
        "parsed_left": None if parsed is None else len(parsed["left"]),
        "parsed_right": None if parsed is None else len(parsed["right"]),
    }

    guess_rng = random.Random(0x10033704)
    guess_total = 200_000
    guess_hits = 0
    guess_started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_seconds = time.perf_counter() - guess_started
    observed_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": observed_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": observed_fraction,
        "candidate_space": search_space(ship),
        "prior": "uniform over all nontrivial oriented partitions, with vertex 0 in left",
        "wall_clock_sec": round(guess_seconds, 6),
    }

    baseline_started = time.perf_counter()
    baseline_candidate, baseline_stats = _dpll_search(ship)
    baseline_seconds = time.perf_counter() - baseline_started
    baseline_solved = bool(baseline_candidate and verify(ship, baseline_candidate)[0])
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    exact_demo = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": observed_fraction < 1e-6 and not baseline_solved,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_valid_fraction": observed_fraction,
        "shipping_baseline_wall_seconds": round(baseline_seconds, 6),
        "shipping_baseline_nodes": baseline_stats["nodes"],
        "shipping_baseline_clause_scans": baseline_stats["clause_scans"],
        "shipping_baseline_solved": baseline_solved,
        "exact_demo_valid_answer_count": exact_demo,
        "exact_demo_candidate_count": search_space(demo),
    }

    attack_names = (
        "occurrence_outlier",
        "greedy_left_to_right",
        "random_restart_walksat_64x8n",
        "spectral_bottom_eigenvector_with_repair",
        "nae_dpll_unit_propagation_10000",
    )
    stats = {
        name: {"successes": 0, "attempts": 0, "operations": 0, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    node_samples = []
    dpll_time_samples = []
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **shipping_params)
        rng = random.Random(seed ^ 0xA5A5)
        attacks = {
            "occurrence_outlier": lambda: _attack_occurrence_outlier(inst),
            "greedy_left_to_right": lambda: _attack_greedy(inst),
            "random_restart_walksat_64x8n": lambda: _attack_walksat(inst, rng),
            "spectral_bottom_eigenvector_with_repair": lambda: _attack_spectral(inst, rng),
        }
        for name, attack in attacks.items():
            started = time.perf_counter()
            candidate, operations = attack()
            elapsed = time.perf_counter() - started
            success = bool(candidate and verify(inst, candidate)[0])
            stats[name]["successes"] += int(success)
            stats[name]["attempts"] += 1
            stats[name]["operations"] += operations
            stats[name]["wall_clock_sec"] += elapsed

        started = time.perf_counter()
        candidate, dpll_stats = _dpll_search(inst)
        elapsed = time.perf_counter() - started
        success = bool(candidate and verify(inst, candidate)[0])
        row = stats["nae_dpll_unit_propagation_10000"]
        row["successes"] += int(success)
        row["attempts"] += 1
        row["operations"] += dpll_stats["clause_scans"]
        row["wall_clock_sec"] += elapsed
        node_samples.append(dpll_stats["nodes"])
        dpll_time_samples.append(elapsed)

    for row in stats.values():
        row["wall_clock_sec"] = round(row["wall_clock_sec"], 6)
    report["G6_adversary_panel"] = {
        "pass": all(row["successes"] == 0 for row in stats.values()),
        "attacks": stats,
        "strongest_attack": "NAE-DPLL with unit propagation",
        "dpll_nodes_median": int(statistics.median(node_samples)),
        "dpll_wall_clock_sec_median": round(statistics.median(dpll_time_samples), 6),
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled_params["extra_layers"] *= 2
    doubled = make_instance(seed=271_828, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    harder = escalate(shipping_params)
    if isinstance(harder, dict):
        harder_inst = make_instance(seed=271_829, **harder)
        harder_ok = verify(harder_inst, harder_inst["answer"])[0]
        fixed_axis = (
            harder["n"] == shipping_params["n"]
            and harder["extra_layers"] > shipping_params["extra_layers"]
        )
    else:
        harder_ok = harder == "cap_bound"
        fixed_axis = harder == "cap_bound"
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * ship["n"] and harder_ok,
        "shipping_n": ship["n"],
        "shipping_clauses": ship["clause_count"],
        "doubled_n": doubled["n"],
        "doubled_clauses": doubled["clause_count"],
        "doubled_planted_verifies": doubled_ok,
        "doubled_verify_reason": doubled_reason,
        "escalated_params": harder,
        "escalated_planted_verifies": harder_ok,
        "fixed_answer_length_axis_used_first": fixed_axis,
    }

    invariant_checks = 0
    preservation_checks = 0
    keys = []
    g8_ok = True
    for seed in range(1_200, 1_220):
        inst = make_instance(seed=seed, **shipping_params)
        key = canonical_key(inst)
        keys.append(key)
        relabelled = _relabel_instance(inst, random.Random(seed * 17 + 1))
        reordered = _reorder_instance(inst, random.Random(seed * 17 + 2))
        composed = _reorder_instance(relabelled, random.Random(seed * 17 + 3))
        for transformed in (relabelled, reordered, composed):
            invariant_checks += 1
            g8_ok &= canonical_key(transformed) == key
            preservation_checks += 1
            g8_ok &= verify(transformed, transformed["answer"])[0]
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": g8_ok and distinct == 20,
        "invariance_checks": invariant_checks,
        "certificate_preservation_checks": preservation_checks,
        "distinct_unrelated_instances": distinct,
        "unrelated_instances_tested": 20,
        "transformations": [
            "arbitrary variable renumbering with certificate carried",
            "clause and within-clause reordering",
            "composition of both transformations",
        ],
        "caveat": "closed-walk traces are a strong invariant, not a complete hypergraph canonizer",
    }

    answer_char_samples = [
        len(json.dumps(make_instance(seed=seed, **shipping_params)["answer"], separators=(",", ":")))
        for seed in range(64)
    ]
    answer_chars = max(answer_char_samples)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = ship["n"]
    intended_operations = ship["n"]
    arms = G9_RESULTS["arms"]
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    evidence_complete = all(arms[name]["attempts"] >= 3 for name in arms)
    hinted_hardened = G9_RESULTS.get("hinted_verdict") == "hardened"
    within_caps = answer_chars <= 2_000 and answer_elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": evidence_complete and hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS.get("hinted_verdict"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "answer_size_instances_measured": len(answer_char_samples),
        "intended_route_operations": intended_operations,
        "operation_model": "one exact side-membership write per vertex after identifying the global split",
    }
    PROBLEM_PROFILE["max_answer_tokens"] = answer_tokens

    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping_params
    report["all_passed"] = all(
        value.get("pass", False)
        for name, value in report.items()
        if name.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
