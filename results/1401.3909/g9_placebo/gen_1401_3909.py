"""Verified problem generator for arXiv:1401.3909.

The generated problem is the exact three-game road-trip subproblem used in
Section 5 of Hoshino and Kawarabayashi's BTTP paper. A team starts at home,
must visit every away venue once, may visit exactly three venues per trip, and
returns home between trips. The answer is the ordered trip plan.

Instances are inverse-generated. We first choose the triplet partition and
then make the venues leaves of a weighted tree with one branch per triplet.
Every valid plan traverses every leaf edge twice; the planted plan is exactly
the one that traverses every branch edge only twice. Thus its optimality is an
identity, not the result of solving a completed instance.

Only the Python standard library is required. Importing this module performs
no file I/O, networking, or printing.
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
from typing import Any


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - the integer implementation is complete
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "optimization",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "symmetric integer venue-distance matrix",
        "ordered three-game road trips",
    ],
    "verification_operations": [
        "partition coverage check",
        "exact integer route-length summation",
        "integer threshold comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Home-to-venue distances have the same residue modulo n+1 precisely "
        "inside each optimal three-game road trip; without noticing this, a "
        "solver must search triplet exact covers or reconstruct the tree metric."
    ),
    "hardness_basis": (
        "Track B: Section 5's standard ordered-trip enumeration has "
        "n!/((n/3)!*2^(n/3)) cases (340,540,200 already at n=15); for the "
        "shipping n=126 distribution a complete exact tree-profile scan is "
        "O(n^3), performs 976,500 row-difference subtractions, and succeeds, "
        "while the compact residue invariant needs 126 modular reductions."
    ),
    "max_answer_tokens": 125,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of n/3 ordered triples partitioning team labels 0..n-1. "
        "Trip order is immaterial and reversing a trip is equivalent, so the "
        "structure-aware language uses lexicographically sorted trips with "
        "each trip no greater than its reversal."
    ),
    "bounds": {
        "number_of_trips": "n/3",
        "trip_length": 3,
        "team_min": 0,
        "team_max": "n-1",
        "each_team_exactly_once": True,
        "quotiented_symmetries": ["trip permutation", "trip reversal"],
        "language_size": "n!/((n/3)!*2^(n/3))",
    },
}

DIFFICULTY = {
    "hard": {"n": 126, "weight_scale": 4096},
}

SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Home-to-venue distances share a residue modulo n+1 exactly within the "
    "three-venue branches of the optimal road-trip plan."
)
PLACEBO_HINT = (
    "The route lengths are exact integers, so keep team labels and trip "
    "endpoints consistent throughout the calculation."
)

# Populated from the script-owned hardening transcripts after those runs.
G9_MEASUREMENTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_yet_measured",
}

NOTES = r"""
Paper definition and Step 0. Section 2 defines BTTP travel: a team begins at
home, travels directly between consecutive away venues, and returns home after
its last away game. The at-most-three constraint limits a road trip to three
games. Section 5 then computes an individual lower bound ILB_t by partitioning
the opposing league into three-team trips and enumerating
n!/((n/3)!*2^(n/3)) ordered trip plans. That is the native problem generated
here; no graph, finite-field, or SAT surrogate replaces it.

What is hard and what is easy. Theorem 1 proves general BTTP and uniform BTTP*
NP-complete, but that worst-case result does not establish hardness for an
inverse-generated distribution. Section 4's Propositions 1 and 2 are the easy
warning: global constraints and individual lower bounds prune the special
n=6 NPB instance, although the reported computation still took 34,716 seconds.
This module therefore makes the narrower Track-B claim. Its completed tree
metrics have a polynomial reconstruction algorithm. Comparing two venue rows
at every other venue recovers sibling leaves in O(n^3); the shipping scan uses
exactly C(126,2)*(126-2)=976,500 subtractions. The compact route instead takes
each of 126 home distances modulo 127 and groups equal residues.

