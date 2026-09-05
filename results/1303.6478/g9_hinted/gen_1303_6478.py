"""Verified problem generator for arXiv:1303.6478.

The paper associates an integral cycle-closure map to a combinatorial type of
a tropical cover.  The graph-theoretic minor argument inside the proof of
Proposition 2.24 shows that a maximal minor indexed by the complement of a
spanning tree is the product of the corresponding edge weights.  (The
proposition is stated for rational covers because it compares cone weights;
the displayed minor argument itself uses only the connected graph and its
cycle basis.)  This module builds genuine trivalent covers made from a chain
of diamonds, forms that minor, and changes both integral lattice bases by
unimodular matrices.  The planted answer is carried through those determinant-
preserving changes; it is never recovered by solving the emitted matrix.
"""

from __future__ import annotations

import hashlib
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
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # The module remains standard-library-only.
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "integer_lattice",
    "computational_core": "graph",
    "certificate_form": "exact_symbolic",
    "native_objects": [
        "weighted trivalent tropical cover of the tropical line",
        "integral cycle-closure lattice map",
        "spanning tree and its complementary edge set",
    ],
    "verification_operations": [
        "exact graph connectivity and cycle-rank checks",
        "exact tropical balancing and Riemann-Hurwitz checks",
        "exact rational slope-times-length comparison",
        "fraction-free Bareiss determinant",
        "exact prime-exponent evaluation",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Definition 2.16 and Proposition 2.24 (the cycle-closure lattice map "
        "and its spanning-tree complementary-minor formula)"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The determinant of the cycle-closure minor is unchanged by integral "
        "basis changes and, in the fundamental-cycle basis of a spanning tree, "
        "is just the product of the complementary edge weights."
    ),
    "hardness_basis": (
        "Track B: fraction-free Bareiss elimination is an O(n^3) exact "
        "algorithm and uses 1,161,280 arithmetic update operations at shipping "
        "n=96 (0.095 seconds mean in the final measured eight-seed panel); the "
        "co-tree invariant in the proof of Proposition 2.24 reduces the intended "
        "route to 128 exact tally/output operations, while the dense 96x96 "
        "calculation is not executable by hand."
    ),
    "max_answer_tokens": 9,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (PROBLEM_PROFILE["intuition_type"] + ": "
                  + PROBLEM_PROFILE["intuition_description"]),
    "reduction": PROBLEM_PROFILE["reduction"],
}


# n is the number of independent diamond cycles and therefore the matrix size.
# The prime basis and answer length stay fixed after the demo rung: escalation
# grows the matrix haystack, not the exponent-vector needle.
DIFFICULTY = {
    "hard": {"n": 96, "mix_bound": 1},
}
SHIPPING_DIFFICULTY = "hard"


STRUCTURAL_HINT = (
    "A spanning tree makes the non-tree edge weights the pivot invariants of "
    "the cycle-closure map under integral basis changes."
)
PLACEBO_HINT = (
    "Careful tracking of the matrix rows and edge identifiers helps avoid "
    "ordinary indexing and transcription mistakes."
)


PRIME_PAIRS = ((7, 53), (13, 47), (17, 43), (19, 41), (23, 37), (29, 31))
PRIME_BASIS = tuple(sorted(p for pair in PRIME_PAIRS for p in pair))
DEGREE = 60

CERTIFICATE_LANGUAGE = {
    "description": (
        "A JSON list [e_0,...,e_11] of 12 nonnegative integers, each at most "
        "n, whose sum is n; it denotes the exact factorization "
        "abs(det M)=product(PRIME_BASIS[i]**e_i)."
    ),
    "bounds": {
        "length": len(PRIME_BASIS),
        "exponent_min": 0,
        "exponent_max": "n",
        "sum": "n",
        "candidate_count": "binomial(n+11,11)",
    },
}


NOTES = (
    "Definition 2.2 fixes morphisms of tropical curves, including integral "
    "slopes, balancing, Riemann-Hurwitz numbers and labels. Definitions 2.16 "
    "and 2.19 define the cycle-closing equations and their lattice index. The "
    "graph-theoretic argument in the proof of Proposition 2.24 identifies every "
    "nonzero maximal minor whose complement is a spanning tree with the product "
    "of the complementary edge weights; although the proposition's cone-weight "
    "comparison is stated for rational covers, that minor argument is genus-"
    "independent. Lemma 3.2 explains why these same lattice minors enter the local "
    "branch-map multiplicity. Theorem 3.3 proves constancy of the branch-map "
    "degree but does not give an algorithm for recovering a cover from branch "
    "data; that prior-triage family was therefore not used. The easy regimes "
    "are the one-dimensional star resolutions of Section 3.1, where one "
    "transposition merely cuts or joins cycles, and an already supplied "
    "combinatorial type, whose metric lengths follow directly from endpoint "
    "distance divided by edge weight. Here each chosen and unchosen branch "
    "weight is drawn symmetrically from the same prime pair, the rows and "
    "columns are mixed independently, and matrix-entry, row-content, "
    "column-content, small/large-branch, and random-composition attacks fail. "
    "Bareiss elimination is disclosed and measured as the successful Track-B "
    "reference algorithm."
)


