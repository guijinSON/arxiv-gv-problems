"""Verified generator for edge-disjoint temporal branchings (arXiv:2002.12694).

The generated temporal digraphs are the star-snapshot instances used in the
proof of Theorem 3.  Four-source blocks stand for the four positive NAE clauses
obtained by omitting one source at a time.  A planted GF(2) linear polynomial
2-colours every block two-and-two, and therefore expands to two base-edge-
disjoint temporal-spanning branchings exactly as in the proof.

The certificate is known before the instance is assembled.  Verification never
reads the planted answer: it evaluates any polynomial in the declared bounded
language, expands both branchings, and checks every temporal snapshot and every
used base edge.  Only the Python standard library is used.
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
from collections import deque
from typing import Any


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "csp_sat",
    "certificate_form": "polynomial",
    "native_objects": [
        "finite temporal digraph given by instantaneous star snapshots",
        "fixed-width binary labels attached to the source vertices",
        "bounded linear-polynomial certificate language over GF(2)",
    ],
    "verification_operations": [
        "exact GF(2) polynomial evaluation",
        "temporal-edge membership and root-reachability count",
        "base-edge disjointness comparison",
        "exact two-colour count in each clause snapshot",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3.2, Theorem 3: the paper's NAE+3-SAT reduction to two "
        "edge-disjoint temporal-spanning branchings on star snapshots"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The XOR of the four binary source codes in every block annihilates "
        "the same GF(2) linear polynomial; without that invariant one must "
        "propagate the displayed exact-two constraints and fit the polynomial."
    ),
    "hardness_basis": (
        "Track B: exact-two block-overlap propagation followed by GF(2) Gaussian "
        "elimination is polynomial, O(B^2+n*w^2), but at shipping size used about "
        "219,000 counted primitive operations and about 0.005 seconds across "
        "eight measured seeds; the compact XOR-kernel route uses at most 297 exact "
        "operations after the invariant is recognized."
    ),
    "max_answer_tokens": 29,
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

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object {constant, support} for a GF(2) linear polynomial: "
        "constant is 0 or 1, and support is a strictly increasing list of "
        "exactly h distinct bit positions from 0 through w-1."
    ),
    "bounds": {
        "constant_values": 2,
        "coefficient_modulus": 2,
        "min_bit_width": 4,
        "max_bit_width": 63,
        "min_support_size": 1,
        "max_support_size": 62,
    },
}

DIFFICULTY = {
    "demo": {"n": 8, "bits": 4, "weight": 2, "repeat_factor": 1},
    "easy": {"n": 64, "bits": 60, "weight": 30, "repeat_factor": 1},
    "medium": {"n": 128, "bits": 60, "weight": 30, "repeat_factor": 1},
    "hard": {"n": 256, "bits": 60, "weight": 30, "repeat_factor": 1},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The XORs of the four binary source codes are sparse vectors in the "
    "kernel of one common GF(2) linear polynomial."
)
PLACEBO_HINT = (
    "Careful bookkeeping of source labels and snapshot numbers helps avoid "
    "mixing base edges with their temporal appearances."
)

# Filled from the three script-owned oracle transcripts after hardening.
# The arms are diagnostic; only the answer-size and operation caps gate G9.
G9_MEASUREMENTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES = r"""
Definition.  Section 2 defines a temporal digraph (G,gamma,lambda), temporal
walks (including waiting only across consecutive active appearances), temporal-
spanning branchings (exactly one root-to-appearance temporal walk), and the
difference between temporal-edge disjointness and base-edge disjointness.

Hard/easy boundary.  Section 3.1 reduces temporal-edge-disjoint temporal-
spanning branchings to Edmonds' static branching problem and is polynomial.
Theorem 4 also gives a polynomial algorithm for base-edge-disjoint temporal-
spanning branchings when every vertex's active times form one interval; in
particular lifetime two is easy.  The generator instead uses the nonconsecutive
odd snapshots of Section 3.2.  Theorem 3 proves the base-edge-disjoint problem
NP-complete for every fixed k>=2 even on a DAG whose underlying graph is a star,
with constant-size snapshots and an ETH lower bound in the lifetime.

Construction.  Theorem 3 maps positive NAE-3-SAT to star snapshots.  A variable
snapshot has sources v and ~v pointing to the centre T.  A clause snapshot has
three positive sources pointing to T.  Both branchings root at every active
source.  Splitting v and ~v between the branchings fixes a Boolean colour; a
clause can span T in both branchings exactly when its three colours are not all
equal.  Each generated four-source block expands into all four three-source
clauses, so it is feasible exactly when the four colours split two-and-two.

Inverse generation.  A fixed-weight GF(2) linear polynomial is sampled first.
Each new four-source block is assembled so that its code XOR lies in that
polynomial's kernel and its four planted colours split two-and-two.  Blocks form
a three-overlap tree, so the planted certificate expands to the theorem's two
branchings without solving the displayed instance.

