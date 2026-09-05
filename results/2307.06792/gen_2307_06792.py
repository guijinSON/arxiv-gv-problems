"""Verified generator for succinct planar vertex-disjoint-path instances.

The problem is the native Planar Disjoint Paths problem defined in Section 1
of Wlodarczyk and Zehavi, arXiv:2307.06792.  Instances are complete binary
trees with a few pendant decorations, represented exactly by an affine vertex
labelling.  Terminal pairs are sampled in disjoint rooted subtrees, so their
unique paths and hence a certificate are known before the public labels are
chosen.  Generation never searches for paths.
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
from collections import deque


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "succinctly represented undirected planar tree",
        "pairwise disjoint terminal pairs",
        "vertex paths",
    ],
    "verification_operations": [
        "exact modular decoding of vertex labels",
        "integer parent-child adjacency comparison",
        "set-based vertex-disjointness comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Undo the affine vertex relabelling to expose binary-tree ancestry; "
        "without this coordinate change, ordinary graph search explores a "
        "large ball in the succinct tree."
    ),
    "hardness_basis": (
        "Track B: breadth-first search finds each unique tree path in O(V+E); "
        "at provisional shipping n=22 selftest measures about 2.7 million edge "
        "scans and 0.6 seconds per instance, while affine decoding plus parent "
        "chains takes fewer than 300 exact arithmetic operations."
    ),
    "max_answer_tokens": 130,
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

DIFFICULTY = {
    "demo": {"n": 4, "route_depth": 2, "pairs": 2, "decoys": 2},
    "easy": {"n": 21, "route_depth": 16, "pairs": 2, "decoys": 12},
    "medium": {"n": 22, "route_depth": 16, "pairs": 2, "decoys": 16},
    "hard": {"n": 23, "route_depth": 16, "pairs": 2, "decoys": 20},
}
SHIPPING_DIFFICULTY = "medium"

STRUCTURAL_HINT = (
    "The public vertex labels are an affine image of rooted binary-tree "
    "coordinates."
)
PLACEBO_HINT = (
    "The public vertex labels require careful attention to the stated integer "
    "conventions."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list containing one ordered simple vertex path per listed "
        "terminal pair, in pair order.  Path i has exactly the declared number "
        "of vertices, begins at s_i, ends at t_i, and all listed public labels "
        "are distinct globally."
    ),
    "bounds": {
        "n_paths": "instance pairs",
        "vertices_per_path": "instance path_lengths[i]",
        "vertex_labels": "affine labels of positions 1..vertex_count",
        "global_repetition": "forbidden",
        "max_atomic_elements": 256,
    },
}

NOTES = (
    "Section 1 fixes the native problem: for pairwise distinct terminal pairs "
    "(s_i,t_i) in an undirected planar graph, output pairwise vertex-disjoint "
    "s_i-t_i paths.  Section 1.3 and Theorem 1.5 identify the easy side: the "
    "general planar problem is FPT in k and solvable in 2^{O(k^2)} n^{O(1)} "
    "time; for this generated tree subfamily, ordinary BFS is already linear. "
    "Therefore the family is Track B, not an average-case or Track-A claim. "
    "The certificate is produced by composition of identities: endpoints are "
    "sampled in disjoint rooted subtrees, their parent chains meet at the known "
    "anchor, and an affine injection modulo a prime carries every path into "
    "public labels.  Pendant chains and all off-route tree vertices are decoys; "
    "they are drawn independently of which child suffixes become terminals. "
    "The attack panel tests degree outliers, numeric-label greed, random "
    "non-backtracking restarts, and the tempting public-label heap ansatz. "
    "The successful BFS reference algorithm is disclosed separately, as Track "
    "B requires.  The paper's Section 5 Set Cover reduction was not used: its "
    "multi-layer flow, weight, and subcubic gadgets would make the output "
    "certificate exceed the no-tool cap at meaningful parameters."
)


# These values are replaced with script-owned evidence after the three oracle
# runs.  The conservative defaults make G9(b) fail before that evidence exists.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 3, "attempts": 3},
    "hinted": {"solved": 3, "attempts": 3},
    "placebo": {"solved": 3, "attempts": 3},
    "hinted_verdict": "not_run",
}


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"```(?:json|text)?\s*(.*?)```", re.I | re.S)
_ENUMERATION_CAP = 200_000
_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate(n, route_depth, pairs, decoys):
    for name, value in (
        ("n", n), ("route_depth", route_depth),
        ("pairs", pairs), ("decoys", decoys),
    ):
        if not _is_int(value):
            raise ValueError(f"{name} must be an integer")
    if not 3 <= n <= 60:
        raise ValueError("n must lie in 3..60")
    if pairs != 2:
        raise ValueError("this family currently requires pairs=2")
    if not 2 <= route_depth < n:
        raise ValueError("route_depth must lie in 2..n-1")
    if not 0 <= decoys <= 64:
        raise ValueError("decoys must lie in 0..64")


def _is_prime(value):
    """Deterministic Miller-Rabin for unsigned 64-bit integers."""
    if value < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for prime in small:
        if value % prime == 0:
            return value == prime
    d = value - 1
    power = 0
    while d % 2 == 0:
        power += 1
        d //= 2
    for base in (2, 325, 9375, 28178, 450775, 9780504, 1795265022):
        if base % value == 0:
            continue
        x = pow(base, d, value)
        if x in (1, value - 1):
            continue
        for _ in range(power - 1):
            x = (x * x) % value
            if x == value - 1:
                break
        else:
            return False
    return True


def _next_prime(value):
    candidate = max(3, value | 1)
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _euclid_divisions(a, p):
    count = 0
    while a:
        p, a = a, p % a
        count += 1
    return count


def _encode(inst, position):
    return (inst["multiplier"] * position + inst["offset"]) % inst["modulus"]


def _decode(inst, label, inverse=None):
    if not _is_int(label):
        return None
    if inverse is None:
        inverse = pow(inst["multiplier"], -1, inst["modulus"])
    position = (inverse * (label - inst["offset"])) % inst["modulus"]
    if 1 <= position <= inst["vertex_count"] and _encode(inst, position) == label:
        return position
    return None


def _position_depth(position):
    return position.bit_length() - 1


def _tree_path(source, target):
    left = []
    right = []
    a, b = source, target
    while a != b:
        if a > b:
            left.append(a)
            a //= 2
        else:
            right.append(b)
            b //= 2
    left.append(a)
    return left + list(reversed(right))


def _sample_descendant(rng, anchor, target_depth, first_bit):
    bits_needed = target_depth - _position_depth(anchor)
    position = 2 * anchor + first_bit
    for _ in range(bits_needed - 1):
        position = 2 * position + rng.getrandbits(1)
    return position


def make_instance(n, seed=0, route_depth=None, pairs=2, decoys=12, **params):
    """Inverse-generate two unique, vertex-disjoint paths in a planar tree."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    if route_depth is None:
        route_depth = min(16, n - 1) if _is_int(n) else 16
    _validate(n, route_depth, pairs, decoys)
    rng = random.Random(seed)

    base_vertices = (1 << (n + 1)) - 1
    decoration_specs = []
    used_bases = set()
    decoration_vertices = 0
    for _ in range(decoys):
        # Decorations occur throughout the tree, not just near the planted paths.
        while True:
            base = rng.randrange(2, base_vertices + 1)
            if base not in used_bases:
                used_bases.add(base)
                break
        length = rng.randint(1, 3)
        start = base_vertices + decoration_vertices + 1
        chain = list(range(start, start + length))
        decoration_vertices += length
        decoration_specs.append((base, chain))

    vertex_count = base_vertices + decoration_vertices
    if n <= 6:
        modulus = _next_prime(vertex_count + 2 * rng.randrange(2, 12) + 1)
    else:
        modulus = _next_prime(vertex_count + 2 * rng.randrange(1009, 1_000_003) + 1)
    while True:
        multiplier = rng.randrange(2, modulus - 1)
        divisions = _euclid_divisions(multiplier, modulus)
        if n <= 6 or 12 <= divisions <= 24:
            break
    offset = rng.randrange(modulus)

    shell = {
        "paper": "arXiv:2307.06792",
        "family": "affinely labelled planar-tree disjoint paths",
        "tree_depth": n,
        "route_depth": route_depth,
        "pair_count": pairs,
        "base_vertices": base_vertices,
        "vertex_count": vertex_count,
        "modulus": modulus,
        "multiplier": multiplier,
        "offset": offset,
    }

    # Anchors 2 and 3 root disjoint subtrees.  The two endpoints are sampled
    # symmetrically from opposite child halves, so neither endpoint is planted
    # from a different marginal distribution.
    terminal_positions = []
    path_positions = []
    for anchor in (2, 3):
        s = _sample_descendant(rng, anchor, route_depth, 0)
        t = _sample_descendant(rng, anchor, route_depth, 1)
        path = _tree_path(s, t)
        terminal_positions.append((s, t))
        path_positions.append(path)

    shell["terminal_pairs"] = [
        [_encode(shell, s), _encode(shell, t)] for s, t in terminal_positions
    ]
    shell["path_lengths"] = [len(path) for path in path_positions]
    shell["decorations"] = [
        {
            "base": _encode(shell, base),
            "chain": [_encode(shell, position) for position in chain],
        }
        for base, chain in decoration_specs
    ]
    shell["answer"] = [
        [_encode(shell, position) for position in path]
        for path in path_positions
    ]
    shell["inverse_euclid_divisions"] = divisions
    return shell


