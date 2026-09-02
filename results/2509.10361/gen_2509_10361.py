"""Verified inverse generator for Load-and-Gas CVRP from arXiv:2509.10361.

The instances are the weighted-star construction in Section 4.3 of
"Parameterized Complexity of Vehicle Routing".  A witness partitions the
clients into three-client routes.  Verification merely replays those routes on
the star and checks integer load and distance bounds.

Standard library only; importing this module has no side effects.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import re
from typing import Any


DIFFICULTY = {
    # Keeping b/n fixed makes the number of exact-sum decoy triples grow with n.
    # Thus larger instances have both a deeper matching and more crowding.
    "medium": {"n": 48, "b_factor": 12},
    "hard": {"n": 72, "b_factor": 12},
}

SHIPPING_DIFFICULTY = "medium"


NOTES = r"""
Paper basis.  Section 2.2 defines Load-and-Gas-Capacitated Vehicle Routing:
the witness is a set of closed depot walks plus an assignment of clients to
walks; load is charged by the assignment, and both every route and the whole
routing have integer weight bounds.  Section 4.3's theorem stating that
LoadGasCVRP is strongly NP-hard even on stars with one depot, constant load
capacity, and unit demands (source label
``thm:loadgascvrp_np_const_demand``) reduces strongly NP-complete Numerical
3-Dimensional Matching to exactly the weighted-star restriction used here.
It proves strong NP-hardness even on treewidth-one stars with one depot,
unit demands, and constant load 3.  The low bits 1, 4, and 16 in the edge
weights force every tight three-client route to contain one client of each
type.

Easy regimes avoided.  Section 4 first gives an |C|^{O(|C|)} algorithm, an FPT
algorithm in k+ell, an FPT algorithm in total weight r when zero-weight edges
are absent, and an XP algorithm in treewidth+ell+g.  Here |C|=3n, k=n,
g=Theta(n), and r=Theta(n^2), so every one of those nonconstant parameters
grows.  Only treewidth=1, |D|=1, ell=3, and unit demand remain fixed, precisely
the para-NP-hard regime of Section 4.3.

Inverse generation and attacks.  Client types and a uniformly shuffled
perfect X-Y-Z matching are sampled first.  Each matched row then receives an
exchangeable random positive composition of b; all 3n values are required to
be distinct.  Randomly permuting the three parts makes X, Y, and Z clients have
the same marginal value distribution.  Presentation order and numeric vertex
IDs are independently shuffled.  Accidental exact-sum triples are the decoys:
they obey exactly the same visible arithmetic relation as planted triples.
The outlier attack aligns clients by value rank, the deterministic greedy
attack repeatedly commits the most constrained X client, and random restart
uses randomized most-constrained-first commitments.  selftest requires all
three to fail on at least eight independent shipping instances.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 1_000_000
_TYPE_TAG = {"X": 1, "Y": 4, "Z": 16}
_TYPES = ("X", "Y", "Z")


