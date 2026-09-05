"""Exact structured tensor-decomposition instances for arXiv:1611.01559.

The paper defines tensor rank through sums of rank-one outer products and proves
that deciding a rank bound is as hard as solving polynomial systems.  This
module stays in that native tensor language, but makes the distributional claim
honestly as Track B: its promised Walsh-structured instances have an efficient
exact inversion algorithm.  A planted pair of XOR shifts is sampled first for
each direct-sum block, and the displayed integer tensor is composed from the
resulting rank-one summands.  The answer is a compact binary matrix specifying
those summands; verification expands and compares the decomposition exactly.
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


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "integer_lattice",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "order-three integer tensor in direct-sum block form",
        "integer rank-one factor codebooks",
        "binary matrix specifying a rank-one decomposition",
    ],
    "verification_operations": [
        "exact integer outer product",
        "exact integer summation",
        "entrywise tensor equality",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Walsh-character symmetry isolates selected latent rank-one summands; "
        "without it one must invert every displayed tensor coordinate stream."
    ),
    "hardness_basis": (
        "Track B: exact Walsh-Hadamard inversion solves the promised family in "
        "O(2*blocks*n*log2(n)) arithmetic operations; at the shipping preset "
        "the reference implementation uses 966 exact arithmetic operations "
        "and measured about 0.0002 seconds mean over eight runs, whereas the zero-character compact "
        "route uses 192 exact operations but must be recognized and executed "
        "without tools."
    ),
    "max_answer_tokens": 24,
}

NATIVE: dict = {
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

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON matrix with exactly `blocks` rows and 2*log2(n) binary entries "
        "per row.  The first half of row q is the little-endian XOR shift of "
        "the second-mode codebook in block q, and the second half is the shift "
        "of the third-mode codebook."
    ),
    "bounds": {
        "max_blocks": 12,
        "max_group_order": 256,
        "entries": [0, 1],
        "max_atomic_elements": 192,
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 4, "blocks": 1, "value_bits": 4},
    "easy": {"n": 8, "blocks": 2, "value_bits": 6},
    "medium": {"n": 16, "blocks": 2, "value_bits": 8},
    "hard": {"n": 32, "blocks": 3, "value_bits": 12},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT: str = (
    "Hint: The Walsh-character basis makes the all-zero latent component a common-sign coefficient in every block."
)
PLACEBO_HINT: str = (
    "Hint: The structured tensor notation rewards careful attention to every block and indexing convention."
)

# Filled only from the three transcript-producing harden.py runs.  Keeping this
# as None makes a pre-oracle selftest visibly provisional instead of pretending
# that an unrun oracle failed.
_G9_EVIDENCE = None

NOTES = r"""
Paper definition and hardness. Section 2 defines an order-three tensor over a
commutative ring, a simple tensor a tensor b tensor c, and rank as the least
number of simple tensors in a sum. Theorem 3 states polynomial-time equivalence
between tensor-rank decision and polynomial-system feasibility over integral
domains; Observation 8 and Corollary 5 provide worst-case NP-hardness. This does
not make an inverse-generated random low-rank distribution hard, so the module
does not claim Track A.

What makes this family easy to a tool. Section 3's slice-completion Lemma 9 and
the reductions in Sections 4-5 make clear that special slice structure can
expose a decomposition. Here that fact is explicit: the first-mode factor
matrix is a Walsh character table, so a fast Walsh-Hadamard transform exactly
recovers the two informative coefficient streams. The reference algorithm is
reported as a successful Track-B algorithm, never hidden in the failing attack
panel.

Generation and certificate. For every block, two codebooks are sampled from the
same uniform-without-replacement integer distribution, as are the two planted
XOR shifts. The target block is assembled as the sum, over all x, of the three
integer vectors character(x), (1,B[x xor s]), and (1,C[x xor t]). Direct-summing
the blocks gives the displayed order-three tensor. The binary answer matrix
stores s and t. make_instance never invokes the Walsh recovery algorithm.

Compact route and attacks. The coefficient of latent x=0 is obtained by adding
the displayed matrices over every first-mode frequency. Its (1,0) and (0,1)
entries locate the two shifts in the public codebooks; this costs 192 exact
operations at shipping size. Random codebooks remove the sign leakage of a
monotone binary-value codebook. The panel tests maximum-magnitude outliers, an
average-marginal greedy choice, 256 structure-aware random restarts, and the
in-context but wrong ansatz that reads shift bits directly from selected raw
Walsh-row signs.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 250_000


