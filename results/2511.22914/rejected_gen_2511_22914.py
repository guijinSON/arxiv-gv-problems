"""Archived rejected Track-B generator for a native reconfiguration CSP family.

This implementation passes its local construction and verification gates, but
the required oracle hardening run solved it on 14 of 15 valid attempts through
four successive fixed-answer-size levels.  It is retained under the required
``rejected_gen_`` name as evidence; see REJECTED.md.

The paper arXiv:2511.22914 defines the solution graph of a CSP: its vertices
are satisfying assignments and adjacent assignments differ in one variable.
This module uses the Boolean min-closed relation LEQ={00,01,11}.  An instance
contains constraints x_u <= x_v, unary pins, and two satisfying assignments.

Generation samples a short modular-arithmetic progression of unpinned
variables first.  It makes that progression the unique legal order in which
those variables can change from the start assignment to the target, and only
then adds path-preserving constraints.  Thus the witness is known by inverse
generation, never by solving the completed instance.

The paper's Theorem 3.8 gives a polynomial greedy algorithm for every language
preserved by an ordered partial Maltsev operation.  On this implication-only
specialization, the stronger standard reference algorithm is a linear-time
topological elimination.  This is therefore explicitly Track B: the full
constraint scan is mechanical, while the intended no-tool route recognizes
the modular progression of the endpoint-difference variables.
"""

from __future__ import annotations

import copy
import hashlib
import heapq
import itertools
import json
import math
import os
import random
import re
import sys
import time
from collections import Counter


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # This finite Boolean family remains standard-library-only.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "logic",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "Boolean CSP formula over the min-closed relation LEQ",
        "two satisfying endpoint assignments",
    ],
    "verification_operations": [
        "exact Boolean assignment update",
        "unary pin comparison",
        "binary LEQ constraint comparison",
        "endpoint equality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The variables on which the endpoints differ form a modular arithmetic "
        "progression whose canonical smaller positive step gives the path; "
        "without that invariant one must eliminate the displayed implications."
    ),
    "hardness_basis": (
        "Track B: Theorem 3.8 gives O(n^2 m |D|^2) greedy descent, while this "
        "LEQ specialization admits Kahn topological elimination in O(n+m), "
        "measured at 4,051 counted operations and 0.000215 seconds in the "
        "recorded 11-run hard-preset median; "
        "the modular-progression route takes at most 166 exact operations "
        "over the 64-seed shipping audit, while "
        "the full constraint scan is not executable by hand in context."
    ),
    "max_answer_tokens": 15,
}

NATIVE = {
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


DIFFICULTY = {
    "demo": {"n": 11, "active_count": 4, "decoy_percent": 12},
    "easy": {"n": 37, "active_count": 10, "decoy_percent": 18},
    "medium": {"n": 73, "active_count": 12, "decoy_percent": 24},
    "hard": {"n": 131, "active_count": 12, "decoy_percent": 32},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The endpoint-difference indices form a modular arithmetic progression "
    "whose step is the smaller positive representative modulo the variable count."
)
PLACEBO_HINT = (
    "The endpoint assignments and grouped inequalities reward sustained "
    "attention to the variable indices and every displayed constraint direction."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list containing every endpoint-difference variable exactly "
        "once; its length is k and its entries are distinct indices in "
        "0,...,p-1.  The order is the proposed shortest reconfiguration path."
    ),
    "bounds": {
        "length": "k=active_count",
        "entry_minimum": 0,
        "entry_maximum": "p-1",
        "structural_rule": "a permutation of the endpoint-difference variables",
        "maximum_shipping_length": 12,
    },
}

NOTES = (
    "Definition 2.8 defines the solution graph by Hamming-distance-one moves, "
    "and Definition 2.9 fixes RCSP as connectivity between two supplied CSP "
    "solutions.  The generated relation LEQ={(0,0),(0,1),(1,1)} is min-closed; "
    "Lemma 3.13 therefore puts it under the ordered partial Maltsev operation. "
    "Lemma 3.7 proves unique local minima and monotone descent, and Theorem 3.8 "
    "states the O(n^2 m |D|^2) algorithm.  These results rule out Track A and "
    "justify Track B.  The construction samples a modular progression before "
    "the constraints, installs its consecutive LEQ constraints, and draws every "
    "other implication uniformly from the same set of path-preserving ordered "
    "pairs.  Pins make the nonmoving coordinates explicit.  Variable row order, "
    "successor order, and constraint order are shuffled.  The panel tests row "
    "position, per-variable degree, a static greedy score, a plausible but wrong "
    "affine ansatz, and random restarts.  The successful Kahn elimination is "
    "reported separately as the Track-B reference algorithm.  The compact route "
        "recovers the modular progression with its canonical smaller positive step, "
        "without reading the implication haystack or consulting the planted answer.  "
    "Shuffling defeats input-position rules; uniformly sampled path-preserving "
    "decoys obscure degree and static scores; a random modular step defeats the "
    "smallest-gap ansatz; and the forced chain leaves random restarts with exactly "
    "one successful permutation out of k!."
)


