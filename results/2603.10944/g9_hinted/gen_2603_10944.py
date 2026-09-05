"""Verified generator for one-unit minimally-unsatisfiable subsets of 2-CNFs.

The source is arXiv:2603.10944.  Theorem 19 and Corollary 20 identify an MUS
containing a unit clause {x} with a nearly regular implication path beginning
at x.  This module presents a large layered 2-CNF succinctly and asks for such
a path, encoded by one rule choice per layer.

Generation is inverse: a sequence of layer states is sampled first, one rule
per layer is made to telescope along it, and exchangeable decoy rules fill the
other columns.  The generator never searches the finished instance.
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
from collections import Counter


TRACK = "B"


PROBLEM_PROFILE = {
    "native_domain": "logic",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "succinctly specified 2-CNF clause-set",
        "implication digraph",
        "nearly regular implication path certifying a one-unit MUS",
    ],
    "verification_operations": [
        "exact modular addition",
        "exact rule-index and layer-order comparison",
        "exact implication-chain endpoint comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The first component of each translation is a unique difference of two "
        "powers of two, and the held path is the sole row-to-row chain whose "
        "decoded source matches the current landmark; without that invariant one "
        "must perform reachability or meet-in-the-middle search."
    ),
    "hardness_basis": (
        "Track B: Corollary 20 gives linear-time implication-graph reachability "
        "O(ell(F)); the hard preset denotes 528,942,025 clauses, while exact "
        "bidirectional layer search uses O(d^(n/2)) and its measured transition "
        "count and wall time are reported by selftest; decoding the powers-of-two "
        "landmark invariant takes at most 272 exact operations."
    ),
    "max_answer_tokens": 32,
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


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list [[1,j1],...,[n,jn]] containing every layer exactly once in "
        "increasing order, where each rule number ji is an integer from 1 through "
        "the displayed branching factor d.  Thus the bounded language has d^n "
        "members and already enforces every stated shape constraint."
    ),
    "bounds": {
        "layers": "exactly n",
        "entries_per_layer": 2,
        "layer_order": "1 through n, increasing",
        "rule_min": 1,
        "rule_max": "branching d",
        "candidate_count": "d^n",
    },
}


DIFFICULTY = {
    "demo": {
        "n": 4,
        "branching": 2,
        "q": 31,
        "payload_modulus": 7,
        "landmarks": 4,
    },
    "easy": {
        "n": 10,
        "branching": 3,
        "q": 8191,
        "payload_modulus": 1009,
        "landmarks": 12,
    },
    "medium": {
        "n": 14,
        "branching": 4,
        "q": 8191,
        "payload_modulus": 1009,
        "landmarks": 12,
    },
    "hard": {
        "n": 18,
        "branching": 4,
        "q": 8191,
        "payload_modulus": 1009,
        "landmarks": 12,
    },
}

SHIPPING_DIFFICULTY = "hard"

# The G9 scratch copies set this flag so harden.py tests exactly the shipping
# rung without changing the source module by hand.
if os.environ.get("GV_G9_SINGLE") == "1":
    DIFFICULTY = {SHIPPING_DIFFICULTY: dict(DIFFICULTY[SHIPPING_DIFFICULTY])}


STRUCTURAL_HINT = (
    "Modulo q, each first translation component is the unique directed "
    "difference between two powers of two."
)
PLACEBO_HINT = (
    "Across all layers, careful bookkeeping of the displayed rule numbers is "
    "important for an exact answer."
)


# Filled only from transcripts written by scripts/harden.py.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


NOTES = r"""
Section 2.1 fixes clauses, clause-sets, minimal unsatisfiability, deficiency and
MUS exactly.  Section 2.3 fixes the implication digraph and regular/nearly
regular paths.  Theorem 19 is the construction used here: a nearly regular path
starting at the literal x maps to an MUS containing {x}.  The verifier executes
the even more elementary chain check: {x} together with
(x -> a1 -> ... -> not x) is unsatisfiable, and deleting any one link or the
unit makes that chain satisfiable.

