"""Verified generator for covering parabola points by convex polygons.

The geometric encoding is the one used in Section 5.1 and Theorem 1.9 of
arXiv:1504.05476: points on a parabola are in convex position, so the convex
polygon through any chosen subset covers exactly that subset of parabola
points.  Here those subsets form a cyclic covering instance.

For boundary i, polygon C(i, x) omits one outgoing point B(i, x), while
the polygon in the successor group C(s(i), y) contains one incoming point
B(i, g_i(y)).  The groups form three disjoint directed cycles.  Thus a cover
choosing one polygon from every group exists exactly when
    x_i = g_i(x_{s(i)}).
After one common base-3 digit-reversal change of variables, the g_i become
affine permutations of Z/nZ.  The answer is sampled first and the conjugated
affine maps are built around it; generation never solves the emitted covering
instance.
"""

from __future__ import annotations

import bisect
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
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "integer-coordinate points on a parabola",
        "closed convex polygons specified by exact parabola vertices",
    ],
    "verification_operations": [
        "exact integer orientation",
        "exact convex-polygon point containment",
        "cardinality and range checks",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 5.1, proof of Theorem 1.9: parabola points encode arbitrary "
        "set incidences as convex-polygon containment"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Reverse the base-3 digits of every polygon label to expose affine "
        "boundary permutations modulo n; otherwise one must propagate every "
        "possible starting polygon around each cycle."
    ),
    "hardness_basis": (
        "Track B: Section 5.1 and Theorem 1.9 encode covering incidences by "
        "convex polygons on a parabola; the distribution-specific reference "
        "algorithm builds inverse boundary tables and propagates all n starts "
        "on each of three cycles "
        "in O(kn) time; at the shipping instance n=729,k=18 it "
        "used 19,596 indexed operations and 0.010 seconds on the measured seed "
        "(26,244 operations worst case), while the common base-3 "
        "digit-reversal change of variables uses 108 exact arithmetic "
        "operations plus 54 short digit reversals and is not visible as raw "
        "affine differencing in the 13,122 displayed table entries."
    ),
    "max_answer_tokens": 39,
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
    "demo": {"n": 9, "k": 3},
    "easy": {"n": 729, "k": 18},
    "medium": {"n": 2187, "k": 18},
    "hard": {"n": 6561, "k": 18},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Reversing every residue's fixed-width base-3 digits makes each boundary "
    "permutation affine modulo n."
)
PLACEBO_HINT = (
    "Reading every zero-based table position carefully keeps every boundary "
    "permutation indexed modulo n."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "Normal-form cyclic covers: exactly k distinct polygon identifiers "
        "i:x, one for every group i=0,...,k-1, with k-3 boundary equations "
        "propagated from one freely sampled residue on each of three cycles; "
        "order is irrelevant."
    ),
    "bounds": {
        "pairs": "k",
        "group_min": 0,
        "group_max": "k-1",
        "residue_min": 0,
        "residue_max": "n-1",
        "free_cycle_starts": 3,
        "candidate_count": "n^3",
    },
}

NOTES = (
    "Section 3.1 fixes the paper's general problem, including its exact-k "
    "condition and normality requirement.  The generated family instead uses "
    "the paper-licensed convex-polygon covering representation of Section 5.1: Theorem 1.9's "
    "proof places clients p_j=(j(N+1),j^2) on a parabola and observes that a "
    "convex polygon through any chosen subset covers exactly that subset.  "
    "The positive n^{O(sqrt(k))} results for disks and squares do not extend "
    "to arbitrary convex polygons; Theorem 1.9 gives an n^{k-o(1)} SETH lower "
    "bound for the general family.  This particular distribution is Track B, "
    "because its boundary maps admit an O(kn) propagation algorithm.  "
    "Generation samples the k selected polygons first, samples unit affine "
    "slopes with product two on each cycle, conjugates every map by "
    "fixed-width base-3 digit reversal, and sets each intercept so the sampled "
    "polygons cover.  Equal polygon vertex counts defeat size outliers; conjugated "
    "affine maps defeat fixed-label and raw-arithmetic-progression guesses; the "
    "three unique cyclic fixed points defeat greedy start-zero propagation and "
    "structure-aware random-start restarts."
)


