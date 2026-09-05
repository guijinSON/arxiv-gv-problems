"""Self-contained verified generator for the k-clique problem.

The native problem is the k-clique search task in Sections 2.6 and 4 of
Sanyal (Bhaduri) et al., arXiv:2004.10596.  The paper's oracle marks a tuple
exactly when every pair of represented vertices is adjacent.  This module
uses the same finite graph object and the same pairwise certificate check.

Generation is inverse: a uniformly placed set K is chosen first, all edges
inside K are inserted, and the remaining random graph is assembled around
it.  A small, graph-internal parity-probe gadget makes the intended no-tool
route possible without exposing K by vertex names.  Finally every vertex is
randomly relabelled and the certificate is carried through the relabelling.
No clique search occurs during generation.
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

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "undirected simple graph",
        "fixed-width hexadecimal adjacency rows",
        "set of k vertices",
    ],
    "verification_operations": [
        "integer range and distinctness checks",
        "exact adjacency-bit lookup",
        "pairwise edge comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "A repeated low-degree neighborhood identifies adjacency rows whose "
        "GF(2) parity is the hidden clique indicator; without that invariant, "
        "one must search the graph for a rare k-clique."
    ),
    "hardness_basis": (
        "Track B: the paper's Sections 4.2, 5, and 7 enumerate C(n,k) vertex "
        "sets to synthesize the oracle and use O(sqrt(C(n,k)/m)) Grover "
        "iterations; at shipping N=216 and k=8 this is 103,073,959,989,495 "
        "subsets and about 10,152,534 Grover iterations for one answer. The "
        "fixed-k exact branch-and-bound reference is O(N^8) at k=8 and "
        "has its measured recursive-intersection and wall-clock costs recorded "
        "by selftest at the shipping preset, while the parity invariant needs "
        "at most 174 one-hex-digit XOR/check operations."
    ),
    "max_answer_tokens": 9,
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

# n is the number of random-core vertices.  The answer remains short while the
# haystack grows; marker_count + witness_count additional graph vertices form
# the invariant gadget.
DIFFICULTY = {
    "demo": {
        "n": 12, "k": 4, "marker_count": 4, "witness_count": 2,
        "edge_num": 1, "edge_den": 3,
    },
    "easy": {
        "n": 208, "k": 8, "marker_count": 4, "witness_count": 4,
        "edge_num": 1, "edge_den": 4,
    },
    "medium": {
        "n": 216, "k": 8, "marker_count": 6, "witness_count": 2,
        "edge_num": 1, "edge_den": 4,
    },
    "hard": {
        "n": 224, "k": 8, "marker_count": 6, "witness_count": 2,
        "edge_num": 1, "edge_den": 4,
    },
}

SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The repeated low-degree neighborhood is a GF(2) parity probe on the "
    "adjacency rows."
)
PLACEBO_HINT = (
    "The fixed-width hexadecimal rows reward careful use of the stated bit "
    "convention."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A strictly increasing JSON list of exactly k distinct vertex numbers "
        "from 0 through N-1, restricted to vertices whose degree is at least "
        "k-1. Pairwise adjacency is the validity predicate being guessed, not "
        "an additional constraint on this candidate-sampling language."
    ),
    "bounds": {
        "length": "instance k (4..16)",
        "vertex_range": "0..N-1",
        "ordering": "strictly increasing",
        "repetition": "forbidden",
        "obvious_degree_filter": "degree >= k-1",
        "max_atomic_elements": 16,
    },
}

NOTES = (
    "Section 2.6.1 fixes the exact witness: a set C is a clique when every "
    "distinct pair in C is an edge. Sections 4.1.4 and 4.1.5 implement exactly "
    "that pairwise edge test, and Section 4.2 numbers vertices 0 through n-1 "
    "and enumerates all C(n,k) duplicate-free combinations. Sections 5 and 7 "
    "give the easy/mechanical side: O(k*C(n,k)+k) oracle-synthesis gates and "
    "O(sqrt(C(n,k)/m)) Grover iterations for m cliques. The paper proves no "
    "average-case hardness for planted graphs, so this module is explicitly "
    "Track B rather than making a false Track A claim. The graph is built by "
    "inverse generation, and a random vertex permutation carries the planted "
    "certificate. The random core is k-partite, with a degree-balanced planted "
    "transversal and many dead-end partial transversals; plant/decoy cross-edge "
    "density is adjusted to erase the expected-degree signal. Marker incidences "
    "use Bernoulli sampling conditioned only on one hidden parity constraint. "
    "Four to six marker vertices are recognized only "
    "through four equal-neighborhood witness vertices; XORing the marker rows "
    "returns the clique indicator. Degree ranking, common-neighbor greed, "
    "random greedy restarts, a parity-blind marker ansatz, and centered spectral "
    "power iteration are tested as failing attacks. Exact k-clique "
    "branch-and-bound is reported separately as Track B's successful reference "
    "algorithm."
)


# Script-owned oracle evidence is copied here after the bare and two diagnostic
# runs.  Empty records are honest before those runs and do not gate G9(c).
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"```(?:json|text)?\s*(.*?)```", re.I | re.S)
_ENUMERATION_CAP = 200_000
_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate(n, k, marker_count, witness_count, edge_num, edge_den):
    values = {
        "n": n, "k": k, "marker_count": marker_count,
        "witness_count": witness_count, "edge_num": edge_num,
        "edge_den": edge_den,
    }
    for name, value in values.items():
        if not _is_int(value):
            raise ValueError(f"{name} must be an integer")
    if not 10 <= n <= 4096:
        raise ValueError("n must lie in 10..4096")
    if not 4 <= k <= min(16, n):
        raise ValueError("k must lie in 4..min(16,n)")
    if n % k:
        raise ValueError("n must be divisible by k in this k-partite family")
    if marker_count < 4 or marker_count % 2:
        raise ValueError("marker_count must be an even integer at least 4")
    if not 2 <= witness_count <= 16:
        raise ValueError("witness_count must lie in 2..16")
    if not 0 < edge_num < edge_den <= 32:
        raise ValueError("edge density must satisfy 0 < edge_num < edge_den <= 32")


def _add_edge(rows, u, v):
    if u == v:
        raise ValueError("self-loop requested")
    rows[u] |= 1 << v
    rows[v] |= 1 << u


def _bernoulli(rng, numerator, denominator):
    return rng.randrange(denominator) < numerator


def _cross_density(n, k, edge_num, edge_den):
    """Plant-to-decoy density that equalizes expected core degrees.

    The core has k independent parts of size b=n/k.  If q is the
    plant/decoy edge probability and p the decoy/decoy one, equal expected
    degrees require 1+(b-1)q = q+(b-1)p. Tiny demo parameters can make q
    nonpositive; there we retain p because the demo is illustrative.
    """
    part_size = n // k
    numerator = (part_size - 1) * edge_num - edge_den
    denominator = (part_size - 2) * edge_den
    if denominator <= 0 or numerator <= 0:
        return edge_num, edge_den
    divisor = math.gcd(numerator, denominator)
    return numerator // divisor, denominator // divisor


def _sample_marker_bits(rng, count, parity, edge_num, edge_den):
    """Independent Bernoulli bits conditioned only on their XOR parity."""
    while True:
        bits = [
            int(_bernoulli(rng, edge_num, edge_den)) for _ in range(count)
        ]
        if (sum(bits) & 1) == parity:
            return bits


def _permute_rows(rows, old_to_new):
    total = len(rows)
    new_rows = [0] * total
    for old_u, old_row in enumerate(rows):
        new_u = old_to_new[old_u]
        bits = old_row
        while bits:
            low = bits & -bits
            old_v = low.bit_length() - 1
            new_rows[new_u] |= 1 << old_to_new[old_v]
            bits ^= low
    return new_rows


def _encode_rows(rows):
    width = max(1, (len(rows) + 3) // 4)
    return [format(row, f"0{width}x") for row in rows], width


def _decode_rows(inst):
    cached = inst.get("_adjacency_ints")
    if isinstance(cached, list) and len(cached) == inst["vertex_count"]:
        return cached
    return [int(value, 16) for value in inst["adjacency_hex"]]


def make_instance(
    n,
    seed=0,
    k=8,
    marker_count=8,
    witness_count=4,
    edge_num=1,
    edge_den=4,
):
    """Construct a graph and a known k-clique without solving clique search."""
    _validate(n, k, marker_count, witness_count, edge_num, edge_den)
    rng = random.Random(seed)

    core = list(range(n))
    part_size = n // k
    parts = [
        list(range(index * part_size, (index + 1) * part_size))
        for index in range(k)
    ]
    planted = {rng.choice(part) for part in parts}
    markers = list(range(n, n + marker_count))
    witnesses = list(range(n + marker_count, n + marker_count + witness_count))
    total = n + marker_count + witness_count
    rows = [0] * total

    # A random k-partite compatibility graph has one chosen representative in
    # every part.  The chosen transversal is forced complete. Plant-to-decoy
    # density is lowered just enough to match a decoy's expected core degree,
    # removing the simplest planted-clique outlier signal. Other transversals
    # overwhelmingly become dead ends rather than accidental answers.
    cross_num, cross_den = _cross_density(n, k, edge_num, edge_den)
    for left_index, left_part in enumerate(parts):
        for right_part in parts[left_index + 1:]:
            for u in left_part:
                for v in right_part:
                    both_planted = u in planted and v in planted
                    one_planted = (u in planted) != (v in planted)
                    if both_planted or (
                        one_planted and _bernoulli(rng, cross_num, cross_den)
                    ) or (
                        not both_planted
                        and not one_planted
                        and _bernoulli(rng, edge_num, edge_den)
                    ):
                        _add_edge(rows, u, v)

    # The parity of a core vertex's incidences to markers is exactly its clique
    # indicator.  Conditioning a moderately long Bernoulli vector changes each
    # one-edge marginal only slightly, avoiding a per-edge planting signature.
    for v in core:
        bits = _sample_marker_bits(
            rng, marker_count, int(v in planted), edge_num, edge_den
        )
        for index, bit in enumerate(bits):
            if bit:
                _add_edge(rows, v, markers[index])

    # An even-degree marker cycle contributes zero to the XOR of marker rows.
    for index in range(marker_count):
        _add_edge(rows, markers[index], markers[(index + 1) % marker_count])

    # Equal low-degree neighborhoods identify the marker set using graph data
    # alone. Since marker_count is even, these vertices also cancel in row XOR.
    for witness in witnesses:
        for marker in markers:
            _add_edge(rows, witness, marker)

    # A genuine vertex relabelling is applied last and carries the certificate.
    shuffled = list(range(total))
    rng.shuffle(shuffled)
    public_rows = _permute_rows(rows, shuffled)
    answer = sorted(shuffled[v] for v in planted)
    encoded, width = _encode_rows(public_rows)

    return {
        "family": "parity-probe k-clique",
        "paper": "arXiv:2004.10596",
        "vertex_count": total,
        "core_size": n,
        "part_count": k,
        "part_size": part_size,
        "k": k,
        "edge_density": [edge_num, edge_den],
        "plant_decoy_density": [cross_num, cross_den],
        "marker_count": marker_count,
        "witness_count": witness_count,
        "hex_width": width,
        "adjacency_hex": encoded,
        "_adjacency_ints": public_rows,
        "degrees": [row.bit_count() for row in public_rows],
        "answer": answer,
    }


def render(inst):
    n_vertices = inst["vertex_count"]
    lines = [
        "Find a k-clique in an undirected simple graph.",
        "",
        "A clique of size k is a set of exactly k distinct vertices such that "
        "every two different chosen vertices are joined by an edge. Vertex "
        f"numbers are the integers 0 through {n_vertices - 1}. Here k = "
        f"{inst['k']} and N = {n_vertices}.",
        "",
        "The graph is given by hexadecimal adjacency rows. Every row is a "
        f"fixed-width {inst['hex_width']}-digit nonnegative hexadecimal integer. "
        "In row i, bit j is 1 exactly when {i,j} is an edge; bit 0 is the "
        "least-significant (rightmost) bit. Leading zeroes are significant only "
        "for keeping the width fixed. The decimal degree is supplied as a "
        "redundant check. The diagonal bits are 0 and the rows are symmetric.",
        "",
        "Rows are listed by increasing degree (then by vertex number); the row "
        "label, not the display position, is the vertex number.",
        "",
        "row  degree  adjacency_hex",
    ]
    display_order = sorted(
        range(n_vertices),
        key=lambda vertex: (inst["degrees"][vertex], vertex),
    )
    lines.extend(
        f"{vertex:>3}  {inst['degrees'][vertex]:>6}  "
        f"{inst['adjacency_hex'][vertex]}"
        for vertex in display_order
    )
    lines.extend([
        "",
        "Output the vertices in strictly increasing order. Order otherwise does "
        "not matter, repetitions are forbidden, and all bounds are inclusive.",
        "Give your final answer inside <answer></answer> tags as one JSON list "
        f"of exactly {inst['k']} integers.",
        "Format example only (not claimed to be a clique here): "
        f"<answer>{json.dumps(list(range(inst['k'])), separators=(',', ':'))}</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    payload = matches[-1].strip()
    fence = _FENCE_RE.fullmatch(payload)
    if fence:
        payload = fence.group(1).strip()
    try:
        value = json.loads(payload)
    except (ValueError, TypeError):
        # Tolerate the common model response "3, 17, 42" despite requiring JSON.
        if not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", payload):
            return None
        try:
            value = [int(part.strip()) for part in payload.split(",")]
        except ValueError:
            return None
    if not isinstance(value, list):
        return None
    if not all(_is_int(item) for item in value):
        return None
    return value


def verify(inst, answer):
    """Check any valid k-clique; deliberately never consult inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer must not be empty"
    if len(answer) != inst["k"]:
        return False, f"expected exactly {inst['k']} vertices"
    if not all(_is_int(vertex) for vertex in answer):
        return False, "every vertex must be an integer"
    total = inst["vertex_count"]
    if any(vertex < 0 or vertex >= total for vertex in answer):
        return False, f"vertex outside the inclusive range 0..{total - 1}"
    if len(set(answer)) != len(answer):
        return False, "vertices must be distinct"
    if any(answer[index] >= answer[index + 1] for index in range(len(answer) - 1)):
        return False, "vertices must be in strictly increasing order"
    for left_index, left in enumerate(answer):
        row = _decode_rows(inst)[left]
        for right in answer[left_index + 1:]:
            if not ((row >> right) & 1):
                return False, f"missing edge {{{left},{right}}}"
    return True, "ok"


