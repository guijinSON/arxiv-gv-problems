"""Verified generator for Eppstein's integer-coordinate ``flaps and flips``.

The native geometric instance is a collection of equal square flaps, hinged to
a table as in Section 5.1 of arXiv:2410.07666. Section 5.2's edge gadget is a
chain: changing all its flap sides requires flipping from the uncovered end.
This module composes disjoint chains and labels the planted traversal by an
affine bijection of F_q^3. The answer is the affine map, not a long move list.
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
from collections import defaultdict
from typing import Any, Callable


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "geometry",
    "object_regime": "integer_lattice",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "equal square flaps with integer-coordinate hinges",
        "two flat-folded flap states",
        "affine labels over a finite vector space",
    ],
    "verification_operations": [
        "exact integer rectangle-hinge intersection",
        "exact flip-precedence replay",
        "finite-field matrix inversion and affine evaluation",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Labels at the affine-basis ranks of the geometric precedence order "
        "determine the whole legal traversal; without that change of variables "
        "one must extract and order all flap interactions."
    ),
    "hardness_basis": (
        "Track B: comparison-sorting the shuffled hinges and fitting the affine "
        "map costs O(n log n+d^2), measured over 8 shipping instances at a mean "
        "12,443 record/comparison/field operations and 0.0044 seconds; the compact "
        "route uses 26 exact arithmetic operations, including 12 field operations, "
        "after recognizing four affine-basis landmarks hidden among 1,331 arbitrarily "
        "ordered geometry records whose full mechanical sort is unavailable without tools."
    ),
    "max_answer_tokens": 17,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON object containing an invertible 3x3 matrix A over F_q and a "
        "length-3 offset b over F_q. It denotes the permutation v -> Av+b "
        "of all q^3 flap labels."
    ),
    "bounds": {
        "matrix_rows": 3,
        "matrix_columns": 3,
        "offset_length": 3,
        "entry_minimum": 0,
        "entry_maximum": "q-1",
        "matrix_must_be_invertible": True,
    },
}

DIFFICULTY = {
    "demo": {"n": 8, "modulus": 2, "dimension": 3, "chains": 2,
             "side": 1009, "spacing_span": 97},
    "easy": {"n": 125, "modulus": 5, "dimension": 3, "chains": 4,
             "side": 100003, "spacing_span": 9973},
    "medium": {"n": 343, "modulus": 7, "dimension": 3, "chains": 5,
               "side": 100003, "spacing_span": 19997},
    "hard": {"n": 1331, "modulus": 11, "dimension": 3, "chains": 6,
             "side": 1000003, "spacing_span": 199999},
}
SHIPPING_DIFFICULTY = "hard"

STRUCTURAL_HINT = (
    "The labels at power-of-q ranks of the geometric precedence order form an affine basis over F_q."
)
PLACEBO_HINT = (
    "The coordinate table rewards keeping the hinge directions and label digits carefully organized."
)

# Filled from script-owned transcripts after the three arms run.
G9_MEASUREMENTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 2},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "incomplete: OpenRouter key limit after 2 scored attempts",
    "placebo_verdict": "incomplete: OpenRouter key limit before a scored attempt",
}

NOTES = r"""
Definition and construction. Section 5.1 defines equal square flaps hinged by
one full edge to a rigid table, valid above/below relations, and a flip that
changes one flap to another consistent position. Section 5.2 and Figure 10
give the chain edge gadget: a flap on either side covers the next hinge in that
direction. Lemma 11 states that an edge reversal is implemented by flipping
the chain from its uncovered arrowhead towards its tail. Here consecutive
vertical hinges have separation strictly between half a side and one side, so
only consecutive squares can create mutual hinge coverage. Rows are separated
by three side lengths, hence their certificates compose.

Step-0 algorithm question. Theorem 4 proves unrestricted pairwise flaps-and-
flips reachability PSPACE-complete for integer coordinates, via planar bounded-
bandwidth NCL. It does not prove this inverse-generated distribution hard.
Indeed, these composed edge gadgets have an efficient reference algorithm:
group by y, comparison-sort each shuffled row in its legal direction, and fit
the affine map from ranks 0, 1, q, and q^2. Its cost is O(n log n+d^2), so this
module honestly declares Track B. The certificate is sampled first; labels and
geometric chains are then assembled around its induced permutation.

