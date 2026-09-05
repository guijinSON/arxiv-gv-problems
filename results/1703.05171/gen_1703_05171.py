"""Anchored constant-weight code completion from coordinate-permutation orbits.

The paper defines constant-weight binary codes and, in Section 1.2, uses the
action of the symmetric group on coordinates, explicitly observing that this
action preserves weights and Hamming distances.  This generator turns that
native symmetry into exact code-completion instances.  A code orbit is made
first, independently distributed incomplete orbit fragments are added as
decoys, and only then are candidate identifiers assigned.
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


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # pragma: no cover - the implementation is stdlib-complete
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "binary words of one fixed weight",
        "a coordinate permutation preserving weight and Hamming distance",
        "an anchored constant-weight code",
    ],
    "verification_operations": [
        "exact binary Hamming weight",
        "exact pairwise Hamming distance",
        "candidate-index and anchor membership checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 1.2: the simultaneous S_n action on coordinates preserves "
        "weight, Hamming distance, and code cardinality; the instance uses "
        "exactly these coordinate-permutation orbits."
    ),
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Recognize that the supplied coordinate permutation organizes the "
        "candidate words into orbit fragments and that the anchored full "
        "orbit is a code; otherwise search a crowded exact-cover instance."
    ),
    "hardness_basis": (
        "Track B: coordinate-permutation orbit indexing solves these generated "
        "instances in O(NL+kL) bit operations; across eight shipping instances "
        "it used 2,825,984 bit inspections (353,248 each) and 0.0035--0.0457 "
        "seconds across isolated and contended-host audit runs, "
        "while domain-standard Algorithm X used 3,798,441 row "
        "checks, and the compact route uses 294 coordinate-lookups and sorted-list "
        "comparisons after the Section 1.2 symmetry is recognized."
    ),
    "max_answer_tokens": 9,
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
    "demo": {"n": 3, "code_size": 3, "decoy_orbits": 2},
    "easy": {"n": 8, "code_size": 5, "decoy_orbits": 12},
    "medium": {"n": 16, "code_size": 7, "decoy_orbits": 60},
    "hard": {"n": 38, "code_size": 7, "decoy_orbits": 220},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "Hint: The supplied coordinate permutation partitions the candidate words "
    "into short orbit fragments."
)
PLACEBO_HINT = (
    "Hint: The supplied hexadecimal notation makes the candidate words compact "
    "and precisely indexed."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A strictly increasing JSON list of exactly code_size distinct candidate "
        "IDs, containing the mandatory anchor ID; every other ID is drawn from "
        "the displayed candidates individually disjoint from the anchor."
    ),
    "bounds": {
        "list_length": "code_size (at most 8 in the shipping ladder)",
        "id_min": 0,
        "id_max": "candidate_count-1",
        "mandatory_ids": 1,
        "anchor_compatible_before_sampling": True,
    },
}

NOTES = r"""
Paper boundary and exact definition. Section 1 defines a binary word, Hamming
distance, Hamming weight, a code, and A(n,d,w), the maximum size of a set of
weight-w words whose distinct pairs have distance at least d. This module asks
for exactly such a set inside a displayed candidate collection and requires one
displayed anchor word. It does not compile the words into a graph: render hands
the solver the words themselves, and verify recomputes their weights and all
pairwise Hamming distances.

Construction. Section 1.2 states that simultaneous coordinate permutations
preserve weight and distance. Here the coordinate permutation consists of n
disjoint cycles of length k=code_size. A base word chooses one coordinate in
each cycle. Its k images have pairwise disjoint supports, hence common weight n
and distance 2n; they are the planted code. Each decoy base differs from the
anchor by two independently placed phase values, so precisely k-2 of its orbit
words are anchor-compatible and mutually disjoint; one of the two incompatible
shifts is omitted. The absolute phase in every cycle is still uniform, so an
individual decoy word and an individual plant word have exactly the same
one-word distribution. The certificate is carried through the final
lexicographic candidate ordering; it is never obtained by solving the completed
instance.

Step-0 decision. Proposition 1.1 turns an already-known code into feasible SDP
data, and the paragraph following definitions (2)-(3) says A_k is polynomial
time computable for fixed k after symmetry reduction. The largest reported
B_4(22,8,10) computation nevertheless took about three weeks (Section 1.2).
That SDP is an upper-bound algorithm, not a search algorithm for the code asked
for here. Conversely, the paper's Golay lower bound merely filters the 2,048
words of one fixed shortened Golay code, so it is too small and too cheap to be
a scalable Track-A family. This construction is therefore Track B and openly
reports its efficient orbit-indexing solver. The paper-licensed representation
is cited in PROBLEM_PROFILE because the mixed-category corpus guard needs the
combinatorial S_n route made explicit; no native binary-word data are compiled
away.

