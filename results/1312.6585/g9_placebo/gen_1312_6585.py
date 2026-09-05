"""Verified distance-dominating-set generator for arXiv:1312.6585.

The paper's Section 4 defines r-Dominating Set and gives the dynamic-programming
encoder used by its explicit kernel.  This module stays in that native graph
language.  It inverse-generates a tree from radius-r pieces around a known
dominating set, adds construction-independent decoy leaves, and carries the
witness through a reversible relabelling of the vertices.

The family is Track B.  A standard exact greedy algorithm for distance
domination on trees is polynomial and is measured separately.  The intended
no-tool route is shorter: undo the displayed coordinate relabelling and notice
the periodic centers of the induced path.
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
import sys
import time
from collections import deque


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # The family itself needs only the standard library.
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite labelled tree",
        "closed radius-r graph neighborhoods",
        "r-dominating vertex set",
    ],
    "verification_operations": [
        "integer range, distinctness, and coordinate-order checks",
        "exact multi-source breadth-first traversal to radius r",
        "exact coverage comparison against the vertex set",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Undo the public bit-reversal coordinate relabelling: its first "
        "k(2r+1) coordinates induce a path whose radius-r block centers form "
        "a dominating set; without that change of variables one must solve "
        "distance domination on the fully shuffled tree."
    ),
    "hardness_basis": (
        "Track B: exact deepest-undominated-vertex greedy on trees runs in "
        "O(k(n+m)+n) time in the measured implementation; shipping-preset "
        "wall-clock and operation counts are recorded by selftest, while the "
        "coordinate route uses at most 242 exact bit/integer operations."
    ),
    "max_answer_tokens": 19,
}

NATIVE: dict = {
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


DIFFICULTY: dict = {
    "hard": {"n": 2048, "r": 8, "k": 16},
}

SHIPPING_DIFFICULTY: str = "hard"

STRUCTURAL_HINT: str = (
    "The first k(2r+1) inverse-mixed coordinates induce one path divided into equal radius-r blocks."
)
PLACEBO_HINT: str = (
    "Careful bookkeeping of zero-based vertex labels and undirected edges prevents indexing mistakes."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON list of exactly k distinct vertex labels from 0 through n-1, "
        "ordered by increasing inverse-mixed coordinate; the selected vertices "
        "must r-dominate the whole displayed tree."
    ),
    "bounds": {
        "length": "k",
        "entry_range": "0 <= v < n",
        "distinct": True,
        "order": "strictly increasing inverse-mixed coordinate",
        "candidate_count": "binomial(n,k)",
        "max_named_preset_length": 16,
    },
}


# Replaced only after reading the script-owned harden.py transcripts.  API
# errors are not attempts and therefore remain 0/0.
G9_EVIDENCE: dict = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "not_run",
}


NOTES: str = r"""
Section 4 fixes the native definition used here: an r-dominating set S has at
most k vertices and every vertex outside S is at graph distance at most r from
S.  The same section's Lemma 4.1 defines the (2r+1)-state-per-boundary-vertex
dynamic-programming encoder and proves it DP-friendly.  Theorem 4.2 combines
that encoder with the Section 3 protrusion machinery to give a constructive
linear kernel for every fixed r on graphs excluding a fixed apex minor.  It
also records a triple-exponential dependence on r in the displayed constant.

The Step-0 certificate question rules out Track A for this distribution.  Every
generated graph is a tree, and an exact tree algorithm repeatedly takes a
deepest uncovered vertex and selects its r-th ancestor.  The implementation
below measures that successful reference algorithm and reports it outside the
failing attacks.  This is a polynomial certificate producer; the paper's
kernelization is preprocessing and is not misreported as a solver.

Generation is inverse and never solves the completed instance.  First choose
k equally spaced centers on a path of k(2r+1) vertices.  Each center covers its
whole length-(2r+1) block.  Every remaining vertex is made a leaf adjacent near
one of a block's two ends, but still within distance r of that block's center.
Thus the selected centers dominate by construction.  Decoy leaves concentrate
near block boundaries, making boundary vertices competitive under local
coverage statistics without changing validity.  Finally an invertible affine,
XOR, and bit-reversal map relabels every vertex and carries the certificate.

