"""Verified problem generator for arXiv:2601.04295.

The paper's 30 blocks are five disjoint 12-point components.  Each component
is split into four triples and contains all six unions of two triples.  This
module composes those native components, inverse-plants one selected pair,
and applies an invertible modular relabelling.  The certificate is carried
through that map; generation never searches the emitted instance.
"""

from __future__ import annotations

import bisect
import hashlib
import json
import math
import os
import random
import re
import time
from collections import Counter


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "family of six-element blocks on residues modulo a displayed prime",
        "distinguished subset of residue labels",
        "a two-element subset together with a containing block",
    ],
    "verification_operations": [
        "exact integer and modular-arithmetic checks",
        "exact set membership",
        "exact subset containment",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "A common modular step in every block reveals the multiplicative "
        "relabeling; undoing it restores the paper's 12-point/four-triple "
        "components, while missing it leaves a scan of the shuffled blocks."
    ),
    "hardness_basis": (
        "Track B: direct incidence scanning is O(6m); at the shipping preset "
        "its measured membership-test and wall-clock costs are reported by "
        "selftest, while recovering one common modular step and applying "
        "Theorem 1's component decomposition takes under 300 exact operations."
    ),
    "max_answer_tokens": 17,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": " + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {
        "n": 1, "padding_components": 0,
        "min_singletons": 4, "max_singletons": 4, "scramble": False,
    },
    "easy": {
        "n": 32, "padding_components": 288,
        "min_singletons": 26, "max_singletons": 45, "scramble": True,
    },
    "medium": {
        "n": 40, "padding_components": 400,
        "min_singletons": 26, "max_singletons": 45, "scramble": True,
    },
    "hard": {
        "n": 50, "padding_components": 650,
        "min_singletons": 26, "max_singletons": 45, "scramble": True,
    },
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "In every block, the directed pairwise differences modulo p contain a common "
    "nonzero step shared by its two three-term progressions."
)
PLACEBO_HINT = (
    "The selected residues and the entries of each six-element block should be "
    "read with careful attention to all stated ordering conventions."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object with an increasing pair of distinct selected integers and "
        "one increasing six-integer block chosen uniformly from the listed family."
    ),
    "bounds": {
        "pair_size": 2,
        "block_size": 6,
        "point_min": 0,
        "point_max": "modulus-1",
        "candidate_count": "binom(number_selected,2) times 6*(5*n+padding_components)",
    },
}

NOTES = (
    "Section 2 fixes the exact 10 base blocks, their five pairings, their two "
    "three-point halves, and the four recombinations per pair. Section 3, "
    "Theorem 1 and its two-case proof fix the witness: either two selected points "
    "share a base block, or pigeonhole forces two hit base blocks in one paired "
    "couple. Equivalently, each paired couple is one 12-point component partitioned "
    "into four triples, with all six pairwise triple unions as blocks. The paper has "
    "no hardness theorem and its displayed 60-point instance is easy, so this is "
    "honestly Track B. Generation composes only those exact components, places two "
    "selected points in distinct triples of one component, and places at most one "
    "selected point in every other component. It then carries the unique witness "
    "through multiplication by a nonzero residue modulo a prime. All distractor "
    "blocks have the same paper-component distribution as the witness block. Equal "
    "selected-point degrees defeat incidence outliers; a deliberately harmless "
    "consecutive displayed pair defeats closest-value greed; the true pair crosses "
    "the paper's two base blocks and different displayed six-buckets, defeating both "
    "obvious ansatzes; crowding defeats uniform restarts. Direct incidence scan is "
    "disclosed and measured as the successful reference algorithm."
)

# Filled from script-owned transcripts after the three oracle runs.  These are
# diagnostics; G9 gates only answer size and intended-route effort.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0, "errors": 0},
    "hinted": {"solved": 0, "attempts": 0, "errors": 0},
    "placebo": {"solved": 0, "attempts": 0, "errors": 0},
    "hinted_verdict": "pending",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_parameters(n, padding_components, min_singletons, max_singletons, scramble):
    if not _is_int(n) or n < 1:
        raise ValueError("n must be a positive integer")
    if not _is_int(padding_components) or padding_components < 0:
        raise ValueError("padding_components must be a nonnegative integer")
    if not _is_int(min_singletons) or not _is_int(max_singletons):
        raise ValueError("singleton bounds must be integers")
    if not isinstance(scramble, bool):
        raise ValueError("scramble must be a boolean")
    total_components = 5 * n + padding_components
    if not (2 <= min_singletons <= max_singletons < total_components):
        raise ValueError(
            "singleton bounds must satisfy 2 <= min <= max < total components"
        )


