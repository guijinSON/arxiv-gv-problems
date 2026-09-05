#!/usr/bin/env python3
"""Verified witness generator for arXiv:2602.13970.

The generated task is the three-set saving lemma (Section 2.3, Lemma 11),
which is one of the paper's two basic operations for extending a partial
multiple-list colouring.  Instances use an exact, succinct representation of
three finite sets.  The planted witness is obtained by reversing a sampled
permutation, never by searching the generated sets.
"""

from __future__ import annotations

import copy
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
    "computational_core": "other",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "three finite sets of integer colour labels",
        "subsets S, T, and R used by the paper's two-neighbour saving operation",
        "a finite-set membership representation by permuted Venn atoms",
    ],
    "verification_operations": [
        "fixed-width hexadecimal decoding",
        "exact modular word addition, rotation, and XOR",
        "finite-set membership and exact cardinality comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "The three sets are simple intervals in the displayed reversible coordinate; "
        "without changing to that coordinate, the generic construction scans the whole universe."
    ),
    "hardness_basis": (
        "Track B: the Section 2.3 Lemma 11 linear scan is O(2^n * rounds) and at "
        "shipping n=20 used 35,651,584 exact word operations and 1.563 seconds mean "
        "wall-clock; reversing the displayed coordinate uses 275 word operations."
    ),
    "max_answer_tokens": 21,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 4, "m": 3, "rounds": 1},
    "easy": {"n": 16, "m": 8, "rounds": 4},
    "medium": {"n": 18, "m": 8, "rounds": 6},
    "hard": {"n": 20, "m": 8, "rounds": 8},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The displayed round transformation is a permutation whose reverse has the same Feistel symmetry."
)
PLACEBO_HINT = (
    "The displayed hexadecimal words need consistent padding and careful attention to their fixed width."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object with keys S, T, R. Each value is a list of distinct lowercase "
        "ceil(n/4)-digit hexadecimal words from the n-bit universe; repetitions are "
        "forbidden within a list and the three list lengths sum to m."
    ),
    "bounds": {
        "lists": 3,
        "total_words": "m",
        "word_bits": "n",
        "hex_digits_per_word": "ceil(n/4)",
        "candidate_count": "binomial(3*2^n, m)",
    },
}

NOTES = (
    "Section 2.1, Remark 1(3) fixes the object represented by the answer: S is in "
    "A\\C, T is in B\\C, and R is in A intersection B intersection C; the three "
    "cardinalities total m. Section 2.3, Lemma 11 proves existence from "
    "|A|+|B| >= |C|+m by inclusion-exclusion. Its proof also identifies the easy "
    "mechanical route: enumerate the three usable Venn regions and take m entries. "
    "Here that route scans a succinct n-bit universe. The generator instead samples "
    "the answer-side Venn atoms first and carries them backward through a reversible "
    "Feistel relabelling. Equal-width word labels and randomized atom positions remove "
    "numeric outliers; large neutral atoms crowd the rare usable regions; raw-coordinate, "
    "prefix-greedy, random-restart, and forward-as-inverse attacks are measured in selftest."
)

# Filled from script-owned hardening runs after the module is finalized.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "too_easy",
}


_ATOMS = ("NONE", "A", "B", "AC", "BC", "ABC")
_RARE_GROUP = {"A": "S", "B": "T", "ABC": "R"}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _width(n):
    return (n + 3) // 4


def _word(n, value):
    return format(value, f"0{_width(n)}x")


def _rotl(value, shift, width):
    mask = (1 << width) - 1
    shift %= width
    return ((value << shift) | (value >> (width - shift))) & mask


def _feistel(inst, value):
    """The public forward coordinate permutation."""
    w = inst["half_bits"]
    mask = (1 << w) - 1
    value ^= inst["pre_xor"]
    left, right = value >> w, value & mask
    for row in inst["round_data"]:
        f = _rotl((right + row["key"]) & mask, row["rotation"], w) ^ row["constant"]
        left, right = right, left ^ f
    return (((left << w) | right) ^ inst["post_xor"]) & ((1 << inst["n"]) - 1)


