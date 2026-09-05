"""Verified problem generator for arXiv:2005.13305.

The paper's Section 3, Theorem 9 constructs a Deza graph from a strongly
regular graph M and a fixed-point-free Seidel involution P: N=P(M+I).  This
module samples P and an affine relabelling first, then forms N.  A solver must
recover P as a compact affine permutation-matrix certificate.
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
import time


TRACK = "B"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "matrix_certificate",
    "native_objects": [
        "adjacency matrices of affinely relabelled switched lattice graphs",
        "affine encodings of permutation matrices for fixed-point-free Seidel involutions",
    ],
    "verification_operations": [
        "exact GF(2) affine-map evaluation",
        "exact adjacency-set comparison",
        "exact common-neighbour counting",
        "fixed-point and involution checks",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "none",
    "reduction": None,
    "reduction_source": "paper_central",
    "intuition_type": "invariant",
    "intuition_description": (
        "The XOR of the packed labels in a switched lattice neighborhood is "
        "its centre even after an affine change of basis; without that invariant "
        "one reconstructs the strongly regular child by common-neighbour counts."
    ),
    "hardness_basis": (
        "Track B: Section 3, Theorem 9 gives N=P(M+I); the standard exact "
        "algorithm forms N^2 and matches rows against closed child neighborhoods "
        "in O(L*v^3). At the shipping preset (three 64-vertex layers) "
        "it uses 387,072 elementary adjacency comparisons (6,048 machine-word "
        "intersections, with measured wall-clock in selftest), versus 90 exact "
        "XORs after the affine lattice-cross invariant is recognized."
    ),
    "max_answer_tokens": 15,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": list(PROBLEM_PROFILE["native_objects"]),
    "intuition": PROBLEM_PROFILE["intuition_type"] + ": " + PROBLEM_PROFILE["intuition_description"],
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 1, "side_bits": 2},
    "easy": {"n": 3, "side_bits": 3},
    "medium": {"n": 3, "side_bits": 4},
    "hard": {"n": 4, "side_bits": 4},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "Packed-neighborhood XOR is invariant under the hidden affine relabelling "
    "and equals the switched closed-neighborhood centre."
)
PLACEBO_HINT = (
    "Careful bookkeeping is useful when comparing the numbered layers and "
    "their listed neighborhoods."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "One affine GF(2)^d permutation per layer, encoded by the two packed "
        "d-bit integers u and b while the nonzero covector v is displayed in "
        "the instance. A demo d=4 map is a nonzero translation (u=0); every "
        "larger map is a fixed-point-free rank-one affine transvection involution."
    ),
    "bounds": {
        "layers": "n",
        "integers_per_layer": 2,
        "dimension": [4, 6, 8],
        "integer_range": "0 through 2^d-1",
        "linear_rank": {"d=4": 0, "d>=6": 1},
    },
}

G9_ORACLE_RESULTS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 2, "attempts": 3},
    "placebo": {"solved": 1, "attempts": 3},
    "hinted_verdict": "too_easy",
}

NOTES = r"""
Definition and construction. Section 1 defines a Seidel automorphism as an
involutive graph automorphism that interchanges only non-adjacent vertices,
and gives M^2=aA+bB+kI for the two children of a Deza graph. Section 3,
Theorem 9 proves that P(M+I) is a Deza adjacency matrix with children M and
J-I-M when M is strongly regular and P is a fixed-point-free Seidel
automorphism. Example 7 applies it to the lattice graph L_2(n), n even.

Step 0. This cannot honestly be Track A: Theorem 9 is an explicit polynomial
certificate-producing construction. It is Track B. Mechanically, square the
displayed N, recover the child M by its common-neighbor counts, and match every
row of N to a closed-neighborhood row of M. At the shipping preset this
is 387,072 elementary adjacency comparisons before row matching. The compact
route uses the fact that a closed L_2(8) neighborhood is a 15-vertex row-column
cross whose packed labels XOR to its centre. An affine relabelling preserves
that identity because 15 is odd. XORing the rows at 0 and at one basis vector
selected by the displayed covector recovers b and u, so three layers cost 90
exact XORs.

Generation. In original L_2(8) coordinates, one coordinate factor is a
fixed-point-free affine transvection and the other is a nonzero translation;
both are involutions and both move every coordinate. Their product P therefore
moves each lattice vertex to a different row and column, making P a Seidel
involution. Each layer then receives an independently sampled invertible
affine relabelling that mixes all coordinate bits. N=P(M+I) is assembled
directly. The answer is carried through the relabelling, never recovered from
N. The public covector v is part of each instance; the answer contains only u
and b. The demo uses L_2(4) and two translations.

