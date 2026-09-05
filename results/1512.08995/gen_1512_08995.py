"""Verified edge-group three-coloring instances from arXiv:1512.08995.

The paper's Section 1 reduction turns a graph H into a bipartite edge-group
graph: original vertices become inputs, original edges become degree-two
outputs, and two singleton stub groups are added at every input.  With only
three colors the stubs force the remaining (principal) group to be
monochromatic, so its colors are exactly a proper three-coloring of H.

This module inverse-generates a balanced coloring of a flat 5-regular graph,
applies that reduction, and publishes only the reduced edge-group instance.
The planted word is retained as a certificate.  Generation is deterministic
in ``(n, seed, params)``, standard-library-only, and silent on import.
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
from collections import Counter
from typing import Any


TRACK = "A"

_REDUCTION_CITATION = (
    "Section 1 (Preliminaries), fixed-k reduction from vertex coloring: "
    "subdivide every source edge and add k-1 singleton stubs per input"
)

PROBLEM_PROFILE = {
    "native_domain": "combinatorics",
    "object_regime": "finite_discrete",
    "computational_core": "csp_sat",
    "certificate_form": "integer_tuple",
    "native_objects": [
        "bipartite graph with edge groups centered at inputs",
        "three-color edge assignment compressed to principal-group colors",
    ],
    "verification_operations": [
        "expand principal-group colors to all edge colors",
        "scan exact group conflicts at inputs",
        "compare colors on edges sharing each output",
    ],
    "domain_essentiality": "licensed_reduction",
    "reduction_kind": "paper_licensed",
    "reduction": _REDUCTION_CITATION,
    "reduction_source": "paper_central",
    "intuition_type": "constraint propagation",
    "intuition_description": (
        "Recognize the balanced hidden tripartition carried by the principal "
        "groups; without it one must backtrack among three colors on hundreds "
        "of mutually coupled groups."
    ),
    "hardness_basis": (
        "Track A: Section 1 proves edge-group k-colorability NP-complete even "
        "for fixed k=3; shipping uses n=252 hidden balanced classes in a "
        "degree-five flat planted regime, where no efficient exact method is "
        "known for the generated distribution and the measured bounded DSATUR "
        "baseline exhausts 1,000,000 search nodes (wall-clock reported by G5)."
    ),
    "max_answer_tokens": 254,
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
    "demo": {"n": 12, "regular_degree": 3, "switch_rounds": 0},
    "easy": {"n": 252, "regular_degree": 5, "switch_rounds": 50},
    "medium": {"n": 252, "regular_degree": 5, "switch_rounds": 75},
    "hard": {"n": 252, "regular_degree": 5, "switch_rounds": 100},
}
SHIPPING_DIFFICULTY = "easy"

STRUCTURAL_HINT = (
    "The planted source graph has three equal-sized independent classes, "
    "although their public vertex labels are uniformly shuffled."
)
PLACEBO_HINT = (
    "The displayed source graph has many similarly sized neighborhoods, "
    "although their public vertex labels should still be read carefully."
)

CERTIFICATE_LANGUAGE = {
    "description": (
        "A word of exactly n symbols from {1,2,3}, in input order, with the "
        "first symbol 1 and the symbol at the stated anchor neighbor 2."
    ),
    "bounds": {
        "alphabet_size": 3,
        "max_word_length": 504,
        "fixed_symmetry_symbols": 2,
    },
}

NOTES = r"""
Paper grounding and Step 0.  Section 1 (Preliminaries) gives the exact
definition used here: an edge group is a set of incident edges with a common
center, and two incident edges conflict precisely when they belong to
different groups.  The same section reduces vertex k-coloring to the restricted
bipartite edge-group problem by subdividing every source edge and adding k-1
singleton stubs at every input.  It explicitly concludes NP-completeness for
fixed k=3.  The module uses those native input/group/output objects and that
paper-licensed reduction, not a convenience graph surrogate.

What produces the certificate.  The answer is sampled first as three balanced
hidden classes.  Edge-disjoint random perfect matchings and three balanced
half-matchings are placed only between different classes, giving a regular
graph of odd degree; then degree-preserving switches erase the exact matching
layers without changing the planted coloring.  No coloring, SAT, matching,
spectral, or linear-algebra algorithm is run during generation.  The certificate
is the planted principal-group color word; the two stub colors are its two
complementary colors.  Verification expands this representation and performs
only exact color comparisons.

What is easy.  Section 2 colors the one-group-per-input case independently at
outputs and gives the general layering bound D_i*Delta_o.  Sections 3 and 4 give
greedy/recoloring and few-colors approximation algorithms.  Section 5 reduces
the second stage of a chosen-menu construction to bipartite matching and proves
a randomized approximation bound.  None is an exact algorithm for recovering
a promised three-coloring.  We avoid the one-group special case in isolation:
every input has its principal group plus two singleton stubs.  We also avoid
claiming that worst-case NP-completeness proves average-case hardness; the Track
A distributional claim rests on the measured panel at the shipping regime and
is stated with that limitation in the README.

