"""Inverse generator for graceful labelings of zillion graphs.

The family is taken from Section 2.2 of arXiv:2306.12713.  A zillion graph
``[k | l_1, ..., l_u]`` is the disjoint union of one k-edge path and cycles
of lengths l_i.  It is graceful when its a+1 vertices can be bijectively
labelled 0,...,a so that its a edge differences are exactly 1,...,a.

Only the Python standard library is used.  Generation is deterministic from
``(n, seed, params)`` and performs no I/O.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import random
import re
from collections import Counter


DIFFICULTY = {
    "demo": {
        "n": 8,
        "min_cycles": 1,
        "min_distinct_cycles": 1,
        "path_min_ratio": 0.1,
        "path_max_ratio": 0.4,
        "build_attempts": 1400,
    },
    "easy": {
        "n": 64,
        "min_cycles": 3,
        "min_distinct_cycles": 3,
        "path_min_ratio": 0.10,
        "path_max_ratio": 0.65,
        "build_attempts": 1400,
    },
    "medium": {
        "n": 96,
        "min_cycles": 3,
        "min_distinct_cycles": 3,
        "path_min_ratio": 0.10,
        "path_max_ratio": 0.60,
        "build_attempts": 1800,
    },
    "hard": {
        "n": 144,
        "min_cycles": 4,
        "min_distinct_cycles": 3,
        "path_min_ratio": 0.08,
        "path_max_ratio": 0.55,
        "build_attempts": 3000,
    },
}

SHIPPING_DIFFICULTY = "easy"


NOTES = r"""
Paper source and definition.  Section 2.2, immediately before Theorem 2.4,
defines [k | L] as one k-edge path disjoint from cycles with length multiset L.
It calls a labeling graceful when the vertices are exactly {0,...,a} and the
signed differences are {+/-1,...,+/-a}, where a=k+sum(L).  The verifier below
uses the equivalent absolute-difference definition.

Easy regime avoided.  Theorem 2.4 gives a direct construction when
k >= B(L), where B(L)=6*b0+7*b1+29.  Every generated instance is checked to
satisfy k < B(L).  We also require at least three cycles and at least three
different cycle lengths.  Thus the generator does not use the one-cycle cases,
the two-cycle Oberwolfach cases discussed in the Introduction, or the theorem's
long-path construction.  No polynomial-time or closed-form method is known for
the resulting general graceful-labeling search problem; this is a hardness
premise, not a proof of NP-hardness, and is recorded as such in README.md.

Inverse generation.  For every difference d in 1,...,a, generation chooses one
edge {s,s+d}.  A randomized exact search enforces degree 1 or 2 at every label.
There are a edges on a+1 nonisolated vertices, so the result necessarily has
exactly one path component and zero or more cycle components.  Only after a
witness with the requested non-easy component profile is sampled are k and L
exposed as the instance.

Attacks.  Plant and decoy input elements do not exist here: the instance is only
an unlabeled component-size multiset.  The outlier attack assigns extreme labels
to the only degree-1 vertices and zigzags the rest; the greedy attack repeatedly
chooses the largest unused edge difference; the restart attack samples uniformly
from structurally legal label permutations.  selftest() measures all three on
eight independent instances.  None is allowed to solve any tested instance.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _graceful_bound(cycle_lengths: list[int]) -> int:
    even = [x for x in cycle_lengths if x % 2 == 0]
    odd = [x for x in cycle_lengths if x % 2 == 1]
    b0 = 2 * len(even) * ((max(even) if even else 0) + 3)
    b1 = (7 ** (len(odd) - 1)) * (2 * max(odd) + 1) if odd else 0
    return 6 * b0 + 7 * b1 + 29