Attacks. Affine mixing defeats visible row/column modes. All vertices have the
same degree. The panel tries a first-neighbor guess, a fixed lexicographic
transvection, recovering P(0) but taking the lexicographically first compatible
u, reusing one correctly recovered layer certificate on the other independently
relabelled layers, and 256 uniform restarts. The common-neighbor child
reconstruction is the successful Track B reference algorithm and is reported
separately.

Canonicalization. Layers share the public GF(2)^d ground set, so a relabelling
acts on all layers simultaneously. The key ignores neighbor and layer order
and is invariant under a common affine change of basis. It uses the complete
histogram of layer-colored edges, sorted per-vertex colored-degree profiles,
and pairwise cycle types of the recovered maps, minimized over layer order.
This is a strong cheap multiplex invariant, not a general graph-isomorphism
algorithm.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_FENCE_RE = re.compile(r"```(?:json|text)?\s*(.*?)```", re.I | re.S)


def _parity(x: int) -> int:
    return x.bit_count() & 1


def _basis(bits: int) -> list[int]:
    return [0] + [1 << i for i in range(bits)]


def _linear_apply(rows: tuple[int, ...] | list[int], x: int) -> int:
    return sum(_parity(row & x) << i for i, row in enumerate(rows))


def _rank(rows: list[int], bits: int) -> int:
    work = list(rows)
    rank = 0
    for col in range(bits):
        pivot = next((i for i in range(rank, bits) if (work[i] >> col) & 1), None)
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        for i in range(bits):
            if i != rank and ((work[i] >> col) & 1):
                work[i] ^= work[rank]
        rank += 1
    return rank


def _random_invertible(bits: int, rng: random.Random) -> tuple[int, ...]:
    rows = [1 << i for i in range(bits)]
    for _ in range(8 * bits + rng.randrange(8 * bits + 1)):
        i, j = rng.sample(range(bits), 2)
        if rng.randrange(3):
            rows[i] ^= rows[j]
        else:
            rows[i], rows[j] = rows[j], rows[i]
    assert _rank(rows, bits) == bits
    return tuple(rows)


