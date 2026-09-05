"""Verified generator for strict red-blue separation on a rational circle.

The native problem is from Sections 2 and 3.1 of arXiv:2005.06046.  The
paper proves that a cyclic red/blue point set with 2k colour switches can be
separated optimally by k chords.  This module composes that theorem with an
exact polynomial colour identity: its roots are sampled first, the colour
polynomial is expanded from them, and adjacent root gaps give the planted
chords.  Generation never scans the finished instance for a solution.
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
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import rationals
except ImportError:                 # Optional helper; this module has a stdlib path.
    rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "geometry",
    "object_regime": "rational_exact",
    "computational_core": "polynomial_identity",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "rational points on the unit circle",
        "straight chord lines",
        "integer colour polynomial",
    ],
    "verification_operations": [
        "exact integer polynomial evaluation",
        "exact rational circle parametrization",
        "exact chord side-sign comparison",
        "monochromatic-cell comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Recognize that the roots of the expanded colour polynomial are a "
        "centrally symmetric arithmetic progression; without that symmetry one "
        "must evaluate the colour rule along the entire cyclic point order."
    ),
    "hardness_basis": (
        "Track B: exact Sturm isolation solves this promised degree-d input in "
        "O(d^3 log N) rational operations, measured at 87,876 operations and "
        "about 0.08 seconds for d=18 and N=120011 (the paper's O(Nd) cyclic "
        "scan takes 4,320,396 integer operations), while coefficient symmetry "
        "recovers every chord endpoint in at most 66 exact operations, a route "
        "that is mechanically usable without tools only after the progression "
        "invariant is recognized."
    ),
    "max_answer_tokens": 55,
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
    "demo": {"n": 13, "chunks": 2, "multiplicity": 1},
    "easy": {"n": 120_011, "chunks": 9, "multiplicity": 1},
    "medium": {"n": 180_013, "chunks": 9, "multiplicity": 3},
    "hard": {"n": 260_003, "chunks": 9, "multiplicity": 5},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The distinct roots of the displayed colour polynomial form a centrally "
    "symmetric arithmetic progression."
)
PLACEBO_HINT = (
    "Keep the endpoint fractions normalized and follow the required canonical "
    "ordering carefully."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A canonical JSON matrix of exactly k unordered chord rows; each row has "
        "two distinct normalized rational endpoints [odd,2] chosen from the N-1 "
        "midpoint gaps, all 2k endpoints are distinct, endpoints within a row and "
        "rows within the matrix are increasing."
    ),
    "bounds": {
        "rows": "k",
        "rational_denominator": 2,
        "endpoint_numerator_min": 1,
        "endpoint_numerator_max": "2N-3",
        "distinct_endpoints": "2k",
        "candidate_count": "C(N-1,2k) * (2k-1)!!",
    },
}

NOTES = (
    "Section 2 fixes strict separation: no input point lies on a line, and every "
    "red-blue segment must meet a chosen line.  Proposition 3.1 identifies colour "
    "switches as mandatory line intersections, while Section 3.1 constructs one "
    "chord per monochromatic chunk and Theorem 3.8 states polynomial-time "
    "solvability on a circle.  Thus Track A is unavailable.  Mechanically, the "
    "paper's method scans the cyclic order; the generator instead samples the "
    "switch gaps first as a symmetric arithmetic progression, expands the exact "
    "colour polynomial, and carries adjacent gaps into chord certificates.  "
    "A counted Sturm-sequence implementation is the successful generic reference "
    "algorithm; the paper's cyclic scan is also measured separately.  Increasing "
    "odd root multiplicity preserves colours while making blind evaluation more "
    "expensive.  Random centres and spacings defeat endpoint "
    "outliers, leftmost/edge greedies, unit-spacing and small-spacing ansatzes, "
    "and uniform random matchings; the full scan is disclosed as the successful "
    "Track B reference algorithm."
)

# Filled with script-owned evidence after the three hardening runs.  Zeroes are
# an explicit unrun/default state, not evidence manufactured by selftest.
G9_ORACLE_RESULTS = {
    # The latest bare harness run completed all three calls at the candidate
    # shipping preset before the shared OpenRouter quota was exhausted while
    # testing the next rung.  The two diagnostic arms could not be scored.
    "bare": {"solved": 2, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unrun",
}


def _poly_mul(a, b):
    out = [0] * (len(a) + len(b) - 1)
    for i, x in enumerate(a):
        for j, y in enumerate(b):
            out[i + j] += x * y
    return out


def _poly_pow(poly, exponent):
    out = [1]
    base = list(poly)
    power = exponent
    while power:
        if power & 1:
            out = _poly_mul(out, base)
        power //= 2
        if power:
            base = _poly_mul(base, base)
    return out


def _poly_eval(coefficients, value):
    result = 0
    for coefficient in reversed(coefficients):
        result = result * value + coefficient
    return result


def _sign(value):
    return 1 if value > 0 else -1 if value < 0 else 0


def _matching_count(even_size):
    result = 1
    for odd in range(1, even_size, 2):
        result *= odd
    return result


def _canonical_answer_from_numerators(numerators):
    ordered = sorted(numerators)
    rows = [
        [[ordered[i], 2], [ordered[i + 1], 2]]
        for i in range(0, len(ordered), 2)
    ]
    return sorted(rows)


def make_instance(n, seed=0, **params):
    """Compose a circle instance from roots and known separating chords.

    Roots/switches and the answer are chosen before the public polynomial is
    expanded.  No colour scan, factoring, or separator search is performed.
    """
    chunks = params.pop("chunks", 9)
    multiplicity = params.pop("multiplicity", 1)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 9:
        raise ValueError("n must be an integer at least 9")
    if isinstance(chunks, bool) or not isinstance(chunks, int) or chunks < 2:
        raise ValueError("chunks must be an integer at least 2")
    if (isinstance(multiplicity, bool) or not isinstance(multiplicity, int)
            or multiplicity < 1 or multiplicity % 2 == 0):
        raise ValueError("multiplicity must be a positive odd integer")

    distinct_degree = 2 * chunks
    max_offset = distinct_degree - 1
    if n < 2 * max_offset + 7:
        raise ValueError("n is too small for the requested number of chunks")
    rng = random.Random(seed)

    # The doubled roots must be odd so each root R/2 lies strictly between the
    # two integer parameters (R-1)/2 and (R+1)/2.  The progression scale is even.
    max_spacing = max(2, (n - 3) // (2 * max_offset))
    max_spacing -= max_spacing % 2
    min_spacing = max(2, max_spacing // 3)
    if min_spacing % 2:
        min_spacing += 1
    spacing_choices = (max_spacing - min_spacing) // 2 + 1
    spacing = min_spacing + 2 * rng.randrange(spacing_choices)
    extent = spacing * max_offset
    low_center = 1 + extent
    high_center = 2 * n - 3 - extent
    if low_center % 2 == 0:
        low_center += 1
    if high_center % 2 == 0:
        high_center -= 1
    center = low_center + 2 * rng.randrange((high_center - low_center) // 2 + 1)

    offsets = list(range(-max_offset, max_offset + 1, 2))
    roots = [center + spacing * offset for offset in offsets]
    base_polynomial = [1]
    for root in roots:
        base_polynomial = _poly_mul(base_polynomial, [-root, 1])
    coefficients = _poly_pow(base_polynomial, multiplicity)

    # Q is positive outside its roots and every multiplicity is odd, so the
    # negative (blue) chunks lie between roots 0-1, 2-3, ... .  Section 3.1's
    # construction joins the two adjacent switches of each such chunk.
    answer = _canonical_answer_from_numerators(roots)
    return {
        "family": "strict red-blue chord separation on a rational circle",
        "n": n,
        "chunks": chunks,
        "multiplicity": multiplicity,
        "coefficients": coefficients,       # ascending powers of z
        "red_sign": 1,
        "answer": answer,
    }


def render(inst):
    coefficients = ", ".join(str(x) for x in inst["coefficients"])
    k = inst["chunks"]
    sample_rows = [
        [[4 * i + 1, 2], [4 * i + 3, 2]]
        for i in range(k)
    ]
    statement = f"""Strictly separate red and blue rational points on a circle.

