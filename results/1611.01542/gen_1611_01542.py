"""Verified generator for a native p-set-splittability family.

The source paper is Bernstein et al., "The set splittability problem",
arXiv:1611.01542.  Instances are inverse-generated: a perfect matching is
planted before the remaining incidence columns are assembled.

Only the standard library is needed.  The optional gvlib helpers are not used
because this family is finite-discrete and all verification is integer exact.
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
from typing import Any


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite collection of sets",
        "p-splitter subset of the ground set",
    ],
    "verification_operations": [
        "exact set membership",
        "exact intersection cardinality",
        "integer comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The splitter labels form a modular arithmetic progression hidden among "
        "regular-incidence decoys; without noticing it one faces exact-cover search."
    ),
    "hardness_basis": (
        "Track B: domain-standard Algorithm X (O(d^n) worst case) solved 8/8 shipping instances in "
        "88,394 nodes and 2.283 s mean (151,778 nodes and 4.506 s maximum) on the final local run; the "
        "construction-aware O((dn)^2 n) progression scan also solves 8/8 using "
        "1,592,000 modular advances and 0.282 s mean, whereas recognizing its start "
        "and step leaves 216 modular additions/comparisons including output sorting.  Theorem 2.1 supplies only the "
        "general p-SPLIT context, not an average-case claim for this distribution."
    ),
    "max_answer_tokens": 81,
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
        "An unordered subset written as exactly n distinct integer residue labels "
        "from the displayed d*n-element universe; output is the increasing list."
    ),
    "bounds": {
        "max_selected_elements": 256,
        "label_min": 0,
        "label_max": 1_000_002,
        "distinct": 1,
    },
}

DIFFICULTY = {
    "demo": {"n": 4, "degree": 3},
    "easy": {"n": 40, "degree": 5},
    "medium": {"n": 40, "degree": 6},
    "hard": {"n": 40, "degree": 7},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The sought labels form a modular arithmetic progression inside the displayed residue universe."
)
PLACEBO_HINT = (
    "The sought labels reward systematic bookkeeping across the displayed regular incidence data."
)

_PRIME = 1_000_003
_SELFTEST_SEEDS = tuple(range(8))

# Filled from the separately-owned harden.py transcripts after those runs.
_G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "not_run",
    "note": "all bare, structural, and placebo redraws returned OpenRouter HTTP 403 key-limit errors",
}

NOTES = (
    "Section 1 fixes the nearest-integer convention, including either rounding at "
    "half-integers.  Section 2, especially Theorem 2.1, identifies p-SPLIT as the "
    "binary-incidence problem My=round(pM1), but its NP-completeness is only "
    "worst-case.  Section 3 makes collections of at most two sets easy, and Section "
    "4 (Theorems 4.5 and 4.6) makes large multiplicity-1 "
    "Venn regions and k in omega(2^n n) easy; generated instances avoid both regimes "
    "by using 3n sets and making every ground element have multiplicity exactly 3.  "
    "The certificate is planted, never solved for.  Exact regularity defeats degree "
    "outliers; degree-preserving switches erase decoy-layer boundaries; shuffled "
    "labels and rows defeat first-fit and first-pair guesses; random greedy restarts "
    "are measured.  Domain-standard Algorithm X is the successful Track B reference "
    "algorithm, while the full modular-progression certificate algorithm is reported "
    "separately so the efficient construction-aware route is not hidden."
)


def _validate_params(n: int, degree: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 4:
        raise ValueError("n must be an integer at least 4")
    if isinstance(degree, bool) or not isinstance(degree, int):
        raise ValueError("degree must be an integer")
    if degree < 3 or degree >= n:
        raise ValueError("degree must satisfy 3 <= degree < n")
    if degree * n >= _PRIME:
        raise ValueError("degree*n must be smaller than the fixed prime")


def _regular_edges(n: int, degree: int, rng: random.Random) -> tuple[list[tuple[int, ...]], list[int]]:
    """Return a simple 3-uniform degree-regular hypergraph and planted edge indices.

    Layer zero is the held certificate.  The other cyclic layers are mixed by
    cross-edge degree-preserving switches.  No search for a perfect matching occurs.
    """

    vertex_count = 3 * n
    # A random vertex relabelling makes every initial layer edge marginally a
    # uniform triple, including the planted layer.
    vertex_perm = list(range(vertex_count))
    rng.shuffle(vertex_perm)

    layers: list[list[tuple[int, int, int]]] = []
    for layer in range(degree):
        raw = []
        for i in range(n):
            raw.append(
                tuple(
                    sorted(
                        (
                            vertex_perm[i],
                            vertex_perm[n + ((i + layer) % n)],
                            vertex_perm[2 * n + ((i + 2 * layer) % n)],
                        )
                    )
                )
            )
        layers.append(raw)

    plant = list(layers[0])
    decoys = [edge for layer in layers[1:] for edge in layer]
    plant_set = set(plant)
    decoy_set = set(decoys)

    # Mix the guaranteed decoy partitions.  Each accepted switch swaps one
    # endpoint between two edges, preserving all vertex degrees and simplicity.
    switch_target = 24 * len(decoys)
    accepted = 0
    attempts = 0
    attempt_cap = max(200, 20 * switch_target)
    while accepted < switch_target and attempts < attempt_cap:
        attempts += 1
        i, j = rng.sample(range(len(decoys)), 2)
        e1, e2 = decoys[i], decoys[j]
        if set(e1) & set(e2):
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

    edges = plant + decoys
    order = list(range(len(edges)))
    rng.shuffle(order)
    old_to_new = {old: new for new, old in enumerate(order)}
    shuffled = [edges[old] for old in order]
    planted_indices = [old_to_new[i] for i in range(n)]
    return shuffled, planted_indices


def make_instance(n: int, seed: int = 0, degree: int = 5, **params: Any) -> dict:
    """Inverse-generate a p-splittable collection and its splitter certificate."""

    if params:
        unknown = ", ".join(sorted(params))
        raise TypeError(f"unknown parameters: {unknown}")
    _validate_params(n, degree)
    rng = random.Random(seed)
    edges, planted_indices = _regular_edges(n, degree, rng)

    # Give the planted edges a modular-AP label set.  A random affine choice
    # makes each individual plant label uniform, as are individual decoy labels.
    start = rng.randrange(_PRIME)
    step = rng.randrange(1, _PRIME)
    plant_labels = [(start + i * step) % _PRIME for i in range(n)]
    used = set(plant_labels)
    decoy_labels: list[int] = []
    while len(decoy_labels) < len(edges) - n:
        x = rng.randrange(_PRIME)
        if x not in used:
            used.add(x)
            decoy_labels.append(x)
    rng.shuffle(plant_labels)
    rng.shuffle(decoy_labels)

    label_by_edge: list[int | None] = [None] * len(edges)
    planted_index_set = set(planted_indices)
    pi = di = 0
    for edge_index in range(len(edges)):
        if edge_index in planted_index_set:
            label_by_edge[edge_index] = plant_labels[pi]
            pi += 1
        else:
            label_by_edge[edge_index] = decoy_labels[di]
            di += 1
    labels = [int(x) for x in label_by_edge]

    sets = [[] for _ in range(3 * n)]
    for edge_index, vertices in enumerate(edges):
        label = labels[edge_index]
        for vertex in vertices:
            sets[vertex].append(label)
    for row in sets:
        row.sort()
    rng.shuffle(sets)

    answer = sorted(labels[i] for i in planted_indices)
    return {
        "n": n,
        "degree": degree,
        "p": [1, degree],
        "prime": _PRIME,
        "universe": sorted(labels),
        "sets": sets,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the complete, standalone p-splitter problem."""

    n = inst["n"]
    degree = inst["degree"]
    lines = [
        "Find an exact p-splitter for the finite set collection below.",
        "",
        "Definitions: the ground set U is the displayed set of distinct integer labels.",
        "For p = 1/d, a p-splitter is a subset S of U such that every listed set B",
        "contains exactly the nearest integer to |B|/d elements of S.  Here every",
        f"listed set has d = {degree} elements, so the required intersection size is exactly 1.",
        f"Every ground-set label occurs in exactly three listed sets; consequently S must have exactly n = {n} labels.",
        "The listed sets are indexed constraints; equal rows, if present, are each checked.",
        "Labels are residues modulo the displayed prime, represented by their unique",
        "integers from 0 through prime-1.  Only membership in the listed sets determines",
        "whether an answer is a valid splitter; the residue labels are part of the instance.",
        "Order in S does not matter, repeats are forbidden, and all bounds are inclusive.",
        "",
        f"prime = {inst['prime']}",
        f"p = 1/{degree}",
        f"U ({len(inst['universe'])} labels) = " + ", ".join(map(str, inst["universe"])),
        f"Listed sets ({len(inst['sets'])} total, indexed 0 through {len(inst['sets']) - 1}):",
    ]
    for i, row in enumerate(inst["sets"]):
        lines.append(f"B{i} = " + ", ".join(map(str, row)))
    lines.extend(
        [
            "",
            f"Give exactly {n} distinct labels in increasing order, separated by commas.",
            "Give your final answer inside <answer></answer> tags, as a comma-separated list of integers.",
            "Format example only: <answer>12, 47, 105</answer>",
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
    """Parse a comma list from answer tags, tolerating prose and Markdown fences."""

    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if tagged:
        body = tagged[-1].strip()
    else:
        # A forgiving fallback for a bare JSON list in a fenced/prose response.
        brackets = re.findall(r"\[\s*-?\d+(?:\s*,\s*-?\d+)*\s*\]", text, flags=re.S)
        if not brackets:
            return None
        body = brackets[-1]
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1].strip()
    if not body:
        return None
    if not re.fullmatch(r"-?\d+(?:\s*,\s*-?\d+)*", body):
        return None
    try:
        return [int(piece.strip()) for piece in body.split(",")]
    except (TypeError, ValueError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any proposed splitter exactly; the planted answer is never consulted."""

    if not isinstance(answer, list) or any(
        isinstance(x, bool) or not isinstance(x, int) for x in answer
    ):
        return False, "answer must be a list of integer labels"
    if not answer:
        return False, "empty answer"
    if len(set(answer)) != len(answer):
        return False, "duplicate labels are forbidden"
    universe = set(inst["universe"])
    if any(x not in universe for x in answer):
        return False, "label outside the displayed universe"
    if len(answer) != inst["n"]:
        return False, f"wrong cardinality: expected {inst['n']} labels"
    chosen = set(answer)
    for i, row in enumerate(inst["sets"]):
        count = sum(label in chosen for label in row)
        if count != 1:
            return False, f"set B{i} has intersection size {count}, expected 1"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the statement-implied fixed-cardinality answer language."""

    return sorted(rng.sample(inst["universe"], inst["n"]))


def search_space(inst: dict) -> int | None:
    return math.comb(len(inst["universe"]), inst["n"])


def _column_rows(inst: dict) -> dict[int, tuple[int, int, int]]:
    rows: dict[int, list[int]] = {label: [] for label in inst["universe"]}
    for row_index, row in enumerate(inst["sets"]):
        for label in row:
            rows[label].append(row_index)
    return {label: tuple(indices) for label, indices in rows.items()}  # type: ignore[return-value]


def _is_cover_fast(inst: dict, answer: list[int], columns: dict[int, tuple[int, int, int]] | None = None) -> bool:
    if len(answer) != inst["n"] or len(set(answer)) != len(answer):
        return False
    if columns is None:
        columns = _column_rows(inst)
    covered = 0
    for label in answer:
        vertices = columns.get(label)
        if vertices is None:
            return False
        mask = 0
        for vertex in vertices:
            mask |= 1 << vertex
        if covered & mask:
            return False
        covered |= mask
    return covered == (1 << (3 * inst["n"])) - 1


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 200_000:
        return None
    columns = _column_rows(inst)
    count = 0
    for candidate in itertools.combinations(inst["universe"], inst["n"]):
        if _is_cover_fast(inst, list(candidate), columns):
            count += 1
    return count


def canonical_key(inst: dict) -> str:
    """A strong relabelling invariant, not a claimed graph canonical form.

    Full bipartite-incidence isomorphism is not cheaply canonicalized here.  The
    key hashes exact rooted closed-walk signatures through length six in the
    weighted row co-incidence graph, plus local column codegree signatures.
    """

    row_count = len(inst["sets"])
    columns = _column_rows(inst)
    adjacency: list[dict[int, int]] = [dict() for _ in range(row_count)]
    for vertices in columns.values():
        for a, b in itertools.combinations(vertices, 2):
            adjacency[a][b] = adjacency[a].get(b, 0) + 1
            adjacency[b][a] = adjacency[b].get(a, 0) + 1

    rooted = []
    for start in range(row_count):
        values = [0] * row_count
        values[start] = 1
        signature = []
        for length in range(1, 7):
            nxt = [0] * row_count
            for vertex, neighbours in enumerate(adjacency):
                total = 0
                for other, weight in neighbours.items():
                    total += weight * values[other]
                nxt[vertex] = total
            values = nxt
            if length >= 2:
                signature.append(values[start])
        rooted.append(tuple(signature))

    local_columns = []
    for vertices in columns.values():
        pair_weights = []
        for a, b in itertools.combinations(vertices, 2):
            pair_weights.append(adjacency[a].get(b, 0))
        neighbour_degrees = [sum(adjacency[v].values()) for v in vertices]
        local_columns.append((tuple(sorted(pair_weights)), tuple(sorted(neighbour_degrees))))

    invariant = {
        "p": inst["p"],
        "shape": [row_count, len(inst["universe"])],
        "rooted_walks": sorted(rooted),
        "column_local": sorted(local_columns),
        "walk_traces": [sum(sig[i] for sig in rooted) for i in range(5)],
    }
    payload = json.dumps(invariant, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Raise decoy density first, preserving the answer length."""

    current = {k: v for k, v in params.items() if k != "_preset"}
    n = int(current.get("n", DIFFICULTY["hard"]["n"]))
    degree = int(current.get("degree", DIFFICULTY["hard"]["degree"]))
    if degree + 1 < n:
        current["degree"] = degree + 1
        current["n"] = n
        return current
    if n < 120:
        current["n"] = n + 16
        current["degree"] = degree
        return current
    return "cap_bound"


def _greedy_candidate(inst: dict, rng: random.Random | None = None) -> list[int] | None:
    columns = _column_rows(inst)
    labels = sorted(columns)
    row_incident: list[list[int]] = [[] for _ in inst["sets"]]
    for label, vertices in columns.items():
        for vertex in vertices:
            row_incident[vertex].append(label)
    uncovered = set(range(len(inst["sets"])))
    available = set(labels)
    solution: list[int] = []
    while uncovered:
        counts = []
        for vertex in uncovered:
            options = [label for label in row_incident[vertex] if label in available]
            counts.append((len(options), vertex, options))
        minimum = min(item[0] for item in counts)
        tied = [item for item in counts if item[0] == minimum]
        item = rng.choice(tied) if rng is not None else min(tied, key=lambda x: x[1])
        options = item[2]
        if not options:
            return None
        label = rng.choice(options) if rng is not None else min(options)
        solution.append(label)
        touched = set(columns[label])
        conflicting = set()
        for vertex in touched:
            conflicting.update(row_incident[vertex])
        uncovered.difference_update(touched)
        available.difference_update(conflicting)
    return sorted(solution)


def _random_restart(inst: dict, restarts: int, seed: int) -> list[int] | None:
    rng = random.Random(seed)
    for _ in range(restarts):
        candidate = _greedy_candidate(inst, rng)
        if candidate is not None and verify(inst, candidate)[0]:
            return candidate
    return None


def _algorithm_x(inst: dict, node_cap: int = 2_000_000) -> tuple[list[int] | None, int, bool]:
    """Bit-mask Algorithm X for the induced exact-cover instance.

    Returns (solution, visited_nodes, hit_cap).  This is an attack/reference
    implementation only; make_instance never calls it.
    """

    columns = _column_rows(inst)
    labels = sorted(columns)
    edge_index = {label: i for i, label in enumerate(labels)}
    row_count = len(inst["sets"])
    edge_count = len(labels)
    incident = [0] * row_count
    for label, vertices in columns.items():
        bit = 1 << edge_index[label]
        for vertex in vertices:
            incident[vertex] |= bit

    conflicts = [0] * edge_count
    vertex_masks = [0] * edge_count
    for label, vertices in columns.items():
        idx = edge_index[label]
        for vertex in vertices:
            conflicts[idx] |= incident[vertex]
            vertex_masks[idx] |= 1 << vertex

    nodes = 0

    def visit(uncovered: int, available: int, chosen: list[int]) -> list[int] | None | bool:
        nonlocal nodes
        nodes += 1
        if nodes > node_cap:
            return False  # private cap sentinel; a real solution is always a list
        if uncovered == 0:
            return chosen

        remaining = uncovered
        options = 0
        smallest = edge_count + 1
        while remaining:
            bit = remaining & -remaining
            vertex = bit.bit_length() - 1
            here = incident[vertex] & available
            count = here.bit_count()
            if count == 0:
                return None
            if count < smallest:
                smallest = count
                options = here
            remaining -= bit

        while options:
            bit = options & -options
            idx = bit.bit_length() - 1
            result = visit(
                uncovered & ~vertex_masks[idx],
                available & ~conflicts[idx],
                chosen + [labels[idx]],
            )
            if result is False:
                return False
            if isinstance(result, list):
                return result
            options -= bit
        return None

    found = visit((1 << row_count) - 1, (1 << edge_count) - 1, [])
    if found is False:
        return None, nodes, True
    return (sorted(found) if isinstance(found, list) else None), nodes, False


def _full_ap_reference(inst: dict) -> tuple[list[int] | None, int]:
    """Construction-aware Track B reference: exhaustive ordered-pair AP scan."""

    labels = list(inst["universe"])
    universe = set(labels)
    prime = inst["prime"]
    length = inst["n"]
    valid: list[list[int]] = []
    operations = 0
    for start in labels:
        for second in labels:
            if second == start:
                continue
            step = (second - start) % prime
            candidate = []
            value = start
            complete = True
            for _ in range(length):
                candidate.append(value)
                complete = complete and value in universe
                value = (value + step) % prime
                operations += 1
            if complete:
                candidate.sort()
                if verify(inst, candidate)[0]:
                    valid.append(candidate)
    if not valid:
        return None, operations
    valid.sort()
    return valid[0], operations


def _first_pair_progression(inst: dict) -> list[int]:
    labels = inst["universe"]
    start, second = labels[0], labels[1]
    step = (second - start) % inst["prime"]
    return sorted((start + i * step) % inst["prime"] for i in range(inst["n"]))


def _codegree_outlier_candidate(inst: dict) -> list[int]:
    """Greedily pack labels with the smallest local pair-codegree signature."""

    columns = _column_rows(inst)
    pair_counts: dict[tuple[int, int], int] = {}
    for vertices in columns.values():
        for pair in itertools.combinations(vertices, 2):
            key = tuple(sorted(pair))
            pair_counts[key] = pair_counts.get(key, 0) + 1
    ranked = []
    for label, vertices in columns.items():
        counts = sorted(
            pair_counts[tuple(sorted(pair))]
            for pair in itertools.combinations(vertices, 2)
        )
        ranked.append((sum(counts), max(counts), tuple(counts), label, vertices))
    ranked.sort()
    chosen: list[int] = []
    occupied: set[int] = set()
    for _, _, _, label, vertices in ranked:
        if occupied.isdisjoint(vertices):
            chosen.append(label)
            occupied.update(vertices)
    return sorted(chosen)


def _answer_sizes(answer: object) -> tuple[int, int, int]:
    # Match emit.sh's ordinary json.dumps serialization, including separators.
    blob = json.dumps(answer)

    def atoms(value: object) -> int:
        if isinstance(value, dict):
            return sum(atoms(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return sum(atoms(v) for v in value)
        return 1

    return len(blob), math.ceil(len(blob) / 4), atoms(answer)


def _relabel_instance(inst: dict, mapping: dict[int, int], row_order: list[int] | None = None) -> dict:
    result = {k: v for k, v in inst.items() if k not in {"universe", "sets", "answer"}}
    result["universe"] = sorted(mapping[x] for x in inst["universe"])
    transformed_rows = [[mapping[x] for x in row] for row in inst["sets"]]
    if row_order is not None:
        transformed_rows = [transformed_rows[i] for i in row_order]
    result["sets"] = transformed_rows
    result["answer"] = sorted(mapping[x] for x in inst["answer"])
    return result


def selftest() -> dict:
    """Run gates G1--G9 and return their machine-readable measurements."""

    report: dict[str, Any] = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    # G1: all named rungs, several independent seeds.
    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=17, **shipping)
    answer = list(inst["answer"])
    unselected = next(x for x in inst["universe"] if x not in set(answer))
    corruptions = {
        "drop_one": answer[:-1],
        "replace_one": answer[:-1] + [unselected],
        "duplicate_one": answer[:-1] + [answer[0]],
        "empty": [],
        "outside_universe": answer[:-1] + [_PRIME + 7],
    }
    g2_reasons = {name: verify(inst, value)[1] for name, value in corruptions.items()}
    g2_rejected = {name: not verify(inst, value)[0] for name, value in corruptions.items()}
    report["G2_rejects_corruption"] = {
        "pass": all(g2_rejected.values()) and len(set(g2_reasons.values())) == len(g2_reasons),
        "rejected": g2_rejected,
        "reasons": g2_reasons,
    }

    wire = ", ".join(map(str, answer))
    model_style = f"I checked every listed set.\n```text\n<answer>{wire}</answer>\n```\n"
    parsed = parse_answer(model_style)
    json_native = json.loads(json.dumps(answer)) == answer
    report["G3_round_trip"] = {
        "pass": parsed == answer and json_native,
        "model_style_parsed": parsed == answer,
        "json_native": json_native,
    }

    sample_total = 200_000
    sample_hits = 0
    sample_rng = random.Random(0x161101542)
    columns = _column_rows(inst)
    for _ in range(sample_total):
        candidate = random_candidate(inst, sample_rng)
        if _is_cover_fast(inst, candidate, columns):
            sample_hits += 1
    guess_probability = sample_hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "observed_probability": guess_probability,
        "structure_aware_space": search_space(inst),
        "prior": "uniform over all n-subsets of the displayed universe",
    }

    t0 = time.perf_counter()
    reference_answer, reference_operations = _full_ap_reference(inst)
    reference_wall = time.perf_counter() - t0
    reference_ok = reference_answer is not None and verify(inst, reference_answer)[0]
    t0 = time.perf_counter()
    algorithm_x_answer, algorithm_x_nodes, algorithm_x_capped = _algorithm_x(inst)
    algorithm_x_wall = time.perf_counter() - t0
    algorithm_x_ok = (
        not algorithm_x_capped
        and algorithm_x_answer is not None
        and verify(inst, algorithm_x_answer)[0]
    )
    demo_inst = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    report["G5_density_and_baseline"] = {
        "pass": reference_ok and algorithm_x_ok and isinstance(guess_probability, float),
        "shipping_density_hits": sample_hits,
        "shipping_density_samples": sample_total,
        "shipping_solution_fraction_estimate": guess_probability,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo_inst),
        "baseline_algorithm": "Algorithm X exact-cover search",
        "baseline_wall_seconds": round(algorithm_x_wall, 6),
        "baseline_search_nodes": algorithm_x_nodes,
        "baseline_solved": bool(algorithm_x_ok),
        "certificate_scan_wall_seconds": round(reference_wall, 6),
        "certificate_scan_modular_operations": reference_operations,
        "certificate_scan_solved": bool(reference_ok),
    }

    attack_counts = {
        "incidence_and_codegree_outlier": 0,
        "greedy_first_fit": 0,
        "random_restart_256": 0,
        "first_pair_progression_ansatz": 0,
    }
    reference_successes = 0
    reference_ops = []
    reference_times = []
    algorithm_x_successes = 0
    algorithm_x_nodes_all = []
    algorithm_x_times = []
    for seed in _SELFTEST_SEEDS:
        trial = make_instance(seed=10_000 + seed, **shipping)
        # Every label has incidence frequency three.  Probe the stronger local
        # statistic left by the untouched plant: pair codegrees inside its edge.
        outlier = _codegree_outlier_candidate(trial)
        attack_counts["incidence_and_codegree_outlier"] += int(
            verify(trial, outlier)[0]
        )
        greedy = _greedy_candidate(trial)
        attack_counts["greedy_first_fit"] += int(
            greedy is not None and verify(trial, greedy)[0]
        )
        restarted = _random_restart(trial, 256, 700_000 + seed)
        attack_counts["random_restart_256"] += int(restarted is not None)
        ansatz = _first_pair_progression(trial)
        attack_counts["first_pair_progression_ansatz"] += int(verify(trial, ansatz)[0])

        start_time = time.perf_counter()
        found, ops = _full_ap_reference(trial)
        reference_times.append(time.perf_counter() - start_time)
        reference_ops.append(ops)
        reference_successes += int(found is not None and verify(trial, found)[0])

        start_time = time.perf_counter()
        exact_cover, nodes, capped = _algorithm_x(trial)
        algorithm_x_times.append(time.perf_counter() - start_time)
        algorithm_x_nodes_all.append(nodes)
        algorithm_x_successes += int(
            not capped and exact_cover is not None and verify(trial, exact_cover)[0]
        )

    attacks = {
        name: {"successes": successes, "attempts": len(_SELFTEST_SEEDS)}
        for name, successes in attack_counts.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attacks.values())
        and reference_successes == len(_SELFTEST_SEEDS)
        and algorithm_x_successes == len(_SELFTEST_SEEDS),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Algorithm X exact-cover search",
            "complexity": "O(degree^n) worst case with minimum-column branching",
            "wall_clock_sec_mean": round(sum(algorithm_x_times) / len(algorithm_x_times), 6),
            "wall_clock_sec_max": round(max(algorithm_x_times), 6),
            "operations": round(sum(algorithm_x_nodes_all) / len(algorithm_x_nodes_all)),
            "operations_total_over_8": sum(algorithm_x_nodes_all),
            "nodes_mean": round(sum(algorithm_x_nodes_all) / len(algorithm_x_nodes_all), 3),
            "nodes_max": max(algorithm_x_nodes_all),
            "solves": f"{algorithm_x_successes}/{len(_SELFTEST_SEEDS)}, as expected",
        },
        "certificate_algorithm": {
            "name": "full ordered-pair modular arithmetic-progression scan",
            "complexity": "O((degree*n)^2 * n) exact modular operations",
            "wall_clock_sec_mean": round(sum(reference_times) / len(reference_times), 6),
            "wall_clock_sec_max": round(max(reference_times), 6),
            "operations": reference_ops[0] if len(set(reference_ops)) == 1 else reference_ops,
            "solves": f"{reference_successes}/{len(_SELFTEST_SEEDS)}, as expected",
        },
    }

    doubled = make_instance(
        n=2 * shipping["n"], degree=shipping["degree"], seed=91_337
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    escalated = escalate(dict(shipping))
    escalated_ok = False
    if isinstance(escalated, dict):
        escalated_inst = make_instance(seed=91_338, **escalated)
        escalated_ok = verify(escalated_inst, escalated_inst["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and escalated_ok,
        "base_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_reason": doubled_reason,
        "escalated_params": escalated,
        "fixed_answer_axis": "degree",
    }

    invariant_checks = 0
    transformation_checks = 0
    distinct_keys = []
    g8_failures = []
    for seed in range(20):
        base = make_instance(seed=20_000 + seed, **shipping)
        base_key = canonical_key(base)
        distinct_keys.append(base_key)
        rng = random.Random(30_000 + seed)

        row_order = list(range(len(base["sets"])))
        rng.shuffle(row_order)
        labels = list(base["universe"])
        shuffled_labels = labels[:]
        rng.shuffle(shuffled_labels)
        arbitrary_map = dict(zip(labels, shuffled_labels))
        relabelled = _relabel_instance(base, arbitrary_map, row_order)
        # Also reverse the internal presentation order, another irrelevant input order.
        relabelled["sets"] = [list(reversed(row)) for row in relabelled["sets"]]

        multiplier = rng.randrange(1, base["prime"])
        translation = rng.randrange(base["prime"])
        affine_map = {
            x: (multiplier * x + translation) % base["prime"] for x in labels
        }
        affine = _relabel_instance(base, affine_map, list(reversed(row_order)))

        composed_map = {x: affine_map[arbitrary_map[x]] for x in labels}
        composed = _relabel_instance(base, composed_map, list(reversed(row_order)))

        for name, transformed in (
            ("arbitrary+rows", relabelled),
            ("affine+rows", affine),
            ("arbitrary+affine+rows", composed),
        ):
            invariant_checks += 1
            if canonical_key(transformed) != base_key:
                g8_failures.append(f"seed {seed} {name} changed key")
            transformation_checks += 1
            ok, why = verify(transformed, transformed["answer"])
            if not ok:
                g8_failures.append(f"seed {seed} {name} invalid: {why}")

    distinct_count = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_count == 20,
        "invariance_checks": invariant_checks,
        "valid_transformation_checks": transformation_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct_count,
        "failures": g8_failures,
        "invariant_scope": "rooted closed walks and local codegrees; not full GI canonicalization",
    }

    answer_chars, answer_tokens, answer_elements = _answer_sizes(inst["answer"])
    # The prime is 1,000,003, so only three possible labels have seven digits;
    # all other labels have at most six.  This is a seed-independent JSON bound.
    worst_answer_chars = 2 + 2 * (inst["n"] - 1) + 7 * min(3, inst["n"])
    worst_answer_chars += 6 * max(0, inst["n"] - 3)
    worst_answer_tokens = math.ceil(worst_answer_chars / 4)
    # Mergesort needs at most n*ceil(log2(n))-2^ceil(log2(n))+1 comparisons.
    merge_levels = math.ceil(math.log2(inst["n"]))
    sort_comparisons = inst["n"] * merge_levels - (1 << merge_levels) + 1
    intended_operations = (inst["n"] - 1) + sort_comparisons
    arms = _G9_RESULTS["arms"]
    hinted_attempts = arms["hinted"]["attempts"]
    within_caps = (
        worst_answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else 0.0
    )
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else 0.0
    )
    report["G9_no_tool_suitability"] = {
        # Since 2026-09-05 the three arms, including the hinted arm, are
        # diagnostic only.  G9 is gated solely by the answer/effort caps.
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _G9_RESULTS["hinted_verdict"],
        "diagnostic_note": _G9_RESULTS["note"],
        "diagnostic_complete": hinted_attempts >= 3
        and arms["placebo"]["attempts"] >= 3
        and arms["bare"]["attempts"] >= 3,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_chars_worst_case_bound": worst_answer_chars,
        "answer_tokens_worst_case_bound": worst_answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "route_breakdown": {
            "modular_additions": inst["n"] - 1,
            "mergesort_comparisons_worst_case": sort_comparisons,
        },
        "caps_pass": within_caps,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
