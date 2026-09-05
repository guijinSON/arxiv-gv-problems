"""Verified W_4-model generator based on arXiv:1710.06282.

The paper works with minor models: disjoint connected branch sets whose required
pairs touch.  This Track-B family asks for the especially concise case in which
all five branch sets are singletons, so the certificate is a displayed W_4
subgraph and hence, immediately, a W_4 minor model.

Generation is inverse.  It first builds a regular graph carrying an order-four
automorphism, makes the unique fixed vertex the hub of a planted wheel, and
uses one four-cycle orbit as its rim.  A nonlinear permutation then relabels
all vertices.  The generator never searches the completed graph for a wheel.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # This family needs only exact integer graph operations.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "finite simple regular graph",
        "five singleton branch sets of a W_4 minor model",
        "order-four graph automorphism in finite-field coordinates",
    ],
    "verification_operations": [
        "exact branch-set disjointness checks",
        "exact graph adjacency checks",
        "canonical cyclic-order comparisons",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "The supplied order-four symmetry has one fixed vertex, and one orbit "
        "in that vertex's neighborhood is the rim; without recognizing this, "
        "one scans candidate hubs and four-cycles in their neighborhoods."
    ),
    "hardness_basis": (
        "Track B: fixed-pattern W_4 subgraph search is polynomial, and the "
        "implemented neighborhood-cycle scan costs O(n*d^4) on d-regular "
        "instances; on the n=401 shipping instance at selftest seed 17 it used "
        "40,527 exact adjacency probes in 0.024 seconds (the eight-seed panel "
        "used 2,398,351 probes), while the symmetry route used 204 exact "
        "modular-arithmetic and adjacency operations."
    ),
    "max_answer_tokens": 8,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}


DIFFICULTY = {
    "demo": {"n": 41, "degree": 8},
    "easy": {"n": 193, "degree": 12},
    "medium": {"n": 277, "degree": 12},
    "hard": {"n": 401, "degree": 12},
}

SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON array [B_h,B_0,B_1,B_2,B_3] of five singleton integer lists. "
        "The five labels are distinct; B_h is the hub; B_0 starts the rim at "
        "its least label; and the orientation is fixed by B_1 < B_3."
    ),
    "bounds": {
        "branch_sets": 5,
        "vertices_per_branch_set": 1,
        "label_range": "0 <= label < n",
        "rim_start": "minimum rim label",
        "rim_orientation": "second rim label < last rim label",
    },
}

STRUCTURAL_HINT = (
    "The supplied quarter-turn symmetry has one fixed junction, and one of its "
    "four-cycles in that junction's neighborhood is the rim."
)
PLACEBO_HINT = (
    "The displayed adjacency rows and canonical rim convention reward careful "
    "tracking of the five requested junction labels."
)

# Populated from the script-owned runs after hardening.  These are diagnostics;
# only the answer/operation caps gate G9.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 14, "attempts": 15},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run_after_bare_rejection",
}

NOTES = """\
Section 1 fixes the exact object: an H-model is a collection of pairwise
vertex-disjoint connected branch sets, with touching branch sets for every edge
of H.  It also defines W_t as a t-cycle plus a hub adjacent to every rim
vertex.  Theorem 1.5 covers every fixed t >= 3; this module uses t=4 and asks
for singleton branch sets, a native special case whose verification is simply
the ten required disjointness/adjacency facts.

Theorem 1.5 is an extremal packing-transversal theorem, not a distributional
hardness theorem.  Section 2 also explicitly relies on algorithmic graph-minor
machinery, including Theorem 2.2's polynomial kernel for fixed-planar-minor
deletion.  Therefore a Track-A claim would be unsupported.  Track B is honest:
the reference algorithm scans every possible hub and the three canonical
cyclic orders of every four-neighbor set.  Its operation count and time are
measured at the shipping preset.

Construction uses the transformation route.  In raw F_p coordinates the map
Q(x)=a*x+c has order four and exactly one fixed point h.  The graph is built as
Q-edge orbits, is regular, and h is joined to several indistinguishable
four-orbits.  Exactly the median-labelled one is closed into a four-cycle and
is remembered as the planted rim.  A nonlinear permutation E(x)=alpha*x^e+beta
then relabels the graph.  Thus the certificate is carried through an
isomorphism; no completed instance is solved.