# Filled from the script-owned hardening runs.  These are diagnostics only;
# G9 gates the answer and intended-route caps, not oracle success.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 0, "attempts": 0},
    "placebo": {"solved": 0, "attempts": 0},
    "hinted_verdict": "unrun",
}


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_params(n, mix_bound):
    if not _is_int(n) or n < 4:
        raise ValueError("n must be an integer at least 4")
    if not _is_int(mix_bound) or not 1 <= mix_bound <= 16:
        raise ValueError("mix_bound must be an integer from 1 through 16")


def _q(num, den=1):
    if not _is_int(num) or not _is_int(den) or den == 0:
        raise ValueError("invalid rational")
    if den < 0:
        num, den = -num, -den
    g = math.gcd(num, den)
    return [num // g, den // g]


def _q_value(value):
    if (not isinstance(value, list) or len(value) != 2
            or not _is_int(value[0]) or not _is_int(value[1])
            or value[1] <= 0 or math.gcd(abs(value[0]), value[1]) != 1):
        raise ValueError("rational must be a reduced [numerator,denominator] pair")
    return value[0], value[1]


def _matmul(A, B):
    rows, inner, cols = len(A), len(B), len(B[0])
    if not A or len(A[0]) != inner:
        raise ValueError("matrix shape mismatch")
    out = [[0] * cols for _ in range(rows)]
    for i in range(rows):
        for k, aik in enumerate(A[i]):
            if aik:
                bk = B[k]
                for j in range(cols):
                    out[i][j] += aik * bk[j]
    return out


def _unit_lower(n, rng, bound):
    return [[(1 if i == j else rng.randint(-bound, bound) if j < i else 0)
             for j in range(n)] for i in range(n)]


def _unit_upper(n, rng, bound):
    return [[(1 if i == j else rng.randint(-bound, bound) if j > i else 0)
             for j in range(n)] for i in range(n)]


def _scrambled_minor(weights, rng, mix_bound):
    """Return L*diag(weights)*R for unit triangular integral L,R."""
    n = len(weights)
    left = _unit_lower(n, rng, mix_bound)
    right = _unit_upper(n, rng, mix_bound)
    scaled_right = [[weights[i] * x for x in right[i]] for i in range(n)]
    return _matmul(left, scaled_right)


def _make_cover(n, rng):
    vertices = [{
        "id": 0, "target": "c", "position": [0, 1], "genus": 29,
        "labels": [],
    }]
    edges = []
    chosen_weights = []
    next_edge = 0

    def add_edge(a, b, ray, weight, length, cotree=False):
        nonlocal next_edge
        edges.append({
            "id": next_edge, "a": a, "b": b, "ray": ray,
            "weight": weight, "length": length, "cotree": bool(cotree),
        })
        next_edge += 1

    # The center has u-degree 60, v-profile (1,59), and w-degree 60.
    add_edge(0, None, "v", 1, None)
    add_edge(0, None, "v", 59, None)
    add_edge(0, None, "w", DEGREE, None)

    previous = 0
    label = 1
    for stage in range(n):
        split = 2 * stage + 1
        merge = split + 1
        vertices.append({
            "id": split, "target": "u", "position": [2 * stage + 1, 1],
            "genus": 0, "labels": [label],
        })
        label += 1
        vertices.append({
            "id": merge, "target": "u", "position": [2 * stage + 2, 1],
            "genus": 0, "labels": [label],
        })
        label += 1

        # A trunk joins the previous merge (or the center) to this split.
        add_edge(previous, split, "u", DEGREE, _q(1, DEGREE))

        low, high = rng.choice(PRIME_PAIRS)
        selected_low = bool(rng.getrandbits(1))
        branch_data = [(low, selected_low), (high, not selected_low)]
        rng.shuffle(branch_data)  # Edge order carries no planting signal.
        for weight, selected in branch_data:
            add_edge(split, merge, "u", weight, _q(1, weight), selected)
            if selected:
                chosen_weights.append(weight)
        previous = merge

    add_edge(previous, None, "u", DEGREE, None)
    return vertices, edges, chosen_weights


def make_instance(n, seed=0, mix_bound=1, **params):
    """Construct a cover and carry a known co-tree determinant certificate."""
    if params:
        raise TypeError("unknown parameters: " + ", ".join(sorted(params)))
    _validate_params(n, mix_bound)
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    vertices, edges, chosen = _make_cover(n, rng)
    matrix = _scrambled_minor(chosen, rng, mix_bound)
    counts = [chosen.count(p) for p in PRIME_BASIS]
    tree_edges = [e["id"] for e in edges if e["b"] is not None and not e["cotree"]]
    cotree_edges = [e["id"] for e in edges if e["cotree"]]
    return {
        "paper": "arXiv:1303.6478",
        "n": n,
        "mix_bound": mix_bound,
        "degree": DEGREE,
        "genus": n + 29,
        "ramification_profile": {"u": [DEGREE], "v": [1, 59], "w": [DEGREE]},
        "prime_basis": list(PRIME_BASIS),
        "vertices": vertices,
        "edges": edges,
        "spanning_tree_edges": tree_edges,
        "cotree_edges": cotree_edges,
        "cycle_closure_minor": matrix,
        "answer": counts,
    }


def _vertex_text(vertex):
    labels = "-" if not vertex["labels"] else ",".join(map(str, vertex["labels"]))
    return (f"V{vertex['id']} target={vertex['target']} "
            f"pos={vertex['position'][0]}/{vertex['position'][1]} "
            f"genus={vertex['genus']} labels={labels}")


def _edge_text(edge):
    endpoint = "END" if edge["b"] is None else f"V{edge['b']}"
    length = "infinity" if edge["length"] is None else f"{edge['length'][0]}/{edge['length'][1]}"
    return (f"E{edge['id']} V{edge['a']} {endpoint} ray={edge['ray']} "
            f"weight={edge['weight']} length={length}")


def render(inst):
    """Render a complete, exact problem statement."""
    vertex_block = "\n".join(_vertex_text(v) for v in inst["vertices"])
    edge_block = "\n".join(_edge_text(e) for e in inst["edges"])
    matrix_block = "\n".join(" ".join(map(str, row))
                             for row in inst["cycle_closure_minor"])
    tree = ", ".join(f"E{x}" for x in inst["spanning_tree_edges"])
    cotree = ", ".join(f"E{x}" for x in inst["cotree_edges"])
    primes = ", ".join(map(str, inst["prime_basis"]))
    statement = f"""Tropical cycle-closure determinant

The target tropical line is a tripod with center c and rays u, v, w.  A source
vertex mapped to c has the three ray directions; a source vertex at a positive
coordinate on u has a left and a right direction.  Every finite source edge is
mapped linearly to its listed ray with positive integer slope called its weight.
Its target distance equals weight times source length.  At each source vertex,
the sums of adjacent weights in every target direction must agree; their common
value is the local degree.  The Riemann-Hurwitz number is

  r(V) = valence(V) + 2*genus(V) - 2
         - local_degree(V)*(target_valence-2).

It must be nonnegative and equal the number of labels at V.  Ends have infinite
length.  These rules define the tropical cover below; all integers and rational
lengths are exact.  Vertex and edge identifiers are zero-based labels only.

Degree: {inst['degree']}
Source genus: {inst['genus']}
Ramification profile: u={inst['ramification_profile']['u']}, v={inst['ramification_profile']['v']}, w={inst['ramification_profile']['w']}

VERTICES
{vertex_block}

EDGES
{edge_block}

Delete the following finite edges to obtain the stated spanning tree T:
co-tree edges = {cotree}
Equivalently, the finite edges of T are:
tree edges = {tree}

For each integral cycle, its closure equation is the signed sum of
weight(edge)*length(edge).  Restrict the cycle-closure homomorphism to the
co-tree edge lattice.  An integral lattice basis means a basis over the
integers; a change between two such bases has determinant +1 or -1.  The
following {inst['n']} by {inst['n']} integer matrix M represents that restricted
homomorphism after independent changes of integral lattice bases in its domain
and codomain:

MATRIX M (one row per line)
{matrix_block}

Find the exact prime factorization of abs(det(M)).  Use this fixed prime basis:

[{primes}]

Your answer must be a JSON list [e0,...,e11] of exactly 12 integers.  Each ei is
inclusive in 0..{inst['n']}, their sum must be exactly {inst['n']}, and
abs(det(M)) must equal product(prime_basis[i]**ei).  Order is the displayed
prime-basis order; repeats and any other primes are forbidden.

Give your final answer inside <answer></answer> tags, as one JSON integer list.
Example of syntax only (not the answer): <answer>[{inst['n']},0,0,0,0,0,0,0,0,0,0,0]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text):
    """Extract the tagged JSON exponent vector; never raise on malformed text."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    if not matches:
        return None
    payload = matches[-1].strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", payload,
                         flags=re.IGNORECASE | re.DOTALL)
    if fence:
        payload = fence.group(1).strip()
    try:
        value = json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(value, list) or any(not _is_int(x) for x in value):
        return None
    return value


