"""Verified generator for quadratic correspondence colourings (arXiv:2003.14361).

Section 2.1 of the paper defines a q-fold correspondence cover H=(L,H) and
an H-colouring as an independent transversal of its lists.  This module uses
the exact q=2 object on regular bipartite base graphs.  It samples two quadratic
Boolean colour rules first, then builds every matching around their selected
local colours.  The certificate is therefore known by inverse generation.

The promise subclass is Track B.  A signed-graph breadth-first propagation
algorithm solves it in linear time in the displayed cover, while the intended
no-tool route reads the quadratic coefficients from a small anchor pattern.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import random
import re
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "regular bipartite graph",
        "2-fold correspondence cover",
        "quadratic Boolean H-colouring rule",
    ],
    "verification_operations": [
        "exact arithmetic in F_2",
        "quadratic Boolean evaluation",
        "matching-conflict comparison on every base edge",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The matching shifts are the edge coboundary of two quadratic Boolean "
        "colour rules; without recognizing that invariant one propagates "
        "colours through the entire displayed cover."
    ),
    "hardness_basis": (
        "Track B: signed-graph breadth-first propagation solves a satisfiable "
        "2-fold correspondence cover in O(|V|+|E|) time; on the hard preset "
        "the reference implementation measured 61,866 exact scan/XOR operations "
        "and 0.048558 s mean in the final hard-preset eight-seed audit, whereas the quadratic "
        "anchor invariant needs only 235 "
        "exact XORs and no propagation through the remaining cover."
    ),
    "max_answer_tokens": 51,
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
    "hard": {"n": 144, "dimension": 9, "degree": 142},
}
SHIPPING_DIFFICULTY = "hard"


STRUCTURAL_HINT = (
    "The matching-shift labels are an edge coboundary of degree-two Boolean "
    "functions on the displayed vertex codes."
)
PLACEBO_HINT = (
    "The matching-shift table benefits from patient comparison of labelled "
    "entries across the displayed vertex-code rows."
)


CERTIFICATE_LANGUAGE = {
    "description": (
        "One JSON object containing two multilinear Boolean polynomials of "
        "degree at most two, each listing its constant, linear, and pairwise "
        "quadratic coefficients in the stated order, all in {0,1}; the "
        "polynomials choose one local colour at every left and right vertex."
    ),
    "bounds": {
        "number_of_polynomials": 2,
        "degree": 2,
        "variables": "dimension",
        "coefficient_field": "F_2",
        "coefficients_per_polynomial": "1+dimension+binomial(dimension,2)",
        "candidate_count": "2^(2*(1+dimension+binomial(dimension,2)))",
    },
}


# Replaced after the three harness-owned oracle arms have completed.
G9_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "blocked_external",
}


NOTES = r"""
Paper grounding.  Section 2.1 fixes every relevant definition: a cover
H=(L,H), the matching condition between two lists, a q-fold cover, and an
H-colouring as an independent set of size |V(G)| in H.  The same subsection
notes the large gap between ordinary, list, and correspondence colouring even
for K_(d,d).  Theorem 12 is the paper's general existence theorem from local
occupancy, and Section 8.4 is the algorithmic warning that its sufficient
conditions do not automatically give randomized polynomial-time algorithms
for correspondence colouring (the situation is better for list colouring).

STEP 0 / track decision.  This module makes no Track-A claim.  In the q=2
promise subclass, avoiding a matching edge is an XOR equality, so ordinary
breadth-first propagation solves the cover in O(|V|+|E|).  That algorithm is
reported as the successful Track-B reference algorithm.  The rendered matrix
is the input representation, so a reference implementation also scans n^2
cells.  The compact route uses the coboundary invariant and the zero/unit/pair-
code anchor edges, requiring 2*d+6*binomial(d,2)+1 XORs; at the hard preset
this is 235 operations and it does not propagate through the remaining cover.

Certificate production.  Generation samples multilinear quadratic rules
f_L and f_R before the graph cover.  On every base edge
xy it sets the matching shift to f_L(x)+f_R(y)+1 in F_2.  The matching joins
(x,z) to (y,z+shift), so the sampled colours are never joined.  This is inverse
generation, not a solver run.  Verification independently evaluates any two
submitted quadratic rules and checks all displayed matching edges; it never reads
inst['answer'].

