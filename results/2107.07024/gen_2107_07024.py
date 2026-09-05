"""Verified Track-B generator for close-density rainbow matroid bases.

The native problem is the one defined in Section 1 of arXiv:2107.07024.
There are n coloured bases of a rank-n matroid, and a rainbow basis chooses
one element of every colour so that the chosen elements form a matroid basis.
Theorem 1.2 guarantees n-k^3 pairwise-disjoint rainbow bases when the matroid
has n+k elements.  This module takes k=2 and asks for exactly n-8 of them.

The matroid is the uniform matroid U_{n,n+2}.  Each coloured input basis is
therefore represented economically by the two ground elements it omits.
Generation samples distinct modular centres and five nonzero signed radii,
then makes every omitted pair symmetric about its centre.  The offsets not
used as signed radii translate all centres into n-8 disjoint rainbow bases.
The certificate is consequently known before the instance is rendered.

Uniform-matroid rainbow bases are also a bipartite edge-colouring problem.
The reference algorithm regularises the incidence multigraph and repeatedly
finds perfect matchings.  It is polynomial and succeeds, as Track B requires;
the benchmark tests whether a no-tool solver sees the much shorter modular
invariant instead of carrying out that mechanical computation.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import re
import sys
import time
from collections import Counter, deque


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # This finite-discrete family needs no helper library.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "uniform matroid U_{n,n+2}",
        "sequence of coloured matroid bases",
        "pairwise-disjoint rainbow bases",
    ],
    "verification_operations": [
        "integer residue range comparison",
        "coloured-base membership",
        "set cardinality comparison",
        "uniform-matroid basis check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Each two-element omission has a modular midpoint, and the same five "
        "signed radius pairs govern every colour; without recognizing those "
        "translations, one must construct a large edge-colouring."
    ),
    "hardness_basis": (
        "Track B: Section 1 and Theorem 1.2 give the k=2 target n-8, while "
        "the domain-standard algorithm for this uniform-matroid specialization "
        "regularises the bipartite incidence graph and performs repeated "
        "augmenting-path perfect matchings in O(n(n+2)^3) time, measured at "
        "28,190 edge-scan/augmentation operations and 0.0567 seconds in the "
        "shipping preset, whereas the midpoint/translation route uses 285 "
        "modular arithmetic operations."
    ),
    "max_answer_tokens": 191,
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
    "demo": {"n": 9},
    "easy": {"n": 11},
    "medium": {"n": 15},
    "hard": {"n": 19},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Modulo the ground-set size, the omission pairs have distinct midpoints "
    "and only five shared signed radii."
)
PLACEBO_HINT = (
    "Across the ground-set labels, the coloured rows reward consistent and "
    "careful modular bookkeeping."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "An ordered JSON list of t=n-8 lists; each inner list has n residues "
        "in colour order, and for each colour its t entries are distinct "
        "members of that colour's displayed input basis."
    ),
    "bounds": {
        "rainbow_bases": "t=n-8",
        "entries_per_basis": "n",
        "entry_range": "0..n+1",
        "row_rule": "for each colour, t distinct allowed entries",
        "maximum_shipping_atomic_elements": 209,
    },
}

NOTES = (
    "Section 1 fixes the exact native definition: a rainbow base chooses one "
    "element from each coloured input basis, and disjoint rainbow bases never "
    "reuse an element of the same colour.  Theorem 1.2 fixes the close-density "
    "regime and guarantees n-k^3 such bases for a rank-n matroid on n+k "
    "elements; this family uses k=2 and therefore asks for n-8.  Sections 5 "
    "through 12 reveal what produces the paper's general certificate: matroid "
    "intersection followed by alternating-path and path-chain repairs.  More "
    "decisively for hardness, the introduction records Wild's easy strongly-"
    "base-orderable class, which includes the uniform matroid here, and this "
    "specialization has a polynomial edge-colouring algorithm.  The family is "
    "therefore explicitly Track B.  Its mechanical reference "
    "route is bipartite edge-colouring by regularisation and repeated perfect "
    "matchings.  Its compact route uses modular midpoints and shared signed "
    "radii.  The outlier attack ranks globally frequent elements, the greedy "
    "attack never backtracks, the restart attack samples row-feasible schedules, "
    "and the obvious midpoint ansatz tries consecutive shifts; affine relabelling, "
    "colour shuffling, and five nonconsecutive radius pairs defeat those probes."
)


# Filled from the script-owned transcripts after the three hardening runs.
G9_ORACLE_RESULTS = {
    # The current script-owned bare transcript reached the shipping preset once
    # before the OpenRouter account hit its total limit.  Errors are not attempts.
    "bare": {"solved": 0, "attempts": 1},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run_external_quota",
}


def _validate_n(n):
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an odd integer")
    if n < 9 or n % 2 == 0:
        raise ValueError("n must be odd and at least 9")


def _units(modulus):
    return [value for value in range(1, modulus) if math.gcd(value, modulus) == 1]


def make_instance(n, seed=0, **params):
    """Inverse-generate n-8 disjoint rainbow bases of U_{n,n+2}."""
    if params:
        unknown = ", ".join(sorted(params))
        raise TypeError(f"unknown parameters: {unknown}")
    _validate_n(n)
    rng = random.Random(seed)
    modulus = n + 2
    required = n - 8

    # In hidden coordinates, all centres except two are used as colours.
    missing_centres = set(rng.sample(range(modulus), 2))
    centres = [value for value in range(modulus) if value not in missing_centres]
    rng.shuffle(centres)

    # Five unsigned radii account for ten forbidden translations.  Every radius
    # occurs at least once, so the complement has exactly modulus-10=n-8 shifts.
    unsigned = list(range(1, (modulus + 1) // 2))
    radii = rng.sample(unsigned, 5)
    assigned = list(radii)
    assigned.extend(rng.choice(radii) for _ in range(n - len(radii)))
    rng.shuffle(assigned)

    # Affine relabelling preserves cyclic translations but removes any fixed
    # positional convention.  Colour order was already shuffled independently.
    scale = rng.choice(_units(modulus))
    translate = rng.randrange(modulus)
    labelled_centres = [(scale * value + translate) % modulus for value in centres]
    omissions = []
    for centre, radius in zip(centres, assigned):
        left = (scale * (centre - radius) + translate) % modulus
        right = (scale * (centre + radius) + translate) % modulus
        omissions.append(sorted((left, right)))

    signed_radii = set()
    for radius in radii:
        signed_radii.add((scale * radius) % modulus)
        signed_radii.add((-scale * radius) % modulus)
    offsets = [value for value in range(modulus) if value not in signed_radii]
    rng.shuffle(offsets)
    answer = [
        [(centre + offset) % modulus for centre in labelled_centres]
        for offset in offsets
    ]

    return {
        "family": "close_density_rainbow_bases",
        "rank": n,
        "k": 2,
        "ground_size": modulus,
        "ground_elements": list(range(modulus)),
        "matroid": {"type": "uniform", "rank": n, "ground_size": modulus},
        "required_bases": required,
        "omissions": omissions,
        "answer": answer,
    }


def render(inst):
    n = inst["rank"]
    modulus = inst["ground_size"]
    required = inst["required_bases"]
    lines = [
        "DISJOINT RAINBOW BASES IN A CLOSE-DENSITY MATROID",
        "",
        f"The ground set is the integer residues 0,...,{modulus - 1} modulo {modulus}.",
        f"The matroid is the uniform matroid U_{{{n},{modulus}}}: a subset is a basis",
        f"exactly when it consists of {n} distinct ground elements.",
        "",
        f"There are {n} colours, indexed 0,...,{n - 1}.  The input basis of each",
        "colour contains every ground element except its displayed omitted pair:",
    ]
    for colour, pair in enumerate(inst["omissions"]):
        lines.append(f"  colour {colour}: omit {pair[0]}, {pair[1]}")
    lines.extend(
        [
            "",
            "A rainbow basis is a list of exactly one chosen ground element for each",
            "colour, in increasing colour order.  Every chosen element must belong to",
            f"its colour's input basis, and the {n} chosen ground elements must be distinct.",
            "Two rainbow bases are disjoint when, for every fixed colour, they choose",
            "different ground elements.  (Different colours may reuse an element in",
            "different rainbow bases; only each individual rainbow basis must be distinct.)",
            "",
            f"Find {required} pairwise-disjoint rainbow bases.  The order of those bases",
            "does not matter, but each inner list is always in colour order.  Repetitions",
            "within a rainbow basis or within one colour across the lists are forbidden.",
            "All labels are ordinary canonical integers in the inclusive range",
            f"0 through {modulus - 1}; do not replace them by congruent integers.",
            "",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    lines.extend(
        [
            "",
            "Give your final answer inside <answer></answer> tags as one JSON nested list:",
            f"an outer list of {required} inner lists, each containing {n} integers.",
            "Example format: <answer>[[0,1,2],[1,2,0]]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\s*>(.*?)</answer\s*>", text, re.I | re.S)
    if not match:
        return None
    payload = match.group(1).strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return answer if isinstance(answer, list) else None


def verify(inst, answer):
    """Check an arbitrary explicit collection; never consult inst['answer']."""
    n = inst.get("rank")
    modulus = inst.get("ground_size")
    required = inst.get("required_bases")
    omissions = inst.get("omissions")
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if len(answer) != required:
        return False, f"expected exactly {required} rainbow bases"
    if not isinstance(omissions, list) or len(omissions) != n:
        return False, "instance has malformed coloured bases"
    used_by_colour = [set() for _ in range(n)]
    for basis_index, basis in enumerate(answer):
        if not isinstance(basis, list):
            return False, f"rainbow basis {basis_index} is not a list"
        if len(basis) != n:
            return False, f"rainbow basis {basis_index} must contain exactly {n} entries"
        seen_ground = set()
        for colour, value in enumerate(basis):
            if isinstance(value, bool) or not isinstance(value, int):
                return False, f"entry at basis {basis_index}, colour {colour} is not an integer"
            if value < 0 or value >= modulus:
                return False, f"entry at basis {basis_index}, colour {colour} is outside the ground set"
            if value in omissions[colour]:
                return False, f"entry at basis {basis_index}, colour {colour} is omitted from that input basis"
            if value in seen_ground:
                return False, f"rainbow basis {basis_index} repeats a ground element"
            seen_ground.add(value)
            if value in used_by_colour[colour]:
                return False, f"colour {colour} reuses a ground element across rainbow bases"
            used_by_colour[colour].add(value)
        # This cardinality equality is exactly the U_{n,n+2} basis oracle.
        if len(seen_ground) != n:
            return False, f"rainbow basis {basis_index} is not a uniform-matroid basis"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from row-feasible schedules, not the naive cube."""
    n = inst["rank"]
    required = inst["required_bases"]
    modulus = inst["ground_size"]
    by_colour = []
    for omitted in inst["omissions"]:
        allowed = [value for value in range(modulus) if value not in omitted]
        by_colour.append(rng.sample(allowed, required))
    return [
        [by_colour[colour][basis_index] for colour in range(n)]
        for basis_index in range(required)
    ]


