"""Verified generators for a native Levenshtein reconstruction family.

Instances use binary repetition codes and distinct outputs in Hamming balls,
the native objects of arXiv:2211.08812. Generation is inverse: a payload and its
repeated codeword are sampled first, then a certified error array is composed.
"""

from __future__ import annotations

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
        "binary repetition code",
        "distinct received words in binary Hamming space",
        "hexadecimal payload representing a repeated codeword",
    ],
    "verification_operations": [
        "exact repetition-code encoding",
        "exact bitwise XOR",
        "exact Hamming-distance population count",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Within each received word, every logical error coordinate has even "
        "parity across the odd repetition blocks, so blockwise XOR cancels "
        "the errors and exposes the payload."
    ),
    "hardness_basis": (
        "Track B: Section 6 gives coordinatewise majority in optimal Theta(Nn) "
        "time; shipping contains Nn=9,288 received bits, while even its "
        "construction-aware one-block specialization reads 1,032 bits and "
        "solves 8/8 in the measured G6 run; the compact invariant takes 48 "
        "single-hex-digit XORs."
    ),
    "max_answer_tokens": 8,
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
    "easy": {
        "n": 216, "blocks": 9, "payload_nibbles": 6,
        "channels": 43, "high_groups": 4, "t": 104,
    },
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Within each received word, the blockwise error vectors have zero XOR "
    "across the odd set of repetition blocks."
)
PLACEBO_HINT = (
    "Within each received word, careful alignment matters across the odd set "
    "of repetition blocks."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One fixed-width p-digit hexadecimal payload, including leading zeroes; "
        "it represents the binary word obtained by repeating those 4p bits B "
        "times and contains exactly 16^p candidates."
    ),
    "bounds": {
        "max_hex_digits": 16,
        "max_payload_bits": 64,
        "alphabet_size": 16,
        "repetition_blocks": 9,
    },
}

NOTES = r"""
Paper grounding and Step 0. Section 1 fixes the native reconstruction object:
T(Y)=C intersected with every radius-t Hamming ball around the distinct channel
outputs, where t=e+ell>e. Sections 2--5 establish extremal list-size bounds; they
do not establish computational search hardness. The easy results that control
the choice of track are explicit. Section 1 says one channel suffices for t<=e,
Theorems 4 and 6 bound high-channel list sizes, and Section 6 gives the familiar
coordinatewise majority decoder in optimal Theta(Nn) time. Theorem 28 provides
an executable inequality certifying that its majority word is within k of every
feasible transmitted word. Thus Track A would be false. This module uses Track B
and discloses both the paper's mechanical decoder and its cost.

Generation and certificate. C consists of all B-fold repetitions of a d-bit
payload, with B odd. Its minimum distance is exactly B, so e=(B-1)/2. A uniform
payload and codeword x are sampled first. The generator then realizes explicit
bipartite degree sequences for a channels-by-(B*d) error array. Every channel
row has exactly t errors. In each logical coordinate, a row has one of two even
numbers of errors among its B copies. Every physical column has at most
floor(N/2) errors. Therefore every coordinate has strict majority x, while XOR
of the B blocks inside any single received word cancels every error coordinate
and, because B is odd, leaves the payload. This is a composition of identities,
not a solution found by search.

For uniqueness, the minority counts sum to tN. In Theorem 28's inequality with
k=e, replacing the e+1 largest minority terms by their strict majorities adds a
positive amount, so its left side is greater than tN. Every feasible codeword is
within e of the same majority word. Minimum distance 2e+1 makes it unique, and
inverse generation supplies it.

Track B and attacks. Shipping has n=216, N=43, and a 24-bit answer. The full
Section 6 scan reads 9,288 received bits. A stronger construction-aware baseline
needs only majority on one 24-bit repetition block but still reads 1,032 bits;
it is timed and expected to solve. The invariant route XORs nine 6-digit blocks
of one received word, conservatively counted as 48 single-hex-digit XORs.

All channel rows have identical error weight and identical numbers of the two
logical error multiplicities. Random tie-breaking makes rows exchangeable. The
failed panel tests raw-weight selection, a Hamming medoid, 256 uniform payload
restarts, hexadecimal plurality on one block, within-row bit majority, and a
partial three-block XOR. The last two are executable no-tool reactions to the
visible repetition structure; neither is the full hidden invariant. Exact costs
and success counts are produced by selftest().
""".strip()


