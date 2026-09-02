"""Verified planted spherical-subcode problems inspired by arXiv:2411.04916.

The public family is a pool of exact unit vectors.  A witness selects one vector
from each triple so that all selected inner products are at most 1/2.  Internally
this is a proper 3-colouring of a planted 5-regular graph, embedded exactly as a
binary spherical code.  Only the Python standard library is used.
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
    "medium": {"n": 108, "degree": 5, "mix_factor": 40},
    "hard": {"n": 162, "degree": 5, "mix_factor": 50},
}
SHIPPING_DIFFICULTY = "medium"

NOTES = r"""
Paper connection and definition.  Section 1 of Cohn--Li, arXiv:2411.04916,
defines a kissing configuration as unit vectors with every distinct inner
product at most 1/2.  Section 3 (the discussion immediately before Lemma 3.1)
turns the addition of candidate deep-hole vectors into a compatibility search:
not all candidates can coexist, and one must select a large pairwise-compatible
subcode.  This module scales that exact compatibility task instead of replaying
the fixed published coordinates.

Easy regimes avoided.  Lemma 3.1 completely solves the paper's fixed C_10,
distance-6 instance: an LP bound gives 192 and the proof explicitly classifies
the six cosets used in a solution.  That fixed case is therefore a lookup, not a
generator.  More generally, graph 3-colouring is polynomial-time solvable at
maximum degree at most 3, while Theorem 2 of Cavallaro--Fluschnik,
arXiv:2104.08470, proves NP-hardness even for 5-regular planar Hamiltonian
graphs.  The generated compatibility core is 5-regular and n grows.  No
optimality or nonexistence claim is part of the witness.

Inverse generation and attacks.  A balanced colouring is sampled first.  A
simple 5-regular graph is then generated using only cross-colour edges and mixed
by degree-preserving switches.  Each of the three candidates for every vertex
has conflict degree degree+2, so planted and decoy centers have identical norm,
degree, and neighbor-degree statistics.  The outlier attack therefore reduces
to a fixed tie break; the left-to-right greedy attack and a randomized
min-conflicts restart attack are executed by selftest across eight seeds.  The
canonical key uses rooted colour refinement and structural quotient edge
counts; it never uses the seed, planted answer, or rendered text.

