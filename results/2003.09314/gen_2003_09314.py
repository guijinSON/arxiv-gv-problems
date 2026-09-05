"""Verified graph-burning problem generator for arXiv:2003.09314.

The solver receives a path forest by its component orders, exactly the compact
representation used for path forests in the graph-burning literature cited by
the paper.  A certificate assigns each final-time fire-ball radius to one
component.  The checker expands that assignment into a concrete burning
sequence and replays the interval coverage and unburned-source constraints.

Generation is by composition of identities.  The odd ball sizes
1,3,...,2k-1 sum to k^2; whole residue classes of radius indices are bundled
into components and their exact odd-size sums become the component orders.
Those paths therefore come with a burning certificate before their
presentation order is shuffled.
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
except ImportError:  # This family uses only standard-library integer arithmetic.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "subset_sum",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "path forest represented by its component orders",
        "ordered graph-burning fire-ball radii",
        "compressed burning sequence",
    ],
    "verification_operations": [
        "exact integer interval endpoints",
        "exact component-length sums",
        "exact graph-distance comparisons within paths",
        "exact replay of fire-ball coverage",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "decomposition",
    "intuition_description": (
        "Radii in one congruence class modulo t+4 stay together, reducing the "
        "large fixed-bin partition to matching singleton and paired residue "
        "classes; without that invariant one must partition every radius."
    ),
    "hardness_basis": (
        "Track B: Section 1 cites the polynomial algorithm for path forests "
        "with a fixed number of components (Algorithm 15 of Bessy et al., "
        "O(t*m^t)); at the easy shipping preset the executable memoized "
        "fixed-bin specialization solved 8/8 seeds with median 54,107 nodes, "
        "331,076 operations, and 0.104 seconds (2,363,676 operations total), "
        "while the residue-class route uses 231 exact operations."
    ),
    "max_answer_tokens": 30,
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
    "demo": {
        "n": 9,
        "components": 4,
        "filter_min_nodes": 0,
        "filter_max_nodes": 0,
        "random_restarts": 4,
    },
    "easy": {
        "n": 37,
        "components": 8,
        "filter_min_nodes": 5_000,
        "filter_max_nodes": 250_000,
        "random_restarts": 32,
    },
    "medium": {
        "n": 45,
        "components": 8,
        "filter_min_nodes": 15_000,
        "filter_max_nodes": 500_000,
        "random_restarts": 64,
    },
    "hard": {
        "n": 53,
        "components": 8,
        "filter_min_nodes": 40_000,
        "filter_max_nodes": 800_000,
        "random_restarts": 128,
    },
}

SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Radii congruent modulo t+4 are never split between different components."
)
PLACEBO_HINT = (
    "The component lengths and radius indices reward consistently careful bookkeeping."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON array of t nonempty arrays; array c is a strictly increasing "
        "list of radius indices assigned to displayed component c, and together "
        "the arrays partition every integer from 0 through k-1 exactly once."
    ),
    "bounds": {
        "groups": "components=t",
        "total_radius_indices": "n=k",
        "radius_min": 0,
        "radius_max_inclusive": "k-1",
        "max_atomic_elements": 120,
    },
}

# Filled after the script-owned bare/hinted/placebo runs.  These arms are
# diagnostic only; the G9 gate below is the answer/operation cap.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 3, "attempts": 3},
    "hinted": {"solved": 3, "attempts": 3},
    "placebo": {"solved": 3, "attempts": 3},
    "hinted_verdict": "too_easy",
}

NOTES = """\
Section 1 fixes the native definition: in round i a fresh unburned vertex is
ignited, old fires spread one edge per round, and a length-k sequence is valid
exactly when its radius-(k-i) closed neighborhoods cover the graph while later
sources were not already burned.  The same section is decisive at Step 0: it
says Graph Burning is NP-complete even on path forests, but also says the
number is polynomial-time computable when the number of components is fixed.
This family fixes that number, so it is Track B and not an average-case Track A
claim.  The cited path-forest algorithm is Algorithm 15 of Bessy et al.; its
bound is O(t*m^t).

The generator uses the paper's native path-forest objects.  It first groups
the radii 0,...,k-1 by residues modulo q=t+4, randomly pairs q-t residue
classes and leaves the rest single, and makes each resulting exact odd-size
sum a component order.  Shuffling components carries this planted symbolic
schedule through a graph isomorphism.  Candidate instances are retained only
when length-rank, two residual greedy rules, randomized greedy restarts, and
affine-modulo ansatzes fail; the retained certificate remains the original
residue grouping.  A memoized exact fixed-bin solver is run only to measure
and condition mechanical cost, never to obtain the answer.  Verification
independently expands any submitted radius partition into interval centers
and checks source separation and exact cover.