def _eligible_vertices(inst):
    return [
        vertex for vertex, degree in enumerate(inst["degrees"])
        if degree >= inst["k"] - 1
    ]


def random_candidate(inst, rng):
    eligible = _eligible_vertices(inst)
    if len(eligible) < inst["k"]:
        return []
    return sorted(rng.sample(eligible, inst["k"]))


def search_space(inst):
    eligible = len(_eligible_vertices(inst))
    if eligible < inst["k"]:
        return 0
    return math.comb(eligible, inst["k"])


def enumerate_all(inst):
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    count = 0
    for candidate in itertools.combinations(_eligible_vertices(inst), inst["k"]):
        count += int(verify(inst, list(candidate))[0])
    return count


def _wl_invariant(inst):
    """A relabelling-invariant 1-WL quotient, not a hash of presentation."""
    rows = _decode_rows(inst)
    total = len(rows)
    colors = [row.bit_count() for row in rows]
    for _ in range(total):
        signatures = []
        for vertex, row in enumerate(rows):
            neighbor_colors = []
            bits = row
            while bits:
                low = bits & -bits
                neighbor_colors.append(colors[low.bit_length() - 1])
                bits ^= low
            signatures.append((colors[vertex], tuple(sorted(neighbor_colors))))
        palette = {signature: index for index, signature in enumerate(sorted(set(signatures)))}
        new_colors = [palette[signature] for signature in signatures]
        stable = len(set(new_colors)) == len(set(colors))
        colors = new_colors
        if stable:
            break

    classes = {}
    for vertex, color in enumerate(colors):
        classes.setdefault(color, []).append(vertex)
    ordered_colors = sorted(classes)
    class_sizes = [len(classes[color]) for color in ordered_colors]
    quotient = []
    for left_pos, left_color in enumerate(ordered_colors):
        left_class = classes[left_color]
        for right_color in ordered_colors[left_pos:]:
            right_class = classes[right_color]
            edges = 0
            if left_color == right_color:
                for index, u in enumerate(left_class):
                    for v in left_class[index + 1:]:
                        edges += (rows[u] >> v) & 1
            else:
                right_mask = sum(1 << v for v in right_class)
                edges = sum((rows[u] & right_mask).bit_count() for u in left_class)
            quotient.append(edges)
    return [inst["k"], class_sizes, quotient]


