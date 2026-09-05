"""Verified problem generator for arXiv:2004.08801.

The paper constructs partial finite automata whose shortest carefully
synchronizing words are exponentially long base-d counters.  This module asks
for such a word in a bounded straight-line-program (SLP) language.  The SLP is
small, and verification composes partial state maps exactly without expanding
the exponentially long word.
"""

from __future__ import annotations

import collections
import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - this family remains stdlib-only
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "other",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "partial finite automaton",
        "carefully synchronizing word as a straight-line program",
        "power-automaton subset trajectory",
    ],
    "verification_operations": [
        "exact partial-transition composition",
        "definedness check on every state",
        "singleton-image comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The image of the unique total letter is a block transversal on which "
        "each counter letter exposes a fixed-point count and a two-step path "
        "signature; without that joint invariant, one must search the power "
        "automaton or guess an ordered selection of digit letters."
    ),
    "hardness_basis": (
        "Track B: Fact 1 gives breadth-first search in the power automaton, with "
        "O(|Sigma| |Q| 2^|Q|) worst-case time; at the shipping preset it solved "
        "8/8 instances using 2,189 visited subsets, 115,428 transition lookups "
        "and 0.0212 seconds on average, while the counter-transversal invariant "
        "takes 154 exact table operations."
    ),
    "max_answer_tokens": 21,
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


# n is the number of counter blocks.  The automaton has 2*radix*n states.
DIFFICULTY = {
    "demo": {"n": 3, "radix": 3},
    "easy": {"n": 7, "radix": 3},
    "medium": {"n": 8, "radix": 3},
    "hard": {"n": 9, "radix": 4},
}
SHIPPING_DIFFICULTY = "easy"


STRUCTURAL_HINT = (
    "The total letter's image is a transversal on which digit letters have "
    "both a fixed-point count and a two-step path signature."
)
PLACEBO_HINT = (
    "The transition vectors use the displayed state order and a dash always "
    "means that the transition is undefined."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object with the unique total start letter, an ordered list of "
        "exactly n distinct letters selected from the 2n displayed digit-class "
        "letters, and the unique finish letter.  It denotes start W_n finish, "
        "where W_0 is empty and W_i=(W_(i-1) digit_i)^(radix-1) W_(i-1)."
    ),
    "bounds": {
        "start_letters": 1,
        "finish_letters": 1,
        "digit_candidates": "2*n",
        "selected_digits": "n",
        "ordered": True,
        "without_replacement": True,
        "maximum_named_answer_atoms": 11,
        "maximum_supported_answer_atoms": 256,
    },
}


NOTES = (
    "Section 1 defines a carefully synchronizing word: every transition must be "
    "defined from every initial state and all final states must coincide. Fact 1 "
    "identifies the standard algorithm as shortest-path search from Q to a "
    "singleton in the power automaton. Section 2 fixes the construction used "
    "here. Lemma 1 proves that the recursively defined w_i traverses the d-ary "
    "counter states; Lemma 2 composes those words into a careful reset word; "
    "Lemma 3 proves exponential length and uniqueness of the forward move. "
    "Section 3, Theorem 2 transforms any synchronizing DFA B into A_d(B), and "
    "Corollary 2 forces an Omega(d^n) reset length. Here B is a one-letter "
    "constant-reset DFA, so the theorem's proof gives exactly a w_n c. This is "
    "the paper's native automaton transformation, not a reduction to another problem. "
    "Fact 1 rules out Track A: power-automaton BFS is an exact mechanical solver. "
    "Track B is appropriate because that BFS follows d^n counter subsets, whereas "
    "the recursive SLP has n productions. Generation is theorem-backed and then "
    "transformed: state and alphabet names are permuted, and padding states are "
    "sent into the counter by the first letter, carrying the paper's witness. "
    "For each true digit letter a decoy is added with exactly the same unlabelled "
    "one-letter functional graph, defined-transition count, fixed-point count, "
    "rank and path-component multiset. The true letter continues for a second "
    "counter tick; its decoy moves the first tick identically but is then undefined. "
    "Thus public order, single-letter outliers, random restart and a one-tick "
    "transversal greedy rule all fail, while the intended two-step transversal "
    "invariant remains compact."
)


# Filled after isolated harden.py runs.  Since 2026-09-05 these arms are
# diagnostics; only the answer-size and intended-effort caps gate G9.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 1_000_000


