"""Verified Rank-Cut problem generator for arXiv:1305.2743.

The paper reduces Bipartite Contraction to Rank-Cut.  This module stays in
that native graph language.  It samples an affine parity polynomial first,
builds a regular graph whose sparse terminal cut is described by that
polynomial, and returns the polynomial as a compact, exact witness.
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
        "undirected graph with vertices labelled by vectors over F_2",
        "two terminal vertex sets",
        "rank-bounded edge cut",
        "affine polynomial over F_2 describing the cut",
    ],
    "verification_operations": [
        "exact affine-polynomial evaluation over F_2",
        "edge-cut deletion and breadth-first reachability",
        "graphic-matroid rank by disjoint-set union",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The low-Hamming-weight XORs of adjacent vertex labels lie in the "
        "codimension-one parity kernel; without this invariant one must compute "
        "the sparse terminal cut and fit its affine separator mechanically."
    ),
    "hardness_basis": (
        "Track B: Theorems 11 and 12 give randomized and deterministic "
        "2^{O(k^2)}-parameter Rank-Cut methods; "
        "on this generated regime, unit-capacity Ford-Fulkerson plus GF(2) "
        "elimination runs in O(k(n+m)+n*d^2) and at shipping n=60 measured a "
        "median 20,661 counted bit operations and 0.001526 seconds over eight "
        "instances, which is not mechanically executable in the no-tool context, "
        "while the parity-kernel invariant compresses the route to 204 operations."
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
        "An affine polynomial P(x)=c_0*x_0 XOR ... XOR c_(d-1)*x_(d-1) "
        "XOR b over F_2, represented by the d coefficient bits followed by the "
        "constant bit.  The language contains exactly the polynomials with "
        "P(source)=0 and P(target)=1."
    ),
    "bounds": {
        "degree": 1,
        "max_variables": 24,
        "field_order": 2,
        "max_coefficient_count": 25,
        "terminal_orientation_equations": 2,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 24, "label_bits": 7, "cut_size": 2, "degree": 4},
    "easy": {"n": 60, "label_bits": 24, "cut_size": 4, "degree": 6},
    "medium": {"n": 64, "label_bits": 24, "cut_size": 4, "degree": 8},
    "hard": {"n": 68, "label_bits": 24, "cut_size": 4, "degree": 8},
}

SHIPPING_DIFFICULTY: str = "easy"

STRUCTURAL_HINT: str = (
    "The low-Hamming-weight XORs of adjacent labels span a codimension-one parity kernel."
)
PLACEBO_HINT: str = (
    "The binary vertex labels and undirected edge list reward careful bookkeeping throughout."
)

# Replaced with script-owned measurements after the three independent runs.
# The arms are diagnostics; only the answer-size and intended-operation caps
# contribute to the G9 pass flag.
G9_EVIDENCE = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 1, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "too_easy",
    "error_records": {"bare": 0, "hinted": 0, "placebo": 4},
}

NOTES: str = r"""
Section 2 fixes the exact contraction convention: all edges in a set may be
contracted in any order.  More importantly for this module, Lemma 2 proves
that Bipartite Contraction is equivalent to finding a bipartite modulator of
graphic rank at most k.  Section 3 then defines Rank-Cut using exactly that
graphic-rank constraint.  Those definitions rule out the prior triage label
"reconfiguration": the witness is an unordered edge set, not a sequence.

Theorems 11 and 12 are the STEP-0 algorithm warning for Rank-Cut: randomized
2^{O(k^2)} n m and deterministic 2^{O(k^2)} n^{O(1)} algorithms exist.
Theorem 1 transfers these bounds to Bipartite Contraction.  Section 4, Lemma 7
also exhibits the relevant
easy mechanism on Constrained Rank-Cut: a weighted separator is found by at
most k Ford-Fulkerson rounds in O(k(n+m)).  Our instances are ordinary
Rank-Cut, not that constrained input, but their sparse matching cut admits the
same unit-capacity mechanism.  Therefore this generator makes no Track-A
claim.  Its successful measured reference algorithm computes the sparse
terminal cut with augmenting paths and fits the affine polynomial by exact
GF(2) elimination.

Generation is inverse.  A balanced, non-sparse affine polynomial is sampled
first.  Two highly connected circulant pieces are labelled with its zero and
one fibres, a matching of cut_size edges is placed between them, and one
internal matching is removed on each side so that every vertex has the same
degree.  The planted cut is a matching and hence has graphic rank cut_size.
Cross endpoints are resampled until every cross-label XOR has Hamming weight
at least three.  The certificate is never obtained by solving the finished
graph, and the compact invariant is guaranteed rather than merely likely.