def canonical_key(inst):
    payload = json.dumps(_wl_invariant(inst), separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params):
    harder = dict(params)
    current = int(harder["n"])
    if current >= 3072:
        return "cap_bound"
    k = int(harder["k"])
    proposed_n = max(current + 16, (3 * current + 1) // 2)
    proposed_n = min(4096, ((proposed_n + k - 1) // k) * k)
    proposed_witnesses = max(2, int(harder["witness_count"]) - 1)
    proposed_markers = int(harder["marker_count"])

    def operation_bound(marker_total):
        total = proposed_n + marker_total + proposed_witnesses
        hex_digits = (total + 3) // 4
        return proposed_witnesses + (marker_total - 1) * hex_digits + k

    proposed_operations = operation_bound(proposed_markers)
    if proposed_operations > 300 and proposed_markers > 4:
        # Once the haystack is large, remove one pair of parity-probe rows. This
        # is a second fixed-answer-length axis and keeps the manual XOR under the
        # exact-operation cap.
        proposed_markers = 4
        proposed_operations = operation_bound(proposed_markers)
    if proposed_operations > 300:
        return "cap_bound"
    harder["n"] = proposed_n
    # Delete one redundant copy of the twin-row clue while there is redundancy
    # left.  This grows the haystack and weakens the visible clue without
    # lengthening the eight-vertex answer.
    harder["witness_count"] = proposed_witnesses
    harder["marker_count"] = proposed_markers
    return harder


def _find_probe(inst):
    rows = _decode_rows(inst)
    groups = {}
    for vertex, row in enumerate(rows):
        groups.setdefault(row, []).append(vertex)
    candidates = [
        (len(vertices), -rows[vertices[0]].bit_count(), row, vertices)
        for row, vertices in groups.items() if len(vertices) >= 2
    ]
    if not candidates:
        return None, None
    _, _, marker_mask, witnesses = max(candidates)
    markers = []
    bits = marker_mask
    while bits:
        low = bits & -bits
        markers.append(low.bit_length() - 1)
        bits ^= low
    return markers, witnesses


def _compact_route(inst):
    rows = _decode_rows(inst)
    markers, _ = _find_probe(inst)
    if not markers:
        return []
    indicator = 0
    for marker in markers:
        indicator ^= rows[marker]
    answer = []
    while indicator:
        low = indicator & -indicator
        answer.append(low.bit_length() - 1)
        indicator ^= low
    return answer


def _attack_degree(inst):
    ranked = sorted(
        range(inst["vertex_count"]),
        key=lambda vertex: (-inst["degrees"][vertex], vertex),
    )
    return sorted(ranked[:inst["k"]])


def _attack_greedy(inst):
    rows = _decode_rows(inst)
    eligible = set(_eligible_vertices(inst))
    chosen = []
    while eligible and len(chosen) < inst["k"]:
        vertex = max(
            eligible,
            key=lambda item: (
                (rows[item] & sum(1 << v for v in eligible)).bit_count(),
                inst["degrees"][item],
                -item,
            ),
        )
        chosen.append(vertex)
        eligible = {other for other in eligible if (rows[vertex] >> other) & 1}
    return sorted(chosen)


def _attack_random_restart(inst, rng, restarts=256):
    rows = _decode_rows(inst)
    eligible = _eligible_vertices(inst)
    best = []
    for _ in range(restarts):
        candidates = list(eligible)
        rng.shuffle(candidates)
        chosen = []
        while candidates and len(chosen) < inst["k"]:
            # Mild heuristic: choose among four random-frontier vertices the one
            # with most surviving neighbors.
            sample = candidates[: min(4, len(candidates))]
            mask = sum(1 << value for value in candidates)
            vertex = max(sample, key=lambda value: (rows[value] & mask).bit_count())
            chosen.append(vertex)
            candidates = [
                value for value in candidates
                if value != vertex and ((rows[vertex] >> value) & 1)
            ]
        if len(chosen) > len(best):
            best = chosen
        if len(chosen) == inst["k"]:
            return sorted(chosen)
    return sorted(best)


def _attack_marker_common(inst):
    rows = _decode_rows(inst)
    markers, witnesses = _find_probe(inst)
    if not markers:
        return []
    excluded = set(markers) | set(witnesses or [])
    ranked = []
    for vertex in range(inst["vertex_count"]):
        if vertex in excluded:
            continue
        score = sum((rows[marker] >> vertex) & 1 for marker in markers)
        ranked.append((score, inst["degrees"][vertex], -vertex, vertex))
    ranked.sort(reverse=True)
    return sorted(entry[-1] for entry in ranked[:inst["k"]])


def _attack_spectral(inst, rng):
    rows = _decode_rows(inst)
    total = inst["vertex_count"]
    density = inst["edge_density"][0] / inst["edge_density"][1]
    vector = [rng.uniform(-1.0, 1.0) for _ in range(total)]
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    vector = [value / norm for value in vector]
    for _ in range(40):
        vector_sum = sum(vector)
        nxt = []
        for vertex, row in enumerate(rows):
            neighbor_sum = 0.0
            bits = row
            while bits:
                low = bits & -bits
                neighbor_sum += vector[low.bit_length() - 1]
                bits ^= low
            nxt.append(neighbor_sum - density * (vector_sum - vector[vertex]))
        norm = math.sqrt(sum(value * value for value in nxt)) or 1.0
        vector = [value / norm for value in nxt]
    positive = sorted(range(total), key=lambda v: (-vector[v], v))[:inst["k"]]
    negative = sorted(range(total), key=lambda v: (vector[v], v))[:inst["k"]]

    def edge_score(candidate):
        return sum(
            (rows[u] >> v) & 1
            for index, u in enumerate(candidate)
            for v in candidate[index + 1:]
        )

    chosen = max((positive, negative), key=edge_score)
    return sorted(chosen)


def _reference_branch_and_bound(inst, node_cap=20_000_000):
    """Exact increasing-order k-clique DFS using bitset intersections."""
    rows = _decode_rows(inst)
    k = inst["k"]
    eligible_mask = sum(1 << vertex for vertex in _eligible_vertices(inst))
    stats = {"nodes": 0, "intersections": 0, "capped": False}

    def visit(chosen, candidates):
        if len(chosen) == k:
            return chosen
        if len(chosen) + candidates.bit_count() < k:
            return None
        while candidates:
            if len(chosen) + candidates.bit_count() < k:
                return None
            if stats["nodes"] >= node_cap:
                stats["capped"] = True
                return None
            low = candidates & -candidates
            vertex = low.bit_length() - 1
            candidates ^= low
            stats["nodes"] += 1
            stats["intersections"] += 1
            found = visit(chosen + [vertex], candidates & rows[vertex])
            if found is not None:
                return found
            if stats["capped"]:
                return None
        return None

    answer = visit([], eligible_mask)
    return (sorted(answer) if answer is not None else None), stats


def _relabel_instance(inst, old_to_new):
    rows = _decode_rows(inst)
    if sorted(old_to_new) != list(range(len(rows))):
        raise ValueError("old_to_new must be a permutation")
    new_rows = _permute_rows(rows, old_to_new)
    encoded, width = _encode_rows(new_rows)
    transformed = copy.deepcopy(inst)
    transformed["adjacency_hex"] = encoded
    transformed["_adjacency_ints"] = new_rows
    transformed["hex_width"] = width
    transformed["degrees"] = [row.bit_count() for row in new_rows]
    transformed["answer"] = sorted(old_to_new[v] for v in inst["answer"])
    return transformed


def _answer_size(answer):
    blob = json.dumps(answer, separators=(",", ":"))
    return len(blob), (len(blob) + 3) // 4, len(answer)


def _intended_operations(inst):
    # G9 counts operations left after the insight. Rows are displayed by degree,
    # so the repeated low-degree row is visible without a hidden sorting step.
    # Charge every pairwise one-hex-digit XOR separately (not an unrealistic
    # machine-word XOR), plus witness checks and extraction of the k set bits.
    return (
        inst["witness_count"]
        + (inst["marker_count"] - 1) * inst["hex_width"]
        + inst["k"]
    )


def selftest():
    report = {
        "paper": "arXiv:2004.10596",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures = []
    attempts = 0
    for preset, parameters in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **parameters)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({
                    "preset": preset, "seed": seed,
                    "reason": "answer is not JSON-native",
                })
            compact = _compact_route(inst)
            if compact != inst["answer"] or not verify(inst, compact)[0]:
                failures.append({
                    "preset": preset, "seed": seed,
                    "reason": "constructed parity identity failed",
                })
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures,
        "generation_route": "inverse generation plus certificate-preserving vertex relabelling",
    }

    shipping = make_instance(
        seed=200410596, **DIFFICULTY[SHIPPING_DIFFICULTY]
    )
    planted = shipping["answer"]
    drop = planted[:-1]
    swap = list(planted)
    swap[0], swap[1] = swap[1], swap[0]
    duplicate = list(planted)
    duplicate[1] = duplicate[0]
    out_of_range = list(planted)
    out_of_range[-1] = shipping["vertex_count"]
    corruptions = {
        "drop_one_vertex": drop,
        "swap_two_vertices": swap,
        "duplicate_vertex": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = {entry["reason"] for entry in cases.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in cases.values()) and len(reasons) == 5,
        "cases": cases,
        "distinct_reasons": len(reasons),
    }

    answer_text = json.dumps(planted, separators=(",", ":"))
    realistic = (
        "The row-parity invariant gives this clique.\n"
        "```json\n<answer>\n" + answer_text + "\n</answer>\n```\n"
        "Every pair checks out."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged answer") is None,
        "parsed": parsed,
    }

    guess_rng = random.Random(0x200410596)
    guess_hits = 0
    guess_started = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_elapsed = time.perf_counter() - guess_started
    density = guess_hits / _G4_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6,
        "hits": guess_hits,
        "total": _G4_SAMPLES,
        "observed_probability": density,
        "structure_aware_space": search_space(shipping),
        "sampling_rule": (
            "uniform k-subset after enforcing exact length, distinctness, "
            "sorted order, range, and the obvious degree >= k-1 condition"
        ),
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attack_functions = {
        "outlier_high_degree": lambda inst, rng: _attack_degree(inst),
        "greedy_max_common_degree": lambda inst, rng: _attack_greedy(inst),
        "random_restart_16": lambda inst, rng: _attack_random_restart(inst, rng, 16),
        "marker_common_neighbor_ansatz": lambda inst, rng: _attack_marker_common(inst),
        "spectral_centered_power": lambda inst, rng: _attack_spectral(inst, rng),
    }
    attack_results = {
        name: {
            "successes": 0, "attempts": 0,
            "wall_clock_sec_total_8": 0.0,
        }
        for name in attack_functions
    }
    attack_budgets = {
        "outlier_high_degree": shipping["vertex_count"],
        "greedy_max_common_degree": shipping["k"] * shipping["vertex_count"],
        "random_restart_16": 16 * shipping["k"],
        "marker_common_neighbor_ansatz": shipping["vertex_count"],
        "spectral_centered_power": 40 * shipping["vertex_count"] ** 2,
    }
    seeds = list(range(6100, 6100 + _ATTACK_SEEDS))
    reference_runs = []
    compact_successes = 0
    for seed in seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for offset, (name, function) in enumerate(attack_functions.items()):
            started = time.perf_counter()
            candidate = function(inst, random.Random(seed * 1009 + offset))
            elapsed = time.perf_counter() - started
            attack_results[name]["wall_clock_sec_total_8"] += elapsed
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])
            attack_results[name]["attempts"] += 1
        started = time.perf_counter()
        candidate, stats = _reference_branch_and_bound(inst)
        stats["wall_clock_sec"] = time.perf_counter() - started
        stats["solved"] = bool(candidate is not None and verify(inst, candidate)[0])
        reference_runs.append(stats)
        compact_successes += int(verify(inst, _compact_route(inst))[0])
    for result in attack_results.values():
        result["wall_clock_sec_total_8"] = round(
            result["wall_clock_sec_total_8"], 6
        )

    reference_successes = sum(int(run["solved"]) for run in reference_runs)
    reference_algorithm = {
        "name": "exact increasing-order k-clique branch-and-bound with bitset intersections",
        "complexity": (
            "O(N^k) for fixed k (O(N^8) at shipping k=8); "
            "exponential when k is part of the input"
        ),
        "wall_clock_sec_total_8": round(
            sum(run["wall_clock_sec"] for run in reference_runs), 6
        ),
        "wall_clock_sec_mean": round(
            sum(run["wall_clock_sec"] for run in reference_runs) / _ATTACK_SEEDS,
            6,
        ),
        "nodes_mean": sum(run["nodes"] for run in reference_runs) // _ATTACK_SEEDS,
        "nodes_min": min(run["nodes"] for run in reference_runs),
        "nodes_max": max(run["nodes"] for run in reference_runs),
        "intersections_mean": (
            sum(run["intersections"] for run in reference_runs) // _ATTACK_SEEDS
        ),
        "operations": (
            sum(run["intersections"] for run in reference_runs) // _ATTACK_SEEDS
        ),
        "solves": f"{reference_successes}/{_ATTACK_SEEDS}, as expected",
    }
    all_attacks_failed = all(
        result["successes"] == 0 for result in attack_results.values()
    )
    report["G6_adversary_panel"] = {
        "pass": (
            all_attacks_failed
            and reference_successes == _ATTACK_SEEDS
            and compact_successes == _ATTACK_SEEDS
        ),
        "attacks": attack_results,
        "reference_algorithm": reference_algorithm,
        "paper_mechanical_route": {
            "name": "Sections 4.2 and 5 enumerate all graph-vertex k-subsets",
            "candidate_subsets": math.comb(
                shipping["vertex_count"], shipping["k"]
            ),
            "pair_tests_per_full_candidate": math.comb(shipping["k"], 2),
            "grover_iterations_if_one_solution_approx": int(math.sqrt(
                math.comb(shipping["vertex_count"], shipping["k"])
            )),
        },
        "compact_route": {
            "name": "identify twin neighborhood and XOR its adjacency rows over GF(2)",
            "operations": _intended_operations(shipping),
            "solves": f"{compact_successes}/{_ATTACK_SEEDS}, as expected",
        },
    }

    strongest_name = max(
        attack_results,
        key=lambda name: attack_results[name]["wall_clock_sec_total_8"],
    )
    report["G5_density_and_baseline_cost"] = {
        "pass": density < 1e-6 and all_attacks_failed,
        "shipping_density_estimate": density,
        "density_hits": guess_hits,
        "density_samples": _G4_SAMPLES,
        "construction_proven_solution_count_lower_bound": 1,
        "candidate_space": search_space(shipping),
        "strongest_failing_attack": strongest_name,
        "attack_operation_budget_total_8": (
            attack_budgets[strongest_name] * _ATTACK_SEEDS
        ),
        "attack_operation_budget_per_instance": attack_budgets[strongest_name],
        "attack_wall_clock_sec_total_8": attack_results[strongest_name][
            "wall_clock_sec_total_8"
        ],
        "attack_wall_clock_sec_mean": round(
            attack_results[strongest_name]["wall_clock_sec_total_8"]
            / _ATTACK_SEEDS,
            6,
        ),
        "reference_algorithm_nodes_mean": reference_algorithm["nodes_mean"],
        "reference_algorithm_wall_clock_sec_mean": reference_algorithm[
            "wall_clock_sec_mean"
        ],
        "paper_candidate_subsets": math.comb(
            shipping["vertex_count"], shipping["k"]
        ),
        "demo_exact_valid_answers": enumerate_all(
            make_instance(seed=3, **DIFFICULTY["demo"])
        ),
    }

    doubled_parameters = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_parameters["n"] *= 2
    doubled = make_instance(seed=707, **doubled_parameters)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (
            doubled_ok
            and doubled["core_size"] == 2 * shipping["core_size"]
            and search_space(doubled) > search_space(shipping)
            and len(doubled["answer"]) == len(shipping["answer"])
        ),
        "shipping_core_vertices": shipping["core_size"],
        "doubled_core_vertices": doubled["core_size"],
        "candidate_space_before": search_space(shipping),
        "candidate_space_after": search_space(doubled),
        "answer_elements_before": len(shipping["answer"]),
        "answer_elements_after": len(doubled["answer"]),
        "verify_reason": doubled_reason,
    }

    invariance_checks = 0
    carried_checks = 0
    invariance_failures = []
    for seed in range(20):
        inst = make_instance(seed=9000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        base_key = canonical_key(inst)
        total = inst["vertex_count"]
        rng = random.Random(12000 + seed)
        first = list(range(total))
        rng.shuffle(first)
        second = list(range(total))
        rng.shuffle(second)
        composed = [second[first[index]] for index in range(total)]
        reverse = list(reversed(range(total)))
        for name, permutation in (
            ("random", first),
            ("reverse", reverse),
            ("composed_random", composed),
        ):
            variant = _relabel_instance(inst, permutation)
            invariance_checks += 1
            if canonical_key(variant) != base_key:
                invariance_failures.append({"seed": seed, "variant": name})
            carried_checks += 1
            if not verify(variant, variant["answer"])[0]:
                invariance_failures.append({
                    "seed": seed, "variant": name + "_carried_witness",
                })
    unrelated_keys = [
        canonical_key(make_instance(
            seed=20000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY]
        ))
        for seed in range(20)
    ]
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": (
            not invariance_failures
            and invariance_checks >= 60
            and carried_checks >= 60
            and distinct_keys == 20
        ),
        "invariance_checks": invariance_checks,
        "invariance_failures": invariance_failures,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "symmetries_tested": [
            "arbitrary vertex permutation",
            "vertex-order reversal",
            "composition of two arbitrary vertex permutations",
        ],
        "key_method": "degree-seeded 1-WL stable quotient with class-pair edge counts",
    }

    answer_chars, answer_tokens, answer_elements = _answer_size(shipping["answer"])
    intended_operations = _intended_operations(shipping)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
