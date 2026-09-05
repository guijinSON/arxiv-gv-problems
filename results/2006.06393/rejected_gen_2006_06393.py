#!/usr/bin/env python3
"""Verified native hypergraph edge-coloring instances from arXiv:2006.06393.

The paper's hypergraph has ordinary machine--job edges and two kinds of
hyperedge: a group--job hyperedge occupies every machine in one of two
disjoint machine groups.  This module inverse-generates a compact optimal
coloring.  It samples machine offsets first, chooses which colors contain a
group hyperedge, and erases the colors after emitting the resulting
operations.  The answer is a short exact symbolic rule whose expansion is the
full coloring; no generated instance is solved to obtain its certificate.
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
import time


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "two-group machine--job hypergraph",
        "ordinary machine--job edges",
        "group--job hyperedges occupying every machine in a group",
        "compressed modular edge-coloring rule",
    ],
    "verification_operations": [
        "exact modular subtraction",
        "hyperedge incidence expansion",
        "machine/color uniqueness comparison",
        "job/color uniqueness comparison",
        "integer machine-load count",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize that each machine's missing ordinary-job residues are a "
        "cyclic translate of its group's hyperedge-job residues; the translate "
        "is the machine's coloring offset."
    ),
    "hardness_basis": (
        "Track B: exhaustive cyclic correlation solves the bounded certificate "
        "problem in O(m n^2 + E) exact set comparisons (the paper's Theorem 1 "
        "and Section 13 also solve the full optimization class in polynomial "
        "time by LP and integral network flows); at the shipping preset the "
        "reference implementation uses 10,844 counted operations and about "
        "0.003 wall-clock seconds, while the modular-sum invariant leaves 212 "
        "exact operations after it is seen."
    ),
    "max_answer_tokens": 7,
}

NATIVE: dict = {
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


# n is both the number of jobs and the number of colors.  The answer contains
# only 2*group_size offsets: escalation grows the ambient cyclic group and the
# operation haystack without lengthening the witness.
DIFFICULTY: dict = {
    "demo": {"n": 5, "group_size": 2, "hyper_count": 2},
    "easy": {"n": 17, "group_size": 3, "hyper_count": 8},
    "medium": {"n": 37, "group_size": 4, "hyper_count": 18},
    "hard": {"n": 53, "group_size": 4, "hyper_count": 26},
}
SHIPPING_DIFFICULTY = "medium"


STRUCTURAL_HINT: str = (
    "Within either machine group, every machine's set of missing ordinary-job "
    "residues is a cyclic translate of that group's hyperedge-job set."
)
PLACEBO_HINT: str = (
    "Within either machine group, careful bookkeeping of every machine and job "
    "residue helps prevent accidental conflicts between operations."
)


CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON list [s_0,...,s_(m-1)] of one offset per machine, in machine-ID "
        "order; offsets are pairwise distinct members of {1,...,n-1}.  It "
        "denotes the exact coloring color(h,j)=j-s_h mod n for an ordinary "
        "edge and color(group,j)=j for a group hyperedge."
    ),
    "bounds": {
        "length": "number of machines",
        "entry_min": 1,
        "entry_max": "n-1",
        "pairwise_distinct": True,
        "search_space": "P(n-1, number_of_machines)",
    },
}


NOTES: str = (
    "Section 1 fixes the native object: machines are partitioned into two "
    "nonempty groups, ordinary edges use one machine and one job, and a "
    "group--job hyperedge uses every machine in that group and that job. It "
    "also identifies the empty-group case as ordinary bipartite multigraph "
    "edge coloring, so the generator keeps both groups nonempty and includes "
    "both ordinary and group operations. Theorem 1 and Section 13 prove that "
    "an integral optimum can be found in polynomial time after the LP, using "
    "the integral network-flow models developed in Sections 10--12. That fact "
    "rules out Track A and is reported as the broader reference method rather "
    "than hidden. Section 3's decomposition of a coloring into matching "
    "columns is the native scheduling viewpoint used here. Generation is "
    "inverse: pairwise-distinct nonzero offsets are sampled first; disjoint "
    "sets of colors are assigned group hyperedges; ordinary operations fill "
    "every other machine/color slot; then colors are erased. Every machine has "
    "load n, so the constructed n-coloring is optimal. The exact checker "
    "expands any submitted offset rule and tests machine and job conflicts; it "
    "never reads the planted answer. Equal machine loads and randomized labels "
    "defeat the marginal outlier probe; a smallest-gap alignment is broken by "
    "cyclic wraparound; raw, nonmodular centroid arithmetic is broken by the "
    "same wraparound; random restart samples the full structure-aware bounded "
    "language. Exhaustive cyclic correlation succeeds as expected and is "
    "reported separately for Track B."
)


# Filled from script-owned hardening runs.  G9(a,b) are diagnostics; only the
# exact answer/route caps contribute to G9's pass flag.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "not_run",
}


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"^\s*```(?:json|text)?\s*(.*?)\s*```\s*$", re.I | re.S)
_G4_SAMPLES = 200_000
_ENUMERATION_CAP = 200_000
_ATTACK_SEEDS = 8
_RANDOM_RESTARTS = 256


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_parameters(n, group_size, hyper_count):
    for name, value in (("n", n), ("group_size", group_size),
                        ("hyper_count", hyper_count)):
        if not _is_int(value):
            raise ValueError(f"{name} must be an integer")
    if not 5 <= n <= 200:
        raise ValueError("n must lie in 5..200")
    if not 2 <= group_size <= 12:
        raise ValueError("group_size must lie in 2..12")
    if 2 * group_size > n - 1:
        raise ValueError("n-1 must provide a distinct nonzero offset per machine")
    if not 1 <= hyper_count or 2 * hyper_count >= n:
        raise ValueError("hyper_count must be positive and 2*hyper_count < n")
    if math.gcd(n, hyper_count) != 1:
        raise ValueError("hyper_count must be coprime to n")


def _operation_count(n, group_size, hyper_count):
    # In each group, hyper_count colors contribute one hyperedge and every
    # remaining color contributes group_size ordinary edges.
    return 2 * (hyper_count + (n - hyper_count) * group_size)


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a native hypergraph and its compressed coloring rule."""
    group_size = params.pop("group_size", 4)
    hyper_count = params.pop("hyper_count", (n - 1) // 2)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, group_size, hyper_count)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    machine_count = 2 * group_size
    groups = [list(range(group_size)),
              list(range(group_size, machine_count))]

    # The answer is sampled before any operation is created.
    offsets = rng.sample(range(1, n), machine_count)

    colors = list(range(n))
    rng.shuffle(colors)
    hyper_colors = [set(colors[:hyper_count]),
                    set(colors[hyper_count:2 * hyper_count])]

    hyperedges = []
    ordinary_edges = []
    for group_index, machines in enumerate(groups):
        selected = hyper_colors[group_index]
        for color in range(n):
            if color in selected:
                # A group hyperedge at job j=color is assigned that color.
                hyperedges.append([group_index, color])
            else:
                # An ordinary operation on h at j=color+s_h is assigned color.
                for machine in machines:
                    ordinary_edges.append(
                        [machine, (color + offsets[machine]) % n]
                    )

    # Input ordering carries no information and is randomized independently of
    # the witness.  Rendering groups it again for readability.
    rng.shuffle(hyperedges)
    rng.shuffle(ordinary_edges)
    return {
        "n": n,
        "groups": groups,
        "ordinary_edges": ordinary_edges,
        "hyperedges": hyperedges,
        "answer": offsets,
    }


def _incidence_sets(inst):
    n = inst["n"]
    groups = inst["groups"]
    machine_count = sum(len(g) for g in groups)
    hyper = [set(), set()]
    ordinary = [set() for _ in range(machine_count)]
    for group_index, job in inst["hyperedges"]:
        hyper[group_index].add(job)
    for machine, job in inst["ordinary_edges"]:
        ordinary[machine].add(job)
    return hyper, ordinary


def render(inst) -> str:
    """Render a complete, exact problem statement and output contract."""
    n = inst["n"]
    groups = inst["groups"]
    hyper, ordinary = _incidence_sets(inst)
    lines = [
        "Find a compressed optimal edge-coloring of the following two-group "
        "machine--job hypergraph.",
        "",
        f"Jobs and colors are the residues 0,1,...,{n - 1} modulo n={n}. "
        "Machines are numbered from 0. Machine groups are disjoint.",
        "An ordinary edge (h,j) occupies machine h and job j. A group "
        "hyperedge (G,j) occupies every machine in group G and job j.",
        "Two operations conflict exactly when they share a machine or share a "
        "job. A proper coloring assigns different colors to every conflicting "
        "pair.",
        "",
        "Your witness is one offset s_h for each machine h, in machine-ID "
        "order. Every offset must be an integer in 1..n-1, and all offsets must "
        "be pairwise distinct. The witness denotes this complete coloring:",
        "  ordinary edge (h,j) has color (j - s_h) mod n;",
        "  group hyperedge (G,j) has color j.",
        "Find offsets for which that denoted coloring is proper. Every machine "
        "has load n in this instance, so any proper n-coloring is optimal.",
        "",
        "Instance data (each listed edge has multiplicity one; list order does "
        "not matter):",
    ]
    for group_index, machines in enumerate(groups):
        lines.append(f"  G{group_index} machines: {sorted(machines)}")
        lines.append(
            f"  G{group_index} hyperedge jobs: {sorted(hyper[group_index])}"
        )
        for machine in sorted(machines):
            lines.append(
                f"  machine {machine} ordinary-edge jobs: "
                f"{sorted(ordinary[machine])}"
            )
    machine_count = sum(len(g) for g in groups)
    lines.extend([
        "",
        f"Give your final answer inside <answer></answer> tags, as a JSON list "
        f"of exactly {machine_count} integers [s_0,...,s_{machine_count - 1}].",
        ("Example format only: <answer>[1,2," +
         ",".join(str(i) for i in range(3, machine_count + 1)) + "]</answer>"
         if machine_count >= 3 else
         "Example format only: <answer>[1,2]</answer>"),
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Extract the tagged JSON integer list; return None on every malformed input."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    payload = matches[-1].strip()
    fence = _FENCE_RE.match(payload)
    if fence:
        payload = fence.group(1).strip()
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(answer, list):
        return None
    if not all(_is_int(v) for v in answer):
        return None
    return answer


def _validate_instance_shape(inst):
    try:
        n = inst["n"]
        groups = inst["groups"]
        ordinary_edges = inst["ordinary_edges"]
        hyperedges = inst["hyperedges"]
    except (KeyError, TypeError):
        return None, "instance is missing required fields"
    if not _is_int(n) or n < 2:
        return None, "instance modulus n is invalid"
    if not isinstance(groups, list) or len(groups) != 2:
        return None, "instance must have exactly two machine groups"
    if not all(isinstance(g, list) and g for g in groups):
        return None, "both machine groups must be nonempty lists"
    flat = [h for group in groups for h in group]
    if (not all(_is_int(h) for h in flat)
            or sorted(flat) != list(range(len(flat)))):
        return None, "machine IDs must be exactly 0..m-1"
    if not isinstance(ordinary_edges, list) or not isinstance(hyperedges, list):
        return None, "instance edge collections must be lists"
    return (n, groups, ordinary_edges, hyperedges), None


def verify(inst, answer):
    """Check any submitted offset witness exactly, without consulting the plant."""
    shape, problem = _validate_instance_shape(inst)
    if shape is None:
        return False, problem
    n, groups, ordinary_edges, hyperedges = shape
    machine_count = sum(len(g) for g in groups)
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) != machine_count:
        return False, (f"expected {machine_count} offsets, got "
                       f"{len(answer)}")
    for machine, offset in enumerate(answer):
        if not _is_int(offset):
            return False, f"offset at machine {machine} is not an integer"
        if not 1 <= offset < n:
            return False, (f"offset at machine {machine} must lie in 1..{n - 1}, "
                           f"got {offset}")
    if len(set(answer)) != machine_count:
        return False, "offsets must be pairwise distinct"

    machine_color = {}
    job_color = {}
    loads = [0] * machine_count

    for edge_index, edge in enumerate(hyperedges):
        if (not isinstance(edge, list) or len(edge) != 2
                or not all(_is_int(v) for v in edge)):
            return False, f"instance hyperedge {edge_index} is malformed"
        group_index, job = edge
        if group_index not in (0, 1) or not 0 <= job < n:
            return False, f"instance hyperedge {edge_index} is out of range"
        color = job
        job_key = (job, color)
        if job_key in job_color:
            return False, (f"hyperedge {edge_index} repeats job/color "
                           f"({job},{color})")
        job_color[job_key] = ("H", edge_index)
        for machine in groups[group_index]:
            key = (machine, color)
            if key in machine_color:
                return False, (f"hyperedge {edge_index} repeats machine/color "
                               f"({machine},{color})")
            machine_color[key] = ("H", edge_index)
            loads[machine] += 1

    for edge_index, edge in enumerate(ordinary_edges):
        if (not isinstance(edge, list) or len(edge) != 2
                or not all(_is_int(v) for v in edge)):
            return False, f"instance ordinary edge {edge_index} is malformed"
        machine, job = edge
        if not 0 <= machine < machine_count or not 0 <= job < n:
            return False, f"instance ordinary edge {edge_index} is out of range"
        color = (job - answer[machine]) % n
        machine_key = (machine, color)
        if machine_key in machine_color:
            return False, (f"ordinary edge {edge_index} repeats machine/color "
                           f"({machine},{color})")
        job_key = (job, color)
        if job_key in job_color:
            return False, (f"ordinary edge {edge_index} repeats job/color "
                           f"({job},{color})")
        machine_color[machine_key] = ("S", edge_index)
        job_color[job_key] = ("S", edge_index)
        loads[machine] += 1

    if max(loads, default=0) != n:
        return False, (f"instance lower-bound load is {max(loads, default=0)}, "
                       f"not n={n}")
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from distinct, nonzero offset vectors."""
    if not isinstance(rng, random.Random):
        # The contract only promises a compatible RNG, so duck typing remains
        # accepted; this branch merely gives a clearer error for bad callers.
        if not callable(getattr(rng, "sample", None)):
            raise TypeError("rng must provide sample()")
    machine_count = sum(len(g) for g in inst["groups"])
    return rng.sample(range(1, inst["n"]), machine_count)


def search_space(inst):
    """Number of pairwise-distinct nonzero offset vectors."""
    n = inst["n"]
    machine_count = sum(len(g) for g in inst["groups"])
    if n - 1 < machine_count:
        return 0
    return math.factorial(n - 1) // math.factorial(n - 1 - machine_count)


def enumerate_all(inst):
    """Count valid bounded-language witnesses exactly when safely small."""
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    machine_count = sum(len(g) for g in inst["groups"])
    total = 0
    for candidate in itertools.permutations(range(1, inst["n"]), machine_count):
        total += int(verify(inst, list(candidate))[0])
    return total


def _canonical_representation(inst):
    n = inst["n"]
    groups = inst["groups"]
    hyper, ordinary = _incidence_sets(inst)
    best = None
    units = [u for u in range(1, n) if math.gcd(u, n) == 1]
    for unit in units:
        for translation in range(n):
            group_reps = []
            for group_index, machines in enumerate(groups):
                h_jobs = tuple(sorted(
                    (unit * j + translation) % n
                    for j in hyper[group_index]
                ))
                machine_reps = tuple(sorted(
                    tuple(sorted((unit * j + translation) % n
                                 for j in ordinary[machine]))
                    for machine in machines
                ))
                group_reps.append((h_jobs, machine_reps))
            rep = (n, tuple(sorted(group_reps)))
            if best is None or rep < best:
                best = rep
    return best


def canonical_key(inst):
    """Canonicalize operation order, machine relabeling, group swap, and Aff(Z_n)."""
    rep = _canonical_representation(inst)
    return hashlib.sha256(repr(rep).encode("utf-8")).hexdigest()


def _best_hyper_count(n):
    for count in range((n - 1) // 2, 0, -1):
        if math.gcd(n, count) == 1:
            return count
    raise ValueError("no coprime hyper_count")


def escalate(params):
    """Grow the residue haystack at fixed witness length until the route cap binds."""
    n = params["n"]
    group_size = params["group_size"]
    if n >= 53:
        return None
    next_n = min(53, n + 10)
    return {
        "n": next_n,
        "group_size": group_size,
        "hyper_count": _best_hyper_count(next_n),
    }


def _reference_cyclic_correlation(inst):
    """Mechanically test every cyclic shift for every machine."""
    started = time.perf_counter()
    n = inst["n"]
    groups = inst["groups"]
    machine_count = sum(len(g) for g in groups)
    hyper, ordinary = _incidence_sets(inst)
    group_of = {}
    for group_index, machines in enumerate(groups):
        for machine in machines:
            group_of[machine] = group_index

    answer = []
    comparisons = 0
    for machine in range(machine_count):
        missing = set(range(n)) - ordinary[machine]
        h_jobs = hyper[group_of[machine]]
        valid_shifts = []
        for shift in range(1, n):
            matches = True
            # Deliberately complete, not short-circuited: this is the honest
            # mechanical correlation cost at the shipping size.
            for residue in range(n):
                comparisons += 1
                if ((residue in missing)
                        != (((residue - shift) % n) in h_jobs)):
                    matches = False
            if matches:
                valid_shifts.append(shift)
        if len(valid_shifts) != 1:
            return None, {
                "wall_clock_sec": time.perf_counter() - started,
                "set_comparisons": comparisons,
                "operations": comparisons + len(inst["ordinary_edges"])
                              + len(inst["hyperedges"]),
                "failure": (f"machine {machine} has {len(valid_shifts)} "
                            "valid cyclic shifts"),
            }
        answer.append(valid_shifts[0])
    return answer, {
        "wall_clock_sec": time.perf_counter() - started,
        "set_comparisons": comparisons,
        "operations": comparisons + len(inst["ordinary_edges"])
                      + len(inst["hyperedges"]),
        "failure": None,
    }


def _repair_language(values, n, machine_count):
    """Project a heuristic's guesses into the declared structural language."""
    result = []
    used = set()
    for index in range(machine_count):
        raw = values[index] if index < len(values) else index + 1
        value = raw % n
        if value == 0 or value in used:
            value = next(v for v in range(1, n) if v not in used)
        result.append(value)
        used.add(value)
    return result


def _attack_outlier_degree(inst):
    # Every machine has the same total load.  Tie-breaking by machine label is
    # the usual per-element outlier fallback.
    n = inst["n"]
    machine_count = sum(len(g) for g in inst["groups"])
    _, ordinary = _incidence_sets(inst)
    ranked = sorted(range(machine_count), key=lambda h: (len(ordinary[h]), h))
    candidate = [0] * machine_count
    for rank, machine in enumerate(ranked, 1):
        candidate[machine] = rank
    return _repair_language(candidate, n, machine_count), machine_count


def _attack_greedy_smallest_gap(inst):
    n = inst["n"]
    groups = inst["groups"]
    machine_count = sum(len(g) for g in groups)
    hyper, ordinary = _incidence_sets(inst)
    group_of = {h: group_index
                for group_index, machines in enumerate(groups)
                for h in machines}
    values = []
    for machine in range(machine_count):
        missing = set(range(n)) - ordinary[machine]
        values.append((min(missing) - min(hyper[group_of[machine]])) % n)
    return _repair_language(values, n, machine_count), machine_count


def _attack_raw_centroid(inst):
    # A plausible by-hand ansatz that ignores modular wraparound and division
    # in Z_n.  It consumes the same visible sets as the intended invariant but
    # does not execute the needed modular step.
    n = inst["n"]
    groups = inst["groups"]
    machine_count = sum(len(g) for g in groups)
    hyper, ordinary = _incidence_sets(inst)
    group_of = {h: group_index
                for group_index, machines in enumerate(groups)
                for h in machines}
    values = []
    for machine in range(machine_count):
        group_index = group_of[machine]
        missing = set(range(n)) - ordinary[machine]
        count = len(hyper[group_index])
        values.append((sum(missing) - sum(hyper[group_index])) // count)
    return _repair_language(values, n, machine_count), machine_count


def _attack_random_restart(inst, rng, restarts=_RANDOM_RESTARTS):
    candidate = None
    for iteration in range(1, restarts + 1):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate, iteration
    return candidate, restarts


def _reorder_instance(inst, rng):
    out = copy.deepcopy(inst)
    rng.shuffle(out["ordinary_edges"])
    rng.shuffle(out["hyperedges"])
    for group in out["groups"]:
        rng.shuffle(group)
    return out


def _relabel_machines(inst, rng):
    out = copy.deepcopy(inst)
    mapping = {}
    for machines in inst["groups"]:
        targets = machines[:]
        rng.shuffle(targets)
        mapping.update(zip(machines, targets))
    out["groups"] = [[mapping[h] for h in group] for group in inst["groups"]]
    out["ordinary_edges"] = [[mapping[h], j]
                             for h, j in inst["ordinary_edges"]]
    carried = [0] * len(inst["answer"])
    for old, new in mapping.items():
        carried[new] = inst["answer"][old]
    out["answer"] = carried
    return out


def _affine_relabel_jobs(inst, unit, translation):
    out = copy.deepcopy(inst)
    n = inst["n"]
    out["ordinary_edges"] = [
        [h, (unit * j + translation) % n]
        for h, j in inst["ordinary_edges"]
    ]
    out["hyperedges"] = [
        [g, (unit * j + translation) % n]
        for g, j in inst["hyperedges"]
    ]
    # The transformed colors are c' = unit*c + translation, so ordinary
    # offsets scale and the common translation cancels.
    out["answer"] = [(unit * s) % n for s in inst["answer"]]
    return out


def _swap_groups(inst):
    out = copy.deepcopy(inst)
    out["groups"] = [out["groups"][1], out["groups"][0]]
    out["hyperedges"] = [[1 - g, j] for g, j in out["hyperedges"]]
    return out


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _compact_route_operations(inst):
    # Sum each displayed hyperedge and ordinary-edge residue once, followed by
    # subtraction, multiplication by |H|^{-1}, and reduction modulo n for each
    # machine: s_h=(sum(missing_h)-sum(H_group))/|H_group| mod n.
    machine_count = sum(len(g) for g in inst["groups"])
    return (len(inst["ordinary_edges"]) + len(inst["hyperedges"])
            + 3 * machine_count)


def selftest() -> dict:
    """Run every mandatory construction, parsing, hardness, and symmetry gate."""
    report = {}

    g1_failures = []
    g1_tests = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7, 29):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_tests += 1
            if not ok:
                g1_failures.append([preset, seed, why])
            try:
                if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                    g1_failures.append([preset, seed, "answer is not JSON-native"])
            except (TypeError, ValueError) as exc:
                g1_failures.append([preset, seed, f"JSON encoding failed: {exc}"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "tests": g1_tests,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=314159, **shipping_params)
    planted = shipping["answer"]

    corruptions = {}
    dropped = planted[:-1]
    corruptions["drop_one"] = verify(shipping, dropped)
    swapped = planted[:]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    corruptions["swap_two"] = verify(shipping, swapped)
    duplicated = planted[:]
    duplicated[1] = duplicated[0]
    corruptions["duplicate_one"] = verify(shipping, duplicated)
    corruptions["empty"] = verify(shipping, [])
    outside = planted[:]
    outside[0] = shipping["n"]
    corruptions["out_of_range"] = verify(shipping, outside)
    reasons = [why for _, why in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": (all(not ok for ok, _ in corruptions.values())
                 and len(set(reasons)) == len(reasons)),
        "cases": {name: {"accepted": ok, "reason": why}
                  for name, (ok, why) in corruptions.items()},
        "distinct_reasons": len(set(reasons)),
    }

    encoded = json.dumps(planted, separators=(",", ":"))
    response = (
        "The cyclic translates give the following offsets.\n"
        "```json\n<answer>\n" + encoded + "\n</answer>\n```\n"
        "I checked the expanded operation colors."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": (parsed == planted
                 and parse_answer("garbage without answer tags") is None),
        "model_style_response_parsed": parsed == planted,
        "garbage_returns_none": parse_answer("garbage without answer tags") is None,
    }

    guess_rng = random.Random(0x200606393)
    guess_hits = 0
    guess_started = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        guess_hits += int(verify(
            shipping, random_candidate(shipping, guess_rng)
        )[0])
    guess_wall = time.perf_counter() - guess_started
    guess_fraction = guess_hits / _G4_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": _G4_SAMPLES,
        "sampled_fraction": guess_fraction,
        "exact_fraction": f"1/{search_space(shipping)}",
        "sampling_wall_clock_sec": guess_wall,
        "candidate_prior": (
            "uniform over pairwise-distinct nonzero offset vectors, so every "
            "answer-shape and immediately stated structural restriction is enforced"
        ),
    }

    reference_answer, reference_stats = _reference_cyclic_correlation(shipping)
    reference_ok, reference_why = (verify(shipping, reference_answer)
                                    if reference_answer is not None
                                    else (False, reference_stats["failure"]))
    demo = make_instance(seed=314159, **DIFFICULTY["demo"])
    demo_count_started = time.perf_counter()
    demo_count = enumerate_all(demo)
    demo_count_wall = time.perf_counter() - demo_count_started

    attack_results = {
        "outlier_equal_load_rank": {
            "successes": 0, "attempts": 0, "iterations": 0,
            "wall_clock_sec": 0.0,
        },
        "greedy_smallest_gap": {
            "successes": 0, "attempts": 0, "iterations": 0,
            "wall_clock_sec": 0.0,
        },
        "random_restart_256": {
            "successes": 0, "attempts": 0, "iterations": 0,
            "wall_clock_sec": 0.0,
        },
        "by_hand_raw_centroid": {
            "successes": 0, "attempts": 0, "iterations": 0,
            "wall_clock_sec": 0.0,
        },
    }
    reference_successes = 0
    reference_operations = 0
    reference_comparisons = 0
    reference_wall = 0.0
    for seed in range(100, 100 + _ATTACK_SEEDS):
        inst = make_instance(seed=seed, **shipping_params)
        rng = random.Random(seed ^ 0xA5A52006)
        attacks = (
            ("outlier_equal_load_rank", lambda: _attack_outlier_degree(inst)),
            ("greedy_smallest_gap", lambda: _attack_greedy_smallest_gap(inst)),
            ("random_restart_256",
             lambda: _attack_random_restart(inst, rng)),
            ("by_hand_raw_centroid", lambda: _attack_raw_centroid(inst)),
        )
        for name, attack in attacks:
            started = time.perf_counter()
            candidate, iterations = attack()
            elapsed = time.perf_counter() - started
            ok, _ = verify(inst, candidate)
            attack_results[name]["successes"] += int(ok)
            attack_results[name]["attempts"] += 1
            attack_results[name]["iterations"] += iterations
            attack_results[name]["wall_clock_sec"] += elapsed

        candidate, stats = _reference_cyclic_correlation(inst)
        ok, _ = (verify(inst, candidate) if candidate is not None
                 else (False, stats["failure"]))
        reference_successes += int(ok)
        reference_operations += stats["operations"]
        reference_comparisons += stats["set_comparisons"]
        reference_wall += stats["wall_clock_sec"]

    strongest_failed = max(
        attack_results.items(),
        key=lambda item: (item[1]["iterations"], item[1]["wall_clock_sec"]),
    )
    report["G5_density_and_baseline_cost"] = {
        "pass": (guess_fraction < 1e-6 and reference_ok
                 and demo_count == 1),
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_density_samples": _G4_SAMPLES,
        "shipping_sampled_valid_fraction": guess_fraction,
        "shipping_exact_valid_solution_count_theoretical": 1,
        "shipping_exact_density_denominator": search_space(shipping),
        "demo_exact_valid_solution_count": demo_count,
        "demo_search_space": search_space(demo),
        "demo_enumeration_wall_clock_sec": demo_count_wall,
        "reference_wall_clock_sec": reference_stats["wall_clock_sec"],
        "reference_operations": reference_stats["operations"],
        "reference_set_comparisons": reference_stats["set_comparisons"],
        "reference_verify_reason": reference_why,
        "strongest_failed_attack": strongest_failed[0],
        "strongest_failed_attack_iterations": strongest_failed[1]["iterations"],
        "strongest_failed_attack_wall_clock_sec": strongest_failed[1]["wall_clock_sec"],
    }

    all_attacks_failed = all(
        result["successes"] == 0 and result["attempts"] >= _ATTACK_SEEDS
        for result in attack_results.values()
    )
    report["G6_adversary_panel"] = {
        "pass": (all_attacks_failed
                 and reference_successes == _ATTACK_SEEDS),
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "exhaustive cyclic set correlation",
            "complexity": "O(m n^2 + E) exact membership comparisons",
            "wall_clock_sec": reference_wall,
            "operations": reference_operations,
            "set_comparisons": reference_comparisons,
            "attempts": _ATTACK_SEEDS,
            "successes": reference_successes,
            "solves": f"{reference_successes}/{_ATTACK_SEEDS}, as expected",
            "broader_paper_algorithm": (
                "Theorem 1 and Section 13: LP followed by integral network flows, "
                "polynomial time for the full two-hypervertex class"
            ),
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * shipping_params["n"]
    doubled_params["hyper_count"] = _best_hyper_count(doubled_params["n"])
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (doubled_ok
                 and len(doubled["ordinary_edges"]) + len(doubled["hyperedges"])
                 > len(shipping["ordinary_edges"]) + len(shipping["hyperedges"])
                 and search_space(doubled) > search_space(shipping)),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_operations": (len(shipping["ordinary_edges"])
                                + len(shipping["hyperedges"])),
        "doubled_operations": (len(doubled["ordinary_edges"])
                               + len(doubled["hyperedges"])),
        "shipping_search_space": search_space(shipping),
        "doubled_search_space": search_space(doubled),
        "verify_reason": doubled_why,
    }

    invariance = {
        "operation_reorderings": 0,
        "machine_relabellings": 0,
        "group_swaps": 0,
        "affine_job_relabellings": 0,
        "composed_transformations": 0,
    }
    transformed_answers_verified = 0
    unrelated_keys = []
    g8_failures = []
    for index in range(20):
        inst = make_instance(seed=10_000 + index, **shipping_params)
        key = canonical_key(inst)
        unrelated_keys.append(key)
        rng = random.Random(20_000 + index)

        reordered = _reorder_instance(inst, rng)
        if canonical_key(reordered) == key:
            invariance["operation_reorderings"] += 1
        else:
            g8_failures.append([index, "operation reordering changed key"])

        machine_relabelled = _relabel_machines(inst, rng)
        if canonical_key(machine_relabelled) == key:
            invariance["machine_relabellings"] += 1
        else:
            g8_failures.append([index, "machine relabelling changed key"])

        swapped_groups = _swap_groups(inst)
        if canonical_key(swapped_groups) == key:
            invariance["group_swaps"] += 1
        else:
            g8_failures.append([index, "group swap changed key"])

        units = [u for u in range(1, inst["n"])
                 if math.gcd(u, inst["n"]) == 1]
        unit = rng.choice(units)
        translation = rng.randrange(inst["n"])
        affine = _affine_relabel_jobs(inst, unit, translation)
        if canonical_key(affine) == key:
            invariance["affine_job_relabellings"] += 1
        else:
            g8_failures.append([index, "affine job relabelling changed key"])

        composed = _swap_groups(_relabel_machines(affine, rng))
        composed = _reorder_instance(composed, rng)
        if canonical_key(composed) == key:
            invariance["composed_transformations"] += 1
        else:
            g8_failures.append([index, "composed transformation changed key"])
        transformed_answers_verified += int(
            verify(composed, composed["answer"])[0]
        )

    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": (not g8_failures
                 and all(count == 20 for count in invariance.values())
                 and transformed_answers_verified == 20
                 and distinct_keys == 20),
        "invariance_counts": invariance,
        "transformed_answers_verified": transformed_answers_verified,
        "unrelated_distinct_keys": distinct_keys,
        "unrelated_instances": 20,
        "failures": g8_failures,
        "canonicalization": (
            "minimum incidence-set representation over machine permutations "
            "within groups, group swap, operation order, and affine automorphisms "
            "j -> u*j+t of Z_n"
        ),
    }

    answer_blob = json.dumps(planted, separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(planted)
    compact_operations = _compact_route_operations(shipping)
    arms = {name: dict(G9_ORACLE_RESULTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    within_caps = (answer_chars <= 2_000 and answer_elements <= 256
                   and compact_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact_operations,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    PROBLEM_PROFILE["max_answer_tokens"] = answer_tokens
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping_params)
    report["certificate_language"] = CERTIFICATE_LANGUAGE
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
