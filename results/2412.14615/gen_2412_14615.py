"""Planted binary projective-line partition problem generator.

The family is the h-partitionability problem from Sascha Kurz,
"Additive codes attaining the Griesmer bound" (arXiv:2412.14615),
specialized to q=h=2 and multiplicity-one point multisets.

The module is deterministic for (n, seed, params), uses only the standard
library, performs no file I/O, and prints nothing when imported.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import re
from collections import Counter


DIFFICULTY = {
    "demo": {
        "n": 4,
        "bits": 5,
        "min_degree": 1,
        "guard_restarts": 0,
        "guard_nodes": 0,
    },
    "easy": {
        "n": 8,
        "bits": 7,
        "min_degree": 1,
        "guard_restarts": 0,
        "guard_nodes": 0,
    },
    "medium": {
        "n": 96,
        "bits": 12,
        "min_degree": 3,
        "guard_restarts": 16,
        "guard_nodes": 25_000,
    },
    "hard": {
        "n": 192,
        "bits": 14,
        "min_degree": 3,
        "guard_restarts": 16,
        "guard_nodes": 25_000,
    },
}

SHIPPING_DIFFICULTY = "medium"

NOTES = r"""
Definition source.  Section 2 (Preliminaries), Definition
"h-partitionable", says that a multiset M of points of PG(r-1,q) is
h-partitionable when M is exactly the sum of the point-incidence functions of
a multiset of h-dimensional subspaces.  The connection theorem in the same
subsection identifies such projective systems with additive codes.  This module uses q=2, h=2 and point
multiplicity one.  A binary projective point has a unique nonzero r-bit
representative.  Each 2-space (line) has exactly the three points a, b, a XOR
b, so a witness is an exact partition of the supplied points into XOR-zero
triples.

Hard/easy boundary.  Section 4, especially the lemma characterizing
partitionability by A^(1,h;r,q)x=b and the subsequent Smith-normal-form
discussion, separates unrestricted integral solvability from the required
nonnegative decomposition.  The paper calls finding the relevant smallest
nonnegative solution a significant hard challenge and formulates it as an ILP.
The same section gives large open partial-spread cases.  This is an exact-cover
witness problem; perfect matching in arbitrary partial Steiner triple systems
is NP-complete, although that theorem does not prove average-case hardness for
this narrower projective, planted distribution.  No polynomial-time, closed
form, or FPT search algorithm for these growing-r exact decompositions is given
in the paper.

Easy regimes deliberately avoided.  For h=1 the partition is just the points.
The uniform-partition theorem in Section 2 explicitly partitions uniform
multiples of the full projective point set, and Section 3's main theorem and
asymptotic theorem construct sufficiently large chain-type/Griesmer instances.  The generator
uses neither a uniform full space nor those chain types: it uses a sparse,
irregular set, keeps r growing with n, and asks for the actual nonnegative line
decomposition rather than unrestricted integer feasibility.

