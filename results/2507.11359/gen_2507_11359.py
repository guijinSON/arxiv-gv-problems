"""Verified problem generator for arXiv:2507.11359.

The generated task is native to the paper: find a perfect matching in an
explicit sparse 3-uniform hypergraph.  Instances are inverse-generated from a
held perfect matching, so generation never solves the emitted instance.

This is honestly Track B.  Exact-cover backtracking and a polynomial scan of
the deliberately embedded affine label invariant both solve the family with
tools.  The benchmark asks whether a no-tool solver can notice the compact
invariant and write down the matching directly.

Only the Python standard library is used.  Generation is deterministic in
``(n, seed, params)`` and importing this module performs no I/O.
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
from collections import Counter
from typing import Any


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "explicit labelled 3-uniform hypergraph",
        "perfect matching as a set of hyperedge labels",
    ],
    "verification_operations": [
        "exact hyperedge-label lookup",
        "exact vertex-incidence counting",
        "integer equality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The labels of one perfect matching form an affine progression encoded "
        "by the first two displayed labels; without recognizing it one must solve "
        "the hypergraph exact-cover instance."
    ),
    "hardness_basis": (
        "Track B: Section 8 / Procedure 1 gives a polynomial-time lattice-based "
        "decision algorithm in the paper's dense-host sparsification regime, while "
        "the shipping instance is also solved by minimum-column Algorithm X and by "
        "an O((dn)^2 n) affine-progression scan (394,410 mean and 1,042,240 maximum "
        "modular steps over eight shipping seeds, 0.044 s mean); minimum-column "
        "Algorithm X used 174,384 nodes and 1.78 s mean, whereas the recognized "
        "two-anchor route uses 81 exact modular operations."
    ),
    "max_answer_tokens": 80,
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
        "An unordered set of exactly n distinct integer hyperedge labels drawn "
        "from the displayed degree*n labels; JSON stores it as a list."
    ),
    "bounds": {
        "selected_hyperedges": "n",
        "maximum_selected_hyperedges": 256,
        "available_hyperedges": "degree*n",
        "label_min": 0,
        "label_max": 1_000_002,
        "distinct": 1,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 4, "degree": 3, "mixing": 0},
    "easy": {"n": 40, "degree": 5, "mixing": 24},
    "medium": {"n": 40, "degree": 5, "mixing": 32},
    "hard": {"n": 40, "degree": 5, "mixing": 40},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT: str = (
    "The first two displayed labels and one perfect matching are linked by an "
    "affine invariant modulo the stated prime."
)
PLACEBO_HINT: str = (
    "The displayed labels and vertex triples reward careful bookkeeping under "
    "the stated indexing conventions."
)

NOTES: str = (
    "Section 1 defines a k-uniform hypergraph, a matching, and a perfect matching, "
    "and defines H_p by independently retaining host edges. The main result in "
    "Section 1 fixes the "
    "tractable regime delta>c*_(k,l), p>=C log(n)/n^(k-1), so this cannot honestly "
    "be Track A. Section 1.4 defines spread distributions; Section 8, especially "
    "Theorem 8.3 and Procedure 1, explains the lattice-solubility algorithm and "
    "its polynomial search for a constant-size preliminary matching. The paper "
    "also states that unrestricted k>=3 perfect matching is NP-complete, but that "
    "worst-case fact is not used as a claim about this generated distribution. "
    "The answer is sampled first as a random vertex partition. Decoy perfect-"
    "matching layers begin with the same distribution and are mixed by degree-"
    "preserving switches, leaving every vertex degree equal and every edge marginal "
    "symmetric. Numeric labels are assigned afterward; an invertible affine map "
    "makes planted and decoy labels marginally uniform. Local-overlap and numeric "
    "outliers, deterministic greedy packing, randomized greedy restarts, and an "
    "obvious but wrong progression ansatz are tested. Successful Algorithm X and "
    "the exhaustive affine scan are disclosed as Track B references."
)


_PRIME = 1_000_003
_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_SELFTEST_SEEDS = tuple(range(8))
_G4_SAMPLES = 200_000
_ENUMERATION_CAP = 1_000_000
_ALGORITHM_X_CAP = 2_000_000

# Filled after the three isolated harden.py runs.  These values are diagnostics;
# only the exact size/effort caps contribute to G9's pass flag.
_G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "hardened",
}


def _validate_params(n: int, degree: int, mixing: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or not 4 <= n <= 256:
        raise ValueError("n must be an integer in 4..256")
    if isinstance(degree, bool) or not isinstance(degree, int) or degree < 2:
        raise ValueError("degree must be an integer at least 2")
    if degree > math.comb(3 * n - 1, 2):
        raise ValueError("degree exceeds the number of triples through a vertex")
    if isinstance(mixing, bool) or not isinstance(mixing, int) or not 0 <= mixing <= 96:
        raise ValueError("mixing must be an integer in 0..96")
    if degree * n + 2 >= _PRIME:
        raise ValueError("too many hyperedges for distinct labels modulo the prime")


def _random_partition(vertex_count: int, rng: random.Random) -> list[tuple[int, int, int]]:
    vertices = list(range(vertex_count))
    rng.shuffle(vertices)
    return [
        tuple(sorted(vertices[i : i + 3]))
        for i in range(0, vertex_count, 3)
    ]


def _regular_hypergraph(
    n: int, degree: int, mixing: int, rng: random.Random
) -> tuple[list[tuple[int, int, int]], list[int]]:
    """Compose regular layers, retain layer zero, and mix only the decoys.

    Every initial layer is a perfect matching.  Endpoint switches preserve the
    degree sequence and simplicity, but usually destroy the decoy matchings.
    The held layer is never recovered by search.
    """

    vertex_count = 3 * n
    vertex_perm = list(range(vertex_count))
    rng.shuffle(vertex_perm)

    layers: list[list[tuple[int, int, int]]] = []
    used: set[tuple[int, int, int]] = set()
    for layer in range(degree):
        if layer < n:
            raw = [
                tuple(
                    sorted(
                        (
                            vertex_perm[i],
                            vertex_perm[n + ((i + layer) % n)],
                            vertex_perm[2 * n + ((i + 2 * layer) % n)],
                        )
                    )
                )
                for i in range(n)
            ]
        else:
            raw = []
            for _ in range(20_000):
                candidate = _random_partition(vertex_count, rng)
                if used.isdisjoint(candidate):
                    raw = candidate
                    break
            if not raw:
                raise RuntimeError("could not sample a fresh regular layer")
        if len(set(raw)) != n or not used.isdisjoint(raw):
            raise RuntimeError("regular-layer construction produced duplicate edges")
        layers.append(raw)
        used.update(raw)

    plant = list(layers[0])
    plant_set = set(plant)
    decoys = [edge for layer in layers[1:] for edge in layer]
    decoy_set = set(decoys)

    switch_target = mixing * len(decoys)
    accepted = 0
    attempts = 0
    attempt_cap = max(1_000, 30 * switch_target)
    while accepted < switch_target and attempts < attempt_cap and len(decoys) >= 2:
        attempts += 1
        i, j = rng.sample(range(len(decoys)), 2)
        e1, e2 = decoys[i], decoys[j]
        if not set(e1).isdisjoint(e2):
            continue
        a = rng.randrange(3)
        b = rng.randrange(3)
        ne1_list = list(e1)
        ne2_list = list(e2)
        ne1_list[a], ne2_list[b] = ne2_list[b], ne1_list[a]
        ne1 = tuple(sorted(ne1_list))
        ne2 = tuple(sorted(ne2_list))
        if ne1 == ne2 or ne1 in plant_set or ne2 in plant_set:
            continue
        decoy_set.remove(e1)
        decoy_set.remove(e2)
        if ne1 in decoy_set or ne2 in decoy_set:
            decoy_set.add(e1)
            decoy_set.add(e2)
            continue
        decoys[i], decoys[j] = ne1, ne2
        decoy_set.add(ne1)
        decoy_set.add(ne2)
        accepted += 1
    if accepted < switch_target:
        raise RuntimeError("could not complete requested degree-preserving mixing")

    edges = plant + decoys
    order = list(range(len(edges)))
    rng.shuffle(order)
    old_to_new = {old: new for new, old in enumerate(order)}
    shuffled_edges = [edges[old] for old in order]
    planted_indices = [old_to_new[i] for i in range(n)]
    return shuffled_edges, planted_indices


def _assign_labels(
    edge_count: int, planted_indices: list[int], n: int, rng: random.Random
) -> tuple[list[int], list[int], list[int]]:
    """Assign marginally uniform labels and return labels, display order, answer."""

    while True:
        anchor_a = rng.randrange(_PRIME)
        anchor_b = rng.randrange(_PRIME)
        start = (anchor_a + anchor_b) % _PRIME
        step = (anchor_a - anchor_b) % _PRIME
        if step == 0:
            continue
        progression = [(start + i * step) % _PRIME for i in range(n)]
        if len(set(progression)) != n:
            continue
        if anchor_a not in progression and anchor_b not in progression:
            break

    planted_set = set(planted_indices)
    labels: list[int | None] = [None] * edge_count
    progression_order = progression[:]
    shuffled_progression = progression[:]
    rng.shuffle(shuffled_progression)
    for edge_index, label in zip(planted_indices, shuffled_progression):
        labels[edge_index] = label

    available_decoy_indices = [i for i in range(edge_count) if i not in planted_set]
    rng.shuffle(available_decoy_indices)
    anchor_indices = available_decoy_indices[:2]
    labels[anchor_indices[0]] = anchor_a
    labels[anchor_indices[1]] = anchor_b

    used = set(progression)
    used.update((anchor_a, anchor_b))
    for edge_index in available_decoy_indices[2:]:
        while True:
            label = rng.randrange(_PRIME)
            if label not in used:
                used.add(label)
                labels[edge_index] = label
                break

    if any(label is None for label in labels):
        raise RuntimeError("not every hyperedge received a label")
    final_labels = [int(label) for label in labels]
    remaining = [i for i in range(edge_count) if i not in anchor_indices]
    rng.shuffle(remaining)
    display_order = anchor_indices + remaining
    return final_labels, display_order, progression_order


def make_instance(
    n: int, seed: int = 0, degree: int = 5, mixing: int = 24, **params: Any
) -> dict:
    """Inverse-generate a labelled 3-graph and a perfect-matching witness."""

    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, degree, mixing)
    rng = random.Random(seed)
    edges, planted_indices = _regular_hypergraph(n, degree, mixing, rng)
    labels, display_order, answer = _assign_labels(
        len(edges), planted_indices, n, rng
    )
    hyperedges = [
        {"label": labels[index], "vertices": list(edges[index])}
        for index in display_order
    ]
    return {
        "family": "perfect matching in a sparse 3-uniform hypergraph",
        "n": n,
        "vertex_count": 3 * n,
        "degree": degree,
        "mixing": mixing,
        "prime": _PRIME,
        "hyperedges": hyperedges,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the full standalone problem and its exact output contract."""

    lines = [
        "Find a perfect matching in the labelled 3-uniform hypergraph below.",
        "",
        "Definitions: a 3-uniform hypergraph has vertices and hyperedges, with",
        "every hyperedge containing exactly three distinct vertices. A matching is",
        "a set of pairwise vertex-disjoint hyperedges. It is perfect when every",
        "vertex belongs to exactly one selected hyperedge.",
        "",
        f"The vertices are the integers 0 through {inst['vertex_count'] - 1}, inclusive.",
        f"There are {len(inst['hyperedges'])} hyperedges, each with a distinct integer label.",
        f"A perfect matching therefore contains exactly {inst['n']} hyperedges.",
        "Hyperedge order and the order of its three vertices have no mathematical",
        "effect. Hyperedge labels are residues modulo the displayed prime, written",
        "as their unique integers from 0 through prime-1; labels identify edges but",
        "only vertex incidence determines whether a proposed set is a matching.",
        "Answer order does not matter, repeats are",
        "forbidden, and every stated range is inclusive.",
        "",
        f"prime = {inst['prime']}",
        "Hyperedges, one per line as `label: vertex vertex vertex`:",
    ]
    lines.extend(
        f"{edge['label']}: " + " ".join(map(str, edge["vertices"]))
        for edge in inst["hyperedges"]
    )
    lines.extend(
        [
            "",
            f"Give exactly {inst['n']} distinct hyperedge labels, separated by commas.",
            "Give your final answer inside <answer></answer> tags, as a comma-separated list of integers.",
            "Example format only: <answer>12, 47, 105</answer>",
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
    """Parse a comma list from tags, tolerating prose and Markdown fences."""

    if not isinstance(text, str):
        return None
    tagged = _ANSWER_RE.findall(text)
    if tagged:
        body = tagged[-1].strip()
    else:
        brackets = re.findall(r"\[\s*-?\d+(?:\s*,\s*-?\d+)*\s*\]", text, re.S)
        if not brackets:
            return None
        body = brackets[-1][1:-1].strip()
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1].strip()
    if not body or not re.fullmatch(r"-?\d+(?:\s*,\s*-?\d+)*", body):
        return None
    try:
        return [int(piece.strip()) for piece in body.split(",")]
    except (TypeError, ValueError):
        return None


def _edge_map(inst: dict) -> dict[int, tuple[int, int, int]]:
    return {
        edge["label"]: tuple(edge["vertices"])
        for edge in inst["hyperedges"]
    }


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any perfect matching exactly, never consulting ``inst['answer']``."""

    if not isinstance(answer, list) or any(
        isinstance(value, bool) or not isinstance(value, int) for value in answer
    ):
        return False, "answer must be a list of integer hyperedge labels"
    if not answer:
        return False, "empty answer"
    if len(set(answer)) != len(answer):
        return False, "duplicate hyperedge labels are forbidden"
    edges = _edge_map(inst)
    if any(label not in edges for label in answer):
        return False, "unknown hyperedge label"
    if len(answer) != inst["n"]:
        return False, f"wrong number of hyperedges: expected {inst['n']}"
    counts = [0] * inst["vertex_count"]
    for label in answer:
        for vertex in edges[label]:
            counts[vertex] += 1
    bad = next((i for i, count in enumerate(counts) if count != 1), None)
    if bad is not None:
        return False, f"vertex {bad} has coverage {counts[bad]}, expected 1"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the statement-implied fixed-cardinality label sets."""

    labels = [edge["label"] for edge in inst["hyperedges"]]
    return rng.sample(labels, inst["n"])


def search_space(inst: dict) -> int | None:
    return math.comb(len(inst["hyperedges"]), inst["n"])


def _is_matching_fast(
    inst: dict, candidate: list[int], edge_map: dict[int, tuple[int, int, int]] | None = None
) -> bool:
    if len(candidate) != inst["n"] or len(set(candidate)) != len(candidate):
        return False
    if edge_map is None:
        edge_map = _edge_map(inst)
    covered = 0
    for label in candidate:
        vertices = edge_map.get(label)
        if vertices is None:
            return False
        mask = sum(1 << vertex for vertex in vertices)
        if covered & mask:
            return False
        covered |= mask
    return covered.bit_count() == inst["vertex_count"]


def enumerate_all(inst: dict) -> int | None:
    """Count every perfect matching only when the bounded language is small."""

    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    labels = [edge["label"] for edge in inst["hyperedges"]]
    edge_map = _edge_map(inst)
    return sum(
        _is_matching_fast(inst, list(candidate), edge_map)
        for candidate in itertools.combinations(labels, inst["n"])
    )


def _intersection_data(
    inst: dict,
) -> tuple[list[set[int]], dict[tuple[int, int], int]]:
    triples = [set(edge["vertices"]) for edge in inst["hyperedges"]]
    adjacency = [set() for _ in triples]
    weights: dict[tuple[int, int], int] = {}
    for i in range(len(triples)):
        for j in range(i + 1, len(triples)):
            weight = len(triples[i] & triples[j])
            if weight:
                adjacency[i].add(j)
                adjacency[j].add(i)
                weights[(i, j)] = weight
    return adjacency, weights


def canonical_key(inst: dict) -> str:
    """A strong cheap invariant of the unlabelled 3-uniform hypergraph.

    Exact hypergraph canonical labelling is not known to be cheap.  This ignores
    edge labels and applies weighted colour refinement to the edge-intersection
    graph.  It is invariant under vertex relabelling, hyperedge reordering,
    within-edge reordering, and arbitrary bijective renaming of edge labels.
    """

    triples = [tuple(sorted(edge["vertices"])) for edge in inst["hyperedges"]]
    adjacency, weights = _intersection_data(inst)
    multiplicity = Counter(triples)
    local_triangles: list[int] = []
    initial = []
    for i, neighbors in enumerate(adjacency):
        ordered = sorted(neighbors)
        triangles = 0
        for pos, a in enumerate(ordered):
            triangles += sum(b in adjacency[a] for b in ordered[pos + 1 :])
        local_triangles.append(triangles)
        weight_hist = Counter(weights[(min(i, j), max(i, j))] for j in neighbors)
        initial.append(
            (multiplicity[triples[i]], tuple(sorted(weight_hist.items())), triangles)
        )

    palette = {signature: i for i, signature in enumerate(sorted(set(initial)))}
    colors = [palette[signature] for signature in initial]
    for _ in range(len(triples) + 1):
        signatures = []
        for i, neighbors in enumerate(adjacency):
            neighborhood = tuple(
                sorted(
                    (weights[(min(i, j), max(i, j))], colors[j])
                    for j in neighbors
                )
            )
            signatures.append((colors[i], neighborhood))
        palette = {
            signature: i for i, signature in enumerate(sorted(set(signatures)))
        }
        refined = [palette[signature] for signature in signatures]
        if refined == colors:
            break
        colors = refined

    color_counts = sorted(Counter(colors).items())
    edge_counts = Counter()
    for (i, j), weight in weights.items():
        a, b = sorted((colors[i], colors[j]))
        edge_counts[(a, b, weight)] += 1
    profiles = sorted(
        (
            colors[i],
            local_triangles[i],
            tuple(
                sorted(
                    (weights[(min(i, j), max(i, j))], colors[j])
                    for j in adjacency[i]
                )
            ),
        )
        for i in range(len(triples))
    )
    payload = {
        "vertices": inst["vertex_count"],
        "hyperedges": len(triples),
        "color_counts": color_counts,
        "intersection_counts": sorted((list(key), value) for key, value in edge_counts.items()),
        "profiles": profiles,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Increase crowding/mixing first, preserving answer length."""

    if not isinstance(params, dict) or "n" not in params:
        return None
    n = params["n"]
    degree = params.get("degree", 5)
    mixing = params.get("mixing", 24)
    if mixing < 48:
        return {"n": n, "degree": degree, "mixing": min(48, mixing + 8)}
    if degree < 9:
        return {"n": n, "degree": degree + 1, "mixing": mixing}
    if n < 240:
        return {"n": min(240, n + 16), "degree": degree, "mixing": mixing}
    return "cap_bound"


def _incidence_masks(inst: dict) -> tuple[list[int], list[list[int]], list[int], int]:
    labels = [edge["label"] for edge in inst["hyperedges"]]
    masks = [sum(1 << v for v in edge["vertices"]) for edge in inst["hyperedges"]]
    incident = [[] for _ in range(inst["vertex_count"])]
    for edge_index, edge in enumerate(inst["hyperedges"]):
        for vertex in edge["vertices"]:
            incident[vertex].append(edge_index)
    return masks, incident, labels, (1 << inst["vertex_count"]) - 1


def _mrv_options(
    covered: int, incident: list[list[int]], masks: list[int], full: int
) -> list[int]:
    remaining = full ^ covered
    best: list[int] | None = None
    while remaining:
        bit = remaining & -remaining
        vertex = bit.bit_length() - 1
        remaining -= bit
        options = [index for index in incident[vertex] if not masks[index] & covered]
        if not options:
            return []
        if best is None or len(options) < len(best):
            best = options
            if len(best) == 1:
                break
    return best or []


def _greedy_candidate(inst: dict, rng: random.Random | None = None) -> list[int] | None:
    masks, incident, labels, full = _incidence_masks(inst)
    covered = 0
    chosen: list[int] = []
    for _ in range(inst["n"]):
        options = _mrv_options(covered, incident, masks, full)
        if not options:
            return None
        if rng is None:
            def score(index: int) -> tuple[int, int]:
                damage = sum(
                    bool(masks[index] & masks[other])
                    for other in range(len(masks))
                    if not masks[other] & covered
                )
                return damage, labels[index]
            selected = min(options, key=score)
        else:
            selected = rng.choice(options)
        chosen.append(labels[selected])
        covered |= masks[selected]
    return chosen if covered == full else None


def _random_restart(inst: dict, restarts: int, seed: int) -> list[int] | None:
    rng = random.Random(seed)
    for _ in range(restarts):
        candidate = _greedy_candidate(inst, rng)
        if candidate is not None and verify(inst, candidate)[0]:
            return candidate
    return None


def _algorithm_x(
    inst: dict, node_cap: int = _ALGORITHM_X_CAP
) -> tuple[list[int] | None, int, bool]:
    """Minimum-column Algorithm X; never called during generation."""

    masks, incident, labels, full = _incidence_masks(inst)
    nodes = 0
    capped = False

    def search(covered: int, chosen: list[int]) -> list[int] | None:
        nonlocal nodes, capped
        if nodes >= node_cap:
            capped = True
            return None
        nodes += 1
        if covered == full:
            return chosen
        options = _mrv_options(covered, incident, masks, full)
        if not options:
            return None
        for index in options:
            found = search(covered | masks[index], chosen + [labels[index]])
            if found is not None:
                return found
            if capped:
                return None
        return None

    found = search(0, [])
    return found, nodes, capped


def _affine_scan(inst: dict) -> tuple[list[int] | None, int]:
    """Try every ordered label pair as the first two terms of a progression."""

    labels = [edge["label"] for edge in inst["hyperedges"]]
    label_set = set(labels)
    operations = 0
    for start in labels:
        for second in labels:
            if second == start:
                continue
            step = (second - start) % inst["prime"]
            value = start
            candidate: list[int] = []
            complete = True
            for _ in range(inst["n"]):
                operations += 1
                candidate.append(value)
                if value not in label_set:
                    complete = False
                value = (value + step) % inst["prime"]
            if complete and verify(inst, candidate)[0]:
                return candidate, operations
    return None, operations


def _compact_invariant_candidate(inst: dict) -> tuple[list[int], int]:
    first = inst["hyperedges"][0]["label"]
    second = inst["hyperedges"][1]["label"]
    start = (first + second) % inst["prime"]
    step = (first - second) % inst["prime"]
    answer = [(start + i * step) % inst["prime"] for i in range(inst["n"])]
    # One addition and one subtraction for the anchors, then one multiply/add
    # per subsequent term (or equivalent repeated modular addition).
    return answer, 2 * inst["n"] + 1


def _wrong_first_pair_progression(inst: dict) -> list[int]:
    start = inst["hyperedges"][0]["label"]
    second = inst["hyperedges"][1]["label"]
    step = (second - start) % inst["prime"]
    return [(start + i * step) % inst["prime"] for i in range(inst["n"])]


def _local_overlap_outlier(inst: dict) -> list[int]:
    adjacency, _ = _intersection_data(inst)
    scored = []
    for i, neighbors in enumerate(adjacency):
        ordered = sorted(neighbors)
        triangles = 0
        for pos, a in enumerate(ordered):
            triangles += sum(b in adjacency[a] for b in ordered[pos + 1 :])
        scored.append((triangles, len(neighbors), inst["hyperedges"][i]["label"], i))
    scored.sort()
    chosen: list[int] = []
    occupied: set[int] = set()
    for _triangles, _degree, label, index in scored:
        vertices = inst["hyperedges"][index]["vertices"]
        if occupied.isdisjoint(vertices):
            chosen.append(label)
            occupied.update(vertices)
    return chosen


def _numeric_gap_outlier(inst: dict) -> list[int]:
    labels = sorted(edge["label"] for edge in inst["hyperedges"])
    scored = []
    for i, label in enumerate(labels):
        left = (label - labels[i - 1]) % inst["prime"]
        right = (labels[(i + 1) % len(labels)] - label) % inst["prime"]
        scored.append((min(left, right), max(left, right), label))
    scored.sort(reverse=True)
    return [label for _a, _b, label in scored[: inst["n"]]]


def _answer_sizes(answer: object) -> tuple[int, int, int]:
    blob = json.dumps(answer)

    def atoms(value: object) -> int:
        if isinstance(value, dict):
            return sum(atoms(child) for child in value.values())
        if isinstance(value, (list, tuple)):
            return sum(atoms(child) for child in value)
        return 1

    return len(blob), math.ceil(len(blob) / 4), atoms(answer)


def _transform_instance(
    inst: dict,
    rng: random.Random,
    *,
    relabel_vertices: bool,
    reorder_edges: bool,
    reorder_within_edges: bool,
    relabel_edges: bool,
) -> tuple[dict, list[int]]:
    vertex_map = list(range(inst["vertex_count"]))
    if relabel_vertices:
        rng.shuffle(vertex_map)

    labels = [edge["label"] for edge in inst["hyperedges"]]
    label_map = {label: label for label in labels}
    if relabel_edges:
        shuffled = labels[:]
        rng.shuffle(shuffled)
        label_map = dict(zip(labels, shuffled))

    edges = []
    for edge in inst["hyperedges"]:
        vertices = [vertex_map[v] for v in edge["vertices"]]
        if reorder_within_edges:
            rng.shuffle(vertices)
        edges.append({"label": label_map[edge["label"]], "vertices": vertices})
    if reorder_edges:
        rng.shuffle(edges)

    transformed = {
        key: value
        for key, value in inst.items()
        if key not in {"hyperedges", "answer"}
    }
    transformed["hyperedges"] = edges
    carried = [label_map[label] for label in inst["answer"]]
    transformed["answer"] = carried
    return transformed, carried


def selftest() -> dict:
    """Run gates G1--G9 and return all measurements as a JSON-native dict."""

    report: dict[str, Any] = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "problem_profile": PROBLEM_PROFILE,
    }

    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=17, **shipping)
    answer = list(inst["answer"])
    answer_set = set(answer)
    replacement = next(
        edge["label"] for edge in inst["hyperedges"] if edge["label"] not in answer_set
    )
    corruptions = {
        "drop_one": answer[:-1],
        "swap_one_for_decoy": answer[:-1] + [replacement],
        "duplicate_one": answer[:-1] + [answer[0]],
        "empty": [],
        "unknown_label": answer[:-1] + [_PRIME + 7],
    }
    corruption_rows = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_rows[name] = {"accepted": ok, "reason": reason}
    reasons = [row["reason"] for row in corruption_rows.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not row["accepted"] for row in corruption_rows.values())
        and len(set(reasons)) == len(reasons),
        "corruptions": corruption_rows,
    }

    wire = ", ".join(map(str, answer))
    model_style = (
        "I checked that the chosen hyperedges cover each vertex once.\n"
        f"```text\n<answer>{wire}</answer>\n```\n"
    )
    parsed = parse_answer(model_style)
    json_native = json.loads(json.dumps(answer)) == answer
    report["G3_round_trip"] = {
        "pass": parsed == answer and json_native,
        "model_style_parsed": parsed == answer,
        "json_native": json_native,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    sample_rng = random.Random(0x250711359)
    sample_hits = 0
    edge_map = _edge_map(inst)
    for _ in range(_G4_SAMPLES):
        candidate = random_candidate(inst, sample_rng)
        if _is_matching_fast(inst, candidate, edge_map):
            sample_hits += 1
    guess_probability = sample_hits / _G4_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": sample_hits,
        "total": _G4_SAMPLES,
        "observed_probability": guess_probability,
        "structure_aware_space": search_space(inst),
        "prior": "uniform over all n-subsets of the displayed hyperedge labels",
    }

    start_time = time.perf_counter()
    algorithm_x_answer, algorithm_x_nodes, algorithm_x_capped = _algorithm_x(inst)
    algorithm_x_wall = time.perf_counter() - start_time
    algorithm_x_ok = (
        not algorithm_x_capped
        and algorithm_x_answer is not None
        and verify(inst, algorithm_x_answer)[0]
    )
    start_time = time.perf_counter()
    scan_answer, scan_operations = _affine_scan(inst)
    scan_wall = time.perf_counter() - start_time
    scan_ok = scan_answer is not None and verify(inst, scan_answer)[0]
    compact_answer, compact_operations = _compact_invariant_candidate(inst)
    compact_ok = verify(inst, compact_answer)[0]
    demo_inst = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    report["G5_density_and_baseline_cost"] = {
        "pass": algorithm_x_ok and scan_ok and compact_ok,
        "shipping_density_hits": sample_hits,
        "shipping_density_samples": _G4_SAMPLES,
        "shipping_solution_fraction_estimate": guess_probability,
        "shipping_candidate_count": search_space(inst),
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo_inst),
        "baseline_algorithm": "minimum-column Algorithm X exact-cover search",
        "baseline_wall_seconds": round(algorithm_x_wall, 6),
        "baseline_search_nodes": algorithm_x_nodes,
        "baseline_solved": algorithm_x_ok,
        "affine_scan_wall_seconds": round(scan_wall, 6),
        "affine_scan_operations": scan_operations,
        "affine_scan_solved": scan_ok,
        "compact_route_operations": compact_operations,
        "compact_route_solved": compact_ok,
    }

    attack_names = (
        "local_intersection_outlier",
        "numeric_gap_outlier",
        "greedy_mrv_min_damage",
        "random_restart_mrv_256",
        "obvious_first_pair_progression",
    )
    attack_successes = {name: 0 for name in attack_names}
    algorithm_x_successes = 0
    algorithm_x_nodes_all: list[int] = []
    algorithm_x_times: list[float] = []
    scan_successes = 0
    scan_ops_all: list[int] = []
    scan_times: list[float] = []
    compact_successes = 0
    compact_ops_all: list[int] = []
    for offset, seed in enumerate(_SELFTEST_SEEDS):
        trial = make_instance(seed=10_000 + seed, **shipping)
        candidates = {
            "local_intersection_outlier": _local_overlap_outlier(trial),
            "numeric_gap_outlier": _numeric_gap_outlier(trial),
            "greedy_mrv_min_damage": _greedy_candidate(trial),
            "random_restart_mrv_256": _random_restart(
                trial, 256, 700_000 + offset
            ),
            "obvious_first_pair_progression": _wrong_first_pair_progression(trial),
        }
        for name, candidate in candidates.items():
            attack_successes[name] += int(
                candidate is not None and verify(trial, candidate)[0]
            )

        start_time = time.perf_counter()
        found, nodes, capped = _algorithm_x(trial)
        algorithm_x_times.append(time.perf_counter() - start_time)
        algorithm_x_nodes_all.append(nodes)
        algorithm_x_successes += int(
            not capped and found is not None and verify(trial, found)[0]
        )

        start_time = time.perf_counter()
        found, operations = _affine_scan(trial)
        scan_times.append(time.perf_counter() - start_time)
        scan_ops_all.append(operations)
        scan_successes += int(found is not None and verify(trial, found)[0])

        compact, operations = _compact_invariant_candidate(trial)
        compact_ops_all.append(operations)
        compact_successes += int(verify(trial, compact)[0])

    attacks = {
        name: {"successes": count, "attempts": len(_SELFTEST_SEEDS)}
        for name, count in attack_successes.items()
    }
    reference_success = (
        algorithm_x_successes == len(_SELFTEST_SEEDS)
        and scan_successes == len(_SELFTEST_SEEDS)
        and compact_successes == len(_SELFTEST_SEEDS)
    )
    report["G6_adversary_panel"] = {
        "pass": all(row["successes"] == 0 for row in attacks.values())
        and reference_success,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "minimum-column Algorithm X exact-cover search",
            "complexity": "O(degree^n) worst case with minimum-column branching",
            "wall_clock_sec_mean": round(
                sum(algorithm_x_times) / len(algorithm_x_times), 6
            ),
            "wall_clock_sec_max": round(max(algorithm_x_times), 6),
            "operations": round(sum(algorithm_x_nodes_all) / len(algorithm_x_nodes_all)),
            "nodes_total": sum(algorithm_x_nodes_all),
            "nodes_max": max(algorithm_x_nodes_all),
            "solves": f"{algorithm_x_successes}/{len(_SELFTEST_SEEDS)}, as expected",
        },
        "construction_aware_reference": {
            "name": "full ordered-pair affine-progression scan",
            "complexity": "O((degree*n)^2*n) exact modular operations",
            "wall_clock_sec_mean": round(sum(scan_times) / len(scan_times), 6),
            "wall_clock_sec_max": round(max(scan_times), 6),
            "operations_mean": round(sum(scan_ops_all) / len(scan_ops_all)),
            "operations_max": max(scan_ops_all),
            "solves": f"{scan_successes}/{len(_SELFTEST_SEEDS)}, as expected",
        },
        "intended_compact_route": {
            "name": "two-anchor affine invariant",
            "complexity": "O(n) exact modular operations after recognizing the invariant",
            "operations": compact_ops_all[0]
            if len(set(compact_ops_all)) == 1
            else compact_ops_all,
            "solves": f"{compact_successes}/{len(_SELFTEST_SEEDS)}, as expected",
        },
    }

    doubled = make_instance(
        n=2 * shipping["n"],
        degree=shipping["degree"],
        mixing=shipping["mixing"],
        seed=91_337,
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    escalated_params = escalate(dict(shipping))
    escalated_ok = False
    if isinstance(escalated_params, dict):
        escalated_inst = make_instance(seed=91_338, **escalated_params)
        escalated_ok = verify(escalated_inst, escalated_inst["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and escalated_ok,
        "base_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_reason": doubled_reason,
        "escalated_params": escalated_params,
        "escalated_verifies": escalated_ok,
        "fixed_answer_axis": "mixing, then degree",
    }

    invariance_checks = 0
    transformation_checks = 0
    distinct_keys = []
    g8_failures = []
    for seed in range(20):
        base = make_instance(seed=20_000 + seed, **shipping)
        base_key = canonical_key(base)
        distinct_keys.append(base_key)
        rng = random.Random(30_000 + seed)

        transformed, carried = _transform_instance(
            base,
            rng,
            relabel_vertices=True,
            reorder_edges=True,
            reorder_within_edges=True,
            relabel_edges=False,
        )
        invariance_checks += 1
        if canonical_key(transformed) != base_key:
            g8_failures.append({"seed": seed, "transform": "vertex+orders"})
        transformation_checks += 1
        if not verify(transformed, base["answer"])[0]:
            g8_failures.append({"seed": seed, "transform": "original answer"})

        transformed2, carried2 = _transform_instance(
            base,
            rng,
            relabel_vertices=True,
            reorder_edges=True,
            reorder_within_edges=True,
            relabel_edges=True,
        )
        invariance_checks += 1
        if canonical_key(transformed2) != base_key:
            g8_failures.append({"seed": seed, "transform": "all relabellings"})
        transformation_checks += 1
        if carried2 != transformed2["answer"] or not verify(transformed2, carried2)[0]:
            g8_failures.append({"seed": seed, "transform": "carried answer"})

    distinct_count = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_count == 20,
        "invariance_checks": invariance_checks,
        "transformation_validity_checks": transformation_checks,
        "unrelated_distinct": distinct_count,
        "unrelated_attempts": 20,
        "failures": g8_failures,
        "caveat": (
            "weighted color refinement is a strong cheap invariant, not a complete "
            "canonical form for 3-uniform hypergraph isomorphism"
        ),
    }

    worst_answer = make_instance(seed=99, **shipping)["answer"]
    answer_chars, answer_tokens, answer_elements = _answer_sizes(worst_answer)
    hinted = _G9_RESULTS["arms"]["hinted"]
    placebo = _G9_RESULTS["arms"]["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    intended_operations = 2 * shipping["n"] + 1
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": _G9_RESULTS["arms"],
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }
    PROBLEM_PROFILE["max_answer_tokens"] = answer_tokens

    gate_rows = [
        value
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    ]
    report["all_passed"] = all(row.get("pass") is True for row in gate_rows)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
