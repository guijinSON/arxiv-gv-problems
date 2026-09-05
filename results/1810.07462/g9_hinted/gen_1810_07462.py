"""Self-contained verified generator for arXiv:1810.07462.

The paper studies disjoint transversal bases of n given bases in a rank-n
matroid.  This module stays in that native setting: it inverse-generates exact
vector matroids over Q and carries several disjoint transversal bases planted
by an affine direction schedule.  Generation never searches for a witness.
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
    from gvlib import exact_matrices
except ImportError:  # The module has an integer Bareiss fallback below.
    exact_matrices = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "rational_exact",
    "computational_core": "exact_cover",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "bases of an exact vector matroid over Q",
        "disjoint transversal bases represented by a color-by-basis slot matrix",
    ],
    "verification_operations": [
        "integer range and disjointness checks",
        "exact fraction-free determinant tests over Q",
        "exact affine-coordinate comparisons",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Quotienting by the coordinate direction common to all vectors exposes "
        "affinely ordered direction classes; without that view, one must inspect "
        "coordinates and assemble independent rainbow bases mechanically."
    ),
    "hardness_basis": (
        "Track B: exact support-frequency quotient extraction followed by cyclic "
        "1-factorization runs in O(n^3+kn), taking 11,772 counted operations and "
        "about 0.0016 seconds at shipping n=18,k=6; the affine quotient route "
        "uses at most 152 exact arithmetic operations there."
    ),
    "max_answer_tokens": 71,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (PROBLEM_PROFILE["intuition_type"] + ": " +
                  PROBLEM_PROFILE["intuition_description"]),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 4, "k": 2, "head_levels": 2},
    "easy": {"n": 18, "k": 6, "head_levels": 6},
    "medium": {"n": 21, "k": 8, "head_levels": 4},
    "hard": {"n": 24, "k": 10, "head_levels": 3},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The quotient by the coordinate direction common to every vector turns "
    "each displayed row into an affine permutation of direction classes."
)
PLACEBO_HINT = (
    "The zero-based color and slot indices require consistent bookkeeping when "
    "assembling the requested collection of transversal bases."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON k-by-n matrix of slot indices. Row t chooses one slot from every "
        "color class for transversal basis t; entries in each color column are "
        "distinct, and the first color column is strictly increasing."
    ),
    "bounds": {
        "rows": "k",
        "columns": "n",
        "entry_min": 0,
        "entry_max": "n-1",
        "column_distinct": True,
        "canonical_basis_order": "answer[t][0] strictly increasing",
    },
}

NOTES = (
    "Section 1 fixes the exact problem: a transversal basis contains one "
    "distinguished element of every input basis, and disjointness is on colored "
    "copies. Definition 2.1 identifies full rainbow independent sets with these "
    "bases. Theorem 1.1 gives (1/2-epsilon)n disjoint transversal bases for all "
    "sufficiently large rank-n matroids, while Sections 2.1-2.3 produce them by "
    "iterated simple and cascading swaps. The introduction records easy regimes: "
    "the full conjecture is known for strongly base-orderable and paving matroids, "
    "and rank at most four was checked computationally. This generator therefore "
    "makes no Track-A claim. It samples all head coefficients before selecting "
    "the affine transversals, so planted and unused elements have the same local "
    "distribution. Non-unit row drift defeats fixed-column and diagonal guesses; "
    "independent head noise defeats magnitude alignment; exact rank tests defeat "
    "greedy and random-restart false positives. The disclosed polynomial reference "
    "algorithm extracts quotient directions by full coordinate inspection."
)

# Filled from script-owned transcripts after the oracle runs. These are
# diagnostics only; G9 gates the size/effort caps.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unrun",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_parameters(n, k, head_levels):
    if not _is_int(n) or n < 4:
        raise ValueError("n must be an integer at least 4")
    if not _is_int(k) or k < 1 or k > n:
        raise ValueError("k must be an integer between 1 and n")
    if not _is_int(head_levels) or head_levels < 2:
        raise ValueError("head_levels must be an integer at least 2")


def _affine_parameters(n, rng):
    """Choose a row schedule that defeats fixed-column and diagonal guesses."""
    strong = [
        (a, b) for a in range(1, n) for b in range(1, n)
        if math.gcd(a, n) == 1 and math.gcd(b, n) > 1
        and math.gcd(a + b, n) > 1
    ]
    if strong:
        return rng.choice(strong)
    units = [a for a in range(1, n) if math.gcd(a, n) == 1]
    return rng.choice(units), rng.randrange(1, n)


def _det_integer(matrix):
    """Exact fraction-free determinant, used if gvlib is unavailable."""
    n = len(matrix)
    work = [list(map(int, row)) for row in matrix]
    sign, previous = 1, 1
    for pivot_col in range(n - 1):
        if work[pivot_col][pivot_col] == 0:
            pivot = next((r for r in range(pivot_col + 1, n)
                          if work[r][pivot_col] != 0), None)
            if pivot is None:
                return 0
            work[pivot_col], work[pivot] = work[pivot], work[pivot_col]
            sign = -sign
        pivot_value = work[pivot_col][pivot_col]
        for row in range(pivot_col + 1, n):
            for col in range(pivot_col + 1, n):
                numerator = (work[row][col] * pivot_value -
                             work[row][pivot_col] * work[pivot_col][col])
                work[row][col] = numerator // previous
            work[row][pivot_col] = 0
        previous = pivot_value
    return sign * work[-1][-1]


def _det(matrix):
    if exact_matrices is not None:
        return exact_matrices.det(exact_matrices.matrix(matrix))
    return _det_integer(matrix)


def _rank_rows(rows):
    """Exact rank of a short integer row family (at most three in keying)."""
    if not rows:
        return 0
    work = [list(map(int, row)) for row in rows]
    rank = 0
    for col in range(len(work[0])):
        pivot = next((r for r in range(rank, len(work)) if work[r][col]), None)
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        pv = work[rank][col]
        for row in range(len(work)):
            if row == rank or work[row][col] == 0:
                continue
            factor = work[row][col]
            work[row] = [pv * x - factor * y
                         for x, y in zip(work[row], work[rank])]
        rank += 1
        if rank == len(work):
            break
    return rank


def _primitive(vector):
    divisor = 0
    for value in vector:
        divisor = math.gcd(divisor, abs(value))
    if divisor == 0:
        raise ValueError("zero vector is not allowed")
    out = tuple(value // divisor for value in vector)
    first = next(value for value in out if value)
    return tuple(-value for value in out) if first < 0 else out


def make_instance(n, seed=0, k=None, head_levels=4, **params):
    """Inverse-generate exact bases and known disjoint transversal bases."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if k is None:
        k = max(1, n // 3)
    _validate_parameters(n, k, head_levels)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    step, drift = _affine_parameters(n, rng)
    offset = rng.randrange(n)
    values = list(range(-head_levels, 0)) + list(range(1, head_levels + 1))

    bases = []
    for color in range(n):
        row = []
        for slot in range(n):
            direction = (step * slot + drift * color + offset) % n
            head = rng.choice(values)
            vector = [0] * n
            vector[0] = head
            if direction:
                vector[direction] += 1
            row.append(vector)
        bases.append(row)

    # Ensure every non-head direction has at least two projective points. This
    # makes the head line the unique n-element parallel class for canonical_key.
    for direction in range(1, n):
        locations = []
        for color, row in enumerate(bases):
            for slot, vector in enumerate(row):
                tail = [q for q in range(1, n) if vector[q]]
                if tail == [direction]:
                    locations.append((color, slot))
        heads = {bases[c][j][0] for c, j in locations}
        if len(heads) == 1:
            color, slot = locations[-1]
            old = bases[color][slot][0]
            bases[color][slot][0] = next(value for value in values if value != old)

    inverse_step = pow(step, -1, n)
    planted = []
    for target_offset in range(k):
        chosen = []
        for color in range(n):
            target_direction = (color + target_offset) % n
            slot = (inverse_step *
                    (target_direction - drift * color - offset)) % n
            chosen.append(slot)
        planted.append(chosen)
    planted.sort(key=lambda base: base[0])

    return {
        "paper": "arXiv:1810.07462",
        "family": "disjoint transversal bases in an exact vector matroid",
        "field": "Q",
        "n": n,
        "k": k,
        "head_levels": head_levels,
        "coordinate_form": "head_plus_unit_tail",
        "bases": bases,
        "answer": planted,
    }


def render(inst):
    n, k = inst["n"], inst["k"]
    lines = [
        "Find disjoint transversal bases in an exact vector matroid.",
        "",
        "Definitions.",
        f"All vectors lie in Q^{n}; all displayed coordinates are exact integers.",
        "A list of n vectors is a basis exactly when its n-by-n coordinate",
        "matrix has nonzero determinant over Q. There are n colored input bases",
        "B_0,...,B_(n-1), each with slots 0,...,n-1. A transversal basis",
        "chooses exactly one vector from every B_c and the chosen n vectors must",
        "be a basis. Transversal bases are disjoint when no two choose the same",
        "slot from the same B_c; equal coordinate vectors in different colors are",
        "still distinct colored copies for this disjointness rule.",
        "",
        f"Here n={n}. Find exactly k={k} pairwise disjoint transversal bases.",
        "Vectors are listed as slot:[coordinate 0,...,coordinate n-1].",
    ]
    for color, row in enumerate(inst["bases"]):
        entries = [f"{slot}:" + json.dumps(vector, separators=(",", ":"))
                   for slot, vector in enumerate(row)]
        lines.append(f"B_{color}: " + " | ".join(entries))
    lines.extend([
        "",
        "Required answer.",
        "Return a JSON list of exactly k lists. Answer row t is transversal basis",
        "t and must contain exactly n slot indices in color order: entry c selects",
        "that slot of B_c. Indices are zero-based integers in [0,n-1]. Repeats",
        "inside one color column are forbidden. The order of the k bases is",
        "canonical: their selected slots from B_0 must be strictly increasing.",
        "Any collection satisfying these rules and the exact basis tests is valid.",
        "",
        "Give your final answer inside <answer></answer> tags as the JSON matrix.",
        "Example format only: <answer>[[0,2,1,3],[1,3,0,2]]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    match = re.search(r"<answer\b[^>]*>(.*?)</answer>", text,
                      flags=re.IGNORECASE | re.DOTALL)
    if match is None:
        return None
    payload = match.group(1).strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", payload,
                         flags=re.IGNORECASE | re.DOTALL)
    if fence:
        payload = fence.group(1).strip()
    try:
        return json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _selected_matrix(inst, slots):
    # Vectors are columns, while the instance stores each vector as a row list.
    vectors = [inst["bases"][color][slot] for color, slot in enumerate(slots)]
    n = inst["n"]
    return [[vectors[col][row] for col in range(n)] for row in range(n)]


def _sparse_metadata(inst):
    cached = inst.get("_sparse_metadata")
    if cached is not None:
        return cached
    n = inst["n"]
    directions, heads = [], []
    for row in inst["bases"]:
        direction_row, head_row = [], []
        for vector in row:
            if not isinstance(vector, list) or len(vector) != n:
                return None
            tail = [coordinate for coordinate in range(1, n) if vector[coordinate]]
            if tail and (len(tail) != 1 or vector[tail[0]] != 1):
                return None
            direction_row.append(tail[0] if tail else 0)
            head_row.append(vector[0])
        directions.append(direction_row)
        heads.append(head_row)
    cached = (directions, heads)
    inst["_sparse_metadata"] = cached
    return cached


def _is_basis_exact(inst, slots):
    if inst.get("coordinate_form") == "head_plus_unit_tail":
        # For v=h*e_0+e_d (d>0), the selected span contains one dimension
        # for every distinct nonzero d and at most one further e_0 dimension.
        # With n selected vectors it is full precisely in either case below.
        n = inst["n"]
        metadata = _sparse_metadata(inst)
        if metadata is None:
            return _det(_selected_matrix(inst, slots)) != 0
        directions, all_heads = metadata
        tails = []
        heads_by_tail = {}
        has_head_line = False
        for color, slot in enumerate(slots):
            direction = directions[color][slot]
            if not direction:
                has_head_line = True
                continue
            tails.append(direction)
            heads_by_tail.setdefault(direction, []).append(all_heads[color][slot])
        if len(set(tails)) != n - 1:
            return False
        if has_head_line:
            return True
        duplicate_heads = next((values for values in heads_by_tail.values()
                                if len(values) == 2), None)
        return duplicate_heads is not None and duplicate_heads[0] != duplicate_heads[1]
    return _det(_selected_matrix(inst, slots)) != 0


def verify(inst, answer):
    """Check any admissible witness exactly; never consult inst['answer']."""
    try:
        n, k, bases = inst["n"], inst["k"], inst["bases"]
    except (KeyError, TypeError):
        return False, "instance is missing its vector bases"
    if not _is_int(n) or not _is_int(k) or len(bases) != n:
        return False, "instance dimensions are inconsistent"
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list) or len(answer) != k:
        return False, f"answer must contain exactly {k} transversal bases"
    for index, row in enumerate(answer):
        if not isinstance(row, list) or len(row) != n:
            return False, f"transversal basis {index} must contain exactly {n} slots"
        if any(not _is_int(slot) for slot in row):
            return False, f"transversal basis {index} contains a non-integer slot"
        if any(slot < 0 or slot >= n for slot in row):
            return False, f"transversal basis {index} contains an out-of-range slot"
    first_slots = [row[0] for row in answer]
    if any(left >= right for left, right in zip(first_slots, first_slots[1:])):
        return False, "transversal bases are not in canonical B_0-slot order"
    for color in range(n):
        selected = [answer[index][color] for index in range(k)]
        if len(set(selected)) != k:
            return False, f"color B_{color} reuses a slot across transversal bases"
    for index, slots in enumerate(answer):
        try:
            independent = _is_basis_exact(inst, slots)
        except (TypeError, ValueError, ZeroDivisionError):
            return False, "instance contains a malformed coordinate matrix"
        if not independent:
            return False, f"transversal basis {index} has exact determinant zero"
    return True, "ok"