def _falling(value, length):
    result = 1
    for item in range(value - length + 1, value + 1):
        result *= item
    return result


def search_space(inst):
    # Each of n colours independently supplies an ordered t-tuple of distinct
    # members from its n-element input basis.
    return _falling(inst["rank"], inst["required_bases"]) ** inst["rank"]


def enumerate_all(inst):
    """Count demo witnesses exactly with a subset-DP permanent."""
    n = inst["rank"]
    modulus = inst["ground_size"]
    required = inst["required_bases"]
    if required != 1 or modulus > 17:
        return None
    dp = {0: 1}
    for colour in range(n):
        forbidden = set(inst["omissions"][colour])
        nxt = {}
        for mask, count in dp.items():
            for value in range(modulus):
                bit = 1 << value
                if value not in forbidden and not (mask & bit):
                    new_mask = mask | bit
                    nxt[new_mask] = nxt.get(new_mask, 0) + count
        dp = nxt
    return sum(dp.values())


def _incidence_invariant(inst):
    """A strong relabelling invariant for the unlabeled omission multigraph."""
    modulus = inst["ground_size"]
    omissions = inst["omissions"]
    n_colours = len(omissions)
    total = modulus + n_colours
    neighbours = [[] for _ in range(total)]
    for colour, pair in enumerate(omissions):
        node = modulus + colour
        for ground in pair:
            neighbours[node].append(ground)
            neighbours[ground].append(node)

    colours = [0] * modulus + [1] * n_colours
    trace = []
    for _ in range(total + 1):
        signatures = [
            (colours[node], tuple(sorted(colours[other] for other in neighbours[node])))
            for node in range(total)
        ]
        vocabulary = {signature: index for index, signature in enumerate(sorted(set(signatures)))}
        refined = [vocabulary[signature] for signature in signatures]
        trace.append(sorted(Counter(refined).values()))
        if refined == colours:
            break
        colours = refined

    distance_records = []
    for source in range(total):
        distances = [-1] * total
        distances[source] = 0
        queue = deque([source])
        while queue:
            node = queue.popleft()
            for other in neighbours[node]:
                if distances[other] < 0:
                    distances[other] = distances[node] + 1
                    queue.append(other)
        distance_records.append(
            (
                0 if source < modulus else 1,
                colours[source],
                len(neighbours[source]),
                tuple(sorted((colours[node], distances[node]) for node in range(total))),
            )
        )

    edge_multiplicity = Counter(tuple(sorted(pair)) for pair in omissions)
    ground_degrees = [len(neighbours[node]) for node in range(modulus)]
    edge_records = []
    for (left, right), multiplicity in edge_multiplicity.items():
        edge_records.append(
            (min(ground_degrees[left], ground_degrees[right]),
             max(ground_degrees[left], ground_degrees[right]), multiplicity)
        )
    quotient_edges = Counter()
    for node in range(total):
        for other in neighbours[node]:
            if node < other:
                quotient_edges[tuple(sorted((colours[node], colours[other])))] += 1
    return {
        "ground": modulus,
        "colours": n_colours,
        "degree_sequence": sorted(ground_degrees),
        "edge_records": sorted(edge_records),
        "wl_trace": trace,
        "distance_records": sorted(distance_records),
        "quotient_edges": sorted((list(key), value) for key, value in quotient_edges.items()),
    }