def _choose_difference_edges(a: int, rng: random.Random) -> list[tuple[int, int]]:
    """Choose one edge of every length 1..a with all degrees in {1,2}."""
    degree = [0] * (a + 1)
    starts = [0] * (a + 1)
    remaining = set(range(1, a + 1))

    def visit() -> bool:
        if not remaining:
            return all(degree)

        # Most-constrained difference first.  Random tie breakers and candidate
        # order give many witnesses without making planted labels conspicuous.
        choices = []
        for d in sorted(remaining):
            candidates = [
                s for s in range(a - d + 1)
                if degree[s] < 2 and degree[s + d] < 2
            ]
            if not candidates:
                return False
            choices.append((len(candidates), rng.random(), d, candidates))
        _, _, d, candidates = min(choices)
        rng.shuffle(candidates)
        candidates.sort(
            key=lambda s: (
                -(degree[s] == 0) - (degree[s + d] == 0), rng.random()
            )
        )
        remaining.remove(d)

        for start in candidates:
            end = start + d
            degree[start] += 1
            degree[end] += 1
            starts[d] = start

            # Every still-isolated vertex needs a remaining edge endpoint.
            isolated = sum(value == 0 for value in degree)
            if isolated <= 2 * len(remaining) and visit():
                return True

            degree[start] -= 1
            degree[end] -= 1

        remaining.add(d)
        return False

    if not visit():
        raise RuntimeError("internal graceful-witness search failed")
    return [(starts[d], starts[d] + d) for d in range(1, a + 1)]


def _walk_components(a: int, edges: list[tuple[int, int]]) -> tuple[list[int], list[list[int]]]:
    adjacency = [[] for _ in range(a + 1)]
    for u, v in edges:
        adjacency[u].append(v)
        adjacency[v].append(u)

    endpoints = [v for v in range(a + 1) if len(adjacency[v]) == 1]
    if len(endpoints) != 2 or any(len(nbrs) not in (1, 2) for nbrs in adjacency):
        raise RuntimeError("internal component degree invariant failed")

    path = []
    previous = None
    current = min(endpoints)
    while True:
        path.append(current)
        nxt = [v for v in adjacency[current] if v != previous]
        if not nxt:
            break
        previous, current = current, nxt[0]

    visited = set(path)
    cycles = []
    for start in range(a + 1):
        if start in visited:
            continue
        cycle = [start]
        visited.add(start)
        previous = None
        current = start
        while True:
            options = [v for v in adjacency[current] if v != previous]
            if previous is None:
                next_vertex = min(options)
            else:
                next_vertex = options[0]
            if next_vertex == start:
                break
            cycle.append(next_vertex)
            visited.add(next_vertex)
            previous, current = current, next_vertex
        cycles.append(cycle)

    cycles.sort(key=lambda cycle: (len(cycle), tuple(cycle)))
    return path, cycles


def make_instance(
    n: int,
    seed: int = 0,
    min_cycles: int = 3,
    min_distinct_cycles: int = 3,
    path_min_ratio: float = 0.10,
    path_max_ratio: float = 0.65,
    build_attempts: int = 1400,
) -> dict:
    """Sample a graceful labeling first, then expose only its component type.

    ``n`` is the number of edges (and the largest label/difference).  Larger n
    enlarges both the permutation search space and the all-different constraint.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 8:
        raise ValueError("n must be an integer at least 8")
    if not (0 <= min_cycles <= n // 3):
        raise ValueError("min_cycles is outside the feasible range")
    if not (0 <= min_distinct_cycles <= min_cycles or min_cycles == 0):
        raise ValueError("min_distinct_cycles must be between 0 and min_cycles")
    if not (0.0 <= path_min_ratio <= path_max_ratio <= 1.0):
        raise ValueError("path ratios must satisfy 0 <= min <= max <= 1")
    if build_attempts < 1:
        raise ValueError("build_attempts must be positive")

    rng = random.Random(seed)
    min_path = max(1, math.ceil(n * path_min_ratio))
    max_path = max(min_path, math.floor(n * path_max_ratio))

    for _ in range(build_attempts):
        edges = _choose_difference_edges(n, rng)
        path, cycles = _walk_components(n, edges)
        path_edges = len(path) - 1
        lengths = [len(cycle) for cycle in cycles]
        if len(lengths) < min_cycles:
            continue
        if len(set(lengths)) < min_distinct_cycles:
            continue
        if not (min_path <= path_edges <= max_path):
            continue
        if lengths and path_edges >= _graceful_bound(lengths):
            continue

        # Input ordering is intentionally semantically irrelevant.  Shuffling it
        # exercises the parser/key without changing the underlying graph type.
        input_lengths = list(lengths)
        rng.shuffle(input_lengths)
        answer = {"path": path, "cycles": cycles}
        inst = {
            "family": "graceful_zillion_graph",
            "n": n,
            "path_edges": path_edges,
            "cycle_lengths": input_lengths,
            "answer": answer,
        }
        ok, why = verify(inst, answer)
        if not ok:
            raise RuntimeError(f"internal planted witness failed verification: {why}")
        return inst

    raise RuntimeError(
        f"could not sample the requested component profile in {build_attempts} attempts"
    )


def render(inst: dict) -> str:
    k = inst["path_edges"]
    lengths = inst["cycle_lengths"]
    a = k + sum(lengths)
    return f"""Graceful labeling problem (one path plus disjoint cycles)