Step-0 triage rules out Track A for this family.  Corollary 20 finds an MUS
containing a specified unit in linear time by reachability, and Corollary 22
finds any one-unit or two-unit MUS in quadratic time.  Theorems 14 and 15 prove
NP-completeness only for the no-unit Families III and IV; that worst-case result
does not license a Track-A claim for the distribution generated here.

Generation samples the entire held state chain before it constructs any rule.
At each layer, the held rule and every decoy rule have a uniformly distributed
landmark source, a uniformly distributed different landmark target, and a
uniform payload translation.  Their columns are shuffled.  The held deltas
compose by telescoping, so no SAT, path, or subset search is run by the
generator.  Minimum-residue, target-greedy, random-restart, and constant-column
attacks are measured.  The domain reference is exact implication reachability;
the implementation uses bidirectional layer search on the succinct rule table
and is expected to succeed on Track B.
""".strip()


def _validate_params(n, branching, q, payload_modulus, landmarks):
    values = (n, branching, q, payload_modulus, landmarks)
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in values):
        raise TypeError("all parameters must be integers")
    if n < 2:
        raise ValueError("n must be at least 2")
    if not 2 <= branching <= landmarks:
        raise ValueError("branching must lie between 2 and landmarks")
    if landmarks < 3:
        raise ValueError("landmarks must be at least 3")
    if payload_modulus < 2:
        raise ValueError("payload_modulus must be at least 2")
    largest = 1 << (landmarks - 1)
    if q <= 2 * largest:
        raise ValueError("q must exceed twice the largest power-of-two landmark")


def _add(state, delta, q, r):
    return ((state[0] + delta[0]) % q, (state[1] + delta[1]) % r)


def _sub(state, delta, q, r):
    return ((state[0] - delta[0]) % q, (state[1] - delta[1]) % r)


def _formula_size(n, branching, q, payload_modulus):
    # One unit; d clauses at each boundary; d*q*r at every internal transition.
    return 1 + 2 * branching + (n - 2) * branching * q * payload_modulus


def make_instance(
    n,
    seed=0,
    branching=5,
    q=8191,
    payload_modulus=1009,
    landmarks=12,
):
    """Inverse-generate a layered one-unit 2-CNF and a held regular path."""

    _validate_params(n, branching, q, payload_modulus, landmarks)
    rng = random.Random(seed)
    powers = [1 << i for i in range(landmarks)]

    # The path is sampled first.  Its colour chain is stationary and its payload
    # coordinates are independent uniforms, making held-rule deltas marginally
    # identical to decoy-rule deltas.
    colours = [rng.choice(powers)]
    payloads = [rng.randrange(payload_modulus)]
    for _ in range(n):
        nxt = rng.choice(powers)
        while nxt == colours[-1]:
            nxt = rng.choice(powers)
        colours.append(nxt)
        payloads.append(rng.randrange(payload_modulus))

    rules = []
    answer = []
    for layer in range(n):
        held_source = colours[layer]
        sources = [held_source]
        available = [x for x in powers if x != held_source]
        rng.shuffle(available)
        sources.extend(available[: branching - 1])

        tagged = []
        for source in sources:
            if source == held_source:
                target = colours[layer + 1]
                delta_r = (payloads[layer + 1] - payloads[layer]) % payload_modulus
                held = True
            else:
                target = rng.choice(powers)
                while target == source:
                    target = rng.choice(powers)
                delta_r = rng.randrange(payload_modulus)
                held = False
            delta_q = (target - source) % q
            tagged.append(([delta_q, delta_r], held))

        rng.shuffle(tagged)
        row = [item[0] for item in tagged]
        held_index = next(i for i, item in enumerate(tagged) if item[1])
        rules.append(row)
        answer.append([layer + 1, held_index + 1])

    inst = {
        "n": n,
        "branching": branching,
        "q": q,
        "payload_modulus": payload_modulus,
        "landmarks": landmarks,
        "start": [colours[0], payloads[0]],
        "target": [colours[-1], payloads[-1]],
        "rules": rules,
        "formula_clauses": _formula_size(n, branching, q, payload_modulus),
        "answer": answer,
    }

    # This assertion checks only the identity just assembled; it does not search
    # for a certificate in the finished instance.
    ok, reason = verify(inst, answer)
    if not ok:
        raise AssertionError("constructed telescoping path failed: " + reason)
    return inst


def _state_text(state):
    return f"({state[0]},{state[1]})"


def render(inst):
    lines = [
        "Find a minimally-unsatisfiable implication chain in the following exact 2-CNF.",
        "",
        "Definitions. A Boolean literal is a variable X or its negation not X. An",
        "implication A -> B abbreviates the 2-CNF clause (not A OR B). A clause-set",
        "is minimally unsatisfiable when it is unsatisfiable but deleting any one",
        "clause makes it satisfiable.",
        "",
        f"There are n={inst['n']} transitions and d={inst['branching']} numbered rules",
        f"per transition. Coordinates are pairs in Z/{inst['q']}Z x",
        f"Z/{inst['payload_modulus']}Z; addition and subtraction are componentwise",
        "with residues represented by the integers in the indicated ranges.",
        "There is one special variable X. For every internal layer i=1,...,n-1 and",
        "every coordinate z there is a distinct variable V(i,z). Variables in",
        "different layers are distinct even when their coordinates agree.",
        "",
        "The 2-CNF F is specified without expanding its repeated clauses:",
        "  * F contains the unit clause (X).",
        "  * At transition 1, rule j with delta D gives X -> V(1,start+D).",
        "  * At transition i=2,...,n-1, rule j with delta D gives, for EVERY",
        "    coordinate z, V(i-1,z) -> V(i,z+D).",
        "  * At transition n, rule j with delta D gives",
        "    V(n-1,target-D) -> not X.",
        "Every displayed implication contributes its single corresponding 2-CNF",
        "clause. F has no other clauses. Thus F is an exact finite clause-set, not",
        "a probabilistic or approximate object.",
        "",
        f"start  = {_state_text(inst['start'])}",
        f"target = {_state_text(inst['target'])}",
        f"number of clauses in expanded F = {inst['formula_clauses']}",
        "Rule table; each line is `layer: j=(delta_q,delta_r), ...`:",
    ]
    for i, row in enumerate(inst["rules"], 1):
        entries = ", ".join(
            f"{j}=({delta[0]},{delta[1]})" for j, delta in enumerate(row, 1)
        )
        lines.append(f"{i}: {entries}")
    lines.extend(
        [
            "",
            "Choose exactly one rule at every layer. Starting at `start`, add the",
            "chosen delta at each layer. Your answer is valid exactly when the final",
            "coordinate equals `target`. The selected implications then form",
            "X -> V(1,.) -> ... -> V(n-1,.) -> not X. Together with (X), these",
            "n+1 clauses are a minimally unsatisfiable subset: the unit forces the",
            "chain to not X, while deleting the unit or any link breaks the only",
            "displayed chain. Layer numbers and rule numbers are 1-indexed; order",
            "matters, repetitions of a rule number in different layers are allowed,",
            "and every layer must occur once in increasing order.",
            "",
            "Give your final answer inside <answer></answer> tags as a JSON list",
            "[[1,j1],[2,j2],...,[n,jn]].",
            "Example: <answer>[[1,2],[2,1],[3,2],[4,2]]</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value


def verify(inst, answer):
    """Inspect a candidate rule path; never consult ``inst['answer']``."""

    if not isinstance(answer, list):
        return False, "answer_type: expected a JSON list"
    if not answer:
        return False, "answer_empty: no layer choices were supplied"
    n = inst["n"]
    d = inst["branching"]
    if len(answer) != n:
        return False, f"answer_length: expected {n} entries, received {len(answer)}"

    parsed = []
    for pos, entry in enumerate(answer, 1):
        if not (
            isinstance(entry, list)
            and len(entry) == 2
            and all(isinstance(x, int) and not isinstance(x, bool) for x in entry)
        ):
            return False, f"entry_shape: entry {pos} is not [integer layer, integer rule]"
        parsed.append((entry[0], entry[1]))

    layers = [layer for layer, _rule in parsed]
    if len(set(layers)) != len(layers):
        return False, "duplicate_layer: a layer number occurs more than once"
    if layers != list(range(1, n + 1)):
        return False, "layer_order: layers must be exactly 1 through n in increasing order"
    for layer, rule in parsed:
        if not 1 <= rule <= d:
            return False, f"rule_range: layer {layer} has rule {rule}, outside 1..{d}"

    q = inst["q"]
    r = inst["payload_modulus"]
    state = tuple(inst["start"])
    for layer, rule in parsed:
        state = _add(state, inst["rules"][layer - 1][rule - 1], q, r)
    target = tuple(inst["target"])
    if state != target:
        return False, (
            "endpoint_mismatch: selected implications end at "
            f"{_state_text(state)}, not target {_state_text(target)}"
        )

    # The n internal literals belong to distinct layers, and the endpoints are
    # X, not-X.  Hence this executable shape check proves that the selected
    # clauses are the regular chain described in the statement.  The chain plus
    # (X) is MU by direct unit propagation, with each clause indispensable.
    return True, "ok"


def random_candidate(inst, rng):
    return [
        [layer, rng.randrange(1, inst["branching"] + 1)]
        for layer in range(1, inst["n"] + 1)
    ]


def search_space(inst):
    return inst["branching"] ** inst["n"]


def _choices_answer(choices):
    return [[i + 1, choice + 1] for i, choice in enumerate(choices)]


def _half_counts(inst, start_layer, end_layer, start_state, backwards=False):
    """Enumerate a half of the path language, retaining endpoint multiplicity."""

    q = inst["q"]
    r = inst["payload_modulus"]
    states = Counter({tuple(start_state): 1})
    operations = 0
    indices = range(start_layer, end_layer)
    if backwards:
        indices = range(end_layer - 1, start_layer - 1, -1)
    for layer in indices:
        nxt = Counter()
        for state, multiplicity in states.items():
            for delta in inst["rules"][layer]:
                reached = _sub(state, delta, q, r) if backwards else _add(state, delta, q, r)
                nxt[reached] += multiplicity
                operations += 1
        states = nxt
    return states, operations


def _exact_solution_count(inst):
    split = inst["n"] // 2
    forward, op_f = _half_counts(inst, 0, split, inst["start"], False)
    backward, op_b = _half_counts(
        inst, split, inst["n"], inst["target"], True
    )
    count = sum(multiplicity * backward.get(state, 0) for state, multiplicity in forward.items())
    return count, op_f + op_b


def enumerate_all(inst):
    # Meet-in-the-middle is exact enumeration of the two half-languages.  Cap
    # the number of half-words, not the much larger full Cartesian product.
    half_words = inst["branching"] ** math.ceil(inst["n"] / 2)
    if half_words > 1_000_000:
        return None
    return _exact_solution_count(inst)[0]


def _reference_mitm(inst):
    """Exact bidirectional layer search, independent of the planted answer."""

    n = inst["n"]
    d = inst["branching"]
    q = inst["q"]
    r = inst["payload_modulus"]
    split = n // 2

    forward = {tuple(inst["start"]): 0}
    operations = 0
    for layer in range(split):
        nxt = {}
        for state, code in forward.items():
            for choice, delta in enumerate(inst["rules"][layer]):
                reached = _add(state, delta, q, r)
                operations += 1
                if reached not in nxt:
                    nxt[reached] = code * d + choice
        forward = nxt

    backward = {tuple(inst["target"]): 0}
    suffix_len = n - split
    for offset, layer in enumerate(range(n - 1, split - 1, -1)):
        nxt = {}
        for state, code in backward.items():
            for choice, delta in enumerate(inst["rules"][layer]):
                reached = _sub(state, delta, q, r)
                operations += 1
                if reached not in nxt:
                    # Least-significant base-d digit is the choice from the
                    # latest layer; decoding below restores forward order.
                    nxt[reached] = code + choice * (d ** offset)
        backward = nxt

    meeting = next((state for state in forward if state in backward), None)
    if meeting is None:
        return None, operations

    prefix_code = forward[meeting]
    prefix = [0] * split
    for i in range(split - 1, -1, -1):
        prefix[i] = prefix_code % d
        prefix_code //= d
    suffix_code = backward[meeting]
    suffix = []
    for _ in range(suffix_len):
        suffix.append(suffix_code % d)
        suffix_code //= d
    suffix.reverse()
    return _choices_answer(prefix + suffix), operations


def _decode_power_difference(delta, q, landmarks):
    """Decode t-s where s,t are distinct powers of two, or return None."""

    signed = delta if delta <= q // 2 else delta - q
    if signed == 0:
        return None
    magnitude = abs(signed)
    low = magnitude & -magnitude
    odd = magnitude // low
    high = low * (odd + 1)
    if high & (high - 1):
        return None
    limit = 1 << (landmarks - 1)
    if not (low <= limit and high <= limit):
        return None
    return (low, high) if signed > 0 else (high, low)


def _compact_invariant_route(inst):
    """Follow decoded landmark sources; this is the intended insight route."""

    current = inst["start"][0]
    choices = []
    operations = 0
    for layer, row in enumerate(inst["rules"]):
        found = []
        for choice, delta in enumerate(row):
            decoded = _decode_power_difference(delta[0], inst["q"], inst["landmarks"])
            # Count signed-residue normalisation, low-bit extraction/power test,
            # and source comparison as three exact primitive operations.
            operations += 3
            if decoded is not None and decoded[0] == current:
                found.append((choice, decoded[1]))
        if len(found) != 1:
            return None, operations
        choice, current = found[0]
        choices.append(choice)
        # One state update and one emitted rule index.
        operations += 2
    answer = _choices_answer(choices)
    if not verify(inst, answer)[0]:
        return None, operations
    return answer, operations


def _attack_minimum_residue(inst):
    choices = []
    for row in inst["rules"]:
        choices.append(
            min(
                range(inst["branching"]),
                key=lambda j: min(row[j][0], inst["q"] - row[j][0]),
            )
        )
    return _choices_answer(choices), inst["n"] * inst["branching"]


def _circular_distance(a, b, modulus):
    gap = abs(a - b) % modulus
    return min(gap, modulus - gap)


def _attack_target_greedy(inst):
    q = inst["q"]
    r = inst["payload_modulus"]
    target = tuple(inst["target"])
    state = tuple(inst["start"])
    choices = []
    operations = 0
    for row in inst["rules"]:
        options = []
        for choice, delta in enumerate(row):
            reached = _add(state, delta, q, r)
            score = _circular_distance(reached[0], target[0], q) + _circular_distance(
                reached[1], target[1], r
            )
            options.append((score, choice, reached))
            operations += 1
        _score, choice, state = min(options)
        choices.append(choice)
    return _choices_answer(choices), operations


def _attack_random_restarts(inst, seed, restarts=256):
    rng = random.Random(seed)
    operations = 0
    last = None
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        operations += inst["n"]
        if verify(inst, last)[0]:
            return last, operations
    return last, operations


def _attack_constant_column(inst):
    operations = 0
    last = None
    for choice in range(1, inst["branching"] + 1):
        last = [[layer, choice] for layer in range(1, inst["n"] + 1)]
        operations += inst["n"]
        if verify(inst, last)[0]:
            return last, operations
    return last, operations


def _affine_layer_key(row, q, r):
    """Canonical row under rule order and independent affine coordinates."""

    q_anchors = [
        (a[0], pow((b[0] - a[0]) % q, -1, q))
        for a in row
        for b in row
        if a[0] != b[0]
    ]
    r_anchors = [
        (a[1], pow((b[1] - a[1]) % r, -1, r))
        for a in row
        for b in row
        if a[1] != b[1]
    ]
    if not q_anchors:
        q_anchors = [(row[0][0], 1)]
    if not r_anchors:
        r_anchors = [(row[0][1], 1)]
    best = None
    for aq, uq in q_anchors:
        for ar, ur in r_anchors:
            normal = tuple(
                sorted(
                    (((x - aq) * uq) % q, ((y - ar) * ur) % r)
                    for x, y in row
                )
            )
            if best is None or normal < best:
                best = normal
    return best


def canonical_key(inst):
    """Strong cheap invariant under rule order, gauges, scalings and reversal."""

    layers = tuple(
        _affine_layer_key(row, inst["q"], inst["payload_modulus"])
        for row in inst["rules"]
    )
    oriented = min(layers, tuple(reversed(layers)))
    data = (
        inst["n"],
        inst["branching"],
        inst["q"],
        inst["payload_modulus"],
        oriented,
    )
    return hashlib.sha256(repr(data).encode("ascii")).hexdigest()


def _transform_instance(inst, seed, reverse=False):
    """Apply genuine layer gauges/scalings, reversal, and rule reorderings."""

    rng = random.Random(seed)
    n = inst["n"]
    q = inst["q"]
    r = inst["payload_modulus"]
    uq = rng.randrange(1, q)
    while math.gcd(uq, q) != 1:
        uq = rng.randrange(1, q)
    ur = rng.randrange(1, r)
    while math.gcd(ur, r) != 1:
        ur = rng.randrange(1, r)
    shifts = [(rng.randrange(q), rng.randrange(r)) for _ in range(n + 1)]

    if reverse:
        base_rows = [
            [[(-x) % q, (-y) % r] for x, y in row]
            for row in reversed(inst["rules"])
        ]
        base_selected = [entry[1] - 1 for entry in reversed(inst["answer"])]
        base_start = tuple(inst["target"])
        base_target = tuple(inst["start"])
    else:
        base_rows = [[delta[:] for delta in row] for row in inst["rules"]]
        base_selected = [entry[1] - 1 for entry in inst["answer"]]
        base_start = tuple(inst["start"])
        base_target = tuple(inst["target"])

    rows = []
    answer = []
    for i, (row, selected) in enumerate(zip(base_rows, base_selected)):
        tagged = []
        for j, (x, y) in enumerate(row):
            transformed = [
                (uq * x + shifts[i + 1][0] - shifts[i][0]) % q,
                (ur * y + shifts[i + 1][1] - shifts[i][1]) % r,
            ]
            tagged.append((transformed, j == selected))
        rng.shuffle(tagged)
        rows.append([item[0] for item in tagged])
        answer.append([i + 1, next(j for j, item in enumerate(tagged, 1) if item[1])])

    start = [
        (uq * base_start[0] + shifts[0][0]) % q,
        (ur * base_start[1] + shifts[0][1]) % r,
    ]
    target = [
        (uq * base_target[0] + shifts[n][0]) % q,
        (ur * base_target[1] + shifts[n][1]) % r,
    ]
    return {
        "n": n,
        "branching": inst["branching"],
        "q": q,
        "payload_modulus": r,
        "landmarks": inst["landmarks"],
        "start": start,
        "target": target,
        "rules": rows,
        "formula_clauses": inst["formula_clauses"],
        "answer": answer,
    }


def escalate(params):
    harder = dict(params)
    branching = int(harder.get("branching", 2))
    landmarks = int(harder.get("landmarks", 12))
    n = int(harder.get("n", 16))
    if branching >= 4 and n >= 18:
        # A larger payload group grows the expanded implication graph and
        # decreases random-answer density without lengthening the witness.
        if int(harder.get("payload_modulus", 1009)) < 5003:
            harder["payload_modulus"] = 5003
            return harder
        # A fifth rule at all 18 layers would push the compact route above 300.
        return "cap_bound"
    if branching < 5:
        harder["branching"] = branching + 1
        return harder
    if int(harder.get("payload_modulus", 1009)) < 5003:
        harder["payload_modulus"] = 5003
        return harder
    # The next useful branching increment would make the landmark-decoding route
    # exceed 300 operations at n=18; this is an effort-cap, not paper failure.
    if branching >= 4 and n >= 18 and landmarks >= 12:
        return "cap_bound"
    return "cap_bound"


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest():
    report = {}

    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            try:
                inst = make_instance(seed=seed, **params)
                ok, reason = verify(inst, inst["answer"])
                json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
                size_ok = inst["formula_clauses"] == _formula_size(
                    inst["n"], inst["branching"], inst["q"], inst["payload_modulus"]
                )
            except Exception as exc:
                ok = json_ok = size_ok = False
                reason = f"{type(exc).__name__}: {exc}"
            checks += 1
            if not (ok and json_ok and size_ok):
                failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "checked_properties": (
            "planted chain endpoint, JSON answer round-trip, and exact expanded "
            "clause count"
        ),
        "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=271828, **shipping)
    answer = inst["answer"]
    drop = [entry[:] for entry in answer[:-1]]
    swapped = [entry[:] for entry in answer]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicate = [entry[:] for entry in answer]
    duplicate[-1] = duplicate[0][:]
    out_of_range = [entry[:] for entry in answer]
    out_of_range[0][1] = inst["branching"] + 1
    corruptions = {
        "drop_one": drop,
        "swap_two": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    cases = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
        if not ok:
            reasons.append(reason.split(":", 1)[0])
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in cases.values())
        and len(set(reasons)) == len(cases),
        "attempts": len(cases),
        "distinct_reasons": len(set(reasons)),
        "cases": cases,
    }

    response = (
        "The telescoping choices give the requested chain.\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nEach selected implication was checked."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer,
        "parsed_equals_answer": parsed == answer,
        "surrounding_prose_and_fence": True,
    }

    trials = 200_000
    guess_rng = random.Random(0x260310944)
    hits = 0
    started = time.perf_counter()
    for _ in range(trials):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    guess_seconds = time.perf_counter() - started
    exact_count, count_operations = _exact_solution_count(inst)
    space = search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": hits / trials < 1e-6 and exact_count / space < 1e-6,
        "hits": hits,
        "total": trials,
        "observed_probability": hits / trials,
        "exact_valid_answers": exact_count,
        "candidate_space": space,
        "exact_probability": exact_count / space,
        "candidate_space_bits": math.log2(space),
        "prior": "uniform over one in-range rule choice per displayed layer",
        "wall_clock_sec": round(guess_seconds, 6),
    }

    reference_started = time.perf_counter()
    reference_answer, reference_operations = _reference_mitm(inst)
    reference_seconds = time.perf_counter() - reference_started
    reference_ok = reference_answer is not None and verify(inst, reference_answer)[0]
    baseline_started = time.perf_counter()
    baseline_answer, baseline_nodes = _attack_random_restarts(inst, 0xBAD5EED, 256)
    baseline_seconds = time.perf_counter() - baseline_started
    baseline_ok = verify(inst, baseline_answer)[0]
    report["G5_density_and_baseline_cost"] = {
        "pass": reference_ok and not baseline_ok,
        "shipping_seed": 271828,
        "shipping_exact_valid_answers": exact_count,
        "shipping_candidate_space": space,
        "shipping_solution_density": exact_count / space,
        "shipping_sample_hits": hits,
        "shipping_sample_total": trials,
        "exact_count_halfword_transitions": count_operations,
        "strongest_failing_attack": "256 uniform structure-aware random restarts",
        "baseline_nodes": baseline_nodes,
        "baseline_wall_clock_sec": round(baseline_seconds, 6),
        "reference_transitions": reference_operations,
        "reference_wall_clock_sec": round(reference_seconds, 6),
    }

    attack_names = (
        "outlier_minimum_translation_residue",
        "greedy_nearest_target_coordinate",
        "random_restart_256",
        "in_context_constant_rule_column",
    )
    attacks = {name: {"successes": 0, "attempts": 8} for name in attack_names}
    attack_times = {name: 0.0 for name in attack_names}
    attack_operations = {name: 0 for name in attack_names}
    reference_successes = 0
    reference_times = []
    reference_ops = []
    compact_successes = 0
    compact_ops = []
    for seed in range(10_000, 10_008):
        current = make_instance(seed=seed, **shipping)
        funcs = {
            "outlier_minimum_translation_residue": lambda: _attack_minimum_residue(current),
            "greedy_nearest_target_coordinate": lambda: _attack_target_greedy(current),
            "random_restart_256": lambda: _attack_random_restarts(
                current, seed ^ 0xC0FFEE, 256
            ),
            "in_context_constant_rule_column": lambda: _attack_constant_column(current),
        }
        for name, func in funcs.items():
            attack_started = time.perf_counter()
            candidate, operations = func()
            attack_times[name] += time.perf_counter() - attack_started
            attack_operations[name] += operations
            if candidate is not None and verify(current, candidate)[0]:
                attacks[name]["successes"] += 1

        ref_started = time.perf_counter()
        candidate, operations = _reference_mitm(current)
        reference_times.append(time.perf_counter() - ref_started)
        reference_ops.append(operations)
        if candidate is not None and verify(current, candidate)[0]:
            reference_successes += 1

        compact, operations = _compact_invariant_route(current)
        compact_ops.append(operations)
        if compact is not None and verify(current, compact)[0]:
            compact_successes += 1

    for name in attack_names:
        attacks[name]["wall_clock_sec"] = round(attack_times[name], 6)
        attacks[name]["operations"] = attack_operations[name]
    all_failed = all(item["successes"] == 0 for item in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed
        and reference_successes == 8
        and compact_successes == 8
        and max(compact_ops) <= 300,
        "attacks": attacks,
        "reference_algorithm": {
            "name": (
                "exact bidirectional layer search (the succinct implementation of "
                "Corollary 20 implication reachability)"
            ),
            "complexity": (
                "O(d^ceil(n/2)) time and memory on the succinct table; Corollary "
                "20 is O(ell(F)) on expanded F"
            ),
            "solves": f"{reference_successes}/8, as expected",
            "wall_clock_sec": round(sum(reference_times), 6),
            "operations": sum(reference_ops),
            "per_instance_operations": reference_ops,
            "expanded_formula_clauses_per_instance": inst["formula_clauses"],
        },
        "intended_compact_route": {
            "name": "decode powers-of-two differences and follow matching sources",
            "solves": f"{compact_successes}/8",
            "operations_max": max(compact_ops),
            "per_instance_operations": compact_ops,
        },
    }

    doubled_params = dict(shipping)
    doubled_params["n"] = 2 * shipping["n"]
    base = make_instance(seed=314159, **shipping)
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(base),
        "shipping_n": shipping["n"],
        "doubled_n": doubled_params["n"],
        "shipping_search_space": search_space(base),
        "doubled_search_space": search_space(doubled),
        "answer_elements_shipping": _answer_atoms(base["answer"]),
        "answer_elements_doubled": _answer_atoms(doubled["answer"]),
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = 0
    real_transformations = 0
    key_failures = []
    for seed in range(20):
        base = make_instance(seed=50_000 + seed, **shipping)
        base_key = canonical_key(base)
        for variant in range(4):
            transformed = _transform_instance(
                base, seed=60_000 + 4 * seed + variant, reverse=bool(variant & 1)
            )
            invariance_checks += 1
            if canonical_key(transformed) != base_key:
                key_failures.append({"seed": seed, "variant": variant})
            if verify(transformed, transformed["answer"])[0]:
                real_transformations += 1
    unrelated = [
        canonical_key(make_instance(seed=80_000 + seed, **shipping)) for seed in range(20)
    ]
    report["G8_canonical_key"] = {
        "pass": not key_failures
        and real_transformations == invariance_checks
        and len(set(unrelated)) == 20,
        "invariance_checks": invariance_checks,
        "real_transformations_verified": real_transformations,
        "unrelated_attempts": 20,
        "unrelated_distinct_keys": len(set(unrelated)),
        "transformations": (
            "rule permutations, independent layer-coordinate translations, global "
            "unit scalings in both cyclic coordinates, and path reversal through "
            "contraposition"
        ),
        "failures": key_failures,
    }

    answer_blob = json.dumps(answer, separators=(",", ":"))
    compact_answer, intended_operations = _compact_invariant_route(inst)
    arms = {
        name: {
            "solved": G9_ORACLE_RESULTS[name]["solved"],
            "attempts": G9_ORACLE_RESULTS[name]["attempts"],
        }
        for name in ("bare", "hinted", "placebo")
    }
    hinted_minus_placebo = None
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_minus_placebo = (
            arms["hinted"]["solved"] / arms["hinted"]["attempts"]
            - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        )
    within_caps = (
        len(answer_blob) <= 2000
        and _answer_atoms(answer) <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps and compact_answer is not None,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": len(answer_blob),
        "answer_tokens": math.ceil(len(answer_blob) / 4),
        "answer_elements": _answer_atoms(answer),
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "within_caps": within_caps,
    }

    report["paper"] = "arXiv:2603.10944"
    report["family"] = "succinct layered one-unit Family-II implication chain"
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