def _map_count(dimension: int) -> int:
    m = 1 << dimension
    if dimension == 4:
        return m - 1
    if dimension >= 6 and dimension % 2 == 0:
        # v is part of the instance.  Choose nonzero u in v^perp, then b in
        # v^perp \ {0,u}.
        return (m // 2 - 1) * (m // 2 - 2)
    raise ValueError("unsupported public dimension")


def _sample_translation(bits: int, rng: random.Random) -> tuple[int, int, int]:
    return 0, 0, rng.randrange(1, 1 << bits)


def _sample_transvection(bits: int, rng: random.Random) -> tuple[int, int, int]:
    m = 1 << bits
    u = rng.randrange(1, m)
    v_choices = [v for v in range(1, m) if _parity(u & v) == 0]
    v = rng.choice(v_choices)
    b_choices = [b for b in range(m) if _parity(v & b) == 0 and b not in (0, u)]
    return u, v, rng.choice(b_choices)


def _sample_for_covector(bits: int, v: int, rng: random.Random) -> tuple[int, int, int]:
    """Uniformly sample (u,v,b) from the stated language for fixed v."""
    m = 1 << bits
    u = rng.choice([x for x in range(1, m) if _parity(v & x) == 0])
    b = rng.choice([x for x in range(1, m) if x != u and _parity(v & x) == 0])
    return u, v, b


def _apply_params(params: tuple[int, int, int], x: int) -> int:
    u, v, b = params
    return x ^ (u if u and _parity(v & x) else 0) ^ b


def _params_images(params: tuple[int, int, int], bits: int) -> list[int]:
    return [_apply_params(params, x) for x in _basis(bits)]


def _params_from_images(images: object, dimension: int) -> tuple[tuple[int, int, int] | None, str]:
    m = 1 << dimension
    if not isinstance(images, list) or len(images) != dimension + 1:
        return None, f"map must have {dimension + 1} images"
    for i, value in enumerate(images):
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < m:
            return None, f"image {i} out of range [0,{m - 1}]"
    b = images[0]
    deltas = [images[i + 1] ^ b ^ (1 << i) for i in range(dimension)]
    nonzero = {x for x in deltas if x}
    if not nonzero:
        if b == 0:
            return None, "translation must be nonzero"
        return (0, 0, b), "ok"
    if len(nonzero) != 1:
        return None, "linear part is not rank one"
    u = next(iter(nonzero))
    v = sum(1 << i for i, delta in enumerate(deltas) if delta == u)
    if _parity(u & v):
        return None, "linear part is not an involutory transvection"
    if _parity(v & b) or b in (0, u):
        return None, "affine transvection has a fixed point or is not involutory"
    return (u, v, b), "ok"


def _certificate_from_params(params: tuple[int, int, int]) -> dict[str, int]:
    u, _v, b = params
    return {"u": u, "b": b}


def _params_from_certificate(layer: dict, certificate: object):
    dimension = 2 * layer["side_bits"]
    limit = 1 << dimension
    if not isinstance(certificate, dict) or set(certificate) != {"u", "b"}:
        return None, "map must be an object with exactly integer keys 'u' and 'b'"
    u, b = certificate["u"], certificate["b"]
    if isinstance(u, bool) or not isinstance(u, int) or not 0 <= u < limit:
        return None, f"u out of range [0,{limit - 1}]"
    if isinstance(b, bool) or not isinstance(b, int) or not 0 <= b < limit:
        return None, f"b out of range [0,{limit - 1}]"
    if dimension == 4:
        if u != 0:
            return None, "demo translation requires u=0"
        if b == 0:
            return None, "translation b must be nonzero"
        return (0, 0, b), "ok"
    v = layer.get("v")
    if isinstance(v, bool) or not isinstance(v, int) or not 0 < v < limit:
        return None, "instance covector v is malformed"
    if u == 0:
        return None, "transvection vector u must be nonzero"
    if _parity(u & v):
        return None, "u is not orthogonal to the displayed v"
    if _parity(v & b):
        return None, "b is not orthogonal to the displayed v"
    if b in (0, u):
        return None, "b must be distinct from both 0 and u"
    return (u, v, b), "ok"


def _affine_table(rows: tuple[int, ...], offset: int) -> tuple[list[int], list[int]]:
    size = 1 << len(rows)
    forward = [_linear_apply(rows, x) ^ offset for x in range(size)]
    inverse = [0] * size
    for x, y in enumerate(forward):
        inverse[y] = x
    return forward, inverse


def _original_permutation(side_bits: int, rng: random.Random):
    if side_bits == 2:
        row = _sample_translation(side_bits, rng)
        col = _sample_translation(side_bits, rng)
    else:
        row = _sample_transvection(side_bits, rng)
        col = _sample_translation(side_bits, rng)
        if rng.randrange(2):
            row, col = col, row
    side = 1 << side_bits

    def apply(z: int) -> int:
        x, y = divmod(z, side)
        return side * _apply_params(row, x) + _apply_params(col, y)

    return apply


def _build_layer(side_bits: int, rng: random.Random) -> tuple[dict, dict[str, int]]:
    side = 1 << side_bits
    dimension = 2 * side_bits
    vertex_count = side * side
    original_p = _original_permutation(side_bits, rng)
    rows = _random_invertible(dimension, rng)
    offset = rng.randrange(vertex_count)
    relabel, inverse = _affine_table(rows, offset)

    def public_p(z: int) -> int:
        return relabel[original_p(inverse[z])]

    adjacency = [[] for _ in range(vertex_count)]
    for old_z in range(vertex_count):
        old_centre = original_p(old_z)
        a, b = divmod(old_centre, side)
        old_neighbors = [side * a + q for q in range(side)]
        old_neighbors.extend(side * q + b for q in range(side) if q != a)
        public_z = relabel[old_z]
        adjacency[public_z] = [relabel[q] for q in old_neighbors]
        rng.shuffle(adjacency[public_z])
    images = [public_p(x) for x in _basis(dimension)]
    public_params, why = _params_from_images(images, dimension)
    assert public_params is not None, why
    layer = {
        "side_bits": side_bits,
        "v": public_params[1],
        "adjacency": adjacency,
    }
    return layer, _certificate_from_params(public_params)


def make_instance(n: int, seed: int = 0, side_bits: int = 3, **params) -> dict:
    """Sample P and affine coordinates, then build N=P(M+I) exactly."""
    if params:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(params)))
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer")
    if side_bits not in (2, 3, 4):
        raise ValueError("side_bits must be 2, 3, or 4")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    rng = random.Random(seed)
    built = []
    answers_seen = set()
    for _ in range(n):
        for _attempt in range(1000):
            layer, answer = _build_layer(side_bits, rng)
            answer_key = (answer["u"], layer["v"], answer["b"])
            if answer_key not in answers_seen:
                answers_seen.add(answer_key)
                built.append((layer, answer))
                break
        else:
            raise RuntimeError("could not sample distinct layer permutations")
    rng.shuffle(built)
    return {
        "family": "affine Seidel recovery in switched lattice graphs",
        "layers": [x[0] for x in built],
        "answer": {"maps": [x[1] for x in built]},
    }


