"""Verified Prouhet--Tarry--Escott generator for arXiv:2506.11429.

The generator first samples a weighted Boolean cube.  Its even- and odd-parity
vertices have identical power sums below the cube dimension.  In even cube
dimension, each parity class is also closed under the central reflection that
maps a subset to its complement.  A positive translation and a permutation
then hide the construction.  The witness is therefore known by composition of
identities, never by solving the emitted instance.
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
    "native_domain": "number_theory",
    "object_regime": "integer_lattice",
    "computational_core": "subset_sum",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "finite set of non-negative integers",
        "central reflection involution on that set",
    ],
    "verification_operations": [
        "exact integer membership, cardinality, and reflection-pair checks",
        "exact centered second- and fourth-power accumulation",
        "exact comparison equivalent to the five requested power-sum equations",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Recognize a translated Boolean subset-sum cube and color its vertices "
        "by subset parity; otherwise solve a balanced multi-moment subset-sum "
        "problem over the displayed reflection pairs."
    ),
    "hardness_basis": (
        "Track B: symmetry-aware meet-in-the-middle on 32 reflection pairs, "
        "cardinality, and the two independent centered moments runs in "
        "O(2*2^(P/2)) exact time and O(2^(P/2)) memory for P pairs; at the "
        "480-bit-weight/480-bit-scale shipping preset (P=32, degree 5) the "
        "included implementation uses 589,914 counted operations and about "
        "0.3 seconds in repeated local self-tests; "
        "Boolean-cube reconstruction takes "
        "127 exact arithmetic operations and "
        "requires recognizing the hidden invariant."
    ),
    "max_answer_tokens": 17,
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

# n is the bit length of the hidden subset-sum generators.  scale_bits is an
# independent fixed-answer-length dial controlling the common affine dilation.
# Every non-demo witness is one 64-symbol coloring, so both numeric dials can
# grow without making the answer longer.  The demo uses the smallest
# even-dimensional cube that illustrates the same construction on paper.
DIFFICULTY = {
    "demo": {"n": 5, "dimension": 4, "scale_bits": 4},
    "easy": {"n": 160, "dimension": 6, "scale_bits": 160},
    "medium": {"n": 240, "dimension": 6, "scale_bits": 240},
    "hard": {"n": 480, "dimension": 6, "scale_bits": 480},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The centered reflection-pairs are vertices of a weighted Boolean cube "
    "whose subset parity is constant on each pair."
)
PLACEBO_HINT = (
    "The displayed reflection-pairs reward careful bookkeeping when comparing "
    "the several required integer moments."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A word over {A,B}, one symbol per displayed row (at most 64), containing "
        "half A and half B and assigning both members of every x -> C-x "
        "reflection pair the same symbol; swapping all A/B symbols denotes the "
        "complementary valid witness."
    ),
    "bounds": {
        "max_pool_size": 64,
        "max_answer_symbols": 64,
        "max_value_bits": 2055,
        "alphabet": ["A", "B"],
        "reflection_closed": True,
        "max_symbols_of_each_kind": 32,
        "order_matches_displayed_rows": True,
    },
}

NOTES = (
    "Section 1.1 fixes the native PTE definition: two distinct integer arrays "
    "of the same size have equal sums of k-th powers for k=1,...,degree. "
    "Equation (1.4) proves that a common integer dilation and translation "
    "preserve a solution, and Definition 2 makes equal-sum reflection pairs "
    "the defining feature of ideal symmetric PTE solutions of odd degree. The same "
    "section identifies the easy boundary side_size<=degree, where no "
    "non-trivial solution exists. Section 6 gives exhaustive computer-search "
    "algorithms, not a distributional hardness theorem, so this family is "
    "Track B. For six sampled positive weights, the signed exponential "
    "generating function is product(1-exp(w_i*t)), whose first five moments "
    "vanish. Because six is even, subset complementation preserves parity, so "
    "each planted side is a union of sixteen central-reflection pairs. A common "
    "dilation, translation, and a permutation carry the witness to the visible "
    "instance. "
    "The witness is emitted as the A/B coloring of the displayed rows, so "
    "coefficient bit lengths grow without lengthening the answer. The "
    "adversary panel tests pair width outliers, greedy fourth-moment "
    "balancing, sorted alternation, and structure-aware random restarts; the "
    "successful symmetry-aware meet-in-the-middle algorithm is reported "
    "separately, as Track B requires."
)

# Filled from independent script-owned harden.py runs before release.  These
# three arms are diagnostic under the current G9 specification; only the
# answer-size and intended-route caps contribute to the G9 pass value.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 1, "attempts": 3},
    "hinted_verdict": "cap_bound",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _valid_parameters(n, dimension, scale_bits):
    return (
        _is_int(n)
        and _is_int(dimension)
        and _is_int(scale_bits)
        and 5 <= n <= 1024
        and dimension in (4, 6)
        and 4 <= scale_bits <= 1024
        and n >= dimension + 1
    )


def _subset_sums(weights):
    sums = [0]
    masks = [0]
    for bit, weight in enumerate(weights):
        old_sums = list(sums)
        old_masks = list(masks)
        sums.extend(value + weight for value in old_sums)
        masks.extend(mask | (1 << bit) for mask in old_masks)
    return sums, masks


def _sample_weights(rng, n, dimension):
    """Sample positive n-bit weights having distinct subset sums."""
    low, high = 1 << (n - 1), 1 << n
    for _attempt in range(10000):
        weights = [rng.randrange(low, high) for _ in range(dimension)]
        sums, _masks = _subset_sums(weights)
        if len(set(sums)) == 1 << dimension:
            return weights
    raise RuntimeError("could not sample dissociated positive weights")


def make_instance(n, seed=0, dimension=6, scale_bits=48, **params):
    """Construct a symmetric PTE instance from a weighted Prouhet identity."""
    if params:
        raise ValueError("unsupported parameters: " + ", ".join(sorted(params)))
    if not _valid_parameters(n, dimension, scale_bits):
        raise ValueError(
            "need 5<=n<=1024, dimension in {4,6}, 4<=scale_bits<=1024, "
            "and n>=dimension+1"
        )
    if not _is_int(seed):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    weights = _sample_weights(rng, n, dimension)
    raw_sums, masks = _subset_sums(weights)
    scale = rng.randrange(1 << (scale_bits - 1), 1 << scale_bits)
    shift_bits = n + scale_bits
    shift = rng.randrange(1 << (shift_bits - 1), 1 << shift_bits)
    tagged = [(scale * raw + shift, mask) for raw, mask in zip(raw_sums, masks)]
    rng.shuffle(tagged)

    values = [value for value, _mask in tagged]
    answer = "".join(
        "A" if mask.bit_count() % 2 == 0 else "B" for _value, mask in tagged
    )
    return {
        "degree": dimension - 1,
        "side_size": 1 << (dimension - 1),
        "values": values,
        "n_bits": n,
        "scale_bits": scale_bits,
        "answer": answer,
    }


def _decode_instance(inst):
    if not isinstance(inst, dict):
        return None
    degree = inst.get("degree")
    side_size = inst.get("side_size")
    values = inst.get("values")
    if (
        not _is_int(degree)
        or degree not in (3, 5)
        or not _is_int(side_size)
        or side_size != 1 << degree
        or not isinstance(values, list)
        or len(values) != 2 * side_size
        or any(not _is_int(value) or value < 0 for value in values)
        or len(set(values)) != len(values)
    ):
        return None
    return degree, side_size, values


def _reflection_pairs(values):
    """Return sorted (low, high) pairs, or None if central symmetry fails."""
    pool = set(values)
    center_sum = min(values) + max(values)
    if any(center_sum - value not in pool for value in values):
        return None
    pairs = sorted(
        (value, center_sum - value)
        for value in values
        if value < center_sum - value
    )
    if len(pairs) * 2 != len(values):
        return None
    return center_sum, pairs


def render(inst):
    decoded = _decode_instance(inst)
    if decoded is None:
        raise ValueError("malformed instance")
    degree, side_size, values = decoded
    reflected = _reflection_pairs(values)
    if reflected is None:
        raise ValueError("instance is not centrally symmetric")
    center_sum, _pairs = reflected
    rows = "\n".join(f"  {index}: {value}" for index, value in enumerate(values, 1))
    statement = f"""Centrally symmetric Prouhet--Tarry--Escott witness