def canonical_key(inst):
    payload = json.dumps(_incidence_invariant(inst), separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params):
    n = params.get("n")
    if isinstance(n, bool) or not isinstance(n, int):
        return None
    candidate = n + 4
    atoms = candidate * (candidate - 8)
    if atoms > 256:
        return "cap_bound"
    return {**params, "n": candidate}


def _permute_colours(inst, order):
    transformed = copy.deepcopy(inst)
    transformed["omissions"] = [copy.deepcopy(inst["omissions"][old]) for old in order]
    transformed["answer"] = [
        [basis[old] for old in order]
        for basis in inst["answer"]
    ]
    return transformed


def _relabel_ground(inst, old_to_new):
    transformed = copy.deepcopy(inst)
    transformed["omissions"] = [
        sorted((old_to_new[pair[0]], old_to_new[pair[1]]))
        for pair in inst["omissions"]
    ]
    transformed["answer"] = [
        [old_to_new[value] for value in basis]
        for basis in inst["answer"]
    ]
    return transformed


def _reverse_omission_pairs(inst):
    transformed = copy.deepcopy(inst)
    transformed["omissions"] = [list(reversed(pair)) for pair in inst["omissions"]]
    return transformed


# ---------------------------------------------------------------------------
# Reference algorithm and deliberately incomplete no-tool attacks.