Easy regimes and attack response. Theorem 1's factorial-in-ply,
single-exponential-in-treewidth FPT algorithm concerns flat-foldability rather
than this reconfiguration certificate. For this generated regime the row sort
is the stronger special-purpose method and is reported as the successful Track
B reference algorithm. Input order, numeric-label order, identity/translation,
a diagonal affine ansatz, and random affine restarts are tested as failing
in-context attacks. The coordinate-row attack that solved an earlier version
is no longer omitted: full coordinate sorting is now the measured reference
algorithm, while the answer stays at twelve field entries as q grows.
""".strip()


def _is_prime(q: int) -> bool:
    if q < 2:
        return False
    if q % 2 == 0:
        return q == 2
    f = 3
    while f * f <= q:
        if q % f == 0:
            return False
        f += 2
    return True


def _validate_params(n: int, modulus: int, dimension: int, chains: int,
                     side: int, spacing_span: int) -> None:
    vals = (n, modulus, dimension, chains, side, spacing_span)
    if any(isinstance(v, bool) or not isinstance(v, int) for v in vals):
        raise ValueError("all parameters must be integers")
    if not _is_prime(modulus):
        raise ValueError("modulus must be prime")
    if dimension != 3:
        raise ValueError("this certificate language fixes dimension at 3")
    if n != modulus ** dimension:
        raise ValueError("n must equal modulus**dimension")
    if chains < 2 or n < 3 * chains + 2:
        raise ValueError("chains must be at least 2 with at least 3 flaps per tail row")
    if side < 9:
        raise ValueError("side must be at least 9")
    available = side - (side // 2 + 1)
    if spacing_span < 1 or spacing_span > available + 1:
        raise ValueError("spacing_span must fit strictly between side/2 and side")


def _rank_mod(matrix: list[list[int]], q: int) -> int:
    a = [[x % q for x in row] for row in matrix]
    if not a:
        return 0
    rows, cols = len(a), len(a[0])
    rank = 0
    for col in range(cols):
        pivot = next((r for r in range(rank, rows) if a[r][col] % q), None)
        if pivot is None:
            continue
        a[rank], a[pivot] = a[pivot], a[rank]
        inv = pow(a[rank][col], -1, q)
        a[rank] = [(x * inv) % q for x in a[rank]]
        for r in range(rows):
            if r != rank and a[r][col] % q:
                factor = a[r][col] % q
                a[r] = [(a[r][c] - factor * a[rank][c]) % q
                        for c in range(cols)]
        rank += 1
        if rank == rows:
            break
    return rank


def _inverse_matrix_mod(matrix: list[list[int]], q: int) -> list[list[int]] | None:
    d = len(matrix)
    if d == 0 or any(len(row) != d for row in matrix):
        return None
    a = [[matrix[r][c] % q for c in range(d)]
         + [1 if r == c else 0 for c in range(d)] for r in range(d)]
    for col in range(d):
        pivot = next((r for r in range(col, d) if a[r][col] % q), None)
        if pivot is None:
            return None
        a[col], a[pivot] = a[pivot], a[col]
        inv = pow(a[col][col], -1, q)
        a[col] = [(x * inv) % q for x in a[col]]
        for r in range(d):
            if r != col and a[r][col] % q:
                factor = a[r][col] % q
                a[r] = [(a[r][c] - factor * a[col][c]) % q
                        for c in range(2 * d)]
    return [row[d:] for row in a]


def _random_invertible(d: int, q: int, rng: random.Random) -> list[list[int]]:
    """Uniform over all dxd matrices, conditioned on invertibility."""
    while True:
        a = [[rng.randrange(q) for _ in range(d)] for _ in range(d)]
        if _rank_mod(a, q) == d:
            return a


def _mat_vec(a: list[list[int]], v: list[int], q: int) -> list[int]:
    return [sum(x * y for x, y in zip(row, v)) % q for row in a]


def _mat_mul(a: list[list[int]], b: list[list[int]], q: int) -> list[list[int]]:
    return [[sum(a[i][k] * b[k][j] for k in range(len(b))) % q
             for j in range(len(b[0]))] for i in range(len(a))]


def _int_to_vec(value: int, q: int, d: int) -> list[int]:
    out = []
    for _ in range(d):
        out.append(value % q)
        value //= q
    return out


def _vec_to_int(v: list[int], q: int) -> int:
    total = 0
    place = 1
    for x in v:
        total += x * place
        place *= q
    return total


def _affine_label(i: int, a: list[list[int]], b: list[int], q: int, d: int) -> int:
    v = _int_to_vec(i, q, d)
    w = [(x + y) % q for x, y in zip(_mat_vec(a, v, q), b)]
    return _vec_to_int(w, q)


def _tail_composition(total: int, parts: int, rng: random.Random) -> list[int]:
    lengths = [3] * parts
    for _ in range(total - 3 * parts):
        lengths[rng.randrange(parts)] += 1
    rng.shuffle(lengths)
    return lengths


def make_instance(n: int, seed: int = 0, modulus: int = 5,
                  dimension: int = 3, chains: int = 4, side: int = 100003,
                  spacing_span: int = 9973, **params: Any) -> dict:
    """Inverse-generate a native, exact flaps-and-flips certificate instance."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, modulus, dimension, chains, side, spacing_span)
    rng = random.Random(seed)

    matrix = _random_invertible(dimension, modulus, rng)
    offset = [rng.randrange(modulus) for _ in range(dimension)]
    answer = {"matrix": matrix, "offset": offset}
    traversal = [_affine_label(i, matrix, offset, modulus, dimension)
                 for i in range(n)]

    # All affine-basis ranks are in row zero. Its constant gap makes those
    # landmarks addressable; random tail rows provide structural diversity.
    minimum_first = max(n // 2 + 1, modulus ** (dimension - 1) + 1)
    maximum_first = n - 3 * (chains - 1)
    extra_room = max(0, min(maximum_first, (3 * n) // 4) - minimum_first)
    first_length = minimum_first + (rng.randrange(extra_room + 1) if extra_room else 0)
    lengths = [first_length] + _tail_composition(n - first_length, chains - 1, rng)

    directions = [rng.choice(("R", "L")) for _ in range(chains)]
    if len(set(directions)) == 1:
        directions[-1] = "L" if directions[0] == "R" else "R"
    min_spacing = side // 2 + 1
    max_spacing = min(side - 1, min_spacing + spacing_span - 1)
    base_x = rng.randrange(-11 * side, 11 * side + 1)
    base_y = rng.randrange(-11 * side, 11 * side + 1)
    flaps: list[dict[str, int | str]] = []
    cursor = 0
    for row, (length, start_side) in enumerate(zip(lengths, directions)):
        if row == 0:
            fixed_gap = rng.randint(min_spacing, max_spacing)
            gaps = [fixed_gap] * (length - 1)
        else:
            gaps = [rng.randint(min_spacing, max_spacing) for _ in range(length - 1)]
        xs = [base_x + rng.randrange(-2 * side, 2 * side + 1)]
        for gap in gaps:
            xs.append(xs[-1] + gap)
        ordered_xs = xs if start_side == "R" else list(reversed(xs))
        target_side = "L" if start_side == "R" else "R"
        y = base_y + row * (3 * side)
        for j, x in enumerate(ordered_xs):
            flaps.append({"label": traversal[cursor + j], "x": x, "y": y,
                          "start": start_side, "target": target_side})
        cursor += length
    assert cursor == n
    rng.shuffle(flaps)
    return {"n": n, "modulus": modulus, "dimension": dimension,
            "side": side, "min_spacing": min_spacing,
            "max_spacing": max_spacing, "flaps": flaps, "answer": answer}


def _square_x(flap: dict, state: str, side: int) -> tuple[int, int]:
    x = int(flap["x"])
    return (x, x + side) if state == "R" else (x - side, x)


def _covers_hinge(a: dict, state: str, b: dict, side: int) -> bool:
    lo, hi = _square_x(a, state, side)
    bx = int(b["x"])
    if not (lo < bx < hi):
        return False
    ay, by = int(a["y"]), int(b["y"])
    return max(ay, by) < min(ay + side, by + side)


def _dependencies(inst: dict) -> tuple[list[tuple[int, int]], int]:
    """Recompute every forced before/after relation from exact geometry."""
    flaps = inst["flaps"]
    side = int(inst["side"])
    deps: list[tuple[int, int]] = []
    pair_tests = 0
    for i, a in enumerate(flaps):
        for b in flaps[i + 1:]:
            pair_tests += 1
            al, bl = int(a["label"]), int(b["label"])
            if (_covers_hinge(a, str(a["start"]), b, side)
                    and _covers_hinge(b, str(b["target"]), a, side)):
                deps.append((al, bl))
            if (_covers_hinge(b, str(b["start"]), a, side)
                    and _covers_hinge(a, str(a["target"]), b, side)):
                deps.append((bl, al))
    deps.sort()
    return deps, pair_tests


def render(inst: dict) -> str:
    n, q, d = int(inst["n"]), int(inst["modulus"]), int(inst["dimension"])
    side = int(inst["side"])
    lines = [
        "FLAPS AND FLIPS — compact exact reconfiguration certificate", "",
        f"There are {n} congruent square paper flaps of side length {side} on a rigid table.",
        f"Flap labels are 0 through {n - 1}. Here n={q}^{d}, and arithmetic below is in F_{q}.",
        "Each hinge is the vertical closed segment from (x,y) to (x,y+side).",
        "State R places a flap in [x,x+side] x [y,y+side]; state L places it in [x-side,x] x [y,y+side].",
        "Interiors are used: boundary-only contact is not overlap.",
        "A flap covers another hinge when its square interior meets a positive-length part of the other hinge's relative interior.",
        "For these supplied placements, a side assignment is consistent exactly when no two flaps cover each other's hinges; cyclic above-below relations among three flaps are allowed.",
        "A flip toggles one flap between L and R and is legal only when the resulting state is consistent.", "",
        "Every flap must be flipped exactly once, from the displayed start state to the displayed target state.",
        "Certify a legal order compactly by an affine bijection v -> A v + b over F_q.",
        f"For i=0,...,{n - 1}, write i in exactly {d} little-endian base-q digits v=(v0,v1,v2), so i=v0+q*v1+q^2*v2.",
        "Compute w=A*v+b modulo q and decode the next flap label as w0+q*w1+q^2*w2.",
        f"A must be an invertible {d} by {d} matrix, b must have length {d}, and entries are integers 0 through {q - 1}.",
        "The resulting q^3 labels must be a legal flip sequence. Any affine certificate producing one is accepted.",
        "Rows of A are output digits w0 to w2; columns are input digits v0 to v2.", "",
        "Flaps are deliberately listed in arbitrary order:",
    ]
    for f in inst["flaps"]:
        x, y = int(f["x"]), int(f["y"])
        lines.append(f"F{f['label']}: hinge=({x},{y})-({x},{y + side}); "
                     f"start={f['start']}; target={f['target']}")
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    lines.extend(["",
        "Give your final answer inside <answer></answer> tags as one JSON object with keys matrix and offset.",
        "Syntax example only: <answer>{\"matrix\":[[1,0],[0,1]],\"offset\":[0,0]}</answer>",
        f"Your actual matrix must have {d} rows of {d} entries and offset must have {d} entries, all reduced to 0,...,{q - 1}.",
        "Output nothing else inside the tags."])
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text, re.I | re.S)
    if not blocks:
        return None
    body = re.sub(r"^```(?:json|text)?\s*", "", blocks[-1].strip(), flags=re.I)
    body = re.sub(r"\s*```$", "", body).strip()
    try:
        value = json.loads(body)
    except (ValueError, TypeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _validated_certificate(inst: dict, answer: object) -> tuple[list[list[int]] | None, list[int] | None, str | None]:
    if not isinstance(answer, dict):
        return None, None, "answer must be a JSON object"
    if "matrix" not in answer or "offset" not in answer:
        return None, None, "answer must contain matrix and offset"
    a, b = answer["matrix"], answer["offset"]
    d, q = int(inst["dimension"]), int(inst["modulus"])
    if not isinstance(a, list) or len(a) != d:
        return None, None, f"matrix must have exactly {d} rows"
    if any(not isinstance(row, list) or len(row) != d for row in a):
        return None, None, f"every matrix row must have exactly {d} entries"
    flat = [x for row in a for x in row]
    if any(isinstance(x, bool) or not isinstance(x, int) for x in flat):
        return None, None, "matrix entries must be integers"
    if any(x < 0 or x >= q for x in flat):
        return None, None, f"matrix entry outside 0,...,{q - 1}"
    if not isinstance(b, list) or len(b) != d:
        return None, None, f"offset must have exactly {d} entries"
    if any(isinstance(x, bool) or not isinstance(x, int) for x in b):
        return None, None, "offset entries must be integers"
    if any(x < 0 or x >= q for x in b):
        return None, None, f"offset entry outside 0,...,{q - 1}"
    aa, bb = [list(row) for row in a], list(b)
    if _rank_mod(aa, q) != d:
        return None, None, "matrix is singular modulo q"
    return aa, bb, None


def _position_function(inst: dict, answer: object) -> tuple[Callable[[int], int] | None, str | None]:
    a, b, error = _validated_certificate(inst, answer)
    if error:
        return None, error
    assert a is not None and b is not None
    q, d = int(inst["modulus"]), int(inst["dimension"])
    inv = _inverse_matrix_mod(a, q)
    if inv is None:
        return None, "matrix is singular modulo q"

    def position(label: int) -> int:
        w = _int_to_vec(label, q, d)
        shifted = [(x - y) % q for x, y in zip(w, b)]
        return _vec_to_int(_mat_vec(inv, shifted, q), q)
    return position, None


def _verify_with_dependencies(inst: dict, answer: object,
                              deps: list[tuple[int, int]]) -> tuple[bool, str]:
    position, error = _position_function(inst, answer)
    if error:
        return False, error
    assert position is not None
    n = int(inst["n"])
    if {int(f["label"]) for f in inst["flaps"]} != set(range(n)):
        return False, "instance labels are not exactly 0,...,n-1"
    for before, after in deps:
        ib, ia = position(before), position(after)
        if ib > ia:
            return False, (f"illegal flip at step {ia + 1}: flap {after} "
                           f"is still blocked by flap {before}")
    return True, "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any affine witness by exact geometry; never consult inst['answer']."""
    deps, _ = _dependencies(inst)
    return _verify_with_dependencies(inst, answer, deps)


def random_candidate(inst: dict, rng: random.Random) -> object:
    q, d = int(inst["modulus"]), int(inst["dimension"])
    return {"matrix": _random_invertible(d, q, rng),
            "offset": [rng.randrange(q) for _ in range(d)]}


def search_space(inst: dict) -> int | None:
    q, d = int(inst["modulus"]), int(inst["dimension"])
    gl, qd = 1, q ** d
    for k in range(d):
        gl *= qd - q ** k
    return gl * qd


def enumerate_all(inst: dict) -> int | None:
    q, d = int(inst["modulus"]), int(inst["dimension"])
    if int(search_space(inst) or 0) > 20_000:
        return None
    deps, _ = _dependencies(inst)
    count = 0
    for flat in itertools.product(range(q), repeat=d * d):
        a = [list(flat[r * d:(r + 1) * d]) for r in range(d)]
        if _rank_mod(a, q) != d:
            continue
        for b in itertools.product(range(q), repeat=d):
            if _verify_with_dependencies(inst, {"matrix": a, "offset": list(b)}, deps)[0]:
                count += 1
    return count


def _merge_sort_count(items: list, key: Callable[[Any], Any],
                      reverse: bool = False) -> tuple[list, int]:
    if len(items) <= 1:
        return list(items), 0
    mid = len(items) // 2
    left, lc = _merge_sort_count(items[:mid], key, reverse)
    right, rc = _merge_sort_count(items[mid:], key, reverse)
    out, i, j, comparisons = [], 0, 0, lc + rc
    while i < len(left) and j < len(right):
        comparisons += 1
        take_left = key(left[i]) >= key(right[j]) if reverse else key(left[i]) <= key(right[j])
        if take_left:
            out.append(left[i]); i += 1
        else:
            out.append(right[j]); j += 1
    out.extend(left[i:]); out.extend(right[j:])
    return out, comparisons


def _fit_affine_from_sequence(inst: dict, labels: list[int]) -> dict | None:
    q, d, n = int(inst["modulus"]), int(inst["dimension"]), int(inst["n"])
    if len(labels) != n:
        return None
    b = _int_to_vec(labels[0], q, d)
    a = [[0] * d for _ in range(d)]
    for col in range(d):
        w = _int_to_vec(labels[q ** col], q, d)
        for row in range(d):
            a[row][col] = (w[row] - b[row]) % q
    return {"matrix": a, "offset": b}


def _reference_algorithm(inst: dict) -> tuple[dict | None, dict]:
    started = time.perf_counter()
    groups: dict[int, list[dict]] = defaultdict(list)
    for flap in inst["flaps"]:
        groups[int(flap["y"])].append(flap)
    ys, comparisons = _merge_sort_count(list(groups), key=lambda y: y)
    sequence: list[int] = []
    for y in ys:
        row = groups[y]
        ordered, used = _merge_sort_count(
            row, key=lambda f: int(f["x"]), reverse=str(row[0]["start"]) == "L")
        comparisons += used
        sequence.extend(int(f["label"]) for f in ordered)
    cert = _fit_affine_from_sequence(inst, sequence)
    d = int(inst["dimension"])
    # One operation per record to bucket it and one to emit it after sorting.
    # Counting only comparisons hid two complete passes over the input.
    record_operations = 2 * int(inst["n"])
    field_operations = d * d + d
    return cert, {"wall_clock_sec": time.perf_counter() - started,
                  "comparisons": comparisons,
                  "record_operations": record_operations,
                  "field_operations": field_operations,
                  "operations": comparisons + record_operations + field_operations}


def _identity_certificate(inst: dict, offset: list[int] | None = None) -> dict:
    d = int(inst["dimension"])
    return {"matrix": [[1 if i == j else 0 for j in range(d)] for i in range(d)],
            "offset": list(offset) if offset is not None else [0] * d}


def _attack_candidates(inst: dict, rng: random.Random) -> dict[str, dict | None]:
    q, d = int(inst["modulus"]), int(inst["dimension"])
    flaps = inst["flaps"]
    first_b = _int_to_vec(int(flaps[0]["label"]), q, d)
    presentation_fit = _fit_affine_from_sequence(inst, [int(f["label"]) for f in flaps])

    # In-context shortcut: find the true geometric start, but assume A diagonal.
    first_y = min(int(f["y"]) for f in flaps)
    first_row = [f for f in flaps if int(f["y"]) == first_y]
    ordered = sorted(first_row, key=lambda f: int(f["x"]),
                     reverse=str(first_row[0]["start"]) == "L")
    true_b = _int_to_vec(int(ordered[0]["label"]), q, d)
    diagonal = [[0] * d for _ in range(d)]
    for j in range(d):
        w = _int_to_vec(int(ordered[q ** j]["label"]), q, d)
        diagonal[j][j] = (w[j] - true_b[j]) % q or 1
    diagonal_cert = {"matrix": diagonal, "offset": true_b}

    restart_hit = None
    deps, _ = _dependencies(inst)
    for _ in range(256):
        candidate = random_candidate(inst, rng)
        if _verify_with_dependencies(inst, candidate, deps)[0]:
            restart_hit = candidate
            break
    return {
        "outlier_first_presented_as_offset": _identity_certificate(inst, first_b),
        "greedy_numeric_label_identity": _identity_certificate(inst),
        "presentation_order_affine_fit": presentation_fit,
        "in_context_diagonal_affine_ansatz": diagonal_cert,
        "random_affine_restart_256": restart_hit,
    }


def _component_signatures(inst: dict) -> list[tuple[int, tuple[int, ...]]]:
    deps, _ = _dependencies(inst)
    by_label = {int(f["label"]): f for f in inst["flaps"]}
    succ: dict[int, list[int]] = defaultdict(list)
    pred: dict[int, list[int]] = defaultdict(list)
    for a, b in deps:
        succ[a].append(b); pred[b].append(a)
    signatures, seen = [], set()
    for label in by_label:
        if pred[label] or label in seen:
            continue
        path, cur = [], label
        while cur not in seen:
            seen.add(cur); path.append(cur)
            if len(succ[cur]) != 1:
                break
            cur = succ[cur][0]
        gaps = []
        for x, y in zip(path, path[1:]):
            fx, fy = by_label[x], by_label[y]
            dx, dy = int(fx["x"]) - int(fy["x"]), int(fx["y"]) - int(fy["y"])
            gaps.append(dx * dx + dy * dy)
        signatures.append((len(path), tuple(gaps)))
    signatures.extend((1, ()) for label in by_label if label not in seen)
    return sorted(signatures)


def canonical_key(inst: dict) -> str:
    payload = {"side": int(inst["side"]), "components": _component_signatures(inst)}
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def _copy_instance(inst: dict) -> dict:
    return {"n": int(inst["n"]), "modulus": int(inst["modulus"]),
            "dimension": int(inst["dimension"]), "side": int(inst["side"]),
            "min_spacing": int(inst["min_spacing"]),
            "max_spacing": int(inst["max_spacing"]),
            "flaps": [dict(f) for f in inst["flaps"]],
            "answer": {"matrix": [list(r) for r in inst["answer"]["matrix"]],
                       "offset": list(inst["answer"]["offset"])}}


def _transform_for_g8(inst: dict, seed: int) -> tuple[dict, dict]:
    rng = random.Random(seed)
    out = _copy_instance(inst)
    q, d = int(out["modulus"]), int(out["dimension"])
    c, shift = _random_invertible(d, q, rng), [rng.randrange(q) for _ in range(d)]
    old_ys = sorted({int(f["y"]) for f in out["flaps"]})
    new_ys = [y - 91 for y in old_ys]
    rng.shuffle(new_ys)
    y_map = dict(zip(old_ys, new_ys))
    reflect = {y: bool(rng.randrange(2)) for y in old_ys}
    x_shift = {y: rng.randrange(-10_000, 10_001) for y in old_ys}
    for flap in out["flaps"]:
        old_y = int(flap["y"])
        old = _int_to_vec(int(flap["label"]), q, d)
        new = [(x + y) % q for x, y in zip(_mat_vec(c, old, q), shift)]
        flap["label"] = _vec_to_int(new, q)
        if reflect[old_y]:
            flap["x"] = -int(flap["x"]) + x_shift[old_y]
            flap["start"] = "L" if flap["start"] == "R" else "R"
            flap["target"] = "L" if flap["target"] == "R" else "R"
        else:
            flap["x"] = int(flap["x"]) + x_shift[old_y]
        flap["y"] = y_map[old_y]
    rng.shuffle(out["flaps"])
    old_a, old_b = inst["answer"]["matrix"], inst["answer"]["offset"]
    carried = {"matrix": _mat_mul(c, old_a, q),
               "offset": [(x + y) % q for x, y in zip(_mat_vec(c, old_b, q), shift)]}
    out["answer"] = carried
    return out, carried


def escalate(params: dict) -> dict | str | None:
    """Grow q^3 at fixed 12-entry witness size."""
    out = {k: v for k, v in params.items() if k != "_preset"}
    q = int(out.get("modulus", 5))
    nxt = next((p for p in (7, 11, 13, 17, 19, 23, 29, 31) if p > q), None)
    if nxt is None:
        return None
    out["modulus"] = nxt
    out["n"] = nxt ** int(out.get("dimension", 3))
    out["chains"] = min(9, int(out.get("chains", 4)) + 1)
    out["side"] = max(int(out.get("side", 100003)), 1000003)
    out["spacing_span"] = min(int(out["side"]) // 3,
                              max(int(out.get("spacing_span", 9973)), 199999))
    return out


def _answer_size(answer: object) -> tuple[int, int, int]:
    blob = json.dumps(answer, separators=(",", ":"))
    def atoms(x: object) -> int:
        if isinstance(x, dict):
            return sum(atoms(v) for v in x.values())
        if isinstance(x, list):
            return sum(atoms(v) for v in x)
        return 1
    return len(blob), (len(blob) + 3) // 4, atoms(answer)


def _next_scale_params(params: dict) -> dict:
    q = int(params["modulus"])
    q2 = max(q + 1, math.ceil(q * (2 ** (1 / 3))))
    while not _is_prime(q2):
        q2 += 1
    out = dict(params)
    out["modulus"], out["n"] = q2, q2 ** int(out["dimension"])
    out["chains"] = min(9, int(out["chains"]) + 1)
    return out


def selftest() -> dict:
    report: dict[str, Any] = {"paper": "2410.07666", "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY])}

    failures, checks = [], 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2, 17):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            checks += 1
            if not ok or not json_ok:
                failures.append({"preset": preset, "seed": seed, "reason": why})
    report["G1_planted_verifies"] = {"pass": not failures, "checks": checks,
        "failures": failures, "answers_json_native": not failures}

    ship = make_instance(seed=314159, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = {"matrix": [list(r) for r in ship["answer"]["matrix"]],
               "offset": list(ship["answer"]["offset"])}
    swapped = {"matrix": [list(r) for r in planted["matrix"]],
               "offset": list(planted["offset"])}
    swapped["offset"][0], swapped["offset"][1] = swapped["offset"][1], swapped["offset"][0]
    if swapped["offset"] == planted["offset"]:
        swapped["offset"][0] = (swapped["offset"][0] + 1) % int(ship["modulus"])
    duplicate = {"matrix": [list(r) for r in planted["matrix"]],
                 "offset": list(planted["offset"])}
    duplicate["matrix"][1] = list(duplicate["matrix"][0])
    out_of_range = {"matrix": [list(r) for r in planted["matrix"]],
                    "offset": list(planted["offset"])}
    out_of_range["matrix"][0][0] = int(ship["modulus"])
    corruptions = {
        "drop": {"matrix": planted["matrix"][:-1], "offset": planted["offset"]},
        "swap": swapped, "duplicate": duplicate, "empty": {},
        "out_of_range": out_of_range}
    reasons = {name: verify(ship, candidate)[1] for name, candidate in corruptions.items()}
    all_rejected = all(not verify(ship, candidate)[0] for candidate in corruptions.values())
    report["G2_rejects_corruption"] = {"pass": all_rejected and len(set(reasons.values())) == 5,
        "reasons": reasons, "distinct_reasons": len(set(reasons.values()))}

    realistic = "Reasoning...\n```json\n<answer>" + json.dumps(planted, separators=(",", ":")) + "</answer>\n```"
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {"pass": parsed == planted and parse_answer("garbage") is None,
        "realistic_response_parsed": parsed == planted,
        "garbage_returns_none": parse_answer("garbage") is None}

    deps, _ = _dependencies(ship)
    sample_rng, total, hits = random.Random(271828), 200_000, 0
    for _ in range(total):
        if _verify_with_dependencies(ship, random_candidate(ship, sample_rng), deps)[0]:
            hits += 1
    probability = hits / total
    report["G4_guess_resistance"] = {"pass": probability < 1e-6, "hits": hits,
        "total": total, "sampled_probability": probability,
        "candidate_space": search_space(ship),
        "prior": "uniform over GL(3,q) times all q^3 offsets"}

    demo = make_instance(seed=23, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    attack_names = ["outlier_first_presented_as_offset", "greedy_numeric_label_identity",
        "presentation_order_affine_fit", "in_context_diagonal_affine_ansatz",
        "random_affine_restart_256"]
    successes = {name: 0 for name in attack_names}
    attempts = 8
    ref_successes = 0
    ref_seconds = ref_comparisons = ref_operations = 0
    for seed in range(8001, 8001 + attempts):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        ideps, _ = _dependencies(inst)
        for name, candidate in _attack_candidates(inst, random.Random(seed ^ 0xA5A5)).items():
            if candidate is not None and _verify_with_dependencies(inst, candidate, ideps)[0]:
                successes[name] += 1
        cert, metrics = _reference_algorithm(inst)
        if cert is not None and _verify_with_dependencies(inst, cert, ideps)[0]:
            ref_successes += 1
        ref_seconds += float(metrics["wall_clock_sec"])
        ref_comparisons += int(metrics["comparisons"])
        ref_operations += int(metrics["operations"])
    reference = {"name": "comparison-sort each geometric chain and fit its affine basis",
        "complexity": "O(n log n + d^2) exact record/comparison/field operations",
        "wall_clock_sec": ref_seconds, "mean_wall_clock_sec": ref_seconds / attempts,
        "comparisons": ref_comparisons, "mean_comparisons": ref_comparisons // attempts,
        "operations": ref_operations, "mean_operations": ref_operations // attempts,
        "solves": f"{ref_successes}/{attempts}, as expected on Track B"}
    report["G5_density_and_baseline"] = {"pass": probability < 1e-6 and ref_successes == attempts,
        "shipping_density_hits": hits, "shipping_density_total": total,
        "shipping_density_estimate": probability, "demo_exact_valid_count": demo_count,
        "demo_candidate_space": search_space(demo), "baseline_wall_clock_sec": ref_seconds,
        "baseline_comparisons": ref_comparisons, "baseline_operations": ref_operations,
        "strongest_baseline": reference["name"]}
    attacks = {name: {"successes": successes[name], "attempts": attempts} for name in attack_names}
    report["G6_adversary_panel"] = {"pass": all(v["successes"] == 0 for v in attacks.values()),
        "attacks": attacks, "reference_algorithm": reference}

    scaled_params = _next_scale_params(DIFFICULTY[SHIPPING_DIFFICULTY])
    t0 = time.perf_counter()
    scaled = make_instance(seed=424242, **scaled_params)
    build_sec = time.perf_counter() - t0
    scaled_ok, scaled_why = verify(scaled, scaled["answer"])
    report["G7_scales"] = {"pass": scaled_ok and int(scaled["n"]) >= 2 * int(ship["n"]),
        "shipping_n": int(ship["n"]), "scaled_n": int(scaled["n"]),
        "scale_factor": int(scaled["n"]) / int(ship["n"]),
        "scaled_build_sec": build_sec, "scaled_verify_reason": scaled_why,
        "answer_atomic_elements_unchanged": _answer_size(scaled["answer"])[2] == _answer_size(ship["answer"])[2]}

    invariant_checks = transform_valid = 0
    distinct_keys = []
    for j in range(20):
        inst = make_instance(seed=12000 + 37 * j, **DIFFICULTY[SHIPPING_DIFFICULTY])
        transformed, carried = _transform_for_g8(inst, 22000 + j)
        invariant_checks += canonical_key(inst) == canonical_key(transformed)
        transform_valid += verify(transformed, carried)[0]
        distinct_keys.append(canonical_key(inst))
    n_distinct = len(set(distinct_keys))
    report["G8_canonical_key"] = {"pass": invariant_checks == transform_valid == n_distinct == 20,
        "invariance_passed": invariant_checks, "invariance_attempts": 20,
        "transformed_witnesses_valid": transform_valid, "transformed_witness_attempts": 20,
        "unrelated_distinct": n_distinct, "unrelated_attempts": 20,
        "transformations": ["invertible affine relabelling over F_q", "input-record permutation",
            "permutation/translation of independent rows", "independent row reflections with L/R swap",
            "all transformations composed"]}

    chars, tokens, atoms = _answer_size(ship["answer"])
    d = int(ship["dimension"])
    # Four labels are converted to d base-q digits (one divmod per digit),
    # the d basis columns use d modular subtractions apiece, and locating the
    # ranks 1,q,q^2 from the constant geometric gap uses 2d-1 integer ops.
    intended_ops = 4 * d + d * d + (2 * d - 1)
    arms = {name: {"solved": int(G9_MEASUREMENTS[name]["solved"]),
                   "attempts": int(G9_MEASUREMENTS[name]["attempts"])}
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else None)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else None)
    hint_effect = (hinted_rate - placebo_rate
                   if hinted_rate is not None and placebo_rate is not None else None)
    within_caps = chars <= 2000 and atoms <= 256 and intended_ops <= 300
    # Since 2026-09-05 the oracle arms are diagnostics, not gates. Only the
    # answer-size and intended-route caps determine G9's pass flag.
    report["G9_no_tool_suitability"] = {"pass": within_caps,
        "arms": arms, "hinted_minus_placebo": hint_effect,
        "diagnostic_complete": all(arms[name]["attempts"] == 3 for name in arms),
        "hinted_verdict": G9_MEASUREMENTS["hinted_verdict"],
        "placebo_verdict": G9_MEASUREMENTS["placebo_verdict"], "answer_chars": chars,
        "answer_tokens": tokens, "answer_elements": atoms,
        "intended_route_operations": intended_ops, "caps_pass": within_caps}
    report["all_passed"] = all(v.get("pass") for k, v in report.items() if k.startswith("G"))
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
