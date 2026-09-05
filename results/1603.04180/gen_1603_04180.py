"""Verified problem generator derived from arXiv:1603.04180.

The paper's Section 2.2, Lemma 5 connects prescribed pairs of ell-sets by
short, mutually vertex-disjoint paths inside a reservoir.  This module uses the
smallest main-theorem case k=4, ell=1.  It describes a 4-uniform hypergraph by
an exact fixed-width colour predicate and asks for five simultaneous one-edge paths.

Generation is inverse: the reservoir vertices of each answer are sampled first
and terminal colours are chosen around them.  Verification never reads the
planted answer.
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
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "implicitly represented 4-uniform hypergraph",
        "singleton path ends",
        "reservoir vertex set",
    ],
    "verification_operations": [
        "integer range and distinctness checks",
        "exact fixed-width addition, rotation, and XOR",
        "hyperedge colour-XOR comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize that every add-rotate-XOR layer permutes the fixed-width colours, "
        "so a required complementary colour can be decoded instead of searched."
    ),
    "hardness_basis": (
        "Track B: the Section 2.2 connecting search is solved by an exhaustive "
        "colour scan in O(m*2^w*L) time; at the medium shipping preset it measured "
        "708,490 colour tests, 11,335,851 counted operations, and 10.110 seconds on "
        "average, while reversing the five permutation layers takes 90 exact word "
        "operations."
    ),
    "max_answer_tokens": 60,
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
        "A JSON list of m labelled unordered reservoir pairs [[a_i,b_i],...], "
        "with 0 <= a_i < b_i < r and all 2m indices distinct."
    ),
    "bounds": {
        "paths": 5,
        "vertices_per_path": 2,
        "maximum_atomic_elements": 10,
        "index_upper_bound": "instance r-1",
    },
}

STRUCTURAL_HINT = (
    "Each add-rotate-XOR layer in the displayed colour map permutes the fixed-width colour words."
)
PLACEBO_HINT = (
    "Each fixed-width arithmetic detail in the displayed colour map deserves especially careful handling."
)

# `blocks=None` means the quantitative hypotheses of Connecting Lemma 5 are
# satisfied with eta=1/(2q).  The tiny demo deliberately uses only one block.
DIFFICULTY = {
    "demo": {"n": 3, "m": 3, "layers": 1, "blocks": 1},
    "easy": {"n": 17, "m": 5, "layers": 4},
    "medium": {"n": 18, "m": 5, "layers": 5},
    "hard": {"n": 19, "m": 5, "layers": 6},
}

SHIPPING_DIFFICULTY = "medium"

# Filled from the three harness runs before final submission.  They are
# diagnostics, not gates; G9(c)'s size/operation caps are the gate.
G9_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 3, "errors": 0, "complete": True},
    "hinted": {"solved": 0, "attempts": 2, "errors": 4, "complete": False},
    "placebo": {"solved": 0, "attempts": 1, "errors": 4, "complete": False},
}

NOTES = """\
Section 1 defines an ell-path and Hamilton ell-cycle; Theorem 3 fixes the native
regime k>=4, 1<=ell<k/2.  Section 2.2, especially Connecting Lemma 5 and its
first proof case k-2>=2ell, fixes this task: connect prescribed singleton ends
through a reservoir by short disjoint paths.  The lemma itself also identifies
the easy mechanism--search a dense link neighbourhood--so this is Track B, not
Track A.  At k=4 and ell=1 a connector may be one edge.

The word-coloured hypergraph has exactly B representatives of every colour.
Consequently every two-set has about 1/q of all reservoir pairs as completions
before excluding its own vertices and at least eta=1/(2q) afterward.  With
B=2048*m*q^2, r=Bq is twice the lemma's required 32*k*m/eta^3 bound. Generation
still samples the connector first and chooses terminal colours around it.

