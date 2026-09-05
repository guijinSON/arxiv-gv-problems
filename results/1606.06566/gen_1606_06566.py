"""Verified generator for affine band-graph path decompositions.

The native definitions and certificate are from Sections 2, 4, and 5 of
Martin Fuerer's "Faster Computation of Path-Width" (arXiv:1606.06566).
The generator chooses a vertex order first, puts edges only between vertices
at distance at most k in that order, and then emits the resulting nice path
decomposition.  It never computes path-width or searches for a decomposition.
"""

from __future__ import annotations

import copy
import functools
import hashlib
import json
import math
import os
import random
import re
import sys
import time


# Make the repository helper library available when this file is run from its
# own result directory.  This family needs only integers, so it remains fully
# standard-library-only when gvlib is absent.
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "undirected graph with residue-labelled vertices",
        "nice path decomposition encoded by introduce/forget ranks",
    ],
    "verification_operations": [
        "integer rank permutation comparison",
        "exact bag-size counting",
        "exact edge interval-overlap comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize that modular edge-label differences hide an affine image "
        "of a banded vertex order; without that coordinate change one must "
        "search over width-bounded path-decomposition events."
    ),
    "hardness_basis": (
        "Track B: the theorem in Section 5 computes path-width and a path "
        "decomposition in 2^{O(k^2)}n time, while the executable subset "
        "dynamic program used here takes O(n 2^n) time; at shipping n=23, "
        "k=7 it averages 2.63 seconds and 6.46 million transitions over "
        "eight seeds, whereas the affine-difference route uses at most 225 "
        "exact integer operations."
    ),
    "max_answer_tokens": 47,
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
    "demo": {
        "n": 5,
        "width": 2,
        "density_num": 3,
        "density_den": 5,
        "modulus": 59,
    },
    "easy": {
        "n": 17,
        "width": 5,
        "density_num": 3,
        "density_den": 4,
        "modulus": 1009,
    },
    "medium": {
        "n": 20,
        "width": 6,
        "density_num": 4,
        "density_den": 5,
        "modulus": 1009,
    },
    "hard": {
        "n": 23,
        "width": 7,
        "density_num": 43,
        "density_den": 50,
        "modulus": 1009,
    },
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The modular edge-label differences are an affine image of the small "
    "distances in one hidden vertex order."
)
PLACEBO_HINT = (
    "The introduction and forgetting ranks require careful attention to all "
    "of the stated indexing conventions."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "An n-by-2 JSON integer matrix.  Row i gives the introduction and "
        "forgetting ranks of the i-th vertex in the displayed ascending "
        "vertex list; all ranks 0..2n-1 occur once, introduction precedes "
        "forgetting, and at most k+1 intervals are active."
    ),
    "bounds": {
        "rows": "n",
        "columns": 2,
        "rank_min": 0,
        "rank_max": "2n-1",
        "all_ranks_distinct": True,
        "maximum_simultaneous_intervals": "k+1",
    },
}

NOTES = (
    "Section 2 fixes the exact native object: a nice path decomposition is a "
    "2n-event introduce/forget sequence, every vertex is introduced before "
    "it is forgotten, every graph edge appears together in a bag, and width "
    "is maximum bag size minus one.  Section 4, Theorem 1, gives the "
    "2^{O(ell*k)}n width-reduction algorithm from an ell-width decomposition; "
    "Section 5 and its corollary give a certificate-producing "
    "2^{O(k^2)}n algorithm for path-width k.  Thus fixed small k is explicitly "
    "the easy/FPT regime and a Track-A claim would be false.  This Track-B "
    "family chooses an affine order first and samples every non-backbone edge "
    "from the same Bernoulli distribution before writing the FIFO nice "
    "decomposition.  Degree sorting, numeric-label order, fewest-unvisited "
    "greed, and width-aware random restarts are audited.  The successful "
    "generic subset DP is disclosed separately from those failures."
)