def _perfect_matching(counts, stats):
    size = len(counts)
    match_right = [-1] * size

    def augment(left, seen):
        stats["augment_calls"] += 1
        for right in range(size):
            stats["edge_scans"] += 1
            if counts[left][right] <= 0 or seen[right]:
                continue
            seen[right] = True
            if match_right[right] < 0 or augment(match_right[right], seen):
                match_right[right] = left
                return True
        return False

    for left in range(size):
        if not augment(left, [False] * size):
            return None
    match_left = [-1] * size
    for right, left in enumerate(match_right):
        if left >= 0:
            match_left[left] = right
    return match_left


def _reference_algorithm(inst):
    """Classical bipartite regularisation and repeated perfect matchings."""
    started = time.perf_counter()
    n = inst["rank"]
    modulus = inst["ground_size"]
    counts = [[0] * modulus for _ in range(modulus)]
    for colour, omitted in enumerate(inst["omissions"]):
        forbidden = set(omitted)
        for ground in range(modulus):
            if ground not in forbidden:
                counts[colour][ground] = 1

    # Add k=2 dummy left vertices, allowing parallel dummy edges.  The resulting
    # square bipartite multigraph is n-regular, so every residual graph has a
    # perfect matching until all n colour classes have been extracted.
    deficits = [n - sum(counts[left][right] for left in range(n)) for right in range(modulus)]
    remaining_row = n
    for right, deficit in enumerate(deficits):
        put = min(deficit, remaining_row)
        counts[n][right] = put
        counts[n + 1][right] = deficit - put
        remaining_row -= put
    if remaining_row != 0 or sum(counts[n + 1]) != n:
        return None, {
            "edge_scans": 0,
            "augment_calls": 0,
            "matchings": 0,
            "operations": 0,
            "wall_clock_sec": time.perf_counter() - started,
        }

    stats = {"edge_scans": 0, "augment_calls": 0, "matchings": 0}
    extracted = []
    for _ in range(n):
        matching = _perfect_matching(counts, stats)
        if matching is None:
            break
        for left, right in enumerate(matching):
            counts[left][right] -= 1
        extracted.append(matching[:n])
        stats["matchings"] += 1
    stats["operations"] = stats["edge_scans"] + stats["augment_calls"]
    stats["wall_clock_sec"] = time.perf_counter() - started
    if len(extracted) < inst["required_bases"]:
        return None, stats
    return extracted[: inst["required_bases"]], stats


