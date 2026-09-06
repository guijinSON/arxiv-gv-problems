"""Inverse-planted exact-weight binary syndrome decoding instances.

The paper's Definition 3.1 calls the XOR of exactly h distinct vectors an
h-linear combination over F_2.  This module asks for the support of one such
combination with a prescribed value.  Equivalently, for the displayed matrix
H and syndrome s, find a binary vector x of Hamming weight exactly h such that
H x^T = s.

Only Python's standard library is used.  Importing this module has no side
effects.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
import hashlib
import json
import math
import random
import re


DIFFICULTY = {
    "demo": {
        "n": 24,
        "rows": 12,
        "weight": 4,
        "marker_vertices": 5,
        "marker_edges": 6,
    },
    "easy": {
        "n": 160,
        "rows": 92,
        "weight": 16,
        "marker_vertices": 12,
        "marker_edges": 18,
    },
    "medium": {
        "n": 208,
        "rows": 120,
        "weight": 20,
        "marker_vertices": 14,
        "marker_edges": 22,
    },
    "hard": {
        "n": 256,
        "rows": 148,
        "weight": 24,
        "marker_vertices": 16,
        "marker_edges": 26,
    },
}

SHIPPING_DIFFICULTY = "easy"

NOTES = r"""
Paper: V. C. Guerrero Pantoja, J. H. Castillo, and C. A. Trujillo
Solarte, "S_h-sets and linear codes over F_q", arXiv:2411.19413v2.

Definition source.  Section 3, Definitions 3.1 and 3.2 fix the important
semantics: an h-linear combination uses exactly h distinct set elements and
nonzero field coefficients, with permutations omitted.  Over F_2 every
coefficient is 1, so a witness is exactly h distinct column indices whose XOR
is the target.  Theorem 3.1 supplies the parity-check-matrix correspondence.

Easy regimes avoided.  Lemma 3.1 says every linearly independent set is
automatically S_h-linear, so asking a solver to reproduce such a construction
would be a lookup, not a hard search.  The paper's Example after Theorem 3.2
also constructs an S_3-linear set directly from a BCH parity-check matrix;
structured decodable codes are therefore not used here.  Small fixed h admits
enumeration/meet-in-the-middle, and small row dimension admits a 2^r syndrome
table.  For restricted systems, Arvind et al. show that equations of size at
most two give a logarithmic-space problem; with at most two occurrences per
variable the exact problem is FPT in h and is in RNC (deterministic polynomial
time remains open).  This generator instead uses dense unstructured columns
and equations, h growing with n, and r growing with n.

Hardness basis.  Exact-weight binary Ax=b is NP-complete (the exact-weight
form is explicitly recorded by Arvind, Koebler, Kuhnert, and Toran,
Algorithmica 75 (2016), 322-338) and is W[1]-hard parameterized by h even when
variable occurrence is bounded by any constant at least three.  Those are
worst-case results, not a proof for this planted distribution; the mandatory
oracle and adversary results are the empirical complement.

Planting and attacks.  The support is sampled before the columns.  Its indices
are independent of a final random column permutation, so planted and decoy
positions have the same distribution.  A small random affine-dependency
gadget makes canonical diversity measurable without using the seed; it is
independent of the planted support.  Self-tests attack position, column
weight, target distance, affine-dependency degree, greedy residual reduction,
and random-restart swap local search.  None is allowed to pass at shipping
difficulty.

Canonical key.  Full equivalence of binary vector configurations under column
permutation and affine change of coordinates is a code/matroid isomorphism
problem.  The key therefore uses a strong cheap invariant: the stable colour
refinement signature of the complete zero-XOR 4-subset hypergraph, together
with low-order target-preimage counts.  It is invariant under column
permutation, GL(r,2), coordinate permutation, and global translation.  It is
not a complete canonical form; non-isomorphic instances can theoretically
collide.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 250_000


