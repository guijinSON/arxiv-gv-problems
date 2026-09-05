"""Verified Track-B generator for Delta-1 coloring of claw-free line graphs.

The paper works directly with a multigraph H and its line graph L(H) in
Section 6.  Here H is a disjoint union of cycles whose links have multiplicity
four.  Thus every vertex of H has degree 8, every vertex of L(H) has degree 11,
and L(H) is claw-free with no K_11.  A proper 10-edge-coloring of H is exactly
a proper (Delta-1)-vertex-coloring of L(H).

Certificates are composed, never discovered: adjacent four-edge bundles are
given disjoint four-color sets.  Even quotient cycles alternate two sets; odd
cycles use the same alternation followed by a fixed five-set closing identity.
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
from typing import Any


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "8-regular multigraph",
        "four-edge parallel bundles",
        "claw-free line graph",
        "proper Delta-1 coloring",
    ],
    "verification_operations": [
        "exact edge-endpoint incidence",
        "integer palette membership",
        "exact comparison of colors on incident edges",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 6, definition used throughout and Theorem 6.1: vertices of "
        "the line graph are the multigraph edges, with adjacency exactly when "
        "two edges share an endpoint"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Parallel-edge twin classes contract to disjoint cycles; without that "
        "decomposition one faces the randomly relabelled line-graph coloring CSP."
    ),
    "hardness_basis": (
        "Track B: under Theorems 5.5 and 6.6's Delta=11, delta(H)=8 regime, "
        "cycle-CSP dynamic programming over the 210 four-subsets of a 10-color "
        "palette runs in O(n*C(10,4)*C(6,4)); eight hard-preset runs took 0.425 "
        "seconds total and at most 220,134 counted operations, versus 236 color "
        "placements for the compact quotient-cycle identity."
    ),
    "max_answer_tokens": 296,
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
        "One allowed integer color label for every edge id, in increasing edge-id "
        "order.  Each displayed four-edge parallel bundle must receive four "
        "distinct labels; the remaining incidence constraints are the substance "
        "of the problem."
    ),
    "bounds": {
        "palette_size": 10,
        "parallel_bundle_size": 4,
        "candidate_rule": "four distinct palette labels per displayed bundle",
        "shipping_max_edges": 256,
    },
}

DIFFICULTY = {
    "demo": {"n": 5, "max_components": 1},
    "easy": {"n": 39, "max_components": 5},
    "medium": {"n": 49, "max_components": 6},
    "hard": {"n": 59, "max_components": 7},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The four parallel edges in each bundle are twins, and the bundle-incidence quotient is a disjoint union of cycles."
)
PLACEBO_HINT = (
    "The edge identifiers are deliberately unordered, so careful bookkeeping helps prevent transcription mistakes."
)

# Filled from the three script-owned hardening runs after the shipping preset is
# known.  G9(a,b) is diagnostic; only the size/effort cap in G9(c) gates.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not run",
    "placebo_verdict": "not run",
}

NOTES = r"""
Paper grounding and Step 0.  Section 1 states Theorem 5.5: a claw-free graph
with chi >= Delta >= 9 contains K_Delta, equivalently a claw-free graph with
no K_Delta has a (Delta-1)-coloring.  Section 6 uses the paper-native pair H
and L(H), and Theorem 6.1 gives the line-graph case.  Theorem 6.6 proves the
list version when the multigraph has minimum degree at least 7.  The paragraph
after Theorem 6.6 identifies the sharp easy/obstruction boundary: a 5-cycle
with every edge tripled has delta(H)=6 and yields the Delta=8 counterexample
from Figure 1(d).  This generator raises that exact multiplicity to four:
delta(H)=8, Delta(L(H))=11, omega(L(H))=8, and ten colors are guaranteed.

Certificate cost.  The witness is not obtained by running a coloring solver.
It is assembled from two identities on four-subsets of ten colors.  Even
cycles alternate 0123 and 4567.  An odd cycle alternates until its final five
bundles, which use 0123, 4567, 0189, 2345, 6789.  Consecutive sets, including
the wraparound pair, are disjoint.  The standard reference route implemented
below recognizes the bundle quotient and runs dynamic programming over all
C(10,4)=210 states; it is polynomial and succeeds, so Track A would be false.

