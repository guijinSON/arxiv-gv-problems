"""Rejected experimental problem generator for arXiv:2105.05784.

The native object is a labelled, tree-shaped 3D polycube in the paper's
single-step tilt-assembly model.  A submitted pair of vectors is a succinct
program for a complete particle-addition order; the verifier expands that
program and checks the prescribed unit moves exactly.

Generation is by composition of identities.  A monotone lattice path has a
known construction order, an injective affine tag identifies that order, and
invertible public shear operations carry the affine certificate to the tags
shown on the cubes.  The emitted instance is never solved during generation.

This is retained evidence, not a shippable family: the affine tags and shear
program are a benchmark-convenience encoding absent from the source paper, so
the apparent Track-B gap measures the added decoder rather than native STAP.
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
    "native_domain": "algebra",
    "object_regime": "integer_lattice",
    "computational_core": "linear_algebra",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "labelled 3D polycube on the integer grid",
        "anchored seed cube and single-particle construction paths",
        "affine finite-field program for a construction sequence",
    ],
    "verification_operations": [
        "exact integer-grid face adjacency",
        "exact modular shear and affine evaluation",
        "exact replay of unit single-particle moves",
        "connectivity-preserving target comparison",
    ],
    "domain_essentiality": "discretised_analogue",
    "reduction_kind": "convenience",
    "reduction": (
        "Benchmark-convenience affine tags and shear program; this encoding is "
        "not licensed by any section of arXiv:2105.05784."
    ),
    "reduction_source": "benchmark_convenience",
    "intuition_type": "invariant",
    "intuition_description": (
        "Coordinate sum is the hidden construction rank of the monotone "
        "polycube path; without that invariant, a solver must reconstruct the "
        "tree and execute the paper's removal algorithm over every cube."
    ),
    "hardness_basis": (
        "Rejected Track-B candidate: Section 5.1's tree-shape algorithm decides constructibility "
        "and obtains an order in O(n), followed here by O(nr+tr) exact tag "
        "processing; at the hard preset (n=540,r=12,t=120) the implemented "
        "reference uses 11,586 primitive operations per instance, while the "
        "coordinate-sum shortcut needs 252 exact field operations after the "
        "insight and remains error-prone without tools."
    ),
    "max_answer_tokens": 70,
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


DIFFICULTY = {
    "demo": {"n": 7, "modulus": 17, "tag_dim": 2, "shears": 2},
    "easy": {"n": 240, "modulus": 1_000_003, "tag_dim": 12, "shears": 100},
    "medium": {"n": 360, "modulus": 10_000_019, "tag_dim": 12, "shears": 110},
    "hard": {"n": 540, "modulus": 100_000_007, "tag_dim": 12, "shears": 120},
}
SHIPPING_DIFFICULTY = "hard"


STRUCTURAL_HINT = (
    "The coordinate sum is the construction rank, and the tag axes are related "
    "to the certificate axes by reversible shears."
)
PLACEBO_HINT = (
    "The coordinate and tag lists reward careful attention to the stated "
    "indexing and modular conventions."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "An object with slope and offset vectors of equal published length r; "
        "their 2r entries are pairwise-distinct residues in 0..q-1.  The two "
        "vectors define an affine rank-to-tag map after the published shears."
    ),
    "bounds": {
        "vectors": 2,
        "vector_length": "tag_dim",
        "coefficient_min": 0,
        "coefficient_max": "modulus-1",
        "all_coefficients_pairwise_distinct": True,
    },
}


NOTES = r"""
Paper grounding and Step 0.  Section 2 defines a polycube as a finite connected
subset of Z^3, fixes the 2n-by-2n-by-2n workspace, the inlet (0,0,0), the
anchored seed (n,n,n), and a construction step in which the one newly added
particle takes unit moves while the neighborhood of its current position is
free and sticks on first face contact.  Theorem 2 quoted in Section 2 states
that construction and connectivity-preserving deconstruction are reverses.
Section 3, Theorem 7, proves unrestricted 3D-STAP NP-complete and
gives the O(n^2)-length witness bound.  That worst-case theorem is deliberately
not used as an average-case claim here.

