"""Verified problem generator for arXiv:2503.06377.

The family uses the paper's native ``X_5`` vectors.  A row ``s`` with five
entries -1 and five entries +1 encodes

    v(s) = (s/2, 0^10, (1/2,-1/2)) in A_9 (x) A_9 (x) A_1.

Definition 5.2 supplies a certified twelve-row affine equiangular set.  The
generator transports it through coordinate permutations and switching, then
adds same-distribution norm-three vectors.  It never searches for a witness.
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


TRACK = "B"


PROBLEM_PROFILE = {
    "native_domain": "geometry",
    "object_regime": "rational_exact",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "norm-3 vectors in the X_5 slice of an overlattice of A_9 + A_9 + A_1",
        "switching root",
        "coordinate permutations",
    ],
    "verification_operations": [
        "exact integer dot product of scaled rational vectors",
        "exact norm comparison",
        "exact candidate-vector membership",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Recognize the twelve-vector S_4 orbit from Definition 5.2 through its "
        "two conjugated coordinate symmetries; without that orbit structure one "
        "must perform the paper's generic maximum-compatible-subset search."
    ),
    "hardness_basis": (
        "Track B: Section 5 and Lemma 5.4 use a generic maximum-clique "
        "enumeration on 126 switching classes (151200 maxima); the local exact "
        "branch-and-bound and randomized degree-guided reference methods both "
        "start by computing 157500 exact scalar dot-product operations at the "
        "shipping preset (0.041 seconds mean in the final local audit, "
        "O(m^12+m^2 d) worst "
        "case for the exact target-12 search), whereas the compact route uses "
        "at most 300 permutation, lookup, and set-intersection steps and no "
        "exact arithmetic."
    ),
    "max_answer_tokens": 111,
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
        "A lexicographically sorted JSON matrix with exactly 12 distinct rows "
        "and 10 entries per row; every entry is -1 or 1, every row has five of "
        "each sign, every row is one of the displayed candidates, and no two "
        "rows are entrywise negatives (switching mates)."
    ),
    "bounds": {
        "rows": 12,
        "columns": 10,
        "entry_alphabet": [-1, 1],
        "negative_entries_per_row": 5,
        "candidate_count": "the displayed n, at most 252",
    },
}


DIFFICULTY = {
    "demo": {"n": 18, "crowding": 0},
    "easy": {"n": 126, "crowding": 1},
    "medium": {"n": 180, "crowding": 4},
    "hard": {"n": 240, "crowding": 5},
}

SHIPPING_DIFFICULTY = "easy"


STRUCTURAL_HINT = (
    "The target twelve vectors form one orbit under the displayed coordinate "
    "symmetries, up to switching mates."
)
PLACEBO_HINT = (
    "The target twelve vectors reward careful comparison of the displayed "
    "coordinate data and signs."
)


# Filled from the three isolated harden.py runs before the final self-test.
# Zero attempts means the provider failed before an oracle answer was scored;
# these arms are diagnostic and do not substitute for STEP 4's bare verdict.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0, "api_errors": 4},
    "hinted": {"solved": 0, "attempts": 0, "api_errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "api_errors": 4},
    "hinted_verdict": "blocked_api_key_limit",
}


NOTES = r"""
Definition 3.2 fixes Lambda and the switching root.  Definition 4.1 and
Lemma 4.3 give the exact X_5 coordinate formula and inner product
|I intersect J|-2.
Definition 5.2 lists the twelve five-subsets used here, and Lemma 5.3 proves
that they form a maximum affine equiangular set.  Lemma 5.4 is the easy-regime
warning and fixes the track: the authors construct a 126-element compatibility
graph in Magma, enumerate all 151200 size-twelve maxima, and prove transitivity.
Thus a domain-standard exact search exists and Track A would be false.

Generation starts with Definition 5.2's twelve rows, samples a uniform
coordinate permutation and independent switching mates, and adds uniformly
sampled rows from the same 252-row X_5 distribution.  The coordinate
permutation conjugates the two displayed S_4 generators.  The certificate is
carried through these transformations; no compatibility search is used.