Attack hardening.  Every edge has the same line-graph degree 11, every bundle
has four indistinguishable parallel edges, and all labels and input orders are
independently permuted.  The panel tests an endpoint-label statistic, greedy
first-fit around the quotient, 256 structure-aware random restarts, and the
tempting constant parallel-copy coloring.  Odd quotient cycles defeat the two
local constructions.  The successful cycle-CSP dynamic program is reported
separately as Track B's reference algorithm.
""".strip()


_MULTIPLICITY = 4
_N_COLORS = 10
_A = (0, 1, 2, 3)
_B = (4, 5, 6, 7)
_ODD_TAIL = (
    (0, 1, 2, 3),
    (4, 5, 6, 7),
    (0, 1, 8, 9),
    (2, 3, 4, 5),
    (6, 7, 8, 9),
)


def _partition_cycles(n: int, max_components: int, rng: random.Random) -> list[int]:
    """A broad deterministic-from-seed partition into cycle lengths at least 5."""
    limit = min(max_components, n // 5)
    if limit < 1:
        raise ValueError("n must be at least 5")
    count = rng.randint(1, limit)
    remaining = n - 5 * count
    if count == 1:
        extras = [remaining]
    else:
        # Uniform weak composition via stars and bars.
        cuts = sorted(rng.sample(range(remaining + count - 1), count - 1))
        extras = []
        last = -1
        for cut in cuts + [remaining + count - 1]:
            extras.append(cut - last - 1)
            last = cut
    return [5 + extra for extra in extras]


def _compact_color_sets(length: int) -> list[tuple[int, int, int, int]]:
    """Known-by-composition four-color sets around one quotient cycle."""
    if length < 5:
        raise ValueError("cycle length must be at least 5")
    if length % 2 == 0:
        return [_A if i % 2 == 0 else _B for i in range(length)]
    prefix = [_A if i % 2 == 0 else _B for i in range(length - 5)]
    return prefix + list(_ODD_TAIL)


def make_instance(n: int, seed: int = 0, max_components: int = 6, **params: Any) -> dict:
    """Inverse-generate a fourfold-cycle multigraph and its exact 10-coloring."""
    del params
    if isinstance(n, bool) or not isinstance(n, int) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if (isinstance(max_components, bool) or not isinstance(max_components, int)
            or max_components < 1):
        raise ValueError("max_components must be a positive integer")
    rng = random.Random(seed)
    lengths = _partition_cycles(n, max_components, rng)

    palette = rng.sample(range(1000, 10000), _N_COLORS)
    rng.shuffle(palette)

    vertex_perm = list(range(n))
    rng.shuffle(vertex_perm)
    edge_perm = list(range(_MULTIPLICITY * n))
    rng.shuffle(edge_perm)

    answer = [None] * (_MULTIPLICITY * n)
    bundles: list[dict[str, Any]] = []
    vertex_offset = 0
    old_edge = 0
    for length in lengths:
        color_sets = _compact_color_sets(length)
        for i in range(length):
            old_ids = list(range(old_edge, old_edge + _MULTIPLICITY))
            old_edge += _MULTIPLICITY
            color_indices = list(color_sets[i])
            rng.shuffle(color_indices)
            new_ids = []
            for old_id, color_index in zip(old_ids, color_indices):
                new_id = edge_perm[old_id]
                new_ids.append(new_id)
                answer[new_id] = palette[color_index]
            rng.shuffle(new_ids)
            u = vertex_perm[vertex_offset + i]
            v = vertex_perm[vertex_offset + (i + 1) % length]
            if rng.randrange(2):
                u, v = v, u
            bundles.append({"ends": [u, v], "edges": new_ids})
        vertex_offset += length
    rng.shuffle(bundles)

    return {
        "base_vertex_count": n,
        "edge_count": _MULTIPLICITY * n,
        "line_graph_max_degree": 11,
        "palette": palette,
        "bundles": bundles,
        "answer": answer,
    }


def render(inst: dict) -> str:
    lines = [
        "PROBLEM: Properly edge-color the multigraph below with the ten allowed color labels.",
        "",
        "A multigraph may have parallel edges. Two different edges conflict exactly when they share at least one endpoint; parallel edges therefore conflict. A proper edge-coloring assigns different labels to every pair of conflicting edges.",
        "",
        "This multigraph is a disjoint union of cycles in which every cycle link is replaced by four parallel edges. Every base vertex is incident with eight edges. Equivalently, its line graph has one vertex per edge below and joins two vertices exactly when their edges conflict. That line graph is claw-free, has maximum degree Delta=11, and has no clique of size 11. Your task is its proper Delta-1=10 coloring, written as an edge-coloring.",
        "",
        f"Base vertices are the integers 0 through {inst['base_vertex_count'] - 1}.",
        f"Edge ids are the integers 0 through {inst['edge_count'] - 1}.",
        "Allowed color labels: " + ", ".join(map(str, inst["palette"])),
        "",
        "Each line `u--v : e1 e2 e3 e4` is one four-edge parallel bundle between distinct base vertices u and v:",
    ]
    for bundle in inst["bundles"]:
        u, v = bundle["ends"]
        lines.append(f"{u}--{v} : " + " ".join(map(str, bundle["edges"])))
    lines.extend([
        "",
        f"Return exactly {inst['edge_count']} integers. Entry i is the color label assigned to edge id i (0-indexed). Every entry must be one of the ten displayed labels. Repeats are allowed only on nonconflicting edges.",
        "Give your final answer inside <answer></answer> tags as one comma-separated list of integer color labels in increasing edge-id order.",
        "Example format: <answer>1234, 5678, 1234</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: Any) -> object | None:
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json|text)?\s*|\s*```$", "", body,
                      flags=re.IGNORECASE | re.DOTALL).strip()
    if not body:
        return []
    if body.startswith("[") and body.endswith("]"):
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            return None
        if isinstance(value, list) and all(
                isinstance(x, int) and not isinstance(x, bool) for x in value):
            return value
        return None
    if not re.fullmatch(r"[+-]?\d+(?:\s*(?:,|\s)\s*[+-]?\d+)*", body):
        return None
    try:
        return [int(x) for x in re.findall(r"[+-]?\d+", body)]
    except ValueError:
        return None


def verify(inst: dict, answer: Any) -> tuple[bool, str]:
    """Check any valid coloring; deliberately never inspect inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a list of integer color labels"
    if not answer:
        return False, "answer must be a nonempty list"
    expected = inst["edge_count"]
    if len(answer) != expected:
        return False, f"expected {expected} colors, got {len(answer)}"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "every color label must be an integer"
    palette = set(inst["palette"])
    for edge_id, color in enumerate(answer):
        if color not in palette:
            return False, f"edge {edge_id} uses color {color}, which is outside the palette"

    incident: dict[int, list[int]] = {
        v: [] for v in range(inst["base_vertex_count"])
    }
    for bundle_index, bundle in enumerate(inst["bundles"]):
        edge_ids = bundle["edges"]
        colors = [answer[e] for e in edge_ids]
        if len(set(colors)) != len(colors):
            return False, f"parallel bundle {bundle_index} repeats a color"
        u, v = bundle["ends"]
        incident[u].extend(edge_ids)
        incident[v].extend(edge_ids)

    for vertex in range(inst["base_vertex_count"]):
        seen: dict[int, int] = {}
        for edge_id in incident[vertex]:
            color = answer[edge_id]
            if color in seen:
                return False, (
                    f"base vertex {vertex} has incident edges {seen[color]} and "
                    f"{edge_id} with repeated color {color}"
                )
            seen[color] = edge_id
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample the declared structure-aware language: distinct within each bundle."""
    candidate = [None] * inst["edge_count"]
    for bundle in inst["bundles"]:
        picked = rng.sample(inst["palette"], _MULTIPLICITY)
        rng.shuffle(picked)
        for edge_id, color in zip(bundle["edges"], picked):
            candidate[edge_id] = color
    return candidate


def _lazy_random_candidate_valid(
        inst: dict, rng: random.Random, components: list[list[int]] | None = None) -> bool:
    """Validity of one exact candidate draw, stopped once failure is certain.

    The candidate language chooses an ordered four-sample independently for
    every bundle.  Edge order inside a bundle cannot affect whether adjacent
    bundles have disjoint color sets, so this draws the same marginal sets and
    omits only random choices belonging to an already-doomed candidate.
    """
    palette = inst["palette"]
    for component in components if components is not None else _ordered_components(inst):
        first = None
        previous = None
        for _bundle_index in component:
            current = frozenset(rng.sample(palette, _MULTIPLICITY))
            if previous is not None and not previous.isdisjoint(current):
                return False
            if first is None:
                first = current
            previous = current
        if previous is not None and first is not None and not previous.isdisjoint(first):
            return False
    return True


def search_space(inst: dict) -> int | None:
    per_bundle = math.prod(range(_N_COLORS - _MULTIPLICITY + 1, _N_COLORS + 1))
    return per_bundle ** len(inst["bundles"])


def enumerate_all(inst: dict) -> int | None:
    # Even the demo has 5040^5 candidates.  The exact closed-form count is
    # reported by selftest, but this explicitly brute-force API stays capped.
    if search_space(inst) <= 2_000_000:
        hits = 0
        palette = inst["palette"]
        bundles = inst["bundles"]
        choices = list(itertools.permutations(palette, _MULTIPLICITY))
        for rows in itertools.product(choices, repeat=len(bundles)):
            candidate = [None] * inst["edge_count"]
            for bundle, row in zip(bundles, rows):
                for edge_id, color in zip(bundle["edges"], row):
                    candidate[edge_id] = color
            hits += int(verify(inst, candidate)[0])
        return hits
    return None


def _ordered_components(inst: dict) -> list[list[int]]:
    """Return bundle indices in cyclic order, using incidence only."""
    by_vertex: dict[int, list[int]] = {
        v: [] for v in range(inst["base_vertex_count"])
    }
    for index, bundle in enumerate(inst["bundles"]):
        u, v = bundle["ends"]
        by_vertex[u].append(index)
        by_vertex[v].append(index)
    neighbors = [set() for _ in inst["bundles"]]
    for indices in by_vertex.values():
        if len(indices) != 2:
            raise ValueError("base multigraph quotient is not 2-regular")
        a, b = indices
        neighbors[a].add(b)
        neighbors[b].add(a)
    if any(len(row) != 2 for row in neighbors):
        raise ValueError("bundle quotient is not a union of cycles")

    unseen = set(range(len(neighbors)))
    components = []
    while unseen:
        start = min(unseen)
        order = []
        previous = None
        current = start
        while True:
            order.append(current)
            unseen.discard(current)
            options = sorted(neighbors[current])
            nxt = options[0] if options[0] != previous else options[1]
            previous, current = current, nxt
            if current == start:
                break
            if current not in unseen:
                raise ValueError("malformed quotient cycle")
        components.append(order)
    return components


def _cycle_lengths(inst: dict) -> list[int]:
    return sorted(len(component) for component in _ordered_components(inst))


def _structure_ok(inst: dict) -> tuple[bool, str]:
    """Check the promises used to identify the paper's Delta-1 regime."""
    n = inst["base_vertex_count"]
    if len(inst["bundles"]) != n or inst["edge_count"] != _MULTIPLICITY * n:
        return False, "bundle or edge count is inconsistent"
    seen_edges = []
    incidences = [0] * n
    for bundle in inst["bundles"]:
        if len(bundle["edges"]) != _MULTIPLICITY:
            return False, "a bundle does not have multiplicity four"
        u, v = bundle["ends"]
        if not (0 <= u < n and 0 <= v < n) or u == v:
            return False, "a bundle has invalid endpoints"
        incidences[u] += 1
        incidences[v] += 1
        seen_edges.extend(bundle["edges"])
    if sorted(seen_edges) != list(range(inst["edge_count"])):
        return False, "edge ids do not form the required exact range"
    if any(value != 2 for value in incidences):
        return False, "the simple bundle quotient is not 2-regular"
    try:
        lengths = _cycle_lengths(inst)
    except ValueError as exc:
        return False, str(exc)
    if any(length < 5 for length in lengths):
        return False, "a quotient cycle is shorter than five"
    # Each base vertex has multigraph degree 8.  A parallel edge conflicts with
    # its three mates and the other four edges at each endpoint: 3+4+4=11.
    # Quotient girth >=5 makes the multigraph triangle-free, so every line-graph
    # clique is an eight-edge star (or a smaller parallel class), never K_11.
    if inst.get("line_graph_max_degree") != 11:
        return False, "the declared line-graph maximum degree is not 11"
    return True, "ok"