def _compact_route(inst):
    started = time.perf_counter()
    modulus = inst["ground_size"]
    inverse_two = (modulus + 1) // 2
    centres = []
    forbidden_offsets = set()
    operations = 0
    for left, right in inst["omissions"]:
        centre = ((left + right) * inverse_two) % modulus
        operations += 2
        centres.append(centre)
        forbidden_offsets.add((left - centre) % modulus)
        forbidden_offsets.add((right - centre) % modulus)
        operations += 2
    offsets = [value for value in range(modulus) if value not in forbidden_offsets]
    answer = []
    for offset in offsets:
        answer.append([(centre + offset) % modulus for centre in centres])
        operations += len(centres)
    return answer, {
        "operations": operations,
        "wall_clock_sec": time.perf_counter() - started,
        "offsets": len(offsets),
    }


def _attack_outlier_frequency(inst):
    n = inst["rank"]
    modulus = inst["ground_size"]
    required = inst["required_bases"]
    omitted_frequency = Counter(value for pair in inst["omissions"] for value in pair)
    rows_by_colour = []
    for colour in range(n):
        allowed = [value for value in range(modulus) if value not in inst["omissions"][colour]]
        allowed.sort(key=lambda value: (omitted_frequency[value], value))
        rows_by_colour.append(allowed[:required])
    candidate = [
        [rows_by_colour[colour][basis] for colour in range(n)]
        for basis in range(required)
    ]
    return verify(inst, candidate)[0]


def _attack_greedy_left_to_right(inst):
    n = inst["rank"]
    modulus = inst["ground_size"]
    required = inst["required_bases"]
    used_by_colour = [set() for _ in range(n)]
    candidate = []
    for _ in range(required):
        taken = set()
        basis = []
        for colour in range(n):
            choice = next(
                (
                    value
                    for value in range(modulus)
                    if value not in inst["omissions"][colour]
                    and value not in used_by_colour[colour]
                    and value not in taken
                ),
                None,
            )
            if choice is None:
                return False
            basis.append(choice)
            taken.add(choice)
            used_by_colour[colour].add(choice)
        candidate.append(basis)
    return verify(inst, candidate)[0]