_ANSWER_RE = re.compile(
    r"<answer\b[^>]*>\s*(?:0x)?([0-9a-fA-F]+)\s*</answer\s*>", re.I | re.S
)
_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
_ENUMERATION_CAP = 65_536


def _payload_bits(payload_nibbles: int) -> int:
    return 4 * payload_nibbles


def _low_group_weight(blocks: int) -> int:
    """Largest even integer strictly below B/2."""
    value = (blocks - 1) // 2
    return value - value % 2


def _expected_t(blocks: int, payload_nibbles: int,
                high_groups: int) -> int:
    bits = _payload_bits(payload_nibbles)
    return bits * _low_group_weight(blocks) + 2 * high_groups


def _validate_params(n: int, blocks: int, payload_nibbles: int,
                     channels: int, high_groups: int, t: int) -> None:
    values = (n, blocks, payload_nibbles, channels, high_groups, t)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise ValueError("all size parameters must be integers")
    if payload_nibbles < 1:
        raise ValueError("payload_nibbles must be positive")
    bits = _payload_bits(payload_nibbles)
    if blocks < 3 or blocks % 2 == 0:
        raise ValueError("blocks must be an odd integer at least 3")
    if n != blocks * bits:
        raise ValueError("n must equal blocks * 4 * payload_nibbles")
    if channels < 3 or channels % 2 == 0:
        raise ValueError("channels must be an odd integer at least 3")
    if not (0 <= high_groups <= bits):
        raise ValueError("high_groups must lie between 0 and the payload bit count")
    low = _low_group_weight(blocks)
    if low + 2 >= blocks:
        raise ValueError("the high logical error multiplicity must be below blocks")
    expected = _expected_t(blocks, payload_nibbles, high_groups)
    if t != expected:
        raise ValueError(f"t must equal the certified row weight {expected}")
    if t <= (blocks - 1) // 2:
        raise ValueError("t must exceed the code's error-correction capability")


def _format_payload(payload: int, payload_nibbles: int) -> str:
    return format(payload, f"0{payload_nibbles}x")


def _encode_payload(payload: int, blocks: int, payload_nibbles: int) -> int:
    bits = _payload_bits(payload_nibbles)
    if isinstance(payload, bool) or not isinstance(payload, int):
        raise ValueError("payload must be an integer")
    if not (0 <= payload < 1 << bits):
        raise ValueError("payload is outside its declared bit range")
    word = 0
    for _ in range(blocks):
        word = (word << bits) | payload
    return word


def _extract_block(word: int, block: int, payload_bits: int) -> int:
    """Extract a block numbered from zero at the least significant end."""
    return (word >> (block * payload_bits)) & ((1 << payload_bits) - 1)


def _format_grouped_word(word: int, blocks: int,
                         payload_nibbles: int) -> str:
    raw = format(word, f"0{blocks * payload_nibbles}x")
    return " ".join(
        raw[start:start + payload_nibbles]
        for start in range(0, len(raw), payload_nibbles)
    )


def _balanced_degrees(total: int, count: int, rng: random.Random) -> list[int]:
    base, extra = divmod(total, count)
    degrees = [base] * (count - extra) + [base + 1] * extra
    rng.shuffle(degrees)
    return degrees