The degree outlier, deterministic greedy, and 256 random-start greedy trials
are defeated by the crowding of the X_5 compatibility relation.  The tempting
by-hand shortcut of concatenating three orbits of the displayed order-four
generator fails because it ignores the transposition generator.  Exact
branch-and-bound and a randomized top-two-degree variant both solve after first
constructing the full compatibility graph; they are deliberately reported as
successful Track-B reference algorithms, not as failed attacks.
""".strip()


# Definition 5.2, converted from the paper's 1-based notation to 0-based sets.
_I0 = (
    frozenset((1, 2, 3, 4, 6)),
    frozenset((1, 2, 3, 5, 7)),
    frozenset((1, 2, 3, 8, 9)),
    frozenset((0, 2, 3, 7, 9)),
    frozenset((0, 2, 3, 4, 8)),
    frozenset((0, 2, 3, 5, 6)),
    frozenset((0, 1, 3, 6, 8)),
    frozenset((0, 1, 3, 5, 9)),
    frozenset((0, 1, 3, 4, 7)),
    frozenset((0, 1, 2, 4, 5)),
    frozenset((0, 1, 2, 7, 8)),
    frozenset((0, 1, 2, 6, 9)),
)


def _cycle_map(cycle: tuple[int, ...]) -> tuple[int, ...]:
    out = list(range(4))
    for a, b in zip(cycle, cycle[1:] + cycle[:1]):
        out[a] = b
    return tuple(out)


_FOUR_CYCLES = tuple(
    _cycle_map(c)
    for c in (
        (0, 1, 2, 3),
        (0, 2, 1, 3),
        (0, 1, 3, 2),
        (0, 2, 3, 1),
        (0, 3, 1, 2),
        (0, 3, 2, 1),
    )
)


def _compose(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, ...]:
    """The permutation a after b."""

    return tuple(a[b[i]] for i in range(len(a)))


def _inverse(p: tuple[int, ...]) -> tuple[int, ...]:
    out = [0] * len(p)
    for i, j in enumerate(p):
        out[j] = i
    return tuple(out)


def _s4_coordinate_action(sigma: tuple[int, ...]) -> tuple[int, ...]:
    """The ten-coordinate action described immediately after Definition 5.2."""

    inv = _inverse(sigma)
    out = list(range(10))
    for i in range(4):
        out[i] = sigma[i]
    for pos, cyc in enumerate(_FOUR_CYCLES, 4):
        conjugate = _compose(_compose(sigma, cyc), inv)
        out[pos] = 4 + _FOUR_CYCLES.index(conjugate)
    return tuple(out)


_STANDARD_GENERATORS = (
    _s4_coordinate_action((1, 0, 2, 3)),
    _s4_coordinate_action((1, 2, 3, 0)),
)


def _row_from_negative_set(indices: set[int] | frozenset[int]) -> tuple[int, ...]:
    return tuple(-1 if i in indices else 1 for i in range(10))


_ALL_ROWS = tuple(
    _row_from_negative_set(frozenset(c))
    for c in itertools.combinations(range(10), 5)
)


def _move_row(row: tuple[int, ...], permutation: tuple[int, ...]) -> tuple[int, ...]:
    """Move source coordinate i to destination permutation[i]."""

    out = [0] * 10
    for i, value in enumerate(row):
        out[permutation[i]] = value
    return tuple(out)


def _conjugate(permutation: tuple[int, ...], by: tuple[int, ...]) -> tuple[int, ...]:
    return _compose(_compose(by, permutation), _inverse(by))


def _dot(a: tuple[int, ...] | list[int], b: tuple[int, ...] | list[int]) -> int:
    return sum(x * y for x, y in zip(a, b))


def _compatible(a: tuple[int, ...] | list[int], b: tuple[int, ...] | list[int]) -> bool:
    # The actual affine inner product is dot(a,b)/4 + 1/2, so this is exactly
    # the condition that it belongs to {0,1}.
    return abs(_dot(a, b)) == 2


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Plant a transformed copy of Definition 5.2 among X_5 decoys."""

    if not isinstance(n, int) or isinstance(n, bool) or not 12 <= n <= 252:
        raise ValueError("n must be an integer from 12 through 252")
    crowding = int(params.pop("crowding", 0))
    if params:
        raise TypeError(f"unknown parameters: {sorted(params)}")
    if crowding < 0:
        raise ValueError("crowding must be nonnegative")
    rng = random.Random(seed)

    coordinate_permutation = list(range(10))
    rng.shuffle(coordinate_permutation)
    coordinate_permutation_t = tuple(coordinate_permutation)

    planted: set[tuple[int, ...]] = set()
    for indices in _I0:
        moved = _move_row(_row_from_negative_set(indices), coordinate_permutation_t)
        if rng.randrange(2):
            moved = tuple(-x for x in moved)
        planted.add(moved)
    if len(planted) != 12:
        raise AssertionError("the transported Definition 5.2 orbit collapsed")

    symmetries = [
        list(_conjugate(generator, coordinate_permutation_t))
        for generator in _STANDARD_GENERATORS
    ]

    # ``crowding`` controls how many candidate slots are spent on the second
    # orientation of a switching class before the 126 classes are exhausted.
    # This adds exact same-distribution near-misses without changing any row's
    # marginal distribution.
    all_classes = sorted({_line_class(row) for row in _ALL_ROWS})
    planted_by_class = {_line_class(row): row for row in planted}
    distinct_classes = min(126, max(12, n - crowding))
    distinct_classes = max(distinct_classes, math.ceil(n / 2))
    remaining_classes = [row for row in all_classes if row not in planted_by_class]

    # Make the planted orbit the unique *complete* twelve-element orbit of the
    # displayed group.  This is the short Track-B route: orbit membership uses
    # permutations and exact lookups, while a generic solver still sees the
    # paper's maximum-compatible-subset problem.  At least one member of every
    # competing 12-orbit is held out before the remaining decoys are sampled.
    forced_out: set[tuple[int, ...]] = set()
    if 126 - distinct_classes >= 3:
        seen_classes: set[tuple[int, ...]] = set()
        for cls in all_classes:
            if cls in seen_classes or cls in planted_by_class:
                continue
            orbit = _group_orbit(cls, symmetries)
            seen_classes.update(orbit)
            if len(orbit) == 12:
                choices = sorted(orbit - set(planted_by_class))
                if choices:
                    forced_out.add(rng.choice(choices))
    selectable = [row for row in remaining_classes if row not in forced_out]
    rng.shuffle(selectable)
    selected_classes = list(planted_by_class) + selectable[: distinct_classes - 12]
    oriented: dict[tuple[int, ...], tuple[int, ...]] = {}
    for cls in selected_classes:
        if cls in planted_by_class:
            oriented[cls] = planted_by_class[cls]
        elif rng.randrange(2):
            oriented[cls] = tuple(-x for x in cls)
        else:
            oriented[cls] = cls
    candidates = list(oriented.values())
    duplicate_classes = selected_classes[:]
    rng.shuffle(duplicate_classes)
    for cls in duplicate_classes[: n - distinct_classes]:
        candidates.append(tuple(-x for x in oriented[cls]))
    rng.shuffle(candidates)

    answer = [list(row) for row in sorted(planted)]
    return {
        "n": n,
        "candidates": [list(row) for row in candidates],
        "symmetries": symmetries,
        "answer": answer,
    }