Attack hardening.  The base graph is degree-regular and every local cover
colour has exactly the same degree, removing degree and position signatures.
Each non-demo row and column omits one planted-zero and one planted-one vertex,
so marginal shift counts are exactly balanced while the dense base graph is
connected.  Dense linear and quadratic supports defeat constant,
affine-only, one-monomial, and left-first greedy ansatzes.  The row/column-bias outlier
probe discards the quadratic edge correlations, and random restart samples the
full bounded coefficient language.  The successful signed-BFS algorithm
remains outside attacks, as Track B requires.  Canonicalisation uses affine
difference multiplicities and graph colour refinement, and is audited under
independent affine changes of basis on both code spaces.
"""


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_GUESS_SAMPLES = 200_000


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_params(n, dimension, degree, seed):
    if not _is_int(n) or n < 2:
        raise ValueError("n must be an integer at least 2")
    if not _is_int(dimension) or dimension < 2:
        raise ValueError("dimension must be an integer at least 2")
    anchor_count = 1 + dimension + dimension * (dimension - 1) // 2
    if n <= anchor_count:
        raise ValueError("n must exceed the quadratic anchor count")
    if n > (1 << dimension):
        raise ValueError("n cannot exceed the number of Boolean codes")
    if not _is_int(degree) or degree not in (n - 2, n - 1):
        raise ValueError("degree must equal n-2, except that the demo may use n-1")
    if not _is_int(seed):
        raise ValueError("seed must be an integer")


def _code_string(value, dimension):
    """Coefficient-order bits: character h is the x_h coordinate."""
    return "".join("1" if (value >> h) & 1 else "0" for h in range(dimension))


def _basis_pairs(dimension):
    return [
        (first, second)
        for first in range(dimension)
        for second in range(first + 1, dimension)
    ]


def _basis_size(dimension):
    return 1 + dimension + dimension * (dimension - 1) // 2


def _anchor_values(dimension):
    values = [0]
    values.extend(1 << index for index in range(dimension))
    values.extend((1 << first) | (1 << second) for first, second in _basis_pairs(dimension))
    return values


def _dot(coefficients, code):
    """Evaluate a squarefree degree-at-most-two Boolean polynomial."""
    dimension = len(code)
    if len(coefficients) != _basis_size(dimension):
        raise ValueError("coefficient list has the wrong quadratic basis size")
    bits = [char == "1" for char in code]
    value = coefficients[0]
    for coefficient, bit in zip(coefficients[1:1 + dimension], bits):
        value ^= coefficient & bit
    offset = 1 + dimension
    for coefficient, (first, second) in zip(
        coefficients[offset:], _basis_pairs(dimension)
    ):
        value ^= coefficient & bits[first] & bits[second]
    return int(value)


def _xor_code(left, right):
    return "".join("1" if a != b else "0" for a, b in zip(left, right))


def _sample_codes(n, dimension, rng, rule):
    required = _anchor_values(dimension)
    chosen = set(required)
    target = n // 2
    pools = {0: [], 1: []}
    counts = {0: 0, 1: 0}
    for value in range(1 << dimension):
        colour = _evaluate_rule_value(rule, value, dimension)
        if value in chosen:
            counts[colour] += 1
        else:
            pools[colour].append(value)
    if counts[0] > target or counts[1] > target:
        raise ValueError("quadratic anchors cannot fit in a balanced code sample")
    for colour in (0, 1):
        chosen.update(rng.sample(pools[colour], target - counts[colour]))
    values = list(chosen)
    rng.shuffle(values)
    return [_code_string(value, dimension) for value in values]


def _sample_nontrivial_block(length, rng):
    if length <= 2:
        weight = 1
    else:
        weight = rng.randint(max(1, length // 3), min(length - 1, 2 * length // 3))
    support = set(rng.sample(range(length), weight))
    return [1 if index in support else 0 for index in range(length)]


def _sample_rule(dimension, rng):
    while True:
        rule = (
            [rng.randrange(2)]
            + _sample_nontrivial_block(dimension, rng)
            + _sample_nontrivial_block(len(_basis_pairs(dimension)), rng)
        )
        ones = sum(
            _evaluate_rule_value(rule, value, dimension)
            for value in range(1 << dimension)
        )
        if ones == 1 << (dimension - 1):
            return rule


def _anchor_indices(codes, dimension):
    wanted = [_code_string(value, dimension) for value in _anchor_values(dimension)]
    where = {code: index for index, code in enumerate(codes)}
    return [where[code] for code in wanted]


def _regular_bipartite_graph(
    left_codes, right_codes, left_colours, right_colours, degree, rng
):
    """A dense regular graph whose every row/column sees balanced colours."""
    n = len(left_codes)
    dimension = len(left_codes[0])
    left_anchor = _anchor_indices(left_codes, dimension)
    right_anchor = _anchor_indices(right_codes, dimension)
    anchor_count = _basis_size(dimension)
    protected = {(left_anchor[0], right_anchor[j]) for j in range(anchor_count)}
    protected.update((left_anchor[i], right_anchor[0]) for i in range(1, anchor_count))

    if degree == n - 1:
        # The eight-code demo has only one non-anchor on each side, so it uses
        # one omitted perfect matching rather than the balanced pair below.
        while True:
            missing = list(range(n))
            rng.shuffle(missing)
            if all((left, missing[left]) not in protected for left in range(n)):
                break
        missing_by_left = [{missing[left]} for left in range(n)]
    else:
        left_by_colour = {
            bit: [index for index, colour in enumerate(left_colours) if colour == bit]
            for bit in (0, 1)
        }
        right_by_colour = {
            bit: [index for index, colour in enumerate(right_colours) if colour == bit]
            for bit in (0, 1)
        }
        assert all(len(left_by_colour[bit]) == n // 2 for bit in (0, 1))
        assert all(len(right_by_colour[bit]) == n // 2 for bit in (0, 1))
        while True:
            first = [None] * n
            for bit in (0, 1):
                lefts = list(left_by_colour[bit])
                rights = list(right_by_colour[bit])
                rng.shuffle(lefts)
                rng.shuffle(rights)
                for left, right in zip(lefts, rights):
                    first[left] = right
            left_zero = list(left_by_colour[0])
            left_one = list(left_by_colour[1])
            rng.shuffle(left_zero)
            rng.shuffle(left_one)
            mate = {}
            for zero, one in zip(left_zero, left_one):
                mate[zero] = one
                mate[one] = zero
            second = [first[mate[left]] for left in range(n)]
            missing_by_left = [
                {first[left], second[left]} for left in range(n)
            ]
            if all(
                (left, right) not in protected
                for left in range(n)
                for right in missing_by_left[left]
            ):
                break
    adjacency = [set(range(n)) - missing_by_left[left] for left in range(n)]

    assert all(len(row) == degree for row in adjacency)
    column_degrees = [0] * n
    for row in adjacency:
        for right in row:
            column_degrees[right] += 1
    assert all(value == degree for value in column_degrees)
    assert all(right in adjacency[left] for left, right in protected)
    return adjacency


def make_instance(n, seed=0, **params):
    """Inverse-generate a satisfiable quadratic 2-fold correspondence cover."""
    dimension = params.pop("dimension", 9)
    degree = params.pop("degree", n - 2)
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, dimension, degree, seed)
    rng = random.Random(seed)

    # Sample the certificate before any instance constraint exists.
    left_rule = _sample_rule(dimension, rng)
    right_rule = _sample_rule(dimension, rng)
    left_codes = _sample_codes(n, dimension, rng, left_rule)
    right_codes = _sample_codes(n, dimension, rng, right_rule)
    left_colours = [_dot(left_rule, code) for code in left_codes]
    right_colours = [_dot(right_rule, code) for code in right_codes]
    adjacency = _regular_bipartite_graph(
        left_codes, right_codes, left_colours, right_colours, degree, rng
    )
    rows = []
    for left in range(n):
        chars = ["."] * n
        for right in adjacency[left]:
            chars[right] = str(left_colours[left] ^ right_colours[right] ^ 1)
        rows.append("".join(chars))

    answer = {"left": left_rule, "right": right_rule}
    return {
        "family": "quadratic_2fold_correspondence_colouring",
        "n": n,
        "dimension": dimension,
        "degree": degree,
        "left_codes": left_codes,
        "right_codes": right_codes,
        "matching_shifts": rows,
        "answer": answer,
    }


def _decode_answer(inst, answer):
    dimension = inst["dimension"]
    if not isinstance(answer, dict):
        return None, "answer must be a JSON object"
    if set(answer) != {"left", "right"}:
        return None, "answer must contain exactly the keys left and right"
    decoded = {}
    for side in ("left", "right"):
        value = answer[side]
        if not isinstance(value, list):
            return None, f"{side} quadratic rule must be a JSON list"
        expected = _basis_size(dimension)
        if len(value) < expected:
            return None, f"{side} quadratic rule is too short: expected {expected} coefficients"
        if len(value) > expected:
            return None, f"{side} quadratic rule is too long: expected {expected} coefficients"
        for index, bit in enumerate(value):
            if not _is_int(bit) or bit not in (0, 1):
                return None, f"{side} coefficient {index} is not a bit in {{0,1}}"
        decoded[side] = value
    return decoded, None


def verify(inst, answer):
    """Check any submitted quadratic H-colouring; never consult inst['answer']."""
    decoded, error = _decode_answer(inst, answer)
    if error:
        return False, error
    n = inst["n"]
    left_colours = [_dot(decoded["left"], code) for code in inst["left_codes"]]
    right_colours = [_dot(decoded["right"], code) for code in inst["right_codes"]]
    for left, row in enumerate(inst["matching_shifts"]):
        for right, char in enumerate(row):
            if char == ".":
                continue
            shift = ord(char) - ord("0")
            if right_colours[right] == (left_colours[left] ^ shift):
                return False, f"cover conflict on base edge L{left}-R{right}"
    return True, "ok"


def render(inst):
    """Render a complete, self-contained correspondence-colouring problem."""
    n = inst["n"]
    dimension = inst["dimension"]
    lines = [
        "Quadratic 2-fold correspondence colouring over F_2.",
        "",
        f"The base graph is bipartite with left vertices L0,...,L{n-1} and",
        f"right vertices R0,...,R{n-1}.  Each vertex has degree {inst['degree']}.",
        "Every vertex v has a two-element local list {(v,0),(v,1)}.",
        "The two elements inside one local list conflict with each other.",
        "",
        "For every base edge Li-Rj, the table entry s in {0,1} specifies the",
        "perfect matching of conflicts between their lists: (Li,z) conflicts",
        "with (Rj,z XOR s) for both z=0 and z=1.  A dot means Li-Rj is not",
        "a base edge and creates no cross-list conflict.  XOR is addition mod 2.",
        "",
        "An H-colouring chooses exactly one local-list element at every base",
        "vertex and contains no conflicting pair.  You must give such a colouring",
        "in the promised quadratic form below; at least one is guaranteed.",
        "",
        f"Each vertex carries a public code x=(x0,...,x{dimension-1}) in F_2^{dimension};",
        f"write d={dimension} for this code dimension.",
        "A coefficient list first gives the constant c, then the linear",
        "coefficients a0,...,a_(d-1), then one quadratic coefficient b_ij",
        "for every pair 0 <= i < j < d in lexicographic (i,j) order:",
        "  c XOR XOR_i(ai AND xi) XOR XOR_(i<j)(b_ij AND xi AND xj).",
        "Give one coefficient list for all left codes and one for all right codes.",
        "All coefficients must be literal integers 0 or 1 and may repeat.",
        "Vertex order is fixed by the indices below.",
        "",
        "Left codes (the first displayed bit is x0):",
    ]
    lines.extend(f"L{i}: {code}" for i, code in enumerate(inst["left_codes"]))
    lines.append("")
    lines.append("Right codes (the first displayed bit is x0):")
    lines.extend(f"R{i}: {code}" for i, code in enumerate(inst["right_codes"]))
    lines.extend([
        "",
        "Matching-shift table: row i is Li; character j is the entry for Rj.",
        "Columns are 0-indexed from left to right, with exactly n characters per row.",
    ])
    lines.extend(f"L{i}: {row}" for i, row in enumerate(inst["matching_shifts"]))
    zero = [0] * _basis_size(dimension)
    example = json.dumps({"left": zero, "right": zero}, separators=(",", ":"))
    lines.extend([
        "",
        "Output one JSON object with exactly the keys left and right.  Each value",
        f"must be a list of exactly {_basis_size(dimension)} bits: constant; x0,...,x{dimension-1};",
        "then x0*x1,x0*x2,...,x0*x_(d-1),x1*x2,... in lexicographic pair order.",
        "Give your final answer inside <answer></answer> tags, as that exact JSON object.",
        f"Example of the required syntax and shape: <answer>{example}</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text):
    """Extract the last tagged JSON object; return None on all malformed input."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    body = matches[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body)
    try:
        value = json.loads(body)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def random_candidate(inst, rng):
    """Uniform quadratic-rule candidate satisfying every stated shape constraint."""
    if not hasattr(rng, "getrandbits"):
        raise TypeError("rng must provide getrandbits")
    length = _basis_size(inst["dimension"])
    word = rng.getrandbits(2 * length)
    return {
        "left": [(word >> index) & 1 for index in range(length)],
        "right": [(word >> (length + index)) & 1 for index in range(length)],
    }