Plants and decoys are reservoir indices from the same distribution.  The
outlier attack uses extreme indices; the greedy attack checks only a short list
of closest colour words; random restart tries 256 complete certificates; the
by-hand ansatz reverses only one mixing layer.  All are checked across eight
shipping seeds.  The honest reference algorithm fixes one vertex and scans a
whole colour space; it succeeds, as Track B requires, and is reported
separately from the failing attacks.
"""


def _rotl(x: int, amount: int, width: int) -> int:
    mask = (1 << width) - 1
    amount %= width
    return ((x << amount) | (x >> (width - amount))) & mask


def _rotr(x: int, amount: int, width: int) -> int:
    return _rotl(x, width - (amount % width), width)


def _perm(x: int, q: int, mixers: list[list[int]]) -> int:
    """A composition of exactly reversible add/rotate/XOR word maps."""

    mask = q - 1
    width = q.bit_length() - 1
    z = x & mask
    for add, key, rotation in mixers:
        z = (z + add) & mask
        z = _rotl(z, rotation, width)
        z ^= key
    return z


def _inverse_perm(y: int, q: int, mixers: list[list[int]]) -> int:
    mask = q - 1
    width = q.bit_length() - 1
    z = y & mask
    for add, key, rotation in reversed(mixers):
        z ^= key
        z = _rotr(z, rotation, width)
        z = (z - add) & mask
    return z


def _reservoir_colour(inst: dict, vertex: int) -> int:
    return _perm(vertex % inst["q"], inst["q"], inst["mixers"])


def _path_target(inst: dict, i: int) -> int:
    x, y = inst["terminal_colours"][i]
    return x ^ y


def _falling(n: int, k: int) -> int:
    out = 1
    for j in range(k):
        out *= n - j
    return out


def _route_operations(q: int, m: int, layers: int) -> int:
    del q
    # XOR, rotate, subtract per inverse layer, plus three XOR/index operations.
    return m * (3 * layers + 3)


def make_instance(
    n: int,
    seed: int = 0,
    m: int = 4,
    layers: int = 2,
    blocks: int | None = None,
    **params,
) -> dict:
    """Inverse-generate simultaneous connectors in a word-coloured 4-graph.

    `n` is the colour word width and q=2**n. Difficulty grows through the q
    possible colours while the witness always contains exactly 2m indices.
    """

    del params
    if not (1 <= m <= 8):
        raise ValueError("m must lie between 1 and 8")
    width = int(n)
    if not (3 <= width <= 60):
        raise ValueError("n (the word width) must lie between 3 and 60")
    if not (1 <= layers <= 20):
        raise ValueError("layers must lie between 1 and 20")
    q = 1 << width
    theorem_blocks = 2048 * m * q * q
    if blocks is None:
        blocks = theorem_blocks
    blocks = int(blocks)
    if blocks < 1:
        raise ValueError("at least one reservoir block is required")
    r = blocks * q
    if r < 2 * m:
        raise ValueError("the reservoir is too small for disjoint connectors")

    rng = random.Random(seed)
    mixers = [
        [rng.randrange(q), rng.randrange(q), rng.randrange(1, width)]
        for _ in range(layers)
    ]

    used: set[int] = set()
    answer: list[list[int]] = []
    targets: set[int] = set()
    target_list: list[int] = []
    for _ in range(m):
        # Sampling the witness first is the certificate-producing step.  Reject
        # only collisions and degenerate/repeated target colours, not hard cases.
        for _attempt in range(1000):
            a = rng.randrange(r)
            b = rng.randrange(r - 1)
            if b >= a:
                b += 1
            if a in used or b in used:
                continue
            target = _perm(a % q, q, mixers) ^ _perm(b % q, q, mixers)
            if target == 0 or target in targets:
                continue
            break
        else:
            raise RuntimeError("could not sample distinct connector targets")
        used.update((a, b))
        targets.add(target)
        target_list.append(target)
        answer.append(sorted([a, b]))

    # Keep the terminal configuration inside the span of the m planted target
    # colours. Random coefficient patterns create genuine affine-incidence
    # diversity; fully generic 2m colours would all be affinely independent and
    # hence isomorphic when the word width is large.
    terminal_colours: list[list[int]] = []
    for i, target in enumerate(target_list):
        coefficient_mask = rng.randrange(1 << m)
        x_colour = 0
        for j, basis_colour in enumerate(target_list):
            if (coefficient_mask >> j) & 1:
                x_colour ^= basis_colour
        y_colour = target ^ x_colour
        terminal_colours.append([x_colour, y_colour])

    eta_den = 2 * q
    required_r = 32 * 4 * m * eta_den**3
    theorem_condition = r >= required_r and blocks >= theorem_blocks
    # For nonzero target colours there are q/2 unordered colour pairs with B^2
    # representatives. For target zero there are q choices of two distinct
    # representatives of one colour. Take the smaller case, then exclude the
    # at most 2B pairs touching a reservoir vertex already in K.
    nonzero_completions = (q // 2) * blocks * blocks
    zero_completions = q * math.comb(blocks, 2)
    all_completing_pairs = min(nonzero_completions, zero_completions)
    disjoint_completion_lower_bound = all_completing_pairs - 2 * blocks

    return {
        "paper": "arXiv:1603.04180",
        "family": "simultaneous reservoir connectors in a 4-uniform hypergraph",
        "k": 4,
        "ell": 1,
        "m": m,
        "width": width,
        "q": q,
        "layers": layers,
        "mixers": mixers,
        "blocks": blocks,
        "r": r,
        "eta": [1, eta_den],
        "lemma_required_r": required_r,
        "theorem_condition": theorem_condition,
        "all_completing_pairs_per_two_set": all_completing_pairs,
        "disjoint_completion_lower_bound": disjoint_completion_lower_bound,
        "terminal_colours": terminal_colours,
        "answer": answer,
    }


def render(inst: dict) -> str:
    q = inst["q"]
    mixers = inst["mixers"]
    m = inst["m"]
    layer_text = []
    for j, (add, key, rotation) in enumerate(mixers):
        layer_text.append(
            f"  layer {j + 1}: add {add} modulo 2^{inst['width']}; "
            f"rotate the {inst['width']}-bit word left by {rotation}; XOR with {key}"
        )
    lines = [
        "Find simultaneous one-edge loose paths in the following 4-uniform hypergraph.",
        "",
        "Definitions.",
        "A 4-uniform hypergraph has vertices and unordered edges, each edge containing exactly four distinct vertices.",
        "A loose 1-path is an ordered sequence of such edges in which consecutive edges share exactly one vertex; a one-edge path has any chosen singleton at each end.",
        f"There are {2 * m} terminal vertices X0,Y0,...,X{m - 1},Y{m - 1} and reservoir vertices R_j for every integer 0 <= j < r.",
        f"Colours are {inst['width']}-bit unsigned words, so q = 2^{inst['width']} = {q}; XOR is bitwise exclusive-or.",
        "A left rotation moves bits falling off the most-significant end back into the least-significant end, keeping exactly the stated width.",
        f"The reservoir has B = {inst['blocks']} complete colour blocks and r = B*q = {inst['r']}.",
        "",
        "Reservoir colours.",
        f"For R_j start with the {inst['width']}-bit word z = j mod {q}. Apply these layers from top to bottom:",
        *layer_text,
        f"The final word is col(R_j), represented as an integer in 0,...,{q - 1}.",
        "Terminal colours are:",
    ]
    for i, (x, y) in enumerate(inst["terminal_colours"]):
        lines.append(f"  X{i}: {x}    Y{i}: {y}")
    lines.extend(
        [
            "",
            "Four distinct vertices form a hyperedge exactly when the bitwise XOR of their four colours is 0.",
            "For each i, connect Xi to Yi by one hyperedge {Xi,Yi,R_ai,R_bi}.",
            "The m paths must be mutually vertex-disjoint, so every reservoir index used anywhere must be different.",
            "",
            f"Return exactly {m} pairs in terminal order i=0,...,{m - 1}.",
            f"Within every pair require 0 <= a_i < b_i < {inst['r']}; indices are 0-based, the outer list order is fixed by i, and repeats are forbidden.",
            "Use a JSON list of two-integer lists.",
            "Give your final answer inside <answer></answer> tags, as [[a_0,b_0],[a_1,b_1],...].",
            f"Example: <answer>{json.dumps([[2*i, 2*i+1] for i in range(m)], separators=(',', ':'))}</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    try:
        match = re.search(r"<answer>(.*?)</answer>", text, re.IGNORECASE | re.DOTALL)
        if not match:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body).strip()
        value = json.loads(body)
        if not isinstance(value, list):
            return None
        if not all(
            isinstance(pair, list)
            and len(pair) == 2
            and all(isinstance(v, int) and not isinstance(v, bool) for v in pair)
            for pair in value
        ):
            return None
        return value
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    # Deliberately do not access inst["answer"] here.
    if not isinstance(answer, list):
        return False, "answer_not_a_list"
    if len(answer) == 0:
        return False, "answer_empty"
    if len(answer) != inst["m"]:
        return False, "wrong_number_of_paths"

    seen: set[int] = set()
    q = inst["q"]
    r = inst["r"]
    for i, pair in enumerate(answer):
        if not isinstance(pair, list):
            return False, f"path_{i}_not_a_list"
        if len(pair) != 2:
            return False, f"path_{i}_wrong_length"
        a, b = pair
        if not all(isinstance(v, int) and not isinstance(v, bool) for v in pair):
            return False, f"path_{i}_noninteger_vertex"
        if a == b:
            return False, f"path_{i}_repeated_vertex"
        if a > b:
            return False, f"path_{i}_not_increasing"
        if a < 0 or b >= r:
            return False, f"path_{i}_vertex_out_of_range"
        if a in seen or b in seen:
            return False, f"path_{i}_reuses_reservoir_vertex"
        seen.update((a, b))
        x_colour, y_colour = inst["terminal_colours"][i]
        total = (
            x_colour
            ^ y_colour
            ^ _reservoir_colour(inst, a)
            ^ _reservoir_colour(inst, b)
        )
        if total != 0:
            return False, f"path_{i}_four_set_is_not_an_edge"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniform over labelled unordered pairs with global distinctness."""

    r = inst["r"]
    chosen: set[int] = set()
    out: list[list[int]] = []
    for _ in range(inst["m"]):
        while True:
            a = rng.randrange(r)
            if a not in chosen:
                chosen.add(a)
                break
        while True:
            b = rng.randrange(r)
            if b not in chosen:
                chosen.add(b)
                break
        out.append(sorted([a, b]))
    return out