def render(inst: dict) -> str:
    lines = [
        "Recover Seidel involutions from switched lattice graphs.",
        "",
        "A simple graph is strongly regular with parameters (v,k,lambda,mu) if",
        "it has v vertices, every vertex has k neighbors, adjacent vertex pairs",
        "have lambda common neighbors, and distinct nonadjacent pairs have mu.",
        "A Seidel involution P is a graph automorphism with P(P(x))=x that maps",
        "every vertex to a distinct nonneighbor.",
        "",
        "Each layer below is a complete undirected adjacency list on vertices",
        "0,...,2^d-1. Vertex labels denote d-bit vectors: addition is bitwise XOR",
        "and e_i is the integer 2^i. List order carries no information.",
        "",
        "For each layer there is an unknown strongly regular graph M and an",
        "unknown fixed-point-free Seidel involution P of M. The displayed",
        "adjacency matrix is exactly N=P(M+I), where I is the identity matrix.",
        "For d=2s, M is an affinely relabelled lattice graph L_2(2^s). It has",
        "vertices (r,c), joining two distinct vertices exactly when they share r",
        "or c, and strongly regular parameters (2^(2s),2(2^s-1),2^s-2,2).",
        "Different layers use independent hidden affine",
        "lattice coordinates on the same public vector space.",
        "",
        "Certificate language. For each layer output the two packed d-bit integers",
        "u and b. The integer v is displayed with that layer and the map is exactly",
        "P(x)=x XOR (u if parity(v AND x)=1 else 0) XOR b.",
        "For d=4, v=u=0 and b is nonzero. For d>=6, u and v are nonzero,",
        "parity(u AND v)=parity(v AND b)=0, and b is neither 0 nor u.",
        "",
    ]
    for i, layer in enumerate(inst["layers"]):
        dimension = 2 * layer["side_bits"]
        lines.append(
            f"LAYER {i}: d={dimension}, vertices 0..{(1 << dimension) - 1}, "
            f"v={layer['v']}"
        )
        for z, neighbors in enumerate(layer["adjacency"]):
            lines.append(f"{z}: " + ",".join(str(q) for q in neighbors))
        lines.append("")
    lines.extend([
        "Give your final answer inside <answer></answer> tags as one JSON object",
        "with exactly this shape: {\"maps\":[{\"u\":...,\"b\":...}, ...]}",
        "Use the displayed layer order and exactly one u,b object per layer.",
        "Example for one d=4 translation:",
        '<answer>{"maps":[{"u":0,"b":1}]}</answer>',
        "Output nothing else inside the tags.",
    ])
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        lines.extend(["", "Hint: " + STRUCTURAL_HINT])
    elif mode == "placebo":
        lines.extend(["", "Hint: " + PLACEBO_HINT])
    return "\n".join(lines)


def parse_answer(text: object) -> object | None:
    if not isinstance(text, str):
        return None
    match = _ANSWER_RE.search(text)
    candidates = [match.group(1)] if match else []
    candidates.extend(m.group(1) for m in _FENCE_RE.finditer(text))
    candidates.append(text)
    decoder = json.JSONDecoder()
    for candidate in candidates:
        body = candidate.strip()
        fence = _FENCE_RE.fullmatch(body)
        if fence:
            body = fence.group(1).strip()
        try:
            value = json.loads(body)
            if isinstance(value, dict):
                return value
        except (TypeError, ValueError):
            pass
        for pos, char in enumerate(body):
            if char != "{":
                continue
            try:
                value, _end = decoder.raw_decode(body[pos:])
            except (TypeError, ValueError):
                continue
            if isinstance(value, dict):
                return value
    return None