# Filled only from scored, script-owned oracle transcripts.  API errors do not
# count as attempts and cannot support a hardness claim.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer>", re.I | re.S)
_PAIR_RE = re.compile(r"(\d+)\s*:\s*([012]+)_3")


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_power_of_three(value):
    if not _is_int(value) or value < 1:
        return False
    while value % 3 == 0:
        value //= 3
    return value == 1


def _ternary_width(n):
    width = 0
    value = n
    while value > 1:
        value //= 3
        width += 1
    return width


def _digit_reverse(value, n):
    """Reverse exactly log_3(n) ternary digits; this is an involution."""
    result = 0
    for _ in range(_ternary_width(n)):
        value, digit = divmod(value, 3)
        result = 3 * result + digit
    return result


def _ternary_word(value, n):
    """Fixed-width base-3 notation for one residue in 0,...,n-1."""
    width = _ternary_width(n)
    digits = []
    for _ in range(width):
        value, digit = divmod(value, 3)
        digits.append(str(digit))
    return "".join(reversed(digits))


def _validate_parameters(n, k):
    if not _is_power_of_three(n) or n < 9:
        raise ValueError("n must be a power of 3 at least 9")
    if not _is_int(k) or k < 3 or k > 120:
        raise ValueError("k must be an integer in 3,...,120")


def _point_layout(n, k):
    interior = k * (n + 1)
    last = interior + 1
    return interior, last


def _group_index(n, group):
    return 1 + group * (n + 1)


def _boundary_index(n, group, residue):
    return 2 + group * (n + 1) + residue


def _cycles(k):
    """Three intrinsic directed cycles, interleaved across the group labels."""
    return [list(range(offset, k, 3)) for offset in range(3)]


def _cycle_links(k):
    successor = [None] * k
    predecessor = [None] * k
    for cycle in _cycles(k):
        for pos, group in enumerate(cycle):
            nxt = cycle[(pos + 1) % len(cycle)]
            successor[group] = nxt
            predecessor[nxt] = group
    return successor, predecessor


def _apply_affine(transform, point):
    a, b, c, d, tx, ty = transform
    x, y = point
    return [a * x + b * y + tx, c * x + d * y + ty]


def _base_point(inst, point_index):
    last = inst["last_point"]
    if point_index == -1:  # the non-client apex
        return [0, last * last]
    return [point_index * last, point_index * point_index]


def _point(inst, point_index):
    return _apply_affine(inst["affine_transform"], _base_point(inst, point_index))


def _cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _polygon_vertex_indices(inst, group, residue):
    """Parabola-vertex indices of C(group,residue), in increasing order."""
    n = inst["n"]
    k = inst["k"]
    _, predecessor = _cycle_links(k)
    previous = predecessor[group]
    incoming_residue = inst["maps"][previous][residue]
    vertices = [
        0,
        _group_index(n, group),
        _boundary_index(n, previous, incoming_residue),
        inst["last_point"],
    ]
    outgoing_start = _boundary_index(n, group, 0)
    vertices.extend(
        outgoing_start + z for z in range(n) if z != residue
    )
    return sorted(set(vertices))