def search_space(inst):
    return 1 << (2 * _basis_size(inst["dimension"]))


def enumerate_all(inst):
    """Brute-force the bounded language only when it has at most 65,536 words."""
    space = search_space(inst)
    if space > 65_536:
        return None
    length = _basis_size(inst["dimension"])
    count = 0
    for word in range(space):
        left = [(word >> h) & 1 for h in range(length)]
        right = [(word >> (length + h)) & 1 for h in range(length)]
        count += verify(inst, {"left": left, "right": right})[0]
    return count


def _coefficients_from_anchor_values(values, dimension):
    """Interpolate an ANF quadratic from 0, unit, and pair-unit values."""
    constant = values[0]
    linear = [values[1 + index] ^ constant for index in range(dimension)]
    quadratic = []
    offset = 1 + dimension
    for pair_index, (first, second) in enumerate(_basis_pairs(dimension)):
        quadratic.append(
            values[offset + pair_index]
            ^ values[1 + first]
            ^ values[1 + second]
            ^ constant
        )
    return [constant] + linear + quadratic


def _anchor_signature(inst):
    """Both nonconstant quadratic parts and the relative constant."""
    dimension = inst["dimension"]
    left_anchor = _anchor_indices(inst["left_codes"], dimension)
    right_anchor = _anchor_indices(inst["right_codes"], dimension)
    rows = inst["matching_shifts"]
    s00 = int(rows[left_anchor[0]][right_anchor[0]])
    left_values = [int(rows[index][right_anchor[0]]) for index in left_anchor]
    right_values = [int(rows[left_anchor[0]][index]) for index in right_anchor]
    left_rule = _coefficients_from_anchor_values(left_values, dimension)
    right_rule = _coefficients_from_anchor_values(right_values, dimension)
    return s00, left_rule[1:], right_rule[1:]