Planting and attacks.  Disjoint lines are sampled first; their union is the
instance.  Every coordinate used by a planted line is sampled uniformly from
the same ambient space, while decoy lines are the XOR-zero triples that emerge
among those same points.  Labels and point order are shuffled.  Rejection is
only on aggregate crowding and attack success, never on a per-line plant tag.
The shipping preset requires every point to lie on at least three candidate
lines.  It rejects instances solved by left-to-right greedy, rare-point/outlier
greedy, 16 randomized MRV restarts, or a 25,000-node exact-cover backtracker.
The independent G6 panel repeats those attacks (64 random restarts) on eight
fresh seeds.  G4 samples uniformly from all set partitions into unordered
triples, thereby enforcing the answer size, no-repetition, and exact-cover
shape before testing the XOR equations.
""".strip()


_ANSWER_RE = re.compile(
    r"<answer\s*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL
)


def _default_bits(n):
    point_count = 3 * n
    # Keep enough room to sample disjoint points and, asymptotically, about ten
    # candidate lines through a point.  The latter is the useful crowded window.
    room_bits = math.ceil(math.log2(4 * point_count + 1))
    crowd_bits = round(math.log2(max(2, point_count * point_count / 20)))
    return max(4, room_bits, crowd_bits)


def _gf2_rank(values):
    basis = {}
    for value in values:
        x = int(value)
        while x:
            pivot = x.bit_length() - 1
            if pivot in basis:
                x ^= basis[pivot]
            else:
                basis[pivot] = x
                break
    return len(basis)


def _candidate_lines(points):
    """All projective lines fully contained in points, as 1-based triples."""
    location = {value: i for i, value in enumerate(points)}
    result = []
    for i, a in enumerate(points):
        for j in range(i + 1, len(points)):
            k = location.get(a ^ points[j], -1)
            if k > j:
                result.append((i + 1, j + 1, k + 1))
    return result


def _candidate_data(inst):
    lines = _candidate_lines(inst["points"])
    incident = [[] for _ in inst["points"]]
    for line in lines:
        for point in line:
            incident[point - 1].append(line)
    return lines, incident


def _greedy_attack(inst, strategy, rng=None):
    """Return a greedy candidate partition or None, without using the plant."""
    lines, incident = _candidate_data(inst)
    degrees = [len(x) for x in incident]
    remaining = set(range(1, len(inst["points"]) + 1))
    chosen = []
    while remaining:
        available = {}
        if strategy == "left":
            point = min(remaining)
            available[point] = [
                line for line in incident[point - 1]
                if all(x in remaining for x in line)
            ]
        else:
            best_count = None
            best_points = []
            for point in remaining:
                choices = [
                    line for line in incident[point - 1]
                    if all(x in remaining for x in line)
                ]
                available[point] = choices
                count = len(choices)
                if best_count is None or count < best_count:
                    best_count, best_points = count, [point]
                elif count == best_count:
                    best_points.append(point)
            if strategy == "random":
                point = rng.choice(best_points)
            else:
                point = min(best_points, key=lambda x: (degrees[x - 1], x))

        choices = available[point]
        if not choices:
            return None
        if strategy == "left":
            line = min(choices)
        elif strategy == "random":
            line = rng.choice(choices)
        else:  # per-point outlier/rarity score
            line = min(
                choices,
                key=lambda edge: (
                    sum(degrees[x - 1] for x in edge),
                    max(degrees[x - 1] for x in edge),
                    edge,
                ),
            )
        chosen.append(list(line))
        remaining.difference_update(line)
    return chosen


def _global_score_attack(inst):
    """Take globally low-degree lines first; a cheap planting-signature probe."""
    lines, incident = _candidate_data(inst)
    degrees = [len(x) for x in incident]
    ordered = sorted(
        lines,
        key=lambda edge: (
            sum(degrees[x - 1] for x in edge),
            max(degrees[x - 1] for x in edge),
            edge,
        ),
    )
    used = set()
    chosen = []
    for line in ordered:
        if not any(x in used for x in line):
            chosen.append(list(line))
            used.update(line)
    if len(used) != len(inst["points"]):
        return None
    return chosen


def _random_restart_attack(inst, rng, restarts):
    for _ in range(restarts):
        candidate = _greedy_attack(inst, "random", rng)
        if candidate is not None and verify(inst, candidate)[0]:
            return candidate
    return None


def _bounded_backtracking(inst, node_budget):
    """MRV exact-cover search; return (answer|None, nodes, exhausted_budget)."""
    lines, incident = _candidate_data(inst)
    masks = []
    incident_ids = [[] for _ in inst["points"]]
    for edge_id, line in enumerate(lines):
        mask = 0
        for point in line:
            mask |= 1 << (point - 1)
            incident_ids[point - 1].append(edge_id)
        masks.append(mask)

    nodes = 0
    exhausted = False

    def visit(remaining):
        nonlocal nodes, exhausted
        nodes += 1
        if nodes > node_budget:
            exhausted = True
            return None
        if remaining == 0:
            return []

        scan = remaining
        options = None
        while scan:
            bit = scan & -scan
            point = bit.bit_length() - 1
            scan ^= bit
            here = [
                edge_id for edge_id in incident_ids[point]
                if masks[edge_id] & remaining == masks[edge_id]
            ]
            if not here:
                return None
            if options is None or len(here) < len(options):
                options = here
                if len(options) == 1:
                    break

        for edge_id in options:
            suffix = visit(remaining ^ masks[edge_id])
            if suffix is not None:
                return [list(lines[edge_id])] + suffix
            if exhausted:
                return None
        return None

    answer = visit((1 << len(inst["points"])) - 1)
    return answer, nodes, exhausted


def _build_instance(points, bits, n, answer=None, generation=None):
    inst = {
        "family": "binary_projective_line_partition",
        "bits": int(bits),
        "n": int(n),
        "points": list(map(int, points)),
    }
    if generation is not None:
        inst["generation"] = dict(generation)
    if answer is not None:
        inst["answer"] = [sorted(map(int, block)) for block in answer]
        inst["answer"].sort()
    return inst


def make_instance(n, seed=0, **params):
    """Sample disjoint binary projective lines first, then expose their union.

    ``n`` is the number of lines in the required partition, so the instance has
    exactly ``3*n`` points.  Larger n grows both the witness and the exact-cover
    search.  ``bits`` controls ambient dimension/crowding.  The guard parameters
    rejection-sample away instances caught by the named cheap attacks.
    """
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
        raise ValueError("n must be an integer at least 3")
    allowed = {"bits", "min_degree", "guard_restarts", "guard_nodes"}
    unknown = set(params) - allowed
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))

    bits = params.get("bits", _default_bits(n))
    min_degree = params.get("min_degree", 2 if n >= 16 else 1)
    guard_restarts = params.get("guard_restarts", 0)
    guard_nodes = params.get("guard_nodes", 0)
    for name, value, minimum in (
        ("bits", bits, 3),
        ("min_degree", min_degree, 1),
        ("guard_restarts", guard_restarts, 0),
        ("guard_nodes", guard_nodes, 0),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ValueError(f"{name} must be an integer at least {minimum}")
    point_count = 3 * n
    if (1 << bits) - 1 < 2 * point_count:
        raise ValueError("bits leaves too little room for unbiased disjoint-line sampling")

    rng = random.Random(seed)
    ambient_max = (1 << bits) - 1
    for attempt in range(1, 257):
        used = set()
        planted_vectors = []
        failed = False
        for _ in range(n):
            for _draw in range(50_000):
                a = rng.randint(1, ambient_max)
                b = rng.randint(1, ambient_max)
                c = a ^ b
                if a != b and not ({a, b, c} & used):
                    used.update((a, b, c))
                    planted_vectors.append((a, b, c))
                    break
            else:
                failed = True
                break
        if failed:
            continue

        points = list(used)
        rng.shuffle(points)
        if _gf2_rank(points) != bits:
            continue
        index = {value: i + 1 for i, value in enumerate(points)}
        answer = [[index[x] for x in line] for line in planted_vectors]
        trial = _build_instance(
            points,
            bits,
            n,
            answer=answer,
            generation={
                "min_degree": min_degree,
                "guard_restarts": guard_restarts,
                "guard_nodes": guard_nodes,
                "attempt": attempt,
            },
        )
        lines, incident = _candidate_data(trial)
        degrees = [len(row) for row in incident]
        if min(degrees) < min_degree:
            continue
        median = sorted(degrees)[len(degrees) // 2]
        if max(degrees) > max(6, 3 * median):
            continue

        if guard_restarts or guard_nodes:
            if _greedy_attack(trial, "left") is not None:
                continue
            if _greedy_attack(trial, "outlier") is not None:
                continue
            if _global_score_attack(trial) is not None:
                continue
        if guard_restarts:
            attack_rng = random.Random(rng.getrandbits(64))
            if _random_restart_attack(trial, attack_rng, guard_restarts) is not None:
                continue
        if guard_nodes:
            found, _nodes, _exhausted = _bounded_backtracking(trial, guard_nodes)
            if found is not None:
                continue
        # "lines" is intentionally not stored: it is derived public structure,
        # while retaining only points keeps the instance definition minimal.
        return trial
    raise RuntimeError("could not sample a crowded attack-resistant instance")


def render(inst):
    """Return the complete, self-contained solver-facing statement."""
    bits = inst["bits"]
    points = inst["points"]
    lines = [
        "BINARY PROJECTIVE-LINE PARTITION WITNESS PROBLEM",
        "",
        f"Work with {bits}-bit vectors over GF(2). Addition in GF(2) is",
        "coordinate-wise XOR. In the binary projective space, every nonzero",
        "vector below represents one point (there is no nontrivial scalar",
        "rescaling to identify). A projective line is exactly a set of three",
        "distinct points {a,b,c} whose vectors satisfy a XOR b XOR c = 0;",
        "equivalently c = a XOR b.",
        "",
        f"The instance contains {len(points)} distinct nonzero points, labelled",
        f"1 through {len(points)}. Partition all of them into exactly {inst['n']}",
        "projective lines. Every label must occur exactly once. A block is an",
        "unordered triple, the blocks are unordered, and repeats are forbidden.",
        "All bounds are inclusive and labels are 1-indexed.",
        "",
        "POINTS (label: fixed-width vector)",
    ]
    width = len(str(len(points)))
    for label, value in enumerate(points, 1):
        lines.append(f"{label:0{width}d}: {value:0{bits}b}")
    lines.extend([
        "",
        f"Output exactly {inst['n']} triples. Separate labels within a triple by",
        "commas and separate triples by semicolons. Do not use brackets. Order",
        "inside a triple and the order of triples do not matter.",
        "",
        "Give your final answer inside <answer></answer> tags, as",
        "semicolon-separated comma-separated triples of decimal point labels.",
        "Example: <answer>1, 2, 3; 4, 5, 6</answer>",
        "Output nothing else inside the tags.",
    ])
    return "\n".join(lines)


def parse_answer(text):
    """Parse the final tagged list of triples; return None on any malformed text."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if not body:
        return None
    triple_pattern = r"[0-9]+\s*,\s*[0-9]+\s*,\s*[0-9]+"
    if not re.fullmatch(
        rf"{triple_pattern}(?:\s*;\s*{triple_pattern})*", body
    ):
        return None
    try:
        return [
            [int(piece.strip()) for piece in block.split(",")]
            for block in body.split(";")
        ]
    except (TypeError, ValueError):
        return None