def _triple(component_index, triple_index):
    start = 12 * component_index + 3 * triple_index + 1
    return list(range(start, start + 3))


def _union_block(component_index, first_triple, second_triple):
    return _triple(component_index, first_triple) + _triple(
        component_index, second_triple
    )


def _component_blocks(component_index):
    """The paper's two base blocks and four recombinations, in one form."""
    return [
        _union_block(component_index, first, second)
        for first in range(4)
        for second in range(first + 1, 4)
    ]


def _block_code(block):
    return ",".join(str(value) for value in block)


def _make_block_codes(blocks):
    return sorted(_block_code(block) for block in blocks)


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
    candidate = max(2, value)
    if candidate > 2 and candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 1 if candidate == 2 else 2
    return candidate


def _mapped_block(block, multiplier, modulus):
    return sorted((multiplier * point) % modulus for point in block)


def make_instance(
    n,
    seed=0,
    padding_components=0,
    min_singletons=4,
    max_singletons=4,
    scramble=False,
    **params,
):
    """Compose Section 2 components, then carry a witness through a relabelling."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, padding_components, min_singletons, max_singletons, scramble)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    total_components = 5 * n + padding_components
    singleton_span = max_singletons - min_singletons + 1
    # Deliberately material instance data, not a key on the seed: different
    # counts are non-isomorphic because selected status is part of the problem.
    singleton_count = min_singletons + seed % singleton_span
    universe_size = 12 * total_components
    modulus = _next_prime(3 * universe_size + 1) if scramble else None

    # Two singleton components carry the harmless displayed labels 1 and 2.  If
    # their canonical points are d and 2d, multiplication by d^{-1} modulo p maps
    # them to those labels.  This is a decoy, not a computed solution.
    if scramble:
        decoy_component = rng.randrange(1, total_components // 2)
        decoy_point = 12 * decoy_component + 1
        multiplier = pow(decoy_point, -1, modulus)
        fixed_points = [decoy_point, 2 * decoy_point]
        fixed_singletons = [(point - 1) // 12 for point in fixed_points]
    else:
        multiplier = 1
        fixed_singletons = [0, 1]
        fixed_points = [12, 13]

    special_choices = [
        component for component in range(2, total_components)
        if component not in fixed_singletons
    ]
    rng.shuffle(special_choices)
    special_component = left = right = None
    for candidate_component in special_choices:
        cross_base_pairs = [
            (left_point, right_point)
            for left_point in range(12 * candidate_component + 1,
                                    12 * candidate_component + 7)
            for right_point in range(12 * candidate_component + 7,
                                     12 * candidate_component + 13)
            if right_point - left_point > 1
        ]
        rng.shuffle(cross_base_pairs)
        for candidate_left, candidate_right in cross_base_pairs:
            shown_left = ((multiplier * candidate_left) % modulus
                          if scramble else candidate_left)
            shown_right = ((multiplier * candidate_right) % modulus
                           if scramble else candidate_right)
            if abs(shown_left - shown_right) <= 1:
                continue
            if (shown_left - 1) // 6 == (shown_right - 1) // 6:
                continue
            special_component = candidate_component
            left, right = candidate_left, candidate_right
            break
        if special_component is not None:
            break
    if special_component is None:
        raise AssertionError("could not choose an attack-resistant planted pair")

    available = [
        component for component in range(total_components)
        if component not in fixed_singletons and component != special_component
    ]
    singleton_components = fixed_singletons + rng.sample(
        available, singleton_count - 2
    )

    selected_canonical = list(fixed_points)
    selected_canonical.extend(
        12 * component + rng.randrange(12) + 1
        for component in singleton_components[2:]
    )
    selected_canonical.extend((left, right))

    left_triple = ((left - 1) % 12) // 3
    right_triple = ((right - 1) % 12) // 3
    witness_block = _union_block(
        special_component, min(left_triple, right_triple),
        max(left_triple, right_triple)
    )

    canonical_blocks = [
        block
        for component in range(total_components)
        for block in _component_blocks(component)
    ]
    if scramble:
        blocks = [_mapped_block(block, multiplier, modulus)
                  for block in canonical_blocks]
        selected = sorted((multiplier * point) % modulus
                          for point in selected_canonical)
        witness_block = _mapped_block(witness_block, multiplier, modulus)
    else:
        blocks = canonical_blocks
        selected = sorted(selected_canonical)
    rng.shuffle(blocks)
    shown_pair = sorted([
        (multiplier * left) % modulus if scramble else left,
        (multiplier * right) % modulus if scramble else right,
    ])
    answer = {"pair": shown_pair, "block": witness_block}
    return {
        "n": n,
        "padding_components": padding_components,
        "min_singletons": min_singletons,
        "max_singletons": max_singletons,
        "total_components": total_components,
        "universe_size": universe_size,
        "modulus": modulus,
        "scramble": scramble,
        "selected": selected,
        "blocks": blocks,
        # A JSON-native binary-search catalog keeps 200k verifier calls cheap.
        "block_codes": _make_block_codes(blocks),
        "answer": answer,
    }


def render(inst):
    """Render the complete native block-incidence problem."""
    lines = ["PAIR-IN-A-BLOCK WITNESS", ""]
    if inst["scramble"]:
        lines.extend([
            f"All point labels are residues from 0 through p-1, where p = {inst['modulus']} is prime.",
            f"The ground set consists of the {inst['universe_size']} distinct labels that occur in the blocks below.",
            "Whenever modular arithmetic is useful, reduce the result to its unique residue from 0 through p-1.",
        ])
    else:
        lines.append(
            f"The ground set is the integers 1 through {inst['universe_size']}, inclusive."
        )
    lines.extend([
        "A block is an unordered set of exactly six distinct ground-set labels.",
        "The selected set S is:",
        " ".join(str(value) for value in inst["selected"]),
        "",
        f"The block family has {len(inst['blocks'])} blocks. Block numbering below is only for readability:",
    ])
    for index, block in enumerate(inst["blocks"]):
        lines.append(f"{index}: " + " ".join(str(value) for value in block))
    lines.extend([
        "",
        "Find two distinct labels x<y in S and one listed block containing both x and y.",
        "Return the block itself, not its displayed line number. Write both arrays in strictly increasing order.",
        "Give your final answer inside <answer></answer> tags as one JSON object.",
        "This numeric example illustrates syntax only; it is not the answer to this instance:",
        '<answer>{"pair":[3,17],"block":[1,2,3,17,18,19]}</answer>',
        "Replace all eight numbers with your witness. Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Extract the tagged JSON witness, tolerating prose and Markdown fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json|JSON)?\s*", "", body)
        body = re.sub(r"\s*```$", "", body).strip()
    try:
        answer = json.loads(body)
    except (TypeError, ValueError):
        return None
    return answer if isinstance(answer, dict) else None


def verify(inst, answer):
    """Check any pair-and-block witness without consulting the planted answer."""
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if set(answer) != {"pair", "block"}:
        return False, "answer must have exactly the keys pair and block"
    pair = answer["pair"]
    block = answer["block"]
    if not isinstance(pair, list) or len(pair) != 2 or not all(_is_int(x) for x in pair):
        return False, "pair must contain exactly two integers"
    if pair[0] == pair[1]:
        return False, "pair elements must be distinct"
    if pair[0] > pair[1]:
        return False, "pair must be in strictly increasing order"
    selected = inst.get("selected")
    first_pos = bisect.bisect_left(selected, pair[0])
    second_pos = bisect.bisect_left(selected, pair[1])
    if (first_pos == len(selected) or selected[first_pos] != pair[0]
            or second_pos == len(selected) or selected[second_pos] != pair[1]):
        return False, "both pair elements must belong to the selected set"
    if not isinstance(block, list) or len(block) != 6 or not all(_is_int(x) for x in block):
        return False, "block must contain exactly six integers"
    if any(block[i] >= block[i + 1] for i in range(5)):
        return False, "block must be in strictly increasing order"
    code = _block_code(block)
    catalog = inst.get("block_codes")
    pos = bisect.bisect_left(catalog, code)
    if pos == len(catalog) or catalog[pos] != code:
        return False, "block is not a member of the listed family"
    if pair[0] not in block or pair[1] not in block:
        return False, "the listed block does not contain both pair elements"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from selected pairs times listed blocks."""
    pair = sorted(rng.sample(inst["selected"], 2))
    block = list(rng.choice(inst["blocks"]))
    return {"pair": pair, "block": block}