def render(inst: dict) -> str:
    """Render the complete exact-coordinate witness problem."""

    rows = "\n".join(
        f"  {i:03d}: " + " ".join(str(x) for x in row)
        for i, row in enumerate(inst["candidates"])
    )
    syms = "\n".join(
        f"  g{i + 1}: " + " ".join(str(x) for x in permutation)
        for i, permutation in enumerate(inst["symmetries"])
    )
    statement = f"""Exact affine equiangular vectors in the A9+A9+A1 lattice

There are {inst['n']} displayed candidate sign rows s.  Every row has length 10,
has exactly five -1 entries and five +1 entries, and encodes the rational vector

    v(s) = (s_0/2,...,s_9/2, 0,...,0, 1/2,-1/2) in Q^22,

where the middle block contains ten zeros.  The switching root is
r=(0,...,0,1,-1).  Thus v(s) has squared norm 3 and v(s) dot r = 1.

Find exactly 12 DISTINCT displayed rows such that every two distinct returned
rows a,b satisfy a dot b = -2 or +2.  Equivalently, their encoded rational
vectors have inner product 0 or 1, so they form an affine equiangular set of
norm 3 with respect to r.  A solution is guaranteed.

The two auxiliary coordinate symmetries below are permutations of positions
0,...,9.  In a permutation p, the entry originally at position i moves to
position p[i].  A row and its entrywise negative are switching mates.  These
symmetries are instance data, but your answer is accepted solely by the exact
conditions above.

Coordinate symmetries:
{syms}

Candidate rows (the numeric labels are only for reading; return rows, not labels):
{rows}

Return a JSON matrix of 12 rows, with rows in increasing lexicographic order.
Each row must contain exactly ten integers, all -1 or 1.  Order within a row is
the displayed coordinate order; rows may not repeat.

Give your final answer inside <answer></answer> tags, as a JSON matrix.
Example format: <answer>[[ -1,-1,-1,-1,-1,1,1,1,1,1 ],[ -1,-1,-1,-1,1,-1,1,1,1,1 ]]</answer>
The example only illustrates syntax and intentionally has two rows, not twelve.
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the tagged JSON matrix, tolerating prose and Markdown fences."""

    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
    body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        # Models sometimes copy the candidates' human-readable ``+1`` spelling.
        # Unary plus is unambiguous here but is not legal JSON, so tolerate it
        # without relaxing any shape or value condition in verify().
        normalized = re.sub(r"(?<![A-Za-z0-9_.])\+(?=\d)", "", body)
        try:
            value = json.loads(normalized)
        except (TypeError, ValueError):
            return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid twelve-vector coordinate certificate exactly."""

    if not isinstance(answer, list):
        return False, "answer_not_a_matrix"
    if not answer:
        return False, "empty_matrix"
    if len(answer) != 12:
        return False, f"wrong_row_count:{len(answer)}"
    rows: list[tuple[int, ...]] = []
    for i, row in enumerate(answer):
        if not isinstance(row, list) or len(row) != 10:
            return False, f"wrong_row_shape:{i}"
        if any(type(value) is not int or value not in (-1, 1) for value in row):
            return False, f"invalid_entry:{i}"
        if sum(value == -1 for value in row) != 5:
            return False, f"unbalanced_row:{i}"
        rows.append(tuple(row))
    if rows != sorted(rows):
        return False, "rows_not_lexicographic"
    if len(set(rows)) != 12:
        return False, "duplicate_rows"
    candidate_set = {tuple(row) for row in inst.get("candidates", [])}
    for i, row in enumerate(rows):
        if row not in candidate_set:
            return False, f"row_not_displayed:{i}"
    for i in range(12):
        for j in range(i):
            dot = _dot(rows[i], rows[j])
            if dot not in (-2, 2):
                return False, f"bad_inner_product:{j},{i}:{dot}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample a structurally admissible displayed twelve-set.

    A row and its entrywise negative have dot product -10, so a solver gets for
    free that the pair cannot occur together.  Rejection sampling from uniform
    displayed twelve-subsets conditions on that obvious rule without favoring
    the planted orbit.
    """

    while True:
        rows = rng.sample(inst["candidates"], 12)
        if len({_line_class(row) for row in rows}) == 12:
            return [list(row) for row in sorted(rows)]


def search_space(inst: dict) -> int:
    """Exact size of the no-switching-mates certificate language.

    If a switching class occurs with multiplicity one or two, selecting that
    class contributes respectively one or two possible displayed rows.  The
    answer is the degree-12 coefficient of the corresponding product.
    """

    multiplicities: dict[tuple[int, ...], int] = {}
    for row in inst["candidates"]:
        cls = _line_class(row)
        multiplicities[cls] = multiplicities.get(cls, 0) + 1
    coefficients = [1] + [0] * 12
    for multiplicity in multiplicities.values():
        for degree in range(12, 0, -1):
            coefficients[degree] += multiplicity * coefficients[degree - 1]
    return coefficients[12]


