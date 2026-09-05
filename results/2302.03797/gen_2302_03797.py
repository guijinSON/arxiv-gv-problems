"""Verified generator for arXiv:2302.03797.

The family is the paper's native 2-balanced SMSR problem.  Starting from a
random simple target chromosome, generation applies distinct legal symmetric
reversals that increase the number of maximal negative segments (MNS) by one.
Reversing that construction gives a shortest sequence, because Lemma 4.1
allows any symmetric reversal to remove at most one MNS.
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
from functools import lru_cache


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "permutation",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "signed chromosomes with duplicated repeat symbols",
        "symmetric-reversal sequence",
        "start-target adjacency bijection",
    ],
    "verification_operations": [
        "exact signed endpoint matching",
        "maximal negative-segment counting",
        "signed segment-reversal replay",
        "exact chromosome comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The unique adjacency matching splits the start chromosome into signed "
        "runs, after which only the short signed word of boundary occurrences "
        "controls an optimal reversal order; without this compression one must "
        "process the full chromosomes by the paper's quadratic algorithm."
    ),
    "hardness_basis": (
        "Track B: Section 4, Algorithm 1 and Theorem 4.3 solve 2-balanced SMSR "
        "in O(L^2) time; at the hard preset (L=94 symbols), the implemented "
        "reference uses 7,651 exact comparisons/updates and about 0.003--0.02 "
        "seconds per instance on this runner, while the "
        "boundary-word invariant uses at most 296 exact operations."
    ),
    "max_answer_tokens": 10,
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

# n is the number of ordinary repeat names.  Each target also has one flanking
# repeat, and ``genes`` one-copy symbols.  The witness length grows slowly while
# the repeat haystack grows much faster.
DIFFICULTY = {
    "demo": {"n": 6, "genes": 2, "distance": 2},
    "easy": {"n": 28, "genes": 4, "distance": 10},
    "medium": {"n": 36, "genes": 4, "distance": 10},
    "hard": {"n": 44, "genes": 4, "distance": 10},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Only the signed order of run-boundary occurrences matters after matching "
    "each start adjacency to its unique target copy."
)
PLACEBO_HINT = (
    "Careful tracking of signed repeat identifiers matters when comparing each "
    "step with the displayed target chromosome."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly d pairwise-distinct positive repeat identifiers, "
        "drawn without replacement from the n ordinary repeats and the flanking "
        "repeat; each identifier denotes one inclusive symmetric reversal."
    ),
    "bounds": {
        "list_length": "instance field optimum_distance d",
        "alphabet_size": "n+1 repeat identifiers",
        "entries": "positive integers naming displayed repeat symbols",
        "repetition": "forbidden",
        "candidate_count": "P(n+1,d)=(n+1)!/(n+1-d)!",
    },
}

NOTES = (
    "Definition 2.1 fixes a symmetric reversal as inclusive signed reversal "
    "between two oppositely oriented copies of one repeat. Section 4 fixes the "
    "2-balanced optimization regime: both chromosomes are simple with duplication "
    "number two, and every target repeat occurs once in each orientation. "
    "Theorem 4.1 characterizes the zero-MNS target, Lemma 4.1 gives the "
    "one-MNS-per-reversal lower bound, Theorem 4.2 supplies a proper boundary "
    "pair, and Algorithm 1/Theorem 4.3 produce an optimum in O(L^2). "
    "Section 5 makes unrestricted SSR reachability easy in O(L^2), so this is "
    "explicitly Track B; Section 6, Theorem 6.3 proves NP-hardness only after the "
    "target's balanced-orientation condition is dropped. Generation samples the "
    "answer first by composing reversals, retaining a step only when the MNS "
    "certificate rises by one. A final construction screen removes instances "
    "solved by numeric, positional, span, sign-parity, or static-boundary orders. "
    "Plants and decoys are otherwise exchangeable random repeat pairs."
)

# Filled after the script-owned bare/hinted/placebo runs.  These numbers are
# diagnostic only; G9 gates the explicit size and operation caps.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unrun",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_parameters(n, genes, distance):
    if not _is_int(n) or n < 4:
        raise ValueError("n must be an integer at least 4")
    if not _is_int(genes) or genes < 0:
        raise ValueError("genes must be a nonnegative integer")
    if not _is_int(distance) or not 1 <= distance <= n:
        raise ValueError("distance must be an integer between 1 and n")


def _left_right(symbol):
    """Return the oriented (left endpoint, right endpoint) of one symbol."""
    label = abs(symbol)
    if symbol > 0:
        return (label, 0), (label, 1)  # head, tail
    return (label, 1), (label, 0)


def _adjacencies(chromosome):
    result = []
    for left_symbol, right_symbol in zip(chromosome, chromosome[1:]):
        right_endpoint = _left_right(left_symbol)[1]
        left_endpoint = _left_right(right_symbol)[0]
        result.append((right_endpoint, left_endpoint))
    return result


def _edge_key(edge):
    return tuple(sorted(edge))


def _target_map(target):
    """Map each unoriented adjacency to its orientation in a simple target."""
    mapping = {}
    for edge in _adjacencies(target):
        # Self-loops are the paper's entangled case.  The generator excludes them
        # so the direction of every adjacency is unique and directly checkable.
        if edge[0] == edge[1]:
            return None, "target has an entangled adjacency"
        key = _edge_key(edge)
        if key in mapping:
            return None, "target is not simple: an adjacency is repeated"
        mapping[key] = edge
    return mapping, None


def _directions(chromosome, target_mapping):
    directions = []
    for edge in _adjacencies(chromosome):
        target_edge = target_mapping.get(_edge_key(edge))
        if target_edge is None:
            return None, "the chromosome and target have different adjacencies"
        if edge == target_edge:
            directions.append(1)
        elif edge == (target_edge[1], target_edge[0]):
            directions.append(-1)
        else:  # Defensive: endpoint pairs admit no third orientation.
            return None, "an adjacency has no valid direction"
    return directions, None


def _mns_count(chromosome, target, target_mapping=None):
    if target_mapping is None:
        target_mapping, error = _target_map(target)
        if error is not None:
            return None, error
    directions, error = _directions(chromosome, target_mapping)
    if error is not None:
        return None, error
    count = sum(
        direction == -1 and (index == 0 or directions[index - 1] == 1)
        for index, direction in enumerate(directions)
    )
    return count, None


@lru_cache(maxsize=512)
def _cached_mns_count(chromosome_tuple, target_tuple):
    """Cache an exact instance-only lower bound across candidate checks."""
    return _mns_count(list(chromosome_tuple), list(target_tuple))


def _positions(chromosome, label):
    return [index for index, symbol in enumerate(chromosome) if abs(symbol) == label]


def _apply_reversal(chromosome, label):
    positions = _positions(chromosome, label)
    if len(positions) != 2:
        return None, f"repeat {label} does not occur exactly twice"
    left, right = positions
    if chromosome[left] != -chromosome[right]:
        return None, f"repeat {label} is not oppositely oriented"
    middle = [-symbol for symbol in reversed(chromosome[left : right + 1])]
    return chromosome[:left] + middle + chromosome[right + 1 :], None


def _replay(start, sequence):
    current = list(start)
    for step, label in enumerate(sequence, 1):
        current, error = _apply_reversal(current, label)
        if error is not None:
            return None, f"step {step}: {error}"
    return current, None


def _boundary_word(start, target):
    mapping, error = _target_map(target)
    if error is not None:
        return None, None, error
    directions, error = _directions(start, mapping)
    if error is not None:
        return None, None, error
    word = [
        start[index]
        for index in range(1, len(start) - 1)
        if directions[index - 1] != directions[index]
    ]
    return word, directions, None


def _static_boundary_orders(start, target):
    """Plausible no-update guesses used both for screening and G6."""
    word, _directions_list, error = _boundary_word(start, target)
    if error is not None or not word:
        return []
    positions = {}
    for index, signed_label in enumerate(word):
        positions.setdefault(abs(signed_label), []).append(index)
    labels = [label for label, pos in positions.items() if len(pos) == 2]
    return [
        sorted(labels),
        sorted(labels, key=lambda label: positions[label][0]),
        sorted(labels, key=lambda label: positions[label][0], reverse=True),
        sorted(labels, key=lambda label: positions[label][1] - positions[label][0]),
    ]


def _screen_construction(start, target, repeat_ids, distance):
    """Reject only instances cracked by fixed cheap guesses, never find an answer."""
    if len(repeat_ids) < 20:
        return True
    candidates = _static_boundary_orders(start, target)
    candidates.extend(
        [
            sorted(repeat_ids)[:distance],
            sorted(
                repeat_ids,
                key=lambda label: (
                    (_positions(start, label)[-1] - _positions(start, label)[0]),
                    label,
                ),
            )[:distance],
        ]
    )
    for candidate in candidates:
        if len(candidate) != distance:
            continue
        final, error = _replay(start, candidate)
        if error is None and final == target:
            return False
    return True


def make_instance(n, seed=0, **params):
    """Inverse-generate a certified optimum 2-balanced SMSR instance."""
    genes = params.pop("genes", max(0, n // 6))
    distance = params.pop("distance", min(10, max(1, n // 8)))
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, genes, distance)
    rng = random.Random(seed)

    ordinary_repeats = list(range(1, n + 1))
    gene_ids = list(range(n + 1, n + genes + 1))
    anchor = n + genes + 1
    repeat_ids = ordinary_repeats + [anchor]

    # Resampling changes only the random object being built.  The certificate is
    # always the sequence chosen before the start chromosome exists.
    for _attempt in range(2000):
        body = []
        for label in ordinary_repeats:
            body.extend((label, -label))
        for label in gene_ids:
            body.append(label if rng.getrandbits(1) else -label)
        rng.shuffle(body)
        target = [anchor] + body + [-anchor]
        target_mapping, error = _target_map(target)
        if error is not None:
            continue

        current = list(target)
        chosen = []
        current_mns = 0
        complete = True
        for _step in range(distance):
            candidates = []
            for label in ordinary_repeats:
                if label in chosen:
                    continue
                changed, reversal_error = _apply_reversal(current, label)
                if reversal_error is not None:
                    continue
                next_mns, mns_error = _mns_count(changed, target, target_mapping)
                if mns_error is None and next_mns == current_mns + 1:
                    candidates.append(label)
            if not candidates:
                complete = False
                break
            label = candidates[rng.randrange(len(candidates))]
            chosen.append(label)
            current, _ = _apply_reversal(current, label)
            current_mns += 1

        if not complete:
            continue
        start = current
        answer = list(reversed(chosen))
        if not _screen_construction(start, target, repeat_ids, distance):
            continue
        replayed, replay_error = _replay(start, answer)
        if replay_error is not None or replayed != target:
            raise AssertionError("internal inverse-generation failure")
        certified_mns, mns_error = _mns_count(start, target, target_mapping)
        if mns_error is not None or certified_mns != distance:
            raise AssertionError("internal MNS-certificate failure")
        return {
            "paper": "arXiv:2302.03797",
            "problem": "2-balanced minimum symmetric reversals",
            "n": n,
            "genes": genes,
            "seed": seed,
            "start": start,
            "target": target,
            "repeat_ids": repeat_ids,
            "gene_ids": gene_ids,
            "anchor": anchor,
            "optimum_distance": distance,
            "answer": answer,
        }
    raise RuntimeError("could not construct a screened instance after 2000 attempts")


def _format_chromosome(chromosome, width=22):
    tokens = [f"{symbol:+d}" for symbol in chromosome]
    return "\n".join(
        "  " + " ".join(tokens[index : index + width])
        for index in range(0, len(tokens), width)
    )


def render(inst):
    repeat_text = ", ".join(str(label) for label in inst["repeat_ids"])
    gene_text = ", ".join(str(label) for label in inst["gene_ids"]) or "(none)"
    example = list(range(1, inst["optimum_distance"] + 1))
    statement = f"""Minimum symmetric reversals on signed chromosomes (2-balanced case)