# These values are replaced with measurements from script-owned transcripts
# after the three hardening arms have run.  They never affect G9's gated cap.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted": {"solved": 0, "attempts": 0, "errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted_verdict": "infrastructure_blocked",
}


# ---------------------------------------------------------------------------
# Construction helpers.


def _is_prime(value):
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime(value):
    candidate = max(5, int(value))
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _validate_params(n, active_count, decoy_percent):
    if isinstance(n, bool) or not isinstance(n, int) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if isinstance(active_count, bool) or not isinstance(active_count, int):
        raise ValueError("active_count must be an integer")
    modulus = _next_prime(n)
    if not 4 <= active_count < modulus // 2:
        raise ValueError("active_count must be at least 4 and less than p/2")
    if isinstance(decoy_percent, bool) or not isinstance(decoy_percent, int):
        raise ValueError("decoy_percent must be an integer")
    if not 0 <= decoy_percent <= 60:
        raise ValueError("decoy_percent must lie between 0 and 60")
    if modulus > 4099:
        raise ValueError("n is too large for this explicit quadratic generator")
    return modulus


def _path_preserves_leq(kind_u, kind_v, rank_u, rank_v):
    """Whether x_u <= x_v holds throughout the planted decreasing path."""
    if kind_u == "fixed0":
        return True
    if kind_v == "fixed1":
        return True
    if kind_u == "fixed1":
        return kind_v == "fixed1"
    if kind_v == "fixed0":
        return kind_u == "fixed0"
    # Two active values start at one and become zero in increasing rank order.
    return rank_u < rank_v


def _display_rows(variable_count, implications, rng):
    outgoing = [[] for _ in range(variable_count)]
    for left, right in implications:
        outgoing[left].append(right)
    row_order = list(range(variable_count))
    rng.shuffle(row_order)
    rows = []
    for left in row_order:
        if not outgoing[left]:
            continue
        rights = list(outgoing[left])
        rng.shuffle(rights)
        rows.append([left, rights])
    return rows


def _incident_lists(variable_count, implications):
    incident = [[] for _ in range(variable_count)]
    for index, (left, right) in enumerate(implications):
        incident[left].append(index)
        incident[right].append(index)
    return incident


def make_instance(n, seed=0, active_count=12, decoy_percent=24, **params):
    """Inverse-generate a certified shortest LEQ-CSP reconfiguration path."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    modulus = _validate_params(n, active_count, decoy_percent)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)

    # Sample the witness before any constraint exists.
    while True:
        sampled_step = rng.randrange(2, modulus - 1)
        # This canonical orientation is visible in the variable labels once the
        # modular-progression invariant has been found.  It lets the compact
        # route determine the direction without scanning the constraint list.
        step = min(sampled_step, modulus - sampled_step)
        if step < 2:
            continue
        base = rng.randrange(modulus)
        path = [(base + index * step) % modulus for index in range(active_count)]
        if len(set(path)) != active_count:
            continue
        if path == sorted(path) or path == sorted(path, reverse=True):
            continue
        break

    active = set(path)
    active_rank = {variable: index for index, variable in enumerate(path)}
    kinds = []
    pin_values = {}
    for variable in range(modulus):
        if variable in active:
            kinds.append("active")
        else:
            value = rng.randrange(2)
            kinds.append("fixed1" if value else "fixed0")
            pin_values[variable] = value

    start = [pin_values.get(variable, 1) for variable in range(modulus)]
    target = [pin_values.get(variable, 0) for variable in range(modulus)]

    implications = set()
    for index in range(active_count - 1):
        implications.add((path[index], path[index + 1]))

    # All decoys are sampled uniformly from the path-preserving ordered pairs.
    for left in range(modulus):
        for right in range(modulus):
            if left == right or (left, right) in implications:
                continue
            if not _path_preserves_leq(
                kinds[left],
                kinds[right],
                active_rank.get(left),
                active_rank.get(right),
            ):
                continue
            if rng.randrange(100) < decoy_percent:
                implications.add((left, right))

    implication_list = [list(edge) for edge in implications]
    rng.shuffle(implication_list)
    pins = [[variable, pin_values[variable]] for variable in pin_values]
    rng.shuffle(pins)
    display_rows = _display_rows(modulus, implication_list, rng)

    return {
        "family": "min_closed_leq_rcsp_modular_path",
        "requested_n": n,
        "variable_count": modulus,
        "modulus": modulus,
        "active_count": active_count,
        "decoy_percent": decoy_percent,
        "pins": pins,
        "implications": implication_list,
        "start": start,
        "target": target,
        "display_rows": display_rows,
        "incident": _incident_lists(modulus, implication_list),
        "answer": path,
    }


# ---------------------------------------------------------------------------
# Statement, parser, and exact verifier.


def _ones(assignment):
    return [index for index, value in enumerate(assignment) if value]


def render(inst):
    variable_count = inst["variable_count"]
    pins0 = sorted(variable for variable, value in inst["pins"] if value == 0)
    pins1 = sorted(variable for variable, value in inst["pins"] if value == 1)
    rows = "\n".join(
        f"  x{left} <= " + ", ".join(f"x{right}" for right in rights)
        for left, rights in inst["display_rows"]
    )
    statement = f"""Shortest path in a Boolean reconfiguration CSP