def search_space(inst):
    selected_count = len(inst["selected"])
    return math.comb(selected_count, 2) * len(inst["blocks"])


def enumerate_all(inst):
    space = search_space(inst)
    if space > 100_000:
        return None
    total = 0
    selected = inst["selected"]
    for i in range(len(selected)):
        for j in range(i + 1, len(selected)):
            pair = [selected[i], selected[j]]
            for block in inst["blocks"]:
                total += int(verify(inst, {"pair": pair, "block": block})[0])
    return total


def _exact_valid_answer_count(inst):
    selected = set(inst["selected"])
    return sum(math.comb(sum(value in selected for value in block), 2)
               for block in inst["blocks"])


def canonical_key(inst):
    """Exact key for this family from component selected-occupancy types."""
    blocks = inst["blocks"]
    selected = set(inst["selected"])
    points = {point for block in blocks for point in block}
    parent = {point: point for point in points}

    def find(value):
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(first, second):
        first, second = find(first), find(second)
        if first != second:
            parent[second] = first

    for block in blocks:
        for point in block[1:]:
            union(block[0], point)
    point_count = Counter(find(point) for point in points)
    block_count = Counter(find(block[0]) for block in blocks)
    selected_count = Counter(find(point) for point in selected)
    component_signatures = sorted(
        (size, block_count[root], selected_count[root])
        for root, size in point_count.items()
    )
    payload = {"components": component_signatures}
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return "paper-components-v1:" + hashlib.sha256(blob.encode()).hexdigest()


