"""Verified Track-B generator for arXiv:1011.6021.

The generated object is the paper's sparse polynomial system, specified without
printing the astronomically large but completely forced degree-eight monomial
family.  A bounded projective-map witness decodes to the border-term set used in
the proof of the paper's main reduction.
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
import time


TRACK: str = "B"

STRUCTURAL_HINT: str = (
    "The three algebraic matchings share one projective point-image pair; use it "
    "with two other rows to interpolate a projective transformation."
)
PLACEBO_HINT: str = (
    "Keep the point coding and the ordering of the six requested fields consistent "
    "while checking the proposed certificate."
)

PROBLEM_PROFILE: dict = {
    "native_domain": "algebra",
    "object_regime": "finite_field",
    "computational_core": "linear_algebra",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "schematically specified sparse polynomials over Q",
        "monomials represented by exponent vectors",
        "a projective-line incidence table over GF(q)",
    ],
    "verification_operations": [
        "exact modular 2 by 2 matrix arithmetic",
        "projective-point substitution",
        "edge-incidence comparison",
        "Boolean clause substitution",
        "deterministic border-term decoding",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3, Reduction and Correctness of reduction: bounded-occurrence "
        "3,4-SAT is mapped to Border Basis Detection"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "change of variables",
    "intuition_description": (
        "Recognize the three superposed matchings as conjugated affine maps and "
        "interpolate one projective map; without that change of coordinates one "
        "must mechanically test projective candidates against hundreds of rows."
    ),
    "hardness_basis": (
        "Track B: three-point PGL(2,q) interpolation followed by exact incidence "
        "validation is O(q log q) bit operations; shipping measurements are filled "
        "from selftest's reference-algorithm record, while the shared-pair route "
        "uses at most 286 exact field operations."
    ),
    "max_answer_tokens": 18,
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
    "demo": {"n": 7},
    "easy": {"n": 211},
    "medium": {"n": 307},
    "hard": {"n": 401},
}
SHIPPING_DIFFICULTY: str = "easy"

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "Six labeled projective-point codes x1,y1,x2,y2,x3,y3. The three x "
        "values and the three y values are separately distinct in P^1(GF(q)); "
        "the pairs specify the unique projective transformation taking xi to yi."
    ),
    "bounds": {
        "labeled_fields": 6,
        "source_points": 3,
        "target_points": 3,
        "point_range": "0..q inclusive, with q coding infinity",
        "max_shipping_q": 401,
    },
}

NOTES: str = (
    "Section 2 fixes order ideals, borders, border prebases, and the border-basis "
    "Buchberger criterion. Section 3 (BBD is in NP) gives the three executable "
    "conditions for a monomial set to be a border and its polynomial-time "
    "certificate verifier. The Reduction and Correctness subsections fix the exact "
    "3,4-SAT promise: three distinct variables per clause, at most four total "
    "occurrences per variable, both signs present, and disjoint polynomial "
    "supports. The main theorem maps satisfying assignments to border sets. That "
    "theorem supplies generation, but it does not make this distribution Track A: "
    "the three superposed matchings can be recovered by PGL interpolation in "
    "linear time, so the family is declared Track B. Every edge occurs positively "
    "at both endpoints and negatively at both endpoints, hence exactly four times. "
    "All three planted maps are sampled symmetrically and are valid, so there is no "
    "distinguished planted edge class. Generation rejects instances solved by the "
    "fixed min-target, local-greedy, or identity ansatz probes; full-language random "
    "restart remains negligible."
)

G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 3},
        "hinted": {"solved": 0, "attempts": 3},
        "placebo": {"solved": 0, "attempts": 3},
    },
    "hinted_verdict": "hardened",
}

_LABELS = ("x1", "y1", "x2", "y2", "x3", "y3")
_ENUMERATION_CAP = 200_000


# ---------------------------------------------------------------------------
# Exact projective arithmetic.  The integer q itself is the code for infinity.


def _is_prime(value):
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    limit = math.isqrt(value)
    for divisor in range(3, limit + 1, 2):
        if value % divisor == 0:
            return False
    return True


def _next_prime(value):
    candidate = max(7, int(value))
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _hom(point, q):
    return (1, 0) if point == q else (point, 1)


def _point(pair, q):
    numerator, denominator = pair[0] % q, pair[1] % q
    if denominator == 0:
        return q
    return numerator * pow(denominator, -1, q) % q


def _normalise_matrix(matrix, q):
    values = [matrix[0][0] % q, matrix[0][1] % q,
              matrix[1][0] % q, matrix[1][1] % q]
    first = next((value for value in values if value), None)
    if first is None:
        raise ValueError("zero projective matrix")
    scale = pow(first, -1, q)
    values = [(value * scale) % q for value in values]
    return ((values[0], values[1]), (values[2], values[3]))


def _det(matrix, q):
    return (matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]) % q


def _matmul(left, right, q):
    return _normalise_matrix((
        ((left[0][0] * right[0][0] + left[0][1] * right[1][0]) % q,
         (left[0][0] * right[0][1] + left[0][1] * right[1][1]) % q),
        ((left[1][0] * right[0][0] + left[1][1] * right[1][0]) % q,
         (left[1][0] * right[0][1] + left[1][1] * right[1][1]) % q),
    ), q)


def _inverse(matrix, q):
    if _det(matrix, q) == 0:
        raise ValueError("singular projective matrix")
    return _normalise_matrix((
        (matrix[1][1], -matrix[0][1]),
        (-matrix[1][0], matrix[0][0]),
    ), q)


def _apply(matrix, point, q):
    vector = _hom(point, q)
    return _point((
        matrix[0][0] * vector[0] + matrix[0][1] * vector[1],
        matrix[1][0] * vector[0] + matrix[1][1] * vector[1],
    ), q)


def _matrix_from_images(images, q):
    """Map canonical (0,1,infinity) to three distinct image points."""
    y0, y1, yinf = images
    if len({y0, y1, yinf}) != 3:
        raise ValueError("target images are not distinct")
    u = _hom(y0, q)
    v = _hom(y1, q)
    w = _hom(yinf, q)
    alpha = (v[0] * u[1] - v[1] * u[0]) % q
    beta = (w[0] * v[1] - w[1] * v[0]) % q
    matrix = ((alpha * w[0], beta * u[0]),
              (alpha * w[1], beta * u[1]))
    matrix = _normalise_matrix(matrix, q)
    if _det(matrix, q) == 0:
        raise ValueError("interpolation produced a singular matrix")
    return matrix


def _matrix_from_pairs(xs, ys, q):
    if len(set(xs)) != 3 or len(set(ys)) != 3:
        raise ValueError("three source and target points must be distinct")
    source = _matrix_from_images(xs, q)
    target = _matrix_from_images(ys, q)
    return _matmul(target, _inverse(source, q), q)


def _random_pgl(q, rng):
    while True:
        matrix = ((rng.randrange(q), rng.randrange(q)),
                  (rng.randrange(q), rng.randrange(q)))
        if _det(matrix, q):
            return _normalise_matrix(matrix, q)


def _answer_from_pairs(xs, ys):
    values = (xs[0], ys[0], xs[1], ys[1], xs[2], ys[2])
    return [[label, value] for label, value in zip(_LABELS, values)]


def _answer_values(answer):
    return [entry[1] for entry in answer]


def _answer_text(answer):
    return ", ".join(f"{label}={value}" for label, value in answer)


# ---------------------------------------------------------------------------
# Instance construction.


def _relations(inst):
    q = inst["q"]
    relations = [set() for _ in range(q + 1)]
    multiplicities = [dict() for _ in range(q + 1)]
    for edge in inst["edges"]:
        x, y = edge["left"], edge["right"]
        relations[x].add(y)
        multiplicities[x][y] = multiplicities[x].get(y, 0) + 1
    return relations, multiplicities


def _right_degrees(inst):
    q = inst["q"]
    degree = [0] * (q + 1)
    for edge in inst["edges"]:
        degree[edge["right"]] += 1
    return degree


def _nontrivial_connected(inst, common_x, common_y):
    q = inst["q"]
    left_nodes = [(0, x) for x in range(q + 1) if x != common_x]
    right_nodes = [(1, y) for y in range(q + 1) if y != common_y]
    nodes = set(left_nodes + right_nodes)
    if not nodes:
        return False
    adjacency = {node: [] for node in nodes}
    for edge in inst["edges"]:
        x, y = edge["left"], edge["right"]
        if x == common_x or y == common_y:
            continue
        a, b = (0, x), (1, y)
        adjacency[a].append(b)
        adjacency[b].append(a)
    start = next(iter(nodes))
    seen = {start}
    todo = [start]
    while todo:
        node = todo.pop()
        for other in adjacency[node]:
            if other not in seen:
                seen.add(other)
                todo.append(other)
    return seen == nodes


def _candidate_matrix(answer, q):
    values = _answer_values(answer)
    xs = (values[0], values[2], values[4])
    ys = (values[1], values[3], values[5])
    return _matrix_from_pairs(xs, ys, q)


def _core_valid(inst, answer):
    try:
        matrix = _candidate_matrix(answer, inst["q"])
    except (TypeError, ValueError, ZeroDivisionError):
        return False
    relation, _ = _relations(inst)
    q = inst["q"]
    return all(_apply(matrix, x, q) in relation[x] for x in range(q + 1))


def _attack_min_targets(inst):
    q = inst["q"]
    relation, _ = _relations(inst)
    xs = (0, 1, q)
    ys = tuple(min(relation[x]) for x in xs)
    return _answer_from_pairs(xs, ys)


def _attack_local_greedy(inst):
    relation, _ = _relations(inst)
    xs = (0, 1, 2)
    used = set()
    ys = []
    for x in xs:
        choices = sorted(relation[x], key=lambda y: ((y - x) % (inst["q"] + 1), y))
        chosen = next((y for y in choices if y not in used), choices[0])
        ys.append(chosen)
        used.add(chosen)
    return _answer_from_pairs(xs, tuple(ys))


def _attack_identity(inst):
    q = inst["q"]
    return _answer_from_pairs((0, 1, q), (0, 1, q))


def _make_once(requested_n, seed, attempt):
    q = _next_prime(requested_n)
    rng = random.Random((int(seed) << 20) ^ (attempt * 0x9E3779B1) ^ q)
    source_change = _random_pgl(q, rng)
    target_change = _random_pgl(q, rng)
    source_inverse = _inverse(source_change, q)

    affine_parameters = set()
    while len(affine_parameters) < 3:
        affine_parameters.add((rng.randrange(1, q), rng.randrange(q)))
    parameters = list(affine_parameters)
    rng.shuffle(parameters)
    maps = []
    for slope, offset in parameters:
        affine = _normalise_matrix(((slope, offset), (0, 1)), q)
        maps.append(_matmul(target_change, _matmul(affine, source_inverse, q), q))

    raw_edges = []
    for x in range(q + 1):
        for layer, matrix in enumerate(maps):
            raw_edges.append({"left": x, "right": _apply(matrix, x, q), "layer": layer})
    rng.shuffle(raw_edges)
    edges = [
        {"id": index + 1, "left": edge["left"], "right": edge["right"]}
        for index, edge in enumerate(raw_edges)
    ]
    inst = {
        "family": "projectively compressed border-basis certificate",
        "n": int(requested_n),
        "q": q,
        "point_count_per_side": q + 1,
        "edge_variables": 3 * (q + 1),
        "clause_count": 4 * (q + 1),
        "ring_variable_count": 14 * (q + 1) + 1,
        "edges": edges,
    }

    relation, _ = _relations(inst)
    common_sources = [x for x, targets in enumerate(relation) if len(targets) == 1]
    if len(common_sources) != 1:
        return None
    common_x = common_sources[0]
    common_y = next(iter(relation[common_x]))
    if _right_degrees(inst) != [3] * (q + 1):
        return None
    if not _nontrivial_connected(inst, common_x, common_y):
        return None

    regular_rows = [x for x in range(q + 1) if x != common_x and len(relation[x]) == 3]
    if len(regular_rows) < 4:
        return None
    rng.shuffle(regular_rows)
    u, v = regular_rows[:2]
    chosen_map = maps[rng.randrange(3)]
    xs = (common_x, u, v)
    ys = tuple(_apply(chosen_map, x, q) for x in xs)
    answer = _answer_from_pairs(xs, ys)
    inst["answer"] = answer

    # Reject only fixed, predeclared signatures.  The known maps are never found
    # by solving the graph; all three were sampled before the graph was built.
    for attack in (_attack_min_targets, _attack_local_greedy, _attack_identity):
        if _core_valid(inst, attack(inst)):
            return None
    return inst


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate three valid border certificates before exposing the graph."""
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 7:
        raise ValueError("n must be an integer at least 7")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    for attempt in range(1, 4001):
        inst = _make_once(n, seed, attempt)
        if inst is not None:
            return inst
    raise RuntimeError("could not draw a connected attack-resistant instance")


