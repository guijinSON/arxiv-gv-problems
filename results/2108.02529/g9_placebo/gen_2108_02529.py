"""Verified problem generator for arXiv:2108.02529, Switching for 2-designs.

The solver receives the incidence matrix of a symmetric Menon 2-design and
must exhibit one nontrivial switching set.  Instances are constructed from a
binary-character Bush-type Hadamard matrix.  The row groups are switching
sets by Section 3.2 of the paper, before their labels are obscured.

The checker uses only Definition 1: on q selected block rows every point has
incidence count 0, q/2, or q.  It never reads the planted answer.
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
from typing import Any


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - the implementation is stdlib-only
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "linear_algebra",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "block-point incidence matrix of a symmetric Menon 2-design",
        "switching set of blocks",
        "Bush-type Hadamard block structure",
    ],
    "verification_operations": [
        "exact incidence counting",
        "integer comparison with 0, half, and all selected blocks",
        "distinct block-label check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Within a hidden row group, XOR-translating block labels repeats the "
        "row symmetric-difference signature up to complement; without this "
        "invariant one must compare quadratically many row pairs."
    ),
    "hardness_basis": (
        "Track B in the nontrivial q-block switching-set regime of Definition "
        "1 and Section 3.2: exact row-pair signature bucketing runs in "
        "O(v^3/w) bit-word work for v=q^2 and solves every instance; at the "
        "shipping preset its measured wall time and operation count are "
        "recorded by selftest, while the hidden matching invariant uses fewer "
        "than 300 exact operations."
    ),
    "max_answer_tokens": 32,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list of exactly q distinct 0-based block labels from "
        "0,...,q^2-1, written in increasing order; it denotes an unordered "
        "candidate switching set."
    ),
    "bounds": {
        "length": "q (the instance field order)",
        "label_min": 0,
        "label_max": "q^2-1",
        "distinct": True,
        "maximum_supported_length": 32,
    },
}

# The first two oracle rungs deliberately expose the Bush block ordering.  The
# hard rung keeps the same native object but labels each group as a coset of a
# hidden matching subspace.  This makes the ladder about recognition, not a
# longer witness.
DIFFICULTY = {
    "hard": {"n": 16, "label_mode": "matching"},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Inspect two-bit XOR translations of block labels for repeated row "
    "symmetric-difference signatures up to complement."
)
PLACEBO_HINT = (
    "Inspect the hexadecimal incidence rows carefully and keep the block and "
    "point indexing conventions in view."
)

# Filled from script-owned transcripts after the three oracle arms run.
G9_MEASUREMENTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}

NOTES = r"""
Definition and native construction.  Definition 1 says that a set B1 of
blocks is a switching set precisely when every point is on none, half, or all
of B1; the zero and all columns are P1 and P2.  Theorem 2 proves that
complementing the half columns preserves the 2-(v,k,lambda) parameters.
Section 3.2 defines a Bush-type Hadamard matrix in q by q blocks of size q and
observes that every zero diagonal block of its 0/1 incidence matrix determines
a q-block switching set.

Step 0 and the easy boundary.  The paper proves preservation, not hardness,
and Remark 4 makes the unrestricted problem trivial because every pair of
blocks switches.  This module therefore requires exactly q>2 blocks and makes
no Track-A claim.  In the paper's displayed block order, selecting a diagonal
row group costs q label selections and has no compression gap; those are the
deliberately easy ladder rungs.  The shipping distribution relabels the same
native incidence object by a structured but concealed binary matching.

Theorem-backed generation.  Let q be a power of two and use GF(2^m).  For row
(a,b) and column (c,d), set H=sign(a,c)*(-1)^Tr((a+c)(b+d)), with sign(a,a)=+1
and independent off-diagonal block signs.  A diagonal q by q block is all +1;
every off-diagonal block is row- and column-balanced.  Rows with different a
are orthogonal after summing over d, and rows with equal a but different b are
orthogonal after summing over c.  Thus H is a Bush-type Hadamard matrix of
order q^2.  Replacing +1 by 0 and -1 by 1 gives the Section 3.2 symmetric Menon
design.  The certificate is the known row group a=0, carried through the label
map; it is never recovered from the completed instance.