def escalate(params):
    """No honest post-ladder axis remains after paper-component padding."""
    # The fixed ladder already grows both the paper-copy count and the number of
    # decoy components while the eight-atom answer stays fixed.  Two full oracle
    # sweeps continued to solve even at 21,000 blocks by finding the compact modular
    # route.  More padding changes only prompt length, not the route being tested.
    return None


def _answer_for_pair(inst, pair):
    for block in inst["blocks"]:
        if pair[0] in block and pair[1] in block:
            return {"pair": sorted(pair), "block": list(block)}
    return {"pair": sorted(pair), "block": list(inst["blocks"][0])}


def _attack_selected_degree_outlier(inst):
    degree = {point: 0 for point in inst["selected"]}
    for block in inst["blocks"]:
        for point in block:
            if point in degree:
                degree[point] += 1
    guessed = sorted(degree, key=lambda point: (-degree[point], point))[:2]
    return _answer_for_pair(inst, guessed)


def _attack_closest_selected_pair(inst):
    selected = inst["selected"]
    guessed = min(([selected[i], selected[i + 1]] for i in range(len(selected) - 1)),
                  key=lambda pair: (pair[1] - pair[0], pair))
    return _answer_for_pair(inst, guessed)


def _attack_random_restart(inst, rng, restarts=256):
    candidate = random_candidate(inst, rng)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return candidate


def _attack_same_base_block(inst):
    buckets = {}
    for point in inst["selected"]:
        base = (point - 1) // 6
        if base in buckets:
            return _answer_for_pair(inst, [buckets[base], point])
        buckets[base] = point
    return {"pair": inst["selected"][:2], "block": list(inst["blocks"][0])}


def _direct_scan_reference(inst):
    selected = set(inst["selected"])
    operations = 0
    for block in inst["blocks"]:
        hits = []
        for point in block:
            operations += 1
            if point in selected:
                hits.append(point)
                if len(hits) == 2:
                    return {"pair": sorted(hits), "block": list(block)}, operations
    return None, operations


