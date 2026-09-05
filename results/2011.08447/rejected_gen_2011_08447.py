"""Exploratory rejected generator for below-threshold planted-clique recovery.

The family is the r=t=0 specialization of Definition 2 in Khanna,
"Exact recovery of planted cliques in semi-random graphs"
(arXiv:2011.08447v5).  A clique is sampled first, so its witness is known by
inverse generation; all remaining edges are independent Bernoulli(1/2).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import time
from collections import Counter
from itertools import combinations


TRACK = "A"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "undirected graph from the G(n,1/2) planted-clique model",
        "fixed-cardinality vertex set",
    ],
    "verification_operations": [
        "integer range and distinctness checks",
        "exact adjacency-bit lookup",
        "pairwise clique check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "search pruning",
    "intuition_description": (
        "A true clique keeps surviving repeated common-neighborhood intersections; "
        "without choosing a coherent branch, random neighborhoods leave an exponential search."
    ),
    "hardness_basis": (
        "Track A: Section 1.4 cites the Barak-Hopkins-Kelner-Kothari-Moitra-Potechin "
        "degree-d Sum-of-Squares lower bound for planted clique below n^(1/2-o(1)); "
        "this p=1/2 family uses k about 1.1*n^0.4=o(sqrt(n)), and at the shipping "
        "preset a color-bound exact clique search exhausts 100,000 nodes on 8/8 seeds."
    ),
    "max_answer_tokens": 40,
}

NATIVE: dict = {
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

# k is explicit only for the hand-scale demonstration.  The other presets use
# the integer-only schedule k=ceil(1.1*n^0.4), which stays below sqrt(n).
DIFFICULTY: dict = {
    "demo": {"n": 16, "k": 6},
    "easy": {"n": 768},
    "medium": {"n": 896},
    "hard": {"n": 1024},
}

SHIPPING_DIFFICULTY = "easy"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "An unordered set of exactly k distinct 0-indexed vertex IDs from 0..n-1, "
        "serialized canonically as an increasing JSON-style integer list; every pair "
        "of selected vertices must be an edge."
    ),
    "bounds": {
        "cardinality": "instance k (16 at the initial shipping preset)",
        "entry_min": 0,
        "entry_max": "n-1",
        "distinct": True,
        "order_semantics": "irrelevant; increasing form is canonical",
        "maximum_supported_cardinality": 256,
    },
}

STRUCTURAL_HINT = (
    "A genuine clique is marked by unusually persistent intersections of several vertex neighborhoods."
)

PLACEBO_HINT = (
    "A careful solution should keep close track of vertex numbering and adjacency-row boundaries."
)

# Filled from the separately run oracle arms after hardening.  These are external
# measurements, never used by generation or verification.
G9_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}
G9_HINTED_VERDICT = "pending"

NOTES = r"""
Paper reading:
- Definition 2 in Section 1.2 fixes the native semi-random model.  Setting r=t=0
  leaves the planted set S, its random boundary, and the G(n-k,p) Gamma block;
  Section 1.4 explicitly identifies this as ordinary planted clique.
- Theorem 2 and Algorithm 1 make the paper's studied k=Omega(sqrt(np)) regime
  polynomial-time via an SDP, so this module does not claim Track A there.
- Section 1.4 cites the nearly tight SoS lower bound below sqrt(n).  The generated
  schedule k=Theta(n^0.4), p=1/2 lies in that below-threshold regime while staying
  above the typical background clique scale at the shipped sizes.

Generation samples S first and then samples every non-S pair with the same fair
coin.  There are no label, ordering, degree-correction, or decoy distributions that
distinguish planted vertices beyond the clique edges themselves.

Attacks:
- degree outlier: choose the k highest-degree vertices;
- global greedy: start at maximum degree and repeatedly maximize residual degree;
- 256 random restarts: the same residual-degree heuristic from random starts;
- centered spectral: shifted power iteration on A-(J-I)/2 with three rounding widths;
- exact color-bound search: a Tomita-style greedy-color upper bound, capped at
  100,000 recursive nodes.  This is also the measured strongest baseline.