def _bareiss_det(matrix, with_stats=False):
    """Exact fraction-free determinant and a transparent arithmetic count."""
    if not isinstance(matrix, list) or not matrix:
        raise ValueError("matrix must be nonempty")
    n = len(matrix)
    if any(not isinstance(row, list) or len(row) != n for row in matrix):
        raise ValueError("matrix must be square")
    if any(not _is_int(x) for row in matrix for x in row):
        raise ValueError("matrix entries must be integers")
    if n == 1:
        return (matrix[0][0], {"arithmetic_updates": 0, "row_swaps": 0}) if with_stats else matrix[0][0]
    M = [row[:] for row in matrix]
    sign, previous, updates, swaps = 1, 1, 0, 0
    for k in range(n - 1):
        if M[k][k] == 0:
            pivot = next((r for r in range(k + 1, n) if M[r][k]), None)
            if pivot is None:
                result = 0
                stats = {"arithmetic_updates": updates, "row_swaps": swaps}
                return (result, stats) if with_stats else result
            M[k], M[pivot] = M[pivot], M[k]
            sign = -sign
            swaps += 1
        pivot_value = M[k][k]
        for i in range(k + 1, n):
            mik = M[i][k]
            row_i = M[i]
            row_k = M[k]
            for j in range(k + 1, n):
                row_i[j] = (row_i[j] * pivot_value - mik * row_k[j]) // previous
                updates += 4  # two products, one subtraction, one exact division
            row_i[k] = 0
        previous = pivot_value
    result = sign * M[-1][-1]
    stats = {"arithmetic_updates": updates, "row_swaps": swaps}
    return (result, stats) if with_stats else result


def _is_prime(value):
    if not _is_int(value) or value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    d = 3
    while d * d <= value:
        if value % d == 0:
            return False
        d += 2
    return True