def search_space(inst: dict) -> int | None:
    r = inst["r"]
    m = inst["m"]
    return _falling(r, 2 * m) // (2**m)


def enumerate_all(inst: dict) -> int | None:
    """Count by bounded backtracking only on genuinely small instances."""

    if search_space(inst) > 300_000:
        return None
    r = inst["r"]
    pairs_by_path: list[list[tuple[int, int]]] = []
    for i in range(inst["m"]):
        good = []
        for a in range(r):
            for b in range(a + 1, r):
                candidate = [[0, 1] for _ in range(inst["m"])]
                candidate[i] = [a, b]
                x, y = inst["terminal_colours"][i]
                if (x ^ y ^ _reservoir_colour(inst, a) ^ _reservoir_colour(inst, b)) == 0:
                    good.append((a, b))
        pairs_by_path.append(good)

    count = 0

    def visit(i: int, used: set[int]) -> None:
        nonlocal count
        if i == inst["m"]:
            count += 1
            return
        for a, b in pairs_by_path[i]:
            if a not in used and b not in used:
                visit(i + 1, used | {a, b})

    visit(0, set())
    return count


def _linear_relation_code(sequence: list[int]) -> list[int]:
    """Coordinates in the greedily encountered basis, invariant under GL(w,2)."""

    pivots: dict[int, tuple[int, int]] = {}
    rank = 0
    code = []
    for value in sequence:
        x = value
        coordinates = 0
        for pivot in sorted(pivots, reverse=True):
            if (x >> pivot) & 1:
                row, row_coordinates = pivots[pivot]
                x ^= row
                coordinates ^= row_coordinates
        if x:
            new_coordinate = 1 << rank
            rank += 1
            pivot = x.bit_length() - 1
            pivots[pivot] = (x, coordinates ^ new_coordinate)
            coordinates = new_coordinate
        code.append(coordinates)
    return code


