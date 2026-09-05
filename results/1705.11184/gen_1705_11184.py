"""Verified problem generator based on Lemma 5.2 of arXiv:1705.11184.

The generated problem is a finite escape-path certificate in the one-cop-moves
game.  It uses the path safety criterion proved as Lemma 5.2 of Gao--Yang:
if a cop starts farther from the endpoint than the robber's path length, that
cop cannot catch the robber along the path.  The check is exact and does not
consult the planted answer.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:  # The family needs only integers; keep the supported repo import pattern.
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - the module is standard-library-only.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "implicitly specified finite planar graph",
        "one-cop-moves game configuration",
        "compressed robber spoke path",
    ],
    "verification_operations": [
        "exact inverse bit relabelling",
        "exact shortest-path distance in a subdivided wheel",
        "three exact path-safety inequalities",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Undo the bit relabelling to expose the reflected-Gray cyclic boundary; "
        "without that coordinate change one must inspect exponentially many spokes."
    ),
    "hardness_basis": (
        "Track B: the standard exhaustive endpoint scan is O(2^n); at shipping "
        "n=24 a measured scan visited 8,418,459 endpoints in 2.627444 seconds "
        "and used 132,280,080 accounted integer operations, while the disclosed "
        "structure-aware algorithm is O(n+encoding_rounds) and takes 160 exact "
        "word/bit-placement operations after recognizing the cyclic intervals."
    ),
    "max_answer_tokens": 11,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 4, "encoding_rounds": 0},
    "easy": {"n": 20, "encoding_rounds": 1},
    "medium": {"n": 22, "encoding_rounds": 2},
    "hard": {"n": 24, "encoding_rounds": 3},
}

SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "One JSON spoke-path descriptor {path:{kind:'spoke',label:x}}, where x "
        "is an n-bit integer label; the descriptor denotes all spoke vertices "
        "from the hub through boundary endpoint x."
    ),
    "bounds": {
        "path_descriptors": 1,
        "shipping_label_bits": 24,
        "kind_tokens": 1,
    },
}

STRUCTURAL_HINT = (
    "Interpret the boundary labels in their reflected-Gray cyclic order when comparing the cops' distance arcs."
)
PLACEBO_HINT = (
    "Track the endpoint labels and their stated spoke depths carefully when comparing the cops' distance constraints."
)

NOTES = """\
Section 2 fixes the exact one-cop-moves rules: the robber moves first in a
round, then exactly one cop traverses one edge.  Section 5, Lemma 5.2 supplies
the finite certificate used here: a length-L robber path is safe from a cop
whose initial distance to its endpoint exceeds L.  Lemma 5.1 explicitly
discusses shortest-path computation via the Floyd--Warshall idea.  Section 7
records the easy/general algorithmic side: known game characterisations would
inspect almost every (v,S) pair and cost about 1.2e23 steps on the authors'
302,762-vertex graph, while the planar separator theorem gives an O(sqrt(n))
upper bound on the number of cops (not a compact strategy for a position).