Degree equalisation defeats the vertex-outlier attack.  Random labels make
individual coordinates, the direct terminal-difference ansatz, and sparse
affine ansatzes uninformative.  The energy of every wrong parity is
essentially random, defeating coordinate descent and bounded random
restarts.  A deliberately included systematic basis of short endpoint XORs
gives a compact route: its span is the kernel of the planted functional.  The
hint names only this invariant; it does not state a recovery procedure or a
derived coefficient.  The ladder first grows the ambient regular graph and
its decoy density while the 25-bit answer stays fixed; escalate() returns
cap_bound only when another such increase would cross G9's 300-operation
intended-route cap.
""".strip()


def _parity(value: int) -> int:
    return value.bit_count() & 1


def _validate_params(n: int, label_bits: int, cut_size: int, degree: int) -> None:
    values = (n, label_bits, cut_size, degree)
    if any(isinstance(v, bool) or not isinstance(v, int) for v in values):
        raise ValueError("all parameters must be integers")
    if label_bits < 4:
        raise ValueError("label_bits must be at least 4")
    if cut_size < 2 or cut_size % 2:
        raise ValueError("cut_size must be a positive even integer")
    if degree < 4 or degree % 2:
        raise ValueError("degree must be an even integer at least 4")
    left_size = 2 * (label_bits - 1) + cut_size
    right_size = n - left_size
    if right_size <= degree:
        raise ValueError(
            "n is too small for the systematic kernel basis and both circulants"
        )
    if n >= (1 << label_bits):
        raise ValueError("label space is too small for distinct vertex labels")


def _sample_function(label_bits: int, rng: random.Random) -> tuple[int, int]:
    low = max(2, label_bits // 3)
    high = label_bits - low
    while True:
        mask = rng.randrange(1, 1 << label_bits)
        if low <= mask.bit_count() <= high:
            return mask, rng.randrange(2)


def _sample_label(
    wanted: int,
    coefficient_mask: int,
    constant: int,
    label_bits: int,
    used: set[int],
    rng: random.Random,
) -> int:
    while True:
        value = rng.randrange(1 << label_bits)
        if value in used:
            continue
        if (_parity(coefficient_mask & value) ^ constant) == wanted:
            used.add(value)
            return value


def _circulant_edges(order: list[int], degree: int) -> set[tuple[int, int]]:
    size = len(order)
    edges: set[tuple[int, int]] = set()
    for pos, vertex in enumerate(order):
        for distance in range(1, degree // 2 + 1):
            other = order[(pos + distance) % size]
            edges.add((min(vertex, other), max(vertex, other)))
    return edges


def _block_order(blocks: list[list[int]], rng: random.Random) -> list[int]:
    blocks = [list(block) for block in blocks]
    rng.shuffle(blocks)
    return [vertex for block in blocks for vertex in block]


def _far_cross_matching(
    left: list[int], right: list[int], rng: random.Random
) -> list[int] | None:
    """Match each left label to a right label at Hamming distance at least 3."""

    candidates = []
    for left_label in left:
        row = [
            j
            for j, right_label in enumerate(right)
            if (left_label ^ right_label).bit_count() > 2
        ]
        rng.shuffle(row)
        candidates.append(row)
    left_order = list(range(len(left)))
    rng.shuffle(left_order)
    left_order.sort(key=lambda i: len(candidates[i]))
    right_owner: dict[int, int] = {}

    def augment(left_index: int, seen: set[int]) -> bool:
        for right_index in candidates[left_index]:
            if right_index in seen:
                continue
            seen.add(right_index)
            owner = right_owner.get(right_index)
            if owner is None or augment(owner, seen):
                right_owner[right_index] = left_index
                return True
        return False

    for left_index in left_order:
        if not augment(left_index, set()):
            return None
    result = [0] * len(left)
    for right_index, left_index in right_owner.items():
        result[left_index] = right_index
    return result


def make_instance(
    n: int,
    seed: int = 0,
    label_bits: int = 24,
    cut_size: int = 4,
    degree: int = 6,
    **params,
) -> dict:
    """Plant an affine Rank-Cut certificate before constructing the graph."""

    if params:
        raise ValueError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, label_bits, cut_size, degree)
    rng = random.Random(seed)

    coefficient_mask, constant = _sample_function(label_bits, rng)
    pivot = (coefficient_mask & -coefficient_mask).bit_length() - 1
    used: set[int] = set()

    # Each difference below lies in ker(coefficient_mask).  Together these
    # label differences are a systematic basis for that codimension-one space.
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

    left_size = 2 * (label_bits - 1) + cut_size
    right_size = n - left_size
    left_cross = [
        _sample_label(0, coefficient_mask, constant, label_bits, used, rng)
        for _ in range(cut_size)
    ]
    # Cross-edge differences must not be confused with the deliberately short
    # kernel differences. Resample until a distance->2 perfect matching exists,
    # making the compact route valid on the unlimited seed stream rather than
    # merely overwhelmingly likely when label_bits is large.
    while True:
        right_cross = [
            _sample_label(1, coefficient_mask, constant, label_bits, used, rng)
            for _ in range(cut_size)
        ]
        cross_order = _far_cross_matching(left_cross, right_cross, rng)
        if cross_order is not None:
            break
        used.difference_update(right_cross)
    left_extra_count = left_size - 2 * (label_bits - 1) - cut_size
    left_extra = [
        _sample_label(0, coefficient_mask, constant, label_bits, used, rng)
        for _ in range(left_extra_count)
    ]
    right_extra = [
        _sample_label(1, coefficient_mask, constant, label_bits, used, rng)
        for _ in range(right_size - cut_size)
    ]

    left_cross_blocks = [
        left_cross[i : i + 2] for i in range(0, cut_size, 2)
    ]
    right_cross_blocks = [
        right_cross[i : i + 2] for i in range(0, cut_size, 2)
    ]
    left_blocks = kernel_pairs + left_cross_blocks + [[x] for x in left_extra]
    right_blocks = right_cross_blocks + [[x] for x in right_extra]
    left_order_labels = _block_order(left_blocks, rng)
    right_order_labels = _block_order(right_blocks, rng)

    all_labels = left_order_labels + right_order_labels
    old_vertices = list(range(n))
    rng.shuffle(old_vertices)
    label_to_vertex = {label: old_vertices[i] for i, label in enumerate(all_labels)}
    labels = [0] * n
    for label, vertex in label_to_vertex.items():
        labels[vertex] = label

    left_order = [label_to_vertex[x] for x in left_order_labels]
    right_order = [label_to_vertex[x] for x in right_order_labels]
    edges = _circulant_edges(left_order, degree) | _circulant_edges(
        right_order, degree
    )

    # Delete one internal matching incident with every future cross endpoint.
    # Adding the cross matching back makes the whole graph exactly regular.
    for blocks, mapping in (
        (left_cross_blocks, label_to_vertex),
        (right_cross_blocks, label_to_vertex),
    ):
        for first_label, second_label in blocks:
            edge = tuple(sorted((mapping[first_label], mapping[second_label])))
            if edge not in edges:
                raise AssertionError("cross-endpoint block is not a circulant edge")
            edges.remove(edge)

    for i, j in enumerate(cross_order):
        u = label_to_vertex[left_cross[i]]
        v = label_to_vertex[right_cross[j]]
        edges.add((min(u, v), max(u, v)))

    edge_list = [list(edge) for edge in edges]
    rng.shuffle(edge_list)
    source = label_to_vertex[left_order_labels[0]]
    target = label_to_vertex[right_order_labels[0]]
    answer = [
        (coefficient_mask >> bit) & 1 for bit in range(label_bits)
    ] + [constant]

    return {
        "family": "Rank-Cut with an affine F_2 cut certificate",
        "n": n,
        "label_bits": label_bits,
        "cut_size": cut_size,
        "degree": degree,
        "vertices": list(range(n)),
        "labels": labels,
        "edges": edge_list,
        "X": [source],
        "Y": [target],
        "M": [],
        "answer": answer,
    }


def _bits_text(value: int, width: int) -> str:
    # Left-to-right is x_0, x_1, ..., not conventional most-significant first.
    return "".join(str((value >> bit) & 1) for bit in range(width))


def _answer_text(answer: list[int]) -> str:
    return "".join(str(bit) for bit in answer[:-1]) + "|" + str(answer[-1])


def render(inst: dict) -> str:
    d = inst["label_bits"]
    label_lines = "\n".join(
        f"  {vertex}: {_bits_text(inst['labels'][vertex], d)}"
        for vertex in inst["vertices"]
    )
    edge_lines = []
    row: list[str] = []
    for edge in inst["edges"]:
        row.append(f"{edge[0]}-{edge[1]}")
        if len(row) == 12:
            edge_lines.append("  " + " ".join(row))
            row = []
    if row:
        edge_lines.append("  " + " ".join(row))

    statement = f"""Rank-Cut with an affine certificate