def _connected(vertices, bounded_edges):
    if not vertices:
        return False
    adjacency = {v: [] for v in vertices}
    for edge in bounded_edges:
        adjacency[edge["a"]].append(edge["b"])
        adjacency[edge["b"]].append(edge["a"])
    seen, stack = set(), [next(iter(vertices))]
    while stack:
        v = stack.pop()
        if v in seen:
            continue
        seen.add(v)
        stack.extend(adjacency[v])
    return seen == set(vertices)


def _tree_check(vertex_ids, edges):
    if len(edges) != len(vertex_ids) - 1:
        return False
    parent = {v: v for v in vertex_ids}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for edge in edges:
        a, b = find(edge["a"]), find(edge["b"])
        if a == b:
            return False
        parent[a] = b
    return len({find(v) for v in vertex_ids}) == 1


def _validate_cover(inst):
    """Validate the native tropical object and return its selected weights."""
    try:
        n = inst["n"]
        if not _is_int(n) or n < 1 or inst["degree"] != DEGREE:
            return False, "invalid size or degree", None
        if inst["prime_basis"] != list(PRIME_BASIS):
            return False, "invalid prime basis", None
        vertices, edges = inst["vertices"], inst["edges"]
        if not isinstance(vertices, list) or not isinstance(edges, list):
            return False, "vertices and edges must be lists", None
        by_id = {}
        for vertex in vertices:
            vid = vertex.get("id")
            if not _is_int(vid) or vid in by_id:
                return False, "vertex identifiers must be distinct integers", None
            if vertex.get("target") not in ("c", "u"):
                return False, "invalid vertex target", None
            _q_value(vertex.get("position"))
            if not _is_int(vertex.get("genus")) or vertex["genus"] < 0:
                return False, "invalid vertex genus", None
            if (not isinstance(vertex.get("labels"), list)
                    or any(not _is_int(x) or x < 1 for x in vertex["labels"])):
                return False, "invalid vertex labels", None
            by_id[vid] = vertex
        centers = [v for v in vertices if v["target"] == "c"]
        if len(centers) != 1:
            return False, "the cover must have one vertex above c", None

        edge_ids, bounded, incidence = set(), [], {v: [] for v in by_id}
        profiles = {"u": [], "v": [], "w": []}
        for edge in edges:
            eid = edge.get("id")
            if not _is_int(eid) or eid in edge_ids:
                return False, "edge identifiers must be distinct integers", None
            edge_ids.add(eid)
            a, b, ray, weight = edge.get("a"), edge.get("b"), edge.get("ray"), edge.get("weight")
            if a not in by_id or (b is not None and b not in by_id) or a == b:
                return False, "invalid edge endpoint", None
            if ray not in profiles or not _is_int(weight) or weight <= 0:
                return False, "invalid edge ray or weight", None
            incidence[a].append(edge)
            if b is None:
                if edge.get("length") is not None or edge.get("cotree"):
                    return False, "an end must be infinite and cannot be a co-tree edge", None
                profiles[ray].append(weight)
            else:
                incidence[b].append(edge)
                bounded.append(edge)
                if ray != "u":
                    return False, "every bounded edge must map to u", None
                ln, ld = _q_value(edge.get("length"))
                if ln <= 0:
                    return False, "bounded lengths must be positive", None
                pa = by_id[a]["position"]
                pb = by_id[b]["position"]
                delta_num = abs(pa[0] * pb[1] - pb[0] * pa[1])
                delta_den = pa[1] * pb[1]
                if weight * ln * delta_den != ld * delta_num:
                    return False, "slope times length does not equal target distance", None

        if not _connected(by_id, bounded):
            return False, "source graph is disconnected", None
        labels, rh_sum = [], 0
        for vid, vertex in by_id.items():
            groups = {}
            for edge in incidence[vid]:
                if vertex["target"] == "c":
                    direction = edge["ray"]
                else:
                    if edge["ray"] != "u":
                        return False, "a ray vertex has an edge on the wrong target ray", None
                    if edge["b"] is None:
                        direction = "right"
                    else:
                        other = edge["b"] if edge["a"] == vid else edge["a"]
                        p, q = vertex["position"], by_id[other]["position"]
                        cmp = q[0] * p[1] - p[0] * q[1]
                        if cmp == 0:
                            return False, "an edge has equal target endpoints", None
                        direction = "right" if cmp > 0 else "left"
                groups[direction] = groups.get(direction, 0) + edge["weight"]
            required = ("u", "v", "w") if vertex["target"] == "c" else ("left", "right")
            if set(groups) != set(required) or len(set(groups.values())) != 1:
                return False, "tropical balancing fails", None
            local_degree = next(iter(groups.values()))
            target_valence = 3 if vertex["target"] == "c" else 2
            rh = len(incidence[vid]) + 2 * vertex["genus"] - 2 - local_degree * (target_valence - 2)
            if rh < 0 or len(vertex["labels"]) != rh:
                return False, "Riemann-Hurwitz number or label count fails", None
            if vertex["target"] == "c" and rh != 0:
                return False, "the center vertex is not trivalent-type (RH zero)", None
            if vertex["target"] != "c" and (len(incidence[vid]) != 3 or vertex["genus"] != 0 or rh != 1):
                return False, "a moving vertex is not trivalent genus zero", None
            labels.extend(vertex["labels"])
            rh_sum += rh
        if sorted(labels) != list(range(1, rh_sum + 1)):
            return False, "labels are not exactly 1 through the total RH number", None

        cycle_rank = len(bounded) - len(vertices) + 1
        if cycle_rank != n:
            return False, "cycle rank does not equal n", None
        source_genus = cycle_rank + sum(v["genus"] for v in vertices)
        if source_genus != inst["genus"]:
            return False, "source genus is inconsistent", None
        expected_profile = {key: sorted(value) for key, value in inst["ramification_profile"].items()}
        if {key: sorted(value) for key, value in profiles.items()} != expected_profile:
            return False, "ramification profile is inconsistent", None
        if any(sum(values) != DEGREE for values in profiles.values()):
            return False, "end weights do not have the stated degree", None

        cotree = [e for e in bounded if e.get("cotree") is True]
        tree = [e for e in bounded if e.get("cotree") is False]
        if [e["id"] for e in tree] != inst["spanning_tree_edges"]:
            return False, "spanning-tree edge list is inconsistent", None
        if [e["id"] for e in cotree] != inst["cotree_edges"]:
            return False, "co-tree edge list is inconsistent", None
        if len(cotree) != n or not _tree_check(set(by_id), tree):
            return False, "the stated complement is not a spanning tree", None
        weights = [e["weight"] for e in cotree]
        if any(weight not in PRIME_BASIS for weight in weights):
            return False, "a co-tree weight is outside the prime basis", None
        return True, "ok", weights
    except (KeyError, TypeError, ValueError, AttributeError):
        return False, "malformed tropical-cover instance", None