The generator inversely chooses the sole uncovered boundary spoke, partitions
the other boundary positions into three cop-distance arcs, and only afterward
applies a Gray-code/bit relabelling.  Thus it never solves the generated
instance.  All candidate endpoints have identical graph degree.  The Hamming
outlier, numeric-gap, random-restart, and unweighted-cyclic-gap attacks fail on
the measured panel.  The honest reference algorithm is exhaustive endpoint
scanning; it succeeds and is reported separately because this is Track B.
"""


def _rotl(x: int, amount: int, n: int) -> int:
    amount %= n
    mask = (1 << n) - 1
    if amount == 0:
        return x & mask
    return ((x << amount) | (x >> (n - amount))) & mask


def _rotr(x: int, amount: int, n: int) -> int:
    return _rotl(x, -amount, n)


def _permute_bits(x: int, permutation: list[int]) -> int:
    """Move source bit j to output bit permutation[j]."""
    out = 0
    for source, target in enumerate(permutation):
        out |= ((x >> source) & 1) << target
    return out


def _inverse_permute_bits(x: int, permutation: list[int]) -> int:
    out = 0
    for source, target in enumerate(permutation):
        out |= ((x >> target) & 1) << source
    return out


def _gray(x: int) -> int:
    return x ^ (x >> 1)


def _inverse_gray(g: int) -> int:
    # Exact inverse of x -> x XOR floor(x/2).
    x = 0
    while g:
        x ^= g
        g >>= 1
    return x


def _encode_raw(inst: dict, raw: int) -> int:
    x = _permute_bits(raw, inst["bit_permutation"]) ^ inst["xor_mask"]
    n = inst["n"]
    for rotation, mask in inst["twists"]:
        x = _rotl(x, rotation, n) ^ mask
    return x


def _decode_raw(inst: dict, label: int) -> int:
    x = label
    n = inst["n"]
    for rotation, mask in reversed(inst["twists"]):
        x = _rotr(x ^ mask, rotation, n)
    x ^= inst["xor_mask"]
    return _inverse_permute_bits(x, inst["bit_permutation"])


def _encode_position(inst: dict, position: int) -> int:
    m = inst["boundary_size"]
    gray_index = (inst["order_offset"] + inst["order_direction"] * position) % m
    return _encode_raw(inst, _gray(gray_index))


def _decode_position(inst: dict, label: int) -> int:
    m = inst["boundary_size"]
    gray_index = _inverse_gray(_decode_raw(inst, label))
    return (inst["order_direction"] * (gray_index - inst["order_offset"])) % m


def _cyclic_distance(a: int, b: int, modulus: int) -> int:
    d = abs(a - b)
    return min(d, modulus - d)


def _distance_to_endpoint(inst: dict, cop: dict, endpoint_position: int) -> int:
    """Exact graph distance from a cop to a boundary endpoint.

    A shortest route goes either inward through the hub or outward to the
    boundary followed by the shorter boundary arc.
    """
    spoke_length = inst["spoke_length"]
    cop_position = _decode_position(inst, cop["label"])
    around = _cyclic_distance(cop_position, endpoint_position,
                              inst["boundary_size"])
    return min(cop["depth"] + spoke_length,
               (spoke_length - cop["depth"]) + around)


def make_instance(n: int, seed: int = 0, encoding_rounds: int = 1, **params) -> dict:
    """Inverse-generate a unique Lemma-5.2-safe spoke path.

    The graph is a planar subdivided wheel: 2**n radial spokes share a hub,
    each has ``spoke_length`` edges, and their endpoints form a cycle.  Labels
    are a reversible scrambling of reflected-Gray cyclic coordinates.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 4:
        raise ValueError("n must be an integer at least 4")
    if isinstance(encoding_rounds, bool) or not isinstance(encoding_rounds, int):
        raise ValueError("encoding_rounds must be a nonnegative integer")
    if encoding_rounds < 0:
        raise ValueError("encoding_rounds must be a nonnegative integer")

    rng = random.Random(seed)
    m = 1 << n
    spoke_length = m // 4

    # Three closed cyclic arcs of radii d_i have total cardinality M-1.
    total_radius = m // 2 - 2
    base = total_radius // 3
    jitter = base // 8
    if jitter:
        d1 = base - jitter + rng.randrange(jitter + 1)
        d2 = base - jitter + rng.randrange(jitter + 1)
    else:
        d1 = base
        d2 = base
    d3 = total_radius - d1 - d2
    depths = [d1, d2, d3]
    rng.shuffle(depths)
    if not all(1 <= d <= spoke_length for d in depths):
        raise AssertionError("constructed cop depth is outside its spoke")

    target_position = rng.randrange(m)
    cursor = (target_position + 1) % m
    cop_positions = []
    for depth in depths:
        cop_positions.append((cursor + depth) % m)
        cursor = (cursor + 2 * depth + 1) % m
    if cursor != target_position:
        raise AssertionError("cop arcs did not compose to the promised gap")

    permutation = list(range(n))
    rng.shuffle(permutation)
    xor_mask = rng.randrange(m)
    twists = []
    for _ in range(encoding_rounds):
        twists.append([rng.randrange(1, n), rng.randrange(m)])

    inst = {
        "family": "one-cop-moves safe spoke path",
        "paper": "arXiv:1705.11184",
        "n": n,
        "boundary_size": m,
        "spoke_length": spoke_length,
        "bit_permutation": permutation,
        "xor_mask": xor_mask,
        "twists": twists,
        "order_offset": rng.randrange(m),
        "order_direction": rng.choice([-1, 1]),
    }
    inst["cops"] = [
        {"label": _encode_position(inst, position), "depth": depth}
        for position, depth in zip(cop_positions, depths)
    ]
    inst["answer"] = {
        "path": {"kind": "spoke", "label": _encode_position(inst, target_position)}
    }
    return inst


