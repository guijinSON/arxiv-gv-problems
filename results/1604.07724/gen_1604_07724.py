"""Verified generator for connected subgraphs in many graph layers.

The family is the Connectivity-ML-Subgraph construction in Section 4,
Theorem 1 and Corollary 5 of Bredereck et al. (arXiv:1604.07724).  A
balanced biclique is planted by degree-preserving switches in a dense random
graph and carried through the paper's reduction to native star layers.
"""

from __future__ import annotations

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
    from gvlib import exact_matrices, rationals
except ImportError:                 # pragma: no cover - no helper is needed
    exact_matrices = rationals = None


TRACK: str = "A"

PROBLEM_PROFILE: dict = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "graph",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "multi-layer graph whose layers are stars on a shared vertex set",
        "vertex set inducing a connected graph in many layers",
    ],
    "verification_operations": [
        "exact layer-incidence bitset intersection",
        "bit population count",
        "induced-star connectivity check",
    ],
    "domain_essentiality": "native",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 4, Theorem 1 and Corollary 5: the central reduction from "
        "Balanced Biclique to Connectivity-ML-Subgraph using star layers"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "reduction recognition",
    "intuition_description": (
        "The vertex-by-layer incidence table is a bipartite graph, and a "
        "connected set in many shared-hub star layers is exactly one shore "
        "of a balanced biclique; without this recognition one searches raw "
        "subsets of the common vertex set."
    ),
    "hardness_basis": (
        "Track A: Section 4, Theorem 1 proves W[1]-hardness for combined "
        "selected-vertex/layer parameters via Balanced Biclique; the presets "
        "use k=ell+1 with ell growing from 13 to 17 in degree-preserving "
        "dense planted-biclique instances, above the logarithmic accidental-"
        "biclique scale and below the square-root spectral scale, and G5 "
        "measures the capped exact-search cost at the shipping preset."
    ),
    "max_answer_tokens": 13,
}

NATIVE: dict = {
    "domain": PROBLEM_PROFILE["native_domain"],
    "core": PROBLEM_PROFILE["computational_core"],
    "objects": PROBLEM_PROFILE["native_objects"],
    "intuition": (
        PROBLEM_PROFILE["intuition_type"] + ": "
        + PROBLEM_PROFILE["intuition_description"]
    ),
    "reduction": PROBLEM_PROFILE["reduction"],
}

CERTIFICATE_LANGUAGE: dict = {
    "description": (
        "A strictly increasing JSON list of exactly k distinct vertex IDs "
        "from 0 through vertex_count-1.  The list must contain the displayed "
        "shared hub; the remaining ell IDs are sampled uniformly from all "
        "non-hub vertices."
    ),
    "bounds": {
        "length": "instance k = required_layers + 1",
        "entries": "distinct integers in [0, vertex_count)",
        "order": "strictly increasing",
        "required_member": "the displayed shared hub",
    },
}

DIFFICULTY: dict = {
    "demo": {"n": 8, "h": 2},
    "easy": {"n": 256, "h": 13},
    "medium": {"n": 400, "h": 15},
    "hard": {"n": 600, "h": 17},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT: str = (
    "The vertex-by-layer incidence table is the biadjacency matrix of a "
    "hidden balanced complete bipartite subgraph."
)
PLACEBO_HINT: str = (
    "The vertex identifiers and fixed-width hexadecimal rows should be read "
    "with consistent indexing throughout."
)

# These counts are updated only from transcripts produced by scripts/harden.py.
G9_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}

NOTES: str = r"""
Definition and regime. Section 1 defines Pi-ML-Subgraph: choose at least k
vertices whose induced graph has property Pi in at least ell of t layers.
Section 2 defines Connectivity, and Section 4 supplies the construction used
here.  In the star-layer regime every qualifying set can be trimmed to exactly
k=h+1 vertices, so the bounded output language loses no yes-witness.

What makes it easy. Proposition 3 gives an FPT algorithm in the total number
of layers t and an XP algorithm when ell or t-ell is constant.  Consequently
the generator has t=n growing and ell=h growing.  Theorem 2's polynomial
two-layer matching algorithm and Proposition 2's small-deletion FPT regime
were also rejected at Step 0 as bases for this family.

Certificate algorithm and track. Verification is polynomial: intersect the
h layer-incidence bitsets belonging to the non-hub answer vertices and count
the common layers.  That checker does not produce the witness.  Theorem 1
reduces Balanced Biclique to exactly these star layers and proves W[1]-hardness
for the combined parameters k and ell.  Track A is an empirical distributional
claim, not a proof of average-case hardness: the shipping distribution is a
dense random graph with a degree-preserved planted K_h,h, h above the usual
accidental-biclique scale and far below the square-root spectral scale.  G5
and G6 report the capped exact and spectral evidence.

Generation. Sample two disjoint h-sets first. Draw every edge of G(n,1/2).
For every missing planted cross-edge, perform a 2-switch: delete c-x and d-y,
then add c-d and x-y. This preserves every vertex degree exactly. The planted
biclique is therefore known before the public instance exists without giving
its vertices a degree signature. Independently permute graph vertices into
public non-hub IDs and graph rows into layer IDs. Theorem 1 turns each graph
row into a star layer whose leaves are that row's neighbors; the shared center
is the hub. The answer is the hub plus either planted shore.

Attack handling. The degree outlier attack tests both extremes; greedy and
random-restart attacks maximize surviving common layers; the construction-
aware pair attack starts from the pair with the largest common neighborhood;
centered singular-vector iteration tests the usual planted-subgraph signal;
and capped branch-and-bound is the standard exact balanced-biclique search.
Plants and decoys inherit the same initial G(n,1/2) degree distribution because
the switches preserve all degrees. Public vertex and layer permutations remove
position and row/column-alignment clues.
""".strip()