_ANALYSIS_CACHE = {}


def _analyze_instance(inst):
    entry = _ANALYSIS_CACHE.get(id(inst))
    if entry is not None and entry[0] is inst:
        return entry[1]
    ok, reason, weights = _validate_cover(inst)
    if not ok:
        result = (False, reason, None, None)
    else:
        matrix = inst.get("cycle_closure_minor")
        try:
            determinant = abs(_bareiss_det(matrix))
        except (TypeError, ValueError, ZeroDivisionError):
            result = (False, "malformed cycle-closure matrix", None, None)
        else:
            expected = math.prod(weights)
            if determinant != expected:
                result = (False, "matrix is not the promised co-tree closure minor", None, None)
            else:
                exponents = [weights.count(p) for p in PRIME_BASIS]
                result = (True, "ok", determinant, exponents)
    if len(_ANALYSIS_CACHE) >= 256:
        _ANALYSIS_CACHE.pop(next(iter(_ANALYSIS_CACHE)))
    _ANALYSIS_CACHE[id(inst)] = (inst, result)
    return result


def verify(inst, answer):
    """Accept every bounded prime-exponent witness equal to the exact minor."""
    if answer is None:
        return False, "answer is absent"
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "exponent vector is empty"
    expected_len = len(PRIME_BASIS)
    if len(answer) != expected_len:
        return False, f"expected {expected_len} exponents, got {len(answer)}"
    if any(not _is_int(x) for x in answer):
        return False, "every exponent must be an integer"
    n = inst.get("n") if isinstance(inst, dict) else None
    if not _is_int(n):
        return False, "instance has no valid n"
    if any(x < 0 or x > n for x in answer):
        return False, f"every exponent must lie in 0..{n}"
    if sum(answer) != n:
        return False, f"exponents must sum to {n}"
    ok, reason, determinant, _ = _analyze_instance(inst)
    if not ok:
        return False, reason
    candidate = math.prod(pow(p, exponent) for p, exponent in zip(PRIME_BASIS, answer))
    if candidate != determinant:
        return False, "prime-exponent factorization does not equal abs(det(M))"
    return True, "ok"