def enumerate_all(inst: dict) -> int | None:
    """Count witnesses on hand-scale instances and cap larger work."""

    candidates = inst["candidates"]
    if len(candidates) > 24 or math.comb(len(candidates), 12) > 250_000:
        return None
    count = 0
    for indices in itertools.combinations(range(len(candidates)), 12):
        rows = [candidates[i] for i in indices]
        if all(
            _compatible(rows[i], rows[j])
            for i in range(12)
            for j in range(i)
        ):
            count += 1
    return count


def _line_class(row: tuple[int, ...] | list[int]) -> tuple[int, ...]:
    row_t = tuple(row)
    negative = tuple(-x for x in row_t)
    return min(row_t, negative)


def _act_on_line(
    row: tuple[int, ...], permutation: tuple[int, ...] | list[int]
) -> tuple[int, ...]:
    return _line_class(_move_row(row, tuple(permutation)))


def _group_orbit(
    row: tuple[int, ...], symmetries: list[list[int]]
) -> frozenset[tuple[int, ...]]:
    start = _line_class(row)
    orbit = {start}
    pending = [start]
    while pending:
        current = pending.pop()
        for symmetry in symmetries:
            moved = _act_on_line(current, symmetry)
            if moved not in orbit:
                orbit.add(moved)
                pending.append(moved)
    return frozenset(orbit)