def _parse_maps(inst: dict, answer: object):
    if not isinstance(answer, dict) or set(answer) != {"maps"}:
        return None, "answer must be an object with exactly the key 'maps'"
    maps = answer["maps"]
    if not isinstance(maps, list) or len(maps) != len(inst["layers"]):
        return None, f"expected {len(inst['layers'])} map certificates"
    params = []
    for i, (layer, certificate) in enumerate(zip(inst["layers"], maps)):
        parsed, why = _params_from_certificate(layer, certificate)
        if parsed is None:
            return None, f"layer {i} {why}"
        params.append(parsed)
    return params, "ok"


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    params, why = _parse_maps(inst, answer)
    if params is None:
        return False, why
    for layer_index, (layer, p_params) in enumerate(zip(inst["layers"], params)):
        side = 1 << layer["side_bits"]
        dimension = 2 * layer["side_bits"]
        vertex_count = 1 << dimension
        adjacency = layer.get("adjacency")
        expected_degree = 2 * side - 1
        if not isinstance(adjacency, list) or len(adjacency) != vertex_count:
            return False, f"instance layer {layer_index} has malformed adjacency data"
        nsets = []
        for z, row in enumerate(adjacency):
            if not isinstance(row, list) or len(row) != expected_degree:
                return False, f"instance layer {layer_index} row {z} has wrong degree"
            shown = set(row)
            if len(shown) != len(row) or z in shown or any(
                isinstance(q, bool) or not isinstance(q, int) or not 0 <= q < vertex_count
                for q in row
            ):
                return False, f"instance layer {layer_index} row {z} is not a simple neighborhood"
            nsets.append(shown)
        if any(x not in nsets[y] for x in range(vertex_count) for y in nsets[x]):
            return False, f"instance layer {layer_index} adjacency is not symmetric"

        permutation = [_apply_params(p_params, x) for x in range(vertex_count)]
        child = []
        for x in range(vertex_count):
            row = set(nsets[permutation[x]])
            if x not in row:
                return False, f"layer {layer_index} P(M+I) identity misses diagonal at {x}"
            row.remove(x)
            child.append(row)
        child_degree = 2 * (side - 1)
        if any(len(row) != child_degree for row in child):
            return False, f"layer {layer_index} reconstructed child has wrong degree"
        if any(x in child[x] for x in range(vertex_count)) or any(
            x not in child[y] for x in range(vertex_count) for y in child[x]
        ):
            return False, f"layer {layer_index} reconstructed child is not a simple undirected graph"
        for x in range(vertex_count):
            if permutation[x] in child[x]:
                return False, f"layer {layer_index} P moves vertex {x} to a neighbor"
            if {permutation[q] for q in child[x]} != child[permutation[x]]:
                return False, f"layer {layer_index} P is not a child automorphism at {x}"
        lam = side - 2
        for x in range(vertex_count):
            for y in range(x + 1, vertex_count):
                common = len(child[x] & child[y])
                target = lam if y in child[x] else 2
                if common != target:
                    return False, f"layer {layer_index} child common-neighbor mismatch at {x},{y}"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    maps = []
    for layer in inst["layers"]:
        dimension = 2 * layer["side_bits"]
        params = (
            _sample_translation(dimension, rng)
            if dimension == 4
            else _sample_for_covector(dimension, layer["v"], rng)
        )
        maps.append(_certificate_from_params(params))
    return {"maps": maps}


def search_space(inst: dict) -> int:
    result = 1
    for layer in inst["layers"]:
        result *= _map_count(2 * layer["side_bits"])
    return result


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space > 200_000:
        return None
    layer = inst["layers"][0] if len(inst["layers"]) == 1 else None
    if layer is None or 2 * layer["side_bits"] != 4:
        return None
    count = 0
    for b in range(1, 16):
        count += int(verify(inst, {"maps": [{"u": 0, "b": b}]})[0])
    return count


def _compact_recover(inst: dict) -> dict:
    maps = []
    for layer in inst["layers"]:
        dimension = 2 * layer["side_bits"]
        b = 0
        for q in layer["adjacency"][0]:
            b ^= q
        if dimension == 4:
            maps.append({"u": 0, "b": b})
            continue
        v = layer["v"]
        x = v & -v
        centre = 0
        for q in layer["adjacency"][x]:
            centre ^= q
        maps.append({"u": centre ^ x ^ b, "b": b})
    return {"maps": maps}


def _reference_recover(inst: dict):
    started = time.perf_counter()
    maps = []
    intersections = elementary = row_lookups = 0
    for layer in inst["layers"]:
        side = 1 << layer["side_bits"]
        dimension = 2 * layer["side_bits"]
        vertex_count = 1 << dimension
        masks = []
        for row in layer["adjacency"]:
            mask = 0
            for q in row:
                mask |= 1 << q
            masks.append(mask)
        child = [0] * vertex_count
        for x in range(vertex_count):
            for y in range(x + 1, vertex_count):
                intersections += 1
                elementary += vertex_count
                if (masks[x] & masks[y]).bit_count() == side:
                    child[x] |= 1 << y
                    child[y] |= 1 << x
        closed = {child[y] | (1 << y): y for y in range(vertex_count)}
        if len(closed) != vertex_count:
            return None, {"error": "nonunique child rows"}
        permutation = []
        for x in range(vertex_count):
            row_lookups += 1
            if masks[x] not in closed:
                return None, {"error": "closed-row match failed"}
            permutation.append(closed[masks[x]])
        b = permutation[0]
        if dimension == 4:
            maps.append({"u": 0, "b": b})
        else:
            v = layer["v"]
            x = v & -v
            maps.append({"u": permutation[x] ^ x ^ b, "b": b})
    return {"maps": maps}, {
        "wall_clock_sec": time.perf_counter() - started,
        "bitset_intersections": intersections,
        "row_hash_lookups": row_lookups,
        "elementary_adjacency_comparisons": elementary,
    }