def _is_power_of_two(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 2 and value & (value - 1) == 0


def _bit_width(n):
    return n.bit_length() - 1


def _bits(value, width):
    return [(value >> bit) & 1 for bit in range(width)]


def _from_bits(bits):
    return sum(bit << position for position, bit in enumerate(bits))


def _character(frequency, latent):
    return -1 if (frequency & latent).bit_count() & 1 else 1


def _sample_codebook(rng, n, value_bits):
    radius = (1 << (value_bits - 1)) - 1
    if 2 * radius < n:
        raise ValueError("value_bits leaves too few distinct nonzero code values")
    # Sample indices from a range object: escalated coefficient heights can be
    # enormous, and constructing that whole population would defeat scalability.
    picks = rng.sample(range(2 * radius), n)
    return [index - radius if index < radius else index - radius + 1 for index in picks]


def _build_rows(b_code, c_code, b_shift, c_shift):
    """Return labelled 2x2 slices of the planted block tensor."""
    n = len(b_code)
    rows = []
    for frequency in range(n):
        m00 = m01 = m10 = m11 = 0
        for latent in range(n):
            sign = _character(frequency, latent)
            bv = b_code[latent ^ b_shift]
            cv = c_code[latent ^ c_shift]
            m00 += sign
            m01 += sign * cv
            m10 += sign * bv
            m11 += sign * bv * cv
        rows.append([frequency, [[m00, m01], [m10, m11]]])
    return rows


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a structured exact rank-one tensor decomposition."""
    blocks = params.get("blocks", 3)
    value_bits = params.get("value_bits", max(8, _bit_width(n) + 3))
    if not _is_power_of_two(n) or not 4 <= n <= CERTIFICATE_LANGUAGE["bounds"]["max_group_order"]:
        raise ValueError("n must be a power of two between 4 and 256")
    if not isinstance(blocks, int) or isinstance(blocks, bool) or not 1 <= blocks <= CERTIFICATE_LANGUAGE["bounds"]["max_blocks"]:
        raise ValueError("blocks is outside the certificate-language bound")
    if not isinstance(value_bits, int) or not max(3, _bit_width(n)) <= value_bits <= 256:
        raise ValueError("value_bits must be an integer between log2(n) and 256")
    width = _bit_width(n)
    if 2 * width * blocks > CERTIFICATE_LANGUAGE["bounds"]["max_atomic_elements"]:
        raise ValueError("answer would exceed the declared atomic-element bound")

    rng = random.Random(seed)
    block_data = []
    answer = []
    for _ in range(blocks):
        b_code = _sample_codebook(rng, n, value_bits)
        c_code = _sample_codebook(rng, n, value_bits)
        b_shift = rng.randrange(n)
        c_shift = rng.randrange(n)
        rows = _build_rows(b_code, c_code, b_shift, c_shift)
        rng.shuffle(rows)  # Display order is deliberately non-semantic.
        block_data.append({"B_code": b_code, "C_code": c_code, "slices": rows})
        answer.append(_bits(b_shift, width) + _bits(c_shift, width))

    return {
        "n": n,
        "block_count": blocks,
        "value_bits": value_bits,
        "blocks": block_data,
        "answer": answer,
    }


def render(inst) -> str:
    """Render a self-contained statement and an exact JSON output contract."""
    n = inst["n"]
    width = _bit_width(n)
    lines = [
        "Structured rank-one decomposition of an order-three integer tensor",
        "",
        "An order-three integer tensor is an array T[i,j,k].  The outer product",
        "a⊗b⊗c is the tensor with entry a[i]*b[j]*c[k].  A displayed block below",
        "has first-mode coordinates i=0,...,n-1 and two coordinates in each of",
        "the other modes.  Different blocks form a direct sum: every tensor entry",
        "whose three coordinates do not belong to one common block is zero.",
        "",
        f"Here n={n}=2^{width} and there are {inst['block_count']} blocks.",
        "Identify each integer x in 0,...,n-1 with its fixed-width binary vector.",
        "The operation x XOR s is bitwise exclusive-or.  Define",
        "  chi_i(x) = (-1)^(popcount(i AND x)).",
        "For block q, its public second-mode factors are B_q(y)=(1,B_code_q[y])",
        "and its public third-mode factors are C_q(z)=(1,C_code_q[z]).",
        "",
        "Find shifts s_q,t_q in 0,...,n-1 for which every displayed block equals",
        "  sum over x=0,...,n-1 of chi(x) ⊗ B_q(x XOR s_q) ⊗ C_q(x XOR t_q),",
        "where chi(x) is the length-n vector with coordinate i equal to chi_i(x).",
        "Thus your shifts specify an exact decomposition into n rank-one integer",
        "tensors per block.  All equalities are ordinary integer equalities.",
        "Slice order below is arbitrary; each slice is labelled by its frequency i.",
    ]
    for q, block in enumerate(inst["blocks"]):
        lines.extend(
            [
                "",
                f"BLOCK {q}",
                "B_code: " + json.dumps(block["B_code"], separators=(",", ":")),
                "C_code: " + json.dumps(block["C_code"], separators=(",", ":")),
                "Slices T_q[i,:,:] (each is [[T00,T01],[T10,T11]]):",
            ]
        )
        for frequency, matrix in block["slices"]:
            lines.append(
                f"i={frequency}: " + json.dumps(matrix, separators=(",", ":"))
            )

    zero_row = [0] * (2 * width)
    example = [zero_row[:] for _ in range(inst["block_count"])]
    lines.extend(
        [
            "",
            f"Output a JSON matrix with exactly {inst['block_count']} rows and {2 * width} bits per row.",
            f"In row q, bits 0..{width - 1} encode s_q little-endian and bits {width}..{2 * width - 1} encode t_q little-endian.",
            "Every entry must be the integer 0 or 1; block order is the displayed order.",
            "Give your final answer inside <answer></answer> tags, as that JSON matrix.",
            "Example: <answer>"
            + json.dumps(example, separators=(",", ":"))
            + "</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Extract the last well-formed tagged JSON matrix; never raise on garbage."""
    if not isinstance(text, str) or len(text) > 2_000_000:
        return None
    matches = _ANSWER_RE.findall(text)
    for body in reversed(matches):
        cleaned = body.strip()
        fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.I | re.S)
        if fence:
            cleaned = fence.group(1).strip()
        try:
            value = json.loads(cleaned)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, list):
            return value
    return None