def _inverse_with_cost(value, modulus):
    """Extended Euclid, returning an inverse and a conservative division count."""
    old_r, r = value, modulus
    old_s, s = 1, 0
    operations = 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        operations += 3
    if old_r != 1:
        return None, operations
    return old_s % modulus, operations + 1


def _recover_multiplier(inst):
    """Recover the multiplicative relabelling from one native six-block."""
    block = inst["blocks"][0]
    modulus = inst["modulus"]
    counts = Counter()
    operations = 0
    for first in block:
        for second in block:
            if first != second:
                counts[(second - first) % modulus] += 1
                operations += 1
    peak = max(counts.values())
    operations += len(counts)
    candidates = sorted(step for step, count in counts.items() if count == peak)
    if len(candidates) == 2 and sum(candidates) == modulus:
        inverse, inverse_cost = _inverse_with_cost(candidates[0], modulus)
        operations += inverse_cost
        trials = [
            (candidates[0], inverse),
            (candidates[1], (-inverse) % modulus),
        ]
    else:
        trials = []
        for step in candidates:
            inverse, inverse_cost = _inverse_with_cost(step, modulus)
            operations += inverse_cost
            trials.append((step, inverse))
    for step, inverse in trials:
        decoded = sorted((inverse * point) % modulus for point in block)
        operations += 2 * len(block)
        if not all(1 <= point <= inst["universe_size"] for point in decoded):
            continue
        return step, inverse, operations
    return None, None, operations


def _compact_reference(inst):
    """Undo the modular map and use the paper's four-triple component form."""
    if not inst["scramble"]:
        multiplier, inverse, operations = 1, 1, 0
    else:
        multiplier, inverse, operations = _recover_multiplier(inst)
        if multiplier is None:
            return None, operations
    occupied = {}
    for shown_point in inst["selected"]:
        point = ((inverse * shown_point) % inst["modulus"]
                 if inst["scramble"] else shown_point)
        component = (point - 1) // 12
        operations += 3
        if component in occupied:
            previous_point, previous_shown = occupied[component]
            first_triple = ((previous_point - 1) % 12) // 3
            second_triple = ((point - 1) % 12) // 3
            operations += 4
            canonical = _union_block(
                component, min(first_triple, second_triple),
                max(first_triple, second_triple)
            )
            block = sorted(
                (multiplier * value) % inst["modulus"]
                if inst["scramble"] else value
                for value in canonical
            )
            operations += 2 * len(block)
            return {"pair": sorted([previous_shown, shown_point]), "block": block}, operations
        occupied[component] = (point, shown_point)
    return None, operations


def _transformed_instance(inst, seed, relabel, reorder):
    rng = random.Random(seed)
    labels = sorted({point for block in inst["blocks"] for point in block})
    if relabel:
        shuffled = list(labels)
        rng.shuffle(shuffled)
        mapping = dict(zip(labels, shuffled))
    else:
        mapping = {value: value for value in labels}
    blocks = [sorted(mapping[value] for value in block) for block in inst["blocks"]]
    if reorder:
        rng.shuffle(blocks)
    answer = {
        "pair": sorted(mapping[value] for value in inst["answer"]["pair"]),
        "block": sorted(mapping[value] for value in inst["answer"]["block"]),
    }
    return {
        "n": inst["n"],
        "padding_components": inst["padding_components"],
        "min_singletons": inst["min_singletons"],
        "max_singletons": inst["max_singletons"],
        "total_components": inst["total_components"],
        "universe_size": inst["universe_size"],
        "modulus": inst["modulus"],
        "scramble": inst["scramble"],
        "selected": sorted(mapping[value] for value in inst["selected"]),
        "blocks": blocks,
        "block_codes": _make_block_codes(blocks),
        "answer": answer,
    }


def _json_answer_size(answer):
    compact = json.dumps(answer, separators=(",", ":"))

    def atoms(value):
        if isinstance(value, dict):
            return sum(atoms(item) for item in value.values())
        if isinstance(value, list):
            return sum(atoms(item) for item in value)
        return 1

    return len(compact), (len(compact) + 3) // 4, atoms(answer)