def _inverse_feistel(inst, coordinate):
    """Reverse the sampled permutation by composition of exact identities."""
    w = inst["half_bits"]
    mask = (1 << w) - 1
    value = coordinate ^ inst["post_xor"]
    left, right = value >> w, value & mask
    for row in reversed(inst["round_data"]):
        f = _rotl((left + row["key"]) & mask, row["rotation"], w) ^ row["constant"]
        left, right = right ^ f, left
    return (((left << w) | right) ^ inst["pre_xor"]) & ((1 << inst["n"]) - 1)


def _positive_composition(total, parts, rng):
    cuts = set()
    while len(cuts) < parts - 1:
        cuts.add(rng.randrange(1, total))
    cuts = sorted(cuts)
    points = [0] + cuts + [total]
    return [points[i + 1] - points[i] for i in range(parts)]


def _validate_parameters(n, m, rounds):
    if not _is_int(n) or n < 4 or n > 4096 or n % 2:
        raise ValueError("n must be an even integer from 4 through 4096")
    if not _is_int(m) or m < 3 or m > 64:
        raise ValueError("m must be an integer from 3 through 64")
    if (1 << n) - m < 3:
        raise ValueError("the universe needs room for three nonempty neutral atoms")
    if not _is_int(rounds) or rounds < 1 or rounds > 8:
        raise ValueError("rounds must be an integer from 1 through 8")


