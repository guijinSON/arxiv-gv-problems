"""Verified tight-pattern stabbing-polygon generator for arXiv:1211.1490.

The family instantiates the rational unit-circle gadgets in the proof of
Theorem 1 (Section 5).  A certificate chooses T_i or F_i in every variable
gadget.  Each satisfied clause then has a canonical completion using two of
its three p-points, producing the lower-bound vertex pattern in the proof.

Instances are inverse-generated from a random selector.  Four 3-CNF clauses
encode each ternary XOR equation, and the XOR triples overlap as a hidden
cycle.  The planted selector is used only while constructing the right-hand
sides; verification never reads inst["answer"].
"""

from __future__ import annotations

import copy
import functools
import hashlib
import json
import math
import os
import random
import re
import statistics
import sys
import time
from collections import defaultdict
from fractions import Fraction


sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)
try:  # The exact geometry below needs only Fraction; gvlib remains optional.
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - standard-library-only fallback.
    exact_matrices = rationals = None


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "Each four-clause block on the same variable triple is the CNF truth table "
    "of one ternary parity constraint."
)
PLACEBO_HINT: str = (
    "Each variable and clause index deserves careful checking when the selected "
    "point IDs are transferred to the final list."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "geometry",
    "object_regime": "rational_exact",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "rational points on the unit circle given parametrically",
        "line-segment variable, clause, and connector gadgets",
        "a compact selector for a convex stabbing polygon",
    ],
    "verification_operations": [
        "exact rational unit-circle coordinate construction",
        "exact orientation and convex-polygon containment tests",
        "exact endpoint-incidence and Boolean connector checks",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 5, Theorem 1 and Appendix A (the 3-SAT reduction and its exact "
        "rational unit-circle realization)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "reduction recognition",
    "intuition_description": (
        "Recognize each shuffled four-clause gadget as a ternary XOR equation "
        "and the two-variable overlaps as a cycle; without that recognition the "
        "solver searches an exponentially large polygon-selector space."
    ),
    "hardness_basis": (
        "Track B: decoding the paper's connector gadgets and applying dense "
        "Gaussian elimination over GF(2) solves this cyclic-XOR subdistribution "
        "in O(n^3); at shipping n=89 it used a median 15,039 exact XORs and "
        "0.0019 seconds locally, versus at most 291 exact XORs for the compact "
        "cycle recurrence, whose shuffled blocks and hidden overlap order cannot "
        "be mechanically reconstructed by hand in the model context."
    ),
    "max_answer_tokens": 83,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"]
    + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 5},
    "easy": {"n": 65},
    "medium": {"n": 77},
    "hard": {"n": 89},
}
SHIPPING_DIFFICULTY: str = "hard"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "An ordered list of n point IDs. Entry i is exactly T_i=4i+1 or "
        "F_i=4i+2; it compactly specifies the variable vertices of the completed "
        "stabbing polygon."
    ),
    "bounds": {
        "shipping_entries": 89,
        "choices_per_entry": 2,
        "maximum_shipping_point_id": 355,
    },
}

NOTES: str = (
    "Section 1 fixes stabbing to mean that at least one segment endpoint is "
    "contained in the polygon. Section 5, Theorem 1 fixes the NP-hard crossing-"
    "segment regime and proves that the lower-bound pattern has one of T_i,F_i "
    "per variable and two of p_j1,p_j2,p_j3 per clause. Appendix A supplies the "
    "exact rational unit-circle coordinates used here. Theorem 2 makes pairwise-"
    "disjoint segments polynomial-time solvable, and Observation 1 gives an "
    "O(2^k P(n)) FPT algorithm in the number k of crossing segments, so k grows "
    "linearly here. Track A would still be unjustified for this planted "
    "distribution: its four-clause blocks decode to XOR and Gaussian elimination "
    "solves them. The generator therefore declares Track B and measures that "
    "algorithm. Balanced literal counts defeat signed-frequency outliers; random "
    "variable and clause permutations defeat positional leakage; coordinate "
    "descent, random restart, and low-period ansatz attacks are tested explicitly."
)


# Filled from the three script-owned hardening runs after STEP 4.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 1, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "too_easy",
    "hinted_harness_verdict": "cap_bound_after_solved_restricted_rung",
}


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _vid(i: int, kind: int) -> int:
    """Variable point ID: kind 0=a, 1=T, 2=F, 3=b."""
    return 4 * i + kind


def _cid(n: int, j: int, kind: int) -> int:
    """Clause point ID: kind 0=c, 1=p1, 2=p2, 3=p3, 4=d."""
    return 4 * n + 5 * j + kind