Every vertex has the same degree, the hub is not selected by identifier, and
the rim is neither the first nor last neighboring Q-orbit.  The panel tests
degree/identifier outliers, maximum local edge density followed by a greedy
walk, random legal certificates, and the tempting fixed-point/first-orbit
ansatz.  The exact neighborhood scan is deliberately successful and is
reported separately as Track B's reference algorithm.
"""


_TAG_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_PAIRING_ATTEMPTS = 50_000


def _is_prime(value: int) -> bool:
    if isinstance(value, bool) or not isinstance(value, int) or value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime_one_mod_four(value: int) -> int:
    candidate = max(5, value)
    candidate += (1 - candidate) % 4
    while not _is_prime(candidate):
        candidate += 4
    return candidate


def _validate_params(n: int, degree: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 41:
        raise ValueError("n must be a prime integer at least 41")
    if not _is_prime(n) or n % 4 != 1:
        raise ValueError("n must be prime and congruent to 1 modulo 4")
    if isinstance(degree, bool) or not isinstance(degree, int):
        raise ValueError("degree must be an integer divisible by 4")
    if degree < 8 or degree % 4:
        raise ValueError("degree must be at least 8 and divisible by 4")
    if degree >= n - 1:
        raise ValueError("degree must be smaller than n-1")
    if (n - 1) // 4 < degree // 4 + 3:
        raise ValueError("n has too few quarter-turn orbits for this degree")


def _sqrt_minus_one(p: int) -> int:
    for value in range(2, p):
        if value * value % p == p - 1:
            return value
    raise ValueError("p has no square root of -1")


def _choose_codec(p: int, rng: random.Random) -> dict:
    exponents = [e for e in range(3, min(p - 1, 32), 2)
                 if math.gcd(e, p - 1) == 1]
    e = rng.choice(exponents)
    return {
        "exponent": e,
        "inverse_exponent": pow(e, -1, p - 1),
        "multiplier": rng.randrange(1, p),
        "offset": rng.randrange(p),
    }


def _encode(codec: dict, raw: int, p: int) -> int:
    return (codec["multiplier"] * pow(raw, codec["exponent"], p)
            + codec["offset"]) % p


def _decode(codec: dict, label: int, p: int) -> int:
    inv_multiplier = pow(codec["multiplier"], -1, p)
    powered = (label - codec["offset"]) * inv_multiplier % p
    return pow(powered, codec["inverse_exponent"], p)


def _q(raw: int, p: int, multiplier: int, offset: int) -> int:
    return (multiplier * raw + offset) % p


def _raw_orbits(p: int, q_multiplier: int, q_offset: int, hub: int) -> list[list[int]]:
    unseen = set(range(p))
    unseen.remove(hub)
    result = []
    while unseen:
        start = min(unseen)
        orbit = [start]
        for _ in range(3):
            orbit.append(_q(orbit[-1], p, q_multiplier, q_offset))
        if len(set(orbit)) != 4 or _q(orbit[-1], p, q_multiplier, q_offset) != start:
            raise AssertionError("quarter-turn did not create a four-orbit")
        unseen.difference_update(orbit)
        result.append(orbit)
    return result


def _add_edge(edges: set[tuple[int, int]], left: int, right: int) -> None:
    if left == right:
        raise AssertionError("loop in raw graph")
    edge = (min(left, right), max(left, right))
    if edge in edges:
        raise AssertionError("parallel raw edge")
    edges.add(edge)


def _pair_orbit_demands(demands: list[int], forbidden_pairs: set[tuple[int, int]],
                        rng: random.Random) -> list[tuple[int, int]]:
    stubs = [index for index, amount in enumerate(demands) for _ in range(amount)]
    if len(stubs) % 2:
        raise AssertionError("odd orbit-stub total")
    for _ in range(_PAIRING_ATTEMPTS):
        trial = list(stubs)
        rng.shuffle(trial)
        multiplicity: dict[tuple[int, int], int] = {}
        pairs = []
        valid = True
        for position in range(0, len(trial), 2):
            left, right = trial[position], trial[position + 1]
            pair = (min(left, right), max(left, right))
            if left == right or pair in forbidden_pairs:
                valid = False
                break
            count = multiplicity.get(pair, 0) + 1
            if count > 4:
                valid = False
                break
            multiplicity[pair] = count
            pairs.append(pair)
        if valid:
            return pairs
    raise RuntimeError("could not pair quotient-orbit stubs")


def _canonical_cycle(labels: list[int]) -> list[int]:
    if len(labels) != 4 or len(set(labels)) != 4:
        raise ValueError("a rim cycle needs four distinct labels")
    least_index = labels.index(min(labels))
    forward = labels[least_index:] + labels[:least_index]
    reverse = [forward[0], forward[3], forward[2], forward[1]]
    return forward if forward[1] < forward[3] else reverse


def _adjacency_from_edges(n: int, edges: set[tuple[int, int]]) -> list[list[int]]:
    adjacency = [[] for _ in range(n)]
    for left, right in edges:
        adjacency[left].append(right)
        adjacency[right].append(left)
    for row in adjacency:
        row.sort()
    return adjacency


def make_instance(n: int, seed: int = 0, degree: int = 12,
                  _concealment_round: int = 0, **params) -> dict:
    """Inverse-generate a regular graph and a carried singleton W_4 model."""
    _validate_params(n, degree)
    attempt_seed = seed if _concealment_round == 0 else (
        int(seed) * 1_000_003 + _concealment_round * 97_409 + 17_100_628
    )
    rng = random.Random(attempt_seed)
    p = n
    q_multiplier = _sqrt_minus_one(p)
    hub = rng.randrange(p)
    q_offset = (1 - q_multiplier) * hub % p
    codec = _choose_codec(p, rng)
    orbits = _raw_orbits(p, q_multiplier, q_offset, hub)

    selected_indices = rng.sample(range(len(orbits)), degree // 4)
    selected_indices.sort(key=lambda index: min(
        _encode(codec, raw, p) for raw in orbits[index]
    ))
    rim_index = selected_indices[len(selected_indices) // 2]
    rim_orbit = orbits[rim_index]

    raw_edges: set[tuple[int, int]] = set()
    for index in selected_indices:
        for raw in orbits[index]:
            _add_edge(raw_edges, hub, raw)
    for phase in range(4):
        _add_edge(raw_edges, rim_orbit[phase], rim_orbit[(phase + 1) % 4])

    demands = [degree for _ in orbits]
    for index in selected_indices:
        demands[index] -= 1
    demands[rim_index] -= 2

    # Cross-orbit matchings consume two quotient stubs.  When the remaining
    # total is odd, one antipodal matching in an ordinary orbit flips parity
    # while preserving both regularity and Q-invariance.
    if sum(demands) % 2:
        ordinary = [i for i in range(len(orbits)) if i not in selected_indices]
        internal_index = rng.choice(ordinary)
        orbit = orbits[internal_index]
        _add_edge(raw_edges, orbit[0], orbit[2])
        _add_edge(raw_edges, orbit[1], orbit[3])
        demands[internal_index] -= 1

    selected_set = set(selected_indices)
    forbidden_pairs = {
        (left, right)
        for left, right in itertools.combinations(sorted(selected_set), 2)
    }
    quotient_pairs = _pair_orbit_demands(demands, forbidden_pairs, rng)
    used_shifts: dict[tuple[int, int], set[int]] = {}
    for left, right in quotient_pairs:
        used = used_shifts.setdefault((left, right), set())
        choices = [shift for shift in range(4) if shift not in used]
        shift = rng.choice(choices)
        used.add(shift)
        for phase in range(4):
            _add_edge(raw_edges, orbits[left][phase],
                      orbits[right][(phase + shift) % 4])

    raw_adjacency = _adjacency_from_edges(p, raw_edges)
    if any(len(row) != degree for row in raw_adjacency):
        raise AssertionError("regularity construction failed")

    raw_to_label = [_encode(codec, raw, p) for raw in range(p)]
    if len(set(raw_to_label)) != p:
        raise AssertionError("codec is not a permutation")
    label_to_raw = [0] * p
    for raw, label in enumerate(raw_to_label):
        label_to_raw[label] = raw

    visible_edges = {
        (min(raw_to_label[left], raw_to_label[right]),
         max(raw_to_label[left], raw_to_label[right]))
        for left, right in raw_edges
    }
    adjacency = _adjacency_from_edges(p, visible_edges)
    rim_labels_q_order = [raw_to_label[raw] for raw in rim_orbit]
    rim_labels = _canonical_cycle(rim_labels_q_order)
    answer = [[raw_to_label[hub]]] + [[label] for label in rim_labels]

    instance = {
        "family": "singleton W_4 minor model in a regular symmetric graph",
        "n": p,
        "degree": degree,
        "t": 4,
        "adjacency": adjacency,
        "rotation": {"multiplier": q_multiplier, "offset": q_offset},
        "codec": codec,
        "label_to_raw": label_to_raw,
        "raw_to_label": raw_to_label,
        "_edge_set": visible_edges,
        "answer": answer,
    }
    planted_hub = answer[0][0]
    edge_set = visible_edges
    planted_local_edges = sum(
        1 for left, right in itertools.combinations(adjacency[planted_hub], 2)
        if _has_edge(edge_set, left, right)
    )
    best_decoy_local_edges = max(
        sum(1 for left, right in itertools.combinations(adjacency[vertex], 2)
            if _has_edge(edge_set, left, right))
        for vertex in range(p) if vertex != planted_hub
    )
    if planted_local_edges >= best_decoy_local_edges:
        if _concealment_round >= 100:
            raise RuntimeError("could not conceal the planted hub's local density")
        return make_instance(n=n, seed=seed, degree=degree,
                             _concealment_round=_concealment_round + 1)
    return instance


def render(inst: dict) -> str:
    p = inst["n"]
    codec = inst["codec"]
    rotation = inst["rotation"]
    rows = "\n".join(
        f"{vertex}: " + " ".join(map(str, neighbors))
        for vertex, neighbors in enumerate(inst["adjacency"])
    )
    if codec.get("kind") == "table":
        coordinate_text = (
            "For this relabelled form, raw(label) is the following table in "
            "increasing label order:\n" + " ".join(map(str, inst["label_to_raw"]))
        )
    else:
        inverse_multiplier = pow(codec["multiplier"], -1, p)
        coordinate_text = (
            f"A reversible coordinate audit accompanies the graph.  Raw x is labelled "
            f"E(x)=({codec['multiplier']}*x^{codec['exponent']}+"
            f"{codec['offset']}) mod {p}.  Conversely, label y has raw coordinate "
            f"(({inverse_multiplier}*(y-{codec['offset']})) mod {p})^"
            f"{codec['inverse_exponent']} mod {p}."
        )
    text = f"""Find a singleton-branch-set W_4 minor model in the graph below.