The graph has one path with {k} edges (therefore {k + 1} vertices) and
{len(lengths)} vertex-disjoint cycles.  In the input order, the cycle lengths are:
{json.dumps(lengths)}

These components are mutually vertex-disjoint.  A cycle of length ell has ell
vertices and ell edges.  Thus the whole graph has {a + 1} vertices and {a} edges.

Assign every integer label from 0 through {a}, inclusive, to exactly one vertex.
For an edge whose endpoint labels are x and y, its edge difference is |x-y|.
Your labeling is valid exactly when the {a} edge differences are all distinct;
equivalently, they must be precisely 1 through {a}, inclusive.

Represent the path by listing its {k + 1} labels in traversal order.  Represent
each cycle by listing its labels in cyclic order; the last entry is adjacent to
the first.  Reversing the path, rotating or reversing a cycle, and reordering
cycles are allowed.  The multiset of submitted cycle lengths must equal the
input multiset.  Labels are 0-indexed integers, repetitions are forbidden, and
no edges exist between different listed components.

Give your final answer inside <answer></answer> tags, as one JSON object with
exactly the keys "path" and "cycles", each mapped to arrays of integers.
Format-only example: <answer>{{"path":[0,1],"cycles":[[2,3,4]]}}</answer>
The example numbers are not an answer to this instance.  Output nothing else
inside the tags.
"""


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    for body in reversed(matches):
        body = body.strip()
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
        starts = [i for i, char in enumerate(body) if char == "{"]
        for start in starts:
            try:
                value, end = json.JSONDecoder().raw_decode(body[start:])
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if body[start + end :].strip():
                continue
            if isinstance(value, dict):
                return value
    return None


def _edge_differences(path: list[int], cycles: list[list[int]]) -> list[int]:
    differences = [abs(path[i] - path[i + 1]) for i in range(len(path) - 1)]
    for cycle in cycles:
        differences.extend(
            abs(cycle[i] - cycle[(i + 1) % len(cycle)])
            for i in range(len(cycle))
        )
    return differences


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    # Deliberately never access inst["answer"].
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if "path" not in answer:
        return False, "missing path"
    if "cycles" not in answer:
        return False, "missing cycles"
    if set(answer) != {"path", "cycles"}:
        return False, "answer has unexpected keys"

    path = answer["path"]
    cycles = answer["cycles"]
    if not isinstance(path, list):
        return False, "path must be an array"
    if len(path) != inst["path_edges"] + 1:
        return False, "path has wrong length"
    if not isinstance(cycles, list) or any(not isinstance(c, list) for c in cycles):
        return False, "cycles must be an array of arrays"
    if sorted(map(len, cycles)) != sorted(inst["cycle_lengths"]):
        return False, "cycle lengths do not match the instance"

    labels = path + [label for cycle in cycles for label in cycle]
    if any(isinstance(label, bool) or not isinstance(label, int) for label in labels):
        return False, "labels must be integers"
    a = inst["path_edges"] + sum(inst["cycle_lengths"])
    if any(label < 0 or label > a for label in labels):
        return False, f"label out of range 0..{a}"
    if len(set(labels)) != len(labels):
        return False, "labels are not distinct"
    if len(labels) != a + 1:
        return False, "not every label is used"

    differences = _edge_differences(path, cycles)
    if sorted(differences) != list(range(1, a + 1)):
        return False, f"edge differences are not exactly 1..{a}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniform over graph labelings modulo only fixed representation choices.

    Every returned candidate already has the exact component shapes and uses
    every allowed label once.  It therefore models a solver that gets all shape,
    range, cardinality, and bijection constraints for free.
    """
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    a = inst["path_edges"] + sum(inst["cycle_lengths"])
    labels = list(range(a + 1))
    rng.shuffle(labels)
    cut = inst["path_edges"] + 1
    path = labels[:cut]
    cycles = []
    for length in inst["cycle_lengths"]:
        cycles.append(labels[cut : cut + length])
        cut += length
    return {"path": path, "cycles": cycles}