def _bits_to_answer(bits) -> list[int]:
    return [_vid(i, 1 if bit else 2) for i, bit in enumerate(bits)]


def _answer_to_bits_fast(answer) -> list[int]:
    return [1 if value == _vid(i, 1) else 0 for i, value in enumerate(answer)]


def _expand_xor_as_cnf(variables, rhs: int) -> list[list[int]]:
    """Return four 3-clauses whose satisfying rows have parity rhs."""
    clauses = []
    for assignment in range(8):
        bits = [(assignment >> k) & 1 for k in range(3)]
        if (bits[0] ^ bits[1] ^ bits[2]) == rhs:
            continue
        # This clause is false exactly on `bits`.
        clauses.append(
            [variables[k] + 1 if bits[k] == 0 else -(variables[k] + 1)
             for k in range(3)]
        )
    return clauses


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a rational stabbing-polygon gadget instance.

    A random selector and a random hidden variable cycle are sampled first.
    Their ternary parities define the clauses, so the returned certificate is
    known by construction and is never obtained by solving the clauses.
    """
    if params:
        unknown = ", ".join(sorted(params))
        raise TypeError(f"unknown make_instance parameters: {unknown}")
    if not _is_int(n) or n < 5:
        raise ValueError("n must be an integer at least 5")
    if n % 3 == 0:
        raise ValueError("n must not be divisible by 3 (the XOR cycle must be full-rank)")
    if not _is_int(seed):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    bits = [rng.randrange(2) for _ in range(n)]
    cycle = list(range(n))
    rng.shuffle(cycle)

    clauses = []
    for i in range(n):
        triple = [cycle[i], cycle[(i + 1) % n], cycle[(i + 2) % n]]
        rhs = bits[triple[0]] ^ bits[triple[1]] ^ bits[triple[2]]
        block = _expand_xor_as_cnf(triple, rhs)
        for clause in block:
            rng.shuffle(clause)
            clauses.append(clause)
    rng.shuffle(clauses)

    return {
        "n": n,
        "clauses": clauses,
        "answer": _bits_to_answer(bits),
        "geometry": {
            "point_parametrization": "U(t)=((t^2-1)/(t^2+1),2t/(t^2+1))",
            "variable_rotation_parameter": 100 * n * n,
            "clause_rotation_parameter": 100 * len(clauses) * len(clauses),
        },
    }


def _render_clause(clause) -> str:
    return " ".join(("+" if lit > 0 else "-") + str(abs(lit)) for lit in clause)


def render(inst) -> str:
    n = inst["n"]
    clauses = inst["clauses"]
    m = len(clauses)
    lines = [
        "Tight-pattern stabbing polygon (exact rational instance)",
        "",
        "A segment is stabbed when at least one of its two endpoints lies on or "
        "inside the polygon. All indices and point IDs below are 0-based.",
        "",
        "Exact point construction. For a positive integer t define",
        "  U(t) = ((t^2-1)/(t^2+1), 2t/(t^2+1)).",
        "If r=(rx,ry)=U(t), define the clockwise rational rotation",
        "  R_r(x,y) = (rx*x + ry*y, -ry*x + rx*y).",
        "Every displayed construction is exact over the rationals; all of its "
        "points lie on the unit circle.",
        "",
        f"There are n={n} variable gadgets. Put rV=U({100*n*n}). For variable i, "
        "let q=U(5i+1), negate both coordinates after applying the rotations, and set",
        "  a_i=-q, T_i=-R_rV(q), F_i=-R_rV^2(q), b_i=-R_rV^3(q).",
        "Their point IDs are 4i, 4i+1, 4i+2, 4i+3 respectively. The gadget "
        "segments are (a_i,a_i), (b_i,b_i), and (T_i,F_i).",
        "",
        f"There are m={m} clause gadgets. Put rC=U({100*m*m}). For clause j, "
        "let q=U(5j+1) and set",
        "  c_j=q, p_j1=R_rC(q), p_j2=R_rC^2(q), p_j3=R_rC^3(q), d_j=R_rC^4(q).",
        f"Their IDs are 4n+5j through 4n+5j+4 (here 4n={4*n}). The gadget "
        "segments are (c_j,c_j), (d_j,d_j), (p_j1,p_j2), (p_j2,p_j3), "
        "and (p_j3,p_j1).",
        "",
        "Each signed literal below adds one connector segment. At position r=1,2,3, "
        "literal +k connects T_(k-1) to p_jr; literal -k connects F_(k-1) "
        "to p_jr. A positive literal is true when T is chosen, and a negative "
        "literal is true when F is chosen. No variable repeats within a clause.",
        "",
        "Clauses (j: three signed literals):",
    ]
    lines.extend(f"  {j}: {_render_clause(clause)}" for j, clause in enumerate(clauses))
    lines.extend(
        [
            "",
            "Find the compact selector of a completed tight-pattern polygon. Your "
            "answer must contain exactly n point IDs in variable order: entry i must "
            "be T_i=4i+1 or F_i=4i+2. For each clause the completion omits the p-point "
            "at the first true literal position and includes the other two; it also "
            "includes every a_i,b_i,c_j,d_j. The polygon visits all included points "
            "in counterclockwise order around the unit circle. Thus a selector is "
            "valid exactly when this concrete completed convex polygon stabs every "
            "listed gadget and connector segment.",
            "",
            "Order matters, repeats are forbidden, and the bounds are inclusive. "
            "Give your final answer inside <answer></answer> tags as comma-separated "
            "decimal point IDs.",
            "Example for n=3: <answer>1, 6, 9</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    if not matches:
        return None
    payload = matches[-1].strip()
    payload = re.sub(r"^```(?:text|json)?\s*", "", payload, flags=re.IGNORECASE)
    payload = re.sub(r"\s*```$", "", payload)
    if not payload:
        return None
    parts = [part.strip() for part in payload.split(",")]
    if not parts or any(not re.fullmatch(r"[+-]?\d+", part) for part in parts):
        return None
    try:
        return [int(part) for part in parts]
    except (TypeError, ValueError, OverflowError):
        return None


def _unit_point(t: int):
    den = t * t + 1
    return (Fraction(t * t - 1, den), Fraction(2 * t, den))


def _rotate_clockwise(point, rotor):
    x, y = point
    rx, ry = rotor
    return (rx * x + ry * y, -ry * x + rx * y)


def _cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _angle_half(point):
    x, y = point
    return 0 if y > 0 or (y == 0 and x >= 0) else 1


def _angle_compare(item_a, item_b):
    _, a = item_a
    _, b = item_b
    ha, hb = _angle_half(a), _angle_half(b)
    if ha != hb:
        return -1 if ha < hb else 1
    det = a[0] * b[1] - a[1] * b[0]
    if det > 0:
        return -1
    if det < 0:
        return 1
    return 0


@functools.lru_cache(maxsize=16)
def _geometry(n: int, m: int):
    points = [None] * (4 * n + 5 * m)
    rv = _unit_point(100 * n * n)
    for i in range(n):
        point = _unit_point(5 * i + 1)
        for kind in range(4):
            points[_vid(i, kind)] = (-point[0], -point[1])
            point = _rotate_clockwise(point, rv)
    rc = _unit_point(100 * m * m)
    for j in range(m):
        point = _unit_point(5 * j + 1)
        for kind in range(5):
            points[_cid(n, j, kind)] = point
            point = _rotate_clockwise(point, rc)
    ordered = tuple(
        point_id for point_id, _ in sorted(
            enumerate(points), key=functools.cmp_to_key(_angle_compare)
        )
    )
    return tuple(points), ordered


def _inside_convex(poly, point) -> bool:
    """Exact membership in a strict counterclockwise convex polygon."""
    if len(poly) < 3:
        return False
    p0 = poly[0]
    left = _cross(p0, poly[1], point)
    right = _cross(p0, poly[-1], point)
    if left < 0 or right > 0:
        return False
    lo, hi = 1, len(poly) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if _cross(p0, poly[mid], point) >= 0:
            lo = mid
        else:
            hi = mid
    return _cross(poly[lo], poly[(lo + 1) % len(poly)], point) >= 0


def _literal_true(literal: int, bits) -> bool:
    bit = bits[abs(literal) - 1]
    return bool(bit) if literal > 0 else not bool(bit)


def _satisfies_clauses(clauses, bits) -> bool:
    return all(any(_literal_true(lit, bits) for lit in clause) for clause in clauses)


def _completed_vertices(inst, answer, bits):
    n = inst["n"]
    chosen = set(answer)
    for i in range(n):
        chosen.add(_vid(i, 0))
        chosen.add(_vid(i, 3))
    for j, clause in enumerate(inst["clauses"]):
        chosen.add(_cid(n, j, 0))
        chosen.add(_cid(n, j, 4))
        true_positions = [r for r, lit in enumerate(clause) if _literal_true(lit, bits)]
        if not true_positions:
            return None
        omitted = true_positions[0]
        for r in range(3):
            if r != omitted:
                chosen.add(_cid(n, j, r + 1))
    return chosen


def _segments(inst):
    n = inst["n"]
    segments = []
    for i in range(n):
        segments.extend([
            (_vid(i, 0), _vid(i, 0)),
            (_vid(i, 3), _vid(i, 3)),
            (_vid(i, 1), _vid(i, 2)),
        ])
    for j, clause in enumerate(inst["clauses"]):
        c, p1, p2, p3, d = [_cid(n, j, k) for k in range(5)]
        segments.extend([(c, c), (d, d), (p1, p2), (p2, p3), (p3, p1)])
        for r, literal in enumerate(clause):
            variable = abs(literal) - 1
            endpoint = _vid(variable, 1 if literal > 0 else 2)
            segments.append((endpoint, _cid(n, j, r + 1)))
    return segments


def verify(inst, answer):
    """Check any valid selector; never consult the planted inst['answer']."""
    try:
        n = inst["n"]
        clauses = inst["clauses"]
    except (KeyError, TypeError):
        return False, "malformed instance"
    if not isinstance(answer, list):
        return False, "answer must be a list of point IDs"
    if not answer:
        return False, "answer is empty"
    if len(answer) != n:
        return False, f"answer must contain exactly {n} point IDs"
    if any(not _is_int(value) for value in answer):
        return False, "every point ID must be an integer"
    max_id = 4 * n + 5 * len(clauses) - 1
    if any(value < 0 or value > max_id for value in answer):
        return False, f"point ID outside the inclusive range 0..{max_id}"
    if len(set(answer)) != len(answer):
        return False, "point IDs must not repeat"
    for i, value in enumerate(answer):
        if value not in (_vid(i, 1), _vid(i, 2)):
            return False, f"entry {i} must be T_{i}={_vid(i,1)} or F_{i}={_vid(i,2)}"

    bits = _answer_to_bits_fast(answer)
    for j, clause in enumerate(clauses):
        if not any(_literal_true(lit, bits) for lit in clause):
            return False, f"connector constraints fail at clause gadget {j}"

    chosen = _completed_vertices(inst, answer, bits)
    if chosen is None:
        return False, "a clause has no canonical true-literal completion"
    expected = 3 * n + 4 * len(clauses)
    if len(chosen) != expected:
        return False, "completed polygon has the wrong tight-pattern vertex count"

    try:
        points, full_order = _geometry(n, len(clauses))
    except Exception as exc:  # exact construction failure is an instance defect.
        return False, f"exact coordinate construction failed: {type(exc).__name__}"
    if any(x * x + y * y != 1 for x, y in points):
        return False, "a constructed point is not exactly on the unit circle"
    if len(set(points)) != len(points):
        return False, "the exact point construction contains duplicate points"

    polygon_ids = [point_id for point_id in full_order if point_id in chosen]
    polygon = [points[point_id] for point_id in polygon_ids]
    if len(polygon) != expected:
        return False, "completed point set and polygon order disagree"
    for i in range(len(polygon)):
        if _cross(polygon[i - 1], polygon[i], polygon[(i + 1) % len(polygon)]) <= 0:
            return False, "completed polygon is not strictly convex and simple"

    inside = [False] * len(points)
    for point_id, point in enumerate(points):
        inside[point_id] = point_id in chosen or _inside_convex(polygon, point)
    for segment_index, (u, v) in enumerate(_segments(inst)):
        if not inside[u] and not inside[v]:
            return False, f"segment {segment_index} is not stabbed"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniform selector after enforcing one legal endpoint per variable gadget."""
    if not hasattr(rng, "randrange"):
        raise TypeError("rng must provide randrange")
    return [_vid(i, 1 if rng.randrange(2) else 2) for i in range(inst["n"])]