def render(inst):
    lines = [
        "Find two pairwise vertex-disjoint paths in the planar graph below.",
        "",
        "Graph definition (complete and exact).",
        "The graph is simple, undirected, and finite.  It is a complete rooted binary tree with some pendant chains, so it is planar.",
        f"Let D={inst['tree_depth']}, N=2^(D+1)-1={inst['base_vertices']}, P={inst['modulus']}, A={inst['multiplier']}, and B={inst['offset']}.",
        "For every integer x with 1 <= x <= the vertex_count below, define its public vertex label E(x)=(A*x+B) mod P.",
        f"The vertex set is E(1),...,E({inst['vertex_count']}); these labels are distinct because P>{inst['vertex_count']} and A is nonzero modulo prime P.",
        "For every 1 <= x <= (N-1)/2, add the two tree edges {E(x),E(2x)} and {E(x),E(2x+1)}.",
        "The only additional edges are the pendant chains listed next.  A row 'base: c1 c2 ...' adds edges {base,c1},{c1,c2},... .",
        "",
        "Pendant chains (public labels):",
    ]
    if inst["decorations"]:
        for decoration in inst["decorations"]:
            labels = " ".join(str(x) for x in decoration["chain"])
            lines.append(f"  {decoration['base']}: {labels}")
    else:
        lines.append("  (none)")
    lines.extend([
        "",
        "Terminal pairs, in required output order (all labels are public labels):",
    ])
    for index, ((source, target), length) in enumerate(
        zip(inst["terminal_pairs"], inst["path_lengths"])
    ):
        lines.append(
            f"  pair {index}: s={source}, t={target}; output exactly {length} vertices"
        )
    lines.extend([
        "",
        "A path is an ordered list of distinct vertex labels beginning at its stated s, ending at its stated t, with every consecutive pair joined by an edge.",
        "The two paths must share no vertex.  Repetitions are forbidden, labels are decimal integers, and pair numbering is zero-based.",
        "",
        "Give your final answer inside <answer></answer> tags as one JSON list of two integer lists, one path per pair in the displayed order.",
        "Example format: <answer>[[12,34,56],[78,90,11]]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def _parse_json_fragment(text):
    cleaned = text.strip()
    fence = _FENCE_RE.fullmatch(cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        return json.loads(cleaned)
    except (TypeError, ValueError):
        decoder = json.JSONDecoder()
        for index, character in enumerate(cleaned):
            if character != "[":
                continue
            try:
                value, _ = decoder.raw_decode(cleaned[index:])
                return value
            except ValueError:
                continue
    return None


def parse_answer(text):
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if match:
        return _parse_json_fragment(match.group(1))
    fence = _FENCE_RE.search(text)
    if fence:
        return _parse_json_fragment(fence.group(1))
    return _parse_json_fragment(text)


def _decoration_maps(inst, inverse=None):
    if inverse is None:
        inverse = pow(inst["multiplier"], -1, inst["modulus"])
    neighbor_map = {}
    for decoration in inst["decorations"]:
        base = _decode(inst, decoration["base"], inverse)
        chain = [_decode(inst, label, inverse) for label in decoration["chain"]]
        if base is None or any(position is None for position in chain):
            return None
        previous = base
        for position in chain:
            neighbor_map.setdefault(previous, []).append(position)
            neighbor_map.setdefault(position, []).append(previous)
            previous = position
    return neighbor_map


def _neighbors(inst, position, decoration_map=None):
    result = []
    base_vertices = inst["base_vertices"]
    if position <= base_vertices:
        if position > 1:
            result.append(position // 2)
        if 2 * position <= base_vertices:
            result.extend((2 * position, 2 * position + 1))
    if decoration_map is None:
        decoration_map = _decoration_maps(inst) or {}
    result.extend(decoration_map.get(position, ()))
    return result


def verify(inst, answer):
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) != inst["pair_count"]:
        return False, f"wrong path count: expected {inst['pair_count']}"
    inverse = pow(inst["multiplier"], -1, inst["modulus"])
    decoration_map = _decoration_maps(inst, inverse)
    if decoration_map is None:
        return False, "instance has malformed decoration labels"
    used = set()
    for index, path in enumerate(answer):
        if not isinstance(path, list):
            return False, f"path {index} must be a JSON list"
        if len(path) != inst["path_lengths"][index]:
            return False, f"path {index} has wrong declared length"
        if any(not _is_int(label) for label in path):
            return False, f"path {index} contains a non-integer label"
        positions = [_decode(inst, label, inverse) for label in path]
        if any(position is None for position in positions):
            return False, f"path {index} contains a label outside the vertex set"
        source, target = inst["terminal_pairs"][index]
        if path[0] != source or path[-1] != target:
            return False, f"path {index} has wrong endpoint orientation"
        if len(set(path)) != len(path):
            return False, f"path {index} repeats a vertex"
        for step, (left, right) in enumerate(zip(positions, positions[1:])):
            if right not in _neighbors(inst, left, decoration_map):
                return False, f"path {index} step {step} is not an edge"
        overlap = used.intersection(path)
        if overlap:
            return False, f"path {index} intersects an earlier path"
        used.update(path)
    return True, "ok"


def _falling_factorial(n, k):
    value = 1
    for offset in range(k):
        value *= n - offset
    return value


def search_space(inst):
    internal = sum(length - 2 for length in inst["path_lengths"])
    available = inst["vertex_count"] - 2 * inst["pair_count"]
    return _falling_factorial(available, internal)


def random_candidate(inst, rng):
    """Sample uniformly after enforcing shape, endpoints, and no repetitions."""
    terminal_positions = {
        _decode(inst, label)
        for pair in inst["terminal_pairs"] for label in pair
    }
    internal_total = sum(length - 2 for length in inst["path_lengths"])
    chosen = []
    chosen_set = set()
    while len(chosen) < internal_total:
        position = rng.randrange(1, inst["vertex_count"] + 1)
        if position in terminal_positions or position in chosen_set:
            continue
        chosen.append(position)
        chosen_set.add(position)
    answer = []
    cursor = 0
    for (source, target), length in zip(
        inst["terminal_pairs"], inst["path_lengths"]
    ):
        count = length - 2
        middle = [_encode(inst, x) for x in chosen[cursor:cursor + count]]
        cursor += count
        answer.append([source] + middle + [target])
    return answer


def enumerate_all(inst):
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    terminals = {
        _decode(inst, label)
        for pair in inst["terminal_pairs"] for label in pair
    }
    allowed = [
        position for position in range(1, inst["vertex_count"] + 1)
        if position not in terminals
    ]
    internal_counts = [length - 2 for length in inst["path_lengths"]]
    valid = 0
    for selected in itertools.permutations(allowed, sum(internal_counts)):
        cursor = 0
        candidate = []
        for (source, target), count in zip(inst["terminal_pairs"], internal_counts):
            middle = [_encode(inst, x) for x in selected[cursor:cursor + count]]
            cursor += count
            candidate.append([source] + middle + [target])
        valid += int(verify(inst, candidate)[0])
    return valid


def _tree_distance(left, right):
    return len(_tree_path(left, right)) - 1


def canonical_key(inst):
    """Invariant under affine labels, pair order/orientation, and tree mirrors.

    A metric signature of all marked attachment bases is used instead of full
    tree isomorphism; it is the strongest cheap invariant needed here.
    """
    terminal_pairs = [
        tuple(_decode(inst, label) for label in pair)
        for pair in inst["terminal_pairs"]
    ]
    decorations = [
        (_decode(inst, item["base"]), len(item["chain"]))
        for item in inst["decorations"]
    ]
    candidates = []
    for order in itertools.permutations(range(len(terminal_pairs))):
        for flips in itertools.product((0, 1), repeat=len(terminal_pairs)):
            terminals = []
            for new_index, old_index in enumerate(order):
                pair = terminal_pairs[old_index]
                if flips[new_index]:
                    pair = (pair[1], pair[0])
                terminals.extend(pair)
            term_metric = [
                _tree_distance(terminals[i], terminals[j])
                for i in range(len(terminals))
                for j in range(i + 1, len(terminals))
            ]
            decoration_features = sorted(
                [length] + [_tree_distance(base, terminal) for terminal in terminals]
                for base, length in decorations
            )
            decoration_metric = sorted(
                (min(li, lj), max(li, lj), _tree_distance(bi, bj))
                for i, (bi, li) in enumerate(decorations)
                for bj, lj in decorations[i + 1:]
            )
            candidates.append((term_metric, decoration_features, decoration_metric))
    payload = {
        "tree_depth": inst["tree_depth"],
        "path_lengths": sorted(inst["path_lengths"]),
        "signature": min(candidates),
    }
    data = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()


def escalate(params):
    current = dict(params)
    current.pop("_preset", None)
    n = current.get("n")
    route_depth = current.get("route_depth", 16)
    decoys = current.get("decoys", 12)
    if not _is_int(n):
        return None
    if n < 44:
        current["n"] = n + 2
        current["decoys"] = min(64, decoys + 4)
        return current
    if route_depth < 24:
        # Once extra depth lies outside the BFS ball, enlarge that ball while
        # the certificate remains far below both output caps.
        current["n"] = min(60, n + 1)
        current["route_depth"] = route_depth + 2
        current["decoys"] = min(64, decoys + 4)
        return current
    return "cap_bound"


def _reference_bfs(inst):
    decoration_map = _decoration_maps(inst) or {}
    paths = []
    edge_scans = 0
    visited_total = 0
    for source_label, target_label in inst["terminal_pairs"]:
        source = _decode(inst, source_label)
        target = _decode(inst, target_label)
        queue = deque([source])
        predecessor = {source: None}
        while queue:
            vertex = queue.popleft()
            if vertex == target:
                break
            for neighbor in _neighbors(inst, vertex, decoration_map):
                edge_scans += 1
                if neighbor not in predecessor:
                    predecessor[neighbor] = vertex
                    queue.append(neighbor)
        visited_total += len(predecessor)
        if target not in predecessor:
            return None, {"edge_scans": edge_scans, "visited": visited_total}
        reverse_path = []
        cursor = target
        while cursor is not None:
            reverse_path.append(cursor)
            cursor = predecessor[cursor]
        paths.append([_encode(inst, x) for x in reversed(reverse_path)])
    return paths, {"edge_scans": edge_scans, "visited": visited_total}


def _compact_route(inst):
    answer = []
    for source_label, target_label in inst["terminal_pairs"]:
        source = _decode(inst, source_label)
        target = _decode(inst, target_label)
        answer.append([_encode(inst, x) for x in _tree_path(source, target)])
    return answer


def _walk_by_rule(inst, chooser):
    decoration_map = _decoration_maps(inst) or {}
    result = []
    for pair_index, (source_label, target_label) in enumerate(inst["terminal_pairs"]):
        current = _decode(inst, source_label)
        previous = None
        path = [source_label]
        for step in range(inst["path_lengths"][pair_index] - 1):
            choices = [x for x in _neighbors(inst, current, decoration_map) if x != previous]
            if not choices:
                break
            nxt = chooser(inst, choices, target_label, step)
            previous, current = current, nxt
            path.append(_encode(inst, current))
        result.append(path)
    return result


def _attack_degree(inst):
    decoration_map = _decoration_maps(inst) or {}
    return _walk_by_rule(
        inst,
        lambda graph, choices, target, step: min(
            choices,
            key=lambda x: (-len(_neighbors(graph, x, decoration_map)), _encode(graph, x)),
        ),
    )


def _attack_numeric_greedy(inst):
    return _walk_by_rule(
        inst,
        lambda graph, choices, target, step: min(
            choices, key=lambda x: abs(_encode(graph, x) - target)
        ),
    )


def _attack_random_restart(inst, rng, restarts=256):
    decoration_map = _decoration_maps(inst) or {}
    for _ in range(restarts):
        candidate = []
        for pair_index, (source_label, target_label) in enumerate(inst["terminal_pairs"]):
            current = _decode(inst, source_label)
            previous = None
            path = [source_label]
            for _step in range(inst["path_lengths"][pair_index] - 1):
                choices = [x for x in _neighbors(inst, current, decoration_map) if x != previous]
                if not choices:
                    break
                nxt = rng.choice(choices)
                previous, current = current, nxt
                path.append(_encode(inst, current))
            candidate.append(path)
        if verify(inst, candidate)[0]:
            return candidate
    return candidate


def _raw_heap_path(source, target):
    if source <= 0 or target <= 0:
        return [source, target]
    return _tree_path(source, target)


def _attack_public_label_heap(inst):
    return [
        _raw_heap_path(source, target)
        for source, target in inst["terminal_pairs"]
    ]


def _mirror_position(position, base_vertices):
    if position > base_vertices:
        return position
    depth = _position_depth(position)
    leading = 1 << depth
    suffix = position - leading
    mask = leading - 1
    return leading + (suffix ^ mask)


def _transformed_instance(inst, *, multiplier=None, offset=None,
                          reorder=False, reverse=False, mirror=False):
    """Carry an isomorphism and its known witness through the instance."""
    old = inst
    new = copy.deepcopy(inst)
    if multiplier is None:
        multiplier = old["multiplier"]
    if offset is None:
        offset = old["offset"]
    new["multiplier"] = multiplier
    new["offset"] = offset

    def carry(label, decoration=False):
        position = _decode(old, label)
        if mirror and not decoration:
            position = _mirror_position(position, old["base_vertices"])
        return _encode(new, position)

    new_decorations = []
    for item in old["decorations"]:
        new_decorations.append({
            "base": carry(item["base"]),
            "chain": [carry(label, decoration=True) for label in item["chain"]],
        })
    new["decorations"] = new_decorations
    new["terminal_pairs"] = [
        [carry(pair[0]), carry(pair[1])] for pair in old["terminal_pairs"]
    ]
    new["answer"] = [
        [carry(label) for label in path] for path in old["answer"]
    ]
    if reverse:
        new["terminal_pairs"] = [[b, a] for a, b in new["terminal_pairs"]]
        new["answer"] = [list(reversed(path)) for path in new["answer"]]
    if reorder:
        new["terminal_pairs"].reverse()
        new["path_lengths"].reverse()
        new["answer"].reverse()
    return new


def _answer_size(answer):
    blob = json.dumps(answer, separators=(",", ":"))
    atoms = sum(len(path) for path in answer)
    return len(blob), (len(blob) + 3) // 4, atoms


def _intended_operations(inst):
    # One Euclidean division per inverse step; three primitive arithmetic
    # operations per endpoint decode and output-label encode; one parent
    # division for every non-anchor edge of each known route.
    atoms = sum(inst["path_lengths"])
    endpoint_decodes = 2 * inst["pair_count"]
    parent_steps = sum(length - 1 for length in inst["path_lengths"])
    return (
        inst["inverse_euclid_divisions"]
        + 3 * endpoint_decodes
        + parent_steps
        + 3 * atoms
    )


def selftest():
    report = {
        "paper": "arXiv:2307.06792",
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
                failures.append({"preset": preset, "seed": seed, "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures,
    }

    shipping = make_instance(seed=230706792, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    drop = copy.deepcopy(planted)
    drop.pop()
    swap = copy.deepcopy(planted)
    swap[0][1], swap[0][2] = swap[0][2], swap[0][1]
    duplicate = copy.deepcopy(planted)
    duplicate[0][2] = duplicate[0][1]
    out_of_range = copy.deepcopy(planted)
    out_of_range[0][1] = shipping["modulus"]
    corruptions = {
        "drop_one_path": drop,
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
        "The affine coordinates give the following paths.\n"
        "```json\n<answer>\n" + answer_text + "\n</answer>\n```\n"
        "I checked every consecutive edge."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no answer here") is None,
        "path_count": len(parsed) if isinstance(parsed, list) else None,
    }

    guess_rng = random.Random(0x230706792)
    hits = 0
    guess_started = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_elapsed = time.perf_counter() - guess_started
    density = hits / _G4_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6,
        "hits": hits,
        "total": _G4_SAMPLES,
        "observed_probability": density,
        "structure_aware_space": search_space(shipping),
        "sampling_rule": "uniform ordered internal vertices after fixing shape, endpoints, public vertex membership, and global distinctness",
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attack_functions = {
        "degree_outlier_walk": lambda inst, rng: _attack_degree(inst),
        "greedy_public_label_distance": lambda inst, rng: _attack_numeric_greedy(inst),
        "random_nonbacktracking_256": lambda inst, rng: _attack_random_restart(inst, rng, 256),
        "public_label_heap_ansatz": lambda inst, rng: _attack_public_label_heap(inst),
    }
    attack_results = {
        name: {"successes": 0, "attempts": 0, "wall_clock_sec_total_8": 0.0}
        for name in attack_functions
    }
    attack_nodes = {
        "degree_outlier_walk": sum(shipping["path_lengths"]),
        "greedy_public_label_distance": sum(shipping["path_lengths"]),
        "random_nonbacktracking_256": 256 * sum(shipping["path_lengths"]),
        "public_label_heap_ansatz": 4 * shipping["modulus"].bit_length(),
    }
    seeds = list(range(8100, 8100 + _ATTACK_SEEDS))
    for seed in seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for offset, (name, function) in enumerate(attack_functions.items()):
            started = time.perf_counter()
            candidate = function(inst, random.Random(seed * 1009 + offset))
            elapsed = time.perf_counter() - started
            attack_results[name]["wall_clock_sec_total_8"] += elapsed
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])
            attack_results[name]["attempts"] += 1
    for result in attack_results.values():
        result["wall_clock_sec_total_8"] = round(result["wall_clock_sec_total_8"], 6)

    reference_successes = 0
    reference_seconds = 0.0
    reference_scans = []
    reference_visited = []
    compact_successes = 0
    for seed in seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        started = time.perf_counter()
        candidate, stats = _reference_bfs(inst)
        reference_seconds += time.perf_counter() - started
        reference_scans.append(stats["edge_scans"])
        reference_visited.append(stats["visited"])
        reference_successes += int(candidate is not None and verify(inst, candidate)[0])
        compact_successes += int(verify(inst, _compact_route(inst))[0])
    reference_algorithm = {
        "name": "breadth-first search for each pair in the tree",
        "complexity": "O(k(V+E)) time and O(V) memory on an explicit graph",
        "wall_clock_sec_total_8": round(reference_seconds, 6),
        "wall_clock_sec_mean": round(reference_seconds / _ATTACK_SEEDS, 6),
        "edge_scans_mean": sum(reference_scans) // len(reference_scans),
        "edge_scans_min": min(reference_scans),
        "edge_scans_max": max(reference_scans),
        "visited_vertices_mean": sum(reference_visited) // len(reference_visited),
        "solves": f"{reference_successes}/{_ATTACK_SEEDS}, as expected",
    }
    all_failed = all(item["successes"] == 0 for item in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == _ATTACK_SEEDS and compact_successes == _ATTACK_SEEDS,
        "attacks": attack_results,
        "reference_algorithm": reference_algorithm,
        "compact_route": {
            "name": "affine decode, binary-tree parent chains, affine encode",
            "operations": _intended_operations(shipping),
            "solves": f"{compact_successes}/{_ATTACK_SEEDS}, as expected",
        },
    }

    strongest_name = max(
        attack_results,
        key=lambda name: attack_results[name]["wall_clock_sec_total_8"],
    )
    report["G5_density_and_baseline_cost"] = {
        "pass": density < 1e-6 and all_failed,
        "shipping_density_estimate": density,
        "density_hits": hits,
        "density_samples": _G4_SAMPLES,
        "construction_proven_solution_count": 1,
        "candidate_space": search_space(shipping),
        "strongest_failing_attack": strongest_name,
        "attack_node_or_restart_budget_total_8": attack_nodes[strongest_name] * _ATTACK_SEEDS,
        "attack_wall_clock_sec_total_8": attack_results[strongest_name]["wall_clock_sec_total_8"],
        "reference_algorithm_edge_scans_mean": reference_algorithm["edge_scans_mean"],
        "reference_algorithm_wall_clock_sec_mean": reference_algorithm["wall_clock_sec_mean"],
        "demo_exact_valid_answers": enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"])),
    }

    doubled_parameters = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_parameters["n"] += 1  # complete-tree vertex count is thereby doubled
    doubled = make_instance(seed=707, **doubled_parameters)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["vertex_count"] >= 2 * shipping["base_vertices"],
        "shipping_n": shipping["tree_depth"],
        "doubled_n": doubled["tree_depth"],
        "shipping_vertices": shipping["vertex_count"],
        "doubled_vertices": doubled["vertex_count"],
        "answer_elements_before": sum(shipping["path_lengths"]),
        "answer_elements_after": sum(doubled["path_lengths"]),
        "verify_reason": doubled_reason,
    }

    invariance_checks = 0
    invariance_failures = []
    carried_checks = 0
    for seed in range(20):
        inst = make_instance(seed=9000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        base_key = canonical_key(inst)
        rng = random.Random(12000 + seed)
        new_multiplier = rng.randrange(2, inst["modulus"] - 1)
        new_offset = rng.randrange(inst["modulus"])
        variants = (
            _transformed_instance(inst, reorder=True),
            _transformed_instance(inst, reverse=True),
            _transformed_instance(inst, multiplier=new_multiplier, offset=new_offset),
            _transformed_instance(
                inst, multiplier=new_multiplier, offset=new_offset,
                reorder=True, reverse=True, mirror=True,
            ),
        )
        for variant_index, variant in enumerate(variants):
            invariance_checks += 1
            if canonical_key(variant) != base_key:
                invariance_failures.append({"seed": seed, "variant": variant_index})
            if variant_index == 3:
                carried_checks += 1
                if not verify(variant, variant["answer"])[0]:
                    invariance_failures.append({"seed": seed, "variant": "carried witness"})
    unrelated_keys = [
        canonical_key(make_instance(seed=20000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY]))
        for seed in range(20)
    ]
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not invariance_failures and carried_checks >= 20 and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "invariance_failures": invariance_failures,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "symmetries_tested": [
            "terminal-pair reorder",
            "endpoint reversal",
            "new affine public relabelling",
            "composition with global rooted-tree mirror",
        ],
    }

    answer_chars, answer_tokens, answer_elements = _answer_size(shipping["answer"])
    intended_operations = _intended_operations(shipping)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    hinted_hardened = G9_ORACLE_RESULTS["hinted_verdict"] == "hardened"
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
