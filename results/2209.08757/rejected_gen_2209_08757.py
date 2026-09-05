"""Exact Track-B Path Set Packing generator for arXiv:2209.08757.

The paper defines Path Set Packing on an undirected graph and explicitly notes
that it is polynomial-time solvable when the host graph is a tree.  This module
uses the smallest useful tree, a star.  A length-two path through the centre is
an edge of a bipartite graph on the star's leaves, so path packing is matching.

Two projective-linear permutations of P^1(F_q) are composed so that their union
is one even cycle.  Either alternating edge class is a perfect path packing.
The answer is a normalized 2 by 2 matrix over F_q, not a list of q+1 path IDs;
the verifier expands it and checks the actual host-graph edges exactly.

Generation is deterministic in (n, seed, params), uses only a local
random.Random(seed), and never solves the instance it emits.
"""

from __future__ import annotations

from collections import deque
import json
import math
import os
import random
import re
import sys
import time
from typing import Any


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # pragma: no cover - this family has a stdlib-only path
    exact_matrices = rationals = None


TRACK: str = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_field",
    "computational_core": "graph",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "an undirected star graph",
        "simple length-two paths through the star centre",
        "a normalized 2 by 2 projective-linear matrix over GF(q)",
    ],
    "verification_operations": [
        "exact modular matrix determinant and normalization",
        "exact projective-linear evaluation over GF(q)",
        "candidate-path membership lookup",
        "exact host-edge collision scan",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "The leaf-incidence graph of the displayed star paths is one even "
        "cycle, and its two alternating edge classes are projective-linear "
        "permutations; without seeing that symmetry, one must run matching "
        "and reconstruct a matrix from the expanded packing."
    ),
    "hardness_basis": (
        "Track B: Section 1.1 and the polynomial forest subroutine in Section "
        "5.1 make tree-host Path Set Packing polynomial; at shipping q=1009 "
        "the implemented O(VE) augmenting-path matching reference used a "
        "measured mean 16,241 edge/field operations and 0.002614 seconds, while "
        "the alternating-cycle/projective route needs at most 92 exact "
        "operations after the symmetry is seen."
    ),
    "max_answer_tokens": 8,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 5},
    "easy": {"n": 1009},
    "medium": {"n": 2003},
    "hard": {"n": 4001},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "View the star paths through their bipartite leaf-incidence cycle, whose "
    "alternating-edge symmetry is projective-linear."
)
PLACEBO_HINT = (
    "Approach the displayed star paths carefully, keeping each leaf label and "
    "finite-field convention consistently organized."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One JSON object containing a normalized invertible 2 by 2 matrix "
        "over GF(q): four residues in 0..q-1, with the first nonzero "
        "row-major entry equal to 1.  There are exactly q(q^2-1) candidates."
    ),
    "bounds": {
        "rows": 2,
        "columns": 2,
        "atomic_entries": 4,
        "entry_range": "0..q-1",
        "normalization": "first nonzero row-major entry is 1",
    },
}

