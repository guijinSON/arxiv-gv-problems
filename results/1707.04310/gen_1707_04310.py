"""Verified constrained-shuffle generator for arXiv:1707.04310.

The paper's CSh[(ab)*] instance is a tuple of words.  This module samples
pointwise-complementary word pairs, shuffles the tuple, and asks for the pair
partition.  Every submitted pair expands to a legal alternating interleaving:
at each aligned position, emit its ``a`` and then its ``b``.  Thus the answer
is known by inverse construction and verification never consults it.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import re
import time


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "tuple of words over the alphabet {a,b}",
        "disjoint union of labeled directed paths",
    ],
    "verification_operations": [
        "path-index range and partition checks",
        "exact symbol-by-symbol complementation",
        "constructive alternating-interleaving check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Project each long path word onto power-of-two positions, where the "
        "resulting short signatures occur in complementary pairs; without "
        "that invariant one must process every symbol of every path."
    ),
    "hardness_basis": (
        "Track B: exact complement hashing solves this generated subclass in "
        "O(nL) time; at shipping n=42 and L=512 it performs 43,029 counted "
        "symbol/hash operations in a measured mean below 0.001 seconds, whereas the "
        "power-of-two signature route uses 273 symbol/look-up operations, below "
        "the no-tool cap but unavailable unless the projection is noticed."
    ),
    "max_answer_tokens": 127,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"]
    + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON list of n/2 two-element lists that partitions the 0-based path "
        "indices. Pair order and the order within a pair are immaterial."
    ),
    "bounds": {
        "number_of_pairs": "n/2",
        "pair_size": 2,
        "index_lower_bound": 0,
        "index_upper_bound": "n-1",
        "indices_form_a_partition": True,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 4, "word_length": 8, "signature_bits": 2},
    "easy": {"n": 22, "word_length": 64, "signature_bits": 5},
    "medium": {"n": 34, "word_length": 256, "signature_bits": 6},
    "hard": {"n": 42, "word_length": 512, "signature_bits": 6},
}
SHIPPING_DIFFICULTY: str = "hard"

STRUCTURAL_HINT: str = (
    "The symbols at 1-based positions 1, 2, 4, 8, 16, and 32 form complement-paired signatures."
)
PLACEBO_HINT: str = (
    "The symbols in every listed path should be tracked with consistent 1-based position numbering."
)

# Updated only from script-owned oracle runs.  The bare hard-preset arm has
# scored evidence; zero attempts on the other arms is explicit and cannot be
# mistaken for model failures.
G9_MEASUREMENTS = {
    "arms": {
        "bare": {"solved": 3, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "pending",
}

NOTES: str = r"""
Section 2 fixes the native objects: CSh[K] is given a tuple of words and asks
whether an interleaving belongs to K; equivalently, its DAG is a disjoint union
of labeled directed paths.  Example 2.1 says that K=(ab)* requires an order
starting with a, ending with b, and alternating throughout.  Theorem 3.6 proves
CSh[(ab)*] NP-hard through the Section 3 shuffle reduction from the unary
3-PARTITION family of Lemma 3.2.  The proof produces a topological-order witness,
and Proposition 2.2 checks such a witness in polynomial time.

Step-0 algorithm question: the NP-hardness theorem does not make this planted
distribution hard.  These instances have an exact O(nL) algorithm: hash every
word and look up its pointwise complement.  At the shipping preset selftest
counts 43,029 symbol/hash operations.  Consequently the module is Track B.
The compact route reads only signature_bits power-of-two positions per word;
those signatures are unique and complementary, so 42*6 symbol reads plus 21
lookups recover the certificate in 273 operations.  The certificate itself is
sampled first; each base word and its complement are then assembled around it.

The easy regimes in the paper also matter.  Theorem 4.3 places monomial target
languages in NL.  Proposition C.2 gives an O(k log n)-space nondeterministic
algorithm when DAG width k (or the number of input strings for CSh) is bounded,
and notes the corresponding task was already known in PTIME.  We do not invoke
either as Track-A evidence: our number of paths grows, and the stronger special
algorithm above is fully disclosed.