The graph is finite, simple, and undirected.  Its vertices are the integers 0
through {p - 1}.  The adjacency table gives every neighbor of every vertex;
thus each undirected edge appears in both endpoint rows.  Every row has exactly
{inst['degree']} distinct entries.

A W_4 is a wheel with five vertices: one hub h and four distinct rim vertices
r0,r1,r2,r3.  The hub is adjacent to all four rim vertices, and the rim has the
cycle edges r0-r1, r1-r2, r2-r3, r3-r0.  Extra edges are allowed.  A minor model
uses five pairwise-disjoint, nonempty, connected branch sets, with an edge
between the corresponding branch sets for every W_4 edge.  Here every branch
set must be a singleton, so direct adjacency certifies the model.

To remove rotations and reversal ambiguity, r0 must be the numerically least
rim label and r1 must be less than r3.  Labels are ordinary integers, all bounds
are inclusive, and no label may repeat.

{coordinate_text}
The supplied raw-coordinate quarter-turn is
Q(x)=({rotation['multiplier']}*x+{rotation['offset']}) mod {p}.

Adjacency table:
{rows}

Give your final answer inside <answer></answer> tags as one JSON array
[[h],[r0],[r1],[r2],[r3]].  Each inner array is one singleton branch set.
Example: <answer>[[8],[2],[5],[11],[7]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    match = _TAG_RE.search(text)
    if not match:
        return None
    payload = match.group(1).strip()
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return answer


def _edges(inst: dict) -> set[tuple[int, int]]:
    cached = inst.get("_edge_set")
    if isinstance(cached, set):
        return cached
    result = set()
    for left, neighbors in enumerate(inst["adjacency"]):
        for right in neighbors:
            if left < right:
                result.add((left, right))
    return result


def _has_edge(edge_set: set[tuple[int, int]], left: int, right: int) -> bool:
    return (min(left, right), max(left, right)) in edge_set


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list) or len(answer) != 5:
        return False, "answer must contain exactly five branch sets"
    for index, branch in enumerate(answer):
        if not isinstance(branch, list) or len(branch) != 1:
            return False, f"branch set {index} must be a singleton list"
        label = branch[0]
        if isinstance(label, bool) or not isinstance(label, int):
            return False, f"branch set {index} has a non-integer label"
        if not 0 <= label < inst["n"]:
            return False, f"branch set {index} has a label outside 0..{inst['n'] - 1}"
    labels = [branch[0] for branch in answer]
    if len(set(labels)) != 5:
        return False, "branch sets are not pairwise disjoint"
    hub, rim = labels[0], labels[1:]
    if rim[0] != min(rim):
        return False, "r0 is not the least rim label"
    if rim[1] >= rim[3]:
        return False, "rim orientation is not canonical (r1 must be less than r3)"
    edge_set = _edges(inst)
    for vertex in rim:
        if not _has_edge(edge_set, hub, vertex):
            return False, f"hub {hub} is not adjacent to rim vertex {vertex}"
    for index in range(4):
        left, right = rim[index], rim[(index + 1) % 4]
        if not _has_edge(edge_set, left, right):
            return False, f"rim edge {left}-{right} is absent"
    return True, "ok"