def _anchor_filter(inst, answer, signature=None):
    """Cheap exact rejection on the guaranteed anchor edges, then full verify."""
    decoded, error = _decode_answer(inst, answer)
    if error:
        return False
    s00, left_nonconstant, right_nonconstant = signature or _anchor_signature(inst)
    if (
        decoded["left"][1:] != left_nonconstant
        or decoded["right"][1:] != right_nonconstant
    ):
        return False
    if decoded["right"][0] != (decoded["left"][0] ^ s00 ^ 1):
        return False
    return verify(inst, answer)[0]


def _code_value(code):
    value = 0
    for index, char in enumerate(code):
        value |= (char == "1") << index
    return value


def _affine_code_profiles(codes):
    """Per-vertex profiles invariant under every affine change of basis.

    For a code set S and nonzero difference d, let m(d) be the number of
    unordered pairs in S at XOR difference d.  An invertible affine map merely
    permutes the nonzero differences.  The profile of x is the multiset of
    m(x XOR y) over y != x; it is therefore invariant without collapsing the
    association between code geometry and base-graph vertices.
    """
    values = [_code_value(code) for code in codes]
    multiplicity = {}
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            difference = values[i] ^ values[j]
            multiplicity[difference] = multiplicity.get(difference, 0) + 1
    profiles = [
        tuple(sorted(multiplicity[value ^ other] for other in values if other != value))
        for value in values
    ]
    dimension = len(codes[0])
    count_histogram = {}
    for count in multiplicity.values():
        count_histogram[count] = count_histogram.get(count, 0) + 1
    count_histogram[0] = (1 << dimension) - 1 - len(multiplicity)
    spectrum = tuple(sorted(count_histogram.items()))
    return profiles, spectrum


def canonical_key(inst):
    """Strong cheap invariant under vertex, side, frame, and affine relabelling.

    The shift bits are omitted deliberately: every generated shift assignment
    is a coboundary, and affine swaps of the two colours in local lists gauge
    all generated assignments to the same all-zero XOR system.  Code profiles
    use only affine-dependence multiplicities.  Deterministic colour refinement
    then couples those profiles to the unlabelled bipartite base graph.
    """
    n = inst["n"]
    left_profiles, left_spectrum = _affine_code_profiles(inst["left_codes"])
    right_profiles, right_spectrum = _affine_code_profiles(inst["right_codes"])
    adjacency = [[] for _ in range(2 * n)]
    for left, row in enumerate(inst["matching_shifts"]):
        for right, char in enumerate(row):
            if char != ".":
                adjacency[left].append(n + right)
                adjacency[n + right].append(left)

    signatures = left_profiles + right_profiles
    colour_map = {value: index for index, value in enumerate(sorted(set(signatures)))}
    colours = [colour_map[value] for value in signatures]
    rounds = []
    for _ in range(8):
        side_colours = sorted([sorted(colours[:n]), sorted(colours[n:])])
        rounds.append(side_colours)
        signatures = [
            (colours[vertex], tuple(sorted(colours[other] for other in adjacency[vertex])))
            for vertex in range(2 * n)
        ]
        ordered = sorted(set(signatures))
        colour_map = {value: index for index, value in enumerate(ordered)}
        refined = [colour_map[value] for value in signatures]
        if refined == colours:
            break
        colours = refined

    payload = json.dumps(
        [
            n,
            inst["dimension"],
            inst["degree"],
            sorted([left_spectrum, right_spectrum]),
            rounds,
        ],
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params):
    """Crowd a larger regular cover while the quadratic certificate stays fixed."""
    current = dict(params)
    current.pop("_preset", None)
    n = current["n"]
    dimension = current.get("dimension", 9)
    if n >= min(768, 1 << dimension):
        return None
    harder_n = min(min(768, 1 << dimension), max(n + 32, math.ceil(4 * n / 3)))
    current["n"] = harder_n
    current["degree"] = harder_n - 2
    return current