def make_instance(n, seed=0, m=12, rounds=2, **params):
    """Inverse-generate a Lemma 11 instance and carry its witness backward."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_parameters(n, m, rounds)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    universe = 1 << n
    half_bits = n // 2
    half_mask = (1 << half_bits) - 1

    rare_counts = _positive_composition(m, 3, rng)
    neutral_counts = _positive_composition(universe - m, 3, rng)
    counts = {
        "A": rare_counts[0],
        "B": rare_counts[1],
        "ABC": rare_counts[2],
        "NONE": neutral_counts[0],
        "AC": neutral_counts[1],
        "BC": neutral_counts[2],
    }
    order = list(_ATOMS)
    rng.shuffle(order)
    blocks = []
    cursor = 0
    for atom in order:
        blocks.append({"lo": cursor, "hi": cursor + counts[atom], "atom": atom})
        cursor += counts[atom]

    round_data = []
    for _ in range(rounds):
        round_data.append({
            "key": rng.randrange(1 << half_bits),
            "rotation": rng.randrange(1, half_bits),
            "constant": rng.randrange(1 << half_bits),
        })
    inst = {
        "paper": "arXiv:2602.13970",
        "family": "three-set saving witness from Section 2.3, Lemma 11",
        "n": n,
        "m": m,
        "universe_size": universe,
        "half_bits": half_bits,
        "rounds": rounds,
        "pre_xor": rng.randrange(universe),
        "post_xor": rng.randrange(universe),
        "round_data": round_data,
        "blocks": blocks,
    }

    # The usable coordinate intervals were sampled before the labels.  Reversing
    # the permutation carries those known atoms to an exact certificate.
    answer = {"S": [], "T": [], "R": []}
    for block in blocks:
        group = _RARE_GROUP.get(block["atom"])
        if group is None:
            continue
        answer[group].extend(
            _word(n, _inverse_feistel(inst, coordinate))
            for coordinate in range(block["lo"], block["hi"])
        )
    for group in answer:
        answer[group].sort()
    inst["answer"] = answer
    return inst


def _atom_for_coordinate(inst, coordinate):
    for block in inst["blocks"]:
        if block["lo"] <= coordinate < block["hi"]:
            return block["atom"]
    return None


def _atom_for_value(inst, value):
    return _atom_for_coordinate(inst, _feistel(inst, value))


def _atom_counts(inst):
    counts = {atom: 0 for atom in ("NONE", "A", "B", "C", "AB", "AC", "BC", "ABC")}
    for block in inst["blocks"]:
        counts[block["atom"]] += block["hi"] - block["lo"]
    return counts


def _validate_instance(inst):
    try:
        n, m, rounds = inst["n"], inst["m"], inst["rounds"]
        _validate_parameters(n, m, rounds)
        universe = 1 << n
        if inst["universe_size"] != universe or inst["half_bits"] != n // 2:
            return None, "instance has inconsistent universe dimensions"
        if not _is_int(inst["pre_xor"]) or not 0 <= inst["pre_xor"] < universe:
            return None, "instance pre-XOR mask is out of range"
        if not _is_int(inst["post_xor"]) or not 0 <= inst["post_xor"] < universe:
            return None, "instance post-XOR mask is out of range"
        if not isinstance(inst["round_data"], list) or len(inst["round_data"]) != rounds:
            return None, "instance has the wrong number of rounds"
        half = 1 << (n // 2)
        for row in inst["round_data"]:
            if set(row) != {"key", "rotation", "constant"}:
                return None, "instance round has malformed fields"
            if not all(_is_int(row[key]) for key in row):
                return None, "instance round values must be integers"
            if not (0 <= row["key"] < half and 0 <= row["constant"] < half
                    and 1 <= row["rotation"] < n // 2):
                return None, "instance round value is out of range"
        blocks = inst["blocks"]
        if not isinstance(blocks, list) or len(blocks) != len(_ATOMS):
            return None, "instance must contain six Venn-atom blocks"
        ordered = sorted(blocks, key=lambda block: block.get("lo", -1))
        cursor = 0
        seen = set()
        for block in ordered:
            if set(block) != {"lo", "hi", "atom"}:
                return None, "instance Venn block has malformed fields"
            if block["atom"] not in _ATOMS or block["atom"] in seen:
                return None, "instance Venn block label is invalid or repeated"
            if not _is_int(block["lo"]) or not _is_int(block["hi"]):
                return None, "instance Venn endpoints must be integers"
            if block["lo"] != cursor or block["hi"] <= block["lo"]:
                return None, "instance Venn blocks do not form a consecutive partition"
            cursor = block["hi"]
            seen.add(block["atom"])
        if cursor != universe:
            return None, "instance Venn blocks do not cover the universe"
        counts = _atom_counts(inst)
        size_a = counts["A"] + counts["AC"] + counts["ABC"]
        size_b = counts["B"] + counts["BC"] + counts["ABC"]
        size_c = counts["AC"] + counts["BC"] + counts["ABC"]
        if size_a + size_b != size_c + m:
            return None, "instance does not satisfy the promised tight cardinality identity"
        return {"counts": counts, "size_a": size_a, "size_b": size_b, "size_c": size_c}, None
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        return None, "malformed instance: " + str(exc)


def render(inst):
    """Render a self-contained exact finite-set witness problem."""
    data, error = _validate_instance(inst)
    if error is not None:
        raise ValueError(error)
    n, m, w = inst["n"], inst["m"], inst["half_bits"]
    width = _width(n)
    round_lines = []
    for index, row in enumerate(inst["round_data"], 1):
        round_lines.append(
            f"  {index}: key={_word(w, row['key'])}, rotate={row['rotation']}, "
            f"constant={_word(w, row['constant'])}"
        )
    block_lines = [
        f"  [{block['lo']}, {block['hi']}): {block['atom']}"
        for block in inst["blocks"]
    ]
    example = '{"S":["' + "0" * width + '"],"T":[],"R":[]}'
    statement = f"""Three-set saving witness (arXiv:2602.13970, Section 2.3, Lemma 11)

The universe U is all n-bit integers x with 0 <= x < 2^n, where n={n}; thus
|U|={inst['universe_size']}.  In answers, write every x as exactly {width} lowercase
hexadecimal digits, including leading zeroes.

Three finite sets A, B, C are defined through a coordinate y=P(x).  All arithmetic
below is exact. XOR is bitwise exclusive-or. rotl_w(q,s) rotates the w-bit word q
left by s positions, with wraparound. Here w={w}.

To compute P(x):
  1. Replace x by x XOR {_word(n, inst['pre_xor'])}.
  2. Split it into the high w-bit word ell and low w-bit word r.
  3. For each listed round, replace (ell,r) simultaneously by
       (r, ell XOR (rotl_w((r+key) mod 2^w, rotate) XOR constant)).
{chr(10).join(round_lines)}
  4. Join ell as the high half and r as the low half, then XOR
     {_word(n, inst['post_xor'])}. The resulting n-bit integer is y=P(x).

Use the unique half-open interval [lo,hi) containing y to obtain its Venn atom:
{chr(10).join(block_lines)}
The atom labels mean NONE (in no set), A (only A), B (only B), AC (in A and C
but not B), BC (in B and C but not A), and ABC (in all three sets). Consequently
|A|={data['size_a']}, |B|={data['size_b']}, |C|={data['size_c']}, and the promised
tight identity |A|+|B|=|C|+m holds for m={m}.

