"""Rejected experimental generator for edge--vertex domination in UDGs.

The family is native to arXiv:2111.13552.  It samples the certificate edges
first and then samples every remaining point from their exact domination
region.  Thus the answer is carried by inverse generation; no domination
solver is run while making an instance.  G and V pass, but the attempted
Track-A family fails G5/G6 because exact set-cover search solves 4/8 shipping
instances.  See REJECTED.md and selftest_report.json.
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
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - helpers are optional here
    exact_matrices = rationals = None


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "geometry",
    "object_regime": "rational_exact",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "integer-coordinate unit-disk representation",
        "induced unit disk graph",
        "edge-vertex dominating edge set",
    ],
    "verification_operations": [
        "exact squared-distance comparison",
        "exact graph-edge lookup",
        "closed-neighborhood union",
        "integer cardinality and distinctness checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Extreme uncovered points restrict a useful edge to an overlap of two "
        "unit-radius lenses; propagating those restrictions exposes a small "
        "cover, whereas unstructured edge search faces thousands of choices."
    ),
    "hardness_basis": (
        "Rejected Track-A claim: Section 3 proves worst-case EVDS-UDG "
        "NP-complete only through the Lemmas 2--4 planar-Vertex-Cover "
        "reduction; this unrelated planted distribution at n=180 and k=10 "
        "is solved on 4/8 fixed seeds by the exact set-cover branch-and-bound "
        "reported in G5/G6."
    ),
    "max_answer_tokens": 25,
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
    "demo": {"n": 9, "k": 1, "pitch": 2000},
    "easy": {"n": 180, "k": 10, "pitch": 2100},
    "medium": {"n": 260, "k": 14, "pitch": 2000},
    "hard": {"n": 360, "k": 16, "pitch": 2000},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Extreme uncovered points constrain the useful edges through overlapping "
    "unit-radius lens neighborhoods."
)
PLACEBO_HINT = (
    "Careful bookkeeping of vertex labels and squared distances is useful in "
    "this instance."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "An unordered JSON list of exactly k distinct undirected graph edges; "
        "each edge is a two-element increasing list [u,v] with 0 <= u < v < n."
    ),
    "bounds": {
        "edge_count": "exactly the displayed k",
        "endpoints": "integer vertex labels 0..n-1",
        "edge_order": "u < v",
        "distinct": True,
        "outer_order": "irrelevant",
    },
}

NOTES = (
    "Section 1 fixes the exact definition used by verify: an edge (a,b) "
    "edge-vertex dominates precisely the vertices in N[a] union N[b].  "
    "Section 3's NP-membership lemma gives O(|V||E|) witness verification and "
    "its final theorem proves the bounded-size decision problem NP-complete "
    "on UDGs.  The easy results that determine the track are Section 4's "
    "final PTAS theorem and Section 5's O(m+n) 5-approximation theorem: "
    "neither returns an exact "
    "threshold witness, so they do not collapse the exact Track A task.  "
    "Lemma 5's local PTAS subproblem explicitly enumerates O(r^2)-tuples in "
    "n^{O(r^2)} time.  Generation is inverse: k adjacent endpoint pairs are "
    "sampled first on a jittered rational grid, then every other point is "
    "sampled inside the union of their closed unit disks.  Every point is "
    "therefore in N[a] union N[b] for a planted pair before the graph is ever "
    "constructed.  Public labels, a global grid isometry, and translation are "
    "randomized.  Degree/coverage outliers, gain greedy, randomized restricted "
    "candidate lists, geometric short-edge selection, rare-vertex LP-style "
    "rounding, and the paper's maximal-matching construction are measured in "
    "G6.  The NP-completeness theorem is worst-case; resistance of this planted "
    "distribution is empirical and is a required caveat, not inferred from the "
    "theorem alone.  The final audit added a capped exact 0-1 set-cover "
    "branch-and-bound; it succeeds on 4/8 shipping seeds, so this attempted "
    "Track-A family is rejected rather than shipped."
)

# Script-owned oracle evidence is copied here after the three runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

_SCALE = 1000
_ENUMERATION_CAP = 200_000


def _validate_parameters(n, k, pitch):
    for name, value in (("n", n), ("k", k), ("pitch", pitch)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if k < 1:
        raise ValueError("k must be positive")
    if n < 2 * k + 1:
        raise ValueError("n must be at least 2*k+1")
    if not 1500 <= pitch <= 2400:
        raise ValueError("pitch must lie in 1500..2400")


def _sqdist(p, q):
    dx = p[0] - q[0]
    dy = p[1] - q[1]
    return dx * dx + dy * dy


def _random_short_vector(rng):
    while True:
        dx = rng.randint(-850, 850)
        dy = rng.randint(-850, 850)
        d2 = dx * dx + dy * dy
        if 250 * 250 <= d2 <= 900 * 900:
            return dx, dy


def _apply_isometry(points, code, tx, ty):
    out = []
    for x, y in points:
        if code == 0:
            a, b = x, y
        elif code == 1:
            a, b = -x, y
        elif code == 2:
            a, b = x, -y
        elif code == 3:
            a, b = -x, -y
        elif code == 4:
            a, b = y, x
        elif code == 5:
            a, b = -y, x
        elif code == 6:
            a, b = y, -x
        else:
            a, b = -y, -x
        out.append([a + tx, b + ty])
    return out


def make_instance(n, seed=0, **params):
    """Inverse-generate a rational UDG and a known exact-size EVDS.

    The selected endpoint pairs exist before any other point.  A rejection
    sampler draws each later point only from the union of the unit disks about
    those endpoints, which is exactly the selected edges' domination region.
    The sampler never searches for an EVDS.
    """
    k = params.pop("k", 16)
    pitch = params.pop("pitch", 2000)
    params.pop("_preset", None)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, k, pitch)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    columns = math.ceil(math.sqrt(k))
    rows = math.ceil(k / columns)
    points = []
    planted = []
    used = set()

    for cell in range(k):
        col, row = cell % columns, cell // columns
        cx = (col + 1) * pitch + rng.randint(-340, 340)
        cy = (row + 1) * pitch + rng.randint(-340, 340)
        dx, dy = _random_short_vector(rng)
        pair = ([cx - dx // 2, cy - dy // 2],
                [cx + (dx - dx // 2), cy + (dy - dy // 2)])
        ids = []
        for point in pair:
            key = tuple(point)
            while key in used:
                point[0] += 1
                key = tuple(point)
            used.add(key)
            ids.append(len(points))
            points.append(point)
        planted.append(tuple(ids))

    min_x = min(p[0] for p in points) - _SCALE
    max_x = max(p[0] for p in points) + _SCALE
    min_y = min(p[1] for p in points) - _SCALE
    max_y = max(p[1] for p in points) + _SCALE
    radius2 = _SCALE * _SCALE
    attempts = 0
    while len(points) < n:
        attempts += 1
        if attempts > 1000 * n:
            raise RuntimeError("point rejection sampler exhausted")
        point = [rng.randint(min_x, max_x), rng.randint(min_y, max_y)]
        if tuple(point) in used:
            continue
        if any(_sqdist(point, points[a]) <= radius2
               or _sqdist(point, points[b]) <= radius2
               for a, b in planted):
            used.add(tuple(point))
            points.append(point)

    # Hide construction order, and independently randomize the coordinate frame.
    old_to_new = list(range(n))
    rng.shuffle(old_to_new)
    relabelled = [None] * n
    for old, new in enumerate(old_to_new):
        relabelled[new] = points[old]
    planted = [tuple(sorted((old_to_new[a], old_to_new[b])))
               for a, b in planted]
    code = rng.randrange(8)
    tx, ty = rng.randint(-50_000, 50_000), rng.randint(-50_000, 50_000)
    points = _apply_isometry(relabelled, code, tx, ty)

    return {
        "paper": "arXiv:2111.13552",
        "family": "exact edge-vertex domination in a rational unit disk graph",
        "n": n,
        "k": k,
        "scale": _SCALE,
        "pitch": pitch,
        "points": points,
        "answer": [list(edge) for edge in sorted(planted)],
    }


def _graph(inst):
    cache = inst.get("_graph_cache")
    if cache is not None:
        return cache
    points = inst["points"]
    n = len(points)
    radius2 = inst["scale"] ** 2
    adjacency = [0] * n
    edges = []
    for v in range(n):
        for u in range(v):
            if _sqdist(points[u], points[v]) <= radius2:
                adjacency[u] |= 1 << v
                adjacency[v] |= 1 << u
                edges.append((u, v))
    covers = []
    for u, v in edges:
        covers.append(adjacency[u] | adjacency[v] | (1 << u) | (1 << v))
    edge_index = {edge: i for i, edge in enumerate(edges)}
    by_vertex = [[] for _ in range(n)]
    for i, cover in enumerate(covers):
        bits = cover
        while bits:
            bit = bits & -bits
            by_vertex[bit.bit_length() - 1].append(i)
            bits -= bit
    cache = {
        "adjacency": adjacency,
        "edges": edges,
        "covers": covers,
        "edge_index": edge_index,
        "by_vertex": by_vertex,
        "all": (1 << n) - 1,
    }
    inst["_graph_cache"] = cache
    return cache


def render(inst):
    lines = [
        "Find an exact-size edge-vertex dominating set in a unit disk graph.",
        "",
        "Definitions.",
        "The vertices are labelled 0 through n-1 and have the integer coordinates",
        "listed below.  Two distinct vertices are adjacent exactly when their",
        "squared Euclidean distance is at most scale^2; equality is included.",
        "Thus an undirected edge is written [u,v] with u < v.",
        "An edge [u,v] edge-vertex dominates every vertex equal or adjacent to",
        "u or v.  A set of edges is an edge-vertex dominating set (EVDS) when",
        "every graph vertex is dominated by at least one selected edge.",
        "",
        f"n = {inst['n']}",
        f"scale = {inst['scale']}",
        f"Required number of distinct edges k = {inst['k']}",
        "Coordinates (label: x y):",
    ]
    lines.extend(f"{i}: {p[0]} {p[1]}" for i, p in enumerate(inst["points"]))
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    example = [[2 * i, 2 * i + 1] for i in range(inst["k"])]
    lines.extend([
        "",
        "Return exactly k distinct graph edges.  The outer list is unordered;",
        "reordering its edges does not change the answer.  Repeated edges and",
        "loops are forbidden.  All bounds above are inclusive where stated.",
        "Give your final answer inside <answer></answer> tags, as one JSON list",
        "of k two-integer lists, with each inner list in increasing endpoint order.",
        "Format-only example (not claimed to use graph edges):",
        "<answer>" + json.dumps(example, separators=(",", ":")) + "</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\b[^>]*>(.*?)</answer>", text,
                      flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    body = match.group(1).strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\s*```$", "", body)
    try:
        answer = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(answer, list):
        return None
    return answer


def verify(inst, answer):
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer list is empty"
    if len(answer) != inst["k"]:
        return False, f"answer must contain exactly {inst['k']} edges"
    normalized = []
    for edge in answer:
        if not isinstance(edge, list) or len(edge) != 2:
            return False, "each edge must be a two-element JSON list"
        u, v = edge
        if (isinstance(u, bool) or isinstance(v, bool)
                or not isinstance(u, int) or not isinstance(v, int)):
            return False, "edge endpoints must be integers"
        if not (0 <= u < inst["n"] and 0 <= v < inst["n"]):
            return False, "vertex label out of range"
        if u == v:
            return False, "loops are not graph edges"
        if u > v:
            return False, "each edge must have increasing endpoints"
        normalized.append((u, v))
    if len(set(normalized)) != len(normalized):
        return False, "selected edges must be distinct"
    graph = _graph(inst)
    chosen = []
    for edge in normalized:
        index = graph["edge_index"].get(edge)
        if index is None:
            return False, f"{list(edge)} is not a graph edge"
        chosen.append(index)
    covered = 0
    for index in chosen:
        covered |= graph["covers"][index]
    if covered != graph["all"]:
        missing = (graph["all"] ^ (graph["all"] & covered)).bit_count()
        return False, f"selected edges leave {missing} vertices undominated"
    return True, "ok"


def random_candidate(inst, rng):
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    edges = _graph(inst)["edges"]
    return [list(edge) for edge in rng.sample(edges, inst["k"])]


def search_space(inst):
    m = len(_graph(inst)["edges"])
    return math.comb(m, inst["k"])


def enumerate_all(inst):
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    count = 0
    edges = _graph(inst)["edges"]
    for selection in itertools.combinations(edges, inst["k"]):
        if verify(inst, [list(edge) for edge in selection])[0]:
            count += 1
    return count


def _normalized_points(points):
    candidates = []
    for code in range(8):
        transformed = _apply_isometry(points, code, 0, 0)
        min_x = min(p[0] for p in transformed)
        min_y = min(p[1] for p in transformed)
        candidates.append(tuple(sorted((p[0] - min_x, p[1] - min_y)
                                       for p in transformed)))
    return min(candidates)


def canonical_key(inst):
    """Canonical under label permutations, translations, and grid isometries."""
    payload = (inst["n"], inst["k"], inst["scale"],
               _normalized_points(inst["points"]))
    return hashlib.sha256(repr(payload).encode("ascii")).hexdigest()


def escalate(params):
    params = {k: v for k, v in params.items() if k != "_preset"}
    n = int(params.get("n", DIFFICULTY["hard"]["n"]))
    k = int(params.get("k", DIFFICULTY["hard"]["k"]))
    pitch = int(params.get("pitch", 2000))
    # Grow only the decoy cloud: the written witness stays exactly 2*k atoms.
    return {"n": max(n + 80, (3 * n) // 2), "k": k, "pitch": pitch}


def _ids_to_answer(graph, ids, k):
    chosen = []
    seen = set()
    for index in ids:
        if index not in seen:
            seen.add(index)
            chosen.append(index)
    if len(chosen) > k:
        chosen = chosen[:k]
    if len(chosen) < k:
        for index in range(len(graph["edges"])):
            if index not in seen:
                chosen.append(index)
                seen.add(index)
                if len(chosen) == k:
                    break
    return [list(graph["edges"][index]) for index in chosen]


def _attack_static_coverage(inst):
    graph = _graph(inst)
    order = sorted(range(len(graph["edges"])),
                   key=lambda i: (-graph["covers"][i].bit_count(), graph["edges"][i]))
    return verify(inst, _ids_to_answer(graph, order, inst["k"]))[0]


def _greedy_ids(inst, rng=None, rcl=1):
    graph = _graph(inst)
    uncovered = graph["all"]
    chosen = []
    available = set(range(len(graph["edges"])))
    for _ in range(inst["k"]):
        ranked = sorted(available,
                        key=lambda i: (-(graph["covers"][i] & uncovered).bit_count(),
                                       graph["edges"][i]))
        if not ranked:
            break
        width = min(rcl, len(ranked))
        index = ranked[0] if rng is None else ranked[rng.randrange(width)]
        chosen.append(index)
        available.remove(index)
        uncovered &= ~graph["covers"][index]
        if not uncovered:
            break
    return chosen


def _attack_greedy_gain(inst):
    graph = _graph(inst)
    ids = _greedy_ids(inst)
    return verify(inst, _ids_to_answer(graph, ids, inst["k"]))[0]


def _attack_random_restart(inst, seed, restarts=64):
    graph = _graph(inst)
    rng = random.Random(seed ^ 0x9E3779B9)
    for _ in range(restarts):
        ids = _greedy_ids(inst, rng, rcl=12)
        if verify(inst, _ids_to_answer(graph, ids, inst["k"]))[0]:
            return True
    return False


def _attack_short_edges(inst):
    graph = _graph(inst)
    points = inst["points"]
    order = sorted(range(len(graph["edges"])),
                   key=lambda i: (_sqdist(points[graph["edges"][i][0]],
                                          points[graph["edges"][i][1]]),
                                  graph["edges"][i]))
    return verify(inst, _ids_to_answer(graph, order, inst["k"]))[0]


def _attack_rare_vertex_rounding(inst):
    """A cheap dual-weight set-cover rounding heuristic."""
    graph = _graph(inst)
    weights = [max(1, 1_000_000 // len(graph["by_vertex"][v]))
               for v in range(inst["n"])]
    uncovered = graph["all"]
    chosen = []
    available = set(range(len(graph["edges"])))
    for _ in range(inst["k"]):
        best = None
        best_score = -1
        for i in available:
            bits = graph["covers"][i] & uncovered
            score = 0
            while bits:
                bit = bits & -bits
                score += weights[bit.bit_length() - 1]
                bits -= bit
            if score > best_score:
                best_score, best = score, i
        if best is None:
            break
        chosen.append(best)
        available.remove(best)
        uncovered &= ~graph["covers"][best]
    return verify(inst, _ids_to_answer(graph, chosen, inst["k"]))[0]


def _attack_maximal_matching(inst):
    """Run Section 4's maximal-matching EVDS, then its obvious k-edge trim."""
    graph = _graph(inst)
    order = sorted(range(len(graph["edges"])),
                   key=lambda i: (-graph["covers"][i].bit_count(), graph["edges"][i]))
    used_vertices = set()
    matching = []
    for i in order:
        u, v = graph["edges"][i]
        if u not in used_vertices and v not in used_vertices:
            matching.append(i)
            used_vertices.add(u)
            used_vertices.add(v)
    # A maximal matching is an EVDS but normally violates the threshold.  The
    # attack keeps the k members with greatest individual coverage.
    matching.sort(key=lambda i: -graph["covers"][i].bit_count())
    return verify(inst, _ids_to_answer(graph, matching, inst["k"]))[0]


