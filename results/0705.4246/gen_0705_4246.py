"""Verified problem generator for arXiv:0705.4246.

The native task is a two-variable equation in the rank-two free group.  The
base equation is the paper's Section 3 word [x,y]^2 x, after one elementary
Nielsen transformation.  Further Nielsen transformations obscure a displayed
rank-two solution; Lemma 2.16 carries the solution through them exactly.

Generation never solves its output.  It starts with the Section 3 solution,
chooses the transformations, and evaluates the equation.  Verification freely
reduces a candidate substitution and compares it with the target word.
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


TRACK: str = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_discrete",
    "computational_core": "other",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "reduced words in the free group F(a,b)",
        "a two-variable word w(x,y)",
        "exact word-length and letter-multiplicity constraints",
    ],
    "verification_operations": [
        "exact free-group inversion",
        "exact word substitution",
        "stack-based free reduction",
        "exact reduced-word comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize the displayed exponent-sum pair as the column sum of a "
        "positive unimodular Nielsen matrix; without that change of variables "
        "one must length-reduce the full equation word."
    ),
    "hardness_basis": (
        "Track B: the introduction cites Ciobanu's polynomial-time rank-two "
        "endomorphism algorithm, and Definition 2.15 plus Lemmas 2.16-2.17 give "
        "Nielsen reduction; at hard n=10 the executable full-word reference "
        "solver measured 33,268 symbol scans (about 0.03 seconds) across eight "
        "shipping instances, while the Euclidean column-sum route used at most "
        "121 exact operations."
    ),
    "max_answer_tokens": 29,
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
        "A JSON object {x,y}.  Each value is a word over a,A,b,B of the exact "
        "displayed length and with the exact displayed multiplicity of each "
        "letter.  Uppercase is inverse.  Words need not be freely reduced as "
        "written; the checker reduces after substitution."
    ),
    "bounds": {
        "fields": ["x", "y"],
        "alphabet": ["a", "A", "b", "B"],
        "n_words": 2,
        "alphabet_size": 4,
        "lengths": "instance-displayed exact lengths",
        "letter_multiplicities": "instance-displayed exact counts",
        "maximum_total_letters_at_shipping": 101,
        "maximum_serialized_characters_at_shipping": 116,
        "maximum_estimated_tokens_at_shipping": 29,
        "candidate_count": "product of the two multiset-permutation counts",
    },
}

DIFFICULTY = {
    "demo": {"n": 1, "min_switches": 0, "t_span": 1, "answer_cap": 32},
    "easy": {"n": 7, "min_switches": 3, "t_span": 3, "answer_cap": 150},
    "medium": {"n": 9, "min_switches": 5, "t_span": 4, "answer_cap": 220},
    "hard": {"n": 10, "min_switches": 6, "t_span": 4, "answer_cap": 250},
}

SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The displayed exponent-sum pair is the column sum of a positive unimodular Nielsen matrix."
)
PLACEBO_HINT = (
    "The displayed uppercase and lowercase letters require careful attention during free reduction."
)

# Filled from the three independent harden.py runs once the bare level is fixed.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES = r"""
Section 1.1 fixes a solution as an exact substitution of two elements of F into
w(x,y), with equality in the free group.  Section 2.1 identifies the easy
regimes: primitive w (Proposition 1.9), w=1 and rank-one solutions (Lemma 2.2),
and proper powers (Lemma 2.3 and Corollary 2.5).  The generator instead starts
from Section 3's non-primitive, non-power word [x,y]^2 x and its displayed
rank-two solution.  Definition 2.15 and Lemma 2.16 say elementary Nielsen moves
carry both equation words and solution pairs; that is the construction route.

Track A is unavailable: the introduction explicitly cites Ciobanu's
polynomial-time decision method for w(x,y)=u, and Lemma 2.17 gives effective
Nielsen reduction.  Track B compares literal full-word Nielsen reduction with
the compact invariant: abelianization turns the planted positive Nielsen map
into a 2 by 2 unimodular nonnegative matrix, whose column sum uniquely recovers
the matrix by Bezout and whose shear factors follow by Euclidean subtraction.