def _orders_for_four(vertices: list[int] | tuple[int, ...]) -> list[list[int]]:
    least = min(vertices)
    others = sorted(v for v in vertices if v != least)
    orders = []
    for permutation in itertools.permutations(others):
        order = [least] + list(permutation)
        if order[1] < order[3]:
            orders.append(order)
    return orders


def random_candidate(inst: dict, rng: random.Random) -> object:
    n = inst["n"]
    hub = rng.randrange(n)
    sampled = rng.sample(range(n - 1), 4)
    rim_set = [value if value < hub else value + 1 for value in sampled]
    order = rng.choice(_orders_for_four(rim_set))
    return [[hub]] + [[vertex] for vertex in order]


def search_space(inst: dict) -> int | None:
    n = inst["n"]
    return n * math.comb(n - 1, 4) * 3


def _count_answers(inst: dict, cap_candidates: int | None = None) -> int | None:
    edge_set = _edges(inst)
    candidates = 0
    answers = 0
    for hub, neighbors in enumerate(inst["adjacency"]):
        for rim_set in itertools.combinations(neighbors, 4):
            for rim in _orders_for_four(rim_set):
                candidates += 1
                if cap_candidates is not None and candidates > cap_candidates:
                    return None
                if all(_has_edge(edge_set, rim[index], rim[(index + 1) % 4])
                       for index in range(4)):
                    answers += 1
    return answers