def _attack_exact_set_cover(inst, node_cap=1_000_000):
    """Capped exact 0--1 set-cover branch-and-bound.

    Every UDG edge represents the set N[u] union N[v].  Equal cover sets are
    merged, the least-constrained uncovered vertex is branched on, and a
    cardinality lower bound plus a transposition table prune the search.  The
    returned success is checked through the public verifier.  This is the
    domain-standard exact attack that invalidated this attempted Track-A
    family at the oracle-selected shipping preset.
    """
    graph = _graph(inst)
    representative = {}
    for edge_id, cover in enumerate(graph["covers"]):
        representative.setdefault(cover, edge_id)
    covers = list(representative)
    representatives = [representative[cover] for cover in covers]
    by_vertex = [[] for _ in range(inst["n"])]
    for cover_id, cover in enumerate(covers):
        bits = cover
        while bits:
            bit = bits & -bits
            by_vertex[bit.bit_length() - 1].append(cover_id)
            bits -= bit

    nodes = 0
    memo = {}
    max_cover = max(cover.bit_count() for cover in covers)

    def search(uncovered, remaining, chosen):
        nonlocal nodes
        nodes += 1
        if nodes > node_cap:
            return None
        if not uncovered:
            return chosen
        if remaining <= 0:
            return False
        if (uncovered.bit_count() + max_cover - 1) // max_cover > remaining:
            return False
        if memo.get(uncovered, -1) >= remaining:
            return False
        memo[uncovered] = remaining

        bits = uncovered
        options = None
        while bits:
            bit = bits & -bits
            vertex = bit.bit_length() - 1
            bits -= bit
            candidate_options = by_vertex[vertex]
            if options is None or len(candidate_options) < len(options):
                options = candidate_options
        ordered = sorted(
            options,
            key=lambda cover_id: -(covers[cover_id] & uncovered).bit_count(),
        )
        for cover_id in ordered:
            result = search(
                uncovered & ~covers[cover_id],
                remaining - 1,
                chosen + (cover_id,),
            )
            if result is None:
                return None
            if result is not False:
                return result
        return False

    result = search(graph["all"], inst["k"], ())
    if result is None or result is False:
        return False, nodes
    edge_ids = [representatives[cover_id] for cover_id in result]
    answer = _ids_to_answer(graph, edge_ids, inst["k"])
    return verify(inst, answer)[0], nodes