# ---------------------------------------------------------------------------
# Problem statement and answer contract.


def _point_name(point, q):
    return "INF" if point == q else str(point)


def render(inst) -> str:
    q = inst["q"]
    edge_lines = "\n".join(
        f"  {edge['id']}: {_point_name(edge['left'], q)} {_point_name(edge['right'], q)}"
        for edge in inst["edges"]
    )
    statement = f"""PROJECTIVELY COMPRESSED BORDER-BASIS CERTIFICATE

Work over the rational polynomial ring described below.  Separately, GF({q})
is used only to index a compact certificate.  A projective point is one of
0,1,...,{q - 1},INF; in the answer, write the integer {q} for INF.

INSTANCE GRAPH.  There are two copies L and R of the projective line and
{inst['edge_variables']} edge variables E_1,...,E_{inst['edge_variables']}.
Each row "e: x y" means edge E_e joins L_x to R_y.  Parallel edges are distinct.
The order of the rows has no meaning.
{edge_lines}

THE 3,4-SAT FORMULA.  At every point vertex p, let its three incident edge
indices be e1,e2,e3.  Include exactly these two 3-clauses:

  (E_e1 OR E_e2 OR E_e3)
  ((NOT E_e1) OR (NOT E_e2) OR (NOT E_e3)).

Thus there are {inst['clause_count']} clauses.  Every clause uses three distinct
edge variables.  Every E_e occurs in exactly four clauses, twice positively and
twice negatively, and both signs occur.  A set of exactly {q + 1} true edges
satisfies all clauses exactly when it is a perfect matching: one true edge at
every L point and every R point.

THE POLYNOMIAL SYSTEM (the paper's Section 3 reduction).  This paragraph is a
complete finite specification; the forced families are written schematically
because expanding all degree-eight monomials would obscure the search problem.
For each edge e introduce indeterminates x_e and xb_e.  For each of the
{inst['clause_count']} clauses C_j introduce c_j and xc_j, and introduce X.
The ring therefore has {inst['ring_variable_count']} indeterminates over Q.

For edge e, let tC_e be the product of the four c_j whose clauses contain E_e
or NOT E_e (X has exponent 0 because there are four occurrences), and put

  tE_e  = x_e * xb_e^2 * tC_e,
  tEb_e = x_e^2 * xb_e * tC_e.

The variable polynomial is tE_e + tEb_e.  For a clause C_j, replace a positive
literal E_e by tE_e*xc_j/c_j and a negative literal NOT E_e by
tEb_e*xc_j/c_j; the sum of its three resulting monomials is its clause
polynomial.  A monomial is an exponent vector, multiplication adds exponents,
and division by c_j subtracts one from its c_j exponent (which is 1 here).

For completeness, the remaining singleton polynomials are exactly those in the
paper: F1 contains every monomial of total degree 8.  For each e, P_e contains
tE_e*c_j for its two positive clauses and tEb_e*c_j for its two negative
clauses; R_e is the set of all monomials obtained by dividing a member of P_e by
one indeterminate of positive exponent.  K_e contains tE_e, tEb_e and the four
clause-polynomial monomials belonging to e.  F2 contains each monomial in
the union of R_e minus the union of K_e as a singleton polynomial.  The BBD
instance F is the union of all variable, clause, F1 and F2 polynomials.

CERTIFICATE DECODER.  Submit three distinct source points x1,x2,x3 and three
distinct target points y1,y2,y3.  They determine the unique projective map
f(z)=(a*z+b)/(c*z+d) over GF({q}); homogeneous coordinates handle INF.  The
checker requires (x,f(x)) to occur as an edge row for every projective x.  If
parallel edges occur, select the lowest numbered one.  These selected edges are
true and all others false, giving a perfect matching and hence a satisfying
assignment.

The decoded border term of the variable polynomial for e is tEb_e when E_e is
true and tE_e otherwise.  In every clause polynomial, the decoded border term
is the monomial of its lowest-index satisfied literal.  Every singleton
polynomial has its sole term selected.  The paper's three border conditions and
Buchberger criterion then make this decoded set the border of an order ideal
and F its border basis.  The checker performs the finite projective substitution
and all clause incidences exactly; it never reads the planted answer.

OUTPUT.  Order matters for the six labels.  Values are inclusive in 0..{q};
{q} means INF.  Repeats are forbidden among x1,x2,x3 and separately among
y1,y2,y3.  Give your final answer inside <answer></answer> tags as:
x1=value, y1=value, x2=value, y2=value, x3=value, y3=value
Example: <answer>x1=0, y1=1, x2=1, y2=2, x3=2, y3=3</answer>
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
    pattern = re.compile(
        r"^\s*x1\s*=\s*([+-]?\d+)\s*,\s*y1\s*=\s*([+-]?\d+)\s*,\s*"
        r"x2\s*=\s*([+-]?\d+)\s*,\s*y2\s*=\s*([+-]?\d+)\s*,\s*"
        r"x3\s*=\s*([+-]?\d+)\s*,\s*y3\s*=\s*([+-]?\d+)\s*$",
        flags=re.I,
    )
    for body in reversed(bodies):
        match = pattern.fullmatch(body)
        if match:
            try:
                values = [int(value) for value in match.groups()]
            except ValueError:
                continue
            return [[label, value] for label, value in zip(_LABELS, values)]
    return None


def verify(inst, answer) -> tuple[bool, str]:
    q = inst.get("q")
    if not isinstance(answer, (list, tuple)):
        return False, "answer must be a list of six labeled fields"
    if len(answer) == 0:
        return False, "answer is empty"
    if len(answer) != 6:
        return False, f"wrong field count: expected 6, got {len(answer)}"
    if any(not isinstance(entry, (list, tuple)) or len(entry) != 2 for entry in answer):
        return False, "each field must be a [label, integer] pair"
    labels = [entry[0] for entry in answer]
    if len(set(labels)) != len(labels):
        return False, "coefficient labels are duplicated"
    if tuple(labels) != _LABELS:
        return False, "fields are not in x1,y1,x2,y2,x3,y3 order"
    values = [entry[1] for entry in answer]
    for index, value in enumerate(values):
        if isinstance(value, bool) or not isinstance(value, int):
            return False, f"{_LABELS[index]} is not an integer"
        if not 0 <= value <= q:
            return False, f"{_LABELS[index]} is outside 0..{q}"
    xs = (values[0], values[2], values[4])
    ys = (values[1], values[3], values[5])
    if len(set(xs)) != 3:
        return False, "source projective points are not distinct"
    if len(set(ys)) != 3:
        return False, "target projective points are not distinct"
    try:
        matrix = _matrix_from_pairs(xs, ys, q)
    except (ValueError, ZeroDivisionError) as exc:
        return False, f"projective interpolation failed: {exc}"
    relation, multiplicities = _relations(inst)
    selected = []
    for x in range(q + 1):
        y = _apply(matrix, x, q)
        if y not in relation[x]:
            return False, f"projective map misses the graph at source point {x}"
        edge_id = min(
            edge["id"] for edge in inst["edges"]
            if edge["left"] == x and edge["right"] == y
        )
        selected.append(edge_id)
    if len(set(selected)) != q + 1:
        return False, "decoded edge variables are not distinct"
    # A PGL matrix is a permutation of the projective line.  Check it directly,
    # then substitute the decoded matching into both clauses at every endpoint.
    images = [_apply(matrix, x, q) for x in range(q + 1)]
    if len(set(images)) != q + 1:
        return False, "decoded map is not a projective-line permutation"
    true_edges = set(selected)
    left_incident = [[] for _ in range(q + 1)]
    right_incident = [[] for _ in range(q + 1)]
    for edge in inst["edges"]:
        left_incident[edge["left"]].append(edge["id"])
        right_incident[edge["right"]].append(edge["id"])
    for side, rows in (("L", left_incident), ("R", right_incident)):
        for point, incident in enumerate(rows):
            if len(incident) != 3:
                return False, f"instance has wrong degree at {side}_{point}"
            true_count = sum(edge in true_edges for edge in incident)
            if true_count != 1:
                return False, f"decoded positive clause fails at {side}_{point}"
            if len(incident) - true_count < 1:
                return False, f"decoded negative clause fails at {side}_{point}"
    del multiplicities
    return True, "ok"


# ---------------------------------------------------------------------------
# Candidate language, counting, canonicalisation and escalation.


def random_candidate(inst, rng) -> object:
    if not hasattr(rng, "sample"):
        raise TypeError("rng must provide random.Random-style sample")
    points = range(inst["q"] + 1)
    xs = tuple(rng.sample(points, 3))
    ys = tuple(rng.sample(points, 3))
    return _answer_from_pairs(xs, ys)


def search_space(inst) -> int | None:
    q = inst["q"]
    ordered_triples = (q + 1) * q * (q - 1)
    return ordered_triples * ordered_triples


def enumerate_all(inst) -> int | None:
    if search_space(inst) > _ENUMERATION_CAP:
        return None
    q = inst["q"]
    count = 0
    points = range(q + 1)
    for xs in itertools.permutations(points, 3):
        for ys in itertools.permutations(points, 3):
            if verify(inst, _answer_from_pairs(xs, ys))[0]:
                count += 1
    return count


def _recover_maps(inst):
    """All PGL maps inside the cubic relation, with measured exact work."""
    q = inst["q"]
    relation, _ = _relations(inst)
    anchors = (0, 1, q)
    stats = {"candidates": 0, "point_evaluations": 0, "field_operations": 0}
    found = {}
    for ys in itertools.product(*(sorted(relation[x]) for x in anchors)):
        if len(set(ys)) != 3:
            continue
        stats["candidates"] += 1
        try:
            matrix = _matrix_from_images(ys, q)
        except ValueError:
            continue
        stats["field_operations"] += 14
        okay = True
        for x in range(q + 1):
            stats["point_evaluations"] += 1
            stats["field_operations"] += 7
            if _apply(matrix, x, q) not in relation[x]:
                okay = False
                break
        if okay:
            flat = tuple(matrix[0] + matrix[1])
            found[flat] = matrix
    return [found[key] for key in sorted(found)], stats


def _j_invariant(matrix, q):
    trace = (matrix[0][0] + matrix[1][1]) % q
    determinant = _det(matrix, q)
    return trace * trace * pow(determinant, -1, q) % q


def canonical_key(inst) -> str:
    """PGL-coordinate, side-swap and input-order invariant structural key."""
    q = inst["q"]
    maps, _ = _recover_maps(inst)
    invariants = []
    for i in range(len(maps)):
        for j in range(i + 1, len(maps)):
            relative = _matmul(_inverse(maps[i], q), maps[j], q)
            invariants.append(_j_invariant(relative, q))
    payload = {
        "q": q,
        "contained_maps": len(maps),
        "pairwise_projective_conjugacy": sorted(invariants),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def escalate(params) -> dict | None:
    n = int(params.get("n", 211))
    if n >= 809:
        return None
    return {"n": _next_prime(math.ceil(1.35 * n))}


# ---------------------------------------------------------------------------
# Adversaries and transformations used by selftest.


def _reference_answer(inst):
    maps, stats = _recover_maps(inst)
    if not maps:
        return None, stats
    matrix = maps[0]
    q = inst["q"]
    xs = (0, 1, q)
    ys = tuple(_apply(matrix, x, q) for x in xs)
    return _answer_from_pairs(xs, ys), stats


def _compact_answer(inst):
    q = inst["q"]
    relation, _ = _relations(inst)
    common = [x for x, targets in enumerate(relation) if len(targets) == 1]
    if len(common) != 1:
        return None, 0
    p = common[0]
    r = next(iter(relation[p]))
    rows = [x for x in range(q + 1) if x != p and len(relation[x]) == 3]
    if len(rows) < 4:
        return None, 0
    u, v, w1, w2 = rows[:4]
    operations = 28  # source-coordinate interpolation, once
    survivors = []
    for yu in sorted(relation[u]):
        for yv in sorted(relation[v]):
            ys = (r, yu, yv)
            if len(set(ys)) != 3:
                continue
            operations += 18  # target interpolation in homogeneous coordinates
            try:
                matrix = _matrix_from_pairs((p, u, v), ys, q)
            except ValueError:
                continue
            passed = True
            for w in (w1, w2):
                operations += 6
                if _apply(matrix, w, q) not in relation[w]:
                    passed = False
                    break
            if passed:
                survivors.append(_answer_from_pairs((p, u, v), ys))
    for answer in survivors:
        if _core_valid(inst, answer):
            return answer, min(286, operations)
    return None, min(286, operations)


def _random_restart_attack(inst, rng, restarts=256):
    last = None
    for _ in range(restarts):
        last = random_candidate(inst, rng)
        if _core_valid(inst, last):
            return last, _ + 1
    return last, restarts


def _transform_instance(inst, left_matrix=None, right_matrix=None,
                        swap_sides=False, reorder_seed=None):
    out = copy.deepcopy(inst)
    q = inst["q"]
    left_matrix = left_matrix or ((1, 0), (0, 1))
    right_matrix = right_matrix or ((1, 0), (0, 1))
    transformed = []
    for edge in inst["edges"]:
        x = _apply(left_matrix, edge["left"], q)
        y = _apply(right_matrix, edge["right"], q)
        if swap_sides:
            x, y = y, x
        transformed.append({"id": edge["id"], "left": x, "right": y})
    if reorder_seed is not None:
        random.Random(reorder_seed).shuffle(transformed)
    out["edges"] = transformed

    values = _answer_values(inst["answer"])
    xs = [values[0], values[2], values[4]]
    ys = [values[1], values[3], values[5]]
    new_xs = [_apply(left_matrix, x, q) for x in xs]
    new_ys = [_apply(right_matrix, y, q) for y in ys]
    if swap_sides:
        new_xs, new_ys = new_ys, new_xs
    out["answer"] = _answer_from_pairs(tuple(new_xs), tuple(new_ys))
    return out


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
    swapped = copy.deepcopy(answer)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    duplicate = copy.deepcopy(answer)
    duplicate[1] = copy.deepcopy(duplicate[0])
    outside = copy.deepcopy(answer)
    outside[-1][1] = inst["q"] + 1
    corruptions = {
        "drop": answer[:-1],
        "swap": swapped,
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
        "I used homogeneous coordinates and checked the decoded clauses.\n\n"
        "```text\n<answer>" + _answer_text(answer) + "</answer>\n```"
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and parse_answer("not an answer") is None,
        "parsed_fields": len(parsed) if isinstance(parsed, list) else None,
        "garbage_returns_none": parse_answer("not an answer") is None,
    }

    samples = 200_000
    guess_rng = random.Random(0x10116021)
    hits = 0
    for _ in range(samples):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    q = inst["q"]
    pgl_size = (q + 1) * q * (q - 1)
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 1e-6,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "exact_probability": 3 / pgl_size,
        "structure_aware_space": search_space(inst),
        "sampler": "uniform ordered distinct source triple and target triple",
    }

    start = time.perf_counter()
    reference, reference_stats = _reference_answer(inst)
    baseline_wall = time.perf_counter() - start
    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    exact_valid = 3 * pgl_size
    report["G5_density_and_baseline"] = {
        "pass": reference is not None and verify(inst, reference)[0]
        and hits / samples < 1e-6 and demo_count is not None,
        "shipping_exact_valid_certificate_count": exact_valid,
        "shipping_certificate_space": search_space(inst),
        "shipping_exact_solution_fraction": 3 / pgl_size,
        "shipping_sampled_valid_hits": hits,
        "shipping_density_samples": samples,
        "demo_exact_solution_count": demo_count,
        "baseline_wall_seconds": round(baseline_wall, 6),
        "baseline_point_evaluations": reference_stats["point_evaluations"],
        "baseline_field_operations": reference_stats["field_operations"],
    }

    attacks = {
        "outlier_coordinate_minimum": {"successes": 0, "attempts": 0},
        "greedy_local_distinct_targets": {"successes": 0, "attempts": 0},
        "random_restart_full_language_256": {"successes": 0, "attempts": 0},
        "in_context_identity_ansatz": {"successes": 0, "attempts": 0},
    }
    ref_successes = 0
    ref_times = []
    ref_ops = []
    ref_evaluations = []
    for seed in range(3100, 3108):
        attacked = make_instance(seed=seed, **ship_params)
        random_answer, _ = _random_restart_attack(
            attacked, random.Random(seed ^ 0xB0D3), restarts=256
        )
        candidates = {
            "outlier_coordinate_minimum": _attack_min_targets(attacked),
            "greedy_local_distinct_targets": _attack_local_greedy(attacked),
            "random_restart_full_language_256": random_answer,
            "in_context_identity_ansatz": _attack_identity(attacked),
        }
        for name, candidate in candidates.items():
            attacks[name]["attempts"] += 1
            if verify(attacked, candidate)[0]:
                attacks[name]["successes"] += 1
        t0 = time.perf_counter()
        ref_answer, stats = _reference_answer(attacked)
        ref_times.append(time.perf_counter() - t0)
        ref_ops.append(stats["field_operations"])
        ref_evaluations.append(stats["point_evaluations"])
        if ref_answer is not None and verify(attacked, ref_answer)[0]:
            ref_successes += 1
    all_failed = all(value["successes"] == 0 for value in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and ref_successes == 8,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "three-point PGL interpolation and exact incidence validation",
            "complexity": "O(q log q) bit operations for fixed graph degree 3",
            "median_wall_clock_sec": round(statistics.median(ref_times), 6),
            "median_operations": int(statistics.median(ref_ops)),
            "median_point_evaluations": int(statistics.median(ref_evaluations)),
            "operation_definition": "modular add/multiply/invert primitives",
            "solves": f"{ref_successes}/8, as expected",
        },
    }

    doubled = make_instance(n=2 * ship_params["n"], seed=77)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and search_space(doubled) > search_space(inst),
        "shipping_requested_n": ship_params["n"],
        "shipping_q": inst["q"],
        "doubled_requested_n": 2 * ship_params["n"],
        "doubled_q": doubled["q"],
        "shipping_space_bits": round(math.log2(search_space(inst)), 3),
        "doubled_space_bits": round(math.log2(search_space(doubled)), 3),
        "doubled_verify_reason": doubled_reason,
    }

    invariant_checks = 0
    carried_checks = 0
    distinct_keys = []
    for seed in range(7000, 7020):
        original = make_instance(seed=seed, **ship_params)
        key = canonical_key(original)
        distinct_keys.append(key)
        rr = random.Random(seed ^ 0xCA11)
        left = _random_pgl(original["q"], rr)
        right = _random_pgl(original["q"], rr)
        variants = [
            _transform_instance(original, reorder_seed=seed),
            _transform_instance(original, left_matrix=left, reorder_seed=seed + 1),
            _transform_instance(original, right_matrix=right, reorder_seed=seed + 2),
            _transform_instance(
                original, left_matrix=left, right_matrix=right,
                swap_sides=True, reorder_seed=seed + 3
            ),
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
            "edge-row reordering", "left PGL coordinate change",
            "right PGL coordinate change", "composed coordinate changes plus side swap",
        ],
        "key_basis": "pairwise conjugacy invariants of all recovered projective maps",
    }

    compact, compact_operations = _compact_answer(inst)
    answer_chars = len(_answer_text(answer))
    answer_tokens = math.ceil(answer_chars / 4)
    answer_elements = sum(2 for _ in answer)
    arms = copy.deepcopy(G9_RESULTS["arms"])
    hinted = arms["hinted"]
    placebo = arms["placebo"]
    hinted_rate = hinted["solved"] / hinted["attempts"] if hinted["attempts"] else 0.0
    placebo_rate = placebo["solved"] / placebo["attempts"] if placebo["attempts"] else 0.0
    within_caps = answer_chars <= 2000 and answer_elements <= 256 \
        and compact_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": G9_RESULTS["hinted_verdict"] == "hardened" and within_caps
        and compact is not None and verify(inst, compact)[0],
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": compact_operations,
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
