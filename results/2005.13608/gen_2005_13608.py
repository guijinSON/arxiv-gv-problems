"""Verified total Roman strategies for direct graph products (arXiv:2005.13608).

The factor graph is represented exactly by the non-neighbour masks between two
labelled vertex parts.  It is regular and contains a planted central triangle.
The three vertices of that triangle are selected before the remaining incidence
rows are mixed, so generation never solves the instance it creates.  Section 3,
Theorem 10(iii) of the paper carries two central triangles to a weight-6 total
Roman dominating function on the direct product (and proves it is minimum).

This is an honest Track-B family.  The same theorem gives a polynomial reference
algorithm: enumerate all factor triangles and test the central condition.  The
short no-tool route instead recognizes an anchor-row overlap invariant.
"""

from __future__ import annotations

import functools
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
try:
    from gvlib import exact_matrices, rationals  # noqa: F401
except ImportError:  # This graph family has a complete standard-library fallback.
    exact_matrices = rationals = None


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "regular graph given by exact bipartite non-neighbour masks",
        "direct product of the factor graph with itself",
        "sparse weight-six total Roman dominating labelling",
    ],
    "verification_operations": [
        "exact bit-mask adjacency tests",
        "exact triangle tests",
        "exact bitwise verification of the central-triangle condition",
        "integer label-weight comparison",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The anchor's complement-neighbourhood has a unique high-overlap row "
        "whose two disjoint partners form the central triangle; without this "
        "invariant one enumerates and tests factor triangles."
    ),
    "hardness_basis": (
        "Track B: Section 3, Theorem 10(iii) gives an O(N^4) scalar (or O(N^3) "
        "bit-parallel) central-triangle enumeration algorithm; at shipping it "
        "used at most 1,273,144 word operations per instance and 0.319 seconds "
        "over eight instances, while the compact anchor-overlap route used 284 "
        "exact word operations."
    ),
    "max_answer_tokens": 32,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}


# n is the size of each displayed side of the factor graph.  The factor itself
# has 2n vertices, and its direct square has 4n^2 vertices.  The answer always
# contains exactly three product vertices; difficulty grows in the haystack.
DIFFICULTY = {
    "demo": {"n": 21, "guide_gap": 1, "mix_rounds": 16},
    "easy": {"n": 24, "guide_gap": 1, "mix_rounds": 16},
    "medium": {"n": 48, "guide_gap": 2, "mix_rounds": 24},
    "hard": {"n": 72, "guide_gap": 4, "mix_rounds": 32},
}
SHIPPING_DIFFICULTY = "hard"

# G9 scratch runs set this flag so harden.py evaluates only the shipping rung.
if os.environ.get("GV_G9_SINGLE") == "1":
    DIFFICULTY = {
        SHIPPING_DIFFICULTY: dict(DIFFICULTY[SHIPPING_DIFFICULTY])
    }


CERTIFICATE_LANGUAGE = {
    "description": (
        "A strictly lexicographically increasing JSON list of exactly three "
        "distinct product vertices [u,v], with 0 <= u,v < 2n, that induce a "
        "triangle in the direct product.  Those three vertices receive label 2 "
        "and every other product vertex receives label 0."
    ),
    "bounds": {
        "product_vertices": 3,
        "integer_coordinates_per_vertex": 2,
        "coordinate_range": "0 <= coordinate < 2n",
        "order": "strict lexicographic order",
        "structural_rule": "the three product vertices induce a triangle",
        "candidate_count": "6 times the square of the factor triangle count",
    },
}


STRUCTURAL_HINT = (
    "The anchor row lies in a unique high-overlap relation ending at three "
    "pairwise-disjoint complement-neighbourhood masks."
)
PLACEBO_HINT = (
    "The hexadecimal rows use least-significant bit zero and require careful "
    "distinction between the two vertex sides."
)


# Updated only after the script-owned isolated oracle runs.
G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 0},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 1, "attempts": 3},
    "hinted_verdict": "too_easy",
}