def _validated_rows(block, n):
    rows = block.get("slices")
    if not isinstance(rows, list) or len(rows) != n:
        return None
    mapped = {}
    for item in rows:
        if not isinstance(item, list) or len(item) != 2:
            return None
        frequency, matrix = item
        if not isinstance(frequency, int) or isinstance(frequency, bool) or not 0 <= frequency < n or frequency in mapped:
            return None
        if (
            not isinstance(matrix, list)
            or len(matrix) != 2
            or any(not isinstance(row, list) or len(row) != 2 for row in matrix)
            or any(
                not isinstance(value, int) or isinstance(value, bool)
                for row in matrix
                for value in row
            )
        ):
            return None
        mapped[frequency] = matrix
    return mapped if len(mapped) == n else None


def verify(inst, answer) -> tuple[bool, str]:
    """Verify any valid shift matrix by exact expansion; never inspect inst['answer']."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON matrix"
    if not answer:
        return False, "answer matrix cannot be empty"
    block_count = inst.get("block_count")
    if not isinstance(block_count, int) or isinstance(block_count, bool) or block_count < 1:
        return False, "malformed instance block count"
    if len(answer) < block_count:
        return False, "too few block rows"
    if len(answer) > block_count:
        return False, "too many block rows"
    n = inst.get("n")
    if not _is_power_of_two(n):
        return False, "malformed instance order"
    width = _bit_width(n)
    shifts = []
    for q, row in enumerate(answer):
        if not isinstance(row, list) or len(row) != 2 * width:
            return False, f"row {q} must contain exactly {2 * width} bits"
        if any(not isinstance(bit, int) or isinstance(bit, bool) or bit not in (0, 1) for bit in row):
            return False, f"row {q} contains a non-binary entry"
        shifts.append((_from_bits(row[:width]), _from_bits(row[width:])))

    blocks = inst.get("blocks")
    if not isinstance(blocks, list) or len(blocks) != block_count:
        return False, "malformed instance blocks"
    mapped_blocks = []
    for q, (block, (b_shift, c_shift)) in enumerate(zip(blocks, shifts)):
        b_code = block.get("B_code")
        c_code = block.get("C_code")
        if (
            not isinstance(b_code, list)
            or not isinstance(c_code, list)
            or len(b_code) != n
            or len(c_code) != n
            or len(set(b_code)) != n
            or len(set(c_code)) != n
            or any(not isinstance(v, int) or isinstance(v, bool) for v in b_code + c_code)
        ):
            return False, f"malformed codebook in block {q}"
        mapped = _validated_rows(block, n)
        if mapped is None:
            return False, f"malformed tensor slices in block {q}"

        # Cheap necessary check makes random-candidate sampling fast.  A candidate
        # that survives it is still checked by full exact recomposition below.
        b_zero = sum(mapped[i][1][0] for i in range(n))
        c_zero = sum(mapped[i][0][1] for i in range(n))
        if b_zero != n * b_code[b_shift]:
            return False, f"block {q} second-mode zero coefficient mismatch"
        if c_zero != n * c_code[c_shift]:
            return False, f"block {q} third-mode zero coefficient mismatch"
        mapped_blocks.append(mapped)

    for q, (block, (b_shift, c_shift), mapped) in enumerate(zip(blocks, shifts, mapped_blocks)):
        expected = _build_rows(block["B_code"], block["C_code"], b_shift, c_shift)
        for frequency, matrix in expected:
            if mapped[frequency] != matrix:
                return False, f"block {q} fails exact rank-one recomposition at slice {frequency}"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample the full shape-valid binary certificate language."""
    width = _bit_width(inst["n"])
    return [
        [rng.randrange(2) for _ in range(2 * width)]
        for _ in range(inst["block_count"])
    ]


