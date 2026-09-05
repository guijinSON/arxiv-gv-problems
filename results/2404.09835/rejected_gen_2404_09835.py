"""Verified problem generator for arXiv:2404.09835.

The paper works with axis-aligned 2-by-2 squares in integer-coordinate grid
polygons.  This module keeps those native objects.  A submitted one-row matrix
is a compact symbolic packing: the public decoder expands it into one square
per reference centre, and the verifier checks containment and disjointness
against the displayed polygon with integer arithmetic only.
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
try:  # The implementation is deliberately stdlib-only, but keep repo access sane.
    from gvlib import exact_matrices, rationals
except ImportError:  # pragma: no cover - no helper is required
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE: dict = {
    "native_domain": "geometry",
    "object_regime": "integer_lattice",
    "computational_core": "linear_algebra",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "simple integer-coordinate orthogonal polygon",
        "axis-aligned 2-by-2 squares",
        "one-row modular decoder matrix for a compressed packing",
    ],
    "verification_operations": [
        "exact modular matrix-vector multiplication",
        "exact integer point-in-grid-polygon tests",
        "exact axis-aligned rectangle overlap tests",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize that the dense displacement decoder is the inverse of a "
        "two-tap operator along one directed cycle; without that change of "
        "variables, recovering the compact packing key requires dense exact "
        "elimination."
    ),
    "hardness_basis": (
        "Track B: enumerate the polygon's integer square positions and solve "
        "the resulting dense modular system by Gaussian elimination in O(n^3); "
        "at final tested n=48,p=65537 this took a median 0.000629 seconds and "
        "17,493 counted exact field operations per instance, whereas the cyclic "
        "two-tap route takes exactly 3n=144 exact operations."
    ),
    "max_answer_tokens": 73,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 4, "p": 17},
    "easy": {"n": 48, "p": 4099},
    "medium": {"n": 48, "p": 65537},
    "hard": {"n": 48, "p": 1000003},
}
SHIPPING_DIFFICULTY: str = "medium"

STRUCTURAL_HINT: str = (
    "Along the displayed directed cycle, the dense offset matrix is the "
    "inverse of a two-tap linear operator."
)
PLACEBO_HINT: str = (
    "Across the displayed coordinate data, careful indexing and exact modular "
    "arithmetic are both important."
)

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A JSON one-row n-column matrix [[x_0,...,x_(n-1)]] over GF(p): "
        "entries are pairwise distinct integers in 0..p-1.  The public dense "
        "decoder expands it to exactly n integer-coordinate 2-by-2 squares."
    ),
    "bounds": {
        "rows": 1,
        "columns": "n",
        "entry_min": 0,
        "entry_max": "p-1",
        "entries_pairwise_distinct": True,
        "candidate_count": "p!/(p-n)!",
        "max_named_n": 96,
        "max_named_prime": 1000003,
    },
}

NOTES: str = r"""
Section 1 defines 2x2-Square-Packing: place k axis-aligned 2-by-2 squares in a
polygon with pairwise disjoint interiors.  Section 2.2 fixes the exact discrete
model.  Lemma 6 says an integer-coordinate grid polygon admitting k squares has
such a packing at integer coordinates.  Lemma 7 says every integer-coordinate
2-by-2 square covers exactly one odd/odd unit reference centre, so the number of
reference centres is an exact packing upper bound.  Theorem 1 is worst-case
NP-hardness even for orthogonally convex grid polygons; it says nothing about
the inverse-generated distribution here.

The easy cases matter.  Section 1.1 reports polynomial algorithms for some
families of simple grid polygons and a PTAS even with holes.  This module's
height-two comb polygons are intentionally easy once an expanded packing is
allowed: every tooth exposes its unique square.  Therefore a Track A claim
would be false.  The task is the paper-motivated compressed-certificate issue
noted around its NP-membership discussion: recover a bounded symbolic key whose
public decoder expands to an actual perfect packing.

Generation is inverse.  It samples the pairwise-distinct key x first.  For a
public directed cycle rho, let (Pz)_i=z_(rho(i)) and B=I+3P over GF(p).  The
geometric-series identity

  B^-1 = (1-(-3)^n)^-1 sum_(j=0)^(n-1) (-3)^j P^j