def _cycle_type(permutation: list[int]) -> tuple[int, ...]:
    seen = [False] * len(permutation)
    out = []
    for start in range(len(permutation)):
        if seen[start]:
            continue
        x = start
        length = 0
        while not seen[x]:
            seen[x] = True
            length += 1
            x = permutation[x]
        out.append(length)
    return tuple(sorted(out))


def canonical_key(inst: dict) -> str:
    """Strong multiplex invariant, independent of layer and neighbor order."""
    recovered = _compact_recover(inst)
    layer_count = len(inst["layers"])
    vertex_count = len(inst["layers"][0]["adjacency"])
    if any(len(layer["adjacency"]) != vertex_count for layer in inst["layers"]):
        payload = [(len(layer["adjacency"]),) for layer in inst["layers"]]
        return hashlib.sha256(repr(sorted(payload)).encode()).hexdigest()
    sets = [[set(row) for row in layer["adjacency"]] for layer in inst["layers"]]
    full_maps = []
    for layer, certificate in zip(inst["layers"], recovered["maps"]):
        parsed, why = _params_from_certificate(layer, certificate)
        if parsed is None:
            raise ValueError(why)
        full_maps.append([_apply_params(parsed, x) for x in range(vertex_count)])
    best = None
    orders = itertools.permutations(range(layer_count)) if layer_count <= 7 else [tuple(range(layer_count))]
    for order in orders:
        edge_hist = [0] * (1 << layer_count)
        local = [[0] * (1 << layer_count) for _ in range(vertex_count)]
        for x in range(vertex_count):
            for y in range(x + 1, vertex_count):
                mask = 0
                for new_bit, old_layer in enumerate(order):
                    if y in sets[old_layer][x]:
                        mask |= 1 << new_bit
                edge_hist[mask] += 1
                local[x][mask] += 1
                local[y][mask] += 1
        product_types = []
        for pos, i in enumerate(order):
            for j in order[pos + 1:]:
                composition = [full_maps[i][full_maps[j][x]] for x in range(vertex_count)]
                product_types.append(_cycle_type(composition))
        signature = (tuple(edge_hist), tuple(sorted(tuple(row) for row in local)), tuple(product_types))
        encoded = repr(signature)
        if best is None or encoded < best:
            best = encoded
    return hashlib.sha256(best.encode()).hexdigest()


def escalate(params: dict) -> dict | str | None:
    n = params.get("n")
    side_bits = params.get("side_bits", 3)
    if side_bits == 3:
        return {"n": max(3, int(n or 1)), "side_bits": 4}
    if side_bits == 4 and isinstance(n, int) and n < 4:
        return {"n": n + 1, "side_bits": 4}
    return None


def _lex_certificate(layer: dict, b: int | None = None) -> dict[str, int]:
    dimension = 2 * layer["side_bits"]
    if dimension == 4:
        return {"u": 0, "b": b if b in range(1, 1 << dimension) else 1}
    v = layer["v"]
    legal_u = [u for u in range(1, 1 << dimension) if _parity(u & v) == 0]
    if b is None or not 0 < b < (1 << dimension) or _parity(v & b):
        b = next(x for x in legal_u if x != legal_u[0])
    u = next(x for x in legal_u if x != b)
    return {"u": u, "b": b}


def _first_neighbor_attack(inst: dict) -> object:
    return {"maps": [_lex_certificate(layer, layer["adjacency"][0][0]) for layer in inst["layers"]]}


def _lexicographic_attack(inst: dict) -> object:
    return {"maps": [_lex_certificate(layer) for layer in inst["layers"]]}


def _anchor_lex_linear_attack(inst: dict) -> object:
    maps = []
    for layer in inst["layers"]:
        b = 0
        for q in layer["adjacency"][0]:
            b ^= q
        maps.append(_lex_certificate(layer, b))
    return {"maps": maps}