def enumerate_all(inst: dict) -> int | None:
    # Every valid certificate first chooses four of the hub's displayed
    # neighbors, so this is exact enumeration of the bounded language with
    # the obviously necessary hub-adjacency constraint already propagated.
    return _count_answers(inst, cap_candidates=2_000_000)


def _normalized_raw_edges(inst: dict) -> list[list[int]]:
    p = inst["n"]
    rotation = inst["rotation"]
    a, c = rotation["multiplier"], rotation["offset"]
    hub = (-c * pow(a - 1, -1, p)) % p
    label_to_raw = inst["label_to_raw"]
    normalized = []
    for left, right in _edges(inst):
        raw_left = (label_to_raw[left] - hub) % p
        raw_right = (label_to_raw[right] - hub) % p
        normalized.append(sorted((raw_left, raw_right)))
    normalized.sort()
    return normalized


def canonical_key(inst: dict) -> str:
    payload = {
        "n": inst["n"],
        "degree": inst["degree"],
        "rotation_multiplier": inst["rotation"]["multiplier"],
        "normalized_raw_edges": _normalized_raw_edges(inst),
    }
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()


def escalate(params: dict) -> dict | str | None:
    current = int(params["n"])
    return {"n": _next_prime_one_mod_four(2 * current),
            "degree": int(params.get("degree", 12))}


def _reference_algorithm(inst: dict) -> tuple[object | None, dict[str, int]]:
    edge_set = _edges(inst)
    probes = 0
    candidate_cycles = 0
    hubs = 0
    for hub, neighbors in enumerate(inst["adjacency"]):
        hubs += 1
        for rim_set in itertools.combinations(neighbors, 4):
            for rim in _orders_for_four(rim_set):
                candidate_cycles += 1
                good = True
                for index in range(4):
                    probes += 1
                    if not _has_edge(edge_set, rim[index], rim[(index + 1) % 4]):
                        good = False
                        break
                if good:
                    return ([[hub]] + [[vertex] for vertex in rim], {
                        "hubs": hubs,
                        "candidate_cycles": candidate_cycles,
                        "adjacency_probes": probes,
                    })
    return None, {"hubs": hubs, "candidate_cycles": candidate_cycles,
                  "adjacency_probes": probes}


def _greedy_from_hub(inst: dict, hub: int) -> object:
    neighbors = sorted(inst["adjacency"][hub])
    edge_set = _edges(inst)
    if len(neighbors) < 4:
        return []
    start = neighbors[0]
    path = [start]
    unused = set(neighbors[1:])
    while len(path) < 4:
        choices = sorted(v for v in unused if _has_edge(edge_set, path[-1], v))
        if not choices:
            choices = sorted(unused)
        chosen = choices[0]
        path.append(chosen)
        unused.remove(chosen)
    rim = _canonical_cycle(path)
    return [[hub]] + [[vertex] for vertex in rim]


def _attack_degree_identifier(inst: dict) -> object:
    maximum = max(len(row) for row in inst["adjacency"])
    hub = min(v for v, row in enumerate(inst["adjacency"]) if len(row) == maximum)
    return _greedy_from_hub(inst, hub)


def _local_edge_count(inst: dict, hub: int) -> int:
    edge_set = _edges(inst)
    return sum(1 for left, right in itertools.combinations(inst["adjacency"][hub], 2)
               if _has_edge(edge_set, left, right))


def _attack_local_density_greedy(inst: dict) -> object:
    scores = [(_local_edge_count(inst, hub), -hub, hub)
              for hub in range(inst["n"])]
    hub = max(scores)[2]
    return _greedy_from_hub(inst, hub)