def _atom_count(value):
    if isinstance(value, dict):
        return sum(_atom_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_atom_count(v) for v in value)
    return 1


def _relabel_instance(inst, permutation):
    n = inst["n"]
    points = [None] * n
    for old, new in enumerate(permutation):
        points[new] = list(inst["points"][old])
    answer = [[min(permutation[u], permutation[v]),
               max(permutation[u], permutation[v])]
              for u, v in inst["answer"]]
    out = {k: v for k, v in inst.items() if not k.startswith("_")}
    out["points"] = points
    out["answer"] = sorted(answer)
    return out


def _coordinate_variant(inst, code, tx, ty):
    out = {k: v for k, v in inst.items() if not k.startswith("_")}
    out["points"] = _apply_isometry(inst["points"], code, tx, ty)
    out["answer"] = [list(edge) for edge in inst["answer"]]
    return out


def selftest():
    report = {}

    # G1: all ladder rungs, several independent seeds, and JSON-native answers.
    planted_ok = 0
    planted_total = 0
    json_ok = True
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            planted_total += 1
            planted_ok += int(verify(inst, inst["answer"])[0])
            json_ok &= json.loads(json.dumps(inst["answer"])) == inst["answer"]
    report["G1_planted_verifies"] = {
        "pass": planted_ok == planted_total and json_ok,
        "verified": planted_ok,
        "attempts": planted_total,
        "answers_json_native": bool(json_ok),
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = shipping["answer"]
    graph = _graph(shipping)
    corruptions = {
        "drop_one": answer[:-1],
        "collapse_endpoint": [[answer[0][0], answer[0][0]]] + answer[1:],
        "duplicate_edge": [answer[0], answer[0]] + answer[2:],
        "empty": [],
        "out_of_range": [[0, shipping["n"]]] + answer[1:],
    }
    outcomes = {name: verify(shipping, candidate)
                for name, candidate in corruptions.items()}
    reasons = [reason for ok, reason in outcomes.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not ok for ok, _ in outcomes.values())
                and len(set(reasons)) == len(reasons),
        "cases": {name: {"accepted": ok, "reason": reason}
                  for name, (ok, reason) in outcomes.items()},
        "distinct_reasons": len(set(reasons)),
    }

    model_text = ("I checked the closed neighborhoods.\n```json\n<answer>"
                  + json.dumps(answer) + "</answer>\n```\nThat is my final set.")
    parsed = parse_answer(model_text)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("no tagged answer here") is None,
        "parsed_equals_answer": parsed == answer,
        "garbage_returns_none": parse_answer("no tagged answer here") is None,
    }

    # G4/G5 share the same shipping-preset structure-aware sample.
    guess_rng = random.Random(0x211113552)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "candidate_space": str(search_space(shipping)),
        "sampler": "uniform k-subset of actual UDG edges (shape and edge validity enforced)",
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    t0 = time.perf_counter()
    exact_demo = enumerate_all(demo)
    demo_time = time.perf_counter() - t0
    attack_seeds = tuple(range(800, 808))
    t0 = time.perf_counter()
    exact_results = {}
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        exact_results[seed] = _attack_exact_set_cover(inst)
    baseline_time = time.perf_counter() - t0
    exact_successes = sum(int(success) for success, _ in exact_results.values())
    exact_nodes = sum(nodes for _, nodes in exact_results.values())
    report["G5_density_and_baseline"] = {
        "pass": exact_demo is not None and guess_total >= 200_000
                and exact_successes == 0,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_estimate": guess_probability,
        "demo_exact_valid_answers": exact_demo,
        "demo_candidate_space": search_space(demo),
        "demo_enumeration_wall_sec": round(demo_time, 6),
        "strongest_attack": "exact 0-1 set-cover branch-and-bound, 1,000,000-node cap",
        "baseline_successes": exact_successes,
        "baseline_attempts": len(attack_seeds),
        "baseline_wall_sec": round(baseline_time, 6),
        "baseline_search_nodes": exact_nodes,
        "per_seed_nodes": {str(seed): nodes
                           for seed, (_, nodes) in exact_results.items()},
    }

    attacks = {
        "outlier_edge_coverage": 0,
        "greedy_maximum_gain": 0,
        "random_restart_64": 0,
        "geometric_shortest_edges": 0,
        "lp_dual_weight_rounding": 0,
        "paper_maximal_matching_then_trim": 0,
        "exact_set_cover_branch_and_bound": exact_successes,
    }
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        attacks["outlier_edge_coverage"] += int(_attack_static_coverage(inst))
        attacks["greedy_maximum_gain"] += int(_attack_greedy_gain(inst))
        attacks["random_restart_64"] += int(_attack_random_restart(inst, seed, 64))
        attacks["geometric_shortest_edges"] += int(_attack_short_edges(inst))
        attacks["lp_dual_weight_rounding"] += int(_attack_rare_vertex_rounding(inst))
        attacks["paper_maximal_matching_then_trim"] += int(_attack_maximal_matching(inst))
    attack_report = {name: {"successes": successes, "attempts": len(attack_seeds)}
                     for name, successes in attacks.items()}
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attack_report.values()),
        "attacks": attack_report,
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    t0 = time.perf_counter()
    doubled = make_instance(seed=42, **doubled_params)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] > shipping["n"],
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_build_and_verify_wall_sec": round(time.perf_counter() - t0, 6),
        "doubled_planted_verifies": doubled_ok,
    }

    invariant_checks = 0
    carried_checks = 0
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(seed=10_000 + seed, **DIFFICULTY["demo"])
        base_key = canonical_key(base)
        unrelated_keys.append(base_key)
        rng = random.Random(seed)
        permutation = list(range(base["n"]))
        rng.shuffle(permutation)
        variants = [
            _relabel_instance(base, permutation),
            _coordinate_variant(base, 1, 12_345, -7_654),
            _coordinate_variant(_relabel_instance(base, permutation),
                                6, -33_333, 22_222),
            _coordinate_variant(base, 4, 999, 111),
        ]
        for variant in variants:
            invariant_checks += int(canonical_key(variant) == base_key)
            carried_checks += int(verify(variant, variant["answer"])[0])
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 80 and carried_checks == 80
                and len(set(unrelated_keys)) == 20,
        "invariance_passed": invariant_checks,
        "invariance_attempts": 80,
        "carried_witness_passed": carried_checks,
        "carried_witness_attempts": 80,
        "unrelated_distinct": len(set(unrelated_keys)),
        "unrelated_attempts": 20,
        "transformations": "vertex relabel; reflection+translation; composed relabel/isometry; axis swap",
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _atom_count(shipping["answer"])
    intended_operations = 12 * shipping["k"] + 16
    arms = {name: dict(result) for name, result in G9_ORACLE_RESULTS.items()
            if name in ("bare", "hinted", "placebo")}
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    hinted_rate = (hinted["solved"] / hinted["attempts"]
                   if hinted["attempts"] else 0.0)
    placebo_rate = (placebo["solved"] / placebo["attempts"]
                    if placebo["attempts"] else 0.0)
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and intended_operations <= 300)
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

    report["all_passed"] = all(
        value.get("pass", False) for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