def search_space(inst):
    return inst["n"] ** (2 * inst["block_count"])


def enumerate_all(inst):
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    n = inst["n"]
    width = _bit_width(n)
    count = 0
    for values in itertools.product(range(n), repeat=2 * inst["block_count"]):
        candidate = [
            _bits(values[2 * q], width) + _bits(values[2 * q + 1], width)
            for q in range(inst["block_count"])
        ]
        count += int(verify(inst, candidate)[0])
    return count


def _signed_row_key(matrix):
    flat = tuple(value for row in matrix for value in row)
    negated = tuple(-value for value in flat)
    return min(flat, negated)


def _affine_matrix(matrix, b_sign, b_offset, c_sign, c_offset):
    """Apply (1,b)->(1,b_sign*b+b_offset) in the last two modes."""
    m00, m01 = matrix[0]
    m10, m11 = matrix[1]
    return [
        [m00, c_offset * m00 + c_sign * m01],
        [
            b_offset * m00 + b_sign * m10,
            b_offset * c_offset * m00
            + b_offset * c_sign * m01
            + b_sign * c_offset * m10
            + b_sign * c_sign * m11,
        ],
    ]


def _code_normalisations(code):
    """Canonical translations/reflections of a one-dimensional integer code."""
    low, high = min(code), max(code)
    return [
        (tuple(sorted(value - low for value in code)), 1, -low),
        (tuple(sorted(high - value for value in code)), -1, high),
    ]


def _block_invariant(block, n, transpose=False):
    """A strong cheap invariant under all declared affine/XOR relabellings."""
    b_code = block["C_code"] if transpose else block["B_code"]
    c_code = block["B_code"] if transpose else block["C_code"]
    raw_matrices = []
    for _, matrix in block["slices"]:
        raw_matrices.append(
            [[matrix[0][0], matrix[1][0]], [matrix[0][1], matrix[1][1]]]
            if transpose
            else matrix
        )

    variants = []
    for b_normal, b_sign, b_offset in _code_normalisations(b_code):
        for c_normal, c_sign, c_offset in _code_normalisations(c_code):
            matrices = tuple(
                sorted(
                    _signed_row_key(
                        _affine_matrix(
                            matrix, b_sign, b_offset, c_sign, c_offset
                        )
                    )
                    for matrix in raw_matrices
                )
            )
            variants.append((b_normal, c_normal, matrices))
    return min(variants)


def canonical_key(inst) -> str:
    """Canonicalise block order, row order, XOR labels, signs, and mode swap.

    Exact isomorphism of the coupled codebooks and all character rows would be a
    coloured-array isomorphism problem.  This key uses a stronger cheaply
    computable invariant: code-value multisets and signed slice multisets.  It
    intentionally forgets more labels than the proved transformations, so the
    README records the remote possibility of an over-collision.
    """
    n = inst["n"]
    descriptors = []
    for block in inst["blocks"]:
        normal = _block_invariant(block, n, False)
        swapped = _block_invariant(block, n, True)
        descriptors.append(min(normal, swapped))
    material = repr((n, tuple(sorted(descriptors)))).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def escalate(params):
    """Increase coefficient bit-cost first; only later enlarge the latent group."""
    clean = {key: value for key, value in params.items() if key != "_preset"}
    n = clean.get("n")
    blocks = clean.get("blocks", 3)
    value_bits = clean.get("value_bits", 12)
    if not _is_power_of_two(n) or not isinstance(value_bits, int):
        return None
    # Fixed answer length: larger coefficients make every mental transform and
    # exact multiplication harder while leaving the shift matrix unchanged.
    if value_bits < 28:
        clean["value_bits"] = value_bits + 4
        return clean
    next_n = 2 * n
    if next_n <= CERTIFICATE_LANGUAGE["bounds"]["max_group_order"]:
        next_atoms = 2 * _bit_width(next_n) * blocks
        if next_atoms <= CERTIFICATE_LANGUAGE["bounds"]["max_atomic_elements"]:
            clean["n"] = next_n
            clean["value_bits"] = value_bits + 1
            return clean
    return "cap_bound"


