"""Verified affine matching-cut generator for arXiv:2505.22351.

The paper proves that d-Cut is NP-complete even on partitioned probe split
graphs.  This module constructs connected regular bipartite members of that
native class.  An affine parity polynomial is sampled first, and the graph is
built around its two fibres, so the certificate is known by inverse generation.
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
import statistics
import time
from collections import deque


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "graph",
    "certificate_form": "polynomial",
    "native_objects": [
        "connected bipartite graph",
        "partition into probes and independent non-probes",
        "affine vertex labels over F_2",
        "matching-cut opposite-neighbour constraint",
    ],
    "verification_operations": [
        "exact affine-polynomial evaluation over F_2",
        "opposite-colour neighbour counting",
        "set and graph-incidence checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 4, Theorem 4.3: a bipartite graph is partitioned probe split "
        "when one bipartition class is made the independent non-probe set"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The Hamming-weight-one and -two differences on selected graph edges "
        "span the codimension-one parity kernel; without noticing that invariant, "
        "one must recover the sparse cut mechanically and fit its affine separator."
    ),
    "hardness_basis": (
        "Track B: unit-capacity Ford-Fulkerson followed by exact GF(2) elimination "
        "solves this generated subclass in O(k(n+m)+n b^2) and at shipping n=68 "
        "measured a median 23,275 counted bit operations and 0.0005 seconds over "
        "eight instances, whereas the compact parity-kernel route uses 228 operations."
    ),
    "max_answer_tokens": 13,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "An affine polynomial P(x)=c_0*x_0 XOR ... XOR c_(b-1)*x_(b-1) "
        "XOR q over F_2, represented by b coefficient bits followed by q. "
        "Candidates are oriented by P(source)=0 and P(target)=1."
    ),
    "bounds": {
        "field_order": 2,
        "max_degree": 1,
        "shipping_variables": 24,
        "shipping_coefficient_count": 25,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 30, "label_bits": 7, "cut_size": 2, "degree": 6},
    "easy": {"n": 68, "label_bits": 24, "cut_size": 2, "degree": 6},
    "medium": {"n": 76, "label_bits": 24, "cut_size": 2, "degree": 6},
    "hard": {"n": 84, "label_bits": 24, "cut_size": 2, "degree": 6},
}

SHIPPING_DIFFICULTY: str = "easy"

STRUCTURAL_HINT: str = (
    "The Hamming-weight-one and -two label differences on edges lie in a common codimension-one parity kernel."
)
PLACEBO_HINT: str = (
    "The binary vertex labels and the undirected edge list both reward consistent, careful bookkeeping."
)

# Filled from the script-owned hardening runs.  The diagnostic arms never gate
# G9; only the answer and intended-route caps do.
G9_EVIDENCE = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 1, "attempts": 3},
    },
    "hinted_verdict": "hardened",
    "oracle_status": "completed",
    "error_records": {"bare": 0, "hinted": 0, "placebo": 0},
}

NOTES: str = r"""
Section 2 and Observation 2.1 fix the exact object: a red-blue d-colouring
uses both colours and gives every vertex at most d neighbours of the other
colour.  The same section explicitly defines precoloured pairs, which license
the source/target orientation used here.  Section 4, Theorem 4.3 is the native
probe-split result: for a bipartite graph, take one bipartition class as the
independent non-probe set and add all missing edges inside it; the completion
is split.  No graph, SAT, or finite-field surrogate replaces the paper's graph
object--the affine labels are benchmark-side certificate compression, and the
polynomial is accepted only after its induced colouring passes the paper's
native opposite-neighbour test on the supplied graph.

Theorem 1.4 is the STEP-0 warning about easy regimes.  For d>=2, d-Cut is
polynomial on partitioned probe H-free graphs exactly when H is an induced
subgraph of P1+P4; Theorem 3.2 supplies the positive result by bounded
branching and colour-processing, while Theorem 3.1 covers matching cut.
Conversely, Theorem 4.3 proves NP-hardness
on probe split (hence probe 2P2-free) graphs for every fixed d.  That is only a
worst-case statement.  This generated distribution has a polynomial min-cut
route, so the module is honestly Track B rather than claiming Track A.

Generation is inverse.  A balanced non-sparse affine polynomial is drawn
first.  Its zero and one fibres each receive a regular connected bipartite
union of edge-disjoint Hamiltonian cycles.  Two internal matching edges are exchanged for two cross-fibre
edges, leaving every vertex regular while the cross edges form a matching.
Inside either fibre, deleting the one exchanged edge leaves one Hamiltonian
path and two Hamiltonian cycles, so every nontrivial internal cut has at least
1+2+2=5 edges; the two cross-fibre edges are therefore the unique minimum
terminal cut used by the reference algorithm.
The zero fibre contains a systematic basis of short label differences for the
kernel.  Cross edges are resampled until their differences have Hamming weight
greater than two, so the compact invariant is guaranteed for every seed.

