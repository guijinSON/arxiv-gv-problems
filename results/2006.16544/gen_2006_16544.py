"""Verified generator for arXiv:2006.16544.

The witness is a properly coloured tight Hamilton cycle in a 4-uniform
hypergraph.  Instances use the dense near-Dirac construction for tight cycles:
a planted cycle in a cubic base graph is carried to an alternating tight cycle
of the 4-graph.  Public GF(2) annotations give an intentionally mechanical way
to recover the planted base cycle, while a circulant change of variables gives
the intended compact route.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import time
from collections import Counter, deque


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "The decoder rows are a common-offset circulant basis: cancel the offset "
    "row, order the rotations of the inverse of 1+x+x^3, and recover K with "
    "the corresponding three-tap rotation before testing the edge masks."
)
PLACEBO_HINT: str = (
    "The decoder rows use fixed-width hexadecimal masks: keep the bit order, "
    "cyclic indexing, vertex partition, and normalization convention consistent "
    "when checking the edge masks."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "an exactly specified edge-coloured 4-uniform hypergraph",
        "a vertex bipartition and cubic base graph defining its hyperedges",
        "GF(2) decoder annotations on the base edges",
    ],
    "verification_operations": [
        "set cardinality and membership",
        "exact evaluation of the 4-uniform hyperedge predicate",
        "exact hyperedge-colour comparison",
        "cyclic permutation and normalization checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Project an alternating tight cycle to the cubic base graph and cancel "
        "the affine offset in a hidden circulant GF(2) basis; without that change "
        "of variables one must eliminate a dense decoder system."
    ),
    "hardness_basis": (
        "Track B: GF(2) Gaussian elimination followed by edge classification "
        "solves the shipping decoder in O(r*b^2+|E|*b) bit operations and measured "
        "349,522 counted bit operations / 0.001537 seconds at shipping, whereas the "
        "circulant route needs 259 exact packed-word XOR/parity operations.  The "
        "underlying near-threshold regime is the k=4 case of Garbe--Mycroft "
        "Theorem 1.5 (minimum codegree N/2-O(1))."
    ),
    "max_answer_tokens": 253,
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
    "demo": {"n": 8, "key_bits": 8, "decoder_decoys": 0, "anchors": 2},
    "easy": {"n": 112, "key_bits": 88, "decoder_decoys": 32, "anchors": 0},
    "medium": {"n": 116, "key_bits": 92, "decoder_decoys": 64, "anchors": 0},
    "hard": {"n": 120, "key_bits": 96, "decoder_decoys": 96, "anchors": 0},
}
SHIPPING_DIFFICULTY: str = "easy"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A list of exactly 2n distinct vertex identifiers, starting with min(A), "
        "alternating A,B, with the next A identifier smaller than the previous A "
        "identifier, and containing every required projected anchor edge."
    ),
    "bounds": {
        "max_shipping_atomic_elements": 240,
        "max_shipping_characters": 2000,
        "index_base": 0,
        "repetitions": 0,
    },
}

NOTES: str = (
    "Section 1 of arXiv:2006.16544 fixes the (k,l)-cycle definition, says that a "
    "coloured hypergraph is proper when every intersecting edge pair has different "
    "colours, and states Theorem 1 for properly coloured tight Hamilton cycles. "
    "Section 2 and Section 3's absorbing proof show why the regime above "
    "(1/2+gamma)N is guaranteed rather than a hard search distribution; the "
    "Introduction also explicitly says a uniform random-order/Local-Lemma route "
    "fails for incomplete hosts.  The generator therefore stays in the native "
    "4-uniform objects but uses the hard side of the same Dirac boundary: the "
    "k=4 dense construction in Garbe--Mycroft, Section 8 / Theorem 1.5, carries a "
    "cubic Hamilton cycle to a 4-graph of minimum codegree N/2-O(1).  The planted "
    "cycle is sampled first, an independent perfect matching supplies identically "
    "distributed decoy edges, and the tight-cycle witness is carried through the "
    "construction.  Dense random GF(2) edge masks defeat Hamming-weight outliers, "
    "label-greedy tracing, random walks, and the zero-key by-hand ansatz.  Gaussian "
    "elimination is reported honestly as the successful Track-B reference method."
)

# Filled from scripts/harden.py evidence after the three isolated runs.  A pending
# verdict deliberately fails G9 rather than inventing oracle evidence.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "hardened",
}


def _mask(bits):
    return (1 << bits) - 1


def _rotl(value, amount, bits):
    amount %= bits
    value &= _mask(bits)
    if amount == 0:
        return value
    return ((value << amount) | (value >> (bits - amount))) & _mask(bits)


def _rotr(value, amount, bits):
    return _rotl(value, -amount, bits)


def _circulant_inverse(bits):
    """First column of the inverse of multiplication by 1+x+x^3."""
    tap = 1 | (1 << 1) | (1 << 3)
    rows = []
    for output_bit in range(bits):
        coefficients = 0
        for input_bit in range(bits):
            if (_rotl(tap, input_bit, bits) >> output_bit) & 1:
                coefficients |= 1 << input_bit
        rows.append([coefficients, int(output_bit == 0)])
    pivot_row = 0
    for column in range(bits):
        pivot = next(
            (r for r in range(pivot_row, bits) if (rows[r][0] >> column) & 1),
            None,
        )
        if pivot is None:
            raise ValueError("key_bits makes 1+x+x^3 singular modulo x^b-1")
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        for r in range(bits):
            if r != pivot_row and ((rows[r][0] >> column) & 1):
                rows[r][0] ^= rows[pivot_row][0]
                rows[r][1] ^= rows[pivot_row][1]
        pivot_row += 1
    answer = 0
    for bit, row in enumerate(rows):
        if row[1]:
            answer |= 1 << bit
    return answer


def _offset(bits):
    return int("d6a39c5e71b428f09d3c6a57", 16) & _mask(bits)


def _structured_decoder_rows(bits, decoys, key, rng):
    inverse = _circulant_inverse(bits)
    offset = _offset(bits)
    masks = [offset] + [offset ^ _rotl(inverse, i, bits) for i in range(bits)]
    used = set(masks)
    while len(masks) < bits + 1 + decoys:
        candidate = rng.getrandbits(bits)
        if candidate not in used:
            used.add(candidate)
            masks.append(candidate)
    rows = [[row, (row & key).bit_count() & 1] for row in masks]
    rng.shuffle(rows)
    return rows


def _compact_decode(rows, bits):
    """Use the intended affine-circulant shortcut; return None if malformed."""
    table = {row: rhs for row, rhs in rows}
    if len(table) != len(rows):
        return None
    offset = _offset(bits)
    inverse = _circulant_inverse(bits)
    if offset not in table:
        return None
    offset_rhs = table[offset]
    z = 0
    for i in range(bits):
        row = offset ^ _rotl(inverse, i, bits)
        if row not in table:
            return None
        if table[row] ^ offset_rhs:
            z |= 1 << i
    return (z ^ _rotr(z, 1, bits) ^ _rotr(z, 3, bits)) & _mask(bits)


def _gaussian_decode(rows, bits):
    """Exact GF(2) elimination; return (unique key or None, counted bit ops)."""
    work = [[int(mask), int(rhs)] for mask, rhs in rows]
    pivot_rows = []
    rank = 0
    operations = 0
    for column in range(bits):
        pivot = None
        for r in range(rank, len(work)):
            operations += 1
            if (work[r][0] >> column) & 1:
                pivot = r
                break
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        for r in range(len(work)):
            if r == rank:
                continue
            operations += 1
            if (work[r][0] >> column) & 1:
                work[r][0] ^= work[rank][0]
                work[r][1] ^= work[rank][1]
                operations += bits + 1
        pivot_rows.append((column, rank))
        rank += 1
        if rank == bits:
            break
    if rank != bits:
        return None, operations
    key = 0
    for column, row in pivot_rows:
        operations += 1
        if work[row][1]:
            key |= 1 << column
    for row, rhs in rows:
        operations += bits
        if ((row & key).bit_count() & 1) != rhs:
            return None, operations
    return key, operations


def _random_matching_avoiding(n, forbidden, rng):
    vertices = list(range(n))
    for _ in range(10000):
        rng.shuffle(vertices)
        matching = [
            tuple(sorted((vertices[i], vertices[i + 1])))
            for i in range(0, n, 2)
        ]
        if all(edge not in forbidden for edge in matching):
            return matching
    raise RuntimeError("could not sample a matching disjoint from the planted cycle")


def _conditioned_edge_mask(bits, key, desired, used, rng):
    for _ in range(10000):
        value = rng.getrandbits(bits)
        if value not in used and ((value & key).bit_count() & 1) == desired:
            used.add(value)
            return value
    raise RuntimeError("could not sample a distinct conditioned decoder mask")


def _canonical_cycle(inst, sequence):
    """Normalize a cyclic alternating sequence to the statement's convention."""
    sequence = list(sequence)
    if not sequence:
        return sequence
    aset = set(inst["A"])
    first = min(aset)
    try:
        pos = sequence.index(first)
    except ValueError:
        return sequence
    sequence = sequence[pos:] + sequence[:pos]
    if len(sequence) >= 6 and sequence[2] > sequence[-2]:
        sequence = [sequence[0]] + list(reversed(sequence[1:]))
    return sequence