def canonical_key(inst: dict) -> str:
    """A switching-, coordinate-, and input-order invariant structural key.

    Full isomorphism of arbitrary induced compatibility structures is not
    attempted.  The stable colour-refinement and group-orbit profile used here
    is the strongest cheap invariant needed for duplicate detection.
    """

    multiplicity: dict[tuple[int, ...], int] = {}
    for raw in inst["candidates"]:
        cls = _line_class(raw)
        multiplicity[cls] = multiplicity.get(cls, 0) + 1
    vertices = sorted(multiplicity)
    neighbours: dict[tuple[int, ...], tuple[tuple[int, ...], ...]] = {}
    for vertex in vertices:
        neighbours[vertex] = tuple(
            other
            for other in vertices
            if other != vertex and _compatible(vertex, other)
        )

    orbit_data: dict[tuple[int, ...], tuple[int, tuple[int, ...]]] = {}
    orbit_profiles = []
    seen: set[tuple[int, ...]] = set()
    symmetries = inst.get("symmetries", [])
    for vertex in vertices:
        orbit = _group_orbit(vertex, symmetries)
        profile = (len(orbit), tuple(sorted(multiplicity.get(x, 0) for x in orbit)))
        orbit_data[vertex] = profile
        if vertex not in seen:
            seen.update(orbit)
            orbit_profiles.append(profile)

    signatures = {
        vertex: (
            multiplicity[vertex],
            sum(multiplicity[x] for x in neighbours[vertex]),
            orbit_data[vertex],
        )
        for vertex in vertices
    }
    colours: dict[tuple[int, ...], int] = {}
    palette = {signature: i for i, signature in enumerate(sorted(set(signatures.values())))}
    for vertex in vertices:
        colours[vertex] = palette[signatures[vertex]]
    for _ in range(len(vertices)):
        refined = {
            vertex: (
                colours[vertex],
                tuple(sorted(colours[x] for x in neighbours[vertex])),
            )
            for vertex in vertices
        }
        palette = {signature: i for i, signature in enumerate(sorted(set(refined.values())))}
        new_colours = {vertex: palette[refined[vertex]] for vertex in vertices}
        if new_colours == colours:
            break
        colours = new_colours
    payload = {
        "colour_histogram": sorted(
            (colour, sum(1 for value in colours.values() if value == colour))
            for colour in set(colours.values())
        ),
        "vertex_profiles": sorted(
            (
                colours[vertex],
                multiplicity[vertex],
                sum(multiplicity[x] for x in neighbours[vertex]),
                orbit_data[vertex],
            )
            for vertex in vertices
        ),
        "orbit_profiles": sorted(orbit_profiles),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Increase the decoy haystack while the 12-by-10 witness stays fixed."""

    current = int(params.get("n", 12))
    result = {k: v for k, v in params.items() if k != "_preset"}
    if current < 180:
        result["n"] = 180
        result["crowding"] = max(int(result.get("crowding", 0)), 4)
        return result
    # At n=252 every switching class occurs in both orientations, so all seeds
    # become isomorphic.  Stop at 249: it is harder than the named hard preset
    # while retaining three seed-dependent singleton classes and real diversity.
    if current < 249:
        result["n"] = 249
        result["crowding"] = max(int(result.get("crowding", 0)), 5)
        return result
    return None


def _answer_from_indices(inst: dict, indices: list[int]) -> list[list[int]]:
    return [list(row) for row in sorted(tuple(inst["candidates"][i]) for i in indices)]


def _compatibility_bits(inst: dict) -> tuple[list[int], int]:
    candidates = [tuple(row) for row in inst["candidates"]]
    adjacency = [0] * len(candidates)
    scalar_operations = 0
    for i in range(len(candidates)):
        for j in range(i):
            dot = 0
            for x, y in zip(candidates[i], candidates[j]):
                dot += x * y
                scalar_operations += 2
            if abs(dot) == 2:
                adjacency[i] |= 1 << j
                adjacency[j] |= 1 << i
    return adjacency, scalar_operations


def _reference_search(inst: dict) -> tuple[object | None, dict]:
    """Generic exact branch-and-bound for a 12-vector compatible subset."""

    started = time.perf_counter()
    adjacency, scalar_operations = _compatibility_bits(inst)
    nodes = 0
    branches = 0

    def visit(chosen: list[int], candidates: int) -> list[int] | None:
        nonlocal nodes, branches
        nodes += 1
        need = 12 - len(chosen)
        if need == 0:
            return chosen
        if candidates.bit_count() < need:
            return None
        ordered: list[int] = []
        bits = candidates
        while bits:
            bit = bits & -bits
            vertex = bit.bit_length() - 1
            bits -= bit
            ordered.append(vertex)
        ordered.sort(
            key=lambda vertex: (adjacency[vertex] & candidates).bit_count(),
            reverse=True,
        )
        remaining = candidates
        for vertex in ordered:
            bit = 1 << vertex
            if not remaining & bit:
                continue
            branches += 1
            result = visit(chosen + [vertex], remaining & adjacency[vertex])
            if result is not None:
                return result
            remaining &= ~bit
            if remaining.bit_count() < need:
                break
        return None

    indices = visit([], (1 << len(adjacency)) - 1)
    elapsed = time.perf_counter() - started
    answer = None if indices is None else _answer_from_indices(inst, indices)
    return answer, {
        "nodes": nodes,
        "branches": branches,
        "scalar_operations": scalar_operations + nodes + branches,
        "wall_clock_sec": elapsed,
    }


def _symmetry_route(inst: dict) -> tuple[object | None, dict]:
    """Find a compatible transitive S4 orbit without arithmetic dot products.

    Compatibility of balanced sign rows is equivalent to their negative-entry
    sets meeting in two or three coordinates.  Because each candidate orbit is
    transitive and the relation is invariant under the supplied permutations,
    it is enough to compare one representative with the other eleven members.
    """

    by_class: dict[tuple[int, ...], tuple[int, ...]] = {}
    for raw in inst["candidates"]:
        row = tuple(raw)
        by_class.setdefault(_line_class(row), row)
    all_classes = sorted({_line_class(row) for row in _ALL_ROWS})
    seen: set[tuple[int, ...]] = set()
    permutation_applications = 0
    membership_lookups = 0
    intersection_tests = 0
    complete_twelve_orbits = 0
    for start in all_classes:
        if start in seen:
            continue
        orbit = {start}
        pending = [start]
        while pending:
            current = pending.pop()
            for symmetry in inst["symmetries"]:
                permutation_applications += 1
                moved = _act_on_line(current, symmetry)
                if moved not in orbit:
                    orbit.add(moved)
                    pending.append(moved)
        seen.update(orbit)
        if len(orbit) == 12:
            complete_twelve_orbits += 1
            membership_lookups += 12
            ordered_orbit = sorted(orbit)
            if not all(row in by_class for row in ordered_orbit):
                continue
            base_negative = {i for i, value in enumerate(ordered_orbit[0]) if value < 0}
            compatible = True
            for other in ordered_orbit[1:]:
                intersection_tests += 1
                other_negative = {i for i, value in enumerate(other) if value < 0}
                if len(base_negative & other_negative) not in (2, 3):
                    compatible = False
                    break
            if compatible:
                answer = [list(by_class[row]) for row in ordered_orbit]
                answer.sort()
                return answer, {
                    "complete_twelve_orbits_examined": complete_twelve_orbits,
                    "permutation_applications": permutation_applications,
                    "membership_lookups": membership_lookups,
                    "set_intersection_tests": intersection_tests,
                    "exact_arithmetic_operations": 0,
                }
    return None, {
        "complete_twelve_orbits_examined": complete_twelve_orbits,
        "permutation_applications": permutation_applications,
        "membership_lookups": membership_lookups,
        "set_intersection_tests": intersection_tests,
        "exact_arithmetic_operations": 0,
    }


def _degree_order(inst: dict) -> tuple[list[int], list[int]]:
    adjacency, _ = _compatibility_bits(inst)
    order = sorted(
        range(len(adjacency)),
        key=lambda i: ((adjacency[i]).bit_count(), tuple(inst["candidates"][i])),
        reverse=True,
    )
    return adjacency, order


def _attack_outlier(inst: dict) -> object:
    _, order = _degree_order(inst)
    return _answer_from_indices(inst, order[:12])


def _attack_greedy(inst: dict, rng: random.Random | None = None) -> object:
    adjacency, _ = _degree_order(inst)
    return _greedy_from_adjacency(inst, adjacency, rng=rng)


def _greedy_from_adjacency(
    inst: dict,
    adjacency: list[int],
    rng: random.Random | None = None,
    random_first: bool = False,
    top_k: int = 1,
) -> object:
    """Degree-guided compatible-set heuristic on a precomputed graph."""

    available = (1 << len(adjacency)) - 1
    chosen: list[int] = []
    while available and len(chosen) < 12:
        vertices = [i for i in range(len(adjacency)) if available & (1 << i)]
        if random_first and not chosen:
            if rng is None:
                raise ValueError("random_first requires an rng")
            vertex = rng.choice(vertices)
        else:
            ranked = sorted(
                vertices,
                key=lambda i: (
                    (adjacency[i] & available).bit_count(),
                    tuple(inst["candidates"][i]),
                ),
                reverse=True,
            )
            cutoff = min(top_k, len(ranked))
            if rng is None or cutoff == 1:
                vertex = ranked[0]
            else:
                vertex = rng.choice(ranked[:cutoff])
        chosen.append(vertex)
        available &= adjacency[vertex]
    return _answer_from_indices(inst, chosen)


def _attack_random_restarts(inst: dict, seed: int, restarts: int = 256) -> object:
    """Try random initial vertices followed by the obvious max-degree rule."""

    rng = random.Random(seed)
    adjacency, _ = _compatibility_bits(inst)
    last: object = []
    for _ in range(restarts):
        last = _greedy_from_adjacency(
            inst, adjacency, rng=rng, random_first=True, top_k=1
        )
        if verify(inst, last)[0]:
            return last
    return last


def _reference_randomized_top_two(inst: dict, seed: int, restarts: int = 64) -> object:
    """A successful coded heuristic, reported as Track-B reference evidence."""

    rng = random.Random(seed)
    adjacency, _ = _compatibility_bits(inst)
    last: object = []
    for _ in range(restarts):
        last = _greedy_from_adjacency(inst, adjacency, rng=rng, top_k=2)
        if verify(inst, last)[0]:
            return last
    return last


def _attack_three_cyclic_orbits(inst: dict) -> object:
    """By-hand ansatz: join three 4-orbits, ignoring the other generator."""

    candidates = [tuple(row) for row in inst["candidates"]]
    by_class = {_line_class(row): row for row in candidates}
    cyclic = inst["symmetries"][1]
    used: set[tuple[int, ...]] = set()
    chosen: list[tuple[int, ...]] = []
    for seed in sorted(candidates):
        cls = _line_class(seed)
        if cls in used:
            continue
        orbit = []
        current = cls
        for _ in range(4):
            if current not in orbit:
                orbit.append(current)
            current = _act_on_line(current, cyclic)
        used.update(orbit)
        if len(orbit) == 4 and all(row in by_class for row in orbit):
            chosen.extend(by_class[row] for row in orbit)
        if len(chosen) >= 12:
            break
    return [list(row) for row in sorted(chosen[:12])]


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(x) for x in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_answer_atoms(x) for x in value)
    return 1


def _transformed_copy(
    inst: dict,
    seed: int,
    *,
    reorder: bool = True,
    relabel: bool = True,
    switch: bool = True,
    reorder_symmetries: bool = False,
) -> tuple[dict, list[list[int]]]:
    """Apply any requested problem-preserving relabellings."""

    rng = random.Random(seed)
    coordinate = list(range(10))
    if relabel:
        rng.shuffle(coordinate)
    coordinate_t = tuple(coordinate)

    # Switch an entire unoriented line class at once.  When both orientations
    # occur this swaps them instead of collapsing two labelled candidates.
    flip_class: dict[tuple[int, ...], bool] = {}
    for row in inst["candidates"]:
        flip_class.setdefault(
            _line_class(row), bool(rng.randrange(2)) if switch else False
        )

    def carry(raw: list[int]) -> list[int]:
        row = tuple(raw)
        if flip_class[_line_class(row)]:
            row = tuple(-x for x in row)
        return list(_move_row(row, coordinate_t))

    candidates = [carry(row) for row in inst["candidates"]]
    if reorder:
        rng.shuffle(candidates)
    answer = sorted(carry(row) for row in inst["answer"])
    symmetries = [
        list(_conjugate(tuple(symmetry), coordinate_t))
        for symmetry in inst["symmetries"]
    ]
    if reorder_symmetries:
        rng.shuffle(symmetries)
    changed = {
        "n": inst["n"],
        "candidates": candidates,
        "symmetries": symmetries,
        "answer": answer,
    }
    return changed, answer


def selftest() -> dict:
    """Run all mandatory correctness, density, attack, scaling, and size gates."""

    report: dict[str, object] = {}

    # G1: every named preset, several independent seeds, including JSON safety.
    g1_attempts = 0
    g1_failures = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 19):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            g1_attempts += 1
            if not ok or not json_ok:
                g1_failures.append({"preset": preset, "seed": seed, "reason": reason})
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "verified": g1_attempts - len(g1_failures),
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20250306377, **shipping_params)
    planted = inst["answer"]

    # G2: five perturbation classes, each required to reach a distinct reason.
    corruptions: dict[str, object] = {}
    corruptions["empty"] = []
    corruptions["drop"] = planted[:-1]
    swapped = [row[:] for row in planted]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    corruptions["swap"] = swapped
    duplicate = [row[:] for row in planted]
    duplicate[-1] = duplicate[0][:]
    duplicate.sort()
    corruptions["duplicate"] = duplicate
    invalid = [row[:] for row in planted]
    invalid[0][0] = 2
    corruptions["out_of_range"] = invalid
    reasons = {}
    for name, answer in corruptions.items():
        ok, reason = verify(inst, answer)
        reasons[name] = {"rejected": not ok, "reason": reason}
    distinct_reasons = len({entry["reason"].split(":", 1)[0] for entry in reasons.values()})
    report["G2_rejects_corruption"] = {
        "pass": all(entry["rejected"] for entry in reasons.values()) and distinct_reasons == 5,
        "distinct_reasons": distinct_reasons,
        "cases": reasons,
    }

    # G3: realistic prose plus a fenced tagged payload.
    model_style = (
        "I used the exact dot-product condition.\n\n"
        "<answer>```json\n"
        + json.dumps(planted)
        + "\n```</answer>\nThe rows are sorted as requested."
    )
    parsed = parse_answer(model_style)
    report["G3_round_trip"] = {
        "pass": parsed == planted,
        "parsed_matches": parsed == planted,
    }

    # G4 and the shipping-density part of G5 use the declared structure-aware
    # language: unordered twelve-subsets of already valid displayed rows.
    guess_rng = random.Random(63077)
    samples = 200_000
    hits = 0
    started = time.perf_counter()
    for _ in range(samples):
        candidate = random_candidate(inst, guess_rng)
        if verify(inst, candidate)[0]:
            hits += 1
    guess_seconds = time.perf_counter() - started
    empirical_probability = hits / samples
    # Lemma 5.4 reports exactly 151,200 maximum cliques on the complete set of
    # 126 switching classes.  Removing classes cannot create cliques, and each
    # doubled class can multiply the orientations of a line-class clique by at
    # most two.  This deliberately loose theorem-backed bound turns the zero-hit
    # observation into an actual probability bound rather than a confidence
    # claim based only on 200,000 trials.
    multiplicities: dict[tuple[int, ...], int] = {}
    for row in inst["candidates"]:
        cls = _line_class(row)
        multiplicities[cls] = multiplicities.get(cls, 0) + 1
    doubled_classes = sum(value == 2 for value in multiplicities.values())
    valid_answer_upper_bound = 151_200 * (2 ** min(12, doubled_classes))
    probability_upper_bound = valid_answer_upper_bound / search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": (
            samples >= 200_000
            and empirical_probability < 1e-6
            and probability_upper_bound < 1e-6
        ),
        "hits": hits,
        "total": samples,
        "empirical_probability": empirical_probability,
        "structure_aware_space": search_space(inst),
        "paper_maximum_cliques": 151_200,
        "doubled_switching_classes": doubled_classes,
        "valid_answer_upper_bound": valid_answer_upper_bound,
        "certified_probability_upper_bound": probability_upper_bound,
        "wall_clock_sec": guess_seconds,
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)

    # G6 is measured before G5 so the latter can report a real strongest-attack
    # cost at exactly the shipping preset.
    attack_seeds = tuple(range(4100, 4108))
    attack_names = (
        "outlier_top_12_degrees",
        "greedy_max_compatible_degree",
        "random_start_then_greedy_256",
        "three_cyclic_orbits_by_hand_ansatz",
    )
    attack_results = {name: {"successes": 0, "attempts": 0} for name in attack_names}
    strongest_attack_seconds = 0.0
    strongest_attack_iterations = 0
    reference_successes = 0
    reference_nodes = []
    reference_operations = []
    reference_seconds = []
    compact_successes = 0
    compact_steps = []
    top_two_successes = 0
    top_two_seconds = []
    for seed in attack_seeds:
        trial = make_instance(seed=seed, **shipping_params)
        attempts = (
            _attack_outlier(trial),
            _attack_greedy(trial),
            _attack_random_restarts(trial, seed ^ 0x5A17, 256),
            _attack_three_cyclic_orbits(trial),
        )
        for name, answer in zip(attack_names, attempts):
            attack_results[name]["attempts"] += 1
            attack_results[name]["successes"] += int(verify(trial, answer)[0])
        t0 = time.perf_counter()
        _attack_random_restarts(trial, seed ^ 0xA55A, 256)
        strongest_attack_seconds += time.perf_counter() - t0
        strongest_attack_iterations += 256

        t0 = time.perf_counter()
        top_two_answer = _reference_randomized_top_two(trial, seed ^ 0x22A2, 64)
        top_two_seconds.append(time.perf_counter() - t0)
        top_two_successes += int(verify(trial, top_two_answer)[0])

        answer, cost = _reference_search(trial)
        reference_successes += int(answer is not None and verify(trial, answer)[0])
        reference_nodes.append(cost["nodes"])
        reference_operations.append(cost["scalar_operations"])
        reference_seconds.append(cost["wall_clock_sec"])
        compact_answer, compact_cost = _symmetry_route(trial)
        compact_successes += int(
            compact_answer is not None and verify(trial, compact_answer)[0]
        )
        compact_steps.append(
            compact_cost["permutation_applications"]
            + compact_cost["membership_lookups"]
            + compact_cost["set_intersection_tests"]
        )

    all_attacks_failed = all(result["successes"] == 0 for result in attack_results.values())
    reference = {
        "name": "exact maximum-compatible-subset branch-and-bound",
        "complexity": "O(m^2*d + m^12) worst case; d=10 and target size=12",
        "wall_clock_sec": sum(reference_seconds),
        "mean_wall_clock_sec": sum(reference_seconds) / len(reference_seconds),
        "max_nodes": max(reference_nodes),
        "mean_nodes": sum(reference_nodes) / len(reference_nodes),
        "mean_operations": sum(reference_operations) / len(reference_operations),
        "operations": sum(reference_operations),
        "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        "additional_solver": {
            "name": "randomized top-two-degree clique heuristic",
            "complexity": "O(m^2*d + R*m^2) for R=64 restarts",
            "wall_clock_sec": sum(top_two_seconds),
            "minimum_exact_scalar_operations": (
                len(attack_seeds) * inst["n"] * (inst["n"] - 1) * 10
            ),
            "solves": f"{top_two_successes}/{len(attack_seeds)}, as expected",
        },
    }
    report["G6_adversary_panel"] = {
        "pass": (
            all_attacks_failed
            and reference_successes == len(attack_seeds)
            and top_two_successes == len(attack_seeds)
            and compact_successes == len(attack_seeds)
        ),
        "attacks": attack_results,
        "reference_algorithm": reference,
        "compact_route": {
            "name": "complete S4 orbit recognition",
            "solves": f"{compact_successes}/{len(attack_seeds)}",
            "max_discrete_steps": max(compact_steps),
            "exact_arithmetic_operations": 0,
        },
    }

    report["G5_density_and_baseline"] = {
        "pass": (
            empirical_probability < 1e-6
            and probability_upper_bound < 1e-6
            and all_attacks_failed
        ),
        "shipping_n": inst["n"],
        "shipping_density_hits": hits,
        "shipping_density_samples": samples,
        "shipping_sampled_solution_fraction": empirical_probability,
        "shipping_certified_solution_fraction_upper_bound": probability_upper_bound,
        "demo_n": demo["n"],
        "demo_exact_solution_count": demo_count,
        "strongest_failing_attack_wall_seconds": strongest_attack_seconds,
        "strongest_failing_attack_iterations": strongest_attack_iterations,
        "reference_mean_nodes": reference["mean_nodes"],
        "reference_mean_operations": reference["mean_operations"],
        "reference_wall_seconds": reference["wall_clock_sec"],
    }

    # G7: double the shipping ground set while the answer remains 120 atoms.
    doubled_params = dict(shipping_params)
    doubled_params["n"] = min(252, 2 * int(shipping_params["n"]))
    doubled_params["crowding"] = int(shipping_params.get("crowding", 0)) + 1
    doubled = make_instance(seed=9182, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] == 2 * inst["n"],
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "shipping_answer_atoms": _answer_atoms(inst["answer"]),
        "doubled_answer_atoms": _answer_atoms(doubled["answer"]),
        "verify_reason": doubled_reason,
    }

    # G8: test each family symmetry and a composition of all of them.
    invariant_checks = 0
    preserving_checks = 0
    invariant_failures = []
    transformation_specs = (
        ("row_reorder", {"reorder": True, "relabel": False, "switch": False}),
        ("coordinate_relabel", {"reorder": False, "relabel": True, "switch": False}),
        ("class_switching", {"reorder": False, "relabel": False, "switch": True}),
        (
            "composed_with_generator_reorder",
            {
                "reorder": True,
                "relabel": True,
                "switch": True,
                "reorder_symmetries": True,
            },
        ),
    )
    for seed in range(20):
        original = make_instance(seed=7000 + seed, **shipping_params)
        original_key = canonical_key(original)
        for offset, (name, options) in enumerate(transformation_specs):
            changed, carried = _transformed_copy(
                original, 8000 + 10 * seed + offset, **options
            )
            same = original_key == canonical_key(changed)
            ok, reason = verify(changed, carried)
            invariant_checks += 1
            preserving_checks += int(ok)
            if not same or not ok:
                invariant_failures.append(
                    {
                        "seed": seed,
                        "transformation": name,
                        "key_invariant": same,
                        "verify_reason": reason,
                    }
                )
    unrelated_keys = [
        canonical_key(make_instance(seed=9120 + seed, **shipping_params))
        for seed in range(20)
    ]
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": (
            not invariant_failures
            and preserving_checks == invariant_checks
            and invariant_checks == 80
            and distinct_keys == 20
        ),
        "invariance_checks": invariant_checks,
        "invariance_passed": invariant_checks - len(invariant_failures),
        "preserving_transform_checks": preserving_checks,
        "transformations_per_seed": [name for name, _ in transformation_specs],
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "failures": invariant_failures,
    }

    answer_blob = json.dumps(inst["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    compact_answer, compact_cost = _symmetry_route(inst)
    compact_ok = compact_answer is not None and verify(inst, compact_answer)[0]
    intended_operations = compact_cost["exact_arithmetic_operations"]
    intended_discrete_steps = (
        compact_cost["permutation_applications"]
        + compact_cost["membership_lookups"]
        + compact_cost["set_intersection_tests"]
    )
    arms = {
        name: {
            "solved": evidence["solved"],
            "attempts": evidence["attempts"],
            "api_errors": evidence.get("api_errors", 0),
        }
        for name, evidence in G9_EVIDENCE.items()
        if name in ("bare", "hinted", "placebo")
    }
    hinted = arms["hinted"]["solved"]
    placebo = arms["placebo"]["solved"]
    hinted_minus_placebo = (
        None
        if (
            hinted is None
            or placebo is None
            or not arms["hinted"]["attempts"]
            or not arms["placebo"]["attempts"]
        )
        else hinted / arms["hinted"]["attempts"]
        - placebo / arms["placebo"]["attempts"]
    )
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and intended_operations <= 300
        and intended_discrete_steps <= 300
    )
    report["G9_no_tool_suitability"] = {
        # Since 2026-09-05 both the three-arm comparison and the hinted-arm
        # verdict are diagnostic only.  G9's gate is the answer/route cap.
        "pass": within_caps and compact_ok,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "intended_route_discrete_steps": intended_discrete_steps,
        "intended_route_verified": compact_ok,
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