For every integer j with 0 <= j < N={inst['n']}, the input contains the exact
point

    P(j) = ((1-j^2)/(1+j^2), 2j/(1+j^2))

on the unit circle.  These are N distinct points, encountered in increasing j
order along one arc.  Let Q(z)=a_0+a_1*z+...+a_d*z^d be the integer polynomial
whose coefficients [a_0,a_1,...,a_d] (ascending-power order) are

    [{coefficients}]

A point P(j) is red when {inst['red_sign']}*Q(2j)>0 and blue when
{inst['red_sign']}*Q(2j)<0.  The supplied data guarantee Q(2j) is never zero.

A chord endpoint parameter u means the rational point
P(u)=((1-u^2)/(1+u^2),2u/(1+u^2)).  A chord row [u,v] denotes the entire straight
line through P(u) and P(v).  A collection of lines strictly separates the input
when no input point lies on a line and every cell induced by the lines contains
points of at most one colour (equivalently, every red-blue segment meets a line).

Find exactly k={k} separating chord lines.  Every endpoint must be the midpoint
of a gap between consecutive input parameters: write it as the normalized
rational [r,2], where r is odd and 1 <= r <= {2 * inst['n'] - 3}.  All {2*k}
endpoints must be distinct.  In each chord put the smaller rational first, and
sort the k chord rows lexicographically.  Thus the answer is a JSON matrix of
shape k by 2 by 2; order is only a required canonical serialization, not a
geometric orientation.  Fractions are exact [numerator,denominator] pairs.