There are {variable_count} Boolean variables x0,...,x{variable_count - 1};
their values are 0 or 1 with the usual order 0 < 1.  A pin xj=c requires xj
to equal c.  A displayed row

    xu <= xv, xw

abbreviates the two constraints xu <= xv and xu <= xw.  An assignment is a
solution exactly when it obeys every pin and every displayed inequality.

The solution graph has one vertex for every solution.  Two solutions are
adjacent exactly when they differ in the value of one variable.  A
reconfiguration path is a sequence of such single-variable changes in which
every intermediate assignment, including both endpoints, is a solution.

Pins at 0:
{json.dumps(pins0)}
Pins at 1:
{json.dumps(pins1)}

The start assignment has value 1 exactly at these 0-indexed variables and 0
at all others:
{json.dumps(_ones(inst['start']))}

The target assignment has value 1 exactly at these 0-indexed variables and 0
at all others:
{json.dumps(_ones(inst['target']))}

Inequality rows (row order and the order after <= carry no meaning):
{rows}

Output a shortest path using exactly {inst['active_count']} changes.  Write a
JSON list [v0,...,v{inst['active_count'] - 1}] of distinct 0-indexed variable
indices.  Starting at the start assignment, step i changes x_vi directly to
its target value.  Every listed variable must be one on which the endpoints
differ, every such variable must occur once, and every intermediate assignment
must satisfy all pins and inequalities.  Order matters; repeats are forbidden.

Give your final answer inside <answer></answer> tags, as one JSON list of
exactly {inst['active_count']} integers.
Example of the required syntax and length (not a claimed solution):
<answer>{json.dumps([-1] + list(range(inst['active_count'] - 1)))}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    if not match:
        return None
    payload = match.group(1).strip()
    payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
    payload = re.sub(r"\s*```$", "", payload)
    try:
        value = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value


def _changing_variables(inst):
    return [
        index
        for index, (start, target) in enumerate(zip(inst["start"], inst["target"]))
        if start != target
    ]