def _reference_signed_bfs(inst):
    """Domain-standard propagation, including the cost of scanning the table."""
    n = inst["n"]
    adjacency = [[] for _ in range(2 * n)]
    scans = 0
    edges = 0
    for left, row in enumerate(inst["matching_shifts"]):
        for right, char in enumerate(row):
            scans += 1
            if char == ".":
                continue
            relation = int(char) ^ 1  # colour_R = colour_L XOR relation
            adjacency[left].append((n + right, relation))
            adjacency[n + right].append((left, relation))
            edges += 1

    colours = [None] * (2 * n)
    xor_operations = 0
    components = 0
    for start in range(2 * n):
        if colours[start] is not None:
            continue
        components += 1
        colours[start] = 0
        queue = [start]
        cursor = 0
        while cursor < len(queue):
            vertex = queue[cursor]
            cursor += 1
            for neighbour, relation in adjacency[vertex]:
                expected = colours[vertex] ^ relation
                xor_operations += 1
                if colours[neighbour] is None:
                    colours[neighbour] = expected
                    queue.append(neighbour)
                elif colours[neighbour] != expected:
                    return None, {
                        "table_cells_scanned": scans,
                        "edges": edges,
                        "xor_operations": xor_operations,
                        "components": components,
                    }

    dimension = inst["dimension"]
    left_anchor = _anchor_indices(inst["left_codes"], dimension)
    right_anchor = _anchor_indices(inst["right_codes"], dimension)
    left_values = [colours[index] for index in left_anchor]
    right_values = [colours[n + index] for index in right_anchor]
    left = _coefficients_from_anchor_values(left_values, dimension)
    right = _coefficients_from_anchor_values(right_values, dimension)
    xor_operations += 2 * (
        dimension + 3 * len(_basis_pairs(dimension))
    )
    result = {"left": left, "right": right}
    stats = {
        "table_cells_scanned": scans,
        "edges": edges,
        "xor_operations": xor_operations,
        "components": components,
        "operations": scans + xor_operations,
    }
    return result, stats


def _attack_constant(inst):
    dimension = inst["dimension"]
    length = _basis_size(dimension)
    signature = _anchor_signature(inst)
    for left_constant in (0, 1):
        for right_constant in (0, 1):
            candidate = {
                "left": [left_constant] + [0] * (length - 1),
                "right": [right_constant] + [0] * (length - 1),
            }
            if _anchor_filter(inst, candidate, signature):
                return candidate
    return None


def _attack_greedy_left_first(inst):
    """Set every left colour to zero and greedily minimize right conflicts."""
    n = inst["n"]
    dimension = inst["dimension"]
    right_colours = [0] * n
    for right in range(n):
        conflicts = [0, 0]
        for left, row in enumerate(inst["matching_shifts"]):
            char = row[right]
            if char != ".":
                conflicts[int(char)] += 1
        right_colours[right] = 0 if conflicts[0] <= conflicts[1] else 1
    right_anchor = _anchor_indices(inst["right_codes"], dimension)
    right = _coefficients_from_anchor_values(
        [right_colours[index] for index in right_anchor], dimension
    )
    candidate = {"left": [0] * _basis_size(dimension), "right": right}
    return candidate if _anchor_filter(inst, candidate, _anchor_signature(inst)) else None


def _attack_marginal_majority(inst):
    """Fit anchor coefficients from per-row/column majority shift labels."""
    n = inst["n"]
    dimension = inst["dimension"]
    row_vote = []
    for row in inst["matching_shifts"]:
        bits = [int(char) for char in row if char != "."]
        row_vote.append(int(sum(bits) * 2 >= len(bits)))
    column_vote = []
    for right in range(n):
        bits = [int(inst["matching_shifts"][left][right]) for left in range(n)
                if inst["matching_shifts"][left][right] != "."]
        column_vote.append(int(sum(bits) * 2 >= len(bits)))
    left_anchor = _anchor_indices(inst["left_codes"], dimension)
    right_anchor = _anchor_indices(inst["right_codes"], dimension)
    left = _coefficients_from_anchor_values(
        [row_vote[index] for index in left_anchor], dimension
    )
    right = _coefficients_from_anchor_values(
        [column_vote[index] for index in right_anchor], dimension
    )
    candidate = {
        "left": left,
        "right": right,
    }
    return candidate if _anchor_filter(inst, candidate, _anchor_signature(inst)) else None


def _attack_single_monomial(inst):
    dimension = inst["dimension"]
    length = _basis_size(dimension)
    signature = _anchor_signature(inst)
    nonconstant = [[0] * (length - 1)]
    for index in range(length - 1):
        term = [0] * (length - 1)
        term[index] = 1
        nonconstant.append(term)
    for left_terms in nonconstant:
        for right_terms in nonconstant:
            for lc in (0, 1):
                for rc in (0, 1):
                    candidate = {
                        "left": [lc] + left_terms,
                        "right": [rc] + right_terms,
                    }
                    if _anchor_filter(inst, candidate, signature):
                        return candidate
    return None


def _attack_affine_only(inst):
    """Use the exact affine part exposed at zero/unit codes, ignoring pairs."""
    dimension = inst["dimension"]
    s00, left_terms, right_terms = _anchor_signature(inst)
    n_quadratic = len(_basis_pairs(dimension))
    candidate = {
        "left": [0] + left_terms[:dimension] + [0] * n_quadratic,
        "right": [s00 ^ 1] + right_terms[:dimension] + [0] * n_quadratic,
    }
    return candidate if _anchor_filter(inst, candidate, (s00, left_terms, right_terms)) else None


