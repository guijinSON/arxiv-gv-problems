"""Verified generator for a Path Contraction witness family from arXiv:2403.06290.

The family uses the split-graph construction in Section 5.2, Theorem 4.  A pair
of orthogonal Boolean vectors determines the four witness bags in the proof.
Generation is inverse: endpoint pairs are chosen first; every other vector is
then sampled from the same Hamming layer subject to having no extra orthogonal
pair.  A planted half-swap orbit structure gives the intended Track-B shortcut.
"""

from __future__ import annotations

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
    "certificate_form": "integer_tuple",
    "native_objects": [
        "two constant-weight Boolean-vector families",
        "chordal split graph specified by its clique-incidence table",
        "endpoint pairs for four-bag path witness structures",
    ],
    "verification_operations": [
        "exact bit-set intersection",
        "induced-subgraph connectivity by breadth-first search",
        "exact quotient adjacency comparison with P4",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 5.2, Theorem 4: the paper's central reduction from Orthogonal "
        "Vectors to Path Contraction on chordal split graphs"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "symmetry",
    "intuition_description": (
        "Almost all rows on each side occur in two-cycles of the coordinate "
        "half-swap involution; its unmatched rows contain the endpoints, while "
        "a solver missing that symmetry scans every cross-pair."
    ),
    "hardness_basis": (
        "Track B: exhaustive Orthogonal Vectors scanning takes O(n^2 d) time "
        "and at shipping n=130,d=72 performs exactly 1216800 Boolean coordinate "
        "products (about 0.08 seconds in selftest_report.json); recognizing the half-swap "
        "two-cycles reduces this to 2n+t^2=276 exact word operations."
    ),
    "max_answer_tokens": 12,
}

NATIVE = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"]
        + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

DIFFICULTY = {
    "demo": {"n": 6, "d": 16, "weight": 5, "target_count": 2},
    "easy": {"n": 100, "d": 64, "weight": 20, "target_count": 4},
    "medium": {"n": 130, "d": 64, "weight": 20, "target_count": 4},
    "hard": {"n": 130, "d": 72, "weight": 20, "target_count": 4},
}

SHIPPING_DIFFICULTY = "hard"

CERTIFICATE_LANGUAGE = {
    "description": (
        "A lexicographically sorted JSON list of exactly target_count distinct "
        "0-based [X-index,Y-index] pairs, each index in 0..n-1"
    ),
    "bounds": {"pairs": 4, "indices_per_pair": 2, "max_index_exclusive": 130},
}

STRUCTURAL_HINT = (
    "The two coordinate halves define an involution under which each displayed side is almost a union of two-cycles."
)
PLACEBO_HINT = (
    "The two displayed vertex families require consistent bookkeeping when comparing their coordinate neighborhoods."
)

# Filled from the three isolated harden.py runs.  They remain literal so importing
# the module never reads transcripts or depends on the current working directory.
_G9_ARMS = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 1, "attempts": 3},
    "placebo": {"solved": 2, "attempts": 3},
}
_G9_HINTED_VERDICT = "too_easy"

NOTES = """\
Definition: Section 2 defines an H-witness structure as a partition into nonempty
connected bags whose bag-adjacency graph is exactly H.  Section 5.2, Theorem 4
fixes this generator: its split graph has independent sets X,Y and clique
Z={z_X,z_1,...,z_d,z_Y}; an orthogonal x_i,y_j gives the four bags displayed in
the forward direction of the proof.

Easy cases avoided: the Introduction says P3 is polynomial-time solvable;
Theorem 3 makes planar Path Contraction polynomial-time; chordal Path Contraction
has the known O(nm) algorithm quoted immediately before Theorem 4; and Theorem 1
gives the general O*(2^k) FPT algorithm, so small k is not used.  This is therefore
Track B, not a distributional Track A claim.

Certificate production: the general mechanical route is the O(n^2 d) Orthogonal
Vectors scan implicit in Theorem 4.  The generated distribution also has a hidden
half-swap involution: all non-endpoint rows occur with their swapped-half mate.
Finding the unmatched rows and testing only their cross-product costs 2n+t^2
word operations.  The generator does not run either route to obtain its answer:
it samples the endpoint vectors first and carries their indices through shuffles.

Attack hardening: all X and Y vertices have identical degree, planted positions
are independently shuffled, and every row is sampled from the same constant-
weight layer.  The successful construction-aware half-swap attack is disclosed
beside the Track-B reference scan.  The failing panel measures degree/outlier,
greedy minimum-intersection, random restart, and visual row-alignment attacks.
"""