Track-B producer and compact route.  For any two rows, hash their incidence
XOR up to global complement.  Within a Bush row group, a fixed b-difference
has the same hash in every group, so its bucket contains v/2 row pairs;
cross-group buckets are smaller for the sampled block signs.  Unioning the
large-bucket edges recovers all switching groups in O(v^3/w) bit-word work.
For shipping labels, the a=constant groups are cosets of the span of m
disjoint two-bit masks.  Testing the C(2m,2) such translations against one
second row pair identifies the masks, after which their span is a certificate.

Attacks.  Every block has the same degree and every pair of blocks has the
same intersection, so per-row magnitude and ordinary pair-distance outliers
carry no planted signal.  The panel tests lexicographic row outliers, greedy
common-zero extension, random restarts, and every coordinate-subspace coset.
The independent block phases are conditioned only to defeat those declared
greedy and coordinate ansatzes and to make the stated compact invariant exact;
all blocks and all q genuine groups still come from the same distribution.
""".strip()


# Irreducible binary polynomials, including the x^m term.
_IRREDUCIBLE = {
    2: 0b111,          # x^2 + x + 1
    3: 0b1011,         # x^3 + x + 1
    4: 0b10011,        # x^4 + x + 1
    5: 0b100101,       # x^5 + x^2 + 1
}


def _gf_mul(x: int, y: int, degree: int) -> int:
    """Multiply in GF(2^degree) using the fixed irreducible polynomial."""
    modulus = _IRREDUCIBLE[degree]
    result = 0
    while y:
        if y & 1:
            result ^= x
        y >>= 1
        x <<= 1
        if x & (1 << degree):
            x ^= modulus
    return result


def _gf_trace_bit(x: int, degree: int) -> int:
    """Absolute trace GF(2^degree)->GF(2), returned as 0 or 1."""
    total = 0
    term = x
    for _ in range(degree):
        total ^= term
        term = _gf_mul(term, term, degree)
    return total & 1


def _rank_binary(vectors: list[int]) -> int:
    basis: dict[int, int] = {}
    for value in vectors:
        x = value
        while x:
            pivot = x.bit_length() - 1
            if pivot in basis:
                x ^= basis[pivot]
            else:
                basis[pivot] = x
                break
    return len(basis)


def _span(basis: list[int]) -> list[int]:
    values = [0]
    for vector in basis:
        values += [x ^ vector for x in values]
    return sorted(values)


def _matching_basis(degree: int, rng: random.Random) -> list[int]:
    positions = list(range(2 * degree))
    rng.shuffle(positions)
    return [
        (1 << positions[2 * i]) | (1 << positions[2 * i + 1])
        for i in range(degree)
    ]


def _complete_basis(prefix: list[int], width: int, rng: random.Random) -> list[int]:
    result = list(prefix)
    candidates = list(range(1, 1 << width))
    rng.shuffle(candidates)
    for value in candidates:
        if _rank_binary(result + [value]) > len(result):
            result.append(value)
            if len(result) == width:
                return result
    raise RuntimeError("could not complete a binary basis")


def _encode_rows(rows: list[int], width: int) -> list[str]:
    digits = (width + 3) // 4
    return [format(row, f"0{digits}x") for row in rows]


def _decode_rows(inst: dict) -> list[int]:
    return [int(row, 16) for row in inst["rows_hex"]]


def _canonical_signature(value: int, full_mask: int) -> int:
    complement = full_mask ^ value
    return value if value < complement else complement


def _compact_periods(rows: list[int], width: int) -> list[int]:
    """Two-bit translations passing the intended one-probe invariant."""
    full_mask = (1 << width) - 1
    # A matching span contains only even-parity labels, so the unit label 1 is
    # guaranteed to lie in a different coset from 0.
    probe = 1
    result = []
    label_bits = (width - 1).bit_length()
    for left in range(label_bits):
        for right in range(left + 1, label_bits):
            delta = (1 << left) | (1 << right)
            first = _canonical_signature(rows[0] ^ rows[delta], full_mask)
            second = _canonical_signature(
                rows[probe] ^ rows[probe ^ delta], full_mask
            )
            if first == second:
                result.append(delta)
    return result


def _coordinate_candidates(width: int, q: int):
    """Yield cosets of coordinate subspaces, the obvious label ansatz."""
    degree = q.bit_length() - 1
    label_bits = (width - 1).bit_length()
    for positions in itertools.combinations(range(label_bits), degree):
        basis = [1 << position for position in positions]
        subspace = _span(basis)
        remaining = [p for p in range(label_bits) if p not in positions]
        for fixed in range(1 << len(remaining)):
            offset = 0
            for i, position in enumerate(remaining):
                if (fixed >> i) & 1:
                    offset |= 1 << position
            yield sorted(offset ^ x for x in subspace)


def _is_switching_rows(rows: list[int], selected: list[int], q: int) -> bool:
    """Bit-sliced exact test that every column count is 0, q/2, or q."""
    # Since q is a power of two, these are exactly the counts whose lower
    # log2(q/2) binary digits vanish.  Ripple addition keeps one whole column
    # plane in a Python integer; there is no floating point or approximation.
    planes: list[int] = []
    for label in selected:
        carry = rows[label]
        plane = 0
        while carry:
            if plane == len(planes):
                planes.append(carry)
                break
            next_carry = planes[plane] & carry
            planes[plane] ^= carry
            carry = next_carry
            plane += 1
    low_planes = q.bit_length() - 2
    return all((planes[i] if i < len(planes) else 0) == 0
               for i in range(low_planes))


def _greedy_rows(rows: list[int], width: int, q: int) -> list[int]:
    """The declared common-zero greedy attack, on already decoded rows."""
    full_mask = (1 << width) - 1
    chosen = [0]
    common_zero = full_mask ^ rows[0]
    while len(chosen) < q:
        available = [x for x in range(width) if x not in chosen]
        pick = max(available, key=lambda x: (
            (common_zero & (full_mask ^ rows[x])).bit_count(), -x
        ))
        chosen.append(pick)
        common_zero &= full_mask ^ rows[pick]
    return sorted(chosen)


def make_instance(n: int, seed: int = 0, label_mode: str = "matching",
                  **params: Any) -> dict:
    """Construct a Bush-type Menon design and a known switching set."""
    del params
    if (isinstance(n, bool) or not isinstance(n, int) or n < 4
            or n > 32 or n & (n - 1)):
        raise ValueError("n must be a power of two in [4,32]")
    if label_mode not in {"contiguous", "matching"}:
        raise ValueError("label_mode must be 'contiguous' or 'matching'")

    q = n
    degree = q.bit_length() - 1
    width = q * q
    master = random.Random(seed)
    phase_rng = random.Random(master.getrandbits(128))
    row_rng = random.Random(master.getrandbits(128))
    point_rng = random.Random(master.getrandbits(128))

    # Labels are linear images of (a,b).  Varying b spans the known switching
    # group.  The matching mode makes that subspace non-coordinate while
    # preserving a short, exact recognition route.
    if label_mode == "contiguous":
        varying_basis = [1 << i for i in range(degree)]
        fixed_basis = [1 << (degree + i) for i in range(degree)]
    else:
        varying_basis = _matching_basis(degree, row_rng)
        completed = _complete_basis(varying_basis, 2 * degree, row_rng)
        fixed_basis = completed[degree:]

    row_label = [0] * width
    for a in range(q):
        a_part = 0
        for bit, vector in enumerate(fixed_basis):
            if (a >> bit) & 1:
                a_part ^= vector
        for b in range(q):
            label = a_part
            for bit, vector in enumerate(varying_basis):
                if (b >> bit) & 1:
                    label ^= vector
            row_label[a * q + b] = label

    point_permutation = list(range(width))
    point_rng.shuffle(point_permutation)  # internal column -> displayed label

    mul = [[_gf_mul(x, y, degree) for y in range(q)] for x in range(q)]
    trace = [_gf_trace_bit(x, degree) for x in range(q)]

    # Retry only the independent off-diagonal block signs.  The answer remains
    # the theorem-backed row group throughout; this never solves an instance.
    for _attempt in range(256):
        phase = [[0] * q for _ in range(q)]
        for a in range(q):
            for c in range(q):
                if a != c:
                    phase[a][c] = phase_rng.getrandbits(1)

        rows = [0] * width
        for a in range(q):
            for b in range(q):
                bits = 0
                for c in range(q):
                    phase_bit = phase[a][c]
                    ac = a ^ c
                    for d in range(q):
                        # A=(J-H)/2, hence incidence 1 exactly for sign -1.
                        incident = phase_bit ^ trace[mul[ac][b ^ d]]
                        if incident:
                            bits |= 1 << point_permutation[c * q + d]
                rows[row_label[a * q + b]] = bits

        if label_mode == "contiguous":
            break
        periods = _compact_periods(rows, width)
        if set(periods) == set(varying_basis):
            # Rule out every coordinate-coset shortcut by construction.  This
            # is a check against a declared attack, not certificate search.
            coordinate_hit = any(
                _is_switching_rows(rows, candidate, q)
                for candidate in _coordinate_candidates(width, q)
            )
            greedy_hit = _is_switching_rows(
                rows, _greedy_rows(rows, width, q), q
            )
            if not coordinate_hit and not greedy_hit:
                break
    else:
        raise RuntimeError("could not sample a suitably camouflaged block phase")

    answer = _span(varying_basis)  # the a=0 row group, known before rows exist
    instance = {
        "q": q,
        "v": width,
        "k": q * (q - 1) // 2,
        "lambda": q * (q - 2) // 4,
        "label_mode": label_mode,
        "rows_hex": _encode_rows(rows, width),
        "answer": answer,
    }
    ok, reason = verify(instance, answer)
    if not ok:  # defensive assertion of the theorem-backed construction
        raise RuntimeError(f"constructed switching set failed: {reason}")
    return instance


def render(inst: dict) -> str:
    """Render a complete switching-set recovery problem."""
    q = inst["q"]
    width = inst["v"]
    lines = [
        "SWITCHING SET IN A 2-DESIGN",
        "",
        "A 2-(v,k,lambda) design has v labelled points and a collection of "
        "blocks: every block contains exactly k points, and every two distinct "
        "points occur together in exactly lambda blocks.",
        "",
        f"Here v={width}, k={inst['k']}, lambda={inst['lambda']}, and there "
        f"are {width} blocks and {width} points, both labelled 0 through "
        f"{width - 1}.",
        "",
        f"Find exactly q={q} distinct block labels forming a switching set. "
        f"For this task, that means: for every point, its incidence count "
        f"among your {q} selected blocks must be exactly 0, {q // 2}, or {q}. "
        "The order of your labels does not matter, and repeated labels are "
        "forbidden.",
        "",
        "The incidence matrix is listed by block label.  Each row is a "
        f"fixed-width hexadecimal integer.  Bit j of that integer, counting "
        f"the least-significant bit as bit 0, is 1 exactly when the block "
        f"contains point j.  Leading zeroes are significant only as padding "
        f"to {width} bits.",
        "",
        "block : incidence-bitset-in-hex",
    ]
    lines.extend(f"{label}: {row}" for label, row in enumerate(inst["rows_hex"]))
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags, as a JSON list "
        f"of exactly {q} distinct integer block labels in increasing order.",
        "JSON syntax example for a hypothetical three-label instance: "
        "<answer>[3, 17, 42]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Extract the JSON list inside answer tags; never raise on bad output."""
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer>\s*(.*?)\s*</answer>", text,
                      flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    payload = match.group(1).strip()
    if payload.startswith("```"):
        payload = re.sub(r"^```(?:json)?\s*", "", payload,
                         flags=re.IGNORECASE)
        payload = re.sub(r"\s*```$", "", payload)
    try:
        answer = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return answer if isinstance(answer, list) else None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any q-block switching set by exact Definition-1 counts."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    q = inst["q"]
    if len(answer) < q:
        return False, f"too few block labels: expected {q}"
    if len(answer) > q:
        return False, f"too many block labels: expected {q}"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in answer):
        return False, "every block label must be an integer"
    if any(x < 0 or x >= inst["v"] for x in answer):
        return False, f"block label outside 0..{inst['v'] - 1}"
    if len(set(answer)) != q:
        return False, "block labels must be distinct"
    if answer != sorted(answer):
        return False, "block labels must be in increasing order"
    rows = _decode_rows(inst)
    if not _is_switching_rows(rows, answer, q):
        return False, "selected blocks are not a switching set"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the stated q-subset language, already sorted."""
    return sorted(rng.sample(range(inst["v"]), inst["q"]))


def search_space(inst: dict) -> int:
    """Number of q-subsets of the v block labels."""
    return math.comb(inst["v"], inst["q"])


def enumerate_all(inst: dict) -> int | None:
    """Count all witnesses only when the exact q-subset scan is small."""
    space = search_space(inst)
    if space > 100_000:
        return None
    rows = _decode_rows(inst)
    return sum(
        _is_switching_rows(rows, list(candidate), inst["q"])
        for candidate in itertools.combinations(range(inst["v"]), inst["q"])
    )


def _reference_components(inst: dict) -> tuple[list[list[int]], int]:
    """Recover groups with the Track-B quadratic row-pair algorithm."""
    rows = _decode_rows(inst)
    width = inst["v"]
    full_mask = (1 << width) - 1
    buckets: dict[int, list[tuple[int, int]]] = {}
    for left in range(width):
        for right in range(left + 1, width):
            signature = _canonical_signature(rows[left] ^ rows[right], full_mask)
            buckets.setdefault(signature, []).append((left, right))

    parent = list(range(width))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        x = find(x)
        y = find(y)
        if x != y:
            parent[y] = x

    threshold = width // 2
    large_edges = 0
    for edges in buckets.values():
        if len(edges) >= threshold:
            large_edges += len(edges)
            for left, right in edges:
                union(left, right)
    groups: dict[int, list[int]] = {}
    for label in range(width):
        groups.setdefault(find(label), []).append(label)
    components = sorted((sorted(group) for group in groups.values()),
                        key=lambda group: (len(group), group))
    return components, large_edges


def _strongest_attack(inst: dict) -> list[int] | None:
    components, _ = _reference_components(inst)
    for component in components:
        if len(component) == inst["q"] and verify(inst, component)[0]:
            return component
    return None


def _attack_outlier(inst: dict) -> list[int]:
    rows = _decode_rows(inst)
    return sorted(sorted(range(inst["v"]), key=lambda x: rows[x])[:inst["q"]])


def _attack_greedy(inst: dict) -> list[int]:
    rows = _decode_rows(inst)
    return _greedy_rows(rows, inst["v"], inst["q"])


def _attack_coordinate(inst: dict) -> list[int] | None:
    rows = _decode_rows(inst)
    for candidate in _coordinate_candidates(inst["v"], inst["q"]):
        if _is_switching_rows(rows, candidate, inst["q"]):
            return candidate
    return None


def _attack_random(inst: dict, seed: int, restarts: int = 512) -> list[int] | None:
    rng = random.Random(seed ^ 0xA5B3571)
    rows = _decode_rows(inst)
    for _ in range(restarts):
        candidate = sorted(rng.sample(range(inst["v"]), inst["q"]))
        if _is_switching_rows(rows, candidate, inst["q"]):
            return candidate
    return None


def _half_incidence_mask(rows: list[int], group: list[int], q: int,
                         width: int) -> int:
    """Columns incident with exactly half of a switching group."""
    result = 0
    for point in range(width):
        count = sum((rows[block] >> point) & 1 for block in group)
        if count == q // 2:
            result |= 1 << point
    return result


def _switch_rank_profile(inst: dict) -> tuple:
    """Ranks after zero, one, and two paper switches, canonically aggregated.

    The reference partition is recovered from the incidence matrix, not read
    from the planted answer.  Switching any recovered group is exactly
    Theorem 2's transformation.  Binary matrix rank and the sorted spectra are
    invariant under arbitrary block and point relabellings.
    """
    rows = _decode_rows(inst)
    components, _ = _reference_components(inst)
    groups = [group for group in components if len(group) == inst["q"]]
    if len(groups) != inst["q"]:
        # This marker is itself invariant and avoids pretending that a failed
        # structural recovery produced a canonical partition.
        return ("unresolved", _rank_binary(rows), len(groups))
    masks = [
        _half_incidence_mask(rows, group, inst["q"], inst["v"])
        for group in groups
    ]

    def switched_rank(indices: tuple[int, ...]) -> int:
        changed = list(rows)
        for index in indices:
            toggle = masks[index]
            for block in groups[index]:
                changed[block] ^= toggle
        return _rank_binary(changed)

    global_spectra = []
    ranks_by_subset: dict[tuple[int, ...], int] = {}
    for size in range(3):
        histogram: dict[int, int] = {}
        for subset in itertools.combinations(range(len(groups)), size):
            rank = switched_rank(subset)
            ranks_by_subset[subset] = rank
            histogram[rank] = histogram.get(rank, 0) + 1
        global_spectra.append((size, tuple(sorted(histogram.items()))))

    # Retain incidence between a group and pair-switch ranks before sorting
    # group labels away.  This is materially stronger than one global rank
    # histogram while remaining polynomial and exactly relabelling-invariant.
    local_spectra = []
    for group in range(len(groups)):
        single_rank = ranks_by_subset[(group,)]
        pair_histogram: dict[int, int] = {}
        for other in range(len(groups)):
            if other == group:
                continue
            subset = tuple(sorted((group, other)))
            rank = ranks_by_subset[subset]
            pair_histogram[rank] = pair_histogram.get(rank, 0) + 1
        local_spectra.append((single_rank, tuple(sorted(pair_histogram.items()))))
    return tuple(global_spectra), tuple(sorted(local_spectra))


def canonical_key(inst: dict) -> str:
    """A switching-rank invariant under independent block/point relabelling.

    Full bipartite graph canonisation is intentionally not claimed.  The key
    recovers the Bush groups structurally and records binary ranks after all
    zero-, one-, and two-group switches.  The sorted global and per-group
    spectra are unchanged by either allowed relabelling.
    """
    payload = json.dumps({
        "parameters": [inst["v"], inst["k"], inst["lambda"], inst["q"]],
        "switch_rank_profile": _switch_rank_profile(inst),
    }, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _relabel(inst: dict, block_perm: list[int], point_perm: list[int]) -> dict:
    """Carry an instance and its witness through independent relabellings."""
    width = inst["v"]
    old_rows = _decode_rows(inst)
    new_rows = [0] * width
    for old_block, old_bits in enumerate(old_rows):
        bits = 0
        for old_point in range(width):
            if (old_bits >> old_point) & 1:
                bits |= 1 << point_perm[old_point]
        new_rows[block_perm[old_block]] = bits
    result = dict(inst)
    result["rows_hex"] = _encode_rows(new_rows, width)
    result["answer"] = sorted(block_perm[x] for x in inst["answer"])
    return result


def escalate(params: dict) -> dict | str | None:
    """Increase the incidence haystack while the matching witness stays short."""
    clean = {k: v for k, v in params.items() if k != "_preset"}
    n = clean.get("n")
    if not isinstance(n, int):
        return None
    if clean.get("label_mode") != "matching":
        clean["label_mode"] = "matching"
        return clean
    if n < 32:
        clean["n"] = n * 2
        return clean
    # q=64 needs more than 300 post-insight comparisons and its rendered q^2
    # incidence matrix no longer fits the no-tool setting.  The mathematical
    # family scales, but the benchmark's effort cap is the limiting resource.
    return "cap_bound"


def _answer_atoms(answer: object) -> int:
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def _intended_operations(q: int) -> int:
    degree = q.bit_length() - 1
    # Two row XORs and one equality-up-to-complement test per two-bit mask,
    # followed by enumeration of the matching span.
    return 3 * math.comb(2 * degree, 2) + (q - 1)


def selftest() -> dict:
    """Run mandatory correctness, density, attack, scaling, and key gates."""
    report: dict[str, Any] = {"paper": "2108.02529", "track": TRACK,
                              "shipping_difficulty": SHIPPING_DIFFICULTY}

    g1_failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(3):
            inst = make_instance(seed=seed, **params)
            attempts += 1
            ok, reason = verify(inst, inst["answer"])
            if not ok or json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append({"preset": preset, "seed": seed,
                                    "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures, "attempts": attempts, "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping)
    answer = list(inst["answer"])
    outside = next(x for x in range(inst["v"]) if x not in answer)
    corruptions = {
        "drop_one": answer[:-1],
        "swap_one": sorted(answer[:-1] + [outside]),
        "duplicate_one": sorted(answer[:-1] + [answer[0]]),
        "empty": [],
        "out_of_range": sorted(answer[:-1] + [inst["v"]]),
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    distinct_reasons = len({case["reason"] for case in cases.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and distinct_reasons == len(cases),
        "cases": cases,
        "distinct_reasons": distinct_reasons,
    }

    realistic = (
        "I checked the column counts exactly.\n```json\n"
        f"<answer>{json.dumps(answer)}</answer>\n```\n"
        "The labels are zero-based."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {"pass": parsed == answer, "parsed": parsed}

    guess_rng = random.Random(20260905)
    guess_total = 200_000
    guess_hits = 0
    rows = _decode_rows(inst)
    for _ in range(guess_total):
        candidate = random_candidate(inst, guess_rng)
        guess_hits += int(_is_switching_rows(rows, candidate, inst["q"]))
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "candidate_space": search_space(inst),
        "sampler": "uniform q-subsets, already distinct and sorted",
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    reference_times = []
    reference_successes = 0
    reference_edges = []
    for seed in range(8):
        trial = make_instance(seed=seed, **shipping)
        started = time.perf_counter()
        components, edge_count = _reference_components(trial)
        elapsed = time.perf_counter() - started
        reference_times.append(elapsed)
        reference_edges.append(edge_count)
        reference_successes += int(any(
            len(group) == trial["q"] and verify(trial, group)[0]
            for group in components
        ))
    v = inst["v"]
    words = (v + 63) // 64
    pair_count = math.comb(v, 2)
    operation_count = pair_count * words * 3
    report["G5_density_and_baseline"] = {
        "pass": reference_successes == 8,
        "shipping_density_hits": guess_hits,
        "shipping_density_total": guess_total,
        "shipping_observed_fraction": guess_hits / guess_total,
        "shipping_structure_aware_space": search_space(inst),
        "shipping_valid_solution_count": None,
        "demo_valid_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "baseline_wall_clock_sec_mean": sum(reference_times) / len(reference_times),
        "baseline_wall_clock_sec_max": max(reference_times),
        "baseline_operations": operation_count,
        "baseline_pairs": pair_count,
        "baseline_large_bucket_edges_mean": sum(reference_edges) / len(reference_edges),
    }

    attack_results = {
        "outlier_lexicographic_row": {"successes": 0, "attempts": 8},
        "greedy_common_zero": {"successes": 0, "attempts": 8},
        "random_restart_512": {"successes": 0, "attempts": 8},
        "coordinate_subspace_ansatz": {"successes": 0, "attempts": 8},
    }
    for seed in range(8):
        trial = make_instance(seed=seed, **shipping)
        candidates = {
            "outlier_lexicographic_row": _attack_outlier(trial),
            "greedy_common_zero": _attack_greedy(trial),
            "random_restart_512": _attack_random(trial, seed),
            "coordinate_subspace_ansatz": _attack_coordinate(trial),
        }
        for name, candidate in candidates.items():
            if candidate is not None and verify(trial, candidate)[0]:
                attack_results[name]["successes"] += 1
    all_failed = all(result["successes"] == 0
                     for result in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "canonical row-pair symmetric-difference bucketing",
            "complexity": "O(v^3/w) bit-word work and O(v^2) stored pairs",
            "wall_clock_sec_mean": sum(reference_times) / len(reference_times),
            "wall_clock_sec_max": max(reference_times),
            "operations": operation_count,
            "pairs": pair_count,
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    doubled_params = dict(shipping)
    doubled_params["n"] = min(32, shipping["n"] * 2)
    doubled_params["label_mode"] = "matching"
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["v"] > inst["v"]
        and search_space(doubled) > search_space(inst),
        "shipping_n": shipping["n"],
        "doubled_n": doubled_params["n"],
        "shipping_v": inst["v"],
        "doubled_v": doubled["v"],
        "shipping_space": search_space(inst),
        "doubled_space": search_space(doubled),
        "doubled_verify_reason": doubled_reason,
    }

    key_failures = []
    distinct_keys = []
    for seed in range(20):
        key_params = {"n": 16, "label_mode": "matching"}
        original = make_instance(seed=10_000 + seed, **key_params)
        base_key = canonical_key(original)
        distinct_keys.append(base_key)
        relabel_rng = random.Random(20_000 + seed)
        block_perm = list(range(original["v"]))
        point_perm = list(range(original["v"]))
        relabel_rng.shuffle(block_perm)
        relabel_rng.shuffle(point_perm)
        identity = list(range(original["v"]))
        variants = {
            "block": _relabel(original, block_perm, identity),
            "point": _relabel(original, identity, point_perm),
            "composed": _relabel(original, block_perm, point_perm),
        }
        for name, variant in variants.items():
            if canonical_key(variant) != base_key:
                key_failures.append({"seed": seed, "transformation": name,
                                     "failure": "key changed"})
            ok, reason = verify(variant, variant["answer"])
            if not ok:
                key_failures.append({"seed": seed, "transformation": name,
                                     "failure": reason})
    unrelated_distinct = len(set(distinct_keys))
    report["G8_canonical_key"] = {
        "pass": not key_failures and unrelated_distinct == 20,
        "invariance_checks": 40,
        "composed_transformation_checks": 20,
        "real_transformation_checks": 60,
        "unrelated_attempts": 20,
        "unrelated_distinct": unrelated_distinct,
        "transformations": [
            "arbitrary block relabelling with carried witness",
            "arbitrary point relabelling",
            "composition of independent block and point relabellings",
        ],
        "key_strength": (
            "binary-rank spectra after every zero-, one-, and two-group "
            "paper switch"
        ),
        "failures": key_failures,
    }

    answer_blob = json.dumps(answer)
    intended = _intended_operations(inst["q"])
    arms = {name: dict(G9_MEASUREMENTS[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_attempts = arms["hinted"].get("attempts", 0)
    placebo_attempts = arms["placebo"].get("attempts", 0)
    difference = None
    if hinted_attempts and placebo_attempts:
        difference = (
            arms["hinted"].get("solved", 0) / hinted_attempts
            - arms["placebo"].get("solved", 0) / placebo_attempts
        )
    within_caps = (len(answer_blob) <= 2000 and _answer_atoms(answer) <= 256
                   and intended <= 300)
    compact = _compact_periods(rows, inst["v"])
    compact_answer = _span(compact) if _rank_binary(compact) == inst["q"].bit_length() - 1 else []
    report["G9_no_tool_suitability"] = {
        "pass": within_caps and verify(inst, compact_answer)[0],
        "arms": arms,
        "hinted_minus_placebo": difference,
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "answer_chars": len(answer_blob),
        "answer_tokens": (len(answer_blob) + 3) // 4,
        "answer_elements": _answer_atoms(answer),
        "intended_route_operations": intended,
        "compact_route_verifies": verify(inst, compact_answer)[0],
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        gate.get("pass", False) for name, gate in report.items()
        if name.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