Attacks.  Every public vertex has the same odd total degree and every public
edge is sampled by the same matching-and-switch mechanism, so degree outliers
do not identify the plant.  Random relabeling defeats index order.  Switches
destroy the initial layers and exact per-class degree profile that a plain
adjacency eigenspace would expose.
Selftest runs a degree/order outlier probe, saturation greedy coloring,
min-conflicts random restart, non-backtracking spectral clustering, and bounded
exact DSATUR.  Plants and decoys are not separate populations: all groups and
conflict outputs participate in the same planted distribution.
""".strip()


_ANSWER_RE = re.compile(r"<answer\b[^>]*>(.*?)</answer\s*>", re.I | re.S)
_ENUMERATION_CAP = 2_000_000
_DSATUR_PANEL_BUDGET = 1_000_000
_DSATUR_BASELINE_BUDGET = 1_000_000

# Filled from the script-owned hardening runs after the three arms have run.
_ORACLE_EVIDENCE = {
    "bare": {"solved": 0, "attempts": 3},
    "hinted": {"solved": 0, "attempts": 3},
    "placebo": {"solved": 0, "attempts": 3},
    "hinted_verdict": "hardened",
}


def _validate_params(n: int, regular_degree: int, switch_rounds: int) -> None:
    if isinstance(n, bool) or not isinstance(n, int) or n < 12 or n % 6:
        raise ValueError("n must be an integer multiple of 6 and at least 12")
    if n > 504:
        raise ValueError("n may not exceed the certificate-language bound 504")
    class_size = n // 3
    if (isinstance(regular_degree, bool) or not isinstance(regular_degree, int)
            or regular_degree < 2 or regular_degree > 2 * class_size):
        raise ValueError("regular_degree must be an integer in 2..2n/3")
    if (isinstance(switch_rounds, bool) or not isinstance(switch_rounds, int)
            or switch_rounds < 0 or switch_rounds > 100):
        raise ValueError("switch_rounds must be an integer in 0..100")


def _canon_edge(u: int, v: int) -> tuple[int, int]:
    return (u, v) if u < v else (v, u)


def _sample_matching(left: list[int], right: list[int],
                     edges: set[tuple[int, int]],
                     rng: random.Random) -> list[tuple[int, int]]:
    """Sample a simple matching, disjoint from the edges already present."""
    if len(left) != len(right):
        raise ValueError("matching sides must have equal sizes")
    for _attempt in range(10_000):
        targets = right[:]
        rng.shuffle(targets)
        layer = [_canon_edge(left[i], targets[i]) for i in range(len(left))]
        if not any(edge in edges for edge in layer):
            return layer
    raise RuntimeError("could not sample an edge-disjoint matching")


def _regular_tripartite_edges(class_size: int, regular_degree: int,
                               rng: random.Random) -> set[tuple[int, int]]:
    """Build a balanced simple tripartite regular graph with known colors."""
    classes = [list(range(i * class_size, (i + 1) * class_size))
               for i in range(3)]
    edges: set[tuple[int, int]] = set()
    pair_degree = regular_degree // 2
    for left in range(3):
        for right in range(left + 1, 3):
            for _ in range(pair_degree):
                edges.update(_sample_matching(classes[left], classes[right],
                                              edges, rng))

    if regular_degree % 2:
        # Split each class in half.  A half-matching between every pair of
        # classes gives every vertex one extra edge and no degree outlier.
        extra: dict[tuple[int, int], list[int]] = {}
        for color in range(3):
            vertices = classes[color][:]
            rng.shuffle(vertices)
            half = class_size // 2
            extra[(color, (color + 1) % 3)] = vertices[:half]
            extra[(color, (color - 1) % 3)] = vertices[half:]
        for left, right in ((0, 1), (1, 2), (2, 0)):
            edges.update(_sample_matching(extra[(left, right)],
                                          extra[(right, left)], edges, rng))
    return edges


def _switch_edges(edges: set[tuple[int, int]], class_size: int,
                  switch_rounds: int, rng: random.Random) -> None:
    """Destroy matching layers while preserving degree and planted colors."""
    rows = list(edges)
    target = switch_rounds * class_size
    for _ in range(target):
        for _attempt in range(10_000):
            pos1, pos2 = rng.sample(range(len(rows)), 2)
            edge1, edge2 = rows[pos1], rows[pos2]
            u, v = edge1
            x, y = edge2
            orientations = [(u, v, x, y), (u, v, y, x),
                            (v, u, x, y), (v, u, y, x)]
            rng.shuffle(orientations)
            for a, b, c, d in orientations:
                if a == c or a // class_size != c // class_size:
                    continue
                if b // class_size == d // class_size:
                    continue
                new1 = _canon_edge(a, d)
                new2 = _canon_edge(c, b)
                if new1 in edges or new2 in edges:
                    continue
                edges.remove(edge1)
                edges.remove(edge2)
                edges.add(new1)
                edges.add(new2)
                rows[pos1], rows[pos2] = new1, new2
                break
            else:
                continue
            break
        else:
            raise RuntimeError("could not perform a degree-preserving switch")


def _canonicalize_colors(colors: list[int], anchor: int) -> str:
    """Rename a 0/1/2 coloring so positions 0 and anchor become 1 and 2."""
    first = colors[0]
    second = colors[anchor]
    if first == second:
        order = [first] + [c for c in range(3) if c != first]
    else:
        order = [first, second] + [c for c in range(3)
                                   if c not in (first, second)]
    rename = {old: str(new + 1) for new, old in enumerate(order)}
    return "".join(rename[c] for c in colors)


def make_instance(n: int, seed: int = 0, **params: Any) -> dict:
    """Inverse-generate a three-colorable restricted edge-group instance."""
    unknown = set(params) - {"regular_degree", "switch_rounds"}
    if unknown:
        raise TypeError("unknown parameter(s): " + ", ".join(sorted(unknown)))
    regular_degree = params.get("regular_degree", 5)
    switch_rounds = params.get("switch_rounds", 20)
    _validate_params(n, regular_degree, switch_rounds)
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    rng = random.Random(seed)
    class_size = n // 3
    edges = _regular_tripartite_edges(class_size, regular_degree, rng)
    _switch_edges(edges, class_size, switch_rounds, rng)

    # Randomly hide the three balanced independent classes.  The permutation
    # maps old hidden-class positions to public input numbers.
    permutation = list(range(n))
    rng.shuffle(permutation)
    public_edges = sorted(
        _canon_edge(permutation[u], permutation[v]) for u, v in edges
    )
    colors = [0] * n
    for old, public in enumerate(permutation):
        colors[public] = old // class_size

    adjacency = _adjacency(n, public_edges)
    anchor = min(adjacency[0])
    answer = _canonicalize_colors(colors, anchor)
    return {
        "family": "edge_group_three_coloring",
        "n": n,
        "regular_degree": regular_degree,
        "switch_rounds": switch_rounds,
        "colors": 3,
        "base_edges": [[u, v] for u, v in public_edges],
        "anchor_neighbor": anchor,
        "answer": answer,
    }


def _adjacency(n: int, edges: list[list[int]] | list[tuple[int, int]]) -> list[set[int]]:
    adjacency = [set() for _ in range(n)]
    for row in edges:
        u, v = row
        adjacency[u].add(v)
        adjacency[v].add(u)
    return adjacency


def render(inst: dict) -> str:
    """Render the complete reduced edge-group object and answer contract."""
    n = inst["n"]
    edges = inst["base_edges"]
    lines = "\n".join(f"O{j}: I{u} I{v}" for j, (u, v) in enumerate(edges))
    statement = f"""Exact three-coloring of a bipartite edge-group graph