# Filled from the script-owned oracle transcripts after the three arms run.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"```(?:json|text)?\s*(.*?)```", re.I | re.S)
_G4_SAMPLES = 200_000
_ENUMERATION_CAP = 200_000
_ATTACK_SEEDS = tuple(range(8))


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_prime(value):
    if not _is_int(value) or value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _validate_params(n, width, density_num, density_den, modulus):
    for name, value in (
        ("n", n),
        ("width", width),
        ("density_num", density_num),
        ("density_den", density_den),
        ("modulus", modulus),
    ):
        if not _is_int(value):
            raise ValueError(f"{name} must be an integer")
    if not 3 <= n <= 120:
        raise ValueError("n must lie in 3..120")
    if not 1 <= width <= (n - 1) // 2:
        raise ValueError("width must lie in 1..floor((n-1)/2)")
    if not 0 < density_num <= density_den:
        raise ValueError("density must satisfy 0 < numerator <= denominator")
    if not _is_prime(modulus) or modulus <= 10 * n:
        raise ValueError("modulus must be prime and greater than 10n")


def _adjacency(inst):
    vertices = inst["vertices"]
    index = {vertex: i for i, vertex in enumerate(vertices)}
    adjacency = [0] * len(vertices)
    for edge in inst["edges"]:
        if not isinstance(edge, (list, tuple)) or len(edge) != 2:
            raise ValueError("malformed edge")
        left, right = edge
        if left not in index or right not in index or left == right:
            raise ValueError("edge has an unknown endpoint or a loop")
        i, j = index[left], index[right]
        adjacency[i] |= 1 << j
        adjacency[j] |= 1 << i
    return adjacency


def _fifo_endpoints(order, width, n):
    """Nice path decomposition for a bandwidth-width vertex order."""
    endpoints = [[-1, -1] for _ in range(n)]
    rank = 0
    for position, vertex in enumerate(order):
        endpoints[vertex][0] = rank
        rank += 1
        if position >= width:
            endpoints[order[position - width]][1] = rank
            rank += 1
    for vertex in order[n - width :]:
        endpoints[vertex][1] = rank
        rank += 1
    return endpoints


def _decomposition_from_order(inst, order):
    """Turn any vertex-separation order into a nice path decomposition."""
    n = inst["n"]
    if sorted(order) != list(range(n)):
        return None
    adjacency = _adjacency(inst)
    position = [0] * n
    for i, vertex in enumerate(order):
        position[vertex] = i
    last_neighbor = list(position)
    for vertex in range(n):
        mask = adjacency[vertex]
        while mask:
            bit = mask & -mask
            neighbor = bit.bit_length() - 1
            last_neighbor[vertex] = max(last_neighbor[vertex], position[neighbor])
            mask ^= bit

    endpoints = [[-1, -1] for _ in range(n)]
    active = []
    rank = 0
    for i, vertex in enumerate(order):
        endpoints[vertex][0] = rank
        rank += 1
        active.append(vertex)
        keep = []
        for old in active:
            if last_neighbor[old] <= i:
                endpoints[old][1] = rank
                rank += 1
            else:
                keep.append(old)
        active = keep
    return endpoints