NOTES = r"""
STEP 0 and paper grounding.  Section 1.1 defines Path Set Packing exactly: the
input is a finite simple undirected graph G, a collection P of simple paths in
G, and k; a witness is at least k pairwise edge-disjoint paths.  Section 1.2
states the equivalent conflict-graph independent-set view.  Theorem 1 proves
W[1]-hardness for vertex-cover number, and its reduction in Section 3 asks for
k(n-1)+binom(k,2) paths.  Theorem 2 proves W[1]-hardness for pathwidth plus
maximum degree plus solution size and asks for k+binom(k,2) paths.  Those
reductions are legitimate Track-A worst-case results, but neither proves that
a planted random distribution is hard, and the first makes the witness grow
with the source haystack.  This module therefore does not make a Track-A claim.

The paper's easy results were checked before construction.  Section 1.1 says
PSP is polynomial-time solvable when G is a tree.  Section 5.1 restates the EPT
maximum-independent-set subroutine and Corollary 2 says a maximum path packing
in a forest is computable in polynomial time.  Theorem 3 gives an FPT algorithm
for feedback-vertex number plus maximum degree; Theorem 4 gives an FPT
4-approximation by feedback-edge number; Theorem 5 is FPT for treewidth plus
maximum degree plus maximum path length.  Our host is a star, so hiding this
algorithm would make a false Track-A claim.  Here it is the Track-B reference.

Native construction.  The projective line P^1(F_q) is the q residues plus one
point INF.  A nonsingular matrix acts on it by x -> (a*x+b)/(c*x+d), with the
usual exact rules at a zero denominator and at INF.  A Singer element is chosen
with one orbit of length q+1.  A seed selects a coprime power, then independent
random projective coordinate changes A and B turn the identity and that power
into M0=B*A^-1 and M1=B*S^e*A^-1.  Their graphs are two perfect matchings and
their union is one 2(q+1)-cycle.  Each pair (x,y) becomes the native simple path
L_x--C--R_y in a star.  Either M0 or M1 therefore expands to q+1 pairwise
edge-disjoint paths.  The generator knows M0 by composition of identities; it
never runs matching on the emitted instance.

Certificate and compact route.  The witness is a normalized matrix, a compact
exact description of q+1 actual paths.  Verification evaluates it at every
projective point, looks up each candidate path, materializes its two star
edges, and rejects any collision.  For the intended route, traverse five edges
of the single incidence cycle and take the three edges of one parity.  Three
distinct projective point correspondences determine one PGL(2,q) matrix by a
3 by 4 homogeneous elimination.  This costs at most 92 exact operations after
the cycle symmetry is recognized, independent of q.  The mechanical reference
runs augmenting-path bipartite matching and then the same interpolation.

Hardening against cheap attacks.  Every left and right leaf has degree exactly
two, so degree/frequency outliers do not exist and both alternating matchings
come from the same distribution.  The first two displayed edges are placed at
cycle positions zero and three; display-order greedy accepts both and thereby
strands the intervening vertex, so it cannot complete a perfect packing.  Both
valid transformations are forced to be non-affine, defeating the obvious
two-point affine ansatz.  Uniform random restart samples normalized PGL
matrices, not malformed 4-tuples, so its prior is exactly the declared
certificate language.

Canonicalization.  Reordering paths is irrelevant.  A projective relabelling U
of left coordinates and V of right coordinates changes each solution M to
V*M*U^-1.  Decomposing the public even cycle into its two alternating
matchings and interpolating them gives relative transformation H=M1^-1*M0.
The scalar- and conjugacy-invariant value trace(H)^2/det(H), also unchanged by
H -> H^-1, is the canonical variant key.  G8 tests path reordering, independent
left/right projective relabelling, side exchange, and their composition.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_G4_SAMPLES = 200_000
_ATTACK_SEEDS = 8
_ENUMERATION_CAP = 200_000
_SINGER_CACHE: dict[int, tuple[int, int, int, int]] = {}
_REP_CACHE: dict[int, list[tuple[int, int]]] = {}
_PAIR_CACHE: dict[int, tuple[dict, dict[tuple[int, int], int]]] = {}

# Filled after the three script-owned hardening runs.  These numbers are
# diagnostic only; G9's gate is the answer/route cap.
_ORACLE_EVIDENCE = {
    "bare": {"solved": 3, "attempts": 3, "api_errors": 0},
    "hinted": {"solved": 0, "attempts": 0, "api_errors": 4},
    "placebo": {"solved": 0, "attempts": 0, "api_errors": 4},
    "hinted_verdict": "unavailable: OpenRouter HTTP 403 key limit",
}


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    divisor = 3
    while divisor * divisor <= n:
        if n % divisor == 0:
            return False
        divisor += 2
    return True


def _next_prime(n: int) -> int:
    candidate = max(5, n)
    if candidate % 2 == 0:
        candidate += 1
    while not _is_prime(candidate):
        candidate += 2
    return candidate


def _checked_prime(value: object) -> int:
    if not _is_int(value) or value < 5:
        raise ValueError("n must be a prime integer at least 5")
    value = int(value)
    if not _is_prime(value):
        raise ValueError("n must be prime")
    return value


def _factor_primes(n: int) -> list[int]:
    factors = []
    divisor = 2
    while divisor * divisor <= n:
        if n % divisor == 0:
            factors.append(divisor)
            while n % divisor == 0:
                n //= divisor
        divisor += 1 if divisor == 2 else 2
    if n > 1:
        factors.append(n)
    return factors


def _mat_mul(left: tuple[int, int, int, int],
             right: tuple[int, int, int, int], q: int
             ) -> tuple[int, int, int, int]:
    a, b, c, d = left
    e, f, g, h = right
    return (
        (a * e + b * g) % q,
        (a * f + b * h) % q,
        (c * e + d * g) % q,
        (c * f + d * h) % q,
    )


def _mat_pow(matrix: tuple[int, int, int, int], exponent: int, q: int
             ) -> tuple[int, int, int, int]:
    result = (1, 0, 0, 1)
    base = matrix
    while exponent:
        if exponent & 1:
            result = _mat_mul(result, base, q)
        base = _mat_mul(base, base, q)
        exponent //= 2
    return result


def _mat_normalize(matrix: tuple[int, int, int, int], q: int
                   ) -> tuple[int, int, int, int]:
    values = tuple(value % q for value in matrix)
    first = next((value for value in values if value), None)
    if first is None:
        raise ValueError("zero projective matrix")
    scale = pow(first, -1, q)
    return tuple(value * scale % q for value in values)


def _mat_det(matrix: tuple[int, int, int, int], q: int) -> int:
    a, b, c, d = matrix
    return (a * d - b * c) % q


def _mat_inv(matrix: tuple[int, int, int, int], q: int
             ) -> tuple[int, int, int, int]:
    a, b, c, d = matrix
    if _mat_det(matrix, q) == 0:
        raise ValueError("singular matrix")
    return _mat_normalize((d, -b, -c, a), q)


def _mat_compose(left: tuple[int, int, int, int],
                 right: tuple[int, int, int, int], q: int
                 ) -> tuple[int, int, int, int]:
    return _mat_normalize(_mat_mul(left, right, q), q)


def _is_scalar(matrix: tuple[int, int, int, int], q: int) -> bool:
    a, b, c, d = (value % q for value in matrix)
    return a != 0 and b == 0 and c == 0 and a == d


def _act(matrix: tuple[int, int, int, int], point: int, q: int) -> int:
    """Act on P^1(F_q), representing INF by the integer q."""
    a, b, c, d = matrix
    if point == q:
        return q if c == 0 else a * pow(c, -1, q) % q
    denominator = (c * point + d) % q
    if denominator == 0:
        return q
    return (a * point + b) * pow(denominator, -1, q) % q


def _find_singer(q: int) -> tuple[int, int, int, int]:
    """Find a PGL(2,q) element of exact projective order q+1."""
    cached = _SINGER_CACHE.get(q)
    if cached is not None:
        return cached
    order = q + 1
    factors = _factor_primes(order)
    for determinant in range(1, q):
        for trace in range(q):
            candidate = (0, (-determinant) % q, 1, trace)
            if not _is_scalar(_mat_pow(candidate, order, q), q):
                continue
            if any(_is_scalar(_mat_pow(candidate, order // prime, q), q)
                   for prime in factors):
                continue
            result = _mat_normalize(candidate, q)
            _SINGER_CACHE[q] = result
            return result
    raise RuntimeError(f"failed to construct a Singer cycle over GF({q})")


def _conjugacy_invariant(matrix: tuple[int, int, int, int], q: int) -> int:
    a, _b, _c, d = matrix
    determinant = _mat_det(matrix, q)
    return (a + d) ** 2 * pow(determinant, -1, q) % q


def _representative_powers(q: int) -> list[tuple[int, int]]:
    """Coprime powers, one per trace^2/determinant invariant."""
    cached = _REP_CACHE.get(q)
    if cached is not None:
        return cached
    singer = _find_singer(q)
    seen = set()
    representatives = []
    for exponent in range(1, q + 1):
        if math.gcd(exponent, q + 1) != 1:
            continue
        powered = _mat_normalize(_mat_pow(singer, exponent, q), q)
        invariant = _conjugacy_invariant(powered, q)
        if invariant not in seen:
            seen.add(invariant)
            representatives.append((exponent, invariant))
    if not representatives:
        raise RuntimeError("no projective-cycle representatives")
    _REP_CACHE[q] = representatives
    return representatives


def _random_pgl(q: int, rng: random.Random) -> tuple[int, int, int, int]:
    while True:
        matrix = tuple(rng.randrange(q) for _ in range(4))
        if _mat_det(matrix, q):
            return _mat_normalize(matrix, q)


def _matrix_json(matrix: tuple[int, int, int, int]) -> dict:
    a, b, c, d = matrix
    return {"matrix": [[a, b], [c, d]]}


def _matrix_from_answer(answer: dict) -> tuple[int, int, int, int]:
    rows = answer["matrix"]
    return (rows[0][0], rows[0][1], rows[1][0], rows[1][1])


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Compose two known projective matchings into a native PSP instance."""
    q = _checked_prime(n)
    if params:
        raise ValueError("unknown parameters: " + ", ".join(sorted(params)))
    if not _is_int(seed):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)

    singer = _find_singer(q)
    representatives = _representative_powers(q)
    exponent, _invariant = representatives[seed % len(representatives)]
    relative = _mat_normalize(_mat_pow(singer, exponent, q), q)

    # Reject only coordinate systems in which a valid map becomes affine; the
    # two actual matching classes remain completely symmetric.
    for _ in range(10_000):
        left_coordinates = _random_pgl(q, rng)
        right_coordinates = _random_pgl(q, rng)
        left_inverse = _mat_inv(left_coordinates, q)
        first = _mat_compose(right_coordinates, left_inverse, q)
        second = _mat_compose(
            _mat_compose(right_coordinates, relative, q), left_inverse, q
        )
        if first[2] != 0 and second[2] != 0:
            break
    else:  # pragma: no cover - probability is negligible
        raise RuntimeError("could not choose non-affine projective coordinates")

    points = list(range(q + 1))
    first_map = [_act(first, x, q) for x in points]
    second_map = [_act(second, x, q) for x in points]
    if len(set(first_map)) != q + 1 or len(set(second_map)) != q + 1:
        raise AssertionError("constructed matrix is not a projective permutation")
    if any(y0 == y1 for y0, y1 in zip(first_map, second_map)):
        raise AssertionError("Singer matchings unexpectedly share an edge")

    second_inverse = [0] * (q + 1)
    for x, y in enumerate(second_map):
        second_inverse[y] = x

    # Traverse the public 2-regular incidence graph in cycle order.  Consecutive
    # entries share alternately a right and a left leaf.
    cycle_edges = []
    x = 0
    visited_left = set()
    for _ in range(q + 1):
        if x in visited_left:
            raise AssertionError("relative projective action is not one cycle")
        visited_left.add(x)
        y = first_map[x]
        cycle_edges.append((x, y))
        x_next = second_inverse[y]
        cycle_edges.append((x_next, y))
        x = x_next
    if x != 0 or len(visited_left) != q + 1:
        raise AssertionError("relative projective action did not close correctly")

    # Display-order greedy is made deterministically bad without distinguishing
    # either valid alternating class: cycle edges 0 and 3 have opposite parity.
    prefix = [cycle_edges[0], cycle_edges[3]]
    remainder = [edge for index, edge in enumerate(cycle_edges)
                 if index not in (0, 3)]
    rng.shuffle(remainder)
    pairs = [list(edge) for edge in prefix + remainder]

    return {
        "paper": "arXiv:2209.08757",
        "family": "projective-cycle path packing on a star",
        "q": q,
        "k": q + 1,
        "infinity": q,
        "paths": pairs,
        "answer": _matrix_json(first),
    }