def random_candidate(inst, rng):
    n, k = inst["n"], inst["k"]
    columns = [sorted(rng.sample(range(n), k))]
    columns.extend(rng.sample(range(n), k) for _ in range(1, n))
    return [[columns[color][base] for color in range(n)] for base in range(k)]


def search_space(inst):
    n, k = inst["n"], inst["k"]
    falling = math.factorial(n) // math.factorial(n - k)
    return math.comb(n, k) * pow(falling, n - 1)


def enumerate_all(inst):
    space = search_space(inst)
    if space > 120_000:
        return None
    n, k = inst["n"], inst["k"]
    total = 0
    for first in itertools.combinations(range(n), k):
        choices = [list(first)]

        def visit(color):
            nonlocal total
            if color == n:
                candidate = [[choices[c][t] for c in range(n)] for t in range(k)]
                total += int(verify(inst, candidate)[0])
                return
            for ordered in itertools.permutations(range(n), k):
                choices.append(ordered)
                visit(color + 1)
                choices.pop()

        visit(1)
    return total


def canonical_key(inst):
    """Strong GL- and relabelling-invariant for this generated matroid family."""
    n, k = inst["n"], inst["k"]
    counts = {}
    for row in inst["bases"]:
        for vector in row:
            key = _primitive(vector)
            counts[key] = counts.get(key, 0) + 1
    anchors = [vector for vector, count in counts.items() if count == n]
    if len(anchors) != 1:
        # A general represented-matroid normal form is intractable. This sorted
        # projective multiplicity spectrum remains GL- and relabelling-invariant.
        data = [n, k, sorted(counts.values())]
        return hashlib.sha256(json.dumps(data, separators=(",", ":")).encode()).hexdigest()
    anchor = anchors[0]
    representatives = sorted(vector for vector in counts if vector != anchor)
    groups = []
    while representatives:
        representative = representatives.pop(0)
        group = [representative]
        remaining = []
        for vector in representatives:
            if _rank_rows([anchor, representative, vector]) <= 2:
                group.append(vector)
            else:
                remaining.append(vector)
        representatives = remaining
        groups.append(tuple(sorted(counts[vector] for vector in group)))
    invariant = [n, k, counts[anchor], sorted(groups)]
    return hashlib.sha256(json.dumps(invariant, separators=(",", ":")).encode()).hexdigest()


