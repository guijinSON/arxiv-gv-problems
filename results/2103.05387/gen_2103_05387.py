"""Verified temporal-star exploration generator for arXiv:2103.05387.

The paper defines a strict exploration of a temporal star as one visit to every
leaf, returning to the centre between leaves.  Instances here have ``n`` visit
slots, where ``n`` is a power of two: slot s consists of times 2s+1 and 2s+2.
Every edge is available in a small set of slots.  Consequently an exploration
is exactly a perfect matching between star edges and slots.

Generation composes affine permutations of the binary vector space underlying
the slot labels.  It samples an invertible linear map and translation offsets
first, then carries one translated map as the exploration certificate.  It
never solves the emitted matching instance.
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
from collections import deque


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "For odd row size, the bitwise XOR of a row's slot numbers is an affine "
    "linear function of the edge number's binary bits."
)
PLACEBO_HINT: str = (
    "For every row, careful checking of its slot numbers and the edge number "
    "helps prevent subtle indexing mistakes."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "permutation",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "temporal star with integer edge-availability times",
        "strict temporal exploration visiting every leaf",
        "edge-to-visit-slot permutation",
    ],
    "verification_operations": [
        "exact integer time-set membership",
        "exact permutation and distinctness checks",
        "strict temporal-walk replay",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize that odd-cardinality row XORs reveal a hidden affine map over "
        "binary vectors and use it to align every star edge with one visit slot; "
        "without that invariant, the availability relation must be matched "
        "mechanically."
    ),
    "hardness_basis": (
        "Track B: the domain-standard Hopcroft-Karp bipartite-matching algorithm "
        "runs in O(E sqrt(V)); at the provisional hard preset (n=256, degree=3, "
        "seed 271828) it used 1,280 availability-edge inspections and 0.000210 "
        "seconds, while the row-XOR invariant uses 281 exact XOR operations and "
        "is not mechanically executable in a no-tool context without first "
        "recognizing the hidden binary-linear structure."
    ),
    "max_answer_tokens": 293,
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

DIFFICULTY: dict = {
    "demo": {"n": 8, "degree": 3},
    "easy": {"n": 64, "degree": 3},
    "medium": {"n": 128, "degree": 3},
    "hard": {"n": 256, "degree": 3},
}
SHIPPING_DIFFICULTY: str = "hard"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON list [s_0,...,s_(n-1)] of exactly n distinct slot indices. "
        "Every s_i is an integer in 0..n-1 listed in star-edge order. Thus the "
        "bounded candidate language is the n! permutations of the slots; whether "
        "each chosen slot is available to its edge is the predicate being checked."
    ),
    "bounds": {
        "atomic_elements": "n",
        "entry_min": 0,
        "entry_max": "n-1",
        "all_distinct": True,
        "candidate_count": "n!",
    },
}

# Filled only from transcripts written by scripts/harden.py.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted": {"solved": 0, "attempts": 0, "errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "errors": 4},
    "hinted_verdict": "pending",
    "blocker": "OpenRouter HTTP 403: account key total limit exceeded",
}

NOTES: str = (
    "Section 2 fixes the exact native definition: a temporal graph has integer "
    "time-sets, walks are strict, and StarExp asks for a closed walk from the "
    "star centre visiting every leaf. Section 3, Theorem 3.1 and Corollary 3.2 "
    "show StarExp(k) NP-complete for k at least four, while the Introduction "
    "records the polynomial-time algorithm for k at most three. Section 4, "
    "Corollary 4.5 gives an O(w^3 2^(3w) Lambda) interval-membership-width "
    "algorithm, and Corollary 5.5 makes evenly spaced instances FPT in k; these "
    "easy regimes rule out an undisclosed Track A claim. This generator instead "
    "uses the paper's temporal-star object directly and declares Track B. There "
    "are n two-time visit slots. Each of several affine binary permutations "
    "assigns every edge to a different slot, so choosing one affine offset "
    "constructs and certifies an exploration without solving. Because a complete "
    "strict exploration uses 2n traversals drawn from exactly 2n global times, "
    "every valid exploration is slot-aligned and verification is exact matching "
    "plus temporal replay. Plants and decoys are the same affine-offset "
    "distribution. Equal row degrees and equal slot frequencies defeat the "
    "outlier probe; shuffled presentation defeats first-fit; randomized greedy "
    "restarts strand unmatched edges; and ordinary modular-shift guesses fail "
    "because the hidden map is a dense random invertible binary-linear map. "
    "Hopcroft-Karp is intentionally disclosed and measured as the successful "
    "reference algorithm."
)


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_power_of_two(value):
    return _is_int(value) and value >= 1 and value & (value - 1) == 0


def _binary_rank(columns):
    """Return the rank of integer bit-vector columns over GF(2)."""

    pivots = {}
    for column in columns:
        value = column
        while value:
            pivot = value.bit_length() - 1
            if pivot in pivots:
                value ^= pivots[pivot]
            else:
                pivots[pivot] = value
                break
    return len(pivots)


def _linear_image(value, columns):
    result = 0
    while value:
        low_bit = value & -value
        result ^= columns[low_bit.bit_length() - 1]
        value ^= low_bit
    return result


def _row_map(inst):
    return {row["edge"]: row["slots"] for row in inst["rows"]}


def make_instance(n, seed=0, degree=3, **params) -> dict:
    """Compose binary-affine slot permutations and carry one exploration.

    ``n`` is a power-of-two number of leaves and visit slots.  Labels are bit
    vectors of width log2(n), represented as ordinary integers. ``degree`` is
    an odd number of equally distributed translation offsets, hence the number
    of allowed slots per edge.  No matching or search routine is called here.
    """

    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if not _is_power_of_two(n) or n < 8:
        raise ValueError("n must be a power-of-two integer at least 8")
    if not _is_int(degree) or not 3 <= degree < n or degree % 2 != 1:
        raise ValueError("degree must be an odd integer in 3..n-1")
    if not _is_int(seed):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    dimension = n.bit_length() - 1
    # Rejection sampling constructs an invertible map; it does not search for a
    # witness to the emitted instance.  The density condition rules out nearly
    # permutation matrices whose pattern would be a per-bit outlier.
    while True:
        columns = [rng.randrange(1, n) for _ in range(dimension)]
        if (
            _binary_rank(columns) == dimension
            and all(column.bit_count() >= 2 for column in columns)
        ):
            break
    offsets = rng.sample(range(n), degree)
    chosen_offset = rng.choice(offsets)

    rows = []
    for edge in range(n):
        slots = sorted(
            _linear_image(edge, columns) ^ offset
            for offset in offsets
        )
        rows.append({"edge": edge, "slots": slots})
    rng.shuffle(rows)

    answer = [
        _linear_image(edge, columns) ^ chosen_offset
        for edge in range(n)
    ]
    return {
        "family": "strict temporal-star slot exploration",
        "n": n,
        "degree": degree,
        "rows": rows,
        "time_rule": "slot s is the visit (2*s+1, 2*s+2)",
        "answer": answer,
    }


def render(inst) -> str:
    """Render a complete, self-contained temporal exploration problem."""

    n = inst["n"]
    lines = [
        "STRICT TEMPORAL-STAR EXPLORATION",
        "",
        f"There is a star with centre c and {n} leaf edges, numbered 0 through {n - 1}.",
        "A time-edge (i,t) means that leaf edge i may be traversed at integer time t.",
        "A strict temporal walk uses strictly increasing traversal times.",
        "A visit to a leaf traverses its edge from c to the leaf and later traverses",
        "the same edge back to c. A complete exploration visits every leaf exactly once",
        "and is therefore a closed strict temporal walk of exactly 2n traversals.",
        "",
        f"There are {n} numbered visit slots, 0 through {n - 1}. Slot s uses times",
        "2*s+1 outward and 2*s+2 back. For each edge, the line below lists exactly",
        "the slots in which both of those times are active. No other times are active.",
        "The row order is only presentation order; edge numbers determine answer order.",
        "",
        "EDGE : AVAILABLE SLOTS",
    ]
    for row in inst["rows"]:
        lines.append(f"{row['edge']} : " + " ".join(str(x) for x in row["slots"]))
    lines.extend([
        "",
        "Return a JSON list [s_0,...,s_(n-1)] of exactly n decimal integers, where",
        "s_i is the slot used by edge i. Indices are 0-based; entries must be distinct;",
        "repetitions and ellipses are forbidden; and every s_i must occur on edge i's line.",
        "Sorting visits by slot then replays the required strict closed temporal walk.",
        "",
        "Give your final answer inside <answer></answer> tags, as that JSON list.",
        "Example: <answer>[2,0,1]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Extract the last tagged/fenced JSON integer list; never raise on prose."""

    if not isinstance(text, str):
        return None
    try:
        tagged = _ANSWER_RE.findall(text)
        if tagged:
            payload = tagged[-1].strip()
            payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
            payload = re.sub(r"\s*```$", "", payload)
        else:
            fenced = re.findall(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text, re.I)
            if fenced:
                payload = fenced[-1]
            else:
                lists = re.findall(r"\[[\s\d,+\-]*\]", text)
                if not lists:
                    return None
                payload = lists[-1]
        value = json.loads(payload)
        if not isinstance(value, list):
            return None
        if any(not _is_int(item) for item in value):
            return None
        return value
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _validate_instance(inst):
    try:
        n = inst["n"]
        degree = inst["degree"]
        rows = inst["rows"]
    except (KeyError, TypeError):
        return False, "malformed instance"
    if not _is_power_of_two(n) or n < 8:
        return False, "malformed slot count"
    if not _is_int(degree) or not 3 <= degree < n or degree % 2 != 1:
        return False, "malformed row degree"
    if not isinstance(rows, list) or len(rows) != n:
        return False, "instance must contain one row per edge"
    seen_edges = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"edge", "slots"}:
            return False, "malformed availability row"
        edge = row["edge"]
        slots = row["slots"]
        if not _is_int(edge) or not 0 <= edge < n or edge in seen_edges:
            return False, "edge labels must be distinct integers in range"
        seen_edges.add(edge)
        if not isinstance(slots, list) or len(slots) != degree:
            return False, "availability row has wrong size"
        if any(not _is_int(slot) or not 0 <= slot < n for slot in slots):
            return False, "availability slot out of range"
        if slots != sorted(set(slots)):
            return False, "availability slots must be sorted and distinct"
    if seen_edges != set(range(n)):
        return False, "edge labels are incomplete"
    return True, "ok"


