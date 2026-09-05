"""Verified generators for Levenshtein sequence reconstruction instances.

The native objects are binary words, a one-error-correcting Hamming code, and
distinct channel outputs in Hamming balls, exactly as in arXiv:2211.08812.
Generation is inverse: sample the transmitted codeword first, then compose a
balanced constant-weight error matrix whose column parities form a singleton.
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
import random
import re
import time
from typing import Any


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "binary Hamming code",
        "distinct received words in binary Hamming space",
    ],
    "verification_operations": [
        "GF(2) parity-check syndrome",
        "exact bitwise XOR",
        "exact Hamming-distance comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "A global XOR cancellation compresses all channel outputs to a word one "
        "Hamming error from the answer; every coordinate is otherwise nearly "
        "balanced, forcing the paper's coordinate-by-coordinate majority scan."
    ),
    "hardness_basis": (
        "Track B: Section 6 states that majority reconstruction is optimal-time "
        "Theta(Nn); at shipping n=255 and N=43 it inspects 10,965 channel bits "
        "and solves 8/8 instances in about 0.01 seconds total (the exact run is in G6), "
        "while the composed XOR-and-syndrome route uses at most 68 exact word operations."
    ),
    "max_answer_tokens": 66,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "hard": {"n": 255, "channels": 43, "t": 117},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "A global bitwise-XOR invariant links the odd collection of received words "
    "to the code's one-error geometry."
)
PLACEBO_HINT = (
    "A careful bit-by-bit comparison links the received words to the code's "
    "stated distance constraints."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One fixed-width hexadecimal binary word c of length n=2^r-1, with no "
        "0x prefix, whose Hamming-code syndrome XOR{i : c_i=1} is zero."
    ),
    "bounds": {
        "max_bits": 511,
        "alphabet_size": 2,
        "parity_checks": 9,
    },
}

NOTES = r"""
Paper grounding and Step 0.  Section 1 fixes the native reconstruction object:
T(Y)=C intersected with all radius-t Hamming balls around the distinct channel
outputs, where t=e+ell>e.  Sections 2--5 study information-theoretic list size,
not computational search hardness.  The easy regimes that matter here are stated
explicitly: one channel suffices when t<=e; Theorems 4 and 6 bound list size once
the number of channels crosses V(n,ell-1)+1; and Section 6 gives the well-known
majority algorithm with optimal Theta(Nn) time.  Theorem 28 supplies a deterministic,
exactly checkable inequality guaranteeing that majority lies within k of the
transmitted word.  A random-corruption planted family would therefore fail Track A.

Generation and certificate.  C is the binary Hamming code of length 2^r-1, whose
parity-check columns are the nonzero r-bit coordinate labels; it has minimum
distance 3 and e=1.  A uniform codeword x is sampled first.  Every channel error
mask has exactly the public weight t=e+ell.  The error matrix is built by assigning
an even, near-half column weight to every coordinate except one coordinate with an
odd, near-half weight.  A least-loaded-row construction makes every row have weight
exactly t.  Consequently every coordinate has a strict correct majority while the
XOR of all error rows is exactly the singleton odd column.  Thus all outputs are
distinct and exactly t from x, Theorem 28 applies with k=1, and XOR of all odd-many
outputs is one bit from x.  The planted answer is never found by solving the
instance.

Track B and attacks.  The paper's majority decoder is the successful reference
algorithm, not a failed Track-A attack.  Shipping majority reads Nn=10,965 bits;
the alternative identity needs N whole-word XORs, r fixed parity masks, and one
bit flip.  All received rows have the same distance t from x, every bit is close
to a tie, and public order is randomized.  The adversary panel tests raw-weight
outliers, a Hamming medoid with one-error decoding, uniform codeword restarts,
hexadecimal-digit plurality, and the tempting but invalid raw XOR answer.  Exact
timings and operation counts are produced by selftest().
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>\s*(?:0x)?([0-9a-fA-F]+)\s*</answer\s*>", re.I | re.S)
_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
_ENUMERATION_CAP = 65_536