def _compact_operation_bound(inst):
    """A conservative exact-operation bound for the intended Track B route."""
    if not inst["scramble"]:
        return 3 * len(inst["selected"]) + 16
    # Thirty directed differences; at most fourteen distinct differences; Lame's
    # Euclidean-algorithm bound with slack; two six-entry sign trials; one decoded
    # selected-list scan; and construction of the six-entry output block.
    euclid_divisions = math.ceil(1.45 * inst["modulus"].bit_length()) + 1
    inverse_operations = 3 * euclid_divisions + 1
    return (30 + 14 + inverse_operations + 24
            + 3 * (inst["max_singletons"] + 2) + 16)


def selftest():
    report = {
        "paper": "arXiv:2601.04295",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures = []
    attempts = 0
    for preset, parameters in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **parameters)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "answer is not JSON-native"})
            count = _exact_valid_answer_count(inst)
            if count != 1:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": f"expected one valid answer, found {count}"})
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures,
        "construction": "disjoint composition of Section 2 four-triple components",
    }

    shipping = make_instance(seed=260104295, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    corruptions = {
        "drop_one": {"pair": planted["pair"][:1], "block": planted["block"]},
        "swap_pair_order": {"pair": list(reversed(planted["pair"])), "block": planted["block"]},
        "duplicate_pair_element": {"pair": [planted["pair"][0]] * 2, "block": planted["block"]},
        "empty_block": {"pair": planted["pair"], "block": []},
        "out_of_range": {"pair": [0, planted["pair"][1]], "block": planted["block"]},
    }
    corruption_results = {}
    for name, answer in corruptions.items():
        ok, reason = verify(shipping, answer)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = {entry["reason"] for entry in corruption_results.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in corruption_results.values())
        and len(reasons) == len(corruption_results),
        "cases": corruption_results,
        "distinct_reasons": len(reasons),
    }

    body = json.dumps(planted, separators=(",", ":"))
    realistic = ("The intersection check is complete.\n<answer>\n```json\n" + body
                 + "\n```\n</answer>\nThis is the requested witness.")
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged answer") is None,
        "realistic_response_parsed": parsed == planted,
    }

    guess_rng = random.Random(0x260104295)
    guess_total = 2_000_000
    guess_hits = 0
    started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_elapsed = time.perf_counter() - started
    exact_count = _exact_valid_answer_count(shipping)
    exact_density = exact_count / search_space(shipping)
    sampled_density = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": sampled_density < 1e-6 and exact_density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": sampled_density,
        "exact_probability": exact_density,
        "structure_aware_space": search_space(shipping),
        "sampling_rule": "uniform selected pair times uniform listed block; shape, membership, and ordering are enforced",
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attack_functions = {
        "selected_degree_outlier": lambda inst, rng: _attack_selected_degree_outlier(inst),
        "greedy_closest_values": lambda inst, rng: _attack_closest_selected_pair(inst),
        "random_restart_256": lambda inst, rng: _attack_random_restart(inst, rng, 256),
        "same_displayed_six_bucket_ansatz": lambda inst, rng: _attack_same_base_block(inst),
    }
    attack_results = {name: {"successes": 0, "attempts": 0}
                      for name in attack_functions}
    attack_elapsed = {name: 0.0 for name in attack_functions}
    attack_seeds = list(range(8100, 8108))
    reference_successes = compact_successes = 0
    reference_operations = []
    compact_operations = []
    reference_elapsed = compact_elapsed = 0.0
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for offset, (name, function) in enumerate(attack_functions.items()):
            rng = random.Random(seed * 1009 + offset)
            t0 = time.perf_counter()
            candidate = function(inst, rng)
            attack_elapsed[name] += time.perf_counter() - t0
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])
            attack_results[name]["attempts"] += 1
        t0 = time.perf_counter()
        candidate, operations = _direct_scan_reference(inst)
        reference_elapsed += time.perf_counter() - t0
        reference_operations.append(operations)
        reference_successes += int(candidate is not None and verify(inst, candidate)[0])
        t0 = time.perf_counter()
        candidate, operations = _compact_reference(inst)
        compact_elapsed += time.perf_counter() - t0
        compact_operations.append(operations)
        compact_successes += int(candidate is not None and verify(inst, candidate)[0])
    for name in attack_results:
        attack_results[name]["wall_clock_sec_total_8"] = round(attack_elapsed[name], 6)
    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    intended_bound = _compact_operation_bound(shipping)
    reference = {
        "name": "direct block-incidence scan",
        "complexity": "O(6m) exact membership tests for m listed six-blocks",
        "wall_clock_sec_total_8": round(reference_elapsed, 6),
        "wall_clock_sec_mean": round(reference_elapsed / len(attack_seeds), 8),
        "operations_mean": sum(reference_operations) // len(reference_operations),
        "operations_min": min(reference_operations),
        "operations_max": max(reference_operations),
        "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
    }
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == compact_successes == len(attack_seeds),
        "attacks": attack_results,
        "reference_algorithm": reference,
        "compact_route": {
            "name": "selected-list component scan plus the four-triple union rule",
            "wall_clock_sec_total_8": round(compact_elapsed, 6),
            "operations_mean": sum(compact_operations) / len(compact_operations),
            "operations_max_measured": max(compact_operations),
            "worst_case_exact_operations": intended_bound,
            "solves": f"{compact_successes}/{len(attack_seeds)}, as expected",
        },
    }

    strongest = max(attack_elapsed, key=attack_elapsed.get)
    report["G5_density_and_baseline_cost"] = {
        "pass": exact_density < 1e-6 and sampled_density < 1e-6 and all_failed,
        "exact_valid_answer_count_at_shipping": exact_count,
        "exact_density_at_shipping": exact_density,
        "sampled_density_at_shipping": sampled_density,
        "density_hits": guess_hits,
        "density_samples": guess_total,
        "candidate_space": search_space(shipping),
        "strongest_failing_attack": strongest,
        "strongest_attack_wall_clock_sec_total_8": round(attack_elapsed[strongest], 6),
        "strongest_attack_trials_total_8": 256 * len(attack_seeds),
        "reference_algorithm_operations_mean": reference["operations_mean"],
        "reference_algorithm_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
        "demo_bruteforce_valid_answers": enumerate_all(
            make_instance(seed=3, **DIFFICULTY["demo"]))
    }

    doubled = make_instance(
        n=2 * shipping["n"],
        padding_components=shipping["padding_components"],
        min_singletons=shipping["min_singletons"],
        max_singletons=shipping["max_singletons"],
        scramble=shipping["scramble"],
        seed=260104295,
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(shipping)
        and len(doubled["blocks"]) > len(shipping["blocks"]),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_blocks": len(shipping["blocks"]),
        "doubled_blocks": len(doubled["blocks"]),
        "shipping_search_space": search_space(shipping),
        "doubled_search_space": search_space(doubled),
        "verify_reason": doubled_reason,
    }

    invariance_checks = carried_checks = 0
    key_failures = []
    for offset in range(20):
        inst = make_instance(seed=9000 + offset, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        for variant, (relabel, reorder) in enumerate(((False, True), (True, False), (True, True))):
            transformed = _transformed_instance(
                inst, 12000 + 10 * offset + variant, relabel, reorder
            )
            invariance_checks += 1
            if canonical_key(transformed) != key:
                key_failures.append({"seed": offset, "variant": variant,
                                     "reason": "key changed"})
            carried_checks += 1
            if not verify(transformed, transformed["answer"])[0]:
                key_failures.append({"seed": offset, "variant": variant,
                                     "reason": "carried witness failed"})
    unrelated = [canonical_key(make_instance(seed=20000 + offset,
                 **DIFFICULTY[SHIPPING_DIFFICULTY])) for offset in range(20)]
    distinct_keys = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "invariance_failures": key_failures,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "symmetries_tested": [
            "arbitrary block reordering",
            "arbitrary ground-set relabelling",
            "composition of ground-set relabelling and block reordering",
        ],
        "key_method": "exact multiset of block-connected component size/block/selected occupancies",
    }

    answer_chars, answer_tokens, answer_elements = _json_answer_size(shipping["answer"])
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else None)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else None)
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_bound <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (hinted_rate - placebo_rate
                                  if hinted_rate is not None and placebo_rate is not None
                                  else None),
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_bound,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["pass"] = all(gate.get("pass") is True for gate in gates)
    report["all_passed"] = report["pass"]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