constructs the dense decoder A without solving anything.  The tooth offsets are
y=A x, and the polygon is drawn around the resulting n disjoint squares.  A
candidate is checked by recomputing A x, expanding all squares, and testing the
native geometry.  No verifier branch reads inst["answer"].

The certificate-producing reference method scans the tooth edges to get y and
performs generic modular Gaussian elimination on A x=y.  It succeeds by design
and is reported separately, as Track B requires.  The compact route recognizes
A=B^-1 and computes x_i=y_i+3y_(rho(i)); extracting n offsets, multiplying n
times, and adding n times is counted conservatively as 3n exact operations.
The outlier-rank, diagonal greedy, uniform-restart, and direct-offset ansatz
attacks all submit well-formed keys but do not perform that change of variables.
""".strip()


G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "too_easy",
}

_ANSWER_RE = re.compile(
    r"<answer\b[^>]*>(.*?)</answer\s*>", re.IGNORECASE | re.DOTALL
)
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)
_TAP = 3


def _is_prime(value: int) -> bool:
    if isinstance(value, bool) or not isinstance(value, int) or value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def _random_cycle(size: int, rng: random.Random) -> list[int]:
    order = list(range(size))
    rng.shuffle(order)
    rho = [0] * size
    for i, value in enumerate(order):
        rho[value] = order[(i + 1) % size]
    return rho


def _inverse_two_tap(size: int, p: int, rho: list[int]) -> list[list[int]]:
    """Return (I + 3P_rho)^-1 by a finite geometric identity."""
    ratio = (-_TAP) % p
    denominator = (1 - pow(ratio, size, p)) % p
    if denominator == 0:
        raise ValueError("I + 3P is singular for these parameters")
    scale = pow(denominator, p - 2, p)
    matrix = [[0] * size for _ in range(size)]
    for row in range(size):
        column = row
        coefficient = scale
        for _ in range(size):
            matrix[row][column] = coefficient
            coefficient = coefficient * ratio % p
            column = rho[column]
    return matrix


def _matvec(matrix: list[list[int]], vector: list[int], p: int) -> list[int]:
    return [sum(a * b for a, b in zip(row, vector)) % p for row in matrix]


def _polygon_for_offsets(offsets: list[int], p: int) -> tuple[list[list[int]], list[int], int]:
    """Make a height-two comb: one isolated two-cell tooth per lane."""
    stride = p + 7
    bases = [i * stride for i in range(len(offsets))]
    teeth = [base + 2 + offset for base, offset in zip(bases, offsets)]
    width = len(offsets) * stride
    vertices: list[list[int]] = [[0, 0], [width, 0], [width, 1]]
    cursor = width
    for q in reversed(teeth):
        right = q + 2
        if cursor != right:
            vertices.append([right, 1])
        vertices.extend([[right, 2], [q, 2], [q, 1]])
        cursor = q
    if cursor != 0:
        vertices.append([0, 1])
    return vertices, bases, stride


def _map_vertex(vertex: list[int], frame: dict) -> list[int]:
    x, y = vertex
    return [frame["ox"] + frame["sx"] * x,
            frame["oy"] + frame["sy"] * y]


def _unmap_vertex(vertex: list[int], frame: dict) -> list[int]:
    x, y = vertex
    return [(x - frame["ox"]) * frame["sx"],
            (y - frame["oy"]) * frame["sy"]]


def _rotate_boundary(vertices: list[list[int]], rng: random.Random) -> list[list[int]]:
    shift = rng.randrange(len(vertices))
    moved = vertices[shift:] + vertices[:shift]
    if rng.randrange(2):
        moved = list(reversed(moved))
    return moved


def _make_instance(n: int, p: int, seed: int = 0) -> dict:
    if isinstance(n, bool) or not isinstance(n, int) or n < 4:
        raise ValueError("n must be an integer at least 4")
    if not _is_prime(p) or p <= n:
        raise ValueError("p must be prime and greater than n")
    rng = random.Random(seed)
    rho = _random_cycle(n, rng)
    matrix = _inverse_two_tap(n, p, rho)

    # Both the certificate language and all simple attacks enforce distinctness.
    # Resample before building the instance, never after seeing/solving it.
    for _ in range(10_000):
        key = rng.sample(range(p), n)
        offsets = _matvec(matrix, key, p)
        if len(set(offsets)) == n:
            break
    else:  # pragma: no cover - named presets have overwhelming success probability
        raise RuntimeError("could not sample distinct visible tooth offsets")

    canonical_polygon, bases, stride = _polygon_for_offsets(offsets, p)
    frame = {
        "ox": rng.randrange(-10_000, 10_001),
        "oy": rng.randrange(-10_000, 10_001),
        "sx": rng.choice((-1, 1)),
        "sy": rng.choice((-1, 1)),
    }
    polygon = [_map_vertex(v, frame) for v in canonical_polygon]
    polygon = _rotate_boundary(polygon, rng)
    row_records = [
        {"lane_base": bases[i], "coefficients": list(matrix[i])}
        for i in range(n)
    ]
    return {
        "family": "compressed perfect 2-by-2-square packing",
        "n": n,
        "field_prime": p,
        "tap": _TAP,
        "cycle": rho,
        "stride": stride,
        "frame": frame,
        "polygon": polygon,
        "decoder_rows": row_records,
        "target_squares": n,
        "answer": [key],
    }


# Keep the requested make_instance(n, seed=0, **params) interface while allowing
# DIFFICULTY to pass p as a named argument.
def make_instance(n, seed=0, **params) -> dict:  # type: ignore[no-redef]
    if "p" not in params:
        raise ValueError("missing required prime parameter p")
    extra = set(params) - {"p"}
    if extra:
        raise ValueError("unknown parameters: " + ", ".join(sorted(extra)))
    return _make_instance(n, params["p"], seed)


def _format_vertices(vertices: list[list[int]]) -> str:
    lines = []
    for start in range(0, len(vertices), 10):
        chunk = vertices[start:start + 10]
        lines.append("  " + " ".join(f"({x},{y})" for x, y in chunk))
    return "\n".join(lines)


def _format_matrix(rows: list[dict]) -> str:
    return "\n".join(
        f"  {i}: base={row['lane_base']}  A[{i}]=["
        + ",".join(str(v) for v in row["coefficients"]) + "]"
        for i, row in enumerate(rows)
    )


def render(inst) -> str:
    """Render the complete self-contained packing problem."""
    n = inst["n"]
    p = inst["field_prime"]
    cycle_text = ",".join(str(v) for v in inst["cycle"])
    frame = inst["frame"]
    statement = f"""COMPRESSED PERFECT PACKING OF A SIMPLE GRID POLYGON