def _validate_parameters(n: int, h: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError("n must be an integer")
    if isinstance(h, bool) or not isinstance(h, int):
        raise ValueError("h must be an integer")
    if h < 2:
        raise ValueError("h must be at least 2")
    if n < 2 * h + 4:
        raise ValueError("n must be at least 2*h+4")


def _edge_key(a: int, b: int) -> tuple[int, int]:
    if a == b:
        raise ValueError("loops are not allowed")
    return (a, b) if a < b else (b, a)


def _neighbors_from_edges(n: int, edges: set[tuple[int, int]]) -> list[set[int]]:
    neighbors = [set() for _ in range(n)]
    for a, b in edges:
        neighbors[a].add(b)
        neighbors[b].add(a)
    return neighbors


def _degree_preserving_plant(
    n: int,
    left: list[int],
    right: list[int],
    rng: random.Random,
) -> tuple[set[tuple[int, int]], int]:
    """Draw G(n,1/2), then force left x right by degree-preserving switches."""
    planted = set(left) | set(right)
    outsiders = [v for v in range(n) if v not in planted]
    for _attempt in range(200):
        edges = {
            (a, b)
            for a in range(n)
            for b in range(a + 1, n)
            if rng.getrandbits(1)
        }
        original_degrees = [0] * n
        for a, b in edges:
            original_degrees[a] += 1
            original_degrees[b] += 1
        neighbors = _neighbors_from_edges(n, edges)
        switches = 0
        failed = False
        missing = [(a, b) for a in left for b in right
                   if _edge_key(a, b) not in edges]
        rng.shuffle(missing)
        for a, b in missing:
            xs = [x for x in outsiders if x in neighbors[a]]
            ys = [y for y in outsiders if y in neighbors[b]]
            rng.shuffle(xs)
            rng.shuffle(ys)
            choice = None
            for x in xs:
                for y in ys:
                    if x != y and _edge_key(x, y) not in edges:
                        choice = (x, y)
                        break
                if choice is not None:
                    break
            if choice is None:
                failed = True
                break
            x, y = choice
            edges.remove(_edge_key(a, x))
            edges.remove(_edge_key(b, y))
            edges.add(_edge_key(a, b))
            edges.add(_edge_key(x, y))
            neighbors[a].remove(x)
            neighbors[x].remove(a)
            neighbors[b].remove(y)
            neighbors[y].remove(b)
            neighbors[a].add(b)
            neighbors[b].add(a)
            neighbors[x].add(y)
            neighbors[y].add(x)
            switches += 1
        if failed:
            continue
        degrees = [0] * n
        for a, b in edges:
            degrees[a] += 1
            degrees[b] += 1
        if degrees != original_degrees:
            raise AssertionError("2-switch implementation changed a degree")
        if any(_edge_key(a, b) not in edges for a in left for b in right):
            raise AssertionError("planting did not complete the biclique")
        return edges, switches
    raise RuntimeError("could not realize the planted biclique by 2-switches")


def _perm_old_to_new(rng: random.Random, size: int) -> list[int]:
    images = list(range(size))
    rng.shuffle(images)
    return images


def make_instance(n: int, seed: int = 0, h: int | None = None,
                  **params: object) -> dict:
    """Build a paper-native star-layer instance from a known planted biclique."""
    if params:
        raise ValueError(f"unknown generation parameters: {sorted(params)}")
    if h is None:
        h = max(2, int(math.log2(n)) + 4)
    _validate_parameters(n, h)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    rng = random.Random(seed)

    planted_vertices = rng.sample(range(n), 2 * h)
    left = planted_vertices[:h]
    right = planted_vertices[h:]
    edges, _switches = _degree_preserving_plant(n, left, right, rng)
    neighbors = _neighbors_from_edges(n, edges)

    # Public vertex 0..n includes one uniformly positioned hub.  Old graph
    # vertices are mapped bijectively to the remaining public IDs.
    hub = rng.randrange(n + 1)
    public_nonhub = [v for v in range(n + 1) if v != hub]
    rng.shuffle(public_nonhub)
    vertex_image = public_nonhub
    layer_image = _perm_old_to_new(rng, n)
    width = (n + 3) // 4

    entries = []
    for old_vertex in range(n):
        mask = 0
        for old_layer in neighbors[old_vertex]:
            mask |= 1 << layer_image[old_layer]
        entries.append([vertex_image[old_vertex], format(mask, f"0{width}x")])
    rng.shuffle(entries)

    answer_side = left if rng.getrandbits(1) == 0 else right
    answer = sorted([hub] + [vertex_image[v] for v in answer_side])
    return {
        "family": "connectivity_multi_layer_shared_hub_stars",
        "base_order": n,
        "vertex_count": n + 1,
        "layer_count": n,
        "shared_hub": hub,
        "select_size": h + 1,
        "required_layers": h,
        "mask_hex_width": width,
        "incidence": entries,
        "answer": answer,
    }


def _instance_view(inst: dict) -> tuple[list[int], dict[int, int]]:
    try:
        n = inst["base_order"]
        vertex_count = inst["vertex_count"]
        layer_count = inst["layer_count"]
        hub = inst["shared_hub"]
        select_size = inst["select_size"]
        required = inst["required_layers"]
        width = inst["mask_hex_width"]
        entries = inst["incidence"]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"missing instance field: {exc}") from exc
    integers = [n, vertex_count, layer_count, hub, select_size, required, width]
    if any(isinstance(v, bool) or not isinstance(v, int) for v in integers):
        raise ValueError("instance dimensions must be integers")
    if n < 1 or vertex_count != n + 1 or layer_count != n:
        raise ValueError("inconsistent instance dimensions")
    if not 0 <= hub < vertex_count:
        raise ValueError("shared hub is outside the vertex range")
    if select_size != required + 1 or not 1 <= required <= n:
        raise ValueError("inconsistent selection thresholds")
    if width != (layer_count + 3) // 4:
        raise ValueError("incorrect hexadecimal mask width")
    if not isinstance(entries, list) or len(entries) != n:
        raise ValueError("incidence must contain one row per non-hub vertex")
    masks: dict[int, int] = {}
    for row in entries:
        if not (isinstance(row, list) and len(row) == 2):
            raise ValueError("each incidence row must be [vertex, hex_mask]")
        vertex, encoded = row
        if (isinstance(vertex, bool) or not isinstance(vertex, int)
                or not 0 <= vertex < vertex_count or vertex == hub):
            raise ValueError("incidence row has an invalid vertex")
        if vertex in masks:
            raise ValueError("incidence repeats a vertex")
        if (not isinstance(encoded, str) or len(encoded) != width
                or re.fullmatch(r"[0-9a-fA-F]+", encoded) is None):
            raise ValueError("incidence row has an invalid hexadecimal mask")
        mask = int(encoded, 16)
        if mask >= (1 << layer_count):
            raise ValueError("incidence mask sets a nonexistent layer bit")
        masks[vertex] = mask
    vertices = [v for v in range(vertex_count) if v != hub]
    if set(masks) != set(vertices):
        raise ValueError("incidence does not cover exactly the non-hub vertices")
    return vertices, masks