def verify(inst, answer):
    """Replay any proposed shortest path; never consult inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "path list is empty"
    expected = len(_changing_variables(inst))
    if len(answer) != expected:
        return False, f"path has {len(answer)} changes; expected exactly {expected}"
    if any(isinstance(value, bool) or not isinstance(value, int) for value in answer):
        return False, "every path entry must be an integer variable index"
    variable_count = inst["variable_count"]
    if any(value < 0 or value >= variable_count for value in answer):
        return False, f"variable index outside the inclusive range 0..{variable_count - 1}"
    if len(set(answer)) != len(answer):
        return False, "path repeats a variable index"
    changing = set(_changing_variables(inst))
    if set(answer) != changing:
        return False, "path entries are not exactly the endpoint-difference variables"

    values = list(inst["start"])
    pin_map = dict(inst["pins"])
    implications = inst["implications"]
    incident = inst.get("incident")
    if not isinstance(incident, list) or len(incident) != variable_count:
        incident = _incident_lists(variable_count, implications)
    for step_index, variable in enumerate(answer, 1):
        values[variable] = inst["target"][variable]
        if variable in pin_map and values[variable] != pin_map[variable]:
            return False, f"step {step_index} violates the pin on x{variable}"
        for edge_index in incident[variable]:
            left, right = implications[edge_index]
            if values[left] > values[right]:
                return (
                    False,
                    f"step {step_index} violates inequality x{left} <= x{right}",
                )
    if values != inst["target"]:
        return False, "replayed endpoint is not the target assignment"
    return True, "ok"


# ---------------------------------------------------------------------------
# Certificate language and algorithms.


def random_candidate(inst, rng):
    changing = _changing_variables(inst)
    return rng.sample(changing, len(changing))


def search_space(inst):
    return math.factorial(len(_changing_variables(inst)))


def enumerate_all(inst):
    changing = _changing_variables(inst)
    if len(changing) > 9:
        return None
    count = 0
    for candidate in itertools.permutations(changing):
        if verify(inst, list(candidate))[0]:
            count += 1
    return count


def _precedence_graph(inst):
    """Derive necessary orders for direct start-to-target changes."""
    changing = set(_changing_variables(inst))
    successors = {variable: set() for variable in changing}
    indegree = {variable: 0 for variable in changing}
    operations = inst["variable_count"]
    for left, right in inst["implications"]:
        operations += 1
        if left not in changing or right not in changing:
            continue
        start_left = inst["start"][left]
        start_right = inst["start"][right]
        target_left = inst["target"][left]
        target_right = inst["target"][right]
        # If changing right alone breaks LEQ, left must change first.
        if start_left > target_right:
            before, after = left, right
        # If changing left alone breaks LEQ, right must change first.
        elif target_left > start_right:
            before, after = right, left
        else:
            continue
        operations += 2
        if after not in successors[before]:
            successors[before].add(after)
            indegree[after] += 1
    return successors, indegree, operations


def _reference_algorithm(inst):
    """Specialized O(n+m) Kahn elimination; never reads the planted answer."""
    started = time.perf_counter()
    successors, indegree, operations = _precedence_graph(inst)
    available = [variable for variable, degree in indegree.items() if degree == 0]
    heapq.heapify(available)
    operations += len(indegree)
    path = []
    while available:
        variable = heapq.heappop(available)
        operations += 1
        path.append(variable)
        for successor in successors[variable]:
            indegree[successor] -= 1
            operations += 1
            if indegree[successor] == 0:
                heapq.heappush(available, successor)
                operations += 1
    if len(path) != len(indegree) or not verify(inst, path)[0]:
        return None, {
            "operations": operations,
            "wall_clock_sec": time.perf_counter() - started,
        }
    return path, {
        "operations": operations,
        "wall_clock_sec": time.perf_counter() - started,
    }


def _compact_route(inst):
    """Recover the canonically oriented progression; do not scan constraints."""
    started = time.perf_counter()
    active = set(_changing_variables(inst))
    modulus = inst["modulus"]
    operations = 0
    if len(active) < 3 or modulus != inst["variable_count"]:
        return None, {"operations": operations, "wall_clock_sec": 0.0}
    pivot = min(active)
    candidates = []
    for value in active:
        if value == pivot:
            continue
        candidates.append((value - pivot) % modulus)
        operations += 1
    scores = {}
    for step in candidates:
        score = 0
        for value in active:
            shifted = (value + step) % modulus
            operations += 1
            score += int(shifted in active)
        scores[step] = score
    best_score = max(scores.values())
    # A length-k modular progression overlaps itself in k-1 places after
    # translation by either signed common step.  The construction canonically
    # uses the smaller positive representative, which removes the reversal.
    best_steps = sorted(
        {min(step, modulus - step) for step, score in scores.items()
         if score == best_score}
    )
    for step in best_steps:
        starts = []
        for value in active:
            predecessor = (value - step) % modulus
            operations += 1
            if predecessor not in active:
                starts.append(value)
        if len(starts) != 1:
            continue
        sequence = [starts[0]]
        for _ in range(len(active) - 1):
            sequence.append((sequence[-1] + step) % modulus)
            operations += 1
        if set(sequence) != active:
            continue
        return sequence, {
            "operations": operations,
            "wall_clock_sec": time.perf_counter() - started,
        }
    return None, {
        "operations": operations,
        "wall_clock_sec": time.perf_counter() - started,
    }


def _fast_path_check(candidate, successors):
    """Exact precedence check after successors were derived from the instance."""
    position = {variable: index for index, variable in enumerate(candidate)}
    return all(
        position[before] < position[after]
        for before, afters in successors.items()
        for after in afters
    )


# ---------------------------------------------------------------------------
# Canonicalization and genuine relabellings.


def _wl_encoding(start, target, implications):
    variable_count = len(start)
    outgoing = [[] for _ in range(variable_count)]
    incoming = [[] for _ in range(variable_count)]
    for left, right in implications:
        outgoing[left].append(right)
        incoming[right].append(left)
    base_signatures = [(start[v], target[v]) for v in range(variable_count)]
    palette = {
        signature: index for index, signature in enumerate(sorted(set(base_signatures)))
    }
    colors = [palette[signature] for signature in base_signatures]
    signatures = []
    # Directed 1-WL refinement to stabilization is a cheap isomorphism
    # invariant.  It normally individualizes these random instances; the
    # fallback below remains explicit because 1-WL is not a full GI solver.
    for _round in range(variable_count):
        old_class_count = len(set(colors))
        width = max(colors) + 1
        signatures = []
        for vertex in range(variable_count):
            out_counts = [0] * width
            in_counts = [0] * width
            for neighbor in outgoing[vertex]:
                out_counts[colors[neighbor]] += 1
            for neighbor in incoming[vertex]:
                in_counts[colors[neighbor]] += 1
            signatures.append(
                (colors[vertex], tuple(out_counts), tuple(in_counts))
            )
        unique_signatures = sorted(set(signatures))
        refined_palette = {
            signature: index for index, signature in enumerate(unique_signatures)
        }
        refined = [refined_palette[signature] for signature in signatures]
        colors = refined
        # Refinement never merges classes.  Equal class counts therefore mean
        # the partition is stable even if its canonical integer labels changed.
        if len(unique_signatures) == old_class_count:
            break

    if len(set(colors)) == variable_count:
        order = sorted(range(variable_count), key=lambda vertex: colors[vertex])
        renaming = {vertex: index for index, vertex in enumerate(order)}
        payload = {
            "status": [[start[v], target[v]] for v in order],
            "edges": sorted([renaming[left], renaming[right]] for left, right in implications),
        }
    else:
        # A strongest-cheap-invariant fallback for the unlikely non-discrete WL
        # partition.  The README states that this is not a full GI algorithm.
        edge_colors = Counter((colors[left], colors[right]) for left, right in implications)
        payload = {
            "color_status": sorted(
                (colors[v], start[v], target[v]) for v in range(variable_count)
            ),
            "edge_color_counts": sorted(
                [left, right, count] for (left, right), count in edge_colors.items()
            ),
            "vertex_signatures": sorted(signatures),
        }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def canonical_key(inst):
    start = list(inst["start"])
    target = list(inst["target"])
    edges = [tuple(edge) for edge in inst["implications"]]
    # RCSP reachability is symmetric in its endpoints, and complementing the
    # Boolean domain carries x<=y to (1-y)<=(1-x).  Minimize over both genuine
    # symmetries; _wl_encoding handles arbitrary variable relabellings.
    variants = [
        (start, target, edges),
        (target, start, edges),
        (
            [1 - value for value in start],
            [1 - value for value in target],
            [(right, left) for left, right in edges],
        ),
        (
            [1 - value for value in target],
            [1 - value for value in start],
            [(right, left) for left, right in edges],
        ),
    ]
    canonical = min(_wl_encoding(s, t, e) for s, t, e in variants)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _refresh_derived(inst):
    inst["incident"] = _incident_lists(inst["variable_count"], inst["implications"])
    local_rng = random.Random(0)
    inst["display_rows"] = _display_rows(
        inst["variable_count"], inst["implications"], local_rng
    )
    return inst


def _relabel_variables(inst, permutation):
    """Carry the full instance and witness through old-index -> new-index."""
    variable_count = inst["variable_count"]
    if sorted(permutation) != list(range(variable_count)):
        raise ValueError("permutation is not a variable relabelling")
    transformed = copy.deepcopy(inst)
    start = [0] * variable_count
    target = [0] * variable_count
    for old, new in enumerate(permutation):
        start[new] = inst["start"][old]
        target[new] = inst["target"][old]
    transformed["start"] = start
    transformed["target"] = target
    transformed["pins"] = [[permutation[v], value] for v, value in inst["pins"]]
    transformed["implications"] = [
        [permutation[left], permutation[right]]
        for left, right in inst["implications"]
    ]
    transformed["answer"] = [permutation[v] for v in inst["answer"]]
    return _refresh_derived(transformed)


def _reorder_constraints(inst, rng):
    transformed = copy.deepcopy(inst)
    rng.shuffle(transformed["pins"])
    rng.shuffle(transformed["implications"])
    transformed["answer"] = list(inst["answer"])
    return _refresh_derived(transformed)


def _complement_domain(inst):
    """Use x<=y iff (1-y)<=(1-x), carrying the same move indices."""
    transformed = copy.deepcopy(inst)
    transformed["start"] = [1 - value for value in inst["start"]]
    transformed["target"] = [1 - value for value in inst["target"]]
    transformed["pins"] = [[v, 1 - value] for v, value in inst["pins"]]
    transformed["implications"] = [
        [right, left] for left, right in inst["implications"]
    ]
    transformed["answer"] = list(inst["answer"])
    return _refresh_derived(transformed)


def _swap_endpoints(inst):
    """Exchange endpoints and carry the witness by reversing the path."""
    transformed = copy.deepcopy(inst)
    transformed["start"] = list(inst["target"])
    transformed["target"] = list(inst["start"])
    transformed["answer"] = list(reversed(inst["answer"]))
    return _refresh_derived(transformed)


# ---------------------------------------------------------------------------
# Adversary panel.


def _candidate_from_order(active, scored):
    return [variable for _score, variable in sorted(scored)]


def _attack_input_position(inst):
    active = set(_changing_variables(inst))
    candidate = [left for left, _rights in inst["display_rows"] if left in active]
    for variable in sorted(active):
        if variable not in candidate:
            candidate.append(variable)
    return verify(inst, candidate)[0]


def _attack_outlier_degree(inst):
    active = _changing_variables(inst)
    degrees = Counter()
    for left, right in inst["implications"]:
        degrees[left] += 1
        degrees[right] += 1
    candidate = _candidate_from_order(active, [(-degrees[v], v) for v in active])
    return verify(inst, candidate)[0]


def _attack_static_greedy(inst):
    active = _changing_variables(inst)
    active_set = set(active)
    score = Counter()
    for left, right in inst["implications"]:
        if left in active_set:
            score[left] += 1
        if right in active_set:
            score[right] -= 1
    candidate = _candidate_from_order(active, [(-score[v], v) for v in active])
    return verify(inst, candidate)[0]


def _attack_obvious_affine(inst):
    active = sorted(_changing_variables(inst))
    modulus = inst["modulus"]
    pivot = active[0]
    step = min((value - pivot) % modulus for value in active[1:])
    candidate = []
    current = pivot
    active_set = set(active)
    while current in active_set and current not in candidate:
        candidate.append(current)
        current = (current + step) % modulus
    candidate.extend(value for value in active if value not in candidate)
    return verify(inst, candidate)[0]


def _attack_random_restart(inst, seed, restarts=256):
    rng = random.Random(seed ^ int(canonical_key(inst)[:16], 16))
    for _ in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _answer_atoms(answer):
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def escalate(params):
    if not isinstance(params, dict):
        return None
    current_n = int(params.get("n", DIFFICULTY[SHIPPING_DIFFICULTY]["n"]))
    current_modulus = _next_prime(current_n)
    current_decoys = int(params.get("decoy_percent", 24))
    harder_n = _next_prime(2 * _next_prime(current_n) + 1)
    if harder_n > 4099:
        if current_modulus < 4099:
            harder_n = 4099
        elif current_decoys < 60:
            harder_n = current_modulus
        else:
            return None
    return {
        "n": harder_n,
        "active_count": int(params.get("active_count", 12)),
        "decoy_percent": min(60, current_decoys + 3),
    }


# ---------------------------------------------------------------------------
# Mandatory gates.


def selftest():
    report = {}
    shipping_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    shipping = make_instance(seed=872341, **shipping_params)

    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (3, 19, 101):
            attempts += 1
            instance = make_instance(seed=seed, **params)
            ok, reason = verify(instance, instance["answer"])
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(instance["answer"])) != instance["answer"]:
                failures.append(
                    {"preset": preset, "seed": seed, "reason": "answer is not JSON-native"}
                )
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
    }

    planted = list(shipping["answer"])
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two": [planted[1], planted[0]] + planted[2:],
        "duplicate": [planted[0], planted[0]] + planted[2:],
        "empty": [],
        "out_of_range": [shipping["variable_count"]] + planted[1:],
    }
    corruption_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        accepted, reason = verify(shipping, candidate)
        corruption_results[name] = {"accepted": accepted, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(not result["accepted"] for result in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The decreasing path is forced by the inequalities.\n```json\n"
        "<answer>\n"
        + json.dumps(shipping["answer"])
        + "\n</answer>\n```\n"
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == shipping["answer"] and verify(shipping, parsed)[0],
        "parsed_exactly": parsed == shipping["answer"],
    }

    sample_total = 200_000
    sample_hits = 0
    sample_rng = random.Random(604211)
    sample_successors, _sample_indegree, _sample_operations = _precedence_graph(
        shipping
    )
    sample_started = time.perf_counter()
    for _ in range(sample_total):
        candidate = random_candidate(shipping, sample_rng)
        if _fast_path_check(candidate, sample_successors):
            # Full replay confirms every sampled hit; the fast predicate itself
            # is exactly the implication precedence relation.
            if not verify(shipping, candidate)[0]:
                raise AssertionError("fast precedence check disagrees with verify")
            sample_hits += 1
    sample_wall = time.perf_counter() - sample_started
    observed_probability = sample_hits / sample_total
    exact_probability = 1 / search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": observed_probability < 1e-6 and exact_probability < 1e-6,
        "hits": sample_hits,
        "total": sample_total,
        "observed_probability": observed_probability,
        "construction_proven_valid_answers": 1,
        "exact_probability": exact_probability,
        "certificate_space": search_space(shipping),
        "wall_clock_sec": round(sample_wall, 6),
    }

    # Report a short median rather than a noisy single sub-millisecond timing.
    reference_trials = [_reference_algorithm(shipping) for _ in range(11)]
    reference_answer = reference_trials[0][0]
    reference_stats = dict(reference_trials[0][1])
    reference_stats["wall_clock_sec"] = sorted(
        stats["wall_clock_sec"] for _answer, stats in reference_trials
    )[len(reference_trials) // 2]
    compact_answer, compact_stats = _compact_route(shipping)
    compact_route_failures = []
    compact_route_max_operations = compact_stats["operations"]
    for seed in range(64):
        compact_instance = make_instance(seed=12000 + seed, **shipping_params)
        compact_candidate, compact_seed_stats = _compact_route(compact_instance)
        compact_route_max_operations = max(
            compact_route_max_operations, compact_seed_stats["operations"]
        )
        if compact_candidate is None or not verify(
            compact_instance, compact_candidate
        )[0]:
            compact_route_failures.append(seed)
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": (
            demo_count == 1
            and reference_answer is not None
            and verify(shipping, reference_answer)[0]
            and compact_answer is not None
            and verify(shipping, compact_answer)[0]
            and not compact_route_failures
        ),
        "shipping_density_hits": sample_hits,
        "shipping_density_samples": sample_total,
        "shipping_sampled_valid_fraction": observed_probability,
        "shipping_construction_proven_solution_count": 1,
        "shipping_exact_fraction": exact_probability,
        "demo_exact_solution_count": demo_count,
        "demo_certificate_space": search_space(demo),
        "reference_algorithm_operations": reference_stats["operations"],
        "reference_algorithm_wall_clock_sec": round(
            reference_stats["wall_clock_sec"], 6
        ),
        "compact_route_operations": compact_stats["operations"],
        "compact_route_max_operations_64_seeds": compact_route_max_operations,
        "compact_route_failures_64_seeds": compact_route_failures,
        "compact_route_wall_clock_sec": round(compact_stats["wall_clock_sec"], 6),
    }

    attack_names = (
        "input_row_position",
        "outlier_total_degree",
        "greedy_static_constraint_score",
        "obvious_smallest_gap_affine_ansatz",
        "random_restart_256",
    )
    successes = {name: 0 for name in attack_names}
    reference_runs = []
    for seed in range(310, 318):
        attacked = make_instance(seed=seed, **shipping_params)
        successes["input_row_position"] += int(_attack_input_position(attacked))
        successes["outlier_total_degree"] += int(_attack_outlier_degree(attacked))
        successes["greedy_static_constraint_score"] += int(
            _attack_static_greedy(attacked)
        )
        successes["obvious_smallest_gap_affine_ansatz"] += int(
            _attack_obvious_affine(attacked)
        )
        successes["random_restart_256"] += int(
            _attack_random_restart(attacked, seed)
        )
        found, stats = _reference_algorithm(attacked)
        stats["solved"] = bool(found is not None and verify(attacked, found)[0])
        reference_runs.append(stats)
    attacks = {
        name: {"successes": count, "attempts": 8}
        for name, count in successes.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attacks.values())
        and all(run["solved"] for run in reference_runs),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "implication precedence extraction plus Kahn elimination",
            "complexity": "O(n+m) exact Boolean/set operations",
            "operations": reference_stats["operations"],
            "max_operations": max(run["operations"] for run in reference_runs),
            "wall_clock_sec": round(reference_stats["wall_clock_sec"], 6),
            "max_wall_clock_sec": round(
                max(run["wall_clock_sec"] for run in reference_runs), 6
            ),
            "solves": f"{sum(run['solved'] for run in reference_runs)}/8, as expected",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] = _next_prime(2 * shipping["variable_count"] + 1)
    doubled = make_instance(seed=991, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    _doubled_answer, doubled_reference = _reference_algorithm(doubled)
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["variable_count"] > shipping["variable_count"]
        and doubled_reference["operations"] > reference_stats["operations"],
        "shipping_n": shipping["variable_count"],
        "doubled_n": doubled["variable_count"],
        "doubled_verify_reason": doubled_reason,
        "answer_length_unchanged": len(doubled["answer"]) == len(shipping["answer"]),
        "shipping_reference_operations": reference_stats["operations"],
        "doubled_reference_operations": doubled_reference["operations"],
    }

    invariance_checks = 0
    carried_checks = 0
    key_failures = []
    unrelated_keys = set()
    canonical_params = dict(DIFFICULTY["easy"])
    for seed in range(20):
        instance = make_instance(seed=8000 + seed, **canonical_params)
        base_key = canonical_key(instance)
        unrelated_keys.add(base_key)
        rng = random.Random(9000 + seed)
        permutation = list(range(instance["variable_count"]))
        rng.shuffle(permutation)
        relabelled = _relabel_variables(instance, permutation)
        reordered = _reorder_constraints(instance, rng)
        composed = _reorder_constraints(relabelled, rng)
        complemented = _complement_domain(instance)
        swapped = _swap_endpoints(instance)
        complement_swapped = _complement_domain(swapped)
        relabel_complement = _relabel_variables(complemented, permutation)
        fully_composed = _reorder_constraints(
            _relabel_variables(complement_swapped, permutation), rng
        )
        variants = [
            relabelled,
            reordered,
            composed,
            complemented,
            swapped,
            complement_swapped,
            relabel_complement,
            fully_composed,
        ]
        for variant in variants:
            invariance_checks += 1
            if canonical_key(variant) != base_key:
                key_failures.append({"seed": seed, "kind": "key_invariance"})
            carried_checks += 1
            if not verify(variant, variant["answer"])[0]:
                key_failures.append({"seed": seed, "kind": "carried_witness"})
    report["G8_canonical_key"] = {
        "pass": not key_failures and len(unrelated_keys) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated": len(unrelated_keys),
        "unrelated_attempts": 20,
        "transformations": [
            "arbitrary variable relabelling",
            "pin and implication reordering",
            "composed relabelling and reordering",
            "Boolean complementation with inequality reversal",
            "endpoint exchange with path reversal",
            "complementation composed with endpoint exchange",
            "relabeling composed with complementation",
            "relabeling, reordering, complementation, and endpoint exchange",
        ],
        "failures": key_failures,
    }

    # Exact worst case: the k largest legal indices maximize decimal width.
    worst_answer = list(
        range(
            shipping["variable_count"] - shipping["active_count"],
            shipping["variable_count"],
        )
    )
    answer_chars = len(json.dumps(worst_answer))
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    arms = copy.deepcopy(G9_ORACLE_RESULTS)
    hinted_verdict = arms.pop("hinted_verdict", "not_run")
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = (
        placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    )
    compact_ok = (
        compact_answer is not None
        and verify(shipping, compact_answer)[0]
        and not compact_route_failures
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and compact_route_max_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        # Since 2026-09-05 the oracle arms are diagnostic only.  The sole gate
        # here is the answer/route cap in part (c).
        "pass": within_caps and compact_ok,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": hinted_verdict,
        "arms_recorded_not_gated": True,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact_route_max_operations,
        "intended_route_samples": 64,
        "intended_route_failures": compact_route_failures,
        "intended_route_verified": compact_ok,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping_params
    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