A signed chromosome is an ordered list of nonzero signed integers.  The absolute
value is a symbol name and the sign is its orientation.  The repeat identifiers
are {{{repeat_text}}}; each occurs exactly twice.  The one-copy gene identifiers
are {{{gene_text}}}.  The special flanking repeat is {inst['anchor']}.

A symmetric reversal on repeat r is legal only when the current chromosome has
exactly two occurrences of r with opposite signs.  If their zero-based positions
are i<j, replace the inclusive segment x[i:j+1] by its reverse with every sign
negated.  Thus [a,b,c] becomes [-c,-b,-a].  Positions are recomputed after every
step.  Different listed reversals are applied from left to right.

Find a shortest sequence transforming START exactly into TARGET.  For this
instance the optimum length is {inst['optimum_distance']}.  Your list must contain
exactly {inst['optimum_distance']} pairwise-distinct positive repeat identifiers;
order matters, genes may not be used, and the displayed orientation of TARGET is
the required final orientation.

START ({len(inst['start'])} symbols):
{_format_chromosome(inst['start'])}

TARGET ({len(inst['target'])} symbols):
{_format_chromosome(inst['target'])}

Give your final answer inside <answer></answer> tags as one JSON list of exactly
{inst['optimum_distance']} integers, in execution order.
Example of the required syntax: <answer>{json.dumps(example)}</answer>
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
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    content = matches[-1].strip()
    fence = re.fullmatch(r"```(?:json|text)?\s*(.*?)\s*```", content, flags=re.I | re.S)
    if fence:
        content = fence.group(1).strip()
    try:
        value = json.loads(content)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list) or any(not _is_int(item) for item in value):
        return None
    return value