Equal degrees defeat the per-vertex outlier attack.  Dense planted coefficient
vectors defeat one- and two-coordinate affine ansatzes.  Random affine
restarts and a one-sweep local greedy heuristic fail in the measured panel.
The required domain algorithm is not hidden: unit-capacity Ford-Fulkerson
recovers the unique small terminal cut and exact GF(2) elimination fits its
affine separator.  A lazy-adjacency spectral bisection is audited separately
and is expected to succeed on this Track B distribution.
""".strip()


def _parity(value: int) -> int:
    return value.bit_count() & 1


def _bits_text(value: int, width: int) -> str:
    # Left-to-right order is x_0, x_1, ..., not ordinary binary place order.
    return "".join(str((value >> bit) & 1) for bit in range(width))


def _answer_text(answer: list[int]) -> str:
    return "".join(str(bit) for bit in answer[:-1]) + "|" + str(answer[-1])


def _sample_function(label_bits: int, rng: random.Random) -> tuple[int, int]:
    low = max(3, label_bits // 3)
    high = label_bits - low
    while True:
        mask = rng.randrange(1, 1 << label_bits)
        if low <= mask.bit_count() <= high:
            return mask, rng.randrange(2)


def _sample_label(
    wanted: int,
    mask: int,
    constant: int,
    label_bits: int,
    used: set[int],
    rng: random.Random,
) -> int:
    for _ in range(1 << min(label_bits, 16)):
        value = rng.randrange(1 << label_bits)
        if value in used:
            continue
        if (_parity(mask & value) ^ constant) == wanted:
            used.add(value)
            return value
    raise RuntimeError("could not sample a fresh label in the requested fibre")


def _validate_params(n: int, label_bits: int, cut_size: int, degree: int) -> None:
    values = (n, label_bits, cut_size, degree)
    if any(isinstance(v, bool) or not isinstance(v, int) for v in values):
        raise ValueError("all parameters must be integers")
    if label_bits < 7:
        raise ValueError("label_bits must be at least 7")
    if cut_size < 2 or cut_size % 2:
        raise ValueError("cut_size must be a positive even integer")
    if degree % 2:
        raise ValueError("degree must be even")
    if degree <= cut_size * 2:
        raise ValueError("degree must exceed twice cut_size")
    left_size = 2 * (label_bits - 1) + cut_size
    right_size = n - left_size
    if n % 2 or left_size % 2 or right_size % 2:
        raise ValueError("both hidden colour fibres must have even size")
    if left_size // 2 <= degree or right_size // 2 <= degree:
        raise ValueError("each bipartite cell must contain more than degree vertices")
    if n >= (1 << label_bits):
        raise ValueError("label space is too small for distinct vertex labels")


def _joint_shuffle(pairs: list[list[int]], rng: random.Random) -> tuple[list[int], list[int]]:
    pairs = [list(pair) for pair in pairs]
    rng.shuffle(pairs)
    return [pair[0] for pair in pairs], [pair[1] for pair in pairs]


def _bipartite_hamiltonian_edges(
    first: list[int], second: list[int], degree: int, rng: random.Random
) -> set[tuple[int, int]]:
    """Union of edge-disjoint Hamiltonian cycles in a balanced bipartite graph.

    The first cycle uses identity and shift-one matchings, so every aligned
    pair is an edge.  Each later pair of matchings is sampled so that their
    union is another Hamiltonian cycle and no edge is repeated.
    """
    if len(first) != len(second):
        raise ValueError("bipartite cells have unequal size")
    size = len(first)
    permutations: list[list[int]] = [
        list(range(size)),
        [(i + 1) % size for i in range(size)],
    ]
    used_by_row = [{i, (i + 1) % size} for i in range(size)]

    def new_permutation() -> list[int]:
        for _ in range(20_000):
            candidate = list(range(size))
            rng.shuffle(candidate)
            if all(candidate[i] not in used_by_row[i] for i in range(size)):
                return candidate
        raise RuntimeError("could not sample an edge-disjoint perfect matching")

    def union_is_hamiltonian(p: list[int], q: list[int]) -> bool:
        inverse_q = [0] * size
        for i, value in enumerate(q):
            inverse_q[value] = i
        seen = set()
        current = 0
        while current not in seen:
            seen.add(current)
            current = inverse_q[p[current]]
        return current == 0 and len(seen) == size

    for _cycle in range(1, degree // 2):
        for _ in range(20_000):
            p = new_permutation()
            for i, value in enumerate(p):
                used_by_row[i].add(value)
            try:
                q = new_permutation()
            finally:
                for i, value in enumerate(p):
                    used_by_row[i].remove(value)
            if union_is_hamiltonian(p, q):
                permutations.extend((p, q))
                for i in range(size):
                    used_by_row[i].add(p[i])
                    used_by_row[i].add(q[i])
                break
        else:
            raise RuntimeError("could not sample an edge-disjoint Hamiltonian cycle")

    edges: set[tuple[int, int]] = set()
    for permutation in permutations:
        for i, u in enumerate(first):
            v = second[permutation[i]]
            edges.add((min(u, v), max(u, v)))
    return edges


def _far_matching(
    left: list[int], right: list[int], rng: random.Random
) -> list[int] | None:
    candidates: list[list[int]] = []
    for value in left:
        row = [
            j for j, other in enumerate(right)
            if (value ^ other).bit_count() > 2
        ]
        rng.shuffle(row)
        candidates.append(row)
    order = list(range(len(left)))
    rng.shuffle(order)
    order.sort(key=lambda i: len(candidates[i]))
    owner: dict[int, int] = {}

    def augment(i: int, seen: set[int]) -> bool:
        for j in candidates[i]:
            if j in seen:
                continue
            seen.add(j)
            if j not in owner or augment(owner[j], seen):
                owner[j] = i
                return True
        return False

    if any(not augment(i, set()) for i in order):
        return None
    result = [0] * len(left)
    for j, i in owner.items():
        result[i] = j
    return result


def _coordinate_signatures(inst: dict) -> list[tuple]:
    """Translation-invariant signatures used to canonicalise bit permutations."""
    n = inst["n"]
    d = inst["label_bits"]
    source = inst["source"]
    origin = inst["labels"][source]
    adjacency = [[] for _ in range(n)]
    for u, v in inst["edges"]:
        adjacency[u].append(v)
        adjacency[v].append(u)
    probes = set(inst["P"])
    signatures = []
    for bit in range(d):
        values = [((label ^ origin) >> bit) & 1 for label in inst["labels"]]
        edge_cross = sum(values[u] != values[v] for u, v in inst["edges"])
        local = []
        for vertex in range(n):
            role = 1 if vertex == source else 2 if vertex == inst["target"] else 0
            one_neighbours = sum(values[w] for w in adjacency[vertex])
            local.append(
                (role, int(vertex in probes), values[vertex], one_neighbours)
            )
        signatures.append((values[inst["target"]], edge_cross, tuple(sorted(local))))
    return signatures


def _build_once(
    n: int,
    label_bits: int,
    cut_size: int,
    degree: int,
    rng: random.Random,
) -> dict:
    coefficient_mask, constant = _sample_function(label_bits, rng)
    pivot = (coefficient_mask & -coefficient_mask).bit_length() - 1
    used: set[int] = set()

    # Each pair difference is a systematic kernel vector.  The collection is
    # a basis of the codimension-one kernel of coefficient_mask.
    kernel_pairs: list[list[int]] = []
    for bit in range(label_bits):
        if bit == pivot:
            continue
        difference = 1 << bit
        if (coefficient_mask >> bit) & 1:
            difference ^= 1 << pivot
        while True:
            first = _sample_label(
                0, coefficient_mask, constant, label_bits, used, rng
            )
            second = first ^ difference
            if second not in used:
                used.add(second)
                kernel_pairs.append([first, second])
                break
            used.remove(first)

    half_cross = cut_size // 2
    left_a_cross = [
        _sample_label(0, coefficient_mask, constant, label_bits, used, rng)
        for _ in range(half_cross)
    ]
    left_b_cross = [
        _sample_label(0, coefficient_mask, constant, label_bits, used, rng)
        for _ in range(half_cross)
    ]

    while True:
        right_b_cross = [
            _sample_label(1, coefficient_mask, constant, label_bits, used, rng)
            for _ in range(half_cross)
        ]
        right_a_cross = [
            _sample_label(1, coefficient_mask, constant, label_bits, used, rng)
            for _ in range(half_cross)
        ]
        a_to_b = _far_matching(left_a_cross, right_b_cross, rng)
        b_to_a = _far_matching(left_b_cross, right_a_cross, rng)
        if a_to_b is not None and b_to_a is not None:
            break
        used.difference_update(right_b_cross)
        used.difference_update(right_a_cross)

    left_slots = kernel_pairs + [
        [left_a_cross[i], left_b_cross[i]] for i in range(half_cross)
    ]
    left_a_labels, left_b_labels = _joint_shuffle(left_slots, rng)

    right_size = n - (2 * (label_bits - 1) + cut_size)
    right_cell_size = right_size // 2
    right_slots = [
        [right_a_cross[i], right_b_cross[i]] for i in range(half_cross)
    ]
    while len(right_slots) < right_cell_size:
        right_slots.append([
            _sample_label(1, coefficient_mask, constant, label_bits, used, rng),
            _sample_label(1, coefficient_mask, constant, label_bits, used, rng),
        ])
    right_a_labels, right_b_labels = _joint_shuffle(right_slots, rng)

    all_labels = left_a_labels + left_b_labels + right_a_labels + right_b_labels
    vertices = list(range(n))
    rng.shuffle(vertices)
    label_to_vertex = {label: vertices[i] for i, label in enumerate(all_labels)}
    labels = [0] * n
    for label, vertex in label_to_vertex.items():
        labels[vertex] = label

    left_a = [label_to_vertex[x] for x in left_a_labels]
    left_b = [label_to_vertex[x] for x in left_b_labels]
    right_a = [label_to_vertex[x] for x in right_a_labels]
    right_b = [label_to_vertex[x] for x in right_b_labels]
    edges = _bipartite_hamiltonian_edges(left_a, left_b, degree, rng)
    edges |= _bipartite_hamiltonian_edges(right_a, right_b, degree, rng)

    # Replace one internal matching edge incident with each future cross
    # endpoint.  This makes every vertex degree exactly `degree`.
    for a_labels, b_labels in (
        (left_a_cross, left_b_cross),
        (right_a_cross, right_b_cross),
    ):
        for a_label, b_label in zip(a_labels, b_labels):
            edge = tuple(sorted((label_to_vertex[a_label], label_to_vertex[b_label])))
            if edge not in edges:
                raise AssertionError("cross endpoints were not aligned at offset zero")
            edges.remove(edge)

    for i, j in enumerate(a_to_b or []):
        u = label_to_vertex[left_a_cross[i]]
        v = label_to_vertex[right_b_cross[j]]
        edges.add((min(u, v), max(u, v)))
    for i, j in enumerate(b_to_a or []):
        u = label_to_vertex[left_b_cross[i]]
        v = label_to_vertex[right_a_cross[j]]
        edges.add((min(u, v), max(u, v)))

    edge_list = [list(edge) for edge in edges]
    rng.shuffle(edge_list)
    probes = left_a + right_a
    nonprobes = left_b + right_b
    rng.shuffle(probes)
    rng.shuffle(nonprobes)
    source = label_to_vertex[kernel_pairs[0][0]]
    target = label_to_vertex[right_a_labels[0]]
    answer = [
        (coefficient_mask >> bit) & 1 for bit in range(label_bits)
    ] + [constant]
    return {
        "family": "Affine matching cut in a partitioned probe split graph",
        "n": n,
        "label_bits": label_bits,
        "d": 1,
        "cut_size": cut_size,
        "degree": degree,
        "vertices": list(range(n)),
        "labels": labels,
        "edges": edge_list,
        "P": probes,
        "N": nonprobes,
        "source": source,
        "target": target,
        "answer": answer,
    }


def make_instance(
    n: int,
    seed: int = 0,
    label_bits: int = 24,
    cut_size: int = 2,
    degree: int = 6,
    **params,
) -> dict:
    """Build a probe-split matching-cut instance by inverse generation."""
    if params:
        raise ValueError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, label_bits, cut_size, degree)
    rng = random.Random(seed)
    # Avoid accidentally indistinguishable displayed coordinates in the
    # intended short-difference puzzle.  A collision merely resamples
    # construction randomness; it never solves the graph or inspects the
    # planted certificate's validity.  canonical_key independently handles
    # arbitrary invertible changes of basis.
    for _attempt in range(64):
        try:
            inst = _build_once(n, label_bits, cut_size, degree, rng)
        except RuntimeError:
            continue
        signatures = _coordinate_signatures(inst)
        if len(set(signatures)) == label_bits:
            return inst
    raise RuntimeError("could not obtain uniquely canonicalisable coordinates")


def render(inst: dict) -> str:
    d = inst["label_bits"]
    label_lines = "\n".join(
        f"  {v}: {_bits_text(inst['labels'][v], d)}" for v in inst["vertices"]
    )
    edge_lines: list[str] = []
    row: list[str] = []
    for u, v in inst["edges"]:
        row.append(f"{u}-{v}")
        if len(row) == 12:
            edge_lines.append("  " + " ".join(row))
            row = []
    if row:
        edge_lines.append("  " + " ".join(row))

    statement = f"""Affine matching cut in a partitioned probe split graph

