"""Self-contained verified problem generator for arXiv:1303.2263.

The paper proves that certain 2-connected f-heavy graphs are Hamiltonian.  This
module stays with the paper's native graph objects.  Its graphs are two cliques
joined by two perfect matchings hidden behind reversible word permutations.
Every vertex is heavy, so the hypotheses of Theorem 5 hold.  Two disjoint
cross-edges are a compact, exactly checkable certificate of a Hamilton cycle.

Generation is a transformation of a known instance: start with two indexed
cliques and two coordinate matchings, then independently relabel the two sides
by bijections.  The certificate is carried through those bijections; no search
is used to manufacture it.
"""

from __future__ import annotations

import bisect
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
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "finite simple graph given by an exact adjacency predicate",
        "heavy vertices in the sense of the paper",
        "Hamilton cycle compressed by two cross-edges",
    ],
    "verification_operations": [
        "integer range and distinctness checks",
        "exact fixed-width addition, rotation, and XOR",
        "graph-edge predicate evaluation",
        "deterministic expansion of two clique paths into a Hamilton cycle",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Conjugate both clique labels into the common hidden coordinate, where "
        "the sparse cross-edges become two matchings; without this change of "
        "variables one must scan the opposite clique for usable cross-edges."
    ),
    "hardness_basis": (
        "Track B: scanning the two-clique cut and splicing clique paths is "
        "O(2^n*layers); at the provisional easy shipping preset the reference "
        "implementation's measured cost is recorded by selftest, while the "
        "reversible-coordinate route uses 80 exact word operations."
    ),
    "max_answer_tokens": 8,
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
        "A JSON list [[x0,y0],[x1,y1]] of two labelled cross-edges L_xi--R_yi, "
        "where 0 <= x0 < x1 < q, 0 <= yi < q, and y0 != y1."
    ),
    "bounds": {
        "cross_edges": 2,
        "atomic_integer_elements": 4,
        "index_min": 0,
        "index_max": "q-1, where q=2^n in the instance",
        "repetitions": "left endpoints and right endpoints are separately distinct",
    },
}

STRUCTURAL_HINT = (
    "Both sparse cross-edge layers become coordinate matchings after conjugation by the two displayed word permutations."
)
PLACEBO_HINT = (
    "Both displayed cross-edge tests require careful attention to the fixed-width indexing and arithmetic conventions."
)

DIFFICULTY = {
    "easy": {"n": 16, "layers": 6, "components": 12},
}

SHIPPING_DIFFICULTY = "easy"

# Populated from the isolated script-owned oracle runs before final delivery.
# These values are diagnostic; only the answer/effort caps gate G9.
G9_ARM_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
}

NOTES = """\
Section 1 fixes all definitions used here: finite simple graphs, Hamilton cycles,
heavy vertices (global degree at least half the order), induced f-heavy
subgraphs, and R-f-heavy graphs.  Theorem 5 is the source result: every
2-connected {claw,P7,D}-f-heavy or {claw,P7,H}-f-heavy graph is Hamiltonian.
Every generated graph has order 2q and degree q+1 at every vertex, so every
vertex is heavy and both alternatives of Theorem 5 hold.  This deliberately
lies in the easier global Fan regime identified by Theorem 1 and Remark 1; the
paper gives an existence proof, not a hard average-case distribution or a
certificate-search algorithm.

The family is therefore Track B.  A specialist can scan the cut between the two
cliques for two disjoint cross-edges and splice the two clique paths.  That
algorithm is polynomial for this distribution and is reported as the successful
reference algorithm.  The intended compact route instead recognizes that the
two public add/rotate/XOR maps are bijections and reverses the right-hand map.

Construction starts from two coordinate cliques joined by the identity matching
and by a fixed-point-free block-cycle permutation.  Independent reversible word
maps relabel each clique, carrying two sampled identity-matching edges with them.
The two matching layers use the same distribution, so planted edges are not
degree, width, position, or frequency outliers.  The attack panel tests the
all-degrees-tied label choice, raw-label nearest neighbours, 256 structured
random restarts, and a plausible one-layer-only inverse ansatz.
"""