A simple grid polygon is the closed region bounded by a non-self-intersecting
cycle of horizontal and vertical segments whose vertices have integer
coordinates.  The vertices below are consecutive around the boundary; the
starting vertex and orientation carry no meaning.

You must give a compact key for {n} closed, axis-aligned 2-by-2 squares.  Every
decoded square must lie wholly in the polygon, and square interiors must be
pairwise disjoint.  Touching along boundaries is allowed.

All arithmetic in the decoder is over GF({p}): reduce to the least
nonnegative residue in 0..{p - 1}.  Your answer is one JSON row
[[x_0,...,x_{n - 1}]] containing exactly {n} PAIRWISE DISTINCT integers in
0..{p - 1}; coordinates and indices are 0-based, and order matters.

For decoder row i, compute

    s_i = sum(A[i][j] * x_j for j=0..{n - 1}) mod {p}.

The row's canonical square has lower-left corner
(base_i + 2 + s_i, 0) and upper-right corner
(base_i + 4 + s_i, 2).  Map each canonical point (u,v) to the displayed
polygon by X(u)={frame['ox']}+({frame['sx']})*u and
Y(v)={frame['oy']}+({frame['sy']})*v.  If an axis is reflected, take the
smaller mapped coordinate as the physical lower coordinate.

The public directed cycle rho is listed as rho[0],...,rho[{n - 1}].  It is
metadata about the decoder coordinates; following rho from any index visits
all {n} indices exactly once.

rho=[{cycle_text}]

Decoder rows:
{_format_matrix(inst['decoder_rows'])}

Polygon boundary vertices:
{_format_vertices(inst['polygon'])}