def _attack_random_restart(inst, seed, restarts=256):
    rng = random.Random(seed ^ int(canonical_key(inst)[:16], 16))
    for _ in range(restarts):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True
    return False


def _attack_consecutive_midpoint_shifts(inst):
    modulus = inst["ground_size"]
    inverse_two = (modulus + 1) // 2
    centres = [((left + right) * inverse_two) % modulus for left, right in inst["omissions"]]
    candidate = [
        [(centre + shift) % modulus for centre in centres]
        for shift in range(inst["required_bases"])
    ]
    return verify(inst, candidate)[0]


def _answer_atoms(answer):
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def _find_swap_corruption(inst):
    corrupted = copy.deepcopy(inst["answer"])
    first = corrupted[0]
    n = inst["rank"]
    for left in range(n):
        for right in range(left + 1, n):
            if first[right] in inst["omissions"][left] or first[left] in inst["omissions"][right]:
                first[left], first[right] = first[right], first[left]
                return corrupted
    # Deterministic fallback: swap one entry with an omitted label, which is
    # still a one-coordinate exchange if an unusually symmetric seed occurs.
    first[0], inst_value = inst["omissions"][0][0], first[0]
    _ = inst_value
    return corrupted


def selftest():
    report = {}
    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
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
                failures.append({"preset": preset, "seed": seed, "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
    }

    planted = shipping["answer"]
    drop_one = copy.deepcopy(planted)
    drop_one[0] = drop_one[0][:-1]
    duplicate = copy.deepcopy(planted)
    duplicate[-1] = list(duplicate[0])
    out_of_range = copy.deepcopy(planted)
    out_of_range[0][0] = shipping["ground_size"]
    corruptions = {
        "drop_one": drop_one,
        "swap_one": _find_swap_corruption(shipping),
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    corruption_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"accepted": ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(not value["accepted"] for value in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The common translations give the following schedule.\n```json\n<answer>\n"
        + json.dumps(planted)
        + "\n</answer>\n```\n"
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted and verify(shipping, parsed)[0],
        "parsed": parsed == planted,
    }

    samples = 200_000
    hits = 0
    sample_rng = random.Random(604211)
    sample_started = time.perf_counter()
    for _ in range(samples):
        if verify(shipping, random_candidate(shipping, sample_rng))[0]:
            hits += 1
    sample_wall = time.perf_counter() - sample_started
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "structure_aware_prior": "independent uniform ordered samples without replacement from every coloured input basis",
        "certificate_space": search_space(shipping),
        "wall_clock_sec": round(sample_wall, 6),
    }

    reference_answer, reference_stats = _reference_algorithm(shipping)
    compact_answer, compact_stats = _compact_route(shipping)
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": (
            isinstance(demo_count, int)
            and demo_count > 0
            and reference_answer is not None
            and verify(shipping, reference_answer)[0]
            and verify(shipping, compact_answer)[0]
        ),
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_sampled_valid_fraction": hits / samples,
        "demo_exact_solution_count": demo_count,
        "demo_certificate_space": search_space(demo),
        "reference_algorithm_operations": reference_stats["operations"],
        "reference_algorithm_edge_scans": reference_stats["edge_scans"],
        "reference_algorithm_augment_calls": reference_stats["augment_calls"],
        "reference_algorithm_wall_clock_sec": round(reference_stats["wall_clock_sec"], 6),
        "compact_route_operations": compact_stats["operations"],
        "sampling_wall_clock_sec": round(sample_wall, 6),
    }

    counts = {
        "outlier_global_frequency": 0,
        "greedy_left_to_right_no_backtracking": 0,
        "random_restart_256": 0,
        "consecutive_midpoint_shift_ansatz": 0,
    }
    reference_runs = []
    for seed in range(310, 318):
        instance = make_instance(seed=seed, **shipping_params)
        counts["outlier_global_frequency"] += int(_attack_outlier_frequency(instance))
        counts["greedy_left_to_right_no_backtracking"] += int(_attack_greedy_left_to_right(instance))
        counts["random_restart_256"] += int(_attack_random_restart(instance, seed))
        counts["consecutive_midpoint_shift_ansatz"] += int(
            _attack_consecutive_midpoint_shifts(instance)
        )
        found, stats = _reference_algorithm(instance)
        stats["solved"] = bool(found is not None and verify(instance, found)[0])
        reference_runs.append(stats)
    attacks = {
        name: {"successes": successes, "attempts": 8}
        for name, successes in counts.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attacks.values())
        and all(run["solved"] for run in reference_runs),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "bipartite regularisation plus repeated augmenting-path perfect matchings",
            "complexity": "O(n(n+2)^3) integer edge scans for this implementation",
            "operations": reference_stats["operations"],
            "max_operations": max(run["operations"] for run in reference_runs),
            "wall_clock_sec": round(reference_stats["wall_clock_sec"], 6),
            "max_wall_clock_sec": round(max(run["wall_clock_sec"] for run in reference_runs), 6),
            "solves": f"{sum(run['solved'] for run in reference_runs)}/8, as expected",
        },
    }

    doubled_params = {"n": 2 * shipping["rank"] + 1}
    doubled = make_instance(seed=991, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["rank"] > 2 * shipping["rank"]
        and search_space(doubled) > search_space(shipping),
        "shipping_n": shipping["rank"],
        "doubled_n": doubled["rank"],
        "doubled_verify_reason": doubled_reason,
        "shipping_answer_elements": _answer_atoms(shipping["answer"]),
        "doubled_answer_elements": _answer_atoms(doubled["answer"]),
        "search_space_growth_bits": search_space(doubled).bit_length()
        - search_space(shipping).bit_length(),
    }

    invariance_checks = 0
    carried_checks = 0
    failures = []
    unrelated = set()
    for seed in range(20):
        instance = make_instance(seed=8000 + seed, **shipping_params)
        key = canonical_key(instance)
        unrelated.add(key)
        rng = random.Random(9000 + seed)
        colour_order = list(range(instance["rank"]))
        ground_order = list(range(instance["ground_size"]))
        rng.shuffle(colour_order)
        rng.shuffle(ground_order)
        variants = [
            _permute_colours(instance, colour_order),
            _relabel_ground(instance, ground_order),
            _reverse_omission_pairs(instance),
            _relabel_ground(_permute_colours(instance, colour_order), ground_order),
        ]
        for variant in variants:
            invariance_checks += 1
            if canonical_key(variant) != key:
                failures.append({"seed": seed, "kind": "invariance"})
            carried_checks += 1
            if not verify(variant, variant["answer"])[0]:
                failures.append({"seed": seed, "kind": "carried_witness"})
    report["G8_canonical_key"] = {
        "pass": not failures and len(unrelated) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated": len(unrelated),
        "unrelated_attempts": 20,
        "transformations": [
            "colour permutation",
            "arbitrary ground relabelling",
            "order reversal inside omission pairs",
            "composition",
        ],
        "key_method": "WL refinement plus distance and multigraph invariants; not a complete graph-isomorphism canon",
        "failures": failures,
    }

    answer_blobs = [
        json.dumps(make_instance(seed=seed, **shipping_params)["answer"])
        for seed in range(100)
    ]
    answer_chars = max(map(len, answer_blobs))
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    intended_operations = compact_stats["operations"]
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_operations <= 300
    arms = copy.deepcopy(G9_ORACLE_RESULTS)
    bare = arms.get("bare", {"solved": 0, "attempts": 0})
    hinted = arms.get("hinted", {"solved": 0, "attempts": 0})
    placebo = arms.get("placebo", {"solved": 0, "attempts": 0})
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted.get("attempts") else None
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo.get("attempts") else None
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {"bare": bare, "hinted": hinted, "placebo": placebo},
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": arms.get("hinted_verdict", "not_run"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
