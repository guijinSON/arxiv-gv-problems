"""Retained rejected prototype for compact two-galaxy certificates.

The native objects are the edge partitions into galaxies (star forests) that
define star arboricity in arXiv:1312.5698.  Each instance is an edge-tagged
graph assembled as the union of two planted star forests.  The answer is a
nonzero Boolean linear form: evaluating it on every edge tag reconstructs the
two galaxies, which the verifier then checks directly.

Generation samples the linear form and the two forests first.  It never solves
the graph it emits.  Nevertheless, REJECTED.md explains why the tag/slot/probe
overlay is benchmark convenience absent from the paper and cannot establish
native coverage.  The module is kept only because the task requires rejected
prototypes to remain available for audit.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time
from collections import Counter, deque
from typing import Any


TRACK = "B"
REJECTED_PROTOTYPE = True

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "linear_algebra",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "edge-tagged finite graph",
        "two galaxies (vertex-disjoint unions of stars)",
        "Boolean linear form defining an edge partition",
    ],
    "verification_operations": [
        "exact parity evaluation on integer bit vectors",
        "exact graph component traversal",
        "degree and edge-count test for every star component",
    ],
    "domain_essentiality": "discretised_analogue",
    "reduction_kind": "convenience",
    "reduction": (
        "Benchmark convenience: edge tags, slots, and the probe are not licensed "
        "by arXiv:1312.5698; they create the parity-reconstruction shortcut."
    ),
    "reduction_source": "benchmark_convenience",
    "intuition_type": "invariant",
    "intuition_description": (
        "The tag differences among the same-star edges at the probe vertex "
        "are orthogonal to the hidden Boolean linear form, and their slot "
        "pattern exposes its coefficients without decomposing the full graph."
    ),
    "hardness_basis": (
        "Track B: contaminant-omission plus GF(2) nullspace elimination solves "
        "this generated distribution in O(d^4+md) bit operations; at the hard "
        "preset it used 697,717 scalar bit operations and 0.068 seconds in the "
        "recorded shipping baseline, whereas the slot invariant gives a "
        "257-operation route on 65 probe edges that is executable only after "
        "recognizing the construction."
    ),
    "max_answer_tokens": 8,
}

NATIVE = {
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

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object {\"mask\": M}, where M is a decimal integer with "
        "2^(bits-1) <= M < 2^bits.  It denotes the Boolean linear form "
        "edge_color(tag) = parity(M AND tag)."
    ),
    "bounds": {
        "object_keys": ["mask"],
        "mask_bits": "the instance field bits",
        "top_bit_must_be_one": True,
        "atomic_elements": 1,
    },
}

DIFFICULTY = {
    "demo": {"n": 2, "bits": 5},
    "easy": {"n": 3, "bits": 24},
    "medium": {"n": 5, "bits": 40},
    "hard": {"n": 8, "bits": 64},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "At the probe, the complete slot family has tag differences orthogonal to the hidden parity mask."
)
PLACEBO_HINT = (
    "At the probe, the displayed edge records reward careful attention to their integer fields."
)

# Populated from the script-owned transcripts after the three arms are run.
G9_MEASUREMENTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not yet run",
    "placebo_verdict": "not yet run",
}

NOTES = r"""
Paper grounding and Step 0.  Section 1 defines a galaxy as a vertex-disjoint
union of stars and sa(G) as the minimum number of galaxies partitioning E(G).
The introduction also states the general NP-completeness of deciding sa(G)<=2,
but worst-case NP-completeness says nothing about an inverse-generated
distribution.  Lemma 4 in Section 3.1 is the constructive warning: under its
tripartite degree conditions, alternating perfect matchings immediately give
two galaxies.  The paper's exact hypercube values in Theorem 2, Proposition 1,
and Lemma 5 likewise come with direct constructions or product bounds.  A
Track-A claim for those objects would therefore be false.

Why Track B.  This family keeps the paper's native witness--an edge partition
whose two classes are checked as star forests--but writes that partition as a
Boolean linear form on public edge tags.  The unrestricted planted coloring is
easy once known, and this generated regime also has a polynomial decoder:
at the degree-(d+1) probe, omit each possible contaminating edge, row-reduce
the other d tag differences over GF(2), and verify the resulting one-dimensional
nullspace.  The reference implementation measures that O(d^4+md) route.  The
short route notices that slots 0,...,d-1 occur once plus one duplicate; after
discarding the duplicate contaminant, slot i differs from slot 0 only in bit
i-1 and possibly the top bit.  Those top bits are the mask coefficients.