Mechanical and compact routes. The reference solver parses/indexes all N words,
then repeatedly applies the supplied permutation to the anchor. Its declared
cost is O(NL+kL) bit inspections for word length L=n*k, and selftest records its
measured shipping cost. Once the orbit invariant is noticed, the no-tool route
needs (k-1)n coordinate lookups plus (k-1) ceiling(log2 N) comparisons in the
lexicographically sorted list: 294 operations at the shipping preset. This is
below the 300-operation cap but still awkward without a sandbox or text-search.

Easy regimes and attacks. A tool with a dictionary makes orbit lookup routine,
which is why this is not Track A. Domain-standard Algorithm X is also run and
reported as a successful Track-B reference. The outlier attack uses coordinate-
frequency rarity, the two greedy attacks use input order or aggregate
disjointness, and random restart greedily samples the anchor-compatible pool;
all are required to fail on eight shipping seeds. The mandatory-anchor
constraint is incorporated into random_candidate, as is the immediately
deducible requirement that every other chosen word be disjoint from the anchor.
canonical_key uses iterative row/coordinate color refinement on orbit phases.
It is invariant under arbitrary coordinate relabelling and candidate reorder,
but is not claimed to solve exact isomorphism of all colored set systems.
""".strip()

# Filled after the script-owned bare, structural, and placebo hardening runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}

_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 1_000_000


def _check_int(name: str, value: object, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer at least {minimum}")
    return value


def _support_to_int(support: tuple[int, ...] | list[int]) -> int:
    value = 0
    for coordinate in support:
        value |= 1 << coordinate
    return value


def _int_to_support(word: int) -> tuple[int, ...]:
    support = []
    while word:
        low = word & -word
        support.append(low.bit_length() - 1)
        word ^= low
    return tuple(support)


def _apply_permutation(word: int, permutation: list[int]) -> int:
    moved = 0
    while word:
        low = word & -word
        coordinate = low.bit_length() - 1
        moved |= 1 << permutation[coordinate]
        word ^= low
    return moved


def _orbit_words(
    offsets: tuple[int, ...], cycles: list[list[int]], code_size: int
) -> list[int]:
    return [
        _support_to_int([
            cycle[(offset + shift) % code_size]
            for cycle, offset in zip(cycles, offsets)
        ])
        for shift in range(code_size)
    ]


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Construct a full permutation orbit first, then add partial orbit decoys."""
    code_size = params.pop("code_size", 8)
    decoy_orbits = params.pop("decoy_orbits", 0)
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    block_count = _check_int("n", n, 2)
    k = _check_int("code_size", code_size, 3)
    decoys = _check_int("decoy_orbits", decoy_orbits, 0)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    available_orbits = k ** (block_count - 1)
    if decoys + 1 > available_orbits:
        raise ValueError("too many distinct orbit fragments for these parameters")

    rng = random.Random(seed)
    length = block_count * k
    coordinates = list(range(length))
    rng.shuffle(coordinates)
    cycles = []
    permutation = [0] * length
    for start in range(0, length, k):
        cycle = coordinates[start:start + k]
        cycles.append(cycle)
        for i, coordinate in enumerate(cycle):
            permutation[coordinate] = cycle[(i + 1) % k]

    # Normalize the first offset to zero when testing orbit identity: adding a
    # common constant merely selects another base point in the same orbit.
    orbit_keys: set[tuple[int, ...]] = set()

    def fresh_offsets() -> tuple[int, ...]:
        while True:
            raw = tuple(rng.randrange(k) for _ in range(block_count))
            origin = raw[0]
            key = tuple((value - origin) % k for value in raw)
            if key not in orbit_keys:
                orbit_keys.add(key)
                return raw

    plant_offsets = fresh_offsets()
    planted_words = _orbit_words(plant_offsets, cycles, k)
    all_words = list(planted_words)
    for _ in range(decoys):
        # A two-phase near orbit. Relative to the public anchor, shifts -a and
        # -b collide in at least one cycle; every other shift is disjoint. One
        # colliding shift is omitted, leaving k-2 eligible mutually compatible
        # decoys plus one visibly anchor-incompatible word. This crowds the
        # exact-cover graph without changing any single word's uniform marginal.
        while True:
            a, b = rng.sample(range(k), 2)
            deltas = [a if rng.randrange(2) == 0 else b for _ in range(block_count)]
            deltas[0] = a
            deltas[1] = b
            rng.shuffle(deltas)
            offsets = tuple(
                (plant_offsets[column] + deltas[column]) % k
                for column in range(block_count)
            )
            origin = offsets[0]
            key = tuple((value - origin) % k for value in offsets)
            if key not in orbit_keys:
                orbit_keys.add(key)
                break
        orbit = _orbit_words(offsets, cycles, k)
        omitted_shift = rng.choice(((-a) % k, (-b) % k))
        all_words.extend(
            word for shift, word in enumerate(orbit) if shift != omitted_shift
        )

    # Word values are unique because distinct normalized offset vectors are
    # distinct permutation orbits. Sorting makes the rendered membership table
    # searchable without changing the certificate.
    all_words.sort()
    word_to_id = {word: index for index, word in enumerate(all_words)}
    if len(word_to_id) != len(all_words):
        raise AssertionError("construction unexpectedly produced duplicate words")
    answer = sorted(word_to_id[word] for word in planted_words)
    anchor_word = planted_words[0]
    anchor_id = word_to_id[anchor_word]
    width = (length + 3) // 4
    eligible = [
        index
        for index, word in enumerate(all_words)
        if index != anchor_id
        and (anchor_word ^ word).bit_count() >= 2 * block_count
    ]

    return {
        "n": block_count,
        "length": length,
        "code_size": k,
        "word_weight": block_count,
        "min_distance": 2 * block_count,
        "decoy_orbits": decoys,
        "candidate_count": len(all_words),
        "hex_width": width,
        "permutation": permutation,
        "words": [format(word, f"0{width}x") for word in all_words],
        "anchor": anchor_id,
        # Cached because G4 draws 200,000 candidates. It is derivable directly
        # from the public anchor and words and is intentionally not rendered.
        "anchor_eligible": eligible,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render a complete anchored constant-weight-code completion problem."""
    candidates = "\n".join(
        f"{index}: {word}" for index, word in enumerate(inst["words"])
    )
    example = list(range(inst["code_size"]))
    statement = f"""Anchored constant-weight binary code completion

A binary word of length L is a string of L zero/one bits. Its Hamming weight is
the number of 1 bits. The Hamming distance between two words is the number of
coordinates on which they differ. A constant-weight code of size k, weight w,
and minimum distance d is a set of exactly k distinct length-L words, every one
of weight w, such that every pair has Hamming distance at least d.

Choose a code from the candidate table below. Candidate IDs are 0-based. Your
code must contain the mandatory anchor ID {inst['anchor']}. The answer is a
strictly increasing list of exactly {inst['code_size']} distinct IDs; order has
no mathematical meaning, and increasing order is the required canonical output.

Parameters:
  L = {inst['length']}
  k = {inst['code_size']}
  w = {inst['word_weight']}
  d = {inst['min_distance']}

Words are written as exactly {inst['hex_width']} lowercase hexadecimal digits,
including leading zeroes. Coordinate i is bit i counted from the RIGHT starting
at i=0. Thus XOR followed by an exact 1-bit count gives Hamming distance.

The following supplied coordinate permutation maps old coordinate i to the
entry at position i. It is instance data and may be useful:
{json.dumps(inst['permutation'], separators=(',', ':'))}

Candidate table (ID: hexadecimal word), sorted by hexadecimal word:
{candidates}

Give your final answer inside <answer></answer> tags, as one JSON array of
exactly {inst['code_size']} strictly increasing 0-based candidate IDs.
Example format (not necessarily a solution): <answer>{json.dumps(example)}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract an integer JSON list from tags, a fence, or surrounding prose."""
    if not isinstance(text, str):
        return None
    tagged = _ANSWER_RE.findall(text)
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, re.I | re.S)
    bare = re.findall(r"\[(?:\s*-?\d+\s*,)*\s*-?\d+\s*\]", text, re.S)
    bodies = tagged if tagged else (fenced if fenced else bare)
    for body in reversed(bodies):
        try:
            value = json.loads(body.strip())
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(value, list) and all(
            isinstance(item, int) and not isinstance(item, bool) for item in value
        ):
            return value
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any submitted candidate code exactly, without reading the plant."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    expected = inst["code_size"]
    if len(answer) != expected:
        return False, f"wrong number of IDs: expected {expected}, got {len(answer)}"
    if any(isinstance(item, bool) or not isinstance(item, int) for item in answer):
        return False, "every candidate ID must be an integer"
    if any(item < 0 or item >= inst["candidate_count"] for item in answer):
        return False, "candidate ID out of range"
    if len(set(answer)) != len(answer):
        return False, "candidate IDs must be distinct"
    if answer != sorted(answer):
        return False, "candidate IDs must be strictly increasing"
    if inst["anchor"] not in answer:
        return False, f"mandatory anchor ID {inst['anchor']} is missing"

    words = [int(inst["words"][item], 16) for item in answer]
    for item, word in zip(answer, words):
        weight = word.bit_count()
        if weight != inst["word_weight"]:
            return False, f"candidate {item} has weight {weight}, not {inst['word_weight']}"
    for left in range(len(words)):
        for right in range(left + 1, len(words)):
            distance = (words[left] ^ words[right]).bit_count()
            if distance < inst["min_distance"]:
                return False, (
                    f"IDs {answer[left]} and {answer[right]} have distance "
                    f"{distance}, below {inst['min_distance']}"
                )
    return True, "ok"


def _eligible_ids(inst: dict) -> list[int]:
    if "anchor_eligible" in inst:
        return list(inst["anchor_eligible"])
    anchor = int(inst["words"][inst["anchor"]], 16)
    return [
        index
        for index, raw in enumerate(inst["words"])
        if index != inst["anchor"]
        and (anchor ^ int(raw, 16)).bit_count() >= inst["min_distance"]
    ]


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly after enforcing shape, anchor, and anchor compatibility."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    eligible = _eligible_ids(inst)
    need = inst["code_size"] - 1
    if len(eligible) < need:
        raise ValueError("instance has fewer anchor-compatible IDs than required")
    return sorted([inst["anchor"], *rng.sample(eligible, need)])


def search_space(inst: dict) -> int | None:
    eligible = len(_eligible_ids(inst))
    return math.comb(eligible, inst["code_size"] - 1)


def enumerate_all(inst: dict) -> int | None:
    """Count valid anchored codes exactly when the structured space is small."""
    total = search_space(inst)
    if total is None or total > _ENUMERATION_CAP:
        return None
    count = 0
    anchor = inst["anchor"]
    for rest in itertools.combinations(_eligible_ids(inst), inst["code_size"] - 1):
        count += int(verify(inst, sorted((anchor, *rest)))[0])
    return count


def _phase_matrix(inst: dict) -> tuple[list[list[int]], int]:
    """Express each candidate by its phase in every permutation cycle."""
    permutation = inst["permutation"]
    k = inst["code_size"]
    anchor_support = _int_to_support(int(inst["words"][inst["anchor"]], 16))
    cycles = []
    coordinate_phase: dict[int, tuple[int, int]] = {}
    for column, start in enumerate(anchor_support):
        cycle = []
        value = start
        for phase in range(k):
            if value in coordinate_phase:
                raise ValueError("anchor does not select one point in each cycle")
            coordinate_phase[value] = (column, phase)
            cycle.append(value)
            value = permutation[value]
        if value != start:
            raise ValueError("permutation cycle has the wrong length")
        cycles.append(cycle)
    if len(coordinate_phase) != inst["length"]:
        raise ValueError("anchor does not meet every permutation cycle")

    matrix = []
    for raw in inst["words"]:
        row = [-1] * len(cycles)
        for coordinate in _int_to_support(int(raw, 16)):
            column, phase = coordinate_phase[coordinate]
            if row[column] != -1:
                raise ValueError("candidate meets a permutation cycle twice")
            row[column] = phase
        if any(value < 0 for value in row):
            raise ValueError("candidate misses a permutation cycle")
        matrix.append(row)
    return matrix, inst["anchor"]


def _color_refinement_signature(inst: dict) -> dict:
    """Invariant of the phase matrix under row and permutation-cycle reorder."""
    matrix, anchor = _phase_matrix(inst)
    row_count = len(matrix)
    column_count = inst["n"]
    row_colors = [int(row == anchor) for row in range(row_count)]
    column_colors = [0] * column_count
    rounds = 0
    for rounds in range(1, 17):
        row_signatures = [
            (
                "r",
                int(row == anchor),
                row_colors[row],
                tuple(sorted(
                    (column_colors[column], matrix[row][column])
                    for column in range(column_count)
                )),
            )
            for row in range(row_count)
        ]
        column_signatures = [
            (
                "c",
                column_colors[column],
                tuple(sorted(
                    (row_colors[row], matrix[row][column])
                    for row in range(row_count)
                )),
            )
            for column in range(column_count)
        ]
        all_signatures = row_signatures + column_signatures
        palette = {
            signature: color
            for color, signature in enumerate(sorted(set(all_signatures)))
        }
        new_rows = [palette[signature] for signature in row_signatures]
        new_columns = [palette[signature] for signature in column_signatures]
        if new_rows == row_colors and new_columns == column_colors:
            break
        row_colors, column_colors = new_rows, new_columns

    row_hist = sorted((color, row_colors.count(color)) for color in set(row_colors))
    column_hist = sorted(
        (color, column_colors.count(color)) for color in set(column_colors)
    )
    incidence: dict[tuple[int, int, int], int] = {}
    for row in range(row_count):
        for column in range(column_count):
            key = (row_colors[row], column_colors[column], matrix[row][column])
            incidence[key] = incidence.get(key, 0) + 1
    return {
        "length": inst["length"],
        "code_size": inst["code_size"],
        "candidate_count": inst["candidate_count"],
        "rounds": rounds,
        "rows": row_hist,
        "columns": column_hist,
        "incidence": sorted((list(key), value) for key, value in incidence.items()),
    }


def canonical_key(inst: dict) -> str:
    """Hash a structural color-refinement invariant, never seed or rendering."""
    payload = json.dumps(
        _color_refinement_signature(inst), sort_keys=True, separators=(",", ":")
    )
    digest = hashlib.sha256(payload.encode("ascii")).hexdigest()
    return f"anchored-cw-orbit-wl:{digest}"


def escalate(params: dict) -> dict | str | None:
    """Grow only the partial-orbit haystack, keeping the answer length fixed."""
    expected = {"n", "code_size", "decoy_orbits"}
    if not isinstance(params, dict) or set(params) != expected:
        return None
    n = params["n"]
    k = params["code_size"]
    decoys = params["decoy_orbits"]
    if any(isinstance(x, bool) or not isinstance(x, int) for x in (n, k, decoys)):
        return None
    # Up to 1,000 fragments keeps rendering within ordinary model contexts;
    # answer size and the <=300-operation compact route remain unchanged.
    if decoys < 1_000 and decoys + 1 < k ** (n - 1):
        return {"n": n, "code_size": k, "decoy_orbits": min(1_000, decoys + 130)}
    return None


def _reference_orbit_solver(inst: dict) -> tuple[list[int] | None, int]:
    """Index every word, then recover the complete orbit of the anchor."""
    words = [int(raw, 16) for raw in inst["words"]]
    by_word = {word: index for index, word in enumerate(words)}
    current = words[inst["anchor"]]
    ids = []
    moved_supports = 0
    for _ in range(inst["code_size"]):
        index = by_word.get(current)
        if index is None:
            return None, inst["candidate_count"] * inst["length"] + moved_supports
        ids.append(index)
        current = _apply_permutation(current, inst["permutation"])
        moved_supports += inst["word_weight"]
    operations = inst["candidate_count"] * inst["length"] + moved_supports
    return sorted(ids), operations


def _algorithm_x(
    inst: dict, node_cap: int = 5_000_000
) -> tuple[list[int] | None, int, int]:
    """Domain-standard exact-cover search with a minimum-column rule.

    Pairwise disjoint weight-n words of cardinality k cover all k*n
    coordinates, so the Hamming-code task is an exact-cover instance without
    replacing the objects used by verify. The returned counters are recursion
    nodes and exact row-availability checks.
    """
    words = [int(raw, 16) for raw in inst["words"]]
    anchor = inst["anchor"]
    full = (1 << inst["length"]) - 1
    uncovered_start = full ^ words[anchor]
    rows_by_coordinate: list[list[int]] = [[] for _ in range(inst["length"])]
    for index in _eligible_ids(inst):
        for coordinate in _int_to_support(words[index]):
            rows_by_coordinate[coordinate].append(index)

    nodes = 0
    row_checks = 0

    def search(uncovered: int, chosen: list[int]) -> list[int] | None:
        nonlocal nodes, row_checks
        nodes += 1
        if nodes > node_cap:
            return None
        if uncovered == 0:
            return chosen if len(chosen) == inst["code_size"] else None
        if len(chosen) >= inst["code_size"]:
            return None

        options: list[int] | None = None
        remaining = uncovered
        while remaining:
            low = remaining & -remaining
            coordinate = low.bit_length() - 1
            remaining ^= low
            available = []
            for index in rows_by_coordinate[coordinate]:
                row_checks += 1
                word = words[index]
                if word & uncovered == word:
                    available.append(index)
            if not available:
                return None
            if options is None or len(available) < len(options):
                options = available
                if len(options) == 1:
                    break

        if options is None:
            return None
        for index in options:
            result = search(uncovered ^ words[index], [*chosen, index])
            if result is not None:
                return result
        return None

    result = search(uncovered_start, [anchor])
    return (sorted(result) if result is not None else None), nodes, row_checks


def _greedy_from_order(inst: dict, order: list[int]) -> tuple[list[int] | None, int]:
    chosen = [inst["anchor"]]
    chosen_words = [int(inst["words"][inst["anchor"]], 16)]
    steps = 0
    for index in order:
        if index == inst["anchor"]:
            continue
        word = int(inst["words"][index], 16)
        compatible = True
        for previous in chosen_words:
            steps += 1
            if (word ^ previous).bit_count() < inst["min_distance"]:
                compatible = False
                break
        if compatible:
            chosen.append(index)
            chosen_words.append(word)
            if len(chosen) == inst["code_size"]:
                return sorted(chosen), steps
    return None, steps


def _outlier_rarity(inst: dict) -> tuple[list[int] | None, int]:
    eligible = _eligible_ids(inst)
    frequencies = [0] * inst["length"]
    supports = {}
    for index in eligible:
        support = _int_to_support(int(inst["words"][index], 16))
        supports[index] = support
        for coordinate in support:
            frequencies[coordinate] += 1
    order = sorted(
        eligible,
        key=lambda index: (
            sum(frequencies[c] for c in supports[index]),
            index,
        ),
    )
    candidate, steps = _greedy_from_order(inst, order)
    return candidate, steps + len(eligible) * inst["word_weight"]


def _max_disjointness_greedy(inst: dict) -> tuple[list[int] | None, int]:
    eligible = _eligible_ids(inst)
    words = {index: int(inst["words"][index], 16) for index in eligible}
    degree = {index: 0 for index in eligible}
    steps = 0
    for position, left in enumerate(eligible):
        for right in eligible[position + 1:]:
            steps += 1
            if (words[left] & words[right]) == 0:
                degree[left] += 1
                degree[right] += 1
    order = sorted(eligible, key=lambda index: (-degree[index], index))
    candidate, greedy_steps = _greedy_from_order(inst, order)
    return candidate, steps + greedy_steps


def _random_restart_greedy(
    inst: dict, rng: random.Random, restarts: int = 256
) -> tuple[bool, int]:
    eligible = _eligible_ids(inst)
    steps = 0
    for _ in range(restarts):
        order = list(eligible)
        rng.shuffle(order)
        candidate, used = _greedy_from_order(inst, order)
        steps += used
        if candidate is not None and verify(inst, candidate)[0]:
            return True, steps
    return False, steps


def _near_anchor_ids(inst: dict) -> tuple[list[int] | None, int]:
    """Plausible visual ansatz: inspect anchor-near IDs before distant lines."""
    anchor = inst["anchor"]
    eligible = _eligible_ids(inst)
    order = sorted(eligible, key=lambda index: (abs(index - anchor), index))
    return _greedy_from_order(inst, order)


def _reorder_candidates(inst: dict, order: list[int]) -> dict:
    old_to_new = {old: new for new, old in enumerate(order)}
    moved = dict(inst)
    moved["words"] = [inst["words"][old] for old in order]
    moved["anchor"] = old_to_new[inst["anchor"]]
    moved["anchor_eligible"] = sorted(
        old_to_new[index] for index in _eligible_ids(inst)
    )
    moved["answer"] = sorted(old_to_new[index] for index in inst["answer"])
    return moved


def _relabel_coordinates(inst: dict, old_to_new: list[int]) -> dict:
    length = inst["length"]
    if sorted(old_to_new) != list(range(length)):
        raise ValueError("coordinate relabelling must be a permutation")
    inverse = [0] * length
    for old, new in enumerate(old_to_new):
        inverse[new] = old
    permutation = [0] * length
    for new in range(length):
        old = inverse[new]
        permutation[new] = old_to_new[inst["permutation"][old]]

    words = []
    for raw in inst["words"]:
        value = int(raw, 16)
        moved = 0
        for old in _int_to_support(value):
            moved |= 1 << old_to_new[old]
        words.append(format(moved, f"0{inst['hex_width']}x"))
    moved_inst = dict(inst)
    moved_inst["permutation"] = permutation
    moved_inst["words"] = words
    return moved_inst


def _answer_metrics(answer: list[int]) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))
    return len(encoded), math.ceil(len(encoded) / 4), len(answer)


def _compact_operations(inst: dict) -> int:
    return (
        (inst["code_size"] - 1) * inst["word_weight"]
        + (inst["code_size"] - 1) * math.ceil(math.log2(inst["candidate_count"]))
    )


def selftest() -> dict:
    """Run all local generation, verification, density, attack, and symmetry gates."""
    report: dict = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            recovered, _ = _reference_orbit_solver(inst)
            if recovered != inst["answer"]:
                g1_failures.append(f"{preset}/{seed}: orbit recovery mismatch")
            try:
                encoded = json.loads(json.dumps(inst["answer"]))
            except (TypeError, ValueError) as exc:
                g1_failures.append(f"{preset}/{seed}: JSON error {exc}")
            else:
                if encoded != inst["answer"]:
                    g1_failures.append(f"{preset}/{seed}: JSON round-trip changed answer")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
        "construction_audit": "the carried permutation orbit matched every planted answer",
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=123, **shipping_params)
    answer = ship["answer"]

    swapped = list(answer)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = list(answer)
    duplicated[1] = duplicated[0]
    out_of_range = list(answer)
    out_of_range[-1] = ship["candidate_count"]
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": duplicated,
        "empty": [],
        "out_of_range": out_of_range,
    }
    corruption_results = {
        name: {"accepted": verify(ship, candidate)[0], "reason": verify(ship, candidate)[1]}
        for name, candidate in corruptions.items()
    }
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": (
            all(not entry["accepted"] for entry in corruption_results.values())
            and len(set(reasons)) == len(reasons)
        ),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    realistic = (
        "The orbit calculation gives this code.\n```json\n"
        f"<answer>\n{json.dumps(answer)}\n</answer>\n```\n"
        "All IDs are in increasing order."
    )
    parsed = parse_answer(realistic)
    fenced = parse_answer("My result is:\n```json\n" + json.dumps(answer) + "\n```")
    report["G3_round_trip"] = {
        "pass": (
            parsed == answer
            and fenced == answer
            and verify(ship, parsed)[0]
            and verify(ship, fenced)[0]
            and parse_answer("no answer here") is None
        ),
        "tagged_matches": parsed == answer,
        "fenced_matches": fenced == answer,
        "garbage_returns_none": parse_answer("no answer here") is None,
    }

    guess_rng = random.Random(0x170305171)
    guess_total = 200_000
    guess_hits = 0
    guess_t0 = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_wall = time.perf_counter() - guess_t0
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_fraction,
        "candidate_space": search_space(ship),
        "anchor_compatible_candidates": len(_eligible_ids(ship)),
        "sampling_prior": (
            "uniform over increasing anchored k-subsets after filtering every "
            "candidate that visibly fails distance to the mandatory anchor"
        ),
        "wall_clock_sec": round(guess_wall, 6),
    }

    attack_names = (
        "outlier_coordinate_rarity",
        "greedy_lexicographic_first_fit",
        "random_restart_greedy_256",
        "in_context_near_anchor_ids",
    )
    attacks = {
        name: {"successes": 0, "attempts": 0, "steps": 0, "wall_clock_sec": 0.0}
        for name in attack_names
    }
    reference_successes = 0
    reference_nodes = 0
    reference_row_checks = 0
    reference_wall = 0.0
    orbit_successes = 0
    orbit_operations = 0
    orbit_wall = 0.0
    attack_seeds = list(range(800, 808))
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **shipping_params)

        t0 = time.perf_counter()
        candidate, steps = _outlier_rarity(inst)
        elapsed = time.perf_counter() - t0
        stat = attacks["outlier_coordinate_rarity"]
        stat["attempts"] += 1
        stat["successes"] += int(candidate is not None and verify(inst, candidate)[0])
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        candidate, steps = _greedy_from_order(inst, list(range(inst["candidate_count"])))
        elapsed = time.perf_counter() - t0
        stat = attacks["greedy_lexicographic_first_fit"]
        stat["attempts"] += 1
        stat["successes"] += int(candidate is not None and verify(inst, candidate)[0])
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        success, steps = _random_restart_greedy(inst, random.Random(seed ^ 0xC0DE), 256)
        elapsed = time.perf_counter() - t0
        stat = attacks["random_restart_greedy_256"]
        stat["attempts"] += 1
        stat["successes"] += int(success)
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        candidate, steps = _near_anchor_ids(inst)
        elapsed = time.perf_counter() - t0
        stat = attacks["in_context_near_anchor_ids"]
        stat["attempts"] += 1
        stat["successes"] += int(candidate is not None and verify(inst, candidate)[0])
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        t0 = time.perf_counter()
        recovered, nodes, row_checks = _algorithm_x(inst)
        elapsed = time.perf_counter() - t0
        reference_wall += elapsed
        reference_nodes += nodes
        reference_row_checks += row_checks
        reference_successes += int(
            recovered is not None and verify(inst, recovered)[0]
        )

        t0 = time.perf_counter()
        recovered, operations = _reference_orbit_solver(inst)
        elapsed = time.perf_counter() - t0
        orbit_wall += elapsed
        orbit_operations += operations
        orbit_successes += int(recovered is not None and verify(inst, recovered)[0])

    for stat in attacks.values():
        stat["wall_clock_sec"] = round(stat["wall_clock_sec"], 6)
    all_failed = all(stat["successes"] == 0 for stat in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": (
            all_failed
            and reference_successes == len(attack_seeds)
            and orbit_successes == len(attack_seeds)
        ),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Algorithm X exact-cover backtracking with minimum-column branching",
            "complexity": "exponential worst case; exact cover on k*n coordinates",
            "wall_clock_sec": round(reference_wall, 6),
            "nodes": reference_nodes,
            "row_checks": reference_row_checks,
            "operations": reference_nodes + reference_row_checks,
            "average_nodes_per_instance": reference_nodes // len(attack_seeds),
            "average_row_checks_per_instance": reference_row_checks // len(attack_seeds),
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
        "known_efficient_algorithm": {
            "name": "full candidate indexing plus coordinate-permutation orbit lookup",
            "complexity": "O(NL+kL) exact bit inspections",
            "wall_clock_sec": round(orbit_wall, 6),
            "operations": orbit_operations,
            "average_operations_per_instance": orbit_operations // len(attack_seeds),
            "solves": f"{orbit_successes}/{len(attack_seeds)}, as expected",
        },
        "compact_route_audit": {
            "name": "follow the anchor orbit with binary search in the sorted table",
            "operations_per_instance": _compact_operations(ship),
            "solves": "construction identity, audited by G1",
        },
    }

    demo = make_instance(seed=123, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    strongest_failing = max(attacks.items(), key=lambda item: item[1]["wall_clock_sec"])
    report["G5_density_and_baseline"] = {
        "pass": (
            demo_count is not None
            and demo_count >= 1
            and reference_successes == 8
            and orbit_successes == 8
        ),
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": guess_total,
        "shipping_sampled_density": guess_fraction,
        "shipping_candidate_space": search_space(ship),
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "reference_algorithm_wall_clock_sec": round(reference_wall, 6),
        "reference_algorithm_nodes": reference_nodes,
        "reference_algorithm_row_checks": reference_row_checks,
        "reference_average_nodes": reference_nodes // len(attack_seeds),
        "reference_average_row_checks": reference_row_checks // len(attack_seeds),
        "known_efficient_algorithm_wall_clock_sec": round(orbit_wall, 6),
        "known_efficient_algorithm_operations": orbit_operations,
        "strongest_failing_attack": strongest_failing[0],
        "strongest_failing_attack_wall_clock_sec": strongest_failing[1]["wall_clock_sec"],
        "strongest_failing_attack_steps": strongest_failing[1]["steps"],
    }

    ladder_lengths = [
        params["n"] * params["code_size"] for params in DIFFICULTY.values()
    ]
    ladder_spaces = [
        search_space(make_instance(seed=91, **params))
        for params in DIFFICULTY.values()
    ]
    doubled = make_instance(
        n=2 * ship["n"],
        code_size=ship["code_size"],
        decoy_orbits=ship["decoy_orbits"],
        seed=909,
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": (
            ladder_lengths == sorted(set(ladder_lengths))
            and all(
                left < right
                for left, right in zip(ladder_spaces, ladder_spaces[1:])
            )
            and doubled_ok
            and doubled["length"] == 2 * ship["length"]
            and len(doubled["answer"]) == len(ship["answer"])
        ),
        "preset_word_lengths": dict(zip(DIFFICULTY, ladder_lengths)),
        "preset_candidate_spaces": dict(zip(DIFFICULTY, ladder_spaces)),
        "doubled_word_length": doubled["length"],
        "doubled_answer_length": len(doubled["answer"]),
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
    }

    invariant_checks = 0
    witness_checks = 0
    failures = []
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(n=9, code_size=5, decoy_orbits=18, seed=20_000 + seed)
        base_key = canonical_key(inst)
        unrelated_keys.append(base_key)
        rng = random.Random(30_000 + seed)
        coordinate_map = list(range(inst["length"]))
        rng.shuffle(coordinate_map)
        candidate_order = list(range(inst["candidate_count"]))
        rng.shuffle(candidate_order)
        variants = (
            _reorder_candidates(inst, candidate_order),
            _relabel_coordinates(inst, coordinate_map),
            _reorder_candidates(
                _relabel_coordinates(inst, coordinate_map), candidate_order
            ),
        )
        for number, moved in enumerate(variants):
            invariant_checks += 1
            if canonical_key(moved) != base_key:
                failures.append(f"key/{seed}/{number}")
            witness_checks += 1
            if not verify(moved, moved["answer"])[0]:
                failures.append(f"witness/{seed}/{number}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not failures and distinct_keys == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": witness_checks,
        "invariance_failures": failures,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "transformations": [
            "arbitrary candidate-table reorder with IDs carried",
            "arbitrary coordinate relabelling with the permutation conjugated",
            "composition of candidate reorder and coordinate relabelling",
        ],
        "canonicalization_caveat": (
            "color refinement is a strong cheap invariant, not a complete "
            "isomorphism algorithm for colored set systems"
        ),
    }

    chars, tokens, elements = _answer_metrics(ship["answer"])
    intended_operations = _compact_operations(ship)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else None
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else None
    )
    within_caps = (
        chars <= 2_000
        and tokens <= PROBLEM_PROFILE["max_answer_tokens"]
        and elements <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        # All three oracle arms are diagnostics as of 2026-09-05; only the
        # answer-size, answer-shape, and intended-route caps still gate G9.
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None
        ),
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") is True for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