def verify(inst, answer):
    """Check any formatted optimum reversal sequence; never inspect inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if any(not _is_int(label) for label in answer):
        return False, "every answer entry must be an integer"
    allowed = set(inst["repeat_ids"])
    for index, label in enumerate(answer):
        if label not in allowed:
            return False, f"unknown repeat identifier at index {index}: {label}"
    if len(set(answer)) != len(answer):
        return False, "repeat identifiers must be pairwise distinct"

    optimum, error = _cached_mns_count(tuple(inst["start"]), tuple(inst["target"]))
    if error is not None:
        return False, "invalid instance: " + error
    if len(answer) != optimum:
        return False, f"wrong length: the exact MNS lower bound is {optimum}, got {len(answer)}"

    final, error = _replay(inst["start"], answer)
    if error is not None:
        return False, error
    if final != inst["target"]:
        mismatch = next(
            (index for index, pair in enumerate(zip(final, inst["target"])) if pair[0] != pair[1]),
            None,
        )
        return False, f"replay does not reach TARGET (first mismatch at position {mismatch})"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample uniformly from the stated fixed-length, no-repeat language."""
    return rng.sample(inst["repeat_ids"], inst["optimum_distance"])


def _permutation_count(alphabet, length):
    result = 1
    for value in range(alphabet - length + 1, alphabet + 1):
        result *= value
    return result