Give your final answer inside <answer></answer> tags, as that JSON matrix.
Example: <answer>{json.dumps(sample_rows, separators=(',', ':'))}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Parse a tagged JSON chord matrix, tolerating prose and fenced output."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, re.I | re.S)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError):
        return None
    if not isinstance(value, list):
        return None
    return value


def _validated_numerators(inst, answer):
    if not isinstance(answer, list):
        return None, "answer must be a JSON list of chord rows"
    if not answer:
        return None, "answer must not be empty"
    if len(answer) != inst["chunks"]:
        return None, f"expected {inst['chunks']} chord rows, got {len(answer)}"
    rows = []
    flat = []
    for row_index, row in enumerate(answer, 1):
        if not isinstance(row, list) or len(row) != 2:
            return None, f"chord row {row_index} must contain exactly two endpoints"
        parsed_row = []
        for endpoint_index, endpoint in enumerate(row, 1):
            if (not isinstance(endpoint, list) or len(endpoint) != 2
                    or any(isinstance(x, bool) or not isinstance(x, int)
                           for x in endpoint)):
                return None, (
                    f"endpoint {row_index}.{endpoint_index} must be an integer "
                    "[numerator,denominator] pair"
                )
            numerator, denominator = endpoint
            if denominator != 2 or numerator % 2 == 0:
                return None, (
                    f"endpoint {row_index}.{endpoint_index} is not a normalized "
                    "half-integer gap midpoint"
                )
            if not 1 <= numerator <= 2 * inst["n"] - 3:
                return None, f"endpoint {row_index}.{endpoint_index} is outside the gap range"
            parsed_row.append(numerator)
            flat.append(numerator)
        rows.append(parsed_row)
    if len(set(flat)) != len(flat):
        return None, "all chord endpoints must be distinct"
    if any(row[0] >= row[1] for row in rows):
        return None, "endpoints within each chord must be strictly increasing"
    if rows != sorted(rows):
        return None, "chord rows must be lexicographically sorted"
    return rows, "ok"