All paths have equal length and exactly half a-labels, defeating length and
frequency outliers.  Tuple order is uniformly shuffled, defeating adjacency,
first-compatible, and fixed-order pairing rules.  Uniform perfect-matching
restarts are measured separately.  The successful complement-hash method is
reported as the Track-B reference algorithm, never hidden among failing attacks.
""".strip()


_SWAP = str.maketrans({"a": "b", "b": "a"})


def _signature_positions(bits: int) -> list[int]:
    """Zero-based positions corresponding to 1,2,4,... in the statement."""
    return [(1 << i) - 1 for i in range(bits)]


def _complement(word: str) -> str:
    return word.translate(_SWAP)


def _canonical_pairs(pairs) -> list[list[int]]:
    return sorted([sorted([int(pair[0]), int(pair[1])]) for pair in pairs])


def _validate_params(n: int, word_length: int, signature_bits: int) -> None:
    vals = (n, word_length, signature_bits)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in vals):
        raise TypeError("n, word_length, and signature_bits must be integers")
    if n < 4 or n % 2:
        raise ValueError("n must be an even integer at least 4")
    if signature_bits < 2:
        raise ValueError("signature_bits must be at least 2")
    if n // 2 > 1 << (signature_bits - 1):
        raise ValueError("signature_bits do not provide enough complement classes")
    if word_length < (1 << (signature_bits - 1)) or word_length % 2:
        raise ValueError("word_length must be even and include every signature position")


def _word_with_signature(code: int, bits: int, length: int,
                         rng: random.Random) -> str:
    positions = _signature_positions(bits)
    chars = [None] * length
    for bit, position in enumerate(positions):
        # Low-order code bit is written at the earliest power-of-two position.
        chars[position] = "b" if (code >> bit) & 1 else "a"
    a_used = sum(symbol == "a" for symbol in chars if symbol is not None)
    remaining = [i for i, symbol in enumerate(chars) if symbol is None]
    a_needed = length // 2 - a_used
    if not 0 <= a_needed <= len(remaining):
        raise ValueError("signature cannot be completed to a balanced word")
    a_positions = set(rng.sample(remaining, a_needed))
    for position in remaining:
        chars[position] = "a" if position in a_positions else "b"
    return "".join(chars)


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate complementary paths and retain their pair partition."""
    word_length = params.pop("word_length", 512)
    signature_bits = params.pop("signature_bits", 6)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, word_length, signature_bits)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")

    rng = random.Random(seed)
    pair_count = n // 2
    # Codes below 2^(bits-1) have top bit 0, so no two sampled bases are
    # complements; each generated word therefore has exactly one partner.
    base_codes = rng.sample(range(1 << (signature_bits - 1)), pair_count)
    tagged_words = []
    for pair_id, code in enumerate(base_codes):
        word = _word_with_signature(code, signature_bits, word_length, rng)
        tagged_words.append((word, pair_id))
        tagged_words.append((_complement(word), pair_id))
    rng.shuffle(tagged_words)

    strings = [word for word, _ in tagged_words]
    members: dict[int, list[int]] = {}
    for index, (_, pair_id) in enumerate(tagged_words):
        members.setdefault(pair_id, []).append(index)
    answer = _canonical_pairs(members.values())
    return {
        "family": "constrained shuffle into (ab)*",
        "n": n,
        "word_length": word_length,
        "signature_bits": signature_bits,
        "strings": strings,
        "answer": answer,
    }


