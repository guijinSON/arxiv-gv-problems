"""Verified Shuffle Product witness generator for arXiv:2605.03727.

The module inverse-generates an interleaving map, samples equally distributed
source words, and composes the target from the next source symbol named by the
map.  The certificate is therefore known before the problem is assembled; no
instance is solved during generation.
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
import sys
import time
from collections import Counter


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # This finite-word family needs only the standard library.
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "source words over a finite alphabet",
        "target word",
        "position-by-position shuffle interleaving map",
    ],
    "verification_operations": [
        "integer range and multiplicity checks",
        "exact left-to-right symbol comparison",
        "exact source-exhaustion check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Write target positions in binary: alternating bit coordinates identify "
        "the source subsequence, whereas missing that coordinate split leaves a "
        "large multidimensional shuffle search."
    ),
    "hardness_basis": (
        "Track B: the fixed-k multidimensional dynamic program cited immediately "
        "before Theorem 3.1 has O(k(m+1)^k) state-transition cost for k equal-length "
        "sources; a memoized exact implementation solved 8/8 shipping instances "
        "at n=192, k=8 after 1,381,309 search-node visits in 9.14 seconds in the final gate "
        "measurement, while the alternating-bit coordinate route needs 232 exact "
        "classifications, signature reads, and lookups."
    ),
    "max_answer_tokens": 385,
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
        "A JSON list of n source indices.  Each index from 0 through k-1 occurs "
        "exactly n/k times; list order is the assignment to successive target "
        "positions."
    ),
    "bounds": {
        "shipping_answer_length": 192,
        "source_index_lower_bound": 0,
        "shipping_source_index_upper_bound": 7,
        "shipping_multiplicity_per_index": 24,
        "order_matters": 1,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 8, "k": 2, "alphabet_size": 4, "signature_length": 1},
    "easy": {"n": 64, "k": 4, "alphabet_size": 4, "signature_length": 2},
    "medium": {"n": 128, "k": 8, "alphabet_size": 4, "signature_length": 2},
    "hard": {"n": 192, "k": 8, "alphabet_size": 4, "signature_length": 2},
}
SHIPPING_DIFFICULTY: str = "hard"

STRUCTURAL_HINT: str = (
    "In the binary expansion of each 0-based target position, alternating bit coordinates are invariant for symbols drawn from one source."
)
PLACEBO_HINT: str = (
    "In the displayed source and target words, careful 0-based position tracking and consistent symbol bookkeeping help prevent indexing and transcription errors."
)

# Filled from the script-owned hardening runs after the local gates pass.
G9_MEASUREMENTS: dict = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "pending",
}

NOTES: str = r"""
Section 3, Definition 1 fixes the native problem used here: a target word is a
shuffle of source words when a bijection maps every source position to an equal
target symbol and preserves the order within every source.  The answer emitted
here is the equivalent inverse map, one source index per target position.
Theorem 3.1 proves that Binary Shuffle Product is XNLP-complete parameterized by
the number k of source words.  The paragraph immediately before that theorem
also records the important easy regime: constant-k instances are solvable in
polynomial time by multidimensional dynamic programming.  The theorem's
membership proof describes certificate search as guessing the source used at
each target position while retaining all k source cursors.

Step-0 algorithm question: a memoized form of that dynamic program produces a
witness in O(k(m+1)^k) state-transition work for k sources of common length m.
It is the successful Track-B reference algorithm, not a failing adversary.  At
the shipping preset, the final gate run over seeds 0--7 made 1,381,309 search-node visits
in 9.14 seconds.  The planted distribution is therefore not claimed to evade an
efficient fixed-k method.  Its intended no-tool shortcut is instead a change of
variables: alternating bits of the target-position index select a coordinate
class, and two-symbol source prefixes identify how those classes were relabelled.
That route uses 232 counted classifications, signature reads, and lookups.

Generation is inverse, never search-based.  The interleaving map is fixed first,
its coordinate classes are uniformly relabelled, and every source is sampled
from the same distribution: equal length, exactly equal alphabet histogram, and
a uniformly sampled unique prefix signature.  The target is then composed by
following the held map.  A verifier merely advances the named cursor and compares
symbols exactly.