def _attack_random_restart(inst, rng, restarts=256):
    signature = _anchor_signature(inst)
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if _anchor_filter(inst, candidate, signature):
            return candidate
    return None


def _reorder_instance(inst, left_order, right_order):
    out = copy.deepcopy(inst)
    out["left_codes"] = [inst["left_codes"][i] for i in left_order]
    out["right_codes"] = [inst["right_codes"][j] for j in right_order]
    out["matching_shifts"] = [
        "".join(inst["matching_shifts"][i][j] for j in right_order)
        for i in left_order
    ]
    return out


def _rule_from_function(dimension, function):
    values = [function(value) for value in _anchor_values(dimension)]
    return _coefficients_from_anchor_values(values, dimension)


def _evaluate_rule_value(rule, value, dimension):
    return _dot(rule, _code_string(value, dimension))


def _carry_rule(rule, dimension, preimage):
    return _rule_from_function(
        dimension,
        lambda new_value: _evaluate_rule_value(
            rule, preimage(new_value), dimension
        ),
    )


def _permute_coordinates(inst, order, answer, right_order=None):
    right_order = order if right_order is None else right_order
    out = copy.deepcopy(inst)
    out["left_codes"] = ["".join(code[h] for h in order) for code in inst["left_codes"]]
    out["right_codes"] = [
        "".join(code[h] for h in right_order) for code in inst["right_codes"]
    ]
    dimension = inst["dimension"]

    def inverse(permutation):
        def apply(new_value):
            old_value = 0
            for new_index, old_index in enumerate(permutation):
                if (new_value >> new_index) & 1:
                    old_value |= 1 << old_index
            return old_value
        return apply

    carried = {
        "left": _carry_rule(answer["left"], dimension, inverse(order)),
        "right": _carry_rule(answer["right"], dimension, inverse(right_order)),
    }
    return out, carried


def _translate_coordinates(inst, translation, answer, right_translation=None):
    right_translation = translation if right_translation is None else right_translation
    out = copy.deepcopy(inst)
    out["left_codes"] = [_xor_code(code, translation) for code in inst["left_codes"]]
    out["right_codes"] = [
        _xor_code(code, right_translation) for code in inst["right_codes"]
    ]
    dimension = inst["dimension"]
    carried = {}
    for side, offset in (("left", translation), ("right", right_translation)):
        offset_value = _code_value(offset)
        carried[side] = _carry_rule(
            answer[side], dimension, lambda value, delta=offset_value: value ^ delta
        )
    return out, carried


def _shear_coordinates(inst, side, target, source, answer):
    """Apply y_target=x_target XOR x_source on one side and carry the rule."""
    out = copy.deepcopy(inst)
    key = side + "_codes"
    recoded = []
    for code in inst[key]:
        chars = list(code)
        chars[target] = str(int(chars[target]) ^ int(chars[source]))
        recoded.append("".join(chars))
    out[key] = recoded
    dimension = inst["dimension"]
    carried = copy.deepcopy(answer)

    def preimage(value):
        return value ^ (((value >> source) & 1) << target)

    carried[side] = _carry_rule(answer[side], dimension, preimage)
    return out, carried


def _swap_sides(inst, answer):
    out = copy.deepcopy(inst)
    n = inst["n"]
    out["left_codes"], out["right_codes"] = out["right_codes"], out["left_codes"]
    out["matching_shifts"] = [
        "".join(inst["matching_shifts"][left][right] for left in range(n))
        for right in range(n)
    ]
    return out, {"left": list(answer["right"]), "right": list(answer["left"])}


def _change_local_frames(inst, left_mask, right_mask, answer):
    out = copy.deepcopy(inst)
    rows = []
    for left, row in enumerate(inst["matching_shifts"]):
        lflip = _dot(left_mask, inst["left_codes"][left])
        chars = []
        for right, char in enumerate(row):
            if char == ".":
                chars.append(char)
            else:
                rflip = _dot(right_mask, inst["right_codes"][right])
                chars.append(str(int(char) ^ lflip ^ rflip))
        rows.append("".join(chars))
    out["matching_shifts"] = rows
    carried = {
        "left": [a ^ b for a, b in zip(answer["left"], left_mask)],
        "right": [a ^ b for a, b in zip(answer["right"], right_mask)],
    }
    return out, carried


