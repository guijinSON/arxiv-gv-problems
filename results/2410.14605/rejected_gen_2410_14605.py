"""Verified representation-conversion generator for arXiv:2410.14605.

Section 2, equation (2.8) of Bulkhali--Sun states the equivalence

    T(x) + T(y)  ~  F(u) + G(v),

where T(t)=t(t+1)/2, F(t)=t(5t+1)/2, and G(t)=t(5t+3)/2.
The module supplies exact representations on one side and asks for
representations on the other.  Certificates are carried through a norm-five
Gaussian-integer change of coordinates; no generated target is solved.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import statistics
import time


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "After completing the paired quadratic terms to odd squares, a norm-five "
    "Gaussian-integer symmetry preserves their total."
)
PLACEBO_HINT: str = (
    "After organizing the displayed rows by direction and size, careful exact "
    "arithmetic preserves every required total."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "number_theory",
    "object_regime": "integer_lattice",
    "computational_core": "other",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "generalized triangular numbers",
        "integer-valued quadratic polynomials",
        "representations by ternary quadratic sums",
        "norm-five Gaussian-integer coordinate transformations",
    ],
    "verification_operations": [
        "exact integer polynomial evaluation",
        "exact integer range comparison",
        "exact equality of ternary quadratic sums",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Complete the paired quadratic terms to odd squares and recognize "
        "multiplication by a Gaussian integer of norm five; without that "
        "coordinate change one enumerates bounded pairs in every row."
    ),
    "hardness_basis": (
        "Track B: bounded meet-in-the-middle enumeration for the Section 2, "
        "equation (2.8) representation conversion is O(r*n^2) pair probes; "
        "at the shipping preset the measured reference cost is filled from "
        "selftest, while the norm-five coordinate route uses at most 24 exact "
        "operations per row and 288 operations for twelve rows."
    ),
    "max_answer_tokens": 128,
}

NATIVE: dict = {
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


# ``n`` controls the magnitude of every source coordinate and hence the area of
# the two-coordinate enumeration haystack.  The answer always has 12 records.
DIFFICULTY: dict = {
    "demo": {"n": 12, "rows": 1},
    "easy": {"n": 100_000, "rows": 12},
    "medium": {"n": 180_000, "rows": 12},
    "hard": {"n": 300_000, "rows": 12},
}
SHIPPING_DIFFICULTY: str = "easy"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON list in displayed row order.  Each record is [row_id,x,y,z]. "
        "There is exactly one record per row.  Coordinates are integers in the "
        "row-specific inclusive bounds printed in the statement: nonnegative "
        "for a T+T+T target, and the complete finite integer ranges implied by "
        "F(x)<=N, G(y)<=N, T(z)<=N for an F+G+T target."
    ),
    "bounds": {
        "max_rows": 12,
        "fields_per_record": 4,
        "row_order": "displayed order",
        "coordinate_bounds": "exact row-specific bounds derived from N",
    },
}

NOTES: str = (
    "Section 1 fixes universality over Z and the exact integer-valued ternary "
    "quadratic shape. Section 2 defines equivalence as equality of represented "
    "sets and equation (2.8), labelled (513) in the source, states "
    "T(x)+T(y) ~ F(x)+G(y). This is the family used here; no graph or finite-"
    "field surrogate is introduced. Completing squares gives "
    "40(T(a)+T(b))+10=5(2a+1)^2+5(2b+1)^2 and "
    "40(F(u)+G(v))+10=(10u+1)^2+(10v+3)^2. Multiplication by 1+2i or its "
    "conjugate carries a sampled source pair to the requested side, with signs "
    "and order selected modulo 10. Thus make_instance transforms a certificate "
    "it already holds and never searches the target. The paper proves an "
    "equivalence rather than computational hardness, so Track A is not claimed. "
    "The easy case is precisely recognizing that norm-five transformation: the "
    "mechanical alternative measured here enumerates bounded coordinate pairs. "
    "Rows mix both directions, shuffle the symmetric triangular coordinates, "
    "and use source coordinates from one common interval. The panel tests a "
    "magnitude outlier match, greedy term filling, source copying, a single "
    "unbranched norm-five ansatz, and structure-aware random restarts."
)


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 2_000_000
_INTENDED_OPS_PER_ROW = 24

# Filled only after the three isolated script-owned hardening runs.
_ORACLE_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "pending",
}


def _tri(x: int) -> int:
    return x * (x + 1) // 2


def _fifth_one(x: int) -> int:
    return x * (5 * x + 1) // 2


def _fifth_three(x: int) -> int:
    return x * (5 * x + 3) // 2


def _ceil_div(a: int, b: int) -> int:
    return -((-a) // b)


def _tri_upper(target: int) -> int:
    return (math.isqrt(8 * target + 1) - 1) // 2


def _forward_bounds(target: int) -> tuple[int, int, int, int, int, int]:
    # 40F(u)+1=(10u+1)^2 and 40G(v)+9=(10v+3)^2.
    ru = math.isqrt(40 * target + 1)
    rv = math.isqrt(40 * target + 9)
    return (
        _ceil_div(-ru - 1, 10),
        (ru - 1) // 10,
        _ceil_div(-rv - 3, 10),
        (rv - 3) // 10,
        0,
        _tri_upper(target),
    )


def _row_bounds(row: dict) -> list[list[int]]:
    target = row["target"]
    if row["direction"] == "TTT_to_FGT":
        lo_u, hi_u, lo_v, hi_v, lo_w, hi_w = _forward_bounds(target)
        return [[lo_u, hi_u], [lo_v, hi_v], [lo_w, hi_w]]
    upper = _tri_upper(target)
    return [[0, upper], [0, upper], [0, upper]]


def _normalise_residue(value: int, residue: int) -> int | None:
    if value % 10 == residue:
        return value
    if (-value) % 10 == residue:
        return -value
    return None


def _forward_images(a: int, b: int) -> list[tuple[int, int]]:
    """Every direct norm-five image compatible with F and G residues."""
    odd_a, odd_b = 2 * a + 1, 2 * b + 1
    images = []
    raw_pairs = (
        (odd_a + 2 * odd_b, 2 * odd_a - odd_b),
        (odd_a - 2 * odd_b, 2 * odd_a + odd_b),
    )
    for first, second in raw_pairs:
        for candidate_u, candidate_v in ((first, second), (second, first)):
            square_u = _normalise_residue(candidate_u, 1)
            square_v = _normalise_residue(candidate_v, 3)
            if square_u is None or square_v is None:
                continue
            u = (square_u - 1) // 10
            v = (square_v - 3) // 10
            if _fifth_one(u) + _fifth_three(v) == _tri(a) + _tri(b):
                if (u, v) not in images:
                    images.append((u, v))
    return images


def _source_valid(row: dict) -> bool:
    source = row.get("source")
    if not isinstance(source, list) or len(source) != 3:
        return False
    if any(isinstance(x, bool) or not isinstance(x, int) for x in source):
        return False
    if row["direction"] == "TTT_to_FGT":
        value = sum(_tri(x) for x in source)
    elif row["direction"] == "FGT_to_TTT":
        value = _fifth_one(source[0]) + _fifth_three(source[1]) + _tri(source[2])
    else:
        return False
    return value == row.get("target")


def _validate_params(n: int, rows: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 6:
        raise ValueError("n must be an integer at least 6")
    if isinstance(rows, bool) or not isinstance(rows, int) or not 1 <= rows <= 12:
        raise ValueError("rows must be an integer in 1..12")


def make_instance(n, seed=0, **params) -> dict:
    """Transform sampled representations through the paper's equivalence."""
    rows = params.pop("rows", 12)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, rows)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    rng = random.Random(seed)

    directions = ["TTT_to_FGT" if i % 2 == 0 else "FGT_to_TTT"
                  for i in range(rows)]
    rng.shuffle(directions)
    used_labels = set()
    public_rows = []
    answers_by_label = {}

    for direction in directions:
        for _ in range(10_000):
            a = rng.randrange(n, 2 * n)
            b = rng.randrange(n, 2 * n)
            c = rng.randrange(n, 2 * n)
            if (2 * a + 1) % 5 == 0 and (2 * b + 1) % 5 == 0:
                continue
            images = _forward_images(a, b)
            if images:
                break
        else:
            raise RuntimeError("could not sample a transformable triangular pair")

        u, v = rng.choice(images)
        target = _tri(a) + _tri(b) + _tri(c)
        while True:
            label = rng.randrange(10_000, 99_999)
            if label not in used_labels:
                used_labels.add(label)
                break

        if direction == "TTT_to_FGT":
            source = [a, b, c]
            rng.shuffle(source)
            answer_coords = [u, v, c]
        else:
            source = [u, v, c]
            answer_coords = [a, b, c]
            rng.shuffle(answer_coords)

        row = {
            "id": label,
            "direction": direction,
            "target": target,
            "source": source,
        }
        if not _source_valid(row):
            raise AssertionError("constructed source representation is invalid")
        public_rows.append(row)
        answers_by_label[label] = [label] + answer_coords

    rng.shuffle(public_rows)
    answer = [answers_by_label[row["id"]] for row in public_rows]
    inst = {
        "family": "norm5_representation_conversion",
        "n": n,
        "rows": public_rows,
        "answer": answer,
    }
    ok, why = verify(inst, answer)
    if not ok:
        raise AssertionError("constructed answer failed verification: " + why)
    return inst