def verify(inst, answer):
    """Check any canonical chord witness exactly; never consult inst['answer']."""
    rows, reason = _validated_numerators(inst, answer)
    if rows is None:
        return False, reason
    coefficients = inst["coefficients"]

    # This cheap necessary check makes malformed random candidates cheap without
    # weakening verification of a candidate that reaches the geometric test.
    for endpoint_number, numerator in enumerate(itertools.chain.from_iterable(rows), 1):
        gap = (numerator - 1) // 2
        left = _poly_eval(coefficients, 2 * gap)
        right = _poly_eval(coefficients, 2 * (gap + 1))
        if left == 0 or right == 0 or _sign(left) == _sign(right):
            return False, f"endpoint {endpoint_number} is not a color-switch gap"

    # For chord endpoints u=r/2 and v=s/2, substituting P(j) into the chord
    # equation has the sign of (2j-r)(2j-s), up to one common positive factor.
    # The tuple below is therefore the exact line-arrangement cell signature.
    cell_colors = {}
    for j in range(inst["n"]):
        doubled = 2 * j
        signature = tuple(
            1 if (doubled - left) * (doubled - right) > 0 else -1
            for left, right in rows
        )
        polynomial_sign = _sign(_poly_eval(coefficients, doubled))
        if polynomial_sign == 0:
            return False, f"instance point P({j}) lies on the color polynomial"
        colour = 1 if inst["red_sign"] * polynomial_sign > 0 else -1
        previous = cell_colors.setdefault(signature, colour)
        if previous != colour:
            return False, "a line-arrangement cell contains both red and blue points"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample canonical matchings of 2k distinct midpoint gaps."""
    count = 2 * inst["chunks"]
    gaps = rng.sample(range(inst["n"] - 1), count)
    rng.shuffle(gaps)
    rows = []
    for i in range(0, count, 2):
        pair = sorted((2 * gaps[i] + 1, 2 * gaps[i + 1] + 1))
        rows.append([[pair[0], 2], [pair[1], 2]])
    return sorted(rows)


def search_space(inst):
    gaps = inst["n"] - 1
    endpoints = 2 * inst["chunks"]
    return math.comb(gaps, endpoints) * _matching_count(endpoints)


def _all_matchings(values):
    values = tuple(values)
    if not values:
        yield ()
        return
    first = values[0]
    for i in range(1, len(values)):
        second = values[i]
        rest = values[1:i] + values[i + 1:]
        for tail in _all_matchings(rest):
            yield ((first, second),) + tail


def enumerate_all(inst):
    total = search_space(inst)
    if total > 100_000:
        return None
    endpoints = 2 * inst["chunks"]
    count = 0
    for chosen in itertools.combinations(range(inst["n"] - 1), endpoints):
        numerators = [2 * gap + 1 for gap in chosen]
        for matching in _all_matchings(numerators):
            candidate = sorted(
                [[[min(a, b), 2], [max(a, b), 2]] for a, b in matching]
            )
            count += int(verify(inst, candidate)[0])
    return count


def canonical_key(inst):
    """Normalize polynomial scaling/sign and global colour-name exchange.

    The compressed point set has no input-list ordering.  Positive polynomial
    scaling is the same colour rule, simultaneous polynomial/sign negation is
    the same rule, and exchanging red with blue preserves all separators.
    """
    coefficients = list(inst["coefficients"])
    content = 0
    for coefficient in coefficients:
        content = math.gcd(content, abs(coefficient))
    content = max(content, 1)
    coefficients = [coefficient // content for coefficient in coefficients]
    if coefficients[-1] < 0:
        coefficients = [-coefficient for coefficient in coefficients]
    payload = {
        "n": inst["n"],
        "chunks": inst["chunks"],
        "polynomial_up_to_nonzero_scale": coefficients,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def escalate(params):
    """Grow scan length and odd multiplicity without lengthening the witness."""
    n = params.get("n")
    chunks = params.get("chunks", 9)
    multiplicity = params.get("multiplicity", 1)
    if not all(isinstance(x, int) for x in (n, chunks, multiplicity)):
        return None
    if multiplicity < 7:
        return {
            "n": min(600_011, max(n + 1, (3 * n) // 2)),
            "chunks": chunks,
            "multiplicity": multiplicity + 2,
        }
    if n < 600_011:
        return {"n": min(600_011, 2 * n), "chunks": chunks, "multiplicity": multiplicity}
    return None


def _reference_scan(inst):
    """Section 3.1's full cyclic colour scan, with exact operation count."""
    coefficients = inst["coefficients"]
    degree = len(coefficients) - 1
    switches = []
    previous = _sign(_poly_eval(coefficients, 0))
    operations = 2 * degree
    for j in range(1, inst["n"]):
        current = _sign(_poly_eval(coefficients, 2 * j))
        operations += 2 * degree
        if current != previous:
            switches.append(2 * j - 1)
        previous = current
    answer = _canonical_answer_from_numerators(switches)
    return answer, operations


def _counted_normalize(poly):
    out = list(poly)
    while out and out[-1] == 0:
        out.pop()
    return out


def _counted_derivative(poly, counter):
    out = []
    for index in range(1, len(poly)):
        out.append(poly[index] * index)
        counter[0] += 1
    return _counted_normalize(out)


def _counted_divmod_poly(dividend, divisor, counter):
    remainder = _counted_normalize(dividend)
    divisor = _counted_normalize(divisor)
    if not divisor:
        raise ZeroDivisionError("polynomial division by zero")
    divisor_degree = len(divisor) - 1
    quotient = [Fraction(0)] * max(0, len(remainder) - divisor_degree)
    for power in range(len(remainder) - 1, divisor_degree - 1, -1):
        if remainder[power] == 0:
            continue
        factor = remainder[power] / divisor[-1]
        counter[0] += 1
        quotient[power - divisor_degree] = factor
        for index in range(divisor_degree + 1):
            remainder[power - divisor_degree + index] -= factor * divisor[index]
            counter[0] += 2
    return _counted_normalize(quotient), _counted_normalize(remainder)


