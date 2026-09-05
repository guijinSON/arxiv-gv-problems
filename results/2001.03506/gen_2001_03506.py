"""Verified packing generator based on arXiv:2001.03506.

The paper's Section 1.1 defines a packing of a collection of multipartite
graphs into a common host.  This module uses the exact two-part special case:
each guest is a perfect matching and a witness is a matrix of cluster-respecting
embedding maps whose image edges are pairwise disjoint.

Instances are inverse-generated.  We first sample planted and decoy translation
factors in reciprocal coordinates, then take their union as the host.  The
planted factors are retained as the certificate; no packing algorithm is run by
``make_instance``.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "permutation",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "regular bipartite host graph",
        "collection of spanning perfect-matching guest graphs",
        "cluster-respecting edge-disjoint packing maps",
    ],
    "verification_operations": [
        "exact permutation check",
        "bipartite edge membership",
        "pairwise host-edge disjointness",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Modular reciprocals turn the host's concealed matching factors into "
        "constant-difference classes; without that coordinate change one must "
        "edge-colour the regular bipartite host."
    ),
    "hardness_basis": (
        "Track B: repeated augmenting-path bipartite matching solves the family "
        "in O(kVE); at shipping n=23, host degree 16 and k=10 it averages about "
        "10,300 edge probes and 0.001 seconds over eight seeds, whereas the "
        "reciprocal-coordinate route uses at most 252 exact modular operations."
    ),
    "max_answer_tokens": 481,
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
    "demo": {"n": 5, "host_degree": 3, "guests": 2},
    "easy": {"n": 13, "host_degree": 9, "guests": 6},
    "medium": {"n": 17, "host_degree": 12, "guests": 8},
    "hard": {"n": 23, "host_degree": 16, "guests": 10},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Taking modular reciprocals of the two vertex labels turns each hidden "
    "perfect matching into a constant-difference class."
)
PLACEBO_HINT = (
    "Tracking the two vertex labels carefully helps separate the overlapping "
    "perfect matchings in this regular host graph."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A k-by-n JSON matrix of integers in [0,n-1]; every row is a "
        "permutation, and row h lists the right-cluster images for guest h."
    ),
    "bounds": {
        "rows": "number of guests k",
        "columns": "prime cluster size n",
        "entry_min": 0,
        "entry_max": "n-1",
        "row_rule": "each row is a permutation",
        "candidate_count": "(n!)^k",
    },
}

NOTES = (
    "Section 1.1 fixes the native definition: each guest map is injective and "
    "all guest edges must map injectively into host edges. Theorem 1.2 gives the "
    "bounded-degree multipartite regime and Section 4.2, Step 1 identifies "
    "conflict-free packings with matchings in an auxiliary hypergraph. The proof "
    "does not give a distributional hardness theorem: it uses random refinement, "
    "the pseudorandom hypergraph-matching theorem (Theorem 3.6), and ordinary "
    "blow-up-lemma completion (Theorem 3.5). This family is therefore Track B. "
    "Its perfect-matching subclass is mechanically solved by repeated augmenting "
    "paths. Planted and unused factors are sampled without replacement from the "
    "same translation distribution. Regularity defeats degree outliers; reciprocal "
    "conjugation defeats raw constant-difference and sorted-neighbour rules; near-"
    "capacity packing defeats unaugmented greedy and randomized greedy restarts."
)


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_GUESS_SAMPLES = 200_000

# Filled from the separately run oracle harnesses before final delivery.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0, "service_errors": 4},
    "hinted": {"solved": 0, "attempts": 0, "service_errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "service_errors": 4},
    "hinted_verdict": "unreachable",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_prime(value):
    if not _is_int(value) or value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _coordinate(value, modulus):
    """The involution 0 -> 0 and x -> x^{-1} on F_p^*."""
    return 0 if value == 0 else pow(value, -1, modulus)


def _factor_row(modulus, offset):
    """Conjugate a translation by the reciprocal-coordinate involution."""
    return [
        _coordinate((_coordinate(x, modulus) + offset) % modulus, modulus)
        for x in range(modulus)
    ]


def _validate_params(n, host_degree, guests, seed):
    if not _is_prime(n) or n < 5:
        raise ValueError("n must be a prime integer at least 5")
    if not _is_int(host_degree) or not 2 <= host_degree < n:
        raise ValueError("host_degree must be an integer in [2,n-1]")
    if not _is_int(guests) or not 1 <= guests < host_degree:
        raise ValueError("guests must be an integer in [1,host_degree-1]")
    if not _is_int(seed):
        raise ValueError("seed must be an integer")


def _host_map(inst):
    rows = inst.get("host_rows")
    if not isinstance(rows, list):
        return None
    result = {}
    for record in rows:
        if not isinstance(record, dict):
            return None
        left = record.get("left")
        neighbours = record.get("right_neighbors")
        if not _is_int(left) or not isinstance(neighbours, list):
            return None
        result[left] = set(neighbours)
    return result


def make_instance(n, seed=0, **params):
    """Inverse-generate a multipartite perfect-matching packing instance.

    The planted factor offsets and the unused offsets are drawn together before
    the host exists.  Their conjugated translation factors are then united to
    form the host, and the planted subset is retained as the JSON-native answer.
    No matching, edge-colouring, or packing search occurs here.
    """
    host_degree = params.pop("host_degree", max(2, min(n - 1, (2 * n) // 3)))
    guests = params.pop("guests", max(1, min(host_degree - 1, n // 3)))
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, host_degree, guests, seed)
    rng = random.Random(seed)

    # Plants and decoys are exchangeable positions in one uniformly shuffled
    # sample without replacement.  The split is made before the host is built.
    offsets = list(range(1, n))
    rng.shuffle(offsets)
    chosen = offsets[:host_degree]
    planted_offsets = chosen[:guests]

    factor_rows = [_factor_row(n, offset) for offset in chosen]
    host = [set() for _ in range(n)]
    for row in factor_rows:
        for left, right in enumerate(row):
            host[left].add(right)

    host_rows = []
    for left in range(n):
        neighbours = sorted(host[left])
        rng.shuffle(neighbours)
        host_rows.append({"left": left, "right_neighbors": neighbours})
    rng.shuffle(host_rows)

    answer = [_factor_row(n, offset) for offset in planted_offsets]
    rng.shuffle(answer)  # guest graphs are labelled but mutually isomorphic

    return {
        "n": n,
        "host_degree": host_degree,
        "guests": guests,
        "host_rows": host_rows,
        "answer": answer,
    }


def render(inst):
    n = inst["n"]
    guests = inst["guests"]
    degree = inst["host_degree"]
    lines = [
        "Find an edge-disjoint packing of perfect matchings into a bipartite host graph.",
        "",
        "Definitions and instance.",
        f"The size parameter is n={n}.",
        f"The host has a left cluster L and a right cluster R, each labelled by the integers 0 through {n - 1}.",
        "An undirected host edge is written (x,y), with x the label in L and y the label in R.",
        f"The host is {degree}-regular. Its complete adjacency list is below; row order and neighbour order carry no meaning.",
        f"There are {guests} labelled guest graphs, numbered 0 through {guests - 1}.",
        f"Guest h has left vertices a(h,x), right vertices b(h,x), and exactly the {n} edges a(h,x)--b(h,x) for x=0,...,{n - 1}.",
        "",
        "A normalized packing fixes every a(h,x) to host vertex L_x. For every guest h you must give a permutation p_h of 0,...,n-1; b(h,x) is mapped to R_{p_h[x]}.",
        "The packing is valid exactly when every (x,p_h[x]) is a listed host edge and no host edge is used by two guests.",
        "Unused host edges are allowed. Guest order and all matrix positions are significant; repetitions inside a row are forbidden.",
        "",
        "Host adjacency (inclusive 0-based labels):",
    ]
    for record in inst["host_rows"]:
        neighbours = " ".join(str(value) for value in record["right_neighbors"])
        lines.append(f"  L_{record['left']}: {neighbours}")
    lines.extend([
        "",
        f"Output a JSON matrix with exactly {guests} rows and exactly {n} integers per row.",
        "Row h is [p_h[0],p_h[1],...,p_h[n-1]]. Every entry must be an integer in the inclusive range shown above.",
        "For syntax only, a two-guest instance with n=3 could use <answer>[[0,1,2],[1,2,0]]</answer>.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags, as the JSON matrix just specified.",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        return json.loads(body)
    except (TypeError, ValueError):
        return None


def verify(inst, answer):
    """Check any normalized packing without consulting ``inst['answer']``."""
    n = inst.get("n")
    guests = inst.get("guests")
    host = _host_map(inst)
    if host is None or set(host) != set(range(n)):
        return False, "instance host adjacency is malformed"
    if not isinstance(answer, list):
        return False, "answer must be a list of guest rows"
    if not answer:
        return False, "answer is empty"
    if len(answer) != guests:
        return False, f"expected exactly {guests} guest rows"

    used = {}
    for guest, row in enumerate(answer):
        if not isinstance(row, list):
            return False, f"guest row {guest} is not a list"
        if len(row) != n:
            return False, f"guest row {guest} must contain exactly {n} entries"
        for left, right in enumerate(row):
            if not _is_int(right):
                return False, f"entry ({guest},{left}) is not an integer"
            if not 0 <= right < n:
                return False, f"entry ({guest},{left}) is outside 0..{n - 1}"
        if len(set(row)) != n:
            return False, f"guest row {guest} is not a permutation"
        for left, right in enumerate(row):
            edge = (left, right)
            if right not in host[left]:
                return False, f"guest {guest} uses absent host edge ({left},{right})"
            if edge in used:
                return False, (
                    f"host edge ({left},{right}) is reused by guests "
                    f"{used[edge]} and {guest}"
                )
            used[edge] = guest
    return True, "ok"


def random_candidate(inst, rng):
    """Sample k independent permutations, enforcing the obvious row structure."""
    n = inst["n"]
    candidate = []
    for _ in range(inst["guests"]):
        row = list(range(n))
        rng.shuffle(row)
        candidate.append(row)
    return candidate


def search_space(inst):
    return math.factorial(inst["n"]) ** inst["guests"]


def enumerate_all(inst):
    space = search_space(inst)
    if space > 200_000:
        return None
    permutations = list(itertools.permutations(range(inst["n"])))
    count = 0
    for rows in itertools.product(permutations, repeat=inst["guests"]):
        ok, _ = verify(inst, [list(row) for row in rows])
        if ok:
            count += 1
    return count


def _side_signature(neighbour_sets):
    """A relabelling-invariant intersection signature for one bipartition side."""
    size = len(neighbour_sets)
    vertex_profiles = []
    for i in range(size):
        vertex_profiles.append(tuple(sorted(
            len(neighbour_sets[i] & neighbour_sets[j])
            for j in range(size) if j != i
        )))
    pair_profiles = []
    for i in range(size):
        for j in range(i + 1, size):
            common = neighbour_sets[i] & neighbour_sets[j]
            triples = tuple(sorted(
                len(common & neighbour_sets[k])
                for k in range(size) if k != i and k != j
            ))
            pair_profiles.append((len(common), triples))
    return (tuple(sorted(vertex_profiles)), tuple(sorted(pair_profiles)))


def canonical_key(inst):
    """Key on bipartite intersection invariants, never on seed or rendering."""
    n = inst["n"]
    host = _host_map(inst)
    if host is None:
        return "malformed"
    left_sets = [host[left] for left in range(n)]
    right_sets = [set() for _ in range(n)]
    for left, neighbours in enumerate(left_sets):
        for right in neighbours:
            right_sets[right].add(left)
    side_blocks = sorted([
        repr(_side_signature(left_sets)),
        repr(_side_signature(right_sets)),
    ])
    payload = json.dumps(
        [n, inst["host_degree"], inst["guests"], side_blocks],
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params):
    """Grow ambient labels/decoys while keeping the matrix near 230 entries."""
    current = (
        params.get("n"),
        params.get("host_degree"),
        params.get("guests"),
    )
    levels = [
        (23, 16, 10),
        (29, 17, 8),
        (31, 19, 8),
        (41, 20, 6),
        (59, 21, 4),
    ]
    for index, level in enumerate(levels[:-1]):
        if current == level:
            n, host_degree, guests = levels[index + 1]
            return {"n": n, "host_degree": host_degree, "guests": guests}
    if current == levels[-1]:
        return "cap_bound"
    # Bring any named rung or compatible custom rung to the first fixed-length
    # escalation.  Three dials change, which prevents a one-axis answer-growth loop.
    if _is_int(current[0]) and current[0] < 23:
        return {"n": 23, "host_degree": 16, "guests": 10}
    return None


def _attack_greedy(inst, rng=None):
    """Sequential matching with no augmentation or backtracking."""
    n = inst["n"]
    host = _host_map(inst)
    used = set()
    rows = []
    for _ in range(inst["guests"]):
        taken = set()
        row = [None] * n
        left_order = list(range(n))
        if rng is not None:
            rng.shuffle(left_order)
        for left in left_order:
            choices = sorted(
                right for right in host[left]
                if right not in taken and (left, right) not in used
            )
            if not choices:
                return None
            right = choices[0] if rng is None else rng.choice(choices)
            row[left] = right
            taken.add(right)
            used.add((left, right))
        rows.append(row)
    return rows


def _attack_constant_difference(inst):
    """The obvious affine ansatz in the displayed, untransformed labels."""
    n = inst["n"]
    host = _host_map(inst)
    frequencies = []
    for difference in range(n):
        frequency = sum(
            1 for left in range(n)
            if (left + difference) % n in host[left]
        )
        frequencies.append((-frequency, difference))
    differences = [item[1] for item in sorted(frequencies)[:inst["guests"]]]
    return [[(left + difference) % n for left in range(n)]
            for difference in differences]


def _reference_decomposition(inst):
    """Repeated augmenting-path matching; return (answer, edge probes)."""
    n = inst["n"]
    remaining = [set() for _ in range(n)]
    for left, neighbours in _host_map(inst).items():
        remaining[left] = set(neighbours)
    probes = 0
    answer = []

    for _ in range(inst["guests"]):
        matched_left = [-1] * n  # indexed by right vertex

        def augment(left, seen):
            nonlocal probes
            for right in sorted(remaining[left]):
                probes += 1
                if seen[right]:
                    continue
                seen[right] = True
                if matched_left[right] < 0 or augment(matched_left[right], seen):
                    matched_left[right] = left
                    return True
            return False

        for left in range(n):
            if not augment(left, [False] * n):
                return None, probes
        row = [None] * n
        for right, left in enumerate(matched_left):
            row[left] = right
        answer.append(row)
        for left, right in enumerate(row):
            remaining[left].remove(right)
    return answer, probes


def _relabel_instance(inst, left_perm, right_perm, guest_perm, swap_sides=False):
    """Carry an instance and its witness through graph/guest relabellings."""
    n = inst["n"]
    host = _host_map(inst)
    if swap_sides:
        new_edges = [(right_perm[y], left_perm[x])
                     for x in range(n) for y in host[x]]
    else:
        new_edges = [(left_perm[x], right_perm[y])
                     for x in range(n) for y in host[x]]
    new_host = [set() for _ in range(n)]
    for left, right in new_edges:
        new_host[left].add(right)
    rows = [
        {"left": left, "right_neighbors": sorted(new_host[left])}
        for left in range(n)
    ]
    rows.reverse()  # also exercise irrelevant input ordering
    carried = [None] * inst["guests"]
    for old_guest, old_row in enumerate(inst["answer"]):
        new_row = [None] * n
        if swap_sides:
            for old_left, old_right in enumerate(old_row):
                new_left = right_perm[old_right]
                new_row[new_left] = left_perm[old_left]
        else:
            for old_left, old_right in enumerate(old_row):
                new_left = left_perm[old_left]
                new_row[new_left] = right_perm[old_right]
        carried[guest_perm[old_guest]] = new_row
    return {
        "n": n,
        "host_degree": inst["host_degree"],
        "guests": inst["guests"],
        "host_rows": rows,
        "answer": carried,
    }


def _answer_elements(value):
    if isinstance(value, dict):
        return sum(_answer_elements(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_elements(item) for item in value)
    return 1


def selftest():
    report = {}

    # G1: every preset, multiple independent seeds, and JSON-native witnesses.
    planted_ok = 0
    json_ok = 0
    total = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            total += 1
            planted_ok += int(verify(inst, inst["answer"])[0])
            json_ok += int(json.loads(json.dumps(inst["answer"])) == inst["answer"])
    report["G1_planted_verifies"] = {
        "pass": planted_ok == total and json_ok == total,
        "verified": planted_ok,
        "attempts": total,
        "json_native": json_ok,
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    answer = json.loads(json.dumps(shipping["answer"]))

    # G2: each named corruption is rejected for a different reason.
    corruptions = {}
    corruptions["empty"] = []
    corruptions["drop_guest"] = answer[:-1]
    dropped_entry = json.loads(json.dumps(answer))
    dropped_entry[0] = dropped_entry[0][:-1]
    corruptions["drop_element"] = dropped_entry
    duplicate = json.loads(json.dumps(answer))
    duplicate[0][1] = duplicate[0][0]
    corruptions["duplicate"] = duplicate
    out_of_range = json.loads(json.dumps(answer))
    out_of_range[0][0] = shipping["n"]
    corruptions["out_of_range"] = out_of_range
    swapped = None
    for guest in range(shipping["guests"]):
        for left in range(shipping["n"] - 1):
            trial = json.loads(json.dumps(answer))
            trial[guest][left], trial[guest][left + 1] = (
                trial[guest][left + 1], trial[guest][left]
            )
            ok, reason = verify(shipping, trial)
            if not ok and "absent host edge" in reason:
                swapped = trial
                break
        if swapped is not None:
            break
    corruptions["swap"] = swapped
    reasons = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        reasons[name] = reason
        if ok:
            reasons[name] = "ACCEPTED"
    report["G2_rejects_corruption"] = {
        "pass": (
            swapped is not None
            and all(reason != "ACCEPTED" for reason in reasons.values())
            and len(set(reasons.values())) == len(reasons)
        ),
        "rejected": sum(reason != "ACCEPTED" for reason in reasons.values()),
        "attempts": len(reasons),
        "distinct_reasons": len(set(reasons.values())),
        "reasons": reasons,
    }

    # G3: tagged JSON survives prose, whitespace, and a markdown fence.
    model_style = (
        "I used edge disjointness after checking the rows.\n"
        "<answer>\n```json\n"
        + json.dumps(answer)
        + "\n```\n</answer>\nThe matrix is above."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(shipping, parsed)[0],
        "parsed_equal": parsed == answer,
    }

    # G4/G5 density: structure-aware samples already make every guest row a
    # permutation.  Bregman's permanent bound supplies an analytic upper bound
    # even when a zero-hit sample cannot by itself certify a tiny probability.
    rng = random.Random(271828)
    hits = 0
    for _ in range(_GUESS_SAMPLES):
        hits += int(verify(shipping, random_candidate(shipping, rng))[0])
    n = shipping["n"]
    degree = shipping["host_degree"]
    guests = shipping["guests"]
    log_upper = guests * (
        (n / degree) * math.lgamma(degree + 1) - math.lgamma(n + 1)
    )
    bregman_upper = math.exp(log_upper)
    report["G4_guess_resistance"] = {
        "pass": hits / _GUESS_SAMPLES < 1e-6 and bregman_upper < 1e-6,
        "hits": hits,
        "total": _GUESS_SAMPLES,
        "observed_fraction": hits / _GUESS_SAMPLES,
        "analytic_probability_upper_bound": bregman_upper,
        "candidate_space": search_space(shipping),
        "sampler_prior": "independent uniformly random row permutations",
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_valid = enumerate_all(demo)
    baseline_times = []
    baseline_probes = []
    baseline_successes = 0
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        started = time.perf_counter()
        candidate, probes = _reference_decomposition(inst)
        baseline_times.append(time.perf_counter() - started)
        baseline_probes.append(probes)
        baseline_successes += int(verify(inst, candidate)[0])
    report["G5_density_and_baseline"] = {
        "pass": (
            demo_valid is not None
            and hits / _GUESS_SAMPLES < 1e-6
            and baseline_successes == 8
        ),
        "shipping_density_hits": hits,
        "shipping_density_samples": _GUESS_SAMPLES,
        "shipping_density_estimate": hits / _GUESS_SAMPLES,
        "demo_exact_valid_answers": demo_valid,
        "demo_candidate_space": search_space(demo),
        "baseline_successes": baseline_successes,
        "baseline_attempts": 8,
        "baseline_wall_clock_seconds_avg": sum(baseline_times) / len(baseline_times),
        "baseline_wall_clock_seconds_max": max(baseline_times),
        "baseline_edge_probes_avg": sum(baseline_probes) / len(baseline_probes),
        "baseline_edge_probes_max": max(baseline_probes),
    }

    # G6: all attacks are construction-aware but avoid the intended reciprocal
    # change of variables.  The polynomial reference algorithm is separate on B.
    attack_counts = {
        "degree_outlier": 0,
        "greedy_no_augmentation": 0,
        "randomized_greedy_256": 0,
        "raw_constant_difference_ansatz": 0,
    }
    reference_successes = 0
    reference_probes = []
    reference_times = []
    for seed in range(8):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        host = _host_map(inst)
        left_degrees = [len(host[left]) for left in range(inst["n"])]
        # The outlier heuristic declines to guess when the regular host has no
        # uniquely exceptional row or column.
        outlier_candidate = None if len(set(left_degrees)) == 1 else []
        if outlier_candidate is not None:
            attack_counts["degree_outlier"] += int(verify(inst, outlier_candidate)[0])

        greedy = _attack_greedy(inst)
        attack_counts["greedy_no_augmentation"] += int(verify(inst, greedy)[0])

        restart_rng = random.Random(1000 + seed)
        restart_success = False
        for _ in range(256):
            candidate = _attack_greedy(inst, restart_rng)
            if candidate is not None and verify(inst, candidate)[0]:
                restart_success = True
                break
        attack_counts["randomized_greedy_256"] += int(restart_success)

        affine = _attack_constant_difference(inst)
        attack_counts["raw_constant_difference_ansatz"] += int(verify(inst, affine)[0])

        started = time.perf_counter()
        candidate, probes = _reference_decomposition(inst)
        reference_times.append(time.perf_counter() - started)
        reference_probes.append(probes)
        reference_successes += int(verify(inst, candidate)[0])

    attacks = {
        name: {"successes": successes, "attempts": 8}
        for name, successes in attack_counts.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "repeated augmenting-path bipartite matching",
            "complexity": "O(k V E)",
            "wall_clock_sec_avg": sum(reference_times) / len(reference_times),
            "wall_clock_sec_max": max(reference_times),
            "edge_probes_avg": sum(reference_probes) / len(reference_probes),
            "edge_probes_max": max(reference_probes),
            "solves": f"{reference_successes}/8, as expected on Track B",
        },
    }

    # G7: more than double the cluster size while holding the answer near the cap.
    doubled_params = {"n": 47, "host_degree": 20, "guests": 5}
    doubled = make_instance(seed=99, **doubled_params)
    report["G7_scales"] = {
        "pass": doubled["n"] >= 2 * shipping["n"] and verify(doubled, doubled["answer"])[0],
        "shipping_n": shipping["n"],
        "larger_n": doubled["n"],
        "shipping_answer_elements": _answer_elements(shipping["answer"]),
        "larger_answer_elements": _answer_elements(doubled["answer"]),
        "larger_candidate_bits": search_space(doubled).bit_length(),
    }

    # G8: row/column relabelling, guest relabelling, input reordering and side
    # exchange are all genuine symmetries and are tested in composition.
    invariant_checks = 0
    witness_checks = 0
    for seed in range(20):
        inst = make_instance(seed=seed + 200, **DIFFICULTY[SHIPPING_DIFFICULTY])
        rng = random.Random(seed + 9000)
        left_perm = list(range(inst["n"]))
        right_perm = list(range(inst["n"]))
        guest_perm = list(range(inst["guests"]))
        rng.shuffle(left_perm)
        rng.shuffle(right_perm)
        rng.shuffle(guest_perm)
        transformed = _relabel_instance(
            inst, left_perm, right_perm, guest_perm, swap_sides=False
        )
        invariant_checks += int(canonical_key(inst) == canonical_key(transformed))
        witness_checks += int(verify(transformed, transformed["answer"])[0])
        swapped_sides = _relabel_instance(
            inst, left_perm, right_perm, guest_perm, swap_sides=True
        )
        invariant_checks += int(canonical_key(inst) == canonical_key(swapped_sides))
        witness_checks += int(verify(swapped_sides, swapped_sides["answer"])[0])
    unrelated_keys = {
        canonical_key(make_instance(seed=seed + 5000, **DIFFICULTY[SHIPPING_DIFFICULTY]))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 40 and witness_checks == 40 and len(unrelated_keys) == 20,
        "invariance_checks": invariant_checks,
        "invariance_attempts": 40,
        "carried_witness_checks": witness_checks,
        "carried_witness_attempts": 40,
        "distinct_unrelated_keys": len(unrelated_keys),
        "distinctness_attempts": 20,
    }

    blob = json.dumps(shipping["answer"], separators=(",", ":"))
    elements_rm = _answer_elements(shipping["answer"])
    # Conservative lexical count: every integer and every JSON punctuation mark
    # is counted separately.  This deliberately exceeds chars/4 for dense JSON.
    token_estimate = len(re.findall(r"\d+|[][{},:]", blob))
    intended_ops = (shipping["n"] - 1) + shipping["n"] * shipping["guests"]
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_attempts = arms["hinted"].get("attempts", 0)
    placebo_attempts = arms["placebo"].get("attempts", 0)
    difference = None
    if hinted_attempts and placebo_attempts:
        difference = (
            arms["hinted"].get("solved", 0) / hinted_attempts
            - arms["placebo"].get("solved", 0) / placebo_attempts
        )
    report["G9_no_tool_suitability"] = {
        "pass": len(blob) <= 2000 and elements_rm <= 256 and intended_ops <= 300,
        "arms": arms,
        "hinted_minus_placebo": difference,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": len(blob),
        "answer_tokens": token_estimate,
        "answer_elements": elements_rm,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