def _validate_params(n, radix):
    if isinstance(n, bool) or not isinstance(n, int) or n < 2:
        raise ValueError("n must be an integer at least 2")
    if n > 254:
        raise ValueError("n exceeds the supported certificate bound")
    if isinstance(radix, bool) or not isinstance(radix, int) or radix < 3:
        raise ValueError("radix must be an integer at least 3")
    if radix > 32:
        raise ValueError("radix may not exceed 32")


def _core(block, digit, radix):
    return block * radix + digit


def _add_edge(mapping, source, target):
    if mapping[source] != -1:
        raise AssertionError("duplicate transition source in construction")
    mapping[source] = target


def _padding_for_real(mapping, pads, block, n, radix, rng):
    """Complete a real digit map to the common one-letter graph."""
    order = list(pads)
    rng.shuffle(order)
    cursor = 0
    for state in order[cursor:cursor + radix * block]:
        _add_edge(mapping, state, state)
    cursor += radix * block
    for _ in range(n - block):
        source, target = order[cursor], order[cursor + 1]
        cursor += 2
        _add_edge(mapping, source, target)


def _padding_for_decoy(mapping, pads, block, n, radix, rng):
    """Complete a one-tick decoy to the same one-letter graph as a real digit."""
    order = list(pads)
    rng.shuffle(order)
    cursor = 0
    for state in order[cursor:cursor + radix * block]:
        _add_edge(mapping, state, state)
    cursor += radix * block

    path = order[cursor:cursor + radix]
    cursor += radix
    for source, target in zip(path, path[1:]):
        _add_edge(mapping, source, target)

    for _ in range(n - block - 1):
        source, target = order[cursor], order[cursor + 1]
        cursor += 2
        _add_edge(mapping, source, target)


def _digit_mapping(n, radix, block, real, pads, rng):
    total_states = 2 * radix * n
    mapping = [-1] * total_states

    # More-significant blocks are fixed.
    for higher in range(block + 1, n):
        for digit in range(radix):
            state = _core(higher, digit, radix)
            _add_edge(mapping, state, state)

    # The selected block is either the true radix path or a one-tick prefix.
    if real:
        for digit in range(radix - 1):
            _add_edge(
                mapping,
                _core(block, digit, radix),
                _core(block, digit + 1, radix),
            )
    else:
        _add_edge(
            mapping,
            _core(block, 0, radix),
            _core(block, 1, radix),
        )

    # Less-significant blocks carry from their top digit back to zero.
    for lower in range(block):
        _add_edge(
            mapping,
            _core(lower, radix - 1, radix),
            _core(lower, 0, radix),
        )

    if real:
        _padding_for_real(mapping, pads, block, n, radix, rng)
    else:
        _padding_for_decoy(mapping, pads, block, n, radix, rng)
    return mapping


def _permute_state_map(mapping, old_to_new):
    result = [-1] * len(mapping)
    for old_source, old_target in enumerate(mapping):
        if old_target >= 0:
            result[old_to_new[old_source]] = old_to_new[old_target]
    return result


def _letter_name(index, count):
    width = max(2, len(str(count - 1)))
    return "x" + str(index).zfill(width)


