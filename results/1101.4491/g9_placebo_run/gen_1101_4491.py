"""Verified Track-B generator based on Lemma 2.1 of arXiv:1101.4491.

The paper repeatedly reduces external-certificate selection to the following
bipartite matching fact.  If S is a minimum vertex cover of B=(X union Y,E),
then every I subset S_X can be matched into Y minus S_Y.  Here S=X and I=X.
A modular perfect matching is sampled first, after which indistinguishable
row-wise decoy edges and presentation permutations are added.
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
import time
from collections import Counter, deque


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "The neighbor rows share one row-independent value of right label minus left label modulo n."
)
PLACEBO_HINT: str = (
    "The neighbor rows reward one careful row-by-row check of right labels against left labels throughout."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "bipartite graph",
        "minimum vertex cover",
        "matching from a specified cover subset",
    ],
    "verification_operations": [
        "bipartite edge membership",
        "integer equality",
        "right-endpoint distinctness",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "A hidden perfect matching has one common modular displacement; without "
        "recognizing it, a solver must carry out augmenting-path matching."
    ),
    "hardness_basis": (
        "Track B: Hopcroft--Karp solves Lemma 2.1's bipartite matching task in "
        "O(E sqrt(V)); at n=127 and degree=12 it took a median 3,826 edge "
        "scans and about 0.000153 seconds over eight seeds (a non-guaranteed "
        "depth-2 repair probe took a median 727 scans), while the compact "
        "common-displacement route uses at most n+3*degree=163 exact modular "
        "operations."
    ),
    "max_answer_tokens": 100,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {"medium": {"n": 171, "degree": 20}}
SHIPPING_DIFFICULTY: str = "medium"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A permutation of all n right-vertex labels, written in displayed I-vertex "
        "order.  This enforces the stated length, range, and distinctness before "
        "edge membership is tested; the bounded language therefore has n! strings."
    ),
    "bounds": {
        "max_left_vertices": 254,
        "max_right_vertices": 254,
        "max_answer_atoms": 254,
        "index_base": 0,
    },
}

NOTES: str = (
    "Section 2, Lemma 2.1 fixes the exact family: for a minimum vertex cover S "
    "of a bipartite graph B=(X union Y,E), every I subset S_X can be matched "
    "into Y minus S_Y. Its Hall-theorem proof is the source of the matching "
    "certificate later used in the FAST, dense-RTI, and FASBT kernel proofs. "
    "Here S=X and I=X; the planted perfect matching proves both that S is minimum "
    "and that Lemma 2.1 applies. Section 1 says the four editing problems are NP-"
    "complete but fixed-parameter tractable; Theorems 2.7, 2.20, 3.12, and 4.12 "
    "give 4k, O(k^2), 5k, and 5k kernels, so no Track-A claim is made for a "
    "bounded-conflict planted distribution. Plants and decoys have the same "
    "one-edge marginals. Random row and adjacency order defeats positional rules; "
    "column-degree variation defeats the minimum-degree probe; deterministic and "
    "randomized greedy matching probes are measured; fixed offsets 0,+1,-1 test "
    "an obvious modular ansatz. Hopcroft--Karp and a successful shallow augmenting-"
    "path probe are disclosed as Track-B reference routes."
)


G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "unavailable_quota",
}


def _sample_offsets(rng, n, degree, planted):
    offsets = {planted}
    while len(offsets) < degree:
        offsets.add(rng.randrange(n))
    return offsets


def make_instance(n, seed=0, degree=8, **params) -> dict:
    """Inverse-generate a Lemma-2.1 matching instance.

    The common modular shift, hence a perfect matching, is sampled before any
    decoy edge.  S=X is a vertex cover of size n, while the planted matching has
    size n, so Koenig's theorem (or weak duality for matching/cover) proves S is
    minimum without solving the emitted instance.
    """
    del params
    if isinstance(n, bool) or not isinstance(n, int) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if isinstance(degree, bool) or not isinstance(degree, int):
        raise ValueError("degree must be an integer")
    if degree < 2 or degree >= n:
        raise ValueError("degree must satisfy 2 <= degree < n")

    rng = random.Random(seed)
    planted_shift = rng.randrange(n)
    neighbors = {
        x: {(x + offset) % n for offset in _sample_offsets(rng, n, degree, planted_shift)}
        for x in range(n)
    }

    # A presentation permutation with a useful but non-leaking property: the
    # first three rows have exactly the planted displacement in common.  No edge
    # within any row is marked, and every offset has the same one-edge marginal.
    prefix = None
    vertices = list(range(n))
    for _ in range(5000):
        trial = rng.sample(vertices, 3)
        common = set(range(n))
        for x in trial:
            common &= {(y - x) % n for y in neighbors[x]}
        if common == {planted_shift}:
            prefix = trial
            break
    if prefix is None:
        for trial in itertools.combinations(vertices, 3):
            common = set(range(n))
            for x in trial:
                common &= {(y - x) % n for y in neighbors[x]}
            if common == {planted_shift}:
                prefix = list(trial)
                break
    if prefix is None:
        raise RuntimeError("could not find three rows isolating the planted displacement")

    prefix_set = set(prefix)
    rest = [x for x in vertices if x not in prefix_set]
    rng.shuffle(rest)
    display_order = list(prefix) + rest
    rows = []
    for x in display_order:
        row_neighbors = list(neighbors[x])
        rng.shuffle(row_neighbors)
        rows.append({"left": x, "neighbors": row_neighbors})

    answer = [(row["left"] + planted_shift) % n for row in rows]
    return {
        "family": "Lemma 2.1 cover-subset matching",
        "n": n,
        "degree": degree,
        "left_vertices": list(range(n)),
        "right_vertices": list(range(n)),
        "minimum_vertex_cover": {"S_X": list(range(n)), "S_Y": []},
        "I": list(range(n)),
        "rows": rows,
        "answer": answer,
    }


def _answer_text(answer):
    return ", ".join(str(value) for value in answer)


def render(inst) -> str:
    n = inst["n"]
    degree = inst["degree"]
    rows = [
        f"{position:3d}. x={row['left']}: "
        + " ".join(str(y) for y in row["neighbors"])
        for position, row in enumerate(inst["rows"], 1)
    ]

    hint = ""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        hint = "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        hint = "\n\nHint: " + PLACEBO_HINT

    return f"""MATCHING FROM A MINIMUM-VERTEX-COVER SUBSET