The checker performs the matrix multiplication, expands all {n} squares, tests
their unit grid cells against the polygon using exact integer predicates, and
tests every rectangle pair for interior overlap.  Any key in the stated
language whose expansion is a valid packing is accepted.

Give your final answer inside <answer></answer> tags, as a JSON one-row matrix
of exactly {n} integers.  Example of the syntax for four entries:
<answer>[[3,0,11,7]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def _json_from_fragment(fragment: str):
    fragment = fragment.strip()
    try:
        return json.loads(fragment)
    except (TypeError, ValueError):
        pass
    decoder = json.JSONDecoder()
    for position, char in enumerate(fragment):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(fragment[position:])
            return value
        except ValueError:
            continue
    return None


def parse_answer(text) -> object | None:
    """Parse tagged JSON, fenced JSON, or a JSON matrix surrounded by prose."""
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    if match:
        return _json_from_fragment(match.group(1))
    for fence in _FENCE_RE.findall(text):
        value = _json_from_fragment(fence)
        if value is not None:
            return value
    return _json_from_fragment(text)


def _validate_answer_shape(inst: dict, answer) -> tuple[list[int] | None, str]:
    if not isinstance(answer, list):
        return None, "answer must be a JSON one-row matrix"
    if len(answer) == 0:
        return None, "answer matrix must contain one row, not zero rows"
    if len(answer) != 1:
        return None, "answer matrix must contain exactly one row"
    row = answer[0]
    if not isinstance(row, list):
        return None, "the sole matrix row must be a JSON list"
    if len(row) != inst["n"]:
        return None, f"matrix row must contain exactly {inst['n']} entries"
    p = inst["field_prime"]
    for i, value in enumerate(row):
        if isinstance(value, bool) or not isinstance(value, int):
            return None, f"entry {i} must be an integer"
        if value < 0 or value >= p:
            return None, f"entry {i} is outside 0..{p - 1}"
    if len(set(row)) != len(row):
        return None, "matrix entries must be pairwise distinct"
    return row, "ok"


def _point_inside_polygon_doubled(
    polygon: list[list[int]], px2: int, py2: int
) -> bool:
    """Exact ray crossing; query coordinates are doubled half-integers."""
    inside = False
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        x1, y1 = a
        x2, y2 = b
        if x1 != x2:
            continue
        ay, by = 2 * y1, 2 * y2
        if (ay > py2) != (by > py2) and 2 * x1 > px2:
            inside = not inside
    return inside


def _canonical_cell_center_physical(
    cell_x: int, cell_y: int, frame: dict
) -> tuple[int, int]:
    return (
        2 * frame["ox"] + frame["sx"] * (2 * cell_x + 1),
        2 * frame["oy"] + frame["sy"] * (2 * cell_y + 1),
    )


def _decoded_canonical_squares(inst: dict, row: list[int]):
    p = inst["field_prime"]
    squares = []
    for record in inst["decoder_rows"]:
        offset = sum(a * b for a, b in zip(record["coefficients"], row)) % p
        left = record["lane_base"] + 2 + offset
        squares.append((left, 0, left + 2, 2))
    return squares


def verify(inst, answer) -> tuple[bool, str]:
    """Verify a compact packing without consulting the planted answer."""
    row, reason = _validate_answer_shape(inst, answer)
    if row is None:
        return False, reason
    polygon = inst["polygon"]
    frame = inst["frame"]
    squares = _decoded_canonical_squares(inst, row)
    if len(squares) != inst["target_squares"]:
        return False, "decoder produced the wrong number of squares"
    for i, (left, bottom, right, top) in enumerate(squares):
        for cx in range(left, right):
            for cy in range(bottom, top):
                px2, py2 = _canonical_cell_center_physical(cx, cy, frame)
                if not _point_inside_polygon_doubled(polygon, px2, py2):
                    return False, f"decoded square {i} is not contained in the polygon"
    for i in range(len(squares)):
        a = squares[i]
        for j in range(i + 1, len(squares)):
            b = squares[j]
            if (max(a[0], b[0]) < min(a[2], b[2])
                    and max(a[1], b[1]) < min(a[3], b[3])):
                return False, f"decoded squares {i} and {j} overlap in their interiors"
    return True, "ok"


def random_candidate(inst, rng) -> object:
    """Uniformly sample the stated distinct-entry one-row matrix language."""
    return [rng.sample(range(inst["field_prime"]), inst["n"])]


def search_space(inst) -> int | None:
    p, n = inst["field_prime"], inst["n"]
    result = 1
    for value in range(p - n + 1, p + 1):
        result *= value
    return result


def enumerate_all(inst) -> int | None:
    """Brute force only tiny certificate languages; never hang on a preset."""
    space = search_space(inst)
    if space is None or space > 100_000:
        return None
    count = 0
    p, n = inst["field_prime"], inst["n"]
    for row in itertools.permutations(range(p), n):
        count += int(verify(inst, [list(row)])[0])
    return count


def _extract_offsets(inst: dict) -> list[int]:
    """Read the unique y=2 tooth edge in every canonical lane."""
    frame = inst["frame"]
    canonical = [_unmap_vertex(v, frame) for v in inst["polygon"]]
    tops = []
    for a, b in zip(canonical, canonical[1:] + canonical[:1]):
        if a[1] == b[1] == 2 and abs(a[0] - b[0]) == 2:
            tops.append(min(a[0], b[0]))
    offsets_by_base = {}
    for q in tops:
        lane = q // inst["stride"]
        if 0 <= lane < inst["n"]:
            base = lane * inst["stride"]
            offset = q - base - 2
            if 0 <= offset < inst["field_prime"]:
                offsets_by_base[base] = offset
    result = []
    for record in inst["decoder_rows"]:
        base = record["lane_base"]
        if base not in offsets_by_base:
            raise ValueError("polygon does not expose exactly one tooth in a lane")
        result.append(offsets_by_base[base])
    if len(offsets_by_base) != inst["n"]:
        raise ValueError("unexpected number of polygon teeth")
    return result


def _gaussian_key(inst: dict) -> tuple[list[list[int]] | None, int]:
    """Generic exact solve of A*x=y, with counted field operations."""
    p = inst["field_prime"]
    n = inst["n"]
    y = _extract_offsets(inst)
    augmented = [
        list(record["coefficients"]) + [rhs]
        for record, rhs in zip(inst["decoder_rows"], y)
    ]
    operations = n  # exact coordinate subtractions used to extract offsets
    for column in range(n):
        pivot = next((r for r in range(column, n)
                      if augmented[r][column] % p), None)
        if pivot is None:
            return None, operations
        if pivot != column:
            augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        inverse = pow(augmented[column][column] % p, p - 2, p)
        operations += 1
        for j in range(column, n + 1):
            augmented[column][j] = augmented[column][j] * inverse % p
            operations += 1
        for row in range(n):
            if row == column:
                continue
            factor = augmented[row][column] % p
            if not factor:
                continue
            for j in range(column, n + 1):
                augmented[row][j] = (
                    augmented[row][j] - factor * augmented[column][j]
                ) % p
                operations += 2
    return [[augmented[i][n] for i in range(n)]], operations


def _make_distinct(values: list[int], p: int) -> list[int]:
    used = set()
    result = []
    for original in values:
        value = original % p
        while value in used:
            value = (value + 1) % p
        used.add(value)
        result.append(value)
    return result


def _attack_outlier_rank(inst: dict) -> list[list[int]]:
    offsets = _extract_offsets(inst)
    order = sorted(range(inst["n"]), key=lambda i: (offsets[i], i))
    row = [0] * inst["n"]
    for rank, i in enumerate(order):
        row[i] = rank
    return [row]


def _attack_diagonal_greedy(inst: dict) -> list[list[int]]:
    p = inst["field_prime"]
    offsets = _extract_offsets(inst)
    row = []
    for i, record in enumerate(inst["decoder_rows"]):
        diagonal = record["coefficients"][i]
        row.append(offsets[i] * pow(diagonal, p - 2, p) % p)
    return [_make_distinct(row, p)]


def _attack_identity(inst: dict) -> list[list[int]]:
    return [_make_distinct(_extract_offsets(inst), inst["field_prime"])]


def _attack_random_restarts(
    inst: dict, rng: random.Random, restarts: int = 256
) -> tuple[bool, int]:
    for attempt in range(1, restarts + 1):
        if verify(inst, random_candidate(inst, rng))[0]:
            return True, attempt
    return False, restarts


def _cycle_sequence(inst: dict, values: list[int], start: int) -> tuple[int, ...]:
    out = []
    current = start
    for _ in range(inst["n"]):
        out.append(values[current])
        current = inst["cycle"][current]
    return tuple(out)


def _canonical_vertex_cycle(inst: dict) -> tuple[tuple[int, int], ...]:
    vertices = [tuple(_unmap_vertex(v, inst["frame"])) for v in inst["polygon"]]
    variants = []
    for seq in (vertices, list(reversed(vertices))):
        for i in range(len(seq)):
            variants.append(tuple(seq[i:] + seq[:i]))
    return min(variants)


def canonical_key(inst) -> str:
    """Canonicalize boundary start/orientation, frame, and decoder labels."""
    offsets = _extract_offsets(inst)
    cycle_normal = min(
        _cycle_sequence(inst, offsets, start) for start in range(inst["n"])
    )
    payload = {
        "family": "compressed-grid-polygon-packing-v1",
        "n": inst["n"],
        "p": inst["field_prime"],
        "tap": inst["tap"],
        "boundary": _canonical_vertex_cycle(inst),
        "cycle_offsets": cycle_normal,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def escalate(params) -> dict | str | None:
    """Raise coefficient entropy at fixed n once the named ladder is exhausted."""
    if not isinstance(params, dict) or set(params) != {"n", "p"}:
        return None
    n, p = params["n"], params["p"]
    if p == 1_000_003:
        return {"n": n, "p": 1_000_000_007}
    if p == 1_000_000_007:
        return {"n": n, "p": 2_147_483_647}
    return "cap_bound"


def _transform_frame(
    inst: dict, dx: int, dy: int, flip_x: bool, flip_y: bool = False
) -> dict:
    moved = dict(inst)
    frame = dict(inst["frame"])
    polygon = [list(v) for v in inst["polygon"]]
    if flip_x:
        axis = 2 * frame["ox"]
        polygon = [[axis - x, y] for x, y in polygon]
        frame["sx"] *= -1
    if flip_y:
        axis = 2 * frame["oy"]
        polygon = [[x, axis - y] for x, y in polygon]
        frame["sy"] *= -1
    polygon = [[x + dx, y + dy] for x, y in polygon]
    frame["ox"] += dx
    frame["oy"] += dy
    moved["frame"] = frame
    moved["polygon"] = polygon
    moved["answer"] = [list(inst["answer"][0])]
    return moved


def _reorder_boundary(inst: dict, shift: int, reverse: bool) -> dict:
    moved = dict(inst)
    vertices = [list(v) for v in inst["polygon"]]
    shift %= len(vertices)
    vertices = vertices[shift:] + vertices[:shift]
    if reverse:
        vertices.reverse()
    moved["polygon"] = vertices
    moved["answer"] = [list(inst["answer"][0])]
    return moved


def _relabel_decoder(inst: dict, order: list[int]) -> dict:
    """Arbitrarily rename row/key coordinates and carry the witness."""
    n = inst["n"]
    inverse = [0] * n
    for new, old in enumerate(order):
        inverse[old] = new
    moved = dict(inst)
    moved["cycle"] = [inverse[inst["cycle"][order[new]]] for new in range(n)]
    moved["decoder_rows"] = [
        {
            "lane_base": inst["decoder_rows"][old]["lane_base"],
            "coefficients": [
                inst["decoder_rows"][old]["coefficients"][old_col]
                for old_col in order
            ],
        }
        for old in order
    ]
    moved["answer"] = [[inst["answer"][0][old] for old in order]]
    return moved


def _answer_metrics(answer: object) -> tuple[int, int, int]:
    encoded = json.dumps(answer, separators=(",", ":"))
    elements = len(answer[0]) if (
        isinstance(answer, list) and len(answer) == 1
        and isinstance(answer[0], list)
    ) else 0
    return len(encoded), math.ceil(len(encoded) / 4), elements


def selftest() -> dict:
    """Run G1--G9 and return the complete machine-readable report."""
    report: dict = {
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append(f"{preset}/{seed}: {reason}")
            try:
                restored = json.loads(json.dumps(inst["answer"]))
            except (TypeError, ValueError) as exc:
                g1_failures.append(f"{preset}/{seed}: JSON error {exc}")
            else:
                if restored != inst["answer"]:
                    g1_failures.append(f"{preset}/{seed}: JSON round-trip changed answer")
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    ship = make_instance(seed=123, **shipping)
    planted = ship["answer"][0]
    swapped = list(planted)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicated = list(planted)
    duplicated[1] = duplicated[0]
    corruptions = {
        "drop": [planted[:-1]],
        "swap": [swapped],
        "duplicate": [duplicated],
        "empty": [],
        "out_of_range": [[ship["field_prime"]] + planted[1:]],
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(ship, candidate)
        corruption_results[name] = {"accepted": ok, "reason": reason}
    reasons = [entry["reason"] for entry in corruption_results.values()]
    report["G2_rejects_corruption"] = {
        "pass": (
            all(not entry["accepted"] for entry in corruption_results.values())
            and len(set(reasons)) == len(reasons)
        ),
        "cases": corruption_results,
        "distinct_reasons": len(set(reasons)),
    }

    compact = json.dumps(ship["answer"], separators=(",", ":"))
    realistic = (
        "I recovered the modular packing key.\n```json\n"
        f"<answer>\n{compact}\n</answer>\n```\n"
        "The tagged matrix is my final certificate."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == ship["answer"] and verify(ship, parsed)[0],
        "parsed_matches": parsed == ship["answer"],
        "realistic_wrapper": True,
    }

    guess_rng = random.Random(0x240409835)
    guess_total = 200_000
    guess_hits = 0
    guess_start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    guess_wall = time.perf_counter() - guess_start
    guess_fraction = guess_hits / guess_total
    exact_fraction = 1 / search_space(ship)
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_fraction": guess_fraction,
        "candidate_space": search_space(ship),
        "certified_valid_keys": 1,
        "exact_solution_fraction": exact_fraction,
        "sampling_prior": (
            "uniform pairwise-distinct GF(p) row, already satisfying every "
            "shape/range/distinctness rule stated to the solver"
        ),
        "wall_clock_sec": round(guess_wall, 6),
    }

    attack_names = (
        "outlier_offset_rank",
        "greedy_diagonal_fit",
        "random_restart_256",
        "direct_offset_as_key",
    )
    attack_stats = {
        name: {"successes": 0, "attempts": 0, "steps": 0,
               "wall_clock_sec": 0.0}
        for name in attack_names
    }
    reference_successes = 0
    reference_operations = 0
    reference_walls = []
    for seed in range(800, 808):
        inst = make_instance(seed=seed, **shipping)

        start = time.perf_counter()
        candidate = _attack_outlier_rank(inst)
        elapsed = time.perf_counter() - start
        stat = attack_stats["outlier_offset_rank"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["steps"] += inst["n"] * math.ceil(math.log2(inst["n"]))
        stat["wall_clock_sec"] += elapsed

        start = time.perf_counter()
        candidate = _attack_diagonal_greedy(inst)
        elapsed = time.perf_counter() - start
        stat = attack_stats["greedy_diagonal_fit"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["steps"] += 4 * inst["n"]
        stat["wall_clock_sec"] += elapsed

        start = time.perf_counter()
        success, steps = _attack_random_restarts(
            inst, random.Random(seed ^ 0xA551), 256
        )
        elapsed = time.perf_counter() - start
        stat = attack_stats["random_restart_256"]
        stat["attempts"] += 1
        stat["successes"] += int(success)
        stat["steps"] += steps
        stat["wall_clock_sec"] += elapsed

        start = time.perf_counter()
        candidate = _attack_identity(inst)
        elapsed = time.perf_counter() - start
        stat = attack_stats["direct_offset_as_key"]
        stat["attempts"] += 1
        stat["successes"] += int(verify(inst, candidate)[0])
        stat["steps"] += inst["n"]
        stat["wall_clock_sec"] += elapsed

        start = time.perf_counter()
        solution, operations = _gaussian_key(inst)
        elapsed = time.perf_counter() - start
        reference_walls.append(elapsed)
        reference_operations += operations
        reference_successes += int(
            solution is not None and verify(inst, solution)[0]
        )

    for stat in attack_stats.values():
        stat["wall_clock_sec"] = round(stat["wall_clock_sec"], 6)
    all_failed = all(stat["successes"] == 0 for stat in attack_stats.values())
    reference_total_wall = sum(reference_walls)
    reference_average_operations = reference_operations // 8
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attack_stats,
        "reference_algorithm": {
            "name": (
                "integer-placement enumeration followed by dense modular "
                "Gaussian elimination"
            ),
            "complexity": "O(V+n^3) exact operations",
            "wall_clock_sec": round(reference_total_wall, 6),
            "median_wall_clock_sec": round(sorted(reference_walls)[4], 6),
            "operations": reference_operations,
            "average_operations_per_instance": reference_average_operations,
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    demo = make_instance(seed=123, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    strongest_failing = max(
        attack_stats.items(), key=lambda item: item[1]["wall_clock_sec"]
    )
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and reference_successes == 8,
        "shipping_certified_solution_count": 1,
        "shipping_exact_solution_fraction": exact_fraction,
        "shipping_sampled_valid_hits": guess_hits,
        "shipping_sampled_valid_total": guess_total,
        "shipping_sampled_density": guess_fraction,
        "demo_bruteforce_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "reference_algorithm_wall_clock_sec": round(reference_total_wall, 6),
        "reference_algorithm_median_wall_clock_sec": round(
            sorted(reference_walls)[4], 6
        ),
        "reference_algorithm_operations": reference_operations,
        "reference_average_operations_per_instance": reference_average_operations,
        "strongest_failing_attack": strongest_failing[0],
        "strongest_failing_attack_wall_clock_sec": strongest_failing[1][
            "wall_clock_sec"
        ],
        "strongest_failing_attack_steps": strongest_failing[1]["steps"],
    }

    ladder_spaces = [
        search_space(make_instance(seed=7, **params))
        for params in DIFFICULTY.values()
    ]
    doubled = make_instance(
        n=2 * shipping["n"], p=max(shipping["p"], 65537), seed=909
    )
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": ladder_spaces == sorted(set(ladder_spaces)) and doubled_ok,
        "preset_candidate_spaces": dict(zip(DIFFICULTY, ladder_spaces)),
        "doubled_n": doubled["n"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "fixed_answer_length_axis_after_hard": "increase p at n=96",
    }

    invariant_checks = 0
    witness_checks = 0
    invariant_failures = []
    unrelated_keys = []
    for seed in range(20):
        inst = make_instance(n=12, p=257, seed=20_000 + seed)
        key = canonical_key(inst)
        unrelated_keys.append(key)
        rng = random.Random(30_000 + seed)
        order = list(range(inst["n"]))
        rng.shuffle(order)
        relabelled = _relabel_decoder(inst, order)
        reordered = _reorder_boundary(inst, 3 + seed, bool(seed & 1))
        framed = _transform_frame(inst, 19 - seed, seed - 7, True, True)
        composed = _transform_frame(
            _reorder_boundary(relabelled, 5 + seed, True),
            -13, 29, True, bool(seed & 1)
        )
        for number, moved in enumerate(
            (relabelled, reordered, framed, composed)
        ):
            invariant_checks += 1
            if canonical_key(moved) != key:
                invariant_failures.append(f"key/{seed}/{number}")
            witness_checks += 1
            if not verify(moved, moved["answer"])[0]:
                invariant_failures.append(f"witness/{seed}/{number}")
    distinct_keys = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not invariant_failures and distinct_keys == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": witness_checks,
        "invariance_failures": invariant_failures,
        "unrelated_instances": 20,
        "distinct_keys": distinct_keys,
        "transformations": [
            "arbitrary simultaneous decoder-row/key-coordinate relabelling",
            "polygon boundary cyclic shift and reversal",
            "global integer translation and independent axis reflections",
            "composition of all three kinds",
        ],
    }

    chars, tokens, elements = _answer_metrics(ship["answer"])
    intended_operations = 3 * ship["n"]
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        chars <= 2_000 and elements <= 256 and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] >= tokens
    )
    hinted_minus_placebo = (
        hinted_rate - placebo_rate if arms["placebo"]["attempts"] else None
    )
    report["G9_no_tool_suitability"] = {
        "pass": (
            G9_ORACLE_RESULTS["hinted_verdict"] == "hardened" and within_caps
        ),
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