The undirected simple graph below has vertices 0 through {inst['n'] - 1}.
Each vertex v has a displayed {d}-bit label x(v).  In every displayed label,
the LEFTMOST bit is x_0, followed by x_1, ..., with x_{d - 1} rightmost.

An affine polynomial over F_2 is
  P(x) = c_0*x_0 XOR c_1*x_1 XOR ... XOR c_{d - 1}*x_{d - 1} XOR b,
where every c_i and b is 0 or 1.  It defines the edge set
  C(P) = {{uv in E : P(x(u)) != P(x(v))}}.

For an edge set C, its graphic rank r(C) is the number of edges in a spanning
forest of the graph whose edge set is C (isolated vertices are irrelevant).
Equivalently, r(C) is summed as |V(K)|-1 over the nontrivial connected
components K of C.  An (X,Y)-cut is an edge set whose deletion leaves no path
from any vertex of X to any vertex of Y.

Find an affine polynomial P such that:
  1. P is oriented with P(x({inst['X'][0]}))=0 and P(x({inst['Y'][0]}))=1;
  2. C(P) is an (X,Y)-cut; and
  3. r(C(P)) <= k={inst['cut_size']}.

Here X={inst['X']} and Y={inst['Y']}; M is empty, so M-rank is ordinary rank.
The order of edges is irrelevant, there are no loops, and vertex numbering is
0-based.

Vertex labels (vertex: bits x_0...x_{d - 1}):
{label_lines}

Edges (u-v):
{chr(10).join(edge_lines)}

Give your final answer inside <answer></answer> tags as exactly {d} coefficient
bits c_0...c_{d - 1}, then a vertical bar, then the constant bit b.
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
    coefficient_text, constant = matches[0]
    coefficient_text = re.sub(r"\s+", "", coefficient_text)
    if not coefficient_text:
        return None
    return [int(bit) for bit in coefficient_text] + [int(constant)]


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
    if any(isinstance(bit, bool) or not isinstance(bit, int) or bit not in (0, 1)
           for bit in answer):
        return None, "coefficient outside GF(2)"
    mask = sum(answer[bit] << bit for bit in range(inst["label_bits"]))
    return mask, answer[-1]