The easy-regime result controls the track choice.  Section 5.1, Theorem 13,
proves that a tree-shaped polyomino is decidable in O(n) by repeatedly removing
accessible leaves, and Corollary 14 extends it to tree-shaped polycubes.  The present
monotone paths are inside that regime, so this is explicitly Track B.  Section
5.2's Theorems 20 and 24 also make 2-scaled non-degenerate polyominoes and
3-scaled non-degenerate polycubes constructible; the generator uses neither
scaled-shape theorem.

Construction and certificate.  Starting at the anchored seed, a balanced
random word in the three positive coordinate directions creates a monotone
induced grid path.  Its prefix is always connected and each next cube is
reachable by the public canonical route above the target bounding box.  A
base affine tag i*slope+offset over GF(q) is injective because slope is nonzero
and n<q.  Public elementary updates v[d] <- v[d]+v[s] are invertible and are
applied to both vectors before tags are attached.  This composes a known legal
construction order with reversible identities; generation performs no search.

Hardness and attacks.  The reference method reconstructs the grid path from
the seed using face adjacency, reads the first two tags, and undoes the shear
program.  It is reported as a successful O(nr+tr) Track-B reference, never as a
failed attack.  The failing panel tests residue outliers, the tempting public
record order, 256 structure-aware random certificates, and the plausible but
wrong forward-shear ansatz.  Cubes and tags are shuffled uniformly; there is
no separate planted population.  Difficulty grows mainly by adding shuffled
cubes and shears while the 24-integer answer remains fixed outside the demo.
""".strip()


G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "not_run",
}


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"```(?:json|text|python)?\s*(.*?)```", re.I | re.S)
_DIRS = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8
_ENUMERATION_CAP = 200_000
_TAG_CACHE = {}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate(n, modulus, tag_dim, shears):
    for name, value in (
        ("n", n), ("modulus", modulus), ("tag_dim", tag_dim), ("shears", shears)
    ):
        if not _is_int(value):
            raise ValueError(f"{name} must be an integer")
    if not 4 <= n <= 10_000:
        raise ValueError("n must lie in 4..10000")
    if not n < modulus <= 2_147_483_647:
        raise ValueError("modulus must be greater than n and at most 2147483647")
    if not 2 <= tag_dim <= 64:
        raise ValueError("tag_dim must lie in 2..64")
    if 2 * tag_dim > modulus:
        raise ValueError("modulus is too small for pairwise-distinct coefficients")
    if not 0 <= shears <= 140:
        raise ValueError("shears must lie in 0..140")


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _neighbors(point):
    x, y, z = point
    for dx, dy, dz in _DIRS:
        yield (x + dx, y + dy, z + dz)


def _apply_shears(vector, shear_program, modulus):
    result = list(vector)
    for dst, src in shear_program:
        result[dst] = (result[dst] + result[src]) % modulus
    return result


def _undo_shears(vector, shear_program, modulus):
    result = list(vector)
    for dst, src in reversed(shear_program):
        result[dst] = (result[dst] - result[src]) % modulus
    return result


def _balanced_axis_word(n, rng):
    steps = n - 1
    counts = [steps // 3] * 3
    for axis in rng.sample(range(3), steps % 3):
        counts[axis] += 1
    word = [axis for axis, count in enumerate(counts) for _ in range(count)]
    rng.shuffle(word)
    return word


def _coordinates_from_word(n, word):
    point = (n, n, n)
    coordinates = [point]
    for axis in word:
        delta = [0, 0, 0]
        delta[axis] = 1
        point = _add(point, tuple(delta))
        coordinates.append(point)
    return coordinates


def make_instance(n, seed=0, modulus=1_000_003, tag_dim=12, shears=100, **params):
    """Compose a known monotone construction with an invertible affine tag map."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    _validate(n, modulus, tag_dim, shears)
    rng = random.Random(seed)

    axis_word = _balanced_axis_word(n, rng)
    coordinates = _coordinates_from_word(n, axis_word)

    # Sampling without replacement makes the bounded certificate language exact.
    coefficients = rng.sample(range(modulus), 2 * tag_dim)
    base_slope = coefficients[:tag_dim]
    base_offset = coefficients[tag_dim:]

    shear_program = []
    previous = None
    for _ in range(shears):
        while True:
            dst = rng.randrange(tag_dim)
            src = rng.randrange(tag_dim - 1)
            if src >= dst:
                src += 1
            pair = (dst, src)
            if pair != previous:
                break
        shear_program.append([dst, src])
        previous = pair

    shown_slope = _apply_shears(base_slope, shear_program, modulus)
    shown_offset = _apply_shears(base_offset, shear_program, modulus)
    if not any(shown_slope):
        raise AssertionError("an invertible shear mapped a nonzero vector to zero")

    markers = rng.sample(range(10_000_000, 99_999_999), tag_dim)
    records = []
    for rank, coordinate in enumerate(coordinates):
        tag = [
            (rank * shown_slope[j] + shown_offset[j]) % modulus
            for j in range(tag_dim)
        ]
        records.append({"coord": list(coordinate), "tag": tag})
    rng.shuffle(records)

    return {
        "paper": "arXiv:2105.05784",
        "family": "succinct construction sequence for a monotone tree polycube",
        "n": n,
        "workspace_side": 2 * n,
        "inlet": [0, 0, 0],
        "seed_coord": [n, n, n],
        "modulus": modulus,
        "tag_dim": tag_dim,
        "tag_axis_markers": markers,
        "shear_program": shear_program,
        "records": records,
        "answer": {"slope": base_slope, "offset": base_offset},
    }