The compact route uses the public relabelling map and the periodic path centers.
At hard, sixteen evaluations each use one multiplication, addition, reduction,
XOR, and eleven bit placements, plus the two small parameter operations: at
most 242 exact operations.  The reference tree scan touches the shuffled input
and its radius-r neighborhoods and is measured on eight seeds in selftest.

The adversary panel targets the planting: largest radius-r neighborhoods,
highest-degree uncovered greediness, 256 legal random restarts, and the obvious
but wrong boundary phase in inverse coordinates.  Decoys and plants use the
same vertex label permutation; pendant multiplicities and edge order are
sampled independently after the centers have been fixed.  canonical_key uses
the exact AHU unlabelled-tree canonical form, so it is invariant under arbitrary
vertex and edge relabelling rather than keying on the seed or rendered text.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _validate_params(n: int, r: int, k: int) -> None:
    for name, value in (("n", n), ("r", r), ("k", k)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if n < 2 or n & (n - 1):
        raise ValueError("n must be a power of two")
    if r < 1 or k < 1:
        raise ValueError("r and k must be positive")
    if k * (2 * r + 1) > n:
        raise ValueError("n must be at least k*(2r+1)")


def _reverse_bits(value: int, bits: int) -> int:
    result = 0
    for _ in range(bits):
        result = (result << 1) | (value & 1)
        value >>= 1
    return result


def _mix_vertex(x: int, n: int, mix: dict) -> int:
    z = ((mix["multiplier"] * x + mix["addend"]) % n) ^ mix["xor_mask"]
    return _reverse_bits(z, mix["bits"])


def _unmix_vertex(vertex: int, n: int, mix: dict) -> int:
    z = _reverse_bits(vertex, mix["bits"]) ^ mix["xor_mask"]
    return (mix["inverse_multiplier"] * (z - mix["addend"])) % n


def _ordered_by_coordinate(inst: dict, vertices: list[int]) -> list[int]:
    return sorted(vertices, key=lambda v: _unmix_vertex(v, inst["n"], inst["mix"]))


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a labelled tree and a known r-dominating set."""

    r = params.pop("r", 8)
    k = params.pop("k", 16)
    if params:
        raise ValueError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, r, k)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    q = 2 * r + 1
    base_n = k * q

    # Logical vertices 0..base_n-1 form the path.  All remaining vertices are
    # leaves, assigned nearly evenly to blocks and attached close to a randomly
    # chosen side.  Offset 1 or q-2 keeps the leaf exactly distance r from the
    # planted center; offsets 2 or q-3 create statistically similar decoys.
    logical_edges: list[tuple[int, int]] = [
        (v, v + 1) for v in range(base_n - 1)
    ]
    blocks = list(range(k))
    rng.shuffle(blocks)
    near_offsets = (1, 2, q - 3, q - 2)
    for index, leaf in enumerate(range(base_n, n)):
        block = blocks[index % k]
        # Re-shuffle each complete pass so no block acquires a position signal.
        if index and index % k == 0:
            rng.shuffle(blocks)
            block = blocks[0]
        offset = near_offsets[rng.randrange(len(near_offsets))]
        logical_edges.append((leaf, block * q + offset))

    bits = n.bit_length() - 1
    multiplier = rng.randrange(1, n, 2)
    addend = rng.randrange(n)
    xor_mask = rng.randrange(n)
    mix = {
        "bits": bits,
        "multiplier": multiplier,
        "inverse_multiplier": pow(multiplier, -1, n),
        "addend": addend,
        "xor_mask": xor_mask,
    }

    edges = [
        sorted((_mix_vertex(u, n, mix), _mix_vertex(v, n, mix)))
        for u, v in logical_edges
    ]
    rng.shuffle(edges)
    answer = [_mix_vertex(block * q + r, n, mix) for block in range(k)]

    return {
        "family": "r-Dominating Set on a labelled tree",
        "n": n,
        "r": r,
        "k": k,
        "base_path_vertices": base_n,
        "mix": mix,
        "edges": edges,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the complete solver-facing problem, with no default hint."""

    mix = inst["mix"]
    lines = [
        "Distance domination in a labelled tree",
        "",
        f"The vertex set is the integers 0 through {inst['n'] - 1}.",
        "Every pair [u,v] below is one undirected edge; there are no loops or",
        "parallel edges.  The displayed graph is a tree.",
        "",
        f"Let r={inst['r']} and k={inst['k']}.  A set D r-dominates the tree if",
        "every vertex has graph distance at most r from at least one vertex in D.",
        "Graph distance is the number of edges in a shortest path, so a selected",
        "vertex has distance zero from D.",
        "",
        "The labels also carry a public reversible coordinate relabelling.  For",
        f"a coordinate x in 0..{inst['n'] - 1}, compute",
        f"  z = (({mix['multiplier']}*x + {mix['addend']}) mod {inst['n']}) XOR {mix['xor_mask']},",
        f"then reverse exactly {mix['bits']} binary bits of z (including leading",
        "zeros).  Call the resulting vertex label L(x).  XOR is bitwise exclusive-or.",
        "This coordinate data is part of the labelled instance; it does not alter",
        "the graph-distance definition above.",
        "",
        "Edges:",
    ]
    # Several edges per line keep large native instances writable and readable.
    edge_tokens = [f"[{u},{v}]" for u, v in inst["edges"]]
    for start in range(0, len(edge_tokens), 12):
        lines.append("  " + " ".join(edge_tokens[start : start + 12]))

    lines.extend(
        [
            "",
            f"Find exactly {inst['k']} distinct vertex labels whose set r-dominates",
            "the whole tree.  (Requiring exactly k is equivalent here to the usual",
            "at-most-k question, because any smaller dominating set can be padded",
            "with unused vertices.)  List the labels in strictly increasing x-coordinate",
            "order, where v=L(x); numeric label order is irrelevant.  Repeats are forbidden.",
            "Any witness satisfying these conditions is accepted.",
            "",
            "Give your final answer inside <answer></answer> tags as one JSON list",
            f"of exactly {inst['k']} integers.",
            "Example: <answer>[3,17,42]</answer>",
            "Whitespace inside the tags is allowed. Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Parse a tagged JSON integer list while tolerating surrounding prose."""

    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    payload = match.group(1).strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        value = json.loads(payload)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list) or any(
        isinstance(v, bool) or not isinstance(v, int) for v in value
    ):
        return None
    return value


def _adjacency(inst: dict) -> list[list[int]]:
    n = inst["n"]
    adjacency = [[] for _ in range(n)]
    for edge in inst["edges"]:
        if not isinstance(edge, list) or len(edge) != 2:
            raise ValueError("malformed edge")
        u, v = edge
        if not (0 <= u < n and 0 <= v < n) or u == v:
            raise ValueError("malformed edge endpoint")
        adjacency[u].append(v)
        adjacency[v].append(u)
    return adjacency


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check one witness exactly, without consulting inst['answer']."""

    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) < inst["k"]:
        return False, f"too few vertices: expected {inst['k']}"
    if len(answer) > inst["k"]:
        return False, f"too many vertices: expected {inst['k']}"
    if any(isinstance(v, bool) or not isinstance(v, int) for v in answer):
        return False, "every vertex label must be an integer"
    if any(v < 0 or v >= inst["n"] for v in answer):
        return False, f"vertex label outside 0..{inst['n'] - 1}"
    if len(set(answer)) != len(answer):
        return False, "vertex labels must be distinct"
    coordinates = [
        _unmix_vertex(v, inst["n"], inst["mix"]) for v in answer
    ]
    if any(a >= b for a, b in zip(coordinates, coordinates[1:])):
        return False, "vertices are not in increasing inverse-mixed coordinate order"

    try:
        adjacency = _adjacency(inst)
    except (TypeError, ValueError) as exc:
        return False, f"malformed instance: {exc}"
    distance = [-1] * inst["n"]
    queue = deque()
    for vertex in answer:
        distance[vertex] = 0
        queue.append(vertex)
    while queue:
        vertex = queue.popleft()
        if distance[vertex] == inst["r"]:
            continue
        for neighbor in adjacency[vertex]:
            if distance[neighbor] < 0:
                distance[neighbor] = distance[vertex] + 1
                queue.append(neighbor)
    missing = next((v for v, d in enumerate(distance) if d < 0), None)
    if missing is not None:
        return False, f"vertex {missing} is farther than r from the proposed set"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample a legal-shape k-set and put it in required order."""

    candidate = rng.sample(range(inst["n"]), inst["k"])
    return _ordered_by_coordinate(inst, candidate)


def search_space(inst: dict) -> int | None:
    """The exact number of legal-shape candidates."""

    return math.comb(inst["n"], inst["k"])


def enumerate_all(inst: dict) -> int | None:
    """Count all valid witnesses when at most 200,000 legal sets exist."""

    if search_space(inst) > 200_000:
        return None
    count = 0
    for vertices in itertools.combinations(range(inst["n"]), inst["k"]):
        candidate = _ordered_by_coordinate(inst, list(vertices))
        if verify(inst, candidate)[0]:
            count += 1
    return count


def _tree_centers(adjacency: list[list[int]]) -> list[int]:
    n = len(adjacency)
    if n <= 2:
        return list(range(n))
    degree = [len(row) for row in adjacency]
    leaves = deque(v for v, d in enumerate(degree) if d <= 1)
    remaining = n
    while remaining > 2:
        layer = len(leaves)
        remaining -= layer
        for _ in range(layer):
            leaf = leaves.popleft()
            for neighbor in adjacency[leaf]:
                degree[neighbor] -= 1
                if degree[neighbor] == 1:
                    leaves.append(neighbor)
    return sorted(leaves)


def _rooted_tree_code(adjacency: list[list[int]], root: int, blocked: int = -1) -> str:
    parent = {root: blocked}
    order = [root]
    for vertex in order:
        for neighbor in adjacency[vertex]:
            if neighbor != parent[vertex]:
                parent[neighbor] = vertex
                order.append(neighbor)
    codes: dict[int, str] = {}
    for vertex in reversed(order):
        child_codes = [
            codes[neighbor]
            for neighbor in adjacency[vertex]
            if parent.get(neighbor) == vertex
        ]
        codes[vertex] = "(" + "".join(sorted(child_codes)) + ")"
    return codes[root]


def canonical_key(inst: dict) -> str:
    """Exact AHU canonical key for the unlabelled tree, plus r and k."""

    adjacency = _adjacency(inst)
    centers = _tree_centers(adjacency)
    if len(centers) == 1:
        code = _rooted_tree_code(adjacency, centers[0])
    else:
        left = _rooted_tree_code(adjacency, centers[0], centers[1])
        right = _rooted_tree_code(adjacency, centers[1], centers[0])
        code = "(" + "".join(sorted((left, right))) + ")"
    payload = json.dumps(
        {"r": inst["r"], "k": inst["k"], "tree": code},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Double the decoy haystack while keeping r, k, and witness length fixed."""

    current = dict(params)
    n = current.get("n")
    r = current.get("r", 8)
    k = current.get("k", 16)
    if not isinstance(n, int):
        return None
    next_n = n * 2
    next_bits = next_n.bit_length() - 1
    compact_operations = 2 + k * (next_bits + 4)
    if compact_operations > 300:
        return "cap_bound"
    return {"n": next_n, "r": r, "k": k}


def _coverage_masks(inst: dict) -> list[int]:
    adjacency = _adjacency(inst)
    masks: list[int] = []
    for source in range(inst["n"]):
        seen = {source}
        frontier = [source]
        for _ in range(inst["r"]):
            next_frontier = []
            for vertex in frontier:
                for neighbor in adjacency[vertex]:
                    if neighbor not in seen:
                        seen.add(neighbor)
                        next_frontier.append(neighbor)
            frontier = next_frontier
            if not frontier:
                break
        mask = 0
        for vertex in seen:
            mask |= 1 << vertex
        masks.append(mask)
    return masks


def _fast_valid(inst: dict, answer: list[int], masks: list[int]) -> bool:
    if len(answer) != inst["k"] or len(set(answer)) != len(answer):
        return False
    covered = 0
    for vertex in answer:
        if not 0 <= vertex < inst["n"]:
            return False
        covered |= masks[vertex]
    return covered.bit_count() == inst["n"]


def _reference_tree_greedy(inst: dict) -> tuple[list[int] | None, dict]:
    """Exact minimum distance-r domination greedy for a tree."""

    started = time.perf_counter()
    adjacency = _adjacency(inst)
    operations = 2 * len(inst["edges"])
    root = next((v for v, row in enumerate(adjacency) if len(row) == 1), 0)
    operations += inst["n"]

    parent = [-1] * inst["n"]
    depth = [-1] * inst["n"]
    depth[root] = 0
    traversal = [root]
    for vertex in traversal:
        for neighbor in adjacency[vertex]:
            operations += 1
            if depth[neighbor] < 0:
                depth[neighbor] = depth[vertex] + 1
                parent[neighbor] = vertex
                traversal.append(neighbor)

    by_depth = sorted(range(inst["n"]), key=lambda v: depth[v], reverse=True)
    operations += inst["n"]
    dominated = [False] * inst["n"]
    selected: list[int] = []
    for vertex in by_depth:
        operations += 1
        if dominated[vertex]:
            continue
        center = vertex
        for _ in range(inst["r"]):
            operations += 1
            if parent[center] >= 0:
                center = parent[center]
        if center not in selected:
            selected.append(center)
        queue = deque([(center, 0)])
        seen = {center}
        while queue:
            current, distance = queue.popleft()
            dominated[current] = True
            operations += 1
            if distance == inst["r"]:
                continue
            for neighbor in adjacency[current]:
                operations += 1
                if neighbor not in seen:
                    seen.add(neighbor)
                    queue.append((neighbor, distance + 1))

    raw_selected = len(selected)
    if raw_selected > inst["k"]:
        return None, {
            "operations": operations,
            "wall_clock_sec": time.perf_counter() - started,
            "selected_before_padding": raw_selected,
        }
    used = set(selected)
    if len(selected) < inst["k"]:
        for vertex in range(inst["n"]):
            if vertex not in used:
                selected.append(vertex)
                used.add(vertex)
                operations += 1
                if len(selected) == inst["k"]:
                    break
    answer = _ordered_by_coordinate(inst, selected)
    operations += len(answer) * math.ceil(math.log2(max(2, len(answer))))
    return answer, {
        "operations": operations,
        "wall_clock_sec": time.perf_counter() - started,
        "selected_before_padding": raw_selected,
    }


def _compact_coordinate_answer(inst: dict) -> tuple[list[int], dict]:
    started = time.perf_counter()
    q = 2 * inst["r"] + 1
    answer = [
        _mix_vertex(block * q + inst["r"], inst["n"], inst["mix"])
        for block in range(inst["k"])
    ]
    operations = 2 + inst["k"] * (inst["mix"]["bits"] + 4)
    return answer, {
        "operations": operations,
        "wall_clock_sec": time.perf_counter() - started,
    }


def _attack_outlier_coverage(inst: dict, masks: list[int]) -> list[int]:
    ranked = sorted(
        range(inst["n"]),
        key=lambda v: (-masks[v].bit_count(), v),
    )[: inst["k"]]
    return _ordered_by_coordinate(inst, ranked)


def _attack_degree_outlier(inst: dict) -> list[int]:
    adjacency = _adjacency(inst)
    ranked = sorted(
        range(inst["n"]), key=lambda v: (-len(adjacency[v]), v)
    )[: inst["k"]]
    return _ordered_by_coordinate(inst, ranked)


def _attack_greedy_coverage(inst: dict, masks: list[int]) -> list[int]:
    chosen: list[int] = []
    available = set(range(inst["n"]))
    covered = 0
    for _ in range(inst["k"]):
        best = min(
            available,
            key=lambda v: (-(masks[v] & ~covered).bit_count(), v),
        )
        chosen.append(best)
        available.remove(best)
        covered |= masks[best]
    return _ordered_by_coordinate(inst, chosen)


def _attack_boundary_phase(inst: dict) -> list[int]:
    q = 2 * inst["r"] + 1
    candidate = [
        _mix_vertex(block * q, inst["n"], inst["mix"])
        for block in range(inst["k"])
    ]
    return candidate


def _relabel_instance(inst: dict, permutation: list[int]) -> dict:
    transformed = copy.deepcopy(inst)
    transformed["edges"] = [
        [permutation[u], permutation[v]] for u, v in transformed["edges"]
    ]
    transformed["answer"] = _ordered_by_coordinate(
        transformed, [permutation[v] for v in inst["answer"]]
    )
    return transformed


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest() -> dict:
    report: dict = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures = []
    attempts = 0
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
            else:
                failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "verified": attempts - len(failures),
        "attempts": attempts,
        "json_roundtrips": json_roundtrips,
        "failures": failures,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    corruptions: dict[str, tuple[bool, str]] = {}
    corruptions["empty"] = verify(shipping, [])
    corruptions["dropped"] = verify(shipping, shipping["answer"][:-1])
    swapped = list(shipping["answer"])
    swapped[0], swapped[1] = swapped[1], swapped[0]
    corruptions["swapped"] = verify(shipping, swapped)
    duplicated = list(shipping["answer"])
    duplicated[1] = duplicated[0]
    corruptions["duplicated"] = verify(shipping, duplicated)
    out_of_range = list(shipping["answer"])
    out_of_range[0] = shipping["n"]
    corruptions["out_of_range"] = verify(shipping, out_of_range)
    reasons = {name: result[1] for name, result in corruptions.items()}
    report["G2_rejects_corruption"] = {
        "pass": (
            all(not result[0] for result in corruptions.values())
            and len(set(reasons.values())) == len(reasons)
        ),
        "reasons": reasons,
        "distinct_reasons": len(set(reasons.values())),
    }

    model_response = (
        "I found a distance-dominating set.\n```text\n<answer>"
        + json.dumps(shipping["answer"])
        + "</answer>\n```\nThe coordinates are in the requested order."
    )
    parsed = parse_answer(model_response)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and parse_answer("garbage") is None,
        "model_style_roundtrip": parsed == shipping["answer"],
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    shipping_masks = _coverage_masks(shipping)
    guess_rng = random.Random(20260905)
    guess_total = 200_000
    guess_hits = 0
    guess_started = time.perf_counter()
    # This is exactly random_candidate's uniform k-subset distribution and
    # required coordinate ordering, with inverse coordinates cached once so
    # the measurement does not repeatedly reverse the same label bits.
    coordinate_of = [
        _unmix_vertex(v, shipping["n"], shipping["mix"])
        for v in range(shipping["n"])
    ]
    for _ in range(guess_total):
        candidate = guess_rng.sample(range(shipping["n"]), shipping["k"])
        candidate.sort(key=coordinate_of.__getitem__)
        if _fast_valid(shipping, candidate, shipping_masks):
            guess_hits += 1
    guess_elapsed = time.perf_counter() - guess_started
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "empirical_probability": guess_probability,
        "structure_aware": True,
        "sampler": "uniform k-subset with mandatory coordinate ordering",
        "candidate_space": search_space(shipping),
        "wall_clock_sec": guess_elapsed,
    }

    reference_results = []
    compact_results = []
    attack_names = (
        "outlier_radius_neighborhood",
        "outlier_degree",
        "greedy_max_uncovered",
        "random_restart_256",
        "in_context_boundary_phase",
    )
    attack_successes = {name: 0 for name in attack_names}
    adversary_attempts = 8
    for seed in range(adversary_attempts):
        inst = make_instance(seed=10_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        masks = _coverage_masks(inst)

        reference_answer, reference_stats = _reference_tree_greedy(inst)
        reference_ok = (
            reference_answer is not None and verify(inst, reference_answer)[0]
        )
        reference_stats["verified"] = reference_ok
        reference_results.append(reference_stats)

        compact_answer, compact_stats = _compact_coordinate_answer(inst)
        compact_ok = verify(inst, compact_answer)[0]
        compact_stats["verified"] = compact_ok
        compact_results.append(compact_stats)

        candidates = {
            "outlier_radius_neighborhood": _attack_outlier_coverage(inst, masks),
            "outlier_degree": _attack_degree_outlier(inst),
            "greedy_max_uncovered": _attack_greedy_coverage(inst, masks),
            "in_context_boundary_phase": _attack_boundary_phase(inst),
        }
        for name, candidate in candidates.items():
            if _fast_valid(inst, candidate, masks):
                attack_successes[name] += 1

        restart_rng = random.Random(30_000 + seed)
        restart_solved = False
        for _ in range(256):
            candidate = random_candidate(inst, restart_rng)
            if _fast_valid(inst, candidate, masks):
                restart_solved = True
                break
        if restart_solved:
            attack_successes["random_restart_256"] += 1

    median_reference_wall = statistics.median(
        result["wall_clock_sec"] for result in reference_results
    )
    median_reference_ops = int(
        statistics.median(result["operations"] for result in reference_results)
    )
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": (
            guess_hits == 0
            and demo_count is not None
            and demo_count > 0
            and all(result["verified"] for result in reference_results)
        ),
        "shipping_valid_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_estimate": guess_probability,
        "demo_exact_valid_answer_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_wall_clock_sec": median_reference_wall,
        "baseline_operations": median_reference_ops,
    }

    attacks = {
        name: {"successes": successes, "attempts": adversary_attempts}
        for name, successes in attack_successes.items()
    }
    report["G6_adversary_panel"] = {
        "pass": (
            all(item["successes"] == 0 for item in attacks.values())
            and all(result["verified"] for result in reference_results)
            and all(result["verified"] for result in compact_results)
        ),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "deepest-undominated-vertex greedy for distance domination on trees",
            "complexity": "O(k(n+m)+n) for this direct exact implementation",
            "wall_clock_sec_median": median_reference_wall,
            "operations_median": median_reference_ops,
            "solves": (
                f"{sum(result['verified'] for result in reference_results)}/"
                f"{adversary_attempts}, as expected"
            ),
        },
        "compact_route": {
            "name": "inverse-coordinate path-block centers",
            "operations": int(
                statistics.median(result["operations"] for result in compact_results)
            ),
            "solves": (
                f"{sum(result['verified'] for result in compact_results)}/"
                f"{adversary_attempts}"
            ),
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (
            doubled_ok
            and doubled["n"] == 2 * shipping["n"]
            and len(doubled["answer"]) == len(shipping["answer"])
        ),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_decoy_leaves": shipping["n"] - shipping["base_path_vertices"],
        "doubled_decoy_leaves": doubled["n"] - doubled["base_path_vertices"],
        "answer_length_both": len(shipping["answer"]),
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = 0
    witness_checks = 0
    invariant_failures = []
    for seed in range(20):
        inst = make_instance(seed=40_000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)

        reordered = copy.deepcopy(inst)
        reordered["edges"] = list(reversed(reordered["edges"]))

        permutation = list(range(inst["n"]))
        random.Random(50_000 + seed).shuffle(permutation)
        relabelled = _relabel_instance(inst, permutation)

        composed = _relabel_instance(reordered, list(reversed(range(inst["n"]))))
        composed["edges"] = [[v, u] for u, v in reversed(composed["edges"])]

        for label, transformed in (
            ("edge_reorder", reordered),
            ("vertex_relabel", relabelled),
            ("composed", composed),
        ):
            invariance_checks += 1
            if canonical_key(transformed) != key:
                invariant_failures.append([seed, label, "canonical key changed"])
            witness_checks += 1
            ok, reason = verify(transformed, transformed["answer"])
            if not ok:
                invariant_failures.append([seed, label, reason])

    unrelated_keys = {
        canonical_key(
            make_instance(
                seed=60_000 + seed,
                **DIFFICULTY[SHIPPING_DIFFICULTY],
            )
        )
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and len(unrelated_keys) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": witness_checks,
        "distinct_unrelated_keys": len(unrelated_keys),
        "unrelated_attempts": 20,
        "failures": invariant_failures,
        "method": "exact AHU unlabelled-tree canonical form",
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(shipping["answer"])
    intended_operations = 2 + shipping["k"] * (shipping["mix"]["bits"] + 4)
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    arms = copy.deepcopy(G9_EVIDENCE["arms"])
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    if hinted["attempts"] and placebo["attempts"]:
        hinted_minus_placebo = (
            hinted["solved"] / hinted["attempts"]
            - placebo["solved"] / placebo["attempts"]
        )
    else:
        hinted_minus_placebo = None
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2))