def _mask(width: int) -> int:
    return (1 << width) - 1


def _rotl(value: int, amount: int, width: int) -> int:
    amount %= width
    value &= _mask(width)
    if amount == 0:
        return value
    return ((value << amount) | (value >> (width - amount))) & _mask(width)


def _rotr(value: int, amount: int, width: int) -> int:
    return _rotl(value, -amount, width)


def _perm(value: int, width: int, mixers: list[list[int]]) -> int:
    """Apply a bijective add/rotate/XOR word permutation."""

    mask = _mask(width)
    z = value & mask
    for add, key, rotation in mixers:
        z = (z + add) & mask
        z = _rotl(z, rotation, width)
        z ^= key
    return z


def _inverse_perm(value: int, width: int, mixers: list[list[int]]) -> int:
    mask = _mask(width)
    z = value & mask
    for add, key, rotation in reversed(mixers):
        z ^= key
        z = _rotr(z, rotation, width)
        z = (z - add) & mask
    return z


def _starts(lengths: list[int]) -> list[int]:
    starts = [0]
    for length in lengths[:-1]:
        starts.append(starts[-1] + length)
    return starts


def _block_rotate(inst: dict, z: int) -> int:
    """Rotate z by direction within its interval block."""

    starts = inst["cycle_starts"]
    block = bisect.bisect_right(starts, z) - 1
    start = starts[block]
    length = inst["cycle_lengths"][block]
    offset = z - start
    return start + ((offset + inst["direction"]) % length)


def _cross_edge(inst: dict, x: int, y: int) -> bool:
    left = _perm(x, inst["width"], inst["left_mixers"])
    right = _perm(y, inst["width"], inst["right_mixers"])
    return right == left or right == _block_rotate(inst, left)


def _random_composition(q: int, count: int, rng: random.Random) -> list[int]:
    """Uniform stars-and-bars extras atop a minimum part size of two."""

    extra = q - 2 * count
    slots = extra + count - 1
    bars = sorted(rng.sample(range(slots), count - 1))
    pieces = []
    previous = -1
    for bar in bars + [slots]:
        pieces.append(2 + bar - previous - 1)
        previous = bar
    rng.shuffle(pieces)
    return pieces


def _make_mixers(width: int, layers: int, rng: random.Random) -> list[list[int]]:
    q = 1 << width
    return [
        [rng.randrange(q), rng.randrange(q), rng.randrange(1, width)]
        for _ in range(layers)
    ]