def make_instance(n, seed=0, **params):
    """Inverse-generate a graph and a nice path-decomposition certificate."""
    width = params.pop("width", max(1, n // 3))
    density_num = params.pop("density_num", 4)
    density_den = params.pop("density_den", 5)
    modulus = params.pop("modulus", 1009)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, width, density_num, density_den, modulus)
    rng = random.Random(seed)

    # Avoid multipliers whose first n residues are nearly monotone as ordinary
    # integers.  This is presentation randomisation, chosen before any edge.
    lower = 5 * n
    multipliers = [
        value
        for value in range(2, modulus - 1)
        if min(value, modulus - value) >= lower
    ]
    multiplier = rng.choice(multipliers)
    offset = rng.randrange(modulus)
    hidden_labels = [
        (multiplier * position + offset) % modulus for position in range(n)
    ]
    if len(set(hidden_labels)) != n:
        raise AssertionError("prime-modulus affine labels must be distinct")
    vertices = sorted(hidden_labels)
    to_index = {label: i for i, label in enumerate(vertices)}
    hidden_order = [to_index[label] for label in hidden_labels]

    edges = set()
    for distance in range(1, width + 1):
        for left_position in range(n - distance):
            # The distance-one path is the structural invariant.  The widest
            # diagonal is retained so the advertised width is not vacuous.
            keep = (
                distance in (1, width)
                or rng.randrange(density_den) < density_num
            )
            if keep:
                u = hidden_labels[left_position]
                v = hidden_labels[left_position + distance]
                edges.add((min(u, v), max(u, v)))

    answer = _fifo_endpoints(hidden_order, width, n)
    return {
        "family": "affinely relabelled band graph path decomposition",
        "n": n,
        "width": width,
        "density_num": density_num,
        "density_den": density_den,
        "modulus": modulus,
        "vertices": vertices,
        "edges": [list(edge) for edge in sorted(edges)],
        "answer": answer,
    }


def render(inst):
    n = inst["n"]
    vertices = inst["vertices"]
    edge_chunks = []
    edges = inst["edges"]
    for start in range(0, len(edges), 8):
        edge_chunks.append(
            "  "
            + " ".join(
                f"({left},{right})" for left, right in edges[start : start + 8]
            )
        )
    edge_text = "\n".join(edge_chunks)
    statement = f"""Construct a nice path decomposition of an undirected graph.

The graph has n={n} vertices.  Vertex names are distinct residues modulo
q={inst['modulus']}; they are merely names, and the complete ascending vertex
list is
  {' '.join(str(vertex) for vertex in vertices)}

Its undirected edges are the unordered pairs below.  There are no loops, no
parallel edges, and no edges other than those listed.
{edge_text}

A nice path decomposition is a sequence of exactly 2n events.  Every vertex is
introduced once and later forgotten once.  Starting with the empty set, the bag
after an introduction contains the new vertex, and the bag after a forgetting
does not contain the forgotten vertex.  Every listed edge must have both
endpoints together in at least one bag.  The width is the largest bag size minus
one.  Your decomposition must have width at most k={inst['width']}.

Encode the decomposition as a JSON matrix with exactly n rows and two integer
columns.  Row i corresponds to the i-th vertex in the ascending list above
(0-based row indexing).  Its entries [a,b] are that vertex's introduction rank
a and forgetting rank b.  Ranks are 0-based: every integer 0 through {2*n-1}
must occur exactly once in the matrix, and a<b in every row.  Rows may not be
reordered, and repeated ranks are forbidden.

Give your final answer inside <answer></answer> tags as the JSON matrix.
Example format: <answer>[[0,3],[1,2]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def _parse_json_list(fragment):
    try:
        value = json.loads(fragment.strip())
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, list) else None


def parse_answer(text):
    if not isinstance(text, str):
        return None
    tagged = _ANSWER_RE.search(text)
    if tagged:
        return _parse_json_list(tagged.group(1))
    for fenced in _FENCE_RE.finditer(text):
        parsed = _parse_json_list(fenced.group(1))
        if parsed is not None:
            return parsed
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\[", text):
        try:
            value, _ = decoder.raw_decode(text[match.start() :])
        except (ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, list):
            return value
    return None


def verify(inst, answer):
    """Check any valid nice path decomposition; never consult planted data."""
    n = inst.get("n")
    if not _is_int(n) or n < 1:
        return False, "instance has invalid n"
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) != n:
        return False, f"expected exactly {n} endpoint pairs"

    ranks = []
    for row, pair in enumerate(answer):
        if not isinstance(pair, list) or len(pair) != 2:
            return False, f"row {row} is not a two-entry JSON list"
        intro, forget = pair
        if not _is_int(intro) or not _is_int(forget):
            return False, f"row {row} contains a non-integer rank"
        if not (0 <= intro < 2 * n and 0 <= forget < 2 * n):
            return False, f"row {row} has a rank outside 0..{2*n-1}"
        if intro >= forget:
            return False, f"row {row} is not introduced before it is forgotten"
        ranks.extend((intro, forget))
    if len(set(ranks)) != 2 * n:
        return False, "event ranks are not all distinct"
    if set(ranks) != set(range(2 * n)):
        return False, "event ranks do not cover every integer in range"

    event = [None] * (2 * n)
    for vertex, (intro, forget) in enumerate(answer):
        event[intro] = (1, vertex)
        event[forget] = (-1, vertex)
    active = set()
    maximum = 0
    for rank, (kind, vertex) in enumerate(event):
        if kind == 1:
            if vertex in active:
                return False, f"vertex {vertex} is introduced twice"
            active.add(vertex)
        else:
            if vertex not in active:
                return False, f"vertex {vertex} is forgotten while absent"
            active.remove(vertex)
        maximum = max(maximum, len(active))
        if maximum - 1 > inst["width"]:
            return False, f"bag after event {rank} exceeds width {inst['width']}"
    if active:
        return False, "final bag is not empty"

    vertices = inst.get("vertices")
    if not isinstance(vertices, list) or len(vertices) != n or len(set(vertices)) != n:
        return False, "instance vertex list is malformed"
    index = {vertex: i for i, vertex in enumerate(vertices)}
    for edge_number, edge in enumerate(inst.get("edges", [])):
        if not isinstance(edge, list) or len(edge) != 2:
            return False, f"instance edge {edge_number} is malformed"
        if edge[0] not in index or edge[1] not in index:
            return False, f"instance edge {edge_number} has unknown endpoint"
        u, v = index[edge[0]], index[edge[1]]
        if not (
            answer[u][0] < answer[v][1]
            and answer[v][0] < answer[u][1]
        ):
            return False, f"edge {edge_number} is never covered by a bag"
    return True, "ok"


@functools.lru_cache(maxsize=None)
def _language_count(unintroduced, active, capacity):
    if unintroduced == 0 and active == 0:
        return 1
    total = 0
    if unintroduced and active < capacity:
        total += unintroduced * _language_count(
            unintroduced - 1, active + 1, capacity
        )
    if active:
        total += active * _language_count(unintroduced, active - 1, capacity)
    return total


def search_space(inst):
    return _language_count(inst["n"], 0, inst["width"] + 1)


def random_candidate(inst, rng):
    """Uniformly sample a labelled event sequence already respecting width."""
    n = inst["n"]
    capacity = inst["width"] + 1
    unintroduced = list(range(n))
    active = []
    endpoints = [[-1, -1] for _ in range(n)]
    for rank in range(2 * n):
        u, a = len(unintroduced), len(active)
        intro_suffix = (
            _language_count(u - 1, a + 1, capacity)
            if u and a < capacity
            else 0
        )
        forget_suffix = (
            _language_count(u, a - 1, capacity) if a else 0
        )
        intro_weight = u * intro_suffix
        forget_weight = a * forget_suffix
        choice = rng.randrange(intro_weight + forget_weight)
        if choice < intro_weight:
            selected = choice // intro_suffix
            vertex = unintroduced.pop(selected)
            active.append(vertex)
            endpoints[vertex][0] = rank
        else:
            choice -= intro_weight
            selected = choice // forget_suffix
            vertex = active.pop(selected)
            endpoints[vertex][1] = rank
    return endpoints


def enumerate_all(inst):
    if search_space(inst) > _ENUMERATION_CAP:
        return None
    n = inst["n"]
    capacity = inst["width"] + 1
    adjacency = _adjacency(inst)
    full = (1 << n) - 1

    @functools.lru_cache(maxsize=None)
    def count(introduced, active):
        if introduced == full and active == 0:
            return 1
        unintroduced = full ^ introduced
        total = 0
        if unintroduced and active.bit_count() < capacity:
            remaining = unintroduced
            while remaining:
                bit = remaining & -remaining
                total += count(introduced | bit, active | bit)
                remaining ^= bit
        forgettable = active
        while forgettable:
            bit = forgettable & -forgettable
            vertex = bit.bit_length() - 1
            if adjacency[vertex] & unintroduced == 0:
                total += count(introduced, active ^ bit)
            forgettable ^= bit
        return total

    return count(0, 0)


def _wl_canonical_data(inst):
    adjacency = _adjacency(inst)
    n = len(adjacency)
    colors = [mask.bit_count() for mask in adjacency]

    def compress(signatures):
        unique = {signature: i for i, signature in enumerate(sorted(set(signatures)))}
        return [unique[signature] for signature in signatures]

    colors = compress(colors)
    for _ in range(n + 1):
        signatures = []
        for vertex, mask in enumerate(adjacency):
            neighbor_colors = []
            while mask:
                bit = mask & -mask
                neighbor_colors.append(colors[bit.bit_length() - 1])
                mask ^= bit
            signatures.append((colors[vertex], tuple(sorted(neighbor_colors))))
        new_colors = compress(signatures)
        if new_colors == colors:
            break
        colors = new_colors

    color_count = max(colors) + 1
    classes = [[] for _ in range(color_count)]
    for vertex, color in enumerate(colors):
        classes[color].append(vertex)
    quotient = [[0] * color_count for _ in range(color_count)]
    for left in range(n):
        mask = adjacency[left]
        for right in range(left + 1, n):
            if mask >> right & 1:
                a, b = sorted((colors[left], colors[right]))
                quotient[a][b] += 1
    data = {
        "n": n,
        "width": inst["width"],
        "class_sizes": [len(group) for group in classes],
        "quotient": quotient,
    }
    if all(len(group) == 1 for group in classes):
        order = [group[0] for group in classes]
        bits = []
        for i in range(n):
            for j in range(i + 1, n):
                bits.append(1 if adjacency[order[i]] >> order[j] & 1 else 0)
        data["canonical_adjacency"] = bits
    else:
        # This is the strongest inexpensive invariant used for tied WL cells.
        # It can over-collide non-isomorphic graphs, but never separates two
        # relabellings of the same graph.
        data["stable_vertex_signatures"] = sorted(
            (colors[v], adjacency[v].bit_count()) for v in range(n)
        )
    return data


def canonical_key(inst):
    payload = json.dumps(
        _wl_canonical_data(inst), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def escalate(params):
    harder = dict(params)
    numerator = harder.get("density_num", 4)
    denominator = harder.get("density_den", 5)
    if numerator * 100 < 96 * denominator:
        target = min(96, math.floor(100 * numerator / denominator) + 5)
        harder["density_num"] = target
        harder["density_den"] = 100
        return harder
    n = harder["n"]
    if n >= 120:
        return "cap_bound"
    harder["n"] = min(120, n + 4)
    harder["width"] = min(harder["width"] + 1, (harder["n"] - 1) // 2)
    modulus = harder.get("modulus", 1009)
    if modulus <= 10 * harder["n"]:
        # The named ladder never reaches this branch; retain deterministic
        # support for future escalations without importing a primality package.
        candidate = 10 * harder["n"] + 1
        while not _is_prime(candidate):
            candidate += 1
        harder["modulus"] = candidate
    return harder


def _compact_recover(inst):
    """Recover the affine path from its unique n-1 modular difference class."""
    n, modulus = inst["n"], inst["modulus"]
    vertices = inst["vertices"]
    index = {vertex: i for i, vertex in enumerate(vertices)}
    counts = {}
    by_difference = {}
    for left, right in inst["edges"]:
        raw = (right - left) % modulus
        difference = min(raw, modulus - raw)
        counts[difference] = counts.get(difference, 0) + 1
        by_difference.setdefault(difference, []).append((left, right))
    candidates = [difference for difference, count in counts.items() if count == n - 1]
    for difference in sorted(candidates):
        path_adjacency = {vertex: [] for vertex in vertices}
        for left, right in by_difference[difference]:
            path_adjacency[left].append(right)
            path_adjacency[right].append(left)
        endpoints = [vertex for vertex in vertices if len(path_adjacency[vertex]) == 1]
        if len(endpoints) != 2 or any(
            len(path_adjacency[vertex]) not in (1, 2) for vertex in vertices
        ):
            continue
        order_labels = []
        previous = None
        current = min(endpoints)
        while current is not None:
            order_labels.append(current)
            options = [v for v in path_adjacency[current] if v != previous]
            following = options[0] if options else None
            previous, current = current, following
        if len(order_labels) == n and len(set(order_labels)) == n:
            order = [index[label] for label in order_labels]
            answer = _fifo_endpoints(order, inst["width"], n)
            if verify(inst, answer)[0]:
                return answer
    return None


def _reference_subset_dp(inst):
    """Generic O(n 2^n) vertex-separation DP with a carried witness."""
    n = inst["n"]
    if n > 24:
        return None, {
            "transitions": 0,
            "reachable_states": 0,
            "boundary_checks": 0,
            "refused_above_n": 24,
        }
    adjacency = _adjacency(inst)
    size = 1 << n
    full = size - 1
    neighbor_union = [0] * size
    for mask in range(1, size):
        bit = mask & -mask
        neighbor_union[mask] = (
            neighbor_union[mask ^ bit] | adjacency[bit.bit_length() - 1]
        )
    reachable = bytearray(size)
    parent = bytearray([255]) * size
    reachable[0] = 1
    transitions = 0
    valid_states = 0
    boundary_checks = 0
    for mask in range(size):
        if not reachable[mask]:
            continue
        boundary_checks += 1
        outside = full ^ mask
        boundary = mask & neighbor_union[outside]
        if boundary.bit_count() > inst["width"]:
            continue
        valid_states += 1
        remaining = outside
        while remaining:
            bit = remaining & -remaining
            new_mask = mask | bit
            transitions += 1
            if not reachable[new_mask]:
                reachable[new_mask] = 1
                parent[new_mask] = bit.bit_length() - 1
            remaining ^= bit
    if not reachable[full]:
        return None, {
            "transitions": transitions,
            "reachable_states": valid_states,
            "boundary_checks": boundary_checks,
        }
    reverse_order = []
    mask = full
    while mask:
        vertex = parent[mask]
        if vertex == 255:
            return None, {
                "transitions": transitions,
                "reachable_states": valid_states,
                "boundary_checks": boundary_checks,
            }
        reverse_order.append(vertex)
        mask ^= 1 << vertex
    order = list(reversed(reverse_order))
    answer = _decomposition_from_order(inst, order)
    return answer, {
        "transitions": transitions,
        "reachable_states": valid_states,
        "boundary_checks": boundary_checks,
    }


def _greedy_fewest_unvisited(inst):
    adjacency = _adjacency(inst)
    n = inst["n"]
    selected = 0
    order = []
    for _ in range(n):
        options = [vertex for vertex in range(n) if not (selected >> vertex & 1)]
        vertex = min(
            options,
            key=lambda v: (
                (adjacency[v] & ~selected).bit_count(),
                -(adjacency[v] & selected).bit_count(),
                v,
            ),
        )
        order.append(vertex)
        selected |= 1 << vertex
    return _decomposition_from_order(inst, order)


def _attack_candidates(inst, seed):
    adjacency = _adjacency(inst)
    n = inst["n"]
    label_orders = [list(range(n)), list(reversed(range(n)))]
    degree_orders = [
        sorted(range(n), key=lambda v: (adjacency[v].bit_count(), v)),
        sorted(range(n), key=lambda v: (-adjacency[v].bit_count(), v)),
    ]
    rng = random.Random(seed ^ 0x160606566)
    return {
        "numeric_label_order": [
            _decomposition_from_order(inst, order) for order in label_orders
        ],
        "outlier_degree_order": [
            _decomposition_from_order(inst, order) for order in degree_orders
        ],
        "greedy_fewest_unvisited": [_greedy_fewest_unvisited(inst)],
        "width_aware_random_restart_256": [
            random_candidate(inst, rng) for _ in range(256)
        ],
    }


def _relabel_variants(inst, seed):
    rng = random.Random(seed)
    old_vertices = list(inst["vertices"])
    permuted = list(old_vertices)
    rng.shuffle(permuted)
    mapping = dict(zip(old_vertices, permuted))
    inverse = {new: old for old, new in mapping.items()}
    old_rows = dict(zip(old_vertices, inst["answer"]))

    edge_only = copy.deepcopy(inst)
    rng.shuffle(edge_only["edges"])

    relabelled = copy.deepcopy(inst)
    relabelled["vertices"] = sorted(permuted)
    relabelled["edges"] = [
        [mapping[left], mapping[right]] for left, right in inst["edges"]
    ]
    relabelled["answer"] = [
        list(old_rows[inverse[new]]) for new in relabelled["vertices"]
    ]

    composed = copy.deepcopy(relabelled)
    rng.shuffle(composed["edges"])
    for edge in composed["edges"]:
        if rng.randrange(2):
            edge.reverse()
    return [edge_only, relabelled, composed]


def _atomic_elements(value):
    if isinstance(value, dict):
        return sum(_atomic_elements(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atomic_elements(item) for item in value)
    return 1


def selftest():
    report = {}
    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
    }

    inst = make_instance(seed=19, **shipping_params)
    answer = inst["answer"]
    corruptions = {
        "drop": copy.deepcopy(answer[:-1]),
        "swap": copy.deepcopy(answer),
        "duplicate": copy.deepcopy(answer),
        "empty": [],
        "out_of_range": copy.deepcopy(answer),
    }
    corruptions["swap"][0].reverse()
    corruptions["duplicate"][1] = list(corruptions["duplicate"][0])
    corruptions["out_of_range"][0][0] = -1
    rejected = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in rejected.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "I used the introduce/forget event convention from the question.\n"
        "```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nThe maximum active bag has the requested size."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x160606566)
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - guess_start
    guess_fraction = guess_hits / _G4_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": _G4_SAMPLES,
        "fraction": guess_fraction,
        "structure_aware_language": (
            "uniform labelled event sequences with introduction-before-forget "
            "and maximum active set k+1"
        ),
        "candidate_space_bits": search_space(inst).bit_length(),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = (
        "numeric_label_order",
        "outlier_degree_order",
        "greedy_fewest_unvisited",
        "width_aware_random_restart_256",
    )
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    reference_successes = 0
    reference_seconds = 0.0
    reference_transitions = 0
    reference_states = 0
    compact_successes = 0
    for seed in _ATTACK_SEEDS:
        trial = make_instance(seed=seed, **shipping_params)
        candidates = _attack_candidates(trial, seed)
        for name in attack_names:
            start = time.perf_counter()
            won = any(
                candidate is not None and verify(trial, candidate)[0]
                for candidate in candidates[name]
            )
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(won)
        start = time.perf_counter()
        recovered, counts = _reference_subset_dp(trial)
        reference_seconds += time.perf_counter() - start
        reference_transitions += counts["transitions"]
        reference_states += counts["reachable_states"]
        reference_successes += int(
            recovered is not None and verify(trial, recovered)[0]
        )
        compact = _compact_recover(trial)
        compact_successes += int(compact is not None and verify(trial, compact)[0])

    attacks = {
        name: {
            "successes": successes[name],
            "attempts": len(_ATTACK_SEEDS),
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "exact subset DP over vertex-separation prefixes",
        "complexity": "O(n 2^n) exact bit-set transitions",
        "wall_clock_sec": round(reference_seconds / len(_ATTACK_SEEDS), 6),
        "operations": reference_transitions // len(_ATTACK_SEEDS),
        "reachable_states": reference_states // len(_ATTACK_SEEDS),
        "solves": f"{reference_successes}/{len(_ATTACK_SEEDS)}, as expected",
    }
    all_failed = all(successes[name] == 0 for name in attack_names)
    report["G6_adversary_panel"] = {
        "pass": all_failed
        and reference_successes == len(_ATTACK_SEEDS)
        and compact_successes == len(_ATTACK_SEEDS),
        "attacks": attacks,
        "reference_algorithm": reference,
        "intended_compact_route": {
            "name": "modular edge-difference invariant and FIFO bags",
            "solves": f"{compact_successes}/{len(_ATTACK_SEEDS)}",
            "operations_upper_bound": sum(
                inst["n"] - distance
                for distance in range(1, inst["width"] + 1)
            )
            + 4 * inst["n"],
        },
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and demo_count is not None
        and demo_count > 0
        and all_failed
        and reference_successes == len(_ATTACK_SEEDS),
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": _G4_SAMPLES,
        "shipping_solution_density": guess_fraction,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "baseline_attack_wall_clock_sec": round(
            attack_seconds["width_aware_random_restart_256"]
            / len(_ATTACK_SEEDS),
            6,
        ),
        "baseline_attack_iterations": 256,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    ladder_n = [params["n"] for params in DIFFICULTY.values()]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and search_space(doubled) > search_space(inst)
        and ladder_n == sorted(ladder_n)
        and len(set(ladder_n)) == len(ladder_n),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_reason,
        "candidate_space_bits_shipping": search_space(inst).bit_length(),
        "candidate_space_bits_doubled": search_space(doubled).bit_length(),
    }

    invariant = 0
    real = 0
    unrelated = []
    for seed in range(201, 221):
        original = make_instance(seed=seed, **shipping_params)
        key = canonical_key(original)
        for transformed in _relabel_variants(original, seed ^ 0xA55A):
            invariant += int(canonical_key(transformed) == key)
            real += int(verify(transformed, transformed["answer"])[0])
        unrelated.append(key)
    distinct = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": invariant == 60 and real == 60 and distinct == 20,
        "invariant_relabellings": invariant,
        "invariance_attempts": 60,
        "real_transformations_verified": real,
        "real_transformation_attempts": 60,
        "unrelated_distinct_keys": distinct,
        "unrelated_attempts": 20,
        "transformations": [
            "input-edge reordering",
            "arbitrary vertex renaming with carried certificate",
            "composition of vertex renaming, edge reordering, and endpoint reversal",
        ],
        "caveat": (
            "1-WL is complete on these 20 tested asymmetric instances; tied "
            "color classes fall back to a safe but potentially colliding quotient invariant"
        ),
    }

    encoded = json.dumps(answer, separators=(",", ":"))
    answer_chars = len(encoded)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _atomic_elements(answer)
    digits = len(str(2 * inst["n"] - 1))
    worst_chars = inst["n"] * (2 * digits + 4) + 1
    worst_tokens = math.ceil(worst_chars / 4)
    max_edges = sum(
        inst["n"] - distance for distance in range(1, inst["width"] + 1)
    )
    intended_operations = max_edges + 4 * inst["n"]
    arms = {
        arm: dict(G9_ORACLE_RESULTS[arm])
        for arm in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == worst_tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": worst_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