The paper's SDP was not run: the module is standard-library-only and no SDP solver
is available.  The centered spectral method and exact color-bound branch-and-bound
cover the principal polynomial planted-subgraph attack and the standard exact
maximum-clique attack, respectively; omission of the SDP is a README caveat.
"""


def _default_k(n: int) -> int:
    """Return ceil(1.1*n**0.4), using integer arithmetic only."""
    k = 3
    # (1.1*n^.4)^5 = 1.1^5*n^2 = 1.61051*n^2.
    while 100_000 * (k**5) < 161_051 * n * n:
        k += 1
    return k


def _has_edge(rows: list[int], u: int, v: int) -> bool:
    return bool((rows[u] >> v) & 1)


def _degrees(rows: list[int]) -> list[int]:
    return [row.bit_count() for row in rows]


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Plant S first, then sample all other edges; no instance is solved."""
    if isinstance(n, bool) or not isinstance(n, int) or n < 8:
        raise ValueError("n must be an integer at least 8")
    k = params.pop("k", None)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if k is None:
        k = _default_k(n)
    if isinstance(k, bool) or not isinstance(k, int) or not 3 <= k <= min(256, n):
        raise ValueError("k must be an integer in 3..min(256,n)")

    rng = random.Random(seed)
    planted = set(rng.sample(range(n), k))
    rows = [0] * n
    for u in range(n):
        for v in range(u + 1, n):
            present = (u in planted and v in planted) or bool(rng.getrandbits(1))
            if present:
                rows[u] |= 1 << v
                rows[v] |= 1 << u

    return {
        "family": "G(n,1/2) planted clique (Definition 2 with r=t=0)",
        "n": n,
        "k": k,
        "p": [1, 2],
        "adjacency_rows": rows,
        "answer": sorted(planted),
    }


def _bit_chunks(bits: str, width: int = 64) -> str:
    return " ".join(bits[i : i + width] for i in range(0, len(bits), width)) or "-"


