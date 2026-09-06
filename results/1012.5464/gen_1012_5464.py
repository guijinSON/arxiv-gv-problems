"""Weight-six witnesses in binary self-dual codes of length 36.

This module turns the native objects in Harada--Munemasa, arXiv:1012.5464,
into a Track-B witness problem.  Each instance is a list of generator matrices
for binary self-dual [36,18] codes.  Exactly one matrix is a transformed copy
of the code displayed in Figure 1; its first original generator row is a
known weight-six word.  Coordinate permutations and invertible changes of
row basis carry that certificate to the instance.  The other matrices are
transformed copies of elementary direct-sum codes and two extremal
representatives from the paper's electronic database; their exact weight
enumerators contain no weight-six term.

The planted change of basis makes the carried word equal to the XOR of all
18 displayed rows.  Verification does not use that fact or ``inst["answer"]``:
because every displayed code is self-dual, it checks a proposed support by
the 18 exact GF(2) orthogonality equations.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import random
import re
import sys
import time
from functools import lru_cache


# Keep the shared helpers importable when harden.py is run from this directory.
# This finite-field family does not need them, and remains standard-library-only
# if the repository helpers are absent.
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "binary generator matrices of self-dual [36,18] codes",
        "support of a Hamming-weight-six codeword",
    ],
    "verification_operations": [
        "exact binary rank and self-orthogonality checks",
        "exact dot products over GF(2)",
        "Hamming-weight and range checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "ansatz",
    "intuition_description": (
        "Test the complete row-basis parity in each code block; without that "
        "ansatz, fixed-weight syndrome search examines thousands of triples "
        "per block."
    ),
    "hardness_basis": (
        "Track B: a pair-syndrome prefilter followed by meet-in-the-middle "
        "collision search on triples of the 36 parity-check columns takes "
        "O(b*36^3) exact operations; over eight shipping-preset instances "
        "(b=8) it used at most 63098 counted operations and about 0.025 seconds, "
        "while the complete-row-parity "
        "route uses at most 144 exact 36-bit XOR/popcount "
        "operations."
    ),
    "max_answer_tokens": 7,
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


# n is the number of independently displayed length-36 code blocks.  The
# witness always contains one block number and six coordinates, so escalation
# grows the haystack without lengthening the answer.
DIFFICULTY = {
    "demo": {
        "n": 2,
        "plant_mode": "row_sum",
        "mix_rounds": 40,
        "permute": True,
    },
    "easy": {
        "n": 8,
        "plant_mode": "row_sum",
        "mix_rounds": 180,
        "permute": True,
    },
    "medium": {
        "n": 12,
        "plant_mode": "row_sum",
        "mix_rounds": 220,
        "permute": True,
    },
    "hard": {
        "n": 16,
        "plant_mode": "row_sum",
        "mix_rounds": 260,
        "permute": True,
    },
}

SHIPPING_DIFFICULTY = "easy"

# Scratch G9 runs set this flag after copying the exact shipping module.
if os.environ.get("GV_G9_SINGLE") == "1":
    DIFFICULTY = {
        SHIPPING_DIFFICULTY: dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    }


STRUCTURAL_HINT = (
    "The parity of the complete eighteen-row basis, not a small subset of "
    "rows, is the relevant invariant."
)
PLACEBO_HINT = (
    "The placement of all thirty-six coordinate columns, not their visual "
    "spacing, deserves careful bookkeeping."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "Seven integers [block,c1,c2,c3,c4,c5,c6]: block is a displayed "
        "0-based block index, and 0 <= c1 < ... < c6 < 36 are distinct "
        "0-based coordinate indices."
    ),
    "bounds": {
        "integer_count": 7,
        "support_size": 6,
        "coordinates_per_block": 36,
        "block_index_bound": "number of displayed blocks",
    },
}


NOTES = (
    "Section 1 fixes the exact binary inner product, dual-code, self-dual-code, "
    "and coordinate-equivalence definitions. Section 2.1 makes generator "
    "matrices and invertible basis/coordinate transformations the native "
    "classification objects. Section 4 and Figure 1 give G=(I_18,M) for a "
    "self-dual [36,18,6] code; its first displayed row has weight six, and the "
    "paper's (gamma,delta)=(12,4) weight enumerator shows there are exactly "
    "12 such words. Section 1 points to reference [6]'s electronic generators; "
    "two [36,18,8] representatives from its 36-d8.magma file supplement the "
    "elementary decoys, so a weight-four prefilter cannot isolate the target. "
    "Theorem 1 is a finite classification (519492 classes), and the paper says "
    "all calculations used Magma, so this is not a Track-A claim. The efficient "
    "reference method is pair prefiltering followed by triple-syndrome "
    "collision search. The planted basis is conditioned so individual rows, "
    "pairs, a row-weight outlier probe, and greedy cancellation do not reveal "
    "a word; uniform random row combinations are also tested."
)


# Figure 1 of arXiv:1012.5464.  The target is coordinate-equivalent to
# (I_18, M): int(s, 2) together with the module's least-significant-bit-first
# display convention applies one fixed reversal to the 18 coordinates of M.
_FIGURE1_M = (
    "001100000010100010",
    "001100000010101101",
    "000110000001110101",
    "000110000001000110",
    "001000000001100101",
    "001000000010011001",
    "101110001000111111",
    "101110110111111100",
    "110001000100100110",
    "110010111011010110",
    "010011011000110011",
    "011100010111001111",
    "001011100111000000",
    "111011101000000011",
    "010000101111100101",
    "101111011111011010",
    "110111110111101010",
    "001011111011100110",
)


# Exact enumerator of the Figure-1 code.  It is also obtained from the paper's
# formula with (alpha,beta,gamma,delta)=(0,0,12,4).
_TARGET_ENUM = (
    1, 0, 0, 0, 0, 0, 12, 0, 289, 0, 1560, 0, 10387, 0, 28468, 0,
    54859, 0, 70992, 0, 54859, 0, 28468, 0, 10387, 0, 1560, 0, 289,
    0, 12, 0, 0, 0, 0, 0, 1,
)

# Three elementary decoy types.  B_m is generated by [I_m | J_m-I_m].
# These partitions sum to dimension 18 and none has a weight-six word.
_ELEMENTARY_DECOY_RECIPES = ((18,), (14, 4), (10, 8))

# The first representatives of the two extremal weight-enumerator classes in
# the authors' electronic 36-d8.magma supplement (reference [6], linked from
# Section 1).  The database contains all 41 inequivalent [36,18,8] codes.
# Keeping one representative of each enumerator class is enough to ensure that
# a weight-four pair-collision prefilter leaves many plausible target blocks.
_EXTREMAL_ROW_TEXTS = (
    (
        "100000000000000000001000001101100011",
        "010000000000000000001000001101011100",
        "001000000000000001000101001010010001",
        "000100000000000001000101000101100001",
        "000010000000000000100110101110100001",
        "000001000000000000100110011101010001",
        "000000100000000001101000111100001010",
        "000000010000000001101011000000000110",
        "000000001000000001000110010100101000",
        "000000000100000001001010101011101011",
        "000000000010000000000010100111010100",
        "000000000001000000001101100100010111",
        "000000000000100000001000101000101101",
        "000000000000010000101011010101110000",
        "000000000000001001000111010110110011",
        "000000000000000101100111010100011110",
        "000000000000000011101111001110010010",
        "000000000000000000010011110010101110",
    ),
    (
        "100000000000000100010000101000101001",
        "010000000000000100010000101000010110",
        "001000000000000100010011010101110011",
        "000100000000000100010011010110000000",
        "000010000000000100010101111000110011",
        "000001000000000100010101110111001100",
        "000000100000000100010110010000100001",
        "000000010000000100010110100011101101",
        "000000001000000001000110111111101110",
        "000000000100000001000101000011011101",
        "000000000010000101000111110110010100",
        "000000000001000101000100111001100100",
        "000000000000100001010111000101000101",
        "000000000000010001010100001010000110",
        "000000000000001100000011110000001111",
        "000000000000000011000011111100000000",
        "000000000000000000110011110000111100",
        "000000000000000000001111000000110011",
    ),
)

_EXTREMAL_ENUMS = (
    (
        1, 0, 0, 0, 0, 0, 0, 0, 225, 0, 2016, 0, 9555, 0,
        28800, 0, 55755, 0, 69440, 0, 55755, 0, 28800, 0, 9555,
        0, 2016, 0, 225, 0, 0, 0, 0, 0, 0, 0, 1,
    ),
    (
        1, 0, 0, 0, 0, 0, 0, 0, 289, 0, 1632, 0, 10387, 0,
        28288, 0, 54859, 0, 71232, 0, 54859, 0, 28288, 0, 10387,
        0, 1632, 0, 289, 0, 0, 0, 0, 0, 0, 0, 1,
    ),
)


def _figure1_rows() -> list[int]:
    # The reversal implicit in int(s, 2) is a harmless coordinate permutation
    # applied uniformly to the right half of every row.
    return [(1 << i) | (int(s, 2) << 18) for i, s in enumerate(_FIGURE1_M)]


def _b_rows(m: int) -> list[int]:
    """Rows of [I_m | J_m-I_m], a self-dual binary code for even m."""
    right_all = (1 << m) - 1
    return [
        (1 << i) | ((right_all ^ (1 << i)) << m)
        for i in range(m)
    ]


def _direct_sum_rows(parts: tuple[int, ...]) -> list[int]:
    rows: list[int] = []
    offset = 0
    for m in parts:
        for row in _b_rows(m):
            rows.append(row << offset)
        offset += 2 * m
    if offset != 36 or len(rows) != 18:
        raise AssertionError("bad length-36 direct-sum recipe")
    return rows


def _poly_mul(a: list[int], b: list[int]) -> list[int]:
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        if x:
            for j, y in enumerate(b):
                if y:
                    out[i + j] += x * y
    return out


def _b_enumerator(m: int) -> list[int]:
    # A sum of t generator rows has weight 2t when t is even, and m when t
    # is odd.  This proves the decoys have no word of weight six.
    out = [0] * (2 * m + 1)
    for t in range(m + 1):
        out[2 * t if t % 2 == 0 else m] += math.comb(m, t)
    return out


def _recipe_enumerator(parts: tuple[int, ...]) -> tuple[int, ...]:
    out = [1]
    for m in parts:
        out = _poly_mul(out, _b_enumerator(m))
    out += [0] * (37 - len(out))
    return tuple(out[:37])


_ELEMENTARY_DECOY_ENUMS = tuple(
    _recipe_enumerator(p) for p in _ELEMENTARY_DECOY_RECIPES
)
_DECOY_ENUMS = _ELEMENTARY_DECOY_ENUMS + _EXTREMAL_ENUMS


def _row_texts_to_ints(row_texts: tuple[str, ...]) -> list[int]:
    return [
        sum((ch == "1") << i for i, ch in enumerate(text))
        for text in row_texts
    ]


def _decoy_base_rows(index: int) -> list[int]:
    if index < len(_ELEMENTARY_DECOY_RECIPES):
        return _direct_sum_rows(_ELEMENTARY_DECOY_RECIPES[index])
    return _row_texts_to_ints(
        _EXTREMAL_ROW_TEXTS[index - len(_ELEMENTARY_DECOY_RECIPES)]
    )


def _bruteforce_enumerator(rows: list[int]) -> tuple[int, ...]:
    """Enumerate all 2^18 codewords, using Gray order for one XOR per word."""
    if len(rows) != 18:
        raise ValueError("an enumerated code must have dimension 18")
    counts = [0] * 37
    word = 0
    previous_gray = 0
    counts[0] = 1
    for index in range(1, 1 << 18):
        gray = index ^ (index >> 1)
        changed = gray ^ previous_gray
        word ^= rows[changed.bit_length() - 1]
        counts[word.bit_count()] += 1
        previous_gray = gray
    return tuple(counts)


def _row_xor(rows: list[int], coefficient_mask: int) -> int:
    out = 0
    while coefficient_mask:
        bit = coefficient_mask & -coefficient_mask
        out ^= rows[bit.bit_length() - 1]
        coefficient_mask ^= bit
    return out


def _apply_basis(rows: list[int], basis_rows: list[int]) -> list[int]:
    return [_row_xor(rows, q) for q in basis_rows]


def _random_basis(dimension: int, rng: random.Random, rounds: int) -> list[int]:
    """Generate an invertible row-operation matrix by construction."""
    q = [1 << i for i in range(dimension)]
    for _ in range(rounds):
        i, j = rng.sample(range(dimension), 2)
        q[i] ^= q[j]
        if rng.randrange(5) == 0:
            rng.shuffle(q)
    rng.shuffle(q)
    return q


def _sum_constrained_basis(
    dimension: int, target_coeff: int, rng: random.Random, rounds: int
) -> list[int]:
    """Invertible Q with XOR of its rows equal to target_coeff."""
    if target_coeff <= 0 or target_coeff >= 1 << dimension:
        raise ValueError("target coefficient must be a nonzero dimension-bit vector")
    pivot = (target_coeff & -target_coeff).bit_length() - 1
    q = [1 << i for i in range(dimension) if i != pivot]
    partial = 0
    for row in q:
        partial ^= row
    q.append(target_coeff ^ partial)
    # Paired row additions preserve the XOR of all rows, and each addition is
    # elementary.  Distinct source/targets make their composition invertible.
    for _ in range(rounds):
        i, j, k = rng.sample(range(dimension), 3)
        q[i] ^= q[j]
        q[k] ^= q[j]
        if rng.randrange(5) == 0:
            rng.shuffle(q)
    rng.shuffle(q)
    return q


def _permute_columns(rows: list[int], order: list[int]) -> list[int]:
    out = []
    for row in rows:
        new_row = 0
        for new, old in enumerate(order):
            if (row >> old) & 1:
                new_row |= 1 << new
        out.append(new_row)
    return out


def _bits(row: int, width: int = 36) -> str:
    # Column 0 is the leftmost displayed character.
    return "".join("1" if (row >> i) & 1 else "0" for i in range(width))


def _ints(block: dict) -> list[int]:
    return [
        sum((ch == "1") << i for i, ch in enumerate(text))
        for text in block["rows"]
    ]


def _binary_rank(rows: list[int]) -> int:
    """Exact row rank over GF(2), using integer bit-vectors."""
    basis: dict[int, int] = {}
    for raw in rows:
        value = raw
        while value:
            pivot = value.bit_length() - 1
            if pivot in basis:
                value ^= basis[pivot]
            else:
                basis[pivot] = value
                break
    return len(basis)


@lru_cache(maxsize=1024)
def _checked_self_dual_rows(row_texts: tuple[str, ...]) -> tuple[int, ...]:
    """Execute the rank and orthogonality facts used by the membership check."""
    if len(row_texts) != 18:
        raise ValueError("a block must contain exactly 18 rows")
    if any(not isinstance(row, str) or len(row) != 36
           or any(ch not in "01" for ch in row) for row in row_texts):
        raise ValueError("every block row must be a 36-bit binary string")
    rows = tuple(
        sum((ch == "1") << i for i, ch in enumerate(text))
        for text in row_texts
    )
    if _binary_rank(list(rows)) != 18:
        raise ValueError("the selected generator does not have rank 18")
    if any((rows[i] & rows[j]).bit_count() & 1
           for i in range(18) for j in range(i, 18)):
        raise ValueError("the selected generator rows are not mutually orthogonal")
    return rows


def _weak_compositions(total: int, parts: int):
    if parts == 1:
        yield (total,)
        return
    for first in range(total + 1):
        for rest in _weak_compositions(total - first, parts - 1):
            yield (first,) + rest


def _decoy_counts(n_decoys: int, seed: int) -> tuple[int, ...]:
    """A diverse composition with at least half the decoys extremal.

    The elementary and extremal sub-compositions are independently unranked
    from ``seed``.  This prevents a weight-four pair-collision scan from
    leaving the Figure-1 target as the sole surviving block.
    """
    if n_decoys == 0:
        return (0,) * len(_DECOY_ENUMS)
    extremal_total = (n_decoys + 1) // 2
    elementary_total = n_decoys - extremal_total
    elementary = list(_weak_compositions(elementary_total, 3))
    extremal = list(_weak_compositions(extremal_total, 2))
    choice_count = len(elementary) * len(extremal)
    index = int(seed) % choice_count
    elementary_choice = elementary[index % len(elementary)]
    extremal_choice = extremal[index // len(elementary)]
    return elementary_choice + extremal_choice


def _make_transformed_block(
    base_rows: list[int],
    enumerator: tuple[int, ...],
    kind: str,
    rng: random.Random,
    rounds: int,
    order: list[int] | None = None,
    constrained_coeff: int | None = None,
) -> tuple[dict, list[int] | None]:
    if constrained_coeff is None:
        q = _random_basis(18, rng, rounds)
    else:
        q = _sum_constrained_basis(18, constrained_coeff, rng, rounds)
    transformed = _apply_basis(base_rows, q)
    if order is None:
        order = list(range(36))
        rng.shuffle(order)
    transformed = _permute_columns(transformed, order)
    block = {
        "rows": [_bits(row) for row in transformed],
        "weight_enumerator": list(enumerator),
        "kind": kind,
    }
    support = None
    if constrained_coeff is not None:
        planted_old = _row_xor(base_rows, constrained_coeff)
        inverse = [0] * 36
        for new, old in enumerate(order):
            inverse[old] = new
        support = sorted(inverse[i] for i in range(36) if (planted_old >> i) & 1)
    return block, support


def _candidate_from_word(block_index: int, word: int) -> list[int] | None:
    if word.bit_count() != 6:
        return None
    return [block_index] + [i for i in range(36) if (word >> i) & 1]


def _attack_outlier_basis_weight(inst: dict) -> list[int] | None:
    # A construction-aware per-block outlier probe: select the basis containing
    # the lightest displayed row, then try its complete row parity.
    scores = []
    for b, block in enumerate(inst["blocks"]):
        rows = _ints(block)
        scores.append((min(row.bit_count() for row in rows), b, rows))
    _, b, rows = min(scores)
    word = 0
    for row in rows:
        word ^= row
    return _candidate_from_word(b, word)


def _attack_greedy_cancellation(inst: dict) -> list[int] | None:
    for b, block in enumerate(inst["blocks"]):
        rows = _ints(block)
        word = min(rows, key=lambda x: (x.bit_count(), x))
        unused = set(range(18))
        for _ in range(18):
            best = None
            for i in unused:
                trial = word ^ rows[i]
                score = (trial.bit_count(), i)
                if best is None or score < best[0]:
                    best = (score, i, trial)
            if best is None or best[2].bit_count() >= word.bit_count():
                break
            _, i, word = best
            unused.remove(i)
        candidate = _candidate_from_word(b, word)
        if candidate is not None:
            return candidate
    return None


def _attack_small_basis_sums(inst: dict) -> list[int] | None:
    for b, block in enumerate(inst["blocks"]):
        rows = _ints(block)
        for row in rows:
            candidate = _candidate_from_word(b, row)
            if candidate is not None:
                return candidate
        for i in range(18):
            for j in range(i + 1, 18):
                candidate = _candidate_from_word(b, rows[i] ^ rows[j])
                if candidate is not None:
                    return candidate
    return None


def _attack_random_row_combinations(
    inst: dict, rng: random.Random, restarts: int = 32
) -> list[int] | None:
    for _ in range(restarts):
        b = rng.randrange(len(inst["blocks"]))
        rows = _ints(inst["blocks"][b])
        mask = rng.randrange(1, 1 << 18)
        candidate = _candidate_from_word(b, _row_xor(rows, mask))
        if candidate is not None:
            return candidate
    return None


def make_instance(
    n: int,
    seed: int = 0,
    plant_mode: str = "row_sum",
    mix_rounds: int = 220,
    permute: bool = True,
    **params,
) -> dict:
    """Construct an instance and carry a weight-six word through transformations."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if not isinstance(n, int) or isinstance(n, bool) or n < 1:
        raise ValueError("n must be a positive number of code blocks")
    if plant_mode not in {"visible", "row_sum"}:
        raise ValueError("plant_mode must be 'visible' or 'row_sum'")
    if not isinstance(mix_rounds, int) or mix_rounds < 0:
        raise ValueError("mix_rounds must be a nonnegative integer")

    rng = random.Random(seed)
    target_base = _figure1_rows()
    target_coeff = 1  # first Figure-1 row, whose Hamming weight is six
    decoy_counts = _decoy_counts(n - 1, seed)

    # The regular family rejects only transformations on which one of the
    # declared cheap attacks accidentally works.  The witness remains the
    # carried Figure-1 row and is never found by solving the built instance.
    max_attempts = 200 if plant_mode == "row_sum" else 1
    for _attempt in range(max_attempts):
        blocks: list[dict] = []
        if plant_mode == "visible":
            target_rows = target_base
            order = list(range(36))
            target_block = {
                "rows": [_bits(row) for row in target_rows],
                "weight_enumerator": list(_TARGET_ENUM),
                "kind": "figure1_target",
            }
            target_support = [i for i in range(36) if (target_rows[0] >> i) & 1]
        else:
            order = list(range(36))
            if permute:
                rng.shuffle(order)
            target_block, target_support = _make_transformed_block(
                target_base,
                _TARGET_ENUM,
                "figure1_target",
                rng,
                mix_rounds,
                order=order,
                constrained_coeff=target_coeff,
            )
            if target_support is None:
                raise AssertionError("target support was not carried")
        blocks.append(target_block)

        for recipe_index, count in enumerate(decoy_counts):
            base = _decoy_base_rows(recipe_index)
            for _ in range(count):
                decoy_order = list(range(36))
                if permute:
                    rng.shuffle(decoy_order)
                block, _ = _make_transformed_block(
                    base,
                    _DECOY_ENUMS[recipe_index],
                    f"decoy_{recipe_index}",
                    rng,
                    mix_rounds,
                    order=decoy_order,
                )
                blocks.append(block)

        if permute:
            rng.shuffle(blocks)
        target_index = next(i for i, block in enumerate(blocks)
                            if block["kind"] == "figure1_target")
        answer = [target_index] + list(target_support)
        inst = {
            "n": n,
            "length": 36,
            "dimension": 18,
            "target_weight": 6,
            "blocks": blocks,
            "answer": answer,
            "construction": {
                "decoy_counts": list(decoy_counts),
                "plant_mode": plant_mode,
            },
        }
        if plant_mode == "visible":
            return inst
        cheap = (
            _attack_outlier_basis_weight(inst),
            _attack_greedy_cancellation(inst),
            _attack_small_basis_sums(inst),
        )
        if all(not verify(inst, candidate)[0] for candidate in cheap):
            return inst
    raise RuntimeError("could not draw a transformation defeating the cheap probes")