Below are {len(values)} distinct non-negative integers. Their minimum plus their
maximum is C = {center_sum}. Every displayed integer x has the unique displayed
reflection partner C-x.

Color every displayed row either A or B, subject to both requirements below.
Your answer is a {len(values)}-character word whose character in position i is
the color of displayed row i.

1. Use exactly {side_size} A symbols and {side_size} B symbols. Both members of
   each reflection pair must receive the same symbol. Thus each color consists
   of exactly {side_size // 2} whole reflection pairs.
2. For every exponent k = 1, 2, ..., {degree}, the exact integer power sums agree:

       sum(a**k for a in A) = sum(b**k for b in B).

The labels before the colons are 1-based row numbers. The first answer symbol
colors row 1, the second colors row 2, and so on; symbols may not be reordered.
Uppercase A and B are the only allowed symbols. Arithmetic is over ordinary
integers with no rounding or modulus.

Displayed integers:
{rows}

Give your final answer inside <answer></answer> tags as exactly one unquoted
{len(values)}-character word over uppercase A and B. Example syntax for a
hypothetical four-row instance: <answer>ABBA</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse a tagged A/B word, tolerating prose and markdown fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", body, flags=re.I | re.S)
    if fence:
        body = fence.group(1).strip()
    if re.fullmatch(r"[AB]+", body) is None:
        return None
    return body


def verify(inst, answer):
    """Check any submitted symmetric PTE coloring exactly; never read the plant."""
    decoded = _decode_instance(inst)
    if decoded is None:
        return False, "malformed instance"
    degree, side_size, values = decoded
    reflected = _reflection_pairs(values)
    if reflected is None:
        return False, "displayed values are not centrally symmetric"
    center_sum, _pairs = reflected
    if not isinstance(answer, str):
        return False, "answer must be an A/B word"
    if not answer:
        return False, "answer is empty"
    if any(symbol not in "AB" for symbol in answer):
        bad = next(symbol for symbol in answer if symbol not in "AB")
        return False, f"answer contains invalid symbol {bad!r}; use only A and B"
    if len(answer) < len(values):
        return False, f"answer is too short: {len(answer)} symbols; expected {len(values)}"
    if len(answer) > len(values):
        return False, f"answer is too long: {len(answer)} symbols; expected {len(values)}"
    if answer.count("A") != side_size:
        return False, f"answer has {answer.count('A')} A symbols; expected {side_size}"

    color_of = dict(zip(values, answer))
    broken = next(
        (value for value in values if color_of[value] != color_of[center_sum - value]),
        None,
    )
    if broken is not None:
        return False, f"reflection partners of value {broken} have different colors"

    # For a reflection-closed equal-size coloring, equality through odd degree
    # five is equivalent to equality of the centered second and fourth moments.
    # Use doubled centered coordinates delta=2*x-C to stay entirely integral.
    even_exponents = tuple(range(2, degree + 1, 2))
    totals = {exponent: 0 for exponent in even_exponents}
    chosen = {exponent: 0 for exponent in even_exponents}
    for low, high in _pairs:
        delta2 = (high - low) ** 2
        totals[2] += delta2
        if color_of[low] == "A":
            chosen[2] += delta2
        if degree >= 4:
            delta4 = delta2 * delta2
            totals[4] += delta4
            if color_of[low] == "A":
                chosen[4] += delta4
    for exponent in even_exponents:
        discrepancy = 2 * chosen[exponent] - totals[exponent]
        if discrepancy:
            return False, f"centered power {exponent} sums differ by {discrepancy}"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly choose half the reflection pairs, satisfying the free rules."""
    decoded = _decode_instance(inst)
    if decoded is None or not isinstance(rng, random.Random):
        raise ValueError("need a valid instance and random.Random")
    _degree, side_size, values = decoded
    reflected = _reflection_pairs(values)
    if reflected is None:
        raise ValueError("instance is not centrally symmetric")
    _center_sum, pairs = reflected
    selected = {value for pair in rng.sample(pairs, side_size // 2) for value in pair}
    return "".join("A" if value in selected else "B" for value in values)


def search_space(inst):
    decoded = _decode_instance(inst)
    if decoded is None:
        raise ValueError("malformed instance")
    _degree, side_size, values = decoded
    reflected = _reflection_pairs(values)
    if reflected is None:
        raise ValueError("instance is not centrally symmetric")
    _center_sum, pairs = reflected
    return math.comb(len(pairs), side_size // 2)


def enumerate_all(inst):
    """Brute-force the bounded language only when it has <=200,000 members."""
    decoded = _decode_instance(inst)
    if decoded is None:
        raise ValueError("malformed instance")
    _degree, side_size, values = decoded
    reflected = _reflection_pairs(values)
    if reflected is None:
        raise ValueError("instance is not centrally symmetric")
    _center_sum, pairs = reflected
    if search_space(inst) > 200000:
        return None
    count = 0
    for chosen_pairs in itertools.combinations(pairs, side_size // 2):
        selected = {value for pair in chosen_pairs for value in pair}
        candidate = "".join("A" if value in selected else "B" for value in values)
        count += int(verify(inst, candidate)[0])
    return count


def _compact_cube_recover(inst):
    """Recover the subset-parity half, counting exact arithmetic operations."""
    decoded = _decode_instance(inst)
    if decoded is None:
        return None, {"operations": 0, "reason": "malformed instance"}
    degree, _side_size, values = decoded
    dimension = degree + 1
    shift = min(values)
    normalized = [value - shift for value in values]

    ordered = sorted(normalized)
    sum_to_mask = {0: 0}
    additions = 0
    for bit in range(dimension):
        unexplained = next((value for value in ordered if value not in sum_to_mask), None)
        if unexplained is None:
            return None, {"operations": 0, "reason": "cube dimension collapsed"}
        additions_here = {
            subtotal + unexplained: mask | (1 << bit)
            for subtotal, mask in list(sum_to_mask.items())
        }
        additions += len(sum_to_mask)
        if set(additions_here) & set(sum_to_mask):
            return None, {"operations": 0, "reason": "non-dissociated cube"}
        sum_to_mask.update(additions_here)
    if set(sum_to_mask) != set(normalized) or len(sum_to_mask) != len(values):
        return None, {"operations": 0, "reason": "not a complete subset-sum cube"}

    answer = "".join(
        "A" if sum_to_mask[norm].bit_count() % 2 == 0 else "B"
        for norm in normalized
    )
    operations = len(values) + additions
    ok, reason = verify(inst, answer)
    return (answer if ok else None), {
        "operations": operations,
        "subtractions": len(values),
        "subset_sum_additions": additions,
        "reason": reason,
    }


def _pair_features(pair, degree, counter):
    """Centered even moments that determine pair sums through odd degree."""
    delta = pair[1] - pair[0]
    delta2 = delta * delta
    counter["operations"] += 2
    features = [delta2]
    power = delta2
    for _exponent in range(4, degree, 2):
        power *= delta2
        counter["operations"] += 1
        features.append(power)
    return tuple(features)


def _state_table(features, counter):
    width = len(features[0])
    states = [(0,) * (width + 1)] * (1 << len(features))
    for mask in range(1, 1 << len(features)):
        bit_value = mask & -mask
        bit = bit_value.bit_length() - 1
        previous = states[mask ^ bit_value]
        row = features[bit]
        states[mask] = (previous[0] + 1,) + tuple(
            previous[index + 1] + row[index] for index in range(width)
        )
        counter["operations"] += width + 1
    return states


def _mitm_reference(inst):
    """Exact symmetry-aware meet-in-the-middle, independent of the plant."""
    decoded = _decode_instance(inst)
    if decoded is None:
        return None, {"operations": 0, "lookups": 0, "wall_clock_sec": 0.0}
    degree, side_size, values = decoded
    reflected = _reflection_pairs(values)
    if reflected is None:
        return None, {"operations": 0, "lookups": 0, "wall_clock_sec": 0.0}
    _center_sum, pairs = reflected
    if len(pairs) > 32:
        return None, {"operations": 0, "lookups": 0, "wall_clock_sec": 0.0}

    started = time.perf_counter()
    counter = {"operations": 0}
    features = [_pair_features(pair, degree, counter) for pair in pairs]
    width = len(features[0])
    targets = (side_size // 2,) + tuple(
        sum(row[index] for row in features) // 2 for index in range(width)
    )

    split = len(pairs) // 2
    right_states = _state_table(features[split:], counter)
    right_first = {}
    right_counts = {}
    for mask, state in enumerate(right_states):
        right_first.setdefault(state, mask)
        right_counts[state] = right_counts.get(state, 0) + 1

    left_states = _state_table(features[:split], counter)
    lookups = 0
    valid_count = 0
    found_masks = None
    for left_mask, state in enumerate(left_states):
        needed = tuple(targets[index] - state[index] for index in range(width + 1))
        counter["operations"] += width + 1
        lookups += 1
        matches = right_counts.get(needed, 0)
        valid_count += matches
        if matches and found_masks is None:
            found_masks = (left_mask, right_first[needed])

    answer = None
    if found_masks is not None:
        left_mask, right_mask = found_masks
        chosen_pairs = [
            pairs[index]
            for index in range(split)
            if left_mask & (1 << index)
        ]
        chosen_pairs.extend(
            pairs[split + index]
            for index in range(len(pairs) - split)
            if right_mask & (1 << index)
        )
        selected = {value for pair in chosen_pairs for value in pair}
        candidate = "".join("A" if value in selected else "B" for value in values)
        if verify(inst, candidate)[0]:
            answer = candidate

    return answer, {
        "operations": counter["operations"],
        "lookups": lookups,
        "right_states": len(right_states),
        "valid_count": valid_count,
        "wall_clock_sec": time.perf_counter() - started,
    }


def _outlier_pair_widths(inst):
    _degree, side_size, values = _decode_instance(inst)
    _center_sum, pairs = _reflection_pairs(values)
    ordered = sorted(pairs, key=lambda pair: pair[1] - pair[0])
    quarter = side_size // 4
    chosen = ordered[:quarter] + ordered[-quarter:]
    selected = {value for pair in chosen for value in pair}
    return "".join("A" if value in selected else "B" for value in values)


def _greedy_fourth_moment(inst):
    _degree, side_size, values = _decode_instance(inst)
    _center_sum, pairs = _reflection_pairs(values)
    left, right = [], []
    left_sum = right_sum = 0
    for pair in sorted(pairs, key=lambda p: (p[1] - p[0]) ** 4, reverse=True):
        score = (pair[1] - pair[0]) ** 4
        if len(left) >= side_size // 2:
            right.append(pair)
            right_sum += score
        elif len(right) >= side_size // 2:
            left.append(pair)
            left_sum += score
        elif left_sum <= right_sum:
            left.append(pair)
            left_sum += score
        else:
            right.append(pair)
            right_sum += score
    selected = {value for pair in left for value in pair}
    return "".join("A" if value in selected else "B" for value in values)


def _sorted_pair_alternation(inst):
    _degree, _side_size, values = _decode_instance(inst)
    _center_sum, pairs = _reflection_pairs(values)
    selected = {value for pair in pairs[::2] for value in pair}
    return "".join("A" if value in selected else "B" for value in values)


def canonical_key(inst):
    """Canonicalize input order, integral affine maps, and reflection."""
    decoded = _decode_instance(inst)
    if decoded is None:
        raise ValueError("malformed instance")
    degree, side_size, values = decoded
    minimum = min(values)
    differences = [value - minimum for value in values]
    scale = math.gcd(*differences)
    if scale <= 0:
        raise ValueError("degenerate affine scale")
    normalized = sorted(value // scale for value in differences)
    maximum = normalized[-1]
    reflected = sorted(maximum - value for value in normalized)
    canonical = min(normalized, reflected)
    payload = json.dumps(
        {"degree": degree, "side_size": side_size, "values": canonical},
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def escalate(params):
    """Increase two numeric dials while keeping the 64-symbol witness fixed."""
    if not isinstance(params, dict):
        raise ValueError("params must be a dict")
    n = params.get("n")
    dimension = params.get("dimension", 6)
    scale_bits = params.get("scale_bits")
    if not _valid_parameters(n, dimension, scale_bits):
        raise ValueError("malformed parameters")
    if dimension < 6:
        return {
            "n": max(80, n + 8),
            "dimension": 6,
            "scale_bits": max(80, scale_bits + 8),
        }
    if n == 1024 and scale_bits == 1024:
        return None
    return {
        "n": min(1024, n * 2),
        "dimension": dimension,
        "scale_bits": min(1024, scale_bits * 2),
    }


def _transform_instance(inst, multiplier, translation, permutation=None):
    decoded = _decode_instance(inst)
    if (
        decoded is None
        or not _is_int(multiplier)
        or multiplier == 0
        or not _is_int(translation)
    ):
        raise ValueError("bad transformation")
    _degree, _side_size, values = decoded
    transformed = [multiplier * value + translation for value in values]
    coloring = inst["answer"]
    if min(transformed) < 0:
        raise ValueError("transformation left the non-negative regime")
    if permutation is not None:
        if sorted(permutation) != list(range(len(values))):
            raise ValueError("bad permutation")
        transformed = [transformed[index] for index in permutation]
        coloring = "".join(coloring[index] for index in permutation)
    return {
        "degree": inst["degree"],
        "side_size": inst["side_size"],
        "values": transformed,
        "n_bits": inst.get("n_bits"),
        "scale_bits": inst.get("scale_bits"),
        "answer": coloring,
    }


def _answer_atom_count(answer):
    if isinstance(answer, dict):
        return sum(_answer_atom_count(value) for value in answer.values())
    if isinstance(answer, (list, tuple)):
        return sum(_answer_atom_count(value) for value in answer)
    if isinstance(answer, str) and answer and set(answer) <= {"A", "B"}:
        return len(answer)
    return 1


def selftest():
    """Run correctness, resistance, scaling, canonicalization, and G9 gates."""
    report = {}
    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 271828):
            inst = make_instance(seed=seed, **params)
            g1_attempts += 1
            ok, reason = verify(inst, inst["answer"])
            json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            if not ok or not json_ok:
                g1_failures.append(
                    {"preset": preset, "seed": seed, "reason": reason, "json": json_ok}
                )
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=424242, **shipping)
    answer = inst["answer"]
    center_sum, pairs = _reflection_pairs(inst["values"])
    color_of = dict(zip(inst["values"], answer))
    chosen_pairs = [pair for pair in pairs if color_of[pair[0]] == "A"]
    unchosen_pairs = [pair for pair in pairs if color_of[pair[0]] == "B"]

    one_value_swap = list(answer)
    first_a = next(index for index, symbol in enumerate(answer) if symbol == "A")
    first_b = next(
        index
        for index, symbol in enumerate(answer)
        if symbol == "B"
        and inst["values"][index] != center_sum - inst["values"][first_a]
    )
    one_value_swap[first_a], one_value_swap[first_b] = (
        one_value_swap[first_b],
        one_value_swap[first_a],
    )

    pair_swap = list(answer)
    chosen_values = set(chosen_pairs[0])
    unchosen_values = set(unchosen_pairs[0])
    for index, value in enumerate(inst["values"]):
        if value in chosen_values:
            pair_swap[index] = "B"
        elif value in unchosen_values:
            pair_swap[index] = "A"
    corruptions = {
        "drop": answer[:-1],
        "swap": "".join(one_value_swap),
        "duplicate": answer + answer[0],
        "empty": "",
        "out_of_range": "X" + answer[1:],
        "whole_pair_near_miss": "".join(pair_swap),
    }
    cases = {}
    core_reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
        if name != "whole_pair_near_miss":
            core_reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": (
            all(case["rejected"] for case in cases.values())
            and len(set(core_reasons)) == len(core_reasons)
        ),
        "cases": cases,
        "distinct_core_reasons": len(set(core_reasons)),
    }

    model_style = (
        "I checked reflection closure and all exact moments. My witness is:\n"
        "<answer>\n```\n" + answer + "\n```\n</answer>\n"
        "The complement is the other displayed half."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(8675309)
    guess_total = 200000
    guess_hits = 0
    guess_started = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        assert len(candidate) == len(inst["values"])
        assert candidate.count("A") == candidate.count("B") == inst["side_size"]
        candidate_colors = dict(zip(inst["values"], candidate))
        assert all(
            candidate_colors[value] == candidate_colors[center_sum - value]
            for value in inst["values"]
        )
        guess_hits += int(verify(inst, candidate)[0])
    guess_elapsed = time.perf_counter() - guess_started
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "search_space": search_space(inst),
        "sampling_prior": (
            "uniform over all choices of 16 of the 32 reflection pairs; every "
            "candidate has the stated size, closure, and equal first moment"
        ),
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attack_counts = {
        "outlier_extreme_pair_widths": 0,
        "greedy_fourth_moment_balance": 0,
        "random_restart_256_pair_halves": 0,
        "by_hand_sorted_pair_alternation": 0,
    }
    attack_times = {name: 0.0 for name in attack_counts}
    reference_operations = []
    reference_times = []
    reference_counts = []
    reference_successes = 0
    compact_operations = []
    compact_successes = 0
    attempts = 8
    for trial in range(attempts):
        trial_inst = make_instance(seed=10000 + trial, **shipping)
        for name, function in (
            ("outlier_extreme_pair_widths", _outlier_pair_widths),
            ("greedy_fourth_moment_balance", _greedy_fourth_moment),
            ("by_hand_sorted_pair_alternation", _sorted_pair_alternation),
        ):
            started = time.perf_counter()
            candidate = function(trial_inst)
            attack_times[name] += time.perf_counter() - started
            attack_counts[name] += int(verify(trial_inst, candidate)[0])

        started = time.perf_counter()
        restart_rng = random.Random(20000 + trial)
        restart_solved = False
        for _ in range(256):
            if verify(trial_inst, random_candidate(trial_inst, restart_rng))[0]:
                restart_solved = True
                break
        attack_times["random_restart_256_pair_halves"] += time.perf_counter() - started
        attack_counts["random_restart_256_pair_halves"] += int(restart_solved)

        reference, reference_stats = _mitm_reference(trial_inst)
        reference_ok = reference is not None and verify(trial_inst, reference)[0]
        reference_successes += int(reference_ok)
        reference_operations.append(reference_stats["operations"])
        reference_times.append(reference_stats["wall_clock_sec"])
        reference_counts.append(reference_stats["valid_count"])

        compact, compact_stats = _compact_cube_recover(trial_inst)
        compact_ok = compact is not None and verify(trial_inst, compact)[0]
        compact_successes += int(compact_ok)
        compact_operations.append(compact_stats["operations"])

    attacks = {
        name: {
            "successes": attack_counts[name],
            "attempts": attempts,
            "wall_clock_sec": round(attack_times[name], 6),
        }
        for name in attack_counts
    }
    panel_pass = all(entry["successes"] == 0 for entry in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": (
            panel_pass
            and reference_successes == attempts
            and compact_successes == attempts
        ),
        "attacks": attacks,
        "reference_algorithm": {
            "name": (
                "symmetry-aware meet-in-the-middle on reflection-pair "
                "cardinality and centered even moments"
            ),
            "complexity": (
                "O(degree * 2^(P/2)) exact time and O(2^(P/2)) memory "
                "for P reflection pairs"
            ),
            "wall_clock_sec": round(max(reference_times), 6),
            "mean_wall_clock_sec": round(sum(reference_times) / len(reference_times), 6),
            "operations": max(reference_operations),
            "states": 2 ** (inst["side_size"] // 2),
            "solves": f"{reference_successes}/{attempts}, as expected",
        },
        "compact_route": {
            "name": "translation removal and Boolean-cube reconstruction",
            "max_operations": max(compact_operations),
            "solves": f"{compact_successes}/{attempts}",
        },
    }

    demo_inst = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    exact_shipping_count = reference_counts[0]
    exact_shipping_density = exact_shipping_count / search_space(inst)
    report["G5_density_and_baseline_cost"] = {
        "pass": (
            guess_fraction < 1e-6
            and demo_count is not None
            and len(set(reference_counts)) == 1
            and exact_shipping_density < 1e-6
            and reference_successes == attempts
            and max(compact_operations) <= 300
        ),
        "shipping_exact_solution_count": exact_shipping_count,
        "shipping_count_seed": 10000,
        "shipping_solution_density": exact_shipping_density,
        "shipping_candidate_space": search_space(inst),
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "demo_exact_solution_count": demo_count,
        "baseline_name": (
            "symmetry-aware meet-in-the-middle on reflection-pair "
            "cardinality and centered even moments"
        ),
        "baseline_wall_clock_sec": round(max(reference_times), 6),
        "baseline_operation_count": max(reference_operations),
        "baseline_states": 2 ** (inst["side_size"] // 2),
        "random_restart_panel_wall_clock_sec": round(
            attack_times["random_restart_256_pair_halves"], 6
        ),
        "random_restart_panel_iterations": 256 * attempts,
        "reference_wall_clock_sec": round(max(reference_times), 6),
        "reference_operation_count": max(reference_operations),
        "compact_route_max_operations": max(compact_operations),
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled_started = time.perf_counter()
    doubled = make_instance(seed=31337, **doubled_params)
    doubled_build = time.perf_counter() - doubled_started
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_params["n"] > shipping["n"],
        "shipping_n": shipping["n"],
        "doubled_n": doubled_params["n"],
        "answer_elements_unchanged": len(doubled["answer"]) == len(inst["answer"]),
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_reason,
    }

    invariance_total = invariance_passed = 0
    carried_total = carried_passed = 0
    for seed in range(20):
        base = make_instance(seed=30000 + seed, **shipping)
        base_key = canonical_key(base)
        rng = random.Random(40000 + seed)
        permutation = list(range(len(base["values"])))
        rng.shuffle(permutation)
        positive_u = rng.randrange(2, 100)
        positive_t = rng.randrange(0, 100000)
        reflection_t = positive_u * max(base["values"]) + rng.randrange(0, 100000)
        transformed = [
            _transform_instance(base, 1, 0, permutation),
            _transform_instance(base, positive_u, positive_t),
            _transform_instance(base, positive_u, positive_t, permutation),
            _transform_instance(base, -positive_u, reflection_t),
            _transform_instance(base, -positive_u, reflection_t, permutation),
        ]
        for variant in transformed:
            invariance_total += 1
            carried_total += 1
            invariance_passed += int(canonical_key(variant) == base_key)
            carried_passed += int(verify(variant, variant["answer"])[0])

    unrelated_keys = {
        canonical_key(make_instance(seed=50000 + seed, **shipping))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": (
            invariance_passed == invariance_total
            and carried_passed == carried_total
            and len(unrelated_keys) == 20
        ),
        "invariance_checks_passed": invariance_passed,
        "invariance_checks_total": invariance_total,
        "carried_certificate_checks_passed": carried_passed,
        "carried_certificate_checks_total": carried_total,
        "unrelated_distinct": len(unrelated_keys),
        "unrelated_total": 20,
        "symmetries_tested": [
            "input permutation",
            "positive integral affine map",
            "global reflection",
            "each affine map composed with input permutation",
        ],
    }

    answer_blob = json.dumps(inst["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atom_count(inst["answer"])
    intended_ops = max(compact_operations)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS.get("hinted_verdict"),
        "diagnostic_complete": all(
            arms[name]["attempts"] > 0 for name in ("bare", "hinted", "placebo")
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "within_caps": within_caps,
    }

    gate_values = [
        value
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    ]
    report["all_passed"] = all(value.get("pass") for value in gate_values)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=False))