def _sample_weight_mask(rng: random.Random, d: int, weight: int) -> int:
    mask = 0
    for bit in rng.sample(range(d), weight):
        mask |= 1 << bit
    return mask


def _draw_distinct_masks(
    rng: random.Random,
    count: int,
    d: int,
    weight: int,
    forbidden: set[int] | None = None,
) -> list[int]:
    """Uniform rejection sampling from one Hamming layer, never solution search."""
    blocked = set() if forbidden is None else set(forbidden)
    if math.comb(d, weight) - len(blocked) < count:
        raise ValueError("not enough constant-weight vectors for these parameters")
    out: list[int] = []
    used = set(blocked)
    while len(out) < count:
        value = _sample_weight_mask(rng, d, weight)
        if value not in used:
            used.add(value)
            out.append(value)
    return out


def _half_swap(mask: int, d: int) -> int:
    """Swap the low and high d/2 coordinate blocks (d is even)."""
    half = d // 2
    low = mask & ((1 << half) - 1)
    return (low << half) | (mask >> half)


def make_instance(n: int, seed: int = 0, **params) -> dict:
    """Inverse-generate a split graph and known P4 endpoint certificates."""
    d = int(params.get("d", 64))
    target_count = int(params.get("target_count", 4))
    weight = int(params.get("weight", max(2, d // 3)))
    n = int(n)
    if n < 3 or target_count < 1 or target_count >= n or (n - target_count) % 2:
        raise ValueError("require n >= 3, 1 <= target_count < n, and n-target_count even")
    if d < 8 or d % 2 or not (1 <= weight <= d // 2):
        raise ValueError("require even d >= 8 and 1 <= weight <= d/2")
    universe = math.comb(d, weight)
    if universe < 8 * n:
        raise ValueError("Hamming layer is too small for unbiased decoys")

    rng = random.Random(seed)
    # Sample the target X rows first.  Non-target rows are installed in tau
    # two-cycles.  Every individual row is marginally from the same Hamming layer.
    x_tagged: list[tuple[int, int | None]] = []
    x_used: set[int] = set()
    for label in range(target_count):
        while True:
            x = _sample_weight_mask(rng, d, weight)
            tx = _half_swap(x, d)
            if x != tx and x not in x_used and tx not in x_used:
                break
        x_used.add(x)
        x_tagged.append((x, label))
    for _ in range((n - target_count) // 2):
        while True:
            x = _sample_weight_mask(rng, d, weight)
            tx = _half_swap(x, d)
            if x != tx and x not in x_used and tx not in x_used:
                break
        x_used.update((x, tx))
        x_tagged.extend(((x, None), (tx, None)))
    rng.shuffle(x_tagged)
    x_masks = [x for x, _ in x_tagged]
    x_index_by_label = {label: i for i, (_, label) in enumerate(x_tagged) if label is not None}

    # Each target Y is drawn from the complement of its designated target X,
    # and is required to meet every other X.  All remaining Y rows arrive in
    # tau-pairs and meet every X.  These local rejection tests prevent extra
    # solutions; they never search for the already-chosen endpoint certificate.
    y_tagged: list[tuple[int, int | None]] = []
    y_used: set[int] = set()
    for label in range(target_count):
        xi = x_index_by_label[label]
        available = [c for c in range(d) if not (x_masks[xi] & (1 << c))]
        for _attempt in range(100_000):
            y = sum(1 << c for c in rng.sample(available, weight))
            ty = _half_swap(y, d)
            if y == ty or y in y_used or ty in y_used:
                continue
            if any((x & y) == 0 for i, x in enumerate(x_masks) if i != xi):
                continue
            break
        else:
            raise RuntimeError("failed to sample a planted Y row")
        y_used.add(y)
        y_tagged.append((y, label))
    for _ in range((n - target_count) // 2):
        for _attempt in range(100_000):
            y = _sample_weight_mask(rng, d, weight)
            ty = _half_swap(y, d)
            if y == ty or y in y_used or ty in y_used:
                continue
            if any((x & y) == 0 or (x & ty) == 0 for x in x_masks):
                continue
            break
        else:
            raise RuntimeError("failed to sample a decoy Y orbit")
        y_used.update((y, ty))
        y_tagged.extend(((y, None), (ty, None)))
    rng.shuffle(y_tagged)
    y_masks = [y for y, _ in y_tagged]
    y_index_by_label = {label: j for j, (_, label) in enumerate(y_tagged) if label is not None}
    answer = sorted(
        [[x_index_by_label[label], y_index_by_label[label]] for label in range(target_count)]
    )

    return {
        "n": n,
        "d": d,
        "weight": weight,
        "target_count": target_count,
        "k": 2 * n + d - 2,
        "X": x_masks,
        "Y": y_masks,
        "answer": answer,
    }


def _mask_text(mask: int, d: int) -> str:
    return f"0x{mask:0{(d + 3) // 4}x}"


def render(inst: dict) -> str:
    n, d, t = inst["n"], inst["d"], inst["target_count"]
    x_lines = "\n".join(f"  x{i}: {_mask_text(m, d)}" for i, m in enumerate(inst["X"]))
    y_lines = "\n".join(f"  y{j}: {_mask_text(m, d)}" for j, m in enumerate(inst["Y"]))
    example = json.dumps([[i, i] for i in range(t)], separators=(",", ":"))
    statement = f"""Find endpoint certificates for path contractions in a chordal split graph.

The graph G is defined as follows.  X={{x0,...,x{n-1}}} and
Y={{y0,...,y{n-1}}} are independent sets.  Z={{zX,z0,...,z{d-1},zY}} is a
clique.  Each displayed row is a fixed-width hexadecimal integer.  Bit c means
the coefficient of 2^c (the rightmost hexadecimal digit contains bits 0..3).
Vertex xi is adjacent to zX and to coordinate vertex zc exactly when bit c of
its row is 1.  Vertex yj is adjacent to zY and to zc exactly when bit c of its
row is 1.  There are no other edges.  Thus G is a connected chordal split graph.

For a proposed pair [i,j], define Z1 as the neighbors of xi in Z, Z2 as the
neighbors of yj in Z, and Z3=Z\\(Z1 union Z2).  The pair is valid exactly when
the following four nonempty bags form a path-witness structure in the listed
order:
  W1={{xi}}
  W2=Z1 union Z3 union (X\\{{xi}})
  W3=Z2 union (Y\\{{yj}})
  W4={{yj}}
A path-witness structure means that every bag induces a connected subgraph,
the bags partition all vertices, and two distinct bags have at least one edge
between them exactly when they are consecutive in the displayed order.  Such a
structure contracts G to the four-vertex path P4 using exactly k={inst['k']}
edge contractions.

Return exactly {t} distinct valid pairs.  Indices are 0-based and lie in
0..{n-1}.  Order within a pair is always [X-index,Y-index].  Sort the list of
pairs lexicographically; repeats are forbidden.

X incidence masks:
{x_lines}

Y incidence masks:
{y_lines}

Give your final answer inside <answer></answer> tags as a JSON list of {t}
integer pairs sorted lexicographically.
Example of the required syntax only: <answer>{example}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Parse tagged JSON, with a conservative fenced/embedded JSON fallback."""
    if not isinstance(text, str):
        return None
    bodies = re.findall(r"<answer\b[^>]*>(.*?)</answer>", text, flags=re.I | re.S)
    candidates = list(reversed(bodies))
    if not candidates:
        candidates = [text]
    decoder = json.JSONDecoder()
    for body in candidates:
        cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", body.strip(), flags=re.I)
        try:
            return json.loads(cleaned)
        except (TypeError, ValueError):
            pass
        for match in re.finditer(r"\[", cleaned):
            try:
                value, _ = decoder.raw_decode(cleaned[match.start() :])
                return value
            except ValueError:
                continue
    return None


def _graph_adjacency(inst: dict) -> list[set[int]]:
    n, d = inst["n"], inst["d"]
    size = 2 * n + d + 2
    z_x = 2 * n
    z_first = z_x + 1
    z_y = z_first + d
    z_vertices = list(range(z_x, z_y + 1))
    adj = [set() for _ in range(size)]

    def add(a: int, b: int) -> None:
        adj[a].add(b)
        adj[b].add(a)

    for a_pos, a in enumerate(z_vertices):
        for b in z_vertices[a_pos + 1 :]:
            add(a, b)
    for i, mask in enumerate(inst["X"]):
        add(i, z_x)
        for c in range(d):
            if mask & (1 << c):
                add(i, z_first + c)
    for j, mask in enumerate(inst["Y"]):
        vertex = n + j
        add(vertex, z_y)
        for c in range(d):
            if mask & (1 << c):
                add(vertex, z_first + c)
    return adj


def _bags_for_pair(inst: dict, i: int, j: int) -> list[set[int]]:
    n, d = inst["n"], inst["d"]
    z_x = 2 * n
    z_first = z_x + 1
    z_y = z_first + d
    z_all = set(range(z_x, z_y + 1))
    z1 = {z_x} | {
        z_first + c for c in range(d) if inst["X"][i] & (1 << c)
    }
    z2 = {z_y} | {
        z_first + c for c in range(d) if inst["Y"][j] & (1 << c)
    }
    z3 = z_all - (z1 | z2)
    return [
        {i},
        z1 | z3 | (set(range(n)) - {i}),
        z2 | (set(range(n, 2 * n)) - {n + j}),
        {n + j},
    ]


def _connected(vertices: set[int], adj: list[set[int]]) -> bool:
    if not vertices:
        return False
    start = next(iter(vertices))
    seen = {start}
    stack = [start]
    while stack:
        v = stack.pop()
        for u in adj[v]:
            if u in vertices and u not in seen:
                seen.add(u)
                stack.append(u)
    return seen == vertices


def _is_p4_witness_pair(
    inst: dict, i: int, j: int, adj: list[set[int]] | None = None
) -> bool:
    if inst["X"][i] & inst["Y"][j]:
        return False
    if adj is None:
        adj = _graph_adjacency(inst)
    bags = _bags_for_pair(inst, i, j)
    universe = set(range(len(adj)))
    if any(not bag for bag in bags):
        return False
    if set().union(*bags) != universe or sum(map(len, bags)) != len(universe):
        return False
    if any(not _connected(bag, adj) for bag in bags):
        return False
    for a in range(4):
        for b in range(a + 1, 4):
            adjacent = any(adj[v] & bags[b] for v in bags[a])
            if adjacent != (b == a + 1):
                return False
    return True


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Accept every sorted set of the required number of valid endpoint pairs."""
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    t, n = inst["target_count"], inst["n"]
    if len(answer) != t:
        return False, f"expected exactly {t} pairs"
    pairs: list[tuple[int, int]] = []
    for pos, pair in enumerate(answer):
        if not isinstance(pair, list) or len(pair) != 2:
            return False, f"entry {pos} is not a two-integer pair"
        i, j = pair
        if isinstance(i, bool) or isinstance(j, bool) or not isinstance(i, int) or not isinstance(j, int):
            return False, f"entry {pos} contains a non-integer index"
        if not (0 <= i < n and 0 <= j < n):
            return False, f"entry {pos} has an index out of range"
        pairs.append((i, j))
    if len(set(pairs)) != len(pairs):
        return False, "pairs must be distinct"
    if pairs != sorted(pairs):
        return False, "pairs must be lexicographically sorted"

    graph = None
    for i, j in pairs:
        if inst["X"][i] & inst["Y"][j]:
            return False, f"pair [{i},{j}] has intersecting coordinate neighborhoods"
        if graph is None:
            graph = _graph_adjacency(inst)
            if len(graph) - 4 > inst["k"]:
                return False, "the four-bag witness exceeds the contraction budget"
        if not _is_p4_witness_pair(inst, i, j, graph):
            return False, f"pair [{i},{j}] does not induce the required P4 quotient"
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly from the stated language of sorted distinct pairs."""
    n, t = inst["n"], inst["target_count"]
    chosen = sorted(rng.sample(range(n * n), t))
    return [[value // n, value % n] for value in chosen]


def search_space(inst: dict) -> int:
    return math.comb(inst["n"] * inst["n"], inst["target_count"])


def enumerate_all(inst: dict) -> int | None:
    """Brute-force tiny presets only; never let diagnostic enumeration hang."""
    space = search_space(inst)
    if space > 200_000:
        return None
    n, t = inst["n"], inst["target_count"]
    total = 0
    for values in itertools.combinations(range(n * n), t):
        candidate = [[value // n, value % n] for value in values]
        if verify(inst, candidate)[0]:
            total += 1
    return total


def _wl_invariant(inst: dict) -> object:
    """A graph-isomorphism invariant (not claimed to be a complete canonical form)."""
    adj = _graph_adjacency(inst)
    colors = [0] * len(adj)
    signatures: list[tuple] = []
    for _ in range(len(adj)):
        signatures = [(colors[v], tuple(sorted(colors[u] for u in adj[v]))) for v in range(len(adj))]
        palette = {sig: c for c, sig in enumerate(sorted(set(signatures)))}
        new_colors = [palette[sig] for sig in signatures]
        if new_colors == colors:
            break
        colors = new_colors
    class_sizes = [colors.count(c) for c in range(max(colors) + 1)]
    quotient_rows = []
    for c in range(max(colors) + 1):
        v = colors.index(c)
        counts = [0] * (max(colors) + 1)
        for u in adj[v]:
            counts[colors[u]] += 1
        quotient_rows.append([class_sizes[c], counts])
    # Pairwise common-neighbor counts strengthen the invariant while remaining
    # unchanged by every vertex relabelling.
    adj_bits = [sum(1 << u for u in neighbors) for neighbors in adj]
    common = sorted(
        (adj_bits[a] & adj_bits[b]).bit_count()
        for a in range(len(adj))
        for b in range(a + 1, len(adj))
    )
    return [sorted(len(ns) for ns in adj), quotient_rows, common]


def canonical_key(inst: dict) -> str:
    raw = json.dumps(
        [inst["target_count"], _wl_invariant(inst)],
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """Increase coordinate noise at fixed n, witness count, and answer length."""
    out = {k: v for k, v in params.items() if k != "_preset"}
    d = int(out.get("d", 64))
    out["d"] = d + 8
    return out


def _reference_pairs(inst: dict) -> tuple[list[list[int]], int]:
    """Domain-standard O(n^2 d) scan, intentionally not the planted shortcut."""
    out = []
    coordinate_products = 0
    d = inst["d"]
    for i, x in enumerate(inst["X"]):
        for j, y in enumerate(inst["Y"]):
            dot = 0
            for c in range(d):
                coordinate_products += 1
                dot += ((x >> c) & 1) * ((y >> c) & 1)
            if dot == 0:
                out.append([i, j])
    return sorted(out), coordinate_products


def _compact_pairs(inst: dict) -> tuple[list[list[int]], int]:
    """Construction-aware half-swap route, independent of inst['answer']."""
    xs = set(inst["X"])
    ys = set(inst["Y"])
    unmatched_x = [i for i, x in enumerate(inst["X"]) if _half_swap(x, inst["d"]) not in xs]
    unmatched_y = [j for j, y in enumerate(inst["Y"]) if _half_swap(y, inst["d"]) not in ys]
    pairs = sorted(
        [i, j]
        for i in unmatched_x
        for j in unmatched_y
        if (inst["X"][i] & inst["Y"][j]) == 0
    )
    operations = 2 * inst["n"] + len(unmatched_x) * len(unmatched_y)
    return pairs, operations


def _attack_candidates(inst: dict, rng: random.Random) -> dict[str, list[list[int]] | None]:
    n, t = inst["n"], inst["target_count"]
    # Per-element degree is exactly tied; deterministic tie-breaking is the only
    # information this outlier probe has.
    outlier = sorted([[i, i] for i in range(t)])

    used_y: set[int] = set()
    greedy = []
    for i in range(t):
        choices = sorted(
            (int((inst["X"][i] & inst["Y"][j]).bit_count()), j)
            for j in range(n)
            if j not in used_y
        )
        j = choices[0][1]
        used_y.add(j)
        greedy.append([i, j])
    greedy.sort()

    aligned_a = sorted([[i, i] for i in range(t)])
    aligned_b = sorted([[i, n - 1 - i] for i in range(t)])
    score_a = sum((inst["X"][i] & inst["Y"][j]).bit_count() for i, j in aligned_a)
    score_b = sum((inst["X"][i] & inst["Y"][j]).bit_count() for i, j in aligned_b)
    visual = aligned_a if score_a <= score_b else aligned_b

    restart_hit = None
    for _ in range(256):
        candidate = random_candidate(inst, rng)
        if verify(inst, candidate)[0]:
            restart_hit = candidate
            break
    return {
        "outlier_equal_degree": outlier,
        "greedy_minimum_intersection": greedy,
        "random_restart_256": restart_hit,
        "visual_same_or_reverse_row": visual,
    }


def _permute_instance(
    inst: dict,
    rng: random.Random,
    reorder: bool = False,
    coordinates: bool = False,
    swap_sides: bool = False,
) -> tuple[dict, list[list[int]]]:
    n, d = inst["n"], inst["d"]
    xs, ys = list(inst["X"]), list(inst["Y"])
    answer = [list(p) for p in inst["answer"]]
    if reorder:
        px = list(range(n))
        py = list(range(n))
        rng.shuffle(px)
        rng.shuffle(py)
        inv_x = {old: new for new, old in enumerate(px)}
        inv_y = {old: new for new, old in enumerate(py)}
        xs = [xs[old] for old in px]
        ys = [ys[old] for old in py]
        answer = [[inv_x[i], inv_y[j]] for i, j in answer]
    if coordinates:
        pc = list(range(d))
        rng.shuffle(pc)

        def pm(mask: int) -> int:
            value = 0
            for new, old in enumerate(pc):
                if mask & (1 << old):
                    value |= 1 << new
            return value

        xs = [pm(x) for x in xs]
        ys = [pm(y) for y in ys]
    if swap_sides:
        xs, ys = ys, xs
        answer = [[j, i] for i, j in answer]
    transformed = {
        "n": n,
        "d": d,
        "weight": inst["weight"],
        "target_count": inst["target_count"],
        "k": inst["k"],
        "X": xs,
        "Y": ys,
        "answer": sorted(answer),
    }
    return transformed, sorted(answer)


def _answer_atoms(value: object) -> int:
    if isinstance(value, dict):
        return sum(_answer_atoms(v) for v in value.values())
    if isinstance(value, list):
        return sum(_answer_atoms(v) for v in value)
    return 1


def selftest() -> dict:
    report: dict[str, object] = {"track": TRACK}

    # G1: all named presets and multiple seeds, plus the graph-level bag check.
    g1_checked = 0
    g1_ok = True
    compact_matches = 0
    for preset, params in DIFFICULTY.items():
        for seed in range(4):
            inst = make_instance(seed=seed, **params)
            ok, _ = verify(inst, inst["answer"])
            graph_ok = all(_is_p4_witness_pair(inst, i, j) for i, j in inst["answer"])
            compact, _ = _compact_pairs(inst)
            reference, _ = _reference_pairs(inst)
            routes_match = compact == reference == inst["answer"]
            compact_matches += int(routes_match)
            g1_ok &= ok and graph_ok and routes_match
            g1_checked += 1
    report["G1_planted_verifies"] = {
        "pass": bool(g1_ok),
        "instances": g1_checked,
        "independent_routes_match": compact_matches,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=81723, **shipping_params)
    ans = [list(p) for p in inst["answer"]]

    # G2: five distinct corruptions, intentionally routed to distinct diagnostics.
    bad_nonorth = [list(p) for p in ans]
    replacement = None
    old_i, old_j = bad_nonorth[0]
    for j in range(inst["n"]):
        if inst["X"][old_i] & inst["Y"][j] and [old_i, j] not in bad_nonorth:
            replacement = [old_i, j]
            break
    bad_nonorth[0] = replacement
    bad_nonorth.sort()
    corruptions = {
        "empty": [],
        "drop_one": ans[:-1],
        "duplicate": sorted(ans[:-1] + [ans[0]]),
        "swap_order": list(reversed(ans)),
        "out_of_range": sorted(ans[:-1] + [[inst["n"], 0]]),
        "change_one": bad_nonorth,
    }
    reasons = {name: verify(inst, value)[1] for name, value in corruptions.items()}
    g2_ok = all(not verify(inst, value)[0] for value in corruptions.values())
    g2_ok &= len(set(reasons.values())) == len(reasons)
    report["G2_rejects_corruption"] = {
        "pass": bool(g2_ok),
        "cases": reasons,
        "distinct_reasons": len(set(reasons.values())),
    }

    response = "I used the four bags from Theorem 4.\n```json\n<answer>\n" + json.dumps(ans) + "\n</answer>\n```"
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == ans and json.loads(json.dumps(ans)) == ans,
        "realistic_response": parsed == ans,
        "json_native": json.loads(json.dumps(ans)) == ans,
    }

    # G4/G5 share a shipping-preset structure-aware Monte Carlo sample.
    samples = 200_000
    guess_rng = random.Random(990177)
    hits = 0
    t0 = time.perf_counter()
    for _ in range(samples):
        if verify(inst, random_candidate(inst, guess_rng))[0]:
            hits += 1
    guess_elapsed = time.perf_counter() - t0
    report["G4_guess_resistance"] = {
        "pass": hits / samples < 0.000001 and 1 / search_space(inst) < 0.000001,
        "hits": hits,
        "total": samples,
        "observed_probability": hits / samples,
        "exact_probability": 1 / search_space(inst),
        "structure_aware_space": search_space(inst),
        "prior": "uniform sorted target_count-subset of the n^2 typed X-Y pairs",
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)

    # G6: every attack is evaluated on eight independent shipping instances.
    attacks = {
        "outlier_equal_degree": {"successes": 0, "attempts": 8},
        "greedy_minimum_intersection": {"successes": 0, "attempts": 8},
        "random_restart_256": {"successes": 0, "attempts": 8},
        "visual_same_or_reverse_row": {"successes": 0, "attempts": 8},
    }
    attack_wall = 0.0
    ref_wall = 0
    ref_ops = 0
    ref_success = 0
    compact_ops = 0
    compact_success = 0
    compact_wall = 0.0
    for seed in range(8):
        trial = make_instance(seed=5000 + seed, **shipping_params)
        attack_start = time.perf_counter()
        candidates = _attack_candidates(trial, random.Random(7000 + seed))
        for name, candidate in candidates.items():
            if candidate is not None and verify(trial, candidate)[0]:
                attacks[name]["successes"] += 1
        attack_wall += time.perf_counter() - attack_start
        start = time.perf_counter()
        found, ops = _reference_pairs(trial)
        ref_wall += time.perf_counter() - start
        ref_ops += ops
        if verify(trial, found)[0]:
            ref_success += 1
        start = time.perf_counter()
        compact_found, operations = _compact_pairs(trial)
        compact_wall += time.perf_counter() - start
        compact_ops += operations
        if verify(trial, compact_found)[0]:
            compact_success += 1
    report["G5_density_and_baseline"] = {
        "pass": demo_count == 1 and hits / samples < 0.000001 and ref_success == 8,
        "shipping_density_sample": {"hits": hits, "total": samples},
        "shipping_theoretical_density": f"1/{search_space(inst)}",
        "shipping_exact_solution_fraction": 1 / search_space(inst),
        "demo_exact_valid_answers_by_enumeration": demo_count,
        "demo_candidate_space": search_space(demo),
        "strongest_failing_attack": {
            "name": "random_restart_256",
            "wall_clock_sec_for_panel": attack_wall,
            "iterations": 8 * 256,
            "successes": attacks["random_restart_256"]["successes"],
        },
        "baseline_iterations": 8 * 256,
        "baseline_wall_clock_sec": attack_wall,
        "reference_algorithm_operations": ref_ops // 8,
        "reference_algorithm_wall_clock_sec": ref_wall / 8,
        "sampling_wall_clock_sec": guess_elapsed,
    }
    report["G6_adversary_panel"] = {
        "pass": all(v["successes"] == 0 and v["attempts"] >= 8 for v in attacks.values()),
        "attacks": attacks,
        "reference_algorithm": {
            "name": "naive Orthogonal Vectors pair scan from the Theorem 4 reduction",
            "complexity": "O(n^2 d)",
            "wall_clock_sec": ref_wall / 8,
            "operations": ref_ops // 8,
            "solves": f"{ref_success}/8, as expected",
            "compact_route": "half-swap orbit exceptions, then their cross-product",
            "compact_route_operations": compact_ops // 8,
            "compact_route_wall_clock_sec": compact_wall / 8,
            "compact_route_solves": f"{compact_success}/8, as expected",
        },
    }

    doubled = dict(shipping_params)
    doubled["n"] *= 2
    doubled["d"] += 8
    scaled = make_instance(seed=119, **doubled)
    report["G7_scales"] = {
        "pass": verify(scaled, scaled["answer"])[0]
        and search_space(scaled) > search_space(inst),
        "base_n": inst["n"],
        "doubled_n": scaled["n"],
        "base_space": search_space(inst),
        "doubled_space": search_space(scaled),
    }

    invariant_checks = 0
    carried_checks = 0
    original_keys = []
    g8_ok = True
    for seed in range(20):
        base = make_instance(seed=90000 + seed, **shipping_params)
        key = canonical_key(base)
        original_keys.append(key)
        rng = random.Random(120000 + seed)
        for flags in ((True, False, False), (False, True, False), (False, False, True), (True, True, True)):
            changed, carried = _permute_instance(
                base,
                rng,
                reorder=flags[0],
                coordinates=flags[1],
                swap_sides=flags[2],
            )
            g8_ok &= canonical_key(changed) == key
            invariant_checks += 1
            g8_ok &= verify(changed, carried)[0]
            carried_checks += 1
    distinct = len(set(original_keys))
    g8_ok &= distinct == 20
    report["G8_canonical_key"] = {
        "pass": bool(g8_ok),
        "invariance_checks": invariant_checks,
        "carried_witness_checks": carried_checks,
        "distinct_unrelated": distinct,
        "unrelated_attempts": 20,
        "transformations": ["X/Y reorderings", "coordinate permutation", "side swap", "composition"],
        "method": "1-WL quotient plus degree and common-neighbor multisets",
    }

    answer_blob = json.dumps(inst["answer"])
    answer_chars = len(answer_blob)
    answer_tokens = (answer_chars + 3) // 4
    answer_elements = _answer_atoms(inst["answer"])
    intended_ops = 2 * inst["n"] + inst["target_count"] ** 2
    hinted_attempts = _G9_ARMS["hinted"]["attempts"]
    placebo_attempts = _G9_ARMS["placebo"]["attempts"]
    within_caps = answer_chars <= 2000 and answer_elements <= 256 and intended_ops <= 300
    report["G9_no_tool_suitability"] = {
        # Since 2026-09-05 both the three-arm comparison and the hinted verdict
        # are diagnostics.  Only the answer-size and intended-effort caps gate.
        "pass": bool(within_caps),
        "arms": _G9_ARMS,
        "hinted_minus_placebo": (
            _G9_ARMS["hinted"]["solved"] / hinted_attempts
            - _G9_ARMS["placebo"]["solved"] / placebo_attempts
            if hinted_attempts and placebo_attempts
            else None
        ),
        "hinted_verdict": _G9_HINTED_VERDICT,
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "within_caps": within_caps,
    }
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping_params)
    report["certificate_language"] = CERTIFICATE_LANGUAGE
    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items()
        if key.startswith("G") and key[1:2].isdigit()
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