def _polygon_covers_index(inst, group, residue, point_index):
    """Exact containment for a generated client in a generated polygon.

    Included parabola points are polygon vertices.  For an omitted point, its
    adjacent included parabola vertices form a lower-hull edge and the apex is
    strictly on the other side of that edge.  The exact orientation comparison
    is an executable separation certificate, including after any invertible
    affine transformation.
    """
    n = inst["n"]
    k = inst["k"]
    last = inst["last_point"]
    if point_index in (0, last, _group_index(n, group)):
        return True

    outgoing_start = _boundary_index(n, group, 0)
    outgoing_end = outgoing_start + n - 1
    omitted = outgoing_start + residue
    if outgoing_start <= point_index <= outgoing_end and point_index != omitted:
        return True

    _, predecessor = _cycle_links(k)
    previous = predecessor[group]
    incoming = _boundary_index(
        n, previous, inst["maps"][previous][residue]
    )
    if point_index == incoming:
        return True

    # Find the neighboring included parabola vertices without materializing
    # the n-1 consecutive outgoing vertices.
    fixed = [0, _group_index(n, group), incoming, last]
    candidates = list(fixed)
    below = min(outgoing_end, point_index - 1)
    if below == omitted:
        below -= 1
    if outgoing_start <= below <= outgoing_end:
        candidates.append(below)
    above = max(outgoing_start, point_index + 1)
    if above == omitted:
        above += 1
    if outgoing_start <= above <= outgoing_end:
        candidates.append(above)
    candidates = sorted(set(candidates))
    pos = bisect.bisect_left(candidates, point_index)
    if pos == 0 or pos == len(candidates):
        return False
    left_index, right_index = candidates[pos - 1], candidates[pos]
    left = _point(inst, left_index)
    right = _point(inst, right_index)
    query = _point(inst, point_index)
    apex = _point(inst, -1)
    interior_side = _cross(left, right, apex)
    query_side = _cross(left, right, query)
    return query_side == 0 or query_side * interior_side > 0


def make_instance(n, seed=0, k=18) -> dict:
    """Inverse-generate a unique cyclic cover and its polygon witness."""
    _validate_parameters(n, k)
    rng = random.Random(seed)

    # Sample the answer before any map is constructed.  Excluding the three
    # elementary ansatzes only keeps the adversary checks deterministic; it
    # does not solve or search the resulting instance.
    while True:
        selected_u = [rng.randrange(n) for _ in range(k)]
        selected = [_digit_reverse(value, n) for value in selected_u]
        if selected[0] == 0:
            continue
        if len(set(selected)) == 1:
            continue
        if all(selected[i] == i % n for i in range(k)):
            continue
        break

    cycles = _cycles(k)
    successor, _ = _cycle_links(k)
    units = [value for value in range(1, n) if math.gcd(value, n) == 1]
    slopes = [units[rng.randrange(len(units))] for _ in range(k)]
    for cycle in cycles:
        # Make the composed slope exactly 2.  Then 1-2=-1 is a unit for every
        # allowed modulus, so each affine cycle has one fixed point.  It also makes the
        # final modular inverse in the compact route trivial for every seed,
        # keeping that route below the no-tool arithmetic cap.
        last = cycle[-1]
        others = math.prod(slopes[i] for i in cycle[:-1]) % n
        slopes[last] = 2 * pow(others, -1, n) % n

    maps = []
    relabel = [_digit_reverse(value, n) for value in range(n)]
    for i, slope in enumerate(slopes):
        nxt = selected_u[successor[i]]
        intercept = (selected_u[i] - slope * nxt) % n
        maps.append([
            relabel[(slope * relabel[value] + intercept) % n]
            for value in range(n)
        ])
    inverse_maps = []
    for table in maps:
        inverse = [0] * n
        for source, target in enumerate(table):
            inverse[target] = source
        inverse_maps.append(inverse)

    # A random invertible affine transformation changes every displayed
    # coordinate but preserves convexity and containment.
    while True:
        a, b, c, d = [rng.randint(-4, 4) for _ in range(4)]
        if a * d - b * c:
            break
    affine = [a, b, c, d, rng.randint(-100, 100), rng.randint(-100, 100)]
    _, last = _point_layout(n, k)
    map_order = list(range(k))
    rng.shuffle(map_order)

    return {
        "family": "three-cycle convex-polygon cover",
        "n": n,
        "k": k,
        "last_point": last,
        "cycles": cycles,
        "maps": maps,
        "inverse_maps": inverse_maps,
        "affine_transform": affine,
        "map_declaration_order": map_order,
        "answer": [[i, selected[i]] for i in range(k)],
    }


def _format_table(values, n, width=20):
    lines = []
    for start in range(0, len(values), width):
        lines.append(
            " ".join(_ternary_word(x, n) for x in values[start:start + width])
        )
    return "\n      ".join(lines)