Inverse construction and certificate. Sample the triplet partition first.
For each triplet create a positive-weight branch from the home root and attach
its three venues by positive leaf edges. Each home distance on a branch is
chosen to have one branch-specific residue modulo n+1. For any ordered trip,
the route length is the sum of tree-edge traversals. Across a complete plan
every leaf edge is traversed twice. The planted grouping traverses every
branch edge twice; any other grouping splits at least one branch across two or
more trips and traverses that positive edge at least four times. Thus the
planted grouping is the unique optimal partition (trip order and reversal can
still vary), and the target is known without solving.

Attack hardening. Team labels are shuffled. Branch residues, center weights,
and leaf magnitudes are exchangeable across groups. Leaf magnitudes span a
much wider range than the branch discount, so sorting home distances, taking
the locally cheapest trip, grouping consecutive labels, and uniform random
restart do not reveal the planted partition. The successful complete
distance-profile reconstruction is reported separately as Track B's reference
algorithm rather than misreported as a failed Track-A attack.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 250_000


def _validate_params(n: int, weight_scale: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer")
    if isinstance(weight_scale, bool) or not isinstance(weight_scale, int):
        raise ValueError("weight_scale must be an integer")
    if n < 6 or n % 3:
        raise ValueError("n must be a multiple of 3 and at least 6")
    if not 1 <= weight_scale <= 1_000_000:
        raise ValueError("weight_scale must lie in [1,1000000]")


def _canonical_trip(trip: list[int] | tuple[int, int, int]) -> tuple[int, int, int]:
    direct = tuple(trip)
    reverse = tuple(reversed(trip))
    return min(direct, reverse)


def _canonical_plan(plan: list[list[int]]) -> list[list[int]]:
    return [list(row) for row in sorted(_canonical_trip(row) for row in plan)]


def _plan_cost(inst: dict, plan: list[list[int]]) -> int:
    matrix = inst["distance"]
    total = 0
    for a, b, c in plan:
        # Matrix index 0 is home; away team t has matrix index t+1.
        ai, bi, ci = a + 1, b + 1, c + 1
        total += (
            matrix[0][ai]
            + matrix[ai][bi]
            + matrix[bi][ci]
            + matrix[ci][0]
        )
    return total


def make_instance(n: int, seed: int = 0, *, weight_scale: int = 64) -> dict:
    """Inverse-generate a certified optimal three-game road-trip plan."""

    _validate_params(n, weight_scale)
    rng = random.Random(seed)
    groups = n // 3
    modulus = n + 1

    # G: choose the certificate before any distances exist.
    hidden_group = [group for group in range(groups) for _ in range(3)]
    rng.shuffle(hidden_group)
    residues = rng.sample(range(modulus), groups)

    # Home-to-leaf magnitudes are deliberately much more variable than the
    # branch discount. Consequently local magnitude heuristics do not expose
    # sibling leaves, while exact global optimality still follows from the tree.
    q_low = 20_000 * weight_scale
    q_high = q_low + 2_000_000 * weight_scale
    quotients = rng.sample(range(q_low, q_high), n)
    # Branch-edge savings stay in the same small exact range as the leaf
    # magnitudes grow. Raising weight_scale therefore crowds the objective:
    # wrong plans become relatively closer to the optimum without changing
    # the answer length or compromising the strict integer gap.
    center_edge = [rng.randrange(1, 201) for _ in range(groups)]
    home_distance = [
        modulus * quotients[team] + residues[hidden_group[team]]
        for team in range(n)
    ]
    leaf_edge = [
        home_distance[team] - center_edge[hidden_group[team]]
        for team in range(n)
    ]
    assert min(leaf_edge) > 0

    # Matrix index 0 is the home venue. The remaining n points are leaves of
    # the weighted tree described in the module docstring.
    size = n + 1
    distance = [[0] * size for _ in range(size)]
    for team in range(n):
        idx = team + 1
        distance[0][idx] = home_distance[team]
        distance[idx][0] = home_distance[team]
    for i in range(n):
        for j in range(i + 1, n):
            if hidden_group[i] == hidden_group[j]:
                value = leaf_edge[i] + leaf_edge[j]
            else:
                value = home_distance[i] + home_distance[j]
            distance[i + 1][j + 1] = value
            distance[j + 1][i + 1] = value

    planted_groups = [[] for _ in range(groups)]
    for team, group in enumerate(hidden_group):
        planted_groups[group].append(team)
    answer = _canonical_plan([sorted(row) for row in planted_groups])

    inst = {
        "paper": "arXiv:1401.3909",
        "n": n,
        "weight_scale": weight_scale,
        "distance": distance,
        "target": 0,
        "answer": answer,
    }
    inst["target"] = _plan_cost(inst, answer)
    return inst


def _matrix_text(matrix: list[list[int]]) -> str:
    """Render the strict upper triangle with H followed by away labels."""

    n = len(matrix) - 1
    lines = ["H: " + " ".join(str(matrix[0][j]) for j in range(1, n + 1))]
    for team in range(n - 1):
        row = " ".join(
            str(matrix[team + 1][other + 1])
            for other in range(team + 1, n)
        )
        lines.append(f"{team}: {row}")
    lines.append(f"{n - 1}: (empty)")
    return "\n".join(lines)


def render(inst: dict) -> str:
    """Return the complete problem statement and exact output contract."""

    statement = f"""Three-game road-trip planning (arXiv:1401.3909, Section 5)

One team has a home venue H and must play once at each of n={inst['n']} away
venues labelled 0,...,{inst['n'] - 1}. It starts at H, makes exactly
{inst['n'] // 3} separate road trips, and returns to H after every trip. Every
road trip visits exactly three distinct away venues, and every away venue must
occur in exactly one trip.

A trip [a,b,c] is ordered: its route is H -> a -> b -> c -> H. Its length is
D(H,a)+D(a,b)+D(b,c)+D(c,H). The total plan length is the sum over all trips.
The order of the trips is irrelevant. Reversing one trip gives the same length
because D is symmetric, but any orientation is accepted.

The exact symmetric integer distance matrix has zero diagonal. Its strict
upper triangle is listed below. The first row gives D(H,0),...,D(H,n-1).
Each later row i gives D(i,i+1),...,D(i,n-1), in that order.

{_matrix_text(inst['distance'])}

Find a road-trip plan whose total length is at most T={inst['target']}
(inclusive).

Give your final answer inside <answer></answer> tags as one JSON list of exactly
{inst['n'] // 3} ordered triples, using each integer 0,...,{inst['n'] - 1}
exactly once. Example syntax: <answer>[[0,1,2],[3,4,5]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the final tagged JSON value; return None on malformed text."""

    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    payload = matches[-1].strip()
    if payload.startswith("```") and payload.endswith("```"):
        lines = payload.splitlines()
        if len(lines) >= 2:
            payload = "\n".join(lines[1:-1]).strip()
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return answer if isinstance(answer, list) else None


def _validated_plan(inst: dict, answer: object) -> tuple[list[list[int]] | None, str]:
    if not isinstance(answer, list):
        return None, "answer must be a JSON list"
    if not answer:
        return None, "answer is empty"
    if len(answer) != inst["n"] // 3:
        return None, "plan has the wrong number of road trips"
    if any(not isinstance(trip, list) or len(trip) != 3 for trip in answer):
        return None, "every road trip must contain exactly three teams"

    flat: list[int] = []
    for trip in answer:
        for team in trip:
            if isinstance(team, bool) or not isinstance(team, int):
                return None, "team labels must be integers"
            if team < 0 or team >= inst["n"]:
                return None, "team label is outside 0..n-1"
            flat.append(team)
    if len(set(flat)) != len(flat):
        return None, "a team label appears more than once"
    if set(flat) != set(range(inst["n"])):
        return None, "the plan does not cover every away team"
    return [[int(team) for team in trip] for trip in answer], "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid road-trip witness without reading inst['answer']."""

    plan, reason = _validated_plan(inst, answer)
    if plan is None:
        return False, reason
    total = _plan_cost(inst, plan)
    if total > inst["target"]:
        return False, f"travel {total} exceeds target {inst['target']}"
    return True, "ok"


def _fast_valid(inst: dict, answer: object) -> bool:
    plan, _reason = _validated_plan(inst, answer)
    return plan is not None and _plan_cost(inst, plan) <= inst["target"]


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample road plans after quotienting obvious symmetries."""

    labels = list(range(inst["n"]))
    rng.shuffle(labels)
    trips = []
    for start in range(0, inst["n"], 3):
        trips.append(list(_canonical_trip(labels[start:start + 3])))
    trips.sort()
    return trips


def search_space(inst: dict) -> int | None:
    n = inst["n"]
    groups = n // 3
    return math.factorial(n) // (math.factorial(groups) * (2 ** groups))


def enumerate_all(inst: dict) -> int | None:
    """Count canonical valid road plans when the quotient space is small."""

    if search_space(inst) > _ENUMERATION_CAP:
        return None
    seen: set[tuple[tuple[int, int, int], ...]] = set()
    valid = 0
    for ordering in itertools.permutations(range(inst["n"])):
        plan = tuple(sorted(
            _canonical_trip(ordering[start:start + 3])
            for start in range(0, inst["n"], 3)
        ))
        if plan in seen:
            continue
        seen.add(plan)
        valid += int(_fast_valid(inst, [list(row) for row in plan]))
    return valid


def canonical_key(inst: dict) -> str:
    """A strong cheap invariant under every permutation of away labels.

    The home venue is distinguished. Full weighted-graph canonization is not
    attempted; sorted weighted row profiles are the strongest inexpensive
    invariant used here, and random edge weights make collisions unlikely.
    """

    matrix = inst["distance"]
    profiles = sorted(
        (matrix[0][idx], tuple(sorted(matrix[idx])))
        for idx in range(1, inst["n"] + 1)
    )
    payload = {
        "n": inst["n"],
        "target": inst["target"],
        "home_row": sorted(matrix[0][1:]),
        "away_profiles": profiles,
    }
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Crowd the objective at fixed answer length, then double the venue set."""

    current = int(params.get("n", DIFFICULTY["hard"]["n"]))
    harder = {key: value for key, value in params.items() if key != "_preset"}
    scale = max(1, int(harder.get("weight_scale", 4096)))
    if scale < 1_000_000:
        harder["weight_scale"] = min(1_000_000, scale * 8)
        return harder
    if current < 252:
        harder["n"] = 2 * current
        return harder
    return "cap_bound"


def _structural_decode(inst: dict) -> list[list[int]] | None:
    modulus = inst["n"] + 1
    buckets: dict[int, list[int]] = {}
    for team in range(inst["n"]):
        residue = inst["distance"][0][team + 1] % modulus
        buckets.setdefault(residue, []).append(team)
    if len(buckets) != inst["n"] // 3 or any(len(row) != 3 for row in buckets.values()):
        return None
    return _canonical_plan([sorted(row) for row in buckets.values()])


def _intended_operation_bound(inst: dict) -> int:
    # One modular reduction per away venue; grouping is symbolic bookkeeping.
    return inst["n"]


def _reference_profile_scan(inst: dict) -> tuple[list[list[int]] | None, dict[str, int]]:
    """Recover sibling leaves using complete constant row-difference tests."""

    n = inst["n"]
    matrix = inst["distance"]
    neighbours = [set() for _ in range(n)]
    operations = 0
    pair_tests = 0
    for i in range(n):
        ii = i + 1
        for j in range(i + 1, n):
            jj = j + 1
            pair_tests += 1
            deltas = set()
            for k in range(n):
                if k == i or k == j:
                    continue
                kk = k + 1
                deltas.add(matrix[ii][kk] - matrix[jj][kk])
                operations += 1
            if len(deltas) == 1:
                neighbours[i].add(j)
                neighbours[j].add(i)

    unseen = set(range(n))
    groups: list[list[int]] = []
    while unseen:
        root = min(unseen)
        group = {root} | (neighbours[root] & unseen)
        if len(group) != 3:
            return None, {"operations": operations, "pair_tests": pair_tests}
        groups.append(sorted(group))
        unseen -= group
    return _canonical_plan(groups), {
        "operations": operations,
        "pair_tests": pair_tests,
    }


def _home_sorted_plan(inst: dict) -> list[list[int]]:
    order = sorted(
        range(inst["n"]),
        key=lambda team: (inst["distance"][0][team + 1], team),
    )
    return _canonical_plan([
        order[start:start + 3] for start in range(0, inst["n"], 3)
    ])


def _consecutive_label_plan(inst: dict) -> list[list[int]]:
    return [list(range(start, start + 3)) for start in range(0, inst["n"], 3)]


def _greedy_short_edge_plan(inst: dict) -> list[list[int]]:
    """Repeatedly extend the shortest remaining edge by its cheapest third."""

    matrix = inst["distance"]
    remaining = set(range(inst["n"]))
    plan: list[list[int]] = []
    while remaining:
        ordered = sorted(remaining)
        _length, a, b = min(
            (matrix[i + 1][j + 1], i, j)
            for pos, i in enumerate(ordered)
            for j in ordered[pos + 1:]
        )
        c = min(
            remaining - {a, b},
            key=lambda team: min(
                matrix[0][a + 1]
                + matrix[a + 1][b + 1]
                + matrix[b + 1][team + 1]
                + matrix[team + 1][0],
                matrix[0][a + 1]
                + matrix[a + 1][team + 1]
                + matrix[team + 1][b + 1]
                + matrix[b + 1][0],
            ),
        )
        plan.append([a, b, c])
        remaining -= {a, b, c}
    return _canonical_plan(plan)


def _attack_candidates(inst: dict, rng: random.Random) -> dict[str, object]:
    return {
        "outlier_sort_home_distance": _home_sorted_plan(inst),
        "greedy_shortest_remaining_edge": _greedy_short_edge_plan(inst),
        "by_hand_consecutive_labels": _consecutive_label_plan(inst),
        "random_restart_256": [random_candidate(inst, rng) for _ in range(256)],
    }


def _attack_succeeds(inst: dict, candidate: object) -> bool:
    if (
        isinstance(candidate, list)
        and candidate
        and isinstance(candidate[0], list)
        and candidate[0]
        and isinstance(candidate[0][0], list)
    ):
        return any(_fast_valid(inst, item) for item in candidate)
    return _fast_valid(inst, candidate)


def _permuted_instance(inst: dict, rng: random.Random) -> tuple[dict, list[list[int]]]:
    """Relabel away venues and carry the planted road plan."""

    n = inst["n"]
    new_to_old = list(range(n))
    rng.shuffle(new_to_old)
    old_to_new = [0] * n
    for new, old in enumerate(new_to_old):
        old_to_new[old] = new

    old_matrix = inst["distance"]
    transformed = dict(inst)
    transformed["distance"] = [[0] * (n + 1) for _ in range(n + 1)]
    index_map = [0] + [old + 1 for old in new_to_old]
    for i in range(n + 1):
        for j in range(n + 1):
            transformed["distance"][i][j] = old_matrix[index_map[i]][index_map[j]]
    carried = [
        [old_to_new[team] for team in trip] for trip in inst["answer"]
    ]
    transformed["answer"] = _canonical_plan(carried)
    return transformed, transformed["answer"]


def _atom_count(value: object) -> int:
    if isinstance(value, dict):
        return sum(_atom_count(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atom_count(item) for item in value)
    return 1


def selftest() -> dict:
    """Run mandatory gates G1--G9 and return a JSON-native report."""

    report: dict[str, Any] = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    g1_failures: list[str] = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=314159, **shipping_params)
    planted = json.loads(json.dumps(ship["answer"]))

    dropped = json.loads(json.dumps(planted))
    dropped[0] = dropped[0][:-1]
    swapped = json.loads(json.dumps(planted))
    swapped[0][0], swapped[1][0] = swapped[1][0], swapped[0][0]
    duplicated = json.loads(json.dumps(planted))
    duplicated[0][0] = duplicated[1][0]
    out_of_range = json.loads(json.dumps(planted))
    out_of_range[0][0] = ship["n"]
    corruptions = {
        "drop_one_element": dropped,
        "swap_members_between_trips": swapped,
        "duplicate_one": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    cases: dict[str, dict[str, Any]] = {}
    reasons: list[str] = []
    for name, candidate in corruptions.items():
        ok, reason = verify(ship, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in cases.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "cases": cases,
    }

    model_style = (
        "The triplets cover every venue and meet the exact bound.\n"
        "```json\n<answer>" + json.dumps(planted) + "</answer>\n```\n"
        "The tagged value is my final road plan."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged answer") is None,
        "parsed_matches": parsed == planted,
    }

    samples = 200_000
    sample_rng = random.Random(8_675_309)
    hits = 0
    for _ in range(samples):
        hits += int(_fast_valid(ship, random_candidate(ship, sample_rng)))
    observed = hits / samples
    unordered_partitions = (
        math.factorial(ship["n"])
        // ((math.factorial(3) ** (ship["n"] // 3))
            * math.factorial(ship["n"] // 3))
    )
    exact_density = 1.0 / unordered_partitions
    exact_valid_canonical = 3 ** (ship["n"] // 3)
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6 and exact_density < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": observed,
        "exact_probability_by_tree_identity": exact_density,
        "candidate_space": search_space(ship),
        "exact_valid_canonical_road_plans": exact_valid_canonical,
        "sampler": (
            "uniform ordered trip plans after quotienting trip permutation "
            "and trip reversal"
        ),
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    attack_names = [
        "outlier_sort_home_distance",
        "greedy_shortest_remaining_edge",
        "by_hand_consecutive_labels",
        "random_restart_256",
    ]
    attack_results = {
        name: {"successes": 0, "attempts": 8} for name in attack_names
    }
    reference_successes = 0
    reference_times: list[float] = []
    reference_operations: list[int] = []
    reference_pair_tests: list[int] = []
    for seed in range(8):
        trial = make_instance(seed=12_000 + seed, **shipping_params)
        candidates = _attack_candidates(trial, random.Random(700_000 + seed))
        for name in attack_names:
            attack_results[name]["successes"] += int(
                _attack_succeeds(trial, candidates[name])
            )
        started = time.perf_counter()
        reference_answer, counts = _reference_profile_scan(trial)
        elapsed = time.perf_counter() - started
        reference_times.append(elapsed)
        reference_operations.append(counts["operations"])
        reference_pair_tests.append(counts["pair_tests"])
        reference_successes += int(
            reference_answer is not None and verify(trial, reference_answer)[0]
        )

    reference = {
        "name": "complete constant distance-row profile scan",
        "paper_location": "Section 5 ordered three-game road-trip packing",
        "complexity": "O(n^3) exact integer subtractions and O(n^2) storage",
        "wall_clock_sec_mean": sum(reference_times) / len(reference_times),
        "wall_clock_sec_max": max(reference_times),
        "operations_mean": sum(reference_operations) / len(reference_operations),
        "operations_max": max(reference_operations),
        "pair_tests_mean": sum(reference_pair_tests) / len(reference_pair_tests),
        "solves": f"{reference_successes}/8, as expected",
    }
    all_attacks_failed = all(
        row["successes"] == 0 and row["attempts"] >= 8
        for row in attack_results.values()
    )
    report["G5_density_and_baseline"] = {
        "pass": exact_density < 1e-6
        and demo_count == 3 ** (demo["n"] // 3)
        and reference_successes == 8
        and reference["operations_mean"] >= 100_000,
        "shipping_density_hits": hits,
        "shipping_density_total": samples,
        "shipping_observed_fraction": observed,
        "shipping_exact_fraction_by_tree_identity": exact_density,
        "shipping_structure_aware_space": search_space(ship),
        "shipping_exact_valid_canonical_plans": exact_valid_canonical,
        "demo_valid_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "baseline_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
        "baseline_wall_clock_sec_max": reference["wall_clock_sec_max"],
        "baseline_operations_mean": reference["operations_mean"],
        "baseline_operations_max": reference["operations_max"],
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": reference,
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * doubled_params["n"]
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and search_space(doubled) > search_space(ship)
        and _atom_count(doubled["answer"]) > _atom_count(ship["answer"]),
        "shipping_n": ship["n"],
        "doubled_n": doubled["n"],
        "shipping_candidate_space": search_space(ship),
        "doubled_candidate_space": search_space(doubled),
        "doubled_verify_reason": doubled_reason,
        "answer_elements_shipping": _atom_count(ship["answer"]),
        "answer_elements_doubled": _atom_count(doubled["answer"]),
    }

    invariant_checks = 0
    carried_witness_checks = 0
    composed_checks = 0
    unrelated_keys: list[str] = []
    g8_failures: list[str] = []
    for seed in range(20):
        trial = make_instance(seed=20_000 + seed, **DIFFICULTY["medium"])
        key = canonical_key(trial)
        unrelated_keys.append(key)

        permuted, carried = _permuted_instance(
            trial, random.Random(30_000 + seed)
        )
        if canonical_key(permuted) == key:
            invariant_checks += 1
        else:
            g8_failures.append(f"away-team permutation changed key at seed {seed}")
        if verify(permuted, carried)[0]:
            carried_witness_checks += 1
        else:
            g8_failures.append(f"carried witness failed at seed {seed}")

        twice, carried_twice = _permuted_instance(
            permuted, random.Random(40_000 + seed)
        )
        if canonical_key(twice) == key and verify(twice, carried_twice)[0]:
            composed_checks += 1
        else:
            g8_failures.append(f"composed permutation failed at seed {seed}")

    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "real_transformation_checks": carried_witness_checks,
        "composed_transformation_checks": composed_checks,
        "unrelated_distinct": distinct,
        "unrelated_attempts": 20,
        "transformations": [
            "arbitrary permutation of all away-team labels with carried plan",
            "composition of two independent away-team permutations",
        ],
        "key_limit": (
            "sorted weighted-row profiles; full weighted-graph canonization "
            "is not attempted"
        ),
        "failures": g8_failures,
    }

    answer_blob = json.dumps(ship["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    arms = {
        name: {
            "solved": int(G9_MEASUREMENTS[name]["solved"]),
            "attempts": int(G9_MEASUREMENTS[name]["attempts"]),
        }
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else None
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else None
    )
    compact_answer = _structural_decode(ship)
    intended_operations = _intended_operation_bound(ship)
    within_caps = (
        answer_chars <= 2_000
        and _atom_count(ship["answer"]) <= 256
        and intended_operations <= 300
        and answer_tokens <= PROBLEM_PROFILE["max_answer_tokens"]
        and compact_answer is not None
        and verify(ship, compact_answer)[0]
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": _atom_count(ship["answer"]),
        "intended_route_operations": intended_operations,
        "compact_route_verifies": compact_answer is not None
        and verify(ship, compact_answer)[0],
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    report["certificate_language"] = CERTIFICATE_LANGUAGE
    report["problem_profile"] = PROBLEM_PROFILE
    gates = [name for name in report if name.startswith("G")]
    report["all_passed"] = all(bool(report[name].get("pass")) for name in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