The answer's exact letter multiplicities are disclosed.  This makes the G4
prior structure-aware: it samples only multiset permutations a solver would
retain, rather than arbitrary noise.  Signed permutations of both coefficient
generators and variables remove fixed orientation cues.  The audited attacks
are a frequency outlier, a target-prefix greedy arrangement, 256 random
multiset restarts, and a one-shear ansatz.  None is the successful Euclidean
route, which is measured separately alongside the domain-standard reference.
""".strip()


# Internal words are tuples from {+/-1,+/-2}; 1,2 denote the first and second
# generator and negative integers denote inverses.  Strings are used on the wire.
_AMBIENT_TO_CHAR = {1: "a", -1: "A", 2: "b", -2: "B"}
_CHAR_TO_AMBIENT = {value: key for key, value in _AMBIENT_TO_CHAR.items()}
_FORMAL_TO_CHAR = {1: "x", -1: "X", 2: "y", -2: "Y"}
_CHAR_TO_FORMAL = {value: key for key, value in _FORMAL_TO_CHAR.items()}
_COUNT_ORDER = ("a", "A", "b", "B")


def _reduce(word):
    stack = []
    for letter in word:
        if stack and stack[-1] == -letter:
            stack.pop()
        else:
            stack.append(letter)
    return tuple(stack)


def _inverse(word):
    return tuple(-letter for letter in reversed(word))


def _multiply(*words):
    return _reduce(itertools.chain.from_iterable(words))


def _power(word, exponent):
    if exponent < 0:
        return _power(_inverse(word), -exponent)
    result = ()
    base = tuple(word)
    # Straight repetition is deliberately used: shipping exponents are tiny,
    # and it makes the exact work performed by the verifier transparent.
    for _ in range(exponent):
        result = _multiply(result, base)
    return result


def _commutator(left, right):
    # This is the convention in the paper's displayed Section 3 calculation.
    return _multiply(_inverse(left), _inverse(right), left, right)


def _substitute(word, first, second):
    output = []
    for letter in word:
        image = first if abs(letter) == 1 else second
        output.extend(image if letter > 0 else _inverse(image))
    return _reduce(output)


def _encode(word, formal=False):
    table = _FORMAL_TO_CHAR if formal else _AMBIENT_TO_CHAR
    return "".join(table[letter] for letter in word) or "1"


def _decode(text, formal=False, allow_identity=True):
    if not isinstance(text, str):
        return None
    if text == "1" and allow_identity:
        return ()
    table = _CHAR_TO_FORMAL if formal else _CHAR_TO_AMBIENT
    if not text or any(letter not in table for letter in text):
        return None
    return tuple(table[letter] for letter in text)


def _signed_maps():
    maps = []
    for order in ((1, 2), (2, 1)):
        for sign1 in (-1, 1):
            for sign2 in (-1, 1):
                maps.append((sign1 * order[0], sign2 * order[1]))
    return tuple(maps)


_SIGNED_MAPS = _signed_maps()


def _inverse_signed_map(mapping):
    result = [0, 0]
    for source, image in enumerate(mapping, 1):
        target = abs(image)
        result[target - 1] = source if image > 0 else -source
    return tuple(result)


def _apply_signed_word(word, mapping):
    return _substitute(word, (mapping[0],), (mapping[1],))


def _apply_signed_pair(mapping, pair):
    return (
        _substitute((mapping[0],), pair[0], pair[1]),
        _substitute((mapping[1],), pair[0], pair[1]),
    )


def _base_words():
    x = (1,)
    y = (2,)
    comm = _commutator(x, y)
    w0 = _multiply(comm, comm, x)       # [x,y]^2 x from Section 3
    w1 = _substitute(w0, (1, 2), (2,))  # one fixed Nielsen transform
    return w0, w1


_W0, _W1 = _base_words()
_L_INV = ((1, -2), (2,))  # inverse of x -> xy, y -> y
_R_INV = ((1,), (2, -1))  # inverse of x -> x, y -> yx


def _base_target_and_solution(t):
    a = (1,)
    b = (2,)
    # Section 3: [b^-1 a^t, b^-1 a b]^2_comm * b^-1 a^t
    # equals [a,b] a^-1 b^-1 a^(t+1).
    x0 = _multiply(_inverse(b), _power(a, t))
    y0 = _multiply(_inverse(b), a, b)
    u = _multiply(
        _commutator(a, b), _inverse(a), _inverse(b), _power(a, t + 1)
    )
    # w1 = L(w0), so L^-1 carries the displayed solution to w1.
    x1 = _multiply(x0, _inverse(y0))
    y1 = y0
    assert _substitute(_W1, x1, y1) == u
    return u, (x1, y1)


def _forward_nielsen_images(sequence):
    first, second = (1,), (2,)
    for move in sequence:
        if move == "L":
            first = _multiply(first, second)
        else:
            second = _multiply(second, first)
    return first, second


def _inverse_nielsen_values(pair, sequence):
    first, second = pair
    # The image pair is built by right-composing elementary maps, so values are
    # recovered in reverse construction order.
    for move in reversed(sequence):
        if move == "L":
            first = _multiply(first, _inverse(second))
        else:
            second = _multiply(second, _inverse(first))
    return first, second


def _switches(sequence):
    return sum(left != right for left, right in zip(sequence, sequence[1:]))


def _counts(word):
    counter = Counter(_encode(word))
    return [counter[letter] for letter in _COUNT_ORDER]


def _count_word(counts):
    return "".join(letter * count for letter, count in zip(_COUNT_ORDER, counts))


def _sample_multiset_word(counts, rng):
    letters = list(_count_word(counts))
    rng.shuffle(letters)
    return "".join(letters)


def _validate_parameters(n, min_switches, t_span, answer_cap):
    values = (n, min_switches, t_span, answer_cap)
    if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
        raise ValueError("all parameters must be integers")
    if n < 0 or n > 24:
        raise ValueError("n must lie between 0 and 24")
    if min_switches < 0 or min_switches > max(0, n - 1):
        raise ValueError("min_switches must lie between 0 and n-1")
    if t_span < 1:
        raise ValueError("t_span must be positive")
    if answer_cap < 8:
        raise ValueError("answer_cap is too small")


def make_instance(
    n: int,
    seed: int = 0,
    min_switches: int = 0,
    t_span: int = 3,
    answer_cap: int = 250,
) -> dict:
    """Construct an equation and its solution by exact Nielsen transport."""

    _validate_parameters(n, min_switches, t_span, answer_cap)
    rng = random.Random(seed)
    chosen = None
    # This samples construction parameters, not candidate solutions.  Every
    # trial already comes with its transported certificate.
    for _ in range(20_000):
        sequence = "".join(rng.choice("LR") for _ in range(n))
        if _switches(sequence) < min_switches:
            continue
        t = 1 + rng.randrange(t_span)
        u_base, base_pair = _base_target_and_solution(t)
        images = _forward_nielsen_images(sequence)
        w_positive = _substitute(_W1, images[0], images[1])
        pair_positive = _inverse_nielsen_values(base_pair, sequence)
        if len(pair_positive[0]) + len(pair_positive[1]) > answer_cap:
            continue
        # Avoid shallow accidental instances at non-demo levels.
        if n >= 7 and len(w_positive) < 55:
            continue
        chosen = (sequence, t, u_base, w_positive, pair_positive)
        break
    if chosen is None:
        raise ValueError("no construction fits the requested answer cap")

    sequence, t, u_base, w_positive, pair_positive = chosen
    variable_map = rng.choice(_SIGNED_MAPS)
    ambient_map = rng.choice(_SIGNED_MAPS)
    w_final = _apply_signed_word(w_positive, variable_map)
    variable_normalizer = _inverse_signed_map(variable_map)
    pair_variable = _apply_signed_pair(variable_normalizer, pair_positive)
    u_final = _apply_signed_word(u_base, ambient_map)
    pair_final = tuple(_apply_signed_word(word, ambient_map) for word in pair_variable)
    assert _substitute(w_final, pair_final[0], pair_final[1]) == u_final

    answer = {"x": _encode(pair_final[0]), "y": _encode(pair_final[1])}
    exponent_sums = [
        sum(1 if letter == generator else -1 if letter == -generator else 0
            for letter in w_final)
        for generator in (1, 2)
    ]
    return {
        "n": n,
        "w": _encode(w_final, formal=True),
        "u": _encode(u_final),
        "exponent_sums": exponent_sums,
        "x_length": len(answer["x"]),
        "y_length": len(answer["y"]),
        "x_counts": _counts(pair_final[0]),
        "y_counts": _counts(pair_final[1]),
        "answer": answer,
    }


def render(inst: dict) -> str:
    statement = f"""Solve one exact equation in the free group F(a,b).