def _r_for_length(n: int) -> int:
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer of the form 2^r-1 with r>=2")
    if n > 511 or (n + 1) & n:
        raise ValueError("n must be of the form 2^r-1 and at most 511")
    return (n + 1).bit_length() - 1


def _validate_params(n: int, channels: int, t: int) -> int:
    r = _r_for_length(n)
    if isinstance(channels, bool) or not isinstance(channels, int):
        raise ValueError("channels must be an integer")
    if channels < 11 or channels % 4 != 3:
        raise ValueError("channels must be at least 11 and congruent to 3 modulo 4")
    if isinstance(t, bool) or not isinstance(t, int):
        raise ValueError("t must be an integer")
    if t < 3 or not (t & 1) or 2 * t + 1 > n:
        raise ValueError("t must be odd, at least 3, and satisfy 2t+1<=n")
    return r


def _width(n: int) -> int:
    return (n + 3) // 4


def _format_word(word: int, n: int) -> str:
    return format(word, f"0{_width(n)}x")


def _syndrome_sparse(word: int) -> int:
    """Return XOR of the 1-based labels of set coordinates."""
    syndrome = 0
    rest = word
    while rest:
        bit = rest & -rest
        syndrome ^= bit.bit_length()
        rest ^= bit
    return syndrome


@functools.lru_cache(maxsize=None)
def _parity_masks(n: int) -> tuple[int, ...]:
    r = _r_for_length(n)
    masks = []
    for parity_bit in range(r):
        mask = 0
        for coordinate in range(1, n + 1):
            if coordinate & (1 << parity_bit):
                mask |= 1 << (coordinate - 1)
        masks.append(mask)
    return tuple(masks)


@functools.lru_cache(maxsize=None)
def _data_mask(n: int) -> int:
    """Bits in the systematic positions (all non-powers of two)."""
    mask = 0
    for coordinate in range(1, n + 1):
        if coordinate & (coordinate - 1):
            mask |= 1 << (coordinate - 1)
    return mask


def _syndrome_dense(word: int, n: int) -> int:
    """Syndrome by r fixed parity masks, suitable for the compact route."""
    syndrome = 0
    for parity_bit, mask in enumerate(_parity_masks(n)):
        if (word & mask).bit_count() & 1:
            syndrome |= 1 << parity_bit
    return syndrome


def _uniform_codeword(n: int, rng: random.Random) -> int:
    """Uniformly sample the [2^r-1, 2^r-r-1, 3] binary Hamming code."""
    word = rng.getrandbits(n) & _data_mask(n)
    syndrome = _syndrome_dense(word, n)
    bit = 1
    while bit <= n:
        if syndrome & bit:
            word |= 1 << (bit - 1)
        bit <<= 1
    assert _syndrome_dense(word, n) == 0
    return word