def _fwht(values):
    out = list(values)
    operations = 0
    span = 1
    while span < len(out):
        for start in range(0, len(out), 2 * span):
            for offset in range(span):
                i = start + offset
                j = i + span
                a, b = out[i], out[j]
                out[i] = a + b
                out[j] = a - b
                operations += 2
        span *= 2
    return out, operations


def _reference_algorithm(inst):
    """Recover via exact Walsh-Hadamard inversion of both informative streams."""
    n = inst["n"]
    width = _bit_width(n)
    answer = []
    operations = 0
    for block in inst["blocks"]:
        mapped = _validated_rows(block, n)
        if mapped is None:
            return None, operations
        transformed = {}
        for row, col in ((1, 0), (0, 1)):
            stream = [mapped[i][row][col] for i in range(n)]
            coeffs, used = _fwht(stream)
            transformed[(row, col)] = coeffs
            operations += used
        b_value = transformed[(1, 0)][0]
        c_value = transformed[(0, 1)][0]
        if b_value % n or c_value % n:
            return None, operations
        b_value //= n
        c_value //= n
        operations += 2
        try:
            b_shift = block["B_code"].index(b_value)
            c_shift = block["C_code"].index(c_value)
        except ValueError:
            return None, operations
        answer.append(_bits(b_shift, width) + _bits(c_shift, width))
    return answer, operations


def _attack_outlier(blocks, n):
    width = _bit_width(n)
    answer = []
    for block in blocks:
        b = max(range(n), key=lambda x: (abs(block["B_code"][x]), -x))
        c = max(range(n), key=lambda x: (abs(block["C_code"][x]), -x))
        answer.append(_bits(b, width) + _bits(c, width))
    return answer


def _attack_greedy_marginal(inst):
    n = inst["n"]
    width = _bit_width(n)
    answer = []
    for block in inst["blocks"]:
        mapped = _validated_rows(block, n)
        target_b = mapped[0][1][0]
        target_c = mapped[0][0][1]
        b = min(range(n), key=lambda x: (abs(n * block["B_code"][x] - target_b), x))
        c = min(range(n), key=lambda x: (abs(n * block["C_code"][x] - target_c), x))
        answer.append(_bits(b, width) + _bits(c, width))
    return answer


def _attack_raw_sign_bits(inst):
    """Plausible in-context ansatz: treat selected raw signs as shift bits."""
    n = inst["n"]
    width = _bit_width(n)
    answer = []
    for block in inst["blocks"]:
        mapped = _validated_rows(block, n)
        b_bits = [int(mapped[1 << bit][1][0] < 0) for bit in range(width)]
        c_bits = [int(mapped[1 << bit][0][1] < 0) for bit in range(width)]
        answer.append(b_bits + c_bits)
    return answer


def _permute_bits(value, permutation):
    result = 0
    for new_position, old_position in enumerate(permutation):
        if value >> old_position & 1:
            result |= 1 << new_position
    return result


def _random_linear_images(width, rng):
    """Images of the standard basis under a random invertible GF(2) map."""
    images = [1 << bit for bit in range(width)]
    for _ in range(4 * width + 1):
        first, second = rng.sample(range(width), 2)
        if rng.randrange(2):
            images[first], images[second] = images[second], images[first]
        else:
            images[first] ^= images[second]
    return images


def _linear_map(value, images):
    result = 0
    for bit, image in enumerate(images):
        if value >> bit & 1:
            result ^= image
    return result


def _dual_map_table(images):
    """Map old character labels i to A^{-T}i for x->Ax."""
    n = 1 << len(images)
    table = [None] * n
    for old_frequency in range(n):
        for new_frequency in range(n):
            if all(
                ((new_frequency & image).bit_count() & 1)
                == ((old_frequency >> bit) & 1)
                for bit, image in enumerate(images)
            ):
                table[old_frequency] = new_frequency
                break
        if table[old_frequency] is None:
            raise AssertionError("basis map was not invertible")
    return table