def verify(inst, answer):
    """Check any complete temporal exploration without reading ``inst['answer']``."""

    valid, reason = _validate_instance(inst)
    if not valid:
        return False, reason
    n = inst["n"]
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if any(not _is_int(slot) for slot in answer):
        return False, "every answer entry must be an integer"
    if len(answer) != n:
        return False, f"wrong length: expected exactly {n} slots"
    if any(slot < 0 or slot >= n for slot in answer):
        return False, f"slot index out of range 0..{n - 1}"
    if len(set(answer)) != n:
        return False, "slot indices must be distinct"

    rows = _row_map(inst)
    for edge, slot in enumerate(answer):
        if slot not in rows[edge]:
            return False, f"edge {edge} is not active throughout slot {slot}"

    # Exact replay in temporal order.  Slot distinctness makes this sequence use
    # all n slots, but replay it explicitly so verification remains about the
    # paper's temporal walk rather than only an abstract matching.
    ordered = sorted((slot, edge) for edge, slot in enumerate(answer))
    previous_time = 0
    visited = set()
    at_centre = True
    for slot, edge in ordered:
        outward = 2 * slot + 1
        backward = outward + 1
        if not at_centre or outward <= previous_time or backward <= outward:
            return False, "traversal times are not a strict closed walk"
        if edge in visited:
            return False, "an edge is visited more than once"
        at_centre = False
        previous_time = outward
        at_centre = True
        previous_time = backward
        visited.add(edge)
    if not at_centre or len(visited) != n:
        return False, "walk is not a complete closed exploration"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from the stated, structure-aware permutation language."""

    candidate = list(range(inst["n"]))
    rng.shuffle(candidate)
    return candidate


def search_space(inst):
    return math.factorial(inst["n"])


def _candidate_valid_fast(inst, answer, row_sets=None):
    n = inst["n"]
    if not isinstance(answer, list) or len(answer) != n or len(set(answer)) != n:
        return False
    if row_sets is None:
        row_sets = {edge: set(slots) for edge, slots in _row_map(inst).items()}
    return all(answer[edge] in row_sets[edge] for edge in range(n))


def enumerate_all(inst):
    """Count all explorations when the declared language has at most 200k words."""

    if search_space(inst) > 200_000:
        return None
    row_sets = {edge: set(slots) for edge, slots in _row_map(inst).items()}
    count = 0
    for candidate in itertools.permutations(range(inst["n"])):
        if all(candidate[edge] in row_sets[edge] for edge in range(inst["n"])):
            count += 1
    return count


def canonical_key(inst):
    """Complete invariant under leaf relabelling and availability-row order.

    A temporal star has no structure among its leaves, so with fixed integer
    times its isomorphism type is exactly the multiset of leaf time-sets.  Slot
    s deterministically stands for the time pair (2s+1,2s+2).
    """

    normalized_rows = sorted(tuple(row["slots"]) for row in inst["rows"])
    payload = {
        "n": inst["n"],
        "degree": inst["degree"],
        "time_sets": normalized_rows,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def escalate(params):
    """Increase decoy crowding at fixed answer length before reporting the cap."""

    current = dict(params)
    n = int(current.get("n", 256))
    degree = int(current.get("degree", 3))
    # At n=256, degree five leaves the row-XOR route at 299 operations.
    if n == 256 and degree < 5:
        current["degree"] = 5
        return current
    if n < 256:
        current["n"] = min(256, 2 * n)
        return current
    return "cap_bound"


def _hopcroft_karp(inst):
    """Domain-standard perfect matching, with exact edge-inspection counts."""

    adjacency = _row_map(inst)
    n = inst["n"]
    pair_left = [-1] * n
    pair_right = [-1] * n
    distance = [0] * n
    inspections = 0
    phases = 0

    def bfs():
        nonlocal inspections
        queue = deque()
        found = False
        for left in range(n):
            if pair_left[left] == -1:
                distance[left] = 0
                queue.append(left)
            else:
                distance[left] = -1
        while queue:
            left = queue.popleft()
            for right in adjacency[left]:
                inspections += 1
                mate = pair_right[right]
                if mate == -1:
                    found = True
                elif distance[mate] < 0:
                    distance[mate] = distance[left] + 1
                    queue.append(mate)
        return found

    def dfs(left):
        nonlocal inspections
        for right in adjacency[left]:
            inspections += 1
            mate = pair_right[right]
            if mate == -1 or (
                distance[mate] == distance[left] + 1 and dfs(mate)
            ):
                pair_left[left] = right
                pair_right[right] = left
                return True
        distance[left] = -1
        return False

    matched = 0
    while bfs():
        phases += 1
        progress = 0
        for left in range(n):
            if pair_left[left] == -1 and dfs(left):
                matched += 1
                progress += 1
        if progress == 0:
            break
    result = pair_left if matched == n else None
    return result, {
        "edge_inspections": inspections,
        "phases": phases,
        "matched": matched,
    }


def _attack_outlier_frequency(inst):
    rows = _row_map(inst)
    frequency = [0] * inst["n"]
    for slots in rows.values():
        for slot in slots:
            frequency[slot] += 1
    return [min(rows[edge], key=lambda s: (frequency[s], s)) for edge in range(inst["n"])]


def _attack_greedy_first_fit(inst, rng=None):
    order = [row["edge"] for row in inst["rows"]]
    if rng is not None:
        rng.shuffle(order)
    rows = _row_map(inst)
    used = set()
    answer = [None] * inst["n"]
    for edge in order:
        available = [slot for slot in rows[edge] if slot not in used]
        if not available:
            return None
        slot = rng.choice(available) if rng is not None else available[0]
        answer[edge] = slot
        used.add(slot)
    return answer


def _attack_modular_shift(inst):
    rows = _row_map(inst)
    n = inst["n"]
    for shift in rows[0]:
        candidate = [(edge + shift) % n for edge in range(n)]
        if _candidate_valid_fast(inst, candidate):
            return candidate
    return None


def _invariant_witness(inst):
    """Recover a binary-affine exploration using only rendered row data.

    This is the intended compact Track-B route, not generation.  Because the
    row degree is odd, XORing a row cancels the common translation an odd
    number of times and reveals ``linear_image(edge) XOR constant``.  Comparing
    row zero with each power-of-two row recovers the map's columns.  Dynamic
    programming then evaluates the affine map with one XOR per remaining edge.
    """

    rows = _row_map(inst)
    n = inst["n"]
    row_zero_xor = 0
    for slot in rows[0]:
        row_zero_xor ^= slot
    columns = []
    for bit in range(n.bit_length() - 1):
        row_xor = 0
        for slot in rows[1 << bit]:
            row_xor ^= slot
        columns.append(row_xor ^ row_zero_xor)
    answer = [rows[0][0]]
    for edge in range(1, n):
        low_bit = edge & -edge
        answer.append(
            answer[edge ^ low_bit] ^ columns[low_bit.bit_length() - 1]
        )
    return answer


def _relabeled(inst, permutation, reorder_rows=False, seed=0):
    """Relabel leaves and carry the slot-list witness through the map."""

    result = {
        key: value
        for key, value in inst.items()
        if key not in {"rows", "answer"}
    }
    rows = [
        {"edge": permutation[row["edge"]], "slots": list(row["slots"])}
        for row in inst["rows"]
    ]
    if reorder_rows:
        random.Random(seed).shuffle(rows)
    result["rows"] = rows
    answer = [None] * inst["n"]
    for old_edge, slot in enumerate(inst["answer"]):
        answer[permutation[old_edge]] = slot
    result["answer"] = answer
    return result


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(item) for item in value)
    return 1


def _intended_route_operations(params):
    # XOR row zero and each basis row, compare their aggregates with row zero,
    # then extend one chosen slot using one recovered-column XOR per edge.
    dimension = params["n"].bit_length() - 1
    return (
        (dimension + 1) * (params["degree"] - 1)
        + dimension
        + params["n"] - 1
    )


def selftest():
    report = {}

    # G1: every named rung, three seeds, exact JSON round-tripping.
    failures = []
    checks = 0
    for preset, kwargs in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **kwargs)
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok or json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=271828, **shipping)
    answer = inst["answer"]

    # G2: five distinct semantic failures and five distinct reasons.
    duplicate = list(answer)
    duplicate[-1] = duplicate[0]
    out_of_range = list(answer)
    out_of_range[-1] = inst["n"]
    swapped = None
    for left in range(inst["n"]):
        for right in range(left + 1, inst["n"]):
            candidate = list(answer)
            candidate[left], candidate[right] = candidate[right], candidate[left]
            if not verify(inst, candidate)[0]:
                swapped = candidate
                break
        if swapped is not None:
            break
    corruptions = {
        "drop_one": answer[:-1],
        "swap_two": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    corruption_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        if not ok:
            reasons.append(reason.split(":", 1)[0])
    report["G2_rejects_corruption"] = {
        "pass": (
            swapped is not None
            and all(item["rejected"] for item in corruption_results.values())
            and len(set(reasons)) == 5
        ),
        "attempts": len(corruption_results),
        "distinct_reasons": len(set(reasons)),
        "cases": corruption_results,
    }

    # G3: required tags inside a realistic fenced, prose-bearing response.
    response = (
        "I matched each temporal edge to one visit slot and replayed the walk.\n"
        "```json\n<answer>\n"
        + json.dumps(answer)
        + "\n</answer>\n```\nAll slots are used once."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer,
        "parsed_equals_answer": parsed == answer,
        "surrounding_prose_and_fence": True,
    }

    # G4 and G5 density: sample the exact permutation language. Distinctness is
    # explicit in the statement and therefore built into the prior; availability
    # membership remains the nontrivial predicate.
    trials = 200_000
    rng = random.Random(0x210305387)
    row_sets = {edge: set(slots) for edge, slots in _row_map(inst).items()}
    hits = 0
    guess_started = time.perf_counter()
    for _ in range(trials):
        if _candidate_valid_fast(inst, random_candidate(inst, rng), row_sets):
            hits += 1
    guess_seconds = time.perf_counter() - guess_started
    report["G4_guess_resistance"] = {
        "pass": hits / trials < 1e-6,
        "hits": hits,
        "total": trials,
        "observed_probability": hits / trials,
        "candidate_space": search_space(inst),
        "candidate_space_log2": round(math.log2(search_space(inst)), 3),
        "prior": "uniform over all permutations of the n visit slots",
        "wall_clock_sec": round(guess_seconds, 6),
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    reference_started = time.perf_counter()
    reference_answer, reference_counts = _hopcroft_karp(inst)
    reference_seconds = time.perf_counter() - reference_started
    reference_ok = reference_answer is not None and verify(inst, reference_answer)[0]
    compact_answer = _invariant_witness(inst)
    compact_ok, compact_reason = verify(inst, compact_answer)

    baseline_started = time.perf_counter()
    baseline_rng = random.Random(424242)
    baseline_success = False
    baseline_restarts = 256
    for _ in range(baseline_restarts):
        candidate = _attack_greedy_first_fit(inst, baseline_rng)
        if candidate is not None and _candidate_valid_fast(inst, candidate, row_sets):
            baseline_success = True
            break
    baseline_seconds = time.perf_counter() - baseline_started
    report["G5_density_and_baseline_cost"] = {
        "pass": (
            demo_count is not None
            and reference_ok
            and compact_ok
            and hits / trials < 1e-6
        ),
        "shipping_seed": 271828,
        "shipping_sample_hits": hits,
        "shipping_sample_total": trials,
        "shipping_solution_density": hits / trials,
        "demo_exact_valid_answers": demo_count,
        "demo_candidate_space": search_space(demo),
        "strongest_failing_attack": "randomized greedy first-fit, 256 restarts",
        "baseline_restarts": baseline_restarts,
        "baseline_success": baseline_success,
        "baseline_wall_clock_sec": round(baseline_seconds, 6),
        "reference_wall_clock_sec": round(reference_seconds, 6),
        "reference_edge_inspections": reference_counts["edge_inspections"],
        "reference_phases": reference_counts["phases"],
        "compact_route_verified": compact_ok,
        "compact_route_reason": compact_reason,
        "compact_route_operations": _intended_route_operations(shipping),
    }

    # G6: four tool-free attacks fail; matching is the successful Track-B reference.
    attacks = {
        "outlier_slot_frequency": {"successes": 0, "attempts": 8},
        "greedy_first_fit": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "in_context_modular_shift_ansatz": {"successes": 0, "attempts": 8},
    }
    attack_elapsed = {name: 0.0 for name in attacks}
    reference_successes = 0
    reference_operations = []
    reference_times = []
    for seed in range(10_000, 10_008):
        current = make_instance(seed=seed, **shipping)
        current_sets = {
            edge: set(slots) for edge, slots in _row_map(current).items()
        }
        candidates = {}

        started = time.perf_counter()
        candidates["outlier_slot_frequency"] = _attack_outlier_frequency(current)
        attack_elapsed["outlier_slot_frequency"] += time.perf_counter() - started

        started = time.perf_counter()
        candidates["greedy_first_fit"] = _attack_greedy_first_fit(current)
        attack_elapsed["greedy_first_fit"] += time.perf_counter() - started

        started = time.perf_counter()
        rr_rng = random.Random(seed ^ 0xA5A5A5)
        restart_candidate = None
        for _ in range(256):
            trial = _attack_greedy_first_fit(current, rr_rng)
            if trial is not None and _candidate_valid_fast(current, trial, current_sets):
                restart_candidate = trial
                break
        candidates["random_restart_256"] = restart_candidate
        attack_elapsed["random_restart_256"] += time.perf_counter() - started

        started = time.perf_counter()
        candidates["in_context_modular_shift_ansatz"] = _attack_modular_shift(current)
        attack_elapsed["in_context_modular_shift_ansatz"] += time.perf_counter() - started

        for name, candidate in candidates.items():
            if candidate is not None and verify(current, candidate)[0]:
                attacks[name]["successes"] += 1

        started = time.perf_counter()
        ref_answer, counts = _hopcroft_karp(current)
        reference_times.append(time.perf_counter() - started)
        reference_operations.append(counts["edge_inspections"])
        if ref_answer is not None and verify(current, ref_answer)[0]:
            reference_successes += 1

    for name in attacks:
        attacks[name]["wall_clock_sec"] = round(attack_elapsed[name], 6)
    all_failed = all(
        result["successes"] == 0 and result["attempts"] >= 8
        for result in attacks.values()
    )
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Hopcroft-Karp bipartite perfect matching",
            "complexity": "O(E sqrt(V))",
            "solves": f"{reference_successes}/8, as expected",
            "wall_clock_sec": round(sum(reference_times), 6),
            "operations": sum(reference_operations),
            "operation_unit": "availability-edge inspections across eight shipping instances",
            "per_instance_operations": reference_operations,
        },
    }

    # G7: double the ground set while preserving the answer form.
    doubled = dict(shipping)
    doubled["n"] = 2 * shipping["n"]
    doubled_inst = make_instance(seed=314159, **doubled)
    doubled_ok, doubled_reason = verify(doubled_inst, doubled_inst["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled_inst) > search_space(inst),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "candidate_space_log2_shipping": round(math.log2(search_space(inst)), 3),
        "candidate_space_log2_doubled": round(math.log2(search_space(doubled_inst)), 3),
        "doubled_verify_reason": doubled_reason,
    }

    # G8: leaf relabelling, row reordering, and their composition over 20 seeds.
    invariance_checks = 0
    real_transformations = 0
    key_failures = []
    # Use enough offset-set entropy that unrelated seeds do not collide merely
    # because two small binary set systems are translates of one another.
    small_params = {"n": 64, "degree": 5}
    for seed in range(20):
        base = make_instance(seed=50_000 + seed, **small_params)
        base_key = canonical_key(base)
        rng = random.Random(60_000 + seed)
        permutation = list(range(base["n"]))
        rng.shuffle(permutation)
        identity = list(range(base["n"]))
        for use_relabel, reorder_rows in ((False, True), (True, False), (True, True)):
            transformed = _relabeled(
                base,
                permutation if use_relabel else identity,
                reorder_rows=reorder_rows,
                seed=70_000 + seed,
            )
            invariance_checks += 1
            if canonical_key(transformed) != base_key:
                key_failures.append({
                    "seed": seed,
                    "leaf_relabel": use_relabel,
                    "row_reorder": reorder_rows,
                })
            carried = transformed["answer"] if use_relabel else base["answer"]
            if verify(transformed, carried)[0]:
                real_transformations += 1
    unrelated = [
        canonical_key(make_instance(seed=80_000 + seed, **small_params))
        for seed in range(20)
    ]
    report["G8_canonical_key"] = {
        "pass": (
            not key_failures
            and real_transformations == invariance_checks
            and len(set(unrelated)) == 20
        ),
        "invariance_checks": invariance_checks,
        "real_transformations_verified": real_transformations,
        "unrelated_attempts": 20,
        "unrelated_distinct_keys": len(set(unrelated)),
        "failures": key_failures,
        "canonical_scope": "complete for temporal-star leaf relabelling at fixed time labels",
    }

    # G9(a,b) is transcript-owned and diagnostic only; G9(c) is the sole gate
    # and is measured locally and exactly.
    # emit.sh uses json.dumps with its normal separators, so measure that exact
    # representation rather than a more flattering compact encoding.
    answer_blob = json.dumps(answer)
    worst_blob = json.dumps(list(range(inst["n"])))
    arms = {
        name: {
            "solved": G9_ORACLE_RESULTS[name]["solved"],
            "attempts": G9_ORACLE_RESULTS[name]["attempts"],
            "errors": G9_ORACLE_RESULTS[name].get("errors", 0),
        }
        for name in ("bare", "hinted", "placebo")
    }
    hinted = arms["hinted"]["solved"]
    placebo = arms["placebo"]["solved"]
    hinted_minus_placebo = None
    if (
        isinstance(hinted, int)
        and isinstance(placebo, int)
        and arms["hinted"]["attempts"]
        and arms["placebo"]["attempts"]
    ):
        hinted_minus_placebo = (
            hinted / arms["hinted"]["attempts"]
            - placebo / arms["placebo"]["attempts"]
        )
    intended_ops = _intended_route_operations(shipping)
    within_caps = (
        len(answer_blob) <= 2000
        and _answer_atoms(answer) <= 256
        and intended_ops <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "oracle_blocker": G9_ORACLE_RESULTS.get("blocker"),
        "answer_chars": len(answer_blob),
        "answer_tokens": math.ceil(len(answer_blob) / 4),
        "answer_elements": _answer_atoms(answer),
        "worst_case_answer_chars": len(worst_blob),
        "worst_case_answer_tokens": math.ceil(len(worst_blob) / 4),
        "intended_route_operations": intended_ops,
        "within_caps": within_caps,
    }

    report["paper"] = "arXiv:2103.05387"
    report["family"] = "strict temporal-star slot exploration"
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping)
    report["all_passed"] = all(
        value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