def render(inst) -> str:
    rows = []
    for index, word in enumerate(inst["strings"]):
        # Spaces are visual separators and are explicitly excluded from words.
        blocks = " ".join(word[start:start + 64]
                          for start in range(0, len(word), 64))
        rows.append(f"{index}: {blocks}")
    statement = f"""CONSTRAINED SHUFFLE INTO (ab)*

You are given {inst['n']} strings (directed paths) over the two-symbol alphabet
{{a,b}}. Each string has exactly {inst['word_length']} symbols. An interleaving
chooses one not-yet-used symbol at a time while preserving the left-to-right
order inside every string. The target language (ab)* consists of the empty word,
ab, abab, ababab, and so on: it starts with a, alternates, and ends with b.

Find a partition of all {inst['n']} strings into {inst['n'] // 2} pairs such that,
within every pair, the two strings have opposite symbols at every position. Such
a pair certifies an alternating interleaving: at each aligned position take the
a-symbol first and the b-symbol second; concatenate the certified pairs in any
order. Thus the requested partition is a finite witness for this CSh[(ab)*]
instance.

Indices are 0-based from 0 through {inst['n'] - 1}, inclusive. Every index must
occur exactly once. Pair order and order within a pair do not matter. Spaces in
the listing separate 64-symbol display blocks and are not part of a string.
Positions within a string are 1-based when discussed.

Strings (index: word):
{chr(10).join(rows)}

Give your final answer inside <answer></answer> tags as JSON: a list of exactly
{inst['n'] // 2} two-integer lists.
Example format: <answer>[[0,1],[2,3]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    """Parse the final tagged JSON block while tolerating prose and fences."""
    try:
        matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>",
                             str(text), re.I | re.S)
        if not matches:
            return None
        body = matches[-1].strip()
        fence = chr(96) * 3
        if body.startswith(fence) and body.endswith(fence):
            body = re.sub(r"^```[^\n]*\n?", "", body)
            body = re.sub(r"\n?```$", "", body).strip()
        elif body.startswith("~~~") and body.endswith("~~~"):
            body = re.sub(r"^~~~[^\n]*\n?", "", body)
            body = re.sub(r"\n?~~~$", "", body).strip()
        value = json.loads(body)
        if not isinstance(value, list):
            return None
        if any(not isinstance(pair, list) or len(pair) != 2 for pair in value):
            return None
        if any(isinstance(x, bool) or not isinstance(x, int)
               for pair in value for x in pair):
            return None
        return value
    except Exception:
        return None


def verify(inst, answer) -> tuple[bool, str]:
    """Check a path-pair certificate exactly, without reading inst['answer']."""
    n = inst.get("n")
    strings = inst.get("strings")
    if not isinstance(answer, list):
        return False, "answer must be a JSON list of pairs"
    if not answer:
        return False, "answer is empty"
    if len(answer) != n // 2:
        return False, f"expected exactly {n // 2} pairs"
    if any(not isinstance(pair, list) or len(pair) != 2 for pair in answer):
        return False, "every entry must be a two-integer list"
    flat = [value for pair in answer for value in pair]
    if any(isinstance(value, bool) or not isinstance(value, int) for value in flat):
        return False, "every path index must be an integer"
    if any(value < 0 or value >= n for value in flat):
        return False, f"path index outside the inclusive range 0..{n - 1}"
    if len(set(flat)) != len(flat):
        return False, "a path index is repeated"
    if set(flat) != set(range(n)):
        return False, "the pairs do not cover every path index"
    if not isinstance(strings, list) or len(strings) != n:
        return False, "malformed instance string table"
    for left, right in answer:
        a = strings[left]
        b = strings[right]
        if len(a) != len(b) or any(x == y for x, y in zip(a, b)):
            return False, f"paths {left} and {right} are not pointwise complements"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Sample uniformly from all perfect matchings of the stated path set."""
    indices = list(range(inst["n"]))
    rng.shuffle(indices)
    return _canonical_pairs([indices[i:i + 2] for i in range(0, len(indices), 2)])


def search_space(inst) -> int | None:
    """Return (n-1)!!, the number of perfect matchings on n named paths."""
    n = inst["n"]
    total = 1
    for value in range(n - 1, 0, -2):
        total *= value
    return total


def enumerate_all(inst) -> int | None:
    """Brute-force all matchings only when their number is safely tiny."""
    if search_space(inst) > 200_000:
        return None
    n = inst["n"]
    used = [False] * n
    candidate = []
    count = 0

    def visit() -> None:
        nonlocal count
        try:
            first = next(i for i, flag in enumerate(used) if not flag)
        except StopIteration:
            count += int(verify(inst, candidate)[0])
            return
        used[first] = True
        for second in range(first + 1, n):
            if not used[second]:
                used[second] = True
                candidate.append([first, second])
                visit()
                candidate.pop()
                used[second] = False
        used[first] = False

    visit()
    return count


def _reverse_complement_words(strings: list[str]) -> list[str]:
    # Reverse the global schedule and swap a/b: (ab)* is preserved.
    return [_complement(word[::-1]) for word in strings]