An edge group is a set of graph edges sharing one common endpoint.  A valid
edge-group coloring assigns colors to edges so that two edges with a common
endpoint have different colors exactly when they belong to different groups.
Edges in the same group may share a color.  Only colors 1, 2, and 3 may be used.

This instance has inputs I0,...,I{n - 1}.  Every line below defines one
degree-two conflict output Oj and its two incident inputs.  At each input Iu,
all edges from Iu to listed conflict outputs form one principal group P[u].
In addition, Iu has two private degree-one stub outputs, with one incident edge
in singleton group A[u] and the other in singleton group B[u].  Thus the three
groups at Iu are P[u], A[u], and B[u].  This compact description specifies the
entire bipartite graph, every edge, and every group; private stub outputs have
no other incident edge.

Conflict outputs (input order within a line is irrelevant):
{lines}

Find a valid edge-group coloring with the three allowed colors.  Return its
principal-group color word: symbol u is the common color assigned to every
edge in P[u].  Once that symbol is chosen, assign the two other colors to the
singleton stub groups A[u] and B[u], in increasing order.  Because the two
stubs and P[u] are distinct groups at one input, any valid three-coloring has
exactly this form.  A degree-two output Oj requires its two displayed
principal colors to differ.

The answer must be one word of exactly {n} symbols from the alphabet 1,2,3,
in input order I0 through I{n - 1}; spaces, commas, and repeated indexing are
not allowed.  To remove global color-name symmetry, symbol 0 must be 1 and
symbol {inst['anchor_neighbor']} (the least-numbered conflict neighbor of I0)
must be 2.