def render(inst) -> str:
    n = inst["n"]
    k = inst["k"]
    last = inst["last_point"]
    a, b, c, d, tx, ty = inst["affine_transform"]
    tables = []
    for i in inst["map_declaration_order"]:
        tables.append(
            f"g_{i}(0),...,g_{i}({n - 1}):\n      "
            + _format_table(inst["maps"][i], n)
        )
    zero_word = _ternary_word(0, n)
    example = ", ".join(f"{i}:{zero_word}_3" for i in range(k))
    cycles = "\n".join(
        "    " + " -> ".join(map(str, cycle + [cycle[0]]))
        for cycle in inst["cycles"]
    )

    statement = f"""Convex-polygon point cover (all arithmetic is exact)

Let n={n}, k={k}, and L={last}.  The modulus n is a power of 3.  Start with parabola points
P_j=(jL,j^2) for every integer 0 <= j <= L, and the apex A=(0,L^2).
Apply the same affine map
    T(x,y)=({a}x{b:+d}y{tx:+d}, {c}x{d:+d}y{ty:+d})
to every point.  Its determinant is {a*d-b*c}, so it is invertible.  The
clients to cover are all transformed points T(P_j); T(A) is not a client.

For 0 <= i < k and 0 <= z < n, define client names
    G_i     = T(P_(1+i(n+1)))
    B_i,z   = T(P_(2+i(n+1)+z)).
The group-successor map s(i) is defined by these three directed cycles:
{cycles}
Let p(i) denote the predecessor of i in its displayed cycle.  All index bounds
above are inclusive where <= is written; all i and z indices are zero-based.

There are kn candidate closed convex polygons C(i,x), one for each
0 <= i < k and 0 <= x < n.  C(i,x) is the convex hull of these exact points:
    T(A), T(P_0), T(P_L), G_i,
    every B_i,z with z != x, and
    the one point B_p(i),g_p(i)(x).
Equivalently, put those vertices in increasing P-index order around the lower
chain, with T(A) closing the polygon.  Boundary points count as covered.
No other points are polygon vertices.  The tables defining the permutations
g_i are below.  Each table is listed at inputs 0,1,...,n-1 even though the
table blocks themselves may appear in any order.  Every table output is a
fixed-width base-3 word; leading zeroes are significant, and a word
d_(w-1)...d_0 denotes the integer sum d_j*3^j.

{chr(10).join(tables)}

Select exactly k distinct polygons whose union covers every client T(P_j).
The answer is unordered.  A valid cover necessarily selects one polygon from
each group i, but you must give all k concrete polygon identifiers.

Give your final answer inside <answer></answer> tags as comma-separated
i:trits_3 pairs, with exactly one pair for every i=0,...,{k - 1}.  Each trits
field is exactly {_ternary_width(n)} base-3 digits (including leading zeroes)
and represents x in 0,...,{n - 1}.
Example format (showing the required shape, not a claimed cover):
<answer>{example}</answer>
Output nothing else inside the tags."""

    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    if not isinstance(text, str):
        return None
    matches = list(_ANSWER_RE.finditer(text))
    if not matches:
        return None
    body = matches[-1].group(1).strip()
    if not body:
        return []
    pieces = body.split(",")
    answer = []
    for piece in pieces:
        match = _PAIR_RE.fullmatch(piece.strip())
        if match is None:
            return None
        answer.append([int(match.group(1)), int(match.group(2), 3)])
    return answer