def verify(inst, answer):
    """Accept any exact projective-line partition; never inspect the plant."""
    if not isinstance(answer, list):
        return False, "answer must be a list of triples"
    if not answer:
        return False, "answer must contain at least one block"
    if len(answer) != inst["n"]:
        return False, f"expected exactly {inst['n']} blocks, got {len(answer)}"

    point_count = len(inst["points"])
    seen = set()
    for block_number, block in enumerate(answer, 1):
        if not isinstance(block, (list, tuple)):
            return False, f"block B{block_number} must be a triple"
        if len(block) != 3:
            return False, f"block B{block_number} has size {len(block)}, not 3"
        for label in block:
            if isinstance(label, bool) or not isinstance(label, int):
                return False, f"block B{block_number} contains a non-integer label"
            if not 1 <= label <= point_count:
                return False, f"point label {label} is outside 1..{point_count}"
        if len(set(block)) != 3:
            return False, f"block B{block_number} repeats a point label"
        duplicate = next((label for label in block if label in seen), None)
        if duplicate is not None:
            return False, f"point label {duplicate} occurs in more than one block"
        seen.update(block)

        a, b, c = (inst["points"][label - 1] for label in block)
        if a ^ b ^ c:
            return False, f"block B{block_number} is not a projective line"

    if len(seen) != point_count:
        missing = min(set(range(1, point_count + 1)) - seen)
        return False, f"point label {missing} is not covered"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample a set partition into unordered triples.

    This already enforces the exact number and size of blocks, label range,
    no repetition, and exact coverage.  Only the XOR-line equations remain.
    """
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    labels = list(range(1, len(inst["points"]) + 1))
    rng.shuffle(labels)
    return [labels[i:i + 3] for i in range(0, len(labels), 3)]


def search_space(inst):
    """Number of partitions of 3n labelled points into n unordered triples."""
    n = inst["n"]
    return math.factorial(3 * n) // (math.factorial(n) * (math.factorial(3) ** n))


def enumerate_all(inst):
    """Count all line partitions exactly when a capped DFS is feasible."""
    point_count = len(inst["points"])
    if point_count > 24:
        return None
    lines, _incident = _candidate_data(inst)
    masks = []
    by_point = [[] for _ in range(point_count)]
    for line in lines:
        mask = sum(1 << (point - 1) for point in line)
        masks.append(mask)
        for point in line:
            by_point[point - 1].append(mask)

    nodes = 0
    cap = 2_000_000

    def count(remaining):
        nonlocal nodes
        nodes += 1
        if nodes > cap:
            raise OverflowError
        if remaining == 0:
            return 1
        scan = remaining
        choices = None
        while scan:
            bit = scan & -scan
            point = bit.bit_length() - 1
            scan ^= bit
            here = [mask for mask in by_point[point] if mask & remaining == mask]
            if not here:
                return 0
            if choices is None or len(here) < len(choices):
                choices = here
                if len(choices) == 1:
                    break
        return sum(count(remaining ^ mask) for mask in choices)

    try:
        return count((1 << point_count) - 1)
    except OverflowError:
        return None


def _wl_invariant(inst):
    """A relabelling-invariant color-refinement fingerprint of line incidence."""
    lines, incident = _candidate_data(inst)
    point_count = len(inst["points"])
    line_count = len(lines)
    point_to_edges = [[] for _ in range(point_count)]
    edge_to_points = []
    for edge_index, line in enumerate(lines):
        edge_to_points.append([point - 1 for point in line])
        for point in line:
            point_to_edges[point - 1].append(edge_index)

    colors = [0] * point_count + [1] * line_count
    history = []
    for _ in range(12):
        signatures = []
        for point in range(point_count):
            signatures.append((
                0,
                colors[point],
                tuple(sorted(colors[point_count + edge]
                             for edge in point_to_edges[point])),
            ))
        for edge in range(line_count):
            signatures.append((
                1,
                colors[point_count + edge],
                tuple(sorted(colors[point] for point in edge_to_points[edge])),
            ))
        unique = {signature: number for number, signature in enumerate(sorted(set(signatures)))}
        new_colors = [unique[signature] for signature in signatures]
        history.append(sorted(Counter(new_colors).items()))
        if new_colors == colors:
            colors = new_colors
            break
        colors = new_colors

    point_profiles = sorted(
        (
            colors[point],
            len(point_to_edges[point]),
            tuple(sorted(colors[point_count + edge]
                         for edge in point_to_edges[point])),
        )
        for point in range(point_count)
    )
    edge_profiles = sorted(
        (
            colors[point_count + edge],
            tuple(sorted(colors[point] for point in edge_to_points[edge])),
        )
        for edge in range(line_count)
    )
    return {
        "bits": inst["bits"],
        "points": point_count,
        "lines": line_count,
        "history": history,
        "point_profiles": point_profiles,
        "edge_profiles": edge_profiles,
    }


def canonical_key(inst):
    """Invariant under point reordering and every invertible GF(2) basis map.

    Exact isomorphism of the induced line hypergraph is not attempted.  The key
    is a strong Weisfeiler--Leman incidence invariant; possible collisions are
    documented in README.md.
    """
    payload = json.dumps(
        _wl_invariant(inst), sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    return "line-wl-v1:" + hashlib.sha256(payload).hexdigest()


def escalate(params):
    """Double the partition width while preserving the crowded search window."""
    if not isinstance(params, dict) or "n" not in params:
        return None
    n = int(params["n"]) * 2
    if n > 384:
        return None
    return {
        "n": n,
        "bits": _default_bits(n),
        "min_degree": max(3, int(params.get("min_degree", 3))),
        "guard_restarts": max(16, int(params.get("guard_restarts", 0))),
        "guard_nodes": max(25_000, int(params.get("guard_nodes", 0))),
    }


def _format_answer(answer):
    return "; ".join(", ".join(map(str, block)) for block in answer)


def _invertible_images(bits, rng):
    """Images of the standard basis under a random elementary GL map."""
    images = [1 << i for i in range(bits)]
    rng.shuffle(images)
    for _ in range(4 * bits):
        i, j = rng.sample(range(bits), 2)
        images[i] ^= images[j]
    return images


def _linear_image(value, images):
    result = 0
    bit = 0
    while value:
        if value & 1:
            result ^= images[bit]
        value >>= 1
        bit += 1
    return result


def _transform_instance(inst, rng, reorder, basis_change):
    images = _invertible_images(inst["bits"], rng) if basis_change else None
    transformed = [
        _linear_image(value, images) if images is not None else value
        for value in inst["points"]
    ]
    order = list(range(len(transformed)))
    if reorder:
        rng.shuffle(order)
    inverse = [0] * len(order)
    for new_index, old_index in enumerate(order, 1):
        inverse[old_index] = new_index
    points = [transformed[old_index] for old_index in order]
    answer = [
        [inverse[label - 1] for label in block]
        for block in inst["answer"]
    ]
    return _build_instance(points, inst["bits"], inst["n"], answer=answer)


def selftest():
    """Run mandatory gates and return their measured, JSON-serializable report."""
    report = {}

    # G1: every named preset, three seeds each.
    g1_failures = []
    g1_checked = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_checked += 1
            if not ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "checked": g1_checked,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=111, **shipping)
    plant = [block[:] for block in inst["answer"]]

    # G2: five different malformed/corrupted witnesses and distinct reasons.
    corruptions = {}
    corruptions["drop"] = plant[:-1]
    duplicate = [block[:] for block in plant]
    duplicate[0][1] = duplicate[0][0]
    corruptions["duplicate"] = duplicate
    corruptions["empty"] = []
    out_of_range = [block[:] for block in plant]
    out_of_range[0][0] = len(inst["points"]) + 1
    corruptions["out_of_range"] = out_of_range

    swapped = None
    for i in range(len(plant)):
        for j in range(i + 1, len(plant)):
            for a in range(3):
                for b in range(3):
                    trial = [block[:] for block in plant]
                    trial[i][a], trial[j][b] = trial[j][b], trial[i][a]
                    if not verify(inst, trial)[0]:
                        swapped = trial
                        break
                if swapped is not None:
                    break
            if swapped is not None:
                break
        if swapped is not None:
            break
    corruptions["swap"] = swapped
    reasons = {}
    rejected = 0
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        reasons[name] = reason
        if not ok:
            rejected += 1
    report["G2_rejects_corruption"] = {
        "pass": rejected == 5 and len(set(reasons.values())) == 5,
        "rejected": rejected,
        "total": 5,
        "distinct_reasons": len(set(reasons.values())) == 5,
        "reasons": reasons,
    }

    # G3: realistic prose + fence, with the exact public wire representation.
    response = (
        "I checked every XOR.\n```text\n<answer>"
        + _format_answer(plant)
        + "</answer>\n```\n"
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == plant and verify(inst, parsed)[0],
        "parsed_blocks": len(parsed) if parsed is not None else None,
    }

    # G4: uniform over exact set partitions into triples, not arbitrary noise.
    guess_inst = make_instance(seed=222, **shipping)
    guess_rng = random.Random(0x241214615)
    total = 200_000
    hits = 0
    for _ in range(total):
        if verify(guess_inst, random_candidate(guess_inst, guess_rng))[0]:
            hits += 1
    probability = hits / total
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": total,
        "empirical_probability": probability,
        "prior": "uniform over all partitions of all labels into unordered triples",
        "naive_space": search_space(guess_inst),
    }

    # G5: exact enumeration on a deliberately small independent instance.
    small = make_instance(
        n=5, seed=17, bits=6, min_degree=1, guard_restarts=0, guard_nodes=0
    )
    solutions = enumerate_all(small)
    small_space = search_space(small)
    fraction = None if solutions is None else solutions / small_space
    report["G5_sparse"] = {
        "pass": solutions is not None and fraction < 1e-5,
        "points": len(small["points"]),
        "solutions": solutions,
        "naive_space": small_space,
        "solution_fraction": fraction,
    }

    # G6: attacks know the public construction but never inspect inst['answer'].
    attacks = {
        "outlier_rare_point": {"solved": 0, "attempts": 8, "seeds_solved": []},
        "left_to_right": {"solved": 0, "attempts": 8, "seeds_solved": []},
        "global_line_score": {"solved": 0, "attempts": 8, "seeds_solved": []},
        "random_restart_64": {"solved": 0, "attempts": 8, "seeds_solved": []},
        "backtracking_25000_nodes": {"solved": 0, "attempts": 8, "seeds_solved": []},
    }
    degree_ranges = []
    backtrack_nodes = []
    for seed in range(300, 308):
        attack_inst = make_instance(seed=seed, **shipping)
        _all_lines, incident = _candidate_data(attack_inst)
        degrees = [len(row) for row in incident]
        degree_ranges.append([min(degrees), max(degrees)])
        candidates = {
            "outlier_rare_point": _greedy_attack(attack_inst, "outlier"),
            "left_to_right": _greedy_attack(attack_inst, "left"),
            "global_line_score": _global_score_attack(attack_inst),
            "random_restart_64": _random_restart_attack(
                attack_inst, random.Random(seed ^ 0xA5A5A5A5), 64
            ),
        }
        bounded, nodes, exhausted = _bounded_backtracking(attack_inst, 25_000)
        backtrack_nodes.append({"seed": seed, "nodes": nodes, "budget_exhausted": exhausted})
        candidates["backtracking_25000_nodes"] = bounded
        for name, candidate in candidates.items():
            if candidate is not None and verify(attack_inst, candidate)[0]:
                attacks[name]["solved"] += 1
                attacks[name]["seeds_solved"].append(seed)
    report["G6_adversary_panel"] = {
        "pass": all(data["solved"] == 0 for data in attacks.values()),
        "seeds": 8,
        "attacks": attacks,
        "candidate_degree_ranges": degree_ranges,
        "backtracking": backtrack_nodes,
    }

    # G7: double the number of planted lines while preserving crowding.
    doubled_params = escalate(dict(shipping))
    doubled = make_instance(seed=707, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * shipping["n"],
        "base_lines": shipping["n"],
        "base_points": 3 * shipping["n"],
        "doubled_lines": doubled["n"],
        "doubled_points": len(doubled["points"]),
        "doubled_bits": doubled["bits"],
        "verify_reason": doubled_reason,
    }

    # G8: point-order relabelling, GL basis maps, and their composition.
    invariant_checks = 0
    real_checks = 0
    invariant_failures = []
    unrelated_keys = []
    for seed in range(500, 520):
        base = make_instance(seed=seed, **shipping)
        key = canonical_key(base)
        unrelated_keys.append(key)
        transform_rng = random.Random(seed ^ 0x8C4A11)
        variants = [
            ("reorder", _transform_instance(base, transform_rng, True, False)),
            ("basis", _transform_instance(base, transform_rng, False, True)),
            ("composed", _transform_instance(base, transform_rng, True, True)),
        ]
        for name, variant in variants:
            invariant_checks += 1
            if canonical_key(variant) != key:
                invariant_failures.append({"seed": seed, "transform": name})
        # The carried answer proves that the composed relabelling is genuine.
        real_ok, _real_reason = verify(variants[-1][1], variants[-1][1]["answer"])
        real_checks += int(real_ok)
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": (
            not invariant_failures
            and real_checks == 20
            and distinct == len(unrelated_keys)
        ),
        "invariance_checks": invariant_checks,
        "real_transform_checks": real_checks,
        "real_transform_total": 20,
        "distinct_unrelated": distinct,
        "unrelated_total": len(unrelated_keys),
        "failures": invariant_failures,
        "transformations": [
            "arbitrary point-list permutation with carried labels",
            "invertible GF(2) change of basis",
            "composition of both",
        ],
        "method": "incidence-hypergraph color-refinement invariant",
    }

    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["all_passed"] = all(
        value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