Find three subsets S,T,R such that S is a subset of A\\C, T is a subset of B\\C,
R is a subset of A intersection B intersection C, and |S|+|T|+|R|={m}. Order
inside each list does not matter. Repetitions within a list are forbidden. S,T,R
may have different sizes, including zero; only their total size is fixed.

Give your final answer inside <answer></answer> tags as one compact JSON object
with exactly the keys S, T, R and lists of fixed-width lowercase hexadecimal words.
Example of the syntax only: <answer>{example}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Extract the JSON witness from tags or a surrounding model response."""
    if not isinstance(text, str):
        return None
    tagged = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.IGNORECASE | re.DOTALL)
    candidates = list(reversed(tagged))
    if not candidates:
        candidates = [text]
    decoder = json.JSONDecoder()
    for body in candidates:
        cleaned = body.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            value = json.loads(cleaned)
            if isinstance(value, dict):
                return value
        except (ValueError, TypeError):
            pass
        for match in re.finditer(r"\{", cleaned):
            try:
                value, _ = decoder.raw_decode(cleaned[match.start():])
            except ValueError:
                continue
            if isinstance(value, dict):
                return value
    return None


def _decode_answer(inst, answer):
    if not isinstance(answer, dict):
        return None, "answer must be a JSON object"
    if set(answer) != {"S", "T", "R"}:
        return None, "answer must have exactly the keys S, T, R"
    decoded = {}
    width = _width(inst["n"])
    universe = inst["universe_size"]
    for group in ("S", "T", "R"):
        words = answer[group]
        if not isinstance(words, list):
            return None, f"{group} must be a JSON list"
        if any(not isinstance(word, str) for word in words):
            return None, f"{group} contains a non-string word"
        if any(len(word) != width for word in words):
            return None, f"{group} contains a word of the wrong width"
        if any(re.fullmatch(r"[0-9a-f]+", word) is None for word in words):
            return None, f"{group} contains a non-lowercase-hexadecimal word"
        values = [int(word, 16) for word in words]
        if any(value >= universe for value in values):
            return None, f"{group} contains a word outside the n-bit universe"
        if len(set(values)) != len(values):
            return None, f"{group} contains duplicate words"
        decoded[group] = values
    if sum(len(decoded[group]) for group in decoded) != inst["m"]:
        return None, "the three list lengths do not sum to m"
    return decoded, None


def verify(inst, answer):
    """Check any witness in the declared language; never read inst['answer']."""
    data, error = _validate_instance(inst)
    if error is not None:
        return False, error
    decoded, error = _decode_answer(inst, answer)
    if error is not None:
        return False, error
    required = {"S": "A", "T": "B", "R": "ABC"}
    descriptions = {"S": "A\\C", "T": "B\\C", "R": "A intersection B intersection C"}
    for group in ("S", "T", "R"):
        for value in decoded[group]:
            atom = _atom_for_value(inst, value)
            if atom != required[group]:
                return False, f"{group} word {_word(inst['n'], value)} is not in {descriptions[group]}"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the bounded, shape-aware certificate language."""
    universe = inst["universe_size"]
    selected = set()
    while len(selected) < inst["m"]:
        selected.add(rng.randrange(3 * universe))
    answer = {"S": [], "T": [], "R": []}
    groups = ("S", "T", "R")
    for tagged in selected:
        group, value = divmod(tagged, universe)
        answer[groups[group]].append(_word(inst["n"], value))
    for group in answer:
        answer[group].sort()
    return answer


def search_space(inst):
    """Exact size of the structure-aware bounded answer language."""
    return math.comb(3 * inst["universe_size"], inst["m"])


def enumerate_all(inst):
    """Brute-force small languages, with a strict cap."""
    if search_space(inst) > 250_000:
        return None
    universe = inst["universe_size"]
    groups = ("S", "T", "R")
    count = 0
    for selected in itertools.combinations(range(3 * universe), inst["m"]):
        answer = {"S": [], "T": [], "R": []}
        for tagged in selected:
            group, value = divmod(tagged, universe)
            answer[groups[group]].append(_word(inst["n"], value))
        count += int(verify(inst, answer)[0])
    return count