def verify(inst, answer):
    """Check any proposed polygon cover, never consulting inst['answer']."""
    k = inst["k"]
    n = inst["n"]
    if not isinstance(answer, list):
        return False, "answer must be a list of polygon identifiers"
    if not answer:
        return False, "answer is empty"
    if len(answer) != k:
        return False, f"expected exactly k={k} polygons"
    for pair in answer:
        if not (
            isinstance(pair, list)
            and len(pair) == 2
            and _is_int(pair[0])
            and _is_int(pair[1])
        ):
            return False, "each polygon identifier must have form [i,x]"
    if len({tuple(pair) for pair in answer}) != k:
        return False, "duplicate polygon identifier"
    for group, residue in answer:
        if not 0 <= group < k:
            return False, "polygon group out of range"
        if not 0 <= residue < n:
            return False, "polygon label out of range"
    chosen = {}
    for group, residue in answer:
        if group in chosen:
            return False, "two polygons were selected from one group"
        chosen[group] = residue
    if len(chosen) != k:
        return False, "a polygon group is missing"

    # G_i forces one selected polygon per group.  C(i,x_i) covers every
    # outgoing B_i,z except B_i,x_i.  Check that the next selected polygon
    # geometrically contains precisely this remaining client.
    successor, _ = _cycle_links(k)
    for i in range(k):
        missing = _boundary_index(n, i, chosen[i])
        next_group = successor[i]
        if not _polygon_covers_index(
            inst, next_group, chosen[next_group], missing
        ):
            return False, f"boundary {i} client B_{i},{chosen[i]} is uncovered"
    return True, "ok"


def random_candidate(inst, rng):
    """Uniformly sample starts, propagating every non-closing cycle edge."""
    values = _propagate_cycle_starts(
        inst, [rng.randrange(inst["n"]) for _ in inst["cycles"]]
    )
    groups = list(range(inst["k"]))
    rng.shuffle(groups)
    return [[i, values[i]] for i in groups]


def search_space(inst):
    return inst["n"] ** len(inst["cycles"])


def enumerate_all(inst):
    space = search_space(inst)
    if space > 200_000:
        return None
    total = 0
    for starts in itertools.product(range(inst["n"]), repeat=len(inst["cycles"])):
        residues = _propagate_cycle_starts(inst, starts)
        candidate = [[i, residues[i]] for i in range(inst["k"])]
        total += int(verify(inst, candidate)[0])
    return total


def canonical_key(inst):
    """Hash canonical labelled incidence data, never seed or rendering.

    The table index i and residue input are intrinsic polygon/client labels in
    the formula.  Declaration order and every global invertible affine change
    of coordinates are normalized away because neither changes containment.
    """
    payload = {
        "n": inst["n"],
        "k": inst["k"],
        "cycles": inst["cycles"],
        "maps": inst["maps"],
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params):
    current = params.get("n")
    k = params.get("k", 18)
    if not _is_int(current):
        return None
    # Grow the number of decoy polygons and each permutation table while the
    # answer remains exactly k pairs.
    return {"n": 3 * current, "k": k}


def _inverse_table(table):
    inverse = [0] * len(table)
    for source, target in enumerate(table):
        inverse[target] = source
    return inverse


def _reference_solve(inst):
    """O(kn) orbit propagation; intentionally never called by generation."""
    n = inst["n"]
    k = inst["k"]
    # Build the inverse tables here rather than using the generator's cache:
    # the measured wall clock must include every step available to a solver.
    inverses = []
    operations = 0
    for table in inst["maps"]:
        inverse = [0] * n
        for source, target in enumerate(table):
            inverse[target] = source
            operations += 1
        inverses.append(inverse)
    values = [None] * k
    for cycle in inst["cycles"]:
        found = False
        for start in range(n):
            current = start
            values[cycle[0]] = start
            for edge in cycle[:-1]:
                current = inverses[edge][current]
                values[_cycle_links(k)[0][edge]] = current
                operations += 1
            operations += 1
            if current == inst["maps"][cycle[-1]][start]:
                found = True
                break
        if not found:
            return None, operations
    return [[i, values[i]] for i in range(k)], operations


def _egcd_inverse_counted(value, modulus):
    old_r, r = value, modulus
    old_s, s = 1, 0
    operations = 0
    while r:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_s, s = s, old_s - quotient * s
        operations += 5  # division, two multiplications, two subtractions
    if old_r != 1:
        raise ValueError("value has no inverse")
    return old_s % modulus, operations