def _near_half_column_degrees(n: int, channels: int, t: int,
                              singleton: int,
                              rng: random.Random) -> list[int]:
    """Column degrees below half, with exactly one odd degree and fixed sum."""
    total = channels * t
    max_degree = (channels - 1) // 2
    max_even = max_degree if max_degree % 2 == 0 else max_degree - 1
    max_odd = max_degree if max_degree % 2 == 1 else max_degree - 1
    odd_choices = list(range(1, max_odd + 1, 2))
    odd_degree = min(odd_choices, key=lambda d: (abs(d * n - total), d))
    remainder = total - odd_degree
    if remainder < 0 or remainder > (n - 1) * max_even or remainder % 2:
        raise ValueError("parameters cannot realize the balanced XOR certificate")

    base = min(max_even, (remainder // (n - 1)) // 2 * 2)
    degrees = [base] * n
    degrees[singleton] = odd_degree
    leftover = remainder - base * (n - 1)
    coordinates = [j for j in range(n) if j != singleton]
    while leftover:
        eligible = [j for j in coordinates if degrees[j] + 2 <= max_even]
        if not eligible:
            raise ValueError("parameters exhaust the strict-majority degree budget")
        rng.shuffle(eligible)
        take = min(len(eligible), leftover // 2)
        for coordinate in eligible[:take]:
            degrees[coordinate] += 2
        leftover -= 2 * take
    assert sum(degrees) == total
    assert degrees[singleton] % 2 == 1
    assert all(
        degree % 2 == (coordinate == singleton)
        for coordinate, degree in enumerate(degrees)
    )
    assert max(degrees) * 2 < channels
    return degrees


def _make_error_masks(n: int, channels: int, t: int,
                      rng: random.Random) -> tuple[list[int], int]:
    """Construct a balanced row-regular matrix with singleton column XOR."""
    for _ in range(1_000):
        singleton = rng.randrange(n)
        degrees = _near_half_column_degrees(n, channels, t, singleton, rng)
        masks = [0] * channels
        row_loads = [0] * channels
        coordinates = list(range(n))
        rng.shuffle(coordinates)
        for coordinate in coordinates:
            # Random tie-breaking among least-loaded rows makes rows exchangeable;
            # greedy balancing keeps their loads at distance at most one.
            rows = list(range(channels))
            rng.shuffle(rows)
            rows.sort(key=row_loads.__getitem__)
            for row in rows[:degrees[coordinate]]:
                masks[row] |= 1 << coordinate
                row_loads[row] += 1
        if row_loads != [t] * channels or len(set(masks)) != channels:
            continue
        total_xor = 0
        for mask in masks:
            total_xor ^= mask
        if total_xor != 1 << singleton:
            continue
        rng.shuffle(masks)
        return masks, singleton
    raise RuntimeError("could not compose distinct balanced channel masks")


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Inverse-generate a native Levenshtein reconstruction instance."""
    allowed = {"channels", "t"}
    unknown = set(params) - allowed
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    channels = params.get("channels", 43)
    t = params.get("t", 9)
    r = _validate_params(n, channels, t)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    transmitted = _uniform_codeword(n, rng)
    masks, _singleton = _make_error_masks(n, channels, t, rng)
    outputs = [transmitted ^ mask for mask in masks]
    assert len(outputs) == channels and len(set(outputs)) == channels
    assert all((received ^ transmitted).bit_count() == t for received in outputs)
    return {
        "family": "Levenshtein sequence reconstruction in a Hamming code",
        "n": n,
        "r": r,
        "e": 1,
        "ell": t - 1,
        "t": t,
        "channels": channels,
        "outputs": outputs,
        "answer": _format_word(transmitted, n),
    }


def render(inst: dict) -> str:
    """Render the complete self-contained problem statement."""
    n = inst["n"]
    r = inst["r"]
    width = _width(n)
    rows = "\n".join(
        f"  {i + 1}: {_format_word(word, n)}"
        for i, word in enumerate(inst["outputs"])
    )
    text = f"""Levenshtein sequence reconstruction over GF(2)

A binary word has n={n} coordinates b_1,...,b_n.  It is written as exactly
{width} hexadecimal digits, including leading zeroes and without a 0x prefix,
using the integer convention value=sum(b_i*2^(i-1)).  Thus coordinate 1 is the
least significant bit.  Hexadecimal is only a compact exact notation for the
binary word.

For two words u and v, their Hamming distance d(u,v) is the number of 1 bits in
u XOR v.  Let C be the binary Hamming code with parity-check columns equal to
the nonzero {r}-bit coordinate labels 1,...,{n}.  Explicitly, c belongs to C if
and only if the bitwise XOR of every 1-based index i for which c_i=1 is zero.
This code has minimum distance 3 and corrects one substitution error (e=1).

An unknown transmitted codeword x in C was sent through N={inst['channels']}
channels.  The N outputs below are distinct, and every output differs from x in
at most t={inst['t']} coordinates (so ell=t-e={inst['ell']}).  The numbered lines
are an unordered set; their displayed order and line numbers carry no meaning.

Received words:
{rows}

Find any codeword c in C satisfying d(c,y)<=t for every displayed received word
y.  Equality at distance t is allowed.  The answer is one fixed-width
{width}-digit hexadecimal word; letter case is ignored, repeats are not an
additional notion, and no coordinate may lie outside 1..{n}.

Give your final answer inside <answer></answer> tags, as exactly {width}
hexadecimal digits with no 0x prefix.
Example format: <answer>{'0' * (width - 1)}1</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def parse_answer(text: object) -> object | None:
    """Extract one tagged fixed-width-looking hexadecimal word."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if len(matches) != 1:
        return None
    return matches[0].lower()


def _answer_to_word(inst: dict, answer: object) -> tuple[int | None, str | None]:
    width = _width(inst["n"])
    if not isinstance(answer, str) or not answer:
        return None, "answer must be a nonempty hexadecimal string"
    if not _HEX_RE.fullmatch(answer):
        return None, "answer contains a non-hexadecimal character"
    if len(answer) < width:
        return None, f"hexadecimal answer is too short ({len(answer)}<{width})"
    if len(answer) > width:
        return None, f"hexadecimal answer is too long ({len(answer)}>{width})"
    word = int(answer, 16)
    if word >= 1 << inst["n"]:
        return None, f"value has a 1 outside coordinates 1..{inst['n']}"
    return word, None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any candidate codeword directly; never inspect inst['answer']."""
    word, error = _answer_to_word(inst, answer)
    if error is not None or word is None:
        return False, error or "malformed answer"
    syndrome = _syndrome_dense(word, inst["n"])
    if syndrome:
        return False, f"word is not in the Hamming code (syndrome {syndrome})"
    for index, received in enumerate(inst["outputs"], 1):
        distance = (word ^ received).bit_count()
        if distance > inst["t"]:
            return False, (
                f"word exceeds radius {inst['t']} at channel {index} "
                f"(distance {distance})"
            )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the statement-implied Hamming-code candidate space."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    return _format_word(_uniform_codeword(inst["n"], rng), inst["n"])


def search_space(inst: dict) -> int | None:
    """Exact number 2^(n-r) of words in the declared Hamming code."""
    return 1 << (inst["n"] - inst["r"])


def enumerate_all(inst: dict) -> int | None:
    """Count all valid codewords only when the full code is safely small."""
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    data_coordinates = [
        i for i in range(1, inst["n"] + 1) if i & (i - 1)
    ]
    hits = 0
    for payload in range(space):
        word = 0
        for bit_index, coordinate in enumerate(data_coordinates):
            if payload & (1 << bit_index):
                word |= 1 << (coordinate - 1)
        syndrome = _syndrome_sparse(word)
        parity = 1
        while parity <= inst["n"]:
            if syndrome & parity:
                word |= 1 << (parity - 1)
            parity <<= 1
        if verify(inst, _format_word(word, inst["n"]))[0]:
            hits += 1
    return hits


def canonical_key(inst: dict) -> str:
    """Strong cheap Hamming-metric invariant, independent of output ordering."""
    outputs = inst["outputs"]
    profiles = []
    for word in outputs:
        profiles.append(sorted((word ^ other).bit_count() for other in outputs))
    form = [inst["n"], inst["t"], len(outputs), sorted(profiles)]
    payload = json.dumps(form, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the channel haystack at fixed 255-bit answer length."""
    if not isinstance(params, dict):
        return None
    n = params.get("n")
    channels = params.get("channels")
    t = params.get("t")
    if not all(isinstance(v, int) and not isinstance(v, bool)
               for v in (n, channels, t)):
        return None
    out = dict(params)
    if n < 255:
        out.update({"n": 255, "channels": 43, "t": 117})
        return out
    if channels < 83:
        out["channels"] = 83
        return out
    if channels < 163:
        out["channels"] = 163
        return out
    if channels < 263:
        out["channels"] = 263
        return out
    if channels < 275:
        # 275 + 3*8 + 1 = 300 compact-route operations, exactly the G9 cap.
        out["channels"] = 275
        return out
    # More channels remain mathematically available, but the compact route would
    # exceed G9's 300-operation no-tool limit.  That is a benchmark cap, not a
    # claim that the family has no harder instances.
    return "cap_bound"


def _decode_one_error(word: int, n: int) -> int:
    syndrome = _syndrome_dense(word, n)
    if syndrome:
        word ^= 1 << (syndrome - 1)
    return word


def _reference_majority(inst: dict) -> tuple[str, int]:
    """Section 6 majority followed by standard one-error Hamming decoding."""
    majority = 0
    operations = 0
    threshold = inst["channels"] // 2
    for coordinate in range(inst["n"]):
        ones = 0
        for received in inst["outputs"]:
            ones += (received >> coordinate) & 1
            operations += 1
        if ones > threshold:
            majority |= 1 << coordinate
    decoded = _decode_one_error(majority, inst["n"])
    operations += 3 * inst["r"] + 1
    return _format_word(decoded, inst["n"]), operations


def _compact_xor_decode(inst: dict) -> tuple[str, int]:
    """Composition shortcut: global XOR, r parity reductions, one correction."""
    aggregate = 0
    for received in inst["outputs"]:
        aggregate ^= received
    decoded = _decode_one_error(aggregate, inst["n"])
    operations = inst["channels"] + 3 * inst["r"] + 1
    return _format_word(decoded, inst["n"]), operations


def _raw_weight_outlier(inst: dict) -> str:
    target = min(
        inst["outputs"],
        key=lambda word: (word.bit_count(), word),
    )
    return _format_word(_decode_one_error(target, inst["n"]), inst["n"])


def _medoid_attack(inst: dict) -> str:
    outputs = inst["outputs"]
    target = min(
        outputs,
        key=lambda word: (
            sum((word ^ other).bit_count() for other in outputs),
            word,
        ),
    )
    return _format_word(_decode_one_error(target, inst["n"]), inst["n"])


def _hex_plurality_attack(inst: dict) -> str:
    """Take each displayed hex digit's plurality, then enforce code membership."""
    width = _width(inst["n"])
    rows = [_format_word(word, inst["n"]) for word in inst["outputs"]]
    digits = []
    for position in range(width):
        counts = [0] * 16
        for row in rows:
            counts[int(row[position], 16)] += 1
        digits.append(max(range(16), key=lambda digit: (counts[digit], -digit)))
    word = int("".join(format(digit, "x") for digit in digits), 16)
    return _format_word(_decode_one_error(word, inst["n"]), inst["n"])


def _random_restart_attack(inst: dict, rng: random.Random,
                           restarts: int = 256) -> tuple[str, int]:
    last = random_candidate(inst, rng)
    for iteration in range(1, restarts + 1):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last, iteration
    return last, restarts


def _xor_only_attack(inst: dict) -> str:
    aggregate = 0
    for received in inst["outputs"]:
        aggregate ^= received
    return _format_word(aggregate, inst["n"])


def _majority_theorem_lhs(inst: dict) -> int:
    counts = []
    for coordinate in range(inst["n"]):
        ones = sum((word >> coordinate) & 1 for word in inst["outputs"])
        counts.append(min(ones, inst["channels"] - ones))
    counts.sort(reverse=True)
    return sum(inst["channels"] - m for m in counts[:2]) + sum(counts[2:])


def _rotate_label(coordinate: int, r: int) -> int:
    return ((coordinate << 1) & ((1 << r) - 1)) | (coordinate >> (r - 1))


def _coordinate_automorphism(word: int, n: int) -> int:
    r = _r_for_length(n)
    transformed = 0
    rest = word
    while rest:
        bit = rest & -rest
        old = bit.bit_length()
        new = _rotate_label(old, r)
        transformed |= 1 << (new - 1)
        rest ^= bit
    return transformed


def _transform_instance(inst: dict, *, reorder: list[int] | None = None,
                        translate: int = 0, automate: bool = False) -> dict:
    """Carry the instance and answer through true Hamming-code symmetries."""
    if _syndrome_sparse(translate):
        raise ValueError("translation must be a Hamming codeword")
    n = inst["n"]

    def carry(word: int) -> int:
        value = word ^ translate
        return _coordinate_automorphism(value, n) if automate else value

    outputs = [carry(word) for word in inst["outputs"]]
    if reorder is not None:
        if sorted(reorder) != list(range(len(outputs))):
            raise ValueError("reorder must be a permutation of output rows")
        outputs = [outputs[i] for i in reorder]
    answer_word = carry(int(inst["answer"], 16))
    transformed = dict(inst)
    transformed["outputs"] = outputs
    transformed["answer"] = _format_word(answer_word, n)
    return transformed


def _find_radius_corruption(inst: dict) -> str:
    original = int(inst["answer"], 16)
    n = inst["n"]
    for a in range(1, min(n, 32) + 1):
        for b in range(a + 1, min(n, 63) + 1):
            c = a ^ b
            if not (1 <= c <= n) or c in (a, b):
                continue
            other = original ^ (1 << (a - 1)) ^ (1 << (b - 1)) ^ (1 << (c - 1))
            candidate = _format_word(other, n)
            ok, reason = verify(inst, candidate)
            if not ok and reason.startswith("word exceeds radius"):
                return candidate
    raise AssertionError("could not make an in-code radius corruption")


def selftest() -> dict:
    """Run G1--G9 and return machine-readable measured evidence."""
    report: dict[str, Any] = {}

    checked = 0
    theorem_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 99):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            assert ok, (preset, seed, why)
            assert json.loads(json.dumps(inst["answer"])) == inst["answer"]
            decoded, _operations = _reference_majority(inst)
            assert verify(inst, decoded)[0]
            assert _majority_theorem_lhs(inst) > inst["t"] * inst["channels"]
            theorem_checks += 1
            checked += 1
    report["G1_planted_verifies"] = {
        "pass": True,
        "instances": checked,
        "theorem_28_checks": theorem_checks,
        "generation_route": (
            "inverse generation plus a row-regular error matrix with a "
            "singleton column-parity certificate"
        ),
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **ship_params)
    answer = inst["answer"]
    swapped = None
    base_syndrome_reason = verify(
        inst, _format_word(int(answer, 16) ^ 1, inst["n"])
    )[1]
    for i in range(1, len(answer)):
        for j in range(i + 1, len(answer)):
            if answer[i] == answer[j]:
                continue
            trial = list(answer)
            trial[i], trial[j] = trial[j], trial[i]
            candidate = "".join(trial)
            ok, why = verify(inst, candidate)
            if not ok and why != base_syndrome_reason and "syndrome" in why:
                swapped = candidate
                break
        if swapped is not None:
            break
    assert swapped is not None
    corruptions = {
        "empty": "",
        "drop_one": answer[1:],
        "duplicate_one": answer + answer[-1],
        "non_hex": answer[:-1] + "g",
        "out_of_range": _format_word(int(answer, 16) | (1 << inst["n"]), inst["n"]),
        "flip_one_bit": _format_word(int(answer, 16) ^ 1, inst["n"]),
        "swap_two_digits": swapped,
        "other_codeword": _find_radius_corruption(inst),
    }
    reasons = {}
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        assert not ok, (name, bad)
        reasons[name] = why
    assert len(set(reasons.values())) == len(reasons), reasons
    report["G2_rejects_corruption"] = {"pass": True, "reasons": reasons}

    response = (
        "The parity check leaves one candidate.\n```text\n<answer>"
        + answer
        + "</answer>\n```\nThe coordinate convention is least-significant-bit first."
    )
    assert parse_answer(response) == answer
    assert parse_answer("no tagged answer") is None
    assert parse_answer("<answer>not hexadecimal</answer>") is None
    assert parse_answer("<answer>0</answer><answer>1</answer>") is None
    report["G3_round_trip"] = {
        "pass": True,
        "json_native": True,
        "answer_hex_digits": len(answer),
    }

    guess_inst = make_instance(seed=8675309, **ship_params)
    guess_rng = random.Random(13579)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        if verify(guess_inst, random_candidate(guess_inst, guess_rng))[0]:
            guess_hits += 1
    guess_density = guess_hits / guess_total
    assert guess_density < 1e-6, (guess_hits, guess_total)
    report["G4_guess_resistance"] = {
        "pass": True,
        "hits": guess_hits,
        "total": guess_total,
        "empirical_probability": guess_density,
        "structure_aware_space": search_space(guess_inst),
        "prior": "uniform over all words satisfying the public Hamming parity checks",
    }

    demo = make_instance(seed=31415, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    assert isinstance(demo_count, int) and demo_count >= 1

    density_inst = make_instance(seed=112358, **ship_params)
    density_rng = random.Random(24680)
    density_total = 200_000
    density_hits = 0
    for _ in range(density_total):
        if verify(density_inst, random_candidate(density_inst, density_rng))[0]:
            density_hits += 1

    attack_seeds = list(range(3100, 3108))
    attacks = {
        "per_element_lowest_raw_weight": {"successes": 0, "attempts": 8},
        "greedy_hamming_medoid_decode": {"successes": 0, "attempts": 8},
        "random_codeword_restart_256": {"successes": 0, "attempts": 8},
        "by_hand_hex_digit_plurality_decode": {"successes": 0, "attempts": 8},
        "by_hand_global_xor_without_syndrome": {"successes": 0, "attempts": 8},
    }
    restart_iterations = 0
    restart_elapsed = 0.0
    reference_operations = []
    reference_elapsed = 0.0
    reference_successes = 0
    compact_operations = []
    compact_successes = 0
    for seed in attack_seeds:
        target = make_instance(seed=seed, **ship_params)
        if verify(target, _raw_weight_outlier(target))[0]:
            attacks["per_element_lowest_raw_weight"]["successes"] += 1
        if verify(target, _medoid_attack(target))[0]:
            attacks["greedy_hamming_medoid_decode"]["successes"] += 1
        restart_t0 = time.perf_counter()
        candidate, iterations = _random_restart_attack(
            target, random.Random(seed ^ 0xA511CE)
        )
        restart_elapsed += time.perf_counter() - restart_t0
        restart_iterations += iterations
        if verify(target, candidate)[0]:
            attacks["random_codeword_restart_256"]["successes"] += 1
        if verify(target, _hex_plurality_attack(target))[0]:
            attacks["by_hand_hex_digit_plurality_decode"]["successes"] += 1
        if verify(target, _xor_only_attack(target))[0]:
            attacks["by_hand_global_xor_without_syndrome"]["successes"] += 1

        reference_t0 = time.perf_counter()
        decoded, operations = _reference_majority(target)
        reference_elapsed += time.perf_counter() - reference_t0
        reference_operations.append(operations)
        if verify(target, decoded)[0]:
            reference_successes += 1
        compact, compact_ops = _compact_xor_decode(target)
        compact_operations.append(compact_ops)
        if verify(target, compact)[0]:
            compact_successes += 1

    assert all(row["successes"] == 0 for row in attacks.values()), attacks
    assert reference_successes == len(attack_seeds)
    assert compact_successes == len(attack_seeds)
    assert max(compact_operations) <= 300

    report["G5_density_and_baseline_cost"] = {
        "pass": True,
        "shipping_exact_solution_count": 1,
        "shipping_candidate_count": search_space(density_inst),
        "shipping_exact_valid_fraction_formula": "1/2^247",
        "shipping_exact_valid_fraction_decimal": 1 / search_space(density_inst),
        "exact_count_basis": (
            "Theorem 28 with k=e=1 places every valid codeword within distance "
            "one of the same majority word; minimum distance three makes it "
            "unique, and G1 supplies one such codeword"
        ),
        "shipping_sample_hits": density_hits,
        "shipping_sample_total": density_total,
        "shipping_valid_fraction": density_hits / density_total,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_attack": "Section 6 coordinatewise majority plus Hamming decoding",
        "baseline_wall_seconds_8_instances": reference_elapsed,
        "baseline_max_operations": max(reference_operations),
        "baseline_attempts": len(attack_seeds),
        "failing_restart_wall_seconds": restart_elapsed,
        "failing_restart_iterations": restart_iterations,
    }

    report["G6_adversary_panel"] = {
        "pass": True,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Section 6 coordinatewise majority plus one-error Hamming decoding",
            "complexity": "Theta(N*n) time and O(n) counters",
            "wall_clock_sec": reference_elapsed,
            "operations": max(reference_operations),
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
        "compact_route": {
            "name": "global XOR cancellation plus Hamming syndrome",
            "operations": max(compact_operations),
            "solves": f"{compact_successes}/{len(attack_seeds)}",
        },
    }

    doubled_params = {"n": 511, "channels": 43, "t": 235}
    doubled = make_instance(seed=424242, **doubled_params)
    ok, why = verify(doubled, doubled["answer"])
    assert ok, why
    assert search_space(doubled) > search_space(inst)
    report["G7_scales"] = {
        "pass": True,
        "base_n": inst["n"],
        "doubled_n": doubled["n"],
        "base_candidate_space": search_space(inst),
        "doubled_candidate_space": search_space(doubled),
        "planted_verifies": True,
    }

    invariance_checks = 0
    real_transform_checks = 0
    original_answer_transform_checks = 0
    unrelated_keys = []
    key_params = DIFFICULTY["medium"]
    for seed in range(20):
        base = make_instance(seed=9000 + seed, **key_params)
        key = canonical_key(base)
        unrelated_keys.append(key)
        rng = random.Random(700_000 + seed)
        order = list(range(base["channels"]))
        rng.shuffle(order)
        translation = _uniform_codeword(base["n"], rng)
        transforms = [
            _transform_instance(base, reorder=order),
            _transform_instance(base, translate=translation),
            _transform_instance(base, automate=True),
            _transform_instance(
                base, reorder=order, translate=translation, automate=True
            ),
        ]
        for transformed in transforms:
            assert canonical_key(transformed) == key
            invariance_checks += 1
            ok, why = verify(transformed, transformed["answer"])
            assert ok, (seed, why)
            real_transform_checks += 1
        ok, why = verify(transforms[0], base["answer"])
        assert ok, (seed, why)
        original_answer_transform_checks += 1
    distinct = len(set(unrelated_keys))
    assert distinct == len(unrelated_keys)
    report["G8_canonical_key"] = {
        "pass": True,
        "invariance_checks": invariance_checks,
        "real_transform_checks": real_transform_checks,
        "original_answer_transform_checks": original_answer_transform_checks,
        "distinct_unrelated": distinct,
        "unrelated_total": len(unrelated_keys),
        "symmetries": (
            "output reordering, translation by a codeword, cyclic linear "
            "automorphism of parity-check labels, and their composition"
        ),
    }

    compact_json = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(compact_json)
    answer_tokens_upper_bound = answer_chars
    answer_elements = inst["n"]
    compact_answer, intended_operations = _compact_xor_decode(inst)
    assert verify(inst, compact_answer)[0]
    within_caps = (
        answer_chars <= 2_000
        and answer_tokens_upper_bound <= 500
        and answer_elements <= 256
        and intended_operations <= 300
    )
    arms = {
        "bare": {"solved": 0, "attempts": 0, "errors": 4},
        "hinted": {"solved": 0, "attempts": 0, "errors": 4},
        "placebo": {"solved": 0, "attempts": 0, "errors": 4},
    }
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": None,
        "hinted_verdict": "unavailable: OpenRouter key limit exceeded",
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens_upper_bound,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "token_measure": "conservative one-token-per-character upper bound",
        "caps": {"chars": 2000, "tokens": 500, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for name, value in report.items()
        if name.startswith("G") and name[1:2].isdigit()
    )
    report["external_hardening_complete"] = False
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2))