def _raw_fixed_point(inst: dict) -> int:
    p = inst["n"]
    a = inst["rotation"]["multiplier"]
    c = inst["rotation"]["offset"]
    return (-c * pow(a - 1, -1, p)) % p


def _visible_q(inst: dict, label: int) -> int:
    p = inst["n"]
    raw = inst["label_to_raw"][label]
    moved = _q(raw, p, inst["rotation"]["multiplier"],
               inst["rotation"]["offset"])
    return inst["raw_to_label"][moved]


def _neighbor_q_orbits(inst: dict, hub_label: int) -> list[list[int]]:
    unseen = set(inst["adjacency"][hub_label])
    orbits = []
    while unseen:
        start = min(unseen)
        orbit = [start]
        for _ in range(3):
            orbit.append(_visible_q(inst, orbit[-1]))
        unseen.difference_update(orbit)
        orbits.append(orbit)
    return orbits


def _attack_fixed_point_first_orbit(inst: dict) -> object:
    hub = inst["raw_to_label"][_raw_fixed_point(inst)]
    orbits = _neighbor_q_orbits(inst, hub)
    orbit = min(orbits, key=lambda values: min(values))
    rim = _canonical_cycle(orbit)
    return [[hub]] + [[vertex] for vertex in rim]


def _attack_random_restart(inst: dict, seed: int, restarts: int = 256) -> object | None:
    rng = random.Random(seed)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _pow_operation_count(exponent: int) -> int:
    # Left-to-right binary exponentiation: one square after the leading bit,
    # plus one multiply for every remaining 1 bit.
    bits = bin(exponent)[2:]
    return max(0, len(bits) - 1) + bits[1:].count("1")


def _compact_route(inst: dict) -> tuple[object | None, int]:
    """Execute and count the intended fixed-point/orbit route."""
    p = inst["n"]
    codec = inst["codec"]
    operations = 0
    # Extended-Euclid/modular-inverse work is conservatively charged by twice
    # the modulus bit length, plus the multiply/add/reduction around it.
    operations += 2 * p.bit_length() + 4
    raw_hub = _raw_fixed_point(inst)
    operations += _pow_operation_count(codec["exponent"]) + 3
    hub = _encode(codec, raw_hub, p)
    neighbor_set = set(inst["adjacency"][hub])
    operations += len(neighbor_set)

    unseen = set(neighbor_set)
    edge_set = _edges(inst)
    while unseen:
        label = min(unseen)
        operations += len(unseen)
        operations += _pow_operation_count(codec["inverse_exponent"]) + 5
        raw = _decode(codec, label, p)
        raw_orbit = [raw]
        for _ in range(3):
            raw_orbit.append(_q(raw_orbit[-1], p,
                                inst["rotation"]["multiplier"],
                                inst["rotation"]["offset"]))
            operations += 3
        orbit = []
        for value in raw_orbit:
            orbit.append(_encode(codec, value, p))
            operations += _pow_operation_count(codec["exponent"]) + 3
        unseen.difference_update(orbit)
        operations += 4
        rim = _canonical_cycle(orbit)
        good = True
        for index in range(4):
            operations += 1
            if not _has_edge(edge_set, rim[index], rim[(index + 1) % 4]):
                good = False
                break
        if good:
            return [[hub]] + [[vertex] for vertex in rim], operations
    return None, operations


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(item) for item in value)
    return 1


def _relabel_instance(inst: dict, rng: random.Random) -> tuple[dict, dict[int, int]]:
    n = inst["n"]
    old_to_new_list = list(range(n))
    rng.shuffle(old_to_new_list)
    old_to_new = dict(enumerate(old_to_new_list))
    adjacency = [[] for _ in range(n)]
    for old, neighbors in enumerate(inst["adjacency"]):
        adjacency[old_to_new[old]] = sorted(old_to_new[v] for v in neighbors)
    edge_set = {
        (min(old_to_new[left], old_to_new[right]),
         max(old_to_new[left], old_to_new[right]))
        for left, right in _edges(inst)
    }
    label_to_raw = [0] * n
    for old_label, raw in enumerate(inst["label_to_raw"]):
        label_to_raw[old_to_new[old_label]] = raw
    raw_to_label = [0] * n
    for label, raw in enumerate(label_to_raw):
        raw_to_label[raw] = label
    answer = [[old_to_new[branch[0]]] for branch in inst["answer"]]
    answer = [answer[0]] + [[v] for v in _canonical_cycle(
        [branch[0] for branch in answer[1:]]
    )]
    transformed = dict(inst)
    transformed.update({
        "adjacency": adjacency,
        "_edge_set": edge_set,
        "label_to_raw": label_to_raw,
        "raw_to_label": raw_to_label,
        "codec": {"kind": "table"},
        "answer": answer,
    })
    return transformed, old_to_new