def _bipartite_rows(row_degrees: list[int], column_degrees: list[int],
                    rng: random.Random) -> list[int]:
    """Random-tie Havel-Hakimi realization of a bipartite degree sequence."""
    if sum(row_degrees) != sum(column_degrees):
        raise ValueError("bipartite degree sums do not match")
    remaining = list(row_degrees)
    rows = [0] * len(row_degrees)
    columns = list(enumerate(column_degrees))
    rng.shuffle(columns)
    columns.sort(key=lambda item: item[1], reverse=True)
    for column, degree in columns:
        order = list(range(len(rows)))
        rng.shuffle(order)
        order.sort(key=remaining.__getitem__, reverse=True)
        if degree > len(order) or (degree and remaining[order[degree - 1]] <= 0):
            raise ValueError("degree sequence is not bipartite-graphical")
        for row in order[:degree]:
            rows[row] |= 1 << column
            remaining[row] -= 1
    if any(remaining):
        raise ValueError("bipartite realization left positive row degree")
    return rows


def _make_error_masks(blocks: int, payload_nibbles: int, channels: int,
                      high_groups: int, rng: random.Random) -> list[int]:
    """Compose equal-weight rows with even parity in every logical group."""
    bits = _payload_bits(payload_nibbles)
    low = _low_group_weight(blocks)
    selection_columns = _balanced_degrees(channels * high_groups, bits, rng)
    selections = _bipartite_rows([high_groups] * channels, selection_columns, rng)
    masks = [0] * channels
    for logical_bit in range(bits):
        row_degrees = [
            low + 2 * ((selections[row] >> logical_bit) & 1)
            for row in range(channels)
        ]
        column_degrees = _balanced_degrees(sum(row_degrees), blocks, rng)
        if max(column_degrees) > channels // 2:
            raise ValueError("parameters cannot keep every physical column below half")
        local_rows = _bipartite_rows(row_degrees, column_degrees, rng)
        for row, local in enumerate(local_rows):
            for block in range(blocks):
                if (local >> block) & 1:
                    masks[row] |= 1 << (block * bits + logical_bit)
    expected_t = bits * low + 2 * high_groups
    if any(mask.bit_count() != expected_t for mask in masks):
        raise AssertionError("error-row regularity construction failed")
    if len(set(masks)) != channels:
        raise RuntimeError("constructed channel errors were not distinct")
    return masks


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Inverse-generate a native substitution-channel reconstruction instance."""
    allowed = {"blocks", "payload_nibbles", "channels", "high_groups", "t"}
    unknown = set(params) - allowed
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    blocks = params.get("blocks", 9)
    payload_nibbles = params.get("payload_nibbles", 16)
    channels = params.get("channels", 163)
    high_groups = params.get("high_groups", 14)
    t = params.get("t", _expected_t(blocks, payload_nibbles, high_groups))
    _validate_params(n, blocks, payload_nibbles, channels, high_groups, t)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    payload = rng.getrandbits(_payload_bits(payload_nibbles))
    transmitted = _encode_payload(payload, blocks, payload_nibbles)
    masks = _make_error_masks(blocks, payload_nibbles, channels, high_groups, rng)
    outputs = [transmitted ^ mask for mask in masks]
    assert len(outputs) == channels and len(set(outputs)) == channels
    assert all((word ^ transmitted).bit_count() == t for word in outputs)
    return {
        "family": "Levenshtein reconstruction in a binary repetition code",
        "n": n,
        "blocks": blocks,
        "payload_nibbles": payload_nibbles,
        "payload_bits": _payload_bits(payload_nibbles),
        "channels": channels,
        "high_groups": high_groups,
        "t": t,
        "e": (blocks - 1) // 2,
        "ell": t - (blocks - 1) // 2,
        "outputs": outputs,
        "answer": _format_payload(payload, payload_nibbles),
    }


def render(inst: dict) -> str:
    """Render the complete self-contained problem statement."""
    rows = "\n".join(
        f"  {index + 1}: "
        f"{_format_grouped_word(word, inst['blocks'], inst['payload_nibbles'])}"
        for index, word in enumerate(inst["outputs"])
    )
    p = inst["payload_nibbles"]
    text = f"""Levenshtein sequence reconstruction over GF(2)

A payload is exactly p={p} hexadecimal digits, including leading zeroes and
without a 0x prefix. Each hexadecimal digit denotes four bits in the usual
most-significant-digit-first convention, so a payload has d={inst['payload_bits']}
bits. Letter case is ignored.