def render(inst: dict) -> str:
    n = inst["n"]
    k = inst["k"]
    rows = inst["adjacency_rows"]
    lines = [
        "PLANTED-CLIQUE WITNESS PROBLEM",
        "",
        f"The vertices of an undirected simple graph are the integers 0 through {n - 1}.",
        f"Find any set of exactly {k} distinct vertices that induces a clique.",
        "A clique means that every two distinct selected vertices are joined by an edge.",
        "Order has no mathematical meaning, but write the IDs in strictly increasing order.",
        "",
        "The graph is given by the upper triangle of its adjacency matrix.",
        "On row i, after deleting spaces, character offset t (starting at 0) is the",
        "edge bit for the pair (i, i+1+t): 1 means edge and 0 means nonedge.",
        "A dash denotes the empty final row. Spaces merely group bits for readability.",
        "",
        "UPPER-TRIANGLE ROWS",
    ]
    for u in range(n):
        bits = "".join("1" if _has_edge(rows, u, v) else "0" for v in range(u + 1, n))
        lines.append(f"{u}: {_bit_chunks(bits)}")
    lines.extend(
        [
            "",
            "Give your final answer inside <answer></answer> tags as exactly k",
            "comma-separated, strictly increasing decimal vertex IDs, with no repeats.",
            "Example: <answer>3, 17, 42</answer>",
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
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("[") and body.endswith("]"):
        body = body[1:-1].strip()
    if not body:
        return []
    parts = [part.strip() for part in body.split(",")]
    if any(not re.fullmatch(r"[+-]?\d+", part) for part in parts):
        return None
    try:
        return [int(part) for part in parts]
    except (TypeError, ValueError, OverflowError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    # Deliberately never consult inst["answer"].
    if not isinstance(answer, list):
        return False, "answer must be a list of vertex IDs"
    if not answer:
        return False, "answer is empty"
    if len(answer) != inst["k"]:
        return False, f"expected exactly {inst['k']} vertices"
    if any(isinstance(v, bool) or not isinstance(v, int) for v in answer):
        return False, "every vertex ID must be an integer"
    if any(v < 0 or v >= inst["n"] for v in answer):
        return False, f"vertex ID outside 0..{inst['n'] - 1}"
    if len(set(answer)) != len(answer):
        return False, "vertex IDs must be distinct"
    rows = inst["adjacency_rows"]
    for u, v in combinations(answer, 2):
        if not _has_edge(rows, u, v):
            return False, f"vertices {u} and {v} are not adjacent"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    return sorted(rng.sample(range(inst["n"]), inst["k"]))


def search_space(inst: dict) -> int | None:
    return math.comb(inst["n"], inst["k"])


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 100_000:
        return None
    count = 0
    for candidate in combinations(range(inst["n"]), inst["k"]):
        if verify(inst, list(candidate))[0]:
            count += 1
    return count


def _wl_invariant(inst: dict) -> object:
    """A strong cheap isomorphism invariant, not a claimed GI canonizer."""
    rows = inst["adjacency_rows"]
    n = inst["n"]
    colors = [0] * n
    for _ in range(8):
        signatures = []
        for v in range(n):
            counts: Counter[int] = Counter()
            bits = rows[v]
            while bits:
                bit = bits & -bits
                u = bit.bit_length() - 1
                bits -= bit
                counts[colors[u]] += 1
            signatures.append((colors[v], tuple(sorted(counts.items()))))
        palette = {sig: i for i, sig in enumerate(sorted(set(signatures)))}
        new_colors = [palette[sig] for sig in signatures]
        if new_colors == colors:
            break
        colors = new_colors

    class_sizes = tuple(sorted(Counter(colors).items()))
    edge_counts: Counter[tuple[int, int]] = Counter()
    for u in range(n):
        bits = rows[u] >> (u + 1)
        offset = u + 1
        while bits:
            bit = bits & -bits
            v = offset + bit.bit_length() - 1
            bits -= bit
            a, b = sorted((colors[u], colors[v]))
            edge_counts[(a, b)] += 1
    return [n, inst["k"], class_sizes, tuple(sorted(edge_counts.items()))]


def canonical_key(inst: dict) -> str:
    payload = json.dumps(_wl_invariant(inst), separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    n = int(params.get("n", 0))
    if n < 8:
        return None
    next_n = n + max(128, n // 4)
    next_k = _default_k(next_n)
    if next_k > 256:
        return "cap_bound"
    # Drop an explicit demo k: escalated levels follow the below-threshold schedule.
    return {"n": next_n}


def _candidate_ok(inst: dict, candidate: list[int] | None) -> bool:
    return candidate is not None and verify(inst, candidate)[0]


def _greedy_candidate(inst: dict, start: int) -> list[int] | None:
    rows = inst["adjacency_rows"]
    degrees = _degrees(rows)
    n = inst["n"]
    k = inst["k"]
    remaining = (1 << n) - 1
    chosen: list[int] = []
    vertex = start
    while len(chosen) < k:
        chosen.append(vertex)
        remaining &= rows[vertex]
        remaining &= ~(1 << vertex)
        if len(chosen) == k:
            return chosen
        if not remaining:
            return None
        bits = remaining
        best_vertex = -1
        best_score = (-1, -1)
        while bits:
            bit = bits & -bits
            v = bit.bit_length() - 1
            bits -= bit
            score = ((rows[v] & remaining).bit_count(), degrees[v])
            if score > best_score:
                best_score = score
                best_vertex = v
        vertex = best_vertex
    return chosen


def _spectral_candidates(inst: dict, iterations: int = 48) -> tuple[list[list[int]], int]:
    """Shifted power iteration for the leading centered-adjacency direction."""
    rows = inst["adjacency_rows"]
    n = inst["n"]
    k = inst["k"]
    neighbors: list[list[int]] = []
    directed_edges = 0
    for row in rows:
        vertices = []
        bits = row
        while bits:
            bit = bits & -bits
            vertices.append(bit.bit_length() - 1)
            bits -= bit
        neighbors.append(vertices)
        directed_edges += len(vertices)

    rng = random.Random(0x201108447)
    x = [rng.random() - 0.5 for _ in range(n)]
    mean = sum(x) / n
    x = [value - mean for value in x]
    shift = 2.0 * math.sqrt(n)
    for _ in range(iterations):
        total = sum(x)
        y = [
            sum(x[u] for u in neighbors[v]) - 0.5 * (total - x[v]) + shift * x[v]
            for v in range(n)
        ]
        mean_y = sum(y) / n
        y = [value - mean_y for value in y]
        norm = math.sqrt(sum(value * value for value in y))
        if norm == 0.0:
            break
        x = [value / norm for value in y]

    outputs: list[list[int]] = []
    for reverse in (True, False):
        ranked = sorted(range(n), key=lambda v: x[v], reverse=reverse)
        for width in (k, 2 * k, 3 * k):
            pool = ranked[: min(width, n)]
            pool_mask = sum(1 << v for v in pool)
            outputs.append(
                sorted(
                    sorted(pool, key=lambda v: (rows[v] & pool_mask).bit_count(), reverse=True)[:k]
                )
            )
    operations = iterations * (directed_edges + 8 * n)
    return outputs, operations


def _color_bound_search(
    inst: dict, node_cap: int = 100_000
) -> tuple[list[int] | None, int, bool]:
    """Budgeted exact maximum-clique search with greedy-color upper bounds."""
    rows = inst["adjacency_rows"]
    n = inst["n"]
    target = inst["k"]
    nodes = 0
    exhausted = False
    solution: list[int] | None = None

    def color_sort(candidates: int) -> tuple[list[int], list[int]]:
        order: list[int] = []
        bounds: list[int] = []
        color = 0
        uncolored = candidates
        while uncolored:
            color += 1
            available = uncolored
            while available:
                bit = available & -available
                vertex = bit.bit_length() - 1
                order.append(vertex)
                bounds.append(color)
                uncolored &= ~bit
                available &= ~bit
                available &= ~rows[vertex]
        return order, bounds

    def expand(candidates: int, chosen: list[int]) -> bool:
        nonlocal nodes, exhausted, solution
        nodes += 1
        if nodes > node_cap:
            exhausted = True
            return False
        order, bounds = color_sort(candidates)
        for idx in range(len(order) - 1, -1, -1):
            if len(chosen) + bounds[idx] < target:
                return False
            vertex = order[idx]
            extended = chosen + [vertex]
            if len(extended) == target:
                solution = extended
                return True
            if expand(candidates & rows[vertex], extended):
                return True
            candidates &= ~(1 << vertex)
            if exhausted:
                return False
        return False

    expand((1 << n) - 1, [])
    return solution, nodes, exhausted


def _permuted_instance(inst: dict, old_to_new: list[int]) -> tuple[dict, list[int]]:
    n = inst["n"]
    rows = inst["adjacency_rows"]
    new_rows = [0] * n
    for u in range(n):
        bits = rows[u] >> (u + 1)
        offset = u + 1
        while bits:
            bit = bits & -bits
            v = offset + bit.bit_length() - 1
            bits -= bit
            a, b = old_to_new[u], old_to_new[v]
            new_rows[a] |= 1 << b
            new_rows[b] |= 1 << a
    carried = sorted(old_to_new[v] for v in inst["answer"])
    changed = dict(inst)
    changed["adjacency_rows"] = new_rows
    changed["answer"] = carried
    return changed, carried


def _json_token_count(answer: object) -> int:
    blob = json.dumps(answer, separators=(",", ":"))
    return len(re.findall(r"-?\d+|[\[\],:{}]", blob))


def selftest() -> dict:
    report: dict = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    # G1: every preset and several independent seeds.
    g1_failures = []
    g1_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(3):
            inst = make_instance(seed=seed, **params)
            g1_checks += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed, "reason": "not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    # G2: five corruption classes with five distinct rejection messages.
    inst = make_instance(seed=2718, **DIFFICULTY["demo"])
    answer = inst["answer"]
    replacement = None
    for outsider in range(inst["n"]):
        if outsider in answer:
            continue
        candidate = answer[:-1] + [outsider]
        if not verify(inst, candidate)[0]:
            replacement = candidate
            break
    corruptions = {
        "drop_one": answer[:-1],
        "replace_one": replacement,
        "duplicate": answer[:-1] + [answer[0]],
        "empty": [],
        "out_of_range": answer[:-1] + [inst["n"]],
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [value["reason"] for value in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(value["rejected"] for value in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic prose and a fenced answer block.
    encoded = ", ".join(map(str, answer))
    response = f"I checked all pairs.\n```text\n<answer>{encoded}</answer>\n```\n"
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed": parsed,
        "garbage_returns_none": parse_answer("no tagged answer here") is None,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=424242, **shipping_params)

    # G4/G5 density: the structure-aware prior is uniform over k-subsets.
    guess_rng = random.Random(0xC1A0)
    samples = 200_000
    hits = 0
    for _ in range(samples):
        hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    probability = hits / samples
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": probability,
        "candidate_space": search_space(shipping),
        "prior": "uniform over all k-element vertex subsets",
    }

    demo_count_inst = make_instance(seed=101, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_count_inst)

    # G6 attacks, with exact-search timing retained for G5's strongest baseline.
    attack_attempts = 8
    successes = {
        "outlier_top_degree": 0,
        "greedy_residual_degree": 0,
        "random_restart_256": 0,
        "centered_spectral_rounding": 0,
        "exact_color_bound_100k": 0,
    }
    exact_nodes = []
    exact_seconds = []
    exact_exhausted = 0
    spectral_operations = []
    for seed in range(attack_attempts):
        trial = make_instance(seed=seed, **shipping_params)
        degrees = _degrees(trial["adjacency_rows"])
        degree_answer = sorted(
            sorted(range(trial["n"]), key=lambda v: degrees[v], reverse=True)[: trial["k"]]
        )
        successes["outlier_top_degree"] += int(_candidate_ok(trial, degree_answer))

        start = max(range(trial["n"]), key=lambda v: degrees[v])
        successes["greedy_residual_degree"] += int(
            _candidate_ok(trial, _greedy_candidate(trial, start))
        )

        restart_rng = random.Random(70_000 + seed)
        restart_hit = False
        for _ in range(256):
            candidate = _greedy_candidate(trial, restart_rng.randrange(trial["n"]))
            if _candidate_ok(trial, candidate):
                restart_hit = True
                break
        successes["random_restart_256"] += int(restart_hit)

        spectral, op_count = _spectral_candidates(trial)
        spectral_operations.append(op_count)
        successes["centered_spectral_rounding"] += int(
            any(_candidate_ok(trial, candidate) for candidate in spectral)
        )

        before = time.perf_counter()
        exact_answer, nodes, exhausted = _color_bound_search(trial, node_cap=100_000)
        exact_seconds.append(time.perf_counter() - before)
        exact_nodes.append(nodes)
        exact_exhausted += int(exhausted)
        successes["exact_color_bound_100k"] += int(_candidate_ok(trial, exact_answer))

    attacks = {
        name: {"successes": count, "attempts": attack_attempts}
        for name, count in successes.items()
    }
    attacks["random_restart_256"]["restarts_per_attempt"] = 256
    attacks["centered_spectral_rounding"]["iterations"] = 48
    attacks["centered_spectral_rounding"]["max_estimated_operations"] = max(
        spectral_operations
    )
    attacks["exact_color_bound_100k"]["node_cap"] = 100_000
    attacks["exact_color_bound_100k"]["exhausted_attempts"] = exact_exhausted
    attacks["exact_color_bound_100k"]["max_nodes"] = max(exact_nodes)
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in attacks.values()),
        "attacks": attacks,
        "paper_sdp_not_run": (
            "No standard-library SDP solver is available; centered spectral rounding and "
            "exact color-bound maximum-clique search were run instead."
        ),
    }

    report["G5_density_and_baseline"] = {
        "pass": isinstance(probability, float)
        and exact_nodes
        and all(node >= 100_000 for node in exact_nodes),
        "shipping_density": {
            "hits": hits,
            "samples": samples,
            "observed_fraction": probability,
            "preset": SHIPPING_DIFFICULTY,
            "n": shipping["n"],
            "k": shipping["k"],
        },
        "exact_small_count": {
            "preset": "demo",
            "n": demo_count_inst["n"],
            "k": demo_count_inst["k"],
            "valid_answers": demo_count,
            "candidate_space": search_space(demo_count_inst),
        },
        "strongest_attack": {
            "name": "greedy-color upper-bound exact clique search",
            "node_cap": 100_000,
            "nodes_per_seed": exact_nodes,
            "wall_clock_sec_per_seed": [round(value, 6) for value in exact_seconds],
            "total_wall_clock_sec": round(sum(exact_seconds), 6),
            "successes": successes["exact_color_bound_100k"],
            "attempts": attack_attempts,
        },
    }

    # G7: double n and let the below-threshold schedule grow k sublinearly.
    doubled = make_instance(n=2 * shipping["n"], seed=9090)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(shipping),
        "shipping": {
            "n": shipping["n"],
            "k": shipping["k"],
            "candidate_space": search_space(shipping),
        },
        "doubled": {
            "n": doubled["n"],
            "k": doubled["k"],
            "candidate_space": search_space(doubled),
            "verify_reason": doubled_reason,
        },
    }

    # G8: vertex relabellings and their compositions on 20 independent graphs.
    invariance_checks = 0
    transport_checks = 0
    nontrivial_transforms = 0
    invariant_failures = []
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(n=64, k=9, seed=50_000 + seed)
        base_key = canonical_key(base)
        unrelated_keys.append(base_key)
        rng = random.Random(60_000 + seed)
        p1 = list(range(base["n"]))
        p2 = list(range(base["n"]))
        rng.shuffle(p1)
        rng.shuffle(p2)
        composed = [p2[p1[v]] for v in range(base["n"])]
        for permutation in (p1, p2, composed):
            changed, carried = _permuted_instance(base, permutation)
            invariance_checks += 1
            transport_checks += 1
            nontrivial_transforms += int(changed["adjacency_rows"] != base["adjacency_rows"])
            if canonical_key(changed) != base_key:
                invariant_failures.append(f"key-seed-{seed}")
            if not verify(changed, carried)[0]:
                invariant_failures.append(f"witness-seed-{seed}")
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures
        and invariance_checks == 60
        and transport_checks == 60
        and nontrivial_transforms >= 20
        and distinct == 20,
        "invariance_checks": invariance_checks,
        "real_transform_verify_checks": transport_checks,
        "nontrivial_transformations": nontrivial_transforms,
        "distinct_unrelated": distinct,
        "unrelated_attempts": 20,
        "failures": invariant_failures,
        "transformations": ["vertex permutation A", "vertex permutation B", "A composed with B"],
        "key_kind": "8-round color-refinement quotient; strong invariant, not complete GI",
    }

    answers = [make_instance(seed=80_000 + seed, **shipping_params)["answer"] for seed in range(16)]
    answer_chars = max(len(json.dumps(value, separators=(",", ":"))) for value in answers)
    answer_tokens = max(_json_token_count(value) for value in answers)
    answer_elements = max(len(value) for value in answers)
    # No answer-producing shortcut follows from the common-neighborhood
    # observation. Counting only a known-good branch would assume the witness.
    intended_operations = min(exact_nodes) if exact_nodes else 100_001
    hinted = G9_ARM_RESULTS["hinted"]
    placebo = G9_ARM_RESULTS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    within_caps = (
        answer_chars <= 2_000
        and answer_tokens <= 500
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": G9_HINTED_VERDICT == "hardened" and within_caps,
        "arms": G9_ARM_RESULTS,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_HINTED_VERDICT,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "operation_definition": (
            "minimum measured nodes of the strongest branch search; the paper "
            "supplies no shorter post-insight answer-producing route"
        ),
        "caps": {"chars": 2_000, "tokens": 500, "atomic_elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