def _compact_solve(inst):
    """Digit-reversal/affine route and an exact arithmetic operation count."""
    n = inst["n"]
    k = inst["k"]
    coefficients = []
    operations = 0
    one_label = _digit_reverse(1, n)
    for table in inst["maps"]:
        intercept = _digit_reverse(table[0], n)
        at_one = _digit_reverse(table[one_label], n)
        coefficients.append(((at_one - intercept) % n, intercept))
        operations += 1

    values = [None] * k
    for cycle in inst["cycles"]:
        # Compose the boundary maps around this cycle: H(x)=A*x+B.
        A, B = 1, 0
        for edge in reversed(cycle):
            slope, intercept = coefficients[edge]
            A, B = slope * A % n, (slope * B + intercept) % n
            operations += 3
        denominator = (1 - A) % n
        operations += 1
        if denominator == n - 1:
            inverse = n - 1
        else:
            inverse, inverse_operations = _egcd_inverse_counted(denominator, n)
            operations += inverse_operations
        start = B * inverse % n
        operations += 1

        values[cycle[0]] = start
        current = start
        for edge in reversed(cycle[1:]):
            slope, intercept = coefficients[edge]
            current = (slope * current + intercept) % n
            values[edge] = current
            operations += 2
    return [[i, _digit_reverse(values[i], n)] for i in range(k)], operations


def _attack_outlier_equal_size(inst):
    # Every polygon has exactly n+4 parabola vertices plus the apex, so the
    # usual smallest/largest-object outlier rule ties at residue zero.
    return [[i, 0] for i in range(inst["k"])]


def _attack_greedy_start_zero(inst):
    # Greedy covers the sole point left by the previous group, but its initial
    # tie is unresolved.  Taking zero propagates consistently until closure.
    values = _propagate_cycle_starts(inst, [0] * len(inst["cycles"]))
    return [[i, values[i]] for i in range(inst["k"])]


def _attack_arithmetic_ansatz(inst):
    return [[i, i % inst["n"]] for i in range(inst["k"])]