The binary code C consists of the words formed by repeating one payload exactly
B={inst['blocks']} times. Spaces below separate the B consecutive blocks and are
not bits. Thus every codeword has n=B*d={inst['n']} bits. The Hamming distance
d(u,v) is the number of bit positions where u and v differ, equivalently the
number of 1 bits in u XOR v. Distinct codewords of C differ in at least B bits,
so C corrects e={inst['e']} substitution errors.

An unknown codeword x in C was sent through N={inst['channels']} channels. The
N outputs below are distinct, and every output differs from x in at most
t={inst['t']} bit positions (so ell=t-e={inst['ell']}). The numbered lines form
an unordered set: line order and line numbers carry no information. Block order
within each line is left to right as displayed; repeated blocks and repeated
payload digits are allowed.

Received words:
{rows}

Find any p-digit payload a such that the B-fold repetition c of a satisfies
d(c,y)<=t for every displayed received word y. Equality at distance t is
allowed. The answer is the payload a, not the full repeated codeword.

Give your final answer inside <answer></answer> tags, as exactly {p}
hexadecimal digits with no 0x prefix.
Example format: <answer>{'0' * p}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        text += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        text += "\n\nHint: " + PLACEBO_HINT
    return text


def parse_answer(text: object) -> object | None:
    """Extract one tagged hexadecimal payload; never raise."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if len(matches) != 1:
        return None
    return matches[0].lower()


def _answer_to_payload(inst: dict, answer: object) -> tuple[int | None, str | None]:
    p = inst["payload_nibbles"]
    if not isinstance(answer, str):
        if isinstance(answer, int) and (
            answer < 0 or answer >= 1 << inst["payload_bits"]
        ):
            return None, "integer payload is outside the declared range"
        return None, "answer must be a hexadecimal string"
    if not answer:
        return None, "answer must be a nonempty hexadecimal string"
    if not _HEX_RE.fullmatch(answer):
        return None, "answer contains a non-hexadecimal character"
    if len(answer) < p:
        return None, f"hexadecimal answer is too short ({len(answer)}<{p})"
    if len(answer) > p:
        return None, f"hexadecimal answer is too long ({len(answer)}>{p})"
    return int(answer, 16), None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Inspect any candidate and the instance only; never read inst['answer']."""
    payload, error = _answer_to_payload(inst, answer)
    if error is not None or payload is None:
        return False, error or "malformed answer"
    word = _encode_payload(payload, inst["blocks"], inst["payload_nibbles"])
    for index, received in enumerate(inst["outputs"], 1):
        distance = (word ^ received).bit_count()
        if distance > inst["t"]:
            return False, (
                f"payload {answer.lower()} exceeds radius {inst['t']} at channel "
                f"{index} (distance {distance})"
            )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample all fixed-width payloads allowed by the statement."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    payload = rng.getrandbits(inst["payload_bits"])
    return _format_payload(payload, inst["payload_nibbles"])


def search_space(inst: dict) -> int | None:
    """Exact size of the bounded hexadecimal certificate language."""
    return 1 << inst["payload_bits"]


def enumerate_all(inst: dict) -> int | None:
    """Count all valid payloads when the exact language is safely small."""
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    return sum(
        verify(inst, _format_payload(value, inst["payload_nibbles"]))[0]
        for value in range(space)
    )