The undirected simple graph G below has vertices 0 through {inst['n'] - 1}.
P is the set of probes and N is the set of non-probes.  N is independent.
Adding every missing edge with both endpoints in N makes N a clique while P
is independent, so the completed graph is split; this is a partitioned probe
split graph.  The added completion edges are not edges of G and are not used
when checking your answer.

Each vertex v has a distinct {d}-bit label x(v).  The LEFTMOST displayed bit
is x_0, followed by x_1, ..., with x_{d - 1} rightmost.  An affine polynomial
over F_2 has the form
  Q(x) = c_0*x_0 XOR c_1*x_1 XOR ... XOR c_{d - 1}*x_{d - 1} XOR q,
where each coefficient and q is exactly 0 or 1.  Colour v red when Q(x(v))=0
and blue when Q(x(v))=1.

A red-blue 1-colouring is a matching cut when both colours occur and every
vertex has at most one neighbour of the opposite colour.  Find an affine Q
whose induced colouring is a matching cut, oriented so vertex {inst['source']}
is red and vertex {inst['target']} is blue.  Vertex numbering is 0-based;
edges are unordered; loops and repeated edges are absent.

P (probes): {inst['P']}
N (independent non-probes): {inst['N']}

Vertex labels (vertex: bits x_0...x_{d - 1}):
{label_lines}

Edges of G (u-v):
{chr(10).join(edge_lines)}