NOTES = r"""
Section 1 fixes the definitions used by the checker.  A total Roman dominating
function f:V(G)->{0,1,2} requires every zero-labelled vertex to have a
two-labelled neighbour, and the positive-labelled vertices must induce no
isolated vertex.  The direct product has (g,h) adjacent to (g',h') exactly when
gg' and hh' are edges in the two factors.

Section 3 fixes both construction and track.  Theorem 10(i)-(iii) rules out
weights below six (apart from K2 x K2) and proves that central triangles
g1g2g3 and h1h2h3 yield the weight-six function with label 2 on
(g1,h1),(g2,h2),(g3,h3).  Conversely, its proof shows that every weight-six
all-2 support triple projects to central triangles.  This is the exact counting
identity used by enumerate_all.  The theorem also kills Track A for this
distribution: enumerating all factor triangles and checking whether every
factor vertex sees at least two of them is polynomial.  Corollary 11 and Section
4 provide still easier closed-form regimes (complete/bipartite/wheel/fan
products and regular efficient-open-domination graphs), so they are not used as
a hardness claim.

Inverse construction is performed in the complement.  Start with an r-regular
bipartite graph on n+n vertices, n=3r.  Three chosen left rows are disjoint
r-sets partitioning the right side, and hence form a central triangle in the
complement.  A fourth, anchored row has a prescribed large overlap with the
first.  Degree-preserving two-switches mix every other row, after which
independent left/right relabellings carry the planted triangle and anchor.
Every factor vertex has the same degree, and every complement row has the same
weight, so the planted vertices are not per-vertex degree/width outliers.

The failing panel tests equal-degree/label order, a lexicographic triangle, a
minimum-overlap greedy packing, an anchor-only numeric continuation, and random
legal product triangles.  The successful reference algorithm exhausts factor
triangles as licensed by Theorem 10 and is reported separately because this is
Track B.  The compact route compares the anchor mask with each left mask, then
compares the unique maximum-overlap mask with each left mask; at n=72 this is
284 AND/popcount word operations.

The canonical key is invariant under arbitrary independent relabellings of the
two displayed sides and row-order changes.  It applies anchor-individualized
colour refinement to the complete weighted graph of row-intersection sizes.
This is a strong polynomial invariant, not a complete canonical form for
bipartite graph isomorphism; the README records the limitation.

After n=72, increasing n would preserve the six-atom answer but would exceed
G9(c)'s 300-operation intended-route ceiling because the shortcut costs 4n-4.
Accordingly, escalate() first exhausts guide weakening and additional mixing at
fixed n, then returns None rather than misreporting an answer-size cap.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)


def _validate_params(n: int, guide_gap: int, mix_rounds: int) -> tuple[int, int, int]:
    for name, value in (("n", n), ("guide_gap", guide_gap),
                        ("mix_rounds", mix_rounds)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
    # The switch construction can be overconstrained below 21: for example,
    # there need not be enough movable rows to make the anchor's maximum
    # overlap unique while retaining exactly two disjoint partners.  Keep the
    # public parameter range to the regime for which generation is reliable.
    if n < 21 or n % 3:
        raise ValueError("n must be a multiple of 3 and at least 21")
    r = n // 3
    if not 1 <= guide_gap < r:
        raise ValueError("guide_gap must satisfy 1 <= guide_gap < n/3")
    if mix_rounds < 1:
        raise ValueError("mix_rounds must be positive")
    return n, guide_gap, mix_rounds


def _cyclic_mask(start: int, width: int, modulus: int) -> int:
    mask = 0
    for offset in range(width):
        mask |= 1 << ((start + offset) % modulus)
    return mask


def _switch_mixed_rows(n: int, guide_gap: int, mix_rounds: int,
                       rng: random.Random) -> tuple[list[int], list[int], int]:
    """Build complement rows while retaining the known planted certificate."""
    r = n // 3
    centers = [0, r, 2 * r]
    anchor = guide_gap
    frozen = set(centers + [anchor])
    movable = [i for i in range(n) if i not in frozen]

    for _attempt in range(16):
        rows = [set((i + k) % n for k in range(r)) for i in range(n)]
        for _ in range(mix_rounds * n * r):
            a, b = rng.sample(movable, 2)
            # Sorting makes determinism depend only on (n, seed, params), not
            # on implementation-specific set iteration order.
            x = rng.choice(sorted(rows[a]))
            y = rng.choice(sorted(rows[b]))
            if x == y or y in rows[a] or x in rows[b]:
                continue
            rows[a].remove(x)
            rows[a].add(y)
            rows[b].remove(y)
            rows[b].add(x)

        masks = [sum(1 << j for j in row) for row in rows]
        root_mask = masks[anchor]
        overlaps = [
            (root_mask & masks[i]).bit_count() if i != anchor else -1
            for i in range(n)
        ]
        best = max(overlaps)
        best_rows = [i for i, value in enumerate(overlaps) if value == best]
        disjoint = [
            i for i in range(n)
            if i != centers[0] and not (masks[centers[0]] & masks[i])
        ]
        if best_rows == [centers[0]] and set(disjoint) == set(centers[1:]):
            # Degree checks are construction invariants, not searches for C.
            assert all(mask.bit_count() == r for mask in masks)
            column_degrees = [
                sum((mask >> j) & 1 for mask in masks) for j in range(n)
            ]
            assert column_degrees == [r] * n
            return masks, centers, anchor
    raise RuntimeError("could not mix decoys while preserving the guide invariant")


def _permute_mask(mask: int, permutation: list[int], n: int) -> int:
    out = 0
    for old in range(n):
        if (mask >> old) & 1:
            out |= 1 << permutation[old]
    return out


def make_instance(n: int, seed: int = 0, guide_gap: int = 1,
                  mix_rounds: int = 16, **params) -> dict:
    """Inverse-generate a direct-product TRDF with a known weight-six witness."""
    if params:
        unknown = ", ".join(sorted(params))
        raise ValueError(f"unknown parameter(s): {unknown}")
    n, guide_gap, mix_rounds = _validate_params(n, guide_gap, mix_rounds)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)
    masks, centers, anchor = _switch_mixed_rows(
        n, guide_gap, mix_rounds, rng
    )

    left_perm = list(range(n))
    right_perm = list(range(n))
    rng.shuffle(left_perm)
    rng.shuffle(right_perm)
    relabelled = [0] * n
    for old_left, mask in enumerate(masks):
        relabelled[left_perm[old_left]] = _permute_mask(mask, right_perm, n)
    planted = sorted(left_perm[c] for c in centers)
    row_order = list(range(n))
    rng.shuffle(row_order)

    answer = [[vertex, vertex] for vertex in planted]
    return {
        "family": "central-triangle total Roman strategy on G x G",
        "n": n,
        "factor_order": 2 * n,
        "complement_row_weight": n // 3,
        "guide_gap": guide_gap,
        "mix_rounds": mix_rounds,
        "anchor": left_perm[anchor],
        "row_masks": relabelled,
        "row_order": row_order,
        "answer": answer,
    }


@functools.lru_cache(maxsize=128)
def _adjacency_cached(n: int, row_masks: tuple[int, ...]) -> tuple[int, ...]:
    """Factor adjacency rows as exact Python-integer bit sets."""
    low = (1 << n) - 1
    all_factor = (1 << (2 * n)) - 1
    rows = [0] * (2 * n)
    for i, nonneighbors in enumerate(row_masks):
        same_side = low ^ (1 << i)
        cross = (low ^ nonneighbors) << n
        rows[i] = same_side | cross
    for j in range(n):
        left_neighbors = 0
        for i, nonneighbors in enumerate(row_masks):
            if not ((nonneighbors >> j) & 1):
                left_neighbors |= 1 << i
        right_neighbors = ((low ^ (1 << j)) << n)
        rows[n + j] = left_neighbors | right_neighbors
    assert all(not (rows[i] & (1 << i)) for i in range(2 * n))
    assert all((row & ~all_factor) == 0 for row in rows)
    return tuple(rows)


def _adjacency(inst: dict) -> tuple[int, ...]:
    return _adjacency_cached(inst["n"], tuple(inst["row_masks"]))


def _edge(adjacency: tuple[int, ...], u: int, v: int) -> bool:
    return u != v and bool((adjacency[u] >> v) & 1)


def _is_triangle(adjacency: tuple[int, ...], triple: tuple[int, int, int]) -> bool:
    a, b, c = triple
    return _edge(adjacency, a, b) and _edge(adjacency, a, c) and _edge(adjacency, b, c)


def _is_central(adjacency: tuple[int, ...], triple: tuple[int, int, int]) -> bool:
    if len(set(triple)) != 3 or not _is_triangle(adjacency, triple):
        return False
    a, b, c = triple
    seen_twice = (
        (adjacency[a] & adjacency[b])
        | (adjacency[a] & adjacency[c])
        | (adjacency[b] & adjacency[c])
    )
    return seen_twice == (1 << len(adjacency)) - 1


@functools.lru_cache(maxsize=32)
def _triangles_cached(n: int, row_masks: tuple[int, ...]) -> tuple[tuple[int, int, int], ...]:
    adjacency = _adjacency_cached(n, row_masks)
    order = 2 * n
    triangles = []
    for a in range(order - 2):
        for b in range(a + 1, order - 1):
            if not _edge(adjacency, a, b):
                continue
            common = adjacency[a] & adjacency[b]
            for c in range(b + 1, order):
                if (common >> c) & 1:
                    triangles.append((a, b, c))
    return tuple(triangles)


def _factor_triangles(inst: dict) -> tuple[tuple[int, int, int], ...]:
    return _triangles_cached(inst["n"], tuple(inst["row_masks"]))


def render(inst: dict) -> str:
    """Render a self-contained exact problem statement."""
    n = inst["n"]
    width = max(1, (n + 3) // 4)
    lines = [
        "Find a weight-6 total Roman strategy on a direct product.",
        "",
        f"Define a simple factor graph G on {2*n} vertices numbered 0 through {2*n-1}.",
        f"Its left side is L_i=i for 0<=i<{n}; its right side is R_j={n}+j for 0<=j<{n}.",
        "There are no loops. Every two distinct left vertices are adjacent, and",
        "every two distinct right vertices are adjacent. Across the sides, L_i",
        "and R_j are adjacent exactly when bit j of row M_i below is 0.",
        "Hexadecimal bit 0 is the least-significant (rightmost) bit; leading zeroes",
        "are included only for readability. Thus a 1 records a cross-side NON-edge.",
        f"Every M_i has exactly {inst['complement_row_weight']} one-bits.",
        "",
        f"One annotated left vertex is the anchor: L_{inst['anchor']}.",
        "The annotation is part of the instance but does not change adjacency.",
        "The non-neighbour rows are presented in arbitrary order:",
    ]
    for i in inst["row_order"]:
        lines.append(f"M_{i} = 0x{inst['row_masks'][i]:0{width}x}")
    lines.extend([
        "",
        "The direct product P=G x G has vertices (u,v), with 0<=u,v<"
        + str(2 * n) + ". Distinct product vertices (u,v) and (u',v') are",
        "adjacent in P exactly when uu' is an edge of G AND vv' is an edge of G.",
        "",
        "A total Roman dominating function assigns each product vertex a label in",
        "{0,1,2}. Every label-0 vertex must have a label-2 neighbour, and the",
        "subgraph induced by all positive-label vertices must have minimum degree",
        "at least 1. Its weight is the sum of all labels. This instance is promised",
        "to admit a total Roman dominating function of weight exactly 6.",
        "",
        "Submit exactly three distinct product vertices. They will receive label 2;",
        "every other product vertex receives label 0. The three submitted vertices",
        "must induce a triangle in P and be in strict lexicographic order, with no",
        "repetitions. Coordinates and",
        "all indexing are zero-based; interval bounds above are inclusive at 0 and",
        "exclusive at the upper endpoint.",
        "",
        "Give your final answer inside <answer></answer> tags as one JSON list of",
        "three pairs [[u1,v1],[u2,v2],[u3,v3]].",
        "Example: <answer>[[0,1],[2,3],[4,5]]</answer>",
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: str):
    """Extract the last tagged JSON answer; return None on malformed text."""
    if not isinstance(text, str):
        return None
    matches = _ANSWER_RE.findall(text)
    if not matches:
        return None
    try:
        value = json.loads(matches[-1].strip())
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value


def verify(inst: dict, answer) -> tuple[bool, str]:
    """Check any certificate in the language, without reading inst['answer']."""
    if answer == []:
        return False, "answer is empty"
    if not isinstance(answer, list) or len(answer) != 3:
        return False, "answer must contain exactly three product vertices"
    pairs = []
    for pair in answer:
        if not isinstance(pair, list) or len(pair) != 2:
            return False, "each product vertex must be a JSON pair [u,v]"
        if any(isinstance(x, bool) or not isinstance(x, int) for x in pair):
            return False, "all product-vertex coordinates must be integers"
        pairs.append((pair[0], pair[1]))
    if len(set(pairs)) != 3:
        return False, "the three product vertices must be distinct"
    order = inst["factor_order"]
    if any(u < 0 or u >= order or v < 0 or v >= order for u, v in pairs):
        return False, f"a coordinate is outside the allowed range 0..{order-1}"
    if pairs != sorted(pairs):
        return False, "product vertices must be in strict lexicographic order"

    # Preserve the submitted pairing: independently sorting the two projections
    # would silently verify a different set of product vertices.
    first = tuple(u for u, _ in pairs)
    second = tuple(v for _, v in pairs)
    if len(set(first)) != 3 or len(set(second)) != 3:
        return False, "each factor projection must contain three distinct vertices"
    adjacency = _adjacency(inst)
    if not _is_triangle(adjacency, first) or not _is_triangle(adjacency, second):
        return False, "the support does not induce a triangle in the direct product"
    # Check domination directly, without appealing to the planted answer or to
    # the theorem.  For factor vertex x, signature(x) records which one of the
    # three submitted coordinates is adjacent to x.  Product vertex (x,y) sees
    # a submitted label-2 vertex exactly when the two signatures intersect.
    full = (1 << order) - 1

    def present_signatures(coordinates):
        present = set()
        for signature in range(8):
            vertices = full
            for index, coordinate in enumerate(coordinates):
                if (signature >> index) & 1:
                    vertices &= adjacency[coordinate]
                else:
                    vertices &= full ^ adjacency[coordinate]
            if vertices:
                present.add(signature)
        return present

    present_first = present_signatures(first)
    present_second = present_signatures(second)
    if any((a & b) == 0 for a in present_first for b in present_second):
        return False, "some label-0 product vertex has no label-2 neighbour"
    # The required product triangle already proves that every positive vertex
    # has positive degree.  Three labels 2 have weight exactly six.
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random):
    """Uniformly sample the stated language of product-graph triangles."""
    triangles = _factor_triangles(inst)
    left = rng.choice(triangles)
    right = list(rng.choice(triangles))
    rng.shuffle(right)
    return [list(pair) for pair in sorted(zip(left, right))]


def search_space(inst: dict) -> int:
    """Exact number of three-vertex triangles in G x G."""
    count = len(_factor_triangles(inst))
    return 6 * count * count


def enumerate_all(inst: dict):
    """Count all valid certificates using Theorem 10's exact factorization."""
    if inst["factor_order"] > 160:
        return None
    adjacency = _adjacency(inst)
    central = sum(
        _is_central(adjacency, triangle)
        for triangle in _factor_triangles(inst)
    )
    return 6 * central * central