def canonical_key(inst) -> str:
    """Exact key modulo input-tuple order and global reverse-complement."""
    words = list(inst["strings"])
    direct = sorted(words)
    reversed_swapped = sorted(_reverse_complement_words(words))
    normal = min(direct, reversed_swapped)
    payload = json.dumps(normal, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params) -> dict | str | None:
    """Grow unread tail data first, keeping the pairing witness fixed-length."""
    harder = {key: value for key, value in params.items() if key != "_preset"}
    length = harder.get("word_length", 512)
    n = harder.get("n", 42)
    bits = harder.get("signature_bits", 6)
    if length < 4096:
        harder["word_length"] = length * 2
        return harder
    candidate_n = n + 4
    needed = max(bits, math.ceil(math.log2(candidate_n // 2)) + 1)
    # The compact signature route costs n*b symbol reads plus n/2 lookups.
    # Do not let an oracle escalation create a level that violates G9(c).
    if candidate_n * needed + candidate_n // 2 <= 300:
        harder["n"] = candidate_n
        harder["signature_bits"] = needed
        return harder
    return "cap_bound"


def _reference_complement_hash(inst) -> tuple[list[list[int]] | None, int]:
    """Domain reference algorithm: hash words and look up exact complements."""
    strings = inst["strings"]
    table = {word: index for index, word in enumerate(strings)}
    unused = set(range(len(strings)))
    pairs = []
    # Count one full scan to hash the input, and a complement construction plus
    # a hash scan for every representative actually looked up.
    operations = len(strings) * inst["word_length"]
    while unused:
        left = min(unused)
        target = _complement(strings[left])
        operations += 2 * inst["word_length"] + 1
        right = table.get(target)
        if right is None or right == left or right not in unused:
            return None, operations
        pairs.append([left, right])
        unused.remove(left)
        unused.remove(right)
    return _canonical_pairs(pairs), operations


def _attack_adjacent_rows(inst):
    return [[i, i + 1] for i in range(0, inst["n"], 2)]


def _attack_frequency_extremes(inst):
    # A standard outlier statistic; all generated paths are exactly balanced.
    order = sorted(range(inst["n"]),
                   key=lambda i: (inst["strings"][i].count("a"), i))
    pairs = [[order[i], order[-1 - i]] for i in range(inst["n"] // 2)]
    return _canonical_pairs(pairs)


def _attack_first_opposite(inst):
    unused = set(range(inst["n"]))
    pairs = []
    while unused:
        left = min(unused)
        unused.remove(left)
        right = next((j for j in sorted(unused)
                      if inst["strings"][j][0] != inst["strings"][left][0]),
                     min(unused) if unused else left)
        if right not in unused:
            return _attack_adjacent_rows(inst)
        unused.remove(right)
        pairs.append([left, right])
    return _canonical_pairs(pairs)


def _row_permuted(inst, rng: random.Random) -> dict:
    order = list(range(inst["n"]))
    rng.shuffle(order)
    old_to_new = {old: new for new, old in enumerate(order)}
    changed = copy.deepcopy(inst)
    changed["strings"] = [inst["strings"][old] for old in order]
    changed["answer"] = _canonical_pairs(
        [[old_to_new[left], old_to_new[right]] for left, right in inst["answer"]]
    )
    return changed


def _reverse_complemented(inst) -> dict:
    changed = copy.deepcopy(inst)
    changed["strings"] = _reverse_complement_words(inst["strings"])
    changed["answer"] = copy.deepcopy(inst["answer"])
    return changed


def _answer_token_measure(answer) -> int:
    # Conservative lexical count: every integer and JSON punctuation mark.
    return len(re.findall(r"\d+|[\[\],-]", json.dumps(answer)))


def _answer_atoms(answer) -> int:
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest() -> dict:
    report = {
        "paper": "1707.04310",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: all named rungs and independent seeds.
    g1_ok = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_ok += int(ok)
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": g1_ok == 12 and not g1_failures,
        "verified": g1_ok,
        "attempts": 12,
        "failures": g1_failures,
    }

    # G2: each corruption reaches a distinct validation branch.
    probe = make_instance(seed=29, **DIFFICULTY["easy"])
    good = copy.deepcopy(probe["answer"])
    corruptions = {
        "drop_one_element": ([good[0][:1]] + good[1:]),
        "swap_between_pairs": (
            [[good[0][0], good[1][1]], [good[1][0], good[0][1]]] + good[2:]
        ),
        "duplicate_index": ([[good[0][0], good[0][0]]] + good[1:]),
        "empty": [],
        "out_of_range": ([[good[0][0], probe["n"]]] + good[1:]),
    }
    rejected = {}
    for name, answer in corruptions.items():
        ok, why = verify(probe, answer)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = [result["reason"] for result in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in rejected.values())
        and len(set(reasons)) == len(reasons),
        "corruptions": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: exact round-trip from realistic prose and a fenced block.
    planted = probe["answer"]
    body = json.dumps(planted, separators=(",", ":"))
    response = "I matched the paths exactly.\n<answer>\n```json\n" + body + "\n```\n</answer>\n"
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_equals_answer": parsed == planted,
    }

    shipping = make_instance(seed=8675309, **DIFFICULTY[SHIPPING_DIFFICULTY])
    samples = 200_000
    guess_rng = random.Random(170704310)
    hits = 0
    for _ in range(samples):
        hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    fraction = hits / samples
    report["G4_guess_resistance"] = {
        "pass": samples >= 200_000 and fraction < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": fraction,
        "candidate_space": search_space(shipping),
        "prior": "uniform over all perfect matchings of the named paths",
    }

    # G6 and the successful Track-B reference algorithm at eight shipping seeds.
    attack_names = (
        "outlier_label_frequency_extremes",
        "greedy_first_opposite_symbol",
        "input_adjacent_pairing",
        "random_restart_128_matchings",
    )
    attacks = {name: {"successes": 0, "attempts": 8} for name in attack_names}
    ref_successes = 0
    ref_times = []
    ref_operations = []
    for seed in range(80, 88):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidates = {
            "outlier_label_frequency_extremes": _attack_frequency_extremes(inst),
            "greedy_first_opposite_symbol": _attack_first_opposite(inst),
            "input_adjacent_pairing": _attack_adjacent_rows(inst),
        }
        rr_rng = random.Random(900_000 + seed)
        random_hit = False
        for _ in range(128):
            if verify(inst, random_candidate(inst, rr_rng))[0]:
                random_hit = True
                break
        candidates["random_restart_128_matchings"] = (
            inst["answer"] if random_hit else _attack_adjacent_rows(inst)
        )
        for name, candidate in candidates.items():
            attacks[name]["successes"] += int(verify(inst, candidate)[0])

        start = time.perf_counter()
        reference, operations = _reference_complement_hash(inst)
        elapsed = time.perf_counter() - start
        ref_successes += int(reference is not None and verify(inst, reference)[0])
        ref_times.append(elapsed)
        ref_operations.append(operations)

    all_attacks_failed = all(item["successes"] == 0 for item in attacks.values())
    mean_wall = sum(ref_times) / len(ref_times)
    mean_ops = sum(ref_operations) // len(ref_operations)
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and ref_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact pointwise-complement hashing",
            "complexity": "O(nL) exact symbol operations and O(nL) storage",
            "wall_clock_sec": round(mean_wall, 6),
            "operations": mean_ops,
            "solves": f"{ref_successes}/8, as expected",
        },
    }

    demo_count = enumerate_all(make_instance(seed=0, **DIFFICULTY["demo"]))
    report["G5_density_and_baseline"] = {
        "pass": hits == 0 and demo_count == 1 and ref_successes == 8,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_fraction": fraction,
        "demo_exact_solution_count": demo_count,
        "baseline_wall_clock_sec": round(mean_wall, 6),
        "baseline_operation_count": mean_ops,
    }

    # G7: double both path count and word length.  The witness is still planted,
    # even though this diagnostic build is deliberately beyond the shipping rung.
    doubled_params = dict(DIFFICULTY["hard"])
    doubled_params["n"] *= 2
    doubled_params["word_length"] *= 2
    doubled_params["signature_bits"] = 7
    doubled = make_instance(seed=101, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * shipping["n"]
        and doubled["word_length"] == 2 * shipping["word_length"],
        "original_n": shipping["n"],
        "doubled_n": doubled["n"],
        "original_word_length": shipping["word_length"],
        "doubled_word_length": doubled["word_length"],
        "verify_reason": doubled_why,
    }

    # G8: row permutations, global reverse+letter-swap, and their composition.
    invariance = 0
    transformed_verified = 0
    keys = []
    for seed in range(120, 140):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        rng = random.Random(700_000 + seed)
        permuted = _row_permuted(inst, rng)
        reversed_swapped = _reverse_complemented(inst)
        composed = _row_permuted(reversed_swapped, rng)
        key = canonical_key(inst)
        for changed in (permuted, reversed_swapped, composed):
            invariance += int(canonical_key(changed) == key)
        transformed_verified += int(verify(permuted, permuted["answer"])[0])
        transformed_verified += int(verify(reversed_swapped,
                                           reversed_swapped["answer"])[0])
        transformed_verified += int(verify(composed, composed["answer"])[0])
        keys.append(key)
    report["G8_canonical_key"] = {
        "pass": invariance == 60 and transformed_verified == 60
        and len(set(keys)) == 20,
        "invariance_checks_passed": invariance,
        "invariance_checks_attempted": 60,
        "transformed_witnesses_verified": transformed_verified,
        "transformed_witnesses_attempted": 60,
        "unrelated_distinct_keys": len(set(keys)),
        "unrelated_instances": 20,
        "exact_symmetries": [
            "permutation of input strings",
            "global path reversal composed with a<->b label swap",
        ],
    }

    blob = json.dumps(shipping["answer"])
    answer_tokens = _answer_token_measure(shipping["answer"])
    answer_elements = _answer_atoms(shipping["answer"])
    intended_ops = shipping["n"] * shipping["signature_bits"] + shipping["n"] // 2
    arms = copy.deepcopy(G9_MEASUREMENTS["arms"])
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = len(blob) <= 2000 and answer_elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "answer_chars": len(blob),
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