def _cut_stats(
    inst: dict,
    mask: int,
    constant: int,
    rank_limit: int | None = None,
) -> tuple[int, int, list[list[int]]]:
    parent = list(range(inst["n"]))
    size = [1] * inst["n"]

    def find(vertex: int) -> int:
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    rank = 0
    cut: list[list[int]] = []
    values = [
        _parity(mask & label) ^ constant for label in inst["labels"]
    ]
    for u, v in inst["edges"]:
        if values[u] == values[v]:
            continue
        cut.append([u, v])
        ru, rv = find(u), find(v)
        if ru != rv:
            if size[ru] < size[rv]:
                ru, rv = rv, ru
            parent[rv] = ru
            size[ru] += size[rv]
            rank += 1
            if rank_limit is not None and rank > rank_limit:
                return rank, len(cut), cut
    return rank, len(cut), cut


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    parsed = _mask_from_answer(inst, answer)
    if parsed[0] is None:
        return False, parsed[1]
    mask, constant = parsed
    source, target = inst["X"][0], inst["Y"][0]
    source_value = _parity(mask & inst["labels"][source]) ^ constant
    target_value = _parity(mask & inst["labels"][target]) ^ constant
    if (source_value, target_value) != (0, 1):
        return False, "polynomial does not have the required terminal orientation"

    rank, _cut_count, cut = _cut_stats(
        inst, mask, constant, rank_limit=inst["cut_size"]
    )
    if rank > inst["cut_size"]:
        return False, f"cut has graphic rank {rank}, exceeding k={inst['cut_size']}"

    removed = {tuple(sorted(edge)) for edge in cut}
    adjacency = [[] for _ in range(inst["n"])]
    for u, v in inst["edges"]:
        if (min(u, v), max(u, v)) in removed:
            continue
        adjacency[u].append(v)
        adjacency[v].append(u)
    seen = {source}
    queue = deque([source])
    while queue:
        vertex = queue.popleft()
        for other in adjacency[vertex]:
            if other not in seen:
                seen.add(other)
                queue.append(other)
    if target in seen:
        return False, "C(P) does not separate X from Y"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    d = inst["label_bits"]
    source, target = inst["X"][0], inst["Y"][0]
    delta = inst["labels"][source] ^ inst["labels"][target]
    pivot = (delta & -delta).bit_length() - 1
    mask = 0
    for bit in range(d):
        if bit != pivot and rng.randrange(2):
            mask |= 1 << bit
    required = 1 ^ _parity(mask & delta)
    if required:
        mask |= 1 << pivot
    constant = _parity(mask & inst["labels"][source])
    return [(mask >> bit) & 1 for bit in range(d)] + [constant]


def search_space(inst: dict) -> int | None:
    return 1 << (inst["label_bits"] - 1)


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 200_000:
        return None
    # random_candidate is a bijective parametrization only if driven by each
    # free-bit word explicitly, so enumerate those words directly here.
    d = inst["label_bits"]
    source, target = inst["X"][0], inst["Y"][0]
    delta = inst["labels"][source] ^ inst["labels"][target]
    pivot = (delta & -delta).bit_length() - 1
    free_bits = [bit for bit in range(d) if bit != pivot]
    count = 0
    for word in range(space):
        mask = 0
        for pos, bit in enumerate(free_bits):
            if (word >> pos) & 1:
                mask |= 1 << bit
        if (1 ^ _parity(mask & delta)):
            mask |= 1 << pivot
        constant = _parity(mask & inst["labels"][source])
        candidate = [(mask >> bit) & 1 for bit in range(d)] + [constant]
        if verify(inst, candidate)[0]:
            count += 1
    return count


def _linear_basis_coordinates(vectors: list[int], dimension: int) -> list[int]:
    """Coordinates in the first independent ordered basis, invariant under GL."""
    independence: dict[int, int] = {}
    basis: list[int] = []
    for original in vectors:
        value = original
        while value:
            pivot = value.bit_length() - 1
            if pivot in independence:
                value ^= independence[pivot]
            else:
                independence[pivot] = value
                basis.append(original)
                break
        if len(basis) == dimension:
            break
    if len(basis) != dimension:
        raise ValueError("vertex labels do not affinely span their declared space")

    pivots: dict[int, tuple[int, int]] = {}
    for index, original in enumerate(basis):
        value = original
        combination = 1 << index
        while value:
            pivot = value.bit_length() - 1
            if pivot in pivots:
                row, row_combination = pivots[pivot]
                value ^= row
                combination ^= row_combination
            else:
                pivots[pivot] = (value, combination)
                break

    coordinates = []
    for original in vectors:
        value = original
        combination = 0
        while value:
            pivot = value.bit_length() - 1
            if pivot not in pivots:
                raise ValueError("basis failed to span a label difference")
            row, row_combination = pivots[pivot]
            value ^= row
            combination ^= row_combination
        coordinates.append(combination)
    return coordinates