def random_candidate(inst, rng):
    """Sample a uniform weak composition of n into 12 bounded exponents."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    n, k = inst["n"], len(PRIME_BASIS)
    bars = sorted(rng.sample(range(n + k - 1), k - 1))
    positions = [-1] + bars + [n + k - 1]
    return [positions[i + 1] - positions[i] - 1 for i in range(k)]


def search_space(inst):
    return math.comb(inst["n"] + len(PRIME_BASIS) - 1, len(PRIME_BASIS) - 1)


def enumerate_all(inst):
    space = search_space(inst)
    if space > 100_000:
        return None
    n, k, count = inst["n"], len(PRIME_BASIS), 0

    def visit(prefix, remaining, slots):
        nonlocal count
        if slots == 1:
            candidate = prefix + [remaining]
            count += int(verify(inst, candidate)[0])
            return
        for value in range(remaining + 1):
            visit(prefix + [value], remaining - value, slots - 1)

    visit([], n, k)
    return count


def _cover_signature(inst):
    """Recover the rooted diamond chain without trusting storage order/IDs."""
    vertices = {v["id"]: v for v in inst["vertices"]}
    bounded = [e for e in inst["edges"] if e["b"] is not None]
    adjacency = {v: [] for v in vertices}
    for edge in bounded:
        adjacency[edge["a"]].append(edge)
        adjacency[edge["b"]].append(edge)
    centers = [v for v in vertices.values() if v["target"] == "c"]
    if len(centers) != 1:
        raise ValueError("not one rooted cover")
    previous = centers[0]["id"]
    candidates = adjacency[previous]
    if len(candidates) != 1:
        raise ValueError("center does not start one chain")
    edge = candidates[0]
    split = edge["b"] if edge["a"] == previous else edge["a"]
    signature = []
    seen = {edge["id"]}
    while True:
        forward = [e for e in adjacency[split] if e["id"] not in seen]
        if len(forward) != 2:
            raise ValueError("not a diamond split")
        endpoints = []
        for branch in forward:
            endpoints.append(branch["b"] if branch["a"] == split else branch["a"])
        if endpoints[0] != endpoints[1]:
            raise ValueError("diamond branches do not rejoin")
        merge = endpoints[0]
        selected = [e for e in forward if e.get("cotree")]
        unselected = [e for e in forward if not e.get("cotree")]
        if len(selected) != 1 or len(unselected) != 1:
            raise ValueError("diamond co-tree choice is invalid")
        signature.append((selected[0]["weight"], unselected[0]["weight"]))
        seen.update(e["id"] for e in forward)
        onward = [e for e in adjacency[merge] if e["id"] not in seen]
        if not onward:
            break
        if len(onward) != 1:
            raise ValueError("diamond chain branches")
        trunk = onward[0]
        seen.add(trunk["id"])
        split = trunk["b"] if trunk["a"] == merge else trunk["a"]
    return signature


def canonical_key(inst):
    payload = {
        "degree": inst["degree"],
        "profile": inst["ramification_profile"],
        "rooted_diamonds": _cover_signature(inst),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def escalate(params):
    params = dict(params)
    n = params.get("n")
    mix_bound = params.get("mix_bound", 1)
    _validate_params(n, mix_bound)
    # The 12-entry witness is independent of n, so there is always another
    # fixed-answer-length hardness step available.  Grow both the matrix and,
    # until its documented cap, the coefficient-mixing range; neither change
    # lengthens the answer.
    params["n"] = n + 64
    params["mix_bound"] = min(16, mix_bound + 1)
    return params


def _normalize_counts(values, n):
    values = [max(0, min(n, int(x))) for x in values[:len(PRIME_BASIS)]]
    values += [0] * (len(PRIME_BASIS) - len(values))
    total = sum(values)
    if total > n:
        for i in range(len(values) - 1, -1, -1):
            take = min(values[i], total - n)
            values[i] -= take
            total -= take
    elif total < n:
        for i in range(len(values)):
            take = min(n - values[i], n - total)
            values[i] += take
            total += take
            if total == n:
                break
    return values


def _valuation_counts(value):
    value = abs(value)
    counts = []
    for prime in PRIME_BASIS:
        count = 0
        while value and value % prime == 0:
            value //= prime
            count += 1
        counts.append(count)
    return counts


def _attack_uniform(inst, rng):
    n, k = inst["n"], len(PRIME_BASIS)
    return [n // k + int(i < n % k) for i in range(k)]


def _attack_smaller_branch(inst, rng):
    signature = _cover_signature(inst)
    values = [0] * len(PRIME_BASIS)
    for selected, other in signature:
        values[PRIME_BASIS.index(min(selected, other))] += 1
    return values


def _attack_diagonal(inst, rng):
    product = math.prod(abs(row[i]) or 1
                        for i, row in enumerate(inst["cycle_closure_minor"]))
    return _normalize_counts(_valuation_counts(product), inst["n"])


def _attack_row_contents(inst, rng):
    product = 1
    for row in inst["cycle_closure_minor"]:
        content = 0
        for value in row:
            content = math.gcd(content, abs(value))
        product *= max(1, content)
    return _normalize_counts(_valuation_counts(product), inst["n"])


def _attack_column_contents(inst, rng):
    product = 1
    matrix = inst["cycle_closure_minor"]
    for column in range(inst["n"]):
        content = 0
        for row in range(inst["n"]):
            content = math.gcd(content, abs(matrix[row][column]))
        product *= max(1, content)
    return _normalize_counts(_valuation_counts(product), inst["n"])


def _attack_first_nonzero(inst, rng):
    product = 1
    matrix = inst["cycle_closure_minor"]
    for column in range(inst["n"]):
        value = next((abs(matrix[row][column]) for row in range(inst["n"])
                      if matrix[row][column]), 1)
        product *= value
    return _normalize_counts(_valuation_counts(product), inst["n"])


def _attack_random_restart(inst, rng, restarts):
    ok, _, _, target = _analyze_instance(inst)
    if not ok:
        return _attack_uniform(inst, rng)
    candidate = None
    for _ in range(restarts):
        candidate = random_candidate(inst, rng)
        if candidate == target:
            return candidate
    return candidate


def _reference_algorithm(inst):
    start = time.perf_counter()
    determinant, stats = _bareiss_det(inst["cycle_closure_minor"], with_stats=True)
    value = abs(determinant)
    counts, factor_ops = [], 0
    for prime in PRIME_BASIS:
        exponent = 0
        while value % prime == 0:
            value //= prime
            exponent += 1
            factor_ops += 2
        factor_ops += 1
        counts.append(exponent)
    elapsed = time.perf_counter() - start
    stats["factor_trial_operations"] = factor_ops
    stats["total_exact_operations"] = stats["arithmetic_updates"] + factor_ops
    stats["unfactored_remainder"] = value
    stats["elapsed_sec"] = elapsed
    return counts, stats


def _transform_instance(inst, seed):
    """Relabel vertices/edges and change both matrix bases unimodularly."""
    rng = random.Random(seed)
    transformed = json.loads(json.dumps(inst))
    old_vertices = [v["id"] for v in transformed["vertices"]]
    new_vertices = old_vertices[:]
    rng.shuffle(new_vertices)
    vmap = dict(zip(old_vertices, new_vertices))
    for vertex in transformed["vertices"]:
        vertex["id"] = vmap[vertex["id"]]
    for edge in transformed["edges"]:
        edge["a"] = vmap[edge["a"]]
        if edge["b"] is not None:
            edge["b"] = vmap[edge["b"]]

    old_edges = [e["id"] for e in transformed["edges"]]
    new_edges = old_edges[:]
    rng.shuffle(new_edges)
    emap = dict(zip(old_edges, new_edges))
    for edge in transformed["edges"]:
        edge["id"] = emap[edge["id"]]
    rng.shuffle(transformed["vertices"])
    rng.shuffle(transformed["edges"])
    transformed["spanning_tree_edges"] = [emap[x] for x in inst["spanning_tree_edges"]]
    transformed["cotree_edges"] = [emap[x] for x in inst["cotree_edges"]]
    # Lists must follow the transformed storage order, which is semantically void.
    transformed["spanning_tree_edges"] = [e["id"] for e in transformed["edges"]
                                              if e["b"] is not None and not e["cotree"]]
    transformed["cotree_edges"] = [e["id"] for e in transformed["edges"] if e["cotree"]]

    M = [row[:] for row in transformed["cycle_closure_minor"]]
    n = len(M)
    for _ in range(8):
        a, b = rng.sample(range(n), 2)
        coefficient = rng.choice((-1, 1))
        if rng.getrandbits(1):
            M[a] = [x + coefficient * y for x, y in zip(M[a], M[b])]
        else:
            for row in M:
                row[a] += coefficient * row[b]
    if rng.getrandbits(1):
        M[0] = [-x for x in M[0]]
    transformed["cycle_closure_minor"] = M
    return transformed


def _answer_size(answer):
    blob = json.dumps(answer, separators=(",", ":"))
    atoms = sum(1 for _ in answer)
    return len(blob), (len(blob) + 3) // 4, atoms


def _worst_answer_size(n, slots):
    """Exact worst compact-JSON character count over weak compositions."""
    best = [-1] * (n + 1)
    best[0] = 0
    for _ in range(slots):
        nxt = [-1] * (n + 1)
        for used, score in enumerate(best):
            if score < 0:
                continue
            for value in range(n - used + 1):
                nxt[used + value] = max(
                    nxt[used + value], score + len(str(value)))
        best = nxt
    chars = 2 + (slots - 1) + best[n]  # brackets, commas, integer digits
    return chars, (chars + 3) // 4


def selftest():
    report = {
        "paper": "arXiv:1303.6478",
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
        "pass": not failures, "attempts": attempts, "failures": failures,
    }

    shipping = make_instance(seed=13036478, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = shipping["answer"]
    unequal = next((pair for pair in ((i, j) for i in range(len(planted))
                                      for j in range(i + 1, len(planted)))
                    if planted[pair[0]] != planted[pair[1]]), None)
    if unequal is None:
        raise AssertionError("shipping answer unexpectedly has equal exponents")
    swapped = planted[:]
    swapped[unequal[0]], swapped[unequal[1]] = swapped[unequal[1]], swapped[unequal[0]]
    out_of_range = planted[:]
    out_of_range[0] = shipping["n"] + 1
    corruptions = {
        "drop_one": planted[:-1],
        "swap_two_unequal": swapped,
        "duplicate_one": planted + [planted[-1]],
        "empty": [],
        "out_of_range": out_of_range,
    }
    corruption_results = {}
    for name, candidate in corruptions.items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
    reasons = {item["reason"] for item in corruption_results.values()}
    report["G2_rejects_corruption"] = {
        "pass": (all(item["rejected"] for item in corruption_results.values())
                 and len(reasons) == len(corruption_results)),
        "cases": corruption_results,
        "distinct_reasons": len(reasons),
    }

    realistic = ("The co-tree invariant gives the following exponents.\n<answer>\n"
                 "```json\n" + json.dumps(planted) + "\n```\n</answer>\n"
                 "I checked the factorization exactly.")
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == planted and parse_answer("no tagged answer") is None,
        "parsed": parsed,
    }

    guess_rng, guess_total, guess_hits = random.Random(0x13036478), 200_000, 0
    started = time.perf_counter()
    for _ in range(guess_total):
        guess_hits += int(verify(shipping, random_candidate(shipping, guess_rng))[0])
    guess_elapsed = time.perf_counter() - started
    exact_density = 1.0 / search_space(shipping)
    report["G4_guess_resistance"] = {
        "pass": guess_hits / guess_total < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_hits / guess_total,
        "exact_probability": exact_density,
        "structure_aware_space": search_space(shipping),
        "sampling_rule": "uniform weak compositions of n into the 12 stated prime exponents",
        "wall_clock_sec": round(guess_elapsed, 6),
    }

    attacks = {
        "uniform_prime_counts": _attack_uniform,
        "smaller_branch_outlier": _attack_smaller_branch,
        "diagonal_valuation": _attack_diagonal,
        "row_content_greedy": _attack_row_contents,
        "column_content_greedy": _attack_column_contents,
        "first_nonzero_column_ansatz": _attack_first_nonzero,
        "random_restart_4096": lambda inst, rng: _attack_random_restart(inst, rng, 4096),
    }
    attack_results = {name: {"successes": 0, "attempts": 0}
                      for name in attacks}
    attack_elapsed = {name: 0.0 for name in attacks}
    reference_successes, reference_elapsed, reference_ops = 0, 0.0, []
    reference_updates, reference_swaps = [], []
    compact_successes = 0
    attack_seeds = list(range(8100, 8108))
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        for offset, (name, attack) in enumerate(attacks.items()):
            rng = random.Random(seed * 1009 + offset)
            t0 = time.perf_counter()
            candidate = attack(inst, rng)
            attack_elapsed[name] += time.perf_counter() - t0
            attack_results[name]["successes"] += int(verify(inst, candidate)[0])
            attack_results[name]["attempts"] += 1
        candidate, stats = _reference_algorithm(inst)
        reference_elapsed += stats["elapsed_sec"]
        reference_ops.append(stats["total_exact_operations"])
        reference_updates.append(stats["arithmetic_updates"])
        reference_swaps.append(stats["row_swaps"])
        reference_successes += int(verify(inst, candidate)[0])
        signature = _cover_signature(inst)
        compact = [sum(selected == p for selected, _ in signature) for p in PRIME_BASIS]
        compact_successes += int(verify(inst, compact)[0])
    for name in attacks:
        attack_results[name]["wall_clock_sec_total_8"] = round(attack_elapsed[name], 6)
    all_failed = all(item["successes"] == 0 for item in attack_results.values())
    reference = {
        "name": "fraction-free Bareiss determinant followed by division over the fixed prime basis",
        "complexity": "O(n^3) exact integer arithmetic plus O(n+12) exact divisions",
        "wall_clock_sec_total_8": round(reference_elapsed, 6),
        "wall_clock_sec_mean": round(reference_elapsed / len(attack_seeds), 6),
        "operations_mean": sum(reference_ops) // len(reference_ops),
        "operations_min": min(reference_ops),
        "operations_max": max(reference_ops),
        "bareiss_updates_mean": sum(reference_updates) // len(reference_updates),
        "row_swaps_total": sum(reference_swaps),
        "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
    }
    intended_operations = shipping["n"] + 2 * len(PRIME_BASIS) + 8
    report["G6_adversary_panel"] = {
        "pass": (all_failed and reference_successes == len(attack_seeds)
                 and compact_successes == len(attack_seeds)),
        "attacks": attack_results,
        "reference_algorithm": reference,
        "compact_route": {
            "name": "co-tree minor identity from the proof of Proposition 2.24, then prime tally",
            "worst_case_exact_operations": intended_operations,
            "solves": f"{compact_successes}/{len(attack_seeds)}, as expected",
        },
    }

    strongest = max(attack_elapsed, key=attack_elapsed.get)
    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline_cost"] = {
        "pass": exact_density < 1e-6 and all_failed and reference_successes == 8,
        "exact_valid_answers": 1,
        "exact_density_at_shipping": exact_density,
        "sampled_density_at_shipping": guess_hits / guess_total,
        "density_hits": guess_hits,
        "density_samples": guess_total,
        "candidate_space": search_space(shipping),
        "strongest_failing_attack": strongest,
        "attack_wall_clock_sec_total_8": round(attack_elapsed[strongest], 6),
        "attack_candidate_evaluations_total_8": 4096 * 8,
        "reference_algorithm_operations_mean": reference["operations_mean"],
        "reference_algorithm_wall_clock_sec_mean": reference["wall_clock_sec_mean"],
        "demo_exact_valid_answers": demo_count,
        "demo_candidate_space": search_space(demo),
    }

    doubled = make_instance(n=2 * shipping["n"], mix_bound=shipping["mix_bound"], seed=707)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": doubled_ok and len(doubled["cycle_closure_minor"]) == 2 * shipping["n"],
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "shipping_matrix_entries": shipping["n"] ** 2,
        "doubled_matrix_entries": doubled["n"] ** 2,
        "verify_reason": doubled_reason,
    }

    invariance_checks, carried_checks, failures = 0, 0, []
    for seed in range(20):
        inst = make_instance(seed=9000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        transformed = _transform_instance(inst, 12000 + seed)
        invariance_checks += 1
        if canonical_key(inst) != canonical_key(transformed):
            failures.append({"seed": seed, "reason": "key changed under relabelling/basis change"})
        carried_checks += 1
        ok, reason = verify(transformed, inst["answer"])
        if not ok:
            failures.append({"seed": seed, "reason": "carried witness failed: " + reason})
    unrelated = [canonical_key(make_instance(seed=20000 + seed,
                 **DIFFICULTY[SHIPPING_DIFFICULTY])) for seed in range(20)]
    distinct = len(set(unrelated))
    report["G8_canonical_key"] = {
        "pass": not failures and distinct == 20,
        "invariance_checks": invariance_checks,
        "invariance_failures": failures,
        "carried_witness_checks": carried_checks,
        "unrelated_instances": 20,
        "distinct_keys": distinct,
        "symmetries_tested": [
            "vertex renumbering", "edge renumbering", "vertex/edge storage reordering",
            "parallel-branch storage swaps", "unimodular row basis changes",
            "unimodular column basis changes", "row sign change",
        ],
    }

    chars, tokens, atoms = _answer_size(shipping["answer"])
    worst_chars, worst_tokens = _worst_answer_size(
        shipping["n"], len(PRIME_BASIS))
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    within_caps = (worst_chars <= 2000 and atoms <= 256
                   and intended_operations <= 300
                   and PROBLEM_PROFILE["max_answer_tokens"] == worst_tokens)
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": atoms,
        "worst_case_answer_chars": worst_chars,
        "worst_case_answer_tokens": worst_tokens,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["pass"] = all(gate.get("pass") is True for gate in gates)
    report["all_passed"] = report["pass"]
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