def make_instance(n, seed=0, **params):
    """Construct a relabelled Section-2 counter and its compact reset SLP."""
    radix = params.pop("radix", 3)
    if params:
        raise TypeError("unexpected parameters: " + ", ".join(sorted(params)))
    _validate_params(n, radix)
    rng = random.Random(seed)

    core_states = radix * n
    total_states = 2 * radix * n
    pads = list(range(core_states, total_states))

    # The paper's first letter collapses each block to its zero state.  Padding
    # states are distributed evenly among the same n image states.
    start_map = [-1] * total_states
    for block in range(n):
        for digit in range(radix):
            start_map[_core(block, digit, radix)] = _core(block, 0, radix)
    shuffled_pads = list(pads)
    rng.shuffle(shuffled_pads)
    for position, state in enumerate(shuffled_pads):
        block = position // radix
        start_map[state] = _core(block, 0, radix)

    role_maps = [("start", None, start_map)]
    real_roles = []
    for block in range(n):
        real_name = ("real", block)
        decoy_name = ("decoy", block)
        real_roles.append(real_name)
        role_maps.append(
            (real_name[0], block,
             _digit_mapping(n, radix, block, True, pads, rng))
        )
        role_maps.append(
            (decoy_name[0], block,
             _digit_mapping(n, radix, block, False, pads, rng))
        )

    finish_map = [-1] * total_states
    target_block = rng.randrange(n)
    for block in range(n):
        finish_map[_core(block, radix - 1, radix)] = _core(target_block, 0, radix)
    role_maps.append(("finish", None, finish_map))

    # A simultaneous state relabelling and an independent alphabet shuffle carry
    # the known witness while removing all construction-order labels.
    state_order = list(range(total_states))
    rng.shuffle(state_order)
    old_to_new = [0] * total_states
    for new, old in enumerate(state_order):
        old_to_new[old] = new
    role_maps = [
        (kind, block, _permute_state_map(mapping, old_to_new))
        for kind, block, mapping in role_maps
    ]
    rng.shuffle(role_maps)

    alphabet = [_letter_name(i, len(role_maps)) for i in range(len(role_maps))]
    transitions = [[-1] * len(role_maps) for _ in range(total_states)]
    role_to_letter = {}
    for letter_index, (kind, block, mapping) in enumerate(role_maps):
        for state, target in enumerate(mapping):
            transitions[state][letter_index] = target
        role_to_letter[(kind, block)] = alphabet[letter_index]

    answer = {
        "start": role_to_letter[("start", None)],
        "digits": [role_to_letter[("real", block)] for block in range(n)],
        "finish": role_to_letter[("finish", None)],
    }
    instance = {
        "n": n,
        "radix": radix,
        "states": ["s" + str(i).zfill(max(2, len(str(total_states - 1))))
                   for i in range(total_states)],
        "alphabet": alphabet,
        "transitions": transitions,
        "digit_defined_entries": (radix + 1) * n - 1,
        "expanded_word_length": radix ** n + 1,
        "answer": answer,
    }
    # Catch construction mistakes here, while the certificate is still local.
    ok, reason = verify(instance, answer)
    if not ok:
        raise AssertionError("constructed certificate failed: " + reason)
    return instance


def _letter_maps(inst):
    state_count = len(inst["states"])
    letter_count = len(inst["alphabet"])
    return [
        [inst["transitions"][state][letter] for state in range(state_count)]
        for letter in range(letter_count)
    ]


def _candidate_classes(inst):
    maps = _letter_maps(inst)
    starts = []
    digits = []
    for index, mapping in enumerate(maps):
        defined = [target for target in mapping if target >= 0]
        if len(defined) == len(mapping):
            starts.append(index)
        if (
            len(defined) == inst["digit_defined_entries"]
            and len(set(defined)) == len(defined)
        ):
            digits.append(index)
    occupied = set(starts) | set(digits)
    finishes = [index for index in range(len(maps)) if index not in occupied]
    return starts, digits, finishes