def _counted_monic(poly, counter):
    poly = _counted_normalize(poly)
    if not poly:
        return []
    leading = poly[-1]
    out = [coefficient / leading for coefficient in poly]
    counter[0] += len(poly)
    return out


def _counted_gcd_poly(left, right, counter):
    left = _counted_normalize(left)
    right = _counted_normalize(right)
    while right:
        _, remainder = _counted_divmod_poly(left, right, counter)
        left, right = right, remainder
    return _counted_monic(left, counter)


def _counted_squarefree_part(poly, counter):
    derivative = _counted_derivative(poly, counter)
    divisor = _counted_gcd_poly(poly, derivative, counter)
    if len(divisor) <= 1:
        return _counted_monic(poly, counter)
    quotient, remainder = _counted_divmod_poly(poly, divisor, counter)
    if remainder:
        raise ArithmeticError("nonzero remainder in squarefree decomposition")
    return _counted_monic(quotient, counter)


def _counted_scale_positive(poly, counter):
    if not poly:
        return []
    magnitude = abs(poly[-1])
    out = [coefficient / magnitude for coefficient in poly]
    counter[0] += len(poly)
    return out


def _counted_sturm_sequence(poly, counter):
    derivative = _counted_derivative(poly, counter)
    sequence = [
        _counted_scale_positive(poly, counter),
        _counted_scale_positive(derivative, counter),
    ]
    while len(sequence[-1]) > 1:
        _, remainder = _counted_divmod_poly(sequence[-2], sequence[-1], counter)
        if not remainder:
            break
        sequence.append(_counted_scale_positive(
            [-coefficient for coefficient in remainder], counter
        ))
    return sequence


def _counted_evaluate(poly, value, counter):
    x = Fraction(value)
    result = Fraction(0)
    for coefficient in reversed(poly):
        result = result * x + coefficient
        counter[0] += 2
    return result


def _counted_sign_changes(sequence, value, counter):
    previous = 0
    changes = 0
    for poly in sequence:
        result = _counted_evaluate(poly, value, counter)
        sign = 1 if result > 0 else -1 if result < 0 else 0
        if sign == 0:
            continue
        if previous and sign != previous:
            changes += 1
        previous = sign
    return changes


def _reference_sturm(inst):
    """Generic exact root isolation, with counted rational arithmetic.

    Generated roots are odd integers.  Sturm counts on even endpoints isolate
    each distinct root in a final interval (2j, 2j+2), so no numerical root
    approximation or factor table is used.
    """
    counter = [0]
    polynomial = [Fraction(coefficient) for coefficient in inst["coefficients"]]
    squarefree = _counted_squarefree_part(polynomial, counter)
    sequence = _counted_sturm_sequence(squarefree, counter)
    left = 0
    right = 2 * inst["n"]
    left_changes = _counted_sign_changes(sequence, left, counter)
    right_changes = _counted_sign_changes(sequence, right, counter)
    stack = [(left, right, left_changes, right_changes)]
    isolated = []
    while stack:
        lo, hi, changes_lo, changes_hi = stack.pop()
        root_count = changes_lo - changes_hi
        counter[0] += 1
        if root_count == 0:
            continue
        if hi - lo == 2:
            counter[0] += 2
            if root_count != 1:
                return None, counter[0]
            root = lo + 1
            counter[0] += 1
            if _counted_evaluate(squarefree, root, counter) != 0:
                return None, counter[0]
            isolated.append(root)
            continue
        midpoint = (lo + hi) // 2
        counter[0] += 2
        if midpoint % 2:
            midpoint -= 1
            counter[0] += 1
        if not lo < midpoint < hi:
            return None, counter[0]
        middle_changes = _counted_sign_changes(sequence, midpoint, counter)
        stack.append((midpoint, hi, middle_changes, changes_hi))
        stack.append((lo, midpoint, changes_lo, middle_changes))
    expected = 2 * inst["chunks"]
    if len(isolated) != expected:
        return None, counter[0]
    return _canonical_answer_from_numerators(isolated), counter[0]