def _popcount(value: int) -> int:
    """Number of set bits, compatible with the repository's Python 3.9."""
    return bin(value).count("1")


def _rank(values: list[int]) -> int:
    """Rank of binary column vectors represented by nonnegative integers."""
    pivots: dict[int, int] = {}
    for original in values:
        value = original
        while value:
            bit = value.bit_length() - 1
            if bit in pivots:
                value ^= pivots[bit]
            else:
                pivots[bit] = value
                break
    return len(pivots)


def _affine_rank(values: list[int]) -> int:
    """Dimension of the affine span, invariant under global translation."""
    if not values:
        return 0
    anchor = values[0]
    return _rank([value ^ anchor for value in values[1:]])


def _random_basis(rows: int, rng: random.Random) -> list[int]:
    """Images of the standard basis under a random invertible linear map."""
    basis: list[int] = []
    current_rank = 0
    while len(basis) < rows:
        value = rng.randrange(1, 1 << rows)
        new_rank = _rank(basis + [value])
        if new_rank > current_rank:
            basis.append(value)
            current_rank = new_rank
    return basis


def _linear_map(value: int, basis_images: list[int]) -> int:
    result = 0
    bit = 0
    while value:
        if value & 1:
            result ^= basis_images[bit]
        value >>= 1
        bit += 1
    return result