def _canonical_terminal_configuration(inst: dict) -> list[int]:
    """Canonical under affine colour maps and pair reorder/endpoint swap."""

    pairs = inst["terminal_colours"]
    forms = []
    for order in itertools.permutations(range(len(pairs))):
        for swaps in range(1 << len(pairs)):
            sequence = []
            for position, i in enumerate(order):
                a, b = pairs[i]
                if (swaps >> position) & 1:
                    a, b = b, a
                sequence.extend((a, b))
            # Pair permutations and endpoint swaps make every terminal eligible
            # as the origin, so no separate translation loop is needed.
            origin = sequence[0]
            forms.append(_linear_relation_code([v ^ origin for v in sequence]))
    return min(forms)


def canonical_key(inst: dict) -> str:
    """Canonical under block relabelling, terminal symmetries, and affine colour maps."""

    payload = {
        "q": inst["q"],
        "blocks": inst["blocks"],
        "m": inst["m"],
        "terminal_configuration": _canonical_terminal_configuration(inst),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Increase colour crowding at fixed witness length, then respect G9(c)."""

    p = {k: v for k, v in params.items() if k != "_preset"}
    n = int(p.get("n", 3))
    m = int(p.get("m", 4))
    layers = int(p.get("layers", 1))
    if layers < 8:
        layers += 1
    else:
        n += 1
    q = 1 << n
    if _route_operations(q, m, layers) > 300:
        return "cap_bound"
    return {"n": n, "m": m, "layers": layers}


def _reference_scan(inst: dict) -> tuple[list[list[int]], int, int]:
    """Mechanical Track-B baseline: fix one colour and scan one full period."""

    q = inst["q"]
    out = []
    evaluations = 0
    for i in range(inst["m"]):
        first = (2 * i) * q
        need = _path_target(inst, i) ^ _reservoir_colour(inst, first)
        found = None
        for residue in range(q):
            evaluations += 1
            if _perm(residue, q, inst["mixers"]) == need:
                found = (2 * i + 1) * q + residue
                break
        if found is None:
            raise AssertionError("permutation scan found no complementary colour")
        out.append(sorted([first, found]))
    operations = evaluations * (3 * inst["layers"] + 1) + 3 * inst["m"]
    return out, evaluations, operations


def _attack_outlier(inst: dict) -> list[list[int]]:
    return [[2 * i, 2 * i + 1] for i in range(inst["m"])]


def _attack_greedy_shortlist(inst: dict, width: int = 32) -> list[list[int]]:
    q = inst["q"]
    out = []
    for i in range(inst["m"]):
        a = (2 * i) * q
        target = _path_target(inst, i)
        best = None
        for residue in range(min(width, q)):
            b = (2 * i + 1) * q + residue
            residual = target ^ _reservoir_colour(inst, a) ^ _reservoir_colour(inst, b)
            score = residual
            if best is None or score < best[0]:
                best = (score, b)
        out.append(sorted([a, best[1]]))
    return out


def _attack_single_layer(inst: dict) -> list[list[int]]:
    q = inst["q"]
    width = inst["width"]
    mask = q - 1
    out = []
    for i in range(inst["m"]):
        a = (2 * i) * q
        need = _path_target(inst, i) ^ _reservoir_colour(inst, a)
        # Reverse only the outermost layer, the most plausible incomplete ansatz.
        add, key, rotation = inst["mixers"][-1]
        residue = (_rotr(need ^ key, rotation, width) - add) & mask
        b = (2 * i + 1) * q + residue
        out.append(sorted([a, b]))
    return out


def _affine_colour(colour: int, width: int, offset: int) -> int:
    mask = (1 << width) - 1
    shift = 1 + (offset % (width - 1))
    rotation = 1 + ((offset // width) % (width - 1))
    z = colour ^ ((colour << shift) & mask)
    z = _rotl(z, rotation, width)
    return z ^ (offset & mask)


def _transform_affine_colours(inst: dict, offset: int) -> tuple[dict, list[list[int]]]:
    q = inst["q"]
    width = inst["width"]
    out = copy.deepcopy(inst)
    out["terminal_colours"] = [
        [_affine_colour(a, width, offset), _affine_colour(b, width, offset)]
        for a, b in inst["terminal_colours"]
    ]
    carried = []
    for pair in inst["answer"]:
        new_pair = []
        for vertex in pair:
            block, residue = divmod(vertex, q)
            old_colour = _perm(residue, q, inst["mixers"])
            new_colour = _affine_colour(old_colour, width, offset)
            new_residue = _inverse_perm(new_colour, q, inst["mixers"])
            new_pair.append(block * q + new_residue)
        carried.append(sorted(new_pair))
    out["answer"] = carried
    return out, carried


def _transform_mapping(inst: dict, delta: int) -> tuple[dict, list[list[int]]]:
    q = inst["q"]
    width = inst["width"]
    new_mixers = [
        [
            (add + delta * (j + 1)) % q,
            key ^ ((delta * (2 * j + 1)) % q),
            1 + ((rotation + delta + j - 1) % (width - 1)),
        ]
        for j, (add, key, rotation) in enumerate(inst["mixers"])
    ]
    out = copy.deepcopy(inst)
    out["mixers"] = new_mixers
    carried = []
    for pair in inst["answer"]:
        new_pair = []
        for vertex in pair:
            block, residue = divmod(vertex, q)
            colour = _perm(residue, q, inst["mixers"])
            new_residue = _inverse_perm(colour, q, new_mixers)
            new_pair.append(block * q + new_residue)
        carried.append(sorted(new_pair))
    out["answer"] = carried
    return out, carried


def _transform_pair_order(inst: dict) -> tuple[dict, list[list[int]]]:
    order = list(reversed(range(inst["m"])))
    out = copy.deepcopy(inst)
    out["terminal_colours"] = [list(reversed(inst["terminal_colours"][i])) for i in order]
    carried = [inst["answer"][i][:] for i in order]
    out["answer"] = carried
    return out, carried


def _transform_blocks(inst: dict) -> tuple[dict, list[list[int]]]:
    q = inst["q"]
    blocks = inst["blocks"]
    out = copy.deepcopy(inst)
    carried = []
    for pair in inst["answer"]:
        new_pair = []
        for vertex in pair:
            block, residue = divmod(vertex, q)
            new_pair.append(((block + 1) % blocks) * q + residue)
        carried.append(sorted(new_pair))
    out["answer"] = carried
    return out, carried


def selftest() -> dict:
    report: dict = {
        "paper": "1603.04180",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": DIFFICULTY[SHIPPING_DIFFICULTY],
    }

    # G1: every preset and three independent seeds.
    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer_not_json_native"])
            if preset != "demo":
                if not inst["theorem_condition"] or inst["r"] < inst["lemma_required_r"]:
                    g1_failures.append([preset, seed, "connecting_lemma_size_bound_failed"])
                if (
                    inst["disjoint_completion_lower_bound"] * inst["eta"][1]
                    < math.comb(inst["r"], 2) * inst["eta"][0]
                ):
                    g1_failures.append([preset, seed, "connecting_lemma_degree_bound_failed"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "theorem_condition_checks": 9,
        "failures": g1_failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **ship_params)

    corruptions = {}
    a = copy.deepcopy(inst["answer"])
    a[0] = a[0][:-1]
    corruptions["drop_one"] = verify(inst, a)
    a = copy.deepcopy(inst["answer"])
    a[0] = list(reversed(a[0]))
    corruptions["swap_pair_order"] = verify(inst, a)
    a = copy.deepcopy(inst["answer"])
    a[0][1] = a[0][0]
    corruptions["duplicate"] = verify(inst, a)
    corruptions["empty"] = verify(inst, [])
    a = copy.deepcopy(inst["answer"])
    a[0][1] = inst["r"]
    corruptions["out_of_range"] = verify(inst, a)
    reasons = [reason for ok, reason in corruptions.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(not ok for ok, _ in corruptions.values()) and len(set(reasons)) == len(reasons),
        "cases": {name: {"accepted": ok, "reason": reason} for name, (ok, reason) in corruptions.items()},
    }

    model_response = (
        "I checked every exact colour XOR.\n```json\n<answer>"
        + json.dumps(inst["answer"])
        + "</answer>\n```\nThose are the connectors."
    )
    parsed = parse_answer(model_response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and parse_answer("garbage") is None,
        "realistic_response_parsed": parsed == inst["answer"],
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    # G4/G5 shipping density, sampled from the declared structured language.
    guess_total = 200_000
    guess_hits = 0
    guess_rng = random.Random(8675309)
    for _ in range(guess_total):
        ok, _ = verify(inst, random_candidate(inst, guess_rng))
        guess_hits += int(ok)
    guess_rate = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_rate < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "empirical_probability": guess_rate,
        "candidate_space": search_space(inst),
        "prior": "uniform labelled disjoint unordered reservoir pairs",
    }

    demo_inst = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)

    # G6 and the Track-B reference algorithm, all at the shipping preset.
    attack_names = (
        "outlier_extreme_indices",
        "greedy_nearest_colour_32",
        "random_restart_256",
        "by_hand_single_layer_ansatz",
    )
    attack_successes = {name: 0 for name in attack_names}
    attack_attempts = {name: 0 for name in attack_names}
    ref_successes = 0
    ref_evaluations = []
    ref_operations = []
    ref_seconds = []
    for seed in range(8):
        probe = make_instance(seed=10_000 + seed, **ship_params)
        guesses = {
            "outlier_extreme_indices": _attack_outlier(probe),
            "greedy_nearest_colour_32": _attack_greedy_shortlist(probe),
            "by_hand_single_layer_ansatz": _attack_single_layer(probe),
        }
        rr_rng = random.Random(90_000 + seed)
        rr_answer = None
        for _ in range(256):
            candidate = random_candidate(probe, rr_rng)
            if verify(probe, candidate)[0]:
                rr_answer = candidate
                break
        guesses["random_restart_256"] = rr_answer
        for name, candidate in guesses.items():
            attack_attempts[name] += 1
            if candidate is not None and verify(probe, candidate)[0]:
                attack_successes[name] += 1

        t0 = time.perf_counter()
        ref_answer, evaluations, operations = _reference_scan(probe)
        elapsed = time.perf_counter() - t0
        ref_successes += int(verify(probe, ref_answer)[0])
        ref_evaluations.append(evaluations)
        ref_operations.append(operations)
        ref_seconds.append(elapsed)

    attacks = {
        name: {
            "successes": attack_successes[name],
            "attempts": attack_attempts[name],
        }
        for name in attack_names
    }
    reference = {
        "name": "period-aware exhaustive complementary-colour scan",
        "complexity": "O(m*2^width*layers) exact word operations",
        "wall_clock_sec_mean": sum(ref_seconds) / len(ref_seconds),
        "wall_clock_sec_max": max(ref_seconds),
        "colour_evaluations_mean": sum(ref_evaluations) / len(ref_evaluations),
        "operations_mean": sum(ref_operations) / len(ref_operations),
        "operations_max": max(ref_operations),
        "successes": ref_successes,
        "attempts": 8,
        "solves": f"{ref_successes}/8, as expected",
    }
    report["G5_density_and_baseline"] = {
        "pass": guess_rate < 1e-6 and ref_successes == 8,
        "shipping_solution_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_estimate": guess_rate,
        "demo_exact_solution_count": demo_count,
        "demo_candidate_count": search_space(demo_inst),
        "baseline_wall_clock_seconds_mean": reference["wall_clock_sec_mean"],
        "baseline_colour_iterations_mean": reference["colour_evaluations_mean"],
        "baseline_operations_mean": reference["operations_mean"],
    }
    report["G6_adversary_panel"] = {
        "pass": all(v["successes"] == 0 and v["attempts"] >= 8 for v in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": reference,
    }

    doubled = dict(ship_params)
    doubled["n"] = int(doubled["n"]) + 1
    bigger = make_instance(seed=271828, **doubled)
    bigger_ok, bigger_reason = verify(bigger, bigger["answer"])
    report["G7_scales"] = {
        "pass": bigger_ok and bigger["q"] > inst["q"] and search_space(bigger) > search_space(inst),
        "shipping_q": inst["q"],
        "doubled_q": bigger["q"],
        "answer_elements_before": 2 * inst["m"],
        "answer_elements_after": 2 * bigger["m"],
        "doubled_verify_reason": bigger_reason,
    }

    invariant_checks = 0
    transform_checks = 0
    invariance_failures = []
    keys = []
    for seed in range(20):
        base = make_instance(seed=50_000 + seed, **ship_params)
        key = canonical_key(base)
        keys.append(key)
        offset = 1 + seed
        transformed = []
        affine, affine_answer = _transform_affine_colours(base, offset)
        transformed.append(("affine_colour_map", affine, affine_answer))
        mapped, mapped_answer = _transform_mapping(base, seed + 1)
        transformed.append(("mapping_relabel", mapped, mapped_answer))
        reordered, reordered_answer = _transform_pair_order(base)
        transformed.append(("pair_reorder_swap", reordered, reordered_answer))
        blocked, blocked_answer = _transform_blocks(base)
        transformed.append(("block_rotation", blocked, blocked_answer))
        # One genuine composition, as required by the gate wording.
        composed, composed_answer = _transform_pair_order(affine)
        transformed.append(("affine_then_pair_reorder", composed, composed_answer))
        for name, changed, carried in transformed:
            invariant_checks += 1
            if canonical_key(changed) != key:
                invariance_failures.append([seed, name, "key_changed"])
            ok, reason = verify(changed, carried)
            transform_checks += 1
            if not ok:
                invariance_failures.append([seed, name, reason])
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": not invariance_failures and distinct == 20,
        "invariance_checks": invariant_checks,
        "valid_transformation_checks": transform_checks,
        "distinct_unrelated_keys": distinct,
        "unrelated_instances": 20,
        "failures": invariance_failures,
        "symmetries": [
            "invertible affine colour maps over GF(2)",
            "reservoir colour-coordinate relabelling",
            "terminal-pair reorder and endpoint swap",
            "reservoir block rotation",
            "compositions of the above",
        ],
    }

    blobs = [json.dumps(make_instance(seed=s, **ship_params)["answer"]) for s in range(20)]
    answer_chars = max(map(len, blobs))
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = 2 * inst["m"]
    route_ops = _route_operations(inst["q"], inst["m"], inst["layers"])
    arms = copy.deepcopy(G9_ARM_RESULTS)
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
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and route_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": (
            "incomplete_api_quota"
            if not arms["hinted"].get("complete", False)
            else "not_yet_measured"
            if arms["hinted"]["attempts"] == 0
            else ("too_easy" if arms["hinted"]["solved"] else "hardened")
        ),
        "diagnostic_complete": all(
            arm.get("complete", False) for arm in arms.values()
        ),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": route_ops,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