def _representation_symmetry(inst: dict) -> int:
    lengths = inst["cycle_lengths"]
    result = 2  # reverse the nonempty path
    for length in lengths:
        result *= 2 * length  # rotate and reverse each cycle
    for multiplicity in Counter(lengths).values():
        result *= math.factorial(multiplicity)
    return result


def search_space(inst: dict) -> int | None:
    """Number of structurally legal labelings modulo presentation symmetries."""
    a = inst["path_edges"] + sum(inst["cycle_lengths"])
    return math.factorial(a + 1) // _representation_symmetry(inst)


def enumerate_all(inst: dict) -> int | None:
    """Exactly count valid labelings for at most eight edges; otherwise stop."""
    a = inst["path_edges"] + sum(inst["cycle_lengths"])
    if a > 8:
        return None
    path_size = inst["path_edges"] + 1
    valid_representations = 0
    for permutation in itertools.permutations(range(a + 1)):
        path = list(permutation[:path_size])
        cycles = []
        cut = path_size
        for length in inst["cycle_lengths"]:
            cycles.append(list(permutation[cut : cut + length]))
            cut += length
        differences = _edge_differences(path, cycles)
        if sorted(differences) == list(range(1, a + 1)):
            valid_representations += 1
    symmetry = _representation_symmetry(inst)
    if valid_representations % symmetry:
        raise RuntimeError("enumeration symmetry invariant failed")
    return valid_representations // symmetry