Equal histograms remove length and frequency outliers.  Random source relabelling
removes positional bias.  The adversary panel tries transition-count outliers,
least-advanced greedy assignment, 256 random greedy restarts, and the natural
by-hand ansatz that each consecutive k-symbol target block uses every source
once.  The block ansatz is false because the coordinate classes are interleaved
across alternating binary digits rather than contiguous rounds.
""".strip()


_ALPHABET = "abcdefghij"
_ANSWER_RE = re.compile(
    r"<answer\b[^>]*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL
)


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_params(n: int, k: int, alphabet_size: int,
                     signature_length: int) -> None:
    if not all(_is_int(v) for v in (n, k, alphabet_size, signature_length)):
        raise TypeError("n, k, alphabet_size, and signature_length must be integers")
    if k < 2 or k & (k - 1):
        raise ValueError("k must be a power of two at least 2")
    if not 2 <= alphabet_size <= len(_ALPHABET):
        raise ValueError("alphabet_size must lie between 2 and 10 inclusive")
    if signature_length < 1:
        raise ValueError("signature_length must be positive")
    source_bits = k.bit_length() - 1
    period = 1 << (2 * source_bits)
    if n < period or n % period:
        raise ValueError("n must be a positive multiple of k squared")
    source_length = n // k
    if source_length % alphabet_size:
        raise ValueError("n/k must be divisible by alphabet_size")


def _coordinate_code(position: int, k: int) -> int:
    """Extract binary coordinates 0,2,4,... from a target position."""
    bits = k.bit_length() - 1
    period_mask = (1 << (2 * bits)) - 1
    position &= period_mask
    code = 0
    for out_bit in range(bits):
        code |= ((position >> (2 * out_bit)) & 1) << out_bit
    return code


def _eligible_prefixes(alphabet: str, length: int,
                       per_symbol: int) -> list[tuple[str, ...]]:
    return [
        prefix
        for prefix in itertools.product(alphabet, repeat=length)
        if all(prefix.count(symbol) <= per_symbol for symbol in alphabet)
    ]


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a Shuffle Product instance and its interleaving map."""
    k = params.pop("k", 8)
    alphabet_size = params.pop("alphabet_size", 4)
    signature_length = params.pop("signature_length", 2)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, k, alphabet_size, signature_length)
    if not _is_int(seed):
        raise TypeError("seed must be an integer")

    rng = random.Random(seed)
    alphabet = _ALPHABET[:alphabet_size]
    source_length = n // k
    per_symbol = source_length // alphabet_size

    coordinate_to_source = list(range(k))
    rng.shuffle(coordinate_to_source)
    answer = [coordinate_to_source[_coordinate_code(position, k)]
              for position in range(n)]

    prefixes = _eligible_prefixes(alphabet, signature_length, per_symbol)
    if len(prefixes) < k:
        raise ValueError("the signature language has fewer than k eligible prefixes")
    chosen_prefixes = rng.sample(prefixes, k)

    sources = []
    for prefix in chosen_prefixes:
        remaining_counts = {symbol: per_symbol for symbol in alphabet}
        for symbol in prefix:
            remaining_counts[symbol] -= 1
        tail = []
        for symbol in alphabet:
            tail.extend([symbol] * remaining_counts[symbol])
        rng.shuffle(tail)
        sources.append("".join(prefix) + "".join(tail))

    cursors = [0] * k
    target_symbols = []
    for source_index in answer:
        target_symbols.append(sources[source_index][cursors[source_index]])
        cursors[source_index] += 1

    return {
        "family": "shuffle_product_interleaving",
        "n": n,
        "k": k,
        "alphabet": alphabet,
        "sources": sources,
        "target": "".join(target_symbols),
        "answer": answer,
    }


def _display_word(word: str, width: int = 64) -> str:
    return " ".join(word[start:start + width]
                    for start in range(0, len(word), width))


