"""Verified problem generator for arXiv:2107.14126.

The task uses the paper's coloring-to-growth reduction.  A solver partitions a
displayed graph H into independent sets.  That partition expands, without any
search, into a zero-excess d=2 growth schedule for the target obtained by
joining H to a universal clique.  Instances are inverse-generated from a
balanced hidden coloring; the planted partition is known before any edges are
sampled.
"""

from __future__ import annotations

import copy
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
except ImportError:  # pragma: no cover - this family is standard-library-only
    exact_matrices = rationals = None


TRACK = "A"

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "target graph specified as a base graph joined to a universal clique",
        "zero-excess d=2 graph-growth schedule",
        "partition of base vertices into independent birth slots",
    ],
    "verification_operations": [
        "exact edge-membership comparison",
        "exact independent-set check",
        "exact replay of vertex births and local edge activations",
        "exact final-graph equality",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": (
        "Section 3, Theorem 4 (label thm:NP-HARD): join H to an |V(H)|-vertex "
        "universal clique, making growth-schedule length encode a coloring of H"
    ),
    "reduction_source": "paper_central",
    "intuition_type": "reduction recognition",
    "intuition_description": (
        "The universal clique supplies distinct parents, while the remaining "
        "birth slots are exactly independent sets of the displayed base graph."
    ),
    "hardness_basis": (
        "Track A: Section 3, Theorem 4 (thm:NP-HARD) proves zero-excess growth "
        "NP-complete via this universal-clique join; the shipping distribution "
        "uses balanced planted 6-color graphs with n=192 and cross-edge "
        "probability 25/192 (fixed expected degree about 20.8), where capped "
        "DSATUR visits 100001 nodes on each of "
        "8 seeds without a schedule (3.187 seconds per instance in the recorded "
        "local run; the current exact measurement is in G5)."
    ),
    "max_answer_tokens": 168,
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
    "easy": {"n": 192, "colors": 6, "density": 25},
}
SHIPPING_DIFFICULTY = "easy"

CERTIFICATE_LANGUAGE = {
    "description": (
        "An unordered set partition of H0,...,H(n-1) into exactly k nonempty "
        "independent sets, serialized as a JSON list of k integer lists; every "
        "vertex occurs exactly once.  Class order and order within a class are "
        "semantically irrelevant."
    ),
    "bounds": {
        "shipping_vertices": 192,
        "shipping_classes": 6,
        "vertex_min": 0,
        "vertex_max": 191,
        "each_vertex_exactly_once": True,
    },
}

STRUCTURAL_HINT = (
    "Slot membership in the universal-join target is governed entirely by "
    "independent sets of the displayed base graph."
)
PLACEBO_HINT = (
    "Careful bookkeeping of the displayed vertex names and slot boundaries "
    "helps avoid malformed schedules."
)

# Filled after the three isolated harden.py runs.  Until then G9 is deliberately
# reported as pending rather than manufactured from local heuristics.
G9_RESULTS = {
    "arms": {
        "bare": {"solved": 0, "attempts": 0},
        "hinted": {"solved": 0, "attempts": 0},
        "placebo": {"solved": 0, "attempts": 0},
    },
    "hinted_verdict": "pending",
}

NOTES = """\
Section 2.1 and Definition 1 fix the exact d=2 dynamics: an old vertex has at
most one child in a slot, and the child may join its parent and old neighbors
of that parent.  Section 3, Theorem 4 (thm:NP-HARD) is the construction used here:
join a graph H to an equally large universal clique; color classes of H become
birth slots and the clique vertices are distinct parents.  The certificate is
produced from the hidden balanced coloring before cross-class edges are drawn,
never by solving the resulting graph.

The easy regimes explicitly avoided are Section 2's optimal polynomial
trimming algorithm for d=1, Section 3's candidate-elimination recognition for
unbounded-length zero-excess schedules, and Section 3's matching-plus-2-SAT
fast-growth algorithm for exactly log(n) zero-excess slots.  This family uses
d=2 and the variable-slot NP-complete regime instead.

Plant and non-plant vertices have the same marginal degree distribution.
Degree ranking, deterministic greedy coloring, 256 randomized greedy restarts,
a bottom-eigenspace clustering probe, and capped exact DSATUR are all measured
on eight shipping seeds.  Input-edge order and vertex names are randomized.
"""