def canonical_key(inst: dict) -> str:
    """Complete isomorphism invariant for a path plus unlabeled cycles."""
    normal = {
        "family": "graceful_zillion_graph",
        "path_edges": int(inst["path_edges"]),
        "cycle_lengths": sorted(map(int, inst["cycle_lengths"])),
    }
    payload = json.dumps(normal, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | None:
    current = int(params.get("n", 64))
    if current >= 240:
        return None
    harder = dict(params)
    harder["n"] = min(240, math.ceil(current * 4 / 3))
    harder["min_cycles"] = min(4, max(3, int(params.get("min_cycles", 3))))
    harder["min_distinct_cycles"] = 3
    harder["path_max_ratio"] = min(float(params.get("path_max_ratio", 0.60)), 0.55)
    harder["build_attempts"] = max(int(params.get("build_attempts", 1800)), 3500)
    return harder


def _answer_from_flat(inst: dict, flat: list[int]) -> dict:
    cut = inst["path_edges"] + 1
    answer = {"path": flat[:cut], "cycles": []}
    for length in inst["cycle_lengths"]:
        answer["cycles"].append(flat[cut : cut + length])
        cut += length
    return answer


def _outlier_attack(inst: dict) -> dict:
    """Put extreme labels at the path endpoints, then alternate extremes."""
    a = inst["n"]
    order = []
    low, high = 0, a
    while low <= high:
        order.append(low)
        low += 1
        if low <= high:
            order.append(high)
            high -= 1
    # The endpoints are the only degree-one vertices, so explicitly give them
    # the two magnitude outliers before filling the internal positions.
    path_size = inst["path_edges"] + 1
    if path_size >= 2:
        rest = [x for x in order if x not in (0, a)]
        path = [0] + rest[: path_size - 2] + [a]
        flat = path + rest[path_size - 2 :]
    else:
        flat = order
    return _answer_from_flat(inst, flat)


def _greedy_attack(inst: dict) -> dict:
    """Greedily realize the largest still-unused difference at each step."""
    a = inst["n"]
    unused = set(range(a + 1))
    flat = []
    previous = 0
    flat.append(previous)
    unused.remove(previous)
    used_differences = set()
    while unused:
        candidates = sorted(unused)
        nxt = max(
            candidates,
            key=lambda value: (
                abs(value - previous) not in used_differences,
                abs(value - previous),
                -value,
            ),
        )
        used_differences.add(abs(nxt - previous))
        flat.append(nxt)
        unused.remove(nxt)
        previous = nxt
    return _answer_from_flat(inst, flat)


def _find_bad_swap(inst: dict) -> dict:
    planted = inst["answer"]
    flat = planted["path"] + [x for c in planted["cycles"] for x in c]
    for i in range(len(flat)):
        for j in range(i + 1, len(flat)):
            changed = list(flat)
            changed[i], changed[j] = changed[j], changed[i]
            candidate = _answer_from_flat(inst, changed)
            ok, _ = verify(inst, candidate)
            if not ok:
                return candidate
    raise RuntimeError("could not find a corrupting swap")


def selftest() -> dict:
    report: dict[str, object] = {}

    # G1: every named preset, several independent seeds.
    g1_cases = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError(f"G1 {preset}/{seed}: {why}")
            g1_cases.append({"preset": preset, "seed": seed, "ok": ok})
    report["G1_planted_verifies"] = {"pass": True, "cases": g1_cases}

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping)

    # G2: five different corruptions must reach five different rejection paths.
    drop = copy.deepcopy(inst["answer"])
    drop["path"].pop()
    swap = _find_bad_swap(inst)
    duplicate = copy.deepcopy(inst["answer"])
    duplicate["path"][0] = duplicate["path"][1]
    empty = {}
    out_of_range = copy.deepcopy(inst["answer"])
    out_of_range["path"][0] = inst["n"] + 1
    corruptions = {
        "drop": drop,
        "swap": swap,
        "duplicate": duplicate,
        "empty": empty,
        "out_of_range": out_of_range,
    }
    reasons = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        if ok:
            raise AssertionError(f"G2 accepted {name}")
        reasons[name] = why
    if len(set(reasons.values())) != len(reasons):
        raise AssertionError(f"G2 reasons are not distinct: {reasons}")
    report["G2_rejects_corruption"] = {"pass": True, "reasons": reasons}

    # G3: prose and markdown around the tagged JSON are tolerated.
    encoded = json.dumps(inst["answer"], separators=(",", ":"))
    response = f"I checked every difference.\n```json\n<answer>{encoded}</answer>\n```\n"
    parsed = parse_answer(response)
    if parsed != inst["answer"] or not verify(inst, parsed)[0]:
        raise AssertionError("G3 realistic round trip failed")
    garbage_cases = ["", "no tags", "<answer>{bad}</answer>", "<answer>[]</answer>"]
    if any(parse_answer(value) is not None for value in garbage_cases):
        raise AssertionError("G3 malformed input did not return None")
    report["G3_round_trip"] = {
        "pass": True,
        "realistic_response": True,
        "garbage_rejected": len(garbage_cases),
    }

    # G4: uniform structural guesses, with all obvious constraints enforced.
    guess_rng = random.Random(8675309)
    total = 200_000
    hits = 0
    for _ in range(total):
        hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    probability = hits / total
    if probability >= 1e-6:
        raise AssertionError(f"G4 hit rate too high: {hits}/{total}")
    report["G4_guess_resistance"] = {
        "pass": True,
        "hits": hits,
        "total": total,
        "measured_probability": probability,
        "prior": "uniform label permutation with exact path/cycle shapes and bijection",
        "naive_structural_space": str(search_space(inst)),
    }

    # G5: enumerate a genuinely small generated problem exactly.
    small = make_instance(
        8,
        seed=17,
        min_cycles=0,
        min_distinct_cycles=0,
        path_min_ratio=0.0,
        path_max_ratio=1.0,
        build_attempts=20,
    )
    solutions = enumerate_all(small)
    space = search_space(small)
    if solutions is None or not (0 < solutions < space):
        raise AssertionError("G5 exact enumeration failed")
    density = solutions / space
    if density >= 0.02:
        raise AssertionError(f"G5 small-instance density is not sparse: {density}")
    report["G5_sparse"] = {
        "pass": True,
        "n": small["n"],
        "path_edges": small["path_edges"],
        "cycle_lengths": small["cycle_lengths"],
        "valid_answers": solutions,
        "structural_space": space,
        "density": density,
    }

    # G6: three construction-aware cheap attacks over eight fresh problems.
    attack_rows = {
        "degree_outlier_extremes": {"attempts": 0, "solved": 0},
        "largest_difference_greedy": {"attempts": 0, "solved": 0},
        "random_restart_128": {"attempts": 0, "solved": 0},
    }
    for offset in range(8):
        attacked = make_instance(seed=7000 + offset, **shipping)
        candidates = {
            "degree_outlier_extremes": [_outlier_attack(attacked)],
            "largest_difference_greedy": [_greedy_attack(attacked)],
            "random_restart_128": [
                random_candidate(attacked, random.Random(900_000 + 1000 * offset + j))
                for j in range(128)
            ],
        }
        for name, trials in candidates.items():
            row = attack_rows[name]
            row["attempts"] += len(trials)
            solved = any(verify(attacked, candidate)[0] for candidate in trials)
            row["solved"] += int(solved)
    if any(row["solved"] for row in attack_rows.values()):
        raise AssertionError(f"G6 attack succeeded: {attack_rows}")
    report["G6_adversary_panel"] = {
        "pass": True,
        "instances": 8,
        "attacks": attack_rows,
    }

    # G7: double n, rebuild, verify, and compare exact structural spaces.
    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled_params["build_attempts"] = max(doubled_params["build_attempts"], 5000)
    doubled = make_instance(seed=271828, **doubled_params)
    ok, why = verify(doubled, doubled["answer"])
    if not ok:
        raise AssertionError(f"G7 doubled plant failed: {why}")
    if search_space(doubled) <= search_space(inst):
        raise AssertionError("G7 doubled search space did not grow")
    report["G7_scales"] = {
        "pass": True,
        "base_n": inst["n"],
        "doubled_n": doubled["n"],
        "base_space_digits": len(str(search_space(inst))),
        "doubled_space_digits": len(str(search_space(doubled))),
        "doubled_planted_verifies": True,
    }

    # G8: component order, traversal direction, cycle rotation/reversal, and
    # global label reflection are the full cheap symmetries of this encoding.
    keys = []
    invariance_checks = 0
    carried_witness_checks = 0
    answer_symmetry_checks = 0
    for seed in range(20):
        original = make_instance(seed=20_000 + seed, **shipping)
        key = canonical_key(original)
        keys.append(key)

        reordered = copy.deepcopy(original)
        reordered["cycle_lengths"] = list(reversed(reordered["cycle_lengths"]))
        if canonical_key(reordered) != key:
            raise AssertionError("G8 cycle-input reordering changed key")
        invariance_checks += 1
        if not verify(reordered, original["answer"])[0]:
            raise AssertionError("G8 real input reordering did not preserve witness")
        carried_witness_checks += 1

        transformed_answer = {
            "path": list(reversed(original["answer"]["path"])),
            "cycles": [],
        }
        for index, cycle in enumerate(reversed(original["answer"]["cycles"])):
            moved = cycle[1:] + cycle[:1]
            if index % 2:
                moved = list(reversed(moved))
            transformed_answer["cycles"].append(moved)
        if not verify(reordered, transformed_answer)[0]:
            raise AssertionError("G8 composed traversal symmetries broke witness")
        answer_symmetry_checks += 1

        a = original["n"]
        reflected = {
            "path": [a - x for x in original["answer"]["path"]],
            "cycles": [[a - x for x in c] for c in original["answer"]["cycles"]],
        }
        if not verify(original, reflected)[0]:
            raise AssertionError("G8 global label reflection broke witness")
        answer_symmetry_checks += 1

    if len(set(keys)) != len(keys):
        raise AssertionError("G8 unrelated seeds produced duplicate graph types")
    report["G8_canonical_key"] = {
        "pass": True,
        "seeds": 20,
        "input_reordering_invariance_checks": invariance_checks,
        "carried_witness_checks": carried_witness_checks,
        "answer_symmetry_checks": answer_symmetry_checks,
        "distinct_unrelated_keys": len(set(keys)),
        "complete_invariant": "one path length plus sorted cycle-length multiset",
    }

    report["all_passed"] = True
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