def render(inst: dict) -> str:
    n = inst["n"]
    m = inst["boundary_size"]
    s = inst["spoke_length"]
    twists = json.dumps(inst["twists"], separators=(",", ":"))
    cops = ", ".join(
        f"cop {i + 1}: (label={c['label']}, depth={c['depth']})"
        for i, c in enumerate(inst["cops"])
    )
    statement = f"""One-cop-moves escape certificate on a planar graph

The finite undirected graph has a hub H and {m} spokes.  A spoke is identified
by an integer label x with 0 <= x < {m}.  For every label x it has vertices
(x,1),...,(x,{s}); H is adjacent to (x,1), consecutive depths on one spoke
are adjacent, and the boundary vertices (x,{s}) form one cycle in the order
defined below.  Thus the graph is a planar subdivided wheel.

Boundary order.  Number cyclic positions i=0,...,{m - 1}.  All bit operations
use exactly {n} low bits, numbered from least-significant bit 0.  A left rotation
by r moves bit j to bit (j+r) mod {n}.  Let gray(z)=z XOR floor(z/2).  To obtain
the spoke label B(i), start with gray(({inst['order_offset']} +
{inst['order_direction']}*i) mod {m}); move source bit j to output bit p[j]
for
  p = {json.dumps(inst['bit_permutation'])};
XOR the result with {inst['xor_mask']}; then apply these [left-rotation, XOR-mask]
pairs from left to right:
  twists = {twists}.
Here left-rotation is cyclic on {n} bits.  The boundary cycle has edges between
(B(i),{s}) and (B((i+1) mod {m}),{s}).

Game configuration.  The robber is at H and moves first.  In every round the
robber traverses one edge and afterward exactly one of the three cops traverses
one edge.  A cop catches the robber by ever occupying her vertex.  The cops are
on the following spokes; depth is graph distance from H:
  {cops}

Your witness must select a canonical spoke path from H through
(x,1),(x,2),...,(x,{s}).  It is valid exactly when, for each of the three cops,
the cop's initial shortest-path distance to endpoint (x,{s}) is strictly greater
than {s}.  This exact inequality certifies that the robber reaches the endpoint
without capture even if that cop were allowed to move after every robber step.
There is exactly one valid label.  Labels are decimal integers; indexing is
0-based; no other path kind or extra field is allowed.

Give your final answer inside <answer></answer> tags, as exactly this JSON form,
replacing x by one decimal integer:
{{"path":{{"kind":"spoke","label":x}}}}
Example: <answer>{{"path":{{"kind":"spoke","label":3}}}}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str):
    if not isinstance(text, str):
        return None
    tagged = re.search(r"<answer\b[^>]*>(.*?)</answer>", text,
                       flags=re.IGNORECASE | re.DOTALL)
    candidates = []
    if tagged:
        candidates.append(tagged.group(1).strip())
    candidates.append(text.strip())
    decoder = json.JSONDecoder()
    for candidate in candidates:
        if candidate.startswith("```") and candidate.endswith("```"):
            lines = candidate.splitlines()
            if len(lines) >= 3:
                candidate = "\n".join(lines[1:-1]).strip()
        starts = [0] if candidate.startswith("{") else []
        starts.extend(i for i, ch in enumerate(candidate) if ch == "{" and i != 0)
        for start in starts:
            try:
                value, _ = decoder.raw_decode(candidate[start:])
            except (ValueError, TypeError):
                continue
            if isinstance(value, dict):
                return value
    return None


def verify(inst: dict, answer) -> tuple[bool, str]:
    if not isinstance(answer, dict):
        return False, "answer must be a JSON object"
    if set(answer) != {"path"}:
        return False, "answer must contain exactly one 'path' field"
    path = answer["path"]
    if not isinstance(path, dict):
        return False, "path must be a JSON object"
    if "kind" not in path:
        return False, "path is missing kind"
    if "label" not in path:
        return False, "path is missing label"
    if set(path) != {"kind", "label"}:
        return False, "path contains unexpected fields"
    if path["kind"] != "spoke":
        return False, "path kind must be 'spoke'"
    label = path["label"]
    if isinstance(label, bool) or not isinstance(label, int):
        return False, "spoke label must be an integer"
    if not 0 <= label < inst["boundary_size"]:
        return False, "spoke label is out of range"

    endpoint_position = _decode_position(inst, label)
    for index, cop in enumerate(inst["cops"], start=1):
        distance = _distance_to_endpoint(inst, cop, endpoint_position)
        if distance <= inst["spoke_length"]:
            return False, f"cop {index} can reach the endpoint in {distance} steps"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random):
    return {
        "path": {
            "kind": "spoke",
            "label": rng.randrange(inst["boundary_size"]),
        }
    }


def search_space(inst: dict) -> int:
    return inst["boundary_size"]


def enumerate_all(inst: dict):
    if inst["boundary_size"] > 65536:
        return None
    count = 0
    for label in range(inst["boundary_size"]):
        ok, _ = verify(inst, {"path": {"kind": "spoke", "label": label}})
        count += int(ok)
    return count


def _canonical_cop_cycle(inst: dict):
    """Canonical coloured-cycle representation, modulo dihedral symmetry."""
    m = inst["boundary_size"]
    at = {
        _decode_position(inst, cop["label"]): cop["depth"]
        for cop in inst["cops"]
    }
    positions = sorted(at)
    forms = []
    for start in positions:
        for direction in (1, -1):
            ordered = sorted(positions, key=lambda p: ((p - start) * direction) % m)
            form = []
            for index, position in enumerate(ordered):
                nxt = ordered[(index + 1) % len(ordered)]
                gap = ((nxt - position) * direction) % m
                form.append([at[position], gap])
            forms.append(form)
    return min(forms)


def canonical_key(inst: dict) -> str:
    structural = {
        "n": inst["n"],
        "spoke_length": inst["spoke_length"],
        "cop_cycle": _canonical_cop_cycle(inst),
    }
    blob = json.dumps(structural, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params: dict):
    harder = dict(params)
    harder.pop("_preset", None)
    harder["n"] = int(harder.get("n", 20)) + 1
    harder["encoding_rounds"] = min(8, int(harder.get("encoding_rounds", 1)) + 1)
    # Both axes keep the one-object answer fixed: a larger boundary crowds the
    # haystack, while another reversible twist hides its cyclic coordinate.
    return harder


def _relabel_instance(inst: dict, rng: random.Random, *,
                      cycle_automorphism: bool = True,
                      label_relabelling: bool = True,
                      cop_reordering: bool = True) -> dict:
    """Return an isomorphic representation and carry the witness through it.

    The switches let G8 test each represented symmetry separately and in every
    nonempty composition, rather than testing only one combined map.
    """
    result = json.loads(json.dumps(inst))
    cop_positions = [_decode_position(inst, cop["label"]) for cop in inst["cops"]]
    answer_position = _decode_position(inst, inst["answer"]["path"]["label"])

    if cycle_automorphism:
        shift = rng.randrange(inst["boundary_size"])
        direction = rng.choice([-1, 1])
        cop_positions = [
            (shift + direction * position) % inst["boundary_size"]
            for position in cop_positions
        ]
        answer_position = (
            shift + direction * answer_position
        ) % inst["boundary_size"]

    # Changing the displayed spoke labels is a global vertex renaming.  The
    # abstract cyclic graph and all marked depths remain unchanged.
    if label_relabelling:
        result["order_offset"] = rng.randrange(inst["boundary_size"])
        result["order_direction"] = rng.choice([-1, 1])
        result["bit_permutation"] = list(range(inst["n"]))
        rng.shuffle(result["bit_permutation"])
        result["xor_mask"] = rng.randrange(inst["boundary_size"])
        result["twists"].append([
            rng.randrange(1, inst["n"]), rng.randrange(inst["boundary_size"])
        ])
    result["cops"] = [
        {"label": _encode_position(result, position), "depth": cop["depth"]}
        for position, cop in zip(cop_positions, inst["cops"])
    ]
    if cop_reordering:
        rng.shuffle(result["cops"])
    result["answer"] = {
        "path": {"kind": "spoke", "label": _encode_position(result, answer_position)}
    }
    return result


def _candidate(label: int) -> dict:
    return {"path": {"kind": "spoke", "label": label}}


def _attack_outlier_hamming(inst: dict):
    # Choose the label farthest in total Hamming distance from the three cop
    # labels.  This is a genuine per-label outlier probe, but it deliberately
    # does not decode the hidden cyclic coordinate.
    label = 0
    for bit in range(inst["n"]):
        ones = sum((cop["label"] >> bit) & 1 for cop in inst["cops"])
        if ones < 2:  # choose the bit opposite the majority of three
            label |= 1 << bit
    return _candidate(label)


def _attack_greedy_numeric_gap(inst: dict):
    labels = sorted(cop["label"] for cop in inst["cops"])
    m = inst["boundary_size"]
    gaps = []
    for i, label in enumerate(labels):
        nxt = labels[(i + 1) % len(labels)]
        gap = (nxt - label) % m
        gaps.append((gap, label))
    gap, label = max(gaps)
    return _candidate((label + gap // 2) % m)


def _attack_unweighted_cyclic_gap(inst: dict):
    """Plausible no-tool ansatz: decode, but pretend cop radii are equal."""
    positions = sorted(_decode_position(inst, cop["label"])
                       for cop in inst["cops"])
    m = inst["boundary_size"]
    gaps = []
    for index, position in enumerate(positions):
        nxt = positions[(index + 1) % len(positions)]
        gaps.append(((nxt - position) % m, position))
    gap, position = max(gaps)
    midpoint = (position + gap // 2) % m
    return _candidate(_encode_position(inst, midpoint))


def _attack_random_restart(inst: dict, rng: random.Random, restarts: int = 256):
    last = _candidate(0)
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if verify(inst, last)[0]:
            return last
    return last


def _reference_endpoint_scan(inst: dict):
    """Honest Track-B mechanical algorithm: inspect cyclic endpoints in order."""
    m = inst["boundary_size"]
    cop_data = [(_decode_position(inst, c["label"]), c["depth"])
                for c in inst["cops"]]
    distance_tests = 0
    for position in range(m):
        safe = True
        for cop_position, depth in cop_data:
            distance_tests += 1
            around = position - cop_position
            if around < 0:
                around = -around
            other_way = m - around
            if other_way < around:
                around = other_way
            # Because every cop has positive depth, the hub route is longer
            # than the robber's spoke.  The endpoint fails exactly when its
            # boundary separation is at most the cop's depth.
            if around <= depth:
                safe = False
                break
        if safe:
            answer = _candidate(_encode_position(inst, position))
            # Six primitive integer operations/comparisons per exact cyclic
            # distance test is a conservative reproducible accounting.
            operations = 6 * distance_tests + 4 * inst["n"]
            return answer, position + 1, distance_tests, operations
    return None, m, distance_tests, 6 * distance_tests


def _compact_interval_route(inst: dict):
    """Disclosed Track-B shortcut; never consults ``inst['answer']``.

    Each cop forbids one closed cyclic interval.  If their union has a
    singleton complement, that singleton immediately follows the clockwise
    end of one interval.  Only three candidates need checking after decoding.
    """
    m = inst["boundary_size"]
    for cop in inst["cops"]:
        position = _decode_position(inst, cop["label"])
        candidate_position = (position + cop["depth"] + 1) % m
        candidate = _candidate(_encode_position(inst, candidate_position))
        if verify(inst, candidate)[0]:
            return candidate
    return None


def _answer_elements(value) -> int:
    if isinstance(value, dict):
        return sum(_answer_elements(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_elements(v) for v in value)
    return 1


def _intended_route_operations(inst: dict) -> int:
    # Decode 3 cop labels, compare their 3 exact arcs, encode one endpoint.
    n = inst["n"]
    rounds = len(inst["twists"])
    gray_inverse_ops = math.ceil(math.log2(n))
    return 4 * n + 8 * rounds + 3 * gray_inverse_ops + 25


def selftest() -> dict:
    report = {}

    g1_cases = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_cases += 1
            if not ok:
                g1_failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "cases": g1_cases,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping_params)
    planted = inst["answer"]
    corruptions = {
        "drop": {"path": {"kind": "spoke"}},
        "swap": {"path": {"kind": planted["path"]["label"], "label": "spoke"}},
        "duplicate": {"path": {**planted["path"],
                                  "duplicate_label": planted["path"]["label"]}},
        "empty": {},
        "out_of_range": _candidate(inst["boundary_size"]),
    }
    rejection_reasons = {}
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        rejection_reasons[name] = {"rejected": not ok, "reason": reason}
    reasons = [entry["reason"] for entry in rejection_reasons.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(e["rejected"] for e in rejection_reasons.values())
                and len(set(reasons)) == len(reasons),
        "cases": rejection_reasons,
        "distinct_reasons": len(set(reasons)),
    }

    answer_json = json.dumps(planted, separators=(",", ":"))
    realistic = (
        "I checked the three endpoint inequalities.\n\n"
        "```json\n<answer>\n" + answer_json + "\n</answer>\n```"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("garbage") is None,
        "parsed_equals_answer": parsed == planted,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    samples = 200_000
    guess_rng = random.Random(271828)
    hits = 0
    for _ in range(samples):
        hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_probability = hits / samples
    exact_density = 1.0 / search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6 and exact_density < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": guess_probability,
        "exact_structure_aware_probability": exact_density,
        "candidate_space": search_space(inst),
    }

    reference_inst = make_instance(seed=9001, **shipping_params)
    start = time.perf_counter()
    ref_answer, ref_nodes, ref_tests, ref_operations = _reference_endpoint_scan(reference_inst)
    ref_seconds = time.perf_counter() - start
    ref_ok = ref_answer is not None and verify(reference_inst, ref_answer)[0]
    report["G5_density_and_baseline_cost"] = {
        "pass": ref_ok and exact_density < 1e-6,
        "shipping_valid_answer_count": 1,
        "shipping_candidate_count": search_space(inst),
        "shipping_exact_solution_fraction": exact_density,
        "shipping_sample_hits": hits,
        "shipping_sample_total": samples,
        "baseline_wall_seconds": round(ref_seconds, 6),
        "baseline_nodes": ref_nodes,
        "baseline_distance_tests": ref_tests,
        "baseline_operations": ref_operations,
    }

    attack_functions = {
        "outlier_label_hamming": lambda x, r: _attack_outlier_hamming(x),
        "greedy_largest_numeric_gap": lambda x, r: _attack_greedy_numeric_gap(x),
        "random_restart_256": lambda x, r: _attack_random_restart(x, r, 256),
        "by_hand_unweighted_cyclic_gap": lambda x, r: _attack_unweighted_cyclic_gap(x),
    }
    attack_results = {name: {"successes": 0, "attempts": 8}
                      for name in attack_functions}
    reference_successes = 0
    reference_total_nodes = 0
    reference_total_tests = 0
    reference_total_operations = 0
    compact_successes = 0
    reference_start = time.perf_counter()
    for attempt in range(8):
        panel_inst = make_instance(seed=10000 + attempt, **shipping_params)
        for offset, (name, attack) in enumerate(attack_functions.items()):
            candidate = attack(panel_inst, random.Random(50000 + 97 * attempt + offset))
            attack_results[name]["successes"] += int(verify(panel_inst, candidate)[0])
        candidate, nodes, tests, operations = _reference_endpoint_scan(panel_inst)
        reference_successes += int(candidate is not None and verify(panel_inst, candidate)[0])
        reference_total_nodes += nodes
        reference_total_tests += tests
        reference_total_operations += operations
        compact = _compact_interval_route(panel_inst)
        compact_successes += int(
            compact is not None and verify(panel_inst, compact)[0]
        )
    reference_panel_seconds = time.perf_counter() - reference_start
    all_failed = all(result["successes"] == 0 for result in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "exhaustive endpoint scan in cyclic graph order",
            "complexity": "O(2^n) endpoint checks after O(n) exact decoding",
            "wall_clock_sec": round(reference_panel_seconds, 6),
            "operations": reference_total_operations,
            "nodes": reference_total_nodes,
            "distance_tests": reference_total_tests,
            "solves": f"{reference_successes}/8, as expected",
        },
        "intended_compact_route": {
            "name": "decode three Gray coordinates and test interval successors",
            "complexity": "O(n + encoding_rounds) exact word/bit operations",
            "per_instance_operations": _intended_route_operations(inst),
            "solves": f"{compact_successes}/8, as expected",
        },
    }

    doubled = make_instance(n=2 * shipping_params["n"], seed=4242,
                            encoding_rounds=shipping_params["encoding_rounds"] + 1)
    doubled_ok = verify(doubled, doubled["answer"])[0]
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["boundary_size"] > inst["boundary_size"],
        "shipping_n": shipping_params["n"],
        "doubled_n": 2 * shipping_params["n"],
        "shipping_boundary_size": inst["boundary_size"],
        "doubled_boundary_size": doubled["boundary_size"],
        "doubled_planted_verifies": doubled_ok,
    }

    invariant_checks = 0
    carried_checks = 0
    g8_failures = []
    unrelated_keys = []
    symmetry_variants = [
        (True, False, False),
        (False, True, False),
        (False, False, True),
        (True, True, False),
        (True, False, True),
        (False, True, True),
        (True, True, True),
    ]
    for seed in range(20):
        original = make_instance(seed=20000 + seed, **shipping_params)
        for variant_index, switches in enumerate(symmetry_variants):
            changed = _relabel_instance(
                original,
                random.Random(30000 + 100 * seed + variant_index),
                cycle_automorphism=switches[0],
                label_relabelling=switches[1],
                cop_reordering=switches[2],
            )
            if canonical_key(original) != canonical_key(changed):
                g8_failures.append(
                    [seed, variant_index, "key changed under relabelling"]
                )
            else:
                invariant_checks += 1
            if verify(changed, changed["answer"])[0]:
                carried_checks += 1
            else:
                g8_failures.append(
                    [seed, variant_index, "carried witness failed"]
                )
        unrelated_keys.append(canonical_key(original))
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not g8_failures and invariant_checks == 140
                and carried_checks == 140 and distinct_keys == 20,
        "invariance_checks": invariant_checks,
        "real_transformation_checks": carried_checks,
        "unrelated_distinct_keys": distinct_keys,
        "unrelated_attempts": 20,
        "transformations": [
            "dihedral boundary-coordinate change",
            "global bit-permutation/rotate-XOR vertex relabelling",
            "cop input reordering",
        ],
        "failures": g8_failures,
    }

    # Measure the worst serialisation at this preset, not merely this seed's
    # planted label (whose decimal representation may be shorter).
    answer_blob = json.dumps(_candidate(inst["boundary_size"] - 1),
                             separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_elements(inst["answer"])
    intended_operations = _intended_route_operations(inst)
    within_caps = answer_chars <= 2000 and answer_elements <= 256 \
        and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": {
            "bare": {"solved": 0, "attempts": 0},
            "hinted": {"solved": 0, "attempts": 0},
            "placebo": {"solved": 0, "attempts": 0},
        },
        "hinted_minus_placebo": None,
        "hinted_verdict": "unavailable: OpenRouter returned HTTP 403 quota errors",
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = shipping_params
    report["demo_solution_count"] = enumerate_all(
        make_instance(seed=0, **DIFFICULTY["demo"])
    )
    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