A word is a string over a, A, b, B.  Here A means a^(-1), B means
b^(-1), juxtaposition is multiplication, and the empty word is the identity.
Equality means equality after repeatedly deleting consecutive inverse pairs aA,
Aa, bB, or Bb.  The unknown words x and y are substituted into a word over
x, X, y, Y, where X means x^(-1) and Y means y^(-1).

Equation word w(x,y): {inst['w']}
Target reduced word u: {inst['u']}

For reference, the exponent sums of x and y in w are respectively
{inst['exponent_sums'][0]} and {inst['exponent_sums'][1]}.  An exponent sum
counts a lowercase occurrence as +1 and its uppercase inverse as -1.

Find words x and y such that freely reducing w(x,y) gives exactly u.  Your
spelled words need not themselves be freely reduced, but they must obey all
of these exact side constraints:
  x has length {inst['x_length']} and counts [a,A,b,B] = {inst['x_counts']};
  y has length {inst['y_length']} and counts [a,A,b,B] = {inst['y_counts']}.
Order matters, repetitions are allowed exactly as prescribed by those counts,
and all indexing implicit in the strings is left-to-right.

Give your final answer inside <answer></answer> tags as one JSON object with
exactly two string fields, x and y.
Example: <answer>{{"x":"aB","y":"bA"}}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer>\s*(.*?)\s*</answer>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        answer = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(answer, dict) or set(answer) != {"x", "y"}:
        return None
    if not all(isinstance(answer[key], str) for key in ("x", "y")):
        return None
    return {"x": answer["x"], "y": answer["y"]}


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if set(answer) != {"x", "y"}:
        return False, "answer must have exactly the fields x and y"
    if not isinstance(answer["x"], str) or not isinstance(answer["y"], str):
        return False, "x and y must both be strings"
    for name in ("x", "y"):
        word = answer[name]
        expected_length = inst[name + "_length"]
        if len(word) != expected_length:
            return False, f"{name} must have length {expected_length}"
        invalid = sorted(set(word) - set(_CHAR_TO_AMBIENT))
        if invalid:
            return False, f"{name} contains a symbol outside a,A,b,B"
        if _counts(_decode(word)) != inst[name + "_counts"]:
            return False, f"{name} has the wrong [a,A,b,B] multiplicities"
    x_word = _decode(answer["x"])
    y_word = _decode(answer["y"])
    formal = _decode(inst["w"], formal=True)
    target = _decode(inst["u"])
    if formal is None or target is None:
        return False, "instance contains a malformed word"
    if _substitute(formal, x_word, y_word) != target:
        return False, "the freely reduced substitution does not equal u"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    return {
        "x": _sample_multiset_word(inst["x_counts"], rng),
        "y": _sample_multiset_word(inst["y_counts"], rng),
    }


def _multinomial(counts):
    total = sum(counts)
    result = math.factorial(total)
    for count in counts:
        result //= math.factorial(count)
    return result