def _reuse_first_attack(inst: dict) -> object:
    exact = _compact_recover(inst)
    return {"maps": [dict(exact["maps"][0]) for _ in inst["layers"]]}


def _common_affine_relabel(inst: dict, seed: int):
    rng = random.Random(seed)
    dimension = 2 * inst["layers"][0]["side_bits"]
    vertex_count = 1 << dimension
    rows = _random_invertible(dimension, rng)
    offset = rng.randrange(vertex_count)
    relabel, inverse = _affine_table(rows, offset)
    exact = _compact_recover(inst)
    transformed = []
    answers = []
    for layer, certificate in zip(inst["layers"], exact["maps"]):
        params, why = _params_from_certificate(layer, certificate)
        assert params is not None, why

        def new_p(x: int) -> int:
            return relabel[_apply_params(params, inverse[x])]

        adjacency = [[] for _ in range(vertex_count)]
        for old_z, row in enumerate(layer["adjacency"]):
            new_z = relabel[old_z]
            adjacency[new_z] = [relabel[q] for q in row]
            rng.shuffle(adjacency[new_z])
        images = [new_p(x) for x in _basis(dimension)]
        new_params, why = _params_from_images(images, dimension)
        assert new_params is not None, why
        transformed.append({
            "side_bits": layer["side_bits"],
            "v": new_params[1],
            "adjacency": adjacency,
        })
        answers.append(_certificate_from_params(new_params))
    order = list(range(len(transformed)))
    rng.shuffle(order)
    out = {
        "family": inst["family"],
        "layers": [transformed[i] for i in order],
        "answer": {"maps": [answers[i] for i in order]},
    }
    return out, out["answer"]


def _corruptions(inst: dict) -> dict[str, object]:
    answer = copy.deepcopy(inst["answer"])
    drop = copy.deepcopy(answer)
    drop["maps"][0].pop("b")
    swap = copy.deepcopy(answer)
    swap["maps"][0], swap["maps"][1] = swap["maps"][1], swap["maps"][0]
    duplicate = copy.deepcopy(answer)
    duplicate["maps"][0]["b"] = duplicate["maps"][0]["u"]
    out_of_range = copy.deepcopy(answer)
    dimension = 2 * inst["layers"][0]["side_bits"]
    out_of_range["maps"][0]["b"] = 1 << dimension
    return {"drop": drop, "swap": swap, "duplicate": duplicate, "empty": {}, "out_of_range": out_of_range}


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(x) for x in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(x) for x in value)
    return 1