The script-owned hardening run tested 21 independent oracle calls over the
three named presets and four fixed-length escalations.  Every call returned a
verified witness, including the final k=53, t=11 level.  The harness returned
budget_bound because escalate() still offered another conditioned level after
its six-escalation budget.  This is therefore a parked family, not a hardened
release and not a Track-A hardness claim.  At the provisional easy rung the
isolated G9 runs were 3/3 solved with the structural hint and 3/3 with the
placebo, so the measured hinted-minus-placebo effect is zero.
"""


_TAG_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_CAP = object()


def _mix_seed(seed: int, nonce: int) -> int:
    x = (int(seed) & ((1 << 64) - 1)) ^ 0x200309314C0FFEE
    x = (x + (nonce + 1) * 0x9E3779B97F4A7C15) & ((1 << 128) - 1)
    x ^= x >> 30
    x *= 0xBF58476D1CE4E5B9
    x ^= x >> 27
    x *= 0x94D049BB133111EB
    x ^= x >> 31
    return x & ((1 << 128) - 1)


def _valid_shape_quick(inst: dict, answer: object) -> bool:
    if not isinstance(answer, list) or len(answer) != inst["components"]:
        return False
    flat: list[int] = []
    for group in answer:
        if not isinstance(group, list) or not group:
            return False
        if any(not isinstance(r, int) or isinstance(r, bool) for r in group):
            return False
        if group != sorted(group) or len(group) != len(set(group)):
            return False
        flat.extend(group)
    return sorted(flat) == list(range(inst["k"]))


def _assignment_valid(inst: dict, answer: object) -> bool:
    if not _valid_shape_quick(inst, answer):
        return False
    assert isinstance(answer, list)
    return all(
        sum(2 * radius + 1 for radius in group) == inst["lengths"][component]
        for component, group in enumerate(answer)
    )


def _groups_from_choices(k: int, components: int, choices: list[int]) -> list[list[int]]:
    groups: list[list[int]] = [[] for _ in range(components)]
    for radius, component in enumerate(choices):
        if 0 <= component < components:
            groups[component].append(radius)
    return groups


def _residue_class_certificate(inst: dict) -> tuple[list[list[int]] | None, int]:
    """Recover the singleton/pair residue decomposition from public data."""
    k = inst["k"]
    t = inst["components"]
    modulus = t + 4
    if modulus > k:
        return None, 0
    class_radii = [list(range(residue, k, modulus)) for residue in range(modulus)]
    class_weights = [0] * modulus
    operations = 0
    for residue, radii in enumerate(class_radii):
        for radius in radii:
            class_weights[residue] += 2 * radius + 1
            operations += 1

    by_sum: dict[int, list[tuple[int, ...]]] = {}
    for residue, weight in enumerate(class_weights):
        by_sum.setdefault(weight, []).append((residue,))
        operations += 1
    for left in range(modulus):
        for right in range(left + 1, modulus):
            total = class_weights[left] + class_weights[right]
            by_sum.setdefault(total, []).append((left, right))
            operations += 1

    options = [by_sum.get(length, []) for length in inst["lengths"]]
    if any(not row for row in options):
        return None, operations
    chosen: list[tuple[int, ...] | None] = [None] * t

    def search(used_mask: int, remaining_components: tuple[int, ...]) -> bool:
        nonlocal operations
        if not remaining_components:
            return used_mask == (1 << modulus) - 1
        best_component = -1
        best_options: list[tuple[int, ...]] | None = None
        for component in remaining_components:
            feasible: list[tuple[int, ...]] = []
            for residues in options[component]:
                operations += 1
                mask = sum(1 << residue for residue in residues)
                if mask & used_mask == 0:
                    feasible.append(residues)
            if not feasible:
                return False
            if best_options is None or len(feasible) < len(best_options):
                best_component = component
                best_options = feasible
        assert best_options is not None
        tail = tuple(c for c in remaining_components if c != best_component)
        for residues in best_options:
            mask = sum(1 << residue for residue in residues)
            chosen[best_component] = residues
            if search(used_mask | mask, tail):
                return True
        chosen[best_component] = None
        return False

    if not search(0, tuple(range(t))):
        return None, operations
    groups: list[list[int]] = [[] for _ in range(t)]
    for component, residues in enumerate(chosen):
        assert residues is not None
        groups[component] = sorted(
            radius for residue in residues for radius in class_radii[residue]
        )
        operations += len(groups[component])
    return groups, operations


def _attack_length_rank_blocks(inst: dict) -> list[list[int]] | None:
    """Outlier probe: match equal-count radius bands to length ranks."""
    k = inst["k"]
    t = inst["components"]
    quotient, extra = divmod(k, t)
    points = [0]
    for i in range(t):
        points.append(points[-1] + quotient + int(i < extra))
    blocks = [list(range(points[i], points[i + 1])) for i in range(t)]
    blocks.sort(key=lambda g: sum(2 * radius + 1 for radius in g))
    components = sorted(range(t), key=lambda c: (inst["lengths"][c], c))
    answer: list[list[int]] = [[] for _ in range(t)]
    for component, block in zip(components, blocks):
        answer[component] = block
    return answer


def _attack_residual_greedy(inst: dict, tightest: bool) -> list[list[int]] | None:
    remaining = list(inst["lengths"])
    groups: list[list[int]] = [[] for _ in remaining]
    for radius in range(inst["k"] - 1, -1, -1):
        weight = 2 * radius + 1
        options = [c for c, value in enumerate(remaining) if value >= weight]
        if not options:
            return None
        if tightest:
            component = min(options, key=lambda c: (remaining[c] - weight, c))
        else:
            component = max(options, key=lambda c: (remaining[c], -c))
        remaining[component] -= weight
        groups[component].append(radius)
    for group in groups:
        group.sort()
    return groups if not any(remaining) else None


def _attack_random_greedy(
    inst: dict, rng: random.Random, restarts: int
) -> tuple[list[list[int]] | None, int]:
    steps = 0
    for _ in range(restarts):
        remaining = list(inst["lengths"])
        groups: list[list[int]] = [[] for _ in remaining]
        for radius in range(inst["k"] - 1, -1, -1):
            steps += 1
            weight = 2 * radius + 1
            options = [c for c, value in enumerate(remaining) if value >= weight]
            if not options:
                break
            options.sort(key=lambda c: (remaining[c] - weight, c))
            component = rng.choice(options[: min(3, len(options))])
            remaining[component] -= weight
            groups[component].append(radius)
        else:
            if not any(remaining):
                for group in groups:
                    group.sort()
                return groups, steps
    return None, steps


def _attack_affine_modulo(inst: dict) -> tuple[list[list[int]] | None, int]:
    """By-hand ansatz: component classes are affine residues modulo t."""
    k = inst["k"]
    t = inst["components"]
    attempts = 0
    for multiplier in range(1, t):
        if math.gcd(multiplier, t) != 1:
            continue
        for shift in range(t):
            attempts += 1
            choices = [(multiplier * radius + shift) % t for radius in range(k)]
            answer = _groups_from_choices(k, t, choices)
            if _assignment_valid(inst, answer):
                return answer, attempts * k
    return None, attempts * k


def _reference_fixed_bin_dp(
    inst: dict, node_cap: int | None = None
) -> tuple[list[list[int]] | None | object, int, int]:
    """Memoized exact assignment, polynomial when component count is fixed.

    The state is (next radius, remaining component orders).  Its worst-case
    count is at most k*product(L_c+1), which is polynomial in the expanded
    path-forest order for fixed t, matching the regime of the paper's cited
    path-forest algorithm.  `_CAP` means the explicit measurement cap fired.
    """
    k = inst["k"]
    t = inst["components"]
    memo: set[tuple[int, tuple[int, ...]]] = set()
    nodes = 0
    operations = 0

    def dfs(radius: int, remaining: tuple[int, ...]) -> list[int] | None | object:
        nonlocal nodes, operations
        nodes += 1
        if node_cap is not None and nodes > node_cap:
            return _CAP
        if radius < 0:
            return [] if not any(remaining) else None
        key = (radius, remaining)
        if key in memo:
            return None
        weight = 2 * radius + 1
        seen_residuals: set[int] = set()
        order = sorted(range(t), key=lambda c: (remaining[c], c))
        for component in order:
            operations += 1
            residual = remaining[component]
            if residual < weight or residual in seen_residuals:
                continue
            seen_residuals.add(residual)
            changed = list(remaining)
            changed[component] -= weight
            result = dfs(radius - 1, tuple(changed))
            if result is _CAP:
                return _CAP
            if isinstance(result, list):
                return result + [component]
        memo.add(key)
        return None

    choices = dfs(k - 1, tuple(inst["lengths"]))
    if choices is _CAP or choices is None:
        return choices, nodes, operations
    assert isinstance(choices, list) and len(choices) == k
    return _groups_from_choices(k, t, choices), nodes, operations


def _raw_instance(n: int, components: int, seed: int, nonce: int) -> dict:
    rng = random.Random(_mix_seed(seed, nonce))
    modulus = components + 4
    classes = [list(range(residue, n, modulus)) for residue in range(modulus)]
    class_ids = list(range(modulus))
    rng.shuffle(class_ids)
    bundles: list[list[int]] = []
    for pair in range(4):
        bundles.append(class_ids[2 * pair : 2 * pair + 2])
    bundles.extend([[class_ids[index]] for index in range(8, modulus)])
    normalized_bundles = bundles
    blocks = [
        sorted(radius for residue in bundle for radius in classes[residue])
        for bundle in normalized_bundles
    ]
    lengths = [sum(2 * radius + 1 for radius in block) for block in blocks]
    order = list(range(components))
    rng.shuffle(order)
    shown_lengths = [lengths[old] for old in order]
    answer = [blocks[old] for old in order]
    return {
        "paper": "arXiv:2003.09314",
        "family": "compressed burning certificate for a path forest",
        "k": n,
        "n": n,
        "components": components,
        "residue_modulus": modulus,
        "lengths": shown_lengths,
        "order": n * n,
        "answer": answer,
    }


def _passes_filter(
    inst: dict,
    seed: int,
    nonce: int,
    filter_min_nodes: int,
    filter_max_nodes: int,
    random_restarts: int,
) -> tuple[bool, dict[str, int | float]]:
    compact, compact_operations = _residue_class_certificate(inst)
    if (
        compact is None
        or compact_operations > 300
        or not _assignment_valid(inst, compact)
    ):
        return False, {}
    if filter_min_nodes <= 0:
        return True, {"nodes": 0, "operations": 0, "wall_clock_sec": 0.0}
    cheap = [
        _attack_length_rank_blocks(inst),
        _attack_residual_greedy(inst, True),
        _attack_residual_greedy(inst, False),
    ]
    if any(candidate is not None and _assignment_valid(inst, candidate) for candidate in cheap):
        return False, {}
    # This stream is replayed by G6, so the on-disk panel is reproducible.
    for salt in range(1):
        random_answer, _ = _attack_random_greedy(
            inst,
            random.Random(_mix_seed((seed ^ 0xA77AC) + salt, nonce)),
            random_restarts,
        )
        if random_answer is not None and _assignment_valid(inst, random_answer):
            return False, {}
    affine, _ = _attack_affine_modulo(inst)
    if affine is not None and _assignment_valid(inst, affine):
        return False, {}
    start = time.perf_counter()
    reference, nodes, operations = _reference_fixed_bin_dp(inst, filter_max_nodes)
    wall = time.perf_counter() - start
    if reference is _CAP or reference is None:
        return False, {}
    if nodes < filter_min_nodes or not _assignment_valid(inst, reference):
        return False, {}
    return True, {
        "nodes": nodes,
        "operations": operations,
        "wall_clock_sec": wall,
    }


def make_instance(
    n: int,
    seed: int = 0,
    components: int = 8,
    filter_min_nodes: int = 0,
    filter_max_nodes: int = 0,
    random_restarts: int = 64,
    **params: Any,
) -> dict:
    """Construct a certified path forest without solving the output instance."""
    del params
    if not isinstance(n, int) or isinstance(n, bool) or n < 3:
        raise ValueError("n must be an integer at least 3")
    if n > 120:
        raise ValueError("n>120 exceeds this family's declared answer language")
    if not isinstance(components, int) or not 4 <= components < n:
        raise ValueError("components must be an integer in [4,n)")
    if filter_min_nodes < 0 or filter_max_nodes < 0 or random_restarts < 0:
        raise ValueError("filter and restart counts must be nonnegative")
    if filter_min_nodes and filter_max_nodes <= filter_min_nodes:
        raise ValueError("filter_max_nodes must exceed filter_min_nodes")

    max_candidates = 2_048
    for nonce in range(max_candidates):
        inst = _raw_instance(n, components, seed, nonce)
        passed, metrics = _passes_filter(
            inst,
            seed,
            nonce,
            filter_min_nodes,
            filter_max_nodes,
            random_restarts,
        )
        if passed:
            inst["filter_min_nodes"] = filter_min_nodes
            inst["filter_max_nodes"] = filter_max_nodes
            inst["random_restarts"] = random_restarts
            inst["selection_attempts"] = nonce + 1
            inst["selection_nonce"] = nonce
            inst["reference_filter_metrics"] = {
                "nodes": int(metrics["nodes"]),
                "operations": int(metrics["operations"]),
            }
            return inst
    raise RuntimeError(
        f"no attack-resistant instance found in {max_candidates} candidates"
    )


def render(inst: dict) -> str:
    k = inst["k"]
    t = inst["components"]
    example_groups = [[component] for component in range(t - 1)]
    example_groups.append(list(range(t - 1, k)))
    lines = [
        "Find a compressed burning certificate for the path forest below.",
        "",
        "Definitions.",
        "A path of order L has vertices 0,1,...,L-1 and edges between consecutive vertices.",
        "A path forest is the disjoint union of its displayed path components; vertices in different components have infinite distance.",
        f"There are k={k} rounds. In round i (1-indexed), choose one vertex that was not burned in an earlier round; by the end, its fire covers every vertex at distance at most k-i.",
        "Equivalently, radius r=k-i belongs to round i and its fire ball has at most 2r+1 vertices on a path.",
        "",
        "Compressed certificate.",
        f"Partition every radius index 0,1,...,{k-1} among the t={t} displayed components.",
        "For each component, the checker reads its radii in the required increasing order and lays their intervals left-to-right: radius r occupies the next 2r+1 vertices and its source is the middle vertex of that interval.",
        "The checker expands these sources into rounds i=k-r, verifies that every source was unburned when selected, and verifies that the fire balls cover every vertex exactly.",
        "Thus your assignment is valid precisely when the odd sizes assigned to every component sum to that component's displayed order; the checker still performs the full interval replay independently.",
        "",
        f"Total graph order = {inst['order']} = k^2.",
        "Component orders (0-based component index: order):",
    ]
    for component, length in enumerate(inst["lengths"]):
        lines.append(f"{component}: {length}")
    lines.extend(
        [
            "",
            f"Give your final answer inside <answer></answer> tags as a JSON array of exactly {t} nonempty arrays.",
            "Array c lists, in strictly increasing order, the distinct radius indices assigned to component c; together the arrays must contain each radius 0 through k-1 exactly once.",
            "Example syntax only: <answer>"
            + json.dumps(example_groups, separators=(",", ":"))
            + "</answer>",
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
    def decode(body: str) -> object | None:
        body = body.strip()
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
        if not body:
            return None
        try:
            value = json.loads(body)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        return value if isinstance(value, list) else None

    try:
        tagged = _TAG_RE.findall(text)
        for body in reversed(tagged):
            value = decode(body)
            if value is not None:
                return value
        fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, re.I | re.S)
        for body in reversed(fenced):
            value = decode(body)
            if value is not None:
                return value
        decoder = json.JSONDecoder()
        values: list[object] = []
        for start, char in enumerate(text):
            if char != "[":
                continue
            try:
                value, _ = decoder.raw_decode(text[start:])
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            if isinstance(value, list):
                values.append(value)
        return values[-1] if values else None
    except Exception:
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    t = inst["components"]
    k = inst["k"]
    if not isinstance(answer, list):
        return False, "malformed: expected a JSON array of component arrays"
    if not answer:
        return False, "empty: the component partition is absent"
    if len(answer) != t:
        return False, f"wrong group count: expected {t}, got {len(answer)}"

    flat: list[int] = []
    for component, group in enumerate(answer):
        if not isinstance(group, list):
            return False, f"malformed group: component {component} is not an array"
        if not group:
            return False, f"empty component: component {component} has no radius"
        for radius in group:
            if not isinstance(radius, int) or isinstance(radius, bool):
                return False, "malformed radius: every radius index must be an integer"
            if radius < 0 or radius >= k:
                return False, f"out of range: radius {radius} is not in [0,{k-1}]"
        if group != sorted(group):
            return False, f"noncanonical order: component {component} is not increasing"
        if len(group) != len(set(group)):
            return False, f"duplicate within component: component {component} repeats a radius"
        flat.extend(group)

    counts: dict[int, int] = {}
    for radius in flat:
        counts[radius] = counts.get(radius, 0) + 1
    repeated = sorted(radius for radius, count in counts.items() if count > 1)
    if repeated:
        return False, f"duplicate across components: radius {repeated[0]} appears twice"
    missing = sorted(set(range(k)) - set(flat))
    if missing:
        return False, f"incomplete: radius {missing[0]} is missing"

    sources: dict[int, tuple[int, int]] = {}
    covered_intervals: list[list[tuple[int, int]]] = [[] for _ in range(t)]
    for component, group in enumerate(answer):
        position = 0
        for radius in group:
            left = position
            right = position + 2 * radius
            source = position + radius
            sources[radius] = (component, source)
            covered_intervals[component].append((left, right))
            position = right + 1
        expected = inst["lengths"][component]
        if position != expected:
            return False, (
                f"component length mismatch: component {component} receives "
                f"{position} vertices of fire-ball capacity, not {expected}"
            )

    # Replay the requirement that a later source was not reached by an earlier
    # source.  Radius r is ignited in round k-r, so larger radii ignite earlier.
    for earlier_radius in range(k - 1, -1, -1):
        c1, p1 = sources[earlier_radius]
        earlier_round = k - earlier_radius
        for later_radius in range(earlier_radius - 1, -1, -1):
            c2, p2 = sources[later_radius]
            if c1 != c2:
                continue
            later_round = k - later_radius
            if abs(p1 - p2) < later_round - earlier_round:
                return False, (
                    f"source already burned: radius {later_radius}'s source was "
                    f"reached before round {later_round}"
                )

    # Exact interval replay: no gaps, no overlaps, and the last endpoint is L-1.
    for component, intervals in enumerate(covered_intervals):
        cursor = 0
        for left, right in intervals:
            if left != cursor:
                return False, f"coverage gap or overlap in component {component}"
            cursor = right + 1
        if cursor != inst["lengths"][component]:
            return False, f"coverage incomplete in component {component}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    k = inst["k"]
    t = inst["components"]
    while True:
        choices = [rng.randrange(t) for _ in range(k)]
        if len(set(choices)) == t:
            return _groups_from_choices(k, t, choices)


def search_space(inst: dict) -> int | None:
    k = inst["k"]
    t = inst["components"]
    # Number of onto maps from the k labeled radii to t labeled components.
    return sum(
        (-1) ** missing * math.comb(t, missing) * (t - missing) ** k
        for missing in range(t + 1)
    )


def enumerate_all(inst: dict) -> int | None:
    k = inst["k"]
    t = inst["components"]
    if t ** k > 1_000_000:
        return None
    count = 0
    for choices in itertools.product(range(t), repeat=k):
        if len(set(choices)) != t:
            continue
        answer = _groups_from_choices(k, t, list(choices))
        count += int(verify(inst, answer)[0])
    return count


def canonical_key(inst: dict) -> str:
    canonical = {
        "k": inst["k"],
        "component_orders": sorted(inst["lengths"]),
    }
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _reorder_components(inst: dict, order: list[int]) -> tuple[dict, list[list[int]]]:
    if sorted(order) != list(range(inst["components"])):
        raise ValueError("order must permute the components")
    moved = {key: value for key, value in inst.items() if key != "answer"}
    moved["lengths"] = [inst["lengths"][old] for old in order]
    carried = [inst["answer"][old][:] for old in order]
    moved["answer"] = carried
    return moved, carried


def escalate(params: dict) -> dict | str | None:
    p = {key: value for key, value in params.items() if key != "_preset"}
    t = int(p.get("components", 8))
    n = int(p["n"])
    # Grow the assignment haystack at fixed certificate length first.
    # t=12 pushes the measured residue-recovery route over the 300-operation
    # G9(c) cap for the current hard size, so t=11 is this fixed-length axis's
    # last usable point.
    if t < min(11, n - 1):
        p["components"] = t + 1
        p["filter_min_nodes"] = min(100_000, max(5_000, int(p.get("filter_min_nodes", 0))))
        p["filter_max_nodes"] = max(
            p["filter_min_nodes"] + 1,
            min(1_500_000, max(250_000, int(p.get("filter_max_nodes", 0)))),
        )
        return p
    minimum = int(p.get("filter_min_nodes", 0))
    if minimum < 100_000:
        p["filter_min_nodes"] = min(100_000, max(10_000, minimum * 2))
        p["filter_max_nodes"] = min(
            1_500_000, max(p["filter_min_nodes"] * 4, int(p.get("filter_max_nodes", 0)))
        )
        p["random_restarts"] = min(512, max(64, int(p.get("random_restarts", 0)) * 2))
        return p
    if n < 120:
        next_n = min(120, n + max(4, n // 8))
        probe = _raw_instance(next_n, t, 0, 0)
        compact, operations = _residue_class_certificate(probe)
        if compact is None or operations > 300:
            return "cap_bound"
        p["n"] = next_n
        return p
    return "cap_bound"


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))
    elements = sum(len(group) for group in answer) if isinstance(answer, list) else 1
    return len(encoded), math.ceil(len(encoded) / 4), elements


def selftest() -> dict:
    report: dict[str, Any] = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures: list[str] = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append(f"{preset}/{seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=123, **shipping)
    answer = [group[:] for group in ship["answer"]]
    if len(answer[0]) < 2:
        raise AssertionError("shipping corruption fixture needs a two-radius group")
    swapped_order = [group[:] for group in answer]
    swapped_order[0][0], swapped_order[0][1] = swapped_order[0][1], swapped_order[0][0]
    dropped = [group[:] for group in answer]
    dropped[0] = dropped[0][:-1]
    duplicate_inside = [group[:] for group in answer]
    duplicate_inside[0] = sorted(duplicate_inside[0] + [duplicate_inside[0][0]])
    duplicate_across = [group[:] for group in answer]
    duplicate_across[1] = sorted(duplicate_across[1] + [duplicate_across[0][0]])
    exchanged = [group[:] for group in answer]
    exchanged[0][0], exchanged[1][0] = exchanged[1][0], exchanged[0][0]
    exchanged[0].sort()
    exchanged[1].sort()
    corruptions = {
        "empty": [],
        "drop_group": answer[:-1],
        "drop_element": dropped,
        "swap_order": swapped_order,
        "duplicate_inside": duplicate_inside,
        "duplicate_across": duplicate_across,
        "out_of_range": [[ship["k"]] + answer[0][1:]] + [g[:] for g in answer[1:]],
        "exchange_components": exchanged,
    }
    corruption_results = {
        name: {"accepted": verify(ship, value)[0], "reason": verify(ship, value)[1]}
        for name, value in corruptions.items()
    }
    reasons = [row["reason"] for row in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not row["accepted"] for row in corruption_results.values())
        and len(reasons) == len(set(reasons)),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "The radius blocks tile all displayed paths.\n<answer>\n```json\n"
        + json.dumps(answer)
        + "\n```\n</answer>\nThe interval replay is exact."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer
        and verify(ship, parsed)[0]
        and parse_answer("unrelated garbage") is None,
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("unrelated garbage") is None,
    }

    guess_rng = random.Random(0x20030914)
    guess_total = 200_000
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_wall = time.perf_counter() - start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_fraction,
        "candidate_space": search_space(ship),
        "sampling_prior": "uniform onto assignments of all radii to labeled nonempty components",
        "wall_clock_sec": round(guess_wall, 6),
    }

    attack_names = (
        "outlier_length_rank_blocks",
        "greedy_tightest_residual",
        "greedy_largest_residual",
        "random_greedy_restarts",
        "affine_modulo_ansatz",
    )
    attacks = {
        name: {
            "successes": 0,
            "attempts": 0,
            "operations": 0,
            "wall_clock_sec": 0.0,
        }
        for name in attack_names
    }
    reference = {
        "name": "memoized fixed-bin path-forest dynamic program",
        "complexity": "O(k*t*product_c(L_c+1)); polynomial for fixed t",
        "successes": 0,
        "attempts": 0,
        "nodes": 0,
        "operations": 0,
        "wall_clock_sec": 0.0,
        "per_seed": [],
    }
    for seed in range(800, 808):
        current = make_instance(seed=seed, **shipping)

        start = time.perf_counter()
        candidate = _attack_length_rank_blocks(current)
        elapsed = time.perf_counter() - start
        row = attacks[attack_names[0]]
        row["attempts"] += 1
        row["successes"] += int(candidate is not None and verify(current, candidate)[0])
        row["operations"] += current["k"]
        row["wall_clock_sec"] += elapsed

        for name, tightest in ((attack_names[1], True), (attack_names[2], False)):
            start = time.perf_counter()
            candidate = _attack_residual_greedy(current, tightest)
            elapsed = time.perf_counter() - start
            row = attacks[name]
            row["attempts"] += 1
            row["successes"] += int(candidate is not None and verify(current, candidate)[0])
            row["operations"] += current["k"] * current["components"]
            row["wall_clock_sec"] += elapsed

        start = time.perf_counter()
        candidate, steps = _attack_random_greedy(
            current,
            random.Random(_mix_seed(seed ^ 0xA77AC, current["selection_nonce"])),
            int(shipping["random_restarts"]),
        )
        elapsed = time.perf_counter() - start
        row = attacks[attack_names[3]]
        row["attempts"] += 1
        row["successes"] += int(candidate is not None and verify(current, candidate)[0])
        row["operations"] += steps
        row["wall_clock_sec"] += elapsed

        start = time.perf_counter()
        candidate, operations = _attack_affine_modulo(current)
        elapsed = time.perf_counter() - start
        row = attacks[attack_names[4]]
        row["attempts"] += 1
        row["successes"] += int(candidate is not None and verify(current, candidate)[0])
        row["operations"] += operations
        row["wall_clock_sec"] += elapsed

        start = time.perf_counter()
        candidate, nodes, operations = _reference_fixed_bin_dp(
            current, int(shipping["filter_max_nodes"])
        )
        elapsed = time.perf_counter() - start
        solved = isinstance(candidate, list) and verify(current, candidate)[0]
        reference["attempts"] += 1
        reference["successes"] += int(solved)
        reference["nodes"] += nodes
        reference["operations"] += operations
        reference["wall_clock_sec"] += elapsed
        reference["per_seed"].append(
            {
                "seed": seed,
                "solved": solved,
                "nodes": nodes,
                "operations": operations,
                "wall_clock_sec": round(elapsed, 6),
            }
        )

    for row in attacks.values():
        row["wall_clock_sec"] = round(row["wall_clock_sec"], 6)
    reference["wall_clock_sec"] = round(reference["wall_clock_sec"], 6)
    reference["solves"] = f"{reference['successes']}/{reference['attempts']}, as expected"
    all_failed = all(row["successes"] == 0 for row in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference["successes"] == reference["attempts"] == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "construction_aware_attacks": list(attack_names),
    }

    demo = make_instance(seed=123, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": guess_hits == 0
        and demo_count is not None
        and demo_count > 0
        and report["G6_adversary_panel"]["pass"],
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": guess_total,
        "shipping_sampled_density": guess_fraction,
        "shipping_candidate_space": search_space(ship),
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "demo_n": demo["k"],
        "baseline_algorithm": reference["name"],
        "baseline_total_wall_clock_sec": reference["wall_clock_sec"],
        "baseline_total_nodes": reference["nodes"],
        "baseline_total_operations": reference["operations"],
    }

    ladder = []
    for name, params in DIFFICULTY.items():
        sample = make_instance(seed=2, **params)
        ladder.append(
            {
                "preset": name,
                "k": sample["k"],
                "components": sample["components"],
                "candidate_space": search_space(sample),
                "filter_min_nodes": sample["filter_min_nodes"],
            }
        )
    doubled_params = dict(shipping)
    doubled_params["n"] = min(120, 2 * int(shipping["n"]))
    doubled_params["filter_min_nodes"] = 0
    doubled_params["filter_max_nodes"] = 0
    doubled_params["random_restarts"] = 0
    doubled = make_instance(seed=909, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    harder_fixed = escalate(shipping)
    report["G7_scales"] = {
        "pass": doubled_ok
        and isinstance(harder_fixed, dict)
        and harder_fixed["n"] == shipping["n"]
        and harder_fixed["components"] > shipping["components"]
        and all(
            ladder[i]["candidate_space"] < ladder[i + 1]["candidate_space"]
            for i in range(3)
        ),
        "ladder": ladder,
        "fixed_length_escalation": harder_fixed,
        "size_doubled_params": doubled_params,
        "size_doubled_verifies": doubled_ok,
        "size_doubled_reason": doubled_reason,
    }

    invariant_checks = 0
    witness_checks = 0
    key_failures: list[str] = []
    unrelated_keys: list[str] = []
    symmetry_params = {
        "n": 29,
        "components": 7,
        "filter_min_nodes": 0,
        "filter_max_nodes": 0,
        "random_restarts": 0,
    }
    for seed in range(20):
        original = make_instance(seed=20_000 + seed, **symmetry_params)
        base_key = canonical_key(original)
        unrelated_keys.append(base_key)
        rng = random.Random(30_000 + seed)
        first = list(range(original["components"]))
        rng.shuffle(first)
        moved, carried = _reorder_components(original, first)
        second = list(range(original["components"]))
        rng.shuffle(second)
        moved_twice, carried_twice = _reorder_components(moved, second)
        for number, (variant, witness) in enumerate(
            ((moved, carried), (moved_twice, carried_twice))
        ):
            invariant_checks += 1
            if canonical_key(variant) != base_key:
                key_failures.append(f"key/{seed}/{number}")
            witness_checks += 1
            if not verify(variant, witness)[0]:
                key_failures.append(f"witness/{seed}/{number}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct_keys == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": witness_checks,
        "invariance_failures": key_failures,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "transformations": [
            "arbitrary component reordering",
            "composition of two independent component reorderings",
            "implicit reversal of any path component",
        ],
        "key_definition": "SHA-256 of k and the sorted multiset of component orders",
    }

    compact, compact_operations = _residue_class_certificate(ship)
    if compact is None or not verify(ship, compact)[0]:
        compact_operations = 10**9
    chars, tokens, elements = _answer_metrics(ship["answer"])
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        chars <= 2_000
        and elements <= 256
        and compact_operations <= 300
        and tokens <= PROBLEM_PROFILE["max_answer_tokens"]
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": compact_operations,
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