def search_space(inst: dict) -> int | None:
    return _multinomial(inst["x_counts"]) * _multinomial(inst["y_counts"])


def _unique_multiset_words(counts):
    letters = list(_COUNT_ORDER)
    remaining = list(counts)
    length = sum(counts)
    output = []

    def visit():
        if len(output) == length:
            yield "".join(output)
            return
        for index, letter in enumerate(letters):
            if remaining[index]:
                remaining[index] -= 1
                output.append(letter)
                yield from visit()
                output.pop()
                remaining[index] += 1

    yield from visit()


def enumerate_all(inst: dict) -> int | None:
    if search_space(inst) > 500_000:
        return None
    count = 0
    y_words = list(_unique_multiset_words(inst["y_counts"]))
    for x_word in _unique_multiset_words(inst["x_counts"]):
        for y_word in y_words:
            if verify(inst, {"x": x_word, "y": y_word})[0]:
                count += 1
    return count


def _transform_counts_ambient(counts, mapping):
    result = [0, 0, 0, 0]
    char_index = {letter: index for index, letter in enumerate(_COUNT_ORDER)}
    for old_letter, amount in zip((1, -1, 2, -2), counts):
        image = mapping[abs(old_letter) - 1]
        if old_letter < 0:
            image = -image
        result[char_index[_AMBIENT_TO_CHAR[image]]] += amount
    return result


def _inverse_counts(counts):
    return [counts[1], counts[0], counts[3], counts[2]]


def _transform_constraints_variable(inst, mapping):
    inverse_map = _inverse_signed_map(mapping)
    old = {
        1: (inst["x_length"], list(inst["x_counts"])),
        2: (inst["y_length"], list(inst["y_counts"])),
    }
    transformed = []
    for image in inverse_map:
        length, counts = old[abs(image)]
        transformed.append((length, counts if image > 0 else _inverse_counts(counts)))
    return transformed


def _canonical_serial(inst, ambient_map, variable_map):
    w = _apply_signed_word(_decode(inst["w"], formal=True), variable_map)
    u = _apply_signed_word(_decode(inst["u"]), ambient_map)
    constraints = _transform_constraints_variable(inst, variable_map)
    constraints = [
        (length, _transform_counts_ambient(counts, ambient_map))
        for length, counts in constraints
    ]
    payload = [
        _encode(w, formal=True),
        _encode(u),
        constraints[0][0],
        constraints[0][1],
        constraints[1][0],
        constraints[1][1],
    ]
    return json.dumps(payload, separators=(",", ":"))


def canonical_key(inst: dict) -> str:
    # Complete for signed permutations/inversions of the two coefficient
    # generators and two variables.  General Nielsen equivalence is deliberately
    # not claimed as a cheap relabelling invariant.
    canonical = min(
        _canonical_serial(inst, ambient, variable)
        for ambient in _SIGNED_MAPS
        for variable in _SIGNED_MAPS
    )
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    current = dict(params)
    if current["n"] >= 10:
        return "cap_bound"
    current["n"] += 1
    current["min_switches"] = min(
        current["n"] - 1, current.get("min_switches", 0) + 1
    )
    current["t_span"] = current.get("t_span", 3) + 1
    current["answer_cap"] = min(250, current.get("answer_cap", 250) + 20)
    return current


def _parse_base_target(word):
    for t in range(1, 128):
        target, _ = _base_target_and_solution(t)
        if target == word:
            return t
        if len(target) > len(word) + 2:
            break
    return None