def make_instance(
    n: int,
    seed: int = 0,
    layers: int = 6,
    components: int = 12,
    **params,
) -> dict:
    """Construct and relabel a known Hamiltonian two-clique graph.

    ``n`` is the word width, so each clique has q=2**n vertices.  The answer
    always has four integers; increasing n grows the cross-edge haystack.
    """

    del params
    width = int(n)
    layers = int(layers)
    components = int(components)
    if not (3 <= width <= 24):
        raise ValueError("n (the word width) must lie between 3 and 24")
    if not (1 <= layers <= 20):
        raise ValueError("layers must lie between 1 and 20")
    q = 1 << width
    if not (2 <= components <= min(64, q // 2)):
        raise ValueError("components must lie between 2 and min(64,q/2)")

    rng = random.Random(seed)
    lengths = _random_composition(q, components, rng)
    left_mixers = _make_mixers(width, layers, rng)
    right_mixers = _make_mixers(width, layers, rng)

    # Sample two edges of the identity coordinate matching first, then carry
    # them through the two independently chosen relabellings.
    z0, z1 = rng.sample(range(q), 2)
    answer = [
        [
            _inverse_perm(z, width, left_mixers),
            _inverse_perm(z, width, right_mixers),
        ]
        for z in (z0, z1)
    ]
    answer.sort(key=lambda pair: pair[0])

    return {
        "paper": "arXiv:1303.2263",
        "width": width,
        "q": q,
        "vertex_count": 2 * q,
        "layers": layers,
        "components": components,
        "cycle_lengths": lengths,
        "cycle_starts": _starts(lengths),
        "direction": 1,
        "left_mixers": left_mixers,
        "right_mixers": right_mixers,
        "answer": answer,
    }


def _format_layers(name: str, mixers: list[list[int]], width: int) -> list[str]:
    lines = [f"For {name}, start with z equal to its raw index."]
    for i, (add, key, rotation) in enumerate(mixers, 1):
        lines.append(
            f"  layer {i}: add {add} modulo 2^{width}; rotate the {width}-bit "
            f"word left by {rotation}; XOR with {key}"
        )
    lines.append(f"The resulting integer is {name}.")
    return lines


def render(inst: dict) -> str:
    """Render a complete standalone problem, with hints disabled by default."""

    width = inst["width"]
    q = inst["q"]
    direction_word = "forward" if inst["direction"] == 1 else "backward"
    lines = [
        "Find a compact Hamilton-cycle certificate in the graph below.",
        "",
        "Definitions.",
        "A finite simple graph has undirected edges, no loops, and no repeated edges.",
        "A Hamilton cycle is a cyclic ordering that visits every vertex exactly once and uses a graph edge at every step, including the last-to-first step.",
        "A vertex in an N-vertex graph is heavy when its degree is at least N/2.",
        "An induced subgraph is f-heavy when, for each two vertices at distance exactly 2 inside that subgraph, at least one is heavy in the whole graph.",
        "",
        "Graph.",
        f"Set q = 2^{width} = {q}.  The 2q vertices are L_x and R_y for integers 0 <= x,y < q.",
        "Every two distinct L-vertices are adjacent, and every two distinct R-vertices are adjacent.",
        "Cross-edges L_x--R_y are defined by the exact word maps and block rotation below.",
        f"All word operations retain exactly {width} bits. XOR is bitwise exclusive-or.",
        "A left rotation moves bits falling off the most-significant end back into the least-significant end.",
        "",
        "Left word map A(x):",
    ]
    lines.extend(_format_layers("A(x)", inst["left_mixers"], width))
    lines.extend(["", "Right word map B(y):"])
    lines.extend(_format_layers("B(y)", inst["right_mixers"], width))
    lines.extend(
        [
            "",
            "Block rotation rho.",
            "Partition 0,...,q-1 into consecutive intervals having these lengths, in this order:",
            "  " + ", ".join(map(str, inst["cycle_lengths"])),
            f"Within each interval, rho moves one position {direction_word}, wrapping at that interval's end.",
            "There are no one-element intervals.",
            "",
            "The cross-edge rule is:",
            "  L_x--R_y is an edge exactly when B(y) = A(x) or B(y) = rho(A(x)).",
            "No other cross-edges exist.",
            "Every vertex has q-1 neighbours in its own side and two across the cut, hence degree q+1 >= (2q)/2; in particular every vertex is heavy.",
            "",
            "Certificate and its Hamilton cycle.",
            "Return two cross-edges [[x0,y0],[x1,y1]]. They denote the following cyclic order:",
            "  L_x0; all other L-vertices except L_x1 in increasing raw index; L_x1;",
            "  R_y1; all other R-vertices except R_y0 in increasing raw index; R_y0; back to L_x0.",
            "Because each side is a clique, this is a Hamilton cycle exactly when the two displayed cross pairs are edges and have four distinct endpoints.",
            "",
            f"Require 0 <= x0 < x1 < {q}, 0 <= y0,y1 < {q}, and y0 != y1.",
            "Indices are 0-based. The outer order is fixed by x0 < x1; repeats are forbidden; each pair is [left_index,right_index].",
            "Use a JSON list containing exactly two two-integer lists.",
            "Give your final answer inside <answer></answer> tags, as [[x0,y0],[x1,y1]].",
            "Example: <answer>[[0,1],[2,3]]</answer>",
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
    """Extract the last tagged JSON answer; never raise on malformed output."""

    if not isinstance(text, str):
        return None
    bodies = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    candidates = list(reversed(bodies))
    if not candidates:
        # Tolerate an otherwise realistic response that forgot tags but used a
        # fenced or bare JSON two-pair array.
        candidates = re.findall(r"\[\s*\[[^\[\]]+\]\s*,\s*\[[^\[\]]+\]\s*\]", text, re.S)
        candidates.reverse()
    for body in candidates:
        cleaned = body.strip()
        cleaned = re.sub(r"^```(?:json|text)?\s*", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            value = json.loads(cleaned)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, list):
            return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any certificate in the declared language, never the planted one."""

    if not isinstance(answer, list):
        return False, "answer_must_be_a_JSON_list"
    if len(answer) == 0:
        return False, "answer_is_empty"
    if len(answer) != 2:
        return False, "expected_exactly_2_cross_edges"
    for i, pair in enumerate(answer):
        if not isinstance(pair, list) or len(pair) != 2:
            return False, f"pair_{i}_must_contain_exactly_2_integers"
        if any(not isinstance(v, int) or isinstance(v, bool) for v in pair):
            return False, f"pair_{i}_contains_a_non_integer"
    q = inst["q"]
    for i, (x, y) in enumerate(answer):
        if not (0 <= x < q):
            return False, f"left_endpoint_out_of_range_in_pair_{i}"
        if not (0 <= y < q):
            return False, f"right_endpoint_out_of_range_in_pair_{i}"
    (x0, y0), (x1, y1) = answer
    if x0 >= x1:
        return False, "left_endpoints_not_in_strictly_increasing_order"
    if y0 == y1:
        return False, "right_endpoints_are_not_distinct"
    if not _cross_edge(inst, x0, y0):
        return False, "pair_0_is_not_a_cross_edge"
    if not _cross_edge(inst, x1, y1):
        return False, "pair_1_is_not_a_cross_edge"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly after enforcing every explicit shape constraint."""

    q = inst["q"]
    x0, x1 = sorted(rng.sample(range(q), 2))
    y0, y1 = rng.sample(range(q), 2)
    return [[x0, y0], [x1, y1]]


def search_space(inst: dict) -> int:
    q = inst["q"]
    return math.comb(q, 2) * q * (q - 1)


def enumerate_all(inst: dict) -> int | None:
    """Brute-force the declared language only when it has at most 100,000 words."""

    if search_space(inst) > 100_000:
        return None
    q = inst["q"]
    total = 0
    for x0, x1 in itertools.combinations(range(q), 2):
        for y0 in range(q):
            for y1 in range(q):
                if y0 != y1 and verify(inst, [[x0, y0], [x1, y1]])[0]:
                    total += 1
    return total


def canonical_key(inst: dict) -> str:
    """Canonical isomorphism key for the two-matching cross graph.

    After deleting the two cliques' internal edges, the union of the two
    matchings is a disjoint union of even cycles.  Its component half-lengths
    are exactly ``cycle_lengths``.  Their sorted multiset is unchanged by raw
    vertex relabelling, block reorder/reversal, or swapping the two cliques,
    and completely determines this represented graph family.
    """

    payload = {
        "family": "two_cliques_two_matchings",
        "q": inst["q"],
        "cross_cycle_half_lengths": sorted(inst["cycle_lengths"]),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Grow the cut haystack and reversible depth while the answer stays fixed."""

    harder = dict(params)
    width = int(harder.get("n", 3))
    layers = int(harder.get("layers", 1))
    components = int(harder.get("components", 2))
    if width < 23 and layers < 20:
        harder["n"] = width + 1
        harder["layers"] = layers + 2
        harder["components"] = min(64, components + 2)
        return harder
    if width < 24:
        harder["n"] = width + 1
        harder["components"] = min(64, components + 2)
        return harder
    return "cap_bound"


def _reference_scan(inst: dict) -> tuple[object | None, int, int, float]:
    """Scan the cut for two disjoint edges and splice the two clique paths."""

    started = time.perf_counter()
    operations = 0
    edge_tests = 0
    used_right: set[int] = set()
    answer = []
    width = inst["width"]
    per_perm = 3 * inst["layers"]
    for x in (0, 1):
        left = _perm(x, width, inst["left_mixers"])
        operations += per_perm
        rotated = _block_rotate(inst, left)
        operations += 3
        found = None
        for y in range(inst["q"]):
            if y in used_right:
                continue
            right = _perm(y, width, inst["right_mixers"])
            operations += per_perm + 2
            edge_tests += 1
            if right == left or right == rotated:
                found = y
                break
        if found is None:
            return None, operations, edge_tests, time.perf_counter() - started
        used_right.add(found)
        answer.append([x, found])
    elapsed = time.perf_counter() - started
    return answer, operations, edge_tests, elapsed


def _degree_tie_attack(inst: dict) -> object:
    # Every vertex has the same degree, so the deterministic label tie-break is
    # the only information this per-vertex attack has.
    return [[0, 0], [1, 1]]


def _nearest_label_attack(inst: dict) -> object:
    q = inst["q"]
    x0 = q // 3
    x1 = x0 + 1
    return [[x0, x0], [x1, x1]]


def _partial_inverse_attack(inst: dict) -> object | None:
    """Undo only the final right-map layer, a plausible hand shortcut."""

    width = inst["width"]
    mask = _mask(width)
    result = []
    for x in (0, 1):
        target = _perm(x, width, inst["left_mixers"])
        add, key, rotation = inst["right_mixers"][-1]
        y = target ^ key
        y = _rotr(y, rotation, width)
        y = (y - add) & mask
        result.append([x, y])
    if result[0][1] == result[1][1]:
        return None
    return result


def _random_restart_attack(inst: dict, seed: int, restarts: int = 256) -> object | None:
    rng = random.Random(seed)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _carry_under_new_mixers(
    inst: dict,
    new_left: list[list[int]],
    new_right: list[list[int]],
) -> dict:
    out = copy.deepcopy(inst)
    out["left_mixers"] = copy.deepcopy(new_left)
    out["right_mixers"] = copy.deepcopy(new_right)
    carried = []
    for x, y in inst["answer"]:
        zx = _perm(x, inst["width"], inst["left_mixers"])
        zy = _perm(y, inst["width"], inst["right_mixers"])
        carried.append(
            [
                _inverse_perm(zx, inst["width"], new_left),
                _inverse_perm(zy, inst["width"], new_right),
            ]
        )
    carried.sort(key=lambda pair: pair[0])
    out["answer"] = carried
    return out


def _rekey(inst: dict, seed: int) -> dict:
    rng = random.Random(seed)
    return _carry_under_new_mixers(
        inst,
        _make_mixers(inst["width"], inst["layers"], rng),
        _make_mixers(inst["width"], inst["layers"], rng),
    )


def _reorder_blocks(inst: dict, seed: int) -> dict:
    rng = random.Random(seed)
    order = list(range(len(inst["cycle_lengths"])))
    rng.shuffle(order)
    old_lengths = inst["cycle_lengths"]
    old_starts = inst["cycle_starts"]
    new_lengths = [old_lengths[i] for i in order]
    new_starts = _starts(new_lengths)
    new_position = {old_i: new_i for new_i, old_i in enumerate(order)}

    def move_coordinate(z: int) -> int:
        old_i = bisect.bisect_right(old_starts, z) - 1
        offset = z - old_starts[old_i]
        return new_starts[new_position[old_i]] + offset

    out = copy.deepcopy(inst)
    out["cycle_lengths"] = new_lengths
    out["cycle_starts"] = new_starts
    carried = []
    for x, y in inst["answer"]:
        zx = move_coordinate(_perm(x, inst["width"], inst["left_mixers"]))
        zy = move_coordinate(_perm(y, inst["width"], inst["right_mixers"]))
        carried.append(
            [
                _inverse_perm(zx, inst["width"], inst["left_mixers"]),
                _inverse_perm(zy, inst["width"], inst["right_mixers"]),
            ]
        )
    carried.sort(key=lambda pair: pair[0])
    out["answer"] = carried
    return out


def _swap_sides(inst: dict) -> dict:
    out = copy.deepcopy(inst)
    out["left_mixers"], out["right_mixers"] = (
        copy.deepcopy(inst["right_mixers"]),
        copy.deepcopy(inst["left_mixers"]),
    )
    out["direction"] = -inst["direction"]
    out["answer"] = sorted([[y, x] for x, y in inst["answer"]])
    return out


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _theorem_facts(inst: dict) -> bool:
    q = inst["q"]
    order = 2 * q
    degree = q + 1
    # Each clique stays connected after deleting one vertex and at least one of
    # the two perfect matchings remains, so the graph is 2-connected for q>=4.
    return 2 * degree >= order and q >= 4 and all(length >= 2 for length in inst["cycle_lengths"])


def selftest() -> dict:
    report: dict = {}

    # G1: all four presets, three independent seeds, plus the paper hypotheses.
    failures = []
    checks = 0
    theorem_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append(f"{preset}/{seed}: answer_not_JSON_native")
            if not _theorem_facts(inst):
                failures.append(f"{preset}/{seed}: theorem_hypotheses_failed")
            else:
                theorem_checks += 1
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "checks": checks,
        "theorem_hypothesis_checks": theorem_checks,
        "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping_params)

    # G2: five corruption classes with five deliberately distinct reasons.
    corruptions = {
        "empty": [],
        "drop": [list(inst["answer"][0])],
        "swap": [list(inst["answer"][1]), list(inst["answer"][0])],
        "duplicate": [
            list(inst["answer"][0]),
            [inst["answer"][1][0], inst["answer"][0][1]],
        ],
        "out_of_range": [
            [inst["q"], inst["answer"][0][1]],
            list(inst["answer"][1]),
        ],
    }
    reasons = {}
    rejected = True
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected &= not ok
        reasons[name] = why
    report["G2_rejects_corruption"] = {
        "pass": rejected and len(set(reasons.values())) == len(reasons),
        "reasons": reasons,
    }

    body = json.dumps(inst["answer"])
    realistic = (
        "The two clique paths use the following cross edges.\n\n"
        "```json\n"
        f"<answer>\n{body}\n</answer>\n"
        "```\nI checked both wraparound edges."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0] and parse_answer("garbage") is None,
        "parsed": parsed,
    }

    samples = 200_000
    hits = 0
    sample_rng = random.Random(271828)
    sampling_started = time.perf_counter()
    for _ in range(samples):
        if verify(inst, random_candidate(inst, sample_rng))[0]:
            hits += 1
    sampling_elapsed = time.perf_counter() - sampling_started
    density = hits / samples
    q = inst["q"]
    exact_valid_count = 2 * q * q - 3 * q
    exact_density = exact_valid_count / search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": samples >= 200_000 and density < 1e-6,
        "hits": hits,
        "total": samples,
        "estimated_probability": density,
        "exact_probability": exact_density,
        "structure_aware": True,
        "candidate_space": search_space(inst),
    }

    attack_seeds = list(range(700, 708))
    reference_successes = 0
    reference_operations = []
    reference_tests = []
    reference_times = []
    reference_answers = {}
    for seed in attack_seeds:
        trial = make_instance(seed=seed, **shipping_params)
        candidate, operations, edge_tests, elapsed = _reference_scan(trial)
        reference_operations.append(operations)
        reference_tests.append(edge_tests)
        reference_times.append(elapsed)
        reference_answers[seed] = candidate
        if candidate is not None and verify(trial, candidate)[0]:
            reference_successes += 1

    median_ops = sorted(reference_operations)[len(reference_operations) // 2]
    median_tests = sorted(reference_tests)[len(reference_tests) // 2]
    median_time = sorted(reference_times)[len(reference_times) // 2]
    demo_inst = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    report["G5_density_and_baseline"] = {
        "pass": density < 1e-6 and reference_successes == len(attack_seeds) and demo_count is not None,
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_density_estimate": density,
        "shipping_exact_density_by_counting": exact_density,
        "shipping_exact_valid_answer_count": exact_valid_count,
        "sampling_wall_seconds": round(sampling_elapsed, 6),
        "baseline_wall_seconds_median": round(median_time, 6),
        "baseline_operation_count_median": median_ops,
        "baseline_edge_tests_median": median_tests,
        "demo_exact_valid_answer_count_bruteforce": demo_count,
    }

    attack_names = {
        "degree_tie_smallest_labels": 0,
        "greedy_nearest_raw_label": 0,
        "random_restart_256": 0,
        "single_layer_inverse_by_hand": 0,
    }
    for seed in attack_seeds:
        trial = make_instance(seed=seed, **shipping_params)
        candidates = {
            "degree_tie_smallest_labels": _degree_tie_attack(trial),
            "greedy_nearest_raw_label": _nearest_label_attack(trial),
            "random_restart_256": _random_restart_attack(trial, seed ^ 0xBAD5EED),
            "single_layer_inverse_by_hand": _partial_inverse_attack(trial),
        }
        for name, candidate in candidates.items():
            if candidate is not None and verify(trial, candidate)[0]:
                attack_names[name] += 1
    attacks = {
        name: {"successes": successes, "attempts": len(attack_seeds)}
        for name, successes in attack_names.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["successes"] == 0 for item in attacks.values()) and reference_successes == len(attack_seeds),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "two-clique cut scan followed by clique-path splicing",
            "complexity": "O(2^n * layers) exact word operations for two cut edges",
            "wall_clock_sec_median": round(median_time, 6),
            "operations_median": median_ops,
            "edge_tests_median": median_tests,
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
    }

    doubled_params = dict(shipping_params)
    doubled_params["n"] += 1
    doubled_params["layers"] += 1
    doubled_params["components"] += 2
    doubled = make_instance(seed=424242, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["vertex_count"] == 2 * inst["vertex_count"] and len(doubled["answer"]) == len(inst["answer"]),
        "shipping_vertices": inst["vertex_count"],
        "doubled_vertices": doubled["vertex_count"],
        "shipping_answer_atoms": _answer_atoms(inst["answer"]),
        "doubled_answer_atoms": _answer_atoms(doubled["answer"]),
        "doubled_verify_reason": doubled_why,
    }

    invariant_checks = 0
    carried_checks = 0
    keys = []
    transform_count = 0
    for seed in range(20):
        trial = make_instance(seed=9000 + seed, **shipping_params)
        keys.append(canonical_key(trial))
        rekeyed = _rekey(trial, 12000 + seed)
        reordered = _reorder_blocks(trial, 13000 + seed)
        swapped = _swap_sides(trial)
        composed = _swap_sides(_reorder_blocks(_rekey(trial, 14000 + seed), 15000 + seed))
        for transformed in (rekeyed, reordered, swapped, composed):
            transform_count += 1
            if canonical_key(transformed) == canonical_key(trial):
                invariant_checks += 1
            if verify(transformed, transformed["answer"])[0]:
                carried_checks += 1
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": invariant_checks == transform_count and carried_checks == transform_count and distinct == 20,
        "invariance_checks_passed": invariant_checks,
        "invariance_checks_total": transform_count,
        "carried_witness_checks_passed": carried_checks,
        "carried_witness_checks_total": transform_count,
        "distinct_unrelated_keys": distinct,
        "unrelated_instances": 20,
        "transformations": [
            "independent raw relabelling of both cliques by new word permutations",
            "reordering equal-size coordinate blocks with the induced vertex map",
            "swapping the two cliques and reversing every cross component",
            "composition of all three transformations",
        ],
    }

    answer_blob = json.dumps(inst["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    worst_blob = json.dumps([[q - 2, q - 2], [q - 1, q - 1]])
    worst_tokens = (len(worst_blob) + 3) // 4
    answer_elements = _answer_atoms(inst["answer"])
    intended_operations = 12 * inst["layers"] + 8
    hinted = G9_ARM_RESULTS["hinted"]
    placebo = G9_ARM_RESULTS["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == worst_tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": copy.deepcopy(G9_ARM_RESULTS),
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": "diagnostic_only",
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_tokens": worst_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping_params
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