def _canonical_partition(parts):
    groups = [sorted(int(v) for v in part) for part in parts]
    groups.sort(key=lambda g: (g[0] if g else -1, len(g), g))
    return groups


def make_instance(n, seed=0, **params) -> dict:
    """Inverse-generate a certified zero-excess growth instance.

    A balanced coloring is sampled first.  Edges are then sampled independently
    only between different planted classes.  The returned answer is the known
    independent-set partition and is never recovered from the sampled graph.
    """
    n = int(n)
    colors = int(params.get("colors", 6))
    density = int(params.get("density", 25))
    edge_num = density
    edge_den = n
    if colors < 2 or n < 2 * colors:
        raise ValueError("need colors >= 2 and n >= 2*colors")
    if not (0 < density < n):
        raise ValueError("need 0 < density < n")

    rng = random.Random(seed)
    vertices = list(range(n))
    rng.shuffle(vertices)
    q, rem = divmod(n, colors)
    hidden = []
    pos = 0
    for c in range(colors):
        size = q + (1 if c < rem else 0)
        hidden.append(vertices[pos:pos + size])
        pos += size
    hidden_color = [0] * n
    for c, group in enumerate(hidden):
        for v in group:
            hidden_color[v] = c

    edges = []
    for u in range(n):
        for v in range(u):
            if (hidden_color[u] != hidden_color[v]
                    and rng.randrange(edge_den) < edge_num):
                edges.append([v, u])
    rng.shuffle(edges)

    return {
        "paper": "2107.14126",
        "n": n,
        "colors": colors,
        "density": density,
        "edge_num": edge_num,
        "edge_den": edge_den,
        "edges": edges,
        # In the paper's reduction the target has H plus an n-vertex universal
        # clique.  With G0's initiator not counted as an update, this normal form
        # uses n-1 clique births and `colors` H-birth slots.
        "target_vertices": 2 * n,
        "update_slot_bound": n - 1 + colors,
        "answer": _canonical_partition(hidden),
    }