def _find_rim_corruption(inst: dict, answer: list[list[int]]) -> object:
    hub = answer[0][0]
    rim = [branch[0] for branch in answer[1:]]
    for permutation in itertools.permutations(rim):
        candidate_rim = list(permutation)
        if candidate_rim[0] != min(candidate_rim) or candidate_rim[1] >= candidate_rim[3]:
            continue
        candidate = [[hub]] + [[v] for v in candidate_rim]
        ok, reason = verify(inst, candidate)
        if not ok and reason.startswith("rim edge"):
            return candidate
    raise AssertionError("could not construct a rim-order corruption")


def selftest() -> dict:
    """Run all mandatory gates and return their measured results."""
    report = {
        "paper": "arXiv:1710.06282",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    g1_failures = []
    construction_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            instance = make_instance(seed=seed, **params)
            ok, reason = verify(instance, instance["answer"])
            if not ok:
                g1_failures.append(f"{preset}/seed={seed}: {reason}")
            if json.loads(json.dumps(instance["answer"])) != instance["answer"]:
                g1_failures.append(f"{preset}/seed={seed}: answer is not JSON-native")
            for vertex, row in enumerate(instance["adjacency"]):
                construction_checks += 1
                if len(row) != params["degree"] or len(set(row)) != len(row):
                    g1_failures.append(
                        f"{preset}/seed={seed}: degree/simple check failed at {vertex}"
                    )
            for raw in range(instance["n"]):
                moved = _q(raw, instance["n"],
                           instance["rotation"]["multiplier"],
                           instance["rotation"]["offset"])
                construction_checks += 1
                for neighbor_label in instance["adjacency"][instance["raw_to_label"][raw]]:
                    neighbor_raw = instance["label_to_raw"][neighbor_label]
                    moved_edge = (
                        instance["raw_to_label"][moved],
                        instance["raw_to_label"][_q(
                            neighbor_raw, instance["n"],
                            instance["rotation"]["multiplier"],
                            instance["rotation"]["offset"],
                        )],
                    )
                    if not _has_edge(_edges(instance), *moved_edge):
                        g1_failures.append(
                            f"{preset}/seed={seed}: Q is not an automorphism"
                        )
                        break
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": len(DIFFICULTY) * 4,
        "construction_identity_checks": construction_checks,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=17, **shipping)
    answer = json.loads(json.dumps(inst["answer"]))
    drop_one = answer[:-1]
    swap_two = _find_rim_corruption(inst, answer)
    duplicate = json.loads(json.dumps(answer))
    duplicate[2][0] = duplicate[1][0]
    out_of_range = json.loads(json.dumps(answer))
    out_of_range[0][0] = inst["n"]
    nonsingleton = json.loads(json.dumps(answer))
    nonsingleton[0].append(nonsingleton[1][0])
    corruptions = {
        "drop_one": drop_one,
        "swap_two": swap_two,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
        "nonsingleton": nonsingleton,
    }
    corruption_report = {}
    rejection_reasons = set()
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        corruption_report[name] = {"rejected": not ok, "reason": reason}
        if not ok:
            rejection_reasons.add(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruption_report.values())
        and len(rejection_reasons) == len(corruptions),
        "distinct_reasons": len(rejection_reasons),
        "corruptions": corruption_report,
    }

    realistic = (
        "The fixed-point orbit gives the following model.\n```json\n"
        f"<answer>{json.dumps(answer)}</answer>\n```\n"
        "Each inner array is a singleton branch set."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {"pass": parsed == answer, "parsed": parsed}

    guess_rng = random.Random(171006282)
    guess_total = 200_000
    guess_hits = 0
    guess_started = time.perf_counter()
    for _ in range(guess_total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            guess_hits += 1
    guess_elapsed = time.perf_counter() - guess_started
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "empirical_probability": guess_hits / guess_total,
        "structure_aware_prior": (
            "uniform hub, uniform four distinct non-hub labels, and uniform "
            "canonical cyclic order; all shape/disjointness conventions enforced"
        ),
        "search_space": search_space(inst),
        "elapsed_sec": round(guess_elapsed, 6),
    }

    count_started = time.perf_counter()
    exact_count = enumerate_all(inst)
    count_elapsed = time.perf_counter() - count_started
    reference_started = time.perf_counter()
    reference_answer, reference_ops = _reference_algorithm(inst)
    reference_elapsed = time.perf_counter() - reference_started
    reference_ok = bool(reference_answer is not None and verify(inst, reference_answer)[0])
    report["G5_density_and_baseline"] = {
        "pass": exact_count is not None and reference_ok,
        "shipping_n": inst["n"],
        "exact_valid_answers": exact_count,
        "certificate_language_size": search_space(inst),
        "exact_density": exact_count / search_space(inst) if exact_count is not None else None,
        "count_elapsed_sec": round(count_elapsed, 6),
        "strongest_attack": "neighborhood four-cycle scan",
        "baseline_wall_clock_sec": round(reference_elapsed, 6),
        "baseline_operations": reference_ops,
    }

    attack_functions = {
        "degree_then_smallest_neighbor_greedy": lambda x, s: _attack_degree_identifier(x),
        "max_local_density_greedy_walk": lambda x, s: _attack_local_density_greedy(x),
        "random_restart_256": lambda x, s: _attack_random_restart(x, 100_000 + s),
        "fixed_point_first_neighbor_orbit": lambda x, s: _attack_fixed_point_first_orbit(x),
    }
    attacks = {name: {"successes": 0, "attempts": 8}
               for name in attack_functions}
    reference_successes = 0
    reference_total_operations = 0
    reference_total_time = 0.0
    planted_hub_local_ranks = []
    for seed in range(8):
        trial = make_instance(seed=1000 + seed, **shipping)
        local_scores = [_local_edge_count(trial, vertex)
                        for vertex in range(trial["n"])]
        planted_hub = trial["answer"][0][0]
        planted_score = local_scores[planted_hub]
        planted_hub_local_ranks.append(
            1 + sum(score > planted_score for score in local_scores)
        )
        for name, attack in attack_functions.items():
            candidate = attack(trial, seed)
            if candidate is not None and verify(trial, candidate)[0]:
                attacks[name]["successes"] += 1
        started = time.perf_counter()
        candidate, operations = _reference_algorithm(trial)
        reference_total_time += time.perf_counter() - started
        reference_total_operations += operations["adjacency_probes"]
        if candidate is not None and verify(trial, candidate)[0]:
            reference_successes += 1
    all_failed = all(result["successes"] == 0 for result in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attacks,
        "planted_hub_rank_by_neighbor_edge_count": planted_hub_local_ranks,
        "reference_algorithm": {
            "name": "exact hub-neighborhood four-cycle scan",
            "complexity": "O(n*d^4) exact adjacency probes on d-regular input",
            "wall_clock_sec": round(reference_total_time, 6),
            "operations": reference_total_operations,
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    doubled_n = _next_prime_one_mod_four(2 * DIFFICULTY["hard"]["n"])
    doubled_started = time.perf_counter()
    doubled = make_instance(n=doubled_n, degree=DIFFICULTY["hard"]["degree"], seed=91)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    doubled_elapsed = time.perf_counter() - doubled_started
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_n > 2 * DIFFICULTY["hard"]["n"],
        "base_n": DIFFICULTY["hard"]["n"],
        "doubled_n": doubled_n,
        "build_and_verify_sec": round(doubled_elapsed, 6),
        "verify_reason": doubled_reason,
        "answer_atoms_unchanged": _answer_atoms(doubled["answer"]) == 5,
    }

    invariance_checks = 0
    carried_witness_checks = 0
    g8_failures = []
    unrelated_keys = []
    for seed in range(20):
        original = make_instance(seed=20_000 + seed, **DIFFICULTY["easy"])
        key = canonical_key(original)
        unrelated_keys.append(key)
        transformed, _ = _relabel_instance(original, random.Random(30_000 + seed))
        transformed["adjacency"] = [list(reversed(row)) for row in transformed["adjacency"]]
        invariance_checks += 1
        if canonical_key(transformed) != key:
            g8_failures.append(f"seed={seed}: key changed under relabelling/reordering")
        carried_witness_checks += 1
        ok, reason = verify(transformed, transformed["answer"])
        if not ok:
            g8_failures.append(f"seed={seed}: carried witness failed: {reason}")
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and invariance_checks >= 20
        and carried_witness_checks >= 20 and distinct_count == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_witness_checks,
        "unrelated_distinct": distinct_count,
        "unrelated_total": 20,
        "failures": g8_failures,
    }

    compact_answer, compact_operations = _compact_route(inst)
    compact_ok = compact_answer is not None and verify(inst, compact_answer)[0]
    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(inst["answer"])
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and compact_operations <= 300 and compact_ok)
    bare = G9_ORACLE_RESULTS["bare"]
    hinted = G9_ORACLE_RESULTS["hinted"]
    placebo = G9_ORACLE_RESULTS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {"bare": dict(bare), "hinted": dict(hinted), "placebo": dict(placebo)},
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact_operations,
        "intended_route_verifies": compact_ok,
    }

    report["all_pass"] = all(
        isinstance(value, dict) and value.get("pass") is True
        for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