def search_space(inst):
    return 1 << inst["n"]


def enumerate_all(inst):
    n = inst["n"]
    if n > 18:
        return None
    count = 0
    for mask in range(1 << n):
        bits = [(mask >> i) & 1 for i in range(n)]
        if _satisfies_clauses(inst["clauses"], bits):
            count += 1
    return count


def _decode_xor_equations(inst):
    groups = defaultdict(list)
    n = inst["n"]
    for clause in inst["clauses"]:
        if not isinstance(clause, list) or len(clause) != 3:
            raise ValueError("every CNF clause must contain three literals")
        variables = tuple(sorted(abs(lit) - 1 for lit in clause))
        if len(set(variables)) != 3 or variables[0] < 0 or variables[-1] >= n:
            raise ValueError("invalid variable triple")
        groups[variables].append(clause)
    equations = {}
    for variables, block in groups.items():
        if len(block) != 4:
            raise ValueError("an XOR block must contain four clauses")
        forbidden = set()
        for clause in block:
            row = {}
            for literal in clause:
                variable = abs(literal) - 1
                if variable in row:
                    raise ValueError("repeated variable in clause")
                row[variable] = 0 if literal > 0 else 1
            forbidden.add(tuple(row[v] for v in variables))
        if len(forbidden) != 4:
            raise ValueError("duplicate forbidden rows in XOR block")
        parities = {a ^ b ^ c for a, b, c in forbidden}
        if len(parities) != 1:
            raise ValueError("four-clause block is not a parity truth table")
        equations[frozenset(variables)] = 1 - next(iter(parities))
    if len(equations) != n:
        raise ValueError("cyclic system must contain exactly n XOR equations")
    return equations