def render(inst) -> str:
    n = int(inst["n"])
    k = int(inst["colors"])
    edges = json.dumps(inst["edges"], separators=(",", ":"))
    statement = f"""Zero-excess growth schedule for a universal-join graph

There are two named groups of vertices:

* U0,...,U{n - 1} form a clique, and every Ui is adjacent to every other
  vertex.  Thus all U-vertices are universal.
* H0,...,H{n - 1} induce the graph H whose complete edge list is printed below.
  There are no other H-H edges.

The target graph T is exactly this {2 * n}-vertex graph.  Vertex indices are
0-based.  Every edge [a,b] below is undirected; endpoint order and edge-list
order carry no information.

H_EDGES={edges}

Growth rule (edge-activation distance d=2): initially only U0 exists.  In one
update slot, each already existing vertex may create at most one new child.
A new child must connect to its parent and may also connect to any already
existing neighbor of that parent.  Two children created in the same slot
cannot be connected to each other.  A zero-excess schedule never deletes an
edge.

Find exactly {k} nonempty sets partitioning all H-vertex indices 0,...,{n - 1}
such that no H-edge has both endpoints in one set.  Such a partition is a
concrete certificate for this normal-form zero-excess schedule: first create
U1,...,U{n - 1} one per slot from U0, connecting each to all older U-vertices;
then use your {k} sets as the next {k} birth slots.  Within each set, increasing
H-index order assigns distinct parents U0,U1,..., and every child activates
exactly its target edges to older vertices.  The verifier performs this replay
and compares the final graph with T.  The schedule has at most
{inst['update_slot_bound']} update slots.  Set order and order inside a set do
not matter, repeats are forbidden, and every H-index must occur exactly once.

Give your final answer inside <answer></answer> tags as a JSON list of exactly
{k} nonempty integer lists.
Example format: <answer>[[0,3],[1,4],[2,5]]</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\nHint: " + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\nHint: " + PLACEBO_HINT
    return statement


def _strip_fence(text):
    text = text.strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 2:
            text = "\n".join(lines[1:-1]).strip()
    return text


def parse_answer(text):
    """Parse a tagged JSON partition, tolerating prose and markdown fences."""
    if not isinstance(text, str):
        return None
    matches = re.findall(r"<answer\b[^>]*>(.*?)</answer\s*>", text,
                         flags=re.IGNORECASE | re.DOTALL)
    candidates = [_strip_fence(x) for x in reversed(matches)]
    if not candidates:
        # A forgiving fallback for a model that supplies a bare/fenced array.
        candidates = [text]
    decoder = json.JSONDecoder()
    for candidate in candidates:
        candidate = _strip_fence(candidate)
        try:
            value = json.loads(candidate)
            return value if isinstance(value, list) else None
        except (ValueError, TypeError):
            pass
        for match in re.finditer(r"\[", candidate):
            try:
                value, _ = decoder.raw_decode(candidate[match.start():])
            except (ValueError, TypeError):
                continue
            if isinstance(value, list):
                return value
    return None


def _adjacency(inst):
    n = int(inst["n"])
    adj = [set() for _ in range(n)]
    masks = [0] * n
    for edge in inst["edges"]:
        u, v = int(edge[0]), int(edge[1])
        adj[u].add(v)
        adj[v].add(u)
        masks[u] |= 1 << v
        masks[v] |= 1 << u
    return adj, masks


def _replay_normal_schedule(inst, parts):
    """Replay the expanded schedule and compare exactly with its target."""
    n = int(inst["n"])
    total = 2 * n
    base_adj, _ = _adjacency(inst)
    expected = [0] * total
    all_vertices = (1 << total) - 1
    u_mask = (1 << n) - 1

    for u in range(n):
        expected[u] = all_vertices ^ (1 << u)
    for v in range(n):
        hv = n + v
        expected[hv] = u_mask
        for w in base_adj[v]:
            expected[hv] |= 1 << (n + w)

    grown = [0] * total
    alive = 1  # U0

    def birth(child, parent, wanted_old):
        nonlocal alive
        if alive & (1 << child):
            return False, "replay attempted to create an existing vertex"
        if not (alive & (1 << parent)):
            return False, "replay used a parent that was not yet alive"
        allowed = (grown[parent] | (1 << parent)) & alive
        if wanted_old & ~allowed:
            return False, "replay violated the d=2 local-activation rule"
        for old in range(total):
            if wanted_old & (1 << old):
                grown[child] |= 1 << old
                grown[old] |= 1 << child
        alive |= 1 << child
        return True, "ok"

    # Grow the universal clique.  U0 is adjacent to every older U at each step.
    for child in range(1, n):
        ok, why = birth(child, 0, alive)
        if not ok:
            return False, why

    # Grow each independent color class in one simultaneous slot.  All wanted
    # neighbors are old; same-slot H-H edges were already ruled out by verify.
    for part in parts:
        slot_alive = alive
        pending = []
        for j, v in enumerate(sorted(part)):
            child = n + v
            wanted = u_mask
            for w in base_adj[v]:
                hw = n + w
                if slot_alive & (1 << hw):
                    wanted |= 1 << hw
            allowed = (grown[j] | (1 << j)) & slot_alive
            if wanted & ~allowed:
                return False, "replay violated the d=2 local-activation rule"
            pending.append((child, wanted))
        for child, wanted in pending:
            for old in range(total):
                if wanted & (1 << old):
                    grown[child] |= 1 << old
                    grown[old] |= 1 << child
            alive |= 1 << child

    if alive != all_vertices:
        return False, "replay did not create every target vertex"
    if grown != expected:
        return False, "replayed final graph differs from the target graph"
    return True, "ok"


def verify(inst, answer):
    """Verify any partition certificate in the declared language."""
    n = int(inst["n"])
    k = int(inst["colors"])
    if not isinstance(answer, list):
        return False, "answer must be a JSON list of color classes"
    if not answer:
        return False, "answer is empty"
    if len(answer) != k or any(not isinstance(part, list) or not part
                               for part in answer):
        return False, f"expected exactly {k} nonempty color classes"

    seen = set()
    clean = []
    for part in answer:
        group = []
        for v in part:
            if isinstance(v, bool) or not isinstance(v, int):
                return False, "every vertex name must be an integer"
            if not 0 <= v < n:
                return False, f"vertex out of range: {v}"
            if v in seen:
                return False, f"duplicate vertex: {v}"
            seen.add(v)
            group.append(v)
        clean.append(group)
    if len(seen) != n:
        return False, f"missing vertex: listed {len(seen)} of {n}"

    color = [-1] * n
    for c, group in enumerate(clean):
        for v in group:
            color[v] = c
    for u, v in inst["edges"]:
        if color[u] == color[v]:
            return False, f"edge conflict: H{u}-H{v} lies within one class"

    ok, why = _replay_normal_schedule(inst, clean)
    if not ok:
        return False, why
    return True, "ok"


def _stirling2(n, k):
    if k < 0 or k > n:
        return 0
    row = [0] * (k + 1)
    row[0] = 1
    for _ in range(n):
        nxt = [0] * (k + 1)
        for j in range(1, k + 1):
            nxt[j] = row[j - 1] + j * row[j]
        row = nxt
    return row[k]


def random_candidate(inst, rng):
    """Uniformly sample an unlabeled, exactly-k-block set partition."""
    n = int(inst["n"])
    k = int(inst["colors"])
    while True:
        labels = [rng.randrange(k) for _ in range(n)]
        if len(set(labels)) == k:
            break
    groups = [[] for _ in range(k)]
    for v, c in enumerate(labels):
        groups[c].append(v)
    return _canonical_partition(groups)


def search_space(inst):
    return _stirling2(int(inst["n"]), int(inst["colors"]))


def enumerate_all(inst):
    """Count valid exactly-k partitions when the full partition space is small."""
    n = int(inst["n"])
    k = int(inst["colors"])
    if search_space(inst) > 150_000:
        return None
    _, masks = _adjacency(inst)
    class_masks = [0] * k
    nodes = 0
    cap = 2_000_000

    def rec(v, used):
        nonlocal nodes
        nodes += 1
        if nodes > cap:
            raise RuntimeError("enumeration cap")
        if v == n:
            return int(used == k)
        if used + (n - v) < k:
            return 0
        total = 0
        for c in range(min(used + 1, k)):
            if masks[v] & class_masks[c]:
                continue
            old = class_masks[c]
            class_masks[c] |= 1 << v
            total += rec(v + 1, max(used, c + 1))
            class_masks[c] = old
        return total

    try:
        class_masks[0] = 1  # restricted-growth normalization: vertex 0 in block 0
        return rec(1, 1)
    except RuntimeError:
        return None


def _wl_invariant(inst):
    """A label-invariant 1-WL signature, strengthened by cell edge counts."""
    n = int(inst["n"])
    adj, _ = _adjacency(inst)
    colors = [len(adj[v]) for v in range(n)]
    for _ in range(n):
        sigs = [(colors[v], tuple(sorted(colors[u] for u in adj[v])))
                for v in range(n)]
        palette = {sig: i for i, sig in enumerate(sorted(set(sigs)))}
        new = [palette[sig] for sig in sigs]
        if new == colors:
            break
        colors = new
    cells = {}
    for v, c in enumerate(colors):
        cells.setdefault(c, []).append(v)
    edge_counts = {}
    for u, v in inst["edges"]:
        a, b = sorted((colors[u], colors[v]))
        edge_counts[(a, b)] = edge_counts.get((a, b), 0) + 1
    return {
        "n": n,
        "k": int(inst["colors"]),
        "cell_sizes": sorted((c, len(vs)) for c, vs in cells.items()),
        "cell_degrees": sorted(
            (c, tuple(sorted(len(adj[v]) for v in vs)))
            for c, vs in cells.items()
        ),
        "cell_edges": sorted((a, b, z) for (a, b), z in edge_counts.items()),
    }


def canonical_key(inst):
    payload = json.dumps(_wl_invariant(inst), sort_keys=True,
                         separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def escalate(params):
    p = dict(params)
    n = int(p["n"])
    density = int(p.get("density", 25))
    # First tighten at fixed witness length.  This shrinks the solution set;
    # every escalated rung must still be re-audited because extra density can
    # eventually help planted-color recovery.
    if density < 28:
        p["density"] = density + 1
        return p
    # Then grow the graph while the certificate remains within 256 atoms.
    if n < 256:
        p["n"] = min(256, n + 16)
        p["density"] = 25
        return p
    return "cap_bound"


def _parts_from_colors(colors, k):
    if colors is None or len(colors) == 0:
        return None
    groups = [[] for _ in range(k)]
    for v, c in enumerate(colors):
        if not 0 <= c < k:
            return None
        groups[c].append(v)
    # A coloring with fewer colors can be split without introducing conflicts.
    while any(not g for g in groups):
        empty = next(i for i, g in enumerate(groups) if not g)
        donor = max(range(k), key=lambda i: len(groups[i]))
        if len(groups[donor]) < 2:
            return None
        groups[empty].append(groups[donor].pop())
    return _canonical_partition(groups)


def _attack_degree_quantiles(inst):
    adj, _ = _adjacency(inst)
    order = sorted(range(inst["n"]), key=lambda v: (len(adj[v]), v))
    colors = [0] * inst["n"]
    for i, v in enumerate(order):
        colors[v] = i % inst["colors"]
    return _parts_from_colors(colors, inst["colors"])


def _greedy_dsatur(inst, rng=None, restarts=1):
    adj, _ = _adjacency(inst)
    n, k = inst["n"], inst["colors"]
    for _ in range(restarts):
        colors = [-1] * n
        saturation = [0] * n
        failed = False
        for _step in range(n):
            uncolored = [v for v in range(n) if colors[v] < 0]
            score = max((saturation[v].bit_count(), len(adj[v]))
                        for v in uncolored)
            choices = [v for v in uncolored
                       if (saturation[v].bit_count(), len(adj[v])) == score]
            v = (rng.choice(choices) if rng is not None else min(choices))
            available = [c for c in range(k)
                         if not (saturation[v] & (1 << c))]
            if not available:
                failed = True
                break
            c = (rng.choice(available) if rng is not None else available[0])
            colors[v] = c
            for u in adj[v]:
                if colors[u] < 0:
                    saturation[u] |= 1 << c
        if not failed:
            return _parts_from_colors(colors, k)
    return None


def _orthonormalize(columns, constant=True):
    if not columns:
        return []
    n = len(columns[0])
    out = []
    for col in columns:
        v = list(col)
        if constant:
            mean = sum(v) / n
            v = [x - mean for x in v]
        for q in out:
            dot = sum(a * b for a, b in zip(v, q))
            v = [a - dot * b for a, b in zip(v, q)]
        norm = math.sqrt(sum(x * x for x in v))
        if norm > 1e-12:
            out.append([x / norm for x in v])
    return out


def _attack_spectral(inst, rng):
    """Bottom-adjacency eigenspace plus deterministic k-means."""
    adj, _ = _adjacency(inst)
    n, k = inst["n"], inst["colors"]
    dim = k - 1
    columns = [[rng.uniform(-1.0, 1.0) for _ in range(n)]
               for _ in range(dim)]
    columns = _orthonormalize(columns)
    shift = max(len(x) for x in adj) + 1
    for _ in range(45):
        moved = []
        for col in columns:
            moved.append([
                shift * col[v] - sum(col[u] for u in adj[v])
                for v in range(n)
            ])
        columns = _orthonormalize(moved)
        if len(columns) != dim:
            return None
    points = [tuple(columns[j][v] for j in range(dim)) for v in range(n)]

    def dist2(a, b):
        return sum((x - y) ** 2 for x, y in zip(a, b))

    first = max(range(n), key=lambda v: (sum(x * x for x in points[v]), -v))
    centers = [points[first]]
    while len(centers) < k:
        nxt = max(range(n), key=lambda v: min(dist2(points[v], c)
                                              for c in centers))
        centers.append(points[nxt])
    labels = [0] * n
    for _ in range(35):
        new = [min(range(k), key=lambda c: dist2(points[v], centers[c]))
               for v in range(n)]
        groups = [[v for v in range(n) if new[v] == c] for c in range(k)]
        if any(not g for g in groups):
            return None
        new_centers = []
        for group in groups:
            new_centers.append(tuple(
                sum(points[v][j] for v in group) / len(group)
                for j in range(dim)
            ))
        if new == labels:
            labels = new
            break
        labels, centers = new, new_centers
    return _parts_from_colors(labels, k)


def _attack_exact_dsatur(inst, node_limit=100_000):
    """Exact DSATUR branch-and-bound, capped only for the adversary panel."""
    _, masks = _adjacency(inst)
    n, k = inst["n"], inst["colors"]
    degrees = [m.bit_count() for m in masks]
    colors = [-1] * n
    saturation = [0] * n
    nodes = 0
    capped = False

    def rec(done):
        nonlocal nodes, capped
        nodes += 1
        if nodes > node_limit:
            capped = True
            return None
        if done == n:
            return colors[:]
        v = max((x for x in range(n) if colors[x] < 0),
                key=lambda x: (saturation[x].bit_count(), degrees[x], -x))
        forbidden = saturation[v]
        highest = max(colors)
        # Color symmetry: use existing colors, plus at most the next new color.
        for c in range(min(k, highest + 2)):
            if forbidden & (1 << c):
                continue
            colors[v] = c
            changes = []
            neighbors = masks[v]
            while neighbors:
                bit = neighbors & -neighbors
                u = bit.bit_length() - 1
                neighbors -= bit
                if colors[u] < 0 and not (saturation[u] & (1 << c)):
                    changes.append((u, saturation[u]))
                    saturation[u] |= 1 << c
            found = rec(done + 1)
            if found is not None:
                return found
            for u, old in changes:
                saturation[u] = old
            colors[v] = -1
            if capped:
                return None
        return None

    answer = rec(0)
    return _parts_from_colors(answer, k), nodes, capped


def _relabel_instance(inst, permutation, reverse_edges=False):
    """Carry a base-vertex relabelling through both instance and witness."""
    out = copy.deepcopy(inst)
    out["edges"] = [[permutation[u], permutation[v]] for u, v in inst["edges"]]
    out["edges"] = [[min(u, v), max(u, v)] for u, v in out["edges"]]
    if reverse_edges:
        out["edges"].reverse()
    out["answer"] = _canonical_partition(
        [[permutation[v] for v in part] for part in inst["answer"]]
    )
    return out


def _answer_token_measure(answer):
    # Stable, conservative approximation used throughout this corpus.
    return (len(json.dumps(answer, separators=(",", ":"))) + 3) // 4


def selftest():
    report = {"paper": "2107.14126", "track": TRACK,
              "shipping_difficulty": SHIPPING_DIFFICULTY}

    # G1: every preset, several unrelated seeds, and JSON-native answers.
    g1_attempts = 0
    g1_ok = 0
    json_native = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17):
            inst = make_instance(seed=seed, **params)
            ok, _ = verify(inst, inst["answer"])
            g1_attempts += 1
            g1_ok += int(ok)
            json_native += int(json.loads(json.dumps(inst["answer"]))
                               == inst["answer"])
    report["G1_planted_verifies"] = {
        "pass": g1_ok == g1_attempts and json_native == g1_attempts,
        "verified": g1_ok,
        "attempts": g1_attempts,
        "json_native": json_native,
    }

    # G2: five semantically different corruptions and five distinct diagnostics.
    base = make_instance(seed=222, **DIFFICULTY[SHIPPING_DIFFICULTY])
    planted = copy.deepcopy(base["answer"])
    corruptions = {}
    dropped = copy.deepcopy(planted)
    dropped[-1].pop()
    corruptions["drop"] = dropped

    swapped = None
    for a in range(len(planted)):
        if swapped is not None:
            break
        for b in range(a + 1, len(planted)):
            if swapped is not None:
                break
            for ia in range(len(planted[a])):
                if swapped is not None:
                    break
                for ib in range(len(planted[b])):
                    trial = copy.deepcopy(planted)
                    trial[a][ia], trial[b][ib] = trial[b][ib], trial[a][ia]
                    ok, why = verify(base, trial)
                    if not ok and why.startswith("edge conflict"):
                        swapped = trial
                        break
    corruptions["swap"] = swapped if swapped is not None else [[0]]
    duplicated = copy.deepcopy(planted)
    duplicated[-1][-1] = planted[0][0]
    corruptions["duplicate"] = duplicated
    corruptions["empty"] = []
    out_of_range = copy.deepcopy(planted)
    out_of_range[0][0] = base["n"]
    corruptions["out_of_range"] = out_of_range
    rejection_reasons = {}
    all_rejected = True
    for name, answer in corruptions.items():
        ok, why = verify(base, answer)
        all_rejected &= not ok
        rejection_reasons[name] = why
    report["G2_rejects_corruption"] = {
        "pass": all_rejected and len(set(rejection_reasons.values())) == 5,
        "reasons": rejection_reasons,
    }

    # G3: realistic surrounding prose, fences, and exact JSON round trip.
    encoded = json.dumps(base["answer"], separators=(",", ":"))
    response = ("I used the independent birth slots from the join construction.\n"
                "<answer>\n```json\n" + encoded
                + "\n```\n</answer>\nThe replay is zero-excess.")
    parsed = parse_answer(response)
    report["G3_round_trip"] = {
        "pass": parsed == base["answer"] and parse_answer("nonsense") is None,
        "model_style_round_trip": parsed == base["answer"],
        "garbage_returns_none": parse_answer("nonsense") is None,
    }

    shipping_params = DIFFICULTY[SHIPPING_DIFFICULTY]
    density_inst = make_instance(seed=424242, **shipping_params)
    guess_rng = random.Random(0x210714126)
    guess_total = 200_000
    guess_hits = 0
    density_start = time.perf_counter()
    for _ in range(guess_total):
        candidate = random_candidate(density_inst, guess_rng)
        guess_hits += int(verify(density_inst, candidate)[0])
    density_wall = time.perf_counter() - density_start
    guess_probability = guess_hits / guess_total
    report["G4_guess_resistance"] = {
        "pass": guess_probability < 1e-6,
        "hits": guess_hits,
        "total": guess_total,
        "observed_probability": guess_probability,
        "structure_aware": True,
        "candidate_space": search_space(density_inst),
    }

    # G6 is measured before G5 so G5 can report the strongest baseline cost.
    attack_names = [
        "degree_quantile_outlier",
        "greedy_dsatur_no_backtrack",
        "randomized_greedy_256",
        "spectral_bottom_eigenspace",
        "exact_dsatur_100k_nodes",
    ]
    attack_successes = {name: 0 for name in attack_names}
    attack_walls = {name: 0.0 for name in attack_names}
    exact_nodes = 0
    exact_capped = 0
    attack_seeds = list(range(6000, 6008))
    for seed in attack_seeds:
        inst = make_instance(seed=seed, **shipping_params)

        started = time.perf_counter()
        ans = _attack_degree_quantiles(inst)
        attack_walls[attack_names[0]] += time.perf_counter() - started
        attack_successes[attack_names[0]] += int(
            ans is not None and verify(inst, ans)[0])

        started = time.perf_counter()
        ans = _greedy_dsatur(inst)
        attack_walls[attack_names[1]] += time.perf_counter() - started
        attack_successes[attack_names[1]] += int(
            ans is not None and verify(inst, ans)[0])

        started = time.perf_counter()
        ans = _greedy_dsatur(inst, random.Random(seed ^ 0xA11CE), 256)
        attack_walls[attack_names[2]] += time.perf_counter() - started
        attack_successes[attack_names[2]] += int(
            ans is not None and verify(inst, ans)[0])

        started = time.perf_counter()
        ans = _attack_spectral(inst, random.Random(seed ^ 0x5EEC7))
        attack_walls[attack_names[3]] += time.perf_counter() - started
        attack_successes[attack_names[3]] += int(
            ans is not None and verify(inst, ans)[0])

        started = time.perf_counter()
        ans, nodes, capped = _attack_exact_dsatur(inst, 100_000)
        attack_walls[attack_names[4]] += time.perf_counter() - started
        exact_nodes += nodes
        exact_capped += int(capped)
        attack_successes[attack_names[4]] += int(
            ans is not None and verify(inst, ans)[0])

    attacks = {}
    for name in attack_names:
        attacks[name] = {
            "successes": attack_successes[name],
            "attempts": len(attack_seeds),
            "wall_clock_sec": round(attack_walls[name], 6),
        }
    attacks["exact_dsatur_100k_nodes"].update({
        "nodes": exact_nodes,
        "capped_attempts": exact_capped,
    })
    report["G6_adversary_panel"] = {
        "pass": all(z == 0 for z in attack_successes.values()),
        "attacks": attacks,
    }

    demo = make_instance(seed=3, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    report["G5_density_baseline"] = {
        "pass": isinstance(guess_probability, float)
                and exact_nodes >= 800_000 and density_wall >= 0.0,
        # Top-level numeric mirrors are consumed by submit.sh's schema-agnostic
        # density/cost check; the structured records below retain full context.
        "shipping_density_hits": guess_hits,
        "shipping_density_samples": guess_total,
        "baseline_nodes": exact_nodes,
        "baseline_wall_seconds": round(attack_walls[attack_names[4]], 6),
        "shipping_density": {
            "kind": "sampled",
            "hits": guess_hits,
            "total": guess_total,
            "observed_fraction": guess_probability,
            "wall_clock_sec": round(density_wall, 6),
        },
        "additional_demo_exact_valid_partitions": demo_count,
        "additional_demo_candidate_space": search_space(demo),
        "baseline": {
            "attack": "exact DSATUR with saturation and color symmetry",
            "shipping_instances": len(attack_seeds),
            "nodes_total": exact_nodes,
            "nodes_per_instance": exact_nodes // len(attack_seeds),
            "capped_instances": exact_capped,
            "wall_clock_sec_total": round(attack_walls[attack_names[4]], 6),
            "wall_clock_sec_per_instance": round(
                attack_walls[attack_names[4]] / len(attack_seeds), 6),
        },
    }

    # G7: the certificate space grows and a doubled instance still verifies.
    spaces = []
    for params in DIFFICULTY.values():
        spaces.append(search_space(make_instance(seed=91, **params)))
    doubled_params = dict(shipping_params)
    doubled_params["n"] = 2 * shipping_params["n"]
    doubled = make_instance(seed=91, **doubled_params)
    doubled_ok, doubled_why = verify(doubled, doubled["answer"])
    report["G7_scales"] = {
        "pass": all(a < b for a, b in zip(spaces, spaces[1:])) and doubled_ok,
        "preset_search_spaces": spaces,
        "original_n": shipping_params["n"],
        "doubled_n": doubled_params["n"],
        "doubled_verifies": doubled_ok,
        "verify_reason": doubled_why,
    }

    # G8: vertex relabelling, input order, and their composition over 20 seeds.
    invariant_ok = 0
    invariant_attempts = 0
    carried_ok = 0
    carried_attempts = 0
    unrelated = []
    small_params = {"n": 48, "colors": 4, "density": 9}
    for seed in range(700, 720):
        inst = make_instance(seed=seed, **small_params)
        rng = random.Random(seed ^ 0xC4A0)
        perm = list(range(inst["n"]))
        rng.shuffle(perm)
        relabelled = _relabel_instance(inst, perm)
        reordered = copy.deepcopy(inst)
        reordered["edges"].reverse()
        composed = _relabel_instance(inst, perm, reverse_edges=True)
        key = canonical_key(inst)
        for transformed in (relabelled, reordered, composed):
            invariant_attempts += 1
            invariant_ok += int(canonical_key(transformed) == key)
            carried_attempts += 1
            carried_ok += int(verify(transformed, transformed["answer"])[0])
        unrelated.append(key)
    report["G8_canonical_key"] = {
        "pass": invariant_ok == invariant_attempts
                and carried_ok == carried_attempts
                and len(set(unrelated)) == 20,
        "invariance_checks_passed": invariant_ok,
        "invariance_checks_attempted": invariant_attempts,
        "transformed_witnesses_verified": carried_ok,
        "transformed_witnesses_attempted": carried_attempts,
        "unrelated_distinct_keys": len(set(unrelated)),
        "unrelated_instances": 20,
        "caveat": "1-WL plus cell edge counts is a strong cheap invariant, not a complete graph-isomorphism canonizer",
    }

    answer_blob = json.dumps(density_inst["answer"], separators=(",", ":"))
    answer_elements = sum(len(part) for part in density_inst["answer"])
    answer_tokens = _answer_token_measure(density_inst["answer"])
    intended_ops = density_inst["n"] + density_inst["colors"]
    arms = G9_RESULTS["arms"]
    hinted_minus_placebo = (
        arms["hinted"]["solved"] / max(1, arms["hinted"]["attempts"])
        - arms["placebo"]["solved"] / max(1, arms["placebo"]["attempts"])
    )
    hinted_hardened = G9_RESULTS["hinted_verdict"] == "hardened"
    within_caps = (len(answer_blob) <= 2000 and answer_elements <= 256
                   and intended_ops <= 300)
    report["G9_no_tool_suitability"] = {
        "pass": hinted_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_minus_placebo,
        "hinted_verdict": G9_RESULTS["hinted_verdict"],
        "answer_chars": len(answer_blob),
        "answer_tokens": answer_tokens,
        "answer_elements": answer_elements,
        "intended_route_operations": intended_ops,
        "operation_definition": (
            "one final slot-placement per H vertex plus one class-boundary action "
            "per slot after the independent-set partition is recognized"
        ),
    }

    gates = [value for key, value in report.items() if key.startswith("G")]
    report["all_passed"] = all(gate.get("pass") for gate in gates)
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
