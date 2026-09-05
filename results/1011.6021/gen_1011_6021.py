"""Verified problem generator derived from arXiv:1011.6021.

The paper reduces bounded-occurrence 3,4-SAT to Border Basis Detection (BBD).
This module inverse-generates a satisfying assignment as the graph of a compact
triangular quadratic permutation over F_2, carries it through that reduction,
and asks for the compact polynomial-map certificate.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import os
import random
import re
import statistics
import sys
import time


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals
except ImportError:  # The construction below remains standard-library-only.
    exact_matrices = rationals = None


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "The bitwise XOR of the three targets in every row is a triangular "
    "quadratic permutation of the source bits."
)
PLACEBO_HINT: str = (
    "The binary labels and coefficient blocks reward careful attention to bit "
    "order and the stated indexing conventions."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "csp_sat",
    "certificate_form": "polynomial",
    "native_objects": [
        "schematically specified sparse polynomials over Q from the paper's Border Basis Detection reduction",
        "triangular quadratic polynomial map over GF(2)",
        "3-regular bipartite incidence table",
        "bounded-occurrence 3,4-SAT incidence system",
    ],
    "verification_operations": [
        "exact GF(2) polynomial evaluation",
        "bitwise XOR",
        "Boolean clause substitution",
        "deterministic decoding of the succinct witness to the paper's border-term set",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3, Theorems 3.12-3.13 (Reduction and Correctness of reduction): "
        "3,4-SAT is mapped to Border Basis Detection"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "Notice that the rowwise XOR of three unordered target values cancels "
        "the three masks and exposes one quadratic permutation; without this "
        "invariant a solver faces list recovery among three choices per row."
    ),
    "hardness_basis": (
        "Track B: exact quadratic list recovery by rowwise XOR, Boolean "
        "interpolation, and exhaustive validation is O(N (log N)^3); at the "
        "shipping preset N=1024 it performs 474258 counted exact primitives "
        "with a measured median wall-clock time of 0.012734 seconds, whereas "
        "the selected-row route uses "
        "258 exact GF(2)^10 additions and is still too long to execute casually "
        "without tools."
    ),
    "max_answer_tokens": 110,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": "
    + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY: dict = {
    "demo": {"n": 8},
    "easy": {"n": 256},
    "medium": {"n": 512},
    "hard": {"n": 1024},
}
SHIPPING_DIFFICULTY: str = "hard"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A labeled coefficient tensor for d triangular quadratic Boolean "
        "polynomials. Output bit i equals input bit i plus a constant, all "
        "earlier linear monomials, and all products x_j*x_k with j<k<i. "
        "Every displayed coefficient is 0 or 1, and the constant vector is "
        "one of the three targets displayed in source row zero."
    ),
    "bounds": {
        "field": "GF(2)",
        "degree": 2,
        "triangular": True,
        "max_input_bits": 12,
        "max_free_coefficients": 298,
        "shipping_input_bits": 10,
        "shipping_free_coefficients": 175,
        "instance_conditioned_constant_choices": 3,
        "coefficient_values": 2,
    },
}

NOTES: str = (
    "Section 2 and Theorem 2.1 fix order ideals, borders, border prebases, and "
    "the border-basis Buchberger criterion. Theorems 3.9 and 3.11 give three "
    "executable necessary-and-sufficient conditions for a monomial set to be a "
    "border and a polynomial verifier; they do not produce a border. "
    "The Reduction and Correctness subsections require exactly three variables "
    "per clause, at most four total occurrences per Boolean variable, both signs, "
    "and no complementary pair in a clause. The bipartite construction here has "
    "one positive and one negative clause at each endpoint, so every edge variable "
    "has exactly four occurrences, two of each sign. A satisfying matching is "
    "sampled before the formula, and Theorems 3.12-3.13 carry it to a border. "
    "This is Track B, not Track A: rowwise XOR and quadratic interpolation are a "
    "polynomial-time recovery algorithm. The masks are sampled symmetrically and "
    "sum to zero, so all three polynomial matchings are valid and none is a "
    "distinguished plant. Minimum-target, rank-greedy, bipartite-matching-and-fit, "
    "random-certificate, and unshifted-center attacks are tested explicitly. The "
    "returned polynomial is a succinct selector for the proof's border-term set, "
    "not a replacement for the BBD certificate: verify expands its selected "
    "matching and checks every clause before the forced singleton border terms "
    "are decoded."
)


G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "hardened",
    "evidence_status": (
        "bare, hinted, and placebo transcripts are fresh at the shipping "
        "preset; each shipping arm held 0/3"
    ),
}

_SECTION_LABELS = ("constant", "linear", "quadratic")
_ENUMERATION_CAP = 100_000


# ---------------------------------------------------------------------------
# Coefficient language and exact Boolean-polynomial arithmetic.


def _dimension(point_count):
    if isinstance(point_count, bool) or not isinstance(point_count, int):
        raise TypeError("n must be an integer power of two")
    if point_count < 8 or point_count & (point_count - 1):
        raise ValueError("n must be a power of two and at least 8")
    d = point_count.bit_length() - 1
    if d > 12:
        raise ValueError("n is too large for the bounded certificate language")
    return d


def _free_coefficients(d):
    return d + math.comb(d, 2) + math.comb(d, 3)


def _blank_coefficients(d):
    return [
        ["constant", [0] * d],
        ["linear", [[0] * i for i in range(d)]],
        ["quadratic", [[0] * math.comb(i, 2) for i in range(d)]],
    ]


def _random_coefficients(d, rng):
    answer = _blank_coefficients(d)
    answer[0][1] = [rng.randrange(2) for _ in range(d)]
    answer[1][1] = [[rng.randrange(2) for _ in range(i)] for i in range(d)]
    answer[2][1] = [
        [rng.randrange(2) for _ in range(math.comb(i, 2))]
        for i in range(d)
    ]
    return answer


def _sections(answer):
    return answer[0][1], answer[1][1], answer[2][1]


def _validate_shape(answer, d):
    # The certificate language is deliberately JSON-native.  Restrict the
    # verifier to exactly the shapes parse_answer can produce; accepting Python
    # tuples here would make the text and direct-call interfaces disagree.
    if not isinstance(answer, list):
        return False, "answer must be a list of three labeled sections"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) != 3:
        return False, f"wrong section count: expected 3, got {len(answer)}"
    if any(not isinstance(part, list) or len(part) != 2 for part in answer):
        return False, "each section must be a [label, coefficient-block] pair"
    labels = [part[0] for part in answer]
    if len(set(labels)) != len(labels):
        return False, "section labels are duplicated"
    if tuple(labels) != _SECTION_LABELS:
        return False, "sections are not in constant, linear, quadratic order"
    constant, linear, quadratic = _sections(answer)
    if not isinstance(constant, list) or len(constant) != d:
        return False, f"constant block must contain exactly {d} bits"
    if not isinstance(linear, list) or len(linear) != d:
        return False, f"linear block must contain exactly {d} rows"
    if any(not isinstance(row, list) or len(row) != i
           for i, row in enumerate(linear)):
        return False, "linear row i must contain i coefficients"
    if not isinstance(quadratic, list) or len(quadratic) != d:
        return False, f"quadratic block must contain exactly {d} rows"
    if any(not isinstance(row, list) or len(row) != math.comb(i, 2)
           for i, row in enumerate(quadratic)):
        return False, "quadratic row i must contain C(i,2) coefficients"
    values = list(constant)
    values.extend(value for row in linear for value in row)
    values.extend(value for row in quadratic for value in row)
    if any(isinstance(value, bool) or not isinstance(value, int)
           or value not in (0, 1) for value in values):
        return False, "every coefficient must be the integer 0 or 1"
    return True, "ok"


def _eval_map(answer, x, d):
    constant, linear, quadratic = _sections(answer)
    out = 0
    for i in range(d):
        bit = ((x >> i) & 1) ^ constant[i]
        for j, coefficient in enumerate(linear[i]):
            bit ^= coefficient & ((x >> j) & 1)
        for coefficient, (j, k) in zip(
                quadratic[i], itertools.combinations(range(i), 2)):
            bit ^= coefficient & ((x >> j) & 1) & ((x >> k) & 1)
        out |= bit << i
    return out


def _evaluation_bit_operations(d):
    # One XOR for each diagonal/constant combination, two primitives for every
    # linear term, and three for every quadratic term.
    return d + 2 * math.comb(d, 2) + 3 * math.comb(d, 3)


def _coefficients_from_values(d, value_at):
    """Interpolate the declared triangular quadratic map from Boolean values."""
    answer = _blank_coefficients(d)
    y0 = value_at(0)
    answer[0][1] = [(y0 >> i) & 1 for i in range(d)]
    basis_values = [value_at(1 << j) for j in range(d)]
    # Cache each finite difference once.  Besides being faster, this makes the
    # executed interpolation agree exactly with the vector-XOR accounting used
    # by the Track-B reference and compact routes below.
    linear_differences = [value ^ y0 for value in basis_values]
    quadratic_differences = {}
    for j, k in itertools.combinations(range(d), 2):
        quadratic_differences[(j, k)] = (
            value_at((1 << j) ^ (1 << k))
            ^ basis_values[j] ^ basis_values[k] ^ y0
        )
    for i in range(d):
        answer[1][1][i] = [
            (linear_differences[j] >> i) & 1 for j in range(i)
        ]
        answer[2][1][i] = [
            (quadratic_differences[(j, k)] >> i) & 1
            for j, k in itertools.combinations(range(i), 2)
        ]
    return answer


def _toggle_constant(answer, vector):
    out = copy.deepcopy(answer)
    for i in range(len(out[0][1])):
        out[0][1][i] ^= (vector >> i) & 1
    return out


def _special_points(d):
    points = [0]
    points.extend(1 << j for j in range(d))
    points.extend((1 << j) ^ (1 << k)
                  for j, k in itertools.combinations(range(d), 2))
    return points


# ---------------------------------------------------------------------------
# Inverse generation and paper-licensed reduction instance.


def _target_index(inst):
    return inst["targets_by_source"]


def _center_value(inst, x):
    targets = _target_index(inst)[x]
    return targets[0] ^ targets[1] ^ targets[2]


def _make_once(n, seed, attempt):
    d = _dimension(n)
    rng = random.Random((int(seed) << 24) ^ (attempt * 0x9E3779B1) ^ n)
    center = _random_coefficients(d, rng)

    mask1 = rng.randrange(1, n)
    mask2 = rng.randrange(1, n)
    while mask2 == mask1:
        mask2 = rng.randrange(1, n)
    masks = [mask1, mask2, mask1 ^ mask2]
    rng.shuffle(masks)

    targets_by_source = []
    for x in range(n):
        base = _eval_map(center, x, d)
        targets = [base ^ mask for mask in masks]
        rng.shuffle(targets)
        targets_by_source.append(targets)

    chosen_mask = masks[rng.randrange(3)]
    answer = _toggle_constant(center, chosen_mask)
    inst = {
        "family": "quadratic-map border-basis certificate",
        "n": n,
        "dimension": d,
        "point_count_per_side": n,
        "edge_variable_count": 3 * n,
        "clause_count": 4 * n,
        "ring_variable_count": 14 * n + 1,
        "row_order": list(range(n)),
        "targets_by_source": targets_by_source,
        "answer": answer,
    }
    # These are fixed, declared construction attacks, not a search for the
    # certificate. The certificate and all three valid matchings were sampled
    # before this filtering step.
    for attack in (_attack_minimum_targets, _attack_rank_greedy,
                   _attack_matching_fit, _attack_unshifted_center):
        if _core_valid(inst, attack(inst)):
            return None
    return inst


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate three algebraic satisfying assignments, then reduce."""
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    _dimension(n)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    for attempt in range(1, 1001):
        inst = _make_once(n, seed, attempt)
        if inst is not None:
            return inst
    raise RuntimeError("could not draw an attack-resistant algebraic instance")