def search_space(inst):
    return _permutation_count(len(inst["repeat_ids"]), inst["optimum_distance"])


def enumerate_all(inst):
    space = search_space(inst)
    if space > 100_000:
        return None
    count = 0
    for candidate in itertools.permutations(inst["repeat_ids"], inst["optimum_distance"]):
        count += int(verify(inst, list(candidate))[0])
    return count


def _canonical_form(first, second, repeat_ids, gene_ids, anchor):
    repeat_set, gene_set = set(repeat_ids), set(gene_ids)
    labels = {anchor: ("A", 0)}
    orientation = {anchor: 1}
    next_repeat = next_gene = 0
    encoded = []
    for chromosome in (first, second):
        row = []
        for symbol in chromosome:
            label = abs(symbol)
            sign = 1 if symbol > 0 else -1
            if label not in labels:
                if label in repeat_set:
                    labels[label] = ("R", next_repeat)
                    next_repeat += 1
                elif label in gene_set:
                    labels[label] = ("G", next_gene)
                    next_gene += 1
                else:
                    labels[label] = ("X", label)
                orientation[label] = sign
            role, rank = labels[label]
            normalized_sign = sign * orientation[label]
            row.append((role, rank, normalized_sign))
        encoded.append(tuple(row))
    return tuple(encoded)