def render(inst: dict) -> str:
    lines = [
        "Weight-six word in binary self-dual codes",
        "",
        "All arithmetic is over GF(2): addition is XOR (1+1=0). For binary",
        "vectors u,v of length 36, their inner product is the parity of the",
        "coordinates where both have a 1. A binary linear code is the set of",
        "all XORs of the rows of its generator matrix. Its dual consists of",
        "all vectors orthogonal to every codeword. A code is self-dual when it",
        "equals its dual.",
        "",
        f"Below are {len(inst['blocks'])} independent 18-by-36 binary generator",
        "matrices. In every matrix the 18 rows are independent and mutually",
        "orthogonal, so they generate a self-dual code of length 36. At least",
        "one displayed code contains a word of Hamming weight exactly 6.",
        "",
        "Find any one such word. Coordinates are numbered 0 through 35 from",
        "left to right within a row; block numbers are 0-based. A support means",
        "six distinct coordinate numbers whose incidence vector belongs to the",
        "row span of the selected block. Order the six coordinates increasingly.",
        "",
    ]
    for b, block in enumerate(inst["blocks"]):
        lines.append(f"BLOCK {b}")
        for r, row in enumerate(block["rows"]):
            lines.append(f"{r:02d}: {row}")
        lines.append("")
    lines.extend([
        "Give your final answer inside <answer></answer> tags, as exactly seven",
        "comma-separated integers: block,c1,c2,c3,c4,c5,c6.",
        "Example: <answer>2, 1, 5, 9, 14, 23, 31</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer>", re.I | re.S)


def parse_answer(text) -> object | None:
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    body = re.sub(r"^```(?:json|text)?\s*|\s*```$", "", body, flags=re.I | re.S)
    if not body:
        return None
    if body.startswith("[") and body.endswith("]"):
        try:
            value = json.loads(body)
        except (TypeError, ValueError):
            return None
        if not isinstance(value, list):
            return None
        return value
    pieces = [piece.strip() for piece in body.split(",")]
    if not pieces or any(not re.fullmatch(r"[+-]?\d+", p) for p in pieces):
        return None
    try:
        return [int(p) for p in pieces]
    except ValueError:
        return None


def verify(inst: dict, answer) -> tuple[bool, str]:
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list):
        return False, "answer must be a list of seven integers"
    if len(answer) != 7:
        return False, "answer must contain exactly seven integers"
    if any(not isinstance(x, int) or isinstance(x, bool) for x in answer):
        return False, "every answer entry must be an integer"
    block_index, *coords = answer
    if not 0 <= block_index < len(inst["blocks"]):
        return False, "block index is out of range"
    if any(not 0 <= c < 36 for c in coords):
        return False, "a coordinate index is out of range"
    if len(set(coords)) != 6:
        return False, "coordinate indices must be distinct"
    if coords != sorted(coords):
        return False, "coordinate indices must be strictly increasing"
    block = inst["blocks"][block_index]
    try:
        rows = _checked_self_dual_rows(tuple(block["rows"]))
    except (KeyError, TypeError, ValueError) as exc:
        return False, "malformed selected code block: " + str(exc)
    # Rank 18 plus self-orthogonality in length 36 proves C=C^perp.  The
    # following 18 parity checks therefore decide membership exactly.
    for row_index, row in enumerate(rows):
        parity = 0
        for coordinate in coords:
            parity ^= (row >> coordinate) & 1
        if parity:
            return False, f"support is not in the code (row {row_index} has odd inner product)"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    return [rng.randrange(len(inst["blocks"]))] + sorted(rng.sample(range(36), 6))