Give your final answer inside <answer></answer> tags, as that exact color word.
Syntax-only example (not instance data): <answer>123132</answer>
Output nothing else inside the tags."""
    mode = os.environ.get("GV_HINT_MODE")
    if mode == "structural":
        statement += "\n\n" + STRUCTURAL_HINT
    elif mode == "placebo":
        statement += "\n\n" + PLACEBO_HINT
    return statement


def parse_answer(text: str) -> object | None:
    """Extract the last tagged color word; tolerate prose and fences."""
    if not isinstance(text, str):
        return None
    for body in reversed(_ANSWER_RE.findall(text)):
        body = body.strip()
        if body.startswith("```") and body.endswith("```"):
            rows = body.splitlines()
            if len(rows) >= 3:
                body = "\n".join(rows[1:-1]).strip()
        # Also accept a JSON string containing the exact word.
        if len(body) >= 2 and body[0] == body[-1] == '"':
            try:
                body = json.loads(body)
            except (TypeError, ValueError):
                continue
        if isinstance(body, str) and body and all(c in "123" for c in body):
            return body
    return None


def verify(inst: dict, answer: object) -> tuple[bool, str]:
    """Check any normalized valid principal-group coloring; never read plant."""
    if not isinstance(answer, str):
        return False, "answer must be one color word"
    if not answer:
        return False, "color word must not be empty"
    n = inst.get("n")
    if not isinstance(n, int) or n < 1:
        return False, "malformed instance size"
    if len(answer) != n:
        return False, f"color word must contain exactly {n} symbols"
    if any(c not in "123" for c in answer):
        return False, "every symbol must be one of 1, 2, or 3"
    if answer[0] != "1":
        return False, "symbol 0 must be 1 to normalize color names"
    anchor = inst.get("anchor_neighbor")
    if not isinstance(anchor, int) or not (0 <= anchor < n):
        return False, "malformed anchor neighbor"
    if answer[anchor] != "2":
        return False, f"symbol {anchor} must be 2 to normalize color names"

    edges = inst.get("base_edges")
    if not isinstance(edges, list):
        return False, "malformed conflict-output list"
    seen: set[tuple[int, int]] = set()
    for output, row in enumerate(edges):
        if (not isinstance(row, list) or len(row) != 2
                or any(isinstance(v, bool) or not isinstance(v, int) for v in row)):
            return False, f"malformed conflict output O{output}"
        u, v = row
        if not (0 <= u < v < n) or (u, v) in seen:
            return False, f"malformed endpoints at conflict output O{output}"
        seen.add((u, v))
        if answer[u] == answer[v]:
            return False, (
                f"conflict output O{output} joins I{u} and I{v}, both color "
                f"{answer[u]}"
            )
    # At each input, the principal color plus the two complementary stub
    # colors are pairwise distinct, so the expanded edge coloring is valid.
    return True, "ok"


def random_candidate(inst: dict, rng: random.Random) -> object:
    """Sample uniformly after enforcing the two stated symmetry constraints."""
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be an instance of random.Random")
    n = inst["n"]
    anchor = inst["anchor_neighbor"]
    word = [str(rng.randrange(1, 4)) for _ in range(n)]
    word[0] = "1"
    word[anchor] = "2"
    return "".join(word)


def search_space(inst: dict) -> int | None:
    """Exact size of the normalized three-color-word language."""
    return 3 ** (inst["n"] - 2)


def enumerate_all(inst: dict) -> int | None:
    """Count normalized valid colorings when the exact language is small."""
    if search_space(inst) > _ENUMERATION_CAP:
        return None
    n = inst["n"]
    anchor = inst["anchor_neighbor"]
    free = [i for i in range(n) if i not in (0, anchor)]
    word = ["1"] * n
    word[anchor] = "2"
    count = 0
    for values in itertools.product("123", repeat=len(free)):
        for index, value in zip(free, values):
            word[index] = value
        if verify(inst, "".join(word))[0]:
            count += 1
    return count


def _structural_signature(inst: dict) -> list[Any]:
    """Strong cheap isomorphism invariant (not a complete canonical form)."""
    n = inst["n"]
    adjacency = _adjacency(n, inst["base_edges"])
    degrees = sorted(len(row) for row in adjacency)

    triangles = []
    for u in range(n):
        neighbors = sorted(adjacency[u])
        triangles.append(sum(v in adjacency[w]
                             for i, v in enumerate(neighbors)
                             for w in neighbors[i + 1:]))

    common_hist: Counter[int] = Counter()
    for u in range(n):
        for v in range(u + 1, n):
            common_hist[len(adjacency[u] & adjacency[v])] += 1

    # Exact traces count closed walks and remain invariant under every vertex
    # permutation.  Sparse multiplication costs O(n*m*walk_length).
    traces = []
    for length in range(3, 9):
        trace = 0
        for start in range(n):
            vector = {start: 1}
            for _ in range(length):
                nxt: dict[int, int] = {}
                for u, value in vector.items():
                    for v in adjacency[u]:
                        nxt[v] = nxt.get(v, 0) + value
                vector = nxt
            trace += vector.get(start, 0)
        traces.append(trace)
    return [
        n,
        len(inst["base_edges"]),
        degrees,
        sorted(triangles),
        sorted(common_hist.items()),
        traces,
    ]


def canonical_key(inst: dict) -> str:
    """Hash a structural invariant, never the seed, answer, or rendering."""
    payload = json.dumps(_structural_signature(inst), separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def escalate(params: dict) -> dict | str | None:
    """First erase more planting structure at fixed n, then approach atom cap."""
    if not isinstance(params, dict):
        return None
    n = params.get("n")
    degree = params.get("regular_degree", 5)
    switches = params.get("switch_rounds", 0)
    if not all(isinstance(v, int) and not isinstance(v, bool)
               for v in (n, degree, switches)):
        return None
    out = dict(params)
    if switches < 100:
        out["switch_rounds"] = switches + 1
        return out
    return "cap_bound"


def _transform_instance(inst: dict, permutation: list[int],
                        edge_order: list[int] | None = None,
                        reverse_alternate: bool = False) -> dict:
    """Carry an instance and witness through input/output relabelings."""
    n = inst["n"]
    if sorted(permutation) != list(range(n)):
        raise ValueError("permutation is not a relabeling of 0..n-1")
    rows = []
    for j, (u, v) in enumerate(inst["base_edges"]):
        a, b = permutation[u], permutation[v]
        row = [min(a, b), max(a, b)]
        if reverse_alternate and j % 2:
            row.reverse()
        rows.append(row)
    if edge_order is not None:
        if sorted(edge_order) != list(range(len(rows))):
            raise ValueError("edge_order is not a conflict-output relabeling")
        rows = [rows[i] for i in edge_order]
    # Canonicalize endpoints because verify treats their ordering as syntax,
    # while edge reversal itself is a real undirected-edge representation change.
    rows = [[min(u, v), max(u, v)] for u, v in rows]

    old_word = inst["answer"]
    public_colors = [0] * n
    for old, new in enumerate(permutation):
        public_colors[new] = int(old_word[old]) - 1
    adjacency = _adjacency(n, rows)
    anchor = min(adjacency[0])
    answer = _canonicalize_colors(public_colors, anchor)
    return {
        "family": inst["family"],
        "n": n,
        "regular_degree": inst["regular_degree"],
        "switch_rounds": inst["switch_rounds"],
        "colors": 3,
        "base_edges": rows,
        "anchor_neighbor": anchor,
        "answer": answer,
    }


def _adjacency_for_attack(inst: dict) -> list[set[int]]:
    return _adjacency(inst["n"], inst["base_edges"])


def _degree_order_attack(inst: dict) -> str:
    """Per-element probe: cycle colors down degree/index order."""
    adjacency = _adjacency_for_attack(inst)
    order = sorted(range(inst["n"]), key=lambda u: (-len(adjacency[u]), u))
    colors = [0] * inst["n"]
    for rank, vertex in enumerate(order):
        colors[vertex] = rank % 3
    return _canonicalize_colors(colors, inst["anchor_neighbor"])


def _greedy_saturation_attack(inst: dict) -> str:
    """DSATUR vertex selection with no backtracking."""
    adjacency = _adjacency_for_attack(inst)
    n = inst["n"]
    colors = [-1] * n
    masks = [0] * n
    colors[0] = 0
    anchor = inst["anchor_neighbor"]
    colors[anchor] = 1
    for v in adjacency[0]:
        if colors[v] < 0:
            masks[v] |= 1
    for v in adjacency[anchor]:
        if colors[v] < 0:
            masks[v] |= 2
    for _ in range(n - 2):
        vertex = max((u for u in range(n) if colors[u] < 0),
                     key=lambda u: (masks[u].bit_count(), len(adjacency[u]), -u))
        available = [c for c in range(3) if not masks[vertex] & (1 << c)]
        if not available:
            for u in range(n):
                if colors[u] < 0:
                    colors[u] = 0
            return _canonicalize_colors(colors, anchor)
        color = available[0]
        colors[vertex] = color
        for v in adjacency[vertex]:
            if colors[v] < 0:
                masks[v] |= 1 << color
    return _canonicalize_colors(colors, anchor)


def _min_conflicts_attack(inst: dict, rng: random.Random,
                          restarts: int = 8, steps: int = 5_000
                          ) -> tuple[str, int]:
    """Random-restart local repair with exact incremental conflict counts."""
    adjacency = _adjacency_for_attack(inst)
    n = inst["n"]
    last = [0] * n
    operations = 0
    for _ in range(restarts):
        colors = [rng.randrange(3) for _ in range(n)]
        counts = [sum(colors[v] == colors[w] for w in adjacency[v])
                  for v in range(n)]
        operations += sum(len(row) for row in adjacency)
        bad = {v for v, count in enumerate(counts) if count}
        for _step in range(steps):
            if not bad:
                return _canonicalize_colors(colors, inst["anchor_neighbor"]), operations
            vertex = rng.choice(tuple(bad))
            scores = [sum(colors[w] == color for w in adjacency[vertex])
                      for color in range(3)]
            operations += 3 * len(adjacency[vertex])
            best = min(scores)
            choices = [c for c, score in enumerate(scores) if score == best]
            new_color = rng.choice(choices)
            old_color = colors[vertex]
            if new_color == old_color and rng.randrange(20) == 0:
                new_color = rng.randrange(3)
            if new_color == old_color:
                continue
            colors[vertex] = new_color
            counts[vertex] = scores[new_color]
            for neighbor in adjacency[vertex]:
                if colors[neighbor] == old_color:
                    counts[neighbor] -= 1
                if colors[neighbor] == new_color:
                    counts[neighbor] += 1
                if counts[neighbor]:
                    bad.add(neighbor)
                else:
                    bad.discard(neighbor)
            if counts[vertex]:
                bad.add(vertex)
            else:
                bad.discard(vertex)
        last = colors
    return _canonicalize_colors(last, inst["anchor_neighbor"]), operations


def _nonbacktracking_spectral_attack(inst: dict, rng: random.Random,
                                     iterations: int = 80) -> tuple[str, int]:
    """Two-vector non-backtracking spectral clustering, standard-library only."""
    adjacency = _adjacency_for_attack(inst)
    directed: list[tuple[int, int]] = []
    position: dict[tuple[int, int], int] = {}
    for u in range(inst["n"]):
        for v in sorted(adjacency[u]):
            position[(u, v)] = len(directed)
            directed.append((u, v))
    reverse = [position[(v, u)] for u, v in directed]
    outgoing = [[position[(v, w)] for w in sorted(adjacency[v])]
                for _, v in directed]
    size = len(directed)
    vectors = [[rng.uniform(-1.0, 1.0) for _ in range(size)] for _ in range(2)]
    operations = 0

    def orthonormalize(rows: list[list[float]]) -> list[list[float]]:
        result: list[list[float]] = []
        for row in rows:
            mean = sum(row) / len(row)
            row = [x - mean for x in row]
            for previous in result:
                dot = sum(x * y for x, y in zip(row, previous))
                row = [x - dot * y for x, y in zip(row, previous)]
            norm = math.sqrt(sum(x * x for x in row)) or 1.0
            result.append([x / norm for x in row])
        return result

    vectors = orthonormalize(vectors)
    for _ in range(iterations):
        rows = []
        for vector in vectors:
            sums = [sum(vector[j] for j in out) for out in outgoing]
            # Apply -B.  For directed edge u->v, omit the immediate reverse v->u.
            rows.append([-(sums[i] - vector[reverse[i]]) for i in range(size)])
            operations += sum(len(out) for out in outgoing)
        vectors = orthonormalize(rows)

    points = []
    for vertex in range(inst["n"]):
        incoming = [position[(u, vertex)] for u in adjacency[vertex]]
        points.append(tuple(sum(vector[j] for j in incoming) for vector in vectors))
    # Deterministic farthest-point initialization followed by Lloyd iterations.
    first = min(range(len(points)), key=lambda i: (points[i][0], points[i][1], i))
    centers = [points[first]]
    while len(centers) < 3:
        index = max(
            range(len(points)),
            key=lambda i: min((points[i][0] - c[0]) ** 2
                              + (points[i][1] - c[1]) ** 2 for c in centers),
        )
        centers.append(points[index])
    labels = [0] * len(points)
    for _ in range(20):
        labels = [
            min(range(3), key=lambda c: ((point[0] - centers[c][0]) ** 2
                                         + (point[1] - centers[c][1]) ** 2, c))
            for point in points
        ]
        updated = []
        for color in range(3):
            cluster = [points[i] for i, label in enumerate(labels) if label == color]
            if not cluster:
                updated.append(centers[color])
            else:
                updated.append((sum(p[0] for p in cluster) / len(cluster),
                                sum(p[1] for p in cluster) / len(cluster)))
        if updated == centers:
            break
        centers = updated
    return _canonicalize_colors(labels, inst["anchor_neighbor"]), operations


def _dsatur_attack(inst: dict, node_budget: int
                   ) -> tuple[str | None, int]:
    """Exact DSATUR/DPLL search with propagation and a hard node budget."""
    adjacency = _adjacency_for_attack(inst)
    n = inst["n"]
    anchor = inst["anchor_neighbor"]
    colors = [-1] * n
    masks = [0] * n
    colors[0] = 0
    colors[anchor] = 1
    for v in adjacency[0]:
        if colors[v] < 0:
            masks[v] |= 1
    for v in adjacency[anchor]:
        if colors[v] < 0:
            masks[v] |= 2
    nodes = 0

    def search(left: int) -> list[int] | None:
        nonlocal nodes
        nodes += 1
        if nodes > node_budget:
            return None
        if left == 0:
            return colors[:]
        vertex = max((u for u in range(n) if colors[u] < 0),
                     key=lambda u: (masks[u].bit_count(), len(adjacency[u]), -u))
        available = (~masks[vertex]) & 7
        for color in range(3):
            bit = 1 << color
            if not available & bit:
                continue
            colors[vertex] = color
            changed: list[tuple[int, int]] = []
            impossible = False
            for neighbor in adjacency[vertex]:
                if colors[neighbor] < 0:
                    old = masks[neighbor]
                    new = old | bit
                    if new != old:
                        masks[neighbor] = new
                        changed.append((neighbor, old))
                        if new == 7:
                            impossible = True
            if not impossible:
                result = search(left - 1)
                if result is not None:
                    return result
            for neighbor, old in changed:
                masks[neighbor] = old
            colors[vertex] = -1
            if nodes > node_budget:
                return None
        return None

    result = search(n - 2)
    if result is None:
        return None, nodes
    return _canonicalize_colors(result, anchor), nodes


def _answer_atoms(answer: object) -> int:
    if isinstance(answer, str):
        return len(answer)
    if isinstance(answer, dict):
        return sum(_answer_atoms(value) for value in answer.values())
    if isinstance(answer, list):
        return sum(_answer_atoms(value) for value in answer)
    return 1


def selftest() -> dict:
    """Run G1--G9 and return machine-readable measured evidence."""
    report: dict[str, Any] = {}

    checked = 0
    for preset, params in DIFFICULTY.items():
        for seed in (0, 1, 17, 99):
            inst = make_instance(seed=seed, **params)
            ok, reason = verify(inst, inst["answer"])
            assert ok, (preset, seed, reason)
            assert json.loads(json.dumps(inst["answer"])) == inst["answer"]
            checked += 1
    report["G1_planted_verifies"] = {
        "pass": True,
        "instances": checked,
        "generation_route": "inverse generation plus paper-licensed reduction",
    }

    shipping = DIFFICULTY[SHIPPING_DIFFICULTY]
    inst = make_instance(seed=20260904, **shipping)
    answer = inst["answer"]
    anchor = inst["anchor_neighbor"]
    edge_u, edge_v = next((u, v) for u, v in inst["base_edges"]
                          if u not in (0, anchor) and v not in (0, anchor))
    duplicated = list(answer)
    duplicated[edge_v] = duplicated[edge_u]
    swapped = list(answer)
    swapped[0], swapped[anchor] = swapped[anchor], swapped[0]
    corruptions = {
        "empty": "",
        "drop_one": answer[:-1],
        "swap_normalizers": "".join(swapped),
        "duplicate_across_conflict": "".join(duplicated),
        "out_of_range": answer[:-1] + "4",
    }
    reasons = {}
    for name, bad in corruptions.items():
        ok, reason = verify(inst, bad)
        assert not ok, (name, bad)
        reasons[name] = reason
    assert len(set(reasons.values())) == len(reasons), reasons
    report["G2_rejects_corruption"] = {"pass": True, "reasons": reasons}

    response = (
        "I propagated the forced groups and checked every output.\n"
        "```text\n<answer>" + answer + "</answer>\n```\n"
        "The word uses input order."
    )
    assert parse_answer(response) == answer
    assert parse_answer("no tagged answer") is None
    assert parse_answer("<answer>12x3</answer>") is None
    report["G3_round_trip"] = {
        "pass": True,
        "answer_elements": len(answer),
        "json_native": True,
    }

    guess_inst = make_instance(seed=8675309, **shipping)
    guess_rng = random.Random(13579)
    guess_total = 200_000
    guess_hits = sum(
        verify(guess_inst, random_candidate(guess_inst, guess_rng))[0]
        for _ in range(guess_total)
    )
    guess_density = guess_hits / guess_total
    assert guess_density < 1e-6, (guess_hits, guess_total)
    report["G4_guess_resistance"] = {
        "pass": True,
        "hits": guess_hits,
        "total": guess_total,
        "empirical_probability": guess_density,
        "structure_aware_space": search_space(guess_inst),
        "prior": "uniform normalized color words with both free symmetries fixed",
    }

    demo = make_instance(seed=31415, **DIFFICULTY["demo"])
    demo_count = enumerate_all(demo)
    assert isinstance(demo_count, int) and demo_count >= 1

    density_inst = make_instance(seed=112358, **shipping)
    density_rng = random.Random(24680)
    density_total = 200_000
    density_hits = sum(
        verify(density_inst, random_candidate(density_inst, density_rng))[0]
        for _ in range(density_total)
    )

    baseline_inst = make_instance(seed=424242, **shipping)
    baseline_start = time.perf_counter()
    baseline_answer, baseline_nodes = _dsatur_attack(
        baseline_inst, _DSATUR_BASELINE_BUDGET
    )
    baseline_seconds = time.perf_counter() - baseline_start
    baseline_solved = (baseline_answer is not None
                       and verify(baseline_inst, baseline_answer)[0])
    assert not baseline_solved, (baseline_nodes, baseline_seconds)
    report["G5_density_and_baseline"] = {
        "pass": True,
        "shipping_density_hits": density_hits,
        "shipping_density_samples": density_total,
        "shipping_density_estimate": density_hits / density_total,
        "demo_exact_solution_count": demo_count,
        "demo_n": demo["n"],
        "baseline_wall_seconds": round(baseline_seconds, 6),
        "baseline_nodes": baseline_nodes,
        "baseline_node_budget": _DSATUR_BASELINE_BUDGET,
        "baseline_solved": baseline_solved,
    }

    attack_seeds = list(range(3100, 3108))
    attack_names = [
        "per_element_degree_order",
        "greedy_saturation_no_backtrack",
        "random_restart_min_conflicts_8x5000",
        "nonbacktracking_spectral_clustering",
        "exact_dsatur_dpll_1m_nodes",
    ]
    attacks = {name: {"successes": 0, "attempts": len(attack_seeds)}
               for name in attack_names}
    attack_costs = {name: 0 for name in attack_names}
    for seed in attack_seeds:
        current = make_instance(seed=seed, **shipping)
        candidates: dict[str, str | None] = {}
        candidates[attack_names[0]] = _degree_order_attack(current)
        candidates[attack_names[1]] = _greedy_saturation_attack(current)
        candidate, operations = _min_conflicts_attack(
            current, random.Random(seed ^ 0xA5A5A5A5)
        )
        candidates[attack_names[2]] = candidate
        attack_costs[attack_names[2]] += operations
        candidate, operations = _nonbacktracking_spectral_attack(
            current, random.Random(seed ^ 0x5A5A5A5A)
        )
        candidates[attack_names[3]] = candidate
        attack_costs[attack_names[3]] += operations
        candidate, nodes = _dsatur_attack(current, _DSATUR_PANEL_BUDGET)
        candidates[attack_names[4]] = candidate
        attack_costs[attack_names[4]] += nodes
        for name, candidate in candidates.items():
            if candidate is not None and verify(current, candidate)[0]:
                attacks[name]["successes"] += 1
    all_failed = all(row["successes"] == 0 for row in attacks.values())
    assert all_failed, attacks
    for name in attack_names:
        attacks[name]["operations_or_nodes"] = attack_costs[name]
    report["G6_adversary_panel"] = {
        "pass": all_failed,
        "attacks": attacks,
        "domain_standard_attack": "exact_dsatur_dpll_1m_nodes",
        "construction_aware_attack": "nonbacktracking_spectral_clustering",
    }

    doubled_params = dict(shipping)
    doubled_params["n"] *= 2
    doubled = make_instance(seed=777, **doubled_params)
    doubled_ok, doubled_reason = verify(doubled, doubled["answer"])
    assert doubled_ok, doubled_reason
    escalated = escalate(shipping)
    assert isinstance(escalated, dict) and escalated != shipping
    report["G7_scales"] = {
        "pass": True,
        "shipping_n": shipping["n"],
        "doubled_n": doubled["n"],
        "doubled_edges": len(doubled["base_edges"]),
        "escalated_params": escalated,
    }

    invariant_trials = 0
    carried_trials = 0
    original_keys = []
    for seed in range(20):
        small = make_instance(n=30, regular_degree=5, switch_rounds=8,
                              seed=5000 + seed)
        original_key = canonical_key(small)
        original_keys.append(original_key)
        rng = random.Random(9000 + seed)
        permutation = list(range(small["n"]))
        rng.shuffle(permutation)
        edge_order = list(range(len(small["base_edges"])))
        rng.shuffle(edge_order)
        transformed = _transform_instance(
            small, permutation, edge_order=edge_order, reverse_alternate=True
        )
        assert canonical_key(transformed) == original_key
        invariant_trials += 1
        ok, reason = verify(transformed, transformed["answer"])
        assert ok, reason
        carried_trials += 1
        # Compose with a second independent relabeling.
        second = list(range(small["n"]))
        rng.shuffle(second)
        composed = _transform_instance(transformed, second)
        assert canonical_key(composed) == original_key
        invariant_trials += 1
        ok, reason = verify(composed, composed["answer"])
        assert ok, reason
        carried_trials += 1
    distinct_keys = len(set(original_keys))
    assert distinct_keys == len(original_keys), original_keys
    report["G8_canonical_key"] = {
        "pass": True,
        "invariant_relabelings": invariant_trials,
        "valid_carried_witnesses": carried_trials,
        "distinct_unrelated": distinct_keys,
        "unrelated_attempts": len(original_keys),
        "key_kind": "exact walk/common-neighbor invariant; not seed or render hash",
    }

    answer_chars = len(json.dumps(inst["answer"]))
    answer_atoms = _answer_atoms(inst["answer"])
    # Conservative tokenizer-independent bound: every color symbol may be one
    # token, plus the JSON quote pair.  Actual common tokenizers use fewer.
    answer_tokens = answer_atoms + 2
    intended_operations = inst["n"]
    within_caps = (answer_chars <= 2_000 and answer_atoms <= 256
                   and intended_operations <= 300)
    hinted_still_hardened = _ORACLE_EVIDENCE["hinted_verdict"] == "hardened"
    arms = {key: dict(_ORACLE_EVIDENCE[key])
            for key in ("bare", "hinted", "placebo")}
    hinted_rate = (arms["hinted"]["solved"] / arms["hinted"]["attempts"]
                   if arms["hinted"]["attempts"] else 0.0)
    placebo_rate = (arms["placebo"]["solved"] / arms["placebo"]["attempts"]
                    if arms["placebo"]["attempts"] else 0.0)
    report["G9_no_tool_suitability"] = {
        "pass": hinted_still_hardened and within_caps,
        "arms": arms,
        "hinted_minus_placebo": hinted_rate - placebo_rate,
        "hinted_verdict": _ORACLE_EVIDENCE["hinted_verdict"],
        "answer_chars": answer_chars,
        "answer_tokens": answer_tokens,
        "answer_elements": answer_atoms,
        "intended_route_operations": intended_operations,
        "within_caps": within_caps,
    }

    report["all_passed"] = all(
        isinstance(value, dict) and value.get("pass")
        for key, value in report.items() if key.startswith("G")
    )
    return report


if __name__ == "__main__":
    print(json.dumps(selftest(), indent=2, sort_keys=True))