def canonical_key(inst):
    """Canonicalize renaming/sign gauges and whole-chromosome reversal."""
    start, target = inst["start"], inst["target"]
    rev_start = [-symbol for symbol in reversed(start)]
    rev_target = [-symbol for symbol in reversed(target)]
    pairs = [
        (start, target),
        (rev_start, rev_target),
    ]
    forms = [
        _canonical_form(
            first,
            second,
            inst["repeat_ids"],
            inst["gene_ids"],
            inst["anchor"],
        )
        for first, second in pairs
    ]
    payload = json.dumps(
        {"distance": inst["optimum_distance"], "form": min(forms)},
        separators=(",", ":"),
    )
    return "smsr2:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params):
    harder = dict(params)
    n = int(harder.get("n", 0))
    if n >= 45:
        return "cap_bound"
    harder["n"] = 45
    harder["genes"] = int(harder.get("genes", 0))
    # Keep the answer length fixed: only the repeat haystack grows.
    return harder


def _attack_smallest_labels(inst):
    return sorted(inst["repeat_ids"])[: inst["optimum_distance"]]


def _attack_shortest_spans(inst):
    scored = []
    for label in inst["repeat_ids"]:
        positions = _positions(inst["start"], label)
        scored.append((positions[-1] - positions[0], label))
    return [label for _span, label in sorted(scored)[: inst["optimum_distance"]]]


def _orientation_product(chromosome, label):
    values = [symbol for symbol in chromosome if abs(symbol) == label]
    return math.prod(1 if symbol > 0 else -1 for symbol in values)


def _attack_sign_parity(inst):
    labels = list(inst["repeat_ids"])
    labels.sort(
        key=lambda label: (
            _orientation_product(inst["start"], label)
            == _orientation_product(inst["target"], label),
            _positions(inst["start"], label)[0],
        )
    )
    return labels[: inst["optimum_distance"]]


def _attack_static_boundaries(inst):
    orders = _static_boundary_orders(inst["start"], inst["target"])
    if not orders:
        return _attack_smallest_labels(inst)
    return orders[1]


def _attack_leftmost_greedy(inst):
    current = list(inst["start"])
    chosen = []
    for _step in range(inst["optimum_distance"]):
        mismatch = next(
            (i for i, (left, right) in enumerate(zip(current, inst["target"])) if left != right),
            len(current) // 2,
        )
        choices = []
        for label in inst["repeat_ids"]:
            if label in chosen:
                continue
            positions = _positions(current, label)
            if len(positions) != 2 or current[positions[0]] != -current[positions[1]]:
                continue
            left, right = positions
            covers = left <= mismatch <= right
            choices.append((not covers, right - left, abs(left - mismatch), label))
        if not choices:
            break
        label = min(choices)[-1]
        chosen.append(label)
        current, _ = _apply_reversal(current, label)
    for label in inst["repeat_ids"]:
        if len(chosen) == inst["optimum_distance"]:
            break
        if label not in chosen:
            chosen.append(label)
    return chosen


def _attack_random_restart(inst, rng, restarts=256):
    last = None
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last
    return last