Hardening history.  A proposed 48-vertex "easy" rung was retired after the
32-restart min-conflicts attack solved all 8/8 held-out seeds.  A proposed
84-vertex medium rung likewise failed G6 on 1/8 seeds even though three LLM
oracles had failed it.  The first retained rung is n=108, where each of the
degree, greedy, and restart attacks solved 0/8 and the official multi-vendor
harness returned hardened.  This history is retained because the LLM result by
itself would otherwise have hidden a cheap algorithmic failure.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_INTEGER_LIST_RE = re.compile(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", re.S)
_ENUMERATION_CAP = 600_000


def _pair(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def _deranged_matching(
    left: list[int], right: list[int], forbidden: set[tuple[int, int]], rng: random.Random
) -> list[tuple[int, int]] | None:
    """Find a randomized bijection avoiding the existing cross edges."""
    if len(left) != len(right):
        return None
    order = list(left)
    rng.shuffle(order)

    # Randomized augmenting-path matching is reliable even for the tiny n=12
    # enumeration instance, where blind permutation retries can get stuck.
    choices = {}
    for u in order:
        choices[u] = [v for v in right if _pair(u, v) not in forbidden]
        rng.shuffle(choices[u])
        if not choices[u]:
            return None
    owner: dict[int, int] = {}

    def augment(u: int, seen: set[int]) -> bool:
        for v in choices[u]:
            if v in seen:
                continue
            seen.add(v)
            if v not in owner or augment(owner[v], seen):
                owner[v] = u
                return True
        return False

    for u in order:
        if not augment(u, set()):
            return None
    return [_pair(u, v) for v, u in owner.items()]


def _initial_five_regular(
    groups: list[list[int]], rng: random.Random
) -> list[tuple[int, int]] | None:
    """Build a simple 5-regular tripartite graph before random switches."""
    size = len(groups[0])
    edges: set[tuple[int, int]] = set()

    # Two random perfect matchings between each pair of colour classes.
    for a, b in ((0, 1), (0, 2), (1, 2)):
        for _ in range(2):
            matching = _deranged_matching(groups[a], groups[b], edges, rng)
            if matching is None:
                return None
            edges.update(matching)

    # One more incident edge per vertex.  Balanced halves make the extra edges
    # split evenly among the three pairs of colour classes.
    routed: dict[tuple[int, int], list[int]] = {}
    for colour in range(3):
        vertices = list(groups[colour])
        rng.shuffle(vertices)
        others = [c for c in range(3) if c != colour]
        routed[(colour, others[0])] = vertices[: size // 2]
        routed[(colour, others[1])] = vertices[size // 2 :]

    for a, b in ((0, 1), (0, 2), (1, 2)):
        matching = _deranged_matching(routed[(a, b)], routed[(b, a)], edges, rng)
        if matching is None:
            return None
        edges.update(matching)
    return sorted(edges)


def _connected(n: int, edges: list[tuple[int, int]]) -> bool:
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    seen = {0}
    stack = [0]
    while stack:
        u = stack.pop()
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                stack.append(v)
    return len(seen) == n


def _mix_edges(
    edges: list[tuple[int, int]], colours: list[int], target: int, rng: random.Random
) -> tuple[list[tuple[int, int]], int]:
    """Random degree-preserving switches, never introducing a monochrome edge."""
    work = list(edges)
    edge_set = set(work)
    successes = 0
    attempts = 0
    limit = max(2_000, target * 60)
    while successes < target and attempts < limit:
        attempts += 1
        i = rng.randrange(len(work))
        j = rng.randrange(len(work) - 1)
        if j >= i:
            j += 1
        a, b = work[i]
        c, d = work[j]
        if len({a, b, c, d}) != 4:
            continue
        if rng.randrange(2):
            new1, new2 = _pair(a, c), _pair(b, d)
        else:
            new1, new2 = _pair(a, d), _pair(b, c)
        if colours[new1[0]] == colours[new1[1]]:
            continue
        if colours[new2[0]] == colours[new2[1]] or new1 == new2:
            continue
        old1, old2 = work[i], work[j]
        if {new1, new2} == {old1, old2}:
            continue
        if (new1 in edge_set and new1 not in (old1, old2)) or (
            new2 in edge_set and new2 not in (old1, old2)
        ):
            continue
        edge_set.remove(old1)
        edge_set.remove(old2)
        edge_set.add(new1)
        edge_set.add(new2)
        work[i], work[j] = new1, new2
        successes += 1
    return sorted(edge_set), successes


def _adjacency(n: int, edges: list[tuple[int, int]]) -> list[list[int]]:
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    for row in adj:
        row.sort()
    return adj


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Sample a colouring first, then build a regular graph and centers around it.

    ``n`` is rounded up to a multiple of six (and at least twelve), because the
    balanced 5-regular construction needs even colour classes.  Increasing n
    increases both the witness length and the structure-aware space 3**n.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer")
    degree = params.pop("degree", 5)
    mix_factor = params.pop("mix_factor", 40)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if degree != 5:
        raise ValueError("this family uses degree=5; changing it changes the hard regime")
    if isinstance(mix_factor, bool) or not isinstance(mix_factor, int) or mix_factor < 0:
        raise ValueError("mix_factor must be a nonnegative integer")

    actual_n = max(12, 6 * math.ceil(n / 6))
    rng = random.Random(seed)

    # G: the witness is sampled before any graph edge exists.
    planted_colours = [c for c in range(3) for _ in range(actual_n // 3)]
    rng.shuffle(planted_colours)
    answer = [3 * v + planted_colours[v] for v in range(actual_n)]
    groups = [[v for v, c in enumerate(planted_colours) if c == colour] for colour in range(3)]

    edges = None
    mixed = 0
    for _ in range(100):
        start = _initial_five_regular(groups, rng)
        if start is None:
            continue
        candidate, mixed = _mix_edges(start, planted_colours, mix_factor * actual_n, rng)
        if _connected(actual_n, candidate):
            edges = candidate
            break
    if edges is None:
        raise RuntimeError("could not construct a connected planted regular graph")

    adj = _adjacency(actual_n, edges)
    if any(len(row) != degree for row in adj):
        raise RuntimeError("internal error: generated graph is not 5-regular")
    if any(planted_colours[u] == planted_colours[v] for u, v in edges):
        raise RuntimeError("internal error: generated edge violates the plant")

    return {
        "family": "planted_spherical_subcode_3colour",
        "n": actual_n,
        "requested_n": n,
        "base_degree": degree,
        "conflict_degree": degree + 2,
        "edges": edges,
        "adjacency": adj,
        "mix_factor": mix_factor,
        "mix_successes": mixed,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a complete exact-coordinate spherical-code search problem."""
    n = inst["n"]
    d = inst["conflict_degree"]
    edge_lines = "\n".join(f"{u} {v}" for u, v in inst["edges"])
    return f"""Find a kissing subconfiguration in the following finite pool.

A kissing configuration is a set of unit vectors in Euclidean space such that
the inner product of every two distinct selected vectors is at most 1/2.

There are {n} vertex groups, numbered 0 through {n - 1}.  Group v contains the
three candidate centers with IDs 3*v, 3*v+1, and 3*v+2; their local colours are
0, 1, and 2 respectively.  IDs and vertices are 0-indexed.  You must select
exactly one candidate from every group, hence exactly {n} distinct candidates.
The output IDs must be in strictly increasing order.  Order otherwise has no
mathematical significance, and repetitions are forbidden.

Here is the exact coordinate definition.  Make a conflict graph on all {3*n}
candidate IDs.  Two candidates conflict exactly when either:
  (a) they are different candidates in the same vertex group; or
  (b) they have the same local colour and their vertex pair is in BASE_EDGES.
Every candidate has conflict degree D={d}.  Give the ambient space D common
coordinates C_0,...,C_(D-1), followed by one coordinate Q_e for every unordered
conflict-graph edge e.  For candidate i, let z_i be the 0/1 vector that is 1 in
all D common coordinates and in Q_e exactly when e is incident with i, and 0
elsewhere.  Define the actual center x_i = z_i/sqrt(2*D).

Thus ||x_i||=1 exactly.  For distinct candidates i,j, direct substitution gives
<x_i,x_j>=(D+1)/(2*D)>1/2 if they conflict, and exactly 1/2 otherwise.  Therefore
the requested IDs are precisely a pairwise nonconflicting selection.  You may
use either this inner-product definition or the equivalent conflict rules.

All unordered base-graph edges follow, one "u v" pair per line.  Edges are
inclusive data; a pair not listed is not a base edge.
BASE_EDGES
{edge_lines}
END_BASE_EDGES

Give your final answer inside <answer></answer> tags, as exactly {n}
comma-separated integer candidate IDs in strictly increasing order.
Example of the required syntax: <answer>0, 4, 8</answer>
Output nothing else inside the tags.
"""


def parse_answer(text: str) -> object | None:
    """Extract the final tagged comma-separated integer list, without raising."""
    if not isinstance(text, str):
        return None
    blocks = _ANSWER_RE.findall(text)
    if not blocks:
        return None
    payload = blocks[-1].strip()
    if not payload or _INTEGER_LIST_RE.fullmatch(payload) is None:
        return None
    try:
        return [int(piece.strip()) for piece in payload.split(",")]
    except (TypeError, ValueError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any witness by exact integer inner-product recomputation.

    The planted answer is intentionally never consulted.  Since all selected
    centers have squared unscaled norm 2D, a conflict gives dot D+1 and every
    nonconflict gives dot D.  Checking the two explicit conflict rules is thus
    exactly the same as expanding all binary vectors, without floating point.
    """
    n = inst["n"]
    if not isinstance(answer, list):
        return False, "answer must be a list of candidate indices"
    if not answer:
        return False, "answer is empty"
    if len(answer) != n:
        return False, f"expected exactly {n} candidate indices, got {len(answer)}"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "every candidate index must be an integer"
    if any(x < 0 or x >= 3 * n for x in answer):
        return False, f"candidate index out of range 0..{3*n - 1}"
    if len(set(answer)) != n:
        return False, "candidate indices must be distinct"
    if any(answer[i] >= answer[i + 1] for i in range(n - 1)):
        return False, "candidate indices must be in strictly increasing order"

    colours = [-1] * n
    for candidate in answer:
        vertex, colour = divmod(candidate, 3)
        if colours[vertex] != -1:
            return False, f"more than one candidate was selected from vertex group {vertex}"
        colours[vertex] = colour
    if any(c < 0 for c in colours):
        return False, "one or more vertex groups have no selected candidate"

    d = inst["conflict_degree"]
    # Norms are exactly (D + D)/(2D)=1.  A same-colour base edge contributes
    # the one shared Q_e beyond the D common coordinates.
    for u, v in inst["edges"]:
        if colours[u] == colours[v]:
            i, j = 3 * u + colours[u], 3 * v + colours[v]
            return False, (
                f"selected centers {i} and {j} conflict: unscaled inner product "
                f"{d + 1} exceeds the allowed {d}"
            )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the solver-aware space: one center from every group."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    return [3 * v + rng.randrange(3) for v in range(inst["n"])]


def search_space(inst: dict) -> int | None:
    """Return the structure-aware candidate count (also the naive stated space)."""
    return 3 ** inst["n"]


def enumerate_all(inst: dict) -> int | None:
    """Count all proper colourings exactly when the full space is capped."""
    n = inst["n"]
    if 3**n > _ENUMERATION_CAP:
        return None
    edges = inst["edges"]
    total = 0
    for colours in itertools.product(range(3), repeat=n):
        if all(colours[u] != colours[v] for u, v in edges):
            total += 1
    return total


def _rooted_refinement_code(adj: list[list[int]], root: int) -> str:
    """An isomorphism-invariant rooted quotient code.

    On the random regular graphs used here, individualizing one root normally
    makes colour refinement discrete, in which case the code contains the full
    canonically labelled edge set.  It remains a sound (possibly incomplete)
    invariant if some colour classes do not split.
    """
    n = len(adj)
    labels = [0] * n
    labels[root] = 1
    for _ in range(n + 1):
        signatures = [
            (labels[v], tuple(sorted(labels[w] for w in adj[v]))) for v in range(n)
        ]
        kinds = {sig: i for i, sig in enumerate(sorted(set(signatures)))}
        new_labels = [kinds[sig] for sig in signatures]
        if new_labels == labels:
            break
        labels = new_labels
    classes = max(labels) + 1
    sizes = [0] * classes
    for colour in labels:
        sizes[colour] += 1
    edge_counts: dict[tuple[int, int], int] = {}
    for u in range(n):
        for v in adj[u]:
            if u < v:
                key = _pair(labels[u], labels[v])
                edge_counts[key] = edge_counts.get(key, 0) + 1
    return json.dumps(
        [labels[root], sizes, sorted((a, b, count) for (a, b), count in edge_counts.items())],
        separators=(",", ":"),
    )


def canonical_key(inst: dict) -> str:
    """Return a structural key invariant under vertex and input-edge relabelling."""
    n = inst["n"]
    adj = _adjacency(n, [_pair(u, v) for u, v in inst["edges"]])
    rooted = sorted(_rooted_refinement_code(adj, root) for root in range(n))
    structural = json.dumps(
        [n, sorted(len(row) for row in adj), rooted], separators=(",", ":")
    ).encode("ascii")
    return "rr3c-wl:" + hashlib.sha256(structural).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase the CSP core while keeping the degree-5 hard regime unchanged."""
    current = int(params.get("n", 48))
    if current >= 300:
        return None
    harder = dict(params)
    harder["n"] = 6 * math.ceil((current * 3 / 2) / 6)
    return harder


def _answer_from_colours(colours: list[int]) -> list[int]:
    return [3 * v + colour for v, colour in enumerate(colours)]


def _outlier_attack(inst: dict) -> list[int]:
    # Every local choice has exactly the same conflict degree.  A degree attack
    # has no ranking signal, so its documented deterministic tie-break is 0.
    return [3 * v for v in range(inst["n"])]


def _greedy_attack(inst: dict) -> list[int]:
    colours = [-1] * inst["n"]
    for v in range(inst["n"]):
        forbidden = {colours[w] for w in inst["adjacency"][v] if colours[w] >= 0}
        available = [c for c in range(3) if c not in forbidden]
        colours[v] = available[0] if available else 0
    return _answer_from_colours(colours)


def _random_restart_attack(inst: dict, rng: random.Random) -> list[int]:
    """A bounded min-conflicts attack: 32 restarts and 12n repair moves each."""
    n = inst["n"]
    edges = inst["edges"]
    adj = inst["adjacency"]
    last = [0] * n
    for _ in range(32):
        colours = [rng.randrange(3) for _ in range(n)]
        for _ in range(12 * n):
            bad = [(u, v) for u, v in edges if colours[u] == colours[v]]
            if not bad:
                return _answer_from_colours(colours)
            u, v = bad[rng.randrange(len(bad))]
            vertex = u if rng.randrange(2) == 0 else v
            costs = [sum(colours[w] == c for w in adj[vertex]) for c in range(3)]
            best = min(costs)
            choices = [c for c, cost in enumerate(costs) if cost == best]
            colours[vertex] = choices[rng.randrange(len(choices))]
        last = colours
    return _answer_from_colours(last)


def _relabel_instance(
    inst: dict, permutation: list[int], colour_permutation: list[int], rng: random.Random
) -> dict:
    """Carry an instance and its witness through composed family symmetries."""
    n = inst["n"]
    edges = [_pair(permutation[u], permutation[v]) for u, v in inst["edges"]]
    rng.shuffle(edges)  # Input ordering is also semantically irrelevant.
    old_colours = [candidate % 3 for candidate in inst["answer"]]
    new_colours = [-1] * n
    for old_v, old_colour in enumerate(old_colours):
        new_colours[permutation[old_v]] = colour_permutation[old_colour]
    transformed = dict(inst)
    transformed["edges"] = edges
    transformed["adjacency"] = _adjacency(n, edges)
    transformed["answer"] = _answer_from_colours(new_colours)
    return transformed


def selftest() -> dict:
    """Run all mandatory generation, verification, hardness, and symmetry gates."""
    report: dict[str, Any] = {
        "family": "planted_spherical_subcode_3colour",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: every named preset, eight seeds apiece.
    g1_failures = []
    g1_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(8):
            instance = make_instance(seed=seed, **params)
            ok, reason = verify(instance, instance["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    # G2: generic corruptions hit five different diagnostic branches.
    probe = make_instance(n=48, seed=314159, degree=5, mix_factor=30)
    planted = list(probe["answer"])
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two_positions": [planted[1], planted[0], *planted[2:]],
        "duplicate_index": [planted[0], planted[0], *planted[2:]],
        "empty": [],
        "out_of_range": [*planted[:-1], 3 * probe["n"]],
    }
    g2_results = {}
    for name, bad_answer in corruptions.items():
        ok, reason = verify(probe, bad_answer)
        g2_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in g2_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in g2_results.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "cases": g2_results,
    }

    # G3: model-style prose and markdown around the exact tagged block.
    payload = ", ".join(map(str, probe["answer"]))
    response = f"I checked the pairwise constraints.\n```text\n<answer>{payload}</answer>\n```\nDone."
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == probe["answer"] and parse_answer("garbage") is None,
        "parsed_length": len(parsed) if isinstance(parsed, list) else None,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4: uniform over all 3**n structurally admissible selections.
    ship = make_instance(seed=271828, **DIFFICULTY[SHIPPING_DIFFICULTY])
    trials = 200_000
    hits = 0
    guess_rng = random.Random(1618033)
    for _ in range(trials):
        candidate = random_candidate(ship, guess_rng)
        if verify(ship, candidate)[0]:
            hits += 1
    rate = hits / trials
    report["G4_guess_resistance"] = {
        "pass": rate < 1e-6,
        "hits": hits,
        "total": trials,
        "empirical_rate": rate,
        "sampling_prior": "uniform over one of three centers from every vertex group",
        "structure_aware_space": search_space(ship),
    }

    # G5: the n=12 space is small enough for an exact complete count.
    small = make_instance(n=12, seed=424242, degree=5, mix_factor=20)
    solution_count = enumerate_all(small)
    small_space = search_space(small)
    fraction = None if solution_count is None else solution_count / small_space
    report["G5_sparse"] = {
        "pass": solution_count is not None and 0 < solution_count and fraction < 1e-3,
        "n": small["n"],
        "solutions": solution_count,
        "search_space": small_space,
        "fraction": fraction,
    }

    # G6: construction-aware attacks must all fail on all eight held-out seeds.
    attack_stats = {
        "degree_outlier_tiebreak": {"solved": 0, "attempts": 0},
        "left_to_right_greedy": {"solved": 0, "attempts": 0},
        "random_restart_min_conflicts": {"solved": 0, "attempts": 0},
    }
    for seed in range(100, 108):
        instance = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        attacks = {
            "degree_outlier_tiebreak": _outlier_attack(instance),
            "left_to_right_greedy": _greedy_attack(instance),
            "random_restart_min_conflicts": _random_restart_attack(
                instance, random.Random(900_000 + seed)
            ),
        }
        for name, candidate in attacks.items():
            attack_stats[name]["attempts"] += 1
            attack_stats[name]["solved"] += int(verify(instance, candidate)[0])
    report["G6_adversary_panel"] = {
        "pass": all(stats["solved"] == 0 and stats["attempts"] >= 8 for stats in attack_stats.values()),
        "attacks": attack_stats,
        "identical_candidate_degree": ship["conflict_degree"],
    }

    # G7: doubling the requested size builds, verifies, and cubes the exponent.
    base_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params = dict(base_params)
    doubled_params["n"] = 2 * base_params["n"]
    doubled = make_instance(seed=1234567, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] > ship["n"]
        and search_space(doubled) > search_space(ship),
        "base_n": ship["n"],
        "doubled_n": doubled["n"],
        "base_space_digits": len(str(search_space(ship))),
        "doubled_space_digits": len(str(search_space(doubled))),
        "doubled_verify": doubled_reason,
    }

    # G8: compose vertex relabelling, edge reordering, and global colour relabelling.
    invariant_checks = 0
    carried_witness_checks = 0
    keys = []
    g8_failures = []
    for seed in range(20):
        instance = make_instance(n=24, seed=70_000 + seed, degree=5, mix_factor=20)
        key = canonical_key(instance)
        keys.append(key)
        relabel_rng = random.Random(80_000 + seed)
        permutation = list(range(instance["n"]))
        relabel_rng.shuffle(permutation)
        colour_permutation = [0, 1, 2]
        relabel_rng.shuffle(colour_permutation)
        transformed = _relabel_instance(
            instance, permutation, colour_permutation, relabel_rng
        )
        transformed_key = canonical_key(transformed)
        invariant_checks += 1
        if transformed_key != key:
            g8_failures.append({"seed": seed, "kind": "key_changed"})
        ok, reason = verify(transformed, transformed["answer"])
        carried_witness_checks += 1
        if not ok:
            g8_failures.append({"seed": seed, "kind": "map_not_real", "reason": reason})
        # Edge reordering alone preserves the original, untransformed answer.
        reordered = dict(instance)
        reordered_edges = list(instance["edges"])
        relabel_rng.shuffle(reordered_edges)
        reordered["edges"] = reordered_edges
        reordered["adjacency"] = _adjacency(instance["n"], reordered_edges)
        if canonical_key(reordered) != key or not verify(reordered, instance["answer"])[0]:
            g8_failures.append({"seed": seed, "kind": "edge_order"})
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "real_transformation_witness_checks": carried_witness_checks,
        "distinct_unrelated": distinct,
        "unrelated_total": 20,
        "transformations": ["vertex permutation", "edge-list reorder", "global colour permutation", "composition"],
        "failures": g8_failures,
    }

    gate_values = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