def _edge_cycle(equations):
    edges = list(equations)
    neighbors = {edge: [] for edge in edges}
    for i, edge in enumerate(edges):
        for other in edges[i + 1:]:
            if len(edge & other) == 2:
                neighbors[edge].append(other)
                neighbors[other].append(edge)
    if any(len(value) != 2 for value in neighbors.values()):
        raise ValueError("two-variable overlaps do not form one cycle")
    start = min(edges, key=lambda edge: tuple(sorted(edge)))
    first = min(neighbors[start], key=lambda edge: tuple(sorted(edge)))
    order = [start]
    previous, current = start, first
    while current != start:
        if current in order:
            raise ValueError("overlap graph contains a short cycle")
        order.append(current)
        choices = [edge for edge in neighbors[current] if edge != previous]
        if len(choices) != 1:
            raise ValueError("overlap cycle is ambiguous")
        previous, current = current, choices[0]
    if len(order) != len(edges):
        raise ValueError("overlap graph is disconnected")
    return order


def canonical_key(inst):
    equations = _decode_xor_equations(inst)
    order = _edge_cycle(equations)
    sequence = "".join(str(equations[edge]) for edge in order)
    candidates = []
    for text in (sequence, sequence[::-1]):
        candidates.extend(text[i:] + text[:i] for i in range(len(text)))
    bracelet = min(candidates)
    payload = f"n={inst['n']};rhs_bracelet={bracelet}"
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def _dense_gaussian_certificate(inst):
    """Generic GF(2) elimination reference algorithm with operation counts."""
    started = time.perf_counter()
    equations = _decode_xor_equations(inst)
    n = inst["n"]
    rows = []
    for variables, rhs in equations.items():
        row = [0] * (n + 1)
        for variable in variables:
            row[variable] = 1
        row[n] = rhs
        rows.append(row)
    pivot_row = 0
    exact_operations = 0
    pivot_tests = 0
    for column in range(n):
        pivot = None
        for r in range(pivot_row, n):
            pivot_tests += 1
            if rows[r][column]:
                pivot = r
                break
        if pivot is None:
            continue
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        for r in range(n):
            if r == pivot_row:
                continue
            pivot_tests += 1
            if rows[r][column]:
                for c in range(column, n + 1):
                    rows[r][c] ^= rows[pivot_row][c]
                    exact_operations += 1
        pivot_row += 1
    if pivot_row != n:
        raise ValueError("reference system is not full rank")
    bits = [0] * n
    for row in rows:
        pivot = next((c for c in range(n) if row[c]), None)
        if pivot is None:
            if row[n]:
                raise ValueError("inconsistent reference system")
            continue
        bits[pivot] = row[n]
    elapsed = time.perf_counter() - started
    return _bits_to_answer(bits), {
        "wall_clock_sec": elapsed,
        "exact_operations": exact_operations,
        "pivot_tests": pivot_tests,
        "rank": pivot_row,
    }