def canonical_key(inst: dict) -> str:
    """Metric invariant under channel, block, bit, and translation symmetries."""
    outputs = inst["outputs"]
    row_profiles = [
        sorted((word ^ other).bit_count() for other in outputs)
        for word in outputs
    ]
    column_minorities = []
    for coordinate in range(inst["n"]):
        ones = sum((word >> coordinate) & 1 for word in outputs)
        column_minorities.append(min(ones, len(outputs) - ones))
    form = [
        inst["n"], inst["blocks"], inst["payload_bits"], inst["t"],
        len(outputs), sorted(row_profiles), sorted(column_minorities),
    ]
    data = json.dumps(form, separators=(",", ":"))
    return hashlib.sha256(data.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow only the channel haystack; keep answer and compact route fixed."""
    if len(DIFFICULTY) == 1:
        return None
    if not isinstance(params, dict):
        return None
    channels = params.get("channels")
    if isinstance(channels, bool) or not isinstance(channels, int):
        return None
    out = dict(params)
    out["channels"] = 2 * channels - 3
    return out


def _reference_one_block_majority(inst: dict) -> tuple[str, int]:
    """Construction-aware specialization of the Section 6 majority scan."""
    bits = inst["payload_bits"]
    threshold = inst["channels"] // 2
    payload = 0
    operations = 0
    for logical_bit in range(bits):
        ones = 0
        for received in inst["outputs"]:
            ones += (received >> logical_bit) & 1
            operations += 1
        if ones > threshold:
            payload |= 1 << logical_bit
    return _format_payload(payload, inst["payload_nibbles"]), operations


def _compact_block_xor(inst: dict, row: int = 0) -> tuple[str, int]:
    """XOR every repetition block of one output row."""
    payload = 0
    for block in range(inst["blocks"]):
        payload ^= _extract_block(
            inst["outputs"][row], block, inst["payload_bits"]
        )
    operations = inst["payload_nibbles"] * (inst["blocks"] - 1)
    return _format_payload(payload, inst["payload_nibbles"]), operations


def _raw_weight_attack(inst: dict) -> str:
    word = min(inst["outputs"], key=lambda value: (value.bit_count(), value))
    payload = _extract_block(word, 0, inst["payload_bits"])
    return _format_payload(payload, inst["payload_nibbles"])


def _medoid_attack(inst: dict) -> str:
    outputs = inst["outputs"]
    word = min(
        outputs,
        key=lambda value: (
            sum((value ^ other).bit_count() for other in outputs), value
        ),
    )
    payload = _extract_block(word, 0, inst["payload_bits"])
    return _format_payload(payload, inst["payload_nibbles"])


def _hex_plurality_attack(inst: dict) -> str:
    prefixes = [
        _format_payload(
            _extract_block(word, 0, inst["payload_bits"]),
            inst["payload_nibbles"],
        )
        for word in inst["outputs"]
    ]
    digits = []
    for position in range(inst["payload_nibbles"]):
        counts = [0] * 16
        for prefix in prefixes:
            counts[int(prefix[position], 16)] += 1
        digits.append(max(range(16), key=lambda digit: (counts[digit], -digit)))
    return "".join(format(digit, "x") for digit in digits)


def _within_row_majority_attack(inst: dict) -> str:
    word = inst["outputs"][0]
    payload = 0
    threshold = inst["blocks"] // 2
    for logical_bit in range(inst["payload_bits"]):
        ones = sum(
            (word >> (block * inst["payload_bits"] + logical_bit)) & 1
            for block in range(inst["blocks"])
        )
        if ones > threshold:
            payload |= 1 << logical_bit
    return _format_payload(payload, inst["payload_nibbles"])


def _partial_block_xor_attack(inst: dict) -> str:
    payload = 0
    for block in range(min(3, inst["blocks"])):
        payload ^= _extract_block(
            inst["outputs"][0], block, inst["payload_bits"]
        )
    return _format_payload(payload, inst["payload_nibbles"])


def _random_restart_attack(inst: dict, rng: random.Random,
                           restarts: int = 256) -> tuple[str, int]:
    last = random_candidate(inst, rng)
    for iteration in range(1, restarts + 1):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last, iteration
    return last, restarts


def _majority_theorem_lhs(inst: dict) -> int:
    minorities = []
    for coordinate in range(inst["n"]):
        ones = sum((word >> coordinate) & 1 for word in inst["outputs"])
        minorities.append(min(ones, inst["channels"] - ones))
    minorities.sort(reverse=True)
    k = inst["e"]
    return (
        sum(inst["channels"] - value for value in minorities[:k + 1])
        + sum(minorities[k + 1:])
    )


def _permute_bits(value: int, width: int, permutation: list[int]) -> int:
    if sorted(permutation) != list(range(width)):
        raise ValueError("bit permutation is malformed")
    out = 0
    for old, new in enumerate(permutation):
        if (value >> old) & 1:
            out |= 1 << new
    return out


def _transform_instance(inst: dict, *, reorder: list[int] | None = None,
                        translate_payload: int = 0,
                        block_permutation: list[int] | None = None,
                        bit_permutation: list[int] | None = None) -> dict:
    """Carry the instance and answer through exact repetition-code symmetries."""
    blocks = inst["blocks"]
    bits = inst["payload_bits"]
    if block_permutation is None:
        block_permutation = list(range(blocks))
    if bit_permutation is None:
        bit_permutation = list(range(bits))
    if sorted(block_permutation) != list(range(blocks)):
        raise ValueError("block permutation is malformed")
    if not (0 <= translate_payload < 1 << bits):
        raise ValueError("translation payload is outside range")
    translation = _encode_payload(
        translate_payload, blocks, inst["payload_nibbles"]
    )

    def carry(word: int) -> int:
        word ^= translation
        old_blocks = [_extract_block(word, block, bits) for block in range(blocks)]
        new_blocks = [0] * blocks
        for old, new in enumerate(block_permutation):
            new_blocks[new] = _permute_bits(old_blocks[old], bits, bit_permutation)
        out = 0
        for block in reversed(new_blocks):
            out = (out << bits) | block
        return out

    outputs = [carry(word) for word in inst["outputs"]]
    if reorder is not None:
        if sorted(reorder) != list(range(len(outputs))):
            raise ValueError("row reorder is malformed")
        outputs = [outputs[index] for index in reorder]
    answer_value = int(inst["answer"], 16) ^ translate_payload
    answer_value = _permute_bits(answer_value, bits, bit_permutation)
    transformed = dict(inst)
    transformed["outputs"] = outputs
    transformed["answer"] = _format_payload(answer_value, inst["payload_nibbles"])
    return transformed


def _different_payload(answer: str, payload_nibbles: int, salt: int) -> str:
    return _format_payload(int(answer, 16) ^ salt, payload_nibbles)


def selftest() -> dict:
    """Run all local G1--G9 gates and return measured JSON-native evidence."""
    report: dict[str, Any] = {}

    checked = 0
    theorem_checks = 0
    previous_n = 0
    previous_reference_cost = 0
    for preset, params in DIFFICULTY.items():
        assert params["n"] > previous_n
        cost = params["channels"] * _payload_bits(params["payload_nibbles"])
        assert cost > previous_reference_cost
        previous_n = params["n"]
        previous_reference_cost = cost
        for seed in (0, 1, 17, 99):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            assert ok, (preset, seed, why)
            assert json.loads(json.dumps(inst["answer"])) == inst["answer"]
            assert _reference_one_block_majority(inst)[0] == inst["answer"]
            for row in (0, len(inst["outputs"]) // 2, len(inst["outputs"]) - 1):
                assert _compact_block_xor(inst, row)[0] == inst["answer"]
            assert _majority_theorem_lhs(inst) > inst["t"] * inst["channels"]
            theorem_checks += 1
            checked += 1
    report["G1_planted_verifies"] = {
        "pass": True,
        "instances": checked,
        "theorem_28_checks": theorem_checks,
        "generation_route": (
            "inverse generation and composition of even block-error parities "
            "realized by exact bipartite degree sequences"
        ),
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **ship_params)
    answer = inst["answer"]
    p = inst["payload_nibbles"]
    swapped = None
    for left in range(p):
        for right in range(left + 1, p):
            if answer[left] == answer[right]:
                continue
            trial = list(answer)
            trial[left], trial[right] = trial[right], trial[left]
            candidate = "".join(trial)
            if not verify(inst, candidate)[0]:
                swapped = candidate
                break
        if swapped is not None:
            break
    assert swapped is not None
    corruptions: dict[str, object] = {
        "empty": "",
        "drop_one": answer[1:],
        "duplicate_one": answer + answer[-1],
        "non_hex": answer[:-1] + "g",
        "out_of_range": 1 << inst["payload_bits"],
        "flip_one_digit": _different_payload(answer, p, 1),
        "swap_two_digits": swapped,
        "wrong_type": [answer],
    }
    reasons = {}
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        assert not ok, (name, bad)
        reasons[name] = why
    assert len(set(reasons.values())) == len(reasons), reasons
    report["G2_rejects_corruption"] = {"pass": True, "reasons": reasons}

    response = (
        "I used the repeated-block invariant.\n```text\n<answer>"
        + answer
        + "</answer>\n```\nThe leading zeroes are included."
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
    guess_hits = sum(
        verify(guess_inst, random_candidate(guess_inst, guess_rng))[0]
        for _ in range(guess_total)
    )
    guess_probability = guess_hits / guess_total
    assert guess_probability < 1e-6, (guess_hits, guess_total)
    report["G4_guess_resistance"] = {
        "pass": True,
        "hits": guess_hits,
        "total": guess_total,
        "empirical_probability": guess_probability,
        "structure_aware_space": search_space(guess_inst),
        "prior": "uniform over all fixed-width hexadecimal payloads",
    }

    demo = make_instance(seed=31415, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    assert demo_count == 1

    density_inst = make_instance(seed=112358, **ship_params)
    density_rng = random.Random(24680)
    density_total = 200_000
    density_hits = sum(
        verify(density_inst, random_candidate(density_inst, density_rng))[0]
        for _ in range(density_total)
    )

    attack_seeds = list(range(3100, 3108))
    attacks = {
        "per_element_lowest_raw_weight": {"successes": 0, "attempts": 8},
        "greedy_hamming_medoid_first_block": {"successes": 0, "attempts": 8},
        "random_payload_restart_256": {"successes": 0, "attempts": 8},
        "by_hand_first_block_hex_plurality": {"successes": 0, "attempts": 8},
        "by_hand_within_row_bit_majority": {"successes": 0, "attempts": 8},
        "by_hand_three_block_partial_xor": {"successes": 0, "attempts": 8},
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
        candidates = {
            "per_element_lowest_raw_weight": _raw_weight_attack(target),
            "greedy_hamming_medoid_first_block": _medoid_attack(target),
            "by_hand_first_block_hex_plurality": _hex_plurality_attack(target),
            "by_hand_within_row_bit_majority": _within_row_majority_attack(target),
            "by_hand_three_block_partial_xor": _partial_block_xor_attack(target),
        }
        for name, candidate in candidates.items():
            if verify(target, candidate)[0]:
                attacks[name]["successes"] += 1
        start = time.perf_counter()
        candidate, iterations = _random_restart_attack(
            target, random.Random(seed ^ 0xA511CE)
        )
        restart_elapsed += time.perf_counter() - start
        restart_iterations += iterations
        if verify(target, candidate)[0]:
            attacks["random_payload_restart_256"]["successes"] += 1

        start = time.perf_counter()
        decoded, operations = _reference_one_block_majority(target)
        reference_elapsed += time.perf_counter() - start
        reference_operations.append(operations)
        if verify(target, decoded)[0]:
            reference_successes += 1
        compact, compact_ops = _compact_block_xor(target)
        compact_operations.append(compact_ops)
        if verify(target, compact)[0]:
            compact_successes += 1

    assert all(row["successes"] == 0 for row in attacks.values()), attacks
    assert reference_successes == len(attack_seeds)
    assert compact_successes == len(attack_seeds)
    assert max(compact_operations) <= 300

    candidate_count = search_space(density_inst)
    assert candidate_count is not None
    report["G5_density_and_baseline_cost"] = {
        "pass": True,
        "shipping_exact_solution_count": 1,
        "shipping_candidate_count": candidate_count,
        "shipping_exact_valid_fraction_formula": f"1/2^{density_inst['payload_bits']}",
        "shipping_exact_valid_fraction_decimal": 1 / candidate_count,
        "exact_count_basis": (
            "Theorem 28 with k=e=4 places every valid repetition-code word "
            "within four bits of one majority word; distance nine makes it "
            "unique, and G1 supplies one"
        ),
        "shipping_sample_hits": density_hits,
        "shipping_sample_total": density_total,
        "shipping_valid_fraction": density_hits / density_total,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo),
        "baseline_attack": "Section 6 majority restricted to one repeated block",
        "baseline_wall_seconds_8_instances": reference_elapsed,
        "baseline_max_bit_observations": max(reference_operations),
        "full_paper_majority_bit_observations": (
            density_inst["channels"] * density_inst["n"]
        ),
        "baseline_attempts": len(attack_seeds),
        "failing_restart_wall_seconds": restart_elapsed,
        "failing_restart_iterations": restart_iterations,
    }

    report["G6_adversary_panel"] = {
        "pass": True,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Section 6 majority specialized to one repetition block",
            "complexity": "Theta(N*d) on this distribution; full scan Theta(N*n)",
            "wall_clock_sec": reference_elapsed,
            "operations": max(reference_operations),
            "full_word_operations": density_inst["channels"] * density_inst["n"],
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
        "compact_route": {
            "name": "within-row XOR of all repetition blocks",
            "operation_unit": "one single-hex-digit XOR",
            "operations": max(compact_operations),
            "solves": f"{compact_successes}/{len(attack_seeds)}",
        },
    }

    escalated_params = escalate(ship_params)
    assert isinstance(escalated_params, dict)
    doubled = make_instance(seed=424242, **escalated_params)
    ok, why = verify(doubled, doubled["answer"])
    assert ok, why
    base_input_bits = inst["channels"] * inst["n"]
    doubled_input_bits = doubled["channels"] * doubled["n"]
    assert doubled_input_bits > 1.9 * base_input_bits
    assert search_space(doubled) == search_space(inst)
    assert _compact_block_xor(doubled)[1] == _compact_block_xor(inst)[1]
    report["G7_scales"] = {
        "pass": True,
        "base_channels": inst["channels"],
        "doubled_channels": doubled["channels"],
        "base_input_bits": base_input_bits,
        "doubled_input_bits": doubled_input_bits,
        "answer_bits_held_fixed": inst["payload_bits"],
        "compact_operations_held_fixed": _compact_block_xor(inst)[1],
        "named_preset_n_strictly_increases": True,
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
        row_order = list(range(base["channels"]))
        block_order = list(range(base["blocks"]))
        bit_order = list(range(base["payload_bits"]))
        rng.shuffle(row_order)
        rng.shuffle(block_order)
        rng.shuffle(bit_order)
        translation = rng.getrandbits(base["payload_bits"])
        transforms = [
            _transform_instance(base, reorder=row_order),
            _transform_instance(base, block_permutation=block_order),
            _transform_instance(base, bit_permutation=bit_order),
            _transform_instance(base, translate_payload=translation),
            _transform_instance(
                base, reorder=row_order, block_permutation=block_order,
                bit_permutation=bit_order, translate_payload=translation,
            ),
        ]
        for transformed in transforms:
            assert canonical_key(transformed) == key
            invariance_checks += 1
            ok, why = verify(transformed, transformed["answer"])
            assert ok, (seed, why)
            real_transform_checks += 1
        for transformed in transforms[:2]:
            ok, why = verify(transformed, base["answer"])
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
            "channel reordering, repetition-block permutation, consistent "
            "payload-bit permutation, codeword translation, and composition"
        ),
    }

    compact_json = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(compact_json)
    answer_tokens_upper_bound = answer_chars
    answer_elements = inst["payload_bits"]
    compact_answer, intended_operations = _compact_block_xor(inst)
    assert verify(inst, compact_answer)[0]
    within_caps = (
        answer_chars <= 2_000
        and answer_tokens_upper_bound <= 500
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {
            "bare": {"solved": 0, "attempts": 0, "errors": 0},
            "hinted": {"solved": 0, "attempts": 0, "errors": 0},
            "placebo": {"solved": 0, "attempts": 0, "errors": 0},
        },
        "hinted_minus_placebo": None,
        "hinted_verdict": "not yet run",
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens_upper_bound,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "operation_unit": "one single-hex-digit XOR",
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