def canonical_key(inst: dict) -> str:
    """Complete invariant for disjoint unions of fourfold simple cycles."""
    payload = {
        "multiplicity": _MULTIPLICITY,
        "palette_size": len(inst["palette"]),
        "cycle_lengths": _cycle_lengths(inst),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    current = int(params.get("n", 5))
    if current >= 63:
        return "cap_bound"
    harder = dict(params)
    harder["n"] = min(63, current + 4)
    harder["max_components"] = max(int(params.get("max_components", 1)), 7)
    return harder


def _assign_sets(inst: dict, component_sets: list[list[int]]) -> list[int]:
    answer = [None] * inst["edge_count"]
    for component, masks in zip(_ordered_components(inst), component_sets):
        for bundle_index, mask in zip(component, masks):
            colors = [inst["palette"][i] for i in range(_N_COLORS) if mask >> i & 1]
            for edge_id, color in zip(sorted(inst["bundles"][bundle_index]["edges"]), colors):
                answer[edge_id] = color
    return answer


def _reference_cycle_dp(inst: dict) -> tuple[list[int], int]:
    """Polynomial reference solver, independent of the planted certificate."""
    operations = 0
    masks = []
    for comb in itertools.combinations(range(_N_COLORS), _MULTIPLICITY):
        mask = sum(1 << i for i in comb)
        masks.append(mask)
        operations += _MULTIPLICITY
    neighbors: dict[int, list[int]] = {mask: [] for mask in masks}
    for left in masks:
        for right in masks:
            operations += 1
            if left & right == 0:
                neighbors[left].append(right)

    all_paths: list[list[int]] = []
    for component in _ordered_components(inst):
        operations += 2 * len(component)
        first = masks[0]
        current = {first}
        parents: list[dict[int, int]] = []
        for _ in range(1, len(component)):
            layer: dict[int, int] = {}
            for previous in current:
                for nxt in neighbors[previous]:
                    operations += 1
                    if nxt not in layer:
                        layer[nxt] = previous
            parents.append(layer)
            current = set(layer)
        end = next((mask for mask in sorted(current) if mask & first == 0), None)
        if end is None:
            raise RuntimeError("cycle DP unexpectedly found no coloring")
        reverse_path = [end]
        for layer in reversed(parents):
            end = layer[end]
            reverse_path.append(end)
        path = list(reversed(reverse_path))
        all_paths.append(path)
        operations += len(path) * _MULTIPLICITY
    return _assign_sets(inst, all_paths), operations


def _endpoint_statistic_candidate(inst: dict) -> list[int]:
    candidate = [None] * inst["edge_count"]
    for bundle in inst["bundles"]:
        u, v = bundle["ends"]
        offset = (3 * min(u, v) + 7 * max(u, v)) % _N_COLORS
        for rank, edge_id in enumerate(sorted(bundle["edges"])):
            candidate[edge_id] = inst["palette"][(offset + rank) % _N_COLORS]
    return candidate


def _greedy_cycle_candidate(inst: dict) -> list[int]:
    paths = []
    for component in _ordered_components(inst):
        prior = 0
        row = []
        for _ in component:
            available = [i for i in range(_N_COLORS) if not (prior >> i & 1)]
            mask = sum(1 << i for i in available[:_MULTIPLICITY])
            row.append(mask)
            prior = mask
        paths.append(row)
    return _assign_sets(inst, paths)


def _parallel_copy_candidate(inst: dict) -> list[int]:
    candidate = [None] * inst["edge_count"]
    for bundle in inst["bundles"]:
        for rank, edge_id in enumerate(sorted(bundle["edges"])):
            candidate[edge_id] = inst["palette"][rank]
    return candidate


def _random_restart_candidate(inst: dict, seed: int, restarts: int = 256) -> list[int]:
    rng = random.Random(seed)
    last = None
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last
    assert last is not None
    return last


def _attack_candidates(inst: dict, seed: int) -> dict[str, list[int]]:
    return {
        "outlier_endpoint_label_statistic": _endpoint_statistic_candidate(inst),
        "greedy_bundle_first_fit": _greedy_cycle_candidate(inst),
        "random_restart_256": _random_restart_candidate(inst, 900_000 + seed),
        "parallel_copy_index_ansatz": _parallel_copy_candidate(inst),
    }


def _valid_set_cycles(length: int) -> int:
    """Trace(A^length) for the Kneser graph KG(10,4)."""
    return (
        15 ** length
        + 9 * ((-10) ** length)
        + 35 * (6 ** length)
        + 75 * ((-3) ** length)
        + 90
    )


def _exact_valid_answers(inst: dict) -> int:
    set_cycles = math.prod(_valid_set_cycles(length) for length in _cycle_lengths(inst))
    return set_cycles * (math.factorial(_MULTIPLICITY) ** len(inst["bundles"]))


def _answer_wire(answer: list[int]) -> str:
    return ", ".join(map(str, answer))


def _count_atoms(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_count_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_count_atoms(v) for v in value)
    return 1


def _find_distinct_swap(inst: dict, answer: list[int], forbidden_reason: str) -> list[int]:
    for i in range(len(answer)):
        for j in range(i + 1, len(answer)):
            if answer[i] == answer[j]:
                continue
            bad = list(answer)
            bad[i], bad[j] = bad[j], bad[i]
            ok, why = verify(inst, bad)
            if not ok and why != forbidden_reason:
                return bad
    raise AssertionError("could not manufacture a rejected swap corruption")


def _transformed_instances(inst: dict) -> list[tuple[dict, list[int], str]]:
    rng = random.Random(0x1269)
    original = list(inst["answer"])
    out = []

    vertex = copy.deepcopy(inst)
    perm = list(range(inst["base_vertex_count"]))
    rng.shuffle(perm)
    for bundle in vertex["bundles"]:
        bundle["ends"] = [perm[x] for x in bundle["ends"]]
    out.append((vertex, original, "base-vertex relabelling"))

    edges = copy.deepcopy(inst)
    edge_perm = list(range(inst["edge_count"]))
    rng.shuffle(edge_perm)
    carried = [None] * inst["edge_count"]
    for old, new in enumerate(edge_perm):
        carried[new] = original[old]
    for bundle in edges["bundles"]:
        bundle["edges"] = [edge_perm[x] for x in bundle["edges"]]
    edges["answer"] = list(carried)
    out.append((edges, carried, "edge-id relabelling"))

    reordered = copy.deepcopy(inst)
    rng.shuffle(reordered["bundles"])
    for bundle in reordered["bundles"]:
        bundle["ends"].reverse()
        rng.shuffle(bundle["edges"])
    out.append((reordered, original, "bundle reordering and endpoint reversal"))

    palette = copy.deepcopy(inst)
    new_labels = rng.sample(range(20000, 40000), _N_COLORS)
    mapping = dict(zip(inst["palette"], new_labels))
    palette["palette"] = new_labels
    palette_answer = [mapping[x] for x in original]
    palette["answer"] = list(palette_answer)
    out.append((palette, palette_answer, "color-label relabelling"))

    composed = copy.deepcopy(edges)
    for bundle in composed["bundles"]:
        bundle["ends"] = [perm[x] for x in bundle["ends"]]
        bundle["ends"].reverse()
    rng.shuffle(composed["bundles"])
    composed_mapping = dict(zip(inst["palette"], new_labels))
    composed["palette"] = new_labels
    composed_answer = [composed_mapping[x] for x in carried]
    composed["answer"] = list(composed_answer)
    out.append((composed, composed_answer, "composed relabellings"))
    return out


def selftest() -> dict:
    report: dict[str, Any] = {
        "paper": "1206.1269",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1: every preset, multiple unrelated seeds, plus JSON-native answers.
    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 104729):
            inst = make_instance(seed=seed, **params)
            attempts += 1
            ok, why = verify(inst, inst["answer"])
            structure, structure_why = _structure_ok(inst)
            json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            if not ok or not json_ok or not structure:
                failures.append({
                    "preset": preset,
                    "seed": seed,
                    "reason": why if not ok else structure_why,
                })
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "structural_promise_checks": attempts,
        "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=24681357, **shipping_params)
    answer = list(inst["answer"])

    # G2: all requested corruption modes, with distinct diagnostics.
    duplicate = list(answer)
    first_bundle = inst["bundles"][0]["edges"]
    duplicate[first_bundle[1]] = duplicate[first_bundle[0]]
    _, duplicate_reason = verify(inst, duplicate)
    swapped = _find_distinct_swap(inst, answer, duplicate_reason)
    out_of_range = list(answer)
    out_of_range[0] = max(inst["palette"]) + 1
    corruptions = {
        "drop_one": answer[:-1],
        "swap_two": swapped,
        "duplicate_one": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    cases = {}
    reasons = []
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        cases[name] = {"rejected": not ok, "reason": why}
        reasons.append(why)
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in cases.values())
        and len(set(reasons)) == len(reasons),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic prose, a markdown fence, tags, and comma-separated payload.
    response = (
        "I contracted the parallel twin classes and colored the quotient cycles.\n"
        "```text\n<answer>" + _answer_wire(answer) + "</answer>\n```\n"
        "The entries are in increasing edge-id order."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("garbage") is None,
        "parsed_length": len(parsed) if isinstance(parsed, list) else None,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4: candidates already satisfy the obvious four-distinct-within-a-bundle rule.
    trials = 200_000
    rng = random.Random(0x12061269)
    hits = 0
    sampling_components = _ordered_components(inst)
    for _ in range(trials):
        hits += int(_lazy_random_candidate_valid(inst, rng, sampling_components))
    observed = hits / trials
    space = search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6,
        "hits": hits,
        "total": trials,
        "observed_probability": observed,
        "candidate_space": space,
        "sampling_prior": "lazy exact draws from independent ordered four-color samples without replacement inside every displayed bundle",
    }

    # Track-B reference algorithm: independently solve via cycle-CSP DP.
    reference_attempts = 8
    reference_successes = 0
    max_operations = 0
    t0 = time.perf_counter()
    for seed in range(800, 800 + reference_attempts):
        test = make_instance(seed=seed, **shipping_params)
        got, operations = _reference_cycle_dp(test)
        reference_successes += int(verify(test, got)[0])
        max_operations = max(max_operations, operations)
    reference_wall = time.perf_counter() - t0

    valid_count = _exact_valid_answers(inst)
    exact_log10_density = math.log10(valid_count) - math.log10(space)
    report["G5_density_and_baseline"] = {
        "pass": observed < 1e-6 and reference_successes == reference_attempts,
        "shipping_sample_hits": hits,
        "shipping_sample_total": trials,
        "shipping_sampled_solution_fraction": observed,
        "exact_valid_answer_count": valid_count,
        "exact_density_log10": exact_log10_density,
        "baseline_wall_clock_seconds": round(reference_wall, 6),
        "baseline_operations_max": max_operations,
        "baseline_attempts": reference_attempts,
    }

    # G6: failing no-tool attacks; the successful polynomial method is separate.
    attack_counts = {
        name: {"successes": 0, "attempts": 0}
        for name in (
            "outlier_endpoint_label_statistic",
            "greedy_bundle_first_fit",
            "random_restart_256",
            "parallel_copy_index_ansatz",
        )
    }
    for seed in range(8):
        test = make_instance(seed=9000 + seed, **shipping_params)
        for name, candidate in _attack_candidates(test, seed).items():
            ok, _ = verify(test, candidate)
            attack_counts[name]["successes"] += int(ok)
            attack_counts[name]["attempts"] += 1
    all_failed = all(
        row["successes"] == 0 and row["attempts"] >= 8
        for row in attack_counts.values()
    )
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attack_counts,
        "reference_algorithm": {
            "name": "dynamic programming on the quotient-cycle CSP",
            "complexity": "O(n*C(10,4)*C(6,4)) transitions after incidence decomposition",
            "wall_clock_sec": round(reference_wall, 6),
            "operations": max_operations,
            "successes": reference_successes,
            "attempts": reference_attempts,
            "solves": f"{reference_successes}/{reference_attempts}, as expected on Track B",
        },
    }

    # G7: named levels grow; an escalation and a size-doubled instance still verify.
    harder = escalate(shipping_params)
    if isinstance(harder, dict):
        hard_inst = make_instance(seed=111, **harder)
        hard_ok = verify(hard_inst, hard_inst["answer"])[0]
        harder_space = search_space(hard_inst)
    else:
        hard_ok = harder == "cap_bound"
        harder_space = space
    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=222, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": hard_ok and doubled_ok and harder_space > space,
        "shipping_bundles": inst["edge_count"] // _MULTIPLICITY,
        "escalated_bundles": harder.get("n") if isinstance(harder, dict) else None,
        "shipping_candidate_bits": space.bit_length(),
        "escalated_candidate_bits": harder_space.bit_length(),
        "doubled_n": doubled_params["n"],
        "doubled_verifies": doubled_ok,
    }

    # G8: exact graph-isomorphism invariant for this restricted family.
    selected: list[tuple[int, dict]] = []
    seen_keys = set()
    seed = 20_000
    while len(selected) < 20 and seed < 25_000:
        test = make_instance(seed=seed, **shipping_params)
        key = canonical_key(test)
        if key not in seen_keys:
            selected.append((seed, test))
            seen_keys.add(key)
        seed += 1
    g8_failures = []
    invariance_checks = 0
    carried_checks = 0
    for source_seed, base in selected:
        key = canonical_key(base)
        for transformed, carried_answer, symmetry in _transformed_instances(base):
            invariance_checks += 1
            if canonical_key(transformed) != key:
                g8_failures.append(f"seed {source_seed}: key changed under {symmetry}")
            ok, why = verify(transformed, carried_answer)
            carried_checks += 1
            if not ok:
                g8_failures.append(
                    f"seed {source_seed}: carried answer failed under {symmetry}: {why}"
                )
    report["G8_canonical_key"] = {
        "pass": not g8_failures and len(selected) == 20 and len(seen_keys) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated": len(seen_keys),
        "unrelated_attempts": len(selected),
        "seeds_examined": seed - 20_000,
        "failures": g8_failures,
        "symmetries": [
            "base-vertex relabelling",
            "edge-id relabelling",
            "bundle reordering and endpoint reversal",
            "color-label relabelling",
            "compositions of these maps",
        ],
    }

    # G9(a,b) is recorded; G9(c) alone gates.
    blob = json.dumps(answer, separators=(",", ":"))
    chars = len(blob)
    atoms = _count_atoms(answer)
    tokens = (chars + 3) // 4
    intended_operations = inst["edge_count"]
    arms = {name: dict(G9_EVIDENCE[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else 0.0
    )
    within_caps = chars <= 2000 and atoms <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "placebo_verdict": G9_EVIDENCE["placebo_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": atoms,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if re.match(r"G\d", key)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