def render(inst):
    """Render a self-contained careful-synchronization problem."""
    starts, digits, finishes = _candidate_classes(inst)
    alphabet = inst["alphabet"]
    states = inst["states"]
    lines = [
        "Carefully synchronizing a partial finite automaton",
        "",
        "A partial finite automaton has a finite state set, an alphabet, and at "
        "most one transition for each (state, letter) pair. A word is carefully "
        "synchronizing when every letter can be applied at every currently "
        "possible state and, after the whole word, all initial states have the "
        "same final state.",
        "",
        f"This instance has {len(states)} states, counter depth n={inst['n']}, "
        f"and radix d={inst['radix']}.",
        "State order: " + " ".join(states),
        "Alphabet: " + " ".join(alphabet),
        "",
        "For each letter below, the bracket contains one entry per source state "
        "in the displayed state order. A state name is the target; '-' means "
        "undefined. No transitions other than these exist.",
    ]
    for letter_index, letter in enumerate(alphabet):
        vector = []
        for source in range(len(states)):
            target = inst["transitions"][source][letter_index]
            vector.append("-" if target < 0 else states[target])
        lines.append(letter + ": [" + " ".join(vector) + "]")

    lines.extend([
        "",
        "Your answer is a compact straight-line program (SLP), not the expanded "
        "word. To make the bounded answer language explicit, its start field must "
        "be the sole total-map letter, its digits field must select exactly n "
        "distinct digit-class letters in an order you choose, and its finish "
        "field must be the sole remaining letter. The mechanically derived classes "
        "are supplied here:",
        "  start class: " + " ".join(alphabet[i] for i in starts),
        "  digit class: " + " ".join(alphabet[i] for i in digits),
        "  finish class: " + " ".join(alphabet[i] for i in finishes),
        "",
        "If the ordered digits are [g1,...,gn], define W0 to be the empty word "
        "and Wi=(W(i-1) gi)^(d-1) W(i-1) for i=1,...,n. Your SLP denotes "
        "start Wn finish, an expanded word of exactly "
        + str(inst["expanded_word_length"])
        + " letters. Order matters; digit letters may not repeat. The SLP is "
        "valid exactly when its expanded word is carefully synchronizing.",
        "",
        "Give your final answer inside <answer></answer> tags as one JSON object "
        "with string fields start and finish and a string-list field digits.",
        "Example: <answer>{\"start\":\"x00\",\"digits\":[\"x01\",\"x02\"],"
        "\"finish\":\"x03\"}</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Extract the last tagged JSON answer, tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    payload = matches[-1].strip()
    if payload.startswith("```") and payload.endswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload, flags=re.I)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return answer if isinstance(answer, dict) else None


def _compose(first, second):
    """Partial map of the word 'first then second'."""
    result = [-1] * len(first)
    for state, middle in enumerate(first):
        if middle >= 0:
            result[state] = second[middle]
    return result


def _word_map(inst, start_index, digit_indices, finish_index):
    maps = _letter_maps(inst)
    size = len(inst["states"])
    current = list(range(size))  # W_0
    for digit_index in digit_indices:
        tick = _compose(current, maps[digit_index])
        repeated = list(range(size))
        for _ in range(inst["radix"] - 1):
            repeated = _compose(repeated, tick)
        current = _compose(repeated, current)
        if all(target < 0 for target in current):
            break
    result = _compose(maps[start_index], current)
    return _compose(result, maps[finish_index])


def verify(inst, answer):
    """Verify any valid bounded SLP without consulting inst['answer']."""
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if not all(field in answer for field in ("start", "digits", "finish")):
        return False, "answer object is missing a required field"
    if not isinstance(answer["start"], str) or not isinstance(answer["finish"], str):
        return False, "start and finish must be letter-name strings"
    if not isinstance(answer["digits"], list):
        return False, "digits must be a JSON list"
    if len(answer["digits"]) != inst["n"]:
        return False, "digits list has the wrong length"
    if any(not isinstance(letter, str) for letter in answer["digits"]):
        return False, "every digit must be a letter-name string"
    if len(set(answer["digits"])) != len(answer["digits"]):
        return False, "digit letters must be pairwise distinct"

    alphabet = inst["alphabet"]
    requested = [answer["start"], *answer["digits"], answer["finish"]]
    unknown = [letter for letter in requested if letter not in alphabet]
    if unknown:
        return False, "answer contains an unknown letter"
    index = {letter: i for i, letter in enumerate(alphabet)}
    starts, digits, finishes = _candidate_classes(inst)
    if index[answer["start"]] not in starts:
        return False, "start is not in the declared total-map class"
    if any(index[letter] not in digits for letter in answer["digits"]):
        return False, "a selected digit is not in the declared digit class"
    if index[answer["finish"]] not in finishes:
        return False, "finish is not in the declared finish class"

    word_map = _word_map(
        inst,
        index[answer["start"]],
        [index[letter] for letter in answer["digits"]],
        index[answer["finish"]],
    )
    if any(target < 0 for target in word_map):
        return False, "compressed word encounters an undefined transition"
    if len(set(word_map)) != 1:
        return False, "compressed word does not synchronize all states"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from the public, structure-aware SLP language."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    starts, digits, finishes = _candidate_classes(inst)
    if len(starts) != 1 or len(finishes) != 1:
        raise ValueError("instance does not have the declared candidate classes")
    return {
        "start": inst["alphabet"][starts[0]],
        "digits": [inst["alphabet"][i]
                   for i in rng.sample(digits, inst["n"])],
        "finish": inst["alphabet"][finishes[0]],
    }


def search_space(inst):
    """Exact size of the structure-aware ordered-without-replacement language."""
    starts, digits, finishes = _candidate_classes(inst)
    if len(starts) != 1 or len(finishes) != 1:
        return 0
    return math.factorial(len(digits)) // math.factorial(len(digits) - inst["n"])


def enumerate_all(inst):
    """Count valid SLPs exactly when the candidate language is small."""
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    starts, digits, finishes = _candidate_classes(inst)
    start = inst["alphabet"][starts[0]]
    finish = inst["alphabet"][finishes[0]]
    valid = 0
    for ordering in itertools.permutations(digits, inst["n"]):
        answer = {
            "start": start,
            "digits": [inst["alphabet"][i] for i in ordering],
            "finish": finish,
        }
        valid += int(verify(inst, answer)[0])
    return valid


def _refinement_fingerprint(inst):
    """Relabelling-invariant color refinement of the transition ternary relation."""
    table = inst["transitions"]
    n_states = len(table)
    n_letters = len(inst["alphabet"])
    state_colors = [0] * n_states
    letter_colors = [1] * n_letters

    incoming = [[[] for _ in range(n_states)] for _ in range(n_letters)]
    for source, row in enumerate(table):
        for letter, target in enumerate(row):
            if target >= 0:
                incoming[letter][target].append(source)

    for _ in range(n_states + n_letters + 2):
        state_signatures = []
        for state in range(n_states):
            outgoing = sorted(
                (letter_colors[letter], state_colors[target])
                for letter, target in enumerate(table[state]) if target >= 0
            )
            inc = []
            for letter in range(n_letters):
                inc.extend(
                    (letter_colors[letter], state_colors[source])
                    for source in incoming[letter][state]
                )
            inc.sort()
            state_signatures.append(json.dumps(["S", outgoing, inc], separators=(",", ":")))

        letter_signatures = []
        for letter in range(n_letters):
            edges = sorted(
                (state_colors[source], state_colors[table[source][letter]])
                for source in range(n_states) if table[source][letter] >= 0
            )
            letter_signatures.append(json.dumps(["L", edges], separators=(",", ":")))

        universe = sorted(set(state_signatures + letter_signatures))
        palette = {signature: color for color, signature in enumerate(universe)}
        new_states = [palette[signature] for signature in state_signatures]
        new_letters = [palette[signature] for signature in letter_signatures]
        if new_states == state_colors and new_letters == letter_colors:
            break
        state_colors, letter_colors = new_states, new_letters

    triples = sorted(
        (state_colors[source], letter_colors[letter], state_colors[target])
        for source, row in enumerate(table)
        for letter, target in enumerate(row) if target >= 0
    )
    payload = {
        "state_color_counts": sorted(collections.Counter(state_colors).items()),
        "letter_color_counts": sorted(collections.Counter(letter_colors).items()),
        "triples": triples,
        "state_count": n_states,
        "letter_count": n_letters,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def canonical_key(inst):
    """A strong cheap invariant under arbitrary state and alphabet relabelling."""
    fingerprint = _refinement_fingerprint(inst)
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


def escalate(params):
    """Increase radix at fixed certificate length before lengthening the answer."""
    current = dict(params)
    current.pop("_preset", None)
    n = current.get("n")
    radix = current.get("radix", 3)
    if not isinstance(n, int) or not isinstance(radix, int):
        return None
    # Intended-route operations are 2*d*n + 2*n^2 + 2*n.  Stay under G9(c).
    if 2 * (radix + 1) * n + 2 * n * n + 2 * n <= 300:
        current["radix"] = radix + 1
        return current
    # At the cap there is no honest no-tool axis left for this representation.
    return None


def _apply_letter_to_subset(inst, subset, letter_index, counter=None):
    image = 0
    remaining = subset
    while remaining:
        bit = remaining & -remaining
        state = bit.bit_length() - 1
        remaining ^= bit
        if counter is not None:
            counter["transition_lookups"] += 1
        target = inst["transitions"][state][letter_index]
        if target < 0:
            return None
        image |= 1 << target
    return image


def _reference_power_bfs(inst):
    """Fact 1's domain-standard exact algorithm, measured without hidden solvers."""
    started = time.perf_counter()
    state_count = len(inst["states"])
    initial = (1 << state_count) - 1
    queue = collections.deque([(initial, 0)])
    seen = {initial}
    stats = {
        "nodes": 0,
        "transition_attempts": 0,
        "transition_lookups": 0,
        "max_frontier": 1,
        "word_length": None,
    }
    while queue:
        subset, distance = queue.popleft()
        stats["nodes"] += 1
        if subset and subset & (subset - 1) == 0:
            stats["word_length"] = distance
            stats["wall_clock_sec"] = time.perf_counter() - started
            stats["found"] = True
            return stats
        for letter in range(len(inst["alphabet"])):
            stats["transition_attempts"] += 1
            image = _apply_letter_to_subset(inst, subset, letter, stats)
            if image is not None and image not in seen:
                seen.add(image)
                queue.append((image, distance + 1))
        stats["max_frontier"] = max(stats["max_frontier"], len(queue))
    stats["wall_clock_sec"] = time.perf_counter() - started
    stats["found"] = False
    return stats


def _fixed_public_order_attack(inst):
    starts, digits, finishes = _candidate_classes(inst)
    chosen = sorted(digits, key=lambda i: inst["alphabet"][i])[:inst["n"]]
    return {
        "start": inst["alphabet"][starts[0]],
        "digits": [inst["alphabet"][i] for i in chosen],
        "finish": inst["alphabet"][finishes[0]],
    }


def _component_signature(mapping):
    defined = sum(target >= 0 for target in mapping)
    fixed = sum(target == state for state, target in enumerate(mapping))
    indegrees = [0] * len(mapping)
    for target in mapping:
        if target >= 0:
            indegrees[target] += 1
    return defined, fixed, tuple(sorted(indegrees))


def _single_letter_outlier_attack(inst):
    starts, digits, finishes = _candidate_classes(inst)
    maps = _letter_maps(inst)
    chosen = sorted(
        digits,
        key=lambda i: (_component_signature(maps[i]), inst["alphabet"][i]),
    )[:inst["n"]]
    return {
        "start": inst["alphabet"][starts[0]],
        "digits": [inst["alphabet"][i] for i in chosen],
        "finish": inst["alphabet"][finishes[0]],
    }


def _one_tick_greedy_attack(inst):
    """Use only immediate legality, deliberately omitting the two-step invariant."""
    starts, digits, finishes = _candidate_classes(inst)
    maps = _letter_maps(inst)
    start_subset = _apply_letter_to_subset(
        inst, (1 << len(inst["states"])) - 1, starts[0]
    )
    start_states = []
    remaining_start = start_subset
    while remaining_start:
        bit = remaining_start & -remaining_start
        start_states.append(bit.bit_length() - 1)
        remaining_start ^= bit
    selected = []
    remaining = set(digits)
    current_word_map = list(range(len(inst["states"])))
    current_subset = start_subset
    for _ in range(inst["n"]):
        legal = []
        for letter in remaining:
            if _apply_letter_to_subset(inst, current_subset, letter) is not None:
                legal.append(letter)
        if not legal:
            break
        choice = min(legal, key=lambda i: inst["alphabet"][i])
        selected.append(choice)
        remaining.remove(choice)

        tick = _compose(current_word_map, maps[choice])
        repeated = list(range(len(inst["states"])))
        for _ in range(inst["radix"] - 1):
            repeated = _compose(repeated, tick)
        current_word_map = _compose(repeated, current_word_map)
        images = {current_word_map[state] for state in start_states
                  if current_word_map[state] >= 0}
        if len(images) != inst["n"]:
            break
        current_subset = 0
        for target in images:
            current_subset |= 1 << target

    for letter in sorted(remaining, key=lambda i: inst["alphabet"][i]):
        if len(selected) == inst["n"]:
            break
        selected.append(letter)
    return {
        "start": inst["alphabet"][starts[0]],
        "digits": [inst["alphabet"][i] for i in selected],
        "finish": inst["alphabet"][finishes[0]],
    }


def _relabel_instance(inst, rng):
    """Apply arbitrary state/letter renaming and carry the certificate."""
    n_states = len(inst["states"])
    n_letters = len(inst["alphabet"])
    state_new = list(range(n_states))
    letter_new = list(range(n_letters))
    rng.shuffle(state_new)
    rng.shuffle(letter_new)

    table = [[-1] * n_letters for _ in range(n_states)]
    for old_state in range(n_states):
        for old_letter in range(n_letters):
            old_target = inst["transitions"][old_state][old_letter]
            if old_target >= 0:
                table[state_new[old_state]][letter_new[old_letter]] = state_new[old_target]

    width_s = max(2, len(str(n_states - 1)))
    width_l = max(2, len(str(n_letters - 1)))
    alphabet = ["r" + str(i).zfill(width_l) for i in range(n_letters)]
    old_label_to_new = {}
    for old_letter, old_label in enumerate(inst["alphabet"]):
        old_label_to_new[old_label] = alphabet[letter_new[old_letter]]
    answer = {
        "start": old_label_to_new[inst["answer"]["start"]],
        "digits": [old_label_to_new[x] for x in inst["answer"]["digits"]],
        "finish": old_label_to_new[inst["answer"]["finish"]],
    }
    return {
        "n": inst["n"],
        "radix": inst["radix"],
        "states": ["t" + str(i).zfill(width_s) for i in range(n_states)],
        "alphabet": alphabet,
        "transitions": table,
        "digit_defined_entries": inst["digit_defined_entries"],
        "expanded_word_length": inst["expanded_word_length"],
        "answer": answer,
    }


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def _intended_route_operations(inst):
    # Read the start image, inspect every digit candidate on its n image states,
    # and make one second-step test per candidate.
    return (
        len(inst["states"])
        + 2 * inst["n"] * inst["n"]
        + 2 * inst["n"]
    )


def selftest():
    """Run correctness, resistance, scaling, invariance, and no-tool gates."""
    report = {}
    preset_checks = 0
    json_checks = 0
    planted_ok = True
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 991):
            inst = make_instance(seed=seed, **params)
            planted_ok &= verify(inst, inst["answer"])[0]
            preset_checks += 1
            planted_ok &= json.loads(json.dumps(inst["answer"])) == inst["answer"]
            json_checks += 1
    report["G1_planted_verifies"] = {
        "pass": bool(planted_ok),
        "preset_seed_checks": preset_checks,
        "json_native_checks": json_checks,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping)
    corruptions = {}
    dropped = json.loads(json.dumps(inst["answer"]))
    dropped["digits"] = dropped["digits"][:-1]
    corruptions["drop_one"] = verify(inst, dropped)
    swapped = json.loads(json.dumps(inst["answer"]))
    swapped["digits"][0], swapped["digits"][1] = (
        swapped["digits"][1], swapped["digits"][0]
    )
    corruptions["swap_two"] = verify(inst, swapped)
    duplicated = json.loads(json.dumps(inst["answer"]))
    duplicated["digits"][1] = duplicated["digits"][0]
    corruptions["duplicate"] = verify(inst, duplicated)
    corruptions["empty"] = verify(inst, {})
    out_of_range = json.loads(json.dumps(inst["answer"]))
    out_of_range["digits"][0] = "x999999"
    corruptions["out_of_range"] = verify(inst, out_of_range)
    reasons = [result[1] for result in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not result[0] for result in corruptions.values())
                and len(set(reasons)) == len(reasons),
        "cases": {name: {"accepted": value[0], "reason": value[1]}
                  for name, value in corruptions.items()},
        "distinct_reasons": len(set(reasons)),
    }

    answer_json = json.dumps(inst["answer"], separators=(",", ":"))
    response = (
        "I followed the counter blocks.\n```json\n<answer>\n"
        + answer_json
        + "\n</answer>\n```\nThe tags contain only the requested object."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0],
        "prose_and_fence": True,
    }

    guess_rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    space = search_space(inst)
    exact_density = 1.0 / space
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6 and exact_density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_valid_fraction": guess_hits / guess_total,
        "candidate_space": space,
        "exact_valid_answers": 1,
        "exact_density_by_construction": exact_density,
        "sampling_prior": "uniform ordered n-subset of the public 2n digit class",
    }

    attack_seeds = (101, 202, 303, 404, 505, 606, 707, 808)
    attack_success = {
        "single_letter_outlier": 0,
        "fixed_public_order": 0,
        "random_restart_256": 0,
        "one_tick_transversal_greedy": 0,
    }
    reference_runs = []
    for seed in attack_seeds:
        candidate_inst = make_instance(seed=seed, **shipping)
        attack_success["single_letter_outlier"] += int(
            verify(candidate_inst, _single_letter_outlier_attack(candidate_inst))[0]
        )
        attack_success["fixed_public_order"] += int(
            verify(candidate_inst, _fixed_public_order_attack(candidate_inst))[0]
        )
        rr_rng = random.Random(seed ^ 0xA5A5A5A5)
        restart_solved = False
        for _ in range(256):
            if verify(candidate_inst, random_candidate(candidate_inst, rr_rng))[0]:
                restart_solved = True
                break
        attack_success["random_restart_256"] += int(restart_solved)
        attack_success["one_tick_transversal_greedy"] += int(
            verify(candidate_inst, _one_tick_greedy_attack(candidate_inst))[0]
        )
        reference_runs.append(_reference_power_bfs(candidate_inst))

    attacks = {
        name: {"successes": successes, "attempts": len(attack_seeds)}
        for name, successes in attack_success.items()
    }
    reference_successes = sum(run["found"] for run in reference_runs)
    mean_wall = sum(run["wall_clock_sec"] for run in reference_runs) / len(reference_runs)
    mean_nodes = sum(run["nodes"] for run in reference_runs) / len(reference_runs)
    mean_lookups = (
        sum(run["transition_lookups"] for run in reference_runs)
        / len(reference_runs)
    )
    report["G5_density_and_baseline"] = {
        "pass": exact_density < 1e-6 and reference_successes == len(reference_runs),
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_sampled_valid_fraction": guess_hits / guess_total,
        "exact_valid_answer_count_by_construction": 1,
        "candidate_space": space,
        "reference_wall_clock_seconds_mean": mean_wall,
        "reference_wall_clock_seconds_max": max(
            run["wall_clock_sec"] for run in reference_runs
        ),
        "reference_nodes_mean": mean_nodes,
        "reference_transition_lookups_mean": mean_lookups,
    }
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "breadth-first search in the power automaton (Fact 1)",
            "complexity": "O(|Sigma|*|Q|*2^|Q|) worst-case exact",
            "wall_clock_sec_mean": mean_wall,
            "wall_clock_sec_max": max(run["wall_clock_sec"] for run in reference_runs),
            "nodes_mean": mean_nodes,
            "transition_lookups_mean": mean_lookups,
            "operations": int(round(mean_lookups)),
            "solves": str(reference_successes) + "/" + str(len(reference_runs))
                       + ", as expected on Track B",
            "shortest_word_length": reference_runs[0]["word_length"],
        },
    }

    doubled = make_instance(
        n=2 * shipping["n"],
        radix=shipping.get("radix", 3),
        seed=424242,
    )
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok
                and search_space(doubled) > space
                and doubled["expanded_word_length"] > inst["expanded_word_length"],
        "shipping_n": shipping["n"],
        "doubled_n": 2 * shipping["n"],
        "shipping_candidate_space": space,
        "doubled_candidate_space": search_space(doubled),
        "shipping_expanded_length": inst["expanded_word_length"],
        "doubled_expanded_length": doubled["expanded_word_length"],
        "doubled_planted_verifies": doubled_ok,
    }

    invariant_checks = 0
    carried_checks = 0
    invariant_ok = True
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(seed=10_000 + seed, **shipping)
        unrelated_keys.append(canonical_key(base))
        base_key = canonical_key(base)
        for salt in (1, 2, 3):
            transformed = _relabel_instance(
                base, random.Random((seed + 1) * 1_000_003 + salt)
            )
            invariant_ok &= canonical_key(transformed) == base_key
            invariant_checks += 1
            carried_ok = verify(transformed, transformed["answer"])[0]
            invariant_ok &= carried_ok
            carried_checks += int(carried_ok)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_ok and distinct_count == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct_count,
        "transformations": "arbitrary state and alphabet permutations, composed",
        "invariant": "iterated color refinement of the transition ternary relation",
    }

    answer_blobs = []
    answer_atoms = []
    route_ops = []
    for seed in range(20):
        measured = make_instance(seed=50_000 + seed, **shipping)
        blob = json.dumps(measured["answer"], separators=(",", ":"))
        answer_blobs.append(len(blob))
        answer_atoms.append(_answer_atoms(measured["answer"]))
        route_ops.append(_intended_route_operations(measured))
    answer_chars = max(answer_blobs)
    answer_tokens = (answer_chars + 3) // 4
    elements = max(answer_atoms)
    operations = max(route_ops)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else 0.0
    )
    within_caps = answer_chars <= 2000 and elements <= 256 and operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": elements,
        "intended_route_operations": operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    report["demo"] = {
        "answer": demo["answer"],
        "verify": list(verify(demo, demo["answer"])),
        "enumerated_valid_answers": enumerate_all(demo),
        "candidate_space": search_space(demo),
    }
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping)
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