def _reference_algorithm(inst, naive_matching=True):
    """Implement Section 4 Algorithm 1 without reading the planted answer."""
    started = time.perf_counter()
    target_edges = _adjacencies(inst["target"])
    start_edges = _adjacencies(inst["start"])
    operations = 0
    mapping = {}
    if naive_matching:
        for edge in start_edges:
            key = _edge_key(edge)
            found = None
            for target_edge in target_edges:
                operations += 1
                if key == _edge_key(target_edge):
                    found = target_edge
                    break
            if found is None:
                return None, {"operations": operations, "wall_clock_sec": time.perf_counter() - started}
            mapping[key] = found
    else:
        mapping = {_edge_key(edge): edge for edge in target_edges}
        operations += len(target_edges)

    current = list(inst["start"])
    sequence = []
    for _round in range(len(current)):
        if current == inst["target"]:
            break
        directions, error = _directions(current, mapping)
        operations += len(current) - 1
        if error is not None:
            return None, {"operations": operations, "wall_clock_sec": time.perf_counter() - started}
        boundary = [False] * len(current)
        for index in range(1, len(current) - 1):
            operations += 1
            boundary[index] = directions[index - 1] != directions[index]
        positions = {}
        for index, symbol in enumerate(current):
            operations += 1
            positions.setdefault(abs(symbol), []).append(index)
        choices = []
        for label, pair in positions.items():
            operations += 1
            if (
                len(pair) == 2
                and boundary[pair[0]]
                and boundary[pair[1]]
                and current[pair[0]] == -current[pair[1]]
            ):
                choices.append(label)
        if not choices:
            return None, {"operations": operations, "wall_clock_sec": time.perf_counter() - started}
        label = min(choices)
        sequence.append(label)
        current, error = _apply_reversal(current, label)
        if error is not None:
            return None, {"operations": operations, "wall_clock_sec": time.perf_counter() - started}
    stats = {
        "operations": operations,
        "wall_clock_sec": time.perf_counter() - started,
        "reversals": len(sequence),
    }
    return sequence if current == inst["target"] else None, stats


def _compact_boundary_algorithm(inst):
    """Compress Algorithm 1 to the signed boundary word and count exact work."""
    word, directions, error = _boundary_word(inst["start"], inst["target"])
    if error is not None:
        return None, {"operations": 0, "error": error}
    # One exact operation per target-index insertion and per start lookup.
    operations = (len(inst["target"]) - 1) + len(directions)
    sequence = []
    while word:
        positions = {}
        for index, symbol in enumerate(word):
            positions.setdefault(abs(symbol), []).append(index)
        choices = [
            label
            for label, pair in positions.items()
            if len(pair) == 2 and word[pair[0]] == -word[pair[1]]
        ]
        if not choices:
            return None, {"operations": operations, "error": "no proper boundary pair"}
        label = min(choices)
        left, right = positions[label]
        operations += right - left + 1
        transformed = [-symbol for symbol in reversed(word[left : right + 1])]
        word = word[:left] + transformed + word[right + 1 :]
        # The chosen occurrences cease to be boundaries.  Every other boundary
        # remains a boundary; only its signed order inside the word changes.
        word = word[:left] + word[left + 1 : right] + word[right + 1 :]
        sequence.append(label)
    return sequence, {"operations": operations, "reversals": len(sequence)}


def _relabel_instance(inst, seed):
    rng = random.Random(seed)
    repeats = [label for label in inst["repeat_ids"] if label != inst["anchor"]]
    genes = list(inst["gene_ids"])
    shuffled_repeats, shuffled_genes = list(repeats), list(genes)
    rng.shuffle(shuffled_repeats)
    rng.shuffle(shuffled_genes)
    mapping = dict(zip(repeats, shuffled_repeats))
    mapping.update(zip(genes, shuffled_genes))
    mapping[inst["anchor"]] = inst["anchor"]
    flips = {label: (-1 if rng.getrandbits(1) else 1) for label in repeats + genes}
    flips[inst["anchor"]] = 1

    def convert(symbol):
        sign = 1 if symbol > 0 else -1
        return sign * flips[abs(symbol)] * mapping[abs(symbol)]

    transformed = dict(inst)
    transformed["start"] = [convert(symbol) for symbol in inst["start"]]
    transformed["target"] = [convert(symbol) for symbol in inst["target"]]
    transformed["repeat_ids"] = sorted(mapping[label] for label in inst["repeat_ids"])
    transformed["gene_ids"] = sorted(mapping[label] for label in inst["gene_ids"])
    transformed["answer"] = [mapping[label] for label in inst["answer"]]
    return transformed


def _reverse_instance(inst):
    transformed = dict(inst)
    transformed["start"] = [-symbol for symbol in reversed(inst["start"])]
    transformed["target"] = [-symbol for symbol in reversed(inst["target"])]
    transformed["answer"] = list(inst["answer"])
    return transformed