def render(inst: dict) -> str:
    vertices, _ = _instance_view(inst)
    del vertices
    rows = "\n".join(f"{vertex}: {mask}" for vertex, mask in inst["incidence"])
    example = list(range(inst["select_size"]))
    statement = f"""Connected induced subgraph in many layers

There are {inst['vertex_count']} vertices, with integer IDs 0 through
{inst['vertex_count'] - 1}, and {inst['layer_count']} undirected simple graph
layers numbered 0 through {inst['layer_count'] - 1}.  Every layer is a star
with the same hub vertex H={inst['shared_hub']}; a star may have any number of
leaves.  Thus the only possible edge in layer j incident to a non-hub vertex v
is {{H,v}}.

The table below completely specifies every layer.  Each row is
"vertex: hexadecimal-mask" for one non-hub vertex.  Every mask has exactly
{inst['mask_hex_width']} hexadecimal digits.  Bit j of the represented
nonnegative integer is 1 exactly when edge {{H,v}} is present in layer j; bit
0 is the least-significant (rightmost) bit.  No edges other than those encoded
by these masks exist.  Row order has no significance.

{rows}

Find exactly k={inst['select_size']} distinct vertices such that their induced
subgraph is connected in at least ell={inst['required_layers']} different
layers.  In a layer, "induced" means keeping precisely the edges of that layer
whose two endpoints are both selected.  A graph is connected when every pair
of its vertices is joined by an edge-path.  The same selected vertex set must
work in all counted layers.  Layer order does not matter.

Give the k vertex IDs as one strictly increasing JSON list; IDs are 0-indexed,
order is otherwise mathematically irrelevant, and repetitions are forbidden.
Give your final answer inside <answer></answer> tags, as that JSON list.
Example: <answer>{json.dumps(example)}</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    if not isinstance(text, str):
        return None
    blocks = re.findall(r"<answer\s*>(.*?)</answer\s*>", text,
                        flags=re.IGNORECASE | re.DOTALL)
    if not blocks:
        return None
    body = blocks[-1].strip()
    if body.startswith("```"):
        body = re.sub(r"^```(?:json|text)?\s*", "", body,
                      flags=re.IGNORECASE)
        body = re.sub(r"\s*```$", "", body).strip()
    try:
        value = json.loads(body)
    except (ValueError, TypeError):
        return None
    if not isinstance(value, list):
        return None
    if any(isinstance(v, bool) or not isinstance(v, int) for v in value):
        return None
    return value


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    if not isinstance(answer, list):
        return False, "answer must be a JSON list"
    if not answer:
        return False, "answer is empty"
    if any(isinstance(v, bool) or not isinstance(v, int) for v in answer):
        return False, "every vertex ID must be an integer"
    try:
        vertex_count = inst["vertex_count"]
        required_length = inst["select_size"]
        hub = inst["shared_hub"]
    except (KeyError, TypeError):
        return False, "instance is missing a threshold field"
    if any(v < 0 or v >= vertex_count for v in answer):
        return False, "a vertex ID is outside the allowed range"
    if len(set(answer)) != len(answer):
        return False, "vertex IDs must be distinct"
    if answer != sorted(answer):
        return False, "vertex IDs must be strictly increasing"
    if len(answer) != required_length:
        return False, f"answer must contain exactly {required_length} vertices"
    if hub not in answer:
        return False, "the shared hub is absent"
    try:
        _, masks = _instance_view(inst)
    except ValueError as exc:
        return False, f"malformed instance: {exc}"
    common = (1 << inst["layer_count"]) - 1
    for vertex in answer:
        if vertex != hub:
            common &= masks[vertex]
    count = common.bit_count()
    if count < inst["required_layers"]:
        return False, (
            f"the induced set is connected in only {count} layers, fewer than "
            f"the required {inst['required_layers']}"
        )
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    vertices, _ = _instance_view(inst)
    chosen = rng.sample(vertices, inst["required_layers"])
    return sorted([inst["shared_hub"]] + chosen)


def search_space(inst: dict) -> int | None:
    return math.comb(inst["base_order"], inst["required_layers"])


def _fast_valid(inst: dict, answer: list[int], masks: dict[int, int]) -> bool:
    common = (1 << inst["layer_count"]) - 1
    for vertex in answer:
        if vertex != inst["shared_hub"]:
            common &= masks[vertex]
    return common.bit_count() >= inst["required_layers"]


def enumerate_all(inst: dict) -> int | None:
    space = search_space(inst)
    if space is None or space > 1_000_000:
        return None
    vertices, masks = _instance_view(inst)
    count = 0
    for chosen in itertools.combinations(vertices, inst["required_layers"]):
        answer = sorted([inst["shared_hub"], *chosen])
        count += int(_fast_valid(inst, answer, masks))
    return count


def _wl_invariant(inst: dict) -> object:
    vertices, masks_by_label = _instance_view(inst)
    n = inst["layer_count"]
    col_masks = [masks_by_label[v] for v in vertices]
    row_neighbors = [[] for _ in range(n)]
    col_neighbors = []
    for col, mask in enumerate(col_masks):
        neighbors = []
        bits = mask
        while bits:
            bit = bits & -bits
            row = bit.bit_length() - 1
            neighbors.append(row)
            row_neighbors[row].append(col)
            bits ^= bit
        col_neighbors.append(neighbors)
    col_colors = [0] * n
    row_colors = [1] * n
    for _ in range(5):
        col_signatures = [
            ("C", col_colors[i], tuple(sorted(row_colors[j]
                                              for j in col_neighbors[i])))
            for i in range(n)
        ]
        row_signatures = [
            ("R", row_colors[j], tuple(sorted(col_colors[i]
                                              for i in row_neighbors[j])))
            for j in range(n)
        ]
        universe = sorted(set(col_signatures + row_signatures), key=repr)
        palette = {signature: color for color, signature in enumerate(universe)}
        new_cols = [palette[s] for s in col_signatures]
        new_rows = [palette[s] for s in row_signatures]
        if new_cols == col_colors and new_rows == row_colors:
            break
        col_colors, row_colors = new_cols, new_rows
    col_final = sorted(
        (col_colors[i], len(col_neighbors[i]),
         tuple(sorted(row_colors[j] for j in col_neighbors[i])))
        for i in range(n)
    )
    row_final = sorted(
        (row_colors[j], len(row_neighbors[j]),
         tuple(sorted(col_colors[i] for i in row_neighbors[j])))
        for j in range(n)
    )
    return [n, inst["select_size"], inst["required_layers"], col_final, row_final]


def canonical_key(inst: dict) -> str:
    payload = json.dumps(_wl_invariant(inst), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    current_n = int(params["n"])
    current_h = int(params.get("h", max(2, int(math.log2(current_n)) + 4)))
    harder_n = current_n + max(64, current_n // 2)
    # First grow only the haystack.  Once the first-moment estimate for an
    # accidental K_h,h in G(harder_n,1/2) reaches 1e-6, increase h by two to
    # keep random valid witnesses rare.  This postpones answer growth until the
    # fixed-length ambient-size axis has genuinely run out.
    log_expected = (
        2 * math.lgamma(harder_n + 1)
        - 2 * math.lgamma(current_h + 1)
        - 2 * math.lgamma(harder_n - current_h + 1)
        - current_h * current_h * math.log(2)
    )
    harder_h = current_h if log_expected < math.log(1e-6) else current_h + 2
    if harder_h + 1 > 256:
        return "cap_bound"
    return {"n": harder_n, "h": harder_h}


def _candidate(inst: dict, vertices: list[int]) -> list[int]:
    return sorted([inst["shared_hub"], *vertices])


def _attack_degree_extremes(inst: dict) -> bool:
    vertices, masks = _instance_view(inst)
    h = inst["required_layers"]
    ordered = sorted(vertices, key=lambda v: (masks[v].bit_count(), v))
    return (verify(inst, _candidate(inst, ordered[:h]))[0]
            or verify(inst, _candidate(inst, ordered[-h:]))[0])


def _greedy_from_start(
    inst: dict,
    start: int,
    vertices: list[int],
    masks: dict[int, int],
    rng: random.Random | None = None,
    pool: set[int] | None = None,
) -> list[int]:
    h = inst["required_layers"]
    chosen = [start]
    available = [v for v in vertices if v != start
                 and (pool is None or v in pool)]
    common = masks[start]
    while len(chosen) < h and available:
        scored = sorted(
            ((common & masks[v]).bit_count(), masks[v].bit_count(), -v, v)
            for v in available
        )
        if rng is None:
            pick = scored[-1][3]
        else:
            width = min(4, len(scored))
            top = scored[-width:]
            pick = rng.choice(top)[3]
        chosen.append(pick)
        available.remove(pick)
        common &= masks[pick]
    return _candidate(inst, chosen)


def _attack_greedy(inst: dict) -> bool:
    vertices, masks = _instance_view(inst)
    start = max(vertices, key=lambda v: (masks[v].bit_count(), -v))
    return verify(inst, _greedy_from_start(inst, start, vertices, masks))[0]


def _attack_random_restart(inst: dict, seed: int, restarts: int = 256) -> bool:
    vertices, masks = _instance_view(inst)
    rng = random.Random(seed)
    for _ in range(restarts):
        start = rng.choice(vertices)
        candidate = _greedy_from_start(inst, start, vertices, masks, rng)
        if verify(inst, candidate)[0]:
            return True
    return False


def _attack_pair_intersection(inst: dict) -> bool:
    vertices, masks = _instance_view(inst)
    best = None
    for i, a in enumerate(vertices):
        for b in vertices[i + 1:]:
            score = (masks[a] & masks[b]).bit_count()
            row = (score, -a, -b, a, b)
            if best is None or row > best:
                best = row
    if best is None:
        return False
    pool = set(vertices)
    first, second = best[3], best[4]
    common = masks[first] & masks[second]
    chosen = [first, second]
    pool.remove(first)
    pool.remove(second)
    while len(chosen) < inst["required_layers"] and pool:
        pick = max(pool, key=lambda v: ((common & masks[v]).bit_count(),
                                        masks[v].bit_count(), -v))
        chosen.append(pick)
        pool.remove(pick)
        common &= masks[pick]
    return verify(inst, _candidate(inst, chosen))[0]


def _attack_spectral(inst: dict, seed: int) -> bool:
    """Centered biadjacency power iteration plus a small greedy cleanup."""
    vertices, masks = _instance_view(inst)
    n = inst["layer_count"]
    edge_count = sum(mask.bit_count() for mask in masks.values())
    density = edge_count / (len(vertices) * n)
    rng = random.Random(seed)
    x = [rng.uniform(-1.0, 1.0) for _ in vertices]

    def normalize(vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    x = normalize(x)
    for _ in range(35):
        total_x = sum(x)
        y = [-density * total_x for _ in range(n)]
        for index, vertex in enumerate(vertices):
            bits = masks[vertex]
            while bits:
                bit = bits & -bits
                y[bit.bit_length() - 1] += x[index]
                bits ^= bit
        y = normalize(y)
        total_y = sum(y)
        next_x = []
        for vertex in vertices:
            value = -density * total_y
            bits = masks[vertex]
            while bits:
                bit = bits & -bits
                value += y[bit.bit_length() - 1]
                bits ^= bit
            next_x.append(value)
        x = normalize(next_x)

    h = inst["required_layers"]
    orders = [
        sorted(range(len(vertices)), key=lambda i: (x[i], -vertices[i]), reverse=True),
        sorted(range(len(vertices)), key=lambda i: (x[i], vertices[i])),
        sorted(range(len(vertices)), key=lambda i: (abs(x[i]), -vertices[i]),
               reverse=True),
    ]
    for order in orders:
        direct = [vertices[i] for i in order[:h]]
        if verify(inst, _candidate(inst, direct))[0]:
            return True
        pool = {vertices[i] for i in order[:min(2 * h, len(order))]}
        for start in list(pool):
            candidate = _greedy_from_start(
                inst, start, vertices, masks, pool=pool
            )
            if verify(inst, candidate)[0]:
                return True
    return False


def _exact_biclique_search(inst: dict, node_cap: int = 1_000_000) -> dict:
    """Capped exact enumeration of column shores with common-row pruning."""
    vertices, masks = _instance_view(inst)
    h = inst["required_layers"]
    ordered = sorted(vertices, key=lambda v: (-masks[v].bit_count(), v))
    all_rows = (1 << inst["layer_count"]) - 1
    nodes = 0
    found: list[int] | None = None

    def rec(position: int, chosen: list[int], common: int) -> None:
        nonlocal nodes, found
        if found is not None or nodes >= node_cap:
            return
        nodes += 1
        if common.bit_count() < h:
            return
        if len(chosen) == h:
            found = _candidate(inst, chosen)
            return
        needed = h - len(chosen)
        if len(ordered) - position < needed:
            return
        last = len(ordered) - needed
        for index in range(position, last + 1):
            vertex = ordered[index]
            rec(index + 1, chosen + [vertex], common & masks[vertex])
            if found is not None or nodes >= node_cap:
                return

    started = time.perf_counter()
    rec(0, [], all_rows)
    elapsed = time.perf_counter() - started
    success = found is not None and verify(inst, found)[0]
    return {
        "success": success,
        "answer": found,
        "nodes": nodes,
        "node_cap": node_cap,
        "cap_reached": nodes >= node_cap and found is None,
        "wall_clock_sec": elapsed,
    }


def _permute_mask(mask: int, permutation: list[int]) -> int:
    moved = 0
    bits = mask
    while bits:
        bit = bits & -bits
        moved |= 1 << permutation[bit.bit_length() - 1]
        bits ^= bit
    return moved


def _relabel_instance(inst: dict, seed: int) -> dict:
    rng = random.Random(seed)
    vertex_perm = _perm_old_to_new(rng, inst["vertex_count"])
    layer_perm = _perm_old_to_new(rng, inst["layer_count"])
    width = inst["mask_hex_width"]
    moved = {key: value for key, value in inst.items()
             if key not in {"shared_hub", "incidence", "answer"}}
    moved["shared_hub"] = vertex_perm[inst["shared_hub"]]
    moved["incidence"] = [
        [vertex_perm[vertex], format(_permute_mask(int(mask, 16), layer_perm),
                                     f"0{width}x")]
        for vertex, mask in inst["incidence"]
    ]
    rng.shuffle(moved["incidence"])
    moved["answer"] = sorted(vertex_perm[v] for v in inst["answer"])
    return moved


def _answer_atoms(answer: object) -> int:
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, (list, tuple)):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def _measure_attacks(params: dict, attempts: int = 8) -> tuple[dict, dict]:
    names = [
        "outlier_incidence_degree_extremes",
        "greedy_maximum_common_layers",
        "random_restart_256_greedy",
        "pair_common_neighborhood_outlier",
        "spectral_centered_biadjacency",
        "exact_balanced_biclique_branch_20m",
    ]
    successes = {name: 0 for name in names}
    exact_rows = []
    for seed in range(9100, 9100 + attempts):
        inst = make_instance(seed=seed, **params)
        successes[names[0]] += int(_attack_degree_extremes(inst))
        successes[names[1]] += int(_attack_greedy(inst))
        successes[names[2]] += int(_attack_random_restart(inst, seed))
        successes[names[3]] += int(_attack_pair_intersection(inst))
        successes[names[4]] += int(_attack_spectral(inst, seed))
        exact = _exact_biclique_search(inst, node_cap=20_000_000)
        successes[names[5]] += int(exact["success"])
        exact_rows.append(exact)
    attacks = {
        name: {"successes": successes[name], "attempts": attempts}
        for name in names
    }
    costs = {
        "name": "capped exact balanced-biclique branch and bound",
        "complexity": "O(binomial(n,h)) worst case with common-row pruning",
        "nodes_total": sum(row["nodes"] for row in exact_rows),
        "nodes_mean": sum(row["nodes"] for row in exact_rows) / attempts,
        "wall_clock_sec_total": sum(row["wall_clock_sec"] for row in exact_rows),
        "wall_clock_sec_mean": (
            sum(row["wall_clock_sec"] for row in exact_rows) / attempts
        ),
        "caps_reached": sum(int(row["cap_reached"]) for row in exact_rows),
    }
    return attacks, costs


def selftest() -> dict:
    report: dict = {}

    failures = []
    checks = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 2026):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            json_ok = json.loads(json.dumps(inst["answer"])) == inst["answer"]
            checks += 1
            if not (ok and json_ok):
                failures.append({"preset": preset, "seed": seed,
                                 "reason": reason, "json_native": json_ok})
    report["G1_planted_verifies"] = {
        "pass": not failures, "checks": checks, "failures": failures,
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=314159, **shipping)
    answer = inst["answer"]
    swap = answer[:]
    swap[0], swap[1] = swap[1], swap[0]
    replacement = next(v for v in range(inst["vertex_count"])
                       if v not in answer)
    corruptions = {
        "drop_one": answer[:-1],
        "swap_two": swap,
        "duplicate": answer[:-1] + [answer[-2]],
        "empty": [],
        "out_of_range": answer[:-1] + [inst["vertex_count"]],
        "valid_shape_wrong_set": sorted(answer[:-1] + [replacement]),
    }
    rejection_rows = {}
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        rejection_rows[name] = {"rejected": not ok, "reason": reason}
    mandatory_reasons = [rejection_rows[name]["reason"] for name in
                         ("drop_one", "swap_two", "duplicate", "empty",
                          "out_of_range")]
    report["G2_rejects_corruption"] = {
        "pass": all(row["rejected"] for row in rejection_rows.values())
                and len(set(mandatory_reasons)) == len(mandatory_reasons),
        "rejections": rejection_rows,
        "distinct_mandatory_reasons": len(set(mandatory_reasons)),
    }

    realistic = (
        "The shared set has enough common layers.\n```json\n"
        f"<answer>{json.dumps(answer)}</answer>\n```\nChecked exactly."
    )
    parsed = parse_answer(realistic)
    report["G3_round_trip"] = {
        "pass": parsed == answer and verify(inst, parsed)[0]
                and parse_answer("garbage") is None,
        "parsed_matches": parsed == answer,
        "garbage_returns_none": parse_answer("garbage") is None,
    }

    vertices, masks = _instance_view(inst)
    rng = random.Random(0x160407724)
    total = 200_000
    hits = 0
    predicate_matches = 0
    started = time.perf_counter()
    for index in range(total):
        candidate = sorted([inst["shared_hub"],
                            *rng.sample(vertices, inst["required_layers"])])
        fast = _fast_valid(inst, candidate, masks)
        hits += int(fast)
        if index < 100:
            predicate_matches += int(fast == verify(inst, candidate)[0])
    sample_seconds = time.perf_counter() - started
    fraction = hits / total
    report["G4_guess_resistance"] = {
        "pass": fraction < 1e-6 and predicate_matches == 100,
        "hits": hits,
        "total": total,
        "empirical_probability": fraction,
        "structure_aware_space": search_space(inst),
        "prior": "uniform h-subset of non-hub vertices; the hub is included for free",
        "fast_predicate_matches_verify": f"{predicate_matches}/100",
        "sampling_wall_seconds": sample_seconds,
    }

    baseline = _exact_biclique_search(inst, node_cap=20_000_000)
    demo = make_instance(seed=0, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    density_rng = random.Random(0x160407725)
    density_total = 200_000
    density_hits = 0
    for _ in range(density_total):
        candidate = sorted([
            inst["shared_hub"],
            *density_rng.sample(vertices, inst["required_layers"]),
        ])
        density_hits += int(_fast_valid(inst, candidate, masks))
    report["G5_density_and_baseline"] = {
        "pass": density_hits / density_total < 1e-6
                and not baseline["success"] and demo_count is not None
                and demo_count >= 1,
        "shipping_observed_valid_fraction": density_hits / density_total,
        "shipping_density_sample_count": density_total,
        "shipping_valid_hits": density_hits,
        "shipping_candidate_space": search_space(inst),
        "shipping_exact_valid_count": None,
        "baseline_wall_seconds": baseline["wall_clock_sec"],
        "baseline_nodes": baseline["nodes"],
        "baseline_node_cap": baseline["node_cap"],
        "baseline_cap_reached": baseline["cap_reached"],
        "baseline_successes": int(baseline["success"]),
        "baseline_algorithm": "exact balanced-biclique branch and bound",
        "demo_exact_valid_count": demo_count,
    }

    attacks, attack_cost = _measure_attacks(shipping, attempts=8)
    report["G6_adversary_panel"] = {
        "pass": all(row["successes"] == 0 for row in attacks.values()),
        "attacks": attacks,
        "standard_attack_cost": attack_cost,
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=271828, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    spaces = [search_space(make_instance(seed=9, **params))
              for name, params in DIFFICULTY.items() if name != "demo"]
    report["G7_scales"] = {
        "pass": doubled_ok and spaces == sorted(spaces)
                and len(set(spaces)) == len(spaces),
        "shipping_n": shipping["n"],
        "doubled_n": doubled_params["n"],
        "doubled_verifies": doubled_ok,
        "doubled_reason": doubled_reason,
        "named_candidate_spaces": spaces,
        "escalated_params": escalate(shipping),
    }

    invariant = True
    invariance_checks = 0
    carried_checks = 0
    g8_failures = []
    for seed in range(20):
        trial = make_instance(seed=10_000 + seed, **DIFFICULTY["easy"])
        key = canonical_key(trial)
        once = _relabel_instance(trial, 20_000 + seed)
        transforms = [
            once,
            _relabel_instance(trial, 30_000 + seed),
            _relabel_instance(once, 40_000 + seed),
        ]
        for moved in transforms:
            invariance_checks += 1
            if canonical_key(moved) != key:
                invariant = False
                g8_failures.append([seed, "key changed under relabelling"])
            carried_checks += 1
            if not verify(moved, moved["answer"])[0]:
                invariant = False
                g8_failures.append([seed, "carried witness stopped verifying"])
    unrelated = {
        canonical_key(make_instance(seed=50_000 + seed, **DIFFICULTY["easy"]))
        for seed in range(20)
    }
    report["G8_canonical_key"] = {
        "pass": invariant and len(unrelated) == 20,
        "invariance_checks": invariance_checks,
        "real_transformation_verify_checks": carried_checks,
        "distinct_unrelated_keys": len(unrelated),
        "unrelated_instances": 20,
        "symmetries": [
            "arbitrary common-vertex relabelling",
            "arbitrary layer permutation",
            "incidence-row reordering",
            "compositions of these transformations",
        ],
        "key_kind": "five-round bipartite Weisfeiler-Leman invariant",
        "failures": g8_failures,
    }

    blob = json.dumps(answer, separators=(",", ":"))
    chars = len(blob)
    tokens = math.ceil(chars / 4)
    elements = _answer_atoms(answer)
    intended_operations = inst["required_layers"] + 1
    arms = {name: dict(G9_EVIDENCE[name])
            for name in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else None)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else None)
    within_caps = chars <= 2000 and elements <= 256 and intended_operations <= 300
    report["G9_no_tool_suitability"] = {
        "pass": within_caps,
        "arms": arms,
        "hinted_minus_placebo": (
            hinted_rate - placebo_rate
            if hinted_rate is not None and placebo_rate is not None else None
        ),
        "hinted_verdict": G9_EVIDENCE["hinted_verdict"],
        "answer_chars": chars,
        "answer_tokens": tokens,
        "answer_elements": elements,
        "intended_route_operations": intended_operations,
        "caps": {"chars": 2000, "elements": 256, "operations": 300},
    }

    report["track"] = TRACK
    report["shipping_difficulty"] = SHIPPING_DIFFICULTY
    report["shipping_params"] = dict(shipping)
    report["certificate_language"] = CERTIFICATE_LANGUAGE
    report["problem_profile"] = PROBLEM_PROFILE
    report["all_passed"] = all(
        value.get("pass", False) for key, value in report.items()
        if key.startswith("G") and isinstance(value, dict)
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