def _intersection_refinement(inst: dict) -> list:
    """Anchor-aware invariant of the complement-row intersection structure."""
    masks = inst["row_masks"]
    n = inst["n"]
    matrix = [
        [(masks[i] & masks[j]).bit_count() for j in range(n)]
        for i in range(n)
    ]
    colors = [int(i == inst["anchor"]) for i in range(n)]
    for _ in range(5):
        signatures = [
            (colors[i], tuple(sorted(
                (matrix[i][j], colors[j]) for j in range(n) if j != i
            )))
            for i in range(n)
        ]
        palette = {sig: k for k, sig in enumerate(sorted(set(signatures)))}
        new_colors = [palette[sig] for sig in signatures]
        if new_colors == colors:
            break
        colors = new_colors
    vertex_records = sorted(
        (colors[i], tuple(sorted(
            (matrix[i][j], colors[j]) for j in range(n) if j != i
        )))
        for i in range(n)
    )
    return [inst["n"], inst["complement_row_weight"], vertex_records]


def canonical_key(inst: dict) -> str:
    """A relabelling-invariant rooted incidence signature, not a seed hash."""
    payload = json.dumps(_intersection_refinement(inst), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params: dict):
    """Increase decoy mixing and weaken the guide at fixed answer length."""
    p = {k: v for k, v in params.items() if k != "_preset"}
    n = int(p.get("n", 72))
    gap = int(p.get("guide_gap", 1))
    rounds = int(p.get("mix_rounds", 16))
    limit = max(1, n // 6 - 1)
    if gap < limit:
        p["guide_gap"] = min(limit, gap + max(1, n // 36))
        p["mix_rounds"] = min(128, rounds + 16)
        return p
    if rounds < 128:
        p["mix_rounds"] = min(128, rounds * 2)
        return p
    # Raising n would keep the six-atom answer short, but the intended scan
    # costs 4n-4 word operations and n=72 is already close to G9(c)'s limit of
    # 300.  This is an effort ceiling, not the answer-size ceiling denoted by
    # "cap_bound".  With guide strength and mixing exhausted, no further
    # admissible axis remains.
    return None


def _transform_instance(inst: dict, left_perm: list[int], right_perm: list[int],
                        reverse_rows: bool = False) -> dict:
    """Carry the rooted graph and witness through independent side relabellings."""
    n = inst["n"]
    if sorted(left_perm) != list(range(n)) or sorted(right_perm) != list(range(n)):
        raise ValueError("side maps must be permutations")
    rows = [0] * n
    for old_left, mask in enumerate(inst["row_masks"]):
        rows[left_perm[old_left]] = _permute_mask(mask, right_perm, n)

    def vertex_map(value: int) -> int:
        if value < n:
            return left_perm[value]
        return n + right_perm[value - n]

    answer = sorted(
        [[vertex_map(u), vertex_map(v)] for u, v in inst["answer"]]
    )
    order = [left_perm[i] for i in inst["row_order"]]
    if reverse_rows:
        order.reverse()
    return {
        "family": inst["family"],
        "n": n,
        "factor_order": 2 * n,
        "complement_row_weight": inst["complement_row_weight"],
        "guide_gap": inst["guide_gap"],
        "mix_rounds": inst["mix_rounds"],
        "anchor": left_perm[inst["anchor"]],
        "row_masks": rows,
        "row_order": order,
        "answer": answer,
    }


def _shortcut_decode(inst: dict) -> tuple[list[list[int]] | None, int]:
    """The intended anchor-overlap route and its exact word-operation count."""
    masks = inst["row_masks"]
    anchor = inst["anchor"]
    root = masks[anchor]
    scored = []
    operations = 0
    for i, mask in enumerate(masks):
        if i == anchor:
            continue
        score = (root & mask).bit_count()
        operations += 2  # one AND, one population count
        scored.append((score, i))
    maximum = max(score for score, _ in scored)
    candidates = [i for score, i in scored if score == maximum]
    if len(candidates) != 1:
        return None, operations
    first = candidates[0]
    disjoint = []
    for i, mask in enumerate(masks):
        if i == first:
            continue
        overlap = (masks[first] & mask).bit_count()
        operations += 2
        if overlap == 0:
            disjoint.append(i)
    if len(disjoint) != 2:
        return None, operations
    centers = sorted([first] + disjoint)
    return [[v, v] for v in centers], operations


def _reference_find(inst: dict) -> tuple[list[list[int]] | None, int, int]:
    """Theorem-10 exhaustive central-triangle scan with counted word operations."""
    adjacency = _adjacency(inst)
    order = len(adjacency)
    full = (1 << order) - 1
    operations = 0
    examined = 0
    for a, b, c in itertools.combinations(range(order), 3):
        examined += 1
        operations += 1
        if not _edge(adjacency, a, b):
            continue
        operations += 1
        if not _edge(adjacency, a, c):
            continue
        operations += 1
        if not _edge(adjacency, b, c):
            continue
        cover = (
            (adjacency[a] & adjacency[b])
            | (adjacency[a] & adjacency[c])
            | (adjacency[b] & adjacency[c])
        )
        operations += 6  # three ANDs, two ORs, one exact equality
        if cover == full:
            return [[a, a], [b, b], [c, c]], operations, examined
    return None, operations, examined


def _degree_outlier_attack(inst: dict) -> list[list[int]]:
    adjacency = _adjacency(inst)
    ranked = sorted(range(len(adjacency)), key=lambda v: (-adjacency[v].bit_count(), v))
    return [[v, v] for v in sorted(ranked[:3])]


def _anchor_numeric_attack(inst: dict) -> list[list[int]]:
    n = inst["n"]
    values = sorted({inst["anchor"], (inst["anchor"] + 1) % n,
                     (inst["anchor"] + 2) % n})
    while len(values) < 3:
        values.append(next(v for v in range(n) if v not in values))
        values.sort()
    return [[v, v] for v in values]


def _lexicographic_triangle_attack(inst: dict) -> list[list[int]]:
    triangle = _factor_triangles(inst)[0]
    return [[v, v] for v in triangle]


def _greedy_overlap_attack(inst: dict) -> list[list[int]]:
    masks = inst["row_masks"]
    # The obvious use of the annotated vertex is to greedily minimize overlap;
    # the actual invariant first moves in the opposite direction.
    chosen = [inst["anchor"]]
    while len(chosen) < 3:
        candidates = [i for i in range(inst["n"]) if i not in chosen]
        nxt = min(candidates, key=lambda i: (
            sum((masks[i] & masks[j]).bit_count() for j in chosen), i
        ))
        chosen.append(nxt)
    chosen.sort()
    return [[v, v] for v in chosen]


def _random_restart_attack(inst: dict, rng: random.Random,
                           restarts: int = 256) -> tuple[list[list[int]], int]:
    candidate = None
    for attempt in range(1, restarts + 1):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            return candidate, attempt
    assert candidate is not None
    return candidate, restarts


def _atomic_elements(value) -> int:
    if isinstance(value, dict):
        return sum(_atomic_elements(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_atomic_elements(v) for v in value)
    return 1


def selftest() -> dict:
    """Run G1--G9 and return machine-readable measured evidence."""
    report = {}

    checked = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 99):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            assert ok, (preset, seed, why)
            assert json.loads(json.dumps(inst["answer"])) == inst["answer"]
            shortcut, operations = _shortcut_decode(inst)
            assert shortcut is not None and verify(inst, shortcut)[0]
            assert operations == 4 * params["n"] - 4
            checked += 1
    report["G1_planted_verifies"] = {
        "pass": True,
        "instances": checked,
        "generation_route": "inverse generation plus Theorem 10(iii)",
    }

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260905, **ship_params)
    answer = inst["answer"]
    corruptions = {
        "empty": [],
        "drop_one": answer[:-1],
        "duplicate": [answer[0], answer[0], answer[2]],
        "out_of_range": [answer[0], answer[1], [inst["factor_order"], 0]],
        "swap_order": [answer[1], answer[0], answer[2]],
    }
    reasons = {}
    for name, bad in corruptions.items():
        ok, why = verify(inst, bad)
        assert not ok, (name, bad)
        reasons[name] = why
    assert len(set(reasons.values())) == len(reasons), reasons
    report["G2_rejects_corruption"] = {"pass": True, "reasons": reasons}

    response = (
        "The two factor projections are central triangles.\n```json\n<answer>"
        + json.dumps(answer, separators=(",", ":"))
        + "</answer>\n```\nAll coordinates are zero-based."
    )
    assert parse_answer(response) == answer
    assert parse_answer("no tagged answer") is None
    assert parse_answer("<answer>[[0, nope]]</answer>") is None
    report["G3_round_trip"] = {
        "pass": True,
        "json_native": True,
        "answer_elements": _atomic_elements(answer),
    }

    guess_inst = make_instance(seed=8675309, **ship_params)
    guess_rng = random.Random(13579)
    guess_total = 200_000
    guess_hits = 0
    for _ in range(guess_total):
        if verify(guess_inst, random_candidate(guess_inst, guess_rng))[0]:
            guess_hits += 1
    guess_density = guess_hits / guess_total
    assert guess_density < 1e-6, (guess_hits, guess_total)
    report["G4_guess_resistance"] = {
        "pass": True,
        "hits": guess_hits,
        "total": guess_total,
        "empirical_probability": guess_density,
        "structure_aware_space": search_space(guess_inst),
        "prior": "uniform over all three-vertex triangles of G x G",
    }

    exact_solutions = enumerate_all(guess_inst)
    assert isinstance(exact_solutions, int) and exact_solutions >= 6
    candidate_count = search_space(guess_inst)
    exact_fraction = exact_solutions / candidate_count

    attack_seeds = list(range(3100, 3108))
    attacks = {
        "equal_degree_then_smallest_labels": {"successes": 0, "attempts": 8},
        "lexicographically_first_factor_triangle": {"successes": 0, "attempts": 8},
        "greedy_minimum_row_overlap": {"successes": 0, "attempts": 8},
        "anchor_plus_next_numeric_labels": {"successes": 0, "attempts": 8},
        "random_legal_product_triangles_256": {"successes": 0, "attempts": 8},
    }
    restart_iterations = 0
    restart_seconds = 0.0
    reference_operations = []
    reference_examined = []
    reference_seconds = 0.0
    reference_successes = 0
    shortcut_operations = []
    for seed in attack_seeds:
        target = make_instance(seed=seed, **ship_params)
        probes = {
            "equal_degree_then_smallest_labels": _degree_outlier_attack(target),
            "lexicographically_first_factor_triangle": _lexicographic_triangle_attack(target),
            "greedy_minimum_row_overlap": _greedy_overlap_attack(target),
            "anchor_plus_next_numeric_labels": _anchor_numeric_attack(target),
        }
        for name, candidate in probes.items():
            if verify(target, candidate)[0]:
                attacks[name]["successes"] += 1
        t0 = time.perf_counter()
        candidate, used = _random_restart_attack(
            target, random.Random(seed ^ 0xA51CE), 256
        )
        restart_seconds += time.perf_counter() - t0
        restart_iterations += used
        if verify(target, candidate)[0]:
            attacks["random_legal_product_triangles_256"]["successes"] += 1

        t0 = time.perf_counter()
        reference, operations, examined = _reference_find(target)
        reference_seconds += time.perf_counter() - t0
        reference_operations.append(operations)
        reference_examined.append(examined)
        if reference is not None and verify(target, reference)[0]:
            reference_successes += 1
        shortcut, compact_ops = _shortcut_decode(target)
        assert shortcut is not None and verify(target, shortcut)[0]
        shortcut_operations.append(compact_ops)

    assert all(row["successes"] == 0 for row in attacks.values()), attacks
    assert reference_successes == len(attack_seeds)
    report["G5_density_and_baseline_cost"] = {
        "pass": True,
        "shipping_exact_solution_count": exact_solutions,
        "shipping_candidate_count": candidate_count,
        "shipping_exact_valid_fraction": exact_fraction,
        "shipping_sample_hits": guess_hits,
        "shipping_sample_total": guess_total,
        "baseline_wall_seconds": reference_seconds,
        "baseline_max_word_operations": max(reference_operations),
        "baseline_total_word_operations": sum(reference_operations),
        "baseline_max_triangles_examined": max(reference_examined),
        "baseline_attempts": len(attack_seeds),
        "baseline_attack": "Theorem-10 exhaustive central-triangle enumeration",
        "failing_restart_wall_seconds": restart_seconds,
        "failing_restart_iterations": restart_iterations,
    }

    report["G6_adversary_panel"] = {
        "pass": True,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "Theorem-10 exhaustive central-triangle enumeration",
            "complexity": "O(N^4) scalar adjacency checks; O(N^3) bit-parallel",
            "wall_clock_sec": reference_seconds,
            "operations_max": max(reference_operations),
            "operations_total": sum(reference_operations),
            "triangles_examined_max": max(reference_examined),
            "solves": f"{reference_successes}/{len(attack_seeds)}, as expected",
        },
        "compact_route": {
            "name": "anchor maximum-overlap followed by disjoint-row invariant",
            "operations_max": max(shortcut_operations),
            "solves": f"{len(attack_seeds)}/{len(attack_seeds)}, as expected",
        },
    }

    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled_params["guide_gap"] *= 2
    doubled = make_instance(seed=424242, **doubled_params)
    ok, why = verify(doubled, doubled["answer"])
    assert ok, why
    base_lower = 6 * (2 * math.comb(ship_params["n"], 3)) ** 2
    doubled_lower = 6 * (2 * math.comb(doubled_params["n"], 3)) ** 2
    assert doubled_lower > base_lower
    report["G7_scales"] = {
        "pass": True,
        "base_factor_order": inst["factor_order"],
        "doubled_factor_order": doubled["factor_order"],
        "base_candidate_lower_bound": base_lower,
        "doubled_candidate_lower_bound": doubled_lower,
        "answer_elements_unchanged": _atomic_elements(doubled["answer"]),
        "planted_verifies": True,
    }

    invariance_checks = 0
    real_transform_checks = 0
    product_symmetry_checks = 0
    unrelated_keys = []
    key_params = {"n": 24, "guide_gap": 1, "mix_rounds": 16}
    for seed in range(20):
        base = make_instance(seed=9000 + seed, **key_params)
        key = canonical_key(base)
        unrelated_keys.append(key)
        rng = random.Random(700_000 + seed)
        p_left = list(range(base["n"]))
        p_right = list(range(base["n"]))
        rng.shuffle(p_left)
        rng.shuffle(p_right)
        transformed = _transform_instance(base, p_left, p_right, reverse_rows=True)
        assert canonical_key(transformed) == key
        invariance_checks += 1
        ok, why = verify(transformed, transformed["answer"])
        assert ok, (seed, why)
        real_transform_checks += 1

        reordered = dict(base)
        reordered["row_order"] = list(reversed(base["row_order"]))
        assert canonical_key(reordered) == key
        invariance_checks += 1
        swapped = sorted([[v, u] for u, v in base["answer"]])
        ok, why = verify(base, swapped)
        assert ok, (seed, why)
        product_symmetry_checks += 1
    distinct = len(set(unrelated_keys))
    assert distinct == len(unrelated_keys)
    report["G8_canonical_key"] = {
        "pass": True,
        "invariance_checks": invariance_checks,
        "real_transform_checks": real_transform_checks,
        "product_coordinate_swap_checks": product_symmetry_checks,
        "distinct_unrelated": distinct,
        "unrelated_total": len(unrelated_keys),
        "symmetries": (
            "independent left/right vertex relabelling, input-row reordering, "
            "and direct-product coordinate swap"
        ),
    }

    compact = json.dumps(inst["answer"], separators=(",", ":"))
    answer_chars = len(compact)
    answer_tokens_upper = answer_chars
    answer_elements = _atomic_elements(inst["answer"])
    shortcut, intended_operations = _shortcut_decode(inst)
    assert shortcut is not None and verify(inst, shortcut)[0]
    within_caps = (
        answer_chars <= 2000
        and answer_tokens_upper <= 500
        and answer_elements <= 256
        and intended_operations <= 300
    )
    arms = {
        name: dict(G9_ORACLE_RESULTS[name])
        for name in ("bare", "hinted", "placebo")
    }
    hinted_rate = (
        arms["hinted"]["solved"] / arms["hinted"]["attempts"]
        if arms["hinted"]["attempts"] else 0.0
    )
    placebo_rate = (
        arms["placebo"]["solved"] / arms["placebo"]["attempts"]
        if arms["placebo"]["attempts"] else 0.0
    )
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens_upper,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_operations,
        "token_measure": "conservative one-token-per-character upper bound",
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for name, value in report.items()
        if name.startswith("G") and name[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2))