def _attack_raw_affine_first_difference(inst):
    """Fit affine maps directly to raw table entries, missing the relabelling."""
    n = inst["n"]
    coefficients = [((table[1] - table[0]) % n, table[0])
                    for table in inst["maps"]]
    values = [0] * inst["k"]
    for cycle in inst["cycles"]:
        slope_total, intercept_total = 1, 0
        for edge in reversed(cycle):
            slope, intercept = coefficients[edge]
            slope_total = slope * slope_total % n
            intercept_total = (slope * intercept_total + intercept) % n
        denominator = (1 - slope_total) % n
        divisor = math.gcd(denominator, n)
        if intercept_total % divisor:
            return _attack_arithmetic_ansatz(inst)
        reduced_modulus = n // divisor
        if reduced_modulus == 1:
            start = 0
        else:
            start = (
                (intercept_total // divisor)
                * pow(denominator // divisor, -1, reduced_modulus)
            ) % reduced_modulus
        values[cycle[0]] = start
        current = start
        for edge in reversed(cycle[1:]):
            slope, intercept = coefficients[edge]
            current = (slope * current + intercept) % n
            values[edge] = current
    return [[i, values[i]] for i in range(inst["k"])]


def _propagate_cycle_starts(inst, starts):
    """Enforce every cycle equation except the three closing equations."""
    inverses = inst["inverse_maps"]
    successor, _ = _cycle_links(inst["k"])
    values = [None] * inst["k"]
    for cycle, start in zip(inst["cycles"], starts):
        current = start
        values[cycle[0]] = current
        for edge in cycle[:-1]:
            current = inverses[edge][current]
            values[successor[edge]] = current
    return values


def _attack_random_propagated_starts(inst, rng, restarts=8):
    """Try random starts while enforcing every locally forced boundary choice.

    This is the structure-aware random-restart attack: unlike independent full
    tuples, every attempted candidate already satisfies the k-1 propagation
    equations that become free once a starting residue is chosen.
    """
    last_candidate = None
    for _ in range(restarts):
        starts = [rng.randrange(inst["n"]) for _ in inst["cycles"]]
        values = _propagate_cycle_starts(inst, starts)
        last_candidate = [[i, values[i]] for i in range(inst["k"])]
        if verify(inst, last_candidate)[0]:
            return last_candidate
    return last_candidate


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def _compose_coordinate_map(first, second):
    """Return second(first(point)) for two six-integer affine maps."""
    a, b, c, d, tx, ty = first
    e, f, g, h, ux, uy = second
    return [
        e * a + f * c,
        e * b + f * d,
        g * a + h * c,
        g * b + h * d,
        e * tx + f * ty + ux,
        g * tx + h * ty + uy,
    ]


def selftest():
    report = {}

    planted_attempts = 0
    json_attempts = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 7):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            if not ok:
                raise AssertionError(f"{preset}/{seed}: {why}")
            planted_attempts += 1
            if json.loads(json.dumps(inst["answer"])) != inst["answer"]:
                raise AssertionError("answer is not JSON-native")
            json_attempts += 1
    report["G1_planted_verifies"] = {
        "pass": True,
        "verified": planted_attempts,
        "json_roundtrips": json_attempts,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260421, **shipping)
    planted = [pair[:] for pair in inst["answer"]]
    corruptions = {}
    tests = {
        "drop_one": planted[:-1],
        "swap_one_value": [
            pair[:] if pair[0] else [0, (pair[1] + 1) % inst["n"]]
            for pair in planted
        ],
        "duplicate": [planted[0][:], planted[0][:]]
        + [pair[:] for pair in planted[2:]],
        "empty": [],
        "out_of_range": [[g, (inst["n"] if g == 0 else x)] for g, x in planted],
    }
    reasons = []
    for name, candidate in tests.items():
        ok, why = verify(inst, candidate)
        corruptions[name] = {"rejected": not ok, "reason": why}
        reasons.append(why)
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in corruptions.values())
        and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "cases": corruptions,
    }

    formatted = ", ".join(
        f"{i}:{_ternary_word(x, inst['n'])}_3" for i, x in inst["answer"]
    )
    response = (
        "I used the boundary incidences.\n```text\n"
        f"<answer> {formatted} </answer>\n```\nThat is the cover."
    )
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and verify(inst, parsed)[0],
        "parsed_pairs": len(parsed) if parsed is not None else 0,
    }

    guess_rng = random.Random(0x150405476)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        guess_hits += int(verify(inst, random_candidate(inst, guess_rng))[0])
    guess_fraction = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_fraction < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "fraction": guess_fraction,
        "structure_aware_space": search_space(inst),
        "prior": (
            "one uniform start per cycle, with all non-closing boundary "
            "equations propagated"
        ),
    }

    demo = make_instance(seed=11, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    start = time.perf_counter()
    reference_answer, reference_operations = _reference_solve(inst)
    reference_wall = time.perf_counter() - start
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1
        and guess_fraction < 1e-6
        and verify(inst, reference_answer)[0],
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "shipping_density_fraction": guess_fraction,
        "shipping_analytic_solution_count": 1,
        "demo_exact_solution_count": demo_count,
        "baseline_operations": reference_operations,
        "baseline_wall_seconds": round(reference_wall, 6),
    }

    attack_results = {
        "equal_vertex_count_outlier": {"successes": 0, "attempts": 0},
        "greedy_largest_gain_start_zero": {"successes": 0, "attempts": 0},
        "random_restart_propagated_8": {"successes": 0, "attempts": 0},
        "constant_or_index_ansatz": {"successes": 0, "attempts": 0},
        "raw_affine_first_difference": {"successes": 0, "attempts": 0},
    }
    reference_successes = 0
    reference_total_operations = 0
    reference_total_wall = 0.0
    for seed in range(8):
        trial = make_instance(seed=50_000 + seed, **shipping)
        candidates = {
            "equal_vertex_count_outlier": _attack_outlier_equal_size(trial),
            "greedy_largest_gain_start_zero": _attack_greedy_start_zero(trial),
            "constant_or_index_ansatz": _attack_arithmetic_ansatz(trial),
            "raw_affine_first_difference": _attack_raw_affine_first_difference(trial),
        }
        restart_rng = random.Random(0x150405 + seed)
        candidates["random_restart_propagated_8"] = (
            _attack_random_propagated_starts(trial, restart_rng, restarts=8)
        )
        for name, candidate in candidates.items():
            attack_results[name]["attempts"] += 1
            attack_results[name]["successes"] += int(verify(trial, candidate)[0])

        ref_start = time.perf_counter()
        ref_answer, ref_operations = _reference_solve(trial)
        reference_total_wall += time.perf_counter() - ref_start
        reference_total_operations += ref_operations
        reference_successes += int(verify(trial, ref_answer)[0])

    all_failed = all(value["successes"] == 0 for value in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "inverse-table orbit propagation",
            "complexity": "O(k*n) time and space",
            "wall_clock_sec": round(reference_total_wall / 8, 6),
            "operations": round(reference_total_operations / 8),
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    doubled_n = 3 * shipping["n"]
    doubled = make_instance(n=doubled_n, k=shipping["k"], seed=31337)
    report["G7_scales"] = {
        "pass": verify(doubled, doubled["answer"])[0]
        and search_space(doubled) > search_space(inst),
        "shipping_n": shipping["n"],
        "doubled_n": doubled_n,
        "answer_pairs_unchanged": len(doubled["answer"]) == len(inst["answer"]),
        "space_ratio_gt_one": search_space(doubled) // search_space(inst),
    }

    invariant_checks = 0
    carried_checks = 0
    unrelated_keys = set()
    extra_map = [2, 1, -1, 3, 17, -29]
    for seed in range(20):
        original = make_instance(seed=70_000 + seed, **shipping)
        unrelated_keys.add(canonical_key(original))
        base_key = canonical_key(original)
        variants = []
        reordered = dict(original)
        reordered["map_declaration_order"] = list(
            reversed(original["map_declaration_order"])
        )
        variants.append(reordered)
        transformed = dict(original)
        transformed["affine_transform"] = _compose_coordinate_map(
            original["affine_transform"], extra_map
        )
        variants.append(transformed)
        combined = dict(transformed)
        combined["map_declaration_order"] = reordered["map_declaration_order"]
        variants.append(combined)
        for variant in variants:
            invariant_checks += 1
            if canonical_key(variant) != base_key:
                raise AssertionError("canonical key changed under symmetry")
            carried_checks += int(verify(variant, original["answer"])[0])
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 60
        and carried_checks == 60
        and len(unrelated_keys) == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated": len(unrelated_keys),
        "unrelated_attempts": 20,
        "symmetries": [
            "permutation of labelled table declarations",
            "global invertible affine coordinate map",
            "composition of both",
        ],
    }

    compact_answer, compact_operations = _compact_solve(inst)
    # The profile promises a worst-case answer bound for the whole shipping
    # preset, not merely the length of this one sampled witness.
    widest_answer = [[i, inst["n"] - 1] for i in range(inst["k"])]
    answer_blob = json.dumps(widest_answer, separators=(",", ":"))
    answer_chars = len(answer_blob)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atoms(inst["answer"])
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    if arms["hinted"]["attempts"] and arms["placebo"]["attempts"]:
        hinted_minus_placebo = (
            arms["hinted"]["solved"] / arms["hinted"]["attempts"]
            - arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        )
    else:
        hinted_minus_placebo = None
    within_caps = (
        answer_chars <= 2000
        and answer_elements <= 256
        and compact_operations <= 300
    )
    report["G9_no_tool_suitability"] = {
        # The three oracle arms, including the hinted arm, are diagnostic as
        # of 2026-09-05.  Only the answer-size and intended-effort caps gate.
        "pass": within_caps and verify(inst, compact_answer)[0],
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact_operations,
        "intended_route_digit_reversals": 3 * inst["k"],
    }

    report["all_passed"] = all(
        value.get("pass", False)
        for key, value in report.items()
        if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