def selftest() -> dict:
    report = {}
    checks = json_checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(5):
            inst = make_instance(seed=seed, **params)
            ok, why = verify(inst, inst["answer"])
            assert ok, (preset, seed, why)
            checks += 1
            assert json.loads(json.dumps(inst["answer"])) == inst["answer"]
            json_checks += 1
    report["G1_planted_verifies"] = {"pass": True, "checks": checks, "json_native_checks": json_checks}

    ship = make_instance(seed=37, **DIFFICULTY[SHIPPING_DIFFICULTY])
    reasons = {}
    for name, candidate in _corruptions(ship).items():
        ok, why = verify(ship, candidate)
        assert not ok, (name, why)
        reasons[name] = why
    assert len(set(reasons.values())) == len(reasons), reasons
    report["G2_rejects_corruption"] = {"pass": True, "reasons": reasons}

    realistic = "Reasoning omitted.\n```json\n<answer>\n" + json.dumps(ship["answer"]) + "\n</answer>\n```\n"
    assert parse_answer(realistic) == ship["answer"]
    assert parse_answer("Reasoning omitted.\n```json\n" + json.dumps(ship["answer"]) + "\n```") == ship["answer"]
    assert parse_answer("garbage") is None
    report["G3_round_trip"] = {"pass": True, "prose_and_fence": True}

    samples = 200_000
    hits = 0
    guess_rng = random.Random(910247)
    for _ in range(samples):
        hits += int(verify(ship, random_candidate(ship, guess_rng))[0])
    density = hits / samples
    assert density < 1e-6
    report["G4_guess_resistance"] = {
        "pass": True, "hits": hits, "total": samples,
        "observed_probability": density, "structure_aware_space": search_space(ship),
    }

    reference_stats = []
    successes = 0
    for seed in range(8):
        inst = make_instance(seed=1000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        candidate, stats = _reference_recover(inst)
        successes += int(candidate is not None and verify(inst, candidate)[0])
        reference_stats.append(stats)
    assert successes == 8
    average_reference = {
        key: sum(float(x[key]) for x in reference_stats) / len(reference_stats)
        for key in ("wall_clock_sec", "bitset_intersections", "row_hash_lookups", "elementary_adjacency_comparisons")
    }
    demo = make_instance(seed=7, **DIFFICULTY["demo"])
    report["G5_density_and_baseline"] = {
        "pass": True,
        "shipping_density": {"hits": hits, "total": samples, "fraction": density},
        "demo_exact_valid_answers": enumerate_all(demo),
        "demo_search_space": search_space(demo),
        "baseline_wall_clock_sec": average_reference["wall_clock_sec"],
        "baseline_operations": average_reference["elementary_adjacency_comparisons"],
        "reference_average": average_reference,
    }

    attacks = {
        "degree_tie_then_first_neighbor": {"successes": 0, "attempts": 8},
        "greedy_lexicographic_transvection": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "anchor_then_lexicographic_linear_part": {"successes": 0, "attempts": 8},
        "reuse_first_layer_map": {"successes": 0, "attempts": 8},
    }
    attack_rng = random.Random(481516)
    for seed in range(8):
        inst = make_instance(seed=7000 + seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        fixed = {
            "degree_tie_then_first_neighbor": _first_neighbor_attack(inst),
            "greedy_lexicographic_transvection": _lexicographic_attack(inst),
            "anchor_then_lexicographic_linear_part": _anchor_lex_linear_attack(inst),
            "reuse_first_layer_map": _reuse_first_attack(inst),
        }
        for name, candidate in fixed.items():
            attacks[name]["successes"] += int(verify(inst, candidate)[0])
        solved = False
        for _ in range(256):
            if verify(inst, random_candidate(inst, attack_rng))[0]:
                solved = True
                break
        attacks["random_restart_256"]["successes"] += int(solved)
    assert all(x["successes"] == 0 for x in attacks.values())
    report["G6_adversary_panel"] = {
        "pass": True,
        "attacks": attacks,
        "reference_algorithm": {
            "name": "common-neighbour child reconstruction plus closed-row matching",
            "complexity": "O(sum over layers of v^3) elementary adjacency comparisons",
            "wall_clock_sec": average_reference["wall_clock_sec"],
            "operations": average_reference["elementary_adjacency_comparisons"],
            "bitset_intersections": average_reference["bitset_intersections"],
            "solves": "8/8, as expected",
        },
    }

    doubled = make_instance(n=2 * DIFFICULTY[SHIPPING_DIFFICULTY]["n"], side_bits=3, seed=99)
    ok, why = verify(doubled, doubled["answer"])
    assert ok, why
    assert len(render(doubled)) > len(render(ship))
    report["G7_scales"] = {
        "pass": True, "shipping_layers": len(ship["layers"]),
        "doubled_layers": len(doubled["layers"]), "doubled_planted_verifies": True,
    }

    keys = []
    invariant = carried = 0
    for seed in range(20):
        inst = make_instance(seed=seed, **DIFFICULTY[SHIPPING_DIFFICULTY])
        key = canonical_key(inst)
        keys.append(key)
        changed, changed_answer = _common_affine_relabel(inst, 90000 + seed)
        assert canonical_key(changed) == key
        invariant += 1
        ok, why = verify(changed, changed_answer)
        assert ok, why
        carried += 1
    assert len(set(keys)) == 20, len(set(keys))
    report["G8_canonical_key"] = {
        "pass": True, "invariance_checks": invariant, "carried_witness_checks": carried,
        "distinct_unrelated": len(set(keys)), "unrelated_attempts": 20,
        "symmetries": ["neighbor-list reorder", "layer reorder", "common affine change of basis and translation"],
    }

    blob = json.dumps(ship["answer"], separators=(",", ":"))
    atoms = _answer_atoms(ship["answer"])
    tokens = math.ceil(len(blob) / 4)
    intended_ops = sum(
        (len(layer["adjacency"][0]) - 1)
        if 2 * layer["side_bits"] == 4
        else 2 * (len(layer["adjacency"][0]) - 1) + 2
        for layer in ship["layers"]
    )
    assert len(blob) <= 2000 and atoms <= 256 and intended_ops <= 300
    arms = {name: dict(G9_ORACLE_RESULTS[name]) for name in ("bare", "hinted", "placebo")}
    hinted_rate = arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
    placebo_rate = arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    report["G9_no_tool_suitability"] = {
        "pass": True, "arms": arms, "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": G9_ORACLE_RESULTS["hinted_verdict"],
        "answer_chars": len(blob), "answer_tokens": tokens, "answer_elements": atoms,
        "intended_route_operations": intended_ops,
    }
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