def render(inst) -> str:
    lines = [
        "Representation conversion for three integer-valued quadratic terms",
        "",
        "For every integer t define",
        "  T(t) = t(t+1)/2,",
        "  F(t) = t(5t+1)/2,",
        "  G(t) = t(5t+3)/2.",
        "These expressions are integers for every integer t.",
        "",
        "Each row below supplies an exact representation of its target N on one",
        "side. Find any representation on the named target side, subject to the",
        "printed inclusive coordinate bounds. Rows are independent.",
        "",
    ]
    for row in inst["rows"]:
        bounds = _row_bounds(row)
        if row["direction"] == "TTT_to_FGT":
            source_name = "T(a)+T(b)+T(c)"
            target_name = "F(x)+G(y)+T(z)"
        else:
            source_name = "F(a)+G(b)+T(c)"
            target_name = "T(x)+T(y)+T(z)"
        lines.extend([
            f"row {row['id']}:",
            f"  N = {row['target']}",
            f"  supplied {source_name} coordinates = {json.dumps(row['source'])}",
            f"  required target: {target_name} = N",
            "  bounds: "
            + ", ".join(
                f"{name} in [{bound[0]}, {bound[1]}]"
                for name, bound in zip(("x", "y", "z"), bounds)
            ),
            "",
        ])
    lines.extend([
        "Use the rows in exactly the displayed order. Bounds are closed; negative",
        "coordinates are allowed only where a printed lower bound is negative.",
        "All arithmetic and equalities are exact over the integers.",
        "",
        "Give your final answer inside <answer></answer> tags as one JSON list.",
        "Each displayed row contributes [row_id,x,y,z], in displayed order.",
        "Example: <answer>[[12345,2,-1,4],[67890,0,3,7]]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text) -> object | None:
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    if body.startswith("```") and body.endswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
    try:
        answer = json.loads(body)
    except (TypeError, ValueError):
        return None
    return answer


def verify(inst, answer) -> tuple[bool, str]:
    rows = inst.get("rows")
    if not isinstance(rows, list) or not rows:
        return False, "instance has no rows"
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if len(answer) != len(rows):
        return False, f"expected {len(rows)} row records"

    parsed_records = []
    for position, record in enumerate(answer):
        if not isinstance(record, list) or len(record) != 4:
            return False, f"record {position} must be [row_id,x,y,z]"
        if any(isinstance(value, bool) or not isinstance(value, int)
               for value in record):
            return False, f"record {position} contains a non-integer"
        parsed_records.append(record)

    labels = [record[0] for record in parsed_records]
    if len(set(labels)) != len(labels):
        return False, "duplicate row label"
    expected_labels = [row["id"] for row in rows]
    if labels != expected_labels:
        return False, "row labels are not in displayed order"

    for row, record in zip(rows, parsed_records):
        coordinates = record[1:]
        bounds = _row_bounds(row)
        if any(value < lower or value > upper
               for value, (lower, upper) in zip(coordinates, bounds)):
            return False, f"row {row['id']} has a coordinate out of range"
        x, y, z = coordinates
        if row["direction"] == "TTT_to_FGT":
            value = _fifth_one(x) + _fifth_three(y) + _tri(z)
        else:
            value = _tri(x) + _tri(y) + _tri(z)
        if value != row["target"]:
            return False, f"row {row['id']} does not represent its target"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    answer = []
    for row in inst["rows"]:
        coordinates = [rng.randint(lower, upper)
                       for lower, upper in _row_bounds(row)]
        answer.append([row["id"]] + coordinates)
    return answer


def search_space(inst) -> int | None:
    total = 1
    for row in inst["rows"]:
        for lower, upper in _row_bounds(row):
            total *= upper - lower + 1
    return total


def _is_triangular(value: int) -> int | None:
    if value < 0:
        return None
    discriminant = 8 * value + 1
    root = math.isqrt(discriminant)
    if root * root == discriminant and root % 2 == 1:
        return (root - 1) // 2
    return None


def _pair_work(row: dict) -> int:
    bounds = _row_bounds(row)
    return (bounds[0][1] - bounds[0][0] + 1) * (bounds[1][1] - bounds[1][0] + 1)


def _count_row_solutions(row: dict) -> int:
    bounds = _row_bounds(row)
    count = 0
    if row["direction"] == "TTT_to_FGT":
        for u in range(bounds[0][0], bounds[0][1] + 1):
            first = _fifth_one(u)
            for v in range(bounds[1][0], bounds[1][1] + 1):
                remaining = row["target"] - first - _fifth_three(v)
                if _is_triangular(remaining) is not None:
                    count += 1
    else:
        upper = bounds[0][1]
        for a in range(upper + 1):
            first = _tri(a)
            for b in range(upper + 1):
                remaining = row["target"] - first - _tri(b)
                if remaining < 0:
                    break
                if _is_triangular(remaining) is not None:
                    count += 1
    return count


def enumerate_all(inst) -> int | None:
    if sum(_pair_work(row) for row in inst["rows"]) > _ENUMERATION_CAP:
        return None
    total = 1
    for row in inst["rows"]:
        total *= _count_row_solutions(row)
    return total


def _canonical_source(row: dict) -> list[int]:
    source = row["source"]
    if row["direction"] == "TTT_to_FGT":
        return sorted(_tri(value) for value in source)
    return [_fifth_one(source[0]), _fifth_three(source[1]), _tri(source[2])]


def canonical_key(inst) -> str:
    canonical_rows = sorted(
        [row["direction"], row["target"], _canonical_source(row)]
        for row in inst["rows"]
    )
    payload = json.dumps(canonical_rows, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params) -> dict | str | None:
    if not isinstance(params, dict):
        return None
    n = params.get("n")
    rows = params.get("rows", 12)
    try:
        _validate_params(n, rows)
    except (TypeError, ValueError):
        return None
    # Fixed row count: this grows only the enumeration haystack.  Stop only when
    # the larger coordinate strings would actually threaten the character cap.
    next_n = n * 2
    estimated_chars = rows * (4 * len(str(4 * next_n)) + 18) + 2
    if estimated_chars > 1_900:
        return "cap_bound"
    return {"n": next_n, "rows": rows}


def _inverse_f_positive(value: int) -> int:
    return max(0, (math.isqrt(40 * max(value, 0) + 1) - 1) // 10)


def _inverse_g_positive(value: int) -> int:
    return max(0, (math.isqrt(40 * max(value, 0) + 9) - 3) // 10)


def _attack_copy_source(inst: dict) -> list[list[int]]:
    result = []
    for row in inst["rows"]:
        values = list(row["source"])
        bounds = _row_bounds(row)
        values = [min(max(value, lower), upper)
                  for value, (lower, upper) in zip(values, bounds)]
        result.append([row["id"]] + values)
    return result


def _attack_magnitude_match(inst: dict) -> list[list[int]]:
    result = []
    for row in inst["rows"]:
        source = row["source"]
        if row["direction"] == "TTT_to_FGT":
            ordered = sorted(source, key=lambda value: _tri(value), reverse=True)
            u = _inverse_f_positive(_tri(ordered[0]))
            v = _inverse_g_positive(_tri(ordered[1]))
            coords = [u, v, ordered[2]]
        else:
            contributions = [
                _fifth_one(source[0]),
                _fifth_three(source[1]),
                _tri(source[2]),
            ]
            coords = [_tri_upper(value) for value in contributions]
        result.append([row["id"]] + coords)
    return result


def _attack_greedy(inst: dict) -> list[list[int]]:
    result = []
    for row in inst["rows"]:
        remaining = row["target"]
        if row["direction"] == "TTT_to_FGT":
            u = _inverse_f_positive(remaining)
            remaining -= _fifth_one(u)
            v = _inverse_g_positive(remaining)
            remaining -= _fifth_three(v)
            w = _tri_upper(remaining)
            coords = [u, v, w]
        else:
            coords = []
            for _ in range(3):
                value = _tri_upper(remaining)
                coords.append(value)
                remaining -= _tri(value)
        result.append([row["id"]] + coords)
    return result


def _fixed_forward(a: int, b: int) -> tuple[int, int] | None:
    odd_a, odd_b = 2 * a + 1, 2 * b + 1
    raw_u, raw_v = odd_a + 2 * odd_b, 2 * odd_a - odd_b
    square_u = _normalise_residue(raw_u, 1)
    square_v = _normalise_residue(raw_v, 3)
    if square_u is None or square_v is None:
        return None
    return (square_u - 1) // 10, (square_v - 3) // 10


def _attack_fixed_norm5(inst: dict) -> list[list[int]]:
    """Runnable by hand, but deliberately omits conjugation and coordinate swap."""
    result = []
    for row in inst["rows"]:
        source = row["source"]
        if row["direction"] == "TTT_to_FGT":
            pair = _fixed_forward(source[0], source[1])
            coords = [0, 0, source[2]] if pair is None else [pair[0], pair[1], source[2]]
        else:
            square_u = 10 * source[0] + 1
            square_v = 10 * source[1] + 3
            num_a = square_u + 2 * square_v
            num_b = 2 * square_u - square_v
            if num_a % 5 or num_b % 5:
                coords = [0, 0, max(0, source[2])]
            else:
                odd_a, odd_b = num_a // 5, num_b // 5
                a = (odd_a - 1) // 2
                b = (odd_b - 1) // 2
                coords = [a, b, max(0, source[2])]
                bounds = _row_bounds(row)
                coords = [min(max(value, lower), upper)
                          for value, (lower, upper) in zip(coords, bounds)]
        result.append([row["id"]] + coords)
    return result


def _reference_solve_row(row: dict) -> tuple[list[int] | None, int]:
    """Exact bounded pair enumeration; returns (coordinates, pair probes)."""
    bounds = _row_bounds(row)
    probes = 0
    if row["direction"] == "TTT_to_FGT":
        for u in range(bounds[0][0], bounds[0][1] + 1):
            first = _fifth_one(u)
            for v in range(bounds[1][0], bounds[1][1] + 1):
                probes += 1
                remaining = row["target"] - first - _fifth_three(v)
                w = _is_triangular(remaining)
                if w is not None:
                    return [u, v, w], probes
    else:
        upper = bounds[0][1]
        for a in range(upper + 1):
            first = _tri(a)
            for b in range(upper + 1):
                probes += 1
                remaining = row["target"] - first - _tri(b)
                if remaining < 0:
                    break
                w = _is_triangular(remaining)
                if w is not None:
                    return [a, b, w], probes
    return None, probes


def _reference_algorithm(inst: dict) -> tuple[list[list[int]] | None, int]:
    answer = []
    probes = 0
    for row in inst["rows"]:
        coordinates, used = _reference_solve_row(row)
        probes += used
        if coordinates is None:
            return None, probes
        answer.append([row["id"]] + coordinates)
    return answer, probes


def _answer_atoms(answer) -> int:
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def _corruptions(inst: dict) -> dict[str, object]:
    answer = json.loads(json.dumps(inst["answer"]))
    dropped = json.loads(json.dumps(answer[:-1]))
    empty = []

    duplicated = json.loads(json.dumps(answer))
    if len(duplicated) >= 2:
        duplicated[1] = list(duplicated[0])
    else:
        duplicated.append(list(duplicated[0]))

    out_of_range = json.loads(json.dumps(answer))
    first_bounds = _row_bounds(inst["rows"][0])
    out_of_range[0][1] = first_bounds[0][1] + 1

    swapped = None
    for row_index, row in enumerate(inst["rows"]):
        for left, right in ((1, 2), (1, 3), (2, 3)):
            candidate = json.loads(json.dumps(answer))
            candidate[row_index][left], candidate[row_index][right] = (
                candidate[row_index][right], candidate[row_index][left]
            )
            ok, _ = verify(inst, candidate)
            if not ok:
                swapped = candidate
                break
        if swapped is not None:
            break
    if swapped is None:
        swapped = json.loads(json.dumps(answer))
        swapped[0][1] += 1

    return {
        "drop_one": dropped,
        "swap_one": swapped,
        "duplicate": duplicated,
        "empty": empty,
        "out_of_range": out_of_range,
    }


def _transformed_instance(inst: dict, seed: int) -> tuple[dict, list[list[int]]]:
    """Compose row reorder, row relabel, and genuine source symmetries."""
    rng = random.Random(seed)
    answer_map = {record[0]: record[1:] for record in inst["answer"]}
    rows = json.loads(json.dumps(inst["rows"]))
    rng.shuffle(rows)
    carried = []
    for position, row in enumerate(rows):
        old_label = row["id"]
        new_label = 200_000 + 97 * position + rng.randrange(1, 80)
        row["id"] = new_label
        if row["direction"] == "TTT_to_FGT":
            rng.shuffle(row["source"])
            index = rng.randrange(3)
            row["source"][index] = -row["source"][index] - 1
        else:
            row["source"][2] = -row["source"][2] - 1
        if not _source_valid(row):
            raise AssertionError("claimed source symmetry did not preserve a row")
        carried.append([new_label] + answer_map[old_label])
    transformed = {
        "family": inst["family"],
        "n": inst["n"],
        "rows": rows,
        # This key is irrelevant to verify and canonical_key, but keep the object
        # schema complete for render and external callers.
        "answer": carried,
    }
    return transformed, carried


def selftest() -> dict:
    report = {}

    # G1: every named rung and several independent seeds.
    planted_checks = 0
    json_checks = 0
    g1_reasons = []
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            planted_checks += 1
            if not ok:
                g1_reasons.append(f"{preset}/{seed}: {why}")
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_checks += 1
    report["G1_planted_verifies"] = {
        "pass": not g1_reasons and json_checks == planted_checks,
        "verified": planted_checks - len(g1_reasons),
        "attempts": planted_checks,
        "json_native": json_checks,
        "failures": g1_reasons,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    sample_inst = make_instance(seed=91, **shipping)

    # G2: five structurally distinct corruptions and five distinct diagnostics.
    corruption_results = {}
    reasons = []
    for name, candidate in _corruptions(sample_inst).items():
        ok, why = verify(sample_inst, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": why}
        reasons.append(why)
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruption_results.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "cases": corruption_results,
    }

    # G3: tagged JSON surrounded by realistic prose and a markdown fence.
    blob = json.dumps(sample_inst["answer"], separators=(",", ":"))
    response = "I used the quadratic-form identity.\n<answer>\n```json\n" + blob + "\n```\n</answer>\n"
    parsed = parse_answer(response)
    malformed = parse_answer("The answer is probably a short list.")
    report["G3_round_trip"] = {
        "pass": parsed == sample_inst["answer"] and malformed is None,
        "realistic_response_parsed": parsed == sample_inst["answer"],
        "garbage_returned_none": malformed is None,
    }

    # G4 and the shipping-density half of G5 share the mandated 200k draw.
    guess_rng = random.Random(0x241014605)
    guess_samples = 200_000
    guess_hits = 0
    for _ in range(guess_samples):
        candidate = random_candidate(sample_inst, guess_rng)
        if verify(sample_inst, candidate)[0]:
            guess_hits += 1
    guess_probability = guess_hits / guess_samples
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_samples,
        "probability": guess_probability,
        "space": search_space(sample_inst),
        "sampler": "uniform in every printed coordinate interval, with exact row shape and labels",
    }

    demo_inst = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)

    # G6: attacks on eight shipping instances plus the successful Track-B
    # reference algorithm.  Timings/probes are retained for G5 as well.
    attack_names = {
        "magnitude_outlier_match": _attack_magnitude_match,
        "greedy_largest_term_first": _attack_greedy,
        "copy_supplied_coordinates": _attack_copy_source,
        "single_orientation_norm5_ansatz": _attack_fixed_norm5,
    }
    attack_results = {name: {"successes": 0, "attempts": 0}
                      for name in attack_names}
    attack_results["structure_aware_random_restart_256"] = {
        "successes": 0,
        "attempts": 0,
    }
    reference_successes = 0
    reference_times = []
    reference_probes = []
    for seed in range(8):
        inst = make_instance(seed=10_000 + seed, **shipping)
        for name, attack in attack_names.items():
            attack_results[name]["attempts"] += 1
            if verify(inst, attack(inst))[0]:
                attack_results[name]["successes"] += 1
        restart_rng = random.Random(50_000 + seed)
        restart_solved = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, restart_rng))[0]:
                restart_solved = True
                break
        attack_results["structure_aware_random_restart_256"]["attempts"] += 1
        attack_results["structure_aware_random_restart_256"]["successes"] += int(restart_solved)

        started = time.perf_counter()
        reference_answer, probes = _reference_algorithm(inst)
        elapsed = time.perf_counter() - started
        solved = reference_answer is not None and verify(inst, reference_answer)[0]
        reference_successes += int(solved)
        reference_times.append(elapsed)
        reference_probes.append(probes)

    all_attacks_failed = all(item["successes"] == 0 for item in attack_results.values())
    reference = {
        "name": "bounded exact pair enumeration with triangular discriminant test",
        "complexity": "O(rows*n^2) worst-case exact",
        "wall_clock_sec_median": statistics.median(reference_times),
        "wall_clock_sec_max": max(reference_times),
        "pair_probes_median": int(statistics.median(reference_probes)),
        "pair_probes_max": max(reference_probes),
        "operation_count_median": int(statistics.median(reference_probes)) * 6,
        "successes": reference_successes,
        "attempts": 8,
        "solves": f"{reference_successes}/8, as expected",
    }
    report["G5_density_and_baseline"] = {
        "pass": demo_count is not None and demo_count > 0
        and guess_probability < 1e-6 and reference_successes == 8,
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_samples,
        "shipping_density_estimate": guess_probability,
        "demo_exact_valid_answer_count": demo_count,
        "baseline_wall_clock_sec_median": reference["wall_clock_sec_median"],
        "baseline_pair_probes_median": reference["pair_probes_median"],
        "baseline_pair_probes_max": reference["pair_probes_max"],
    }
    report["G6_adversary_panel"] = {
        "pass": all_attacks_failed and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": reference,
    }

    # G7: double the only difficulty axis while holding answer atoms fixed.
    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=777, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    base_space = search_space(sample_inst)
    doubled_space = search_space(doubled)
    report["G7_scales"] = {
        "pass": doubled_ok and doubled_space > base_space
        and _answer_atoms(doubled["answer"]) == _answer_atoms(sample_inst["answer"]),
        "base_n": shipping["n"],
        "doubled_n": doubled_params["n"],
        "base_space_bits": base_space.bit_length(),
        "doubled_space_bits": doubled_space.bit_length(),
        "answer_atoms_each": _answer_atoms(doubled["answer"]),
        "verify_reason": doubled_reason,
    }

    # G8: the tested transformations are row order, row IDs, permutations of
    # the symmetric TTT source, triangular reflection, and their composition.
    invariant = 0
    preserved = 0
    original_answer_preserved = 0
    keys = []
    for seed in range(20):
        inst = make_instance(seed=20_000 + seed, **shipping)
        transformed, carried = _transformed_instance(inst, 30_000 + seed)
        if canonical_key(inst) == canonical_key(transformed):
            invariant += 1
        if verify(transformed, carried)[0]:
            preserved += 1

        source_only = json.loads(json.dumps(inst))
        for row in source_only["rows"]:
            if row["direction"] == "TTT_to_FGT":
                row["source"].reverse()
                row["source"][0] = -row["source"][0] - 1
            else:
                row["source"][2] = -row["source"][2] - 1
        if canonical_key(inst) == canonical_key(source_only) and verify(
                source_only, inst["answer"])[0]:
            original_answer_preserved += 1
        keys.append(canonical_key(inst))
    distinct = len(set(keys))
    report["G8_canonical_key"] = {
        "pass": invariant == 20 and preserved == 20
        and original_answer_preserved == 20 and distinct == 20,
        "invariance_passed": invariant,
        "invariance_attempts": 20,
        "carried_witness_verified": preserved,
        "original_witness_verified_after_source_symmetry": original_answer_preserved,
        "distinct_unrelated_keys": distinct,
        "distinctness_attempts": 20,
        "transformations": [
            "row reordering",
            "row-label relabelling",
            "permutation of TTT source coordinates",
            "triangular reflection t -> -t-1",
            "composition of all listed transformations",
        ],
    }

    answer_blobs = []
    answer_atoms = []
    for seed in range(20):
        inst = make_instance(seed=40_000 + seed, **shipping)
        answer_blobs.append(json.dumps(inst["answer"], separators=(",", ":")))
        answer_atoms.append(_answer_atoms(inst["answer"]))
    answer_chars = max(map(len, answer_blobs))
    answer_tokens = (answer_chars + 3) // 4
    max_atoms = max(answer_atoms)
    route_ops = _INTENDED_OPS_PER_ROW * shipping["rows"]
    arms = {
        name: dict(_ORACLE_EVIDENCE[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    hinted_hardened = (
        _ORACLE_EVIDENCE["hinted_verdict"] == "hardened"
        and arms["hinted"]["attempts"] >= 3
        and arms["hinted"]["solved"] == 0
    )
    within_caps = answer_chars <= 2_000 and max_atoms <= 256 and route_ops <= 300
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _ORACLE_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": max_atoms,
        "intended_route_operations": route_ops,
        "within_caps": within_caps,
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping)
    report["all_passed"] = all(
        value.get("pass") is True
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