def render(inst) -> str:
    """Render a complete native Shuffle Product witness problem."""
    n = inst["n"]
    k = inst["k"]
    source_length = n // k
    rows = "\n".join(
        f"{index}: {_display_word(word)}"
        for index, word in enumerate(inst["sources"])
    )
    statement = f"""SHUFFLE PRODUCT INTERLEAVING WITNESS

You are given {k} source words and one target word over the alphabet
{{{','.join(inst['alphabet'])}}}.  Every source word has exactly {source_length}
symbols and the target has exactly {n} symbols.  Spaces in the display only
separate 64-symbol blocks; they are not symbols.

A valid shuffle interleaving reads the target from left to right.  At each target
position it chooses one source word and consumes that source's next unused symbol.
The consumed symbol must equal the target symbol at that position.  Symbols in
each source must therefore be consumed in their original left-to-right order.
After the last target symbol, every source must be exhausted exactly.

Return the interleaving as a list of exactly {n} source indices: entry p names the
source consumed at 0-based target position p.  Source indices are the integers 0
through {k - 1}, inclusive.  Repetitions are required, list order matters, and
each source index must occur exactly {source_length} times.

Source words (0-based index: word):
{rows}

Target word:
{_display_word(inst['target'])}

Give your final answer inside <answer></answer> tags as one JSON list of exactly
{n} base-10 integers.
Example syntax: <answer>[0,1,0,1]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    """Parse the final tagged JSON list, tolerating prose and markdown fences."""
    if not isinstance(text, str):
        return None
    try:
        matches = _ANSWER_RE.findall(text)
        if not matches:
            return None
        body = matches[-1].strip()
        if body.startswith("```") and body.endswith("```"):
            body = re.sub(r"^```[^\n]*\n?", "", body)
            body = re.sub(r"\n?```$", "", body).strip()
        elif body.startswith("~~~") and body.endswith("~~~"):
            body = re.sub(r"^~~~[^\n]*\n?", "", body)
            body = re.sub(r"\n?~~~$", "", body).strip()
        value = json.loads(body)
        if not isinstance(value, list):
            return None
        if any(not _is_int(entry) for entry in value):
            return None
        return value
    except Exception:
        return None


def verify(inst, answer) -> tuple[bool, str]:
    """Check any interleaving witness exactly; never inspect inst['answer']."""
    n = inst.get("n")
    k = inst.get("k")
    sources = inst.get("sources")
    target = inst.get("target")
    if answer is None:
        return False, "answer is absent"
    if not isinstance(answer, (list, tuple)):
        return False, "answer must be a sequence of source indices"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) != n:
        return False, f"wrong length: expected {n}, got {len(answer)}"
    for position, source_index in enumerate(answer):
        if not _is_int(source_index):
            return False, f"non-integer source index at target position {position}"
        if not 0 <= source_index < k:
            return False, (
                f"source index out of range at target position {position}: "
                f"{source_index}"
            )

    source_length = n // k
    counts = Counter(answer)
    for source_index in range(k):
        if counts[source_index] != source_length:
            return False, (
                f"wrong multiplicity for source {source_index}: expected "
                f"{source_length}, got {counts[source_index]}"
            )

    cursors = [0] * k
    for position, source_index in enumerate(answer):
        source_position = cursors[source_index]
        actual = sources[source_index][source_position]
        expected = target[position]
        if actual != expected:
            return False, (
                f"symbol mismatch at target position {position}: source "
                f"{source_index} contributes {actual!r}, target requires {expected!r}"
            )
        cursors[source_index] += 1
    if any(cursor != len(sources[index])
           for index, cursor in enumerate(cursors)):
        return False, "not every source word is exhausted"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniformly sample the exact-multiplicity language a solver would search."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    source_length = inst["n"] // inst["k"]
    candidate = [index for index in range(inst["k"])
                 for _ in range(source_length)]
    rng.shuffle(candidate)
    return candidate


def search_space(inst) -> int | None:
    """Return the exact multinomial size n!/(m!)^k of the answer language."""
    n = inst["n"]
    k = inst["k"]
    source_length = n // k
    return math.factorial(n) // (math.factorial(source_length) ** k)


def enumerate_all(inst) -> int | None:
    """Count valid answers exactly when the language has at most 200,000 words."""
    if search_space(inst) > 200_000:
        return None
    k = inst["k"]
    remaining = [inst["n"] // k] * k
    candidate = []
    valid = 0

    def visit() -> None:
        nonlocal valid
        if len(candidate) == inst["n"]:
            if verify(inst, candidate)[0]:
                valid += 1
            return
        for source_index in range(k):
            if remaining[source_index]:
                remaining[source_index] -= 1
                candidate.append(source_index)
                visit()
                candidate.pop()
                remaining[source_index] += 1

    visit()
    return valid


def _normal_form(inst) -> str:
    alphabet = tuple(inst["alphabet"])
    candidates = []
    for reversed_words in (False, True):
        raw_target = inst["target"][::-1] if reversed_words else inst["target"]
        raw_sources = [word[::-1] if reversed_words else word
                       for word in inst["sources"]]
        for permuted_alphabet in itertools.permutations(alphabet):
            translation = str.maketrans(dict(zip(alphabet, permuted_alphabet)))
            target = raw_target.translate(translation)
            sources = sorted(word.translate(translation) for word in raw_sources)
            candidates.append(target + "|" + "|".join(sources))
    return min(candidates)


def canonical_key(inst) -> str:
    """Canonicalise source order, alphabet names, and global word reversal."""
    payload = f"{inst['n']}:{inst['k']}:" + _normal_form(inst)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params) -> dict | str | None:
    """Increase ambiguity at fixed answer length before declaring the cap bound."""
    harder = dict(params)
    alphabet_size = harder.get("alphabet_size", 4)
    if alphabet_size >= 4:
        harder["alphabet_size"] = 3
        return harder
    if alphabet_size == 3:
        harder["alphabet_size"] = 2
        harder["signature_length"] = max(3, harder.get("signature_length", 2))
        return harder
    if harder.get("n", 192) < 256:
        # Only after exhausting the fixed-length alphabet axis do we lengthen
        # the witness to the 256-atom boundary.  Its 64-entry coordinate template
        # is still computed once and repeated, so the compact route remains under
        # the arithmetic-operation cap.
        harder["n"] = 256
        return harder
    # A further supported multiple of k^2 would have at least 320 answer atoms.
    return "cap_bound"


def _greedy(inst, mode: str, rng: random.Random | None = None):
    sources = inst["sources"]
    target = inst["target"]
    k = inst["k"]
    cursors = [0] * k
    answer = []
    transitions = [sum(left != right for left, right in zip(word, word[1:]))
                   for word in sources]
    for symbol in target:
        eligible = [
            index for index in range(k)
            if cursors[index] < len(sources[index])
            and sources[index][cursors[index]] == symbol
        ]
        if not eligible:
            return None
        if mode == "least_advanced":
            chosen = min(eligible, key=lambda index: (cursors[index], index))
        elif mode == "transition_outlier":
            chosen = min(eligible, key=lambda index: (-transitions[index], index))
        elif mode == "random":
            chosen = rng.choice(eligible)
        else:
            raise ValueError("unknown greedy mode")
        cursors[chosen] += 1
        answer.append(chosen)
    return answer if all(cursor == len(sources[index])
                         for index, cursor in enumerate(cursors)) else None


def _round_block_attack(inst):
    """Assume every consecutive k-target block consumes every source once."""
    sources = inst["sources"]
    target = inst["target"]
    k = inst["k"]
    cursors = [0] * k
    answer = []
    for start in range(0, len(target), k):
        unused = set(range(k))
        for symbol in target[start:start + k]:
            eligible = [
                index for index in sorted(unused)
                if cursors[index] < len(sources[index])
                and sources[index][cursors[index]] == symbol
            ]
            if not eligible:
                return None
            chosen = min(eligible, key=lambda index: (cursors[index], index))
            unused.remove(chosen)
            cursors[chosen] += 1
            answer.append(chosen)
    return answer


def _exact_dp_solve(inst, node_limit: int | None = None):
    """Memoized fixed-k shuffle DP; return (answer, visited_states, exhausted)."""
    sources = inst["sources"]
    target = inst["target"]
    k = inst["k"]
    lengths = tuple(len(word) for word in sources)
    dead = set()
    visited = 0
    old_limit = sys.getrecursionlimit()
    if old_limit < len(target) + 100:
        sys.setrecursionlimit(len(target) + 100)

    def search(position: int, state: tuple[int, ...]):
        nonlocal visited
        visited += 1
        if node_limit is not None and visited > node_limit:
            return "limit"
        if position == len(target):
            return () if state == lengths else None
        if state in dead:
            return None
        symbol = target[position]
        eligible = [
            index for index in range(k)
            if state[index] < lengths[index]
            and sources[index][state[index]] == symbol
        ]
        eligible.sort(key=lambda index: (lengths[index] - state[index], index))
        for source_index in eligible:
            next_state = list(state)
            next_state[source_index] += 1
            suffix = search(position + 1, tuple(next_state))
            if suffix == "limit":
                return "limit"
            if suffix is not None:
                return (source_index,) + suffix
        dead.add(state)
        return None

    try:
        result = search(0, (0,) * k)
    finally:
        if sys.getrecursionlimit() != old_limit:
            sys.setrecursionlimit(old_limit)
    if result == "limit":
        return None, visited, False
    return (list(result) if result is not None else None), visited, True


def _projection_solve(inst):
    """Enumerate binary-coordinate projections; diagnostic special solver."""
    n = inst["n"]
    k = inst["k"]
    source_bits = k.bit_length() - 1
    position_bits = (n - 1).bit_length()
    source_lookup = {word: index for index, word in enumerate(inst["sources"])}
    operations = n  # exact hashing/reading of all source symbols
    for chosen_bits in itertools.combinations(range(position_bits), source_bits):
        groups = [[] for _ in range(k)]
        classes = []
        for position, symbol in enumerate(inst["target"]):
            code = 0
            for out_bit, position_bit in enumerate(chosen_bits):
                code |= ((position >> position_bit) & 1) << out_bit
            groups[code].append(symbol)
            classes.append(code)
            operations += source_bits + 1
        if any(len(group) != n // k for group in groups):
            continue
        mapping = {}
        for code, group in enumerate(groups):
            word = "".join(group)
            operations += len(word)
            if word not in source_lookup:
                break
            mapping[code] = source_lookup[word]
        if len(mapping) == k:
            answer = [mapping[code] for code in classes]
            if verify(inst, answer)[0]:
                return answer, operations, chosen_bits
    return None, operations, None


def _relabel_sources(inst, order: list[int]):
    """Return an equivalent instance and carry its answer through the relabelling."""
    transformed = copy.deepcopy(inst)
    transformed["sources"] = [inst["sources"][old] for old in order]
    old_to_new = {old: new for new, old in enumerate(order)}
    transformed["answer"] = [old_to_new[index] for index in inst["answer"]]
    return transformed


def _rename_alphabet(inst):
    transformed = copy.deepcopy(inst)
    alphabet = inst["alphabet"]
    rotated = alphabet[1:] + alphabet[:1]
    translation = str.maketrans(dict(zip(alphabet, rotated)))
    transformed["alphabet"] = rotated
    transformed["sources"] = [word.translate(translation)
                              for word in inst["sources"]]
    transformed["target"] = inst["target"].translate(translation)
    return transformed


def _reverse_words(inst):
    transformed = copy.deepcopy(inst)
    transformed["sources"] = [word[::-1] for word in inst["sources"]]
    transformed["target"] = inst["target"][::-1]
    transformed["answer"] = list(reversed(inst["answer"]))
    return transformed


def _answer_atom_count(answer) -> int:
    if isinstance(answer, dict):
        return sum(_answer_atom_count(value) for value in answer.values())
    if isinstance(answer, (list, tuple)):
        return sum(_answer_atom_count(value) for value in answer)
    return 1


def _intended_route_operations(inst, signature_length: int) -> int:
    """Count the compact route's exact operations at this parameter setting.

    The coordinate-label template has period k^2.  It is computed once using
    log2(k) bit extractions per position, then repeated without more arithmetic.
    Two signatures are read for each class (from its target fibre and its source)
    and one exact lookup identifies the relabelling.
    """
    k = inst["k"]
    source_bits = k.bit_length() - 1
    period = k * k
    return period * source_bits + 2 * k * signature_length + k


def selftest() -> dict:
    """Run gates G1--G9 and return their measured, JSON-native report."""
    report = {}

    g1_attempts = 0
    g1_failures = []
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/seed={seed}: {reason}")
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not g1_failures and json_roundtrips == g1_attempts,
        "verified": g1_attempts - len(g1_failures),
        "attempts": g1_attempts,
        "json_native_roundtrips": json_roundtrips,
        "failures": g1_failures,
    }

    inst = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = list(inst["answer"])
    corruptions = {}
    corrupted = planted[:-1]
    corruptions["drop_one"] = verify(inst, corrupted)
    corruptions["empty"] = verify(inst, [])
    corrupted = list(planted)
    corrupted[0] = inst["k"]
    corruptions["out_of_range"] = verify(inst, corrupted)
    corrupted = list(planted)
    replacement = (corrupted[0] + 1) % inst["k"]
    corrupted[0] = replacement
    corruptions["duplicate_one_label"] = verify(inst, corrupted)
    swapped_result = None
    for left in range(len(planted)):
        for right in range(left + 1, len(planted)):
            if planted[left] == planted[right]:
                continue
            corrupted = list(planted)
            corrupted[left], corrupted[right] = corrupted[right], corrupted[left]
            candidate_result = verify(inst, corrupted)
            if not candidate_result[0]:
                swapped_result = candidate_result
                break
        if swapped_result is not None:
            break
    corruptions["swap_two_positions"] = swapped_result or (True, "no corrupting swap")
    reasons = [reason for ok, reason in corruptions.values() if not ok]
    report["G2_rejects_corruption"] = {
        "pass": all(not ok for ok, _ in corruptions.values())
        and len(reasons) == len(set(reasons)),
        "cases": {name: {"accepted": ok, "reason": reason}
                  for name, (ok, reason) in corruptions.items()},
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "I used the source cursors as the state.\n\n"
        "<answer>\n```json\n" + json.dumps(inst["answer"]) +
        "\n```\n</answer>\n"
    )
    parsed = parse_answer(realistic)
    garbage_cases = ["", "no tags here", "<answer>[0, nope]</answer>",
                     "<answer>{\"x\": 1}</answer>"]
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"]
        and all(parse_answer(case) is None for case in garbage_cases),
        "realistic_response_round_trip": parsed == inst["answer"],
        "garbage_rejected": sum(parse_answer(case) is None for case in garbage_cases),
        "garbage_attempts": len(garbage_cases),
    }

    guess_rng = random.Random(0x260503727)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            guess_hits += 1
    guess_wall = time.perf_counter() - guess_start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_total >= 200_000 and guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_fraction,
        "structure_aware_constraints": (
            "length n and exact multiplicity n/k for every source index"
        ),
        "wall_clock_sec": round(guess_wall, 6),
        "candidate_space": search_space(inst),
    }

    attack_seeds = list(range(8))
    attack_successes = {
        "outlier_transition_priority": 0,
        "greedy_least_advanced": 0,
        "random_restart_256": 0,
        "in_context_round_block_ansatz": 0,
    }
    reference_successes = 0
    reference_nodes = 0
    reference_max_nodes = 0
    reference_wall = 0.0
    projection_successes = 0
    projection_operations = 0
    for seed in attack_seeds:
        trial = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidate = _greedy(trial, "transition_outlier")
        if candidate is not None and verify(trial, candidate)[0]:
            attack_successes["outlier_transition_priority"] += 1
        candidate = _greedy(trial, "least_advanced")
        if candidate is not None and verify(trial, candidate)[0]:
            attack_successes["greedy_least_advanced"] += 1
        restart_hit = False
        for restart in range(256):
            candidate = _greedy(
                trial, "random", random.Random(seed * 100_003 + restart)
            )
            if candidate is not None and verify(trial, candidate)[0]:
                restart_hit = True
                break
        if restart_hit:
            attack_successes["random_restart_256"] += 1
        candidate = _round_block_attack(trial)
        if candidate is not None and verify(trial, candidate)[0]:
            attack_successes["in_context_round_block_ansatz"] += 1

        dp_start = time.perf_counter()
        candidate, nodes, exhausted = _exact_dp_solve(trial)
        reference_wall += time.perf_counter() - dp_start
        reference_nodes += nodes
        reference_max_nodes = max(reference_max_nodes, nodes)
        if exhausted and candidate is not None and verify(trial, candidate)[0]:
            reference_successes += 1
        projection, operations, _ = _projection_solve(trial)
        projection_operations += operations
        if projection is not None and verify(trial, projection)[0]:
            projection_successes += 1
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_solution_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": guess_fraction < 1e-6 and reference_successes == len(attack_seeds),
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_solution_fraction": guess_fraction,
        "demo_exact_solution_count": demo_solution_count,
        "demo_candidate_count": search_space(demo),
        "baseline_wall_clock_sec": round(reference_wall, 6),
        "baseline_nodes": reference_nodes,
        "baseline_max_nodes_one_instance": reference_max_nodes,
        "baseline_instances_solved": reference_successes,
    }

    attacks = {
        name: {"successes": successes, "attempts": len(attack_seeds)}
        for name, successes in attack_successes.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(result["successes"] == 0 for result in attacks.values())
        and reference_successes == len(attack_seeds),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "memoized fixed-k multidimensional Shuffle Product DP",
            "complexity": "O(k*(m+1)^k) time and O((m+1)^k) states",
            "wall_clock_sec": round(reference_wall, 6),
            "operations": reference_nodes,
            "max_operations_one_instance": reference_max_nodes,
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
        "compact_route": {
            "name": "alternating binary coordinate projection plus prefix signatures",
            "intended_operations": _intended_route_operations(
                inst, DIFFICULTY[SHIPPING_DIFFICULTY]["signature_length"]
            ),
            "mechanical_projection_scan_operations": projection_operations,
            "solves": f"{projection_successes}/{len(attack_seeds)}",
        },
    }

    doubled_params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    doubled_params["n"] *= 2
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] > inst["n"]
        and search_space(doubled) > search_space(inst),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "shipping_search_space_bits": search_space(inst).bit_length(),
        "doubled_search_space_bits": search_space(doubled).bit_length(),
    }

    invariant_checks = 0
    carried_checks = 0
    unrelated_keys = []
    for seed in range(20):
        base = make_instance(seed=10_000 + seed,
                             **DIFFICULTY[SHIPPING_DIFFICULTY])
        base_key = canonical_key(base)
        unrelated_keys.append(base_key)
        order = list(range(base["k"]))
        random.Random(seed + 99).shuffle(order)
        relabelled = _relabel_sources(base, order)
        alphabet_renamed = _rename_alphabet(base)
        reversed_words = _reverse_words(base)
        composed = _reverse_words(_rename_alphabet(relabelled))
        for transformed in (relabelled, alphabet_renamed, reversed_words, composed):
            if canonical_key(transformed) == base_key:
                invariant_checks += 1
            if verify(transformed, transformed["answer"])[0]:
                carried_checks += 1
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 80
        and carried_checks == 80
        and len(set(unrelated_keys)) == 20,
        "invariance_passed": invariant_checks,
        "invariance_attempts": 80,
        "carried_witnesses_verified": carried_checks,
        "carried_witness_attempts": 80,
        "distinct_unrelated_keys": len(set(unrelated_keys)),
        "unrelated_attempts": 20,
        "transformations": [
            "source-word reordering with source-index relabelling",
            "global alphabet permutation",
            "simultaneous reversal of every source and the target",
            "composition of all three",
        ],
    }

    answer_blob = json.dumps(inst["answer"])
    lexical_tokens = len(re.findall(r"-?\d+|[\[\]{},:]", answer_blob))
    answer_elements = _answer_atom_count(inst["answer"])
    signature_length = DIFFICULTY[SHIPPING_DIFFICULTY]["signature_length"]
    intended_operations = _intended_route_operations(inst, signature_length)
    within_caps = (
        len(answer_blob) <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    arms = copy.deepcopy(G9_MEASUREMENTS["arms"])
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = (arms["hinted"]["solved"] / hinted_attempts
                   if hinted_attempts else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / placebo_attempts
                    if placebo_attempts else 0.0)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "answer_chars": len(answer_blob),
        "answer_tokens": lexical_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        result.get("pass") is True
        for name, result in report.items()
        if name.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
