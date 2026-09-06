"""Planted k-disjoint-clique witness generator for arXiv:1008.2814.

The solver is given a simple undirected graph and must return ``k`` pairwise
disjoint cliques of a prescribed common size.  Generation chooses those vertex
sets first, samples all other edges independently, and finally erases the
construction labels with a uniform vertex permutation.

This module is standard-library only, deterministic from ``(n, seed, params)``,
and performs no I/O at import time.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import random
import re
from typing import Any


DIFFICULTY = {
    "demo": {"n": 16, "k": 1},
    "easy": {"n": 144, "k": 3},
    "medium": {"n": 225, "k": 3},
    "hard": {"n": 400, "k": 3},
    "extreme": {"n": 625, "k": 4},
}
SHIPPING_DIFFICULTY = "easy"


NOTES = r"""
Definition source: Section 2 of Brendan P. W. Ames and Stephen A. Vavasis,
"Convex optimization for the planted k-disjoint-clique problem"
(arXiv:1008.2814), defines a k-disjoint-clique subgraph as k vertex-disjoint
cliques; it need not cover the graph.  Its maximum-node objective is not used
here because an optimum would violate the witness-only contract.  Instead the
statement supplies k and a common clique size, and asks for the feasibility
witness at the heart of that formulation.  Direct edge lookup verifies it.

Hard/easy boundary: Section 2 notes worst-case NP-hardness already at k=1.
Section 3, Theorem 3.1 gives polynomial-time convex recovery under adversarial
noise when only O(r_hat^2) extra edges obey per-clique degree bounds.  Section
4 defines the random planted model used here.  Theorem 4.5 and the examples
immediately following it recover constant-p random instances when the minimum
clique size is at least order sqrt(N) (and impose additional restrictions on
the clique sizes/count).  The conclusions explicitly say there are no matching
lower bounds.  This generator deliberately takes r=floor(N^(9/20))+1, which is
o(sqrt(N)), so it is outside that proved polynomial recovery regime.  Search
hardness for this planted random distribution is the standard planted-clique
assumption, not a theorem of the paper; the paper proves only worst-case
NP-hardness and recovery above a sufficient threshold.

The answer is sampled first as k disjoint equal-size sets.  Every remaining
edge, including edges between planted cliques and all decoy-decoy edges, is a
fair independent coin.  A final uniform permutation hides positions and clique
order.  Thus planted vertices have only the unavoidable sub-sqrt(N) internal
degree shift; no special label, width, edge probability, or ordering identifies
them.  The adversary panel tests (1) high-degree outlier seeds followed by
degree-greedy completion, (2) deterministic left-to-right clique growth, and
(3) randomized restarts using induced-degree greedy growth.

An initial 64-vertex/2-clique rung is intentionally not a preset: although a
first oracle run failed to solve it, G6 found that degree-greedy solved 4/8
fixed seeds and randomized greedy solved 8/8.  It was removed before shipping.
The 16-vertex ``demo`` rung exists only for a readable example and deliberate
oracle escalation; the first level eligible to ship under all local gates is
the 144-vertex ``easy`` rung.

Graph isomorphism is not known to have a simple general polynomial canonical
form.  canonical_key runs canonical 1-dimensional Weisfeiler-Leman refinement.
For these dense random graphs it normally makes every vertex unique, in which
case the emitted adjacency serialization is a complete canonical form.  A
deterministic stable-colour quotient plus degree/triangle/common-neighbour
profiles is used if refinement is not discrete.  That fallback is a strong
invariant, not a complete isomorphism test; nonisomorphic adversarial graphs
could collide.  The key never reads the seed, render output, or planted answer.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 1_000_000


def _integer_power_floor(n: int, numerator: int, denominator: int) -> int:
    """Return floor(n ** (numerator / denominator)) using integer arithmetic."""
    lo, hi = 0, n + 1
    target = n ** numerator
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if mid ** denominator <= target:
            lo = mid
        else:
            hi = mid
    return lo


def _clique_size(n: int) -> int:
    return _integer_power_floor(n, 9, 20) + 1