def make_instance(n, seed=0, key_bits=88, decoder_decoys=32, anchors=0,
                  **params) -> dict:
    """Inverse-generate a base cycle and carry it through the dense 4-graph map."""
    del params
    for name, value in (("n", n), ("key_bits", key_bits),
                        ("decoder_decoys", decoder_decoys), ("anchors", anchors)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if n < 8 or n % 2:
        raise ValueError("n must be an even integer at least 8")
    if key_bits < 8 or key_bits % 2:
        raise ValueError("key_bits must be an even integer at least 8")
    if decoder_decoys < 0:
        raise ValueError("decoder_decoys must be nonnegative")
    if anchors < 0 or anchors > n // 2:
        raise ValueError("anchors must lie between 0 and n/2")
    _circulant_inverse(key_bits)

    rng = random.Random(seed)
    key = rng.getrandbits(key_bits)
    if key == 0:
        key = 1 << rng.randrange(key_bits)
    decoder_rows = _structured_decoder_rows(key_bits, decoder_decoys, key, rng)

    planted = list(range(n))
    rng.shuffle(planted)
    cycle_edges = {
        tuple(sorted((planted[i], planted[(i + 1) % n]))) for i in range(n)
    }
    matching = _random_matching_avoiding(n, cycle_edges, rng)
    all_edges = sorted(cycle_edges | set(matching))

    used_masks = set()
    annotated = []
    for u, v in all_edges:
        desired = 0 if (u, v) in cycle_edges else 1
        edge_mask = _conditioned_edge_mask(
            key_bits, key, desired, used_masks, rng
        )
        annotated.append([u, v, edge_mask])

    # Choose vertex-disjoint planted edges as optional redundant clues.
    anchor_edges = []
    taken = set()
    for i in range(0, n, max(1, n // max(1, anchors))):
        if len(anchor_edges) >= anchors:
            break
        edge = tuple(sorted((planted[i], planted[(i + 1) % n])))
        if not (set(edge) & taken):
            anchor_edges.append(list(edge))
            taken.update(edge)
    if len(anchor_edges) != anchors:
        for edge in sorted(cycle_edges):
            if len(anchor_edges) >= anchors:
                break
            if not (set(edge) & taken):
                anchor_edges.append(list(edge))
                taken.update(edge)
    if len(anchor_edges) != anchors:
        raise RuntimeError("could not choose the requested disjoint anchors")

    # Relabel the entire hypergraph, mixing the two sides.  The public partition
    # remains, but neither side is a numeric interval.
    labels = list(range(2 * n))
    rng.shuffle(labels)
    amap = {old: labels[old] for old in range(n)}
    bmap = {old: labels[n + old] for old in range(n)}
    A = sorted(amap.values())
    B = sorted(bmap.values())
    annotated = sorted(
        [[amap[u], amap[v], edge_mask] for u, v, edge_mask in annotated],
        key=lambda row: tuple(sorted(row[:2])),
    )
    anchor_edges = sorted(
        [sorted((amap[u], amap[v])) for u, v in anchor_edges]
    )

    b_order = list(range(n))
    rng.shuffle(b_order)
    raw_answer = []
    for a, b in zip(planted, b_order):
        raw_answer.extend((amap[a], bmap[b]))

    inst = {
        "family": "annotated properly coloured tight Hamilton cycle",
        "uniformity": 4,
        "n_base": n,
        "vertex_count": 2 * n,
        "A": A,
        "B": B,
        "base_edges": annotated,
        "anchors": anchor_edges,
        "key_bits": key_bits,
        "decoder_decoys": decoder_decoys,
        "decoder_rows": decoder_rows,
        "minimum_codegree_lower_bound": n - 2 * (3 + 1),
    }
    inst["answer"] = _canonical_cycle(inst, raw_answer)
    return inst


def _hex(value, bits):
    return f"{value:0{(bits + 3) // 4}x}"


def render(inst) -> str:
    bits = inst["key_bits"]
    edge_lines = [
        f"  {u} {v} | {_hex(mask, bits)}"
        for u, v, mask in inst["base_edges"]
    ]
    row_lines = [
        f"  {_hex(mask, bits)} | {rhs}"
        for mask, rhs in inst["decoder_rows"]
    ]
    anchors = (
        ", ".join(f"{{{u},{v}}}" for u, v in inst["anchors"])
        if inst["anchors"] else "none"
    )
    statement = f"""PROPERLY COLOURED TIGHT HAMILTON CYCLE IN A 4-GRAPH

A 4-uniform hypergraph has vertices and unordered 4-element hyperedges.  A
tight Hamilton cycle is a cyclic ordering of every vertex in which every four
cyclically consecutive vertices form a hyperedge.  It is properly coloured if
every two of those hyperedges that intersect have different colours.

This instance has {inst['vertex_count']} vertices, numbered 0 through
{inst['vertex_count'] - 1}, partitioned into the following equal sets:
  A = {inst['A']}
  B = {inst['B']}

The hypergraph is specified exactly by a cubic simple graph G on A.  Its rows
below are "u v | m", where {{u,v}} is an undirected edge and m is a public
{bits}-bit hexadecimal annotation.  Leading zeroes are significant only for
width; bit 0 is the least significant bit.
{chr(10).join(edge_lines)}

For any 4-set e, put a=|e intersect A|.  It is a hyperedge exactly when:
  * a is 0, 1, or 4; or
  * a=2 and the two A-vertices form an edge of G; or
  * a=3 and none of the three A-pairs is an edge of G.
There are no other hyperedges.  The colour of a hyperedge is its injective
lexicographic rank among all 4-subsets of the numbered vertex set.  Thus two
hyperedges have the same colour exactly when they are the same 4-set; this is
an exact integer colouring, not a floating-point convention.

The following public decoder rows have format "mask | rhs" and mean
parity(mask AND K)=rhs over GF(2), for one promised unique {bits}-bit word K.
XOR is addition and parity is the number of 1-bits modulo 2.
{chr(10).join(row_lines)}

The instance promises that the G-edges whose annotations m satisfy
parity(m AND K)=0 form a Hamilton cycle of G.  This promise is auxiliary
information for finding a witness; the checker accepts every valid witness,
whether or not it is that promised cycle.

Required projected A-edges that your cycle must contain: {anchors}.

Output exactly {inst['vertex_count']} distinct vertex identifiers in cyclic
order.  The first must be min(A)={min(inst['A'])}; entries must alternate A,B;
and to remove reversal ambiguity the A-entry at position 2 must be smaller than
the A-entry at the penultimate position (positions are 0-based here).  Every
vertex must occur once, order matters subject to this normalization, repeats
are forbidden, and all displayed bounds are inclusive.  Projecting the output
to its A entries must include every required edge above.

Give your final answer inside <answer></answer> tags, as comma-separated decimal
integers.  Example format: <answer>0, 9, 2, 7</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json|text)?\s*|\s*```$", "", body,
                  flags=re.I | re.S).strip()
    if body == "":
        return []
    if body.startswith("[") and body.endswith("]"):
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            return None
        if not isinstance(value, list):
            return None
        if any(isinstance(v, bool) or not isinstance(v, int) for v in value):
            return None
        return value
    if not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", body):
        return None
    try:
        return [int(part.strip()) for part in body.split(",")]
    except ValueError:
        return None


def _base_edge_set(inst):
    return {tuple(sorted((u, v))) for u, v, _mask_value in inst["base_edges"]}


def _is_hyperedge(inst, vertices):
    edge = frozenset(vertices)
    if len(edge) != 4:
        return False
    aset = set(inst["A"])
    a_vertices = sorted(edge & aset)
    count = len(a_vertices)
    if count in (0, 1, 4):
        return True
    base = _base_edge_set(inst)
    if count == 2:
        return tuple(a_vertices) in base
    if count == 3:
        return all(tuple(pair) not in base for pair in itertools.combinations(a_vertices, 2))
    return False


def _edge_colour(inst, vertices):
    """Combinadic rank: an injective natural-number colour for a 4-set."""
    ordered = sorted(vertices)
    if len(ordered) != 4 or len(set(ordered)) != 4:
        return None
    return sum(math.comb(value, i + 1) for i, value in enumerate(ordered))


def verify(inst, answer) -> tuple[bool, str]:
    """Check a submitted cycle exactly, without consulting inst['answer']."""
    if not isinstance(answer, list) or any(
        isinstance(v, bool) or not isinstance(v, int) for v in answer
    ):
        return False, "answer must be a list of integer vertex identifiers"
    if not answer:
        return False, "answer is empty"
    total = inst["vertex_count"]
    if len(answer) != total:
        return False, f"answer must contain exactly {total} vertices"
    universe = set(inst["A"]) | set(inst["B"])
    unknown = [v for v in answer if v not in universe]
    if unknown:
        return False, f"answer contains unknown vertex {unknown[0]}"
    if len(set(answer)) != total:
        return False, "answer repeats a vertex"
    aset = set(inst["A"])
    bset = set(inst["B"])
    if answer[0] != min(aset):
        return False, "cycle is not rotated to start at min(A)"
    for i, vertex in enumerate(answer):
        expected = aset if i % 2 == 0 else bset
        if vertex not in expected:
            return False, f"A/B alternation fails at position {i}"
    if answer[2] >= answer[-2]:
        return False, "cycle orientation is not normalized"

    projected = answer[::2]
    projected_edges = {
        tuple(sorted((projected[i], projected[(i + 1) % len(projected)])))
        for i in range(len(projected))
    }
    for u, v in inst["anchors"]:
        if tuple(sorted((u, v))) not in projected_edges:
            return False, f"required projected edge {{{u},{v}}} is absent"

    cycle_edges = []
    for i in range(total):
        edge = tuple(answer[(i + j) % total] for j in range(4))
        if not _is_hyperedge(inst, edge):
            return False, f"cyclic 4-set at position {i} is not a hyperedge"
        cycle_edges.append((frozenset(edge), _edge_colour(inst, edge)))
    for i in range(total):
        edge_i, colour_i = cycle_edges[i]
        for j in range(i + 1, total):
            edge_j, colour_j = cycle_edges[j]
            if edge_i & edge_j and colour_i == colour_j:
                return False, f"intersecting cycle hyperedges {i} and {j} share a colour"
    return True, "ok"


def _anchor_blocks(inst, rng):
    aset = set(inst["A"])
    used = set()
    blocks = []
    for u, v in inst["anchors"]:
        pair = [u, v]
        if rng.randrange(2):
            pair.reverse()
        blocks.append(pair)
        used.update(pair)
    blocks.extend([[v] for v in aset - used])
    rng.shuffle(blocks)
    return blocks


def random_candidate(inst, rng) -> object:
    """Uniform candidate after enforcing shape, normalization, and anchors."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    a_order = [v for block in _anchor_blocks(inst, rng) for v in block]
    b_order = list(inst["B"])
    rng.shuffle(b_order)
    sequence = []
    for a, b in zip(a_order, b_order):
        sequence.extend((a, b))
    return _canonical_cycle(inst, sequence)


def search_space(inst) -> int | None:
    n = inst["n_base"]
    anchors = len(inst["anchors"])
    # Contract each vertex-disjoint required edge to a freely orientable block.
    a_cycles = (1 << anchors) * math.factorial(n - anchors - 1) // 2
    return a_cycles * math.factorial(n)


def enumerate_all(inst) -> int | None:
    n = inst["n_base"]
    if n > 9:
        return None
    aset = sorted(inst["A"])
    first = aset[0]
    base = _base_edge_set(inst)
    anchors = {tuple(sorted(edge)) for edge in inst["anchors"]}
    valid_projected = 0
    for tail in itertools.permutations(aset[1:]):
        order = (first,) + tail
        if order[1] >= order[-1]:
            continue
        edges = {
            tuple(sorted((order[i], order[(i + 1) % n]))) for i in range(n)
        }
        if anchors <= edges and edges <= base:
            valid_projected += 1
    return valid_projected * math.factorial(n)


def _graph_profiles(inst):
    """Strong cheap isomorphism invariant for the cubic base graph."""
    vertices = list(inst["A"])
    adjacency = {v: set() for v in vertices}
    edges = []
    for u, v, _mask_value in inst["base_edges"]:
        adjacency[u].add(v)
        adjacency[v].add(u)
        edges.append((u, v))
    anchor_set = {tuple(sorted(edge)) for edge in inst["anchors"]}
    profiles = []
    for root in vertices:
        distance = {root: 0}
        queue = deque([root])
        while queue:
            u = queue.popleft()
            for v in adjacency[u]:
                if v not in distance:
                    distance[v] = distance[u] + 1
                    queue.append(v)
        layer_sizes = tuple(sorted(Counter(distance.values()).items()))
        edge_layers = Counter()
        anchor_layers = Counter()
        for u, v in edges:
            signature = tuple(sorted((distance.get(u, n := len(vertices) + 1),
                                      distance.get(v, n))))
            edge_layers[signature] += 1
            if tuple(sorted((u, v))) in anchor_set:
                anchor_layers[signature] += 1
        profiles.append((layer_sizes, tuple(sorted(edge_layers.items())),
                         tuple(sorted(anchor_layers.items()))))
    return sorted(profiles)


def canonical_key(inst) -> str:
    """Invariant under all vertex/edge/row relabellings tested by selftest."""
    payload = {
        "n": inst["n_base"],
        "anchor_count": len(inst["anchors"]),
        "base_profiles": _graph_profiles(inst),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def escalate(params) -> dict | str | None:
    """Raise decoder crowding first, then n until the answer-format cap binds."""
    harder = dict(params)
    if harder.get("decoder_decoys", 0) < 128:
        harder["decoder_decoys"] = min(128, harder.get("decoder_decoys", 0) + 32)
        harder["anchors"] = 0
        return harder
    if harder.get("n", 0) < 124:
        harder["n"] = min(124, harder.get("n", 0) + 4)
        harder["key_bits"] = min(96, harder.get("key_bits", 8) + 4)
        return harder
    return "cap_bound"


def _answer_from_projected(inst, projected, b_order=None):
    if b_order is None:
        b_order = sorted(inst["B"])
    sequence = []
    for a, b in zip(projected, b_order):
        sequence.extend((a, b))
    return _canonical_cycle(inst, sequence)


def _cycle_from_edges(inst, selected):
    adjacency = {v: [] for v in inst["A"]}
    for u, v in selected:
        if u not in adjacency or v not in adjacency:
            return None
        adjacency[u].append(v)
        adjacency[v].append(u)
    if any(len(adjacency[v]) != 2 for v in adjacency):
        return None
    start = min(adjacency)
    order = [start]
    previous = None
    current = start
    while True:
        candidates = [v for v in adjacency[current] if v != previous]
        if not candidates:
            return None
        nxt = min(candidates) if previous is None else candidates[0]
        if nxt == start:
            break
        if nxt in order:
            return None
        order.append(nxt)
        previous, current = current, nxt
    if len(order) != len(adjacency):
        return None
    if order[1] > order[-1]:
        order = [order[0]] + list(reversed(order[1:]))
    return order


def _reference_solve(inst):
    started = time.perf_counter()
    key, operations = _gaussian_decode(inst["decoder_rows"], inst["key_bits"])
    if key is None:
        return None, operations, time.perf_counter() - started
    selected = []
    for u, v, edge_mask in inst["base_edges"]:
        operations += inst["key_bits"]
        if ((edge_mask & key).bit_count() & 1) == 0:
            selected.append((u, v))
    projected = _cycle_from_edges(inst, selected)
    answer = None if projected is None else _answer_from_projected(inst, projected)
    return answer, operations, time.perf_counter() - started


def _candidate_from_greedy(inst):
    adjacency = {v: [] for v in inst["A"]}
    for u, v, _edge_mask in inst["base_edges"]:
        adjacency[u].append(v)
        adjacency[v].append(u)
    start = min(adjacency)
    order = [start]
    seen = {start}
    while len(order) < len(adjacency):
        choices = sorted(v for v in adjacency[order[-1]] if v not in seen)
        if not choices:
            return None
        order.append(choices[0])
        seen.add(choices[0])
    if start not in adjacency[order[-1]]:
        return None
    return _answer_from_projected(inst, order)


def _random_walk_attack(inst, seed, restarts=256):
    rng = random.Random(seed)
    adjacency = {v: [] for v in inst["A"]}
    for u, v, _edge_mask in inst["base_edges"]:
        adjacency[u].append(v)
        adjacency[v].append(u)
    start = min(adjacency)
    for _ in range(restarts):
        order = [start]
        seen = {start}
        while len(order) < len(adjacency):
            choices = [v for v in adjacency[order[-1]] if v not in seen]
            if not choices:
                break
            nxt = rng.choice(choices)
            order.append(nxt)
            seen.add(nxt)
        if len(order) == len(adjacency) and start in adjacency[order[-1]]:
            answer = _answer_from_projected(inst, order)
            if verify(inst, answer)[0]:
                return answer
    return None


def _outlier_attack(inst):
    n = inst["n_base"]
    ranked = sorted(
        inst["base_edges"], key=lambda row: (row[2].bit_count(), row[2], row[0], row[1])
    )
    selected = [(u, v) for u, v, _edge_mask in ranked[:n]]
    projected = _cycle_from_edges(inst, selected)
    return None if projected is None else _answer_from_projected(inst, projected)


def _zero_key_attack(inst):
    selected = [(u, v) for u, v, _edge_mask in inst["base_edges"]]
    projected = _cycle_from_edges(inst, selected)
    return None if projected is None else _answer_from_projected(inst, projected)


def _unmatched_rhs_ansatz(inst):
    """A plausible no-tool mistake: read shuffled RHS bits in displayed order."""
    bits = inst["key_bits"]
    guessed = 0
    for i, (_row, rhs) in enumerate(inst["decoder_rows"][:bits]):
        if rhs:
            guessed |= 1 << i
    selected = [
        (u, v) for u, v, edge_mask in inst["base_edges"]
        if ((edge_mask & guessed).bit_count() & 1) == 0
    ]
    projected = _cycle_from_edges(inst, selected)
    return None if projected is None else _answer_from_projected(inst, projected)


def _relabel_instance(inst, mapping, reorder_seed=None):
    out = {
        key: value for key, value in inst.items()
        if key not in {"A", "B", "base_edges", "anchors", "answer", "decoder_rows"}
    }
    out["A"] = sorted(mapping[v] for v in inst["A"])
    out["B"] = sorted(mapping[v] for v in inst["B"])
    out["base_edges"] = [
        [mapping[u], mapping[v], edge_mask]
        for u, v, edge_mask in inst["base_edges"]
    ]
    out["anchors"] = [sorted((mapping[u], mapping[v])) for u, v in inst["anchors"]]
    out["decoder_rows"] = [list(row) for row in inst["decoder_rows"]]
    carried = [mapping[v] for v in inst["answer"]]
    if reorder_seed is not None:
        rng = random.Random(reorder_seed)
        rng.shuffle(out["base_edges"])
        rng.shuffle(out["anchors"])
        rng.shuffle(out["decoder_rows"])
    out["answer"] = _canonical_cycle(out, carried)
    return out


def _permute_decoder_bits(inst, permutation):
    """Rename GF(2) coordinates in every public annotation and decoder row."""
    bits = inst["key_bits"]
    if sorted(permutation) != list(range(bits)):
        raise ValueError("permutation must rename every decoder bit exactly once")

    def rename(mask_value):
        result = 0
        for old, new in enumerate(permutation):
            if (mask_value >> old) & 1:
                result |= 1 << new
        return result

    out = {
        key: value for key, value in inst.items()
        if key not in {"base_edges", "decoder_rows", "answer"}
    }
    out["base_edges"] = [
        [u, v, rename(edge_mask)] for u, v, edge_mask in inst["base_edges"]
    ]
    out["decoder_rows"] = [
        [rename(row), rhs] for row, rhs in inst["decoder_rows"]
    ]
    out["answer"] = list(inst["answer"])
    return out


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest() -> dict:
    report = {}

    # G1: every preset, multiple independent seeds, and JSON-native answers.
    g1_failures = []
    g1_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
            compact = _compact_decode(inst["decoder_rows"], inst["key_bits"])
            if compact is None:
                g1_failures.append(f"{preset}/{seed}: compact decoder failed")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "checks": g1_checks, "failures": g1_failures
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping)

    # G2: five corruption classes with deliberately distinct verifier reasons.
    corruptions = {}
    corruptions["empty"] = []
    corruptions["drop"] = inst["answer"][:-1]
    duplicate = list(inst["answer"])
    duplicate[4] = duplicate[2]
    corruptions["duplicate"] = duplicate
    outside = list(inst["answer"])
    outside[5] = inst["vertex_count"] + 7
    corruptions["out_of_range"] = outside
    swapped_answer = None
    swapped_reason = None
    for i in range(4, len(inst["answer"]) - 4, 2):
        for j in range(i + 2, min(len(inst["answer"]) - 2, i + 18), 2):
            candidate = list(inst["answer"])
            candidate[i], candidate[j] = candidate[j], candidate[i]
            ok, why = verify(inst, candidate)
            if not ok and why.startswith("cyclic 4-set"):
                swapped_answer, swapped_reason = candidate, why
                break
        if swapped_answer is not None:
            break
    corruptions["swap"] = swapped_answer if swapped_answer is not None else list(reversed(inst["answer"]))
    reasons = {}
    all_rejected = True
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        all_rejected &= not ok
        reasons[name] = why
    report["G2_rejects_corruption"] = {
        "pass": all_rejected and len(set(reasons.values())) == len(reasons),
        "reasons": reasons,
        "swap_search_reason": swapped_reason,
    }

    # G3: prose, a fenced answer, and whitespace around the required tags.
    answer_body = ", ".join(map(str, inst["answer"]))
    response = (
        "I projected to A and checked the wraparound.\n\n"
        "```text\nFinal witness follows.\n```\n"
        f"<answer>\n{answer_body}\n</answer>\n"
        "The tags contain only the requested integers."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0],
        "parsed_length": len(parsed) if isinstance(parsed, list) else None,
    }

    # G4 and shipping density for G5 share the mandated structure-aware sample.
    samples = 200_000
    hits = 0
    guess_rng = random.Random(271828)
    started = time.perf_counter()
    for _ in range(samples):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            hits += 1
    sampling_seconds = time.perf_counter() - started
    probability = hits / samples
    report["G4_guess_resistance"] = {
        "pass": samples >= 200_000 and probability < 1e-6,
        "hits": hits,
        "total": samples,
        "estimated_probability": probability,
        "structure_aware": True,
        "candidate_space": search_space(inst),
    }

    # Track-B reference method: successful by design and kept outside attacks.
    attack_seeds = list(range(700, 708))
    reference_successes = 0
    reference_operations = []
    reference_times = []
    for seed in attack_seeds:
        trial = make_instance(seed=seed, **shipping)
        candidate, operations, elapsed = _reference_solve(trial)
        reference_operations.append(operations)
        reference_times.append(elapsed)
        if candidate is not None and verify(trial, candidate)[0]:
            reference_successes += 1

    report["G5_density_and_baseline"] = {
        "pass": probability < 1e-6 and reference_successes == len(attack_seeds),
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_estimate": probability,
        "sampling_wall_seconds": round(sampling_seconds, 6),
        "baseline_wall_seconds_median": round(
            sorted(reference_times)[len(reference_times) // 2], 6
        ),
        "baseline_operation_count_median": sorted(reference_operations)[
            len(reference_operations) // 2
        ],
        "demo_exact_valid_answer_count": enumerate_all(
            make_instance(seed=0, **DIFFICULTY["demo"])
        ),
    }

    attack_results = {
        "hamming_weight_outlier": 0,
        "smallest_label_greedy": 0,
        "random_walk_256": 0,
        "unmatched_rhs_by_hand_ansatz": 0,
    }
    for seed in attack_seeds:
        trial = make_instance(seed=seed, **shipping)
        candidates = {
            "hamming_weight_outlier": _outlier_attack(trial),
            "smallest_label_greedy": _candidate_from_greedy(trial),
            "random_walk_256": _random_walk_attack(trial, seed ^ 0xBAD5EED),
            "unmatched_rhs_by_hand_ansatz": _unmatched_rhs_ansatz(trial),
        }
        for name, candidate in candidates.items():
            if candidate is not None and verify(trial, candidate)[0]:
                attack_results[name] += 1
    attacks = {
        name: {"successes": successes, "attempts": len(attack_seeds)}
        for name, successes in attack_results.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attacks.values())
        and reference_successes == len(attack_seeds),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact GF(2) Gaussian elimination plus parity classification",
            "complexity": "O(r*b^2 + |E|*b) bit operations",
            "wall_clock_sec_median": round(
                sorted(reference_times)[len(reference_times) // 2], 6
            ),
            "operations_median": sorted(reference_operations)[
                len(reference_operations) // 2
            ],
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
    }

    doubled = make_instance(
        n=2 * shipping["n"], seed=424242,
        key_bits=shipping["key_bits"],
        decoder_decoys=shipping["decoder_decoys"], anchors=0,
    )
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["vertex_count"] == 2 * inst["vertex_count"],
        "shipping_vertices": inst["vertex_count"],
        "doubled_vertices": doubled["vertex_count"],
        "doubled_verify_reason": doubled_why,
    }

    invariant_checks = 0
    carried_checks = 0
    keys = []
    for seed in range(20):
        trial = make_instance(seed=9000 + seed, **shipping)
        keys.append(canonical_key(trial))
        rng = random.Random(12000 + seed)
        labels = list(range(trial["vertex_count"]))
        rng.shuffle(labels)
        mapping = {old: labels[old] for old in range(trial["vertex_count"])}
        relabelled = _relabel_instance(trial, mapping, reorder_seed=15000 + seed)
        bit_permutation = list(range(trial["key_bits"]))
        rng.shuffle(bit_permutation)
        transformed = _permute_decoder_bits(relabelled, bit_permutation)
        if canonical_key(transformed) == canonical_key(trial):
            invariant_checks += 1
        if verify(transformed, transformed["answer"])[0]:
            carried_checks += 1
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 20 and carried_checks == 20 and distinct == 20,
        "invariance_checks_passed": invariant_checks,
        "carried_witness_checks_passed": carried_checks,
        "distinct_unrelated_keys": distinct,
        "unrelated_instances": 20,
        "transformations": [
            "arbitrary renaming of all hypergraph vertices",
            "base-edge, anchor, and decoder-row reordering",
            "arbitrary renaming of GF(2) decoder coordinates",
            "composition of vertex/coordinate renaming and all reorderings",
        ],
    }

    answer_blob = json.dumps(inst["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(inst["answer"])
    intended_operations = (
        inst["key_bits"] + len(inst["base_edges"]) + 3
    )
    arms = G9_RESULTS["arms"]
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    within_caps = (
        answer_chars <= 2000 and answer_elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == answer_tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": G9_RESULTS["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