Give your final answer inside <answer></answer> tags as exactly {d} coefficient
bits c_0...c_{d - 1}, then a vertical bar, then the constant bit q.
Example for a 5-variable instance: <answer>01011|1</answer>
Whitespace inside the tags is allowed. Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    matches = re.findall(
        r"<answer>\s*([01](?:[01\s]*[01])?)\s*\|\s*([01])\s*</answer>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if len(matches) != 1:
        return None
    coefficients, constant = matches[0]
    coefficients = re.sub(r"\s+", "", coefficients)
    if not coefficients:
        return None
    return [int(bit) for bit in coefficients] + [int(constant)]


def _mask_from_answer(inst: dict, answer: object) -> tuple[int, int] | tuple[None, str]:
    expected = inst["label_bits"] + 1
    if not isinstance(answer, list):
        return None, "answer must be a coefficient list"
    if not answer:
        return None, "empty coefficient vector"
    if len(answer) < expected:
        return None, "coefficient vector is too short"
    if len(answer) > expected:
        return None, "coefficient vector is too long"
    if any(
        isinstance(bit, bool) or not isinstance(bit, int) or bit not in (0, 1)
        for bit in answer
    ):
        return None, "coefficient outside GF(2)"
    mask = sum(answer[bit] << bit for bit in range(inst["label_bits"]))
    return mask, answer[-1]


def _values(inst: dict, mask: int, constant: int) -> list[int]:
    return [_parity(mask & label) ^ constant for label in inst["labels"]]


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    parsed = _mask_from_answer(inst, answer)
    if parsed[0] is None:
        return False, parsed[1]
    mask, constant = parsed
    values = _values(inst, mask, constant)
    if (values[inst["source"]], values[inst["target"]]) != (0, 1):
        return False, "polynomial does not have the required terminal orientation"
    opposite = [0] * inst["n"]
    for u, v in inst["edges"]:
        if values[u] != values[v]:
            opposite[u] += 1
            if opposite[u] > inst["d"]:
                return False, f"vertex {u} exceeds the opposite-neighbour bound"
            opposite[v] += 1
            if opposite[v] > inst["d"]:
                return False, f"vertex {v} exceeds the opposite-neighbour bound"
    return True, "ok"


def _terminal_pivot(inst: dict) -> tuple[int, int]:
    delta = inst["labels"][inst["source"]] ^ inst["labels"][inst["target"]]
    pivot = (delta & -delta).bit_length() - 1
    return delta, pivot


def _answer_from_mask(inst: dict, mask: int) -> list[int]:
    constant = _parity(mask & inst["labels"][inst["source"]])
    return [
        (mask >> bit) & 1 for bit in range(inst["label_bits"])
    ] + [constant]


def random_candidate(inst: dict, rng: random.Random) -> object:
    d = inst["label_bits"]
    delta, pivot = _terminal_pivot(inst)
    mask = 0
    for bit in range(d):
        if bit != pivot and rng.randrange(2):
            mask |= 1 << bit
    if 1 ^ _parity(mask & delta):
        mask |= 1 << pivot
    return _answer_from_mask(inst, mask)


def search_space(inst: dict) -> int | None:
    return 1 << (inst["label_bits"] - 1)


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 200_000:
        return None
    d = inst["label_bits"]
    delta, pivot = _terminal_pivot(inst)
    free = [bit for bit in range(d) if bit != pivot]
    count = 0
    for word in range(space):
        mask = 0
        for pos, bit in enumerate(free):
            if (word >> pos) & 1:
                mask |= 1 << bit
        if 1 ^ _parity(mask & delta):
            mask |= 1 << pivot
        count += int(verify(inst, _answer_from_mask(inst, mask))[0])
    return count


def _wl_colours(inst: dict) -> tuple[list[int], list[list[int]]]:
    """Canonical colour refinement rooted at the two terminals and P/N roles."""
    n = inst["n"]
    adjacency = [[] for _ in range(n)]
    for u, v in inst["edges"]:
        adjacency[u].append(v)
        adjacency[v].append(u)
    probes = set(inst["P"])
    raw = [
        (int(v == inst["source"]), int(v == inst["target"]), int(v in probes))
        for v in range(n)
    ]
    palette = {value: i for i, value in enumerate(sorted(set(raw)))}
    colours = [palette[value] for value in raw]
    for _ in range(n):
        signatures = [
            (colours[v], tuple(sorted(colours[w] for w in adjacency[v])))
            for v in range(n)
        ]
        palette = {value: i for i, value in enumerate(sorted(set(signatures)))}
        refined = [palette[value] for value in signatures]
        if refined == colours:
            break
        colours = refined
    return colours, adjacency


def _basis_coordinates(vectors: list[int], dimension: int) -> dict[int, int]:
    """Coordinates in an ordered GF(2) basis, keyed by vector value."""
    if len(vectors) != dimension:
        raise ValueError("not enough vectors for an affine basis")
    echelon: dict[int, tuple[int, int]] = {}
    for index, vector in enumerate(vectors):
        reduced = vector
        combination = 1 << index
        for pivot in sorted(echelon, reverse=True):
            if (reduced >> pivot) & 1:
                row, row_combination = echelon[pivot]
                reduced ^= row
                combination ^= row_combination
        if not reduced:
            raise ValueError("affine basis vectors are dependent")
        echelon[reduced.bit_length() - 1] = (reduced, combination)

    def coordinates(vector: int) -> int:
        reduced = vector
        combination = 0
        for pivot in sorted(echelon, reverse=True):
            if (reduced >> pivot) & 1:
                row, row_combination = echelon[pivot]
                reduced ^= row
                combination ^= row_combination
        if reduced:
            raise ValueError("vertex labels do not lie in the affine span")
        return combination

    return {vector: coordinates(vector) for vector in set(vectors)}


def _canonical_payload(inst: dict) -> dict:
    """A vertex- and affine-coordinate-invariant payload.

    Stable colour refinement individualises every vertex at the shipping
    presets.  Its order chooses an affine basis of label differences, so the
    resulting coordinates are unchanged by every invertible GF(2) change of
    basis and by every global translation.  On a small symmetric instance,
    where refinement does not individualise, the fallback is the strongest
    cheap quotient invariant used by this family and deliberately omits labels.
    """
    colours, _adjacency = _wl_colours(inst)
    probes = set(inst["P"])
    common = {
        "n": inst["n"],
        "d": inst["d"],
        "degree": inst["degree"],
        "label_bits": inst["label_bits"],
    }
    if len(set(colours)) != inst["n"]:
        cell_sizes = [colours.count(colour) for colour in sorted(set(colours))]
        edge_cells: dict[tuple[int, int], int] = {}
        for u, v in inst["edges"]:
            pair = tuple(sorted((colours[u], colours[v])))
            edge_cells[pair] = edge_cells.get(pair, 0) + 1
        return {
            **common,
            "fallback": "stable rooted colour-refinement quotient",
            "cell_sizes": cell_sizes,
            "edge_cells": sorted([a, b, count] for (a, b), count in edge_cells.items()),
        }

    vertex_order = sorted(range(inst["n"]), key=lambda v: colours[v])
    origin = inst["labels"][inst["source"]]
    selected: list[int] = []
    echelon: dict[int, int] = {}
    for vertex in vertex_order:
        difference = inst["labels"][vertex] ^ origin
        reduced = difference
        for pivot in sorted(echelon, reverse=True):
            if (reduced >> pivot) & 1:
                reduced ^= echelon[pivot]
        if reduced:
            echelon[reduced.bit_length() - 1] = reduced
            selected.append(difference)
            if len(selected) == inst["label_bits"]:
                break
    coordinate_map = _basis_coordinates(selected, inst["label_bits"])

    # _basis_coordinates only receives basis vectors; reduce all label
    # differences in the same ordered basis here.
    basis_echelon: dict[int, tuple[int, int]] = {}
    for index, vector in enumerate(selected):
        reduced = vector
        combination = 1 << index
        for pivot in sorted(basis_echelon, reverse=True):
            if (reduced >> pivot) & 1:
                row, row_combination = basis_echelon[pivot]
                reduced ^= row
                combination ^= row_combination
        basis_echelon[reduced.bit_length() - 1] = (reduced, combination)

    def canonical_label(label: int) -> int:
        difference = label ^ origin
        if difference in coordinate_map:
            return coordinate_map[difference]
        result = 0
        for pivot in sorted(basis_echelon, reverse=True):
            if (difference >> pivot) & 1:
                row, combination = basis_echelon[pivot]
                difference ^= row
                result ^= combination
        if difference:
            raise ValueError("vertex labels do not have full affine span")
        return result

    position = {vertex: i for i, vertex in enumerate(vertex_order)}
    return {
        **common,
        "labels": [canonical_label(inst["labels"][v]) for v in vertex_order],
        "roles": [
            [
                int(v == inst["source"]),
                int(v == inst["target"]),
                int(v in probes),
            ]
            for v in vertex_order
        ],
        "edges": sorted(
            sorted((position[u], position[v])) for u, v in inst["edges"]
        ),
    }


def canonical_key(inst: dict) -> str:
    """Invariant under vertex relabelling and affine GF(2) label changes."""
    blob = json.dumps(
        _canonical_payload(inst), sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    return hashlib.sha256(blob).hexdigest()


def escalate(params: dict) -> dict | str | None:
    n = int(params["n"])
    label_bits = int(params.get("label_bits", 24))
    cut_size = int(params.get("cut_size", 2))
    degree = int(params.get("degree", 6))
    # The compact route scans m=n*degree/2 edges and makes label_bits coefficient
    # decisions.  Grow n while the polynomial answer stays exactly the same size.
    max_n = 2 * ((300 - label_bits) // degree)
    if n < max_n:
        new_n = min(max_n, max(n + 8, ((5 * n) // 4 + 1) // 2 * 2))
        return {
            "n": new_n,
            "label_bits": label_bits,
            "cut_size": cut_size,
            "degree": degree,
        }
    return "cap_bound"


def _add_directed(residual: list, u: int, v: int, capacity: int) -> None:
    forward = [v, len(residual[v]), capacity]
    reverse = [u, len(residual[u]), 0]
    residual[u].append(forward)
    residual[v].append(reverse)


def _fit_affine(inst: dict, values: list[int]) -> tuple[object | None, dict]:
    variables = inst["label_bits"] + 1
    rows = [
        label | (1 << inst["label_bits"]) | (values[v] << variables)
        for v, label in enumerate(inst["labels"])
    ]
    rank = 0
    pivot_tests = 0
    row_xors = 0
    for column in range(variables):
        pivot_row = None
        for row_index in range(rank, len(rows)):
            pivot_tests += 1
            if (rows[row_index] >> column) & 1:
                pivot_row = row_index
                break
        if pivot_row is None:
            continue
        rows[rank], rows[pivot_row] = rows[pivot_row], rows[rank]
        for row_index in range(len(rows)):
            if row_index != rank and ((rows[row_index] >> column) & 1):
                rows[row_index] ^= rows[rank]
                row_xors += 1
        rank += 1
    stats = {
        "rank": rank,
        "pivot_tests": pivot_tests,
        "row_xors": row_xors,
        "bit_operations": pivot_tests + row_xors * (variables + 1),
    }
    coefficient_mask = (1 << variables) - 1
    for row in rows:
        if (row & coefficient_mask) == 0 and ((row >> variables) & 1):
            return None, stats
    if rank < variables:
        return None, stats
    solution = [0] * variables
    for row in rows:
        coefficients = row & coefficient_mask
        if coefficients and not (coefficients & (coefficients - 1)):
            column = coefficients.bit_length() - 1
            solution[column] = (row >> variables) & 1
    return solution, stats


def _reference_min_cut_and_fit(inst: dict) -> tuple[object | None, dict]:
    """Unit-capacity terminal min-cut followed by exact affine fitting."""
    n = inst["n"]
    residual: list[list[list[int]]] = [[] for _ in range(n)]
    for u, v in inst["edges"]:
        _add_directed(residual, u, v, 1)
        _add_directed(residual, v, u, 1)
    source, target = inst["source"], inst["target"]
    flow = 0
    bfs_rounds = 0
    edge_scans = 0
    while True:
        bfs_rounds += 1
        previous: list[tuple[int, int] | None] = [None] * n
        previous[source] = (-1, -1)
        queue = deque([source])
        while queue and previous[target] is None:
            u = queue.popleft()
            for edge_index, edge in enumerate(residual[u]):
                edge_scans += 1
                v, _reverse, capacity = edge
                if capacity and previous[v] is None:
                    previous[v] = (u, edge_index)
                    queue.append(v)
                    if v == target:
                        break
        if previous[target] is None:
            break
        vertex = target
        while vertex != source:
            item = previous[vertex]
            if item is None:
                raise AssertionError("augmenting path predecessor vanished")
            u, edge_index = item
            edge = residual[u][edge_index]
            edge[2] -= 1
            residual[vertex][edge[1]][2] += 1
            vertex = u
        flow += 1
        if flow > inst["cut_size"]:
            return None, {
                "flow": flow,
                "bfs_rounds": bfs_rounds,
                "edge_scans": edge_scans,
                "bit_operations": edge_scans,
            }

    reachable = {source}
    queue = deque([source])
    while queue:
        u = queue.popleft()
        for v, _reverse, capacity in residual[u]:
            edge_scans += 1
            if capacity and v not in reachable:
                reachable.add(v)
                queue.append(v)
    colours = [0 if v in reachable else 1 for v in range(n)]
    answer, fit_stats = _fit_affine(inst, colours)
    operations = edge_scans + fit_stats["bit_operations"]
    return answer, {
        "flow": flow,
        "bfs_rounds": bfs_rounds,
        "edge_scans": edge_scans,
        "pivot_tests": fit_stats["pivot_tests"],
        "row_xors": fit_stats["row_xors"],
        "bit_operations": operations,
    }


def _compact_kernel_route(inst: dict) -> tuple[object | None, dict]:
    d = inst["label_bits"]
    parent = list(range(d))

    def find(bit: int) -> int:
        while parent[bit] != bit:
            parent[bit] = parent[parent[bit]]
            bit = parent[bit]
        return bit

    def union(first: int, second: int) -> None:
        first, second = find(first), find(second)
        if first != second:
            parent[second] = first

    zero_bits: set[int] = set()
    short = 0
    for u, v in inst["edges"]:
        difference = inst["labels"][u] ^ inst["labels"][v]
        weight = difference.bit_count()
        if weight == 1:
            zero_bits.add(difference.bit_length() - 1)
            short += 1
        elif weight == 2:
            bits = [bit for bit in range(d) if (difference >> bit) & 1]
            union(bits[0], bits[1])
            short += 1
    anchored = {find(bit) for bit in zero_bits}
    unanchored = {find(bit) for bit in range(d) if find(bit) not in anchored}
    stats = {
        "edge_label_tests": len(inst["edges"]),
        "short_differences": short,
        "coefficient_decisions": d,
        "operations": len(inst["edges"]) + d,
    }
    if len(unanchored) != 1:
        return None, stats
    root = next(iter(unanchored))
    mask = sum(1 << bit for bit in range(d) if find(bit) == root)
    delta, _pivot = _terminal_pivot(inst)
    if _parity(mask & delta) != 1:
        return None, stats
    return _answer_from_mask(inst, mask), stats


def _spectral_bisection_and_fit(
    inst: dict, iterations: int = 96
) -> tuple[object | None, dict]:
    """Lazy-adjacency power iteration in the all-ones orthogonal subspace."""
    n = inst["n"]
    adjacency = [[] for _ in range(n)]
    for u, v in inst["edges"]:
        adjacency[u].append(v)
        adjacency[v].append(u)
    x = [math.sin((v + 1) * 1.618033988749895) for v in range(n)]
    mean = sum(x) / n
    x = [value - mean for value in x]
    operations = 2 * n
    for _ in range(iterations):
        y = [inst["degree"] * x[v] + sum(x[w] for w in adjacency[v]) for v in range(n)]
        operations += n + 2 * len(inst["edges"])
        mean = sum(y) / n
        y = [value - mean for value in y]
        norm = math.sqrt(sum(value * value for value in y)) or 1.0
        x = [value / norm for value in y]
        operations += 4 * n
    source_sign = x[inst["source"]] >= 0.0
    colours = [int((value >= 0.0) != source_sign) for value in x]
    if colours[inst["target"]] != 1:
        return None, {"iterations": iterations, "operations": operations}
    answer, fit_stats = _fit_affine(inst, colours)
    operations += fit_stats["bit_operations"]
    return answer, {
        "iterations": iterations,
        "operations": operations,
        "pivot_tests": fit_stats["pivot_tests"],
        "row_xors": fit_stats["row_xors"],
    }


def _oriented_mask(inst: dict, preferred: int) -> int:
    delta, pivot = _terminal_pivot(inst)
    mask = preferred & ((1 << inst["label_bits"]) - 1)
    if _parity(mask & delta) != 1:
        mask ^= 1 << pivot
    return mask


def _attack_degree_outlier(inst: dict) -> object:
    degrees = [0] * inst["n"]
    for u, v in inst["edges"]:
        degrees[u] += 1
        degrees[v] += 1
    scores = []
    for bit in range(inst["label_bits"]):
        zero = [degrees[v] for v, label in enumerate(inst["labels"]) if not ((label >> bit) & 1)]
        one = [degrees[v] for v, label in enumerate(inst["labels"]) if (label >> bit) & 1]
        score = abs(sum(zero) * len(one) - sum(one) * len(zero))
        scores.append(score)
    bit = max(range(inst["label_bits"]), key=lambda b: (scores[b], -b))
    return _answer_from_mask(inst, _oriented_mask(inst, 1 << bit))


def _violation_score(inst: dict, mask: int) -> int:
    answer = _answer_from_mask(inst, mask)
    values = _values(inst, mask, answer[-1])
    opposite = [0] * inst["n"]
    for u, v in inst["edges"]:
        if values[u] != values[v]:
            opposite[u] += 1
            opposite[v] += 1
    return sum(max(0, count - inst["d"]) for count in opposite)


def _attack_one_sweep_greedy(inst: dict) -> object:
    starting = _attack_degree_outlier(inst)
    parsed = _mask_from_answer(inst, starting)
    if parsed[0] is None:
        return starting
    mask = parsed[0]
    delta, pivot = _terminal_pivot(inst)
    best_score = _violation_score(inst, mask)
    # One coordinate sweep is a plausible no-tool/local heuristic; it is not
    # the multi-pass kernel recovery route that the benchmark is meant to test.
    for bit in range(inst["label_bits"]):
        if bit == pivot:
            continue
        trial = mask ^ (1 << bit)
        if (delta >> bit) & 1:
            trial ^= 1 << pivot
        score = _violation_score(inst, trial)
        if score < best_score:
            mask, best_score = trial, score
    return _answer_from_mask(inst, mask)


def _attack_sparse_ansatz(inst: dict) -> tuple[object, int]:
    tested = 0
    d = inst["label_bits"]
    for weight in (1, 2):
        for bits in itertools.combinations(range(d), weight):
            mask = sum(1 << bit for bit in bits)
            delta, _pivot = _terminal_pivot(inst)
            if _parity(mask & delta) != 1:
                continue
            tested += 1
            candidate = _answer_from_mask(inst, mask)
            if verify(inst, candidate)[0]:
                return candidate, tested
    return _attack_degree_outlier(inst), tested


def _attack_random_restart(inst: dict, seed: int, restarts: int = 256) -> object:
    rng = random.Random(seed)
    last = random_candidate(inst, rng)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        last = candidate
        if verify(inst, candidate)[0]:
            return candidate
    return last


def _relabel_instance(inst: dict, permutation: list[int]) -> dict:
    n = inst["n"]
    if sorted(permutation) != list(range(n)):
        raise ValueError("not a vertex permutation")
    out = copy.deepcopy(inst)
    labels = [0] * n
    for old, new in enumerate(permutation):
        labels[new] = inst["labels"][old]
    out["labels"] = labels
    out["vertices"] = list(range(n))
    out["edges"] = [[permutation[u], permutation[v]] for u, v in inst["edges"]]
    out["P"] = [permutation[v] for v in inst["P"]]
    out["N"] = [permutation[v] for v in inst["N"]]
    out["source"] = permutation[inst["source"]]
    out["target"] = permutation[inst["target"]]
    return out


def _general_affine_relabel_labels(
    inst: dict, rows: list[int], translation: int
) -> tuple[dict, list[int]]:
    """Apply x -> A*x+t for an invertible binary matrix with given rows."""
    d = inst["label_bits"]
    if len(rows) != d or any(row < 0 or row >= (1 << d) for row in rows):
        raise ValueError("invalid GF(2) change-of-basis matrix")
    # Rank-check the row matrix exactly.
    echelon: dict[int, int] = {}
    for row in rows:
        reduced = row
        for pivot in sorted(echelon, reverse=True):
            if (reduced >> pivot) & 1:
                reduced ^= echelon[pivot]
        if not reduced:
            raise ValueError("change-of-basis matrix is singular")
        echelon[reduced.bit_length() - 1] = reduced

    out = copy.deepcopy(inst)
    out["labels"] = [
        sum(_parity(row & label) << bit for bit, row in enumerate(rows))
        ^ translation
        for label in inst["labels"]
    ]
    parsed = _mask_from_answer(inst, inst["answer"])
    if parsed[0] is None:
        raise AssertionError(parsed[1])
    values = _values(inst, parsed[0], parsed[1])
    new_answer, _stats = _fit_affine(out, values)
    if new_answer is None:
        raise AssertionError("invertible affine relabelling lost the certificate")
    out["answer"] = new_answer
    return out, new_answer


def _random_invertible_rows(dimension: int, rng: random.Random) -> list[int]:
    rows = [1 << bit for bit in range(dimension)]
    for _ in range(4 * dimension):
        first = rng.randrange(dimension)
        second = rng.randrange(dimension - 1)
        if second >= first:
            second += 1
        if rng.randrange(3):
            rows[first] ^= rows[second]
        else:
            rows[first], rows[second] = rows[second], rows[first]
    return rows


def _find_swap_corruption(inst: dict) -> tuple[list[int], str]:
    answer = inst["answer"]
    for i in range(inst["label_bits"]):
        for j in range(i + 1, inst["label_bits"]):
            if answer[i] == answer[j]:
                continue
            corrupted = list(answer)
            corrupted[i], corrupted[j] = corrupted[j], corrupted[i]
            ok, reason = verify(inst, corrupted)
            if not ok and reason not in {
                "coefficient vector is too short",
                "coefficient vector is too long",
                "empty coefficient vector",
                "coefficient outside GF(2)",
            }:
                return corrupted, reason
    raise AssertionError("no rejected coefficient swap was found")


def _count_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_count_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_count_atoms(item) for item in value)
    if isinstance(value, str) and set(value) <= {"0", "1", "|"}:
        return sum(character in "01" for character in value)
    return 1


def _assert_instance_structure(inst: dict) -> None:
    n = inst["n"]
    vertices = list(range(n))
    if inst["vertices"] != vertices:
        raise AssertionError("vertices are not exactly 0 through n-1")
    probes, nonprobes = set(inst["P"]), set(inst["N"])
    if probes & nonprobes or probes | nonprobes != set(vertices):
        raise AssertionError("P and N do not partition the vertices")
    if len(inst["P"]) != len(probes) or len(inst["N"]) != len(nonprobes):
        raise AssertionError("P or N contains a repeated vertex")
    if len(inst["labels"]) != n or len(set(inst["labels"])) != n:
        raise AssertionError("vertex labels are not distinct")
    if any(label < 0 or label >= (1 << inst["label_bits"]) for label in inst["labels"]):
        raise AssertionError("vertex label is outside the declared bit width")

    adjacency = [set() for _ in vertices]
    seen_edges: set[tuple[int, int]] = set()
    for edge in inst["edges"]:
        if not isinstance(edge, list) or len(edge) != 2:
            raise AssertionError("malformed edge")
        u, v = edge
        if not (0 <= u < v < n) or (u, v) in seen_edges:
            raise AssertionError("edge is invalid, reversed, or repeated")
        # P and N are the two bipartition classes.  In particular N is
        # independent; after completing N to a clique, (N,P) is a split
        # partition with clique N and independent set P.
        if (u in probes) == (v in probes):
            raise AssertionError("edge does not cross the declared P/N bipartition")
        seen_edges.add((u, v))
        adjacency[u].add(v)
        adjacency[v].add(u)
    if any(len(neighbours) != inst["degree"] for neighbours in adjacency):
        raise AssertionError("graph is not regular of the declared degree")
    reached = {0}
    queue = deque([0])
    while queue:
        vertex = queue.popleft()
        for neighbour in adjacency[vertex]:
            if neighbour not in reached:
                reached.add(neighbour)
                queue.append(neighbour)
    if len(reached) != n:
        raise AssertionError("graph is disconnected")


def selftest() -> dict:
    report: dict = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    planted_checks = 0
    json_checks = 0
    structure_checks = 0
    answer_independence_checks = 0
    preset_sizes = {}
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            _assert_instance_structure(inst)
            structure_checks += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError(f"G1 {preset}/{seed}: {reason}")
            planted_checks += 1
            public_inst = dict(inst)
            planted_answer = public_inst.pop("answer")
            if not verify(public_inst, planted_answer)[0]:
                raise AssertionError("verify depends on inst['answer']")
            answer_independence_checks += 1
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                raise AssertionError("answer is not JSON-native")
            json_checks += 1
        sample = make_instance(seed=0, **params)
        preset_sizes[preset] = {
            "vertices": sample["n"],
            "edges": len(sample["edges"]),
            "search_space": search_space(sample),
        }
    report["G1_planted_verifies"] = {
        "pass": True,
        "verified": planted_checks,
        "json_round_trips": json_checks,
        "probe_split_structure_checks": structure_checks,
        "answer_independence_checks": answer_independence_checks,
        "preset_sizes": preset_sizes,
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    answer = list(demo["answer"])
    _swapped, swap_reason = _find_swap_corruption(demo)
    corruptions = {
        "drop": verify(demo, answer[:-1])[1],
        "swap": swap_reason,
        "duplicate": verify(demo, answer[:1] + answer)[1],
        "empty": verify(demo, [])[1],
        "out_of_range": verify(demo, [2] + answer[1:])[1],
    }
    if len(set(corruptions.values())) != len(corruptions):
        raise AssertionError(f"G2 reasons are not distinct: {corruptions}")
    report["G2_rejects_corruption"] = {
        "pass": True,
        "reasons": corruptions,
    }

    response = (
        "I used the parity constraints.\n```text\n<answer>\n"
        + " ".join(str(bit) for bit in answer[:-1])
        + " | "
        + str(answer[-1])
        + "\n</answer>\n```\nThat is my final answer."
    )
    recovered = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": recovered == answer and parse_answer("garbage") is None,
        "realistic_response": recovered == answer,
        "garbage_returns_none": parse_answer("garbage") is None,
    }
    if not report["G3_round_trip"]["pass"]:
        raise AssertionError("G3 failed")

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    guess_rng = random.Random(271828)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "structure_aware_space": search_space(shipping),
        "prior": "uniform terminal-oriented affine polynomials over F_2",
    }
    if not report["G4_guess_resistance"]["pass"]:
        raise AssertionError("G4 failed")

    demo_count = enumerate_all(demo)
    start = time.perf_counter()
    reference_answer, reference_stats = _reference_min_cut_and_fit(shipping)
    reference_wall = time.perf_counter() - start
    reference_ok = reference_answer is not None and verify(shipping, reference_answer)[0]
    report["G5_density_and_baseline"] = {
        "pass": demo_count is not None and reference_ok,
        "shipping_density_hits": guess_hits,
        "shipping_density_total": guess_total,
        "baseline_wall_clock_sec": reference_wall,
        "baseline_operations": reference_stats["bit_operations"],
        "shipping_density": {
            "hits": guess_hits,
            "total": guess_total,
            "observed_fraction": guess_rate,
        },
        "exact_demo_valid_answers": demo_count,
        "exact_demo_candidates": search_space(demo),
        "strongest_attack_shipping": {
            "name": "unit-capacity Ford-Fulkerson plus exact GF(2) elimination",
            "wall_clock_sec": reference_wall,
            **reference_stats,
            "verified": reference_ok,
        },
    }
    if not report["G5_density_and_baseline"]["pass"]:
        raise AssertionError("G5 failed")

    attack_results = {
        "equal_degree_outlier": {"successes": 0, "attempts": 8},
        "one_sweep_greedy": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "sparse_affine_ansatz": {"successes": 0, "attempts": 8},
    }
    reference_ops = []
    reference_times = []
    reference_successes = 0
    spectral_ops = []
    spectral_times = []
    spectral_successes = 0
    compact_successes = 0
    sparse_tests = []
    for seed in range(100, 108):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "equal_degree_outlier": _attack_degree_outlier(inst),
            "one_sweep_greedy": _attack_one_sweep_greedy(inst),
            "random_restart_256": _attack_random_restart(inst, seed + 9000),
        }
        sparse_candidate, tested = _attack_sparse_ansatz(inst)
        candidates["sparse_affine_ansatz"] = sparse_candidate
        sparse_tests.append(tested)
        for name, candidate in candidates.items():
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])

        start = time.perf_counter()
        candidate, stats = _reference_min_cut_and_fit(inst)
        reference_times.append(time.perf_counter() - start)
        reference_ops.append(stats["bit_operations"])
        reference_successes += int(candidate is not None and verify(inst, candidate)[0])

        start = time.perf_counter()
        spectral_candidate, spectral_stats = _spectral_bisection_and_fit(inst)
        spectral_times.append(time.perf_counter() - start)
        spectral_ops.append(spectral_stats["operations"])
        spectral_successes += int(
            spectral_candidate is not None and verify(inst, spectral_candidate)[0]
        )

        compact_candidate, _compact_stats = _compact_kernel_route(inst)
        compact_successes += int(
            compact_candidate is not None and verify(inst, compact_candidate)[0]
        )

    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "unit-capacity Ford-Fulkerson plus exact GF(2) elimination",
            "complexity": "O(k(n+m)+n*b^2) exact",
            "wall_clock_sec_median": statistics.median(reference_times),
            "operations_median": int(statistics.median(reference_ops)),
            "solves": f"{reference_successes}/8, as expected",
            "spectral_audit": {
                "name": "lazy-adjacency spectral bisection plus GF(2) fitting",
                "complexity": "O(T(n+m)+n*b^2)",
                "wall_clock_sec_median": statistics.median(spectral_times),
                "operations_median": int(statistics.median(spectral_ops)),
                "solves": f"{spectral_successes}/8, expected on Track B",
            },
        },
        "compact_kernel_route": {"solves": f"{compact_successes}/8"},
        "sparse_masks_tested_range": [min(sparse_tests), max(sparse_tests)],
    }
    if not report["G6_adversary_panel"]["pass"]:
        raise AssertionError(f"G6 failed: {report['G6_adversary_panel']}")

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=23, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    _, ship_stats = _reference_min_cut_and_fit(shipping)
    _, double_stats = _reference_min_cut_and_fit(doubled)
    report["G7_scales"] = {
        "pass": (
            doubled_ok
            and doubled["n"] > shipping["n"]
            and len(doubled["edges"]) > len(shipping["edges"])
            and double_stats["bit_operations"] > ship_stats["bit_operations"]
        ),
        "vertices": [shipping["n"], doubled["n"]],
        "edges": [len(shipping["edges"]), len(doubled["edges"])],
        "reference_operations": [
            ship_stats["bit_operations"],
            double_stats["bit_operations"],
        ],
        "answer_atoms": [_count_atoms(shipping["answer"]), _count_atoms(doubled["answer"])],
    }
    if not report["G7_scales"]["pass"]:
        raise AssertionError("G7 failed")

    invariance_checks = 0
    carried_checks = 0
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(seed=1000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        unrelated_keys.append(key)
        rng = random.Random(seed + 7000)
        vertex_permutation = list(range(inst["n"]))
        rng.shuffle(vertex_permutation)
        change_of_basis = _random_invertible_rows(inst["label_bits"], rng)
        translation = rng.randrange(1 << inst["label_bits"])

        relabelled = _relabel_instance(inst, vertex_permutation)
        rng.shuffle(relabelled["edges"])
        rng.shuffle(relabelled["P"])
        rng.shuffle(relabelled["N"])
        if canonical_key(relabelled) != key:
            raise AssertionError("vertex/input relabelling changed canonical_key")
        invariance_checks += 1
        if not verify(relabelled, inst["answer"])[0]:
            raise AssertionError("vertex relabelling did not carry witness")
        carried_checks += 1

        affine, affine_answer = _general_affine_relabel_labels(
            inst, change_of_basis, translation
        )
        if canonical_key(affine) != key:
            raise AssertionError("coordinate affine relabelling changed canonical_key")
        invariance_checks += 1
        if not verify(affine, affine_answer)[0]:
            raise AssertionError("coordinate affine relabelling did not carry witness")
        carried_checks += 1

        composed = _relabel_instance(affine, vertex_permutation)
        rng.shuffle(composed["edges"])
        if canonical_key(composed) != key:
            raise AssertionError("composed relabellings changed canonical_key")
        invariance_checks += 1
        if not verify(composed, affine_answer)[0]:
            raise AssertionError("composed relabelling did not carry witness")
        carried_checks += 1

        reordered = copy.deepcopy(inst)
        rng.shuffle(reordered["edges"])
        rng.shuffle(reordered["P"])
        rng.shuffle(reordered["N"])
        if canonical_key(reordered) != key:
            raise AssertionError("input reordering changed canonical_key")
        invariance_checks += 1

    report["G8_canonical_key"] = {
        "pass": (
            invariance_checks == 80
            and carried_checks == 60
            and len(set(unrelated_keys)) == 20
        ),
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_distinct": len(set(unrelated_keys)),
        "unrelated_total": 20,
        "symmetries": [
            "vertex relabelling",
            "edge and P/N list reordering",
            "invertible GF(2) change of basis",
            "global label translation",
            "compositions of these maps",
        ],
    }
    if not report["G8_canonical_key"]["pass"]:
        raise AssertionError("G8 failed")

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    compact_answer, compact_stats = _compact_kernel_route(shipping)
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _count_atoms(shipping["answer"])
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and compact_stats["operations"] <= 300
        and compact_answer is not None
        and verify(shipping, compact_answer)[0]
    )
    arms = copy.deepcopy(G9_EVIDENCE["arms"])
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = (
        arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else None
    )
    placebo_rate = (
        arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else None
    )
    difference = (
        hinted_rate - placebo_rate
        if hinted_rate is not None and placebo_rate is not None
        else None
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": difference,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "oracle_status": G9_EVIDENCE["oracle_status"],
        "error_records": copy.deepcopy(G9_EVIDENCE["error_records"]),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact_stats["operations"],
        "caps_only_are_gated": True,
    }
    if not report["G9_no_tool_suitability"]["pass"]:
        raise AssertionError("G9 size/effort caps failed")

    report["all_gates_pass"] = all(
        value.get("pass", True)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    report["all_passed"] = report["all_gates_pass"]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