Generation and attacks.  The mask is sampled first with its top bit set.  Two
random star factors with disjoint center sets are then laid over the same
vertices.  Every planted star receives an independently translated copy of a
basis for the mask's orthogonal hyperplane, so all its tags have the intended
parity.  Vertex labels and the edge list are shuffled.  The top-bit-only,
probe-tag-majority, eight-slot partial, and 256-restart attacks are all tested;
the successful generic nullspace decoder is reported separately, as Track B
requires.  Edges in both planted colors use the same tag construction and the
same star-size distribution.
""".strip()


_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8
_ENUMERATION_CAP = 1 << 16
_PREPARED_CACHE: dict[int, tuple[dict, dict]] = {}


def _parity(x: int) -> int:
    return x.bit_count() & 1


def _norm_edge(u: int, v: int) -> tuple[int, int]:
    return (u, v) if u < v else (v, u)


def _validate_params(n: int, bits: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    if isinstance(bits, bool) or not isinstance(bits, int) or bits < 5:
        raise ValueError("bits must be an integer at least 5")
    if bits > 96:
        raise ValueError("bits above 96 are outside this certificate language")


def _sample_mask(bits: int, rng: random.Random) -> int:
    top = 1 << (bits - 1)
    while True:
        mask = top | rng.getrandbits(bits - 1)
        low_ones = (mask & (top - 1)).bit_count()
        if max(1, (bits - 1) // 4) <= low_ones <= max(2, 3 * (bits - 1) // 4):
            if bits <= 9 or mask & (((1 << (bits - 1)) - 1) ^ 0xFF):
                return mask


def _star_factor(
    vertex_count: int,
    centers: list[int],
    rng: random.Random,
) -> tuple[list[tuple[int, int]], dict[int, list[tuple[int, int]]]]:
    leaves = [v for v in range(vertex_count) if v not in set(centers)]
    rng.shuffle(leaves)
    degree = (vertex_count - len(centers)) // len(centers)
    by_center: dict[int, list[tuple[int, int]]] = {}
    edges: list[tuple[int, int]] = []
    for i, center in enumerate(centers):
        star = [_norm_edge(center, v) for v in leaves[i * degree : (i + 1) * degree]]
        by_center[center] = star
        edges.extend(star)
    return edges, by_center


def _base_with_parity(bits: int, mask: int, color: int, rng: random.Random) -> int:
    top = 1 << (bits - 1)
    base = rng.getrandbits(bits)
    if _parity(base & mask) != color:
        base ^= top
    return base


def _tag_star(
    bits: int,
    mask: int,
    color: int,
    rng: random.Random,
    used: set[int],
) -> list[tuple[int, int]]:
    """Return (tag, slot) pairs forming an affine basis of mask^perp."""
    top = 1 << (bits - 1)
    while True:
        base = _base_with_parity(bits, mask, color, rng)
        pairs = [(base, 0)]
        for slot in range(1, bits):
            coordinate = slot - 1
            difference = 1 << coordinate
            if (mask >> coordinate) & 1:
                difference |= top
            pairs.append((base ^ difference, slot))
        tags = {tag for tag, _ in pairs}
        if len(tags) == bits and tags.isdisjoint(used):
            used.update(tags)
            rng.shuffle(pairs)
            return pairs


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Inverse-generate an edge-tagged graph and its symbolic galaxy partition."""
    bits = params.pop("bits", None)
    if params:
        raise TypeError(f"unexpected parameters: {sorted(params)}")
    if bits is None:
        raise TypeError("missing required parameter: bits")
    _validate_params(n, bits)
    rng = random.Random(seed)
    mask = _sample_mask(bits, rng)

    vertex_count = n * (bits + 1)
    vertices = list(range(vertex_count))
    rng.shuffle(vertices)
    centers0 = vertices[:n]
    centers1 = vertices[n : 2 * n]

    # Resample both factors because, for very small n, one first-factor center
    # can receive every opposite center and leave no edge-disjoint completion.
    for _ in range(10_000):
        edges0, stars0 = _star_factor(vertex_count, centers0, rng)
        edges1, stars1 = _star_factor(vertex_count, centers1, rng)
        if set(edges0).isdisjoint(edges1):
            break
    else:
        raise RuntimeError("could not construct edge-disjoint star factors")

    records: dict[tuple[int, int], list[int]] = {}
    used_tags: set[int] = set()
    for color, stars in ((0, stars0), (1, stars1)):
        for center in centers0 if color == 0 else centers1:
            star_edges = list(stars[center])
            tag_slots = _tag_star(bits, mask, color, rng, used_tags)
            rng.shuffle(star_edges)
            for edge, (tag, slot) in zip(star_edges, tag_slots):
                records[edge] = [edge[0], edge[1], tag, slot]

    # Relabel graph vertices after construction, then shuffle the edge table.
    relabel = list(range(vertex_count))
    rng.shuffle(relabel)
    edge_rows = []
    for u, v, tag, slot in records.values():
        a, b = _norm_edge(relabel[u], relabel[v])
        edge_rows.append([a, b, tag, slot])
    rng.shuffle(edge_rows)

    degree = [0] * vertex_count
    incident: list[list[int]] = [[] for _ in range(vertex_count)]
    for i, (u, v, _, _) in enumerate(edge_rows):
        degree[u] += 1
        degree[v] += 1
        incident[u].append(i)
        incident[v].append(i)
    candidates = [v for v, value in enumerate(degree) if value == bits + 1]
    if not candidates:
        raise RuntimeError("constructed graph has no probe candidate")

    # Prefer a probe on which the tempting 'take the smaller duplicate tag'
    # shortcut chooses the contaminant.  This changes no edge distribution.
    probe = candidates[0]
    for v in candidates:
        rows = [edge_rows[i] for i in incident[v]]
        greedy = _greedy_duplicate_mask_from_rows(rows, bits)
        if greedy is None or greedy != mask:
            probe = v
            break

    probe_rows = sorted((edge_rows[i][:] for i in incident[probe]), key=lambda row: (row[3], row[2]))
    return {
        "paper": "arXiv:1312.5698",
        "n": n,
        "bits": bits,
        "vertex_count": vertex_count,
        "edge_count": len(edge_rows),
        "edges": edge_rows,
        "probe_vertex": probe,
        "probe_edges": probe_rows,
        "answer": {"mask": mask},
    }