def _choose_shape(
    n: int,
    rows: int | None,
    weight: int | None,
    marker_vertices: int | None,
    marker_edges: int | None,
) -> tuple[int, int, int, int]:
    if isinstance(n, bool) or not isinstance(n, int) or n < 24:
        raise ValueError("n must be an integer at least 24")
    if marker_vertices is None:
        marker_vertices = max(6, min(16, n // 13))
    if marker_edges is None:
        marker_edges = marker_vertices + max(2, marker_vertices // 2)
    if rows is None:
        # Edge-marker columns add relations but no rank.  Cap the default row
        # count so make_instance(n) works even at the documented minimum n=24.
        rows = max(12, min(round(0.575 * n), n - marker_edges))
    if weight is None:
        weight = max(4, round(0.10 * n))
        if weight % 2:
            weight += 1

    values = (rows, weight, marker_vertices, marker_edges)
    if any(isinstance(x, bool) or not isinstance(x, int) for x in values):
        raise ValueError("rows, weight, marker_vertices, and marker_edges must be integers")
    if not (12 <= rows < n):
        raise ValueError("rows must satisfy 12 <= rows < n")
    if not (4 <= weight <= n):
        raise ValueError("weight must satisfy 4 <= weight <= n")
    if not (4 <= marker_vertices + 1 <= rows):
        raise ValueError("marker_vertices must leave room for an affine anchor")
    max_edges = marker_vertices * (marker_vertices - 1) // 2
    if not (marker_vertices - 1 <= marker_edges <= max_edges):
        raise ValueError("marker_edges must be enough to connect the marker graph")
    if 1 + marker_vertices + marker_edges >= n:
        raise ValueError("the marker gadget must use fewer than n columns")
    # Edge points lie in the span of the anchor and marker vertices, so only
    # the n-marker_edges remaining columns can contribute independent pivots.
    if rows > n - marker_edges:
        raise ValueError("rows cannot exceed n - marker_edges for this construction")
    return rows, weight, marker_vertices, marker_edges


def _random_marker_graph(vertices: int, edge_count: int, rng: random.Random) -> list[tuple[int, int]]:
    """A connected random graph; only its unlabeled structure enters the key."""
    edges: set[tuple[int, int]] = set()
    order = list(range(vertices))
    rng.shuffle(order)
    for pos in range(1, vertices):
        u = order[pos]
        v = order[rng.randrange(pos)]
        edges.add((min(u, v), max(u, v)))
    while len(edges) < edge_count:
        u, v = rng.sample(range(vertices), 2)
        edges.add((min(u, v), max(u, v)))
    return sorted(edges)


def make_instance(
    n: int,
    seed: int = 0,
    *,
    rows: int | None = None,
    weight: int | None = None,
    marker_vertices: int | None = None,
    marker_edges: int | None = None,
) -> dict:
    """Sample a support first, then build a binary syndrome around it.

    ``n`` is the number of available vectors.  With default parameters both
    the syndrome dimension and required weight grow linearly with ``n``.
    The returned ``answer`` uses 1-based indices.
    """
    rows, weight, marker_vertices, marker_edges = _choose_shape(
        n, rows, weight, marker_vertices, marker_edges
    )
    rng = random.Random(seed)

    # G: the witness is sampled before any problem data.
    answer = sorted(index + 1 for index in rng.sample(range(n), weight))

    # Work in a raw coordinate system.  The anchor/vertex/edge points encode a
    # random affine graph through zero-XOR quadruples
    # {anchor, vertex_u, vertex_v, edge_uv}.  The support is independent of it.
    anchor = 1
    vertices = [1 << (i + 1) for i in range(marker_vertices)]
    graph_edges = _random_marker_graph(marker_vertices, marker_edges, rng)
    edge_points = [anchor ^ vertices[u] ^ vertices[v] for u, v in graph_edges]
    raw = [anchor, *vertices, *edge_points]

    while True:
        used = set(raw)
        candidate = list(raw)
        while len(candidate) < n:
            value = rng.randrange(1, 1 << rows)
            if value not in used:
                candidate.append(value)
                used.add(value)
        if _rank(candidate) == rows:
            raw = candidate
            break

    # Dense random change of basis hides coordinate artefacts without changing
    # any linear relation.  A final permutation makes every displayed position
    # exchangeable with respect to planted membership.
    basis_images = _random_basis(rows, rng)
    columns = [_linear_map(value, basis_images) for value in raw]
    rng.shuffle(columns)

    target = 0
    for index in answer:
        target ^= columns[index - 1]

    return {
        "family": "exact_weight_binary_syndrome",
        "n": n,
        "rows": rows,
        "weight": weight,
        "columns": columns,
        "target": target,
        "answer": answer,
        "marker_vertices": marker_vertices,
        "marker_edges": marker_edges,
    }


def render(inst: dict) -> str:
    """Render a complete, self-contained exact-weight XOR problem."""
    n = inst["n"]
    rows = inst["rows"]
    weight = inst["weight"]
    lines = [
        "Exact-weight binary syndrome problem",
        "",
        "All vectors below belong to the binary vector space F_2^r. Addition in",
        "this space is coordinatewise XOR: 0+0=0, 0+1=1, and 1+1=0.",
        f"Here r={rows}. Each displayed bit string has exactly {rows} coordinates;",
        "the leftmost displayed bit is coordinate 1 and the rightmost is coordinate r.",
        "",
        f"Choose exactly h={weight} DISTINCT vectors from the n={n} indexed vectors",
        "so that their XOR is exactly the target. Each index may be used at most once.",
        "Indices are 1-based and inclusive (1 through n). Order does not matter.",
        "",
        f"target: {inst['target']:0{rows}b}",
        "vectors:",
    ]
    width = len(str(n))
    lines.extend(
        f"{index:>{width}}: {value:0{rows}b}"
        for index, value in enumerate(inst["columns"], 1)
    )
    example = ", ".join(str(i) for i in range(1, weight + 1))
    lines.extend(
        [
            "",
            "Give your final answer inside <answer></answer> tags, as exactly",
            f"{weight} comma-separated decimal indices. Repeats are forbidden; order is ignored.",
            f"Example of the required syntax (not a hint): <answer>{example}</answer>",
            "Output nothing else inside the tags.",
        ]
    )
    return "\n".join(lines)


def parse_answer(text: str) -> object | None:
    """Parse a comma-separated index list from answer tags; never raise."""
    if not isinstance(text, str):
        return None
    try:
        blocks = _ANSWER_RE.findall(text)
        for block in reversed(blocks):
            value = block.strip()
            if not value or not re.fullmatch(r"[+-]?\d+(?:\s*,\s*[+-]?\d+)*", value):
                continue
            return [int(piece.strip(), 10) for piece in value.split(",")]
    except (TypeError, ValueError, OverflowError):
        return None
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any valid support without consulting the planted witness."""
    if not isinstance(answer, list):
        return False, "answer must be a list of decimal indices"
    if not answer:
        return False, "answer is empty"
    if len(answer) != inst["weight"]:
        return False, f"wrong number of indices: expected {inst['weight']}, got {len(answer)}"
    if any(isinstance(index, bool) or not isinstance(index, int) for index in answer):
        return False, "every index must be an integer"
    if len(set(answer)) != len(answer):
        return False, "indices must be distinct; a duplicate was supplied"
    if any(index < 1 or index > inst["n"] for index in answer):
        return False, f"index out of range; valid indices are 1 through {inst['n']}"
    total = 0
    for index in answer:
        total ^= inst["columns"][index - 1]
    if total != inst["target"]:
        return False, "selected vectors XOR to the wrong target"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Uniformly sample the exact-size, distinct-index space a solver searches."""
    return sorted(rng.sample(range(1, inst["n"] + 1), inst["weight"]))


def search_space(inst: dict) -> int | None:
    """Number of exact-size distinct supports (already structure-aware)."""
    return math.comb(inst["n"], inst["weight"])


def enumerate_all(inst: dict) -> int | None:
    """Count every valid support when the exact search space is safely capped."""
    space = search_space(inst)
    if space is None or space > _ENUMERATION_CAP:
        return None
    count = 0
    columns = inst["columns"]
    target = inst["target"]
    for support in combinations(range(inst["n"]), inst["weight"]):
        total = 0
        for index in support:
            total ^= columns[index]
        count += total == target
    return count


def _four_circuits(columns: list[int]) -> list[tuple[int, int, int, int]]:
    """All four-element column subsets with XOR zero, in canonical index order."""
    buckets: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for left in range(len(columns)):
        for right in range(left + 1, len(columns)):
            buckets[columns[left] ^ columns[right]].append((left, right))
    circuits: set[tuple[int, int, int, int]] = set()
    for pairs in buckets.values():
        if len(pairs) < 2:
            continue
        for first_pos in range(len(pairs)):
            a, b = pairs[first_pos]
            for second_pos in range(first_pos + 1, len(pairs)):
                c, d = pairs[second_pos]
                if len({a, b, c, d}) == 4:
                    circuits.add(tuple(sorted((a, b, c, d))))
    return sorted(circuits)


def _hypergraph_signature(vertex_count: int, edges: list[tuple[int, ...]]) -> dict:
    """Permutation-invariant colour-refinement signature of a uniform hypergraph."""
    incident: list[list[int]] = [[] for _ in range(vertex_count)]
    for edge_index, edge in enumerate(edges):
        for vertex in edge:
            incident[vertex].append(edge_index)

    vertex_colours = [0] * vertex_count
    edge_colours = [0] * len(edges)
    history: list[dict] = []
    for _ in range(12):
        edge_signatures = [tuple(sorted(vertex_colours[v] for v in edge)) for edge in edges]
        edge_palette = {sig: pos for pos, sig in enumerate(sorted(set(edge_signatures)))}
        new_edge_colours = [edge_palette[sig] for sig in edge_signatures]

        vertex_signatures = [
            (vertex_colours[v], tuple(sorted(new_edge_colours[e] for e in incident[v])))
            for v in range(vertex_count)
        ]
        vertex_palette = {sig: pos for pos, sig in enumerate(sorted(set(vertex_signatures)))}
        new_vertex_colours = [vertex_palette[sig] for sig in vertex_signatures]
        history.append(
            {
                "v": sorted(Counter(new_vertex_colours).items()),
                "e": sorted(Counter(new_edge_colours).items()),
            }
        )
        if new_vertex_colours == vertex_colours and new_edge_colours == edge_colours:
            break
        vertex_colours = new_vertex_colours
        edge_colours = new_edge_colours

    # The incidence pattern between final colour classes adds strength while
    # remaining independent of displayed vertex labels.
    edge_patterns = Counter(tuple(sorted(vertex_colours[v] for v in edge)) for edge in edges)
    return {
        "edge_count": len(edges),
        "degrees": sorted(len(items) for items in incident),
        "history": history,
        "edge_patterns": sorted((list(pattern), count) for pattern, count in edge_patterns.items()),
    }


def _target_counts(inst: dict) -> dict[str, int]:
    """Cheap target invariants whose subset parity matches h under translation."""
    columns = inst["columns"]
    target = inst["target"]
    parity = inst["weight"] & 1
    counts: dict[str, int] = {}
    if parity:
        counts["one"] = sum(value == target for value in columns)
        triple = 0
        # Shipping weights are even, but keep odd custom instances bounded.
        if len(columns) <= 96:
            for a, b, c in combinations(columns, 3):
                triple += (a ^ b ^ c) == target
        else:
            triple = -1
        counts["three"] = triple
    else:
        pair_buckets: dict[int, list[tuple[int, int]]] = defaultdict(list)
        pair_count = 0
        for left in range(len(columns)):
            for right in range(left + 1, len(columns)):
                value = columns[left] ^ columns[right]
                pair_count += value == target
                pair_buckets[value].append((left, right))
        four_sets: set[tuple[int, int, int, int]] = set()
        for value, first_pairs in pair_buckets.items():
            other = value ^ target
            if other not in pair_buckets or value > other:
                continue
            second_pairs = pair_buckets[other]
            for a, b in first_pairs:
                for c, d in second_pairs:
                    if len({a, b, c, d}) == 4:
                        four_sets.add(tuple(sorted((a, b, c, d))))
        counts["two"] = pair_count
        counts["four"] = len(four_sets)
    return counts


def canonical_key(inst: dict) -> str:
    """Strong affine/GL/column-permutation invariant, not a seed or render hash."""
    circuits = _four_circuits(inst["columns"])
    payload = {
        "family": "exact_weight_binary_syndrome",
        "n": inst["n"],
        "rows": inst["rows"],
        "weight": inst["weight"],
        "affine_rank": _affine_rank(inst["columns"]),
        "four_xor_hypergraph": _hypergraph_signature(inst["n"], circuits),
        "target_counts": _target_counts(inst),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "affine4:" + hashlib.sha256(encoded).hexdigest()


def escalate(params: dict) -> dict | None:
    """Raise all exponential-cost axes while preserving the planted regime."""
    try:
        n = int(params["n"])
        rows = int(params.get("rows", round(0.575 * n)))
        weight = int(params.get("weight", round(0.10 * n)))
        marker_vertices = int(params.get("marker_vertices", max(6, n // 13)))
        marker_edges = int(params.get("marker_edges", marker_vertices + marker_vertices // 2))
    except (KeyError, TypeError, ValueError):
        return None
    new_n = n + max(40, n // 4)
    new_rows = max(rows + 1, round(rows * new_n / n))
    new_weight = max(weight + 2, round(weight * new_n / n))
    if new_weight % 2:
        new_weight += 1
    new_vertices = min(new_rows - 2, marker_vertices + 2)
    new_edges = min(
        new_vertices * (new_vertices - 1) // 2,
        marker_edges + 4,
    )
    return {
        "n": new_n,
        "rows": new_rows,
        "weight": new_weight,
        "marker_vertices": new_vertices,
        "marker_edges": new_edges,
    }


# ------------------------------ self-test helpers -------------------------


def _outlier_candidates(inst: dict) -> dict[str, list[int]]:
    h = inst["weight"]
    columns = inst["columns"]
    target = inst["target"]
    circuits = _four_circuits(columns)
    degrees = [0] * inst["n"]
    for circuit in circuits:
        for vertex in circuit:
            degrees[vertex] += 1
    rules = {
        "position_first": list(range(h)),
        "lowest_column_weight": sorted(range(inst["n"]), key=lambda i: (_popcount(columns[i]), i))[:h],
        "closest_to_target": sorted(
            range(inst["n"]), key=lambda i: (_popcount(columns[i] ^ target), i)
        )[:h],
        "highest_affine_degree": sorted(range(inst["n"]), key=lambda i: (-degrees[i], i))[:h],
    }
    return {name: sorted(i + 1 for i in support) for name, support in rules.items()}


def _greedy_attack(inst: dict) -> list[int]:
    chosen: list[int] = []
    unused = set(range(inst["n"]))
    residual = inst["target"]
    for _ in range(inst["weight"]):
        pick = min(unused, key=lambda i: (_popcount(residual ^ inst["columns"][i]), i))
        chosen.append(pick)
        unused.remove(pick)
        residual ^= inst["columns"][pick]
    return sorted(i + 1 for i in chosen)


def _random_restart_attack(inst: dict, rng: random.Random, restarts: int = 20) -> list[int]:
    """Swap local search minimizing residual Hamming weight; returns its best support."""
    columns = inst["columns"]
    best_support: list[int] | None = None
    best_score = inst["rows"] + 1
    all_indices = set(range(inst["n"]))
    for _ in range(restarts):
        support = set(rng.sample(range(inst["n"]), inst["weight"]))
        residual = inst["target"]
        for index in support:
            residual ^= columns[index]
        score = _popcount(residual)
        for _step in range(min(24, inst["weight"] + 4)):
            best_swap: tuple[int, int, int, int] | None = None
            outside = all_indices - support
            for remove in sorted(support):
                base = residual ^ columns[remove]
                for add in sorted(outside):
                    new_residual = base ^ columns[add]
                    new_score = _popcount(new_residual)
                    if new_score < score and (
                        best_swap is None or (new_score, remove, add) < best_swap[:3]
                    ):
                        best_swap = (new_score, remove, add, new_residual)
            if best_swap is None:
                break
            score, remove, add, residual = best_swap
            support.remove(remove)
            support.add(add)
            if score == 0:
                return sorted(i + 1 for i in support)
        if score < best_score:
            best_score = score
            best_support = sorted(support)
    assert best_support is not None
    return [i + 1 for i in best_support]


def _transform_columns(inst: dict, basis: list[int] | None = None, translation: int = 0) -> dict:
    transformed = dict(inst)
    if basis is None:
        columns = list(inst["columns"])
        target = inst["target"]
    else:
        columns = [_linear_map(value, basis) for value in inst["columns"]]
        target = _linear_map(inst["target"], basis)
    if translation:
        columns = [value ^ translation for value in columns]
        if inst["weight"] & 1:
            target ^= translation
    transformed["columns"] = columns
    transformed["target"] = target
    transformed["answer"] = list(inst["answer"])
    return transformed


def _permute_columns(inst: dict, order: list[int]) -> dict:
    transformed = dict(inst)
    transformed["columns"] = [inst["columns"][old] for old in order]
    inverse = {old: new for new, old in enumerate(order)}
    transformed["answer"] = sorted(inverse[index - 1] + 1 for index in inst["answer"])
    return transformed


def _coordinate_permutation_basis(rows: int, rng: random.Random) -> list[int]:
    order = list(range(rows))
    rng.shuffle(order)
    return [1 << order[i] for i in range(rows)]


def selftest() -> dict:
    """Run gates G1--G8 and return their measured, JSON-serializable report."""
    report: dict[str, object] = {
        "family": "exact_weight_binary_syndrome",
        "shipping_difficulty": SHIPPING_DIFFICULTY,
    }

    # G1: every preset across several seeds.
    g1_cases = []
    g1_ok = True
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 991):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            g1_cases.append({"preset": preset, "seed": seed, "ok": ok, "reason": reason})
            g1_ok &= ok
    report["G1_planted_verifies"] = {"pass": g1_ok, "cases": g1_cases}

    ship_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    base = make_instance(seed=424242, **ship_params)

    # G2: each requested corruption has its own diagnostic category.
    planted = list(base["answer"])
    corruptions: dict[str, list[int]] = {
        "drop_one": planted[:-1],
        "duplicate": planted[:-1] + [planted[-2]],
        "empty": [],
        "out_of_range": planted[:-1] + [base["n"] + 1],
    }
    replacement = next(i for i in range(1, base["n"] + 1) if i not in planted)
    corruptions["replace_one"] = sorted(planted[:-1] + [replacement])
    g2_results = {}
    reasons = []
    for name, candidate in corruptions.items():
        ok, reason = verify(base, candidate)
        g2_results[name] = {"rejected": not ok, "reason": reason}
        reasons.append(reason)
    g2_ok = all(item["rejected"] for item in g2_results.values()) and len(set(reasons)) == len(reasons)
    report["G2_rejects_corruption"] = {
        "pass": g2_ok,
        "distinct_reasons": len(set(reasons)),
        "tests": g2_results,
    }

    # G3: realistic prose/fence wrapper and malformed garbage.
    encoded_answer = ", ".join(map(str, planted))
    response = (
        "I computed the syndrome by XORing the selected rows.\n\n"
        "```text\n<answer>  " + encoded_answer + "  </answer>\n```\n"
        "The indices above are 1-based."
    )
    parsed = parse_answer(response)
    malformed = parse_answer("```<answer>1, two, 3</answer>```")
    g3_ok = parsed == planted and malformed is None
    report["G3_round_trip"] = {
        "pass": g3_ok,
        "parsed_equals_answer": parsed == planted,
        "garbage_returns_none": malformed is None,
    }

    # G4: uniform exact-size supports, not arbitrary bit vectors or noisy lists.
    guess_rng = random.Random(7331)
    trials = 250_000
    hits = 0
    for _ in range(trials):
        candidate = random_candidate(base, guess_rng)
        hits += verify(base, candidate)[0]
    probability = hits / trials
    report["G4_guess_resistance"] = {
        "pass": probability < 1e-6,
        "hits": hits,
        "total": trials,
        "measured_probability": probability,
        "prior": "uniform over exactly h distinct 1-based indices",
        "structure_aware_space": search_space(base),
    }

    # G5: a deliberately small instance for exact counting.
    small = make_instance(
        n=40,
        rows=32,
        weight=4,
        marker_vertices=6,
        marker_edges=7,
        seed=9127,
    )
    solution_count = enumerate_all(small)
    small_space = search_space(small)
    fraction = None if solution_count is None else solution_count / small_space
    g5_ok = solution_count is not None and solution_count >= 1 and fraction is not None and fraction < 1e-3
    report["G5_sparse"] = {
        "pass": g5_ok,
        "n": small["n"],
        "weight": small["weight"],
        "solutions": solution_count,
        "search_space": small_space,
        "solution_fraction": fraction,
    }

    # G6: attacks know the statement and exploit generator-visible statistics.
    attack_names = [
        "position_first",
        "lowest_column_weight",
        "closest_to_target",
        "highest_affine_degree",
        "greedy_residual",
        "random_restart_swap",
    ]
    attack_successes = {name: 0 for name in attack_names}
    attack_seeds = list(range(800, 808))
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **ship_params)
        for name, candidate in _outlier_candidates(inst).items():
            attack_successes[name] += verify(inst, candidate)[0]
        attack_successes["greedy_residual"] += verify(inst, _greedy_attack(inst))[0]
        attack_successes["random_restart_swap"] += verify(
            inst, _random_restart_attack(inst, random.Random(seed ^ 0x5EED))
        )[0]
    attack_results = {
        name: {"successes": count, "trials": len(attack_seeds), "fails_all": count == 0}
        for name, count in attack_successes.items()
    }
    report["G6_adversary_panel"] = {
        "pass": all(item["fails_all"] for item in attack_results.values()),
        "seeds": attack_seeds,
        "attacks": attack_results,
    }

    # G7: fixed rates make all recognized exponential axes grow with n.
    doubled_params = dict(ship_params)
    doubled_params["n"] *= 2
    doubled_params["rows"] *= 2
    doubled_params["weight"] *= 2
    doubled_params["marker_vertices"] += 2
    doubled_params["marker_edges"] += 4
    doubled = make_instance(seed=1234567, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    base_bits = search_space(base).bit_length() - 1
    doubled_bits = search_space(doubled).bit_length() - 1
    g7_ok = (
        doubled_ok
        and doubled["n"] > base["n"]
        and doubled["rows"] > base["rows"]
        and doubled["weight"] > base["weight"]
        and doubled_bits > base_bits
    )
    report["G7_scales"] = {
        "pass": g7_ok,
        "base": {
            "n": base["n"],
            "rows": base["rows"],
            "weight": base["weight"],
            "log2_search_space_floor": base_bits,
        },
        "doubled": {
            "n": doubled["n"],
            "rows": doubled["rows"],
            "weight": doubled["weight"],
            "log2_search_space_floor": doubled_bits,
            "planted_ok": doubled_ok,
            "reason": doubled_reason,
        },
    }

    # G8: 20 seeds, five real relabellings each, plus unrelated distinctness.
    invariant_checks = 0
    witness_checks = 0
    invariant_failures = []
    keys = []
    for seed in range(20_000, 20_020):
        inst = make_instance(seed=seed, **ship_params)
        key = canonical_key(inst)
        keys.append(key)
        trng = random.Random(seed ^ 0xC4A0)

        order = list(range(inst["n"]))
        trng.shuffle(order)
        permuted = _permute_columns(inst, order)

        coordinate = _transform_columns(inst, _coordinate_permutation_basis(inst["rows"], trng))
        general_basis = _random_basis(inst["rows"], trng)
        linear = _transform_columns(inst, general_basis)
        translation = trng.randrange(1, 1 << inst["rows"])
        affine = _transform_columns(inst, None, translation)

        composed = _transform_columns(inst, general_basis, translation)
        composed_order = list(range(inst["n"]))
        trng.shuffle(composed_order)
        composed = _permute_columns(composed, composed_order)

        for name, transformed in (
            ("column_permutation", permuted),
            ("coordinate_permutation", coordinate),
            ("general_change_of_basis", linear),
            ("global_translation", affine),
            ("composed", composed),
        ):
            invariant_checks += 1
            transformed_key = canonical_key(transformed)
            if transformed_key != key:
                invariant_failures.append({"seed": seed, "transformation": name})
            witness_checks += 1
            if not verify(transformed, transformed["answer"])[0]:
                invariant_failures.append({"seed": seed, "transformation": name, "witness": "failed"})

    distinct_keys = len(set(keys))
    g8_ok = not invariant_failures and distinct_keys == len(keys)
    report["G8_canonical_key"] = {
        "pass": g8_ok,
        "invariance_checks": invariant_checks,
        "witness_preservation_checks": witness_checks,
        "unrelated_instances": len(keys),
        "distinct_keys": distinct_keys,
        "failures": invariant_failures,
        "transformations": [
            "column permutation",
            "coordinate permutation",
            "general GL(r,2) change of basis",
            "global translation with parity-correct target",
            "GL + translation + column permutation",
        ],
        "key_basis": "colour-refined zero-XOR 4-hypergraph plus target counts",
        "complete_isomorphism_test": False,
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(isinstance(gate, dict) and gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