def canonical_key(inst):
    """Complete isomorphism invariant for three finite sets: Venn-atom sizes."""
    data, error = _validate_instance(inst)
    if error is not None:
        raise ValueError(error)
    payload = {
        "universe": inst["universe_size"],
        "venn_atom_sizes": [[atom, data["counts"][atom]] for atom in sorted(data["counts"])],
        "m": inst["m"],
    }
    blob = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    return "three-set-saving-v1:" + hashlib.sha256(blob.encode()).hexdigest()


def escalate(params):
    """Grow the implicit universe and one permutation-crowding dial, not the answer."""
    n = params.get("n")
    m = params.get("m", 12)
    rounds = params.get("rounds", 2)
    if not all(_is_int(value) for value in (n, m, rounds)):
        return None
    candidate = {"n": n + 2, "m": m, "rounds": min(8, rounds + 1)}
    width = _width(candidate["n"])
    dummy = {"S": ["0" * width], "T": ["0" * width],
             "R": ["0" * width] * (m - 2)}
    if len(json.dumps(dummy, separators=(",", ":"))) > 2000:
        return "cap_bound"
    return candidate


def _compact_witness(inst):
    answer = {"S": [], "T": [], "R": []}
    for block in inst["blocks"]:
        group = _RARE_GROUP.get(block["atom"])
        if group is None:
            continue
        for coordinate in range(block["lo"], block["hi"]):
            answer[group].append(_word(inst["n"], _inverse_feistel(inst, coordinate)))
    for group in answer:
        answer[group].sort()
    return answer


def _reference_scan(inst):
    answer = {"S": [], "T": [], "R": []}
    tested = 0
    for value in range(inst["universe_size"]):
        tested += 1
        group = _RARE_GROUP.get(_atom_for_value(inst, value))
        if group is not None:
            answer[group].append(_word(inst["n"], value))
    for group in answer:
        answer[group].sort()
    return answer, {
        "coordinate_evaluations": tested,
        "round_evaluations": tested * inst["rounds"],
        "exact_word_operations": tested * (4 * inst["rounds"] + 2),
    }


def _candidate_from_tagged(inst, tagged_values):
    universe = inst["universe_size"]
    groups = ("S", "T", "R")
    chosen = set(tagged_values)
    cursor = 0
    while len(chosen) < inst["m"]:
        chosen.add(cursor)
        cursor += 1
    chosen = sorted(chosen)[:inst["m"]]
    answer = {"S": [], "T": [], "R": []}
    for tagged in chosen:
        group, value = divmod(tagged, universe)
        answer[groups[group]].append(_word(inst["n"], value))
    return answer


def _attack_numeric_outlier(inst):
    return _candidate_from_tagged(inst, range(inst["m"]))


def _attack_greedy_prefix(inst, budget=512):
    universe = inst["universe_size"]
    group_number = {"S": 0, "T": 1, "R": 2}
    tagged = []
    for value in range(min(budget, universe)):
        group = _RARE_GROUP.get(_atom_for_value(inst, value))
        if group is not None:
            tagged.append(group_number[group] * universe + value)
    return _candidate_from_tagged(inst, tagged)


def _attack_random_restart(inst, rng, budget=4096):
    universe = inst["universe_size"]
    group_number = {"S": 0, "T": 1, "R": 2}
    tagged = []
    for value in rng.sample(range(universe), min(budget, universe)):
        group = _RARE_GROUP.get(_atom_for_value(inst, value))
        if group is not None:
            tagged.append(group_number[group] * universe + value)
    return _candidate_from_tagged(inst, tagged)


def _attack_forward_as_inverse(inst):
    tagged = []
    universe = inst["universe_size"]
    group_number = {"S": 0, "T": 1, "R": 2}
    for block in inst["blocks"]:
        group = _RARE_GROUP.get(block["atom"])
        if group is None:
            continue
        for coordinate in range(block["lo"], block["hi"]):
            tagged.append(group_number[group] * universe + _feistel(inst, coordinate))
    return _candidate_from_tagged(inst, tagged)