def _rows_to_bits(rows: list[list[str]]) -> list[str]:
    return ["".join(row) for row in rows]


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Sample the disjoint clique witness first, then build a noisy graph.

    ``n`` is the number of graph vertices and is the size parameter.  The
    common required clique size is ``floor(n**(9/20)) + 1``.  The optional
    ``k`` parameter defaults to 3.  All non-forced edges have probability 1/2.
    Larger ``n`` increases the matrix size, clique size, and candidate space.
    """
    k = params.pop("k", 3)
    if params:
        unknown = ", ".join(sorted(params))
        raise TypeError(f"unknown make_instance parameter(s): {unknown}")
    if not isinstance(n, int) or isinstance(n, bool) or n < 16:
        raise ValueError("n must be an integer at least 16")
    if not isinstance(k, int) or isinstance(k, bool) or k < 1:
        raise ValueError("k must be a positive integer")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed must be an integer")

    r = _clique_size(n)
    if k * r > n:
        raise ValueError("n is too small for k disjoint cliques of the required size")

    rng = random.Random(seed)

    # G: sample the answer before any graph edge.  These temporary labels and
    # the construction order are erased by the final uniform permutation.
    pool = list(range(n))
    rng.shuffle(pool)
    planted = [pool[i * r:(i + 1) * r] for i in range(k)]
    planted_pair = set()
    for clique in planted:
        planted_pair.update((min(u, v), max(u, v))
                            for u, v in itertools.combinations(clique, 2))

    rows = [["0"] * n for _ in range(n)]
    for u in range(n):
        for v in range(u + 1, n):
            edge = (u, v) in planted_pair or rng.getrandbits(1) == 1
            if edge:
                rows[u][v] = "1"
                rows[v][u] = "1"

    # A uniform relabelling removes positions and construction order.  The
    # answer's clique order is independently shuffled because it has no meaning.
    permutation = list(range(n))
    rng.shuffle(permutation)
    moved = [["0"] * n for _ in range(n)]
    for u in range(n):
        pu = permutation[u]
        for v in range(u + 1, n):
            if rows[u][v] == "1":
                pv = permutation[v]
                moved[pu][pv] = "1"
                moved[pv][pu] = "1"
    answer = [sorted(permutation[v] for v in clique) for clique in planted]
    rng.shuffle(answer)

    row_order = list(range(n))
    rng.shuffle(row_order)
    return {
        "family": "planted_k_disjoint_clique_feasibility",
        "n": n,
        "k": k,
        "clique_size": r,
        "edge_probability_numerator": 1,
        "edge_probability_denominator": 2,
        "adjacency": _rows_to_bits(moved),
        "row_order": row_order,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a complete, unambiguous problem statement."""
    n = inst["n"]
    k = inst["k"]
    r = inst["clique_size"]
    lines = [
        "Planted k-disjoint-clique witness problem",
        "",
        f"The graph has {n} vertices numbered 0 through {n - 1} inclusive.",
        "It is a simple undirected graph: it has no loops, and adjacency is",
        "symmetric. A clique of size r is a set of r distinct vertices for which",
        "every pair of different vertices is joined by an edge.",
        "",
        f"Find exactly {k} pairwise vertex-disjoint cliques, each of size exactly {r}.",
        "The cliques need not cover every vertex. The order of the cliques and the",
        "order of vertices inside a clique do not matter. Vertices may not repeat",
        "inside a clique or occur in two different cliques.",
        "",
        "ADJACENCY MATRIX",
        "Each labeled row contains exactly one bit per vertex. In row v, bit j is",
        "1 exactly when vertices v and j are adjacent; positions are counted from",
        "0 at the left. Every diagonal bit is 0. Rows may be displayed out of",
        "numeric order, so use the integer label before the colon.",
    ]
    for vertex in inst.get("row_order", range(n)):
        lines.append(f"{vertex}: {inst['adjacency'][vertex]}")
    lines.extend([
        "",
        f"Return a JSON array containing exactly {k} arrays. Each inner array must",
        f"contain exactly {r} distinct 0-based vertex numbers. JSON integers only:",
        "do not use names, ranges, ellipses, or repeated values.",
        "",
        "Give your final answer inside <answer></answer> tags, as that JSON array.",
        "Example syntax only (for two cliques of size three):",
        "<answer>[[0,4,9],[2,5,7]]</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Extract the last tagged JSON answer, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if not body:
        return None
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        # Also tolerate the repository's generic ``[...], [...]`` list-of-lists
        # probe, while the public contract continues to require the outer array.
        try:
            value = json.loads("[" + body + "]")
        except (TypeError, ValueError):
            return None
    return value


def _edge(inst: dict, u: int, v: int) -> bool:
    return inst["adjacency"][u][v] == "1"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid clique collection; never consult the planted answer."""
    k = inst["k"]
    r = inst["clique_size"]
    n = inst["n"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON array of cliques"
    if len(answer) != k:
        return False, f"wrong number of cliques: expected {k}, got {len(answer)}"

    used: set[int] = set()
    for clique_index, clique in enumerate(answer):
        if not isinstance(clique, list):
            return False, f"clique {clique_index} must be a JSON array"
        if len(clique) != r:
            return False, (f"wrong clique size at clique {clique_index}: "
                           f"expected {r}, got {len(clique)}")
        for value in clique:
            if not isinstance(value, int) or isinstance(value, bool):
                return False, f"non-integer vertex in clique {clique_index}"
            if value < 0 or value >= n:
                return False, f"vertex out of range in clique {clique_index}: {value}"
        if len(set(clique)) != r:
            return False, f"duplicate vertex within clique {clique_index}"
        overlap = used.intersection(clique)
        if overlap:
            return False, f"vertex occurs in more than one clique: {min(overlap)}"
        used.update(clique)
        ordered = sorted(clique)
        for u, v in itertools.combinations(ordered, 2):
            if not _edge(inst, u, v):
                return False, f"missing edge in clique {clique_index}: {u}-{v}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from shape-valid disjoint equal-size clique candidates.

    This incorporates every free structural rule in the statement: exact inner
    and outer sizes, in-range distinct vertices, pairwise disjointness, and the
    irrelevance of both orders.  It does not bias toward graph edges or the
    planted witness.
    """
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    count = inst["k"] * inst["clique_size"]
    picked = rng.sample(range(inst["n"]), count)
    r = inst["clique_size"]
    groups = [sorted(picked[i:i + r]) for i in range(0, count, r)]
    groups.sort()
    return groups


def search_space(inst: dict) -> int | None:
    """Count unordered collections of k disjoint r-subsets of n vertices."""
    n, k, r = inst["n"], inst["k"], inst["clique_size"]
    if k < 0 or r < 0 or k * r > n:
        return 0
    return math.factorial(n) // (
        math.factorial(n - k * r) * (math.factorial(r) ** k) * math.factorial(k)
    )


def _is_clique(inst: dict, vertices: tuple[int, ...] | list[int]) -> bool:
    return all(_edge(inst, u, v) for u, v in itertools.combinations(vertices, 2))


def enumerate_all(inst: dict) -> int | None:
    """Exactly count witnesses when the structure-aware space is at most 1e6."""
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    n, k, r = inst["n"], inst["k"], inst["clique_size"]
    cliques = [combo for combo in itertools.combinations(range(n), r)
               if _is_clique(inst, combo)]
    count = 0
    for chosen in itertools.combinations(cliques, k):
        union: set[int] = set()
        for clique in chosen:
            union.update(clique)
        if len(union) == k * r:
            count += 1
    return count


def _adjacency_bits(inst: dict) -> list[int]:
    return [int(row, 2) for row in inst["adjacency"]]


def _wl_colours(inst: dict) -> list[int]:
    """Canonical 1-WL colours, with numeric IDs assigned by sorted signatures."""
    n = inst["n"]
    neighbours = [[j for j, bit in enumerate(row) if bit == "1"]
                  for row in inst["adjacency"]]
    degrees = [len(row) for row in neighbours]
    palette = {degree: colour for colour, degree in enumerate(sorted(set(degrees)))}
    colours = [palette[degree] for degree in degrees]
    for _ in range(n):
        signatures = [(colours[v], tuple(sorted(colours[w] for w in neighbours[v])))
                      for v in range(n)]
        unique = sorted(set(signatures))
        mapping = {signature: colour for colour, signature in enumerate(unique)}
        new_colours = [mapping[signature] for signature in signatures]
        if new_colours == colours:
            break
        colours = new_colours
    return colours


def canonical_key(inst: dict) -> str:
    """Hash a vertex-relabeling invariant of the public graph and target shape."""
    n = inst["n"]
    colours = _wl_colours(inst)
    rows_as_int = _adjacency_bits(inst)
    colour_classes: dict[int, list[int]] = {}
    for vertex, colour in enumerate(colours):
        colour_classes.setdefault(colour, []).append(vertex)

    payload: dict[str, Any] = {
        "version": 1,
        "n": n,
        "k": inst["k"],
        "r": inst["clique_size"],
        "class_sizes": [len(colour_classes[c]) for c in sorted(colour_classes)],
    }
    if len(colour_classes) == n:
        order = sorted(range(n), key=lambda vertex: colours[vertex])
        payload["mode"] = "discrete-wl-canonical"
        payload["canonical_adjacency"] = [
            "".join(inst["adjacency"][u][v] for v in order) for u in order
        ]
    else:
        # Relabeling-invariant fallback.  It intentionally does not claim to be
        # complete for adversarial graph isomorphism.
        degrees = [row.bit_count() for row in rows_as_int]
        triangles = []
        common_profiles = []
        for u in range(n):
            triangle_twice = 0
            profile = []
            for v in range(n):
                if u == v:
                    continue
                common = (rows_as_int[u] & rows_as_int[v]).bit_count()
                if inst["adjacency"][u][v] == "1":
                    triangle_twice += common
                profile.append((inst["adjacency"][u][v], degrees[v],
                                colours[v], common))
            triangles.append(triangle_twice // 2)
            common_profiles.append((colours[u], degrees[u], triangles[-1],
                                    tuple(sorted(profile))))
        quotient_edges = []
        for c1 in sorted(colour_classes):
            for c2 in sorted(colour_classes):
                if c1 > c2:
                    continue
                edges = 0
                for u in colour_classes[c1]:
                    for v in colour_classes[c2]:
                        if ((c1 != c2 or u < v)
                                and inst["adjacency"][u][v] == "1"):
                            edges += 1
                quotient_edges.append((c1, c2, edges))
        payload["mode"] = "stable-invariant-fallback"
        payload["vertex_profiles"] = sorted(common_profiles)
        payload["quotient_edges"] = quotient_edges

    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return "kdc-invariant-v1:" + hashlib.sha256(encoded).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase graph order by 50%, keeping the sub-sqrt clique exponent."""
    if not isinstance(params, dict) or "n" not in params:
        return None
    n = params["n"]
    if not isinstance(n, int) or isinstance(n, bool) or n >= 1400:
        return None
    out = dict(params)
    out["n"] = n + max(64, n // 2)
    return out


def _degrees(inst: dict) -> list[int]:
    return [row.count("1") for row in inst["adjacency"]]


def _complete_shape(inst: dict, partial: list[list[int]], order: list[int]) -> list[list[int]]:
    """Fill an attack's partial groups without using the plant or breaking shape."""
    used = {v for group in partial for v in group}
    cursor = 0
    for group in partial:
        while len(group) < inst["clique_size"]:
            while order[cursor] in used:
                cursor += 1
            value = order[cursor]
            cursor += 1
            group.append(value)
            used.add(value)
    while len(partial) < inst["k"]:
        group = []
        while len(group) < inst["clique_size"]:
            while order[cursor] in used:
                cursor += 1
            value = order[cursor]
            cursor += 1
            group.append(value)
            used.add(value)
        partial.append(group)
    return [sorted(group) for group in partial]


def _grow_greedily(inst: dict, order: list[int]) -> list[list[int]]:
    """Grow k cliques using a fixed public vertex preference order."""
    used: set[int] = set()
    groups: list[list[int]] = []
    r = inst["clique_size"]
    for _ in range(inst["k"]):
        group: list[int] = []
        for vertex in order:
            if vertex not in used and all(_edge(inst, vertex, u) for u in group):
                group.append(vertex)
                if len(group) == r:
                    break
        used.update(group)
        groups.append(group)
    return _complete_shape(inst, groups, order)


def _attack_degree_outlier(inst: dict) -> list[list[int]]:
    degrees = _degrees(inst)
    order = sorted(range(inst["n"]), key=lambda v: (-degrees[v], v))
    return _grow_greedily(inst, order)


def _attack_left_to_right(inst: dict) -> list[list[int]]:
    return _grow_greedily(inst, list(range(inst["n"])))


def _attack_random_restarts(
    inst: dict, rng: random.Random, restarts: int = 24
) -> list[list[int]] | None:
    """Randomized induced-degree clique growth, constrained to valid shape."""
    n, k, r = inst["n"], inst["k"], inst["clique_size"]
    all_vertices = set(range(n))
    fallback_order = list(range(n))
    for _ in range(restarts):
        available = set(all_vertices)
        groups: list[list[int]] = []
        failed = False
        for _group_index in range(k):
            if not available:
                failed = True
                break
            group = [rng.choice(tuple(sorted(available)))]
            candidates = {v for v in available - set(group)
                          if _edge(inst, v, group[0])}
            while len(group) < r and candidates:
                # Prefer vertices with many neighbours still in the common
                # neighbourhood; random ties make restarts genuinely distinct.
                scored = []
                for v in candidates:
                    induced_degree = sum(_edge(inst, v, w)
                                         for w in candidates if w != v)
                    scored.append((induced_degree, rng.random(), v))
                vertex = max(scored)[2]
                group.append(vertex)
                candidates = {v for v in candidates if v != vertex
                              and _edge(inst, v, vertex)}
            if len(group) < r:
                failed = True
                break
            groups.append(group)
            available.difference_update(group)
        if not failed:
            candidate = [sorted(group) for group in groups]
            if verify(inst, candidate)[0]:
                return candidate
        shaped = _complete_shape(inst, groups, fallback_order)
        if verify(inst, shaped)[0]:
            return shaped
    return None


def _copy_public(inst: dict) -> dict:
    return {
        key: (list(value) if key in ("adjacency", "row_order") else value)
        for key, value in inst.items()
        if key != "answer"
    }


def _transformed_instance(inst: dict, mode: str, salt: int) -> dict:
    """Apply genuine public symmetries and carry the witness through them."""
    rng = random.Random(0x10082814 + salt)
    out = _copy_public(inst)
    answer = [list(group) for group in inst["answer"]]
    n = inst["n"]

    if mode in ("vertex_relabel", "combined"):
        permutation = list(range(n))
        rng.shuffle(permutation)
        moved = [["0"] * n for _ in range(n)]
        for u in range(n):
            for v in range(u + 1, n):
                if inst["adjacency"][u][v] == "1":
                    pu, pv = permutation[u], permutation[v]
                    moved[pu][pv] = "1"
                    moved[pv][pu] = "1"
        out["adjacency"] = _rows_to_bits(moved)
        out["row_order"] = [permutation[v] for v in out["row_order"]]
        answer = [[permutation[v] for v in group] for group in answer]

    if mode in ("row_reorder", "combined"):
        rng.shuffle(out["row_order"])

    if mode in ("answer_reorder", "combined"):
        rng.shuffle(answer)
        for group in answer:
            rng.shuffle(group)

    out["answer"] = answer
    return out


def _find_swap_corruption(inst: dict) -> list[list[int]]:
    candidate = [list(group) for group in inst["answer"]]
    for i in range(len(candidate)):
        for j in range(i + 1, len(candidate)):
            for ai, a in enumerate(candidate[i]):
                for bj, b in enumerate(candidate[j]):
                    left = candidate[i][:]
                    right = candidate[j][:]
                    left[ai], right[bj] = b, a
                    if not _is_clique(inst, left) or not _is_clique(inst, right):
                        candidate[i], candidate[j] = left, right
                        return candidate
    raise RuntimeError("could not construct a swap corruption")


def selftest() -> dict:
    """Run mandatory gates G1--G8 and return measured results."""
    report: dict[str, Any] = {}

    # G1: every named preset and several independent seeds.
    g1_failures = []
    g1_total = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_total += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "verified": g1_total,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **ship_params)

    # G2: five different corruptions and five different checker diagnostics.
    dropped = [list(group) for group in inst["answer"]]
    dropped[0] = dropped[0][:-1]
    swapped = _find_swap_corruption(inst)
    duplicate = [list(group) for group in inst["answer"]]
    duplicate[0][0] = duplicate[0][1]
    out_of_range = [list(group) for group in inst["answer"]]
    out_of_range[0][0] = inst["n"]
    corruptions = {
        "drop_one": dropped,
        "swap_between_cliques": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    g2_results = {name: verify(inst, candidate)
                  for name, candidate in corruptions.items()}
    reasons = [reason for ok, reason in g2_results.values() if not ok]
    report["G2_rejects_corruption"] = {
        "pass": (all(not ok for ok, _ in g2_results.values())
                 and len(set(reasons)) == len(corruptions)),
        "cases": {name: {"rejected": not ok, "reason": reason}
                  for name, (ok, reason) in g2_results.items()},
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic prose plus a Markdown fence around the exact tagged JSON.
    body = json.dumps(inst["answer"], separators=(",", ":"))
    model_reply = ("I checked all pairwise edges and disjointness.\n\n```json\n"
                   f"<answer>\n{body}\n</answer>\n```\nFinal witness above.")
    parsed = parse_answer(model_reply)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0],
        "parsed_equal": parsed == inst["answer"],
    }

    # G4: uniform shape-valid partitions, not arbitrary nested arrays/subsets.
    guess_rng = random.Random(0x10082814)
    total = 200_000
    hits = 0
    for _ in range(total):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    report["G4_guess_resistance"] = {
        "pass": hits / total < 1e-6,
        "hits": hits,
        "total": total,
        "empirical_probability": hits / total,
        "prior": ("uniform unordered collection of k disjoint r-subsets; exact "
                  "shape, range, uniqueness, and disjointness enforced"),
        "structure_aware_search_space": search_space(inst),
    }

    # G5: an exact small control of the identical planted/noise construction.
    tiny = make_instance(n=16, k=2, seed=7)
    tiny_count = enumerate_all(tiny)
    tiny_space = search_space(tiny)
    fraction = None if tiny_count is None else tiny_count / tiny_space
    report["G5_sparse"] = {
        "pass": (tiny_count is not None and fraction is not None
                 and fraction < 0.001),
        "control_n": tiny["n"],
        "control_k": tiny["k"],
        "control_clique_size": tiny["clique_size"],
        "enumerated_solutions": tiny_count,
        "structure_aware_search_space": tiny_space,
        "solution_fraction": fraction,
        "shipping_enumeration": enumerate_all(inst),
        "enumeration_cap": _ENUMERATION_CAP,
    }

    # G6: attacks use only public data and always propose/check a full witness.
    attack_rows: dict[str, list[dict[str, Any]]] = {
        "degree_outlier_greedy": [],
        "left_to_right_greedy": [],
        "induced_degree_random_restarts": [],
    }
    for seed in range(8):
        attacked = make_instance(seed=10_000 + seed, **ship_params)
        degree_candidate = _attack_degree_outlier(attacked)
        degree_ok, degree_reason = verify(attacked, degree_candidate)
        left_candidate = _attack_left_to_right(attacked)
        left_ok, left_reason = verify(attacked, left_candidate)
        restart_candidate = _attack_random_restarts(
            attacked, random.Random(90_000 + seed), restarts=24,
        )
        restart_ok = (restart_candidate is not None
                      and verify(attacked, restart_candidate)[0])
        attack_rows["degree_outlier_greedy"].append({
            "seed": seed, "solved": degree_ok, "reason": degree_reason,
        })
        attack_rows["left_to_right_greedy"].append({
            "seed": seed, "solved": left_ok, "reason": left_reason,
        })
        attack_rows["induced_degree_random_restarts"].append({
            "seed": seed, "solved": restart_ok, "restarts": 24,
        })
    attack_summary = {
        name: {
            "successes": sum(bool(row["solved"]) for row in rows),
            "seeds": len(rows),
            "runs": rows,
        }
        for name, rows in attack_rows.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in attack_summary.values()),
        "attacks": attack_summary,
    }

    # G7: double graph order; exponent and candidate space must both increase.
    doubled_params = dict(ship_params)
    doubled_params["n"] = 2 * ship_params["n"]
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (doubled_ok
                 and doubled["n"] == 2 * inst["n"]
                 and doubled["clique_size"] > inst["clique_size"]
                 and search_space(doubled) > search_space(inst)),
        "base_n": inst["n"],
        "doubled_n": doubled["n"],
        "base_clique_size": inst["clique_size"],
        "doubled_clique_size": doubled["clique_size"],
        "base_search_space": search_space(inst),
        "doubled_search_space": search_space(doubled),
        "planted_verify": doubled_ok,
        "verify_reason": doubled_reason,
    }

    # G8: vertex labels, displayed row order, answer order, and compositions.
    modes = ("vertex_relabel", "row_reorder", "answer_reorder", "combined")
    invariance_checks = 0
    real_transform_checks = 0
    failures = []
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(seed=50_000 + seed, **ship_params)
        base_key = canonical_key(base)
        unrelated_keys.append(base_key)
        for mode in modes:
            moved = _transformed_instance(base, mode, seed)
            invariance_checks += 1
            if canonical_key(moved) != base_key:
                failures.append({"seed": seed, "mode": mode,
                                 "kind": "key_changed"})
            ok, reason = verify(moved, moved["answer"])
            real_transform_checks += 1
            if not ok:
                failures.append({"seed": seed, "mode": mode,
                                 "kind": "carried_witness_failed",
                                 "reason": reason})
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not failures and distinct == 20,
        "invariance_checks": invariance_checks,
        "real_transform_checks": real_transform_checks,
        "transformations": list(modes),
        "unrelated_distinct": distinct,
        "unrelated_total": 20,
        "failures": failures,
        "caveat": ("complete when 1-WL is discrete; otherwise a strong cheap "
                   "invariant, not a complete graph-isomorphism canonical form"),
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(ship_params)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