def _validate_parameters(n: int, b_factor: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 4:
        raise ValueError("n must be an integer at least 4")
    if isinstance(b_factor, bool) or not isinstance(b_factor, int) or b_factor < 12:
        raise ValueError("b_factor must be an integer at least 12")


def _fresh_compositions(
    count: int, target: int, rng: random.Random
) -> list[tuple[int, int, int]]:
    """Draw exchangeable, globally distinct positive 3-compositions."""

    lower = max(1, target // 8)
    used: set[int] = set()
    rows: list[tuple[int, int, int]] = []
    attempts = 0
    limit = max(100_000, count * 20_000)
    while len(rows) < count:
        attempts += 1
        if attempts > limit:
            # This should be unreachable for b_factor >= 12.  Failing loudly is
            # preferable to silently changing the requested distribution.
            raise RuntimeError("could not draw enough distinct compositions")
        a = rng.randrange(lower, target - 2 * lower + 1)
        b = rng.randrange(lower, target - a - lower + 1)
        parts = [a, b, target - a - b]
        if len(set(parts)) != 3 or any(value in used for value in parts):
            continue
        rng.shuffle(parts)
        row = (parts[0], parts[1], parts[2])
        rows.append(row)
        used.update(row)
    return rows


def make_instance(n: int, seed: int = 0, *, b_factor: int = 12) -> dict:
    """Plant a routing first, then construct a weighted star around it.

    ``n`` is both the number of vehicles and the number of three-client routes;
    the graph has ``3*n + 1`` vertices.  At fixed ``b_factor``, increasing n
    increases the matching depth and the expected number of accidental
    exact-sum triples.
    """

    _validate_parameters(n, b_factor)
    rng = random.Random(seed)

    # G: choose types and the hidden perfect matching before drawing any values.
    client_ids = list(range(1, 3 * n + 1))
    rng.shuffle(client_ids)
    x_ids = client_ids[:n]
    y_ids = client_ids[n : 2 * n]
    z_ids = client_ids[2 * n :]
    rng.shuffle(y_ids)
    rng.shuffle(z_ids)
    planted_rows = [list(row) for row in zip(x_ids, y_ids, z_ids)]

    target = b_factor * n
    compositions = _fresh_compositions(n, target, rng)
    type_by_id = {
        **{client_id: "X" for client_id in x_ids},
        **{client_id: "Y" for client_id in y_ids},
        **{client_id: "Z" for client_id in z_ids},
    }
    value_by_id: dict[int, int] = {}
    for row, parts in zip(planted_rows, compositions):
        for client_id, value in zip(row, parts):
            value_by_id[client_id] = value

    clients = []
    for client_id in client_ids:
        client_type = type_by_id[client_id]
        value = value_by_id[client_id]
        clients.append(
            {
                "id": client_id,
                "type": client_type,
                "value": value,
                "demand": 1,
                "edge_weight": 64 * value + _TYPE_TAG[client_type],
            }
        )
    rng.shuffle(clients)

    gas_capacity = 2 * (64 * target + 21)
    total_budget = n * gas_capacity
    answer = sorted(planted_rows, key=lambda row: row[0])

    # Every planted route is 0-a-0-b-0-c-0 and is exactly tight.
    by_id = {client["id"]: client for client in clients}
    assert all(
        2 * sum(by_id[v]["edge_weight"] for v in row) == gas_capacity
        for row in answer
    )
    assert 2 * sum(client["edge_weight"] for client in clients) == total_budget

    return {
        "family": "Load-and-Gas-Capacitated Vehicle Routing on a weighted star",
        "n": n,
        "depot": 0,
        "clients": clients,
        "vehicle_limit": n,
        "load_capacity": 3,
        "gas_capacity": gas_capacity,
        "total_budget": total_budget,
        "target_sum": target,
        "b_factor": b_factor,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Return the complete solver-facing problem statement."""

    by_type = {
        client_type: sorted(
            (client for client in inst["clients"] if client["type"] == client_type),
            key=lambda client: client["id"],
        )
        for client_type in _TYPES
    }
    data_lines = []
    for client_type in _TYPES:
        entries = " ".join(
            f'{c["id"]}:{c["value"]}:{c["edge_weight"]}'
            for c in by_type[client_type]
        )
        data_lines.append(f"{client_type} {entries}")
    data = "\n".join(data_lines)
    example_ids = [by_type[t][0]["id"] for t in _TYPES]

    return f"""LOAD-AND-GAS-CAPACITATED VEHICLE ROUTING ON A STAR

The input is an undirected weighted star.  Its centre is the sole depot,
vertex {inst["depot"]}.  Every other listed vertex is a client and has exactly
one edge, joining it to the depot, with the listed integer EDGE_WEIGHT.  Every
client has demand 1.

A vehicle route is a closed walk that starts and ends at the depot.  A client
is served by the route to which it is assigned.  The load of a route is the
sum of demands assigned to it, and the route weight is the sum of traversed
edge weights, counting every traversal.  At most {inst["vehicle_limit"]}
routes may be used.  Each route has load at most {inst["load_capacity"]} and
weight at most {inst["gas_capacity"]}.  The sum of all route weights must be at
most {inst["total_budget"]}.

Find a routing that serves every one of the {3 * inst["n"]} clients.  For this
star and these tight bounds, a witness can and must be written as exactly
{inst["n"]} disjoint groups of three clients.  Each group must contain exactly
one client of displayed type X, one of type Y, and one of type Z.  A group
[a,b,c] denotes the closed route
{inst["depot"]}-a-{inst["depot"]}-b-{inst["depot"]}-c-{inst["depot"]}; the order
inside a group and the order of groups do not matter.  Every client ID must
occur exactly once.  IDs are arbitrary integers: use them exactly as listed;
there is no positional or 0/1-index convention to infer.

The VALUE column is a derived aid.  Edge weights are encoded as 64*VALUE+tag,
where the tags for X,Y,Z are 1,4,16.  Consequently a valid group has one of
each type and its three VALUEs sum exactly to {inst["target_sum"]}.  The
checker nevertheless replays the star routes and recomputes all load and
weight bounds.

CLIENT DATA
Each entry is ID:VALUE:EDGE_WEIGHT.  Entries after the initial type letter may
be reordered without changing the instance.
{data}

Give your final answer inside <answer></answer> tags, as one JSON array of
exactly {inst["n"]} three-integer arrays.  Each inner array is one route group;
do not include the depot and do not repeat a client ID.
Format example only: <answer>[[{example_ids[0]}, {example_ids[1]}, {example_ids[2]}]]</answer>
Output nothing else inside the tags."""


def _strip_code_fence(body: str) -> str:
    body = body.strip()
    if not (body.startswith("```") and body.endswith("```")):
        return body
    lines = body.splitlines()
    if len(lines) < 2:
        return body
    return "\n".join(lines[1:-1]).strip()


def parse_answer(text: str) -> object | None:
    """Extract the last syntactically valid tagged JSON route array."""

    if not isinstance(text, str):
        return None
    for raw in reversed(_ANSWER_RE.findall(text)):
        body = _strip_code_fence(raw)
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            continue
        if not isinstance(value, list):
            continue
        syntactic = True
        for group in value:
            if not isinstance(group, list) or any(
                not isinstance(x, int) or isinstance(x, bool) for x in group
            ):
                syntactic = False
                break
        if syntactic:
            return value
    return None


def _client_map(inst: dict) -> dict[int, dict]:
    return {client["id"]: client for client in inst["clients"]}


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Replay the proposed routes.  The planted ``inst['answer']`` is ignored."""

    if not isinstance(answer, list):
        return False, "answer must be a JSON array of route groups"
    if not answer:
        return False, "answer is empty"
    if any(not isinstance(group, list) for group in answer):
        return False, "every route group must be a JSON array"
    if any(len(group) != 3 for group in answer):
        return False, "each route group must contain exactly 3 client IDs"
    if any(
        not isinstance(client_id, int) or isinstance(client_id, bool)
        for group in answer
        for client_id in group
    ):
        return False, "every client ID must be an integer"

    clients = _client_map(inst)
    flat = [client_id for group in answer for client_id in group]
    unknown = [client_id for client_id in flat if client_id not in clients]
    if unknown:
        return False, f"unknown client ID: {unknown[0]}"
    if len(answer) != inst["vehicle_limit"]:
        return False, f'expected exactly {inst["vehicle_limit"]} route groups'
    if len(set(flat)) != len(flat):
        return False, "each client ID must occur exactly once; a duplicate was found"
    if set(flat) != set(clients):
        return False, "route groups do not cover exactly all clients"

    total_weight = 0
    for route_index, group in enumerate(answer, 1):
        types = {clients[client_id]["type"] for client_id in group}
        if types != set(_TYPES):
            return False, f"route {route_index} must contain one X, one Y, and one Z client"
        load = sum(clients[client_id]["demand"] for client_id in group)
        if load > inst["load_capacity"]:
            return False, f"route {route_index} exceeds the load capacity"
        # On a star, serving each listed leaf and returning traverses its edge
        # once in each direction.
        route_weight = 2 * sum(clients[client_id]["edge_weight"] for client_id in group)
        if route_weight > inst["gas_capacity"]:
            excess = route_weight - inst["gas_capacity"]
            return False, f"route {route_index} exceeds the gas capacity by {excess}"
        total_weight += route_weight

    if total_weight > inst["total_budget"]:
        return False, f"routing exceeds the total weight budget by {total_weight - inst['total_budget']}"
    return True, "ok"


def _ids_by_type(inst: dict) -> dict[str, list[int]]:
    return {
        client_type: sorted(
            client["id"]
            for client in inst["clients"]
            if client["type"] == client_type
        )
        for client_type in _TYPES
    }


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample a type-correct perfect 3-way partition.

    This builds in everything a solver gets for free from the output contract:
    the route count, arity, distinctness, full coverage, and one-of-each-type
    rule.  It does not bias toward the planted matching or toward arithmetically
    compatible triples, since finding a compatible perfect matching is the task.
    """

    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    pools = _ids_by_type(inst)
    xs = pools["X"][:]
    ys = pools["Y"][:]
    zs = pools["Z"][:]
    rng.shuffle(ys)
    rng.shuffle(zs)
    groups = [[x, y, z] for x, y, z in zip(xs, ys, zs)]
    rng.shuffle(groups)
    for group in groups:
        rng.shuffle(group)
    return groups


def search_space(inst: dict) -> int | None:
    """Count normalized type-correct partitions: (n!)^2."""

    n = inst["n"]
    return math.factorial(n) ** 2


def _compatible_pairs(inst: dict) -> tuple[list[int], list[int], list[int], dict[int, list[tuple[int, int]]]]:
    pools = _ids_by_type(inst)
    xs, ys, zs = pools["X"], pools["Y"], pools["Z"]
    clients = _client_map(inst)
    z_by_weight = {clients[z]["edge_weight"]: z for z in zs}
    pairs: dict[int, list[tuple[int, int]]] = {}
    half_gas = inst["gas_capacity"] // 2
    for x in xs:
        choices = []
        for y in ys:
            need = half_gas - clients[x]["edge_weight"] - clients[y]["edge_weight"]
            z = z_by_weight.get(need)
            if z is not None:
                choices.append((y, z))
        pairs[x] = choices
    return xs, ys, zs, pairs


def enumerate_all(inst: dict) -> int | None:
    """Exactly count valid perfect matchings when the naive work is capped."""

    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    xs, ys, zs, pairs = _compatible_pairs(inst)
    y_index = {value: i for i, value in enumerate(ys)}
    z_index = {value: i for i, value in enumerate(zs)}
    memo: dict[tuple[int, int, int], int] = {}

    def count(i: int, used_y: int, used_z: int) -> int:
        if i == len(xs):
            return 1
        key = (i, used_y, used_z)
        if key in memo:
            return memo[key]
        total = 0
        for y, z in pairs[xs[i]]:
            y_bit = 1 << y_index[y]
            z_bit = 1 << z_index[z]
            if not (used_y & y_bit or used_z & z_bit):
                total += count(i + 1, used_y | y_bit, used_z | z_bit)
        memo[key] = total
        return total

    return count(0, 0, 0)


def canonical_key(inst: dict) -> str:
    """Canonical key for weighted-star isomorphism, ignoring all vertex IDs."""

    client_rows = sorted(
        (
            client["edge_weight"],
            client["demand"],
            client["type"],
            client["value"],
        )
        for client in inst["clients"]
    )
    canonical = {
        "topology": "one-depot-star",
        "clients": client_rows,
        "vehicle_limit": inst["vehicle_limit"],
        "load_capacity": inst["load_capacity"],
        "gas_capacity": inst["gas_capacity"],
        "total_budget": inst["total_budget"],
    }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return "loadgas-star-v1:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | None:
    """Increase matching depth and crowding, up to a renderer-safe ceiling."""

    n = params.get("n")
    b_factor = params.get("b_factor", 12)
    if isinstance(n, bool) or not isinstance(n, int) or n >= 180:
        return None
    return {"n": max(n + 1, math.ceil(n * 4 / 3)), "b_factor": b_factor}


# --- deliberately cheap attacks used by selftest ---------------------------


def _complete_partial(
    chosen: list[list[int]], remaining_x: set[int], remaining_y: set[int], remaining_z: set[int]
) -> list[list[int]]:
    tail = [list(row) for row in zip(sorted(remaining_x), sorted(remaining_y), sorted(remaining_z))]
    return chosen + tail


def _attack_outlier(inst: dict) -> list[list[int]]:
    """Align clients using only the per-client magnitude statistic."""

    clients = _client_map(inst)
    pools = _ids_by_type(inst)
    xs = sorted(pools["X"], key=lambda v: (clients[v]["value"], v))
    ys = sorted(pools["Y"], key=lambda v: (clients[v]["value"], v))
    zs = sorted(pools["Z"], key=lambda v: (-clients[v]["value"], v))
    return [[x, y, z] for x, y, z in zip(xs, ys, zs)]


def _attack_greedy(inst: dict) -> list[list[int]]:
    """Most-constrained-first exact-triple commitments, without backtracking."""

    xs, ys, zs, pairs = _compatible_pairs(inst)
    remaining_x, remaining_y, remaining_z = set(xs), set(ys), set(zs)
    chosen: list[list[int]] = []
    while remaining_x:
        options = []
        for x in remaining_x:
            available = [(y, z) for y, z in pairs[x] if y in remaining_y and z in remaining_z]
            options.append((len(available), x, available))
        _, x, available = min(options, key=lambda row: (row[0], row[1]))
        if not available:
            return _complete_partial(chosen, remaining_x, remaining_y, remaining_z)
        y, z = min(available)
        chosen.append([x, y, z])
        remaining_x.remove(x)
        remaining_y.remove(y)
        remaining_z.remove(z)
    return chosen


def _attack_random_restart(inst: dict, rng: random.Random, restarts: int = 64) -> list[list[int]]:
    """Randomized greedy exact triples with MRV, but no backtracking."""

    xs, ys, zs, pairs = _compatible_pairs(inst)
    best: list[list[int]] = []
    best_remainder = (set(xs), set(ys), set(zs))
    for _ in range(restarts):
        remaining_x, remaining_y, remaining_z = set(xs), set(ys), set(zs)
        chosen: list[list[int]] = []
        while remaining_x:
            options = []
            for x in remaining_x:
                available = [(y, z) for y, z in pairs[x] if y in remaining_y and z in remaining_z]
                options.append((len(available), x, available))
            minimum = min(row[0] for row in options)
            tied = [row for row in options if row[0] == minimum]
            _, x, available = rng.choice(tied)
            if not available:
                break
            y, z = rng.choice(available)
            chosen.append([x, y, z])
            remaining_x.remove(x)
            remaining_y.remove(y)
            remaining_z.remove(z)
        if not remaining_x:
            return chosen
        if len(chosen) > len(best):
            best = chosen
            best_remainder = (remaining_x, remaining_y, remaining_z)
    return _complete_partial(best, *best_remainder)


def _relabel_and_reorder(inst: dict, rng: random.Random, *, relabel: bool, reorder: bool) -> dict:
    transformed = copy.deepcopy(inst)
    all_ids = [inst["depot"]] + [client["id"] for client in inst["clients"]]
    mapping = {value: value for value in all_ids}
    if relabel:
        new_ids = all_ids[:]
        rng.shuffle(new_ids)
        mapping = dict(zip(all_ids, new_ids))
        transformed["depot"] = mapping[inst["depot"]]
        for client in transformed["clients"]:
            client["id"] = mapping[client["id"]]
        transformed["answer"] = [
            [mapping[client_id] for client_id in group]
            for group in transformed["answer"]
        ]
    if reorder:
        rng.shuffle(transformed["clients"])
    return transformed


def selftest() -> dict:
    """Run gates G1--G8 and return a JSON-serializable evidence dictionary."""

    report: dict[str, Any] = {}

    # G1: every named preset over several independent seeds.
    g1_checks = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 29):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_checks += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checks": g1_checks,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping)
    planted = copy.deepcopy(inst["answer"])

    # G2: five requested corruptions, designed to reach five distinct checks.
    corruptions: dict[str, object] = {}
    dropped = copy.deepcopy(planted)
    dropped[0] = dropped[0][:-1]
    corruptions["drop_one_element"] = dropped
    swapped = copy.deepcopy(planted)
    swapped[0][0], swapped[1][0] = swapped[1][0], swapped[0][0]
    corruptions["swap_same_type_between_routes"] = swapped
    duplicated = copy.deepcopy(planted)
    duplicated[0][0] = duplicated[1][0]
    corruptions["duplicate_client"] = duplicated
    corruptions["empty"] = []
    out_of_range = copy.deepcopy(planted)
    out_of_range[0][0] = max(_client_map(inst)) + 10_000
    corruptions["out_of_range"] = out_of_range
    corruption_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        if not ok:
            reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": len(reasons) == 5 and len(set(reasons)) == 5,
        "rejected": len(reasons),
        "distinct_reasons": len(set(reasons)),
        "cases": corruption_results,
    }

    # G3: realistic surrounding prose and a fenced JSON body.
    response = (
        "I checked all route totals.\n\n<answer>\n```json\n"
        + json.dumps(inst["answer"])
        + "\n```\n</answer>\nThe tagged block is my final answer."
    )
    parsed = parse_answer(response)
    garbage = [
        "no tags here",
        "<answer>not json</answer>",
        '<answer>{"routes": []}</answer>',
        "<answer></answer>",
    ]
    garbage_none = sum(parse_answer(text) is None for text in garbage)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and garbage_none == len(garbage),
        "model_style_round_trip": parsed == inst["answer"],
        "garbage_returned_none": f"{garbage_none}/{len(garbage)}",
    }

    # G4: uniform over normalized, type-correct perfect partitions.
    guess_rng = random.Random(0x250910361)
    trials = 200_000
    hits = 0
    for _ in range(trials):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    rate = hits / trials
    report["G4_guess_resistance"] = {
        "pass": trials >= 200_000 and rate < 1e-6,
        "hits": hits,
        "total": trials,
        "empirical_probability": rate,
        "prior": "uniform over all type-correct perfect X-Y-Z partitions",
        "naive_structural_space": search_space(inst),
    }

    # G5: an exactly enumerable probe from the same construction.
    probe = make_instance(n=6, seed=271828, b_factor=20)
    probe_space = search_space(probe)
    probe_solutions = enumerate_all(probe)
    fraction = None if probe_solutions is None else probe_solutions / probe_space
    report["G5_sparse"] = {
        "pass": probe_solutions is not None and probe_solutions > 0 and fraction < 0.01,
        "probe_n": 6,
        "valid_answers": probe_solutions,
        "candidate_space": probe_space,
        "fraction": fraction,
    }

    # G6: attacks know the public construction but never receive the plant.
    attack_seeds = list(range(800, 808))
    attack_hits = {"value_rank_outlier": 0, "mrv_greedy": 0, "random_restart_64": 0}
    attack_reasons: dict[str, list[str]] = {name: [] for name in attack_hits}
    for seed in attack_seeds:
        attack_inst = make_instance(seed=seed, **shipping)
        candidates = {
            "value_rank_outlier": _attack_outlier(attack_inst),
            "mrv_greedy": _attack_greedy(attack_inst),
            "random_restart_64": _attack_random_restart(
                attack_inst, random.Random(seed ^ 0xA5A5A5A5), 64
            ),
        }
        for name, candidate in candidates.items():
            ok, reason = verify(attack_inst, candidate)
            attack_hits[name] += int(ok)
            attack_reasons[name].append(reason)
    report["G6_adversary_panel"] = {
        "pass": all(hits == 0 for hits in attack_hits.values()),
        "seeds": len(attack_seeds),
        "attacks": {
            name: {
                "solved": attack_hits[name],
                "failed": len(attack_seeds) - attack_hits[name],
                "sample_failure_reason": next(
                    (reason for reason in attack_reasons[name] if reason != "ok"), None
                ),
            }
            for name in attack_hits
        },
    }

    # G7: double the size parameter; the structural space strictly increases.
    doubled_params = dict(shipping)
    doubled_params["n"] = shipping["n"] * 2
    doubled = make_instance(seed=1234567, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst),
        "base_n": shipping["n"],
        "doubled_n": doubled_params["n"],
        "doubled_clients": len(doubled["clients"]),
        "doubled_planted_reason": doubled_reason,
        "base_space": search_space(inst),
        "doubled_space": search_space(doubled),
    }

    # G8: vertex relabeling, input reordering, and their composition.
    invariance_checks = 0
    witness_checks = 0
    g8_failures = []
    for seed in range(20):
        original = make_instance(seed=10_000 + seed, **shipping)
        key = canonical_key(original)
        for transform_name, relabel, reorder in (
            ("relabel", True, False),
            ("reorder", False, True),
            ("relabel_then_reorder", True, True),
        ):
            transformed = _relabel_and_reorder(
                original,
                random.Random(90_000 + 10 * seed + invariance_checks),
                relabel=relabel,
                reorder=reorder,
            )
            invariance_checks += 1
            if canonical_key(transformed) != key:
                g8_failures.append({"seed": seed, "transform": transform_name, "kind": "key"})
            carried_ok, carried_reason = verify(transformed, transformed["answer"])
            witness_checks += 1
            if not carried_ok:
                g8_failures.append(
                    {
                        "seed": seed,
                        "transform": transform_name,
                        "kind": "witness",
                        "reason": carried_reason,
                    }
                )
    unrelated_keys = {
        canonical_key(make_instance(seed=50_000 + seed, **shipping))
        for seed in range(24)
    }
    report["G8_canonical_key"] = {
        "pass": not g8_failures and len(unrelated_keys) == 24,
        "invariance": f"{invariance_checks - sum(f['kind'] == 'key' for f in g8_failures)}/{invariance_checks}",
        "transformed_witnesses": f"{witness_checks - sum(f['kind'] == 'witness' for f in g8_failures)}/{witness_checks}",
        "unrelated_distinct": f"{len(unrelated_keys)}/24",
        "transformations": ["arbitrary vertex relabeling", "client-row reordering", "composition of both"],
        "failures": g8_failures,
    }

    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