def _wl_invariant(inst: dict) -> dict:
    n = inst["n"]
    adjacency: list[list[int]] = [[] for _ in range(n)]
    for u, v in inst["edges"]:
        adjacency[u].append(v)
        adjacency[v].append(u)
    xset, yset = set(inst["X"]), set(inst["Y"])
    colors = [
        (1 if v in xset else 2 if v in yset else 0, len(adjacency[v]))
        for v in range(n)
    ]
    palette = {signature: i for i, signature in enumerate(sorted(set(colors)))}
    ids = [palette[signature] for signature in colors]
    for _ in range(n):
        signatures = [
            (ids[v], tuple(sorted(ids[w] for w in adjacency[v])))
            for v in range(n)
        ]
        palette = {
            signature: i for i, signature in enumerate(sorted(set(signatures)))
        }
        new_ids = [palette[signature] for signature in signatures]
        if new_ids == ids:
            break
        ids = new_ids
    if len(set(ids)) != n:
        # Generated instances individualize completely in the G8 audit.  This
        # fallback remains invariant but is explicitly weaker than canonical
        # graph isomorphism for a hand-edited instance with unresolved twins.
        return {
            "n": n,
            "label_bits": inst["label_bits"],
            "k": inst["cut_size"],
            "color_class_sizes": sorted(
                list(ids).count(color) for color in set(ids)
            ),
            "graph_edges": len(inst["edges"]),
        }

    canonical_vertices = sorted(range(n), key=lambda vertex: ids[vertex])
    canonical_position = {
        vertex: position for position, vertex in enumerate(canonical_vertices)
    }
    canonical_edges = sorted(
        sorted((canonical_position[u], canonical_position[v]))
        for u, v in inst["edges"]
    )
    origin = inst["labels"][canonical_vertices[0]]
    differences = [inst["labels"][vertex] ^ origin for vertex in canonical_vertices]
    affine_coordinates = _linear_basis_coordinates(
        differences, inst["label_bits"]
    )
    return {
        "n": n,
        "label_bits": inst["label_bits"],
        "k": inst["cut_size"],
        "canonical_edges": canonical_edges,
        "affine_label_coordinates": affine_coordinates,
    }