def _compact_recover(inst):
    """Recover the progression from the top coefficients, counting operations."""
    coefficients = inst["coefficients"]
    total_degree = len(coefficients) - 1
    distinct_degree = 2 * inst["chunks"]
    operations = 0
    multiplicity = total_degree // distinct_degree
    operations += 1
    leading = coefficients[-1]
    root_sum = -coefficients[-2] // leading
    operations += 2
    center = root_sum // total_degree
    operations += 1
    e2 = coefficients[-3] // leading
    operations += 1
    root_square_sum = root_sum * root_sum - 2 * e2
    operations += 3
    offset_square_sum = distinct_degree * (distinct_degree * distinct_degree - 1) // 3
    operations += 4
    centered_square_sum = root_square_sum - total_degree * center * center
    operations += 3
    spacing_square = centered_square_sum // (multiplicity * offset_square_sum)
    operations += 2
    spacing = math.isqrt(spacing_square)
    operations += max(1, spacing_square.bit_length() // 2)
    if spacing * spacing != spacing_square:
        return None, operations
    operations += 1
    max_offset = distinct_degree - 1
    roots = []
    for offset in range(-max_offset, max_offset + 1, 2):
        roots.append(center + spacing * offset)
        operations += 2
    return _canonical_answer_from_numerators(roots), operations


def _candidate_from_center_spacing(inst, center, spacing):
    degree = 2 * inst["chunks"]
    roots = [
        center + spacing * offset
        for offset in range(-(degree - 1), degree, 2)
    ]
    if (len(set(roots)) != degree or min(roots) < 1
            or max(roots) > 2 * inst["n"] - 3 or any(root % 2 == 0 for root in roots)):
        return None
    return _canonical_answer_from_numerators(roots)


def _attack_candidates(inst, seed):
    k = inst["chunks"]
    endpoint_count = 2 * k
    max_gap = inst["n"] - 2
    leading = inst["coefficients"][-1]
    total_degree = len(inst["coefficients"]) - 1
    center = (-inst["coefficients"][-2] // leading) // total_degree

    leftmost = _canonical_answer_from_numerators(
        [2 * gap + 1 for gap in range(endpoint_count)]
    )
    edge_gaps = list(range(k)) + list(range(max_gap - k + 1, max_gap + 1))
    edges = _canonical_answer_from_numerators([2 * gap + 1 for gap in edge_gaps])
    unit = _candidate_from_center_spacing(inst, center, 2)
    small_spacing = [
        candidate
        for spacing in range(2, 66, 2)
        if (candidate := _candidate_from_center_spacing(inst, center, spacing)) is not None
    ]
    rrng = random.Random(seed ^ 0x200506046)
    restarts = [random_candidate(inst, rrng) for _ in range(256)]
    return {
        "outlier_extreme_gap_indices": [edges],
        "greedy_leftmost_consecutive_gaps": [leftmost],
        "midpoint_unit_spacing_ansatz": [unit] if unit is not None else [],
        "by_hand_32_small_spacing_trials": small_spacing,
        "random_restart_256": restarts,
    }


def _relabel_variants(inst, seed):
    rng = random.Random(seed)
    scale = rng.randrange(2, 10)
    variants = []
    # A: positive representation scaling; B: global colour exchange; C: negate
    # both the polynomial representation and red-sign convention.
    for mask in range(1, 8):
        out = {
            key: (list(value) if isinstance(value, list) else value)
            for key, value in inst.items()
        }
        if mask & 1:
            out["coefficients"] = [scale * x for x in out["coefficients"]]
        if mask & 2:
            out["red_sign"] *= -1
        if mask & 4:
            out["coefficients"] = [-x for x in out["coefficients"]]
            out["red_sign"] *= -1
        variants.append(out)
    return variants


def _answer_atom_count(value):
    if isinstance(value, dict):
        return sum(_answer_atom_count(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atom_count(v) for v in value)
    return 1


def selftest():
    report = {}
    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]

    g1_failures = []
    g1_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            g1_attempts += 1
            if not ok:
                g1_failures.append([preset, seed, why])
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                g1_failures.append([preset, seed, "answer is not JSON-native"])
    report["G1_planted_verifies"] = {
        "pass": not g1_failures,
        "attempts": g1_attempts,
        "failures": g1_failures,
        "construction": "sample roots, expand identity, carry adjacent switch chords",
    }

    inst = make_instance(seed=19, **shipping)
    answer = inst["answer"]
    swapped = [list(row) for row in answer]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicate = json.loads(json.dumps(answer))
    duplicate[-1][-1] = list(duplicate[0][0])
    out_of_range = json.loads(json.dumps(answer))
    out_of_range[0][0] = [-1, 2]
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": out_of_range,
    }
    rejected = {}
    for name, candidate in corruptions.items():
        ok, why = verify(inst, candidate)
        rejected[name] = {"rejected": not ok, "reason": why}
    reasons = [item["reason"] for item in rejected.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in rejected.values())
        and len(set(reasons)) == len(reasons),
        "cases": rejected,
        "distinct_reasons": len(set(reasons)),
    }

    response = (
        "The switch chords are below.\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nEach fraction is exact."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0],
        "parsed_equals_answer": parsed == answer,
    }

    guess_rng = random.Random(0x200506046)
    guess_total = 200_000
    guess_hits = 0
    start = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_seconds = time.perf_counter() - start
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "structure_aware_space": search_space(inst),
        "candidate_space_bits": search_space(inst).bit_length(),
        "wall_clock_sec": round(guess_seconds, 6),
    }

    attack_names = [
        "outlier_extreme_gap_indices",
        "greedy_leftmost_consecutive_gaps",
        "midpoint_unit_spacing_ansatz",
        "by_hand_32_small_spacing_trials",
        "random_restart_256",
    ]
    successes = {name: 0 for name in attack_names}
    attack_seconds = {name: 0.0 for name in attack_names}
    paper_scan_successes = 0
    paper_scan_seconds = 0.0
    paper_scan_operations = 0
    reference_successes = 0
    reference_seconds = 0.0
    reference_operations = 0
    reference_operations_max = 0
    compact_successes = 0
    compact_operations = 0
    for seed in range(101, 109):
        trial = make_instance(seed=seed, **shipping)
        candidates = _attack_candidates(trial, seed)
        for name in attack_names:
            start = time.perf_counter()
            won = any(verify(trial, candidate)[0] for candidate in candidates[name])
            attack_seconds[name] += time.perf_counter() - start
            successes[name] += int(won)
        start = time.perf_counter()
        recovered, operations = _reference_scan(trial)
        paper_scan_seconds += time.perf_counter() - start
        paper_scan_operations += operations
        paper_scan_successes += int(verify(trial, recovered)[0])
        start = time.perf_counter()
        recovered, operations = _reference_sturm(trial)
        reference_seconds += time.perf_counter() - start
        reference_operations += operations
        reference_operations_max = max(reference_operations_max, operations)
        reference_successes += int(
            recovered is not None and verify(trial, recovered)[0]
        )
        compact, operations = _compact_recover(trial)
        compact_operations = max(compact_operations, operations)
        compact_successes += int(compact is not None and verify(trial, compact)[0])
    attacks = {
        name: {
            "successes": successes[name],
            "attempts": 8,
            "wall_clock_sec": round(attack_seconds[name], 6),
        }
        for name in attack_names
    }
    reference = {
        "name": "exact Sturm-sequence isolation on even integer endpoints",
        "complexity": (
            "O(d^3 log N) rational-arithmetic operations on this promised "
            "integer-root family"
        ),
        "wall_clock_sec": round(reference_seconds / 8, 6),
        "operations": reference_operations // 8,
        "operations_max": reference_operations_max,
        "solves": f"{reference_successes}/8, as expected",
    }
    paper_scan = {
        "name": "Section 3.1 cyclic colour/chunk scan with Horner evaluation",
        "complexity": "O(Nd) exact integer operations for succinct degree d colours",
        "wall_clock_sec": round(paper_scan_seconds / 8, 6),
        "operations": paper_scan_operations // 8,
        "solves": f"{paper_scan_successes}/8, as expected",
    }
    all_failed = all(value == 0 for value in successes.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed
        and reference_successes == 8
        and paper_scan_successes == 8
        and compact_successes == 8,
        "attacks": attacks,
        "reference_algorithm": reference,
        "paper_reference_algorithm": paper_scan,
        "intended_compact_route": {
            "name": "leading-coefficient recovery of a symmetric root progression",
            "solves": f"{compact_successes}/8",
            "operations_upper_bound": compact_operations,
        },
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    exact_valid_matchings = _matching_count(2 * inst["chunks"])
    shipping_candidate_space = search_space(inst)
    shipping_exact_density = exact_valid_matchings / shipping_candidate_space
    report["G5_density_and_baseline_cost"] = {
        "pass": guess_fraction < 1e-6
        and shipping_exact_density < 1e-6
        and demo_count == _matching_count(2 * demo["chunks"])
        and all_failed
        and reference_successes == 8
        and paper_scan_successes == 8
        and compact_successes == 8,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "shipping_solution_density_sample": guess_fraction,
        "shipping_exact_solution_count": exact_valid_matchings,
        "shipping_exact_candidate_space": shipping_candidate_space,
        "shipping_exact_solution_density": shipping_exact_density,
        "shipping_exact_density_fraction": [
            exact_valid_matchings,
            shipping_candidate_space,
        ],
        "demo_exact_solution_count": demo_count,
        "demo_candidate_space": search_space(demo),
        "baseline_attack_wall_clock_sec": round(
            attack_seconds["random_restart_256"] / 8, 6
        ),
        "baseline_attack_iterations": 256,
        "reference_wall_clock_sec": reference["wall_clock_sec"],
        "reference_operation_count": reference["operations"],
        "reference_operation_count_max": reference["operations_max"],
        "paper_scan_wall_clock_sec": paper_scan["wall_clock_sec"],
        "paper_scan_operation_count": paper_scan["operations"],
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    start = time.perf_counter()
    doubled = make_instance(seed=77, **doubled_params)
    doubled_build = time.perf_counter() - start
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    ladder = [
        (DIFFICULTY[name]["n"], DIFFICULTY[name]["multiplicity"])
        for name in DIFFICULTY
    ]
    report["G7_scales"] = {
        "pass": doubled_ok
        and doubled["n"] == 2 * inst["n"]
        and search_space(doubled) > search_space(inst)
        and ladder == sorted(ladder)
        and len(set(ladder)) == len(ladder),
        "shipping_n": inst["n"],
        "doubled_n": doubled["n"],
        "doubled_build_sec": round(doubled_build, 6),
        "doubled_verify_reason": doubled_why,
        "candidate_space_bits_shipping": search_space(inst).bit_length(),
        "candidate_space_bits_doubled": search_space(doubled).bit_length(),
        "fixed_answer_rows": inst["chunks"],
    }

    invariant_count = 0
    real_transform_count = 0
    unrelated_keys = []
    # Canonicalization is representation-level, so a smaller non-demo instance
    # exercises every symmetry without repeating a 120k-point verification 140
    # times.  It still has ample centre/spacing entropy for distinctness.
    canonical_params = {"n": 10_009, "chunks": 4, "multiplicity": 1}
    for seed in range(201, 221):
        original = make_instance(seed=seed, **canonical_params)
        key = canonical_key(original)
        for transformed in _relabel_variants(original, seed ^ 0x5A5A):
            invariant_count += int(key == canonical_key(transformed))
            real_transform_count += int(verify(transformed, original["answer"])[0])
        unrelated_keys.append(key)
    distinct_count = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": invariant_count == 140
        and real_transform_count == 140
        and distinct_count == 20,
        "invariant_relabellings": invariant_count,
        "real_transformations_verified": real_transform_count,
        "unrelated_distinct_keys": distinct_count,
        "unrelated_attempts": 20,
        "transformations": [
            "positive polynomial representation scaling",
            "global red/blue name exchange",
            "simultaneous polynomial and colour-sign negation",
            "all nonempty compositions of those three",
        ],
    }

    encoded_answer = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(encoded_answer)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atom_count(inst["answer"])
    largest = 2 * inst["n"] - 3
    worst = [
        [[largest - 4 * i - 2, 2], [largest - 4 * i, 2]]
        for i in range(inst["chunks"])
    ]
    worst_case_answer_chars = len(json.dumps(worst, separators=(",", ":")))
    worst_case_answer_tokens = math.ceil(worst_case_answer_chars / 4)
    compact, measured_operations = _compact_recover(inst)
    # The integer-square-root counter varies by two operations with the sampled
    # spacing.  Report the worst case over the entire shipping spacing range.
    intended_operations = max(66, measured_operations)
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (
        answer_chars <= 2_000
        and answer_elements <= 256
        and intended_operations <= 300
        and PROBLEM_PROFILE["max_answer_tokens"] == worst_case_answer_tokens
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "worst_case_answer_chars": worst_case_answer_chars,
        "worst_case_answer_tokens": worst_case_answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "compact_route_verified": compact is not None and verify(inst, compact)[0],
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") is True for value in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