def _answer_atoms(value):
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def selftest():
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    # G1: every named preset across several independent seeds.
    failures = []
    json_roundtrips = 0
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 29):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            checks += 1
            if not ok:
                failures.append({"preset": preset, "seed": seed, "reason": reason})
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not failures and json_roundtrips == checks,
        "checks": checks,
        "json_native_roundtrips": json_roundtrips,
        "failures": failures,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=511, **shipping_params)
    answer = copy.deepcopy(inst["answer"])
    left_one = next(index for index, bit in enumerate(answer["left"][1:], 1) if bit == 1)
    left_zero = next(index for index, bit in enumerate(answer["left"][1:], 1) if bit == 0)
    swapped_left = list(answer["left"])
    swapped_left[left_one], swapped_left[left_zero] = (
        swapped_left[left_zero],
        swapped_left[left_one],
    )
    corruptions = {
        "drop_one": {"left": answer["left"][:-1], "right": answer["right"]},
        "duplicate_one": {"left": answer["left"] + [answer["left"][-1]], "right": answer["right"]},
        "empty": None,
        "out_of_range": {"left": [2] + answer["left"][1:], "right": answer["right"]},
        "swap_one": {"left": swapped_left, "right": answer["right"]},
    }
    cases = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": all(case["rejected"] for case in cases.values()) and len(set(reasons)) == len(reasons),
        "distinct_reasons": len(set(reasons)),
        "cases": cases,
    }

    realistic = (
        "I used the matching constraints and obtained:\n```json\n<answer>"
        + json.dumps(inst["answer"])
        + "</answer>\n```\nThe lists are in left/right order."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == inst["answer"] and parse_answer("no tagged answer") is None,
        "parsed_equals_answer": parsed == inst["answer"],
        "garbage_returns_none": parse_answer("no tagged answer") is None,
    }

    # G4/G5 shipping density.  The anchor filter is an exact necessary test;
    # only its extremely rare survivors pay for a full verification.
    rng = random.Random(0x200314361)
    hits = 0
    anchor_signature = _anchor_signature(inst)
    started = time.perf_counter()
    for _ in range(_GUESS_SAMPLES):
        hits += _anchor_filter(inst, random_candidate(inst, rng), anchor_signature)
    guess_seconds = time.perf_counter() - started
    space = search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": hits / _GUESS_SAMPLES < 1e-6,
        "hits": hits,
        "total": _GUESS_SAMPLES,
        "observed_probability": hits / _GUESS_SAMPLES,
        "exact_probability": 2 / space,
        "search_space": space,
        "prior": "uniform pairs of correctly shaped quadratic Boolean rules",
        "sampling_seconds": round(guess_seconds, 6),
    }

    baseline_records = []
    for seed in range(8):
        audit_inst = make_instance(seed=9_000 + seed, **shipping_params)
        started = time.perf_counter()
        candidate, stats = _reference_signed_bfs(audit_inst)
        elapsed = time.perf_counter() - started
        solved = candidate is not None and verify(audit_inst, candidate)[0]
        baseline_records.append((solved, elapsed, stats))
    demo_inst = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo_inst)
    mean_wall = sum(item[1] for item in baseline_records) / len(baseline_records)
    mean_ops = sum(item[2].get("operations", 0) for item in baseline_records) / len(baseline_records)
    report["G5_density_and_baseline"] = {
        "pass": (
            demo_count is not None
            and all(item[0] for item in baseline_records)
            and all(item[2].get("components") == 1 for item in baseline_records)
        ),
        "shipping_density_hits": hits,
        "shipping_density_samples": _GUESS_SAMPLES,
        "shipping_solution_fraction_estimate": hits / _GUESS_SAMPLES,
        "shipping_exact_valid_answer_count": 2,
        "shipping_exact_solution_fraction": 2 / space,
        "demo_exact_valid_answer_count": demo_count,
        "baseline_solved": sum(item[0] for item in baseline_records),
        "baseline_attempts": len(baseline_records),
        "baseline_wall_seconds_mean": round(mean_wall, 6),
        "baseline_wall_seconds_max": round(max(item[1] for item in baseline_records), 6),
        "baseline_operations_mean": mean_ops,
        "baseline_table_cells_scanned": shipping_params["n"] ** 2,
        "baseline_connected_components": [item[2]["components"] for item in baseline_records],
    }

    attack_functions = {
        "constant_rule_ansatz": lambda x, r: _attack_constant(x),
        "greedy_left_first": lambda x, r: _attack_greedy_left_first(x),
        "outlier_row_column_bias": lambda x, r: _attack_marginal_majority(x),
        "single_monomial_ansatz": lambda x, r: _attack_single_monomial(x),
        "affine_only_anchor_fit": lambda x, r: _attack_affine_only(x),
        "random_restart_256": lambda x, r: _attack_random_restart(x, r, 256),
    }
    attack_results = {name: {"successes": 0, "attempts": 8} for name in attack_functions}
    reference_successes = 0
    reference_walls = []
    reference_operations = []
    for seed in range(8):
        audit_inst = make_instance(seed=17_000 + seed, **shipping_params)
        for name, attack in attack_functions.items():
            candidate = attack(audit_inst, random.Random(44_000 + seed))
            if candidate is not None and verify(audit_inst, candidate)[0]:
                attack_results[name]["successes"] += 1
        started = time.perf_counter()
        candidate, stats = _reference_signed_bfs(audit_inst)
        reference_walls.append(time.perf_counter() - started)
        reference_operations.append(stats.get("operations", 0))
        reference_successes += candidate is not None and verify(audit_inst, candidate)[0]
    all_failed = all(value["successes"] == 0 for value in attack_results.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == 8,
        "attacks": attack_results,
        "reference_algorithm": {
            "name": "signed-graph breadth-first propagation with quadratic readout",
            "complexity": "O(n^2 + |E|) for the displayed n-by-n table",
            "wall_clock_sec": round(sum(reference_walls) / len(reference_walls), 6),
            "operations": round(sum(reference_operations) / len(reference_operations)),
            "connected_components": 1,
            "solves": f"{reference_successes}/8, as expected",
        },
    }

    harder = escalate(shipping_params)
    doubled_n = min(2 * shipping_params["n"], 1 << shipping_params["dimension"])
    doubled_degree = doubled_n - 2
    started = time.perf_counter()
    doubled = make_instance(
        n=doubled_n,
        dimension=shipping_params["dimension"],
        degree=doubled_degree,
        seed=707,
    )
    doubled_build = time.perf_counter() - started
    doubled_ok = verify(doubled, doubled["answer"])[0]
    escalated = make_instance(seed=708, **harder) if isinstance(harder, dict) else None
    report["G7_scales"] = {
        "pass": doubled_ok and escalated is not None and verify(escalated, escalated["answer"])[0],
        "shipping_n": shipping_params["n"],
        "doubled_n": doubled_n,
        "doubled_build_seconds": round(doubled_build, 6),
        "answer_atoms_before": _answer_atoms(inst["answer"]),
        "answer_atoms_after": _answer_atoms(doubled["answer"]),
        "fixed_answer_escalation": harder,
    }

    # G8: vertex reorder, independent affine coordinate changes, side swap,
    # affine local colour frames, and a composition, on twenty unrelated seeds.
    invariance_checks = 0
    carried_checks = 0
    key_failures = []
    unrelated_keys = []
    deterministic_rebuilds = 0
    for seed in range(20):
        base = make_instance(seed=31_000 + seed, **shipping_params)
        rebuilt = make_instance(seed=31_000 + seed, **shipping_params)
        if rebuilt == base:
            deterministic_rebuilds += 1
        else:
            key_failures.append({"seed": seed, "transformation": "rebuild", "kind": "determinism"})
        base_answer = base["answer"]
        base_key = canonical_key(base)
        unrelated_keys.append(base_key)
        trng = random.Random(81_000 + seed)

        left_order = list(range(base["n"]))
        right_order = list(range(base["n"]))
        trng.shuffle(left_order)
        trng.shuffle(right_order)
        transformed = _reorder_instance(base, left_order, right_order)
        candidates = [("vertex_reorder", transformed, copy.deepcopy(base_answer))]

        left_coordinate_order = list(range(base["dimension"]))
        right_coordinate_order = list(range(base["dimension"]))
        trng.shuffle(left_coordinate_order)
        trng.shuffle(right_coordinate_order)
        transformed2, carried2 = _permute_coordinates(
            base, left_coordinate_order, base_answer, right_coordinate_order
        )
        candidates.append(("independent_coordinate_permutations", transformed2, carried2))

        left_translation = "".join(
            str(trng.randrange(2)) for _ in range(base["dimension"])
        )
        right_translation = "".join(
            str(trng.randrange(2)) for _ in range(base["dimension"])
        )
        transformed3, carried3 = _translate_coordinates(
            base, left_translation, base_answer, right_translation
        )
        candidates.append(("independent_code_translations", transformed3, carried3))

        left_target, left_source = trng.sample(range(base["dimension"]), 2)
        right_target, right_source = trng.sample(range(base["dimension"]), 2)
        transformed_shear, carried_shear = _shear_coordinates(
            base, "left", left_target, left_source, base_answer
        )
        transformed_shear, carried_shear = _shear_coordinates(
            transformed_shear, "right", right_target, right_source, carried_shear
        )
        candidates.append(("independent_basis_shears", transformed_shear, carried_shear))

        transformed4, carried4 = _swap_sides(base, base_answer)
        candidates.append(("side_swap", transformed4, carried4))

        left_mask = [trng.randrange(2) for _ in range(_basis_size(base["dimension"]))]
        right_mask = [trng.randrange(2) for _ in range(_basis_size(base["dimension"]))]
        transformed5, carried5 = _change_local_frames(base, left_mask, right_mask, base_answer)
        candidates.append(("affine_local_frames", transformed5, carried5))

        composed = _reorder_instance(base, left_order, right_order)
        composed_answer = copy.deepcopy(base_answer)
        composed, composed_answer = _permute_coordinates(
            composed,
            left_coordinate_order,
            composed_answer,
            right_coordinate_order,
        )
        composed, composed_answer = _translate_coordinates(
            composed, left_translation, composed_answer, right_translation
        )
        composed, composed_answer = _shear_coordinates(
            composed, "left", left_target, left_source, composed_answer
        )
        composed, composed_answer = _shear_coordinates(
            composed, "right", right_target, right_source, composed_answer
        )
        composed, composed_answer = _swap_sides(composed, composed_answer)
        composed, composed_answer = _change_local_frames(
            composed, left_mask, right_mask, composed_answer
        )
        candidates.append(("all_composed", composed, composed_answer))

        for name, transformed_inst, carried in candidates:
            invariance_checks += 1
            if canonical_key(transformed_inst) != base_key:
                key_failures.append({"seed": seed, "transformation": name, "kind": "key"})
            carried_checks += 1
            if not verify(transformed_inst, carried)[0]:
                key_failures.append({"seed": seed, "transformation": name, "kind": "witness"})
    distinct = len(set(unrelated_keys))
    report["G8_canonical_key"] = {
        "pass": not key_failures and distinct == 20,
        "invariance_checks": invariance_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "unrelated_distinct_keys": distinct,
        "deterministic_rebuilds": deterministic_rebuilds,
        "transformations": [
            "independent left/right vertex reorder",
            "independent coordinate permutations",
            "independent code translations",
            "independent invertible basis shears",
            "left/right side swap",
            "independent affine local-colour frames",
            "composition of all six transformation classes",
        ],
        "invariant": (
            "affine code-difference multiplicities coupled to the unlabelled "
            "base graph by deterministic colour refinement"
        ),
        "failures": key_failures,
    }

    answer_blob = json.dumps(inst["answer"], separators=(",", ":"))
    arms = {
        key: {"solved": value["solved"], "attempts": value["attempts"]}
        for key, value in G9_RESULTS.items()
        if key in ("bare", "hinted", "placebo")
    }
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    difference = None
    if hinted["attempts"] and placebo["attempts"]:
        difference = (
            hinted["solved"] / hinted["attempts"]
            - placebo["solved"] / placebo["attempts"]
        )
    answer_chars = len(answer_blob)
    answer_elements = _answer_atoms(inst["answer"])
    intended_operations = (
        2 * inst["dimension"]
        + 6 * len(_basis_pairs(inst["dimension"]))
        + 1
    )
    caps_pass = answer_chars <= 2_000 and answer_elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": caps_pass,
        "arms": arms,
        "hinted_minus_placebo": difference,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": math.ceil(answer_chars / 4),
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2_000, "elements": 256, "operations": 300},
    }

    gate_values = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(value.get("pass") for value in gate_values)
    report["shipping_params"] = dict(shipping_params)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