def _compact_cycle_certificate(inst):
    """Linear recurrence route used only for measurement and independent checks."""
    started = time.perf_counter()
    equations = _decode_xor_equations(inst)
    edges = _edge_cycle(equations)
    n = len(edges)
    variable_cycle = []
    for i, edge in enumerate(edges):
        dropped = edge - edges[(i + 1) % n]
        if len(dropped) != 1:
            raise ValueError("successive XOR triples must drop one variable")
        variable_cycle.append(next(iter(dropped)))
    for i, edge in enumerate(edges):
        expected = {
            variable_cycle[i],
            variable_cycle[(i + 1) % n],
            variable_cycle[(i + 2) % n],
        }
        if set(edge) != expected:
            raise ValueError("recovered cycle does not reproduce the XOR triples")

    rhs = [equations[edge] for edge in edges]
    particular = [0, 0]
    exact_operations = 0
    for i in range(n - 2):
        particular.append(rhs[i] ^ particular[i] ^ particular[i + 1])
        exact_operations += 2

    winning = None
    for u in (0, 1):
        for v in (0, 1):
            uv = u ^ v
            exact_operations += 1
            pattern = (u, v, uv)
            tail_one = particular[n - 2] ^ pattern[(n - 2) % 3]
            tail_two = particular[n - 1] ^ pattern[(n - 1) % 3]
            head_zero = u
            head_one = v
            exact_operations += 2
            check_one = tail_one ^ tail_two ^ head_zero
            check_two = tail_two ^ head_zero ^ head_one
            exact_operations += 4
            if check_one == rhs[n - 2] and check_two == rhs[n - 1]:
                winning = pattern
                break
        if winning is not None:
            break
    if winning is None:
        raise ValueError("cyclic recurrence has no closing seed")
    solution = [0] * n
    for i, variable in enumerate(variable_cycle):
        solution[variable] = particular[i] ^ winning[i % 3]
        exact_operations += 1
    elapsed = time.perf_counter() - started
    return _bits_to_answer(solution), {
        "wall_clock_sec": elapsed,
        "exact_operations": exact_operations,
        "cycle_length": n,
    }