def render(inst: dict) -> str:
    """Render a self-contained problem statement and exact output contract."""
    bits = inst["bits"]
    width = (bits + 3) // 4
    lines = [
        "Find a compact two-galaxy edge partition.",
        "",
        "A star is a graph K_1,r for r >= 1 (K_2 is allowed). A galaxy, also",
        "called a star forest, is a graph whose connected components are stars.",
        "The undirected simple graph below has vertices numbered from 0 through",
        f"{inst['vertex_count'] - 1}. It has {inst['edge_count']} edges.",
        "",
        f"Each edge row is: u v tag slot.  Tags are {bits}-bit nonnegative",
        "integers printed in hexadecimal; slots are integers from 0 through",
        f"{bits - 1}. Edge order is irrelevant and no edge is repeated.",
        "",
        "Your answer is a bit mask M. Color an edge with",
        "    parity(M AND tag),",
        "where AND is bitwise conjunction and parity is the number of 1-bits",
        "modulo 2. The mask must have exactly the stated bit width: its top bit",
        f"must be 1, so 2^{bits - 1} <= M < 2^{bits}. Both resulting color",
        "classes must be galaxies. The verifier expands your rule over every",
        "edge and checks every connected component exactly. There are no open",
        "intervals, approximations, omitted edges, or indexing conventions.",
        "",
        "The listed probe vertex has degree bits+1. Its incident rows are copied",
        "before the complete table for convenience; they are not extra edges.",
        f"probe_vertex = {inst['probe_vertex']}",
        "probe_edges:",
    ]
    for u, v, tag, slot in inst["probe_edges"]:
        lines.append(f"  {u} {v} 0x{tag:0{width}x} {slot}")
    lines.extend(["", "complete_edge_table:"])
    for u, v, tag, slot in inst["edges"]:
        lines.append(f"  {u} {v} 0x{tag:0{width}x} {slot}")
    lines.extend(
        [
            "",
            "Give your final answer inside <answer></answer> tags as a JSON",
            "object with one decimal integer field named mask.",
            "Example: <answer>{\"mask\": 23}</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Extract the delimited JSON answer; return None on all malformed input."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer>\s*(.*?)\s*</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    try:
        value = json.loads(matches[-1])
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _prepare_instance(inst: dict) -> tuple[dict | None, str]:
    cached = _PREPARED_CACHE.get(id(inst))
    if cached is not None and cached[0] is inst:
        return cached[1], "ok"
    if not isinstance(inst, dict):
        return None, "instance_shape: instance must be an object"
    bits = inst.get("bits")
    vertex_count = inst.get("vertex_count")
    edges = inst.get("edges")
    if isinstance(bits, bool) or not isinstance(bits, int) or bits < 5 or bits > 96:
        return None, "instance_bits: invalid bit width"
    if isinstance(vertex_count, bool) or not isinstance(vertex_count, int) or vertex_count < 2:
        return None, "instance_vertices: invalid vertex count"
    if not isinstance(edges, list) or inst.get("edge_count") != len(edges):
        return None, "instance_edges: invalid edge table or count"
    graph_edges: list[tuple[int, int]] = []
    tags: list[int] = []
    slots: list[int] = []
    adjacency: list[list[int]] = [[] for _ in range(vertex_count)]
    seen_pairs: set[tuple[int, int]] = set()
    seen_tags: set[int] = set()
    for i, row in enumerate(edges):
        if not isinstance(row, list) or len(row) != 4:
            return None, f"instance_edge_shape: row {i} is not [u,v,tag,slot]"
        u, v, tag, slot = row
        if any(isinstance(x, bool) or not isinstance(x, int) for x in row):
            return None, f"instance_edge_type: row {i} contains a non-integer"
        if not (0 <= u < v < vertex_count):
            return None, f"instance_edge_range: row {i} has invalid endpoints"
        if not (0 <= tag < (1 << bits)):
            return None, f"instance_tag_range: row {i} has an invalid tag"
        if not (0 <= slot < bits):
            return None, f"instance_slot_range: row {i} has an invalid slot"
        if (u, v) in seen_pairs:
            return None, f"instance_duplicate_edge: row {i} repeats an edge"
        if tag in seen_tags:
            return None, f"instance_duplicate_tag: row {i} repeats a tag"
        seen_pairs.add((u, v))
        seen_tags.add(tag)
        graph_edges.append((u, v))
        tags.append(tag)
        slots.append(slot)
        adjacency[u].append(i)
        adjacency[v].append(i)
    if any(not row for row in adjacency):
        return None, "instance_isolate: every listed vertex must meet an edge"
    probe = inst.get("probe_vertex")
    probe_edges = inst.get("probe_edges")
    if isinstance(probe, bool) or not isinstance(probe, int) or not 0 <= probe < vertex_count:
        return None, "instance_probe: invalid probe vertex"
    expected_probe = sorted((edges[i] for i in adjacency[probe]), key=lambda row: (row[3], row[2]))
    if probe_edges != expected_probe or len(probe_edges) != bits + 1:
        return None, "instance_probe_rows: copied probe rows do not match the graph"

    # A deterministic prefix of actual simple length-three paths supplies a
    # sound quick-rejection filter. Full verification still follows survivors.
    quick: list[tuple[int, int, int]] = []
    for middle, (u, v) in enumerate(graph_edges):
        for left in adjacency[u]:
            if left == middle:
                continue
            a, b = graph_edges[left]
            outer_left = b if a == u else a
            for right in adjacency[v]:
                if right == middle or right == left:
                    continue
                a, b = graph_edges[right]
                outer_right = b if a == v else a
                if outer_left != outer_right and outer_left not in (u, v) and outer_right not in (u, v):
                    quick.append((left, middle, right))
                    if len(quick) >= 160:
                        break
            if len(quick) >= 160:
                break
        if len(quick) >= 160:
            break
    data = {
        "bits": bits,
        "vertex_count": vertex_count,
        "graph_edges": graph_edges,
        "tags": tags,
        "slots": slots,
        "adjacency": adjacency,
        "quick": quick,
    }
    _PREPARED_CACHE[id(inst)] = (inst, data)
    return data, "ok"


def _check_star_forests(data: dict, colors: list[int]) -> tuple[bool, str]:
    graph_edges = data["graph_edges"]
    adjacency = data["adjacency"]
    vertex_count = data["vertex_count"]
    for color in (0, 1):
        seen: set[int] = set()
        for start in range(vertex_count):
            if start in seen or not any(colors[e] == color for e in adjacency[start]):
                continue
            queue = [start]
            seen.add(start)
            vertices = []
            edge_twice = 0
            branching = 0
            while queue:
                u = queue.pop()
                vertices.append(u)
                degree = 0
                for edge_index in adjacency[u]:
                    if colors[edge_index] != color:
                        continue
                    degree += 1
                    a, b = graph_edges[edge_index]
                    v = b if a == u else a
                    if v not in seen:
                        seen.add(v)
                        queue.append(v)
                edge_twice += degree
                branching += int(degree > 1)
            edge_count = edge_twice // 2
            if edge_count != len(vertices) - 1:
                return False, f"galaxy_{color}_cycle: a component is not a tree"
            if branching > 1:
                return False, f"galaxy_{color}_centers: a component has more than one possible center"
    return True, "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Verify any valid bounded linear-form witness; never read inst['answer']."""
    if not isinstance(answer, dict):
        return False, "answer_type: expected a JSON object"
    keys = set(answer)
    if not keys:
        return False, "missing_both: expected exactly the mask field"
    if "mask" not in keys:
        return False, "missing_mask: the mask field is absent"
    if keys != {"mask"}:
        return False, "unexpected_fields: expected exactly one field named mask"
    mask = answer["mask"]
    if isinstance(mask, bool) or not isinstance(mask, int):
        return False, "mask_type: mask must be an integer"
    data, reason = _prepare_instance(inst)
    if data is None:
        return False, reason
    bits = data["bits"]
    if not ((1 << (bits - 1)) <= mask < (1 << bits)):
        return False, "mask_range: mask must have exactly the stated bit width"

    tags = data["tags"]
    for a, b, c in data["quick"]:
        value = _parity(mask & tags[a])
        if _parity(mask & tags[b]) == value and _parity(mask & tags[c]) == value:
            return False, "monochromatic_path: one color contains a four-vertex path"
    colors = [_parity(mask & tag) for tag in tags]
    if not colors or all(value == colors[0] for value in colors):
        return False, "empty_color: both galaxy classes must be nonempty"
    return _check_star_forests(data, colors)


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the stated top-bit-normalized mask language."""
    bits = inst["bits"]
    return {"mask": (1 << (bits - 1)) | rng.getrandbits(bits - 1)}


def search_space(inst: dict) -> int:
    return 1 << (inst["bits"] - 1)


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    top = 1 << (inst["bits"] - 1)
    return sum(verify(inst, {"mask": top | suffix})[0] for suffix in range(space))


def _vertex_signatures(inst: dict) -> list[tuple[tuple[int, int], ...]]:
    incident: list[list[tuple[int, int]]] = [[] for _ in range(inst["vertex_count"])]
    for u, v, tag, slot in inst["edges"]:
        incident[u].append((tag, slot))
        incident[v].append((tag, slot))
    return [tuple(sorted(row)) for row in incident]


def canonical_key(inst: dict) -> str:
    """Vertex-renaming and edge-order invariant key using unique edge tags."""
    signatures = _vertex_signatures(inst)
    edge_records = []
    for u, v, tag, slot in inst["edges"]:
        ends = sorted((signatures[u], signatures[v]))
        edge_records.append((ends[0], ends[1], tag, slot))
    payload = (inst["bits"], tuple(sorted(signatures)), tuple(sorted(edge_records)))
    return hashlib.sha256(repr(payload).encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the graph/decoy haystack while keeping the one-integer answer fixed."""
    n = int(params.get("n", 2))
    bits = int(params.get("bits", 64))
    if n < 32:
        return {"n": min(32, 2 * n), "bits": bits}
    return None


def _nullspace_one(rows: list[int], bits: int, counter: dict[str, int]) -> int | None:
    """Return the unique nonzero vector orthogonal to rows, or None."""
    work = list(rows)
    pivot_cols: list[int] = []
    rank = 0
    for col in range(bits):
        pivot = None
        for r in range(rank, len(work)):
            counter["row_tests"] += 1
            counter["bit_operations"] += 1
            if (work[r] >> col) & 1:
                pivot = r
                break
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        for r in range(len(work)):
            if r != rank:
                counter["row_tests"] += 1
                counter["bit_operations"] += 1
                if (work[r] >> col) & 1:
                    work[r] ^= work[rank]
                    counter["row_xors"] += 1
                    counter["bit_operations"] += bits
        pivot_cols.append(col)
        rank += 1
        if rank == len(work):
            break
    if rank != bits - 1:
        return None
    free = next((c for c in range(bits) if c not in set(pivot_cols)), None)
    if free is None:
        return None
    vector = 1 << free
    for row, pivot_col in zip(work[:rank], pivot_cols):
        counter["bit_operations"] += bits
        if _parity(row & vector):
            vector |= 1 << pivot_col
    return vector


def _reference_decode(inst: dict) -> tuple[object | None, dict[str, int]]:
    """Ignore slots: try every probe contaminant and solve a GF(2) nullspace."""
    counter = {"omissions": 0, "row_tests": 0, "row_xors": 0, "bit_operations": 0}
    rows = inst["probe_edges"]
    bits = inst["bits"]
    for omitted in range(len(rows)):
        counter["omissions"] += 1
        tags = [row[2] for i, row in enumerate(rows) if i != omitted]
        base = tags[0]
        differences = [tag ^ base for tag in tags[1:]]
        candidate = _nullspace_one(differences, bits, counter)
        if candidate is None or not ((candidate >> (bits - 1)) & 1):
            continue
        answer = {"mask": candidate}
        if verify(inst, answer)[0]:
            return answer, counter
    return None, counter


def _slot_decode_rows(rows: list[list[int]], bits: int, partial: int | None = None) -> int | None:
    by_slot: dict[int, list[int]] = {}
    for _, _, tag, slot in rows:
        by_slot.setdefault(slot, []).append(tag)
    if set(by_slot) != set(range(bits)) or sorted(map(len, by_slot.values())).count(2) != 1:
        return None
    duplicate = next(slot for slot, tags in by_slot.items() if len(tags) == 2)
    bases = by_slot[0] if duplicate == 0 else by_slot[0][:1]
    low_mask = (1 << (bits - 1)) - 1
    limit = bits if partial is None else min(bits, partial + 1)
    for base in bases:
        choices: dict[int, int] = {0: base}
        good = True
        for slot in range(1, limit):
            expected = 1 << (slot - 1)
            matches = [tag for tag in by_slot[slot] if ((tag ^ base) & low_mask) == expected]
            if len(matches) != 1:
                good = False
                break
            choices[slot] = matches[0]
        if not good:
            continue
        mask = 1 << (bits - 1)
        for slot in range(1, limit):
            if (choices[slot] ^ base) >> (bits - 1):
                mask |= 1 << (slot - 1)
        return mask
    return None


def _compact_decode(inst: dict) -> object | None:
    mask = _slot_decode_rows(inst["probe_edges"], inst["bits"])
    answer = {"mask": mask} if mask is not None else None
    return answer if answer is not None and verify(inst, answer)[0] else None


def _greedy_duplicate_mask_from_rows(rows: list[list[int]], bits: int) -> int | None:
    """Tempting but wrong: keep the smaller tag in the duplicated slot."""
    by_slot: dict[int, list[int]] = {}
    for _, _, tag, slot in rows:
        by_slot.setdefault(slot, []).append(tag)
    if set(by_slot) != set(range(bits)):
        return None
    chosen = []
    for slot in range(bits):
        chosen.append([0, 0, min(by_slot[slot]), slot])
    return _slot_decode_rows(chosen, bits)


def _attack_top_bit(inst: dict) -> object:
    return {"mask": 1 << (inst["bits"] - 1)}


def _attack_probe_majority(inst: dict) -> object:
    bits = inst["bits"]
    tags = [row[2] for row in inst["probe_edges"]]
    mask = 1 << (bits - 1)
    for bit in range(bits - 1):
        if sum((tag >> bit) & 1 for tag in tags) > len(tags) // 2:
            mask |= 1 << bit
    return {"mask": mask}


def _attack_low_slots(inst: dict) -> object:
    partial = _slot_decode_rows(inst["probe_edges"], inst["bits"], partial=8)
    if partial is None:
        partial = 1 << (inst["bits"] - 1)
    return {"mask": partial}


def _attack_greedy_duplicate(inst: dict) -> object:
    mask = _greedy_duplicate_mask_from_rows(inst["probe_edges"], inst["bits"])
    if mask is None:
        mask = 1 << (inst["bits"] - 1)
    return {"mask": mask}


def _relabel_instance(inst: dict, rng: random.Random) -> tuple[dict, object]:
    labels = list(range(inst["vertex_count"]))
    rng.shuffle(labels)
    rows = []
    for u, v, tag, slot in inst["edges"]:
        a, b = _norm_edge(labels[u], labels[v])
        rows.append([a, b, tag, slot])
    rng.shuffle(rows)
    transformed = {
        key: json.loads(json.dumps(value))
        for key, value in inst.items()
        if key not in ("edges", "probe_vertex", "probe_edges", "answer")
    }
    transformed["edges"] = rows
    transformed["probe_vertex"] = labels[inst["probe_vertex"]]
    transformed["probe_edges"] = sorted(
        (row[:] for row in rows if transformed["probe_vertex"] in row[:2]),
        key=lambda row: (row[3], row[2]),
    )
    carried = json.loads(json.dumps(inst["answer"]))
    transformed["answer"] = carried
    return transformed, carried


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest() -> dict:
    """Run all mandatory gates and return a JSON-native measured report."""
    started = time.perf_counter()
    report: dict[str, Any] = {
        "paper": "1312.5698",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 29):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed, "reason": "answer not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    inst = make_instance(n=3, bits=24, seed=404)
    planted = json.loads(json.dumps(inst["answer"]))
    corruptions = {
        "drop": {"constant": 0},
        "swap": {"mask": "not-an-integer"},
        "duplicate": {"mask": planted["mask"], "mask_copy": planted["mask"]},
        "empty": {},
        "out_of_range": {"mask": 1 << inst["bits"]},
    }
    corruption_results = {}
    reason_codes = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        reason_codes.append(reason.split(":", 1)[0])
    report["G2_rejects_corruption"] = {
        "pass": all(value["rejected"] for value in corruption_results.values())
        and len(set(reason_codes)) == 5,
        "cases": corruption_results,
        "distinct_reason_codes": len(set(reason_codes)),
    }

    encoded = json.dumps(inst["answer"], separators=(",", ":"))
    response = f"The parity rule is below.\n```json\n<answer>{encoded}</answer>\n```\nDone."
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0] and parse_answer("garbage") is None,
        "model_style_response_chars": len(response),
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    shipping = make_instance(seed=7701, **DIFFICULTY[SHIPPING_DIFFICULTY])
    verify(shipping, shipping["answer"])  # populate the validated-instance cache
    guess_rng = random.Random(99173)
    hits = 0
    for _ in range(_G4_SAMPLES):
        hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    density = hits / _G4_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6,
        "hits": hits,
        "total": _G4_SAMPLES,
        "estimated_probability": density,
        "candidate_space": search_space(shipping),
        "sampling_prior": "uniform over all bits-bit masks whose top bit is one",
    }

    baseline_start = time.perf_counter()
    decoded, baseline_counter = _reference_decode(shipping)
    baseline_sec = time.perf_counter() - baseline_start
    baseline_ok = decoded is not None and verify(shipping, decoded)[0]
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_exact = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": density < 1e-6 and baseline_ok and isinstance(demo_exact, int),
        "shipping_density_hits": hits,
        "shipping_density_samples": _G4_SAMPLES,
        "shipping_solution_fraction_estimate": density,
        "demo_exact_valid_count": demo_exact,
        "demo_candidate_space": search_space(demo),
        "baseline_wall_clock_sec": baseline_sec,
        "baseline_operations": baseline_counter["bit_operations"],
        "baseline_row_tests": baseline_counter["row_tests"],
        "baseline_row_xors": baseline_counter["row_xors"],
        "baseline_omissions": baseline_counter["omissions"],
        "baseline_verified": baseline_ok,
    }

    attack_counts = {
        "outlier_top_bit_only": 0,
        "greedy_probe_bit_majority": 0,
        "partial_first_eight_slots": 0,
        "greedy_smaller_duplicate_tag": 0,
        "random_restart_256": 0,
    }
    ref_successes = 0
    ref_operations = 0
    ref_omissions = 0
    compact_successes = 0
    ref_start = time.perf_counter()
    for seed in range(1200, 1200 + _ATTACK_SEEDS):
        trial = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        attack_counts["outlier_top_bit_only"] += int(verify(trial, _attack_top_bit(trial))[0])
        attack_counts["greedy_probe_bit_majority"] += int(verify(trial, _attack_probe_majority(trial))[0])
        attack_counts["partial_first_eight_slots"] += int(verify(trial, _attack_low_slots(trial))[0])
        attack_counts["greedy_smaller_duplicate_tag"] += int(verify(trial, _attack_greedy_duplicate(trial))[0])
        restart_rng = random.Random(seed ^ 0x5A17)
        restart_hit = False
        for _ in range(256):
            if verify(trial, random_candidate(trial, restart_rng))[0]:
                restart_hit = True
                break
        attack_counts["random_restart_256"] += int(restart_hit)
        reference, counter = _reference_decode(trial)
        ref_operations += counter["bit_operations"]
        ref_omissions += counter["omissions"]
        ref_successes += int(reference is not None and verify(trial, reference)[0])
        compact = _compact_decode(trial)
        compact_successes += int(compact is not None and verify(trial, compact)[0])
    ref_sec = time.perf_counter() - ref_start
    attacks = {
        name: {"successes": successes, "attempts": _ATTACK_SEEDS}
        for name, successes in attack_counts.items()
    }
    all_failed = all(value["successes"] == 0 for value in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_successes == _ATTACK_SEEDS and compact_successes == _ATTACK_SEEDS,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "probe contaminant enumeration plus exact GF(2) nullspace elimination",
            "complexity": "O(d^4 + m*d) scalar bit operations",
            "wall_clock_sec": ref_sec,
            "operations": ref_operations,
            "mean_operations": ref_operations / _ATTACK_SEEDS,
            "mean_omissions": ref_omissions / _ATTACK_SEEDS,
            "solves": f"{ref_successes}/{_ATTACK_SEEDS}, as expected",
        },
        "compact_slot_decoder": {
            "solves": f"{compact_successes}/{_ATTACK_SEEDS}, as expected",
            "declared_operations": 4 * DIFFICULTY[SHIPPING_DIFFICULTY]["bits"] + 1,
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=5150, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    sizes = [make_instance(seed=8, **params)["edge_count"] for params in DIFFICULTY.values()]
    report["G7_scales"] = {
        "pass": doubled_ok and sizes == sorted(sizes) and len(set(sizes)) == len(sizes),
        "preset_edge_counts": dict(zip(DIFFICULTY, sizes)),
        "doubled_n": doubled_params["n"],
        "doubled_edge_count": doubled["edge_count"],
        "doubled_verifies": doubled_ok,
        "reason": doubled_reason,
    }

    invariant_ok = 0
    carried_ok = 0
    original_keys = []
    for seed in range(20):
        original = make_instance(seed=9000 + seed, **DIFFICULTY["medium"])
        transformed, carried = _relabel_instance(original, random.Random(70000 + seed))
        original_key = canonical_key(original)
        transformed_key = canonical_key(transformed)
        original_keys.append(original_key)
        invariant_ok += int(original_key == transformed_key)
        carried_ok += int(verify(transformed, carried)[0])
    distinct = len(set(original_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_ok == 20 and carried_ok == 20 and distinct == 20,
        "relabel_invariant": invariant_ok,
        "relabel_attempts": 20,
        "carried_witness_verifies": carried_ok,
        "carried_attempts": 20,
        "distinct_unrelated_keys": distinct,
        "unrelated_attempts": 20,
        "transformations": "arbitrary vertex renaming composed with arbitrary edge-table reordering",
        "invariant": "unique-tag incidence signatures and tagged edge records",
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    intended_ops = 4 * shipping["bits"] + 1
    evidence = G9_MEASUREMENTS
    hinted_rate = evidence["hinted"]["solved"] / max(1, evidence["hinted"]["attempts"])
    placebo_rate = evidence["placebo"]["solved"] / max(1, evidence["placebo"]["attempts"])
    caps_ok = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": caps_ok,
        "arms": {
            "bare": evidence["bare"],
            "hinted": evidence["hinted"],
            "placebo": evidence["placebo"],
        },
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": evidence["hinted_verdict"],
        "placebo_verdict": evidence["placebo_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
    }

    gates = [value for key, value in report.items() if key.startswith("G") and isinstance(value, dict)]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    report["elapsed_sec"] = time.perf_counter() - started
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