def search_space(inst: dict) -> int | None:
    return len(inst["blocks"]) * math.comb(36, 6)


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 2_000_000:
        return None
    count = 0
    for block in inst["blocks"]:
        rows = _ints(block)
        columns = []
        for c in range(36):
            syndrome = 0
            for r, row in enumerate(rows):
                syndrome |= (((row >> c) & 1) << r)
            columns.append(syndrome)
        for support in itertools.combinations(range(36), 6):
            syndrome = 0
            for c in support:
                syndrome ^= columns[c]
            count += syndrome == 0
    return count


def canonical_key(inst: dict) -> str:
    # The full weight enumerator is invariant under row-basis changes,
    # coordinate relabelling, and block order.  It is a strong cheap invariant,
    # though not a complete code-isomorphism canonical form (see README).
    invariant = sorted(tuple(block["weight_enumerator"])
                       for block in inst["blocks"])
    payload = json.dumps(invariant, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    current = int(params.get("n", 0))
    # Each block costs 17 vector XORs and one exact Hamming-weight test.  Sixteen
    # blocks cost 288 operations; a seventeenth would cross G9's cap.
    if current < 16:
        out = dict(params)
        out["n"] = min(16, max(current + 1, (3 * current + 1) // 2))
        out["plant_mode"] = "row_sum"
        out["permute"] = True
        out["mix_rounds"] = max(220, int(out.get("mix_rounds", 0)))
        return out
    # At fixed block count and answer length, further row mixing removes residual
    # presentation clues without increasing the compact-route operation count.
    rounds = int(params.get("mix_rounds", 0))
    if rounds < 1040:
        out = dict(params)
        out["mix_rounds"] = min(1040, max(320, 2 * rounds))
        return out
    return None


def _columns(block: dict) -> list[int]:
    rows = _ints(block)
    out = []
    for c in range(36):
        syndrome = 0
        for r, row in enumerate(rows):
            syndrome |= (((row >> c) & 1) << r)
        out.append(syndrome)
    return out


def _has_weight_four(columns: list[int]) -> tuple[bool, dict]:
    """Detect a four-column zero sum by a disjoint pair collision."""
    seen: dict[int, list[tuple[int, int]]] = {}
    pair_syndromes = 0
    collision_checks = 0
    for i, j in itertools.combinations(range(36), 2):
        syndrome = columns[i] ^ columns[j]
        pair_syndromes += 1
        for a, b in seen.get(syndrome, ()):
            collision_checks += 1
            if len({a, b, i, j}) == 4:
                return True, {
                    "pair_syndromes": pair_syndromes,
                    "pair_collision_checks": collision_checks,
                }
        seen.setdefault(syndrome, []).append((i, j))
    return False, {
        "pair_syndromes": pair_syndromes,
        "pair_collision_checks": collision_checks,
    }


def _reference_triple_collision(inst: dict) -> tuple[list[int] | None, dict]:
    # The elementary decoys have minimum distance four, so a specialist first
    # removes them with pair-syndrome collisions.  The extremal d=8 decoys
    # deliberately survive this construction-aware prefilter together with the
    # d=6 Figure-1 target.
    survivors = []
    pair_syndromes = 0
    pair_collision_checks = 0
    cached_columns = []
    for b, block in enumerate(inst["blocks"]):
        columns = _columns(block)
        cached_columns.append(columns)
        has_four, stats = _has_weight_four(columns)
        pair_syndromes += stats["pair_syndromes"]
        pair_collision_checks += stats["pair_collision_checks"]
        if not has_four:
            survivors.append(b)

    triple_count = 0
    xor_operations = 0
    collision_checks = 0
    for b in survivors:
        columns = cached_columns[b]
        seen: dict[int, list[tuple[int, int, int]]] = {}
        for triple in itertools.combinations(range(36), 3):
            syndrome = columns[triple[0]] ^ columns[triple[1]] ^ columns[triple[2]]
            triple_count += 1
            xor_operations += 2
            for prior in seen.get(syndrome, ()):
                collision_checks += 1
                if not set(prior).intersection(triple):
                    candidate = [b] + sorted(prior + triple)
                    if verify(inst, candidate)[0]:
                        return candidate, {
                            "pair_syndromes": pair_syndromes,
                            "pair_collision_checks": pair_collision_checks,
                            "prefilter_survivors": len(survivors),
                            "triple_syndromes": triple_count,
                            "xor_operations": xor_operations,
                            "collision_checks": collision_checks,
                            "operations": (
                                pair_syndromes + pair_collision_checks
                                + xor_operations + collision_checks
                            ),
                        }
            seen.setdefault(syndrome, []).append(triple)
    return None, {
        "pair_syndromes": pair_syndromes,
        "pair_collision_checks": pair_collision_checks,
        "prefilter_survivors": len(survivors),
        "triple_syndromes": triple_count,
        "xor_operations": xor_operations,
        "collision_checks": collision_checks,
        "operations": (
            pair_syndromes + pair_collision_checks
            + xor_operations + collision_checks
        ),
    }


def _compact_row_parity(inst: dict) -> tuple[list[int] | None, int]:
    operations = 0
    for b, block in enumerate(inst["blocks"]):
        rows = _ints(block)
        word = rows[0]
        for row in rows[1:]:
            word ^= row
            operations += 1
        operations += 1  # exact Hamming-weight test
        candidate = _candidate_from_word(b, word)
        if candidate is not None and verify(inst, candidate)[0]:
            return candidate, operations
    return None, operations


def _transform_instance(
    inst: dict,
    rng: random.Random,
    reorder_rows: bool = False,
    change_row_basis: bool = False,
    permute_coordinates: bool = False,
    reorder_blocks: bool = False,
) -> dict:
    blocks = []
    answer = list(inst["answer"])
    old_target = answer[0]
    target_coords = answer[1:]
    for old_b, block in enumerate(inst["blocks"]):
        rows = _ints(block)
        if change_row_basis:
            rows = _apply_basis(rows, _random_basis(18, rng, 60))
        if reorder_rows:
            rng.shuffle(rows)
        carried = list(target_coords) if old_b == old_target else None
        if permute_coordinates:
            order = list(range(36))
            rng.shuffle(order)
            rows = _permute_columns(rows, order)
            if carried is not None:
                inverse = [0] * 36
                for new, old in enumerate(order):
                    inverse[old] = new
                carried = sorted(inverse[c] for c in carried)
        blocks.append({
            "rows": [_bits(row) for row in rows],
            "weight_enumerator": list(block["weight_enumerator"]),
            "kind": block["kind"],
        })
        if carried is not None:
            target_coords = carried

    block_order = list(range(len(blocks)))
    if reorder_blocks:
        rng.shuffle(block_order)
    new_blocks = [blocks[old] for old in block_order]
    new_target = block_order.index(old_target)
    return {
        "n": inst["n"],
        "length": 36,
        "dimension": 18,
        "target_weight": 6,
        "blocks": new_blocks,
        "answer": [new_target] + target_coords,
        "construction": dict(inst["construction"]),
    }


def _answer_metrics(answer) -> tuple[int, int, int]:
    # Match emit.sh, which serialises inst["answer"] with ordinary json.dumps.
    blob = json.dumps(answer)

    def atoms(value) -> int:
        if isinstance(value, dict):
            return sum(atoms(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return sum(atoms(v) for v in value)
        return 1

    return len(blob), (len(blob) + 3) // 4, atoms(answer)


# Replaced with measured transcript counts after the three harness runs.  The
# arms are diagnostic under the 2026-09-05 contract; only the size/effort caps
# determine G9 pass/fail.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3, "errors": 0},
    "hinted": {"solved": 0, "attempts": 3, "errors": 0},
    "placebo": {"solved": 0, "attempts": 3, "errors": 0},
    "hinted_verdict": "hardened",
}


def selftest() -> dict:
    report: dict = {}

    enumerator_checks = {
        "figure1": _bruteforce_enumerator(_figure1_rows()) == _TARGET_ENUM,
    }
    for index in range(len(_DECOY_ENUMS)):
        enumerator_checks[f"decoy_{index}"] = (
            _bruteforce_enumerator(_decoy_base_rows(index))
            == _DECOY_ENUMS[index]
            and _DECOY_ENUMS[index][6] == 0
        )

    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": why})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": "answer is not JSON-native"})
            for block_index, block in enumerate(inst["blocks"]):
                try:
                    _checked_self_dual_rows(tuple(block["rows"]))
                except (KeyError, TypeError, ValueError) as exc:
                    g1_failures.append({
                        "preset": preset,
                        "seed": seed,
                        "reason": f"block {block_index} is invalid: {exc}",
                    })
    report["G1_planted_verifies"] = {
        "pass": not g1_failures and all(enumerator_checks.values()),
        "attempts": g1_attempts,
        "failures": g1_failures,
        "bruteforce_weight_enumerator_checks": enumerator_checks,
        "codewords_enumerated_per_base_code": 1 << 18,
    }

    params = dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    inst = make_instance(seed=10125464, **params)
    good = list(inst["answer"])
    corruptions = {
        "drop_one": good[:-1],
        "swap_two": [good[0], good[2], good[1]] + good[3:],
        "duplicate": [good[0], good[1], good[1]] + good[3:],
        "empty": [],
        "out_of_range": [len(inst["blocks"])] + good[1:],
    }
    rejection_reasons = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejection_reasons[name] = {"rejected": not ok, "reason": why}
    reasons = [item["reason"] for item in rejection_reasons.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in rejection_reasons.values())
                and len(set(reasons)) == len(reasons),
        "cases": rejection_reasons,
        "distinct_reason_count": len(set(reasons)),
    }

    answer_text = ", ".join(map(str, good))
    realistic = (
        "I checked the GF(2) inner products.\n\n```text\n"
        f"<answer>{answer_text}</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == good and verify(inst, parsed)[0],
        "parsed": parsed,
        "expected": good,
    }

    guess_rng = random.Random(1012546401)
    sample_total = 200_000
    hits = 0
    candidate_columns = [_columns(block) for block in inst["blocks"]]
    t0 = time.perf_counter()
    for _ in range(sample_total):
        candidate = random_candidate(inst, guess_rng)
        syndrome = 0
        for coordinate in candidate[1:]:
            syndrome ^= candidate_columns[candidate[0]][coordinate]
        hits += int(syndrome == 0)
    guess_sec = time.perf_counter() - t0
    exact_solutions = sum(block["weight_enumerator"][6]
                          for block in inst["blocks"])
    exact_space = search_space(inst)
    exact_density = exact_solutions / exact_space
    report["G4_guess_resistance"] = {
        "pass": hits / sample_total < 1e-6 and exact_density < 1e-6,
        "hits": hits,
        "total": sample_total,
        "fraction": hits / sample_total,
        "exact_solution_count": exact_solutions,
        "candidate_space": exact_space,
        "exact_fraction": exact_density,
        "structure_aware_constraints": [
            "a valid displayed block index",
            "exactly six distinct coordinates from 0 through 35",
            "coordinates already sorted increasingly",
        ],
        "wall_clock_sec": round(guess_sec, 6),
    }

    reference_runs = []
    compact_runs = []
    reference_failures = 0
    compact_failures = 0
    for seed in range(800, 808):
        trial = make_instance(seed=seed, **params)
        start = time.perf_counter()
        answer, stats = _reference_triple_collision(trial)
        stats["wall_clock_sec"] = time.perf_counter() - start
        reference_runs.append(stats)
        reference_failures += int(not verify(trial, answer)[0])
        start = time.perf_counter()
        compact, operations = _compact_row_parity(trial)
        compact_runs.append({
            "operations": operations,
            "wall_clock_sec": time.perf_counter() - start,
        })
        compact_failures += int(not verify(trial, compact)[0])

    baseline_start = time.perf_counter()
    baseline_successes = 0
    baseline_combinations = 0
    for seed in range(8):
        trial = make_instance(seed=900 + seed, **params)
        candidate = _attack_small_basis_sums(trial)
        baseline_successes += int(verify(trial, candidate)[0])
        baseline_combinations += len(trial["blocks"]) * (18 + math.comb(18, 2))
    baseline_sec = time.perf_counter() - baseline_start
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_start = time.perf_counter()
    demo_count = enumerate_all(demo)
    demo_sec = time.perf_counter() - demo_start
    report["G5_density_and_baseline_cost"] = {
        "pass": exact_density < 1e-6 and baseline_successes == 0
                and reference_failures == 0,
        "shipping_exact_solution_count": exact_solutions,
        "shipping_candidate_space": exact_space,
        "shipping_exact_density": exact_density,
        "shipping_sample_hits": hits,
        "shipping_sample_total": sample_total,
        "demo_exact_solution_count_by_enumeration": demo_count,
        "demo_candidate_space": search_space(demo),
        "demo_enumeration_wall_clock_sec": round(demo_sec, 6),
        "strongest_failing_attack": "basis_sums_of_at_most_two_rows",
        "baseline_combinations": baseline_combinations,
        "baseline_successes": baseline_successes,
        "baseline_wall_clock_sec": round(baseline_sec, 6),
        "reference_operations_max": max(x["operations"] for x in reference_runs),
        "reference_wall_clock_sec_max": round(
            max(x["wall_clock_sec"] for x in reference_runs), 6
        ),
    }

    attack_functions = {
        "outlier_lightest_basis_block": (
            lambda trial, rng: _attack_outlier_basis_weight(trial)
        ),
        "greedy_row_cancellation": (
            lambda trial, rng: _attack_greedy_cancellation(trial)
        ),
        "random_row_combination_32": (
            lambda trial, rng: _attack_random_row_combinations(trial, rng, 32)
        ),
        "by_hand_sums_of_at_most_two_rows": (
            lambda trial, rng: _attack_small_basis_sums(trial)
        ),
    }
    attack_results = {}
    for attack_index, (name, attack) in enumerate(attack_functions.items()):
        successes = 0
        start = time.perf_counter()
        for seed in range(8):
            trial = make_instance(seed=1200 + seed, **params)
            candidate = attack(trial, random.Random(attack_index * 10000 + seed))
            successes += int(verify(trial, candidate)[0])
        attack_results[name] = {
            "successes": successes,
            "attempts": 8,
            "wall_clock_sec": round(time.perf_counter() - start, 6),
        }
    all_failed = all(x["successes"] == 0 for x in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_failures == 0 and compact_failures == 0,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": (
                "pair-syndrome weight-4 prefilter, then meet-in-the-middle "
                "collision search on 3-column syndromes"
            ),
            "complexity": "O(b*36^3) exact time and O(36^3) stored triples",
            "wall_clock_sec": round(
                sum(x["wall_clock_sec"] for x in reference_runs) / 8, 6
            ),
            "wall_clock_sec_max": round(
                max(x["wall_clock_sec"] for x in reference_runs), 6
            ),
            "operations": max(x["operations"] for x in reference_runs),
            "pair_syndromes": max(x["pair_syndromes"] for x in reference_runs),
            "prefilter_survivors": max(
                x["prefilter_survivors"] for x in reference_runs
            ),
            "triple_syndromes": max(x["triple_syndromes"] for x in reference_runs),
            "solves": f"{8 - reference_failures}/8, as expected",
        },
        "intended_compact_route": {
            "name": "scan the XOR of each complete 18-row displayed basis",
            "complexity": "17 exact vector XORs plus one weight test per block",
            "wall_clock_sec": round(
                sum(x["wall_clock_sec"] for x in compact_runs) / 8, 6
            ),
            "operations": max(x["operations"] for x in compact_runs),
            "worst_case_operations_at_preset": 18 * len(inst["blocks"]),
            "solves": f"{8 - compact_failures}/8",
        },
    }

    doubled_start = time.perf_counter()
    doubled = make_instance(
        n=2 * params["n"],
        seed=71,
        plant_mode="row_sum",
        mix_rounds=params["mix_rounds"],
        permute=True,
    )
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * params["n"]
                and len(doubled["answer"]) == len(inst["answer"]),
        "shipping_blocks": params["n"],
        "doubled_blocks": doubled["n"],
        "answer_elements_shipping": len(inst["answer"]),
        "answer_elements_doubled": len(doubled["answer"]),
        "doubled_build_and_verify_sec": round(time.perf_counter() - doubled_start, 6),
        "doubled_verify_reason": doubled_why,
        "escalation_after_shipping": escalate(params),
    }

    invariant_count = 0
    real_count = 0
    transform_failures = []
    transformations = (
        {"reorder_rows": True},
        {"change_row_basis": True},
        {"permute_coordinates": True},
        {"reorder_blocks": True},
        {
            "reorder_rows": True,
            "change_row_basis": True,
            "permute_coordinates": True,
            "reorder_blocks": True,
        },
    )
    for seed in range(20):
        original = make_instance(seed=2000 + seed, **params)
        key = canonical_key(original)
        for j, transform in enumerate(transformations):
            carried = _transform_instance(
                original, random.Random(50000 + 10 * seed + j), **transform
            )
            if canonical_key(carried) == key:
                invariant_count += 1
            else:
                transform_failures.append({
                    "seed": seed, "transform": transform, "failure": "key changed"
                })
            ok, why = verify(carried, carried["answer"])
            if ok:
                real_count += 1
            else:
                transform_failures.append({
                    "seed": seed, "transform": transform, "failure": why
                })
    unrelated = [
        canonical_key(make_instance(seed=3000 + seed, **params))
        for seed in range(20)
    ]
    report["G8_canonical_key"] = {
        "pass": not transform_failures and invariant_count == 100
                and real_count == 100 and len(set(unrelated)) == 20,
        "canonical_invariant": "multiset of full block weight enumerators",
        "transformations": [
            "row reordering in every generator matrix",
            "invertible row-basis change in every generator matrix",
            "coordinate permutation within every code block",
            "reordering the list of code blocks",
            "composition of all four",
        ],
        "invariant_relabellings": invariant_count,
        "real_transformations_verified": real_count,
        "unrelated_attempts": 20,
        "unrelated_distinct_keys": len(set(unrelated)),
        "failures": transform_failures,
    }

    answer_chars, answer_tokens, answer_atoms = _answer_metrics(inst["answer"])
    route_operations = 18 * len(inst["blocks"])
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else None
    )
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else None
    )
    within_caps = (
        answer_chars <= 2000 and answer_atoms <= 256 and route_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == 7
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None
        ),
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": 28,
        "worst_case_answer_tokens": 7,
        "answer_elements": answer_atoms,
        "intended_route_operations": route_operations,
        "within_caps": within_caps,
        "diagnostic_complete": all(arms[name]["attempts"] >= 3 for name in arms),
        "diagnostic_is_not_a_gate": True,
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