def _equation_score(inst, bits) -> int:
    equations = _decode_xor_equations(inst)
    return sum(
        (bits[a] ^ bits[b] ^ bits[c]) == rhs
        for variables, rhs in equations.items()
        for a, b, c in [tuple(variables)]
    )


def _attack_signed_frequency(inst):
    positive = [0] * inst["n"]
    negative = [0] * inst["n"]
    for clause in inst["clauses"]:
        for literal in clause:
            (positive if literal > 0 else negative)[abs(literal) - 1] += 1
    bits = [1 if positive[i] > negative[i] else 0 for i in range(inst["n"])]
    return _bits_to_answer(bits)


def _attack_coordinate_greedy(inst):
    bits = _answer_to_bits_fast(_attack_signed_frequency(inst))
    score = _equation_score(inst, bits)
    for i in range(inst["n"]):
        bits[i] ^= 1
        trial = _equation_score(inst, bits)
        if trial > score:
            score = trial
        else:
            bits[i] ^= 1
    return _bits_to_answer(bits)


def _attack_random_restart(inst, rng, restarts=256):
    best = None
    best_score = -1
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        bits = _answer_to_bits_fast(candidate)
        score = _equation_score(inst, bits)
        if score > best_score:
            best, best_score = candidate, score
        if score == inst["n"]:
            return candidate
    return best


def _attack_low_period_ansatz(inst):
    n = inst["n"]
    best = None
    best_score = -1
    for period in range(1, 9):
        for mask in range(1 << period):
            bits = [(mask >> (i % period)) & 1 for i in range(n)]
            score = _equation_score(inst, bits)
            if score > best_score:
                best, best_score = _bits_to_answer(bits), score
    return best


def _relabel_instance(inst, permutation, rng):
    """Carry the formula and witness through a variable/point relabelling."""
    n = inst["n"]
    if sorted(permutation) != list(range(n)):
        raise ValueError("permutation must relabel 0..n-1")
    clauses = []
    for clause in inst["clauses"]:
        mapped = []
        for literal in clause:
            new_var = permutation[abs(literal) - 1] + 1
            mapped.append(new_var if literal > 0 else -new_var)
        rng.shuffle(mapped)
        clauses.append(mapped)
    rng.shuffle(clauses)
    old_bits = _answer_to_bits_fast(inst["answer"])
    new_bits = [0] * n
    for old, new in enumerate(permutation):
        new_bits[new] = old_bits[old]
    transformed = copy.deepcopy(inst)
    transformed["clauses"] = clauses
    transformed["answer"] = _bits_to_answer(new_bits)
    return transformed


def escalate(params):
    n = params.get("n")
    if not _is_int(n):
        return None
    # The certificate remains below the 256-atom cap; the intended exact-XOR
    # route, rather than transcription, becomes binding after n=95.
    if n < 95:
        candidate = n + 6
        while candidate % 3 == 0:
            candidate += 1
        return {"n": candidate}
    return None


def _answer_size(answer):
    encoded = json.dumps(answer, separators=(",", ":"))
    return {
        "chars": len(encoded),
        "tokens": math.ceil(len(encoded) / 4),
        "elements": len(answer),
    }