def _transformed_instance(
    inst,
    rng,
    *,
    reorder_rows=False,
    reorder_blocks=False,
    translate_labels=False,
    permute_bit_coordinates=False,
    linear_basis_change=False,
    translate_latent=False,
    affine_code_values=False,
    swap_modes=False,
):
    """Carry tensor, factor tables, and witness through genuine relabellings."""
    n = inst["n"]
    width = _bit_width(n)
    new_blocks = []
    new_answer = []
    for block, answer_row in zip(inst["blocks"], inst["answer"]):
        b_shift = _from_bits(answer_row[:width])
        c_shift = _from_bits(answer_row[width:])
        b_code = list(block["B_code"])
        c_code = list(block["C_code"])
        rows = [[frequency, [list(matrix[0]), list(matrix[1])]] for frequency, matrix in block["slices"]]

        if translate_labels:
            ub = rng.randrange(n)
            uc = rng.randrange(n)
            moved_b = [0] * n
            moved_c = [0] * n
            for x in range(n):
                moved_b[x ^ ub] = b_code[x]
                moved_c[x ^ uc] = c_code[x]
            b_code, c_code = moved_b, moved_c
            b_shift ^= ub
            c_shift ^= uc

        if permute_bit_coordinates:
            permutation = list(range(width))
            rng.shuffle(permutation)
            moved_b = [0] * n
            moved_c = [0] * n
            for x in range(n):
                moved_b[_permute_bits(x, permutation)] = b_code[x]
                moved_c[_permute_bits(x, permutation)] = c_code[x]
            b_code, c_code = moved_b, moved_c
            rows = [
                [_permute_bits(frequency, permutation), matrix]
                for frequency, matrix in rows
            ]
            b_shift = _permute_bits(b_shift, permutation)
            c_shift = _permute_bits(c_shift, permutation)

        if linear_basis_change:
            images = _random_linear_images(width, rng)
            dual = _dual_map_table(images)
            moved_b = [0] * n
            moved_c = [0] * n
            for x in range(n):
                moved_b[_linear_map(x, images)] = b_code[x]
                moved_c[_linear_map(x, images)] = c_code[x]
            b_code, c_code = moved_b, moved_c
            rows = [[dual[frequency], matrix] for frequency, matrix in rows]
            b_shift = _linear_map(b_shift, images)
            c_shift = _linear_map(c_shift, images)

        if translate_latent:
            translation = rng.randrange(n)
            for item in rows:
                if _character(item[0], translation) == -1:
                    item[1] = [[-value for value in row] for row in item[1]]
            b_shift ^= translation
            c_shift ^= translation

        if affine_code_values:
            b_sign = -1 if rng.randrange(2) else 1
            c_sign = -1 if rng.randrange(2) else 1
            b_offset = rng.randrange(-17, 18)
            c_offset = rng.randrange(-17, 18)
            b_code = [b_sign * value + b_offset for value in b_code]
            c_code = [c_sign * value + c_offset for value in c_code]
            rows = [
                [
                    frequency,
                    _affine_matrix(
                        matrix, b_sign, b_offset, c_sign, c_offset
                    ),
                ]
                for frequency, matrix in rows
            ]

        if swap_modes:
            b_code, c_code = c_code, b_code
            rows = [
                [frequency, [[matrix[0][0], matrix[1][0]], [matrix[0][1], matrix[1][1]]]]
                for frequency, matrix in rows
            ]
            b_shift, c_shift = c_shift, b_shift

        if reorder_rows:
            rng.shuffle(rows)
        new_blocks.append({"B_code": b_code, "C_code": c_code, "slices": rows})
        new_answer.append(_bits(b_shift, width) + _bits(c_shift, width))

    if reorder_blocks:
        order = list(range(inst["block_count"]))
        rng.shuffle(order)
        new_blocks = [new_blocks[index] for index in order]
        new_answer = [new_answer[index] for index in order]

    return {
        "n": n,
        "block_count": inst["block_count"],
        "value_bits": inst["value_bits"],
        "blocks": new_blocks,
        "answer": new_answer,
    }


def _answer_atoms(answer):
    if isinstance(answer, list):
        return sum(_answer_atoms(item) for item in answer)
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    return 1