Step-0 certificate algorithm.  A specialist can build the graph of blocks that
share three sources, try the six balanced colourings of one block, propagate
exact-two constraints, and fit a GF(2) affine form by Gaussian elimination.
That polynomial reference algorithm is O(B^2+n*w^2) and is measured over eight
shipping seeds.  The compact route instead XORs one basis-sized prefix of block
codes: singleton XORs mark zero coefficients and two-bit XORs connect the one
coefficients.  At w=60 this takes at most 297 exact operations.
Attacks.  Raw vertex labels, source-code rows, block rows inside each structural
part, and source order within blocks are shuffled.  The panel tests low-bit and
frequency outliers, a limited greedy swap search, an eight-block partial XOR
shortcut that is plausible by hand, and random restarts.  The successful full
constraint-propagation/Gaussian algorithm is reported separately, as Track B
requires.  A uniformly random fixed-weight support removes a low-bit signature;
conditioning every block on the same exact-two rule removes planted-row
outliers; the 60-bit space defeats frequency and random guesses; and exposing
only eight of the 59 independent sparse kernel directions leaves the partial
XOR shortcut underdetermined.
""".strip()


def _validate_params(n: int, bits: int, weight: int, repeat_factor: int) -> None:
    for name, value in (
        ("n", n),
        ("bits", bits),
        ("weight", weight),
        ("repeat_factor", repeat_factor),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    if bits < 4 or bits > 63:
        raise ValueError("bits must lie in the inclusive range 4..63")
    if weight < 1 or weight >= bits:
        raise ValueError("weight must lie in the inclusive range 1..bits-1")
    if n < bits + 4:
        raise ValueError("n must be at least bits+4")
    if n >= (1 << bits):
        raise ValueError("n must be smaller than the code space 2^bits")
    if repeat_factor < 1 or repeat_factor > 8:
        raise ValueError("repeat_factor must lie in the inclusive range 1..8")


def _mask_from_support(support: list[int]) -> int:
    mask = 0
    for bit in support:
        mask |= 1 << bit
    return mask


def _colour(code: int, mask: int, constant: int) -> int:
    return ((code & mask).bit_count() & 1) ^ constant


def _gf2_rank(rows: list[int], columns: int) -> int:
    work = list(rows)
    rank = 0
    for col in range(columns):
        pivot = next((r for r in range(rank, len(work)) if (work[r] >> col) & 1), None)
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        for r in range(len(work)):
            if r != rank and ((work[r] >> col) & 1):
                work[r] ^= work[rank]
        rank += 1
        if rank == len(work):
            break
    return rank


def _kernel_basis(mask: int, bits: int) -> list[int]:
    """A sparse basis for the hyperplane orthogonal to nonzero ``mask``."""
    support = [i for i in range(bits) if (mask >> i) & 1]
    zeroes = [i for i in range(bits) if not ((mask >> i) & 1)]
    anchor = support[0]
    basis = [1 << z for z in zeroes]
    basis.extend((1 << anchor) | (1 << s) for s in support[1:])
    if len(basis) != bits - 1 or _gf2_rank(basis, bits) != bits - 1:
        raise AssertionError("internal kernel basis is not independent")
    return basis


def _try_root_block(
    rng: random.Random,
    d: int,
    bits: int,
    mask: int,
    constant: int,
) -> list[int] | None:
    limit = 1 << bits
    three = rng.sample(range(limit), 3)
    fourth = d ^ three[0] ^ three[1] ^ three[2]
    block = three + [fourth]
    if len(set(block)) != 4:
        return None
    if sum(_colour(code, mask, constant) for code in block) != 2:
        return None
    return block


def _build_codes_and_blocks(
    n: int,
    bits: int,
    mask: int,
    constant: int,
    basis: list[int],
    rng: random.Random,
) -> tuple[list[int], list[list[int]]]:
    """Grow a balanced three-overlap block tree with prescribed block XORs."""
    schedule = list(basis)
    while len(schedule) < n - 3:
        schedule.append(rng.choice(basis))

    root = None
    for _ in range(20_000):
        root = _try_root_block(rng, schedule[0], bits, mask, constant)
        if root is not None:
            break
    if root is None:
        raise RuntimeError("could not construct a balanced root block")

    codes = list(root)
    used = set(codes)
    blocks = [list(root)]
    for d in schedule[1:]:
        made = None
        for _ in range(20_000):
            parent = rng.choice(blocks)
            omitted = rng.randrange(4)
            old_three = [parent[i] for i in range(4) if i != omitted]
            new_code = d ^ old_three[0] ^ old_three[1] ^ old_three[2]
            if new_code in used:
                continue
            candidate = old_three + [new_code]
            if sum(_colour(code, mask, constant) for code in candidate) != 2:
                continue
            made = candidate
            break
        if made is None:
            raise RuntimeError("could not extend the balanced block tree")
        blocks.append(made)
        new_value = made[-1]
        codes.append(new_value)
        used.add(new_value)

    if len(codes) != n or len(blocks) != n - 3:
        raise AssertionError("internal block-tree size mismatch")
    return codes, blocks


def make_instance(
    n: int,
    seed: int = 0,
    bits: int = 36,
    weight: int = 18,
    repeat_factor: int = 1,
    **params: Any,
) -> dict:
    """Inverse-generate certified temporal branchings without solving the instance."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, bits, weight, repeat_factor)
    rng = random.Random(seed)

    # Resampling only enforces representation rank and collision hygiene.  The
    # certificate is sampled first on every attempt; no candidate is searched
    # for against an already-built instance.
    for _attempt in range(200):
        support = sorted(rng.sample(range(bits), weight))
        constant = rng.randrange(2)
        mask = _mask_from_support(support)
        basis = _kernel_basis(mask, bits)
        rng.shuffle(basis)
        codes, semantic_blocks = _build_codes_and_blocks(
            n, bits, mask, constant, basis, rng
        )
        augmented = [code | (1 << bits) for code in codes]
        if _gf2_rank(augmented, bits + 1) == bits + 1:
            break
    else:
        raise RuntimeError("could not obtain full-rank public source codes")

    # Raw source identifiers are presentation only.  Codes remain attached to
    # their vertices and are the variables of the certificate polynomial.
    identifiers = list(range(n))
    rng.shuffle(identifiers)
    code_to_id = dict(zip(codes, identifiers))
    variables = [{"id": code_to_id[c], "code": c} for c in codes]
    rng.shuffle(variables)

    base_blocks = [[code_to_id[c] for c in block] for block in semantic_blocks]
    # The first w-1 rows contain one copy of every kernel-basis direction but
    # are internally shuffled; later rows are same-distribution repeats.
    prefix_len = bits - 1
    prefix = base_blocks[:prefix_len]
    tail = base_blocks[prefix_len:]
    rng.shuffle(prefix)
    rng.shuffle(tail)
    for block in prefix + tail:
        rng.shuffle(block)
    ordered_base = prefix + tail

    blocks: list[list[int]] = [list(block) for block in ordered_base]

    # Extra crowding layers tighten the instance with fresh constraints rather
    # than copying rows that add no information.  Each new row is drawn from
    # the same exact-two condition as every base row, and the held certificate
    # is still known before the row is assembled.
    if repeat_factor > 1:
        colour_classes = {0: [], 1: []}
        for code in codes:
            colour_classes[_colour(code, mask, constant)].append(code_to_id[code])
        seen_blocks = {tuple(sorted(block)) for block in blocks}
        wanted = (repeat_factor - 1) * max(1, n // 8)
        attempts = 0
        while wanted:
            attempts += 1
            if attempts > 20_000 + 200 * len(blocks):
                raise RuntimeError("could not draw enough distinct crowding blocks")
            block = (
                rng.sample(colour_classes[0], 2)
                + rng.sample(colour_classes[1], 2)
            )
            key = tuple(sorted(block))
            if key in seen_blocks:
                continue
            seen_blocks.add(key)
            rng.shuffle(block)
            blocks.append(block)
            wanted -= 1

    return {
        "n": n,
        "bits": bits,
        "weight": weight,
        "repeat_factor": repeat_factor,
        "centre": "T",
        "variables": variables,
        "blocks": blocks,
        "answer": {"constant": constant, "support": support},
    }


def _code_maps(inst: dict) -> tuple[dict[int, int], dict[int, int]]:
    id_to_code: dict[int, int] = {}
    code_to_id: dict[int, int] = {}
    for row in inst["variables"]:
        vertex = int(row["id"])
        code = int(row["code"])
        id_to_code[vertex] = code
        code_to_id[code] = vertex
    return id_to_code, code_to_id


def _answer_syntax(inst: dict, answer: Any) -> tuple[bool, str]:
    bits = int(inst["bits"])
    weight = int(inst["weight"])
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object with constant and support"
    if not answer:
        return False, "answer certificate is empty"
    if set(answer) != {"constant", "support"}:
        return False, "answer must contain exactly the keys constant and support"
    constant = answer["constant"]
    support = answer["support"]
    if isinstance(constant, bool) or not isinstance(constant, int) or constant not in (0, 1):
        return False, "constant must be the integer 0 or 1"
    if not isinstance(support, list):
        return False, "support must be a JSON list"
    if len(support) != weight:
        return False, f"wrong support size: expected exactly {weight} bit positions"
    if any(isinstance(bit, bool) or not isinstance(bit, int) for bit in support):
        return False, "every support position must be an integer"
    if len(set(support)) != len(support):
        return False, "support contains a duplicate bit position"
    if any(bit < 0 or bit >= bits for bit in support):
        return False, f"support position outside the inclusive range 0..{bits - 1}"
    if support != sorted(support):
        return False, "support positions must be in strictly increasing order"
    return True, "ok"


def _fast_valid(inst: dict, answer: Any) -> bool:
    good, _ = _answer_syntax(inst, answer)
    if not good:
        return False
    id_to_code, _ = _code_maps(inst)
    if len(id_to_code) != int(inst["n"]):
        return False
    mask = _mask_from_support(answer["support"])
    constant = int(answer["constant"])
    for raw_block in inst["blocks"]:
        try:
            colours = [_colour(id_to_code[int(v)], mask, constant) for v in raw_block]
        except (KeyError, TypeError, ValueError):
            return False
        if len(raw_block) != 4 or len(set(map(int, raw_block))) != 4 or sum(colours) != 2:
            return False
    return True


def verify(inst: dict, answer: Any) -> tuple[bool, str]:
    """Expand and check any valid polynomial branching certificate exactly."""
    good, reason = _answer_syntax(inst, answer)
    if not good:
        return False, reason

    n = int(inst["n"])
    bits = int(inst["bits"])
    variables = inst.get("variables")
    if not isinstance(variables, list) or len(variables) != n:
        return False, "instance has a malformed variable table"
    id_to_code, code_to_id = _code_maps(inst)
    if set(id_to_code) != set(range(n)) or len(code_to_id) != n:
        return False, "instance variable identifiers or codes are not distinct and complete"
    if any(code < 0 or code >= (1 << bits) for code in id_to_code.values()):
        return False, "instance contains a source code outside the declared bit width"

    mask = _mask_from_support(answer["support"])
    constant = int(answer["constant"])
    colours = {v: _colour(code, mask, constant) for v, code in id_to_code.items()}

    # A base edge is represented by (kind, variable id): positive v->T or
    # negative ~v->T.  Every temporal appearance of one base edge must belong
    # to at most one branching.
    used_base_edges = [set(), set()]
    temporal_edges = [[], []]

    # Variable snapshot i: sources v_i and ~v_i are roots in both branchings;
    # each branching selects its owned source edge to reach the centre T.
    for vertex in range(n):
        owner_positive = 0 if colours[vertex] == 1 else 1
        owner_negative = 1 - owner_positive
        selections = [None, None]
        selections[owner_positive] = ("positive", vertex)
        selections[owner_negative] = ("negative", vertex)
        for branch in (0, 1):
            edge = selections[branch]
            if edge is None:
                return False, f"variable snapshot {vertex} leaves branch {branch + 1} without T"
            used_base_edges[branch].add(edge)
            temporal_edges[branch].append(("variable", vertex, edge))

    # Each displayed block expands to four clause snapshots.  Omitting each
    # source once yields all four triples.  Exactly one selected root edge in a
    # branch means exactly one root-to-T temporal walk in that snapshot.
    blocks = inst.get("blocks")
    if not isinstance(blocks, list):
        return False, "instance has a malformed block list"
    for block_index, raw_block in enumerate(blocks):
        if not isinstance(raw_block, list) or len(raw_block) != 4:
            return False, f"block {block_index} does not contain exactly four sources"
        if any(isinstance(v, bool) or not isinstance(v, int) for v in raw_block):
            return False, f"block {block_index} contains a non-integer source id"
        if len(set(raw_block)) != 4 or any(v not in id_to_code for v in raw_block):
            return False, f"block {block_index} has repeated or unknown sources"
        block_colours = [colours[v] for v in raw_block]
        if sum(block_colours) != 2:
            return False, (
                f"temporal-spanning failure in block {block_index}: its four "
                "sources do not split two-and-two between the branchings"
            )
        for omitted in range(4):
            active = [v for j, v in enumerate(raw_block) if j != omitted]
            for branch in (0, 1):
                wanted_colour = 1 if branch == 0 else 0
                eligible = [v for v in active if colours[v] == wanted_colour]
                if not eligible:
                    return False, (
                        f"clause snapshot block {block_index}/omit {omitted} "
                        f"has no root edge for branch {branch + 1}"
                    )
                # This tie-break makes the compressed certificate expand to one
                # concrete branching, while accepting every valid polynomial.
                chosen = min(eligible, key=lambda v: (id_to_code[v], v))
                edge = ("positive", chosen)
                used_base_edges[branch].add(edge)
                temporal_edges[branch].append(("clause", 4 * block_index + omitted, edge))

    overlap = used_base_edges[0] & used_base_edges[1]
    if overlap:
        return False, "the expanded branchings reuse a base edge"

    # With empty even snapshots every active source is a root and waiting is
    # impossible.  The selected edge is therefore the unique root-to-T walk;
    # checking one edge per nonempty snapshot is an exact reachability count.
    expected_snapshots = n + 4 * len(blocks)
    for branch in (0, 1):
        if len(temporal_edges[branch]) != expected_snapshots:
            return False, f"branch {branch + 1} does not span every nonempty snapshot"
    return True, "ok"


def render(inst: dict) -> str:
    """Render the complete temporal-graph problem and exact output contract."""
    n = int(inst["n"])
    bits = int(inst["bits"])
    weight = int(inst["weight"])
    blocks = inst["blocks"]
    nonempty = n + 4 * len(blocks)
    lifetime = 2 * nonempty - 1
    width = (bits + 3) // 4
    lines = [
        "TWO BASE-EDGE-DISJOINT TEMPORAL-SPANNING BRANCHINGS",
        "",
        "A temporal vertex is a pair (vertex,time) at which that vertex is active.",
        "A temporal edge (u,t)->(v,t') may be used only when t<=t'. A temporal",
        "walk follows temporal edges forward in time and may wait from (v,t) to",
        "(v,t+1) only when v is active at both consecutive times.",
        "",
        "A branching rooted at a set R of temporal vertices must have exactly one",
        "temporal walk from R to every active temporal vertex. Two branchings are",
        "base-edge-disjoint when no directed edge u->v of the base digraph has",
        "any temporal appearance in both branchings.",
        "",
        f"This instance has centre T and {n} positive sources v0..v{n - 1}, each",
        f"with a negative mate ~v0..~v{n - 1}. Its lifetime is {lifetime}.",
        "Only odd times are nonempty; every even time is empty, so no waiting",
        "between nonempty snapshots is possible. All edges below are instantaneous",
        "source->T edges. Every active source, but never T, is in both root sets.",
        "",
        "The variable snapshots come first, in source-id order. Snapshot i has",
        "active vertices v_i, ~v_i, T and edges v_i->T, ~v_i->T.",
        "",
        f"Each positive source has a distinct {bits}-bit public code. Bit 0 is the",
        "least significant bit. Codes are hexadecimal; leading zeroes are included:",
    ]
    variable_chunks = [
        f"v{row['id']}=0x{int(row['code']):0{width}x}" for row in inst["variables"]
    ]
    for i in range(0, len(variable_chunks), 6):
        lines.append("  " + "  ".join(variable_chunks[i:i + 6]))
    lines.extend([
        "",
        "After the variable snapshots come the four clause snapshots for each",
        "displayed block, in displayed block order. If a block row is [a,b,c,d],",
        "its four snapshots have respectively the three positive sources obtained",
        "by omitting a, then b, then c, then d; each has those three edges to T.",
        "The order of sources within a row is significant only for this omission",
        "order. Repeated block rows are distinct later temporal demands.",
        "",
        f"Blocks ({len(blocks)} rows):",
    ])
    for i, block in enumerate(blocks):
        lines.append(f"  {i}: [" + ",".join(f"v{v}" for v in block) + "]")
    lines.extend([
        "",
        "Your answer is a GF(2) linear polynomial L on the public codes.",
        "The integer constant is 0 or 1. The support is a strictly increasing",
        f"list of exactly {weight} distinct bit positions in the inclusive range",
        f"0..{bits - 1}. For a source with code x, define",
        "",
        "  L(x) = constant XOR (the listed bits of x),",
        "",
        "where XOR means addition modulo 2.",
        "",
        "The certificate expands to two concrete branchings as follows.",
        "Branch 1 owns v_i->T when L(code(v_i))=1 and owns ~v_i->T otherwise.",
        "Branch 2 owns the other one of those two base edges. In each variable",
        "snapshot each branch uses its owned edge. In each clause snapshot each",
        "branch uses the owned active positive-source edge having the smallest",
        "public code (source id breaks a tie, although codes here are distinct).",
        "",
        "The polynomial is valid exactly when this expansion gives two temporal-",
        "spanning branchings and their sets of used base edges are disjoint. Any",
        "polynomial in the stated bounded language with that property is accepted.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    example_support = list(range(weight))
    example = json.dumps({"constant": 0, "support": example_support}, separators=(",", ":"))
    lines.extend([
        "",
        "Give your final answer inside <answer></answer> tags as one JSON object",
        "with keys constant and support, exactly in the format just defined.",
        f"Example: <answer>{example}</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text: Any) -> object | None:
    """Extract the JSON certificate from prose, whitespace, or a markdown fence."""
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    if not match:
        return None
    body = match.group(1).strip()
    body = re.sub(r"^```(?:json|text|python)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    return value


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the fixed-weight GF(2) polynomial language."""
    bits = int(inst["bits"])
    weight = int(inst["weight"])
    return {
        "constant": rng.randrange(2),
        "support": sorted(rng.sample(range(bits), weight)),
    }


def search_space(inst: dict) -> int | None:
    return 2 * math.comb(int(inst["bits"]), int(inst["weight"]))


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the exact bounded language only at genuinely tiny presets."""
    space = search_space(inst)
    if space is None or space > 200_000:
        return None
    total = 0
    bits = int(inst["bits"])
    weight = int(inst["weight"])
    for support_tuple in itertools.combinations(range(bits), weight):
        support = list(support_tuple)
        for constant in (0, 1):
            total += int(_fast_valid(inst, {"constant": constant, "support": support}))
    return total


def _unique_blocks(inst: dict) -> list[list[int]]:
    seen: set[tuple[int, ...]] = set()
    result = []
    for block in inst["blocks"]:
        key = tuple(sorted(map(int, block)))
        if key not in seen:
            seen.add(key)
            result.append(list(key))
    return result


def _solve_gf2_affine(
    codes: list[int],
    colours: list[int],
    bits: int,
) -> tuple[dict | None, int]:
    """Solve L(code_i)=colour_i and count elementary GF(2) operations."""
    rows = [[int(code) | (1 << bits), int(colour)] for code, colour in zip(codes, colours)]
    variables = bits + 1
    rank = 0
    pivots: list[int] = []
    operations = 0
    for col in range(variables):
        pivot = None
        for r in range(rank, len(rows)):
            operations += 1
            if (rows[r][0] >> col) & 1:
                pivot = r
                break
        if pivot is None:
            continue
        if pivot != rank:
            rows[rank], rows[pivot] = rows[pivot], rows[rank]
            operations += 1
        for r in range(len(rows)):
            if r == rank:
                continue
            operations += 1
            if (rows[r][0] >> col) & 1:
                rows[r][0] ^= rows[rank][0]
                rows[r][1] ^= rows[rank][1]
                operations += variables + 1
        pivots.append(col)
        rank += 1
        if rank == len(rows):
            break
    for coeffs, rhs in rows:
        operations += 1
        if coeffs == 0 and rhs:
            return None, operations

    solution = 0
    for r, col in reversed(list(enumerate(pivots))):
        rhs = rows[r][1]
        remaining = rows[r][0] & ~(1 << col)
        operations += 1 + remaining.bit_count()
        if (remaining & solution).bit_count() & 1:
            rhs ^= 1
        if rhs:
            solution |= 1 << col
    support = [bit for bit in range(bits) if (solution >> bit) & 1]
    constant = (solution >> bits) & 1
    return {"constant": constant, "support": support}, operations


def _reference_algorithm(inst: dict) -> tuple[dict | None, dict[str, int]]:
    """Domain reference: exact-two propagation, then GF(2) elimination."""
    blocks = _unique_blocks(inst)
    n = int(inst["n"])
    bits = int(inst["bits"])
    id_to_code, _ = _code_maps(inst)
    adjacency = [[] for _ in blocks]
    overlap_comparisons = 0
    for i in range(len(blocks)):
        for j in range(i + 1, len(blocks)):
            shared = 0
            # Count the literal comparisons a simple implementation performs.
            for a in blocks[i]:
                for b in blocks[j]:
                    overlap_comparisons += 1
                    shared += int(a == b)
            if shared == 3:
                adjacency[i].append(j)
                adjacency[j].append(i)

    propagation_ops = 0
    elimination_ops = 0
    candidates_tried = 0
    if not blocks:
        return None, {
            "overlap_comparisons": overlap_comparisons,
            "propagation_operations": 0,
            "elimination_operations": 0,
            "candidates_tried": 0,
            "operations": overlap_comparisons,
        }

    root = blocks[0]
    for ones in itertools.combinations(range(4), 2):
        candidates_tried += 1
        colours: dict[int, int] = {
            root[i]: int(i in ones) for i in range(4)
        }
        queue = deque([0])
        reached = {0}
        consistent = True
        while queue and consistent:
            current = queue.popleft()
            propagation_ops += 1
            for neighbour in adjacency[current]:
                propagation_ops += 1
                if neighbour in reached:
                    continue
                block = blocks[neighbour]
                unknown = [v for v in block if v not in colours]
                known_sum = sum(colours[v] for v in block if v in colours)
                propagation_ops += len(block) + 1
                if len(unknown) == 1:
                    forced = 2 - known_sum
                    if forced not in (0, 1):
                        consistent = False
                        break
                    colours[unknown[0]] = forced
                    reached.add(neighbour)
                    queue.append(neighbour)
                elif not unknown:
                    if known_sum != 2:
                        consistent = False
                        break
                    reached.add(neighbour)
                    queue.append(neighbour)
        if not consistent or len(colours) != n:
            continue
        for block in blocks:
            propagation_ops += 4
            if sum(colours[v] for v in block) != 2:
                consistent = False
                break
        if not consistent:
            continue

        ordered_ids = sorted(id_to_code)
        candidate, cost = _solve_gf2_affine(
            [id_to_code[v] for v in ordered_ids],
            [colours[v] for v in ordered_ids],
            bits,
        )
        elimination_ops += cost
        if candidate is not None and len(candidate["support"]) == int(inst["weight"]):
            if verify(inst, candidate)[0]:
                counts = {
                    "overlap_comparisons": overlap_comparisons,
                    "propagation_operations": propagation_ops,
                    "elimination_operations": elimination_ops,
                    "candidates_tried": candidates_tried,
                }
                counts["operations"] = sum(
                    counts[k] for k in (
                        "overlap_comparisons",
                        "propagation_operations",
                        "elimination_operations",
                    )
                )
                return candidate, counts

    counts = {
        "overlap_comparisons": overlap_comparisons,
        "propagation_operations": propagation_ops,
        "elimination_operations": elimination_ops,
        "candidates_tried": candidates_tried,
    }
    counts["operations"] = sum(
        counts[k] for k in (
            "overlap_comparisons",
            "propagation_operations",
            "elimination_operations",
        )
    )
    return None, counts


def _block_code_xor(inst: dict, block: list[int]) -> int:
    id_to_code, _ = _code_maps(inst)
    value = 0
    for vertex in block:
        value ^= id_to_code[int(vertex)]
    return value


def _score_support(inst: dict, support: list[int]) -> int:
    candidate = {"constant": 0, "support": sorted(support)}
    good, _ = _answer_syntax(inst, candidate)
    if not good:
        return -1
    id_to_code, _ = _code_maps(inst)
    mask = _mask_from_support(candidate["support"])
    score = 0
    for block in _unique_blocks(inst):
        score += int(sum(_colour(id_to_code[v], mask, 0) for v in block) == 2)
    return score


def _attack_candidates(inst: dict, seed: int) -> dict[str, dict]:
    bits = int(inst["bits"])
    weight = int(inst["weight"])
    id_to_code, _ = _code_maps(inst)

    low = list(range(weight))
    one_counts = [sum((code >> bit) & 1 for code in id_to_code.values()) for bit in range(bits)]
    frequency = sorted(
        range(bits),
        key=lambda bit: (-abs(2 * one_counts[bit] - len(id_to_code)), bit),
    )[:weight]

    # A bounded, genuinely by-hand partial use of the intended XOR invariant:
    # inspect only eight rows, mark singleton directions as zero, and favor
    # endpoints of observed two-bit relations.  It deliberately does not scan
    # the full basis-sized prefix.
    forbidden: set[int] = set()
    pair_degree = [0] * bits
    for block in _unique_blocks(inst)[:8]:
        d = _block_code_xor(inst, block)
        support_d = [bit for bit in range(bits) if (d >> bit) & 1]
        if len(support_d) == 1:
            forbidden.add(support_d[0])
        elif len(support_d) == 2:
            pair_degree[support_d[0]] += 1
            pair_degree[support_d[1]] += 1
    partial = sorted(
        range(bits), key=lambda bit: (bit in forbidden, -pair_degree[bit], bit)
    )[:weight]

    # Limited local improvement from the conspicuous low-bit ansatz.  Eight
    # swaps is small enough to attempt manually; ties are deterministic.
    greedy = set(low)
    current_score = _score_support(inst, sorted(greedy))
    for _ in range(8):
        best = None
        best_score = current_score
        for remove in sorted(greedy):
            for add in range(bits):
                if add in greedy:
                    continue
                trial = sorted((greedy - {remove}) | {add})
                score = _score_support(inst, trial)
                if score > best_score:
                    best_score = score
                    best = (remove, add)
        if best is None:
            break
        greedy.remove(best[0])
        greedy.add(best[1])
        current_score = best_score

    return {
        "linear_low_bits_ansatz": {"constant": 0, "support": sorted(low)},
        "outlier_bit_frequency": {"constant": 0, "support": sorted(frequency)},
        "prefix_xor_constraints_8": {"constant": 0, "support": sorted(partial)},
        "greedy_balance_swap_8": {"constant": 0, "support": sorted(greedy)},
    }


def canonical_key(inst: dict) -> str:
    """Canonical under raw source renaming and every input row reordering."""
    id_to_code, _ = _code_maps(inst)
    canonical_blocks = []
    for block in inst["blocks"]:
        canonical_blocks.append(sorted(id_to_code[int(v)] for v in block))
    normal = {
        "bits": int(inst["bits"]),
        "weight": int(inst["weight"]),
        "codes": sorted(id_to_code.values()),
        "blocks_as_code_multiset": sorted(canonical_blocks),
    }
    blob = json.dumps(normal, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def _renumber_and_reorder(inst: dict, rng: random.Random) -> dict:
    """Apply a genuine base-vertex relabelling and independent input reorderings."""
    n = int(inst["n"])
    labels = list(range(n))
    shuffled = list(labels)
    rng.shuffle(shuffled)
    mapping = dict(zip(labels, shuffled))
    transformed = {
        "n": n,
        "bits": int(inst["bits"]),
        "weight": int(inst["weight"]),
        "repeat_factor": int(inst["repeat_factor"]),
        "centre": inst["centre"],
        "variables": [
            {"id": mapping[int(row["id"])], "code": int(row["code"])}
            for row in inst["variables"]
        ],
        "blocks": [
            [mapping[int(v)] for v in block]
            for block in inst["blocks"]
        ],
        "answer": {
            "constant": int(inst["answer"]["constant"]),
            "support": list(inst["answer"]["support"]),
        },
    }
    rng.shuffle(transformed["variables"])
    rng.shuffle(transformed["blocks"])
    for block in transformed["blocks"]:
        rng.shuffle(block)
    return transformed


def escalate(params: dict) -> dict | str | None:
    """Tighten with fresh rows, then double the haystack; answer size is fixed."""
    clean = {k: v for k, v in params.items() if k != "_preset"}
    repeat_factor = int(clean.get("repeat_factor", 1))
    if repeat_factor < 4:
        clean["repeat_factor"] = repeat_factor + 1
        return clean
    doubled = 2 * int(clean.get("n", DIFFICULTY[SHIPPING_DIFFICULTY]["n"]))
    if doubled >= (1 << int(clean.get("bits", 36))):
        return None
    clean["n"] = doubled
    clean["repeat_factor"] = 1
    return clean


def _atom_count(value: Any) -> int:
    if isinstance(value, dict):
        return sum(_atom_count(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atom_count(v) for v in value)
    return 1


def _intended_route_operations(inst: dict) -> int:
    # For w-1 basis rows: three word-XORs, one sparse-direction inspection,
    # and one mark/union.  Two final operations choose either constant and emit.
    return 5 * (int(inst["bits"]) - 1) + 2


def selftest() -> dict:
    """Run every local gate and return a fully JSON-native measured report."""
    report: dict[str, Any] = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            g1_attempts += 1
            ok, why = verify(inst, inst["answer"])
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: answer is not JSON-native")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=314159, **ship_params)
    planted = {
        "constant": int(ship["answer"]["constant"]),
        "support": list(ship["answer"]["support"]),
    }
    swapped = list(planted["support"])
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = list(planted["support"])
    duplicated[1] = duplicated[0]
    outside = list(planted["support"])
    outside[-1] = int(ship["bits"])
    corruptions = {
        "drop_one": {"constant": planted["constant"], "support": planted["support"][:-1]},
        "swap_two": {"constant": planted["constant"], "support": swapped},
        "duplicate_one": {"constant": planted["constant"], "support": duplicated},
        "empty": {},
        "out_of_range": {"constant": planted["constant"], "support": outside},
    }
    g2_cases = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, why = verify(ship, candidate)
        g2_cases[name] = {"rejected": not ok, "reason": why}
        reasons.append(why)
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in g2_cases.values()) and len(set(reasons)) == 5,
        "distinct_reasons": len(set(reasons)),
        "cases": g2_cases,
    }

    answer_text = json.dumps(planted, separators=(",", ":"))
    model_style = (
        "The four-source checks are balanced.\n```json\n"
        f"<answer>{answer_text}</answer>\n```\n"
        "This polynomial expands to the two branchings."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("garbage") is None,
        "parsed": parsed,
    }

    samples = 250_000
    guess_rng = random.Random(8_675_309)
    hits = 0
    for _ in range(samples):
        candidate = random_candidate(ship, guess_rng)
        if _fast_valid(ship, candidate):
            hits += 1
            if not verify(ship, candidate)[0]:
                raise AssertionError("fast density checker disagrees with verify")
    fraction = hits / samples
    report["G4_guess_resistance"] = {
        "pass": fraction < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": fraction,
        "candidate_space": search_space(ship),
        "sampler": "uniform over fixed-weight GF(2) linear polynomials",
    }

    demo = make_instance(seed=17, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    reference_times = []
    reference_operations = []
    reference_successes = 0
    for seed in range(8):
        inst = make_instance(seed=9_000 + seed, **ship_params)
        started = time.perf_counter()
        candidate, counts = _reference_algorithm(inst)
        elapsed = time.perf_counter() - started
        reference_times.append(elapsed)
        reference_operations.append(counts["operations"])
        reference_successes += int(candidate is not None and verify(inst, candidate)[0])
    report["G5_density_and_baseline"] = {
        "pass": demo_count is not None and fraction < 1e-6 and reference_successes == 8,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "strongest_attack_wall_clock_sec_max": max(reference_times),
        "strongest_attack_operations_max": max(reference_operations),
        "shipping_density": {
            "hits": hits,
            "total": samples,
            "observed_fraction": fraction,
            "n": int(ship["n"]),
        },
        "demo_exact": {
            "valid_certificates": demo_count,
            "candidate_space": search_space(demo),
            "n": int(demo["n"]),
        },
        "strongest_attack": {
            "name": "exact-two overlap propagation plus GF(2) Gaussian elimination",
            "solves": f"{reference_successes}/8",
            "wall_clock_sec_mean": sum(reference_times) / len(reference_times),
            "wall_clock_sec_max": max(reference_times),
            "operations_mean": sum(reference_operations) / len(reference_operations),
            "operations_max": max(reference_operations),
        },
    }

    attack_names = [
        "linear_low_bits_ansatz",
        "outlier_bit_frequency",
        "prefix_xor_constraints_8",
        "greedy_balance_swap_8",
        "random_restart_256",
    ]
    attacks = {name: {"successes": 0, "attempts": 8} for name in attack_names}
    panel_ref_successes = 0
    panel_ref_times = []
    panel_ref_operations = []
    for seed in range(8):
        inst = make_instance(seed=12_000 + seed, **ship_params)
        for name, candidate in _attack_candidates(inst, seed).items():
            attacks[name]["successes"] += int(verify(inst, candidate)[0])
        restart_rng = random.Random(700_000 + seed)
        restart_hit = False
        for _ in range(256):
            if _fast_valid(inst, random_candidate(inst, restart_rng)):
                restart_hit = True
                break
        attacks["random_restart_256"]["successes"] += int(restart_hit)

        started = time.perf_counter()
        candidate, counts = _reference_algorithm(inst)
        elapsed = time.perf_counter() - started
        panel_ref_times.append(elapsed)
        panel_ref_operations.append(counts["operations"])
        panel_ref_successes += int(candidate is not None and verify(inst, candidate)[0])
    all_failed = all(
        result["successes"] == 0 and result["attempts"] >= 8
        for result in attacks.values()
    )
    report["G6_adversary_panel"] = {
        "pass": all_failed and panel_ref_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "exact-two block-overlap propagation plus GF(2) Gaussian elimination",
            "complexity": "O(B^2 + n*w^2) exact",
            "wall_clock_sec_mean": sum(panel_ref_times) / len(panel_ref_times),
            "wall_clock_sec_max": max(panel_ref_times),
            "operations_mean": sum(panel_ref_operations) / len(panel_ref_operations),
            "operations_max": max(panel_ref_operations),
            "solves": f"{panel_ref_successes}/8, as expected",
        },
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] = 2 * int(doubled_params["n"])
    doubled = make_instance(seed=424_242, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    _, shipping_counts = _reference_algorithm(ship)
    _, doubled_counts = _reference_algorithm(doubled)
    report["G7_scales"] = {
        "pass": (
            doubled_ok
            and len(doubled["blocks"]) > len(ship["blocks"])
            and doubled_counts["operations"] > shipping_counts["operations"]
            and _atom_count(doubled["answer"]) == _atom_count(ship["answer"])
        ),
        "shipping_n": int(ship["n"]),
        "doubled_n": int(doubled["n"]),
        "shipping_blocks": len(ship["blocks"]),
        "doubled_blocks": len(doubled["blocks"]),
        "shipping_reference_operations": shipping_counts["operations"],
        "doubled_reference_operations": doubled_counts["operations"],
        "answer_atoms_shipping": _atom_count(ship["answer"]),
        "answer_atoms_doubled": _atom_count(doubled["answer"]),
        "doubled_verify_reason": doubled_reason,
    }

    invariant_checks = 0
    real_transform_checks = 0
    composed_checks = 0
    unrelated_keys = []
    g8_failures = []
    for seed in range(20):
        inst = make_instance(seed=20_000 + seed, **DIFFICULTY["medium"])
        key = canonical_key(inst)
        unrelated_keys.append(key)
        transformed = _renumber_and_reorder(inst, random.Random(30_000 + seed))
        composed = _renumber_and_reorder(transformed, random.Random(40_000 + seed))
        if canonical_key(transformed) == key:
            invariant_checks += 1
        else:
            g8_failures.append(f"single relabelling changed key at seed {seed}")
        if verify(transformed, inst["answer"])[0]:
            real_transform_checks += 1
        else:
            g8_failures.append(f"carried answer failed after relabelling at seed {seed}")
        if canonical_key(composed) == key and verify(composed, inst["answer"])[0]:
            composed_checks += 1
        else:
            g8_failures.append(f"composed transformation failed at seed {seed}")
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and distinct_count == 20,
        "invariance_checks": invariant_checks,
        "real_transformation_checks": real_transform_checks,
        "composed_transformation_checks": composed_checks,
        "unrelated_distinct": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "arbitrary positive/negative source-pair renumbering",
            "variable-table reordering",
            "block-row and within-block source reordering",
            "composition of all listed transformations",
        ],
        "failures": g8_failures,
    }

    answer_blob = json.dumps(ship["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    intended_ops = _intended_route_operations(ship)
    arms = {
        name: {
            "solved": int(G9_MEASUREMENTS[name]["solved"]),
            "attempts": int(G9_MEASUREMENTS[name]["attempts"]),
        }
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"]
        else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"]
        else 0.0
    )
    within_caps = (
        answer_chars <= 2_000
        and _atom_count(ship["answer"]) <= 256
        and intended_ops <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": _atom_count(ship["answer"]),
        "intended_route_operations": intended_ops,
    }

    required = [key for key in report if key.startswith("G")]
    report["all_pass"] = all(bool(report[key].get("pass")) for key in required)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