def selftest():
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    failures = []
    attempts = 0
    json_roundtrips = 0
    independent_checks = 0
    compact_operation_counts = []
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, "plant", reason])
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
            compact, stats = _compact_cycle_certificate(inst)
            compact_operation_counts.append(stats["exact_operations"])
            independent_checks += 1
            compact_ok, compact_reason = verify(inst, compact)
            if not compact_ok:
                failures.append([preset, seed, "compact", compact_reason])
    report["G1_planted_verifies"] = {
        "pass": not failures
        and json_roundtrips == attempts
        and independent_checks == attempts,
        "attempts": attempts,
        "json_roundtrips": json_roundtrips,
        "independent_compact_route_checks": independent_checks,
        "max_compact_exact_operations_all_presets": max(compact_operation_counts),
        "failures": failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=90210, **ship_params)
    answer = inst["answer"]
    drop = answer[:-1]
    duplicate = answer[:]
    duplicate[1] = duplicate[0]
    swapped = answer[:]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    out_of_range = answer[:]
    out_of_range[0] = 4 * inst["n"] + 5 * len(inst["clauses"])
    corruptions = {
        "drop": drop,
        "swap": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = [case["reason"] for case in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values())
        and len(set(reasons)) == len(reasons),
        "cases": cases,
    }

    answer_text = ", ".join(str(value) for value in answer)
    realistic = (
        "I reconstructed the selector from the gadget constraints.\n\n"
        "```text\n<answer>" + answer_text + "</answer>\n```\n"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("no delimited answer") is None,
        "parsed_equals_answer": parsed == answer,
        "garbage_returns_none": parse_answer("no delimited answer") is None,
    }

    samples = 200_000
    sample_rng = random.Random(0x12111490)
    equations = _decode_xor_equations(inst)
    decoded = [(tuple(variables), rhs) for variables, rhs in equations.items()]
    hits = 0
    for _ in range(samples):
        candidate = random_candidate(inst, sample_rng)
        bits = _answer_to_bits_fast(candidate)
        if all(bits[a] ^ bits[b] ^ bits[c] == rhs
               for (a, b, c), rhs in decoded):
            hits += 1
    exact_probability = 1.0 / (1 << inst["n"])
    report["G4_guess_resistance"] = {
        "pass": hits == 0 and exact_probability < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "exact_probability": exact_probability,
        "structure_aware_space": search_space(inst),
        "sampler": "uniform after enforcing exactly one legal T_i/F_i choice per variable",
    }

    attack_results = {
        "outlier_signed_literal_frequency": {"successes": 0, "attempts": 0},
        "greedy_single_variable_improvement": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
        "in_context_low_period_ansatz": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_times = []
    reference_operations = []
    reference_tests = []
    compact_successes = 0
    compact_times = []
    compact_operations = []
    for seed in range(3100, 3108):
        attacked = make_instance(seed=seed, **ship_params)
        candidates = {
            "outlier_signed_literal_frequency": _attack_signed_frequency(attacked),
            "greedy_single_variable_improvement": _attack_coordinate_greedy(attacked),
            "random_restart_256": _attack_random_restart(
                attacked, random.Random(seed ^ 0xA5A5), restarts=256
            ),
            "in_context_low_period_ansatz": _attack_low_period_ansatz(attacked),
        }
        for name, candidate in candidates.items():
            attack_results[name]["attempts"] += 1
            if verify(attacked, candidate)[0]:
                attack_results[name]["successes"] += 1

        reference, stats = _dense_gaussian_certificate(attacked)
        reference_times.append(stats["wall_clock_sec"])
        reference_operations.append(stats["exact_operations"])
        reference_tests.append(stats["pivot_tests"])
        if verify(attacked, reference)[0]:
            reference_successes += 1

        compact, compact_stats = _compact_cycle_certificate(attacked)
        compact_times.append(compact_stats["wall_clock_sec"])
        compact_operations.append(compact_stats["exact_operations"])
        if verify(attacked, compact)[0]:
            compact_successes += 1

    all_failed = all(item["successes"] == 0 for item in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8 and compact_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "four-clause XOR decoding plus dense Gaussian elimination over GF(2)",
            "complexity": "O(n^3) exact field operations",
            "median_wall_clock_sec": round(statistics.median(reference_times), 6),
            "median_operations": int(statistics.median(reference_operations)),
            "median_pivot_tests": int(statistics.median(reference_tests)),
            "solves": f"{reference_successes}/8, as expected",
        },
        "compact_route": {
            "name": "overlap-cycle recovery and a second-order GF(2) recurrence",
            "complexity": "O(n^2) overlap checks and O(n) exact XOR operations",
            "median_wall_clock_sec": round(statistics.median(compact_times), 6),
            "median_operations": int(statistics.median(compact_operations)),
            "solves": f"{compact_successes}/8, as expected",
        },
    }

    demo_count = enumerate_all(make_instance(seed=3, **DIFFICULTY["demo"]))
    baseline_started = time.perf_counter()
    _attack_random_restart(inst, random.Random(77123), restarts=256)
    baseline_wall = time.perf_counter() - baseline_started
    report["G5_density_and_baseline"] = {
        "pass": hits == 0
        and demo_count == 1
        and reference_successes == 8
        and min(reference_operations) > 0,
        "shipping_valid_hits": hits,
        "shipping_density_samples": samples,
        "shipping_observed_solution_fraction": hits / samples,
        "shipping_exact_solution_count": 1,
        "shipping_exact_density": exact_probability,
        "demo_exact_solution_count": demo_count,
        "baseline_wall_seconds": round(baseline_wall, 6),
        "baseline_random_restart_iterations": 256,
        "reference_median_wall_seconds": round(statistics.median(reference_times), 6),
        "reference_median_operations": int(statistics.median(reference_operations)),
    }

    doubled_n = 2 * inst["n"]
    while doubled_n % 3 == 0:
        doubled_n += 1
    doubled = make_instance(n=doubled_n, seed=77)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and doubled["n"] >= 2 * inst["n"],
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "shipping_search_bits": inst["n"],
        "doubled_search_bits": doubled["n"],
        "dense_elimination_asymptotic_growth": round((doubled_n / inst["n"]) ** 3, 3),
        "doubled_verify_reason": doubled_reason,
    }

    invariance_checks = 0
    carried_witness_checks = 0
    failures = []
    unrelated_keys = []
    for offset in range(20):
        original = make_instance(seed=7000 + offset, **ship_params)
        key = canonical_key(original)
        unrelated_keys.append(key)
        rng = random.Random(8000 + offset)

        reordered = copy.deepcopy(original)
        reordered["clauses"] = [list(reversed(clause))
                                  for clause in reversed(reordered["clauses"])]
        permutation = list(range(original["n"]))
        rng.shuffle(permutation)
        relabelled = _relabel_instance(original, permutation, rng)
        composed = copy.deepcopy(relabelled)
        composed["clauses"] = [list(reversed(clause))
                                for clause in reversed(composed["clauses"])]
        for name, variant in (
            ("clause_and_literal_reordering", reordered),
            ("variable_and_point_relabelling", relabelled),
            ("composed_relabelling", composed),
        ):
            invariance_checks += 1
            if canonical_key(variant) != key:
                failures.append([offset, name, "key changed"])
        carried_witness_checks += 1
        ok, reason = verify(relabelled, relabelled["answer"])
        if not ok:
            failures.append([offset, "variable relabelling", reason])
    report["G8_canonical_key"] = {
        "pass": not failures and len(set(unrelated_keys)) == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_witness_checks,
        "distinct_unrelated_keys": len(set(unrelated_keys)),
        "unrelated_instances": 20,
        "symmetries": (
            "clause order, literal order, arbitrary variable/point relabelling, "
            "and their composition"
        ),
        "key_basis": (
            "the lexicographically least dihedral rotation of the decoded XOR "
            "right-hand-side cycle, never the seed or rendered text"
        ),
        "failures": failures,
    }

    size = _answer_size(answer)
    arms = copy.deepcopy(G9_RESULTS["arms"])
    hinted_attempts = arms["hinted"]["attempts"]
    placebo_attempts = arms["placebo"]["attempts"]
    hinted_rate = arms["hinted"]["solved"] / hinted_attempts if hinted_attempts else 0.0
    placebo_rate = (
        arms["placebo"]["solved"] / placebo_attempts if placebo_attempts else 0.0
    )
    intended_operations = max(compact_operations)
    hinted_hardened = G9_RESULTS["hinted_verdict"] == "hardened"
    within_caps = (
        size["chars"] <= 2000
        and size["elements"] <= 256
        and intended_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "hinted_harness_verdict": G9_RESULTS["hinted_harness_verdict"],
        "answer_chars": size["chars"],
        "answer_tokens": size["tokens"],
        "answer_elements": size["elements"],
        "intended_route_operations": intended_operations,
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