# ---------------------------------------------------------------------------
# Problem statement and answer contract.


def _coefficient_example(d):
    return json.dumps(_blank_coefficients(d), separators=(",", ":"))


def render(inst) -> str:
    n = inst["n"]
    d = inst["dimension"]
    rows = "\n".join(
        f"  {x}: " + " ".join(str(y) for y in inst["targets_by_source"][x])
        for x in inst["row_order"]
    )
    statement = f"""TRIANGULAR-POLYNOMIAL BORDER-BASIS CERTIFICATE

All bit positions below are 0-indexed from the least significant bit. Integers
0 through {n - 1} represent the vectors GF(2)^{d}; vector addition is bitwise
XOR. The order of table rows and the order of the three targets in a row have no
mathematical meaning.

INSTANCE TABLE. Each row `x: y0 y1 y2` gives three distinct edges from a left
vertex x to right vertices y0,y1,y2. Every right vertex also has degree three.
Thus this is a 3-regular bipartite graph on two copies of GF(2)^{d}.
{rows}

THE 3,4-SAT INSTANCE. Introduce one Boolean variable E_(x,y) for every displayed
edge. At each left vertex and at each right vertex, let its three incident edge
variables be e1,e2,e3 and include the two clauses

  (e1 OR e2 OR e3)  and  ((NOT e1) OR (NOT e2) OR (NOT e3)).

There are {inst['edge_variable_count']} variables and {inst['clause_count']}
clauses. Every clause has three distinct variables. Every edge variable occurs
exactly four times, twice positively and twice negatively; both signs occur and
no clause contains a variable and its negation. Selecting exactly one edge at
each left and right vertex therefore satisfies all clauses.

THE PAPER'S POLYNOMIAL SYSTEM. The following is a finite schematic specification
of the sparse rational polynomials in Section 3 of Ananth--Dukkipati; expanding
the forced degree-eight family is unnecessary. For each Boolean edge variable e
introduce x_e and xb_e. For each clause C_j introduce c_j and xc_j, and introduce
X. There are {inst['ring_variable_count']} indeterminates over Q. Let tC_e be the
product of the four c_j for clauses containing e or NOT e (the exponent of X is
zero), and define

  tE_e  = x_e * xb_e^2 * tC_e,
  tEb_e = x_e^2 * xb_e * tC_e.

The variable polynomial for e is tE_e+tEb_e. In clause C_j, replace a positive
literal e by tE_e*xc_j/c_j and a negative literal by tEb_e*xc_j/c_j, and sum the
three monomials. F1 contains every total-degree-eight monomial. For an edge e,
P_e contains tE_e*xc_j for its positive occurrences and tEb_e*xc_j for its
negative occurrences; R_e contains every monomial obtained by dividing a member
of P_e by one indeterminate of positive exponent. K_e contains tE_e, tEb_e, and
the four clause-polynomial monomials belonging to e. F2 contains each monomial
in (union R_e) minus (union K_e) as a singleton polynomial. The BBD instance is
the union of the variable, clause, F1, and F2 polynomials.

YOUR WITNESS. Give a triangular quadratic polynomial permutation H on d={d}
bits. For each output bit i, its value is, in GF(2),

  H_i(x) = x_i + constant[i]
           + sum_{{0<=j<i}} linear[i][j] * x_j
           + sum_{{0<=j<k<i}} quadratic[i][pair(j,k)] * x_j*x_k.

The quadratic coefficients in row i are ordered lexicographically by pairs
(0,1),(0,2),...,(0,i-1),(1,2),...,(i-2,i-1). Empty rows are required. Because
the coefficient of x_i is fixed to one and no later input bit occurs, every
well-formed H is automatically a permutation. The checker evaluates H(x) for
all {n} sources and requires H(x) to be one of the three displayed targets.
Those edges form a perfect matching, hence a satisfying assignment.

The matching deterministically decodes to the paper's border certificate: choose
tEb_e from the variable polynomial when edge e is true and tE_e otherwise;
choose the lowest-listed satisfied literal's monomial in each clause polynomial;
choose the sole monomial of every singleton polynomial. The checker substitutes
the matching in every endpoint clause exactly. Section 3's reduction then gives
the corresponding border of an order ideal.

OUTPUT. Supply exactly three labeled JSON arrays in the order constant, linear,
quadratic. Every coefficient is the integer 0 or 1; strings and JSON booleans are
invalid. The constant block has {d} entries. Linear row i has i entries and
quadratic row i has C(i,2) entries. Here is a well-formed format example (not a
claim that the all-zero coefficients solve this instance):

  {_coefficient_example(d)}

Give your final answer inside <answer></answer> tags as that exact JSON value.
Example: <answer>{_coefficient_example(d)}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text) -> object | None:
    if not isinstance(text, str):
        return None
    bodies = re.findall(r"<answer\s*>(.*?)</answer\s*>", text, flags=re.I | re.S)
    for body in reversed(bodies):
        cleaned = body.strip()
        if cleaned.startswith("```") and cleaned.endswith("```"):
            lines = cleaned.splitlines()
            cleaned = "\n".join(lines[1:-1]).strip()
        try:
            answer = json.loads(cleaned)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(answer, list):
            return answer
    return None


def _core_valid(inst, answer):
    d = inst["dimension"]
    ok, _ = _validate_shape(answer, d)
    if not ok:
        return False
    targets = _target_index(inst)
    for x in range(inst["n"]):
        if _eval_map(answer, x, d) not in targets[x]:
            return False
    return True


def verify(inst, answer) -> tuple[bool, str]:
    try:
        n = inst["n"]
        d = inst["dimension"]
        targets = _target_index(inst)
    except (KeyError, TypeError):
        return False, "instance is missing its exact incidence data"
    ok, reason = _validate_shape(answer, d)
    if not ok:
        return False, reason
    if n != 1 << d or len(targets) != n:
        return False, "instance point count is inconsistent"

    images = []
    for x in range(n):
        y = _eval_map(answer, x, d)
        if y not in targets[x]:
            return False, f"polynomial map misses the table at source {x}"
        images.append(y)

    if len(set(images)) != n:
        return False, "polynomial map is not a permutation"
    right_degrees = [0] * n
    for source_targets in targets:
        if (not isinstance(source_targets, (list, tuple))
                or len(source_targets) != 3
                or len(set(source_targets)) != 3):
            return False, "instance has a non-cubic source row"
        for y in source_targets:
            if isinstance(y, bool) or not isinstance(y, int) or not 0 <= y < n:
                return False, "instance has an out-of-range target"
            right_degrees[y] += 1
    if any(degree != 3 for degree in right_degrees):
        return False, "instance is not cubic on the target side"

    # Exact clause substitution: one selected edge and two unselected edges at
    # every endpoint makes both its positive and its negative 3-clause true.
    left_true_counts = [1] * n
    right_true_counts = [0] * n
    for y in images:
        right_true_counts[y] += 1
    if any(value != 1 for value in left_true_counts + right_true_counts):
        return False, "decoded assignment fails an endpoint clause"
    return True, "ok"


# ---------------------------------------------------------------------------
# Bounded language, reference algorithm, attacks, and canonicalisation.


def random_candidate(inst, rng) -> object:
    if not hasattr(rng, "randrange"):
        raise TypeError("rng must provide random.Random-style randrange")
    answer = _random_coefficients(inst["dimension"], rng)
    # H(0) is exactly the constant vector, so a solver gets this constraint for
    # free from the first row.  Sampling all 2^d constants would overstate guess
    # resistance by a factor of 2^d/3.
    constant = inst["targets_by_source"][0][rng.randrange(3)]
    answer[0][1] = [
        (constant >> i) & 1 for i in range(inst["dimension"])
    ]
    return answer


def search_space(inst) -> int | None:
    d = inst["dimension"]
    return 3 * (1 << (_free_coefficients(d) - d))


def enumerate_all(inst) -> int | None:
    space = search_space(inst)
    if space > _ENUMERATION_CAP:
        return None
    d = inst["dimension"]
    count = 0
    tail_space = 1 << (_free_coefficients(d) - d)
    for constant in inst["targets_by_source"][0]:
        for code in range(tail_space):
            answer = _blank_coefficients(d)
            answer[0][1] = [(constant >> i) & 1 for i in range(d)]
            cursor = 0
            for i in range(d):
                for j in range(i):
                    answer[1][1][i][j] = (code >> cursor) & 1
                    cursor += 1
            for i in range(d):
                for j in range(math.comb(i, 2)):
                    answer[2][1][i][j] = (code >> cursor) & 1
                    cursor += 1
            if verify(inst, answer)[0]:
                count += 1
    return count


def _reference_answer(inst):
    """Polynomial-time full-table recovery with explicit operation accounting."""
    d, n = inst["dimension"], inst["n"]
    centers = [_center_value(inst, x) for x in range(n)]
    answer = _coefficients_from_values(d, centers.__getitem__)
    offset = inst["targets_by_source"][0][0] ^ centers[0]
    answer = _toggle_constant(answer, offset)
    validated = _core_valid(inst, answer)
    interpolation_ops = d + 3 * math.comb(d, 2)
    stats = {
        "row_center_vector_xors": 2 * n,
        "interpolation_vector_xors": interpolation_ops,
        "offset_vector_xors": 1,
        "validation_scalar_operations": n * (_evaluation_bit_operations(d) + 1),
    }
    stats["total_counted_operations"] = sum(stats.values())
    stats["validated"] = validated
    return answer, stats


def _compact_answer(inst):
    d = inst["dimension"]
    cache = {x: _center_value(inst, x) for x in _special_points(d)}
    answer = _coefficients_from_values(d, cache.__getitem__)
    offset = inst["targets_by_source"][0][0] ^ cache[0]
    answer = _toggle_constant(answer, offset)
    operations = (2 * len(cache) + d
                  + 3 * math.comb(d, 2) + 1)
    return answer, operations


def _attack_minimum_targets(inst):
    d = inst["dimension"]
    return _coefficients_from_values(
        d, lambda x: min(inst["targets_by_source"][x]))


def _attack_rank_greedy(inst):
    d = inst["dimension"]

    def chosen(x):
        targets = sorted(inst["targets_by_source"][x])
        return targets[x.bit_count() % 3]

    return _coefficients_from_values(d, chosen)


def _attack_unshifted_center(inst):
    d = inst["dimension"]
    return _coefficients_from_values(d, lambda x: _center_value(inst, x))


def _attack_matching_fit(inst):
    """Find a perfect matching, then force-fit it to the answer language."""
    n = inst["n"]
    match_left = [-1] * n
    match_right = [-1] * n
    for start in range(n):
        queue = [start]
        head = 0
        seen_left = {start}
        seen_right = set()
        parent_right = {}
        free_right = None
        while head < len(queue) and free_right is None:
            x = queue[head]
            head += 1
            for y in sorted(inst["targets_by_source"][x]):
                if y in seen_right:
                    continue
                seen_right.add(y)
                parent_right[y] = x
                if match_right[y] < 0:
                    free_right = y
                    break
                next_left = match_right[y]
                if next_left not in seen_left:
                    seen_left.add(next_left)
                    queue.append(next_left)
        if free_right is None:
            return _blank_coefficients(inst["dimension"])
        y = free_right
        while y >= 0:
            x = parent_right[y]
            previous_y = match_left[x]
            match_left[x] = y
            match_right[y] = x
            y = previous_y
    return _coefficients_from_values(inst["dimension"], match_left.__getitem__)


def _random_restart_attack(inst, rng, restarts=256):
    last = None
    for index in range(restarts):
        last = random_candidate(inst, rng)
        if _core_valid(inst, last):
            return last, index + 1
    return last, restarts


def _translate_answer(answer, source_mask, target_mask):
    d = len(answer[0][1])
    return _coefficients_from_values(
        d, lambda x: _eval_map(answer, x ^ source_mask, d) ^ target_mask)


def _transform_instance(inst, source_mask=0, target_mask=0,
                        reorder_seed=None, permute_targets=False):
    out = copy.deepcopy(inst)
    n = inst["n"]
    transformed = [None] * n
    rng = random.Random(reorder_seed) if reorder_seed is not None else None
    for x in range(n):
        new_x = x ^ source_mask
        values = [y ^ target_mask for y in inst["targets_by_source"][x]]
        if permute_targets and rng is not None:
            rng.shuffle(values)
        transformed[new_x] = values
    out["targets_by_source"] = transformed
    out["row_order"] = list(range(n))
    if rng is not None:
        rng.shuffle(out["row_order"])
    out["answer"] = _translate_answer(
        inst["answer"], source_mask, target_mask)
    return out


def _canonical_payload(inst):
    d, n = inst["dimension"], inst["n"]
    center = _coefficients_from_values(d, lambda x: _center_value(inst, x))
    constant, linear, quadratic = _sections(center)
    del constant
    offsets = sorted(y ^ _center_value(inst, 0)
                     for y in inst["targets_by_source"][0])
    quadratic_flat = tuple(value for row in quadratic for value in row)

    # Source translations preserve triangular degree two. Quadratic terms stay
    # fixed; a translation changes a linear coefficient by contractions of the
    # quadratic tensor. Target translations affect only constants, which are
    # intentionally absent from the normal form.
    translated_linears = []
    for source_mask in range(n):
        flat = []
        for i in range(d):
            pairs = list(itertools.combinations(range(i), 2))
            qlookup = {pair: quadratic[i][index]
                       for index, pair in enumerate(pairs)}
            for j in range(i):
                value = linear[i][j]
                for k in range(i):
                    if k == j:
                        continue
                    pair = (j, k) if j < k else (k, j)
                    value ^= qlookup.get(pair, 0) & ((source_mask >> k) & 1)
                flat.append(value)
        translated_linears.append(tuple(flat))
    return {
        "dimension": d,
        "quadratic": quadratic_flat,
        "translation_normalised_linear": min(translated_linears),
        "mask_multiset": tuple(offsets),
    }


def canonical_key(inst) -> str:
    payload = _canonical_payload(inst)
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params) -> dict | str | None:
    n = int(params.get("n", 256))
    if n < 1024:
        return {"n": 2 * n}
    # The next dimension has 231 free coefficients and fits the character cap,
    # but its selected-row route takes 311 operations and fails G9(c). There is
    # no honest harder rung under the no-tool effort cap.
    return "cap_bound"


# ---------------------------------------------------------------------------
# Mandatory gates.


def _answer_atom_count(answer):
    if isinstance(answer, dict):
        return sum(_answer_atom_count(value) for value in answer.values())
    if isinstance(answer, (list, tuple)):
        return sum(_answer_atom_count(value) for value in answer)
    return 1


def selftest():
    report = {"track": TRACK, "shipping_difficulty": SHIPPING_DIFFICULTY}

    attempts = 0
    failures = []
    json_roundtrips = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            attempts += 1
            if not ok:
                failures.append([preset, seed, reason])
            if json.loads(json.dumps(inst["answer"])) == inst["answer"]:
                json_roundtrips += 1
    report["G1_planted_verifies"] = {
        "pass": not failures and json_roundtrips == attempts,
        "attempts": attempts,
        "json_roundtrips": json_roundtrips,
        "failures": failures,
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=90210, **ship_params)
    answer = inst["answer"]
    drop = copy.deepcopy(answer)
    drop.pop()
    swap = copy.deepcopy(answer)
    swap[0], swap[1] = swap[1], swap[0]
    duplicate = copy.deepcopy(answer)
    duplicate[1][0] = duplicate[0][0]
    outside = copy.deepcopy(answer)
    outside[0][1][0] = 2
    corruptions = {
        "drop": drop,
        "swap": swap,
        "duplicate": duplicate,
        "empty": [],
        "out_of_range": outside,
    }
    cases = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(inst, candidate)
        cases[name] = {"rejected": not ok, "reason": reason}
    reasons = [item["reason"] for item in cases.values()]
    report["G2_rejects_corruption"] = {
        "pass": all(item["rejected"] for item in cases.values())
        and len(set(reasons)) == len(reasons),
        "cases": cases,
    }

    realistic = (
        "I used the row invariant and checked the decoded clauses.\n\n"
        "```json\n<answer>" + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("not an answer") is None,
        "parsed_sections": len(parsed) if isinstance(parsed, list) else None,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    samples = 200_000
    guess_rng = random.Random(0x10116021)
    hits = 0
    for _ in range(samples):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    observed = hits / samples
    valid_count_upper_bound = 3 ** len(_special_points(inst["dimension"]))
    analytic_probability_upper_bound = valid_count_upper_bound / search_space(inst)
    report["G4_guess_resistance"] = {
        "pass": observed < 1e-6 and analytic_probability_upper_bound < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": observed,
        "structure_aware_space": search_space(inst),
        "valid_count_upper_bound": valid_count_upper_bound,
        "analytic_probability_upper_bound": analytic_probability_upper_bound,
        "upper_bound_reason": (
            "a quadratic map is determined by its values at 0, unit vectors, "
            "and pair sums, with at most three table choices at each point"
        ),
        "sampler": (
            "uniform over the three row-zero-compatible constants and every "
            "remaining free coefficient; the fixed diagonal and dependency "
            "order are enforced"
        ),
    }

    start = time.perf_counter()
    reference, reference_stats = _reference_answer(inst)
    baseline_wall = time.perf_counter() - start
    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": verify(inst, reference)[0] and observed < 1e-6
        and demo_count is not None,
        "shipping_sampled_valid_hits": hits,
        "shipping_density_samples": samples,
        "shipping_sampled_solution_fraction": observed,
        "shipping_solution_fraction_upper_bound": analytic_probability_upper_bound,
        "shipping_certificate_space": search_space(inst),
        "known_constructed_solutions_lower_bound": 3,
        "demo_exact_solution_count": demo_count,
        "baseline_wall_seconds": round(baseline_wall, 6),
        "baseline_counted_operations": reference_stats["total_counted_operations"],
        "baseline_operation_breakdown": reference_stats,
    }

    attacks = {
        "outlier_minimum_target": {"successes": 0, "attempts": 0},
        "greedy_target_rank": {"successes": 0, "attempts": 0},
        "domain_matching_then_quadratic_fit": {"successes": 0, "attempts": 0},
        "random_restart_256": {"successes": 0, "attempts": 0},
        "in_context_unshifted_center": {"successes": 0, "attempts": 0},
    }
    ref_successes = 0
    ref_times = []
    ref_ops = []
    for seed in range(3100, 3108):
        attacked = make_instance(seed=seed, **ship_params)
        random_answer, _ = _random_restart_attack(
            attacked, random.Random(seed ^ 0xB0D3), restarts=256)
        candidates = {
            "outlier_minimum_target": _attack_minimum_targets(attacked),
            "greedy_target_rank": _attack_rank_greedy(attacked),
            "domain_matching_then_quadratic_fit": _attack_matching_fit(attacked),
            "random_restart_256": random_answer,
            "in_context_unshifted_center": _attack_unshifted_center(attacked),
        }
        for name, candidate in candidates.items():
            attacks[name]["attempts"] += 1
            if verify(attacked, candidate)[0]:
                attacks[name]["successes"] += 1
        t0 = time.perf_counter()
        ref_answer, stats = _reference_answer(attacked)
        ref_times.append(time.perf_counter() - t0)
        ref_ops.append(stats["total_counted_operations"])
        if verify(attacked, ref_answer)[0]:
            ref_successes += 1
    all_failed = all(item["successes"] == 0 for item in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "rowwise-XOR quadratic interpolation with full validation",
            "complexity": "O(N (log N)^3) exact operations",
            "median_wall_clock_sec": round(statistics.median(ref_times), 6),
            "median_operations": int(statistics.median(ref_ops)),
            "operation_definition": (
                "one d-bit vector XOR during recovery, or one scalar GF(2) "
                "AND/XOR or table-membership primitive during validation"
            ),
            "solves": f"{ref_successes}/8, as expected",
        },
    }

    doubled = make_instance(n=2 * ship_params["n"], seed=77)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst),
        "shipping_n": ship_params["n"],
        "shipping_dimension": inst["dimension"],
        "doubled_n": doubled["n"],
        "doubled_dimension": doubled["dimension"],
        "shipping_free_coefficients": _free_coefficients(inst["dimension"]),
        "doubled_free_coefficients": _free_coefficients(doubled["dimension"]),
        "shipping_language_size": search_space(inst),
        "doubled_language_size": search_space(doubled),
        "doubled_verify_reason": doubled_reason,
    }

    invariant_checks = 0
    carried_checks = 0
    distinct_keys = []
    for seed in range(7000, 7020):
        original = make_instance(seed=seed, **ship_params)
        key = canonical_key(original)
        distinct_keys.append(key)
        rng = random.Random(seed ^ 0xCA11)
        source_mask = rng.randrange(original["n"])
        target_mask = rng.randrange(original["n"])
        variants = [
            _transform_instance(original, reorder_seed=seed,
                                permute_targets=True),
            _transform_instance(original, source_mask=source_mask,
                                reorder_seed=seed + 1, permute_targets=True),
            _transform_instance(original, target_mask=target_mask,
                                reorder_seed=seed + 2, permute_targets=True),
            _transform_instance(original, source_mask=source_mask,
                                target_mask=target_mask,
                                reorder_seed=seed + 3, permute_targets=True),
        ]
        for transformed in variants:
            invariant_checks += 1
            if canonical_key(transformed) == key:
                ok, _ = verify(transformed, transformed["answer"])
                if ok:
                    carried_checks += 1
    report["G8_canonical_key"] = {
        "pass": invariant_checks == 80 and carried_checks == 80
        and len(set(distinct_keys)) == 20,
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "unrelated_distinct": len(set(distinct_keys)),
        "unrelated_attempts": 20,
        "transformations": [
            "row and within-row reordering",
            "global source XOR translation",
            "global target XOR translation",
            "composed source and target translations plus reorderings",
        ],
        "key_basis": (
            "translation-normalised linear tensor, quadratic tensor, and mask "
            "multiset recovered from the unordered table"
        ),
    }

    compact, compact_operations = _compact_answer(inst)
    answer_text = json.dumps(answer, separators=(",", ":"))
    answer_chars = len(answer_text)
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = _answer_atom_count(answer)
    arms = copy.deepcopy(G9_RESULTS["arms"])
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    within_caps = (answer_chars <= 2000 and answer_elements <= 256
                   and compact_operations <= 300)
    report["G9_no_tool_suitability"] = {
        # The oracle arms are diagnostics as of 2026-09-05.  Only the answer
        # size/atom and intended-route effort caps gate this result.
        "pass": within_caps and verify(inst, compact)[0],
        "arms": arms,
        "evidence_status": G9_RESULTS["evidence_status"],
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact_operations,
        "operation_definition": (
            f"one exact XOR of two GF(2)^{inst['dimension']} vectors"
        ),
        "operation_breakdown": {
            "selected_row_center_xors": 2 * len(_special_points(inst["dimension"])),
            "interpolation_xors": (
                inst["dimension"]
                + 3 * math.comb(inst["dimension"], 2)
            ),
            "offset_xor": 1,
        },
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