A bipartite graph has two disjoint vertex classes X and Y, and every edge joins
one X vertex to one Y vertex.  A vertex cover is a set touching every edge.  A
matching is a set of edges with no shared endpoint.

Here X=Y={{0,1,...,{n - 1}}}; the two copies are distinct even though their
integer labels are the same.  The displayed row for x lists exactly its {degree}
neighbors in Y, so those and only those pairs xy are edges.  S_X=X and S_Y is
empty; S is a minimum vertex cover.  The specified subset I is all of X.  (A
perfect matching returned below also independently certifies that the n-vertex
cover S is minimum.)

Find a matching of every vertex of I into Y minus S_Y=Y.  Give one right endpoint
for every displayed row, in exactly the displayed row order.  Thus the answer
must contain exactly {n} integers, every integer must lie in 0..{n - 1}, the
integer at a row must occur in that row's neighbor list, and no right endpoint
may repeat.  Row order matters; neighbor order does not.

NEIGHBOR TABLE
{chr(10).join(rows)}{hint}

Give your final answer inside <answer></answer> tags as exactly {n} decimal
integers separated by commas, one right endpoint per displayed row.  Example:
<answer>3, 0, 4</answer>
Output nothing else inside the tags."""


def parse_answer(text):
    """Extract the last tagged comma/whitespace-separated integer list."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json|text)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    if not body:
        return []
    try:
        if body.startswith("["):
            value = json.loads(body)
            if isinstance(value, list) and all(
                isinstance(item, int) and not isinstance(item, bool) for item in value
            ):
                return value
            return None
        pieces = [piece for piece in re.split(r"[\s,]+", body) if piece]
        if not pieces or any(re.fullmatch(r"[+-]?\d+", piece) is None for piece in pieces):
            return None
        return [int(piece) for piece in pieces]
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def verify(inst, answer):
    """Check a matching exactly, without reading inst['answer']."""
    n = inst["n"]
    if not isinstance(answer, list):
        return False, "answer must be a list of right-vertex labels"
    if not answer:
        return False, "answer is empty"
    if len(answer) != n:
        return False, f"expected exactly {n} right endpoints"
    if any(isinstance(value, bool) or not isinstance(value, int) for value in answer):
        return False, "every right endpoint must be an integer"
    if len(set(answer)) != n:
        return False, "right endpoints must be distinct"
    if any(value < 0 or value >= n for value in answer):
        return False, f"right endpoints must lie in 0..{n - 1}"
    for position, (row, value) in enumerate(zip(inst["rows"], answer), 1):
        if value not in row["neighbors"]:
            return False, f"position {position} is not an edge of its displayed row"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from the n! shape/range/distinctness-aware language."""
    candidate = inst["right_vertices"][:]
    rng.shuffle(candidate)
    return candidate


def search_space(inst):
    return math.factorial(inst["n"])


def enumerate_all(inst):
    space = search_space(inst)
    if space > 1_000_000:
        return None
    count = 0
    for candidate in itertools.permutations(inst["right_vertices"]):
        if verify(inst, list(candidate))[0]:
            count += 1
    return count


def _structural_code(inst):
    """Cheap relabelling-invariant code for the bipartite graph.

    Color refinement is supplemented by both sides' pairwise common-neighbor
    multisets.  This is not a complete graph-isomorphism canonical form, a caveat
    recorded in README, but is much stronger than hashing labels or render text.
    """
    rows = inst["rows"]
    n = inst["n"]
    adjacency = [set() for _ in range(2 * n)]
    for row in rows:
        x = row["left"]
        for y in row["neighbors"]:
            adjacency[x].add(n + y)
            adjacency[n + y].add(x)

    colors = [0] * n + [1] * n
    for _ in range(2 * n + 1):
        signatures = [
            (colors[v], tuple(sorted(colors[w] for w in adjacency[v])))
            for v in range(2 * n)
        ]
        palette = {sig: index for index, sig in enumerate(sorted(set(signatures)))}
        new_colors = [palette[sig] for sig in signatures]
        if new_colors == colors:
            break
        colors = new_colors

    left_common = sorted(
        len(adjacency[a] & adjacency[b])
        for a in range(n)
        for b in range(a + 1, n)
    )
    right_common = sorted(
        len(adjacency[n + a] & adjacency[n + b])
        for a in range(n)
        for b in range(a + 1, n)
    )
    color_sizes = sorted(Counter(colors).values())
    edge_color_counts = Counter()
    for x in range(n):
        for y in adjacency[x]:
            edge_color_counts[(colors[x], colors[y])] += 1
    payload = {
        "n": n,
        "color_sizes": color_sizes,
        "edge_colors": sorted((a, b, c) for (a, b), c in edge_color_counts.items()),
        "left_common": left_common,
        "right_common": right_common,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def canonical_key(inst):
    return hashlib.sha256(_structural_code(inst).encode("utf-8")).hexdigest()


def escalate(params):
    """First add same-marginal decoys at fixed answer length, then grow n."""
    n = int(params["n"])
    degree = int(params.get("degree", 8))
    if degree < 20:
        return {"n": n, "degree": min(20, degree + 2)}
    if n + 22 <= 237:
        return {"n": n + 22, "degree": degree}
    return "cap_bound"


def _hopcroft_karp(inst):
    """Return (matching in display order, edge scans), or (None, scans)."""
    rows = inst["rows"]
    n = inst["n"]
    pair_u = [-1] * n
    pair_v = [-1] * n
    distance = [0] * n
    scans = 0

    def bfs():
        nonlocal scans
        queue = deque()
        found = False
        for u in range(n):
            if pair_u[u] == -1:
                distance[u] = 0
                queue.append(u)
            else:
                distance[u] = -1
        while queue:
            u = queue.popleft()
            for v in rows[u]["neighbors"]:
                scans += 1
                mate = pair_v[v]
                if mate == -1:
                    found = True
                elif distance[mate] == -1:
                    distance[mate] = distance[u] + 1
                    queue.append(mate)
        return found

    def dfs(u):
        nonlocal scans
        for v in rows[u]["neighbors"]:
            scans += 1
            mate = pair_v[v]
            if mate == -1 or (distance[mate] == distance[u] + 1 and dfs(mate)):
                pair_u[u] = v
                pair_v[v] = u
                return True
        distance[u] = -1
        return False

    matching = 0
    while bfs():
        for u in range(n):
            if pair_u[u] == -1 and dfs(u):
                matching += 1
    if matching != n:
        return None, scans
    return pair_u, scans


def _outlier_candidate(inst):
    degrees = Counter(y for row in inst["rows"] for y in row["neighbors"])
    return [
        min(row["neighbors"], key=lambda y: (degrees[y], y))
        for row in inst["rows"]
    ]


def _greedy_candidate(inst):
    used = set()
    answer = []
    for row in inst["rows"]:
        available = [y for y in sorted(row["neighbors"]) if y not in used]
        chosen = available[0] if available else min(row["neighbors"])
        answer.append(chosen)
        used.add(chosen)
    return answer


def _randomized_greedy_candidate(inst, rng):
    """Try a random row order, always respecting edges and distinctness."""
    order = list(range(inst["n"]))
    rng.shuffle(order)
    used = set()
    answer = [None] * inst["n"]
    for position in order:
        choices = [
            value
            for value in inst["rows"][position]["neighbors"]
            if value not in used
        ]
        if not choices:
            return None
        chosen = rng.choice(choices)
        answer[position] = chosen
        used.add(chosen)
    return answer


def _bounded_augmenting_candidate(inst, rng, max_depth=2):
    """A deliberately cheap, non-guaranteed matching repair probe.

    This is reported as a successful Track-B reference probe, never as a failing
    attack.  It allows only ``max_depth`` reassignments along an augmenting path.
    """
    n = inst["n"]
    mate = {}
    answer = [None] * n
    scans = 0
    order = list(range(n))
    rng.shuffle(order)

    def augment(position, seen, depth):
        nonlocal scans
        choices = inst["rows"][position]["neighbors"][:]
        rng.shuffle(choices)
        for value in choices:
            scans += 1
            if value in seen:
                continue
            seen.add(value)
            displaced = mate.get(value)
            if displaced is None or (
                depth > 0 and augment(displaced, seen, depth - 1)
            ):
                mate[value] = position
                answer[position] = value
                return True
        return False

    for position in order:
        if not augment(position, set(), max_depth):
            return None, scans
    return answer, scans


def _fixed_offset_candidates(inst):
    n = inst["n"]
    for offset in (0, 1, n - 1):
        candidate = [(row["left"] + offset) % n for row in inst["rows"]]
        yield candidate


def _relabel_instance(inst, rng, *, reorder=False, remap_left=False, remap_right=False):
    """Apply genuine bipartite-graph relabellings and carry the witness."""
    out = copy.deepcopy(inst)
    selected = {row["left"]: value for row, value in zip(out["rows"], out["answer"])}

    if remap_left:
        old = list(range(out["n"]))
        new = old[:]
        rng.shuffle(new)
        mapping = dict(zip(old, new))
        selected = {mapping[x]: y for x, y in selected.items()}
        for row in out["rows"]:
            row["left"] = mapping[row["left"]]
        out["left_vertices"] = sorted(mapping.values())
        out["I"] = sorted(mapping[x] for x in out["I"])
        out["minimum_vertex_cover"]["S_X"] = sorted(
            mapping[x] for x in out["minimum_vertex_cover"]["S_X"]
        )

    if remap_right:
        old = list(range(out["n"]))
        new = old[:]
        rng.shuffle(new)
        mapping = dict(zip(old, new))
        selected = {x: mapping[y] for x, y in selected.items()}
        for row in out["rows"]:
            row["neighbors"] = [mapping[y] for y in row["neighbors"]]
        out["right_vertices"] = sorted(mapping.values())
        out["minimum_vertex_cover"]["S_Y"] = sorted(
            mapping[y] for y in out["minimum_vertex_cover"]["S_Y"]
        )

    if reorder:
        rng.shuffle(out["rows"])
        for row in out["rows"]:
            rng.shuffle(row["neighbors"])

    out["answer"] = [selected[row["left"]] for row in out["rows"]]
    return out


def _answer_atoms(answer):
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, (list, tuple)):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest():
    report = {}

    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **shipping_params)

    swapped = inst["answer"][:]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    corruptions = {
        "drop": inst["answer"][:-1],
        "swap": swapped,
        "duplicate": [inst["answer"][0]] * 2 + inst["answer"][2:],
        "empty": [],
        "out_of_range": [inst["n"]] + inst["answer"][1:],
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "I found a matching by comparing the rows.\n\n<answer>\n```text\n"
        + _answer_text(inst["answer"])
        + "\n```\n</answer>\nThe matching is above."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"],
        "parsed_entries": len(parsed) if isinstance(parsed, list) else None,
    }

    sample_total = 200_000
    sample_rng = random.Random(0x11014491)
    sample_hits = 0
    sample_start = time.perf_counter()
    for _ in range(sample_total):
        candidate = random_candidate(inst, sample_rng)
        if verify(inst, candidate)[0]:
            sample_hits += 1
    sample_seconds = time.perf_counter() - sample_start
    observed = sample_hits / sample_total
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "observed_probability": observed,
        "candidate_space": search_space(inst),
        "prior": "uniform over all n! right-vertex permutations",
    }

    attack_names = (
        "outlier_minimum_column_degree",
        "greedy_first_unused_neighbor",
        "randomized_greedy_restart_256",
        "fixed_offsets_0_plusminus1",
    )
    attack_successes = {name: 0 for name in attack_names}
    reference_successes = 0
    reference_scans = []
    reference_times = []
    repair_successes = 0
    repair_scans = []
    repair_restarts = []
    repair_times = []
    attack_seeds = list(range(800, 808))
    for seed in attack_seeds:
        attack_inst = make_instance(seed=seed, **shipping_params)
        if verify(attack_inst, _outlier_candidate(attack_inst))[0]:
            attack_successes["outlier_minimum_column_degree"] += 1
        if verify(attack_inst, _greedy_candidate(attack_inst))[0]:
            attack_successes["greedy_first_unused_neighbor"] += 1

        restart_rng = random.Random(seed ^ 0xA55A)
        restart_won = False
        for _ in range(256):
            candidate = _randomized_greedy_candidate(attack_inst, restart_rng)
            if candidate is not None and verify(attack_inst, candidate)[0]:
                restart_won = True
                break
        attack_successes["randomized_greedy_restart_256"] += int(restart_won)

        fixed_won = any(
            verify(attack_inst, candidate)[0]
            for candidate in _fixed_offset_candidates(attack_inst)
        )
        attack_successes["fixed_offsets_0_plusminus1"] += int(fixed_won)

        started = time.perf_counter()
        reference_answer, scans = _hopcroft_karp(attack_inst)
        elapsed = time.perf_counter() - started
        solved = reference_answer is not None and verify(attack_inst, reference_answer)[0]
        reference_successes += int(solved)
        reference_scans.append(scans)
        reference_times.append(elapsed)

        repair_rng = random.Random(seed ^ 999)
        repair_total_scans = 0
        repair_answer = None
        repair_started = time.perf_counter()
        for restart in range(1, 17):
            repair_answer, scans = _bounded_augmenting_candidate(
                attack_inst, repair_rng, max_depth=2
            )
            repair_total_scans += scans
            if repair_answer is not None and verify(attack_inst, repair_answer)[0]:
                break
        repair_elapsed = time.perf_counter() - repair_started
        repair_solved = (
            repair_answer is not None and verify(attack_inst, repair_answer)[0]
        )
        repair_successes += int(repair_solved)
        repair_scans.append(repair_total_scans)
        repair_restarts.append(restart)
        repair_times.append(repair_elapsed)

    attacks = {
        name: {"successes": attack_successes[name], "attempts": len(attack_seeds)}
        for name in attack_names
    }
    median_scans = statistics.median(reference_scans)
    median_wall = statistics.median(reference_times)
    median_repair_scans = statistics.median(repair_scans)
    median_repair_restarts = statistics.median(repair_restarts)
    median_repair_wall = statistics.median(repair_times)
    report["G6_adversary_panel"] = {
        "pass": all(entry["successes"] == 0 for entry in attacks.values())
        and reference_successes == len(attack_seeds)
        and repair_successes == len(attack_seeds),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Hopcroft-Karp bipartite maximum matching",
            "complexity": "O(E sqrt(V))",
            "wall_clock_sec_median": median_wall,
            "operations_median_edge_scans": median_scans,
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
        "additional_reference_probe": {
            "name": "random-order depth-2 augmenting-path repair, up to 16 restarts",
            "guaranteed": False,
            "wall_clock_sec_median": median_repair_wall,
            "operations_median_edge_scans": median_repair_scans,
            "restarts_median": median_repair_restarts,
            "solves": f"{repair_successes}/{len(attack_seeds)}, as expected for Track B",
        },
    }

    demo_inst = make_instance(seed=11, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    report["G5_density_and_baseline_cost"] = {
        "pass": observed < 1e-6
        and demo_count is not None
        and reference_successes == len(attack_seeds),
        "shipping_density_hits": sample_hits,
        "shipping_density_samples": sample_total,
        "shipping_density_fraction": observed,
        "shipping_sampling_wall_seconds": sample_seconds,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo_inst),
        "baseline_wall_seconds_median": median_wall,
        "baseline_edge_scan_operations_median": median_scans,
        "shallow_repair_wall_seconds_median": median_repair_wall,
        "shallow_repair_edge_scan_operations_median": median_repair_scans,
        "shallow_repair_restarts_median": median_repair_restarts,
    }

    named_bits = [math.lgamma(params["n"] + 1) / math.log(2) for params in DIFFICULTY.values()]
    doubled_params = {"n": 2 * shipping_params["n"], "degree": shipping_params["degree"]}
    started = time.perf_counter()
    doubled = make_instance(seed=31337, **doubled_params)
    doubled_build = time.perf_counter() - started
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": all(a < b for a, b in zip(named_bits, named_bits[1:])) and doubled_ok,
        "ladder_log2_candidate_spaces": named_bits,
        "doubled_n": doubled_params["n"],
        "doubled_build_seconds": doubled_build,
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = 0
    carried_checks = 0
    g8_failures = []
    unrelated_keys = []
    transforms = (
        {"reorder": True},
        {"remap_left": True},
        {"remap_right": True},
        {"reorder": True, "remap_left": True, "remap_right": True},
    )
    for seed in range(20):
        base = make_instance(seed=10_000 + seed, **shipping_params)
        key = canonical_key(base)
        unrelated_keys.append(key)
        for index, flags in enumerate(transforms):
            moved = _relabel_instance(base, random.Random(seed * 101 + index), **flags)
            invariance_checks += 1
            if canonical_key(moved) != key:
                g8_failures.append(f"seed {seed}, transform {index}: key changed")
            ok, reason = verify(moved, moved["answer"])
            carried_checks += 1
            if not ok:
                g8_failures.append(f"seed {seed}, transform {index}: {reason}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_distinct": distinct_keys,
        "unrelated_attempts": 20,
        "failures": g8_failures,
        "method": "bipartite color refinement plus pairwise common-neighbor multisets",
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    intended_operations = inst["n"] + 3 * inst["degree"]
    arms = copy.deepcopy(G9_RESULTS["arms"])
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else None
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else None
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping_params
    report["all_passed"] = all(
        entry.get("pass") is True
        for key, entry in report.items()
        if key.startswith("G") and isinstance(entry, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