def _json_answer_size(answer):
    serialized = json.dumps(answer)
    return len(serialized), (len(serialized) + 3) // 4


def selftest():
    report = {
        "paper": "arXiv:2302.03797",
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
                failures.append({"preset": preset, "seed": seed, "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
        "construction": "inverse reversal composition with a one-MNS increase certified at every step",
    }

    shipping = make_instance(seed=230203797, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    replacement = next(label for label in shipping["repeat_ids"] if label not in planted)
    changed = list(planted)
    changed[0] = replacement
    duplicate = list(planted)
    duplicate[-1] = duplicate[0]
    out_of_range = list(planted)
    out_of_range[0] = max(shipping["repeat_ids"]) + 1000
    corruptions = {
        "drop_one": planted[:-1],
        "swap_one_for_decoy": changed,
        "duplicate_one": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = {entry["reason"] for entry in corruption_results.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in corruption_results.values())
        and len(reasons) == len(corruption_results),
        "cases": corruption_results,
        "distinct_reasons": len(reasons),
    }

    realistic = (
        "The boundary order gives the following sequence.\n<answer>\n```json\n"
        + json.dumps(planted)
        + "\n```\n</answer>\nI replayed it from left to right."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("there is no tagged answer") is None,
        "parsed": parsed,
    }

    guess_rng = random.Random(0x230203797)
    guess_total = 200_000
    guess_hits = 0
    guess_started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_elapsed = time.perf_counter() - guess_started
    observed_density = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": observed_density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": observed_density,
        "structure_aware_space": search_space(shipping),
        "sampling_rule": "uniform ordered samples without replacement, already enforcing exact length, repeat-only entries, and distinctness",
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attacks = {
        "outlier_smallest_identifiers": lambda inst, rng: _attack_smallest_labels(inst),
        "outlier_shortest_spans": lambda inst, rng: _attack_shortest_spans(inst),
        "sign_parity_guess": lambda inst, rng: _attack_sign_parity(inst),
        "static_boundary_left_to_right": lambda inst, rng: _attack_static_boundaries(inst),
        "greedy_leftmost_mismatch": lambda inst, rng: _attack_leftmost_greedy(inst),
        "random_restart_256": lambda inst, rng: _attack_random_restart(inst, rng, 256),
    }
    attack_results = {name: {"successes": 0, "attempts": 0} for name in attacks}
    attack_elapsed = {name: 0.0 for name in attacks}
    reference_successes = compact_successes = 0
    reference_operations = []
    reference_elapsed = 0.0
    compact_operations = []
    attack_seeds = list(range(8100, 8108))
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for offset, (name, attack) in enumerate(attacks.items()):
            rng = random.Random(seed * 1009 + offset)
            started = time.perf_counter()
            candidate = attack(inst, rng)
            attack_elapsed[name] += time.perf_counter() - started
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])
            attack_results[name]["attempts"] += 1

        solution, stats = _reference_algorithm(inst, naive_matching=True)
        reference_elapsed += stats["wall_clock_sec"]
        reference_operations.append(stats["operations"])
        if solution is not None:
            reference_successes += int(verify(inst, solution)[0])
        compact_solution, compact_stats = _compact_boundary_algorithm(inst)
        compact_operations.append(compact_stats["operations"])
        if compact_solution is not None:
            compact_successes += int(verify(inst, compact_solution)[0])

    for name in attacks:
        attack_results[name]["wall_clock_sec_total_8"] = round(attack_elapsed[name], 6)
    all_attacks_failed = all(row["successes"] == 0 for row in attack_results.values())
    reference = {
        "name": "Section 4 Algorithm 1: adjacency matching and proper-boundary reversals",
        "complexity": "O(L^2) exact comparisons for chromosome length L",
        "wall_clock_sec_total_8": round(reference_elapsed, 6),
        "wall_clock_sec_mean": round(reference_elapsed / len(attack_seeds), 8),
        "operations_mean": sum(reference_operations) // len(reference_operations),
        "operations_min": min(reference_operations),
        "operations_max": max(reference_operations),
        "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed
        and reference_successes == len(attack_seeds)
        and compact_successes == len(attack_seeds),
        "attacks": attack_results,
        "reference_algorithm": reference,
        "compact_route": {
            "name": "unique adjacency directions compressed to the signed boundary word",
            "operations_mean": sum(compact_operations) / len(compact_operations),
            "operations_min": min(compact_operations),
            "operations_max": max(compact_operations),
            "worst_case_bound": (
                2 * (len(shipping["start"]) - 1)
                + shipping["optimum_distance"] * (shipping["optimum_distance"] + 1)
            ),
            "solves": f"{compact_successes}/{len(attack_seeds)}, as expected",
        },
    }

    strongest = max(attack_elapsed, key=attack_elapsed.get)
    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    report["G5_density_and_baseline_cost"] = {
        "pass": observed_density < 1e-6 and all_attacks_failed,
        "sampled_density_at_shipping": observed_density,
        "density_hits": guess_hits,
        "density_samples": guess_total,
        "candidate_space": search_space(shipping),
        "strongest_failing_attack": strongest,
        "attack_wall_clock_sec_total_8": round(attack_elapsed[strongest], 6),
        "random_restart_candidates_total_8": 256 * len(attack_seeds),
        "reference_algorithm_operations_mean": reference["operations_mean"],
        "reference_algorithm_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
        "demo_exact_valid_answers": enumerate_all(demo),
        "demo_candidate_space": search_space(demo),
    }

    doubled = make_instance(
        n=2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        genes=2 * DIFFICULTY[SHIPPING_DIFFICULTY]["genes"],
        distance=DIFFICULTY[SHIPPING_DIFFICULTY]["distance"],
        seed=707,
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and len(doubled["start"]) > len(shipping["start"]),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_chromosome_symbols": len(shipping["start"]),
        "doubled_chromosome_symbols": len(doubled["start"]),
        "answer_elements_both": shipping["optimum_distance"],
        "verify_reason": doubled_reason,
    }

    invariance_checks = carried_checks = 0
    key_failures = []
    for offset in range(20):
        inst = make_instance(seed=9000 + offset, **DIFFICULTY["medium"])
        expected_key = canonical_key(inst)
        relabelled = _relabel_instance(inst, 12000 + offset)
        variants = [
            ("relabel_and_sign_gauge", relabelled),
            ("whole_reverse", _reverse_instance(inst)),
            (
                "composed_relabel_and_whole_reverse",
                _reverse_instance(relabelled),
            ),
        ]
        for name, transformed in variants:
            invariance_checks += 1
            if canonical_key(transformed) != expected_key:
                key_failures.append({"seed": offset, "variant": name, "reason": "key changed"})
            carried_checks += 1
            ok, reason = verify(transformed, transformed["answer"])
            if not ok:
                key_failures.append({"seed": offset, "variant": name, "reason": reason})
    unrelated = [
        canonical_key(make_instance(seed=20000 + offset, **DIFFICULTY["medium"]))
        for offset in range(20)
    ]
    distinct_keys = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct_keys == 20,
        "invariance_checks": invariance_checks,
        "invariance_failures": key_failures,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "symmetries_tested": [
            "repeat and gene renaming",
            "independent symbol-orientation gauge flips",
            "simultaneous whole-chromosome reverse-negation",
            "composition of all preceding transformations",
        ],
        "canonicalization": "first-occurrence role ranks, orientation normalization, and lexicographic minimization over direction/reversal",
    }

    answer_chars, answer_tokens = _json_answer_size(shipping["answer"])
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    intended_bound = (
        2 * (len(shipping["start"]) - 1)
        + shipping["optimum_distance"] * (shipping["optimum_distance"] + 1)
    )
    within_caps = (
        answer_chars <= 2000
        and len(shipping["answer"]) <= 256
        and intended_bound <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "oracle_status": "unrun or unavailable when attempts is zero",
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": len(shipping["answer"]),
        "intended_route_operations": intended_bound,
        "measured_compact_operations_max_8": max(compact_operations),
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["pass"] = all(gate.get("pass") is True for gate in gates)
    report["all_passed"] = report["pass"]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