def render(inst):
    n = inst["n"]
    q = inst["modulus"]
    r = inst["tag_dim"]
    high = 2 * n - 1
    lines = [
        "SINGLE-STEP TILT ASSEMBLY: COMPRESSED CONSTRUCTION CERTIFICATE",
        "",
        "A polycube is a finite face-connected set of unit cubes centered at",
        "integer 3D grid positions. Two positions are in face contact exactly when",
        "their Manhattan distance is one. The workspace has coordinates",
        f"0..{high} in each axis. One seed cube is anchored at ({n},{n},{n}).",
        "",
        "A construction step puts one new cube at the inlet (0,0,0). The new cube",
        "alone moves. Each move changes exactly one coordinate by 1 and stays in",
        "the workspace. It may move from p only while all six positions at",
        "Manhattan distance one from p are empty. On first entering face contact",
        "with the existing assembly it sticks and that construction step ends.",
        "Cubes already attached never move.",
        "",
        "The target consists of the shuffled coordinate/tag records below. Tags",
        f"are ordered vectors of length r={r} over the prime field modulo q={q}.",
        "Tag-axis order matters. The marker line gives a permanent name for each",
        "tag axis; it is metadata for relabeling, not an arithmetic operand.",
        "",
        "TAG-AXIS MARKERS:",
        " ".join(map(str, inst["tag_axis_markers"])),
        "",
        f"TARGET CUBES ({n} records, deliberately shuffled):",
    ]
    for record in inst["records"]:
        coord = ",".join(map(str, record["coord"]))
        tag = ",".join(map(str, record["tag"]))
        lines.append(f"({coord}) : [{tag}]")
    lines.extend([
        "",
        "A certificate is two vectors slope and offset. Each has length r, every",
        f"entry is an integer in 0..{q - 1}, and all 2r entries must be pairwise",
        "distinct. To expand a certificate, copy them to U=slope and V=offset,",
        "then execute the following shear lines from top to bottom. A line d<-d+s",
        "means U[d]=(U[d]+U[s]) mod q and V[d]=(V[d]+V[s]) mod q.",
        "",
        f"SHEAR PROGRAM ({len(inst['shear_program'])} lines):",
    ])
    lines.extend(f"{dst}<-{dst}+{src}" for dst, src in inst["shear_program"])
    lines.extend([
        "",
        f"For construction rank i=0,1,...,{n - 1}, compute the tag vector",
        "T_i=(i*U+V) mod q componentwise and select the unique target record with",
        "that tag. Rank 0 must select the anchored seed, and ranks 1 onward give",
        "the particle-addition order. Every target record must be selected once.",
        "",
        "The movement path for a selected target (x,y,z) is part of this compressed",
        f"certificate: from (0,0,0), move in +z to (0,0,{high}), then in +x to",
        f"(x,0,{high}), then in +y to (x,y,{high}), then in -z to (x,y,z+1),",
        "and finally one step in -z to (x,y,z). The entire expanded sequence must",
        "obey the move/contact rule and finish with exactly the target polycube.",
        "All ranks and tag axes are 0-indexed; no residue representatives outside",
        "the stated range are accepted.",
        "",
        "Give your final answer inside <answer></answer> tags as one JSON object",
        f"with exactly two arrays of {r} integers: slope, then offset.",
        "Example shape: <answer>{\"slope\":[0,1],\"offset\":[2,3]}</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Recover the last tagged JSON answer while tolerating prose and fences."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    fenced = _FENCE_RE.fullmatch(body)
    if fenced:
        body = fenced.group(1).strip()
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict):
        return None
    if set(value) != {"slope", "offset"}:
        return None
    return value


def _construction_path(inst, target):
    high = inst["workspace_side"] - 1
    x, y, z = target
    path = [(0, 0, 0)]
    path.extend((0, 0, level) for level in range(1, high + 1))
    path.extend((level, 0, high) for level in range(1, x + 1))
    path.extend((x, level, high) for level in range(1, y + 1))
    path.extend((x, y, level) for level in range(high - 1, z, -1))
    path.append((x, y, z))
    return path


def _tag_index(inst):
    """Index displayed records once; the cache contains no planted information."""
    key = id(inst)
    cached = _TAG_CACHE.get(key)
    if cached is not None and cached[0] is inst:
        return cached[1], cached[2]
    mapping = {}
    duplicate = False
    for record in inst["records"]:
        tag = tuple(record["tag"])
        if tag in mapping:
            duplicate = True
        mapping[tag] = tuple(record["coord"])
    if len(_TAG_CACHE) >= 64:
        _TAG_CACHE.clear()
    _TAG_CACHE[key] = (inst, mapping, duplicate)
    return mapping, duplicate


def _candidate_vectors(inst, answer):
    if answer == {} or answer == []:
        return None, None, "answer is empty"
    if not isinstance(answer, dict) or set(answer) != {"slope", "offset"}:
        return None, None, "answer must be an object with exactly slope and offset"
    slope, offset = answer["slope"], answer["offset"]
    if not isinstance(slope, list) or len(slope) != inst["tag_dim"]:
        return None, None, f"slope must contain exactly {inst['tag_dim']} entries"
    if not isinstance(offset, list) or len(offset) != inst["tag_dim"]:
        return None, None, f"offset must contain exactly {inst['tag_dim']} entries"
    if not all(_is_int(value) for value in slope + offset):
        return None, None, "all coefficients must be integers"
    q = inst["modulus"]
    if not all(0 <= value < q for value in slope + offset):
        return None, None, f"a coefficient is outside the residue range 0..{q - 1}"
    if len(set(slope + offset)) != 2 * inst["tag_dim"]:
        return None, None, "the 2r coefficients are not pairwise distinct"
    return slope, offset, "ok"


def verify(inst, answer):
    """Expand and exactly replay any submitted compressed construction witness.

    Straight runs are checked in run-length form.  The checks below establish
    their unit expansion without iterating over empty workspace positions: the
    inlet columns are separated from every target by at least two grid units,
    the two horizontal runs are at least two layers above the whole target,
    and every point of the final descent has coordinate sum at least two above
    the current monotone prefix until the last move.
    """
    slope, offset, reason = _candidate_vectors(inst, answer)
    if reason != "ok":
        return False, reason

    q = inst["modulus"]
    shown_slope = _apply_shears(slope, inst["shear_program"], q)
    shown_offset = _apply_shears(offset, inst["shear_program"], q)
    tag_to_coord, duplicate_tags = _tag_index(inst)
    if duplicate_tags:
        return False, "instance contains duplicate target tags"

    order = []
    seen_tags = set()
    for rank in range(inst["n"]):
        tag = tuple(
            (rank * shown_slope[j] + shown_offset[j]) % q
            for j in range(inst["tag_dim"])
        )
        coordinate = tag_to_coord.get(tag)
        if coordinate is None:
            return False, f"tag mismatch at construction rank {rank}"
        if tag in seen_tags:
            return False, f"the affine program repeats a tag at rank {rank}"
        seen_tags.add(tag)
        order.append(coordinate)
    if len(seen_tags) != len(tag_to_coord):
        return False, "the affine program does not select every target cube"

    seed = tuple(inst["seed_coord"])
    if order[0] != seed:
        return False, "construction rank 0 does not select the anchored seed"
    side = inst["workspace_side"]
    target_shape = set(tag_to_coord.values())
    if len(target_shape) != inst["n"]:
        return False, "instance contains duplicate target coordinates"
    if any(any(value < 0 or value >= side for value in point) for point in target_shape):
        return False, "a target cube lies outside the workspace"

    high = side - 1
    if min(min(point) for point in target_shape) < 2:
        return False, "the target is not separated from the inlet routing columns"
    if max(point[2] for point in target_shape) > high - 2:
        return False, "the target is not separated from the upper routing plane"

    # A positive-unit monotone path is induced: coordinate sum increases by one
    # per rank, so nonconsecutive cubes cannot be face-neighbors.  This also
    # proves all descent positions above target+e_z clear of the current prefix.
    for rank, point in enumerate(order):
        if sum(point) != 3 * inst["n"] + rank:
            return False, f"coordinate sum does not equal construction rank {rank}"
        if rank:
            previous = order[rank - 1]
            delta = tuple(point[j] - previous[j] for j in range(3))
            if delta not in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
                return False, f"rank {rank} is not the next cube of a monotone grid path"

    assembly = {seed}
    total_unit_moves = 0
    for rank, target in enumerate(order[1:], 1):
        if target in assembly:
            return False, f"rank {rank} selects an already occupied position"
        x, y, z = target
        # Exact length of the five public axis-aligned runs.  Their endpoints
        # and clearance are certified by the bounds/rank checks above.
        step_moves = high + x + y + (high - z - 1) + 1
        if step_moves <= 0:
            return False, f"rank {rank} has an invalid run-length path"
        total_unit_moves += step_moves
        pretarget = (x, y, z + 1)
        if any(neighbor in assembly for neighbor in _neighbors(pretarget)):
            return False, f"rank {rank} sticks before the final path step"
        contacts = sum(neighbor in assembly for neighbor in _neighbors(target))
        if contacts != 1:
            return False, f"rank {rank} target has {contacts} prior face contacts"
        assembly.add(target)
    if assembly != target_shape:
        return False, "expanded construction does not equal the target polycube"
    return True, "ok"


def random_candidate(inst, rng):
    values = rng.sample(range(inst["modulus"]), 2 * inst["tag_dim"])
    return {
        "slope": values[:inst["tag_dim"]],
        "offset": values[inst["tag_dim"]:],
    }


def search_space(inst):
    q = inst["modulus"]
    result = 1
    for value in range(2 * inst["tag_dim"]):
        result *= q - value
    return result


def enumerate_all(inst):
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    hits = 0
    r = inst["tag_dim"]
    for values in itertools.permutations(range(inst["modulus"]), 2 * r):
        candidate = {"slope": list(values[:r]), "offset": list(values[r:])}
        hits += int(verify(inst, candidate)[0])
    return hits


def _records_by_coordinate(inst):
    return {tuple(record["coord"]): record for record in inst["records"]}


def _reference_algorithm(inst):
    """Paper-style path reconstruction followed by exact affine recovery."""
    started = time.perf_counter()
    records = _records_by_coordinate(inst)
    n = inst["n"]
    r = inst["tag_dim"]
    operations = n * (r + 3)  # scalar input fields read
    seed = tuple(inst["seed_coord"])
    if seed not in records:
        return None, {"operations": operations, "wall_clock_sec": 0.0}
    order = [seed]
    previous = None
    current = seed
    while len(order) < n:
        candidates = []
        for neighbor in _neighbors(current):
            operations += 1
            if neighbor in records and neighbor != previous:
                candidates.append(neighbor)
        if len(candidates) != 1:
            return None, {
                "operations": operations,
                "wall_clock_sec": time.perf_counter() - started,
            }
        previous, current = current, candidates[0]
        order.append(current)

    shown_offset = list(records[order[0]]["tag"])
    shown_slope = [
        (records[order[1]]["tag"][j] - shown_offset[j]) % inst["modulus"]
        for j in range(r)
    ]
    operations += r
    slope = _undo_shears(shown_slope, inst["shear_program"], inst["modulus"])
    offset = _undo_shears(shown_offset, inst["shear_program"], inst["modulus"])
    operations += 2 * len(inst["shear_program"])
    return {"slope": slope, "offset": offset}, {
        "operations": operations,
        "wall_clock_sec": time.perf_counter() - started,
    }


def _attack_outlier(inst):
    values = sorted({value for record in inst["records"] for value in record["tag"]})
    need = 2 * inst["tag_dim"]
    if len(values) < need:
        return None
    picked = values[:need]
    r = inst["tag_dim"]
    return {"slope": picked[:r], "offset": picked[r:]}


def _candidate_from_two_tags(inst, first, second, reverse=True):
    q = inst["modulus"]
    shown_offset = list(first)
    shown_slope = [(second[j] - first[j]) % q for j in range(inst["tag_dim"])]
    operation = _undo_shears if reverse else _apply_shears
    return {
        "slope": operation(shown_slope, inst["shear_program"], q),
        "offset": operation(shown_offset, inst["shear_program"], q),
    }


def _attack_public_order(inst):
    return _candidate_from_two_tags(
        inst, inst["records"][0]["tag"], inst["records"][1]["tag"], reverse=True
    )


def _attack_forward_shears(inst):
    records = _records_by_coordinate(inst)
    seed = tuple(inst["seed_coord"])
    positive_neighbors = [point for point in _neighbors(seed) if point in records]
    if len(positive_neighbors) != 1:
        return None
    return _candidate_from_two_tags(
        inst,
        records[seed]["tag"],
        records[positive_neighbors[0]]["tag"],
        reverse=False,
    )


def _normalize_instance(inst):
    """Canonical payload modulo record order and named coordinate-axis relabelings."""
    n = inst["n"]
    r = inst["tag_dim"]
    marker_order = sorted(range(r), key=lambda j: inst["tag_axis_markers"][j])
    new_index = {old: new for new, old in enumerate(marker_order)}
    normalized_shears = [
        [new_index[dst], new_index[src]] for dst, src in inst["shear_program"]
    ]
    ordered = sorted(
        inst["records"],
        key=lambda record: sum(record["coord"]) - 3 * n,
    )
    spatial_word = []
    for left, right in zip(ordered, ordered[1:]):
        differences = [right["coord"][j] - left["coord"][j] for j in range(3)]
        if differences.count(1) != 1 or any(value not in (0, 1) for value in differences):
            spatial_word.append(3)
        else:
            spatial_word.append(differences.index(1))
    spatial_orbit = min(
        tuple(permutation[axis] if axis < 3 else axis for axis in spatial_word)
        for permutation in itertools.permutations(range(3))
    )
    return {
        "n": n,
        "workspace_side": inst["workspace_side"],
        "modulus": inst["modulus"],
        "tag_dim": r,
        "markers": sorted(inst["tag_axis_markers"]),
        "shears": normalized_shears,
        "spatial_word_orbit": spatial_orbit,
        "ranked_tags": [
            [record["tag"][j] for j in marker_order] for record in ordered
        ],
    }


def canonical_key(inst):
    payload = json.dumps(_normalize_instance(inst), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _relabel_instance(inst, rng):
    result = copy.deepcopy(inst)
    spatial = list(range(3))
    tags = list(range(inst["tag_dim"]))
    rng.shuffle(spatial)
    rng.shuffle(tags)
    tag_inverse = {old: new for new, old in enumerate(tags)}

    for record in result["records"]:
        old_coord = record["coord"][:]
        old_tag = record["tag"][:]
        record["coord"] = [old_coord[spatial[j]] for j in range(3)]
        record["tag"] = [old_tag[tags[j]] for j in range(inst["tag_dim"])]
    result["seed_coord"] = [inst["seed_coord"][spatial[j]] for j in range(3)]
    result["tag_axis_markers"] = [
        inst["tag_axis_markers"][tags[j]] for j in range(inst["tag_dim"])
    ]
    result["shear_program"] = [
        [tag_inverse[dst], tag_inverse[src]] for dst, src in inst["shear_program"]
    ]
    result["answer"] = {
        "slope": [inst["answer"]["slope"][tags[j]] for j in range(inst["tag_dim"])],
        "offset": [inst["answer"]["offset"][tags[j]] for j in range(inst["tag_dim"])],
    }
    rng.shuffle(result["records"])
    return result


def escalate(params):
    next_params = dict(params)
    next_params["n"] = min(10_000, max(params["n"] + 1, (3 * params["n"]) // 2))
    prime_ladder = [1_000_003, 10_000_019, 100_000_007, 1_000_000_007, 2_147_483_647]
    next_params["modulus"] = next(
        (prime for prime in prime_ladder if prime > params["modulus"]),
        params["modulus"],
    )
    next_params["shears"] = min(140, params["shears"] + 5)
    if next_params == params:
        return None
    return next_params


def _answer_elements(answer):
    return len(answer.get("slope", [])) + len(answer.get("offset", []))


def selftest():
    report = {}

    # G1: every preset and three seeds, including JSON-native serialization.
    failures = []
    attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            attempts += 1
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append([preset, seed, "answer is not JSON-native"])
                continue
            ok, reason = verify(inst, inst["answer"])
            if not ok:
                failures.append([preset, seed, reason])
    report["G1_planted_verifies"] = {
        "pass": not failures,
        "attempts": attempts,
        "failures": failures,
    }

    # G2: five corruption modes and five distinct rejection reasons.
    demo = make_instance(seed=23, **DIFFICULTY["demo"])
    good = copy.deepcopy(demo["answer"])
    corruptions = {}
    dropped = copy.deepcopy(good)
    dropped["slope"].pop()
    corruptions["drop_one"] = dropped
    swapped = copy.deepcopy(good)
    swapped["slope"][0], swapped["offset"][0] = (
        swapped["offset"][0], swapped["slope"][0]
    )
    corruptions["swap_one"] = swapped
    duplicated = copy.deepcopy(good)
    duplicated["offset"][0] = duplicated["slope"][0]
    corruptions["duplicate_one"] = duplicated
    corruptions["empty"] = {}
    outside = copy.deepcopy(good)
    outside["slope"][0] = demo["modulus"]
    corruptions["out_of_range"] = outside
    cases = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(demo, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
                and len(set(reasons)) == len(reasons),
        "cases": cases,
        "distinct_reasons": len(set(reasons)),
    }

    # G3: realistic prose, a Markdown fence inside the tags, and malformed text.
    realistic = (
        "I reconstructed the monotone order and reversed the shears.\n"
        "<answer>```json\n"
        + json.dumps(good, separators=(",", ":"))
        + "\n```</answer>\nThe unit paths then check out."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == good and verify(demo, parsed)[0]
                and parse_answer("garbage") is None,
        "parsed_equals_answer": parsed == good,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    shipping = make_instance(seed=314159, **shipping_params)

    # G4/G5 density: one structure-aware sample, reused without relabeling it.
    guess_rng = random.Random(271828)
    guess_hits = 0
    guess_started = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_elapsed = time.perf_counter() - guess_started
    guess_probability = guess_hits / _G4_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": _G4_SAMPLES,
        "observed_probability": guess_probability,
        "structure_aware_space": search_space(shipping),
        "sampling_rule": "uniform ordered sample of 2r distinct field residues",
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    # G6 attacks and successful Track-B reference algorithm on eight seeds.
    attacks = {
        "outlier_smallest_tag_residues": {"successes": 0, "attempts": 0},
        "greedy_public_record_order": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
        "in_context_forward_shear_ansatz": {"successes": 0, "attempts": 0},
    }
    attack_times = {name: 0.0 for name in attacks}
    reference_successes = 0
    reference_operations = []
    reference_times = []
    random_trials = 0
    for index in range(_ATTACK_SEEDS):
        inst = make_instance(seed=10_000 + index, **shipping_params)
        for name, function in (
            ("outlier_smallest_tag_residues", _attack_outlier),
            ("greedy_public_record_order", _attack_public_order),
            ("in_context_forward_shear_ansatz", _attack_forward_shears),
        ):
            started = time.perf_counter()
            candidate = function(inst)
            elapsed = time.perf_counter() - started
            attack_times[name] += elapsed
            attacks[name]["attempts"] += 1
            attacks[name]["successes"] += int(
                candidate is not None and verify(inst, candidate)[0]
            )

        started = time.perf_counter()
        restart_rng = random.Random(90_000 + index)
        solved = False
        for _ in range(256):
            random_trials += 1
            if verify(inst, random_candidate(inst, restart_rng))[0]:
                solved = True
                break
        attack_times["random_restart_256"] += time.perf_counter() - started
        attacks["random_restart_256"]["attempts"] += 1
        attacks["random_restart_256"]["successes"] += int(solved)

        candidate, stats = _reference_algorithm(inst)
        reference_operations.append(stats["operations"])
        reference_times.append(stats["wall_clock_sec"])
        reference_successes += int(candidate is not None and verify(inst, candidate)[0])

    for name in attacks:
        attacks[name]["wall_clock_sec_total_8"] = round(attack_times[name], 6)
    all_attacks_failed = all(result["successes"] == 0 for result in attacks.values())
    reference = {
        "name": "Section 5.1 tree-path reconstruction plus affine recovery",
        "complexity": "O(n*r + t*r) input processing; O(n) geometric tree traversal",
        "wall_clock_sec_mean": round(sum(reference_times) / len(reference_times), 6),
        "wall_clock_sec_total_8": round(sum(reference_times), 6),
        "operations_mean": round(sum(reference_operations) / len(reference_operations)),
        "operations_min": min(reference_operations),
        "operations_max": max(reference_operations),
        "solves": f"{reference_successes}/{_ATTACK_SEEDS}, as expected",
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == _ATTACK_SEEDS,
        "attacks": attacks,
        "reference_algorithm": reference,
        "compact_route": {
            "name": "use coordinate-sum rank and undo the public shears",
            "operations": shipping["tag_dim"] + 2 * len(shipping["shear_program"]),
        },
    }

    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_probability < 1e-6 and all_attacks_failed
                and reference_successes == _ATTACK_SEEDS and demo_count == 1,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": _G4_SAMPLES,
        "shipping_valid_fraction": guess_probability,
        "analytic_shipping_valid_solution_count": 1,
        "demo_exact_solution_count_by_enumeration": demo_count,
        "candidate_space": search_space(shipping),
        "strongest_failing_attack": "random_restart_256",
        "baseline_wall_clock_seconds_total_8": round(
            attack_times["random_restart_256"], 6
        ),
        "baseline_restarts_total_8": random_trials,
        "reference_algorithm_operations_mean": reference["operations_mean"],
        "reference_algorithm_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
    }

    # G7: double the target while retaining the same 24-atom answer shape.
    doubled_params = dict(shipping_params)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=777, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok
                and search_space(doubled) == search_space(shipping)
                and len(doubled["records"]) == 2 * len(shipping["records"]),
        "n_before": shipping["n"],
        "n_after_doubling": doubled["n"],
        "space_before": search_space(shipping),
        "space_after": search_space(doubled),
        "answer_elements_before": _answer_elements(shipping["answer"]),
        "answer_elements_after": _answer_elements(doubled["answer"]),
        "verify_reason": doubled_reason,
    }

    # G8: record order, spatial axes, named tag axes, and their compositions.
    invariance_checks = 0
    carried_checks = 0
    failures = []
    unrelated_keys = []
    g8_params = {"n": 48, "modulus": 1009, "tag_dim": 6, "shears": 12}
    for index in range(20):
        inst = make_instance(seed=20_000 + index, **g8_params)
        key = canonical_key(inst)
        unrelated_keys.append(key)

        reordered = copy.deepcopy(inst)
        reordered["records"].reverse()
        invariance_checks += 1
        if canonical_key(reordered) != key:
            failures.append([index, "record order"])
        carried_checks += 1
        if not verify(reordered, reordered["answer"])[0]:
            failures.append([index, "record-order carried witness"])

        transformed = _relabel_instance(inst, random.Random(30_000 + index))
        invariance_checks += 1
        if canonical_key(transformed) != key:
            failures.append([index, "spatial and tag-axis relabeling"])
        carried_checks += 1
        if not verify(transformed, transformed["answer"])[0]:
            failures.append([index, "relabeling carried witness"])

        composed = _relabel_instance(transformed, random.Random(40_000 + index))
        invariance_checks += 1
        if canonical_key(composed) != key:
            failures.append([index, "composed relabeling"])
        carried_checks += 1
        if not verify(composed, composed["answer"])[0]:
            failures.append([index, "composed carried witness"])
    report["G8_canonical_key"] = {
        "pass": not failures and len(set(unrelated_keys)) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "failures": failures,
        "unrelated_instances": 20,
        "distinct_keys": len(set(unrelated_keys)),
        "symmetries_tested": [
            "target-record order",
            "all 3D coordinate-axis permutations",
            "named tag-axis permutations",
            "compositions of spatial/tag relabelings",
        ],
    }

    answer_blob = json.dumps(shipping["answer"], separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_elements(shipping["answer"])
    intended_operations = shipping["tag_dim"] + 2 * len(shipping["shear_program"])
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else 0.0
    placebo_rate = arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else 0.0
    evidence_complete = all(arms[name]["attempts"] >= 3 for name in arms)
    hinted_hardened = (
        G9_ORACLE_RESULTS["hinted_verdict"] == "hardened"
        and arms["hinted"]["solved"] == 0
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": evidence_complete and hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    report["paper"] = "arXiv:2105.05784"
    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping_params)
    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