def render(inst: dict) -> str:
    """Render the complete native path-packing task and exact output format."""
    q = inst["q"]
    inf = inst["infinity"]
    lines = [
        "Find an exact projective certificate for a Path Set Packing.",
        "",
        "Graph and paths.",
        f"Let q={q}, a prime. The projective labels are 0,1,...,{q - 1},INF;",
        f"the table encodes INF by the integer {inf}.",
        "The undirected host graph is a star with centre C and two disjoint",
        "families of leaves L_x and R_y, one leaf for each projective label.",
        "For every table row 'id x y', candidate path id is the simple path",
        "L_x--C--R_y. Path IDs are 0-indexed. Different paths are edge-disjoint",
        "exactly when they repeat neither a left label x nor a right label y.",
        f"You need a packing of exactly k={q + 1} candidate paths.",
        "",
        "Certificate language.",
        "Output one 2-by-2 matrix [[a,b],[c,d]] over GF(q). Every entry must be",
        f"an ordinary decimal integer in 0..{q - 1}. Its determinant a*d-b*c",
        "must be nonzero modulo q. Matrices differing by a nonzero scalar encode",
        "the same map, so the first nonzero entry in row-major order must be 1.",
        "No other normalization is accepted.",
        "",
        "The matrix acts on the projective labels as follows, with all finite",
        "arithmetic modulo q:",
        "  finite x: T(x)=INF if c*x+d=0; otherwise",
        "            T(x)=(a*x+b)*(c*x+d)^(-1) modulo q;",
        "  x=INF:    T(INF)=INF if c=0; otherwise T(INF)=a*c^(-1) modulo q.",
        "Here z^(-1) is the unique residue w with z*w=1 modulo q.",
        "",
        "For every projective x, the table must contain the path (x,T(x)).",
        f"Those {q + 1} paths are the packing certified by your matrix. The",
        "checker expands the rule, checks table membership, and scans their two",
        "host edges for collisions. Order in the table has no mathematical role,",
        "and candidate paths may not be repeated in a packing.",
        "",
        "CANDIDATE_PATHS (id x y)",
    ]
    for path_id, (x, y) in enumerate(inst["paths"]):
        lines.append(f"{path_id} {x} {y}")
    lines.extend([
        "END_CANDIDATE_PATHS",
        "",
        "Give your final answer inside <answer></answer> tags as exactly one JSON",
        "object with key matrix and the normalized 2-by-2 integer array.",
        "Example syntax (only a format example):",
        '<answer>{"matrix":[[1,2],[3,4]]}</answer>',
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    """Extract tagged JSON while tolerating surrounding prose and fences."""
    try:
        if not isinstance(text, str):
            return None
        match = _ANSWER_RE.search(text)
        if match is None:
            return None
        body = match.group(1).strip()
        body = re.sub(r"^```(?:json)?\s*", "", body, flags=re.I)
        body = re.sub(r"\s*```$", "", body).strip()
        answer = json.loads(body)
        return answer if isinstance(answer, dict) else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def _pair_lookup(inst: dict) -> dict[tuple[int, int], int]:
    key = id(inst)
    cached = _PAIR_CACHE.get(key)
    if cached is not None and cached[0] is inst:
        return cached[1]
    lookup = {}
    for path_id, pair in enumerate(inst.get("paths", [])):
        if (isinstance(pair, list) and len(pair) == 2
                and _is_int(pair[0]) and _is_int(pair[1])):
            lookup[(pair[0], pair[1])] = path_id
    if len(_PAIR_CACHE) >= 128:
        _PAIR_CACHE.clear()
    _PAIR_CACHE[key] = (inst, lookup)
    return lookup


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Expand and check any valid matrix witness; never inspect inst['answer']."""
    q = inst.get("q")
    if answer == {} or answer == []:
        return False, "empty answer is not a witness"
    if not isinstance(answer, dict):
        return False, "answer must be one JSON object"
    if set(answer) != {"matrix"}:
        return False, "answer must contain exactly the key matrix"
    rows = answer["matrix"]
    if (not isinstance(rows, list) or len(rows) != 2
            or any(not isinstance(row, list) or len(row) != 2 for row in rows)):
        return False, "matrix must have exactly two rows of two entries"
    values = [rows[0][0], rows[0][1], rows[1][0], rows[1][1]]
    if any(not _is_int(value) for value in values):
        return False, "all matrix entries must be integers"
    if any(value < 0 or value >= q for value in values):
        return False, f"matrix entries must lie in 0..{q - 1}"
    first_nonzero = next((value for value in values if value), None)
    if first_nonzero != 1:
        return False, "matrix is not projectively normalized"
    matrix = tuple(values)
    if _mat_det(matrix, q) == 0:
        return False, "matrix is singular modulo q"

    lookup = _pair_lookup(inst)
    selected_ids = []
    used_host_edges = set()
    for x in range(q + 1):
        y = _act(matrix, x, q)
        path_id = lookup.get((x, y))
        if path_id is None:
            x_text = "INF" if x == q else str(x)
            y_text = "INF" if y == q else str(y)
            return False, f"required path ({x_text},{y_text}) is absent"
        selected_ids.append(path_id)
        for host_edge in (("L", x), ("R", y)):
            if host_edge in used_host_edges:
                return False, "expanded paths share a host-graph edge"
            used_host_edges.add(host_edge)
    if len(selected_ids) != inst.get("k"):
        return False, "expanded certificate has the wrong number of paths"
    if len(set(selected_ids)) != len(selected_ids):
        return False, "expanded certificate repeats a candidate path"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from normalized PGL(2,q), the exact stated language."""
    q = inst["q"]
    return _matrix_json(_random_pgl(q, rng))


def search_space(inst: dict) -> int | None:
    q = inst["q"]
    return q * (q * q - 1)


def enumerate_all(inst: dict) -> int | None:
    """Count valid certificates exactly when normalized PGL is small enough."""
    q = inst["q"]
    if search_space(inst) > _ENUMERATION_CAP:
        return None
    count = 0
    # Canonical matrices whose first entry is 1.
    for b in range(q):
        for c in range(q):
            for d in range(q):
                matrix = (1, b, c, d)
                if _mat_det(matrix, q):
                    count += int(verify(inst, _matrix_json(matrix))[0])
    # Canonical matrices beginning [0,1].
    for c in range(1, q):
        for d in range(q):
            count += int(verify(inst, _matrix_json((0, 1, c, d)))[0])
    return count


def _null_matrix_from_three(pairs: list[tuple[int, int]], q: int,
                            counter: list[int] | None = None
                            ) -> tuple[int, int, int, int] | None:
    """Interpolate the unique PGL map through three point pairs."""
    if len(pairs) < 3:
        return None
    rows = []
    for x, y in pairs[:3]:
        x0, x1 = ((1, 0) if x == q else (x, 1))
        y0, y1 = ((1, 0) if y == q else (y, 1))
        rows.append([
            (-y1 * x0) % q,
            (-y1 * x1) % q,
            (y0 * x0) % q,
            (y0 * x1) % q,
        ])
        if counter is not None:
            counter[0] += 8

    pivot_columns = []
    pivot_row = 0
    for column in range(4):
        chosen = next((row for row in range(pivot_row, 3)
                       if rows[row][column] % q), None)
        if chosen is None:
            continue
        rows[pivot_row], rows[chosen] = rows[chosen], rows[pivot_row]
        inverse = pow(rows[pivot_row][column], -1, q)
        rows[pivot_row] = [value * inverse % q for value in rows[pivot_row]]
        if counter is not None:
            counter[0] += 5
        for row in range(3):
            if row == pivot_row or rows[row][column] == 0:
                continue
            factor = rows[row][column]
            rows[row] = [
                (rows[row][j] - factor * rows[pivot_row][j]) % q
                for j in range(4)
            ]
            if counter is not None:
                counter[0] += 8
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == 3:
            break
    if len(pivot_columns) != 3:
        return None
    free_columns = [column for column in range(4)
                    if column not in pivot_columns]
    if len(free_columns) != 1:
        return None
    free = free_columns[0]
    vector = [0, 0, 0, 0]
    vector[free] = 1
    for row, column in enumerate(pivot_columns):
        vector[column] = (-rows[row][free]) % q
    try:
        matrix = _mat_normalize(tuple(vector), q)
    except ValueError:
        return None
    if _mat_det(matrix, q) == 0:
        return None
    if counter is not None:
        counter[0] += 8
    return matrix


def _matrix_from_matching(pairs: list[tuple[int, int]], q: int,
                          counter: list[int] | None = None
                          ) -> tuple[int, int, int, int] | None:
    ordered = sorted(pairs)
    matrix = _null_matrix_from_three(ordered, q, counter)
    if matrix is None:
        return None
    for x, y in ordered:
        if counter is not None:
            counter[0] += 1
        if _act(matrix, x, q) != y:
            return None
    return matrix


def _alternating_matrices(inst: dict
                          ) -> tuple[tuple[int, int, int, int],
                                     tuple[int, int, int, int]] | None:
    """Recover the two edge-colour classes of the public 2-regular graph."""
    q = inst["q"]
    pairs = [tuple(pair) for pair in inst["paths"]]
    count = len(pairs)
    left_adj = [[] for _ in range(q + 1)]
    right_adj = [[] for _ in range(q + 1)]
    for edge_id, (x, y) in enumerate(pairs):
        if not (0 <= x <= q and 0 <= y <= q):
            return None
        left_adj[x].append(edge_id)
        right_adj[y].append(edge_id)
    if count != 2 * (q + 1):
        return None
    if any(len(edges) != 2 for edges in left_adj + right_adj):
        return None
    colors: list[int | None] = [None] * count
    for start in range(count):
        if colors[start] is not None:
            continue
        colors[start] = 0
        queue = deque([start])
        while queue:
            edge_id = queue.popleft()
            x, y = pairs[edge_id]
            for adjacency in (left_adj[x], right_adj[y]):
                other = adjacency[0] if adjacency[1] == edge_id else adjacency[1]
                wanted = 1 - int(colors[edge_id])
                if colors[other] is None:
                    colors[other] = wanted
                    queue.append(other)
                elif colors[other] != wanted:
                    return None
    classes = [[], []]
    for edge_id, color in enumerate(colors):
        classes[int(color)].append(pairs[edge_id])
    first = _matrix_from_matching(classes[0], q)
    second = _matrix_from_matching(classes[1], q)
    if first is None or second is None:
        return None
    return first, second


def canonical_key(inst: dict) -> str:
    """Projective-coordinate, side-swap, and input-order invariant key."""
    q = inst["q"]
    matrices = _alternating_matrices(inst)
    if matrices is None:
        # This branch is only for malformed out-of-family data; it does not use
        # seed or render text and remains deterministic.
        degree_signature = sorted(tuple(pair) for pair in inst.get("paths", []))
        return json.dumps({"q": q, "malformed_pairs": degree_signature},
                          separators=(",", ":"))
    first, second = matrices
    relative = _mat_compose(_mat_inv(second, q), first, q)
    invariant = _conjugacy_invariant(relative, q)
    return f"q={q};trace2_over_det={invariant}"


def escalate(params: dict) -> dict | str | None:
    """Grow the path haystack while the four-entry witness stays fixed-size."""
    if not isinstance(params, dict) or "n" not in params:
        return None
    current = params["n"]
    if not _is_int(current) or current < 5:
        return None
    harder = _next_prime(2 * int(current) + 1)
    return {"n": harder}


def _reference_matching(inst: dict) -> tuple[object | None, dict]:
    """O(VE) augmenting-path matching, then exact PGL interpolation."""
    q = inst["q"]
    size = q + 1
    adjacency = [[] for _ in range(size)]
    for x, y in inst["paths"]:
        adjacency[x].append(y)
    pair_left = [-1] * size
    pair_right = [-1] * size
    operations = 0
    augmentations = 0
    started = time.perf_counter()

    for root in range(size):
        if pair_left[root] != -1:
            continue
        queue = deque([root])
        seen_left = {root}
        seen_right = set()
        parent_right: dict[int, int] = {}
        free_right = None
        while queue and free_right is None:
            left = queue.popleft()
            operations += 1
            for right in adjacency[left]:
                operations += 1
                if right == pair_left[left] or right in seen_right:
                    continue
                seen_right.add(right)
                parent_right[right] = left
                if pair_right[right] == -1:
                    free_right = right
                    break
                next_left = pair_right[right]
                if next_left not in seen_left:
                    seen_left.add(next_left)
                    queue.append(next_left)
        if free_right is None:
            elapsed = time.perf_counter() - started
            return None, {
                "operations": operations,
                "augmentations": augmentations,
                "wall_clock_sec": elapsed,
            }
        right = free_right
        while True:
            left = parent_right[right]
            previous_right = pair_left[left]
            pair_left[left] = right
            pair_right[right] = left
            operations += 3
            if previous_right == -1:
                break
            right = previous_right
        augmentations += 1

    counter = [operations]
    matching = [(x, pair_left[x]) for x in range(size)]
    matrix = _matrix_from_matching(matching, q, counter)
    elapsed = time.perf_counter() - started
    stats = {
        "operations": counter[0],
        "augmentations": augmentations,
        "wall_clock_sec": elapsed,
    }
    return (None if matrix is None else _matrix_json(matrix)), stats


def _greedy_display_order(inst: dict) -> tuple[object | None, int]:
    used_left = set()
    used_right = set()
    matching = []
    operations = 0
    for x, y in inst["paths"]:
        operations += 2
        if x not in used_left and y not in used_right:
            used_left.add(x)
            used_right.add(y)
            matching.append((x, y))
    if len(matching) != inst["k"]:
        return None, operations
    matrix = _matrix_from_matching(matching, inst["q"])
    return (None if matrix is None else _matrix_json(matrix)), operations


def _affine_ansatz(inst: dict) -> object | None:
    q = inst["q"]
    finite = []
    for x, y in inst["paths"]:
        if x < q and y < q and all(old_x != x for old_x, _ in finite):
            finite.append((x, y))
        if len(finite) == 2:
            break
    if len(finite) < 2 or finite[0][0] == finite[1][0]:
        return None
    x0, y0 = finite[0]
    x1, y1 = finite[1]
    slope = (y1 - y0) * pow((x1 - x0) % q, -1, q) % q
    if slope == 0:
        return None
    intercept = (y0 - slope * x0) % q
    return _matrix_json(_mat_normalize((slope, intercept, 0, 1), q))


def _coordinate_transform(inst: dict, left: tuple[int, int, int, int],
                          right: tuple[int, int, int, int], seed: int) -> dict:
    q = inst["q"]
    paths = [[_act(left, x, q), _act(right, y, q)]
             for x, y in inst["paths"]]
    random.Random(seed).shuffle(paths)
    carried = _mat_compose(
        _mat_compose(right, _matrix_from_answer(inst["answer"]), q),
        _mat_inv(left, q), q,
    )
    return {
        **{key: value for key, value in inst.items()
           if key not in ("paths", "answer")},
        "paths": paths,
        "answer": _matrix_json(carried),
    }


def _swap_sides(inst: dict, seed: int) -> dict:
    q = inst["q"]
    paths = [[y, x] for x, y in inst["paths"]]
    random.Random(seed).shuffle(paths)
    carried = _mat_inv(_matrix_from_answer(inst["answer"]), q)
    return {
        **{key: value for key, value in inst.items()
           if key not in ("paths", "answer")},
        "paths": paths,
        "answer": _matrix_json(carried),
    }


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(item) for item in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(item) for item in value)
    return 1


def _corruption_cases(inst: dict) -> dict[str, object]:
    answer = json.loads(json.dumps(inst["answer"]))
    matrix = _matrix_from_answer(answer)
    duplicate = _matrix_json((matrix[0], matrix[1], matrix[0], matrix[1]))
    cases: dict[str, object] = {
        "empty": {},
        "drop": {"matrix": [[matrix[0], matrix[1]], [matrix[2]]]},
        "duplicate": duplicate,
        "out_of_range": {"matrix": [[inst["q"], matrix[1]],
                                      [matrix[2], matrix[3]]]},
    }
    existing_reasons = {verify(inst, candidate)[1]
                        for candidate in cases.values()}
    values = list(matrix)
    for left in range(4):
        for right in range(left + 1, 4):
            swapped = values[:]
            swapped[left], swapped[right] = swapped[right], swapped[left]
            candidate = _matrix_json(tuple(swapped))
            ok, reason = verify(inst, candidate)
            if not ok and reason not in existing_reasons:
                cases["swap"] = candidate
                return cases
    # An extraordinarily symmetric answer can make every literal swap collide
    # with an existing diagnostic.  A seed-independent fallback still swaps the
    # two rows, then changes only the projective representative.
    swapped = (matrix[2], matrix[3], matrix[0], matrix[1])
    cases["swap"] = _matrix_json(swapped)
    return cases


def selftest() -> dict:
    """Run the nine required gates and return their measured JSON-native report."""
    report: dict[str, Any] = {
        "paper": "2209.08757",
        "track": TRACK,
        "shipping_difficulty": SHIPPING_DIFFICULTY,
        "shipping_params": dict(DIFFICULTY[SHIPPING_DIFFICULTY]),
    }

    # G1: every preset, three seeds, plus JSON-native round trips.
    verified = 0
    json_roundtrips = 0
    attempts = 0
    for params in DIFFICULTY.values():
        for seed in (0, 1, 17):
            instance = make_instance(seed=seed, **params)
            attempts += 1
            verified += int(verify(instance, instance["answer"])[0])
            answer = instance["answer"]
            json_roundtrips += int(json.loads(json.dumps(answer)) == answer)
    report["G1_planted_verifies"] = {
        "pass": verified == attempts and json_roundtrips == attempts,
        "verified": verified,
        "json_roundtrips": json_roundtrips,
        "attempts": attempts,
    }

    shipping = make_instance(seed=424242, **DIFFICULTY[SHIPPING_DIFFICULTY])

    # G2: five specified corruption forms, with distinct diagnostics.
    corruption_results = {}
    reasons = []
    for name, candidate in _corruption_cases(shipping).items():
        ok, reason = verify(shipping, candidate)
        corruption_results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    report["G2_rejects_corruption"] = {
        "pass": (len(corruption_results) == 5
                 and all(item["rejected"] for item in corruption_results.values())
                 and len(set(reasons)) == 5),
        "rejected": sum(item["rejected"] for item in corruption_results.values()),
        "attempts": 5,
        "distinct_reasons": len(set(reasons)),
        "cases": corruption_results,
    }

    # G3: realistic prose/fence variations and malformed text.
    answer_json = json.dumps(shipping["answer"], separators=(",", ":"))
    responses = [
        f"I checked all projective points. <answer>{answer_json}</answer>",
        f"Final result:\n<answer>```json\n{answer_json}\n```</answer>\nDone.",
        f"Some reasoning precedes this.\n<answer>  {answer_json}  </answer>",
    ]
    parsed = sum(parse_answer(response) == shipping["answer"]
                 for response in responses)
    garbage_rejected = parse_answer("no tagged JSON here") is None
    report["G3_round_trip"] = {
        "pass": parsed == len(responses) and garbage_rejected,
        "parsed": parsed,
        "attempts": len(responses),
        "garbage_rejected": garbage_rejected,
    }

    # G4: exact-language, structure-aware random guesses.
    rng = random.Random(220908757)
    hits = 0
    started = time.perf_counter()
    for _ in range(_G4_SAMPLES):
        hits += int(verify(shipping, random_candidate(shipping, rng))[0])
    sampling_seconds = time.perf_counter() - started
    probability = hits / _G4_SAMPLES
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": _G4_SAMPLES,
        "observed_probability": probability,
        "search_space": search_space(shipping),
        "prior": (
            "uniform over normalized nonsingular PGL(2,q) matrices; shape, "
            "entry bounds, determinant, and projective normalization are "
            "already enforced"
        ),
        "sampling_seconds": round(sampling_seconds, 6),
    }

    # G6 is measured before G5 so G5 can cite the strongest costs.
    attack_names = (
        "outlier_leaf_frequency",
        "greedy_display_order",
        "random_restart_256",
        "by_hand_affine_two_point_ansatz",
    )
    attack_successes = {name: 0 for name in attack_names}
    attack_operations = {name: 0 for name in attack_names}
    reference_successes = 0
    reference_operations = []
    reference_times = []
    greedy_times = []
    for offset in range(_ATTACK_SEEDS):
        instance = make_instance(seed=9000 + offset,
                                 **DIFFICULTY[SHIPPING_DIFFICULTY])

        # All degrees are two, so the per-leaf outlier probe has no candidate.
        left_degrees = [0] * instance["k"]
        right_degrees = [0] * instance["k"]
        for x, y in instance["paths"]:
            left_degrees[x] += 1
            right_degrees[y] += 1
        outlier = None
        attack_operations["outlier_leaf_frequency"] += len(instance["paths"])
        if len(set(left_degrees + right_degrees)) != 1:
            outlier = _affine_ansatz(instance)
        attack_successes["outlier_leaf_frequency"] += int(
            outlier is not None and verify(instance, outlier)[0]
        )

        greedy_started = time.perf_counter()
        greedy, greedy_ops = _greedy_display_order(instance)
        greedy_times.append(time.perf_counter() - greedy_started)
        attack_operations["greedy_display_order"] += greedy_ops
        attack_successes["greedy_display_order"] += int(
            greedy is not None and verify(instance, greedy)[0]
        )

        local_rng = random.Random(700_000 + offset)
        random_hit = False
        for _ in range(256):
            candidate = random_candidate(instance, local_rng)
            attack_operations["random_restart_256"] += 1
            if verify(instance, candidate)[0]:
                random_hit = True
                break
        attack_successes["random_restart_256"] += int(random_hit)

        affine = _affine_ansatz(instance)
        attack_operations["by_hand_affine_two_point_ansatz"] += 12
        attack_successes["by_hand_affine_two_point_ansatz"] += int(
            affine is not None and verify(instance, affine)[0]
        )

        reference, stats = _reference_matching(instance)
        reference_successes += int(
            reference is not None and verify(instance, reference)[0]
        )
        reference_operations.append(stats["operations"])
        reference_times.append(stats["wall_clock_sec"])

    attacks = {
        name: {"successes": attack_successes[name],
               "attempts": _ATTACK_SEEDS,
               "operations_mean": attack_operations[name] // _ATTACK_SEEDS}
        for name in attack_names
    }
    all_failed = all(item["successes"] == 0 for item in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": all_failed and reference_successes == _ATTACK_SEEDS,
        "attacks": attacks,
        "reference_algorithm": {
            "name": (
                "augmenting-path bipartite matching on the star leaves, "
                "followed by exact PGL interpolation"
            ),
            "complexity": "O(VE) matching plus O(q log q) exact evaluation",
            "wall_clock_sec_mean": round(
                sum(reference_times) / len(reference_times), 6
            ),
            "operations_mean": sum(reference_operations) // len(reference_operations),
            "operations_max": max(reference_operations),
            "operation_model": (
                "one adjacency/queue action or exact GF(q) field operation; "
                "a field inversion counts as one operation"
            ),
            "solves": f"{reference_successes}/{_ATTACK_SEEDS}, as expected",
        },
    }

    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 2 and probability < 1e-6,
        "shipping_valid_hits": hits,
        "shipping_density_samples": _G4_SAMPLES,
        "shipping_observed_solution_fraction": probability,
        "exact_shipping_solution_count_by_construction": 2,
        "exact_shipping_density": 2 / search_space(shipping),
        "demo_n": demo["q"],
        "demo_exact_solution_count": demo_count,
        "strongest_failing_attack": "greedy display-order maximal matching",
        "strongest_attack_operations_mean": (
            attack_operations["greedy_display_order"] // _ATTACK_SEEDS
        ),
        "strongest_attack_wall_clock_sec_mean": round(
            sum(greedy_times) / len(greedy_times), 6
        ),
        "reference_operations_mean": (
            sum(reference_operations) // len(reference_operations)
        ),
        "operation_model": (
            "one adjacency/queue action or exact GF(q) field operation; "
            "a field inversion counts as one operation"
        ),
        "reference_wall_clock_sec_mean": round(
            sum(reference_times) / len(reference_times), 6
        ),
    }

    # G7: size doubles, witness stays four field elements, and costs grow.
    shipping_n = shipping["q"]
    doubled_n = _next_prime(2 * shipping_n)
    doubled = make_instance(n=doubled_n, seed=12345)
    escalated_params = escalate(DIFFICULTY[SHIPPING_DIFFICULTY])
    escalated = (make_instance(seed=54321, **escalated_params)
                 if isinstance(escalated_params, dict) else None)
    operation_ladder = {}
    path_ladder = {}
    for name, params in DIFFICULTY.items():
        instance = make_instance(seed=77, **params)
        _answer, stats = _reference_matching(instance)
        operation_ladder[name] = stats["operations"]
        path_ladder[name] = len(instance["paths"])
    named = ["demo", "easy", "medium", "hard"]
    paths_increase = all(path_ladder[named[i]] < path_ladder[named[i + 1]]
                         for i in range(3))
    report["G7_scales"] = {
        "pass": (verify(doubled, doubled["answer"])[0]
                 and escalated is not None
                 and verify(escalated, escalated["answer"])[0]
                 and paths_increase
                 and _answer_atoms(doubled["answer"]) == 4),
        "doubled_requested_n": 2 * shipping_n,
        "doubled_supported_prime_n": doubled_n,
        "doubled_planted_verifies": verify(doubled, doubled["answer"])[0],
        "first_escalated_params": escalated_params,
        "first_escalated_verifies": (
            escalated is not None and verify(escalated, escalated["answer"])[0]
        ),
        "fixed_answer_axis": (
            "q grows the 2(q+1)-path haystack while the answer remains one "
            "four-entry matrix"
        ),
        "candidate_path_ladder": path_ladder,
        "reference_operation_ladder": operation_ladder,
    }

    # G8: public structural key under all declared isomorphisms.
    invariance_checks = 0
    carried_checks = 0
    transformations = 0
    keys = []
    for seed in range(20):
        instance = make_instance(seed=seed,
                                 **DIFFICULTY[SHIPPING_DIFFICULTY])
        original_key = canonical_key(instance)
        keys.append(original_key)
        rng_transform = random.Random(800_000 + seed)
        left = _random_pgl(instance["q"], rng_transform)
        right = _random_pgl(instance["q"], rng_transform)
        reordered = _coordinate_transform(
            instance, (1, 0, 0, 1), (1, 0, 0, 1), 10_000 + seed
        )
        relabelled = _coordinate_transform(
            instance, left, right, 20_000 + seed
        )
        swapped = _swap_sides(instance, 30_000 + seed)
        composed = _swap_sides(relabelled, 40_000 + seed)
        for transformed in (reordered, relabelled, swapped, composed):
            transformations += 1
            invariance_checks += int(canonical_key(transformed) == original_key)
            carried_checks += int(verify(transformed, transformed["answer"])[0])
    report["G8_canonical_key"] = {
        "pass": (invariance_checks == transformations
                 and carried_checks == transformations
                 and len(set(keys)) == 20),
        "invariance_checks": invariance_checks,
        "invariance_attempts": transformations,
        "carried_witness_checks": carried_checks,
        "carried_witness_attempts": transformations,
        "unrelated_distinct_keys": len(set(keys)),
        "unrelated_attempts": 20,
        "transformations": [
            "candidate-path reordering",
            "independent left/right PGL coordinate changes",
            "exchange of left and right leaf families",
            "composition of PGL relabelling, side exchange, and reordering",
        ],
    }

    # G9(c) is the only gate.  The three arms are recorded diagnostics.
    answer_blobs = [
        json.dumps(make_instance(seed=seed,
                                 **DIFFICULTY[SHIPPING_DIFFICULTY])["answer"],
                   separators=(",", ":"))
        for seed in range(20)
    ]
    answer_chars = max(len(blob) for blob in answer_blobs)
    answer_tokens = max((len(blob) + 3) // 4 for blob in answer_blobs)
    answer_elements = _answer_atoms(shipping["answer"])
    intended_operations = 92
    arms = {
        arm: dict(_ORACLE_EVIDENCE[arm])
        for arm in ("bare", "hinted", "placebo")
    }
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else None)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else None)
    caps_pass = (answer_chars <= 2000 and answer_elements <= 256
                 and intended_operations <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": caps_pass,
        "caps_pass": caps_pass,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None
        ),
        "hinted_verdict": _ORACLE_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
    }

    gated = [key for key in report if key.startswith("G")]
    report["all_passed"] = all(report[key].get("pass", False) for key in gated)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