def escalate(params):
    n, k = params["n"], params.get("k", max(1, params["n"] // 3))
    levels = params.get("head_levels", 4)
    if n < 24:
        next_n = min(24, n + 3)
        next_k = min(10, k + 2, next_n)
        return {"n": next_n, "k": next_k,
                "head_levels": max(3, levels - 1)}
    if levels > 2:
        return {"n": n, "k": k, "head_levels": levels - 1}
    # Once the named hard rung is crowded as far as useful, enlarge the
    # ambient rank while shortening the number of requested bases.  This grows
    # the haystack without growing the 240-atom witness.
    if n == 24:
        return {"n": 30, "k": 7, "head_levels": 2}
    if n == 30:
        return {"n": 36, "k": 6, "head_levels": 2}
    return "cap_bound"


def _candidate_from_columns(columns):
    k = len(columns[0])
    answer = [[columns[color][base] for color in range(len(columns))]
              for base in range(k)]
    answer.sort(key=lambda row: row[0])
    return answer


def _attack_fixed_columns(inst):
    return [[base for _color in range(inst["n"])] for base in range(inst["k"])]


def _attack_diagonal_slots(inst):
    n, k = inst["n"], inst["k"]
    return [[(color + base) % n for color in range(n)] for base in range(k)]


def _attack_head_magnitude(inst):
    columns = []
    for row in inst["bases"]:
        ordered = sorted(range(inst["n"]),
                         key=lambda slot: (abs(row[slot][0]), row[slot][0], slot))
        columns.append(ordered[:inst["k"]])
    return _candidate_from_columns(columns)


def _attack_support_then_slot(inst):
    columns = []
    for row in inst["bases"]:
        ordered = sorted(range(inst["n"]),
                         key=lambda slot: (sum(value != 0 for value in row[slot]), slot))
        columns.append(ordered[:inst["k"]])
    return _candidate_from_columns(columns)


def _attack_random_restart(inst, rng, attempts=256):
    candidate = None
    for _ in range(attempts):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate
    return candidate


def _reference_algorithm(inst):
    """Mechanical coordinate inspection and quotient-direction factorization."""
    n, k = inst["n"], inst["k"]
    tests = 0
    frequencies = [0] * n
    for coordinate in range(n):
        for row in inst["bases"]:
            for vector in row:
                tests += 1
                frequencies[coordinate] += int(vector[coordinate] != 0)
    head = max(range(n), key=lambda coordinate: frequencies[coordinate])
    lookup = []
    for row in inst["bases"]:
        by_direction = {}
        for slot, vector in enumerate(row):
            tail = []
            for coordinate, value in enumerate(vector):
                tests += 1
                if coordinate != head and value:
                    tail.append(coordinate)
            direction = tail[0] if len(tail) == 1 else head
            by_direction[direction] = slot
        lookup.append(by_direction)
    answer = []
    for target_offset in range(k):
        answer.append([lookup[color][(color + target_offset) % n]
                       for color in range(n)])
    answer.sort(key=lambda base: base[0])
    return answer, {"coordinate_tests": tests,
                    "factorization_lookups": n * k,
                    "operations": tests + n * k}


def _transformed_instance(inst, seed, transformations=None):
    """Carry a witness through selected instance-preserving relabellings."""
    rng = random.Random(seed)
    n = inst["n"]
    if transformations is None:
        transformations = {
            "color_permutation", "slot_permutations", "projective_scalings",
            "coordinate_permutation", "unimodular_shear",
        }
    transformations = set(transformations)
    old_colors = list(range(n))
    if "color_permutation" in transformations:
        rng.shuffle(old_colors)
    new_bases, inverses = [], []
    for old_color in old_colors:
        old_slots = list(range(n))
        if "slot_permutations" in transformations:
            rng.shuffle(old_slots)
        inverse = [0] * n
        row = []
        for new_slot, old_slot in enumerate(old_slots):
            inverse[old_slot] = new_slot
            scale = (rng.choice((-3, -2, -1, 1, 2, 3))
                     if "projective_scalings" in transformations else 1)
            row.append([scale * value for value in inst["bases"][old_color][old_slot]])
        new_bases.append(row)
        inverses.append(inverse)

    coordinates = list(range(n))
    if "coordinate_permutation" in transformations:
        rng.shuffle(coordinates)
    for row in new_bases:
        for index, vector in enumerate(row):
            changed = [vector[coordinates[q]] for q in range(n)]
            if n >= 2 and "unimodular_shear" in transformations:
                changed[0] += changed[1]
            row[index] = changed

    carried = []
    for base in inst["answer"]:
        carried.append([inverses[new_color][base[old_color]]
                        for new_color, old_color in enumerate(old_colors)])
    carried.sort(key=lambda answer_row: answer_row[0])
    transformed = {key: value for key, value in inst.items()
                   if key not in ("bases", "answer")}
    transformed["coordinate_form"] = "general_integer"
    transformed["bases"], transformed["answer"] = new_bases, carried
    return transformed


def _json_answer_size(answer):
    compact = json.dumps(answer, separators=(",", ":"))
    atoms = sum(len(row) for row in answer)
    return len(compact), (len(compact) + 3) // 4, atoms


def selftest():
    report = {
        "paper": "arXiv:1810.07462",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    failures, attempts = [], 0
    for preset, parameters in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **parameters)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                failures.append({"preset": preset, "seed": seed,
                                 "reason": "answer is not JSON-native"})
    report["G1_planted_verifies"] = {
        "pass": not failures, "attempts": attempts, "failures": failures}

    shipping = make_instance(seed=181007462, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    swapped_bases = list(reversed([row[:] for row in planted]))
    reused = [row[:] for row in planted]
    reused[1][1] = reused[0][1]
    corruptions = {
        "empty_answer": [],
        "drop_one_basis": planted[:-1],
        "drop_one_slot": [planted[0][:-1]] + [row[:] for row in planted[1:]],
        "swap_basis_order": swapped_bases,
        "reuse_colored_slot": reused,
        "out_of_range": [[shipping["n"]] + planted[0][1:]] +
                        [row[:] for row in planted[1:]],
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = {entry["reason"] for entry in corruption_results.values()}
    report["G2_rejects_corruption"] = {
        "pass": (all(entry["rejected"] for entry in corruption_results.values())
                 and len(reasons) == len(corruption_results)),
        "cases": corruption_results,
        "distinct_reasons": len(reasons),
    }

    payload = json.dumps(planted, separators=(",", ":"))
    realistic = ("I checked every determinant exactly.\n<answer>\n```json\n" +
                 payload + "\n```\n</answer>\nThese are zero-based slots.")
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged answer") is None,
        "json_chars": len(payload),
    }

    guess_rng = random.Random(0x181007462)
    guess_total, guess_hits = 200_000, 0
    started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_elapsed = time.perf_counter() - started
    density = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": density < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": density,
        "structure_aware_space": search_space(shipping),
        "sampling_rule": (
            "uniform canonical k-by-n slot matrices: columnwise disjointness and "
            "strict B_0 ordering are enforced before exact rank tests"
        ),
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attack_functions = {
        "fixed_slot_columns": lambda inst, rng: _attack_fixed_columns(inst),
        "diagonal_slot_rule": lambda inst, rng: _attack_diagonal_slots(inst),
        "head_magnitude_alignment": lambda inst, rng: _attack_head_magnitude(inst),
        "support_size_then_slot": lambda inst, rng: _attack_support_then_slot(inst),
        "random_restart_256": lambda inst, rng: _attack_random_restart(inst, rng, 256),
    }
    attack_results = {name: {"successes": 0, "attempts": 0}
                      for name in attack_functions}
    attack_elapsed = {name: 0.0 for name in attack_functions}
    attack_seeds = list(range(8100, 8108))
    reference_successes, reference_elapsed = 0, 0.0
    reference_operations = []
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for offset, (name, function) in enumerate(attack_functions.items()):
            rng = random.Random(seed * 1009 + offset)
            before = time.perf_counter()
            candidate = function(inst, rng)
            attack_elapsed[name] += time.perf_counter() - before
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])
            attack_results[name]["attempts"] += 1
        before = time.perf_counter()
        answer, stats = _reference_algorithm(inst)
        reference_elapsed += time.perf_counter() - before
        reference_operations.append(stats["operations"])
        reference_successes += int(verify(inst, answer)[0])
    for name in attack_results:
        attack_results[name]["wall_clock_sec_total_8"] = round(attack_elapsed[name], 6)
    all_failed = all(row["successes"] == 0 for row in attack_results.values())
    reference = {
        "name": "exact support-frequency quotient extraction plus cyclic 1-factorization",
        "complexity": "O(n^3 + kn) exact coordinate tests/lookups",
        "wall_clock_sec_total_8": round(reference_elapsed, 6),
        "wall_clock_sec_mean": round(reference_elapsed / len(attack_seeds), 8),
        "operations_mean": sum(reference_operations) // len(reference_operations),
        "operations_min": min(reference_operations),
        "operations_max": max(reference_operations),
        "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
    }
    intended_operations = shipping["n"] * shipping["k"] + 2 * shipping["n"] + 8
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == len(attack_seeds),
        "attacks": attack_results,
        "reference_algorithm": reference,
        "compact_route": {
            "name": "affine quotient-direction schedule",
            "worst_case_exact_operations": intended_operations,
            "count_model": (
                "one target-direction update per output entry, two n-term setup "
                "passes, and eight modular setup operations"
            ),
            "solves": "by inverse-generation identity",
        },
    }

    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    enum_started = time.perf_counter()
    demo_count = enumerate_all(demo)
    enum_elapsed = time.perf_counter() - enum_started
    strongest = max(attack_elapsed, key=attack_elapsed.get)
    report["G5_density_and_baseline_cost"] = {
        "pass": density < 1e-6 and all_failed and demo_count is not None,
        "sampled_density_at_shipping": density,
        "density_hits": guess_hits,
        "density_samples": guess_total,
        "candidate_space_at_shipping": search_space(shipping),
        "exact_demo_valid_answers": demo_count,
        "exact_demo_candidate_space": search_space(demo),
        "exact_demo_enumeration_wall_clock_sec": round(enum_elapsed, 6),
        "strongest_failing_attack": strongest,
        "baseline_wall_clock_sec_total_8": round(attack_elapsed[strongest], 6),
        "baseline_attempts_or_iterations": 8 * (256 if strongest == "random_restart_256" else 1),
    }

    doubled = make_instance(n=2 * shipping["n"], k=shipping["k"],
                            head_levels=shipping["head_levels"], seed=991)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and len(doubled["bases"]) == 2 * shipping["n"],
        "original_n": shipping["n"],
        "doubled_n": doubled["n"],
        "fixed_k": doubled["k"],
        "doubled_vector_count": doubled["n"] ** 2,
        "verify_reason": doubled_reason,
    }

    invariant_checks = carried_checks = 0
    key_failures = []
    transformation_cases = {
        "color_permutation": {"color_permutation"},
        "slot_permutations": {"slot_permutations"},
        "projective_scalings": {"projective_scalings"},
        "coordinate_permutation": {"coordinate_permutation"},
        "unimodular_shear": {"unimodular_shear"},
        "full_composition": {
            "color_permutation", "slot_permutations", "projective_scalings",
            "coordinate_permutation", "unimodular_shear",
        },
    }
    for seed in range(20):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        original_key = canonical_key(inst)
        for case_index, (case_name, transformations) in enumerate(
                transformation_cases.items()):
            transformed = _transformed_instance(
                inst, 50000 + 101 * seed + case_index, transformations)
            if original_key != canonical_key(transformed):
                key_failures.append({"seed": seed, "kind": "invariance",
                                     "transformation": case_name})
            else:
                invariant_checks += 1
            ok, reason = verify(transformed, transformed["answer"])
            if not ok:
                key_failures.append({"seed": seed, "kind": "carried_witness",
                                     "transformation": case_name,
                                     "reason": reason})
            else:
                carried_checks += 1
    unrelated_keys = [canonical_key(make_instance(seed=90000 + seed,
                                                   **DIFFICULTY[SHIPPING_DIFFICULTY]))
                      for seed in range(20)]
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct_count == 20,
        "invariant_relabellings": invariant_checks,
        "carried_witnesses_valid": carried_checks,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": list(transformation_cases),
        "failures": key_failures,
    }

    # The affine schedule changes decimal widths. Measure the worst serialized
    # answer over a deterministic 256-seed shipping sweep, not just one seed.
    shipping_sizes = [
        _json_answer_size(make_instance(seed=seed,
                                        **DIFFICULTY[SHIPPING_DIFFICULTY])["answer"])
        for seed in range(256)
    ]
    answer_chars, answer_tokens, answer_elements = max(shipping_sizes)
    arms = {name: dict(G9_ORACLE_RESULTS.get(name, {"solved": 0, "attempts": 0}))
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    within_caps = (answer_chars <= 2000 and answer_elements <= 256 and
                   intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS.get("hinted_verdict", "unrun"),
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"answer_chars": answer_chars, "answer_elements": answer_elements,
                 "intended_route_operations": intended_operations},
    }

    report["pass"] = all(value.get("pass", False) for key, value in report.items()
                         if key.startswith("G") and key[1:2].isdigit())
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