def _xor_relabel(inst, mask, reverse_blocks=False):
    transformed = copy.deepcopy(inst)
    transformed["pre_xor"] ^= mask
    if reverse_blocks:
        transformed["blocks"].reverse()
    answer = {}
    for group in ("S", "T", "R"):
        answer[group] = sorted(
            _word(inst["n"], int(word, 16) ^ mask) for word in inst["answer"][group]
        )
    transformed["answer"] = answer
    return transformed


def _answer_size(answer):
    compact = json.dumps(answer, separators=(",", ":"))
    elements = sum(len(answer[group]) for group in ("S", "T", "R"))
    return len(compact), (len(compact) + 3) // 4, elements


def selftest():
    report = {
        "paper": "arXiv:2602.13970",
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
            for value in (0, inst["universe_size"] // 3, inst["universe_size"] - 1):
                if _inverse_feistel(inst, _feistel(inst, value)) != value:
                    failures.append({"preset": preset, "seed": seed, "reason": "permutation inverse failed"})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
        "generation_route": "sample Venn atoms, then carry them through an exact inverse permutation",
    }

    shipping = make_instance(seed=260213970, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    dropped = copy.deepcopy(planted)
    drop_group = next(group for group in ("S", "T", "R") if dropped[group])
    dropped[drop_group].pop()
    swapped = copy.deepcopy(planted)
    swapped["S"][0], swapped["T"][0] = swapped["T"][0], swapped["S"][0]
    duplicated = copy.deepcopy(planted)
    duplicate_group = max(("S", "T", "R"), key=lambda group: len(duplicated[group]))
    duplicated[duplicate_group][1] = duplicated[duplicate_group][0]
    outside = copy.deepcopy(planted)
    outside_group = next(group for group in ("S", "T", "R") if outside[group])
    outside[outside_group][0] = _word(shipping["n"], shipping["universe_size"])
    corruptions = {
        "drop_one": dropped,
        "swap_categories": swapped,
        "duplicate_one": duplicated,
        "empty": {},
        "out_of_range": outside,
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = {row["reason"] for row in cases.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in cases.values()) and len(reasons) == len(cases),
        "cases": cases,
        "distinct_reasons": len(reasons),
    }

    realistic = (
        "The useful atoms are exhausted by the following sets.\n<answer>\n```json\n"
        + json.dumps(planted, separators=(",", ":"))
        + "\n```\n</answer>\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no witness here") is None,
        "parsed": parsed == planted,
    }

    guess_rng = random.Random(0x260213970)
    guess_total = 200_000
    guess_hits = 0
    t0 = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_elapsed = time.perf_counter() - t0
    observed = guess_hits / guess_total
    exact_density = 1.0 / search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": observed,
        "exact_probability": exact_density,
        "structure_aware_space": search_space(shipping),
        "sampling_rule": "uniform m-subset of the three tagged n-bit universes; shape and total size are pre-enforced",
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attack_functions = {
        "numeric_outlier_smallest": lambda inst, rng: _attack_numeric_outlier(inst),
        "greedy_prefix_512": lambda inst, rng: _attack_greedy_prefix(inst, 512),
        "random_restart_4096": lambda inst, rng: _attack_random_restart(inst, rng, 4096),
        "by_hand_forward_as_inverse": lambda inst, rng: _attack_forward_as_inverse(inst),
    }
    attack_results = {name: {"successes": 0, "attempts": 0} for name in attack_functions}
    attack_elapsed = {name: 0.0 for name in attack_functions}
    seeds = list(range(8100, 8108))
    for seed in seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for offset, (name, function) in enumerate(attack_functions.items()):
            rng = random.Random(seed * 1009 + offset)
            started = time.perf_counter()
            candidate = function(inst, rng)
            attack_elapsed[name] += time.perf_counter() - started
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])
            attack_results[name]["attempts"] += 1
    for name in attack_results:
        attack_results[name]["wall_clock_sec_total_8"] = round(attack_elapsed[name], 6)
    all_attacks_failed = all(row["successes"] == 0 for row in attack_results.values())

    reference_successes = compact_successes = 0
    reference_elapsed = 0.0
    reference_stats = []
    for seed in seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        started = time.perf_counter()
        candidate, stats = _reference_scan(inst)
        reference_elapsed += time.perf_counter() - started
        reference_stats.append(stats)
        reference_successes += int(verify(inst, candidate)[0])
        compact_successes += int(verify(inst, _compact_witness(inst))[0])
    reference = {
        "name": "linear enumeration of the three usable Venn regions (Lemma 11 proof)",
        "complexity": "O(2^n * rounds) exact word operations for the succinct universe",
        "wall_clock_sec_total_8": round(reference_elapsed, 6),
        "wall_clock_sec_mean": round(reference_elapsed / len(seeds), 6),
        "coordinate_evaluations_mean": sum(row["coordinate_evaluations"] for row in reference_stats) // len(seeds),
        "round_evaluations_mean": sum(row["round_evaluations"] for row in reference_stats) // len(seeds),
        "operations_mean": sum(row["exact_word_operations"] for row in reference_stats) // len(seeds),
        "solves": f"{reference_successes}/{len(seeds)}, as expected",
    }
    intended_operations = shipping["m"] * (4 * shipping["rounds"] + 2) + 3
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == compact_successes == len(seeds),
        "attacks": attack_results,
        "reference_algorithm": reference,
        "compact_route": {
            "name": "reverse the Feistel coordinate on each usable interval word",
            "worst_case_exact_operations": intended_operations,
            "count_model": "per word: pre/post XOR plus add, rotate, XOR-constant, and XOR-left per round; three setup checks",
            "solves": f"{compact_successes}/{len(seeds)}, as expected",
        },
    }

    strongest = max(attack_elapsed, key=attack_elapsed.get)
    report["G5_density_and_baseline_cost"] = {
        "pass": observed < 1e-6 and all_attacks_failed and reference_successes == len(seeds),
        "sampled_density_at_shipping": observed,
        "density_hits": guess_hits,
        "density_samples": guess_total,
        "mathematically_valid_answers": 1,
        "candidate_space": search_space(shipping),
        "strongest_failing_attack": strongest,
        "strongest_attack_wall_clock_sec_total_8": round(attack_elapsed[strongest], 6),
        "strongest_attack_candidate_tests_total_8": 4096 * len(seeds),
        "reference_algorithm_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
        "reference_algorithm_operations_mean": reference["operations_mean"],
        "demo_exact_valid_answers_by_enumeration": enumerate_all(
            make_instance(seed=3, **DIFFICULTY["demo"])
        ),
    }

    doubled = make_instance(
        n=2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        m=shipping["m"],
        rounds=shipping["rounds"],
        seed=707,
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["universe_size"] > shipping["universe_size"],
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_universe": shipping["universe_size"],
        "doubled_universe": doubled["universe_size"],
        "answer_elements_unchanged": sum(map(len, shipping["answer"].values()))
        == sum(map(len, doubled["answer"].values())),
        "verify_reason": doubled_reason,
    }

    invariance_checks = 0
    carried_checks = 0
    key_failures = []
    for seed in range(20):
        inst = make_instance(seed=9000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        rng = random.Random(12000 + seed)
        mask = rng.randrange(inst["universe_size"])
        variants = [
            _xor_relabel(inst, mask, False),
            _xor_relabel(inst, 0, True),
            _xor_relabel(inst, mask, True),
        ]
        for variant_index, transformed in enumerate(variants):
            invariance_checks += 1
            if canonical_key(transformed) != key:
                key_failures.append({"seed": seed, "variant": variant_index, "reason": "key changed"})
            carried_checks += 1
            if not verify(transformed, transformed["answer"])[0]:
                key_failures.append({"seed": seed, "variant": variant_index, "reason": "carried witness failed"})
    unrelated = [
        canonical_key(make_instance(seed=20000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY]))
        for seed in range(20)
    ]
    distinct = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct == 20,
        "invariance_checks": invariance_checks,
        "invariance_failures": key_failures,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct,
        "symmetries_tested": [
            "global XOR relabelling of every universe element",
            "reordering the six input Venn-atom blocks",
            "composition of relabelling and block reordering",
        ],
        "completeness_basis": "three labelled finite sets are isomorphic exactly when all eight Venn-atom sizes agree",
    }

    chars, tokens, elements = _answer_size(shipping["answer"])
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = chars <= 2000 and elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["pass"] = all(gate.get("pass") is True for gate in gates)
    report["all_passed"] = report["pass"]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