def selftest() -> dict:
    report = {}

    planted_ok = 0
    planted_total = 0
    for params in DIFFICULTY.values():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            planted_ok += int(verify(inst, inst["answer"])[0])
            planted_total += 1
    report["G1_planted_verifies"] = {
        "pass": planted_ok == planted_total,
        "verified": planted_ok,
        "attempts": planted_total,
        "construction": "inverse generation followed by exact outer-product recomposition",
    }

    shipping = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    base = json.loads(json.dumps(shipping["answer"]))
    swap_candidate = json.loads(json.dumps(base))
    flat_positions = [
        (q, position)
        for q, row in enumerate(swap_candidate)
        for position in range(len(row))
    ]
    first = next(
        (pair for pair in itertools.combinations(flat_positions, 2) if swap_candidate[pair[0][0]][pair[0][1]] != swap_candidate[pair[1][0]][pair[1][1]]),
        None,
    )
    if first is not None:
        (q1, p1), (q2, p2) = first
        swap_candidate[q1][p1], swap_candidate[q2][p2] = swap_candidate[q2][p2], swap_candidate[q1][p1]
    out_of_range = json.loads(json.dumps(base))
    out_of_range[0][0] = 2
    corruptions = {
        "drop": base[:-1],
        "swap": swap_candidate,
        "duplicate": base + [base[0]],
        "empty": [],
        "out_of_range": out_of_range,
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = {entry["reason"] for entry in corruption_results.values()}
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in corruption_results.values()) and len(reasons) == len(corruption_results),
        "cases": corruption_results,
        "distinct_reasons": len(reasons),
    }

    wire = json.dumps(base, separators=(",", ":"))
    realistic = (
        "Using the character-table decomposition gives the shifts below.\n"
        f"<answer>```json\n{wire}\n```</answer>\n"
        "The matrix uses little-endian bits."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == base and json.loads(json.dumps(base)) == base,
        "parsed_equals_answer": parsed == base,
        "json_native": json.loads(json.dumps(base)) == base,
    }

    guess_rng = random.Random(8675309)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_total >= 200_000 and guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_rate,
        "exact_probability": 1 / search_space(shipping),
        "candidate_space": search_space(shipping),
        "prior": "uniform over every shape-valid binary shift matrix",
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    baseline_start = time.perf_counter()
    reference_answer, reference_operations = _reference_algorithm(shipping)
    baseline_seconds = time.perf_counter() - baseline_start
    reference_ok = reference_answer is not None and verify(shipping, reference_answer)[0]
    attack_rng = random.Random(0x5A17)
    attack_start = time.perf_counter()
    attack_hit = False
    for _ in range(256):
        if verify(shipping, random_candidate(shipping, attack_rng))[0]:
            attack_hit = True
            break
    attack_seconds = time.perf_counter() - attack_start
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_total >= 200_000 and guess_rate < 1e-6 and reference_ok and not attack_hit and enumerate_all(demo) == 1,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_fraction": guess_rate,
        "shipping_exact_solution_probability": 1 / search_space(shipping),
        "shipping_exact_enumeration": enumerate_all(shipping),
        "demo_exact_solution_count": enumerate_all(demo),
        "demo_candidate_space": search_space(demo),
        "baseline_algorithm": "exact Walsh-Hadamard inversion of two informative coordinate streams",
        "baseline_wall_clock_seconds": round(baseline_seconds, 6),
        "baseline_exact_operations": reference_operations,
        "baseline_verified": reference_ok,
        "strongest_failing_attack": "256 structure-aware random restarts",
        "strongest_attack_restarts": 256,
        "strongest_attack_succeeded": attack_hit,
        "strongest_attack_wall_clock_seconds": round(attack_seconds, 6),
    }

    attacks = {
        "outlier_max_code_magnitude": {"successes": 0, "attempts": 8},
        "greedy_nearest_raw_marginal": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "raw_basis_row_sign_ansatz": {"successes": 0, "attempts": 8},
    }
    reference_successes = 0
    reference_times = []
    reference_ops = []
    failing_attack_times = []
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        attack_start = time.perf_counter()
        candidates = {
            "outlier_max_code_magnitude": _attack_outlier(inst["blocks"], inst["n"]),
            "greedy_nearest_raw_marginal": _attack_greedy_marginal(inst),
            "raw_basis_row_sign_ansatz": _attack_raw_sign_bits(inst),
        }
        for name, candidate in candidates.items():
            attacks[name]["successes"] += int(verify(inst, candidate)[0])
        restart_rng = random.Random(seed ^ 0x5A17)
        restart_hit = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, restart_rng))[0]:
                restart_hit = True
                break
        attacks["random_restart_256"]["successes"] += int(restart_hit)
        failing_attack_times.append(time.perf_counter() - attack_start)

        ref_start = time.perf_counter()
        recovered, operations = _reference_algorithm(inst)
        reference_times.append(time.perf_counter() - ref_start)
        reference_ops.append(operations)
        reference_successes += int(recovered is not None and verify(inst, recovered)[0])

    all_attacks_failed = all(
        result["successes"] == 0 and result["attempts"] >= 8
        for result in attacks.values()
    )
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8,
        "attacks": attacks,
        "strongest_failing_attack_wall_clock_sec_mean": round(sum(failing_attack_times) / len(failing_attack_times), 6),
        "reference_algorithm": {
            "name": "exact Walsh-Hadamard inversion of two informative streams",
            "complexity": "O(2*blocks*n*log2(n)) exact arithmetic",
            "wall_clock_sec_mean": round(sum(reference_times) / len(reference_times), 6),
            "wall_clock_sec_max": round(max(reference_times), 6),
            "operations_mean": round(sum(reference_ops) / len(reference_ops)),
            "operations_max": max(reference_ops),
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    doubled = make_instance(
        n=2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"],
        blocks=DIFFICULTY[SHIPPING_DIFFICULTY]["blocks"],
        value_bits=DIFFICULTY[SHIPPING_DIFFICULTY]["value_bits"],
        seed=2718,
    )
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * shipping["n"] and search_space(doubled) > search_space(shipping),
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_tensor_nonzero_block_entries": 4 * shipping["n"] * shipping["block_count"],
        "doubled_tensor_nonzero_block_entries": 4 * doubled["n"] * doubled["block_count"],
        "shipping_search_space_bits": int(math.log2(search_space(shipping))),
        "doubled_search_space_bits": int(math.log2(search_space(doubled))),
        "doubled_planted_verifies": doubled_ok,
    }

    transformations = {
        "row_reordering": {"reorder_rows": True},
        "block_reordering": {"reorder_blocks": True},
        "independent_codebook_translations": {"translate_labels": True},
        "bit_coordinate_permutation": {"permute_bit_coordinates": True},
        "general_linear_bit_basis_change": {"linear_basis_change": True},
        "latent_global_translation": {"translate_latent": True},
        "integer_code_affine_basis_change": {"affine_code_values": True},
        "second_third_mode_swap": {"swap_modes": True},
        "all_composed": {
            "reorder_rows": True,
            "reorder_blocks": True,
            "translate_labels": True,
            "permute_bit_coordinates": True,
            "linear_basis_change": True,
            "translate_latent": True,
            "affine_code_values": True,
            "swap_modes": True,
        },
    }
    invariant_checks = 0
    carried_checks = 0
    changed_serializations = 0
    for seed in range(20):
        inst = make_instance(seed=1000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        original_blob = json.dumps(inst["blocks"], sort_keys=True)
        for offset, options in enumerate(transformations.values()):
            transformed = _transformed_instance(
                inst, random.Random(9000 + 100 * seed + offset), **options
            )
            invariant_checks += int(canonical_key(transformed) == key)
            carried_checks += int(verify(transformed, transformed["answer"])[0])
            changed_serializations += int(json.dumps(transformed["blocks"], sort_keys=True) != original_blob)
    unrelated = [
        canonical_key(make_instance(seed=2000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY]))
        for seed in range(20)
    ]
    total_transform_checks = 20 * len(transformations)
    report["G8_canonical_key"] = {
        "pass": invariant_checks == total_transform_checks and carried_checks == total_transform_checks and changed_serializations >= 20 and len(set(unrelated)) == 20,
        "transformations": list(transformations),
        "invariance_checks_passed": invariant_checks,
        "invariance_checks_attempted": total_transform_checks,
        "carried_witness_checks_passed": carried_checks,
        "carried_witness_checks_attempted": total_transform_checks,
        "changed_serializations": changed_serializations,
        "unrelated_distinct_keys": len(set(unrelated)),
        "unrelated_attempts": len(unrelated),
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(shipping["answer"])
    intended_operations = shipping["block_count"] * (2 * (shipping["n"] - 1) + 2)
    evidence = _G9_EVIDENCE or {
        "arms": {
            "bare": {"solved": 0, "attempts": 0},
            "hinted": {"solved": 0, "attempts": 0},
            "placebo": {"solved": 0, "attempts": 0},
        },
        "hinted_verdict": "pending",
    }
    arms = evidence["arms"]
    hinted_rate = arms["hinted"]["solved"] / arms["hinted"]["attempts"] if arms["hinted"]["attempts"] else None
    placebo_rate = arms["placebo"]["solved"] / arms["placebo"]["attempts"] if arms["placebo"]["attempts"] else None
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_operations <= 300
    evidence_complete = all(arms[name]["attempts"] >= 3 for name in ("bare", "hinted", "placebo"))
    report["G9_no_tool_suitability"] = {
        "pass": evidence_complete and evidence["hinted_verdict"] == "hardened" and within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None
            else None
        ),
        "hinted_verdict": evidence["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
        "evidence_complete": evidence_complete,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = DIFFICULTY[SHIPPING_DIFFICULTY]
    report["certificate_language"] = CERTIFICATE_LANGUAGE
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