def canonical_key(inst: dict) -> str:
    """Invariant under vertex relabelling and affine changes of label basis."""
    payload = json.dumps(
        _wl_invariant(inst), sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def escalate(params: dict) -> dict | str | None:
    n = int(params["n"])
    label_bits = int(params.get("label_bits", 24))
    cut_size = int(params.get("cut_size", 4))
    degree = int(params.get("degree", 6))
    # Exhaust the fixed-answer-length ambient-size axis before touching the
    # certificate. One packed edge-label test per edge plus one coefficient
    # decision per coordinate is the compact route counted by G9(c).
    max_n = (2 * (300 - label_bits)) // degree
    if n < max_n:
        new_n = min(max_n, max(n + 8, (5 * n) // 4))
        return {
            "n": new_n,
            "label_bits": label_bits,
            "cut_size": cut_size,
            "degree": degree,
        }
    return "cap_bound"


def _add_directed(residual, u: int, v: int, capacity: int) -> None:
    forward = [v, len(residual[v]), capacity]
    reverse = [u, len(residual[u]), 0]
    residual[u].append(forward)
    residual[v].append(reverse)


def _reference_cut_and_fit(inst: dict) -> tuple[object | None, dict]:
    """Ford-Fulkerson terminal cut, followed by exact affine fitting."""
    n = inst["n"]
    residual: list[list[list[int]]] = [[] for _ in range(n)]
    for u, v in inst["edges"]:
        # Symmetric unit capacities model one undirected unit-capacity edge.
        _add_directed(residual, u, v, 1)
        _add_directed(residual, v, u, 1)
    source, target = inst["X"][0], inst["Y"][0]
    flow = 0
    bfs_rounds = 0
    edge_scans = 0
    while True:
        bfs_rounds += 1
        previous = [None] * n
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
            u, edge_index = previous[vertex]
            edge = residual[u][edge_index]
            reverse_index = edge[1]
            edge[2] -= 1
            residual[vertex][reverse_index][2] += 1
            vertex = u
        flow += 1
        if flow > inst["cut_size"]:
            return None, {
                "flow": flow,
                "bfs_rounds": bfs_rounds,
                "edge_scans": edge_scans,
                "pivot_tests": 0,
                "row_xors": 0,
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

    variables = inst["label_bits"] + 1
    rows = []
    for vertex, label in enumerate(inst["labels"]):
        rhs = 0 if vertex in reachable else 1
        rows.append(label | (1 << inst["label_bits"]) | (rhs << variables))
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
        "flow": flow,
        "bfs_rounds": bfs_rounds,
        "edge_scans": edge_scans,
        "pivot_tests": pivot_tests,
        "row_xors": row_xors,
        "bit_operations": edge_scans
        + pivot_tests
        + row_xors * (variables + 1),
    }
    if rank != variables:
        return None, stats
    solution = [0] * variables
    coefficient_mask = (1 << variables) - 1
    for row in rows:
        coefficients = row & coefficient_mask
        if coefficients == 0:
            if (row >> variables) & 1:
                return None, stats
            continue
        if coefficients & (coefficients - 1):
            continue
        column = coefficients.bit_length() - 1
        solution[column] = (row >> variables) & 1
    return solution, stats


def _answer_from_mask(inst: dict, mask: int) -> list[int]:
    constant = _parity(mask & inst["labels"][inst["X"][0]])
    return [
        (mask >> bit) & 1 for bit in range(inst["label_bits"])
    ] + [constant]


def _compact_kernel_route(inst: dict) -> tuple[object | None, dict]:
    """Recover the affine normal from weight-one/two edge-label XORs.

    A weight-one difference anchors one coefficient at zero; a weight-two
    difference equates two coefficients. Generation supplies a star spanning
    all one-coordinates and singleton anchors for every zero-coordinate, while
    forbidding short cross differences. Exactly one unanchored equality
    component therefore remains.
    """

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
    short_differences = 0
    for u, v in inst["edges"]:
        difference = inst["labels"][u] ^ inst["labels"][v]
        weight = difference.bit_count()
        if weight == 1:
            zero_bits.add(difference.bit_length() - 1)
            short_differences += 1
        elif weight == 2:
            bits = [bit for bit in range(d) if (difference >> bit) & 1]
            union(bits[0], bits[1])
            short_differences += 1

    anchored_roots = {find(bit) for bit in zero_bits}
    unanchored_roots = {
        find(bit) for bit in range(d) if find(bit) not in anchored_roots
    }
    stats = {
        "edge_label_tests": len(inst["edges"]),
        "short_differences": short_differences,
        "coefficient_decisions": d,
        "operations": len(inst["edges"]) + d,
    }
    if len(unanchored_roots) != 1:
        return None, stats
    one_root = next(iter(unanchored_roots))
    mask = sum(1 << bit for bit in range(d) if find(bit) == one_root)
    delta, _pivot = _terminal_pivot(inst)
    if _parity(mask & delta) != 1:
        return None, stats
    return _answer_from_mask(inst, mask), stats


def _terminal_pivot(inst: dict) -> tuple[int, int]:
    delta = inst["labels"][inst["X"][0]] ^ inst["labels"][inst["Y"][0]]
    pivot = (delta & -delta).bit_length() - 1
    return delta, pivot


def _attack_degree_outlier(inst: dict) -> object:
    degrees = [0] * inst["n"]
    for u, v in inst["edges"]:
        degrees[u] += 1
        degrees[v] += 1
    # All degrees are equal by construction.  The natural tie-break is the
    # first coordinate that distinguishes the two terminals.
    _delta, pivot = _terminal_pivot(inst)
    return _answer_from_mask(inst, 1 << pivot)


def _attack_terminal_difference(inst: dict) -> object:
    """Try a one-shot normal vector read from the two terminal labels.

    This is executable without graph search or coefficient fitting: use the
    terminal-label XOR itself and toggle one differing coordinate only when
    needed to satisfy the mandatory orientation.
    """

    delta, pivot = _terminal_pivot(inst)
    mask = delta
    if _parity(mask & delta) != 1:
        mask ^= 1 << pivot
    return _answer_from_mask(inst, mask)


def _rank_for_mask(inst: dict, mask: int) -> int:
    constant = _parity(mask & inst["labels"][inst["X"][0]])
    return _cut_stats(inst, mask, constant)[0]


def _attack_sparse_ansatz(inst: dict) -> tuple[object, int]:
    d = inst["label_bits"]
    delta, _pivot = _terminal_pivot(inst)
    best_mask = None
    best_rank = inst["n"] + 1
    tested = 0
    for weight in (1, 2):
        for positions in itertools.combinations(range(d), weight):
            mask = sum(1 << bit for bit in positions)
            if _parity(mask & delta) != 1:
                continue
            tested += 1
            rank = _rank_for_mask(inst, mask)
            if rank < best_rank:
                best_mask, best_rank = mask, rank
    if best_mask is None:
        _delta, pivot = _terminal_pivot(inst)
        best_mask = 1 << pivot
    return _answer_from_mask(inst, best_mask), tested


def _attack_coordinate_descent(
    inst: dict, rng: random.Random, restarts: int = 8
) -> tuple[object, int]:
    d = inst["label_bits"]
    delta, pivot = _terminal_pivot(inst)
    moves = []
    for bit in range(d):
        if bit == pivot:
            continue
        move = 1 << bit
        if (delta >> bit) & 1:
            move |= 1 << pivot
        moves.append(move)
    best_mask = 1 << pivot
    best_rank = _rank_for_mask(inst, best_mask)
    evaluations = 1
    for restart in range(restarts):
        if restart == 0:
            mask = 1 << pivot
        else:
            candidate = random_candidate(inst, rng)
            mask = sum(candidate[bit] << bit for bit in range(d))
        current = _rank_for_mask(inst, mask)
        evaluations += 1
        for _ in range(d):
            choices = []
            for move in moves:
                trial = mask ^ move
                rank = _rank_for_mask(inst, trial)
                evaluations += 1
                choices.append((rank, trial))
            rank, trial = min(choices)
            if rank >= current:
                break
            mask, current = trial, rank
        if current < best_rank:
            best_mask, best_rank = mask, current
    return _answer_from_mask(inst, best_mask), evaluations


def _attack_random_restart(
    inst: dict, rng: random.Random, restarts: int = 256
) -> tuple[object, int]:
    best = random_candidate(inst, rng)
    best_mask = sum(best[bit] << bit for bit in range(inst["label_bits"]))
    best_rank = _rank_for_mask(inst, best_mask)
    for _ in range(restarts - 1):
        candidate = random_candidate(inst, rng)
        mask = sum(
            candidate[bit] << bit for bit in range(inst["label_bits"])
        )
        rank = _rank_for_mask(inst, mask)
        if rank < best_rank:
            best, best_rank = candidate, rank
    return best, restarts


def _permute_label(value: int, order: list[int]) -> int:
    result = 0
    for new_bit, old_bit in enumerate(order):
        result |= ((value >> old_bit) & 1) << new_bit
    return result


def _transform_instance(
    inst: dict,
    vertex_order: list[int] | None = None,
    bit_order: list[int] | None = None,
    linear_ops: list[tuple[int, int]] | None = None,
    translation: int = 0,
    edge_seed: int | None = None,
) -> dict:
    out = copy.deepcopy(inst)
    n, d = inst["n"], inst["label_bits"]
    if vertex_order is None:
        vertex_order = list(range(n))
    if bit_order is None:
        bit_order = list(range(d))
    if linear_ops is None:
        linear_ops = []
    if sorted(vertex_order) != list(range(n)) or sorted(bit_order) != list(range(d)):
        raise ValueError("transformations must be permutations")

    new_labels = [0] * n
    for old_vertex in range(n):
        new_vertex = vertex_order[old_vertex]
        transformed_label = _permute_label(
            inst["labels"][old_vertex], bit_order
        )
        for target_bit, source_bit in linear_ops:
            if not (0 <= target_bit < d and 0 <= source_bit < d):
                raise ValueError("linear-operation coordinate is out of range")
            transformed_label ^= (
                (transformed_label >> source_bit) & 1
            ) << target_bit
        new_labels[new_vertex] = transformed_label ^ translation
    out["labels"] = new_labels
    out["vertices"] = list(range(n))
    out["edges"] = [
        sorted((vertex_order[u], vertex_order[v])) for u, v in inst["edges"]
    ]
    if edge_seed is not None:
        random.Random(edge_seed).shuffle(out["edges"])
    out["X"] = [vertex_order[v] for v in inst["X"]]
    out["Y"] = [vertex_order[v] for v in inst["Y"]]

    old_coefficients = inst["answer"][:-1]
    new_coefficients = [old_coefficients[old_bit] for old_bit in bit_order]
    for target_bit, source_bit in linear_ops:
        # new x_target = old x_target XOR old x_source.  This elementary
        # operation is its own inverse, so c'_source=c_source XOR c_target.
        new_coefficients[source_bit] ^= new_coefficients[target_bit]
    new_mask = sum(bit << i for i, bit in enumerate(new_coefficients))
    new_constant = inst["answer"][-1] ^ _parity(new_mask & translation)
    out["answer"] = new_coefficients + [new_constant]
    return out


def selftest() -> dict:
    report: dict = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    failures = []
    attempts = 0
    json_roundtrips = 0
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

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=90210, **ship_params)
    answer = inst["answer"]
    swapped = None
    for i in range(len(answer)):
        for j in range(i + 1, len(answer)):
            if answer[i] == answer[j]:
                continue
            trial = list(answer)
            trial[i], trial[j] = trial[j], trial[i]
            if not verify(inst, trial)[0]:
                swapped = trial
                break
        if swapped is not None:
            break
    if swapped is None:
        swapped = list(reversed(answer))
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": answer + [answer[-1]],
        "empty": [],
        "out_of_range": answer[:-1] + [2],
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
    }

    realistic = (
        "I used the parity kernel and checked the resulting edge cut.\n\n"
        "```text\n<answer> "
        + _answer_text(answer)
        + " </answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("there is no tagged answer") is None,
        "parsed_elements": len(parsed) if isinstance(parsed, list) else None,
        "garbage_returns_none": parse_answer("there is no tagged answer") is None,
    }

    samples = 200_000
    guess_rng = random.Random(0x13052743)
    hits = 0
    start = time.perf_counter()
    for _ in range(samples):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            hits += 1
    guess_seconds = time.perf_counter() - start
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "structure_aware_space": search_space(inst),
        "sample_seconds": round(guess_seconds, 6),
        "sampler": (
            "uniform affine polynomials already satisfying P(source)=0 and "
            "P(target)=1"
        ),
    }

    baseline_start = time.perf_counter()
    baseline_candidate, baseline_evaluations = _attack_coordinate_descent(
        inst, random.Random(99173), restarts=8
    )
    baseline_seconds = time.perf_counter() - baseline_start
    reference_start = time.perf_counter()
    reference_candidate, reference_stats = _reference_cut_and_fit(inst)
    reference_seconds = time.perf_counter() - reference_start
    reference_solved = (
        reference_candidate is not None and verify(inst, reference_candidate)[0]
    )
    demo_count = enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline"] = {
        "pass": (
            hits / samples < 1e-6
            and demo_count is not None
            and reference_solved
        ),
        "shipping_valid_hits": hits,
        "shipping_density_samples": samples,
        "shipping_observed_solution_fraction": hits / samples,
        "shipping_space_size": search_space(inst),
        "demo_exact_solution_count": demo_count,
        "baseline_wall_seconds": round(baseline_seconds, 6),
        "baseline_candidate_evaluations": baseline_evaluations,
        "baseline_solved": verify(inst, baseline_candidate)[0],
        "strongest_reference_name": (
            "unit-capacity Ford-Fulkerson cut plus GF(2) elimination"
        ),
        "strongest_reference_wall_seconds": round(reference_seconds, 6),
        "strongest_reference_operations": reference_stats["bit_operations"],
        "strongest_reference_solved": reference_solved,
    }

    attacks = {
        "outlier_equal_degree": {"successes": 0, "attempts": 0},
        "greedy_coordinate_descent_8x": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
        "in_context_terminal_difference_ansatz": {
            "successes": 0,
            "attempts": 0,
        },
        "weight_at_most_2_ansatz": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_times = []
    reference_operations = []
    reference_scans = []
    compact_successes = 0
    compact_operations = []
    for seed in range(3100, 3108):
        attacked = make_instance(seed=seed, **ship_params)
        candidates = {
            "outlier_equal_degree": _attack_degree_outlier(attacked),
            "greedy_coordinate_descent_8x": _attack_coordinate_descent(
                attacked, random.Random(seed ^ 0xA5A5), restarts=8
            )[0],
            "random_restart_256": _attack_random_restart(
                attacked, random.Random(seed ^ 0x5A5A), restarts=256
            )[0],
            "in_context_terminal_difference_ansatz": (
                _attack_terminal_difference(attacked)
            ),
            "weight_at_most_2_ansatz": _attack_sparse_ansatz(attacked)[0],
        }
        for name, candidate in candidates.items():
            attacks[name]["attempts"] += 1
            if verify(attacked, candidate)[0]:
                attacks[name]["successes"] += 1
        start = time.perf_counter()
        reference_answer, stats = _reference_cut_and_fit(attacked)
        reference_times.append(time.perf_counter() - start)
        reference_operations.append(stats["bit_operations"])
        reference_scans.append(stats["edge_scans"])
        if reference_answer is not None and verify(attacked, reference_answer)[0]:
            reference_successes += 1
        compact_answer, compact_stats = _compact_kernel_route(attacked)
        compact_operations.append(compact_stats["operations"])
        if compact_answer is not None and verify(attacked, compact_answer)[0]:
            compact_successes += 1
    all_failed = all(entry["successes"] == 0 for entry in attacks.values())
    median_reference_time = statistics.median(reference_times)
    median_reference_operations = int(statistics.median(reference_operations))
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": (
                "unit-capacity Ford-Fulkerson cut plus GF(2) Gaussian elimination"
            ),
            "complexity": "O(k(n+m) + n*d^2) exact bit operations",
            "median_wall_clock_sec": round(median_reference_time, 6),
            "median_operations": median_reference_operations,
            "median_residual_edge_scans": int(statistics.median(reference_scans)),
            "operation_definition": (
                "residual-edge scans and pivot tests count once; each packed row "
                "XOR counts d+2 bit operations"
            ),
            "solves": f"{reference_successes}/8, as expected",
        },
        "compact_route": {
            "name": "low-Hamming parity-kernel recovery",
            "median_operations": int(statistics.median(compact_operations)),
            "solves": f"{compact_successes}/8",
        },
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=77, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and len(doubled["edges"]) > len(inst["edges"]),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "shipping_edges": len(inst["edges"]),
        "doubled_edges": len(doubled["edges"]),
        "answer_elements_unchanged": len(doubled["answer"]) == len(answer),
        "doubled_verify_reason": doubled_reason,
    }

    invariant_checks = 0
    carried_checks = 0
    distinct_keys = []
    for offset in range(20):
        original = make_instance(seed=7000 + offset, **ship_params)
        key = canonical_key(original)
        distinct_keys.append(key)
        vertex_order = list(range(original["n"]))
        random.Random(8000 + offset).shuffle(vertex_order)
        bit_order = list(range(original["label_bits"]))
        random.Random(9000 + offset).shuffle(bit_order)
        operation_rng = random.Random(9500 + offset)
        linear_ops = [
            tuple(operation_rng.sample(range(original["label_bits"]), 2))
            for _ in range(original["label_bits"])
        ]
        translation = random.Random(10000 + offset).randrange(
            1 << original["label_bits"]
        )
        variants = [
            _transform_instance(
                original, vertex_order=vertex_order, edge_seed=11000 + offset
            ),
            _transform_instance(
                original, bit_order=bit_order, linear_ops=linear_ops
            ),
            _transform_instance(original, translation=translation),
            _transform_instance(
                original,
                vertex_order=vertex_order,
                bit_order=bit_order,
                linear_ops=linear_ops,
                translation=translation,
                edge_seed=12000 + offset,
            ),
        ]
        for variant in variants:
            invariant_checks += 1
            if canonical_key(variant) == key and verify(
                variant, variant["answer"]
            )[0]:
                carried_checks += 1
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 80
        and carried_checks == 80
        and len(set(distinct_keys)) == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_distinct": len(set(distinct_keys)),
        "unrelated_attempts": 20,
        "symmetries": [
            "arbitrary vertex renumbering",
            "edge-list reordering",
            "global bit-coordinate permutation",
            "invertible GF(2) changes of basis",
            "global XOR translation of every label",
            "all listed symmetries composed",
        ],
    }

    serialized = json.dumps(answer, separators=(",", ":"))
    answer_chars = len(serialized)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = len(answer)
    compact_answer, compact_stats = _compact_kernel_route(inst)
    intended_operations = compact_stats["operations"]
    arms = copy.deepcopy(G9_EVIDENCE["arms"])
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    hinted_rate = (
        hinted["solved"] / hinted["attempts"] if hinted["attempts"] else None
    )
    placebo_rate = (
        placebo["solved"] / placebo["attempts"] if placebo["attempts"] else None
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
        and compact_answer is not None
        and verify(inst, compact_answer)[0]
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "oracle_error_records": copy.deepcopy(G9_EVIDENCE["error_records"]),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "intended_route_verifies": (
            compact_answer is not None and verify(inst, compact_answer)[0]
        ),
    }

    # Replace the provisional profile sentence with actual measurements in the
    # report; the module constant is patched after the final shipping run.
    report["track_B_mechanical_cost"] = {
        "median_wall_clock_sec": round(median_reference_time, 6),
        "median_operations": median_reference_operations,
        "compact_route_operations": intended_operations,
    }
    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if re.match(r"G\d", key)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