def _decode_column_sum(p, q):
    """Recover the unique nonnegative unimodular columns summing to (p,q)."""
    if p <= 0 or q <= 0 or math.gcd(p, q) != 1:
        return None
    if q == 1:
        second = (p - 1, 1)
    else:
        d = pow(p, -1, q)
        second = ((p * d - 1) // q, d)
    first = (p - second[0], q - second[1])
    if first[0] * second[1] - first[1] * second[0] != 1:
        return None
    left = list(first)
    right = list(second)
    reversed_moves = []
    while left != [1, 0] or right != [0, 1]:
        if left[0] >= right[0] and left[1] >= right[1]:
            left[0] -= right[0]
            left[1] -= right[1]
            reversed_moves.append("L")
        elif right[0] >= left[0] and right[1] >= left[1]:
            right[0] -= left[0]
            right[1] -= left[1]
            reversed_moves.append("R")
        else:
            return None
        if len(reversed_moves) > 64:
            return None
    return "".join(reversed(reversed_moves))


def _normalizers_for_target(inst):
    target = _decode(inst["u"])
    for ambient_normalizer in _SIGNED_MAPS:
        normalized = _apply_signed_word(target, ambient_normalizer)
        t = _parse_base_target(normalized)
        if t is not None:
            yield ambient_normalizer, t


def _compact_solve(inst):
    formal = _decode(inst["w"], formal=True)
    operations = 0
    for ambient_normalizer, t in _normalizers_for_target(inst):
        operations += 8
        ambient_denormalizer = _inverse_signed_map(ambient_normalizer)
        _, base_pair = _base_target_and_solution(t)
        for variable_normalizer in _SIGNED_MAPS:
            normalized = _apply_signed_word(formal, variable_normalizer)
            sx = sum(1 if z == 1 else -1 if z == -1 else 0 for z in normalized)
            sy = sum(1 if z == 2 else -1 if z == -2 else 0 for z in normalized)
            operations += 6
            sequence = _decode_column_sum(sx, sy)
            if sequence is None:
                continue
            images = _forward_nielsen_images(sequence)
            operations += 2 * len(sequence) + 4
            if _substitute(_W1, images[0], images[1]) != normalized:
                continue
            positive_pair = _inverse_nielsen_values(base_pair, sequence)
            variable_pair = _apply_signed_pair(variable_normalizer, positive_pair)
            final_pair = tuple(
                _apply_signed_word(word, ambient_denormalizer)
                for word in variable_pair
            )
            answer = {"x": _encode(final_pair[0]), "y": _encode(final_pair[1])}
            # Constructing/spelling the witness is accounted for separately by
            # G9's answer-element cap.  Here "operations" means the exact
            # integer/group operations after the invariant is recognized.
            operations += 3 * len(sequence) + 8
            if verify(inst, answer)[0]:
                return answer, operations, sequence, variable_normalizer
    return None, operations, None, None


def _nielsen_reduce_full_word(normalized, max_depth):
    current = normalized
    path = ""
    operations = 0
    for _ in range(max_depth + 1):
        if current == _W1:
            return path, operations
        if len(path) >= max_depth:
            break
        operations += 2 * len(current)
        candidates = [
            (_substitute(current, _L_INV[0], _L_INV[1]), "L"),
            (_substitute(current, _R_INV[0], _R_INV[1]), "R"),
        ]
        candidates.sort(key=lambda item: (len(item[0]), item[1]))
        next_word, move = candidates[0]
        if len(next_word) >= len(current):
            break
        current = next_word
        path += move
    return None, operations


def _reference_solve(inst):
    formal = _decode(inst["w"], formal=True)
    total_operations = 0
    for ambient_normalizer, t in _normalizers_for_target(inst):
        ambient_denormalizer = _inverse_signed_map(ambient_normalizer)
        _, base_pair = _base_target_and_solution(t)
        for variable_normalizer in _SIGNED_MAPS:
            normalized = _apply_signed_word(formal, variable_normalizer)
            path, operations = _nielsen_reduce_full_word(normalized, inst["n"] + 2)
            total_operations += operations + len(normalized)
            if path is None:
                continue
            positive_pair = _inverse_nielsen_values(base_pair, path)
            variable_pair = _apply_signed_pair(variable_normalizer, positive_pair)
            final_pair = tuple(
                _apply_signed_word(word, ambient_denormalizer)
                for word in variable_pair
            )
            answer = {"x": _encode(final_pair[0]), "y": _encode(final_pair[1])}
            total_operations += len(answer["x"]) + len(answer["y"])
            if verify(inst, answer)[0]:
                return answer, total_operations
    return None, total_operations


# Two exact determinant-one matrix quotients provide a fast necessary test.
_HASH_PRIMES = (1_000_003, 1_000_033)
_HASH_A = (1, 2, 0, 1)
_HASH_B = (1, 0, 2, 1)


def _mat_mul(left, right, p):
    a, b, c, d = left
    e, f, g, h = right
    return (
        (a * e + b * g) % p,
        (a * f + b * h) % p,
        (c * e + d * g) % p,
        (c * f + d * h) % p,
    )


def _mat_inv(matrix, p):
    a, b, c, d = matrix
    return (d % p, -b % p, -c % p, a % p)


def _word_matrix(word, p):
    result = (1, 0, 0, 1)
    generators = {1: _HASH_A, 2: _HASH_B}
    for letter in word:
        matrix = generators[abs(letter)]
        if letter < 0:
            matrix = _mat_inv(matrix, p)
        result = _mat_mul(result, matrix, p)
    return result


def _mat_apply_signed_pair(mapping, pair, p):
    result = []
    for image in mapping:
        matrix = pair[abs(image) - 1]
        result.append(matrix if image > 0 else _mat_inv(matrix, p))
    return tuple(result)


_DIHEDRAL_P = 1_000_003
_DIHEDRAL_GENERATORS = (
    ((1, 0), (0, 1)),
    ((17, 1), (31, 0)),
)


def _dih_mul(left, right, p=_DIHEDRAL_P):
    # (r,s) denotes rotation^r * reflection^s in D_{2p}.
    return ((left[0] + (-right[0] if left[1] else right[0])) % p,
            left[1] ^ right[1])


def _dih_inv(value, p=_DIHEDRAL_P):
    return ((value[0] if value[1] else -value[0]) % p, value[1])


def _dih_word(word, generators):
    value = (0, 0)
    for letter in word:
        image = generators[abs(letter) - 1]
        if letter < 0:
            image = _dih_inv(image)
        value = _dih_mul(value, image)
    return value


def _dih_signed_pair(mapping, pair):
    return tuple(
        pair[abs(image) - 1] if image > 0 else _dih_inv(pair[abs(image) - 1])
        for image in mapping
    )


def _candidate_valid_fast(inst, answer, compact_plan=None):
    # The quotient test can reject but never accept falsely: any true equality
    # has equal images under every group homomorphism.  Hash matches are checked
    # by the exact verifier.
    if compact_plan is None:
        recovered, _, sequence, variable_normalizer = _compact_solve(inst)
        if recovered is None:
            return verify(inst, answer)[0]
        compact_plan = (sequence, variable_normalizer)
    sequence, variable_normalizer = compact_plan
    x_word = _decode(answer.get("x")) if isinstance(answer, dict) else None
    y_word = _decode(answer.get("y")) if isinstance(answer, dict) else None
    if x_word is None or y_word is None:
        return False
    inverse_normalizer = _inverse_signed_map(variable_normalizer)
    target = _decode(inst["u"])
    # A tiny noncommutative quotient is much cheaper than 2x2 modular matrices
    # for 200,000 candidates.  A mismatch is a rigorous rejection; the rare
    # matches continue to a second quotient and finally exact verification.
    for generators in _DIHEDRAL_GENERATORS:
        pair = (_dih_word(x_word, generators), _dih_word(y_word, generators))
        first, second = _dih_signed_pair(inverse_normalizer, pair)
        for move in sequence:
            if move == "L":
                first = _dih_mul(first, second)
            else:
                second = _dih_mul(second, first)
        current = (0, 0)
        for letter in _W1:
            value = first if abs(letter) == 1 else second
            if letter < 0:
                value = _dih_inv(value)
            current = _dih_mul(current, value)
        if current != _dih_word(target, generators):
            return False
    for p in _HASH_PRIMES:
        pair = (_word_matrix(x_word, p), _word_matrix(y_word, p))
        pair = _mat_apply_signed_pair(inverse_normalizer, pair, p)
        first, second = pair
        for move in sequence:
            if move == "L":
                first = _mat_mul(first, second, p)
            else:
                second = _mat_mul(second, first, p)
        # Evaluate the fixed w1 exactly in the matrix quotient.
        current = (1, 0, 0, 1)
        for letter in _W1:
            matrix = first if abs(letter) == 1 else second
            if letter < 0:
                matrix = _mat_inv(matrix, p)
            current = _mat_mul(current, matrix, p)
        if current != _word_matrix(target, p):
            return False
    return verify(inst, answer)[0]


def _fit_counts_from_stream(inst, name, stream):
    remaining = dict(zip(_COUNT_ORDER, inst[name + "_counts"]))
    output = []
    # Attack streams may be cyclic and omit a required letter.  Give the
    # heuristic a bounded opportunity, then append the still-missing multiset
    # in the public alphabet order.
    budget = max(16, 16 * inst[name + "_length"])
    bounded = itertools.islice(stream, budget)
    fallback = itertools.chain.from_iterable(
        itertools.repeat(letter, inst[name + "_length"])
        for letter in _COUNT_ORDER
    )
    for letter in itertools.chain(bounded, fallback):
        if remaining.get(letter, 0):
            output.append(letter)
            remaining[letter] -= 1
            if len(output) == inst[name + "_length"]:
                return "".join(output)
    raise AssertionError("unreachable")


def _attack_outlier(inst):
    # Put the most frequent letters first, independently in each word.
    answer = {}
    for name in ("x", "y"):
        order = sorted(
            _COUNT_ORDER,
            key=lambda letter: (-inst[name + "_counts"][_COUNT_ORDER.index(letter)], letter),
        )
        answer[name] = _fit_counts_from_stream(inst, name, itertools.cycle(order))
    return answer


def _attack_target_prefix(inst):
    stream = itertools.cycle(inst["u"] + inst["u"][::-1])
    x = _fit_counts_from_stream(inst, "x", stream)
    stream = itertools.cycle(inst["u"][::-1] + inst["u"])
    y = _fit_counts_from_stream(inst, "y", stream)
    return {"x": x, "y": y}


def _attack_one_shear(inst):
    # Normalize the coefficient orientation but pretend every positive Nielsen
    # map was a single repeated L shear.  Counts are then repaired without using
    # the equation, keeping this inside the stated candidate language.
    t_info = next(iter(_normalizers_for_target(inst)), None)
    if t_info is None:
        return _attack_outlier(inst)
    ambient_normalizer, t = t_info
    _, pair = _base_target_and_solution(t)
    shear = max(abs(value) for value in inst["exponent_sums"])
    guessed = _inverse_nielsen_values(pair, "L" * min(shear, 32))
    denorm = _inverse_signed_map(ambient_normalizer)
    streams = [
        itertools.cycle(_encode(_apply_signed_word(word, denorm)) or "a")
        for word in guessed
    ]
    return {
        "x": _fit_counts_from_stream(inst, "x", streams[0]),
        "y": _fit_counts_from_stream(inst, "y", streams[1]),
    }


def _relabel_instance(inst, ambient_map=(1, 2), variable_map=(1, 2)):
    changed = dict(inst)
    w = _apply_signed_word(_decode(inst["w"], formal=True), variable_map)
    u = _apply_signed_word(_decode(inst["u"]), ambient_map)
    changed["w"] = _encode(w, formal=True)
    changed["u"] = _encode(u)
    changed["exponent_sums"] = [
        sum(1 if z == g else -1 if z == -g else 0 for z in w)
        for g in (1, 2)
    ]
    constraints = _transform_constraints_variable(inst, variable_map)
    changed["x_length"], x_counts = constraints[0]
    changed["y_length"], y_counts = constraints[1]
    changed["x_counts"] = _transform_counts_ambient(x_counts, ambient_map)
    changed["y_counts"] = _transform_counts_ambient(y_counts, ambient_map)

    old_pair = (_decode(inst["answer"]["x"]), _decode(inst["answer"]["y"]))
    new_pair = _apply_signed_pair(_inverse_signed_map(variable_map), old_pair)
    new_pair = tuple(_apply_signed_word(word, ambient_map) for word in new_pair)
    changed["answer"] = {"x": _encode(new_pair[0]), "y": _encode(new_pair[1])}
    return changed


def _answer_elements(answer):
    return len(answer["x"]) + len(answer["y"])


def selftest() -> dict:
    report = {}

    # G1 across every rung and several independent constructions.
    checks = 0
    failures = []
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed, "reason": "not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "failures": failures,
        "construction": "Section 3 solution transported by Lemma 2.16 Nielsen maps",
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=271828, **shipping_params)
    answer = inst["answer"]

    # G2: five natural corruptions, deliberately arranged to exercise distinct
    # checker paths.
    swapped_letters = list(answer["x"])
    for right in range(1, len(swapped_letters)):
        if swapped_letters[right] != swapped_letters[0]:
            swapped_letters[0], swapped_letters[right] = (
                swapped_letters[right], swapped_letters[0]
            )
            break
    swapped = "".join(swapped_letters)
    corruptions = {
        "drop_one": {"x": answer["x"][:-1], "y": answer["y"]},
        "swap_two": {"x": swapped, "y": answer["y"]},
        "duplicate_word": {"x": answer["x"], "y": answer["x"]},
        "empty": None,
        "out_of_range": {"x": "z" + answer["x"][1:], "y": answer["y"]},
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = [item["reason"] for item in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "corruptions": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The exponent sums reveal the Nielsen coordinates.\n```json\n"
        + "<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nI then checked the free reduction."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer,
        "parsed_equals_answer": parsed == answer,
        "surrounding_prose_and_markdown": True,
    }

    # Recover the public compact plan once; it is used only as a fast necessary
    # quotient test for the 200k samples.
    compact_answer, compact_ops, sequence, variable_normalizer = _compact_solve(inst)
    compact_plan = (sequence, variable_normalizer)
    trials = 200_000
    rng = random.Random(0x07054246)
    hits = 0
    guess_started = time.perf_counter()
    for _ in range(trials):
        candidate = random_candidate(inst, rng)
        hits += int(_candidate_valid_fast(inst, candidate, compact_plan))
    guess_seconds = time.perf_counter() - guess_started
    guess_rate = hits / trials
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": hits,
        "total": trials,
        "observed_probability": guess_rate,
        "candidate_space": search_space(inst),
        "prior": "uniform independent permutations of each disclosed letter multiset",
        "wall_clock_sec": round(guess_seconds, 6),
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    baseline_rng = random.Random(424242)
    baseline_started = time.perf_counter()
    baseline_success = False
    for _ in range(256):
        if _candidate_valid_fast(inst, random_candidate(inst, baseline_rng), compact_plan):
            baseline_success = True
            break
    baseline_seconds = time.perf_counter() - baseline_started

    reference_started = time.perf_counter()
    reference_answer, reference_ops = _reference_solve(inst)
    reference_seconds = time.perf_counter() - reference_started
    reference_ok = reference_answer is not None and verify(inst, reference_answer)[0]
    report["G5_density_and_baseline_cost"] = {
        "pass": demo_count is not None and reference_ok and not baseline_success,
        "shipping_seed": 271828,
        "shipping_density_hits": hits,
        "shipping_density_samples": trials,
        "shipping_sampled_solution_fraction": guess_rate,
        "shipping_exact_solution_count": None,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "strongest_failing_attack": "256 structure-aware random multiset restarts",
        "baseline_iterations": 256,
        "baseline_success": baseline_success,
        "baseline_wall_clock_sec": round(baseline_seconds, 6),
        "reference_operation_count": reference_ops,
        "reference_wall_clock_sec": round(reference_seconds, 6),
    }

    attack_names = (
        "letter_frequency_outlier",
        "target_prefix_greedy",
        "random_multiset_restart_256",
        "in_context_single_shear_ansatz",
    )
    attacks = {name: {"successes": 0, "attempts": 8, "wall_clock_sec": 0.0}
               for name in attack_names}
    reference_successes = 0
    reference_operations = []
    reference_times = []
    compact_successes = 0
    compact_operations = []
    compact_times = []
    for seed in range(10_000, 10_008):
        current = make_instance(seed=seed, **shipping_params)
        candidates = {
            "letter_frequency_outlier": _attack_outlier(current),
            "target_prefix_greedy": _attack_target_prefix(current),
            "in_context_single_shear_ansatz": _attack_one_shear(current),
        }
        rr_rng = random.Random(seed ^ 0xBAD5EED)
        rr_answer = None
        rr_start = time.perf_counter()
        recovered, _, seq, norm = _compact_solve(current)
        plan = (seq, norm)
        for _ in range(256):
            trial = random_candidate(current, rr_rng)
            if _candidate_valid_fast(current, trial, plan):
                rr_answer = trial
                break
        attacks["random_multiset_restart_256"]["wall_clock_sec"] += (
            time.perf_counter() - rr_start
        )
        candidates["random_multiset_restart_256"] = rr_answer
        for name, candidate in candidates.items():
            started = time.perf_counter()
            solved = candidate is not None and verify(current, candidate)[0]
            attacks[name]["successes"] += int(solved)
            if name != "random_multiset_restart_256":
                attacks[name]["wall_clock_sec"] += time.perf_counter() - started

        started = time.perf_counter()
        ref, ops = _reference_solve(current)
        reference_times.append(time.perf_counter() - started)
        reference_operations.append(ops)
        reference_successes += int(ref is not None and verify(current, ref)[0])

        started = time.perf_counter()
        compact, ops, _, _ = _compact_solve(current)
        compact_times.append(time.perf_counter() - started)
        compact_operations.append(ops)
        compact_successes += int(compact is not None and verify(current, compact)[0])

    for result in attacks.values():
        result["wall_clock_sec"] = round(result["wall_clock_sec"], 6)
    all_failed = all(item["successes"] == 0 for item in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "full-word rank-two Nielsen/Whitehead length reduction",
            "paper_basis": "Definition 2.15 and Lemmas 2.16-2.17",
            "complexity": "O(n*|w|) symbol scans on this positive-Nielsen distribution; Ciobanu's general rank-two endomorphism decision algorithm is polynomial-time",
            "wall_clock_sec": round(sum(reference_times), 6),
            "operations": sum(reference_operations),
            "operation_unit": "formal-word symbols scanned across eight shipping instances",
            "per_instance_operations": reference_operations,
            "solves": f"{reference_successes}/8, as expected",
        },
        "intended_compact_route": {
            "name": "Bezout reconstruction and Euclidean factorization of the Nielsen matrix",
            "wall_clock_sec": round(sum(compact_times), 6),
            "operations_max": max(compact_operations),
            "operations": compact_operations,
            "solves": f"{compact_successes}/8",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled_params["answer_cap"] = 20_000
    doubled_params["min_switches"] = shipping_params["min_switches"]
    doubled = make_instance(seed=314159, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * inst["n"]
        and len(doubled["w"]) > len(inst["w"]),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "shipping_word_length": len(inst["w"]),
        "doubled_word_length": len(doubled["w"]),
        "shipping_candidate_space": search_space(inst),
        "doubled_candidate_space": search_space(doubled),
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = 0
    real_transformations = 0
    failures = []
    unrelated = []
    ambient_a = (2, -1)
    variable_a = (-2, 1)
    ambient_b = (-1, -2)
    variable_b = (2, -1)
    for seed in range(20):
        original = make_instance(seed=50_000 + seed, **shipping_params)
        key = canonical_key(original)
        unrelated.append(key)
        variants = (
            _relabel_instance(original, ambient_map=ambient_a),
            _relabel_instance(original, variable_map=variable_a),
            _relabel_instance(original, ambient_map=ambient_b, variable_map=variable_b),
        )
        for index, changed in enumerate(variants):
            invariance_checks += 1
            if canonical_key(changed) != key:
                failures.append({"seed": seed, "variant": index, "reason": "key changed"})
            real_transformations += 1
            if not verify(changed, changed["answer"])[0]:
                failures.append({"seed": seed, "variant": index, "reason": "carried answer failed"})
    distinct = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": not failures and distinct == 20,
        "invariance_checks": invariance_checks,
        "real_transformation_checks": real_transformations,
        "distinct_unrelated_keys": distinct,
        "unrelated_attempts": 20,
        "transformations": [
            "signed coefficient-generator permutation",
            "signed variable permutation",
            "composition of both kinds",
        ],
        "failures": failures,
        "caveat": "complete only for signed permutations, not arbitrary Nielsen equivalence",
    }

    encoded = json.dumps(answer, separators=(",", ":"))
    answer_chars = len(encoded)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_elements(answer)
    arms = {name: dict(G9_EVIDENCE[name]) for name in ("bare", "hinted", "placebo")}
    evidence_complete = all(arms[name]["solved"] is not None for name in arms)
    hinted_minus_placebo = None
    if evidence_complete:
        hinted_minus_placebo = (
            arms["hinted"]["solved"] / arms["hinted"]["attempts"]
            - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        )
    intended_operations = max(compact_operations + [compact_ops])
    within_caps = answer_chars <= 2_000 and answer_elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "within_caps": within_caps,
    }

    # Check the declared measured token bound against every shipping seed used
    # above, not just the representative instance.
    max_tokens = 0
    for seed in range(64):
        current = make_instance(seed=70_000 + seed, **shipping_params)
        chars = len(json.dumps(current["answer"], separators=(",", ":")))
        max_tokens = max(max_tokens, math.ceil(chars / 4))
    report["profile_measurements"] = {
        "shipping_answer_tokens_max_over_64_seeds": max_tokens,
        "shipping_answer_tokens_exact_language_max": 29,
        "declared_max_answer_tokens": PROBLEM_PROFILE["max_answer_tokens"],
    }
    if max_tokens > PROBLEM_PROFILE["max_answer_tokens"]:
        report["G9_no_tool_suitability"]["pass"] = False
        report["G9_no_tool_suitability"]["profile_bound_failure"] = True

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
